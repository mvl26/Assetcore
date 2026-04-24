# Copyright (c) 2026, AssetCore Team
# Service layer cho Module IMM-06 — Bàn giao & Đào tạo.
# Controller gọi vào đây; không có business logic trong controller.

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _paginate(doctype: str, filters: dict, fields: list[str],
              page: int, page_size: int) -> dict:
    """Generic paginated query."""
    total = frappe.db.count(doctype, filters)
    items = frappe.db.get_all(
        doctype,
        filters=filters,
        fields=fields,
        limit_page_length=page_size,
        limit_start=(page - 1) * page_size,
        order_by="modified desc",
    )
    import math
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


# ─── READ ─────────────────────────────────────────────────────────────────────

def get_handover_record(name: str) -> dict:
    """Return full Handover Record with linked Training Sessions.

    Args:
        name: Handover Record name.

    Returns:
        dict: record data + training_sessions list.
    """
    doc = frappe.get_doc("Handover Record", name)
    sessions = frappe.db.get_all(
        "Training Session",
        filters={"handover_ref": name, "docstatus": ("!=", 2)},
        fields=["name", "training_type", "training_date", "trainer",
                "status", "competency_confirmed", "duration_hours"],
        order_by="training_date desc",
    )
    for s in sessions:
        s["trainees_count"] = frappe.db.count("Training Trainee", {"parent": s["name"]})
        s["passed_count"] = frappe.db.count("Training Trainee", {"parent": s["name"], "passed": 1})

    events = frappe.db.get_all(
        "Asset Lifecycle Event",
        filters={"root_record": name, "root_doctype": "Handover Record"},
        fields=["name", "event_type", "timestamp", "actor", "from_status", "to_status", "notes"],
        order_by="timestamp desc",
    )
    return {**doc.as_dict(), "training_sessions": sessions, "lifecycle_events": events}


def list_handover_records(
    status: str | None = None,
    dept: str | None = None,
    asset: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List Handover Records with optional filters and pagination.

    Args:
        status: Filter by status.
        dept: Filter by clinical_dept.
        asset: Filter by asset.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        dict: Paginated result.
    """
    filters: dict = {"docstatus": ("!=", 2)}
    if status:
        filters["status"] = status
    if dept:
        filters["clinical_dept"] = dept
    if asset:
        filters["asset"] = asset
    fields = ["name", "asset", "clinical_dept", "handover_date",
              "received_by", "handover_type", "status", "modified"]
    return _paginate("Handover Record", filters, fields, int(page), int(page_size))


def get_asset_training_history(asset_name: str) -> dict:
    """Return all Training Sessions for a given asset.

    Args:
        asset_name: AC Asset name.

    Returns:
        dict: sessions list and summary stats.
    """
    sessions = frappe.db.get_all(
        "Training Session",
        filters={"asset": asset_name, "docstatus": ("!=", 2)},
        fields=["name", "training_type", "training_date", "trainer",
                "trainer_type", "status", "competency_confirmed", "duration_hours"],
        order_by="training_date desc",
    )
    total_trained = 0
    for s in sessions:
        count = frappe.db.count("Training Trainee", {"parent": s["name"]})
        s["trainees_count"] = count
        total_trained += count
    return {
        "asset": asset_name,
        "sessions": sessions,
        "total_sessions": len(sessions),
        "total_trained": total_trained,
    }


def get_dashboard_stats() -> dict:
    """Return KPI summary for IMM-06 dashboard.

    Returns:
        dict: KPI counts.
    """
    from frappe.utils import get_first_day, get_last_day, getdate
    today = getdate(nowdate())
    first_day = get_first_day(today)
    last_day = get_last_day(today)

    pending = frappe.db.count(
        "Handover Record", {"status": "Handover Pending", "docstatus": ("!=", 2)}
    )
    completed_month = frappe.db.count(
        "Handover Record",
        {
            "status": "Handed Over",
            "handover_date": ["between", [first_day, last_day]],
        },
    )
    training_scheduled = frappe.db.count(
        "Training Session", {"status": "Scheduled", "docstatus": ("!=", 2)}
    )
    # Average days Draft → Handed Over
    rows = frappe.db.sql(
        """
        SELECT DATEDIFF(handover_date, creation) AS days
        FROM `tabHandover Record`
        WHERE status = 'Handed Over'
          AND handover_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
        """,
        as_dict=True,
    )
    avg_days = round(sum(r.days for r in rows if r.days) / len(rows), 1) if rows else 0.0

    # Training pass rate
    total_trainees = frappe.db.count("Training Trainee", {})
    passed_trainees = frappe.db.count("Training Trainee", {"passed": 1, "attendance": "Present"})
    pass_rate = round((passed_trainees / total_trainees) * 100, 1) if total_trainees else 0.0

    return {
        "total_pending_handover": pending,
        "completed_this_month": completed_month,
        "training_scheduled": training_scheduled,
        "avg_days_to_handover": avg_days,
        "training_pass_rate": pass_rate,
    }


# ─── WRITE ───────────────────────────────────────────────────────────────────

def create_handover_record(
    commissioning_ref: str,
    clinical_dept: str,
    handover_date: str,
    received_by: str,
    handover_type: str = "Full",
) -> dict:
    """Create a new Handover Record.

    Args:
        commissioning_ref: Asset Commissioning name.
        clinical_dept: AC Department name.
        handover_date: Date string YYYY-MM-DD.
        received_by: User email.
        handover_type: Full / Conditional / Temporary.

    Returns:
        dict: Created Handover Record fields.
    """
    doc = frappe.get_doc({
        "doctype": "Handover Record",
        "commissioning_ref": commissioning_ref,
        "clinical_dept": clinical_dept,
        "handover_date": handover_date,
        "received_by": received_by,
        "handover_type": handover_type,
        "status": "Draft",
    })
    doc.insert(ignore_permissions=False)
    return {
        "name": doc.name,
        "asset": doc.asset,
        "clinical_dept": doc.clinical_dept,
        "handover_date": doc.handover_date,
        "workflow_state": doc.workflow_state,
        "status": doc.status,
    }


def schedule_training(
    handover_name: str,
    training_type: str,
    trainer: str,
    training_date: str,
    duration_hours: float = 0.0,
    trainees: list | None = None,
) -> dict:
    """Create a Training Session linked to a Handover Record.

    Args:
        handover_name: Handover Record name.
        training_type: Operation/Safety/Emergency/Maintenance/Full.
        trainer: User email.
        training_date: Date string YYYY-MM-DD.
        duration_hours: Session length in hours.
        trainees: List of {trainee_user, role} dicts.

    Returns:
        dict: Created Training Session fields.
    """
    trainees = trainees or []
    handover = frappe.get_doc("Handover Record", handover_name)
    session = frappe.get_doc({
        "doctype": "Training Session",
        "handover_ref": handover_name,
        "asset": handover.asset,
        "training_type": training_type,
        "trainer_type": "HTM",
        "trainer": trainer,
        "training_date": training_date,
        "duration_hours": duration_hours,
        "status": "Scheduled",
        "trainees": [
            {"trainee_user": t.get("trainee_user"), "role": t.get("role", ""), "attendance": "Present"}
            for t in trainees
        ],
    })
    session.insert(ignore_permissions=False)

    # Transition handover to Training Scheduled if still Draft
    if handover.status == "Draft":
        handover.db_set("status", "Training Scheduled", commit=True)

    return {
        "name": session.name,
        "handover_ref": handover_name,
        "training_type": training_type,
        "training_date": training_date,
        "status": "Scheduled",
    }


def complete_training(
    training_session_name: str,
    scores: list | None = None,
    notes: str = "",
) -> dict:
    """Mark a Training Session as Completed and record trainee scores.

    Args:
        training_session_name: Training Session name.
        scores: List of {trainee_user, score, passed} dicts.
        notes: Session completion notes.

    Returns:
        dict: Updated Training Session summary.
    """
    scores = scores or []
    session = frappe.get_doc("Training Session", training_session_name)
    score_map = {s["trainee_user"]: s for s in scores}

    for row in session.trainees:
        if row.trainee_user in score_map:
            s = score_map[row.trainee_user]
            row.score = s.get("score", 0)
            row.passed = 1 if s.get("passed") else 0

    session.notes = notes or session.notes
    session.status = "Completed"
    session.save(ignore_permissions=False)

    passed_count = sum(1 for t in session.trainees if t.passed and t.attendance == "Present")
    total = len([t for t in session.trainees if t.attendance == "Present"])
    return {
        "name": session.name,
        "status": "Completed",
        "competency_confirmed": bool(session.competency_confirmed),
        "passed_count": passed_count,
        "total_trainees": total,
    }


def confirm_handover(
    name: str,
    dept_head_signoff: str,
    notes: str = "",
) -> dict:
    """Confirm handover: set signoff, validate, and submit.

    Args:
        name: Handover Record name.
        dept_head_signoff: User email of Dept Head.
        notes: Optional handover notes.

    Returns:
        dict: Submitted record info.
    """
    doc = frappe.get_doc("Handover Record", name)
    if not dept_head_signoff:
        frappe.throw(_("VR-04: Bắt buộc có chữ ký Trưởng khoa trước khi hoàn tất bàn giao."))

    doc.dept_head_signoff = dept_head_signoff
    if notes:
        doc.handover_notes = (doc.handover_notes or "") + f"\n{notes}"
    doc.status = "Handed Over"
    doc.workflow_state = "Handed Over"
    doc.save(ignore_permissions=False)
    doc.submit()

    # Find lifecycle event created by on_submit
    event = frappe.db.get_value(
        "Asset Lifecycle Event",
        {"root_record": name, "event_type": "handover_completed"},
        "name",
    )
    return {
        "name": doc.name,
        "status": "Handed Over",
        "docstatus": doc.docstatus,
        "dept_head_signoff": dept_head_signoff,
        "lifecycle_event": event,
    }
