"""Complete IMM-02 workflow for all 3 Tech Specs through to Locked state."""
import frappe
from frappe.model.workflow import apply_workflow


SPECS = ["TS-26-00007", "TS-26-00008", "TS-26-00009"]

INFRA_ROWS = [
    {"domain": "Electrical", "compatibility_status": "Compatible",
     "remark": "Nguồn điện 220V ổn định, có UPS dự phòng tại vị trí lắp đặt"},
    {"domain": "Medical Gas", "compatibility_status": "Compatible",
     "remark": "Hệ thống khí y tế (O2, khí nén) đạt áp suất yêu cầu theo ISO 7396"},
    {"domain": "Network/IT", "compatibility_status": "Compatible",
     "remark": "Mạng LAN Cat6 đã kéo sẵn, VLAN thiết bị y tế tách biệt VLAN admin"},
    {"domain": "HIS-PACS-LIS", "compatibility_status": "Need Upgrade",
     "remark": "Cần cấu hình thêm HL7 listener trên HIS để nhận dữ liệu thiết bị mới"},
    {"domain": "HVAC", "compatibility_status": "Compatible",
     "remark": "Nhiệt độ phòng duy trì 20-25°C, độ ẩm 45-65% — đạt yêu cầu IEC 60601"},
    {"domain": "Space-Layout", "compatibility_status": "Compatible",
     "remark": "Diện tích lắp đặt đủ 4m², lối đi vận chuyển ≥ 1.2m"},
]

LOCK_IN_ITEMS = [
    {"criterion": "Protocol Standard", "score": 1,
     "rationale": "Thiết bị hỗ trợ chuẩn mở HL7/DICOM, không bị khóa giao thức độc quyền"},
    {"criterion": "Consumable Source", "score": 2,
     "rationale": "Vật tư tiêu hao có thể mua từ ≥ 2 nhà cung cấp thay thế trên thị trường VN"},
    {"criterion": "Software License", "score": 2,
     "rationale": "License phần mềm theo thiết bị, phí gia hạn hàng năm ở mức chấp nhận"},
    {"criterion": "Parts Source", "score": 2,
     "rationale": "Linh kiện thay thế có sẵn qua đại lý chính hãng tại Việt Nam"},
    {"criterion": "Service Tooling", "score": 1,
     "rationale": "Công cụ dịch vụ tiêu chuẩn, không yêu cầu thiết bị chuyên dụng đặc biệt"},
]


def run():
    frappe.set_user("Administrator")

    for spec_name in SPECS:
        doc = frappe.get_doc("IMM Tech Spec", spec_name)
        print(f"\n=== {spec_name} (state: {doc.workflow_state}) ===")

        # Step 1: Hoàn tất benchmark (Reviewing → Benchmarked)
        if doc.workflow_state == "Reviewing":
            apply_workflow(doc, "Hoàn tất benchmark")
            frappe.db.commit()
            doc = frappe.get_doc("IMM Tech Spec", spec_name)
            print(f"  → {doc.workflow_state}")

        # Step 2: Add infra_compat rows if missing
        if doc.workflow_state == "Benchmarked":
            existing_domains = {row.domain for row in (doc.infra_compat or [])}
            for row_data in INFRA_ROWS:
                if row_data["domain"] not in existing_domains:
                    doc.append("infra_compat", row_data)
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"  Infra compat: {len(doc.infra_compat)} rows")

        # Step 3: Create Lock-in Risk Assessment if not exists
        existing_lr = frappe.db.get_value("IMM Lock-in Risk Assessment", {"spec_ref": spec_name}, "name")
        if not existing_lr:
            lr = frappe.new_doc("IMM Lock-in Risk Assessment")
            lr.spec_ref = spec_name
            lr.threshold_used = 2.5
            lr.mitigation_plan = (
                "1. Ưu tiên lựa chọn nhà cung cấp có cam kết hỗ trợ ≥ 10 năm và có đại lý tại VN.\n"
                "2. Ký hợp đồng bảo trì có SLA rõ ràng, phụ tùng lưu kho tối thiểu 2 năm.\n"
                "3. Đào tạo kỹ thuật viên nội bộ đến mức có thể xử lý sự cố cấp 1."
            )
            lr.mitigation_evidence = "Hợp đồng bảo trì ký kết — lưu tại hồ sơ mua sắm thiết bị."
            for item in LOCK_IN_ITEMS:
                lr.append("items", item)
            lr.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"  Lock-in Risk: {lr.name} score={lr.lock_in_score}")

            # Link back to tech spec
            frappe.db.set_value("IMM Tech Spec", spec_name, {
                "lock_in_risk_ref": lr.name,
                "lock_in_score": lr.lock_in_score,
                "mitigation_plan": lr.mitigation_plan,
                "mitigation_evidence": lr.mitigation_evidence,
            })
            frappe.db.commit()
        else:
            print(f"  Lock-in Risk: {existing_lr} (exists)")
            lr_doc = frappe.get_doc("IMM Lock-in Risk Assessment", existing_lr)
            frappe.db.set_value("IMM Tech Spec", spec_name, {
                "lock_in_risk_ref": existing_lr,
                "lock_in_score": lr_doc.lock_in_score,
            })
            frappe.db.commit()

        # Step 4: Đánh giá rủi ro xong (Benchmarked → Risk Assessed)
        doc = frappe.get_doc("IMM Tech Spec", spec_name)
        if doc.workflow_state == "Benchmarked":
            apply_workflow(doc, "Đánh giá rủi ro xong")
            frappe.db.commit()
            doc = frappe.get_doc("IMM Tech Spec", spec_name)
            print(f"  → {doc.workflow_state}")

        # Step 5: Trình duyệt spec (Risk Assessed → Pending Approval)
        doc = frappe.get_doc("IMM Tech Spec", spec_name)
        if doc.workflow_state == "Risk Assessed":
            apply_workflow(doc, "Trình duyệt spec")
            frappe.db.commit()
            doc = frappe.get_doc("IMM Tech Spec", spec_name)
            print(f"  → {doc.workflow_state}")

        # Step 6: Phê duyệt spec (Pending Approval → Locked) via lock_spec
        doc = frappe.get_doc("IMM Tech Spec", spec_name)
        if doc.workflow_state == "Pending Approval":
            from assetcore.api.imm02 import _lock_spec
            result = _lock_spec(spec_name, "Administrator",
                                "Phê duyệt spec kỹ thuật sau rà soát đầy đủ hồ sơ benchmark và đánh giá rủi ro lock-in.")
            frappe.db.commit()
            print(f"  → Locked (docstatus={result.get('docstatus')})")

    # Final summary
    print("\n=== FINAL STATE ===")
    for spec_name in SPECS:
        doc = frappe.get_doc("IMM Tech Spec", spec_name)
        print(f"  {spec_name}: {doc.workflow_state} docstatus={doc.docstatus}")
    print("Done.")
