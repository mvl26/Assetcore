# IMM-01 — API Interface

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh Giá Nhu Cầu & Dự Toán |
| Base URL | `/api/method/assetcore.api.imm01` |

---

## Endpoints

### POST create_needs_assessment

**Request:**
```json
{
  "requesting_dept": "Hồi sức Tích cực",
  "equipment_type": "Máy thở ICU",
  "quantity": 2,
  "estimated_budget": 500000000,
  "clinical_justification": "Máy thở hiện tại đã 12 năm, hỏng thường xuyên...",
  "priority": "Critical",
  "linked_device_model": "DM-00001"
}
```
**Response 200:**
```json
{"success": true, "data": {"name": "NA-26-04-00001", "status": "Draft"}}
```

---

### GET get_needs_assessment

`?name=NA-26-04-00001`

**Response:** Full document object.

---

### GET list_needs_assessments

`?status=Submitted&dept=Hồi+sức+Tích+cực&year=2026&page=1&page_size=20`

**Response:**
```json
{"success": true, "data": {"items": [...], "total": 45, "page": 1}}
```

---

### POST submit_for_review

```json
{"name": "NA-26-04-00001"}
```
**Response:** `{"success": true, "data": {"status": "Submitted"}}`

---

### POST approve_needs_assessment

```json
{
  "name": "NA-26-04-00001",
  "approved_budget": 450000000,
  "notes": "Điều chỉnh theo khung giá BYT 2026"
}
```
**Response:** `{"success": true, "data": {"status": "Approved", "approved_budget": 450000000}}`

---

### POST reject_needs_assessment

```json
{
  "name": "NA-26-04-00001",
  "reason": "Đã có thiết bị tương đương đang hoạt động tại kho"
}
```
**Response:** `{"success": true, "data": {"status": "Rejected"}}`

---

### GET get_dashboard_stats

`?year=2026&dept=all`

**Response:**
```json
{
  "success": true,
  "data": {
    "total": 42,
    "by_status": {"Draft": 5, "Submitted": 8, "Under Review": 6, "Approved": 18, "Rejected": 5},
    "total_requested_budget": 12500000000,
    "total_approved_budget": 9800000000,
    "avg_processing_days": 9.4,
    "by_priority": {"Critical": 8, "High": 14, "Medium": 15, "Low": 5},
    "approval_rate": 78.3
  }
}
```

---

## Error Codes

| Code | Mô tả |
|---|---|
| `VALIDATION_ERROR` | VR vi phạm |
| `NOT_FOUND` | Record không tồn tại |
| `PERMISSION_ERROR` | Không đủ quyền |
| `INVALID_STATE` | Transition không hợp lệ từ trạng thái hiện tại |
