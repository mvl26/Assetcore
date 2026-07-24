# Copyright (c) 2026, AssetCore Team
"""IMM-00 — Chính sách mật khẩu AssetCore: thông điệp tiếng Việt, KHÔNG HTML.

Frappe đánh giá độ mạnh mật khẩu bằng zxcvbn và khi trượt thì
``frappe/core/doctype/user/user.py::handle_password_test_fail`` **tự dựng một
khối HTML tiếng Anh** (``<div class="alert alert-warning">…</div><ul>…</ul>``)
rồi throw. Người dùng cuối AssetCore chỉ biết giao diện tiếng Việt, và FE không
render HTML thô từ backend → mọi đường đặt/đổi mật khẩu phải **tự kiểm TRƯỚC**
và trả thông điệp đã chuẩn hoá ở đây.

Tập chuỗi phản hồi của zxcvbn trong Frappe là **đóng** (24 chuỗi, xem
``frappe/utils/password_strength.py``) nên dịch được trọn vẹn; chuỗi lạ (Frappe
nâng cấp) rơi về câu tiếng Việt chung — KHÔNG bao giờ lọt tiếng Anh ra UI.
"""
from __future__ import annotations

from typing import Any

import frappe

#: Độ dài tối thiểu (ràng buộc của AssetCore, độc lập với điểm zxcvbn).
MIN_PASSWORD_LENGTH = 8

#: Câu mở đầu cho mọi lỗi mật khẩu yếu.
WEAK_PASSWORD_HEADLINE = "Mật khẩu chưa đủ mạnh."

#: Gợi ý chung khi không map được phản hồi cụ thể.
GENERIC_ADVICE = (
    "Hãy dùng mật khẩu dài hơn, kết hợp chữ hoa, chữ thường, số và ký tự đặc biệt; "
    "tránh từ ngữ thông dụng và thông tin cá nhân."
)

#: Bản dịch tiếng Việt cho TOÀN BỘ chuỗi phản hồi zxcvbn của Frappe.
#: Nguồn: ``frappe/utils/password_strength.py``.
FEEDBACK_VI: dict[str, str] = {
    # ── Cảnh báo (warning) ────────────────────────────────────────────────
    "This is a top-10 common password.":
        "Đây là một trong 10 mật khẩu bị dùng nhiều nhất.",
    "This is a top-100 common password.":
        "Đây là một trong 100 mật khẩu bị dùng nhiều nhất.",
    "This is a very common password.":
        "Đây là mật khẩu rất phổ biến.",
    "This is similar to a commonly used password.":
        "Mật khẩu này gần giống một mật khẩu phổ biến.",
    "A word by itself is easy to guess.":
        "Một từ đơn lẻ rất dễ đoán.",
    "Common words are easy to guess.":
        "Từ ngữ thông dụng rất dễ đoán.",
    "Names and surnames by themselves are easy to guess.":
        "Họ hoặc tên đứng một mình rất dễ đoán.",
    "Common names and surnames are easy to guess.":
        "Họ và tên thông dụng rất dễ đoán.",
    "Dates are often easy to guess.":
        "Ngày tháng thường rất dễ đoán.",
    "Recent years are easy to guess.":
        "Các năm gần đây rất dễ đoán.",
    "Straight rows of keys are easy to guess":
        "Dãy phím liền nhau trên bàn phím rất dễ đoán.",
    "Short keyboard patterns are easy to guess":
        "Chuỗi phím ngắn theo hình dạng bàn phím rất dễ đoán.",
    # ── Gợi ý (suggestions) ───────────────────────────────────────────────
    "Add numbers or special characters.":
        "Hãy thêm chữ số hoặc ký tự đặc biệt.",
    "All-uppercase is almost as easy to guess as all-lowercase.":
        "Viết hoa toàn bộ gần như dễ đoán ngang viết thường toàn bộ.",
    "Capitalization doesn't help very much.":
        "Chỉ viết hoa chữ cái đầu gần như không tăng độ an toàn.",
    "Predictable substitutions like '@' instead of 'a' don't help very much.":
        "Thay thế dễ đoán như '@' cho 'a' gần như không tăng độ an toàn.",
    "Avoid dates and years that are associated with you.":
        "Tránh ngày tháng và năm gắn với bản thân bạn.",
    "Avoid years that are associated with you.":
        "Tránh những năm gắn với bản thân bạn.",
    "Avoid sequences like abc or 6543 as they are easy to guess":
        "Tránh dãy liên tiếp như abc hoặc 6543 vì rất dễ đoán.",
    "Better add a few more letters or another word":
        "Hãy thêm vài ký tự nữa hoặc thêm một từ khác.",
    "Let's avoid repeated words and characters":
        "Tránh lặp lại từ và ký tự.",
    "Try to avoid repeated words and characters":
        "Hãy tránh lặp lại từ và ký tự.",
    "Make use of longer keyboard patterns":
        "Hãy dùng chuỗi phím dài hơn trên bàn phím.",
    "Try to use a longer keyboard pattern with more turns":
        "Hãy dùng chuỗi phím dài hơn và đổi hướng nhiều hơn.",
}


def translate_feedback(text: str) -> str:
    """Dịch một chuỗi phản hồi zxcvbn; chuỗi lạ → chuỗi rỗng (KHÔNG trả tiếng Anh)."""
    return FEEDBACK_VI.get((text or "").strip(), "")


def describe_feedback(feedback: dict[str, Any] | None) -> str:
    """Chuẩn hoá ``feedback`` của Frappe thành MỘT câu tiếng Việt, không HTML.

    Args:
        feedback: dict ``{"warning": str, "suggestions": [str, ...]}`` do
            ``frappe.core.doctype.user.user.test_password_strength`` trả về.

    Returns:
        Thông điệp tiếng Việt dạng text thuần, luôn khác rỗng.
    """
    feedback = feedback or {}
    parts: list[str] = [WEAK_PASSWORD_HEADLINE]

    warning = translate_feedback(feedback.get("warning") or "")
    if warning:
        parts.append(warning)

    tips = [
        vi
        for vi in (translate_feedback(s) for s in (feedback.get("suggestions") or []))
        if vi
    ]
    if tips:
        parts.append(" ".join(tips))
    elif not warning:
        # Không map được gì (Frappe đổi chuỗi) → vẫn phải là tiếng Việt.
        parts.append(GENERIC_ADVICE)

    return " ".join(parts)


def check_password(password: str, user_name: str | None = None) -> str | None:
    """Kiểm mật khẩu theo chính sách site; trả thông điệp tiếng Việt nếu KHÔNG đạt.

    Gọi hàm này TRƯỚC khi gán ``new_password``/``update_password`` để Frappe
    không có cơ hội throw khối HTML tiếng Anh của nó.

    Args:
        password: mật khẩu người dùng nhập.
        user_name: tên User (để zxcvbn phạt mật khẩu chứa họ tên/email).

    Returns:
        ``None`` nếu đạt; chuỗi thông điệp tiếng Việt nếu không đạt.
    """
    from frappe.core.doctype.user.user import test_password_strength

    if len(password or "") < MIN_PASSWORD_LENGTH:
        return f"Mật khẩu phải có tối thiểu {MIN_PASSWORD_LENGTH} ký tự."

    user_data = ()
    if user_name and frappe.db.exists("User", user_name):
        user_data = frappe.db.get_value(
            "User", user_name,
            ["first_name", "middle_name", "last_name", "email", "birth_date"],
        )

    feedback = (test_password_strength(password, user_data=user_data) or {}).get("feedback") or {}
    if feedback.get("password_policy_validation_passed") is False:
        return describe_feedback(feedback)
    return None
