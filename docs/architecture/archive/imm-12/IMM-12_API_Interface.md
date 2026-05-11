# IMM-12 — API Interface Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | **DRAFT** — endpoints đề xuất, ⚠️ Pending implementation (`api/imm12.py` chưa tồn tại) |
| Base URL | `/api/method/assetcore.api.imm12` |
| Tác giả | AssetCore Team |

> **Lưu ý quan trọng:** IMM-12 v1 dùng lại endpoints CAPA từ IMM-00 (`assetcore.api.imm00.create_capa`, `close_capa`, `list_capa`). IMM-12 chỉ bổ sung endpoints riêng cho **Incident** và **RCA** (đề xuất ở Section 3.B).

---

## 1. Authentication

Mọi endpoint yêu cầu xác thực, hai phương thức:

```http
# API Token (server-to-server)
Authorization: token <api_key>:<api_secret>

# Session cookie (Frappe UI / SPA)
Cookie: sid=<session_id>
```

- Thiếu/sai credential → HTTP 401
- User không có Role hợp lệ → HTTP 403

---

## 2. Response Format

Theo convention IMM-00 — tất cả response gói trong `message`:

**Success (HTTP 200):**

```json
{
  "message": {
    "success": true,
    "data": { /* payload */ }
  }
}
```

**Error (HTTP 400/401/403/404/409/422/500):**

```json
{
  "message": {
    "success": false,
    "error": "Thông báo lỗi tiếng Việt",
    "code": 422
  }
}
```

Helper: `assetcore/utils/response.py` — `_ok(data)` / `_err(msg, code)`.

---

## 3. Endpoints

### 3.A — CAPA endpoints (REUSE từ IMM-00, ✅ LIVE)

| Method | Endpoint | Actor | Mô tả | Trạng thái |
|---|---|---|---|---|
| `POST` | `assetcore.api.imm00.create_capa` | Workshop Lead, QA Officer | Tạo CAPA Record (Draft) | ✅ LIVE |
| `POST` | `assetcore.api.imm00.update_capa` | Assigned user, QA Officer | Cập nhật CAPA fields | ✅ LIVE |
| `POST` | `assetcore.api.imm00.submit_capa` | QA Officer | Submit CAPA (validate BR-00-08) | ✅ LIVE |
| `POST` | `assetcore.api.imm00.close_capa` | QA Officer | Đóng CAPA với verification | ✅ LIVE |
| `GET`  | `assetcore.api.imm00.list_capa` | All | List CAPA với filters/pagination | ✅ LIVE |
| `GET`  | `assetcore.api.imm00.get_capa` | All | Chi tiết một CAPA | ✅ LIVE |

→ Spec đầy đủ xem `docs/imm-00/IMM-00_API_Interface.md` §3.7 (CAPA endpoints).

### 3.B — Incident & RCA endpoints (RIÊNG IMM-12, ⚠️ Pending)

| Method | Endpoint | Actor | Mô tả | Trạng thái |
|---|---|---|---|---|
| `POST` | `assetcore.api.imm12.report_incident` | Reporting User, Workshop Lead | Tạo Incident Report mới | ⚠️ Pending |
| `GET`  | `assetcore.api.imm12.get_incident` | All (per perm) | Chi tiết một IR | ⚠️ Pending |
| `GET`  | `assetcore.api.imm12.list_incidents` | All | Danh sách IR với filters | ⚠️ Pending |
| `POST` | `assetcore.api.imm12.acknowledge_incident` | Workshop Lead | Acknowledge IR, set assigned_to | ⚠️ Pending |
| `POST` | `assetcore.api.imm12.resolve_incident` | Workshop Lead, KTV | Đánh dấu Resolved → kích hoạt RCA nếu cần | ⚠️ Pending |
| `POST` | `assetcore.api.imm12.close_incident` | Workshop Lead, QA Officer | Đóng IR (validate RCA Completed) | ⚠️ Pending |
| `POST` | `assetcore.api.imm12.cancel_incident` | Workshop Lead | Huỷ IR (false alarm), bắt buộc lý do | ⚠️ Pending |
| `POST` | `assetcore.api.imm12.create_rca` | Workshop Lead, QA Officer | Tạo RCA Record thủ công | ⚠️ Pending |
| `GET`  | `assetcore.api.imm12.get_rca` | All | Chi tiết RCA Record | ⚠️ Pending |
| `POST` | `assetcore.api.imm12.submit_rca` | Workshop Lead, QA Officer | Submit RCA → auto gọi `imm00.create_capa()` | ⚠️ Pending |
| `GET`  | `assetcore.api.imm12.get_chronic_failures` | Workshop Lead, QA Officer | Danh sách asset chronic | ⚠️ Pending |
| `GET`  | `assetcore.api.imm12.get_asset_incident_history` | All | Lịch sử IR theo asset | ⚠️ Pending |
| `GET`  | `assetcore.api.imm12.get_dashboard` | Workshop Lead, Ops Manager, QA | KPI dashboard | ⚠️ Pending |
| `POST` | `assetcore.api.imm12.trigger_chronic_detection` | System Admin | Manual trigger scheduler (admin only) | ⚠️ Pending |

---

### 3.B.1 `report_incident` — POST

**Request:**

```json
{
  "asset": "ACC-ASSET-2026-00012",
  "fault_code": "VENT_ALARM_HIGH",
  "fault_description": "Máy thở báo alarm P_HIGH liên tục, áp suất vượt 40 cmH2O",
  "severity": "Critical",
  "clinical_impact": "Bệnh nhân phụ thuộc, đã chuẩn bị bóng ambu",
  "workaround_applied": true,
  "attachments": []
}
```

**Response (Success):**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "IR-2026-0042",
      "asset": "ACC-ASSET-2026-00012",
      "asset_name": "Máy thở Drager Evita 800",
      "department": "ICU",
      "severity": "Critical",
      "status": "Open",
      "reported_at": "2026-04-18T08:12:00+07:00",
      "asset_lifecycle_status": "Out of Service",
      "lifecycle_event": "ALE-2026-0089",
      "audit_trail": "IMM-AUD-2026-0001234",
      "message": "Sự cố Critical đã ghi nhận. Asset đã chuyển sang Out of Service."
    }
  }
}
```

**Service implementation note:** wraps `imm00.create_lifecycle_event()`, `imm00.transition_asset_status()`, `imm00.log_audit_event()`.

---

### 3.B.2 `acknowledge_incident` — POST

**Request:**

```json
{
  "name": "IR-2026-0042",
  "assigned_to": "ktv.nguyen@hospital.vn",
  "notes": "KTV đang di chuyển đến ICU"
}
```

**Response:**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "IR-2026-0042",
      "status": "Acknowledged",
      "acknowledged_at": "2026-04-18T08:35:00+07:00",
      "assigned_to": "ktv.nguyen@hospital.vn",
      "lifecycle_event": "ALE-2026-0090"
    }
  }
}
```

---

### 3.B.3 `resolve_incident` — POST

**Request:**

```json
{
  "name": "IR-2026-0042",
  "resolution_notes": "Đã thay pressure sensor và calibrate lại."
}
```

**Response:**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "IR-2026-0042",
      "status": "RCA Required",
      "resolved_at": "2026-04-18T11:45:00+07:00",
      "rca_required": true,
      "rca_record": "RCA-2026-0012",
      "rca_due_date": "2026-04-25",
      "lifecycle_event": "ALE-2026-0095"
    }
  }
}
```

---

### 3.B.4 `close_incident` — POST

**Request:** `{ "name": "IR-2026-0042" }`

**Response (Success):**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "IR-2026-0042",
      "status": "Closed",
      "closed_at": "2026-04-21T10:00:00+07:00",
      "rca_record": "RCA-2026-0012",
      "linked_capa": "CAPA-2026-0023"
    }
  }
}
```

**Response (Blocked — BR-12-02):**

```json
{
  "message": {
    "success": false,
    "error": "Không thể đóng sự cố Major/Critical khi RCA chưa hoàn thành",
    "code": 422,
    "data": {
      "incident_report": "IR-2026-0042",
      "rca_record": "RCA-2026-0012",
      "rca_status": "RCA In Progress"
    }
  }
}
```

---

### 3.B.5 `submit_rca` — POST (orchestration: tạo CAPA tự động)

**Request:**

```json
{
  "name": "RCA-2026-0012",
  "rca_method": "5Why",
  "root_cause": "Pressure sensor degraded do nhiệt độ phòng vượt 28°C kéo dài",
  "contributing_factors": "HVAC ICU không ổn định trong 3 tháng qua",
  "five_why_steps": [
    {"why": "1", "question": "Tại sao alarm?", "answer": "Sensor sai số"},
    {"why": "2", "question": "Tại sao sensor sai số?", "answer": "Drift do nhiệt độ"},
    {"why": "3", "question": "Tại sao nhiệt độ cao?", "answer": "HVAC không ổn định"},
    {"why": "4", "question": "Tại sao HVAC không ổn?", "answer": "Maintenance HVAC trễ"},
    {"why": "5", "question": "Tại sao maintenance trễ?", "answer": "Không có schedule HVAC trong CMMS"}
  ]
}
```

**Response:**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "RCA-2026-0012",
      "status": "Completed",
      "completed_date": "2026-04-22",
      "linked_capa": "CAPA-2026-0023",
      "capa_due_date": "2026-05-22",
      "audit_trail": "IMM-AUD-2026-0001245"
    }
  }
}
```

**Implementation:** internally calls `imm00.create_capa(asset, "RCA Record", rca_name, severity_to_fault_severity(rca.severity), due_days=30)`.

---

### 3.B.6 `get_chronic_failures` — GET

**Response:**

```json
{
  "message": {
    "success": true,
    "data": [
      {
        "asset": "ACC-ASSET-2026-00042",
        "asset_name": "Máy siêu âm GE Vivid E9",
        "department": "Tim mạch",
        "fault_code": "PROBE_DISCONNECT",
        "incident_count": 3,
        "first_incident": "2026-02-15",
        "last_incident": "2026-04-17",
        "rca_record": "RCA-2026-0007",
        "rca_status": "RCA Required",
        "rca_due_date": "2026-05-01",
        "related_incidents": ["IR-2026-0010", "IR-2026-0031", "IR-2026-0055"]
      }
    ]
  }
}
```

---

## 4. Error Codes

| Code | HTTP | Tên | Message (VI) | BR liên quan |
|---|---|---|---|---|
| `IR-001` | 400 | `IncidentAssetNotFound` | "Thiết bị không tồn tại trong hệ thống" | VR-12-01 |
| `IR-002` | 400 | `InvalidSeverity` | "Mức độ không hợp lệ. Chọn Minor / Major / Critical" | — |
| `IR-003` | 409 | `AlreadyAcknowledged` | "Sự cố này đã được tiếp nhận trước đó" | — |
| `IR-004` | 422 | `CannotCloseWithoutRCA` | "Không thể đóng sự cố Major/Critical khi RCA chưa hoàn thành" | BR-12-02 |
| `IR-005` | 422 | `RepairWONotCompleted` | "Không thể đóng sự cố khi Work Order sửa chữa chưa hoàn thành" | — |
| `IR-006` | 400 | `CriticalClinicalImpactMissing` | "Sự cố Critical bắt buộc mô tả tác động lâm sàng" | BR-12-01 |
| `IR-007` | 404 | `IncidentNotFound` | "Không tìm thấy sự cố: {name}" | — |
| `IR-008` | 403 | `PermissionDenied` | "Bạn không có quyền thực hiện thao tác này" | — |
| `IR-009` | 422 | `InvalidStatusTransition` | "Chuyển trạng thái không hợp lệ: {from} → {to}" | — |
| `RCA-001` | 409 | `RCAAlreadyExists` | "Đã có RCA đang mở cho sự cố này: {rca_name}" | — |
| `RCA-002` | 400 | `RCAIncompleteSubmit` | "Phân tích RCA chưa đầy đủ. Cần điền root_cause và rca_method" | BR-12-07 |
| `RCA-003` | 404 | `RCANotFound` | "Không tìm thấy RCA Record: {name}" | — |
| `CAPA-001` | 422 | `CAPAIncompleteSubmit` | "CAPA cần đầy đủ root_cause + corrective_action + preventive_action" | BR-00-08 |
| `CAPA-002` | 403 | `CAPACloseRoleRequired` | "Chỉ QA Officer có quyền đóng CAPA" | — |
| `AUD-001` | 403 | `AuditTrailImmutable` | "Audit trail là bất biến — không thể xóa hoặc sửa" | BR-00-03 |

---

## 5. Webhook Events (⚠️ Pending — đề xuất Sprint 12.5)

| Event | Trigger | Payload | Subscribers (đề xuất) |
|---|---|---|---|
| `incident.created` | `report_incident` success | `{name, asset, severity, reported_by}` | IMM-15 (Vigilance), notification svc |
| `incident.critical_reported` | severity = Critical | `{name, asset, clinical_impact}` | Email BGĐ, SMS gateway (future) |
| `rca.completed` | `submit_rca` success | `{rca, asset, root_cause, capa_created}` | QA dashboard |
| `capa.created` | via `imm00.create_capa()` | `{capa, source_doctype, source_name}` | QA Officer assignment |
| `capa.closed` | via `imm00.close_capa()` | `{capa, evidence}` | Audit log |
| `chronic.detected` | `detect_chronic_failures` | `{asset, fault_code, incident_count, rca}` | Workshop Lead, Risk Register (IMM-13) |

---

## 6. curl Examples

### 6.1 Tạo Incident Critical (⚠️ Pending endpoint)

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm12.report_incident" \
  -H "Content-Type: application/json" \
  -H "Authorization: token api_key:api_secret" \
  -d '{
    "asset": "ACC-ASSET-2026-00012",
    "fault_code": "VENT_ALARM_HIGH",
    "fault_description": "Máy thở alarm P_HIGH liên tục",
    "severity": "Critical",
    "clinical_impact": "Bệnh nhân phụ thuộc, đã chuẩn bị bóng ambu"
  }'
```

### 6.2 Tạo CAPA (✅ LIVE — qua IMM-00)

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm00.create_capa" \
  -H "Authorization: token api_key:api_secret" \
  -d '{
    "asset": "ACC-ASSET-2026-00012",
    "source_doctype": "RCA Record",
    "source_name": "RCA-2026-0012",
    "fault_severity": "Major",
    "due_days": 30
  }'
```

### 6.3 Close CAPA (✅ LIVE — qua IMM-00)

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm00.close_capa" \
  -H "Authorization: token api_key:api_secret" \
  -d '{
    "capa_name": "CAPA-2026-0023",
    "corrective_action": "Thay sensor + calibrate",
    "preventive_action": "Rút ngắn PM interval xuống 3 tháng",
    "evidence": ["calibration_cert.pdf"]
  }'
```

---

## 7. Implementation Notes

### 7.1 Phân chia trách nhiệm

| Nhóm endpoint | File implementation | Trạng thái |
|---|---|---|
| CAPA CRUD | `assetcore/api/imm00.py` | ✅ LIVE |
| Incident CRUD + workflow | `assetcore/api/imm12.py` | ⚠️ Pending |
| RCA CRUD + Submit (orchestration) | `assetcore/api/imm12.py` | ⚠️ Pending |
| Chronic detection trigger | `assetcore/api/imm12.py` (admin only) | ⚠️ Pending |

### 7.2 Service layer rule

- API endpoint **không chứa business logic** — chỉ parse param, call service, format response
- Mọi state transition gọi `services/imm12.py` → which calls `services/imm00.py`
- KHÔNG gọi trực tiếp `frappe.get_doc().save()` từ API layer

### 7.3 Idempotency

- `report_incident`: KHÔNG idempotent (mỗi call tạo IR mới) — client phải dedupe
- `acknowledge_incident`, `resolve_incident`, `close_incident`: idempotent — repeat call → return current state
- `submit_rca`: idempotent — repeat call sau Completed → return existing CAPA

### 7.4 Permission enforcement

- Endpoint nhận `@frappe.whitelist()` + role check qua `assetcore/permission.py`
- DocType-level perm fixtures (reuse từ IMM-00 `fixtures/imm_roles.json` + extend cho RCA Record)

### 7.5 Audit trail

- Mọi mutation endpoint phải gọi `imm00.log_audit_event()` ở cuối service layer
- Audit entry phải bao gồm: `actor`, `event_type`, `from_status`, `to_status`, `change_summary`, `ref_doctype`, `ref_name`
