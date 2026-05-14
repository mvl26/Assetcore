// Copyright (c) 2026, AssetCore Team
// Client Script: Asset Document — IMM-05

frappe.ui.form.on('Asset Document', {

	refresh(frm) {
		_set_field_visibility(frm);
		_add_custom_buttons(frm);
	},

	workflow_state(frm) {
		_set_field_visibility(frm);
	},

	doc_category(frm) {
		_toggle_expiry_required(frm);
		_toggle_authority_required(frm);
	},

	is_exempt(frm) {
		_toggle_exempt_section(frm);
	},

	version(frm) {
		_toggle_change_summary_required(frm);
	},

	// ── Field visibility theo state ───────────────────────────────────────────
});

function _set_field_visibility(frm) {
	const state = frm.doc.workflow_state;
	const isDraft = state === 'Draft';
	const isRejected = state === 'Rejected';
	const isActive = state === 'Active';
	const isArchived = state === 'Archived';
	const isExpired = state === 'Expired';

	// Approval section: chỉ hiện khi Active
	frm.toggle_display(['approved_by', 'approval_date'], isActive);

	// Rejection reason: chỉ hiện khi Rejected
	frm.toggle_display('rejection_reason', isRejected);

	// Version control section: chỉ hiện khi Archived
	frm.toggle_display(
		['superseded_by', 'archived_by_version', 'archive_date'],
		isArchived
	);

	// Readonly khi không còn Draft
	const isEditable = isDraft || isRejected;
	frm.toggle_enable(['doc_category', 'doc_type_detail', 'doc_number',
		'version', 'issued_date', 'expiry_date', 'issuing_authority',
		'file_attachment', 'is_exempt', 'visibility'], isEditable);

	// Exempt section: chỉ hiện khi is_exempt = 1
	_toggle_exempt_section(frm);

	// change_summary: required nếu version != "1.0"
	_toggle_change_summary_required(frm);

	// Indicators badge
	if (isExpired) {
		frm.dashboard.add_indicator(__('Đã hết hạn'), 'red');
	} else if (state === 'Pending_Review') {
		frm.dashboard.add_indicator(__('Chờ duyệt'), 'orange');
	} else if (isActive) {
		frm.dashboard.add_indicator(__('Đang hiệu lực'), 'green');
	}
}

function _toggle_exempt_section(frm) {
	const isExempt = frm.doc.is_exempt;
	frm.toggle_display('section_exempt', true);
	frm.toggle_display(['exempt_reason', 'exempt_proof'], isExempt);
	frm.set_df_property('exempt_reason', 'reqd', isExempt ? 1 : 0);
	frm.set_df_property('exempt_proof', 'reqd', isExempt ? 1 : 0);
}

function _toggle_expiry_required(frm) {
	const cat = frm.doc.doc_category;
	const required = cat === 'Legal' || cat === 'Certification';
	frm.set_df_property('expiry_date', 'reqd', required ? 1 : 0);
}

function _toggle_authority_required(frm) {
	const required = frm.doc.doc_category === 'Legal';
	frm.set_df_property('issuing_authority', 'reqd', required ? 1 : 0);
}

function _toggle_change_summary_required(frm) {
	const needsSummary = frm.doc.version && frm.doc.version !== '1.0';
	frm.set_df_property('change_summary', 'reqd', needsSummary ? 1 : 0);
	if (needsSummary) {
		frm.set_df_property('change_summary', 'description',
			'⚠️ Bắt buộc — Tóm tắt các thay đổi so với phiên bản trước.');
	}
}

function _add_custom_buttons(frm) {
	if (frm.is_new()) return;

	// Nút Tạo Document Request
	if (frm.doc.workflow_state === 'Draft') {
		frm.add_custom_button(__('Tạo Yêu cầu Tài liệu'), () => {
			frappe.new_doc('Document Request', {
				asset_ref: frm.doc.asset_ref,
				doc_type_required: frm.doc.doc_type_detail,
				doc_category: frm.doc.doc_category,
				source_type: 'Dashboard',
			});
		}, __('Hành động'));
	}

	// Nút xem lịch sử
	frm.add_custom_button(__('Lịch sử thay đổi'), () => {
		frappe.call({
			method: 'assetcore.api.imm05.get_document_history',
			args: { name: frm.doc.name },
			callback(r) {
				if (!r.exc && r.message?.data?.history) {
					_show_history_dialog(r.message.data.history);
				}
			}
		});
	});
}

function _show_history_dialog(history) {
	const rows = history.map(h =>
		`<tr>
			<td>${h.timestamp}</td>
			<td>${h.user}</td>
			<td>${h.action}</td>
			<td>${h.from_state || '—'} → ${h.to_state || '—'}</td>
		</tr>`
	).join('');
	frappe.msgprint({
		title: __('Lịch sử thay đổi'),
		indicator: 'blue',
		message: `<table class="table table-bordered table-sm">
			<thead><tr>
				<th>Thời gian</th><th>Người dùng</th><th>Hành động</th><th>Trạng thái</th>
			</tr></thead>
			<tbody>${rows || '<tr><td colspan="4">Chưa có lịch sử</td></tr>'}</tbody>
		</table>`,
	});
}
