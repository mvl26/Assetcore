"""Create IMM-03 Vendor Evaluations and Procurement Decisions for all 3 Tech Specs."""
import json
import frappe
from frappe.model.workflow import apply_workflow

DT_VE = "IMM Vendor Evaluation"
DT_PD = "IMM Procurement Decision"

# Supplier IDs from DB
SUP_DRAGER   = "AC-SUP-2026-0017"  # Cty TNHH Drager Medical Vietnam
SUP_BINHMINH = "AC-SUP-2026-0018"  # Cty CP Thiet bi Y te Binh Minh
SUP_MEDITR   = "AC-SUP-2026-0021"  # Meditronic Vietnam Co. Ltd

EVAL_DATA = [
    {
        "spec_ref": "TS-26-00007",  # Monitor bệnh nhân Mindray BeneView T9
        "candidates": [SUP_DRAGER, SUP_BINHMINH, SUP_MEDITR],
        "quotations": [
            {"candidate_supplier": SUP_DRAGER, "quotation_no": "QT-DR-2026-031",
             "quotation_date": "2026-03-10", "quotation_validity": "2026-06-10",
             "price": 325000000, "currency": "VND", "delivery_days": 60,
             "warranty_months": 24, "payment_terms": "30% tạm ứng, 70% sau nghiệm thu"},
            {"candidate_supplier": SUP_BINHMINH, "quotation_no": "QT-BM-2026-018",
             "quotation_date": "2026-03-11", "quotation_validity": "2026-06-11",
             "price": 298000000, "currency": "VND", "delivery_days": 45,
             "warranty_months": 18, "payment_terms": "50% tạm ứng, 50% khi giao hàng"},
            {"candidate_supplier": SUP_MEDITR, "quotation_no": "QT-MT-2026-007",
             "quotation_date": "2026-03-12", "quotation_validity": "2026-06-12",
             "price": 315000000, "currency": "VND", "delivery_days": 55,
             "warranty_months": 24, "payment_terms": "30% tạm ứng, 70% sau lắp đặt"},
        ],
        "winner": SUP_BINHMINH,
        "awarded_price": 298000000,
        "funding_source": "NSNN",
    },
    {
        "spec_ref": "TS-26-00008",  # Máy siêu âm Philips EPIQ 7
        "candidates": [SUP_DRAGER, SUP_BINHMINH, SUP_MEDITR],
        "quotations": [
            {"candidate_supplier": SUP_DRAGER, "quotation_no": "QT-DR-2026-032",
             "quotation_date": "2026-03-10", "quotation_validity": "2026-06-10",
             "price": 1920000000, "currency": "VND", "delivery_days": 90,
             "warranty_months": 24, "payment_terms": "30% tạm ứng, 70% sau nghiệm thu"},
            {"candidate_supplier": SUP_BINHMINH, "quotation_no": "QT-BM-2026-019",
             "quotation_date": "2026-03-11", "quotation_validity": "2026-06-11",
             "price": 1850000000, "currency": "VND", "delivery_days": 75,
             "warranty_months": 24, "payment_terms": "30% tạm ứng, 40% khi giao, 30% nghiệm thu"},
            {"candidate_supplier": SUP_MEDITR, "quotation_no": "QT-MT-2026-008",
             "quotation_date": "2026-03-12", "quotation_validity": "2026-06-12",
             "price": 1900000000, "currency": "VND", "delivery_days": 80,
             "warranty_months": 36, "payment_terms": "20% tạm ứng, 80% sau lắp đặt và nghiệm thu"},
        ],
        "winner": SUP_BINHMINH,
        "awarded_price": 1850000000,
        "funding_source": "Xã hội hóa",
        "procurement_method": "Đấu thầu rộng rãi",
    },
    {
        "spec_ref": "TS-26-00009",  # Máy thở Dräger Evita V500
        "candidates": [SUP_DRAGER, SUP_BINHMINH, SUP_MEDITR],
        "quotations": [
            {"candidate_supplier": SUP_DRAGER, "quotation_no": "QT-DR-2026-033",
             "quotation_date": "2026-03-10", "quotation_validity": "2026-06-10",
             "price": 985000000, "currency": "VND", "delivery_days": 84,
             "warranty_months": 24, "payment_terms": "30% tạm ứng, 70% sau nghiệm thu"},
            {"candidate_supplier": SUP_BINHMINH, "quotation_no": "QT-BM-2026-020",
             "quotation_date": "2026-03-11", "quotation_validity": "2026-06-11",
             "price": 1020000000, "currency": "VND", "delivery_days": 70,
             "warranty_months": 24, "payment_terms": "30% tạm ứng, 70% khi giao hàng"},
            {"candidate_supplier": SUP_MEDITR, "quotation_no": "QT-MT-2026-009",
             "quotation_date": "2026-03-12", "quotation_validity": "2026-06-12",
             "price": 970000000, "currency": "VND", "delivery_days": 90,
             "warranty_months": 36, "payment_terms": "20% tạm ứng, 80% sau lắp đặt"},
        ],
        "winner": SUP_MEDITR,
        "awarded_price": 970000000,
        "funding_source": "NSNN",
    },
]

CRITERIA = [
    {"group": "Technical", "criterion": "Đáp ứng yêu cầu kỹ thuật theo spec đã duyệt",
     "weight_pct": 40, "scorer_role": "IMM HTM Engineer",
     "description": "So sánh thông số kỹ thuật thực tế vs Tech Spec (TS đã Locked)"},
    {"group": "Commercial", "criterion": "Giá chào thầu và tổng chi phí vòng đời 5 năm (TCO)",
     "weight_pct": 30, "scorer_role": "IMM Finance Officer",
     "description": "Bao gồm giá thiết bị, phụ kiện, đào tạo, bảo trì hàng năm"},
    {"group": "Support", "criterion": "Năng lực hỗ trợ kỹ thuật và SLA dịch vụ tại Việt Nam",
     "weight_pct": 20, "scorer_role": "IMM HTM Engineer",
     "description": "Phản ứng sự cố, kho phụ tùng, số lượng kỹ thuật viên được đào tạo"},
    {"group": "Compliance", "criterion": "Giấy phép lưu hành, chứng nhận ISO, đăng ký UDI",
     "weight_pct": 10, "scorer_role": "IMM Risk Officer",
     "description": "Kiểm tra giấy phép Bộ Y tế, ISO 13485, chứng nhận CE/FDA"},
]

SCORES = {
    "Technical": {SUP_DRAGER: 85, SUP_BINHMINH: 88, SUP_MEDITR: 82},
    "Commercial": {SUP_DRAGER: 78, SUP_BINHMINH: 92, SUP_MEDITR: 80},
    "Support": {SUP_DRAGER: 90, SUP_BINHMINH: 85, SUP_MEDITR: 88},
    "Compliance": {SUP_DRAGER: 95, SUP_BINHMINH: 90, SUP_MEDITR: 92},
}


def run():
    frappe.set_user("Administrator")
    created_ves = []
    created_pds = []

    from assetcore.api.imm03 import _create_decision, _award_decision, _record_contract as _rc

    existing_ve_map = {
        ve["spec_ref"]: ve["name"]
        for ve in frappe.db.sql(
            "SELECT name, spec_ref FROM `tabIMM Vendor Evaluation`", as_dict=True
        )
    }
    existing_pd_map = {
        pd["spec_ref"]: pd["name"]
        for pd in frappe.db.sql(
            "SELECT name, spec_ref FROM `tabIMM Procurement Decision`", as_dict=True
        )
    }

    for data in EVAL_DATA:
        spec_ref = data["spec_ref"]
        print(f"\n=== {spec_ref} ===")

        # --- Create or reuse Vendor Evaluation ---
        if spec_ref in existing_ve_map:
            ve_name = existing_ve_map[spec_ref]
            print(f"  VE exists: {ve_name}")
        else:
            ve = frappe.new_doc(DT_VE)
            ve.spec_ref = spec_ref
            ve.weighting_scheme = json.dumps({"Technical": 40, "Commercial": 30, "Support": 20, "Compliance": 10})
            for c in CRITERIA:
                ve.append("criteria", c)
            for sup in data["candidates"]:
                ve.append("candidates", {"supplier": sup, "in_avl": 0})
            ve.insert(ignore_permissions=True)
            frappe.db.commit()
            ve_name = ve.name
            print(f"  VE created: {ve_name}")
            created_ves.append(ve_name)

            ve = frappe.get_doc(DT_VE, ve_name)
            for q in data["quotations"]:
                ve.append("quotations", q)
            ve.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"  Quotations added: {len(ve.quotations)}")

            ve = frappe.get_doc(DT_VE, ve_name)
            for cand in ve.candidates:
                sup_scores = {}
                for crit_row in ve.criteria:
                    group = crit_row.group
                    if group in SCORES:
                        sup_scores[crit_row.criterion] = SCORES[group].get(cand.supplier, 80)
                cand.scores = json.dumps(sup_scores)
            ve.save(ignore_permissions=True)
            frappe.db.commit()
            print("  Scores saved")

            ve = frappe.get_doc(DT_VE, ve_name)
            for action in ["Mở RFQ", "Nhận báo giá xong", "Hoàn tất chấm điểm"]:
                apply_workflow(ve, action)
                frappe.db.commit()
                ve = frappe.get_doc(DT_VE, ve_name)
                print(f"  → {ve.workflow_state}")

        # --- Create or reuse Procurement Decision ---
        if spec_ref in existing_pd_map:
            pd_name = existing_pd_map[spec_ref]
            print(f"  PD exists: {pd_name}")
        else:
            method = data.get("procurement_method", "Chào hàng cạnh tranh")
            pd_result = _create_decision(ve_name, method,
                                          "Nghị định 24/2024/NĐ-CP về mua sắm tài sản công")
            frappe.db.commit()
            pd_name = pd_result["name"]
            print(f"  PD created: {pd_name}")
            created_pds.append(pd_name)

        pd = frappe.get_doc(DT_PD, pd_name)
        if pd.workflow_state == "Draft":
            for action in ["Chọn phương án", "Bắt đầu thương thảo", "Đề xuất trúng thầu", "Trình BGĐ"]:
                apply_workflow(pd, action)
                frappe.db.commit()
                pd = frappe.get_doc(DT_PD, pd_name)
                print(f"  PD → {pd.workflow_state}")

        if pd.workflow_state == "Pending Approval":
            contract_doc_ref = f"/files/hop-dong-{pd_name}.pdf"
            _award_decision(
                pd_name, data["winner"], data["awarded_price"],
                data["funding_source"], "Administrator", contract_doc_ref,
                "Hội đồng tư vấn mua sắm nhất trí thống nhất lựa chọn nhà thầu.",
            )
            frappe.db.commit()
            pd = frappe.get_doc(DT_PD, pd_name)
            print(f"  PD Awarded → state={pd.workflow_state} docstatus={pd.docstatus}")

        # --- Record Contract ---
        pd = frappe.get_doc(DT_PD, pd_name)
        if pd.workflow_state == "Awarded":
            from assetcore.api.imm03 import _record_contract
            contract_no = f"HĐ-TTYT-2026-{pd_name[-3:]}"
            _record_contract(pd_name, contract_no, "", "2026-04-01")
            frappe.db.commit()
            pd = frappe.get_doc(DT_PD, pd_name)
            print(f"  PD Contract Signed → state={pd.workflow_state}")
        else:
            print(f"  PD already at: {pd.workflow_state}")

    # Summary
    print("\n=== SUMMARY ===")
    print(f"Vendor Evaluations ({len(created_ves)}): {created_ves}")
    print(f"Procurement Decisions ({len(created_pds)}): {created_pds}")
    print("Done.")
