# Copyright (c) 2026, AssetCore Team
"""Phân trang ``Bundle`` — SPEC §10, §13 ("2 trang liền kề RỜI RẠC").

Bất biến bắt buộc: sắp xếp phải có TIEBREAKER
----------------------------------------------
Sắp theo một cột không duy nhất (``modified``, ``creation``) rồi phân trang bằng
``LIMIT/OFFSET`` là hỏng khi có bản ghi **trùng giá trị**: thứ tự giữa chúng do
storage engine quyết, khác nhau giữa hai truy vấn ⇒ trang 2 lặp lại bản ghi của
trang 1 **và** bỏ sót bản ghi khác. Người dùng không thấy lỗi — chỉ thấy thiếu dữ liệu.

Lỗi này đã có thật trong repo (``api/imm00.py:293`` thiếu tiebreaker, ghi trong sổ
nợ Đợt 0). Ở FHIR nó nặng hơn: client đồng bộ trọn bộ qua phân trang sẽ mất bản ghi
mà không có cách nào biết.

Nên :func:`order_by` **luôn** nối ``name`` làm khoá phụ — ``name`` là PRIMARY KEY
nên bảo đảm thứ tự toàn phần.
"""

from __future__ import annotations

from urllib.parse import urlencode

#: Số bản ghi mỗi trang khi client không truyền ``_count``.
DEFAULT_COUNT = 20
#: Trần cứng — chặn client kéo cả bảng trong một nhịp (R4 cho phép server giới hạn).
MAX_COUNT = 200


def clamp_count(raw: str | int | None) -> int:
    """Ép ``_count`` về khoảng hợp lệ.

    Giá trị lạ (âm, chữ, quá lớn) được quy về mặc định/trần thay vì báo lỗi — R4
    cho phép server tự giới hạn, và trả lỗi ở đây làm client lạ tắc ngay bước đầu.

    Args:
        raw: giá trị ``_count`` client truyền.

    Returns:
        Số bản ghi mỗi trang, trong ``[1, MAX_COUNT]``.
    """
    try:
        value = int(raw) if raw is not None else DEFAULT_COUNT
    except (TypeError, ValueError):
        return DEFAULT_COUNT
    if value < 1:
        return DEFAULT_COUNT
    return min(value, MAX_COUNT)


def order_by(sort_field: str = "modified", descending: bool = True) -> str:
    """Mệnh đề ``ORDER BY`` **luôn kèm tiebreaker** ``name``.

    Args:
        sort_field: cột sắp chính.
        descending: True = giảm dần.

    Returns:
        Chuỗi cho tham số ``order_by`` của Frappe, vd ``"modified desc, name desc"``.
    """
    direction = "desc" if descending else "asc"
    if sort_field == "name":
        return f"name {direction}"
    return f"{sort_field} {direction}, name {direction}"


def links(
    base: str,
    params: dict[str, str],
    *,
    offset: int,
    count: int,
    total: int,
) -> tuple[str, str | None, str | None]:
    """Dựng bộ link ``self`` / ``next`` / ``previous`` cho ``Bundle``.

    Args:
        base: URL type-level, vd ``https://site/fhir/R4/Device``.
        params: tham số truy vấn hiện tại (không gồm ``_offset``/``_count``).
        offset: vị trí bắt đầu của trang hiện tại.
        count: số bản ghi mỗi trang.
        total: tổng số bản ghi khớp.

    Returns:
        ``(self_link, next_link, previous_link)`` — ``None`` khi không có trang đó.
    """
    def _url(off: int) -> str:
        query = {**params, "_count": str(count), "_offset": str(off)}
        return f"{base}?{urlencode(sorted(query.items()))}"

    self_link = _url(offset)
    next_link = _url(offset + count) if offset + count < total else None
    prev_link = _url(max(offset - count, 0)) if offset > 0 else None
    return self_link, next_link, prev_link
