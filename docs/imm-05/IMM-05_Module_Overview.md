# IMM-05 — Quản lý Hồ sơ & Tuân thủ

**Module:** IMM-05 — Đăng ký, Cấp phép & Quản lý Hồ sơ Thiết bị Y tế
**Phiên bản:** 1.0
**Ngày cập nhật:** 2026-04-17
**Trạng thái:** IMPLEMENTED (core features done)

---

## Module Overview

IMM-05 là **Document Repository** tập trung quản lý toàn bộ hồ sơ kỹ thuật, pháp lý và kiểm định gắn với từng thiết bị y tế trong suốt vòng đời. Đây **không** phải module đơn lẻ — IMM-05 vận hành song song liên tục với tất cả module khác, từ khi thiết bị được mint tại IMM-04 đến khi thanh lý tại IMM-13/14.

DocType chính: **`Asset Document`** (naming: `DOC-.asset_ref.-.YYYY.-.#####`)

---

## Trạng thái Implementation

| Tính năng | Trạng thái | Ghi chú |
|-----------|:----------:|---------|
| Upload tài liệu & điền metadata | DONE | HTM Technician → Draft |
| Workflow Approve / Reject | DONE | API `approve_document`, `reject_document` |
| Version control (auto-archive cũ) | DONE | Trigger trong `approve_document` |
| Auto-import từ IMM-04 | PARTIAL | Logic viết trong `asset_commissioning.py`, cần test E2E |
| Expiry alerts scheduler (90/60/30/0 ngày) | DONE | `tasks.check_document_expiry()` |
| Batch update Asset completeness | DONE | `tasks.update_asset_completeness()` |
| Dashboard KPI API | DONE | `imm05.get_dashboard_stats()` |
| Document Request (yêu cầu tài liệu thiếu) | DONE | DocType + API `create_document_request` |
| Overdue Request escalation | DONE | `tasks.check_overdue_document_requests()` |
| Exempt handling (NĐ98 miễn đăng ký) | DONE | API `mark_exempt`, field `is_exempt` |
| Dashboard UI frontend | TODO | Spec có, chưa implement UI component |
| Email notification templates | TODO | Nội dung email còn inline string |
| Document Request tracking UI | TODO | API sẵn, chưa có form UI |

---

## Phạm vi

### In Scope

| Chức năng | Mô tả |
|-----------|-------|
| F-01: Document Repository | Kho hồ sơ per-Asset (instance) và per-Item (model) |
| F-02: Phân loại tài liệu | 5 nhóm: Legal, Technical, Certification, Training, QA |
| F-03: Metadata đầy đủ | Số hiệu, ngày cấp, expiry, version, cơ quan cấp, approver |
| F-04: Version control | Archive tự động version cũ khi version mới được duyệt |
| F-05: Auto-import từ IMM-04 | Kế thừa CO/CQ/Packing/Manual/Warranty/License khi Asset mint |
| F-06: Expiry alert | Scheduler daily: 90/60/30/0 ngày + Expiry Alert Log |
| F-07: Dashboard | KPI compliance, expiry timeline, completeness theo khoa |
| F-08: Audit trail | Mọi thao tác sinh record (upload, approve, archive, expire) |

### Out of Scope

| Chức năng | Module phụ trách |
|-----------|-----------------|
| Quản lý hợp đồng vendor | IMM-02 |
| Lịch đào tạo nhân viên | IMM-06 |
| Lịch hiệu chuẩn định kỳ | IMM-11 |
| CAPA management | IMM-16 |
| Electronic signature (chữ ký số) | v2.0 |
| FHIR/HIS integration | Phase 2 |

---

## Document Repository Structure

| Category | `doc_category` | Loại tài liệu cụ thể (`doc_type_detail`) |
|----------|---------------|------------------------------------------|
| Pháp lý | `Legal` | Giấy phép nhập khẩu, Giấy phép hoạt động, Chứng nhận đăng ký lưu hành, Giấy phép bức xạ |
| Kỹ thuật | `Technical` | Service Manual, User Manual (HDSD), Schematic, Spec Sheet, Parts Catalog |
| Kiểm định | `Certification` | Chứng chỉ hiệu chuẩn, Kết quả kiểm định, Biên bản đo kiểm, Chứng nhận CE/FDA |
| Đào tạo | `Training` | Tài liệu đào tạo, Biên bản đào tạo, Video hướng dẫn |
| Chất lượng | `QA` | CO - Chứng nhận Xuất xứ, CQ - Chứng nhận Chất lượng, Warranty Card, Packing List |

---

## Required Document Set (bắt buộc per Asset)

| # | Loại tài liệu | Bắt buộc | Có expiry? | Điều kiện |
|---|---------------|:--------:|:----------:|-----------|
| 1 | Chứng nhận đăng ký lưu hành | Có | Có | Bắt buộc theo NĐ98/2021 |
| 2 | CO - Chứng nhận Xuất xứ | Có | Không | — |
| 3 | CQ - Chứng nhận Chất lượng | Có | Không | — |
| 4 | User Manual (HDSD) | Có | Không | Per-model, áp dụng chung |
| 5 | Warranty Card | Có | Có | Thời hạn bảo hành |
| 6 | Giấy phép nhập khẩu | Conditional | Có | Nếu thiết bị nhập khẩu |
| 7 | Giấy phép bức xạ | Conditional | Có | Nếu `is_radiation_device = True` |

Cấu hình bộ hồ sơ bắt buộc qua master DocType **`Required Document Type`** (không hard-code).

---

## Workflow States

| State | Mô tả | Entry Condition | Exit Condition | Actor |
|-------|-------|-----------------|----------------|-------|
| `Draft` | Vừa upload, chưa review | Tạo mới hoặc import từ IMM-04 | Submit for Review | HTM Technician |
| `Pending_Review` | Đang chờ duyệt | `file_attachment` không trống | Approve hoặc Reject | Biomed Engineer / Tổ HC-QLCL |
| `Active` | Có hiệu lực, đang dùng | Được Approve | Expiry hoặc superseded bởi version mới | System (auto) |
| `Expired` | Đã hết hạn, cần gia hạn | `expiry_date == today` (scheduler) | Upload version mới | System (auto) |
| `Archived` | Lưu trữ lịch sử, terminal | Bị thay thế bởi version mới hoặc Asset thanh lý | TERMINAL | System (auto) |
| `Rejected` | Bị từ chối, cần sửa và nộp lại | Reviewer Reject | Tạo document mới | HTM Technician |

---

## Business Rules (BR-01 → BR-10)

| Code | Rule | Enforcement |
|------|------|-------------|
| BR-01 | Mỗi Asset chỉ có 1 `Active` doc per `doc_type_detail` — approve mới tự archive cũ | Server (`approve_document`) |
| BR-02 | Không xóa cứng document — chỉ archive, không delete | Server (override `on_trash`) |
| BR-03 | Expiry alert theo mốc 90 / 60 / 30 / 0 ngày, sinh `Expiry Alert Log` | Cron daily 00:30 |
| BR-04 | Auto-import từ IMM-04 khi `Asset Commissioning` submit `Clinical_Release` | Hook `on_submit` |
| BR-05 | Bộ hồ sơ bắt buộc cấu hình qua `Required Document Type` master, không hard-code | Dashboard + GW-2 check |
| BR-06 | Doc `is_model_level = True` áp dụng chung cho mọi asset cùng Item | Client + Server |
| BR-07 | **GW-2 Gate**: Block `Asset Commissioning` Submit nếu thiếu Chứng nhận ĐK lưu hành (hoặc chưa có `is_exempt`) | Server (`asset_commissioning.validate`) |
| BR-08 | Thiết bị Exempt NĐ98: `is_exempt = True` + `exempt_proof` upload → `document_status = "Compliant (Exempt)"` | Server (`update_asset_completeness`) |
| BR-09 | `change_summary` bắt buộc khi `version != "1.0"` | Server (`validate`) |
| BR-10 | Doc `visibility = "Internal_Only"` chỉ hiển thị với HTM Technician, Tổ HC-QLCL, Biomed, Workshop Head | Server (list filter) + Client |

---

## DocTypes

### Asset Document (primary)

| Field | Type | Bắt buộc | Ghi chú |
|-------|------|:---------:|---------|
| `asset_ref` | Link → Asset | Có | Định danh thiết bị (per-instance) |
| `model_ref` | Link → Item | — | Per-model (auto-fetch) |
| `is_model_level` | Check | — | Tick = dùng chung cho toàn bộ model |
| `doc_category` | Select | Có | Legal / Technical / Certification / Training / QA |
| `doc_type_detail` | Data | Có | Loại tài liệu cụ thể |
| `doc_number` | Data | Có | Số hiệu tài liệu |
| `version` | Data | Có | Mặc định `"1.0"` |
| `issued_date` | Date | Có | — |
| `expiry_date` | Date | — | Bắt buộc nếu Legal / Certification |
| `days_until_expiry` | Int | — | Virtual: `expiry_date - today` |
| `file_attachment` | Attach | Có | PDF/JPG/PNG, max 25 MB |
| `approved_by` | Link → User | — | Set khi Approve |
| `approval_date` | Date | — | Set khi Approve |
| `rejection_reason` | Small Text | — | Bắt buộc khi Reject |
| `superseded_by` | Link → Asset Document | — | Version control |
| `change_summary` | Small Text | — | Bắt buộc khi version != `"1.0"` |
| `visibility` | Select | — | `Public` / `Internal_Only` |
| `is_exempt` | Check | — | Miễn đăng ký NĐ98 |
| `exempt_reason` | Small Text | — | Bắt buộc khi `is_exempt = 1` |
| `exempt_proof` | Attach | — | Bắt buộc khi `is_exempt = 1` |
| `source_commissioning` | Link → Asset Commissioning | — | Nếu import từ IMM-04 |
| `source_module` | Data | — | `"IMM-04"`, `"IMM-11"`, v.v. |
| `workflow_state` | Link → Workflow State | — | Quản lý bởi Frappe Workflow |

### Supporting DocTypes

| DocType | Naming | Mô tả |
|---------|--------|-------|
| `Expiry Alert Log` | `EAL-.YYYY.-.MM.-.#####` | Log cảnh báo hết hạn — system-only write |
| `Document Request` | `DOCREQ-.YYYY.-.MM.-.#####` | Theo dõi tài liệu còn thiếu, deadline, escalation |
| `Required Document Type` | — | Master config bộ hồ sơ bắt buộc per Item Group |

---

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `imm05.list_documents` | Danh sách document, phân trang + filter |
| GET | `imm05.get_document` | Chi tiết 1 document |
| POST | `imm05.create_document` | Tạo document mới (Draft) |
| POST | `imm05.update_document` | Sửa metadata (Draft / Rejected only) |
| POST | `imm05.approve_document` | Approve → Active, auto-archive version cũ |
| POST | `imm05.reject_document` | Reject với lý do bắt buộc |
| GET | `imm05.get_asset_documents` | Toàn bộ docs của 1 Asset, group theo category |
| GET | `imm05.get_dashboard_stats` | KPI + expiry timeline + compliance by dept |
| GET | `imm05.get_expiring_documents` | Docs sắp hết hạn trong N ngày |
| GET | `imm05.get_compliance_by_dept` | Compliance rate theo khoa (%) |
| GET | `imm05.get_document_history` | Lịch sử thay đổi (wrap Frappe Version) |
| POST | `imm05.create_document_request` | Tạo Document Request cho tài liệu thiếu |
| GET | `imm05.get_document_requests` | Danh sách Document Request theo asset / status |
| POST | `imm05.mark_exempt` | Đánh dấu thiết bị Exempt khỏi NĐ98 |

---

## Scheduler Jobs

| Function | Lịch chạy | Mô tả |
|----------|-----------|-------|
| `check_document_expiry()` | Daily 00:30 | Kiểm tra expiry, tạo `Expiry Alert Log`, auto-expire doc quá hạn |
| `update_asset_completeness()` | Daily 01:00 | Batch update `custom_doc_completeness_pct` và `custom_document_status` trên Asset |
| `check_overdue_document_requests()` | Daily | Leo thang Document Request quá hạn → `status = Overdue`, email Workshop Head + VP Block2 |

**Alert levels theo mốc hết hạn:**

| Ngày còn lại | Level | Thông báo |
|:------------:|-------|-----------|
| 90 | Info | Workshop Head |
| 60 | Warning | Workshop Head + Biomed Engineer |
| 30 | Critical | Workshop Head + VP Block2 |
| 0 | Danger | Workshop Head + VP Block2 + QA Risk Team → auto-Expire |

---

## Integration Points

| Hướng | Module | Mô tả |
|-------|--------|-------|
| IMM-04 → IMM-05 | Asset Commissioning | `on_submit` (Clinical_Release) → auto-tạo Document Set cho Asset mới |
| IMM-05 → IMM-08 | PM Work Order | Cung cấp Service Manual, Spec Sheet cho bảo trì định kỳ |
| IMM-05 → IMM-09 | Repair Work Order | Cung cấp Schematic, Parts Catalog cho sửa chữa |
| IMM-11 → IMM-05 | Calibration | Lưu trữ chứng chỉ hiệu chuẩn sau mỗi chu kỳ |
| IMM-05 → IMM-10 | Compliance Dashboard | `custom_document_status` trên Asset đóng góp vào compliance score |
| IMM-05 → IMM-13 | Decommission | Auto-archive toàn bộ hồ sơ khi thanh lý Asset |

---

## Known Gaps / TODO

| Gap | Mức độ | Kế hoạch |
|-----|:------:|----------|
| Auto-import IMM-04 cần test E2E đầy đủ | High | Sprint tiếp theo |
| Email notification dùng inline string, chưa có template | Medium | Tạo Email Template DocType |
| Dashboard compliance UI frontend chưa implement | High | Cần build component imm05_dashboard |
| Document Request form UI chưa có | Medium | API sẵn sàng, cần UI layer |
| Exempt handling UI (form workflow) chưa rõ | Low | Hiện chỉ qua API `mark_exempt` |
| GW-2 gate trong `asset_commissioning.validate` cần UAT | High | Test case trong UAT script |

---

## QMS Mapping

| Yêu cầu | Nguồn | Cách đáp ứng |
|---------|-------|--------------|
| Kiểm soát tài liệu (Document Control) | ISO 13485 §4.2 | Workflow Draft → Review → Active, version control, audit trail |
| Truy xuất nguồn gốc (Traceability) | WHO HTM Standard | `source_commissioning`, `source_module`, Lifecycle Event log |
| Quản lý hồ sơ thiết bị (DHF/DMR) | ISO 13485 §4.2.4 | Kho hồ sơ per-Asset, bộ hồ sơ bắt buộc qua `Required Document Type` |
| Đăng ký lưu hành thiết bị y tế | NĐ 98/2021/NĐ-CP | GW-2 gate block nếu thiếu Chứng nhận ĐK lưu hành |
| Cảnh báo hiệu lực tài liệu | WHO HTM Annex 7 | Scheduler 90/60/30/0 ngày + `Expiry Alert Log` |
| Kiểm soát truy cập thông tin | ISO 13485 §4.2.5 | `visibility` field + role-based filter (`Internal_Only`) |
| Không xóa hồ sơ y tế | NĐ 98 + WHO HTM | BR-02: override `on_trash`, chỉ Archive, không Delete |
