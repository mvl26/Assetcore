// Copyright (c) 2026, AssetCore Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Commissioning", {

	// ──────────────────────────────────────────────
	// FORM LOAD
	// ──────────────────────────────────────────────
	refresh(frm) {
		frm._update_field_visibility();
		frm._setup_barcode_fields();
		frm._add_action_buttons();
	},

	workflow_state(frm) {
		frm._update_field_visibility();
	},

	// ──────────────────────────────────────────────
	// VR-05: SOFT WARNING — Thiếu Manual HDSD
	// ──────────────────────────────────────────────
	after_save(frm) {
		// Kiểm tra xem trong commissioning_documents có Manual chưa
		let has_manual = (frm.doc.commissioning_documents || []).some(
			row => row.doc_type === "Manual / HDSD" && row.status === "Received"
		);

		if (!has_manual && frm.doc.workflow_state === "Pending_Doc_Verify") {
			frappe.show_alert({
				message: __("⚠️ Cảnh báo: Chưa nhận được Sách hướng dẫn sử dụng (Manual / HDSD). "
					+ "Vui lòng yêu cầu Vendor bổ sung trước giai đoạn Đào tạo."),
				indicator: "orange"
			}, 10);
		}
	},

	// ──────────────────────────────────────────────
	// VR-08: BARCODE SCANNER ENFORCE
	// ──────────────────────────────────────────────
	vendor_serial_no(frm) {
		// Kiểm tra không cho paste chuỗi quá dài (thường là do gõ tay)
		let sn = frm.doc.vendor_serial_no || "";
		if (sn.length > 0 && sn.length < 4) {
			frappe.show_alert({
				message: __("Cảnh báo: Serial Number có vẻ quá ngắn. Vui lòng sử dụng Súng Barcode Scanner thay vì nhập tay!"),
				indicator: "orange"
			}, 8);
		}
	},

	is_radiation_device(frm) {
		if (frm.doc.is_radiation_device) {
			frappe.show_alert({
				message: __("⚠️ Thiết bị này có bức xạ. Bắt buộc upload Giấy phép Cục ATBXHN trước khi Phát hành."),
				indicator: "red"
			}, 12);
			frm.set_df_property("qa_license_doc", "reqd", 1);
		} else {
			frm.set_df_property("qa_license_doc", "reqd", 0);
		}
	},
});

// ──────────────────────────────────────────────
// CHILD TABLE: Commissioning Checklist
// ──────────────────────────────────────────────
frappe.ui.form.on("Commissioning Checklist", {
	test_result(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.test_result === "Fail") {
			frappe.show_alert({
				message: __("Dòng {0} — '{1}': Kết quả Không Đạt. Bắt buộc điền Ghi chú Nguyên nhân!",
					[row.idx, row.parameter]),
				indicator: "red"
			}, 8);
			frappe.model.set_value(cdt, cdn, "fail_note", "");
			// Set màu đỏ cho dòng
			$(frm.fields_dict["baseline_tests"].grid.grid_rows[row.idx - 1].row)
				.css("background-color", "#FFEBEE");
		} else if (row.test_result === "Pass") {
			$(frm.fields_dict["baseline_tests"].grid.grid_rows[row.idx - 1].row)
				.css("background-color", "#E8F5E9");
		}
	}
});

// ──────────────────────────────────────────────
// INTERNAL HELPERS
// ──────────────────────────────────────────────
$.extend(frappe.ui.form.Form.prototype, {

	_update_field_visibility() {
		let frm = this;
		let state = frm.doc.workflow_state;

		// Section Identification — chỉ show khi đủ bước
		let show_identification = ["Identification", "Initial_Inspection",
			"Re_Inspection", "Clinical_Hold", "Clinical_Release"].includes(state);
		frm.toggle_display("section_identification", show_identification);

		// Tab Baseline — chỉ show khi vào giai đoạn test
		let show_baseline = ["Initial_Inspection", "Re_Inspection",
			"Clinical_Release", "Clinical_Hold"].includes(state);
		frm.toggle_display("tab_baseline", show_baseline);

		// Section Installation date — lock sau khi qua Installing
		let lock_install_info = ["Identification", "Initial_Inspection",
			"Re_Inspection", "Clinical_Release", "Clinical_Hold"].includes(state);
		frm.set_df_property("installation_date", "read_only", lock_install_info ? 1 : 0);
		frm.set_df_property("vendor_engineer_name", "read_only", lock_install_info ? 1 : 0);

		// final_asset — luôn read only
		frm.set_df_property("final_asset", "read_only", 1);
		frm.set_df_property("is_radiation_device", "read_only", 1);
	},

	_setup_barcode_fields() {
		let frm = this;
		// Override field vendor_serial_no để hiển thị hint barcode
		if (frm.doc.workflow_state === "Identification") {
			frm.set_df_property("vendor_serial_no", "description",
				"📷 Vui lòng sử dụng Súng Barcode Scanner. Đặt con trỏ vào ô → Bấm trigger súng.");
		}
	},

	_add_action_buttons() {
		let frm = this;

		// Nút Report DOA — hiển thị khi đang lắp đặt
		if (frm.doc.workflow_state === "Installing" && !frm.doc.__islocal) {
			frm.add_custom_button(__("🚨 Báo cáo Sự cố DOA"), function() {
				frappe.prompt([
					{
						fieldtype: "Select",
						fieldname: "nc_type",
						label: "Loại sự cố",
						options: "DOA\nMissing\nCrash",
						reqd: 1
					},
					{
						fieldtype: "Small Text",
						fieldname: "description",
						label: "Mô tả sự cố",
						reqd: 1
					}
				], function(values) {
					frm.call("create_nc_from_form", {
						nc_type: values.nc_type,
						description: values.description
					}).then(r => {
						frappe.show_alert({
							message: __("Phiếu NC {0} đã được tạo.", [r.message]),
							indicator: "orange"
						});
						frm.reload_doc();
					});
				}, __("Tạo Phiếu Báo Lỗi"), __("Xác nhận"));
			}, __("Hành động"));
		}
	}
});
