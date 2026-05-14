# 07 — Testing & QA — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. Backend và Frontend đã triển khai.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày | 2026-05-14 |
| Trạng thái | LIVE — Wave 2 (unit tests planted; integration/UAT planned) |

---

## I. Test Plan

### I.1 Test Pyramid

```
           /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
          /   E2E / UAT (12)     \    ← Playwright / manual UAT
         /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
        /  Integration (8)        \   ← Full flow Eval→Decision→PO
       /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
      /   Unit (≥ 40)              \  ← 7 VR + 5 Gate + scoring + scheduler
     ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
```

**Coverage target:** ≥ 85% (lines), 100% các VR + Gate.

---

### I.2 Unit Tests — Implemented vs Planned

**File ground truth:** `assetcore/tests/test_imm03.py` — chứa 5 class actual (pure-Python, KHÔNG mở DB):

| Class | Methods | Mô tả |
|---|---|---|
| `TestParseWeighting` | `test_none_returns_defaults`, `test_dict_passthrough`, `test_valid_json_parsed`, `test_invalid_json_returns_defaults` | Helper `_parse_weighting` |
| `TestParseJsonField` | `test_none_returns_empty_dict`, `test_dict_passthrough`, `test_valid_json_string`, `test_invalid_json_returns_empty` | Helper `_parse_json_field` |
| `TestComputeEvalScores` | `test_higher_score_candidate_wins`, `test_unknown_criterion_ignored`, `test_empty_candidates_no_recommended` | `_compute_eval_scores` + `recommended_candidate = top supplier name` |
| `TestGateG04Method` | `test_draft_state_skips_check`, `test_chi_dinh_thau_exceeds_limit_raises`, `test_chi_dinh_thau_within_limit_but_no_legal_basis_raises`, `test_chao_hang_within_limit_and_legal_basis_passes`, `test_unknown_method_skips`, `test_no_method_skips` | `_validate_gate_g04_method` |
| `TestMethodRules` | `test_chi_dinh_thau_limit_is_50m`, `test_chao_hang_canh_tranh_limit_is_1b`, `test_dau_thau_rong_rai_has_no_price_cap` | Hằng số `_METHOD_RULES` |

**Planned (chưa viết):** VR-03-03 quotation validity, VR-03-04 envelope, VR-03-05 winner AVL, VR-03-07 unique decision per spec, G05, mint AC Purchase integration, AVL expiry scheduler, scorecard idempotency. Các stub dưới đây là **roadmap**, không phải code hiện hữu.

### I.2.a Test Stub Roadmap (chưa implement)

```python
import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from assetcore.services.shared import ServiceError, ErrorCode


class TestImm03ValidationRules(FrappeTestCase):
    """Unit tests cho 7 VR của IMM-03."""

    def setUp(self):
        """Tạo test data: AC Supplier, AVL Entry, IMM Tech Spec."""
        self.supplier_avl = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": "Test Vinamed",
            "imm_avl_status": "Approved",
        }).insert(ignore_permissions=True)

        self.supplier_non_avl = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": "Test Hamilton",
            "imm_avl_status": "Not Applicable",
        }).insert(ignore_permissions=True)

        self.avl_entry = frappe.get_doc({
            "doctype": "IMM AVL Entry",
            "supplier": self.supplier_avl.name,
            "device_category": "Imaging",
            "validity_years": 2,
            "valid_from": frappe.utils.today(),
            "status": "Approved",
        }).insert(ignore_permissions=True)

    def test_vr01_not_enough_candidates_for_open_tender(self):
        """VR-03-01: Đấu thầu rộng rãi cần ≥ 3 candidate."""
        from assetcore.services.imm03 import _vr01_min_candidates
        doc = frappe.get_doc({
            "doctype": "IMM Vendor Evaluation",
            "candidates": [
                {"supplier": self.supplier_avl.name},
                {"supplier": self.supplier_non_avl.name},
            ],
        })
        doc.procurement_method = "Đấu thầu rộng rãi"
        with self.assertRaises(ServiceError) as ctx:
            _vr01_min_candidates(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("VR-03-01", str(ctx.exception))

    def test_vr01_single_candidate_ok_for_direct_award(self):
        """VR-03-01: Chỉ định thầu cho phép = 1 candidate."""
        from assetcore.services.imm03 import _vr01_min_candidates
        doc = frappe.get_doc({
            "doctype": "IMM Vendor Evaluation",
            "candidates": [{"supplier": self.supplier_avl.name}],
        })
        doc.procurement_method = "Chỉ định thầu"
        # Không raise là pass
        _vr01_min_candidates(doc)

    def test_vr02_non_avl_vendor_requires_sign_off_at_submit(self):
        """VR-03-02: Non-AVL vendor phải có sign_off_non_avl."""
        from assetcore.services.imm03 import _vr02_avl_check
        doc = frappe.get_doc({"doctype": "IMM Vendor Evaluation"})
        doc.candidates = [
            frappe._dict(supplier=self.supplier_non_avl.name, in_avl=False, sign_off_non_avl=None),
        ]
        doc.docstatus = 0  # simulate submitting
        with self.assertRaises(ServiceError) as ctx:
            _vr02_avl_check(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("VR-03-02", str(ctx.exception))

    def test_vr03_expired_quotation_raises(self):
        """VR-03-03: Quotation hết hạn không được submit."""
        from assetcore.services.imm03 import _vr03_quotation_validity
        import datetime
        doc = frappe.get_doc({"doctype": "IMM Vendor Evaluation"})
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        doc.quotations = [
            frappe._dict(quotation_no="QT-001", quotation_validity=yesterday),
        ]
        with self.assertRaises(ServiceError) as ctx:
            _vr03_quotation_validity(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("VR-03-03", str(ctx.exception))

    def test_vr04_price_over_105pct_envelope_raises(self):
        """VR-03-04: Awarded > 105% envelope → conflict."""
        from assetcore.services.imm03 import _vr04_decision_within_envelope
        doc = frappe.get_doc({
            "doctype": "IMM Procurement Decision",
            "awarded_price": 2_700_000_000,
            "plan_ref": "PP-26-001",
            "plan_line": "line001",
        })
        # Stub plan line allocated_budget = 2,500,000,000
        with self.assertRaises(ServiceError) as ctx:
            _vr04_decision_within_envelope(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.CONFLICT)
        self.assertIn("VR-03-04", str(ctx.exception))

    def test_vr05_winner_without_avl_active_raises(self):
        """VR-03-05: Winner phải có AVL Active."""
        from assetcore.services.imm03 import _vr05_avl_active_required
        doc = frappe.get_doc({
            "doctype": "IMM Procurement Decision",
            "awarded_vendor": self.supplier_non_avl.name,
            "spec_ref": "TS-26-00045",
        })
        # spec device_category = "Imaging", supplier_non_avl có AVL Not Applicable
        with self.assertRaises(ServiceError) as ctx:
            _vr05_avl_active_required(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("VR-03-05", str(ctx.exception))

    def test_vr07_duplicate_decision_per_spec_raises(self):
        """VR-03-07: 1 Tech Spec ↔ 1 Decision Awarded."""
        from assetcore.services.imm03 import _vr07_unique_decision_per_spec
        # Create awarded decision for spec
        existing = frappe.get_doc({
            "doctype": "IMM Procurement Decision",
            "spec_ref": "TS-26-00045",
            "docstatus": 1,
            "workflow_state": "Awarded",
        }).insert(ignore_permissions=True)
        doc = frappe.get_doc({
            "doctype": "IMM Procurement Decision",
            "spec_ref": "TS-26-00045",
            "docstatus": 0,
        })
        with self.assertRaises(ServiceError) as ctx:
            _vr07_unique_decision_per_spec(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.DUPLICATE)
        self.assertIn("VR-03-07", str(ctx.exception))

    def tearDown(self):
        frappe.db.rollback()


class TestImm03GateChecks(FrappeTestCase):
    """Unit tests cho 5 Gate của IMM-03."""

    def test_gate_g01_missing_compliance_scoring(self):
        """G01: Fail nếu chưa chấm điểm nhóm Compliance."""
        from assetcore.services.imm03 import _validate_gate_g01
        doc = frappe.get_doc({"doctype": "IMM Vendor Evaluation"})
        doc.criteria = [
            frappe._dict(group="Technical", criterion="Spec match"),
            frappe._dict(group="Compliance", criterion="ISO cert"),
        ]
        doc.candidates = [
            frappe._dict(name="c1", scores={"Spec match": 4}),
            # Missing Compliance score
        ]
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g01(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("G01", str(ctx.exception))

    def test_gate_g02_no_valid_quotation_raises(self):
        """G02: Fail nếu không có quotation hợp lệ."""
        from assetcore.services.imm03 import _validate_gate_g02
        doc = frappe.get_doc({"doctype": "IMM Vendor Evaluation"})
        doc.quotations = []
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g02(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("G02", str(ctx.exception))

    def test_gate_g04_direct_award_above_threshold_raises(self):
        """G04: Chỉ định thầu vượt ngưỡng NĐ."""
        from assetcore.services.imm03 import _validate_gate_g04
        doc = frappe.get_doc({
            "doctype": "IMM Procurement Decision",
            "procurement_method": "Chỉ định thầu",
            "awarded_price": 200_000_000,  # > 50M threshold
        })
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g04(doc)
        self.assertIn("G04", str(ctx.exception))

    def test_gate_g05_missing_contract_doc_raises(self):
        """G05: Fail nếu thiếu contract_doc."""
        from assetcore.services.imm03 import _validate_gate_g05
        doc = frappe.get_doc({
            "doctype": "IMM Procurement Decision",
            "funding_source": "NSNN",
            "board_approver": "vp@hospital.vn",
            "contract_doc": None,  # thiếu
        })
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g05(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("G05", str(ctx.exception))

    def tearDown(self):
        frappe.db.rollback()


class TestImm03ScoringAlgorithm(FrappeTestCase):
    """Unit tests cho thuật toán compute_eval_score."""

    def test_compute_eval_score_correct_weighted_sum(self):
        """compute_eval_score tính đúng weighted_score."""
        from assetcore.services.imm03 import compute_eval_score
        doc = frappe.get_doc({"doctype": "IMM Vendor Evaluation"})
        doc.weighting_scheme = {"Technical": 35, "Commercial": 25, "Financial": 10, "Support": 15, "Compliance": 15}
        doc.criteria = [
            frappe._dict(group="Technical", criterion="Spec match", weight_pct=100),
        ]
        doc.candidates = [
            frappe._dict(name="c1", scores={"Spec match": 4}),
            frappe._dict(name="c2", scores={"Spec match": 5}),
        ]
        compute_eval_score(doc)
        # Technical 35% × criterion 100% × score 4 = 1.4
        self.assertAlmostEqual(doc.candidates[0].weighted_score, 1.4, places=2)
        # top candidate = c2
        self.assertEqual(doc.recommended_candidate, "c2")

    def test_compute_eval_score_sorts_descending(self):
        """compute_eval_score sort candidates desc by weighted_score."""
        from assetcore.services.imm03 import compute_eval_score
        doc = frappe.get_doc({"doctype": "IMM Vendor Evaluation"})
        doc.weighting_scheme = {"Technical": 100}
        doc.criteria = [frappe._dict(group="Technical", criterion="X", weight_pct=100)]
        doc.candidates = [
            frappe._dict(name="low", scores={"X": 2}),
            frappe._dict(name="high", scores={"X": 5}),
        ]
        compute_eval_score(doc)
        self.assertEqual(doc.candidates[0].name, "high")

    def tearDown(self):
        frappe.db.rollback()


class TestImm03ScorecardScheduler(FrappeTestCase):
    """Unit tests cho Vendor Scorecard idempotency."""

    def test_update_vendor_scorecard_idempotent(self):
        """Re-run cùng (year, quarter, vendor) không tạo duplicate."""
        from assetcore.services.imm03 import update_vendor_scorecard
        vendor = "VINAMED"
        period = {"year": 2026, "quarter": 2}
        update_vendor_scorecard(vendor=vendor, period=period)
        count_before = frappe.db.count(
            "IMM Vendor Scorecard",
            {"period_year": 2026, "period_quarter": 2, "supplier": vendor}
        )
        update_vendor_scorecard(vendor=vendor, period=period)  # re-run
        count_after = frappe.db.count(
            "IMM Vendor Scorecard",
            {"period_year": 2026, "period_quarter": 2, "supplier": vendor}
        )
        self.assertEqual(count_before, count_after)

    def tearDown(self):
        frappe.db.rollback()


class TestImm03AcPurchaseGate(FrappeTestCase):
    """Unit test VR-03-08: AC Purchase TBYT phải qua Decision."""

    def test_direct_ac_purchase_tbyt_raises(self):
        """AC Purchase thiết bị y tế không có imm_procurement_decision → throw."""
        from assetcore.services.imm03 import validate_ac_purchase_imm_link
        po = frappe.get_doc({
            "doctype": "AC Purchase",
            "imm_procurement_decision": None,
            "items": [{"asset_category": "Imaging"}],  # HTM category
        })
        with self.assertRaises(ServiceError) as ctx:
            validate_ac_purchase_imm_link(po)
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("VR-03-08", str(ctx.exception))

    def tearDown(self):
        frappe.db.rollback()
```

---

### I.3 Workflow Transition Tests

```python
class TestImm03WorkflowTransitions(FrappeTestCase):
    """Kiểm tra tất cả transition hợp lệ và bất hợp lệ."""

    # IMM Vendor Evaluation workflow
    def test_eval_draft_to_open_rfq(self):
        """Draft → Open RFQ: hợp lệ bởi IMM Procurement Officer."""
        ...

    def test_eval_open_rfq_to_quotation_received_requires_g02(self):
        """Open RFQ → Quotation Received: cần ≥ 1 quotation hợp lệ (G02)."""
        ...

    def test_eval_quotation_received_to_evaluated_requires_g01(self):
        """Quotation Received → Evaluated: cần đủ 5 group scoring (G01)."""
        ...

    def test_eval_invalid_transition_evaluated_to_open_rfq(self):
        """Evaluated → Open RFQ: không cho phép (Evaluated là terminal)."""
        ...

    # IMM Procurement Decision workflow
    def test_decision_draft_to_method_selected_requires_g04(self):
        """Draft → Method Selected: G04 check phương án mua sắm."""
        ...

    def test_decision_pending_approval_to_awarded_requires_board_role(self):
        """Pending Approval → Awarded: chỉ IMM Board Approver."""
        ...

    def test_decision_awarded_to_cancelled_blocked(self):
        """Awarded → Cancelled: không cho phép (terminal positive)."""
        ...

    # AVL workflow
    def test_avl_draft_to_approved_by_board(self):
        """AVL Draft → Approved: chỉ IMM Board Approver."""
        ...

    def test_avl_approved_to_suspended_by_risk(self):
        """AVL Approved → Suspended: IMM Risk Officer được phép."""
        ...
```

---

### I.4 Integration Tests

```python
class TestImm03FullFlow(FrappeTestCase):
    """Integration test: Eval Draft → Evaluated → Decision Awarded → PO mint."""

    def test_full_eval_to_awarded_flow(self):
        """Full happy path: IMM-02 spec → Eval seed → candidates + quotations → score → Evaluated → Decision → Award → PO."""
        # 1. Seed evaluation from spec
        # 2. Add 3 AVL candidates
        # 3. Open RFQ, submit 3 quotations
        # 4. Score all 5 groups
        # 5. Transition → Evaluated
        # 6. Create Decision
        # 7. Award Decision → verify AC Purchase created
        # 8. Verify Plan Line status = Awarded
        # 9. Verify IMM Audit Trail has "Awarded" event
        ...

    def test_avl_lifecycle_approve_to_expired(self):
        """AVL: Draft → Approved → scheduler → Expired."""
        # 1. Create AVL with valid_from=today, validity_years=1
        # 2. Approve AVL
        # 3. Mock today = valid_to + 1 day
        # 4. Run check_avl_expiry()
        # 5. Verify status = Expired
        # 6. Verify Supplier.imm_avl_status updated
        ...

    def test_vendor_scorecard_quarterly_pipeline(self):
        """Quarterly scorecard: aggregate KPI từ IMM-04/09/15/10."""
        # 1. Setup mock data IMM-04, IMM-09, IMM-15, IMM-10
        # 2. Run update_vendor_scorecard(vendor, period)
        # 3. Verify VS record created with correct KPI rows
        # 4. Verify overall_score = weighted sum
        ...
```

---

### I.5 Audit Trail Tests

```python
class TestImm03AuditTrail(FrappeTestCase):
    """Kiểm tra IMM Audit Trail được ghi đúng."""

    def test_award_decision_writes_audit_trail(self):
        """award_decision() ghi IMM Audit Trail với action='Awarded'."""
        ...

    def test_po_created_audit_trail_entry(self):
        """Mint AC Purchase ghi IMM Audit Trail 'PO Created'."""
        ...

    def test_audit_trail_is_immutable(self):
        """VR-03-06: Không thể sửa/xóa IMM Audit Trail đã tạo."""
        ...
```

---

### I.6 API Tests

```python
class TestImm03API(FrappeTestCase):
    """API endpoint tests."""

    def test_create_vendor_profile_ok(self):
        """POST create_vendor_profile → {success: true}."""
        ...

    def test_create_avl_entry_ok(self):
        """POST create_avl_entry → {success: true, data.status: 'Draft'}."""
        ...

    def test_award_decision_forbidden_for_non_board(self):
        """POST award_decision → {success: false, code: 'FORBIDDEN'} nếu không phải Board Approver."""
        ...

    def test_score_evaluation_wrong_role_forbidden(self):
        """POST score_evaluation với scorer_role không khớp role → FORBIDDEN."""
        ...

    def test_dashboard_kpis_structure(self):
        """GET dashboard_kpis → 7 KPI keys đầy đủ."""
        ...
```

---

### I.7 Run Commands & Coverage

```bash
# Run toàn bộ test IMM-03
bench --site [site] run-tests --module assetcore.tests.test_imm03

# Run với coverage
bench --site [site] run-tests --module assetcore.tests.test_imm03 --coverage

# Run chỉ unit tests VR
bench --site [site] run-tests --module assetcore.tests.test_imm03.TestImm03ValidationRules

# Run chỉ integration tests
bench --site [site] run-tests --module assetcore.tests.test_imm03.TestImm03FullFlow
```

**Coverage targets:**
- Lines: ≥ 85%
- VR functions (7 VR): 100%
- Gate functions (5 gates): 100%
- `award_decision` (critical): 100%
- `compute_eval_score`: 100%

---

## II. UAT Script

### II.1 Phạm vi UAT

IMM-03 Wave 2 UAT xác nhận:
- Vendor Profile extension trên AC Supplier
- AVL lifecycle + auto-expiry
- Vendor Evaluation với scoring đa tiêu chí
- Procurement Decision 9 states
- Award → mint AC Purchase
- Vendor Scorecard quarterly
- Supplier Audit + CAPA

### II.2 Tài khoản test

| Tài khoản | Role | Mục đích |
|---|---|---|
| `dt.hd.ncc@test.vn` | IMM Procurement Officer | Tạo vendor, evaluation, decision |
| `kh.tc@test.vn` | IMM Planning Officer | Chấm Commercial; xem dashboard |
| `htm.engineer@test.vn` | IMM HTM Engineer | Chấm Technical |
| `tckt@test.vn` | IMM Finance Officer | Chấm Financial; Contract Signed |
| `qa.risk@test.vn` | IMM Risk Officer | Chấm Compliance; Supplier Audit |
| `ptp.k1@test.vn` | IMM Department Head | Submit; trình BGĐ |
| `vp.block1@test.vn` | IMM Board Approver | Approve AVL; Award Decision |
| `cmms.admin@test.vn` | IMM System Admin | Override |

### II.3 Test Data

- Suppliers: VINAMED, HAMILTON-VN, MINDRAY-VN, DRAGER-VN (đã tạo trong ERPNext)
- IMM Tech Spec: TS-26-00045 (Locked, plan_line=line001)
- IMM Procurement Plan: PP-26-001, allocated_budget=2.5 tỷ
- IMM Procurement Method Config: seed theo NĐ

### II.4 UAT Scenarios

| UAT-ID | Kịch bản | Actor | Expected | Kết quả |
|---|---|---|---|---|
| UAT-IMM03-01 | Tạo Vendor Profile VINAMED + cert ISO 9001 | ĐT-HĐ-NCC | Profile saved, cert Active | ☐ |
| UAT-IMM03-02 | Approve AVL VINAMED/Imaging 2 năm | VP Block1 | Status Approved, valid_to auto | ☐ |
| UAT-IMM03-03 | AVL auto-Expired + email cảnh báo | Scheduler | status=Expired, email sent | ☐ |
| UAT-IMM03-04 | Eval tự seed từ event imm02_spec_locked | System | VE-26-00120 Draft tạo | ☐ |
| UAT-IMM03-05 | Add 3 candidate (2 AVL + 1 non-AVL), warning hiện | ĐT-HĐ-NCC | in_avl flags đúng, warning | ☐ |
| UAT-IMM03-06 | Nhập 3 quotation → state Quotation Received | ĐT-HĐ-NCC | G02 pass, state change | ☐ |
| UAT-IMM03-07 | Chấm điểm 5 group (HTM+KH-TC+TCKT+QA+ĐT) → Evaluated | Mixed | weighted_score compute, recommended set | ☐ |
| UAT-IMM03-08 | Tạo Decision → Method Selected (G04 Đấu thầu rộng rãi OK) | ĐT-HĐ-NCC | state Method Selected | ☐ |
| UAT-IMM03-09 | Award Decision → AC Purchase mint | VP Block1 | docstatus=1, AC-PUR tạo, Plan Line Awarded | ☐ |
| UAT-IMM03-10 | Tạo AC Purchase TBYT direct (không có Decision) → throw | ĐT-HĐ-NCC | VR-03-08 block | ☐ |
| UAT-IMM03-11 | Vendor Scorecard quarterly aggregate KPI | Scheduler | VS-2026-Q2-VINAMED, kpi_rows đúng | ☐ |
| UAT-IMM03-12 | Supplier Audit với Critical finding → AVL Suspended | QA Risk | AVL Suspended, email VP Block1 | ☐ |

### II.5 Sign-off

| Vai trò | Họ tên | Ngày | Chữ ký |
|---|---|---|---|
| IMM Department Head | | | |
| QA Risk Officer | | | |
| CMMS Admin | | | |

**Điều kiện release:** ≥ 95% test case PASS; 0 Critical open; PO mint 100% thành công với decision hợp lệ.

---

## III. Security Review

### III.1 RBAC Matrix (DocPerm)

| DocType | Role | Read | Write | Create | Delete | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|---|---|
| IMM Vendor Evaluation | IMM Procurement Officer | Y | Y | Y | N | N | N | N |
| IMM Vendor Evaluation | IMM Department Head | Y | Y | N | N | Y | Y | N |
| IMM Vendor Evaluation | IMM Planning Officer | Y | N | N | N | N | N | N |
| IMM Vendor Evaluation | IMM HTM Engineer | Y | N | N | N | N | N | N |
| IMM Vendor Evaluation | IMM Risk Officer | Y | N | N | N | N | N | N |
| IMM Vendor Evaluation | IMM System Admin | Y | Y | Y | Y | Y | Y | Y |
| IMM Procurement Decision | IMM Procurement Officer | Y | Y | Y | N | N | N | N |
| IMM Procurement Decision | IMM Department Head | Y | Y | N | N | N | N | N |
| IMM Procurement Decision | IMM Board Approver | Y | Y | N | N | Y | N | N |
| IMM Procurement Decision | IMM Finance Officer | Y | Y | N | N | N | N | N |
| IMM Procurement Decision | IMM System Admin | Y | Y | Y | Y | Y | Y | Y |
| IMM AVL Entry | IMM Procurement Officer | Y | Y | Y | N | N | N | N |
| IMM AVL Entry | IMM Board Approver | Y | Y | N | N | Y | Y | N |
| IMM AVL Entry | IMM Risk Officer | Y | N | N | N | N | N | N |
| IMM AVL Entry | IMM System Admin | Y | Y | Y | Y | Y | Y | Y |
| IMM Vendor Scorecard | All IMM | Y | N | N | N | N | N | N |
| IMM Vendor Scorecard | IMM System Admin | Y | Y | Y | Y | N | N | N |
| IMM Supplier Audit | IMM Risk Officer | Y | Y | Y | N | Y | N | N |
| IMM Supplier Audit | IMM System Admin | Y | Y | Y | Y | Y | Y | Y |

### III.2 Field Permlevel

| Field | Permlevel | Visible to |
|---|---|---|
| `awarded_price` | 1 | KH-TC, TCKT, PTP Khối 1, VP Block1, System Admin |
| `envelope_check_pct` | 1 | KH-TC, TCKT, PTP Khối 1, VP Block1, System Admin |
| `funding_source` | 1 | KH-TC, TCKT, PTP Khối 1, VP Block1, System Admin |
| `funding_evidence` | 1 | TCKT, PTP Khối 1, VP Block1, System Admin |
| `contract_doc` | 1 | TCKT, PTP Khối 1, VP Block1, System Admin |
| `board_approver` | 1 | PTP Khối 1, VP Block1, System Admin |

### III.3 API Security

- Mọi endpoint phải có `@frappe.whitelist()` — không có anonymous access.
- `award_decision`: kiểm tra `frappe.has_permission("IMM Procurement Decision", "submit")` + role `IMM Board Approver`.
- `approve_avl`: kiểm tra role `IMM Board Approver`.
- Score group validation: `scorer_role` phải match Frappe role của user hiện tại — không để FE gửi role tùy ý.

### III.4 Audit Trail

- Mọi state transition ghi `IMM Audit Trail` với `actor = frappe.session.user`.
- `award_decision` ghi 2 events: "Awarded" + "PO Created".
- IMM Audit Trail: `permlevel 2` (read-only với mọi non-admin).
- VR-03-06: controller `validate` của `IMM Audit Trail` kiểm tra `docstatus=1 and modified_by != System` → throw.

### III.5 STRIDE Threat Analysis

| Threat | Tình huống | Biện pháp giảm thiểu |
|---|---|---|
| **Spoofing** | FE gửi `scorer_role` giả để chấm điểm nhóm không có quyền | BE validate role của `frappe.session.user` — không tin FE payload |
| **Tampering** | Sửa `awarded_price` sau khi submit Decision | `docstatus=1` → read-only; permlevel 1 restrict access |
| **Repudiation** | Phủ nhận đã Award Decision | IMM Audit Trail bất biến: actor + timestamp + from_state + to_state |
| **Information Disclosure** | User thông thường xem giá trúng thầu nhạy cảm | Permlevel 1 + FE mask `***` |
| **Elevation of Privilege** | Non-Board user gọi `award_decision` | API kiểm tra `frappe.has_role("IMM Board Approver")` |
| **Denial of Service** | Scorecard quarterly query nặng cả 1000 vendor cùng lúc | Scheduler chạy background job, không blocking; rate limit API |

### III.6 Data Sensitivity

| Dữ liệu | Mức độ | Xử lý |
|---|---|---|
| `awarded_price`, `funding_source` | Nhạy cảm — tài chính | Permlevel 1; không log rõ ràng |
| `vat_code`, `bank_account` | Nhạy cảm — vendor | Permlevel 0 + audit trail truy cập |
| `contract_doc` | Nhạy cảm — pháp lý | Permlevel 1; private file |
| `scores`, `weighted_score` | Bình thường | Permlevel 0 |
| `imm_overall_score` | Bình thường | Permlevel 0 |

### III.7 Code Quality Targets

| Metric | Target |
|---|---|
| Cyclomatic complexity (per function) | ≤ 10 |
| Function length | ≤ 50 lines |
| File length | ≤ 200 lines |
| Test coverage (lines) | ≥ 85% |
| Test coverage (VR + Gate) | 100% |
| Type hints | 100% function signatures |
| Docstrings | 100% public functions |
| No hardcoded logic | Required |
| No logic in controller | Required |
