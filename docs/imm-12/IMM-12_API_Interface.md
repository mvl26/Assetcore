# IMM-12 — API Interface
## Endpoints, Sequence Diagrams & JSON Contracts

**Module:** IMM-12
**Version:** 1.0
**Ngày:** 2026-04-17
**Trạng thái:** Draft

---

## 1. Sequence Diagrams

### 1.1 Report P1 Incident + Auto Escalation Flow

```
Reporting User          Frontend            Backend API           Scheduler
      │                    │                     │                    │
      │  Fill form P1      │                     │                    │
      │  (asset, fault)    │                     │                    │
      ├──────────────────► │                     │                    │
      │                    │  POST create_incident                    │
      │                    ├────────────────────►│                    │
      │                    │                     │ validate asset     │
      │                    │                     │ set created_at     │
      │                    │                     │ status = New       │
      │                    │                     │ create Lifecycle   │
      │                    │                     │ Event              │
      │                    │◄────────────────────┤                    │
      │                    │  {ir_name, status}  │                    │
      │◄───────────────────┤                     │                    │
      │  "IR-2026-00042    │                     │                    │
      │   đã tạo — P1      │                     │                    │
      │   SLA: 30 phút"    │                     │                    │
      │                    │                     │                    │
      │         [30 minutes pass — Workshop Manager không Acknowledge]│
      │                    │                     │                    │
      │                    │          ◄──────────┤ check_sla_timers() │
      │                    │                     │ elapsed > 30 min   │
      │                    │                     │ response_breached  │
      │                    │                     │ = True             │
      │                    │                     │                    │
      │                    │                     │ create SLA         │
      │                    │                     │ Compliance Log     │
      │                    │                     │ (immutable)        │
      │                    │                     │                    │
      │                    │                     │ sendmail →         │
      │                    │                     │ BGĐ + PTP Khối 2   │
      │                    │                     │                    │
      BGĐ Email ◄──────────────────────────────────────────────────┤
      PTP Email ◄──────────────────────────────────────────────────┤
```

---

### 1.2 SLA Breach Detection Flow (Every 30 Minutes)

```
Scheduler               Database               Notification          SLA Log
    │                      │                        │                   │
    │ Every 30 min         │                        │                   │
    ├─────────────────────►│                        │                   │
    │ get_all IR where     │                        │                   │
    │ status IN            │                        │                   │
    │ (New, Ack, In Prog)  │                        │                   │
    │◄─────────────────────┤                        │                   │
    │ [list of open IRs]   │                        │                   │
    │                      │                        │                   │
    │ FOR each IR:         │                        │                   │
    │  elapsed = now - created_at                   │                   │
    │  IF elapsed >= sla_limit:                     │                   │
    │    ├─ check SLA Log  │                        │                   │
    │    │  exists?        │                        │                   │
    │    ├────────────────►│                        │                   │
    │    │◄────────────────┤                        │                   │
    │    │  [exists = NO]  │                        │                   │
    │    │                 │                        │                   │
    │    ├─ set_value      │                        │                   │
    │    │  breached = True│                        │                   │
    │    ├────────────────►│                        │                   │
    │    │                 │                        │                   │
    │    ├─ INSERT         │                        │                   │
    │    │  SLA Compliance │                        │                   │
    │    │  Log            │                        │                   │
    │    ├────────────────────────────────────────────────────────────►│
    │    │                 │                        │                   │
    │    ├─ sendmail       │                        │                   │
    │    ├────────────────────────────────────────►│                   │
    │    │                 │         email sent     │                   │
    │    │                 │         to recipients  │                   │
    │                      │                        │                   │
    │  ELSE IF elapsed >= 0.8 * sla_limit:         │                   │
    │    ├─ set sla_status = "At Risk"              │                   │
    │    ├────────────────►│                        │                   │
    │    ├─ send At Risk alert                      │                   │
    │    ├────────────────────────────────────────►│                   │
```

---

### 1.3 Chronic Failure Detection → RCA Creation Flow

```
Daily Scheduler      Database           RCA Record         Notifications
     │                  │                   │                   │
     │ 02:00 daily      │                   │                   │
     │ detect_chronic   │                   │                   │
     ├─────────────────►│                   │                   │
     │ SQL GROUP BY     │                   │                   │
     │ (asset,          │                   │                   │
     │  fault_code)     │                   │                   │
     │ HAVING COUNT≥3   │                   │                   │
     │◄─────────────────┤                   │                   │
     │ [chronic groups] │                   │                   │
     │                  │                   │                   │
     │ FOR each group:  │                   │                   │
     │  check existing  │                   │                   │
     │  open RCA?       │                   │                   │
     ├─────────────────►│                   │                   │
     │◄─────────────────┤                   │                   │
     │  [NO open RCA]   │                   │                   │
     │                  │                   │                   │
     │  INSERT RCA      │                   │                   │
     │  Record          │                   │                   │
     ├────────────────────────────────────►│                   │
     │◄────────────────────────────────────┤                   │
     │  RCA-2026-00007  │                   │                   │
     │                  │                   │                   │
     │  UPDATE IR       │                   │                   │
     │  is_chronic=True │                   │                   │
     │  rca_record=RCA  │                   │                   │
     ├─────────────────►│                   │                   │
     │                  │                   │                   │
     │  notify Workshop │                   │                   │
     │  Manager + PTP   │                   │                   │
     ├──────────────────────────────────────────────────────►│
     │                  │                   │  Chronic Failure   │
     │                  │                   │  Alert sent        │
```

---

### 1.4 Close Incident — RCA Gate Check Flow

```
Workshop Manager        Frontend             Backend (validate)      RCA Record
      │                    │                      │                     │
      │  Click "Close IR"  │                      │                     │
      ├──────────────────► │                      │                     │
      │                    │  POST close_incident │                     │
      │                    ├─────────────────────►│                     │
      │                    │                      │ get IR data          │
      │                    │                      │ priority = P1/P2?    │
      │                    │                      │ → YES                │
      │                    │                      │                     │
      │                    │                      │  get RCA Record      │
      │                    │                      ├────────────────────►│
      │                    │                      │◄────────────────────┤
      │                    │                      │  status = In Progress│
      │                    │                      │  (NOT Completed)     │
      │                    │                      │                     │
      │                    │                      │  throw ValidationError│
      │                    │◄─────────────────────┤  IR-004              │
      │                    │ 422 + error message  │                     │
      │◄───────────────────┤                      │                     │
      │  "Không thể đóng   │                      │                     │
      │   sự cố P1/P2 khi  │                      │                     │
      │   RCA chưa hoàn    │                      │                     │
      │   thành"           │                      │                     │
      │                    │                      │                     │
      │  [Complete RCA]    │                      │                     │
      ├──────────────────► │                      │                     │
      │                    │  POST submit RCA     │                     │
      │                    ├─────────────────────────────────────────► │
      │                    │◄───────────────────────────────────────── │
      │                    │  RCA status = Completed                    │
      │                    │                      │                     │
      │  [Close IR again]  │                      │                     │
      ├──────────────────► │                      │                     │
      │                    │  POST close_incident │                     │
      │                    ├─────────────────────►│                     │
      │                    │                      │  RCA = Completed ✅  │
      │                    │                      │  Close allowed       │
      │                    │                      │  status = Closed     │
      │                    │◄─────────────────────┤  create Lifecycle    │
      │                    │  200 OK              │  Event               │
      │◄───────────────────┤                      │                     │
      │  IR Closed         │                      │                     │
```

---

## 2. Endpoints Table

| Method | Endpoint | Actor | Mô tả |
|---|---|---|---|
| `POST` | `assetcore.api.imm12.create_incident` | Reporting User | Tạo Incident Report mới |
| `GET` | `assetcore.api.imm12.get_incident` | All | Lấy chi tiết một IR |
| `GET` | `assetcore.api.imm12.get_incident_list` | All | Danh sách IR với filters |
| `POST` | `assetcore.api.imm12.acknowledge_incident` | Workshop Manager | Tiếp nhận IR, set priority, start SLA |
| `POST` | `assetcore.api.imm12.link_repair_wo` | Workshop Manager | Link Asset Repair WO vào IR |
| `POST` | `assetcore.api.imm12.resolve_incident` | KTV HTM / Workshop Manager | Đánh dấu IR Resolved |
| `POST` | `assetcore.api.imm12.close_incident` | Workshop Manager / PTP | Đóng IR (sau RCA nếu cần) |
| `POST` | `assetcore.api.imm12.cancel_incident` | Workshop Manager | Huỷ IR (false alarm) |
| `POST` | `assetcore.api.imm12.create_rca` | Workshop Manager | Tạo RCA Record thủ công |
| `GET` | `assetcore.api.imm12.get_rca` | All | Chi tiết một RCA Record |
| `POST` | `assetcore.api.imm12.submit_rca` | KTV Senior / Workshop | Submit RCA đã hoàn thành |
| `GET` | `assetcore.api.imm12.get_sla_dashboard` | PTP / Workshop Manager | KPI dashboard SLA |
| `GET` | `assetcore.api.imm12.get_chronic_failures` | Workshop Manager / PTP | Danh sách chronic failures |
| `GET` | `assetcore.api.imm12.get_asset_incident_history` | All | Lịch sử IR của một asset |
| `GET` | `assetcore.api.imm12.get_sla_compliance_log` | PTP / Audit | Nhật ký SLA breach |

---

## 3. JSON Payloads

### 3.1 `create_incident` — Request

```json
{
  "asset": "ACC-ASS-2026-00012",
  "fault_code": "VENT_ALARM_HIGH",
  "fault_description": "Máy thở báo alarm liên tục P_HIGH, áp suất đường thở vượt ngưỡng 40 cmH2O, bệnh nhân đang thở máy",
  "clinical_impact": "Bệnh nhân 62 tuổi sau phẫu thuật tim đang phụ thuộc hoàn toàn vào máy thở. Đã gọi bác sĩ trực và chuẩn bị bóng ambu",
  "workaround_applied": true,
  "attachments": []
}
```

### 3.1 `create_incident` — Response (Success)

```json
{
  "success": true,
  "data": {
    "name": "IR-2026-00042",
    "asset": "ACC-ASS-2026-00012",
    "asset_name": "Máy thở Drager Evita 800",
    "department": "ICU — Hồi sức tích cực",
    "location": "Phòng 302, Tầng 3",
    "fault_code": "VENT_ALARM_HIGH",
    "status": "New",
    "sla_status": "On Track",
    "created_at": "2026-04-17T08:12:00+07:00",
    "priority": null,
    "sla_response_hours": null,
    "sla_resolution_hours": null,
    "message": "Sự cố đã được ghi nhận. Workshop sẽ tiếp nhận trong thời gian sớm nhất."
  }
}
```

---

### 3.2 `acknowledge_incident` — Request

```json
{
  "name": "IR-2026-00042",
  "priority": "P1 Critical",
  "assigned_to": "ktv.nguyen@hospital.vn",
  "notes": "KTV Nguyễn đang di chuyển đến ICU"
}
```

### 3.2 `acknowledge_incident` — Response

```json
{
  "success": true,
  "data": {
    "name": "IR-2026-00042",
    "status": "Acknowledged",
    "priority": "P1 Critical",
    "response_at": "2026-04-17T08:35:00+07:00",
    "response_minutes": 23,
    "sla_response_breached": false,
    "sla_status": "On Track",
    "sla_resolution_deadline": "2026-04-17T12:12:00+07:00",
    "sla_resolution_hours": 4.0,
    "lifecycle_event": "ALE-2026-00089"
  }
}
```

---

### 3.3 `link_repair_wo` — Request

```json
{
  "incident_report": "IR-2026-00042",
  "repair_wo": "AR-2026-00089"
}
```

### 3.3 `link_repair_wo` — Response

```json
{
  "success": true,
  "data": {
    "incident_report": "IR-2026-00042",
    "repair_wo": "AR-2026-00089",
    "status": "In Progress",
    "lifecycle_event": "ALE-2026-00090"
  }
}
```

---

### 3.4 `resolve_incident` — Request

```json
{
  "name": "IR-2026-00042",
  "resolution_notes": "Đã thay thế pressure sensor và calibrate lại. Máy thở hoạt động bình thường. Kiểm tra 30 phút không có alarm."
}
```

### 3.4 `resolve_incident` — Response

```json
{
  "success": true,
  "data": {
    "name": "IR-2026-00042",
    "status": "Resolved",
    "resolved_at": "2026-04-17T11:45:00+07:00",
    "resolution_minutes": 213,
    "sla_resolution_breached": false,
    "sla_status": "On Track",
    "rca_required": true,
    "rca_record": "RCA-2026-00012",
    "rca_status": "RCA Required",
    "rca_due_date": "2026-04-24",
    "lifecycle_event": "ALE-2026-00095"
  }
}
```

---

### 3.5 `close_incident` — Request

```json
{
  "name": "IR-2026-00042"
}
```

### 3.5 `close_incident` — Response (Success — RCA Completed)

```json
{
  "success": true,
  "data": {
    "name": "IR-2026-00042",
    "status": "Closed",
    "closed_at": "2026-04-19T10:00:00+07:00",
    "sla_response_breached": false,
    "sla_resolution_breached": false,
    "rca_record": "RCA-2026-00012",
    "lifecycle_event": "ALE-2026-00112"
  }
}
```

### 3.5 `close_incident` — Response (Blocked — RCA not completed)

```json
{
  "success": false,
  "error": "Không thể đóng sự cố P1/P2 khi RCA chưa hoàn thành. Vui lòng hoàn thành RCA trước",
  "code": "IR-004",
  "data": {
    "incident_report": "IR-2026-00042",
    "rca_record": "RCA-2026-00012",
    "rca_status": "RCA In Progress"
  }
}
```

---

### 3.6 `create_rca` — Request

```json
{
  "incident_report": "IR-2026-00042",
  "asset": "ACC-ASS-2026-00012",
  "fault_code": "VENT_ALARM_HIGH",
  "trigger_type": "P1 Incident",
  "assigned_to": "ktv.senior@hospital.vn"
}
```

### 3.6 `create_rca` — Response

```json
{
  "success": true,
  "data": {
    "name": "RCA-2026-00012",
    "asset": "ACC-ASS-2026-00012",
    "incident_report": "IR-2026-00042",
    "status": "RCA Required",
    "due_date": "2026-04-24",
    "assigned_to": "ktv.senior@hospital.vn"
  }
}
```

---

### 3.7 `get_sla_dashboard` — Response

```json
{
  "success": true,
  "data": {
    "period": {
      "year": 2026,
      "month": 4,
      "label": "Tháng 04/2026"
    },
    "summary": {
      "total_incidents": 67,
      "total_breaches": 4,
      "overall_compliance_pct": 94.0,
      "chronic_detected": 2,
      "rca_completion_rate_pct": 85.7
    },
    "by_priority": {
      "P1 Critical": {
        "total": 5,
        "breached_response": 0,
        "breached_resolution": 0,
        "compliance_pct": 100.0,
        "mtta_minutes": 18.4,
        "mttr_hours": 3.2
      },
      "P2 High": {
        "total": 8,
        "breached_response": 0,
        "breached_resolution": 1,
        "compliance_pct": 87.5,
        "mtta_minutes": 102.0,
        "mttr_hours": 7.8
      },
      "P3 Medium": {
        "total": 52,
        "breached_response": 2,
        "breached_resolution": 3,
        "compliance_pct": 94.2,
        "mtta_minutes": 195.0,
        "mttr_hours": 19.3
      },
      "P4 Low": {
        "total": 2,
        "breached_response": 0,
        "breached_resolution": 0,
        "compliance_pct": 100.0,
        "mtta_minutes": 360.0,
        "mttr_hours": 24.5
      }
    },
    "open_incidents": [
      {
        "name": "IR-2026-00052",
        "asset": "ACC-ASS-2026-00031",
        "asset_name": "Máy siêu âm GE Vivid E10",
        "priority": "P2 High",
        "status": "In Progress",
        "sla_status": "At Risk",
        "created_at": "2026-04-17T06:30:00+07:00",
        "sla_resolution_deadline": "2026-04-17T14:30:00+07:00",
        "seconds_remaining": 4800
      }
    ],
    "breach_trend_6months": [
      { "month": "2025-11", "total": 3, "breaches": 0 },
      { "month": "2025-12", "total": 5, "breaches": 1 },
      { "month": "2026-01", "total": 4, "breaches": 0 },
      { "month": "2026-02", "total": 7, "breaches": 2 },
      { "month": "2026-03", "total": 6, "breaches": 1 },
      { "month": "2026-04", "total": 4, "breaches": 0 }
    ]
  }
}
```

---

### 3.8 `get_chronic_failures` — Response

```json
{
  "success": true,
  "data": [
    {
      "asset": "ACC-ASS-2026-00042",
      "asset_name": "Máy siêu âm GE Vivid E9",
      "department": "Tim mạch",
      "fault_code": "PROBE_DISCONNECT",
      "fault_label": "Đầu dò siêu âm mất kết nối",
      "incident_count": 3,
      "first_incident": "2026-02-15",
      "last_incident": "2026-04-17",
      "rca_record": "RCA-2026-00007",
      "rca_status": "RCA Required",
      "rca_due_date": "2026-05-01",
      "related_incidents": [
        "IR-2026-00010",
        "IR-2026-00031",
        "IR-2026-00055"
      ]
    }
  ]
}
```

---

### 3.9 `get_incident_list` — Response

```json
{
  "success": true,
  "data": {
    "page": 1,
    "page_size": 20,
    "total": 7,
    "items": [
      {
        "name": "IR-2026-00042",
        "asset": "ACC-ASS-2026-00012",
        "asset_name": "Máy thở Drager Evita 800",
        "department": "ICU",
        "fault_code": "VENT_ALARM_HIGH",
        "priority": "P1 Critical",
        "status": "In Progress",
        "sla_status": "On Track",
        "created_at": "2026-04-17T08:12:00+07:00",
        "response_at": "2026-04-17T08:35:00+07:00",
        "resolved_at": null,
        "sla_response_breached": false,
        "sla_resolution_breached": false,
        "is_chronic": false,
        "repair_wo": "AR-2026-00089",
        "assigned_to": "ktv.nguyen@hospital.vn"
      }
    ]
  }
}
```

---

## 4. Error Code Table

| Code | HTTP Status | Tên lỗi | Message (Tiếng Việt) | Ghi chú |
|---|---|---|---|---|
| `IR-001` | 400 | `IncidentAssetNotFound` | "Thiết bị không tồn tại trong hệ thống" | asset link không hợp lệ |
| `IR-002` | 400 | `InvalidPriority` | "Mức độ ưu tiên không hợp lệ. Chọn P1, P2, P3 hoặc P4" | priority ngoài danh sách cho phép |
| `IR-003` | 409 | `AlreadyAcknowledged` | "Sự cố này đã được tiếp nhận trước đó" | Acknowledge 2 lần |
| `IR-004` | 422 | `CannotCloseWithoutRCA` | "Không thể đóng sự cố P1/P2 khi RCA chưa hoàn thành. Vui lòng hoàn thành RCA trước" | BR-12-04 |
| `IR-005` | 422 | `RepairWONotCompleted` | "Không thể đóng sự cố khi Work Order sửa chữa chưa hoàn thành" | repair_wo.status != Completed |
| `IR-006` | 400 | `P1ClinicalImpactMissing` | "Sự cố P1 bắt buộc phải mô tả tác động lâm sàng đến bệnh nhân" | clinical_impact trống khi P1 |
| `IR-007` | 404 | `IncidentNotFound` | "Không tìm thấy sự cố: {name}" | IR không tồn tại |
| `IR-008` | 403 | `PermissionDenied` | "Bạn không có quyền thực hiện thao tác này" | Role không đủ quyền |
| `IR-009` | 409 | `CannotCancelActiveRepair` | "Không thể hủy sự cố khi Work Order sửa chữa đang In Progress" | Cancel khi WO active |
| `IR-010` | 422 | `InvalidStatusTransition` | "Chuyển trạng thái không hợp lệ: {from} → {to}" | State machine violation |
| `RCA-001` | 409 | `RCAAlreadyExists` | "Đã có RCA đang mở cho sự cố này: {rca_name}" | Tránh duplicate RCA |
| `RCA-002` | 400 | `RCAIncompleteSubmit` | "Phân tích RCA chưa đầy đủ. Cần điền nguyên nhân gốc và hành động khắc phục" | Validate trước Submit |
| `RCA-003` | 404 | `RCANotFound` | "Không tìm thấy RCA Record: {name}" | RCA link invalid |
| `SLA-001` | 403 | `SLALogImmutable` | "Nhật ký SLA là bất biến và không thể thay đổi theo quy định audit trail" | BR-12-05 |
| `SLA-002` | 422 | `InvalidResolutionBeforeAcknowledge` | "Thời gian giải quyết không thể trước thời gian tiếp nhận" | resolved_at < response_at |
| `SLA-003` | 400 | `FutureTimestamp` | "Thời gian không hợp lệ — không thể đặt thời gian trong tương lai" | Prevent backdating |

---

## 5. curl Examples

### 5.1 Tạo Incident Report mới (P1)

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.create_incident" \
  -H "Content-Type: application/json" \
  -H "Authorization: token api_key:api_secret" \
  -d '{
    "asset": "ACC-ASS-2026-00012",
    "fault_code": "VENT_ALARM_HIGH",
    "fault_description": "Máy thở báo alarm P_HIGH liên tục, áp suất vượt ngưỡng 40 cmH2O",
    "clinical_impact": "Bệnh nhân phụ thuộc hoàn toàn, đã chuẩn bị bóng ambu",
    "workaround_applied": true
  }'
```

### 5.2 Acknowledge IR với Priority P1

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.acknowledge_incident" \
  -H "Content-Type: application/json" \
  -H "Authorization: token api_key:api_secret" \
  -d '{
    "name": "IR-2026-00042",
    "priority": "P1 Critical",
    "assigned_to": "ktv.nguyen@hospital.vn",
    "notes": "KTV đang di chuyển đến ICU"
  }'
```

### 5.3 Link Repair Work Order vào IR

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.link_repair_wo" \
  -H "Content-Type: application/json" \
  -H "Authorization: token api_key:api_secret" \
  -d '{
    "incident_report": "IR-2026-00042",
    "repair_wo": "AR-2026-00089"
  }'
```

### 5.4 Resolve Incident

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.resolve_incident" \
  -H "Content-Type: application/json" \
  -H "Authorization: token api_key:api_secret" \
  -d '{
    "name": "IR-2026-00042",
    "resolution_notes": "Đã thay pressure sensor, calibrate lại. Máy hoạt động bình thường."
  }'
```

### 5.5 Lấy SLA Dashboard tháng 04/2026

```bash
curl -G \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.get_sla_dashboard" \
  -H "Authorization: token api_key:api_secret" \
  --data-urlencode "year=2026" \
  --data-urlencode "month=4"
```

### 5.6 Lấy danh sách IR đang mở với filter

```bash
curl -G \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.get_incident_list" \
  -H "Authorization: token api_key:api_secret" \
  --data-urlencode 'filters={"status": ["in", ["New","Acknowledged","In Progress"]], "priority": "P1 Critical"}' \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=10"
```

### 5.7 Lấy Chronic Failures hiện tại

```bash
curl -G \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.get_chronic_failures" \
  -H "Authorization: token api_key:api_secret"
```

### 5.8 Tạo RCA Record thủ công

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.create_rca" \
  -H "Content-Type: application/json" \
  -H "Authorization: token api_key:api_secret" \
  -d '{
    "incident_report": "IR-2026-00042",
    "asset": "ACC-ASS-2026-00012",
    "fault_code": "VENT_ALARM_HIGH",
    "trigger_type": "P1 Incident",
    "assigned_to": "ktv.senior@hospital.vn"
  }'
```

### 5.9 Lấy lịch sử IR của một Asset

```bash
curl -G \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.get_asset_incident_history" \
  -H "Authorization: token api_key:api_secret" \
  --data-urlencode "asset=ACC-ASS-2026-00012" \
  --data-urlencode "limit=20"
```

### 5.10 Close Incident (sau khi RCA complete)

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.close_incident" \
  -H "Content-Type: application/json" \
  -H "Authorization: token api_key:api_secret" \
  -d '{
    "name": "IR-2026-00042"
  }'
```
