# Copyright (c) 2026, AssetCore Team
# Depreciation & Asset Accounting API — IMM-06 (Financial lifecycle)
from __future__ import annotations

import math
from datetime import date

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, date_diff

from assetcore.utils.helpers import _err, _ok

_DT_ASSET = "AC Asset"

_DEPR_FIELDS = [
    "name", "asset_name", "asset_category",
    "department", "location",
    "purchase_date", "in_service_date",
    "gross_purchase_amount", "residual_value",
    "depreciation_method", "useful_life_years",
    "accumulated_depreciation", "current_book_value",
    "lifecycle_status",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _compute_one(asset: dict) -> dict:
    """Return updated depreciation numbers for a single asset dict (no DB write)."""
    gross    = float(asset.get("gross_purchase_amount") or 0)
    residual = float(asset.get("residual_value") or 0)
    years    = int(asset.get("useful_life_years") or 0)
    start    = asset.get("in_service_date")
    method   = (asset.get("depreciation_method") or "").strip()

    if not method or method == "None" or gross <= 0 or years <= 0 or not start:
        return {"accumulated": float(asset.get("accumulated_depreciation") or 0),
                "book_value":  float(asset.get("current_book_value") or gross),
                "configured":  False, "pct_depreciated": 0.0}

    depreciable  = max(0.0, gross - residual)
    days_elapsed = max(0, date_diff(nowdate(), getdate(start)))
    total_days   = years * 365

    if method == "Double Declining":
        rate        = 2.0 / years
        accumulated = min(depreciable, depreciable * rate * (days_elapsed / 365))
    else:  # Straight Line (default)
        accumulated = min(depreciable, depreciable * days_elapsed / total_days)

    accumulated = round(accumulated, 0)
    book_value  = round(gross - accumulated, 0)
    pct         = round(accumulated / gross * 100, 1) if gross > 0 else 0.0
    return {"accumulated": accumulated, "book_value": book_value,
            "configured": True, "pct_depreciated": pct}


def _yearly_schedule(asset: dict) -> list[dict]:
    """Yearly depreciation schedule from in_service_date to end-of-life."""
    gross    = float(asset.get("gross_purchase_amount") or 0)
    residual = float(asset.get("residual_value") or 0)
    years    = int(asset.get("useful_life_years") or 0)
    start    = asset.get("in_service_date")
    method   = (asset.get("depreciation_method") or "").strip()

    if not method or method == "None" or gross <= 0 or years <= 0 or not start:
        return []

    depreciable = max(0.0, gross - residual)
    start_date  = getdate(start)
    rows = []

    if method == "Double Declining":
        rate = 2.0 / years
        book = gross
        for yr in range(1, years + 1):
            annual = round(min(book - residual, book * rate), 0)
            book   = round(book - annual, 0)
            rows.append({
                "year":        start_date.year + yr - 1,
                "annual_depr": annual,
                "accumulated": round(gross - book, 0),
                "book_value":  max(residual, book),
            })
    else:  # Straight Line
        annual = round(depreciable / years, 0)
        accumulated = 0.0
        for yr in range(1, years + 1):
            this_yr = annual if yr < years else round(depreciable - accumulated, 0)
            accumulated += this_yr
            rows.append({
                "year":        start_date.year + yr - 1,
                "annual_depr": this_yr,
                "accumulated": accumulated,
                "book_value":  round(gross - accumulated, 0),
            })

    return rows


# ─── API ──────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_assets_depreciation(page: int = 1, page_size: int = 50,
                              method_filter: str = "",
                              status_filter: str = "",
                              category_filter: str = "") -> dict:
    """List all assets with live-computed depreciation values."""
    filters: dict = {}
    if method_filter:
        filters["depreciation_method"] = method_filter
    if status_filter:
        filters["lifecycle_status"] = status_filter
    if category_filter:
        filters["asset_category"] = category_filter

    page    = int(page)
    pg_size = int(page_size)
    total   = frappe.db.count(_DT_ASSET, filters)

    assets = frappe.get_all(
        _DT_ASSET, filters=filters,
        fields=_DEPR_FIELDS,
        limit_start=(page - 1) * pg_size,
        limit_page_length=pg_size,
        order_by="asset_name asc",
    )

    # Enrich with computed values
    for a in assets:
        computed = _compute_one(a)
        a["accumulated_depreciation"] = computed["accumulated"]
        a["current_book_value"]       = computed["book_value"]
        a["configured"]               = computed["configured"]
        a["pct_depreciated"]          = computed["pct_depreciated"]

    return _ok({"items": assets, "pagination": {"page": page, "page_size": pg_size, "total": total}})


@frappe.whitelist()
def get_depreciation_stats() -> dict:
    """Aggregate accounting stats across all configured assets."""
    assets = frappe.get_all(_DT_ASSET, fields=_DEPR_FIELDS)

    total_gross       = 0.0
    total_accumulated = 0.0
    total_book        = 0.0
    configured_count  = 0
    unconfigured      = 0
    fully_depreciated = 0
    by_method: dict[str, int]   = {}
    by_category: dict[str, float] = {}

    for a in assets:
        gross   = float(a.get("gross_purchase_amount") or 0)
        total_gross += gross

        computed = _compute_one(a)
        if not computed["configured"]:
            unconfigured += 1
            total_book   += gross
            continue

        configured_count += 1
        acc   = computed["accumulated"]
        bv    = computed["book_value"]
        total_accumulated += acc
        total_book        += bv

        if bv <= float(a.get("residual_value") or 0) + 1:
            fully_depreciated += 1

        m = (a.get("depreciation_method") or "Khác").strip()
        by_method[m] = by_method.get(m, 0) + 1

        cat = a.get("asset_category") or "Chưa phân loại"
        by_category[cat] = by_category.get(cat, 0.0) + bv

    overall_pct = round(total_accumulated / total_gross * 100, 1) if total_gross > 0 else 0.0

    return _ok({
        "total_assets":        len(assets),
        "configured_count":    configured_count,
        "unconfigured_count":  unconfigured,
        "fully_depreciated":   fully_depreciated,
        "total_gross":         round(total_gross, 0),
        "total_accumulated":   round(total_accumulated, 0),
        "total_book_value":    round(total_book, 0),
        "overall_pct":         overall_pct,
        "by_method":           [{"method": k, "count": v} for k, v in by_method.items()],
        "by_category":         sorted(
            [{"category": k, "book_value": v} for k, v in by_category.items()],
            key=lambda x: -x["book_value"]
        )[:8],
    })


@frappe.whitelist()
def compute_one_depreciation(name: str) -> dict:
    """Compute and persist depreciation for a single asset."""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_("Không tìm thấy thiết bị"), 404)

    a = frappe.db.get_value(_DT_ASSET, name, _DEPR_FIELDS, as_dict=True) or {}
    computed = _compute_one(a)

    if computed["configured"]:
        frappe.db.set_value(_DT_ASSET, name, {
            "accumulated_depreciation": computed["accumulated"],
            "current_book_value":       computed["book_value"],
        })
        frappe.db.commit()

    return _ok({**computed, "name": name})


@frappe.whitelist(methods=["POST"])
def compute_all_depreciation() -> dict:
    """Batch compute and persist depreciation for all configured assets."""
    assets = frappe.get_all(_DT_ASSET, fields=_DEPR_FIELDS)
    updated = 0
    skipped = 0

    for a in assets:
        computed = _compute_one(a)
        if not computed["configured"]:
            skipped += 1
            continue
        frappe.db.set_value(_DT_ASSET, a["name"], {
            "accumulated_depreciation": computed["accumulated"],
            "current_book_value":       computed["book_value"],
        })
        updated += 1

    if updated:
        frappe.db.commit()

    return _ok({"updated": updated, "skipped": skipped})


@frappe.whitelist()
def get_depreciation_schedule(name: str) -> dict:
    """Return yearly depreciation schedule for a single asset."""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_("Không tìm thấy thiết bị"), 404)

    a       = frappe.db.get_value(_DT_ASSET, name, _DEPR_FIELDS, as_dict=True) or {}
    schedule = _yearly_schedule(a)
    today_year = date.today().year

    for row in schedule:
        row["is_current"] = row["year"] == today_year
        row["is_future"]  = row["year"] > today_year

    return _ok({
        "name":        name,
        "asset_name":  a.get("asset_name"),
        "gross":       float(a.get("gross_purchase_amount") or 0),
        "residual":    float(a.get("residual_value") or 0),
        "method":      a.get("depreciation_method"),
        "years":       a.get("useful_life_years"),
        "in_service":  str(a.get("in_service_date") or ""),
        "schedule":    schedule,
    })
