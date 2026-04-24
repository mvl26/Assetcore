"""Seed script IMM-01→03: xoá data test, tạo 5 kịch bản thực tế."""
import frappe
from frappe.utils import today, add_days, add_months

frappe.init(site='assetcore')
frappe.connect()
frappe.set_user("Administrator")


def delete_all(doctype):
    names = frappe.get_all(doctype, pluck="name")
    for n in names:
        frappe.delete_doc(doctype, n, force=True, ignore_missing=True)
    frappe.db.commit()


def ins(doctype, **kwargs):
    doc = frappe.get_doc({"doctype": doctype, **kwargs})
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc


def sv(doctype, name, **fields):
    frappe.db.set_value(doctype, name, fields)
    frappe.db.commit()


def add_child(doctype, parent_name, parent_doctype, **kwargs):
    doc = frappe.get_doc({
        "doctype": doctype,
        "parent": parent_name,
        "parentfield": "items",
        "parenttype": parent_doctype,
        **kwargs,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc


# ─── 1. Xoá toàn bộ data cũ ──────────────────────────────────────────────────

print("── Xoá data cũ ─────────────────────────────────────────────────────────")
for dt in [
    "Purchase Order Request", "Vendor Evaluation Item", "Vendor Evaluation",
    "Technical Specification", "Procurement Plan Item",
    "Procurement Plan", "Needs Assessment",
]:
    cnt = frappe.db.count(dt)
    delete_all(dt)
    print(f"  Xoá {cnt:>3}  {dt}")


# ─── 2. Cập nhật Supplier ─────────────────────────────────────────────────────

print("\n── Cập nhật Master Data (Supplier) ─────────────────────────────────────")
sup_patches = {
    "AC-SUP-2026-0001": dict(
        supplier_name="MedEquip Vietnam JSC",
        vendor_type="Manufacturer", country="Vietnam",
        email_id="sales@medequip.vn", phone="024-3825-1100",
        local_representative="Nguyễn Văn Hùng",
        iso_13485_cert="ISO13485-VN-0042", iso_13485_expiry=add_months(today(), 18),
        contract_start="2025-01-01", contract_end="2027-12-31",
        contract_value=15_000_000_000, is_active=1,
    ),
    "AC-SUP-2026-0002": dict(
        supplier_name="BioService Medical Co., Ltd",
        vendor_type="Service", country="Vietnam",
        email_id="contract@bioservice.vn", phone="028-3930-5500",
        local_representative="Trần Thị Mai",
        iso_13485_cert="ISO13485-VN-0089", iso_13485_expiry=add_months(today(), 12),
        contract_start="2024-07-01", contract_end="2026-06-30",
        contract_value=4_500_000_000, is_active=1,
    ),
    "AC-SUP-2026-0003": dict(
        supplier_name="VietCal Metrology Lab",
        vendor_type="Calibration Lab", country="Vietnam",
        email_id="info@vietcal.vn", phone="024-3556-7700",
        local_representative="Lê Quang Minh",
        iso_17025_cert="VIVAL-17025-0031", iso_17025_expiry=add_months(today(), 24),
        is_active=1,
    ),
}
for name, vals in sup_patches.items():
    if frappe.db.exists("AC Supplier", name):
        frappe.db.set_value("AC Supplier", name, vals)

# Philips — tạo nếu chưa có
philips_list = frappe.get_all("AC Supplier", filters={"supplier_name": ["like", "%Philips%"]}, pluck="name")
if philips_list:
    SUP_PHILIPS = philips_list[0]
else:
    p = ins("AC Supplier",
        supplier_name="Philips Medical Vietnam LLC",
        vendor_type="Manufacturer", country="Netherlands",
        email_id="vn.medical@philips.com", phone="028-3823-9900",
        local_representative="Phạm Đức Khoa",
        iso_13485_cert="ISO13485-EU-0017", iso_13485_expiry=add_months(today(), 30),
        contract_start="2025-06-01", contract_end="2028-05-31",
        contract_value=28_000_000_000, is_active=1,
    )
    SUP_PHILIPS = p.name

frappe.db.commit()
print(f"  4 suppliers OK | Philips = {SUP_PHILIPS}")


# ─── Kịch bản A: Máy thở ICU — Happy Path NA→PP→TS→VE→POR Released ──────────

print("\n── A: Máy thở ICU (Happy Path hoàn chỉnh) ──────────────────────────────")

na_a = ins("Needs Assessment",
    requesting_dept="AC-DEPT-0001",
    request_date="2026-01-05",
    requested_by="Administrator",
    equipment_type="Máy thở cao cấp ICU Ventilator",
    quantity=2,
    priority="Critical",
    estimated_budget=3_200_000_000,
    current_equipment_age=9,
    failure_frequency="Constant",
    clinical_justification=(
        "Hai máy thở Drager Evita 4 hiện tại đã hoạt động 9 năm (vượt vòng đời khuyến nghị 7 năm). "
        "Tần suất hỏng hóc 8 lần trong 12 tháng qua, gây gián đoạn chăm sóc bệnh nhân nặng. "
        "ICU 16 giường đang vận hành tỷ lệ lấp đầy 92%. Cần 2 máy thở thế hệ mới "
        "hỗ trợ đầy đủ các mode SIMV, PSV, APRV và NIV để đáp ứng yêu cầu lâm sàng."
    ),
    status="Approved",
    approved_budget=3_200_000_000,
    htmreview_notes=(
        "Đã kiểm tra hiện trạng 2 máy thở tại ICU. Xác nhận xuống cấp nghiêm trọng, "
        "nhiều linh kiện không còn sản xuất. Khuyến nghị thay thế ngay trong Q1/2026."
    ),
    finance_notes="Ngân sách Q1/2026 đã được HĐQT phê duyệt trong kế hoạch đầu tư TSCĐ.",
)
print(f"  NA: {na_a.name} — Approved")

pp_a = ins("Procurement Plan",
    plan_year=2026,
    approved_budget=3_500_000_000,
    allocated_budget=3_200_000_000,
    remaining_budget=300_000_000,
    status="Budget Locked",
    approved_by="Administrator",
    approval_date="2026-01-15",
    approval_notes="Kế hoạch Q1/2026 — thiết bị hồi sức tích cực. Nguồn ngân sách TSCĐ.",
)
ppi_a = add_child("Procurement Plan Item", pp_a.name, "Procurement Plan",
    needs_assessment=na_a.name,
    equipment_description="Máy thở cao cấp ICU (Hamilton G5 Pro hoặc tương đương)",
    quantity=2,
    estimated_unit_cost=1_600_000_000,
    total_cost=3_200_000_000,
    priority="Critical",
    planned_quarter="Q1",
    status="Pending",
)
print(f"  PP: {pp_a.name} Budget Locked | PPI: {ppi_a.name}")

ts_a = ins("Technical Specification",
    needs_assessment=na_a.name,
    equipment_description="Máy thở cao cấp ICU — Hamilton G5 Pro hoặc tương đương",
    status="Approved",
    regulatory_class="Class C",
    mdd_class="Class IIb",
    procurement_method="Tender",
    reference_price_estimate=3_200_000_000,
    expected_delivery_weeks=10,
    performance_requirements=(
        "<p><strong>Mode hô hấp bắt buộc:</strong> VCV, PCV, SIMV, PSV, APRV, CPAP, NIV</p>"
        "<p><strong>Thông số kỹ thuật:</strong></p><ul>"
        "<li>Tidal volume: 20–2000 mL, độ chính xác ±5%</li>"
        "<li>Áp lực hít vào: 5–80 cmH₂O</li>"
        "<li>FiO₂: 21–100%, blender oxy tích hợp</li>"
        "<li>Màn hình cảm ứng ≥15 inch, hiển thị waveform và pressure-volume loop</li>"
        "<li>Pin dự phòng ≥4 giờ vận hành liên tục</li>"
        "<li>Kết nối HL7/FHIR với HIS</li></ul>"
    ),
    safety_standards="IEC 60601-1 | ISO 80601-2-12 | EN 794-3",
    reference_standard="ISO 80601-2-12:2011 — Medical electrical equipment: Ventilators for critical care",
    warranty_terms="24 tháng bảo hành toàn bộ phần cứng, cam kết uptime ≥98%",
    training_requirements="Đào tạo bác sĩ ICU và điều dưỡng 3 ngày tại chỗ, cấp chứng chỉ vận hành",
    reviewed_by="Administrator",
    review_date="2026-01-20",
    review_notes="Đặc tả phù hợp yêu cầu lâm sàng ICU tuyến trung ương.",
)
print(f"  TS: {ts_a.name} — Approved")

ve_a = ins("Vendor Evaluation",
    linked_plan=pp_a.name,
    linked_technical_spec=ts_a.name,
    evaluation_date="2026-02-10",
    bid_issue_date="2026-01-25",
    bid_closing_date="2026-02-07",
    bid_opening_date="2026-02-08",
    bids_received_count=2,
    status="Approved",
    recommended_vendor="AC-SUP-2026-0001",
    selection_justification=(
        "MedEquip Vietnam JSC đạt tổng điểm cao nhất (87/100), đáp ứng toàn bộ yêu cầu kỹ thuật TS. "
        "Có kinh nghiệm triển khai >30 máy thở tại bệnh viện tuyến trung ương. "
        "Sản phẩm Hamilton G5 Pro đạt điểm kỹ thuật 88/100, giao hàng 10 tuần trong hạn. "
        "Giá chào hàng 3.0 tỷ VNĐ nằm trong ngân sách được phê duyệt (3.2 tỷ)."
    ),
    committee_members="Administrator; Trưởng khoa ICU; Trưởng phòng VTBM; Trưởng phòng Tài chính",
    tech_reviewed_by="Administrator",
    tech_review_date="2026-02-09",
    approved_by="Administrator",
    approval_date="2026-02-12",
    unsuccessful_vendor_notified=1,
)
add_child("Vendor Evaluation Item", ve_a.name, "Vendor Evaluation",
    vendor="AC-SUP-2026-0001", vendor_name="MedEquip Vietnam JSC",
    quoted_price=3_000_000_000,
    technical_score=88, financial_score=82, profile_score=90, risk_score=85, total_score=87,
    score_band="A (≥8)",
    compliant_with_ts=1, has_nd98_registration=1, bid_compliant=1,
    quoted_delivery_weeks=10, offered_payment_terms="30% tạm ứng, 70% sau nghiệm thu",
    is_recommended=1,
    notes="Hamilton G5 Pro — đủ spec, đội kỹ thuật tại chỗ trong 24h, đào tạo onsite 3 ngày.",
)
add_child("Vendor Evaluation Item", ve_a.name, "Vendor Evaluation",
    vendor="AC-SUP-2026-0002", vendor_name="BioService Medical Co., Ltd",
    quoted_price=2_800_000_000,
    technical_score=72, financial_score=90, profile_score=70, risk_score=68, total_score=74,
    score_band="B (6–7.9)",
    compliant_with_ts=1, has_nd98_registration=1, bid_compliant=1,
    quoted_delivery_weeks=14, offered_payment_terms="50% tạm ứng, 50% sau lắp đặt",
    is_recommended=0,
    notes="Giá thấp hơn 200M nhưng điểm kỹ thuật thấp, giao hàng chậm hơn 4 tuần.",
)
print(f"  VE: {ve_a.name} — Approved | MedEquip recommended")

por_a = ins("Purchase Order Request",
    linked_plan_item=ppi_a.name,
    procurement_plan=pp_a.name,
    linked_evaluation=ve_a.name,
    vendor="AC-SUP-2026-0001",
    vendor_name="MedEquip Vietnam JSC",
    equipment_description="Máy thở cao cấp ICU Hamilton G5 Pro x2",
    quantity=2,
    unit_price=1_500_000_000,
    total_amount=3_000_000_000,
    delivery_terms="DAP Bệnh viện, bao gồm lắp đặt và đào tạo vận hành tại chỗ",
    incoterms="DAP",
    payment_terms="30% tạm ứng sau ký HĐ, 70% sau nghiệm thu kỹ thuật",
    expected_delivery_date=add_days(today(), 70),
    warranty_period_months=24,
    payment_schedule_notes=(
        "Đợt 1: 900.000.000 VNĐ (30%) — sau ký hợp đồng\n"
        "Đợt 2: 2.100.000.000 VNĐ (70%) — sau nghiệm thu kỹ thuật và bàn giao"
    ),
    status="Draft",
)
sv("Purchase Order Request", por_a.name,
    status="Approved", approved_by="Administrator", approval_date="2026-02-20")
sv("Purchase Order Request", por_a.name,
    status="Released", released_by="Administrator", release_date="2026-02-21")
sv("Procurement Plan Item", ppi_a.name, status="PO Raised", por_reference=por_a.name)
print(f"  POR: {por_a.name} — Released ✓  (Kịch bản A hoàn chỉnh)")


# ─── Kịch bản B: CĐHA — Multi-item PP, 2 NA → 1 VE → 2 POR Draft ─────────────

print("\n── B: Chẩn đoán Hình ảnh (2 NA → 1 PP 2 items → VE → 2 POR Draft) ──────")

na_b1 = ins("Needs Assessment",
    requesting_dept="AC-DEPT-0002",
    request_date="2026-01-10",
    requested_by="Administrator",
    equipment_type="Máy X-quang kỹ thuật số DR",
    quantity=1, priority="High",
    estimated_budget=2_500_000_000,
    current_equipment_age=11,
    failure_frequency="Frequently",
    clinical_justification=(
        "Máy X-quang CR hiện tại (2015) hết hỗ trợ kỹ thuật từ nhà sản xuất tháng 12/2024. "
        "Chất lượng ảnh suy giảm, không đạt tiêu chuẩn chẩn đoán hiện đại. "
        "Nâng cấp lên DR (Digital Radiography) giảm liều phóng xạ 40% và rút ngắn quy trình chụp từ 5 phút xuống 30 giây."
    ),
    status="Approved", approved_budget=2_500_000_000,
    htmreview_notes="Máy vượt vòng đời, không còn linh kiện thay thế. Ưu tiên cao cho Q2/2026.",
    finance_notes="Phê duyệt ngân sách từ nguồn đầu tư TSCĐ Q2/2026.",
)

na_b2 = ins("Needs Assessment",
    requesting_dept="AC-DEPT-0002",
    request_date="2026-01-12",
    requested_by="Administrator",
    equipment_type="Máy siêu âm 4D Doppler màu",
    quantity=2, priority="High",
    estimated_budget=2_400_000_000,
    current_equipment_age=7,
    failure_frequency="Occasionally",
    clinical_justification=(
        "3 máy siêu âm 2D hiện tại không hỗ trợ Doppler màu và 4D. "
        "Nhu cầu siêu âm tim mạch và sản khoa 4D tăng 35% trong 2 năm qua (từ 800 lên 1.080 ca/tháng). "
        "Bổ sung 2 máy siêu âm cao cấp 4D đáp ứng đủ lịch hẹn và nâng cao chất lượng chẩn đoán tim bẩm sinh."
    ),
    status="Approved", approved_budget=2_400_000_000,
    htmreview_notes="Xác nhận nhu cầu lâm sàng — khuyến nghị đầu tư Q2/2026.",
    finance_notes="Phê duyệt ngân sách từ nguồn đầu tư TSCĐ Q2/2026.",
)
print(f"  NA-DR: {na_b1.name} | NA-Siêu âm: {na_b2.name}")

pp_b = ins("Procurement Plan",
    plan_year=2026,
    approved_budget=5_200_000_000,
    allocated_budget=4_900_000_000,
    remaining_budget=300_000_000,
    status="Budget Locked",
    approved_by="Administrator",
    approval_date="2026-02-01",
    approval_notes="Kế hoạch Q2/2026 — nâng cấp thiết bị chẩn đoán hình ảnh.",
)
ppi_b1 = add_child("Procurement Plan Item", pp_b.name, "Procurement Plan",
    needs_assessment=na_b1.name,
    equipment_description="Máy X-quang kỹ thuật số DR treo trần (Fixed DR System)",
    quantity=1, estimated_unit_cost=2_500_000_000, total_cost=2_500_000_000,
    priority="High", planned_quarter="Q2", status="Pending",
)
ppi_b2 = add_child("Procurement Plan Item", pp_b.name, "Procurement Plan",
    needs_assessment=na_b2.name,
    equipment_description="Máy siêu âm 4D Doppler màu (Premium Ultrasound System)",
    quantity=2, estimated_unit_cost=1_200_000_000, total_cost=2_400_000_000,
    priority="High", planned_quarter="Q2", status="Pending",
)
print(f"  PP: {pp_b.name} Budget Locked | Items: {ppi_b1.name} (DR), {ppi_b2.name} (Siêu âm)")

ts_b = ins("Technical Specification",
    needs_assessment=na_b1.name,
    equipment_description="Thiết bị CĐHA — X-quang DR treo trần & Siêu âm 4D Doppler màu",
    status="Approved",
    regulatory_class="Class C",
    mdd_class="Class IIb",
    procurement_method="Tender",
    reference_price_estimate=4_900_000_000,
    expected_delivery_weeks=12,
    performance_requirements=(
        "<p><strong>DR (Digital Radiography):</strong></p><ul>"
        "<li>Detector FPD 43×43cm, độ phân giải ≥3.4 lp/mm</li>"
        "<li>Liều bức xạ ≤1.5 mGy/image ở chế độ chuẩn</li>"
        "<li>Kết nối DICOM 3.0, tích hợp PACS</li></ul>"
        "<p><strong>Siêu âm 4D:</strong></p><ul>"
        "<li>≥4 đầu dò tích hợp (tim, bụng, cơ xương, nông)</li>"
        "<li>4D real-time, Doppler màu + PW/CW</li>"
        "<li>Kết nối PACS/DICOM, lưu trữ clip video</li></ul>"
    ),
    safety_standards="IEC 60601-1 | IEC 60601-1-3 (DR) | IEC 60601-2-37 (Siêu âm)",
    reference_standard="NEMA XR-29:2013 (DR) | IEC 61157:2007 (Siêu âm)",
    warranty_terms="24 tháng bảo hành toàn phần, cam kết uptime ≥96%",
    training_requirements="Đào tạo KTBM và kỹ thuật viên hình ảnh 5 ngày tại chỗ",
    reviewed_by="Administrator",
    review_date="2026-02-05",
    review_notes="Đặc tả phù hợp yêu cầu nâng cấp toàn bộ phòng CĐHA.",
)

ve_b = ins("Vendor Evaluation",
    linked_plan=pp_b.name,
    linked_technical_spec=ts_b.name,
    evaluation_date="2026-03-05",
    bid_issue_date="2026-02-10",
    bid_closing_date="2026-03-01",
    bid_opening_date="2026-03-02",
    bids_received_count=2,
    status="Approved",
    recommended_vendor=SUP_PHILIPS,
    selection_justification=(
        "Philips Medical Vietnam đạt tổng điểm 91/100 — cao nhất. "
        "DR DigitalDiagnost C90 đáp ứng 97% yêu cầu kỹ thuật DR. "
        "Siêu âm EPIQ Elite hỗ trợ đầy đủ 4D, Doppler màu, AI tim mạch tích hợp. "
        "Đội ứng cứu kỹ thuật tại chỗ trong 4h. Giá cao hơn MedEquip 6.5% nhưng chất lượng và dịch vụ hậu mãi vượt trội."
    ),
    committee_members="Administrator; Trưởng khoa CĐHA; Trưởng phòng VTBM; Trưởng phòng Tài chính",
    tech_reviewed_by="Administrator",
    tech_review_date="2026-03-04",
    approved_by="Administrator",
    approval_date="2026-03-07",
    unsuccessful_vendor_notified=1,
)
add_child("Vendor Evaluation Item", ve_b.name, "Vendor Evaluation",
    vendor=SUP_PHILIPS, vendor_name="Philips Medical Vietnam LLC",
    quoted_price=4_900_000_000,
    technical_score=93, financial_score=85, profile_score=95, risk_score=90, total_score=91,
    score_band="A (≥8)",
    compliant_with_ts=1, has_nd98_registration=1, bid_compliant=1,
    quoted_delivery_weeks=12, offered_payment_terms="25% tạm ứng, 75% sau nghiệm thu",
    is_recommended=1,
    notes="DR: DigitalDiagnost C90 | Siêu âm: EPIQ Elite. Đào tạo onsite 5 ngày, hotline 24/7.",
)
add_child("Vendor Evaluation Item", ve_b.name, "Vendor Evaluation",
    vendor="AC-SUP-2026-0001", vendor_name="MedEquip Vietnam JSC",
    quoted_price=4_600_000_000,
    technical_score=78, financial_score=92, profile_score=75, risk_score=72, total_score=79,
    score_band="B (6–7.9)",
    compliant_with_ts=1, has_nd98_registration=1, bid_compliant=1,
    quoted_delivery_weeks=16, offered_payment_terms="40% tạm ứng, 60% sau nghiệm thu",
    is_recommended=0,
    notes="Giá cạnh tranh hơn 300M nhưng điểm kỹ thuật thấp, giao hàng chậm hơn 4 tuần.",
)
print(f"  VE: {ve_b.name} — Approved | Philips recommended")

por_b1 = ins("Purchase Order Request",
    linked_plan_item=ppi_b1.name, procurement_plan=pp_b.name, linked_evaluation=ve_b.name,
    vendor=SUP_PHILIPS, vendor_name="Philips Medical Vietnam LLC",
    equipment_description="Máy X-quang DR treo trần Philips DigitalDiagnost C90",
    quantity=1, unit_price=2_400_000_000, total_amount=2_400_000_000,
    delivery_terms="DAP Bệnh viện, bao gồm lắp đặt phòng X-quang và hiệu chỉnh",
    incoterms="DAP", payment_terms="25% tạm ứng, 75% sau nghiệm thu kỹ thuật",
    expected_delivery_date=add_days(today(), 84),
    warranty_period_months=24, status="Draft",
)
sv("Procurement Plan Item", ppi_b1.name, status="PO Raised", por_reference=por_b1.name)

por_b2 = ins("Purchase Order Request",
    linked_plan_item=ppi_b2.name, procurement_plan=pp_b.name, linked_evaluation=ve_b.name,
    vendor=SUP_PHILIPS, vendor_name="Philips Medical Vietnam LLC",
    equipment_description="Máy siêu âm 4D Doppler màu Philips EPIQ Elite x2",
    quantity=2, unit_price=1_150_000_000, total_amount=2_300_000_000,
    delivery_terms="DAP Bệnh viện, đào tạo vận hành 3 ngày/máy cho kỹ thuật viên",
    incoterms="DAP", payment_terms="25% tạm ứng, 75% sau nghiệm thu kỹ thuật",
    expected_delivery_date=add_days(today(), 84),
    warranty_period_months=24, status="Draft",
)
sv("Procurement Plan Item", ppi_b2.name, status="PO Raised", por_reference=por_b2.name)
print(f"  POR-DR: {por_b1.name} Draft | POR-Siêu âm: {por_b2.name} Draft")


# ─── Kịch bản C: NA bị từ chối — ECG dư thừa ─────────────────────────────────

print("\n── C: NA Rejected — CCU yêu cầu ECG nhưng đã đủ thiết bị ─────────────")

na_c = ins("Needs Assessment",
    requesting_dept="AC-DEPT-0003",
    request_date="2026-01-18",
    requested_by="Administrator",
    equipment_type="Máy điện tim 12 kênh (ECG)",
    quantity=3, priority="Medium",
    estimated_budget=180_000_000,
    current_equipment_age=4,
    failure_frequency="Rarely",
    clinical_justification=(
        "Khoa CCU đề xuất bổ sung 3 máy ECG 12 kênh để tăng năng lực tiếp nhận bệnh nhân đau ngực cấp. "
        "Hiện tại khoa có 5 máy ECG đang hoạt động tốt."
    ),
    status="Rejected",
    htmreview_notes=(
        "Kiểm tra tại chỗ ngày 2026-01-22: 5/5 máy ECG GE MAC 5500 đang hoạt động bình thường, "
        "tuổi đời trung bình 4 năm. Tỷ lệ sử dụng 60%, không có tình trạng chờ đợi thiết bị. "
        "Không có chỉ định thay thế hoặc bổ sung theo tiêu chuẩn WHO HTM."
    ),
    finance_notes="Không phê duyệt — thiết bị hiện tại đủ năng lực phục vụ.",
    reject_reason=(
        "Từ chối theo khuyến nghị HTM (2026-01-23):\n"
        "• 5 máy ECG hiện tại còn hoạt động tốt, tỷ lệ sử dụng chỉ 60%\n"
        "• Không có dữ liệu về tình trạng chờ đợi thiết bị trong 12 tháng qua\n"
        "• Ngân sách Q1/2026 ưu tiên cho hạng mục cấp thiết hơn (máy thở ICU)\n"
        "Khuyến nghị: Khoa CCU đề xuất lại Q4/2026 kèm báo cáo tải trọng thực tế và số liệu thời gian chờ đợi."
    ),
)
print(f"  NA: {na_c.name} — ECG Rejected ✓")


# ─── Kịch bản D: Dao mổ điện — Waiver vendor khác NCC đề xuất ────────────────

print("\n── D: ESU Phòng mổ — Waiver chọn NCC khác đề xuất (VR-03-07) ───────────")

na_d = ins("Needs Assessment",
    requesting_dept="AC-DEPT-0005",
    request_date="2026-02-01",
    requested_by="Administrator",
    equipment_type="Dao mổ điện đa năng (Electrosurgical Unit — ESU)",
    quantity=2, priority="High",
    estimated_budget=600_000_000,
    current_equipment_age=8,
    failure_frequency="Frequently",
    clinical_justification=(
        "Dao mổ điện Valleylab Force FX (lắp đặt 2016) đã vượt vòng đời thiết kế 7 năm. "
        "Hỏng hóc 4 lần trong năm 2025, trong đó 3 lần gây trì hoãn ca phẫu thuật khẩn. "
        "Phòng mổ cần 2 ESU mới hỗ trợ đốt điện độc lập hai cực (bipolar) và đốt plasma argon (APC)."
    ),
    status="Approved", approved_budget=600_000_000,
    htmreview_notes="Xác nhận thiết bị xuống cấp, tiềm ẩn rủi ro an toàn bệnh nhân. Ưu tiên Q2/2026.",
    finance_notes="Phê duyệt từ nguồn dự phòng sửa chữa thiết bị.",
)

pp_d = ins("Procurement Plan",
    plan_year=2026,
    approved_budget=700_000_000, allocated_budget=600_000_000, remaining_budget=100_000_000,
    status="Budget Locked",
    approved_by="Administrator", approval_date="2026-02-10",
    approval_notes="Thay thế ESU khẩn cấp — Phòng mổ.",
)
ppi_d = add_child("Procurement Plan Item", pp_d.name, "Procurement Plan",
    needs_assessment=na_d.name,
    equipment_description="Dao mổ điện đa năng ESU (Valleylab FT10 hoặc tương đương)",
    quantity=2, estimated_unit_cost=300_000_000, total_cost=600_000_000,
    priority="High", planned_quarter="Q2", status="Pending",
)

ts_d = ins("Technical Specification",
    needs_assessment=na_d.name,
    equipment_description="Dao mổ điện đa năng (Electrosurgical Unit — ESU)",
    status="Approved",
    regulatory_class="Class C",
    mdd_class="Class IIb",
    procurement_method="RFQ",
    reference_price_estimate=600_000_000,
    expected_delivery_weeks=8,
    performance_requirements=(
        "<ul><li>Công suất cắt: ≥300W (monopolar), ≥120W (bipolar)</li>"
        "<li>Hỗ trợ argon plasma coagulation (APC) tùy chọn</li>"
        "<li>Hệ thống kiểm tra tiếp xúc điện cực liên tục (CEM/RCMP)</li>"
        "<li>Màn hình LED rõ ràng, cài đặt từ 1 điểm vận hành</li>"
        "<li>Pedal foot switch tích hợp</li></ul>"
    ),
    safety_standards="IEC 60601-1 | IEC 60601-2-2 | NFPA 99",
    warranty_terms="24 tháng bảo hành toàn phần, hợp đồng bảo trì toàn diện",
    training_requirements="Đào tạo kỹ thuật viên phòng mổ 1 ngày, cấp tài liệu vận hành tiếng Việt",
    reviewed_by="Administrator",
    review_date="2026-02-15",
)

ve_d = ins("Vendor Evaluation",
    linked_plan=pp_d.name,
    linked_technical_spec=ts_d.name,
    evaluation_date="2026-03-10",
    bid_issue_date="2026-02-18",
    bid_closing_date="2026-03-08",
    bid_opening_date="2026-03-09",
    bids_received_count=2,
    status="Approved",
    recommended_vendor="AC-SUP-2026-0001",
    selection_justification=(
        "MedEquip Vietnam đạt điểm kỹ thuật cao nhất (84/100). "
        "Tuy nhiên, Trưởng phòng mổ đề xuất ưu tiên BioService Medical do hợp đồng bảo hành toàn diện "
        "đang chạy cho toàn bộ phòng mổ (2024–2026), giúp tối ưu chi phí vận hành. "
        "Hội đồng chấp thuận với biên bản miễn trừ VR-03-07 đầy đủ."
    ),
    committee_members="Administrator; Trưởng phòng Mổ; Trưởng phòng VTBM; Phòng Tài chính",
    tech_reviewed_by="Administrator",
    tech_review_date="2026-03-09",
    approved_by="Administrator",
    approval_date="2026-03-12",
    unsuccessful_vendor_notified=1,
)
add_child("Vendor Evaluation Item", ve_d.name, "Vendor Evaluation",
    vendor="AC-SUP-2026-0001", vendor_name="MedEquip Vietnam JSC",
    quoted_price=590_000_000,
    technical_score=85, financial_score=88, profile_score=82, risk_score=80, total_score=84,
    score_band="B (6–7.9)",
    compliant_with_ts=1, has_nd98_registration=1, bid_compliant=1,
    quoted_delivery_weeks=8, offered_payment_terms="40% tạm ứng, 60% sau nghiệm thu",
    is_recommended=1,
    notes="Medtronic Force FX-8C — đúng spec, giao 8 tuần.",
)
add_child("Vendor Evaluation Item", ve_d.name, "Vendor Evaluation",
    vendor="AC-SUP-2026-0002", vendor_name="BioService Medical Co., Ltd",
    quoted_price=620_000_000,
    technical_score=80, financial_score=80, profile_score=85, risk_score=88, total_score=82,
    score_band="B (6–7.9)",
    compliant_with_ts=1, has_nd98_registration=1, bid_compliant=1,
    quoted_delivery_weeks=6, offered_payment_terms="Thanh toán 1 lần sau nghiệm thu bàn giao",
    is_recommended=0,
    notes="Erbe VIO 3 — giao nhanh 6 tuần, có HĐ bảo hành toàn diện phòng mổ đang chạy.",
)
print(f"  VE: {ve_d.name} — Approved | MedEquip recommended")

# POR với waiver — chọn BioService thay vì MedEquip được đề xuất
por_d = ins("Purchase Order Request",
    linked_plan_item=ppi_d.name, procurement_plan=pp_d.name, linked_evaluation=ve_d.name,
    vendor="AC-SUP-2026-0002", vendor_name="BioService Medical Co., Ltd",
    equipment_description="Dao mổ điện đa năng Erbe VIO 3 x2 — Waiver VR-03-07",
    quantity=2, unit_price=310_000_000, total_amount=620_000_000,
    delivery_terms="DAP Bệnh viện, lắp đặt và kiểm định điện an toàn tại chỗ",
    incoterms="DAP",
    payment_terms="Thanh toán 1 lần sau nghiệm thu và bàn giao",
    expected_delivery_date=add_days(today(), 42),
    warranty_period_months=24,
    cancellation_reason=(
        "VR-03-07 WAIVER — Lý do chọn BioService Medical thay vì MedEquip Vietnam (NCC đề xuất từ VE):\n\n"
        "1. Tối ưu chi phí vận hành: BioService đang thực hiện HĐ bảo hành toàn diện phòng mổ (2024–2026), "
        "việc bổ sung ESU vào hợp đồng hiện có tiết kiệm ước tính 85 triệu VNĐ/năm chi phí bảo trì.\n\n"
        "2. Năng lực kỹ thuật tại chỗ: Đội kỹ thuật BioService đã quen thiết bị phòng mổ tại bệnh viện, "
        "thời gian phản hồi ứng cứu thực tế <2h (nhanh hơn cam kết hợp đồng).\n\n"
        "3. Erbe VIO 3 đáp ứng đầy đủ yêu cầu kỹ thuật TS, giao hàng nhanh hơn 2 tuần so với MedEquip.\n\n"
        "Biên bản miễn trừ VR-03-07 đã được ký bởi Trưởng phòng VTBM và Giám đốc BV ngày 2026-03-11."
    ),
    status="Draft",
)
sv("Procurement Plan Item", ppi_d.name, status="PO Raised", por_reference=por_d.name)
print(f"  POR: {por_d.name} — Waiver BioService (Draft) ✓")


# ─── Kịch bản E: MRI 1.5T — POR vượt 500M cần Giám đốc duyệt ───────────────

print("\n── E: MRI 1.5T — 17.5 tỷ, requires_director_approval, Under Review ──────")

na_e = ins("Needs Assessment",
    requesting_dept="AC-DEPT-0001",
    request_date="2026-02-15",
    requested_by="Administrator",
    equipment_type="Máy cộng hưởng từ MRI 1.5 Tesla",
    quantity=1, priority="Critical",
    estimated_budget=18_000_000_000,
    current_equipment_age=0,
    failure_frequency="Rarely",
    clinical_justification=(
        "Bệnh viện hiện chưa có MRI, toàn bộ bệnh nhân cần chụp MRI phải chuyển viện hoặc tự đến cơ sở khác. "
        "Thống kê 2025: 1.240 ca chuyển viện để chụp MRI, chi phí vận chuyển và chậm trễ chẩn đoán "
        "ước tính 4,2 tỷ VNĐ/năm. Đầu tư MRI 1.5T dự kiến hoàn vốn trong 4,3 năm "
        "dựa trên công suất 15 ca/ngày tại mức giá dịch vụ hiện hành."
    ),
    status="Approved", approved_budget=18_000_000_000,
    htmreview_notes=(
        "Đánh giá nhu cầu đạt — MRI 1.5T phù hợp quy mô bệnh viện 500 giường tuyến tỉnh. "
        "Đề xuất ưu tiên hệ thống ZBO (Zero Boil-Off) để giảm chi phí vận hành helium lỏng."
    ),
    finance_notes="Phê duyệt bởi HĐQT — Nghị quyết số 05/2026/NQ-HĐQT ngày 2026-02-14.",
)

pp_e = ins("Procurement Plan",
    plan_year=2026,
    approved_budget=20_000_000_000, allocated_budget=18_000_000_000, remaining_budget=2_000_000_000,
    status="Budget Locked",
    approved_by="Administrator", approval_date="2026-03-01",
    approval_notes="Dự án MRI — phê duyệt theo Nghị quyết HĐQT 05/2026. Nguồn: vay ngân hàng + TSCĐ.",
)
ppi_e = add_child("Procurement Plan Item", pp_e.name, "Procurement Plan",
    needs_assessment=na_e.name,
    equipment_description="Hệ thống MRI 1.5 Tesla toàn thân (Philips Ingenia Ambition hoặc tương đương)",
    quantity=1, estimated_unit_cost=18_000_000_000, total_cost=18_000_000_000,
    priority="Critical", planned_quarter="Q3", status="Pending",
)

ts_e = ins("Technical Specification",
    needs_assessment=na_e.name,
    equipment_description="Máy cộng hưởng từ MRI 1.5 Tesla — toàn thân",
    status="Approved",
    regulatory_class="Class C",
    mdd_class="Class IIb",
    procurement_method="Tender",
    reference_price_estimate=18_000_000_000,
    expected_delivery_weeks=24,
    performance_requirements=(
        "<p><strong>Thông số kỹ thuật bắt buộc:</strong></p><ul>"
        "<li>Từ trường 1.5 Tesla, siêu dẫn, hoạt động liên tục 24/7</li>"
        "<li>Bore ≥70 cm, chiều dài bore ≤163 cm (thiết kế bore ngắn)</li>"
        "<li>Gradient ≥45 mT/m, slew rate ≥200 T/m/s</li>"
        "<li>Hỗ trợ chuỗi xung: T1, T2, PD, FLAIR, DWI, MRA, MRS, fMRI, DTI</li>"
        "<li>Hệ thống làm lạnh helium closed-loop (Zero Boil-Off — ZBO)</li>"
        "<li>Phần mềm post-processing tim mạch, thần kinh học</li></ul>"
    ),
    safety_standards="IEC 60601-2-33 | NEMA MS 1 | ASTM F2052 (RF shielding)",
    reference_standard="IEC 60601-2-33:2010+A2:2015 — Safety of MR equipment",
    warranty_terms="24 tháng bảo hành toàn bộ, cam kết uptime ≥95%, ứng cứu trong 8h",
    site_requirements="Phòng máy chuyên dụng, sàn tải trọng ≥800 kg/m², hệ thống điều hòa chuyên dụng, RF shielding",
    training_requirements="Đào tạo 2 tuần tại bệnh viện cho BS chẩn đoán hình ảnh và KTBM, cấp chứng chỉ vận hành",
    reviewed_by="Administrator",
    review_date="2026-03-10",
    review_notes="Đặc tả phù hợp, ưu tiên hệ thống ZBO để giảm chi phí vận hành helium dài hạn.",
)

ve_e = ins("Vendor Evaluation",
    linked_plan=pp_e.name,
    linked_technical_spec=ts_e.name,
    evaluation_date="2026-04-05",
    bid_issue_date="2026-03-05",
    bid_closing_date="2026-04-01",
    bid_opening_date="2026-04-02",
    bids_received_count=2,
    status="Approved",
    recommended_vendor=SUP_PHILIPS,
    selection_justification=(
        "Philips Medical Vietnam đạt tổng điểm cao nhất (89/100). "
        "MRI Ingenia Ambition 1.5T có ZBO helium (tiết kiệm ~200 triệu VNĐ/năm chi phí helium lỏng), "
        "bore 70cm thân thiện bệnh nhân, phần mềm dStream Anatomical Intelligence hỗ trợ AI chẩn đoán. "
        "Giá 17.5 tỷ trong ngân sách (18 tỷ được duyệt). "
        "MedEquip Vietnam đạt 75/100, thiếu ZBO, giao hàng chậm hơn 4 tuần."
    ),
    committee_members="Administrator; Giám đốc BV; Trưởng phòng VTBM; Trưởng phòng Tài chính; Tư vấn kỹ thuật độc lập (NIMPE)",
    tech_reviewed_by="Administrator",
    tech_review_date="2026-04-03",
    approved_by="Administrator",
    approval_date="2026-04-07",
    unsuccessful_vendor_notified=1,
)
add_child("Vendor Evaluation Item", ve_e.name, "Vendor Evaluation",
    vendor=SUP_PHILIPS, vendor_name="Philips Medical Vietnam LLC",
    quoted_price=17_500_000_000,
    technical_score=92, financial_score=88, profile_score=90, risk_score=85, total_score=89,
    score_band="A (≥8)",
    compliant_with_ts=1, has_nd98_registration=1, bid_compliant=1,
    quoted_delivery_weeks=24, offered_payment_terms="20% đặt cọc, 50% lắp đặt, 30% nghiệm thu",
    is_recommended=1,
    notes="Philips Ingenia Ambition 1.5T — ZBO, bore 70cm, dStream AI. Đào tạo 2 tuần onsite.",
)
add_child("Vendor Evaluation Item", ve_e.name, "Vendor Evaluation",
    vendor="AC-SUP-2026-0001", vendor_name="MedEquip Vietnam JSC",
    quoted_price=16_800_000_000,
    technical_score=75, financial_score=92, profile_score=70, risk_score=65, total_score=75,
    score_band="B (6–7.9)",
    compliant_with_ts=1, has_nd98_registration=1, bid_compliant=1,
    quoted_delivery_weeks=28, offered_payment_terms="30% đặt cọc, 70% nghiệm thu",
    is_recommended=0,
    notes="Giá thấp hơn 700M nhưng không có ZBO helium, điểm kỹ thuật thấp hơn.",
)
print(f"  VE: {ve_e.name} — Approved | Philips recommended")

# POR 17.5 tỷ — cần Giám đốc duyệt
por_e = ins("Purchase Order Request",
    linked_plan_item=ppi_e.name, procurement_plan=pp_e.name, linked_evaluation=ve_e.name,
    vendor=SUP_PHILIPS, vendor_name="Philips Medical Vietnam LLC",
    equipment_description="Hệ thống MRI 1.5T Philips Ingenia Ambition — lắp đặt, RF shielding và đào tạo",
    quantity=1, unit_price=17_500_000_000, total_amount=17_500_000_000,
    requires_director_approval=1,
    delivery_terms="DDP Bệnh viện, bao gồm xây dựng phòng máy, lắp đặt, RF shielding và đào tạo",
    incoterms="DDP",
    payment_terms="20% đặt cọc sau ký HĐ, 50% sau lắp đặt + FAT, 30% sau nghiệm thu lâm sàng",
    expected_delivery_date=add_days(today(), 168),
    warranty_period_months=24,
    payment_schedule_notes=(
        "Đợt 1: 3.500.000.000 VNĐ (20%) — sau ký hợp đồng\n"
        "Đợt 2: 8.750.000.000 VNĐ (50%) — sau lắp đặt hoàn chỉnh + Factory Acceptance Test\n"
        "Đợt 3: 5.250.000.000 VNĐ (30%) — sau nghiệm thu lâm sàng 30 ngày vận hành"
    ),
    status="Draft",
)
sv("Purchase Order Request", por_e.name, status="Under Review", approver="Administrator")
sv("Procurement Plan Item", ppi_e.name, status="PO Raised", por_reference=por_e.name)
print(f"  POR: {por_e.name} — 17.5 tỷ, requires_director_approval=1, Under Review ✓")


# ─── Summary ──────────────────────────────────────────────────────────────────

print("\n── Tổng kết ─────────────────────────────────────────────────────────────")
for dt in [
    "Needs Assessment", "Procurement Plan", "Procurement Plan Item",
    "Technical Specification", "Vendor Evaluation", "Vendor Evaluation Item",
    "Purchase Order Request",
]:
    print(f"  {frappe.db.count(dt):>3}  {dt}")

frappe.destroy()
print("\n✓ Seed hoàn tất — 5 kịch bản IMM-01→03.")
