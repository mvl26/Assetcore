# Copyright (c) 2026, AssetCore Team
"""Filter helpers shared by IMM list endpoints.

Two responsibilities:
1. `normalize_filters()` — wrap raw lists in ``["in", value]`` so Frappe
   does not misinterpret them as ``[op, value]`` pairs.
2. `pop_search()` + `count_with_or()` — translate the FE free-text
   ``search`` filter key into ``or_filters`` LIKE clauses. The FE puts
   ``search`` into the same dict as column filters; if it leaks through to
   ``frappe.get_list`` we get ``Unknown column 'tab<DocType>.search'``.
"""
from __future__ import annotations

import frappe

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


_LINK_LOOKUP_LIMIT = 500


def pop_search(
    f: dict | None,
    searchable_fields: list[str],
    *,
    link_search: dict[str, tuple[str, str]] | None = None,
) -> tuple[dict, list | None]:
    """Pop the FE free-text ``search`` key and translate it to ``or_filters``.

    The FE list views put ``search`` into the same filter dict as the column
    filters (e.g. ``{"workflow_state": "Draft", "search": "NR-2026"}``). If
    the BE passes the dict straight to ``frappe.get_list`` MariaDB rejects
    with ``Unknown column 'tab<DocType>.search' in 'WHERE'``.

    This helper extracts ``search`` and returns an ``or_filters`` list of
    ``[field, "like", "%search%"]`` triples — one per ``searchable_fields``.

    Args:
        f: filter dict from API layer, may contain a ``search`` key.
        searchable_fields: fields on the parent DocType to OR-LIKE the term
            across (direct LIKE on parent columns).
        link_search: optional ``{link_field: (linked_doctype, display_field)}``.
            Use when the FE placeholder promises searching by the **display
            name** of a Link target (e.g. "tên model" — model_name lives on
            ``IMM Device Model``, not on the parent). For each entry the
            helper looks up linked rows whose ``display_field`` LIKE the
            term, then adds ``[link_field, "in", [matched_ids]]`` to the OR
            clause. Lookup is capped at ``_LINK_LOOKUP_LIMIT`` matches.

    Returns:
        ``(filters_without_search, or_filters_or_None)``. Pass both straight
        to ``frappe.get_list`` / :func:`count_with_or`.
    """
    f = dict(f or {})
    raw = f.pop("search", None)
    if raw is None:
        return f, None
    term = str(raw).strip()
    if not term:
        return f, None
    like = f"%{term}%"
    or_filters: list = [[field, "like", like] for field in searchable_fields]
    for link_field, (linked_doctype, display_field) in (link_search or {}).items():
        try:
            rows = frappe.get_all(
                linked_doctype,
                or_filters=[
                    [display_field, "like", like],
                    ["name", "like", like],
                ],
                fields=["name"],
                limit_page_length=_LINK_LOOKUP_LIMIT,
                ignore_permissions=True,
            )
        except Exception:
            rows = []
        ids = [r["name"] for r in rows]
        if ids:
            or_filters.append([link_field, "in", ids])
    return f, or_filters


def count_with_or(
    doctype: str,
    filters: dict | None,
    or_filters: list | None,
) -> int:
    """Count rows matching ``filters`` AND/OR ``or_filters`` — permission-aware.

    INVARIANT (ADR-IMM00-LIST-SCOPE §4b): the total MUST be computed with the
    **same predicate that ``frappe.get_list`` applies to the items** — including
    ``permission_query_conditions`` (row-scope hooks). The previous implementation
    used ``frappe.db.count`` / ``frappe.get_all``, **neither of which applies
    ``permission_query_conditions``**, so for a row-scoped persona (vendor /
    internal technician before the read-all fix) the count counted EVERY row while
    ``get_list`` returned only the scoped subset → header "Tổng N" ≠ số dòng thực.

    Fix: count via ``frappe.get_list(..., limit_page_length=0)`` for BOTH the
    search (``or_filters``) and non-search paths. ``get_list`` runs the same
    ``DatabaseQuery`` engine as the items query and applies the same
    ``permission_query_conditions`` + DocPerm checks ⇒ ``count == len(items)`` for
    every persona on every list endpoint that pairs this helper with
    ``frappe.get_list`` (AC Asset / NR / Plan Period / Tender Spec / Vendor Eval /
    Procurement Document). ``or_filters`` is preserved verbatim for free-text LIKE
    search parity.

    NOTE: ``limit_page_length=0`` materializes the matching ``name`` list (capped
    by the bounded dataset). Acceptable at current scale (~1.4k assets); see ADR
    §4b ROADMAP for a streaming count if a dataset grows past ~50k.
    """
    rows = frappe.get_list(
        doctype,
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=["name"],
        limit_page_length=0,
    )
    return len(rows)
