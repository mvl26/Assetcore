# Copyright (c) 2026, AssetCore Team
"""Business logic for IMM-04 Asset Commissioning — Tier 2 service layer."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, get_first_day, getdate, nowdate

from assetcore.repositories.commissioning_repo import CommissioningRepo, NonConformanceRepo
from assetcore.services.shared import (
    ErrorCode,
    ServiceError,
    assert_distinct_signers,
    assert_not_self_submitter,
)
from assetcore.services.shared import rbac
from assetcore.utils.notify import MSG, nthrow, nthrow_in_hook
from assetcore.utils.pagination import paginate

# AUTH-05 — 4-eyes / Separation-of-Duties signer fields on Asset Commissioning.
# A single user cannot occupy more than one of these roles on the same phiếu.
_SIGNER_FIELDS = (
    "clinical_head",     # Trưởng khoa lâm sàng
    "qa_officer",        # QA/QC officer
    "board_approver",    # Ban Giám đốc
    "pending_approver",  # current approver in pipeline
    "owner",             # phiếu submitter
)

# ─── Constants ────────────────────────────────────────────────────────────────

_DT = "Asset Commissioning"
_DT_NC = "Asset QA Non Conformance"
_DT_ASSET = "AC Asset"
_DT_MODEL = "IMM Device Model"
_DT_SUPPLIER = "AC Supplier"
_DT_DEPT = "AC Department"
_DT_PO = "AC Purchase"

_STATE_CLINICAL_RELEASE = "Clinical Release"
_STATE_INITIAL_INSPECTION = "Initial Inspection"
_STATE_RE_INSPECTION = "Re Inspection"
_TERMINAL_STATES = frozenset({_STATE_CLINICAL_RELEASE, "Return To Vendor"})

# ─── Overdue SLA single-source-of-truth (BR-04-10) ────────────────────────────
# MỘT date-anchor + MỘT ngưỡng dùng chung cho cả 3 call-site (scheduler alert,
# dashboard KPI, list drill `overdue=1`) — chống divergence reception_date vs
# expected_installation_date. Anchor CHỐT = reception_date (Core Doc KPI-04-01
# §I.5 + BR-04-10: "trong OVERDUE_DAYS ngày từ reception_date") — ngày nhận hàng
# auto-set today() khi tạo phiếu, là đồng hồ SLA nghiệm thu (Draft → Clinical
# Release). KHÔNG dùng expected_installation_date làm anchor (ngày-hẹn kế hoạch,
# KHÔNG phải mốc bắt đầu SLA). KHÔNG inline literal threshold ngoài OVERDUE_DAYS.
OVERDUE_DAYS = 30
_OVERDUE_ANCHOR = "reception_date"


def overdue_commissioning_filter(today: str | None = None) -> dict:
    """SoT filter cho 'Phiếu nghiệm thu quá hạn SLA' (BR-04-10).

    Trả filter dict drillable dùng chung bởi scheduler alert + dashboard KPI +
    list `overdue=1`. Quá hạn ⟺ anchor < (today - OVERDUE_DAYS), phiếu chưa ở
    terminal state (Clinical Release / Return To Vendor) và chưa bị Cancel.

    Args:
        today: ngày tham chiếu (ISO yyyy-mm-dd); mặc định nowdate() — cho phép
               test/scheduler bơm 1 mốc thời gian cố định cho cả 3 call-site.
    """
    cutoff = add_days(today or nowdate(), -OVERDUE_DAYS)
    return {
        _OVERDUE_ANCHOR: ("<", str(cutoff)),
        "workflow_state": ("not in", list(_TERMINAL_STATES)),
        "docstatus": ("!=", 2),
    }

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
    # Cho phép sửa các trường định danh (chỉ khi docstatus=0 — đã chặn ở save_commissioning):
    "master_item", "vendor", "clinical_dept",
    "expected_installation_date", "vendor_serial_no",
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
        "search_fields": ["name", "supplier", "invoice_no"],
        "filters": {},
        "extra_fields": ["supplier", "invoice_no", "purchase_date"],
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
        "dynamic_filter_fields": {"is_group", "parent_department"},
    },
    "AC Location": {
        "label_field": "location_name",
        "search_fields": ["name", "location_name", "location_code"],
        "filters": {},
        "extra_fields": ["location_name", "location_code", "clinical_area_type"],
        "dynamic_filter_fields": {"is_group", "parent_location", "clinical_area_type"},
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
    "PM Checklist Template": {
        "label_field": "template_name",
        "search_fields": ["name", "template_name", "asset_category", "pm_type"],
        "filters": {},
        "extra_fields": ["template_name", "asset_category", "pm_type", "version"],
    },
    "AC UOM": {
        "label_field": "uom_name",
        "search_fields": ["name", "uom_name", "symbol"],
        "filters": {"is_active": 1},
        "extra_fields": ["uom_name", "symbol"],
    },
    "AC Spare Part": {
        "label_field": "part_name",
        "search_fields": ["name", "part_name", "part_code"],
        "filters": {},
        "extra_fields": ["part_name", "part_code"],
    },
    "AC Spare Part Category": {
        "label_field": "name",
        "search_fields": ["name"],
        "filters": {},
        "extra_fields": [],
        "optional": True,
    },
    "AC Vendor": {
        "label_field": "name",
        "search_fields": ["name"],
        "filters": {},
        "extra_fields": [],
        "optional": True,
    },
    "IMM Calibration Schedule": {
        "label_field": "name",
        # 'asset' is the real Link→AC Asset column; 'asset_ref' does NOT exist
        # on this DocType and previously raised OperationalError 1054.
        "search_fields": ["name", "asset"],
        "filters": {},
        "extra_fields": ["asset"],
        "optional": True,
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
        nthrow_in_hook(
            MSG.IMM04_DUP_SERIAL,
            serial=doc.vendor_serial_no,
            ref=_("Tài Sản {0}").format(existing_asset),
        )
    existing_comm = frappe.db.get_value(
        _DT, {"vendor_serial_no": doc.vendor_serial_no, "name": ("!=", doc.name or ""), "docstatus": ("!=", 2)}, "name",
    )
    if existing_comm:
        nthrow_in_hook(
            MSG.IMM04_DUP_SERIAL,
            serial=doc.vendor_serial_no,
            ref=_("Phiếu Nghiệm Thu {0}").format(existing_comm),
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
            filters={"root_record": doc.name, "root_doctype": _DT},
            fields=["name", "timestamp", "actor", "event_type"],
        )
    }
    for row in doc.get("lifecycle_events") or []:
        if row.name and row.name in existing:
            orig = existing[row.name]
            if row.actor != orig["actor"] or row.event_type != orig["event_type"]:
                nthrow_in_hook(MSG.IMM04_LIFECYCLE_LOCKED)


def _validate_document_expiry(doc: Document) -> None:
    today = getdate()
    for d in doc.get("commissioning_documents") or []:
        expiry = d.get("expiry_date")
        if expiry and d.get("status") == "Received":
            days = date_diff(expiry, today)
            if days < 0:
                nthrow_in_hook(MSG.IMM04_DOC_EXPIRED, doc_type=d.doc_type, expiry=expiry)
            elif days < 30:
                frappe.msgprint(
                    _("Cảnh báo: '{0}' hết hạn sau {1} ngày.").format(d.doc_type, days),
                    alert=True, indicator="yellow",
                )


def validate_gate_g01(doc: Document) -> None:
    """Gate G01 (VR-02): mandatory docs Received before To_Be_Installed.

    Logic:
    - Bỏ qua khi insert / Draft / Pending Doc Verify (đang soạn).
    - Bỏ qua khi user MARK 'documents_incomplete=1' + có note giải thích → phiếu
      vẫn duyệt được, hồ sơ bổ sung sau (yêu cầu nghiệp vụ: thực tế nhiều thiết bị
      tới mà CO/CQ chậm — không thể block toàn bộ quy trình lắp đặt).
    - Còn lại: thiếu hồ sơ bắt buộc → throw block transition.
    """
    if not doc.workflow_state or doc.workflow_state in {"Draft", "Pending Doc Verify"}:
        return

    missing = [
        d.doc_type for d in (doc.get("commissioning_documents") or [])
        if d.get("is_mandatory") and d.status not in ("Received", "Waived")
    ]
    if not missing:
        return

    # User xác nhận thiếu + có note → cho phép duyệt, log warning
    if doc.get("documents_incomplete") and (doc.get("documents_incomplete_note") or "").strip():
        frappe.msgprint(
            _("⚠ Phiếu duyệt với hồ sơ thiếu: {0}. Ghi chú: {1}").format(
                ", ".join(missing), doc.documents_incomplete_note,
            ),
            alert=True, indicator="orange",
        )
        return

    nthrow_in_hook(MSG.IMM04_DOCS_INCOMPLETE, missing=", ".join(missing))


def validate_gate_g03(doc: Document) -> None:
    """Gate G03 (VR-03): 100% baseline tests Pass/N/A before Clinical Release."""
    if doc.workflow_state not in (_STATE_CLINICAL_RELEASE, _STATE_RE_INSPECTION):
        return
    failed = [row.parameter for row in (doc.get("baseline_tests") or []) if row.test_result == "Fail"]
    if failed:
        nthrow_in_hook(MSG.IMM04_BASELINE_FAILED, failed=", ".join(failed))


def validate_gate_g05_g06(doc: Document) -> None:
    """Gate G05+G06: no open NCs + board_approver required for Clinical Release."""
    if doc.workflow_state != _STATE_CLINICAL_RELEASE:
        return
    open_nc = frappe.db.count(_DT_NC, {"ref_commissioning": doc.name, "resolution_status": "Open"})
    if open_nc > 0:
        nthrow_in_hook(MSG.IMM04_OPEN_NC, count=open_nc)
    if not doc.board_approver:
        nthrow_in_hook(MSG.IMM04_BOARD_APPROVER_REQUIRED)


def check_auto_clinical_hold(doc: Document) -> bool:
    """VR-07: Return True if device needs Clinical Hold (Class C/D/Radiation)."""
    high_risk = doc.risk_class in ("C", "D", "Radiation") if doc.risk_class else bool(doc.is_radiation_device)
    if high_risk:
        doc.is_radiation_device = 1
    return high_risk


def log_lifecycle_event(doc: Document, event_type: str, from_status: str, to_status: str, remarks: str = "") -> None:
    """Persist a lifecycle/audit event for the commissioning record.

    RC-05 fix: the Asset Commissioning DocType does NOT declare a `lifecycle_events`
    child table (only a Section Break exists in JSON), so any `doc.append(...)`
    silently no-ops and the "Lịch sử phiếu" tab stays empty. Persist to the canonical
    `IMM Audit Trail` (SHA-256 chained) so the timeline can read it back. The asset
    field is left blank pre-release and populated post-release via `final_asset`.
    Best-effort: never block a state transition because audit logging failed.
    """
    from assetcore.utils.lifecycle import log_audit_event as _log_audit
    try:
        _log_audit(
            asset=doc.get("final_asset") or "",
            event_type="State Change",
            actor=frappe.session.user,
            ref_doctype=_DT,
            ref_name=doc.name,
            change_summary=(remarks or event_type),
            from_status=from_status or "",
            to_status=to_status or "",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-04 audit log failed: {doc.name}")

    # Best-effort append to child table (works only if DocType ever declares it)
    if not hasattr(doc, "lifecycle_events"):
        return
    try:
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
    except Exception:
        pass


def _stamp_commissioning_date(doc: Document) -> None:
    """SoT (BR-04-11): set commissioning_date = ngày vào Clinical Release.

    Idempotent — chỉ ghi khi field còn NULL (KHÔNG ghi đè ngày bàn giao đã có).
    Mutate doc in-memory; caller chịu trách nhiệm persist (doc.save / doc.submit
    của chính write-path). KHÔNG @whitelist (internal). Đây là điểm hội tụ logic
    của cả 3 release path (transition_state / submit_commissioning /
    approve_clinical_release) → 1 chỗ định nghĩa, mỗi path gọi 1 lần SAU khi
    workflow_state đã thành Clinical Release.
    """
    if doc.workflow_state == _STATE_CLINICAL_RELEASE and not doc.get("commissioning_date"):
        doc.commissioning_date = nowdate()


def handle_commissioning_cancel(doc: Document) -> None:
    """on_cancel: block if Asset already created."""
    if doc.final_asset:
        nthrow_in_hook(MSG.IMM04_CANCEL_ASSET_ACTIVE, asset=doc.final_asset)
    if doc.workflow_state not in ("Draft", "Non Conformance", "Return To Vendor"):
        nthrow_in_hook(
            MSG.IMM04_BAD_STATE,
            state=doc.workflow_state,
            expected="Draft, Non Conformance, Return To Vendor",
        )


def _load_model_data(master_item: str) -> dict:
    """Load Model (Tier 2) data + inherit Category (Tier 1) financial defaults.

    Chain: AC Asset Category → IMM Device Model → (merged into result).
    Model fields win over Category for interval overrides;
    Category fills financial defaults only (no Model override).
    """
    if not master_item:
        return {}
    model = frappe.db.get_value(
        _DT_MODEL, master_item,
        ["asset_category", "medical_device_class", "risk_classification",
         "is_pm_required", "pm_interval_days",
         "is_calibration_required", "calibration_interval_days",
         "expected_lifespan_years"],
        as_dict=True,
    ) or {}
    if not model:
        return {}

    cat_name = model.get("asset_category")
    if cat_name:
        cat = frappe.db.get_value(
            "AC Asset Category", cat_name,
            ["default_depreciation_method", "total_depreciation_months",
             "depreciation_frequency", "default_residual_value_pct",
             "default_pm_required", "default_pm_interval_days",
             "default_calibration_required", "default_calibration_interval_days"],
            as_dict=True,
        ) or {}
        # Financial defaults come only from Category (single source of truth)
        model["_cat_depreciation_method"]     = cat.get("default_depreciation_method") or ""
        model["_cat_total_months"]            = int(cat.get("total_depreciation_months") or 0)
        model["_cat_depreciation_frequency"]  = cat.get("depreciation_frequency") or "Monthly"
        model["_cat_residual_value_pct"]      = cat.get("default_residual_value_pct") or 0
        # PM/Calib: Model wins; fall back to Category if Model blank
        if not model.get("is_pm_required"):
            model["is_pm_required"] = cat.get("default_pm_required") or 0
            model["pm_interval_days"] = model.get("pm_interval_days") or cat.get("default_pm_interval_days") or 0
        if not model.get("is_calibration_required"):
            model["is_calibration_required"] = cat.get("default_calibration_required") or 0
            model["calibration_interval_days"] = model.get("calibration_interval_days") or cat.get("default_calibration_interval_days") or 0

    return model


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

    # BUG-009 fallback: nếu QR vẫn trống tại thời điểm mint, sinh ngay tại đây.
    # Đảm bảo AC Asset luôn có udi_code khi commissioning hoàn thành.
    if not doc.internal_tag_qr:
        try:
            result = generate_internal_qr(doc.name)
            doc.internal_tag_qr = result.get("internal_tag_qr") or doc.internal_tag_qr
        except ServiceError:
            # Không block mint nếu sinh QR thất bại — log và tiếp tục.
            frappe.log_error(
                f"QR fallback generation failed for {doc.name}",
                "IMM-04 QR Fallback",
            )

    model_data = _load_model_data(doc.master_item)
    med_class, risk_clf = _resolve_risk_class(doc, model_data)

    # Compute residual value from Category default pct (if any)
    purchase_amount = float(doc.purchase_price or 0)
    residual_pct = float(model_data.get("_cat_residual_value_pct") or 0)
    residual_value = purchase_amount * residual_pct / 100.0 if residual_pct else 0

    # Convert total months → useful_life_years (for existing Asset field)
    total_months = int(model_data.get("_cat_total_months") or 0)
    useful_years = (total_months // 12) if total_months else int(model_data.get("expected_lifespan_years") or 0)

    asset = frappe.get_doc({
        "doctype": _DT_ASSET,
        "asset_name": doc.asset_description or doc.master_item or doc.name,
        "device_model": doc.master_item or "",
        # Tier 1 inheritance (canonical depreciation rules come from Category)
        "asset_category": model_data.get("asset_category") or "",
        "depreciation_method": model_data.get("_cat_depreciation_method") or "",
        "total_depreciation_months": total_months,
        "depreciation_frequency": model_data.get("_cat_depreciation_frequency") or "Monthly",
        "depreciation_start_date": nowdate(),
        "useful_life_years": useful_years,
        "residual_value": residual_value,
        # Operational fields
        "supplier": doc.vendor or "",
        "department": doc.clinical_dept or "",
        "location": doc.installation_location or doc.clinical_dept or "",
        "purchase_date": doc.reception_date or nowdate(),
        "in_service_date": nowdate(),
        "gross_purchase_amount": purchase_amount,
        "warranty_expiry_date": doc.warranty_expiry_date or None,
        "manufacturer_sn": doc.vendor_serial_no or "",
        "udi_code": doc.internal_tag_qr or "",
        "commissioning_ref": doc.name,
        "medical_device_class": med_class,
        "risk_classification": risk_clf,
        "commissioning_date": nowdate(),
        "is_pm_required": model_data.get("is_pm_required") or 0,
        "pm_interval_days": model_data.get("pm_interval_days") or 0,
        "is_calibration_required": model_data.get("is_calibration_required") or 0,
        "calibration_interval_days": model_data.get("calibration_interval_days") or 0,
    })
    asset.flags.ignore_mandatory = True
    asset.insert(ignore_permissions=True)
    # Apply workflow transition Draft → Commissioned
    try:
        from frappe.model.workflow import apply_workflow
        apply_workflow(asset, "Commission")
    except Exception:
        frappe.db.set_value(_DT_ASSET, asset.name, "lifecycle_status", "Commissioned")
    create_lifecycle_event(
        asset=asset.name, event_type="commissioned", actor=frappe.session.user,
        from_status="", to_status="Commissioned",
        root_doctype=_DT, root_record=doc.name,
        notes=f"Commissioned via IMM-04: {doc.name}",
    )

    try:
        transferred = _transfer_commissioning_documents_to_asset(doc, asset.name)
        if transferred:
            frappe.logger().info(
                f"Transferred {transferred} documents from {doc.name} → Asset {asset.name}"
            )
    except Exception as e:
        frappe.logger().warning(f"Document transfer failed for {asset.name}: {e}")

    # Auto-generate depreciation schedule (Phase 2)
    try:
        from assetcore.services import depreciation as depr_svc
        sched_result = depr_svc.generate_schedule(asset.name, force=False)
        frappe.logger().info(f"Depreciation schedule generated for {asset.name}: {sched_result}")
    except Exception as e:
        frappe.logger().warning(f"Schedule generation failed for {asset.name}: {e}")

    return asset.name


# ─── Scheduler ────────────────────────────────────────────────────────────────

def check_commissioning_overdue() -> None:
    """Daily: warn Workshop Head on commissioning quá hạn SLA (> OVERDUE_DAYS).

    Dùng CHUNG SoT `overdue_commissioning_filter()` với dashboard KPI + list drill
    → tập phiếu nhận alert == tập KPI == tập drill rows (cùng anchor, cùng ngưỡng).
    """
    today = nowdate()
    overdue = frappe.get_all(
        _DT,
        filters=overdue_commissioning_filter(today),
        fields=["name", "vendor", "workflow_state", _OVERDUE_ANCHOR, "commissioned_by"],
    )
    for comm in overdue:
        _send_overdue_alert(comm, date_diff(today, comm[_OVERDUE_ANCHOR]))


def _send_overdue_alert(comm: dict, days_open: int) -> None:
    # R22: "IMM Workshop Lead" không tồn tại -> email im lặng. Dùng role THẬT.
    from assetcore.services.shared import notify_roles
    users = frappe.db.get_all("Has Role", filters={"role": notify_roles.WORKSHOP_HEAD[0], "parenttype": "User"}, fields=["parent"])
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
    # Enrich label cho các Link field — FE hiển thị tên thay vì mã code
    vendor_name = (
        frappe.db.get_value(_DT_SUPPLIER, doc.vendor, "supplier_name")
        if doc.vendor else ""
    ) or doc.vendor or ""
    master_item_name = (
        frappe.db.get_value(_DT_MODEL, doc.master_item, "model_name")
        if doc.master_item else ""
    ) or doc.master_item or ""
    clinical_dept_name = (
        frappe.db.get_value(_DT_DEPT, doc.clinical_dept, "department_name")
        if doc.clinical_dept else ""
    ) or doc.clinical_dept or ""

    return {
        "name": doc.name,
        "workflow_state": doc.workflow_state,
        "docstatus": doc.docstatus,
        "po_reference": doc.po_reference,
        "master_item": doc.master_item,
        "master_item_name": master_item_name,
        "vendor": doc.vendor,
        "vendor_name": vendor_name,
        "clinical_dept": doc.clinical_dept,
        "clinical_dept_name": clinical_dept_name,
        "expected_installation_date": str(doc.expected_installation_date or ""),
        "installation_date": str(doc.installation_date or ""),
        "reception_date": str(doc.get("reception_date") or ""),
        "risk_class": doc.get("risk_class") or "",
        "board_approver": doc.get("board_approver") or "",
        "pending_approver":      doc.get("pending_approver") or "",
        "approval_stage":        doc.get("approval_stage") or "",
        "approval_submitted_at": str(doc.get("approval_submitted_at") or ""),
        "approval_remarks":      doc.get("approval_remarks") or "",
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
        "documents_incomplete": doc.get("documents_incomplete") or 0,
        "documents_incomplete_note": doc.get("documents_incomplete_note") or "",
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
        # Phase 1 notification framework — message_code + context tự render
        # vào envelope qua handle() trong api/imm04.py.
        nthrow(MSG.IMM04_NOT_FOUND, name=name)
    try:
        frappe.has_permission(_DT, ptype="read", doc=name, throw=True)
    except frappe.PermissionError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Bạn không có quyền xem phiếu này")
    result = _serialize_commissioning(doc)
    result["allowed_transitions"] = _get_workflow_transitions(name)
    return result


def _is_truthy(value) -> bool:
    """Chuẩn hoá cờ ảo (overdue) từ FE: 1/'1'/True/'true' → True; 0/''/None → False."""
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _dict_to_list_filters(d: dict) -> list:
    """Chuyển filter dict → Frappe list-filter form [[doctype, field, op, val], ...].

    Cho phép cùng 1 cột mang nhiều ràng buộc (vd workflow_state user-chosen + NOT IN
    terminal) mà không clobber như dict.update().
    """
    out: list = []
    for field, cond in d.items():
        op, val = cond if isinstance(cond, tuple) else ("=", cond)
        out.append([_DT, field, op, val])
    return out


def list_commissioning(filters: dict, page: int = 1, page_size: int = 20) -> dict:
    try:
        frappe.has_permission(_DT, ptype="read", throw=True)
    except frappe.PermissionError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền truy cập")

    safe_filters = {k: v for k, v in filters.items() if k in _ALLOWED_FILTER_KEYS}
    if "docstatus" not in safe_filters:
        safe_filters["docstatus"] = ("!=", 2)

    # Tham số ảo `overdue=1` (BR-04-10): AND thêm SoT overdue_commissioning_filter()
    # vào điều kiện list — KHÔNG lọt qua _ALLOWED_FILTER_KEYS dạng raw column, KHÔNG
    # clobber các filter khác. Chuyển sang Frappe list-filter form để cùng 1 cột
    # (workflow_state) có thể mang nhiều ràng buộc (user-chosen AND not-in-terminal).
    query_filters: list | dict = safe_filters
    if _is_truthy(filters.get("overdue")):
        query_filters = _dict_to_list_filters(safe_filters)
        for field, cond in overdue_commissioning_filter().items():
            op, val = cond if isinstance(cond, tuple) else ("=", cond)
            query_filters.append([_DT, field, op, val])

    page = max(1, int(page))
    page_size = min(max(1, int(page_size)), 100)
    total = frappe.db.count(_DT, query_filters)
    pg = paginate(total, page, page_size)

    records = frappe.get_all(
        _DT, filters=query_filters, fields=_LIST_FIELDS,
        order_by=_ORDER_MODIFIED,
        limit_start=pg["offset"], limit_page_length=pg["page_size"],
    )

    item_ids = {r.get("master_item") for r in records if r.get("master_item")}
    vendor_ids = {r.get("vendor") for r in records if r.get("vendor")}
    dept_ids = {r.get("clinical_dept") for r in records if r.get("clinical_dept")}
    po_ids = {r.get("po_reference") for r in records if r.get("po_reference")}
    asset_ids = {r.get("final_asset") for r in records if r.get("final_asset")}

    item_map = (
        {i.name: i.model_name for i in frappe.get_all(_DT_MODEL, filters={"name": ["in", list(item_ids)]}, fields=["name", "model_name"])}
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
    po_map: dict = {}
    if po_ids:
        try:
            po_rows = frappe.get_all(
                _DT_PO, filters={"name": ["in", list(po_ids)]},
                fields=["name", "purchase_name"],
            )
            po_map = {p.name: (p.get("purchase_name") or p.name) for p in po_rows}
        except Exception:
            po_map = {}
    asset_map: dict = {}
    if asset_ids:
        try:
            asset_rows = frappe.get_all(
                _DT_ASSET, filters={"name": ["in", list(asset_ids)]},
                fields=["name", "asset_name"],
            )
            asset_map = {a.name: a.asset_name for a in asset_rows}
        except Exception:
            asset_map = {}

    for r in records:
        r["master_item_name"] = item_map.get(r.get("master_item"), r.get("master_item") or "")
        r["device_model_name"] = r["master_item_name"]  # alias per DC contract
        r["vendor_name"] = vendor_map.get(r.get("vendor"), r.get("vendor") or "")
        r["supplier_name"] = r["vendor_name"]  # alias per DC contract
        r["clinical_dept_name"] = dept_map.get(r.get("clinical_dept"), r.get("clinical_dept") or "")
        r["po_ref_name"] = po_map.get(r.get("po_reference"), r.get("po_reference") or "")
        r["asset_name"] = asset_map.get(r.get("final_asset"), r.get("final_asset") or "")

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

    return {
        "kpis": {
            "pending_count": sum(v for k, v in state_map.items() if k not in _TERMINAL_STATES),
            "hold_count": state_map.get("Clinical Hold", 0),
            "open_nc_count": frappe.db.count(_DT_NC, {"resolution_status": "Open", "docstatus": ("!=", 2)}),
            # SoT (BR-04-11): 'Bàn giao tháng này' đếm theo commissioning_date
            # (ngày vào Clinical Release) trong cửa sổ [đầu tháng, hôm nay] — KHÔNG
            # dùng `modified` (mọi .save() tháng này sẽ thổi phồng count phiếu tháng
            # trước). BETWEEN loại NULL legacy tự nhiên → NULL-safe, không lọt count.
            # card count == số rows drill list Clinical Release cùng cửa sổ tháng.
            "released_this_month": frappe.db.count(_DT, {
                "workflow_state": _STATE_CLINICAL_RELEASE, "docstatus": 1,
                "commissioning_date": ("between", [str(first_day), str(nowdate())]),
            }),
            # SoT: cùng filter với list drill `overdue=1` + scheduler alert.
            # card count == drill rows == scheduler set (BR-04-10).
            "overdue_sla": frappe.db.count(_DT, overdue_commissioning_filter()),
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


def search_link(
    doctype: str,
    query: str = "",
    page_length: int = 10,
    extra_filters: dict | None = None,
) -> list:
    if doctype not in _ALLOWED_SEARCH_DOCTYPES:
        raise ServiceError(ErrorCode.FORBIDDEN, f"DocType '{doctype}' không được phép tìm kiếm")
    config = _ALLOWED_SEARCH_DOCTYPES[doctype]
    if config.get("optional") and not frappe.db.exists("DocType", doctype):
        return []
    filters = dict(config["filters"])
    # Merge whitelisted dynamic filters from caller (e.g. {is_group: 1} for tree parents)
    allowed_dynamic = config.get("dynamic_filter_fields") or set()
    if extra_filters and allowed_dynamic:
        for k, v in extra_filters.items():
            if k in allowed_dynamic:
                filters[k] = v
    # Defense-in-depth (root-cause class of bug IMM-11∩IMM-04): drop any
    # configured field that is not a real column so a config drift can never
    # surface as OperationalError 1054 / a leaked traceback to the caller.
    # 'name' is always valid; business errors (FORBIDDEN/NOT_FOUND) are untouched.
    meta = frappe.get_meta(doctype)
    def _live(field: str) -> bool:
        return field == "name" or meta.has_field(field)
    search_fields = [f for f in config["search_fields"] if _live(f)]
    extra_fields = [f for f in config["extra_fields"] if _live(f)]
    or_filters = []
    if query:
        q = f"%{query}%"
        for field in search_fields:
            or_filters.append([doctype, field, "like", q])
    fields = [*{*extra_fields, "name"}]
    results = frappe.db.get_all(
        doctype, filters=filters, or_filters=or_filters or None,
        fields=fields, limit=int(page_length), order_by=_ORDER_MODIFIED,
        ignore_permissions=True,
    )
    label_field = config["label_field"]
    items = []
    for row in results:
        value = row.get("name") or row.get(label_field, "")
        label = row.get(label_field) or value
        desc_parts = [str(row[f]) for f in extra_fields if f != label_field and row.get(f)]
        items.append({"value": value, "label": label, "description": " | ".join(desc_parts)})
    return items


def get_po_details(po_name: str) -> dict:
    if not frappe.db.exists(_DT_PO, po_name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy đơn hàng '{po_name}'")
    po = frappe.get_doc(_DT_PO, po_name)
    supplier_name = frappe.db.get_value(_DT_SUPPLIER, po.supplier, "supplier_name") or po.supplier or ""
    return {
        "po_name": po.name,
        "supplier": po.supplier or "",
        "supplier_name": supplier_name,
        "invoice_no": po.invoice_no or "",
        "transaction_date": str(po.purchase_date or ""),
        "items": [
            {"item_code": i.spare_part, "item_name": i.part_name, "qty": i.qty}
            for i in (po.items or [])
        ],
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
    prev_state = doc.workflow_state
    frappe.model.workflow.apply_workflow(doc, action)
    log_lifecycle_event(doc, action, prev_state, doc.workflow_state)
    # BR-04-11: stamp ngày bàn giao khi (và chỉ khi) phiếu vừa vào Clinical Release.
    # Đặt TRƯỚC doc.save → persist cùng lượt với auto-mint create_ac_asset bên dưới.
    _stamp_commissioning_date(doc)
    doc.save(ignore_permissions=False)

    # RC-06 fix: once we reach Clinical Release (acceptance "Hoàn tất"), auto-mint
    # the AC Asset even if the user hasn't clicked Submit yet. Idempotent — guarded
    # by `doc.final_asset` inside `create_ac_asset`. Best-effort: don't block the
    # workflow if asset creation fails — surface as a log entry the user can chase.
    if doc.workflow_state == _STATE_CLINICAL_RELEASE and not doc.final_asset:
        try:
            asset_name = create_ac_asset(doc)
            if asset_name:
                frappe.db.set_value(_DT, doc.name, "final_asset", asset_name)
                doc.reload()
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"IMM-04 auto-mint asset failed on transition: {doc.name}",
            )
            frappe.msgprint(
                _("⚠ Phiếu đã chuyển sang '{0}' nhưng không tạo được Tài sản tự động: {1}. "
                  "Vui lòng bấm Submit để thử lại.").format(_STATE_CLINICAL_RELEASE, str(e)),
                alert=True, indicator="orange",
            )

    return {
        "name": name, "action_applied": action,
        "new_state": doc.workflow_state, "docstatus": doc.docstatus,
        "final_asset": doc.final_asset,
    }


def submit_commissioning(name: str) -> dict:
    if not frappe.db.exists(_DT, name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu '{name}'")
    # R20 FIX: gate qua capability THẬT (commissioning.submit → DocPerm submit
    # trên Asset Commissioning: Commissioning Manager=1, User=0). Trước fix dùng
    # _SUBMIT_ROLES role-name bịa ("IMM Operations Manager"/"IMM Workshop Lead")
    # → KHÔNG user nào pass → submit commissioning chết (bug IMM-12 lặp lại).
    if not rbac.can("commissioning.submit"):
        raise ServiceError(ErrorCode.FORBIDDEN,
                           "Chỉ Commissioning Manager mới được Submit phiếu nghiệm thu")
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

    # Gate 5 — IMM-04 ↔ IMM-16: block commissioning nếu asset có Critical CAPA/finding mở
    asset_for_check = getattr(doc, "final_asset", "") or getattr(doc, "master_item", "")
    if asset_for_check:
        try:
            from assetcore.services.imm16 import check_asset_compliance_status  # noqa: PLC0415
            cstatus = check_asset_compliance_status(asset_for_check)
            if cstatus.get("blocked"):
                reasons_msg = "; ".join(
                    f"{r.get('type')}={r.get('ref')}" for r in cstatus.get("reasons", [])
                )
                raise ServiceError(
                    ErrorCode.COMPLIANCE_BLOCKED,
                    _("IMM-16 gate: asset {0} bị block do compliance ({1})").format(
                        asset_for_check, reasons_msg
                    ),
                )
        except ServiceError:
            raise
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-04: compliance gate failed")

    # BR-04-11: bảo hiểm stamp ngày bàn giao cho phiếu vào Clinical Release từ
    # trước fix mà chưa được stamp. Idempotent (no-op nếu đã có). submit persist.
    _stamp_commissioning_date(doc)
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


_DOC_FIELDS = ("doc_type", "status", "is_mandatory", "doc_number", "remarks", "file_url")
_DOC_DATE_FIELDS = ("received_date", "expiry_date")


def _apply_document_updates(doc, rows: list) -> None:
    """Replace child table khi FE gửi danh sách đầy đủ.

    FE gửi 1 list các row hiện đang hiển thị (đã merge pending + base). BE
    so khớp theo idx; row mới (idx không tồn tại) → append; row bị bỏ → remove.
    """
    incoming = [r for r in rows if isinstance(r, dict)]
    incoming_idx = {r.get("idx") for r in incoming if r.get("idx") is not None}

    # Xóa row không còn trong incoming
    doc.commissioning_documents = [
        r for r in doc.commissioning_documents if r.idx in incoming_idx
    ]

    existing_by_idx = {r.idx: r for r in doc.commissioning_documents}

    for upd in incoming:
        idx = upd.get("idx")
        target = existing_by_idx.get(idx)
        if target is None:
            target = doc.append("commissioning_documents", {})
        for f in _DOC_FIELDS:
            if f in upd:
                target.set(f, upd[f])
        for f in _DOC_DATE_FIELDS:
            if f in upd:
                target.set(f, upd[f] or None)


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


def generate_internal_qr(name: str) -> dict:
    """BUG-009: Manual / fallback QR generator.

    Idempotent: nếu phiếu đã có QR thì trả lại giá trị hiện tại, không ghi đè.
    Có thể gọi ở bất kỳ workflow_state nào miễn là docstatus != 2 (Cancelled).
    Dùng cùng format `BV-{DEPT}-{YYYY}-{SEQ}` như controller `_generate_internal_qr`.
    """
    import datetime

    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")
    if doc.docstatus == 2:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Phiếu đã hủy, không thể sinh QR")
    try:
        frappe.has_permission(_DT, ptype="write", doc=name, throw=True)
    except frappe.PermissionError as exc:
        raise ServiceError(ErrorCode.FORBIDDEN, "Bạn không có quyền sinh QR cho phiếu này") from exc

    if doc.internal_tag_qr:
        return {
            "name": doc.name,
            "internal_tag_qr": doc.internal_tag_qr,
            "generated": False,
        }

    dept_code = (doc.clinical_dept or "GEN").replace(" ", "").upper()[:6]
    year = datetime.datetime.now().year
    count = frappe.db.count(
        _DT,
        {
            "internal_tag_qr": ("like", f"BV-%-{year}-%"),
            "name": ("!=", doc.name),
        },
    )
    seq = str(count + 1).zfill(4)
    qr = f"BV-{dept_code}-{year}-{seq}"

    frappe.db.set_value(_DT, doc.name, "internal_tag_qr", qr)
    return {"name": doc.name, "internal_tag_qr": qr, "generated": True}


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
    # AUTH-05 — 4-eyes: board_approver must not also be the submitter or
    # already wear another signer hat (clinical_head, qa_officer) on this phiếu.
    assert_distinct_signers(
        doc, "clinical_head", "qa_officer", "owner", "pending_approver",
        candidate_user=board_approver,
        candidate_field="board_approver",
    )
    doc.board_approver = board_approver
    if approval_remarks:
        doc.notes = (doc.notes or "") + f"\n[Board Approval] {approval_remarks}"
    # BR-04-11: stamp ngày bàn giao TRƯỚC save (idempotent). Sau đây
    # doc.commissioning_date luôn non-NULL → return đọc thẳng (bỏ fallback giả).
    _stamp_commissioning_date(doc)
    doc.save(ignore_permissions=True)
    doc.submit()
    return {
        "commissioning": commissioning,
        "new_status": _STATE_CLINICAL_RELEASE,
        "asset_ref": doc.final_asset,
        "commissioning_date": str(doc.commissioning_date),
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
    """Hủy phiếu Commissioning đã Submit (docstatus 1 → 2). Chỉ IMM Operations Manager / IMM Workshop Lead."""
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
    # R20 FIX: gate qua capability THẬT (commissioning.cancel → DocPerm cancel:
    # Commissioning Manager=1, User=0). Bỏ _SUBMIT_ROLES role-name bịa.
    if not rbac.can("commissioning.cancel"):
        raise ServiceError(ErrorCode.FORBIDDEN,
                           "Chỉ Commissioning Manager mới được phép hủy phiếu nghiệm thu")
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


# ─── Submit-for-approval workflow ─────────────────────────────────────────────

# R22: trỏ role THẬT (trước đây "IMM Biomed Technician"/"IMM Operations Manager"
# KHÔNG tồn tại -> mọi approver không-super-admin bị FORBIDDEN -> flow gửi-duyệt
# commissioning chết). Stage kỹ thuật -> Maintenance User; phát hành lâm sàng ->
# Commissioning Manager (chủ sở hữu nghiệp vụ commissioning).
_STAGE_ROLE: dict[str, str] = {
    "Doc Verify":       "Maintenance User",
    "Facility Check":   "Maintenance User",
    "Baseline Review":  "Maintenance User",
    "Clinical Release": "Commissioning Manager",
}

_STATE_TO_STAGE: dict[str, str] = {
    "Draft":              "Doc Verify",
    "Pending Doc Verify": "Doc Verify",
    "To Be Installed":    "Facility Check",
    "Installing":         "Facility Check",
    "Identification":     "Baseline Review",
    "Initial Inspection": "Clinical Release",
    "Clinical Hold":      "Clinical Release",
    "Re Inspection":      "Baseline Review",
}

# Approval-grant resolves the next workflow action from the *current*
# workflow_state (not the stage) so every approvable state maps to the exact
# action string in imm_04_workflow.json. Keyed by workflow_state.
_APPROVE_ACTION_BY_STATE: dict[str, str] = {
    "Pending Doc Verify": "Xác nhận đủ tài liệu",   # → To Be Installed
    "To Be Installed":    "Bắt đầu lắp đặt",         # → Installing
    "Initial Inspection": "Phê duyệt phát hành",     # → Clinical Release
    "Clinical Hold":      "Gỡ giữ lâm sàng",         # → Clinical Release
    "Re Inspection":      "Phê duyệt sau tái kiểm",  # → Clinical Release
}


def _notify_user(user: str, commissioning: str, subject: str, html_body: str) -> None:
    """Create Notification Log + publish realtime for a user."""
    frappe.get_doc({
        "doctype":       "Notification Log",
        "subject":       subject,
        "email_content": html_body,
        "for_user":      user,
        "type":          "Alert",
        "document_type": _DT,
        "document_name": commissioning,
        "from_user":     frappe.session.user,
    }).insert(ignore_permissions=True)
    frappe.publish_realtime(
        "new_notification",
        {"subject": subject, "document_type": _DT, "document_name": commissioning},
        user=user,
    )


def _find_last_approval_submitter(doc) -> str:
    """Latest 'Approval Submitted' event actor; fallback to doc.owner."""
    for ev in reversed(doc.get("lifecycle_events") or []):
        if ev.get("event_type") == "Approval Submitted":
            return ev.get("actor") or ""
    return doc.owner or ""


def submit_for_approval(commissioning: str, approver: str, stage: str = "",
                         remarks: str = "") -> dict:
    """Assign pending approver + create notification."""
    if not frappe.db.exists(_DT, commissioning):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu '{commissioning}'")
    if not approver:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Phải chọn người duyệt")

    doc = frappe.get_doc(_DT, commissioning)

    if not stage:
        stage = _STATE_TO_STAGE.get(doc.workflow_state, "")
        if not stage:
            raise ServiceError(
                ErrorCode.INVALID_PARAMS,
                f"Trạng thái '{doc.workflow_state}' không hỗ trợ gửi duyệt",
            )

    required_role = _STAGE_ROLE.get(stage)
    if required_role:
        user_roles = frappe.get_roles(approver)
        # Allow either the specific stage role OR Super Admin umbrella
        if required_role not in user_roles and "AssetCore Super Admin" not in user_roles:
            raise ServiceError(
                ErrorCode.FORBIDDEN,
                f"Người duyệt '{approver}' không có vai trò '{required_role}'",
            )

    # AUTH-05 — 4-eyes (Separation of Duties):
    #   (a) submitter cannot route the phiếu to themselves.
    #   (b) chosen approver must not already wear another signer hat on this
    #       phiếu (clinical_head, qa_officer, board_approver, owner).
    if approver == frappe.session.user:
        raise ServiceError(
            ErrorCode.FORBIDDEN,
            "4-eyes: bạn không thể gửi phiếu này cho chính mình duyệt — "
            "phải chọn một người duyệt khác.",
        )
    assert_distinct_signers(
        doc, *_SIGNER_FIELDS,
        candidate_user=approver,
        candidate_field="pending_approver",
    )

    now = frappe.utils.now_datetime()
    doc.db_set("pending_approver",      approver, update_modified=False)
    doc.db_set("approval_stage",        stage,    update_modified=False)
    doc.db_set("approval_submitted_at", now,      update_modified=False)
    doc.db_set("approval_remarks",      remarks or "", update_modified=False)

    submitter = frappe.session.user
    submitter_name = frappe.db.get_value("User", submitter, "full_name") or submitter
    subject = f"Yêu cầu duyệt phiếu tiếp nhận: {commissioning}"
    content = (
        f"<p><b>{submitter_name}</b> đã gửi phiếu <b>{commissioning}</b> "
        f"đến bạn để duyệt giai đoạn <b>{stage}</b>.</p>"
    )
    if remarks:
        content += f"<p><i>Ghi chú:</i> {frappe.utils.escape_html(remarks)}</p>"
    _notify_user(approver, commissioning, subject, content)

    try:
        doc.reload()
        doc.append("lifecycle_events", {
            "event_type": "Approval Submitted",
            "timestamp":  now,
            "actor":      submitter,
            "from_state": doc.workflow_state,
            "to_state":   doc.workflow_state,
            "remarks":    f"Gửi duyệt đến {approver} ({stage})" + (f": {remarks}" if remarks else ""),
        })
        doc.save(ignore_permissions=True)
    except Exception:
        pass

    return {
        "name":                  commissioning,
        "pending_approver":      approver,
        "approval_stage":        stage,
        "approval_submitted_at": str(now),
    }


def approve_pending(commissioning: str, decision: str, remarks: str = "") -> dict:
    """Approver accepts or rejects a pending approval."""
    if not frappe.db.exists(_DT, commissioning):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy phiếu '{commissioning}'")
    if decision not in ("Approve", "Reject"):
        raise ServiceError(ErrorCode.INVALID_PARAMS, "decision phải là 'Approve' hoặc 'Reject'")
    if decision == "Reject" and not remarks.strip():
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Phải nhập lý do khi từ chối")

    doc = frappe.get_doc(_DT, commissioning)
    if not doc.pending_approver:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Phiếu không có yêu cầu duyệt đang chờ")

    current_user = frappe.session.user
    if doc.pending_approver != current_user and "AssetCore Super Admin" not in frappe.get_roles(current_user):
        raise ServiceError(ErrorCode.FORBIDDEN, "Bạn không phải người được phân công duyệt phiếu này")

    # AUTH-05 — 4-eyes: approver must not also be the original submitter.
    # Also block sliding into a second signer slot if they already filled one.
    assert_not_self_submitter(doc, submitter_field="owner",
                              candidate_user=current_user)
    assert_distinct_signers(
        doc, "clinical_head", "qa_officer", "board_approver", "owner",
        candidate_user=current_user,
        candidate_field="pending_approver",
    )

    stage = doc.approval_stage or ""
    submitter_user = _find_last_approval_submitter(doc)
    current_user_name = frappe.db.get_value("User", current_user, "full_name") or current_user

    if decision == "Reject":
        doc.db_set("pending_approver",      "",   update_modified=False)
        doc.db_set("approval_stage",        "",   update_modified=False)
        doc.db_set("approval_submitted_at", None, update_modified=False)
        doc.db_set("approval_remarks",      f"TỪ CHỐI: {remarks}", update_modified=False)
        doc.reload()
        doc.append("lifecycle_events", {
            "event_type": "Approval Rejected",
            "timestamp":  frappe.utils.now_datetime(),
            "actor":      current_user,
            "from_state": doc.workflow_state,
            "to_state":   doc.workflow_state,
            "remarks":    f"Từ chối ({stage}): {remarks}",
        })
        doc.save(ignore_permissions=True)
        if submitter_user:
            _notify_user(
                submitter_user, commissioning,
                f"Yêu cầu duyệt bị từ chối: {commissioning}",
                f"<p><b>{current_user_name}</b> đã từ chối phiếu <b>{commissioning}</b>.</p>"
                f"<p><i>Lý do:</i> {frappe.utils.escape_html(remarks)}</p>",
            )
        return {"name": commissioning, "decision": "Reject", "workflow_state": doc.workflow_state}

    # Approve → trigger transition (resolve action from current state)
    from_state = doc.workflow_state
    action = _APPROVE_ACTION_BY_STATE.get(from_state)
    if not action:
        raise ServiceError(
            ErrorCode.CONFLICT,
            f"Không thể duyệt: trạng thái '{from_state}' không có bước duyệt hợp lệ "
            f"(giai đoạn '{stage}')",
        )

    if stage == "Clinical Release" and not doc.board_approver:
        doc.db_set("board_approver", current_user, update_modified=False)

    doc.db_set("pending_approver",      "",   update_modified=False)
    doc.db_set("approval_stage",        "",   update_modified=False)
    doc.db_set("approval_submitted_at", None, update_modified=False)

    doc.reload()
    from frappe.model.workflow import apply_workflow
    new_doc = apply_workflow(doc, action)
    new_doc.append("lifecycle_events", {
        "event_type": "Approval Granted",
        "timestamp":  frappe.utils.now_datetime(),
        "actor":      current_user,
        "from_state": from_state,
        "to_state":   new_doc.workflow_state,
        "remarks":    f"Duyệt ({stage})" + (f": {remarks}" if remarks else ""),
    })
    new_doc.save(ignore_permissions=True)

    if submitter_user:
        _notify_user(
            submitter_user, commissioning,
            f"Yêu cầu duyệt được chấp nhận: {commissioning}",
            f"<p><b>{current_user_name}</b> đã duyệt phiếu <b>{commissioning}</b>. "
            f"Trạng thái mới: <b>{new_doc.workflow_state}</b>.</p>",
        )

    return {"name": commissioning, "decision": "Approve", "workflow_state": new_doc.workflow_state}


def list_my_pending_approvals() -> list[dict]:
    """Commissioning records where current user is the pending_approver."""
    items = frappe.get_all(
        _DT,
        filters={"pending_approver": frappe.session.user, "docstatus": ["!=", 2]},
        fields=["name", "workflow_state", "master_item", "vendor", "clinical_dept",
                "approval_stage", "approval_submitted_at", "approval_remarks",
                "owner", "modified"],
        order_by="approval_submitted_at desc",
        limit_page_length=50,
    )
    vendor_ids = {r.get("vendor") for r in items if r.get("vendor")}
    if vendor_ids:
        mapping = {r.name: r.supplier_name for r in frappe.get_all(
            "AC Supplier", filters={"name": ["in", list(vendor_ids)]}, fields=["name", "supplier_name"],
        )}
        for r in items:
            r["vendor_name"] = mapping.get(r.get("vendor")) or r.get("vendor") or ""
    return items


# ─── Purchase → Commissioning linkage (Wave 1 P1) ─────────────────────────────

def create_commissioning_from_purchase(purchase_name: str, device_idx: int) -> dict:
    """Tạo 1 Asset Commissioning draft từ 1 dòng thiết bị trong AC Purchase."""
    if not frappe.db.exists(_DT_PO, purchase_name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy đơn hàng '{purchase_name}'")
    try:
        frappe.has_permission(_DT, ptype="create", throw=True)
    except frappe.PermissionError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Bạn không có quyền tạo phiếu tiếp nhận")

    po = frappe.get_doc(_DT_PO, purchase_name)
    if po.docstatus != 1:
        raise ServiceError(
            ErrorCode.INVALID_PARAMS,
            "Chỉ tạo phiếu tiếp nhận từ đơn hàng đã duyệt (docstatus=1)",
        )
    if po.status == "Cancelled":
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Đơn hàng đã bị huỷ")

    devices = po.get("devices") or []
    if not devices:
        raise ServiceError(
            ErrorCode.INVALID_PARAMS,
            "Đơn hàng này không có thiết bị. Phụ tùng phải qua phiếu nhập kho.",
        )
    row = next((d for d in devices if int(d.idx) == int(device_idx)), None)
    if not row:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy dòng thiết bị #{device_idx}")
    if row.commissioning_ref:
        raise ServiceError(
            ErrorCode.CONFLICT,
            f"Thiết bị này đã có phiếu tiếp nhận '{row.commissioning_ref}'",
        )
    if not row.device_model:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Dòng thiết bị chưa có Model")

    warranty_expiry = None
    if row.warranty_months and row.warranty_months > 0:
        base = getdate(po.get("expected_delivery") or po.purchase_date or nowdate())
        warranty_expiry = add_days(base, int(row.warranty_months) * 30)

    doc = frappe.get_doc({
        "doctype":                    _DT,
        "workflow_state":             "Draft",  # explicit — phiếu mở ra ở trạng thái nháp, user sửa rồi gửi duyệt
        "po_reference":               purchase_name,
        "master_item":                row.device_model,
        "vendor":                     po.supplier,
        "clinical_dept":              row.clinical_dept or "",
        "expected_installation_date": po.get("expected_delivery") or nowdate(),
        "reception_date":             nowdate(),
        "purchase_price":             float(row.unit_cost or 0),
        "warranty_expiry_date":       warranty_expiry,
        "vendor_serial_no":           row.vendor_serial_no or "",
    })
    _populate_mandatory_documents(doc)
    doc.insert(ignore_permissions=False)

    # Link back on purchase row
    frappe.db.set_value(
        "AC Purchase Device Item", row.name, "commissioning_ref", doc.name,
        update_modified=False,
    )

    return {"name": doc.name, "workflow_state": doc.workflow_state, "purchase": purchase_name}


# ─── Auto-transfer commissioning documents → Asset Document (Wave 1 P2) ──────

# Map commissioning doc_type → (Asset Document doc_category, default validity in months)
_DOC_CATEGORY_MAP: dict[str, tuple[str, int]] = {
    "CO - Chứng nhận Xuất xứ":    ("Certification", 0),
    "CQ - Chứng nhận Chất lượng": ("Certification", 0),
    "Packing List":                ("Technical",     0),
    "Manual / HDSD":               ("Technical",     0),
    "Warranty Card":               ("Legal",         0),
    "Training Certificate":        ("Training",      0),
}


def _transfer_commissioning_documents_to_asset(
    commissioning_doc: Document, asset_name: str,
) -> int:
    """Copy commissioning_documents (có file_url) sang Asset Document (IMM-05).

    Returns: số bản ghi đã tạo.
    """
    if not asset_name or not commissioning_doc.get("commissioning_documents"):
        return 0

    created = 0
    for row in commissioning_doc.commissioning_documents:
        if not row.get("file_url"):
            continue
        if row.get("status") not in ("Received", "Waived"):
            continue

        category, default_months = _DOC_CATEGORY_MAP.get(
            row.get("doc_type") or "", ("Technical", 0),
        )
        expiry = row.get("expiry_date") or None
        if not expiry and default_months > 0:
            expiry = add_days(nowdate(), default_months * 30)

        try:
            ad = frappe.get_doc({
                "doctype":              "Asset Document",
                "asset_ref":            asset_name,
                "source_commissioning": commissioning_doc.name,
                "source_module":        "IMM-04",
                "doc_category":         category,
                "doc_type_detail":      row.get("doc_type") or "",
                "doc_number":           row.get("doc_number") or "",
                "file_url":             row.get("file_url"),
                "expiry_date":          expiry,
                "received_date":        row.get("received_date") or nowdate(),
                "remarks": f"Tự động từ phiếu tiếp nhận {commissioning_doc.name}",
            })
            ad.flags.ignore_mandatory = True
            ad.flags.ignore_permissions = True
            ad.insert(ignore_permissions=True)
            created += 1
        except Exception as e:
            frappe.logger().warning(
                f"Failed to transfer document '{row.get('doc_type')}' to Asset Document: {e}"
            )
    return created


# ─── Get commissioning info for a device row (used by AssetDetailView) ────────

def get_commissioning_origin(asset_name: str) -> dict:
    """Return origin info (commissioning + purchase) for an asset."""
    if not frappe.db.exists(_DT_ASSET, asset_name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy tài sản '{asset_name}'")

    commissioning_ref = frappe.db.get_value(_DT_ASSET, asset_name, "commissioning_ref")
    if not commissioning_ref:
        return {"asset": asset_name, "commissioning": None}

    comm = frappe.db.get_value(
        _DT, commissioning_ref,
        ["name", "workflow_state", "po_reference", "vendor", "master_item",
         "reception_date", "commissioning_date", "vendor_serial_no",
         "purchase_price", "warranty_expiry_date", "commissioned_by"],
        as_dict=True,
    )
    if not comm:
        return {"asset": asset_name, "commissioning": None}

    # Count transferred documents
    doc_count = frappe.db.count(
        "Asset Document",
        {"asset_ref": asset_name, "source_commissioning": commissioning_ref},
    )
    comm["transferred_doc_count"] = doc_count
    return {"asset": asset_name, "commissioning": comm}
