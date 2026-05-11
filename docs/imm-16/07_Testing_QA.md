# IMM-16 — Testing & QA Plan

**Module:** IMM-16 — Compliance Monitoring & CAPA
**Wave:** 3 — PLANNED
**Ngày:** 2026-05-08
**Status:** PLANNED — chưa implement

---

## §I — Test Plan

### I.1 Phạm vi & Chiến lược

Module IMM-16 có 3 vùng tính toán **phải deterministic** — kết quả phụ thuộc chỉ vào input, không phụ thuộc thứ tự hay thời điểm gọi:

| Vùng | Tính toán cốt lõi | Risk nếu sai |
|------|---|---|
| Rule Evaluator | So sánh metric vs threshold theo op (`<`, `>`, `==`, `<=`, `>=`) | Finding sai severity / bỏ sót |
| Scorecard Aggregator | `score_pct = (total − nc) / total × 100` | KPI báo cáo sai → quyết định quản lý sai |
| Compliance Gate | `blocked = any(critical CAPA open for asset)` | WO submit bị chặn sai / bỏ qua chặn |

Chiến lược kiểm thử theo **Test Pyramid**:

```
          ┌──────────────┐
          │  E2E / UAT   │  12 kịch bản (Playwright / manual)
          ├──────────────┤
          │  Integration │  workflow transitions, cross-module gate
          ├──────────────┤
          │  Unit Tests  │  deterministic formula / business rule stubs
          └──────────────┘
```

> ⚠️ Pending implementation — Wave 3

### I.2 Test Scope

| Nhóm | In Scope | Out of Scope |
|------|---|---|
| Rule Evaluator | threshold comparison, idempotent upsert | Rule editor UI |
| Finding Lifecycle | Open → UC → Confirmed NC / FP / Waived | Email template rendering |
| CAPA Workflow | 6 states, re-open, effectiveness check | CAPA PDF export |
| Audit Cycle | Planned → In Progress → Closed, auto-Finding | Audit scheduling UI calendar |
| Scorecard | score_pct formula, immutability, restate | Chart visual rendering |
| Management Review | Quarterly gate, Finalize → Closed | MR meeting minutes editor |
| Cross-module Gate | BR-16-09 block IMM-08/09 WO | IMM-04/05 flows |
| Permission / RBAC | DocPerm + API role check | SSO / LDAP |
| Audit Trail | Frappe Version + IMM Audit Trail hash | Log rotation |

### I.3 Tools & Environments

| Item | Detail |
|------|---|
| Unit test runner | `bench --site test.assetcore.local run-tests --module assetcore` |
| Integration | `bench --site test.assetcore.local run-tests --doctype "IMM Compliance Finding"` |
| UAT | Playwright headless + manual sign-off |
| Coverage target | Line ≥ 85%, Branch ≥ 75% (vùng service layer) |
| CI gate | All unit + integration tests pass trước merge vào `main` |

---

## §II — Unit Test Stubs

> ⚠️ Pending implementation — Wave 3
>
> Các stub dưới đây là **test template** — điền logic khi implement service layer.

### II.1 RuleEvaluator — Deterministic Formula Tests

```python
# tests/test_imm16_rule_evaluator.py
import pytest
from unittest.mock import MagicMock, patch

# ⚠️ Pending implementation — Wave 3
# from assetcore.services.imm16_rule_evaluator import RuleEvaluator, evaluate_threshold


class TestThresholdComparison:
    """
    Kiểm tra evaluate_threshold(metric_value, op, threshold_value) → bool
    Input/output phải DETERMINISTIC — cùng input luôn cùng output.
    """

    # ⚠️ Pending implementation — Wave 3
    # Uncomment khi implement evaluate_threshold

    @pytest.mark.parametrize("metric_val, op, threshold, expected", [
        (78.0,  "<",  90.0,  True),   # PM compliance 78% < 90% → trigger
        (92.0,  "<",  90.0,  False),  # 92% OK → no trigger
        (90.0,  "<",  90.0,  False),  # boundary: NOT strictly less
        (90.0,  "<=", 90.0,  True),   # boundary: less-or-equal triggers
        (30.0,  ">",  0.0,   True),   # calibration overdue days > 0
        (0.0,   ">",  0.0,   False),  # not overdue
        (100.0, "==", 100.0, True),   # doc compliance == 100%
        (99.0,  "==", 100.0, False),  # 99% ≠ 100%
        (50.0,  ">=", 50.0,  True),   # exactly at threshold
    ])
    def test_evaluate_threshold_cases(self, metric_val, op, threshold, expected):
        # result = evaluate_threshold(metric_val, op, threshold)
        # assert result == expected
        pytest.skip("⚠️ Wave 3 — implement evaluate_threshold first")

    def test_invalid_op_raises_value_error(self):
        # with pytest.raises(ValueError, match="op không hợp lệ"):
        #     evaluate_threshold(80.0, "INVALID", 90.0)
        pytest.skip("⚠️ Wave 3 — pending")

    def test_none_metric_value_skips_evaluation(self):
        # result = evaluate_threshold(None, "<", 90.0)
        # assert result is False  # None metric → không tạo Finding
        pytest.skip("⚠️ Wave 3 — pending")


class TestRuleEvaluatorIdempotency:
    """
    Idempotent upsert: cùng (rule, source_record, evaluation_date) → 1 finding.
    """

    def test_second_eval_same_day_does_not_create_duplicate(self):
        """
        TC-03 Step 5: Chạy lại scheduler cùng ngày → count Finding = 1.
        """
        # mock_frappe = MagicMock()
        # evaluator = RuleEvaluator(db=mock_frappe)
        # evaluator.run_for_rule("TEST-R-001", evaluation_date=date(2026, 5, 1))
        # evaluator.run_for_rule("TEST-R-001", evaluation_date=date(2026, 5, 1))
        # assert mock_frappe.db.count("IMM Compliance Finding", {...}) == 1
        pytest.skip("⚠️ Wave 3 — pending")

    def test_different_date_creates_new_finding(self):
        # Ngày khác → finding mới (monthly re-eval)
        pytest.skip("⚠️ Wave 3 — pending")

    def test_finding_severity_maps_from_rule_severity(self):
        """
        Finding severity phải mirror rule severity, không tự tính.
        """
        pytest.skip("⚠️ Wave 3 — pending")

    def test_finding_current_value_captured_correctly(self):
        """
        TC-03 Step 3: current_value=78, threshold_value=90 phải đúng.
        """
        pytest.skip("⚠️ Wave 3 — pending")


class TestRuleChangeControl:
    """
    BR-16-05: Thay đổi rule yêu cầu change_summary.
    VR-11: version tự tăng.
    """

    def test_save_without_change_summary_raises(self):
        # doc = MagicMock(is_new=MagicMock(return_value=False))
        # doc.threshold_definition_changed = True
        # doc.change_summary = ""
        # with pytest.raises(ValidationError, match="Tóm tắt thay đổi"):
        #     IMMComplianceRuleController(doc).validate()
        pytest.skip("⚠️ Wave 3 — pending")

    def test_version_increments_on_save(self):
        # version "1.0" → save → "1.1"
        pytest.skip("⚠️ Wave 3 — pending")

    def test_new_rule_version_is_1_0(self):
        # New doc → version = "1.0"
        pytest.skip("⚠️ Wave 3 — pending")
```

### II.2 ScorecardAggregator — Formula Tests

```python
# tests/test_imm16_scorecard.py
import pytest

# ⚠️ Pending implementation — Wave 3
# from assetcore.services.imm16_scorecard import ScorecardAggregator, compute_score_pct


class TestScorecardFormula:
    """
    score_pct = (total_findings - non_compliant_count) / total_findings * 100
    Round 2 decimal places.
    """

    @pytest.mark.parametrize("total, nc, expected_pct", [
        (100, 10, 90.0),    # 90 compliant / 100 → 90%
        (50,  0,  100.0),   # fully compliant
        (50,  50, 0.0),     # fully non-compliant
        (3,   1,  66.67),   # round to 2dp
        (7,   2,  71.43),   # irrational → round
        (0,   0,  100.0),   # no findings → 100% (convention: no issue = compliant)
    ])
    def test_score_pct_formula(self, total, nc, expected_pct):
        # result = compute_score_pct(total, nc)
        # assert result == expected_pct
        pytest.skip("⚠️ Wave 3 — pending")

    def test_score_pct_cannot_exceed_100(self):
        # Edge: nc < 0 should be clamped to 0
        pytest.skip("⚠️ Wave 3 — pending")

    def test_score_pct_cannot_be_negative(self):
        pytest.skip("⚠️ Wave 3 — pending")


class TestScorecardImmutability:
    """
    VR-09: Sau publish → read-only; chỉ tạo Restate version.
    """

    def test_published_scorecard_raises_on_edit(self):
        # doc = MagicMock(is_published=1, is_new=MagicMock(return_value=False))
        # with pytest.raises(ValidationError, match="Scorecard đã publish"):
        #     IMMComplianceScorecardController(doc).validate()
        pytest.skip("⚠️ Wave 3 — pending")

    def test_restate_creates_new_doc_with_link(self):
        # restate() → new Scorecard with restate_of = original.name
        pytest.skip("⚠️ Wave 3 — pending")

    def test_quarterly_mr_gate_blocks_publish(self):
        """
        BR-16-08: Không có MR Closed của quý trước → raise MR_MISSING_QUARTERLY.
        """
        pytest.skip("⚠️ Wave 3 — pending")

    def test_quarterly_mr_gate_passes_when_mr_closed(self):
        pytest.skip("⚠️ Wave 3 — pending")


class TestScorecardTrend:
    """
    trend_vs_prev_month phải tính đúng delta.
    """

    def test_trend_positive_when_improved(self):
        # prev=80%, curr=85% → trend=+5.0
        pytest.skip("⚠️ Wave 3 — pending")

    def test_trend_negative_when_declined(self):
        # prev=90%, curr=85% → trend=-5.0
        pytest.skip("⚠️ Wave 3 — pending")

    def test_trend_none_when_no_prev_scorecard(self):
        # Tháng đầu tiên → trend=None
        pytest.skip("⚠️ Wave 3 — pending")
```

### II.3 ComplianceGate — Cross-module Gate Tests

```python
# tests/test_imm16_compliance_gate.py
import pytest
from unittest.mock import patch, MagicMock

# ⚠️ Pending implementation — Wave 3
# from assetcore.services.imm16_gate import ComplianceGate, check_asset_compliance_status


class TestComplianceGate:
    """
    BR-16-09: Asset có CAPA Critical open → block WO submit.
    """

    def test_asset_with_critical_capa_is_blocked(self):
        # mock: asset has 1 CAPA Critical in status=[Investigating, Action Plan, Implementation, Verification]
        # result = check_asset_compliance_status("ASSET-001")
        # assert result["blocked"] is True
        # assert "CAPA_CRITICAL_OPEN" in result["reasons"]
        pytest.skip("⚠️ Wave 3 — pending")

    def test_asset_with_no_critical_capa_is_not_blocked(self):
        # CAPA Closed → không block
        pytest.skip("⚠️ Wave 3 — pending")

    def test_asset_with_high_capa_is_not_blocked(self):
        # Chỉ CRITICAL block, HIGH không block (BR-16-09 explicit)
        pytest.skip("⚠️ Wave 3 — pending")

    def test_gate_called_in_imm08_validate(self):
        """
        validate_pm_work_order_before_submit() phải gọi check_asset_compliance_status.
        """
        # with patch("assetcore.services.imm16_gate.check_asset_compliance_status") as mock_gate:
        #     mock_gate.return_value = {"blocked": True, "reasons": ["CAPA_CRITICAL_OPEN"]}
        #     with pytest.raises(ValidationError, match="CAPA Critical"):
        #         validate_pm_work_order_before_submit(doc=MagicMock(asset="ASSET-001"))
        pytest.skip("⚠️ Wave 3 — pending")

    def test_gate_result_is_deterministic(self):
        # Cùng asset, cùng CAPA state → cùng result bất kể thứ tự gọi
        pytest.skip("⚠️ Wave 3 — pending")


class TestCAPAHookValidation:
    """
    doc_events trên IMM CAPA Record — validate trước submit.
    """

    def test_effectiveness_required_before_close(self):
        """
        VR-06: Không có effectiveness_result → không thể chuyển → Closed.
        """
        pytest.skip("⚠️ Wave 3 — pending")

    def test_not_effective_reopens_capa(self):
        """
        BR-16-03: effectiveness_result=Not Effective → status → Re-opened.
        """
        pytest.skip("⚠️ Wave 3 — pending")

    def test_reopen_count_increments(self):
        # reopen_count + 1 mỗi lần re-open
        pytest.skip("⚠️ Wave 3 — pending")

    def test_root_cause_method_required_for_action_plan(self):
        """
        VR-05: root_cause_method bắt buộc khi advance to Action Plan.
        """
        pytest.skip("⚠️ Wave 3 — pending")

    def test_due_date_must_be_future(self):
        """
        VR-12: due_date < today → raise "Hạn hoàn thành phải sau hôm nay".
        """
        pytest.skip("⚠️ Wave 3 — pending")
```

### II.4 WaiveFinding — Validation Tests

```python
# tests/test_imm16_waive_finding.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta

# ⚠️ Pending implementation — Wave 3
# from assetcore.api.imm16 import waive_finding


class TestWaiveFinding:
    """
    VR-04 / BR-16-06: Chỉ VP Block2 được waive; reason ≥ 50 chars; evidence required; expiry > today.
    """

    def test_non_vp_role_raises_forbidden(self):
        # with patch("frappe.session.user", "test_wshead"):
        #     with pytest.raises(PermissionError):
        #         waive_finding(finding_name="FND-001", reason="x"*60, ...)
        pytest.skip("⚠️ Wave 3 — pending")

    def test_short_reason_raises_validation(self):
        # reason="short" (< 50 chars) → VR-04 raise
        pytest.skip("⚠️ Wave 3 — pending")

    def test_missing_evidence_raises_validation(self):
        # evidence=None → VR-04 raise
        pytest.skip("⚠️ Wave 3 — pending")

    def test_expired_waiver_date_raises_validation(self):
        # waiver_expiry = today - 1 → VR-04 raise
        pytest.skip("⚠️ Wave 3 — pending")

    def test_valid_waive_sets_status_waived(self):
        # All valid → finding.status = "Waived"
        pytest.skip("⚠️ Wave 3 — pending")
```

---

## §III — Workflow Transition Tests

> ⚠️ Pending implementation — Wave 3

### III.1 IMM Compliance Finding Workflow

```python
# tests/test_imm16_finding_workflow.py
import frappe
import pytest

# ⚠️ Pending implementation — Wave 3

FINDING_TRANSITIONS = [
    # (from_state, action_vi, to_state, actor_role, should_pass)
    ("Open",             "Xem xét",      "Under Review",  "Tổ HC-QLCL",    True),
    ("Under Review",     "Xác nhận NC",  "Confirmed NC",  "Tổ HC-QLCL",    True),
    ("Under Review",     "Đánh dấu FP",  "False Positive","Tổ HC-QLCL",    True),
    ("Under Review",     "Miễn trừ",     "Waived",        "VP Block2",      True),
    ("Under Review",     "Miễn trừ",     "Waived",        "Tổ HC-QLCL",    False),  # role block
    ("Confirmed NC",     "Giải quyết",   "Resolved",      "Tổ HC-QLCL",    True),
    ("Resolved",         "Mở lại",       "Open",          "Tổ HC-QLCL",    True),
]


@pytest.mark.parametrize("from_s, action, to_s, role, should_pass", FINDING_TRANSITIONS)
def test_finding_transition(from_s, action, to_s, role, should_pass):
    # doc = create_test_finding(status=from_s)
    # set_session_user(role)
    # if should_pass:
    #     apply_workflow_action(doc, action)
    #     assert doc.workflow_state == to_s
    # else:
    #     with pytest.raises(PermissionError):
    #         apply_workflow_action(doc, action)
    pytest.skip("⚠️ Wave 3 — pending")
```

### III.2 IMM CAPA Record Extended Workflow

```python
# tests/test_imm16_capa_workflow.py
import pytest

# ⚠️ Pending implementation — Wave 3

CAPA_TRANSITIONS = [
    # (from_state, action_vi, to_state, should_pass, precondition)
    ("Draft",         "Điều tra",        "Investigating",  True,  None),
    ("Investigating", "Lập kế hoạch",    "Action Plan",    True,  "root_cause_method set"),
    ("Investigating", "Lập kế hoạch",    "Action Plan",    False, "root_cause_method empty"),  # VR-05
    ("Action Plan",   "Triển khai",      "Implementation", True,  "≥1 action_step"),
    ("Implementation","Xác minh",        "Verification",   True,  "all steps Done"),
    ("Verification",  "Đóng",            "Closed",         True,  "effectiveness=Effective"),
    ("Verification",  "Đóng",            "Closed",         False, "effectiveness empty"),       # VR-06
    ("Verification",  "Đóng",            "Closed",         False, "effectiveness=Not Effective"),  # BR-16-03
    ("Verification",  "Không hiệu quả",  "Investigating",  True,  "effectiveness=Not Effective"),  # re-open
    ("Closed",        "Mở lại",          "Investigating",  True,  "role=Tổ HC-QLCL"),
]


@pytest.mark.parametrize("from_s, action, to_s, should_pass, precond", CAPA_TRANSITIONS)
def test_capa_transition(from_s, action, to_s, should_pass, precond):
    pytest.skip("⚠️ Wave 3 — pending")
```

### III.3 IMM Compliance Scorecard Workflow

```python
# tests/test_imm16_scorecard_workflow.py
import pytest

# ⚠️ Pending implementation — Wave 3

SCORECARD_TRANSITIONS = [
    ("Draft",     "Công bố",  "Published", True,  "MR Closed quý trước"),
    ("Draft",     "Công bố",  "Published", False, "Không có MR Closed"),  # BR-16-08
    ("Published", "Khôi phục","Draft",     False, "immutable — VR-09"),
]


@pytest.mark.parametrize("from_s, action, to_s, should_pass, precond", SCORECARD_TRANSITIONS)
def test_scorecard_transition(from_s, action, to_s, should_pass, precond):
    pytest.skip("⚠️ Wave 3 — pending")
```

### III.4 IMM Internal Audit Workflow

```python
# tests/test_imm16_audit_workflow.py
import pytest

# ⚠️ Pending implementation — Wave 3

AUDIT_TRANSITIONS = [
    ("Planned",     "Bắt đầu kiểm toán", "In Progress", True,  None),
    ("In Progress", "Hoàn thành",         "Completed",   True,  "all checklist done"),
    ("Completed",   "Đóng kiểm toán",     "Closed",      True,  "all Major NC có CAPA"),
    ("Completed",   "Đóng kiểm toán",     "Closed",      False, "Major NC chưa có CAPA"),  # VR-08
]


@pytest.mark.parametrize("from_s, action, to_s, should_pass, precond", AUDIT_TRANSITIONS)
def test_audit_transition(from_s, action, to_s, should_pass, precond):
    pytest.skip("⚠️ Wave 3 — pending")
```

---

## §IV — UAT Scenarios

> ⚠️ Pending implementation — Wave 3
>
> 12 kịch bản UAT chọn từ TC-01..TC-12 của `IMM-16_UAT_Script.md`. Actor, precondition, và kết quả mong đợi đã được chuẩn hóa theo định dạng AssetCore UAT.

### UAT-IMM16-01: Tạo Compliance Rule (Happy Path)

**Nguồn gốc:** TC-01
**Actor:** Tổ HC-QLCL (`test_qlcl`)
**Precondition:** PC-02 (user role Tổ HC-QLCL tồn tại)
**Priority:** P1

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | Login `test_qlcl`, mở `/imm16/rules` | Thấy nút `+ Tạo Rule mới` |
| 2 | Tạo rule `rule_code="TEST-R-001"`, `source_module=IMM-08`, `category=PM`, `severity=High` | — |
| 3 | Điền threshold JSON `{"metric":"pm_compliance_pct","op":"<","value":90}` | — |
| 4 | Click Save | Rule saved: `version="1.0"`, `is_active=1`, autoname=`TEST-R-001` |
| 5 | Verify listing `/imm16/rules` | Rule hiện trong danh sách |

**Pass Criteria:** Rule tạo được, version=1.0, is_active=1.

---

### UAT-IMM16-02: Validation Rule (Error Cases)

**Nguồn gốc:** TC-02
**Actor:** Tổ HC-QLCL
**Priority:** P1

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | Tạo rule threshold=`{"foo":"bar"}` | Lỗi VR-01: "Threshold rule không hợp lệ. Cần `metric`, `op`, `value`." |
| 2 | Sửa op=`"INVALID"` | Lỗi VR-01: op không hợp lệ |
| 3 | Sửa threshold hợp lệ, Save | Save thành công |

**Pass Criteria:** VR-01 block save khi threshold sai format/op.

---

### UAT-IMM16-03: Auto-detect Finding qua Scheduler (Idempotent)

**Nguồn gốc:** TC-03
**Actor:** System (scheduler) — Tổ HC-QLCL verify
**Precondition:** UAT-IMM16-01 passed; PC-11 (PM compliance ICU = 78%)
**Priority:** P0 (core functionality)

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | Chạy `bench execute assetcore.tasks.run_compliance_evaluation_monthly` | Hoàn thành không lỗi |
| 2 | Mở `/imm16/findings` filter `rule=TEST-R-001` | Có 1 Finding mới |
| 3 | Verify Finding fields | `severity=High`, `current_value=78`, `threshold_value=90`, `status=Open`, `responsible_dept=ICU` |
| 4 | Chạy lại scheduler cùng ngày | Count Finding = 1 (idempotent — UNIQUE INDEX không tạo duplicate) |

**Pass Criteria:** Idempotency verified — 2 lần chạy = 1 finding.

---

### UAT-IMM16-04: Confirm NC & Open CAPA

**Nguồn gốc:** TC-04
**Actor:** Tổ HC-QLCL
**Precondition:** UAT-IMM16-03 passed
**Priority:** P0

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | Mở Finding từ UAT-03 | Nút [Confirm NC] và [Mark FP] hiện |
| 2 | Click [Confirm NC] | `status → Confirmed NC`, `reviewer` set, `review_date=now` |
| 3 | Click [Open CAPA] | Modal tạo CAPA hiện; `source=Finding` pre-fill |
| 4 | Điền `problem_statement`, `risk_level=High`, `action_owner=test_wshead`, Submit | CAPA tạo `status=Draft`; `finding.capa_ref` set |
| 5 | Verify naming | `CAPA-{YYYY}-#####` đúng format |

**Pass Criteria:** CAPA tạo thành công từ Finding, liên kết 2 chiều.

---

### UAT-IMM16-05: CAPA Lifecycle Full (Happy Path)

**Nguồn gốc:** TC-05
**Actor:** `test_wshead` (action owner) → `test_qlcl` (verify)
**Precondition:** UAT-IMM16-04 passed
**Priority:** P0

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | `test_wshead` advance Draft → Investigating | OK |
| 2 | Advance to Action Plan THIẾU `root_cause_method` | VR-05: "Phải chọn phương pháp RCA..." |
| 3 | Chọn `root_cause_method=5-Why`, `due_date=today-1` | VR-12: "Hạn hoàn thành phải sau hôm nay" |
| 4 | Set `due_date=today+30`, advance → Action Plan | `status=Action Plan` |
| 5 | Thêm 3 action_steps, advance → Implementation | OK |
| 6 | Mark all steps Done, advance → Verification | OK |
| 7 | Advance → Closed mà chưa effectiveness check | VR-06 throw |
| 8 | Click [Effectiveness Check], chọn "Effective", upload evidence | — |
| 9 | Verify CAPA → Closed, linked Finding → Resolved | Cascade tự động |

**Pass Criteria:** Full 6-state lifecycle hoàn thành; Finding auto-resolve.

---

### UAT-IMM16-06: CAPA Re-open (Not Effective)

**Nguồn gốc:** TC-06
**Actor:** `test_qlcl`
**Priority:** P1

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | CAPA ở Verification, Effectiveness Check = "Not Effective" + evidence | CAPA status → Investigating; `reopen_count=1` |
| 2 | Cố advance Verification → Closed trực tiếp | VR-07: "Không thể Close khi effectiveness chưa Effective" |
| 3 | Thêm action_step mới, hoàn thành lại, Effectiveness="Effective" | CAPA → Closed |

**Pass Criteria:** BR-16-03 enforced; reopen_count tăng đúng.

---

### UAT-IMM16-07: Waive Finding (BR-16-06)

**Nguồn gốc:** TC-07
**Actor:** `test_vp2` (VP Block2)
**Priority:** P1

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | `test_qlcl` mở Finding "Under Review" | Button [Waive] KHÔNG hiện |
| 2 | `test_vp2` mở Finding tương tự | Button [Waive] hiện |
| 3 | Click [Waive], `reason` < 50 chars | VR-04: "Lý do miễn trừ cần ≥ 50 ký tự" |
| 4 | Reason đủ, không upload evidence | VR-04: evidence bắt buộc |
| 5 | `expiry < today` | VR-04: "Ngày hết hạn phải sau hôm nay" |
| 6 | Tất cả hợp lệ | `finding.status=Waived` |
| 7 | `test_wshead` cố waive | `code=FORBIDDEN` |

**Pass Criteria:** Waive chỉ VP Block2; 3 VR-04 validation enforced.

---

### UAT-IMM16-08: Internal Audit Cycle

**Nguồn gốc:** TC-08
**Actor:** `test_qlcl` (lead) → `test_auditor` → `test_vp2` (close)
**Priority:** P1

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | Tạo audit `scope=[IMM-08,IMM-11]`, `depts=[ICU,CT]` | `status=Planned` |
| 2 | Click [Start Audit] | `status=In Progress`, `actual_start=today` |
| 3 | `test_auditor` hoàn thành 5 checklist: 1 Major NC, 1 Minor NC, 3 Compliant | — |
| 4 | Verify 2 Finding tự sinh (Major→High, Minor→Medium), `linked_finding` set | Đúng |
| 5 | `test_vp2` cố [Close Audit] mà Major NC chưa có CAPA | VR-08: "Còn Major NC chưa mở CAPA" |
| 6 | Mở CAPA cho Major NC, `test_vp2` [Close Audit] + upload PDF | `status=Closed`, `actual_end=today` |

**Pass Criteria:** Auto-Finding creation; VR-08 gate enforced; audit closed với evidence.

---

### UAT-IMM16-09: Compliance Scorecard sinh + Publish

**Nguồn gốc:** TC-09
**Actor:** System → `test_vp2`
**Priority:** P0

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | Chạy `bench execute assetcore.tasks.update_compliance_scorecard` | Hoàn thành không lỗi |
| 2 | Mở `/imm16/scorecards` | Có scorecard mới `status=Draft` |
| 3 | Verify `score_pct = (total-nc)/total × 100` (round 2dp) | Đúng |
| 4 | Verify `score_by_module`, `score_by_department`, `trend_vs_prev_month` filled | Đúng |
| 5 | Publish khi quý trước có MR Closed | `is_published=1`, `published_at` set |
| 6 | Sau publish, sửa `score_pct` | VR-09: "Scorecard đã publish, không thể sửa" |
| 7 | Click [Tạo Restate] | Scorecard mới với `restate_of` link; bản cũ immutable |

**Pass Criteria:** Formula đúng; immutability enforced; restate flow hoạt động.

---

### UAT-IMM16-10: Quarterly MR Gate (BR-16-08)

**Nguồn gốc:** TC-10
**Actor:** `test_vp2`
**Priority:** P0

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | Xóa/cancel MR quý trước trong test env | Không có MR Closed |
| 2 | Cố [Publish] scorecard tháng đầu quý mới | VR-10: "Quý {q} chưa có Management Review" — `code=MR_MISSING_QUARTERLY` |
| 3 | Tạo MR quý trước, Finalize → Closed | `status=Closed` |
| 4 | Publish lại | OK |

**Pass Criteria:** BR-16-08 hard gate; không thể bypass.

---

### UAT-IMM16-11: Cross-module Gate (BR-16-09)

**Nguồn gốc:** TC-11
**Actor:** `test_biomed` (từ IMM-08)
**Precondition:** `AC-ASSET-TEST-IMM16-003` có CAPA Critical `status=Implementation`
**Priority:** P0 (cross-module integration)

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | `GET /api/method/assetcore.api.imm16.check_asset_compliance_status?asset=AC-ASSET-TEST-IMM16-003` | `{"success":true,"data":{"blocked":true,"reasons":["CAPA_CRITICAL_OPEN"]}}` |
| 2 | Submit IMM-08 PM Work Order trên asset này | Frappe ValidationError: "Block: thiết bị có CAPA Critical chưa close (BR-16-09)" |
| 3 | Close CAPA (Effectiveness=Effective) | CAPA → Closed |
| 4 | Gọi lại API check | `{"success":true,"data":{"blocked":false,"reasons":[]}}` |
| 5 | Submit IMM-08 PM | OK — WO Submitted |

**Pass Criteria:** Gate block/unblock deterministic theo CAPA state.

---

### UAT-IMM16-12: Compliance Heatmap

**Nguồn gốc:** TC-12
**Actor:** `test_qlcl`
**Priority:** P2

| Step | Hành động | Kết quả mong đợi |
|------|---|---|
| 1 | Mở `/imm16/heatmap` | Heatmap render module × dept grid |
| 2 | Verify màu cell: ≥90 xanh, 80-89 vàng, 70-79 cam, <70 đỏ | Đúng |
| 3 | Hover cell `IMM-08 × ICU` | Tooltip: `{module, dept, score, findings_count}` |
| 4 | Click cell → drill-down | Navigate `/imm16/findings` với filter đúng |
| 5 | Cell có Critical Finding → hiển thị ★ | Đúng |

**Pass Criteria:** Heatmap render đúng màu, drill-down navigate đúng.

---

## §V — Security STRIDE

> ⚠️ Pending implementation — Wave 3

### V.1 Threat Model — STRIDE Analysis

| Threat | Scenario | Mitigation | Status |
|--------|---|---|:---:|
| **Spoofing** | Giả mạo `test_qlcl` để create Rule | Frappe session auth + `frappe.only_for()` | PLANNED |
| **Spoofing** | Giả mạo role VP Block2 để waive Finding | `ALLOWED_ROLES["waive_finding"]` check tại API layer | PLANNED |
| **Tampering** | Sửa `score_pct` trên Published Scorecard | VR-09 `validate()` + `perm[write]=0` sau publish | PLANNED |
| **Tampering** | Sửa `current_value` Finding sau Confirmed NC | DocPerm: write=0 cho non-admin sau confirm | PLANNED |
| **Tampering** | Bypass BR-16-09 gate bằng cách gọi WO submit trực tiếp | `validate` hook trong `doc_events` — không thể bypass | PLANNED |
| **Repudiation** | Deny waive Finding sau khi đã waive | IMM Audit Trail + Frappe Version (immutable hash chain) | PLANNED |
| **Repudiation** | Claim CAPA chưa bao giờ được Closed | `doc_events after_submit` ghi audit trail với actor | PLANNED |
| **Info Disclosure** | Xem Finding của dept khác không có quyền | DocPerm `if_owner` + dept filter ở service layer | PLANNED |
| **Info Disclosure** | Lấy list CAPA Critical qua API không auth | `@frappe.whitelist()` yêu cầu logged-in session | PLANNED |
| **Denial of Service** | Flood scheduler `run_compliance_evaluation` | Job dedup bằng UNIQUE INDEX; scheduler rate-limited | PLANNED |
| **Elevation of Privilege** | Tổ HC-QLCL cố finalize MR (chỉ VP2) | `frappe.only_for(["VP Block2", "CMMS Admin"])` tại API | PLANNED |
| **Elevation of Privilege** | Biomed cố effectiveness check | Role check `ALLOWED_ROLES["effectiveness_check"]` | PLANNED |

### V.2 Security Requirements

```
# ⚠️ Pending implementation — Wave 3
SEC-01: Mọi API endpoint trong imm16/ phải có @frappe.whitelist()
SEC-02: Sensitive actions (waive, publish, finalize_mr) phải log vào IMM Audit Trail
SEC-03: Published Scorecard: DocPerm write=0, delete=0 cho tất cả roles ngoài System
SEC-04: CAPA attachment (evidence) phải qua Frappe File với is_private=1
SEC-05: Audit trail hash chain — mỗi entry hash = sha256(prev_hash + content)
```

---

## §VI — DocPerm Matrix

> ⚠️ Pending implementation — Wave 3

### VI.1 IMM Compliance Rule

| Role | Read | Write | Create | Delete | Submit | Cancel |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| Tổ HC-QLCL | ✓ | ✓ | ✓ | ✗ | — | — |
| Internal Auditor | ✓ | ✗ | ✗ | ✗ | — | — |
| Workshop Head | ✓ | ✗ | ✗ | ✗ | — | — |
| Biomed Engineer | ✓ | ✗ | ✗ | ✗ | — | — |
| VP Block2 | ✓ | ✗ | ✗ | ✗ | — | — |
| Trưởng phòng | ✓ | ✗ | ✗ | ✗ | — | — |
| CMMS Admin | ✓ | ✓ | ✓ | ✓ | — | — |

### VI.2 IMM Compliance Finding

| Role | Read | Write | Create | Delete | Submit | Cancel |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| Tổ HC-QLCL | ✓ | ✓* | ✓ | ✗ | ✓ | ✗ |
| Internal Auditor | ✓ | ✓* | ✓ | ✗ | ✗ | ✗ |
| Workshop Head | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Biomed Engineer | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| VP Block2 | ✓ | ✓** | ✗ | ✗ | ✗ | ✗ |
| Trưởng phòng | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| CMMS Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

_* Write only if status = Open / Under Review (pre-confirm)_
_** Write only for waive_reason / waive_evidence fields (via API, không phải form edit)_

### VI.3 IMM CAPA Record (Extended)

| Role | Read | Write | Create | Delete | Submit | Cancel |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| Tổ HC-QLCL | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Internal Auditor | ✓ | ✓* | ✓ | ✗ | ✗ | ✗ |
| Workshop Head | ✓ | ✓* | ✓ | ✗ | ✗ | ✗ |
| Biomed Engineer | ✓ | ✓* | ✓ | ✗ | ✗ | ✗ |
| VP Block2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Trưởng phòng | ✓ | ✓* | ✓ | ✗ | ✗ | ✗ |
| CMMS Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

_* Write limited to owned records / action_steps own dept_

### VI.4 IMM Internal Audit

| Role | Read | Write | Create | Delete | Submit | Cancel |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| Tổ HC-QLCL | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| Internal Auditor | ✓ | ✓* | ✗ | ✗ | ✗ | ✗ |
| Workshop Head | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Biomed Engineer | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| VP Block2 | ✓ | ✓** | ✗ | ✗ | ✓** | ✗ |
| CMMS Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

_* Write only checklist items when audit In Progress_
_** Close audit only_

### VI.5 IMM Compliance Scorecard

| Role | Read | Write | Create | Delete | Submit | Cancel |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| Tổ HC-QLCL | ✓ | ✓* | ✗ | ✗ | ✓* | ✗ |
| Internal Auditor | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Workshop Head | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Biomed Engineer | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| VP Block2 | ✓ | ✗ | ✗ | ✗ | ✓* | ✗ |
| Trưởng phòng | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| System | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CMMS Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

_* Write/Submit only when is_published=0_

### VI.6 IMM Management Review

| Role | Read | Write | Create | Delete | Submit | Cancel |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| Tổ HC-QLCL | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Internal Auditor | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| VP Block2 | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ |
| CMMS Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## §VII — Code Quality Targets

> ⚠️ Pending implementation — Wave 3

### VII.1 Coverage Targets

| Layer | Target | Tool |
|-------|---|---|
| Service layer (`services/imm16*.py`) | Line ≥ 85%, Branch ≥ 75% | `coverage.py` |
| API layer (`api/imm16.py`) | Line ≥ 80% | `coverage.py` |
| Controller hooks (`controllers/imm16*.py`) | Line ≥ 85% | `coverage.py` |
| Frontend stores/composables | Line ≥ 75% | Vitest |
| Frontend components (critical paths) | ≥ 70% | Vitest + Vue Test Utils |

### VII.2 Static Analysis

```yaml
# ⚠️ Pending implementation — Wave 3
ruff:
  target-version: "py311"
  select: ["E", "W", "F", "I", "B", "C4", "UP"]
  ignore: ["E501"]  # line length handled by formatter

mypy:
  strict: true
  modules: ["assetcore.services.imm16*", "assetcore.api.imm16"]

eslint:
  extends: ["@vue/typescript/recommended"]
  rules:
    "@typescript-eslint/no-explicit-any": "error"
    "vue/no-unused-vars": "error"
```

### VII.3 Performance Benchmarks

| Scenario | Target | Method |
|----------|---|---|
| `run_compliance_evaluation_monthly` (1000 rules × 500 assets) | < 120s | Background job; benchmark in staging |
| `get_compliance_heatmap` API (6 months × 8 modules × 20 depts) | < 2s p95 | DB indexes + cache |
| `check_asset_compliance_status` (gate check) | < 200ms p99 | Single SQL query; EXPLAIN ANALYZE |
| `update_compliance_scorecard` (monthly) | < 30s | Batch aggregation |
| Scorecard list page load (50 rows) | < 1s | Frappe list + index on `period` |

### VII.4 Code Review Checklist

```
# Trước mỗi PR merge vào main — IMM-16 specific:
[ ] Service layer không có Frappe DB calls trực tiếp trong controller
[ ] Mọi API endpoint có @frappe.whitelist() + role check
[ ] Mọi action mutation có ghi IMM Audit Trail
[ ] evaluate_threshold() không có side effects
[ ] ScorecardAggregator.compute() idempotent với cùng period input
[ ] ComplianceGate không raise exception — return {blocked, reasons}
[ ] CAPA hook doc_events không break existing IMM CAPA Record tests
[ ] Mọi scheduler job có error handling + logging
[ ] DB indexes được verify bằng EXPLAIN ANALYZE
[ ] TypeScript strict mode — không có `any` type
```

### VII.5 Test Execution Order (CI Pipeline)

```
# ⚠️ Pending implementation — Wave 3
1. Lint (ruff, mypy, eslint) — fail fast
2. Unit tests (pytest tests/test_imm16_*.py) — < 60s
3. Integration tests (workflow transitions) — < 120s
4. Build frontend — < 90s
5. E2E smoke (Playwright critical paths) — < 180s
6. Coverage report — warn if below target
```

---

## Phụ lục: Mapping UAT → Business Rules

| UAT Scenario | Business Rule / VR | Module Doc Reference |
|---|---|---|
| UAT-IMM16-01 | BR-16-05 (change control) | `IMM-16_Functional_Specs.md §4.2` |
| UAT-IMM16-02 | VR-01 (threshold JSON) | `IMM-16_Functional_Specs.md §4.3` |
| UAT-IMM16-03 | BR-16-01 (idempotent eval) | `IMM-16_Functional_Specs.md §4.1` |
| UAT-IMM16-04 | BR-16-04 (CAPA link NC) | `IMM-16_Functional_Specs.md §4.1` |
| UAT-IMM16-05 | VR-05, VR-06, VR-12 | `IMM-16_Functional_Specs.md §4.3` |
| UAT-IMM16-06 | BR-16-03 (effectiveness re-open), VR-07 | `IMM-16_Functional_Specs.md §4.1` |
| UAT-IMM16-07 | BR-16-06 (waive), VR-04 | `IMM-16_Functional_Specs.md §4.1` |
| UAT-IMM16-08 | BR-16-04, VR-08 | `IMM-16_Functional_Specs.md §4.1` |
| UAT-IMM16-09 | BR-16-07 (scorecard immutability), VR-09 | `IMM-16_Functional_Specs.md §4.2` |
| UAT-IMM16-10 | BR-16-08 (quarterly MR gate), VR-10 | `IMM-16_Functional_Specs.md §4.2` |
| UAT-IMM16-11 | BR-16-09 (cross-module gate) | `IMM-16_Functional_Specs.md §4.2` |
| UAT-IMM16-12 | US-16-07 (heatmap drill-down) | `IMM-16_Functional_Specs.md §3` |
