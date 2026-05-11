# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Test plan + UAT + Security review |
| Owner | QA Lead + Tech Lead + QMS Risk |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [04 Backend](./04_Backend_Design.md) |

---

# Phần I — Test Plan

## I.1. Test pyramid

- Unit (service + repository): ~70% effort.
- Integration (DocType lifecycle + workflow + cron): ~25%.
- E2E browser (cockpit drill-down): ~5%.

## I.2. Unit test — Service

| Test ID | Function | Case | Expect |
|---|---|---|---|
| UT-IMM07-S-01 | `compute_metrics` | Asset có đủ event 24h | Snapshot quality=complete |
| UT-IMM07-S-02 | `compute_metrics` | Asset thiếu event | quality=incomplete |
| UT-IMM07-S-03 | `compute_metrics` | Asset retired giữa chu kỳ | partial snapshot |
| UT-IMM07-S-04 | `transition_signal` | Open → InReview valid | OK + audit log |
| UT-IMM07-S-05 | `transition_signal` | Closed → InReview | reject + IMM07_SIGNAL_INVALID_TRANSITION |
| UT-IMM07-S-06 | `verify_chain` | Chain liền mạch | pass |
| UT-IMM07-S-07 | `verify_chain` | Chain bị sửa | fail + IMM07_AUDIT_CHAIN_BROKEN |

## I.3. Unit test — Validators & Repository

| Test ID | Target | Case |
|---|---|---|
| UT-IMM07-V-01 | `IMMPerformanceMetric.validate` | Edit value sau khi hash → reject |
| UT-IMM07-R-01 | `PerformanceRepo.get_snapshot` | Lookup theo unique key trả đúng record |
| UT-IMM07-R-02 | `LifecycleEventRepo.get_events` | Window 24h đúng range |

## I.4. Integration test — DocType lifecycle

`IMM Replacement Signal` Draft → Open → InReview → ActionPlanned → Closed; mỗi transition kiểm tra audit + permission.

## I.5. Integration test — Workflow

Threshold maker/checker — maker không thể self-approve.

## I.6. Integration test — Audit chain integrity

Tạo 100 snapshot; verify_chain → pass. Sửa 1 record → fail.

## I.7. API test

Mỗi endpoint trong [05 §0 Catalog]: happy path + 403 + 400 + 404.

## I.8. E2E browser (optional)

- Login Trưởng phòng → Cockpit hiện.
- Click drill-down → Drawer hiện source records.
- Take signal → state thay đổi.

## I.9. Performance test

- Cron compute_metrics 10k asset ≤ 30 phút.
- API drill_down p95 ≤ 300ms ở 50 concurrent user.

## I.10. Test data

Fixture: 100 asset × 5 KPI × 30 ngày = 15k snapshot. Seed qua patch test-only.

## I.11. Run commands & Coverage gate

```bash
bench --site test_site run-tests --module assetcore.tests.test_imm07
bench --site test_site run-tests --coverage
```

Gate: service ≥ 85%, DocType ≥ 70%, API ≥ 60% (CONVENTIONS §6).

## I.12. Đo chất lượng mã nguồn (Code Quality Measurement)

| Metric | Target | Tool |
|---|---|---|
| Cyclomatic complexity | ≤ 10 per function | radon |
| Lint pass | 100% | ruff + black |
| Type coverage | 100% public | mypy |
| FE lint | 100% | eslint + prettier |

---

# Phần II — UAT Script

## II.1. Phạm vi UAT

5 site pilot — 2 bệnh viện hạng I, 3 bệnh viện hạng II. Duration: 2 tuần.

## II.2. Tester accounts

| Role | Số tester / site |
|---|---|
| Trưởng phòng | 1 |
| WS Lead | 1 |
| KTV | 2 |
| QMS Risk | 1 |

## II.3. Test data đã seed

- 50 asset thật được clone lên môi trường UAT.
- Snapshot 30 ngày trước.
- 5 signal Open + 2 Closed.

## II.4. Test scenarios

| ID | Tên |
|---|---|
| UAT-IMM07-01 | Xem cockpit hằng ngày |
| UAT-IMM07-02 | Drill-down từ KPI tile |
| UAT-IMM07-03 | Take signal và Plan action |
| UAT-IMM07-04 | Re-compute snapshot |
| UAT-IMM07-05 | Export báo cáo BYT PDF |
| UAT-IMM07-06 | QMS verify hash chain weekly |

## II.5. Tổng hợp kết quả & Bug found

*(Cập nhật sau UAT — `*(Cập nhật mỗi release)*`.)*

---

# Phần III — Security Review (gate)

## III.1. RBAC

Matrix role × action:

| Action | Trưởng phòng | WS Lead | KTV | QMS Risk | CNTT Admin |
|---|---|---|---|---|---|
| View cockpit toàn site | ✅ | ✅ | ❌ | ✅ (read) | ✅ |
| View snapshot khoa khác | ✅ | ✅ | ❌ | ✅ | ✅ |
| Re-compute | ❌ | ✅ | ❌ | ❌ | ✅ |
| Transition signal | ✅ | ❌ | ❌ | ❌ | ❌ |
| Verify chain | ❌ | ❌ | ❌ | ✅ | ✅ |
| Edit KPI definition | ❌ | ❌ | ❌ | ❌ | ✅ |
| Maker threshold | ❌ | ✅ | ❌ | ❌ | ❌ |
| Checker threshold | ✅ | ❌ | ❌ | ❌ | ❌ |

## III.2. API security

- Mọi endpoint `@frappe.whitelist()` (allow_guest=False mặc định).
- CSRF token bắt buộc cho POST.
- Rate limit `recompute_one` ≤ 10 req/phút.

## III.3. Audit trail integrity

Hash chain SHA-256 mọi snapshot + signal transition. Verify cron weekly + on-demand.

## III.4. Authentication & session

- Frappe session timeout 8 giờ.
- API key roadmap 2FA.

## III.5. Data sensitivity

Không có PII. Chỉ dữ liệu thiết bị + asset code.

## III.6. Vendor isolation

IMM-07 không expose cho vendor. Vendor không có role nào trong matrix III.1.

## III.7. Secrets management

Không có secret module-specific.

## III.8. Logging & monitoring

- Audit log mọi mutation.
- Scheduler log alert khi job fail/quá thời gian.
- APM (Sentry / Frappe error log) cho exception.

## III.9. Threat model (STRIDE-lite)

| Threat | Mitigation |
|---|---|
| Spoofing | Frappe session + API key |
| Tampering | Hash chain + immutable snapshot |
| Repudiation | Audit trail + actor field |
| Info disclosure | RBAC department-scoped |
| DoS | Rate limit + cron lock |
| Elevation | Maker/checker workflow threshold |

## III.10. Penetration test

*(Schedule 1 lần/năm cùng audit toàn hệ thống — `*(Cập nhật mỗi release)*`.)*

## III.11. Sign-off

- [ ] Tech Lead BE
- [ ] Tech Lead FE
- [ ] QMS Risk Officer
- [ ] CNTT (System owner)

---

## 99. Template per UAT scenario

### UAT-IMM07-01 — Xem cockpit hằng ngày

| Mục | Giá trị |
|---|---|
| Actor | Trưởng phòng |
| Pre-condition | Đăng nhập, cron đêm trước đã chạy |
| Steps | 1. Vào `/imm07/cockpit` 2. Quan sát 6 KPI tile 3. Click 1 tile drill-down |
| Expected | KPI tile hiện đủ, drawer drill-down list source records |
| Pass criteria | Tester confirm số liệu khớp với báo cáo Excel hiện hành ±2% |

*(UAT-02..06 — `*(Cập nhật trước UAT thật)*`.)*
