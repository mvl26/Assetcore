"""Seed realistic data for IMM-04, IMM-05, IMM-06.

Run: bench --site miyano execute assetcore.scripts.seed.seed_imm_456.run
"""
from __future__ import annotations

import frappe
from frappe.utils import add_days, add_months, nowdate, getdate


REAL_DATA = {
    "vendors": ["AC-SUP-2026-0017", "AC-SUP-2026-0018", "AC-SUP-2026-0021"],
    "models": ["IMM-MDL-2026-0023", "IMM-MDL-2026-0024", "IMM-MDL-2026-0026"],
    "depts": ["Khoa-HSTC", "Khoa-CDHA", "Phong-Mo-2"],
    "locations": ["AC-LOC-2026-0127", "AC-LOC-2026-0129", "AC-LOC-2026-0128"],
    "asset_names": [
        "Máy thở Dräger Evita V500 – Khoa Hồi sức tích cực",
        "Monitor bệnh nhân Mindray BeneView T9 – Phòng Mổ 2",
        "Máy siêu âm Philips EPIQ 7 – Khoa Chẩn đoán Hình ảnh",
    ],
    "users": ["chuvanhieu357@gmail.com", "snonamevx@gmail.com", "sohaidiuuu@gmail.com"],
}


# The 3 genuine demo assets. NEVER pick "newest 3" (order_by creation desc) —
# when the DB is polluted with leaked test assets that selects garbage as "real".
# Pin by their stable business codes so the seed is reproducible + leak-proof.
REAL_ASSET_CODES = ("TS-2025-USG-001", "TS-2025-VEN-001", "TS-2025-CT-001")


def _ensure_assets() -> list[str]:
    """Resolve the 3 genuine demo AC Asset records by their fixed business codes.

    Deterministic + leak-proof: filters on the canonical ``TS-2025-%`` codes
    instead of ``order_by creation desc`` (which would pick freshly-leaked test
    assets when the site is polluted). Returns them in REAL_ASSET_CODES order so
    downstream scenario indexes stay stable.
    """
    found = {
        a["name"]: a
        for a in frappe.get_all(
            "AC Asset",
            filters={"name": ["in", list(REAL_ASSET_CODES)]},
            fields=["name", "asset_name", "department", "device_model", "supplier", "location"],
            ignore_permissions=True,
        )
    }
    missing = [c for c in REAL_ASSET_CODES if c not in found]
    if missing:
        raise RuntimeError(
            f"Genuine demo assets missing: {missing}. Expected {REAL_ASSET_CODES} "
            "to exist before seeding IMM-04/05/06."
        )
    ordered = [found[c] for c in REAL_ASSET_CODES]
    print(f"  Using {len(ordered)} genuine demo AC Assets:")
    for a in ordered:
        print(f"    - {a['name']} | {a['asset_name']}")
    return [a["name"] for a in ordered]


def seed_imm04(asset_names: list[str]) -> list[str]:
    """Create 3 Asset Commissioning (acceptance) records."""
    print("\n=== IMM-04: Asset Commissioning ===")
    out: list[str] = []
    purchases = [p["name"] for p in frappe.get_all("AC Purchase", limit=3, order_by="creation desc", ignore_permissions=True)]
    if len(purchases) < 3:
        raise RuntimeError(f"Need >=3 AC Purchase records, found {len(purchases)}")
    scenarios = [
        {
            "asset_idx": 0,
            "po_reference": purchases[0],
            "delivery_note_no": "DN-DRG-2026-04-22",
            "purchase_price": 1_850_000_000,
            "vendor_engineer_name": "KS. Hoàng Văn Tâm — Dräger Medical Vietnam",
            "asset_description": "Máy thở Dräger Evita V500 cấu hình ICU đầy đủ — model năm 2023, kèm bộ làm ẩm và 2 trolley vận chuyển.",
            "warranty_months": 24,
            "is_radiation_device": 0,
            "risk_class": "Class IIb",
        },
        {
            "asset_idx": 1,
            "po_reference": purchases[1],
            "delivery_note_no": "DN-MNR-2026-04-25",
            "purchase_price": 685_000_000,
            "vendor_engineer_name": "KS. Lê Trung Hiếu — Mindray Vietnam",
            "asset_description": "Monitor bệnh nhân Mindray BeneView T9, 12.1 inch, module ECG/SpO2/NIBP/IBP/EtCO2, kèm trolley và pin dự phòng.",
            "warranty_months": 36,
            "is_radiation_device": 0,
            "risk_class": "Class IIa",
        },
        {
            "asset_idx": 2,
            "po_reference": purchases[2],
            "delivery_note_no": "DN-PHL-2026-04-30",
            "purchase_price": 3_120_000_000,
            "vendor_engineer_name": "KS. Trần Quốc Việt — Philips Healthcare Vietnam",
            "asset_description": "Máy siêu âm Philips EPIQ 7 cấu hình tim mạch + tổng quát, gồm 4 đầu dò (X5-1, C5-1, L12-3, S5-1) và bàn điều khiển nâng hạ.",
            "warranty_months": 24,
            "is_radiation_device": 0,
            "risk_class": "Class IIa",
        },
    ]
    today = getdate(nowdate())
    for i, s in enumerate(scenarios):
        asset = frappe.get_doc("AC Asset", asset_names[s["asset_idx"]])
        existing = frappe.db.get_value(
            "Asset Commissioning", {"po_reference": s["po_reference"]}
        )
        if existing:
            print(f"  [skip] Already exists: {existing} (PO={s['po_reference']})")
            out.append(existing)
            continue
        doc = frappe.new_doc("Asset Commissioning")
        doc.update({
            "po_reference": s["po_reference"],
            "master_item": asset.device_model,
            "vendor": asset.supplier,
            "clinical_dept": asset.department,
            "expected_installation_date": add_days(today, -10 + i * 3),
            "reception_date": add_days(today, -7 + i * 3),
            "asset_description": s["asset_description"],
            "delivery_note_no": s["delivery_note_no"],
            "purchase_price": s["purchase_price"],
            "warranty_expiry_date": add_months(today, s["warranty_months"]),
            "installation_date": add_days(today, -5 + i * 3),
            "vendor_engineer_name": s["vendor_engineer_name"],
            "commissioned_by": "chuvanhieu357@gmail.com",
            "installation_location": asset.location,
            "received_by": "chuvanhieu357@gmail.com",
            "dept_head_acceptance": "snonamevx@gmail.com",
            "is_radiation_device": s["is_radiation_device"],
            "risk_class": s["risk_class"],
            "clinical_head": "snonamevx@gmail.com",
            "qa_officer": "sohaidiuuu@gmail.com",
            "board_approver": "chuvanhieu357@gmail.com",
            "facility_checklist_pass": 1,
            "vendor_serial_no": f"SN-REAL-{s['po_reference'].split('-')[-1]}",
            "approval_remarks": "Hồ sơ bàn giao đầy đủ. Đề nghị duyệt commissioning.",
        })
        doc.insert(ignore_permissions=True)
        print(f"  [+] {doc.name} | PO={s['po_reference']} | {asset.asset_name}")
        out.append(doc.name)
    return out


def seed_imm05(asset_names: list[str]) -> list[str]:
    """Create 3 Asset Document records (legal/technical/certification)."""
    print("\n=== IMM-05: Asset Document ===")
    out: list[str] = []
    scenarios = [
        {
            "asset_idx": 0,
            "doc_category": "Legal",
            "doc_type_detail": "Giấy phép lưu hành sản phẩm BYT",
            "doc_number": "BYT-LH-2024-DRG-V500-0145",
            "version": "1.0",
            "issuing_authority": "Bộ Y tế — Cục Quản lý Khám chữa bệnh",
            "issued_date": "2024-03-15",
            "expiry_date": add_days(nowdate(), 540),
            "notes": "Giấy phép lưu hành Máy thở Dräger Evita V500 theo NĐ98/2021/NĐ-CP. Đính kèm bản scan màu, công chứng tại UBND Q1 ngày 18/03/2024.",
            "visibility": "Internal_Only",
        },
        {
            "asset_idx": 1,
            "doc_category": "Technical",
            "doc_type_detail": "Hướng dẫn vận hành tiếng Việt",
            "doc_number": "TECH-MNR-T9-VN-2024-Rev2",
            "version": "2.1",
            "issuing_authority": "Mindray Vietnam Co., Ltd",
            "issued_date": "2024-01-20",
            "expiry_date": None,
            "notes": "Tài liệu HDSD bản tiếng Việt — Mindray BeneView T9 firmware 02.05. Bao gồm troubleshooting code E-001 đến E-128.",
            "visibility": "Public",
        },
        {
            "asset_idx": 2,
            "doc_category": "Certification",
            "doc_type_detail": "Biên bản hiệu chuẩn ban đầu",
            "doc_number": "CAL-EPQ7-INIT-2024-0089",
            "version": "1.0",
            "issuing_authority": "Trung tâm Kiểm chuẩn TBYT TP.HCM",
            "issued_date": "2024-04-12",
            "expiry_date": add_months(nowdate(), 12),
            "notes": "Biên bản hiệu chuẩn ban đầu sau lắp đặt — Philips EPIQ 7, đo độ chính xác đo lường tim mạch theo TCVN 8023:2009. Pass toàn bộ test points.",
            "visibility": "Internal_Only",
        },
    ]
    for s in scenarios:
        asset = frappe.get_doc("AC Asset", asset_names[s["asset_idx"]])
        existing = frappe.db.get_value(
            "Asset Document", {"doc_number": s["doc_number"]}
        )
        if existing:
            print(f"  [skip] Already exists: {existing} (doc#={s['doc_number']})")
            out.append(existing)
            continue
        doc = frappe.new_doc("Asset Document")
        doc.update({
            "asset_ref": asset.name,
            "model_ref": asset.device_model,
            "clinical_dept": asset.department,
            "is_model_level": 0,
            "doc_category": s["doc_category"],
            "doc_type_detail": s["doc_type_detail"],
            "doc_number": s["doc_number"],
            "version": s["version"],
            "issued_date": s["issued_date"],
            "expiry_date": s["expiry_date"],
            "issuing_authority": s["issuing_authority"],
            "visibility": s["visibility"],
            "approved_by": "chuvanhieu357@gmail.com",
            "approval_date": nowdate(),
            "notes": s["notes"],
            "change_summary": s.get("change_summary") or "Phiên bản phát hành ban đầu sau khi commissioning thiết bị.",
        })
        doc.insert(ignore_permissions=True)
        print(f"  [+] {doc.name} | {s['doc_category']} | {s['doc_type_detail']}")
        out.append(doc.name)
    return out


def seed_imm06(asset_names: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Create 3 Training Program + 3 Session + 3 User Competency records."""
    print("\n=== IMM-06: Training Program + Session + Competency ===")
    progs: list[str] = []
    sessions: list[str] = []
    comps: list[str] = []

    prog_specs = [
        {
            "program_code": "TPGM-DRG-V500-INIT",
            "program_name": "Vận hành Máy thở Dräger Evita V500 — Khóa đầu vào ICU",
            "description": "Khóa đào tạo ban đầu cho điều dưỡng và bác sĩ ICU vận hành Máy thở Dräger Evita V500. Bao gồm cài đặt mode CMV/SIMV/PSV, alarm management, bảo dưỡng cấp người dùng.",
            "model_idx": 0,
            "training_type": "Initial",
            "duration_hours": 16.0,
            "validity_months": 24,
            "assessment_method": "Both",
            "passing_score_pct": 80.0,
            "instructor_qual": "Bác sĩ ICU hoặc KS lâm sàng có chứng chỉ Dräger Master Trainer",
        },
        {
            "program_code": "TPGM-MNR-T9-REFRESH",
            "program_name": "Cập nhật Monitor Mindray BeneView T9 — Khóa bổ sung",
            "description": "Khóa bồi dưỡng định kỳ — 2 năm/lần — cho điều dưỡng Phòng Mổ 2. Tập trung vào module EtCO2 mới và quy trình arrhythmia analysis cập nhật 2025.",
            "model_idx": 1,
            "training_type": "Refresher",
            "duration_hours": 8.0,
            "validity_months": 24,
            "assessment_method": "Practical",
            "passing_score_pct": 75.0,
            "instructor_qual": "KTV cấp 3 trở lên, có chứng chỉ Mindray Certified Trainer",
        },
        {
            "program_code": "TPGM-PHL-EPQ7-ADV",
            "program_name": "Siêu âm tim mạch chuyên sâu Philips EPIQ 7",
            "description": "Đào tạo nâng cao kỹ thuật siêu âm tim 4D, strain imaging và xQuant cho bác sĩ chuyên ngành Tim mạch can thiệp. Bắt buộc trước khi cấp quyền vận hành.",
            "model_idx": 2,
            "training_type": "Advanced",
            "duration_hours": 40.0,
            "validity_months": 36,
            "assessment_method": "Both",
            "passing_score_pct": 85.0,
            "instructor_qual": "Bác sĩ Tim mạch can thiệp có chứng chỉ Philips EPIQ Advanced Application Specialist",
        },
    ]
    for s in prog_specs:
        existing = frappe.db.get_value("IMM Training Program", {"program_code": s["program_code"]})
        if existing:
            print(f"  [skip prog] {existing}")
            progs.append(existing)
            continue
        doc = frappe.new_doc("IMM Training Program")
        doc.update({
            "program_code": s["program_code"],
            "program_name": s["program_name"],
            "description": s["description"],
            "target_device_model": REAL_DATA["models"][s["model_idx"]],
            "is_mandatory_for_operation": 1,
            "training_type": s["training_type"],
            "content_outline": f"<p>1. Tổng quan thiết bị và rủi ro lâm sàng</p><p>2. Quy trình vận hành tiêu chuẩn (SOP)</p><p>3. Xử lý alarm và sự cố thường gặp</p><p>4. Bảo dưỡng cấp người dùng</p><p>5. Đánh giá lý thuyết + thực hành cuối khóa</p>",
            "duration_hours": s["duration_hours"],
            "validity_period_months": s["validity_months"],
            "requires_recertification": 1,
            "assessment_method": s["assessment_method"],
            "passing_score_pct": s["passing_score_pct"],
            "instructor_qualification_required": s["instructor_qual"],
            "is_active": 1,
        })
        doc.insert(ignore_permissions=True)
        print(f"  [+ prog] {doc.name} | {s['program_name']}")
        progs.append(doc.name)

    # Training Sessions
    sess_specs = [
        {"prog_idx": 0, "date": add_days(nowdate(), -14), "type": "Onsite",
         "location": "Phòng đào tạo TTYT — Tầng 2 Nhà A",
         "instructor": "chuvanhieu357@gmail.com",
         "duration_planned": 16.0, "duration_actual": 16.0,
         "remarks": "Hoàn thành đầy đủ chương trình. 6/6 học viên đạt yêu cầu lý thuyết và thực hành."},
        {"prog_idx": 1, "date": add_days(nowdate(), -7), "type": "Onsite",
         "location": "Phòng Mổ 2 — Khu vực thực hành",
         "instructor": "snonamevx@gmail.com",
         "duration_planned": 8.0, "duration_actual": 8.5,
         "remarks": "Vượt giờ 30 phút do bổ sung phần thực hành EtCO2 calibration. Tất cả học viên đạt."},
        {"prog_idx": 2, "date": add_days(nowdate(), -3), "type": "Hybrid",
         "location": "Khoa Chẩn đoán Hình ảnh — Phòng siêu âm 1",
         "instructor": "chuvanhieu357@gmail.com",
         "duration_planned": 40.0, "duration_actual": 38.0,
         "remarks": "Khóa nâng cao — kết hợp online (16h lý thuyết) và onsite (22h thực hành). Học viên cần thêm 2h tự ôn để đạt mức Senior."},
    ]
    for s in sess_specs:
        existing = frappe.db.get_value(
            "IMM Training Session",
            {"training_program": progs[s["prog_idx"]], "session_date": s["date"]},
        )
        if existing:
            print(f"  [skip sess] {existing}")
            sessions.append(existing)
            continue
        doc = frappe.new_doc("IMM Training Session")
        doc.update({
            "training_program": progs[s["prog_idx"]],
            "session_date": s["date"],
            "session_type": s["type"],
            "location": s["location"],
            "instructor": s["instructor"],
            "duration_planned_hours": s["duration_planned"],
            "duration_actual_hours": s["duration_actual"],
            "evaluation_method": "Bài kiểm tra trắc nghiệm 30 câu + bài thực hành theo SOP của thiết bị",
            "status_remarks": s["remarks"],
        })
        doc.insert(ignore_permissions=True)
        print(f"  [+ sess] {doc.name} | {s['date']} | {s['type']}")
        sessions.append(doc.name)

    # User Competencies
    comp_specs = [
        {"user": "chuvanhieu357@gmail.com", "prog_idx": 0, "sess_idx": 0, "dept": "Khoa-HSTC",
         "level": "Senior Operator", "theory": 92.0, "practical": 90.0,
         "validity_months": 24, "supervisor": "snonamevx@gmail.com"},
        {"user": "snonamevx@gmail.com", "prog_idx": 1, "sess_idx": 1, "dept": "Phong-Mo-2",
         "level": "Operator", "theory": 82.0, "practical": 85.0,
         "validity_months": 24, "supervisor": "chuvanhieu357@gmail.com"},
        {"user": "sohaidiuuu@gmail.com", "prog_idx": 2, "sess_idx": 2, "dept": "Khoa-CDHA",
         "level": "Trainer", "theory": 95.0, "practical": 93.0,
         "validity_months": 36, "supervisor": "chuvanhieu357@gmail.com"},
    ]
    for s in comp_specs:
        existing = frappe.db.get_value(
            "IMM User Competency",
            {"user": s["user"], "training_program": progs[s["prog_idx"]]},
        )
        if existing:
            print(f"  [skip comp] {existing}")
            comps.append(existing)
            continue
        achieved = add_days(nowdate(), -1)
        # BR-06-13: SoT DUY NHẤT cho expiry + recert (1 call) — KHÔNG inline công thức.
        # Lazy-import để tránh side effect ở import-time của script seed.
        from assetcore.services.imm06 import compute_competency_dates
        dates = compute_competency_dates(achieved, s["validity_months"])
        doc = frappe.new_doc("IMM User Competency")
        doc.update({
            "user": s["user"],
            "device_model": REAL_DATA["models"][s["prog_idx"]],
            "training_program": progs[s["prog_idx"]],
            "training_session": sessions[s["sess_idx"]],
            "department_at_assessment": s["dept"],
            "competency_level": s["level"],
            "achieved_date": achieved,
            "validity_months": s["validity_months"],
            "expiry_date": dates["expiry_date"],
            "recertification_due_date": dates["recertification_due_date"],
            "last_assessment_score": (s["theory"] + s["practical"]) / 2,
            "theory_score": s["theory"],
            "practical_score": s["practical"],
            "supervisor_signoff": s["supervisor"],
            "signoff_date": achieved,
        })
        doc.insert(ignore_permissions=True)
        print(f"  [+ comp] {doc.name} | {s['user']} | level={s['level']}")
        comps.append(doc.name)

    return progs, sessions, comps


def run() -> None:
    frappe.set_user("Administrator")
    print("Seeding IMM-04 / IMM-05 / IMM-06 with realistic data...")
    asset_names = _ensure_assets()
    if len(asset_names) < 3:
        raise RuntimeError("Need at least 3 AC Asset records.")
    accept_names = seed_imm04(asset_names)
    doc_names = seed_imm05(asset_names)
    prog_names, sess_names, comp_names = seed_imm06(asset_names)
    frappe.db.commit()
    print("\n=== SUMMARY ===")
    print(f"IMM-04 Asset Commissioning: {accept_names}")
    print(f"IMM-05 Asset Document: {doc_names}")
    print(f"IMM-06 Training Programs: {prog_names}")
    print(f"IMM-06 Training Sessions: {sess_names}")
    print(f"IMM-06 User Competencies: {comp_names}")
    print("[DONE]")
