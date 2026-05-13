# IMM-08 — Kiểm thử & An ninh (Testing, QA & Security)

| Mục | Giá trị |
|---|---|
| Module | **IMM-08 — Bảo trì Định kỳ (Preventive Maintenance)** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | QA Lead + Tech Lead |
| Liên kết | [Module Overview](./IMM-08_Module_Overview.md) · [Functional Specs](./IMM-08_Functional_Specs.md) · [API Interface](./IMM-08_API_Interface.md) |

---

# Phần I — Test Plan

## I.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │  ← Playwright; 1 Golden Scenario (PM full lifecycle)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │  ← pytest + Frappe whitelist (9 endpoints)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │  ← pytest FrappeTestCase (PM WO lifecycle)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │  ← TDD; bulk ở đây (controller + tasks)
     ─┴────────────────────────────────────────────┴─
```

Mọi service function phải có test trước khi code (TDD — CLAUDE.md §17). Mỗi business rule (BR-08-01 → 10) có ≥ 1 happy + 1 negative test.

## I.2. Unit Test — Service Layer

**File:** `assetcore/tests/test_imm08_service.py`

| Test class | Hàm cover | Cases dự kiến |
|---|---|---|
| `TestGeneratePMWorkOrders` | `tasks.generate_pm_work_orders()` | happy(due today), skip(Out of Service BR-08-04), skip(no template BR-08-01), idempotent(no dup WO) |
| `TestCheckPMOverdue` | `tasks.check_pm_overdue()` | happy(set Overdue), email ≤7d Workshop, email 8-30d VP Block2, email >30d BGĐ, skip Completed |
| `TestValidateChecklist` | `pm_work_order._validate_checklist_complete()` | all results filled → pass, 1 empty → VR-08-03 raise |
| `TestValidatePhoto` | `pm_work_order._validate_photo_for_high_risk()` | Class I → skip, Class III + no photo → VR-08-04 raise |
| `TestValidateCmSource` | `pm_work_order._validate_cm_source()` | wo_type=Corrective + source → pass, wo_type=Corrective + no source → VR-08-05 raise |
| `TestUpdatePMSchedule` | `pm_work_order._update_pm_schedule()` | next_due = completion_date + interval (BR-08-03), not due_date |
| `TestHandleFailures` | `pm_work_order._handle_failures()` | Fail-Minor → CM Medium + asset Active, Fail-Major → CM Critical + asset Out of Service (BR-08-09) |
| `TestIsLate` | `pm_work_order._set_completion()` | completion ≤ due → is_late=False, completion > due → is_late=True + days_late (BR-08-05) |
| `TestTaskLog` | `pm_work_order._create_pm_task_log()` | Task Log created immutable; no second creation for same WO |
| `TestReschedule` | `api/imm08.py: reschedule_pm()` | happy(reason ≥ 5), fail(reason < 5 chars VR-08-09), fail(wrong state VR-08-08) |

**Pattern seed:**
```python
class TestGeneratePMWorkOrders(FrappeTestCase):
    def setUp(self):
        self.asset = make_asset("AC-ASSET-PM-TEST-001", status="Active",
                                 risk_class="Class II")
        self.schedule = make_pm_schedule(asset_ref=self.asset.name,
                                          pm_type="Quarterly",
                                          next_due_date=today())
        self.template = make_pm_checklist_template(
            asset_category=self.asset.asset_category, pm_type="Quarterly")

    def test_creates_wo_when_due(self):
        generate_pm_work_orders()
        wos = frappe.get_all("PM Work Order",
                              filters={"asset_ref": self.asset.name, "status": "Open"})
        self.assertEqual(len(wos), 1)

    def test_idempotent_no_duplicate(self):
        generate_pm_work_orders()
        generate_pm_work_orders()
        wos = frappe.get_all("PM Work Order",
                              filters={"asset_ref": self.asset.name})
        self.assertEqual(len(wos), 1)  # BR: không tạo WO thứ 2

    def test_skip_when_out_of_service(self):
        frappe.db.set_value("Asset", self.asset.name, "status", "Out of Service")
        generate_pm_work_orders()
        wos = frappe.get_all("PM Work Order",
                              filters={"asset_ref": self.asset.name})
        self.assertEqual(len(wos), 0)  # BR-08-04
```

## I.3. Unit Test — Validators & Repository

**File:** `assetcore/tests/test_imm08_validators.py`

| Validator | Happy | Fail |
|---|---|---|
| `_check_checklist_result_notes(doc)` | result=Fail, notes filled → pass | result=Fail, notes empty → VR-08-06 raise |
| `_check_unique_pm_schedule(doc)` | New (asset, pm_type) pair → pass | Duplicate → VR-08-07 raise |
| `_check_assign_state(doc)` | WO status=Open → pass | WO status=Completed → VR-08-08 raise |
| `PMWorkOrderRepo.list(filters)` | Paginated results, filter by status/asset | Invalid filter → empty list |
| `PMWorkOrderRepo.get(name)` | Full doc + checklist + schedule info | Not found → NOT_FOUND raise |

## I.4. Integration Test — DocType Lifecycle

**File:** `assetcore/tests/test_pm_work_order_doctype.py`

| Test | Setup | Action | Assert |
|---|---|---|---|
| `test_validate_checklist_incomplete_blocks_submit` | WO In Progress, 1 empty result | `doc.submit()` | `ValidationError` VR-08-03 |
| `test_validate_photo_class3_required` | WO Class III, no photo | `doc.submit()` | `ValidationError` VR-08-04 |
| `test_on_submit_updates_pm_schedule` | WO Completed, completion_date set | `doc.submit()` | `PM Schedule.next_due_date = completion_date + interval` (BR-08-03) |
| `test_on_submit_creates_task_log` | WO valid all pass | `doc.submit()` | `PM Task Log` record created |
| `test_on_submit_fail_minor_creates_cm_wo` | WO with Fail-Minor item | `doc.submit()` | CM WO created, priority=Medium, source_pm_wo set (BR-08-09) |
| `test_on_submit_fail_major_out_of_service` | WO Class III with Fail-Major | `report_major_failure()` | Asset.status=Out of Service, CM WO priority=Critical (BR-08-09) |
| `test_on_submit_updates_asset_dates` | WO Completed | `doc.submit()` | `Asset.custom_last_pm_date`, `custom_next_pm_date` updated |
| `test_audit_trail_immutable` | PM Task Log inserted | `frappe.db.set_value("PM Task Log", ...)` | `PermissionError` (in_create=1 + DocPerm) |

## I.5. Integration Test — Workflow Transitions

**File:** `assetcore/tests/test_imm08_workflow.py`

PM Work Order có 7 states:

| Transition | From → To | Trigger | Test |
|---|---|---|---|
| Phân công KTV | Open → In Progress | `assign_technician` | pass + fail(wrong role — Operator cannot assign) + fail(wrong state VR-08-08) |
| Submit Completed | In Progress → Completed | `submit_pm_result` | pass(all Pass) + fail(checklist incomplete VR-08-03) + fail(Class III no photo VR-08-04) |
| Hoãn lịch | Open/In Progress → Pending–Device Busy | `reschedule_pm` | pass(reason ≥5) + fail(reason <5 VR-08-09) |
| Resume từ Pending | Pending–Device Busy → In Progress | assign again | pass |
| Scheduler Overdue | Open/In Progress → Overdue | `check_pm_overdue` | after due_date → Overdue |
| Major Failure | In Progress → Halted–Major Failure | `report_major_failure` | pass + asset → Out of Service + CM WO created |
| Hủy | Open/Overdue → Cancelled | `cancel_pm_wo` | pass(Workshop Head) + fail(wrong role) |

## I.6. Integration Test — Audit Chain Integrity

**File:** `assetcore/tests/test_imm08_audit.py`

```python
def test_pm_task_log_immutable_after_create():
    # Create PM WO → submit (Completed)
    # Assert PM Task Log created
    # Try frappe.db.set_value("PM Task Log", name, "is_late", 1)
    # Assert raises PermissionError (in_create=1 + DocPerm no write)

def test_audit_chain_intact_after_pm_lifecycle():
    # Create PM Schedule → generate WO → assign → submit Completed
    # Assert verify_audit_chain(asset) == True at each step

def test_audit_chain_breaks_on_tamper():
    # Insert 1 IMM Audit Trail record
    # Modify hash_sha256 directly
    # Assert verify_audit_chain() == False
```

## I.7. API Test

**File:** `assetcore/tests/test_imm08_api.py`

| Test | Endpoint | Verify |
|---|---|---|
| `test_list_pm_work_orders_pagination` | `list_pm_work_orders` | page=1, page_size=20, total ≥ 0 |
| `test_list_filter_status_open` | `list_pm_work_orders?filters={"status":"Open"}` | Mọi row status == Open |
| `test_get_existing_wo` | `get_pm_work_order?name=PM-WO-...` | `success=true`, checklist fields present |
| `test_get_not_found` | `get_pm_work_order?name=FAKE` | `success=false`, `code=NOT_FOUND` |
| `test_assign_technician_happy` | `assign_technician` | status==In Progress, assigned_to set |
| `test_assign_technician_wrong_state` | Completed WO | `code=BAD_STATE` VR-08-08 |
| `test_submit_pm_result_happy` | All checklist Pass, Class II | `success=true`, `new_status=Completed`, `next_pm_date` set |
| `test_submit_pm_result_incomplete_checklist` | 1 empty result | `code=VALIDATION` VR-08-03 |
| `test_submit_pm_result_class3_no_photo` | Class III, no attachment | `code=VALIDATION` VR-08-04 |
| `test_report_major_failure` | `report_major_failure` | WO=Halted, Asset=Out of Service, CM WO created |
| `test_reschedule_pm_short_reason` | reason="OK" (3 chars) | `code=VALIDATION` VR-08-09 |
| `test_get_dashboard_stats` | `get_pm_dashboard_stats?year=2026&month=4` | `compliance_rate_pct`, `overdue`, `trend_6months` present |
| `test_no_permission_operator` | role=VP Block2 → `assign_technician` | HTTP 403 |
| `test_idempotent_submit` | submit 2 lần | 2nd call → `code=BAD_STATE` VR-08-10 |

## I.8. E2E Browser (Playwright)

**File:** `assetcore/tests/e2e/test_imm08_golden.py`

**Golden scenario:** Commissioning submit → PM Schedule tạo → scheduler `generate_pm_work_orders` → WO Open → Workshop Head phân công KTV → KTV điền checklist (all Pass, attach photo nếu Class III) → submit → Completed → Verify PM Schedule.next_due_date = completion_date + interval → PM Task Log immutable → Dashboard KPI cập nhật.

Chạy: `pytest assetcore/tests/e2e/ -m imm08 --headed` (staging only).

## I.9. Performance Test

| Metric | Target | Phương pháp |
|---|---|---|
| `list_pm_work_orders` p95 (50k WO, page=20) | ≤ 300 ms | k6 ramping 20 VU |
| `submit_pm_result` p95 | ≤ 1.5 s | k6 |
| `get_pm_dashboard_stats` p95 | ≤ 800 ms | k6 |
| `report_major_failure` p95 | ≤ 2 s | k6 |
| Scheduler `generate_pm_work_orders` (500 schedules) | ≤ 60 s | bench execute + timer |
| Scheduler `check_pm_overdue` (200 overdue WO) | ≤ 30 s | bench execute + timer |
| Calendar view FE render (30 days, 50 events) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |

## I.10. Test Data

| Loại | Cách seed | File |
|---|---|---|
| AC Asset (test) | `tests/fixtures/test_assets_pm.json` | 4 assets: Class I, II, III, Out of Service |
| PM Schedule | `tests/fixtures/test_pm_schedules.json` | 4 schedules gắn assets trên |
| PM Checklist Template | `tests/fixtures/test_pm_templates.json` | 2 templates (Class II + Class III) |
| PM Work Order | `tests/fixtures/test_pm_work_orders.json` | 5 WO (Open, In Progress, Overdue, Completed, Halted) |
| UAT full seed | `scripts/uat/uat_imm08.py` | Assets + users + PM Schedules + templates đầy đủ |

Reset script: `bench --site assetcore.local execute assetcore.scripts.uat.uat_imm08.setup_seed`

## I.11. Run Commands & Coverage Gate

```bash
# Unit + integration
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm08_service
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_pm_work_order_doctype

# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage

# UAT golden scenario
bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm08.run
```

| Layer | Coverage target | Đo |
|---|---|---|
| Service (`tasks.py` + `pm_work_order.py`) | ≥ 85% | `coverage report` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm08.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | Không crash build | CI `npm run build` |

CI fail nếu coverage < target hoặc bất kỳ test nào fail.

## I.12. Đo Chất Lượng Mã Nguồn

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — PMDashboardView) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format chuẩn PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm08) | main chunk ≤ 250 KB gzip | ≤ budget | Mỗi PR FE (CI report) |

---

# Phần II — UAT Script

## II.1. Phạm vi UAT

**In-scope:**
- Auto-create PM WO khi đến hạn + idempotency (BR-08-01, BR-08-04)
- Happy path submit + lifecycle update (BR-08-03, BR-08-05, BR-08-08)
- Overdue detection + email leo thang (BR-08-05)
- Fail-Minor → CM WO Medium (BR-08-09)
- Fail-Major → CM WO Critical + Asset Out of Service (BR-08-09, BR-08-04)
- Class III ảnh bắt buộc (BR-08-06)
- Reschedule PM (VR-08-09)
- PM Task Log immutable (BR-08-10)
- Hook IMM-04 → IMM-08 (commissioning auto PM Schedule)
- Calendar view + Dashboard KPI
- Mobile checklist UX

**Out-of-scope (UAT):** Load testing, mobile offline sync, calibration WO (IMM-11), holiday list integration.

**Pre-conditions:**
- UAT site: `uat.assetcore.vn` đã deploy bản mới nhất
- Seed data: `bench --site miyano execute assetcore.scripts.uat.uat_imm08.setup_seed`
- 3 tester accounts tạo (xem §II.2)
- Browser: Chrome ≥ 120 hoặc Edge ≥ 120

## II.2. Tester Accounts

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `wm.test` | wm.test@hospital.vn | Workshop Head | Phân công KTV, reschedule, Calendar, Dashboard |
| `ktv.test` | ktv.test@hospital.vn | HTM Technician | Điền checklist, upload ảnh, submit WO |
| `ptp.test` | ptp.test@hospital.vn | VP Block2 | Xem Dashboard KPI, nhận email leo thang |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT).

## II.3. Test Data Đã Seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset | 4 | SEED-PM-01 (Class II Quarterly), SEED-PM-02 (Class II Annual, overdue), SEED-PM-03 (Class III Quarterly), SEED-PM-04 (Class II, Out of Service) |
| PM Schedule | 4 | Gắn với 4 assets trên |
| PM Checklist Template | 1 | `PMCT-Mechanical Ventilator-Quarterly` với ≥ 5 items (≥ 1 critical) |
| Users | 3 | `ktv_test`, `wm_test`, `ptp_test` |

## II.4. Test Scenarios

### UAT-IMM08-01 — Tự Động Tạo PM Work Order + Idempotency (BR-08-01)

**Liên kết:** US-08-01, BR-08-01, BR-08-04
**Role tester:** Scheduler (chạy thủ công)
**Mục tiêu:** Scheduler tạo PM WO đúng khi đến hạn; không tạo bản sao.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `bench --site miyano execute assetcore.tasks.generate_pm_work_orders` | Không lỗi, log `N WOs created` | ☐ |
| 2 | Truy cập `/pm/work-orders?asset_ref=AC-ASSET-UAT-001` | 1 PM WO status=Open, due_date=hôm nay | ☐ |
| 3 | Email Workshop Head | Email `[AssetCore] N PM Work Order mới hôm nay` | ☐ |
| 4 | Mở `/pm/calendar` | SEED-PM-01 hiển thị đúng ngày, màu Open | ☐ |
| 5 | Chạy lại scheduler | KHÔNG tạo WO thứ 2 (idempotent) | ☐ |
| 6 | Seed SEED-PM-04 `status=Out of Service`, chạy scheduler | KHÔNG tạo WO cho SEED-PM-04 (BR-08-04) | ☐ |

**Acceptance:** Tất cả 6 step Pass.

---

### UAT-IMM08-02 — Happy Path: Phân Công + Submit Đúng Hạn (BR-08-03, BR-08-08)

**Liên kết:** US-08-02, BR-08-03, BR-08-05, BR-08-08, BR-08-10
**Role tester:** Workshop Head → KTV
**Mục tiêu:** Full flow phân công → điền checklist → submit → PM Schedule cập nhật đúng (BR-08-03).

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `wm.test` mở WO SEED-PM-01, bấm "Phân công" → `ktv.test` | Status = In Progress, assigned_to set | ☐ |
| 2 | `ktv.test` đăng nhập, mở WO | Checklist clone từ template hiển thị | ☐ |
| 3 | Thử submit khi 1 item chưa điền result | Lỗi VR-08-03 "Tất cả mục checklist phải có kết quả..." | ☐ |
| 4 | Điền tất cả items = Pass, tick "Gắn sticker", nhập duration=45 phút | Progress 100%, nút Hoàn thành enable | ☐ |
| 5 | Click "Hoàn thành" | WO status=Completed, `is_late=false` | ☐ |
| 6 | Kiểm tra PM Schedule | `next_due_date = completion_date + pm_interval` (BR-08-03, KHÔNG từ due_date) | ☐ |
| 7 | Kiểm tra PM Task Log | 1 entry tạo, `is_late=false`, `days_late=0` | ☐ |
| 8 | Thử update PM Task Log qua UI | Bị block — BR-08-10 | ☐ |
| 9 | Kiểm tra Asset | `custom_last_pm_date=today`, `custom_next_pm_date` đúng | ☐ |

**Acceptance:** Tất cả 9 step Pass.

---

### UAT-IMM08-03 — Overdue + Leo Thang Email (BR-08-05)

**Liên kết:** US-08-04, BR-08-05
**Role tester:** Scheduler → Workshop Head + VP Block2
**Mục tiêu:** WO quá hạn 10 ngày → Overdue + email leo thang đúng cấp.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | WO SEED-PM-02 due_date = today-10, status=Open | Setup đúng | ☐ |
| 2 | `bench --site miyano execute assetcore.tasks.check_pm_overdue` | Log `N WOs marked Overdue` | ☐ |
| 3 | Kiểm tra WO | status = Overdue | ☐ |
| 4 | Dashboard `/pm/dashboard` | WO trong bảng "Quá hạn", màu đỏ | ☐ |
| 5 | Email Workshop Head | Alert "PM WO ... quá hạn 10 ngày" | ☐ |
| 6 | Email VP Block2 (8 ≤ 10 ≤ 30 ngày → leo thang) | Có email leo thang | ☐ |
| 7 | `ktv.test` submit kết quả Pass | `is_late=true`, `days_late=10` | ☐ |
| 8 | Dashboard compliance rate | Giảm phản ánh đúng | ☐ |

**Acceptance:** Tất cả 8 step Pass.

---

### UAT-IMM08-04 — Fail-Minor → CM WO Tự Sinh (BR-08-09, BR-08-02)

**Liên kết:** US-08-02 (variant), BR-08-09, BR-08-02
**Role tester:** HTM Technician
**Mục tiêu:** Khi có item Fail-Minor → CM WO tự tạo với priority Medium, asset vẫn Active.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `ktv.test` mở WO, điền 9/10 items = Pass | — | ☐ |
| 2 | Item #4 (không Critical) chọn Fail-Minor, nhập notes | Notes bắt buộc khi Fail (VR-08-06) | ☐ |
| 3 | Điền item #10 = Pass, submit | Status=Completed, overall_result="Pass with Minor Issues" | ☐ |
| 4 | Kiểm tra CM WO mới | `wo_type=Corrective`, `source_pm_wo` trỏ về WO này, priority=Medium | ☐ |
| 5 | Asset.status | Vẫn Active (Fail-Minor không Out of Service) | ☐ |
| 6 | CM WO `technician_notes` | Chứa "Tạo tự động từ PM failure..." | ☐ |

**Acceptance:** Tất cả 6 step Pass.

---

### UAT-IMM08-05 — Major Failure → Asset Out of Service (BR-08-04, BR-08-09)

**Liên kết:** US-08-03, BR-08-04, BR-08-09, BR-08-06
**Role tester:** HTM Technician → Workshop Head + VP Block2
**Mục tiêu:** Fail-Major → WO Halted + Asset Out of Service + CM WO Critical.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `ktv.test` mở WO SEED-PM-03 (Class III) | Banner "Class III ⚠ Cần ảnh" hiển thị | ☐ |
| 2 | Thử submit khi không upload ảnh | Lỗi VR-08-04 "Class III bắt buộc upload ảnh" | ☐ |
| 3 | Đánh dấu 1 item Critical = Fail-Major | Toast warning, nút "Báo lỗi Major" highlight | ☐ |
| 4 | Click "Báo lỗi Major", nhập description ≥ 10 ký tự | Modal confirm | ☐ |
| 5 | Confirm | WO status = Halted–Major Failure | ☐ |
| 6 | Asset status | Out of Service (BR-08-04) | ☐ |
| 7 | CM WO mới | priority=Critical, `source_pm_wo` đúng, notes chứa `[MAJOR FAILURE]` | ☐ |
| 8 | Email Workshop Head + VP Block2 | Email khẩn HTML | ☐ |
| 9 | Chạy lại scheduler | KHÔNG tạo PM WO mới cho SEED-PM-03 (BR-08-04) | ☐ |

**Acceptance:** Tất cả 9 step Pass.

---

### UAT-IMM08-06 — Reschedule PM (VR-08-09)

**Liên kết:** US-08-06, VR-08-09
**Role tester:** Workshop Head
**Mục tiêu:** Reschedule PM với lý do bắt buộc ≥ 5 ký tự.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `wm.test` mở WO bất kỳ Open, click "Hoãn lịch" | Dialog hiện | ☐ |
| 2 | Nhập reason = "Bận" (4 ký tự) | Lỗi VR-08-09 "Lý do hoãn lịch tối thiểu 5 ký tự" | ☐ |
| 3 | Nhập reason ≥ 5 ký tự, chọn new_date = today+3 | API 200, WO status = Pending–Device Busy | ☐ |
| 4 | Kiểm tra `technician_notes` | Có dòng `[Hoãn lịch...→...]: <reason>` | ☐ |
| 5 | Mở `/pm/calendar` | WO hiển thị ngày mới, màu Pending | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM08-07 — Hook IMM-04 → IMM-08 Auto-tạo PM Schedule

**Liên kết:** US-08-07, BR-08-07
**Role tester:** HTM Technician (commissioning)
**Mục tiêu:** Submit Asset Commissioning → PM Schedule tự tạo.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Tạo Asset Commissioning với asset_category = "Mechanical Ventilator" | Saved | ☐ |
| 2 | Submit ACC-... | Submit thành công | ☐ |
| 3 | Kiểm tra PM Schedule | 1 record mới, naming `PMS-{asset}-Quarterly`, `created_from_commissioning` link đúng | ☐ |
| 4 | `next_due_date` | = commissioning_date + pm_interval_days | ☐ |
| 5 | Chạy scheduler ngay | KHÔNG tạo WO (next_due_date > today + alert_days_before) | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM08-08 — Dashboard KPI + Calendar View

**Liên kết:** US-08-08
**Role tester:** VP Block2 + Workshop Head
**Mục tiêu:** Dashboard hiển thị KPI đúng công thức; Calendar đúng màu.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `ptp.test` mở `/pm/dashboard` | 5 KPI cards load | ☐ |
| 2 | Compliance rate khớp công thức | `(on_time / total) × 100` | ☐ |
| 3 | Bảng "Quá hạn" | Chỉ hiện WO status=Overdue | ☐ |
| 4 | Trend 6 tháng | 6 entry, ratio đúng | ☐ |
| 5 | `wm.test` mở `/pm/calendar?year=2026&month=5` | Events màu hoá theo status | ☐ |
| 6 | Click event → drawer chi tiết WO | Slide-in đúng thông tin | ☐ |

**Acceptance:** Tất cả 6 step Pass.

---

### UAT-IMM08-09 — Mobile Checklist UX

**Liên kết:** NFR-08-04
**Role tester:** HTM Technician (điện thoại)
**Mục tiêu:** Checklist hoạt động tốt trên thiết bị di động.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở WO trên Chrome Android viewport 375px | Layout one-item-per-screen | ☐ |
| 2 | Tap nút Pass/Fail | Tap target ≥ 48px, không nhầm nút | ☐ |
| 3 | Click "Đính kèm ảnh" | Camera mở, ảnh attach | ☐ |
| 4 | Class III WO không upload ảnh, click Hoàn thành | Toast "Class III bắt buộc upload ảnh" | ☐ |
| 5 | Upload ảnh, submit | Submit thành công | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM08-10 — Permission Matrix

**Liên kết:** Functional Specs §5
**Role tester:** Tất cả roles
**Mục tiêu:** Mỗi role chỉ thực hiện đúng action cho phép.

| Role | Action | Expected | Pass/Fail |
|---|---|---|---|
| HTM Technician | Điền checklist + submit | ✅ | ☐ |
| HTM Technician | Phân công KTV | ❌ FORBIDDEN | ☐ |
| HTM Technician | Delete PM WO | ❌ FORBIDDEN | ☐ |
| Workshop Head | Phân công KTV | ✅ | ☐ |
| Workshop Head | Reschedule PM | ✅ | ☐ |
| Workshop Head | Delete PM WO | ❌ FORBIDDEN | ☐ |
| VP Block2 | Xem Dashboard | ✅ | ☐ |
| VP Block2 | Submit PM result | ❌ FORBIDDEN | ☐ |
| CMMS Admin | Delete PM WO | ✅ | ☐ |

**Acceptance:** Tất cả 9 row Pass.

---

## II.5. Tổng Hợp Kết Quả & Bug Found

### Bảng kết quả

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM08-01 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM08-02 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM08-03 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM08-04 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM08-05 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM08-06 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM08-07 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM08-08 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM08-09 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM08-10 | ☐ Pass / ☐ Fail | | | |

**Ngưỡng chấp nhận:** ≥ 8/10 Pass; UAT-IMM08-01, 02, 03, 05 **bắt buộc** Pass.

### Sign-off UAT

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (Workshop Manager) | | | |
| Đại diện end-user (VP Block2) | | | |

**Quy ước go-live:** Blocker = 0, Major ≤ 2 (có workaround đã documented).

### Bug Log

| Issue ID | Severity | Mô tả | Fix status |
|---|---|---|---|
| (điền khi phát sinh) | | | |

---

# Phần III — Security Review

## III.1. RBAC

### Role definitions

Xem `assetcore/fixtures/role.json` + `role_profile.json`. Các role liên quan IMM-08:

| Role | Quyền trên PM Work Order |
|---|---|
| Workshop Head | R/W/Create/Submit/Cancel |
| CMMS Admin | Full (bao gồm Delete) |
| HTM Technician | Read, Write (assigned only), Submit (assigned only) |
| Biomed Engineer | Read, Write (hỗ trợ), Submit |
| VP Block2 | Read only |

### DocPerm Matrix — `PM Work Order`

| Role | Read | Write | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| Workshop Head | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| HTM Technician | ✅ (assigned) | ✅ (assigned) | ❌ | ✅ (assigned) | ❌ | ❌ |
| Biomed Engineer | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| VP Block2 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| CMMS Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### DocPerm Matrix — `PM Task Log`

| Role | Read | Create | Write | Delete |
|---|---|---|---|---|
| Workshop Head | ✅ | ✅ (system) | ❌ | ❌ |
| HTM Technician | ✅ | ❌ | ❌ | ❌ |
| CMMS Admin | ✅ | ✅ | ❌ | ❌ |

Note: `PM Task Log` sử dụng `in_create=1` — immutable sau khi tạo.

### Field-level permission (permlevel)

| Field | permlevel | Mô tả |
|---|---|---|
| `technician_notes` | 0 — all authenticated | Ghi chú kỹ thuật |
| `source_pm_wo` | 0 — all authenticated | Truy xuất nguồn CM |
| `is_late`, `days_late` | 1 — Workshop Head+ | KPI nhạy cảm — KTV không nhìn thấy |

### User Permission (Row-level)

```python
def pm_work_order_query(user):
    if frappe.has_role("Workshop Head", user) or frappe.has_role("CMMS Admin", user):
        return ""
    if frappe.has_role("VP Block2", user) or frappe.has_role("Biomed Engineer", user):
        return ""  # read-all
    # HTM Technician: assigned_to only
    return f"(`tabPM Work Order`.assigned_to = '{user}')"
```

## III.2. API Security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ✅ | Mọi `@frappe.whitelist()` có docstring + required role check |
| CSRF | ✅ | Frappe default X-Frappe-CSRF-Token |
| Input validation | ✅ | `name` field validate qua `frappe.get_value` trước khi dùng |
| SQL injection | ✅ | Frappe ORM parameterized; không raw SQL trong imm08.py |
| Rate limit | ⚠️ Roadmap | Cần cấu hình cho `report_major_failure` + `submit_pm_result` |

## III.3. Audit Trail Integrity

- Mỗi PM WO Completed tạo `PM Task Log` (immutable, `in_create=1`).
- Mọi state change (Major Failure, Overdue, Completed, Cancelled) sinh `IMM Audit Trail` qua `lifecycle.log_audit_event()`.
- Hash chain SHA-256: `hash = SHA256(prev_hash + canonical_json(event))`.
- API verify: `assetcore.utils.lifecycle.verify_audit_chain(asset)` → `bool`.
- Test tamper: `test_audit_chain_breaks_on_tamper()` (§I.6).
- `PM Task Log`: DocPerm không có Write/Delete cho bất kỳ user role nào.
- Retention: ≥ 5 năm theo NĐ98/2021/NĐ-CP Điều 15.

## III.4. Authentication & Session

| Hạng mục | Config |
|---|---|
| Login | Frappe default — username + password |
| Session timeout | 8 giờ |
| Lockout policy | 3 lần fail → lock 15 phút |
| Password policy | Minimum 8 ký tự, 1 chữ hoa, 1 số |
| API key | Per-user, rotate mỗi 90 ngày |
| 2FA | Roadmap Phase 2 |

## III.5. Data Sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Kết quả checklist | `checklist_results[].result` | Internal | Role permission |
| KPI lateness | `is_late`, `days_late` | Confidential | permlevel 1 |
| Ghi chú kỹ thuật | `technician_notes` | Internal | Role permission |
| Ảnh thiết bị | Photo attachments | Internal | Role permission |
| Dữ liệu bệnh nhân | Không lưu | N/A | IMM-08 KHÔNG lưu patient data |

## III.6. Vendor Isolation

`Vendor Engineer` (external) không có quyền trên `PM Work Order` trong DocPerm mặc định. Vendor technician hoạt động qua `AC Authorized Technician` (IMM-03), tách biệt với PM internal flow. Nếu mở rộng trong tương lai:
- Chỉ thấy WO có `vendor_assigned = session.user`.
- Không thấy: `is_late`, `days_late`, audit trail của vendor khác.
- Không export bulk.

## III.7. Secrets Management

- `site_config.json` không commit vào git.
- Email alert token lưu `frappe.conf`, không hardcode.
- Backup encrypt at-rest; off-site S3 theo `08_Deployment.md §I.2b`.
- Secret scan CI: `detect-secrets` trong pre-commit hook.

## III.8. Logging & Monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Major Failure phát hiện | CRITICAL | `frappe.log_error` + Audit Trail + email | ✅ Email Workshop Head + VP Block2 |
| PM WO Overdue > 30 ngày | ERROR | Email scheduler log | ✅ Email BGĐ |
| Scheduler `generate_pm_work_orders` không chạy | WARNING | Frappe scheduler log | ✅ Email CMMS Admin |
| PM Task Log tamper attempt | ERROR | `frappe.log_error` | ✅ Email CMMS Admin |
| Audit chain verify fail | ERROR | `frappe.log_error` | ✅ Email CMMS Admin |
| API 4xx (submit fail) | INFO | Frappe access log | ❌ |

## III.9. Threat Model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Spoofing — KTV | Giả mạo session KTV | Low | High | Session HttpOnly + SameSite; row-level permission |
| Tampering — PM Task Log | Sửa `PM Task Log` DB trực tiếp | Low | Critical | `in_create=1`; DocPerm no-write; test immutability |
| Tampering — next_pm_date | Sửa tắt `next_due_date` để skip PM | Low | High | `_update_pm_schedule()` enforce BR-08-03; audit trail |
| Repudiation — Completion | KTV phủ nhận đã submit | Low | High | `PM Task Log` + `IMM Audit Trail` hash chain + actor field |
| Info Disclosure — KPI | KTV xem `is_late` / `days_late` của mình | Low | Medium | permlevel 1 — ẩn với HTM Technician |
| DoS — Scheduler | Scheduler overload 10k+ WO/ngày | Medium | Medium | Batch 100/run; index `status + next_due_date`; skip Out of Service |
| Elevation — Cancel WO | KTV tự cancel WO của người khác | Low | High | Role check trong `cancel_pm_wo`; row-level permission |

## III.10. Penetration Test

Trước release (go-live bệnh viện):
- Burp Suite / OWASP ZAP scan trên `uat.assetcore.vn` — 0 High/Critical open.
- sqlmap (mode safe) trên `submit_pm_result`, `report_major_failure`.
- CSRF token verify bằng curl không có token.
- Role escalation: thử gọi `assign_technician` với role VP Block2 → 403.
- Report lưu: `docs/security/pentest_imm08_v1.md`.

## III.11. Sign-off Security

| Vai trò | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Tech Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner (Workshop Manager) | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

**Điều kiện go-live:** Tất cả Sign-off là Pass hoặc Pass with conditions (với workaround documented).

---

## DoD — Hoàn chỉnh

### I. Test Plan
- [x] Test class structure cho 10 service functions (BR-08-01 → 10)
- [x] ≥ 1 happy + 1 negative test mỗi function
- [x] 7 workflow states — mọi transition có test
- [x] PM Task Log immutable test
- [x] Audit chain test (intact + tampered)
- [x] API test ≥ 60% coverage target (9 endpoints)
- [x] Performance target xác định (k6) — đặc biệt `list_pm_work_orders` ≤ 300ms
- [x] CI command xác định
- [x] SonarQube + Lighthouse target xác định

### II. UAT
- [x] 10 UAT scenario, cover mọi 10 BR + permission + audit + dashboard + mobile
- [x] Mọi User Story (US-08-01 → 08-08) có ≥ 1 UAT scenario
- [x] Test data seed script: `uat_imm08.py`
- [x] 3 Tester accounts + password documented
- [x] Sign-off section sẵn sàng

### III. Security
- [x] DocPerm matrix đầy đủ cho PM Work Order + PM Task Log
- [x] `PM Task Log` immutable policy documented
- [x] Threat model ≥ 7 threat với mitigation
- [ ] Pentest report lưu `docs/security/` (trước go-live)
- [ ] Rate limit `report_major_failure` (roadmap)
- [x] Vendor isolation policy documented
- [x] Sign-off section sẵn sàng
