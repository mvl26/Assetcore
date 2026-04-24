# IMM-13 — Ngừng sử dụng và Điều chuyển (API Interface)

| Thuộc tính    | Giá trị                                              |
|---------------|------------------------------------------------------|
| Module        | IMM-13 — API Interface                               |
| Phiên bản     | 2.0.0                                                |
| Ngày cập nhật | 2026-04-24                                           |
| Base URL      | `/api/method/assetcore.api.imm13.`                   |
| Auth          | Frappe session cookie hoặc API Key/Secret header     |
| Spec Format   | OpenAPI 3.0                                          |

---

## Quy ước chung

### Envelope Response

```json
// Success
{ "success": true, "data": { ... } }

// Error
{ "success": false, "error": "Mô tả lỗi tiếng Việt", "code": "ERROR_CODE" }
```

### HTTP Status Codes

| Code | Ý nghĩa |
|---|---|
| 200 | Thành công |
| 400 | Validation error / business rule violation |
| 403 | Không đủ quyền |
| 404 | Không tìm thấy record |
| 409 | Conflict (e.g. duplicate DR) |
| 500 | Internal server error |

### Error Codes chuẩn

| Code | Mô tả |
|---|---|
| `ACTIVE_WO_EXISTS` | Asset còn Work Order mở (BR-13-01) |
| `DUPLICATE_DR` | Đã có DR active cho asset (BR-13-02) |
| `BIO_HAZARD_CLEARANCE_MISSING` | Thiếu bio_hazard_clearance (BR-13-03) |
| `REGULATORY_DOC_MISSING` | Thiếu regulatory_clearance_doc (BR-13-04) |
| `DATA_DESTRUCTION_NOT_CONFIRMED` | Chưa xác nhận xóa dữ liệu (BR-13-05) |
| `RESIDUAL_RISK_MISSING` | Chưa đánh giá residual risk (BR-13-06) |
| `VP_APPROVAL_REQUIRED` | Cần phê duyệt VP Block2 (BR-13-08) |
| `INVALID_LOCATION` | Location điều chuyển không hợp lệ (BR-13-09) |
| `RECEIVING_OFFICER_MISSING` | Thiếu người tiếp nhận (BR-13-10) |
| `REJECTION_REASON_MISSING` | Thiếu lý do từ chối (BR-13-11) |
| `ASSET_NOT_FOUND` | Không tìm thấy AC Asset |
| `DR_NOT_FOUND` | Không tìm thấy Decommission Request |
| `INVALID_STATE_TRANSITION` | Chuyển trạng thái không hợp lệ |
| `PERMISSION_DENIED` | Không có quyền thực hiện action này |

---

## 1. create_suspension_request

**POST** `/api/method/assetcore.api.imm13.create_suspension_request`

Tạo phiếu yêu cầu ngừng sử dụng / điều chuyển mới.

**Auth:** IMM HTM Manager, IMM CMMS Admin

**Request Body:**

```json
{
  "asset": "ECG-2019-003",
  "suspension_reason": "End of Life",
  "reason_details": "Máy ECG 7 năm, mainboard hỏng, không còn phụ tùng thay thế từ nhà sản xuất Nihon Kohden.",
  "condition_at_suspension": "Non-functional",
  "biological_hazard": false,
  "data_destruction_required": false,
  "regulatory_clearance_required": false,
  "initiated_from_module": "IMM-12",
  "initiated_from_record": "WO-CM-26-04-00089"
}
```

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `asset` | string | Y | Tên AC Asset |
| `suspension_reason` | enum | Y | End of Life / Beyond Economic Repair / Regulatory Non-Compliance / Catastrophic Failure / Technology Obsolescence / Relocation / Donated / Other |
| `reason_details` | string | Y | Mô tả chi tiết |
| `condition_at_suspension` | enum | N | Poor / Non-functional / Partially Functional / Functional but Obsolete |
| `biological_hazard` | boolean | N | Default: false |
| `bio_hazard_clearance` | string | Cond. | Required nếu `biological_hazard=true` |
| `data_destruction_required` | boolean | N | Default: false |
| `regulatory_clearance_required` | boolean | N | Default: false |
| `initiated_from_module` | string | N | e.g. "IMM-12" |
| `initiated_from_record` | string | N | WO name nếu triggered từ WO |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "asset": "ECG-2019-003",
    "asset_name": "ECG 12-lead Nihon Kohden ECG-1550",
    "workflow_state": "Draft",
    "suspension_reason": "End of Life",
    "creation": "2026-04-24 08:30:00",
    "url": "/imm13/suspensions/DR-26-04-00001"
  }
}
```

**Response 400:**

```json
{
  "success": false,
  "error": "Không thể ngừng sử dụng: Thiết bị ECG-2019-003 còn 1 Work Order đang mở (WO-CM-26-00123). Đóng tất cả Work Order trước.",
  "code": "ACTIVE_WO_EXISTS",
  "data": {
    "open_work_orders": ["WO-CM-26-00123"]
  }
}
```

**Response 409:**

```json
{
  "success": false,
  "error": "Đã có phiếu DR-26-03-00008 đang xử lý cho thiết bị ECG-2019-003.",
  "code": "DUPLICATE_DR",
  "data": { "existing_dr": "DR-26-03-00008" }
}
```

---

## 2. get_suspension_request

**GET** `/api/method/assetcore.api.imm13.get_suspension_request`

Lấy chi tiết đầy đủ một phiếu DR.

**Auth:** Tất cả roles có quyền Read

**Query Params:**

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `name` | string | Y | DR name (e.g. DR-26-04-00001) |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "asset": "ECG-2019-003",
    "asset_name": "ECG 12-lead Nihon Kohden ECG-1550",
    "asset_model": "ECG-1550",
    "asset_location": "Khoa Tim mạch",
    "asset_age_years": 7.2,
    "workflow_state": "Under Replacement Review",
    "suspension_reason": "End of Life",
    "reason_details": "Máy ECG 7 năm...",
    "condition_at_suspension": "Non-functional",
    "technical_reviewer": "biomed@benhvien.vn",
    "tech_review_date": "2026-04-22",
    "tech_review_notes": "Mainboard cháy, không còn khả năng sửa.",
    "residual_risk_level": "Low",
    "residual_risk_notes": "Không có nguồn phóng xạ hoặc rủi ro sinh học.",
    "estimated_remaining_life": 0,
    "maintenance_cost_total": 45000000,
    "current_book_value": 20000000,
    "maintenance_cost_ratio": 22.5,
    "outcome": null,
    "biological_hazard": false,
    "data_destruction_required": false,
    "regulatory_clearance_required": false,
    "approved": false,
    "suspension_checklist": [
      {
        "idx": 1,
        "task_name": "Thu hồi thiết bị từ khoa sử dụng",
        "task_category": "Physical",
        "responsible": "htm@benhvien.vn",
        "due_date": "2026-04-30",
        "completed": false
      }
    ],
    "transfer_details": [],
    "lifecycle_events": [
      {
        "event_type": "suspension_initiated",
        "timestamp": "2026-04-21 08:30:00",
        "actor": "htm@benhvien.vn",
        "from_status": "",
        "to_status": "Draft"
      }
    ],
    "creation": "2026-04-21 08:30:00",
    "modified": "2026-04-22 14:15:00"
  }
}
```

**Response 404:**

```json
{
  "success": false,
  "error": "Không tìm thấy phiếu DR-26-99-99999.",
  "code": "DR_NOT_FOUND"
}
```

---

## 3. submit_technical_review

**POST** `/api/method/assetcore.api.imm13.submit_technical_review`

Biomed Engineer hoàn thành hoặc từ chối đánh giá kỹ thuật.

**Auth:** IMM Biomed Engineer, IMM CMMS Admin

**Request Body:**

```json
{
  "name": "DR-26-04-00001",
  "reviewer": "biomed@benhvien.vn",
  "review_notes": "Mainboard cháy hoàn toàn, phụ tùng không còn supply. Không có khả năng sửa chữa.",
  "condition_assessment": "Non-functional",
  "residual_risk_level": "Low",
  "residual_risk_notes": "Thiết bị không có nguồn phóng xạ, không có nguy cơ sinh học.",
  "estimated_remaining_life": 0,
  "approved": true
}
```

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `name` | string | Y | DR name |
| `reviewer` | string | Y | Email Biomed Engineer |
| `review_notes` | string | Y | Ghi chú đánh giá |
| `residual_risk_level` | enum | Y | Low / Medium / High / Critical — BR-13-06 |
| `residual_risk_notes` | string | Y | Mô tả rủi ro |
| `condition_assessment` | enum | N | Tình trạng thiết bị |
| `estimated_remaining_life` | int | N | Tháng còn lại |
| `approved` | boolean | Y | true → hoàn thành; false → từ chối (cần rejection_reason) |
| `rejection_reason` | string | Cond. | Required khi `approved=false` — BR-13-11 |

**Transition:** 
- `approved=true`: Pending Tech Review → Under Replacement Review
- `approved=false`: Pending Tech Review → Cancelled

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "workflow_state": "Under Replacement Review",
    "message": "Đánh giá kỹ thuật hoàn thành. Phiếu đã chuyển sang giai đoạn Review thay thế."
  }
}
```

**Response 400 (thiếu residual_risk_level):**

```json
{
  "success": false,
  "error": "Lỗi BR-13-06: Bắt buộc đánh giá mức độ rủi ro còn lại (Residual Risk Level) trước khi hoàn thành đánh giá kỹ thuật.",
  "code": "RESIDUAL_RISK_MISSING"
}
```

---

## 4. submit_replacement_review

**POST** `/api/method/assetcore.api.imm13.submit_replacement_review`

HTM Manager + Finance quyết định outcome sau replacement review.

**Auth:** IMM HTM Manager, IMM CMMS Admin

**Request Body:**

```json
{
  "name": "DR-26-04-00001",
  "replacement_needed": "No",
  "current_book_value": 20000000,
  "economic_justification": "Chi phí thay thế vượt ngân sách Q2/2026. Chuyển sang Q3.",
  "outcome": "Retire",
  "outcome_notes": "Thiết bị EOL, không thay thế ngay. Trigger IMM-14 để đóng hồ sơ."
}
```

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `name` | string | Y | DR name |
| `replacement_needed` | enum | Y | Yes / No / Deferred |
| `replacement_device_model` | string | Cond. | Required khi replacement_needed=Yes |
| `replacement_estimated_cost` | number | Cond. | Required khi replacement_needed=Yes |
| `current_book_value` | number | N | Finance fill |
| `economic_justification` | string | N | Finance fill |
| `outcome` | enum | Y | Transfer / Suspend / Retire |
| `outcome_notes` | string | N | Ghi chú quyết định |
| `transfer_to_location` | string | Cond. | Required khi outcome=Transfer — BR-13-09 |
| `receiving_officer` | string | Cond. | Required khi outcome=Transfer — BR-13-10 |

**Transition:**
- `outcome=Transfer`: Under Replacement Review → Approved for Transfer
- `outcome=Suspend` hoặc `Retire`: Under Replacement Review → Pending Decommission

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "workflow_state": "Pending Decommission",
    "outcome": "Retire",
    "message": "Quyết định ngừng sử dụng đã được ghi nhận. Phiếu chờ phê duyệt VP Block2."
  }
}
```

---

## 5. approve_suspension

**POST** `/api/method/assetcore.api.imm13.approve_suspension`

VP Block2 phê duyệt việc ngừng sử dụng / retire.

**Auth:** IMM VP Block2, IMM CMMS Admin

**Request Body:**

```json
{
  "name": "DR-26-04-00001",
  "approver": "vp@benhvien.vn",
  "approval_notes": "Đã họp BGĐ ngày 23/04/2026, thống nhất ngừng sử dụng thiết bị ECG-2019-003.",
  "approved": true
}
```

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `name` | string | Y | DR name |
| `approver` | string | Y | Email VP Block2 |
| `approval_notes` | string | Y | Ghi chú phê duyệt |
| `approved` | boolean | Y | true=phê duyệt; false=từ chối (cần rejection_reason) |
| `rejection_reason` | string | Cond. | Required khi approved=false — BR-13-11 |

**Response 200 (approved=true):**

```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "approved": true,
    "approved_by": "vp@benhvien.vn",
    "approval_date": "2026-04-24",
    "message": "Phê duyệt thành công. CMMS Admin có thể submit phiếu để hoàn tất."
  }
}
```

**Response 200 (approved=false → Cancelled):**

```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "workflow_state": "Cancelled",
    "message": "Phiếu đã bị hủy. HTM Manager đã được thông báo."
  }
}
```

---

## 6. execute_transfer

**POST** `/api/method/assetcore.api.imm13.execute_transfer`

Network Manager bắt đầu và hoàn thành quá trình điều chuyển vật lý.

**Auth:** IMM Network Manager, IMM CMMS Admin

**Request Body:**

```json
{
  "name": "DR-26-04-00001",
  "action": "start",
  "transfer_date": "2026-04-25",
  "transfer_conditions": "Thiết bị trong tình trạng không hoạt động. Bao gói đủ tiêu chuẩn vận chuyển.",
  "transport_notes": "Vận chuyển bằng xe bệnh viện, đội HTM tháp tùng."
}
```

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `name` | string | Y | DR name |
| `action` | enum | Y | `start` (→ Transfer In Progress) / `complete` (→ Transferred, submit) |
| `transfer_date` | date | Cond. | Required khi action=start |
| `transfer_conditions` | string | N | Điều kiện bàn giao |
| `transport_notes` | string | N | Ghi chú vận chuyển |
| `handover_confirmed` | boolean | Cond. | Required khi action=complete |

**Response 200 (action=start):**

```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "workflow_state": "Transfer In Progress",
    "message": "Điều chuyển bắt đầu. Hoàn thành checklist và bấm Complete khi bàn giao xong."
  }
}
```

**Response 200 (action=complete):**

```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "workflow_state": "Transferred",
    "asset_new_location": "Khoa Cấp cứu",
    "asset_new_status": "Transferred",
    "message": "Điều chuyển hoàn tất. Asset đã được cập nhật vị trí mới."
  }
}
```

---

## 7. complete_suspension

**POST** `/api/method/assetcore.api.imm13.complete_suspension`

CMMS Admin submit phiếu để hoàn tất ngừng sử dụng (outcome=Suspend/Retire).

**Auth:** IMM CMMS Admin, System Manager

**Request Body:**

```json
{
  "name": "DR-26-04-00001",
  "execution_notes": "Đã thu hồi thiết bị, gắn nhãn ngừng sử dụng, lưu kho tạm B2-KT-01."
}
```

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `name` | string | Y | DR name |
| `execution_notes` | string | N | Ghi chú thực thi |

**Pre-conditions kiểm tra trước submit:**
- `approved = True` (BR-13-08)
- `data_destruction_confirmed = True` nếu `data_destruction_required = True` (BR-13-05)
- `bio_hazard_clearance` filled nếu `biological_hazard = True` (BR-13-03)

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "workflow_state": "Completed",
    "asset": "ECG-2019-003",
    "asset_new_status": "Suspended",
    "imm14_triggered": true,
    "imm14_record": "AAR-26-04-00001",
    "message": "Ngừng sử dụng hoàn tất. IMM-14 đã được khởi tạo để đóng hồ sơ tài sản."
  }
}
```

**Response 400 (data destruction chưa confirm — BR-13-05):**

```json
{
  "success": false,
  "error": "Lỗi BR-13-05: Thiết bị có dữ liệu bệnh nhân cần xóa. Phải xác nhận đã xóa dữ liệu (data_destruction_confirmed) trước khi Submit.",
  "code": "DATA_DESTRUCTION_NOT_CONFIRMED"
}
```

---

## 8. cancel_suspension_request

**POST** `/api/method/assetcore.api.imm13.cancel_suspension_request`

Hủy phiếu DR ở bất kỳ state nào trước Completed/Transferred.

**Auth:** IMM CMMS Admin, System Manager

**Request Body:**

```json
{
  "name": "DR-26-04-00001",
  "rejection_reason": "Thiết bị vừa nhận được phụ tùng từ nhà phân phối, sẽ tiến hành sửa chữa (IMM-09)."
}
```

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `name` | string | Y | DR name |
| `rejection_reason` | string | Y | Bắt buộc — BR-13-11 |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "workflow_state": "Cancelled",
    "asset_status_unchanged": true,
    "message": "Phiếu đã bị hủy. Asset ECG-2019-003 giữ nguyên trạng thái Active."
  }
}
```

---

## 9. get_suspension_list

**GET** `/api/method/assetcore.api.imm13.get_suspension_list`

Danh sách phiếu DR với filter và phân trang.

**Auth:** Tất cả roles có quyền Read

**Query Params:**

| Param | Type | Required | Default | Mô tả |
|---|---|---|---|---|
| `workflow_state` | string | N | — | Filter theo state |
| `asset` | string | N | — | Filter theo asset |
| `suspension_reason` | string | N | — | Filter theo lý do |
| `outcome` | string | N | — | Transfer / Suspend / Retire |
| `year` | int | N | Current year | Filter theo năm tạo |
| `page` | int | N | 1 | Trang hiện tại |
| `page_size` | int | N | 20 | Số record mỗi trang (max 100) |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "rows": [
      {
        "name": "DR-26-04-00001",
        "asset": "ECG-2019-003",
        "asset_name": "ECG 12-lead Nihon Kohden",
        "suspension_reason": "End of Life",
        "condition_at_suspension": "Non-functional",
        "residual_risk_level": "Low",
        "outcome": "Retire",
        "workflow_state": "Completed",
        "creation": "2026-04-21",
        "days_open": 3
      }
    ],
    "total": 47,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

---

## 10. get_retirement_candidates

**GET** `/api/method/assetcore.api.imm13.get_retirement_candidates`

Danh sách assets đáp ứng ngưỡng retirement candidate.

**Auth:** IMM HTM Manager, IMM CMMS Admin

**Query Params:**

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `min_age_percent` | float | N | % tuổi/expected_life (default: 80) |
| `min_cost_ratio` | float | N | % maintenance cost/purchase cost (default: 50) |
| `min_failures_12m` | int | N | Số lần hỏng tối thiểu (default: 4) |
| `department` | string | N | Filter theo khoa |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "total": 5,
    "candidates": [
      {
        "asset": "VENT-2018-007",
        "asset_name": "Máy thở Hamilton T1",
        "location": "ICU",
        "department": "Hồi sức tích cực",
        "age_years": 8.1,
        "expected_life_years": 8,
        "age_percent": 101.25,
        "maintenance_cost_total": 180000000,
        "purchase_cost": 220000000,
        "maintenance_cost_ratio": 81.8,
        "failure_count_12m": 7,
        "downtime_percent_12m": 28.5,
        "is_retirement_candidate": true,
        "retirement_flag_reason": "Số lần hỏng 12 tháng: 7 (ngưỡng: 5); Downtime 28.5% (ngưỡng: 15%)",
        "recommended_action": "Retire - Trigger IMM-13",
        "risk_score": 92
      }
    ]
  }
}
```

---

## 11. get_dashboard_metrics

**GET** `/api/method/assetcore.api.imm13.get_dashboard_metrics`

KPI metrics cho KPI-DASH-IMMIS-13.

**Auth:** IMM HTM Manager, IMM VP Block2, IMM CMMS Admin

**Query Params:**

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `year` | int | N | Năm tính (default: current) |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "year": 2026,
    "suspended_ytd": 8,
    "transferred_ytd": 4,
    "retirement_candidates_count": 5,
    "avg_days_to_complete": 31.2,
    "pending_approval_count": 2,
    "transfer_in_progress_count": 1,
    "overdue_count": 1,
    "residual_risk_distribution": {
      "Low": 7,
      "Medium": 3,
      "High": 2,
      "Critical": 0
    },
    "suspension_by_reason": {
      "End of Life": 6,
      "Beyond Economic Repair": 3,
      "Regulatory Non-Compliance": 2,
      "Catastrophic Failure": 1
    },
    "transfer_by_destination": {
      "Khoa Cấp cứu": 2,
      "Phòng khám vệ tinh A": 1,
      "Trung tâm y tế Q.Tân Phú": 1
    },
    "outcome_distribution": {
      "Retire": 8,
      "Transfer": 4,
      "Suspend": 0
    },
    "sla_compliance_rate": 91.7,
    "kri_alerts": [
      {
        "kri": "HIGH_VALUE_PENDING",
        "message": "1 phiếu có book_value > 500M chưa được VP phê duyệt quá 14 ngày.",
        "severity": "warning",
        "dr_name": "DR-26-03-00012"
      }
    ]
  }
}
```

---

## 12. get_transfer_history

**GET** `/api/method/assetcore.api.imm13.get_transfer_history`

Lịch sử điều chuyển thiết bị.

**Auth:** Tất cả roles có quyền Read

**Query Params:**

| Param | Type | Required | Mô tả |
|---|---|---|---|
| `asset` | string | N | Filter theo asset cụ thể |
| `from_location` | string | N | Filter theo vị trí nguồn |
| `to_location` | string | N | Filter theo vị trí đích |
| `from_date` | date | N | Từ ngày |
| `to_date` | date | N | Đến ngày |
| `page` | int | N | Default: 1 |
| `page_size` | int | N | Default: 20 |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "rows": [
      {
        "dr_name": "DR-26-04-00001",
        "asset": "ECG-2019-003",
        "asset_name": "ECG 12-lead Nihon Kohden",
        "from_location": "Khoa Tim mạch",
        "to_location": "Khoa Cấp cứu",
        "transfer_date": "2026-04-25",
        "receiving_officer": "nurse@benhvien.vn",
        "receiving_officer_name": "Nguyễn Thị B",
        "handover_confirmed": true,
        "handover_date": "2026-04-25",
        "transfer_conditions": "Thiết bị không hoạt động, bàn giao cho kho phụ tùng khoa."
      }
    ],
    "total": 4,
    "page": 1,
    "page_size": 20
  }
}
```

---

## OpenAPI 3.0 Summary Schema

```yaml
openapi: "3.0.3"
info:
  title: AssetCore IMM-13 API — Suspension & Transfer
  version: "2.0.0"
  description: API quản lý ngừng sử dụng và điều chuyển thiết bị y tế

servers:
  - url: https://immis.benhvienid1.vn
    description: Production

security:
  - ApiKeyAuth: []
  - SessionAuth: []

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: Authorization
    SessionAuth:
      type: apiKey
      in: cookie
      name: sid

  schemas:
    ApiResponse:
      type: object
      properties:
        success: { type: boolean }
        data: { type: object }
        error: { type: string }
        code: { type: string }

    DecommissionRequest:
      type: object
      properties:
        name: { type: string, example: "DR-26-04-00001" }
        asset: { type: string }
        workflow_state: { type: string, enum: [Draft, "Pending Tech Review", "Under Replacement Review", "Approved for Transfer", "Transfer In Progress", Transferred, "Pending Decommission", Completed, Cancelled] }
        suspension_reason: { type: string }
        residual_risk_level: { type: string, enum: [Low, Medium, High, Critical] }
        outcome: { type: string, enum: [Transfer, Suspend, Retire] }
        approved: { type: boolean }
        biological_hazard: { type: boolean }
        data_destruction_required: { type: boolean }
        data_destruction_confirmed: { type: boolean }

paths:
  /api/method/assetcore.api.imm13.create_suspension_request:
    post:
      summary: Tạo phiếu ngừng sử dụng/điều chuyển mới
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.get_suspension_request:
    get:
      summary: Lấy chi tiết phiếu DR
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.submit_technical_review:
    post:
      summary: Biomed hoàn thành đánh giá kỹ thuật
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.submit_replacement_review:
    post:
      summary: Quyết định outcome sau replacement review
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.approve_suspension:
    post:
      summary: VP Block2 phê duyệt ngừng sử dụng
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.execute_transfer:
    post:
      summary: Bắt đầu/hoàn thành điều chuyển vật lý
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.complete_suspension:
    post:
      summary: CMMS Admin submit hoàn tất ngừng sử dụng
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.cancel_suspension_request:
    post:
      summary: Hủy phiếu DR
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.get_suspension_list:
    get:
      summary: Danh sách phiếu DR với filter
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.get_retirement_candidates:
    get:
      summary: Danh sách thiết bị đạt ngưỡng retirement
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.get_dashboard_metrics:
    get:
      summary: KPI metrics cho dashboard IMM-13
      tags: [IMM-13]
  /api/method/assetcore.api.imm13.get_transfer_history:
    get:
      summary: Lịch sử điều chuyển thiết bị
      tags: [IMM-13]
```

---

*End of API Interface v2.0.0 — IMM-13 Ngừng sử dụng và Điều chuyển*
