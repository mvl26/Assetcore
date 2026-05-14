# IMM-05 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-05 — Asset Document Repository |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |

---

## 1. Overview

### 1.1 Layered architecture

```
Request (HTTP / Workflow Action / Scheduler)
    │
    ▼
API Layer  (assetcore/api/imm05.py — 14 endpoints)
    │   @frappe.whitelist()
    ▼
Controller (assetcore/.../doctype/asset_document/asset_document.py)
    │   validate(), before_save(), on_update(), on_trash()
    │   11 VR + business logic (archive_old_versions, update_asset_completeness)
    ▼
Frappe ORM → MariaDB (tabAsset Document, tabDocument Request, tabRequired Document Type)
    │
    ▼
Side effects:
  - Frappe Version (auto, track_changes=1)
  - Compliance tính on-the-fly từ `tabAsset Document.workflow_state` (v3: không còn custom_document_status/custom_doc_completeness_pct trên AC Asset)
  - Expiry Alert Log (created bởi scheduler)
```

> **Tech-debt:** Service layer `services/imm05.py` chưa tồn tại. Logic nằm trong controller + `tasks.py`. Khi refactor, di chuyển: `archive_old_versions`, `update_asset_completeness`, `_compute_document_status`.

### 1.2 Files

| File | Vai trò |
|---|---|
| `assetcore/assetcore/doctype/asset_document/asset_document.json` | DocType schema (30 fields, 12 sections, 7 roles) |
| `assetcore/assetcore/doctype/asset_document/asset_document.py` | Controller (`AssetDocument` class, 11 VR + business methods) |
| `assetcore/assetcore/doctype/asset_document/asset_document.js` | Form script (UI behavior) |
| `assetcore/assetcore/doctype/document_request/document_request.json` | Document Request DocType |
| `assetcore/assetcore/doctype/required_document_type/required_document_type.json` | Master config |
| `assetcore/assetcore/workflow/imm_05_document_workflow.json` | Workflow JSON (6 states, 10 transitions) |
| `assetcore/api/imm05.py` | 14 REST endpoints |
| `assetcore/tasks.py` | 3 scheduler functions IMM-05 |

---

## 2. DocType Schema

### 2.1 Asset Document (`tabAsset Document`)

**Config:**

| Property | Value |
|---|---|
| name | Asset Document |
| module | AssetCore |
| autoname | `format:DOC-{asset_ref}-{YYYY}-{#####}` |
| naming_rule | Expression |
| is_submittable | 0 |
| track_changes | 1 |
| track_views | 1 |
| title_field | `doc_type_detail` |
| sort_field | `modified` (DESC) |
| search_fields | `asset_ref,doc_type_detail,doc_number` |

**Fields (30 — group theo section):**

#### Section: Liên kết Thiết bị

| # | fieldname | fieldtype | label | options | reqd | read_only | in_list_view | search_index |
|---|---|---|---|---|:---:|:---:|:---:|:---:|
| 1 | workflow_state | Link | Trạng thái | Workflow State | — | 1 | 1 | 1 |
| 2 | asset_ref | Link | Tài sản | AC Asset | * | — | 1 | 1 |
| 3 | model_ref | Link | Model Thiết bị | IMM Device Model | — | — | — | 1 |
| 4 | is_model_level | Check | Áp dụng toàn bộ Model | — | — | — | — | — |
| 5 | clinical_dept | Link | Khoa / Phòng | AC Department | — | 1 | — | — |
| 6 | source_commissioning | Link | Phiếu Commissioning nguồn | Asset Commissioning | — | 1 | — | — |
| 7 | source_module | Data | Module nguồn | — | — | 1 | — | — |

`clinical_dept` fetch_from `asset_ref.location`.

#### Section: Phân loại Tài liệu

| # | fieldname | fieldtype | options | reqd | in_list_view |
|---|---|---|---|:---:|:---:|
| 8 | doc_category | Select | Legal / Technical / Certification / Training / QA | * | 1 |
| 9 | doc_type_detail | Data | — | * | 1 |
| 10 | doc_number | Data | — | * | — (search_index 1) |
| 11 | version | Data | default "1.0" | * | — |

#### Section: Thông tin Hiệu lực

| # | fieldname | fieldtype | reqd | read_only | in_list_view | search_index |
|---|---|---|:---:|:---:|:---:|:---:|
| 12 | issued_date | Date | * | — | — | — |
| 13 | expiry_date | Date | — | — | 1 | 1 |
| 14 | issuing_authority | Data | — | — | — | — |
| 15 | days_until_expiry | Int | — | 1 | — | — |
| 16 | is_expired | Check | — | 1 | — | — |

#### Section: File đính kèm

| # | fieldname | fieldtype | reqd | read_only |
|---|---|---|:---:|:---:|
| 17 | file_attachment | Attach | * | — |
| 18 | file_name_display | Data | — | 1 |

#### Section: Phê duyệt

| # | fieldname | fieldtype | options | read_only |
|---|---|---|---|:---:|
| 19 | approved_by | Link | User | 1 |
| 20 | approval_date | Date | — | 1 |
| 21 | rejection_reason | Small Text | — | — |

#### Section: Version Control

| # | fieldname | fieldtype | options | read_only |
|---|---|---|---|:---:|
| 22 | superseded_by | Link | Asset Document | 1 |
| 23 | archived_by_version | Data | — | 1 |
| 24 | archive_date | Date | — | 1 |
| 25 | change_summary | Small Text | — | — |

#### Section: Kiểm soát Quyền truy cập

| # | fieldname | fieldtype | options | default | in_list_view |
|---|---|---|---|---|:---:|
| 26 | visibility | Select | Public / Internal_Only | Public | 1 |

#### Section: Miễn đăng ký NĐ98

| # | fieldname | fieldtype |
|---|---|---|
| 27 | is_exempt | Check |
| 28 | exempt_reason | Small Text |
| 29 | exempt_proof | Attach |

#### Section: Ghi chú

| # | fieldname | fieldtype |
|---|---|---|
| 30 | notes | Text Editor |

**Permissions:**

| Role | read | write | create | cancel | amend | delete |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| HTM Technician | 1 | 1 | 1 | — | — | — |
| Biomed Engineer | 1 | 1 | 1 | — | — | — |
| Tổ HC-QLCL | 1 | 1 | 1 | — | — | — |
| Workshop Head | 1 | 1 | 1 | 1 | 1 | — |
| VP Block2 | 1 | 1 | — | 1 | — | — |
| CMMS Admin | 1 | 1 | 1 | 1 | 1 | 1 |
| Clinical Head | 1 | — | — | — | — | — |

### 2.2 Document Request (`tabDocument Request`)

| Property | Value |
|---|---|
| autoname | `format:DOCREQ-{YYYY}-{MM}-{#####}` |
| is_submittable | 0 |
| track_changes | 1 |
| title_field | `doc_type_required` |
| sort_field | `due_date` (ASC) |

**Fields:**

| # | fieldname | fieldtype | options | reqd | default |
|---|---|---|---|:---:|---|
| 1 | asset_ref | Link → Asset | — | * | — |
| 2 | doc_type_required | Data | — | * | — |
| 3 | doc_category | Select | Legal/Technical/Certification/Training/QA | * | — |
| 4 | status | Select | Open/In_Progress/Overdue/Fulfilled/Cancelled | * | Open |
| 5 | priority | Select | Low/Medium/High/Critical | — | Medium |
| 6 | assigned_to | Link → User | — | * | — |
| 7 | due_date | Date | — | * | — |
| 8 | source_type | Select (read_only) | Manual/Dashboard/GW2_Block/Scheduler | — | Manual |
| 9 | escalation_sent | Check (read_only) | — | — | — |
| 10 | request_note | Small Text | — | — | — |
| 11 | fulfilled_by | Link → Asset Document (read_only) | — | — | — |

### 2.3 Required Document Type (`tabRequired Document Type`)

| Property | Value |
|---|---|
| autoname | `field:type_name` |
| is_submittable | 0 |

**Fields:**

| # | fieldname | fieldtype | options | reqd |
|---|---|---|---|:---:|
| 1 | type_name | Data | — | * |
| 2 | doc_category | Select | Legal/Technical/Certification/Training/QA | * |
| 3 | has_expiry | Check | — | — |
| 4 | is_mandatory | Check | — | — |
| 5 | applies_to_asset_category | Link → AC Asset Category | — | — |
| 6 | applies_when_radiation | Check | — | — |

---

## 3. Custom Fields (trên `Asset`)

**v3 change:** Các `custom_*` fields trên Asset đã bị bỏ. Compliance được tính on-the-fly bằng SQL EXISTS subquery trên `tabAsset Document.workflow_state` (xem `api/imm05.get_compliance_by_dept`). Lý do: tránh drift giữa cached status và source of truth.

| Compliance class | Định nghĩa (tính on-the-fly)                                        |
| ---------------- | ------------------------------------------------------------------- |
| Compliant        | Asset có ít nhất 1 `Asset Document` với `workflow_state = 'Active'` |
| Incomplete       | Không có Active doc, nhưng có ít nhất 1 `Draft`                     |
| Non-Compliant    | Có ít nhất 1 `Rejected`                                             |
| Expiring_Soon    | Active doc với `expiry_date <= today + 90d`                         |

---

## 4. Validation Rules

Implement trong `AssetDocument.validate()` (gọi 11 method `vr_XX_*`):

| VR | Method | Trigger | Logic |
|---|---|---|---|
| VR-01 | `vr_01_expiry_after_issued` | `validate` | `expiry_date > issued_date` |
| VR-02 | `vr_02_unique_doc_number` | `validate` | UNIQUE (asset_ref + doc_type_detail + doc_number) |
| VR-03 | `vr_03_file_required_for_review` | `before_save` | `workflow_state="Pending_Review"` ⇒ `file_attachment` not empty |
| VR-04 | `vr_04_legal_requires_authority` | `validate` | `doc_category="Legal"` ⇒ `issuing_authority` reqd |
| VR-05 | `vr_05_no_state_regression` | `validate` | Block change if previous state IN (Archived, Expired) |
| VR-06 | `vr_06_rejection_reason_required` | `before_save` | `workflow_state="Rejected"` ⇒ `rejection_reason` reqd |
| VR-07 | `vr_07_legal_requires_expiry` | `validate` | `doc_category IN (Legal, Certification)` ⇒ `expiry_date` reqd |
| VR-08 | `vr_08_file_format_check` | `validate` | extension IN {.pdf, .jpg, .jpeg, .png, .docx} |
| VR-09 | `vr_09_change_summary_required` | `validate` | `version != "1.0"` ⇒ `change_summary` reqd |
| VR-10 | `vr_10_exempt_fields_required` | `validate` | `is_exempt=1` ⇒ `exempt_reason` + `exempt_proof` reqd |
| VR-11 | `vr_11_exempt_doc_type_check` | `validate` | `is_exempt=1` ⇒ `doc_type_detail IN EXEMPT_DOC_TYPES` |

`EXEMPT_DOC_TYPES = {"Chứng nhận đăng ký lưu hành", "Giấy phép nhập khẩu"}`
`ALLOWED_FILE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}`

---

## 5. Hooks (Controller lifecycle)

```python
class AssetDocument(Document):
    def validate(self):
        # 8 VR methods + auto_fetch_model_and_dept

    def before_save(self):
        # VR-03, VR-06, set_computed_fields()

    def on_update(self):
        if self.workflow_state == "Active":
            self.archive_old_versions()
            self.update_asset_completeness()
        if self.workflow_state in ("Expired", "Active"):
            self.update_asset_completeness()

    def on_trash(self):
        frappe.throw("Không được phép xóa tài liệu...")  # BR-05-02
```

**Business methods:**

| Method | Logic |
|---|---|
| `auto_fetch_model_and_dept()` | Đọc `Asset.item_code` → `model_ref`; `Asset.location` → `clinical_dept` |
| `set_computed_fields()` | `days_until_expiry = expiry_date - today`; `is_expired = (days < 0)`; `file_name_display` |
| `archive_old_versions()` | Query Active docs cùng (asset_ref + doc_type_detail) ≠ self → set Archived + `superseded_by`, `archived_by_version`, `archive_date` |
| `update_asset_completeness()` | Tính `pct = active_required_count / total_required × 100`; build `document_status` qua `_compute_document_status()`; cập nhật 4 custom fields trên Asset |

**`_compute_document_status` logic:**

```
if is_exempt:                return "Compliant (Exempt)"
if has_expired:              return "Non-Compliant"
if has_expiring (≤30 days):  return "Expiring_Soon"
if pct >= 100:               return "Compliant"
else:                        return "Incomplete"
```

---

## 6. API Layer

Xem `IMM-05_API_Interface.md` cho đặc tả 14 endpoints. Module Python: `assetcore/api/imm05.py`.

Constants quan trọng:

```python
_DOCTYPE = "Asset Document"
_INTERNAL_ONLY_ROLES = {"HTM Technician", "Tổ HC-QLCL", "Biomed Engineer",
                        "Workshop Head", "CMMS Admin", "System Manager"}
_APPROVE_ROLES = {"Biomed Engineer", "Tổ HC-QLCL", "CMMS Admin"}
_EXEMPT_ROLES = {"Tổ HC-QLCL", "CMMS Admin", "Workshop Head"}
```

Helper:

- `_can_see_internal()` — bool
- `_apply_visibility_filter(filters)` — inject `visibility IN (Public, "", null)` cho non-internal users

---

## 7. Schedulers

File: `assetcore/tasks.py`

### 7.1 `check_document_expiry()` — Daily 00:30

```
For each milestone IN (90, 60, 30, 0):
    target_date = today + milestone days
    Query Asset Document WHERE workflow_state='Active' AND expiry_date=target_date
    For each doc:
        If Expiry Alert Log đã có (asset_document=doc.name, alert_date=today): skip
        Else: tạo Expiry Alert Log {milestone, expiry_date, asset_document, alert_date=today}
        If milestone == 0: doc.workflow_state = 'Expired'; doc.save()
        Send email theo level (90=Info, 60=Warning, 30=Critical, 0=Danger)
```

### 7.2 `update_asset_completeness()` — Daily 01:00

Batch chạy `update_asset_completeness()` (controller method) trên mọi Asset có doc thay đổi gần đây. Tính nearest_expiry qua SQL aggregate.

### 7.3 `check_overdue_document_requests()` — Daily

```
Query Document Request WHERE status='Open' AND due_date < today
For each req:
    req.status = 'Overdue'
    req.escalation_sent = 1
    Email Workshop Head + VP Block2
```

---

## 8. Workflow JSON

File: `assetcore/assetcore/workflow/imm_05_document_workflow.json`

**States (6):**

| state | doc_status | type |
|---|---|---|
| Draft | 0 | Success |
| Pending Review | 0 | Warning |
| Active | 1 | Success |
| Rejected | 0 | Danger |
| Archived | 2 | Default |
| Expired | 1 | Danger |

**Transitions (10):**

| action | from → to | allowed |
|---|---|---|
| Gửi duyệt | Draft → Pending Review | Biomed Engineer |
| Gửi duyệt | Draft → Pending Review | CMMS Admin |
| Phê duyệt | Pending Review → Active | Tổ HC-QLCL |
| Phê duyệt | Pending Review → Active | CMMS Admin |
| Từ chối | Pending Review → Rejected | Tổ HC-QLCL |
| Từ chối | Pending Review → Rejected | CMMS Admin |
| Gửi lại | Rejected → Pending Review | Biomed Engineer |
| Gửi lại | Rejected → Pending Review | CMMS Admin |
| Lưu trữ | Active → Archived | CMMS Admin |
| Hủy bỏ | Draft → Archived | CMMS Admin |

`workflow_state_field = "workflow_state"`. `is_active = 1`. `send_email_alert = 0` (notify do tasks.py xử lý).

---

## 9. Fixtures & hooks.py

### 9.1 Required fixtures

| File | Nội dung |
|---|---|
| `fixtures/imm00_custom_fields.json` | 4 custom field trên Asset (completeness, status, summary, nearest_expiry) |
| `workflow/imm_05_document_workflow.json` | Workflow LIVE |
| `Required Document Type` records | Seed danh sách bắt buộc (CN ĐK lưu hành, CO, CQ, User Manual, Warranty, Giấy phép nhập khẩu, Giấy phép bức xạ) |

### 9.2 hooks.py registration

```python
scheduler_events = {
    "daily": [
        "assetcore.tasks.check_document_expiry",
        "assetcore.tasks.update_asset_completeness",
        "assetcore.tasks.check_overdue_document_requests",
        # ...
    ]
}

# doc_events: hiện không có entry IMM-05 trong hooks.py (controller tự gọi)
# IMM-04 hook gọi auto-import sang IMM-05 (xem IMM-04 docs)
```

---

## 10. Database Indexes

Frappe tự tạo index theo `search_index=1` trong DocType JSON. IMM-05 có:

| Bảng | Cột | Lý do |
|---|---|---|
| `tabAsset Document` | `workflow_state` | Filter list, scheduler |
| `tabAsset Document` | `asset_ref` | get_asset_documents, completeness query |
| `tabAsset Document` | `model_ref` | get docs theo model |
| `tabAsset Document` | `expiry_date` | check_document_expiry, dashboard timeline |
| `tabAsset Document` | `doc_number` | VR-02 unique check |
| `tabDocument Request` | `asset_ref` | get_document_requests |
| `tabDocument Request` | `status` | filter dashboard |

**Khuyến nghị composite index (manual SQL):**

```sql
CREATE INDEX idx_asd_asset_type_state
  ON `tabAsset Document` (asset_ref, doc_type_detail, workflow_state);

CREATE INDEX idx_asd_state_expiry
  ON `tabAsset Document` (workflow_state, expiry_date);
```

---

## 11. Migration Notes

| Version | Migration cần |
|---|---|
| 1.x → 2.0.0 | Field `change_summary`, `is_exempt`, `exempt_reason`, `exempt_proof`, `archived_by_version`, `archive_date`, `is_model_level` đã có schema chuẩn — chạy `bench migrate`. Custom fields trên Asset cần verify qua fixtures `imm00_custom_fields.json`. |

**Backfill scripts** (manual nếu cần):

```python
# Set is_exempt=0 default cho tất cả docs cũ
frappe.db.sql("UPDATE `tabAsset Document` SET is_exempt=0 WHERE is_exempt IS NULL")

# Set version="1.0" default
frappe.db.sql("UPDATE `tabAsset Document` SET version='1.0' WHERE version IS NULL OR version=''")

# Recompute days_until_expiry và is_expired
for doc in frappe.get_all("Asset Document", filters={"expiry_date": ["is", "set"]}, pluck="name"):
    d = frappe.get_doc("Asset Document", doc)
    d.set_computed_fields()
    d.db_update()
```

---

## 12. ERD

```
┌────────────────┐       ┌──────────────────┐       ┌─────────────────────┐
│     Asset      │ 1───* │  Asset Document  │ *───1 │ Workflow State      │
│ (Frappe core)  │       │                  │       │ (Frappe core)       │
└────────┬───────┘       └────┬─────────┬───┘       └─────────────────────┘
         │                    │         │
         │ 1                  │ 1       │ 1
         │                    │         │
         │                    │         ▼ (superseded_by self-ref)
         │                    │      ┌──────────────────┐
         │                    │      │ Asset Document   │ (older version, Archived)
         │                    │      └──────────────────┘
         │                    │
         │                    │ * (source_commissioning)
         │                    ▼
         │              ┌────────────────────┐
         │              │ Asset Commissioning│ (IMM-04)
         │              └────────────────────┘
         │
         │ 1───*
         ▼
┌─────────────────────┐                    ┌─────────────────────────┐
│ Document Request    │                    │ Required Document Type  │
│  status, due_date,  │                    │  type_name (PK),        │
│  fulfilled_by ───*──┼──────────────►     │  is_mandatory, etc.     │
└─────────────────────┘  fulfilled_by      └─────────────────────────┘
                         → Asset Document

       Compliance tính on-the-fly qua SQL EXISTS trên Asset Document.workflow_state
       (v3: không cache trên AC Asset — get_compliance_by_dept trong api/imm05.py)
```

---

## 13. State Diagram — Asset Document Workflow

```
              ┌─────────┐
              │  Draft  │ ◀── create_document
              └────┬────┘
                   │ "Gửi duyệt" (Biomed/CMMS Admin)
                   ▼
          ┌────────────────┐
          │ Pending Review │
          └────┬───────────┘
               │
       ┌───────┴───────┐
       │               │
"Phê duyệt"       "Từ chối" + reason (VR-06)
(Tổ HC-QLCL/CA)   (Tổ HC-QLCL/CA)
       │               │
       ▼               ▼
   ┌────────┐      ┌──────────┐
   │ Active │      │ Rejected │ ──── "Gửi lại" ──┐
   └────┬───┘      └──────────┘                  │
        │                                        │
        │                                        ▼
        │                              ┌────────────────┐
        │                              │ Pending Review │
        │                              └────────────────┘
        │
   ┌────┼─────────────┬──────────────┐
   │    │             │              │
   ▼    ▼             ▼              ▼
"Lưu  expiry_date  version mới   asset retired
trữ"  = 0 (auto)  được Active    (IMM-13)
   │     │           (auto)            │
   ▼     ▼            ▼                ▼
┌──────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐
│ Archived │  │ Expired │  │ Archived │  │ Archived │
└──────────┘  └─────────┘  └──────────┘  └──────────┘
                            (superseded_by set)

VR-05: Không cho phép thoát khỏi Archived/Expired (terminal).
```

---

## 14. Testing Strategy

| Test type | Target | Coverage |
|---|---|---|
| Unit (controller) | 11 VR + 4 business methods | 90% |
| API | 14 endpoints (success + error paths) | 100% endpoints |
| Workflow | 10 transitions với từng role | 100% |
| Scheduler | 3 jobs idempotent | Manual run + assertion |
| E2E | IMM-04 → IMM-05 auto-import; GW-2 gate; mark_exempt unblock | UAT script |

Test files: `assetcore/assetcore/doctype/asset_document/test_asset_document.py` (TBD).
