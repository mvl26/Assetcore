# 07 — Testing & QA

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Per-module |
| Owner | QA Lead + Tech Lead |
| Liên kết | 02 Analysis · 04 Backend · 05 API · 06 Frontend |

---

# Phần I — Test Plan

## I.1. Test scope

**In-scope**:
- Unit test cho service layer (compute KPI, detect signal, validators)
- Repository test (CRUD + filter + concurrency)
- Integration test API (envelope, ErrorCode, RBAC)
- Workflow test (state transition)
- Scheduler test (idempotency, retention purge)
- E2E test FE (cockpit load + drill-down + ack signal)

**Out-of-scope**:
- Load testing > 10k asset (chuyển Wave performance test)
- Predictive ML (thuộc IMM-17)

## I.2. Test pyramid

| Layer | Tool | Target coverage |
|---|---|---|
| Unit | `pytest` + `frappe.test` | Service ≥ 85%, Repo ≥ 80% |
| Integration | `pytest` + `bench --site test run-tests` | API ≥ 60% |
| E2E FE | Playwright | ≥ 5 critical path |
| Manual UAT | Script §II | 100% UC chính |

## I.3. Test cases (key)

| ID | Loại | Mô tả | Liên kết BR/UC |
|---|---|---|---|
| TC-IMM07-BR-01 | Unit | Availability formula với 1 incident 4h trong 24h → 83.3% | BR-01 |
| TC-IMM07-BR-02 | Unit | MTTR = sum(repair_done - repair_start) / count | BR-02 |
| TC-IMM07-BR-03 | Unit | Window không event → snapshot empty không insert | BR-03 |
| TC-IMM07-BR-04 | Integration | Signal cooldown 30d — không tạo duplicate | BR-04 |
| TC-IMM07-BR-05 | Unit | KPI > 100% → flag DATA_ANOMALY + log warning | BR-05 |
| TC-IMM07-BR-06 | Scheduler | Purge hourly > 30d xóa đúng | BR-06 |
| TC-IMM07-BR-07 | Unit | Hash chain prev_hash khớp last snapshot | BR-07 |
| TC-IMM07-API-01 | Integration | `list_kpi_snapshots` envelope success | UC-04 |
| TC-IMM07-API-02 | Integration | `acknowledge_signal` BAD_STATE khi state ≠ Open | UC-10 |
| TC-IMM07-API-03 | Integration | `verify_chain` detect tampered snapshot | UC-08 |
| TC-IMM07-API-04 | Integration | RBAC: User không có IMM07 Manager → FORBIDDEN khi suppress | NFR Sec |
| TC-IMM07-WF-01 | Workflow | Open → Acknowledged transition | UC-10 |
| TC-IMM07-WF-02 | Workflow | Acknowledged → Closed cần closure_reference hoặc lý do | UC-10 |
| TC-IMM07-FE-01 | E2E | Cockpit load < 2s + heatmap render | UC-05 |
| TC-IMM07-FE-02 | E2E | Drill-down asset từ heatmap | UC-06 |
| TC-IMM07-FE-03 | E2E | Acknowledge signal từ list | UC-10 |
| TC-IMM07-FE-04 | E2E | Cascade: đổi site → reload department | NFR UX |
| TC-IMM07-FE-05 | E2E | Validation: form threshold submit disabled khi invalid | NFR UX |

## I.4. Test data

- Fixture seed: 5 asset (mix Imaging/Lab/Life-support), 30 ngày event giả lập (PM, repair, calibration, incident)
- Fixture threshold: 3 asset class với ngưỡng khác nhau
- File: `assetcore/tests/fixtures/imm07_seed.py`

## I.5. CI

- GitHub Actions: chạy `bench run-tests --module assetcore.tests.test_imm07` mỗi PR
- Playwright chạy trên test site staging mỗi đêm

---

# Phần II — UAT Script

## II.1. Pre-condition

- Site staging có data thật ≥ 30 ngày
- 3 user test: Trưởng phòng VT-TBYT, KTV nhóm HTM, Auditor
- Browser: Chrome ≥ 120

## II.2. UAT scenarios

### UAT-01 — Trưởng phòng xem cockpit hằng ngày
1. Login → menu **IMM-07 Hiệu suất**
2. Chọn site, date range 7d
3. Xác nhận: 6 KPI card hiển thị, heatmap render, signal panel show
4. **Pass**: dữ liệu khớp với báo cáo Excel hiện tại ±5%

### UAT-02 — KTV drill-down asset có downtime cao
1. Trên heatmap, click cell đỏ
2. Xem trang chi tiết asset → tab Event Timeline
3. **Pass**: timeline hiển thị event PM/Repair khớp WO trong IMM-09

### UAT-03 — Trưởng phòng acknowledge signal
1. Mở `/imm-07/signals` → state filter `Open`
2. Click signal → xem chi tiết → click **Ghi nhận**
3. Nhập note → confirm
4. **Pass**: state chuyển `Acknowledged`, audit event sinh

### UAT-04 — Suppress false-positive
1. Tương tự UAT-03 nhưng click **Đánh dấu false-positive**
2. Bắt buộc nhập lý do
3. **Pass**: state `Suppressed`, không tạo signal mới trong cooldown

### UAT-05 — Auditor verify chain
1. Login Auditor → `/imm-07/audit`
2. Chọn 1 asset → click **Kiểm tra hash chain**
3. **Pass**: kết quả `valid: true`, số lượng snapshot kiểm tra hiển thị

### UAT-06 — Manager cấu hình ngưỡng
1. `/imm-07/threshold-config` → chọn asset class `Imaging`
2. Đổi `mtbf_hours_min` từ 2000 → 2500
3. Save → confirm modal
4. **Pass**: audit event `kpi_threshold_updated` ghi đủ before/after

### UAT-07–10
`[BA cần bổ sung]`: bổ sung ≥ 4 scenario nữa cover edge case cascade, ngôn ngữ tiếng Việt, role mismatch, data quality stale.

## II.3. Pass criteria

- 100% scenario pass
- ≤ 2 minor bug (cosmetic), 0 major
- End-user feedback ≥ 4/5 trên usability

---

# Phần III — Security Review

## III.1. Authentication & Session

- Frappe session cookie + CSRF token cho POST → ✓ default
- API key/secret hỗ trợ cho BI tool — chỉ role `IMM07 User` read-only
- Session timeout theo policy site (mặc định 30 phút idle)

## III.2. Authorization (RBAC)

| Role | Permission |
|---|---|
| `IMM07 User` | read snapshot, read signal, read threshold |
| `IMM07 Manager` | + acknowledge/suppress signal, update threshold |
| `Auditor` | read all + verify_chain |
| `System Manager` | full |

DocPerm matrix declare trong `assetcore/fixtures/role.json` + DocType JSON `permissions`.

## III.3. Audit trail

- Hash chain SHA-256 mọi mutation snapshot/signal/config
- Verify endpoint expose cho Auditor
- Audit log không thể xóa (DocType `AC Lifecycle Event` immutable)

## III.4. Input validation

- Mọi POST đi qua `_parse_json` → reject malformed
- Whitelist field `order_by` (chống SQL injection qua Frappe ORM filter)
- Numeric input có min/max trong DocType validation

## III.5. OWASP Top 10

| # | Risk | Mitigation |
|---|---|---|
| A01 Broken Access Control | RBAC 3 cấp + DocPerm + verify role per endpoint |
| A02 Crypto Failures | SHA-256 audit; HTTPS bắt buộc prod |
| A03 Injection | Frappe ORM parameterized; whitelist filter |
| A04 Insecure Design | Threat model trong file này |
| A05 Misconfig | `frappe.conf` không expose; secrets ngoài repo |
| A07 Auth Failures | Frappe session + rate limit `verify_chain` |
| A08 Integrity | Audit chain |
| A09 Logging | `frappe.logger("imm07")` |
| A10 SSRF | Không call URL ngoài |

## III.6. Data sensitivity

- KHÔNG lưu patient data
- Asset metadata: serial, model, location — confidential nội bộ
- Export CSV/PDF có watermark user + timestamp

---

# Phần IV — Code Quality

## IV.1. Linting

- BE: `ruff` + `black` 100% pass; `mypy --strict` cho `services/imm07.py`
- FE: `eslint` + `prettier` + `vue-tsc --noEmit` 100% pass

## IV.2. Coverage gate

- Service ≥ 85% (`pytest --cov=assetcore.services.imm07 --cov-fail-under=85`)
- Repository ≥ 80%
- API ≥ 60%
- FE component (vitest + Vue Test Utils): ≥ 60% cho cockpit + drill-down

## IV.3. Code review checklist

- [ ] Mọi public service function có type hints + docstring tiếng Anh
- [ ] DocType field label tiếng Việt
- [ ] Error qua `ServiceError(ErrorCode.X, "msg VN")`
- [ ] API qua `_handle/_ok/_err`
- [ ] Repo không gọi `frappe.get_doc` rải rác trong service
- [ ] FE dùng `useApi().run()`, không axios trực tiếp
- [ ] FE type mirror BE DTO 1-1
- [ ] Cascade reset cho field phụ thuộc

## IV.4. Tech debt budget

- ≤ 20% sprint capacity dành cho debt
- TODO trong code phải có ticket Jira tham chiếu

---

## DoD — File 07

- [x] Test scope rõ in/out
- [x] Test pyramid + coverage target
- [x] ≥ 15 test case mapped BR/UC
- [x] Test data fixture path
- [x] CI integration
- [x] UAT ≥ 6 scenario (cần bổ sung 4 nữa)
- [x] Security RBAC + audit + OWASP
- [x] Code quality lint + coverage gate
- [ ] QA Lead review + sign-off
