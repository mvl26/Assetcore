# IMM-04 — Kiểm thử & An ninh (Testing, QA & Security)

| Mục | Giá trị |
|---|---|
| Module | **IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | QA Lead + Tech Lead |
| Liên kết | [Module Overview](./IMM-04_Module_Overview.md) · [Functional Specs](./IMM-04_Functional_Specs.md) · [API Interface](./IMM-04_API_Interface.md) |

---

# Phần I — Test Plan

## I.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │  ← Playwright; 1 Golden Scenario full commissioning
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │  ← pytest + Frappe whitelist (33 endpoints)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │  ← pytest FrappeTestCase (11 states)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │  ← TDD; bulk ở đây (gates + VRs)
     ─┴────────────────────────────────────────────┴─
```

Mọi service function phải có test trước khi code (TDD — CLAUDE.md §17). Mỗi gate (G01–G06) và validation rule (VR-01 → VR-07) có ≥ 1 happy + 1 negative test.

**Trạng thái thực tế (2026-05-14):**
- ✅ Test scaffold: **một file duy nhất** `assetcore/tests/test_imm04.py` (246 LOC). Các file con (`test_imm04_service.py`, `test_imm04_validators.py`, `test_imm04_workflow.py`, `test_imm04_audit.py`, `test_imm04_api.py`, `test_imm04_doctype.py`, e2e `test_imm04_golden.py`) **chưa được tách** — phần I.2–I.8 dưới đây là **kế hoạch chia file** đã được consolidate trong `test_imm04.py`.
- ✅ API count theo whitelist: **33 endpoints** (xem `05_API_Specification.md` §0 catalog đã refresh).

## I.2. Unit Test — Service Layer

**File:** `assetcore/tests/test_imm04_service.py`

| Test class | Hàm cover | Cases dự kiến |
|---|---|---|
| `TestInitializeCommissioning` | `initialize_commissioning()` | happy (Class B), happy (Class C → adds License row), Class D, Radiation |
| `TestUniqueSerial` | `_vr01_unique_serial_number()` | happy (SN mới), fail (SN đã gán Asset khác), fail (SN đã gán Commissioning khác) |
| `TestGateG01` | `validate_gate_g01()` | happy (100% Received/Waived), fail (1 Pending), fail (all Pending) |
| `TestGateG03` | `validate_gate_g03()` | happy (all Pass/N/A), fail (1 critical Fail), fail (empty checklist) |
| `TestGateG05G06` | `validate_gate_g05_g06()` | happy (no NC, approver set), fail (Open NC), fail (no approver) |
| `TestRadiationHold` | `check_auto_clinical_hold()` | Class A/B → False, Class C → True, Class D → True, Radiation → True |
| `TestDocumentExpiry` | `_validate_document_expiry()` | happy (future date), fail (past date), warning (< 30 days) |
| `TestMintAsset` | `create_erpnext_asset()` | happy (all fields correct), fail (duplicate serial), fail (no board_approver) |
| `TestCancelBlock` | `handle_commissioning_cancel()` | happy (no final_asset), fail (final_asset exists) |
| `TestLifecycleEvent` | `log_lifecycle_event()` | event appended, from/to/actor correct, timestamp auto-set |
| `TestVR05RiskClassWarning` | `_vr05_risk_class_change_warning()` | no change → pass, change before Initial Inspection → pass, change after → warning |
| `TestVR06Immutability` | `_vr06_immutable_lifecycle_events()` | existing event row → raise, new row → pass |

**Pattern seed:**
```python
class TestGateG01(FrappeTestCase):
    def setUp(self):
        self.doc = make_commissioning(
            risk_class="C",
            workflow_state="Pending Doc Verify"
        )
        # Pre-fill CO/CQ/Manual/License all Received
        self.doc.append("commissioning_documents", {
            "doc_type": "CO", "is_mandatory": 1, "status": "Pending"
        })

    def test_gate_g01_pass_all_received(self):
        for row in self.doc.commissioning_documents:
            row.status = "Received"
        validate_gate_g01(self.doc)  # không raise

    def test_gate_g01_fail_one_pending(self):
        with self.assertRaises(ServiceError) as ctx:
            validate_gate_g01(self.doc)  # CO = Pending
        self.assertIn("CO", str(ctx.exception))
```

## I.3. Unit Test — Validators & Repository

**File:** `assetcore/tests/test_imm04_validators.py`

| Validator | Happy | Fail |
|---|---|---|
| `_check_reception_date_not_future(doc)` | Date = today → pass | Date = tomorrow → raise |
| `_check_serial_length(sn)` | SN 10 chars → pass | SN 2 chars → warn; > 140 chars → raise |
| `_check_file_format(attachment)` | PDF → pass | .exe → raise |
| `_check_file_size(attachment)` | 19.9 MB → pass | 25.1 MB → raise |
| `CommissioningRepo.list(filters)` | Trả list đúng phân trang | Filter không hợp lệ → empty |
| `CommissioningRepo.get(name)` | Trả doc đầy đủ + asset_info | Không tồn tại → raise NOT_FOUND |

## I.4. Integration Test — DocType Lifecycle

**File:** `assetcore/tests/test_asset_commissioning_doctype.py`

| Test | Setup | Action | Assert |
|---|---|---|---|
| `test_before_insert_populates_mandatory_docs` | Item Class C, no prior commissioning | `doc.insert()` | `commissioning_documents` có CO + CQ + Manual + License row |
| `test_before_insert_class_b_no_license_row` | Item Class B | `doc.insert()` | No License row in `commissioning_documents` |
| `test_validate_blocks_future_reception_date` | reception_date = tomorrow | `doc.insert()` | `ValidationError` |
| `test_validate_vr01_duplicate_serial` | Asset với SN đã tồn tại | nhập same SN → `doc.save()` | `ValidationError` chứa "VR-01" |
| `test_vr06_immutable_lifecycle_event` | Commissioning có 1 lifecycle event | Edit event row → `doc.save()` | `ValidationError` chứa "VR-06" |
| `test_on_submit_mints_asset` | All gates pass, board_approver set | `doc.submit()` | `Asset` record tạo, `doc.final_asset != None` |
| `test_on_submit_creates_document_set` | All gates pass | `doc.submit()` | IMM-05 `Asset Document` records tạo |
| `test_on_cancel_blocked_if_asset_exists` | final_asset populated | `doc.cancel()` | `ValidationError` chứa "đã được kích hoạt" |
| `test_clinical_hold_auto_on_class_c` | risk_class = C, baseline all Pass | G03 pass action | workflow_state = "Clinical Hold" |

## I.5. Integration Test — Workflow Transitions

**File:** `assetcore/tests/test_imm04_workflow.py`

Workflow `IMM-04 Workflow` có 11 state, 15+ transition. Test mỗi transition:

| Transition | From → To | Role required | Test |
|---|---|---|---|
| Gửi kiểm tra tài liệu | Draft → Pending Doc Verify | HTM Technician / CMMS Admin | pass + fail(wrong role) |
| Xác nhận đủ tài liệu | Pending Doc Verify → To Be Installed | Biomed Engineer | pass + fail(G01 not met) |
| Yêu cầu bổ sung | Pending Doc Verify → Draft | Biomed Engineer | pass |
| Bắt đầu lắp đặt | To Be Installed → Installing | Biomed Engineer | pass |
| Báo sự cố | To Be Installed → Non Conformance | Biomed / Vendor Engineer | pass |
| Lắp đặt hoàn thành | Installing → Identification | Biomed / Vendor Engineer | pass |
| Báo DOA | Installing → Non Conformance | Biomed / Vendor Engineer | pass |
| Bắt đầu kiểm tra | Identification → Initial Inspection | Biomed Engineer | pass + fail(VR-01 not set) |
| Phê duyệt release | Initial Inspection → Clinical Release | System Manager / CMMS Admin | pass + fail(G06 no approver) + fail(G05 NC open) |
| Giữ lâm sàng | Initial Inspection → Clinical Hold | QA Officer | pass (Class C auto) |
| Tái kiểm | Initial Inspection → Re Inspection | Biomed Engineer | pass (after G03 fail) |
| Gỡ giữ lâm sàng | Clinical Hold → Clinical Release | QA Officer | pass (after license upload) |
| Phê duyệt sau tái kiểm | Re Inspection → Clinical Release | System Manager | pass + fail(G03 still failing) |
| Khắc phục xong | Non Conformance → To Be Installed | Biomed Engineer | pass |
| Trả hàng vendor | Non Conformance → Return To Vendor | System Manager | pass |

## I.6. Integration Test — Audit Chain Integrity

**File:** `assetcore/tests/test_imm04_audit.py`

```python
def test_lifecycle_events_appended_each_transition():
    # Tạo Commissioning → push qua Draft → PendingDocVerify → ToBeInstalled
    # Assert len(doc.lifecycle_events) == 3, event_type đúng

def test_audit_trail_immutable_after_log():
    # Sau khi log_lifecycle_event() → thử edit event row
    # Assert VR-06 raises ValidationError

def test_audit_trail_actor_matches_current_user():
    # Set frappe.session.user = "biomed.nguyen@hospital.vn"
    # Trigger transition → log event
    # Assert event.actor == "biomed.nguyen@hospital.vn"
```

## I.7. API Test

**File:** `assetcore/tests/test_imm04_api.py`

| Test | Endpoint | Verify |
|---|---|---|
| `test_list_default_pagination` | `list_commissionings` | page=1, page_size=20, total ≥ 0 |
| `test_list_filter_by_status` | `list_commissionings?filters={"workflow_state":"Draft"}` | Mọi row đúng state |
| `test_get_existing` | `get_commissioning?name=ACC-...` | `success=true`, fields đầy đủ |
| `test_get_not_found` | `get_commissioning?name=FAKE` | `success=false`, `code=NOT_FOUND` |
| `test_create_happy` | `create_commissioning` | `success=true`, ACC-xx-xx-xxxxx trả về |
| `test_create_no_po` | (no po_reference) | `success=false`, `code=VALIDATION` |
| `test_create_no_permission` | role=Clinical Head | HTTP 403 |
| `test_assign_identification_duplicate_sn` | `assign_identification` với SN trùng | `code=VALIDATION`, chứa "VR-01" |
| `test_gate_g01_block` | `submit_documents` khi CO Pending | `code=VALIDATION`, chứa "G01" |
| `test_approve_clinical_release_no_approver` | `approve_clinical_release` no board_approver | `code=VALIDATION`, chứa "G06" |
| `test_approve_clinical_release_nc_open` | `approve_clinical_release` với NC open | `code=VALIDATION`, chứa "G05" |
| `test_approve_clinical_release_happy` | all gates pass | `success=true`, Asset tạo |
| `test_get_dashboard_stats` | `get_dashboard_stats` | fields `active_count`, `pending_count`, `overdue_count` |
| `test_idempotent_submit` | submit 2 lần | 2nd call → `code=BAD_STATE` |
| `test_barcode_lookup` | `get_barcode_lookup?sn=PHI-XRAY-...` | Trả asset_ref đúng |

## I.8. E2E Browser (Playwright)

**File:** `assetcore/tests/e2e/test_imm04_golden.py`

**Golden scenario:** Tạo Commissioning từ PO → Upload docs → G01 Pass → Lắp đặt → Identification (scan QR) → Baseline tests → G03 Pass → Clinical Release → Verify Asset record created.

Chạy: `pytest assetcore/tests/e2e/ -m imm04 --headed` (staging only).

Kịch bản phụ: Class C → Clinical Hold → Upload license → Gỡ Hold → Approve.

## I.9. Performance Test

| Metric | Target | Phương pháp |
|---|---|---|
| `list_commissionings` p95 (200 records) | ≤ 800 ms | k6 ramping 20 VU |
| `create_commissioning` p95 | ≤ 1.5 s | k6 |
| `approve_clinical_release` (full flow) p95 | ≤ 3 s | k6 (tạo Asset + IMM-05 docs) |
| Scheduler `check_commissioning_overdue` (200 open) | ≤ 30 s | bench execute + timer |
| List view FE render (100 rows) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |
| Upload PDF 20 MB | ≤ 30 s | curl timing |

## I.10. Test Data

| Loại | Cách seed | File |
|---|---|---|
| Item (Device Models) | `tests/fixtures/imm04_items.json` | 4 items (Class B, C, D, Radiation) |
| Purchase Orders | `tests/fixtures/imm04_purchase_orders.json` | 3 PO gắn items trên |
| Asset Commissioning | `tests/fixtures/imm04_commissionings.json` | 5 records ở các state khác nhau |
| Commissioning Checklist Template | `tests/fixtures/imm04_checklist_templates.json` | 2 templates (Medical Imaging, Life Support) |
| UAT full seed | `scripts/uat/uat_imm04.py` | All items + users + POs + seed records |

Reset script: `bench --site assetcore.local execute assetcore.scripts.uat.uat_imm04.seed_data`

## I.11. Run Commands & Coverage Gate

```bash
# Unit + integration
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm04_service
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_asset_commissioning_doctype

# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage

# UAT golden scenario
bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm04.run
```

| Layer | Coverage target | Đo |
|---|---|---|
| Service (`services/imm04.py`) | ≥ 85% | `coverage report` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm04.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | Không crash build | CI `npm run build` |

CI fail nếu coverage < target hoặc bất kỳ test nào fail.

## I.12. Đo Chất Lượng Mã Nguồn

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — Commissioning views) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format chuẩn PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm04) | main chunk ≤ 250 KB gzip | ≤ budget | Mỗi PR FE (CI report) |

---

# Phần II — UAT Script

## II.1. Phạm vi UAT

**In-scope:**
- Tạo Commissioning từ PO (BR-04-01)
- Gate G01 — tài liệu bắt buộc (BR-04-02)
- VR-01 — Serial Number unique (BR-04-03)
- Gate G03 — baseline test pass (BR-04-04)
- VR-07 — Clinical Hold tự động Class C/D/Radiation (BR-04-05)
- Gate G05/G06 — No NC open + board_approver (BR-04-06, BR-04-07)
- GW-2 — IMM-05 compliance (BR-04-08)
- Audit trail immutability (VR-06)
- Auto-mint Asset + downstream triggers
- Dashboard KPIs
- Phân quyền mỗi role

**Out-of-scope (UAT):** Load testing, penetration testing, PDF print format (xử lý ở §I và §III, và roadmap).

**Pre-conditions:**
- UAT site: `uat.assetcore.vn` đã deploy bản mới nhất
- Seed data chạy thành công: `uat_imm04.py seed_data`
- 7 tester accounts tạo (xem §II.2)
- Browser: Chrome ≥ 120 hoặc Edge ≥ 120

## II.2. Tester Accounts

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `tbyt.le` | tbyt.le@hospital.vn | HTM Technician | Tạo phiếu từ PO, ghi nhận nhận hàng |
| `biomed.nguyen` | biomed.nguyen@hospital.vn | Biomed Engineer | Lắp đặt, gán SN, đo baseline |
| `vendor.tech` | vendor.tech@philips.com | Vendor Engineer | Xác nhận lắp đặt, báo DOA |
| `qa.pham` | qa.pham@hospital.vn | QA Officer | Clinical Hold, upload license, gỡ Hold |
| `ws.manager` | ws.manager@hospital.vn | Workshop Head | Submit/Cancel/Amend phiếu |
| `ceo.nguyen` | ceo.nguyen@hospital.vn | VP Block2 / Board | Board approver phê duyệt cuối |
| `cmms.admin` | cmms.admin@hospital.vn | CMMS Admin | Override khi cần; verify immutability |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT).

## II.3. Test Data Đã Seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| Item (Device Model) | 4 | Class B (pump), Class C (X-ray), Class D (ventilator), Radiation (LINAC) |
| Purchase Order | 3 | PO-2026-00023, PO-2026-00024, PO-2026-00025 |
| Asset Commissioning | 5 | Draft, Pending Doc Verify, Clinical Hold, Non Conformance, tiền-Release |
| Commissioning Checklist Template | 2 | Medical Imaging (6 items), Life Support (5 items) |
| Test users | 7 | Đủ role theo §II.2 |

## II.4. Test Scenarios

### UAT-IMM04-01 — Tạo Commissioning từ PO (Happy Path)

**Liên kết:** US-04-01, BR-04-01
**Role tester:** HTM Technician
**Mục tiêu:** Tạo phiếu từ PO hợp lệ, auto-fill thông tin, tạo bộ tài liệu bắt buộc.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Đăng nhập `tbyt.le`, vào `/imm-04/new` | Form tạo phiếu hiển thị | ☐ |
| 2 | Chọn PO: `PO-2026-00023` (Philips X-ray) | Auto-fill vendor, item, risk_class=C, badge đỏ | ☐ |
| 3 | Chọn Location: Khoa Chẩn Đoán Hình Ảnh | — | ☐ |
| 4 | Chọn Commissioned By: `biomed.nguyen` | — | ☐ |
| 5 | Nhập Reception Date: hôm nay | — | ☐ |
| 6 | Bấm "Lưu" | Toast "Phiếu nghiệm thu đã được tạo", naming ACC-YY-MM-##### | ☐ |
| 7 | Kiểm tra tab Tài liệu | Có 4 row: CO, CQ, Manual, License — tất cả Pending | ☐ |
| 8 | Kiểm tra Lifecycle Event | Event `status_changed` to Draft ghi nhận | ☐ |

**Acceptance:** Tất cả 8 step Pass.

---

### UAT-IMM04-02 — Block tạo Asset trực tiếp ERPNext (BR-04-01 Negative)

**Liên kết:** BR-04-01
**Role tester:** Biomed Engineer
**Mục tiêu:** Hệ thống chặn tạo Asset không qua IMM-04.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Đăng nhập `biomed.nguyen`, vào ERPNext → Asset → New | Form Asset ERPNext mở | ☐ |
| 2 | Chọn Item: `ITM-PUMP-BRAUN-001`, bấm Save | Lỗi "Tài sản TTBYT phải tạo qua Phiếu Nghiệm Thu IMM-04" | ☐ |
| 3 | Asset không được lưu trong DB | Verify list Asset không tăng | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

### UAT-IMM04-03 — Gate G01 — Block khi thiếu tài liệu bắt buộc (BR-04-02)

**Liên kết:** US-04-03, BR-04-02
**Role tester:** HTM Technician
**Mục tiêu:** Gate G01 block chuyển trạng thái khi CO còn Pending.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở phiếu ở Pending Doc Verify; CQ, Manual, License = Received; CO = Pending | — | ☐ |
| 2 | Bấm "Xác nhận đủ tài liệu" | Lỗi "Gate G01: Chưa đủ tài liệu bắt buộc. Còn thiếu: CO" | ☐ |
| 3 | Upload CO, đặt status = Received | — | ☐ |
| 4 | Bấm "Xác nhận đủ tài liệu" lại | Status = To Be Installed, Lifecycle Event ghi G01 pass | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM04-04 — VR-01: Validate Serial Number unique (BR-04-03)

**Liên kết:** US-04-02, BR-04-03
**Role tester:** Biomed Engineer
**Mục tiêu:** SN trùng bị block, SN mới được chấp nhận và QR tự sinh.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở phiếu ở Identification, nhập SN: `PHI-XRAY-2025-SN11111` (đã tồn tại) | Ngay khi blur: lỗi inline "VR-01: Serial đã gán cho thiết bị ACC-ASS-2025-00041" | ☐ |
| 2 | Nút "Xác Nhận Định Danh" disabled | — | ☐ |
| 3 | Thay SN = `PHI-XRAY-2026-SN98765` (mới) | Checkmark xanh "Serial hợp lệ" | ☐ |
| 4 | Bấm "Xác Nhận Định Danh" | QR code sinh tự động, Internal Tag `BV-CDHA-2026-001` điền; status → Initial Inspection | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM04-05 — Gate G03: Baseline Fail → Re Inspection (BR-04-04)

**Liên kết:** US-04-04, BR-04-04
**Role tester:** Biomed Engineer
**Mục tiêu:** Item critical fail trong baseline → tự động chuyển Re Inspection.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở phiếu ở Initial Inspection, điền CHK-ELEC-001 (Điện áp): Pass | — | ☐ |
| 2 | Điền CHK-ELEC-002 (Dòng rò, critical): Fail, measured=3.5mA | — | ☐ |
| 3 | Điền CHK-ELEC-003, CHK-FUNC-001, CHK-FUNC-002, CHK-MECH-001: Pass | — | ☐ |
| 4 | Bấm "Nộp Kết Quả Kiểm Tra" | Lỗi "Gate G03: 1 mục critical chưa đạt: Dòng rò vỏ máy"; status → Re Inspection | ☐ |
| 5 | Checklist tab = read-only | Không edit được | ☐ |
| 6 | Lifecycle Event ghi event_type=status_changed, to=Re Inspection | ☐ |

**Acceptance:** Tất cả 6 step Pass.

---

### UAT-IMM04-06 — Clinical Hold tự động Class C (BR-04-05, VR-07)

**Liên kết:** BR-04-05, VR-07
**Role tester:** Biomed Engineer + QA Officer
**Mục tiêu:** Class C sau G03 Pass tự động vào Clinical Hold, QA gỡ hold sau upload license.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Phiếu risk_class=C ở Initial Inspection, điền tất cả baseline Pass | — | ☐ |
| 2 | Bấm "Nộp Kết Quả Kiểm Tra" | Status tự động = Clinical Hold; alert modal "Thiết bị Class C phải có giấy phép BYT" | ☐ |
| 3 | `qa.pham` nhận notification | Notification đến | ☐ |
| 4 | QA Officer mở phiếu, upload License, expiry = 2028-06-30 | — | ☐ |
| 5 | Bấm "Gỡ Clinical Hold" | Status = Clinical Release; nút "Phê Duyệt Release" xuất hiện cho Board | ☐ |
| 6 | Lifecycle Events ghi cả `auto_hold` và `hold_cleared` | ☐ |

**Acceptance:** Tất cả 6 step Pass.

---

### UAT-IMM04-07 — Gate G05: Block Release khi có NC Open (BR-04-06)

**Liên kết:** BR-04-06, VR-04
**Role tester:** VP Block2
**Mục tiêu:** Gate G05 chặn release khi NC chưa đóng.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở phiếu ở Clinical Release (pending), NC `NC-ACC-TEST-NC-001-01` status=Under Review | — | ☐ |
| 2 | Chọn board_approver = `ceo.nguyen`, bấm "Phê Duyệt Release" | Lỗi "Gate G05: Còn 1 NC chưa đóng: NC-ACC-TEST-NC-001-01" | ☐ |
| 3 | Đóng NC (transfer/resolve) | NC status = Closed | ☐ |
| 4 | Bấm "Phê Duyệt Release" lại | Thành công | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM04-08 — Clinical Release thành công → tạo Asset (BR-04-07, BR-04-08)

**Liên kết:** US-04-06, BR-04-07, BR-04-08
**Role tester:** VP Block2
**Mục tiêu:** Toàn bộ flow qua đúng → Asset được mint, IMM-05 document set tạo.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở phiếu Class B, tất cả gates pass, board_approver = `ceo.nguyen` | — | ☐ |
| 2 | Bấm "Phê Duyệt Release" | Asset tạo, `doc.final_asset` điền | ☐ |
| 3 | Mở Asset vừa tạo | status = Active, `custom_vendor_serial`, `custom_internal_qr` đúng | ☐ |
| 4 | Mở IMM-05 List filter theo asset | ≥ 3 Asset Document records tạo tự động | ☐ |
| 5 | Lifecycle Event ghi `released` | ☐ |
| 6 | Notification gửi Purchase User | ☐ |

**Acceptance:** Tất cả 6 step Pass.

---

### UAT-IMM04-09 — DOA → Return To Vendor (BR-04-06)

**Liên kết:** BR-04-06
**Role tester:** Vendor Engineer + Workshop Head
**Mục tiêu:** Báo DOA khi đang lắp đặt → Non Conformance → Return To Vendor.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `vendor.tech` mở phiếu đang Installing, click "Khai Báo DOA" | Popup nhập thông tin NC | ☐ |
| 2 | Điền nc_type=DOA, severity=Critical, upload ảnh | — | ☐ |
| 3 | Submit | NC record tạo, status = Non Conformance | ☐ |
| 4 | `ws.manager` xem xét → bấm "Trả Hàng Vendor" | Status = Return To Vendor (TERMINAL), không tạo Asset | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM04-10 — VR-06: Audit Trail Bất Biến

**Liên kết:** VR-06
**Role tester:** CMMS Admin
**Mục tiêu:** Lifecycle Event không thể bị sửa bởi bất kỳ user nào.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở Commissioning có ≥ 2 Lifecycle Events | — | ☐ |
| 2 | Thử sửa actor/timestamp của event đầu tiên → Save | Lỗi "VR-06: Nhật ký sự kiện không được chỉnh sửa" | ☐ |
| 3 | Timeline tab chỉ hiển thị read-only | Không có Edit button | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

### UAT-IMM04-11 — Phân Quyền Role

**Liên kết:** Security §III.1
**Role tester:** Nhiều role
**Mục tiêu:** Role không đúng không thể trigger action.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `tbyt.le` gọi API `approve_clinical_release` | HTTP 403 | ☐ |
| 2 | `vendor.tech` thử gán Internal Tag | HTTP 403 | ☐ |
| 3 | `biomed.nguyen` mở phiếu, không có nút Cancel | — | ☐ |
| 4 | `ceo.nguyen` mở phiếu, có nút "Phê Duyệt Release" | — | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM04-12 — Dashboard KPIs

**Liên kết:** Functional Specs §Dashboard
**Role tester:** Workshop Head
**Mục tiêu:** Dashboard KPIs phản ánh đúng trạng thái thực tế.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `ws.manager` mở `/imm-04/dashboard` | Tất cả KPI card hiển thị | ☐ |
| 2 | Verify "Phiếu đang mở" | Đúng số phiếu docstatus=0 chưa terminal | ☐ |
| 3 | Verify "Quá hạn > 30 ngày" | Đúng số phiếu reception_date < (today - 30d) | ☐ |
| 4 | Click KPI card → redirect đến list view filter đúng | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

## II.5. Tổng Hợp Kết Quả & Bug Found

### Bảng kết quả

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM04-01 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-02 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-03 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-04 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-05 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-06 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-07 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-08 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-09 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-10 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-11 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM04-12 | ☐ Pass / ☐ Fail | | | |

### Sign-off UAT

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (IMM-04) | | | |
| Đại diện end-user (HTM Officer) | | | |

**Quy ước go-live:** Blocker = 0, Major ≤ 2 (có workaround đã documented). TC-32 (PM auto-create) là known FAIL — documented workaround.

### Bug Log

| Issue ID | Severity | Mô tả | Fix status |
|---|---|---|---|
| IMM04-BUG-032 | Major | PM auto-create sau Clinical Release chưa có listener ở IMM-08 | Known — deferred to IMM-08 Wave 2 |
| IMM04-BUG-033 | Minor | PDF Print Format Biên bản Bàn giao chưa config | Known — deferred |

---

# Phần III — Security Review

## III.1. RBAC

### Role definitions

Xem `assetcore/fixtures/role.json` + `role_profile.json`. Các role liên quan IMM-04:

| Role | Quyền trên Asset Commissioning |
|---|---|
| HTM Technician | Create, Read, Write |
| Biomed Engineer | Read, Write (không create, không submit) |
| Vendor Engineer | Read, Write (state Installing/To Be Installed only) |
| QA Officer | Read, Write (state Clinical Hold only) |
| Workshop Head | Read, Submit, Cancel, Amend, Print, Export |
| VP Block2 | Read, Submit, Cancel, Print, Export |
| CMMS Admin | Full |

### DocPerm Matrix — `Asset Commissioning`

| Role | Read | Write | Create | Submit | Cancel | Amend | Delete |
|---|---|---|---|---|---|---|---|
| HTM Technician | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Biomed Engineer | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Vendor Engineer | ✅ (partial) | ✅ (Installing only) | ❌ | ❌ | ❌ | ❌ | ❌ |
| QA Officer | ✅ | ✅ (Clinical Hold only) | ❌ | ❌ | ❌ | ❌ | ❌ |
| Workshop Head | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| VP Block2 | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| CMMS Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### Field-level permission (permlevel)

| Field | permlevel | Mô tả |
|---|---|---|
| `board_approver` | 1 — VP Block2+ | Chỉ Board/CMMS Admin chọn |
| `approval_remarks` | 1 — VP Block2+ | Ghi chú phê duyệt ẩn với KTV |
| `final_asset` | 1 — Workshop Head+ | Field link Asset sau submit |
| `lifecycle_events` (child) | 1 — Read-only all | Không ai được edit |

### User Permission (Row-level)

`permission_query_conditions` trong `assetcore/permissions.py` sẽ cần bổ sung nếu multi-hospital deploy:
```python
def commissioning_query(user):
    if frappe.has_role("CMMS Admin", user) or frappe.has_role("System Manager", user):
        return ""
    # Filter theo hospital nếu multi-tenant
    return ""  # Single-hospital: no row filter needed
```

## III.2. API Security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ✅ | Mọi `@frappe.whitelist()` có role check |
| CSRF | ✅ | Frappe default X-Frappe-CSRF-Token |
| Input validation | ✅ | `name` field validate qua `frappe.get_value` |
| SQL injection | ✅ | Frappe ORM parameterized; không raw SQL trong imm04.py |
| Rate limit | ⚠️ Roadmap | Cần config cho `approve_clinical_release` endpoint |
| File upload validation | ✅ | Format (PDF/JPG/PNG/TIFF) + size (≤ 20 MB) check ở service |

## III.3. Audit Trail Integrity

- Mọi state change sinh `Lifecycle Event` row qua `log_lifecycle_event()` — VR-06 block edit.
- `Asset Lifecycle Event` là child table của `Asset Commissioning` — không có separate hash chain tại module này (khác với IMM Audit Trail global).
- Sau `on_submit`: `IMM Audit Trail` global ghi event `commissioned` qua `log_audit_event()` + `create_lifecycle_event()` trong `assetcore/utils/lifecycle.py`.
- Test tamper: `test_vr06_immutable_lifecycle_event()` (§I.4).
- Retention: ≥ 5 năm theo NĐ98/2021/NĐ-CP Điều 15.

## III.4. Authentication & Session

| Hạng mục | Config |
|---|---|
| Login | Frappe default — username + password |
| Session timeout | 8 giờ (config `frappe.conf.session_expiry`) |
| Lockout policy | Frappe default: 3 lần fail → lock 15 phút |
| Password policy | Minimum 8 ký tự, 1 chữ hoa, 1 số |
| API key | Per-user, rotate mỗi 90 ngày |
| 2FA | Roadmap Phase 2 — TOTP via Frappe 2FA |

## III.5. Data Sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Số serial thiết bị | `vendor_serial_no`, `internal_tag` | Internal | Role permission |
| Phê duyệt BGĐ | `board_approver`, `approval_remarks` | Confidential | permlevel 1 |
| Thông tin vendor | `vendor`, `po_reference` | Internal | Role permission |
| Giấy phép BYT | `commissioning_documents` License row | Confidential | Role permission |
| Dữ liệu bệnh nhân | Không lưu | N/A | AssetCore KHÔNG lưu patient data |

## III.6. Vendor Isolation

`Vendor Engineer` chỉ được phép:
- Edit phiếu khi ở state `Installing` hoặc `To Be Installed`
- Trigger transition "Lắp đặt hoàn thành" và "Khai báo DOA"
- Không thấy: `board_approver`, `approval_remarks`, tổng giá trị PO, audit trail của vendors khác
- Không export bulk, không print

## III.7. Secrets Management

- `site_config.json` không commit vào git (`.gitignore` đã cấu hình)
- External API token (email, SMS) lưu `frappe.conf`, không hardcode
- Backup encrypt at-rest; off-site S3 theo `08_Deployment.md §I.2b`
- Secret scan CI: `git-secrets` hoặc `detect-secrets` trong pre-commit hook

## III.8. Logging & Monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Clinical Release thành công | INFO | `frappe.log_error` (level INFO) + IMM Audit Trail | ✅ Email Purchase User |
| Commissioning overdue > 30 ngày | WARNING | Scheduler log | ✅ Email Workshop Head |
| Cancel blocked (Asset exists) | WARNING | `frappe.log_error` | ❌ |
| API 4xx (permission denied) | INFO | Frappe access log | ❌ |
| Login fail | INFO | Frappe login log | ✅ (sau 3 lần) |
| Audit trail tamper attempt | ERROR | `frappe.log_error` | ✅ Email CMMS Admin |

## III.9. Threat Model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Spoofing | Giả mạo session TBYT Officer | Low | High | Session HttpOnly + SameSite; Frappe session verify |
| Tampering — Lifecycle | Sửa `lifecycle_events` child row | Low | Critical | VR-06 block edit + `permlevel=1` |
| Tampering — Serial | Thay SN sau khi đã gán Asset | Low | High | VR-01 unique check; `vendor_serial_no` locked sau Submit |
| Repudiation | Vendor phủ nhận đã lắp đặt | Low | Medium | `lifecycle_events` ghi actor + IP; timestamp immutable |
| Info Disclosure | Vendor thấy giá trị PO của hospital | Low | Medium | `board_approver`/cost fields permlevel 1 + Vendor role restriction |
| DoS — Scheduler | Overdue job quét 10,000+ commissionings | Low | Medium | Index `workflow_state + reception_date`; batch 200/run |
| Elevation of Privilege | HTM Technician tự Submit/Cancel | Low | High | Workflow role check; Submit chỉ Workshop Head/VP Block2 |

## III.10. Penetration Test

Trước go-live bệnh viện đầu tiên:
- Burp Suite / OWASP ZAP scan trên `uat.assetcore.vn` — 0 High/Critical open
- sqlmap (mode safe) trên API `create_commissioning`, `approve_clinical_release`
- CSRF token verify bằng curl không có token
- Role escalation: thử gọi `approve_clinical_release` với role HTM Technician → 403
- Report lưu: `docs/security/pentest_imm04_v1.md`

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
- [x] Test class structure cho 12 service functions (gates + VRs)
- [x] ≥ 1 happy + 1 negative test mỗi function
- [x] 15 workflow transitions đều có test
- [x] Audit trail test (VR-06 immutability)
- [x] API test 15 endpoint ≥ 60% coverage target
- [x] Performance target xác định (k6)
- [x] CI command xác định
- [x] SonarQube + Lighthouse target xác định

### II. UAT
- [x] 12 UAT scenario, cover mọi 8 BR + permission + audit + dashboard
- [x] Mọi Business Rule (BR-04-01 → 08) có ≥ 1 UAT scenario
- [x] Test data seed script: `uat_imm04.py`
- [x] 7 Tester accounts + password documented
- [x] Known issue TC-32 (PM auto-create) documented
- [x] Sign-off section sẵn sàng

### III. Security
- [x] DocPerm matrix đầy đủ 7 role
- [x] Field-level permlevel xác định
- [x] Threat model ≥ 7 threat với mitigation
- [ ] Pentest report lưu `docs/security/` (trước go-live)
- [ ] Rate limit `approve_clinical_release` cấu hình (roadmap)
- [x] Vendor isolation policy documented
- [x] Sign-off section sẵn sàng
