// Copyright (c) 2026, AssetCore Team
// Client Script: IMM RCA Record — IMM-12

frappe.ui.form.on('IMM RCA Record', {

	refresh(frm) {
		_set_field_visibility(frm);
		_add_custom_buttons(frm);
		_add_indicators(frm);
		_check_minimum_5why(frm);
	},

	workflow_state(frm) {
		_set_field_visibility(frm);
	},

	rca_method(frm) {
		_toggle_method_section(frm);
	},

	status(frm) {
		_set_field_visibility(frm);
	},
});

frappe.ui.form.on('IMM RCA Five Why Step', {
	five_why_steps_add(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (!row.why_number) {
			const next = (frm.doc.five_why_steps || []).length;
			row.why_number = next;
			frm.refresh_field('five_why_steps');
		}
	},
});

function _set_field_visibility(frm) {
	const state = frm.doc.workflow_state;
	const isReq = state === 'RCA Required';
	const isInProgress = state === 'RCA In Progress';
	const isCompleted = state === 'Completed';

	_toggle_method_section(frm);

	// Lock metadata khi đã start
	frm.toggle_enable(['incident_report', 'asset', 'trigger_type', 'rca_method'],
		isReq);

	// Bắt buộc fields khi Completed
	if (isCompleted || frm.doc.status === 'Completed') {
		frm.set_df_property('root_cause', 'reqd', 1);
		frm.set_df_property('corrective_action_summary', 'reqd', 1);
	}

	// Lock 5-why steps khi Completed (read-only)
	if (isCompleted) {
		frm.toggle_enable(['five_why_steps', 'root_cause',
			'contributing_factors', 'corrective_action_summary',
			'preventive_action_summary'], 0);
	}
}

function _toggle_method_section(frm) {
	const isFiveWhy = (frm.doc.rca_method || '').toLowerCase().includes('5')
		|| (frm.doc.rca_method || '').toLowerCase().includes('why');
	frm.toggle_display('section_five_why', isFiveWhy);
	if (isFiveWhy && (frm.doc.status === 'RCA In Progress'
		|| frm.doc.workflow_state === 'RCA In Progress')) {
		frm.set_df_property('five_why_steps', 'reqd', 1);
	}
}

function _add_indicators(frm) {
	if (frm.doc.status === 'Completed') {
		frm.dashboard.add_indicator(__('RCA hoàn tất'), 'green');
	} else if (frm.doc.status === 'RCA In Progress') {
		frm.dashboard.add_indicator(__('Đang phân tích'), 'orange');
	}
	if (frm.doc.due_date) {
		const due = frappe.datetime.str_to_obj(frm.doc.due_date);
		const today = frappe.datetime.now_date();
		if (frappe.datetime.get_diff(frm.doc.due_date, today) < 0
			&& frm.doc.status !== 'Completed') {
			frm.dashboard.add_indicator(__('Quá hạn'), 'red');
		}
	}
	if ((frm.doc.incident_count || 0) >= 3) {
		frm.dashboard.add_indicator(
			__('Chronic failure ({0} sự cố)', [frm.doc.incident_count]),
			'red'
		);
	}
}

function _add_custom_buttons(frm) {
	if (frm.is_new()) return;
	const state = frm.doc.workflow_state;

	// Thêm bước 5-Why nhanh
	if ((state === 'RCA In Progress' || state === 'RCA Required')
		&& frm.doc.rca_method && frm.doc.rca_method.toLowerCase().includes('why')) {
		frm.add_custom_button(__('Thêm bước Why'), () => {
			_prompt_add_why(frm);
		}, __('Hành động'));
	}

	// Tạo CAPA từ RCA
	if (state === 'RCA In Progress' && !frm.doc.linked_capa) {
		frm.add_custom_button(__('Tạo CAPA'), () => {
			frappe.new_doc('IMM CAPA Record', {
				source_rca: frm.doc.name,
				asset: frm.doc.asset,
				root_cause: frm.doc.root_cause,
				corrective_action: frm.doc.corrective_action_summary,
			});
		}, __('Hành động'));
	}

	// Mở Incident Report gốc
	if (frm.doc.incident_report) {
		frm.add_custom_button(__('Xem Incident gốc'), () => {
			frappe.set_route('Form', 'Incident Report', frm.doc.incident_report);
		});
	}
}

function _prompt_add_why(frm) {
	const existing = frm.doc.five_why_steps || [];
	const next_num = existing.length + 1;
	if (next_num > 5) {
		frappe.msgprint(__('Đã đủ 5 bước Why.'));
		return;
	}
	const last_answer = existing.length
		? existing[existing.length - 1].why_answer || ''
		: '';
	const default_q = next_num === 1
		? __('Tại sao sự cố xảy ra?')
		: __('Tại sao "{0}"?', [last_answer.slice(0, 80)]);

	const d = new frappe.ui.Dialog({
		title: __('Why #{0}', [next_num]),
		fields: [
			{ fieldname: 'why_question', fieldtype: 'Small Text',
			  label: __('Câu hỏi'), reqd: 1, default: default_q },
			{ fieldname: 'why_answer', fieldtype: 'Small Text',
			  label: __('Câu trả lời'), reqd: 1 },
		],
		primary_action_label: __('Thêm'),
		primary_action({ why_question, why_answer }) {
			frm.add_child('five_why_steps', {
				why_number: next_num,
				why_question,
				why_answer,
			});
			frm.refresh_field('five_why_steps');
			frm.dirty();
			d.hide();
		},
	});
	d.show();
}

function _check_minimum_5why(frm) {
	if (!frm.doc.rca_method) return;
	const m = frm.doc.rca_method.toLowerCase();
	if (!m.includes('why')) return;
	if (frm.doc.status !== 'Completed') return;
	const n = (frm.doc.five_why_steps || []).length;
	if (n < 5) {
		frm.dashboard.add_indicator(
			__('Thiếu Why ({0}/5)', [n]), 'red'
		);
	}
}
