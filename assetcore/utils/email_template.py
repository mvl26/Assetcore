# Copyright (c) 2026, AssetCore Team
"""IMM-00 — Khung email chuẩn mang thương hiệu AssetCore. (ISS-002)

Mọi email giao dịch AssetCore gửi cho người dùng cuối (chào mừng, kích hoạt tài
khoản, thông báo cho quản trị viên) phải đi qua ``render_email`` để có CÙNG một
nhận diện: header thương hiệu, thân nội dung, nút hành động, chân trang tiếng
Việt. Người dùng cuối chỉ biết giao diện AssetCore — email không được mang nhận
diện của nền tảng bên dưới.

Ràng buộc kỹ thuật của email HTML (khác web):
  - **Tự chứa**: style phải inline, KHÔNG ``<link>``/CSS ngoài, KHÔNG asset của
    desk — email client chặn tài nguyên ngoài.
  - **Bảng thay cho flex/grid**: Outlook không hỗ trợ layout hiện đại.
  - **Escape dữ liệu người dùng**: tên/khoa phòng do người dùng nhập, nhúng thô
    vào HTML là lỗ HTML-injection.

Chân trang quảng cáo của nền tảng được nối THÊM lúc gửi (ngoài tầm khung này) —
tắt bằng ``assetcore.setup.email.disable_frappe_email_branding``.
"""
from __future__ import annotations

import frappe

BRAND_NAME = "AssetCore"
BRAND_TAGLINE = "Hệ thống Quản lý Thiết bị Y tế"

#: Dấu nhận diện "email này do khung AssetCore dựng" — test dùng để chặn việc
#: quay lại nối chuỗi HTML rời rạc ở từng caller.
#:
#: LƯU Ý: marker nằm trên thẻ ``<html>`` nên **không tới được hộp thư** — Frappe
#: bóc phần thân rồi bọc lại bằng template riêng lúc gửi. Đây là hợp đồng ở biên
#: ``render_email`` (unit test), KHÔNG phải thứ để kiểm tra trên email đã nhận;
#: phần nhận diện THẬT sự tới hộp thư là header thương hiệu + màu + chân trang
#: (đã verify trên message ráp cuối của ``frappe.email.email_body.get_email``).
EMAIL_MARKER = 'data-assetcore-email="1"'

_BRAND_COLOR = "#2563eb"
_INK = "#1f2937"
_MUTED = "#6b7280"
_BORDER = "#e5e7eb"
_CANVAS = "#f3f4f6"

_FOOTER_TEXT = (
    "Email tự động từ hệ thống {brand} — vui lòng không trả lời thư này. "
    "Cần hỗ trợ, hãy liên hệ quản trị viên hệ thống của đơn vị."
).format(brand=BRAND_NAME)


def _esc(value: str | None) -> str:
    """Escape text do người dùng/DB cung cấp trước khi nhúng vào HTML email."""
    return frappe.utils.escape_html(value or "")


def _cta_html(cta_label: str | None, cta_url: str | None) -> str:
    """Nút hành động chính. Trả chuỗi rỗng khi thiếu URL (không render nút chết)."""
    if not cta_url:
        return ""
    label = _esc(cta_label or "Mở AssetCore")
    href = _esc(cta_url)
    return (
        f'<tr><td class="ac-email-cta" style="padding:8px 0 4px 0">'
        f'<a href="{href}" style="display:inline-block;padding:12px 24px;'
        f"background:{_BRAND_COLOR};color:#ffffff;border-radius:8px;"
        f'text-decoration:none;font-weight:600;font-size:15px">{label}</a>'
        f"</td></tr>"
        # Nhiều email client chặn/ẩn nút — luôn kèm URL dạng text để copy tay.
        f'<tr><td style="padding:4px 0 0 0;font-size:13px;color:{_MUTED}">'
        f'Nếu nút không hoạt động, hãy sao chép liên kết sau vào trình duyệt:<br />'
        f'<a href="{href}" style="color:{_BRAND_COLOR};word-break:break-all">{href}</a>'
        f"</td></tr>"
    )


def render_email(
    *,
    title: str,
    body_html: str,
    greeting: str | None = None,
    cta_label: str | None = None,
    cta_url: str | None = None,
    note: str | None = None,
) -> str:
    """Dựng email HTML hoàn chỉnh mang thương hiệu AssetCore.

    Args:
        title: Tiêu đề hiển thị trong thân email (text thô — được escape).
        body_html: Phần thân do caller dựng. Caller **phải tự escape** dữ liệu
            người dùng nhúng trong đó (dùng ``frappe.utils.escape_html``).
        greeting: Tên người nhận để chào (text thô — được escape).
        cta_label: Nhãn nút hành động chính.
        cta_url: URL của nút; thiếu URL thì KHÔNG render nút.
        note: Ghi chú nhỏ dưới thân (vd. hạn dùng của liên kết) — text thô.

    Returns:
        Chuỗi HTML tự chứa, dùng trực tiếp làm ``message`` của ``_safe_sendmail``.
    """
    safe_title = _esc(title)
    greeting_html = (
        f'<tr><td style="padding:0 0 12px 0;font-size:15px;color:{_INK}">'
        f"Xin chào <b>{_esc(greeting)}</b>,</td></tr>"
        if greeting
        else ""
    )
    note_html = (
        f'<tr><td style="padding:16px 0 0 0;font-size:13px;color:{_MUTED}">'
        f"{_esc(note)}</td></tr>"
        if note
        else ""
    )

    return (
        f'<!DOCTYPE html><html lang="vi" {EMAIL_MARKER}>'
        f'<head><meta charset="utf-8" />'
        f'<meta name="viewport" content="width=device-width,initial-scale=1" />'
        f"<title>{safe_title}</title></head>"
        f'<body style="margin:0;padding:0;background:{_CANVAS};'
        f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,Arial,sans-serif">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:{_CANVAS};padding:24px 12px">'
        f'<tr><td align="center">'
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" '
        f'style="max-width:600px;width:100%;background:#ffffff;border:1px solid {_BORDER};'
        f'border-radius:12px;overflow:hidden">'
        # ── Header thương hiệu ──────────────────────────────────────────────
        f'<tr><td style="background:{_BRAND_COLOR};padding:20px 28px">'
        f'<div style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:.2px">'
        f"{BRAND_NAME}</div>"
        f'<div style="color:#dbeafe;font-size:13px;margin-top:2px">{BRAND_TAGLINE}</div>'
        f"</td></tr>"
        # ── Thân ────────────────────────────────────────────────────────────
        f'<tr><td style="padding:28px">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td style="padding:0 0 12px 0;font-size:19px;font-weight:600;color:{_INK}">'
        f"{safe_title}</td></tr>"
        f"{greeting_html}"
        f'<tr><td style="font-size:15px;line-height:1.6;color:{_INK}">{body_html}</td></tr>'
        f"{_cta_html(cta_label, cta_url)}"
        f"{note_html}"
        f"</table></td></tr>"
        # ── Chân trang ──────────────────────────────────────────────────────
        f'<tr><td style="background:#f9fafb;border-top:1px solid {_BORDER};'
        f'padding:16px 28px;font-size:12px;line-height:1.5;color:{_MUTED}">'
        f"{_FOOTER_TEXT}</td></tr>"
        f"</table></td></tr></table></body></html>"
    )
