# Copyright (c) 2026, AssetCore Team
"""AC Asset depreciation — schedule generator + monthly executor.

Nguyên tắc:
  - Luật khấu hao (method, months, frequency, residual%) được lưu tại AC Asset Category.
  - Asset kế thừa từ Category qua Model.
  - Khi Asset được tạo, `generate_schedule()` sinh ra các dòng AC Asset Depreciation Schedule
    với status=Pending.
  - Cron `run_due_depreciation()` chạy định kỳ (daily), quét các dòng Pending có
    scheduled_date <= today, đánh dấu Executed và cập nhật
    asset.accumulated_depreciation + asset.current_book_value.
"""

from __future__ import annotations

import frappe
from frappe.utils import add_days, add_months, flt, getdate, nowdate, today

_DT_ASSET = "AC Asset"
_DT_SCHED = "AC Asset Depreciation Schedule"

_FREQ_MONTHS: dict[str, int] = {
    "Monthly":   1,
    "Quarterly": 3,
    "Yearly":    12,
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _period_end_date(start_date, period_idx: int, months_per_period: int):
    """Tính end date của kỳ thứ period_idx (0-based).

    Kỳ 0 kết thúc vào cuối khoảng đầu tiên. Ngày được lấy là ngày cuối của tháng.
    """
    # start + (idx+1) * months_per_period → first day of next period, then -1 day
    next_boundary = add_months(start_date, (period_idx + 1) * months_per_period)
    return add_days(next_boundary, -1)


def _straight_line_amounts(depreciable_base: float, periods: int) -> list[float]:
    """Straight Line: chia đều, kỳ cuối điều chỉnh rounding."""
    if periods <= 0:
        return []
    base_amt = round(depreciable_base / periods, 2)
    amounts = [base_amt] * (periods - 1)
    amounts.append(round(depreciable_base - sum(amounts), 2))
    return amounts


def _double_declining_amounts(
    gross: float, residual: float, periods: int, months_per_period: int,
) -> list[float]:
    """Double Declining Balance: rate = 2 / (life_years), per-period = rate/periods_per_year.

    Dừng khi book value chạm residual.
    """
    if periods <= 0:
        return []
    total_months = periods * months_per_period
    life_years = max(total_months / 12.0, 1.0)
    annual_rate = 2.0 / life_years
    periods_per_year = 12.0 / months_per_period
    period_rate = annual_rate / periods_per_year

    amounts: list[float] = []
    book = float(gross)
    for i in range(periods):
        remaining_periods = periods - i
        candidate = round(book * period_rate, 2)
        # Nếu kỳ cuối, trả hết phần còn lại về residual
        if remaining_periods == 1:
            candidate = round(book - residual, 2)
        # Không vượt quá (book - residual)
        max_depr = round(book - residual, 2)
        if candidate > max_depr:
            candidate = max_depr
        if candidate < 0:
            candidate = 0.0
        amounts.append(candidate)
        book -= candidate
    return amounts


# ─── Schedule Generator ──────────────────────────────────────────────────────

def generate_schedule(asset_name: str, *, force: bool = False) -> dict:
    """Sinh bảng lịch khấu hao cho 1 Asset.

    Args:
        asset_name: AC Asset name
        force: Nếu True, xóa schedule cũ trước khi sinh. Nếu False, bỏ qua
               nếu đã có schedule.

    Returns: {"asset": name, "periods": n, "total_depreciable": amount}
    """
    asset = frappe.get_doc(_DT_ASSET, asset_name)

    if not force and asset.get("depreciation_schedule"):
        return {"asset": asset_name, "periods": 0, "skipped": True,
                "reason": "Schedule đã tồn tại, dùng force=True để regen"}

    method       = (asset.depreciation_method or "").strip()
    total_months = int(asset.total_depreciation_months or 0)
    frequency    = (asset.depreciation_frequency or "Monthly").strip()
    months_per_period = _FREQ_MONTHS.get(frequency, 1)
    gross        = flt(asset.gross_purchase_amount or 0)
    residual     = flt(asset.residual_value or 0)
    start_date   = asset.depreciation_start_date or asset.in_service_date or asset.commissioning_date

    if not method or total_months <= 0 or gross <= 0 or not start_date:
        return {"asset": asset_name, "periods": 0, "skipped": True,
                "reason": "Thiếu method / total_months / gross / start_date"}
    if residual >= gross:
        return {"asset": asset_name, "periods": 0, "skipped": True,
                "reason": "Residual >= gross, không cần khấu hao"}

    periods = total_months // months_per_period
    if periods <= 0:
        return {"asset": asset_name, "periods": 0, "skipped": True,
                "reason": "total_months < frequency, không sinh được kỳ nào"}

    depreciable_base = gross - residual

    if method == "Straight Line":
        amounts = _straight_line_amounts(depreciable_base, periods)
    elif method == "Double Declining":
        amounts = _double_declining_amounts(gross, residual, periods, months_per_period)
    else:
        # Units of Production hoặc chưa hỗ trợ → fallback Straight Line
        amounts = _straight_line_amounts(depreciable_base, periods)

    # Clear + append
    asset.set("depreciation_schedule", [])
    accumulated = 0.0
    for i, amt in enumerate(amounts):
        accumulated += amt
        remaining = max(gross - accumulated, residual)
        asset.append("depreciation_schedule", {
            "period_number": i + 1,
            "scheduled_date": _period_end_date(start_date, i, months_per_period),
            "depreciation_amount": amt,
            "accumulated_amount": accumulated,
            "remaining_value": remaining,
            "status": "Pending",
        })
    asset.save(ignore_permissions=True)

    return {
        "asset": asset_name,
        "periods": len(amounts),
        "total_depreciable": depreciable_base,
        "method": method,
        "frequency": frequency,
    }


# ─── Cron: Execute due periods ───────────────────────────────────────────────

def run_due_depreciation(as_of: str | None = None) -> dict:
    """Chạy định kỳ: đánh dấu Executed cho các dòng Pending đến hạn,
    cập nhật accumulated_depreciation + current_book_value trên Asset.

    Args:
        as_of: ISO date (YYYY-MM-DD). Mặc định là today.

    Returns: {"executed_rows": N, "updated_assets": M}
    """
    cutoff = getdate(as_of or today())

    rows = frappe.db.sql("""
        SELECT d.name, d.parent AS asset, d.depreciation_amount, d.period_number
        FROM `tabAC Asset Depreciation Schedule` d
        JOIN `tabAC Asset` a ON a.name = d.parent
        WHERE d.status = 'Pending'
          AND d.scheduled_date <= %(cutoff)s
          AND a.docstatus != 2
          AND a.lifecycle_status NOT IN ('Decommissioned', 'Out of Service')
        ORDER BY d.parent, d.period_number ASC
    """, {"cutoff": cutoff}, as_dict=True)

    if not rows:
        return {"executed_rows": 0, "updated_assets": 0}

    # Batch-update the rows
    asset_amounts: dict[str, float] = {}
    for r in rows:
        frappe.db.set_value(_DT_SCHED, r["name"], {
            "status": "Executed",
            "executed_on": nowdate(),
        }, update_modified=False)
        asset_amounts[r["asset"]] = asset_amounts.get(r["asset"], 0.0) + flt(r["depreciation_amount"])

    # Update parent assets
    for asset_name, inc in asset_amounts.items():
        acc, gross = frappe.db.get_value(
            _DT_ASSET, asset_name,
            ["accumulated_depreciation", "gross_purchase_amount"],
        )
        new_acc = flt(acc or 0) + inc
        new_book = max(flt(gross or 0) - new_acc, 0.0)
        frappe.db.set_value(_DT_ASSET, asset_name, {
            "accumulated_depreciation": new_acc,
            "current_book_value": new_book,
        }, update_modified=False)

        try:
            from assetcore.utils.lifecycle import create_lifecycle_event
            create_lifecycle_event(
                asset=asset_name, event_type="depreciated",
                actor="Administrator",
                from_status="", to_status="",
                root_doctype=_DT_ASSET, root_record=asset_name,
                notes=f"Depreciated {inc:,.0f} VND, book value = {new_book:,.0f}",
            )
        except Exception:
            pass

    frappe.db.commit()
    return {"executed_rows": len(rows), "updated_assets": len(asset_amounts)}


# ─── Preview (không lưu DB — dùng cho FE preview trước khi generate) ────────

def bulk_regenerate_by_category(category_name: str) -> dict:
    """Regenerate schedule cho tất cả assets thuộc 1 Asset Category.

    Dùng khi admin thay đổi rules khấu hao của Category và muốn áp dụng
    cho toàn bộ assets. CHỈ regenerate với assets chưa có kỳ nào Executed
    để tránh phá vỡ lịch sử khấu hao đã chạy.
    """
    if not frappe.db.exists("AC Asset Category", category_name):
        return {"error": "Category not found"}

    assets = frappe.get_all(
        _DT_ASSET,
        filters={"asset_category": category_name, "docstatus": ("!=", 2)},
        fields=["name"],
        limit_page_length=10000,
    )

    # Inherit rules from Category to each asset first
    cat = frappe.db.get_value(
        "AC Asset Category", category_name,
        ["default_depreciation_method", "total_depreciation_months",
         "depreciation_frequency", "default_residual_value_pct"],
        as_dict=True,
    ) or {}

    regenerated = 0
    skipped = 0
    errors = 0
    for a in assets:
        try:
            # Skip if any period already executed (preserve history)
            executed_count = frappe.db.count(
                _DT_SCHED,
                {"parent": a.name, "status": "Executed"},
            )
            if executed_count > 0:
                skipped += 1
                continue

            # Copy Category rules down to Asset
            asset_doc = frappe.get_doc(_DT_ASSET, a.name)
            asset_doc.depreciation_method = cat.get("default_depreciation_method") or ""
            asset_doc.total_depreciation_months = int(cat.get("total_depreciation_months") or 0)
            asset_doc.depreciation_frequency = cat.get("depreciation_frequency") or "Monthly"
            residual_pct = float(cat.get("default_residual_value_pct") or 0)
            gross = flt(asset_doc.gross_purchase_amount or 0)
            asset_doc.residual_value = gross * residual_pct / 100.0 if residual_pct else 0
            asset_doc.save(ignore_permissions=True)

            # Regenerate schedule
            generate_schedule(a.name, force=True)
            regenerated += 1
        except Exception as e:
            frappe.logger().warning(f"Bulk regen failed for {a.name}: {e}")
            errors += 1

    frappe.db.commit()
    return {
        "category": category_name,
        "total_assets": len(assets),
        "regenerated": regenerated,
        "skipped_has_history": skipped,
        "errors": errors,
    }


def preview_schedule(
    gross: float, residual: float, method: str,
    total_months: int, frequency: str, start_date: str,
) -> list[dict]:
    """Tính toán schedule preview không lưu DB. Dùng cho UI trước khi sinh thật."""
    months_per_period = _FREQ_MONTHS.get(frequency, 1)
    periods = int(total_months or 0) // months_per_period
    if periods <= 0 or gross <= 0:
        return []
    depreciable_base = float(gross) - float(residual or 0)
    if depreciable_base <= 0:
        return []

    if method == "Straight Line":
        amounts = _straight_line_amounts(depreciable_base, periods)
    elif method == "Double Declining":
        amounts = _double_declining_amounts(gross, residual, periods, months_per_period)
    else:
        amounts = _straight_line_amounts(depreciable_base, periods)

    rows = []
    accumulated = 0.0
    for i, amt in enumerate(amounts):
        accumulated += amt
        remaining = max(float(gross) - accumulated, float(residual or 0))
        rows.append({
            "period_number": i + 1,
            "scheduled_date": str(_period_end_date(start_date, i, months_per_period)),
            "depreciation_amount": amt,
            "accumulated_amount": round(accumulated, 2),
            "remaining_value": round(remaining, 2),
        })
    return rows
