"""Service layer for IMM-04 Asset Commissioning business logic."""
from __future__ import annotations
import frappe
from frappe import _
from frappe.utils import nowdate, getdate, date_diff
from frappe.model.document import Document


def initialize_commissioning(doc: Document) -> None:
    """before_insert: set defaults, auto-fill risk_class from Item, populate mandatory docs."""
    if not doc.reception_date:
        doc.reception_date = nowdate()
    if not doc.risk_class and doc.master_item:
        doc.risk_class = frappe.db.get_value("Item", doc.master_item, "custom_risk_class") or ""
    _populate_mandatory_documents(doc)


def _populate_mandatory_documents(doc: Document) -> None:
    """Pre-fill commissioning_documents with mandatory doc types. Only if empty."""
    if doc.get("commissioning_documents"):
        return
    mandatory_docs = [
        {"doc_type": "CO", "is_mandatory": 1, "status": "Pending"},
        {"doc_type": "CQ", "is_mandatory": 1, "status": "Pending"},
        {"doc_type": "Manual", "is_mandatory": 1, "status": "Pending"},
        {"doc_type": "Warranty", "is_mandatory": 0, "status": "Pending"},
    ]
    if doc.risk_class in ("C", "D", "Radiation"):
        mandatory_docs.append({"doc_type": "License", "is_mandatory": 1, "status": "Pending"})
    if doc.risk_class == "Radiation":
        mandatory_docs.append({"doc_type": "Radiation License", "is_mandatory": 1, "status": "Pending"})
    for d in mandatory_docs:
        doc.append("commissioning_documents", d)


def validate_commissioning(doc: Document) -> None:
    """validate(): run all VR rules."""
    _vr01_unique_serial_number(doc)
    _vr06_immutable_lifecycle_events(doc)
    _vr05_risk_class_change_warning(doc)
    _validate_document_expiry(doc)


def _vr01_unique_serial_number(doc: Document) -> None:
    """VR-01: SN unique across Asset and Commissioning."""
    if not doc.vendor_serial_no:
        return
    existing_asset = frappe.db.get_value("Asset", {"custom_vendor_serial": doc.vendor_serial_no}, "name")
    if existing_asset and existing_asset != doc.get("final_asset"):
        frappe.throw(
            _("VR-01: Serial Number '{0}' đã được gán cho Tài Sản {1}.").format(doc.vendor_serial_no, existing_asset),
            frappe.DuplicateEntryError,
        )
    existing_comm = frappe.db.get_value(
        "Asset Commissioning",
        {"vendor_serial_no": doc.vendor_serial_no, "name": ("!=", doc.name or ""), "docstatus": ("!=", 2)},
        "name",
    )
    if existing_comm:
        frappe.throw(
            _("VR-01: Serial Number '{0}' đã tồn tại trong Phiếu Nghiệm Thu {1}.").format(doc.vendor_serial_no, existing_comm),
            frappe.DuplicateEntryError,
        )


def _vr05_risk_class_change_warning(doc: Document) -> None:
    """VR-05: Warn if risk_class changed after Initial Inspection."""
    if doc.is_new() or doc.workflow_state in ("Draft", "Pending_Doc_Verify", "To_Be_Installed", "Installing", "Identification"):
        return
    original = frappe.db.get_value("Asset Commissioning", doc.name, "risk_class")
    if original and original != doc.risk_class:
        frappe.msgprint(
            _("VR-05: Phân loại rủi ro thay đổi từ '{0}' → '{1}'. Thay đổi này sẽ được ghi vào audit log và cần phê duyệt QA Officer.").format(original, doc.risk_class),
            alert=True, indicator="orange",
        )


def _vr06_immutable_lifecycle_events(doc: Document) -> None:
    """VR-06: Block editing existing lifecycle_events rows."""
    if doc.is_new():
        return
    existing = frappe.db.get_all(
        "Asset Lifecycle Event",
        filters={"parent": doc.name, "parenttype": "Asset Commissioning"},
        fields=["name", "event_timestamp", "actor", "event_type"],
    )
    existing_map = {e["name"]: e for e in existing}
    for row in doc.get("lifecycle_events") or []:
        if row.name and row.name in existing_map:
            orig = existing_map[row.name]
            if row.actor != orig["actor"] or row.event_type != orig["event_type"]:
                frappe.throw(_("VR-06: Nhật ký sự kiện vòng đời không được chỉnh sửa. Dữ liệu audit trail bất biến (ISO 13485 §4.2.5)."))


def _validate_document_expiry(doc: Document) -> None:
    """Warn if commissioning documents are expired or expiring soon."""
    today = getdate()
    for d in doc.get("commissioning_documents") or []:
        expiry = d.get("expiry_date")
        if expiry and d.get("status") == "Received":
            days = date_diff(expiry, today)
            if days < 0:
                frappe.throw(_("Tài liệu '{0}' đã hết hạn vào {1}. Vui lòng cập nhật.").format(d.doc_type, expiry))
            elif days < 30:
                frappe.msgprint(_("Cảnh báo: Tài liệu '{0}' sẽ hết hạn sau {1} ngày ({2}).").format(d.doc_type, days, expiry), alert=True, indicator="yellow")


def validate_gate_g01(doc: Document) -> None:
    """Gate G01 (VR-02): 100% mandatory docs must be Received before To_Be_Installed."""
    early_states = {"Draft", "Pending Doc Verify"}
    if doc.workflow_state in early_states:
        return
    missing = [
        d.doc_type for d in (doc.get("commissioning_documents") or [])
        if d.get("is_mandatory") and d.status not in ("Received", "Waived")
    ]
    if missing:
        frappe.throw(_("VR-02 (Gate G01): Chưa đủ tài liệu bắt buộc. Còn thiếu: {0}").format(", ".join(missing)))


def validate_gate_g03(doc: Document) -> None:
    """Gate G03 (VR-03): 100% baseline tests must Pass or N/A before Clinical Release."""
    if doc.workflow_state not in ("Clinical Release", "Re Inspection"):
        return
    failed = [row.parameter for row in (doc.get("baseline_tests") or []) if row.test_result == "Fail"]
    if failed:
        frappe.throw(_("VR-03 (Gate G03): Các thông số sau không đạt: {0}. Tất cả phải Pass trước khi phát hành.").format(", ".join(failed)))


def validate_gate_g05_g06(doc: Document) -> None:
    """Gate G05+G06: No open NCs + board_approver required for Clinical Release."""
    if doc.workflow_state != "Clinical Release":
        return
    open_nc = frappe.db.count("Asset QA Non Conformance", {"ref_commissioning": doc.name, "resolution_status": "Open"})
    if open_nc > 0:
        frappe.throw(_("VR-04 (Gate G05): Còn {0} NC chưa đóng. Giải quyết tất cả NC trước khi Release.").format(open_nc))
    if not doc.board_approver:
        frappe.throw(_("Gate G06: Cần chọn Người Phê Duyệt Ban Giám Đốc trước khi Clinical Release."))


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
    """on_cancel: block if Asset created; only allow at Draft/NC/Return states."""
    if doc.final_asset:
        frappe.throw(_("Không thể hủy Phiếu Nghiệm Thu '{0}' vì Tài Sản '{1}' đã được kích hoạt. Liên hệ CMMS Admin.").format(doc.name, doc.final_asset))
    if doc.workflow_state not in ("Draft", "Non Conformance", "Return To Vendor"):
        frappe.throw(_("Chỉ có thể hủy khi ở trạng thái Draft, Non Conformance hoặc Return To Vendor. Hiện tại: {0}").format(doc.workflow_state))


def create_erpnext_asset(doc: Document) -> str:
    """Create ERPNext Asset on Clinical Release. Returns asset name. BR-04-01."""
    if doc.final_asset:
        return doc.final_asset
    item_name = frappe.db.get_value("Item", doc.master_item, "item_name") or doc.master_item
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    asset = frappe.get_doc({
        "doctype": "Asset",
        "item_code": doc.master_item,
        "asset_name": item_name,
        "company": company,
        "location": doc.clinical_dept,
        "purchase_date": doc.reception_date or nowdate(),
        "custom_vendor_serial": doc.vendor_serial_no,
        "custom_internal_tag": doc.internal_tag_qr,
        "custom_commissioning_ref": doc.name,
        "custom_risk_class": doc.risk_class or "",
    })
    asset.flags.ignore_mandatory = True
    asset.insert(ignore_permissions=True)
    return asset.name


def check_commissioning_overdue() -> None:
    """Daily scheduler: warn Workshop Manager on commissioning open > 30 days."""
    from frappe.utils import add_days
    cutoff = add_days(nowdate(), -30)
    overdue = frappe.get_all(
        "Asset Commissioning",
        filters={
            "docstatus": 0,
            "workflow_state": ("not in", ["Clinical Release", "Return To Vendor"]),
            "reception_date": ("<", cutoff),
        },
        fields=["name", "vendor", "workflow_state", "reception_date", "commissioned_by"],
    )
    for comm in overdue:
        days_open = frappe.utils.date_diff(nowdate(), comm["reception_date"])
        _send_overdue_commissioning_alert(comm, days_open)


def _send_overdue_commissioning_alert(comm: dict, days_open: int) -> None:
    users = frappe.db.get_all("Has Role", filters={"role": "Workshop Head", "parenttype": "User"}, fields=["parent"])
    emails = [frappe.db.get_value("User", u.parent, "email") for u in users]
    emails = [e for e in emails if e]
    if not emails:
        return
    frappe.sendmail(
        recipients=emails,
        subject=f"[AssetCore] Phiếu {comm['name']} đã mở {days_open} ngày — cần xử lý",
        message=f"<p>Phiếu commissioning <b>{comm['name']}</b> đã mở <b>{days_open} ngày</b> mà chưa hoàn thành. Trạng thái: {comm['workflow_state']}.</p>",
    )
