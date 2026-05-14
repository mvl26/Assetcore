"""
UAT seed script for IMM-15 (Spare Parts Inventory) + IMM-16 (Compliance).
Run: bench --site miyano execute assetcore.scripts.uat.seed_imm15_imm16.run

Creates ~3 records per record-type using realistic Vietnamese hospital data.
Idempotent: skips records that already exist by deterministic name.
"""
from __future__ import annotations
import frappe
from frappe.utils import nowdate, add_days, add_months


# ─── Reference data ────────────────────────────────────────────────────────────

USER = "chuvanhieu357@gmail.com"

WAREHOUSES = [
    {"warehouse_code": "WH-KHO-TT",  "warehouse_name": "Kho trung tâm Vật tư Thiết bị Y tế",
     "department": "Khoa-HSTC", "location": "AC-LOC-2026-0131",
     "manager": USER, "notes": "Kho trung tâm cấp 1 cho phụ tùng quan trọng (Critical)."},
    {"warehouse_code": "WH-KHO-PX",  "warehouse_name": "Kho phân xưởng kỹ thuật",
     "department": "Khoa-HSTC", "location": "AC-LOC-2026-0131",
     "manager": USER, "notes": "Kho phụ tùng tiêu hao và linh kiện điện tử."},
    {"warehouse_code": "WH-QC-HOLD", "warehouse_name": "Kho QC Hold — phụ tùng chờ kiểm",
     "department": "Khoa-HSTC", "location": "AC-LOC-2026-0131",
     "manager": USER, "notes": "Kho cách ly phụ tùng hư hỏng, chờ kiểm định lại."},
]

SPARE_PARTS = [
    {"part_code": "SP-EVT-PEEP-V01", "part_name": "Van PEEP máy thở Dräger Evita V500",
     "part_category": "Mechanical", "manufacturer": "Dräger Medical AG",
     "manufacturer_part_no": "EVT-PEEP-V500-2024",
     "unit_cost": 4_850_000, "stock_uom": "Cái",
     "min_stock_level": 2, "max_stock_level": 10, "is_critical": 1,
     "description": "Van điều áp PEEP — thay thế khi vượt 18 tháng chu kỳ (ref QP-03-2025)."},
    {"part_code": "SP-MBT9-BAT-002", "part_name": "Pin lithium 14.4V Monitor Mindray BeneView T9",
     "part_category": "Battery", "manufacturer": "Mindray Medical Vietnam",
     "manufacturer_part_no": "LI24I-PA12.00.064067",
     "unit_cost": 2_850_000, "stock_uom": "Cái",
     "min_stock_level": 4, "max_stock_level": 20, "is_critical": 1,
     "description": "Pin sạc lithium-ion cho monitor BeneView T9 — chu kỳ 24 tháng."},
    {"part_code": "SP-EPQ7-SPO2", "part_name": "Cảm biến SpO2 máy siêu âm Philips EPIQ 7",
     "part_category": "Sensor", "manufacturer": "Philips Healthcare Vietnam",
     "manufacturer_part_no": "EPQ7-SPO2-ADULT",
     "unit_cost": 1_650_000, "stock_uom": "Cái",
     "min_stock_level": 3, "max_stock_level": 15, "is_critical": 0,
     "description": "Cảm biến SpO2 dùng cho người lớn, hiệu chuẩn theo TCVN 8023."},
]

COMPLIANCE_RULES = [
    {"rule_code": "CR-PM-COMPLIANCE-90", "rule_name": "Tỷ lệ tuân thủ PM tối thiểu 90%/tháng",
     "source_module": "IMM-08", "category": "PM", "severity": "High",
     "evaluation_frequency": "Monthly",
     "threshold_definition": '{"metric":"pm_compliance_pct","op":"<","value":90}',
     "description": "Tỷ lệ PM hoàn thành theo lịch phải >= 90% mỗi tháng theo NĐ98 và WHO HTM."},
    {"rule_code": "CR-CAL-OVERDUE", "rule_name": "Hiệu chuẩn quá hạn — Class II",
     "source_module": "IMM-11", "category": "Calibration", "severity": "Critical",
     "evaluation_frequency": "Daily",
     "threshold_definition": '{"metric":"calibration_overdue_days","op":">","value":0}',
     "description": "Thiết bị Class II quá hạn hiệu chuẩn >0 ngày — vi phạm TCVN 8023:2009."},
    {"rule_code": "CR-DOC-UDI-100", "rule_name": "Hồ sơ UDI đầy đủ 100%",
     "source_module": "IMM-05", "category": "Document", "severity": "Medium",
     "evaluation_frequency": "Weekly",
     "threshold_definition": '{"metric":"udi_completeness_pct","op":"<","value":100}',
     "description": "Toàn bộ thiết bị y tế phải có UDI và giấy phép lưu hành (NĐ98 Đ.5)."},
]


# ─── Seed helpers ──────────────────────────────────────────────────────────────

def _get_or_insert(doctype: str, key_field: str, key_value: str, payload: dict) -> str:
    existing = frappe.db.exists(doctype, {key_field: key_value})
    if existing:
        print(f"  - SKIP {doctype} {key_value} (existing: {existing})")
        return existing
    doc = frappe.get_doc({"doctype": doctype, **payload}).insert(ignore_permissions=True)
    print(f"  + CREATED {doctype}: {doc.name}")
    return doc.name


def _get_asset_pool() -> list[str]:
    assets = frappe.get_all("AC Asset", fields=["name"], limit=5)
    return [a["name"] for a in assets]


# ─── IMM-15 seeders ────────────────────────────────────────────────────────────

def seed_warehouses() -> list[str]:
    print("\n[IMM-15] Seeding AC Warehouse…")
    names = []
    for w in WAREHOUSES:
        names.append(_get_or_insert("AC Warehouse", "warehouse_code", w["warehouse_code"],
                                     {**w, "is_active": 1}))
    return names


def seed_spare_parts() -> list[str]:
    print("\n[IMM-15] Seeding AC Spare Part…")
    names = []
    for p in SPARE_PARTS:
        names.append(_get_or_insert("AC Spare Part", "part_code", p["part_code"],
                                     {**p, "is_active": 1}))
    return names


def seed_stock_levels(warehouses: list[str], parts: list[str]) -> None:
    """Create initial stock for each spare-part × main warehouse."""
    print("\n[IMM-15] Seeding AC Spare Part Stock…")
    qty_map = {0: 8.0, 1: 6.0, 2: 12.0}  # part_idx → qty
    main_wh = warehouses[0]
    for idx, part in enumerate(parts):
        existing = frappe.db.exists("AC Spare Part Stock",
                                      {"spare_part": part, "warehouse": main_wh})
        if existing:
            print(f"  - SKIP Stock {part} @ {main_wh} (existing)")
            continue
        doc = frappe.get_doc({
            "doctype": "AC Spare Part Stock",
            "spare_part": part,
            "warehouse": main_wh,
            "qty_on_hand": qty_map.get(idx, 5.0),
            "reserved_qty": 0,
            "last_movement_date": nowdate(),
        }).insert(ignore_permissions=True)
        print(f"  + CREATED Stock: {doc.name} ({qty_map.get(idx, 5)} @ {main_wh})")


def seed_stock_movements(warehouses: list[str], parts: list[str]) -> list[str]:
    """Create 3 stock movements (Receipt, Issue, Transfer) — Draft state."""
    print("\n[IMM-15] Seeding AC Stock Movement…")
    movements_data = [
        {
            "movement_type": "Receipt",
            "to_warehouse": warehouses[0],
            "notes": "Nhập kho phụ tùng PEEP V500 — đợt thay thế định kỳ Q2/2026.",
            "items": [
                {"spare_part": parts[0], "qty": 5, "uom": "Cái", "rate": 4_850_000},
            ],
        },
        {
            "movement_type": "Issue",
            "from_warehouse": warehouses[0],
            "notes": "Xuất kho pin Mindray BeneView T9 — thay thế ICU giường số 7.",
            "items": [
                {"spare_part": parts[1], "qty": 2, "uom": "Cái", "rate": 2_850_000},
            ],
        },
        {
            "movement_type": "Transfer",
            "from_warehouse": warehouses[0],
            "to_warehouse": warehouses[1],
            "notes": "Chuyển cảm biến SpO2 từ kho trung tâm sang kho phân xưởng kỹ thuật.",
            "items": [
                {"spare_part": parts[2], "qty": 3, "uom": "Cái", "rate": 1_650_000},
            ],
        },
    ]
    names = []
    for idx, m in enumerate(movements_data):
        # Use deterministic key via notes prefix
        key = f"UAT-SM-{idx+1}"
        existing = frappe.db.exists("AC Stock Movement", {"notes": ["like", f"%{m['notes'][:20]}%"]})
        if existing:
            print(f"  - SKIP Movement {key} (existing: {existing})")
            names.append(existing)
            continue
        payload = {
            "doctype": "AC Stock Movement",
            "movement_type": m["movement_type"],
            "posting_date": nowdate(),
            "notes": m["notes"],
            "items": [{"doctype": "AC Stock Movement Item", **it} for it in m["items"]],
        }
        if m.get("from_warehouse"):
            payload["from_warehouse"] = m["from_warehouse"]
        if m.get("to_warehouse"):
            payload["to_warehouse"] = m["to_warehouse"]
        try:
            doc = frappe.get_doc(payload).insert(ignore_permissions=True)
            names.append(doc.name)
            print(f"  + CREATED Movement: {doc.name} ({m['movement_type']})")
        except Exception as e:
            print(f"  ! FAILED Movement {idx+1}: {e}")
    return names


# ─── IMM-16 seeders ────────────────────────────────────────────────────────────

def seed_compliance_rules() -> list[str]:
    print("\n[IMM-16] Seeding IMM Compliance Rule…")
    names = []
    for r in COMPLIANCE_RULES:
        existing = frappe.db.exists("IMM Compliance Rule", {"rule_code": r["rule_code"]})
        if existing:
            print(f"  - SKIP Rule {r['rule_code']} (existing: {existing})")
            names.append(existing)
            continue
        payload = {
            "doctype": "IMM Compliance Rule",
            **r,
            "is_active": 1,
            "version": "1.0",
            "owner_role": "System Manager",
        }
        try:
            doc = frappe.get_doc(payload).insert(ignore_permissions=True)
            names.append(doc.name)
            print(f"  + CREATED Rule: {doc.name}")
        except Exception as e:
            print(f"  ! FAILED Rule {r['rule_code']}: {e}")
    return names


def seed_compliance_findings(rules: list[str], assets: list[str]) -> list[str]:
    print("\n[IMM-16] Seeding IMM Compliance Finding…")
    findings_data = [
        {
            "rule": rules[0] if rules else None,
            "asset": assets[0] if assets else None,
            "responsible_dept": "Khoa-HSTC",
            "severity": "High",
            "status": "Open",
            "current_value": "78",
            "threshold_value": "90",
            "description": "Tỷ lệ tuân thủ PM tháng 04/2026 tại Khoa ICU đạt 78%, dưới ngưỡng 90% — phát hiện qua tự động đánh giá tháng.",
        },
        {
            "rule": rules[1] if len(rules) > 1 else None,
            "asset": assets[1] if len(assets) > 1 else None,
            "responsible_dept": "Khoa-CDHA",
            "severity": "Critical",
            "status": "Under Review",
            "current_value": "45",
            "threshold_value": "0",
            "description": "Máy siêu âm Philips EPIQ 7 quá hạn hiệu chuẩn 45 ngày — vi phạm TCVN 8023.",
        },
        {
            "rule": rules[2] if len(rules) > 2 else None,
            "asset": assets[2] if len(assets) > 2 else None,
            "responsible_dept": "Phong-Mo-2",
            "severity": "Medium",
            "status": "Open",
            "current_value": "92",
            "threshold_value": "100",
            "description": "8% thiết bị tại Phòng Mổ số 2 chưa cập nhật UDI — vi phạm NĐ98.",
        },
    ]
    names = []
    for idx, f in enumerate(findings_data):
        if not f["rule"] or not f["asset"]:
            print(f"  - SKIP Finding {idx+1} (missing rule/asset)")
            continue
        existing = frappe.db.exists("IMM Compliance Finding",
                                      {"rule": f["rule"], "asset": f["asset"]})
        if existing:
            print(f"  - SKIP Finding (rule={f['rule']}, asset={f['asset']}) → {existing}")
            names.append(existing)
            continue
        payload = {
            "doctype": "IMM Compliance Finding",
            **f,
            "detected_date": frappe.utils.now(),
            "evaluation_date": nowdate(),
        }
        try:
            doc = frappe.get_doc(payload).insert(ignore_permissions=True)
            names.append(doc.name)
            print(f"  + CREATED Finding: {doc.name}")
        except Exception as e:
            print(f"  ! FAILED Finding {idx+1}: {e}")
    return names


def seed_capa_records(findings: list[str], assets: list[str]) -> list[str]:
    print("\n[IMM-16] Seeding IMM CAPA Record…")
    capas_data = [
        {
            "asset": assets[0] if assets else None,
            "imm_compliance_finding_ref": findings[0] if findings else None,
            "severity": "Major",
            "source_type": "Non-Conformance",
            "responsible": USER,
            "imm_risk_level": "High",
            "imm_root_cause_method": "5-Why",
            "description": "Quy trình bảo trì định kỳ ICU không được thực hiện đúng lịch — delay 3 tuần do thiếu nhân lực kỹ thuật. Hành động khắc phục: bổ sung KTV. Nguyễn Văn Hùng làm trưởng nhóm PM.",
        },
        {
            "asset": assets[1] if len(assets) > 1 else None,
            "imm_compliance_finding_ref": findings[1] if len(findings) > 1 else None,
            "severity": "Critical",
            "source_type": "Non-Conformance",
            "responsible": USER,
            "imm_risk_level": "Critical",
            "imm_root_cause_method": "Fishbone",
            "description": "Máy siêu âm Philips EPIQ 7 không được lập lịch hiệu chuẩn kịp thời. Hành động: ký hợp đồng dịch vụ hiệu chuẩn năm với Công ty TNHH Philips Việt Nam.",
        },
        {
            "asset": assets[2] if len(assets) > 2 else None,
            "imm_compliance_finding_ref": findings[2] if len(findings) > 2 else None,
            "severity": "Minor",
            "source_type": "Non-Conformance",
            "responsible": USER,
            "imm_risk_level": "Medium",
            "imm_root_cause_method": "Pareto",
            "description": "Hồ sơ UDI Phòng Mổ số 2 chưa nhập đầy đủ vào hệ thống. Hành động: KTV. Trần Thị Lan cập nhật UDI trong vòng 30 ngày.",
        },
    ]
    names = []
    today = nowdate()
    for idx, c in enumerate(capas_data):
        if not c["asset"]:
            print(f"  - SKIP CAPA {idx+1} (no asset)")
            continue
        existing = frappe.db.exists("IMM CAPA Record",
                                      {"imm_compliance_finding_ref": c.get("imm_compliance_finding_ref")})
        if existing and c.get("imm_compliance_finding_ref"):
            print(f"  - SKIP CAPA (finding={c['imm_compliance_finding_ref']}) → {existing}")
            names.append(existing)
            continue
        payload = {
            "doctype": "IMM CAPA Record",
            **c,
            "opened_date": today,
            "due_date": add_days(today, 30),
            "status": "Open",
        }
        try:
            doc = frappe.get_doc(payload).insert(ignore_permissions=True)
            names.append(doc.name)
            print(f"  + CREATED CAPA: {doc.name}")
        except Exception as e:
            print(f"  ! FAILED CAPA {idx+1}: {e}")
    return names


def seed_management_reviews() -> list[str]:
    print("\n[IMM-16] Seeding IMM Management Review…")
    today = nowdate()
    reviews_data = [
        {
            "review_date": add_months(today, -3),
            "chair": USER,
            "status": "Closed",
            "review_period": "Q1/2026",
            "minutes_url": "https://benhviennhi.dms.local/mr/q1-2026.pdf",
            "agenda": "Soát xét tuân thủ Q1/2026 — Đánh giá KPI tổng thể, đề xuất kế hoạch khắc phục cho Q2.",
        },
        {
            "review_date": add_months(today, -6),
            "chair": USER,
            "status": "Closed",
            "review_period": "Q4/2025",
            "minutes_url": "https://benhviennhi.dms.local/mr/q4-2025.pdf",
            "agenda": "Tổng kết tuân thủ năm 2025 — KPI PM compliance đạt 88%, kế hoạch nâng lên 95% năm 2026.",
        },
        {
            "review_date": today,
            "chair": USER,
            "status": "Draft",
            "review_period": "Q2/2026",
            "minutes_url": "",
            "agenda": "Soát xét tuân thủ Q2/2026 — kế hoạch họp ngày 30/05. Chủ đề: CAPA tồn đọng và cải tiến quy trình PM ICU.",
        },
    ]
    names = []
    for idx, r in enumerate(reviews_data):
        existing = frappe.db.exists("IMM Management Review",
                                      {"review_date": r["review_date"]})
        if existing:
            print(f"  - SKIP MR {r['review_period']} (existing: {existing})")
            names.append(existing)
            continue
        payload = {"doctype": "IMM Management Review", **r}
        try:
            doc = frappe.get_doc(payload).insert(ignore_permissions=True)
            names.append(doc.name)
            print(f"  + CREATED MR: {doc.name}")
        except Exception as e:
            print(f"  ! FAILED MR {idx+1}: {e}")
    return names


# ─── Entry point ───────────────────────────────────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("UAT Seed: IMM-15 + IMM-16")
    print("=" * 60)
    frappe.set_user("Administrator")
    assets = _get_asset_pool()
    print(f"Assets available: {len(assets)} — {assets[:3]}")

    # IMM-15
    warehouses = seed_warehouses()
    parts = seed_spare_parts()
    seed_stock_levels(warehouses, parts)
    seed_stock_movements(warehouses, parts)

    # IMM-16
    rules = seed_compliance_rules()
    findings = seed_compliance_findings(rules, assets)
    seed_capa_records(findings, assets)
    seed_management_reviews()

    frappe.db.commit()
    print("\n" + "=" * 60)
    print("SEED COMPLETE — frappe.db.commit() applied")
    print("=" * 60)
