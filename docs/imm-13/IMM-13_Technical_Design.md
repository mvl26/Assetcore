# IMM-13 — Thanh lý Thiết bị Y tế (Technical Design)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-13 — Technical Design |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |

---

## 1. DocType Schema

### 1.1 Decommission Request (Primary)

| Field | Fieldtype | Label | Options / Notes | reqd | in_list |
|---|---|---|---|---|---|
| `workflow_state` | Link | Trạng thái | Workflow State | — | Y |
| **Section: Thông tin Thiết bị** | | | | | |
| `asset` | Link | Thiết bị | AC Asset | Y | Y |
| `asset_name` | Data | Tên Thiết bị | read_only, fetch from asset | — | Y |
| `decommission_reason` | Select | Lý do Thanh lý | End of Life / Beyond Economic Repair / Regulatory Non-Compliance / Catastrophic Failure / Technology Obsolescence / Donated / Other | Y | — |
| `reason_details` | Text Editor | Chi tiết Lý do | | Y | — |
| `condition_at_decommission` | Select | Tình trạng Thiết bị | Poor / Non-functional / Partially Functional / Functional but Obsolete | — | — |
| `last_service_date` | Date | Ngày bảo trì cuối | | — | — |
| **Section: Thông tin Tài chính** | | | | | |
| `total_maintenance_cost` | Currency | Tổng chi phí bảo trì | | — | — |
| `current_book_value` | Currency | Giá trị sổ sách hiện tại | | — | — |
| `estimated_disposal_value` | Currency | Giá trị thanh lý ước tính | | — | — |
| **Section: Phương án Thanh lý** | | | | | |
| `disposal_method` | Select | Phương án | Auction / Transfer to Facility / Scrap / Bio-hazard Disposal / Donate / Return to Vendor | — | Y |
| `transfer_destination` | Data | Đơn vị nhận (Transfer) | depends_on: disposal_method=Transfer to Facility | — | — |
| **Section: Tuân thủ & An toàn** | | | | | |
| `biological_hazard` | Check | Nguy hại sinh học | | — | — |
| `bio_hazard_clearance` | Data | Biện pháp xử lý sinh học | depends_on: biological_hazard | — | — |
| `data_destruction_required` | Check | Cần xoá dữ liệu | | — | — |
| `data_destruction_confirmed` | Check | Đã xoá dữ liệu | | — | — |
| `regulatory_clearance_required` | Check | Cần giấy phép thanh lý | | — | — |
| `regulatory_clearance_doc` | Attach | File giấy phép thanh lý | depends_on: regulatory_clearance_required | — | — |
| **Section: Đánh giá Kỹ thuật** | | | | | |
| `technical_reviewer` | Link | Kỹ sư đánh giá | User | — | — |
| `technical_review_date` | Date | Ngày đánh giá KT | | — | — |
| `technical_review_notes` | Text | Ghi chú đánh giá KT | | — | — |
| **Section: Định giá Tài chính** | | | | | |
| `finance_reviewer` | Link | Kế toán định giá | User | — | — |
| `finance_review_date` | Date | Ngày định giá | | — | — |
| `finance_review_notes` | Text | Ghi chú định giá | | — | — |
| **Section: Phê duyệt** | | | | | |
| `approved_by` | Link | Người phê duyệt | User | — | — |
| `approval_date` | Date | Ngày phê duyệt | | — | — |
| `approval_notes` | Text | Ghi chú phê duyệt | | — | — |
| **Section: Thực thi** | | | | | |
| `execution_date` | Date | Ngày thực hiện | | — | — |
| `executed_by` | Link | Người thực hiện | User | — | — |
| `execution_notes` | Text | Ghi chú thực hiện | | — | — |
| **Tab: Checklist** | | | | | |
| `checklist` | Table | Danh mục công việc | Decommission Checklist Item | — | — |
| **Tab: Lịch sử** | | | | | |
| `lifecycle_events` | Table | Lifecycle Events | Asset Lifecycle Event | — | — |
| **Hidden** | | | | | |
| `status` | Select | Trạng thái | Draft/Technical Review/Financial Valuation/Pending Approval/Board Approved/Execution/Completed/Rejected | — | — |

### 1.2 Decommission Checklist Item (Child)

| Field | Fieldtype | Label | reqd |
|---|---|---|---|
| `task_name` | Data | Tên công việc | Y |
| `responsible` | Link | Người phụ trách | User |
| `due_date` | Date | Hạn thực hiện | — |
| `completed` | Check | Hoàn thành | — |
| `completion_date` | Date | Ngày hoàn thành | — |
| `notes` | Text | Ghi chú | — |

---

## 2. Naming Series

```
Decommission Request: DR-.YY.-.MM.-.#####
Ví dụ: DR-26-04-00001
```

---

## 3. Controller Hooks

```python
class DecommissionRequest(Document):
    def validate(self):
        # Gọi service layer — KHÔNG viết logic trực tiếp
        from assetcore.services import imm13 as svc
        svc.validate_decommission_request(self)

    def on_submit(self):
        from assetcore.services import imm13 as svc
        svc.on_submit_handler(self)

    def on_cancel(self):
        from assetcore.services import imm13 as svc
        svc.on_cancel_handler(self)
```

---

## 4. Service Layer Architecture

File: `assetcore/services/imm13.py` (< 200 lines)

### 4.1 Validation Flow

```
validate_decommission_request(doc)
  ├── _vr01_check_active_work_orders(doc)
  │     └── frappe.db.count([PM WO, CM WO, Calibration] open on asset)
  ├── _vr02_board_approval_threshold(doc)
  │     └── if current_book_value > 500_000_000: msgprint warning
  ├── _vr03_bio_hazard_clearance(doc)
  │     └── if biological_hazard and not bio_hazard_clearance: throw
  ├── _vr04_regulatory_clearance(doc)
  │     └── if regulatory_clearance_required and not regulatory_clearance_doc: throw
  └── _vr05_data_destruction(doc)
        └── if data_destruction_required and doc.docstatus == 1 and not data_destruction_confirmed: throw
```

### 4.2 on_submit Flow

```
on_submit_handler(doc)
  ├── 1. _set_asset_decommissioned(doc.asset)
  │       └── frappe.db.set_value("AC Asset", asset, "status", "Decommissioned")
  ├── 2. log_lifecycle_event(doc, "decommissioned", ...)
  │       └── frappe.get_doc({"doctype": "Asset Lifecycle Event", ...}).insert()
  └── 3. _trigger_imm14_archive(doc)
          └── frappe.get_doc({
                "doctype": "Asset Archive Record",
                "asset": doc.asset,
                "decommission_request": doc.name,
                "archive_date": frappe.utils.nowdate(),
                "archived_by": frappe.session.user,
                "retention_years": 10,
                "status": "Draft"
              }).insert(ignore_permissions=True)
```

---

## 5. Workflow Transitions Table

| # | From | To | Action field | Guard |
|---|---|---|---|---|
| 1 | Draft | Technical Review | submit_for_technical_review | asset + reason + details filled |
| 2 | Technical Review | Financial Valuation | complete_technical_review | technical_reviewer + notes filled |
| 3 | Technical Review | Rejected | reject_technical_review | — |
| 4 | Financial Valuation | Pending Approval | complete_financial_valuation | finance_reviewer + book_value filled |
| 5 | Pending Approval | Board Approved | approve_decommission | approved_by + notes filled |
| 6 | Pending Approval | Rejected | reject_decommission | — |
| 7 | Board Approved | Execution | start_execution | — |
| 8 | Execution | Completed | complete_decommission (submit) | VR-01..VR-05 all pass |
| 9 | Execution | Rejected | reject_execution | System Manager only |

---

## 6. Database Indexes

```sql
-- Decommission Request
CREATE INDEX idx_dr_asset ON `tabDecommission Request` (asset, docstatus);
CREATE INDEX idx_dr_status ON `tabDecommission Request` (status, modified);
CREATE INDEX idx_dr_year ON `tabDecommission Request` (creation);

-- Decommission Checklist Item
CREATE INDEX idx_dci_parent ON `tabDecommission Checklist Item` (parent);
```

---

## 7. Audit Trail Pattern

Mọi state transition phải ghi `Asset Lifecycle Event`:

```python
def log_lifecycle_event(doc, event_type, from_status, to_status, notes=""):
    """Sinh immutable ALE — không được xoá hoặc sửa sau khi insert."""
    frappe.get_doc({
        "doctype": "Asset Lifecycle Event",
        "asset": doc.asset,
        "event_type": event_type,        # "decommissioned"
        "timestamp": frappe.utils.now_datetime(),
        "actor": frappe.session.user,
        "from_status": from_status,
        "to_status": to_status,
        "root_doctype": "Decommission Request",
        "root_record": doc.name,
        "notes": notes,
    }).insert(ignore_permissions=True)
```

---

## 8. Integration Points

| Target | Cơ chế | Timing |
|---|---|---|
| `AC Asset` | `frappe.db.set_value(asset, "status", "Decommissioned")` | on_submit |
| `Asset Lifecycle Event` | direct insert | every transition |
| `Asset Archive Record` | `frappe.get_doc({...}).insert()` | on_submit |
| Email / Realtime | `frappe.publish_realtime` + `frappe.sendmail` | per transition |

---

*End of Technical Design v1.0.0 — IMM-13*
