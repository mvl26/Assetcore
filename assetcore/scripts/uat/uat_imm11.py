"""
UAT IMM-11 — Calibration (smoke test)
Chạy: bench --site miyano execute assetcore.scripts.uat.uat_imm11.run_all
"""
import traceback
import frappe
from frappe.utils import nowdate, add_days

DT_SCHED = "IMM Calibration Schedule"
DT_CAL = "IMM Asset Calibration"
DT_ASSET = "AC Asset"
DT_MODEL = "IMM Device Model"
DT_SUPPLIER = "AC Supplier"

_CACHE_NS = "uat_imm11"


def _p(ok: bool, msg: str) -> str:
    sym = "✅ PASS" if ok else "❌ FAIL"
    print(f"    {sym} — {msg}")
    return "PASS" if ok else "FAIL"


def _asset() -> str:
    return frappe.cache().hget(_CACHE_NS, "asset") or ""


def _cleanup():
    frappe.set_user("Administrator")
    frappe.flags.mute_emails = True
    existing_asset = frappe.cache().hget(_CACHE_NS, "asset")
    if existing_asset:
        frappe.db.delete(DT_CAL, {"asset": existing_asset})
        frappe.db.delete(DT_SCHED, {"asset": existing_asset})
        frappe.db.delete(DT_ASSET, {"name": existing_asset})
    frappe.cache().hdel(_CACHE_NS, "asset")
    frappe.cache().hdel(_CACHE_NS, "schedule")
    frappe.cache().hdel(_CACHE_NS, "cal")
    frappe.db.commit()
    print("  [setup] Dọn dẹp xong.")


def _seed():
    # Seed device model yêu cầu calibration
    model_name = "UAT-IMM11-MODEL"
    if not frappe.db.exists(DT_MODEL, model_name):
        m = frappe.new_doc(DT_MODEL)
        m.model_name = model_name
        m.manufacturer = "UAT Manufacturer"
        m.medical_device_class = "Class II"
        m.risk_classification = "Medium"
        m.is_calibration_required = 1
        m.calibration_interval_days = 365
        m.default_calibration_type = "External"
        m.flags.ignore_mandatory = True
        m.flags.ignore_links = True
        m.insert(ignore_permissions=True)
        frappe.db.set_value(DT_MODEL, m.name, "name", model_name, update_modified=False)

    # Seed asset
    asset = frappe.new_doc(DT_ASSET)
    asset.asset_name = "UAT Máy đo IMM-11"
    asset.serial_no = f"SN-UAT-IMM11-{frappe.generate_hash(length=5)}"
    asset.device_model = model_name
    asset.lifecycle_status = "Active"
    asset.flags.ignore_mandatory = True
    asset.flags.ignore_links = True
    asset.insert(ignore_permissions=True)
    frappe.cache().hset(_CACHE_NS, "asset", asset.name)
    frappe.db.commit()
    print(f"  [setup] Asset seeded: {asset.name}")
    return asset.name


# ═══════════════════════════════════════════════════════════════════════════════
# TC-11-01: Tạo Calibration Schedule qua API
# ═══════════════════════════════════════════════════════════════════════════════
def tc_11_01(results: dict):
    print("\n[TC-11-01] Tạo Calibration Schedule qua API")
    print("-" * 50)
    try:
        from assetcore.api.imm11 import create_calibration_schedule
        res = create_calibration_schedule(
            asset=_asset(),
            calibration_type="External",
            interval_days=365,
        )
        results["TC-11-01-1"] = _p(res.get("success") is True, f"create_calibration_schedule → {res.get('success')}")
        sched_name = res.get("data", {}).get("name")
        results["TC-11-01-2"] = _p(bool(sched_name), f"Schedule name = {sched_name}")
        frappe.cache().hset(_CACHE_NS, "schedule", sched_name)
    except Exception as e:
        traceback.print_exc()
        results["TC-11-01"] = f"EXCEPTION: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-11-02: List schedules (response schema)
# ═══════════════════════════════════════════════════════════════════════════════
def tc_11_02(results: dict):
    print("\n[TC-11-02] list_calibration_schedules")
    print("-" * 50)
    try:
        from assetcore.api.imm11 import list_calibration_schedules
        res = list_calibration_schedules(filters='{"asset": "' + _asset() + '"}')
        results["TC-11-02-1"] = _p(res.get("success") is True, "list → success")
        payload = res.get("data", {})
        # Tier 2 contract: svc.list_schedules trả {data: [...], pagination: {...}}
        rows_key = "data" if "data" in payload else "items"
        rows = payload.get(rows_key, [])
        results["TC-11-02-2"] = _p(bool(payload), f"response có payload (keys: {list(payload.keys())})")
        results["TC-11-02-3"] = _p(len(rows) >= 1, f"có {len(rows)} schedule")
    except Exception as e:
        traceback.print_exc()
        results["TC-11-02"] = f"EXCEPTION: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-11-03: Tạo Calibration WO (In-House) + gate asset operational
# ═══════════════════════════════════════════════════════════════════════════════
def tc_11_03(results: dict):
    print("\n[TC-11-03] Tạo CAL WO In-House + BR-11-07 gate")
    print("-" * 50)
    try:
        from assetcore.api.imm11 import create_calibration
        asset = _asset()
        res = create_calibration(
            asset=asset,
            calibration_type="In-House",
            scheduled_date=nowdate(),
            technician="Administrator",
            calibration_schedule=frappe.cache().hget(_CACHE_NS, "schedule"),
            reference_standard_serial="REF-UAT-001",
        )
        results["TC-11-03-1"] = _p(res.get("success") is True, f"create_calibration → {res.get('success')}")
        cal_name = res.get("data", {}).get("name")
        results["TC-11-03-2"] = _p(bool(cal_name), f"CAL WO name = {cal_name}")
        frappe.cache().hset(_CACHE_NS, "cal", cal_name)

        # Gate BR-11-07: block khi asset Out of Service (không phải recalibration)
        frappe.db.set_value(DT_ASSET, asset, "lifecycle_status", "Out of Service")
        frappe.db.commit()
        res_block = create_calibration(
            asset=asset, calibration_type="In-House",
            scheduled_date=nowdate(), technician="Administrator",
        )
        # Tier 2 refactor: ErrorCode.BAD_STATE thay cho "ASSET_NOT_OPERATIONAL"
        results["TC-11-03-3"] = _p(
            res_block.get("success") is False
            and res_block.get("code") in ("BAD_STATE", "ASSET_NOT_OPERATIONAL"),
            f"BR-11-07 gate block OOS asset (code={res_block.get('code')})",
        )
        # Revert
        frappe.db.set_value(DT_ASSET, asset, "lifecycle_status", "Active")
        frappe.db.commit()
    except Exception as e:
        traceback.print_exc()
        results["TC-11-03"] = f"EXCEPTION: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-11-04: Scheduler — check_calibration_expiry
# ═══════════════════════════════════════════════════════════════════════════════
def tc_11_04(results: dict):
    print("\n[TC-11-04] Scheduler: check_calibration_expiry")
    print("-" * 50)
    try:
        from assetcore.services.imm11 import check_calibration_expiry

        # Asset có next_calibration_date = +365 ngày → On Schedule
        asset = _asset()
        frappe.db.set_value(DT_ASSET, asset, "next_calibration_date", add_days(nowdate(), 365))
        frappe.db.commit()
        check_calibration_expiry()
        status = frappe.db.get_value(DT_ASSET, asset, "calibration_status")
        results["TC-11-04-1"] = _p(status == "On Schedule", f"365 ngày → On Schedule (got: {status})")

        # +20 ngày → Due Soon
        frappe.db.set_value(DT_ASSET, asset, "next_calibration_date", add_days(nowdate(), 20))
        frappe.db.commit()
        check_calibration_expiry()
        status = frappe.db.get_value(DT_ASSET, asset, "calibration_status")
        results["TC-11-04-2"] = _p(status == "Due Soon", f"20 ngày → Due Soon (got: {status})")

        # -5 ngày → Overdue
        frappe.db.set_value(DT_ASSET, asset, "next_calibration_date", add_days(nowdate(), -5))
        frappe.db.commit()
        check_calibration_expiry()
        status = frappe.db.get_value(DT_ASSET, asset, "calibration_status")
        results["TC-11-04-3"] = _p(status == "Overdue", f"-5 ngày → Overdue (got: {status})")
    except Exception as e:
        traceback.print_exc()
        results["TC-11-04"] = f"EXCEPTION: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-11-05: Lookback assessment (BR-11-03)
# ═══════════════════════════════════════════════════════════════════════════════
def tc_11_05(results: dict):
    print("\n[TC-11-05] perform_lookback_assessment")
    print("-" * 50)
    try:
        from assetcore.services.imm11 import perform_lookback_assessment
        model = frappe.db.get_value(DT_ASSET, _asset(), "device_model")
        # Tạo 2 asset cùng model Active
        peers = []
        for i in range(2):
            a = frappe.new_doc(DT_ASSET)
            a.asset_name = f"UAT-Lookback-Peer-{i}"
            a.serial_no = f"LOOK-{frappe.generate_hash(length=5)}"
            a.device_model = model
            a.lifecycle_status = "Active"
            a.flags.ignore_mandatory = True
            a.flags.ignore_links = True
            a.insert(ignore_permissions=True)
            peers.append(a.name)
        frappe.db.commit()

        lookback = perform_lookback_assessment(model, _asset())
        results["TC-11-05-1"] = _p(
            all(p in lookback for p in peers),
            f"Tìm thấy {len(lookback)} peer assets cùng device_model",
        )

        # Cleanup peers
        for p in peers:
            frappe.db.delete(DT_ASSET, {"name": p})
        frappe.db.commit()
    except Exception as e:
        traceback.print_exc()
        results["TC-11-05"] = f"EXCEPTION: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-11-06: KPIs endpoint
# ═══════════════════════════════════════════════════════════════════════════════
def tc_11_06(results: dict):
    print("\n[TC-11-06] get_calibration_kpis")
    print("-" * 50)
    try:
        from assetcore.api.imm11 import get_calibration_kpis
        res = get_calibration_kpis()
        results["TC-11-06-1"] = _p(res.get("success") is True, "KPI → success")
        kpis = res.get("data", {}).get("kpis", {})
        expected_keys = {"total_this_month", "completed", "failed", "pass_rate_pct",
                         "overdue_assets", "due_soon_assets"}
        results["TC-11-06-2"] = _p(
            expected_keys.issubset(set(kpis.keys())),
            f"KPIs có đủ keys: {sorted(kpis.keys())}",
        )
    except Exception as e:
        traceback.print_exc()
        results["TC-11-06"] = f"EXCEPTION: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-11-07: BR-11-05 Immutable sau Submit (block cancel/delete)
# ═══════════════════════════════════════════════════════════════════════════════
def tc_11_07(results: dict):
    print("\n[TC-11-07] BR-11-05: Immutable sau Submit")
    print("-" * 50)
    try:
        # Tạo CAL + thêm measurement Pass + Submit
        cal = frappe.new_doc(DT_CAL)
        cal.asset = _asset()
        cal.calibration_type = "In-House"
        cal.scheduled_date = nowdate()
        cal.actual_date = nowdate()
        cal.technician = "Administrator"
        cal.reference_standard_serial = "REF-UAT-BR05"
        cal.append("measurements", {
            "parameter_name": "Voltage", "unit": "V",
            "nominal_value": 220, "tolerance_positive": 5, "tolerance_negative": 5,
            "measured_value": 221,
        })
        cal.flags.ignore_mandatory = True
        cal.flags.ignore_links = True
        cal.insert(ignore_permissions=True)
        cal.submit()

        # Cancel bị chặn
        try:
            cal.cancel()
            results["TC-11-07-1"] = _p(False, "Cancel KHÔNG bị chặn (BR-11-05 sai)")
        except frappe.ValidationError:
            results["TC-11-07-1"] = _p(True, "Cancel bị chặn bởi BR-11-05")

        # Delete bị chặn
        try:
            frappe.delete_doc(DT_CAL, cal.name, ignore_permissions=True)
            results["TC-11-07-2"] = _p(False, "Delete KHÔNG bị chặn (BR-11-05 sai)")
        except frappe.ValidationError:
            results["TC-11-07-2"] = _p(True, "Delete bị chặn bởi BR-11-05")
    except Exception as e:
        traceback.print_exc()
        results["TC-11-07"] = f"EXCEPTION: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-11-08: BR-11-04 next_calibration_date = certificate_date + interval
# ═══════════════════════════════════════════════════════════════════════════════
def tc_11_08(results: dict):
    print("\n[TC-11-08] BR-11-04: next_cal tính từ certificate_date")
    print("-" * 50)
    try:
        from frappe.utils import getdate
        # Tạo lab hợp lệ
        lab_name = frappe.db.get_value(DT_SUPPLIER,
                                        {"supplier_name": "Trung tâm Đo lường Chất lượng 3"},
                                        "name")
        if not lab_name:
            # Fallback: tạo lab tạm
            lab = frappe.new_doc(DT_SUPPLIER)
            lab.supplier_name = "UAT Lab BR-11-04"
            lab.vendor_type = "Calibration Lab"
            lab.iso_17025_cert = "UAT-VLAS-999"
            lab.iso_17025_expiry = add_days(nowdate(), 365)
            lab.is_active = 1
            lab.flags.ignore_mandatory = True
            lab.insert(ignore_permissions=True)
            lab_name = lab.name

        cert_date = add_days(nowdate(), -7)  # nhận chứng chỉ 7 ngày trước
        cal = frappe.new_doc(DT_CAL)
        cal.asset = _asset()
        cal.calibration_type = "External"
        cal.scheduled_date = add_days(nowdate(), 30)  # due_date khác cert_date
        cal.actual_date = cert_date
        cal.technician = "Administrator"
        cal.lab_supplier = lab_name
        cal.lab_accreditation_number = "VLAS-T-028"
        cal.certificate_file = "/files/uat_cert_br04.pdf"
        cal.certificate_date = cert_date
        cal.status = "Certificate Received"
        cal.append("measurements", {
            "parameter_name": "WBC", "unit": "x10^9/L",
            "nominal_value": 7.5, "tolerance_positive": 3, "tolerance_negative": 3,
            "measured_value": 7.6,
        })
        cal.flags.ignore_mandatory = True
        cal.insert(ignore_permissions=True)
        cal.submit()

        expected_next = add_days(cert_date,
                                  frappe.db.get_value(DT_MODEL,
                                                       frappe.db.get_value(DT_ASSET, _asset(), "device_model"),
                                                       "calibration_interval_days") or 365)
        actual_next = frappe.db.get_value(DT_CAL, cal.name, "next_calibration_date")
        results["TC-11-08-1"] = _p(
            getdate(actual_next) == getdate(expected_next),
            f"next_cal = cert_date + interval ({actual_next} vs expected {expected_next})",
        )

        asset_next = frappe.db.get_value(DT_ASSET, _asset(), "next_calibration_date")
        results["TC-11-08-2"] = _p(
            getdate(asset_next) == getdate(expected_next),
            f"Asset.next_calibration_date sync ({asset_next})",
        )
    except Exception as e:
        traceback.print_exc()
        results["TC-11-08"] = f"EXCEPTION: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-11-09: BR-11-02 Fail → OOS + auto CAPA + lookback populated
# ═══════════════════════════════════════════════════════════════════════════════
def tc_11_09(results: dict):
    print("\n[TC-11-09] BR-11-02: Fail → OOS + CAPA auto")
    print("-" * 50)
    try:
        asset = _asset()
        # Đảm bảo asset Active trước khi fail test
        frappe.db.set_value(DT_ASSET, asset, "lifecycle_status", "Active")

        # Seed peer cùng device_model để test lookback
        model = frappe.db.get_value(DT_ASSET, asset, "device_model")
        peer = frappe.new_doc(DT_ASSET)
        peer.asset_name = "UAT BR-11-02 Peer"
        peer.serial_no = f"PEER-{frappe.generate_hash(length=5)}"
        peer.device_model = model
        peer.lifecycle_status = "Active"
        peer.flags.ignore_mandatory = True
        peer.flags.ignore_links = True
        peer.insert(ignore_permissions=True)
        frappe.db.commit()

        # Tạo CAL In-House với measurement Fail
        cal = frappe.new_doc(DT_CAL)
        cal.asset = asset
        cal.calibration_type = "In-House"
        cal.scheduled_date = nowdate()
        cal.actual_date = nowdate()
        cal.technician = "Administrator"
        cal.reference_standard_serial = "REF-FAIL"
        cal.append("measurements", {
            "parameter_name": "HGB", "unit": "g/dL",
            "nominal_value": 14.0, "tolerance_positive": 3, "tolerance_negative": 3,
            "measured_value": 15.5,  # out of tolerance → Fail
        })
        cal.flags.ignore_mandatory = True
        cal.insert(ignore_permissions=True)
        cal.submit()

        # Verify 1: overall_result = Failed
        overall = frappe.db.get_value(DT_CAL, cal.name, "overall_result")
        results["TC-11-09-1"] = _p(overall == "Failed", f"overall_result = {overall}")

        # Verify 2: Asset OOS
        asset_status = frappe.db.get_value(DT_ASSET, asset, "lifecycle_status")
        results["TC-11-09-2"] = _p(asset_status == "Out of Service",
                                    f"Asset lifecycle → {asset_status}")

        # Verify 3: calibration_status trên Asset = Calibration Failed
        cal_status = frappe.db.get_value(DT_ASSET, asset, "calibration_status")
        results["TC-11-09-3"] = _p(cal_status == "Calibration Failed",
                                    f"Asset.calibration_status = {cal_status}")

        # Verify 4: CAPA auto-tạo
        capa_ref = frappe.db.get_value(DT_CAL, cal.name, "capa_record")
        results["TC-11-09-4"] = _p(bool(capa_ref), f"CAPA tạo tự động: {capa_ref}")

        # Verify 5: Lookback populated trên CAPA (chứa peer)
        if capa_ref:
            lookback = frappe.db.get_value("IMM CAPA Record", capa_ref, "lookback_assets") or ""
            results["TC-11-09-5"] = _p(peer.name in lookback,
                                        f"Lookback chứa peer '{peer.name}' (got: {lookback})")
            lookback_status = frappe.db.get_value("IMM CAPA Record", capa_ref, "lookback_status")
            results["TC-11-09-6"] = _p(lookback_status == "In Progress",
                                        f"lookback_status = {lookback_status}")

        # Restore asset cho TC sau
        frappe.db.set_value(DT_ASSET, asset, "lifecycle_status", "Active")
        frappe.db.delete(DT_ASSET, {"name": peer.name})
        frappe.db.commit()
    except Exception as e:
        traceback.print_exc()
        results["TC-11-09"] = f"EXCEPTION: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-11-10: BR-11-01 Block submit External khi thiếu certificate/accreditation
# ═══════════════════════════════════════════════════════════════════════════════
def tc_11_10(results: dict):
    print("\n[TC-11-10] BR-11-01: External validation")
    print("-" * 50)
    try:
        # Tạo lab tạm với ISO 17025 hợp lệ
        lab = frappe.new_doc(DT_SUPPLIER)
        lab.supplier_name = f"UAT BR-11-01 Lab {frappe.generate_hash(length=4)}"
        lab.vendor_type = "Calibration Lab"
        lab.iso_17025_cert = "UAT-17025"
        lab.iso_17025_expiry = add_days(nowdate(), 365)
        lab.is_active = 1
        lab.flags.ignore_mandatory = True
        lab.insert(ignore_permissions=True)

        # Case A: lab không có vendor_type Calibration Lab → throw
        bad_lab = frappe.new_doc(DT_SUPPLIER)
        bad_lab.supplier_name = f"UAT Non-Lab {frappe.generate_hash(length=4)}"
        bad_lab.vendor_type = "Manufacturer"
        bad_lab.is_active = 1
        bad_lab.flags.ignore_mandatory = True
        bad_lab.insert(ignore_permissions=True)

        cal_bad = frappe.new_doc(DT_CAL)
        cal_bad.asset = _asset()
        cal_bad.calibration_type = "External"
        cal_bad.scheduled_date = nowdate()
        cal_bad.technician = "Administrator"
        cal_bad.lab_supplier = bad_lab.name
        cal_bad.flags.ignore_mandatory = True
        try:
            cal_bad.insert(ignore_permissions=True)
            results["TC-11-10-1"] = _p(False, "Non-Calibration-Lab KHÔNG bị chặn")
        except frappe.ValidationError:
            results["TC-11-10-1"] = _p(True, "Non-Calibration-Lab bị chặn (VR-11-02)")

        # Case B: External với status=Certificate Received nhưng thiếu cert file → throw
        cal_no_cert = frappe.new_doc(DT_CAL)
        cal_no_cert.asset = _asset()
        cal_no_cert.calibration_type = "External"
        cal_no_cert.status = "Certificate Received"
        cal_no_cert.scheduled_date = nowdate()
        cal_no_cert.technician = "Administrator"
        cal_no_cert.lab_supplier = lab.name
        cal_no_cert.flags.ignore_mandatory = True
        try:
            cal_no_cert.insert(ignore_permissions=True)
            results["TC-11-10-2"] = _p(False, "Thiếu certificate KHÔNG bị chặn")
        except frappe.ValidationError:
            results["TC-11-10-2"] = _p(True, "Thiếu certificate bị chặn (VR-11-03)")

        # Cleanup
        frappe.db.delete(DT_SUPPLIER, {"name": lab.name})
        frappe.db.delete(DT_SUPPLIER, {"name": bad_lab.name})
        frappe.db.commit()
    except Exception as e:
        traceback.print_exc()
        results["TC-11-10"] = f"EXCEPTION: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def run_all():
    print("\n" + "=" * 70)
    print("UAT IMM-11 — Calibration (smoke + business rules)")
    print("=" * 70)

    _cleanup()
    _seed()

    results = {}
    tc_11_01(results)
    tc_11_02(results)
    tc_11_03(results)
    tc_11_04(results)
    tc_11_05(results)
    tc_11_06(results)
    tc_11_07(results)
    tc_11_08(results)
    tc_11_09(results)
    tc_11_10(results)

    total = len(results)
    passed = sum(1 for v in results.values() if v == "PASS")
    failed = total - passed

    print("\n" + "=" * 70)
    print(f"KẾT QUẢ: {passed}/{total} PASS  |  {failed} FAIL")
    print("=" * 70)
    if failed:
        print("\nCác TC FAIL:")
        for k, v in results.items():
            if v != "PASS":
                print(f"  ❌ {k} = {v}")
    else:
        print("  ✅ Tất cả test case PASS!")
    return results
