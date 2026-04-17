# IMM-05 — Readiness Audit Report

**Ngày thực hiện:** 2026-04-17  
**Phạm vi:** So sánh `AssetCore_Wave1_BA_Analysis.html` (IMM-05 section) vs `docs/imm-05/*.md`  
**Người thực hiện:** Claude Code (Lead Architect role)  
**Kết luận:** ⚠️ **CẦN CHỈNH SỬA THÊM** — 6 gap phải xử lý trước khi bắt đầu code

---

## 1. Bảng đối chiếu tính năng

### 1.1 Actors & Roles

| Thành phần | BA Analysis | MD Design (FS + TD) | Đánh giá |
|-----------|-------------|---------------------|----------|
| Document owner | **Tổ HC-QLCL & Risk** | **QA Risk Team** | ⚠️ Tên khác nhau — cần chuẩn hóa |
| Document contributor | Kỹ thuật viên HTM | HTM Technician | ✅ Khớp |
| Approver | PTP Khối 2 | VP Block2 + Biomed Engineer | ✅ Khớp (Biomed thêm vào hợp lý) |
| System admin | CMMS Admin | CMMS Admin | ✅ Khớp |
| Clinical viewer | Không mention | Clinical Head (read-only) | ✅ MD mở rộng hợp lệ |

### 1.2 Business Rules

| Mã BA | Nội dung BA | Trạng thái trong MD | Đánh giá |
|-------|------------|---------------------|----------|
| BR-05-01 | Thiết bị A/B/C (NĐ98) PHẢI có số ĐK lưu hành OR văn bản miễn đăng ký TRƯỚC khi release; kiểm tra tại **GW-2 của IMM-04** | ❌ Không có | 🔴 CRITICAL GAP |
| BR-05-02 | Không xóa doc đã approve, chỉ archive với lý do | ✅ BR-02 trong FS, VR-05 + on_trash() trong TD | ✅ Đã cover |
| BR-05-03 | Version mới phải có change summary + người duyệt | ⚠️ Có approver, nhưng không có `change_summary` field | ⚠️ Thiếu field |
| BR-05-04 | Alert 90/60/30 ngày trước expiry | ✅ BR-03 trong FS, Scheduler 7.1 trong TD | ✅ Đã cover |
| BR-05-05 | Minimum docs: IFU + số ĐK (nếu có) + service manual | ⚠️ IFU có, số ĐK có; Service Manual seed data là `is_mandatory=0` | ⚠️ Mâu thuẫn |

### 1.3 Exception Handling

| Tình huống (BA) | MD/FS có xử lý? | Đánh giá |
|-----------------|-----------------|----------|
| Thiết bị miễn đăng ký NĐ98 → "Exempt" + upload văn bản | ❌ Không có field `is_exempt` hay state Exempt | 🔴 MISSING |
| Tài liệu bị mất → tạo "Document Request" task với deadline | ❌ Không có DocType hay cơ chế nào | 🔴 MISSING |
| Số ĐK hết hạn khi đang vận hành → `document_status = "Non-Compliant"` | ⚠️ MD dùng `custom_doc_completeness_pct` (%), không có enum status | ⚠️ MISMATCH |
| Tài liệu confidential NCC → `Internal Only` visibility | ❌ Không có field visibility trên Asset Document | 🔴 MISSING |

### 1.4 Outputs / DocTypes

| Output (BA) | DocType trong MD | Đánh giá |
|-------------|-----------------|----------|
| Asset Document (custom) | ✅ `Asset Document` — 25 fields | ✅ Đủ |
| `Asset.document_status` (enum: Compliant/Incomplete/Expired/Non-Compliant) | ❌ MD có `custom_doc_completeness_pct` (%) + `custom_doc_status_summary` (text) | 🔴 MISMATCH kiểu dữ liệu |
| Frappe Notification (expiry alert) | ✅ `Expiry Alert Log` + scheduler | ✅ Đủ |
| KPI-DASH-IMMIS-05 | ✅ `imm05_dashboard` page | ✅ Đủ |
| **Document Change Log** (audit trail mọi thay đổi) | ❌ Frappe track_changes=True nhưng không có DocType riêng | ⚠️ THIẾU explicit |

### 1.5 User Stories

| US (BA) | Coverage trong FS | Coverage trong TD | Đánh giá |
|---------|-------------------|-------------------|----------|
| US-05-01: Upload & classify docs theo loại, gắn Asset ID | ✅ US-01, F-01, F-02, F-03 | ✅ Fields đầy đủ | ✅ |
| US-05-02: Alert 90/60/30 ngày | ✅ US-04, F-06 | ✅ Scheduler 7.1 | ✅ |
| US-05-03: PTP xem compliance rate theo khoa | ✅ US-05, F-07 | ✅ API `get_compliance_by_dept` | ✅ |

### 1.6 Workflow

| Tiêu chí | BA | MD | Đánh giá |
|---------|----|----|----------|
| Số states | 5 steps (implicit) | 6 states rõ ràng | ✅ MD tốt hơn |
| Trigger từ IMM-04 (auto-import) | ✅ Mention (Trigger từ IMM-04) | ✅ US-03, hook on_submit | ✅ |
| Gateway GW-2: block release nếu docs thiếu | ✅ **Explicitly stated in BA** | ❌ Không có | 🔴 CRITICAL |
| Version control (archive old) | Implicit (BR-05-03) | ✅ US-07, archive_old_versions() | ✅ |

---

## 2. Danh sách Gap / Thiếu sót

### GAP-01 🔴 [CRITICAL] — GW-2 Integration với IMM-04 chưa thiết kế

**BA nói:**
> "IMM-05 hoạt động song song với IMM-04. Hồ sơ cần được hoàn thiện TRƯỚC khi asset có thể release (GW-2 của IMM-04 phải kiểm tra IMM-05 status). Đây là điểm khóa compliance."

> BR-05-01: "Phải có số ĐK lưu hành hoặc miễn đăng ký... trước khi release — linked to IMM-04 GW-2"

**Hiện trạng MD:** Không có. `asset_commissioning.py` hiện tại `on_submit()` chỉ mint asset và fire event.

**Cần làm:**
- Thêm validation trong `asset_commissioning.py`: trước khi Submit, kiểm tra Asset Document của asset đó đã có `Chứng nhận đăng ký lưu hành` (Active) hoặc `is_exempt=True`.
- Phụ thuộc: GAP-02 (Exempt field) phải làm trước.

---

### GAP-02 🔴 [CRITICAL] — "Exempt" option không có trong thiết kế

**BA nói:** Thiết bị nhập khẩu có thể xin miễn đăng ký NĐ98. Khi đó → chọn "Exempt" + upload văn bản miễn đăng ký.

**Cần làm:**
- Thêm field `is_exempt` (Check) vào `Asset Document` khi doc_type_detail = "Chứng nhận đăng ký lưu hành"
- Hoặc tốt hơn: thêm `exempt_reason` (Small Text) + `exempt_document` (Attach) vào Asset Document
- Hoặc tạo field `registration_exempt` + `exempt_proof` trên ERPNext `Asset` core (Custom Field)

---

### GAP-03 🔴 [CRITICAL] — Asset.document_status enum không có trong thiết kế

**BA output:** `Asset.document_status` — Select: Compliant / Incomplete / Expiring Soon / Non-Compliant

**MD thiết kế:** `custom_doc_completeness_pct` (Percent) + `custom_doc_status_summary` (Small Text)

**Vấn đề:** Dashboard và GW-2 check cần một **enum status** rõ ràng để filter, không thể filter bằng percentage. Ví dụ: `Asset.document_status = "Non-Compliant"` là điều kiện đơn giản để block release.

**Cần làm:**
- Thêm custom field `custom_document_status` (Select: Compliant/Incomplete/Expiring_Soon/Non-Compliant) vào Asset
- Scheduler `update_asset_completeness()` phải set cả pct lẫn enum status

---

### GAP-04 🟡 [HIGH] — "Document Request" task chưa có cơ chế

**BA nói:** Khi tài liệu bị mất → tạo "Document Request" task với deadline, set status = "Incomplete". Phòng vật tư theo dõi; leo thang nếu quá 30 ngày.

**Cần làm (2 lựa chọn):**
- Option A: Tạo DocType `Document Request` (nhẹ) — link to Asset + doc_type + deadline + assigned_to + status
- Option B: Dùng Frappe native `ToDo` linked to Asset Document — ít code hơn nhưng ít traceability hơn

**Khuyến nghị:** Option A (phù hợp audit trail requirement)

---

### GAP-05 🟡 [HIGH] — "Internal Only" visibility chưa có

**BA nói:** Tài liệu confidential NCC → `document visibility = "Internal Only"`, chỉ HTM và QLCL được xem.

**Cần làm:**
- Thêm field `visibility` (Select: Public/Internal_Only) vào Asset Document
- Thêm permission check trong `list_documents` API: filter `visibility` theo role

---

### GAP-06 🟡 [MEDIUM] — Document Change Log vs track_changes

**BA output:** "Document Change Log với timestamp + user" — là output DocType riêng biệt.

**MD thiết kế:** Dùng Frappe `track_changes=True` (built-in Version DocType).

**Vấn đề:** Frappe `track_changes` có — nhưng UI không hiện rõ, khó query/dashboard. BA implies một view riêng.

**Cần làm:** Không cần DocType mới — nhưng cần API endpoint `get_document_history(name)` để wrap Frappe's Version DocType cho Dashboard display.

---

### GAP-07 🟢 [LOW] — Actor naming inconsistency

| Vai trò | Tên trong BA | Tên trong MD | 
|---------|-------------|--------------|
| Legal document owner | Tổ HC-QLCL & Risk | QA Risk Team |
| Approver | PTP Khối 2 | VP Block2 |

**Không phải technical gap** — đây là naming convention. Cần quyết định tên chuẩn và nhất quán trong workflow fixture, permission matrix, email templates.

---

### GAP-08 🟢 [LOW] — BR-05-03: `change_summary` field thiếu

**BA:** "Version mới phải có change summary"

**MD:** Field `notes` có nhưng không có `change_summary` riêng biệt.

**Cần làm:** Đổi tên hoặc thêm field `change_summary` (Small Text) vào Asset Document, bắt buộc khi upload version mới (version != "1.0").

---

### GAP-09 🟢 [LOW] — BR-05-05: Service Manual là bắt buộc theo BA nhưng `is_mandatory=0` trong seed data

**BA:** "Hồ sơ tối thiểu: IFU + số ĐK + service manual"

**MD seed data:** `{"type_name": "Service Manual", ..., "is_mandatory": 0}`

**Cần làm:** Cân nhắc đặt `is_mandatory=1` cho Service Manual, hoặc để `is_mandatory=0` nhưng document tại Note trong FS.

---

## 3. Đánh giá Kỹ thuật (Technical Feasibility)

### 3.1 Frappe Platform

| Thành phần | Khả thi? | Ghi chú |
|-----------|:--------:|---------|
| DocType `Asset Document` (25 fields) | ✅ | Standard Frappe pattern |
| Workflow 6 states + transitions | ✅ | Frappe native workflow engine |
| Custom Fields trên ERPNext Asset | ✅ | Đã làm tương tự IMM-04 |
| Scheduler daily (expiry check) | ✅ | Đã có pattern trong `tasks.py` |
| Auto-import từ IMM-04 on_submit | ✅ | Đã có pattern trong `asset_commissioning.py` |
| `track_changes=True` cho audit | ✅ | Frappe built-in |
| GW-2 validation block (GAP-01) | ✅ | Thêm validate() vào asset_commissioning.py |
| Document Request DocType (GAP-04) | ✅ | Simple DocType |
| Visibility filter trong API (GAP-05) | ✅ | Whitelist-based filter đã có pattern trong `imm04.py` |

### 3.2 Điểm rủi ro

| Rủi ro | Mức độ | Biện pháp |
|--------|:------:|-----------|
| GW-2 check phụ thuộc IMM-05 data tồn tại — nếu IMM-05 chưa deploy khi IMM-04 đang chạy sẽ block release | 🔴 | Feature flag: skip GW-2 check nếu `Asset Document` DocType chưa tồn tại |
| `custom_document_status` enum cần batch update cho toàn bộ existing Assets | 🟡 | Migration script + scheduler đầu tiên |
| Auto-import từ IMM-04 tạo Draft docs — nếu commissioning có nhiều docs sẽ tạo nhiều record cùng lúc | 🟡 | Transaction wrap + error handling per-row |
| File size 25MB × nhiều assets có thể fill disk nhanh | 🟢 | Frappe file system warning — cần monitor, S3 plan cho v2 |

---

## 4. Readiness Score

### Thang điểm: 1–10 (10 = Dev Ready hoàn toàn)

| Tiêu chí | Điểm tối đa | Điểm hiện tại | Ghi chú |
|---------|:-----------:|:-------------:|---------|
| Functional Specs đầy đủ | 2.0 | 1.5 | Thiếu Exempt, Document Request |
| Technical Design đầy đủ | 2.0 | 1.6 | Thiếu document_status enum, visibility field |
| BA/MD alignment | 2.0 | 1.2 | 4 critical/high gaps chưa resolve |
| Workflow rõ ràng | 1.0 | 0.8 | GW-2 integration chưa thiết kế |
| Actor + Permission rõ | 1.0 | 0.8 | Naming inconsistency |
| API đủ endpoint | 1.0 | 0.9 | Thiếu `get_document_history` |
| Migration plan rõ | 1.0 | 0.9 | Đủ, cần thêm GAP fixes |

**Tổng: 7.7/10**

### Kết luận:

```
⚠️  CẦN CHỈNH SỬA THÊM

IMM-05 đạt ~77% sẵn sàng. Cần xử lý 3 Critical gaps (GAP-01, GAP-02, GAP-03)
trước khi có thể bắt đầu code. Các Low gaps có thể xử lý song song trong sprint.

Ước tính effort bổ sung: ~4–6 giờ chỉnh sửa tài liệu + validation design
Sau khi fix: ước tính đạt 9.0/10 → ĐÃ SẴN SÀNG TRIỂN KHAI
```

---

## 5. Hành động tiếp theo

### Giai đoạn A — Fix tài liệu (ưu tiên trước khi code)

| # | Action | File cần sửa | Effort |
|---|--------|-------------|--------|
| A1 | Thêm `is_exempt` + `exempt_proof` field vào Asset Document schema | `IMM-05_Technical_Design.md` §2.1 | 30 phút |
| A2 | Thêm `custom_document_status` (Select enum) vào Custom Fields table | `IMM-05_Technical_Design.md` §3.1 | 20 phút |
| A3 | Thêm `visibility` field (Select: Public/Internal_Only) vào Asset Document schema | `IMM-05_Technical_Design.md` §2.1 | 20 phút |
| A4 | Thêm `change_summary` field vào Asset Document schema | `IMM-05_Technical_Design.md` §2.1 | 15 phút |
| A5 | Viết spec GW-2 validation trong `asset_commissioning.py` hook | `IMM-05_Technical_Design.md` §5.2 | 45 phút |
| A6 | Thêm DocType `Document Request` vào schema | `IMM-05_Technical_Design.md` (mục mới) | 30 phút |
| A7 | Cập nhật VR-08 (file format validation) + VR-09 (Exempt logic) vào Validation Rules | `IMM-05_Technical_Design.md` §4 | 20 phút |
| A8 | Sửa tên actor "QA Risk Team" → "Tổ HC-QLCL" hoặc ngược lại — chọn 1 tên duy nhất | `IMM-05_Functional_Specs.md` §3 + TD §2.1 | 15 phút |
| A9 | Cập nhật Exception Handling trong FS để cover Exempt + Document Request | `IMM-05_Functional_Specs.md` §9 | 20 phút |
| A10 | Sửa BR-05-05 service manual `is_mandatory` trong seed data | `IMM-05_Technical_Design.md` §8.2 | 5 phút |

**Tổng effort Giai đoạn A: ~4 giờ**

### Giai đoạn B — Bắt đầu Dev (sau khi Giai đoạn A done)

Theo đúng Migration Plan trong `IMM-05_Technical_Design.md` §11.1:

```
Step 1: DocType Required Document Type
Step 2: DocType Expiry Alert Log
Step 3: DocType Asset Document (với các fields bổ sung từ GAP-01..05)
Step 4: DocType Document Request (mới — từ GAP-04)
Step 5: Custom Fields trên Asset (thêm custom_document_status)
Step 6: bench migrate
Step 7: api/imm05.py + __init__.py
Step 8: tasks.py scheduler
Step 9: asset_document.js client script
Step 10: imm05_dashboard page
Step 11: GW-2 hook trong asset_commissioning.py
Step 12: bench build + clear-cache + restart
```

### Giai đoạn C — UAT

Theo `IMM-05_UAT_Script.md`. Cần bổ sung 2 test case:
- TC-13: Luồng Exempt (thiết bị miễn đăng ký)
- TC-14: GW-2 blocking (asset không đủ hồ sơ → không Submit được IMM-04)

---

## 6. Quyết định cần có trước khi Dev

| # | Câu hỏi | Người quyết định | Tác động |
|---|---------|-----------------|----------|
| D-01 | Tên chuẩn cho Document Owner role: "Tổ HC-QLCL" hay "QA Risk Team"? | PTP Khối 2 / Workshop Head | Workflow fixture, permission matrix, email templates |
| D-02 | GW-2 check: Hard block (không Submit được) hay Soft warning? | Clinical Head + QA | asset_commissioning.py validate logic |
| D-03 | Document Request: DocType riêng hay dùng Frappe ToDo? | CMMS Admin | Dev effort + traceability |
| D-04 | Service Manual: mandatory cho tất cả hay chỉ thiết bị nhóm B/C? | Biomed Engineer | seed data + completeness pct formula |
| D-05 | document_status enum: dùng enum Select field hay tính động từ pct? | Dev + QA | Custom Field type + scheduler logic |

---

*Report được tạo bởi Claude Code — IMM-05 Readiness Audit 2026-04-17*
