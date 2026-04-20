# Copyright (c) 2026, AssetCore Team
"""Pagination helper for list APIs."""
import math


def paginate(total: int, page: int = 1, page_size: int = 20) -> dict:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), 100)
    total_pages = math.ceil(total / page_size) if total else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "offset": (page - 1) * page_size,
    }
