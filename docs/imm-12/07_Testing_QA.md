# IMM-12 — Kiểm thử & An ninh (Testing, QA & Security)

| Mục | Giá trị |
|---|---|
| Module | **IMM-12 — Sự cố & CAPA (Incident & Corrective Action)** |
| Phiên bản | 1.2.0 |
| Ngày cập nhật | 2026-05-14 |
| Owner | QA Lead + Tech Lead |
| Trạng thái | 🟡 BE/FE LIVE — `services/imm12.py`, `api/imm12.py` (14 endpoint), DocType `IMM RCA Record` đã có. Test cốt lõi tại `assetcore/tests/test_imm12.py` ✅. UAT/E2E/Pentest pending. |
| Liên kết | [Module Overview](./IMM-12_Module_Overview.md) · [Functional Specs](./IMM-12_Functional_Specs.md) · [UAT Script](./IMM-12_UAT_Script.md) |

---

# Phần I — Test Plan

## I.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │  ← Playwright; bắt buộc 2 Golden Scenarios
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

⚠️ **Pending implementation** — Mọi test class phải được viết trước khi implement service (TDD). `Incident Report` và `IMM CAPA Record` đã có DocType (IMM-00 LIVE) — test cần cover các **custom fields** và **workflow extensions** mà IMM-12 thêm vào.

## I.2. Unit Test — Service Layer

**File (cần tạo):** `assetcore/tests/test_imm12_service.py`

⚠️ Pending — viết trước khi `services/imm12.py` implement (TDD).

| Test class | Hàm cover | Cases dự kiến |
|---|---|---|
| `TestReportIncident` | `report_incident()` | happy(Minor), happy(Critical → OOS + audit), fail(no asset), fail(Decommissioned asset) |
| `TestClinicalImpact` | `report_incident()` + `VR-12-02` | Critical no clinical_impact → raise; Critical with impact → pass |
| `TestAcknowledge` | `acknowledge_incident()` | happy, fail(not Open/New status), fail(wrong role) |
| `TestResolve` | `resolve_incident()` | happy(Minor → no RCA), happy(Major → RCA triggered), happy(Critical → RCA triggered) |
| `TestTriggerRCA` | `trigger_rca_if_required()` | Major → RCA created, Minor → no RCA, Chronic flag → RCA created |
| `TestRCAGate` | close incident (VR-12-03) | Major with RCA Completed → pass; Major with RCA In Progress → raise |
| `TestCAPAGate` | close incident (VR-12-04) | Critical with CAPA Closed → pass; Critical with CAPA Open → raise |
| `TestChronicDetect` | `detect_chronic_failures()` | 3 incidents same fault_code / 90d → RCA + chronic flag; 2 incidents → no RCA; idempotent (existing RCA open → no duplicate) |
| `TestSubmitRCA` | `submit_rca_and_create_capa()` | happy path, fail(root_cause empty), fail(rca_method invalid) |
| `TestAuditEveryTransition` | All `imm12.*` | Every state change calls `log_audit_event()` |
| `TestCriticalOOS` | `report_incident()` BR-12-04 | Critical submit → `transition_asset_status(→ Out of Service)` called |

**Pattern seed (khi implement):**
```python
class TestReportIncident(FrappeTestCase):
    def setUp(self):
        self.asset = make_asset("ACC-ASSET-TEST-012-001",
                                status="Active", risk_class="Class III")

    def test_critical_incident_sets_asset_oos(self):
        # ⚠️ Pending — implement after services/imm12.py created
        ir = report_incident(
            asset=self.asset.name,
            severity="Critical",
            fault_code="VENT_ALARM_HIGH",
            fault_description="Test",
            clinical_impact="Test patient impact"
        )
        self.asset.reload()
        self.assertEqual(self.asset.lifecycle_status, "Out of Service")

    def test_critical_no_clinical_impact_raises(self):
        # ⚠️ Pending
        with self.assertRaises(ServiceError) as ctx:
            report_incident(
                asset=self.asset.name,
                severity="Critical",
                fault_code="VENT_ALARM_HIGH",
                fault_description="Test"
                # no clinical_impact
            )
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
```

## I.3. Unit Test — Validators & Repository

**File (cần tạo):** `assetcore/tests/test_imm12_validators.py`

⚠️ Pending — viết sau khi custom fields trên `Incident Report` và `RCA Record` DocType tạo xong.

| Validator | Happy | Fail |
|---|---|---|
| `VR-12-01: asset tồn tại và không Decommissioned` | Active asset → pass | Decommissioned asset → raise |
| `VR-12-02: Critical bắt buộc clinical_impact` | Critical + clinical_impact filled → pass | Critical + empty → raise |
| `VR-12-03: Block Close nếu RCA chưa Completed` | Major + RCA Completed → pass | Major + RCA In Progress → raise |
| `VR-12-04: Block Close Critical nếu CAPA chưa Closed` | Critical + CAPA Closed → pass | Critical + CAPA Open → raise |
| `VR-12-05: Thứ tự timestamp hợp lệ` | acknowledged_at < resolved_at → pass | resolved_at < acknowledged_at → raise |
| `VR-12-06: RCA root_cause + rca_method bắt buộc` | Both filled + valid method → pass | Empty root_cause → raise; invalid method → raise |
| `VR-12-07: CAPA fields bắt buộc` | All 3 filled → pass | Any empty → raise (BR-00-08, IMM-00) |
| `IncidentRepo.list(filters)` | Trả list đúng phân trang | Filter invalid → empty |
| `IncidentRepo.get(name)` | Trả doc đầy đủ + asset_info + linked RCA/CAPA | Không tồn tại → raise NOT_FOUND |

## I.4. Integration Test — DocType Lifecycle

**File (cần tạo):** `assetcore/tests/test_incident_report_doctype.py`

⚠️ Pending — `Incident Report` DocType đã LIVE (IMM-00) nhưng custom fields IMM-12 chưa có. Test sau khi custom fields được thêm.

| Test | Setup | Action | Assert |
|---|---|---|---|
| `test_critical_before_submit_needs_clinical_impact` | Asset Active, severity=Critical, clinical_impact=NULL | `doc.save()` | `ValidationError` VR-12-02 |
| `test_critical_submit_sets_asset_oos` | Asset Active, severity=Critical, clinical_impact filled | `doc.save()` | `Asset.lifecycle_status = Out of Service` (BR-12-04) |
| `test_major_resolve_triggers_rca` | IR Major status=In Progress | `resolve_incident(ir.name, ...)` | `RCA Record` created, `IR.status = RCA Required` |
| `test_minor_resolve_no_rca` | IR Minor status=In Progress | `resolve_incident(ir.name, ...)` | No `RCA Record` created, `IR.status = Resolved` |
| `test_close_major_blocked_rca_incomplete` | IR Major, RCA In Progress | `frappe.set_value(IR, status, Closed)` | `ValidationError` VR-12-03 |
| `test_close_major_allowed_rca_completed` | IR Major, RCA Completed | Set status Closed | `IR.status = Closed` |
| `test_audit_trail_on_acknowledge` | IR Open | `acknowledge_incident(ir.name, ...)` | `IMM Audit Trail` record with event_type `incident_acknowledged` |
| `test_chronic_detection_idempotent` | 3 IDs same fault_code/90d, RCA already Open | `detect_chronic_failures()` | No duplicate RCA created |

**File (cần tạo):** `assetcore/tests/test_rca_record_doctype.py`

⚠️ Pending — `RCA Record` DocType chưa tồn tại.

| Test | Setup | Action | Assert |
|---|---|---|---|
| `test_submit_rca_needs_root_cause` | RCA In Progress, root_cause=NULL | `doc.submit()` | `ValidationError` VR-12-06 |
| `test_submit_rca_creates_capa` | RCA with all fields filled | `submit_rca_and_create_capa()` | `IMM CAPA Record` created |
| `test_rca_method_must_be_valid` | rca_method = "RandomMethod" | `doc.submit()` | `ValidationError` VR-12-06 |

## I.5. Integration Test — Workflow Transitions

**File (cần tạo):** `assetcore/tests/test_imm12_workflow.py`

⚠️ Pending — viết sau khi Workflow JSON cho `Incident Report` extension tạo xong.

Workflow `Incident Report` có 6 main states + RCA branch. Test mỗi transition:

| Transition | From → To | Role required | Test |
|---|---|---|---|
| Gửi báo cáo | Draft → Open | Reporting User | pass + fail(Decommissioned asset) |
| Tiếp nhận | Open → Acknowledged | IMM Workshop Lead | pass + fail(wrong role) |
| Phân công WO | Acknowledged → In Progress | IMM Workshop Lead | pass |
| Resolve (Minor) | In Progress → Resolved | IMM Workshop Lead | pass + assert no RCA |
| Resolve (Major/Critical) | In Progress → RCA Required | IMM Workshop Lead | pass + assert RCA created |
| RCA Completed → Close | RCA Required → Closed | IMM Workshop Lead + QA | pass + fail(RCA still In Progress) |
| Hủy (False Alarm) | New/Open → Cancelled | IMM Workshop Lead | pass + require cancel_reason |

## I.6. Integration Test — Audit Chain Integrity

**File (cần tạo):** `assetcore/tests/test_imm12_audit.py`

⚠️ Pending. Reuse pattern từ IMM-09 `test_imm09_audit.py`.

```python
def test_audit_chain_intact_after_incident_lifecycle():
    # Tạo IR → Acknowledge → Assign WO → Resolve → RCA → CAPA → Close
    # Sau mỗi bước, assert verify_audit_chain(asset) == True

def test_every_imm12_transition_creates_audit_entry():
    # Mỗi lần gọi service imm12.*, assert có IMM Audit Trail entry mới

def test_audit_chain_breaks_on_tamper():
    # Submit IR → Insert Audit Trail
    # Sửa thẳng DB hash_sha256
    # Assert verify_audit_chain() == False
```

## I.7. API Test

**File (cần tạo):** `assetcore/tests/test_imm12_api.py`

⚠️ Pending — viết sau khi `api/imm12.py` tạo xong.

| Test | Endpoint | Verify |
|---|---|---|
| `test_list_default` | `list_incidents` | page=1, total ≥ 0, success=true |
| `test_list_filter_severity` | `list_incidents?filters={"severity":"Critical"}` | Mọi row severity == Critical |
| `test_get_existing` | `get_incident?name=IR-...` | `success=true`, fields đầy đủ kể cả linked RCA/CAPA |
| `test_get_not_found` | `get_incident?name=FAKE` | `success=false`, `code=NOT_FOUND` |
| `test_report_incident_happy` | `report_incident` (Minor) | `success=true`, IR name trả về |
| `test_report_critical_no_clinical_impact` | Critical, no clinical_impact | `success=false`, `code=VALIDATION` |
| `test_report_no_permission` | role=IMM QA Officer (no create) | HTTP 403 |
| `test_acknowledge_incident` | `acknowledge_incident` | IR.status=Acknowledged, response_at set |
| `test_resolve_major_triggers_rca` | `resolve_incident` (Major) | RCA Record created in response data |
| `test_close_major_rca_incomplete` | `close_incident` (Major, RCA In Progress) | `code=VALIDATION` VR-12-03 |
| `test_submit_rca` | `submit_rca` with full fields | `success=true`, CAPA created |
| `test_detect_chronic` | `detect_chronic_failures` (manual trigger) | idempotent; RCA created when threshold met |
| `test_get_incident_dashboard` | `get_incident_dashboard_kpis` | MTTA, MTTR, open count, critical count fields |

## I.8. E2E Browser (Playwright)

**File (cần tạo):** `assetcore/tests/e2e/test_imm12_golden.py`

⚠️ Pending — viết sau khi Frontend views hoàn chỉnh.

**Golden scenario 1 — Minor Incident Full Lifecycle:** Điều dưỡng báo cáo IR Minor → Workshop Lead Acknowledge → Link Repair WO → Resolve → Close trực tiếp (không cần RCA) → Verify audit trail + ALE.

**Golden scenario 2 — Critical Incident + RCA + CAPA:** Báo cáo IR Critical → Verify Asset → OOS auto → Acknowledge + phân công KTV → Resolve → Auto RCA trigger → Workshop Lead điền RCA 5-Why → Submit RCA → CAPA auto create → QA Officer Close CAPA → Verify IR Closed.

Chạy: `pytest assetcore/tests/e2e/ -m imm12 --headed` (staging only).

## I.9. Performance Test

⚠️ Pending — thiết lập sau khi API layer hoàn chỉnh.

| Metric | Target | Phương pháp |
|---|---|---|
| `list_incidents` p95 (500 IR) | ≤ 800 ms | k6 ramping 20 VU |
| `report_incident` p95 | ≤ 1.5 s | k6 |
| `get_incident_dashboard_kpis` p95 | ≤ 2 s | k6 |
| Scheduler `detect_chronic_failures` (10k IR) | ≤ 60 s | bench execute + timer |
| List view FE render (100 rows) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |

## I.10. Test Data

⚠️ Pending — seed scripts cần viết trước UAT execution.

| Loại | Cách seed | File (cần tạo) |
|---|---|---|
| AC Asset (test) | `tests/fixtures/test_assets_imm12.json` | 4 assets (xem seed data §3.1 UAT Script) |
| Fault Code dictionary | `tests/fixtures/test_fault_codes.json` | 8 fault codes (xem §3.2 UAT Script) |
| IMM CAPA Record (pre-existing) | Script | 3 CAPA records ở trạng thái khác nhau |
| Chronic history IDs | `tests/fixtures/test_chronic_ir_history.json` | 2 IR cho TC-12-11 (xem §3.5 UAT Script) |
| UAT full seed | `scripts/uat/uat_imm12.py` | 4 assets + 6 users + fault codes |

Reset: `bench --site assetcore.local execute assetcore.scripts.uat.uat_imm12.seed_data`

## I.11. Run Commands & Coverage Gate

⚠️ Pending — commands hoạt động sau khi test files được tạo.

```bash
# Unit + integration (khi implement)
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm12_service
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_incident_report_doctype

# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage

# UAT golden scenario (khi FE hoàn chỉnh)
bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm12.run
```

| Layer | Coverage target | Đo |
|---|---|---|
| Service (`services/imm12.py`) | ≥ 85% | `coverage report` |
| DocType lifecycle (Incident + RCA) | ≥ 70% | `coverage report` |
| API (`api/imm12.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | Không crash build | CI `npm run build` |

## I.12. Đo Chất Lượng Mã Nguồn

⚠️ Pending — áp dụng khi code implement.

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — IncidentDashboard) | Performance ≥ 90, Accessibility ≥ 95 | ≥ target | Mỗi release |
| **ESLint + vue-tsc** | 0 error prod build | pass | Mỗi PR FE |
| **ruff / black** (BE) | 0 error, PEP8 | pass | Mỗi PR |
| **Bundle size** (FE chunk imm12) | ≤ 250 KB gzip | ≤ budget | Mỗi PR FE |

---

# Phần II — UAT Script

## II.1. Phạm vi UAT

**In-scope:**
- Tạo Incident Report (Minor/Major/Critical) với validation BR-12-01
- Acknowledge + phân công → In Progress
- Critical → Auto Asset OOS (BR-12-04)
- Resolve Minor → Close trực tiếp (no RCA)
- Resolve Major/Critical → Auto RCA trigger (BR-12-02)
- RCA 5-Why form → Submit → CAPA auto-create (BR-12-06)
- Close CAPA (BR-00-08) → Close Incident
- Chronic detection (BR-12-03): ≥3 incidents same fault_code/90 ngày
- Audit Trail immutability + chain integrity
- Permission: Reporting User không Acknowledge/Close; QA Officer chỉ Close CAPA

**Out-of-scope (UAT):** Load testing, SMS notification, Vigilance reporting BYT (IMM-15).

**Pre-conditions:**
- ⚠️ UAT chưa thể thực hiện — `services/imm12.py`, `api/imm12.py`, `RCA Record` DocType chưa implement
- Khi ready: UAT site `uat.assetcore.vn` đã deploy; seed data từ `uat_imm12.py` chạy thành công
- Tester accounts tạo (xem §II.2)
- Browser: Chrome ≥ 120 hoặc Edge ≥ 120

## II.2. Tester Accounts

⚠️ Tạo khi UAT chuẩn bị thực hiện. Tham chiếu đầy đủ: `IMM-12_UAT_Script.md §Section 3.3`.

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `nurse.uat` | nurse.uat@hospital.vn | Reporting User | Báo cáo sự cố, test permission |
| `manager.ws` | manager.uat@hospital.vn | IMM Workshop Lead | Acknowledge, phân công, RCA |
| `ktv.nguyen` | ktv.nguyen.uat@hospital.vn | IMM Biomed Technician | Resolve, gắn WO |
| `qa.uat` | qa.uat@hospital.vn (qa.uat) | IMM QA Officer | Close CAPA, verify audit |
| `ptp.uat` | ptp.uat@hospital.vn | IMM Operations Manager | Dashboard, export |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT).

## II.3. Test Data Đã Seed

⚠️ Seed khi implement. Tham chiếu chi tiết: `IMM-12_UAT_Script.md §Section 3`.

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset | 4 | UAT-001 (Class III life-support), UAT-002/003 (Class II), UAT-004 (Class II) |
| Fault Code dictionary | 8 | VENT_ALARM_HIGH/LOW, PROBE_DISCONNECT/FAIL, DISPLAY_LED_FAIL, v.v. |
| Incident Report (pre-seeded) | 3 | IR-UAT-002 (backdated 35 phút), IR-UAT-009/010 (chronic history) |
| Asset Repair WO | 1 | AR-UAT-001 để test TC-12-07 |

## II.4. Test Scenarios

Tham chiếu chi tiết từng step: `IMM-12_UAT_Script.md TC-12-01 → TC-12-17`.

### UAT-IMM12-01 — Tạo IR cơ bản + Critical validation (TC-12-01, TC-12-02)

**Liên kết:** US-12-01, BR-12-01, VR-12-02  
**Role tester:** Reporting User  
**Mục tiêu:** Tạo IR thành công; Critical thiếu clinical_impact → bị block.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Điều dưỡng tạo IR Minor cho ACC-ASS-UAT-004 | IR tạo OK, status = New | ☐ |
| 2 | Tạo IR Critical cho ACC-ASS-UAT-001, để trống clinical_impact | Block: VR-12-02 | ☐ |
| 3 | Điền clinical_impact, Submit | IR tạo OK + Asset → OOS auto | ☐ |
| 4 | Kiểm tra ALE | event `incident_reported` + `asset_out_of_service` | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM12-02 — Acknowledge + In Progress (TC-12-03)

**Liên kết:** US-12-02  
**Role tester:** IMM Workshop Lead  
**Mục tiêu:** Acknowledge trong đúng thời gian; Reporting User không Acknowledge được.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Workshop Lead Acknowledge IR-UAT-001, chọn Priority, phân công KTV | IR → Acknowledged, `response_at` set | ☐ |
| 2 | Điều dưỡng thử Acknowledge IR khác | 403: không có quyền | ☐ |
| 3 | Kiểm tra ALE | event `incident_acknowledged` | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

### UAT-IMM12-03 — Resolve Minor → Close trực tiếp (TC-12-08)

**Liên kết:** BR-12-02 (negative — Minor không cần RCA)  
**Role tester:** IMM Biomed Technician  
**Mục tiêu:** Minor incident close không cần RCA.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | KTV Resolve IR Minor với resolution_notes | status = Resolved, `rca_required = False` | ☐ |
| 2 | Kiểm tra không có RCA Record tạo | — | ☐ |
| 3 | Workshop Lead Close IR | status = Closed | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

### UAT-IMM12-04 — Resolve Major/Critical → Auto RCA (TC-12-09)

**Liên kết:** US-12-03, BR-12-02, BR-12-06  
**Role tester:** IMM Biomed Technician → IMM Workshop Lead  
**Mục tiêu:** Major Resolved → RCA auto-created → block Close cho đến khi RCA Completed.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Resolve IR Major | status = RCA Required, RCA-YYYY-xxxx tạo | ☐ |
| 2 | Thử Close IR khi RCA In Progress | Block: VR-12-03 | ☐ |
| 3 | Workshop Lead điền RCA 5-Why đầy đủ, Submit | RCA status = Completed, CAPA auto-created | ☐ |
| 4 | Close IR | Thành công, status = Closed | ☐ |
| 5 | Kiểm tra ALE + Audit Trail | Đầy đủ | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM12-05 — RCA Form 5-Why validation (TC-12-14)

**Liên kết:** BR-12-07, VR-12-06  
**Role tester:** IMM Biomed Technician / Workshop Lead  
**Mục tiêu:** RCA không submit được khi thiếu root_cause hoặc corrective_action.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Thử Submit RCA khi root_cause_summary trống | Block: VR-12-06 | ☐ |
| 2 | Điền root_cause nhưng để trống corrective_action | Block | ☐ |
| 3 | Điền đầy đủ why_1→5, root_cause, corrective, preventive | Submit OK | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

### UAT-IMM12-06 — QA Officer Close CAPA (TC từ IMM-09 pattern)

**Liên kết:** US-12-04, BR-00-08  
**Role tester:** IMM QA Officer  
**Mục tiêu:** CAPA Close hợp lệ; Workshop Lead không Close CAPA được.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Workshop Lead thử Close CAPA | 403: chỉ QA Officer được close | ☐ |
| 2 | QA Officer Close CAPA với đầy đủ corrective + preventive | CAPA status = Closed | ☐ |
| 3 | Kiểm tra ALE | event CAPA closed | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

### UAT-IMM12-07 — Chronic Failure Detection (TC-12-11)

**Liên kết:** US-12-05, BR-12-03  
**Role tester:** System (manual trigger) + Workshop Lead  
**Mục tiêu:** ≥3 incidents cùng fault_code/90 ngày → RCA auto + chronic flag; idempotent.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Tạo IR-UAT-011 (incident thứ 3 cùng PROBE_DISCONNECT trên UAT-003) | IR tạo OK | ☐ |
| 2 | Chạy `bench execute assetcore.services.imm12.detect_chronic_failures` | RCA tạo với trigger_type="Chronic Failure" | ☐ |
| 3 | Kiểm tra chronic_failure_flag = True trên 3 IR | — | ☐ |
| 4 | Chạy detect lần 2 | Không tạo RCA thứ 2 (idempotent) | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM12-08 — Audit Trail Immutability (TC-12-12)

**Liên kết:** BR-12-05, BR-00-03  
**Role tester:** IMM System Admin  
**Mục tiêu:** Không ai xóa hoặc sửa được `IMM Audit Trail`.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Mở IMM Audit Trail list | Read-only | ☐ |
| 2 | Thử DELETE qua API | 403 Forbidden | ☐ |
| 3 | Thử EDIT bất kỳ field | Block | ☐ |
| 4 | `verify_audit_chain(asset)` | True | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM12-09 — Dashboard KPI (TC-12-15)

**Liên kết:** KPI definitions §11 Module Overview  
**Role tester:** IMM Operations Manager  
**Mục tiêu:** Dashboard hiển thị MTTA, MTTR, open count, critical count; drill-down hoạt động.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | PTP mở `/imm-12/dashboard` | Dashboard load | ☐ |
| 2 | Kiểm tra MTTA = avg(response_at − created_at) | Tính đúng | ☐ |
| 3 | Kiểm tra MTTR = avg(resolved_at − created_at) | Tính đúng | ☐ |
| 4 | Click vào IR trong open list | Redirect đến detail | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM12-10 — Permission: Reporting User scope

**Liên kết:** Security §III.1  
**Role tester:** Reporting User  
**Mục tiêu:** Điều dưỡng chỉ thấy IR của khoa mình; không Acknowledge/Close được.  
**⚠️ Pending execution.**

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Điều dưỡng vào `/imm-12/dashboard` | 403 hoặc redirect | ☐ |
| 2 | Thử API `acknowledge_incident` | 403 | ☐ |
| 3 | Xem IR list | Chỉ thấy IR của own department | ☐ |

**Acceptance:** Tất cả 3 step Pass.

---

## II.5. Tổng Hợp Kết Quả & Bug Found

⚠️ Điền khi UAT thực hiện.

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM12-01 | ⚠️ Pending | | | |
| UAT-IMM12-02 | ⚠️ Pending | | | |
| UAT-IMM12-03 | ⚠️ Pending | | | |
| UAT-IMM12-04 | ⚠️ Pending | | | |
| UAT-IMM12-05 | ⚠️ Pending | | | |
| UAT-IMM12-06 | ⚠️ Pending | | | |
| UAT-IMM12-07 | ⚠️ Pending | | | |
| UAT-IMM12-08 | ⚠️ Pending | | | |
| UAT-IMM12-09 | ⚠️ Pending | | | |
| UAT-IMM12-10 | ⚠️ Pending | | | |

### Sign-off UAT

⚠️ Điền khi UAT hoàn tất.

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (IMM-12) | | | |
| Đại diện end-user (Workshop Manager) | | | |

**Quy ước go-live:** Blocker = 0, Major ≤ 2 (với workaround documented). Critical TC: UAT-IMM12-04, UAT-IMM12-07, UAT-IMM12-08 phải 100% Pass.

### Bug Log

| Issue ID | Severity | Mô tả | Fix status |
|---|---|---|---|
| (điền khi phát sinh) | | | |

---

# Phần III — Security Review

## III.1. RBAC

### Role definitions

| Role | Quyền hạn trên Incident Report |
|---|---|
| Reporting User | Create (own dept), Read (own dept) |
| IMM Workshop Lead | Read all, Acknowledge, Resolve, Create RCA, Close Incident |
| IMM Biomed Technician | Read (assigned), Resolve (assigned) |
| IMM QA Officer | Read all; Close CAPA; verify Audit Trail |
| IMM Department Head | Read all; nhận escalation |
| IMM Operations Manager | Read all; dashboard; export |
| IMM System Admin | Full |

### DocPerm Matrix — `Incident Report`

⚠️ Pending implementation. Matrix đề xuất:

| Role | Read | Write | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| Reporting User | ✅ (own dept) | ✅ (own, draft only) | ✅ | ✅ | ❌ | ❌ |
| IMM Workshop Lead | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| IMM Biomed Technician | ✅ (assigned) | ✅ (assigned) | ❌ | ❌ | ❌ | ❌ |
| IMM QA Officer | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Operations Manager | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### DocPerm Matrix — `RCA Record`

⚠️ Pending implementation.

| Role | Read | Write | Create | Submit |
|---|---|---|---|---|
| IMM Workshop Lead | ✅ | ✅ | ✅ | ✅ |
| IMM QA Officer | ✅ | ✅ | ✅ | ✅ |
| IMM Biomed Technician | ✅ | ✅ (assigned) | ❌ | ❌ |
| IMM Operations Manager | ✅ | ❌ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ |

### DocPerm Matrix — `IMM CAPA Record`

Kế thừa từ IMM-00 (đã LIVE). Chỉ QA Officer có quyền Submit/Close.

### Field-level permission (permlevel)

⚠️ Pending — xác định sau khi custom fields IMM-12 được thiết kế.

| Field | permlevel | Mô tả |
|---|---|---|
| `clinical_impact` | 0 — all authenticated | Cần để audit |
| `rca_record` | 1 — IMM Workshop Lead+ | Link nhạy cảm |
| `linked_capa` | 1 — IMM QA Officer+ | CAPA content |
| `chronic_failure_flag` | 1 — IMM Workshop Lead+ | Internal flag |

### User Permission (Row-level)

⚠️ Pending — `permission_query_conditions` cho Reporting User:
```python
def incident_report_query(user):
    if frappe.has_role("IMM Workshop Lead", user) or frappe.has_role("IMM System Admin", user):
        return ""
    # Reporting User chỉ thấy IR của khoa mình
    user_dept = frappe.db.get_value("Employee", {"user_id": user}, "department")
    if user_dept:
        return f"(`tabIncident Report`.department = '{user_dept}')"
    return f"(`tabIncident Report`.reported_by = '{user}')"
```

## III.2. API Security

⚠️ Pending implementation.

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ⚠️ Pending | Mọi `@frappe.whitelist()` phải có docstring + required role check |
| CSRF | ✅ (Frappe default) | X-Frappe-CSRF-Token |
| Input validation | ⚠️ Pending | `fault_description` sanitize XSS; `name` field validate trước dùng |
| SQL injection | ⚠️ Pending | Frappe ORM parameterized; không raw SQL trong `imm12.py` |
| Rate limit | ⚠️ Roadmap | `report_incident` endpoint — clinical user có thể spam |
| Mobile API security | ⚠️ Pending | Reporting User từ mobile → validate session |

## III.3. Audit Trail Integrity

- Mọi state change (Open/Acknowledged/In Progress/Resolved/Closed/RCA Required) sinh `IMM Audit Trail` qua `services/imm00.py: log_audit_event()` — không gọi trực tiếp, không bypass.
- Hash chain SHA-256 kế thừa từ IMM-00.
- API verify: `assetcore.utils.lifecycle.verify_audit_chain(asset)`.
- ⚠️ Test tamper: `test_audit_chain_breaks_on_tamper()` — Pending.
- `IMM Audit Trail` đã có DocPerm no-delete từ IMM-00.
- Retention: ≥ 5 năm theo NĐ98/2021/NĐ-CP Điều 7; CAPA records ≥ 7 năm (ISO 13485).

## III.4. Authentication & Session

Kế thừa config từ IMM-09 `08_Deployment.md §III.4`. Lưu ý thêm:

| Hạng mục | Config |
|---|---|
| Reporting User từ mobile | Session token validate; không cho API key dài hạn cho Reporting User role |
| Lockout policy | 3 lần fail → lock 15 phút |

## III.5. Data Sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Mô tả sự cố lâm sàng | `clinical_impact`, `fault_description` | Internal | Role permission |
| Thông tin bệnh nhân | **Không lưu** | N/A | Policy: chỉ mô tả thiết bị, không gắn patient ID |
| RCA root cause analysis | `root_cause`, `rca_five_why_steps` | Confidential | permlevel 1 |
| CAPA corrective action | `corrective_action`, `preventive_action` | Internal | IMM QA Officer+ only |
| Chronic failure flag | `chronic_failure_flag` trên asset | Internal | permlevel 1 |

## III.6. Vendor Isolation

Vendor không có quyền trên `Incident Report` hoặc `IMM CAPA Record` mặc định. Nếu mở rộng cho vendor contractor trong tương lai:
- Chỉ thấy IR liên quan đến asset trong contract của họ.
- Không thấy: RCA content, CAPA corrective action, audit trail của incident khác.

## III.7. Secrets Management

Kế thừa policy từ IMM-09. Không có secrets mới trong IMM-12.

## III.8. Logging & Monitoring

⚠️ Pending — cấu hình khi service layer implement.

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Critical Incident tạo | WARNING | `IMM Audit Trail` + email | ✅ Email Workshop Lead + Dept Head ngay lập tức |
| Chronic Failure phát hiện | WARNING | `frappe.log_error` + email | ✅ Email Workshop Lead + QA Officer |
| CAPA overdue > 30 ngày | WARNING | Scheduler log + email | ✅ Email QA Officer (daily) |
| RCA overdue | WARNING | Scheduler log + email | ✅ Email Workshop Lead |
| Audit chain tamper | ERROR | `frappe.log_error` | ✅ Email System Admin |
| Mass incident creation (> 10 IR/phút) | WARNING | Nginx log | ✅ Alert DevOps |

## III.9. Threat Model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Spoofing | Điều dưỡng báo cáo sự cố giả lập để chiếm WO | Low | Medium | IR `reported_by` gắn session user; audit trail actor |
| Tampering — IR severity | Hạ severity từ Critical → Minor để tránh RCA | Low | High | `severity` field: sau Acknowledge chỉ Workshop Lead+ sửa được |
| Tampering — Audit | Sửa `IMM Audit Trail` DB | Low | Critical | DocPerm no-delete (IMM-00); verify chain endpoint |
| Repudiation | Phủ nhận đã Resolve IR | Low | High | `resolved_at` + actor + `IMM Audit Trail` hash |
| Info Disclosure | Điều dưỡng xem IR của khoa khác | Low | Medium | `permission_query_conditions` by department |
| DoS — Chronic detection | Scheduler quét 100k+ IR/run | Medium | Medium | Index `fault_code + asset + created_at`; batch 500/run |
| Elevation of Privilege | Reporting User tự Close CAPA | Low | High | DocPerm: CAPA Submit/Close chỉ IMM QA Officer |

## III.10. Penetration Test

⚠️ Pending — thực hiện trước release đầu tiên.
- Burp Suite scan trên `uat.assetcore.vn`.
- Role escalation: thử `report_incident` (Major, no clinical impact) → verify block.
- Chronic detection idempotent: thử kích hoạt lặp lại.
- CAPA close by Reporting User → 403.
- Report: `docs/security/pentest_imm12_v1.md`.

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
- [x] Test class structure cho 11 service functions (defined)
- [x] ≥ 1 happy + 1 negative test mỗi function (specified)
- [x] 7 workflow transitions đều có test (specified)
- [x] Audit chain test (intact + tampered) (specified)
- [x] API test ≥ 60% coverage target (specified — 13 test cases)
- [x] Performance target xác định (k6)
- [x] CI command xác định
- [x] SonarQube + Lighthouse target xác định
- [ ] Test files thực sự được tạo ⚠️ Pending implementation

### II. UAT
- [x] 10 UAT scenario, cover BR-12-01→07 + permission + audit + dashboard
- [x] Mọi User Story (US-12-01 → 06) có ≥ 1 UAT scenario
- [ ] Test data seed script: `uat_imm12.py` ⚠️ Pending
- [x] 5 Tester accounts + password documented
- [x] Sign-off section sẵn sàng
- [ ] UAT execution thực sự ⚠️ Pending implementation

### III. Security
- [x] DocPerm matrix đề xuất đầy đủ (Incident Report + RCA Record + CAPA)
- [x] Field-level permlevel xác định
- [x] Threat model 7 threat với mitigation
- [ ] Permission query code implement ⚠️ Pending
- [ ] Pentest report ⚠️ Pending
- [ ] Rate limit cấu hình (roadmap)
- [x] Vendor isolation policy documented
- [x] Audit trail immutability kế thừa IMM-00
- [x] Sign-off section sẵn sàng
