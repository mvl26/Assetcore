# 07 — Kiểm thử & An ninh (IMM-07 — Theo dõi hiệu suất)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Trạng thái | Skeleton — test plan; test case detail sau khi BE/FE scaffold |
| Cập nhật | 2026-05-10 |

---

# Phần I — Test Plan

## I.1. Test pyramid

- Unit (service/repository): 60%.
- Integration (DocType lifecycle, workflow, scheduler): 30%.
- E2E (cockpit + drill-down): 10%.

Coverage target service > 50 LOC: ≥ 70% (refer CONVENTIONS §6).

## I.2. Unit test — Service

File dự kiến: `assetcore/tests/services/test_imm07.py`. Bao trùm:
- `build_snapshot` — happy path + thiếu event nguồn + chu kỳ chồng lấp.
- `verify_snapshot` — pass 4-mắt / fail same-user.
- `evaluate_rules` — đủ N chu kỳ liên tiếp / chưa đủ / dedupe signal.
- `close_signal` — resolution hợp lệ / thiếu lý do.

## I.3. Unit test — Validators & Repository

- `Imm07Repo.load_events` — filter đúng period + scope.
- `Imm07Repo.find_open_signals` — dedupe.
- Validator: KPI catalog formula valid, rule threshold dương, period_start < period_end.

## I.4. Integration test — DocType lifecycle

- Tạo `AC KPI Snapshot` → child `AC KPI Value` lưu cùng transaction.
- Tạo `AC Replacement Signal` từ rule eval → liên kết đúng asset + rule.
- Audit trail event sinh đúng cho mỗi state change.

## I.5. Integration test — Workflow

- Snapshot: Draft → Computed → Verified → Closed (happy).
- Snapshot: Verified → Reopened (chỉ QLCL được phép).
- Signal: Open → Reviewing → Resolved | Dismissed.

## I.6. Integration test — Audit chain integrity

Mỗi verify/close ghi `AC Lifecycle Event` với `event_type`, `actor`, `timestamp`, `from_status`, `to_status`. Test chuỗi event không đứt gãy.

## I.7. API test

12 endpoint tại [05_API_Specification.md](./05_API_Specification.md). Smoke test:
- Auth required (401 khi thiếu).
- Permission denied khi role không phù hợp (403).
- Envelope chuẩn `{success, data}` / `{success, error}`.

## I.8. E2E browser (optional)

- Cockpit load + filter cascade khoa.
- Drill-down snapshot → event nguồn.
- Verify snapshot bởi role QLCL.

## I.9. Performance test

- Build snapshot 5.000 asset / chu kỳ tháng < 5 phút (NFR §V.1).
- Cockpit query 12 tháng < 2s p95.

## I.10. Test data

Fixture `assetcore/tests/fixtures/imm07/`:
- 50 asset mẫu phân 3 khoa.
- 6 chu kỳ tháng lifecycle event giả lập.
- KPI catalog 8 KPI mặc định.
- Rule mẫu (MTBF-DROP, DOWNTIME-SPIKE).

*(Tạo cùng Wave 3 sprint 1)*.

## I.11. Run commands & Coverage gate

```bash
bench --site <site> run-tests --module assetcore.tests.services.test_imm07
bench --site <site> run-tests --module assetcore.tests.api.test_imm07
```

Coverage gate: ≥ 70% cho `services/imm07.py`. CI fail nếu giảm.

## I.12. Đo chất lượng mã

- ruff/black cho Python.
- mypy strict cho service layer.
- ESLint + vue-tsc cho FE.

---

# Phần II — UAT Script

## II.1. Phạm vi UAT

End-to-end từ lifecycle event đầu vào tới cockpit + replacement signal + báo cáo ký số.

## II.2. Tester accounts

- `qlcl@hospital.test` (QLCL — verifier).
- `workshop@hospital.test` (Workshop — submitter).
- `bgd@hospital.test` (BGĐ — viewer).

## II.3. Test data đã seed

Refer §I.10.

## II.4. Test scenarios (high-level)

1. **UAT-07-01**: Workshop nhập đủ event PM/CM trong tháng → scheduler chạy → snapshot Computed.
2. **UAT-07-02**: QLCL verify snapshot → trạng thái Verified, không cho sửa.
3. **UAT-07-03**: BGĐ vào cockpit thấy KPI cập nhật + drill-down event nguồn.
4. **UAT-07-04**: Asset có MTBF giảm 3 tháng liên tiếp → signal phát.
5. **UAT-07-05**: QLCL Resolve signal với resolution = Replace → IMM-13 nhận signal.
6. **UAT-07-06**: Export báo cáo tháng PDF có chữ ký số hợp lệ.
7. **UAT-07-07**: Khoa A không thấy KPI khoa B (RBAC).

UAT detail script — *(Soạn cùng QLCL Wave 3 sprint 3)*.

## II.5. Tổng hợp kết quả & Bug found

*(Cập nhật mỗi vòng UAT)*

---

# Phần III — Security Review

## III.1. RBAC

| Role | Read | Build snapshot | Verify | Resolve signal | Admin catalog/rule |
|---|---|---|---|---|---|
| BGĐ | ✓ | ✗ | ✗ | ✗ | ✗ |
| QLCL | ✓ | ✓ (manual) | ✓ | ✓ | ✓ |
| Workshop | ✓ (khoa của mình) | ✗ | ✗ | ✗ | ✗ |
| CNTT/Admin | ✓ | ✓ | ✗ | ✗ | ✓ |

*(Khớp DocPerm khi BE scaffold — refer skill `assetcore-security`)*.

## III.2. API security

- `@frappe.whitelist()` bắt buộc auth.
- Verify endpoint check 4-mắt: `verifier != creator`.
- Rate limit `build_snapshot` / `evaluate_rules` (refer 05 §6).

## III.3. Audit trail integrity

- Mỗi state change → `AC Lifecycle Event` (immutable).
- `verified_by`, `verified_at` không sửa được sau khi set.

## III.4. Authentication & session

Theo Frappe v15 mặc định (CSRF, session timeout config theo `assetcore-security` skill).

---

## DoD — File 07 (IMM-07)

- [x] Test pyramid + plan
- [x] UAT scenario list (7)
- [x] Security RBAC matrix
- [x] Audit chain plan
- [ ] *(Pending: test case ID + coverage số sau Wave 3 implement)*
