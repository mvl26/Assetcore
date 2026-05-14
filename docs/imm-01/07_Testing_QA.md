# 07 — Kiểm thử & An ninh — IMM-01 Đánh giá Nhu cầu & Dự toán

> **Wave 2 — Live.** Test suite hiện tại: `assetcore/tests/test_imm01.py` (123 LOC) — cover scoring formula & priority classification thuần. Các test class còn lại trong tài liệu này (lifecycle, gates, workflow, API, security) là **roadmap** chưa implement.

| Mục | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Phiên bản | 0.1.0 |
| Cập nhật | 2026-05-14 |
| Owner | QA Lead + Tech Lead |
| Liên kết | [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) |

---

# Phần I — Test Plan

## I.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │  ← Playwright; Golden scenario Draft → Approved → Plan
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │  ← pytest + @frappe.whitelist
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │  ← pytest FrappeTestCase
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │  ← TDD; bulk test ở đây
     ─┴────────────────────────────────────────────┴─
```

Mọi service function phải có test trước khi code (TDD — CLAUDE.md §17). Mỗi BR (BR-01-01 → BR-01-08) và Gate (G01 → G05) phải có ≥ 1 happy + 1 negative test.

## I.2. Unit Test — Service Layer

**File hiện có:** `assetcore/tests/test_imm01.py` (123 LOC).

| Test class | Status | Function cover | Cases hiện có |
|---|---|---|---|
| `TestPriorityClassification` | ✅ Live | `_classify_priority()` | P1/P2/P3/P4 thresholds + zero/negative |
| `TestComputePriorityScore` | ✅ Live | `_compute_priority_score()` | all-max → 5.0/P1; all-zero → 0.0/None |
| `TestTargetYear` | ⬜ Planned | `_vr04_target_year()` | happy(current+1), fail(current-1) |
| `TestUniqueActiveRequest` | ⬜ Planned | `_vr01_unique_active_request_per_asset()` | happy/fail duplicate |
| `TestReplacementDecomPlan` | ⬜ Planned | `_vr02_replacement_requires_decom_plan()` | hiện soft warn — test msgprint emit |
| `TestScoreConsistency` | ⬜ Planned | `_vr05_score_consistency()` | sai số > 0.01 → VALIDATION |
| `TestGateG01..G05` | ⬜ Planned | `_validate_gate_g01..g05` | per gate happy/fail |
| `TestRollIntoPlan` | ⬜ Planned | `roll_into_plan()` | tạo mới plan, append, reject non-Approved NR |
| `TestDemandForecast` | ⬜ Planned | `generate_demand_forecast()` | skeleton record per category |
| `TestOverdueCheck` | ⬜ Planned | `check_pending_request_overdue()` | 30d+ NR → log |

**Pattern hiện có** (trích từ `test_imm01.py`):

```python
# assetcore/tests/test_imm01.py — actual file
import unittest
from types import SimpleNamespace
from assetcore.services.imm01 import (
    DEFAULT_PRIORITY_WEIGHTS, _classify_priority, _compute_priority_score,
)

class TestPriorityClassification(unittest.TestCase):
    def test_p1_threshold(self):
        self.assertEqual(_classify_priority(4.0), "P1")
        # ...

class TestComputePriorityScore(unittest.TestCase):
    def test_all_max_yields_5(self):
        doc = _make_doc([
            {"criterion": k, "score": 5, "weight_pct": None, "weighted": None}
            for k in DEFAULT_PRIORITY_WEIGHTS
        ])
        _compute_priority_score(doc)
        self.assertEqual(doc.weighted_score, 5.0)
        self.assertEqual(doc.priority_class, "P1")
```

> Run: `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm01`. Test sử dụng `SimpleNamespace` (không DB), an toàn chạy offline.

## I.3. Integration Test — DocType Lifecycle (planned)

**File (roadmap):** `assetcore/tests/test_imm_needs_request_doctype.py` — chưa tạo.

| Test | Setup | Action | Assert |
|---|---|---|---|
| `test_before_insert_sets_request_date` | Draft NR | `doc.insert()` | `request_date == today()` |
| `test_validate_vr03_fail_short_justification` | NR, justification 50 chars | `doc.insert()` | `ValidationError` |
| `test_validate_vr02_replacement_no_decom` | Replacement, no Decom Plan | `doc.insert()` | `ValidationError` |
| `test_submit_sets_docstatus_1` | NR ở Pending Approval, G05 pass | `doc.submit()` | `docstatus == 1`, `workflow_state == "Approved"` |
| `test_on_submit_creates_audit_trail` | NR approved | `doc.submit()` | `IMM Audit Trail` record exists |
| `test_roll_into_plan_creates_plan` | 3 Approved NR | `roll_into_procurement_plan()` | `IMM Procurement Plan` tạo; plan_items sorted by score desc |

## I.4. Workflow Tests (planned)

**File (roadmap):** `assetcore/tests/test_imm01_workflow.py` — chưa tạo.

| Transition | From → To | Role required | Test |
|---|---|---|---|
| Gửi đề xuất | Draft → Submitted | IMM Clinical User | pass + fail(wrong role) + fail(G01 missing util) |
| Tiếp nhận rà soát | Submitted → Reviewing | IMM HTM Engineer | pass |
| Yêu cầu bổ sung | Submitted → Draft | IMM HTM Engineer | pass |
| Hoàn tất chấm điểm | Reviewing → Prioritized | IMM Planning Officer | pass + fail(G02: 5/6 rows) |
| Bác sớm | Reviewing → Rejected | IMM Department Head | pass + fail(wrong role) |
| Lập dự toán xong | Prioritized → Budgeted | IMM Finance Officer | pass + fail(G03: no OPEX) |
| Trình BGĐ | Budgeted → Pending Approval | IMM Department Head | pass |
| Phê duyệt | Pending Approval → Approved | IMM Board Approver | pass + fail(G05: no funding_source) |
| Từ chối | Pending Approval → Rejected | IMM Board Approver | pass + fail(no rejection_reason) |
| Yêu cầu chỉnh dự toán | Pending Approval → Budgeted | IMM Board Approver | pass |

## I.5. API Tests (planned)

**File (roadmap):** `assetcore/tests/test_imm01_api.py` — chưa tạo.

| Test | Endpoint | Verify |
|---|---|---|
| `test_list_default_pagination` | `list_needs_requests` | `success=true`, `total ≥ 0`, `page=1` |
| `test_list_filter_state` | `list_needs_requests?workflow_state=Submitted` | Mọi item `workflow_state == Submitted` |
| `test_get_existing` | `get_needs_request?name=NR-…` | `success=true`, fields đầy đủ |
| `test_get_not_found` | `get_needs_request?name=FAKE` | `success=false`, `code=NOT_FOUND` |
| `test_create_happy` | `create_needs_request` | `success=true`, name format `NR-…` |
| `test_create_vr03_fail` | short justification | `success=false`, `code=VALIDATION` |
| `test_create_no_permission` | non-clinical role | `success=false`, `code=FORBIDDEN` |
| `test_score_compute` | `score_needs_request` 6 rows | `weighted_score=4.30`, `priority_class=P1` |
| `test_approve_g05_fail` | missing funding_source | `success=false`, `code=BUSINESS_RULE` |
| `test_dashboard_kpis_format` | `dashboard_kpis?period=2026-Q2` | 6 KPI keys present |

## I.6. Coverage Gate

| Layer | Coverage target | Đo |
|---|---|---|
| Service (`services/imm01.py`) | ≥ 85% | `coverage report` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm01.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | Không crash build | CI `npm run build` |

---

# Phần II — UAT Scenarios

## II.1. Pre-conditions

- UAT site: `uat.assetcore.vn` đã deploy Wave 2 build
- Master data seeded: `IMM Device Model`, `Department`, scoring weights
- Test users đã tạo (xem §II.2)
- Browser: Chrome ≥ 120 hoặc Edge ≥ 120

## II.2. Test Users

| Username | Role | Vai trò UAT |
|---|---|---|
| `head.icu@hospital.vn` | IMM Clinical User (head subset) | Tạo NR, Submit |
| `htm.reviewer@hospital.vn` | IMM HTM Engineer | Review, Score |
| `khtc@hospital.vn` | IMM Planning Officer | Chấm điểm, tạo Plan |
| `tckt@hospital.vn` | IMM Finance Officer | Budget Estimate |
| `ptp.k1@hospital.vn` | IMM Department Head | Trình BGĐ |
| `vp.block1@hospital.vn` | IMM Board Approver | Approve/Reject |
| `cmms.admin@hospital.vn` | IMM System Admin | Override |

## II.3. UAT Scenarios

| ID | Actor | Pre-condition | Steps | Kết quả mong đợi | BR cover |
|---|---|---|---|---|---|
| UAT-IMM01-01 | Clinical Head | IMM Device Model tồn tại | Tạo NR type=New, fill đủ (justification ≥ 200 chars), Submit | NR ở Submitted; ALE "Submitted" ghi; email gửi PTP + KH-TC | BR-01-01 |
| UAT-IMM01-02 | Clinical Head | Không có Decommission Plan | Tạo NR type=Replacement, replacement_for_asset không có plan, Submit | VR-01-02 throw; không tạo NR | BR-01-08 |
| UAT-IMM01-03 | Clinical Head | Asset có Decommission Plan Pending | Tạo NR type=Replacement, gắn asset, Submit | NR tạo thành công, utilization auto-fetch từ IMM-07 | BR-01-08, BR-01-02 |
| UAT-IMM01-04 | HTM Reviewer | NR ở Reviewing | Chấm 6 tiêu chí, submit score | weighted_score=4.30, P1 hiển thị; ALE ghi | BR-01-04 |
| UAT-IMM01-05 | HTM Reviewer | NR ở Reviewing | Chấm chỉ 5/6 tiêu chí, click "Hoàn tất chấm điểm" | G02 fail "Cần đủ 6/6 tiêu chí" | BR-01-04 |
| UAT-IMM01-06 | TCKT Officer | NR ở Prioritized | Nhập 5 CAPEX + 5×OPEX lines, set funding_source=NSNN | total_capex, total_opex_5y, tco_5y compute đúng; state Budgeted | BR-01-05 |
| UAT-IMM01-07 | TCKT Officer | NR ở Prioritized | Nhập CAPEX nhưng bỏ OPEX Year 4 | G03 fail "Budget Estimate phải có CAPEX + OPEX 5 năm" | BR-01-05 |
| UAT-IMM01-08 | PTP Khối 1 | NR ở Budgeted | Click "Trình BGĐ" | state Pending Approval; email VP Block1 | — |
| UAT-IMM01-09 | VP Block1 | NR ở Pending Approval, funding_source set | Nhập board_approver=self, click "Phê duyệt" | docstatus=1, state Approved; ALE "Approved" ghi | BR-01-07 |
| UAT-IMM01-10 | VP Block1 | NR ở Pending Approval | Nhấn "Từ chối" không nhập rejection_reason | VALIDATION throw; NR không chuyển state | — |
| UAT-IMM01-11 | KH-TC Officer | 3 NR Approved | Gom vào Plan PP-26-001 qua `roll_into_plan` | Plan tạo, plan_items sort by weighted_score desc; NR.procurement_plan link set | BR-01-06 |
| UAT-IMM01-12 | KH-TC Officer | Plan PP-26-001 tồn tại | Click "Generate IMM-02 Tech Spec Drafts" | 3 Tech Spec Draft tạo (IMM-02); NR.tech_spec_ref link set | — |

## II.4. Acceptance

- ≥ 95% PASS để release Wave 2
- 0 Blocker, ≤ 2 High open (có workaround)
- Audit trail 100% mọi state change

---

# Phần III — Security Review

## III.1. RBAC

### DocPerm Matrix — `IMM Needs Request`

| Role | Read | Write | Create | Submit | Cancel | Amend | Delete |
|---|---|---|---|---|---|---|---|
| IMM Clinical User | ✅ (own dept) | ✅ (own, Draft) | ✅ | ❌ | ❌ | ❌ | ❌ |
| IMM HTM Engineer | ✅ | ✅ (Reviewing) | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Planning Officer | ✅ | ✅ (Prioritized) | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Finance Officer | ✅ | ✅ (Budgeted) | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Department Head | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| IMM Board Approver | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### DocPerm Matrix — `IMM Procurement Plan`

| Role | Read | Write | Create | Submit | Cancel |
|---|---|---|---|---|---|
| IMM Planning Officer | ✅ | ✅ | ✅ | ❌ | ❌ |
| IMM Department Head | ✅ | ✅ | ❌ | ✅ | ✅ |
| IMM Board Approver | ✅ | ❌ | ❌ | ✅ | ✅ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ | ✅ |

## III.2. STRIDE Threat Model

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Spoofing | Giả mạo Clinical Head submit NR của khoa khác | Low | High | `permission_query_conditions` filter by department |
| Tampering — Audit | Sửa IMM Audit Trail record để thay đổi lịch sử phê duyệt | Low | Critical | DocPerm no-delete + no-write; IMM Audit Trail là IMM-00 shared DocType có bảo vệ tập trung |
| Tampering — Score | KH-TC Officer chỉnh weighted_score bỏ qua compute | Medium | High | VR-01-05 server-side recompute; permlevel 0 = read-only cho weighted_score |
| Repudiation | VP Block1 phủ nhận đã Approve | Low | High | IMM Audit Trail ghi actor + timestamp + IP; ALE immutable |
| Info Disclosure | Department User xem NR khoa khác | Low | Medium | `permission_query_conditions`: filter by requesting_department = user.department |
| DoS — Demand Forecast | Scheduler generate_demand_forecast lock DB với big query | Low | Medium | Batch 200 records/run + index `idx_df_year_cat`; chạy 02:30 ngoài giờ cao điểm |
| Elevation of Privilege | TCKT Officer tự Approve NR (bypass VP) | Low | Critical | Workflow role check: IMM Board Approver only; `before_submit` validate role |

## III.3. API Security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ✅ | Mọi `@frappe.whitelist()` có docstring + required role check |
| CSRF | ✅ | Frappe default X-Frappe-CSRF-Token |
| Input validation | ✅ | `name` field validate qua `frappe.get_value` trước khi dùng |
| SQL injection | ✅ | Frappe ORM parameterized; không raw SQL |
| Rate limit | ⚠️ Roadmap | Cần cấu hình cho `create_needs_request`, `approve_needs_request` |
| Permlevel 1 | ✅ | funding_source, funding_evidence, board_approver chỉ TCKT + PTP + VP |

## III.4. Row-level Permission (planned)

> Hiện chưa có `permission_query_conditions` cho `IMM Needs Request` trong `hooks.py`. DocPerm cấp module-wide (xem 04 §II.1). Roadmap snippet:

```python
# assetcore/permissions.py  ⬜ Planned
def needs_request_query(user):
    """Department User chỉ thấy NR của khoa mình."""
    if frappe.has_role("IMM Department Head", user) or \
       frappe.has_role("IMM HTM Engineer", user) or \
       frappe.has_role("IMM System Admin", user):
        return ""  # See all
    dept = frappe.db.get_value("Employee", {"user_id": user}, "department")
    return f"(`tabIMM Needs Request`.requesting_department = '{dept}')"
```

---

# Phần IV — Chất lượng mã nguồn

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, smell ≤ 5, duplication ≤ 3%, coverage ≥ 70% | Quality Gate pass | Mỗi PR |
| **Lighthouse** (FE — Imm01Dashboard) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90 | ≥ target | Mỗi release |
| **ESLint + vue-tsc** | 0 error, 0 warning production build | pass | Mỗi PR FE |
| **ruff / black** (BE) | 0 error, format chuẩn PEP8 | pass | Mỗi PR |
| **Bundle size** (FE chunk imm01) | main chunk ≤ 250 KB gzip | ≤ budget | Mỗi PR FE |
