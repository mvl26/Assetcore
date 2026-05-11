# IMM-02 — Testing & QA

> ⚠️ Pending implementation — Wave 2

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | QA Lead + Dev |
| Liên kết | [04 Backend Design](./04_Backend_Design.md) · [05 API Specification](./05_API_Specification.md) · [08 Deployment](./08_Deployment.md) |

---

# Phần I — Test Plan

## I.1. Test Pyramid

```
              ┌────────────┐
              │  E2E / UAT │  12 scenarios (§II)
              └─────┬──────┘
           ┌────────┴─────────┐
           │  API Integration │  10 test cases
           └────────┬─────────┘
      ┌─────────────┴────────────┐
      │  DocType Lifecycle (Int) │  6 lifecycle tests
      └─────────────┬────────────┘
  ┌────────────────┴───────────────┐
  │  Unit — Service Layer (≥ 45)   │  15 test classes
  └────────────────────────────────┘
```

## I.2. Test Classes (Unit)

| Test Class | Functions covered | File |
|---|---|---|
| `TestDraftFromPlan` | `draft_from_plan`, `_vr01_unique_per_plan_line` | `test_imm_tech_spec.py` |
| `TestSeedDefaultRequirements` | `seed_default_requirements` | `test_imm_tech_spec.py` |
| `TestVR02MandatoryMin` | `_vr02_mandatory_min_count` | `test_imm_tech_spec.py` |
| `TestVR03TestMethod` | `_vr03_test_method_present` | `test_imm_tech_spec.py` |
| `TestVR04BenchmarkMin3` | `_vr04_benchmark_min_3` | `test_imm_market_benchmark.py` |
| `TestVR05InfraCompleteness` | `_vr05_infra_completeness` | `test_imm_tech_spec.py` |
| `TestGateG01` | `validate_gate_g01` | `test_imm_tech_spec.py` |
| `TestGateG02` | `validate_gate_g02` | `test_imm_tech_spec.py` |
| `TestGateG03` | `validate_gate_g03` | `test_imm_tech_spec.py` |
| `TestGateG04` | `validate_gate_g04` | `test_imm_tech_spec.py` |
| `TestLockSpec` | `lock_spec`, `before_submit_tech_spec` | `test_imm_tech_spec.py` |
| `TestComputeLockIn` | `compute_lock_in`, DEFAULT_WEIGHTS | `test_lock_in_risk.py` |
| `TestSpecMatch` | `compute_spec_match` | `test_imm_market_benchmark.py` |
| `TestReissue` | `withdraw_spec`, `reissue_spec` | `test_imm_tech_spec.py` |
| `TestSchedulers` | `check_overdue_drafts`, `benchmark_freshness_alert` | `test_tasks_imm02.py` |

## I.3. Test Stubs (Python — FrappeTestCase Pattern)

```python
# ⚠️ Pending implementation — Wave 2
# assetcore/assetcore/doctype/imm_tech_spec/test_imm_tech_spec.py

import frappe
import unittest
from frappe.test_runner import make_test_objects
from assetcore.services.shared import ServiceError, ErrorCode


class TestDraftFromPlan(unittest.TestCase):
    """Test draft_from_plan: VR-02-01 + happy path"""

    def setUp(self):
        # Create test fixtures: IMM Procurement Plan + plan_line
        self.plan = frappe.get_doc({
            "doctype": "IMM Procurement Plan",
            "plan_name": "Test Plan 2026",
            "fiscal_year": "2026",
        })
        self.plan.insert()

    def test_draft_creates_spec_for_each_line(self):
        """Happy path: draft_from_plan tạo spec cho mỗi plan_line"""
        pass  # ⚠️ Pending implementation

    def test_vr01_duplicate_plan_line_raises(self):
        """VR-02-01: plan_line đã có Active spec → raise DUPLICATE"""
        from assetcore.services.imm02 import draft_from_plan
        # Create first spec
        pass  # ⚠️ Pending implementation
        with self.assertRaises(ServiceError) as ctx:
            draft_from_plan(self.plan.name, ["L1"])
        self.assertEqual(ctx.exception.code, ErrorCode.DUPLICATE)

    def test_seeds_requirements_from_template(self):
        """seed_default_requirements: requirements pre-filled từ template"""
        pass  # ⚠️ Pending implementation


class TestGateG01(unittest.TestCase):
    """Test validate_gate_g01: ≥ 8 mandatory + 100% test_method"""

    def test_gate_g01_passes_with_8_mandatory(self):
        """G01 pass: 8 mandatory requirements đủ test_method"""
        pass  # ⚠️ Pending implementation

    def test_gate_g01_fails_mandatory_count_less_than_8(self):
        """G01 fail: 6 mandatory → raise BUSINESS_RULE"""
        from assetcore.services.imm02 import validate_gate_g01
        doc = frappe.new_doc("IMM Tech Spec")
        # Add 6 mandatory requirements
        pass  # ⚠️ Pending implementation
        with self.assertRaises(ServiceError) as ctx:
            validate_gate_g01(doc)
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("G01", str(ctx.exception))

    def test_gate_g01_fails_missing_test_method(self):
        """G01 fail: 8 mandatory nhưng 1 thiếu test_method → raise BUSINESS_RULE"""
        pass  # ⚠️ Pending implementation


class TestComputeLockIn(unittest.TestCase):
    """Test compute_lock_in: DEFAULT_WEIGHTS + score calculation"""

    def test_compute_lock_in_correct_weights(self):
        """DEFAULT_WEIGHTS: Protocol 0.30, Consumable 0.20, Software 0.20, Parts 0.15, Service 0.15"""
        from assetcore.services.imm02 import compute_lock_in
        doc = frappe.new_doc("IMM Lock-in Risk Assessment")
        doc.append("items", {"dimension": "Protocol Standard", "score": 5})
        doc.append("items", {"dimension": "Consumable Source", "score": 3})
        doc.append("items", {"dimension": "Software License", "score": 2})
        doc.append("items", {"dimension": "Parts Source", "score": 3})
        doc.append("items", {"dimension": "Service Tooling", "score": 2})
        pass  # ⚠️ Pending implementation
        # Expected: 5×0.30 + 3×0.20 + 2×0.20 + 3×0.15 + 2×0.15 = 3.25
        self.assertAlmostEqual(doc.lock_in_score, 3.25, places=2)

    def test_compute_lock_in_all_dimensions_required(self):
        """Thiếu dimension → weighted = 0 cho dimension đó"""
        pass  # ⚠️ Pending implementation


class TestReissue(unittest.TestCase):
    """Test withdraw_spec + reissue_spec versioning chain"""

    def test_reissue_creates_new_version(self):
        """Withdrawn spec → reissue → version bump 1.0 → 2.0, parent_spec set"""
        from assetcore.services.imm02 import reissue_spec
        pass  # ⚠️ Pending implementation

    def test_reissue_only_from_withdrawn(self):
        """reissue từ Locked spec → raise BAD_STATE"""
        from assetcore.services.imm02 import reissue_spec
        pass  # ⚠️ Pending implementation
        with self.assertRaises(ServiceError) as ctx:
            reissue_spec("TS-not-withdrawn")
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)

    def test_locked_spec_cannot_be_edited(self):
        """before_save: Locked spec → frappe.throw"""
        pass  # ⚠️ Pending implementation
```

## I.4. Integration Tests — Lifecycle

| Test | Scenario | Expected |
|---|---|---|
| `test_full_lifecycle_draft_to_locked` | Draft → G01 → Reviewing → G02 → Benchmarked → G03 → Risk Assessed → Pending Approval → G04 → Locked | state=Locked, docstatus=1 |
| `test_lock_triggers_imm03` | lock_spec() | publish_realtime "imm02_spec_locked" được gọi |
| `test_lock_triggers_risk_register` | lock_in_score > threshold | IMM-10 Risk Register entry tạo |
| `test_reissue_chain` | Lock → Withdraw → Reissue × 2 | version "3.0", parent chain đúng |
| `test_audit_trail_logged_all_transitions` | Toàn bộ lifecycle | 7 IMM Audit Trail records |
| `test_immutable_locked_spec` | Save locked spec | frappe.throw raised |

## I.5. Workflow Tests

| Test | From → To | Action | Expected |
|---|---|---|---|
| `test_draft_to_reviewing_g01_pass` | Draft → Reviewing | Gửi rà soát | pass |
| `test_draft_to_reviewing_g01_fail_count` | Draft → Reviewing | Gửi rà soát | BUSINESS_RULE: mandatory < 8 |
| `test_draft_to_reviewing_g01_fail_test_method` | Draft → Reviewing | Gửi rà soát | BUSINESS_RULE: missing test_method |
| `test_reviewing_to_draft` | Reviewing → Draft | Yêu cầu chỉnh sửa | pass |
| `test_reviewing_to_benchmarked_g02_pass` | Reviewing → Benchmarked | Hoàn tất benchmark | pass |
| `test_reviewing_to_benchmarked_g02_fail` | Reviewing → Benchmarked | Hoàn tất benchmark | BUSINESS_RULE: candidates < 3 |
| `test_benchmarked_to_risk_assessed_g03_pass` | Benchmarked → Risk Assessed | Hoàn tất đánh giá rủi ro | pass |
| `test_benchmarked_to_risk_assessed_g03_fail` | Benchmarked → Risk Assessed | Hoàn tất đánh giá rủi ro | BUSINESS_RULE: infra incomplete |
| `test_pending_to_locked_g04_pass` | Pending Approval → Locked | Phê duyệt | pass |
| `test_pending_to_locked_g04_fail_high_lockin` | Pending Approval → Locked | Phê duyệt | BUSINESS_RULE: lock-in no mitigation |

## I.6. API Integration Tests

| Test | Endpoint | Scenario | Expected |
|---|---|---|---|
| `test_list_tech_specs_ok` | `list_tech_specs` | Filter by state | 200, success=true, items[] |
| `test_draft_from_plan_ok` | `draft_from_plan` | 3 plan_lines | created: 3 specs |
| `test_draft_from_plan_vr01` | `draft_from_plan` | plan_line trùng | success=true, skipped=[1 item] |
| `test_add_requirement_ok` | `add_requirement` | mandatory + test_method | success=true, total_mandatory++ |
| `test_bulk_import_ok` | `bulk_import_requirements` | Excel 25 rows | imported=25 |
| `test_submit_benchmark_ok` | `submit_benchmark` | 3 candidates | benchmark_name, recommended_candidate set |
| `test_submit_benchmark_fail_vr04` | `submit_benchmark` | 2 candidates | success=false, code=VALIDATION |
| `test_submit_lock_in_ok` | `submit_lock_in_assessment` | 5 dimensions | lock_in_score correct |
| `test_lock_spec_ok` | `lock_spec` | Pending Approval spec | success=true, state=Locked |
| `test_reissue_spec_ok` | `reissue_spec` | Withdrawn spec | new_spec, version=2.0 |

## I.7. Coverage Gate

| Layer | Tool | Target |
|---|---|---|
| Python (services + api) | coverage.py | ≥ 85% line coverage |
| Python (DocType controllers) | coverage.py | ≥ 80% |
| TypeScript (store + API layer) | vitest | ≥ 75% |
| E2E (UAT critical paths) | Playwright | 12 scenarios pass |

---

# Phần II — UAT Scenarios

| ID | Actor | Pre-condition | Steps | Expected | BRs covered |
|---|---|---|---|---|---|
| UAT-IMM02-01 | HTM Engineer | PP Approved, plan_line có Device Model với template | Click "Generate Tech Spec Drafts" | 5 spec tạo, requirements seeded từ template | BR-02-01, BR-02-02 |
| UAT-IMM02-02 | HTM Engineer | Tech Spec ở Draft, 6 mandatory requirements | Thêm 2 mandatory + test_method → Gửi rà soát | G01 pass, state = Reviewing | BR-02-02, BR-02-03 |
| UAT-IMM02-03 | HTM Engineer | Draft, 8 mandatory nhưng 1 thiếu test_method | Click "Gửi rà soát" | G01 fail: "Cần phương pháp kiểm tra cho yêu cầu bắt buộc: X" | BR-02-03 |
| UAT-IMM02-04 | KH-TC Officer | Spec ở Reviewing | Nhập 3 candidates đủ spec_match + price → Hoàn tất benchmark | G02 pass, state = Benchmarked, recommended_candidate set | BR-02-04 |
| UAT-IMM02-05 | KH-TC Officer | Spec ở Reviewing | Nhập 2 candidates → Hoàn tất benchmark | G02 fail: "Cần ≥ 3 ứng viên so sánh" | BR-02-04 |
| UAT-IMM02-06 | QA Risk Team | Spec ở Benchmarked | Điền 6 mục Infra Compat + nhập 5 chiều Lock-in → Hoàn tất đánh giá | G03 pass, state = Risk Assessed, lock_in_score hiển thị | BR-02-05 |
| UAT-IMM02-07 | QA Risk Team | Spec ở Benchmarked, chỉ 5 mục Infra | Click "Hoàn tất đánh giá" | G03 fail: "Chưa đánh giá mục HVAC" | BR-02-05 |
| UAT-IMM02-08 | VP Block1 | Spec ở Pending Approval, lock_in_score = 4.2 (> 3.5), không có mitigation | Click "Phê duyệt" | G04 fail: "Nguy cơ lock-in cao, cần kế hoạch giảm thiểu" | BR-02-06 |
| UAT-IMM02-09 | VP Block1 | Spec ở Pending Approval, lock_in_score = 4.2, có mitigation_plan + evidence | Click "Phê duyệt" | Locked thành công, IMM-03 triggered | BR-02-06 |
| UAT-IMM02-10 | HTM Engineer | Spec ở Locked | Cố sửa requirement | Hệ thống từ chối: "Spec đã Locked không thể sửa" | BR-02-07 |
| UAT-IMM02-11 | VP Block1 | Spec ở Locked | Rút spec, nhập lý do | Spec = Withdrawn, lý do ghi nhận | BR-02-07 |
| UAT-IMM02-12 | HTM Engineer | Spec ở Withdrawn | Click "Reissue" | Spec mới v2.0 tạo, parent_spec = spec cũ, state = Draft | BR-02-07 |

---

# Phần III — Security

## III.1. STRIDE Threat Model

| Threat | Category | Scenario | Mitigation |
|---|---|---|---|
| T01 | Spoofing | Session hijack để tạo Tech Spec giả | Frappe session + SameSite cookie; API key for integrations |
| T02 | Tampering | Sửa lock_in_score sau khi assess | Permlevel 1: chỉ QA Risk / VP Block1 / Admin ghi; auto-compute tại service layer |
| T03 | Tampering | Submit spec không qua gate | Service layer enforce gates trước mọi transition; unit test gate bypass |
| T04 | Information Disclosure | HTM Engineer xem lock_in_score | Permlevel 1 fields chỉ trả về nếu user có role QA Risk / VP Block1 / Admin |
| T05 | Denial of Service | Bulk import Excel 10,000 rows gây timeout | Max 200 rows per import; file size limit 5MB; rate limit API |
| T06 | Elevation of Privilege | Planning Officer cố Lock spec | Workflow transition check role trước mỗi action |
| T07 | Repudiation | Ai đã Lock spec? Không trace được | IMM Audit Trail immutable: mọi transition ghi actor + timestamp + hash |

## III.2. DocPerm Matrix

### IMM Tech Spec

| Role | R | W | C | D | Submit | Amend | Permlevel 1 (lock_in_score) |
|---|---|---|---|---|---|---|---|
| IMM HTM Engineer | ✅ | ✅ (Draft/Reviewing only) | ✅ | ❌ | ❌ | ❌ | ❌ |
| IMM Planning Officer | ✅ | ✅ (Benchmark fields) | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Risk Officer | ✅ | ✅ (Infra/Lock-in fields) | ❌ | ❌ | ❌ | ❌ | ✅ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| IMM Board Approver | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### IMM Market Benchmark

| Role | R | W | C | Submit |
|---|---|---|---|---|
| IMM HTM Engineer | ✅ | ✅ | ✅ | ❌ |
| IMM Planning Officer | ✅ | ✅ | ✅ | ✅ |
| IMM Risk Officer | ✅ | ❌ | ❌ | ❌ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ |
| IMM Board Approver | ✅ | ❌ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ |

### IMM Lock-in Risk Assessment

| Role | R (permlevel 0) | R (permlevel 1: score) | W | C | Submit |
|---|---|---|---|---|---|
| IMM HTM Engineer | ✅ | ❌ | ❌ | ❌ | ❌ |
| IMM Planning Officer | ✅ | ❌ | ❌ | ❌ | ❌ |
| IMM Risk Officer | ✅ | ✅ | ✅ | ✅ | ✅ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ | ❌ |
| IMM Board Approver | ✅ | ✅ | ❌ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ | ✅ |

## III.3. Permlevel Security Test

```python
# ⚠️ Pending implementation — Wave 2
def test_lock_in_score_hidden_from_htm_engineer():
    """HTM Engineer không thấy lock_in_score (permlevel 1)"""
    # Login as HTM Engineer
    # GET get_tech_spec?name=TS-26-00045
    # Assert: response.data không có lock_in_score field
    pass

def test_lock_in_score_visible_to_risk_officer():
    """QA Risk Officer thấy lock_in_score"""
    # Login as IMM Risk Officer
    # GET get_tech_spec?name=TS-26-00045
    # Assert: response.data.lock_in_score is not None
    pass
```

## III.4. API Security Checklist

- [ ] Rate limit: `draft_from_plan` tối đa 10 requests/minute/user
- [ ] Rate limit: `bulk_import_requirements` tối đa 5 requests/minute/user
- [ ] File upload: max 5MB, chỉ accept `.xlsx`, `.xls`, `.csv`
- [ ] Whitelist: tất cả endpoint phải có `@frappe.whitelist()`
- [ ] Input validation: name fields sanitized (no SQL injection)
- [ ] Permlevel: response filter theo permlevel user trước khi trả về
- [ ] CSRF: Frappe CSRF token trên mọi POST

---

# Phần IV — Code Quality Targets

| Metric | Tool | Target | Ghi chú |
|---|---|---|---|
| Line coverage (Python) | coverage.py | ≥ 85% | Service + API layer |
| Cyclomatic complexity | SonarQube | ≤ 10 per function | Alert nếu vượt |
| Code duplicates | SonarQube | < 5% | |
| TypeScript strict | tsc --strict | 0 errors | |
| Bundle size (imm02) | Vite bundle analyzer | ≤ 120 KB gzipped | |
| Lighthouse score | Lighthouse CI | ≥ 85 (Performance) | TechSpecDetail page |
| ESLint | ESLint + Vue plugin | 0 errors | Warnings cho phép |
| Python lint | ruff + black | 0 errors | Black formatting enforced |
| API response time | k6 | p95 < 1.5s @ 50 concurrent | list_tech_specs |
| Bulk import time | k6 | < 10s @ 100 rows | bulk_import_requirements |
