# Copyright (c) 2026, AssetCore Team
"""Standard API response envelope."""
from typing import Any


def _ok(data: Any = None) -> dict:
    return {"success": True, "data": data}


def _err(msg: str, code: int = 400) -> dict:
    return {"success": False, "error": msg, "code": code}
