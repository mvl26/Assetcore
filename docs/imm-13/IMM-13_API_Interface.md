# IMM-13 — Thanh lý Thiết bị Y tế (API Interface)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-13 — API Interface |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Base URL | `/api/method/assetcore.api.imm13.` |

---

## Quy ước chung

Mọi response đều bọc trong `_ok` / `_err` envelope:

```json
// Success
{"success": true, "data": {...}}

// Error
{"success": false, "error": "Mô tả lỗi tiếng Việt", "code": "ERROR_CODE"}
```

---

## 1. create_decommission_request

**POST** `/api/method/assetcore.api.imm13.create_decommission_request`

Tạo phiếu thanh lý mới.

**Request:**
```json
{
  "asset": "MRI-2024-001",
  "decommission_reason": "End of Life",
  "reason_details": "Thiết bị đã qua 15 năm sử dụng, không còn phụ tùng thay thế.",
  "condition_at_decommission": "Non-functional",
  "current_book_value": 150000000,
  "estimated_disposal_value": 20000000,
  "disposal_method": "Scrap"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "asset": "MRI-2024-001",
    "status": "Draft",
    "creation": "2026-04-21 09:00:00"
  }
}
```

**Error codes:** `ACTIVE_WO_EXISTS`, `ASSET_NOT_FOUND`, `VALIDATION_ERROR`

---

## 2. get_decommission_request

**GET** `/api/method/assetcore.api.imm13.get_decommission_request?name=DR-26-04-00001`

Lấy chi tiết phiếu.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "name": "DR-26-04-00001",
    "asset": "MRI-2024-001",
    "asset_name": "MRI 1.5T Siemens Magnetom",
    "decommission_reason": "End of Life",
    "status": "Technical Review",
    "workflow_state": "Technical Review",
    "current_book_value": 150000000,
    "checklist": [...],
    "lifecycle_events": [...]
  }
}
```

---

## 3. list_decommission_requests

**GET** `/api/method/assetcore.api.imm13.list_decommission_requests`

**Query params:** `status`, `asset`, `year`, `page` (default 1), `page_size` (default 20)

**Response 200:**
```json
{
  "success": true,
  "data": {
    "rows": [{
      "name": "DR-26-04-00001",
      "asset": "MRI-2024-001",
      "asset_name": "MRI 1.5T Siemens",
      "decommission_reason": "End of Life",
      "disposal_method": "Scrap",
      "current_book_value": 150000000,
      "status": "Technical Review",
      "creation": "2026-04-21"
    }],
    "total": 15,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 4. submit_technical_review

**POST** `/api/method/assetcore.api.imm13.submit_technical_review`

```json
{
  "name": "DR-26-04-00001",
  "reviewer": "biomed@hospital.vn",
  "review_notes": "Thiết bị hỏng hoàn toàn, không còn khả năng sửa chữa.",
  "approved": true
}
```

**Transitions:** Technical Review → Financial Valuation (approved=true) hoặc Rejected (approved=false)

---

## 5. submit_financial_valuation

**POST** `/api/method/assetcore.api.imm13.submit_financial_valuation`

```json
{
  "name": "DR-26-04-00001",
  "reviewer": "finance@hospital.vn",
  "final_book_value": 150000000,
  "estimated_disposal_value": 20000000,
  "review_notes": "Đã khấu hao 80%, giá trị còn lại 150 triệu."
}
```

**Transition:** Financial Valuation → Pending Approval

---

## 6. request_approval

**POST** `/api/method/assetcore.api.imm13.request_approval`

```json
{"name": "DR-26-04-00001"}
```

Xác nhận phiếu đã sẵn sàng phê duyệt. Gửi notification cho VP Block2.

---

## 7. approve_decommission

**POST** `/api/method/assetcore.api.imm13.approve_decommission`

```json
{
  "name": "DR-26-04-00001",
  "approver": "vp@hospital.vn",
  "approval_notes": "Đã họp BGĐ ngày 20/04/2026, thống nhất thanh lý."
}
```

**Transition:** Pending Approval → Board Approved

---

## 8. reject_decommission

**POST** `/api/method/assetcore.api.imm13.reject_decommission`

```json
{
  "name": "DR-26-04-00001",
  "reason": "Thiết bị có thể chuyển cho cơ sở y tế tuyến dưới."
}
```

**Transition:** Any → Rejected

---

## 9. execute_decommission

**POST** `/api/method/assetcore.api.imm13.execute_decommission`

```json
{
  "name": "DR-26-04-00001",
  "executor": "htm@hospital.vn",
  "execution_date": "2026-04-25",
  "execution_notes": "Đã thực hiện thanh lý, giao cho đơn vị thu mua phế liệu."
}
```

**Transition:** Board Approved → Execution → (Submit để → Completed)

---

## 10. complete_checklist_item

**POST** `/api/method/assetcore.api.imm13.complete_checklist_item`

```json
{
  "name": "DR-26-04-00001",
  "checklist_item_idx": 1,
  "notes": "Đã hoàn thành thu hồi thiết bị từ khoa Chẩn đoán hình ảnh"
}
```

---

## 11. get_asset_decommission_eligibility

**GET** `/api/method/assetcore.api.imm13.get_asset_decommission_eligibility?asset_name=MRI-2024-001`

Kiểm tra thiết bị có đủ điều kiện thanh lý.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "eligible": false,
    "reasons": [
      "Còn 2 Work Order đang mở: WO-CM-2026-00123, WO-PM-2026-00456"
    ],
    "asset_status": "Under Repair",
    "last_pm_date": "2026-01-15",
    "total_maintenance_cost": 45000000,
    "current_book_value": 150000000,
    "open_work_orders": ["WO-CM-2026-00123", "WO-PM-2026-00456"]
  }
}
```

---

## 12. get_dashboard_stats

**GET** `/api/method/assetcore.api.imm13.get_dashboard_stats`

**Response 200:**
```json
{
  "success": true,
  "data": {
    "decommissioned_ytd": 12,
    "pending_approval": 3,
    "in_execution": 2,
    "avg_days_to_complete": 28.5,
    "total_disposal_value_ytd": 250000000,
    "by_disposal_method": {
      "Scrap": 7,
      "Transfer to Facility": 3,
      "Auction": 2
    },
    "by_reason": {
      "End of Life": 8,
      "Beyond Economic Repair": 4
    }
  }
}
```

---

*End of API Interface v1.0.0 — IMM-13*
