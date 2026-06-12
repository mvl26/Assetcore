# Copyright (c) 2026, AssetCore Team
"""Sender FCM HTTP v1 (EPIC-D / D5) — gửi 1 message push tới 1 device-token.

Spec hợp đồng:
  - `docs/mobile/completion/EPIC-D-push-fcm.md` §D5 / §5.3 (payload shape) / §6.2
    (threat — KHÔNG log creds) / §6.4 (fail-safe).
  - `docs/mobile/06-push-fcm.md` §4.1 (payload FCM HTTP v1) / §5.2 (creds site_config).
  - `ADR-MOBILE-002` — FCM Admin SDK HTTP v1 TRỰC TIẾP (KHÔNG relay Frappe Cloud).

STDLIB-ONLY guard (BE KHÔNG cài lib — `firebase-admin`/`requests`/`google-*` = HARD-STOP
USER). Mọi I/O HTTP qua `urllib` stdlib; ký OAuth2 service-account qua `cryptography`
(ĐÃ có trong env Frappe — RSA-SHA256). KHÔNG import `firebase_admin`/`requests`/`google.*`.

Creds đọc TỪ `site_config` (USER set — D3 [HARD-STOP USER]):
  - `frappe.conf.fcm_service_account_path` — đường dẫn file JSON service-account.
  - `frappe.conf.fcm_project_id` — Firebase project id (vào URL `messages:send`).
Thiếu creds → no-op fail-safe (return None, KHÔNG raise — pattern `_safe_sendmail`
`utils/helpers.py:59`). TUYỆT ĐỐI KHÔNG log nội dung creds (private_key / token bí mật).

Invalidate-on-401: FCM trả 401 / UNREGISTERED / HTTP-404
`messaging/registration-token-not-registered` ⇒ token chết ⇒ gọi
`services.mobile_device_token.invalidate_token(fcm_token)` ĐÚNG 1 LẦN (lazy-import —
chống circular import khi `bench start`; entry-point idempotent set enabled=0).

HARD-STOP USER (chạy THẬT — ngoài scope AUTO/mock-test vòng này):
  - D3: set `fcm_service_account_path` + `fcm_project_id` trong `site_config.json`.
  - outbound HTTPS `fcm.googleapis.com` + `oauth2.googleapis.com` reachable.
  - `bench restart`/reload gunicorn (--preload) để live HTTP qua engine `_dispatch` (D6).
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import frappe
from frappe.utils import strip_html

# ─────────────────────────────────────────────────────────────────────────────
# Hằng số endpoint FCM HTTP v1 / OAuth2 (ADR-MOBILE-002 — direct, KHÔNG relay).
# ─────────────────────────────────────────────────────────────────────────────
_FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
_OAUTH_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_BODY_MAX_LEN = 1000  # §5.3 — body push ≤1000 ký tự.
_HTTP_TIMEOUT = 10  # giây — KHÔNG để treo engine _dispatch (D6).

# Tín hiệu token chết → invalidate (06 §5 / D5). FCM HTTP v1 trả 404 với
# `error.status == "NOT_FOUND"` + detail `messaging/registration-token-not-registered`;
# token hết hạn / sai project → 401 UNAUTHENTICATED hoặc 403.
_DEAD_TOKEN_MARKERS = (
    "UNREGISTERED",
    "registration-token-not-registered",
)


# ─────────────────────────────────────────────────────────────────────────────
# Build payload §5.3 — tách riêng để test shape KHÔNG cần creds/HTTP.
# ─────────────────────────────────────────────────────────────────────────────
def _build_message(token: str, title: str, body: str, data: dict) -> dict:
    """Dựng FCM HTTP v1 `message` đúng SHAPE §5.3 (KHÔNG I/O — pure function).

    - `message.token` = fcm_token của device.
    - `notification.title/body` strip-HTML (tái dùng subject/message in-app/email);
      body cắt ≤1000 ký tự (§5.3 — push body cap).
    - `data{doctype,name,event,deeplink}` data-only routing (APK tự điều hướng) —
      mọi value ÉP về `str` (FCM HTTP v1 yêu cầu data map<string,string>).
    - `android.priority` = "high" (incident/SLA) hoặc "normal" (PM-due); mặc định
      "high" — caller (D6) truyền qua `data['_priority']` nếu muốn hạ.

    Args:
        token: FCM registration token (device đích, enabled=1).
        title: tiêu đề (sẽ strip-HTML).
        body: nội dung (sẽ strip-HTML + cắt ≤1000 ký tự).
        data: routing keys — tối thiểu doctype/name/event/deeplink.

    Returns:
        dict `{"message": {...}}` sẵn sàng `json.dumps` POST FCM.
    """
    data = data or {}
    clean_title = strip_html(title or "")
    clean_body = strip_html(body or "")
    if len(clean_body) > _BODY_MAX_LEN:
        clean_body = clean_body[:_BODY_MAX_LEN]

    priority = str(data.get("_priority") or "high")
    if priority not in ("high", "normal"):
        priority = "high"

    # data map<string,string> — chỉ giữ routing keys nghiệp vụ (loại key nội bộ `_*`).
    data_payload = {
        "doctype": str(data.get("doctype") or ""),
        "name": str(data.get("name") or ""),
        "event": str(data.get("event") or ""),
        "deeplink": str(data.get("deeplink") or ""),
    }

    return {
        "message": {
            "token": token,
            "notification": {
                "title": clean_title,
                "body": clean_body,
            },
            "data": data_payload,
            "android": {"priority": priority},
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Credentials — đọc TỪ site_config (KHÔNG hardcode, KHÔNG log nội dung).
# ─────────────────────────────────────────────────────────────────────────────
def _load_credentials() -> tuple[dict, str] | None:
    """Đọc service-account + project_id TỪ `site_config` (KHÔNG hardcode).

    Thiếu BẤT KỲ creds nào (path / project_id / file không đọc được / JSON hỏng) →
    return None (no-op fail-safe — caller KHÔNG raise). KHÔNG log nội dung creds
    (chỉ log "missing"/"unreadable", KHÔNG private_key).

    Returns:
        `(sa_info_dict, project_id)` nếu đủ creds; None nếu thiếu/lỗi.
    """
    sa_path = frappe.conf.get("fcm_service_account_path")
    project_id = frappe.conf.get("fcm_project_id")
    if not sa_path or not project_id:
        return None
    try:
        with open(sa_path, encoding="utf-8") as fh:
            sa_info = json.load(fh)
    except Exception:
        # KHÔNG log path-content/creds — chỉ ghi nhãn lỗi cấu hình (no secret).
        frappe.log_error(
            "FCM service-account file không đọc được (kiểm tra fcm_service_account_path).",
            "EPIC-D D5 fcm creds",
        )
        return None
    if not sa_info.get("private_key") or not sa_info.get("client_email"):
        frappe.log_error(
            "FCM service-account thiếu private_key/client_email.",
            "EPIC-D D5 fcm creds",
        )
        return None
    return sa_info, str(project_id)


# ─────────────────────────────────────────────────────────────────────────────
# OAuth2 service-account — tự ký JWT (RSA-SHA256, cryptography) → access_token.
# ─────────────────────────────────────────────────────────────────────────────
def _b64url(raw: bytes) -> str:
    """base64url KHÔNG padding (JWT segment encoding)."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _sign_jwt(sa_info: dict) -> str:
    """Ký JWT bearer (RS256) bằng private_key của service-account (stdlib + cryptography).

    KHÔNG dùng google-auth (lib chưa cài — STDLIB-only guard). Claim theo OAuth2
    SA flow (aud=token endpoint, scope=firebase.messaging, exp ≤1h).
    """
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": sa_info["client_email"],
        "scope": _OAUTH_SCOPE,
        "aud": _OAUTH_TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = (
        _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + _b64url(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    ).encode("ascii")

    private_key = serialization.load_pem_private_key(
        sa_info["private_key"].encode("utf-8"), password=None
    )
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return signing_input.decode("ascii") + "." + _b64url(signature)


def _fetch_access_token(sa_info: dict) -> str | None:
    """Đổi JWT bearer lấy OAuth2 access_token (POST oauth2.googleapis.com/token).

    HTTP qua urllib stdlib (KHÔNG requests). Lỗi → None (caller no-op). KHÔNG log
    token/creds.
    """
    assertion = _sign_jwt(sa_info)
    form = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
    ).encode("ascii")
    req = urllib.request.Request(
        _OAUTH_TOKEN_URL,
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        frappe.log_error(
            "FCM OAuth2 token exchange thất bại (kiểm tra creds/outbound HTTPS).",
            "EPIC-D D5 fcm oauth",
        )
        return None
    return payload.get("access_token")


# ─────────────────────────────────────────────────────────────────────────────
# POST message → FCM HTTP v1 (urllib stdlib). Trả (status_code, body_text).
# ─────────────────────────────────────────────────────────────────────────────
def _post_message(project_id: str, message: dict, access_token: str) -> tuple[int, str]:
    """POST `message` tới FCM HTTP v1 `messages:send`. Trả (http_status, body).

    urllib raise HTTPError trên 4xx/5xx — bắt và trả về (code, body) để caller
    quyết invalidate (401/404 token-dead) vs log (lỗi khác). KHÔNG raise lan.
    """
    url = _FCM_SEND_URL.format(project_id=project_id)
    body = json.dumps(message).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:  # 4xx/5xx — đọc body để phân loại token-dead.
        try:
            err_body = exc.read().decode("utf-8", "replace")
        except Exception:
            err_body = ""
        return exc.code, err_body
    except Exception:
        frappe.log_error(
            "FCM messages:send thất bại (mạng/timeout — KHÔNG creds-leak).",
            "EPIC-D D5 fcm send",
        )
        return 0, ""


def _is_dead_token(status: int, body: str) -> bool:
    """Token chết ⇒ invalidate (06 §5 / D5).

    Tín hiệu: HTTP 401 (UNAUTHENTICATED token) hoặc 404 (NOT_FOUND) HOẶC body chứa
    marker `UNREGISTERED` / `registration-token-not-registered`.
    """
    if status in (401, 404):
        return True
    body = body or ""
    return any(marker in body for marker in _DEAD_TOKEN_MARKERS)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry-point — gọi từ engine `_dispatch` (D6, vòng sau).
# ─────────────────────────────────────────────────────────────────────────────
def send_fcm_message(
    token: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool | None:
    """Gửi 1 message push FCM HTTP v1 tới 1 device-token (fail-safe).

    Pipeline: load creds (site_config) → ký OAuth2 SA → POST `messages:send`.
    Token chết (401/UNREGISTERED/404 token-not-registered) → `invalidate_token`
    ĐÚNG 1 LẦN (lazy-import chống circular). Lỗi BẤT KỲ KHÔNG raise lan (fail-safe
    pattern `_safe_sendmail` — kênh #3 KHÔNG vỡ in-app/email §1.3). KHÔNG log creds.

    Args:
        token: FCM registration token (device đích, enabled=1).
        title: tiêu đề (strip-HTML).
        body: nội dung (strip-HTML + cắt ≤1000 ký tự).
        data: routing keys doctype/name/event/deeplink (+ `_priority` tuỳ chọn).

    Returns:
        - None  : no-op (thiếu creds / thiếu token / lỗi OAuth) — fail-safe.
        - True  : FCM nhận message (HTTP 2xx).
        - False : FCM từ chối (gồm token chết — đã invalidate).
    """
    if not token:
        return None

    creds = _load_credentials()
    if creds is None:
        return None  # thiếu creds → no-op fail-safe (KHÔNG raise — §6.4).
    sa_info, project_id = creds

    try:
        access_token = _fetch_access_token(sa_info)
        if not access_token:
            return None  # OAuth fail → no-op (KHÔNG raise; đã log non-secret).

        message = _build_message(token, title, body, data or {})
        status, resp_body = _post_message(project_id, message, access_token)

        if 200 <= status < 300:
            return True

        if _is_dead_token(status, resp_body):
            # Lazy-import chống circular (services↔utils khi bench start).
            from assetcore.services.mobile_device_token import invalidate_token

            invalidate_token(token)
            return False

        # Lỗi khác (5xx/quota/4xx khác) — log nhãn (KHÔNG body có thể chứa token).
        frappe.log_error(
            f"FCM messages:send trả HTTP {status} (không phải token-dead).",
            "EPIC-D D5 fcm send",
        )
        return False
    except Exception:
        # Fail-safe tuyệt đối: KHÔNG vỡ caller (_dispatch). KHÔNG log creds.
        frappe.log_error(frappe.get_traceback(), "EPIC-D D5 send_fcm_message")
        return None
