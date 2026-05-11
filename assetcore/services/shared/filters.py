# Copyright (c) 2026, AssetCore Team
"""Filter normalization helper for service list functions.

Centralizes the `_norm()` utility used by IMM-06, IMM-15, IMM-16 to prevent
each service from duplicating the same operator-token logic.
"""
from __future__ import annotations

_OP_TOKENS = ("in", "not in", "between", "like", "=", "!=", "<", ">", "<=", ">=")


def normalize_filters(f: dict | None) -> dict:
    """Normalize list values in a filter dict to Frappe [op, value] format.

    Frappe `get_all` filters accept either scalar values or [op, value] pairs.
    A raw list without an operator prefix is ambiguous — this function wraps
    such lists in ``["in", value]`` so callers can pass plain Python lists.

    Args:
        f: filter dict from API/service layer, or None.

    Returns:
        Normalized filter dict safe to pass to `frappe.get_all`.
    """
    out: dict = {}
    for k, v in (f or {}).items():
        if isinstance(v, list) and v and not (len(v) == 2 and v[0] in _OP_TOKENS):
            out[k] = ["in", v]
        else:
            out[k] = v
    return out
