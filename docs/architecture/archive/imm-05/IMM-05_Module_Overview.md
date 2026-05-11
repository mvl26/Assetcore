# IMM-05 — Asset Document Repository

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-05 — Asset Document Repository |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |

---

## 1. Mục đích

IMM-05 là **Document Repository** tập trung quản lý toàn bộ hồ sơ kỹ thuật, pháp lý, kiểm định và đào tạo gắn với từng `Asset` (per-instance) hoặc `Item` (per-model) trong suốt vòng đời thiết bị y tế.

**Đặc điểm:**

| Đặc tính | Nội dung |
|---|---|
| Vai trò trong WHO HTM | Documentation & record keeping (HTM 3.2) — cross-cutting xuyên suốt từ Procurement → Decommission |
| Liên kết module | Vận hành **song song liên tục** với mọi module IMM-xx; là bộ điều kiện đầu vào cho GW-2 (IMM-04) |
| Compliance | NĐ 98/2021/NĐ-CP, ISO 13485:2016 §4.2 (Documentation), WHO HTM Annex 7 |
| Phạm vi audit | Mọi thao tác (upload, approve, reject, archive, expire, exempt) ghi version + audit trail |

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│                  Frappe Framework v15                            │
│   Workflow Engine · Version DocType · File · Scheduler · ORM     │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                      AssetCore App                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            IMM-05 Asset Document Repository              │   │
│  │                                                          │   │
│  │  DocTypes:                                               │   │
│  │    • Asset Document        (chính, naming DOC-...)       │   │
│  │    • Document Request      (task quản lý doc thiếu)      │   │
│  │    • Required Document Type (master config doc bắt buộc) │   │
│  │                                                          │   │
│  │  API:        assetcore/api/imm05.py  (14 endpoints)      │   │
│  │  Controller: assetcore/.../asset_document.py             │   │
│  │              (11 validation rules + business logic)      │   │
│  │  Workflow:   workflow/imm_05_document_workflow.json      │   │
│  │              (6 states · 10 transitions)                 │   │
│  │  Scheduler:  tasks.py                                    │   │
│  │     • check_document_expiry        daily 00:30           │   │
│  │     • update_asset_completeness    daily 01:00           │   │
│  │     • check_overdue_document_requests daily              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│   Tích hợp:                                                      │
│     IMM-04 ──▶ IMM-05  (auto-import doc khi commissioning)       │
│     IMM-05 ──▶ IMM-04  (cung cấp GW-2 compliance gate)           │
│     IMM-05 ──▶ IMM-08/09/11 (cung cấp manual, schematic, cert)   │
│     IMM-11 ──▶ IMM-05  (lưu chứng chỉ hiệu chuẩn sau cycle)      │
│     IMM-13 ◀── IMM-05  (auto-archive toàn bộ khi decommission)   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Primary DocType

| DocType | Naming | Mô tả |
|---|---|---|
| Asset Document | `format:DOC-{asset_ref}-{YYYY}-{#####}` | Hồ sơ tài liệu gắn Asset/Model — workflow 6-state, version control, exempt handling |
| Document Request | `format:DOCREQ-{YYYY}-{MM}-{#####}` | Task theo dõi tài liệu còn thiếu, deadline + leo thang |
| Required Document Type | `field:type_name` | Master config bộ hồ sơ bắt buộc (per item group / radiation flag) |

### 3.2 Cấu trúc field nhóm — Asset Document

| Section | Field chính |
|---|---|
| Liên kết Thiết bị | `asset_ref`, `model_ref`, `is_model_level`, `clinical_dept` (fetch), `source_commissioning`, `source_module` |
| Phân loại | `doc_category` (Legal/Technical/Certification/Training/QA), `doc_type_detail`, `doc_number`, `version` |
| Hiệu lực | `issued_date`, `expiry_date`, `issuing_authority`, `days_until_expiry`, `is_expired` |
| File | `file_attachment` (PDF/JPG/PNG/DOCX), `file_name_display` |
| Phê duyệt | `approved_by`, `approval_date`, `rejection_reason` |
| Version Control | `superseded_by`, `archived_by_version`, `archive_date`, `change_summary` |
| Quyền truy cập | `visibility` (Public / Internal_Only) |
| Exempt NĐ98 | `is_exempt`, `exempt_reason`, `exempt_proof` |

**Tổng:** 30 fields / 12 sections — chi tiết tại `IMM-05_Technical_Design.md` §2.

---

## 4. Service Functions / API Endpoints

File: `assetcore/api/imm05.py` — 14 endpoints whitelist:

| # | Endpoint | Method | Caller |
|---|---|---|---|
| 1 | `list_documents` | GET | UI list, dashboards |
| 2 | `get_document` | GET | UI detail |
| 3 | `create_document` | POST | UI create |
| 4 | `update_document` | POST | UI edit (Draft/Rejected) |
| 5 | `approve_document` | POST | Reviewer action (auto-archive cũ) |
| 6 | `reject_document` | POST | Reviewer action (yêu cầu reason) |
| 7 | `get_asset_documents` | GET | Asset docs tab — group theo category + completeness |
| 8 | `get_dashboard_stats` | GET | Dashboard KPIs + timeline + dept compliance |
| 9 | `get_expiring_documents` | GET | Báo cáo doc sắp hết hạn (N ngày) |
| 10 | `get_compliance_by_dept` | GET | Compliance % theo khoa |
| 11 | `get_document_history` | GET | Wrap Frappe Version DocType |
| 12 | `create_document_request` | POST | Tạo task tài liệu thiếu |
| 13 | `get_document_requests` | GET | Danh sách Document Request |
| 14 | `mark_exempt` | POST | Đánh dấu thiết bị Exempt NĐ98 |

> Service layer riêng `services/imm05.py` **chưa tồn tại** — business logic hiện nằm trong controller `asset_document.py` và `tasks.py`. Refactor sang service layer được track như tech-debt.

---

## 5. Workflow & Schedulers

### 5.1 Workflow States — `IMM-05 Document Workflow`

| State | doc_status | Type (badge) | Allow Edit |
|---|---|---|---|
| Draft | 0 | Success | Biomed Engineer |
| Pending Review | 0 | Warning | Biomed Engineer |
| Active | 1 | Success | CMMS Admin |
| Rejected | 0 | Danger | Biomed Engineer |
| Archived | 2 | Default | CMMS Admin |
| Expired | 1 | Danger | CMMS Admin |

> **Note:** Workflow JSON dùng `Pending Review` (có space). API code dùng `Pending_Review` (underscore) — controller map về cùng workflow_state field. UI hiển thị label tiếng Việt.

### 5.2 Transitions

| Action | From → To | Allowed Roles |
|---|---|---|
| Gửi duyệt | Draft → Pending Review | Biomed Engineer, CMMS Admin |
| Phê duyệt | Pending Review → Active | Tổ HC-QLCL, CMMS Admin |
| Từ chối | Pending Review → Rejected | Tổ HC-QLCL, CMMS Admin |
| Gửi lại | Rejected → Pending Review | Biomed Engineer, CMMS Admin |
| Lưu trữ | Active → Archived | CMMS Admin |
| Hủy bỏ | Draft → Archived | CMMS Admin |
| (auto) | Active → Expired | Scheduler `check_document_expiry` |
| (auto) | Active → Archived | Controller `archive_old_versions` khi version mới Active |

### 5.3 Scheduler Jobs — `assetcore/tasks.py`

| Job | Lịch | Hành vi | Đối tượng nhận email |
|---|---|---|---|
| `check_document_expiry` | Daily 00:30 | Quét Active docs hết hạn 90/60/30/0 ngày → tạo `Expiry Alert Log` (idempotent theo alert_date), auto-Expire khi days=0 | Workshop Head, Biomed Engineer, VP Block2 (theo mốc) |
| `update_asset_completeness` | Daily 01:00 | Batch tính `custom_doc_completeness_pct`, `custom_document_status`, `custom_nearest_expiry` cho mọi Asset | — |
| `check_overdue_document_requests` | Daily | Set `status = Overdue` cho Document Request quá `due_date`; gửi escalation Workshop Head + VP Block2 | Workshop Head, VP Block2 |

---

## 6. Roles & Permissions

| Role | Asset Document | Document Request | Quyền chính |
|---|---|---|---|
| HTM Technician | R/W/C | R/W/C | Upload, sửa Draft; thấy Internal_Only |
| Biomed Engineer | R/W/C | R/W/C | Submit duyệt; approve doc kỹ thuật |
| Tổ HC-QLCL | R/W/C | R/W/C | Approve/Reject; mark exempt; thấy Internal_Only |
| Workshop Head | R/W/C/Cancel/Amend | R/W/C/Delete | Quản lý kho hồ sơ; mark exempt |
| VP Block2 | R/W/Cancel | — | Phê duyệt cuối; nhận escalation |
| CMMS Admin | Full | Full | Quản trị, cấu hình, force action |
| Clinical Head | R (Public only) | — | Xem hồ sơ Public của khoa mình |

**Visibility filter:** Khi `visibility = Internal_Only`, chỉ user thuộc `_INTERNAL_ONLY_ROLES` (HTM Technician, Tổ HC-QLCL, Biomed Engineer, Workshop Head, CMMS Admin, System Manager) hoặc `Administrator/admin` mới thấy.

**Exempt permission:** Chỉ `_EXEMPT_ROLES` (Tổ HC-QLCL, CMMS Admin, Workshop Head) được gọi `mark_exempt`.

---

## 7. Business Rules

| ID | Business Rule | Enforce |
|---|---|---|
| BR-05-01 | Mỗi Asset chỉ có 1 `Active` doc per `doc_type_detail` — approve mới tự archive cũ | `archive_old_versions()` trên `on_update`; cũng chạy trong `approve_document` |
| BR-05-02 | Không xóa cứng document — chỉ archive | `on_trash()` throw |
| BR-05-03 | Expiry alert theo mốc 90/60/30/0 ngày, sinh `Expiry Alert Log` (idempotent) | Scheduler `check_document_expiry` |
| BR-05-04 | Auto-import từ IMM-04 khi `Asset Commissioning` chuyển `Clinical_Release` | Hook trên `asset_commissioning.on_submit` (IMM-04) |
| BR-05-05 | Bộ hồ sơ bắt buộc cấu hình qua `Required Document Type` master | `update_asset_completeness()` query `is_mandatory=1` |
| BR-05-06 | Doc `is_model_level=1` áp dụng chung cho mọi asset cùng `model_ref` | UI filter + report layer |
| BR-05-07 | **GW-2 Gate** — Block IMM-04 Submit nếu thiếu Chứng nhận ĐK lưu hành Active hoặc `is_exempt=1` | IMM-04 `asset_commissioning.validate()` query Asset Document |
| BR-05-08 | Exempt NĐ98 → `document_status = "Compliant (Exempt)"` | `_compute_document_status()` |
| BR-05-09 | `change_summary` bắt buộc khi `version != "1.0"` | VR-09 trong `validate()` |
| BR-05-10 | Doc `visibility = Internal_Only` ẩn với non-internal roles | `_apply_visibility_filter()` trong tất cả list endpoint |

---

## 8. Dependencies

| Module | Chiều | Liên kết |
|---|---|---|
| IMM-04 Installation | IN | `Asset Commissioning.on_submit(Clinical_Release)` → tạo Document Set baseline; ngược lại IMM-05 cấp GW-2 gate cho IMM-04 |
| IMM-08 PM | OUT | Service Manual, Spec Sheet (`doc_category=Technical`) |
| IMM-09 Repair | OUT | Schematic, Parts Catalog |
| IMM-11 Calibration | BOTH | Lưu chứng chỉ hiệu chuẩn sau mỗi cycle |
| IMM-10 Compliance Dashboard | OUT | `Asset.custom_document_status` đóng góp compliance score |
| IMM-13 Decommission | OUT | Auto-archive toàn bộ doc khi Asset chuyển Decommissioned |
| Frappe `Version` DocType | IN | `get_document_history` wrap để trả lịch sử thay đổi |

---

## 9. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| 3 DocTypes (Asset Document, Document Request, Required Document Type) | LIVE | Schema ổn định v2.0 |
| Workflow 6 state + 10 transition | LIVE | `imm_05_document_workflow.json` deployed |
| 14 API endpoints | LIVE | `api/imm05.py` |
| 11 Validation Rules (VR-01 → VR-11) trong controller | LIVE | `asset_document.py` |
| 3 Scheduler jobs | LIVE | `tasks.py` |
| Frontend UI (List, Detail, Create, Asset documents tab) | LIVE | `frontend/src/views/Document*.vue` |
| Email notification template | TODO | Hiện inline string trong `tasks.py` |
| Service layer `services/imm05.py` | TODO | Logic vẫn nằm trong controller (tech-debt) |
| Auto-import IMM-04 E2E test | PARTIAL | Code có, cần UAT đầy đủ |
| Dashboard frontend KPI panel | TODO | API ready, component chưa build |

---

## 10. QMS Mapping

| Yêu cầu | Nguồn | Cách đáp ứng |
|---|---|---|
| Document Control | ISO 13485 §4.2 | Workflow Draft → Review → Active, version control, audit trail |
| Traceability | WHO HTM | `source_commissioning`, `source_module`, Frappe Version |
| DHF/DMR | ISO 13485 §4.2.4 | Kho hồ sơ per-Asset + Required Document Type master |
| Đăng ký lưu hành TBYT | NĐ 98/2021/NĐ-CP | GW-2 gate + `is_exempt` flow |
| Cảnh báo hiệu lực | WHO HTM Annex 7 | Scheduler 90/60/30/0 + Expiry Alert Log |
| Kiểm soát truy cập | ISO 13485 §4.2.5 | `visibility` + role-based filter |
| Không xóa hồ sơ y tế | NĐ 98 + WHO HTM | BR-05-02 override `on_trash` |
