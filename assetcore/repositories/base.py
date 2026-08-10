# Copyright (c) 2026, AssetCore Team
"""Generic repository base class cho Frappe DocType.

Service layer dùng `BaseRepository` subclasses thay vì gọi thẳng `frappe.db.*`.
Pagination luôn đi qua `assetcore.utils.pagination.paginate` để hành vi nhất quán.
"""
from __future__ import annotations

from typing import Any, ClassVar

import frappe

from assetcore.utils.pagination import paginate

DEFAULT_FIELDS = ["name"]
DEFAULT_ORDER = "modified desc"

# ── Row-scope mode cho BaseRepository.list (ADR-IMM00-LIST-SCOPE §8.3/§8.3b) ─
# SSoT 3 chế độ. KHÔNG rải literal ở call site — import hằng số.
#
# HAI trục quyền ĐỘC LẬP (đừng gộp — chính chỗ gộp đã sinh lỗ A01 2026-07-25):
#   • ROLE-scope  = DocPerm `read` trên DocType   ("vai trò nào được đọc bảng này")
#   • ROW-scope   = permission_query_conditions + User Permission ("dòng nào của tôi")
#
#   scope        ROLE-scope   ROW-scope   engine              dùng cho
#   ───────────  ──────────   ─────────   ─────────────────   ───────────────────────
#   "user"       ✔ enforce    ✔ enforce   frappe.get_list     list phiếu-của-tôi
#   "system"     ✔ enforce    ✘ bỏ        frappe.get_all      device/plan-centric,
#                                          (+ gate role)       KPI kỳ báo cáo
#   "internal"   ✘ bỏ         ✘ bỏ        frappe.get_all      scheduler / domain-logic
#                                                              / denorm-enrich lookup
LIST_SCOPE_USER = "user"
LIST_SCOPE_SYSTEM = "system"
LIST_SCOPE_INTERNAL = "internal"
_LIST_SCOPES = (LIST_SCOPE_USER, LIST_SCOPE_SYSTEM, LIST_SCOPE_INTERNAL)
# Nhánh KHÔNG áp row-scope nhưng VẪN phải qua DocPerm read cấp vai trò.
_ROLE_GATED_SCOPES = (LIST_SCOPE_SYSTEM,)


class BaseRepository:
    """Subclass và set `DOCTYPE` để tạo repository cho 1 DocType cụ thể."""

    DOCTYPE: ClassVar[str] = ""

    # ── Read ──────────────────────────────────────────────────────────

    @classmethod
    def exists(cls, name: str | dict) -> bool:
        """Kiểm tra tồn tại — chấp nhận name hoặc filters dict."""
        return bool(frappe.db.exists(cls.DOCTYPE, name))

    @classmethod
    def get(cls, name: str):
        """Return Document hoặc None nếu không tồn tại."""
        if not frappe.db.exists(cls.DOCTYPE, name):
            return None
        return frappe.get_doc(cls.DOCTYPE, name)

    @classmethod
    def get_value(cls, name: str, field: str | list[str], *, as_dict: bool = False):
        """Lấy 1 hoặc nhiều field. `as_dict=True` khi field là list."""
        return frappe.db.get_value(cls.DOCTYPE, name, field, as_dict=as_dict)

    @classmethod
    def count(cls, filters: dict | None = None) -> int:
        return frappe.db.count(cls.DOCTYPE, filters or {})

    @classmethod
    def list(
        cls,
        filters: dict | None = None,
        *,
        fields: list[str] | None = None,
        or_filters: list | None = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str = DEFAULT_ORDER,
        scope: str = LIST_SCOPE_USER,
    ) -> tuple[list[dict], dict]:
        """Trả (rows, pagination_meta) — ``total`` và ``rows`` LUÔN cùng một engine.

        INVARIANT **INV-ROWSCOPE** (ADR-IMM00-LIST-SCOPE §8.3): ``pagination.total``
        và ``rows`` PHẢI đi qua CÙNG MỘT engine truy vấn ⇒ ``total == len(rows)`` khi
        ``total <= page_size``, đúng ở CẢ 2 chế độ.

        ============== ===================================== ============================
        ``scope``      ``total``                              ``rows``
        ============== ===================================== ============================
        ``"user"``     ``count_with_or`` → ``frappe.get_list`` ``frappe.get_list`` (scoped)
        ``"system"``   ``count_ignore_permissions`` → get_all  ``frappe.get_all``  (raw)
        ``"internal"`` ``count_ignore_permissions`` → get_all  ``frappe.get_all``  (raw)
        ============== ===================================== ============================

        ``"system"`` và ``"internal"`` DÙNG CHUNG engine nhưng KHÁC nhau đúng một
        thứ: ``"system"`` chạy :func:`assert_doctype_read_permission` TRƯỚC (giữ
        DocPerm read cấp vai-trò), ``"internal"`` thì không. Xem §8.3b.

        Vì sao phải tham-số-hoá (bug production 2 CHIỀU, cùng một root cause):
          - §1 — count thô (``frappe.db.count``) > rows scoped ⇒ header "Tổng 1430"
            nhưng bảng RỖNG cho persona row-scoped.
          - §8 — sau khi count chuyển sang ``get_list`` (permission-aware) mà rows vẫn
            ``get_all``: count scoped **<** rows thô ⇒ KTV **ĐỌC ĐƯỢC PHIẾU KHÔNG ĐƯỢC
            GIAO** (rò dữ liệu row-level) và "đọc được nhưng không ghi được" — read-gate
            lệch write-gate (``_assert_can_attach_repair_photo``).

        Ghi chú de-risk: MỌI call site hiện tại ĐÃ chạy ``frappe.get_list`` một lần cho
        ``total`` ⇒ DocPerm read đã được enforce sẵn ở mọi call site. Chuyển rows sang
        ``get_list`` CHỈ CỘNG THÊM ``permission_query_conditions`` + User Permission vào
        rows — **KHÔNG mở ra bề mặt PermissionError mới**.

        ⚠️ **``"system"`` KHÔNG phải "bỏ hết quyền"** (finding A01 2026-07-25):
        ``frappe.get_all`` bỏ CẢ row-scope LẪN DocPerm read cấp vai-trò, trong khi
        ADR §8.2 **D6 chỉ ratify nới ROW-scope**. Vì vậy nhánh ``"system"`` gate
        tường minh :func:`~assetcore.services.shared.permissions.assert_doctype_read_permission`
        trước khi truy vấn — user không có DocPerm read trên DocType KHÔNG được
        phục vụ dòng nào (trước fix: ``PM User`` đọc được toàn bộ ``Asset Repair``).
        Trường hợp thật sự cần bỏ mọi kiểm tra (scheduler không có session-user,
        domain-logic nội bộ, denorm-enrich tên hiển thị cho row ĐÃ scoped ở tầng
        cha) → khai ``"internal"`` để ý-định-hiện-ra-mặt-chữ, KHÔNG mượn ``"system"``.

        Args:
            scope: ``"user"`` (mặc định — **fail-safe**: call site quên khai báo thì bị
                SIẾT chứ không bị NỚI), ``"system"`` hoặc ``"internal"``. Giá trị khác
                → ``ValueError`` ngay (fail-fast, chống typo ``"System"`` biến thành
                silent-permissive).

        Raises:
            ValueError: ``scope`` không thuộc ``{"user", "system", "internal"}``.
            frappe.PermissionError: ``scope="user"`` hoặc ``"system"`` mà session-user
                thiếu DocPerm read ⇒ **call site người-dùng PHẢI bọc**
                :func:`~assetcore.services.shared.permissions.run_rowscoped`
                (BR-00-ROWSCOPE-403: 403 trên HTTP-200, KHÔNG 500 câm).
        """
        if scope not in _LIST_SCOPES:
            raise ValueError(
                f"BaseRepository.list: scope={scope!r} không hợp lệ — "
                f"chỉ chấp nhận {_LIST_SCOPES} (ADR-IMM00-LIST-SCOPE §8.3)"
            )
        from assetcore.services.shared.filters import count_ignore_permissions, count_with_or

        if scope in _ROLE_GATED_SCOPES:
            # Trục ROLE-scope — giữ nguyên kể cả khi trục ROW-scope được nới (D6).
            from assetcore.services.shared.permissions import assert_doctype_read_permission
            assert_doctype_read_permission(cls.DOCTYPE)

        if scope == LIST_SCOPE_USER:
            total = count_with_or(cls.DOCTYPE, filters, or_filters)
            pg = paginate(total, page, page_size)
            rows = frappe.get_list(
                cls.DOCTYPE,
                filters=filters or {},
                or_filters=or_filters,
                fields=fields or DEFAULT_FIELDS,
                order_by=order_by,
                limit_start=pg["offset"],
                limit_page_length=pg["page_size"],
            )
            return rows, pg

        total = count_ignore_permissions(cls.DOCTYPE, filters, or_filters)
        pg = paginate(total, page, page_size)
        rows = frappe.get_all(
            cls.DOCTYPE,
            filters=filters or {},
            or_filters=or_filters,
            fields=fields or DEFAULT_FIELDS,
            order_by=order_by,
            limit_start=pg["offset"],
            limit_page_length=pg["page_size"],
        )
        return rows, pg

    @classmethod
    def find_one(cls, filters: dict, fields: list[str] | None = None) -> dict | None:
        rows = frappe.get_all(
            cls.DOCTYPE, filters=filters, fields=fields or DEFAULT_FIELDS,
            limit_page_length=1,
        )
        return rows[0] if rows else None

    # ── Write ─────────────────────────────────────────────────────────

    @classmethod
    def create(cls, data: dict, *, ignore_permissions: bool = True):
        """Tạo và insert document mới."""
        doc = frappe.get_doc({"doctype": cls.DOCTYPE, **data})
        doc.insert(ignore_permissions=ignore_permissions)
        return doc

    @classmethod
    def save(cls, doc, *, ignore_permissions: bool = True):
        """Save document hiện có."""
        if ignore_permissions:
            doc.flags.ignore_permissions = True
        doc.save()
        return doc

    @classmethod
    def set_values(cls, name: str, patch: dict) -> None:
        """Update nhiều field bằng set_value (không trigger validate)."""
        frappe.db.set_value(cls.DOCTYPE, name, patch)

    @classmethod
    def update_fields(cls, name: str, patch: dict, *, ignore_permissions: bool = True):
        """Update bằng doc.save() để trigger validate + hooks."""
        doc = frappe.get_doc(cls.DOCTYPE, name)
        for field, value in patch.items():
            doc.set(field, value)
        if ignore_permissions:
            doc.flags.ignore_permissions = True
        doc.save()
        return doc

    @classmethod
    def delete(cls, name: str, *, ignore_permissions: bool = True) -> None:
        frappe.delete_doc(cls.DOCTYPE, name, ignore_permissions=ignore_permissions)

    @classmethod
    def submit(cls, name: str):
        """Submit submittable document."""
        doc = frappe.get_doc(cls.DOCTYPE, name)
        doc.submit()
        return doc
