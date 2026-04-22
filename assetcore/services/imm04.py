# Copyright (c) 2026, AssetCore Team
"""Business logic for IMM-04 Asset Commissioning — Tier 2 service layer."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, get_first_day, getdate, nowdate

from assetcore.repositories.commissioning_repo import CommissioningRepo, NonConformanceRepo
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.pagination import paginate

# ─── Constants ────────────────────────────────────────────────────────────────

_DT = "Asset Commissioning"
_DT_NC = "Asset QA Non Conformance"
_DT_ASSET = "AC Asset"
_DT_MODEL = "IMM Device Model"
_DT_SUPPLIER = "AC Supplier"
_DT_DEPT = "AC Department"
_DT_PO = "Purchase Order"

_STATE_CLINICAL_RELEASE = "Clinical Release"
_STATE_INITIAL_INSPECTION = "Initial Inspection"
_STATE_RE_INSPECTION = "Re Inspection"
_TERMINAL_STATES = frozenset({_STATE_CLINICAL_RELEASE, "Return To Vendor"})
_SUBMIT_ROLES = frozenset({"VP Block2", "Workshop Head"})

_CLASS_I = "Class I"
_CLASS_II = "Class II"
_CLASS_III = "Class III"

_DOC_TYPE_CO = "CO - Chứng nhận Xuất xứ"
_DOC_TYPE_CQ = "CQ - Chứng nhận Chất lượng"
_DOC_TYPE_MANUAL = "Manual / HDSD"
_DOC_TYPE_WARRANTY = "Warranty Card"

_RISK_CLASS_MAP: dict[str, tuple[str, str]] = {
    "A": (_CLASS_I, "Low"),
    "B": (_CLASS_II, "Medium"),
    "C": (_CLASS_III, "High"),
    "D": (_CLASS_III, "Critical"),
}

_CREATE_FIELDS = (
    "po_reference", "master_item", "vendor", "clinical_dept",
    "expected_installation_date", "reception_date",
    "asset_description", "delivery_note_no", "purchase_price", "warranty_expiry_date",
    "vendor_engineer_name", "commissioned_by",
    "installation_location", "received_by", "dept_head_acceptance",
    "is_radiation_device", "risk_class", "radiation_license_no", "doa_incident",
    "clinical_head", "qa_officer", "board_approver", "facility_checklist_pass",
    "vendor_serial_no", "custom_moh_code",
)
_DATE_FIELDS = frozenset({"reception_date", "expected_installation_date", "warranty_expiry_date"})
_REQUIRED_FIELDS = ("po_reference", "master_item", "vendor", "clinical_dept", "expected_installation_date")

_EDITABLE_FIELDS = frozenset({
    "vendor_engineer_name", "qa_license_doc", "site_photo",
    "installation_evidence", "custom_moh_code",
    "risk_class", "reception_date", "clinical_head", "qa_officer",
    "board_approver", "facility_checklist_pass", "overall_inspection_result",
    "handover_doc", "radiation_license_no", "notes",
})

_LIST_FIELDS = [
    "name", "workflow_state", "docstatus",
    "po_reference", "master_item", "vendor",
    "clinical_dept", "expected_installation_date",
    "installation_date", "vendor_serial_no",
    "internal_tag_qr", "final_asset", "modified",
]

_ALLOWED_FILTER_KEYS = frozenset({
    "workflow_state", "po_reference", "master_item", "vendor",
    "clinical_dept", "docstatus", "is_radiation_device",
    "doa_incident", "vendor_serial_no", "internal_tag_qr",
    "expected_installation_date", "final_asset",
})

_ORDER_MODIFIED = "modified desc"

_ALLOWED_SEARCH_DOCTYPES: dict[str, dict] = {
    _DT_PO: {
        "label_field": "name",
        "search_fields": ["name", "supplier_name"],
        "filters": {"docstatus": 1},
        "extra_fields": ["supplier_name", "transaction_date"],
        "optional": True,
    },
    _DT_SUPPLIER: {
        "label_field": "supplier_name",
        "search_fields": ["name", "supplier_name", "supplier_code"],
        "filters": {"is_active": 1},
        "extra_fields": ["supplier_name", "supplier_code", "vendor_type"],
    },
    "AC Department": {
        "label_field": "department_name",
        "search_fields": ["name", "department_name", "department_code"],
        "filters": {},
        "extra_fields": ["department_name", "department_code"],
    },
    "AC Location": {
        "label_field": "location_name",
        "search_fields": ["name", "location_name", "location_code"],
        "filters": {},
        "extra_fields": ["location_name", "location_code", "clinical_area_type"],
    },
    "IMM Device Model": {
        "label_field": "model_name",
        "search_fields": ["name", "model_name", "manufacturer", "gmdn_code"],
        "filters": {},
        "extra_fields": ["model_name", "manufacturer", "medical_device_class"],
    },
    "AC Asset": {
        "label_field": "asset_name",
        "search_fields": ["name", "asset_name", "asset_code", "manufacturer_sn"],
        "filters": {},
        "extra_fields": ["asset_name", "asset_code", "manufacturer_sn", "lifecycle_status"],
    },
    "AC Asset Category": {
        "label_field": "category_name",
        "search_fields": ["name", "category_name"],
        "filters": {},
        "extra_fields": ["category_name"],
    },
    "User": {
        "label_field": "full_name",
        "search_fields": ["name", "full_name", "email"],
        "filters": {"enabled": 1},
        "extra_fields": ["full_name", "email"],
    },
    "AC Warehouse": {
        "label_field": "warehouse_name",
        "search_fields": ["name", "warehouse_name", "warehouse_code"],
        "filters": {"is_active": 1},
        "extra_fields": ["warehouse_name", "warehouse_code"],
    },
}


# ─── DocType Lifecycle Hooks (called from DocType controller) ─────────────────

def initialize_commissioning(doc: Document) -> None:
    """before_insert: defaults, auto-fill from Device Model, mandatory docs."""
    if not doc.reception_date:
        doc.reception_date = nowdate()
    _autofill_from_device_model(doc)
    _populate_mandatory_documents(doc)


def _autofill_from_device_model(doc: Document) -> None:
    if not doc.master_item:
        return
    model = frappe.db.get_value(
        _DT_MODEL, doc.master_item,
        ["medical_device_class", "risk_classification", "is_radiation_device",
         "is_pm_required", "pm_interval_days", "is_calibration_required", "calibration_interval_days"],
        as_dict=True,
    )
    if not model:
        return
    if doc.is_new():
        _class_map = {_CLASS_I: "A", _CLASS_II: "B", _CLASS_III: "C"}
        mapped = _class_map.get(model.medical_device_class, "")
        if mapped:
            doc.risk_class = mapped
    if model.is_radiation_device:
        doc.is_radiation_device = 1
        doc.risk_class = "Radiation"


def _populate_mandatory_documents(doc: Document) -> None:
    if doc.get("commissioning_documents"):
        return
    for d in [
        {"doc_type": _DOC_TYPE_CO, "is_mandatory": 1, "status": "Pending"},
        {"doc_type": _DOC_TYPE_CQ, "is_mandatory": 1, "status": "Pending"},
        {"doc_type": _DOC_TYPE_MANUAL, "is_mandatory": 1, "status": "Pending"},
        {"doc_type": _DOC_TYPE_WARRANTY, "is_mandatory": 0, "status": "Pending"},
    ]:
        doc.append("commissioning_documents", d)


def validate_commissioning(doc: Document) -> None:
    _vr01_unique_serial_number(doc)
    _vr06_immutable_lifecycle_events(doc)
    _vr05_risk_class_change_warning(doc)
    _validate_document_expiry(doc)


def _vr01_unique_serial_number(doc: Document) -> None:
    if not doc.vendor_serial_no:
        return
    existing_asset = frappe.db.get_value(_DT_ASSET, {"manufacturer_sn": doc.vendor_serial_no}, "name")
    if existing_asset and existing_asset != doc.get("final_asset"):
        frappe.throw(
            _("VR-01: Serial Number '{0}' đã được gán cho Tài Sản {1}.").format(doc.vendor_serial_no, existing_asset),
            frappe.DuplicateEntryError,
        )
    existing_comm = frappe.db.get_value(
        _DT, {"vendor_serial_no": doc.vendor_serial_no, "name": ("!=", doc.name or ""), "docstatus": ("!=", 2)}, "name",
    )
    if existing_comm:
        frappe.throw(
            _("VR-01: Serial Number '{0}' đã tồn tại trong Phiếu Nghiệm Thu {1}.").format(doc.vendor_serial_no, existing_comm),
            frappe.DuplicateEntryError,
        )


def _vr05_risk_class_change_warning(doc: Document) -> None:
    early = {"Draft", "Pending Doc Verify", "To Be Installed", "Installing", "Identification"}
    if doc.is_new() or doc.workflow_state in early:
        return
    original = frappe.db.get_value(_DT, doc.name, "risk_class")
    if original and original != doc.risk_class:
        frappe.msgprint(
            _("VR-05: Phân loại rủi ro thay đổi từ '{0}' → '{1}'. Cần phê duyệt QA Officer.").format(original, doc.risk_class),
            alert=True, indicator="orange",
        )


def _vr06_immutable_lifecycle_events(doc: Document) -> None:
    if doc.is_new():
        return
    existing = {
        e["name"]: e
        for e in frappe.db.get_all(
            "Asset Lifecycle Event",
            filters={"parent": doc.name, "parenttype": _DT},
            fields=["name", "event_timestamp", "actor", "event_type"],
        )
    }
    for row in doc.get("lifecycle_events") or []:
        if row.name and row.name in existing:
            orig = existing[row.name]
            if row.actor != orig["actor"] or row.event_type != orig["event_type"]:
                frappe.throw(_("VR-06: Nhật ký sự kiện vòng đời không được chỉnh sửa (ISO 13485 §4.2.5)."))


def _validate_document_expiry(doc: Document) -> None:
    today = getdate()
    for d in doc.get("commissioning_documents") or []:
        expiry = d.get("expiry_date")
        if expiry and d.get("status") == "Received":
            days = date_diff(expiry, today)
            if days < 0:
                frappe.throw(_("Tài liệu '{0}' đã hết hạn vào {1}.").format(d.doc_type, expiry))
            elif days < 30:
                frappe.msgprint(
                    _("Cảnh báo: '{0}' hết hạn sau {1} ngày.").format(d.doc_type, days),
                    alert=True, indicator="yellow",
                )


def validate_gate_g01(doc: Document) -> None:
    """Gate G01 (VR-02): 100% mandatory docs Received before To_Be_Installed."""
    if doc.workflow_state in {"Draft", "Pending Doc Verify"}:
        return
    missing = [
        d.doc_type for d in (doc.get("commissioning_documents") or [])
        if d.get("is_mandatory") and d.status not in ("Received", "Waived")
    ]
    if missing:
        frappe.throw(_("VR-02 (Gate G01): Chưa đủ tài liệu bắt buộc. Còn thiếu: {0}").format(", ".join(missing)))


def validate_gate_g03(doc: Document) -> None:
    """Gate G03 (VR-03): 100% baseline tests Pass/N/A before Clinical Release."""
    if doc.workflow_state not in (_STATE_CLINICAL_RELEASE, _STATE_RE_INSPECTION):
        return
    failed = [row.parameter for row in (doc.get("baseline_tests") or []) if row.test_result == "Fail"]
    if failed:
        frappe.throw(_("VR-03 (Gate G03): Các thông số sau không đạt: {0}.").format(", ".join(failed)))


def validate_gate_g05_g06(doc: Document) -> None:
    """Gate G05+G06: no open NCs + board_approver required for Clinical Release."""
    if doc.workflow_state != _STATE_CLINICAL_RELEASE:
        return
    open_nc = frappe.db.count(_DT_NC, {"ref_commissioning": doc.name, "resolution_status": "Open"})
    if open_nc > 0:
        frappe.throw(_("VR-04 (Gate G05): Còn {0} NC chưa đóng.").format(open_nc))
    if not doc.board_approver:
        frappe.throw(_("Gate G06: Cần chọn Người Phê Duyệt Ban Giám Đốc."))


def check_auto_clinical_hold(doc: Document) -> bool:
    """VR-07: Return True if device needs Clinical Hold (Class C/D/Radiation)."""
    high_risk = doc.risk_class in ("C", "D", "Radiation") if doc.risk_class else bool(doc.is_radiation_device)
    if high_risk:
        doc.is_radiation_device = 1
    return high_risk


def log_lifecycle_event(doc: Document, event_type: str, from_status: str, to_status: str, remarks: str = "") -> None:
    """Append immutable lifecycle event to commissioning record."""
    if not hasattr(doc, "lifecycle_events"):
        return
    doc.append("lifecycle_events", {
        "event_type": event_type,
        "from_status": from_status or "",
        "to_status": to_status or "",
        "actor": frappe.session.user,
        "event_timestamp": frappe.utils.now_datetime(),
        "ip_address": getattr(getattr(frappe.local, "request", None), "remote_addr", ""),
        "remarks": remarks,
        "root_record": doc.name,
    })


def handle_commissioning_cancel(doc: Document) -> None:
    """on_cancel: block if Asset already created."""
    if doc.final_asset:
        frappe.throw(_("Không thể hủy vì Tài Sản '{0}' đã được kích hoạt.").format(doc.final_asset))
    if doc.workflow_state not in ("Draft", "Non Conformance", "Return To Vendor"):
        frappe.throw(
            _("Chỉ hủy khi ở Draft, Non Conformance hoặc Return To Vendor. Hiện tại: {0}").format(doc.workflow_state)
        )


def create_erpnext_asset(doc: Document) -> str:
    return create_ac_asset(doc)


def _load_model_data(master_item: str) -> dict:
    if not master_item:
        return {}
    return frappe.db.get_value(
        _DT_MODEL, master_item,
        ["medical_device_class", "risk_classification", "is_pm_required", "pm_interval_days",
         "is_calibration_required", "calibration_interval_days"],
        as_dict=True,
    ) or {}


def _resolve_risk_class(doc: Document, model_data: dict) -> tuple[str, str]:
    radiation_entry = (model_data.get("medical_device_class") or _CLASS_III, "High")
    risk_map = {**_RISK_CLASS_MAP, "Radiation": radiation_entry}
    fallback = (model_data.get("medical_device_class") or "", model_data.get("risk_classification") or "")
    return risk_map.get(doc.risk_class, fallback)


def create_ac_asset(doc: Document) -> str:
    """Create AC Asset on Clinical Release. Returns asset name. BR-04-01."""
    if doc.final_asset:
        return doc.final_asset
    from assetcore.utils.lifecycle import create_lifecycle_event

    model_data = _load_model_data(doc.master_item)
    med_class, risk_clf = _resolve_risk_class(doc, model_data)

    asset = frappe.get_doc({
        "doctype": _DT_ASSET,
        "asset_name": doc.asset_description or doc.master_item or doc.name,
        "device_model": doc.master_item or "",
        "supplier": doc.vendor or "",
        "department": doc.clinical_dept or "",
        "location": doc.installation_location or doc.clinical_dept or "",
        "purchase_date": doc.reception_date or nowdate(),
        "gross_purchase_amount": doc.purchase_price or 0,
        "warranty_expiry_date": doc.warranty_expiry_date or None,
        "manufacturer_sn": doc.vendor_serial_no or "",
        "udi_code": doc.internal_tag_qr or "",
        "commissioning_ref": doc.name,
        "medical_device_class": med_class,
        "risk_classification": risk_clf,
        "lifecycle_status": "Commissioned",
        "commissioning_date": nowdate(),
        "is_pm_required": model_data.get("is_pm_required") or 0,
        "pm_interval_days": model_data.get("pm_interval_days") or 0,
        "is_calibration_required": model_data.get("is_calibration_required") or 0,
        "calibration_interval_days": model_data.get("calibration_interval_days") or 0,
    })
    asset.flags.ignore_mandatory = True
    asset.insert(ignore_permissions=True)
    create_lifecycle_event(
        asset=asset.name, event_type="commissioned", actor=frappe.session.user,
        from_status="", to_status="Commissioned",
        root_doctype=_DT, root_record=doc.name,
        notes=f"Commissioned via IMM-04: {doc.name}",
    )
    return asset.name


# ─── Scheduler ────────────────────────────────────────────────────────────────

def check_commissioning_overdue() -> None:
    """Daily: warn Workshop Manager on commissioning open > 30 days."""
    cutoff = add_days(nowdate(), -30)
    overdue = frappe.get_all(
        _DT,
        filters={
            "docstatus": 0,
            "workflow_state": ("not in", list(_TERMINAL_STATES)),
            "reception_date": ("<", cutoff),
        },
        fields=["name", "vendor", "workflow_state", "reception_date", "commissioned_by"],
    )
    for comm in overdue:
        _send_overdue_alert(comm, date_diff(nowdate(), comm["reception_date"]))


def _send_overdue_alert(comm: dict, days_open: int) -> None:
    users = frappe.db.get_all("Has Role", filters={"role": "Workshop Head", "parenttype": "User"}, fields=["parent"])
    emails = [frappe.db.get_value("User", u.parent, "email") for u in users]
    emails = [e for e in emails if e]
    if not emails:
        return
    frappe.sendmail(
        recipients=emails,
        subject=f"[AssetCore] Phiếu {comm['name']} đã mở {days_open} ngày",
        message=f"<p>Phiếu <b>{comm['name']}</b> đã mở <b>{days_open} ngày</b>. Trạng thái: {comm['workflow_state']}.</p>",
    )


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _get_workflow_transitions(doc_name: str) -> list[dict]:
    user_roles = frappe.get_roles(frappe.session.user)
    current_state = frappe.db.get_value(_DT, doc_name, "workflow_state")
    try:
        workflow = frappe.get_doc("Workflow", "IMM-04 Workflow")
    except frappe.DoesNotExistError:
        return []
    return [
        {"action": t.action, "next_state": t.next_state, "allowed_role": t.allowed}
        for t in workflow.transitions
        if t.state == current_state and t.allowed in user_roles
    ]


def _serialize_baseline_tests(doc) -> list:
    return [
        {
            "idx": row.idx, "parameter": row.parameter,
            "measured_val": row.measured_val, "unit": row.unit,
            "test_result": row.test_result, "fail_note": row.fail_note,
            "is_critical": row.get("is_critical") or 0,
            "measurement_type": row.get("measurement_type") or "",
            "expected_min": row.get("expected_min"),
            "expected_max": row.get("expected_max"),
            "na_applicable": row.get("na_applicable") or 0,
        }
        for row in doc.baseline_tests
    ]


def _serialize_comm_documents(doc) -> list:
    return [
        {
            "idx": row.idx, "doc_type": row.doc_type, "status": row.status,
            "received_date": str(row.received_date or ""),
            "remarks": row.remarks or "",
            "is_mandatory": row.get("is_mandatory") or 0,
            "file_url": row.get("file_url") or "",
            "doc_number": row.get("doc_number") or "",
            "expiry_date": str(row.get("expiry_date") or ""),
        }
        for row in doc.commissioning_documents
    ]


def _serialize_lifecycle_events(doc) -> list:
    return [
        {
            "idx": row.idx,
            "event_type": row.get("event_type") or "",
            "from_status": row.get("from_status") or "",
            "to_status": row.get("to_status") or "",
            "actor": row.get("actor") or "",
            "event_timestamp": str(row.get("event_timestamp") or ""),
            "ip_address": row.get("ip_address") or "",
            "remarks": row.get("remarks") or "",
        }
        for row in (doc.get("lifecycle_events") or [])
    ]


def _serialize_commissioning(doc) -> dict:
    return {
        "name": doc.name,
        "workflow_state": doc.workflow_state,
        "docstatus": doc.docstatus,
        "po_reference": doc.po_reference,
        "master_item": doc.master_item,
        "vendor": doc.vendor,
        "clinical_dept": doc.clinical_dept,
        "expected_installation_date": str(doc.expected_installation_date or ""),
        "installation_date": str(doc.installation_date or ""),
        "reception_date": str(doc.get("reception_date") or ""),
        "risk_class": doc.get("risk_class") or "",
        "board_approver": doc.get("board_approver") or "",
        "clinical_head": doc.get("clinical_head") or "",
        "qa_officer": doc.get("qa_officer") or "",
        "facility_checklist_pass": doc.get("facility_checklist_pass") or 0,
        "overall_inspection_result": doc.get("overall_inspection_result") or "",
        "handover_doc": doc.get("handover_doc") or "",
        "commissioned_by": doc.get("commissioned_by") or "",
        "commissioning_date": str(doc.get("commissioning_date") or ""),
        "vendor_engineer_name": doc.vendor_engineer_name,
        "is_radiation_device": doc.is_radiation_device,
        "doa_incident": doc.doa_incident,
        "vendor_serial_no": doc.vendor_serial_no,
        "internal_tag_qr": doc.internal_tag_qr,
        "custom_moh_code": doc.custom_moh_code,
        "site_photo": doc.site_photo,
        "installation_evidence": doc.installation_evidence,
        "qa_license_doc": doc.qa_license_doc,
        "final_asset": doc.final_asset,
        "amend_reason": doc.amend_reason,
        "amended_from": doc.amended_from,
        "modified": str(doc.modified),
        "owner": doc.owner,
        "is_locked": doc.docstatus == 1,
        "current_user_roles": frappe.get_roles(frappe.session.user),
        "baseline_tests": _serialize_baseline_tests(doc),
        "commissioning_documents": _serialize_comm_documents(doc),
        "lifecycle_events": _serialize_lifecycle_events(doc),
    }


# ─── Query Functions ──────────────────────────────────────────────────────────

def get_form_context(name: str) -> dict:
    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu '{name}'")
    try:
        frappe.has_permission(_DT, ptype="read", doc=name, throw=True)
    except frappe.PermissionError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Bạn không có quyền xem phiếu này")
    result = _serialize_commissioning(doc)
    result["allowed_transitions"] = _get_workflow_transitions(name)
    return result


def list_commissioning(filters: dict, page: int = 1, page_size: int = 20) -> dict:
    try:
        frappe.has_permission(_DT, ptype="read", throw=True)
    except frappe.PermissionError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền truy cập")

    safe_filters = {k: v for k, v in filters.items() if k in _ALLOWED_FILTER_KEYS}
    if "docstatus" not in safe_filters:
        safe_filters["docstatus"] = ("!=", 2)

    page = max(1, int(page))
    page_size = min(max(1, int(page_size)), 100)
    total = frappe.db.count(_DT, safe_filters)
    pg = paginate(total, page, page_size)

    records = frappe.get_all(
        _DT, filters=safe_filters, fields=_LIST_FIELDS,
        order_by=_ORDER_MODIFIED,
        limit_start=pg["offset"], limit_page_length=pg["page_size"],
    )

    item_ids = {r.get("master_item") for r in records if r.get("master_item")}
    vendor_ids = {r.get("vendor") for r in records if r.get("vendor")}
    dept_ids = {r.get("clinical_dept") for r in records if r.get("clinical_dept")}

    item_map = (
        {i.name: i.item_name for i in frappe.get_all("Item", filters={"name": ["in", list(item_ids)]}, fields=["name", "item_name"])}
        if item_ids else {}
    )
    vendor_map = (
        {v.name: v.supplier_name for v in frappe.get_all(_DT_SUPPLIER, filters={"name": ["in", list(vendor_ids)]}, fields=["name", "supplier_name"])}
        if vendor_ids else {}
    )
    dept_map = (
        {d.name: d.department_name for d in frappe.get_all(_DT_DEPT, filters={"name": ["in", list(dept_ids)]}, fields=["name", "department_name"])}
        if dept_ids else {}
    )

    for r in records:
        r["master_item_name"] = item_map.get(r.get("master_item"), r.get("master_item") or "")
        r["vendor_name"] = vendor_map.get(r.get("vendor"), r.get("vendor") or "")
        r["clinical_dept_name"] = dept_map.get(r.get("clinical_dept"), r.get("clinical_dept") or "")

    return {"items": records, "pagination": pg}


def get_barcode_lookup(barcode: str) -> dict:
    barcode = barcode.strip()
    fields = [
        "name", "workflow_state", "docstatus", "master_item", "vendor", "clinical_dept",
        "installation_date", "final_asset", "vendor_serial_no", "internal_tag_qr",
        "is_radiation_device", "doa_incident",
    ]
    record = frappe.db.get_value(_DT, {"internal_tag_qr": barcode}, fields, as_dict=True)
    if not record:
        record = frappe.db.get_value(_DT, {"vendor_serial_no": barcode}, fields, as_dict=True)
    if not record:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy thiết bị với mã '{barcode}'")
    doc = frappe.get_doc(_DT, record.name)
    return {
        "commissioning_id": record.name,
        "workflow_state": record.workflow_state,
        "docstatus": record.docstatus,
        "is_released": record.workflow_state == _STATE_CLINICAL_RELEASE,
        "device": {
            "model": record.master_item, "vendor": record.vendor, "dept": record.clinical_dept,
            "installation_date": str(record.installation_date or ""),
            "vendor_serial": record.vendor_serial_no, "internal_qr": record.internal_tag_qr,
            "is_radiation": bool(record.is_radiation_device), "doa_incident": bool(record.doa_incident),
        },
        "asset_id": record.final_asset,
        "baseline_tests": [
            {"parameter": r.parameter, "measured_val": r.measured_val, "unit": r.unit, "test_result": r.test_result}
            for r in doc.baseline_tests
        ],
    }


def get_dashboard_stats() -> dict:
    try:
        frappe.has_permission(_DT, ptype="read", throw=True)
    except frappe.PermissionError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền truy cập Dashboard")

    states_count = frappe.db.sql(
        "SELECT workflow_state, COUNT(*) AS count FROM `tabAsset Commissioning` "
        "WHERE docstatus != 2 GROUP BY workflow_state ORDER BY count DESC",
        as_dict=True,
    )
    state_map = {s.workflow_state: s.count for s in states_count}
    first_day = get_first_day(nowdate())
    overdue_cutoff = add_days(nowdate(), -30)

    return {
        "kpis": {
            "pending_count": sum(v for k, v in state_map.items() if k not in _TERMINAL_STATES),
            "hold_count": state_map.get("Clinical Hold", 0),
            "open_nc_count": frappe.db.count(_DT_NC, {"resolution_status": "Open", "docstatus": ("!=", 2)}),
            "released_this_month": frappe.db.count(_DT, {
                "workflow_state": _STATE_CLINICAL_RELEASE, "docstatus": 1,
                "modified": (">=", str(first_day)),
            }),
            "overdue_sla": frappe.db.count(_DT, {
                "expected_installation_date": ("<", str(overdue_cutoff)),
                "workflow_state": ("not in", list(_TERMINAL_STATES)),
                "docstatus": ("!=", 2),
            }),
        },
        "states_breakdown": states_count,
        "recent_list": frappe.get_all(
            _DT, filters={"docstatus": ("!=", 2)},
            fields=["name", "workflow_state", "master_item", "vendor", "clinical_dept",
                    "expected_installation_date", "modified"],
            order_by=_ORDER_MODIFIED, limit_page_length=10,
        ),
    }


def generate_qr_label(name: str) -> dict:
    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu '{name}'")
    try:
        frappe.has_permission(_DT, ptype="read", doc=name, throw=True)
    except frappe.PermissionError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền truy cập")
    if not doc.internal_tag_qr:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Phiếu chưa có mã QR nội bộ")
    return {
        "qr_value": doc.internal_tag_qr,
        "label": {
            "title": "ASSETCORE — NHÃN THIẾT BỊ",
            "commissioning_id": doc.name,
            "internal_qr": doc.internal_tag_qr,
            "vendor_serial": doc.vendor_serial_no or "N/A",
            "model": doc.master_item or "N/A",
            "vendor": doc.vendor or "N/A",
            "dept": doc.clinical_dept or "N/A",
            "moh_code": doc.custom_moh_code or "N/A",
            "installation_date": str(doc.installation_date or "Chưa lắp đặt"),
            "status": doc.workflow_state,
            "asset_id": doc.final_asset or "Chưa có",
            "print_date": str(nowdate()),
        },
        "scan_url": f"/app/asset-commissioning/{doc.name}",
        "docs_url": f"/documents/asset/{doc.final_asset}" if doc.final_asset else None,
    }


def search_link(doctype: str, query: str = "", page_length: int = 10) -> list:
    if doctype not in _ALLOWED_SEARCH_DOCTYPES:
        raise ServiceError(ErrorCode.FORBIDDEN, f"DocType '{doctype}' không được phép tìm kiếm")
    config = _ALLOWED_SEARCH_DOCTYPES[doctype]
    if config.get("optional") and not frappe.db.exists("DocType", doctype):
        return []
    filters = dict(config["filters"])
    or_filters = []
    if query:
        q = f"%{query}%"
        for field in config["search_fields"]:
            or_filters.append([doctype, field, "like", q])
    fields = [*{*config["extra_fields"], "name"}]
    results = frappe.db.get_all(
        doctype, filters=filters, or_filters=or_filters or None,
        fields=fields, limit=int(page_length), order_by=_ORDER_MODIFIED,
    )
    label_field = config["label_field"]
    items = []
    for row in results:
        value = row.get("name") or row.get(label_field, "")
        label = row.get(label_field) or value
        desc_parts = [str(row[f]) for f in config["extra_fields"] if f != label_field and row.get(f)]
        items.append({"value": value, "label": label, "description": " | ".join(desc_parts)})
    return items


def get_po_details(po_name: str) -> dict:
    if not frappe.db.exists("DocType", _DT_PO):
        return {
            "po_name": po_name, "supplier": "", "supplier_name": "",
            "transaction_date": "", "items": [], "unavailable": True,
            "note": "Purchase Order DocType không có. po_reference là soft reference.",
        }
    if not frappe.db.exists(_DT_PO, po_name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy PO '{po_name}'")
    po = frappe.get_doc(_DT_PO, po_name)
    ac_supplier = frappe.db.get_value(_DT_SUPPLIER, {"supplier_name": po.supplier_name}, "name") or ""
    return {
        "po_name": po.name, "supplier": ac_supplier,
        "supplier_name": po.supplier_name,
        "transaction_date": str(po.transaction_date),
        "items": [{"item_code": i.item_code, "item_name": i.item_name, "qty": i.qty} for i in po.items],
    }


# ─── Command Functions ────────────────────────────────────────────────────────

def transition_state(name: str, action: str) -> dict:
    if not frappe.db.exists(_DT, name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu '{name}'")
    try:
        frappe.has_permission(_DT, ptype="write", doc=name, throw=True)
    except frappe.PermissionError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Bạn không có quyền chỉnh sửa phiếu này")
    allowed = _get_workflow_transitions(name)
    allowed_actions = [t["action"] for t in allowed]
    if action not in allowed_actions:
        current_state = frappe.db.get_value(_DT, name, "workflow_state")
        raise ServiceError(
            ErrorCode.INVALID_PARAMS,
            f"Hành động '{action}' không hợp lệ từ '{current_state}'. Cho phép: {allowed_actions}",
        )
    doc = frappe.get_doc(_DT, name)
    frappe.model.workflow.apply_workflow(doc, action)
    doc.save(ignore_permissions=False)
    return {"name": name, "action_applied": action, "new_state": doc.workflow_state, "docstatus": doc.docstatus}


def submit_commissioning(name: str) -> dict:
    if not frappe.db.exists(_DT, name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu '{name}'")
    if not _SUBMIT_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        raise ServiceError(ErrorCode.FORBIDDEN, "Chỉ VP Block2 hoặc Workshop Head mới được Submit")
    doc = frappe.get_doc(_DT, name)
    if doc.docstatus == 1:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Phiếu đã được Submit trước đó")
    if doc.docstatus == 2:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Phiếu đã bị Cancel")
    if doc.workflow_state != _STATE_CLINICAL_RELEASE:
        raise ServiceError(
            ErrorCode.INVALID_PARAMS,
            f"Phiếu phải ở '{_STATE_CLINICAL_RELEASE}'. Hiện tại: {doc.workflow_state}",
        )
    doc.submit()
    return {"name": name, "docstatus": 1, "final_asset": doc.final_asset}


def _apply_baseline_updates(doc, rows: list) -> None:
    bmap = {r.get("idx"): r for r in rows if r.get("idx") is not None}
    for row in doc.baseline_tests:
        upd = bmap.get(row.idx)
        if upd is None:
            continue
        if "measured_val" in upd:
            row.measured_val = upd["measured_val"]
        if "test_result" in upd:
            row.test_result = upd["test_result"]
        if "fail_note" in upd:
            row.fail_note = upd["fail_note"]


def _apply_document_updates(doc, rows: list) -> None:
    dmap = {r.get("idx"): r for r in rows if r.get("idx") is not None}
    for row in doc.commissioning_documents:
        upd = dmap.get(row.idx)
        if upd is None:
            continue
        if "status" in upd:
            row.status = upd["status"]
        if "received_date" in upd:
            row.received_date = upd["received_date"] or None
        if "remarks" in upd:
            row.remarks = upd["remarks"]


def save_commissioning(name: str, fields: dict) -> dict:
    if not frappe.db.exists(_DT, name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu '{name}'")
    try:
        frappe.has_permission(_DT, ptype="write", doc=name, throw=True)
    except frappe.PermissionError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Bạn không có quyền chỉnh sửa phiếu này")
    doc = frappe.get_doc(_DT, name)
    if doc.docstatus == 1:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Phiếu đã Submit, không thể chỉnh sửa")

    for key, value in fields.items():
        if key in _EDITABLE_FIELDS:
            doc.set(key, value)

    if isinstance(fields.get("baseline_tests"), list):
        _apply_baseline_updates(doc, fields["baseline_tests"])

    if isinstance(fields.get("commissioning_documents"), list):
        _apply_document_updates(doc, fields["commissioning_documents"])

    doc.save(ignore_permissions=False)
    return {"name": doc.name, "workflow_state": doc.workflow_state}


def create_commissioning(data: dict) -> dict:
    try:
        frappe.has_permission(_DT, ptype="create", throw=True)
    except frappe.PermissionError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Bạn không có quyền tạo phiếu mới")

    missing = [f for f in _REQUIRED_FIELDS if not data.get(f)]
    if missing:
        raise ServiceError(ErrorCode.INVALID_PARAMS, f"Thiếu trường bắt buộc: {', '.join(missing)}")

    payload: dict = {"doctype": _DT}
    for field in _CREATE_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if field in _DATE_FIELDS and not value:
            value = None
        payload[field] = value

    doc = frappe.get_doc(payload)
    for row in data.get("commissioning_documents") or []:
        doc.append("commissioning_documents", {
            "doc_type": row.get("doc_type", ""), "is_mandatory": row.get("is_mandatory", 0),
            "status": row.get("status", "Pending"), "received_date": row.get("received_date") or None,
            "remarks": row.get("remarks", ""),
        })
    for row in data.get("baseline_tests") or []:
        doc.append("baseline_tests", {
            "parameter": row.get("parameter", ""), "is_critical": row.get("is_critical", 0),
            "measurement_type": row.get("measurement_type", ""), "measured_val": row.get("measured_val", ""),
            "expected_min": row.get("expected_min"), "expected_max": row.get("expected_max"),
            "unit": row.get("unit", ""), "test_result": row.get("test_result", "N/A"),
            "na_applicable": row.get("na_applicable", 0), "fail_note": row.get("fail_note", ""),
        })
    doc.insert(ignore_permissions=False)
    return {"name": doc.name, "workflow_state": doc.workflow_state}


# ─── NC Functions ─────────────────────────────────────────────────────────────

def report_nonconformance(commissioning_name: str, nc_data: dict) -> dict:
    doc = frappe.get_doc({
        "doctype": _DT_NC, "ref_commissioning": commissioning_name,
        "nc_type": nc_data.get("nc_type", "Other"),
        "severity": nc_data.get("severity", "Minor"),
        "description": nc_data.get("description", ""),
        "resolution_status": "Open",
    })
    doc.insert(ignore_permissions=True)
    return {"name": doc.name, "nc_type": doc.nc_type, "severity": doc.severity}


def list_non_conformances(commissioning: str) -> list:
    if not frappe.db.exists(_DT, commissioning):
        raise ServiceError(ErrorCode.NOT_FOUND, "Phiếu Commissioning không tồn tại")
    return frappe.get_all(
        _DT_NC, filters={"ref_commissioning": commissioning},
        fields=["name", "nc_type", "severity", "description", "resolution_status",
                "resolution_note", "root_cause", "closed_by", "closed_date"],
        order_by="creation desc",
    )


def close_nonconformance(nc_name: str, root_cause: str, corrective_action: str) -> dict:
    if not root_cause or not corrective_action:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "root_cause và corrective_action là bắt buộc")
    nc = NonConformanceRepo.get(nc_name)
    if not nc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy NC: {nc_name}")
    nc.resolution_status = "Closed"
    nc.root_cause = root_cause
    nc.corrective_action = corrective_action
    nc.closed_by = frappe.session.user
    nc.closed_date = nowdate()
    nc.save(ignore_permissions=True)
    return {"name": nc_name, "status": "Closed"}


def report_doa(commissioning: str, description: str) -> dict:
    nc = frappe.get_doc({
        "doctype": _DT_NC, "ref_commissioning": commissioning,
        "nc_type": "DOA", "severity": "Critical",
        "description": description, "resolution_status": "Open",
    })
    nc.insert(ignore_permissions=True)
    return {"nc_name": nc.name, "commissioning": commissioning, "severity": "Critical"}


# ─── Identification Functions ─────────────────────────────────────────────────

def assign_identification(name: str, vendor_serial_no: str = "", internal_tag_qr: str = "", custom_moh_code: str = "") -> dict:
    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")
    if doc.workflow_state != "Identification":
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Chỉ có thể gán định danh khi ở trạng thái Identification")
    if vendor_serial_no:
        dup = frappe.db.exists(_DT, {"vendor_serial_no": vendor_serial_no, "name": ("!=", name), "docstatus": ("!=", 2)})
        if dup:
            raise ServiceError(ErrorCode.DUPLICATE, f"VR-01: Serial '{vendor_serial_no}' đã được gán cho {dup}")
    doc.vendor_serial_no = vendor_serial_no or doc.vendor_serial_no
    doc.internal_tag_qr = internal_tag_qr or doc.internal_tag_qr
    doc.custom_moh_code = custom_moh_code or doc.custom_moh_code
    doc.save(ignore_permissions=True)
    return {"name": doc.name, "vendor_serial_no": doc.vendor_serial_no, "internal_tag_qr": doc.internal_tag_qr}


def check_sn_unique(vendor_sn: str, exclude_name: str = "") -> dict:
    if not vendor_sn:
        return {"is_unique": True}
    filters: dict = {"vendor_serial_no": vendor_sn, "docstatus": ("!=", 2)}
    if exclude_name:
        filters["name"] = ("!=", exclude_name)
    existing = frappe.db.get_value(_DT, filters, ["name", "master_item"], as_dict=True)
    if existing:
        return {"is_unique": False, "existing_commissioning": existing.name, "item": existing.master_item}
    return {"is_unique": True}


def submit_baseline_checklist(name: str, results: list) -> dict:
    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")
    if doc.workflow_state != _STATE_INITIAL_INSPECTION:
        raise ServiceError(ErrorCode.INVALID_PARAMS, f"Chỉ submit checklist khi ở {_STATE_INITIAL_INSPECTION}")
    result_map = {r.get("parameter"): r for r in results}
    for row in doc.baseline_tests or []:
        if row.parameter in result_map:
            r = result_map[row.parameter]
            row.measured_val = r.get("measured_val", "")
            row.test_result = r.get("test_result", "")
            row.fail_note = r.get("fail_note", "")
    fails = [r.parameter for r in (doc.baseline_tests or []) if r.test_result == "Fail"]
    if fails:
        raise ServiceError(ErrorCode.VALIDATION, f"BR-04-04: Thông số sau không đạt: {', '.join(fails)}")
    is_high_risk = check_auto_clinical_hold(doc)
    doc.overall_inspection_result = "Pass"
    doc.save(ignore_permissions=True)
    return {"name": doc.name, "overall_result": "Pass", "clinical_hold_required": is_high_risk}


def clear_clinical_hold(name: str, license_no: str = "") -> dict:
    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")
    if doc.workflow_state != "Clinical Hold":
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Commissioning không ở trạng thái Clinical Hold")
    if not doc.qa_license_doc and not license_no:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "BR-04-05: Phải upload giấy phép BYT trước")
    if license_no:
        doc.radiation_license_no = license_no
    doc.save(ignore_permissions=True)
    return {"name": doc.name, "license_no": doc.radiation_license_no}


def upload_document(commissioning: str, doc_index: int, file_url: str = "", expiry_date: str = "", doc_number: str = "") -> dict:
    doc = CommissioningRepo.get(commissioning)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {commissioning}")
    idx = int(doc_index)
    for row in doc.commissioning_documents:
        if row.idx == idx:
            row.status = "Received"
            if file_url:
                row.file_url = file_url
            if expiry_date:
                row.expiry_date = expiry_date
            if doc_number:
                row.doc_number = doc_number
            row.uploaded_by = frappe.session.user
            row.uploaded_at = frappe.utils.now_datetime()
            break
    doc.save(ignore_permissions=True)
    all_mandatory = all(r.status in ("Received", "Waived") for r in doc.commissioning_documents if r.is_mandatory)
    return {"commissioning": commissioning, "doc_index": idx, "all_mandatory_received": all_mandatory}


def approve_clinical_release(commissioning: str, board_approver: str, approval_remarks: str = "") -> dict:
    doc = CommissioningRepo.get(commissioning)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {commissioning}")
    if doc.workflow_state != _STATE_CLINICAL_RELEASE:
        raise ServiceError(ErrorCode.INVALID_PARAMS, f"Phiếu phải ở {_STATE_CLINICAL_RELEASE}. Hiện tại: {doc.workflow_state}")
    if not board_approver:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "board_approver là bắt buộc")
    open_nc = frappe.db.count(_DT_NC, {"ref_commissioning": commissioning, "resolution_status": "Open"})
    if open_nc > 0:
        raise ServiceError(ErrorCode.INVALID_PARAMS, f"VR-04: Còn {open_nc} NC chưa đóng")
    doc.board_approver = board_approver
    if approval_remarks:
        doc.notes = (doc.notes or "") + f"\n[Board Approval] {approval_remarks}"
    doc.save(ignore_permissions=True)
    doc.submit()
    return {
        "commissioning": commissioning,
        "new_status": _STATE_CLINICAL_RELEASE,
        "asset_ref": doc.final_asset,
        "commissioning_date": str(doc.commissioning_date or nowdate()),
        "device_record_queued": True,
    }


def delete_commissioning(name: str) -> dict:
    """Xóa phiếu Commissioning ở trạng thái Bản nháp (docstatus=0)."""
    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu: {name}")
    if doc.docstatus != 0:
        raise ServiceError(ErrorCode.FORBIDDEN, "Chỉ có thể xóa phiếu Bản nháp (docstatus = 0)")
    frappe.delete_doc(_DT, name, ignore_permissions=False)
    return {"deleted": name}


def cancel_commissioning(name: str) -> dict:
    """Hủy phiếu Commissioning đã Submit (docstatus 1 → 2). Chỉ VP Block2 / Workshop Head."""
    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu: {name}")
    if doc.docstatus != 1:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Chỉ có thể hủy phiếu đã Submit (docstatus = 1)")
    if doc.final_asset:
        raise ServiceError(
            ErrorCode.FORBIDDEN,
            f"Không thể hủy vì Tài sản '{doc.final_asset}' đã được kích hoạt trong hệ thống",
        )
    _allowed = _SUBMIT_ROLES | {"System Manager", "Administrator"}
    if not any(r in _allowed for r in frappe.get_roles()):
        raise ServiceError(ErrorCode.FORBIDDEN, "Chỉ VP Block2 hoặc Workshop Head mới được phép hủy phiếu")
    doc.cancel()
    frappe.db.commit()
    log_lifecycle_event(doc, "Cancelled", doc.workflow_state, "Cancelled",
                        f"Phiếu bị hủy bởi {frappe.session.user}")
    return {"name": name, "docstatus": 2, "cancelled_by": frappe.session.user}


def generate_handover_pdf(name: str) -> dict:
    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")
    if doc.workflow_state != _STATE_CLINICAL_RELEASE:
        raise ServiceError(ErrorCode.INVALID_PARAMS, f"Chỉ xuất biên bản khi đã {_STATE_CLINICAL_RELEASE}")
    pdf_url = (
        f"/api/method/frappe.utils.pdf.get_pdf"
        f"?doctype=Asset+Commissioning&name={frappe.utils.quote(name)}&format=Biên+bản+Bàn+giao"
    )
    return {"pdf_url": pdf_url, "name": name}
