# Copyright (c) 2026, AssetCore Team
"""IMM-00 — Cấu hình email gửi đi (SMTP) cho AssetCore. (ISS-002)

Đọc SMTP credentials từ ``apps/assetcore/.env`` (KHÔNG hardcode secret trong
``.py``, KHÔNG commit — ``.env`` đã gitignored) rồi upsert MỘT Email Account
``default_outgoing`` để welcome/notification email của AssetCore thoát ra ngoài.

Root cause ISS-002 (đã verify site ``miyano``):
  1. Scheduler TẮT → Email Queue không flush → welcome mail (enqueue) kẹt.
  2. Không có Email Account ``default_outgoing`` → không có kênh gửi ổn định.

Chạy trực tiếp (KHÔNG cần bench migrate):
    bench --site <site> execute assetcore.setup.email.setup_assetcore_email
"""
from __future__ import annotations

import os
from typing import Any

import frappe

# apps/assetcore/.env  (file này ở assetcore/setup/ → lùi 2 cấp)
_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
_ACCOUNT_NAME = "AssetCore Notifications"

_ENV_KEYS = {
    "server": "ASSETCORE_SMTP_SERVER",
    "port": "ASSETCORE_SMTP_PORT",
    "use_tls": "ASSETCORE_SMTP_USE_TLS",
    "login": "ASSETCORE_SMTP_LOGIN",
    "password": "ASSETCORE_SMTP_PASSWORD",
    "sender": "ASSETCORE_SMTP_SENDER",
}


def _load_env(path: str | None = None) -> dict[str, str]:
    """Parser ``.env`` tối giản (KEY=VALUE) — không phụ thuộc python-dotenv (không cài)."""
    path = path or _ENV_PATH
    env: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


def _read_smtp_config(env: dict[str, str] | None = None) -> dict[str, Any] | None:
    """Chuẩn hoá config SMTP từ env; trả ``None`` nếu thiếu key bắt buộc."""
    env = env if env is not None else _load_env()
    server = (env.get(_ENV_KEYS["server"]) or "").strip()
    login = (env.get(_ENV_KEYS["login"]) or "").strip()
    # Gmail App Password nhập dạng 4 nhóm cách nhau — smtplib cần bỏ khoảng trắng.
    password = (env.get(_ENV_KEYS["password"]) or "").replace(" ", "").strip()
    if not (server and login and password):
        return None
    sender = (env.get(_ENV_KEYS["sender"]) or login).strip() or login
    use_tls_raw = (env.get(_ENV_KEYS["use_tls"]) or "1").strip().lower()
    return {
        "smtp_server": server,
        "smtp_port": (env.get(_ENV_KEYS["port"]) or "587").strip() or "587",
        "use_tls": 1 if use_tls_raw in ("1", "true", "yes", "on") else 0,
        "login": login,
        "password": password,
        "sender": sender,
    }


def configure_outgoing_email(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Upsert Email Account ``default_outgoing`` từ ``.env``. Idempotent.

    Returns:
        ``{"configured": True, "email_account": name, "email_id": ...}`` khi OK, hoặc
        ``{"skipped": True, "reason": ...}`` khi ``.env`` thiếu (an toàn cho CI/env khác).
    """
    cfg = _read_smtp_config(env)
    if not cfg:
        return {"skipped": True, "reason": "Thiếu ASSETCORE_SMTP_* trong apps/assetcore/.env"}

    # `email_id` là UNIQUE index của Email Account: nếu site đã có account CÙNG
    # địa chỉ gửi nhưng KHÁC tên (admin tự tạo tay / seed cũ), tạo mới sẽ nổ
    # UniqueValidationError → NHẬN account đó và cập nhật vào chính nó.
    target = (
        _ACCOUNT_NAME
        if frappe.db.exists("Email Account", _ACCOUNT_NAME)
        else frappe.db.get_value("Email Account", {"email_id": cfg["sender"]}, "name")
    )

    # Frappe chỉ cho phép 1 Email Account default_outgoing — hạ cờ mọi account khác.
    for other in frappe.get_all(
        "Email Account",
        filters={"default_outgoing": 1, "name": ["!=", target or _ACCOUNT_NAME]},
        pluck="name",
    ):
        frappe.db.set_value("Email Account", other, "default_outgoing", 0)

    if target:
        doc = frappe.get_doc("Email Account", target)
    else:
        doc = frappe.new_doc("Email Account")
        doc.email_account_name = _ACCOUNT_NAME

    login_differs = cfg["login"] != cfg["sender"]
    doc.email_id = cfg["sender"]
    doc.smtp_server = cfg["smtp_server"]
    doc.smtp_port = cfg["smtp_port"]
    doc.use_tls = cfg["use_tls"]
    doc.use_ssl = 0
    doc.login_id_is_different = 1 if login_differs else 0
    doc.login_id = cfg["login"] if login_differs else None
    doc.password = cfg["password"]
    doc.awaiting_password = 0
    doc.enable_outgoing = 1
    doc.default_outgoing = 1
    doc.enable_incoming = 0
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"configured": True, "email_account": doc.name, "email_id": doc.email_id}


def _quarantine_stale_queue() -> int:
    """Đánh dấu Email Queue 'Not Sent' cũ → 'Error' để KHÔNG bắn nhầm tới người thật
    khi bật scheduler (các email này kẹt từ lúc scheduler tắt). Trả số row xử lý."""
    rows = frappe.get_all("Email Queue", filters={"status": "Not Sent"}, pluck="name")
    for name in rows:
        frappe.db.set_value(
            "Email Queue",
            name,
            {
                "status": "Error",
                "error": "Quarantined by AssetCore setup_assetcore_email "
                "(stale — scheduler was off khi enqueue).",
            },
            update_modified=False,
        )
    if rows:
        frappe.db.commit()
    return len(rows)


#: Cờ TẠM DỪNG gửi email của AssetCore (default của site — KHÔNG phải site_config,
#: KHÔNG phải xoá code). ``utils.helpers._safe_sendmail`` tôn trọng cờ này.
DELIVERY_DISABLED_FLAG = "assetcore_email_delivery_disabled"


def is_email_delivery_disabled() -> bool:
    """True khi việc gửi email đang bị TẠM DỪNG bằng công tắc của AssetCore."""
    from frappe.utils import cint

    return bool(cint(frappe.db.get_default(DELIVERY_DISABLED_FLAG) or 0))


def set_email_delivery(enabled: bool) -> dict[str, Any]:
    """Bật/tắt gửi email của AssetCore. Đảo ngược hoàn toàn, KHÔNG đụng code.

    Dùng khi nhà cung cấp SMTP tạm thời không gửi được (vd Gmail báo
    ``550 5.4.5 Daily user sending limit exceeded``) — tắt để không sinh rác
    Error Log và không để người dùng tưởng đã nhận được thư.

    ``bench execute --kwargs`` chạy qua ``eval`` của Python, KHÔNG parse JSON →
    phải dùng ``1``/``0`` (``true``/``false`` sẽ nổ ``NameError``).

    Tắt::

        bench --site <site> execute assetcore.setup.email.set_email_delivery \\
            --kwargs '{"enabled": 0}'

    Bật lại::

        bench --site <site> execute assetcore.setup.email.set_email_delivery \\
            --kwargs '{"enabled": 1}'

    Xem trạng thái::

        bench --site <site> execute assetcore.setup.email.is_email_delivery_disabled

    Returns:
        ``{"enabled": bool, "changed": bool}`` — ``changed`` False nghĩa là đã ở
        đúng trạng thái đó từ trước (idempotent).
    """
    want_disabled = not enabled
    already = is_email_delivery_disabled()
    if already != want_disabled:
        frappe.db.set_default(DELIVERY_DISABLED_FLAG, 1 if want_disabled else 0)
        frappe.db.commit()
    return {"enabled": bool(enabled), "changed": already != want_disabled}


def disable_frappe_email_branding() -> dict[str, Any]:
    """Tắt chân trang quảng cáo mặc định của nền tảng trong email gửi đi.

    Frappe nối THÊM khối ``default_mail_footer`` (do ERPNext khai báo — dòng
    "Sent via ERPNext" + link frappe.io) vào MỌI email lúc build message, nằm
    NGOÀI khung ``assetcore.utils.email_template``. Công tắc duy nhất Frappe hỗ
    trợ là default ``disable_standard_email_footer`` ở tầng site.

    Idempotent, KHÔNG cần bench migrate.

    Returns:
        ``{"disabled": True, "changed": bool}`` — ``changed`` False nghĩa là đã
        tắt sẵn từ trước.
    """
    from frappe.utils import cint

    key = "disable_standard_email_footer"
    already = bool(cint(frappe.db.get_default(key) or 0))
    if not already:
        frappe.db.set_default(key, 1)
        frappe.db.commit()
    return {"disabled": True, "changed": not already}


def enable_email_delivery() -> dict[str, Any]:
    """Bật scheduler để Email Queue được flush cho các notification khác.

    (Welcome/activation dùng ``now=True`` nên độc lập với scheduler; hàm này để
    những notification enqueue của AssetCore cũng được gửi.)
    """
    from frappe.utils.scheduler import enable_scheduler, is_scheduler_disabled

    was_disabled = is_scheduler_disabled(verbose=False)
    enable_scheduler()
    frappe.db.commit()
    return {"scheduler_enabled": True, "was_disabled": was_disabled}


def setup_assetcore_email(quarantine_stale: bool = True) -> dict[str, Any]:
    """One-shot ISS-002: cấu hình SMTP từ ``.env`` + dọn queue kẹt + bật scheduler.

    An toàn chạy lại (idempotent). KHÔNG cần bench migrate.
    """
    result: dict[str, Any] = {"email": configure_outgoing_email()}
    if quarantine_stale:
        result["stale_quarantined"] = _quarantine_stale_queue()
    result["branding"] = disable_frappe_email_branding()
    result["delivery"] = enable_email_delivery()
    return result
