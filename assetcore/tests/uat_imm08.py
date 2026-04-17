"""
UAT Script cho IMM-08 — Preventive Maintenance
Chạy: bench --site miyano execute assetcore.tests.uat_imm08.run_all
"""
import json
import frappe
import traceback
from frappe.utils import nowdate, add_days, getdate

# ─── Constants ────────────────────────────────────────────────────────────────
DOCTYPE_WO    = "PM Work Order"
DOCTYPE_SCHED = "PM Schedule"
DOCTYPE_LOG   = "PM Task Log"
DOCTYPE_TPL   = "PM Checklist Template"
ITEM_CODE     = "VENT-PHL-V60"

# ─── Seed IDs ─────────────────────────────────────────────────────────────────
SEED_ASSET_01 = "ACC-ASS-UAT-PM-001"   # Due today — happy path
SEED_ASSET_02 = "ACC-ASS-UAT-PM-002"   # Overdue 10 ngày
SEED_ASSET_03 = "ACC-ASS-UAT-PM-003"   # Minor failure
SEED_ASSET_04 = "ACC-ASS-UAT-PM-004"   # Major failure → Out of Service
SEED_TPL_NAME = "UAT-PM-TEMPLATE-VENT"


def _p(ok: bool, msg: str) -> str:
    sym = "✅ PASS" if ok else "❌ FAIL"
    print(f"    {sym} — {msg}")
    return "PASS" if ok else "FAIL"


def _ensure_custom_fields():
    """Ensure custom fields required by AssetCore exist on Asset."""
    fields = [
        {"fieldname": "custom_risk_class", "fieldtype": "Select", "label": "Risk Class",
         "options": "Class I\nClass II\nClass III", "insert_after": "asset_category"},
        {"fieldname": "custom_last_pm_date", "fieldtype": "Date", "label": "Last PM Date",
         "insert_after": "custom_risk_class"},
        {"fieldname": "custom_next_pm_date", "fieldtype": "Date", "label": "Next PM Date",
         "insert_after": "custom_last_pm_date"},
        {"fieldname": "custom_last_repair_date", "fieldtype": "Date", "label": "Last Repair Date",
         "insert_after": "custom_next_pm_date"},
        {"fieldname": "custom_mttr_avg_hours", "fieldtype": "Float", "label": "Avg MTTR (hrs)",
         "insert_after": "custom_last_repair_date"},
        {"fieldname": "custom_pm_status", "fieldtype": "Data", "label": "PM Status",
         "insert_after": "custom_mttr_avg_hours"},
    ]
    for f in fields:
        if not frappe.db.has_column("Asset", f["fieldname"]):
            cf = frappe.get_doc({"doctype": "Custom Field", "dt": "Asset", **f})
            cf.flags.ignore_links = True
            cf.insert(ignore_permissions=True)
    frappe.db.commit()


def _cleanup():
    frappe.set_user("Administrator")
    frappe.flags.mute_emails = True
    _ensure_custom_fields()
    for model in [DOCTYPE_LOG, DOCTYPE_WO, DOCTYPE_SCHED]:
        frappe.db.delete(model, {"asset_ref": ["like", "ACC-ASS-UAT-PM-%"]})
    frappe.db.delete(DOCTYPE_TPL, {"template_name": SEED_TPL_NAME})
    for name in [SEED_ASSET_01, SEED_ASSET_02, SEED_ASSET_03, SEED_ASSET_04]:
        frappe.db.delete("Asset", {"name": name})
    frappe.db.commit()
    print("  [setup] Dọn dẹp xong.")


def _create_test_asset(name: str, category: str = "Mechanical Ventilator") -> str:
    if frappe.db.exists("Asset", name):
        return name
    doc = frappe.get_doc({
        "doctype": "Asset",
        "asset_name": f"Test Asset {name}",
        "item_code": ITEM_CODE,
        "company": frappe.defaults.get_global_default("company") or "Test Company",
        "purchase_date": add_days(nowdate(), -365),
        "gross_purchase_amount": 100_000_000,
        "asset_category": category,
        "status": "Active",
        "location": "ICU",
    })
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    frappe.db.set_value("Asset", doc.name, "name", name)
    frappe.db.commit()
    return name


def _create_pm_template() -> str:
    existing = frappe.db.get_value(DOCTYPE_TPL, {"template_name": SEED_TPL_NAME}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({
        "doctype": DOCTYPE_TPL,
        "template_name": SEED_TPL_NAME,
        "asset_category": "Mechanical Ventilator",
        "pm_type": "Quarterly",
        "items": [
            {"description": "Kiểm tra điện áp đầu vào (210–240V)", "measurement_type": "Numeric", "unit": "V", "expected_min": 210, "expected_max": 240, "is_critical": 1},
            {"description": "Kiểm tra áp suất khí nén (3.5–6 bar)", "measurement_type": "Numeric", "unit": "bar", "expected_min": 3.5, "expected_max": 6.0, "is_critical": 1},
            {"description": "Vệ sinh bộ lọc màng lọc", "measurement_type": "Pass/Fail", "is_critical": 0},
        ],
    })
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name  # actual name assigned by naming series


def _create_pm_schedule(asset: str, days_offset: int = 0) -> str:
    tpl_name = _create_pm_template()  # returns actual DB name
    due = add_days(nowdate(), days_offset)
    frappe.db.delete(DOCTYPE_SCHED, {"asset_ref": asset})
    doc = frappe.get_doc({
        "doctype": DOCTYPE_SCHED,
        "asset_ref": asset,
        "pm_type": "Quarterly",
        "pm_interval_days": 90,
        "next_due_date": due,
        "checklist_template": tpl_name,
        "status": "Active",
    })
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


# ═══════════════════════════════════════════════════════════════════════════════
# TC-PM-01: Tự động tạo PM Work Order
# ═══════════════════════════════════════════════════════════════════════════════
def tc_pm_01(results: dict):
    print("\n[TC-PM-01] Tự động tạo PM Work Order")
    print("-" * 50)
    try:
        _create_test_asset(SEED_ASSET_01)
        _create_pm_template()
        _create_pm_schedule(SEED_ASSET_01, days_offset=0)

        from assetcore.tasks import generate_pm_work_orders
        generate_pm_work_orders()
        frappe.db.commit()

        wos = frappe.db.get_all(DOCTYPE_WO,
            filters={"asset_ref": SEED_ASSET_01},
            fields=["name", "status", "due_date"])
        results["TC-PM-01-1"] = _p(len(wos) == 1, f"Tạo đúng 1 WO (tìm thấy {len(wos)})")

        if wos:
            wo = wos[0]
            results["TC-PM-01-2"] = _p(wo["status"] == "Open", f"Status = {wo['status']}")
            results["TC-PM-01-3"] = _p(wo["due_date"] == getdate(nowdate()), f"due_date = {wo['due_date']}")

            from assetcore.tasks import generate_pm_work_orders as gen2
            gen2()
            frappe.db.commit()
            wos2 = frappe.db.get_all(DOCTYPE_WO, filters={"asset_ref": SEED_ASSET_01})
            results["TC-PM-01-4"] = _p(len(wos2) == 1, f"Idempotent: vẫn 1 WO (tìm {len(wos2)})")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-PM-01"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-PM-02: PM hoàn thành đúng hạn
# ═══════════════════════════════════════════════════════════════════════════════
def tc_pm_02(results: dict):
    print("\n[TC-PM-02] PM hoàn thành đúng hạn")
    print("-" * 50)
    try:
        wos = frappe.db.get_all(DOCTYPE_WO,
            filters={"asset_ref": SEED_ASSET_01, "status": "Open"}, limit=1)
        if not wos:
            results["TC-PM-02"] = _p(False, "Không có WO Open — cần TC-PM-01 Pass trước")
            return

        wo_name = wos[0]["name"]

        from assetcore.api.imm08 import assign_technician
        r = assign_technician(name=wo_name, technician="Administrator", scheduled_date=nowdate())
        results["TC-PM-02-1"] = _p(r.get("success"), f"Assign: {r.get('error', 'OK')}")

        wo = frappe.get_doc(DOCTYPE_WO, wo_name)
        results["TC-PM-02-2"] = _p(wo.assigned_to == "Administrator", f"assigned_to = {wo.assigned_to}")

        checklist_data = []
        if wo.checklist_results:
            for row in wo.checklist_results:
                row.result = "Pass"
                row.measured_value = "220"
                checklist_data.append({"idx": row.idx, "result": "Pass", "measured_value": "220"})
            wo.save(ignore_permissions=True)
            frappe.db.commit()

        from assetcore.api.imm08 import submit_pm_result
        r2 = submit_pm_result(
            name=wo_name,
            checklist_results=json.dumps(checklist_data),
            overall_result="Pass",
            technician_notes="Hoàn thành bình thường UAT test",
            pm_sticker_attached=1,
            duration_minutes=45,
        )
        results["TC-PM-02-3"] = _p(r2.get("success"), f"Submit: {r2.get('error', 'OK')}")

        wo.reload()
        results["TC-PM-02-4"] = _p(wo.status == "Completed", f"status = {wo.status}")
        results["TC-PM-02-5"] = _p(wo.completion_date is not None, f"completion_date = {wo.completion_date}")

        sched = frappe.db.get_value(DOCTYPE_SCHED,
            {"asset_ref": SEED_ASSET_01}, ["next_due_date", "last_pm_date"], as_dict=True)
        if sched:
            results["TC-PM-02-6"] = _p(str(sched.last_pm_date) == nowdate(),
                                       f"last_pm_date = {sched.last_pm_date}")
            expected_next = add_days(nowdate(), 90)
            results["TC-PM-02-7"] = _p(str(sched.next_due_date) == expected_next,
                                       f"next_due_date = {sched.next_due_date}")

        log = frappe.db.get_all(DOCTYPE_LOG, filters={"pm_work_order": wo_name},
                                fields=["name", "is_late", "overall_result"])
        results["TC-PM-02-8"] = _p(len(log) == 1, f"PM Task Log tạo ({len(log)})")
        if log:
            results["TC-PM-02-9"] = _p(log[0]["is_late"] == 0, f"is_late = {log[0]['is_late']}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-PM-02"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-PM-03: PM trễ hạn & Overdue
# ═══════════════════════════════════════════════════════════════════════════════
def tc_pm_03(results: dict):
    print("\n[TC-PM-03] PM trễ hạn & Overdue")
    print("-" * 50)
    try:
        _create_test_asset(SEED_ASSET_02)
        _create_pm_schedule(SEED_ASSET_02, days_offset=-10)

        from assetcore.tasks import generate_pm_work_orders, check_pm_overdue
        generate_pm_work_orders()
        frappe.db.commit()

        wos = frappe.db.get_all(DOCTYPE_WO, filters={"asset_ref": SEED_ASSET_02},
                                fields=["name", "status", "due_date"])
        results["TC-PM-03-1"] = _p(len(wos) >= 1, f"WO tạo (tìm {len(wos)})")

        if wos:
            wo_name = wos[0]["name"]
            frappe.db.set_value(DOCTYPE_WO, wo_name, "due_date", add_days(nowdate(), -10))
            frappe.db.commit()

            check_pm_overdue()
            frappe.db.commit()

            wo = frappe.get_doc(DOCTYPE_WO, wo_name)
            results["TC-PM-03-2"] = _p(wo.status == "Overdue", f"Status = {wo.status}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-PM-03"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-PM-04: PM phát hiện lỗi Minor
# ═══════════════════════════════════════════════════════════════════════════════
def tc_pm_04(results: dict):
    print("\n[TC-PM-04] PM phát hiện lỗi Minor")
    print("-" * 50)
    try:
        _create_test_asset(SEED_ASSET_03)
        _create_pm_schedule(SEED_ASSET_03, days_offset=0)

        from assetcore.tasks import generate_pm_work_orders
        generate_pm_work_orders()
        frappe.db.commit()

        wos = frappe.db.get_all(DOCTYPE_WO,
            filters={"asset_ref": SEED_ASSET_03, "status": "Open"}, limit=1)
        if not wos:
            results["TC-PM-04"] = _p(False, "Không có WO Open")
            return

        wo_name = wos[0]["name"]
        wo = frappe.get_doc(DOCTYPE_WO, wo_name)
        wo.assigned_to = "Administrator"
        wo.save(ignore_permissions=True)

        checklist_data = []
        if wo.checklist_results:
            for i, row in enumerate(wo.checklist_results):
                result = "Fail–Minor" if i == 2 else "Pass"
                row.result = result
                row.measured_value = "220" if result == "Pass" else ""
                row.failure_note = "Bộ lọc xé rách nhẹ" if result == "Fail–Minor" else ""
                checklist_data.append({
                    "idx": row.idx, "result": result,
                    "measured_value": row.measured_value,
                    "failure_note": row.failure_note,
                })
            wo.save(ignore_permissions=True)
            frappe.db.commit()

        from assetcore.api.imm08 import submit_pm_result
        r = submit_pm_result(
            name=wo_name,
            checklist_results=json.dumps(checklist_data),
            overall_result="Pass with Minor Issues",
            technician_notes="Có lỗi nhỏ ở bộ lọc",
            pm_sticker_attached=1,
            duration_minutes=50,
        )
        results["TC-PM-04-1"] = _p(r.get("success"), f"Submit: {r.get('error', 'OK')}")

        wo.reload()
        results["TC-PM-04-2"] = _p(wo.status == "Completed", f"PM WO status = {wo.status}")

        cm_wo = r.get("data", {}).get("cm_wo_created")
        results["TC-PM-04-3"] = _p(cm_wo is not None, f"CM WO tạo = {cm_wo}")
        if cm_wo:
            cm = frappe.get_doc("Asset Repair", cm_wo)
            results["TC-PM-04-4"] = _p(cm.source_pm_wo == wo_name,
                                       f"source_pm_wo = {cm.source_pm_wo}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-PM-04"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-PM-05: PM phát hiện lỗi Major
# ═══════════════════════════════════════════════════════════════════════════════
def tc_pm_05(results: dict):
    print("\n[TC-PM-05] PM phát hiện lỗi Major")
    print("-" * 50)
    try:
        _create_test_asset(SEED_ASSET_04)
        _create_pm_schedule(SEED_ASSET_04, days_offset=0)

        from assetcore.tasks import generate_pm_work_orders
        generate_pm_work_orders()
        frappe.db.commit()

        wos = frappe.db.get_all(DOCTYPE_WO,
            filters={"asset_ref": SEED_ASSET_04, "status": "Open"}, limit=1)
        if not wos:
            results["TC-PM-05"] = _p(False, "Không có WO Open")
            return

        wo_name = wos[0]["name"]

        from assetcore.api.imm08 import report_major_failure
        r = report_major_failure(
            pm_wo_name=wo_name,
            failure_description="Compressor hỏng hoàn toàn UAT test",
        )
        results["TC-PM-05-1"] = _p(r.get("success"), f"report_major_failure: {r.get('error', 'OK')}")

        wo = frappe.get_doc(DOCTYPE_WO, wo_name)
        results["TC-PM-05-2"] = _p("Major" in (wo.status or ""), f"WO status = {wo.status}")

        asset_status = frappe.db.get_value("Asset", SEED_ASSET_04, "status")
        results["TC-PM-05-3"] = _p(asset_status == "Out of Service", f"Asset status = {asset_status}")

        cm_wo = r.get("data", {}).get("cm_wo_created")
        results["TC-PM-05-4"] = _p(cm_wo is not None, f"CM WO tạo = {cm_wo}")
        if cm_wo:
            cm = frappe.get_doc("Asset Repair", cm_wo)
            results["TC-PM-05-5"] = _p(cm.priority == "Emergency", f"CM WO priority = {cm.priority}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-PM-05"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-PM-06: Block PM khi Asset Out of Service
# ═══════════════════════════════════════════════════════════════════════════════
def tc_pm_06(results: dict):
    print("\n[TC-PM-06] Block PM khi Asset Out of Service")
    print("-" * 50)
    try:
        frappe.db.delete(DOCTYPE_WO, {"asset_ref": SEED_ASSET_04, "status": "Open"})
        frappe.db.commit()

        from assetcore.tasks import generate_pm_work_orders
        generate_pm_work_orders()
        frappe.db.commit()

        wos = frappe.db.get_all(DOCTYPE_WO, filters={"asset_ref": SEED_ASSET_04, "status": "Open"})
        results["TC-PM-06-1"] = _p(len(wos) == 0,
                                   f"Không tạo WO mới cho Out of Service (tìm {len(wos)})")

        frappe.db.set_value("Asset", SEED_ASSET_04, "status", "Active")
        # Ensure schedule exists with due today
        _create_pm_schedule(SEED_ASSET_04, days_offset=0)
        frappe.db.commit()
        generate_pm_work_orders()
        frappe.db.commit()

        wos2 = frappe.db.get_all(DOCTYPE_WO, filters={"asset_ref": SEED_ASSET_04, "status": "Open"})
        results["TC-PM-06-2"] = _p(len(wos2) >= 1,
                                   f"Sau restore Active → WO tạo (tìm {len(wos2)})")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-PM-06"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-PM-07: Dashboard KPI API
# ═══════════════════════════════════════════════════════════════════════════════
def tc_pm_07(results: dict):
    print("\n[TC-PM-07] Dashboard KPI API")
    print("-" * 50)
    try:
        import datetime
        today = datetime.date.today()
        from assetcore.api.imm08 import get_pm_dashboard_stats
        r = get_pm_dashboard_stats(year=today.year, month=today.month)
        results["TC-PM-07-1"] = _p(r.get("success"), f"API success: {r.get('error', 'OK')}")

        if r.get("success"):
            data = r["data"]
            kpis = data.get("kpis", {})
            results["TC-PM-07-2"] = _p("compliance_rate_pct" in kpis,
                                       f"compliance_rate_pct = {kpis.get('compliance_rate_pct')}")
            results["TC-PM-07-3"] = _p("total_scheduled" in kpis,
                                       f"total_scheduled = {kpis.get('total_scheduled')}")
            results["TC-PM-07-4"] = _p("trend_6months" in data,
                                       f"trend_6months = {len(data.get('trend_6months', []))} entries")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-PM-07"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def run_all():
    frappe.set_user("Administrator")
    results: dict[str, str] = {}

    print("\n" + "=" * 70)
    print("IMM-08 UAT — PREVENTIVE MAINTENANCE")
    print("=" * 70)

    _cleanup()
    tc_pm_01(results)
    tc_pm_02(results)
    tc_pm_03(results)
    tc_pm_04(results)
    tc_pm_05(results)
    tc_pm_06(results)
    tc_pm_07(results)

    print("\n" + "=" * 70)
    print("TỔNG HỢP KẾT QUẢ IMM-08 UAT")
    print("=" * 70)
    passed = sum(1 for v in results.values() if v == "PASS")
    failed = sum(1 for v in results.values() if v == "FAIL")
    excepts = sum(1 for v in results.values() if v == "EXCEPTION")
    total = len(results)

    for tc, status in results.items():
        if status == "PASS":
            sym = "✅"
        elif status == "FAIL":
            sym = "❌"
        else:
            sym = "💥"
        print(f"  {sym} {tc}: {status}")

    rate = round(passed / total * 100, 1) if total > 0 else 0
    print(f"\n  Tổng: {total} | Pass: {passed} | Fail: {failed} | Exception: {excepts}")
    print(f"  Pass rate: {rate}%")
    verdict = "✅ ĐẠT YÊU CẦU (≥80%)" if rate >= 80 else "❌ CHƯA ĐẠT YÊU CẦU"
    print(f"  {verdict}")

    return results
