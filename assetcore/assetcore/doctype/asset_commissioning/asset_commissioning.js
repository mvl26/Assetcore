// Copyright (c) 2026, AssetCore Team and contributors
// For license information, please see license.txt

// ──────────────────────────────────────────────
// STATE HELPERS (scoped, không pollute prototype)
// ──────────────────────────────────────────────

const IMM04_STATES = {
	DRAFT:           "Draft_Reception",
	DOC_VERIFY:      "Pending_Doc_Verify",
	TO_INSTALL:      "To_Be_Installed",
	INSTALLING:      "Installing",
	IDENTIFY:        "Identification",
	INSPECT:         "Initial_Inspection",
	NC:              "Non_Conformance",
	HOLD:            "Clinical_Hold",
	REINSPECT:       "Re_Inspection",
	RELEASE:         "Clinical_Release",
	RETURN:          "Return_To_Vendor"
};

function _update_field_visibility(frm) {
	const s = frm.doc.workflow_state;

	// Section Identification — chỉ show từ bước nhận dạng trở đi
	const show_id = [IMM04_STATES.IDENTIFY, IMM04_STATES.INSPECT,
		IMM04_STATES.REINSPECT, IMM04_STATES.HOLD,
		IMM04_STATES.RELEASE, IMM04_STATES.NC].includes(s);
	frm.toggle_display("section_identification", show_id);

	// Tab Baseline — show khi đang kiểm tra và sau
	const show_baseline = [IMM04_STATES.INSPECT, IMM04_STATES.REINSPECT,
		IMM04_STATES.HOLD, IMM04_STATES.RELEASE].includes(s);
	frm.toggle_display("tab_baseline", show_baseline);

	// Tab Documents — show từ Doc Verify trở đi
	const show_docs = [IMM04_STATES.DOC_VERIFY, IMM04_STATES.TO_INSTALL,
		IMM04_STATES.INSTALLING, IMM04_STATES.IDENTIFY, IMM04_STATES.INSPECT,
		IMM04_STATES.REINSPECT, IMM04_STATES.HOLD, IMM04_STATES.RELEASE].includes(s);
	frm.toggle_display("tab_documents", show_docs);

	// Section QA — show từ Identification trở đi
	const show_qa = [IMM04_STATES.IDENTIFY, IMM04_STATES.INSPECT,
		IMM04_STATES.REINSPECT, IMM04_STATES.HOLD, IMM04_STATES.RELEASE].includes(s);
	frm.toggle_display("section_qa", show_qa);

	// Lock thông tin lắp đặt sau khi qua Installing
	const lock_install = [IMM04_STATES.IDENTIFY, IMM04_STATES.INSPECT,
		IMM04_STATES.REINSPECT, IMM04_STATES.HOLD, IMM04_STATES.RELEASE].includes(s);
	frm.set_df_property("installation_date", "read_only", lock_install ? 1 : 0);
	frm.set_df_property("vendor_engineer_name", "read_only", lock_install ? 1 : 0);

	// Các trường luôn read-only
	frm.set_df_property("final_asset", "read_only", 1);
	frm.set_df_property("is_radiation_device", "read_only", 1);
	frm.set_df_property("internal_tag_qr", "read_only", 1);
}

function _setup_barcode_hint(frm) {
	if (frm.doc.workflow_state === IMM04_STATES.IDENTIFY) {
		frm.set_df_property("vendor_serial_no", "description",
			"Vui lòng sử dụng Súng Barcode Scanner. Đặt con trỏ vào ô → Bấm trigger súng.");
	}
}

function _add_action_buttons(frm) {
	if (frm.doc.__islocal) return;

	// Nút DOA — chỉ khi đang Installing
	if (frm.doc.workflow_state === IMM04_STATES.INSTALLING) {
		frm.add_custom_button(__("Báo cáo Sự cố DOA"), function() {
			_open_doa_dialog(frm);
		}, __("Hành động"));
	}

	// Nút xem các NC liên quan — từ NC state trở đi
	const has_nc_states = [IMM04_STATES.NC, IMM04_STATES.REINSPECT,
		IMM04_STATES.HOLD, IMM04_STATES.RELEASE];
	if (has_nc_states.includes(frm.doc.workflow_state)) {
		frm.add_custom_button(__("Xem Phiếu NC"), function() {
			frappe.set_route("List", "Asset QA Non Conformance", {
				ref_commissioning: frm.doc.name
			});
		}, __("Liên kết"));
	}

	// Nút xem Asset đã tạo — sau khi Release
	if (frm.doc.final_asset) {
		frm.add_custom_button(__("Xem Tài sản"), function() {
			frappe.set_route("Form", "AC Asset", frm.doc.final_asset);
		}, __("Liên kết"));
	}
}

function _open_doa_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Tạo Phiếu Báo Lỗi DOA"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "nc_type",
				label: __("Loại sự cố"),
				options: "DOA\nMissing\nCrash",
				reqd: 1
			},
			{
				fieldtype: "Small Text",
				fieldname: "description",
				label: __("Mô tả sự cố"),
				reqd: 1
			},
			{
				fieldtype: "Attach Image",
				fieldname: "damage_photo",
				label: __("Ảnh bằng chứng (Bắt buộc với DOA)")
			}
		],
		primary_action_label: __("Tạo Phiếu NC"),
		primary_action(values) {
			if (values.nc_type === "DOA" && !values.damage_photo) {
				frappe.msgprint({
					message: __("Sự cố DOA bắt buộc đính kèm ảnh bằng chứng."),
					indicator: "red"
				});
				return;
			}
			frm.call("create_nc_from_form", {
				nc_type: values.nc_type,
				description: values.description,
				damage_photo: values.damage_photo || ""
			}).then(r => {
				d.hide();
				frappe.show_alert({
					message: __("Phiếu NC {0} đã được tạo.", [r.message]),
					indicator: "orange"
				}, 8);
				frm.reload_doc();
			});
		}
	});
	d.show();
}

function _render_state_badge(frm) {
	// Hiển thị badge trạng thái màu sắc rõ ràng trên form header
	const state_colors = {
		[IMM04_STATES.DRAFT]:      "gray",
		[IMM04_STATES.DOC_VERIFY]: "blue",
		[IMM04_STATES.TO_INSTALL]: "blue",
		[IMM04_STATES.INSTALLING]: "yellow",
		[IMM04_STATES.IDENTIFY]:   "yellow",
		[IMM04_STATES.INSPECT]:    "orange",
		[IMM04_STATES.NC]:         "red",
		[IMM04_STATES.HOLD]:       "red",
		[IMM04_STATES.REINSPECT]:  "orange",
		[IMM04_STATES.RELEASE]:    "green",
		[IMM04_STATES.RETURN]:     "darkgrey"
	};
	const state = frm.doc.workflow_state;
	const color = state_colors[state] || "gray";

	// Set indicator màu trên form header
	frm.page.set_indicator(state ? __(state.replace(/_/g, " ")) : "", color);
}

// ──────────────────────────────────────────────
// MAIN FORM HANDLER
// ──────────────────────────────────────────────

frappe.ui.form.on("Asset Commissioning", {

	refresh(frm) {
		_update_field_visibility(frm);
		_setup_barcode_hint(frm);
		_add_action_buttons(frm);
		_render_state_badge(frm);
		_setup_doc_table_defaults(frm);
	},

	workflow_state(frm) {
		_update_field_visibility(frm);
		_render_state_badge(frm);
	},

	// VR-05: Soft warning thiếu Manual HDSD
	after_save(frm) {
		const has_manual = (frm.doc.commissioning_documents || []).some(
			row => row.doc_type === "Manual / HDSD" && row.status === "Received"
		);
		if (!has_manual && frm.doc.workflow_state === IMM04_STATES.DOC_VERIFY) {
			frappe.show_alert({
				message: __("Cảnh báo: Chưa nhận được Sách hướng dẫn (Manual / HDSD). "
					+ "Yêu cầu Vendor bổ sung trước giai đoạn Đào tạo."),
				indicator: "orange"
			}, 10);
		}
	},

	// VR-08: Cảnh báo barcode scanner
	vendor_serial_no(frm) {
		const sn = frm.doc.vendor_serial_no || "";
		if (sn.length > 0 && sn.length < 4) {
			frappe.show_alert({
				message: __("Cảnh báo: Serial quá ngắn. Dùng Súng Barcode Scanner thay vì nhập tay!"),
				indicator: "orange"
			}, 8);
		}
	},

	// Bức xạ → bắt buộc giấy phép
	is_radiation_device(frm) {
		if (frm.doc.is_radiation_device) {
			frappe.show_alert({
				message: __("Thiết bị có bức xạ. Bắt buộc upload Giấy phép Cục ATBXHN trước khi Phát hành."),
				indicator: "red"
			}, 12);
		}
		frm.set_df_property("qa_license_doc", "reqd", frm.doc.is_radiation_device ? 1 : 0);
	},

	// Auto-fill bảng hồ sơ chuẩn khi PO được chọn
	po_reference(frm) {
		if (frm.doc.po_reference && !frm.doc.commissioning_documents?.length) {
			_setup_doc_table_defaults(frm);
		}
	}
});

// ──────────────────────────────────────────────
// CHILD TABLE: Commissioning Checklist
// ──────────────────────────────────────────────

frappe.ui.form.on("Commissioning Checklist", {
	test_result(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.idx) return;

		const grid_row = frm.fields_dict["baseline_tests"].grid.grid_rows[row.idx - 1];
		if (!grid_row) return;

		if (row.test_result === "Fail") {
			frappe.show_alert({
				message: __("Dòng {0} — '{1}': Không Đạt. Bắt buộc điền Ghi chú Nguyên nhân!",
					[row.idx, row.parameter]),
				indicator: "red"
			}, 8);
			$(grid_row.row).css("background-color", "#FFEBEE");
		} else if (row.test_result === "Pass") {
			$(grid_row.row).css("background-color", "#E8F5E9");
		} else {
			$(grid_row.row).css("background-color", "");
		}
	}
});

// ──────────────────────────────────────────────
// CHILD TABLE: Commissioning Document Record
// ──────────────────────────────────────────────

frappe.ui.form.on("Commissioning Document Record", {
	status(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.idx) return;

		const grid_row = frm.fields_dict["commissioning_documents"].grid.grid_rows[row.idx - 1];
		if (!grid_row) return;

		if (row.status === "Missing") {
			$(grid_row.row).css("background-color", "#FFEBEE");
		} else if (row.status === "Received") {
			$(grid_row.row).css("background-color", "#E8F5E9");
		} else {
			$(grid_row.row).css("background-color", "#FFF9C4");
		}
	}
});

// ──────────────────────────────────────────────
// HELPER: Pre-fill bảng hồ sơ chuẩn
// ──────────────────────────────────────────────

function _setup_doc_table_defaults(frm) {
	// Chỉ fill khi bảng đang trống và form chưa submitted
	if (frm.doc.docstatus !== 0) return;
	if ((frm.doc.commissioning_documents || []).length > 0) return;

	const standard_docs = [
		"CO - Chứng nhận Xuất xứ",
		"CQ - Chứng nhận Chất lượng",
		"Packing List",
		"Manual / HDSD",
		"Warranty Card"
	];

	standard_docs.forEach(doc_type => {
		const row = frm.add_child("commissioning_documents");
		row.doc_type = doc_type;
		row.status = "Pending";
	});

	frm.refresh_field("commissioning_documents");
}
