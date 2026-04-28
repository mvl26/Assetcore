"""
Seed dữ liệu UAT cho IMM-11 — Calibration
Theo đặc tả SD-01 → SD-04 trong docs/imm-11/IMM-11_UAT_Script.md

Chạy:
    bench --site miyano execute assetcore.scripts.seed.seed_imm11_uat.seed_all

Cleanup (trước khi chạy lại):
    bench --site miyano execute assetcore.scripts.seed.seed_imm11_uat.cleanup_all
"""
import frappe
from frappe.utils import add_days, nowdate

DT_ASSET = "AC Asset"
DT_MODEL = "IMM Device Model"
DT_SUPPLIER = "AC Supplier"
DT_DEPT = "AC Department"
DT_SCHED = "IMM Calibration Schedule"
DT_CAL = "IMM Asset Calibration"

ASSET_PREFIX = "ACC-ASS-UAT-"


# ─────────────────────────────────────────────────────────────────────────────
# SD-03: Device Models
# ─────────────────────────────────────────────────────────────────────────────
# Theo spec: Sysmex XN-1000 | Mindray MEC-1200 | Drager V500 | Fluke ESA620
# Lưu ý: IMM Device Model dùng field `default_calibration_type` với options
#        Internal/External/Both. Service tự map sang In-House/External.

_MODELS = [
    {
        "model_name": "Sysmex XN-1000",
        "manufacturer": "Sysmex",
        "medical_device_class": "Class II",
        "risk_classification": "Medium",
        "is_calibration_required": 1,
        "calibration_interval_days": 365,
        "default_calibration_type": "External",
        "is_pm_required": 1,
    },
    {
        "model_name": "Mindray MEC-1200",
        "manufacturer": "Mindray",
        "medical_device_class": "Class II",
        "risk_classification": "Medium",
        "is_calibration_required": 1,
        "calibration_interval_days": 365,
        "default_calibration_type": "External",
        "is_pm_required": 1,
    },
    {
        "model_name": "Drager V500",
        "manufacturer": "Drager",
        "medical_device_class": "Class III",
        "risk_classification": "High",
        "is_calibration_required": 1,
        "calibration_interval_days": 180,
        "default_calibration_type": "External",
        "is_pm_required": 1,
    },
    {
        "model_name": "Breas VIVO 45",
        "manufacturer": "Breas",
        "medical_device_class": "Class II",
        "risk_classification": "Medium",
        "is_calibration_required": 1,
        "calibration_interval_days": 365,
        "default_calibration_type": "External",
        "is_pm_required": 1,
    },
    {
        "model_name": "Fluke ESA620",
        "manufacturer": "Fluke Biomedical",
        "medical_device_class": "Class I",
        "risk_classification": "Low",
        "is_calibration_required": 1,
        "calibration_interval_days": 365,
        "default_calibration_type": "Internal",  # → service map thành In-House
        "is_pm_required": 0,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SD-04: Calibration Labs (AC Supplier với vendor_type = Calibration Lab)
# ─────────────────────────────────────────────────────────────────────────────

_LABS = [
    {
        "supplier_name": "Trung tâm Đo lường Chất lượng 3",
        "vendor_type": "Calibration Lab",
        "iso_17025_cert": "VLAS-T-028",
        "iso_17025_expiry": "2027-12-31",
        "country": "Vietnam",
        "is_active": 1,
    },
    {
        "supplier_name": "Viện Đo lường Việt Nam",
        "vendor_type": "Calibration Lab",
        "iso_17025_cert": "VLAS-T-001",
        "iso_17025_expiry": "2027-06-30",
        "country": "Vietnam",
        "is_active": 1,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SD-01: Assets (7 thiết bị + các trạng thái đặc biệt)
# ─────────────────────────────────────────────────────────────────────────────
#
# Chú ý: spec yêu cầu asset name theo định dạng ACC-ASS-UAT-001 → 007 (cố định).
# Frappe tạo name tự động theo naming series của AC Asset. Seed sẽ:
#   - tạo doc với set `name` = tên mong muốn trước khi insert
#   - dùng flags.name_set_explicitly để bypass naming series

_TODAY = nowdate()

_ASSETS = [
    {
        "serial": "SN-UAT-001-SYSMEX",
        "asset_name": "Máy phân tích huyết học Sysmex XN-1000",
        "device_model": "Sysmex XN-1000",
        "department_code": "XN-MAU",           # ref SD-01 "XN Máu"
        "department_name": "Khoa XN Máu",
        "next_cal_offset": 12,                 # next_calibration ≈ 2026-05-01 (+12 ngày)
        "interval": 365,
    },
    {
        "serial": "SN-UAT-002-MINDRAY",
        "asset_name": "Monitor BP Mindray MEC-1200",
        "device_model": "Mindray MEC-1200",
        "department_code": "NOI-TIM-MACH",
        "department_name": "Khoa Nội tim mạch",
        "next_cal_offset": -10,                # OVERDUE 10 ngày (~2026-04-10)
        "interval": 365,
    },
    {
        "serial": "SN-UAT-003-DRAGER",
        "asset_name": "Máy thở Drager V500",
        "device_model": "Drager V500",
        "department_code": "ICU-01",
        "department_name": "Khoa Hồi sức cấp cứu",
        "next_cal_offset": 42,
        "interval": 180,
    },
    {
        "serial": "SN-UAT-004-BREAS",
        "asset_name": "Đồng hồ đo áp lực Breas VIVO 45",
        "device_model": "Breas VIVO 45",
        "department_code": "HO-HAP",
        "department_name": "Khoa Hô hấp",
        "next_cal_offset": 25,
        "interval": 365,
    },
    {
        "serial": "SN-UAT-005-SYSMEX-CC",
        "asset_name": "Sysmex XN-1000 (Cấp cứu)",
        "device_model": "Sysmex XN-1000",
        "department_code": "CAP-CUU",
        "department_name": "Khoa Cấp cứu",
        "next_cal_offset": 72,
        "interval": 365,
    },
    {
        "serial": "SN-UAT-006-SYSMEX-ICU",
        "asset_name": "Sysmex XN-1000 (ICU)",
        "device_model": "Sysmex XN-1000",
        "department_code": "ICU-01",
        "department_name": "Khoa Hồi sức cấp cứu",
        "next_cal_offset": 103,
        "interval": 365,
    },
    {
        "serial": "SN-UAT-007-FLUKE",
        "asset_name": "Máy calibration thủ công Fluke ESA620",
        "device_model": "Fluke ESA620",
        "department_code": "WORKSHOP",
        "department_name": "Xưởng KTV HTM",
        "next_cal_offset": 30,
        "interval": 365,
    },
]


# ═════════════════════════════════════════════════════════════════════════════
# SEED FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def _log(msg: str) -> None:
    print(f"  [seed-imm11] {msg}")


def _ensure_department(code: str, dept_name: str) -> str:
    if frappe.db.exists(DT_DEPT, code):
        return code
    doc = frappe.new_doc(DT_DEPT)
    doc.department_code = code
    doc.department_name = dept_name
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    # Rename to deterministic code
    if doc.name != code:
        try:
            frappe.rename_doc(DT_DEPT, doc.name, code, force=True)
        except Exception:
            pass
    return code


def _ensure_model(payload: dict) -> str:
    name = payload["model_name"]
    if frappe.db.exists(DT_MODEL, name):
        frappe.db.set_value(DT_MODEL, name, {
            "is_calibration_required": payload["is_calibration_required"],
            "calibration_interval_days": payload["calibration_interval_days"],
            "default_calibration_type": payload["default_calibration_type"],
        })
        return name
    doc = frappe.new_doc(DT_MODEL)
    for k, v in payload.items():
        setattr(doc, k, v)
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    if doc.name != name:
        try:
            frappe.rename_doc(DT_MODEL, doc.name, name, force=True)
        except Exception:
            pass
    return name


def _ensure_lab(payload: dict) -> str:
    existing = frappe.db.get_value(DT_SUPPLIER, {"supplier_name": payload["supplier_name"]}, "name")
    if existing:
        frappe.db.set_value(DT_SUPPLIER, existing, {
            "vendor_type": payload["vendor_type"],
            "iso_17025_cert": payload["iso_17025_cert"],
            "iso_17025_expiry": payload["iso_17025_expiry"],
        })
        return existing
    doc = frappe.new_doc(DT_SUPPLIER)
    for k, v in payload.items():
        setattr(doc, k, v)
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_asset(idx: int, spec: dict) -> str:
    asset_name = f"{ASSET_PREFIX}{idx:03d}"
    _ensure_department(spec["department_code"], spec["department_name"])

    next_cal = add_days(_TODAY, spec["next_cal_offset"])
    last_cal = add_days(next_cal, -spec["interval"])

    if frappe.db.exists(DT_ASSET, asset_name):
        frappe.db.set_value(DT_ASSET, asset_name, {
            "device_model": spec["device_model"],
            "location": spec["department_code"],
            "lifecycle_status": "Active",
            "is_calibration_required": 1,
            "calibration_interval_days": spec["interval"],
            "last_calibration_date": last_cal,
            "next_calibration_date": next_cal,
        })
        _log(f"Updated {asset_name}")
        return asset_name

    doc = frappe.new_doc(DT_ASSET)
    doc.asset_name = spec["asset_name"]
    doc.serial_no = spec["serial"]
    doc.device_model = spec["device_model"]
    doc.location = spec["department_code"]
    doc.lifecycle_status = "Active"
    doc.is_calibration_required = 1
    doc.calibration_interval_days = spec["interval"]
    doc.last_calibration_date = last_cal
    doc.next_calibration_date = next_cal
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    if doc.name != asset_name:
        try:
            frappe.rename_doc(DT_ASSET, doc.name, asset_name, force=True)
        except Exception:
            _log(f"Không rename được {doc.name} → {asset_name}; giữ tên auto")
            return doc.name
    _log(f"Created {asset_name} — next_cal {next_cal}")
    return asset_name


def _ensure_schedule(asset_name: str, interval: int, next_due: str, cal_type: str) -> str | None:
    existing = frappe.db.get_value(DT_SCHED, {"asset": asset_name, "is_active": 1}, "name")
    if existing:
        frappe.db.set_value(DT_SCHED, existing, {
            "interval_days": interval,
            "next_due_date": next_due,
            "calibration_type": cal_type,
        })
        return existing
    try:
        doc = frappe.new_doc(DT_SCHED)
        doc.asset = asset_name
        doc.device_model = frappe.db.get_value(DT_ASSET, asset_name, "device_model")
        doc.calibration_type = cal_type
        doc.interval_days = interval
        doc.next_due_date = next_due
        doc.last_calibration_date = add_days(next_due, -interval)
        doc.is_active = 1
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception as e:
        _log(f"Schedule cho {asset_name} lỗi: {e}")
        return None


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def seed_all() -> dict:
    """Seed toàn bộ dữ liệu UAT IMM-11. Idempotent (re-run được)."""
    frappe.set_user("Administrator")
    frappe.flags.mute_emails = True

    print("\n" + "=" * 70)
    print("SEED UAT IMM-11 — docs/imm-11/IMM-11_UAT_Script.md (SD-01..04)")
    print("=" * 70)

    summary = {"models": [], "labs": [], "assets": [], "schedules": []}

    # SD-03: Device Models
    _log("SD-03 — Device Models")
    for m in _MODELS:
        summary["models"].append(_ensure_model(m))

    # SD-04: Calibration Labs
    _log("SD-04 — Calibration Labs")
    for lab in _LABS:
        summary["labs"].append(_ensure_lab(lab))

    # SD-01: Assets
    _log("SD-01 — Assets")
    asset_names: list[str] = []
    for idx, spec in enumerate(_ASSETS, start=1):
        name = _ensure_asset(idx, spec)
        asset_names.append(name)
        summary["assets"].append(name)

        # Tạo schedule tương ứng
        next_due = add_days(_TODAY, spec["next_cal_offset"])
        cal_type = "In-House" if spec["device_model"] == "Fluke ESA620" else "External"
        sched = _ensure_schedule(name, spec["interval"], next_due, cal_type)
        if sched:
            summary["schedules"].append(sched)

    frappe.db.commit()

    # Chạy check_calibration_expiry để cập nhật calibration_status
    try:
        from assetcore.services.imm11 import check_calibration_expiry
        check_calibration_expiry()
        frappe.db.commit()
    except Exception as e:
        _log(f"check_calibration_expiry warning: {e}")

    # In kết quả trạng thái cal_status mỗi asset
    print("\n" + "-" * 70)
    print("Asset calibration status (sau scheduler):")
    print("-" * 70)
    rows = frappe.db.get_all(
        DT_ASSET,
        filters={"name": ("in", asset_names)},
        fields=["name", "asset_name", "device_model",
                "next_calibration_date", "calibration_status"],
        order_by="name asc",
    )
    for r in rows:
        print(f"  {r['name']:22s} | {r['device_model']:20s} | "
              f"next={r['next_calibration_date']} | status={r['calibration_status']}")

    print("\n" + "=" * 70)
    print(f"Đã seed: {len(summary['models'])} models · {len(summary['labs'])} labs · "
          f"{len(summary['assets'])} assets · {len(summary['schedules'])} schedules")
    print("=" * 70)
    return summary


def cleanup_all() -> None:
    """Xóa toàn bộ seed IMM-11 UAT (để re-run sạch)."""
    frappe.set_user("Administrator")
    print("\n" + "=" * 70)
    print("CLEANUP SEED IMM-11")
    print("=" * 70)

    # Xóa theo thứ tự child → parent
    asset_names = [f"{ASSET_PREFIX}{i:03d}" for i in range(1, len(_ASSETS) + 1)]

    # CAL records
    for a in asset_names:
        cals = frappe.db.get_all(DT_CAL, {"asset": a}, pluck="name")
        for c in cals:
            try:
                doc = frappe.get_doc(DT_CAL, c)
                if doc.docstatus == 1:
                    doc.flags.ignore_permissions = True
                    doc.cancel()
                frappe.delete_doc(DT_CAL, c, force=True, ignore_permissions=True)
            except Exception as e:
                _log(f"CAL {c}: {e}")

    # Schedules
    for a in asset_names:
        scheds = frappe.db.get_all(DT_SCHED, {"asset": a}, pluck="name")
        for s in scheds:
            try:
                frappe.delete_doc(DT_SCHED, s, force=True, ignore_permissions=True)
            except Exception as e:
                _log(f"SCHED {s}: {e}")

    # Assets
    for a in asset_names:
        if frappe.db.exists(DT_ASSET, a):
            try:
                frappe.delete_doc(DT_ASSET, a, force=True, ignore_permissions=True)
                _log(f"Deleted {a}")
            except Exception as e:
                _log(f"Asset {a}: {e}")

    # Models (chỉ xóa nếu không còn asset nào tham chiếu)
    for m in _MODELS:
        model_name = m["model_name"]
        if not frappe.db.exists(DT_MODEL, model_name):
            continue
        if frappe.db.exists(DT_ASSET, {"device_model": model_name}):
            _log(f"Model {model_name}: còn asset khác tham chiếu — bỏ qua")
            continue
        try:
            frappe.delete_doc(DT_MODEL, model_name, force=True, ignore_permissions=True)
            _log(f"Deleted model {model_name}")
        except Exception as e:
            _log(f"Model {model_name}: {e}")

    # Labs (tương tự)
    for lab in _LABS:
        name = frappe.db.get_value(DT_SUPPLIER, {"supplier_name": lab["supplier_name"]}, "name")
        if name:
            try:
                frappe.delete_doc(DT_SUPPLIER, name, force=True, ignore_permissions=True)
                _log(f"Deleted lab {name}")
            except Exception as e:
                _log(f"Lab {name}: {e}")

    frappe.db.commit()
    print("Cleanup xong.\n")
