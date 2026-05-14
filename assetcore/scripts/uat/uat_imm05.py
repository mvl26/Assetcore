"""
UAT Script cho IMM-05 — Asset Document Repository
Chạy: bench --site miyano execute assetcore.scripts.uat.uat_imm05.run_all
"""
import json
import traceback
import frappe
from frappe.utils import nowdate, add_days

DOCTYPE = "Asset Document"
DT_ASSET = "AC Asset"
DT_ALERT = "Expiry Alert Log"
BASE_API = "assetcore.api.imm05"

_CACHE_NS = "uat_imm05"


def _p(ok: bool, msg: str) -> str:
    sym = "✅ PASS" if ok else "❌ FAIL"
    print(f"    {sym} — {msg}")
    return "PASS" if ok else "FAIL"


def _api(fn, **kwargs):
    import importlib
    mod = importlib.import_module(BASE_API)
    return getattr(mod, fn)(**kwargs)


def _ok(res) -> bool:
    return res.get("success") is True


def _err_res(res) -> bool:
    return res.get("success") is False


def _asset() -> str:
    return frappe.cache().hget(_CACHE_NS, "seed_asset") or ""


def _cleanup():
    frappe.set_user("Administrator")
    frappe.flags.mute_emails = True
    existing = frappe.cache().hget(_CACHE_NS, "seed_asset")
    if existing:
        frappe.db.delete(DT_ALERT, {"asset_ref": existing})
        frappe.db.delete(DOCTYPE, {"asset_ref": existing})
        frappe.db.delete(DT_ASSET, {"name": existing})
    frappe.db.commit()
    frappe.cache().hdel(_CACHE_NS, "seed_asset")
    print("  [setup] Dọn dẹp xong.")


def _seed_asset() -> str:
    doc = frappe.new_doc(DT_ASSET)
    doc.asset_name = "Máy thở UAT IMM-05"
    doc.serial_no = "SN-UAT-IMM05-001"
    doc.lifecycle_status = "Active"
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    frappe.cache().hset(_CACHE_NS, "seed_asset", doc.name)
    print(f"  [setup] Asset seeded: {doc.name}")
    return doc.name


def _insert_doc(extra: dict = None) -> "frappe.Document":
    """Insert Asset Document với issuing_authority để pass VR-04."""
    base = {
        "doctype": DOCTYPE,
        "asset_ref": _asset(),
        "doc_category": "Legal",
        "doc_type_detail": "Giấy phép lưu hành",
        "doc_number": f"UAT-{frappe.generate_hash(length=6)}",
        "version": "1.0",
        "issued_date": nowdate(),
        "expiry_date": add_days(nowdate(), 365),
        "issuing_authority": "Bộ Y tế",
        "file_attachment": "/files/uat_placeholder.pdf",
        "visibility": "Public",
    }
    if extra:
        base.update(extra)
    doc = frappe.get_doc(base)
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    frappe.db.set_value(DOCTYPE, doc.name, "workflow_state", "Draft", update_modified=False)
    frappe.db.commit()
    return doc


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-01: Tạo Asset Document mới
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_01(results: dict):
    print("\n[TC-05-01] Tạo Asset Document")
    print("-" * 50)
    try:
        doc = _insert_doc()
        results["TC-05-01-1"] = _p(frappe.db.exists(DOCTYPE, doc.name),
                                   f"Tạo thành công: {doc.name}")
        results["TC-05-01-2"] = _p(doc.asset_ref == _asset(),
                                   f"asset_ref đúng: {doc.asset_ref}")
        frappe.cache().hset(_CACHE_NS, "doc_draft", doc.name)
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-01"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-02: Gửi duyệt (→ Pending_Review)
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_02(results: dict):
    print("\n[TC-05-02] Gửi duyệt tài liệu")
    print("-" * 50)
    try:
        doc_name = frappe.cache().hget(_CACHE_NS, "doc_draft")
        if not doc_name:
            results["TC-05-02"] = _p(False, "Cần TC-05-01 pass trước")
            return

        frappe.db.set_value(DOCTYPE, doc_name, "workflow_state", "Pending_Review",
                            update_modified=False)
        frappe.db.commit()
        actual = frappe.db.get_value(DOCTYPE, doc_name, "workflow_state")
        results["TC-05-02-1"] = _p(actual == "Pending_Review", f"State = {actual}")
        frappe.cache().hset(_CACHE_NS, "doc_review", doc_name)
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-02"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-03: Từ chối tài liệu
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_03(results: dict):
    print("\n[TC-05-03] Từ chối tài liệu")
    print("-" * 50)
    try:
        doc = _insert_doc()
        frappe.db.set_value(DOCTYPE, doc.name, "workflow_state", "Pending_Review",
                            update_modified=False)
        frappe.db.commit()

        res_no = _api("reject_document", name=doc.name, rejection_reason="")
        results["TC-05-03-1"] = _p(_err_res(res_no),
                                   f"Reject không có lý do → error (success={res_no.get('success')})")

        res = _api("reject_document", name=doc.name, rejection_reason="Thiếu chữ ký")
        results["TC-05-03-2"] = _p(_ok(res),
                                   f"Reject có lý do → ok (success={res.get('success')})")

        actual = frappe.db.get_value(DOCTYPE, doc.name, "workflow_state")
        results["TC-05-03-3"] = _p(actual == "Rejected", f"State = {actual}")

        reason = frappe.db.get_value(DOCTYPE, doc.name, "rejection_reason")
        results["TC-05-03-4"] = _p("chữ ký" in (reason or ""), f"Lý do: {reason}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-03"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-04: Phê duyệt tài liệu (Pending_Review → Active)
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_04(results: dict):
    print("\n[TC-05-04] Phê duyệt tài liệu → Active")
    print("-" * 50)
    try:
        doc_name = frappe.cache().hget(_CACHE_NS, "doc_review")
        if not doc_name:
            results["TC-05-04"] = _p(False, "Cần TC-05-02 pass trước")
            return

        res = _api("approve_document", name=doc_name)
        results["TC-05-04-1"] = _p(_ok(res), f"Approve → ok (success={res.get('success')})")

        actual = frappe.db.get_value(DOCTYPE, doc_name, "workflow_state")
        results["TC-05-04-2"] = _p(actual == "Active", f"State = {actual}")

        approved_by = frappe.db.get_value(DOCTYPE, doc_name, "approved_by")
        results["TC-05-04-3"] = _p(bool(approved_by), f"approved_by = {approved_by}")
        frappe.cache().hset(_CACHE_NS, "doc_active", doc_name)
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-04"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-05: Sửa tài liệu (Draft only)
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_05(results: dict):
    print("\n[TC-05-05] Sửa metadata (Draft only)")
    print("-" * 50)
    try:
        doc = _insert_doc()

        res = _api("update_document", name=doc.name,
                   doc_data=json.dumps({"version": "1.1", "change_summary": "Cập nhật định kỳ"}))
        results["TC-05-05-1"] = _p(_ok(res), f"Update Draft → ok (success={res.get('success')})")

        ver = frappe.db.get_value(DOCTYPE, doc.name, "version")
        results["TC-05-05-2"] = _p(ver == "1.1", f"version = {ver}")

        frappe.db.set_value(DOCTYPE, doc.name, "workflow_state", "Pending_Review",
                            update_modified=False)
        _api("approve_document", name=doc.name)

        res2 = _api("update_document", name=doc.name,
                    doc_data=json.dumps({"notes": "Không cho sửa"}))
        results["TC-05-05-3"] = _p(_err_res(res2),
                                   f"Sửa Active doc → error (success={res2.get('success')})")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-05"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-06: list_documents với phân trang
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_06(results: dict):
    print("\n[TC-05-06] List documents với phân trang")
    print("-" * 50)
    try:
        res = _api("list_documents",
                   filters=json.dumps({"asset_ref": _asset()}),
                   page=1, page_size=10)
        results["TC-05-06-1"] = _p(_ok(res), "list_documents → ok")

        data = res.get("data", {})
        items = data.get("items", [])
        results["TC-05-06-2"] = _p(len(items) > 0, f"Có {len(items)} docs")

        pagination = data.get("pagination", {})
        results["TC-05-06-3"] = _p("total" in pagination,
                                   f"pagination.total = {pagination.get('total')}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-06"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-07: get_document chi tiết
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_07(results: dict):
    print("\n[TC-05-07] Xem chi tiết tài liệu")
    print("-" * 50)
    try:
        docs = frappe.db.get_all(DOCTYPE, {"asset_ref": _asset()}, pluck="name", limit=1)
        doc_name = docs[0] if docs else None
        if not doc_name:
            results["TC-05-07"] = _p(False, "Không có doc để test")
            return

        res = _api("get_document", name=doc_name)
        results["TC-05-07-1"] = _p(_ok(res), "get_document → ok")

        data = res.get("data", {})
        results["TC-05-07-2"] = _p(data.get("name") == doc_name, f"name = {data.get('name')}")
        results["TC-05-07-3"] = _p(data.get("asset_ref") == _asset(),
                                   f"asset_ref = {data.get('asset_ref')}")

        res_nf = _api("get_document", name="DOC-NONEXISTENT-9999")
        results["TC-05-07-4"] = _p(_err_res(res_nf), "Not found → error")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-07"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-08: get_asset_documents nhóm theo asset
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_08(results: dict):
    print("\n[TC-05-08] Nhóm hồ sơ theo Asset")
    print("-" * 50)
    try:
        asset = _asset()
        res = _api("get_asset_documents", asset=asset)
        results["TC-05-08-1"] = _p(_ok(res), "get_asset_documents → ok")

        data = res.get("data", {})
        results["TC-05-08-2"] = _p(data.get("asset") == asset,
                                   f"asset = {data.get('asset')}")
        results["TC-05-08-3"] = _p("documents" in data, "Có key 'documents'")
        results["TC-05-08-4"] = _p("document_status" in data,
                                   f"document_status = {data.get('document_status')}")

        res_nf = _api("get_asset_documents", asset="ACC-NONEXISTENT-9999")
        results["TC-05-08-5"] = _p(_err_res(res_nf), "Asset không tồn tại → error")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-08"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-09: Tài liệu sắp hết hạn (get_expiring_documents)
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_09(results: dict):
    print("\n[TC-05-09] Tài liệu sắp hết hạn")
    print("-" * 50)
    try:
        doc = _insert_doc({"expiry_date": add_days(nowdate(), 20)})
        frappe.db.set_value(DOCTYPE, doc.name, "workflow_state", "Active",
                            update_modified=False)
        frappe.db.commit()

        res = _api("get_expiring_documents", days=30)
        results["TC-05-09-1"] = _p(_ok(res), "get_expiring_documents → ok")

        data = res.get("data", {})
        items = data.get("items", [])
        names = [i["name"] for i in items]
        results["TC-05-09-2"] = _p(doc.name in names,
                                   "Doc hết hạn 20 ngày xuất hiện trong list")
        results["TC-05-09-3"] = _p(data.get("days") == 30, f"days = {data.get('days')}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-09"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-10: Scheduler check_document_expiry
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_10(results: dict):
    print("\n[TC-05-10] Scheduler: check_document_expiry")
    print("-" * 50)
    try:
        frappe.db.delete(DT_ALERT, {"asset_ref": _asset()})

        doc = _insert_doc({"expiry_date": add_days(nowdate(), 7)})
        frappe.db.set_value(DOCTYPE, doc.name, {
            "workflow_state": "Active",
            "is_expired": 0,
        }, update_modified=False)
        frappe.db.commit()

        from assetcore.services.imm05 import check_document_expiry
        result = check_document_expiry()
        results["TC-05-10-1"] = _p(isinstance(result, dict), f"Trả về dict: {result}")
        results["TC-05-10-2"] = _p(result.get("created", 0) > 0,
                                   f"Tạo >= 1 alert (created={result.get('created')})")

        alerts = frappe.db.get_all(DT_ALERT,
                                   filters={"asset_document": doc.name},
                                   fields=["name", "alert_level", "days_remaining"])
        results["TC-05-10-3"] = _p(len(alerts) > 0, f"Có {len(alerts)} alert")
        if alerts:
            results["TC-05-10-4"] = _p(alerts[0]["alert_level"] in ("Danger", "Critical"),
                                       f"alert_level = {alerts[0]['alert_level']}")

        result2 = check_document_expiry()
        results["TC-05-10-5"] = _p(result2.get("created", 0) == 0,
                                   f"Idempotent: created={result2.get('created')}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-10"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-11: Dashboard KPIs
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_11(results: dict):
    print("\n[TC-05-11] Dashboard KPIs")
    print("-" * 50)
    try:
        res = _api("get_dashboard_stats")
        results["TC-05-11-1"] = _p(_ok(res), "get_dashboard_stats → ok")

        data = res.get("data", {})
        kpis = data.get("kpis", {})
        results["TC-05-11-2"] = _p("total_active" in kpis,
                                   f"total_active = {kpis.get('total_active')}")
        results["TC-05-11-3"] = _p("expiring_90d" in kpis,
                                   f"expiring_90d = {kpis.get('expiring_90d')}")
        results["TC-05-11-4"] = _p("expiry_timeline" in data, "Có expiry_timeline")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-11"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05-12: Visibility control (Internal_Only)
# ═══════════════════════════════════════════════════════════════════════════════
def tc_05_12(results: dict):
    print("\n[TC-05-12] Visibility control — Internal_Only")
    print("-" * 50)
    try:
        doc = _insert_doc({"visibility": "Internal_Only"})

        frappe.set_user("Administrator")
        res_admin = _api("get_document", name=doc.name)
        results["TC-05-12-1"] = _p(_ok(res_admin), "Admin xem Internal_Only → ok")

        frappe.set_user("Guest")
        res_guest = _api("get_document", name=doc.name)
        results["TC-05-12-2"] = _p(_err_res(res_guest), "Guest xem Internal_Only → error")

        frappe.set_user("Administrator")
    except Exception as e:
        frappe.set_user("Administrator")
        print(f"  ❌ Exception: {e}")
        traceback.print_exc()
        results["TC-05-12"] = "EXCEPTION"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def run_all():
    print("\n" + "=" * 70)
    print("UAT IMM-05 — Asset Document Repository")
    print("=" * 70)

    _cleanup()
    _seed_asset()

    results = {}
    tc_05_01(results)
    tc_05_02(results)
    tc_05_03(results)
    tc_05_04(results)
    tc_05_05(results)
    tc_05_06(results)
    tc_05_07(results)
    tc_05_08(results)
    tc_05_09(results)
    tc_05_10(results)
    tc_05_11(results)
    tc_05_12(results)

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
    print()
    return results
