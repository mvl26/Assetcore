# 07 — Testing & QA (IMM-14 Giải nhiệm thiết bị)

| Mục | Giá trị |
|---|---|
| Module | IMM-14 — Giải nhiệm thiết bị |
| Phạm vi | Test plan + UAT script + Security review + Code quality |
| Owner | QA Lead + BA + Security Officer |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [04 Backend](./04_Backend_Design.md) |

> Test plan dạng **plan + categories** (BE chưa scaffold). Test case ID + coverage % chốt sau Sprint W3-1.

---

## I. Test plan

### I.1. Phân loại

| Loại | Phạm vi | Tool | Owner |
|---|---|---|---|
| Unit (BE) | Service / Repository / Validator | `bench --site <site> run-tests --module assetcore.tests.test_imm14` | BE Dev |
| Integration (BE) | DocType lifecycle hook + workflow + cross-module (IMM-13/05/15) | `bench run-tests` | BE Dev |
| API contract | Endpoint envelope + error code catalog | Pytest + httpx fixture | BE Dev |
| Workflow smoke | State machine `IMM Asset Closure` từ Draft → Closed → Rollback | Frappe TestCase | BE Dev |
| FE component | Vue component + Pinia action | Vitest + Vue Test Utils | FE Dev |
| FE e2e | Critical flow (create → reconcile → sanitize → finalize → rollback) | Playwright | QA |
| Security | RBAC matrix · whitelist hygiene · CSRF | Manual + script | Security Officer |
| UAT | Kịch bản nghiệp vụ thực tế bệnh viện | Test script tay | BA + QA |
| Performance | finalize P95 <2s, dashboard <3s | k6 / locust | DevOps |

### I.2. Coverage target

Theo `CONVENTIONS.md §6`: file service > 50 LOC phải đạt **≥70% line coverage**. IMM-14 service dự kiến 600–900 LOC → bắt buộc test unit cho mọi method public.

**Required unit test categories**:

- ClosureService: create_from_decision, validate_finalize, run_finalize_transaction, run_rollback (8 test mỗi method tối thiểu — happy + 7 BR fail).
- ReconciliationService: load_open_wo, load_spare_stock, mark_line_done.
- SanitizationService: load_template (theo classification A/B/C/D), sign.
- ClosureRepo: get_active, create, update_state.

### I.3. Critical scenarios (integration)

| # | Scenario | Mô tả | Expected |
|---|---|---|---|
| INT-14-01 | Happy path full | Tạo từ decision → reconcile đủ → sanitize → submit → approve → asset = decommissioned | All gates green, lifecycle event đúng |
| INT-14-02 | Block khi còn WO mở | Asset còn WO PM Open | submit_for_approval reject `IMM14_OPEN_WO` |
| INT-14-03 | Block khi sanitization thiếu | Asset có PHI, chưa ký DPO | finalize reject `IMM14_SANITIZATION_REQUIRED` |
| INT-14-04 | Block khi phụ tùng còn pending | IMM-15 còn line scope=spare_stock status=pending | submit reject `IMM14_PENDING_RECONCILE` |
| INT-14-05 | Atomic transaction | Mock IMM-05 archive fail giữa finalize | Toàn bộ rollback, asset_status không đổi |
| INT-14-06 | Duplicate closure | Tạo closure khi đã có closure active | reject `IMM14_DUPLICATE_CLOSURE` |
| INT-14-07 | SoD violation | Cùng user create + approve | reject `IMM14_SOD_VIOLATION` |
| INT-14-08 | Rollback in window | Closed 5 ngày → request rollback → confirm | Asset trở lại pending_decommission, IMM-05 unarchive |
| INT-14-09 | Rollback expired | Closed 35 ngày, window 30 | reject `IMM14_ROLLBACK_EXPIRED` |
| INT-14-10 | Asset lock | Sửa `AC Asset` đã decommissioned | reject `IMM14_ASSET_LOCKED` |

### I.4. Workflow smoke test

| State chuyển | Role | Expected |
|---|---|---|
| Draft → Reconciling | HTM Engineer | OK |
| Reconciling → Pending Approval (đủ) | HTM Engineer | OK |
| Reconciling → Pending Approval (thiếu) | HTM Engineer | Reject |
| Pending Approval → Closed | Department Head | OK + asset event |
| Pending Approval → Closed | HTM Engineer | Reject (role) |
| Closed → Rollback Requested | Department Head | OK (in window) |
| Rollback Requested → Reopened | Accountant | OK |
| Rollback Requested → Closed (reject) | Accountant | OK |

---

## II. UAT script (≥3 kịch bản)

### II.1. UAT-14-01 — Giải nhiệm asset bình thường (đầy đủ)

**Tiền điều kiện**: Asset máy đo SpO2 model X, có Decommission Decision IMM-13 đã approved, không còn WO mở, không có PHI.

**Bước**:

1. HTM Engineer login, vào `/imm-14/new`, chọn decision → tạo closure.
2. Tab Reconciliation: đóng các dòng WO (nếu có), Storekeeper xử lý phụ tùng (3 dòng, mark scrap), Accountant nhập `final_value = 0`.
3. Tab Sanitization: vì `has_patient_data=false` → bấm "Skip với note", ghi note.
4. QLCL upload biên bản huỷ + ảnh hiện trạng.
5. HTM Engineer "Submit for Approval".
6. Department Head login, mở closure, bấm Approve, gõ closure_no xác nhận.
7. Verify: asset chuyển `decommissioned` ở list IMM-04, IMM-15 stock đã hoàn 0, IMM-05 docs `archived`.

**Expected**: closure state = Closed, dashboard +1 trong tháng.

### II.2. UAT-14-02 — Giải nhiệm asset có dữ liệu bệnh nhân (sanitization bắt buộc)

**Tiền điều kiện**: Asset máy siêu âm, `has_patient_data=true`.

**Bước**:

1. Tạo closure như UAT-14-01.
2. Submit khi chưa ký sanitization → block, hiển thị `IMM14_SANITIZATION_REQUIRED`.
3. DPO login, tab Sanitization, check 8 item, ký xác nhận.
4. HTM Engineer submit lại → OK.
5. Approve → asset decommissioned, evidence sanitization có timestamp + chữ ký DPO.

**Expected**: closure report PDF có section sanitization với chữ ký DPO + thời điểm.

### II.3. UAT-14-03 — Rollback trong window

**Tiền điều kiện**: Closure UAT-14-01 đã Closed 5 ngày.

**Bước**:

1. Department Head mở closure → Request Rollback, nhập lý do "Phát hiện asset không thuộc danh sách thanh lý".
2. Accountant nhận notify, vào closure → Confirm Rollback.
3. Verify: asset_status đảo về `pending_decommission`, IMM-05 docs unarchive, lifecycle event `closure_rolled_back`.

**Expected**: closure state = Reopened, có thể tiếp tục chỉnh.

### II.4. UAT-14-04 — Migration legacy

**Tiền điều kiện**: 5 asset đã thanh lý trước go-live, có hồ sơ giấy.

**Bước**:

1. Admin chạy script `bench execute assetcore.services.imm14.migrate_legacy --kwargs '{"file":"/legacy/2024.csv"}'`.
2. Verify: 5 closure record tạo state `Closed` flag `legacy_imported=true`, asset đã decommissioned.
3. Audit có thể xuất closure report PDF.

---

## III. Security review

### III.1. RBAC matrix verify

Map từ [04 §V](./04_Backend_Design.md). QA tạo 1 user mỗi role + thử full action matrix:

- HTM Engineer: chỉ create + edit Reconciling.
- Storekeeper: chỉ scope=spare_stock.
- Accountant: scope=book_value + confirm rollback.
- DPO: chỉ Sanitization Item.
- Department Head: approve + request rollback.
- Auditor: read-only.

Mọi cell sai = security bug P0.

### III.2. Whitelist hygiene

- Tất cả method `@frappe.whitelist()` có `allow_guest=False`.
- Method modify state có `frappe.has_permission(...)` check.
- Không có method nội bộ rò ra whitelist (review code review checklist).

### III.3. Audit trail

Mọi state transition + finalize + rollback ghi `IMM Audit Trail` với: user, timestamp, before, after, reason. Sanity test: thực hiện 10 action, query audit trail phải có 10 record.

### III.4. CSRF & session

- Endpoint POST yêu cầu CSRF token (Frappe default).
- Session timeout theo policy chung (`assetcore-security` skill).

### III.5. Data sanitization (PII)

- Khi closure approved, không persist nội dung sanitization items có PII trong text — chỉ lưu boolean checked + signed_by.
- Hồ sơ archive IMM-05 giữ nguyên (có thể chứa PII) → role read = Auditor + DPO.

---

## IV. Code quality

| Tiêu chí | Mức |
|---|---|
| Coverage service | ≥70% line |
| Type hint | 100% function (CLAUDE.md §15) |
| Docstring | 100% function public |
| Lint | `ruff` clean |
| Frappe naming | snake_case fieldname, đúng convention DocType |
| Cyclomatic complexity | ≤10 per function |

CI gate: PR fail nếu coverage giảm hoặc lint dirty (refer `assetcore-devops`).

---

## V. Performance test

| Endpoint | Target P95 | Method |
|---|---|---|
| `create_closure` | <500 ms | k6, 50 concurrent users |
| `finalize` | <2000 ms | k6, 10 concurrent (đảm bảo transaction lock) |
| `list_closure` (10000 record) | <800 ms | k6 |
| Dashboard load (5 năm) | <3 s | Browser timing |

Nếu vượt → optimize query (index `asset`, `workflow_state`, `created_on`).

---

## VI. Test data

- Fixture: 20 asset đa dạng (có/không PHI, classification A/B/C/D, có/không phụ tùng tồn).
- 10 Decommission Decision IMM-13 đã approved.
- 5 user đại diện 5 role.
- Script seed: `assetcore/tests/fixtures/imm14_seed.py` *(sprint W3-1).*

---

*Hết file 07. Test case ID detail + coverage report sẽ generate khi BE scaffold xong.*
