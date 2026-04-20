"""
Seed script: PM Work Orders + Asset Repair WOs for UAT testing.
Run: bench --site miyano execute assetcore.scripts.seed_pm_cm_data.run
"""
from __future__ import annotations
import frappe
from frappe.utils import nowdate, add_days, now_datetime


_DT_PM_SCHEDULE = "PM Schedule"
_STATUS_CANNOT_REPAIR = "Cannot Repair"
_TERMINAL_STATUSES = ("Completed", _STATUS_CANNOT_REPAIR)


def _get_assets(n: int = 8) -> list[str]:
    rows = frappe.get_all("AC Asset", filters={"lifecycle_status": ["in", ["Active", "Commissioned"]]},
                          fields=["name"], limit=n)
    return [r.name for r in rows]


def _ensure_technician() -> str:
    users = frappe.get_all("User", filters={"enabled": 1, "user_type": "System User",
                                             "name": ["!=", "Administrator"]},
                            fields=["name"], limit=1)
    return users[0].name if users else "Administrator"


def _get_or_create_schedule(asset: str, pm_type: str) -> str:
    name = f"PMS-{asset}-{pm_type}"
    if frappe.db.exists(_DT_PM_SCHEDULE, name):
        return name
    # Use db.insert to bypass controller validation (seed-only, not production flow)
    frappe.db.sql("""
        INSERT IGNORE INTO `tabPM Schedule`
            (name, asset_ref, pm_type, pm_interval_days,
             owner, creation, modified, modified_by, docstatus)
        VALUES (%s, %s, %s, 90, 'Administrator', NOW(), NOW(), 'Administrator', 0)
    """, (name, asset, pm_type))
    frappe.db.commit()
    return name


def seed_pm_work_orders(assets: list[str], technician: str):
    from frappe.utils import getdate
    today = getdate(nowdate())

    specs = [
        # (asset_idx, status, due_offset_days, is_late, pm_type, overall_result, notes)
        (0, "Scheduled", 5,   0, "Preventive",  None,         "PM tháng 4 theo lịch"),
        (1, "Scheduled", 1,   0, "Preventive",  None,         "Sắp đến hạn"),
        (2, "In Progress", -2, 1, "Preventive",  None,         "Đang thực hiện, trễ 2 ngày"),
        (3, "Completed",  -7,  0, "Preventive",  "Pass",       "Hoàn thành đúng hạn"),
        (4, "Completed",  -14, 0, "Inspection",  "Pass",       "Kiểm tra định kỳ 3 tháng"),
        (5, "Overdue",    -3,  1, "Preventive",  None,         "Quá hạn, chưa thực hiện"),
        (0, "Scheduled",  30,  0, "Calibration", None,         "PM kết hợp hiệu chuẩn"),
        (1, "Completed",  -30, 0, "Inspection",  "Conditional","Kết quả có điều kiện"),
        (2, "Overdue",    -10, 1, "Preventive",  None,         "Trễ hạn nghiêm trọng"),
        (3, "Scheduled",  15,  0, "Preventive",  None,         "Lịch tháng tới"),
    ]

    created = []
    for i, (a_idx, status, due_offset, is_late, pm_type, result, notes) in enumerate(specs):
        asset = assets[a_idx % len(assets)]
        schedule = _get_or_create_schedule(asset, pm_type)
        due_date = str(add_days(today, due_offset))
        scheduled_date = str(add_days(today, due_offset - 1))
        completion_date = str(add_days(today, due_offset + 1)) if result else None

        wo_name = frappe.generate_hash(length=8)
        frappe.db.sql("""
            INSERT INTO `tabPM Work Order`
                (name, asset_ref, pm_schedule, pm_type, wo_type, status,
                 is_late, due_date, scheduled_date, completion_date,
                 assigned_to, assigned_by, technician_notes, overall_result,
                 owner, creation, modified, modified_by, docstatus)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    'Administrator',NOW(),NOW(),'Administrator',0)
        """, (wo_name, asset, schedule, pm_type, "Preventive", status,
              is_late, due_date, scheduled_date, completion_date,
              technician, "Administrator", notes, result or None))
        created.append(wo_name)
        print(f"  Created PM WO: {wo_name} [{status}] asset={asset}")

    print(f"✅ Seeded {len(created)} PM Work Orders")
    return created


def seed_repair_work_orders(assets: list[str], technician: str):
    import datetime

    base_dt = now_datetime()

    specs = [
        # (asset_idx, status, priority, repair_type, sla_hours, hours_ago, root_cause, sla_breached, is_repeat)
        (0, "Open",           "Emergency", "Emergency",        4,  2,   None,         0, 0),
        (1, "Assigned",       "Urgent",    "Corrective",       24, 12,  None,         0, 0),
        (2, "Diagnosing",     "Normal",    "Corrective",       48, 36,  None,         0, 0),
        (3, "In Repair",      "Urgent",    "Corrective",       24, 30,  None,         1, 0),
        (4, "Pending Parts",  "Normal",    "Corrective",       72, 50,  None,         0, 0),
        (0, "Completed",      "Normal",    "Corrective",       48, 72,  "Electrical", 0, 0),
        (1, "Completed",      "Urgent",    "Corrective",       24, 96,  "Mechanical", 1, 1),
        (2, "Completed",      "Emergency", "Emergency",        4,  8,   "Software",   0, 0),
        (3, "Completed",      "Normal",    "Warranty Repair",  72, 168, "Wear and Tear", 0, 0),
        (4, _STATUS_CANNOT_REPAIR, "Normal", "Corrective",       48, 240, "Unknown",    1, 0),
    ]

    created = []
    for a_idx, status, priority, r_type, sla_hours, hours_ago, root_cause, sla_breached, is_repeat in specs:
        asset = assets[a_idx % len(assets)]
        open_dt = base_dt - datetime.timedelta(hours=hours_ago)
        completion_dt = base_dt - datetime.timedelta(hours=max(0, hours_ago - sla_hours)) \
            if status in _TERMINAL_STATUSES else None
        elapsed = round((completion_dt - open_dt).total_seconds() / 3600, 2) if completion_dt else 0

        docstatus = 1 if status in _TERMINAL_STATUSES else 0
        wo_name = frappe.generate_hash(length=8)
        frappe.db.sql("""
            INSERT INTO `tabAsset Repair`
                (name, asset_ref, repair_type, priority, status,
                 open_datetime, completion_datetime, sla_target_hours, mttr_hours,
                 sla_breached, is_repeat_failure, assigned_to, assigned_by,
                 root_cause_category, repair_summary, dept_head_name,
                 owner, creation, modified, modified_by, docstatus)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    'Administrator',NOW(),NOW(),'Administrator',%s)
        """, (wo_name, asset, r_type, priority, status,
              open_dt, completion_dt, sla_hours, elapsed,
              sla_breached, is_repeat, technician, "Administrator",
              root_cause or None,
              f"Đã sửa chữa, nguyên nhân: {root_cause}" if root_cause else None,
              "Trưởng khoa xác nhận" if root_cause else None,
              docstatus))
        created.append(wo_name)
        print(f"  Created Repair WO: {wo_name} [{status}] asset={asset}")

    print(f"✅ Seeded {len(created)} Repair Work Orders")
    return created


def run():
    frappe.set_user("Administrator")
    assets = _get_assets(8)
    if not assets:
        print("❌ No AC Asset records found — seed assets first")
        return

    technician = _ensure_technician()
    print(f"Using technician: {technician}")
    print(f"Using {len(assets)} assets: {assets}")

    print("\n--- Seeding PM Work Orders ---")
    seed_pm_work_orders(assets, technician)

    print("\n--- Seeding Repair Work Orders ---")
    seed_repair_work_orders(assets, technician)

    frappe.db.commit()
    print("\n🎉 Seed complete. Run bench --site miyano migrate if needed.")
