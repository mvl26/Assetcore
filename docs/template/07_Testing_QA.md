# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-`<XX>` |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Q3 là gate go-live.

> **Quy ước nhãn trong tài liệu này**:
> - `**Viết gì**:` mô tả ngắn nội dung cần điền cho section
> - `**Kỹ thuật**:` (khi áp dụng) kỹ thuật thiết kế test sử dụng — vd `BVA`, `EP`, `Decision Table`, `State Transition`, `Use Case`
> - `**Trace**:` liên kết section/bảng cụ thể trong file 02/03/04/05/06
> - `**Mẹo**:` gợi ý thực hành

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

**Viết gì**: Liệt kê toàn bộ artefact test được của module thành 1 bảng. Đây là input chính cho test scope. Mỗi dòng → ≥ 1 test class ở Phần III. Không bỏ sót artefact (sót = lỗ hổng coverage).

**Trace**: 04 Backend §DocType + §Service + §Hook · 05 API §Catalog · 06 Frontend §Components + §Views

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `<…>` | DocType | `<doctype>.json` | Integration (lifecycle) |
| 2 | `<…>` | Workflow | `workflow/<…>.json` | Integration (state transition) |
| 3 | `<…>` | Service function | `services/imm<XX>.py::<fn>` | Unit |
| 4 | `<…>` | Validator | `services/imm<XX>.py::_vr*`, `_validate_gate_*` | Unit (BVA/EP/Decision Table) |
| 5 | `<…>` | Repository / DAO | `repository/<…>.py` | Integration (DB) |
| 6 | `<…>` | API endpoint | `api/imm<XX>.py::<endpoint>` | API integration |
| 7 | `<…>` | Lifecycle event | `hooks.py → events::<…>` | Integration (audit chain) |
| 8 | `<…>` | Scheduler job | `services/imm<XX>.py::<cron_fn>` | Unit + Cron simulation |
| 9 | `<…>` | FE view / composable | `frontend/src/views/<…>.vue` | E2E (Playwright) |
| 10 | `<…>` | Pinia store | `frontend/src/stores/<…>.ts` | Unit (vitest) |

**Mẹo**: chạy `grep -rn "^def\|^class" assetcore/services/imm<XX>.py` để tự liệt kê service functions; chạy `grep -rn "@frappe.whitelist" assetcore/api/imm<XX>.py` để liệt kê endpoint.

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

**Viết gì**: 3 bảng dẫn từ artefact phân tích (file 02) sang test layer. Mỗi User Story/BR/Activity phải có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV. Không có dòng nào "không cover".

**Trace**: 02 §Functional Specs (US + AC) · 02 §Business Rules · 02 §Activity Diagram per UC

### I.2.a. Từ User Story
| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-`<XX>-NN` | `<…>` | AC1, AC2, … | Unit + API + UAT |

### I.2.b. Từ Business Rule
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-`<XX>-NN` | `<…>` | `<…>` | Decision Table / BVA / EP |

### I.2.c. Từ Activity Flow / BPMN
| Activity ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| ACT-`<XX>-NN` | UC-`<…>` | Happy path | Exception X, Y |

**Mẹo**: 1 BR thường sinh ra 1 nhóm test (1 happy + N negative). 1 Activity branch = 1 path test trong State Transition.

## I.3. Risk-based Priority

**Viết gì**: Bảng đánh giá rủi ro cho từng component ở I.1. Test case priority phải khớp risk: Critical/High = bắt buộc cover trong sprint; Medium/Low = best-effort.

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| `<…>` | 4 | 5 | 20 | **Critical** |
| `<…>` | 2 | 3 | 6 | Medium |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

**Mẹo**: workflow approval gate, money flow, audit trail thường = Critical. Dashboard read-only thường = Low.

## I.4. Scope

**Viết gì**:
- **In-scope**: liệt kê 3-5 điểm theo Component Inventory (I.1)
- **Out-of-scope**: liệt kê + nêu lý do (vd "Performance test giao cho Phần III.6", "Cross-module với IMM-`<YY>` chỉ smoke")
- **Assumptions**: master data đã seed, test users đã tạo, browser version, …

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mục tiêu Phần II: chọn đúng kỹ thuật cho từng loại input/logic. Không "vẽ test cho có" — mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

**Viết gì**: Bảng chọn kỹ thuật. Mỗi dòng phải ghi rõ áp dụng vào component nào (link tới I.1).

| Kỹ thuật | Khi nào dùng | Áp dụng vào AssetCore | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm tương đương | DocType `Select` options, `Link` field, request_type, status enum | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date / length field có biên | `target_year`, `qty`, `unit_cost`, `clinical_justification` length, `tco_5y` | 2-3 test/biên: min-1, min, min+1 |
| **Decision Table** | Multi-condition gate, business rule kết hợp | Gates G01..G05, validator có ≥ 2 điều kiện AND/OR | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | Mỗi workflow JSON (Draft → Submitted → … → Approved/Rejected) | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios, API integration test | 1/main flow + 1/alt flow + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | Form tạo Needs Request (request_type × funding_source × …) | Min set cover all pairs |
| **Error Guessing** | Lỗi từ kinh nghiệm: null, empty, unicode, race | Tất cả endpoint nhận user input | Bổ sung — không thay thế kỹ thuật khác |

## II.2. White-box techniques

**Viết gì**: Bảng coverage criteria + cách đo. Mỗi kỹ thuật phải nêu công cụ thực thi.

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions ở I.1 | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Functions có if/else, try/except, while | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | Gates phức hợp (G01..G05), validator multi-AND | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | Critical service function ≤ 20 LOC | Toàn bộ path khả dĩ (loop = 0,1,N) | Manual |

**Mẹo**: ưu tiên Branch coverage cho service layer; MC/DC chỉ áp dụng vào gate logic (số test = N+1 với N condition độc lập).

## II.3. Mapping Component → Kỹ thuật

**Viết gì**: Bảng quyết định — với mỗi loại component ở I.1, kỹ thuật mặc định là gì.

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`_vr*`) | BVA + EP | Error guessing |
| Gate logic (`_validate_gate_*`) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Service function pure | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (form input) |
| Scheduler / cron | Use Case (state setup → run → assert) | Error guessing (lock, partial fail) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

**Viết gì**: Sơ đồ 4 tầng + tỷ lệ test dự kiến. Phần lớn test ở Service unit; ít test ở E2E. Khớp số liệu thực ở III.2-III.5.

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15%
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25%
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55%
     ─┴────────────────────────────────────────────┴─
```

**Trace**: CLAUDE.md §17 (TDD mandatory).

## III.2. Unit test — Service Layer

**Viết gì**: File `tests/test_imm<XX>.py`. Bảng `Test class · Function cover · Kỹ thuật (II.1/II.2) · Số case`. Mỗi test class trace về ≥ 1 dòng I.1.

| Test class | Function cover | Kỹ thuật | Cases (happy/negative) |
|---|---|---|---|
| `Test<…>` | `services/imm<XX>.py::<fn>` | EP + BVA | 3 / 2 |

**Mẹo**: dùng `SimpleNamespace` cho test thuần công thức (không DB) — chạy ms-level, không cần fixture cleanup.

## III.3. Integration — DocType lifecycle

**Viết gì**: File `tests/test_<doctype>_doctype.py`. Cover hook `validate / before_save / on_submit / on_update_after_submit / on_cancel`.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| `<…>` | `<seed fixture>` | `doc.insert()` | `<field> == <…>` | EP |

**Mẹo**: fixture trong `setUpClass` phải có `tearDownClass` purge — xem `assetcore-test` LL-TEST-17.

## III.4. Integration — Workflow transitions

**Viết gì**: File `tests/test_imm<XX>_workflow.py`. **Bắt buộc** cover mọi transition trong workflow JSON (đếm bằng `python3 -c "import json; print(len(json.load(open('<…>.json'))['transitions']))"`).

| Transition | From → To | Role required | Test pass | Test fail (wrong role / gate fail) |
|---|---|---|---|---|
| `<action>` | `<S1>` → `<S2>` | `<role>` | ☐ | ☐ |

**Kỹ thuật**: State Transition Testing — vẽ state graph; mỗi edge = 1 test pass + 1 test fail.

## III.5. Integration — Audit chain integrity

**Viết gì**: 2 test chính:
- (a) Sau N mutation, chain hash SHA-256 hợp lệ end-to-end
- (b) Khi 1 entry bị tamper (sửa `change_summary`), verify endpoint trả `chain_broken=true`

**Trace**: 04 Backend §Audit Trail · `IMM Audit Trail` DocType.

## III.6. API test

**Viết gì**: File `tests/test_imm<XX>_api.py`. Bảng `Test · Endpoint · Verify`. Cover:
- Happy path + envelope `success=true`
- Invalid params → `code=INVALID_PARAMS`
- No permission → `code=FORBIDDEN`
- Pagination (page, page_size boundaries)
- Idempotent retry (POST cùng payload 2 lần)

| Test | Endpoint | Verify | Kỹ thuật |
|---|---|---|---|
| `<…>` | `api/imm<XX>.<fn>` | `success=true`, field X | Use Case |
| `<…>` | `api/imm<XX>.<fn>` (low-role) | `code=FORBIDDEN` | EP (permission partition) |

## III.7. E2E browser (Playwright)

**Viết gì**: Khi nào dùng — flow UI khó cover bằng API: dropdown cascade, modal confirm, workflow button visibility theo role.

**Trace**: `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules).

## III.8. Performance test

**Viết gì**: Bảng `Metric · Target · Test method`. Tool **k6** hoặc `pytest-benchmark`.

| Metric | Target | Method |
|---|---|---|
| List 200 row p95 | ≤ 400ms | k6 GET `<endpoint>` |
| Create endpoint p95 | ≤ 600ms | k6 POST batch |
| Scheduler N record | ≤ 5min/1000 record | `time bench execute …` |

## III.9. Test data & Fixtures

**Viết gì**: Bảng `Loại · Cách seed · File`.

| Loại | Cách seed | File |
|---|---|---|
| Master data (Department, Asset Category, Vendor) | `fixtures/*.json` (cài qua `bench migrate`) | `assetcore/fixtures/` |
| Test records | `test_records.json` per DocType | `<doctype>/test_records.json` |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm<XX>.py` |

**Mẹo**: UAT data phải **thực tế** (tên bệnh viện VN, mã NCC chuẩn). Backend test fixture mới dùng prefix `_Test` — xem `assetcore-test` R-0/R-1.

## III.10. Run commands & Coverage gate

**Viết gì**:
```bash
# Module test
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm<XX>
# Coverage
coverage run -m unittest assetcore.tests.test_imm<XX> && coverage report
# Workflow smoke
bench --site <site> run-tests --module assetcore.tests.guards.test_workflows
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm<XX>.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm<XX>.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

---

# Phần IV — Traceability Matrices

> 3 ma trận theo 3 hướng. Mọi test ở Phần III phải xuất hiện ở **cả 3** bảng (để audit ngược: thiếu cover US? thiếu cover BR? thiếu cover component nào?).

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-`<XX>-NN` | AC1 | `Test<…>::test_<…>` | Unit | ✅ Live / ⬜ Planned |

**DoD**: mọi US trong 02 §Functional Specs có ≥ 1 dòng. Cột Status không được trống.

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-`<XX>-NN` | `<…>` | `Test<…>` | Decision Table | 1 / 3 |

**DoD**: mọi BR có ≥ 1 happy + ≥ 1 negative test. BR Critical (I.3) phải có Decision Table đầy đủ.

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `services/imm<XX>::<fn>` | `Test<…>` | Unit | 92% | Critical |
| `api/imm<XX>::<fn>` | `Test<…>` | API | 75% | High |

**DoD**: mọi component Critical/High phải đạt coverage target III.10; component Low có thể chấp nhận < target nếu document trong cột ghi chú.

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

**Viết gì**: 3 mục con —
- **In-scope**: scenario theo US (V.4)
- **Out-of-scope**: performance (đã làm III.8), security (Phần VI)
- **Pre-condition**: site UAT deploy version `<…>`, fixture loaded, tester accounts active

## V.2. Tester accounts

**Viết gì**: Bảng `Username · Role · Vai trò UAT`. Mỗi role có 1-2 tester.

**Mẹo**: phải có account tester role thấp để cover FORBIDDEN case (không chỉ Admin).

## V.3. Test data đã seed

**Viết gì**: Bảng `DocType · Số lượng · Ghi chú`. Đủ cover happy + edge + permission scenario. Reset script đi kèm.

## V.4. UAT Scenarios — Suy ra từ US + Activity

**Viết gì**: Mỗi scenario theo template §Phụ lục A. ID `UAT-IMM<XX>-NN`.

**Quy tắc suy scenarios** (bắt buộc theo Use Case Testing):
- Mỗi US → ≥ 1 scenario happy path
- Mỗi Activity branch ngoại lệ (I.2.c) → ≥ 1 scenario
- Mỗi role có quyền mutate → ≥ 1 scenario permission verify
- Mỗi workflow terminal transition → ≥ 1 scenario verify audit + cross-module hook
- Form validation negative: ≥ 1 scenario per BR Critical

**Bảng tổng**:

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM`<XX>`-01 | `<role>` | `<…>` | US-…, BR-… | Use Case happy | `<…>` |
| UAT-IMM`<XX>`-02 | `<role>` | `<…>` | US-… AC2 negative | Use Case alt | `<…>` |

## V.5. Tổng hợp kết quả & Bug found

**Viết gì**:
- Bảng `Scenario · Status (Pass/Fail/Block) · Tester · Ngày · Ghi chú`
- Bug list: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status`
- Acceptance: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround)
- Sign-off: BA Lead + QA Lead + Module Owner + (tùy) End-user

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

**Viết gì**: 4 mục con —
- Role definitions (file `fixtures/role.json` + `role_profile.json`)
- DocPerm matrix per DocType (Read/Write/Create/Submit/Cancel/Amend/User Permission/Match field)
- Field-level permission (permlevel ≠ 0 cho field nhạy cảm: `funding_source`, `board_approver`, internal cost)
- User Permission (filter row theo department/vendor)

**Kỹ thuật**: Decision Table — mỗi (role × action × state) là 1 row, expected = Allow/Deny.

## VI.2. API security

**Viết gì**: 5 mục con —
- Whitelist hygiene (mọi `@frappe.whitelist` có docstring + `rbac.require()` + validate input)
- CSRF (Frappe default `X-Frappe-CSRF-Token`)
- Input validation (Link field validate qua `frappe.get_value` trước khi dùng)
- SQL injection (parameterized only; không f-string vào raw SQL)
- Rate limit (cho endpoint mutating: create, approve)

## VI.3. Audit trail integrity

**Viết gì**: Mọi mutation sinh `IMM Audit Trail`. Hash SHA-256 chain. Verify endpoint. Test tamper. User KHÔNG có quyền edit/delete `IMM Audit Trail` (DocPerm + `on_trash` guard ISO 13485:7.5.9).

**Trace**: III.5 test cases.

## VI.4. Authentication & session

**Viết gì**: Login Frappe default. Session timeout. Lockout. Password policy. API key rotation. 2FA roadmap.

## VI.5. Data sensitivity

**Viết gì**: Bảng `Loại · Trường · Sensitivity (Public/Internal/Confidential/Restricted) · Bảo vệ`. Khẳng định KHÔNG lưu patient data.

## VI.6. Vendor isolation

**Viết gì**: Vendor External chỉ thấy WO assigned (qua `permission_query_conditions`). KHÔNG thấy: chi phí, internal note, audit trail vendor khác, dashboard. KHÔNG export.

**Trace**: test case ở III.6 (low-role API call test).

## VI.7. Secrets management

**Viết gì**: Cấm commit `.env` / credential. `site_config.json` không lên git. External token lưu `frappe.conf`. Backup encrypt at-rest off-site.

## VI.8. Logging & monitoring

**Viết gì**: Bảng `Sự kiện · Log level · Where · Alert?`. PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

**Viết gì**: Bảng `Threat · Vector · Likelihood · Impact · Mitigation`. ≥ 6 threat — bắt buộc đủ 6 STRIDE:
- **S**poofing (giả mạo identity)
- **T**ampering (sửa data/audit)
- **R**epudiation (phủ nhận hành động)
- **I**nfo disclosure (lộ data cross-tenant)
- **D**enial of service (lock DB / N+1)
- **E**levation of privilege (low-role gọi admin endpoint)

## VI.10. Penetration test

**Viết gì**: Trước release đầu tiên: Burp/ZAP scan, sqlmap (an toàn), CSRF test, role escalation. Report lưu `docs/security/`.

## VI.11. Sign-off

**Viết gì**: Bảng `Role · Người · Ngày · Chữ ký`. Decision: Pass / Pass with conditions / Fail (block).

---

# Phần VII — Code Quality

## VII.1. Tool matrix

**Viết gì**: Bảng `Tool · Mục tiêu · Target · Cadence`. Cover:
- **SonarQube** (BE Python): bug 0 critical, code smell ≤ N, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100%
- **Lighthouse** (FE): Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80
- **ESLint + vue-tsc** (FE): 0 error, 0 warning trên prod build
- **ruff / black** (BE Python): 0 error, format consistent
- **Bundle size** (FE chunk imm`<XX>`): main ≤ 250KB gzip, async ≤ 80KB gzip

## VII.2. Cadence

**Viết gì**: Khi nào chạy:
- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail)
- Lighthouse: mỗi release lớn + monthly audit
- ESLint / ruff: mỗi PR (CI gate)
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget)

**Mẹo**: gắn screenshot SonarQube + Lighthouse vào file 09 §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM<XX>-<NN> — <Tên>

**Liên kết**: US-<NN>, AC<N>, BR-<NN>, ACT-<NN>
**Role tester**: <…>
**Kỹ thuật áp dụng**: Use Case happy / Use Case alt / EP permission / State Transition
**Mục tiêu**: <1 câu>
**Pre-condition**: <data state cần có>

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | <…> | <…> | ☐ |
| 2 | <…> | <…> | ☐ |

**Post-condition**: <data state sau khi pass>
**Acceptance**: Tất cả step Pass + audit trail có entry tương ứng.
```

# Phụ lục B — Template per Test Case (unit/integration/API)

```markdown
### TC-IMM<XX>-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `target_year=current_year-1`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=VALIDATION, message contains "VR-01-04")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM<XX>-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `<path>.json`
**Role required**: <…>
**Pre-condition**: doc.workflow_state = <from>, gate <Gx> đã pass
**Action**: apply_workflow(doc, "<action>")
**Expected (happy)**: doc.workflow_state = <to>, docstatus = <…>, audit entry created
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (gate fail)**: ServiceError(code=BUSINESS_RULE, message contains "<Gx>")
```

---

# DoD — File 07 hoàn chỉnh

## I. Test Analysis
- [ ] I.1 Component Inventory liệt kê đủ artefact (so với 04/05/06)
- [ ] I.2 mỗi US / BR / Activity có ≥ 1 dòng map
- [ ] I.3 Risk priority gán cho mọi component (không trống)
- [ ] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [ ] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition là tối thiểu)
- [ ] II.2 white-box criteria xác định (statement + branch bắt buộc)
- [ ] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [ ] Test class structure cho mọi service public function (I.1)
- [ ] ≥ 1 happy + 1 negative test mỗi function
- [ ] Workflow transitions cover 100% (đếm = JSON)
- [ ] Audit chain test (intact + tampered)
- [ ] API test ≥ 60% coverage + permission matrix
- [ ] Performance target xác định
- [ ] CI command chạy clean (`bench run-tests --module …`)
- [ ] **SonarQube Quality Gate pass** + **Lighthouse score ≥ target**

## IV. Traceability
- [ ] IV.1 US → Test: mọi US có ≥ 1 Test ID
- [ ] IV.2 BR → Test: mọi BR có happy + negative
- [ ] IV.3 Component → Test: Critical/High đạt coverage target III.10

## V. UAT
- [ ] Mỗi US có ≥ 1 UAT scenario
- [ ] ≥ 1 negative + permission + audit verify scenario
- [ ] Test data seed script chạy được
- [ ] Tester accounts đã tạo ở UAT site (đủ các role, không chỉ Admin)
- [ ] Sign-off section sẵn sàng

## VI. Security
- [ ] DocPerm matrix đầy đủ (Decision Table)
- [ ] Mọi field nhạy cảm có permlevel ≠ 0
- [ ] SQL injection + CSRF test pass
- [ ] Audit chain test pass (intact + tampered)
- [ ] Vendor isolation test pass (low-role API call)
- [ ] Threat model đủ 6 STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live

## VII. Code Quality
- [ ] SonarQube Quality Gate pass
- [ ] Lighthouse ≥ target
- [ ] Bundle size ≤ budget
- [ ] Screenshot báo cáo gắn vào file 09
