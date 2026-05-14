# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-`<XX>` |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (Functional Specs) · 04 Backend · 05 API |

> **Mục đích**: Chiến lược kiểm thử + UAT script + security review. Cover từ unit test BE đến UAT end-user và compliance security. Q3 là gate — không pass = không deploy prod.

---

# Phần I — Test Plan

## I.1. Test pyramid
**Viết gì**: Sơ đồ ASCII 4 tầng. Phần lớn test ở Service layer (unit), DocType + workflow + audit chain ở integration, API ở integration test, E2E + UAT ít. CLAUDE.md §17 mandate TDD.

## I.2. Unit test — Service
**Viết gì**: File `tests/test_imm<XX>_service.py`. Bảng `Test class · Cover function · Số case dự kiến`. Pattern test FrappeTestCase + setUp seed. ≥ 1 happy + 1 negative per function.

## I.3. Unit test — Validators & Repository
**Viết gì**: Validators (`_check_*`) phải có ≥ 1 happy + 1 fail. Repository test thuần query DB thật.

## I.4. Integration test — DocType lifecycle
**Viết gì**: File `tests/test_<doctype>_doctype.py`. Test mọi hook (validate / before_save / on_submit / on_update_after_submit / on_cancel). Bảng `Test · Setup · Action · Assert`.

## I.5. Integration test — Workflow
**Viết gì**: Test mọi transition trong workflow JSON (đếm = số transition ở 04 §3). Permission check per role.

## I.6. Integration test — Audit chain integrity
**Viết gì**: 2 test chính: (a) chain intact sau N mutation, (b) chain breaks khi entry tampered.

## I.7. API test
**Viết gì**: File `tests/test_imm<XX>_api.py`. Bảng `Test · Endpoint · Verify`. Cover happy + invalid + no-permission + pagination + idempotent.

## I.8. E2E browser (optional)
**Viết gì**: Stack Playwright. Khi nào làm: flow phức tạp UI khó test bằng API. Không thay UAT.

## I.9. Performance test
**Viết gì**: Bảng `Metric · Target · Test method`. Cover: list 200 row p95, create endpoint p95, cron N record. Tool k6.

## I.10. Test data
**Viết gì**: Bảng `Loại · Cách seed · File`. Fixtures + test_records.json + UAT seed script (`scripts/uat/uat_imm<XX>.py`).

## I.11. Run commands & Coverage gate
**Viết gì**: Lệnh `bench run-tests` + coverage. Bảng `Layer · Target coverage · Đo`. Service ≥ 85%, DocType ≥ 70%, API ≥ 60%. PR fail CI nếu < target.

## I.12. Đo chất lượng mã nguồn (Code Quality Measurement)
**Viết gì**: Bảng `Tool · Mục tiêu · Target · Cadence`. Cover:
- **SonarQube** (BE Python): bug 0 critical, code smell ≤ N, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100%
- **Lighthouse** (FE): Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80
- **ESLint + vue-tsc** (FE): 0 error, 0 warning trên prod build
- **ruff / black** (BE Python): 0 error, format consistent
- **Bundle size** (FE): main chunk ≤ 250kb gzip, async chunk ≤ 80kb gzip

Khi nào chạy:
- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail)
- Lighthouse: mỗi release lớn + monthly audit
- ESLint/ruff: mỗi PR (CI gate)
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget)

**Mẹo**: Gắn screenshot SonarQube + Lighthouse score vào file 11 §4.4.2 khi báo cáo final.

---

# Phần II — UAT Script

## II.1. Phạm vi UAT
**Viết gì**: 3 mục con — In-scope, Out-of-scope (perf/sec làm ở §I+III), Pre-condition (deploy + fixture + seed + tester account + browser).

## II.2. Tester accounts
**Viết gì**: Bảng `Username · Mật khẩu · Role · Vai trò UAT`. Mỗi role có 1-2 tester.

## II.3. Test data đã seed
**Viết gì**: Bảng `DocType · Số lượng · Ghi chú`. Đủ cover scenario edge case. Reset script.

## II.4. Test scenarios
**Viết gì**: Mỗi scenario theo template §99. ID format `UAT-IMM<XX>-<NN>`. Cover tối thiểu:
- Happy path tạo + xử lý + đóng (≥ 5 scenario)
- Edge case (asset decommissioned, concurrent edit, SLA breach, network down)
- Permission test mỗi role
- Audit chain verify
- Dashboard / report
- Print (nếu có)
- Negative form validation

## II.5. Tổng hợp kết quả & Bug found
**Viết gì**:
- Bảng `Scenario · Status (Pass/Fail/Block) · Tester · Ngày · Ghi chú`
- Sign-off: BA Lead + QA Lead + Module Owner + (tùy) End-user
- Bug list: `Issue ID · Severity · Mô tả · Fix status`. Quy ước go-live: Blocker = 0, Major ≤ 2 (có workaround)

---

# Phần III — Security Review (gate)

## III.1. RBAC
**Viết gì**: 4 mục con —
- Role definitions (file `fixtures/role.json` + `role_profile.json`)
- DocPerm matrix per DocType (Read/Write/Create/Submit/Cancel/Amend/User Permission/Match field)
- Field-level permission (permlevel ≠ 0 cho field nhạy cảm)
- User Permission (filter row theo department/vendor)

## III.2. API security
**Viết gì**: 5 mục con — Whitelist hygiene (mọi @whitelist có docstring + role + validate), CSRF (Frappe default), Input validation, SQL injection (parameterized only), Rate limit.

## III.3. Audit trail integrity
**Viết gì**: Mọi mutation sinh `IMM Audit Trail`. Hash chain SHA-256. Verify endpoint. Test tamper. User KHÔNG edit/delete `IMM Audit Trail`.

## III.4. Authentication & session
**Viết gì**: Login Frappe default. Session timeout config. Lockout policy. Password policy. API key rotation. 2FA roadmap.

## III.5. Data sensitivity
**Viết gì**: Bảng `Loại · Trường · Sensitivity · Bảo vệ`. Khẳng định KHÔNG lưu patient data.

## III.6. Vendor isolation
**Viết gì**: Vendor External chỉ thấy WO assigned. KHÔNG thấy: chi phí, internal note, audit trail vendor khác, dashboard. KHÔNG export.

## III.7. Secrets management
**Viết gì**: Cấm commit .env/credential. site_config.json không lên git. External token lưu `frappe.conf`. Backup encrypt at-rest off-site.

## III.8. Logging & monitoring
**Viết gì**: Bảng `Sự kiện · Log level · Where · Alert?`. PII KHÔNG vào log.

## III.9. Threat model (STRIDE-lite)
**Viết gì**: Bảng `Threat · Vector · Likelihood · Impact · Mitigation`. ≥ 6 threat (Spoofing/Tampering audit/Repudiation/Info disclosure/DoS/Elevation).

## III.10. Penetration test
**Viết gì**: Trước release đầu tiên: Burp/ZAP scan, sqlmap (an toàn), CSRF test, role escalation. Report lưu `docs/security/`.

## III.11. Sign-off
**Viết gì**: Bảng `Role · Người · Ngày · Chữ ký`. Decision: Pass / Pass with conditions / Fail (block).

---

## 99. Template per UAT scenario

```markdown
### UAT-IMM<XX>-<NN> — <Tên>

**Liên kết**: US-<NN>, AC<N>
**Role tester**: <…>
**Mục tiêu**: <1 câu>

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | <…> | <…> | ☐ |
| 2 | <…> | <…> | ☐ |

**Acceptance**: Tất cả step Pass.
```

---

## DoD — File 07 hoàn chỉnh

### I. Test Plan
- [ ] Test class structure cho mọi service public function
- [ ] ≥ 1 happy + 1 negative test mỗi function
- [ ] Workflow transitions đều có test
- [ ] Audit chain test (intact + tampered)
- [ ] API test ≥ 60% coverage
- [ ] Performance target xác định
- [ ] CI command chạy clean
- [ ] **SonarQube Quality Gate pass** + **Lighthouse score ≥ target**

### II. UAT
- [ ] Mỗi User Story có ≥ 1 UAT scenario
- [ ] ≥ 1 negative + permission + audit verify scenario
- [ ] Test data seed script chạy được
- [ ] Tester accounts đã tạo ở UAT site
- [ ] Sign-off section sẵn sàng

### III. Security
- [ ] DocPerm matrix đầy đủ
- [ ] Mọi field nhạy cảm có permlevel ≠ 0
- [ ] SQL injection + CSRF test pass
- [ ] Audit chain test pass (intact + tampered)
- [ ] Vendor isolation test pass
- [ ] Threat model ≥ 6 threat với mitigation
- [ ] Sign-off đầy đủ trước go-live
