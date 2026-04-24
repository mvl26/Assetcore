# IMM-07 — API Interface

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-07 — Vận hành hàng ngày |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Base URL | `/api/method/assetcore.api.imm07.` |

---

## 1. Response Envelope

```json
// Success
{ "success": true, "data": { ... } }

// Error
{ "success": false, "error": "message", "code": "ERROR_CODE" }
```

---

## 2. Endpoints

### 2.1 `create_daily_log` [POST]

**URL:** `POST /api/method/assetcore.api.imm07.create_daily_log`

**Params:**

| Param | Type | Reqd | Mô tả |
|---|---|---|---|
| `asset` | string | Yes | Mã thiết bị |
| `log_date` | string | Yes | Ngày (YYYY-MM-DD) |
| `shift` | string | Yes | Morning 06-14 / Afternoon 14-22 / Night 22-06 |
| `operated_by` | string | Yes | Email người vận hành |
| `operational_status` | string | Yes | Running/Standby/Fault/Under Maintenance/Not Used |
| `start_meter_hours` | float | No | Số giờ máy đầu ca (default 0) |
| `end_meter_hours` | float | No | Số giờ máy cuối ca (default 0) |
| `usage_cycles` | int | No | Số chu kỳ (default 0) |
| `anomaly_detected` | int | No | 0/1 (default 0) |
| `anomaly_type` | string | No | None/Minor/Major/Critical (default None) |
| `anomaly_description` | string | No | Mô tả bất thường |

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "DOL-26-04-21-00001",
    "asset": "ACC-26-04-00001",
    "log_date": "2026-04-21",
    "shift": "Morning 06-14",
    "operational_status": "Running",
    "runtime_hours": 8.0,
    "workflow_state": "Open"
  }
}
```

**Error codes:** `VALIDATION_ERROR` (VR-01, VR-02, VR-03)

---

### 2.2 `get_daily_log` [GET]

**URL:** `GET /api/method/assetcore.api.imm07.get_daily_log?name=DOL-26-04-21-00001`

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "DOL-26-04-21-00001",
    "asset": "ACC-26-04-00001",
    "log_date": "2026-04-21",
    "shift": "Morning 06-14",
    "operated_by": "nurse@bv.vn",
    "operational_status": "Running",
    "start_meter_hours": 1500,
    "end_meter_hours": 1508,
    "runtime_hours": 8.0,
    "anomaly_detected": 0,
    "workflow_state": "Open"
  }
}
```

---

### 2.3 `list_daily_logs` [GET]

**URL:** `GET /api/method/assetcore.api.imm07.list_daily_logs`

**Params:** `asset`, `dept`, `date_from`, `date_to`, `operational_status`, `page` (default 1), `page_size` (default 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "DOL-26-04-21-00001",
        "asset": "ACC-26-04-00001",
        "log_date": "2026-04-21",
        "shift": "Morning 06-14",
        "operational_status": "Running",
        "runtime_hours": 8.0
      }
    ],
    "total": 90,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

---

### 2.4 `submit_log` [POST]

**URL:** `POST /api/method/assetcore.api.imm07.submit_log`

**Params:** `name` (string, reqd)

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "DOL-26-04-21-00001",
    "workflow_state": "Logged",
    "docstatus": 0,
    "linked_incident": null
  }
}
```

Nếu anomaly Major/Critical:
```json
{
  "success": true,
  "data": {
    "name": "DOL-26-04-21-00002",
    "workflow_state": "Logged",
    "linked_incident": "INC-26-04-00007"
  }
}
```

---

### 2.5 `review_log` [POST]

**URL:** `POST /api/method/assetcore.api.imm07.review_log`

**Params:**

| Param | Type | Reqd |
|---|---|---|
| `name` | string | Yes |
| `reviewer_notes` | string | No |

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "DOL-26-04-21-00001",
    "workflow_state": "Reviewed",
    "docstatus": 1,
    "reviewed_by": "depthead@bv.vn",
    "review_date": "2026-04-21"
  }
}
```

---

### 2.6 `get_asset_operation_summary` [GET]

**URL:** `GET /api/method/assetcore.api.imm07.get_asset_operation_summary?asset_name=ACC-26-04-00001&days=30`

**Response:**
```json
{
  "success": true,
  "data": {
    "asset": "ACC-26-04-00001",
    "period_days": 30,
    "total_runtime_hours": 192.5,
    "uptime_pct": 85.3,
    "anomaly_count": 3,
    "fault_days": 2,
    "by_shift": {
      "Morning 06-14": 75.0,
      "Afternoon 14-22": 72.5,
      "Night 22-06": 45.0
    },
    "status_breakdown": {
      "Running": 25,
      "Standby": 3,
      "Fault": 2
    }
  }
}
```

---

### 2.7 `get_dashboard_stats` [GET]

**URL:** `GET /api/method/assetcore.api.imm07.get_dashboard_stats?dept=ICU`

**Params:** `dept` (optional, filter by department)

**Response:**
```json
{
  "success": true,
  "data": {
    "date": "2026-04-21",
    "dept": "ICU",
    "total_assets": 12,
    "running": 10,
    "standby": 1,
    "fault": 1,
    "under_maintenance": 0,
    "not_used": 0,
    "total_runtime_hours_today": 76.5,
    "anomaly_count_today": 1,
    "assets_by_status": [
      { "asset": "ACC-26-04-00001", "name": "Máy thở A", "status": "Running" },
      { "asset": "ACC-26-04-00010", "name": "Monitor B", "status": "Fault" }
    ]
  }
}
```

---

### 2.8 `report_anomaly_from_log` [POST]

**URL:** `POST /api/method/assetcore.api.imm07.report_anomaly_from_log`

**Params:**

| Param | Type | Reqd |
|---|---|---|
| `log_name` | string | Yes |
| `severity` | string | Yes (Minor/Major/Critical) |
| `description` | string | Yes |

**Response:**
```json
{
  "success": true,
  "data": {
    "incident": "INC-26-04-00007",
    "log": "DOL-26-04-21-00001",
    "severity": "Critical"
  }
}
```

---

## 3. Error Code Reference

| Code | Mô tả |
|---|---|
| `VALIDATION_ERROR` | Lỗi VR-01..VR-03 |
| `NOT_FOUND` | Record không tồn tại |
| `PERMISSION_ERROR` | Không đủ quyền |
| `DUPLICATE_LOG` | Log trùng ca/asset/ngày (VR-01) |
| `SYSTEM_ERROR` | Lỗi hệ thống |

*End of API Interface v1.0.0 — IMM-07*
