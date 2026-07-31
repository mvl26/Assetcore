# Copyright (c) 2026, AssetCore Team
"""Pagination helper for list APIs."""
import math

# SSoT upper-cap số bản ghi / 1 trang list (ADR-IMM00-LIST-SCOPE). Định nghĩa
# DUY NHẤT 1 nơi — KHÔNG rải literal 100 ở handler. Mọi list-endpoint phải dùng
# ``paginate(...)["page_size"]`` (đã clamp) làm ``limit_page_length`` truyền vào
# frappe.get_list, để metadata trang == limit query thực ⇒ invariant
# ``len(items) <= pagination.page_size`` giữ + chống truy vấn vô giới hạn (DoS/perf,
# client gửi page_size khổng lồ). Đổi cap ở ĐÂY tác động toàn hệ.
_MAX_PAGE_SIZE = 100


def clamp_page_size(value, default: int = 20) -> int:
    """CLAMP một ``limit``/``page_size`` thô của client về ``[1, _MAX_PAGE_SIZE]``.

    SSoT trần trang cho endpoint list **KHÔNG** đi qua :func:`paginate` (gọi thẳng
    ``frappe.get_all(limit_page_length=...)``) — trước CR-69 các endpoint đó rải
    literal ``100`` hoặc truyền ``limit`` thô, sinh 2 lỗi:

    * ``limit_page_length=0`` trong Frappe nghĩa là **KHÔNG GIỚI HẠN** ⇒ so sánh
      ``len(rows) < 0`` luôn False ⇒ :func:`~assetcore.services.shared.truncation.truncation_meta`
      COUNT thừa rồi báo **cắt oan** (``truncated=1`` khi không dòng nào bị cắt).
    * ``limit`` khổng lồ ⇒ truy vấn vô giới hạn (DoS/perf).

    Args:
        value: giá trị thô (client/param). Falsy (``0``/``None``/``""``) → ``default``.
        default: giá trị thay thế khi ``value`` falsy — dùng default của CHÍNH
            endpoint (vd 10) để hành vi khớp tài liệu API của nó.

    Returns:
        int trong ``[1, _MAX_PAGE_SIZE]``.
    """
    return min(max(int(value or default), 1), _MAX_PAGE_SIZE)


def paginate(total: int, page: int = 1, page_size: int = 20) -> dict:
    """Trả metadata phân trang với ``page_size`` đã CLAMP về ``[1, _MAX_PAGE_SIZE]``.

    Giá trị ``page_size`` trong dict trả về là SSoT giới hạn trang: handler PHẢI
    dùng nó (``pag["page_size"]``) làm ``limit_page_length`` cho frappe.get_list —
    KHÔNG truyền ``page_size`` thô của client (chống ``limit -5`` SQL-crash khi âm
    + truy vấn vô giới hạn khi quá lớn). ``offset`` cũng tính từ page_size đã clamp.
    """
    page = max(int(page or 1), 1)
    page_size = clamp_page_size(page_size, 20)
    total_pages = math.ceil(total / page_size) if total else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "offset": (page - 1) * page_size,
    }
