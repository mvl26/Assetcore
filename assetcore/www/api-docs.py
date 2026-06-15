# Copyright (c) 2026, AssetCore Team
"""Frappe website entry point — trang Swagger UI cho OpenAPI spec (D7).

Render `api-docs.html` nhúng Swagger UI self-host (`public/swagger-ui/`, air-gapped — KHÔNG CDN
ngoài) trỏ vào endpoint `assetcore.api.openapi.spec`. Gate trang theo session (precedent
`www/assetcore.py`): Guest → đẩy về login (endpoint spec ĐÃ session-gate riêng ở api/openapi.py,
trang chỉ là vỏ UI; gate ở đây để khách không thấy khung tài liệu trống/redirect mượt hơn).

KHÔNG modify core, KHÔNG đụng response.py — chỉ get_context cấp asset path + login_required.
"""
from __future__ import annotations

import frappe

no_cache = 1


def get_context(context: dict) -> None:
    """Gate trang theo session: Guest → redirect login.

    Asset path Swagger UI self-host (`/assets/assetcore/swagger-ui/*`) + spec_url
    (`/api/method/assetcore.api.openapi.spec`) là HẰNG TĨNH → nhúng thẳng trong
    `api-docs.html` (KHÔNG cần Jinja context cho URL tĩnh, tránh phụ thuộc context-
    substitution của website renderer). Endpoint spec ĐÃ session-gate riêng ở
    `api/openapi.py`; gate ở đây chỉ để khách không thấy khung tài liệu trống +
    redirect mượt về login.
    """
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/api-docs"
        raise frappe.Redirect
