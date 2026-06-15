# Copyright (c) 2026, AssetCore Team and contributors
# assetcore.api.mobile.v1 — namespace package cho hợp đồng API mobile (versioned /v1).
#
# Lưu ý phạm vi (ADR-MOBILE-001 · EPIC-D):
#   - KHÁC `assetcore.api.mobile` (tiện ích admin-only / pre-flight): package `v1`
#     chứa các ENDPOINT NGHIỆP VỤ thuộc hợp đồng app native, khai trong
#     `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (function-name == operationId).
#   - Handler ở đây là THIN wrapper (CLAUDE.md §15): chỉ parse form_dict + gọi service
#     layer qua `utils/api_handler.handle`. KHÔNG nhồi logic nghiệp vụ vào controller.
#   - Bearer-gated (OAuth2 access token): `@frappe.whitelist(methods=["POST"])` KHÔNG
#     `allow_guest` → guest/no-token bị dispatcher chặn (401/403) TRƯỚC khi vào handler.
#
# RE-EXPORT BẮT BUỘC (path-resolvability — D4 codegen↔runtime):
#   Hợp đồng OpenAPI khai path `/api/method/assetcore.api.mobile.v1.register_device_token`
#   (+ unregister). Frappe dispatcher resolve qua `frappe.get_attr(<path>)` =
#   `getattr(get_module("assetcore.api.mobile.v1"), "register_device_token")` → tra ATTR
#   trên PACKAGE `v1`, KHÔNG tự đi vào submodule `device_token`. Nếu KHÔNG re-export ở đây
#   → AttributeError → HTTP 404 cho MỌI call client-sinh-từ-yaml (dead-end runtime, dù
#   test spec-only vẫn GREEN). Re-export GIỮ `__module__ = ...device_token` (alias attr,
#   KHÔNG re-register whitelist, KHÔNG double-count guard) → path resolve + operationId
#   frozen bất biến. KHÔNG xoá.
from assetcore.api.mobile.v1.device_token import (  # noqa: E402,F401
    register_device_token,
    unregister_device_token,
)

__all__ = ["register_device_token", "unregister_device_token"]
