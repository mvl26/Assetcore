// Copyright (c) 2026, AssetCore Team
// Client Script: IMM Asset Calibration — IMM-11

frappe.ui.form.on('IMM Asset Calibration', {

	refresh(frm) {
		_set_field_visibility(frm);
		_add_custom_buttons(frm);
		_add_indicators(frm);
	},

	workflow_state(frm) {
		_set_field_visibility(frm);
	},

	calibration_type(frm) {
		_toggle_calibration_type_sections(frm);
	},

	overall_result(frm) {
		_toggle_capa_section(frm);
	},

	asset(frm) {
		_load_asset_context(frm);
	},
});

function _set_field_visibility(frm) {
	const state = frm.doc.workflow_state;
	const isScheduled = state === 'Scheduled';
	const isInProgress = state === 'In Progress';
	const isSentToLab = state === 'Sent to Lab';
	const isCertReceived = state === 'Certificate Received';
	const isPassed = state === 'Passed';
	const isFailed = state === 'Failed';
	const isConditionallyPassed = state === 'Conditionally Passed';

	_toggle_calibration_type_sections(frm);
	_toggle_capa_section(frm);

	// Lock metadata khi đã start
	frm.toggle_enable(['asset', 'calibration_type', 'calibration_schedule',
		'scheduled_date'], isScheduled);

	// Cert section khi nhận chứng chỉ
	frm.toggle_display(['certificate_file', 'certificate_date',
		'certificate_number', 'next_calibration_date', 'overall_result'],
		isInProgress || isCertReceived || isPassed || isFailed || isConditionallyPassed);

	// Required khi cần nhận cert
	if (isCertReceived || isInProgress) {
		frm.set_df_property('certificate_file', 'reqd', 1);
		frm.set_df_property('certificate_number', 'reqd', 1);
		frm.set_df_property('next_calibration_date', 'reqd', 1);
		frm.set_df_property('overall_result', 'reqd', 1);
	}
}

function _toggle_calibration_type_sections(frm) {
	const t = frm.doc.calibration_type;
	const isExternal = t === 'External';
	const isInhouse = t === 'In-House';

	frm.toggle_display('section_lab', isExternal);
	frm.toggle_display('section_inhouse', isInhouse);

	if (isExternal) {
		frm.set_df_property('lab_supplier', 'reqd', 1);
		frm.set_df_property('lab_accreditation_number', 'reqd', 1);
	}
	if (isInhouse) {
		frm.set_df_property('reference_standard_serial', 'reqd', 1);
		frm.set_df_property('traceability_reference', 'reqd', 1);
	}
}

function _toggle_capa_section(frm) {
	const result = frm.doc.overall_result;
	const needCapa = result === 'Failed' || result === 'Conditionally Passed';
	frm.toggle_display(['capa_record', 'capa_closed'], needCapa);
	if (needCapa) {
		frm.dashboard.add_indicator(__('Cần CAPA'), 'orange');
	}
}

function _add_indicators(frm) {
	const r = frm.doc.overall_result;
	if (r === 'Passed') {
		frm.dashboard.add_indicator(__('Đạt'), 'green');
	} else if (r === 'Failed') {
		frm.dashboard.add_indicator(__('Không đạt'), 'red');
	} else if (r === 'Conditionally Passed') {
		frm.dashboard.add_indicator(__('Đạt có điều kiện'), 'orange');
	}
	if (frm.doc.workflow_state === 'Sent to Lab') {
		frm.dashboard.add_indicator(__('Đang ở phòng hiệu chuẩn'), 'blue');
	}
}

function _add_custom_buttons(frm) {
	if (frm.is_new()) return;
	const state = frm.doc.workflow_state;

	// Thêm phép đo
	if (state === 'In Progress' || state === 'Certificate Received') {
		frm.add_custom_button(__('Thêm phép đo'), () => {
			_prompt_add_measurement(frm);
		}, __('Hành động'));
	}

	// Đánh dấu CAPA closed
	if (frm.doc.overall_result === 'Failed' && !frm.doc.capa_closed
		&& frm.doc.capa_record) {
		frm.add_custom_button(__('Đánh dấu CAPA hoàn tất'), () => {
			frappe.confirm(
				__('CAPA {0} đã hoàn tất? Sau đó có thể chuyển sang Conditionally Passed.',
				   [frm.doc.capa_record]),
				() => frm.set_value('capa_closed', 1).then(() => frm.save())
			);
		}, __('Hành động'));
	}

	// Lịch sử calibration của asset
	if (frm.doc.asset) {
		frm.add_custom_button(__('Lịch sử hiệu chuẩn'), () => {
			frappe.set_route('List', 'IMM Asset Calibration', { asset: frm.doc.asset });
		});
	}
}

function _prompt_add_measurement(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Thêm phép đo'),
		fields: [
			{ fieldname: 'parameter_name', fieldtype: 'Data',
			  label: __('Tham số'), reqd: 1 },
			{ fieldname: 'unit', fieldtype: 'Data', label: __('Đơn vị'), reqd: 1 },
			{ fieldname: 'nominal_value', fieldtype: 'Float',
			  label: __('Giá trị danh định'), reqd: 1 },
			{ fieldname: 'measured_value', fieldtype: 'Float',
			  label: __('Giá trị đo'), reqd: 1 },
			{ fieldname: 'tolerance', fieldtype: 'Float',
			  label: __('Dung sai (±)'), reqd: 1 },
		],
		primary_action_label: __('Thêm'),
		primary_action(values) {
			frappe.call({
				method: 'assetcore.api.imm11.add_measurement',
				args: { name: frm.doc.name, ...values },
				callback(r) {
					if (!r.exc) { d.hide(); frm.reload_doc(); }
				},
			});
		},
	});
	d.show();
}

function _load_asset_context(frm) {
	if (!frm.doc.asset) return;
	frappe.db.get_value('AC Asset', frm.doc.asset,
		['device_model', 'lifecycle_status'], (v) => {
			if (v && v.lifecycle_status === 'Decommissioned') {
				frappe.show_alert({
					message: __('⚠️ Thiết bị đã thanh lý'),
					indicator: 'red',
				});
			}
		});
}
