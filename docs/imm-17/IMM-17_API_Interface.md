# IMM-17 — Phân tích dự đoán
## API Interface Specification (OpenAPI 3.0)

**Phiên bản:** 1.0.0
**Ngày tạo:** 2026-04-24
**Base URL:** `https://{host}/api/method/assetcore.api.imm17`
**Authentication:** Frappe Session Token (`Authorization: token {api_key}:{api_secret}`)
**Content-Type:** `application/json`
**Response pattern:** `_ok(data)` / `_err(message, code)`

---

## OpenAPI Meta

```yaml
openapi: "3.0.3"
info:
  title: IMM-17 Predictive Analytics API
  version: "1.0.0"
  description: >
    API cho module IMM-17 — Phân tích dự đoán của hệ thống IMMIS.
    Tất cả endpoints đều read-only ngoại trừ các POST endpoints.
    Predictions là recommendations — không tự động tạo Work Order.
  contact:
    name: AssetCore Team
    email: assetcore@benhviennhi.org.vn

servers:
  - url: https://{host}/api/method/assetcore.api.imm17
    description: Production

components:
  securitySchemes:
    FrappeToken:
      type: apiKey
      in: header
      name: Authorization
      description: "Format: token {api_key}:{api_secret}"
  
  schemas:
    SuccessResponse:
      type: object
      properties:
        message:
          type: object
          properties:
            status:
              type: string
              example: "success"
            data:
              type: object

    ErrorResponse:
      type: object
      properties:
        message:
          type: object
          properties:
            status:
              type: string
              example: "error"
            error:
              type: string
            code:
              type: string

security:
  - FrappeToken: []
```

---

## Endpoint 1 — GET `/get_failure_risk_dashboard`

**Mô tả:** Lấy toàn bộ dữ liệu cho Failure Risk Dashboard bao gồm fleet heatmap data, active alerts, KPI summary.

**Roles:** HTM Engineer, HTM Manager, Innovation Center, QLCL

```yaml
GET /api/method/assetcore.api.imm17.get_failure_risk_dashboard

parameters:
  - name: department
    in: query
    required: false
    schema:
      type: string
    description: Lọc theo department (bỏ trống = tất cả)
  - name: asset_category
    in: query
    required: false
    schema:
      type: string
    description: Lọc theo loại thiết bị
  - name: risk_tier
    in: query
    required: false
    schema:
      type: string
      enum: [Low, Medium, High, Critical, All]
      default: All
  - name: include_insufficient_data
    in: query
    required: false
    schema:
      type: boolean
      default: false
    description: Có bao gồm assets không đủ dữ liệu không

responses:
  200:
    description: Dashboard data
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "summary": {
        "last_prediction_run": "2026-04-21T06:00:00",
        "prediction_age_days": 3,
        "is_stale": false,
        "total_assets_assessed": 247,
        "assets_insufficient_data": 18,
        "kpis": {
          "prediction_accuracy_rate_pct": 73.5,
          "preventable_failures_this_month": 3,
          "cost_avoidance_vnd": 85000000,
          "alert_response_rate_pct": 97.2,
          "model_confidence_avg": 0.76,
          "data_sufficiency_rate_pct": 87.9
        }
      },
      "risk_distribution": {
        "critical": 4,
        "high": 12,
        "medium": 47,
        "low": 184
      },
      "active_alerts": {
        "critical": 2,
        "high": 8,
        "medium": 15,
        "total": 25
      },
      "heatmap_data": [
        {
          "asset": "ACC-2021-00041",
          "asset_name": "Máy thở Ventilator Hamilton G5",
          "department": "ICU",
          "asset_category": "Respiratory Equipment",
          "risk_score": 88.3,
          "risk_tier": "Critical",
          "confidence_score": 0.82,
          "confidence_level": "High",
          "top_factors": [
            "Tỷ lệ downtime 8.2%",
            "Chi phí sửa chữa 42% giá trị",
            "Suy giảm MTBF 38%"
          ],
          "last_prediction_date": "2026-04-21T06:12:33",
          "active_alert_count": 1
        },
        {
          "asset": "ACC-2020-00018",
          "asset_name": "Máy siêu âm GE Voluson E10",
          "department": "Radiology",
          "asset_category": "Imaging",
          "risk_score": 76.1,
          "risk_tier": "High",
          "confidence_score": 0.71,
          "confidence_level": "Medium",
          "top_factors": [
            "PM compliance 58%",
            "Tuổi 72 tháng",
            "Tỷ lệ downtime 4.1%"
          ],
          "last_prediction_date": "2026-04-21T06:14:05",
          "active_alert_count": 1
        }
      ]
    }
  }
}
```

---

## Endpoint 2 — GET `/get_asset_risk_score`

**Mô tả:** Lấy chi tiết risk score và factor breakdown cho một asset cụ thể.

**Roles:** HTM Engineer, HTM Manager, Workshop

```yaml
GET /api/method/assetcore.api.imm17.get_asset_risk_score

parameters:
  - name: asset
    in: query
    required: true
    schema:
      type: string
    description: Asset document name (e.g. ACC-2021-00041)
  - name: include_history
    in: query
    required: false
    schema:
      type: boolean
      default: true
    description: Bao gồm lịch sử risk score 6 tháng gần nhất
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "asset": "ACC-2021-00041",
      "asset_name": "Máy thở Ventilator Hamilton G5",
      "department": "ICU",
      "current_prediction": {
        "risk_score": 88.3,
        "risk_tier": "Critical",
        "confidence_score": 0.82,
        "confidence_level": "High",
        "prediction_date": "2026-04-21T06:12:33",
        "recommendation": "KHẨN CẤP: Thiết bị có nguy cơ hỏng rất cao. Nguyên nhân chính: Tỷ lệ downtime, Chi phí sửa chữa. Đề xuất kiểm tra ngay và lên lịch CM."
      },
      "factor_breakdown": [
        {
          "factor_name": "Tỷ lệ downtime",
          "weight": 0.30,
          "raw_score": 82.0,
          "weighted_contribution": 24.6,
          "value": "8.2% downtime trong 12 tháng",
          "source_module": "IMM-09",
          "source_records": ["CM-2025-00234", "CM-2025-00287", "CM-2026-00051"]
        },
        {
          "factor_name": "Chi phí sửa chữa",
          "weight": 0.25,
          "raw_score": 84.0,
          "weighted_contribution": 21.0,
          "value": "42.1% giá trị tài sản trong 12 tháng",
          "source_module": "IMM-09",
          "source_records": ["CM-2025-00234", "CM-2025-00287", "CM-2026-00051"]
        },
        {
          "factor_name": "Suy giảm MTBF",
          "weight": 0.10,
          "raw_score": 76.0,
          "weighted_contribution": 7.6,
          "value": "38% suy giảm MTBF (từ 89 ngày → 55 ngày)",
          "source_module": "IMM-09"
        },
        {
          "factor_name": "Tuổi thiết bị",
          "weight": 0.20,
          "raw_score": 58.3,
          "weighted_contribution": 11.7,
          "value": "70 tháng (5 năm 10 tháng)",
          "source_module": "IMM-04"
        },
        {
          "factor_name": "Tuân thủ PM",
          "weight": 0.15,
          "raw_score": 22.0,
          "weighted_contribution": 3.3,
          "value": "78% compliance (đảo ngược: 22)",
          "source_module": "IMM-08"
        }
      ],
      "risk_score_history": [
        {"month": "2025-11", "risk_score": 54.2, "risk_tier": "Medium"},
        {"month": "2025-12", "risk_score": 61.8, "risk_tier": "Medium"},
        {"month": "2026-01", "risk_score": 68.3, "risk_tier": "Medium"},
        {"month": "2026-02", "risk_score": 75.1, "risk_tier": "High"},
        {"month": "2026-03", "risk_score": 82.7, "risk_tier": "High"},
        {"month": "2026-04", "risk_score": 88.3, "risk_tier": "Critical"}
      ],
      "active_alerts": [
        {
          "alert_name": "PALERT-2026-00142",
          "alert_type": "Failure Risk Critical",
          "severity": "Critical",
          "created_at": "2026-04-21T06:13:00",
          "sla_deadline": "2026-04-21T10:13:00",
          "status": "Open"
        }
      ]
    }
  }
}
```

---

## Endpoint 3 — GET `/get_pm_recommendations`

**Mô tả:** Lấy danh sách đề xuất tối ưu chu kỳ PM, có thể lọc theo status.

**Roles:** HTM Engineer, HTM Manager

```yaml
GET /api/method/assetcore.api.imm17.get_pm_recommendations

parameters:
  - name: status
    in: query
    required: false
    schema:
      type: string
      enum: [Pending, Accepted, Rejected, Deferred, All]
      default: Pending
  - name: department
    in: query
    required: false
    schema:
      type: string
  - name: sort_by
    in: query
    required: false
    schema:
      type: string
      enum: [confidence_desc, delta_pct_desc, asset_name]
      default: confidence_desc
  - name: limit
    in: query
    required: false
    schema:
      type: integer
      default: 50
      maximum: 200
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "total_recommendations": 14,
      "recommendations": [
        {
          "prediction_result": "PRED-20260421-00312",
          "asset": "ACC-2021-00041",
          "asset_name": "Máy thở Ventilator Hamilton G5",
          "department": "ICU",
          "current_interval_days": 90,
          "recommended_interval_days": 72,
          "delta_pct": -20.0,
          "direction": "Shorten",
          "rationale": "45% failures xảy ra trong 30 ngày trước PM → nên rút ngắn chu kỳ",
          "confidence_score": 0.78,
          "confidence_level": "Medium",
          "status": "Pending",
          "supporting_data": {
            "pm_count_analysed": 8,
            "cm_count_analysed": 11,
            "pm_issue_rate": 0.75,
            "pre_pm_failure_rate": 0.45
          },
          "created_at": "2026-04-21T06:14:00"
        },
        {
          "prediction_result": "PRED-20260421-00389",
          "asset": "ACC-2022-00078",
          "asset_name": "Monitor Bệnh nhân Philips MX700",
          "department": "Ward B",
          "current_interval_days": 180,
          "recommended_interval_days": 216,
          "delta_pct": 20.0,
          "direction": "Lengthen",
          "rationale": "Chỉ 12% PM phát hiện vấn đề → có thể kéo dài chu kỳ an toàn",
          "confidence_score": 0.83,
          "confidence_level": "High",
          "status": "Pending",
          "created_at": "2026-04-21T06:17:00"
        }
      ]
    }
  }
}
```

---

## Endpoint 4 — GET `/get_spare_demand_forecast`

**Mô tả:** Lấy dự báo nhu cầu phụ tùng theo danh mục hoặc part number cụ thể.

**Roles:** Workshop, Warehouse, HTM Manager

```yaml
GET /api/method/assetcore.api.imm17.get_spare_demand_forecast

parameters:
  - name: part
    in: query
    required: false
    schema:
      type: string
    description: Lọc theo Item Code (bỏ trống = tất cả)
  - name: device_model
    in: query
    required: false
    schema:
      type: string
    description: Lọc theo Device Model
  - name: months
    in: query
    required: false
    schema:
      type: integer
      default: 3
      minimum: 1
      maximum: 6
    description: Số tháng dự báo
  - name: show_reorder_only
    in: query
    required: false
    schema:
      type: boolean
      default: false
    description: Chỉ hiển thị parts có current_stock < reorder_point
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "forecast_months": 3,
      "generated_at": "2026-04-21T06:00:00",
      "summary": {
        "total_parts_forecast": 87,
        "parts_below_reorder_point": 12,
        "parts_stockout_risk_14d": 3
      },
      "forecasts": [
        {
          "part": "SPARE-VENT-FILTER-001",
          "part_name": "Bộ lọc vi khuẩn Ventilator Hamilton G5",
          "device_model": "Hamilton G5",
          "current_stock": 8,
          "reorder_point": 15,
          "recommended_order_qty": 30,
          "lead_time_days": 21,
          "status": "REORDER_REQUIRED",
          "monthly_forecast": [
            {"month": 1, "forecasted_quantity": 10.5, "seasonal_factor": 1.0},
            {"month": 2, "forecasted_quantity": 9.8, "seasonal_factor": 0.93},
            {"month": 3, "forecasted_quantity": 11.2, "seasonal_factor": 1.07}
          ],
          "avg_monthly_demand": 10.5,
          "confidence_score": 0.81,
          "confidence_level": "High",
          "anomalies_removed": 1,
          "history_months_used": 11
        },
        {
          "part": "SPARE-ECG-LEAD-003",
          "part_name": "Dây điện tim 5-lead Philips",
          "device_model": "Philips MX700",
          "current_stock": 45,
          "reorder_point": 20,
          "recommended_order_qty": 36,
          "lead_time_days": 14,
          "status": "ADEQUATE",
          "monthly_forecast": [
            {"month": 1, "forecasted_quantity": 12.0, "seasonal_factor": 1.0},
            {"month": 2, "forecasted_quantity": 12.0, "seasonal_factor": 1.0},
            {"month": 3, "forecasted_quantity": 12.0, "seasonal_factor": 1.0}
          ],
          "avg_monthly_demand": 12.0,
          "confidence_score": 0.65,
          "confidence_level": "Medium",
          "anomalies_removed": 0,
          "history_months_used": 8
        }
      ]
    }
  }
}
```

---

## Endpoint 5 — GET `/get_budget_forecast`

**Mô tả:** Lấy dự báo ngân sách bảo trì 12 tháng rolling.

**Roles:** KH-TC, HTM Manager, BGĐ, QLCL

```yaml
GET /api/method/assetcore.api.imm17.get_budget_forecast

parameters:
  - name: months
    in: query
    required: false
    schema:
      type: integer
      default: 12
      minimum: 3
      maximum: 24
  - name: department
    in: query
    required: false
    schema:
      type: string
  - name: include_actuals
    in: query
    required: false
    schema:
      type: boolean
      default: true
    description: Bao gồm chi phí thực tế tháng đã qua để so sánh
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "forecast_generated_at": "2026-04-21T06:00:00",
      "fleet_size": 247,
      "confidence_interval_pct": 15,
      "annual_forecast_total_vnd": 4820000000,
      "confidence_lower_vnd": 4097000000,
      "confidence_upper_vnd": 5543000000,
      "monthly_forecast": [
        {
          "month": "2026-05",
          "month_label": "Tháng 5/2026",
          "pm_cost": 125000000,
          "cm_cost": 87000000,
          "calibration_cost": 23000000,
          "parts_cost": 156000000,
          "total": 391000000,
          "confidence_lower": 332000000,
          "confidence_upper": 450000000,
          "is_actual": false
        },
        {
          "month": "2026-04",
          "month_label": "Tháng 4/2026",
          "pm_cost": 118000000,
          "cm_cost": 94000000,
          "calibration_cost": 21000000,
          "parts_cost": 148000000,
          "total": 381000000,
          "actual_total": 367000000,
          "variance_pct": -3.7,
          "is_actual": true
        }
      ],
      "ytd_comparison": {
        "budget_approved_vnd": 4200000000,
        "forecast_vnd": 4820000000,
        "overrun_pct": 14.8,
        "alert_triggered": true,
        "alert_message": "Dự báo vượt ngân sách 14.8% — cần xem xét điều chỉnh"
      }
    }
  }
}
```

---

## Endpoint 6 — GET `/get_replacement_candidates`

**Mô tả:** Lấy danh sách thiết bị có điểm số thay thế cao nhất.

**Roles:** HTM Manager, KH-TC, BGĐ

```yaml
GET /api/method/assetcore.api.imm17.get_replacement_candidates

parameters:
  - name: min_score
    in: query
    required: false
    schema:
      type: number
      default: 60.0
  - name: department
    in: query
    required: false
    schema:
      type: string
  - name: include_action
    in: query
    required: false
    schema:
      type: string
      enum: [All, Monitor Closely, Plan Replacement, Urgent Review]
      default: All
  - name: limit
    in: query
    required: false
    schema:
      type: integer
      default: 20
      maximum: 100
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "total_candidates": 8,
      "urgent_review_count": 2,
      "plan_replacement_count": 4,
      "monitor_count": 2,
      "candidates": [
        {
          "asset": "ACC-2019-00007",
          "asset_name": "Máy X-quang di động Siemens Ysio Max",
          "department": "Radiology",
          "score": 91.3,
          "recommended_action": "Urgent Review",
          "age_months": 84,
          "asset_value_vnd": 2800000000,
          "total_cost_of_ownership_24m_vnd": 4760000000,
          "tco_to_value_ratio": 1.7,
          "availability_pct": 72.3,
          "cm_count_24m": 14,
          "sub_scores": {
            "age_score": 46.7,
            "tco_score": 100.0,
            "availability_score": 27.7,
            "failure_freq_score": 100.0
          },
          "key_drivers": [
            "TCO 170% giá trị tài sản trong 24 tháng",
            "14 sự kiện CM trong 24 tháng",
            "Độ sẵn sàng 72.3%"
          ],
          "projected_12m_maintenance_cost_vnd": 1850000000,
          "confidence_score": 0.85,
          "imm13_review_initiated": false
        }
      ]
    }
  }
}
```

---

## Endpoint 7 — POST `/run_what_if_analysis`

**Mô tả:** Khởi chạy một what-if scenario analysis.

**Roles:** HTM Manager, KH-TC, Innovation Center

```yaml
POST /api/method/assetcore.api.imm17.run_what_if_analysis

requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        required: [scenario_name, scenario_type, change_value, change_unit]
        properties:
          scenario_name:
            type: string
            example: "Giảm PM interval Ventilator 20%"
          scenario_type:
            type: string
            enum: [PM_INTERVAL, FLEET_REDUCTION, PARTS_COST, STAFF_CAPACITY]
          scope_type:
            type: string
            enum: [ALL, DEPARTMENT, DEVICE_MODEL, ASSET_LIST]
            default: ALL
          scope_value:
            type: string
            description: Department name / Device Model / comma-separated assets
          change_value:
            type: number
            description: Magnitude of change (positive = increase, negative = decrease)
          change_unit:
            type: string
            enum: [PERCENT, ABSOLUTE]
            default: PERCENT
          notes:
            type: string
```

**Request Example:**

```json
{
  "scenario_name": "Giảm PM interval Ventilator 20%",
  "scenario_type": "PM_INTERVAL",
  "scope_type": "DEVICE_MODEL",
  "scope_value": "Hamilton G5",
  "change_value": -20,
  "change_unit": "PERCENT",
  "notes": "Phân tích trước khi trình BGĐ Q2/2026"
}
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "scenario_name": "PR-WHATIF-2026-00023",
      "scenario_type": "PM_INTERVAL",
      "scope": "Device Model: Hamilton G5 (12 assets)",
      "change_description": "Giảm PM interval 20% (từ 90 → 72 ngày)",
      "baseline": {
        "annual_cost_vnd": 1240000000,
        "failure_rate_per_100_asset_months": 2.8,
        "annual_downtime_hours": 312,
        "annual_spare_demand_units": 420
      },
      "projected": {
        "annual_cost_vnd": 1327000000,
        "failure_rate_per_100_asset_months": 1.96,
        "annual_downtime_hours": 218,
        "annual_spare_demand_units": 445
      },
      "delta": {
        "annual_cost_delta_vnd": 87000000,
        "annual_cost_delta_pct": 7.0,
        "failure_rate_delta_pct": -30.0,
        "downtime_delta_hours": -94,
        "downtime_delta_pct": -30.1,
        "spare_demand_delta_pct": 6.0
      },
      "interpretation": "Tăng chi phí 87 triệu VNĐ/năm để giảm 94 giờ downtime và 30% tỷ lệ hỏng hóc.",
      "assumptions": [
        "Tỷ lệ thất bại giữ nguyên trừ thay đổi trực tiếp từ PM interval",
        "Chi phí nhân công giữ nguyên",
        "Không có thay đổi về fleet composition",
        "Kết quả mang tính xấp xỉ, sai số ±15%"
      ],
      "confidence_note": "Kết quả mang tính ước tính. Không dùng như cam kết ngân sách.",
      "expires_at": "2026-07-21",
      "status": "Completed"
    }
  }
}
```

---

## Endpoint 8 — GET `/get_what_if_result`

**Mô tả:** Lấy kết quả của một what-if scenario đã chạy trước.

**Roles:** HTM Manager, KH-TC, Innovation Center, QLCL

```yaml
GET /api/method/assetcore.api.imm17.get_what_if_result

parameters:
  - name: scenario
    in: query
    required: true
    schema:
      type: string
    description: IMM What If Scenario name (e.g. PR-WHATIF-2026-00023)
```

**Response:** Same structure as `/run_what_if_analysis` response.

---

## Endpoint 9 — POST `/configure_alert_threshold`

**Mô tả:** Cập nhật ngưỡng alert configuration.

**Roles:** Innovation Center, System Manager

```yaml
POST /api/method/assetcore.api.imm17.configure_alert_threshold

requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        required: [alert_type]
        properties:
          alert_type:
            type: string
            enum: [Failure Risk High, Failure Risk Critical, PM Optimization,
                   Spare Reorder, Spare Stockout Risk, Budget Overrun,
                   Replacement Candidate, Replacement Urgent,
                   Model Low Accuracy, Data Insufficient]
          is_active:
            type: boolean
          high_threshold:
            type: number
            minimum: 50
            maximum: 95
          critical_threshold:
            type: number
            minimum: 70
            maximum: 98
          sla_ack_hours_high:
            type: integer
            minimum: 4
            maximum: 168
          sla_ack_hours_critical:
            type: integer
            minimum: 1
            maximum: 48
          notify_channel:
            type: string
            enum: [In-App, Email, Both]
          dedup_window_hours:
            type: integer
            minimum: 1
            maximum: 168
          effective_date:
            type: string
            format: date
```

**Request Example:**

```json
{
  "alert_type": "Failure Risk High",
  "high_threshold": 72,
  "critical_threshold": 87,
  "sla_ack_hours_high": 36,
  "sla_ack_hours_critical": 4,
  "notify_channel": "Both",
  "effective_date": "2026-05-01"
}
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "alert_config": "ALCFG-Failure Risk High",
      "updated_fields": ["high_threshold", "critical_threshold", "sla_ack_hours_high"],
      "effective_date": "2026-05-01",
      "simulation": {
        "current_alerts_that_would_fire": 15,
        "current_alerts_that_would_not_fire": 3,
        "note": "Với ngưỡng mới, 15 alerts hiện tại vẫn sẽ fire"
      },
      "audit_trail": "ALCFG-AUDIT-2026-00089"
    }
  }
}
```

---

## Endpoint 10 — GET `/get_active_alerts`

**Mô tả:** Lấy danh sách predictive alerts đang active, chưa được acknowledge hoặc đã escalate.

**Roles:** All HTM roles, QLCL, KH-TC (financial alerts only)

```yaml
GET /api/method/assetcore.api.imm17.get_active_alerts

parameters:
  - name: severity
    in: query
    required: false
    schema:
      type: string
      enum: [All, Critical, High, Medium, Info]
      default: All
  - name: status
    in: query
    required: false
    schema:
      type: string
      enum: [Open, Escalated, All]
      default: All
  - name: alert_type
    in: query
    required: false
    schema:
      type: string
  - name: department
    in: query
    required: false
    schema:
      type: string
  - name: overdue_only
    in: query
    required: false
    schema:
      type: boolean
      default: false
    description: Chỉ hiển thị alerts đã quá SLA deadline
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "total_open": 25,
      "overdue_count": 3,
      "alerts": [
        {
          "name": "PALERT-2026-00142",
          "asset": "ACC-2021-00041",
          "asset_name": "Máy thở Ventilator Hamilton G5",
          "department": "ICU",
          "alert_type": "Failure Risk Critical",
          "severity": "Critical",
          "title": "[CRITICAL] Failure Risk Critical — ACC-2021-00041",
          "description": "KHẨN CẤP: Risk score 88.3. Nguyên nhân chính: Tỷ lệ downtime 8.2%, Chi phí sửa chữa 42%.",
          "status": "Open",
          "created_at": "2026-04-21T06:13:00",
          "sla_deadline": "2026-04-21T10:13:00",
          "is_overdue": true,
          "hours_overdue": 15.5,
          "prediction_result": "PRED-20260421-00301"
        },
        {
          "name": "PALERT-2026-00143",
          "asset": "ACC-2020-00018",
          "asset_name": "Máy siêu âm GE Voluson E10",
          "department": "Radiology",
          "alert_type": "Failure Risk High",
          "severity": "High",
          "title": "[HIGH] Failure Risk High — ACC-2020-00018",
          "status": "Open",
          "created_at": "2026-04-21T06:14:00",
          "sla_deadline": "2026-04-23T06:14:00",
          "is_overdue": false,
          "hours_remaining": 32.2
        }
      ]
    }
  }
}
```

---

## Endpoint 11 — POST `/acknowledge_alert`

**Mô tả:** Acknowledge một predictive alert và ghi nhận hành động sẽ thực hiện.

**Roles:** HTM Engineer (High alerts), HTM Manager (Critical alerts)

```yaml
POST /api/method/assetcore.api.imm17.acknowledge_alert

requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        required: [alert_name, action_taken]
        properties:
          alert_name:
            type: string
            description: IMM Predictive Alert name
          action_taken:
            type: string
            description: Mô tả hành động đã/sẽ thực hiện (bắt buộc cho audit trail)
          close_alert:
            type: boolean
            default: false
            description: Đóng alert sau khi acknowledge (nếu đã xử lý xong)
          related_work_order:
            type: string
            description: WO liên quan nếu đã tạo CM/inspection
```

**Request Example:**

```json
{
  "alert_name": "PALERT-2026-00142",
  "action_taken": "Đã lên lịch inspection đặc biệt cho ngày 22/4. Kỹ thuật viên sẽ kiểm tra hệ thống thở và van.",
  "close_alert": false,
  "related_work_order": "WO-2026-00891"
}
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "alert_name": "PALERT-2026-00142",
      "acknowledged_by": "nguyen.van.a@benhviennhi.org.vn",
      "acknowledged_at": "2026-04-21T09:45:00",
      "sla_met": true,
      "time_to_acknowledge_hours": 3.5,
      "action_recorded": true,
      "audit_entry": "ACK-AUDIT-2026-00231"
    }
  }
}
```

---

## Endpoint 12 — POST `/trigger_prediction_run`

**Mô tả:** Kích hoạt thủ công một prediction run (ngoài lịch weekly scheduled).

**Roles:** Innovation Center, System Manager

```yaml
POST /api/method/assetcore.api.imm17.trigger_prediction_run

requestBody:
  required: false
  content:
    application/json:
      schema:
        type: object
        properties:
          models:
            type: array
            items:
              type: string
              enum: [failure_risk, pm_optimization, replacement_score, budget_forecast]
            default: [failure_risk, replacement_score]
          filters:
            type: object
            properties:
              department:
                type: string
              asset_category:
                type: string
              asset_list:
                type: array
                items:
                  type: string
          notes:
            type: string
```

**Response Example (200 — async job started):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "prediction_run": "PR-2026-04-00089",
      "run_type": "Manual",
      "models_queued": ["failure_risk", "replacement_score"],
      "assets_in_scope": 247,
      "estimated_duration_seconds": 45,
      "status": "Queued",
      "note": "Job đã được queued. Kiểm tra lại sau 60 giây hoặc xem trang Prediction History."
    }
  }
}
```

---

## Endpoint 13 — GET `/get_prediction_history`

**Mô tả:** Lấy lịch sử các lần chạy prediction model.

**Roles:** Innovation Center, QLCL, System Manager

```yaml
GET /api/method/assetcore.api.imm17.get_prediction_history

parameters:
  - name: limit
    in: query
    required: false
    schema:
      type: integer
      default: 20
      maximum: 100
  - name: run_type
    in: query
    required: false
    schema:
      type: string
      enum: [All, Scheduled, Manual]
      default: All
  - name: status
    in: query
    required: false
    schema:
      type: string
      enum: [All, Completed, Failed, Partial]
      default: All
  - name: from_date
    in: query
    required: false
    schema:
      type: string
      format: date
  - name: to_date
    in: query
    required: false
    schema:
      type: string
      format: date
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "total_runs": 18,
      "runs": [
        {
          "name": "PR-2026-04-00089",
          "run_date": "2026-04-21T06:00:00",
          "run_type": "Scheduled",
          "status": "Completed",
          "model_version": "1.0.0",
          "total_assets_in_scope": 247,
          "processed_assets": 241,
          "skipped_assets": 6,
          "alerts_generated": 7,
          "duration_seconds": 38.4,
          "error_count": 0
        },
        {
          "name": "PR-2026-04-00078",
          "run_date": "2026-04-14T06:00:00",
          "run_type": "Scheduled",
          "status": "Completed",
          "total_assets_in_scope": 246,
          "processed_assets": 238,
          "skipped_assets": 8,
          "alerts_generated": 5,
          "duration_seconds": 36.1
        }
      ]
    }
  }
}
```

---

## Endpoint 14 — GET `/get_model_accuracy_metrics`

**Mô tả:** Lấy metrics đánh giá độ chính xác của predictive models.

**Roles:** Innovation Center, QLCL, System Manager

```yaml
GET /api/method/assetcore.api.imm17.get_model_accuracy_metrics

parameters:
  - name: model_type
    in: query
    required: false
    schema:
      type: string
      enum: [All, Failure Risk, PM Optimization, Replacement Score]
      default: All
  - name: lookback_months
    in: query
    required: false
    schema:
      type: integer
      default: 6
      minimum: 3
      maximum: 24
```

**Response Example (200):**

```json
{
  "message": {
    "status": "success",
    "data": {
      "evaluated_period": "2025-11 to 2026-04",
      "evaluation_note": "Accuracy calculated by comparing predictions (risk_score > 70) vs. actual failures within 90 days",
      "models": [
        {
          "model_type": "Failure Risk",
          "model_version": "1.0.0",
          "total_predictions": 1284,
          "high_risk_predictions": 87,
          "confirmed_failures": 64,
          "true_positive_rate": 0.735,
          "false_positive_rate": 0.265,
          "precision": 0.735,
          "recall": 0.812,
          "f1_score": 0.771,
          "accuracy_trend": [
            {"month": "2025-11", "true_positive_rate": 0.68},
            {"month": "2025-12", "true_positive_rate": 0.70},
            {"month": "2026-01", "true_positive_rate": 0.72},
            {"month": "2026-02", "true_positive_rate": 0.73},
            {"month": "2026-03", "true_positive_rate": 0.74},
            {"month": "2026-04", "true_positive_rate": 0.74}
          ],
          "meets_target": true,
          "target_true_positive_rate": 0.70,
          "data_quality_score": 0.879,
          "last_review_date": "2026-04-07",
          "last_reviewed_by": "innovation.center@benhviennhi.org.vn"
        }
      ],
      "overall_data_sufficiency": {
        "total_active_assets": 247,
        "assets_with_sufficient_data": 217,
        "sufficiency_rate_pct": 87.9
      }
    }
  }
}
```

---

## Error Response Examples

### 400 — Bad Request

```json
{
  "message": {
    "status": "error",
    "error": "Tham số 'asset' là bắt buộc",
    "code": "MISSING_REQUIRED_PARAM"
  }
}
```

### 403 — Forbidden

```json
{
  "message": {
    "status": "error",
    "error": "Bạn không có quyền xem dữ liệu tài chính của module này",
    "code": "INSUFFICIENT_PERMISSION"
  }
}
```

### 404 — Not Found

```json
{
  "message": {
    "status": "error",
    "error": "Không tìm thấy prediction result cho asset ACC-2021-00999",
    "code": "PREDICTION_NOT_FOUND"
  }
}
```

### 422 — Insufficient Data

```json
{
  "message": {
    "status": "error",
    "error": "Asset ACC-2024-00201 chưa đủ dữ liệu để chạy prediction (cần ít nhất 6 tháng vận hành và 2+ sự kiện PM hoặc CM)",
    "code": "INSUFFICIENT_DATA"
  }
}
```

---

## Rate Limits

| Endpoint category | Limit |
|---|---|
| GET dashboard/list endpoints | 60 req/min per user |
| GET individual asset endpoints | 120 req/min per user |
| POST what-if analysis | 10 req/min per user |
| POST trigger_prediction_run | 5 req/hour per user |
| POST configure_alert | 20 req/min per user |

---

*File tiếp theo: IMM-17_UI_UX_Guide.md*
