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
from assetcore.services.shared.permissions import rowscoped

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

# Ngưỡng "sắp hết hạn" của hồ sơ pháp lý (CR-75 §2.7.a B4) = tier `Critical` của
# `_ALERT_THRESHOLDS` — DẪN XUẤT, KHÔNG khai hằng số thứ hai (đổi tier ⇒ đổi theo).
_EXPIRING_SOON_DAYS = next(days for days, level in _ALERT_THRESHOLDS if level == "Critical")

# `document_status` nào coi là "còn tuân thủ" (CR-75 §2.7.a B7). `Expiring_Soon` là
# CẢNH BÁO, KHÔNG phải vi phạm ⇒ VẪN compliant.
_COMPLIANT_STATUSES = frozenset({"Compliant", "Compliant (Exempt)", "Expiring_Soon"})

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


def is_expired_row(row: dict, today: str | None = None) -> bool:
    """Cặp song sinh Python của `expired_filter()` — cho row ĐÃ nạp (INV-EXP-2).

    Ba mệnh đề, ĐÚNG thứ tự và ĐÚNG ngữ nghĩa của `expired_filter()`:
    ``expiry_date`` có giá trị (NULL-guard) ∧ ``expiry_date < today`` ∧
    ``workflow_state ∉ {Archived, Rejected}``. Đặt ngay dưới `expired_filter()` để
    hai predicate nằm cạnh nhau — đọc là thấy lệch (04 §4.4).

    **Never:** viết ``date_diff(...) < 0`` ở nơi khác · đọc cột đã lưu
    ``Asset Document.is_expired`` (stale từ lần save cuối) · để FE/mobile so ngày
    bằng đồng hồ máy (SSoT overdue = server flag).
    """
    expiry = row.get("expiry_date")
    if not expiry:
        return False
    if row.get("workflow_state") in _EXPIRED_EXCLUDED_STATES:
        return False
    return getdate(expiry) < getdate(today or nowdate())


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


@rowscoped
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
            # A5 (ADR-IMM00-LIST-SCOPE §8.4 + §8.3b): denorm-enrich tên hiển thị cho row
            # ĐÃ scoped ở tầng cha — lookup, KHÔNG phải bề mặt phân quyền (nếu "user",
            # Vendor Engineer mất tên thiết bị trên row họ ĐƯỢC xem = over-block).
            # "internal" (KHÔNG "system"): gate DocPerm read AC Asset ở đây cũng
            # over-block y hệt — persona đọc được Asset Document chưa chắc có DocPerm
            # read AC Asset, mà thứ trả ra chỉ là NHÃN của row họ đã được phép xem.
            scope="internal",
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

#: Field của DocItem trả về trong `documents` (05 §2.7 — 12 field DB + `is_expired`
#: dẫn xuất). `days_until_expiry` ĐƯỢC select nhưng LUÔN bị ghi đè bằng giá trị dẫn
#: xuất lúc đọc (BR-05-21); `is_expired` cột DB KHÔNG select (chống nhầm cột stale).
#: AC-CR-81: `file_attachment` (Attach, giá trị THÔ) được select CHỈ để tra `File` —
#: nó bị `pop` khỏi dòng trước khi trả (INV-FILE-8), KHÔNG BAO GIỜ ra response.
_DOSSIER_ROW_FIELDS = [
    "name", "doc_category", "doc_type_detail", "doc_number", "version",
    "workflow_state", "expiry_date", "days_until_expiry", "visibility",
    "is_exempt", "approved_by", "approval_date", "file_attachment",
]

#: Field tối thiểu cho truy vấn C (tính toán) — KHÔNG select `is_expired`.
#: ⚠ AC-CR-81 KHÔNG đụng danh sách này (AC4): 5 khoá tệp sinh HOÀN TOÀN trên nhánh V.
_DOSSIER_COMPUTE_FIELDS = ["doc_type_detail", "workflow_state", "expiry_date", "is_exempt"]

_DT_FILE = "File"

#: Khoá tệp phát ra MỖI dòng hồ sơ (AC-CR-81). Giá trị RỖNG là "" / 0 — KHÔNG None.
_EMPTY_FILE_META: dict = {
    "file_url": "", "file_name": "", "file_size": 0, "is_private": 0, "has_file": 0,
}


def _resolve_file_meta(urls: set[str]) -> dict[str, dict]:
    """{file_url → metadata} cho tập URL ĐÃ DEDUP — ĐÚNG 1 query `File` (INV-FILE-4).

    Hợp đồng: 05 §2.7.c F2/F3 · thực thi 04 §4.4-bis.

    `urls` PHẢI là URL của các dòng ĐƯỢC XEM (tập **V** đã lọc visibility) — KHÔNG bao
    giờ của tập **C** (INV-FILE-6: URL hồ sơ nội bộ không được rò qua khe tệp). Query
    chạy system-scope (`ignore_permissions=True`) vì `File` có mô hình quyền riêng
    (theo `attached_to_*`): persona KTV không có DocPerm `File` ⇒ query permission-aware
    trả rỗng và MỌI dòng sẽ `has_file=0` cho đúng nhóm dùng chính — dead-gate, cùng
    class-of-bug ADR-IMM09-SPARE-02. Chỉ đọc 4 field METADATA, KHÔNG đọc nội dung tệp,
    và chỉ cho URL người gọi ĐƯỢC XEM ⇒ không nới quyền.

    Args:
        urls: tập `file_attachment` non-empty của các dòng hiển thị (đã dedup).

    Returns:
        dict — CHỈ chứa URL có `File` doc thật. URL vắng mặt ⇒ **link mồ côi** ⇒
        call-site rơi về `_EMPTY_FILE_META` (`has_file=0` ∧ `file_url=""`).
    """
    if not urls:
        return {}                      # KHÔNG phát `IN ()` — 0 query khi tập rỗng
    rows = frappe.get_all(
        _DT_FILE,
        filters={"file_url": ["in", sorted(urls)]},
        fields=["file_url", "file_name", "file_size", "is_private"],
        order_by="creation asc",       # 2 File cùng URL ⇒ bản đầu tiên THẮNG (tất định)
        limit_page_length=0,
        ignore_permissions=True,
    )
    meta: dict[str, dict] = {}
    for r in rows:
        # `setdefault` giữ bản `creation` sớm nhất (đã sort) — KHÔNG ghi đè.
        meta.setdefault(r["file_url"], {
            "file_url": r["file_url"],
            # F4 — SSoT là `File.file_name`, KHÔNG phải cột denorm `file_name_display`
            # (cột đó tính lúc save từ chuỗi URL nên stale khi tệp bị thay).
            "file_name": r.get("file_name") or r["file_url"].rsplit("/", 1)[-1],
            # int() tường minh: bool lọt vào JSON không bị bắt lỗi nhưng làm vỡ
            # strict-deser Dart/Kotlin (INV-FILE-7, quirk CR-01).
            "file_size": int(r.get("file_size") or 0),
            "is_private": int(r.get("is_private") or 0),
            "has_file": 1,
        })
    return meta


def _applicable_required_types(asset_category: str | None) -> list[str]:
    """Mẫu số BR-05-17: loại hồ sơ **bắt buộc ÁP DỤNG** cho nhóm thiết bị của asset.

    ``applies(t, asset) ⟺ (not t.applies_to_asset_category)              # rỗng ⇒ mọi nhóm
                          or t.applies_to_asset_category == asset.asset_category``

    Trả list **đã sort A→Z** (output tất định — 3 mảng dẫn xuất kế thừa thứ tự này).

    [ROADMAP CR-75b] `applies_when_radiation` **KHÔNG** tham gia mẫu số vòng này:
    dữ liệu bức xạ nằm ở `AC Asset Category.has_radiation` (KHÔNG trên `AC Asset`)
    nên mở rộng sẽ đổi mẫu số của nhóm không bức xạ ⇒ ngoài phạm vi (05 §2.7.a B1).
    Tới lúc đó loại có `applies_when_radiation=1` xử lý NHƯ loại thường.
    """
    rows, _pg = RequiredDocumentTypeRepo.list(
        filters={"is_mandatory": 1},
        fields=["type_name", "applies_to_asset_category"],
        page_size=500,
    )
    return sorted({
        r["type_name"] for r in rows
        if not r.get("applies_to_asset_category")
        or r["applies_to_asset_category"] == asset_category
    })


def _dossier_compliance(docs: list[dict], required_types: list[str],
                        today: str | None = None) -> dict:
    """Thuật toán chuẩn CR-75 (05 §2.7.a B3–B6) trên tập doc ĐÃ NẠP — 0 query.

    ``live(t) = {d : d.doc_type_detail == t ∧ d.workflow_state == 'Active'
                     ∧ ¬is_expired_row(d)}``

    ===============================================  ==========================
    Điều kiện                                        Kết quả
    ===============================================  ==========================
    ``live(t) ≠ ∅``                                  ``t`` satisfied
    ``live(t) = ∅`` ∧ ∃ d Active đã quá hạn          ``t ∈ expired_required``
    ``live(t) = ∅`` ∧ không có bản Active nào        ``t ∈ missing_required``
    ===============================================  ==========================

    INV-DOC-2: ``missing ∩ expired = ∅`` ∧ ``|missing| + |expired| = total − satisfied``.

    ⚠ **Đối số THU HẸP tại call-site** (chặn dương-tính-giả, 04 §4.3 "Never sửa hàm
    SSoT"): `has_expiring`/`is_exempt` trả về ở đây ĐÃ được thu hẹp bằng điều kiện
    "hồ sơ đủ" (`satisfied == total` ∧ không có loại quá hạn) nên
    `_compute_document_status` giữ nguyên thứ tự nhánh mà vẫn thoả INV-DOC-3
    (`is_compliant ⟺ pct == 100`):
      * KHÔNG thu hẹp `has_expiring` ⇒ hồ sơ THIẾU (pct 50) mà có 1 loại sắp hết hạn
        sẽ báo `Expiring_Soon` (nhánh `has_expiring` đứng TRƯỚC `pct >= 100`) ⇒
        `is_compliant = 1` cho hồ sơ chưa đủ — đúng loại lỗi CR-75 phải khử.
      * `expiring_required[]` VẪN phát đầy đủ (dữ liệu không mất, chỉ đổi mức ưu tiên
        của *trạng thái tổng*: thiếu hồ sơ nặng hơn sắp-hết-hạn).
    """
    today = today or nowdate()
    by_type: dict[str, list[dict]] = {}
    for d in docs:
        by_type.setdefault(d.get("doc_type_detail") or "", []).append(d)

    satisfied: list[str] = []
    missing: list[str] = []
    expired: list[str] = []
    expiring: list[str] = []
    exempt_cover = False

    for t in required_types:
        actives = [d for d in by_type.get(t, [])
                   if d.get("workflow_state") == DocState.ACTIVE]
        live = [d for d in actives if not is_expired_row(d, today)]
        if not live:
            (expired if actives else missing).append(t)
            continue
        satisfied.append(t)
        # B4 — cover(t) = max(days) trên live; bản KHÔNG có expiry_date ⇒ +∞
        # (không bao giờ "sắp hết hạn") nên chỉ xét khi MỌI bản live đều có hạn.
        covers = [date_diff(d["expiry_date"], today) for d in live if d.get("expiry_date")]
        if len(covers) == len(live) and max(covers) <= _EXPIRING_SOON_DAYS:
            expiring.append(t)
        if any(int(d.get("is_exempt") or 0) for d in live):
            exempt_cover = True

    total = len(required_types)
    satisfied_count = len(satisfied)
    # B5 — mẫu số rỗng ⇒ 100 (KHÔNG chia 0).
    pct = 100 if total == 0 else int(round(satisfied_count / total * 100))
    full_cover = total > 0 and satisfied_count == total and not expired

    return {
        "required_total": total,
        "required_satisfied": satisfied_count,
        "completeness_pct": pct,
        "missing_required": sorted(missing),
        "expired_required": sorted(expired),
        "expiring_required": sorted(expiring),
        "has_expired": bool(expired),
        "has_expiring": bool(expiring) and full_cover,
        "is_exempt": bool(exempt_cover) and full_cover and not expiring,
    }


@rowscoped
def get_asset_documents(asset: str) -> dict:
    """Hồ sơ pháp lý theo Asset — mức đầy đủ TÍNH THẬT + trạng thái XÉT HIỆU LỰC.

    CR-75 (05 §2.7/§2.7.a, 04 §4.4). Trước CR-75 hàm trả `completeness_pct` hằng 0
    và `document_status ∈ {Complete, Incomplete}` chỉ đo SỰ-CÓ-MẶT ⇒ hồ sơ bắt buộc
    ĐÃ QUÁ HẠN vẫn báo "Complete" (dương-tính-giả NĐ98 Điều 41).

    Thứ tự truy vấn BẮT BUỘC (B8): **V trước C**.
      * **V** (hiển thị, `scope="user"`) giữ role-gate/row-scope ⇒ user thiếu DocPerm
        read nhận `PermissionError` **trước** khi tới C ⇒ `@rowscoped` trả 403
        in-envelope trên HTTP-200 (KHÔNG 4xx/500 câm).
      * **C** (tính toán, `scope="internal"`) là aggregate org-truth: tỷ lệ tuân thủ
        KHÔNG phụ thuộc người xem (BR-05-20 / ADR-IMM05-03). `hidden_count = |C| − |V|`
        bộc lộ số bản bị ẩn (minh bạch phân quyền).

    Args:
        asset: `AC Asset.name`.

    Returns:
        dict — MỌI khoá luôn xuất hiện (kể cả mảng rỗng): `asset`, `required_total`,
        `required_satisfied`, `completeness_pct` (0..100), `document_status`
        (enum SSoT 5 giá trị), `is_compliant` (0|1), `missing_required`,
        `expired_required`, `expiring_required`, `hidden_count`, `documents`
        (grouped-object theo `doc_category`, mỗi dòng có `is_expired` 0|1 và
        `days_until_expiry` DẪN XUẤT lúc đọc).

        AC-CR-81 (05 §2.7.c) — MỖI dòng còn có ĐỦ 5 khoá TỆP `file_url` (str, ""),
        `file_name` (str, ""), `file_size` (int BYTE, 0), `is_private` (int 0|1),
        `has_file` (int 0|1), batch-resolve 1 lần qua `_resolve_file_meta`. Link mồ
        côi ⇒ `has_file=0` ∧ `file_url=""` (KHÔNG phát link chết); `file_attachment`
        THÔ bị `pop`, không bao giờ ra response.
    """
    if not AssetRepo.exists(asset):
        nthrow(MSG.IMM05_ASSET_NOT_FOUND, asset=asset)

    today = nowdate()

    # (V) hiển thị — permission-aware, LỌC visibility.
    visible, _pg = DocumentRepo.list(
        filters=_apply_visibility_filter({"asset_ref": asset}),
        fields=_DOSSIER_ROW_FIELDS,
        order_by="doc_category asc, workflow_state asc",
        page_size=500,
    )

    # (C) tính toán — KHÔNG lọc visibility (aggregate org-truth, ADR-IMM05-03).
    all_docs, _pg_all = DocumentRepo.list(
        filters={"asset_ref": asset},
        fields=_DOSSIER_COMPUTE_FIELDS,
        page_size=500,
        scope="internal",
    )

    # 1 query cho nhóm thiết bị (KHÔNG N+1 — mọi phân loại chạy trên tập đã nạp).
    asset_category = frappe.db.get_value("AC Asset", asset, "asset_category")
    compliance = _dossier_compliance(all_docs, _applicable_required_types(asset_category), today)

    # SSoT enum 5 giá trị — lazy-import (Pattern B cross-module, tránh circular).
    from assetcore.assetcore.doctype.asset_document.asset_document import (
        _compute_document_status,
    )
    document_status = _compute_document_status(
        compliance["completeness_pct"],
        compliance["has_expiring"],
        compliance["has_expired"],
        compliance["is_exempt"],
    )

    # AC-CR-81 (05 §2.7.c F2) — batch-resolve tệp: ĐÚNG 1 query `File` cho toàn payload,
    # tập vào là URL của tập **V** (đã lọc visibility) ⇒ 0 rò URL dòng bị ẩn (INV-FILE-6).
    file_meta = _resolve_file_meta(
        {(d.get("file_attachment") or "").strip() for d in visible} - {""}
    )

    grouped: dict = {}
    for d in visible:
        row = dict(d)
        # THÔ không bao giờ ra response (INV-FILE-8 + closed-schema OAS).
        raw_url = (row.pop("file_attachment", "") or "").strip()
        # Mồ côi / chưa đính ⇒ 5 khoá RỖNG — KHÔNG phát link chết (INV-FILE-2/3).
        row.update(file_meta.get(raw_url) or _EMPTY_FILE_META)
        # BR-05-21 — dẫn xuất LÚC ĐỌC (server clock), KHÔNG đọc cột đã lưu.
        row["is_expired"] = int(is_expired_row(row, today))
        row["days_until_expiry"] = (
            date_diff(row["expiry_date"], today) if row.get("expiry_date") else None
        )
        grouped.setdefault(row.get("doc_category") or "Other", []).append(row)

    return {
        "asset": asset,
        "required_total": compliance["required_total"],
        "required_satisfied": compliance["required_satisfied"],
        "completeness_pct": compliance["completeness_pct"],
        "document_status": document_status,
        # Khoá MÁY-ĐỌC: consumer KHÔNG phải so chuỗi (khử class-of-bug dead-branch).
        "is_compliant": int(document_status in _COMPLIANT_STATUSES),
        "missing_required": compliance["missing_required"],
        "expired_required": compliance["expired_required"],
        "expiring_required": compliance["expiring_required"],
        "hidden_count": max(len(all_docs) - len(visible), 0),
        "documents": grouped,
    }


# ─── Dashboards & KPIs ────────────────────────────────────────────────────────

@rowscoped
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


@rowscoped
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


@rowscoped
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
