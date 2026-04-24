# IMM-13 — Ngừng sử dụng và Điều chuyển (Technical Design)

| Thuộc tính    | Giá trị                            |
|---------------|------------------------------------|
| Module        | IMM-13 — Technical Design          |
| Phiên bản     | 2.0.0                              |
| Ngày cập nhật | 2026-04-24                         |
| Stack         | Python · Frappe v15 · MariaDB      |

---

## 1. Entity Relationship Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                         AC Asset                                       │
│  name (PK) · status · location · model · serial_number                │
│  expected_life_years · purchase_date · purchase_cost                   │
└─────────────────────────┬──────────────────────────────────────────────┘
                          │ 1
                          │ n
┌─────────────────────────▼──────────────────────────────────────────────┐
│                   Decommission Request (DR)                            │
│  name (PK) · asset (FK→AC Asset) · workflow_state                     │
│  suspension_reason · outcome · residual_risk_level                     │
│  biological_hazard · data_destruction_required                         │
│  current_book_value · transfer_to_location                             │
│  approved_by · approval_date · approved (Check)                        │
└───┬─────────────────────────┬────────────────────────────────┬─────────┘
    │ 1:n                     │ 1:n                            │ 1:n
    ▼                         ▼                                ▼
┌──────────────────┐  ┌──────────────────────┐  ┌────────────────────────┐
│ Suspension       │  │  Transfer Detail     │  │ Asset Lifecycle Event  │
│ Checklist Item   │  │  (child table)       │  │ (audit trail)          │
│                  │  │                      │  │                        │
│ task_name        │  │ transfer_to_location │  │ event_type             │
│ responsible      │  │ transfer_to_dept     │  │ from_status            │
│ due_date         │  │ receiving_officer    │  │ to_status              │
│ completed (Check)│  │ transfer_date        │  │ actor                  │
│ completion_date  │  │ transfer_conditions  │  │ timestamp              │
│ notes            │  │ transport_notes      │  │ root_record            │
└──────────────────┘  └──────────────────────┘  └────────────────────────┘
```

---

## 2. DocType Schema: Decommission Request (Primary)

### 2.1 Field Definitions (25+ fields)

| # | Field Name | Fieldtype | Label (VI) | Options / Link | reqd | in_list | Ghi chú |
|---|---|---|---|---|---|---|---|
| 1 | `workflow_state` | Link | Trạng thái | Workflow State | — | Y | Auto-managed by Frappe Workflow |
| **— Section: Thông tin Thiết bị —** |||||||||
| 2 | `asset` | Link | Thiết bị | AC Asset | Y | Y | Primary link |
| 3 | `asset_name` | Data | Tên thiết bị | — | — | Y | `fetch_from: asset.asset_name` · read_only |
| 4 | `asset_model` | Data | Model | — | — | — | `fetch_from: asset.device_model` · read_only |
| 5 | `asset_location` | Link | Vị trí hiện tại | Location | — | — | `fetch_from: asset.location` · read_only |
| 6 | `asset_age_years` | Float | Tuổi thiết bị (năm) | — | — | — | Tính từ purchase_date · read_only |
| 7 | `suspension_reason` | Select | Lý do ngừng | End of Life\nBeyond Economic Repair\nRegulatory Non-Compliance\nCatastrophic Failure\nTechnology Obsolescence\nRelocation\nDonated\nOther | Y | Y | — |
| 8 | `reason_details` | Text Editor | Chi tiết lý do | — | Y | — | — |
| 9 | `condition_at_suspension` | Select | Tình trạng thiết bị | Poor\nNon-functional\nPartially Functional\nFunctional but Obsolete | — | Y | — |
| **— Section: Đánh giá Kỹ thuật —** |||||||||
| 10 | `technical_reviewer` | Link | Kỹ sư đánh giá | User | — | — | Frappe user |
| 11 | `tech_review_date` | Date | Ngày đánh giá KT | — | — | — | — |
| 12 | `tech_review_notes` | Text | Ghi chú đánh giá KT | — | — | — | — |
| 13 | `residual_risk_level` | Select | Mức độ rủi ro còn lại | Low\nMedium\nHigh\nCritical | — | Y | BR-13-06: bắt buộc trước khi rời Pending Tech Review |
| 14 | `residual_risk_notes` | Text | Mô tả rủi ro còn lại | — | — | — | — |
| 15 | `estimated_remaining_life` | Int | Tuổi thọ ước tính còn lại (tháng) | — | — | — | 0 = không còn |
| 16 | `maintenance_cost_total` | Currency | Tổng chi phí bảo trì tích lũy | — | — | — | Auto-fetch từ WO history |
| 17 | `downtime_percent_12m` | Percent | % Downtime 12 tháng | — | — | — | Auto-fetch từ IMM-12 |
| **— Section: Review Thay thế —** |||||||||
| 18 | `replacement_needed` | Select | Cần thay thế | Yes\nNo\nDeferred | — | — | — |
| 19 | `replacement_device_model` | Link | Model thay thế đề xuất | Device Model | — | — | `depends_on: replacement_needed == "Yes"` |
| 20 | `replacement_estimated_cost` | Currency | Chi phí thay thế ước tính | — | — | — | — |
| 21 | `replacement_timeline` | Data | Thời gian thay thế dự kiến | — | — | — | Ví dụ: "Q3 2026" |
| 22 | `economic_justification` | Text | Luận chứng kinh tế | — | — | — | Finance điền |
| **— Section: Thông tin Tài chính —** |||||||||
| 23 | `current_book_value` | Currency | Giá trị sổ sách hiện tại | — | — | — | Finance điền |
| 24 | `maintenance_cost_ratio` | Percent | Tỷ lệ bảo trì/giá trị mua | — | — | — | Auto-calc: `maintenance_cost_total / purchase_cost * 100` |
| **— Section: Quyết định Outcome —** |||||||||
| 25 | `outcome` | Select | Quyết định | Transfer\nSuspend\nRetire | — | Y | Quyết định sau Replacement Review |
| 26 | `outcome_notes` | Text | Ghi chú quyết định | — | — | — | — |
| **— Section: Thông tin Điều chuyển —** |||||||||
| 27 | `transfer_to_location` | Link | Vị trí nhận | Location | — | — | `depends_on: outcome == "Transfer"` |
| 28 | `transfer_to_department` | Link | Khoa/Phòng nhận | Department | — | — | — |
| 29 | `receiving_officer` | Link | Người tiếp nhận | User | — | — | BR-13-10: bắt buộc khi Transfer |
| **— Section: Tuân thủ & An toàn —** |||||||||
| 30 | `biological_hazard` | Check | Nguy hại sinh học | — | — | — | — |
| 31 | `bio_hazard_clearance` | Text | Biện pháp xử lý sinh học | — | — | — | `depends_on: biological_hazard` · BR-13-03 |
| 32 | `data_destruction_required` | Check | Cần xóa dữ liệu bệnh nhân | — | — | — | — |
| 33 | `data_destruction_confirmed` | Check | Đã xác nhận xóa dữ liệu | — | — | — | `depends_on: data_destruction_required` · BR-13-05 |
| 34 | `regulatory_clearance_required` | Check | Cần giấy phép pháp lý | — | — | — | — |
| 35 | `regulatory_clearance_doc` | Attach | File giấy phép | — | — | — | `depends_on: regulatory_clearance_required` · BR-13-04 |
| **— Section: Phê duyệt —** |||||||||
| 36 | `approved` | Check | Đã phê duyệt | — | — | — | Set by approve action |
| 37 | `approved_by` | Link | Người phê duyệt | User | — | — | — |
| 38 | `approval_date` | Date | Ngày phê duyệt | — | — | — | — |
| 39 | `approval_notes` | Text | Ghi chú phê duyệt | — | — | — | — |
| 40 | `rejection_reason` | Text | Lý do từ chối | — | — | — | BR-13-11: bắt buộc khi Cancel |
| **— Tab: Checklist —** |||||||||
| 41 | `suspension_checklist` | Table | Danh mục công việc | Suspension Checklist Item | — | — | — |
| **— Tab: Điều chuyển —** |||||||||
| 42 | `transfer_details` | Table | Chi tiết điều chuyển | Transfer Detail | — | — | `depends_on: outcome == "Transfer"` |
| **— Hidden —** |||||||||
| 43 | `initiated_from_module` | Data | Module nguồn | — | — | — | e.g. "IMM-12" nếu auto-triggered |
| 44 | `initiated_from_record` | Data | Record nguồn | — | — | — | WO name nếu triggered từ WO |

---

## 3. DocType Schema: Suspension Checklist Item (Child)

| Field | Fieldtype | Label | reqd | Ghi chú |
|---|---|---|---|---|
| `task_name` | Data | Tên công việc | Y | e.g. "Thu hồi thiết bị từ khoa" |
| `task_category` | Select | Phân loại | — | Physical / Data / Biological / Regulatory / Documentation |
| `responsible` | Link | Người phụ trách | — | User |
| `due_date` | Date | Hạn thực hiện | — | — |
| `completed` | Check | Hoàn thành | — | — |
| `completion_date` | Date | Ngày hoàn thành | — | Auto-set khi `completed` ticked |
| `notes` | Text | Ghi chú | — | — |

**Default checklist items** (auto-insert khi tạo DR):
1. Thu hồi thiết bị từ khoa sử dụng *(Physical)*
2. Gắn nhãn "NGỪNG SỬ DỤNG" lên thiết bị *(Physical)*
3. Kiểm kê phụ tùng / phụ kiện kèm theo *(Documentation)*
4. Xóa dữ liệu bệnh nhân (nếu applicable) *(Data)*
5. Vệ sinh/khử khuẩn thiết bị *(Biological)*
6. Chụp ảnh tình trạng thiết bị *(Documentation)*
7. Lưu kho tạm / chuyển vị trí quy định *(Physical)*

---

## 4. DocType Schema: Transfer Detail (Child)

| Field | Fieldtype | Label | reqd | Ghi chú |
|---|---|---|---|---|
| `transfer_to_location` | Link | Vị trí nhận | Y | Location DocType |
| `transfer_to_department` | Link | Khoa/Phòng nhận | — | Department |
| `receiving_officer` | Link | Người tiếp nhận | Y | User |
| `transfer_date` | Date | Ngày điều chuyển | — | — |
| `transfer_conditions` | Text | Điều kiện bàn giao | — | Tình trạng khi bàn giao |
| `transport_notes` | Text | Ghi chú vận chuyển | — | — |
| `handover_confirmed` | Check | Đã xác nhận bàn giao | — | Receiving officer confirm |
| `handover_date` | Date | Ngày xác nhận bàn giao | — | — |

---

## 5. Naming Series

```
Decommission Request: DR-.YY.-.MM.-.#####
Ví dụ: DR-26-04-00001 (năm 2026, tháng 4, số thứ tự 1)
```

---

## 6. Controller Hooks

```python
# assetcore/doctype/decommission_request/decommission_request.py

class DecommissionRequest(Document):
    """Controller cho Decommission Request — IMM-13.
    
    KHÔNG viết business logic tại đây. Tất cả delegate sang service layer.
    """

    def validate(self) -> None:
        """Chạy validation rules BR-13-01 → BR-13-12."""
        from assetcore.services import imm13 as svc
        svc.validate_suspension_request(self)

    def before_submit(self) -> None:
        """Validation cuối trước khi submit (BR-13-05, BR-13-08)."""
        from assetcore.services import imm13 as svc
        svc.before_submit_handler(self)

    def on_submit(self) -> None:
        """Atomic: set asset status + ALE + optional IMM-14 trigger."""
        from assetcore.services import imm13 as svc
        svc.on_submit_handler(self)

    def on_cancel(self) -> None:
        """Revert asset status nếu cần; log ALE cancelled."""
        from assetcore.services import imm13 as svc
        svc.on_cancel_handler(self)

    def before_insert(self) -> None:
        """Auto-insert default checklist items."""
        from assetcore.services import imm13 as svc
        svc.insert_default_checklist(self)
```

---

## 7. Service Layer: `assetcore/services/imm13.py`

### 7.1 Hàm Public (≥ 8 hàm)

```python
def validate_suspension_request(doc: "DecommissionRequest") -> None:
    """Orchestrate BR-13-01 → BR-13-07 validation.
    
    Args:
        doc: Decommission Request document đang được validate.
    Raises:
        frappe.ValidationError: Khi vi phạm bất kỳ BR nào.
    """
    _br01_check_active_work_orders(doc)
    _br02_check_duplicate_dr(doc)
    _br03_bio_hazard_clearance(doc)
    _br04_regulatory_clearance(doc)
    _br06_residual_risk_required(doc)
    _br07_high_risk_needs_replacement_review(doc)
    _br09_validate_transfer_location(doc)
    _br10_transfer_requires_receiving_officer(doc)


def before_submit_handler(doc: "DecommissionRequest") -> None:
    """Validation trước submit: BR-13-05, BR-13-08.
    
    Args:
        doc: Decommission Request document.
    """
    _br05_data_destruction_confirmed(doc)
    _br08_high_value_needs_vp_approval(doc)


def on_submit_handler(doc: "DecommissionRequest") -> None:
    """Atomic on_submit: cập nhật asset + ALE + trigger IMM-14.
    
    Thực thi trong transaction — nếu bất kỳ bước nào lỗi, rollback toàn bộ.
    
    Args:
        doc: Submitted Decommission Request.
    """
    if doc.outcome == "Transfer":
        _execute_transfer(doc)
    else:
        _execute_suspension(doc)
    
    event_type = "transferred" if doc.outcome == "Transfer" else "suspended"
    log_lifecycle_event(doc, event_type, "Pending Decommission" if doc.outcome != "Transfer" else "Transfer In Progress",
                        doc.workflow_state)

    if doc.outcome == "Retire":
        _trigger_imm14(doc)


def on_cancel_handler(doc: "DecommissionRequest") -> None:
    """Xử lý cancel: log ALE, notify actors.
    
    Args:
        doc: Cancelled Decommission Request.
    """
    log_lifecycle_event(doc, "suspension_cancelled", doc.workflow_state, "Cancelled",
                        notes=doc.rejection_reason)
    _send_notification(doc, recipients=_get_htm_managers(), 
                       message=f"Phiếu {doc.name} đã bị hủy. Lý do: {doc.rejection_reason}")


def log_lifecycle_event(
    doc: "DecommissionRequest",
    event_type: str,
    from_status: str,
    to_status: str,
    notes: str = "",
) -> None:
    """Sinh immutable Asset Lifecycle Event — không được xóa sau insert.
    
    Args:
        doc: DR document.
        event_type: Loại sự kiện (e.g. "suspended", "transferred").
        from_status: Trạng thái trước transition.
        to_status: Trạng thái sau transition.
        notes: Ghi chú bổ sung.
    """
    frappe.get_doc({
        "doctype": "Asset Lifecycle Event",
        "asset": doc.asset,
        "event_type": event_type,
        "timestamp": frappe.utils.now_datetime(),
        "actor": frappe.session.user,
        "from_status": from_status,
        "to_status": to_status,
        "root_doctype": "Decommission Request",
        "root_record": doc.name,
        "notes": notes,
    }).insert(ignore_permissions=True)


def get_asset_suspension_eligibility(asset_name: str) -> dict:
    """Kiểm tra asset đủ điều kiện để tạo DR.
    
    Args:
        asset_name: Tên AC Asset.
    Returns:
        dict với keys: eligible (bool), reasons (list), open_work_orders (list),
        asset_status (str), maintenance_cost_total (float), asset_age_years (float).
    """
    ...


def get_retirement_candidates() -> list[dict]:
    """Trả về danh sách assets đáp ứng retirement candidate thresholds.
    
    Criteria: tuổi >= 80% expected life HOẶC maintenance_cost_ratio >= 50%
    HOẶC failure_count_12m >= 4 HOẶC downtime_percent_12m >= 15%.
    
    Returns:
        list of dicts với: asset_name, asset, age_years, maintenance_ratio,
        failure_count_12m, downtime_percent, recommended_action, risk_score.
    """
    ...


def get_dashboard_metrics() -> dict:
    """KPI metrics cho KPI-DASH-IMMIS-13.
    
    Returns:
        dict với: suspended_ytd, transferred_ytd, retirement_candidates_count,
        avg_days_to_complete, pending_approval_count, residual_risk_distribution,
        suspension_by_reason, transfer_by_destination.
    """
    ...


def insert_default_checklist(doc: "DecommissionRequest") -> None:
    """Auto-insert 7 default checklist items khi tạo DR.
    
    Args:
        doc: Decommission Request mới, chưa saved.
    """
    ...


def check_retirement_candidates() -> None:
    """Scheduler job: daily check và flag retirement candidates.
    
    Chạy hàng ngày lúc 07:00. Gửi notification cho HTM Manager nếu có asset mới
    đạt ngưỡng retirement candidate.
    """
    ...


def check_overdue_dr() -> None:
    """Scheduler job: daily check DR quá hạn SLA.
    
    - DR mở > 45 ngày: notify HTM Manager
    - Pending Tech Review > 5 ngày: escalate CMMS Admin
    - Pending Decommission chưa phê duyệt > 7 ngày: escalate VP Block2
    """
    ...
```

### 7.2 Validation Flow Detail

```
validate_suspension_request(doc)
  ├── _br01_check_active_work_orders(doc)
  │     └── frappe.db.count("Work Order", filters={
  │               "asset": doc.asset,
  │               "docstatus": 1,          # submitted
  │               "status": ("not in", ["Completed", "Cancelled"])
  │           })
  │           → nếu count > 0: frappe.throw("Không thể ngừng sử dụng: còn {n} WO mở...")
  │
  ├── _br02_check_duplicate_dr(doc)
  │     └── frappe.db.exists("Decommission Request", {
  │               "asset": doc.asset,
  │               "docstatus": ("!=", 2),  # not cancelled
  │               "name": ("!=", doc.name)
  │           })
  │           → nếu tồn tại: frappe.throw("Đã có phiếu DR đang xử lý cho thiết bị này...")
  │
  ├── _br03_bio_hazard_clearance(doc)
  │     └── if doc.biological_hazard and not doc.bio_hazard_clearance:
  │             frappe.throw("Lỗi BR-13-03: Bắt buộc khai báo biện pháp xử lý sinh học...")
  │
  ├── _br04_regulatory_clearance(doc)
  │     └── if doc.regulatory_clearance_required and not doc.regulatory_clearance_doc:
  │             frappe.throw("Lỗi BR-13-04: Bắt buộc upload file giấy phép pháp lý...")
  │
  ├── _br06_residual_risk_required(doc)
  │     └── Chỉ check nếu workflow_state đang rời "Pending Tech Review":
  │           if not doc.residual_risk_level:
  │               frappe.throw("Lỗi BR-13-06: Bắt buộc đánh giá Residual Risk Level...")
  │
  ├── _br07_high_risk_needs_replacement_review(doc)
  │     └── if doc.residual_risk_level in ("High", "Critical") and not doc.replacement_needed:
  │             frappe.msgprint("Cảnh báo BR-13-07: Rủi ro cao/nghiêm trọng — cần thực hiện Replacement Review.")
  │
  ├── _br09_validate_transfer_location(doc)
  │     └── if doc.outcome == "Transfer" and not frappe.db.exists("Location", doc.transfer_to_location):
  │             frappe.throw("Lỗi BR-13-09: Vị trí nhận không hợp lệ...")
  │
  └── _br10_transfer_requires_receiving_officer(doc)
        └── if doc.outcome == "Transfer" and not doc.receiving_officer:
                frappe.throw("Lỗi BR-13-10: Bắt buộc điền người tiếp nhận khi điều chuyển...")
```

### 7.3 on_submit Flow

```
on_submit_handler(doc)
  ├── if outcome == "Transfer":
  │     _execute_transfer(doc)
  │       ├── frappe.db.set_value("AC Asset", doc.asset, {
  │       │       "status": "Transferred",
  │       │       "location": doc.transfer_to_location
  │       │   })
  │       └── _confirm_transfer_detail(doc)
  │
  ├── else (Suspend / Retire):
  │     _execute_suspension(doc)
  │       └── frappe.db.set_value("AC Asset", doc.asset, "status", "Suspended")
  │
  ├── log_lifecycle_event(doc, event_type, from_status, to_status)
  │
  └── if outcome == "Retire":
        _trigger_imm14(doc)
          └── frappe.get_doc({
                  "doctype": "Decommission Request",   # IMM-14 DocType
                  "asset": doc.asset,
                  "suspension_request": doc.name,
                  "status": "Draft",
                  "archive_date": frappe.utils.nowdate(),
              }).insert(ignore_permissions=True)
```

---

## 8. Repository Extensions: `assetcore/repositories/asset_repo.py`

```python
def get_asset_open_work_orders(asset_name: str) -> list[dict]:
    """Lấy danh sách WO đang mở trên asset.
    
    Args:
        asset_name: Tên AC Asset.
    Returns:
        list[dict]: Mỗi dict gồm name, status, work_order_type.
    """
    ...


def get_asset_maintenance_cost_total(asset_name: str) -> float:
    """Tính tổng chi phí bảo trì tích lũy từ all WO Completed.
    
    Args:
        asset_name: Tên AC Asset.
    Returns:
        float: Tổng cost (VNĐ).
    """
    ...


def get_asset_failure_count_12m(asset_name: str) -> int:
    """Đếm số lần hỏng hóc (CM WO) trong 12 tháng gần nhất.
    
    Args:
        asset_name: Tên AC Asset.
    Returns:
        int: Số lần hỏng.
    """
    ...


def get_asset_downtime_percent_12m(asset_name: str) -> float:
    """Tính % downtime do hỏng hóc trong 12 tháng.
    
    Args:
        asset_name: Tên AC Asset.
    Returns:
        float: Percent (0-100).
    """
    ...


def flag_retirement_candidate(asset_name: str, reason: str) -> None:
    """Đánh dấu asset là retirement candidate.
    
    Args:
        asset_name: Tên AC Asset.
        reason: Lý do flag (e.g. "maintenance_cost_ratio > 75%").
    """
    frappe.db.set_value("AC Asset", asset_name, {
        "is_retirement_candidate": 1,
        "retirement_flag_reason": reason,
        "retirement_flagged_date": frappe.utils.nowdate(),
    })
```

---

## 9. Scheduler Jobs

| Job Function | Cron | Logic | Recipient |
|---|---|---|---|
| `assetcore.services.imm13.check_retirement_candidates` | Daily 07:00 | So sánh assets vs thresholds (tuổi, cost ratio, failure count, downtime); flag mới → notify HTM Manager | HTM Manager |
| `assetcore.services.imm13.check_overdue_dr` | Daily 08:00 | DR > 45 ngày tổng cộng; Pending Tech > 5 ngày; Pending Decommission > 7 ngày | Theo SLA escalation table |

```python
# assetcore/config/scheduler_events.py (thêm vào existing)
scheduler_events = {
    "daily": [
        "assetcore.services.imm13.check_retirement_candidates",
        "assetcore.services.imm13.check_overdue_dr",
    ]
}
```

---

## 10. Workflow JSON Spec

```json
{
  "name": "Decommission Request",
  "document_type": "Decommission Request",
  "workflow_name": "IMM-13 Suspension & Transfer Workflow",
  "is_active": 1,
  "override_status": 0,
  "send_email_alert": 1,
  "workflow_state_field": "workflow_state",
  "states": [
    {"state": "Draft",                   "doc_status": "0", "allow_edit": "IMM HTM Manager"},
    {"state": "Pending Tech Review",     "doc_status": "0", "allow_edit": "IMM Biomed Engineer"},
    {"state": "Under Replacement Review","doc_status": "0", "allow_edit": "IMM HTM Manager"},
    {"state": "Approved for Transfer",   "doc_status": "0", "allow_edit": "IMM Network Manager"},
    {"state": "Transfer In Progress",    "doc_status": "0", "allow_edit": "IMM Network Manager"},
    {"state": "Transferred",             "doc_status": "1", "allow_edit": ""},
    {"state": "Pending Decommission",    "doc_status": "0", "allow_edit": "IMM CMMS Admin"},
    {"state": "Completed",               "doc_status": "1", "allow_edit": ""},
    {"state": "Cancelled",               "doc_status": "2", "allow_edit": ""}
  ],
  "transitions": [
    {
      "state": "Draft",
      "action": "Gửi đánh giá kỹ thuật",
      "next_state": "Pending Tech Review",
      "allowed": "IMM HTM Manager",
      "condition": "doc.asset and doc.suspension_reason and doc.reason_details"
    },
    {
      "state": "Pending Tech Review",
      "action": "Hoàn thành đánh giá kỹ thuật",
      "next_state": "Under Replacement Review",
      "allowed": "IMM Biomed Engineer",
      "condition": "doc.technical_reviewer and doc.residual_risk_level and doc.tech_review_notes"
    },
    {
      "state": "Pending Tech Review",
      "action": "Từ chối - Có thể sửa chữa",
      "next_state": "Cancelled",
      "allowed": "IMM Biomed Engineer",
      "condition": "doc.rejection_reason"
    },
    {
      "state": "Under Replacement Review",
      "action": "Quyết định Điều chuyển",
      "next_state": "Approved for Transfer",
      "allowed": "IMM HTM Manager",
      "condition": "doc.outcome == 'Transfer' and doc.transfer_to_location and doc.receiving_officer"
    },
    {
      "state": "Under Replacement Review",
      "action": "Quyết định Ngừng / Retire",
      "next_state": "Pending Decommission",
      "allowed": "IMM HTM Manager",
      "condition": "doc.outcome in ('Suspend', 'Retire')"
    },
    {
      "state": "Approved for Transfer",
      "action": "Bắt đầu điều chuyển",
      "next_state": "Transfer In Progress",
      "allowed": "IMM Network Manager"
    },
    {
      "state": "Transfer In Progress",
      "action": "Hoàn thành điều chuyển",
      "next_state": "Transferred",
      "allowed": "IMM CMMS Admin",
      "condition": "doc.docstatus == 1"
    },
    {
      "state": "Pending Decommission",
      "action": "Phê duyệt ngừng sử dụng",
      "next_state": "Pending Decommission",
      "allowed": "IMM VP Block2",
      "condition": "doc.approved_by and doc.approval_notes"
    },
    {
      "state": "Pending Decommission",
      "action": "Submit - Hoàn tất ngừng sử dụng",
      "next_state": "Completed",
      "allowed": "IMM CMMS Admin",
      "condition": "doc.approved == 1 and doc.docstatus == 1"
    },
    {
      "state": "Pending Decommission",
      "action": "Từ chối - Hủy phiếu",
      "next_state": "Cancelled",
      "allowed": "IMM VP Block2",
      "condition": "doc.rejection_reason"
    }
  ]
}
```

---

## 11. Integration Events Specs

### 11.1 IMM-12 Chronic Failure → Auto-flag Retirement Candidate

```python
# Trigger: on_submit của CM Work Order (IMM-12)
# File: assetcore/events/work_order_events.py

def on_submit_cm_work_order(doc, method):
    """Khi submit CM WO, check nếu asset đạt retirement threshold."""
    from assetcore.repositories.asset_repo import get_asset_failure_count_12m
    from assetcore.services.imm13 import flag_retirement_candidate_if_threshold

    if doc.work_order_type == "Corrective Maintenance":
        failure_count = get_asset_failure_count_12m(doc.asset)
        if failure_count >= 5:  # BR threshold
            flag_retirement_candidate_if_threshold(
                doc.asset,
                reason=f"Số lần hỏng hóc trong 12 tháng: {failure_count} (ngưỡng: 5)"
            )
```

### 11.2 DR on_submit (Transfer) → Update Asset Location

```python
# Trong on_submit_handler khi outcome == "Transfer"
frappe.db.set_value("AC Asset", doc.asset, {
    "status": "Transferred",
    "location": doc.transfer_to_location,
    "department": doc.transfer_to_department,
})

# Tạo Asset Transfer record (ERPNext core)
frappe.get_doc({
    "doctype": "Asset Movement",
    "asset": doc.asset,
    "purpose": "Transfer",
    "to_location": doc.transfer_to_location,
    "transaction_date": frappe.utils.nowdate(),
    "reference_doctype": "Decommission Request",
    "reference_name": doc.name,
}).insert(ignore_permissions=True)
```

### 11.3 DR on_submit (Retire) → Trigger IMM-14

```python
# Trong on_submit_handler khi outcome == "Retire"
imm14_doc = frappe.get_doc({
    "doctype": "Asset Archive Record",     # IMM-14 DocType
    "asset": doc.asset,
    "suspension_request": doc.name,
    "archive_date": frappe.utils.nowdate(),
    "archived_by": frappe.session.user,
    "retention_years": 10,
    "status": "Draft",
    "source_module": "IMM-13",
})
imm14_doc.insert(ignore_permissions=True)
frappe.publish_realtime(
    "imm14_triggered",
    {"asset": doc.asset, "dr_name": doc.name, "imm14_name": imm14_doc.name},
    user=frappe.session.user
)
```

---

## 12. Database Indexes

```sql
-- Decommission Request
CREATE INDEX idx_dr_asset_state
    ON `tabDecommission Request` (asset, workflow_state, docstatus);

CREATE INDEX idx_dr_creation
    ON `tabDecommission Request` (creation);

CREATE INDEX idx_dr_outcome
    ON `tabDecommission Request` (outcome, docstatus);

-- Suspension Checklist Item
CREATE INDEX idx_sci_parent
    ON `tabSuspension Checklist Item` (parent, completed);

-- Transfer Detail
CREATE INDEX idx_td_parent
    ON `tabTransfer Detail` (parent);

-- Asset (extensions)
CREATE INDEX idx_asset_retirement_candidate
    ON `tabAC Asset` (is_retirement_candidate, status);
```

---

## 13. Permission Matrix (Frappe Roles)

```json
[
  {
    "role": "IMM HTM Manager",
    "read": 1, "write": 1, "create": 1, "delete": 0,
    "submit": 0, "cancel": 0, "amend": 0,
    "report": 1, "export": 1, "print": 1
  },
  {
    "role": "IMM Biomed Engineer",
    "read": 1, "write": 1, "create": 0, "delete": 0,
    "submit": 0, "cancel": 0,
    "if_owner": 0,
    "permlevel": 1
  },
  {
    "role": "IMM QA Officer",
    "read": 1, "write": 1, "create": 0,
    "permlevel": 1
  },
  {
    "role": "IMM Finance",
    "read": 1, "write": 1, "create": 0,
    "permlevel": 2
  },
  {
    "role": "IMM Network Manager",
    "read": 1, "write": 1, "create": 0, "submit": 0
  },
  {
    "role": "IMM VP Block2",
    "read": 1, "write": 0, "submit": 1, "cancel": 0,
    "report": 1, "export": 1, "print": 1
  },
  {
    "role": "IMM CMMS Admin",
    "read": 1, "write": 1, "create": 1, "delete": 1,
    "submit": 1, "cancel": 1, "amend": 1,
    "report": 1, "export": 1, "print": 1
  }
]
```

---

*End of Technical Design v2.0.0 — IMM-13 Ngừng sử dụng và Điều chuyển*
