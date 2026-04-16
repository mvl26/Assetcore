# IMM-05 UAT Script

**Module:** IMM-05 — Đăng ký, Cấp phép & Quản lý Hồ sơ Thiết bị Y tế
**Version:** 1.0-draft
**Ngày:** 2026-04-16
**Trạng thái:** CHỜ PHÊ DUYỆT

---

## 1. Tổng quan

### 1.1 Mục tiêu UAT

Xác nhận module IMM-05 hoạt động đúng theo Functional Spec, bao gồm:
- Luồng upload → review → approve/reject
- Version control (archive tự động)
- Auto-import từ IMM-04
- Expiry alert scheduler
- Dashboard KPIs
- Permission & audit trail

### 1.2 Preconditions

| # | Điều kiện | Cách chuẩn bị |
|---|----------|---------------|
| PC-01 | Có ít nhất 3 Asset đã mint từ IMM-04 | Chạy IMM-04 flow đến Clinical_Release |
| PC-02 | Có user với role HTM Technician | Tạo test user: `test_ktvh@assetcore.test` |
| PC-03 | Có user với role Biomed Engineer | Tạo test user: `test_biomed@assetcore.test` |
| PC-04 | Có user với role QA Risk Team | Tạo test user: `test_qa@assetcore.test` |
| PC-05 | Có user với role Workshop Head | Tạo test user: `test_txn@assetcore.test` |
| PC-06 | Có user với role Clinical Head | Tạo test user: `test_clinical@assetcore.test` |
| PC-07 | Required Document Types đã seed | Chạy migrate + fixtures |
| PC-08 | Workflow IMM-05 đã active | Verify via Setup > Workflow |
| PC-09 | File PDF test (< 25MB) | Chuẩn bị `test-doc.pdf` |
| PC-10 | File PDF test (> 25MB) | Chuẩn bị `test-large.pdf` |

### 1.3 Test Data

| Asset | Item/Model | Khoa | is_radiation | Ghi chú |
|-------|-----------|------|:------------:|---------|
| AST-TEST-001 | CT Scanner XYZ | ICU | Yes | Thiết bị bức xạ — cần giấy phép |
| AST-TEST-002 | Monitor ABC | OR | No | Thiết bị thường |
| AST-TEST-003 | X-Ray DEF | Cấp cứu | Yes | Thiết bị bức xạ |

---

## 2. Kịch bản kiểm thử

### TC-01: Upload tài liệu mới (Happy Path)

**Actor:** HTM Technician (`test_ktvh`)
**Precondition:** PC-01, PC-02, PC-09

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| 1 | Login với `test_ktvh` | Đăng nhập thành công | ☐ |
| 2 | Mở /app/asset-document/new | Form trống hiện ra, status = Draft | ☐ |
| 3 | Chọn Asset = AST-TEST-001 | `model_ref` và `clinical_dept` tự fill | ☐ |
| 4 | Chọn Nhóm = "Legal" | Field `issuing_authority` hiện required hint | ☐ |
| 5 | Chọn Loại = "Giấy phép nhập khẩu" | — | ☐ |
| 6 | Điền Số hiệu = "NK-2026-0042" | — | ☐ |
| 7 | Điền Ngày cấp = 2026-03-15 | — | ☐ |
| 8 | Điền Ngày hết hạn = 2027-06-30 | `days_until_expiry` tự tính | ☐ |
| 9 | Điền Cơ quan cấp = "Bộ Y tế" | — | ☐ |
| 10 | Upload file test-doc.pdf | File hiển thị tên + kích thước | ☐ |
| 11 | Click Save | Doc saved, status = Draft | ☐ |
| 12 | Verify naming: `DOC-AST-TEST-001-2026-00001` | Naming series đúng format | ☐ |

---

### TC-02: Gửi duyệt và Approve

**Actor:** HTM Technician → Biomed Engineer
**Precondition:** TC-01 passed

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| 1 | (test_ktvh) Click "Gửi Duyệt" | Status → Pending_Review | ☐ |
| 2 | Verify: field metadata → read-only | Không thể edit | ☐ |
| 3 | Login với `test_biomed` | — | ☐ |
| 4 | Mở document vừa tạo | Thấy nút [Approve] và [Reject] | ☐ |
| 5 | Click [Approve] | Status → Active | ☐ |
| 6 | Verify: `approved_by` = test_biomed | Đúng | ☐ |
| 7 | Verify: `approval_date` = today | Đúng | ☐ |
| 8 | Verify: Toast thông báo thành công | Hiện toast xanh | ☐ |

---

### TC-03: Reject tài liệu

**Actor:** QA Risk Team
**Precondition:** 1 document ở Pending_Review

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| 1 | (test_qa) Mở document Pending_Review | Thấy nút [Reject] | ☐ |
| 2 | Click [Reject] | Dialog popup yêu cầu lý do | ☐ |
| 3 | Bấm "Xác nhận" mà KHÔNG điền lý do | Lỗi: "Bắt buộc điền lý do từ chối" | ☐ |
| 4 | Điền lý do: "File không đúng phiên bản" | — | ☐ |
| 5 | Bấm "Xác nhận" | Status → Rejected | ☐ |
| 6 | Verify: `rejection_reason` = "File không đúng phiên bản" | Đúng | ☐ |
| 7 | Verify: notification gửi cho test_ktvh | Thấy notification | ☐ |

---

### TC-04: Version Control (Archive tự động)

**Actor:** HTM Technician + Biomed Engineer
**Precondition:** TC-02 passed (có 1 Active doc "Giấy phép nhập khẩu" cho AST-TEST-001)

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| 1 | (test_ktvh) Tạo doc mới: cùng Asset, cùng loại | — | ☐ |
| 2 | Điền version = "2.0", doc_number khác | — | ☐ |
| 3 | Upload file mới, Save, Gửi Duyệt | Status = Pending_Review | ☐ |
| 4 | (test_biomed) Approve doc mới | Status → Active | ☐ |
| 5 | Verify: doc cũ (v1.0) → Archived | `workflow_state` = Archived | ☐ |
| 6 | Verify: doc cũ `archived_by_version` = "2.0" | Đúng | ☐ |
| 7 | Verify: doc cũ `superseded_by` = doc mới | Link đúng | ☐ |
| 8 | Verify: chỉ 1 Active cho loại này + asset | Count = 1 | ☐ |

---

### TC-05: Auto-import từ IMM-04

**Actor:** System (triggered by IMM-04 Submit)
**Precondition:** 1 phiếu Asset Commissioning ở Clinical_Release, chưa Submit

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| 1 | Mở phiếu Commissioning ở Clinical_Release | — | ☐ |
| 2 | Verify: commissioning_documents có 3 row Received | — | ☐ |
| 3 | Submit phiếu Commissioning | Asset mới được mint | ☐ |
| 4 | Mở Asset mới | Verify `custom_vendor_serial`, `custom_internal_qr` | ☐ |
| 5 | Mở List Asset Document, filter theo asset mới | Phải có >= 3 records (Draft) | ☐ |
| 6 | Verify: mỗi doc có `source_commissioning` đúng | Link về phiếu commissioning | ☐ |
| 7 | Verify: mỗi doc có `source_module` = "IMM-04" | Đúng | ☐ |
| 8 | Nếu thiết bị bức xạ: verify doc "Giấy phép bức xạ" | Phải có 1 doc Legal | ☐ |

---

### TC-06: Validation Rules

**Actor:** HTM Technician

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| **VR-01** | | | |
| 1 | Tạo doc: expiry_date = 2025-01-01, issued_date = 2026-01-01 | Lỗi: "Ngày hết hạn phải sau ngày cấp" | ☐ |
| **VR-02** | | | |
| 2 | Tạo doc: cùng asset + cùng type + cùng doc_number | Lỗi: "Số hiệu trùng lặp" | ☐ |
| **VR-03** | | | |
| 3 | Tạo doc: không upload file → Gửi Duyệt | Lỗi: "File đính kèm bắt buộc" | ☐ |
| **VR-04** | | | |
| 4 | Tạo doc: category = Legal, bỏ trống issuing_authority | Lỗi: "Cơ quan cấp bắt buộc cho hồ sơ Pháp lý" | ☐ |
| **VR-07** | | | |
| 5 | Tạo doc: category = Certification, bỏ trống expiry_date | Lỗi: "Ngày hết hạn bắt buộc cho hồ sơ Kiểm định" | ☐ |
| **File size** | | | |
| 6 | Upload file > 25MB | Lỗi: "File quá lớn (tối đa 25MB)" | ☐ |
| **File format** | | | |
| 7 | Upload file .exe | Lỗi: "Chỉ chấp nhận PDF, JPG, PNG" | ☐ |

---

### TC-07: Expiry Alert Scheduler

**Actor:** System (scheduler)
**Precondition:** 1 Active doc có expiry_date = today + 90 ngày

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| 1 | Chạy `bench execute assetcore.tasks.check_document_expiry` | — | ☐ |
| 2 | Mở Expiry Alert Log list | Có 1 record mới | ☐ |
| 3 | Verify: alert_level = "Info" | Đúng | ☐ |
| 4 | Verify: days_remaining = 90 | Đúng | ☐ |
| 5 | Chạy lại lần 2 cùng ngày | KHÔNG tạo duplicate | ☐ |
| 6 | Đổi expiry_date = today + 30 | — | ☐ |
| 7 | Chạy scheduler | Alert level = "Critical" | ☐ |
| 8 | Đổi expiry_date = today | — | ☐ |
| 9 | Chạy scheduler | Doc status → Expired + alert Danger | ☐ |

---

### TC-08: Permission Matrix

**Mục đích:** Xác nhận RBAC đúng theo actor table

| Action | ktvh | biomed | qa | txn | vp | clinical |
|--------|:----:|:------:|:--:|:---:|:--:|:--------:|
| Create doc | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Edit Draft | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Submit Review | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Approve | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Reject | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Cancel/Amend | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ |
| Read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| View other dept docs | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |

**Test Steps:**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| 1 | (clinical) Try create doc | Permission denied | ☐ |
| 2 | (clinical) Open doc from own dept | Visible, read-only | ☐ |
| 3 | (clinical) Open doc from other dept | Permission denied | ☐ |
| 4 | (ktvh) Try approve doc | Button not visible | ☐ |
| 5 | (biomed) Try cancel doc | Button not visible | ☐ |
| 6 | (txn) Cancel Active doc | Success | ☐ |

---

### TC-09: Dashboard KPIs

**Actor:** Workshop Head hoặc VP Block2

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| 1 | Mở /app/imm05-dashboard | Dashboard load thành công | ☐ |
| 2 | Verify KPI "Active Docs" | Số = count(Active) | ☐ |
| 3 | Verify KPI "Sắp hết hạn 90d" | Số = count(Active + expiry <= 90d) | ☐ |
| 4 | Verify KPI "Đã hết hạn" | Số = count(Expired) | ☐ |
| 5 | Verify KPI "Thiếu hồ sơ" | Số = count(assets with incomplete docs) | ☐ |
| 6 | Click KPI "Đã hết hạn" | Chuyển sang List View filter Expired | ☐ |
| 7 | Verify bảng "Timeline Hết hạn" | Sorted by expiry_date ASC | ☐ |
| 8 | Verify bảng "Compliance theo Khoa" | % = actual/required per dept | ☐ |
| 9 | Verify bảng "Assets Thiếu" | Hiện đúng missing doc types | ☐ |

---

### TC-10: Delete Prevention (BR-02)

**Actor:** CMMS Admin

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| 1 | Mở 1 Archived document | — | ☐ |
| 2 | Try delete (nếu có nút) | Lỗi: "Không được phép xóa" | ☐ |
| 3 | Try delete via API: `frappe.delete_doc(...)` | Lỗi: on_trash block | ☐ |
| 4 | Verify: doc vẫn tồn tại | Doc status không đổi | ☐ |

---

### TC-11: Audit Trail

**Mục đích:** Xác nhận mọi action đều có log

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|----------|-------------------|:---------:|
| 1 | Tạo doc → Save | Version History ghi nhận "Created" | ☐ |
| 2 | Gửi duyệt | Version History: "workflow_state: Draft → Pending_Review" | ☐ |
| 3 | Approve | Version History: "workflow_state: Pending → Active" + "approved_by set" | ☐ |
| 4 | Archive (by new version) | Version History: "workflow_state: Active → Archived" | ☐ |
| 5 | Expire (by scheduler) | Version History: "workflow_state: Active → Expired" | ☐ |
| 6 | Mở Activity tab trên form | Timeline hiện đầy đủ các event | ☐ |

---

### TC-12: API Endpoints

**Mục đích:** Test API cho Vue Frontend

| # | Endpoint | Method | Test | Kết quả mong đợi | Pass/Fail |
|---|----------|--------|------|-------------------|:---------:|
| 1 | imm05.list_documents | GET | No filters | Trả về paginated list | ☐ |
| 2 | imm05.list_documents | GET | filter={"doc_category":"Legal"} | Chỉ Legal docs | ☐ |
| 3 | imm05.get_document | GET | name=DOC-... | Trả về full doc | ☐ |
| 4 | imm05.get_document | GET | name=INVALID | Error NOT_FOUND | ☐ |
| 5 | imm05.create_document | POST | Valid data | Trả về new doc name | ☐ |
| 6 | imm05.create_document | POST | Missing asset_ref | Error MISSING_FIELDS | ☐ |
| 7 | imm05.approve_document | POST | Valid Pending doc | State → Active | ☐ |
| 8 | imm05.approve_document | POST | Draft doc | Error WRONG_STATE | ☐ |
| 9 | imm05.reject_document | POST | No reason | Error VALIDATION | ☐ |
| 10 | imm05.get_asset_documents | GET | asset=AST-... | Grouped by category | ☐ |
| 11 | imm05.get_dashboard_stats | GET | — | KPIs + breakdown | ☐ |
| 12 | imm05.get_expiring_documents | GET | days=90 | Docs within 90d | ☐ |
| 13 | imm05.get_compliance_by_dept | GET | — | Dept list + % | ☐ |

---

## 3. Test Sign-off

| Nhóm | Tổng TC | Pass | Fail | Block | Tester | Ngày |
|------|:-------:|:----:|:----:|:-----:|--------|------|
| Upload & CRUD | TC-01, TC-06 | — | — | — | | |
| Workflow | TC-02, TC-03 | — | — | — | | |
| Version Control | TC-04 | — | — | — | | |
| Auto-import | TC-05 | — | — | — | | |
| Scheduler | TC-07 | — | — | — | | |
| Permission | TC-08 | — | — | — | | |
| Dashboard | TC-09 | — | — | — | | |
| Delete Prevention | TC-10 | — | — | — | | |
| Audit Trail | TC-11 | — | — | — | | |
| API | TC-12 | — | — | — | | |
| **TỔNG** | **12** | — | — | — | | |

### Sign-off Criteria

- **Pass:** 100% TC Pass (0 Fail, 0 Block)
- **Conditional Pass:** >= 90% Pass, Fail items đều P2 (cosmetic), có remediation plan
- **Fail:** Bất kỳ P0/P1 Fail → block release

### Approvers

| Role | Tên | Chữ ký | Ngày |
|------|-----|--------|------|
| BA Lead | | | |
| Dev Lead | | | |
| QA Lead | | | |
| Khoa trưởng đại diện | | | |
