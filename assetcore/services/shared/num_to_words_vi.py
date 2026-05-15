# Copyright (c) 2026, AssetCore Team
"""Tiện ích đọc số tiền thành chữ tiếng Việt (VND).

Dùng chung cho mọi DocType cần hiển thị "số tiền bằng chữ"
(VD: Service Contract, Procurement, ...).
"""
from __future__ import annotations

_DIGITS = ("không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín")
_UNITS = ("", "nghìn", "triệu", "tỷ")


def _read_three_digits(number: int, full: bool) -> str:
    """Đọc một nhóm 3 chữ số.

    Args:
        number: giá trị 0..999.
        full: True nếu đây không phải nhóm cao nhất (cần đọc cả số 0 hàng trăm).
    """
    hundred, rem = divmod(number, 100)
    ten, unit = divmod(rem, 10)
    parts: list[str] = []

    if hundred > 0 or full:
        parts.append(_DIGITS[hundred])
        parts.append("trăm")

    if ten == 0:
        if unit > 0 and (hundred > 0 or full):
            parts.append("lẻ")
        if unit > 0:
            parts.append(_DIGITS[unit])
    elif ten == 1:
        parts.append("mười")
        if unit == 5:
            parts.append("lăm")
        elif unit > 0:
            parts.append(_DIGITS[unit])
    else:
        parts.append(_DIGITS[ten])
        parts.append("mươi")
        if unit == 1:
            parts.append("mốt")
        elif unit == 5:
            parts.append("lăm")
        elif unit > 0:
            parts.append(_DIGITS[unit])

    return " ".join(parts)


def num_to_words_vi(amount: float) -> str:
    """Đọc số tiền VND thành chữ tiếng Việt.

    Args:
        amount: số tiền (>= 0). Phần thập phân được làm tròn về số nguyên đồng.

    Returns:
        Chuỗi tiền bằng chữ, viết hoa chữ cái đầu, kết thúc bằng "đồng".
        Ví dụ: ``num_to_words_vi(1000000) == "Một triệu đồng"``.

    Raises:
        ValueError: khi ``amount`` âm.
    """
    if amount < 0:
        raise ValueError("Số tiền không được âm.")

    number = int(round(amount))
    if number == 0:
        return "Không đồng"

    groups: list[int] = []
    while number > 0:
        number, rem = divmod(number, 1000)
        groups.append(rem)

    segments: list[str] = []
    highest = len(groups) - 1
    for idx in range(highest, -1, -1):
        grp = groups[idx]
        if grp == 0:
            continue
        text = _read_three_digits(grp, full=(idx != highest))
        unit = _UNITS[idx]
        segments.append(f"{text} {unit}".strip())

    result = " ".join(segments).strip()
    return result[0].upper() + result[1:] + " đồng"
