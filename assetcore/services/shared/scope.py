# Copyright (c) 2026, AssetCore Team
"""Scope / Separation-of-Duties helpers used across service layer.

AUTH-05 (4-eyes): provides reusable validator so the same user cannot fill
multiple signatory roles on the same record.
"""
from __future__ import annotations

from collections.abc import Iterable

import frappe

from .errors import ServiceError
from .constants import ErrorCode


def assert_distinct_signers(
    doc,
    *signer_fields: str,
    candidate_user: str | None = None,
    candidate_field: str | None = None,
    bypass_roles: Iterable[str] = ("AssetCore Super Admin",),
) -> None:
    """Raise ServiceError(FORBIDDEN) if `candidate_user` already occupies any
    of the `signer_fields` on `doc`.

    Args:
        doc: Frappe document (or dict) carrying the signer fields.
        signer_fields: field names whose values are user ids already assigned
            (e.g. "clinical_head", "qa_officer", "board_approver", "owner").
        candidate_user: user being proposed as the new signer. Defaults to
            `frappe.session.user`.
        candidate_field: optional field name we're about to fill — excluded
            from the cross-check (so "approve own pending" isn't blocked).
        bypass_roles: roles allowed to override SoD (Super Admin in fixtures).

    Why: NĐ98 separation-of-duties on Asset Commissioning (IMM-04). A single
    user cannot wear multiple "approver" hats (BGĐ + QA + Trưởng khoa) on the
    same phiếu. Without this gate, the IMM-04 acceptance workflow becomes a
    self-approval rubber stamp.
    """
    candidate_user = candidate_user or frappe.session.user
    if not candidate_user or candidate_user == "Guest":
        return

    user_roles = set(frappe.get_roles(candidate_user))
    if user_roles & set(bypass_roles):
        return

    occupied: list[tuple[str, str]] = []
    for fname in signer_fields:
        if fname == candidate_field:
            continue
        existing = doc.get(fname) if hasattr(doc, "get") else doc.get(fname)  # type: ignore[union-attr]
        if existing and existing == candidate_user:
            occupied.append((fname, existing))

    if occupied:
        labels = ", ".join(f"`{f}`" for f, _ in occupied)
        raise ServiceError(
            ErrorCode.FORBIDDEN,
            f"Separation-of-duties (4-eyes): bạn ({candidate_user}) đã ký ở "
            f"vai trò {labels} trên phiếu này; không thể đồng thời ký thêm vai khác.",
        )


def assert_not_self_submitter(
    doc,
    *,
    submitter_field: str = "owner",
    candidate_user: str | None = None,
    bypass_roles: Iterable[str] = ("AssetCore Super Admin",),
) -> None:
    """Raise ServiceError(FORBIDDEN) if the candidate user is the same as the
    record's original submitter — classic 4-eyes for approval steps.

    Used by IMM-04 `approve_pending` so a user cannot approve a phiếu they
    themselves authored / submitted.
    """
    candidate_user = candidate_user or frappe.session.user
    if not candidate_user or candidate_user == "Guest":
        return

    user_roles = set(frappe.get_roles(candidate_user))
    if user_roles & set(bypass_roles):
        return

    submitter = doc.get(submitter_field) if hasattr(doc, "get") else doc.get(submitter_field)  # type: ignore[union-attr]
    if submitter and submitter == candidate_user:
        raise ServiceError(
            ErrorCode.FORBIDDEN,
            f"Separation-of-duties (4-eyes): bạn ({candidate_user}) là người tạo "
            f"phiếu này — không thể tự duyệt. Yêu cầu người duyệt khác.",
        )


_VENDOR_ROLE = "Vendor Engineer"
_BYPASS_ROLES_FOR_SCOPE = ("AssetCore Super Admin", "AssetCore Auditor", "System Manager")
# Asset-link field per DocType (keyed by the doctype STRING the API passes, which
# for calibration is an alias, not the real DocType name). Field names verified
# against DB columns (SHOW COLUMNS):
#   • AC Asset → "name" (asset PK is the scope key itself).
#   • PM Work Order / Asset Repair → "asset_ref" (NOT "asset"! The real column is
#     `asset_ref`; querying "asset" raised Unknown-column 1054 at runtime, swallowed
#     by the resolver's bare except → vendor scope silently returned [] — fixed as
#     part of RC-LIST-VENDORCLOBBER).
#   • "Calibration Schedule"/"Calibration Record" are API aliases handled by the
#     IMM-11 service layer against the real `IMM Calibration Schedule`/`IMM Asset
#     Calibration` DocTypes whose asset column IS "asset" → keep field "asset".
#   • Incident Report → "asset".
_VENDOR_SCOPE_FIELD_MAP = {
    "AC Asset": "name",
    "PM Work Order": "asset_ref",
    "Asset Repair": "asset_ref",
    "Incident Report": "asset",
    "Calibration Schedule": "asset",
    "Calibration Record": "asset",
}


def _resolve_vendor_assigned_assets(user: str) -> list[str]:
    """Return list of asset names a Vendor Engineer is currently assigned to via WO.

    Reads the asset link from both ``PM Work Order`` and ``Asset Repair`` where the
    user is the ``assigned_to`` actor. **The asset link field on BOTH DocTypes is
    ``asset_ref`` (NOT ``asset``)** — verified against DocType JSON + DB columns
    (``SHOW COLUMNS``). Querying the non-existent ``asset`` column raised
    ``OperationalError(1054, "Unknown column 'asset'")`` which was swallowed by the
    bare ``except`` → resolver always returned ``[]`` → ``apply_vendor_scope`` forced
    the ``__none__`` sentinel (masked previously only because the reserved-prefix
    merge clobbered the ``name`` predicate). Fixed as part of RC-LIST-VENDORCLOBBER.
    """
    try:
        rows = frappe.db.sql(
            """
            SELECT DISTINCT asset_ref FROM `tabPM Work Order`
            WHERE assigned_to=%(u)s AND asset_ref IS NOT NULL AND asset_ref != ''
            UNION
            SELECT DISTINCT asset_ref FROM `tabAsset Repair`
            WHERE assigned_to=%(u)s AND asset_ref IS NOT NULL AND asset_ref != ''
            """,
            {"u": user},
            as_dict=False,
        )
    except Exception:
        return []
    return [r[0] for r in rows if r and r[0]]


_SCOPE_SENTINEL = "__none__"
#: Toán tử mà phép GIAO tính được **tĩnh** (0 truy vấn) từ danh sách asset đã được giao.
_POSITIVE_OPS = ("in", "=")
_NEGATIVE_OPS = ("not in", "!=")
_ALL_OPS = (
    "in", "not in", "between", "like", "not like", "=", "!=", "<", ">", "<=", ">=",
)


def _as_id_list(value) -> list[str]:
    """Giá trị (vô hướng hoặc list/tuple) → list mã, bỏ rỗng, GIỮ thứ tự, KHÔNG trùng."""
    raw = value if isinstance(value, (list, tuple, set)) else [value]
    out: list[str] = []
    for v in raw:
        s = str(v).strip()
        if s and s not in out:
            out.append(s)
    return out


def _intersect_in(existing, assigned: list[str]) -> list:
    """GIAO ràng buộc-theo-thiết-bị của caller với tập được-giao ⇒ ``["in", <list>]``.

    Vì sao tồn tại (AC-CR-106 — class-of-bug đo được, bản cũ dòng ``filters[field] =
    ["in", assigned]``): **GÁN** xoá sạch ý định của caller ⇒
      * Vendor Engineer deep-link ĐÚNG MỘT thiết bị (``?asset=A9``) nhận về **MỌI** phiếu
        của **MỌI** thiết bị họ được giao — rò dữ liệu so với yêu cầu, và người dùng tin
        rằng đang xem 1 thiết bị;
      * vỡ bất biến ``count == drill`` cho đúng persona đó (ô trên màn chi tiết đếm theo
        1 thiết bị, màn drill trả toàn bộ) — hai con số không bao giờ khớp.
    GIAO giữ CẢ HAI ràng buộc: phạm vi vendor (an ninh) ∧ ý định caller (nghiệp vụ).

    Shape ĐẦU VÀO phủ đủ 4 dạng đã gặp trên đường dây thật (luật run-4 «filter bị nuốt
    câm»): ``None``/khuyết/rỗng · **vô hướng** ``"A1"`` (FE deep-link) · ``["in", [...]]``
    / ``("in", [...])`` (vendor-scope + service nội bộ) · ``["=", "A1"]`` · list literal
    ``["A1","A2"]`` (mirror :func:`normalize_filters`).

    Shape ĐẦU RA **luôn** ``["in", list]`` — hạ nguồn không phải đoán:
    ``services/imm11.py::_extract_asset_in_scope`` (đã vá run-4) và
    ``_normalize_list_filters`` nhận đúng dạng này, nên GIAO không cần sửa IMM-11.

    Args:
        existing: giá trị filter của caller trên CHÍNH cột scope (có thể khuyết).
        assigned: tập mã asset được giao cho vendor (đã non-empty; có thể là sentinel).

    Returns:
        list: ``["in", <list mã>]``. Giao rỗng ⇒ ``["in", ["__none__"]]`` (0 dòng —
        **KHÔNG** fallback về ``assigned``, vì fallback đó chính là bug đang sửa).

    Op không giao được tĩnh (``like`` / ``between`` / so sánh) ⇒ **FAIL-CLOSED** về
    sentinel + ``frappe.logger`` cảnh báo (§10.4 dòng #8): phạm vi vendor là RANH GIỚI
    AN NINH, nên khi không tính được phần giao ta chọn 0 dòng (lỗi hiển thị HỮU HÌNH, FE
    có empty-state có ngữ cảnh) thay vì nới về "toàn bộ thiết bị của tôi" (rò dữ liệu
    CÂM). Nâng thành 400-in-envelope tường minh = nợ CÓ TÊN ``AC-CR-107`` (phải bọc
    ``try/except`` ở cả 5 call site trước, nếu không ``raise`` sẽ thoát envelope).
    Nhánh ``filters`` dạng LIST KHÔNG dùng helper này: ở đó hai điều kiện cùng field
    ANDed trong SQL đã LÀ phép giao (§10.4 cuối bảng) nên giữ nguyên cách ghép.
    """
    if existing is None:
        return ["in", list(assigned)]
    # Vô hướng (kể cả số) — deep-link 1 mã. Rỗng/khoảng trắng = KHÔNG ràng buộc.
    if not isinstance(existing, (list, tuple, set)):
        wanted = _as_id_list(existing)
        if not wanted:
            return ["in", list(assigned)]
        return ["in", [a for a in wanted if a in assigned] or [_SCOPE_SENTINEL]]

    seq = list(existing)
    if len(seq) == 2 and isinstance(seq[0], str) and seq[0].strip().lower() in _ALL_OPS:
        op = seq[0].strip().lower()
        vals = _as_id_list(seq[1])
        if op in _POSITIVE_OPS:
            keep = [a for a in vals if a in assigned]
        elif op in _NEGATIVE_OPS:
            keep = [a for a in assigned if a not in vals]
        else:
            # Không giao được tĩnh ⇒ fail-closed (xem docstring).
            frappe.logger("assetcore.scope").warning(
                "vendor_scope_unintersectable_op", extra={"op": op}
            )
            keep = []
        return ["in", keep or [_SCOPE_SENTINEL]]

    # List literal không mang toán tử ⇒ tập IN.
    wanted = _as_id_list(seq)
    if not wanted:
        return ["in", list(assigned)]
    return ["in", [a for a in wanted if a in assigned] or [_SCOPE_SENTINEL]]


def apply_vendor_scope(
    filters,
    doctype: str,
    user: str | None = None,
):
    """AUTH-01: Restrict list query to assets/WOs assigned to a Vendor Engineer.

    Non-vendor users (or bypass roles): filters returned unchanged.
    Vendor Engineer with empty scope: filtered to a sentinel that yields zero rows.

    AC-CR-106: ràng buộc vendor được **GIAO** với ràng buộc của caller
    (:func:`_intersect_in`), KHÔNG **GÁN** đè. Không có filter caller ⇒ kết quả y hệt
    hành vi cũ (``["in", assigned]``) ⇒ 0 hồi quy cho 5 call site
    (``api/imm00.py:413`` · ``api/imm08.py`` · ``api/imm09.py`` · ``api/imm11.py`` ×2).
    """
    user = user or frappe.session.user
    if not user or user == "Guest":
        return filters
    roles = set(frappe.get_roles(user))
    if _VENDOR_ROLE not in roles:
        return filters
    if roles & set(_BYPASS_ROLES_FOR_SCOPE):
        return filters
    field = _VENDOR_SCOPE_FIELD_MAP.get(doctype)
    if not field:
        return filters
    assigned = _resolve_vendor_assigned_assets(user) or [_SCOPE_SENTINEL]
    if isinstance(filters, dict):
        filters = dict(filters)
        filters[field] = _intersect_in(filters.get(field), assigned)
        return filters
    if isinstance(filters, list):
        # Filter-list form: hai điều kiện CÙNG field ANDed trong SQL **chính là** phép
        # giao (ADR-IMM00-LIST-SCOPE §10.4 — tiền lệ đã verify:
        # `services/imm00.py::compose_reserved_into` ghép `name in assigned` AND
        # `name not in reserved`). GIỮ NGUYÊN cách ghép ⇒ 0 hồi quy.
        # ⚠️ Nợ CÓ TÊN `AC-CR-109`: nhãn doctype spliced ở đây là chuỗi caller truyền —
        # với IMM-11 đó là **alias API** (`Calibration Schedule`/`Calibration Record`),
        # KHÔNG phải DocType thật (`IMM Calibration Schedule`/`IMM Asset Calibration`).
        # Hoãn được vì nhánh này **hiện không tới được** từ cả 5 call site prod (tất cả
        # truyền dict sau `parse_json`) — bất biến đó được khoá bằng test
        # `test_vendor_scope_intersect.py::test_ac_cr_109_list_branch_unreachable_...`.
        return list(filters) + [[doctype, field, "in", assigned]]
    # Unknown shape: wrap as dict (fail-closed — giữ nguyên hành vi cũ)
    return {field: ["in", assigned]}


def assert_vendor_can_access(doctype: str, name: str, user: str | None = None) -> None:
    """AUTH-10 IDOR guard for detail endpoints.

    Raises ServiceError(FORBIDDEN) when a Vendor Engineer user tries to access a
    record that does not belong to an asset assigned to them via PM/CM Work Order.
    """
    user = user or frappe.session.user
    if not user or user == "Guest":
        return
    roles = set(frappe.get_roles(user))
    if _VENDOR_ROLE not in roles:
        return
    if roles & set(_BYPASS_ROLES_FOR_SCOPE):
        return
    if doctype == "AC Asset":
        asset = name
    else:
        if doctype not in _VENDOR_SCOPE_FIELD_MAP:
            return
        # Asset link field is the doctype's scope field (e.g. PM WO/Asset Repair →
        # "asset_ref"), NOT a literal "asset" column. See _resolve_vendor_assigned_assets.
        asset = frappe.db.get_value(doctype, name, _VENDOR_SCOPE_FIELD_MAP[doctype])
        if not asset:
            return
    # PM Work Order / Asset Repair link the asset via column "asset_ref".
    is_assigned = frappe.db.exists(
        "PM Work Order", {"asset_ref": asset, "assigned_to": user}
    ) or frappe.db.exists(
        "Asset Repair", {"asset_ref": asset, "assigned_to": user}
    )
    if is_assigned:
        return
    raise ServiceError(
        ErrorCode.FORBIDDEN,
        "Bạn không có quyền truy cập tài sản này (không được giao việc).",
    )
