# IMM-09 — Kiểm thử & An ninh (Testing, QA & Security)

| Mục | Giá trị |
|---|---|
| Module | **IMM-09 — Sửa chữa (Corrective Maintenance)** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-14 |
| Owner | QA Lead + Tech Lead |
| Liên kết | [Module Overview](./IMM-09_Module_Overview.md) · [Functional Specs](./IMM-09_Functional_Specs.md) · [API Interface](./IMM-09_API_Interface.md) |

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

Mọi service function phải có test trước khi code (TDD — CLAUDE.md §17). Mỗi business rule (BR-09-01 → 07) có ≥ 1 happy + 1 negative test.

## I.2. Unit Test — Service Layer

**File:** `assetcore/tests/test_imm09_service.py`

| Test class | Hàm cover | Cases dự kiến |
|---|---|---|
| `TestRepairSource` | `validate_repair_source()` | happy(IR), happy(PM WO), fail(no source), fail(both blank) |
| `TestDuplicateWO` | `validate_asset_not_under_repair()` | happy, fail(already Under Repair) |
| `TestRepeatFailure` | `check_repeat_failure()` | happy(no recent), flag(1 WO <30d), flag(2+ WO) |
| `TestSlaTarget` | `get_sla_target()` | 9 combos risk×priority; fallback 480h |
| `TestSpareParts` | `validate_spare_parts_stock_entries()` | happy, fail(missing stock_entry_ref), fail(nonexistent SE ref) |
| `TestFirmwareCR` | `validate_firmware_change_request()` | happy(no firmware update), happy(FCR Approved), fail(FCR Draft), fail(no FCR) |
| `TestChecklist` | `validate_repair_checklist_complete()` | happy(all Pass), fail(1 Fail), fail(N/A row), fail(empty) |
| `TestComplete` | `complete_repair()` | mttr_hours calc correct, sla_breached flag set, ALE created, Asset→Active |
| `TestCannotRepair` | `_mark_cannot_repair()` | Asset→Out of Service, ALE created |
| `TestScheduler` | `check_repair_sla_breach()` | breach flag set for overdue; skip for completed |

**Pattern seed:**
```python
class TestRepairSource(FrappeTestCase):
    def setUp(self):
        self.asset = make_asset("AC-ASSET-TEST-001", status="Active", risk_class="Class III")
        self.ir = make_incident_report(asset=self.asset.name)

    def test_validate_ok_with_ir(self):
        doc = make_repair_wo(asset=self.asset.name, incident_report=self.ir.name)
        validate_repair_source(doc)  # không raise

    def test_validate_fail_no_source(self):
        doc = make_repair_wo(asset=self.asset.name)
        with self.assertRaises(ServiceError) as ctx:
            validate_repair_source(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
```

## I.3. Unit Test — Validators & Repository

**File:** `assetcore/tests/test_imm09_validators.py`

| Validator | Happy | Fail |
|---|---|---|
| `_check_sla_not_set(doc)` | SLA auto-set khi insert | Không set lại nếu đã có |
| `_check_asset_active(asset_ref)` | Asset Active → pass | Asset Decommissioned → raise |
| `RepairRepo.list(filters)` | Trả list đúng phân trang | Filter invalid → empty |
| `RepairRepo.get(name)` | Trả doc đầy đủ + asset_info | Không tồn tại → raise NOT_FOUND |

## I.4. Integration Test — DocType Lifecycle

**File:** `assetcore/tests/test_asset_repair_doctype.py`

| Test | Setup | Action | Assert |
|---|---|---|---|
| `test_before_insert_validates_source` | Asset Active, no IR, no PM WO | `doc.insert()` | `frappe.exceptions.ValidationError` |
| `test_on_insert_sets_asset_under_repair` | Asset Active, IR exists | `doc.insert()` | `Asset.status == "Under Repair"` |
| `test_on_insert_creates_lifecycle_event` | Asset Active | `doc.insert()` | ALE `event_type == "repair_opened"` exists |
| `test_before_submit_validates_checklist` | WO In Repair, 1 Fail row | `doc.submit()` | `ValidationError` |
| `test_on_submit_complete_repair` | WO pending inspection, all Pass | `doc.submit()` | `Asset.status == "Active"`, `mttr_hours > 0` |
| `test_on_submit_cannot_repair` | WO with `cannot_repair_reason` set | `close_work_order(cannot_repair=True)` | `Asset.status == "Out of Service"` |
| `test_audit_trail_immutable` | ALE inserted | `frappe.db.delete("IMM Audit Trail", ...)` | `PermissionError` hoặc DB trigger block |

## I.5. Integration Test — Workflow Transitions

**File:** `assetcore/tests/test_imm09_workflow.py`

Workflow `IMM-09 Repair Workflow` có 9 state, 15 transition. Test mỗi transition:

| Transition | From → To | Role required | Test |
|---|---|---|---|
| Phân công KTV | Open → Assigned | IMM Workshop Lead | pass + fail(wrong role) |
| Bắt đầu chẩn đoán | Assigned → Diagnosing | IMM Biomed Technician | pass |
| Cần vật tư | Diagnosing → Pending Parts | IMM Biomed Technician | pass |
| Vật tư đủ → Bắt đầu | Pending Parts → In Repair | IMM Storekeeper + KTV | pass |
| Bắt đầu không qua Pending Parts | Diagnosing → In Repair | IMM Biomed Technician | pass |
| Đề nghị nghiệm thu | In Repair → Pending Inspection | IMM Biomed Technician | pass |
| Hoàn tất (Completed) | Pending Inspection → Completed | IMM Biomed Technician + Dept Head | pass + fail(checklist incomplete) |
| Không sửa được | Any → Cannot Repair | IMM Workshop Lead | pass + require reason |
| Hủy | Open/Assigned → Cancelled | IMM Workshop Lead | pass + require reason |

## I.6. Integration Test — Audit Chain Integrity

**File:** `assetcore/tests/test_imm09_audit.py`

```python
def test_audit_chain_intact_after_repair_lifecycle():
    # Tạo WO → Assign → Diagnose → Parts → In Repair → Complete
    # Sau mỗi bước, assert verify_audit_chain(asset) == True

def test_audit_chain_breaks_on_tamper():
    # Insert 1 IMM Audit Trail record
    # Sửa thẳng DB field hash_sha256
    # Assert verify_audit_chain() == False
```

## I.7. API Test

**File:** `assetcore/tests/test_imm09_api.py`

| Test | Endpoint | Verify |
|---|---|---|
| `test_list_default_pagination` | `list_repair_work_orders` | page=1, page_size=20, total ≥ 0 |
| `test_list_filter_status_open` | `list_repair_work_orders?filters={"status":"Open"}` | Mọi row status == Open |
| `test_get_existing` | `get_repair_work_order?name=WO-CM-...` | `success=true`, fields đầy đủ |
| `test_get_not_found` | `get_repair_work_order?name=FAKE` | `success=false`, `code=NOT_FOUND` |
| `test_create_happy` | `create_repair_work_order` | `success=true`, WO name trả về |
| `test_create_no_source` | (no IR, no PM WO) | `success=false`, `code=VALIDATION` |
| `test_create_no_permission` | role=IMM Storekeeper | HTTP 403 |
| `test_assign_technician` | `assign_technician` | status==Assigned, assigned_to set |
| `test_close_wo_incomplete_checklist` | `close_work_order` với Fail row | `code=VALIDATION` |
| `test_get_kpis` | `get_repair_kpis` | MTTR, SLA compliance rate fields |
| `test_idempotent_on_submit` | submit 2 lần | 2nd call → `code=BAD_STATE` |

## I.8. E2E Browser (Playwright)

**File:** `assetcore/tests/e2e/test_imm09_golden.py`

**Golden scenario:** IR → Tạo CM WO → Assign → Diagnose → Parts → In Repair → Checklist → Complete → Verify MTTR hiển thị.

Chạy: `pytest assetcore/tests/e2e/ -m imm09 --headed` (staging only).

## I.9. Performance Test

| Metric | Target | Phương pháp |
|---|---|---|
| `list_repair_work_orders` p95 (200 WO) | ≤ 800 ms | k6 ramping 20 VU |
| `create_repair_work_order` p95 | ≤ 1.5 s | k6 |
| `close_work_order` (full flow) p95 | ≤ 2 s | k6 |
| Scheduler `check_repair_sla_breach` (500 WO) | ≤ 30 s | bench execute + timer |
| List view FE render (100 rows) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |

## I.10. Test Data

| Loại | Cách seed | File |
|---|---|---|
| AC Asset (test) | `tests/fixtures/test_assets.json` | 10 assets, 3 risk class |
| Incident Report | `tests/fixtures/test_incident_reports.json` | 5 IR gắn assets trên |
| PM Work Order | `tests/fixtures/test_pm_wos.json` | 3 WO Halted |
| Stock Entry | `tests/fixtures/test_stock_entries.json` | 5 SE với spare parts |
| UAT full seed | `scripts/uat/uat_imm09.py` | 5 assets + users đầy đủ |

Reset script: `bench --site assetcore.local execute assetcore.scripts.uat.uat_imm09.seed_data`

## I.11. Run Commands & Coverage Gate

```bash
# Unit + integration
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm09_service
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_asset_repair_doctype

# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage

# UAT golden scenario
bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm09.run
```

| Layer | Coverage target | Đo |
|---|---|---|
| Service (`services/imm09.py`) | ≥ 85% | `coverage report` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm09.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | Không crash build | CI `npm run build` |

CI fail nếu coverage < target hoặc bất kỳ test nào fail.

## I.12. Đo Chất Lượng Mã Nguồn

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — CMDashboard) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format chuẩn PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm09) | main chunk ≤ 250 KB gzip | ≤ budget | Mỗi PR FE (CI report) |

---

# Phần II — UAT Script

## II.1. Phạm vi UAT

**In-scope:**
- Tạo CM WO từ IR và từ PM WO (BR-09-01)
- Phân công KTV, chẩn đoán, yêu cầu vật tư (BR-09-02)
- Sửa chữa, điền checklist nghiệm thu (BR-09-04)
- Firmware change control (BR-09-03)
- Đóng WO: Completed + Cannot Repair (BR-09-05)
- SLA breach detection (BR-09-07)
- Repeat failure flag + CAPA recommendation (BR-09-06)
- MTTR Report + Dashboard KPI
- Phân quyền mỗi role

**Out-of-scope (UAT):** Load testing, penetration testing, external system integration (xử lý ở §I và §III).

**Pre-conditions:**
- UAT site: `uat.assetcore.vn` đã deploy bản mới nhất
- Seed data chạy thành công: `uat_imm09.py seed_data`
- 6 tester accounts tạo (xem §II.2)
- Browser: Chrome ≥ 120 hoặc Edge ≥ 120

## II.2. Tester Accounts

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `manager.ws` | manager.ws@hospital.vn | IMM Workshop Lead | Tạo/phân công/hủy WO, duyệt FCR |
| `ktv.anha` | ktv.anha@hospital.vn | IMM Biomed Technician | Chẩn đoán, sửa chữa, checklist |
| `ktv.binh` | ktv.binh@hospital.vn | IMM Biomed Technician | Test concurrent + permission |
| `kho.vt` | kho.vt@hospital.vn | IMM Storekeeper | Xuất vật tư, gắn Stock Entry |
| `truong.icu` | truong.icu@hospital.vn | IMM Department Head | Xác nhận nghiệm thu |
| `ptp.k2` | ptp.k2@hospital.vn | IMM Operations Manager | Xem MTTR Report, Dashboard |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT).

## II.3. Test Data Đã Seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset | 5 | Mỗi loại risk class + trạng thái khác nhau |
| Incident Report | 3 | Gắn với 3 asset cụ thể |
| PM Work Order | 2 | 1 Halted–Major Failure, 1 Completed |
| AC Spare Part / Item | 4 | Đã có stock ở `Workshop-Store` |
| Stock Entry | 3 | Sẵn sàng dùng cho gắn `stock_entry_ref` |
| IMM Biomed Technician accounts | 2 | `ktv.anha`, `ktv.binh` |

## II.4. Test Scenarios

### UAT-IMM09-01 — Tạo CM WO từ Incident Report (Happy Path)

**Liên kết:** US-09-01, BR-09-01  
**Role tester:** IMM Workshop Lead  
**Mục tiêu:** Tạo WO với nguồn là IR, kiểm tra WO tạo đúng + Asset chuyển Under Repair.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Đăng nhập `manager.ws`, vào `/imm-09/create` | Form tạo WO hiển thị | ☐ |
| 2 | Chọn Asset: Máy thở Drager (Class III) | Auto-fill risk_class, serial, asset info card hiển thị | ☐ |
| 3 | Gắn Incident Report `IR-2026-00123` | Badge IR hiển thị, source validated | ☐ |
| 4 | Chọn Priority: Urgent | `sla_target_hours` tự tính = 24h (Class III + Urgent) | ☐ |
| 5 | Bấm "Tạo" | Toast "Phiếu sửa chữa đã được tạo", redirect WO detail | ☐ |
| 6 | Kiểm tra Asset Máy thở | `status = Under Repair` | ☐ |
| 7 | Kiểm tra Asset Lifecycle Event | Có event `repair_opened` | ☐ |

**Acceptance:** Tất cả 7 step Pass.

---

### UAT-IMM09-02 — Validation nguồn bắt buộc (BR-09-01 Negative)

**Liên kết:** US-09-01, BR-09-01  
**Role tester:** IMM Workshop Lead  
**Mục tiêu:** Hệ thống block tạo WO khi thiếu cả IR lẫn PM WO.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Tạo WO không điền IR và PM WO | — | ☐ |
| 2 | Bấm "Tạo" | Lỗi "Phải có nguồn sửa chữa", WO không được tạo | ☐ |
| 3 | Form giữ nguyên dữ liệu đã nhập | Không mất dữ liệu | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

### UAT-IMM09-03 — Phân công KTV và chẩn đoán

**Liên kết:** US-09-02, US-09-03  
**Role tester:** IMM Workshop Lead → IMM Biomed Technician  
**Mục tiêu:** Phân công → KTV thấy WO → Chẩn đoán → Yêu cầu vật tư.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Manager mở WO từ UAT-01, bấm "Phân công KTV" | Dropdown KTV hiển thị | ☐ |
| 2 | Chọn `ktv.anha`, lưu | WO status = Assigned, notification gửi đến KTV | ☐ |
| 3 | KTV đăng nhập `ktv.anha`, mở WO | WO hiển thị, action "Bắt đầu chẩn đoán" khả dụng | ☐ |
| 4 | KTV bắt đầu chẩn đoán, điền Root Cause: Electrical | Status = Diagnosing | ☐ |
| 5 | KTV chọn "Cần vật tư = Có", lưu | Status = Pending Parts, notification gửi Kho | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM09-04 — Xuất vật tư và thực hiện sửa chữa (BR-09-02)

**Liên kết:** US-09-04, BR-09-02  
**Role tester:** IMM Storekeeper → IMM Biomed Technician  
**Mục tiêu:** Kho gắn Stock Entry vào Spare Parts → KTV bắt đầu sửa.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Kho mở WO (Pending Parts), thêm row Spare Parts | Thêm `CAP-100UF-25V × 2` | ☐ |
| 2 | Gắn `stock_entry_ref = STE-2026-00456` | Validated: SE tồn tại | ☐ |
| 3 | KTV bấm "Bắt đầu sửa chữa" | Status = In Repair | ☐ |
| 4 | Thử submit khi thiếu stock_entry_ref | Lỗi "Vật tư thiếu chứng từ Stock Entry", `code=VALIDATION` | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM09-05 — Checklist nghiệm thu và hoàn tất WO (BR-09-04, BR-09-05)

**Liên kết:** US-09-06, BR-09-04, BR-09-05  
**Role tester:** IMM Biomed Technician → IMM Department Head  
**Mục tiêu:** Điền checklist → Submit → Asset về Active → MTTR tính đúng.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | KTV mở tab Checklist, điền tất cả result = Pass | — | ☐ |
| 2 | Thử submit khi có 1 row result = Fail | Lỗi "Checklist chưa hoàn tất", block submit | ☐ |
| 3 | Sửa lại tất cả Pass, bấm Submit | WO status = Pending Inspection | ☐ |
| 4 | Trưởng khoa đăng nhập, xác nhận nghiệm thu | `dept_head_name` được ghi, WO = Completed | ☐ |
| 5 | Kiểm tra Asset | `status = Active` | ☐ |
| 6 | Kiểm tra WO field `mttr_hours` | Giá trị > 0, tính đúng calendar time | ☐ |
| 7 | Kiểm tra ALE | event `repair_completed` tạo | ☐ |

**Acceptance:** Tất cả 7 step Pass.

---

### UAT-IMM09-06 — Cannot Repair + Asset Out of Service

**Liên kết:** US-09-08, BR-09-05  
**Role tester:** IMM Workshop Lead  
**Mục tiêu:** WO đóng với lý do không sửa được → Asset Out of Service.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở WO đang Diagnosing, bấm "Không sửa được" | Popup yêu cầu nhập lý do | ☐ |
| 2 | Nhập lý do: "Mạch chủ hỏng nặng, không có linh kiện thay thế" | — | ☐ |
| 3 | Xác nhận | WO = Cannot Repair, Asset = Out of Service | ☐ |
| 4 | Kiểm tra ALE | event `cannot_repair` tạo | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM09-07 — Firmware Change Control (BR-09-03)

**Liên kết:** BR-09-03  
**Role tester:** IMM Workshop Lead + IMM Biomed Technician  
**Mục tiêu:** WO có firmware update phải gắn FCR Approved, không thể submit nếu thiếu.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | WO In Repair, tick "Đã cập nhật firmware = Có" | Field `firmware_change_request` bắt buộc hiển thị | ☐ |
| 2 | Thử submit khi `firmware_change_request` trống | Lỗi "Cần Firmware Change Request đã phê duyệt" | ☐ |
| 3 | Gắn FCR đang ở status Draft | Lỗi "FCR chưa được phê duyệt" | ☐ |
| 4 | Gắn FCR Approved, submit | Submit thành công | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM09-08 — Repeat Failure + CAPA Recommendation (BR-09-06)

**Liên kết:** US-09-07, BR-09-06  
**Role tester:** IMM Workshop Lead  
**Mục tiêu:** Tạo WO thứ 3 trong 30 ngày cho cùng asset → `is_repeat_failure = 1`.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Seed: 2 WO Completed trong 30 ngày cho `ACC-ASS-2026-00033` | — | ☐ |
| 2 | Tạo WO thứ 3 cho cùng asset | Banner "Repeat Failure" hiển thị trên WO form | ☐ |
| 3 | Kiểm tra `is_repeat_failure = 1` | Field đúng | ☐ |
| 4 | Banner có link "Mở CAPA" | Chuyển sang IMM-12 để tạo CAPA | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM09-09 — SLA Breach Detection (BR-09-07)

**Liên kết:** BR-09-07  
**Role tester:** IMM Operations Manager  
**Mục tiêu:** WO open vượt SLA target → `sla_breached = 1`, dashboard phản ánh.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Seed WO Class III Emergency (SLA 4h), set `open_datetime` = 5h trước | — | ☐ |
| 2 | Chạy scheduler hourly manual: `bench execute assetcore.services.imm09.check_repair_sla_breach` | — | ☐ |
| 3 | Kiểm tra WO | `sla_breached = 1`, badge "SLA Vi Phạm" hiển thị | ☐ |
| 4 | PTP mở Dashboard | KPI "SLA Compliance Rate" giảm; WO xuất hiện trong tab vi phạm | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM09-10 — Permission: KTV chỉ thấy WO của mình

**Liên kết:** Security §III.1  
**Role tester:** IMM Biomed Technician (2 accounts)  
**Mục tiêu:** KTV Nguyễn Văn A không thấy WO được giao cho KTV Lê Thị Bình.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | WO-A assigned to `ktv.anha`, WO-B assigned to `ktv.binh` | — | ☐ |
| 2 | `ktv.anha` mở list view | Chỉ thấy WO-A | ☐ |
| 3 | `ktv.anha` truy cập trực tiếp URL của WO-B | Lỗi 403 hoặc "Không có quyền" | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

### UAT-IMM09-11 — Dashboard MTTR Report

**Liên kết:** US-09-09  
**Role tester:** IMM Operations Manager  
**Mục tiêu:** Dashboard CMDashboard hiển thị MTTR đúng, có thể drill-down.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | PTP mở `/imm-09/dashboard` | Tất cả KPI card hiển thị giá trị | ☐ |
| 2 | Click vào MTTR chart | Drill-down theo risk class | ☐ |
| 3 | Filter theo tháng | Chart cập nhật đúng | ☐ |
| 4 | Click 1 WO trong bảng | Redirect đến WO Detail | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM09-12 — Audit Chain Verify

**Liên kết:** III.3 Audit trail integrity  
**Role tester:** IMM QA Officer  
**Mục tiêu:** Audit chain nguyên vẹn sau toàn bộ lifecycle.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở WO đã Completed (từ UAT-05) | — | ☐ |
| 2 | Gọi `verify_audit_chain(asset)` từ console | Trả về `True` | ☐ |
| 3 | Thử sửa 1 record IMM Audit Trail trực tiếp | System block hoặc permission denied | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

## II.5. Tổng Hợp Kết Quả & Bug Found

### Bảng kết quả

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM09-01 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-02 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-03 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-04 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-05 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-06 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-07 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-08 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-09 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-10 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-11 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM09-12 | ☐ Pass / ☐ Fail | | | |

### Sign-off UAT

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (IMM-09) | | | |
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

Xem `assetcore/fixtures/role.json` + `role_profile.json`. Các role liên quan IMM-09:

| Role | Quyền trên Asset Repair |
|---|---|
| IMM Workshop Lead | Create, Read, Write, Submit, Cancel |
| IMM Biomed Technician | Read (own), Write (own) — `if_owner + permission_query` |
| IMM Storekeeper | Read, Write (`spare_parts_used.stock_entry_ref` only) |
| IMM Department Head | Read, Write (`dept_head_name` confirm only) |
| IMM Operations Manager | Read all; dashboard only |
| IMM QA Officer | Read all; audit verify |
| IMM System Admin | Full |

### DocPerm Matrix — `Asset Repair`

| Role | Read | Write | Create | Submit | Cancel | Amend | Delete |
|---|---|---|---|---|---|---|---|
| IMM Workshop Lead | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| IMM Biomed Technician | ✅ (own) | ✅ (own) | ❌ | ✅ (own) | ❌ | ❌ | ❌ |
| IMM Storekeeper | ✅ | ✅ (spare parts only) | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Department Head | ✅ | ✅ (dept_head only) | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Operations Manager | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM QA Officer | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Field-level permission (permlevel)

| Field | permlevel | Mô tả |
|---|---|---|
| `sla_breached` | 1 — IMM Workshop Lead+ | Không cho KTV xem SLA flag |
| `total_parts_cost` | 1 — IMM Operations Manager+ | Chi phí ẩn với KTV/Kho |
| `diagnosis_notes` | 0 — all authenticated | Nội dung kỹ thuật |
| `cannot_repair_reason` | 1 — IMM Workshop Lead+ | Lý do nhạy cảm |

### User Permission (Row-level)

`permission_query_conditions` trong `assetcore/permissions.py`:
```python
def asset_repair_query(user):
    if frappe.has_role("IMM Workshop Lead", user) or frappe.has_role("IMM System Admin", user):
        return ""
    return f"(`tabAsset Repair`.assigned_to = '{user}')"
```

## III.2. API Security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ✅ | Mọi `@frappe.whitelist()` có docstring + required role check |
| CSRF | ✅ | Frappe default X-Frappe-CSRF-Token |
| Input validation | ✅ | `name` field validate qua `frappe.get_value` trước khi dùng |
| SQL injection | ✅ | Frappe ORM parameterized; không raw SQL trong imm09.py |
| Rate limit | ⚠️ Roadmap | Cần cấu hình Frappe rate limit cho endpoint `create_repair_work_order` |

## III.3. Audit Trail Integrity

- Mọi state change (Open/Assigned/Completed/Cannot Repair) sinh `IMM Audit Trail` qua `lifecycle.log_audit_event()`.
- Hash chain SHA-256: `hash = SHA256(prev_hash + canonical_json(event))`.
- API verify: `assetcore.utils.lifecycle.verify_audit_chain(asset)` → `bool`.
- Test tamper: `test_audit_chain_breaks_on_tamper()` (§I.6).
- User KHÔNG có quyền Delete/Amend `IMM Audit Trail` (không có trong DocPerm của bất kỳ role nào).
- Retention: ≥ 5 năm theo NĐ98/2021/NĐ-CP Điều 15.

## III.4. Authentication & Session

| Hạng mục | Config |
|---|---|
| Login | Frappe default — username + password |
| Session timeout | 8 giờ (config `frappe.conf.session_expiry`) |
| Lockout policy | Frappe default: 3 lần fail → lock 15 phút |
| Password policy | Minimum 8 ký tự, 1 chữ hoa, 1 số (enforce Frappe) |
| API key | Tạo per-user, rotate mỗi 90 ngày; không commit vào git |
| 2FA | Roadmap Phase 2 — TOTP via Frappe 2FA |

## III.5. Data Sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Thông tin kỹ thuật thiết bị | `serial_no`, `asset_ref` | Internal | Role permission |
| Chi phí sửa chữa | `total_parts_cost` | Confidential | permlevel 1 |
| Ghi chú nội bộ | `technician_notes` | Internal | Role permission |
| Thông tin cá nhân user | `assigned_to`, `dept_head_name` | Internal | Role permission |
| Dữ liệu bệnh nhân | Không lưu | N/A | AssetCore KHÔNG lưu patient data |

## III.6. Vendor Isolation

`Vendor Engineer` (external) không có quyền trên `Asset Repair` trong DocPerm mặc định. Nếu mở rộng trong tương lai:
- Chỉ thấy WO có `vendor_assigned = session.user`.
- Không thấy: `total_parts_cost`, `diagnosis_notes`, `technician_notes`, audit trail của vendor khác.
- Không export bulk.

## III.7. Secrets Management

- `site_config.json` không commit vào git (`.gitignore` đã cấu hình).
- External API token (email, SMS) lưu `frappe.conf`, không hardcode.
- Backup encrypt at-rest; off-site S3 theo `08_Deployment.md §I.2b`.
- Secret scan CI: `git-secrets` hoặc `detect-secrets` trong pre-commit hook.

## III.8. Logging & Monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| SLA breach phát hiện | WARNING | `frappe.log_error` + `IMM Audit Trail` | ✅ Email Workshop Manager |
| WO overdue > 7 ngày | WARNING | Email scheduler log | ✅ Email Workshop Manager |
| Audit chain tamper | ERROR | `frappe.log_error` | ✅ Email System Admin |
| API 4xx (create WO fail) | INFO | Frappe access log | ❌ |
| Login fail | INFO | Frappe login log | ✅ (sau 3 lần) |
| PII trong log | ❌ | Policy: KHÔNG log patient data | — |

## III.9. Threat Model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Spoofing | Giả mạo session KTV | Low | High | Session cookie HttpOnly + SameSite; Frappe session verify |
| Tampering — Audit | Sửa `IMM Audit Trail` DB trực tiếp | Low | Critical | DocPerm no-delete; DB trigger (roadmap); verify chain endpoint |
| Tampering — WO cost | Edit `total_parts_cost` bypass permlevel | Low | Medium | permlevel 1 + role check |
| Repudiation | KTV phủ nhận đã Submit | Low | High | `IMM Audit Trail` + audit chain hash + actor field |
| Info Disclosure | KTV xem WO của người khác | Low | Medium | `permission_query_conditions` + test UAT-10 |
| DoS — Scheduler | Scheduler overload khi 1000+ WO open | Medium | Medium | Batch 100/run + rate limit; index `status + open_datetime` |
| Elevation of Privilege | KTV tự Cancel WO người khác | Low | High | Workflow role check + `asset_repair_query` |

## III.10. Penetration Test

Trước release đầu tiên (go-live bệnh viện):
- Burp Suite / OWASP ZAP scan trên `uat.assetcore.vn` — 0 High/Critical open.
- sqlmap (mode safe) trên API `create_repair_work_order`, `close_work_order`.
- CSRF token verify bằng curl không có token.
- Role escalation: thử gọi `assign_technician` với role Storekeeper → 403.
- Report lưu: `docs/security/pentest_imm09_v1.md`.

## III.11. Sign-off Security

| Vai trò | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Tech Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

**Điều kiện go-live:** Tất cả Sign-off là Pass hoặc Pass with conditions (với workaround documented).

---

## DoD — Hoàn chỉnh

### I. Test Plan
- [x] Test class structure cho 12 service functions
- [x] ≥ 1 happy + 1 negative test mỗi function
- [x] 9 workflow transitions đều có test  
- [x] Audit chain test (intact + tampered)
- [x] API test ≥ 60% coverage target
- [x] Performance target xác định (k6)
- [x] CI command xác định
- [x] SonarQube + Lighthouse target xác định

### II. UAT
- [x] 12 UAT scenario, cover mọi 7 BR + permission + audit + dashboard
- [x] Mọi User Story (US-09-01 → 09-09) có ≥ 1 UAT scenario
- [x] Test data seed script: `uat_imm09.py`
- [x] 6 Tester accounts + password documented
- [x] Sign-off section sẵn sàng

### III. Security
- [x] DocPerm matrix đầy đủ 7 role
- [x] Field-level permlevel xác định
- [x] Threat model ≥ 7 threat với mitigation
- [ ] Pentest report lưu `docs/security/` (trước go-live)
- [ ] Rate limit cấu hình (roadmap)
- [x] Vendor isolation policy documented
- [x] Sign-off section sẵn sàng
