# IMM-14 — Lưu trữ & Kết thúc Hồ sơ (Technical Design)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-14 — Technical Design |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |

---

## 1. DocType Schema

### 1.1 Asset Archive Record (Primary)

| Field | Fieldtype | Label | Options / Notes | reqd |
|---|---|---|---|---|
| `workflow_state` | Link | Trạng thái | Workflow State | — |
| **Section: Thông tin Lưu trữ** | | | | |
| `asset` | Link | Thiết bị | AC Asset | Y |
| `asset_name` | Data | Tên Thiết bị | read_only | — |
| `decommission_request` | Link | Phiếu Thanh lý | Decommission Request | — |
| `archive_date` | Date | Ngày Lưu trữ | reqd | Y |
| `archived_by` | Link | Người Lưu trữ | User | — |
| **Section: Chi tiết Lưu trữ** | | | | |
| `storage_location` | Data | Vị trí Lưu trữ | (vật lý hoặc số) | — |
| `retention_years` | Int | Số năm Lưu trữ | default=10 | — |
| `release_date` | Date | Ngày Giải phóng | read_only, computed | — |
| `total_documents_archived` | Int | Tổng tài liệu | computed | — |
| `summary_report_url` | Attach | Báo cáo Tóm tắt Vòng đời | | — |
| `archive_notes` | Text Editor | Ghi chú Lưu trữ | | — |
| **Tab: Danh mục Tài liệu** | | | | |
| `documents` | Table | Tài liệu Lưu trữ | Archive Document Entry | — |
| **Tab: Lịch sử** | | | | |
| `lifecycle_events` | Table | Lifecycle Events | Asset Lifecycle Event | — |
| **Hidden** | | | | |
| `status` | Select | Trạng thái | Draft/Compiling/Verified/Archived | — |

### 1.2 Archive Document Entry (Child)

| Field | Fieldtype | Label | Options | reqd |
|---|---|---|---|---|
| `document_type` | Select | Loại tài liệu | Commissioning/PM Record/Repair Record/Calibration/Incident/CAPA/Service Contract/Other | Y |
| `document_name` | Data | Mã tài liệu | | — |
| `document_date` | Date | Ngày tài liệu | | — |
| `archive_status` | Select | Trạng thái | Included/Missing/Waived | Y |
| `notes` | Text | Ghi chú | | — |

---

## 2. Naming Series

```
Asset Archive Record: AAR-.YY.-.#####
Ví dụ: AAR-26-00001
```

---

## 3. Controller Hooks

```python
class AssetArchiveRecord(Document):
    def validate(self):
        from assetcore.services import imm14 as svc
        svc.validate_archive_record(self)

    def before_save(self):
        # Tính release_date
        if self.archive_date and self.retention_years:
            from dateutil.relativedelta import relativedelta
            from frappe.utils import getdate
            d = getdate(self.archive_date)
            self.release_date = d + relativedelta(years=int(self.retention_years))
        # Đếm documents
        self.total_documents_archived = len(self.documents or [])

    def on_submit(self):
        from assetcore.services import imm14 as svc
        svc.finalize_archive_handler(self)
```

---

## 4. Service Layer

File: `assetcore/services/imm14.py` (< 200 lines)

### 4.1 compile_asset_history logic

```python
def compile_asset_history(archive_name: str) -> dict:
    """Tự động tổng hợp tài liệu từ tất cả module cho asset."""
    doc = frappe.get_doc("Asset Archive Record", archive_name)
    asset = doc.asset
    entries = []

    # IMM-04: Commissioning
    entries += _collect_commissioning_docs(asset)

    # IMM-08: PM Work Orders
    entries += _collect_pm_records(asset)

    # IMM-09: Repair
    entries += _collect_repair_records(asset)

    # IMM-11: Calibration
    entries += _collect_calibration_records(asset)

    # IMM-12: Incident
    entries += _collect_incident_records(asset)

    # Clear cũ, insert mới
    doc.documents = []
    for e in entries:
        doc.append("documents", e)

    doc.total_documents_archived = len(entries)
    doc.status = "Compiling"
    doc.save(ignore_permissions=True)
    return {"compiled": len(entries)}
```

### 4.2 finalize_archive_handler

```python
def finalize_archive_handler(doc) -> None:
    """on_submit: set asset Archived + log ALE."""
    if doc.status != "Verified":
        frappe.throw(_("Không thể hoàn tất: Phiếu chưa được QA Officer xác minh."))

    frappe.db.set_value("AC Asset", doc.asset, "status", "Archived")
    log_lifecycle_event(doc, "archived", "Verified", "Archived", "Hồ sơ thiết bị đã lưu trữ")
```

---

## 5. Document Collection — Source Mapping

| document_type | DocType nguồn | Filter field | Date field |
|---|---|---|---|
| Commissioning | `Asset Commissioning` | `final_asset` | `commissioning_date` |
| PM Record | `PM Work Order` | `asset` | `completed_date` |
| Repair Record | `Asset Repair` | `asset_ref` | `completion_datetime` |
| Calibration | `IMM Asset Calibration` | `asset` | `calibration_date` |
| Incident | `Incident Report` | `asset` | `reported_date` |
| Service Contract | `Service Contract Asset` | `asset` | parent `start_date` |

---

## 6. get_asset_full_history timeline format

```json
{
  "asset": "MRI-2024-001",
  "timeline": [
    {
      "date": "2011-03-15",
      "event_type": "commissioned",
      "module": "IMM-04",
      "record": "IMM04-11-03-00001",
      "notes": "Lắp đặt tại Khoa CĐHA"
    },
    {
      "date": "2011-06-15",
      "event_type": "pm_completed",
      "module": "IMM-08",
      "record": "WO-PM-2011-00001",
      "notes": "PM quý 1"
    },
    ...
    {
      "date": "2026-04-21",
      "event_type": "decommissioned",
      "module": "IMM-13",
      "record": "DR-26-04-00001",
      "notes": "Thanh lý EOL"
    }
  ],
  "total_events": 87
}
```

---

## 7. Database Indexes

```sql
CREATE INDEX idx_aar_asset ON `tabAsset Archive Record` (asset, docstatus);
CREATE INDEX idx_aar_release ON `tabAsset Archive Record` (release_date);
CREATE INDEX idx_ade_parent ON `tabArchive Document Entry` (parent);
```

---

*End of Technical Design v1.0.0 — IMM-14*
