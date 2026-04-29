// Copyright (c) 2026, AssetCore Team
// Client Script: PM Work Order — IMM-08

frappe.ui.form.on('PM Work Order', {

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
});

function _set_field_visibility(frm) {
	const state = frm.doc.workflow_state;
	const isOpen = state === 'Open';
	const isInProgress = state === 'In Progress';
	const isPending = state === 'Pending–Device Busy';
	const isCompleted = state === 'Completed';
	const isHalted = state === 'Halted–Major Failure';

	// Result section: chỉ enable khi In Progress hoặc Completed
	frm.toggle_enable(['overall_result', 'technician_notes',
		'pm_sticker_attached', 'duration_minutes', 'attachments'],
		isInProgress || isCompleted);

	// Checklist: edit khi In Progress
	frm.toggle_enable('checklist_results', isInProgress);

	// Source PM (CM-trigger) chỉ hiện khi wo_type = CM
	frm.toggle_display('source_pm_wo', frm.doc.wo_type === 'CM');

	// Khóa metadata sau khi đã start
	frm.toggle_enable(['asset_ref', 'pm_schedule', 'pm_type', 'wo_type',
		'due_date', 'scheduled_date'], isOpen);

	// Halted: bắt buộc note
	if (isHalted) {
		frm.set_df_property('technician_notes', 'reqd', 1);
	}
}

function _add_indicators(frm) {
	if (frm.doc.is_late) {
		frm.dashboard.add_indicator(__('Trễ hạn'), 'red');
	}
	if (frm.doc.workflow_state === 'Completed') {
		frm.dashboard.add_indicator(__('Đã hoàn thành'), 'green');
	} else if (frm.doc.workflow_state === 'Halted–Major Failure') {
		frm.dashboard.add_indicator(__('Lỗi nghiêm trọng - đã tạo CM'), 'red');
	}
}

function _add_custom_buttons(frm) {
	if (frm.is_new()) return;
	const state = frm.doc.workflow_state;

	// Báo lỗi nghiêm trọng → tạo Asset Repair (CM)
	if (state === 'In Progress') {
		frm.add_custom_button(__('Báo lỗi nghiêm trọng'), () => {
			_prompt_major_failure(frm);
		}, __('Hành động'));
	}

	// Reschedule khi Open / Overdue
	if (state === 'Open' || state === 'Overdue') {
		frm.add_custom_button(__('Đổi lịch'), () => {
			_prompt_reschedule(frm);
		}, __('Hành động'));
	}

	// Xem lịch sử PM của asset
	if (frm.doc.asset_ref) {
		frm.add_custom_button(__('Lịch sử PM của thiết bị'), () => {
			frappe.set_route('List', 'PM Work Order', {
				asset_ref: frm.doc.asset_ref,
			});
		});
	}
}

function _prompt_major_failure(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Báo cáo lỗi nghiêm trọng'),
		fields: [
			{ fieldname: 'failure_description', fieldtype: 'Small Text',
			  label: __('Mô tả lỗi'), reqd: 1 },
			{ fieldname: 'severity', fieldtype: 'Select',
			  label: __('Mức độ'), options: 'Low\nMedium\nHigh\nCritical',
			  default: 'High', reqd: 1 },
		],
		primary_action_label: __('Báo cáo & tạo CM'),
		primary_action({ failure_description, severity }) {
			frappe.call({
				method: 'assetcore.api.imm08.report_major_failure',
				args: {
					pm_wo_name: frm.doc.name,
					failure_description,
					severity,
				},
				freeze: true,
				freeze_message: __('Đang tạo Work Order CM…'),
				callback(r) {
					if (!r.exc) {
						d.hide();
						frappe.show_alert({
							message: __('Đã chuyển sang Halted và tạo CM'),
							indicator: 'orange',
						});
						frm.reload_doc();
					}
				},
			});
		},
	});
	d.show();
}

function _prompt_reschedule(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Đổi lịch PM'),
		fields: [
			{ fieldname: 'new_date', fieldtype: 'Date',
			  label: __('Ngày mới'), reqd: 1 },
			{ fieldname: 'reason', fieldtype: 'Small Text',
			  label: __('Lý do'), reqd: 1 },
		],
		primary_action_label: __('Cập nhật'),
		primary_action({ new_date, reason }) {
			frappe.call({
				method: 'assetcore.api.imm08.reschedule_pm',
				args: { name: frm.doc.name, new_date, reason },
				callback(r) {
					if (!r.exc) {
						d.hide();
						frm.reload_doc();
					}
				},
			});
		},
	});
	d.show();
}

function _load_asset_context(frm) {
	if (!frm.doc.asset_ref) return;
	frappe.db.get_value('AC Asset', frm.doc.asset_ref,
		['device_model', 'lifecycle_status'], (v) => {
			if (v && v.lifecycle_status === 'Out of Service') {
				frappe.show_alert({
					message: __('⚠️ Thiết bị đang Out of Service'),
					indicator: 'red',
				});
			}
		});
}
