# IMM-05 — Kiểm thử & An ninh (Testing, QA & Security)

| Mục | Giá trị |
|---|---|
| Module | **IMM-05 — Asset Document Repository** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | QA Lead + Tech Lead |
| Liên kết | [Module Overview](./IMM-05_Module_Overview.md) · [API Interface](./IMM-05_API_Interface.md) |

---

# Phần I — Test Plan

## I.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │  ← Playwright; Golden Scenario upload → approve → expire
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │  ← pytest + Frappe whitelist (14 endpoints)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │  ← pytest FrappeTestCase (6 states)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │    Unit — Controller + Scheduler Logic     │  ← TDD; validate, expiry, version control
     ─┴────────────────────────────────────────────┴─
```

Lưu ý: IMM-05 hiện chưa có `services/imm05.py` — business logic nằm trong controller `asset_document.py` và `tasks.py`. Tests cover controller + tasks. Tech-debt refactor ra service layer được track riêng.

Mỗi business rule (BR-05-01 → BR-05-10) có ≥ 1 happy + 1 negative test.

## I.2. Unit Test — Controller & Tasks

**File:** `assetcore/tests/test_imm05_controller.py`

| Test class | Hàm cover | Cases dự kiến |
|---|---|---|
| `TestUniqueDocNumber` | VR-02: unique doc_number per asset + type | happy (new number), fail (duplicate same asset+type) |
| `TestVersionControlArchive` | `archive_old_versions()` | happy (v1 Active → Archived when v2 Approved), no-op (no prior Active) |
| `TestDeletePrevention` | `on_trash()` | always raise — BR-05-02 |
| `TestExpiryValidation` | VR-01: expiry > issued_date | happy (expiry after issued), fail (expiry before issued) |
| `TestFileRequired` | VR-03: file on submit | happy (file attached), fail (no file when submit) |
| `TestLegalAuthorityRequired` | VR-04: issuing_authority for Legal | happy (set), fail (Legal + no authority) |
| `TestCertExpiryRequired` | VR-07: expiry_date for Certification | happy (set), fail (Certification + no expiry) |
| `TestChangeSummary` | BR-05-09: change_summary for v > 1.0 | happy (v1.0 no summary), fail (v2.0 no summary) |
| `TestVisibilityFilter` | `_apply_visibility_filter()` | Internal user → sees Internal_Only, Clinical Head → does not |
| `TestExemptComputation` | `_compute_document_status()` | exempt=1 → "Compliant (Exempt)", 100% active → "Compliant" |
| `TestGW2Gate` | `_gw2_check_document_compliance()` | has Active license → pass, Expired license → fail, is_exempt=1 → pass |

**File:** `assetcore/tests/test_imm05_tasks.py`

| Test class | Hàm cover | Cases dự kiến |
|---|---|---|
| `TestCheckDocumentExpiry` | `check_document_expiry()` | 90d: alert Info created (idempotent), 30d: alert Critical, 0d: doc → Expired, no duplicate same day |
| `TestUpdateAssetCompleteness` | `update_asset_completeness()` | 100% → Compliant, missing required → Incomplete, expired → At Risk |
| `TestOverdueDocumentRequests` | `check_overdue_document_requests()` | past due_date → status=Overdue, escalation sent |

**Pattern seed:**
```python
class TestVersionControlArchive(FrappeTestCase):
    def setUp(self):
        self.asset = make_asset("AC-ASSET-TEST-001")
        self.doc_v1 = make_asset_document(
            asset_ref=self.asset.name,
            doc_type_detail="Giấy phép nhập khẩu",
            version="1.0",
            workflow_state="Active"
        )

    def test_archive_old_on_new_approve(self):
        doc_v2 = make_asset_document(
            asset_ref=self.asset.name,
            doc_type_detail="Giấy phép nhập khẩu",
            version="2.0"
        )
        doc_v2.workflow_state = "Active"
        doc_v2.save()
        archive_old_versions(doc_v2)
        self.doc_v1.reload()
        self.assertEqual(self.doc_v1.workflow_state, "Archived")
        self.assertEqual(self.doc_v1.superseded_by, doc_v2.name)
```

## I.3. Unit Test — Validators & Repository

**File:** `assetcore/tests/test_imm05_validators.py`

| Validator | Happy | Fail |
|---|---|---|
| `_check_expiry_date_after_issued(doc)` | expiry > issued → pass | expiry ≤ issued → raise |
| `_check_file_format(attachment)` | PDF/JPG/PNG → pass | .exe → raise |
| `_check_file_size(attachment)` | 24.9 MB → pass | 25.1 MB → raise |
| `_check_no_active_duplicate(doc)` | no Active same type → pass | 1 Active same type → warn/block |
| `DocumentRepo.list(filters)` | Trả list đúng phân trang + visibility filter | Filter không hợp lệ → empty |
| `DocumentRepo.get(name)` | Trả doc đầy đủ | Không tồn tại → raise NOT_FOUND |
| `DocumentRepo.get_asset_documents(asset)` | Group theo category, completeness đúng | Asset không tồn tại → raise |

## I.4. Integration Test — DocType Lifecycle

**File:** `assetcore/tests/test_asset_document_doctype.py`

| Test | Setup | Action | Assert |
|---|---|---|---|
| `test_on_trash_always_blocked` | Asset Document Archived | `frappe.delete_doc(...)` | `frappe.PermissionError` hoặc custom `ValidationError` |
| `test_submit_without_file_blocked` | Draft doc, no attachment | `doc.workflow_state = "Pending Review"` + save | `ValidationError` chứa "VR-03" |
| `test_approve_archives_old_active` | 1 Active doc same type | New doc → Approved | Old doc workflow_state == "Archived" |
| `test_scheduler_expires_overdue_doc` | Active doc, expiry = yesterday | Run `check_document_expiry()` | doc.workflow_state == "Expired" |
| `test_change_summary_required_v2` | version = "2.0" | Save without change_summary | `ValidationError` chứa "change_summary" |
| `test_auto_import_from_imm04_on_submit` | Commissioning with docs at Clinical Release | `commissioning.submit()` | ≥ 3 Asset Document records, `source_module = "IMM-04"` |
| `test_gw2_gate_blocks_commissioning` | Asset với no Active license doc | IMM-04 `validate()` | `ValidationError` chứa "GW-2" |
| `test_exempt_bypasses_gw2` | Asset với `is_exempt = 1` | IMM-04 `validate()` | No raise |

## I.5. Integration Test — Workflow Transitions

**File:** `assetcore/tests/test_imm05_workflow.py`

Workflow `IMM-05 Document Workflow` có 6 state, 8 transition:

| Transition | From → To | Role required | Test |
|---|---|---|---|
| Gửi duyệt | Draft → Pending Review | Biomed Engineer, CMMS Admin | pass + fail(no file attached) |
| Phê duyệt | Pending Review → Active | Tổ HC-QLCL, CMMS Admin | pass + fail(wrong role=HTM Technician) |
| Từ chối | Pending Review → Rejected | Tổ HC-QLCL, CMMS Admin | pass + fail(no rejection_reason) |
| Gửi lại | Rejected → Pending Review | Biomed Engineer | pass |
| Lưu trữ thủ công | Active → Archived | CMMS Admin | pass + fail(wrong role) |
| Hủy bỏ | Draft → Archived | CMMS Admin | pass |
| (auto) Expire | Active → Expired | Scheduler | pass (expiry day run) |
| (auto) Archive cũ | Active → Archived | Controller | pass (on approve newer version) |

## I.6. Integration Test — Audit Chain Integrity

**File:** `assetcore/tests/test_imm05_audit.py`

```python
def test_version_history_recorded_on_each_state_change():
    # Create doc → submit → approve
    # Check frappe.get_all("Version", filters={"ref_doctype":"Asset Document", "docname": doc.name})
    # Assert >= 3 version records

def test_expiry_alert_log_idempotent():
    # Create Active doc, expiry = today + 30
    # Run check_document_expiry() twice same day
    # Assert Expiry Alert Log count == 1 (no duplicate)

def test_audit_trail_created_on_approve():
    # Approve document
    # Assert IMM Audit Trail record exists with event_type = "document_approved"
```

## I.7. API Test

**File:** `assetcore/tests/test_imm05_api.py`

| Test | Endpoint | Verify |
|---|---|---|
| `test_list_default_pagination` | `list_documents` | page=1, page_size=20, total ≥ 0 |
| `test_list_internal_only_hidden` | `list_documents` (as Clinical Head) | No Internal_Only rows returned |
| `test_get_existing` | `get_document?name=DOC-...` | `success=true`, fields đầy đủ |
| `test_get_not_found` | `get_document?name=FAKE` | `success=false`, `code=NOT_FOUND` |
| `test_create_happy` | `create_document` | `success=true`, DOC-xx-xxx trả về |
| `test_create_no_asset` | (no asset_ref) | `success=false`, `code=VALIDATION` |
| `test_create_no_permission` | role=Clinical Head | HTTP 403 |
| `test_approve_document_archives_old` | `approve_document` | Old doc → Archived |
| `test_reject_document_no_reason` | `reject_document` without reason | `code=VALIDATION` |
| `test_get_asset_documents_completeness` | `get_asset_documents?asset=ACC-...` | completeness % correct |
| `test_get_expiring_documents` | `get_expiring_documents?days=30` | Only docs expiring ≤ 30d |
| `test_mark_exempt` | `mark_exempt` | is_exempt=1, document_status="Compliant (Exempt)" |
| `test_mark_exempt_wrong_role` | `mark_exempt` by HTM Technician | HTTP 403 |
| `test_get_dashboard_stats` | `get_dashboard_stats` | `active_count`, `expiring_30d`, `expired_count` |

## I.8. E2E Browser (Playwright)

**File:** `assetcore/tests/e2e/test_imm05_golden.py`

**Golden scenario:** Upload doc (HTM Technician) → Gửi duyệt → Approve (Biomed) → Verify Active → Upload version 2 → Approve → Verify v1 Archived → Scheduler chạy → Verify Expired alert log.

Chạy: `pytest assetcore/tests/e2e/ -m imm05 --headed` (staging only).

## I.9. Performance Test

| Metric | Target | Phương pháp |
|---|---|---|
| `list_documents` p95 (500 docs) | ≤ 800 ms | k6 ramping 20 VU |
| `get_asset_documents` p95 (50 docs per asset) | ≤ 500 ms | k6 |
| `approve_document` (with archive old) p95 | ≤ 1.5 s | k6 |
| Scheduler `check_document_expiry` (1000 Active docs) | ≤ 60 s | bench execute + timer |
| `update_asset_completeness` (500 assets) | ≤ 120 s | bench execute + timer |
| File upload 25 MB PDF | ≤ 30 s | curl timing |

## I.10. Test Data

| Loại | Cách seed | File |
|---|---|---|
| AC Asset | `tests/fixtures/imm05_assets.json` | 5 assets (CT, X-Ray, Pump, Ventilator, LINAC) |
| Required Document Type | `tests/fixtures/imm05_required_doc_types.json` | CO, CQ, Manual, License, Radiation License |
| Asset Document (các state) | `tests/fixtures/imm05_documents.json` | Draft/Pending/Active/Archived/Expired per asset |
| Expiry Alert Log | — | Seeded by `check_document_expiry` run |
| UAT full seed | `scripts/uat/uat_imm05.py` | All assets + users + docs |

Reset script: `bench --site assetcore.local execute assetcore.scripts.uat.uat_imm05.seed_data`

## I.11. Run Commands & Coverage Gate

```bash
# Unit + integration
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm05_controller
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_asset_document_doctype

# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage

# UAT golden scenario
bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm05.run

# Manual scheduler test
bench --site assetcore.local execute assetcore.tasks.check_document_expiry
```

| Layer | Coverage target | Đo |
|---|---|---|
| Controller (`asset_document.py`) | ≥ 85% | `coverage report` |
| Tasks (`tasks.py` — imm05 funcs) | ≥ 75% | `coverage report` |
| API (`api/imm05.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | Không crash build | CI `npm run build` |

CI fail nếu coverage < target hoặc bất kỳ test nào fail.

## I.12. Đo Chất Lượng Mã Nguồn

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — Document views) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format chuẩn PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm05) | main chunk ≤ 250 KB gzip | ≤ budget | Mỗi PR FE (CI report) |

---

# Phần II — UAT Script

## II.1. Phạm vi UAT

**In-scope:**
- Upload, gửi duyệt, approve, reject (BR-05-01)
- Version control — archive tự động (BR-05-01)
- Xóa document bị block (BR-05-02)
- Expiry alert scheduler (BR-05-03)
- Auto-import từ IMM-04 (BR-05-04)
- Required Document Type completeness (BR-05-05)
- GW-2 gate cung cấp cho IMM-04 (BR-05-07)
- Exempt NĐ98 flow (BR-05-08)
- Visibility filter Internal_Only (BR-05-10)
- Dashboard KPIs
- Phân quyền mỗi role

**Out-of-scope (UAT):** Load testing, penetration testing (xử lý ở §I và §III).

**Pre-conditions:**
- UAT site: `uat.assetcore.vn` đã deploy bản mới nhất
- Seed data chạy: `uat_imm05.py seed_data`
- 6 tester accounts tạo (xem §II.2)
- ≥ 3 Asset đã được mint từ IMM-04
- Browser: Chrome ≥ 120

## II.2. Tester Accounts

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `test_ktvh` | ktvh@hospital.vn | HTM Technician | Upload doc, gửi duyệt |
| `test_biomed` | biomed@hospital.vn | Biomed Engineer | Approve/Reject doc |
| `test_qa` | qa@hospital.vn | Tổ HC-QLCL | Approve, mark exempt |
| `test_txn` | txn@hospital.vn | Workshop Head | Cancel/Amend, xem Dashboard |
| `test_vp` | vp@hospital.vn | VP Block2 | Nhận escalation, xem KPI |
| `test_clinical` | clinical@hospital.vn | Clinical Head | Read-only Public docs |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT).

## II.3. Test Data Đã Seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset | 5 | Các loại thiết bị, 2 bức xạ |
| Required Document Type | 5 | CO, CQ, Manual, License, Radiation License |
| Asset Document | 8 | Draft, Pending Review, Active, Archived, Expired (per asset) |
| Test PDF files | 3 | test-doc.pdf (<1MB), test-large.pdf (>25MB), test-expired-doc.pdf |

## II.4. Test Scenarios

### UAT-IMM05-01 — Upload tài liệu mới và gửi duyệt (Happy Path)

**Liên kết:** US-05-01, BR-05-01
**Role tester:** HTM Technician → Biomed Engineer
**Mục tiêu:** Upload doc, gửi duyệt, approve thành công → Active.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Đăng nhập `test_ktvh`, vào `/app/asset-document/new` | Form trống, status = Draft | ☐ |
| 2 | Chọn Asset = AC-ASSET-TEST-001; Nhóm = Legal; Loại = Giấy phép nhập khẩu | model_ref và clinical_dept tự fill | ☐ |
| 3 | Điền Số hiệu = NK-2026-0042; Cơ quan = Bộ Y tế; Ngày cấp = 2026-03-15; Hết hạn = 2027-06-30 | `days_until_expiry` tự tính | ☐ |
| 4 | Upload `test-doc.pdf` | File hiển thị tên + kích thước | ☐ |
| 5 | Click Save | Saved, naming `DOC-AC-ASSET-TEST-001-2026-00001` | ☐ |
| 6 | Click "Gửi Duyệt" | Status = Pending Review; field metadata read-only | ☐ |
| 7 | Đăng nhập `test_biomed`, mở doc | Thấy nút [Approve] và [Reject] | ☐ |
| 8 | Click Approve | Status = Active; `approved_by` = test_biomed; `approval_date` = today | ☐ |

**Acceptance:** Tất cả 8 step Pass.

---

### UAT-IMM05-02 — Reject và gửi lại

**Liên kết:** BR-05-01
**Role tester:** Tổ HC-QLCL → HTM Technician
**Mục tiêu:** Reject có lý do → gửi lại sau khi sửa.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `test_qa` mở doc đang Pending Review | Thấy nút [Reject] | ☐ |
| 2 | Click Reject mà KHÔNG điền lý do | Lỗi "Bắt buộc điền lý do từ chối" | ☐ |
| 3 | Điền lý do "File không đúng phiên bản", Confirm | Status = Rejected; notification gửi `test_ktvh` | ☐ |
| 4 | `test_ktvh` upload file mới, bấm "Gửi Lại" | Status = Pending Review | ☐ |
| 5 | `test_biomed` Approve | Status = Active | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM05-03 — Version Control: Archive tự động (BR-05-01)

**Liên kết:** BR-05-01
**Role tester:** HTM Technician + Biomed Engineer
**Mục tiêu:** Approve version mới → version cũ tự Archived.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Đã có 1 Active doc "Giấy phép nhập khẩu" v1.0 cho AC-ASSET-TEST-001 | — | ☐ |
| 2 | `test_ktvh` tạo doc mới: cùng Asset, cùng loại, version = "2.0", thêm change_summary | — | ☐ |
| 3 | Upload file mới, Save, Gửi Duyệt | Status = Pending Review | ☐ |
| 4 | `test_biomed` Approve doc v2.0 | Status = Active | ☐ |
| 5 | Kiểm tra doc v1.0 | `workflow_state` = Archived, `superseded_by` = doc v2.0 | ☐ |
| 6 | Verify: chỉ 1 Active cho loại này + asset | Count Active = 1 | ☐ |

**Acceptance:** Tất cả 6 step Pass.

---

### UAT-IMM05-04 — Block xóa document (BR-05-02)

**Liên kết:** BR-05-02
**Role tester:** CMMS Admin
**Mục tiêu:** Không ai được xóa cứng document.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở 1 Archived document | — | ☐ |
| 2 | Thử xóa qua UI (nếu có nút) | Lỗi "Không được phép xóa hồ sơ thiết bị y tế" | ☐ |
| 3 | Thử `frappe.delete_doc("Asset Document", ...)` qua console | `on_trash` raise | ☐ |
| 4 | Doc vẫn tồn tại với Archived state | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM05-05 — Expiry Alert Scheduler (BR-05-03)

**Liên kết:** BR-05-03
**Role tester:** System
**Mục tiêu:** Scheduler sinh alert đúng mốc, idempotent.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Seed 1 Active doc với expiry = today + 90 ngày | — | ☐ |
| 2 | Chạy `bench execute assetcore.tasks.check_document_expiry` | Expiry Alert Log tạo: alert_level = "Info", days_remaining = 90 | ☐ |
| 3 | Chạy lại lần 2 cùng ngày | Không tạo duplicate (idempotent) | ☐ |
| 4 | Đổi expiry = today + 30, chạy scheduler | Alert level = "Critical" | ☐ |
| 5 | Đổi expiry = today, chạy scheduler | Doc status → Expired; alert Danger | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM05-06 — Auto-import từ IMM-04 (BR-05-04)

**Liên kết:** BR-05-04
**Role tester:** System (triggered by IMM-04 Submit)
**Mục tiêu:** Submit Commissioning → Asset Document set tự tạo.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở Commissioning ở Clinical Release với 3 doc rows Received | — | ☐ |
| 2 | Submit Commissioning | Asset tạo, trigger `create_initial_document_set()` | ☐ |
| 3 | Mở IMM-05 List filter theo asset mới | ≥ 3 Asset Document records (Draft) | ☐ |
| 4 | Verify mỗi doc có `source_commissioning` đúng | Link về phiếu commissioning | ☐ |
| 5 | Verify `source_module = "IMM-04"` | Đúng | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM05-07 — Validation Rules

**Liên kết:** VR-01 → VR-07
**Role tester:** HTM Technician
**Mục tiêu:** Mọi validation rule hoạt động đúng.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Tạo doc: expiry_date = 2025-01-01, issued_date = 2026-01-01 | Lỗi "Ngày hết hạn phải sau ngày cấp" (VR-01) | ☐ |
| 2 | Tạo doc: cùng asset + type + doc_number | Lỗi "Số hiệu trùng lặp" (VR-02) | ☐ |
| 3 | Gửi duyệt doc không có file | Lỗi "File đính kèm bắt buộc" (VR-03) | ☐ |
| 4 | category = Legal, bỏ trống issuing_authority | Lỗi "Cơ quan cấp bắt buộc cho hồ sơ Pháp lý" (VR-04) | ☐ |
| 5 | category = Certification, bỏ trống expiry_date | Lỗi "Ngày hết hạn bắt buộc cho hồ sơ Kiểm định" (VR-07) | ☐ |
| 6 | Upload file > 25 MB | Lỗi "File quá lớn (tối đa 25 MB)" | ☐ |
| 7 | Upload file .exe | Lỗi "Chỉ chấp nhận PDF, JPG, PNG" | ☐ |
| 8 | version = "2.0", không điền change_summary | Lỗi "change_summary bắt buộc khi version > 1.0" (BR-05-09) | ☐ |

**Acceptance:** Tất cả 8 step Pass.

---

### UAT-IMM05-08 — Permission Matrix & Visibility

**Liên kết:** BR-05-10, Security §III.1
**Role tester:** Nhiều role
**Mục tiêu:** RBAC và visibility filter hoạt động đúng.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `test_clinical` thử tạo doc | Permission denied | ☐ |
| 2 | `test_clinical` mở doc Public của khoa mình | Visible, read-only | ☐ |
| 3 | `test_clinical` mở doc Internal_Only | Permission denied hoặc không hiện trong list | ☐ |
| 4 | `test_ktvh` thử Approve doc | Nút Approve không hiển thị | ☐ |
| 5 | `test_txn` Cancel Active doc | Thành công (Workshop Head) | ☐ |
| 6 | `test_qa` mark_exempt doc | Thành công; `is_exempt = 1` | ☐ |
| 7 | `test_ktvh` thử mark_exempt | HTTP 403 | ☐ |

**Acceptance:** Tất cả 7 step Pass.

---

### UAT-IMM05-09 — Dashboard KPIs

**Liên kết:** US-05-09
**Role tester:** Workshop Head
**Mục tiêu:** Dashboard KPIs phản ánh đúng, có thể drill-down.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `test_txn` mở `/imm-05/dashboard` | Dashboard load thành công | ☐ |
| 2 | Verify KPI "Active Docs" | Số = COUNT(Active) thực tế | ☐ |
| 3 | Verify KPI "Sắp hết hạn 90d" | Số đúng | ☐ |
| 4 | Verify KPI "Đã hết hạn" | Số đúng | ☐ |
| 5 | Click KPI "Đã hết hạn" | Chuyển sang List View filter Expired | ☐ |
| 6 | Verify bảng "Compliance theo Khoa" | % = actual/required đúng | ☐ |

**Acceptance:** Tất cả 6 step Pass.

---

### UAT-IMM05-10 — GW-2 Gate cho IMM-04

**Liên kết:** BR-05-07
**Role tester:** VP Block2
**Mục tiêu:** GW-2 block IMM-04 Submit khi thiếu Active license doc.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Asset với risk_class=C không có Active "License" doc trong IMM-05 | — | ☐ |
| 2 | Mở Commissioning phiếu cho asset này, bấm Phê Duyệt Release | Lỗi "GW-2: Thiếu chứng nhận ĐKLH Active" | ☐ |
| 3 | Upload và Approve License doc cho asset | — | ☐ |
| 4 | Bấm Phê Duyệt Release lại | Thành công | ☐ |
| 5 | Asset với `is_exempt = 1` | Phê Duyệt Release không bị block GW-2 | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

## II.5. Tổng Hợp Kết Quả & Bug Found

### Bảng kết quả

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM05-01 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM05-02 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM05-03 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM05-04 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM05-05 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM05-06 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM05-07 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM05-08 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM05-09 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM05-10 | ☐ Pass / ☐ Fail | | | |

### Sign-off UAT

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (IMM-05) | | | |
| Đại diện end-user (Tổ HC-QLCL) | | | |

**Quy ước go-live:** Blocker = 0, Major ≤ 2 (có workaround đã documented).

### Bug Log

| Issue ID | Severity | Mô tả | Fix status |
|---|---|---|---|
| IMM05-BUG-001 | Minor | Email notification template dùng inline string, chưa dùng Email Template DocType | Known — deferred |
| IMM05-BUG-002 | Minor | Service layer (`services/imm05.py`) chưa tách — logic vẫn trong controller | Tech-debt |

---

# Phần III — Security Review

## III.1. RBAC

### Role definitions

Xem `assetcore/fixtures/role.json` + `role_profile.json`. Các role liên quan IMM-05:

| Role | Asset Document | Document Request |
|---|---|---|
| HTM Technician | R/W/C (Draft, Pending Review) | R/W/C |
| Biomed Engineer | R/W/C (approve kỹ thuật) | R/W/C |
| Tổ HC-QLCL | R/W/C (approve/reject, mark exempt) | R/W/C |
| Workshop Head | R/W/C/Cancel/Amend | R/W/C/Delete |
| VP Block2 | R/W/Cancel | — |
| CMMS Admin | Full | Full |
| Clinical Head | R (Public only, own dept) | — |

### DocPerm Matrix — `Asset Document`

| Role | Read | Write | Create | Submit | Cancel | Amend | Delete |
|---|---|---|---|---|---|---|---|
| HTM Technician | ✅ | ✅ (Draft) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Biomed Engineer | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Tổ HC-QLCL | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Workshop Head | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| VP Block2 | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Clinical Head | ✅ (Public) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| CMMS Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

> **Quan trọng:** Không role nào có quyền Delete (BR-05-02 enforce via `on_trash`).

### Field-level permission (permlevel)

| Field | permlevel | Mô tả |
|---|---|---|
| `approved_by`, `approval_date` | 1 — Tổ HC-QLCL+ | Chỉ reviewer thấy và set |
| `rejection_reason` | 1 — Tổ HC-QLCL+ | Lý do từ chối nội bộ |
| `is_exempt`, `exempt_reason`, `exempt_proof` | 1 — Workshop Head / Tổ HC-QLCL | Quyết định exempt nhạy cảm |
| `visibility` | 1 — CMMS Admin+ | Chỉ Admin đổi visibility |

### Visibility filter (row-level)

```python
# _apply_visibility_filter() trong asset_document.py
_INTERNAL_ONLY_ROLES = [
    "HTM Technician", "Tổ HC-QLCL", "Biomed Engineer",
    "Workshop Head", "CMMS Admin", "System Manager"
]

def can_see_internal(user):
    for role in _INTERNAL_ONLY_ROLES:
        if frappe.has_role(role, user):
            return True
    return False
```

## III.2. API Security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ✅ | Mọi 14 endpoint có role check |
| CSRF | ✅ | Frappe default X-Frappe-CSRF-Token |
| Input validation | ✅ | `name` field validate; attachment extension check |
| SQL injection | ✅ | Frappe ORM parameterized |
| File upload security | ✅ | Extension whitelist + size limit 25 MB trong service |
| Rate limit | ⚠️ Roadmap | Cần config cho `approve_document` endpoint |

## III.3. Audit Trail Integrity

- Mọi state change (Draft/Pending/Active/Rejected/Archived/Expired) ghi qua Frappe `Version` DocType (auto) + `IMM Audit Trail` qua `log_audit_event()`.
- `on_trash` raise — không ai xóa được `Asset Document` (BR-05-02).
- `Expiry Alert Log` immutable — không có Delete permission cho bất kỳ role nào.
- `check_document_expiry` idempotent theo `alert_date` + `asset_document` composite unique.
- Retention: ≥ 5 năm theo NĐ98/2021 Điều 15.

## III.4. Authentication & Session

| Hạng mục | Config |
|---|---|
| Login | Frappe default — username + password |
| Session timeout | 8 giờ |
| Lockout | 3 fail → lock 15 phút |
| Password policy | Minimum 8 ký tự, 1 chữ hoa, 1 số |
| API key | Per-user, rotate mỗi 90 ngày |
| 2FA | Roadmap Phase 2 |

## III.5. Data Sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Giấy phép BYT | `file_attachment` (Legal category) | Confidential | Role permission + visibility |
| Lý do từ chối | `rejection_reason` | Internal | permlevel 1 |
| Quyết định exempt | `is_exempt`, `exempt_reason` | Confidential | permlevel 1 + role restriction |
| Thông tin người phê duyệt | `approved_by`, `approval_date` | Internal | permlevel 1 |
| Dữ liệu bệnh nhân | Không lưu | N/A | AssetCore KHÔNG lưu patient data |

## III.6. Vendor Isolation

`Vendor Engineer` không có quyền trực tiếp trên `Asset Document` trong DocPerm mặc định. Nếu cần mở rộng trong tương lai:
- Chỉ thấy doc với `visibility = Public` và `asset_ref` thuộc thiết bị họ đang maintain.
- Không thấy: Legal docs, rejection_reason, exempt fields.
- Không upload/approve.

## III.7. Secrets Management

- `site_config.json` không commit vào git.
- External API token lưu `frappe.conf`, không hardcode.
- Backup encrypt at-rest; off-site S3 theo `08_Deployment.md §I.2b`.
- File attachments lưu trong Frappe private files path (không public URL mặc định).

## III.8. Logging & Monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Document Expired tự động | WARNING | Scheduler log + Expiry Alert Log | ✅ Email Workshop Head, Biomed |
| Document Request overdue | WARNING | Scheduler log | ✅ Email Workshop Head, VP Block2 |
| on_trash attempt | ERROR | `frappe.log_error` | ❌ |
| Approve/Reject action | INFO | Frappe access log + IMM Audit Trail | ❌ |
| Login fail | INFO | Frappe login log | ✅ (sau 3 lần) |
| File upload fail (size/format) | INFO | Frappe error log | ❌ |

## III.9. Threat Model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Spoofing | Giả mạo session Reviewer | Low | High | Session HttpOnly + SameSite |
| Tampering — Delete doc | Xóa record qua admin/API | Low | Critical | `on_trash` raise + DocPerm no-delete |
| Tampering — Backdate expiry | Edit `expiry_date` sau approve | Low | High | permlevel + field locked sau Active |
| Repudiation | QA phủ nhận đã Approve | Low | High | `approved_by` + `approval_date` + IMM Audit Trail |
| Info Disclosure | Clinical Head thấy Internal_Only doc | Low | Medium | `_apply_visibility_filter()` + test UAT-08 |
| DoS — Scheduler | Expiry check 10,000+ Active docs | Low | Medium | Batch 200/run; index `expiry_date + workflow_state` |
| Elevation of Privilege | HTM Technician self-approve doc | Low | High | Workflow role check: Approve chỉ Tổ HC-QLCL/Biomed |

## III.10. Penetration Test

Trước release đầu tiên (go-live bệnh viện):
- Burp Suite / OWASP ZAP scan trên `uat.assetcore.vn` — 0 High/Critical open.
- Test: Clinical Head truy cập trực tiếp URL của Internal_Only doc → 403.
- CSRF token verify bằng curl không có token.
- Role escalation: thử gọi `approve_document` với role HTM Technician → 403.
- Test: thử gọi `frappe.delete_doc("Asset Document", ...)` với CMMS Admin → raise.
- Report lưu: `docs/security/pentest_imm05_v1.md`.

## III.11. Sign-off Security

| Vai trò | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Tech Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

**Điều kiện go-live:** Tất cả Sign-off là Pass hoặc Pass with conditions (workaround documented).

---

## DoD — Hoàn chỉnh

### I. Test Plan
- [x] Test class structure cho 11 controller functions + 3 task functions
- [x] ≥ 1 happy + 1 negative test mỗi BR (BR-05-01 → 10)
- [x] 8 workflow transitions đều có test
- [x] Audit trail test (idempotent expiry, delete block)
- [x] API test 14 endpoint ≥ 60% coverage target
- [x] Performance target xác định (k6)
- [x] CI command xác định
- [x] SonarQube + Lighthouse target xác định

### II. UAT
- [x] 10 UAT scenario, cover mọi 10 BR + permission + audit + dashboard
- [x] Test data seed script: `uat_imm05.py`
- [x] 6 Tester accounts + password documented
- [x] Known tech-debts (service layer, email template) documented
- [x] Sign-off section sẵn sàng

### III. Security
- [x] DocPerm matrix đầy đủ 7 role
- [x] Field-level permlevel xác định
- [x] Visibility filter documented + tested
- [x] Threat model ≥ 7 threat với mitigation
- [ ] Pentest report lưu `docs/security/` (trước go-live)
- [ ] Rate limit `approve_document` cấu hình (roadmap)
- [x] Vendor isolation policy documented
- [x] Sign-off section sẵn sàng
