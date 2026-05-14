// Copyright (c) 2026, AssetCore Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset QA Non Conformance", {

	refresh(frm) {
		_render_nc_status_indicator(frm);
		_update_nc_field_visibility(frm);
		_add_nc_action_buttons(frm);
	},

	nc_type(frm) {
		_update_nc_field_visibility(frm);

		if (frm.doc.nc_type === "DOA") {
			frappe.show_alert({
				message: __("Sự cố DOA: Bắt buộc đính kèm ảnh bằng chứng hỏng hóc!"),
				indicator: "red"
			}, 10);
		}
	},

	resolution_status(frm) {
		_update_nc_field_visibility(frm);
		_render_nc_status_indicator(frm);

		if (frm.doc.resolution_status === "Fixed") {
			frappe.show_alert({
				message: __("Vui lòng ghi rõ Cách khắc phục trong ô Ghi chú."),
				indicator: "blue"
			}, 6);
		}

		if (frm.doc.resolution_status === "Return") {
			frappe.msgprint({
				title: __("Xác nhận Trả hàng"),
				message: __("Trả thiết bị về Vendor sẽ đóng phiếu NC này và "
					+ "kích hoạt quy trình Return_To_Vendor trên phiếu Commissioning. "
					+ "Xác nhận?"),
				indicator: "orange",
				primary_action: {
					label: __("Xác nhận"),
					action() { frappe.hide_msgprint(); }
				}
			});
		}
	},

	ref_commissioning(frm) {
		if (frm.doc.ref_commissioning) {
			// Lấy thông tin từ phiếu commissioning để hiển thị thêm context
			frappe.db.get_value("Asset Commissioning",
				frm.doc.ref_commissioning,
				["master_item", "vendor", "vendor_serial_no", "clinical_dept"],
				(r) => {
					if (r) {
						frm.set_intro(
							__("<b>Thiết bị:</b> {0} | <b>Serial:</b> {1} | <b>Khoa:</b> {2}",
								[r.master_item, r.vendor_serial_no || "—", r.clinical_dept]),
							"blue"
						);
					}
				}
			);
		}
	}
});

// ──────────────────────────────────────────────
// HELPERS
// ──────────────────────────────────────────────

function _update_nc_field_visibility(frm) {
	// damage_proof — bắt buộc khi DOA
	frm.set_df_property("damage_proof", "reqd",
		frm.doc.nc_type === "DOA" ? 1 : 0);

	// resolution_note — chỉ show & bắt buộc khi Fixed
	frm.toggle_display("resolution_note", frm.doc.resolution_status === "Fixed");
	frm.set_df_property("resolution_note", "reqd",
		frm.doc.resolution_status === "Fixed" ? 1 : 0);

	// penalty_amount — read-only khi submitted
	if (frm.doc.docstatus === 1) {
		frm.set_df_property("penalty_amount", "read_only", 1);
	}
}

function _render_nc_status_indicator(frm) {
	const status_map = {
		"Open":   { label: "Chưa xử lý", color: "red" },
		"Fixed":  { label: "Đã sửa",     color: "green" },
		"Return": { label: "Trả hãng",   color: "darkgrey" }
	};
	const entry = status_map[frm.doc.resolution_status] || { label: "—", color: "gray" };
	frm.page.set_indicator(__(entry.label), entry.color);
}

function _add_nc_action_buttons(frm) {
	if (frm.doc.__islocal) return;

	// Nút quay về phiếu Commissioning
	if (frm.doc.ref_commissioning) {
		frm.add_custom_button(__("Xem Phiếu Commissioning"), function() {
			frappe.set_route("Form", "Asset Commissioning", frm.doc.ref_commissioning);
		}, __("Liên kết"));
	}

	// Nút đánh dấu Fixed nhanh (chỉ khi Open và chưa Submit)
	if (frm.doc.resolution_status === "Open" && frm.doc.docstatus === 0) {
		frm.add_custom_button(__("Đánh dấu Đã Sửa"), function() {
			frappe.prompt(
				{
					fieldtype: "Text",
					fieldname: "fix_note",
					label: __("Mô tả cách khắc phục"),
					reqd: 1
				},
				function(values) {
					frappe.model.set_value(frm.doctype, frm.docname,
						"resolution_status", "Fixed");
					frappe.model.set_value(frm.doctype, frm.docname,
						"resolution_note", values.fix_note);
					frm.save();
				},
				__("Xác nhận Khắc phục")
			);
		}, __("Hành động"));
	}
}
