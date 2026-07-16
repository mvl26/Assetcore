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
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.services.shared import rbac
from assetcore.utils.notify import MSG, nthrow

# ─── Constants cho visibility / workflow states ───────────────────────────────

class DocState:
    DRAFT = "Draft"
    PENDING_REVIEW = "Pending Review"
    ACTIVE = "Active"
    ARCHIVED = "Archived"
    EXPIRED = "Expired"
    REJECTED = "Rejected"


class Visibility:
    PUBLIC = "Public"
    INTERNAL_ONLY = "Internal_Only"


# ─── State machine — SoT next-state (khớp fixtures/workflow.json 'IMM-05 Document
# Workflow') ──────────────────────────────────────────────────────────────────
# Server-driven CTA (GATE-8 / LL-FE-51): get_document emit `allowed_transitions =
# _DOC_VALID_TRANSITIONS.get(workflow_state, [])` để FE gate nút CTA theo tập này
# (+ capability doc.approve cho Phê duyệt/Từ chối/Lưu trữ) THAY hardcode
# `workflow_state === 'X'` — hết false-permissive (nút hiện rồi bấm mới 403) và hết
# dead-gate. next_state PHẢI trùng transitions trong fixture — invariant test
# `test_get_document_allowed_transitions_matches_workflow_fixture` chốt equality
# nên thêm/sửa transition mà quên map → đỏ.
#   Draft → Pending Review (Gửi duyệt) | Archived (Hủy bỏ)
#   Pending Review → Active (Phê duyệt) | Rejected (Từ chối)
#   Rejected → Pending Review (Gửi lại)
#   Active → Archived (Lưu trữ)
#   Archived / Expired → [] (trạng thái cuối)
_DOC_VALID_TRANSITIONS: dict[str, list[str]] = {
    DocState.DRAFT: [DocState.PENDING_REVIEW, DocState.ARCHIVED],
    DocState.PENDING_REVIEW: [DocState.ACTIVE, DocState.REJECTED],
    DocState.ACTIVE: [DocState.ARCHIVED],
    DocState.REJECTED: [DocState.PENDING_REVIEW],
    DocState.ARCHIVED: [],
    DocState.EXPIRED: [],
}


_ALERT_THRESHOLDS = [(7, "Danger"), (30, "Critical"), (60, "Warning"), (90, "Info")]

# ─── SoT predicate "Đã hết hạn" (BR-05-16 / INV-EXP-1) ────────────────────────
# RC-EXP (count-vs-drill divergence): KPI 'expired_not_renewed' và drill
# list_documents PHẢI dùng Y HỆT 1 predicate. Trước đây KPI đếm theo
# expiry_date<today thuần còn drill lọc workflow_state='Expired' (dead-state —
# KHÔNG transition nào dẫn vào) → drill rỗng, giấu hồ sơ quá hạn còn hiệu lực
# (NĐ98 Điều 41: thiết bị vận hành với giấy phép hết hạn PHẢI hiện).
#
# Predicate DUY NHẤT:
#   expiry_date IS NOT NULL AND expiry_date < today
#   AND workflow_state NOT IN ('Archived','Rejected')
# - Archived/Rejected dù quá hạn KHÔNG đếm (không phải compliance-gap còn sống).
# - Active/Draft/Pending Review quá hạn ĐẾM (live gap NĐ98). Biên expiry==today
#   CHƯA < today → chưa expired.
#
# ⚠ NULL-guard TƯỜNG MINH bắt buộc (LL-BE-EXP-1): `frappe.db.count` và
# `frappe.get_all` xử lý `["<", date]` với hàng NULL KHÁC NHAU — `db.count`
# (query_builder) loại NULL còn `get_all` (DatabaseQuery) bọc `ifnull()` nên
# hàng `expiry_date=NULL` LẠI khớp `< today`. Nếu predicate KHÔNG có
# `["expiry_date","is","set"]`, count (db.count) != drill (get_all) ngay khi tồn
# tại 1 doc NULL-expiry còn-sống → tái lập đúng count-vs-drill divergence. Vì vậy
# dùng dạng **list-of-conditions** (đồng nhất trên CẢ HAI API) + NULL-guard.
_EXPIRED_EXCLUDED_STATES = [DocState.ARCHIVED, DocState.REJECTED]

# FE phát biểu Ý ĐỊNH bằng marker semantic này; BE vật chất hóa thành predicate
# qua `expired_filter()` (không để FE tự tính date — tránh client/server skew).
_EXPIRY_STATUS_MARKER = "expiry_status"


def expired_filter(today: str | None = None) -> list[list]:
    """SoT predicate 'Đã hết hạn' — dùng CHUNG cho count (KPI) lẫn drill (list).

    BR-05-16 / INV-EXP-1: cả `get_dashboard_stats` (count, `frappe.db.count`) lẫn
    `list_documents` (drill, `frappe.get_all` qua marker ``expiry_status='expired'``)
    tiêu thụ predicate này → count == len(drill items) cho MỌI tập dữ liệu (chênh=0).

    Trả **list-of-conditions** ``[[field, op, value], ...]`` (KHÔNG dict): chỉ dạng
    này cho kết quả ĐỒNG NHẤT trên `db.count` và `get_all` khi có hàng NULL-expiry
    (xem ghi chú NULL-guard phía trên). NULL-guard ``["expiry_date","is","set"]`` là
    BẮT BUỘC, không phải tuỳ chọn.
    """
    return [
        ["expiry_date", "is", "set"],
        ["expiry_date", "<", today or nowdate()],
        ["workflow_state", "not in", _EXPIRED_EXCLUDED_STATES],
    ]


def _dict_to_conditions(filters: dict) -> list[list]:
    """Chuyển Frappe filter dict sang list-of-conditions để AND với `expired_filter()`.

    - giá trị thường ``"Active"`` → ``["field", "=", "Active"]``
    - operator-tuple ``["not in", [...]]`` / ``["in", [...]]`` → ``["field", op, value]``
    Cùng ngữ nghĩa AND như dict gốc, nhưng dạng list đồng nhất với SoT predicate.
    """
    conditions: list[list] = []
    for field, value in (filters or {}).items():
        if isinstance(value, (list, tuple)) and len(value) == 2 and isinstance(value[0], str):
            conditions.append([field, value[0], value[1]])
        else:
            conditions.append([field, "=", value])
    return conditions


# ─── Access control helpers (capability, KHONG so ten role) ───────────────────

def _can_see_internal() -> bool:
    if frappe.session.user in ("Administrator", "admin"):
        return True
    return rbac.can("document" + ".read")


def _apply_visibility_filter(filters: dict) -> dict:
    if not _can_see_internal():
        return {**filters, "visibility": ["in", [Visibility.PUBLIC, "", None]]}
    return filters


def _require_approve_role() -> None:
    if not rbac.can("doc.approve"):
        nthrow(MSG.IMM05_FORBIDDEN_APPROVE)


def _require_exempt_role() -> None:
    if not rbac.can("document" + ".write"):
        nthrow(MSG.IMM05_FORBIDDEN_EXEMPT)


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
    "approved_by",
]


def list_documents(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    f = dict(filters or {})
    # BR-05-16: marker semantic `expiry_status` (KHÔNG phải field DB) → BE là nơi
    # DUY NHẤT vật chất hóa predicate compliance NĐ98 (FE chỉ phát biểu ý định).
    # Pop trước khi build Frappe filter; dịch 'expired' sang SoT `expired_filter()`
    # — CÙNG predicate KPI count dùng (INV-EXP-1: count == len(drill items)).
    expired = f.pop(_EXPIRY_STATUS_MARKER, "") == "expired"
    f = _apply_visibility_filter(f)
    if expired:
        # `expired_filter()` là list-of-conditions (NULL-guard đồng nhất 2 API) nên
        # KHÔNG merge được vào dict → gộp toàn bộ về list-of-conditions: các filter
        # dict còn lại (doc_category, asset_ref, visibility...) AND với SoT predicate.
        f = _dict_to_conditions(f) + expired_filter()
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
    # BE-DC-05-01: enrich approved_by_name
    approver_ids = {r.get("approved_by") for r in rows if r.get("approved_by")}
    if approver_ids:
        umap: dict[str, str] = {}
        try:
            user_rows = frappe.get_all(
                "User",
                filters={"name": ("in", list(approver_ids))},
                fields=["name", "full_name"],
            )
            umap = {u["name"]: u.get("full_name") or u["name"] for u in user_rows}
        except Exception:
            umap = {}
        for r in rows:
            r["approved_by_name"] = umap.get(r.get("approved_by"), "")
    # doc_type_name alias for FE consistency (Link field display)
    for r in rows:
        r.setdefault("doc_type_name", r.get("doc_type_detail") or "")
    return {"items": rows, "pagination": pg}


def get_document(name: str) -> dict:
    doc = DocumentRepo.get(name)
    if not doc:
        nthrow(MSG.IMM05_DOC_NOT_FOUND, name=name)
    if doc.visibility == Visibility.INTERNAL_ONLY and not _can_see_internal():
        nthrow(MSG.IMM05_FORBIDDEN_VIEW)
    data = doc.as_dict()
    if data.get("asset_ref"):
        data["asset_name"] = frappe.db.get_value("AC Asset", data["asset_ref"], "asset_name") or ""
    # Server-driven CTA (GATE-8 / LL-FE-51): FE gate nút chuyển trạng thái theo tập
    # này + can_approve, KHÔNG hardcode workflow_state===. `.get(..., [])` → trạng
    # thái lạ / None degrade an toàn thành "không nút".
    data["allowed_transitions"] = _DOC_VALID_TRANSITIONS.get(doc.workflow_state, [])
    data["can_approve"] = int(rbac.can("doc.approve"))
    return data


def create_document(data: dict) -> dict:
    data.setdefault("workflow_state", DocState.DRAFT)
    data.setdefault("version", "1.0")
    try:
        doc = DocumentRepo.create(data, ignore_permissions=False)
    except frappe.ValidationError as e:
        nthrow(MSG.IMM05_VALIDATION, detail=str(e))
    return {"name": doc.name, "workflow_state": doc.workflow_state}


def submit_for_review(name: str) -> dict:
    """Transition từ Draft/Rejected → Pending Review (VR-03: file bắt buộc)."""
    doc = DocumentRepo.get(name)
    if not doc:
        nthrow(MSG.IMM05_DOC_NOT_FOUND, name=name)
    if doc.workflow_state not in (DocState.DRAFT, DocState.REJECTED):
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Chỉ gửi duyệt từ Draft hoặc Rejected. Hiện tại: {doc.workflow_state}",
        )
    if not doc.file_attachment:
        nthrow(MSG.IMM05_FILE_REQUIRED)
    doc.workflow_state = DocState.PENDING_REVIEW
    doc.flags.ignore_links = True
    DocumentRepo.save(doc)
    return {"name": name, "new_state": DocState.PENDING_REVIEW}


def update_document(name: str, patch: dict) -> dict:
    doc = DocumentRepo.get(name)
    if not doc:
        nthrow(MSG.IMM05_DOC_NOT_FOUND, name=name)
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
        nthrow(MSG.IMM05_DOC_NOT_FOUND, name=name)
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
        nthrow(MSG.IMM05_REJECT_REASON_REQUIRED)
    _require_approve_role()
    doc = DocumentRepo.get(name)
    if not doc:
        nthrow(MSG.IMM05_DOC_NOT_FOUND, name=name)
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


def archive_document(name: str, reason: str = "") -> dict:
    """Manual archive (04_Backend_Design.md:151-152).

    - "Lưu trữ": Active  → Archived
    - "Hủy bỏ":  Draft   → Archived
    NĐ98 Điều 41: document never deleted, only archived (retention 10 năm).
    """
    _require_approve_role()
    doc = DocumentRepo.get(name)
    if not doc:
        nthrow(MSG.IMM05_DOC_NOT_FOUND, name=name)
    if doc.workflow_state not in (DocState.ACTIVE, DocState.DRAFT):
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Chỉ lưu trữ từ Active hoặc Draft. Hiện tại: {doc.workflow_state}",
        )
    patch: dict = {
        "workflow_state": DocState.ARCHIVED,
        "archive_date": nowdate(),
    }
    if reason:
        patch["change_summary"] = reason
    DocumentRepo.update_fields(name, patch)
    return {"name": name, "new_state": DocState.ARCHIVED}


# ─── Asset-centric views ──────────────────────────────────────────────────────

def get_asset_documents(asset: str) -> dict:
    if not AssetRepo.exists(asset):
        nthrow(MSG.IMM05_ASSET_NOT_FOUND, asset=asset)

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
    # RC-EXP: KPI "Đã hết hạn" đếm theo SoT predicate `expired_filter()` —
    # CÙNG predicate (cùng list-of-conditions, gồm NULL-guard) với drill
    # list_documents (kill count-vs-drill divergence). Đếm mọi doc quá hạn còn
    # hiệu lực (Active/Draft/Pending Review) NHƯNG loại Archived/Rejected (không
    # phải compliance-gap còn sống) và doc expiry_date NULL (không có hạn).
    expired_not_renewed = DocumentRepo.count(expired_filter())

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
        nthrow(MSG.IMM05_DOC_NOT_FOUND, name=name)

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
        nthrow(MSG.IMM05_ASSET_NOT_FOUND, asset=asset_ref)
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
        nthrow(MSG.IMM05_ASSET_NOT_FOUND, asset=asset_ref)
    if not exempt_reason or not exempt_proof:
        nthrow(MSG.IMM05_VALIDATION, detail="exempt_reason và exempt_proof là bắt buộc")
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
