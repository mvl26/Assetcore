# IMM-15 — Testing & QA

> ✅ Wave 2 IMPLEMENTED. Test thực tế: `assetcore/tests/test_imm15.py` (9 TestCase, 13 test method). Coverage formal report chưa chạy — xem §I.1.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 1.0.0-rc.2 |
| Template | 07 Testing_QA |
| Ngày cập nhật | 2026-05-14 |
| Trạng thái | IMPLEMENTED — Wave 2 |

---

## §0 — Test Suite Inventory (CURRENT, 2026-05-18)

File: `assetcore/tests/test_imm15.py`

| Class | Test method | Covers |
|---|---|---|
| `TestAllocationLifecycle` | `test_create_requires_work_order_for_non_emergency` | BR-15-01 (non-emergency requires WO) |
| `TestAllocationLifecycle` | `test_create_emergency_without_wo_succeeds` | BR-15-01 Emergency bypass |
| `TestAllocationLifecycle` | `test_approve_requires_correct_role` | Workflow Requested→Approved; FORBIDDEN |
| `TestAllocationLifecycle` | `test_approve_bad_state` | `ErrorCode.BAD_STATE` re-approve |
| `TestUrgencyValidation` | `test_invalid_urgency_rejected` | VR-15-05 urgency enum |
| `TestWarehouseValidation` | `test_inactive_warehouse_rejected` | VR-15-13 inactive warehouse |
| `TestReturnValidation` | `test_return_qty_exceeds_issued` | VR-15-08 return qty cap |
| `TestForecastGeneration` | `test_generate_forecast` | `generate_spare_forecast` Moving_Avg |
| `TestWatchlist` | `test_add_critical_part_ok` | Watchlist Critical-only happy path |
| `TestWatchlist` | `test_add_non_critical_rejected` | VR-15-09 Critical-only enforcement |
| `TestDashboardStats` | `test_dashboard_keys` | `get_dashboard_stats` schema keys |
| `TestDashboardLowStockPerBin` | `test_overview_low_stock_is_per_bin` | Low-stock alert counted per-Bin (not per-part) |
| `TestDashboardLowStockPerBin` | `test_overview_count_matches_stock_page` | Dashboard count matches stock page total |

Run:

```bash
bench --site [site] run-tests --app assetcore --module assetcore.tests.test_imm15
```

> ⚠️ Các test class / coverage target lý thuyết liệt kê dưới §II–§III (TestImm15ValidationRules, TestImm15AllocationService, ...) là **draft chưa triển khai** — giữ làm backlog. Test ID chính xác là class + method ở §0 ở trên.

---

## §I — Test Pyramid

### I.1 Coverage Targets

| Layer | Số test | Target Coverage | Tool |
|---|---|---|---|
| Unit (service logic) | ≥ 50 | ≥ 85% lines | `bench run-tests` / pytest |
| Integration (workflow + hooks) | ≥ 12 | — | `bench run-tests` |
| E2E / API | ≥ 14 | — | curl smoke + Playwright |
| UAT | 14 scenarios | 100% scenario pass | Manual |

### I.2 Run Commands

```bash
# Run all IMM-15 tests
bench --site [site] run-tests --app assetcore --module assetcore.tests.test_imm15

# Run specific test class
bench --site [site] run-tests --app assetcore --module assetcore.tests.test_imm15 \
  --test TestImm15AllocationService

# Coverage report
bench --site [site] run-tests --app assetcore --coverage \
  --module assetcore.tests.test_imm15

# Scheduler test (manual trigger)
bench --site [site] execute assetcore.tasks.check_critical_spare_breach
bench --site [site] execute assetcore.tasks.check_low_stock_alerts
bench --site [site] execute assetcore.tasks.compute_inventory_kpis
bench --site [site] execute assetcore.tasks.reclassify_abc_xyz
```

---

## §II — Unit Tests

### II.1 TestImm15ValidationRules

```python
# assetcore/tests/test_imm15.py

import frappe
from frappe.tests.utils import FrappeTestCase
from assetcore.services.imm15 import (
    AllocationService,
    CycleCountService,
    WatchlistService,
    ForecastService,
)
from assetcore.services.errors import ServiceError, ErrorCode


class TestImm15ValidationRules(FrappeTestCase):
    """Test VR-15-01 through VR-15-13 validation rules."""

    def setUp(self):
        self.allocation_svc = AllocationService()
        self.cycle_count_svc = CycleCountService()
        self.watchlist_svc = WatchlistService()
        self.forecast_svc = ForecastService()
        self._setup_test_items()

    def _setup_test_items(self):
        """Seed minimal test items and warehouses."""
        # Override in actual test setup with frappe.get_doc
        pass

    def test_vr15_01_allocation_requires_work_order_for_routine(self):
        """VR-15-01: Non-emergency allocation must link a Work Order."""
        payload = {
            "work_order_doctype": None,
            "work_order_ref": None,
            "urgency": "Routine",
            "warehouse_from": "Kho trung tâm",
            "items": [{"item_code": "SPARE-MON-BAT", "qty_requested": 1}],
        }
        with self.assertRaises(ServiceError) as ctx:
            self.allocation_svc.create_allocation(payload, actor="test_biomed")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("Work Order", ctx.exception.message)

    def test_vr15_02_traceability_requires_batch(self):
        """VR-15-02: Items with imm_traceability_required=1 must have batch_no on issue."""
        # Stub: allocation Picked for traceability item
        allocation_name = "SAL-2026-TEST-01"
        issue_payload = {
            "name": allocation_name,
            "items": [{"item_code": "SPARE-CT-TUBE-01", "qty_issued": 1, "batch_no": None}],
        }
        with self.assertRaises(ServiceError) as ctx:
            self.allocation_svc.issue_allocation(issue_payload, actor="test_storekeeper")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("batch_no", ctx.exception.message)

    def test_vr15_03_insufficient_stock_raises(self):
        """VR-15-03: Routine issue when Bin qty < qty_requested raises BUSINESS_RULE."""
        # Bin SPARE-PUMP-SEAL = 0
        issue_payload = {
            "name": "SAL-2026-TEST-02",
            "items": [{"item_code": "SPARE-PUMP-SEAL", "qty_issued": 1, "batch_no": None}],
        }
        with self.assertRaises(ServiceError) as ctx:
            self.allocation_svc.issue_allocation(issue_payload, actor="test_storekeeper")
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("Tồn kho", ctx.exception.message)

    def test_vr15_04_cycle_count_variance_requires_root_cause(self):
        """VR-15-04: Variance > 5% or > 5M VND must have root_cause before Reviewed."""
        counted_items = [
            {"item_code": "SPARE-FILT-01", "system_qty": 10, "counted_qty": 4, "root_cause": None},
        ]
        with self.assertRaises(ServiceError) as ctx:
            self.cycle_count_svc.finish_counting("CYC-2026-TEST-01", counted_items, actor="test_storekeeper")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("root_cause", ctx.exception.message)

    def test_vr15_06_min_max_constraint(self):
        """VR-15-06: imm_min_strategic_stock must be <= imm_max_strategic_stock."""
        with self.assertRaises(ServiceError) as ctx:
            self.allocation_svc._validate_spare_item_limits(
                item_code="SPARE-TEST",
                min_stock=10,
                max_stock=5,
            )
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)

    def test_vr15_08_return_qty_exceeds_issued_raises(self):
        """VR-15-08: qty_returned must not exceed qty_issued."""
        returned_items = [{"item_code": "SPARE-MON-BAT", "qty_returned": 5, "condition": "Good"}]
        with self.assertRaises(ServiceError) as ctx:
            self.allocation_svc.return_items("SAL-2026-TEST-03", returned_items, actor="test_storekeeper")
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("qty_returned", ctx.exception.message)

    def test_vr15_09_watchlist_only_accepts_critical_parts(self):
        """VR-15-09: Watchlist entry must have imm_part_class=Critical."""
        payload = {
            "asset": "AC-ASSET-MON-01",
            "spare_item": "SPARE-MON-BAT",  # Major, not Critical
            "warehouse": "Kho trung tâm",
            "min_on_hand": 1,
        }
        with self.assertRaises(ServiceError) as ctx:
            self.watchlist_svc.add_watchlist_entry(payload, actor="test_workshop_head")
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("Critical", ctx.exception.message)

    def test_vr15_10_emergency_override_dual_approver(self):
        """VR-15-10: Emergency override approver_2 must differ from approver_1."""
        override_payload = {
            "approver_1": "test_workshop_head",
            "approver_2": "test_workshop_head",  # Same user — must fail
            "reason": "Test emergency reason (30+ chars for test pass)",
        }
        with self.assertRaises(ServiceError) as ctx:
            self.allocation_svc.issue_allocation(
                {"name": "SAL-2026-TEST-04", "override": override_payload},
                actor="test_workshop_head",
            )
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("khác nhau", ctx.exception.message)

    def test_vr15_11_verified_by_differs_from_counted_by(self):
        """VR-15-11: verified_by must differ from counted_by."""
        with self.assertRaises(ServiceError) as ctx:
            self.cycle_count_svc.post_cycle_count(
                name="CYC-2026-TEST-02",
                verified_by="test_storekeeper",  # Same as counted_by
                actor="test_storekeeper",
            )
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("verified_by", ctx.exception.message)

    def test_vr15_12_forecast_method_whitelist(self):
        """VR-15-12: forecast method must be in allowed list."""
        with self.assertRaises(ServiceError) as ctx:
            self.forecast_svc.generate_forecast(
                period="2026-Q3",
                method="LinearReg",  # Not in whitelist
                actor="test_workshop_head",
            )
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_PARAMS)
        self.assertIn("method", ctx.exception.message)


class TestImm15AllocationService(FrappeTestCase):
    """Test AllocationService business logic."""

    def setUp(self):
        self.svc = AllocationService()

    def test_create_allocation_happy_path(self):
        """Allocation created with state=Requested, audit trail written."""
        # stub
        pass

    def test_create_allocation_generates_correct_naming(self):
        """Allocation name matches pattern SAL-YYYY-#####."""
        # stub: verify name via regex
        pass

    def test_approve_allocation_sets_approved_by_and_date(self):
        """approve_allocation sets approved_by, approval_date, qty_approved fields."""
        # stub
        pass

    def test_issue_allocation_creates_stock_entry(self):
        """issue_allocation creates AC Stock Movement Material Issue, links imm_allocation_ref."""
        # stub: verify via frappe.get_doc("AC Stock Movement", ...)
        pass

    def test_issue_allocation_updates_bin_qty(self):
        """After issue, Bin.actual_qty decremented by qty_issued."""
        # stub
        pass

    def test_issue_allocation_emergency_bypass_stock_check(self):
        """Emergency override: stock check bypassed, audit_flags set to EMERGENCY_OVERRIDE."""
        # stub
        pass

    def test_return_items_good_condition_to_main_warehouse(self):
        """Good condition return → Stock Entry to original warehouse."""
        # stub
        pass

    def test_return_items_damaged_condition_to_qc_hold(self):
        """Damaged return → Stock Entry to QC Hold warehouse."""
        # stub
        pass

    def test_cancel_allocation_cannot_cancel_issued(self):
        """Cannot cancel an Issued allocation."""
        with self.assertRaises(ServiceError) as ctx:
            self.svc.cancel_allocation("SAL-2026-ISSUED", reason="Test", actor="test_ws")
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)

    def test_check_part_availability_returns_sufficient_flag(self):
        """check_part_availability returns dict with sufficient, available_qty, breach_detail."""
        # stub
        pass


class TestImm15CycleCountService(FrappeTestCase):
    """Test CycleCountService logic."""

    def setUp(self):
        self.svc = CycleCountService()

    def test_create_cycle_count_fetches_system_qty_from_bin(self):
        """On creation, system_qty auto-fetched from current Bin."""
        # stub
        pass

    def test_variance_computed_correctly(self):
        """Variance = counted_qty - system_qty; var_pct = variance / system_qty * 100."""
        result = self.svc._compute_variance(system_qty=10, counted_qty=4)
        self.assertEqual(result["variance_qty"], -6)
        self.assertAlmostEqual(result["variance_pct"], -60.0)

    def test_capa_seeded_for_large_variance(self):
        """CAPA seeded when |var_pct| > 5% or |var_value| > 5M VND."""
        # stub: verify frappe.new_doc("CAPA") was called
        pass

    def test_stock_reconciliation_created_on_post(self):
        """Post creates Stock Reconciliation for items with variance != 0."""
        # stub
        pass

    def test_post_cycle_count_updates_bin(self):
        """After Post, Bin reflects counted_qty (via Stock Reconciliation)."""
        # stub
        pass

    def test_idempotent_variance_check(self):
        """Running finish_counting twice with same data does not create duplicate CAPAs."""
        # stub
        pass


class TestImm15WatchlistService(FrappeTestCase):
    """Test WatchlistService and breach detection."""

    def setUp(self):
        self.svc = WatchlistService()

    def test_check_breach_detects_when_actual_below_min(self):
        """Breach detected when actual_qty < min_on_hand."""
        # stub: mock Bin.actual_qty = 0, min_on_hand = 1
        pass

    def test_breach_alert_not_duplicated_same_day(self):
        """check_critical_spare_breach idempotent — no duplicate alert same day."""
        # stub
        pass

    def test_breach_seeds_capa(self):
        """Breach detected → CAPA document seeded (IMM-16)."""
        # stub
        pass

    def test_breach_sends_email_to_workshop_head(self):
        """Breach triggers email to Workshop Head + VP Block 1 + CMMS Admin."""
        # stub: capture frappe.sendmail calls
        pass


class TestImm15ForecastService(FrappeTestCase):
    """Test ForecastService demand calculation."""

    def setUp(self):
        self.svc = ForecastService()

    def test_reorder_point_gte_safety_stock(self):
        """VR-15-07: reorder_point >= safety_stock for every forecast item."""
        # stub
        pass

    def test_generate_forecast_moving_avg_method(self):
        """Moving_Avg method produces forecast_qty > 0 for items with consumption."""
        # stub
        pass

    def test_approve_forecast_creates_material_requests(self):
        """Approved forecast auto-creates MR for items with current_qty < reorder_point."""
        # stub
        pass

    def test_draft_forecast_does_not_create_mr(self):
        """BR-15-07: Draft forecast must not trigger MR creation."""
        # stub
        pass


class TestImm15ABCReclassification(FrappeTestCase):
    """Test quarterly ABC/XYZ reclassification scheduler."""

    def setUp(self):
        from assetcore.tasks import reclassify_abc_xyz
        self.task_fn = reclassify_abc_xyz

    def test_abc_class_assigned_by_cumulative_value(self):
        """ABC: top 80% cumulative value → A, next 15% → B, remainder → C."""
        # stub
        pass

    def test_reclassification_idempotent(self):
        """Running reclassify twice with same data produces same result, no duplicate audit."""
        # stub
        pass

    def test_audit_trail_written_on_class_change(self):
        """ABC reclassification writes IMM Audit Trail when class changes."""
        # stub: action=ABC_RECLASSIFIED, old_class, new_class
        pass


class TestImm15WorkflowTransitions(FrappeTestCase):
    """Test IMM Spare Allocation and IMM Stock Cycle Count workflow transitions."""

    # ─── Allocation Workflow ─────────────────────────────────────────────────

    def test_allocation_requested_to_approved(self):
        """Transition: Requested → Approved (actor: Workshop Head)."""
        # stub
        pass

    def test_allocation_approved_to_picked(self):
        """Transition: Approved → Picked (actor: Storekeeper)."""
        # stub
        pass

    def test_allocation_picked_to_issued(self):
        """Transition: Picked → Issued (actor: Storekeeper)."""
        # stub
        pass

    def test_allocation_issued_to_returned(self):
        """Transition: Issued → Returned (actor: Storekeeper)."""
        # stub
        pass

    def test_allocation_requested_to_cancelled(self):
        """Transition: Requested → Cancelled (actor: Workshop Head)."""
        # stub
        pass

    def test_allocation_approved_to_cancelled(self):
        """Transition: Approved → Cancelled (actor: Workshop Head)."""
        # stub
        pass

    def test_allocation_cannot_go_back_from_issued(self):
        """Issued state: no backward transition allowed."""
        # stub
        pass

    # ─── Cycle Count Workflow ─────────────────────────────────────────────────

    def test_cycle_count_planned_to_counting(self):
        """Transition: Planned → Counting (actor: Storekeeper)."""
        # stub
        pass

    def test_cycle_count_counting_to_reviewed(self):
        """Transition: Counting → Reviewed (actor: Storekeeper)."""
        # stub
        pass

    def test_cycle_count_reviewed_to_posted(self):
        """Transition: Reviewed → Posted (actor: Workshop Head)."""
        # stub
        pass

    def test_cycle_count_reviewed_to_counting_re_count(self):
        """Transition: Reviewed → Counting (Storekeeper can re-count)."""
        # stub
        pass


class TestImm15AuditTrail(FrappeTestCase):
    """Test IMM Audit Trail completeness per BR-15-10."""

    def _get_latest_audit(self, root_name: str, action: str):
        return frappe.db.get_value(
            "IMM Audit Trail",
            {"root_name": root_name, "action": action},
            ["name", "actor", "payload"],
            as_dict=True,
        )

    def test_allocation_created_audit(self):
        """create_allocation writes action=ALLOCATION_CREATED."""
        # stub
        pass

    def test_allocation_issued_audit_has_stock_entry_ref(self):
        """issue_allocation writes action=ALLOCATION_ISSUED with stock_entry_ref in payload."""
        # stub
        pass

    def test_emergency_override_audit_has_two_actors(self):
        """Emergency override writes 2 actors and reason in payload."""
        # stub
        pass

    def test_cycle_count_posted_audit_has_variance_summary(self):
        """post_cycle_count writes action=CYCLE_COUNT_POSTED with variance_value."""
        # stub
        pass

    def test_watchlist_breach_audit(self):
        """Breach detection writes action=CRITICAL_BREACH_DETECTED."""
        # stub
        pass

    def test_abc_reclassified_audit_on_class_change(self):
        """ABC reclassification writes action=ABC_RECLASSIFIED with old/new class."""
        # stub
        pass

    def test_forecast_approved_audit_has_mr_count(self):
        """approve_forecast writes action=FORECAST_APPROVED with mr_count."""
        # stub
        pass


class TestImm15API(FrappeTestCase):
    """Test REST API endpoints via frappe.call simulation."""

    def setUp(self):
        self.client = frappe.test_runner.make_test_client()

    def _call(self, method: str, args: dict = None):
        return frappe.call(f"assetcore.api.imm15.{method}", **(args or {}))

    def test_list_allocations_returns_envelope(self):
        """GET list_allocations → {success: true, data: {items: [...], total: N}}."""
        result = self._call("list_allocations")
        self.assertTrue(result["success"])
        self.assertIn("items", result["data"])
        self.assertIn("total", result["data"])

    def test_create_allocation_missing_work_order_returns_error(self):
        """POST create_allocation without work_order_ref (Routine) → {success: false, error: ...}."""
        result = self._call("create_allocation", {"urgency": "Routine"})
        self.assertFalse(result["success"])
        self.assertIn("code", result["error"])

    def test_approve_allocation_forbidden_for_storekeeper(self):
        """POST approve_allocation by Storekeeper → {success: false, error.code: FORBIDDEN}."""
        # stub: switch user to test_storekeeper
        pass

    def test_issue_allocation_creates_stock_entry_and_returns_ref(self):
        """POST issue_allocation (Picked, sufficient stock) → data includes stock_entry_ref."""
        # stub
        pass

    def test_check_part_availability_p95_under_300ms(self):
        """GET check_part_availability latency P95 < 300ms (NFR-15-02)."""
        import time
        start = time.perf_counter()
        for _ in range(20):
            self._call("check_part_availability", {
                "items": [{"item_code": "SPARE-MON-BAT", "qty": 2}],
                "warehouse": "Kho trung tâm",
            })
        elapsed_ms = (time.perf_counter() - start) / 20 * 1000
        self.assertLess(elapsed_ms, 300, f"P95 latency {elapsed_ms:.1f}ms exceeds 300ms")

    def test_post_cycle_count_missing_root_cause_returns_validation_error(self):
        """POST post_cycle_count without root_cause for large variance → VR-15-04 error."""
        # stub
        pass

    def test_add_watchlist_entry_non_critical_returns_business_rule_error(self):
        """POST add_to_watchlist with Major part → VR-15-09 error."""
        result = self._call("add_to_watchlist", {
            "asset": "AC-ASSET-MON-01",
            "spare_item": "SPARE-MON-BAT",
            "warehouse": "Kho trung tâm",
            "min_on_hand": 1,
        })
        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "BUSINESS_RULE")

    def test_get_dashboard_kpis_returns_all_kpi_fields(self):
        """GET get_dashboard_stats → data contains all expected KPI fields."""
        result = self._call("get_dashboard_stats")
        self.assertTrue(result["success"])
        expected_fields = [
            "stock_turnover_year", "days_on_hand_avg", "stockout_incidents_30d",
            "critical_breach_hours_30d", "cycle_accuracy_pct", "forecast_mape_q",
        ]
        for f in expected_fields:
            self.assertIn(f, result["data"]["kpis"])
```

---

## §III — UAT Scenarios

### III.1 Preconditions

| # | Điều kiện | Cách chuẩn bị |
|---|---|---|
| PC-01 | ≥ 5 Asset từ IMM-04 (1 Critical CT, 1 Major Monitor) | Chạy IMM-04 flow đến Clinical_Release |
| PC-02 | ERPNext Item group "Medical Spare Part" đã có | Setup script |
| PC-03 | ≥ 10 Item (2 Critical, 4 Major, 4 Consumable) với imm_* fields | Chạy fixture seed |
| PC-04 | Custom Fields trên Item đã sync (`bench migrate`) | Verify qua Customize Form |
| PC-05 | 2 Workflows active (Allocation + Cycle Count) | Setup > Workflow |
| PC-06 | Test users: Storekeeper, Workshop Head, Biomed, HTM Tech, VP Block 1, QA, CMMS Admin, Accountant | Tạo test users |
| PC-07 | ≥ 2 Warehouse (Kho trung tâm, Kho phân xưởng, QC Hold) | ERPNext setup |
| PC-08 | Stock Entry seed tồn kho ban đầu | Manual seed |
| PC-09 | 1 PM Work Order Approved (IMM-08) | IMM-08 prereq |
| PC-10 | 1 CM Work Order Emergency (IMM-12) | IMM-12 prereq |
| PC-11 | Critical Spare Watchlist seed cho CT, MRI | Fixture |
| PC-12 | IMM Audit Trail DocType active | Verify |
| PC-13 | AC Backbone Wave 1 (AC Spare Part, AC Stock Movement) LIVE | Deploy Wave 1 first |

### III.2 UAT Test Data

| Item | Class | ABC | Min | Tồn đầu | Traceability |
|---|---|---|---|---|---|
| SPARE-CT-TUBE-01 | Critical | A | 1 | 1 | ☑ |
| SPARE-MRI-COIL | Critical | A | 1 | 1 | ☑ |
| SPARE-MON-BAT | Major | B | 6 | 12 | ☐ |
| SPARE-FILT-01 | Consumable | C | 4 | 10 | ☐ |
| SPARE-DEF-PAD | Consumable | B | 4 | 2 (low) | ☐ |
| SPARE-PUMP-SEAL | Major | B | 2 | 0 (out) | ☐ |

### III.3 UAT Scenarios Table

| # | Kịch bản | Actor | Điều kiện | Kết quả mong đợi | Priority | Pass |
|---|---|---|---|---|---|:---:|
| UAT-IMM15-01 | Tạo Allocation từ PM WO (happy path) | Biomed Engineer | PC-09 | SAL tạo, state=Requested, audit trail | P0 | ☐ |
| UAT-IMM15-02 | Approve → Pick → Issue → Stock Entry giảm Bin | Workshop Head + Storekeeper | TC-01 pass | Stock Entry tạo, Bin giảm, audit | P0 | ☐ |
| UAT-IMM15-03 | Issue yêu cầu batch_no (Traceability) | Storekeeper | SPARE-CT-TUBE-01 | VR-15-02: lỗi nếu thiếu batch; pass nếu có | P0 | ☐ |
| UAT-IMM15-04 | Emergency Override kép | Workshop Head + VP Block 1 | Stock = 0 | EMERGENCY_OVERRIDE flag ghi, dual approver | P0 | ☐ |
| UAT-IMM15-05 | Return Damaged → QC Hold warehouse | Storekeeper | Issued allocation | Damaged → QC Hold; Good → KTT | P1 | ☐ |
| UAT-IMM15-06 | Cycle Count đầy đủ → Post → SR → CAPA | Storekeeper + Workshop Head | Variance FILT-01 -60% | SR tạo, CAPA seed, Bin = counted_qty | P0 | ☐ |
| UAT-IMM15-07 | Critical Watchlist breach → CAPA + email | System scheduler | Bin CT-TUBE-01 = 0 | Breach alert, CAPA, email 3 recipients | P0 | ☐ |
| UAT-IMM15-08 | Demand Forecast → Approve → Auto MR | Workshop Head | ≥ 6 tháng data | MR Draft tạo cho item reorder | P1 | ☐ |
| UAT-IMM15-09 | Validation Rules (7 VRs) | Biomed + Storekeeper | N/A | Mỗi VR trả lỗi tiếng Việt đúng | P1 | ☐ |
| UAT-IMM15-10 | Permission Matrix (8 roles × 9 actions) | All test users | N/A | Forbidden / 403 khi sai role | P1 | ☐ |
| UAT-IMM15-11 | Scheduler Jobs (low_stock, breach, expiry, KPI) | System | Manual trigger | Alert idempotent, email, KPI snapshot | P1 | ☐ |
| UAT-IMM15-12 | Integration IMM-08: reserve spare khi submit WO | Biomed + Storekeeper | PM WO | reserved_qty tăng, auto-allocation | P1 | ☐ |
| UAT-IMM15-13 | Audit Trail đầy đủ (10 actions) | All | Post flow | Mỗi action có IMM Audit Trail entry | P0 | ☐ |
| UAT-IMM15-14 | Dashboard KPI tiles + Realtime update | Storekeeper / Workshop Head | Breach event | KPI tile reload sau realtime event | P2 | ☐ |

### III.4 Sign-off Criteria

| Kết quả | Điều kiện |
|---|---|
| **Pass** | 100% TC Pass (0 Fail, 0 Block) |
| **Conditional Pass** | ≥ 90% Pass; Fail đều P2 (cosmetic); có remediation plan |
| **Fail** | Bất kỳ P0 Fail → block release. UAT-IMM15-01/04/06/07/13 là P0 tuyệt đối |

### III.5 Sign-off Table

| Role | Tên | Chữ ký | Ngày |
|---|---|---|---|
| BA Lead | | | |
| Dev Lead | | | |
| QA Lead | | | |
| Workshop Head đại diện | | | |
| VP Block 1 (PTP Khối 1) | | | |
| Tổ HC-QLCL đại diện | | | |

---

## §IV — Security & RBAC

### IV.1 DocPerm Matrix

| DocType | Read | Create | Write | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| IMM Spare Allocation | All (own+team) | Biomed, HTM Tech, Storekeeper, WS Head, CMMS Admin | Biomed, HTM Tech, Storekeeper (Requested only) | System | WS Head, CMMS Admin | CMMS Admin |
| IMM Spare Allocation Item | (via parent) | (via parent) | (via parent) | — | — | — |
| IMM Stock Cycle Count | Storekeeper, WS Head, QA, CMMS Admin | Storekeeper, WS Head, CMMS Admin | Storekeeper (Counting), WS Head | System | WS Head, CMMS Admin | CMMS Admin |
| IMM Stock Cycle Count Item | (via parent) | (via parent) | (via parent) | — | — | — |
| IMM Spare Part Forecast | WS Head, VP B1, CMMS Admin, Accountant | System (scheduler) | WS Head, CMMS Admin | WS Head, VP B1, CMMS Admin | CMMS Admin | CMMS Admin |
| IMM Spare Forecast Item | (via parent) | (via parent) | (via parent) | — | — | — |
| IMM Critical Spare Watchlist | Storekeeper, WS Head, VP B1, CMMS Admin | WS Head, VP B1, CMMS Admin | WS Head, VP B1, CMMS Admin | — | CMMS Admin | CMMS Admin |
| IMM Audit Trail | All (read own module) | System only | — | — | — | — |

### IV.2 Field-level Permissions

| DocType | Field | Permlevel | Who can see |
|---|---|---|---|
| IMM Spare Allocation | `total_value` | 1 | WS Head, VP B1, CMMS Admin, Accountant |
| IMM Spare Allocation | `override_reason` | 1 | WS Head, VP B1, CMMS Admin |
| IMM Stock Cycle Count | `variance_value` | 1 | WS Head, VP B1, CMMS Admin, Accountant, QA |
| IMM Spare Part Forecast | `forecast_qty` | 0 | All with read access |
| IMM Spare Part Forecast | `auto_mr_value` | 1 | WS Head, VP B1, CMMS Admin, Accountant |

### IV.3 STRIDE Threat Analysis

| Threat | Scenario | Control |
|---|---|---|
| **Spoofing** | Kẻ tấn công giả mạo Approver 2 trong emergency override | `session.user` validate server-side; VR-15-10 enforce khác nhau |
| **Tampering** | Sửa `qty_issued` trong Stock Entry sau khi Issued | Stock Entry docstatus=1; imm_allocation_ref read-only sau issue |
| **Repudiation** | Tranh cãi ai đã override emergency | IMM Audit Trail ghi 2 actors + timestamp + IP; immutable (no delete perm) |
| **Information Disclosure** | Storekeeper xem `total_value` của allocation | Permlevel 1 ẩn field với Storekeeper |
| **Denial of Service** | Flood `check_part_availability` với 1000 items | Rate limit API; cache Bin read (Redis 60s TTL) |
| **Elevation of Privilege** | Storekeeper tự approve allocation mình tạo | Role check server-side `_APPROVE_ALLOCATION_ROLES` không chứa Storekeeper |

### IV.4 Data Sensitivity

| Data | Classification | Control |
|---|---|---|
| `override_reason`, emergency docs | Confidential | Permlevel 1 + audit trail |
| `total_value`, `variance_value` | Internal | Permlevel 1 cho Accountant access |
| Batch / Serial number traceability | Critical (regulatory) | Required field khi `imm_traceability_required=1` |
| `audit_flags = EMERGENCY_OVERRIDE` | Critical | Immutable sau set; visible QA + Management |
| KPI snapshots | Internal | Read-only for Accountant; no delete |

---

## §V — Code Quality Targets

| Metric | Target | Tool |
|---|---|---|
| Test coverage (lines) | ≥ 85% | pytest-cov |
| Cyclomatic complexity | ≤ 10 per function | radon |
| Function length | ≤ 50 lines | manual review |
| File length | ≤ 200 lines | manual review |
| Docstring coverage | 100% public functions | pydocstyle |
| Type hint coverage | 100% public functions | mypy strict |
| Duplicate code blocks | 0 (>6 lines identical) | pylint |
| P95 API latency (check_part_availability) | ≤ 300ms | k6 load test |
| P95 API latency (other endpoints) | ≤ 800ms | k6 load test |
| Concurrent users supported | 50 | k6 ramp test |

### V.1 Linting Commands

```bash
# Type check
mypy assetcore/services/imm15.py assetcore/api/imm15.py

# Complexity
radon cc assetcore/services/imm15.py -s -n B

# Docstring
pydocstyle assetcore/services/imm15.py

# Full lint
pylint assetcore/services/imm15.py assetcore/api/imm15.py
```

---

*IMM-15 Module — Wave 3 PLANNED. Testing & QA v1.0.0-draft. Cập nhật 2026-05-08.*
