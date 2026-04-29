# Copyright (c) 2026, AssetCore Team
# IMM-05 Documents — Tier 2 Business Service Layer.

from __future__ import annotations

import json

import frappe
from frappe.utils import add_days, date_diff, getdate, nowdate

from assetcore.repositories.asset_repo import AssetRepo
from assetcore.repositories.document_repo import (
    DocumentRepo,
    DocumentRequestRepo,
    ExpiryAlertLogRepo,
    RequiredDocumentTypeRepo,
)
from assetcore.services.shared import ErrorCode, Roles, ServiceError, has_any_role

# ─── Constants cho visibility / workflow states ───────────────────────────────

class DocState:
    DRAFT = "Draft"
    PENDING_REVIEW = "Pending_Review"
    ACTIVE = "Active"
    ARCHIVED = "Archived"
    EXPIRED = "Expired"
    REJECTED = "Rejected"


class Visibility:
    PUBLIC = "Public"
    INTERNAL_ONLY = "Internal_Only"


# Legacy hospital roles (hospital workflow — dùng song song IMM roles)
_LEGACY_QA = "IMM QA Officer"
_LEGACY_ADMIN = "IMM System Admin"
_LEGACY_BIOMED = "IMM Biomed Technician"
_LEGACY_WORKSHOP = "IMM Workshop Lead"
_LEGACY_HTM_TECH = "IMM Technician"
_LEGACY_SYSTEM_MGR = "System Manager"

_INTERNAL_VIEW_ROLES = {
    Roles.SYS_ADMIN, Roles.QA, Roles.DEPT_HEAD, Roles.OPS_MANAGER,
    Roles.WORKSHOP, Roles.TECHNICIAN, Roles.DOC_OFFICER,
    _LEGACY_HTM_TECH, _LEGACY_QA, _LEGACY_BIOMED,
    _LEGACY_WORKSHOP, _LEGACY_ADMIN, _LEGACY_SYSTEM_MGR,
}
_APPROVE_ROLES = {
    Roles.SYS_ADMIN, Roles.QA, Roles.DEPT_HEAD, Roles.OPS_MANAGER,
    _LEGACY_BIOMED, _LEGACY_QA, _LEGACY_ADMIN,
}
_EXEMPT_ROLES = {
    Roles.SYS_ADMIN, Roles.QA, Roles.OPS_MANAGER,
    _LEGACY_QA, _LEGACY_ADMIN, _LEGACY_WORKSHOP,
}

_ALERT_THRESHOLDS = [(7, "Danger"), (30, "Critical"), (60, "Warning"), (90, "Info")]


# ─── Access control helpers ───────────────────────────────────────────────────

def _can_see_internal() -> bool:
    if frappe.session.user in ("Administrator", "admin"):
        return True
    return has_any_role(_INTERNAL_VIEW_ROLES)


def _apply_visibility_filter(filters: dict) -> dict:
    if not _can_see_internal():
        return {**filters, "visibility": ["in", [Visibility.PUBLIC, "", None]]}
    return filters


def _require_approve_role() -> None:
    if not has_any_role(_APPROVE_ROLES):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền duyệt/từ chối tài liệu")


def _require_exempt_role() -> None:
    if not has_any_role(_EXEMPT_ROLES):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền đánh dấu Exempt")


# ─── Scheduler ────────────────────────────────────────────────────────────────

def check_document_expiry() -> dict:
    """Scheduler daily: tạo Expiry Alert Log cho tài liệu sắp hết hạn."""
    today = getdate(nowdate())
    created, skipped = 0, 0

    docs, _pg = DocumentRepo.list(
        filters={"expiry_date": ["is", "set"], "is_expired": 0},
        fields=["name", "asset_ref", "doc_type_detail", "expiry_date"],
        page_size=10_000,
    )
    for doc in docs:
        expiry = getdate(doc["expiry_date"])
        days_remaining = date_diff(expiry, today)
        if days_remaining < 0:
            DocumentRepo.set_values(doc["name"], {"is_expired": 1})
            continue
        level = _resolve_alert_level(days_remaining)
        if not level:
            continue
        if ExpiryAlertLogRepo.exists({"asset_document": doc["name"], "alert_date": nowdate()}):
            skipped += 1
            continue
        try:
            ExpiryAlertLogRepo.create({
                "asset_document": doc["name"],
                "asset_ref": doc["asset_ref"],
                "doc_type_detail": doc["doc_type_detail"],
                "expiry_date": doc["expiry_date"],
                "days_remaining": days_remaining,
                "alert_level": level,
                "alert_date": nowdate(),
            })
            created += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"IMM-05 expiry alert failed: {doc['name']}")

    frappe.db.commit()
    result = {"created": created, "skipped": skipped}
    frappe.logger().info(f"IMM-05 check_document_expiry: {result}")
    return result


def _resolve_alert_level(days_remaining: int) -> str | None:
    for threshold, level in _ALERT_THRESHOLDS:
        if days_remaining <= threshold:
            return level
    return None


# ─── Documents CRUD + workflow ────────────────────────────────────────────────

_LIST_FIELDS = [
    "name", "asset_ref", "doc_category", "doc_type_detail",
    "doc_number", "version", "workflow_state", "expiry_date",
    "days_until_expiry", "visibility", "is_exempt", "modified",
]


def list_documents(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    f = _apply_visibility_filter(filters or {})
    rows, pg = DocumentRepo.list(
        filters=f, fields=_LIST_FIELDS,
        page=page, page_size=page_size,
    )
    asset_ids = {r.get("asset_ref") for r in rows if r.get("asset_ref")}
    if asset_ids:
        arows, _ = AssetRepo.list(
            filters={"name": ("in", list(asset_ids))},
            fields=["name", "asset_name"],
            page_size=len(asset_ids),
        )
        amap = {a["name"]: a.get("asset_name") for a in arows}
        for r in rows:
            r["asset_name"] = amap.get(r.get("asset_ref"), "")
    return {"items": rows, "pagination": pg}


def get_document(name: str) -> dict:
    doc = DocumentRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy tài liệu: {name}")
    if doc.visibility == Visibility.INTERNAL_ONLY and not _can_see_internal():
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền xem tài liệu này")
    data = doc.as_dict()
    if data.get("asset_ref"):
        data["asset_name"] = frappe.db.get_value("AC Asset", data["asset_ref"], "asset_name") or ""
    return data


def create_document(data: dict) -> dict:
    data.setdefault("workflow_state", DocState.DRAFT)
    data.setdefault("version", "1.0")
    try:
        doc = DocumentRepo.create(data, ignore_permissions=False)
    except frappe.ValidationError as e:
        raise ServiceError(ErrorCode.VALIDATION, str(e)) from e
    return {"name": doc.name, "workflow_state": doc.workflow_state}


def update_document(name: str, patch: dict) -> dict:
    doc = DocumentRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")
    if doc.workflow_state not in (DocState.DRAFT, DocState.REJECTED):
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Chỉ có thể sửa khi ở Draft hoặc Rejected. Hiện tại: {doc.workflow_state}",
        )
    doc = DocumentRepo.update_fields(name, patch, ignore_permissions=False)
    return {"name": doc.name, "modified": str(doc.modified)}


def approve_document(name: str) -> dict:
    _require_approve_role()
    doc = DocumentRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")
    if doc.workflow_state != DocState.PENDING_REVIEW:
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Chỉ Approve từ Pending_Review. Hiện tại: {doc.workflow_state}",
        )

    # Archive các bản Active cũ của cùng (asset, doc_type_detail)
    old_docs, _ = DocumentRepo.list(
        filters={
            "asset_ref": doc.asset_ref,
            "doc_type_detail": doc.doc_type_detail,
            "workflow_state": DocState.ACTIVE,
            "name": ("!=", name),
        },
        fields=["name"],
        page_size=100,
    )
    for old in old_docs:
        DocumentRepo.set_values(old["name"], {"workflow_state": DocState.ARCHIVED})

    doc.workflow_state = DocState.ACTIVE
    doc.approved_by = frappe.session.user
    doc.approval_date = nowdate()
    doc.flags.ignore_links = True
    DocumentRepo.save(doc)
    return {"name": name, "new_state": DocState.ACTIVE, "approved_by": frappe.session.user}


def reject_document(name: str, rejection_reason: str) -> dict:
    if not rejection_reason:
        raise ServiceError(ErrorCode.VALIDATION, "Lý do từ chối là bắt buộc (VR-06)")
    _require_approve_role()
    doc = DocumentRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")
    if doc.workflow_state != DocState.PENDING_REVIEW:
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Chỉ Reject từ Pending_Review. Hiện tại: {doc.workflow_state}",
        )
    DocumentRepo.update_fields(name, {
        "workflow_state": DocState.REJECTED,
        "rejection_reason": rejection_reason,
    })
    return {"name": name, "new_state": DocState.REJECTED}


# ─── Asset-centric views ──────────────────────────────────────────────────────

def get_asset_documents(asset: str) -> dict:
    if not AssetRepo.exists(asset):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Asset: {asset}")

    filters = _apply_visibility_filter({"asset_ref": asset})
    docs, _pg = DocumentRepo.list(
        filters=filters,
        fields=["name", "doc_category", "doc_type_detail", "doc_number",
                "version", "workflow_state", "expiry_date", "days_until_expiry",
                "visibility", "is_exempt", "approved_by", "approval_date"],
        order_by="doc_category asc, workflow_state asc",
        page_size=500,
    )

    grouped: dict = {}
    for d in docs:
        cat = d.get("doc_category") or "Other"
        grouped.setdefault(cat, []).append(d)

    required_rows, _ = RequiredDocumentTypeRepo.list(
        filters={"is_mandatory": 1},
        fields=["type_name"],
        page_size=500,
    )
    required_types = [r["type_name"] for r in required_rows]
    active_types = {d["doc_type_detail"] for d in docs if d["workflow_state"] == DocState.ACTIVE}
    missing = [t for t in required_types if t not in active_types]

    return {
        "asset": asset,
        "completeness_pct": 0,
        "document_status": "Incomplete" if missing else "Complete",
        "documents": grouped,
        "missing_required": missing,
    }


# ─── Dashboards & KPIs ────────────────────────────────────────────────────────

def get_dashboard_stats() -> dict:
    total_active = DocumentRepo.count({"workflow_state": DocState.ACTIVE})
    expired_not_renewed = DocumentRepo.count({"workflow_state": DocState.EXPIRED})

    ninety_days = add_days(nowdate(), 90)
    # Dùng SQL 1 lần cho câu hỏi "sắp hết hạn trong 90 ngày" + "số assets missing docs"
    expiring_90d = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabAsset Document`
        WHERE workflow_state = 'Active'
          AND expiry_date IS NOT NULL
          AND expiry_date <= %s
          AND expiry_date > CURDATE()
    """, ninety_days)[0][0]
    assets_missing = frappe.db.sql("""
        SELECT COUNT(DISTINCT asset_ref) FROM `tabAsset Document`
        WHERE workflow_state != 'Active'
    """)[0][0]

    timeline, _ = DocumentRepo.list(
        filters={
            "workflow_state": DocState.ACTIVE,
            "expiry_date": ["between", [nowdate(), ninety_days]],
        },
        fields=["name", "asset_ref", "doc_type_detail", "expiry_date", "days_until_expiry"],
        order_by="expiry_date asc",
        page_size=20,
    )

    try:
        dept_stats = frappe.db.sql("""
            SELECT
                a.location as dept,
                COUNT(DISTINCT a.name) as total_assets,
                SUM(CASE WHEN EXISTS (
                    SELECT 1 FROM `tabAsset Document` d
                    WHERE d.asset_ref = a.name AND d.workflow_state = 'Active'
                ) THEN 1 ELSE 0 END) as compliant
            FROM `tabAC Asset` a
            WHERE a.lifecycle_status != 'Decommissioned'
              AND a.location IS NOT NULL
            GROUP BY a.location
            ORDER BY compliant DESC
            LIMIT 15
        """, as_dict=True)
        for row in dept_stats:
            total = row.get("total_assets") or 0
            row["pct"] = round((row.get("compliant") or 0) / total * 100, 1) if total else 0
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-05 dept_stats query failed")
        dept_stats = []

    return {
        "kpis": {
            "total_active": total_active,
            "expiring_90d": expiring_90d,
            "expired_not_renewed": expired_not_renewed,
            "assets_missing_docs": assets_missing,
        },
        "expiry_timeline": list(timeline),
        "compliance_by_dept": dept_stats,
    }


def get_expiring_documents(days: int = 90) -> dict:
    days = min(365, max(1, int(days)))
    target = add_days(nowdate(), days)
    docs, _ = DocumentRepo.list(
        filters={
            "workflow_state": DocState.ACTIVE,
            "expiry_date": ["between", [nowdate(), target]],
        },
        fields=["name", "asset_ref", "doc_category", "doc_type_detail",
                "expiry_date", "days_until_expiry", "issuing_authority"],
        order_by="expiry_date asc",
        page_size=1000,
    )
    return {"days": days, "count": len(docs), "items": docs}


def get_compliance_by_dept() -> list[dict]:
    try:
        rows = frappe.db.sql("""
            SELECT
                a.location as dept,
                COUNT(DISTINCT a.name) as total_assets,
                SUM(CASE WHEN EXISTS (
                    SELECT 1 FROM `tabAsset Document` d
                    WHERE d.asset_ref = a.name AND d.workflow_state = 'Active'
                ) THEN 1 ELSE 0 END) as compliant,
                SUM(CASE WHEN NOT EXISTS (
                    SELECT 1 FROM `tabAsset Document` d
                    WHERE d.asset_ref = a.name AND d.workflow_state = 'Active'
                ) AND EXISTS (
                    SELECT 1 FROM `tabAsset Document` d2
                    WHERE d2.asset_ref = a.name AND d2.workflow_state = 'Draft'
                ) THEN 1 ELSE 0 END) as incomplete,
                SUM(CASE WHEN EXISTS (
                    SELECT 1 FROM `tabAsset Document` d
                    WHERE d.asset_ref = a.name AND d.workflow_state = 'Rejected'
                ) THEN 1 ELSE 0 END) as non_compliant,
                SUM(CASE WHEN EXISTS (
                    SELECT 1 FROM `tabAsset Document` d
                    WHERE d.asset_ref = a.name AND d.workflow_state = 'Active'
                      AND d.expiry_date IS NOT NULL
                      AND d.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 90 DAY)
                ) THEN 1 ELSE 0 END) as expiring_soon
            FROM `tabAC Asset` a
            WHERE a.lifecycle_status != 'Decommissioned' AND a.location IS NOT NULL
            GROUP BY a.location
            ORDER BY compliant DESC
        """, as_dict=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-05 get_compliance_by_dept failed")
        return []

    for r in rows:
        total = r.get("total_assets") or 0
        r["pct"] = round((r.get("compliant") or 0) / total * 100, 1) if total else 0
    return rows


# ─── Document history (wrap Frappe Version) ───────────────────────────────────

def get_document_history(name: str) -> dict:
    if not DocumentRepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")

    versions = frappe.get_all(
        "Version",
        filters={"ref_doctype": DocumentRepo.DOCTYPE, "docname": name},
        fields=["name", "creation", "owner", "data"],
        order_by="creation asc",
    )
    history = []
    for v in versions:
        try:
            vdata = json.loads(v.data) if isinstance(v.data, str) else (v.data or {})
        except (ValueError, TypeError):
            vdata = {}
        changed = vdata.get("changed", [])
        workflow_changes = [c for c in changed if c[0] == "workflow_state"]
        history.append({
            "timestamp": str(v.creation),
            "user": v.owner,
            "action": "Workflow Transition" if workflow_changes else "Field Update",
            "from_state": workflow_changes[0][1] if workflow_changes else None,
            "to_state": workflow_changes[0][2] if workflow_changes else None,
            "changes": [
                {"field": c[0], "old": c[1], "new": c[2]}
                for c in changed if c[0] != "workflow_state"
            ],
        })
    return {"name": name, "history": history}


# ─── Document Requests ────────────────────────────────────────────────────────

def create_document_request(*, asset_ref: str, doc_type_required: str,
                             doc_category: str = "Legal",
                             assigned_to: str | None = None,
                             due_date: str | None = None,
                             priority: str = "Medium",
                             request_note: str = "",
                             source_type: str = "Manual") -> dict:
    if not AssetRepo.exists(asset_ref):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Asset: {asset_ref}")
    assigned_to = assigned_to or frappe.session.user
    due_date = due_date or add_days(nowdate(), 30)

    req = DocumentRequestRepo.create({
        "asset_ref": asset_ref,
        "doc_type_required": doc_type_required,
        "doc_category": doc_category,
        "assigned_to": assigned_to,
        "due_date": due_date,
        "priority": priority,
        "request_note": request_note,
        "source_type": source_type,
        "status": "Open",
    })
    return {"name": req.name, "status": req.status}


def get_document_requests(asset_ref: str = "", status: str = "") -> dict:
    filters: dict = {}
    if asset_ref:
        filters["asset_ref"] = asset_ref
    if status:
        filters["status"] = status
    items, _ = DocumentRequestRepo.list(
        filters=filters,
        fields=["name", "asset_ref", "doc_type_required", "doc_category",
                "assigned_to", "due_date", "status", "priority",
                "escalation_sent", "source_type", "fulfilled_by"],
        order_by="due_date asc",
        page_size=500,
    )
    return {"count": len(items), "items": items}


# ─── Exempt Marking (GAP-02) ──────────────────────────────────────────────────

def mark_exempt(*, asset_ref: str, doc_type_detail: str,
                exempt_reason: str, exempt_proof: str) -> dict:
    _require_exempt_role()
    if not AssetRepo.exists(asset_ref):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Asset: {asset_ref}")
    if not exempt_reason or not exempt_proof:
        raise ServiceError(ErrorCode.VALIDATION,
                           "exempt_reason và exempt_proof là bắt buộc")
    doc = DocumentRepo.create({
        "asset_ref": asset_ref,
        "doc_category": "Legal",
        "doc_type_detail": doc_type_detail,
        "doc_number": f"EXEMPT-{asset_ref}",
        "version": "1.0",
        "issued_date": nowdate(),
        "file_attachment": exempt_proof,
        "is_exempt": 1,
        "exempt_reason": exempt_reason,
        "exempt_proof": exempt_proof,
        "visibility": Visibility.PUBLIC,
        "workflow_state": DocState.ACTIVE,
        "approved_by": frappe.session.user,
        "approval_date": nowdate(),
        "source_module": "IMM-05-Exempt",
    })
    return {
        "document_name": doc.name,
        "is_exempt": True,
        "workflow_state": doc.workflow_state,
    }
