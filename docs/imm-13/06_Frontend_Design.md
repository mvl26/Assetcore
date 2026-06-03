# 06 — Frontend Design (IMM-13)

| Mục | Giá trị |
|---|---|
| Module | IMM-13 — Ngừng sử dụng và điều chuyển |
| Stack | Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query |
| Trạng thái | Skeleton — sẽ implement Sprint Wave 3 — Sprint 4 |
| Liên kết | [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [`docs/res/design/design-frontend.md`](../res/design/design-frontend.md) |

---

## I. Sitemap (route list)

| Route | Component | Quyền (role gate) |
|---|---|---|
| `/imm-13` | `IMM13Dashboard.vue` | KTV, Trưởng khoa, PTP Khối 2, Auditor |
| `/imm-13/reassignments` | `ReassignmentList.vue` | KTV, Trưởng khoa, PTP, Auditor |
| `/imm-13/reassignments/new` | `ReassignmentCreate.vue` (modal hoặc full page) | KTV |
| `/imm-13/reassignments/:name` | `ReassignmentDetail.vue` | tùy state + role |
| `/imm-13/stand-down/new` | `StandDownCreate.vue` | KTV |
| `/imm-13/replacement-reviews` | `ReplacementReviewList.vue` | KTV, TCKT, PTP, QA, Auditor |
| `/imm-13/replacement-reviews/:name` | `ReplacementReviewDetail.vue` | – |
| `/imm-13/residual-risk/:review` | `ResidualRiskForm.vue` | QA Officer |
| `/imm-13/audit/:name` | `AuditChainView.vue` | Auditor |

Layout chung: sidebar trái (chuyển nhanh giữa Reassignment / Replacement / Risk / Audit) + breadcrumb top.

---

## II. Component breakdown

### II.1 Form Reassignment (`ReassignmentCreate.vue`)

Form 3 step:
1. **Chọn asset + lý do** — autocomplete asset (search by tag, serial), textarea reason ≥ 30 ký tự, file upload evidence ≤ 10MB.
2. **Cascade Khoa → Phòng → Vị trí đích** — 4 cấp dropdown (Cơ sở → Khoa → Phòng → Vị trí); reset+reload khi cấp trên đổi.
3. **Confirm** — preview thông tin + cảnh báo nếu cần re-commissioning lite (Asset Class B/C/D + khoa khác chuyên ngành).

### II.2 Detail (`ReassignmentDetail.vue`)

- Header: state badge (theo color spec [02 §IV.3](./02_Analysis_Design.md#iv3-state-machine)).
- Timeline e-sign: KTV → Trưởng khoa nguồn → Trưởng khoa đích → PTP Khối 2 (mỗi bước có dấu / chưa dấu).
- Tab "Lifecycle Events" — link tới các LE liên quan asset.
- Action buttons hiển thị theo role + state (CONVENTIONS §FE).

### II.3 Replacement Review

- Bảng cost items (child table editable inline khi state Draft / Pending Finance).
- Cards summary: residual_value, replacement_cost, repair_cost_aggregate (auto từ IMM-09 lịch sử), risk_score.

### II.4 Residual Risk Form

- Bảng risk × likelihood × impact × mitigation, ≥ 3 dòng. Heatmap màu (Green / Yellow / Red).
- E-sign modal: nhập password re-auth, hiển thị hash sau khi sign.

### II.5 Dashboard

5 widget map vào [02 §I.5 KPI](./02_Analysis_Design.md#i5-kpi-mục-tiêu):
- Stand-down lead time (gauge)
- Reassignment success rate (donut)
- Replacement review compliance (line)
- Residual risk closure rate (badge)
- Asset registry accuracy (number)

---

## III. State management (Pinia store)

```
stores/
  imm13.ts        # main store
```

State shape (high-level):
- `reassignmentList`, `reassignmentDetail`
- `replacementReviewList`, `replacementReviewDetail`
- `residualRiskDraft`
- `dashboardMetrics`
- `loading` flags per resource

Mọi fetch dùng **TanStack Query** (`useQuery` + `useMutation`) — Pinia chỉ giữ derived UI state.

---

## IV. API client

`frontend/src/api/imm13.ts` — wrapper tới các whitelist endpoints liệt kê ở [05](./05_API_Specification.md). Pattern theo `assetcore-fe-module` skill: typed function + envelope `{ success, data, error, code }` parser thống nhất, throw on `success === false`.

---

## V. Cascade fields — bắt buộc

| Field A | Field B (phụ thuộc) | Hành vi |
|---|---|---|
| `target_facility` | `target_department` | Reset + reload danh sách khoa khi facility đổi |
| `target_department` | `target_room` | Reset + reload phòng |
| `target_room` | `target_location` | Reset + reload vị trí cụ thể |
| `asset` | `from_location` | Auto-fill, read-only |
| `asset.classification` | `needs_recommissioning` flag | Auto-tick nếu Class B/C/D + khoa đích khác chuyên ngành |

---

## VI. Validation rules (FE-side, phòng thủ — nguồn truth là BE)

- `reason` ≥ 30 ký tự, không phải toàn whitespace.
- `evidence_files`: ≤ 5 file × 10MB, types: pdf/jpg/png.
- `target_location` ≠ `from_location`.
- Risk item: bắt buộc cả 4 cột (`risk`, `likelihood ∈ {Low, Medium, High}`, `impact ∈ {Low, Medium, High, Critical}`, `mitigation`).
- E-sign password: tối thiểu 8 ký tự (FE chỉ check rỗng + length; xác thực thực ở BE).

---

## VII. Empty / Loading / Error states

Theo `docs/res/design/design-frontend.md`:
- Loading: skeleton bar.
- Empty list: illustration + CTA "Tạo đề xuất mới" (chỉ KTV thấy).
- Error: banner đỏ với mã lỗi (vd `IMM13_COMPETENCY_GAP`) + tiếng Việt thân thiện.

---

## VIII. Accessibility & i18n

- WCAG 2.1 AA (contrast ≥ 4.5, focus visible, keyboard nav cho tất cả action).
- Tiếng Việt primary; key labels không hard-code, dùng `i18n` keys (`imm13.reassignment.create`, ...).

---

## IX. Mockup

*(Mockup Figma — Sprint Wave 3 Sprint 4 do designer cung cấp; cập nhật link vào file này khi có.)*

---

## X. Out-of-scope FE

- Mobile app native (web responsive là đủ cho Đợt 3).
- Offline mode.
- Bulk reassignment (1 form = 1 asset).
