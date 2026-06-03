"""Backfill ``IMM Management Review.quarter`` from ``review_date``.

BUG-002: 36/39 MR rows on miyano site had ``quarter = "Q1-2099"`` (leaked from
``tests/test_imm16.py`` seed data). The controller's ``before_insert`` only
computed quarter when empty, so a stale literal was preserved on bulk reuse.
This patch re-derives quarter from ``review_date`` for every row currently
holding "Q1-2099" (or any quarter whose year is > current_year + 1, i.e.
implausible). Idempotent — safe to re-run.
"""
from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate


def _quarter_from_date(d) -> str:
    gd = getdate(d)
    q = (gd.month - 1) // 3 + 1
    return f"Q{q}-{gd.year}"


def execute() -> None:
    current_year = getdate(nowdate()).year
    rows = frappe.db.sql(
        """
        SELECT name, quarter, review_date
        FROM `tabIMM Management Review`
        WHERE review_date IS NOT NULL
        """,
        as_dict=True,
    )
    if not rows:
        return

    updated = 0
    for r in rows:
        # Detect rows with implausible year (e.g. 2099 leak) or where the
        # stored quarter does not match what review_date implies.
        try:
            stored_year = int(str(r.quarter or "").split("-", 1)[1])
        except (IndexError, ValueError):
            stored_year = 0

        new_quarter = _quarter_from_date(r.review_date)
        needs_fix = (
            r.quarter != new_quarter
            and (stored_year > current_year + 1 or r.quarter == "Q1-2099")
        )
        if not needs_fix:
            continue

        frappe.db.set_value(
            "IMM Management Review", r.name, "quarter", new_quarter,
            update_modified=False,
        )
        updated += 1

    frappe.db.commit()
    print(
        f"[patches.v3_2.002_fix_mr_quarter_q1_2099] "
        f"checked={len(rows)} updated={updated}"
    )
