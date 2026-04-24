"""IMM-01 — Needs Assessment API."""
from __future__ import annotations
import frappe
from frappe import _
from assetcore.utils.helpers import _ok, _err
from assetcore.utils.email import send_approval_request


@frappe.whitelist()
def create_needs_assessment(
    requesting_dept: str,
    equipment_type: str,
    quantity: int,
    estimated_budget: float,
    clinical_justification: str,
    priority: str = "Medium",
    linked_device_model: str = "",
    current_equipment_age: int = 0,
    failure_frequency: str = "",
    technical_specification: str = "",
) -> dict:
    """Create a new IMM-01 Needs Assessment record."""
    try:
        doc = frappe.get_doc(
            {
                "doctype": "Needs Assessment",
                "requesting_dept": requesting_dept,
                "request_date": frappe.utils.today(),
                "requested_by": frappe.session.user,
                "equipment_type": equipment_type,
                "quantity": int(quantity),
                "estimated_budget": float(estimated_budget),
                "clinical_justification": clinical_justification,
                "priority": priority,
                "linked_device_model": linked_device_model or None,
                "current_equipment_age": int(current_equipment_age) if current_equipment_age else None,
                "failure_frequency": failure_frequency or None,
                "technical_specification": technical_specification or None,
                "status": "Draft",
            }
        )
        doc.insert(ignore_permissions=False)
        # _log_lifecycle(doc, "needs_assessment_created", "", "Draft")
        return _ok({"name": doc.name, "status": doc.status})
    except frappe.ValidationError as exc:
        return _err(str(exc), "VALIDATION_ERROR")
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "IMM-01 create_needs_assessment")
        return _err(str(exc), "SERVER_ERROR")


@frappe.whitelist()
def get_needs_assessment(name: str) -> dict:
    """Fetch a single Needs Assessment by name."""
    if not frappe.db.exists("Needs Assessment", name):
        return _err(_("Không tìm thấy phiếu {0}").format(name), "NOT_FOUND")
    doc = frappe.get_doc("Needs Assessment", name)
    return _ok(doc.as_dict())


@frappe.whitelist()
def list_needs_assessments(
    status: str = "",
    dept: str = "",
    year: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List Needs Assessments with optional filters."""
    filters: dict = {}
    if status:
        filters["status"] = status
    if dept:
        filters["requesting_dept"] = dept
    if year:
        filters["request_date"] = ["between", [f"{year}-01-01", f"{year}-12-31"]]

    total = frappe.db.count("Needs Assessment", filters)
    items = frappe.get_list(
        "Needs Assessment",
        filters=filters,
        fields=["name", "requesting_dept", "equipment_type", "priority",
                "estimated_budget", "approved_budget", "status", "request_date"],
        order_by="request_date desc",
        start=(int(page) - 1) * int(page_size),
        page_length=int(page_size),
    )
    return _ok({"items": items, "total": total, "page": int(page)})


@frappe.whitelist()
def submit_for_review(name: str, approver: str = "") -> dict:
    """Transition Draft → Submitted, notify approver by email."""
    doc = _get_doc_or_error(name)
    if doc is None:
        return _err(_("Không tìm thấy phiếu {0}").format(name), "NOT_FOUND")
    if doc.status != "Draft":
        return _err(_("Phiếu phải ở trạng thái Draft"), "INVALID_STATE")
    if not approver:
        return _err(_("Vui lòng chọn người phê duyệt"), "VALIDATION_ERROR")
    doc.status = "Submitted"
    doc.approver = approver
    doc.save(ignore_permissions=False)
    send_approval_request(
        doctype="Needs Assessment",
        doc_name=doc.name,
        approver_user=approver,
        submitted_by=frappe.session.user,
        extra_info=f"{doc.equipment_type} — {doc.requesting_dept}",
    )
    return _ok({"name": doc.name, "status": doc.status})


@frappe.whitelist()
def begin_technical_review(name: str) -> dict:
    """Transition Submitted → Under Review (BR-01-02: HTM Manager bắt đầu xem xét kỹ thuật)."""
    doc = _get_doc_or_error(name)
    if doc is None:
        return _err(_("Không tìm thấy phiếu {0}").format(name), "NOT_FOUND")
    if doc.status != "Submitted":
        return _err(_("Phiếu phải ở trạng thái Submitted"), "INVALID_STATE")
    doc.status = "Under Review"
    # _log_lifecycle(doc, "technical_review_started", "Submitted", "Under Review")
    doc.save(ignore_permissions=False)
    return _ok({"name": doc.name, "status": doc.status})


@frappe.whitelist()
def approve_needs_assessment(name: str, approved_budget: float, notes: str = "") -> dict:
    """Approve a Needs Assessment — Under Review → Approved."""
    doc = _get_doc_or_error(name)
    if doc is None:
        return _err(_("Không tìm thấy phiếu {0}").format(name), "NOT_FOUND")
    if doc.status != "Under Review":
        return _err(_("Phiếu phải ở trạng thái Under Review"), "INVALID_STATE")
    if not doc.htmreview_notes:
        return _err(_("HTM Manager chưa điền nhận xét kỹ thuật"), "VALIDATION_ERROR")
    doc.approved_budget = float(approved_budget)
    doc.finance_notes = notes
    doc.status = "Approved"
    # _log_lifecycle(doc, "approved", "Under Review", "Approved", notes)
    doc.save(ignore_permissions=False)
    return _ok({"name": doc.name, "status": doc.status, "approved_budget": doc.approved_budget})


@frappe.whitelist()
def reject_needs_assessment(name: str, reason: str) -> dict:
    """Reject a Needs Assessment."""
    doc = _get_doc_or_error(name)
    if doc is None:
        return _err(_("Không tìm thấy phiếu {0}").format(name), "NOT_FOUND")
    if doc.status not in ("Submitted", "Under Review"):
        return _err(_("Chỉ có thể từ chối khi đang ở Submitted hoặc Under Review"), "INVALID_STATE")
    if not reason or len(reason.strip()) < 5:
        return _err(_("Lý do từ chối phải ít nhất 5 ký tự"), "VALIDATION_ERROR")
    doc.reject_reason = reason
    doc.status = "Rejected"
    # _log_lifecycle(doc, "rejected", doc.status, "Rejected", reason)
    doc.save(ignore_permissions=False)
    return _ok({"name": doc.name, "status": doc.status})


@frappe.whitelist()
def save_htmreview_notes(name: str, notes: str) -> dict:
    """Lưu nhận xét kỹ thuật HTM (cho phép edit khi Under Review)."""
    doc = _get_doc_or_error(name)
    if doc is None:
        return _err(_("Không tìm thấy phiếu {0}").format(name), "NOT_FOUND")
    if doc.status not in ("Submitted", "Under Review"):
        return _err(_("Chỉ có thể nhập nhận xét khi phiếu đang xét duyệt"), "INVALID_STATE")
    doc.htmreview_notes = notes
    doc.save(ignore_permissions=False)
    return _ok({"name": doc.name, "htmreview_notes": doc.htmreview_notes})


@frappe.whitelist()
def link_technical_spec(na_name: str, ts_name: str) -> dict:
    """Gắn Technical Specification có sẵn vào Needs Assessment."""
    if not frappe.db.exists("Needs Assessment", na_name):
        return _err(_("Không tìm thấy phiếu {0}").format(na_name), "NOT_FOUND")
    if not frappe.db.exists("Technical Specification", ts_name):
        return _err(_("Không tìm thấy đặc tả {0}").format(ts_name), "NOT_FOUND")
    frappe.db.set_value("Needs Assessment", na_name, "technical_specification", ts_name)
    frappe.db.set_value("Technical Specification", ts_name, "needs_assessment", na_name)
    return _ok({"na": na_name, "ts": ts_name})


@frappe.whitelist()
def get_dashboard_stats(year: str = "", dept: str = "") -> dict:
    """Return IMM-01 KPI dashboard statistics."""
    if not year:
        year = str(frappe.utils.getdate().year)
    date_range = [f"{year}-01-01", f"{year}-12-31"]

    base_filters: list = [["request_date", "between", date_range]]
    if dept and dept != "all":
        base_filters.append(["requesting_dept", "=", dept])

    records = frappe.get_list(
        "Needs Assessment",
        filters=base_filters,
        fields=["status", "estimated_budget", "approved_budget"],
        limit=10000,
    )

    by_status: dict = {}
    total_requested = total_approved = 0.0
    for r in records:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        total_requested += float(r.estimated_budget or 0)
        total_approved += float(r.approved_budget or 0)

    approved_count = by_status.get("Approved", 0) + by_status.get("Planned", 0)
    total = len(records)
    approval_rate = round(approved_count / total * 100, 1) if total else 0

    return _ok(
        {
            "total": total,
            "by_status": by_status,
            "total_requested_budget": total_requested,
            "total_approved_budget": total_approved,
            "approval_rate": approval_rate,
        }
    )


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _get_doc_or_error(name: str):
    """Return document or None."""
    if not frappe.db.exists("Needs Assessment", name):
        return None
    return frappe.get_doc("Needs Assessment", name)


# def _log_lifecycle(doc, event_type: str, from_status: str, to_status: str, notes: str = "") -> None:
#     """Append a lifecycle event row."""
#     doc.append(
#         "lifecycle_events",
#         {
#             "event_type": event_type,
#             "from_status": from_status,
#             "to_status": to_status,
#             "actor": frappe.session.user,
#             "event_timestamp": frappe.utils.now(),
#             "notes": notes,
#         },
#     )
