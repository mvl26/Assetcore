# IMM-17 — Frontend Design

| Mục | Giá trị |
|---|---|
| Module | IMM-17 — Phân tích dự đoán |
| Stack | Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query (theo CLAUDE.md `ba/`) |
| Trạng thái | Draft — UI cockpit + flows, layout chi tiết theo design system khi sprint Wave 3 |
| Cập nhật | 2026-05-10 |

---

## 1. Page map

| Route | Page | Audience |
|---|---|---|
| `/imm-17` | Cockpit overview (top-N rủi ro + KPI tile) | Operations Manager |
| `/imm-17/insights` | List `AC Predictive Insight` + filter | HTM Engineer + Manager |
| `/imm-17/insights/:name` | Detail insight + contributing factors + action panel | (idem) |
| `/imm-17/models` | List `IMM Predictive Model` versions | System Admin + Data Scientist |
| `/imm-17/whatif` | What-if PM cycle simulator (UC-17-05) | HTM Engineer |
| `/imm-17/runs` | Pipeline run logs | System Admin + Auditor |

---

## 2. Cockpit overview (page chính)

### 2.1 Layout
- **Header**: KPI strip (4 tile) — Total assets monitored · Active signals · Acked rate · Last run.
- **Main**: bảng top-N (mặc định 20) asset có `replacement_score` cao nhất.
  - Cột: Asset · Khoa · Loại · Failure score · Replacement score · Severity · Last incident · Action.
  - Row click → drill-down detail.
- **Sidebar filter**: khoa, asset category, severity, date range, "chỉ chưa acked".
- **Footer**: link "Pipeline run logs" + last refresh timestamp.

### 2.2 Severity coding
- High (đỏ): `replacement_score >= 0.8` *(Cần khảo sát baseline threshold)*
- Medium (vàng): `0.5 ≤ score < 0.8`
- Low (xám): `< 0.5`

> Threshold cấu hình qua `IMM SLA Policy` hoặc DocType cấu hình riêng — KHÔNG hardcode.

---

## 3. Insight detail page

### Sections
1. **Header**: tên asset (link đến `AC Asset`), run_at, model_version, severity badge.
2. **Score card**: failure_score, replacement_score, recommended_pm_cycle.
3. **Contributing factors**: bảng top features + weight (giải thích model — tuân NFR-17-04 explainability).
4. **History timeline**: lifecycle event + WO + incident gần nhất (đọc từ Asset Lifecycle Event).
5. **Action panel** (UC-17-03):
   - "Mở Replacement Review" → tạo entry IMM-13 (call API IMM-13)
   - "Tạo PM Work Order" → call API IMM-08 với pre-fill cycle
   - "Bỏ qua" → require nhập reason
6. **Audit log**: các action đã thực hiện trên insight này.

### Cascade
- Asset name → click navigate `/imm-04/asset/:name` (asset master detail).
- Lifecycle event row → drill xuống module gốc (IMM-08/09/11/12).

---

## 4. What-if simulator

### Flow
1. Chọn asset (autocomplete từ `AC Asset`).
2. Slider PM cycle (1–24 tháng) — mặc định = cycle hiện tại từ IMM-08.
3. Hit "Mô phỏng" → call `whatif_pm_cycle` → render biểu đồ failure probability theo thời gian.
4. Nút "Export PDF báo cáo what-if" *(Could — Wave 3 cuối)*.

> **Read-only**: KHÔNG thay đổi state thật. Toàn bộ chỉ là simulation.

---

## 5. State management (Pinia)

| Store | Mục đích |
|---|---|
| `usePredictiveCockpitStore` | Cache top-N + filter state |
| `usePredictiveInsightStore` | Insight detail + ack action |
| `usePredictiveModelStore` | Model list + activate (admin) |
| `useWhatIfStore` | What-if local state (không persist) |

---

## 6. API client (TanStack Query)

| Query key | Endpoint | Stale time |
|---|---|---|
| `['imm17', 'cockpit', filters]` | `cockpit_summary` | 5 phút |
| `['imm17', 'insights', filters]` | `list_insights` | 1 phút |
| `['imm17', 'insight', name]` | `get_insight` | 30 giây |
| `['imm17', 'models']` | `list_models` | 5 phút |
| `['imm17', 'runs']` | `run_logs` | 1 phút |

Mutation:
- `acknowledge_insight` → invalidate `['imm17', 'insight', name]` + `['imm17', 'cockpit']`
- `register_model`, `activate_model` → invalidate `['imm17', 'models']`
- `whatif_pm_cycle` → không cache (one-shot)

---

## 7. Validation (client-side)

- Acknowledge `dismiss` → reason bắt buộc, ≥10 ký tự.
- Acknowledge `open_replacement` → confirm modal (vì sẽ tạo IMM-13 record).
- What-if cycle: 1 ≤ cycle_months ≤ 24.

---

## 8. UX rules

- **Read-by-default**: Operations Manager xem cockpit là chính, action chỉ qua nút rõ ràng + confirm.
- **Audit visibility**: panel "Đã làm gì với insight này" hiển thị mọi action đã ghi audit.
- **No silent action**: tuyệt đối không auto-create WO từ frontend — phải có bấm nút + confirm.
- **Empty state**: khi chưa đủ dữ liệu để chạy → hiển thị banner "Đang chờ ≥12 tháng dữ liệu vận hành" + link đến IMM-07 dashboard.

---

## 9. Accessibility & i18n

- Toàn bộ label tiếng Việt (theo convention AssetCore).
- ARIA cho severity badge (text alternative).
- Bảng cockpit hỗ trợ keyboard navigation.

---

## 10. Phụ thuộc FE component

- Reuse: KPI tile, asset autocomplete, lifecycle timeline, audit log panel — đã có từ IMM-04/08/09.
- Mới: severity badge, score progress bar, contributing-factors table, what-if chart (Recharts hoặc tương đương — *(quyết định khi Wave 3 sprint)*).
