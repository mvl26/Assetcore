# Copyright (c) 2026, AssetCore Team
"""IMM-00 REST API — 42 endpoints for AssetCore foundation DocTypes.

Convention:
  GET  → frappe.whitelist(allow_guest=False)
  POST → frappe.whitelist(methods=["POST"])
  Response: _ok(data) | _err(message, code)
"""
import frappe
from frappe import _

from assetcore.utils.response import _ok, _err, ErrorCode
from assetcore.utils.pagination import paginate
from assetcore.services.imm00 import (
    transition_asset_status,
    update_gmdn_status as svc_update_gmdn_status,
    toggle_gmdn_status_via_qr as svc_toggle_gmdn_via_qr,
    validate_asset_for_operations,
    get_sla_policy,
    create_capa,
    close_capa,
    verify_audit_chain,
    transfer_asset,
    create_transfer_request,
    approve_transfer_request,
    reject_transfer_request,
    confirm_receipt,
    cancel_transfer_request,
)

_DT_ASSET = "AC Asset"
_DT_SUPPLIER = "AC Supplier"
_DT_LOCATION = "AC Location"
_DT_DEPARTMENT = "AC Department"
_DT_ASSET_CATEGORY = "AC Asset Category"
_DT_DEVICE_MODEL = "IMM Device Model"
_DT_SLA_POLICY = "IMM SLA Policy"


def _enrich(items: list, field: str, doctype: str, display_field: str, out_field: str = None) -> None:
    """Batch-enrich a list of dicts with a display name for a linked field (avoids N+1)."""
    out = out_field or f"{field}_name"
    ids = {row.get(field) for row in items if row.get(field)}
    if not ids:
        return
    mapping = {r.name: r[display_field] for r in frappe.get_all(
        doctype, filters={"name": ["in", list(ids)]}, fields=["name", display_field],
    )}
    for row in items:
        row[out] = mapping.get(row.get(field)) or row.get(field) or ""
_DT_AUDIT_TRAIL = "IMM Audit Trail"
_DT_CAPA = "IMM CAPA Record"
_DT_LIFECYCLE_EVENT = "Asset Lifecycle Event"
_DT_INCIDENT = "Incident Report"
_DT_TRANSFER = "Asset Transfer"
_DT_SERVICE_CONTRACT = "Service Contract"

_ERR_TRANSFER_NOT_FOUND = "Asset Transfer không tồn tại"
_ERR_CONTRACT_NOT_FOUND = "Service Contract không tồn tại"

_ERR_ASSET_NOT_FOUND = "Asset không tồn tại"
_ERR_SUPPLIER_NOT_FOUND = "Nhà cung cấp không tồn tại"
_ERR_DEVICE_MODEL_NOT_FOUND = "Device Model không tồn tại"
_ERR_AUDIT_NOT_FOUND = "Audit Trail entry không tồn tại"
_ERR_CAPA_NOT_FOUND = "CAPA Record không tồn tại"
_ERR_LIFECYCLE_NOT_FOUND = "Lifecycle Event không tồn tại"
_ERR_INCIDENT_NOT_FOUND = "Incident Report không tồn tại"

_ORDER_EVENT_TS_DESC = "timestamp desc"
_ORDER_MODIFIED_DESC = "modified desc"
_ORDER_DUE_DATE_ASC  = "due_date asc"

# ─────────────────────────────────────────────────────────────────────────────
# AC Asset  (8 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_assets(
    page: int = 1,
    page_size: int = 20,
    lifecycle_status: str = None,
    department: str = None,
    location: str = None,
    asset_category: str = None,
    search: str = None,
    gmdn_status: str = None,
):
    """GET /api/method/assetcore.api.imm00.list_assets"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if lifecycle_status:
        filters["lifecycle_status"] = lifecycle_status
    if department:
        filters["department"] = department
    if location:
        filters["location"] = location
    if asset_category:
        filters["asset_category"] = asset_category
    if gmdn_status:
        filters["gmdn_status"] = gmdn_status

    or_filters = None
    if search:
        like = f"%{search}%"
        or_filters = [
            [_DT_ASSET, "asset_name",      "like", like],
            [_DT_ASSET, "asset_code",      "like", like],
            [_DT_ASSET, "manufacturer_sn", "like", like],
        ]
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tab{_DT_ASSET}`"
            f" WHERE asset_name LIKE %s OR asset_code LIKE %s OR manufacturer_sn LIKE %s",
            [like, like, like],
        )[0][0]
    else:
        total = frappe.db.count(_DT_ASSET, filters=filters)

    pag = paginate(int(total), page, page_size)

    fields = [
        "name", "asset_name", "asset_code", "lifecycle_status",
        "asset_category", "location", "department", "responsible_technician",
        "next_pm_date", "next_calibration_date", "byt_reg_expiry",
        "gmdn_code", "gmdn_status",
        "gross_purchase_amount", "accumulated_depreciation", "current_book_value",
    ]
    items = frappe.get_list(
        _DT_ASSET,
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=fields,
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by=_ORDER_MODIFIED_DESC,
    )
    _enrich(items, "asset_category", _DT_ASSET_CATEGORY, "category_name")
    _enrich(items, "department", _DT_DEPARTMENT, "department_name")
    _enrich(items, "location", _DT_LOCATION, "location_name")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_asset(name: str):
    """GET /api/method/assetcore.api.imm00.get_asset?name=AC-ASSET-..."""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_ASSET, name).as_dict()
    # Enrich linked display names
    if doc.get("asset_category"):
        doc["category_name"] = frappe.db.get_value(_DT_ASSET_CATEGORY, doc["asset_category"], "category_name") or ""
    if doc.get("department"):
        doc["department_name"] = frappe.db.get_value(_DT_DEPARTMENT, doc["department"], "department_name") or ""
    if doc.get("location"):
        doc["location_name"] = frappe.db.get_value(_DT_LOCATION, doc["location"], "location_name") or ""
    if doc.get("supplier"):
        doc["supplier_name"] = frappe.db.get_value(_DT_SUPPLIER, doc["supplier"], "supplier_name") or ""
    if doc.get("device_model"):
        doc["device_model_name"] = frappe.db.get_value(_DT_DEVICE_MODEL, doc["device_model"], "model_name") or ""
    if doc.get("responsible_technician"):
        doc["responsible_technician_name"] = frappe.db.get_value("User", doc["responsible_technician"], "full_name") or ""
    return _ok(doc)


@frappe.whitelist(methods=["POST"])
def create_asset():
    """POST /api/method/assetcore.api.imm00.create_asset

    Hỗ trợ 2 luồng:
      1. Tài sản có sẵn (không qua phiếu tiếp nhận) → cho phép set lifecycle_status
         ban đầu là Commissioned/Active. API insert ở Draft (theo workflow), rồi
         dùng transition_asset_status để dịch chuyển → đúng workflow + audit trail.
      2. Tài sản mua mới → đi qua flow IMM-04 Commissioning, không gọi endpoint này.
    """
    data = dict(frappe.local.form_dict)
    desired_status = data.pop("lifecycle_status", None) or ""
    try:
        doc = frappe.new_doc(_DT_ASSET)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert(ignore_permissions=False)
        if desired_status and desired_status != doc.lifecycle_status:
            # Draft → Active phải đi qua Commissioned (state machine guard).
            chain = ["Commissioned", "Active"] if desired_status == "Active" else [desired_status]
            for step in chain:
                transition_asset_status(
                    doc.name, step,
                    actor=frappe.session.user,
                    reason=_("Khởi tạo tài sản có sẵn"),
                )
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_asset(name: str):
    """POST /api/method/assetcore.api.imm00.update_asset"""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(_DT_ASSET, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save(ignore_permissions=False)
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def transition_status(name: str, to_status: str, reason: str = ""):
    """POST /api/method/assetcore.api.imm00.transition_status"""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    try:
        actor = frappe.session.user
        transition_asset_status(name, to_status, actor=actor, reason=reason)
        frappe.db.commit()
        return _ok({"name": name, "lifecycle_status": to_status})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_gmdn_status(name: str, gmdn_status: str, reason: str = ""):
    """POST /api/method/assetcore.api.imm00.update_gmdn_status"""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    try:
        result = svc_update_gmdn_status(name, gmdn_status, reason)
        frappe.db.commit()
        return _ok(result)
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def toggle_gmdn_status(name: str):
    """POST /api/method/assetcore.api.imm00.toggle_gmdn_status — toggle qua QR scan."""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    try:
        result = svc_toggle_gmdn_via_qr(name)
        frappe.db.commit()
        return _ok(result)
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist()
def get_asset_timeline(name: str, page: int = 1, page_size: int = 50):
    """GET /api/method/assetcore.api.imm00.get_asset_timeline"""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    page, page_size = int(page), int(page_size)
    total = frappe.db.count(_DT_LIFECYCLE_EVENT, {"asset": name})
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_LIFECYCLE_EVENT,
        filters={"asset": name},
        fields=["name", "event_type", "actor", "from_status", "to_status", "timestamp", "notes"],
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by=_ORDER_EVENT_TS_DESC,
    )
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def validate_for_operations(name: str):
    """GET /api/method/assetcore.api.imm00.validate_for_operations"""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    try:
        validate_asset_for_operations(name)
        return _ok({"valid": True})
    except frappe.exceptions.ValidationError as e:
        return _ok({"valid": False, "reason": str(e)})


@frappe.whitelist()
def get_asset_kpi(name: str):
    """GET /api/method/assetcore.api.imm00.get_asset_kpi"""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_ASSET, name)
    return _ok({
        "name": name,
        "lifecycle_status": doc.lifecycle_status,
        "uptime_pct": doc.get("uptime_pct"),
        "mtbf_days": doc.get("mtbf_days"),
        "mttr_hours": doc.get("mttr_hours"),
        "pm_compliance_pct": doc.get("pm_compliance_pct"),
        "total_repair_cost": doc.get("total_repair_cost"),
        "next_pm_date": doc.next_pm_date,
        "next_calibration_date": doc.next_calibration_date,
        "byt_reg_expiry": doc.byt_reg_expiry,
    })


# ─────────────────────────────────────────────────────────────────────────────
# AC Supplier  (4 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_suppliers(page: int = 1, page_size: int = 20, search: str = None, supplier_type: str = None):
    """GET /api/method/assetcore.api.imm00.list_suppliers"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if supplier_type:
        filters["supplier_type"] = supplier_type

    or_filters = None
    if search:
        like = f"%{search}%"
        or_filters = [
            [_DT_SUPPLIER, "name",          "like", like],
            [_DT_SUPPLIER, "supplier_name", "like", like],
            [_DT_SUPPLIER, "supplier_code", "like", like],
            [_DT_SUPPLIER, "email_id",      "like", like],
            [_DT_SUPPLIER, "tax_id",        "like", like],
        ]
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tab{_DT_SUPPLIER}`"
            f" WHERE name LIKE %s OR supplier_name LIKE %s OR supplier_code LIKE %s"
            f" OR email_id LIKE %s OR tax_id LIKE %s",
            [like, like, like, like, like],
        )[0][0]
    else:
        total = frappe.db.count(_DT_SUPPLIER, filters=filters)

    pag = paginate(int(total), page, page_size)
    items = frappe.get_list(
        _DT_SUPPLIER,
        filters=filters,
        or_filters=or_filters,
        fields=["name", "supplier_name", "supplier_code", "supplier_group", "vendor_type",
                "country", "email_id", "phone", "contract_end", "is_active"],
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by="supplier_name asc",
    )
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_supplier(name: str):
    """GET /api/method/assetcore.api.imm00.get_supplier"""
    if not frappe.db.exists(_DT_SUPPLIER, name):
        return _err(_(_ERR_SUPPLIER_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_SUPPLIER, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_supplier():
    """POST /api/method/assetcore.api.imm00.create_supplier"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_SUPPLIER)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_supplier(name: str):
    """POST /api/method/assetcore.api.imm00.update_supplier"""
    if not frappe.db.exists(_DT_SUPPLIER, name):
        return _err(_(_ERR_SUPPLIER_NOT_FOUND), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(_DT_SUPPLIER, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─────────────────────────────────────────────────────────────────────────────
# Locations / Departments / Categories  (6 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_locations(parent: str = None):
    """GET /api/method/assetcore.api.imm00.list_locations"""
    filters = {}
    if parent:
        filters["parent_location"] = parent
    items = frappe.get_list(
        _DT_LOCATION,
        filters=filters,
        fields=["name", "location_name", "location_code", "parent_location", "is_group",
                "clinical_area_type", "infection_control_level", "power_backup_available",
                "emergency_contact", "dept_head", "technical_contact", "notes"],
        order_by="lft asc",
    )
    return _ok(items)


@frappe.whitelist()
def list_departments(parent: str = None):
    """GET /api/method/assetcore.api.imm00.list_departments"""
    filters = {}
    if parent:
        filters["parent_department"] = parent
    items = frappe.get_list(
        _DT_DEPARTMENT,
        filters=filters,
        fields=["name", "department_name", "department_code", "parent_department", "is_group",
                "dept_head", "phone", "email", "is_active"],
        order_by="lft asc",
    )
    return _ok(items)


@frappe.whitelist()
def list_asset_categories():
    """GET /api/method/assetcore.api.imm00.list_asset_categories"""
    items = frappe.get_list(
        _DT_ASSET_CATEGORY,
        fields=["name", "category_name", "description",
                "default_pm_required", "default_pm_interval_days",
                "default_calibration_required", "default_calibration_interval_days",
                "default_depreciation_method", "total_depreciation_months",
                "depreciation_frequency", "default_residual_value_pct",
                "has_radiation", "is_active"],
        order_by="category_name asc",
    )
    return _ok(items)


def _norm_check(d: dict, fields: list) -> dict:
    """Normalize Frappe Check fields (True/False booleans) to 0/1 integers."""
    for f in fields:
        if f in d:
            d[f] = 1 if d[f] else 0
    return d


@frappe.whitelist()
def get_location(name: str):
    """GET /api/method/assetcore.api.imm00.get_location"""
    if not frappe.db.exists(_DT_LOCATION, name):
        return _err(_("Location not found"), 404)
    d = frappe.get_doc(_DT_LOCATION, name).as_dict()
    _norm_check(d, ["is_group", "power_backup_available"])
    return _ok(d)


@frappe.whitelist()
def get_department(name: str):
    """GET /api/method/assetcore.api.imm00.get_department"""
    if not frappe.db.exists(_DT_DEPARTMENT, name):
        return _err(_("Department not found"), 404)
    d = frappe.get_doc(_DT_DEPARTMENT, name).as_dict()
    _norm_check(d, ["is_group", "is_active"])
    return _ok(d)


@frappe.whitelist()
def get_asset_category(name: str):
    """GET /api/method/assetcore.api.imm00.get_asset_category"""
    if not frappe.db.exists(_DT_ASSET_CATEGORY, name):
        return _err(_("Asset Category not found"), 404)
    d = frappe.get_doc(_DT_ASSET_CATEGORY, name).as_dict()
    _norm_check(d, ["default_pm_required", "default_calibration_required", "has_radiation", "is_active"])
    return _ok(d)


@frappe.whitelist(methods=["POST"])
def create_location():
    """POST /api/method/assetcore.api.imm00.create_location"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_LOCATION)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def create_department():
    """POST /api/method/assetcore.api.imm00.create_department"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_DEPARTMENT)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def create_asset_category():
    """POST /api/method/assetcore.api.imm00.create_asset_category"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_ASSET_CATEGORY)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─────────────────────────────────────────────────────────────────────────────
# IMM Device Model  (4 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_device_models(page: int = 1, page_size: int = 20, manufacturer: str = None, search: str = None):
    """GET /api/method/assetcore.api.imm00.list_device_models"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if manufacturer:
        filters["manufacturer"] = manufacturer
    or_filters = []
    if search:
        or_filters = [
            [_DT_DEVICE_MODEL, "name", "like", f"%{search}%"],
            [_DT_DEVICE_MODEL, "model_name", "like", f"%{search}%"],
            [_DT_DEVICE_MODEL, "manufacturer", "like", f"%{search}%"],
            [_DT_DEVICE_MODEL, "model_version", "like", f"%{search}%"],
            [_DT_DEVICE_MODEL, "gmdn_code", "like", f"%{search}%"],
        ]
        like = f"%{search}%"
        filter_conds = " OR ".join([
            f"name LIKE {frappe.db.escape(like)}",
            f"model_name LIKE {frappe.db.escape(like)}",
            f"manufacturer LIKE {frappe.db.escape(like)}",
            f"model_version LIKE {frappe.db.escape(like)}",
            f"gmdn_code LIKE {frappe.db.escape(like)}",
        ])
        manufacturer_cond = f" AND manufacturer = {frappe.db.escape(manufacturer)}" if manufacturer else ""
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tab{_DT_DEVICE_MODEL}` WHERE ({filter_conds}){manufacturer_cond}"
        )[0][0]
    else:
        total = frappe.db.count(_DT_DEVICE_MODEL, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_DEVICE_MODEL,
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=["name", "model_name", "model_version", "manufacturer",
                "medical_device_class", "gmdn_code", "asset_category", "model_image"],
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by="model_name asc",
    )
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_device_model(name: str):
    """GET /api/method/assetcore.api.imm00.get_device_model"""
    if not frappe.db.exists(_DT_DEVICE_MODEL, name):
        return _err(_(_ERR_DEVICE_MODEL_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_DEVICE_MODEL, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_device_model():
    """POST /api/method/assetcore.api.imm00.create_device_model"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_DEVICE_MODEL)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_device_model(name: str):
    """POST /api/method/assetcore.api.imm00.update_device_model"""
    if not frappe.db.exists(_DT_DEVICE_MODEL, name):
        return _err(_(_ERR_DEVICE_MODEL_NOT_FOUND), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(_DT_DEVICE_MODEL, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─── Device Model file upload ────────────────────────────────────────────────
_DEVICE_MODEL_FOLDER = "Home/Device Models"


def _ensure_device_model_folder() -> str:
    """Đảm bảo folder Home/Device Models tồn tại trong File tree, return name."""
    if frappe.db.exists("File", _DEVICE_MODEL_FOLDER):
        return _DEVICE_MODEL_FOLDER
    folder = frappe.get_doc({
        "doctype":   "File",
        "file_name": "Device Models",
        "is_folder": 1,
        "folder":    "Home",
    })
    folder.insert(ignore_permissions=True)
    return folder.name


@frappe.whitelist(methods=["POST"])
def upload_device_model_file(model_name: str = "", fieldname: str = "model_image"):
    """POST — Upload 1 file vào folder Home/Device Models, attach vào IMM Device Model nếu có model_name.

    Form-data:
      - file: File (required)
      - model_name: optional — nếu có sẽ attach vào doc + set field
      - fieldname: 'model_image' | 'catalog_file' (default: model_image)

    Returns: { file_url, file_name, name }
    """
    if fieldname not in ("model_image", "catalog_file"):
        return _err(_("fieldname phải là 'model_image' hoặc 'catalog_file'"), 400)

    files = frappe.request.files
    if not files or "file" not in files:
        return _err(_("Thiếu file upload"), 400)
    upload = files["file"]
    if not upload.filename:
        return _err(_("File không có tên"), 400)

    folder_name = _ensure_device_model_folder()

    file_doc = frappe.get_doc({
        "doctype":      "File",
        "file_name":    upload.filename,
        "folder":       folder_name,
        "is_private":   0,
        "content":      upload.stream.read(),
        "decode":       False,
    })
    if model_name and frappe.db.exists(_DT_DEVICE_MODEL, model_name):
        file_doc.attached_to_doctype = _DT_DEVICE_MODEL
        file_doc.attached_to_name    = model_name
        file_doc.attached_to_field   = fieldname
    file_doc.save(ignore_permissions=True)

    if model_name and frappe.db.exists(_DT_DEVICE_MODEL, model_name):
        frappe.db.set_value(_DT_DEVICE_MODEL, model_name, fieldname, file_doc.file_url,
                            update_modified=False)

    return _ok({
        "name":      file_doc.name,
        "file_url":  file_doc.file_url,
        "file_name": file_doc.file_name,
        "fieldname": fieldname,
    })


# ─────────────────────────────────────────────────────────────────────────────
# IMM SLA Policy  (2 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_sla_policies(priority: str = None, risk_class: str = None,
                       is_active: str = None):
    """GET /api/method/assetcore.api.imm00.list_sla_policies

    Mặc định trả về TẤT CẢ chính sách (cả active và inactive) để FE tự lọc.
    Truyền is_active=1 hoặc 0 nếu muốn lọc ở BE.
    """
    filters: dict = {}
    if priority:
        filters["priority"] = priority
    if risk_class:
        filters["risk_class"] = risk_class
    if is_active in ("0", "1", 0, 1):
        filters["is_active"] = int(is_active)
    items = frappe.get_list(
        _DT_SLA_POLICY,
        filters=filters,
        fields=["name", "policy_name", "priority", "risk_class", "is_default",
                "is_active", "response_time_minutes", "resolution_time_hours"],
        order_by="is_active desc, priority asc, risk_class asc",
        ignore_permissions=False,
    )
    # Normalize Check fields → int 0/1 (Frappe đôi khi trả str/bool gây sai lệch FE)
    for it in items:
        it["is_active"] = 1 if it.get("is_active") else 0
        it["is_default"] = 1 if it.get("is_default") else 0
    return _ok(items)


@frappe.whitelist()
def resolve_sla_policy(priority: str, risk_class: str):
    """GET /api/method/assetcore.api.imm00.resolve_sla_policy"""
    try:
        policy = get_sla_policy(priority, risk_class)
        if not policy:
            return _err(_("Không tìm thấy SLA Policy phù hợp"), 404)
        return _ok(policy)
    except Exception as e:
        return _err(str(e), 500)


# ─────────────────────────────────────────────────────────────────────────────
# IMM Audit Trail  (3 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_audit_trail(asset: str = None, q: str = None,
                      page: int = 1, page_size: int = 50):
    """GET /api/method/assetcore.api.imm00.list_audit_trail

    Params (tất cả optional):
      - asset: lọc theo 1 mã thiết bị cụ thể
      - q:     free-text search trong change_summary / actor / ref_name / asset name
      - page, page_size: phân trang (default 50)

    Không truyền filter → trả về N bản ghi mới nhất toàn hệ thống.
    """
    page, page_size = int(page), int(page_size)
    filters: dict = {}

    if asset:
        if not frappe.db.exists(_DT_ASSET, asset):
            return _err(_(_ERR_ASSET_NOT_FOUND), 404)
        filters["asset"] = asset

    or_filters = None
    if q:
        like = f"%{q}%"
        or_filters = [
            ["asset", "like", like],
            ["change_summary", "like", like],
            ["actor", "like", like],
            ["ref_name", "like", like],
        ]

    if or_filters:
        total = frappe.db.count(_DT_AUDIT_TRAIL, or_filters=or_filters)
    else:
        total = frappe.db.count(_DT_AUDIT_TRAIL, filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_AUDIT_TRAIL,
        filters=filters,
        or_filters=or_filters,
        fields=["name", "asset", "event_type", "actor", "change_summary",
                "from_status", "to_status", "ref_doctype", "ref_name",
                "timestamp", "hash_sha256 as hash"],
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by=_ORDER_EVENT_TS_DESC,
    )
    # Batch-enrich với asset_name (tránh N+1; dùng UX pattern "Tên chính — Mã phụ")
    asset_ids = {r.get("asset") for r in items if r.get("asset")}
    if asset_ids:
        name_map = {
            a["name"]: a["asset_name"]
            for a in frappe.get_all(
                _DT_ASSET,
                filters={"name": ["in", list(asset_ids)]},
                fields=["name", "asset_name"],
            )
        }
        for r in items:
            r["asset_name"] = name_map.get(r.get("asset"), "")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_audit_entry(name: str):
    """GET /api/method/assetcore.api.imm00.get_audit_entry"""
    if not frappe.db.exists(_DT_AUDIT_TRAIL, name):
        return _err(_(_ERR_AUDIT_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_AUDIT_TRAIL, name).as_dict())


@frappe.whitelist()
def verify_chain(asset: str):
    """GET /api/method/assetcore.api.imm00.verify_chain"""
    if not frappe.db.exists(_DT_ASSET, asset):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    result = verify_audit_chain(asset)
    return _ok(result)


# ─────────────────────────────────────────────────────────────────────────────
# IMM CAPA Record  (5 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_capas(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    capa_type: str = None,
    asset: str = None,
):
    """GET /api/method/assetcore.api.imm00.list_capas"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if status:
        filters["status"] = status
    if capa_type:
        filters["capa_type"] = capa_type
    if asset:
        filters["asset"] = asset
    total = frappe.db.count(_DT_CAPA, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_CAPA,
        filters=filters,
        fields=["name", "capa_type", "status", "asset", "title",
                "due_date", "owner", "creation"],
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by=_ORDER_DUE_DATE_ASC,
    )
    _enrich(items, "asset", _DT_ASSET, "asset_name")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_capa(name: str):
    """GET /api/method/assetcore.api.imm00.get_capa"""
    if not frappe.db.exists(_DT_CAPA, name):
        return _err(_(_ERR_CAPA_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_CAPA, name).as_dict()
    if doc.get("asset"):
        doc["asset_name"] = frappe.db.get_value(_DT_ASSET, doc["asset"], "asset_name") or ""
    return _ok(doc)


@frappe.whitelist(methods=["POST"])
def open_capa():
    """POST /api/method/assetcore.api.imm00.open_capa"""
    data = frappe.local.form_dict
    required = ("asset", "severity", "description", "responsible")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return _err(_(f"Thiếu trường bắt buộc: {', '.join(missing)}"), 422)
    try:
        name = create_capa(
            asset=data["asset"],
            source_type=data.get("source_type", "Nonconformance"),
            source_ref=data.get("source_ref", ""),
            severity=data["severity"],
            description=data["description"],
            responsible=data["responsible"],
            due_days=int(data.get("due_days", 30)),
        )
        frappe.db.commit()
        return _ok({"name": name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def close_capa_record(name: str):
    """POST /api/method/assetcore.api.imm00.close_capa_record"""
    if not frappe.db.exists(_DT_CAPA, name):
        return _err(_(_ERR_CAPA_NOT_FOUND), 404)
    data = frappe.local.form_dict
    required = ("root_cause", "corrective_action", "preventive_action")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return _err(_(f"Thiếu trường bắt buộc: {', '.join(missing)}"), 422)
    try:
        close_capa(
            capa_name=name,
            root_cause=data["root_cause"],
            corrective_action=data["corrective_action"],
            preventive_action=data["preventive_action"],
            effectiveness_check=data.get("effectiveness_check"),
            actor=frappe.session.user,
        )
        frappe.db.commit()
        return _ok({"name": name, "status": "Closed"})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist()
def list_overdue_capas(page: int = 1, page_size: int = 20):
    """GET /api/method/assetcore.api.imm00.list_overdue_capas"""
    from frappe.utils import nowdate
    page, page_size = int(page), int(page_size)
    filters = [
        ["status", "in", ["Open", "In Progress"]],
        ["due_date", "<", nowdate()],
    ]
    total = frappe.db.count(_DT_CAPA, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_CAPA,
        filters=filters,
        fields=["name", "capa_type", "status", "asset", "title", "due_date", "owner"],
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by=_ORDER_DUE_DATE_ASC,
    )
    return _ok({"pagination": pag, "items": items})


# ─────────────────────────────────────────────────────────────────────────────
# Asset Lifecycle Event  (2 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_lifecycle_events(asset: str, page: int = 1, page_size: int = 50, event_type: str = None):
    """GET /api/method/assetcore.api.imm00.list_lifecycle_events"""
    if not frappe.db.exists(_DT_ASSET, asset):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    page, page_size = int(page), int(page_size)
    filters = {"asset": asset}
    if event_type:
        filters["event_type"] = event_type
    total = frappe.db.count(_DT_LIFECYCLE_EVENT, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_LIFECYCLE_EVENT,
        filters=filters,
        fields=["name", "event_type", "actor", "from_status", "to_status",
                "timestamp", "root_doctype", "root_record", "notes"],
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by=_ORDER_EVENT_TS_DESC,
    )
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_lifecycle_event(name: str):
    """GET /api/method/assetcore.api.imm00.get_lifecycle_event"""
    if not frappe.db.exists(_DT_LIFECYCLE_EVENT, name):
        return _err(_(_ERR_LIFECYCLE_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_LIFECYCLE_EVENT, name).as_dict())


# ─────────────────────────────────────────────────────────────────────────────
# Incident Report  (5 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_incidents(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    severity: str = None,
    asset: str = None,
):
    """GET /api/method/assetcore.api.imm00.list_incidents"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if status:
        filters["status"] = status
    if severity:
        filters["severity"] = severity
    if asset:
        filters["asset"] = asset
    total = frappe.db.count(_DT_INCIDENT, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_INCIDENT,
        filters=filters,
        fields=["name", "severity", "status", "asset", "description",
                "reported_at", "incident_type", "patient_affected", "reported_to_byt"],
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by="reported_at desc",
    )
    _enrich(items, "asset", _DT_ASSET, "asset_name")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_incident(name: str):
    """GET /api/method/assetcore.api.imm00.get_incident"""
    if not frappe.db.exists(_DT_INCIDENT, name):
        return _err(_(_ERR_INCIDENT_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_INCIDENT, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_incident():
    """POST /api/method/assetcore.api.imm00.create_incident"""
    data = frappe.local.form_dict
    required = ("asset", "severity", "incident_type", "description")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return _err(_(f"Thiếu trường bắt buộc: {', '.join(missing)}"), 422)
    try:
        doc = frappe.new_doc(_DT_INCIDENT)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_incident(name: str):
    """POST /api/method/assetcore.api.imm00.update_incident"""
    if not frappe.db.exists(_DT_INCIDENT, name):
        return _err(_(_ERR_INCIDENT_NOT_FOUND), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(_DT_INCIDENT, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def submit_incident(name: str):
    """POST /api/method/assetcore.api.imm00.submit_incident — submit + create lifecycle event"""
    if not frappe.db.exists(_DT_INCIDENT, name):
        return _err(_(_ERR_INCIDENT_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_INCIDENT, name)
    if doc.docstatus == 1:
        return _err(_("Incident Report đã được submit"), 422)
    try:
        doc.submit()
        frappe.db.commit()
        return _ok({"name": name, "status": doc.status})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─────────────────────────────────────────────────────────────────────────────
# Asset Transfer  (3 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_transfers(asset: str = None, status: str = None,
                   page: int = 1, page_size: int = 20):
    """GET /api/method/assetcore.api.imm00.list_transfers"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if asset:
        filters["asset"] = asset
    if status:
        filters["status"] = status
    total = frappe.db.count(_DT_TRANSFER, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_TRANSFER,
        filters=filters,
        fields=["name", "asset", "transfer_date", "transfer_type", "status",
                "from_location", "to_location", "from_department", "to_department",
                "from_custodian", "to_custodian", "reason",
                "approved_by", "approval_date", "received_by", "received_date"],
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by="transfer_date desc",
    )
    asset_ids = {r.get("asset") for r in items if r.get("asset")}
    if asset_ids:
        name_map = {a["name"]: a["asset_name"] for a in frappe.get_all(
            _DT_ASSET, filters={"name": ["in", list(asset_ids)]},
            fields=["name", "asset_name"])}
        for r in items:
            r["asset_name"] = name_map.get(r.get("asset"), "")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_transfer(name: str):
    """GET /api/method/assetcore.api.imm00.get_transfer"""
    if not frappe.db.exists(_DT_TRANSFER, name):
        return _err(_(_ERR_TRANSFER_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_TRANSFER, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_transfer():
    """POST — Tạo phiếu yêu cầu luân chuyển (status = Pending Approval)."""
    data = {k: v for k, v in frappe.local.form_dict.items() if k not in ("cmd", "doctype")}
    try:
        return _ok(create_transfer_request(data))
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def delete_transfer(name: str):
    """POST — Hủy phiếu luân chuyển (chỉ khi Pending Approval hoặc Rejected)."""
    try:
        return _ok(cancel_transfer_request(name))
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─────────────────────────────────────────────────────────────────────────────
# Service Contract  (4 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_service_contracts(
    supplier: str = None,
    contract_type: str = None,
    page: int = 1,
    page_size: int = 20,
):
    """GET /api/method/assetcore.api.imm00.list_service_contracts"""
    try:
        page, page_size = int(page), int(page_size)
        filters = {}
        if supplier:
            filters["supplier"] = supplier
        if contract_type:
            filters["contract_type"] = contract_type
        total = frappe.db.count(_DT_SERVICE_CONTRACT, filters=filters)
        pag = paginate(total, page, page_size)
        items = frappe.get_list(
            _DT_SERVICE_CONTRACT,
            filters=filters,
            fields=["name", "contract_title", "supplier", "contract_type",
                    "contract_start", "contract_end", "contract_value", "sla_response_hours"],
            limit_start=pag["offset"],
            limit_page_length=page_size,
            order_by="contract_end asc",
        )
        _enrich(items, "supplier", _DT_SUPPLIER, "supplier_name")
        return _ok({"pagination": pag, "items": items})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "list_service_contracts error")
        return _err(str(e))


@frappe.whitelist()
def get_service_contract(name: str):
    """GET /api/method/assetcore.api.imm00.get_service_contract"""
    if not frappe.db.exists(_DT_SERVICE_CONTRACT, name):
        return _err(_(_ERR_CONTRACT_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_SERVICE_CONTRACT, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_service_contract():
    """POST /api/method/assetcore.api.imm00.create_service_contract"""
    data = frappe.local.form_dict
    required = ("contract_title", "supplier", "contract_type", "contract_start", "contract_end")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return _err(_(f"Thiếu trường bắt buộc: {', '.join(missing)}"), 422)
    try:
        doc = frappe.new_doc(_DT_SERVICE_CONTRACT)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_service_contract(name: str):
    """POST /api/method/assetcore.api.imm00.update_service_contract"""
    if not frappe.db.exists(_DT_SERVICE_CONTRACT, name):
        return _err(_(_ERR_CONTRACT_NOT_FOUND), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(_DT_SERVICE_CONTRACT, name)
        if doc.docstatus == 1:
            return _err(_("Hợp đồng đã submit, không thể sửa"), 422)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# Service Contract là DocType lưu trữ đơn giản — không có luồng duyệt.
# Lifecycle: create → update → delete (hoặc để contract_end qua hạn = tự deprecate).
# Dùng làm tham chiếu cho PM / Calibration / Repair WO khi thiết bị có hợp đồng.


@frappe.whitelist(methods=["POST"])
def delete_service_contract(name: str):
    """POST /api/method/assetcore.api.imm00.delete_service_contract"""
    if not frappe.db.exists(_DT_SERVICE_CONTRACT, name):
        return _err(_(_ERR_CONTRACT_NOT_FOUND), 404)
    try:
        doc = frappe.get_doc(_DT_SERVICE_CONTRACT, name)
        if doc.docstatus == 1:
            doc.cancel()
        frappe.delete_doc(_DT_SERVICE_CONTRACT, name, ignore_permissions=False)
        frappe.db.commit()
        return _ok({"name": name, "deleted": True})
    except (frappe.exceptions.ValidationError, frappe.exceptions.LinkExistsError) as e:
        return _err(str(e), 422)
    except Exception as e:
        return _err(f"Không thể xóa: {e}", 500)


@frappe.whitelist()
def list_asset_contracts(asset: str):
    """GET /api/method/assetcore.api.imm00.list_asset_contracts — contracts covering a specific asset"""
    if not frappe.db.exists(_DT_ASSET, asset):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    rows = frappe.db.sql(
        """
        SELECT sc.name, sc.contract_title, sc.supplier, sc.contract_type,
               sc.contract_start, sc.contract_end, sc.sla_response_hours
        FROM `tabService Contract` sc
        INNER JOIN `tabService Contract Asset` sca ON sca.parent = sc.name
        WHERE sca.asset = %s AND sc.docstatus = 1
        ORDER BY sc.contract_end ASC
        """,
        (asset,),
        as_dict=True,
    )
    return _ok(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler triggers  (3 endpoints — for testing / manual trigger)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def trigger_capa_overdue_check():
    """GET /api/method/assetcore.api.imm00.trigger_capa_overdue_check — admin only"""
    _assert_system_admin()
    from assetcore.services.imm00 import check_capa_overdue
    check_capa_overdue()
    return _ok({"triggered": "check_capa_overdue"})


@frappe.whitelist()
def trigger_contract_expiry_check():
    """GET /api/method/assetcore.api.imm00.trigger_contract_expiry_check — admin only"""
    _assert_system_admin()
    from assetcore.services.imm00 import check_vendor_contract_expiry
    check_vendor_contract_expiry()
    return _ok({"triggered": "check_vendor_contract_expiry"})


@frappe.whitelist()
def trigger_registration_expiry_check():
    """GET /api/method/assetcore.api.imm00.trigger_registration_expiry_check — admin only"""
    _assert_system_admin()
    from assetcore.services.imm00 import check_registration_expiry
    check_registration_expiry()
    return _ok({"triggered": "check_registration_expiry"})


# ─────────────────────────────────────────────────────────────────────────────
# Reference Data — Generic Update / Delete (Location, Department, Category)
# ─────────────────────────────────────────────────────────────────────────────

def _generic_update(doctype: str, name: str):
    if not frappe.db.exists(doctype, name):
        return _err(_("Không tìm thấy {0}").format(doctype), ErrorCode.NOT_FOUND)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(doctype, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), ErrorCode.BUSINESS_RULE)


def _generic_delete(doctype: str, name: str):
    if not frappe.db.exists(doctype, name):
        return _err(_("Không tìm thấy {0}").format(doctype), ErrorCode.NOT_FOUND)
    try:
        frappe.delete_doc(doctype, name, ignore_permissions=False)
        frappe.db.commit()
        return _ok({"name": name, "deleted": True})
    except frappe.exceptions.LinkExistsError as e:
        return _err(_("Không thể xóa — đang được tham chiếu: {0}").format(e),
                    ErrorCode.CONFLICT)
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), ErrorCode.BUSINESS_RULE)
    except Exception as e:
        return _err(_("Không thể xóa: {0}").format(e), ErrorCode.INTERNAL_ERROR)


@frappe.whitelist(methods=["POST"])
def update_location(name: str):
    return _generic_update(_DT_LOCATION, name)


@frappe.whitelist(methods=["POST"])
def delete_location(name: str):
    return _generic_delete(_DT_LOCATION, name)


@frappe.whitelist(methods=["POST"])
def update_department(name: str):
    return _generic_update(_DT_DEPARTMENT, name)


@frappe.whitelist(methods=["POST"])
def delete_department(name: str):
    return _generic_delete(_DT_DEPARTMENT, name)


@frappe.whitelist(methods=["POST"])
def update_asset_category(name: str):
    return _generic_update(_DT_ASSET_CATEGORY, name)


@frappe.whitelist(methods=["POST"])
def delete_asset_category(name: str):
    return _generic_delete(_DT_ASSET_CATEGORY, name)


@frappe.whitelist(methods=["POST"])
def delete_supplier(name: str):
    return _generic_delete(_DT_SUPPLIER, name)


@frappe.whitelist(methods=["POST"])
def delete_device_model(name: str):
    return _generic_delete(_DT_DEVICE_MODEL, name)


@frappe.whitelist(methods=["POST"])
def delete_asset(name: str):
    return _generic_delete(_DT_ASSET, name)


@frappe.whitelist(methods=["POST"])
def delete_incident(name: str):
    return _generic_delete(_DT_INCIDENT, name)


# ─────────────────────────────────────────────────────────────────────────────
# IMM SLA Policy — full CRUD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_sla_policy(name: str):
    if not frappe.db.exists(_DT_SLA_POLICY, name):
        return _err(_("SLA Policy not found"), 404)
    d = frappe.get_doc(_DT_SLA_POLICY, name).as_dict()
    # Normalize Check fields về int 0/1 để FE compare chính xác
    d["is_active"] = 1 if d.get("is_active") else 0
    d["is_default"] = 1 if d.get("is_default") else 0
    return _ok(d)


_SLA_CHECK_FIELDS = ("is_active", "is_default")


def _coerce_sla_payload(data: dict) -> dict:
    """Ép Check fields về int 0/1 để tránh sai lệch khi FE gửi '0'/'1' string."""
    out = {k: v for k, v in data.items() if k not in ("cmd", "doctype", "name")}
    for f in _SLA_CHECK_FIELDS:
        if f in out:
            v = out[f]
            out[f] = 1 if str(v).lower() in ("1", "true", "yes", "on") else 0
    return out


@frappe.whitelist(methods=["POST"])
def create_sla_policy():
    try:
        doc = frappe.new_doc(_DT_SLA_POLICY)
        doc.update(_coerce_sla_payload(dict(frappe.local.form_dict)))
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_sla_policy(name: str):
    if not frappe.db.exists(_DT_SLA_POLICY, name):
        return _err(_("SLA Policy not found"), 404)
    try:
        doc = frappe.get_doc(_DT_SLA_POLICY, name)
        doc.update(_coerce_sla_payload(dict(frappe.local.form_dict)))
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def delete_sla_policy(name: str):
    return _generic_delete(_DT_SLA_POLICY, name)


# ─────────────────────────────────────────────────────────────────────────────
# Incident — update/submit already exist; add get_supplier read
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Depreciation (straight-line calculation)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def compute_depreciation(name: str):
    """Compute straight-line depreciation based on in_service_date & useful_life_years."""
    from frappe.utils import getdate, nowdate, date_diff
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    a = frappe.db.get_value(_DT_ASSET, name, [
        "gross_purchase_amount", "residual_value", "useful_life_years",
        "in_service_date", "depreciation_method",
    ], as_dict=True) or {}
    gross = float(a.get("gross_purchase_amount") or 0)
    residual = float(a.get("residual_value") or 0)
    years = int(a.get("useful_life_years") or 0)
    start = a.get("in_service_date")
    method = (a.get("depreciation_method") or "").strip()
    if method in ("", "None") or gross <= 0 or years <= 0 or not start:
        return _ok({"accumulated": 0, "book_value": gross, "note": "Thiếu thông tin hoặc phương pháp = None"})
    depreciable = max(0.0, gross - residual)
    days_elapsed = max(0, date_diff(nowdate(), getdate(start)))
    total_days = years * 365
    if method == "Double Declining":
        rate = 2.0 / years
        accumulated = min(depreciable, depreciable * rate * (days_elapsed / 365))
    else:  # Straight Line + default
        accumulated = min(depreciable, depreciable * (days_elapsed / total_days))
    accumulated = round(accumulated, 2)
    book_value = round(gross - accumulated, 2)
    frappe.db.set_value(_DT_ASSET, name, {
        "accumulated_depreciation": accumulated,
        "current_book_value": book_value,
    })
    frappe.db.commit()
    return _ok({"accumulated": accumulated, "book_value": book_value, "method": method, "days_elapsed": days_elapsed})


# ─────────────────────────────────────────────────────────────────────────────
# Asset Transfer — Workflow endpoints
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_transfer_full(name: str):
    """GET — Lấy toàn bộ thông tin phiếu luân chuyển."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        return _err(_("Phiếu luân chuyển không tồn tại"), 404)
    return _ok(frappe.get_doc(_DT_TRANSFER, name).as_dict())


@frappe.whitelist(methods=["POST"])
def update_transfer(name: str):
    """POST — Cập nhật ghi chú / thông tin phiếu (chỉ khi Pending Approval)."""
    doc_status = frappe.db.get_value(_DT_TRANSFER, name, "status")
    if doc_status != "Pending Approval":
        return _err(_("Chỉ có thể chỉnh sửa phiếu đang Pending Approval"), 422)
    return _generic_update(_DT_TRANSFER, name)


@frappe.whitelist(methods=["POST"])
def approve_transfer(name: str):
    """POST — Phê duyệt phiếu luân chuyển → cập nhật vị trí thiết bị ngay."""
    try:
        return _ok(approve_transfer_request(name))
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def reject_transfer(name: str, rejection_reason: str = ""):
    """POST — Từ chối phiếu luân chuyển."""
    try:
        return _ok(reject_transfer_request(name, rejection_reason))
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def receive_transfer(name: str, handover_notes: str = ""):
    """POST — Bên nhận xác nhận đã tiếp nhận thiết bị."""
    try:
        return _ok(confirm_receipt(name, handover_notes))
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─────────────────────────────────────────────────────────────────────────────
# PM Schedule — List / CRUD (delegates basic fields)
# ─────────────────────────────────────────────────────────────────────────────

_DT_PM_SCHEDULE = "PM Schedule"
_DT_PM_TEMPLATE = "PM Checklist Template"
_DT_FIRMWARE_CR = "Firmware Change Request"
_DT_DOC_REQUEST = "Document Request"


def _paginated_list(doctype: str, filters: dict, fields: list[str],
                    page: int, page_size: int, order_by: str = _ORDER_MODIFIED_DESC):
    offset = (page - 1) * page_size
    total = frappe.db.count(doctype, filters)
    items = frappe.get_all(doctype, filters=filters, fields=fields,
                           order_by=order_by, limit=page_size, start=offset)
    return items, {"total": total, "page": page, "page_size": page_size}


@frappe.whitelist()
def list_pm_schedules(page: int = 1, page_size: int = 20, asset: str = None, status: str = None):
    f = {}
    if asset: f["asset_ref"] = asset
    if status: f["status"] = status
    items, meta = _paginated_list(_DT_PM_SCHEDULE, f,
        ["name", "asset_ref", "pm_type", "status", "pm_interval_days",
         "checklist_template", "responsible_technician",
         "last_pm_date", "next_due_date"],
        int(page), int(page_size), "next_due_date asc")
    asset_ids = {r.get("asset_ref") for r in items if r.get("asset_ref")}
    if asset_ids:
        info_map = {a["name"]: a for a in frappe.get_all(
            _DT_ASSET, filters={"name": ["in", list(asset_ids)]},
            fields=["name", "asset_name", "asset_code"])}
        for r in items:
            info = info_map.get(r.get("asset_ref")) or {}
            r["asset_name"] = info.get("asset_name") or ""
            r["asset_code"] = info.get("asset_code") or ""
    return _ok({"items": items, **meta})


@frappe.whitelist()
def get_pm_schedule(name: str):
    if not frappe.db.exists(_DT_PM_SCHEDULE, name):
        return _err(_("Không tìm thấy lịch PM"), ErrorCode.NOT_FOUND)
    return _ok(frappe.get_doc(_DT_PM_SCHEDULE, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_pm_schedule():
    data = frappe.local.form_dict
    # Validate field-level trước khi insert — trả fields cho FE highlight.
    missing = {}
    if not data.get("asset_ref"):
        missing["asset_ref"] = _("Vui lòng chọn thiết bị")
    if not data.get("checklist_template"):
        missing["checklist_template"] = _("Vui lòng chọn template checklist")
    if not data.get("pm_interval_days"):
        missing["pm_interval_days"] = _("Vui lòng nhập chu kỳ (ngày)")
    if missing:
        return _err(_("Thiếu thông tin bắt buộc"),
                    ErrorCode.VALIDATION_ERROR, fields=missing)

    try:
        doc = frappe.new_doc(_DT_PM_SCHEDULE)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.DuplicateEntryError:
        return _err(_("Lịch PM đã tồn tại cho thiết bị + loại PM này"),
                    ErrorCode.CONFLICT)
    except frappe.exceptions.LinkValidationError as e:
        return _err(str(e), ErrorCode.VALIDATION_ERROR)
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), ErrorCode.BUSINESS_RULE)


@frappe.whitelist(methods=["POST"])
def update_pm_schedule(name: str):
    return _generic_update(_DT_PM_SCHEDULE, name)


@frappe.whitelist(methods=["POST"])
def delete_pm_schedule(name: str):
    return _generic_delete(_DT_PM_SCHEDULE, name)


# ─────────────────────────────────────────────────────────────────────────────
# PM Checklist Template — List / CRUD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_pm_templates(page: int = 1, page_size: int = 50):
    items, meta = _paginated_list(_DT_PM_TEMPLATE, {},
        ["name", "template_name", "asset_category", "pm_type", "version", "effective_date"],
        int(page), int(page_size), _ORDER_MODIFIED_DESC)
    return _ok({"items": items, **meta})


@frappe.whitelist()
def get_pm_template(name: str):
    if not frappe.db.exists(_DT_PM_TEMPLATE, name):
        return _err(_("Template not found"), 404)
    return _ok(frappe.get_doc(_DT_PM_TEMPLATE, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_pm_template():
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_PM_TEMPLATE)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_pm_template(name: str):
    return _generic_update(_DT_PM_TEMPLATE, name)


@frappe.whitelist(methods=["POST"])
def delete_pm_template(name: str):
    return _generic_delete(_DT_PM_TEMPLATE, name)


# ─────────────────────────────────────────────────────────────────────────────
# Firmware Change Request — List / CRUD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_firmware_crs(page: int = 1, page_size: int = 20, status: str = None, asset: str = None):
    f = {}
    if status: f["status"] = status
    if asset: f["asset_ref"] = asset
    items, meta = _paginated_list(_DT_FIRMWARE_CR, f,
        ["name", "asset_ref", "version_before", "version_after", "status",
         "approved_by", "approved_datetime", "applied_datetime"],
        int(page), int(page_size))
    _enrich(items, "asset_ref", _DT_ASSET, "asset_name", "asset_name")
    return _ok({"items": items, **meta})


@frappe.whitelist()
def get_firmware_cr(name: str):
    if not frappe.db.exists(_DT_FIRMWARE_CR, name):
        return _err(_("FCR not found"), 404)
    return _ok(frappe.get_doc(_DT_FIRMWARE_CR, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_firmware_cr():
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_FIRMWARE_CR)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_firmware_cr(name: str):
    return _generic_update(_DT_FIRMWARE_CR, name)


@frappe.whitelist(methods=["POST"])
def delete_firmware_cr(name: str):
    return _generic_delete(_DT_FIRMWARE_CR, name)


# ─────────────────────────────────────────────────────────────────────────────
# Document Request — List / CRUD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_document_requests(page: int = 1, page_size: int = 20, status: str = None, asset: str = None):
    f = {}
    if status: f["status"] = status
    if asset: f["asset_ref"] = asset
    items, meta = _paginated_list(_DT_DOC_REQUEST, f,
        ["name", "asset_ref", "doc_type_required", "doc_category", "status",
         "priority", "assigned_to", "due_date", "fulfilled_by"],
        int(page), int(page_size), _ORDER_DUE_DATE_ASC)
    _enrich(items, "asset_ref", _DT_ASSET, "asset_name", "asset_name")
    return _ok({"items": items, **meta})


@frappe.whitelist()
def get_document_request(name: str):
    if not frappe.db.exists(_DT_DOC_REQUEST, name):
        return _err(_("Document Request not found"), 404)
    return _ok(frappe.get_doc(_DT_DOC_REQUEST, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_document_request():
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_DOC_REQUEST)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_document_request(name: str):
    return _generic_update(_DT_DOC_REQUEST, name)


@frappe.whitelist(methods=["POST"])
def delete_document_request(name: str):
    return _generic_delete(_DT_DOC_REQUEST, name)


# ─────────────────────────────────────────────────────────────────────────────
# Asset Downtime Metrics
# ─────────────────────────────────────────────────────────────────────────────

_DT_DOWNTIME_LOG = "AC Asset Downtime Log"


@frappe.whitelist()
def get_asset_downtime_metrics(asset_name: str, year: int | None = None):
    """Trả về thống kê dừng máy của 1 asset:
    - total_hours: tổng giờ dừng (closed + open đến hiện tại)
    - breakdown_count: số lần dừng máy (số log)
    - mttr_hours: Mean Time To Repair = total_hours / breakdown_count
    - by_reason: phân loại giờ dừng theo reason
    - current_open: log đang mở (nếu có)
    """
    if not frappe.db.exists("AC Asset", asset_name):
        return _err(_("Không tìm thấy thiết bị"), 404)

    now_dt = frappe.utils.now_datetime()
    y = int(year) if year else frappe.utils.getdate(frappe.utils.nowdate()).year
    start_of_year = f"{y}-01-01 00:00:00"
    end_of_year = f"{y}-12-31 23:59:59"

    rows = frappe.get_all(
        _DT_DOWNTIME_LOG,
        filters={
            "asset": asset_name,
            "start_time": ["between", [start_of_year, end_of_year]],
        },
        fields=["name", "reason", "start_time", "end_time",
                "downtime_hours", "is_open", "reference_doctype", "reference_name"],
        order_by="start_time desc",
        limit_page_length=0,
    )

    total_hours = 0.0
    by_reason: dict[str, float] = {}
    current_open = None
    for r in rows:
        if r["is_open"]:
            hrs = frappe.utils.time_diff_in_hours(now_dt, r["start_time"])
            current_open = {**r, "downtime_hours_so_far": round(hrs, 2)}
        else:
            hrs = float(r["downtime_hours"] or 0)
        total_hours += hrs
        by_reason[r["reason"]] = round(by_reason.get(r["reason"], 0.0) + hrs, 2)

    count = len(rows)
    mttr = round(total_hours / count, 2) if count else 0.0

    return _ok({
        "asset": asset_name,
        "year": y,
        "total_hours": round(total_hours, 2),
        "breakdown_count": count,
        "mttr_hours": mttr,
        "by_reason": by_reason,
        "current_open": current_open,
        "logs": rows[:10],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _assert_system_admin():
    if "System Manager" not in frappe.get_roles() and "IMM System Admin" not in frappe.get_roles():
        frappe.throw(_("Không có quyền thực hiện thao tác này"), frappe.PermissionError)


# ─── Depreciation Schedule (Phase 2) ─────────────────────────────────────────

@frappe.whitelist()
def get_depreciation_schedule(asset_name: str):
    """GET — Trả về schedule rows của 1 asset + tổng hợp."""
    if not frappe.db.exists("AC Asset", asset_name):
        return _err(_("Asset not found"), 404)
    rows = frappe.get_all(
        "AC Asset Depreciation Schedule",
        filters={"parent": asset_name, "parenttype": "AC Asset"},
        fields=["name", "period_number", "scheduled_date", "depreciation_amount",
                "accumulated_amount", "remaining_value", "status",
                "executed_on", "journal_entry"],
        order_by="period_number asc",
        limit_page_length=500,
    )
    summary = {
        "total_periods": len(rows),
        "executed_periods": sum(1 for r in rows if r.get("status") == "Executed"),
        "pending_periods":  sum(1 for r in rows if r.get("status") == "Pending"),
        "total_depreciated": sum(float(r.get("depreciation_amount") or 0)
                                  for r in rows if r.get("status") == "Executed"),
    }
    asset = frappe.db.get_value(
        "AC Asset", asset_name,
        ["gross_purchase_amount", "residual_value", "accumulated_depreciation",
         "current_book_value", "depreciation_method", "total_depreciation_months",
         "depreciation_frequency", "depreciation_start_date", "in_service_date"],
        as_dict=True,
    ) or {}
    return _ok({"asset": asset_name, "asset_info": asset, "rows": rows, "summary": summary})


@frappe.whitelist(methods=["POST"])
def regenerate_depreciation_schedule(asset_name: str, force: int = 1):
    """POST — Sinh lại schedule (xóa cũ nếu force=1)."""
    from assetcore.services import depreciation as depr_svc
    try:
        result = depr_svc.generate_schedule(asset_name, force=bool(int(force)))
        return _ok(result)
    except Exception as e:
        return _err(str(e), 400)


@frappe.whitelist()
def preview_depreciation_schedule(gross: float, residual: float, method: str,
                                    total_months: int, frequency: str, start_date: str):
    """GET — Preview schedule không lưu DB (dùng cho form before commit)."""
    from assetcore.services import depreciation as depr_svc
    rows = depr_svc.preview_schedule(
        float(gross or 0), float(residual or 0), method,
        int(total_months or 0), frequency or "Monthly", start_date,
    )
    return _ok(rows)


@frappe.whitelist(methods=["POST"])
def run_due_depreciation_now(as_of: str = ""):
    """POST — Thủ công chạy cron (dành cho admin/testing)."""
    _assert_system_admin()
    from assetcore.services import depreciation as depr_svc
    return _ok(depr_svc.run_due_depreciation(as_of or None))


@frappe.whitelist(methods=["POST"])
def bulk_regenerate_schedule_by_category(category_name: str):
    """POST — Áp dụng lại luật khấu hao của Category cho tất cả assets.

    Skip các assets đã có kỳ Executed (bảo vệ lịch sử).
    """
    _assert_system_admin()
    from assetcore.services import depreciation as depr_svc
    return _ok(depr_svc.bulk_regenerate_by_category(category_name))
