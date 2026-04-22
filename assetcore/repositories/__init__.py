# Copyright (c) 2026, AssetCore Team
"""Tier 3 — Data Access layer.

Mỗi repository wrap 1 DocType với interface gọn: get/list/create/update/delete/exists/count.
Service layer chỉ gọi repository; không import `frappe.db` hay `frappe.get_doc` trực tiếp.

Exception: transaction boundary (`frappe.db.commit()`) vẫn nằm ở service.
"""
from .base import BaseRepository

__all__ = ["BaseRepository"]
