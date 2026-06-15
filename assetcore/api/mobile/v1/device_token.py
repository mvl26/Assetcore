# Copyright (c) 2026, AssetCore Team and contributors
"""EPIC-D / D4 — API handler device-token FCM (register / unregister).

Hợp đồng OpenAPI (SSoT codegen mobile)
--------------------------------------
``docs/mobile/openapi/assetcore-mobile.openapi.yaml``:
  - ``POST /api/method/assetcore.api.mobile.v1.register_device_token``  → operationId ``registerDeviceToken``
  - ``POST /api/method/assetcore.api.mobile.v1.unregister_device_token`` → operationId ``unregisterDeviceToken``

**function-name == operationId frozen** (guard ``test_mob_oas_06_device_token_names_frozen``):
đổi tên 2 hàm dưới đây = vỡ hợp đồng codegen. KHÔNG đổi.

Ranh giới (CLAUDE.md §15 · ADR-MOBILE-001 · 06-push-fcm.md §2.3/§6.2)
--------------------------------------------------------------------
- **THIN wrapper:** handler CHỈ đọc ``frappe.form_dict`` + gọi service D2 qua
  ``utils/api_handler.handle``. KHÔNG nhồi business logic (UPSERT-dedup / audit /
  ép-user / idempotent) vào controller — toàn bộ ở ``services/mobile_device_token.py``.
- **Bearer-gated:** ``@frappe.whitelist(methods=["POST"])`` KHÔNG ``allow_guest`` →
  guest/no-token bị dispatcher chặn 401/403 status-line TRƯỚC khi vào handler
  (đối xứng 12-path-401 == 12-path-403, D-A2).
- **Chống spoof (§6.2):** handler **KHÔNG nhận / KHÔNG forward** ``user`` từ client.
  Service ÉP ``user = frappe.session.user`` (signature service KHÔNG có ``user``;
  ``**_ignore`` nuốt mọi kwargs lạ). Handler chỉ chuyển 4 field hợp lệ
  (fcm_token / platform / device_label / app_version) — KHÔNG ``**form_dict``.
- **In-handler error → HTTP-200 + Error envelope** (đồng pattern EPIC-C, quirk §5):
  ``handle`` bắt ``ServiceError`` (422 VALIDATION: fcm_token rỗng / platform ngoài
  enum) → ``_err(...)`` HTTP-200 body ``{success:false}``. Route theo ``body.success``
  (Decision-B route-by-VALUE, KHÔNG discriminator). Client/test branch theo
  ``envelope.code``/``http_status``, KHÔNG status-line.

Param typing
------------
Tất cả param khai ``str = ""`` (KHÔNG ``None``): GET/form param rỗng cast sang
``None`` có thể trip ``validate_argument_types`` → HTTP 417 (LL-BE-1). ``str=""``
an toàn + service tự ``.strip()`` + validate.
"""
from __future__ import annotations

import frappe
from frappe.rate_limiter import rate_limit

from assetcore.services import mobile_device_token as svc
from assetcore.utils.api_handler import handle

# Ngưỡng rate-limit endpoint register (chống spam đăng ký device-token — 06 §5.3/§5.5).
# Pattern api/imm00.py:427/auth.py:67. ip_based=True: counter theo IP (device chưa có
# user-bucket ổn định lúc register).
#
# THỨ TỰ DECORATOR (BẮT BUỘC): @frappe.whitelist NGOÀI, @rate_limit TRONG — y hệt
# imm00.py:427 (resolve_qr_token). LÝ DO: @frappe.whitelist đăng ký vào registry
# theo OBJECT hàm nó bọc. Nếu @rate_limit bọc NGOÀI → registry giữ hàm-trần (inner),
# nhưng attr module = wrapper rate_limit ⇒ dispatcher get_attr() trả wrapper ⇒
# is_whitelisted(wrapper) FAIL ⇒ MỌI POST bị chặn 403 "not whitelisted" (regression
# D6, bắt bởi test_mob_oas_22j). @rate_limit ở TRONG vẫn raise 429 TRƯỚC thân handler
# (frappe tăng counter rồi throw RateLimitExceededError trước khi gọi fn) ⇒ giữ
# nguyên ý nghĩa chống spam: vượt ngưỡng = 0 UPSERT, 0 audit, no-leak (body-only 429).
# unregister KHÔNG throttle (opt-out luôn cho phép — không phải vector spam).
_REGISTER_RATE_LIMIT = 10


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=_REGISTER_RATE_LIMIT, seconds=60, ip_based=True)
def register_device_token(
    fcm_token: str = "",
    platform: str = "",
    device_label: str = "",
    app_version: str = "",
) -> dict:
    """Đăng ký / cập nhật (UPSERT) device-token FCM cho user ĐANG đăng nhập.

    operationId ``registerDeviceToken`` (FROZEN). Wrap service D2
    ``register_device_token`` — service ÉP ``user = frappe.session.user``
    (chống spoof §6.2). Trả ``_ok(name)`` ⇒ ``{success:true, data:"<hash>"}``;
    lỗi nghiệp vụ (fcm_token rỗng / platform ngoài enum) ⇒ HTTP-200 Error envelope.

    Args:
        fcm_token: registration token FCM SDK cấp (UNIQUE — bắt buộc).
        platform: 'android' | 'ios' (bắt buộc khi register).
        device_label: nhãn thiết bị tuỳ chọn.
        app_version: phiên bản app tuỳ chọn (telemetry).

    Returns:
        Envelope chuẩn: ``{success:true, data:<name>}`` hoặc Error envelope.
    """
    return handle(
        svc.register_device_token,
        fcm_token=fcm_token,
        platform=platform,
        device_label=device_label,
        app_version=app_version,
    )


@frappe.whitelist(methods=["POST"])
def unregister_device_token(fcm_token: str = "") -> dict:
    """Thu hồi (opt-out) device-token FCM của user ĐANG đăng nhập.

    operationId ``unregisterDeviceToken`` (FROZEN). Wrap service D2
    ``unregister_device_token`` — set ``enabled=0`` GIỮ record (lịch sử audit
    NĐ98). Idempotent: token∄ = success no-op KHÔNG raise. Service trả ``None``
    ⇒ ``_ok(None)`` ⇒ ``{success:true, data:null}`` (ack thuần).

    Args:
        fcm_token: registration token cần thu hồi.

    Returns:
        Envelope chuẩn: ``{success:true, data:null}``.
    """
    return handle(svc.unregister_device_token, fcm_token)
