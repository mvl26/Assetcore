# IMM-17 — Testing & QA

| Mục | Giá trị |
|---|---|
| Module | IMM-17 — Phân tích dự đoán |
| Trạng thái | Plan — test case ID + coverage % chốt khi BE scaffold |
| Cập nhật | 2026-05-10 |

---

## 1. Test strategy

| Loại | Mục tiêu | Công cụ |
|---|---|---|
| Unit | Service logic (feature builder, scoring, persist) | pytest + Frappe test framework |
| Integration | Pipeline end-to-end với fixture asset history | pytest + DB seed |
| Workflow | (N/A — IMM-17 không dùng workflow Frappe) | — |
| E2E (UAT) | Cron run → insight → ack → action | `assetcore/scripts/uat/uat_imm17.py` (sẽ tạo) |
| Performance | Pipeline ≤30 phút cho 5,000 asset | bench-mark + profile |
| Security | Vendor ML data anonymisation | review + checklist |
| Fairness | Slice metrics theo khoa/vendor | offline notebook |

---

## 2. Unit test plan

| Category | Test focus |
|---|---|
| `extract_history` | Trả đúng record range, không leak record của asset khác |
| `build_features` | Feature vector đủ chiều, không NaN, robust với asset thiếu data |
| `score` | Output trong [0,1], deterministic với cùng input + version |
| `persist_insight` | Tạo `AC Predictive Insight` đúng, log audit, không double-insert |
| `emit_replacement_signal` | Chỉ emit khi vượt threshold, idempotent với cùng run_id |
| `acknowledge_insight` | State chuyển ACKED, audit ghi actor + reason, không cho ack 2 lần |
| `register_model` / `activate_model` | Versioning đúng, chỉ 1 model Active tại một thời điểm |
| `whatif_pm_cycle` | KHÔNG ghi DB, KHÔNG ghi audit (read-only) |

> Test ID + coverage % gán khi sprint Wave 3 (theo CONVENTIONS.md §6 coverage tối thiểu 70%).

---

## 3. Integration test scenarios

### IT-17-01 — Pipeline end-to-end happy path
- **Fixture**: 10 asset với 12 tháng lifecycle event đa dạng.
- **Action**: gọi `run_weekly_pipeline()`.
- **Expect**: 10 insight, ≥1 audit/asset, run log status=success.

### IT-17-02 — Asset thiếu dữ liệu
- **Fixture**: asset mới commissioning <30 ngày.
- **Expect**: skip, log "INSUFFICIENT_HISTORY", không tạo insight giả.

### IT-17-03 — Threshold trigger replacement signal
- **Fixture**: asset với MTBF giảm + nhiều incident gần đây.
- **Expect**: 1 insight + 1 lifecycle event `replacement_signal_emitted`.

### IT-17-04 — Idempotency
- **Action**: chạy pipeline 2 lần liên tiếp cùng tuần.
- **Expect**: không double-insert insight cho cùng asset/tuần.

### IT-17-05 — Acknowledge flow
- **Action**: ack với decision=open_pm.
- **Expect**: tạo PM WO draft, audit ghi link, insight chuyển ACKED.

### IT-17-06 — Audit chain integrity
- **Action**: sau 5 inference + 3 ack.
- **Expect**: `verify_audit_chain(asset)` trả True.

### IT-17-07 — Permission isolation
- **Action**: Vendor Engineer login + gọi `list_insights`.
- **Expect**: 403 / empty (không leak).

---

## 4. Model quality tests (offline)

| Check | Threshold |
|---|---|
| Precision (validation set) | ≥ KPI-17-01 target *(Cần khảo sát baseline)* |
| Recall | ≥ KPI-17-02 target |
| AUC-ROC | *(Cần khảo sát baseline)* |
| Slice precision (per khoa) | Spread ≤ 15% — không bias |
| Slice precision (per vendor) | Spread ≤ 15% |
| Drift detection | Feature distribution KS-test p > 0.05 trên data tuần mới |

> Model phải pass tất cả check trước khi `activate_model`. Output validation report đính kèm `IMM Predictive Model` record.

---

## 5. UAT scenarios (`scripts/uat/uat_imm17.py` — sẽ tạo Wave 3)

1. **UAT-17-01**: Cron weekly run thành công, sinh ≥1 insight cho mẫu asset critical.
2. **UAT-17-02**: Operations Manager đăng nhập → cockpit hiển thị top-N → click drill-down → thấy contributing factors.
3. **UAT-17-03**: Ack insight với decision=open_replacement → IMM-13 record được tạo (link đúng asset).
4. **UAT-17-04**: HTM Engineer chạy what-if PM cycle → biểu đồ render, không tạo record.
5. **UAT-17-05**: System Admin register + activate model mới → run kế tiếp dùng version mới.
6. **UAT-17-06**: Auditor login → thấy run logs + audit chain verify pass.
7. **UAT-17-07**: Vendor Engineer login → KHÔNG thấy menu IMM-17 (permission).

---

## 6. Security checklist

- [ ] Endpoint `whatif_pm_cycle` không cho phép Vendor Engineer.
- [ ] `register_model` chỉ Data Scientist + System Admin.
- [ ] Vendor ML payload (Wave 3 cuối) không chứa serial / patient data → anonymise.
- [ ] API key vendor ML lưu `frappe.conf`, không ghi log.
- [ ] Audit chain verify cho mọi insight đã sinh.
- [ ] Không dùng `frappe.db.set_value` bypass workflow / audit (R-04).

---

## 7. Performance plan

- Benchmark trên dataset thật 5,000 asset × 24 tháng history.
- Mục tiêu pipeline ≤ 30 phút (NFR-17-01) — *(Cần khảo sát baseline)*.
- Nếu vượt → optimize: parallel asset processing, feature caching, batch DB read.
- Profiling tool: `cProfile` + Frappe SQL profiler.

---

## 8. Definition of Done

Module IMM-17 chỉ release khi:
- [ ] Tất cả unit + integration test pass, coverage ≥70%.
- [ ] ≥1 model version "Validated" và "Active".
- [ ] UAT-17-01 → 07 đều pass.
- [ ] Audit chain verify pass cho ≥100 asset mẫu.
- [ ] Cockpit FE render dưới 2s với 1,000 insight.
- [ ] Tài liệu 9 file đầy đủ, không còn placeholder *(TBD)* không có mô tả lý do.
