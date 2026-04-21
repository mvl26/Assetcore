"""Seed Wave 1 — 5 asset datasets đại diện cho tất cả kịch bản kiểm thử.

Tạo đầy đủ: Master data → Commissioning → AC Asset → PM → Repair → Calibration → CAPA

Kịch bản:
  ASSET-01  Hamilton-C6 Ventilator      — Happy Path (full lifecycle pass)
  ASSET-02  Shimadzu MobileArt X-ray    — Exception  (commissioning blocked tại GW-2)
  ASSET-03  Philips IntelliVue Monitor  — PM Fail    (PM major fail → CM Work Order)
  ASSET-04  Omron HBP-9030 BP Monitor   — Cal Fail   (calibration fail → CAPA)
  ASSET-05  B.Braun Perfusor Pump       — Emergency  (SLA breach → Critical CAPA)

Chạy:
    bench --site assetcore execute assetcore.tests.seed_wave1_full.run

Xóa sạch và chạy lại:
    bench --site assetcore execute assetcore.tests.seed_wave1_full.cleanup
    bench --site assetcore execute assetcore.tests.seed_wave1_full.run
"""
from __future__ import annotations
import frappe
from frappe.utils import add_days, nowdate, now_datetime, add_to_date

# ─── DocType constants ────────────────────────────────────────────────────────
_DT_DEPT        = "AC Department"
_DT_LOC         = "AC Location"
_DT_SUPPLIER    = "AC Supplier"
_DT_CATEGORY    = "AC Asset Category"
_DT_MODEL       = "IMM Device Model"
_DT_COMM        = "Asset Commissioning"
_DT_ASSET       = "AC Asset"
_DT_ASSET_DOC   = "Asset Document"
_DT_PM_TPL      = "PM Checklist Template"
_DT_PM_SCHED    = "PM Schedule"
_DT_PM_WO       = "PM Work Order"
_DT_PM_LOG      = "PM Task Log"
_DT_REPAIR      = "Asset Repair"
_DT_CAL_SCHED   = "IMM Calibration Schedule"
_DT_CAL         = "IMM Asset Calibration"
_DT_CAPA        = "IMM CAPA Record"
_DT_INCIDENT    = "Incident Report"

# ─── Seed tag (dùng để nhận diện khi cleanup) ────────────────────────────────
_TAG = "WAVE1-SEED"

_TODAY = nowdate()


# =============================================================================
# HELPERS
# =============================================================================

def _upsert(doctype: str, filters: dict, data: dict) -> str:
    """Tạo hoặc trả về tên doc đã tồn tại theo filters."""
    existing = frappe.db.get_value(doctype, filters, "name")
    if existing:
        return existing
    doc = frappe.new_doc(doctype)
    for k, v in data.items():
        setattr(doc, k, v)
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    return doc.name


def _get_admin() -> str:
    """Trả về Administrator user."""
    return "Administrator"


def _log(msg: str) -> None:
    print(f"  [seed] {msg}")


# =============================================================================
# PHẦN 1 — MASTER DATA
# =============================================================================

def _seed_category() -> str:
    return _upsert(_DT_CATEGORY, {"category_name": "Medical Equipment"}, {
        "category_name": "Medical Equipment",
        "default_pm_required": 1,
        "default_pm_interval_days": 180,
    })


def _seed_departments() -> dict[str, str]:
    rows = {
        "ICU":  {"department_name": "Khoa Hồi sức Tích cực (ICU)",       "department_code": "ICU"},
        "RAD":  {"department_name": "Khoa Chẩn đoán Hình ảnh",           "department_code": "RAD"},
        "CCU":  {"department_name": "Khoa Tim mạch (CCU)",                "department_code": "CCU"},
        "OPD":  {"department_name": "Phòng khám Ngoại trú (OPD)",        "department_code": "OPD"},
        "OR":   {"department_name": "Phòng mổ (OR)",                      "department_code": "OR"},
    }
    out = {}
    for key, data in rows.items():
        out[key] = _upsert(_DT_DEPT, {"department_name": data["department_name"]}, data)
    return out


def _seed_locations(depts: dict[str, str]) -> dict[str, str]:
    rows = {
        "ICU-01":  {"location_name": "ICU — Phòng 101",         "location_code": "LOC-ICU-01"},
        "RAD-01":  {"location_name": "Phòng X-quang số 1",      "location_code": "LOC-RAD-01"},
        "CCU-01":  {"location_name": "CCU — Phòng 201",         "location_code": "LOC-CCU-01"},
        "OPD-01":  {"location_name": "Phòng khám OPD 05",       "location_code": "LOC-OPD-01"},
        "OR-01":   {"location_name": "Phòng mổ số 3",           "location_code": "LOC-OR-01"},
    }
    out = {}
    for key, data in rows.items():
        out[key] = _upsert(_DT_LOC, {"location_name": data["location_name"]}, data)
    return out


def _seed_suppliers() -> dict[str, str]:
    rows = {
        "MED":  {
            "supplier_name": "MedEquip Vietnam JSC",
            "vendor_type": "Manufacturer",
            "country": "Vietnam",
            "is_active": 1,
        },
        "SVC":  {
            "supplier_name": "BioService Medical Co.",
            "vendor_type": "Service",
            "country": "Vietnam",
            "is_active": 1,
        },
        "CAL":  {
            "supplier_name": "VietCal Metrology Lab",
            "vendor_type": "Calibration Lab",
            "iso_17025_cert": "VILAS-234",
            "iso_17025_expiry": "2027-06-30",
            "country": "Vietnam",
            "is_active": 1,
        },
    }
    out = {}
    for key, data in rows.items():
        out[key] = _upsert(_DT_SUPPLIER, {"supplier_name": data["supplier_name"]}, data)
    return out


def _seed_device_models(category: str) -> dict[str, str]:
    rows = {
        "VENT": {
            "model_name": "Hamilton-C6 Ventilator",
            "manufacturer": "Hamilton Medical",
            "model_number": "Hamilton-C6",
            "medical_device_class": "Class III",
            "risk_classification": "Critical",
            "is_radiation_device": 0,
            "asset_category": category,
            "is_pm_required": 1,   "pm_interval_days": 90,
            "is_calibration_required": 1, "calibration_interval_days": 365,
            "default_calibration_type": "External",
            "gmdn_code": "36263",
        },
        "XRAY": {
            "model_name": "Shimadzu MobileArt Evolution",
            "manufacturer": "Shimadzu",
            "model_number": "MobileArt-EVO",
            "medical_device_class": "Class III",
            "risk_classification": "Critical",
            "is_radiation_device": 1,
            "asset_category": category,
            "is_pm_required": 1,   "pm_interval_days": 180,
            "is_calibration_required": 0,
            "gmdn_code": "40890",
        },
        "MON": {
            "model_name": "Philips IntelliVue MX800",
            "manufacturer": "Philips Healthcare",
            "model_number": "IntelliVue-MX800",
            "medical_device_class": "Class II",
            "risk_classification": "High",
            "is_radiation_device": 0,
            "asset_category": category,
            "is_pm_required": 1,   "pm_interval_days": 180,
            "is_calibration_required": 1, "calibration_interval_days": 365,
            "default_calibration_type": "External",
            "gmdn_code": "37825",
        },
        "BP": {
            "model_name": "Omron HBP-9030 BP Monitor",
            "manufacturer": "Omron Healthcare",
            "model_number": "HBP-9030",
            "medical_device_class": "Class II",
            "risk_classification": "Medium",
            "is_radiation_device": 0,
            "asset_category": category,
            "is_pm_required": 1,   "pm_interval_days": 365,
            "is_calibration_required": 1, "calibration_interval_days": 180,
            "default_calibration_type": "External",
            "gmdn_code": "34576",
        },
        "PUMP": {
            "model_name": "B.Braun Perfusor Space Pump",
            "manufacturer": "B.Braun",
            "model_number": "Perfusor-Space",
            "medical_device_class": "Class III",
            "risk_classification": "Critical",
            "is_radiation_device": 0,
            "asset_category": category,
            "is_pm_required": 1,   "pm_interval_days": 180,
            "is_calibration_required": 1, "calibration_interval_days": 365,
            "default_calibration_type": "External",
            "gmdn_code": "13287",
        },
    }
    out = {}
    for key, data in rows.items():
        out[key] = _upsert(_DT_MODEL,
                           {"model_name": data["model_name"], "manufacturer": data["manufacturer"]},
                           data)
    return out


# =============================================================================
# PHẦN 2 — PM CHECKLIST TEMPLATE (cần cho PM Schedule)
# =============================================================================

_CHECKLIST_ITEMS_COMMON = [
    {"description": "Kiểm tra nguồn điện và nối đất", "measurement_type": "Pass/Fail", "is_critical": 1},
    {"description": "Kiểm tra hiển thị màn hình",     "measurement_type": "Pass/Fail", "is_critical": 0},
    {"description": "Kiểm tra alarm và cảnh báo",     "measurement_type": "Pass/Fail", "is_critical": 1},
    {"description": "Rò dòng điện (Leakage Current)", "measurement_type": "Numeric",
     "unit": "µA", "expected_min": 0, "expected_max": 500, "is_critical": 1},
    {"description": "Kiểm tra vệ sinh và ngoại quan",  "measurement_type": "Pass/Fail", "is_critical": 0},
]


def _seed_pm_template(category: str) -> str:
    tpl_name = "Wave1-PM-Template-General"
    existing = frappe.db.get_value(_DT_PM_TPL, {"template_name": tpl_name}, "name")
    if existing:
        return existing
    doc = frappe.new_doc(_DT_PM_TPL)
    doc.template_name = tpl_name
    doc.asset_category = category
    doc.pm_type = "Semi-Annual"
    doc.version = "1.0"
    doc.effective_date = _TODAY
    for item in _CHECKLIST_ITEMS_COMMON:
        doc.append("checklist_items", item)
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.flags.ignore_validate = True
    doc.insert(ignore_permissions=True)
    _log(f"PM Template: {doc.name}")
    return doc.name


# =============================================================================
# PHẦN 3 — ASSET COMMISSIONING (tạo hồ sơ lắp đặt)
# =============================================================================

_MANDATORY_DOCS = [
    ("CO - Chứng nhận Xuất xứ",    1),
    ("CQ - Chứng nhận Chất lượng", 1),
    ("Manual / HDSD",              1),
    ("Warranty Card",              0),
]

_BASELINE_PASS = [
    {"parameter": "Earth Continuity",     "is_critical": 1, "measurement_type": "Numeric",
     "measured_val": 0.3,  "expected_min": 0, "expected_max": 0.5,   "unit": "Ω",   "test_result": "Pass", "fail_note": ""},
    {"parameter": "Insulation Resistance","is_critical": 1, "measurement_type": "Numeric",
     "measured_val": 15.0, "expected_min": 2, "expected_max": None,  "unit": "MΩ",  "test_result": "Pass", "fail_note": ""},
    {"parameter": "Leakage Current",      "is_critical": 1, "measurement_type": "Numeric",
     "measured_val": 250,  "expected_min": 0, "expected_max": 500,   "unit": "µA",  "test_result": "Pass", "fail_note": ""},
    {"parameter": "Visual Inspection",    "is_critical": 0, "measurement_type": "Pass/Fail",
     "measured_val": None, "expected_min": None, "expected_max": None,"unit": "",    "test_result": "Pass", "fail_note": ""},
]


def _create_commissioning(
    serial_no: str,
    model: str,
    vendor: str,
    dept: str,
    location: str,
    po_ref: str,
    description: str,
    reception_offset: int = -14,
    install_offset: int = -10,
    workflow_state: str = "Clinical Release",
    include_baseline: bool = True,
    docs_status: str = "Received",
) -> str:
    """Tạo Asset Commissioning với trạng thái workflow cụ thể."""
    existing = frappe.db.get_value(_DT_COMM, {"vendor_serial_no": serial_no}, "name")
    if existing:
        _log(f"Commissioning exists: {existing} (sn={serial_no})")
        return existing

    doc = frappe.new_doc(_DT_COMM)
    doc.po_reference = po_ref
    doc.master_item = model
    doc.vendor = vendor
    doc.clinical_dept = dept
    doc.installation_location = location
    doc.asset_description = description
    doc.vendor_serial_no = serial_no
    doc.reception_date = add_days(_TODAY, reception_offset)
    doc.expected_installation_date = add_days(_TODAY, install_offset + 2)
    doc.installation_date = add_days(_TODAY, install_offset)
    doc.workflow_state = workflow_state
    doc.internal_tag_qr = f"QR-{serial_no[:10]}"

    # Commissioning documents
    for doc_type, mandatory in _MANDATORY_DOCS:
        status = docs_status if mandatory else "Pending"
        doc.append("commissioning_documents", {
            "doc_type": doc_type,
            "is_mandatory": mandatory,
            "status": status,
            "received_date": add_days(_TODAY, reception_offset) if status == "Received" else None,
        })

    # Baseline tests
    if include_baseline:
        for row in _BASELINE_PASS:
            doc.append("baseline_tests", row)

    doc.board_approver = _get_admin()  # G06 requires board_approver
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_validate = True   # bypass controller validation for seed data
    doc.flags.ignore_permissions = True

    doc.insert(ignore_permissions=True)

    # Set docstatus directly via DB to avoid triggering on_submit hooks
    if workflow_state == "Clinical Release":
        frappe.db.set_value(_DT_COMM, doc.name, "docstatus", 1)

    _log(f"Commissioning: {doc.name} [{workflow_state}]")
    return doc.name


# =============================================================================
# PHẦN 4 — AC ASSET (tạo trực tiếp, liên kết commissioning)
# =============================================================================

def _create_ac_asset(
    asset_name: str,
    category: str,
    model: str,
    dept: str,
    location: str,
    supplier: str,
    serial_no: str,
    commissioning_ref: str,
    lifecycle_status: str = "Active",
    medical_device_class: str = "Class II",
    risk_classification: str = "Medium",
    is_pm_required: int = 1,
    pm_interval_days: int = 180,
    is_cal_required: int = 1,
    cal_interval_days: int = 365,
    purchase_date_offset: int = -30,
) -> str:
    """Tạo AC Asset mới hoặc trả về tên đã tồn tại."""
    existing = frappe.db.get_value(_DT_ASSET, {"manufacturer_sn": serial_no}, "name")
    if existing:
        _log(f"AC Asset exists: {existing}")
        return existing

    doc = frappe.new_doc(_DT_ASSET)
    doc.asset_name = asset_name
    doc.asset_category = category
    doc.device_model = model
    doc.location = location
    doc.department = dept
    doc.supplier = supplier
    doc.manufacturer_sn = serial_no
    doc.status = "Active"
    doc.lifecycle_status = lifecycle_status
    doc.medical_device_class = medical_device_class
    doc.risk_classification = risk_classification
    doc.commissioning_ref = commissioning_ref
    doc.commissioning_date = add_days(_TODAY, -10)
    doc.purchase_date = add_days(_TODAY, purchase_date_offset)
    doc.gross_purchase_amount = 100_000_000
    doc.in_service_date = add_days(_TODAY, -10)
    doc.is_pm_required = is_pm_required
    doc.pm_interval_days = pm_interval_days
    doc.next_pm_date = add_days(_TODAY, pm_interval_days - 10)
    doc.is_calibration_required = is_cal_required
    doc.calibration_interval_days = cal_interval_days

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    _log(f"AC Asset: {doc.name} — {asset_name}")
    return doc.name


# =============================================================================
# PHẦN 5 — ASSET DOCUMENT (IMM-05)
# =============================================================================

def _create_asset_doc(
    asset_ref: str,
    doc_type_detail: str,
    doc_category: str,
    doc_number: str,
    expiry_date: str | None = None,
    status: str = "Active",
    commissioning_ref: str | None = None,
) -> str:
    existing = frappe.db.get_value(
        _DT_ASSET_DOC,
        {"asset_ref": asset_ref, "doc_number": doc_number},
        "name",
    )
    if existing:
        return existing

    doc = frappe.new_doc(_DT_ASSET_DOC)
    doc.asset_ref = asset_ref
    doc.doc_type_detail = doc_type_detail
    doc.doc_category = doc_category
    doc.doc_number = doc_number
    doc.version = "1.0"
    doc.issued_date = add_days(_TODAY, -30)
    doc.expiry_date = expiry_date
    doc.workflow_state = status
    doc.source_commissioning = commissioning_ref
    doc.source_module = "IMM-04"
    doc.visibility = "Public"
    if status == "Active":
        doc.approved_by = _get_admin()
        doc.approval_date = _TODAY

    doc.issuing_authority = "Cục Quản lý Trang thiết bị và Công trình y tế (DMEC)"
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_validate = True   # bypass VR-04 and other validators for seed data
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    return doc.name


# =============================================================================
# PHẦN 6 — PM SCHEDULE + PM WORK ORDER (IMM-08)
# =============================================================================

def _create_pm_schedule(asset_ref: str, pm_type: str, interval_days: int, template: str) -> str:
    existing = frappe.db.get_value(_DT_PM_SCHED, {"asset_ref": asset_ref, "status": "Active"}, "name")
    if existing:
        return existing

    doc = frappe.new_doc(_DT_PM_SCHED)
    doc.asset_ref = asset_ref
    doc.pm_type = pm_type
    doc.pm_interval_days = interval_days
    doc.checklist_template = template
    doc.status = "Active"
    doc.last_pm_date = add_days(_TODAY, -interval_days)
    doc.next_due_date = add_days(_TODAY, 5)
    doc.alert_days_before = 14
    doc.responsible_technician = _get_admin()

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_validate = True
    doc.insert(ignore_permissions=True)
    _log(f"PM Schedule: {doc.name}")
    return doc.name


def _create_pm_wo(
    asset_ref: str,
    pm_schedule: str,
    pm_type: str,
    status: str = "Completed",
    overall_result: str = "Pass",
    due_offset: int = -3,
    checklist_results: list | None = None,
    source_pm_wo: str | None = None,
    wo_type: str = "Preventive",
) -> str:
    doc = frappe.new_doc(_DT_PM_WO)
    doc.asset_ref = asset_ref
    doc.pm_schedule = pm_schedule
    doc.pm_type = pm_type
    doc.wo_type = wo_type
    doc.due_date = add_days(_TODAY, due_offset)
    doc.scheduled_date = add_days(_TODAY, due_offset)
    doc.status = status
    doc.overall_result = overall_result
    doc.technician_notes = "Thực hiện bảo trì định kỳ theo lịch."
    doc.pm_sticker_attached = 1
    doc.duration_minutes = 90
    doc.assigned_to = _get_admin()
    if source_pm_wo:
        doc.source_pm_wo = source_pm_wo

    # Checklist results
    results = checklist_results or [
        {"description": "Kiểm tra nguồn điện và nối đất", "measurement_type": "Pass/Fail",
         "result": "Pass", "notes": ""},
        {"description": "Kiểm tra hiển thị màn hình",     "measurement_type": "Pass/Fail",
         "result": "Pass", "notes": ""},
        {"description": "Kiểm tra alarm và cảnh báo",     "measurement_type": "Pass/Fail",
         "result": "Pass", "notes": ""},
        {"description": "Rò dòng điện (Leakage Current)", "measurement_type": "Numeric",
         "result": "Pass", "measured_value": 250.0, "unit": "µA", "notes": ""},
        {"description": "Kiểm tra vệ sinh và ngoại quan",  "measurement_type": "Pass/Fail",
         "result": "Pass", "notes": ""},
    ]
    for row in results:
        doc.append("checklist_results", row)

    if status == "Completed":
        doc.completion_date = add_days(_TODAY, due_offset + 1)

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    _log(f"PM WO: {doc.name} [{status} / {overall_result}]")
    return doc.name


# =============================================================================
# PHẦN 7 — ASSET REPAIR (IMM-09)
# =============================================================================

def _create_repair(
    asset_ref: str,
    repair_type: str = "Corrective",
    priority: str = "Urgent",
    status: str = "Completed",
    source_pm_wo: str | None = None,
    incident_report: str | None = None,
    risk_class: str = "Class II",
    sla_target_hours: float = 48.0,
    mttr_hours: float = 20.0,
    sla_breached: int = 0,
    root_cause_category: str = "Electrical",
    repair_summary: str = "Đã sửa chữa và kiểm tra lại thiết bị.",
) -> str:
    # Idempotency: check existing repair for this asset + source
    filters: dict = {"asset_ref": asset_ref}
    if source_pm_wo:
        filters["source_pm_wo"] = source_pm_wo
    elif incident_report:
        filters["incident_report"] = incident_report
    existing = frappe.db.get_value(_DT_REPAIR, filters, "name")
    if existing:
        _log(f"Repair WO exists: {existing}")
        return existing

    # Monkey-patch before_insert validations that block seed data
    import assetcore.services.imm09 as _svc09
    _orig_not_under = _svc09.validate_asset_not_under_repair
    _orig_source    = _svc09.validate_repair_source
    _svc09.validate_asset_not_under_repair = lambda *a, **kw: None
    _svc09.validate_repair_source          = lambda *a, **kw: None

    doc = frappe.new_doc(_DT_REPAIR)
    doc.asset_ref = asset_ref
    doc.repair_type = repair_type
    doc.priority = priority
    doc.status = status
    doc.risk_class = risk_class
    doc.source_pm_wo = source_pm_wo
    doc.incident_report = incident_report
    doc.open_datetime = str(add_to_date(now_datetime(), hours=-(mttr_hours + 1)))
    doc.sla_target_hours = sla_target_hours
    doc.mttr_hours = mttr_hours
    doc.sla_breached = sla_breached
    doc.diagnosis_notes = "Kiểm tra và xác định nguyên nhân lỗi."
    doc.root_cause_category = root_cause_category
    doc.repair_summary = repair_summary
    doc.assigned_to = _get_admin()

    if status == "Completed":
        doc.completion_datetime = str(now_datetime())

    # Repair checklist
    doc.append("repair_checklist", {
        "test_description": "Kiểm tra sau sửa chữa — Nguồn điện",
        "test_category": "Electrical",
        "expected_value": "Normal",
        "measured_value": "Normal",
        "result": "Pass",
    })
    doc.append("repair_checklist", {
        "test_description": "Kiểm tra chức năng cơ bản",
        "test_category": "Performance",
        "expected_value": "Pass",
        "measured_value": "Pass",
        "result": "Pass",
    })

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_permissions = True
    try:
        doc.insert(ignore_permissions=True)
    finally:
        # Restore original functions
        _svc09.validate_asset_not_under_repair = _orig_not_under
        _svc09.validate_repair_source          = _orig_source
    _log(f"Repair WO: {doc.name} [{status} / {repair_type} / SLA breach={sla_breached}]")
    return doc.name


# =============================================================================
# PHẦN 8 — CALIBRATION SCHEDULE + WORK ORDER (IMM-11)
# =============================================================================

def _create_cal_schedule(asset: str, model: str, interval_days: int, cal_type: str = "External") -> str:
    existing = frappe.db.get_value(_DT_CAL_SCHED, {"asset": asset, "is_active": 1}, "name")
    if existing:
        return existing

    doc = frappe.new_doc(_DT_CAL_SCHED)
    doc.asset = asset
    doc.device_model = model
    doc.calibration_type = cal_type
    doc.interval_days = interval_days
    doc.last_calibration_date = add_days(_TODAY, -interval_days)
    doc.next_due_date = add_days(_TODAY, 30)
    doc.is_active = 1

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_validate = True
    doc.insert(ignore_permissions=True)
    _log(f"Cal Schedule: {doc.name}")
    return doc.name


def _create_calibration(
    asset: str,
    model: str,
    cal_schedule: str,
    cal_type: str = "External",
    lab_supplier: str | None = None,
    status: str = "Passed",
    overall_result: str = "Passed",
    measurements: list | None = None,
    certificate_number: str | None = None,
) -> str:
    doc = frappe.new_doc(_DT_CAL)
    doc.asset = asset
    doc.device_model = model
    doc.calibration_schedule = cal_schedule
    doc.calibration_type = cal_type
    doc.status = status
    doc.overall_result = overall_result
    doc.scheduled_date = add_days(_TODAY, -10)
    doc.actual_date = add_days(_TODAY, -7)
    doc.technician = _get_admin()
    doc.assigned_by = _get_admin()

    if cal_type == "External" and lab_supplier:
        doc.lab_supplier = lab_supplier
        doc.lab_accreditation_number = "VILAS-234"
        doc.sent_date = add_days(_TODAY, -10)
        doc.certificate_date = add_days(_TODAY, -7)
        doc.certificate_number = certificate_number or f"VILAS-234-{_TODAY}-001"

    meas = measurements or [
        {"parameter_name": "Độ chính xác đầu ra",  "unit": "mmHg",
         "nominal_value": 120.0, "tolerance_positive": 3.0, "tolerance_negative": 3.0,
         "measured_value": 121.0, "out_of_tolerance": 0, "pass_fail": "Pass"},
        {"parameter_name": "Ổn định tín hiệu",      "unit": "%",
         "nominal_value": 100.0, "tolerance_positive": 2.0, "tolerance_negative": 2.0,
         "measured_value": 100.5, "out_of_tolerance": 0, "pass_fail": "Pass"},
    ]
    for row in meas:
        doc.append("measurements", row)

    if status == "Passed":
        doc.next_calibration_date = add_days(_TODAY, 365)

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    _log(f"Calibration: {doc.name} [{status} / {cal_type}]")
    return doc.name


# =============================================================================
# PHẦN 9 — CAPA RECORD (IMM-12)
# =============================================================================

def _create_capa(
    asset: str,
    severity: str,
    source_type: str,
    source_ref: str,
    description: str,
    status: str = "Open",
    linked_incident: str | None = None,
    lookback_required: int = 0,
    root_cause: str = "",
    corrective_action: str = "",
    due_offset: int = 30,
) -> str:
    doc = frappe.new_doc(_DT_CAPA)
    doc.naming_series = "CAPA-.YYYY.-.#####"
    doc.asset = asset
    doc.severity = severity
    doc.status = status
    doc.source_type = source_type
    doc.source_ref = source_ref
    doc.description = description
    doc.responsible = _get_admin()
    doc.opened_date = _TODAY
    doc.due_date = add_days(_TODAY, due_offset)
    doc.lookback_required = lookback_required
    doc.linked_incident = linked_incident
    doc.root_cause = root_cause
    doc.corrective_action = corrective_action

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    _log(f"CAPA: {doc.name} [{severity} / {source_type}]")
    return doc.name


# =============================================================================
# PHẦN 10 — INCIDENT REPORT
# =============================================================================

def _create_incident(asset: str, severity: str, description: str, incident_type: str = "Failure") -> str:
    doc = frappe.new_doc(_DT_INCIDENT)
    doc.asset = asset
    doc.reported_by = _get_admin()
    doc.reported_at = str(now_datetime())
    doc.incident_type = incident_type
    doc.severity = severity
    doc.status = "Open"
    doc.description = description
    doc.patient_affected = 1 if severity == "Critical" else 0

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    doc.flags.ignore_links = True
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    _log(f"Incident: {doc.name} [{severity}]")
    return doc.name


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def run() -> dict:
    """Tạo toàn bộ 5 asset datasets Wave 1. Idempotent — re-run được."""
    frappe.set_user("Administrator")
    frappe.flags.mute_emails = True

    print("\n" + "=" * 70)
    print("SEED WAVE 1 — 5 Asset Datasets (IMM-04..12)")
    print("=" * 70)

    # ─── Master data ──────────────────────────────────────────────────────────
    print("\n[1/3] Master data...")
    category  = _seed_category()
    depts     = _seed_departments()
    locations = _seed_locations(depts)
    suppliers = _seed_suppliers()
    models    = _seed_device_models(category)
    pm_tpl    = _seed_pm_template(category)
    frappe.db.commit()
    _log(f"Category={category}, Depts={len(depts)}, Locations={len(locations)}")
    _log(f"Suppliers={len(suppliers)}, Models={len(models)}, PM Template={pm_tpl}")

    # ─── 5 Asset datasets ─────────────────────────────────────────────────────
    print("\n[2/3] Tạo 5 Asset datasets...")
    results = {}

    # ─── ASSET-01: Hamilton-C6 Ventilator — Happy Path ────────────────────────
    print("\n  ► ASSET-01: Hamilton-C6 Ventilator — Happy Path")
    comm_01 = _create_commissioning(
        serial_no="HAM-C6-SN-001234",
        model=models["VENT"],
        vendor=suppliers["MED"],
        dept=depts["ICU"],
        location=locations["ICU-01"],
        po_ref="PO-2026-0042",
        description="Máy giúp thở Hamilton-C6 — Khoa ICU",
        workflow_state="Clinical Release",
    )
    asset_01 = _create_ac_asset(
        asset_name="Máy giúp thở Hamilton-C6 — ICU-VENT-01",
        category=category,
        model=models["VENT"],
        dept=depts["ICU"],
        location=locations["ICU-01"],
        supplier=suppliers["MED"],
        serial_no="HAM-C6-SN-001234",
        commissioning_ref=comm_01,
        lifecycle_status="Active",
        medical_device_class="Class III",
        risk_classification="Critical",
        pm_interval_days=90,
        cal_interval_days=365,
    )
    # IMM-05: ĐKLH active
    _create_asset_doc(asset_01, "Chứng nhận đăng ký lưu hành", "Legal",
                      "ĐKLH-HAM-C6-2024", expiry_date="2029-06-30",
                      status="Active", commissioning_ref=comm_01)
    _create_asset_doc(asset_01, "Certificate of Origin", "Technical",
                      "CO-2026-042", commissioning_ref=comm_01)
    _create_asset_doc(asset_01, "Phiếu bảo hành 24 tháng", "Technical",
                      "WR-2026-042", expiry_date=add_days(_TODAY, 700),
                      commissioning_ref=comm_01)
    # IMM-08: PM pass
    pm_sched_01 = _create_pm_schedule(asset_01, "Quarterly", 90, pm_tpl)
    pm_wo_01 = _create_pm_wo(asset_01, pm_sched_01, "Quarterly",
                              status="Completed", overall_result="Pass", due_offset=-3)
    # IMM-11: Calibration pass
    cal_sched_01 = _create_cal_schedule(asset_01, models["VENT"], 365, "External")
    cal_01 = _create_calibration(
        asset_01, models["VENT"], cal_sched_01, "External",
        lab_supplier=suppliers["CAL"],
        status="Passed", overall_result="Passed",
        certificate_number="VILAS-234-2026-VENT-001",
        measurements=[
            {"parameter_name": "Thể tích khí lưu thông (Vt)",
             "unit": "mL", "nominal_value": 500.0,
             "tolerance_positive": 15.0, "tolerance_negative": 15.0,
             "measured_value": 502.0, "out_of_tolerance": 0, "pass_fail": "Pass"},
            {"parameter_name": "Áp lực đỉnh (Peak Pressure)",
             "unit": "cmH2O", "nominal_value": 30.0,
             "tolerance_positive": 5.0, "tolerance_negative": 5.0,
             "measured_value": 30.5, "out_of_tolerance": 0, "pass_fail": "Pass"},
            {"parameter_name": "FiO2 Accuracy",
             "unit": "%", "nominal_value": 40.0,
             "tolerance_positive": 3.0, "tolerance_negative": 3.0,
             "measured_value": 40.2, "out_of_tolerance": 0, "pass_fail": "Pass"},
        ],
    )
    results["asset_01"] = {
        "scenario": "Happy Path", "commissioning": comm_01,
        "asset": asset_01, "pm_wo": pm_wo_01, "calibration": cal_01,
    }
    frappe.db.commit()

    # ─── ASSET-02: Shimadzu X-ray — Exception (GW-2 blocked) ─────────────────
    print("\n  ► ASSET-02: Shimadzu X-ray — Exception (GW-2 block)")
    comm_02 = _create_commissioning(
        serial_no="SHI-MART-SN-5678",
        model=models["XRAY"],
        vendor=suppliers["MED"],
        dept=depts["RAD"],
        location=locations["RAD-01"],
        po_ref="PO-2026-0043",
        description="Máy X-quang di động Shimadzu — Khoa CDHA",
        workflow_state="Initial Inspection",  # Bị kẹt tại đây
        docs_status="Received",
    )
    # IMM-05: ĐKLH chưa được approve (Draft) → GW-2 fail
    _create_asset_doc(None, "Chứng nhận đăng ký lưu hành", "Legal",
                      "ĐKLH-SHIM-2024-DRAFT", expiry_date="2029-06-30",
                      status="Draft", commissioning_ref=comm_02)
    results["asset_02"] = {
        "scenario": "Exception — GW-2 Block",
        "commissioning": comm_02,
        "asset": None,
        "note": "AC Asset KHÔNG được tạo. ĐKLH ở trạng thái Draft → block submit.",
    }
    frappe.db.commit()

    # ─── ASSET-03: Philips Monitor — PM Fail → CM Work Order ─────────────────
    print("\n  ► ASSET-03: Philips Monitor — PM Fail → CM WO")
    comm_03 = _create_commissioning(
        serial_no="PHI-MX800-SN-9012",
        model=models["MON"],
        vendor=suppliers["SVC"],
        dept=depts["CCU"],
        location=locations["CCU-01"],
        po_ref="PO-2026-0044",
        description="Monitor theo dõi Philips MX800 — Khoa Tim mạch",
        workflow_state="Clinical Release",
    )
    asset_03 = _create_ac_asset(
        asset_name="Monitor Philips IntelliVue MX800 — CCU-MON-01",
        category=category,
        model=models["MON"],
        dept=depts["CCU"],
        location=locations["CCU-01"],
        supplier=suppliers["SVC"],
        serial_no="PHI-MX800-SN-9012",
        commissioning_ref=comm_03,
        lifecycle_status="Out of Service",  # Kết quả sau PM major fail
        medical_device_class="Class II",
        risk_classification="High",
        pm_interval_days=180,
    )
    pm_sched_03 = _create_pm_schedule(asset_03, "Semi-Annual", 180, pm_tpl)
    # PM WO: Halted–Major Failure
    pm_wo_03 = _create_pm_wo(
        asset_03, pm_sched_03, "Semi-Annual",
        status="Halted–Major Failure",
        overall_result="Fail",
        due_offset=-1,
        checklist_results=[
            {"description": "Kiểm tra nguồn điện và nối đất", "measurement_type": "Pass/Fail",
             "result": "Pass", "notes": ""},
            {"description": "Kiểm tra hiển thị màn hình",     "measurement_type": "Pass/Fail",
             "result": "Pass", "notes": ""},
            {"description": "Kiểm tra đầu đo SpO2",           "measurement_type": "Pass/Fail",
             "result": "Fail–Major",
             "notes": "Đầu đo SpO2 không nhận tín hiệu, lỗi E-047. Cần thay thế cảm biến."},
            {"description": "Kiểm tra ECG lead 12 kênh",      "measurement_type": "Pass/Fail",
             "result": "Pass", "notes": ""},
            {"description": "Kiểm tra vệ sinh và ngoại quan",  "measurement_type": "Pass/Fail",
             "result": "Pass", "notes": ""},
        ],
    )
    # IMM-09: CM WO được tạo tự động từ PM fail
    cm_wo_03 = _create_repair(
        asset_ref=asset_03,
        repair_type="Corrective",
        priority="Urgent",
        status="Open",  # Vừa được tạo, chưa xử lý
        source_pm_wo=pm_wo_03,
        risk_class="Class II",
        sla_target_hours=48.0,
        mttr_hours=0.0,
        sla_breached=0,
        root_cause_category="Electrical",
        repair_summary="[Auto-created] Sửa chữa lỗi SpO2 sensor từ PM-WO.",
    )
    results["asset_03"] = {
        "scenario": "PM Fail → CM WO",
        "commissioning": comm_03,
        "asset": asset_03,
        "pm_wo": pm_wo_03,
        "cm_wo": cm_wo_03,
    }
    frappe.db.commit()

    # ─── ASSET-04: Omron BP Monitor — Calibration Fail → CAPA ────────────────
    print("\n  ► ASSET-04: Omron BP — Calibration Fail → CAPA")
    comm_04 = _create_commissioning(
        serial_no="OMR-HBP-SN-3456",
        model=models["BP"],
        vendor=suppliers["MED"],
        dept=depts["OPD"],
        location=locations["OPD-01"],
        po_ref="PO-2026-0045",
        description="Máy đo huyết áp điện tử Omron HBP-9030 — Phòng khám OPD",
        workflow_state="Clinical Release",
    )
    asset_04 = _create_ac_asset(
        asset_name="Máy đo HA Omron HBP-9030 — OPD-BP-01",
        category=category,
        model=models["BP"],
        dept=depts["OPD"],
        location=locations["OPD-01"],
        supplier=suppliers["MED"],
        serial_no="OMR-HBP-SN-3456",
        commissioning_ref=comm_04,
        lifecycle_status="Calibrating",  # Sau khi calibration fail (closest valid status)
        medical_device_class="Class II",
        risk_classification="Medium",
        pm_interval_days=365,
        cal_interval_days=180,
    )
    cal_sched_04 = _create_cal_schedule(asset_04, models["BP"], 180, "External")
    # IMM-11: Calibration Failed
    cal_04 = _create_calibration(
        asset_04, models["BP"], cal_sched_04, "External",
        lab_supplier=suppliers["CAL"],
        status="Failed",
        overall_result="Failed",
        certificate_number="VILAS-234-2026-BP-001",
        measurements=[
            {"parameter_name": "Độ chính xác Systolic BP",
             "unit": "mmHg", "nominal_value": 120.0,
             "tolerance_positive": 3.0, "tolerance_negative": 3.0,
             "measured_value": 127.5,   # 7.5 mmHg > tolerance 3 mmHg → OUT
             "out_of_tolerance": 1, "pass_fail": "Fail"},
            {"parameter_name": "Độ chính xác Diastolic BP",
             "unit": "mmHg", "nominal_value": 80.0,
             "tolerance_positive": 3.0, "tolerance_negative": 3.0,
             "measured_value": 85.2,    # 5.2 mmHg > tolerance 3 mmHg → OUT
             "out_of_tolerance": 1, "pass_fail": "Fail"},
            {"parameter_name": "Độ chính xác Heart Rate",
             "unit": "bpm", "nominal_value": 75.0,
             "tolerance_positive": 5.0, "tolerance_negative": 5.0,
             "measured_value": 76.0,
             "out_of_tolerance": 0, "pass_fail": "Pass"},
        ],
    )
    # IMM-12: CAPA từ calibration fail
    capa_04 = _create_capa(
        asset=asset_04,
        severity="Major",
        source_type="IMM Asset Calibration",
        source_ref=cal_04,
        description=(
            "Máy đo huyết áp Omron HBP-9030 (SN: OMR-HBP-SN-3456) "
            "không đạt hiệu chuẩn: Systolic sai lệch +7.5 mmHg, "
            "Diastolic sai lệch +5.2 mmHg — vượt giới hạn ±3 mmHg."
        ),
        status="Open",
        lookback_required=1,
        root_cause="Hao mòn cảm biến áp lực sau 2 năm vận hành.",
        corrective_action="Gửi thay thế cảm biến áp lực tại nhà sản xuất và tái hiệu chuẩn.",
        due_offset=21,
    )
    # Update calibration capa_record reference
    frappe.db.set_value(_DT_CAL, cal_04, "capa_record", capa_04)
    results["asset_04"] = {
        "scenario": "Calibration Fail → CAPA",
        "commissioning": comm_04,
        "asset": asset_04,
        "calibration": cal_04,
        "capa": capa_04,
    }
    frappe.db.commit()

    # ─── ASSET-05: B.Braun Syringe Pump — Emergency SLA Breach → CAPA ────────
    print("\n  ► ASSET-05: B.Braun Pump — Emergency / SLA Breach → CAPA")
    comm_05 = _create_commissioning(
        serial_no="BB-PERF-SN-7890",
        model=models["PUMP"],
        vendor=suppliers["MED"],
        dept=depts["OR"],
        location=locations["OR-01"],
        po_ref="PO-2026-0046",
        description="Bơm tiêm điện B.Braun Perfusor Space — Phòng mổ OR",
        workflow_state="Clinical Release",
    )
    asset_05 = _create_ac_asset(
        asset_name="Bơm tiêm B.Braun Perfusor Space — OR-PUMP-01",
        category=category,
        model=models["PUMP"],
        dept=depts["OR"],
        location=locations["OR-01"],
        supplier=suppliers["MED"],
        serial_no="BB-PERF-SN-7890",
        commissioning_ref=comm_05,
        lifecycle_status="Active",
        medical_device_class="Class III",
        risk_classification="Critical",
        pm_interval_days=180,
        cal_interval_days=365,
    )
    # Incident Report P1
    incident_05 = _create_incident(
        asset=asset_05,
        severity="Critical",
        description=(
            "Bơm tiêm điện B.Braun Perfusor Space (SN: BB-PERF-SN-7890) "
            "ngừng hoạt động đột ngột giữa ca mổ lúc 08:30. Alarm E-999 xuất hiện. "
            "Bệnh nhân được chuyển sang bơm dự phòng ngay lập tức."
        ),
        incident_type="Failure",
    )
    # IMM-09: Emergency Repair — SLA Breach (4h SLA, 5.75h actual)
    repair_05 = _create_repair(
        asset_ref=asset_05,
        repair_type="Emergency",
        priority="Emergency",
        status="Completed",
        incident_report=incident_05,
        risk_class="Class III",
        sla_target_hours=4.0,        # Class III + Emergency = 4h SLA
        mttr_hours=5.75,             # 5.75h > 4h → BREACH
        sla_breached=1,
        root_cause_category="Software",
        repair_summary=(
            "Lỗi firmware E-999: tràn bộ nhớ buffer sau 72h liên tục. "
            "Đã reset firmware, cập nhật lên v3.2.1. Thiết bị hoạt động bình thường."
        ),
    )
    # IMM-12: CAPA Critical từ SLA breach
    capa_05 = _create_capa(
        asset=asset_05,
        severity="Critical",
        source_type="Asset Repair",
        source_ref=repair_05,
        description=(
            "SLA breach nghiêm trọng: Bơm tiêm B.Braun Perfusor Space (SN: BB-PERF-SN-7890) "
            "hỏng khẩn cấp trong ca mổ. MTTR thực tế = 5.75h vượt SLA = 4h. "
            "Sự cố P1 — có ảnh hưởng trực tiếp đến bệnh nhân đang phẫu thuật."
        ),
        status="In Progress",
        linked_incident=incident_05,
        lookback_required=1,
        root_cause="Firmware v3.1.x có bug tràn bộ nhớ sau 72h hoạt động liên tục.",
        corrective_action=(
            "1. Cập nhật firmware tất cả bơm tiêm B.Braun lên v3.2.1.\n"
            "2. Đặt lịch restart firmware định kỳ 48h.\n"
            "3. Kiểm tra lookback toàn bộ Perfusor Space trong bệnh viện."
        ),
        due_offset=14,
    )
    results["asset_05"] = {
        "scenario": "Emergency SLA Breach → Critical CAPA",
        "commissioning": comm_05,
        "asset": asset_05,
        "incident": incident_05,
        "repair": repair_05,
        "capa": capa_05,
    }
    frappe.db.commit()

    # ─── Summary ──────────────────────────────────────────────────────────────
    print("\n[3/3] Hoàn thành!\n")
    print("=" * 70)
    print("SEED WAVE 1 — KẾT QUẢ")
    print("=" * 70)

    rows = [
        ("ASSET-01", "Hamilton-C6 Ventilator",  "Happy Path",          results["asset_01"]),
        ("ASSET-02", "Shimadzu MobileArt X-ray", "Exception (GW-2)",   results["asset_02"]),
        ("ASSET-03", "Philips MX800 Monitor",    "PM Fail → CM WO",    results["asset_03"]),
        ("ASSET-04", "Omron HBP-9030 BP",        "Cal Fail → CAPA",    results["asset_04"]),
        ("ASSET-05", "B.Braun Perfusor Pump",    "Emergency SLA Breach",results["asset_05"]),
    ]

    for asset_id, device, scenario, data in rows:
        print(f"\n  {asset_id} — {device}")
        print(f"    Kịch bản : {scenario}")
        print(f"    Commissioning : {data.get('commissioning', '—')}")
        print(f"    AC Asset      : {data.get('asset') or '⚠ Không được tạo (bị block GW-2)'}")
        for key in ("pm_wo", "cm_wo", "calibration", "repair", "incident", "capa"):
            if data.get(key):
                print(f"    {key:13s} : {data[key]}")
        if data.get("note"):
            print(f"    Ghi chú       : {data['note']}")

    print("\n" + "=" * 70)
    print("Xem kết quả trên trình duyệt:")
    print("  /app/asset-commissioning         — Danh sách Commissioning (5 bản ghi)")
    print("  /app/ac-asset                    — Danh sách AC Asset (4 bản ghi)")
    print("  /app/asset-document              — Danh sách Tài liệu thiết bị")
    print("  /app/pm-work-order               — PM Work Orders")
    print("  /app/asset-repair                — Repair Work Orders")
    print("  /app/imm-asset-calibration       — Calibration Records")
    print("  /app/imm-capa-record             — CAPA Records")
    print("  /app/incident-report             — Incident Reports")
    print("=" * 70)

    return results


# =============================================================================
# CLEANUP
# =============================================================================

def cleanup() -> None:
    """Xóa toàn bộ dữ liệu được seed bởi run(). Dùng để chạy lại sạch."""
    frappe.set_user("Administrator")

    serials = [
        "HAM-C6-SN-001234",
        "SHI-MART-SN-5678",
        "PHI-MX800-SN-9012",
        "OMR-HBP-SN-3456",
        "BB-PERF-SN-7890",
    ]

    print("\n[cleanup] Xóa dữ liệu seed Wave 1...")

    # Lấy danh sách asset
    asset_names = []
    for sn in serials:
        name = frappe.db.get_value(_DT_ASSET, {"manufacturer_sn": sn}, "name")
        if name:
            asset_names.append(name)

    # Xóa theo thứ tự reverse dependency
    def _delete_all(doctype, filters):
        docs = frappe.db.get_all(doctype, filters=filters, pluck="name")
        for d in docs:
            try:
                doc = frappe.get_doc(doctype, d)
                if doc.docstatus == 1:
                    doc.flags.ignore_permissions = True
                    doc.cancel()
                frappe.delete_doc(doctype, d, force=True, ignore_permissions=True)
                print(f"  Deleted {doctype}: {d}")
            except Exception as e:
                print(f"  WARN {doctype} {d}: {e}")

    if asset_names:
        _delete_all(_DT_CAPA,     {"asset": ("in", asset_names)})
        _delete_all(_DT_CAL,      {"asset": ("in", asset_names)})
        _delete_all(_DT_CAL_SCHED,{"asset": ("in", asset_names)})
        _delete_all(_DT_REPAIR,   {"asset_ref": ("in", asset_names)})
        _delete_all(_DT_PM_WO,    {"asset_ref": ("in", asset_names)})
        _delete_all(_DT_PM_SCHED, {"asset_ref": ("in", asset_names)})
        _delete_all(_DT_ASSET_DOC,{"asset_ref": ("in", asset_names)})
        _delete_all(_DT_INCIDENT, {"asset": ("in", asset_names)})
        _delete_all(_DT_ASSET,    {"name": ("in", asset_names)})

    # Commissioning
    for sn in serials:
        name = frappe.db.get_value(_DT_COMM, {"vendor_serial_no": sn}, "name")
        if name:
            try:
                doc = frappe.get_doc(_DT_COMM, name)
                if doc.docstatus == 1:
                    doc.flags.ignore_permissions = True
                    doc.cancel()
                frappe.delete_doc(_DT_COMM, name, force=True, ignore_permissions=True)
                print(f"  Deleted Commissioning: {name}")
            except Exception as e:
                print(f"  WARN Commissioning {name}: {e}")

    # Asset Document không có asset_ref (ASSET-02 doc)
    docs_no_asset = frappe.db.get_all(
        _DT_ASSET_DOC,
        filters={"doc_number": "ĐKLH-SHIM-2024-DRAFT"},
        pluck="name",
    )
    for d in docs_no_asset:
        frappe.delete_doc(_DT_ASSET_DOC, d, force=True, ignore_permissions=True)

    frappe.db.commit()
    print("\n[cleanup] Xong. Chạy lại: bench --site assetcore execute assetcore.tests.seed_wave1_full.run\n")
