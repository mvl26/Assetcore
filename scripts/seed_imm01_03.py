"""
Seed script — IMM-01 → IMM-03 demo data
Xoá toàn bộ data test, tạo lại data thực tế đẹp cho 5 kịch bản.

Chạy: bench --site assetcore execute assetcore.scripts.seed_imm01_03.seed
"""

import frappe
from frappe.utils import today, add_days, add_months, getdate


# ─── Helpers ──────────────────────────────────────────────────────────────────

def delete_all(doctype: str) -> None:
    names = frappe.get_all(doctype, pluck="name")
    for n in names:
        frappe.delete_doc(doctype, n, force=True, ignore_missing=True)
    frappe.db.commit()


def new_doc(doctype: str, **kwargs):
    doc = frappe.get_doc({"doctype": doctype, **kwargs})
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc


def set_status(doctype: str, name: str, **fields) -> None:
    frappe.db.set_value(doctype, name, fields)
    frappe.db.commit()


# ─── Main ─────────────────────────────────────────────────────────────────────

def seed():
    frappe.set_user("Administrator")

    print("── Xoá data cũ ─────────────────────────────────────────────────")
    for dt in [
        "Purchase Order Request",
        "Vendor Evaluation Item",
        "Vendor Evaluation",
        "Technical Specification",
        "Procurement Plan Item",
        "Procurement Plan",
        "Needs Assessment",
    ]:
        count = frappe.db.count(dt)
        delete_all(dt)
        print(f"  Đã xoá {count} {dt}")

    print("\n── Cập nhật Master Data ─────────────────────────────────────────")
    _seed_suppliers()
    _seed_departments()

    print("\n── Kịch bản A: Máy thở ICU (happy path hoàn chỉnh) ─────────────")
    na_a = _scenario_a_ventilator_icu()

    print("\n── Kịch bản B: Thiết bị Chẩn đoán Hình ảnh (multi-item) ────────")
    _scenario_b_radiology_multiitem()

    print("\n── Kịch bản C: Ngoại lệ — NA bị từ chối ────────────────────────")
    _scenario_c_rejected_na()

    print("\n── Kịch bản D: Ngoại lệ — Waiver vendor ─────────────────────────")
    _scenario_d_waiver_vendor()

    print("\n── Kịch bản E: Ngoại lệ — POR vượt 500M, cần GĐ duyệt ──────────")
    _scenario_e_director_approval()

    print("\n✓ Seeding hoàn tất.")


# ─── Master Data ──────────────────────────────────────────────────────────────

def _seed_suppliers():
    existing = frappe.get_all("AC Supplier", pluck="name")
    suppliers = [
        {
            "name": "AC-SUP-2026-0001",
            "supplier_name": "MedEquip Vietnam JSC",
            "vendor_type": "Manufacturer",
            "country": "Vietnam",
            "email_id": "sales@medequip.vn",
            "phone": "024-3825-1100",
            "local_representative": "Nguyễn Văn Hùng",
            "iso_13485_cert": "ISO13485-VN-0042",
            "iso_13485_expiry": add_months(today(), 18),
            "contract_start": "2025-01-01",
            "contract_end": "2027-12-31",
            "contract_value": 15_000_000_000,
            "is_active": 1,
        },
        {
            "name": "AC-SUP-2026-0002",
            "supplier_name": "BioService Medical Co., Ltd",
            "vendor_type": "Service",
            "country": "Vietnam",
            "email_id": "contract@bioservice.vn",
            "phone": "028-3930-5500",
            "local_representative": "Trần Thị Mai",
            "iso_13485_cert": "ISO13485-VN-0089",
            "iso_13485_expiry": add_months(today(), 12),
            "contract_start": "2024-07-01",
            "contract_end": "2026-06-30",
            "contract_value": 4_500_000_000,
            "is_active": 1,
        },
        {
            "name": "AC-SUP-2026-0003",
            "supplier_name": "VietCal Metrology Lab",
            "vendor_type": "Calibration Lab",
            "country": "Vietnam",
            "email_id": "info@vietcal.vn",
            "phone": "024-3556-7700",
            "local_representative": "Lê Quang Minh",
            "iso_17025_cert": "VIVAL-17025-0031",
            "iso_17025_expiry": add_months(today(), 24),
            "is_active": 1,
        },
        {
            "name": "AC-SUP-2026-0004",
            "supplier_name": "Philips Medical Vietnam LLC",
            "vendor_type": "Manufacturer",
            "country": "Netherlands",
            "email_id": "vn.medical@philips.com",
            "phone": "028-3823-9900",
            "local_representative": "Phạm Đức Khoa",
            "iso_13485_cert": "ISO13485-EU-0017",
            "iso_13485_expiry": add_months(today(), 30),
            "contract_start": "2025-06-01",
            "contract_end": "2028-05-31",
            "contract_value": 28_000_000_000,
            "is_active": 1,
        },
    ]
    for s in suppliers:
        if s["name"] in existing:
            frappe.db.set_value("AC Supplier", s["name"], {k: v for k, v in s.items() if k != "name"})
        else:
            doc = frappe.get_doc({"doctype": "AC Supplier", **s})
            doc.insert(ignore_permissions=True)
        print(f"  Supplier: {s['name']} — {s['supplier_name']}")
    frappe.db.commit()


def _seed_departments():
    # Departments đã đẹp, chỉ đảm bảo 5 khoa có đầy đủ info
    dept_updates = {
        "AC-DEPT-0001": {"dept_head": "Administrator", "email": "icu@hospital.vn", "phone": "101"},
        "AC-DEPT-0002": {"dept_head": "Administrator", "email": "rad@hospital.vn", "phone": "102"},
        "AC-DEPT-0003": {"dept_head": "Administrator", "email": "ccu@hospital.vn", "phone": "103"},
        "AC-DEPT-0004": {"dept_head": "Administrator", "email": "opd@hospital.vn", "phone": "104"},
        "AC-DEPT-0005": {"dept_head": "Administrator", "email": "or@hospital.vn",  "phone": "105"},
    }
    for name, vals in dept_updates.items():
        if frappe.db.exists("AC Department", name):
            frappe.db.set_value("AC Department", name, vals)
            print(f"  Dept: {name}")
    frappe.db.commit()


# ─── Scenario A: Máy thở ICU — Happy Path ─────────────────────────────────────

def _scenario_a_ventilator_icu():
    """
    NA (ICU) → Approved
    PP (Q1/2026) → Budget Locked (1 item)
    TS → Completed
    VE → Approved (2 vendors, recommended MedEquip)
    POR → Approved → Released
    """
    # 1. Needs Assessment
    na = new_doc("Needs Assessment",
        requesting_dept="AC-DEPT-0001",
        request_date="2026-01-05",
        requested_by="Administrator",
        equipment_type="Máy thở cao cấp (ICU Ventilator)",
        quantity=2,
        priority="Critical",
        estimated_budget=3_200_000_000,
        current_equipment_age=9,
        failure_frequency="Cao (>5 lần/năm)",
        clinical_justification=(
            "Hai máy thở Drager Evita 4 hiện tại đã hoạt động 9 năm, vượt vòng đời khuyến nghị 7 năm. "
            "Tần suất hỏng hóc tăng cao (8 lần trong 12 tháng qua), gây gián đoạn chăm sóc bệnh nhân nặng. "
            "ICU đang vận hành 16 giường, tỷ lệ lấp đầy 92%, cần 2 máy thở thế hệ mới hỗ trợ "
            "SIMV, PSV, APRV và NIV để đáp ứng yêu cầu lâm sàng hiện tại."
        ),
        status="Approved",
        approved_budget=3_200_000_000,
        htmreview_notes="Đã kiểm tra hiện trạng máy — xác nhận xuống cấp nghiêm trọng. Khuyến nghị thay thế.",
        finance_notes="Ngân sách Q1/2026 đã được phê duyệt trong kế hoạch đầu tư TSCĐ.",
    )
    print(f"  NA: {na.name} — Approved")

    # 2. Procurement Plan
    pp = new_doc("Procurement Plan",
        plan_year=2026,
        approved_budget=3_500_000_000,
        allocated_budget=3_200_000_000,
        remaining_budget=300_000_000,
        status="Budget Locked",
        approved_by="Administrator",
        approval_date="2026-01-15",
        approval_notes="Kế hoạch Q1/2026 — thiết bị hồi sức tích cực. Ngân sách từ nguồn TSCĐ bệnh viện.",
    )
    pp_item_name = frappe.db.get_all("Procurement Plan Item", filters={"parent": pp.name}, pluck="name")
    if not pp_item_name:
        ppi = frappe.get_doc({
            "doctype": "Procurement Plan Item",
            "parent": pp.name,
            "parentfield": "items",
            "parenttype": "Procurement Plan",
            "needs_assessment": na.name,
            "equipment_description": "Máy thở cao cấp ICU (Hamilton G5 hoặc tương đương)",
            "quantity": 2,
            "estimated_unit_cost": 1_600_000_000,
            "total_cost": 3_200_000_000,
            "priority": "Critical",
            "planned_quarter": "Q1",
            "status": "Pending",
        })
        ppi.insert(ignore_permissions=True)
        frappe.db.commit()
        ppi_name = ppi.name
    else:
        ppi_name = pp_item_name[0]
    print(f"  PP: {pp.name} → Budget Locked | Item: {ppi_name}")

    # 3. Technical Specification
    ts = new_doc("Technical Specification",
        equipment_type="Máy thở cao cấp ICU",
        linked_plan_item=ppi_name,
        status="Completed",
        general_requirements=(
            "• Máy thở thế hệ thứ 4, hỗ trợ đầy đủ các mode: VCV, PCV, SIMV, PSV, APRV, CPAP, NIV\n"
            "• Tidal volume: 20–2000 mL, độ chính xác ±5%\n"
            "• Áp lực hít vào: 5–80 cmH₂O\n"
            "• FiO₂: 21–100%, blender tích hợp\n"
            "• Màn hình cảm ứng ≥15 inch, hiển thị waveform và loop\n"
            "• Pin dự phòng ≥4 giờ\n"
            "• Kết nối HL7/FHIR với HIS\n"
            "• Bảo hành 24 tháng, cam kết uptime ≥98%"
        ),
        regulatory_requirements=(
            "• Đăng ký lưu hành Bộ Y tế (NĐ 98/2021)\n"
            "• CE Mark / FDA 510(k) hoặc tương đương\n"
            "• ISO 80601-2-12 (máy thở ICU)\n"
            "• Nhà phân phối có ISO 13485:2016"
        ),
        reviewed_by="Administrator",
        review_date="2026-01-20",
    )
    print(f"  TS: {ts.name} — Completed")

    # 4. Vendor Evaluation
    ve = new_doc("Vendor Evaluation",
        linked_plan=pp.name,
        linked_plan_item=ppi_name,
        linked_technical_spec=ts.name,
        evaluation_date="2026-02-10",
        evaluation_method="Đấu thầu rộng rãi",
        bid_issue_date="2026-01-25",
        bid_closing_date="2026-02-07",
        bid_opening_date="2026-02-08",
        bids_received_count=2,
        status="Approved",
        recommended_vendor="AC-SUP-2026-0001",
        selection_justification=(
            "MedEquip Vietnam JSC đạt tổng điểm cao nhất (87/100), đáp ứng toàn bộ yêu cầu kỹ thuật, "
            "có kinh nghiệm lắp đặt >30 máy thở tại các BV tuyến trung ương. "
            "Giá chào hàng 3.0 tỷ VNĐ nằm trong ngưỡng ngân sách được duyệt."
        ),
        committee_members="Administrator; Trưởng khoa ICU; Phòng VTBM; Phòng Tài chính",
        tech_reviewed_by="Administrator",
        tech_review_date="2026-02-09",
        approved_by="Administrator",
        approval_date="2026-02-12",
        unsuccessful_vendor_notified=1,
    )
    # VE Items
    vei1 = frappe.get_doc({
        "doctype": "Vendor Evaluation Item",
        "parent": ve.name, "parentfield": "items", "parenttype": "Vendor Evaluation",
        "vendor": "AC-SUP-2026-0001",
        "vendor_name": "MedEquip Vietnam JSC",
        "quoted_price": 3_000_000_000,
        "technical_score": 88,
        "financial_score": 82,
        "profile_score": 90,
        "risk_score": 85,
        "total_score": 87,
        "score_band": "Xuất sắc (≥85)",
        "compliant_with_ts": 1,
        "has_nd98_registration": 1,
        "bid_compliant": 1,
        "quoted_delivery_weeks": 10,
        "offered_payment_terms": "30% tạm ứng, 70% sau nghiệm thu",
        "is_recommended": 1,
        "notes": "Sản phẩm: Hamilton G5 Pro. Đội ngũ kỹ thuật hiện diện tại chỗ trong 24h.",
    })
    vei1.insert(ignore_permissions=True)

    vei2 = frappe.get_doc({
        "doctype": "Vendor Evaluation Item",
        "parent": ve.name, "parentfield": "items", "parenttype": "Vendor Evaluation",
        "vendor": "AC-SUP-2026-0002",
        "vendor_name": "BioService Medical Co., Ltd",
        "quoted_price": 2_800_000_000,
        "technical_score": 72,
        "financial_score": 90,
        "profile_score": 70,
        "risk_score": 68,
        "total_score": 74,
        "score_band": "Đạt (70–84)",
        "compliant_with_ts": 1,
        "has_nd98_registration": 1,
        "bid_compliant": 1,
        "quoted_delivery_weeks": 14,
        "offered_payment_terms": "50% tạm ứng, 50% sau lắp đặt",
        "is_recommended": 0,
        "notes": "Giá thấp hơn nhưng điểm kỹ thuật thấp, thời gian giao hàng dài hơn 4 tuần.",
    })
    vei2.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"  VE: {ve.name} — Approved | 2 vendors | Recommended: AC-SUP-2026-0001")

    # 5. Purchase Order Request
    por = new_doc("Purchase Order Request",
        linked_plan_item=ppi_name,
        procurement_plan=pp.name,
        linked_evaluation=ve.name,
        vendor="AC-SUP-2026-0001",
        vendor_name="MedEquip Vietnam JSC",
        equipment_description="Máy thở cao cấp ICU (Hamilton G5 Pro) x2",
        quantity=2,
        unit_price=1_500_000_000,
        total_amount=3_000_000_000,
        delivery_terms="DAP Bệnh viện, lắp đặt và đào tạo tại chỗ",
        incoterms="DAP",
        payment_terms="30% tạm ứng, 70% sau nghiệm thu kỹ thuật",
        expected_delivery_date=add_days(today(), 70),
        warranty_period_months=24,
        payment_schedule_notes="Đợt 1: 900M sau ký HĐ. Đợt 2: 2.1 tỷ sau nghiệm thu.",
        status="Approved",
        approved_by="Administrator",
        approval_date="2026-02-20",
        released_by="Administrator",
        release_date="2026-02-21",
    )
    set_status("Purchase Order Request", por.name, status="Released", release_date="2026-02-21", released_by="Administrator")
    set_status("Procurement Plan Item", ppi_name, status="PO Raised", por_reference=por.name)
    print(f"  POR: {por.name} — Released ✓ (luồng A hoàn chỉnh)")
    return na


# ─── Scenario B: Radiology — Multi-item ───────────────────────────────────────

def _scenario_b_radiology_multiitem():
    """
    2 NA (X-quang + Siêu âm) → Approved
    1 PP với 2 PP Items → Budget Locked
    1 VE (Philips recommended) → Approved
    2 POR (Draft)
    """
    # NA 1 — X-quang
    na1 = new_doc("Needs Assessment",
        requesting_dept="AC-DEPT-0002",
        request_date="2026-01-10",
        requested_by="Administrator",
        equipment_type="Máy X-quang kỹ thuật số DR",
        quantity=1,
        priority="High",
        estimated_budget=2_500_000_000,
        current_equipment_age=11,
        failure_frequency="Trung bình (2–4 lần/năm)",
        clinical_justification=(
            "Máy X-quang CR hiện tại (2015) hết hỗ trợ kỹ thuật từ nhà sản xuất. "
            "Chất lượng ảnh thấp, không đáp ứng tiêu chuẩn chẩn đoán hiện đại. "
            "Cần nâng cấp lên DR (Digital Radiography) để giảm liều phóng xạ 40% và rút ngắn thời gian chụp."
        ),
        status="Approved",
        approved_budget=2_500_000_000,
        htmreview_notes="Máy X-quang vượt vòng đời, không còn linh kiện thay thế. Ưu tiên cao.",
        finance_notes="Phê duyệt ngân sách Q2/2026.",
    )
    print(f"  NA: {na1.name} — X-quang Approved")

    # NA 2 — Siêu âm
    na2 = new_doc("Needs Assessment",
        requesting_dept="AC-DEPT-0002",
        request_date="2026-01-12",
        requested_by="Administrator",
        equipment_type="Máy siêu âm 4D Doppler màu",
        quantity=2,
        priority="High",
        estimated_budget=2_400_000_000,
        current_equipment_age=7,
        failure_frequency="Thấp (<2 lần/năm)",
        clinical_justification=(
            "Khoa CĐHA hiện có 3 máy siêu âm 2D, không hỗ trợ Doppler màu và 4D. "
            "Nhu cầu siêu âm tim mạch và sản khoa 4D tăng 35% trong 2 năm qua. "
            "Cần bổ sung 2 máy siêu âm cao cấp để đáp ứng lịch hẹn và nâng cao chất lượng chẩn đoán."
        ),
        status="Approved",
        approved_budget=2_400_000_000,
        htmreview_notes="Xác nhận nhu cầu lâm sàng — khuyến nghị đầu tư Q2.",
        finance_notes="Phê duyệt ngân sách Q2/2026.",
    )
    print(f"  NA: {na2.name} — Siêu âm Approved")

    # PP
    pp = new_doc("Procurement Plan",
        plan_year=2026,
        approved_budget=5_200_000_000,
        allocated_budget=4_900_000_000,
        remaining_budget=300_000_000,
        status="Budget Locked",
        approved_by="Administrator",
        approval_date="2026-02-01",
        approval_notes="Kế hoạch Q2/2026 — nâng cấp thiết bị chẩn đoán hình ảnh.",
    )

    # PP Item 1
    ppi1 = frappe.get_doc({
        "doctype": "Procurement Plan Item",
        "parent": pp.name, "parentfield": "items", "parenttype": "Procurement Plan",
        "needs_assessment": na1.name,
        "equipment_description": "Máy X-quang kỹ thuật số DR treo trần (Fixed DR System)",
        "quantity": 1,
        "estimated_unit_cost": 2_500_000_000,
        "total_cost": 2_500_000_000,
        "priority": "High",
        "planned_quarter": "Q2",
        "status": "Pending",
    })
    ppi1.insert(ignore_permissions=True)

    # PP Item 2
    ppi2 = frappe.get_doc({
        "doctype": "Procurement Plan Item",
        "parent": pp.name, "parentfield": "items", "parenttype": "Procurement Plan",
        "needs_assessment": na2.name,
        "equipment_description": "Máy siêu âm 4D Doppler màu (Premium Ultrasound System)",
        "quantity": 2,
        "estimated_unit_cost": 1_200_000_000,
        "total_cost": 2_400_000_000,
        "priority": "High",
        "planned_quarter": "Q2",
        "status": "Pending",
    })
    ppi2.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"  PP: {pp.name} → Budget Locked | 2 items ({ppi1.name}, {ppi2.name})")

    # TS
    ts = new_doc("Technical Specification",
        equipment_type="Thiết bị Chẩn đoán Hình ảnh (DR + Siêu âm 4D)",
        linked_plan_item=ppi1.name,
        status="Completed",
        general_requirements=(
            "DR: Detector FPD 43×43cm, độ phân giải ≥3.4 lp/mm, dose ≤1.5 mGy/image\n"
            "Siêu âm: ≥4 đầu dò (tim, bụng, cơ xương, nông), 4D real-time, Doppler màu + PW/CW\n"
            "Kết nối DICOM 3.0, tích hợp PACS"
        ),
        regulatory_requirements=(
            "Đăng ký BYT (NĐ 98/2021) | CE/FDA | IEC 60601-1 | ISO 13485 NCC"
        ),
        reviewed_by="Administrator",
        review_date="2026-02-05",
    )
    print(f"  TS: {ts.name} — Completed")

    # VE
    ve = new_doc("Vendor Evaluation",
        linked_plan=pp.name,
        linked_plan_item=ppi1.name,
        linked_technical_spec=ts.name,
        evaluation_date="2026-03-05",
        evaluation_method="Đấu thầu rộng rãi",
        bid_issue_date="2026-02-10",
        bid_closing_date="2026-03-01",
        bid_opening_date="2026-03-02",
        bids_received_count=2,
        status="Approved",
        recommended_vendor="AC-SUP-2026-0004",
        selection_justification=(
            "Philips Medical Vietnam đạt tổng điểm cao nhất (91/100). "
            "Sản phẩm DR Philips DigitalDiagnost C90 và Siêu âm EPIQ Elite đều đáp ứng ≥95% yêu cầu kỹ thuật. "
            "Có đội ngũ ứng cứu tại chỗ trong 4h. Giá cao hơn MedEquip 6% nhưng chất lượng kỹ thuật vượt trội."
        ),
        committee_members="Administrator; Trưởng khoa CĐHA; Phòng VTBM; Phòng Tài chính",
        tech_reviewed_by="Administrator",
        tech_review_date="2026-03-04",
        approved_by="Administrator",
        approval_date="2026-03-07",
        unsuccessful_vendor_notified=1,
    )
    vei1 = frappe.get_doc({
        "doctype": "Vendor Evaluation Item",
        "parent": ve.name, "parentfield": "items", "parenttype": "Vendor Evaluation",
        "vendor": "AC-SUP-2026-0004",
        "vendor_name": "Philips Medical Vietnam LLC",
        "quoted_price": 4_900_000_000,
        "technical_score": 93,
        "financial_score": 85,
        "profile_score": 95,
        "risk_score": 90,
        "total_score": 91,
        "score_band": "Xuất sắc (≥85)",
        "compliant_with_ts": 1,
        "has_nd98_registration": 1,
        "bid_compliant": 1,
        "quoted_delivery_weeks": 12,
        "offered_payment_terms": "25% tạm ứng, 75% sau nghiệm thu",
        "is_recommended": 1,
        "notes": "DR: DigitalDiagnost C90 | Siêu âm: EPIQ Elite. Đào tạo onsite 5 ngày.",
    })
    vei1.insert(ignore_permissions=True)

    vei2 = frappe.get_doc({
        "doctype": "Vendor Evaluation Item",
        "parent": ve.name, "parentfield": "items", "parenttype": "Vendor Evaluation",
        "vendor": "AC-SUP-2026-0001",
        "vendor_name": "MedEquip Vietnam JSC",
        "quoted_price": 4_600_000_000,
        "technical_score": 78,
        "financial_score": 92,
        "profile_score": 75,
        "risk_score": 72,
        "total_score": 79,
        "score_band": "Đạt (70–84)",
        "compliant_with_ts": 1,
        "has_nd98_registration": 1,
        "bid_compliant": 1,
        "quoted_delivery_weeks": 16,
        "offered_payment_terms": "40% tạm ứng, 60% sau nghiệm thu",
        "is_recommended": 0,
        "notes": "Giá cạnh tranh hơn nhưng điểm kỹ thuật thấp hơn, giao hàng chậm hơn.",
    })
    vei2.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"  VE: {ve.name} — Approved | Recommended: Philips (AC-SUP-2026-0004)")

    # POR 1 — X-quang
    por1 = new_doc("Purchase Order Request",
        linked_plan_item=ppi1.name,
        procurement_plan=pp.name,
        linked_evaluation=ve.name,
        vendor="AC-SUP-2026-0004",
        vendor_name="Philips Medical Vietnam LLC",
        equipment_description="Máy X-quang kỹ thuật số DR treo trần Philips DigitalDiagnost C90",
        quantity=1,
        unit_price=2_400_000_000,
        total_amount=2_400_000_000,
        delivery_terms="DAP Bệnh viện, bao gồm lắp đặt và hiệu chỉnh",
        incoterms="DAP",
        payment_terms="25% tạm ứng, 75% sau nghiệm thu kỹ thuật",
        expected_delivery_date=add_days(today(), 84),
        warranty_period_months=24,
        status="Draft",
    )
    set_status("Procurement Plan Item", ppi1.name, status="PO Raised", por_reference=por1.name)

    # POR 2 — Siêu âm
    por2 = new_doc("Purchase Order Request",
        linked_plan_item=ppi2.name,
        procurement_plan=pp.name,
        linked_evaluation=ve.name,
        vendor="AC-SUP-2026-0004",
        vendor_name="Philips Medical Vietnam LLC",
        equipment_description="Máy siêu âm 4D Doppler màu Philips EPIQ Elite x2",
        quantity=2,
        unit_price=1_150_000_000,
        total_amount=2_300_000_000,
        delivery_terms="DAP Bệnh viện, đào tạo vận hành 3 ngày/máy",
        incoterms="DAP",
        payment_terms="25% tạm ứng, 75% sau nghiệm thu kỹ thuật",
        expected_delivery_date=add_days(today(), 84),
        warranty_period_months=24,
        status="Draft",
    )
    set_status("Procurement Plan Item", ppi2.name, status="PO Raised", por_reference=por2.name)
    print(f"  POR-1: {por1.name} — X-quang (Draft)")
    print(f"  POR-2: {por2.name} — Siêu âm (Draft)")


# ─── Scenario C: NA bị từ chối ────────────────────────────────────────────────

def _scenario_c_rejected_na():
    """CCU yêu cầu máy ECG bị từ chối — đã đủ thiết bị"""
    na = new_doc("Needs Assessment",
        requesting_dept="AC-DEPT-0003",
        request_date="2026-01-18",
        requested_by="Administrator",
        equipment_type="Máy điện tim 12 kênh (ECG)",
        quantity=3,
        priority="Medium",
        estimated_budget=180_000_000,
        current_equipment_age=4,
        failure_frequency="Thấp (<1 lần/năm)",
        clinical_justification=(
            "Khoa CCU đề xuất bổ sung 3 máy ECG 12 kênh để tăng năng lực tiếp nhận bệnh nhân đau ngực. "
            "Hiện tại có 5 máy ECG đang hoạt động tốt."
        ),
        status="Rejected",
        htmreview_notes=(
            "Kiểm tra tại chỗ: 5/5 máy ECG hiện tại hoạt động bình thường, tuổi đời trung bình 4 năm. "
            "Tỷ lệ sử dụng 60%, không có tình trạng chờ đợi thiết bị. Không khuyến nghị mua thêm."
        ),
        finance_notes="Không phê duyệt — chưa đủ căn cứ lâm sàng.",
        reject_reason=(
            "Từ chối theo khuyến nghị HTM: thiết bị hiện tại đủ năng lực phục vụ, tỷ lệ sử dụng thấp (60%). "
            "Ngân sách ưu tiên cho các hạng mục có mức độ cấp thiết cao hơn. "
            "Khoa có thể đề xuất lại vào Q4/2026 kèm số liệu tải trọng thực tế."
        ),
    )
    print(f"  NA: {na.name} — ECG (Rejected) ✓")


# ─── Scenario D: Waiver vendor ────────────────────────────────────────────────

def _scenario_d_waiver_vendor():
    """
    Phòng mổ cần dao mổ điện — VE đề xuất MedEquip
    Nhưng OR Head chọn BioService (có contract bảo hành toàn diện)
    POR với waiver_reason → Draft
    """
    na = new_doc("Needs Assessment",
        requesting_dept="AC-DEPT-0005",
        request_date="2026-02-01",
        requested_by="Administrator",
        equipment_type="Dao mổ điện đa năng (Electrosurgical Unit — ESU)",
        quantity=2,
        priority="High",
        estimated_budget=600_000_000,
        current_equipment_age=8,
        failure_frequency="Trung bình (3–5 lần/năm)",
        clinical_justification=(
            "Dao mổ điện Valleylab Force FX hiện tại đã vượt vòng đời 7 năm. "
            "Hỏng hóc 4 lần trong năm 2025, gây trì hoãn 3 ca phẫu thuật khẩn. "
            "Phòng mổ cần 2 ESU mới hỗ trợ cắt đốt độc lập, bipolar và argon plasma coagulation."
        ),
        status="Approved",
        approved_budget=600_000_000,
        htmreview_notes="Xác nhận thiết bị xuống cấp — ưu tiên thay thế trước Q2/2026.",
        finance_notes="Phê duyệt ngân sách từ nguồn sửa chữa thiết bị.",
    )

    pp = new_doc("Procurement Plan",
        plan_year=2026,
        approved_budget=700_000_000,
        allocated_budget=600_000_000,
        remaining_budget=100_000_000,
        status="Budget Locked",
        approved_by="Administrator",
        approval_date="2026-02-10",
        approval_notes="Kế hoạch thay thế ESU — Phòng mổ.",
    )
    ppi = frappe.get_doc({
        "doctype": "Procurement Plan Item",
        "parent": pp.name, "parentfield": "items", "parenttype": "Procurement Plan",
        "needs_assessment": na.name,
        "equipment_description": "Dao mổ điện đa năng ESU (Valleylab FT10 hoặc tương đương)",
        "quantity": 2,
        "estimated_unit_cost": 300_000_000,
        "total_cost": 600_000_000,
        "priority": "High",
        "planned_quarter": "Q2",
        "status": "Pending",
    })
    ppi.insert(ignore_permissions=True)
    frappe.db.commit()

    ts = new_doc("Technical Specification",
        equipment_type="Dao mổ điện đa năng ESU",
        linked_plan_item=ppi.name,
        status="Completed",
        general_requirements=(
            "• Công suất cắt: ≥300W (monopolar), ≥120W (bipolar)\n"
            "• Hỗ trợ argon plasma coagulation (APC) tùy chọn\n"
            "• Màn hình LED rõ ràng, cài đặt nhanh từ 1 điểm\n"
            "• Hệ thống kiểm tra điện cực liên tục (CEM)\n"
            "• Bảo hành 24 tháng, hợp đồng bảo trì toàn diện"
        ),
        regulatory_requirements="Đăng ký BYT | CE Mark | IEC 60601-2-2 | ISO 13485 NCC",
        reviewed_by="Administrator",
        review_date="2026-02-15",
    )

    ve = new_doc("Vendor Evaluation",
        linked_plan=pp.name,
        linked_plan_item=ppi.name,
        linked_technical_spec=ts.name,
        evaluation_date="2026-03-10",
        evaluation_method="Chào hàng cạnh tranh",
        bid_issue_date="2026-02-18",
        bid_closing_date="2026-03-08",
        bid_opening_date="2026-03-09",
        bids_received_count=2,
        status="Approved",
        recommended_vendor="AC-SUP-2026-0001",
        selection_justification=(
            "MedEquip Vietnam đạt điểm kỹ thuật cao nhất (84/100) với sản phẩm Medtronic Force FX-8C. "
            "Tuy nhiên, trưởng phòng mổ có đề xuất ưu tiên BioService do hợp đồng bảo hành toàn diện hiện có. "
            "Hội đồng chấp thuận với điều kiện có biên bản miễn trừ lý do chọn NCC."
        ),
        committee_members="Administrator; Trưởng phòng Mổ; Phòng VTBM",
        tech_reviewed_by="Administrator",
        tech_review_date="2026-03-09",
        approved_by="Administrator",
        approval_date="2026-03-12",
        unsuccessful_vendor_notified=1,
    )
    vei1 = frappe.get_doc({
        "doctype": "Vendor Evaluation Item",
        "parent": ve.name, "parentfield": "items", "parenttype": "Vendor Evaluation",
        "vendor": "AC-SUP-2026-0001",
        "vendor_name": "MedEquip Vietnam JSC",
        "quoted_price": 590_000_000,
        "technical_score": 85, "financial_score": 88, "profile_score": 82, "risk_score": 80,
        "total_score": 84, "score_band": "Đạt (70–84)",
        "compliant_with_ts": 1, "has_nd98_registration": 1, "bid_compliant": 1,
        "quoted_delivery_weeks": 8,
        "offered_payment_terms": "40% tạm ứng, 60% sau nghiệm thu",
        "is_recommended": 1,
        "notes": "Medtronic Force FX-8C — đúng spec, giao hàng 8 tuần.",
    })
    vei1.insert(ignore_permissions=True)
    vei2 = frappe.get_doc({
        "doctype": "Vendor Evaluation Item",
        "parent": ve.name, "parentfield": "items", "parenttype": "Vendor Evaluation",
        "vendor": "AC-SUP-2026-0002",
        "vendor_name": "BioService Medical Co., Ltd",
        "quoted_price": 620_000_000,
        "technical_score": 80, "financial_score": 80, "profile_score": 85, "risk_score": 88,
        "total_score": 82, "score_band": "Đạt (70–84)",
        "compliant_with_ts": 1, "has_nd98_registration": 1, "bid_compliant": 1,
        "quoted_delivery_weeks": 6,
        "offered_payment_terms": "Thanh toán 1 lần sau nghiệm thu",
        "is_recommended": 0,
        "notes": "Erbe VIO 3 — giao hàng nhanh, có hợp đồng bảo hành toàn diện đang chạy.",
    })
    vei2.insert(ignore_permissions=True)
    frappe.db.commit()

    # POR với waiver — chọn BioService thay vì MedEquip
    por = new_doc("Purchase Order Request",
        linked_plan_item=ppi.name,
        procurement_plan=pp.name,
        linked_evaluation=ve.name,
        vendor="AC-SUP-2026-0002",
        vendor_name="BioService Medical Co., Ltd",
        equipment_description="Dao mổ điện đa năng Erbe VIO 3 x2 (Waiver VR-03-07)",
        quantity=2,
        unit_price=310_000_000,
        total_amount=620_000_000,
        delivery_terms="DAP Bệnh viện, lắp đặt và kiểm định tại chỗ",
        incoterms="DAP",
        payment_terms="Thanh toán 1 lần sau nghiệm thu và bàn giao",
        expected_delivery_date=add_days(today(), 42),
        warranty_period_months=24,
        waiver_reason=(
            "VR-03-07 WAIVER — Chọn BioService Medical thay vì NCC đề xuất MedEquip Vietnam vì:\n"
            "1. BioService đang thực hiện HĐ bảo hành toàn diện thiết bị phòng mổ (2024–2026), "
            "việc tích hợp ESU mới vào hợp đồng này tiết kiệm 85 triệu VNĐ/năm chi phí bảo trì.\n"
            "2. Erbe VIO 3 đáp ứng đầy đủ yêu cầu kỹ thuật, giao hàng nhanh hơn 2 tuần.\n"
            "3. Đội ngũ kỹ thuật BioService đã quen thiết bị phòng mổ tại bệnh viện.\n"
            "Biên bản đề xuất miễn trừ được ký bởi Trưởng phòng VTBM ngày 2026-03-11."
        ),
        status="Draft",
    )
    set_status("Procurement Plan Item", ppi.name, status="PO Raised", por_reference=por.name)
    print(f"  NA: {na.name} | PP: {pp.name} | VE: {ve.name}")
    print(f"  POR: {por.name} — Waiver vendor (BioService thay MedEquip) Draft ✓")


# ─── Scenario E: POR vượt 500M — Director approval ────────────────────────────

def _scenario_e_director_approval():
    """
    ICU cần hệ thống MRI 1.5T — ngân sách 18 tỷ
    POR requires_director_approval = 1, status = Under Review
    """
    na = new_doc("Needs Assessment",
        requesting_dept="AC-DEPT-0001",
        request_date="2026-02-15",
        requested_by="Administrator",
        equipment_type="Máy cộng hưởng từ MRI 1.5 Tesla",
        quantity=1,
        priority="Critical",
        estimated_budget=18_000_000_000,
        current_equipment_age=0,
        failure_frequency="N/A — trang bị mới",
        clinical_justification=(
            "Bệnh viện chưa có MRI, bệnh nhân cần chụp MRI phải chuyển viện hoặc tự đến cơ sở khác. "
            "Thống kê 2025: 1.240 ca chuyển viện chụp MRI, chi phí vận chuyển và chậm trễ chẩn đoán "
            "gây thiệt hại ước tính 4.2 tỷ/năm. Đầu tư MRI 1.5T sẽ hoàn vốn trong vòng 4.3 năm."
        ),
        status="Approved",
        approved_budget=18_000_000_000,
        htmreview_notes="Đánh giá nhu cầu đạt — đề xuất MRI 1.5T là phù hợp quy mô bệnh viện.",
        finance_notes="Phê duyệt từ Hội đồng quản trị — Nghị quyết số 05/2026/NQ-HĐQT.",
    )

    pp = new_doc("Procurement Plan",
        plan_year=2026,
        approved_budget=20_000_000_000,
        allocated_budget=18_000_000_000,
        remaining_budget=2_000_000_000,
        status="Budget Locked",
        approved_by="Administrator",
        approval_date="2026-03-01",
        approval_notes="Dự án đầu tư MRI — HĐQT phê duyệt.",
    )
    ppi = frappe.get_doc({
        "doctype": "Procurement Plan Item",
        "parent": pp.name, "parentfield": "items", "parenttype": "Procurement Plan",
        "needs_assessment": na.name,
        "equipment_description": "Hệ thống MRI 1.5 Tesla toàn thân (Siemens MAGNETOM Sola hoặc tương đương)",
        "quantity": 1,
        "estimated_unit_cost": 18_000_000_000,
        "total_cost": 18_000_000_000,
        "priority": "Critical",
        "planned_quarter": "Q3",
        "status": "Pending",
    })
    ppi.insert(ignore_permissions=True)
    frappe.db.commit()

    ts = new_doc("Technical Specification",
        equipment_type="Máy MRI 1.5 Tesla",
        linked_plan_item=ppi.name,
        status="Completed",
        general_requirements=(
            "• Từ trường 1.5 Tesla, siêu dẫn, hoạt động liên tục\n"
            "• Bore ≥70 cm, chiều dài ≤163 cm (bore ngắn)\n"
            "• Gradient ≥45 mT/m, slew rate ≥200 T/m/s\n"
            "• Hỗ trợ toàn bộ chuỗi xung: T1, T2, FLAIR, DWI, MRA, fMRI\n"
            "• Phần mềm nâng cao: post-processing, tim mạch, neuro\n"
            "• Hệ thống làm lạnh helium closed-loop (Zero Boil-Off)\n"
            "• Bảo hành 24 tháng, cam kết uptime ≥95%"
        ),
        regulatory_requirements=(
            "Đăng ký BYT loại C | CE Mark | FDA 510(k) | IEC 60601-2-33 | ISO 13485 NCC\n"
            "Yêu cầu phòng máy chống từ trường (RF shielding) theo NEMA MS 1"
        ),
        reviewed_by="Administrator",
        review_date="2026-03-10",
    )

    ve = new_doc("Vendor Evaluation",
        linked_plan=pp.name,
        linked_plan_item=ppi.name,
        linked_technical_spec=ts.name,
        evaluation_date="2026-04-05",
        evaluation_method="Đấu thầu quốc tế",
        bid_issue_date="2026-03-05",
        bid_closing_date="2026-04-01",
        bid_opening_date="2026-04-02",
        bids_received_count=2,
        status="Approved",
        recommended_vendor="AC-SUP-2026-0004",
        selection_justification=(
            "Philips Medical Vietnam đạt tổng điểm cao nhất (89/100) với hệ thống MRI Ingenia Ambition 1.5T. "
            "Điểm nổi bật: Zero Boil-Off helium (tiết kiệm 200 triệu/năm chi phí helium), "
            "bore 70 cm thân thiện bệnh nhân, phần mềm dStream Anatomical Intelligence. "
            "Giá 17.5 tỷ — nằm trong ngân sách được duyệt."
        ),
        committee_members="Administrator; Giám đốc BV; Phòng VTBM; Phòng Tài chính; Tư vấn kỹ thuật độc lập",
        tech_reviewed_by="Administrator",
        tech_review_date="2026-04-03",
        approved_by="Administrator",
        approval_date="2026-04-07",
        unsuccessful_vendor_notified=1,
    )
    vei1 = frappe.get_doc({
        "doctype": "Vendor Evaluation Item",
        "parent": ve.name, "parentfield": "items", "parenttype": "Vendor Evaluation",
        "vendor": "AC-SUP-2026-0004",
        "vendor_name": "Philips Medical Vietnam LLC",
        "quoted_price": 17_500_000_000,
        "technical_score": 92, "financial_score": 88, "profile_score": 90, "risk_score": 85,
        "total_score": 89, "score_band": "Xuất sắc (≥85)",
        "compliant_with_ts": 1, "has_nd98_registration": 1, "bid_compliant": 1,
        "quoted_delivery_weeks": 24,
        "offered_payment_terms": "20% đặt cọc, 50% lắp đặt, 30% nghiệm thu",
        "is_recommended": 1,
        "notes": "Philips Ingenia Ambition 1.5T — ZBO helium, bore 70cm, đào tạo 2 tuần.",
    })
    vei1.insert(ignore_permissions=True)
    vei2 = frappe.get_doc({
        "doctype": "Vendor Evaluation Item",
        "parent": ve.name, "parentfield": "items", "parenttype": "Vendor Evaluation",
        "vendor": "AC-SUP-2026-0001",
        "vendor_name": "MedEquip Vietnam JSC",
        "quoted_price": 16_800_000_000,
        "technical_score": 75, "financial_score": 92, "profile_score": 70, "risk_score": 65,
        "total_score": 75, "score_band": "Đạt (70–84)",
        "compliant_with_ts": 1, "has_nd98_registration": 1, "bid_compliant": 1,
        "quoted_delivery_weeks": 28,
        "offered_payment_terms": "30% đặt cọc, 70% nghiệm thu",
        "is_recommended": 0,
        "notes": "Giá cạnh tranh nhưng điểm kỹ thuật thấp hơn, không có ZBO helium.",
    })
    vei2.insert(ignore_permissions=True)
    frappe.db.commit()

    # POR >500M — cần Director
    por = new_doc("Purchase Order Request",
        linked_plan_item=ppi.name,
        procurement_plan=pp.name,
        linked_evaluation=ve.name,
        vendor="AC-SUP-2026-0004",
        vendor_name="Philips Medical Vietnam LLC",
        equipment_description="Hệ thống MRI 1.5T Philips Ingenia Ambition — bao gồm lắp đặt và shielding",
        quantity=1,
        unit_price=17_500_000_000,
        total_amount=17_500_000_000,
        requires_director_approval=1,
        delivery_terms="DDP Bệnh viện, bao gồm xây dựng phòng máy và RF shielding",
        incoterms="DDP",
        payment_terms="20% đặt cọc sau ký HĐ, 50% sau lắp đặt, 30% sau nghiệm thu",
        expected_delivery_date=add_days(today(), 168),
        warranty_period_months=24,
        payment_schedule_notes=(
            "Đợt 1: 3.5 tỷ (20%) — sau ký hợp đồng\n"
            "Đợt 2: 8.75 tỷ (50%) — sau lắp đặt và test factory acceptance\n"
            "Đợt 3: 5.25 tỷ (30%) — sau nghiệm thu lâm sàng"
        ),
        status="Under Review",
        approver="Administrator",
    )
    set_status("Procurement Plan Item", ppi.name, status="PO Raised", por_reference=por.name)
    print(f"  NA: {na.name} | PP: {pp.name} | VE: {ve.name}")
    print(f"  POR: {por.name} — 17.5 tỷ, requires_director_approval=1, Under Review ✓")
