"""Seed real-world data for IMM-08/09/11/12 testing.

Run: bench --site miyano execute assetcore.scripts.seed.seed_test_modules_8_9_11_12.run
"""
from __future__ import annotations

import frappe
from frappe.utils import add_days, now_datetime, today


ASSETS = [
    {
        "name": "AC-ASSET-2026-00407",
        "category": "Thiet-bi-Ho-tro-Su-song",
        "department": "Khoa-HSTC",
        "risk": "High",
        "label": "Máy thở Dräger Evita V500",
    },
    {
        "name": "AC-ASSET-2026-00409",
        "category": "Thiet-bi-Chan-doan-Hinh-anh",
        "department": "Khoa-CDHA",
        "risk": "Medium",
        "label": "Máy siêu âm Philips EPIQ 7",
    },
    {
        "name": "AC-ASSET-2026-00410",
        "category": "Thiet-bi-Phau-thuat-Can-thiep",
        "department": "Phong-Mo-2",
        "risk": "High",
        "label": "Máy bơm tiêm B. Braun Perfusor Space",
    },
]

TECH_USER = "sohaidiuuu@gmail.com"  # Trần Thị Test KTV
ADMIN = "Administrator"


def _exists(doctype: str, name: str) -> bool:
    return bool(frappe.db.exists(doctype, name))


def ensure_checklist_templates() -> dict[str, str]:
    """One template per (category, Quarterly)."""
    tpl_map: dict[str, str] = {}
    items_by_cat = {
        "Thiet-bi-Ho-tro-Su-song": [
            {"item_code": "PM-VENT-01", "description": "Kiểm tra hệ thống van PEEP và áp lực đường thở (TCVN 7303-2)",
             "measurement_type": "Numeric", "unit": "cmH2O", "expected_min": 5.0, "expected_max": 20.0, "is_critical": 1,
             "reference_section": "QP-VENT-03-2025 §4.1"},
            {"item_code": "PM-VENT-02", "description": "Hiệu chuẩn cảm biến SpO2 và FiO2 theo quy trình QP-03-2025",
             "measurement_type": "Pass/Fail", "is_critical": 1, "reference_section": "QP-03-2025"},
            {"item_code": "PM-VENT-03", "description": "Vệ sinh và thay thế bộ lọc HEPA, kiểm tra rò rỉ khí",
             "measurement_type": "Pass/Fail", "is_critical": 0, "reference_section": "Drager Manual §7.2"},
            {"item_code": "PM-VENT-04", "description": "Ghi nhận giờ vận hành và tình trạng pin dự phòng",
             "measurement_type": "Text", "is_critical": 0},
        ],
        "Thiet-bi-Theo-doi-Benh-nhan": [
            {"item_code": "PM-MON-01", "description": "Kiểm tra độ chính xác đo ECG 5 đạo trình theo IEC 60601-2-27",
             "measurement_type": "Numeric", "unit": "mV", "expected_min": 0.5, "expected_max": 5.0, "is_critical": 1,
             "reference_section": "IEC 60601-2-27"},
            {"item_code": "PM-MON-02", "description": "Hiệu chuẩn module NIBP — sai số áp lực ≤ ±3 mmHg",
             "measurement_type": "Pass/Fail", "is_critical": 1},
            {"item_code": "PM-MON-03", "description": "Kiểm tra cảm biến SpO2 và đầu đo nhiệt độ trung tâm",
             "measurement_type": "Pass/Fail", "is_critical": 1},
        ],
        "Thiet-bi-Phau-thuat-Can-thiep": [
            {"item_code": "PM-PUMP-01", "description": "Kiểm tra độ chính xác lưu lượng bơm (test 1ml/h, 5ml/h, 20ml/h) — sai số ≤ ±2%",
             "measurement_type": "Numeric", "unit": "%", "expected_min": -2.0, "expected_max": 2.0, "is_critical": 1,
             "reference_section": "IEC 60601-2-24 §6.3"},
            {"item_code": "PM-PUMP-02", "description": "Kiểm tra cảm biến áp lực occlusion và alarm — đáp ứng < 30 giây",
             "measurement_type": "Pass/Fail", "is_critical": 1},
            {"item_code": "PM-PUMP-03", "description": "Thay pin dự phòng nếu < 80% dung lượng, kiểm tra thời gian backup ≥ 4 giờ",
             "measurement_type": "Numeric", "unit": "giờ", "expected_min": 4.0, "expected_max": 12.0, "is_critical": 0},
            {"item_code": "PM-PUMP-04", "description": "Vệ sinh syringe holder, kiểm tra mòn — thay nếu cần",
             "measurement_type": "Pass/Fail", "is_critical": 0},
        ],
        "Thiet-bi-Chan-doan-Hinh-anh": [
            {"item_code": "PM-US-01", "description": "Kiểm tra đầu dò siêu âm (probe) — không có vết nứt, hình ảnh đồng đều",
             "measurement_type": "Pass/Fail", "is_critical": 1, "reference_section": "Philips EPIQ §6.3"},
            {"item_code": "PM-US-02", "description": "Đo độ phân giải trục (axial) bằng phantom chuẩn",
             "measurement_type": "Numeric", "unit": "mm", "expected_min": 0.3, "expected_max": 1.0, "is_critical": 1},
            {"item_code": "PM-US-03", "description": "Kiểm tra UPS và hệ thống tản nhiệt máy chính",
             "measurement_type": "Pass/Fail", "is_critical": 0},
        ],
    }
    for cat, items in items_by_cat.items():
        tpl_name = f"PMCT-{cat}-Quarterly"
        if not _exists("PM Checklist Template", tpl_name):
            doc = frappe.get_doc({
                "doctype": "PM Checklist Template",
                "template_name": f"Checklist PM Quý — {cat}",
                "asset_category": cat,
                "pm_type": "Quarterly",
                "version": "v1.0-2026",
                "effective_date": today(),
                "approved_by": ADMIN,
                "checklist_items": [{"doctype": "PM Checklist Item", **it} for it in items],
            }).insert(ignore_permissions=True)
            print(f"  + PM Checklist Template: {doc.name}")
        tpl_map[cat] = tpl_name
    return tpl_map


def ensure_pm_schedules(tpl_map: dict[str, str]) -> list[str]:
    schedules: list[str] = []
    for a in ASSETS:
        ps_name = f"PMS-{a['name']}-Quarterly"
        if not _exists("PM Schedule", ps_name):
            doc = frappe.get_doc({
                "doctype": "PM Schedule",
                "asset_ref": a["name"],
                "pm_type": "Quarterly",
                "status": "Active",
                "pm_interval_days": 90,
                "checklist_template": tpl_map[a["category"]],
                "alert_days_before": 14,
                "responsible_technician": TECH_USER,
                "last_pm_date": add_days(today(), -30),
                "next_due_date": add_days(today(), 60),
                "notes": f"Lịch bảo trì định kỳ quý — {a['label']} | tần suất 90 ngày",
            }).insert(ignore_permissions=True)
            print(f"  + PM Schedule: {doc.name}")
        schedules.append(ps_name)
    return schedules


def ensure_pm_work_orders(schedules: list[str]) -> list[str]:
    created: list[str] = []
    notes_map = {
        0: "Bảo trì quý 2/2026 — thay bộ lọc HEPA, kiểm tra van PEEP, hiệu chuẩn SpO2. KTV: Trần Thị Lan.",
        1: "Bảo trì quý — kiểm tra đầu dò siêu âm tim C5-1, đo độ phân giải bằng phantom CIRS, kiểm tra UPS máy chính.",
        2: "Bảo trì quý — kiểm tra độ chính xác lưu lượng bơm (±2%), thay pin dự phòng, hiệu chuẩn áp lực occlusion theo IEC 60601-2-24.",
    }
    for i, ps in enumerate(schedules):
        asset = ASSETS[i]
        existing = frappe.db.get_all("PM Work Order", filters={"pm_schedule": ps}, limit=1)
        if existing:
            created.append(existing[0].name)
            continue
        try:
            doc = _build_pm_wo(asset, ps, i, notes_map)
        except Exception as e:
            print(f"  ! SKIP PM WO for {asset['name']}: {e}")
            continue
        created.append(doc.name)
        print(f"  + PM Work Order: {doc.name}")
    return created


def _build_pm_wo(asset, ps, i, notes_map):
    doc = frappe.get_doc({
        "doctype": "PM Work Order",
        "asset_ref": asset["name"],
        "pm_schedule": ps,
        "wo_type": "Preventive",
        "due_date": add_days(today(), 7 + i * 3),
        "status": "Open",
        "assigned_to": TECH_USER,
        "assigned_by": ADMIN,
        "scheduled_date": add_days(today(), 5 + i * 3),
        "technician_notes": notes_map[i],
    })
    if asset["risk"] in ("High", "Critical"):
        doc.attachments = "/files/pm-photo-before.jpg\n/files/pm-photo-after.jpg"
    doc.insert(ignore_permissions=True)
    return doc


def ensure_asset_repairs(incidents: list[str]) -> list[str]:
    descriptions = [
        {
            "type": "Breakdown",
            "priority": "Emergency",
            "symptoms": "Máy thở báo lỗi E-001 — áp lực đường thở tăng bất thường khi bệnh nhân thở thụ động. Đã tạm dừng sử dụng, chuyển sang máy dự phòng Servo-i.",
            "root_cause_category": "Mechanical",
            "downtime_hours": 6.5,
            "notes": "Thay van PEEP do mòn — ref phụ tùng SP-DR-0234. Đã kiểm tra rò rỉ sau sửa chữa, OK.",
        },
        {
            "type": "Warranty Repair",
            "priority": "Normal",
            "symptoms": "Máy siêu âm hiển thị artifact dạng sọc ngang trên đầu dò C5-1 — ảnh hưởng chất lượng chẩn đoán tim mạch. Sự cố xảy ra sau khi di chuyển thiết bị giữa các phòng.",
            "root_cause_category": "Wear and Tear",
            "downtime_hours": 24.0,
            "notes": "Gửi probe C5-1 về Philips Vietnam bảo hành — số case PVN-WR-2026-0344. Dùng probe dự phòng C5-2 tạm thời.",
        },
        {
            "type": "Corrective",
            "priority": "Urgent",
            "symptoms": "Máy bơm tiêm B. Braun Perfusor Space báo lỗi 'occlusion alarm false trigger' liên tục khi truyền liều thấp <2 ml/h. Đang điều trị bệnh nhi sốc nhiễm trùng tại Phòng Mổ số 2.",
            "root_cause_category": "Mechanical",
            "downtime_hours": 2.5,
            "notes": "Vệ sinh cảm biến áp lực, thay bộ syringe holder bị mòn — phụ tùng SP-BBR-0078. Hiệu chuẩn lại theo TLS B.Braun §3.4.",
        },
    ]
    created: list[str] = []
    for i, asset in enumerate(ASSETS):
        d = descriptions[i]
        # Skip if exists with this asset
        existing = frappe.db.get_all("Asset Repair", filters={"asset_ref": asset["name"]}, limit=1)
        if existing:
            created.append(existing[0].name)
            continue
        risk_map = {"Low": "Class I", "Medium": "Class II", "High": "Class III", "Critical": "Class III"}
        try:
            doc = frappe.get_doc({
                "doctype": "Asset Repair",
                "asset_ref": asset["name"],
                "incident_report": incidents[i] if i < len(incidents) else None,
                "repair_type": d["type"],
                "priority": d["priority"],
                "risk_class": risk_map.get(asset["risk"], "Class II"),
                "open_datetime": now_datetime(),
                "status": "Open",
                "assigned_to": TECH_USER,
                "assigned_by": ADMIN,
                "diagnosis_notes": d["symptoms"],
                "root_cause_category": d["root_cause_category"],
                "repair_summary": d["notes"],
                "technician_notes": d["notes"],
                "sla_target_hours": 4.0 if d["priority"] == "Emergency" else (24.0 if d["priority"] == "Urgent" else 72.0),
            }).insert(ignore_permissions=True)
            created.append(doc.name)
            print(f"  + Asset Repair: {doc.name}")
        except Exception as e:
            print(f"  ! SKIP Asset Repair for {asset['name']}: {e}")
    return created


def ensure_calibrations() -> list[str]:
    cals = [
        {
            "type": "In-House",
            "method": "Hiệu chuẩn cảm biến SpO2 và FiO2 bằng thiết bị chuẩn Fluke VT900A — theo quy trình QP-CAL-03-2025",
            "standard": "TCVN 8023:2009 và IEC 80601-2-61",
            "notes": "Sai số SpO2 đo được: ±1.5% (giới hạn cho phép ±3%). Đạt yêu cầu.",
        },
        {
            "type": "In-House",
            "method": "Kiểm tra độ phân giải máy siêu âm bằng phantom CIRS Model 040GSE — đo axial và lateral resolution",
            "standard": "AIUM Quality Assurance Manual §4.2",
            "notes": "Axial: 0.45mm (chuẩn 0.3–1.0mm). Lateral: 0.62mm. Đạt yêu cầu chẩn đoán tim mạch can thiệp.",
        },
        {
            "type": "External",
            "method": "Hiệu chuẩn độ chính xác lưu lượng bơm tiêm tại phòng thí nghiệm Vinacontrol — sai số ±2% theo IEC 60601-2-24",
            "standard": "IEC 60601-2-24:2012 — phòng VILAS LAS-XD 1234",
            "notes": "Hợp đồng dịch vụ SC-2026-0089 với Cty Bình Minh. Đã gửi thiết bị 2026-05-08, dự kiến chứng chỉ 2026-05-15.",
        },
    ]
    created: list[str] = []
    for i, asset in enumerate(ASSETS):
        c = cals[i]
        existing = frappe.db.get_all("IMM Asset Calibration", filters={"asset": asset["name"]}, limit=1)
        if existing:
            created.append(existing[0].name)
            continue
        try:
            doc = frappe.get_doc({
                "doctype": "IMM Asset Calibration",
                "asset": asset["name"],
                "calibration_type": c["type"],
                "status": "Scheduled",
                "scheduled_date": add_days(today(), 5 + i * 7),
                "technician": TECH_USER,
                "assigned_by": ADMIN,
                "reference_standard_serial": c["standard"],
                "traceability_reference": c.get("trace", "VMI-2026-Q2-Ref-001"),
                "technician_notes": f"{c['method']}\n\nGhi chú: {c['notes']}",
            })
            if c["type"] == "External":
                doc.lab_supplier = "AC-SUP-2026-0018"
                doc.lab_accreditation_number = "LAS-XD 1234"
                doc.lab_contract_ref = "SC-2026-0089"
            doc.insert(ignore_permissions=True)
            created.append(doc.name)
            print(f"  + IMM Asset Calibration: {doc.name}")
        except Exception as e:
            print(f"  ! SKIP Calibration for {asset['name']}: {e}")
    return created


def ensure_incidents() -> list[str]:
    incs = [
        {
            "type": "Malfunction",
            "severity": "High",
            "desc": "<p>Máy thở Dräger Evita V500 báo lỗi <b>E-001</b> — áp lực đường thở tăng bất thường khi bệnh nhân thở thụ động.</p><p>Đã chuyển bệnh nhân sang máy dự phòng Servo-i. Bệnh nhân ổn định, không có biến cố lâm sàng.</p><p>Khoa Hồi sức tích cực ICU - giường số 3. Báo cáo bởi: KTV. Nguyễn Văn Hùng.</p>",
        },
        {
            "type": "Safety Event",
            "severity": "Critical",
            "desc": "<p>Máy siêu âm Philips EPIQ 7 hiển thị artifact dạng sọc ngang trên đầu dò C5-1 trong khi siêu âm tim cấp cứu.</p><p><b>Có nguy cơ ảnh hưởng chất lượng chẩn đoán</b> — bác sĩ phát hiện kịp thời, chuyển sang máy khác để hoàn thành ca.</p><p>Cần điều tra ngay theo NĐ98/2021 do liên quan thiết bị Loại B trong tình huống cấp cứu.</p>",
        },
        {
            "type": "Failure",
            "severity": "Medium",
            "desc": "<p>Máy bơm tiêm B. Braun Perfusor Space báo <b>occlusion alarm</b> giả khi truyền liều thấp dưới 2ml/h.</p><p>Bệnh nhi sốc nhiễm trùng tại Phòng Mổ số 2 đang được truyền vasopressor. Đã chuyển sang bơm dự phòng cùng loại, bệnh nhân ổn định.</p><p>Phát hiện bởi: BS. Nguyễn Thành Lâm — bác sĩ gây mê.</p>",
        },
    ]
    created: list[str] = []
    for i, asset in enumerate(ASSETS):
        inc = incs[i]
        existing = frappe.db.get_all("Incident Report", filters={"asset": asset["name"]}, limit=1)
        if existing:
            created.append(existing[0].name)
            continue
        doc = frappe.get_doc({
            "doctype": "Incident Report",
            "naming_series": "IR-.YYYY.-.####",
            "asset": asset["name"],
            "reported_by": ADMIN,
            "reported_at": now_datetime(),
            "incident_type": inc["type"],
            "severity": inc["severity"],
            "status": "Open",
            "description": inc["desc"],
            "immediate_action": f"<p>Đã tạm dừng sử dụng thiết bị tại {asset['department']} — vị trí số {3 + i * 2}. Chuyển bệnh nhân sang thiết bị dự phòng. Báo cáo kỹ thuật viên ngay.</p>",
            "patient_affected": 1 if inc["severity"] in ("High", "Critical") else 0,
            "patient_impact_description": "Bệnh nhân ổn định, đã chuyển sang máy dự phòng kịp thời, không có biến cố lâm sàng." if inc["severity"] in ("High", "Critical") else "",
            "fault_code": "E-001" if i == 0 else ("SPO2-LOST" if i == 1 else "PROBE-ARTIFACT"),
            "workaround_applied": 1,
            "requires_rca": 1 if inc["severity"] in ("High", "Critical") else 0,
            "rca_required": 1 if inc["severity"] in ("High", "Critical") else 0,
            "clinical_impact": "Không có tổn hại cho bệnh nhân do thiết bị dự phòng được sẵn sàng" if inc["severity"] in ("High", "Critical") else "",
        }).insert(ignore_permissions=True)
        created.append(doc.name)
        print(f"  + Incident Report: {doc.name}")
    return created


def run() -> None:
    frappe.set_user(ADMIN)
    print("=== Seeding test data for IMM-08/09/11/12 ===")
    print("\n[1] PM Checklist Templates")
    tpl_map = ensure_checklist_templates()
    print("\n[2] PM Schedules")
    schedules = ensure_pm_schedules(tpl_map)
    print("\n[3] PM Work Orders (IMM-08)")
    wos = ensure_pm_work_orders(schedules)
    print("\n[4] Incident Reports (IMM-12)")
    incidents = ensure_incidents()
    print("\n[5] Asset Repairs / CM (IMM-09)")
    repairs = ensure_asset_repairs(incidents)
    print("\n[6] Calibrations (IMM-11)")
    cals = ensure_calibrations()
    frappe.db.commit()
    print("\n=== DONE ===")
    print(f"PM WO: {wos}")
    print(f"Asset Repair: {repairs}")
    print(f"Calibration: {cals}")
    print(f"Incident: {incidents}")
