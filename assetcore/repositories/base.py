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
    ) -> tuple[list[dict], dict]:
        """Trả (rows, pagination_meta)."""
        total = cls.count(filters)
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
