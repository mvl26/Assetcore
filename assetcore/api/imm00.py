# Copyright (c) 2026, AssetCore Team
"""IMM-00 REST API — 42 endpoints for AssetCore foundation DocTypes.

Convention:
  GET  → frappe.whitelist(allow_guest=False)
  POST → frappe.whitelist(methods=["POST"])
  Response: _ok(data) | _err(message, code)
"""
import frappe
from frappe import _

from assetcore.utils.response import _ok, _err
from assetcore.utils.pagination import paginate
from assetcore.services.imm00 import (
    transition_asset_status,
    validate_asset_for_operations,
    get_sla_policy,
    create_capa,
    close_capa,
    verify_audit_chain,
    transfer_asset,
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

    or_filters = []
    if search:
        or_filters = [
            ["asset_name", "like", f"%{search}%"],
            ["asset_code", "like", f"%{search}%"],
            ["manufacturer_sn", "like", f"%{search}%"],
        ]

    total = frappe.db.count(_DT_ASSET, filters=filters)
    pag = paginate(total, page, page_size)

    fields = [
        "name", "asset_name", "asset_code", "lifecycle_status",
        "asset_category", "location", "department", "responsible_technician",
        "next_pm_date", "next_calibration_date", "byt_reg_expiry",
    ]
    items = frappe.get_list(
        _DT_ASSET,
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=fields,
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by="modified desc",
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
    """POST /api/method/assetcore.api.imm00.create_asset"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_ASSET)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert(ignore_permissions=False)
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
    or_filters = []
    if search:
        or_filters = [
            ["supplier_name", "like", f"%{search}%"],
            ["tax_id", "like", f"%{search}%"],
        ]
    total = frappe.db.count(_DT_SUPPLIER, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_SUPPLIER,
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=["name", "supplier_name", "supplier_group", "country", "email_id", "contract_end"],
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
        fields=["name", "location_name", "location_type", "parent_location", "is_active"],
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
        fields=["name", "department_name", "parent_department", "head_of_department"],
        order_by="lft asc",
    )
    return _ok(items)


@frappe.whitelist()
def list_asset_categories():
    """GET /api/method/assetcore.api.imm00.list_asset_categories"""
    items = frappe.get_list(
        _DT_ASSET_CATEGORY,
        fields=["name", "category_name", "default_pm_interval_days", "default_calibration_interval_days"],
        order_by="category_name asc",
    )
    return _ok(items)


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
            ["model_name", "like", f"%{search}%"],
            ["model_number", "like", f"%{search}%"],
            ["gmdn_code", "like", f"%{search}%"],
        ]
    total = frappe.db.count(_DT_DEVICE_MODEL, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_DEVICE_MODEL,
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=["name", "model_name", "model_number", "manufacturer", "medical_device_class", "gmdn_code"],
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


# ─────────────────────────────────────────────────────────────────────────────
# IMM SLA Policy  (2 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_sla_policies(priority: str = None, risk_class: str = None):
    """GET /api/method/assetcore.api.imm00.list_sla_policies"""
    filters = {"is_active": 1}
    if priority:
        filters["priority"] = priority
    if risk_class:
        filters["risk_class"] = risk_class
    items = frappe.get_list(
        _DT_SLA_POLICY,
        filters=filters,
        fields=["name", "policy_name", "priority", "risk_class", "is_default",
                "response_time_minutes", "resolution_time_hours", "working_hours_only"],
        order_by="priority asc, risk_class asc",
    )
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

    total = frappe.db.count(_DT_AUDIT_TRAIL,
                             filters=filters if not or_filters else None,
                             or_filters=or_filters) if or_filters else \
            frappe.db.count(_DT_AUDIT_TRAIL, filters)
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
        order_by="due_date asc",
    )
    _enrich(items, "asset", _DT_ASSET, "asset_name")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_capa(name: str):
    """GET /api/method/assetcore.api.imm00.get_capa"""
    if not frappe.db.exists(_DT_CAPA, name):
        return _err(_(_ERR_CAPA_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_CAPA, name).as_dict())


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
        order_by="due_date asc",
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
def list_transfers(asset: str = None, page: int = 1, page_size: int = 20):
    """GET /api/method/assetcore.api.imm00.list_transfers"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if asset:
        filters["asset"] = asset
    total = frappe.db.count(_DT_TRANSFER, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_TRANSFER,
        filters=filters,
        fields=["name", "asset", "transfer_date", "transfer_type",
                "from_location", "to_location", "from_department", "to_department",
                "from_custodian", "to_custodian", "reason", "approved_by"],
        limit_start=pag["offset"],
        limit_page_length=page_size,
        order_by="transfer_date desc",
    )
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_transfer(name: str):
    """GET /api/method/assetcore.api.imm00.get_transfer"""
    if not frappe.db.exists(_DT_TRANSFER, name):
        return _err(_(_ERR_TRANSFER_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_TRANSFER, name).as_dict())


@frappe.whitelist(methods=["POST"])
def delete_transfer(name: str):
    """POST /api/method/assetcore.api.imm00.delete_transfer

    Draft → xóa hẳn. Submitted → cancel (giữ audit trail theo BR-00-04).
    """
    if not frappe.db.exists(_DT_TRANSFER, name):
        return _err(_(_ERR_TRANSFER_NOT_FOUND), 404)
    try:
        doc = frappe.get_doc(_DT_TRANSFER, name)
        if doc.docstatus == 0:
            frappe.delete_doc(_DT_TRANSFER, name, ignore_permissions=False)
            frappe.db.commit()
            return _ok({"name": name, "deleted": True})
        if doc.docstatus == 1:
            doc.cancel()
            frappe.db.commit()
            return _ok({"name": name, "cancelled": True,
                        "message": "Transfer đã hủy; lifecycle event giữ lại để đảm bảo audit trail."})
        return _err(_("Transfer đã bị hủy trước đó"), 422)
    except (frappe.exceptions.ValidationError, frappe.exceptions.LinkExistsError) as e:
        return _err(str(e), 422)
    except Exception as e:
        return _err(f"Không thể xóa: {e}", 500)


@frappe.whitelist(methods=["POST"])
def create_transfer():
    """POST /api/method/assetcore.api.imm00.create_transfer"""
    data = frappe.local.form_dict
    required = ("asset", "transfer_date", "transfer_type", "to_location", "reason")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return _err(_(f"Thiếu trường bắt buộc: {', '.join(missing)}"), 422)
    if not frappe.db.exists(_DT_ASSET, data["asset"]):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    try:
        doc = frappe.new_doc(_DT_TRANSFER)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        doc.submit()
        frappe.db.commit()
        return _ok({"name": doc.name})
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


@frappe.whitelist(methods=["POST"])
def submit_service_contract(name: str):
    """POST /api/method/assetcore.api.imm00.submit_service_contract"""
    if not frappe.db.exists(_DT_SERVICE_CONTRACT, name):
        return _err(_(_ERR_CONTRACT_NOT_FOUND), 404)
    try:
        doc = frappe.get_doc(_DT_SERVICE_CONTRACT, name)
        if doc.docstatus == 1:
            return _err(_("Hợp đồng đã submit"), 422)
        doc.submit()
        frappe.db.commit()
        return _ok({"name": doc.name, "docstatus": 1})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


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
        return _err(_(f"{doctype} not found"), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(doctype, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


def _generic_delete(doctype: str, name: str):
    if not frappe.db.exists(doctype, name):
        return _err(_(f"{doctype} not found"), 404)
    try:
        frappe.delete_doc(doctype, name, ignore_permissions=False)
        frappe.db.commit()
        return _ok({"name": name, "deleted": True})
    except frappe.exceptions.LinkExistsError as e:
        return _err(_(f"Không thể xóa — đang được tham chiếu: {e}"), 422)
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)
    except Exception as e:
        return _err(f"Không thể xóa: {e}", 500)


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
    return _ok(frappe.get_doc(_DT_SLA_POLICY, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_sla_policy():
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_SLA_POLICY)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_sla_policy(name: str):
    return _generic_update(_DT_SLA_POLICY, name)


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
# Asset Transfer — full CRUD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_transfer_full(name: str):
    if not frappe.db.exists(_DT_TRANSFER, name):
        return _err(_("Transfer not found"), 404)
    return _ok(frappe.get_doc(_DT_TRANSFER, name).as_dict())


@frappe.whitelist(methods=["POST"])
def update_transfer(name: str):
    return _generic_update(_DT_TRANSFER, name)


@frappe.whitelist(methods=["POST"])
def approve_transfer(name: str):
    if not frappe.db.exists(_DT_TRANSFER, name):
        return _err(_("Transfer not found"), 404)
    doc = frappe.get_doc(_DT_TRANSFER, name)
    doc.approved_by = frappe.session.user
    doc.approval_date = nowdate()
    doc.save()
    frappe.db.commit()
    return _ok({"name": name, "approved_by": doc.approved_by})


# ─────────────────────────────────────────────────────────────────────────────
# PM Schedule — List / CRUD (delegates basic fields)
# ─────────────────────────────────────────────────────────────────────────────

_DT_PM_SCHEDULE = "PM Schedule"
_DT_PM_TEMPLATE = "PM Checklist Template"
_DT_FIRMWARE_CR = "Firmware Change Request"
_DT_DOC_REQUEST = "Document Request"


def _paginated_list(doctype: str, filters: dict, fields: list[str],
                    page: int, page_size: int, order_by: str = "modified desc"):
    offset = (page - 1) * page_size
    total = frappe.db.count(doctype, filters)
    items = frappe.get_all(doctype, filters=filters, fields=fields,
                           order_by=order_by, limit=page_size, start=offset)
    return _ok({
        "items": items, "total": total,
        "page": page, "page_size": page_size,
    })


@frappe.whitelist()
def list_pm_schedules(page: int = 1, page_size: int = 20, asset: str = None, status: str = None):
    f = {}
    if asset: f["asset_ref"] = asset
    if status: f["status"] = status
    return _paginated_list(_DT_PM_SCHEDULE, f,
        ["name", "asset_ref", "pm_type", "status", "pm_interval_days",
         "checklist_template", "responsible_technician",
         "last_pm_date", "next_due_date"],
        int(page), int(page_size), "next_due_date asc")


@frappe.whitelist()
def get_pm_schedule(name: str):
    if not frappe.db.exists(_DT_PM_SCHEDULE, name):
        return _err(_("PM Schedule not found"), 404)
    return _ok(frappe.get_doc(_DT_PM_SCHEDULE, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_pm_schedule():
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_PM_SCHEDULE)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


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
    return _paginated_list(_DT_PM_TEMPLATE, {},
        ["name", "template_name", "asset_category", "pm_type", "version", "effective_date"],
        int(page), int(page_size), "modified desc")


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
    return _paginated_list(_DT_FIRMWARE_CR, f,
        ["name", "asset_ref", "version_before", "version_after", "status",
         "approved_by", "approved_datetime", "applied_datetime"],
        int(page), int(page_size))


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
    return _paginated_list(_DT_DOC_REQUEST, f,
        ["name", "asset_ref", "doc_type_required", "doc_category", "status",
         "priority", "assigned_to", "due_date", "fulfilled_by"],
        int(page), int(page_size), "due_date asc")


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
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _assert_system_admin():
    if "System Manager" not in frappe.get_roles() and "IMM System Admin" not in frappe.get_roles():
        frappe.throw(_("Không có quyền thực hiện thao tác này"), frappe.PermissionError)
