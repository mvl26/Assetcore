"""Seed realistic demo data for key assets and modules.

Run: bench --site miyano execute assetcore.scripts.uat.seed_demo_data.run
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import frappe
from frappe.utils import add_days, add_months, nowdate, now_datetime

ASSET_NAME = "AC-ASSET-2026-00381"


def _seed_asset_base(asset_name: str) -> None:
    """Update the asset to have realistic fields for demo using direct DB writes to bypass workflow."""
    updates = {
        "asset_name": "Máy siêu âm màu Mindray DC-70 Pro",
        "lifecycle_status": "Active",
        "gross_purchase_amount": 1_250_000_000,
        "in_service_date": "2023-07-10",
        "depreciation_method": "Straight Line",
        "useful_life_years": 10,
        "total_depreciation_months": 120,
        "depreciation_frequency": "Monthly",
        "depreciation_start_date": "2023-08-01",
        "residual_value": 50_000_000,
        "manufacturer_sn": "SN-MDR-DC70-PRO-20230611",
        "risk_classification": "High",
        "is_pm_required": 1,
        "pm_interval_days": 180,
        "last_pm_date": add_days(nowdate(), -90),
        "next_pm_date": add_days(nowdate(), 90),
        "is_calibration_required": 1,
        "calibration_interval_days": 365,
        "last_calibration_date": add_days(nowdate(), -30),
        "next_calibration_date": add_days(nowdate(), 335),
        "byt_reg_no": "BYT-TTBYT-2023-04511",
        "byt_reg_expiry": "2028-06-30",
    }
    # Filter only existing columns to avoid errors on missing custom fields
    asset_cols = set(frappe.db.get_table_columns("AC Asset"))
    filtered = {k: v for k, v in updates.items() if k in asset_cols}
    frappe.db.set_value("AC Asset", asset_name, filtered)
    frappe.db.commit()
    print(f"  ✅ Asset base fields updated: {asset_name}")


def _seed_downtime_logs(asset_name: str) -> None:
    """Create 5 realistic downtime log entries spanning the past year."""
    if frappe.db.count("AC Asset Downtime Log", {"asset": asset_name}) >= 3:
        print(f"  ⏭ Downtime logs already exist for {asset_name}")
        return

    # Valid reason options: "Sửa chữa", "Bảo trì", "Hiệu chuẩn", "Hỏng hóc", "Ngừng vận hành", "Khác"
    entries = [
        {
            "reason": "Hỏng hóc",
            "start_time": str(now_datetime() - timedelta(days=240, hours=4)),
            "end_time":   str(now_datetime() - timedelta(days=240)),
            "downtime_hours": 4.0,
            "notes": "Biến áp ổn áp bị cháy, thay mới 220V/5kVA",
        },
        {
            "reason": "Sửa chữa",
            "start_time": str(now_datetime() - timedelta(days=180, hours=36)),
            "end_time":   str(now_datetime() - timedelta(days=178, hours=12)),
            "downtime_hours": 36.0,
            "notes": "Đầu dò C5-1E không nhận tín hiệu, chờ linh kiện từ Singapore",
        },
        {
            "reason": "Bảo trì",
            "start_time": str(now_datetime() - timedelta(days=90, hours=2)),
            "end_time":   str(now_datetime() - timedelta(days=90)),
            "downtime_hours": 2.0,
            "notes": "Nâng cấp firmware lên v8.3.5 theo khuyến cáo nhà sản xuất",
        },
        {
            "reason": "Sửa chữa",
            "start_time": str(now_datetime() - timedelta(days=45, hours=8)),
            "end_time":   str(now_datetime() - timedelta(days=44, hours=16)),
            "downtime_hours": 8.0,
            "notes": "RAM 16GB bị lỗi sector, thay RAM ECC Kingston DDR4",
        },
        {
            "reason": "Bảo trì",
            "start_time": str(now_datetime() - timedelta(days=7, hours=4)),
            "end_time":   str(now_datetime() - timedelta(days=7)),
            "downtime_hours": 4.0,
            "notes": "Bảo trì định kỳ 6 tháng — vệ sinh đầu dò, kiểm tra độ phân giải, hiệu chỉnh âm thanh",
        },
    ]

    for entry in entries:
        doc = frappe.get_doc({
            "doctype": "AC Asset Downtime Log",
            "asset": asset_name,
            "is_open": 0,
            **entry,
        })
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    print(f"  ✅ Created {len(entries)} downtime logs for {asset_name}")


def _seed_kpi_fields(asset_name: str) -> None:
    """Compute and store KPI values from downtime logs."""
    logs = frappe.get_all(
        "AC Asset Downtime Log",
        filters={"asset": asset_name, "is_open": 0},
        fields=["downtime_hours"],
    )
    total_downtime = sum(float(l["downtime_hours"] or 0) for l in logs)
    breakdown_count = len(logs)
    days_in_service = 365
    total_hours = days_in_service * 24
    downtime_hours = total_downtime
    uptime_pct = round((total_hours - downtime_hours) / total_hours * 100, 2)
    mttr = round(total_downtime / breakdown_count, 2) if breakdown_count else 0
    # MTBF = (operational hours) / (failure_count - 1)
    op_hours = total_hours - downtime_hours
    mtbf_days = round(op_hours / max(breakdown_count - 1, 1) / 24, 1) if breakdown_count > 1 else 0

    # Store computed KPI on AC Asset custom fields if they exist
    update_dict = {}
    asset_cols = frappe.db.get_table_columns("AC Asset")
    if "uptime_pct" in asset_cols:
        update_dict["uptime_pct"] = uptime_pct
    if "mttr_hours" in asset_cols:
        update_dict["mttr_hours"] = mttr
    if "mtbf_days" in asset_cols:
        update_dict["mtbf_days"] = mtbf_days

    if update_dict:
        frappe.db.set_value("AC Asset", asset_name, update_dict)
        frappe.db.commit()
        print(f"  ✅ KPI stored: uptime={uptime_pct}%, MTTR={mttr}h, MTBF={mtbf_days}d")
    else:
        print(f"  ℹ️  KPI fields not in schema yet — KPI tab shows computed stats from downtime logs directly")
        print(f"     Computed: uptime={uptime_pct}%, MTTR={mttr}h, MTBF={mtbf_days}d, breakdowns={breakdown_count}")


def _seed_depreciation_schedule(asset_name: str) -> None:
    """Generate monthly depreciation rows for the asset."""
    try:
        from assetcore.api.imm00 import regenerate_depreciation_schedule
        result = frappe.call(
            "assetcore.api.imm00.regenerate_depreciation_schedule",
            asset_name=asset_name,
            force=True,
        )
        if isinstance(result, dict) and result.get("message", {}).get("success"):
            print(f"  ✅ Depreciation schedule generated via API")
            return
    except Exception as e:
        print(f"  ⚠️  API call failed ({e}), seeding depreciation rows directly")

    # Seed manually if API fails
    DT = "AC Asset Depreciation Schedule"
    if not frappe.db.table_exists(DT):
        print(f"  ⚠️  {DT} table missing — run bench migrate first")
        return

    # Depreciation Schedule is a child table of AC Asset — check via parent field
    if frappe.db.count(DT, {"parent": asset_name, "parentfield": "depreciation_schedule"}) >= 10:
        print(f"  ⏭ Depreciation schedule already exists for {asset_name}")
        return

    gross = 1_250_000_000
    residual = 50_000_000
    months = 120
    monthly_dep = round((gross - residual) / months, 2)
    start = frappe.utils.getdate("2023-08-01")
    cols = set(frappe.db.get_table_columns(DT))

    accumulated = 0
    for i in range(24):   # seed 24 months of history
        dep_date = add_months(str(start), i)
        accumulated += monthly_dep
        payload = {
            "doctype": DT,
            "parent": asset_name,
            "parenttype": "AC Asset",
            "parentfield": "depreciation_schedule",
        }
        # Map to actual column names
        if "scheduled_date" in cols:
            payload["scheduled_date"] = dep_date
        if "depreciation_amount" in cols:
            payload["depreciation_amount"] = monthly_dep
        if "accumulated_amount" in cols:
            payload["accumulated_amount"] = round(accumulated, 2)
        if "remaining_value" in cols:
            payload["remaining_value"] = round(gross - accumulated, 2)
        if "status" in cols:
            payload["status"] = "Executed" if i < 22 else "Pending"
        doc = frappe.get_doc(payload)
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    print(f"  ✅ Created 24 months depreciation schedule for {asset_name}")


def _seed_lifecycle_events(asset_name: str) -> None:
    """Create lifecycle events for the asset audit trail."""
    DT = "Asset Lifecycle Event"
    if not frappe.db.table_exists(DT):
        print(f"  ⚠️  {DT} table missing")
        return

    if frappe.db.count(DT, {"asset": asset_name}) >= 3:
        print(f"  ⏭ Lifecycle events already exist for {asset_name}")
        return

    # Valid event_type values: "commissioned","activated","pm_started","pm_completed",
    # "repair_opened","repair_completed","calibration_started","calibration_passed",
    # "calibration_failed","incident_reported","out_of_service","restored","decommissioned",
    # "transferred","registered"
    events = [
        {
            "event_type": "commissioned",
            "from_status": "Draft",
            "to_status": "Commissioned",
            "actor": "Administrator",
            "event_timestamp": "2023-07-10 08:30:00",
            "remarks": "Nghiệm thu kỹ thuật tháng 7/2023 — Biên bản số NT-2023-0710",
        },
        {
            "event_type": "pm_completed",
            "from_status": "Active",
            "to_status": "Active",
            "actor": "Administrator",
            "event_timestamp": add_days(nowdate(), -90) + " 09:00:00",
            "remarks": "Bảo trì định kỳ 6 tháng — Phiếu BT-2026-0318",
        },
        {
            "event_type": "repair_completed",
            "from_status": "Under Repair",
            "to_status": "Active",
            "actor": "Administrator",
            "event_timestamp": add_days(nowdate(), -44) + " 16:00:00",
            "remarks": "Sửa chữa lỗi RAM — WO-CM-2026-00044",
        },
    ]

    for ev in events:
        cols = frappe.db.get_table_columns(DT)
        payload = {"doctype": DT, "asset": asset_name}
        for k, v in ev.items():
            if k in cols:
                payload[k] = v
        doc = frappe.get_doc(payload)
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    print(f"  ✅ Created {len(events)} lifecycle events for {asset_name}")


def _seed_procurement_plan() -> None:
    """Ensure at least one draft procurement plan exists.

    Proposal-first: tạo plan KÈM các đề xuất (Needs Request) đã duyệt qua API
    (create_procurement_plan nay chặn tạo plan rỗng). Nếu chưa có NR Approved
    nào → dựng skeleton plan trực tiếp để seed không gãy.
    """
    if frappe.db.count("IMM Procurement Plan", {"workflow_state": "Draft"}) > 0:
        print("  ⏭ Draft procurement plan already exists")
        return

    year = frappe.utils.getdate(nowdate()).year
    approved = frappe.get_all(
        "IMM Needs Request",
        filters={"docstatus": 1, "workflow_state": "Approved"},
        pluck="name", limit=5,
    )
    if approved:
        import json
        from assetcore.api.imm01 import _create_procurement_plan
        name = _create_procurement_plan(
            plan_year=year, plan_period="Annual",
            budget_envelope=5_000_000_000,
            needs_requests=json.dumps(approved),
        )["name"]
    else:
        doc = frappe.new_doc("IMM Procurement Plan")
        doc.plan_year = year
        doc.plan_period = "Annual"
        doc.budget_envelope = 5_000_000_000
        doc.insert(ignore_permissions=True)
        name = doc.name
        print("  ⚠ Chưa có Needs Request Approved → skeleton plan rỗng (direct insert)")
    frappe.db.commit()
    print(f"  ✅ Created draft procurement plan: {name}")


def run() -> None:
    print("=== Seeding realistic demo data ===")
    frappe.set_user("Administrator")

    # 1. Asset base data
    print(f"\n[Asset: {ASSET_NAME}]")
    if frappe.db.exists("AC Asset", ASSET_NAME):
        _seed_asset_base(ASSET_NAME)
        _seed_downtime_logs(ASSET_NAME)
        _seed_kpi_fields(ASSET_NAME)
        _seed_depreciation_schedule(ASSET_NAME)
        _seed_lifecycle_events(ASSET_NAME)
    else:
        print(f"  ⚠️  Asset {ASSET_NAME} not found — skipping asset seeding")

    # 2. Procurement plan
    print("\n[Procurement Plans]")
    _seed_procurement_plan()

    frappe.db.commit()
    print("\n=== Seeding complete ===")
