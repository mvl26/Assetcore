// Copyright (c) 2026, AssetCore Team
// Client Script: Incident Report — IMM-12

frappe.ui.form.on('Incident Report', {

	refresh(frm) {
		_set_field_visibility(frm);
		_add_custom_buttons(frm);
		_add_indicators(frm);
	},

	workflow_state(frm) {
		_set_field_visibility(frm);
	},

	severity(frm) {
		_auto_toggle_rca(frm);
	},

	patient_affected(frm) {
		_toggle_patient_section(frm);
	},

	asset(frm) {
		_load_asset_history(frm);
	},
});

function _set_field_visibility(frm) {
	const state = frm.doc.workflow_state;
	const isOpen = state === 'Open';
	const isAck = state === 'Acknowledged';
	const isInProgress = state === 'In Progress';
	const isResolved = state === 'Resolved';
	const isRcaReq = state === 'RCA Required';
	const isClosed = state === 'Closed';

	// Lock metadata sau khi đã ack
	frm.toggle_enable(['asset', 'incident_type', 'severity', 'description',
		'reported_by', 'reported_at'], isOpen);

	// Patient section
	_toggle_patient_section(frm);

	// Resolution section khi gần xong
	frm.toggle_display(['resolution_notes', 'root_cause'],
		isInProgress || isResolved || isRcaReq || isClosed);

	if (isInProgress || isResolved) {
		frm.set_df_property('resolution_notes', 'reqd', 1);
	}
}

function _add_indicators(frm) {
	const sev = frm.doc.severity;
	if (sev === 'Critical') {
		frm.dashboard.add_indicator(__('Critical'), 'red');
	} else if (sev === 'High') {
		frm.dashboard.add_indicator(__('High'), 'orange');
	}
	if (frm.doc.patient_affected) {
		frm.dashboard.add_indicator(__('⚠️ Có ảnh hưởng bệnh nhân'), 'red');
	}
	if (frm.doc.requires_rca) {
		frm.dashboard.add_indicator(__('Yêu cầu RCA'), 'orange');
	}
}

function _add_custom_buttons(frm) {
	if (frm.is_new()) return;
	const state = frm.doc.workflow_state;

	// Tiếp nhận
	if (state === 'Open') {
		frm.add_custom_button(__('Tiếp nhận sự cố'), () => {
			_prompt_acknowledge(frm);
		}, __('Hành động'));
	}

	// Đánh dấu giải quyết
	if (state === 'In Progress') {
		frm.add_custom_button(__('Đánh dấu đã giải quyết'), () => {
			_prompt_resolve(frm);
		}, __('Hành động'));
	}

	// Tạo RCA
	if ((state === 'Resolved' || state === 'RCA Required') && !_has_rca(frm)) {
		frm.add_custom_button(__('Tạo RCA'), () => {
			_prompt_create_rca(frm);
		}, __('Hành động'));
	}

	// Tạo Asset Repair từ Incident
	if (state === 'In Progress' || state === 'Acknowledged') {
		frm.add_custom_button(__('Tạo phiếu sửa chữa'), () => {
			frappe.new_doc('Asset Repair', {
				asset_ref: frm.doc.asset,
				incident_report: frm.doc.name,
				repair_type: 'Corrective',
				priority: frm.doc.severity === 'Critical' ? 'Critical'
					: frm.doc.severity === 'High' ? 'High' : 'Medium',
			});
		}, __('Hành động'));
	}

	// Lịch sử sự cố
	if (frm.doc.asset) {
		frm.add_custom_button(__('Lịch sử sự cố thiết bị'), () => {
			frappe.set_route('List', 'Incident Report', { asset: frm.doc.asset });
		});
	}
}

function _prompt_acknowledge(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Tiếp nhận sự cố'),
		fields: [
			{ fieldname: 'assigned_to', fieldtype: 'Link', options: 'User',
			  label: __('Phân công cho'), reqd: 1 },
			{ fieldname: 'notes', fieldtype: 'Small Text',
			  label: __('Ghi chú') },
		],
		primary_action_label: __('Tiếp nhận'),
		primary_action({ assigned_to, notes }) {
			frappe.call({
				method: 'assetcore.api.imm12.acknowledge_incident',
				args: { name: frm.doc.name, assigned_to, notes: notes || '' },
				callback(r) {
					if (!r.exc) { d.hide(); frm.reload_doc(); }
				},
			});
		},
	});
	d.show();
}

function _prompt_resolve(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Đánh dấu đã giải quyết'),
		fields: [
			{ fieldname: 'resolution_notes', fieldtype: 'Small Text',
			  label: __('Tóm tắt giải quyết'), reqd: 1 },
			{ fieldname: 'root_cause', fieldtype: 'Small Text',
			  label: __('Nguyên nhân gốc') },
		],
		primary_action_label: __('Lưu & chuyển Resolved'),
		primary_action({ resolution_notes, root_cause }) {
			frappe.call({
				method: 'assetcore.api.imm12.resolve_incident',
				args: {
					name: frm.doc.name,
					resolution_notes,
					root_cause: root_cause || '',
				},
				callback(r) {
					if (!r.exc) { d.hide(); frm.reload_doc(); }
				},
			});
		},
	});
	d.show();
}

function _prompt_create_rca(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Tạo phân tích RCA'),
		fields: [
			{ fieldname: 'rca_method', fieldtype: 'Select',
			  label: __('Phương pháp'),
			  options: '5-Why\nFishbone\nFault Tree',
			  default: '5-Why', reqd: 1 },
		],
		primary_action_label: __('Tạo RCA'),
		primary_action({ rca_method }) {
			frappe.call({
				method: 'assetcore.api.imm12.create_rca',
				args: { incident_name: frm.doc.name, rca_method },
				callback(r) {
					if (!r.exc && r.message?.data?.name) {
						d.hide();
						frappe.set_route('Form', 'IMM RCA Record', r.message.data.name);
					}
				},
			});
		},
	});
	d.show();
}

function _toggle_patient_section(frm) {
	const affected = frm.doc.patient_affected;
	frm.toggle_display('patient_impact_description', affected);
	frm.set_df_property('patient_impact_description', 'reqd', affected ? 1 : 0);
}

function _auto_toggle_rca(frm) {
	const sev = frm.doc.severity;
	if (sev === 'High' || sev === 'Critical') {
		if (!frm.doc.requires_rca) {
			frm.set_value('requires_rca', 1);
			frappe.show_alert({
				message: __('Severity {0} → tự động bật yêu cầu RCA', [sev]),
				indicator: 'orange',
			});
		}
	}
}

function _load_asset_history(frm) {
	if (!frm.doc.asset) return;
	frappe.call({
		method: 'assetcore.api.imm12.get_asset_incident_history',
		args: { asset: frm.doc.asset, limit: 5 },
		callback(r) {
			const history = r.message?.data?.history || [];
			if (history.length >= 3) {
				frappe.show_alert({
					message: __('⚠️ Asset này đã có {0} sự cố gần đây — có thể chronic failure',
						[history.length]),
					indicator: 'orange',
				});
			}
		},
	});
}

function _has_rca(frm) {
	// Cách đơn giản: kiểm tra link field. Frappe tự fetch nếu có.
	return !!frm.doc.linked_rca;
}
