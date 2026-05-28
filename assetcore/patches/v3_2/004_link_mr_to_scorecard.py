"""Patch v3_2.004 — BUG-017 backfill.

Liên kết IMM Management Review (MR) tồn tại trước đây mà chưa có
``scorecard_ref`` với IMM Compliance Scorecard cùng quý.

Quy ước map:
- MR.quarter ``Q[1-4]-YYYY`` → tháng (q-1)*3+1 … q*3 trong năm YYYY.
- Ưu tiên scorecard ``is_published=1``, sau đó là ``period_month`` lớn nhất.
- Scope mặc định ``"Hospital"``.
"""

from __future__ import annotations

import re

import frappe

_QUARTER_RE = re.compile(r"^Q([1-4])-(\d{4})$")


def execute() -> None:
    rows = frappe.get_all(
        "IMM Management Review",
        filters={"scorecard_ref": ("in", ["", None])},
        fields=["name", "quarter"],
    )
    if not rows:
        print("[patch v3_2.004] No MR rows need scorecard linking")
        return

    linked = 0
    skipped = 0
    for r in rows:
        q = r.get("quarter") or ""
        m = _QUARTER_RE.match(str(q))
        if not m:
            skipped += 1
            continue
        q_idx = int(m.group(1))
        year = int(m.group(2))
        months = list(range((q_idx - 1) * 3 + 1, q_idx * 3 + 1))
        sc_rows = frappe.get_all(
            "IMM Compliance Scorecard",
            filters={
                "period_year": year,
                "period_month": ("in", months),
                "scope": "Hospital",
            },
            fields=["name", "is_published", "period_month"],
            order_by="is_published desc, period_month desc",
            limit=1,
        )
        if not sc_rows:
            skipped += 1
            continue
        frappe.db.set_value(
            "IMM Management Review", r["name"],
            "scorecard_ref", sc_rows[0]["name"],
            update_modified=False,
        )
        linked += 1

    if linked:
        frappe.db.commit()
    print(f"[patch v3_2.004] MR scorecard backfill — linked={linked} skipped={skipped}")
