# Copyright (c) 2026, AssetCore Team
# Shared helper utilities — dùng chung cho toàn bộ API modules.
#
# DEPRECATED (Phase 0 of notification framework rollout):
#   `_ok` / `_err` đã được hợp nhất về `assetcore.utils.response` —
#   nguồn duy nhất cho API envelope. File này chỉ re-export để giữ backwards-compat
#   cho ~14 module hiện đang `from assetcore.utils.helpers import _err, _ok`.
#   Sẽ xoá block re-export ở Phase 6 sau khi migrate hết callers.

import json

import frappe

# Re-export canonical helpers — KHÔNG redefine ở đây.
from assetcore.utils.response import _err, _ok  # noqa: F401 (re-export for legacy callers)


# ─────────────────────────────────────────────────────────────────────────────
# URL CỦA GIAO DIỆN ASSETCORE (SPA Vue)
# ─────────────────────────────────────────────────────────────────────────────

#: Prefix mà SPA AssetCore được mount trên site Frappe.
#: COUPLING — phải khớp 3 nơi:
#:   - ``hooks.py: website_route_rules`` (``/assetcore/<path:app_path>``)
#:   - ``frontend/vite.config.ts`` (``__APP_BASE__`` khi build)
#:   - hàm ``fe_url`` dưới đây (mọi link BE gửi ra ngoài: email, thông báo)
#: Link gửi cho người dùng cuối PHẢI đi qua đây — nếu dùng ``get_url("/login")``
#: sẽ rơi vào route Frappe desk (404 hoặc form tiếng Anh), KHÔNG phải UI AssetCore.
FE_BASE = "/assetcore"


def fe_url(path: str = "/") -> str:
    """URL tuyệt đối tới một route của giao diện AssetCore.

    Args:
        path: route trong Vue Router, vd ``/login``, ``/set-password?key=abc``.

    Returns:
        URL đầy đủ, vd ``https://site.vn/assetcore/login``.
    """
    from frappe.utils import get_url

    if not path.startswith("/"):
        path = f"/{path}"
    return get_url(f"{FE_BASE}{path}")


# ─────────────────────────────────────────────────────────────────────────────
# API RESPONSE HELPERS — JSON PARSING (giữ tại đây vì không thuộc envelope)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json(raw, default):
    """Parse a JSON string; return default on failure or non-string input."""
    if not raw:
        return default
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_role_emails(roles: list[str]) -> list[str]:
    """Lấy danh sách email của users thuộc các role (dùng SQL cho hiệu năng)."""
    if not roles:
        return []
    placeholders = ", ".join(["%s"] * len(roles))
    rows = frappe.db.sql(
        f"""
        SELECT DISTINCT u.email
        FROM `tabHas Role` hr
        JOIN `tabUser` u ON u.name = hr.parent
        WHERE hr.role IN ({placeholders})
          AND hr.parenttype = 'User'
          AND u.enabled = 1
          AND u.email IS NOT NULL AND u.email != ''
        """,
        roles,
        as_dict=True,
    )
    return [r.email for r in rows]


def _safe_sendmail(**kwargs) -> bool:
    """Wrapper quanh ``frappe.sendmail`` — KHÔNG raise (không phá transaction).

    ISS-002: trước đây nuốt mọi lỗi bằng ``pass`` (không log) → vi phạm yêu cầu
    truy vết. Nay **ghi log** khi gửi lỗi và trả cờ đã-gửi để caller biết trạng
    thái (Sent/Failed). Vẫn bỏ qua khi email bị mute (test/CI).

    Cửa DUY NHẤT mọi email AssetCore đi qua → cũng là nơi tôn trọng công tắc
    tạm dừng gửi (``setup.email.set_email_delivery``). Tắt ở đây trả ``False``
    gọn gàng thay vì để SMTP nổ và làm bẩn Error Log.

    Returns:
        ``True`` nếu đã gửi/enqueue; ``False`` nếu bị mute / đang tạm dừng /
        gửi lỗi.
    """
    if frappe.flags.mute_emails:
        return False
    from assetcore.setup.email import is_email_delivery_disabled

    if is_email_delivery_disabled():
        return False
    try:
        frappe.sendmail(**kwargs)
        return True
    except Exception:
        frappe.log_error(frappe.get_traceback(), "_safe_sendmail failed")
        return False
