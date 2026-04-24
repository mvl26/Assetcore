# IMM-06 — API Interface

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — Bàn giao & Đào tạo |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Base URL | `/api/method/assetcore.api.imm06.` |

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

### 2.1 `create_handover_record` [POST]

**URL:** `POST /api/method/assetcore.api.imm06.create_handover_record`

**Params:**

| Param | Type | Reqd | Mô tả |
|---|---|---|---|
| `commissioning_ref` | string | Yes | Tên phiếu Commissioning |
| `clinical_dept` | string | Yes | Mã khoa nhận |
| `handover_date` | string (YYYY-MM-DD) | Yes | Ngày bàn giao |
| `received_by` | string | Yes | Email người nhận |
| `handover_type` | string | No | Full/Conditional/Temporary (default: Full) |

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "HR-26-04-00001",
    "asset": "ACC-26-04-00001",
    "clinical_dept": "ICU",
    "handover_date": "2026-04-21",
    "workflow_state": "Draft",
    "status": "Draft"
  }
}
```

**Error codes:** `VALIDATION_ERROR` (VR-01, VR-02), `NOT_FOUND`

---

### 2.2 `get_handover_record` [GET]

**URL:** `GET /api/method/assetcore.api.imm06.get_handover_record?name=HR-26-04-00001`

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "HR-26-04-00001",
    "asset": "ACC-26-04-00001",
    "commissioning_ref": "IMM04-26-04-00001",
    "clinical_dept": "ICU",
    "handover_date": "2026-04-21",
    "received_by": "nurse@bv.vn",
    "handover_type": "Full",
    "status": "Training Completed",
    "training_sessions": [
      {
        "name": "TS-26-04-00001",
        "training_type": "Operation",
        "training_date": "2026-04-20",
        "status": "Completed",
        "trainees_count": 5,
        "passed_count": 5
      }
    ],
    "lifecycle_events": [ ... ]
  }
}
```

---

### 2.3 `list_handover_records` [GET]

**URL:** `GET /api/method/assetcore.api.imm06.list_handover_records`

**Params:** `status`, `dept`, `asset`, `page` (default 1), `page_size` (default 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "HR-26-04-00001",
        "asset": "ACC-26-04-00001",
        "clinical_dept": "ICU",
        "handover_date": "2026-04-21",
        "status": "Handed Over",
        "received_by": "nurse@bv.vn"
      }
    ],
    "total": 42,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

---

### 2.4 `schedule_training` [POST]

**URL:** `POST /api/method/assetcore.api.imm06.schedule_training`

**Params:**

| Param | Type | Reqd | Mô tả |
|---|---|---|---|
| `handover_name` | string | Yes | Mã phiếu bàn giao |
| `training_type` | string | Yes | Operation/Safety/Emergency/Maintenance/Full |
| `trainer` | string | Yes | Email trainer |
| `training_date` | string | Yes | Ngày đào tạo |
| `duration_hours` | float | No | Thời lượng giờ |
| `trainees` | JSON list | No | [{trainee_user, role}, ...] |

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-04-00001",
    "handover_ref": "HR-26-04-00001",
    "training_type": "Operation",
    "training_date": "2026-04-20",
    "status": "Scheduled"
  }
}
```

---

### 2.5 `complete_training` [POST]

**URL:** `POST /api/method/assetcore.api.imm06.complete_training`

**Params:**

| Param | Type | Reqd | Mô tả |
|---|---|---|---|
| `training_session_name` | string | Yes | Mã buổi đào tạo |
| `scores` | JSON list | No | [{trainee_user, score, passed}, ...] |
| `notes` | string | No | Ghi chú buổi học |

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-04-00001",
    "status": "Completed",
    "competency_confirmed": true,
    "passed_count": 5,
    "total_trainees": 5
  }
}
```

---

### 2.6 `confirm_handover` [POST]

**URL:** `POST /api/method/assetcore.api.imm06.confirm_handover`

**Params:**

| Param | Type | Reqd | Mô tả |
|---|---|---|---|
| `name` | string | Yes | Mã phiếu bàn giao |
| `dept_head_signoff` | string | Yes | Email Trưởng khoa |
| `notes` | string | No | Ghi chú bàn giao |

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "HR-26-04-00001",
    "status": "Handed Over",
    "docstatus": 1,
    "dept_head_signoff": "depthead@bv.vn",
    "lifecycle_event": "ALE-2026-0000123"
  }
}
```

**Error codes:** `VALIDATION_ERROR` (VR-03, VR-04)

---

### 2.7 `get_asset_training_history` [GET]

**URL:** `GET /api/method/assetcore.api.imm06.get_asset_training_history?asset_name=ACC-26-04-00001`

**Response:**
```json
{
  "success": true,
  "data": {
    "asset": "ACC-26-04-00001",
    "sessions": [
      {
        "name": "TS-26-04-00001",
        "training_type": "Operation",
        "training_date": "2026-04-20",
        "trainer": "biomed@bv.vn",
        "status": "Completed",
        "passed_count": 5
      }
    ],
    "total_sessions": 3,
    "total_trained": 15
  }
}
```

---

### 2.8 `get_dashboard_stats` [GET]

**URL:** `GET /api/method/assetcore.api.imm06.get_dashboard_stats`

**Response:**
```json
{
  "success": true,
  "data": {
    "total_pending_handover": 3,
    "completed_this_month": 8,
    "training_scheduled": 5,
    "avg_days_to_handover": 7.2,
    "training_pass_rate": 94.5
  }
}
```

---

## 3. Error Code Reference

| Code | Mô tả |
|---|---|
| `VALIDATION_ERROR` | Lỗi validation rule (VR-01..VR-04) |
| `NOT_FOUND` | Record không tồn tại |
| `PERMISSION_ERROR` | Không đủ quyền |
| `SYSTEM_ERROR` | Lỗi hệ thống — xem log |

*End of API Interface v1.0.0 — IMM-06*
