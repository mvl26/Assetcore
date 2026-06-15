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


def paginate(total: int, page: int = 1, page_size: int = 20) -> dict:
    """Trả metadata phân trang với ``page_size`` đã CLAMP về ``[1, _MAX_PAGE_SIZE]``.

    Giá trị ``page_size`` trong dict trả về là SSoT giới hạn trang: handler PHẢI
    dùng nó (``pag["page_size"]``) làm ``limit_page_length`` cho frappe.get_list —
    KHÔNG truyền ``page_size`` thô của client (chống ``limit -5`` SQL-crash khi âm
    + truy vấn vô giới hạn khi quá lớn). ``offset`` cũng tính từ page_size đã clamp.
    """
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), _MAX_PAGE_SIZE)
    total_pages = math.ceil(total / page_size) if total else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "offset": (page - 1) * page_size,
    }
