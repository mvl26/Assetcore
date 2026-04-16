# IMM-05 Functional Specification

**Module:** IMM-05 — Đăng ký, Cấp phép & Quản lý Hồ sơ Thiết bị Y tế
**Version:** 1.0-draft
**Ngày:** 2026-04-16
**Trạng thái:** CHỜ PHÊ DUYỆT

---

## 1. Mục tiêu Module

IMM-05 quản lý **toàn bộ kho hồ sơ kỹ thuật, pháp lý, kiểm định** gắn với từng thiết bị y tế (Asset) hoặc từng dòng sản phẩm (Item/Model) trong suốt vòng đời.

**Không phải** module đơn lẻ — IMM-05 là **hệ thống Document Repository** vận hành song song liên tục với tất cả module khác, từ khi thiết bị được mint (IMM-04) đến khi thanh lý (IMM-13/14).

---

## 2. Phạm vi

### 2.1 In Scope

| # | Chức năng | Mô tả |
|---|-----------|-------|
| F-01 | Document Repository | Kho hồ sơ per-Asset (per-instance) và per-Item (per-model) |
| F-02 | Phân loại tài liệu | 5 nhóm: Pháp lý, Kỹ thuật, Kiểm định, Đào tạo, Chất lượng |
| F-03 | Metadata đầy đủ | Số hiệu, ngày cấp, expiry, version, cơ quan cấp, owner, approver |
| F-04 | Version control | Archive tự động version cũ khi version mới được duyệt |
| F-05 | Auto-import từ IMM-04 | Kế thừa CO/CQ/Packing/Manual/Warranty/License khi Asset được mint |
| F-06 | Expiry alert | Scheduler: 90/60/30/0 ngày, email + in-app notification |
| F-07 | Dashboard | Assets thiếu hồ sơ, sắp hết hạn, compliance rate theo khoa |
| F-08 | Audit trail | Mọi thao tác sinh record (upload, approve, archive, expire, reject) |

### 2.2 Out of Scope

| # | Chức năng | Module phụ trách |
|---|-----------|-----------------|
| 1 | Quản lý hợp đồng vendor | IMM-02 |
| 2 | Lịch đào tạo nhân viên | IMM-06 |
| 3 | Lịch hiệu chuẩn định kỳ | IMM-11 |
| 4 | CAPA management | IMM-16 |
| 5 | Electronic signature (chữ ký số) | v2.0 |
| 6 | Integration FHIR/HIS | Phase 2 |

### 2.3 Dependencies

| Module | Chiều | Mô tả |
|--------|-------|-------|
| IMM-04 | IN | Trigger tạo Document Set khi Asset mint; kế thừa commissioning_documents |
| IMM-06 | OUT | Cung cấp Manual/HDSD cho module Đào tạo |
| IMM-08 | OUT | Cung cấp Service Manual, Spec Sheet cho PM |
| IMM-09 | OUT | Cung cấp Schematic, Parts List cho sửa chữa |
| IMM-11 | BOTH | Cung cấp Certificate hiệu chuẩn; nhận lại cert mới sau hiệu chuẩn |
| IMM-10 | OUT | Compliance score dựa trên document completeness |
| IMM-13 | OUT | Archive toàn bộ kho hồ sơ khi thanh lý |

### 2.4 Assumptions

| # | Giả định |
|---|----------|
| A-01 | ERPNext `Asset` là định danh duy nhất — mọi document link về `Asset.name` |
| A-02 | Tài liệu per-Model (IFU, Service Manual) dùng `Item` làm anchor — áp dụng chung cho toàn bộ asset cùng model |
| A-03 | Tài liệu per-Instance (Giấy phép, Cert hiệu chuẩn) link thẳng `Asset` |
| A-04 | File lưu trong Frappe File System (không S3 ở Wave 1) |
| A-05 | Một Asset có thể có nhiều document cùng loại (các version khác nhau) |
| A-06 | Required Document Set (bộ hồ sơ bắt buộc) được cấu hình per-Item Group, không hard-code |

---

## 3. Actor & Phân quyền

| Actor | Vị trí thực tại BV NĐ1 | Quyền IMM-05 | Trách nhiệm chính |
|-------|------------------------|--------------|-------------------|
| **HTM Technician** | Kỹ thuật viên HTM | Create, Read, Write (Draft only) | Upload tài liệu, điền metadata |
| **Biomed Engineer** | Kỹ sư Biomedical | Read, Write, Approve/Reject | Xác nhận tài liệu kỹ thuật |
| **QA Risk Team** | Phòng QA/Quản lý rủi ro | Read, Write, Approve (Pháp lý) | Duyệt giấy phép, compliance docs |
| **Workshop Head** | Trưởng Phân xưởng | Read, Submit, Cancel, Amend | Quản lý kho hồ sơ, override |
| **VP Block2** | Phó Trưởng Khoa Khối 2 | Read, Submit, Cancel | Phê duyệt cuối cho critical docs |
| **CMMS Admin** | IT/CMMS | Full | Quản trị hệ thống |
| **Clinical Head** | Trưởng Khoa Lâm sàng | Read only (khoa mình) | Xem hồ sơ thiết bị tại khoa |

---

## 4. User Stories

### US-01: Upload tài liệu mới

```
Là HTM Technician,
Tôi muốn upload tài liệu (PDF/ảnh) cho một thiết bị và điền metadata,
Để tài liệu được lưu trữ tập trung và sẵn sàng cho người duyệt kiểm tra.

Acceptance Criteria:
- GIVEN tôi có quyền Create trên Asset Document
- WHEN tôi chọn Asset, chọn Category, upload file, điền metadata
- THEN hệ thống tạo record status = Draft
- AND naming series theo format DOC-{ASSET}-{YYYY}-{####}
- AND file được attach vào record
```

### US-02: Duyệt / Từ chối tài liệu

```
Là Biomed Engineer hoặc QA Officer,
Tôi muốn xem xét tài liệu đã upload và Approve hoặc Reject,
Để đảm bảo chất lượng hồ sơ trước khi đưa vào kho chính thức.

Acceptance Criteria:
- GIVEN tài liệu ở status Pending_Review
- WHEN tôi nhấn Approve
- THEN status → Active, approved_by = tôi, approval_date = today
- AND nếu có version cũ cùng loại + cùng asset → version cũ auto-archive

- WHEN tôi nhấn Reject
- THEN status → Rejected
- AND rejection_reason là bắt buộc
- AND notification gửi cho người upload
```

### US-03: Auto-import từ IMM-04

```
Là hệ thống,
Khi phiếu Asset Commissioning được Submit (Clinical_Release),
Tôi tự động tạo Document Set cho Asset mới,
Để kho hồ sơ có baseline ngay từ đầu.

Acceptance Criteria:
- GIVEN phiếu IMM-04 chuyển Clinical_Release → on_submit
- THEN hệ thống tạo 1 Asset Document cho mỗi row Received trong commissioning_documents
- AND mỗi doc có source_commissioning = phiếu IMM-04
- AND status = Draft (cần review lại)
- AND nếu qa_license_doc tồn tại → tạo thêm 1 doc category "Pháp lý"
```

### US-04: Cảnh báo hết hạn

```
Là Workshop Head,
Tôi muốn nhận cảnh báo khi tài liệu sắp hết hạn (90/60/30 ngày),
Để kịp thời gia hạn hoặc thay thế trước khi vi phạm pháp lý.

Acceptance Criteria:
- GIVEN tài liệu Active có expiry_date
- WHEN (expiry_date - today) == 90 THEN gửi alert level "Info" cho Workshop Head
- WHEN (expiry_date - today) == 60 THEN gửi alert level "Warning" cho Workshop Head + Biomed
- WHEN (expiry_date - today) == 30 THEN gửi alert level "Critical" cho Workshop Head + VP Block2
- WHEN (expiry_date - today) == 0 THEN auto-transition status → Expired + alert "Danger"
- AND mỗi lần alert sinh 1 record Expiry Alert Log
```

### US-05: Dashboard hồ sơ thiết bị

```
Là VP Block2 hoặc Workshop Head,
Tôi muốn xem dashboard tổng hợp trạng thái hồ sơ toàn khoa,
Để quản lý compliance và ra quyết định kịp thời.

Acceptance Criteria:
- KPI-01: Tổng tài liệu Active
- KPI-02: Số tài liệu sắp hết hạn (90 ngày tới)
- KPI-03: Số tài liệu ĐÃ hết hạn chưa renew
- KPI-04: Số Asset thiếu hồ sơ bắt buộc
- TABLE-01: Danh sách assets thiếu tài liệu theo khoa
- TABLE-02: Timeline tài liệu hết hạn (30/60/90 ngày tới)
- CHART-01: Compliance rate theo khoa (%)
```

### US-06: Xem kho hồ sơ theo Asset

```
Là Biomed Engineer,
Tôi muốn mở 1 Asset và xem toàn bộ hồ sơ liên quan (tất cả version),
Để có đầy đủ context khi bảo trì hoặc kiểm định.

Acceptance Criteria:
- GIVEN tôi đang xem form Asset
- WHEN tôi mở tab/sidebar "Hồ sơ"
- THEN hiển thị danh sách Asset Document filter theo asset_ref
- AND group theo doc_category
- AND Active docs hiển thị đầu, Archived/Expired hiển thị mờ
```

### US-07: Version control

```
Là HTM Technician,
Khi tôi upload phiên bản mới của tài liệu đã có,
Hệ thống tự archive version cũ và link version mới,
Để luôn chỉ có 1 version Active cho mỗi loại tài liệu.

Acceptance Criteria:
- GIVEN tôi upload doc mới cùng asset + cùng doc_type_detail
- AND version cũ đang Active
- WHEN doc mới được Approve
- THEN version cũ → Archived (archived_by_version = version mới)
- AND version mới → Active
- AND KHÔNG XÓA version cũ (chỉ archive)
```

---

## 5. Workflow — Trạng thái Tài liệu

### 5.1 State Machine

```
                    ┌──────────┐
                    │  Draft   │ ← Tạo mới / Import từ IMM-04
                    └────┬─────┘
                         │ Submit for Review
                         ▼
                ┌─────────────────┐
                │ Pending_Review  │
                └────┬───────┬────┘
                     │       │
              Approve│       │Reject
                     ▼       ▼
              ┌──────┐   ┌──────────┐
              │Active│   │ Rejected │
              └──┬───┘   └──────────┘
                 │
        ┌────────┼──────────────┐
        │        │              │
   Expiry   New Version    Asset Retired
   (auto)   Approved       (IMM-13)
        │        │              │
        ▼        ▼              ▼
   ┌────────┐ ┌────────┐  ┌────────┐
   │Expired │ │Archived│  │Archived│
   └────────┘ └────────┘  └────────┘
```

### 5.2 State Table

| Code | State | Mô tả | Entry Condition | Exit Condition | Actor chính |
|------|-------|-------|-----------------|----------------|-------------|
| S01 | Draft | Vừa upload, chưa review | Tạo mới hoặc import | Submit for Review | HTM Technician |
| S02 | Pending_Review | Đang chờ duyệt | File + metadata đầy đủ | Approve hoặc Reject | Biomed / QA |
| S03 | Active | Đang có hiệu lực, được sử dụng | Approved | Expiry hoặc superseded | — (auto) |
| S04 | Expired | Đã hết hạn, cần gia hạn | expiry_date < today (scheduler) | Upload version mới | — (auto) |
| S05 | Archived | Lưu trữ lịch sử, không sử dụng | Bị thay thế bởi version mới | TERMINAL | — (auto) |
| S06 | Rejected | Bị từ chối, cần sửa | Reviewer reject | Tạo doc mới | Biomed / QA |

### 5.3 Transition Table

| From | Action | To | Role | Condition |
|------|--------|----|------|-----------|
| Draft | Submit_Review | Pending_Review | HTM Technician | file_attachment not empty |
| Pending_Review | Approve | Active | Biomed Engineer, QA Risk Team | — |
| Pending_Review | Reject | Rejected | Biomed Engineer, QA Risk Team | rejection_reason not empty |
| Active | — (scheduler) | Expired | System | expiry_date == today |
| Active | — (auto) | Archived | System | version mới cùng loại được Approve |

---

## 6. Business Rules

| Code | Rule | Mô tả | Enforcement |
|------|------|-------|-------------|
| BR-01 | Mỗi Asset chỉ có 1 Active doc per doc_type_detail | Khi approve mới → archive cũ | Server (on_approve) |
| BR-02 | Không xóa cứng document | Chỉ archive, không delete | Server (override delete) |
| BR-03 | Expiry alert theo mốc 90/60/30/0 | Scheduler daily check | Cron job |
| BR-04 | Auto-import từ IMM-04 | Khi commissioning submit → tạo doc set | Server hook (on_submit) |
| BR-05 | Document set bắt buộc | Config per Item Group (chưa hard-code) | Dashboard check |
| BR-06 | Per-model doc shared | doc is_model_level=True → applicable cho mọi asset cùng Item | Client + Server |

---

## 7. Phân loại Tài liệu

### 7.1 Categories & Types

| Category | doc_category | Loại tài liệu cụ thể (doc_type_detail) |
|----------|-------------|----------------------------------------|
| **Pháp lý** | Legal | Giấy phép nhập khẩu, Giấy phép hoạt động, Chứng nhận đăng ký lưu hành, Giấy phép bức xạ |
| **Kỹ thuật** | Technical | Service Manual, User Manual (HDSD), Schematic, Spec Sheet, Parts Catalog |
| **Kiểm định** | Certification | Chứng chỉ hiệu chuẩn, Kết quả kiểm định, Biên bản đo kiểm, Chứng nhận CE/FDA |
| **Đào tạo** | Training | Tài liệu đào tạo, Biên bản đào tạo, Video hướng dẫn |
| **Chất lượng** | QA | CO - Chứng nhận Xuất xứ, CQ - Chứng nhận Chất lượng, Warranty Card, Packing List |

### 7.2 Required Document Set (cấu hình mặc định)

Khi Asset được mint từ IMM-04, hệ thống kiểm tra bộ hồ sơ bắt buộc:

| # | Loại tài liệu | Bắt buộc | Có expiry? | Ghi chú |
|---|---------------|:--------:|:----------:|---------|
| 1 | Giấy phép nhập khẩu | Conditional | Yes | Nếu thiết bị nhập khẩu |
| 2 | Chứng nhận đăng ký lưu hành | Yes | Yes | Bắt buộc theo NĐ98 |
| 3 | CO - Chứng nhận Xuất xứ | Yes | No | — |
| 4 | CQ - Chứng nhận Chất lượng | Yes | No | — |
| 5 | User Manual (HDSD) | Yes | No | Per-model |
| 6 | Warranty Card | Yes | Yes | Thời hạn bảo hành |
| 7 | Giấy phép bức xạ | Conditional | Yes | Nếu is_radiation_device |

---

## 8. Luồng nghiệp vụ End-to-End

### 8.1 Luồng chính: Upload → Approve → Active

```
Step 1: [HTM Technician] Mở form Asset Document
  → Chọn Asset (hoặc Item nếu per-model)
  → Chọn Category + Type
  → Upload file (PDF/Image, max 25MB)
  → Điền metadata: số hiệu, ngày cấp, cơ quan cấp, expiry_date
  → Save → status = Draft

Step 2: [HTM Technician] Click "Gửi Duyệt"
  → Validation: file_attachment không trống
  → status → Pending_Review
  → Notification gửi cho Biomed Engineer / QA Officer

Step 3: [Biomed / QA] Mở document cần duyệt
  → Xem file đính kèm
  → Kiểm tra metadata vs nội dung file
  → Approve → status = Active
    → approved_by = current user
    → approval_date = today
    → Nếu có version cũ cùng loại → auto-archive
  → HOẶC Reject → status = Rejected
    → rejection_reason bắt buộc điền
    → Notification gửi cho người upload

Step 4: [System] Document Active
  → Asset completeness score tự cập nhật
  → Dashboard compliance refresh
```

### 8.2 Luồng phụ: Auto-import từ IMM-04

```
Trigger: Asset Commissioning → on_submit (Clinical_Release)

Step 1: [System] Đọc commissioning_documents table
  → Lọc rows có status = "Received"
  → Với mỗi row:
    - Tạo Asset Document
    - asset_ref = final_asset
    - doc_category = map từ doc_type
    - status = Draft (cần review lại)
    - source_commissioning = commissioning.name

Step 2: [System] Kiểm tra qa_license_doc
  → Nếu tồn tại (file path):
    - Tạo Asset Document
    - doc_category = "Legal"
    - doc_type_detail = "Giấy phép bức xạ"
    - file_attachment = qa_license_doc

Step 3: [System] Log event
  → Tạo Lifecycle Event: "imm05.document_set.auto_created"
```

### 8.3 Luồng phụ: Expiry Alert Cycle

```
Trigger: Scheduler daily (00:30)

Step 1: [System] Query Asset Document
  WHERE workflow_state = "Active"
  AND expiry_date IS NOT NULL

Step 2: Với mỗi doc:
  - Tính days_remaining = expiry_date - today

  IF days_remaining IN (90, 60, 30):
    → Tạo Expiry Alert Log
    → Gửi email theo template
    → Gửi in-app notification (frappe.publish_realtime)

  IF days_remaining <= 0:
    → Chuyển status → Expired
    → Tạo Expiry Alert Log (level = DANGER)
    → Gửi alert cho tất cả stakeholder
```

### 8.4 Luồng phụ: Version Control

```
Trigger: Biomed/QA Approve document mới

Step 1: [System] Kiểm tra existing Active doc
  WHERE asset_ref = doc.asset_ref
  AND doc_type_detail = doc.doc_type_detail
  AND workflow_state = "Active"
  AND name != doc.name

Step 2: Nếu tìm thấy old_doc:
  → old_doc.workflow_state = "Archived"
  → old_doc.archived_by_version = doc.version
  → old_doc.save()

Step 3: doc.workflow_state = "Active"
```

---

## 9. Exception Handling

| # | Tình huống | Xử lý |
|---|-----------|-------|
| E-01 | Upload file > 25MB | Block + thông báo giới hạn |
| E-02 | File format không hợp lệ (chỉ PDF/JPG/PNG) | Block + danh sách format cho phép |
| E-03 | Expiry_date < issued_date | Validation error VR-01 |
| E-04 | Trùng doc_number cùng type + cùng asset | Validation error VR-02 |
| E-05 | Asset bị Decommission → document vẫn archive | Không chặn, chỉ archive + log |
| E-06 | Reviewer approve doc không có file | Block (VR-03: file bắt buộc) |

---

## 10. QMS Mapping

| QMS Code | Loại | Tên | Module | Trạng thái |
|----------|------|-----|--------|-----------|
| QC-IMMIS-05 | L1/Policy | Chính sách quản lý hồ sơ thiết bị | IMM-05 | Planning |
| PR-HTM-05 | SOP | Quy trình tiếp nhận, phân loại, lưu trữ hồ sơ | IMM-05 | Planning |
| WI-HTM-05-01 | Work Instruction | Hướng dẫn upload tài liệu lên hệ thống | IMM-05 | Planning |
| WI-HTM-05-02 | Work Instruction | Hướng dẫn duyệt & archive tài liệu | IMM-05 | Planning |
| BM-HTM-05-01 | Form | Form upload tài liệu (Asset Document) | IMM-05 | Draft |
| HS-LOG-05-01 | Log | Expiry Alert Log | IMM-05 | Draft |
| KPI-DASH-05 | Dashboard | Dashboard Compliance Hồ sơ | IMM-05 | Planning |

---

## 11. Mapping với WHO HTM Framework

| WHO Guideline | Nội dung | Áp dụng IMM-05 |
|---------------|----------|----------------|
| WHO-HTM 2.1 | Medical device registration and regulation | Document repository cho giấy phép, chứng nhận |
| WHO-HTM 2.3 | Medical device nomenclature | doc_type_detail mapping theo GMDN/UMDNS |
| WHO-HTM 3.2 | Documentation and record keeping | Version control, audit trail, archive policy |
| NĐ 98/2021 | Quản lý trang thiết bị y tế | Bắt buộc: giấy phép lưu hành, giấy phép nhập khẩu |
