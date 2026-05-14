# IMM-01 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |
| Tech | Frappe UI / Vue 3 (frontend) |

---

## 1. Routes

| Route | Component | Role |
|---|---|---|
| `/imm01/needs-request` | `NeedsRequestList.vue` | All IMM roles (filter by dept) |
| `/imm01/needs-request/new` | `NeedsRequestCreate.vue` | Department User, Clinical Head |
| `/imm01/needs-request/:name` | `NeedsRequestDetail.vue` | All IMM roles |
| `/imm01/procurement-plan` | `ProcurementPlanList.vue` | KH-TC, PTP Khối 1, VP Block1 |
| `/imm01/procurement-plan/:name` | `ProcurementPlanDetail.vue` | KH-TC, PTP Khối 1, VP Block1 |
| `/imm01/demand-forecast` | `DemandForecastView.vue` | KH-TC, PTP Khối 1 |
| `/imm01/dashboard` | `Imm01Dashboard.vue` | KH-TC, PTP Khối 1, VP Block1 |

Sidebar group: **Khối 1 — Hoạch định** (parent), 4 items: Đề xuất nhu cầu, Kế hoạch mua sắm, Dự báo nhu cầu, Dashboard.

---

## 2. Wireframes (text)

### 2.1 NeedsRequestList

```
┌───────────────────────────────────────────────────────────────────┐
│ Đề xuất nhu cầu thiết bị                              [+ Tạo mới] │
├───────────────────────────────────────────────────────────────────┤
│ Filter: [Trạng thái▾] [Khoa▾] [Loại▾] [Năm▾] [Ưu tiên▾]   🔍     │
├───────────────────────────────────────────────────────────────────┤
│ NR-26-04-00012  Replacement  ICU      Máy thở Bird     P1  4.32  │
│   2026-04-25                                Submitted  💰 0₫     │
├───────────────────────────────────────────────────────────────────┤
│ NR-26-04-00011  New          NICU     Lồng ấp           P2  3.45  │
│   2026-04-22                                Reviewing  💰 850tr  │
└───────────────────────────────────────────────────────────────────┘
        Hiển thị 1–20 / 87                      < 1 2 3 4 5 >
```

Column priority class hiển thị badge màu: P1=đỏ, P2=cam, P3=vàng, P4=xám.

### 2.2 NeedsRequestDetail

3-tab layout:

```
[1. Thông tin chung] [2. Chấm điểm ưu tiên] [3. Dự toán]   [Audit ▸]

Workflow stepper: Draft ▶ Submitted ▶ Reviewing ▶ Prioritized ▶ Budgeted ▶ Pending Approval ▶ Approved
                                       ●

Tab 1:
  - Header: NR-26-04-00012 · Replacement · P1 · ICU
  - Block "Mục tiêu mua": device_model, quantity, target_year
  - Block "Lý do lâm sàng": clinical_justification (rich text), evidence attach
  - Block "Asset thay thế": replacement_for_asset (link), util/downtime auto-fetch
  - Action footer (theo state): [Lưu] [Gửi đề xuất] / [Yêu cầu bổ sung]

Tab 2: Scoring grid 6 rows (criterion · score 1-5 slider · weight readonly · weighted · evidence)
       → Side panel: weighted_score (dial) + priority_class badge

Tab 3: Budget editor
  - Subtab CAPEX (5 default lines)
  - Subtab OPEX year 1–5
  - Sticky summary footer: total_capex · total_opex_5y · TCO 5y · funding_source select
  - Validation pill: G03 status, envelope utilization %
```

### 2.3 ProcurementPlanDetail

```
┌─────────────────────────────────────────────────────────────────┐
│ PP-26-001 · Annual 2027 · Approved · Envelope 50 tỷ            │
│ Allocated 38.4 tỷ (76.8%)                                       │
├─────────────────────────────────────────────────────────────────┤
│ Filter: [Khoa▾] [Quý▾] [Status▾]                                │
│                                                                 │
│ Rank  NR              Khoa   Model            P  Score  Allocated│
│  1    NR-26-04-00012  ICU    Máy thở          P1 4.32   3.08 tỷ  │
│  2    NR-26-04-00007  NICU   Lồng ấp          P1 4.18   1.20 tỷ  │
│  3    NR-26-03-00021  CĐHA   CT 64-slice      P1 4.05  18.50 tỷ  │
│  ...                                                            │
│                                                                 │
│ [Generate IMM-02 Tech Spec Drafts]   [Export Excel]   [Print]  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 DemandForecastView

Heatmap + line chart:

```
Device Category × Year matrix (qty)
              2027  2028  2029  2030  2031
Imaging        5     4     6     5     4
Life Support   8    10    12    11    10
Lab            3     3     2     2     2
...

Drivers stacked bar
- Replacement (50%)
- Utilization growth (25%)
- Service expansion (25%)

Accuracy badge so với 2026: 87%
```

### 2.5 Imm01Dashboard

6 KPI tiles + 3 charts:

```
[Lead time intake→approved]  [G01 pass rate]   [Envelope utilization]
        38d / target 45d           96%               78% / 95%

[Replacement coverage]  [Forecast accuracy]  [Backlog > 30d]
        85%                  87%                 12 phiếu

Charts:
- Funnel state count
- Stacked bar by department × priority class
- Trendline budget envelope vs allocated by quarter
```

---

## 3. Components

| Component | Mục đích |
|---|---|
| `<NeedsRequestForm>` | Form tổng (3 tab) |
| `<PriorityScoringGrid>` | Lưới chấm điểm 6 tiêu chí |
| `<BudgetEditor>` | Editor matrix CAPEX + OPEX 5y |
| `<WorkflowStepper>` | Stepper hiển thị 8 state |
| `<LifecycleEventTimeline>` | Audit trail dạng timeline |
| `<ProcurementPlanTable>` | Bảng plan_items có drag rank |
| `<DemandForecastHeatmap>` | Heatmap + drilldown |
| `<KPITile>` | Tile dashboard có delta arrow |

---

## 4. UX rules

- Tất cả label, button, error đều **tiếng Việt**.
- Currency format VND, phân tách hàng nghìn dấu chấm: `1.500.000.000₫`.
- Date format `dd/MM/yyyy`.
- Validation inline (red border + helper text bên dưới field).
- Audit timeline luôn hiển thị bên phải detail (collapsible).
- Action footer **sticky bottom**; chỉ hiện action hợp lệ với state + role.
- Confirm dialog cho mọi action workflow (Approve/Reject/Cancel).
- Toast thông báo thành công 3s; error giữ đến khi user đóng.

---

## 5. Permissions UI

UI ẩn / disable theo role + state:

| Role | Có thể thấy nút |
|---|---|
| Department User | Lưu (Draft), Đính kèm; KHÔNG thấy budget tab |
| Clinical Head | Gửi đề xuất |
| HTM Reviewer | Tab 2 chấm điểm; Yêu cầu bổ sung |
| KH-TC Officer | Tab 2 + chuyển Prioritized |
| TCKT Officer | Tab 3 budget; chuyển Budgeted |
| PTP Khối 1 | Trình BGĐ; tạo Procurement Plan |
| VP Block1 | Approve / Reject |

---

## 6. Empty / loading / error states

- **Empty list:** illustration + CTA "Tạo đề xuất đầu tiên" (chỉ Department/Clinical Head).
- **Loading:** skeleton rows 5x cho list, skeleton block cho detail.
- **Error 403:** trang "Không đủ quyền truy cập"; đề xuất liên hệ CMMS Admin.
- **Error 404:** "Phiếu đã bị huỷ hoặc không tồn tại".

---

## 7. Mobile

V1 desktop-first. V2: list + detail responsive cho Clinical Head xem nhanh và approve qua mobile.

*End of UI/UX Guide v0.1.0 — IMM-01*
