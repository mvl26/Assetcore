// Copyright (c) 2026, AssetCore Team
// Client Script: Asset Repair — IMM-09

frappe.ui.form.on('Asset Repair', {

	refresh(frm) {
		_set_field_visibility(frm);
		_add_custom_buttons(frm);
		_add_indicators(frm);
	},

	workflow_state(frm) {
		_set_field_visibility(frm);
	},

	asset_ref(frm) {
		_load_asset_context(frm);
	},

	priority(frm) {
		_compute_sla(frm);
	},
});

function _set_field_visibility(frm) {
	const state = frm.doc.workflow_state;
	const isOpen = state === 'Open';
	const isAssigned = state === 'Assigned';
	const isDiagnosing = state === 'Diagnosing';
	const isPendingParts = state === 'Pending Parts';
	const isInRepair = state === 'In Repair';
	const isPendingInsp = state === 'Pending Inspection';
	const isCompleted = state === 'Completed';

	// Diagnosis chỉ edit khi Diagnosing
	frm.toggle_enable('diagnosis_notes', isDiagnosing || isAssigned);

	// Lock metadata sau khi đã assign
	frm.toggle_enable(['asset_ref', 'incident_report', 'source_pm_wo',
		'repair_type', 'priority'], isOpen);

	// Show parts section khi cần
	frm.toggle_display(['section_parts', 'spare_parts'],
		isPendingParts || isInRepair || isPendingInsp || isCompleted);

	// Show closure section khi gần xong
	frm.toggle_display(['section_closure', 'repair_summary', 'root_cause_category'],
		isPendingInsp || isCompleted);

	if (isPendingInsp || isCompleted) {
		frm.set_df_property('repair_summary', 'reqd', 1);
		frm.set_df_property('root_cause_category', 'reqd', 1);
	}
}

function _add_indicators(frm) {
	if (frm.doc.is_repeat_failure) {
		frm.dashboard.add_indicator(__('Lỗi lặp lại'), 'red');
	}
	if (frm.doc.sla_breached) {
		frm.dashboard.add_indicator(__('SLA quá hạn'), 'red');
	}
	const p = frm.doc.priority;
	if (p === 'Critical' || p === 'High') {
		frm.dashboard.add_indicator(__(`Ưu tiên ${p}`), 'orange');
	}
}

function _add_custom_buttons(frm) {
	if (frm.is_new()) return;
	const state = frm.doc.workflow_state;

	// Phân công KTV
	if (state === 'Open') {
		frm.add_custom_button(__('Phân công KTV'), () => {
			_prompt_assign(frm);
		}, __('Hành động'));
	}

	// Submit diagnosis
	if (state === 'Diagnosing') {
		frm.add_custom_button(__('Hoàn tất chẩn đoán'), () => {
			_prompt_diagnosis(frm);
		}, __('Hành động'));
	}

	// Yêu cầu phụ tùng
	if (state === 'Diagnosing' || state === 'In Repair') {
		frm.add_custom_button(__('Yêu cầu phụ tùng'), () => {
			_prompt_request_parts(frm);
		}, __('Hành động'));
	}

	// Đóng phiếu
	if (state === 'Pending Inspection') {
		frm.add_custom_button(__('Đóng phiếu'), () => {
			_prompt_close(frm);
		}, __('Hành động'));
	}

	// Lịch sử repair của asset
	if (frm.doc.asset_ref) {
		frm.add_custom_button(__('Lịch sử sửa chữa thiết bị'), () => {
			frappe.set_route('List', 'Asset Repair', { asset_ref: frm.doc.asset_ref });
		});
	}
}

function _prompt_assign(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Phân công KTV'),
		fields: [
			{ fieldname: 'technician', fieldtype: 'Link', options: 'User',
			  label: __('Kỹ thuật viên'), reqd: 1 },
			{ fieldname: 'priority', fieldtype: 'Select',
			  options: 'Low\nMedium\nHigh\nCritical',
			  default: frm.doc.priority || 'Medium', label: __('Ưu tiên') },
		],
		primary_action_label: __('Phân công'),
		primary_action({ technician, priority }) {
			frappe.call({
				method: 'assetcore.api.imm09.assign_technician',
				args: { name: frm.doc.name, technician, priority },
				callback(r) {
					if (!r.exc) { d.hide(); frm.reload_doc(); }
				},
			});
		},
	});
	d.show();
}

function _prompt_diagnosis(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Hoàn tất chẩn đoán'),
		fields: [
			{ fieldname: 'diagnosis_notes', fieldtype: 'Small Text',
			  label: __('Kết quả chẩn đoán'), reqd: 1 },
			{ fieldname: 'needs_parts', fieldtype: 'Check',
			  label: __('Cần phụ tùng?') },
		],
		primary_action_label: __('Lưu chẩn đoán'),
		primary_action({ diagnosis_notes, needs_parts }) {
			frappe.call({
				method: 'assetcore.api.imm09.submit_diagnosis',
				args: {
					name: frm.doc.name,
					diagnosis_notes,
					needs_parts: needs_parts ? 1 : 0,
				},
				callback(r) {
					if (!r.exc) { d.hide(); frm.reload_doc(); }
				},
			});
		},
	});
	d.show();
}

function _prompt_request_parts(frm) {
	frappe.msgprint(__('Mở section "Phụ tùng" trên form, thêm dòng linh kiện rồi bấm "Yêu cầu" trên từng dòng.'));
	frm.scroll_to_field('spare_parts');
}

function _prompt_close(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Đóng phiếu sửa chữa'),
		fields: [
			{ fieldname: 'repair_summary', fieldtype: 'Small Text',
			  label: __('Tóm tắt sửa chữa'), reqd: 1,
			  default: frm.doc.repair_summary },
			{ fieldname: 'root_cause_category', fieldtype: 'Select',
			  label: __('Phân loại nguyên nhân'),
			  options: '\nUser Error\nWear and Tear\nDesign Defect\nEnvironmental\nMaintenance Lapse\nUnknown',
			  reqd: 1, default: frm.doc.root_cause_category },
		],
		primary_action_label: __('Đóng phiếu'),
		primary_action({ repair_summary, root_cause_category }) {
			frappe.call({
				method: 'assetcore.api.imm09.close_work_order',
				args: {
					name: frm.doc.name,
					repair_summary,
					root_cause_category,
				},
				callback(r) {
					if (!r.exc) { d.hide(); frm.reload_doc(); }
				},
			});
		},
	});
	d.show();
}

function _load_asset_context(frm) {
	if (!frm.doc.asset_ref) return;
	frappe.db.get_value('AC Asset', frm.doc.asset_ref,
		['device_model', 'lifecycle_status', 'risk_class'], (v) => {
			if (!v) return;
			if (v.lifecycle_status === 'Decommissioned') {
				frappe.show_alert({
					message: __('⚠️ Thiết bị đã thanh lý — không thể sửa'),
					indicator: 'red',
				});
			}
			if (v.risk_class === 'C' || v.risk_class === 'D') {
				frappe.show_alert({
					message: __(`Risk class ${v.risk_class} — yêu cầu QA approval khi đóng`),
					indicator: 'orange',
				});
			}
		});
}

function _compute_sla(frm) {
	const map = { Critical: 4, High: 8, Medium: 24, Low: 72 };
	const hrs = map[frm.doc.priority];
	if (hrs && !frm.doc.sla_target_hours) {
		frm.set_value('sla_target_hours', hrs);
	}
}
