# IMM-11 — Kiểm thử & An ninh (Testing, QA & Security)

| Mục | Giá trị |
|---|---|
| Module | **IMM-11 — Hiệu chuẩn (Calibration)** |
| Phiên bản | 1.1.0 |
| Ngày cập nhật | 2026-05-14 |
| Owner | QA Lead + Tech Lead |
| Trạng thái | 🟡 Tests cốt lõi đã có (`assetcore/tests/test_imm11.py`); UAT/E2E/Pentest pending |
| Liên kết | [Module Overview](./IMM-11_Module_Overview.md) · [Functional Specs](./IMM-11_Functional_Specs.md) · [UAT Script](./IMM-11_UAT_Script.md) |

---

# Phần I — Test Plan

## I.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │  ← Playwright; bắt buộc 1 Golden Scenario
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │  ← pytest + Frappe whitelist
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │  ← pytest FrappeTestCase
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │  ← TDD; bulk ở đây
     ─┴────────────────────────────────────────────┴─
```

⚠️ **Pending implementation** — Mọi test class phải được viết trước khi implement service (TDD — CLAUDE.md §17). Mỗi BR (BR-11-01 → BR-11-07) cần ≥ 1 happy + 1 negative test.

## I.2. Unit Test — Service Layer

**File hiện hữu:** `assetcore/tests/test_imm11.py` ✅ (đang cover các BR-11-xx chính; bổ sung thêm case khi cần)

| Test class | Hàm cover | Cases dự kiến |
|---|---|---|
| `TestLabValidation` | `validate_lab_iso_17025()` | happy(certified lab), fail(not certified), fail(no lab_supplier) |
| `TestCertificateValidation` | `validate_external_certificate()` | happy(all fields), fail(no cert_file), fail(no accreditation_number), fail(future cert_date) |
| `TestMeasurementCompute` | `compute_measurement_results()` | all Pass, 1 Fail, all Fail, empty table, zero tolerance special case |
| `TestCalibrationPass` | `handle_calibration_pass()` | asset dates updated correct, ALE created, no CAPA created |
| `TestCalibrationFail` | `handle_calibration_fail()` | asset → OOS, CAPA created, lookback triggered |
| `TestLookback` | `perform_lookback_assessment()` | 2 active same model found, Decommissioned excluded, no other assets |
| `TestNextCalDate` | `handle_calibration_pass()` | BR-11-04: next_cal = cert_date + interval (not due_date + interval) |
| `TestScheduleCreate` | `create_calibration_schedule_from_commissioning()` | schedule created with correct interval, device_model.calibration_required=0 → skip |
| `TestDueWOs` | `create_due_calibration_wos()` | creates WO for due in 30d, skips if WO already exists (idempotent), skips if schedule inactive |
| `TestExpiryCheck` | `check_calibration_expiry()` | On Schedule, Due Soon (<30d), Overdue, email alerts sent |
| `TestPostRepairCal` | `create_post_repair_calibration()` | creates WO if schedule active, skips if device_model has no cal_required |
| `TestAssetGate` | `validate_asset_for_operations()` gate | active asset → pass, OOS asset → fail (unless is_recalibration=1) |

**Pattern seed (khi implement):**
```python
class TestCalibrationFail(FrappeTestCase):
    def setUp(self):
        self.asset = make_asset("ACC-ASSET-TEST-CAL-001", status="Active",
                                device_model="Sysmex XN-1000")
        self.cal_doc = make_calibration_wo(
            asset=self.asset.name, calibration_type="External"
        )
        # Add 1 failing measurement
        self.cal_doc.append("measurements", {
            "parameter": "HGB", "nominal": 14.0,
            "tolerance_plus": 0.42, "tolerance_minus": 0.42,
            "measured_value": 15.0  # out of tolerance
        })

    def test_fail_sets_asset_out_of_service(self):
        # ⚠️ Pending — implement after services/imm11.py created
        handle_calibration_fail(self.cal_doc)
        self.asset.reload()
        self.assertEqual(self.asset.lifecycle_status, "Out of Service")

    def test_fail_creates_capa(self):
        # ⚠️ Pending
        handle_calibration_fail(self.cal_doc)
        capa = frappe.get_last_doc("IMM CAPA Record",
                                   filters={"source_ref": self.cal_doc.name})
        self.assertIsNotNone(capa)
        self.assertEqual(capa.lookback_required, 1)
```

## I.3. Unit Test — Validators & Repository

**File (cần tạo):** `assetcore/tests/test_imm11_validators.py`

⚠️ Pending — viết sau khi `services/imm11.py` và DocType controllers tạo xong.

| Validator | Happy | Fail |
|---|---|---|
| `VR-11-01: lab iso_17025_certified` | Supplier certified → pass | Supplier not certified → raise |
| `VR-11-02: certificate_file (External)` | File đã upload → pass | File null → raise |
| `VR-11-03: lab_accreditation_number` | Filled → pass | Empty → raise |
| `VR-11-04: measurements ≥1 row` | 3 rows with values → pass | Empty table → raise |
| `VR-11-05: certificate_date not future` | Past date → pass | Future date → raise |
| `VR-11-06: reference_standard_serial (In-House)` | Filled → pass | Empty → raise |
| `VR-11-09: amendment_reason on Amend` | Filled → pass | Empty → raise |
| `VR-11-10: block Cancel after Submit` | docstatus=0 → allow cancel | docstatus=1 → raise |
| `VR-11-11: lookback_status before CAPA close` | Cleared → pass | Pending → raise |
| `VR-11-12: calibration_interval_days > 0` | 365 → pass | 0 → raise |
| `CalibrationRepo.list(filters)` | Trả list đúng phân trang | Filter invalid → empty |
| `CalibrationRepo.get(name)` | Trả doc đầy đủ + asset_info | Không tồn tại → raise NOT_FOUND |

## I.4. Integration Test — DocType Lifecycle

**File (cần tạo):** `assetcore/tests/test_imm_asset_calibration_doctype.py`

⚠️ Pending — viết sau khi DocType `IMM Asset Calibration` tạo xong.

| Test | Setup | Action | Assert |
|---|---|---|---|
| `test_before_submit_blocks_no_cert` | External CAL, no cert file | `doc.submit()` | `ValidationError` VR-11-02 |
| `test_on_submit_pass_updates_asset` | All measurements Pass | `doc.submit()` | `AC Asset.next_calibration_date` cập nhật đúng |
| `test_on_submit_fail_triggers_capa` | 1 measurement OOT | `doc.submit()` | CAPA created, asset → Out of Service |
| `test_on_submit_fail_performs_lookback` | 2 assets same model Active | `doc.submit()` Fail | CAPA.lookback_assets có 2 assets |
| `test_on_cancel_blocked_after_submit` | docstatus=1 | `doc.cancel()` | `ValidationError` VR-11-10 |
| `test_amend_requires_reason` | Submitted doc | `doc.amend()` no reason | `ValidationError` VR-11-09 |
| `test_audit_trail_created_on_submit` | Any submit | `doc.submit()` | `IMM Audit Trail` record exists |
| `test_inhouse_no_cert_required` | In-House CAL, all Pass, no cert file | `doc.submit()` | Submit OK (no cert required) |
| `test_schedule_auto_created_on_commissioning` | Commissioning submit | `commissioning.submit()` | `IMM Calibration Schedule` created |

## I.5. Integration Test — Workflow Transitions

**File (cần tạo):** `assetcore/tests/test_imm11_workflow.py`

⚠️ Pending — viết sau khi Workflow JSON `IMM-11 Calibration Workflow` tạo xong.

Workflow `IMM Asset Calibration` có 8 state (Scheduled → Passed/Failed/Conditionally Passed). Test mỗi transition:

| Transition | From → To | Role required | Test |
|---|---|---|---|
| Gửi đến Lab | Scheduled → Sent to Lab | IMM Workshop Lead / Technician | pass + fail(missing sent_date) |
| Nhận chứng chỉ | Sent to Lab → Certificate Received | IMM Technician | pass + fail(missing cert file) |
| Submit Pass | Certificate Received → Passed | IMM Technician | pass + assert asset dates updated |
| Submit Fail | Certificate Received → Failed | IMM Technician | pass + assert CAPA + OOS |
| In-House Start | Scheduled → In Progress | IMM Technician | pass |
| Submit In-House Pass | In Progress → Passed | IMM Technician | pass (no cert required) |
| Conditionally Passed | Failed → Conditionally Passed | System (CAPA closed + recal pass) | assert ALE event type |
| Cancel (draft only) | Scheduled → Cancelled | IMM Workshop Lead | pass + fail(already submitted) |

## I.6. Integration Test — Audit Chain Integrity

**File (cần tạo):** `assetcore/tests/test_imm11_audit.py`

⚠️ Pending.

```python
def test_audit_chain_intact_after_calibration_lifecycle():
    # Tạo CAL → Sent to Lab → Certificate Received → Submit Pass
    # Sau mỗi bước, assert verify_audit_chain(asset) == True

def test_audit_chain_breaks_on_tamper():
    # Submit CAL → Insert IMM Audit Trail record
    # Sửa thẳng DB field hash_sha256
    # Assert verify_audit_chain() == False

def test_immutable_after_submit():
    # Submit CAL record
    # Thử frappe.db.delete("IMM Asset Calibration", ...)
    # Assert PermissionError
```

## I.7. API Test

**File (cần tạo):** `assetcore/tests/test_imm11_api.py`

⚠️ Pending — viết sau khi `api/imm11.py` tạo xong.

| Test | Endpoint | Verify |
|---|---|---|
| `test_list_default_pagination` | `list_calibrations` | page=1, page_size=20, total ≥ 0 |
| `test_list_filter_status` | `list_calibrations?filters={"status":"Scheduled"}` | Mọi row status == Scheduled |
| `test_get_existing` | `get_calibration?name=CAL-...` | `success=true`, fields đầy đủ |
| `test_get_not_found` | `get_calibration?name=FAKE` | `success=false`, `code=NOT_FOUND` |
| `test_create_external` | `create_calibration` (External) | `success=true`, CAL name trả về |
| `test_create_no_lab_certification` | lab not iso_17025_certified | `success=false`, `code=VALIDATION` |
| `test_submit_pass_updates_asset` | `submit_calibration_results` all Pass | Asset.next_calibration_date updated |
| `test_submit_fail_creates_capa` | `submit_calibration_results` 1 OOT | CAPA created, asset OOS |
| `test_submit_no_cert_external` | No certificate_file | `success=false`, `code=VALIDATION` |
| `test_get_due_calibrations` | `get_due_calibrations?days=30` | returns list within 30 days |
| `test_get_compliance_report` | `get_calibration_compliance_report` | fields: compliance_rate, oot_rate, capa_closure_rate |
| `test_no_permission` | `create_calibration` with role=IMM Storekeeper | HTTP 403 |
| `test_idempotent_scheduler` | `create_due_calibration_wos` chạy 2 lần | No duplicate WOs created |

## I.8. E2E Browser (Playwright)

**File (cần tạo):** `assetcore/tests/e2e/test_imm11_golden.py`

⚠️ Pending — viết sau khi Frontend views hoàn chỉnh.

**Golden scenario — External Track Pass:** Tạo CAL Schedule từ Commissioning → Dashboard hiển thị due soon → KTV tạo CAL record → Gửi Lab → Nhận certificate → Nhập measurements (all Pass) → Submit → Verify Asset dates cập nhật + ALE created.

**Golden scenario — Fail + CAPA Flow:** Submit với 1 OOT measurement → Verify dialog cảnh báo → Confirm submit → Verify Asset OOS + CAPA created + lookback assets populated → QA Officer resolve lookback → Close CAPA → Recalibration Pass → Verify Asset back to Active + lifecycle event `calibration_conditionally_passed`.

Chạy: `pytest assetcore/tests/e2e/ -m imm11 --headed` (staging only).

## I.9. Performance Test

⚠️ Pending — thiết lập sau khi API layer hoàn chỉnh.

| Metric | Target | Phương pháp |
|---|---|---|
| `list_calibrations` p95 (200 CAL) | ≤ 800 ms | k6 ramping 20 VU |
| `submit_calibration_results` (10 measurements) p95 | ≤ 1.5 s | k6 |
| `get_calibration_compliance_report` p95 | ≤ 2 s | k6 |
| Scheduler `create_due_calibration_wos` (500 schedules) | ≤ 30 s | bench execute + timer |
| Scheduler `check_calibration_expiry` (500 assets) | ≤ 30 s | bench execute + timer |
| List view FE render (100 rows) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |

## I.10. Test Data

⚠️ Pending — seed scripts cần viết trước UAT execution.

| Loại | Cách seed | File (cần tạo) |
|---|---|---|
| AC Asset (test) | `tests/fixtures/test_assets_imm11.json` | 7 assets (xem SD-01 trong UAT Script) |
| IMM Calibration Schedule | Script | 7 schedules gắn với assets |
| AC Supplier (Calibration Lab) | `tests/fixtures/test_cal_labs.json` | 2 labs (VLAS-T-028, VLAS-T-001) |
| IMM Device Model (với calibration_interval_days) | `tests/fixtures/test_device_models.json` | 4 models |
| UAT full seed | `scripts/uat/uat_imm11.py` | 7 assets + users + labs + schedules |

Reset script (khi implement): `bench --site assetcore.local execute assetcore.scripts.uat.uat_imm11.seed_data`

## I.11. Run Commands & Coverage Gate

⚠️ Pending — commands bên dưới sẽ hoạt động sau khi test files được tạo.

```bash
# Unit + integration (khi implement)
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm11_service
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm_asset_calibration_doctype

# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage

# UAT golden scenario (khi FE hoàn chỉnh)
bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm11.run
```

| Layer | Coverage target | Đo |
|---|---|---|
| Service (`services/imm11.py`) | ≥ 85% | `coverage report` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm11.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | Không crash build | CI `npm run build` |

CI fail nếu coverage < target hoặc bất kỳ test nào fail.

## I.12. Đo Chất Lượng Mã Nguồn

⚠️ Pending — áp dụng khi code được implement.

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — CalibrationDashboard) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format chuẩn PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm11) | main chunk ≤ 250 KB gzip | ≤ budget | Mỗi PR FE (CI report) |

---

# Phần II — UAT Script

## II.1. Phạm vi UAT

**In-scope:**
- Tạo Calibration Schedule tự động từ IMM-04 Commissioning (FR-11-01)
- External Track: validate lab ISO 17025, certificate, accreditation number (BR-11-01)
- Submit Pass: cập nhật asset dates đúng (BR-11-04)
- Submit Fail: Asset → OOS + CAPA tự động + Lookback (BR-11-02, BR-11-03)
- In-House Track: không cần certificate (FR-11-11 → FR-11-13)
- Immutability: block Cancel/Delete sau Submit; Amend có reason (BR-11-05)
- CAPA lifecycle: Lookback → Root Cause → Close → Recalibration → Asset Active
- Compliance Dashboard + KPI Report
- Scheduler: create due WOs, expiry check, CAPA overdue

**Out-of-scope (UAT):** Load testing, API integration với lab bên ngoài, OCR PDF.

**Pre-conditions:**
- ⚠️ UAT chưa thể thực hiện — module code chưa được implement
- Khi ready: UAT site `uat.assetcore.vn` đã deploy bản mới nhất
- Seed data chạy thành công: `uat_imm11.py seed_data`
- 4 tester accounts tạo (xem §II.2)
- Browser: Chrome ≥ 120 hoặc Edge ≥ 120

## II.2. Tester Accounts

⚠️ Tạo khi UAT chuẩn bị thực hiện.

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `manager.cal` | manager.cal@hospital.vn | IMM Workshop Lead | Tạo lịch, chọn lab, phân công KTV |
| `ktv.cal` | ktv.cal@hospital.vn | IMM Technician | Gửi lab, nhập kết quả, upload cert |
| `qa.cal` | qa.cal@hospital.vn | IMM QA Officer | Review CAPA, Lookback, Close CAPA |
| `ptp.cal` | ptp.cal@hospital.vn | IMM Operations Manager | Dashboard, KPI report |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT).

## II.3. Test Data Đã Seed

⚠️ Seed khi implement. Tham chiếu `IMM-11_UAT_Script.md §Seed Data` (SD-01 → SD-05) cho danh sách đầy đủ.

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset | 7 | SD-01: mix status, models, overdue/due soon |
| AC Supplier (Calibration Lab) | 2 | SD-04: VLAS-T-028, VLAS-T-001 |
| IMM Device Model | 4 | SD-03: Sysmex XN-1000, Mindray MEC-1200, Drager V500, Fluke ESA620 |
| IMM Calibration Schedule | 7 | 1 per asset với interval từ Device Model |
| Sample Certificate PDF | 1 | SD-05: UAT_CAL_Certificate_Sysmex_XN_2026.pdf |

## II.4. Test Scenarios

Tham chiếu chi tiết: `IMM-11_UAT_Script.md TC-11-01 → TC-11-16`.

### UAT-IMM11-01 — Dashboard hiển thị đúng (TC-11-01)

**Liên kết:** US-11-01, FR-11-23  
**Role tester:** IMM Workshop Lead  
**Mục tiêu:** Dashboard hiển thị thiết bị overdue và due soon; nút tạo CAL nhanh.  
**⚠️ Pending execution** — UI chưa implement.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Đăng nhập `manager.cal`, vào `/imm-11` | Dashboard hiển thị 4 KPI card | ☐ |
| 2 | Kiểm tra widget Overdue | `ACC-ASS-UAT-002` (overdue 7 ngày) xuất hiện với badge đỏ | ☐ |
| 3 | Kiểm tra widget Due Soon | `ACC-ASS-UAT-001` (còn 14 ngày) xuất hiện | ☐ |
| 4 | Click [Tạo CAL] | Redirect `/imm-11/create` với asset pre-filled | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM11-02 — Tạo CAL External + Gửi Lab (TC-11-02, TC-11-03)

**Liên kết:** US-11-03, BR-11-01, FR-11-05 → FR-11-07  
**Role tester:** IMM Technician  
**Mục tiêu:** Tạo CAL record External với lab hợp lệ, gửi lab, lifecycle event tạo.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Tạo CAL record, chọn External, lab = VLAS-T-028 | Record tạo OK, status = Scheduled | ☐ |
| 2 | Thử chọn lab không có ISO 17025 | Lỗi VR-11-01: block | ☐ |
| 3 | Điền sent_date, click "Gửi đến Lab" | Status → Sent to Lab, ALE `calibration_sent_to_lab` tạo | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

### UAT-IMM11-03 — Submit Pass: dates cập nhật đúng (TC-11-04, TC-11-12)

**Liên kết:** US-11-02, BR-11-04, FR-11-09, FR-11-14  
**Role tester:** IMM Technician  
**Mục tiêu:** Submit kết quả Pass — Asset dates cập nhật đúng từ `certificate_date` (không từ `due_date`).  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Upload cert, điền cert_date = 2026-04-24 | — | ☐ |
| 2 | Nhập measurements: WBC, PLT, HGB (tất cả Pass) | Badge ✅ PASSED | ☐ |
| 3 | Submit | Submit OK, status = Passed | ☐ |
| 4 | Kiểm tra Asset | next_cal_date = 2027-04-24 (cert_date + 365, không phải due_date + 365) | ☐ |
| 5 | Kiểm tra ALE | event `calibration_completed` tạo | ☐ |
| 6 | Thử Cancel record | Block: VR-11-10 | ☐ |

**Acceptance:** Tất cả 6 step Pass.

---

### UAT-IMM11-04 — Submit Fail: OOS + CAPA + Lookback (TC-11-05, TC-11-06)

**Liên kết:** US-11-04, US-11-06, BR-11-02, BR-11-03  
**Role tester:** IMM Technician → IMM QA Officer  
**Mục tiêu:** Fail trigger → Asset OOS + CAPA auto + Lookback assets populated.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Thêm measurement HGB: measured=15.0 (OOT) | Badge ❌ FAILED hiển thị | ☐ |
| 2 | Submit | Dialog cảnh báo OOS + CAPA + Lookback | ☐ |
| 3 | Xác nhận Submit | status = Failed | ☐ |
| 4 | Kiểm tra Asset | lifecycle_status = Out of Service | ☐ |
| 5 | Kiểm tra CAPA | CAPA-2026-xxxxx tạo, lookback_assets = [UAT-005, UAT-006] | ☐ |
| 6 | QA Officer: lookback_status = Cleared, điền findings | lookback_status updated | ☐ |
| 7 | Thử Close CAPA khi chưa có root_cause | Block: BR-00-08 | ☐ |

**Acceptance:** Tất cả 7 step Pass.

---

### UAT-IMM11-05 — Close CAPA + Recalibration → Asset Active (TC-11-07)

**Liên kết:** US-11-04, FR-11-21  
**Role tester:** IMM QA Officer → IMM Technician  
**Mục tiêu:** Sau CAPA closed + recalibration Pass → Asset về Active + ALE `calibration_conditionally_passed`.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Điền root_cause, corrective, preventive vào CAPA | Accepted | ☐ |
| 2 | Close CAPA | status = Closed | ☐ |
| 3 | Tạo CAL mới (recalibration), Submit Pass | Submit OK | ☐ |
| 4 | Kiểm tra Asset | lifecycle_status = Active | ☐ |
| 5 | Kiểm tra ALE | event `calibration_conditionally_passed` | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM11-06 — In-House Calibration (TC-11-10)

**Liên kết:** US-11-02, FR-11-11 → FR-11-13  
**Role tester:** IMM Technician  
**Mục tiêu:** In-House track không yêu cầu certificate; reference_standard bắt buộc.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Tạo CAL In-House, điền reference_standard_serial, traceability_reference | Accepted | ☐ |
| 2 | Thêm measurements (all Pass) | Pass indicators xanh | ☐ |
| 3 | Submit không upload cert | Submit OK — không yêu cầu cert | ☐ |
| 4 | Thử submit mà không điền reference_standard_serial | Block: VR-11-06 | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM11-07 — Amend Record (TC-11-11)

**Liên kết:** BR-11-05  
**Role tester:** IMM Workshop Lead  
**Mục tiêu:** Submitted record chỉ có thể Amend với lý do; old record tồn tại.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở submitted CAL record | Read-only mode | ☐ |
| 2 | Thử Delete | Blocked | ☐ |
| 3 | Thử Cancel | Block: VR-11-10 | ☐ |
| 4 | Amend không điền amendment_reason | Block: VR-11-09 | ☐ |
| 5 | Amend với reason đầy đủ | Amend OK; old record vẫn tồn tại với amended_from link | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM11-08 — Scheduler tạo WOs + Alert Overdue (TC-11-16)

**Liên kết:** FR-11-22, FR-11-23, FR-11-24  
**Role tester:** System (manual trigger) + IMM Workshop Lead  
**Mục tiêu:** Scheduler tạo WO đúng, email alert overdue gửi đúng người.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Chạy `bench execute assetcore.services.imm11.create_due_calibration_wos` | CAL WO tạo cho asset due ≤ 30 ngày | ☐ |
| 2 | Chạy lại (idempotent check) | Không tạo WO duplicate | ☐ |
| 3 | Set CAPA due_date = hôm qua - 1 ngày, chạy `check_capa_overdue` | Email gửi QA Officer: "CAPA quá hạn" | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

### UAT-IMM11-09 — Compliance Report (TC-11-13)

**Liên kết:** US-11-05, FR-11-25  
**Role tester:** IMM Operations Manager  
**Mục tiêu:** Compliance Rate, OOT Rate, CAPA Closure Rate tính đúng.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | PTP mở `/imm-11/report/compliance`, filter tháng 4/2026 | Báo cáo load | ☐ |
| 2 | Kiểm tra Compliance Rate | % tính đúng (on_time / total × 100) | ☐ |
| 3 | Kiểm tra OOT Rate | % = failed_measurements / total_measurements | ☐ |
| 4 | Kiểm tra chart 6 tháng | Line chart đúng data | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM11-10 — Audit Chain Verify

**Liên kết:** Security §III.3  
**Role tester:** IMM QA Officer  
**Mục tiêu:** Audit chain nguyên vẹn sau full lifecycle.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở CAL record đã Passed | — | ☐ |
| 2 | Gọi `verify_audit_chain(asset)` | True | ☐ |
| 3 | Thử sửa IMM Audit Trail | Block | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

## II.5. Tổng Hợp Kết Quả & Bug Found

### Bảng kết quả

⚠️ Điền khi UAT thực hiện (sau khi module implement xong).

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM11-01 | ⚠️ Pending | | | |
| UAT-IMM11-02 | ⚠️ Pending | | | |
| UAT-IMM11-03 | ⚠️ Pending | | | |
| UAT-IMM11-04 | ⚠️ Pending | | | |
| UAT-IMM11-05 | ⚠️ Pending | | | |
| UAT-IMM11-06 | ⚠️ Pending | | | |
| UAT-IMM11-07 | ⚠️ Pending | | | |
| UAT-IMM11-08 | ⚠️ Pending | | | |
| UAT-IMM11-09 | ⚠️ Pending | | | |
| UAT-IMM11-10 | ⚠️ Pending | | | |

### Sign-off UAT

⚠️ Điền khi UAT hoàn tất.

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (IMM-11) | | | |
| Đại diện end-user (Workshop Manager) | | | |

**Quy ước go-live:** Blocker = 0, Major ≤ 2 (có workaround đã documented).

### Bug Log

| Issue ID | Severity | Mô tả | Fix status |
|---|---|---|---|
| (điền khi phát sinh) | | | |

---

# Phần III — Security Review

## III.1. RBAC

### Role definitions

Xem `assetcore/fixtures/role.json` + `role_profile.json`. Các role liên quan IMM-11:

| Role | Quyền trên IMM Asset Calibration |
|---|---|
| IMM Workshop Lead | Create, Read, Write, Submit, Cancel(draft), Amend |
| IMM Technician | Read (assigned only), Write (assigned only), Submit (assigned) |
| IMM Operations Manager | Read all; dashboard only |
| IMM QA Officer | Read all; Write/Close `IMM CAPA Record` |
| IMM Department Head | Read all; nhận escalation overdue |
| IMM Storekeeper | Read only |
| IMM Document Officer | Read only |
| IMM System Admin | Full |

### DocPerm Matrix — `IMM Asset Calibration`

⚠️ Pending implementation — fixtures chưa tạo. Matrix đề xuất:

| Role | Read | Write | Create | Submit | Cancel | Amend | Delete |
|---|---|---|---|---|---|---|---|
| IMM Workshop Lead | ✅ | ✅ | ✅ | ✅ | ✅ (draft) | ✅ | ❌ |
| IMM Technician | ✅ (own) | ✅ (own) | ❌ | ✅ (own) | ❌ | ❌ | ❌ |
| IMM Operations Manager | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM QA Officer | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### DocPerm Matrix — `IMM Calibration Schedule`

| Role | Read | Write | Create |
|---|---|---|---|
| IMM Workshop Lead | ✅ | ✅ | ✅ |
| IMM Technician | ✅ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ |

### Field-level permission (permlevel)

⚠️ Pending — xác định sau khi DocType fields được thiết kế hoàn chỉnh.

| Field | permlevel | Mô tả |
|---|---|---|
| `lab_accreditation_number` | 0 — all authenticated | Phục vụ kiểm tra audit |
| `certificate_file` | 0 — all authenticated | Cần xem được cho audit |
| `amendment_reason` | 1 — IMM Workshop Lead+ | Lý do amend nhạy cảm |

### User Permission (Row-level)

⚠️ Pending — `permission_query_conditions` cho IMM Technician:
```python
def cal_permission_query(user):
    if frappe.has_role("IMM Workshop Lead", user) or frappe.has_role("IMM System Admin", user):
        return ""
    return f"(`tabIMM Asset Calibration`.technician = '{user}')"
```

## III.2. API Security

⚠️ Pending implementation.

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ⚠️ Pending | Mọi `@frappe.whitelist()` phải có docstring + required role check |
| CSRF | ✅ (Frappe default) | X-Frappe-CSRF-Token |
| Input validation | ⚠️ Pending | `name` field validate qua `frappe.get_value` trước khi dùng |
| SQL injection | ⚠️ Pending | Frappe ORM parameterized; không raw SQL |
| Rate limit | ⚠️ Roadmap | Cấu hình Frappe rate limit cho `submit_calibration_results` |

## III.3. Audit Trail Integrity

- Mọi state change (Scheduled/Sent to Lab/Passed/Failed/Conditionally Passed) sinh `IMM Audit Trail` qua `lifecycle.log_audit_event()`.
- Hash chain SHA-256: `hash = SHA256(prev_hash + canonical_json(event))`.
- API verify: `assetcore.utils.lifecycle.verify_audit_chain(asset)` → `bool`.
- ⚠️ Test tamper: `test_audit_chain_breaks_on_tamper()` — Pending implementation.
- User KHÔNG có quyền Delete/Amend `IMM Audit Trail`.
- Retention: ≥ 7 năm (NĐ98/2021 + ISO 13485:4.2.5).

## III.4. Authentication & Session

| Hạng mục | Config |
|---|---|
| Login | Frappe default — username + password |
| Session timeout | 8 giờ (config `frappe.conf.session_expiry`) |
| Lockout policy | Frappe default: 3 lần fail → lock 15 phút |
| Password policy | Minimum 8 ký tự, 1 chữ hoa, 1 số |
| API key | Tạo per-user, rotate mỗi 90 ngày; không commit vào git |
| 2FA | Roadmap Phase 2 |

## III.5. Data Sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Calibration certificate | `certificate_file` | Internal | Role permission |
| Lab accreditation info | `lab_accreditation_number`, `lab_supplier` | Internal | Role permission |
| Measurement data | `measurements` child table | Internal | Role permission |
| Amendment reason | `amendment_reason` | Confidential | permlevel 1 |
| Dữ liệu bệnh nhân | Không lưu | N/A | AssetCore KHÔNG lưu patient data |

## III.6. Vendor Isolation

Lab hiệu chuẩn bên ngoài (`AC Supplier` với `vendor_type = "Calibration Lab"`) không có quyền user trên `IMM Asset Calibration` mặc định. Nếu mở rộng trong tương lai:
- Chỉ thấy CAL WO của lab mình (`lab_supplier = session.user`).
- Không thấy: measurement chi tiết của asset khác, CAPA content.
- Không export bulk.

## III.7. Secrets Management

- `site_config.json` không commit vào git.
- Backup encrypt at-rest; off-site S3.
- Secret scan CI: `git-secrets` / `detect-secrets` trong pre-commit hook.

## III.8. Logging & Monitoring

⚠️ Pending — cấu hình sau khi service layer implement.

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Calibration Fail (asset OOS) | WARNING | `IMM Audit Trail` + email | ✅ Email QA Officer + Ops Manager |
| CAL overdue > 0 ngày | WARNING | Scheduler log | ✅ Email Workshop Lead |
| CAPA overdue > 30 ngày | WARNING | `frappe.log_error` + email | ✅ Email QA Officer |
| Audit chain tamper | ERROR | `frappe.log_error` | ✅ Email System Admin |
| Submit fail (validation) | INFO | Frappe access log | ❌ |

## III.9. Threat Model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Spoofing | Giả mạo KTV upload cert giả | Low | High | Cert file + accreditation number verify; audit trail |
| Tampering — Certificate | Sửa `certificate_file` sau submit | Low | Critical | Submittable immutable; block cancel/delete |
| Tampering — Audit | Sửa `IMM Audit Trail` DB | Low | Critical | DocPerm no-delete; verify chain endpoint |
| Repudiation | KTV phủ nhận đã submit Fail | Low | High | `IMM Audit Trail` + audit chain hash + actor |
| Info Disclosure | KTV xem CAL của người khác | Low | Medium | `permission_query_conditions` |
| DoS — Lookback | Lookback với 10000+ assets cùng model | Low | Medium | Paginate lookback; index `device_model + lifecycle_status` |
| Elevation of Privilege | Storekeeper tự submit CAL | Low | High | Workflow role check + DocPerm no-Submit for Storekeeper |

## III.10. Penetration Test

⚠️ Pending — thực hiện trước release đầu tiên.
- Burp Suite / OWASP ZAP scan trên `uat.assetcore.vn` — 0 High/Critical open.
- CSRF token verify bằng curl không có token.
- Role escalation: thử gọi `submit_calibration_results` với role Storekeeper → 403.
- Report lưu: `docs/security/pentest_imm11_v1.md`.

## III.11. Sign-off Security

⚠️ Điền khi security review hoàn tất.

| Vai trò | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Tech Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

---

## DoD — Hoàn chỉnh

### I. Test Plan
- [x] Test class structure cho 12 service functions (defined)
- [x] ≥ 1 happy + 1 negative test mỗi function (specified)
- [x] 8 workflow transitions đều có test (specified)
- [x] Audit chain test (intact + tampered) (specified)
- [x] API test ≥ 60% coverage target (specified)
- [x] Performance target xác định (k6)
- [x] CI command xác định
- [x] SonarQube + Lighthouse target xác định
- [ ] Test files thực sự được tạo (`test_imm11_service.py`, etc.) ⚠️ Pending implementation

### II. UAT
- [x] 10 UAT scenario, cover 7 BR + permission + audit + dashboard
- [x] Mọi User Story (US-11-01 → 09) có ≥ 1 UAT scenario
- [ ] Test data seed script: `uat_imm11.py` ⚠️ Pending
- [x] 4 Tester accounts + password documented
- [x] Sign-off section sẵn sàng
- [ ] UAT execution thực sự ⚠️ Pending implementation

### III. Security
- [x] DocPerm matrix đề xuất đầy đủ 8 role
- [x] Field-level permlevel xác định
- [x] Threat model 7 threat với mitigation
- [ ] Permission query code implement ⚠️ Pending
- [ ] Pentest report lưu `docs/security/` (trước go-live)
- [ ] Rate limit cấu hình (roadmap)
- [x] Vendor isolation policy documented
- [x] Sign-off section sẵn sàng
