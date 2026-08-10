# Copyright (c) 2026, AssetCore Team
"""SSoT truncation-meta cho endpoint list KHÔNG phân trang (CR-43 / CR-46 / CR-47).

Hợp đồng TRUNG THỰC khi cắt danh sách: một endpoint list không-phân-trang phục vụ
mobile PHẢI công bố ``total`` / ``truncated`` thay vì cắt IM LẶNG (client tưởng đã
xem hết trong khi còn phiếu chưa hiển thị). ``truncation_meta`` là quy ước DUY NHẤT
để mọi endpoint như vậy (imm00 inbox / imm06 competencies / imm08 due-PM /
imm11 due-calibration) derive cặp cờ này ĐỒNG NHẤT — KHÔNG mỗi nơi tự đếm một kiểu.
"""
from __future__ import annotations

from typing import Callable


def truncation_meta(
    fetched: int, limit: int, count_fn: Callable[[], int]
) -> tuple[int, int]:
    """Derive ``(total, truncated)`` cho một nguồn list bị cắt cứng theo ``limit``.

    ZERO-COST ở ca thường (AC2): khi ``fetched < limit`` (truy vấn trả ÍT hơn trần
    ⇒ đã lấy hết, KHÔNG còn dòng nào bị cắt) thì ``total = fetched`` và
    ``truncated = 0`` mà **KHÔNG** gọi ``count_fn()`` — không phát thêm query COUNT.
    CHỈ khi ``fetched >= limit`` (đã chạm trần, NGHI còn phiếu) mới gọi ``count_fn()``
    để lấy COUNT DB thật trên ĐÚNG filter-set trước khi cắt; ``truncated = 1`` khi
    ``total > limit`` (thật sự còn phiếu chưa hiển thị), ngược lại ``0`` (vừa khít trần).

    Args:
        fetched: số dòng THỰC lấy được (``len(rows)`` sau khi áp trần ``limit``).
        limit: trần cứng đã áp cho truy vấn (``page_size`` / ``limit_page_length``).
        count_fn: callable KHÔNG tham số trả COUNT DB (int) trên CÙNG predicate với
            truy vấn lấy rows — CHỈ được gọi khi ``fetched >= limit`` (lazy, tránh
            COUNT thừa ca không-cắt).

    Returns:
        tuple[int, int]: ``(total, truncated)`` — cả hai là int ≥ 0; ``truncated``
        ∈ {0, 1} (KHÔNG bool, KHÔNG None — parity CR-01, tránh Dart/Kotlin
        int-vs-bool crash khi codegen).
    """
    if fetched < limit:
        return fetched, 0
    total = int(count_fn())
    truncated = 1 if total > limit else 0
    return total, truncated
