# IMM-14 — Lưu trữ & Kết thúc Hồ sơ (API Interface)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-14 — API Interface |
| Phiên bản | 1.0.0 |
| Base URL | `/api/method/assetcore.api.imm14.` |

---

## 1. create_archive_record

**POST** `/api/method/assetcore.api.imm14.create_archive_record`

```json
{
  "asset": "MRI-2024-001",
  "decommission_request": "DR-26-04-00001",
  "archive_date": "2026-04-25",
  "storage_location": "Server DMS / Tủ văn thư P.TBYT",
  "retention_years": 10
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "AAR-26-00001",
    "asset": "MRI-2024-001",
    "status": "Draft",
    "release_date": "2036-04-25"
  }
}
```

---

## 2. get_archive_record

**GET** `/api/method/assetcore.api.imm14.get_archive_record?name=AAR-26-00001`

Returns full record including `documents` table and `lifecycle_events`.

---

## 3. list_archive_records

**GET** `/api/method/assetcore.api.imm14.list_archive_records`

**Params:** `status`, `asset`, `page` (default 1), `page_size` (default 20)

```json
{
  "success": true,
  "data": {
    "rows": [{
      "name": "AAR-26-00001",
      "asset": "MRI-2024-001",
      "asset_name": "MRI 1.5T Siemens",
      "archive_date": "2026-04-25",
      "release_date": "2036-04-25",
      "status": "Archived",
      "total_documents_archived": 35
    }],
    "total": 8,
    "page": 1
  }
}
```

---

## 4. add_document

**POST** `/api/method/assetcore.api.imm14.add_document`

Thêm tài liệu đơn lẻ vào `documents` table.

```json
{
  "archive_name": "AAR-26-00001",
  "document_type": "Service Contract",
  "document_name": "SC-2020-MRI-001",
  "document_date": "2020-03-01",
  "archive_status": "Included"
}
```

---

## 5. compile_asset_history

**POST** `/api/method/assetcore.api.imm14.compile_asset_history`

Tự động tổng hợp tất cả tài liệu. Ghi đè `documents` table với dữ liệu mới.

```json
{"archive_name": "AAR-26-00001"}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "compiled": 35,
    "breakdown": {
      "Commissioning": 1,
      "PM Record": 24,
      "Repair Record": 3,
      "Calibration": 5,
      "Incident": 2
    },
    "missing_count": 0
  }
}
```

---

## 6. verify_archive

**POST** `/api/method/assetcore.api.imm14.verify_archive`

```json
{
  "name": "AAR-26-00001",
  "verified_by": "qa@hospital.vn",
  "notes": "Đã kiểm tra đủ 35 tài liệu theo checklist QA-AR-001."
}
```

**Transition:** Compiling → Verified

---

## 7. finalize_archive

**POST** `/api/method/assetcore.api.imm14.finalize_archive`

Submit record → Archived. Sets Asset.status = "Archived".

```json
{"name": "AAR-26-00001"}
```

---

## 8. get_asset_full_history

**GET** `/api/method/assetcore.api.imm14.get_asset_full_history?asset_name=MRI-2024-001`

Trả về toàn bộ timeline vòng đời thiết bị từ tất cả module.

```json
{
  "success": true,
  "data": {
    "asset": "MRI-2024-001",
    "asset_name": "MRI 1.5T Siemens Magnetom",
    "timeline": [
      {"date": "2011-03-15", "event_type": "commissioned", "module": "IMM-04", "record": "IMM04-11-03-00001"},
      {"date": "2026-04-21", "event_type": "decommissioned", "module": "IMM-13", "record": "DR-26-04-00001"},
      {"date": "2026-04-25", "event_type": "archived", "module": "IMM-14", "record": "AAR-26-00001"}
    ],
    "total_events": 87,
    "lifecycle_years": 15.1
  }
}
```

---

## 9. get_dashboard_stats

**GET** `/api/method/assetcore.api.imm14.get_dashboard_stats`

```json
{
  "success": true,
  "data": {
    "archived_ytd": 8,
    "pending_verification": 2,
    "avg_documents_per_archive": 32.5,
    "missing_document_rate": 3.2,
    "expiring_within_30_days": 0,
    "total_archived_all_time": 45
  }
}
```

---

*End of API Interface v1.0.0 — IMM-14*
