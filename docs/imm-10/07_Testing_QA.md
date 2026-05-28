> ⚠ **[ROADMAP — Wave 3 / Chưa scaffold]**
> Module IMM-10 (Post-Market Surveillance / Hậu kiểm) chưa có code: không có `assetcore/services/imm10.py`, không có `assetcore/api/imm10.py`.
> Nội dung file này là **dự kiến**, sẽ chốt khi sprint Wave 3 mở và phụ thuộc IMM-16 (Compliance Rule Engine) GA trước.

# IMM-10 — Testing & QA

| Mục | Giá trị |
|---|---|
| Module | IMM-10 — Hậu kiểm và tuân thủ |
| Đợt | 3 |
| Trạng thái | Test plan (BE chưa scaffold — test case ID sẽ chốt khi code có) |
| Cập nhật | 2026-05-10 |

> Plan này định khung test pyramid + UAT outline. Test ID cụ thể (`TC-IMM10-01`...) và coverage % thực tế sẽ ghi vào file này khi BE/FE scaffold Sprint Wave 3. Tham chiếu CONVENTIONS §6 (coverage target ≥ 70% Python).

---

## I. Test Pyramid

| Level | Scope | Tooling | Coverage target |
|---|---|---|---|
| Unit | Service function (pure) — open_case, find_scope, validate_case | `bench run-tests` (FrappeTestCase) + pytest helper | ≥ 70% LOC service layer |
| Integration | DocType lifecycle — workflow apply, hooks doc_events, scheduler | FrappeTestCase với fixture | mọi BR-10-* phải có ≥1 test |
| E2E (Golden) | Full Recall scenario + Disclosure timer + Bulk WO + Close + Effectiveness | UAT script `scripts/uat/uat_imm10.py` | 1 happy path + 2 alt path |
| Frontend | Component test (Vue Test Utils) + smoke E2E (Playwright) | Vitest + Playwright | KPI cards, timer, form validation |

---

## II. Unit test plan (services/imm10.py)

| Test ID *(placeholder)* | Function | Kịch bản | Expect |
|---|---|---|---|
| U-01 | `open_case` | Payload hợp lệ | Trả case_no, state=`Draft`, audit log inserted |
| U-02 | `open_case` | Source rỗng cả 3 ref | Raise `IMM10_INVALID_SOURCE` |
| U-03 | `find_scope` | Tiêu chí model+lot | Trả đúng asset count, exclude decommissioned mặc định |
| U-04 | `find_scope` | Có asset historical | `historical=true` flag + vẫn liệt kê |
| U-05 | `lock_scope` | Sau lock, find_scope re-run | Raise `IMM10_SCOPE_LOCKED` |
| U-06 | `start_disclosure_timer` | severity=Critical | `disclosure_due_at = now+48h` chính xác (sai số <1 phút) |
| U-07 | `send_disclosure` | Lần 2 cùng case | Raise `IMM10_ALREADY_DISCLOSED` |
| U-08 | `bulk_create_recall_wo` | Idempotent — gọi 2 lần | Lần 2 trả `created=[]`, `skipped` chứa toàn bộ asset |
| U-09 | `close_case` | WO chưa close 100% | Raise `IMM10_INCOMPLETE_ACTIONS` |
| U-10 | `close_case` | severity High, CAPA chưa mở | Raise `IMM10_CAPA_NOT_OPEN` (BR-10-06) |

(Test ID chính thức `TC-IMM10-XX` chốt khi code có — tuân thủ pattern Wave 1/2.)

---

## III. Integration test plan

| Test ID | Scope | Pre-condition | Action | Expect |
|---|---|---|---|---|
| I-01 | Workflow Draft → Scope Identification | Case mới | `apply_workflow("Xác nhận tín hiệu")` | State chuyển + audit event `case.scope_started` |
| I-02 | Workflow Disclosure Pending → Escalated | disclosure_due_at < now | Scheduler `check_disclosure_breach` chạy | State `Escalated`, finding tạo sang IMM-16 |
| I-03 | Hook subscribe chronic failure | 3 incident cùng model trong 90 ngày | Trigger hook IMM-12 | Compliance Case PMS Signal mở tự động |
| I-04 | Hook subscribe calibration fail | IMM Asset Calibration submit với fail | hook on_submit | PMS Signal log |
| I-05 | Bulk WO route — Recall type=PM | Case Action Pending, action=Replace | `bulk_create_recall_wo(wo_type="PM")` | N PM WO tạo trong IMM-08 với ref tới case |
| I-06 | Bulk WO route — Repair | action=Update Software | `bulk_create_recall_wo(wo_type="Repair")` | N Asset Repair tạo |
| I-07 | Permission filter — Vendor | Login as Vendor Engineer V1 | List cases | Chỉ thấy case có vendor=V1 |
| I-08 | Permission filter — Workshop scope | Login Workshop Lead khoa A | List cases | Chỉ case có affected_asset thuộc khoa A |
| I-09 | Audit trail hash chain | Sau 5 actions trên 1 case | `verify_audit_chain(case)` | Pass |
| I-10 | Lifecycle Event publish | Recall completed cho 1 asset | Check `Asset Lifecycle Event` | Event `recall_completed` xuất hiện với root_record=case_no |

---

## IV. UAT scenarios (Golden)

### UAT-IMM10-01 — Recall vendor end-to-end

1. Vendor gửi notice "Lỗi seal cho model X-Ray PRO 2024".
2. QA Officer mở case Recall, severity=Critical.
3. Find scope: model=X-Ray PRO 2024, lot 2024-01 → 2024-06 → ra 23 asset.
4. Lock scope.
5. Pháp chế gửi công văn Bộ Y tế trong 36h → log disclosure.
6. Bulk create 23 WO Replace.
7. Workshop hoàn thành 23/23 trong 14 ngày.
8. BGĐ phê duyệt close.
9. Scheduler tự tạo effectiveness check ngày 30/60/90.
10. Quý sau: entry tự xuất hiện trong Management Review IMM-16.

**Expect:** Mọi state transition, mọi event ghi audit; KPI dashboard cập nhật real-time.

### UAT-IMM10-02 — FSCA software update

1. Vendor cảnh báo lỗi firmware.
2. Mở case FSCA, action=Update Software.
3. Bulk WO Repair với action note "Cập nhật firmware lên 2.1.4".
4. Verify completion → close → CAPA preventive (rà soát quy trình firmware change control).

### UAT-IMM10-03 — Disclosure breach + escalation

1. Mở case severity=Critical lúc T0.
2. Pháp chế bận, chưa gửi công văn.
3. T0+48h: scheduler `check_disclosure_breach` phát hiện → state → `Escalated`.
4. Notify BGĐ + tạo Compliance Finding sang IMM-16.
5. BGĐ can thiệp, công văn gửi T0+50h.
6. Case về `Action Pending`, finding IMM-16 cập nhật `actual_response_time`.

### UAT-IMM10-04 — PMS internal signal

1. IMM-12 phát hiện 4 incident cùng model Y trong 60 ngày.
2. Hook `subscribe_chronic_failure_signal` mở case `PMS Signal` tự động.
3. QA Officer review, có thể: (a) escalate sang Recall nếu nghi ngờ defect, (b) đóng nếu vấn đề vận hành.

(UAT script `scripts/uat/uat_imm10.py` — Sprint Wave 3.)

---

## V. Idempotency & side-effect tests (CONVENTIONS §6)

- **T-IDEM-01:** `bulk_create_recall_wo` gọi 2 lần liên tiếp — chỉ tạo WO 1 lần (check `case_ref` unique).
- **T-IDEM-02:** Hook `subscribe_chronic_failure_signal` trigger 2 lần cùng condition — chỉ mở 1 case PMS.
- **T-IDEM-03:** `start_disclosure_timer` gọi lại sau khi đã set — không reset timer.
- **T-IDEM-04:** Effectiveness check scheduler chạy 2 lần trong cùng ngày — không tạo task trùng.

---

## VI. Security tests

| Test | Mô tả | Expect |
|---|---|---|
| S-01 | Vendor V1 đọc case của vendor V2 | 403 / không hiện trong list |
| S-02 | Khoa lâm sàng đọc case state Draft | 403 — chỉ xem từ `Action Pending` trở đi |
| S-03 | User không có role IMM QA Officer gọi `open_case` | 403 |
| S-04 | SQL injection trong `scope_criteria.lot_range` | Reject by validation; không đẩy raw vào query |
| S-05 | CSRF với endpoint POST | Frappe X-Frappe-CSRF-Token check pass |
| S-06 | Modify `IMM Audit Trail` qua API | Reject (immutable) |

(Refer skill `assetcore-security` cho threat model đầy đủ.)

---

## VII. Performance tests

| Test | Scenario | Target |
|---|---|---|
| P-01 | `find_scope` với 100k asset | < 5s |
| P-02 | `bulk_create_recall_wo` cho 100 asset | < 30s (async OK) |
| P-03 | Dashboard load với 50 case open | < 2s |
| P-04 | List cases với 1000 case | < 1s (pagination 50) |

---

## VIII. Code quality gate

- Unit test ≥ 70% LOC service layer (CONVENTIONS §6).
- Type hints cho mọi function public (CLAUDE.md §15).
- Docstring cho mọi service function.
- Lint: `ruff check`, `mypy assetcore/services/imm10.py`.
- Frontend: `eslint`, `vue-tsc --noEmit`.

---

## IX. Test commands

```bash
# Unit + integration
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm10

# UAT golden
bench --site assetcore.local execute assetcore.scripts.uat.uat_imm10.run

# Frontend
cd frontend && npm run test:unit -- imm10
cd frontend && npm run test:e2e -- imm10
```

---

*Cập nhật: 2026-05-10. Test plan — code thật + test ID chính thức Sprint Wave 3. Coverage target tuân thủ CONVENTIONS §6.*
