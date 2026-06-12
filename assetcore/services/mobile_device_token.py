# Copyright (c) 2026, AssetCore Team
"""Service layer (3-tier) cho registry token push FCM — EPIC-D / D2.

DocType: `AC Mobile Device Token` (D1, 7 field, `fcm_token` UNIQUE, autoname=hash).
Spec hợp đồng:
  - `docs/mobile/completion/EPIC-D-push-fcm.md` §D2 / §6.2 (threat-spoof) / §6.3 (audit NĐ98)
  - `docs/mobile/06-push-fcm.md` §2.3 (self-service, KHÔNG cap mới) / §2.4 (dedup) /
    §2.5 (unregister GIỮ record + invalidate-on-401) / §5.3 (ÉP user=session)

3 hàm public (self-service field-tech — gate bằng **bearer đã login** + row-level
self-scope D7; KHÔNG thêm capability nghiệp vụ vào CAPABILITY_MAP — §2.3):

  - `register_device_token(*, fcm_token, platform, device_label='', app_version='')`
        ÉP `user = frappe.session.user` (KHÔNG khai báo tham số `user` → chặn spoof
        §6.2: client KHÔNG chọn được chủ token). UPSERT-dedup theo `fcm_token`
        (UNIQUE): tồn tại → cập nhật user/platform/device_label/app_version/last_seen
        + enabled=1 trên CÙNG record (đổi user = re-bind sạch, KHÔNG nhân đôi);
        chưa có → new_doc. Trả `name` (hash) của record.

  - `unregister_device_token(fcm_token)`  set `enabled=0` NHƯNG GIỮ record (audit
        §2.5 — KHÔNG xoá). Idempotent: token∄ = no-op KHÔNG raise.

  - `invalidate_token(fcm_token)`  set `enabled=0` — entry-point cho sender D5 khi
        FCM trả 401/UNREGISTERED. Total-function: idempotent, token∄ = no-op KHÔNG raise.

Audit NĐ98 (§6.3): register + unregister sinh 1 row IMM Audit Trail (SHA-256 chain)
qua `svc00.log_audit_event` — truy xuất ai-đăng-ký-token-nào-khi-nào. `event_type`
dùng giá trị Select canonical `"System"` (token register = thao tác hệ thống/an
ninh, KHÔNG asset-bound) + hành động chi tiết trong `change_summary` — đồng pattern
`services/imm12.py:_log` (canonical Select bucket + summary mô tả). KHÔNG đặt action-
string raw vào `event_type` (Select reqd → InvalidValue nếu ngoài enum).

HARD-STOP USER: bảng `tabAC Mobile Device Token` + UNIQUE index `fcm_token` chỉ live
sau `bench --site miyano migrate` (D1 DocType JSON đã frozen, chưa migrate DB). Mọi
đường ghi DB ở đây = RED-pending-migrate tới khi USER migrate.
"""
from __future__ import annotations

import frappe
from frappe.utils import now_datetime

from assetcore.services import imm00 as svc00
from assetcore.services.shared import ErrorCode, ServiceError

DOCTYPE = "AC Mobile Device Token"

# event_type Select canonical (imm_audit_trail.json options) — token register là
# thao tác hệ thống/an ninh, KHÔNG asset-bound. Action chi tiết ở change_summary.
_AUDIT_EVENT_TYPE = "System"

# Hành động (NĐ98 truy xuất) — nhúng vào change_summary, KHÔNG vào event_type Select.
_ACTION_REGISTER = "register_device_token"
_ACTION_UNREGISTER = "unregister_device_token"

# Platform hợp lệ (đồng bộ Select options DocType D1 — 06 §2.1).
_VALID_PLATFORMS = ("android", "ios")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────
def _find_token_name(fcm_token: str) -> str | None:
    """Tra `name` (hash) của record theo `fcm_token` UNIQUE — None nếu chưa có.

    Đọc qua UNIQUE index (`get_value` filter dict) → O(log n), KHÔNG full-scan.
    """
    return frappe.db.get_value(DOCTYPE, {"fcm_token": fcm_token}, "name")


def _audit(action: str, *, token_name: str | None, fcm_token: str) -> None:
    """Ghi 1 row IMM Audit Trail cho thao tác token (NĐ98 §6.3).

    Fail-safe: lỗi audit KHÔNG vỡ nghiệp vụ register/unregister (token đã ghi DB
    là sự thật; audit chỉ bồi). `asset=None` — token KHÔNG asset-bound (field
    `asset` reqd=0). `event_type` canonical Select; hành động ở `change_summary`.
    """
    try:
        actor = frappe.session.user
        svc00.log_audit_event(
            asset=None,
            event_type=_AUDIT_EVENT_TYPE,
            actor=actor,
            ref_doctype=DOCTYPE,
            ref_name=token_name,
            change_summary=f"{action}: actor={actor}, fcm_token=***{fcm_token[-6:]}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "EPIC-D D2 _audit device-token")


# ─────────────────────────────────────────────────────────────────────────────
# Public service API (3-tier — gọi từ api/mobile/v1 D4)
# ─────────────────────────────────────────────────────────────────────────────
def register_device_token(
    *,
    fcm_token: str,
    platform: str,
    device_label: str = "",
    app_version: str = "",
    **_ignore: object,
) -> str:
    """Đăng ký / cập nhật (UPSERT) 1 token push FCM cho user ĐANG đăng nhập.

    ÉP `user = frappe.session.user` — signature KHÔNG nhận `user`; mọi kwargs lạ
    (vd `user=<nạn nhân>`) bị `**_ignore` nuốt và BỎ → client KHÔNG chọn được chủ
    token (chống spoof §6.2). UPSERT-dedup theo `fcm_token` UNIQUE (§2.4):

      - token đã tồn tại → cập nhật user/platform/device_label/app_version/
        last_seen=now + enabled=1 trên CÙNG record (đổi user = re-bind sạch,
        record cũ chuyển chủ, KHÔNG nhân đôi);
      - chưa có → new_doc('AC Mobile Device Token').

    Sinh audit NĐ98 (§6.3). Trả `name` (hash) của record.

    Args:
        fcm_token: registration token do FCM SDK cấp (UNIQUE — khóa dedup).
        platform: 'android' | 'ios' (Select-canonical 06 §2.1).
        device_label: nhãn thiết bị tuỳ chọn (đa-thiết-bị per user).
        app_version: phiên bản app tuỳ chọn (telemetry).
        **_ignore: NUỐT kwargs lạ (gồm `user`) — KHÔNG đổi chủ token (§6.2).

    Returns:
        `name` (hash) của record token.

    Raises:
        ServiceError(VALIDATION): fcm_token rỗng hoặc platform ngoài enum.
    """
    fcm_token = (fcm_token or "").strip()
    platform = (platform or "").strip()
    if not fcm_token:
        raise ServiceError(ErrorCode.VALIDATION, "Thiếu FCM token", http_status=422)
    if platform not in _VALID_PLATFORMS:
        raise ServiceError(
            ErrorCode.VALIDATION,
            "Nền tảng không hợp lệ (chỉ android/ios)",
            http_status=422,
        )

    user = frappe.session.user  # ÉP — KHÔNG nhận từ client (§6.2)
    now = now_datetime()

    existing = _find_token_name(fcm_token)
    if existing:
        # UPSERT — cập nhật CÙNG record (re-bind sạch nếu đổi chủ; KHÔNG nhân đôi).
        doc = frappe.get_doc(DOCTYPE, existing)
        doc.user = user
        doc.platform = platform
        doc.device_label = device_label or ""
        doc.app_version = app_version or ""
        doc.last_seen = now
        doc.enabled = 1
        doc.save(ignore_permissions=True)
        name = doc.name
    else:
        doc = frappe.get_doc({
            "doctype": DOCTYPE,
            "user": user,
            "fcm_token": fcm_token,
            "platform": platform,
            "device_label": device_label or "",
            "app_version": app_version or "",
            "last_seen": now,
            "enabled": 1,
        })
        doc.insert(ignore_permissions=True)
        name = doc.name

    _audit(_ACTION_REGISTER, token_name=name, fcm_token=fcm_token)
    return name


def unregister_device_token(fcm_token: str) -> None:
    """Hủy đăng ký token (opt-out per-device): set `enabled=0`, GIỮ record (§2.5).

    KHÔNG xoá record — giữ làm lịch sử audit (NĐ98). Idempotent: token∄ = no-op
    KHÔNG raise. Sinh audit NĐ98 khi record tồn tại (§6.3).

    Args:
        fcm_token: registration token cần hủy.
    """
    fcm_token = (fcm_token or "").strip()
    if not fcm_token:
        return
    name = _find_token_name(fcm_token)
    if not name:
        return  # idempotent no-op — KHÔNG raise
    frappe.db.set_value(DOCTYPE, name, "enabled", 0)
    _audit(_ACTION_UNREGISTER, token_name=name, fcm_token=fcm_token)


def invalidate_token(fcm_token: str) -> None:
    """Vô hiệu hóa token chết: set `enabled=0` — entry-point cho sender D5 on-401.

    Gọi từ `utils/fcm.py` (D5) khi FCM trả 401/UNREGISTERED (token-not-registered).
    Total-function: idempotent, token∄ = no-op KHÔNG raise. KHÔNG sinh audit nghiệp
    vụ (đây là dọn rác hệ thống tự động, KHÔNG phải thao tác user) — pattern §2.5.

    Args:
        fcm_token: registration token FCM báo không còn hợp lệ.
    """
    fcm_token = (fcm_token or "").strip()
    if not fcm_token:
        return
    name = _find_token_name(fcm_token)
    if not name:
        return  # idempotent no-op — token đã biến mất, KHÔNG raise
    frappe.db.set_value(DOCTYPE, name, "enabled", 0)
