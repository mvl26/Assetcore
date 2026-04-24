# IMM-17 — Phân tích dự đoán
## Technical Design

**Phiên bản:** 1.0.0
**Ngày tạo:** 2026-04-24
**Tác giả:** Architecture Team
**Trạng thái:** Draft

---

## 1. Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        IMM-17 Core Data Model                                │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐          ┌─────────────────────────┐
│   IMM Prediction Run    │ 1      * │   IMM Prediction Result │
├─────────────────────────┤──────────├─────────────────────────┤
│ PK  name (auto)         │          │ PK  name (auto)         │
│     run_date            │          │ FK  prediction_run      │
│     run_type            │          │ FK  asset               │
│     (SCHEDULED/MANUAL)  │          │     model_type          │
│     status              │          │     (FAILURE_RISK/PM/   │
│     (RUNNING/DONE/FAIL) │          │     SPARE/BUDGET/REPLACE)│
│     triggered_by        │          │     risk_score (FLOAT)  │
│     model_version       │          │     confidence_score    │
│     total_assets        │          │     risk_tier           │
│     processed_assets    │          │     (LOW/MED/HIGH/CRIT) │
│     skipped_assets      │          │     recommendation_text  │
│     duration_seconds    │          │     input_snapshot JSON  │
│     error_log           │          │     output_detail JSON  │
│     notes               │          │     is_current          │
└─────────────────────────┘          │     created_at          │
                                     └───────────┬─────────────┘
                                                 │ 1
                                                 │ *
                                     ┌───────────▼─────────────┐
                                     │  IMM Predictive Alert   │
                                     ├─────────────────────────┤
                                     │ PK  name (auto)         │
                                     │ FK  prediction_result   │
                                     │ FK  asset               │
                                     │     alert_type (enum)   │
                                     │     severity (enum)     │
                                     │     title               │
                                     │     description         │
                                     │     status              │
                                     │     (OPEN/ACKED/CLOSED/ │
                                     │      ESCALATED)         │
                                     │     created_at          │
                                     │     acknowledged_by     │
                                     │     acknowledged_at     │
                                     │     action_taken        │
                                     │     escalated_to        │
                                     │     escalated_at        │
                                     │     closed_by           │
                                     │     closed_at           │
                                     │     sla_deadline        │
                                     └─────────────────────────┘

┌─────────────────────────┐          ┌─────────────────────────┐
│   IMM Alert Config      │          │  IMM What If Scenario   │
├─────────────────────────┤          ├─────────────────────────┤
│ PK  name (auto)         │          │ PK  name (auto)         │
│     alert_type          │          │     scenario_name       │
│     is_active           │          │     created_by          │
│     high_threshold      │          │     created_at          │
│     critical_threshold  │          │     scenario_type       │
│     min_delta_pct       │          │     (PM_INTERVAL/FLEET/ │
│     sla_ack_hours_high  │          │     PARTS_COST/STAFF)   │
│     sla_ack_hours_crit  │          │     scope_type          │
│     primary_owner_role  │          │     (ALL/DEPARTMENT/    │
│     escalate_to_role    │          │     MODEL/ASSET)        │
│     notify_channels     │          │     scope_value         │
│     (email/in-app/both) │          │     change_parameter    │
│     dedup_window_hours  │          │     change_value        │
│     updated_by          │          │     change_unit (/%/abs)│
│     effective_date      │          │     status              │
└─────────────────────────┘          │     (DRAFT/RUNNING/DONE)│
                                     │     result_summary JSON │
                                     │     expires_at          │
                                     │     notes               │
                                     └─────────────────────────┘
```

---

## 2. DocType Specifications

### 2.1 IMM Prediction Run

```json
{
  "doctype": "DocType",
  "name": "IMM Prediction Run",
  "naming_rule": "Expression",
  "autoname": "format:PR-{YYYY}-{MM}-{#####}",
  "module": "Assetcore",
  "is_submittable": 0,
  "track_changes": 1,
  "fields": [
    {"fieldname": "run_date", "fieldtype": "Datetime", "reqd": 1},
    {"fieldname": "run_type", "fieldtype": "Select",
     "options": "Scheduled\nManual\nTriggered", "reqd": 1},
    {"fieldname": "status", "fieldtype": "Select",
     "options": "Queued\nRunning\nCompleted\nFailed\nPartial"},
    {"fieldname": "triggered_by", "fieldtype": "Link", "options": "User"},
    {"fieldname": "model_version", "fieldtype": "Data"},
    {"fieldname": "models_run", "fieldtype": "Small Text"},
    {"fieldname": "total_assets_in_scope", "fieldtype": "Int"},
    {"fieldname": "processed_assets", "fieldtype": "Int"},
    {"fieldname": "skipped_assets", "fieldtype": "Int"},
    {"fieldname": "alerts_generated", "fieldtype": "Int"},
    {"fieldname": "duration_seconds", "fieldtype": "Float"},
    {"fieldname": "error_log", "fieldtype": "Long Text"},
    {"fieldname": "notes", "fieldtype": "Text Editor"}
  ],
  "permissions": [
    {"role": "HTM Manager", "read": 1, "write": 0},
    {"role": "Innovation Center", "read": 1, "write": 1, "create": 1},
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}
  ]
}
```

### 2.2 IMM Prediction Result

```json
{
  "doctype": "DocType",
  "name": "IMM Prediction Result",
  "naming_rule": "Expression",
  "autoname": "format:PRED-{YYYY}{MM}{DD}-{#####}",
  "module": "Assetcore",
  "track_changes": 1,
  "fields": [
    {"fieldname": "prediction_run", "fieldtype": "Link",
     "options": "IMM Prediction Run", "reqd": 1},
    {"fieldname": "asset", "fieldtype": "Link",
     "options": "Asset", "reqd": 1},
    {"fieldname": "asset_name", "fieldtype": "Data", "fetch_from": "asset.asset_name"},
    {"fieldname": "model_type", "fieldtype": "Select",
     "options": "Failure Risk\nPM Optimization\nSpare Demand\nBudget Forecast\nReplacement Score",
     "reqd": 1},
    {"fieldname": "risk_score", "fieldtype": "Float"},
    {"fieldname": "risk_tier", "fieldtype": "Select",
     "options": "Low\nMedium\nHigh\nCritical"},
    {"fieldname": "confidence_score", "fieldtype": "Float"},
    {"fieldname": "confidence_level", "fieldtype": "Select",
     "options": "Low\nMedium\nHigh"},
    {"fieldname": "recommendation_text", "fieldtype": "Text"},
    {"fieldname": "input_snapshot", "fieldtype": "Long Text"},
    {"fieldname": "output_detail", "fieldtype": "Long Text"},
    {"fieldname": "is_current", "fieldtype": "Check", "default": 1},
    {"fieldname": "model_version", "fieldtype": "Data"},
    {"fieldname": "data_sufficiency_status", "fieldtype": "Select",
     "options": "Sufficient\nInsufficient\nMarginal"}
  ]
}
```

### 2.3 IMM Alert Config

```json
{
  "doctype": "DocType",
  "name": "IMM Alert Config",
  "naming_rule": "Expression",
  "autoname": "format:ALCFG-{alert_type}",
  "module": "Assetcore",
  "is_single": 0,
  "track_changes": 1,
  "fields": [
    {"fieldname": "alert_type", "fieldtype": "Select",
     "options": "Failure Risk High\nFailure Risk Critical\nPM Optimization\nSpare Reorder\nSpare Stockout Risk\nBudget Overrun\nReplacement Candidate\nReplacement Urgent\nModel Low Accuracy\nData Insufficient",
     "reqd": 1},
    {"fieldname": "is_active", "fieldtype": "Check", "default": 1},
    {"fieldname": "high_threshold", "fieldtype": "Float"},
    {"fieldname": "critical_threshold", "fieldtype": "Float"},
    {"fieldname": "min_delta_pct", "fieldtype": "Float"},
    {"fieldname": "sla_ack_hours_high", "fieldtype": "Int", "default": 48},
    {"fieldname": "sla_ack_hours_critical", "fieldtype": "Int", "default": 4},
    {"fieldname": "primary_owner_role", "fieldtype": "Link", "options": "Role"},
    {"fieldname": "escalate_to_role", "fieldtype": "Link", "options": "Role"},
    {"fieldname": "notify_channel", "fieldtype": "Select",
     "options": "In-App\nEmail\nBoth"},
    {"fieldname": "dedup_window_hours", "fieldtype": "Int", "default": 72},
    {"fieldname": "effective_date", "fieldtype": "Date"},
    {"fieldname": "updated_by", "fieldtype": "Link", "options": "User"}
  ]
}
```

---

## 3. Service Layer — services/imm17.py

Toàn bộ business logic đặt trong service layer. Controller chỉ gọi service functions.

```python
# assetcore/services/imm17.py
"""
IMM-17 Predictive Analytics Service Layer.

Provides all business logic for predictive models, alert generation,
what-if analysis, and data sufficiency checks.

Author: AssetCore Team
Version: 1.0.0
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_months, flt, now_datetime, today


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_VERSION = "1.0.0"

RISK_WEIGHTS = {
    "age_factor": 0.20,
    "downtime_rate": 0.30,
    "repair_cost_ratio": 0.25,
    "pm_compliance_inverse": 0.15,
    "mtbf_decline": 0.10,
}

REPLACEMENT_WEIGHTS = {
    "age_score": 0.25,
    "tco_score": 0.30,
    "availability_score": 0.25,
    "failure_freq_score": 0.20,
}


# ---------------------------------------------------------------------------
# 1. Data Sufficiency Check
# ---------------------------------------------------------------------------

def check_data_sufficiency(asset: str, model_type: str = "failure_risk") -> dict[str, Any]:
    """
    Validate whether an asset has sufficient historical data to run predictions.

    Args:
        asset: Asset document name.
        model_type: One of 'failure_risk', 'pm_optimization', 'replacement'.

    Returns:
        dict with keys: is_sufficient (bool), reason (str), data_counts (dict).
    """
    asset_doc = frappe.get_doc("Asset", asset)
    install_date = asset_doc.get("purchase_date") or asset_doc.get("creation")
    months_in_service = _months_between(install_date, today())

    pm_count = frappe.db.count("IMM PM Record", {"asset": asset, "status": "Completed"})
    cm_count = frappe.db.count("IMM CM Record", {"asset": asset, "docstatus": 1})

    data_counts = {
        "months_in_service": months_in_service,
        "pm_count": pm_count,
        "cm_count": cm_count,
    }

    if model_type == "failure_risk":
        min_months = _get_threshold("data_sufficiency_min_months", default=6)
        sufficient = months_in_service >= min_months and (pm_count >= 2 or cm_count >= 2)
        reason = (
            "OK" if sufficient
            else f"Cần ít nhất {min_months} tháng vận hành và 2+ sự kiện PM hoặc CM"
        )

    elif model_type == "pm_optimization":
        sufficient = months_in_service >= 12 and pm_count >= 4
        reason = (
            "OK" if sufficient
            else "Cần ít nhất 12 tháng và 4 chu kỳ PM hoàn chỉnh"
        )

    elif model_type == "replacement":
        sufficient = months_in_service >= 24 or cm_count >= 5
        reason = (
            "OK" if sufficient
            else "Cần 24+ tháng vận hành hoặc 5+ sự kiện CM"
        )

    else:
        sufficient = months_in_service >= 6
        reason = "OK" if sufficient else "Không đủ dữ liệu lịch sử"

    return {
        "is_sufficient": sufficient,
        "reason": reason,
        "data_counts": data_counts,
        "status": "Sufficient" if sufficient else "Insufficient",
    }


# ---------------------------------------------------------------------------
# 2. Failure Risk Prediction
# ---------------------------------------------------------------------------

def run_failure_prediction(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Run failure risk prediction for all eligible assets or filtered subset.

    Args:
        filters: Optional dict with keys: department, asset_category, asset_list.

    Returns:
        List of prediction result dicts per asset.
    """
    assets = _get_eligible_assets(filters)
    results = []

    for asset in assets:
        try:
            result = _predict_failure_risk_for_asset(asset)
            results.append(result)
        except Exception as exc:
            frappe.log_error(
                title=f"IMM-17 Failure Prediction Error: {asset}",
                message=str(exc),
            )
            results.append({"asset": asset, "status": "Error", "error": str(exc)})

    return results


def _predict_failure_risk_for_asset(asset: str) -> dict[str, Any]:
    """
    Calculate failure risk score for a single asset using weighted formula.

    Formula:
        risk_score = (age_factor × 0.20) + (downtime_rate × 0.30) +
                     (repair_cost_ratio × 0.25) + (pm_compliance_inv × 0.15) +
                     (mtbf_decline × 0.10)
    All sub-scores normalized to 0–100 before weighting.

    Args:
        asset: Asset document name.

    Returns:
        dict with risk_score, confidence_score, risk_tier, factors, recommendation.
    """
    sufficiency = check_data_sufficiency(asset, "failure_risk")
    if not sufficiency["is_sufficient"]:
        return _insufficient_result(asset, "Failure Risk", sufficiency["reason"])

    indicators = _gather_failure_indicators(asset)
    age_score = _normalize_age(indicators["age_months"])
    downtime_score = _normalize_downtime_rate(indicators["downtime_rate_pct"])
    cost_ratio_score = _normalize_cost_ratio(indicators["repair_cost_ratio"])
    pm_inv_score = 100 - indicators["pm_compliance_pct"]
    mtbf_decline_score = _normalize_mtbf_decline(indicators["mtbf_decline_pct"])

    raw_score = (
        age_score * RISK_WEIGHTS["age_factor"]
        + downtime_score * RISK_WEIGHTS["downtime_rate"]
        + cost_ratio_score * RISK_WEIGHTS["repair_cost_ratio"]
        + pm_inv_score * RISK_WEIGHTS["pm_compliance_inverse"]
        + mtbf_decline_score * RISK_WEIGHTS["mtbf_decline"]
    )

    risk_score = round(min(100, max(0, raw_score)), 1)
    confidence = _calculate_confidence(indicators)
    risk_tier = _classify_risk_tier(risk_score)

    factors = [
        {"name": "Tuổi thiết bị", "score": age_score, "weight": 0.20, "value": f"{indicators['age_months']} tháng"},
        {"name": "Tỷ lệ downtime", "score": downtime_score, "weight": 0.30, "value": f"{indicators['downtime_rate_pct']:.1f}%"},
        {"name": "Chi phí sửa chữa", "score": cost_ratio_score, "weight": 0.25, "value": f"{indicators['repair_cost_ratio']:.1f}% giá trị"},
        {"name": "Tuân thủ PM", "score": pm_inv_score, "weight": 0.15, "value": f"{indicators['pm_compliance_pct']:.0f}% (đảo ngược)"},
        {"name": "Suy giảm MTBF", "score": mtbf_decline_score, "weight": 0.10, "value": f"{indicators['mtbf_decline_pct']:.1f}% suy giảm"},
    ]
    factors_sorted = sorted(factors, key=lambda x: x["score"] * x["weight"], reverse=True)

    recommendation = _build_failure_recommendation(risk_tier, factors_sorted[:3])

    return {
        "asset": asset,
        "model_type": "Failure Risk",
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "confidence_score": confidence,
        "confidence_level": _confidence_level(confidence),
        "factors": factors_sorted,
        "recommendation_text": recommendation,
        "input_snapshot": json.dumps(indicators),
        "status": "Success",
    }


def _gather_failure_indicators(asset: str) -> dict[str, float]:
    """
    Aggregate all indicators needed for failure risk calculation from source modules.

    Args:
        asset: Asset document name.

    Returns:
        dict of computed indicator values.
    """
    asset_doc = frappe.get_doc("Asset", asset)
    install_date = asset_doc.get("purchase_date") or asset_doc.get("creation")
    age_months = _months_between(install_date, today())
    asset_value = flt(asset_doc.get("gross_purchase_amount", 0))

    # Downtime from CM records (last 12 months)
    twelve_months_ago = add_months(today(), -12)
    cm_records = frappe.get_all(
        "IMM CM Record",
        filters={"asset": asset, "docstatus": 1, "failure_date": [">=", twelve_months_ago]},
        fields=["downtime_hours", "repair_cost", "failure_date", "resolution_date"],
    )

    total_downtime_hours = sum(flt(r.get("downtime_hours", 0)) for r in cm_records)
    total_repair_cost = sum(flt(r.get("repair_cost", 0)) for r in cm_records)
    downtime_rate_pct = (total_downtime_hours / (8760 * 1.0)) * 100  # % of 8760h/year
    repair_cost_ratio = (total_repair_cost / asset_value * 100) if asset_value > 0 else 0

    # PM compliance (last 12 months)
    pm_scheduled = frappe.db.count(
        "IMM PM Record", {"asset": asset, "scheduled_date": [">=", twelve_months_ago]}
    )
    pm_completed = frappe.db.count(
        "IMM PM Record",
        {"asset": asset, "status": "Completed", "scheduled_date": [">=", twelve_months_ago]},
    )
    pm_compliance_pct = (pm_completed / pm_scheduled * 100) if pm_scheduled > 0 else 50.0

    # MTBF decline: compare last 6 months vs. prior 6 months
    six_months_ago = add_months(today(), -6)
    mtbf_recent = _calc_mtbf(asset, six_months_ago, today())
    mtbf_prior = _calc_mtbf(asset, add_months(today(), -12), six_months_ago)
    mtbf_decline_pct = (
        ((mtbf_prior - mtbf_recent) / mtbf_prior * 100) if mtbf_prior > 0 else 0
    )

    return {
        "age_months": age_months,
        "asset_value": asset_value,
        "total_downtime_hours_12m": total_downtime_hours,
        "downtime_rate_pct": downtime_rate_pct,
        "total_repair_cost_12m": total_repair_cost,
        "repair_cost_ratio": repair_cost_ratio,
        "pm_scheduled_12m": pm_scheduled,
        "pm_completed_12m": pm_completed,
        "pm_compliance_pct": pm_compliance_pct,
        "mtbf_recent_days": mtbf_recent,
        "mtbf_prior_days": mtbf_prior,
        "mtbf_decline_pct": max(0, mtbf_decline_pct),
        "cm_count_12m": len(cm_records),
    }


# ---------------------------------------------------------------------------
# 3. PM Schedule Optimization
# ---------------------------------------------------------------------------

def optimize_pm_schedule(asset: str) -> dict[str, Any]:
    """
    Calculate recommended PM interval based on failure patterns.

    Logic:
        - If failures cluster within 30 days BEFORE PM date → shorten interval
        - If PM consistently finds no issues → lengthen interval
        - Constrained by manufacturer limits and BR-17-08

    Args:
        asset: Asset document name.

    Returns:
        dict with current_interval_days, recommended_interval_days,
        delta_pct, rationale, confidence_score.
    """
    sufficiency = check_data_sufficiency(asset, "pm_optimization")
    if not sufficiency["is_sufficient"]:
        return _insufficient_result(asset, "PM Optimization", sufficiency["reason"])

    maintenance_plan = frappe.get_all(
        "IMM Maintenance Plan",
        filters={"asset": asset, "status": "Active"},
        fields=["pm_interval_days", "name"],
        limit=1,
    )
    if not maintenance_plan:
        return {"asset": asset, "status": "No Active Maintenance Plan"}

    current_interval = flt(maintenance_plan[0]["pm_interval_days"])

    # Analyse failures relative to PM events
    pm_records = frappe.get_all(
        "IMM PM Record",
        filters={"asset": asset, "status": "Completed"},
        fields=["scheduled_date", "actual_date", "issues_found", "name"],
        order_by="actual_date desc",
        limit=12,
    )

    cm_records = frappe.get_all(
        "IMM CM Record",
        filters={"asset": asset, "docstatus": 1},
        fields=["failure_date"],
        order_by="failure_date desc",
        limit=20,
    )

    # Count PM events with significant issues found
    pm_with_issues = sum(1 for r in pm_records if r.get("issues_found"))
    pm_issue_rate = (pm_with_issues / len(pm_records)) if pm_records else 0

    # Count failures that occurred within 30d before a PM
    pre_pm_failures = _count_pre_pm_failures(cm_records, pm_records, window_days=30)
    pre_pm_failure_rate = (pre_pm_failures / len(cm_records)) if cm_records else 0

    # Decision logic
    if pre_pm_failure_rate > 0.4:
        # Many failures just before PM → shorten interval
        delta_pct = -20
        rationale = f"{pre_pm_failure_rate:.0%} failures xảy ra trong 30 ngày trước PM → nên rút ngắn chu kỳ"
    elif pm_issue_rate < 0.2:
        # PM rarely finds issues → lengthen interval
        delta_pct = +20
        rationale = f"Chỉ {pm_issue_rate:.0%} PM phát hiện vấn đề → có thể kéo dài chu kỳ"
    else:
        delta_pct = 0
        rationale = "Chu kỳ PM hiện tại phù hợp với pattern thực tế"

    min_delta = _get_threshold("pm_optimization_min_delta", default=15)
    if abs(delta_pct) < min_delta:
        return {
            "asset": asset,
            "status": "No Recommendation",
            "reason": f"Delta {abs(delta_pct):.0f}% < ngưỡng tối thiểu {min_delta}%",
            "current_interval_days": current_interval,
        }

    recommended_interval = current_interval * (1 + delta_pct / 100)
    recommended_interval = _apply_interval_constraints(
        recommended_interval, asset, current_interval
    )
    confidence = 0.60 + (len(pm_records) / 24) * 0.30  # More data → higher confidence

    return {
        "asset": asset,
        "model_type": "PM Optimization",
        "current_interval_days": current_interval,
        "recommended_interval_days": round(recommended_interval),
        "delta_pct": delta_pct,
        "rationale": rationale,
        "confidence_score": round(min(0.95, confidence), 2),
        "confidence_level": _confidence_level(confidence),
        "supporting_data": {
            "pm_count_analysed": len(pm_records),
            "cm_count_analysed": len(cm_records),
            "pm_issue_rate": round(pm_issue_rate, 2),
            "pre_pm_failure_rate": round(pre_pm_failure_rate, 2),
        },
        "status": "Success",
    }


# ---------------------------------------------------------------------------
# 4. Spare Parts Demand Forecast
# ---------------------------------------------------------------------------

def forecast_spare_demand(part: str, months: int = 3) -> dict[str, Any]:
    """
    Forecast spare part demand for next N months using simple moving average.

    Args:
        part: Item code (spare part).
        months: Number of months to forecast (default 3).

    Returns:
        dict with monthly_forecast list, reorder_point, recommended_order_qty.
    """
    # Get 12-month consumption history
    history = _get_consumption_history(part, lookback_months=12)

    if len(history) < 5:
        return {
            "part": part,
            "status": "Insufficient History",
            "message": "Cần ít nhất 5 giao dịch lịch sử để dự báo",
        }

    # Remove anomalies using z-score
    clean_history = _remove_anomalies(history)

    # Calculate 3-month moving average
    window = min(3, len(clean_history))
    recent = clean_history[-window:]
    avg_monthly = sum(recent) / window

    # Simple seasonality: compare same month prior year if available
    monthly_forecast = []
    for i in range(months):
        seasonal_factor = _get_seasonal_factor(part, i + 1)
        forecasted = round(avg_monthly * seasonal_factor, 1)
        monthly_forecast.append({
            "month": i + 1,
            "forecasted_quantity": forecasted,
            "seasonal_factor": seasonal_factor,
        })

    # Reorder point = lead_time_demand + safety_stock
    lead_time_days = _get_part_lead_time(part)
    buffer_days = _get_threshold("spare_reorder_buffer_days", default=14)
    daily_avg = avg_monthly / 30
    reorder_point = math.ceil(daily_avg * (lead_time_days + buffer_days))
    recommended_order_qty = math.ceil(avg_monthly * months)

    current_stock = _get_current_stock(part)
    confidence = 0.50 + min(0.40, len(clean_history) / 30)

    return {
        "part": part,
        "model_type": "Spare Demand",
        "monthly_forecast": monthly_forecast,
        "avg_monthly_demand": round(avg_monthly, 1),
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "recommended_order_qty": recommended_order_qty,
        "lead_time_days": lead_time_days,
        "confidence_score": round(confidence, 2),
        "confidence_level": _confidence_level(confidence),
        "anomalies_removed": len(history) - len(clean_history),
        "history_months_used": len(history),
        "status": "Success",
    }


# ---------------------------------------------------------------------------
# 5. Maintenance Budget Forecast
# ---------------------------------------------------------------------------

def forecast_maintenance_budget(months: int = 12) -> dict[str, Any]:
    """
    Forecast total maintenance budget for next N months.

    Algorithm:
        1. Calculate average monthly cost per device model (last 24 months)
        2. Multiply by current fleet composition
        3. Apply trend factor (cost trend slope)
        4. Apply inflation adjustment
        5. Sum across all categories

    Args:
        months: Forecast horizon in months (default 12).

    Returns:
        dict with monthly_forecast, annual_total, confidence_interval, breakdown.
    """
    cost_history = _get_fleet_cost_history(lookback_months=24)
    fleet_composition = _get_current_fleet_composition()

    if len(cost_history) < 12:
        return {
            "status": "Insufficient History",
            "message": "Cần ít nhất 12 tháng dữ liệu chi phí để dự báo ngân sách",
        }

    monthly_forecast = []
    annual_total = 0

    for i in range(months):
        # Trend-adjusted cost estimate
        pm_cost = _project_cost_category("PM", cost_history, i, fleet_composition)
        cm_cost = _project_cost_category("CM", cost_history, i, fleet_composition)
        cal_cost = _project_cost_category("Calibration", cost_history, i, fleet_composition)
        parts_cost = _project_cost_category("Parts", cost_history, i, fleet_composition)

        month_total = pm_cost + cm_cost + cal_cost + parts_cost
        annual_total += month_total

        monthly_forecast.append({
            "month": i + 1,
            "pm_cost": round(pm_cost),
            "cm_cost": round(cm_cost),
            "calibration_cost": round(cal_cost),
            "parts_cost": round(parts_cost),
            "total": round(month_total),
            "confidence_lower": round(month_total * 0.85),
            "confidence_upper": round(month_total * 1.15),
        })

    return {
        "model_type": "Budget Forecast",
        "monthly_forecast": monthly_forecast,
        "annual_total": round(annual_total),
        "confidence_interval_pct": 15,
        "fleet_size": fleet_composition.get("total_assets", 0),
        "data_months_used": len(cost_history),
        "confidence_score": 0.72,
        "confidence_level": "Medium",
        "status": "Success",
    }


# ---------------------------------------------------------------------------
# 6. Replacement Candidate Scoring
# ---------------------------------------------------------------------------

def score_replacement_candidates(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Batch-score all assets for replacement candidacy.

    Scoring formula:
        score = age_score × 0.25 + tco_score × 0.30 +
                availability_score × 0.25 + failure_freq_score × 0.20
    All sub-scores 0–100.

    Args:
        filters: Optional asset filters.

    Returns:
        List of scored assets, sorted by score descending.
    """
    assets = _get_eligible_assets(filters)
    results = []

    for asset in assets:
        try:
            score_result = _score_single_replacement_candidate(asset)
            if score_result.get("score") is not None:
                results.append(score_result)
        except Exception as exc:
            frappe.log_error(
                title=f"IMM-17 Replacement Score Error: {asset}",
                message=str(exc),
            )

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results


def _score_single_replacement_candidate(asset: str) -> dict[str, Any]:
    """
    Score a single asset for replacement candidacy.

    Args:
        asset: Asset document name.

    Returns:
        dict with score, recommended_action, drivers.
    """
    sufficiency = check_data_sufficiency(asset, "replacement")
    if not sufficiency["is_sufficient"]:
        return {"asset": asset, "status": "Insufficient Data"}

    indicators = _gather_replacement_indicators(asset)

    age_score = _normalize_age_replacement(indicators["age_months"])
    tco_score = _normalize_tco(indicators["total_cost_of_ownership"], indicators["asset_value"])
    availability_score = _normalize_availability_inverse(indicators["availability_pct"])
    failure_freq_score = _normalize_failure_frequency(indicators["cm_count_24m"])

    score = (
        age_score * REPLACEMENT_WEIGHTS["age_score"]
        + tco_score * REPLACEMENT_WEIGHTS["tco_score"]
        + availability_score * REPLACEMENT_WEIGHTS["availability_score"]
        + failure_freq_score * REPLACEMENT_WEIGHTS["failure_freq_score"]
    )
    score = round(min(100, max(0, score)), 1)

    if score >= 90:
        recommended_action = "Urgent Review"
    elif score >= 75:
        recommended_action = "Plan Replacement"
    elif score >= 60:
        recommended_action = "Monitor Closely"
    else:
        recommended_action = "Continue Operation"

    return {
        "asset": asset,
        "model_type": "Replacement Score",
        "score": score,
        "recommended_action": recommended_action,
        "age_months": indicators["age_months"],
        "total_cost_of_ownership": indicators["total_cost_of_ownership"],
        "availability_pct": indicators["availability_pct"],
        "cm_count_24m": indicators["cm_count_24m"],
        "sub_scores": {
            "age_score": round(age_score, 1),
            "tco_score": round(tco_score, 1),
            "availability_score": round(availability_score, 1),
            "failure_freq_score": round(failure_freq_score, 1),
        },
        "confidence_score": 0.75,
        "status": "Success",
    }


# ---------------------------------------------------------------------------
# 7. What-If Analysis
# ---------------------------------------------------------------------------

def run_what_if_analysis(scenario: dict[str, Any]) -> dict[str, Any]:
    """
    Run a what-if scenario simulation.

    Supported scenario_type:
        - PM_INTERVAL: change PM interval by X%
        - FLEET_REDUCTION: retire N assets of a model
        - PARTS_COST: parts cost increase by X%
        - STAFF_CAPACITY: change technician hours by X%

    Args:
        scenario: dict with keys: scenario_type, scope_type, scope_value,
                  change_value, change_unit.

    Returns:
        dict with baseline_metrics, projected_metrics, delta_summary.
    """
    scenario_type = scenario.get("scenario_type")
    baseline = _get_baseline_metrics(scenario)

    if scenario_type == "PM_INTERVAL":
        projected = _simulate_pm_interval_change(baseline, scenario)
    elif scenario_type == "FLEET_REDUCTION":
        projected = _simulate_fleet_reduction(baseline, scenario)
    elif scenario_type == "PARTS_COST":
        projected = _simulate_parts_cost_change(baseline, scenario)
    elif scenario_type == "STAFF_CAPACITY":
        projected = _simulate_staff_capacity_change(baseline, scenario)
    else:
        frappe.throw(_(f"Loại kịch bản không được hỗ trợ: {scenario_type}"))

    delta = {
        "annual_cost_delta": projected["annual_cost"] - baseline["annual_cost"],
        "failure_rate_delta": projected["failure_rate"] - baseline["failure_rate"],
        "downtime_delta_hours": projected["annual_downtime_hours"] - baseline["annual_downtime_hours"],
        "spare_demand_delta": projected["annual_spare_demand"] - baseline["annual_spare_demand"],
    }

    return {
        "scenario_type": scenario_type,
        "baseline": baseline,
        "projected": projected,
        "delta": delta,
        "assumptions": _get_simulation_assumptions(scenario),
        "confidence_note": "Kết quả mang tính ước tính. Không dùng như cam kết ngân sách.",
        "expires_at": add_months(today(), 3),
        "status": "Success",
    }


# ---------------------------------------------------------------------------
# 8. Alert Generation
# ---------------------------------------------------------------------------

def generate_alert(
    asset: str,
    alert_type: str,
    severity: str,
    prediction_result_name: str,
    description: str = "",
) -> str:
    """
    Create a predictive alert record if not already active (dedup check).

    Args:
        asset: Asset document name.
        alert_type: Alert type string (matches IMM Alert Config).
        severity: One of 'Info', 'Medium', 'High', 'Critical'.
        prediction_result_name: Link to IMM Prediction Result.
        description: Human-readable description.

    Returns:
        Name of created or existing IMM Predictive Alert.
    """
    config = _get_alert_config(alert_type)
    dedup_hours = config.get("dedup_window_hours", 72)
    dedup_cutoff = datetime.now() - timedelta(hours=dedup_hours)

    # Deduplication check
    existing = frappe.get_all(
        "IMM Predictive Alert",
        filters={
            "asset": asset,
            "alert_type": alert_type,
            "status": ["in", ["Open", "Escalated"]],
            "created_at": [">=", dedup_cutoff],
        },
        limit=1,
    )
    if existing:
        return existing[0]["name"]

    sla_hours = (
        config.get("sla_ack_hours_critical", 4)
        if severity == "Critical"
        else config.get("sla_ack_hours_high", 48)
    )
    sla_deadline = datetime.now() + timedelta(hours=sla_hours)

    alert = frappe.get_doc({
        "doctype": "IMM Predictive Alert",
        "asset": asset,
        "alert_type": alert_type,
        "severity": severity,
        "title": f"[{severity.upper()}] {alert_type} — {asset}",
        "description": description,
        "status": "Open",
        "prediction_result": prediction_result_name,
        "sla_deadline": sla_deadline,
        "created_at": now_datetime(),
    })
    alert.insert(ignore_permissions=True)

    _send_alert_notification(alert)
    return alert.name


# ---------------------------------------------------------------------------
# 9. Scheduler Jobs
# ---------------------------------------------------------------------------

def run_all_predictions() -> dict[str, Any]:
    """
    Weekly scheduled job: run all prediction models for the full fleet.

    Triggered by: Frappe scheduler, every Monday 06:00.

    Returns:
        Summary dict of the prediction run.
    """
    run = frappe.get_doc({
        "doctype": "IMM Prediction Run",
        "run_date": now_datetime(),
        "run_type": "Scheduled",
        "status": "Running",
        "model_version": MODEL_VERSION,
        "triggered_by": "System",
    })
    run.insert(ignore_permissions=True)
    frappe.db.commit()

    summary = {"failure_risk": 0, "replacement": 0, "pm_optimization": 0, "errors": 0}

    try:
        assets = _get_eligible_assets()
        run.total_assets_in_scope = len(assets)
        processed = 0
        alerts_generated = 0

        for asset in assets:
            try:
                fr_result = _predict_failure_risk_for_asset(asset)
                _save_prediction_result(run.name, fr_result)
                if fr_result.get("risk_tier") in ("High", "Critical"):
                    alert_name = generate_alert(
                        asset=asset,
                        alert_type=f"Failure Risk {fr_result['risk_tier']}",
                        severity=fr_result["risk_tier"],
                        prediction_result_name=fr_result.get("result_name", ""),
                        description=fr_result.get("recommendation_text", ""),
                    )
                    if alert_name:
                        alerts_generated += 1
                summary["failure_risk"] += 1

                rep_result = _score_single_replacement_candidate(asset)
                _save_prediction_result(run.name, rep_result)
                if rep_result.get("score", 0) >= 75:
                    generate_alert(
                        asset=asset,
                        alert_type="Replacement Candidate",
                        severity="High" if rep_result["score"] < 90 else "Critical",
                        prediction_result_name=rep_result.get("result_name", ""),
                        description=f"Replacement score: {rep_result.get('score')}",
                    )
                    alerts_generated += 1
                summary["replacement"] += 1
                processed += 1

            except Exception as exc:
                summary["errors"] += 1
                frappe.log_error(
                    title=f"IMM-17 Weekly Run Error: {asset}", message=str(exc)
                )

        run.processed_assets = processed
        run.alerts_generated = alerts_generated
        run.status = "Completed"

    except Exception as exc:
        run.status = "Failed"
        run.error_log = str(exc)
        frappe.log_error(title="IMM-17 Weekly Run Failed", message=str(exc))

    run.save(ignore_permissions=True)
    frappe.db.commit()
    return {"run": run.name, "summary": summary}


def check_prediction_alerts() -> None:
    """
    Daily scheduled job: escalate unacknowledged alerts past SLA deadline.

    Triggered by: Frappe scheduler, daily 06:30.
    """
    overdue_alerts = frappe.get_all(
        "IMM Predictive Alert",
        filters={
            "status": "Open",
            "sla_deadline": ["<", now_datetime()],
        },
        fields=["name", "asset", "severity", "escalated_to", "alert_type"],
    )

    for alert in overdue_alerts:
        config = _get_alert_config(alert["alert_type"])
        escalate_role = config.get("escalate_to_role")

        frappe.db.set_value(
            "IMM Predictive Alert",
            alert["name"],
            {"status": "Escalated", "escalated_at": now_datetime()},
        )

        _send_escalation_notification(alert, escalate_role)

    frappe.db.commit()


# ---------------------------------------------------------------------------
# Private helpers (abbreviated — full implementation in codebase)
# ---------------------------------------------------------------------------

def _get_eligible_assets(filters: dict | None = None) -> list[str]:
    """Return list of active asset names matching filters."""
    conditions = {"status": "Active", "docstatus": 1}
    if filters:
        if filters.get("department"):
            conditions["department"] = filters["department"]
        if filters.get("asset_category"):
            conditions["asset_category"] = filters["asset_category"]
    return [r["name"] for r in frappe.get_all("Asset", filters=conditions, fields=["name"])]


def _months_between(start: Any, end: Any) -> int:
    """Calculate number of complete months between two dates."""
    from frappe.utils import getdate
    s, e = getdate(start), getdate(end)
    return (e.year - s.year) * 12 + (e.month - s.month)


def _normalize_age(age_months: int) -> float:
    """Normalize asset age to 0–100 score. 120 months (10y) = 100."""
    return min(100, age_months / 120 * 100)


def _normalize_downtime_rate(rate_pct: float) -> float:
    """Normalize downtime rate to 0–100. 10%+ = 100."""
    return min(100, rate_pct / 10 * 100)


def _normalize_cost_ratio(ratio_pct: float) -> float:
    """Normalize repair cost ratio to 0–100. 50%+ of asset value = 100."""
    return min(100, ratio_pct / 50 * 100)


def _normalize_mtbf_decline(decline_pct: float) -> float:
    """Normalize MTBF decline to 0–100. 50%+ decline = 100."""
    return min(100, max(0, decline_pct / 50 * 100))


def _classify_risk_tier(score: float) -> str:
    """Classify risk score into tier."""
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def _confidence_level(score: float) -> str:
    """Convert numeric confidence to level string."""
    if score >= 0.80:
        return "High"
    if score >= 0.60:
        return "Medium"
    return "Low"


def _calculate_confidence(indicators: dict) -> float:
    """Calculate confidence score based on data completeness."""
    score = 0.40
    if indicators.get("pm_scheduled_12m", 0) >= 4:
        score += 0.20
    if indicators.get("cm_count_12m", 0) >= 2:
        score += 0.15
    if indicators.get("age_months", 0) >= 24:
        score += 0.15
    if indicators.get("asset_value", 0) > 0:
        score += 0.10
    return round(min(0.95, score), 2)


def _insufficient_result(asset: str, model_type: str, reason: str) -> dict:
    """Standard result dict for assets with insufficient data."""
    return {
        "asset": asset,
        "model_type": model_type,
        "status": "Insufficient Data",
        "data_sufficiency_status": "Insufficient",
        "risk_score": None,
        "confidence_score": 0.0,
        "confidence_level": "Low",
        "recommendation_text": f"Chưa đủ dữ liệu: {reason}",
    }


def _get_threshold(key: str, default: float) -> float:
    """Fetch threshold value from IMM Alert Config or return default."""
    value = frappe.db.get_single_value("IMM Analytics Settings", key)
    return flt(value) if value else default


def _get_alert_config(alert_type: str) -> dict:
    """Fetch alert configuration for given alert type."""
    records = frappe.get_all(
        "IMM Alert Config",
        filters={"alert_type": alert_type, "is_active": 1},
        fields=["*"],
        limit=1,
    )
    return records[0] if records else {}


def _calc_mtbf(asset: str, start: str, end: str) -> float:
    """Calculate Mean Time Between Failures in days for a period."""
    cm_records = frappe.get_all(
        "IMM CM Record",
        filters={"asset": asset, "docstatus": 1, "failure_date": ["between", [start, end]]},
        fields=["failure_date"],
    )
    count = len(cm_records)
    if count < 2:
        return 9999  # Very long MTBF if few failures
    from frappe.utils import date_diff
    total_days = date_diff(end, start)
    return total_days / count


def _send_alert_notification(alert: Any) -> None:
    """Send in-app and/or email notification for new alert."""
    # Implementation: use frappe.sendmail / frappe.publish_realtime
    pass


def _send_escalation_notification(alert: dict, role: str) -> None:
    """Send escalation notification to role members."""
    pass


def _save_prediction_result(run_name: str, result: dict) -> None:
    """Persist a prediction result dict to IMM Prediction Result doctype."""
    if result.get("status") not in ("Success", None):
        return
    doc = frappe.get_doc({
        "doctype": "IMM Prediction Result",
        "prediction_run": run_name,
        "asset": result.get("asset"),
        "model_type": result.get("model_type"),
        "risk_score": result.get("risk_score") or result.get("score"),
        "risk_tier": result.get("risk_tier") or result.get("recommended_action"),
        "confidence_score": result.get("confidence_score", 0),
        "confidence_level": result.get("confidence_level", "Low"),
        "recommendation_text": result.get("recommendation_text", ""),
        "input_snapshot": result.get("input_snapshot", "{}"),
        "output_detail": json.dumps(result),
        "is_current": 1,
        "model_version": MODEL_VERSION,
        "data_sufficiency_status": result.get("data_sufficiency_status", "Sufficient"),
    })
    doc.insert(ignore_permissions=True)
    result["result_name"] = doc.name


def _count_pre_pm_failures(cm_records: list, pm_records: list, window_days: int) -> int:
    """Count CM events occurring within window_days before a PM date."""
    count = 0
    from frappe.utils import getdate, date_diff
    for cm in cm_records:
        failure_date = getdate(cm.get("failure_date"))
        for pm in pm_records:
            pm_date = getdate(pm.get("actual_date") or pm.get("scheduled_date"))
            days_before = date_diff(pm_date, failure_date)
            if 0 <= days_before <= window_days:
                count += 1
                break
    return count


def _apply_interval_constraints(
    interval: float, asset: str, current: float
) -> float:
    """Apply BR-17-08 constraints to recommended PM interval."""
    max_ext = _get_threshold("pm_interval_max_extension", default=50) / 100
    interval = max(7, min(365, interval))
    interval = min(interval, current * (1 + max_ext))
    return interval


def _get_consumption_history(part: str, lookback_months: int) -> list[float]:
    """Return list of monthly consumption quantities (oldest → newest)."""
    # Query IMM Spare Issue records grouped by month
    return []  # Placeholder — full implementation in codebase


def _remove_anomalies(history: list[float]) -> list[float]:
    """Remove statistical anomalies (|z-score| > 3) from consumption history."""
    if len(history) < 3:
        return history
    mean = sum(history) / len(history)
    variance = sum((x - mean) ** 2 for x in history) / len(history)
    std = math.sqrt(variance) if variance > 0 else 1
    return [x for x in history if abs((x - mean) / std) <= 3]


def _get_seasonal_factor(part: str, month_offset: int) -> float:
    """Return seasonal adjustment factor for given month offset."""
    return 1.0  # No seasonality by default; override with actual analysis


def _get_part_lead_time(part: str) -> int:
    """Return lead time in days for a part from supplier."""
    value = frappe.db.get_value("Item", part, "lead_time_days")
    return int(value) if value else 14


def _get_current_stock(part: str) -> float:
    """Return current warehouse stock level for a part."""
    return flt(frappe.db.get_value("Bin", {"item_code": part}, "actual_qty"))


def _get_fleet_cost_history(lookback_months: int) -> list[dict]:
    """Return monthly cost aggregates from all maintenance modules."""
    return []  # Placeholder


def _get_current_fleet_composition(self=None) -> dict:
    """Return fleet size and composition by device model."""
    total = frappe.db.count("Asset", {"status": "Active", "docstatus": 1})
    return {"total_assets": total}


def _project_cost_category(category: str, history: list, month_offset: int, fleet: dict) -> float:
    """Project cost for one category for a future month."""
    return 0.0  # Placeholder — full trend analysis implementation in codebase


def _get_baseline_metrics(scenario: dict) -> dict:
    """Gather current baseline metrics for what-if comparison."""
    return {
        "annual_cost": 0,
        "failure_rate": 0,
        "annual_downtime_hours": 0,
        "annual_spare_demand": 0,
    }


def _simulate_pm_interval_change(baseline: dict, scenario: dict) -> dict:
    """Simulate impact of PM interval change."""
    change_pct = flt(scenario.get("change_value", 0)) / 100
    return {
        "annual_cost": baseline["annual_cost"] * (1 + change_pct * 0.3),
        "failure_rate": baseline["failure_rate"] * (1 - change_pct * 0.5),
        "annual_downtime_hours": baseline["annual_downtime_hours"] * (1 - change_pct * 0.4),
        "annual_spare_demand": baseline["annual_spare_demand"] * (1 + change_pct * 0.2),
    }


def _simulate_fleet_reduction(baseline: dict, scenario: dict) -> dict:
    return baseline  # Placeholder


def _simulate_parts_cost_change(baseline: dict, scenario: dict) -> dict:
    return baseline  # Placeholder


def _simulate_staff_capacity_change(baseline: dict, scenario: dict) -> dict:
    return baseline  # Placeholder


def _get_simulation_assumptions(scenario: dict) -> list[str]:
    return [
        "Tỷ lệ thất bại giữ nguyên trừ thay đổi trực tiếp từ PM interval",
        "Chi phí nhân công giữ nguyên",
        "Không có thay đổi về fleet composition",
        "Kết quả mang tính xấp xỉ, sai số ±15%",
    ]


def _gather_replacement_indicators(asset: str) -> dict:
    """Gather TCO and performance indicators for replacement scoring."""
    asset_doc = frappe.get_doc("Asset", asset)
    install_date = asset_doc.get("purchase_date") or asset_doc.get("creation")
    age_months = _months_between(install_date, today())
    asset_value = flt(asset_doc.get("gross_purchase_amount", 0))

    twenty_four_ago = add_months(today(), -24)
    cm_records = frappe.get_all(
        "IMM CM Record",
        filters={"asset": asset, "docstatus": 1, "failure_date": [">=", twenty_four_ago]},
        fields=["repair_cost", "downtime_hours"],
    )
    cm_cost_24m = sum(flt(r.get("repair_cost", 0)) for r in cm_records)
    downtime_hours_24m = sum(flt(r.get("downtime_hours", 0)) for r in cm_records)
    pm_cost_24m = frappe.db.sql(
        "SELECT COALESCE(SUM(total_cost), 0) FROM `tabIMM PM Record` WHERE asset=%s AND status='Completed' AND scheduled_date>=%s",
        (asset, twenty_four_ago),
    )[0][0]

    total_cost_of_ownership = flt(cm_cost_24m) + flt(pm_cost_24m)
    availability_pct = max(0, 100 - (downtime_hours_24m / (8760 * 2) * 100))

    return {
        "age_months": age_months,
        "asset_value": asset_value,
        "total_cost_of_ownership": total_cost_of_ownership,
        "cm_count_24m": len(cm_records),
        "availability_pct": availability_pct,
    }


def _normalize_age_replacement(age_months: int) -> float:
    return min(100, age_months / 180 * 100)  # 15 years = 100


def _normalize_tco(tco: float, asset_value: float) -> float:
    if asset_value <= 0:
        return 50
    ratio = tco / asset_value
    return min(100, ratio / 1.5 * 100)  # TCO = 150% of asset value = 100


def _normalize_availability_inverse(avail_pct: float) -> float:
    return max(0, 100 - avail_pct)  # Low availability → high score


def _normalize_failure_frequency(cm_count: int) -> float:
    return min(100, cm_count / 10 * 100)  # 10+ failures in 24m = 100


def _build_failure_recommendation(risk_tier: str, top_factors: list) -> str:
    factor_names = ", ".join(f["name"] for f in top_factors[:2])
    if risk_tier == "Critical":
        return f"KHẨN CẤP: Thiết bị có nguy cơ hỏng rất cao. Nguyên nhân chính: {factor_names}. Đề xuất kiểm tra ngay và lên lịch CM."
    if risk_tier == "High":
        return f"CẢNH BÁO: Nguy cơ hỏng hóc cao. Nguyên nhân: {factor_names}. Đề xuất PM sớm hơn lịch hoặc kiểm tra đặc biệt."
    if risk_tier == "Medium":
        return f"Theo dõi: Có dấu hiệu tiềm ẩn ({factor_names}). Đảm bảo PM đúng lịch."
    return "Thiết bị hoạt động ổn định. Tiếp tục theo dõi định kỳ."
```

---

## 4. Scheduler Configuration

Trong `hooks.py` của assetcore:

```python
# assetcore/hooks.py

scheduler_events = {
    "weekly": [
        "assetcore.services.imm17.run_all_predictions",  # Monday 06:00
    ],
    "daily": [
        "assetcore.services.imm17.check_prediction_alerts",  # 06:30
    ],
    "monthly": [
        "assetcore.services.imm17.send_model_accuracy_review_reminder",  # 1st of month
    ],
}
```

---

## 5. Algorithm Chi tiết

### 5.1 Failure Risk Score Formula

```
risk_score = Σ (normalized_indicator × weight)

Indicators:
  age_factor         = min(100, age_months / 120 × 100)
  downtime_rate      = min(100, annual_downtime_pct / 10 × 100)
  repair_cost_ratio  = min(100, (repair_cost_12m / asset_value × 100) / 50 × 100)
  pm_compliance_inv  = 100 - pm_compliance_pct
  mtbf_decline       = min(100, max(0, mtbf_decline_pct / 50 × 100))

Weights: age=0.20, downtime=0.30, cost=0.25, pm_inv=0.15, mtbf=0.10

Risk Tiers:
  0–39   → Low      (no alert)
  40–69  → Medium   (info notification)
  70–84  → High     (alert, SLA 48h)
  85–100 → Critical (alert, SLA 4h)
```

### 5.2 PM Interval Optimization Logic

```
Step 1: Gather last 12 completed PM records
Step 2: Gather last 20 CM records (failures)
Step 3: pre_pm_failure_rate = failures_within_30d_before_PM / total_failures
Step 4: pm_issue_rate = PMs_with_significant_issues / total_PMs

Decision:
  IF pre_pm_failure_rate > 0.4 → shorten by 20%
  IF pm_issue_rate < 0.2       → lengthen by 20%
  ELSE                         → no change

Step 5: Apply BR-17-06 minimum delta filter (15%)
Step 6: Apply BR-17-08 constraints (manufacturer limits, 7–365 days)
Step 7: Calculate confidence = 0.60 + (pm_count / 24) × 0.30
```

### 5.3 Spare Demand Forecast (Simple Moving Average)

```
Step 1: Get monthly consumption for last 12 months
Step 2: Remove anomalies (|z-score| > 3)
Step 3: window = min(3, available_months)
Step 4: avg_monthly = mean(last window months)
Step 5: FOR each forecast month i:
            seasonal_factor = historical_same_month_ratio (default 1.0)
            forecast[i] = avg_monthly × seasonal_factor

Reorder Point = ceil(daily_avg × (lead_time_days + buffer_days))
Order Quantity = ceil(avg_monthly × forecast_horizon_months)

Confidence: 0.50 + min(0.40, clean_history_count / 30)
```

### 5.4 Budget Forecast (Trend × Fleet)

```
Step 1: Calculate per-model monthly cost (24-month average)
Step 2: Calculate trend slope using linear regression on monthly totals
Step 3: FOR each forecast month i:
            base_cost = fleet_size × avg_cost_per_asset
            trend_adjustment = slope × i
            inflation_factor = 1.03^(i/12)  # 3% annual inflation
            monthly_forecast[i] = (base_cost + trend_adjustment) × inflation_factor

Confidence interval: ±15% (±1 std deviation of historical monthly variation)
```

### 5.5 Replacement Score Formula

```
score = age_score × 0.25 + tco_score × 0.30 +
        availability_score × 0.25 + failure_freq_score × 0.20

age_score         = min(100, age_months / 180 × 100)  [15 years = full score]
tco_score         = min(100, (TCO_24m / asset_value) / 1.5 × 100)  [150% ratio = full]
availability_score = 100 - availability_pct  [inverse: lower availability → higher score]
failure_freq_score = min(100, cm_count_24m / 10 × 100)  [10+ failures = full]

Recommended Actions:
  score < 60   → Continue Operation
  60 ≤ score < 75 → Monitor Closely
  75 ≤ score < 90 → Plan Replacement (trigger IMM-13 review)
  score ≥ 90   → Urgent Review (Critical alert)
```

---

## 6. MariaDB Aggregation Queries

### Query: Monthly Maintenance Cost by Category

```sql
-- Used by budget forecast and dashboard KPIs
SELECT
    DATE_FORMAT(t.scheduled_date, '%Y-%m') AS month,
    'PM' AS cost_category,
    SUM(t.total_cost) AS total_cost,
    COUNT(*) AS event_count
FROM `tabIMM PM Record` t
WHERE t.status = 'Completed'
  AND t.scheduled_date >= DATE_SUB(CURDATE(), INTERVAL 24 MONTH)
  AND t.docstatus = 1
GROUP BY DATE_FORMAT(t.scheduled_date, '%Y-%m')

UNION ALL

SELECT
    DATE_FORMAT(c.failure_date, '%Y-%m') AS month,
    'CM' AS cost_category,
    SUM(c.repair_cost) AS total_cost,
    COUNT(*) AS event_count
FROM `tabIMM CM Record` c
WHERE c.docstatus = 1
  AND c.failure_date >= DATE_SUB(CURDATE(), INTERVAL 24 MONTH)
GROUP BY DATE_FORMAT(c.failure_date, '%Y-%m')

ORDER BY month, cost_category;
```

### Query: Fleet Risk Overview (for Heatmap)

```sql
SELECT
    pr.asset,
    a.asset_name,
    a.department,
    a.asset_category,
    pr.risk_score,
    pr.risk_tier,
    pr.confidence_score,
    pr.confidence_level,
    pr.recommendation_text,
    prun.run_date AS last_prediction_date
FROM `tabIMM Prediction Result` pr
JOIN `tabAsset` a ON a.name = pr.asset
JOIN `tabIMM Prediction Run` prun ON prun.name = pr.prediction_run
WHERE pr.is_current = 1
  AND pr.model_type = 'Failure Risk'
  AND a.status = 'Active'
  AND a.docstatus = 1
ORDER BY pr.risk_score DESC;
```

### Query: Asset Downtime and Failure Rate (Aggregated)

```sql
SELECT
    cm.asset,
    COUNT(cm.name) AS failure_count,
    SUM(cm.downtime_hours) AS total_downtime_hours,
    SUM(cm.repair_cost) AS total_repair_cost,
    MIN(cm.failure_date) AS first_failure,
    MAX(cm.failure_date) AS last_failure,
    DATEDIFF(MAX(cm.failure_date), MIN(cm.failure_date)) /
        NULLIF(COUNT(cm.name) - 1, 0) AS mtbf_days
FROM `tabIMM CM Record` cm
WHERE cm.docstatus = 1
  AND cm.failure_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
GROUP BY cm.asset
HAVING failure_count >= 2;
```

---

## 7. What-If Simulation Engine (Simplified)

```python
# Simulation matrix for PM interval change

def _simulate_pm_interval_change(baseline: dict, scenario: dict) -> dict:
    """
    Empirical relationship between PM interval and outcomes:
    - Shorter PM interval (+cost ↑, -failures ↓, -downtime ↓)
    - Longer PM interval (-cost ↓, +failures ↑, +downtime ↑)

    These coefficients are derived from maintenance engineering literature
    and should be calibrated using actual hospital data after 12 months.
    """
    change_pct = flt(scenario.get("change_value", 0)) / 100

    # Empirical sensitivity coefficients
    COST_SENSITIVITY = 0.35    # 10% shorter PM → 3.5% more cost
    FAILURE_SENSITIVITY = 0.50  # 10% shorter PM → 5% fewer failures
    DOWNTIME_SENSITIVITY = 0.40 # 10% shorter PM → 4% less downtime
    DEMAND_SENSITIVITY = 0.20   # 10% shorter PM → 2% more spare demand

    # For interval shortening (negative change_pct):
    # cost goes up, failures/downtime go down
    direction = -1 if change_pct < 0 else 1

    return {
        "annual_cost": baseline["annual_cost"] * (
            1 + abs(change_pct) * COST_SENSITIVITY * direction
        ),
        "failure_rate": baseline["failure_rate"] * (
            1 - abs(change_pct) * FAILURE_SENSITIVITY * direction
        ),
        "annual_downtime_hours": baseline["annual_downtime_hours"] * (
            1 - abs(change_pct) * DOWNTIME_SENSITIVITY * direction
        ),
        "annual_spare_demand": baseline["annual_spare_demand"] * (
            1 + abs(change_pct) * DEMAND_SENSITIVITY * direction
        ),
    }
```

---

*File tiếp theo: IMM-17_API_Interface.md*
