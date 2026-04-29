# IMM-02 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-02 — Tech Spec & Market Analysis |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |

---

## 1. Routes

| Route | Component | Role |
|---|---|---|
| `/imm02/tech-spec` | `TechSpecList.vue` | All IMM roles |
| `/imm02/tech-spec/:name` | `TechSpecDetail.vue` | All IMM roles |
| `/imm02/market-benchmark/:name` | `MarketBenchmarkDetail.vue` | KH-TC, HTM Engineer |
| `/imm02/lock-in-risk/:name` | `LockInRiskDetail.vue` | QA Risk, VP Block1 |
| `/imm02/dashboard` | `Imm02Dashboard.vue` | KH-TC, PTP Khối 1 |

Sidebar group: **Khối 1 — Hoạch định** > Tech Spec.

---

## 2. Wireframes

### 2.1 TechSpecList

```
Tech Spec                                              [+ Tạo từ Plan]
─────────────────────────────────────────────────────────────────────
Filter: [State▾] [Khoa▾] [Category▾] [Year▾] [Lock-in ≤▾]    🔍
─────────────────────────────────────────────────────────────────────
TS-26-00045  v1.0  Máy thở Hamilton    ICU    Risk Assessed   45ms
                  Mandatory 12  Cand 3  Lock-in 3.2 ⚠
TS-26-00044  v2.0  Lồng ấp Drager      NICU   Locked          🔒
                  Mandatory  8  Cand 4  Lock-in 1.8 ✓
─────────────────────────────────────────────────────────────────────
        Hiển thị 1–20 / 67
```

### 2.2 TechSpecDetail

4-tab layout + workflow stepper:

```
[1. Tổng quan] [2. Yêu cầu KT] [3. Benchmark] [4. Hạ tầng + Lock-in]

Stepper: Draft ▶ Reviewing ▶ Benchmarked ▶ Risk Assessed ▶ Pending Approval ▶ Locked
                                  ●

Tab 1:
  - Header TS-26-00045 v1.0 · ICU · Máy thở · Hamilton C6
  - Source: Plan PP-26-001 / NR-26-04-00012 (clickable)
  - Quantity, target_year, version, parent_spec (nếu reissue)
  - Documents grid (datasheet + HSMT excerpt + drawings)

Tab 2 — Requirements editor:
  - Toolbar: [+ Thêm dòng] [Import Excel] [Áp dụng template]
  - Bảng inline editable:
      Group  Parameter         Value/Range    Mandatory  Weight  Test method  Evidence
      Perf   Tidal Volume      20-2000 mL     ✓          8       IEC 60601…   📎
      Safety Alarm Pressure    ≤ 5 cmH2O      ✓          7       Bench        📎
      ...
  - Footer: total_mandatory · total_optional · validate G01

Tab 3 — Benchmark:
  - Top: weighting scheme sliders (Price/Spec/Support/Brand) → recommended top
  - Candidate table (≥3 rows): manufacturer, model, spec_match%, price, support, in_avl
  - Auto recommendation card highlight winner

Tab 4 — Hạ tầng + Lock-in (split):
  - Left: 6 Infra Compat cards (Electrical, Gas, Network, HIS, HVAC, Space)
          status select + remark + cost estimate
  - Right: Lock-in Risk panel (5 dimensions sliders 1-5)
           lock_in_score gauge (target ≤ 2.5)
           mitigation_plan editor + evidence attach
```

### 2.3 LockInRiskDetail

5-dimension radar chart:

```
                Protocol
                   2
              ╱       ╲
   Service 4 ─────────── Consumable 4
              ╲       ╱
                3
        Software       Parts 3

Score: 3.2 / 5 · Threshold: 2.5 · ⚠ Cần mitigation

Mitigation plan (editor)
[ Tải bằng chứng ]   [ Approve mitigation ]
```

### 2.4 Imm02Dashboard

```
KPI tiles:
  Lead time Draft→Locked  Spec ≥3 candidates  Avg lock-in score
       28d / 30d                100%               2.4 / 2.5
  Spec rework rate  Template re-use rate  Backlog Draft >30d
       18% / 20%       72% / 70%               3
Charts:
  - Funnel state count
  - Lock-in distribution histogram
  - Benchmark candidates per spec (box plot)
```

---

## 3. Components

| Component | Mục đích |
|---|---|
| `<RequirementEditor>` | Inline grid editable + group, evidence |
| `<BenchmarkTable>` | Candidates compare + recommended highlight |
| `<InfraCompatCardGrid>` | 6 cards |
| `<LockInRadar>` | Radar chart 5 chiều |
| `<WorkflowStepper>` | 7-state stepper |
| `<VersionTimeline>` | Hiển thị chuỗi parent_spec → reissue versions |

---

## 4. UX rules

- Tab disable theo state (vd: tab Lock-in chỉ enable từ Risk Assessed).
- Sticky save bar dưới mỗi tab.
- Mọi field permlevel 1 (lock_in_score, mitigation) hiển thị icon 🔒 nếu user không đủ quyền.
- Reissue chain hiển thị breadcrumb: TS-001 v1.0 → v2.0 → v3.0 (current).
- Currency format VND, percent 1 decimal.
- Workflow action confirm dialog luôn yêu cầu reason cho Withdraw / Reject.

---

## 5. Permission UI

| Role | Action visible |
|---|---|
| HTM Engineer | Edit tab 1+2, Reissue, Submit Reviewing |
| HTM Lead | Approve Reviewing |
| KH-TC | Edit tab 3 |
| QA Risk Team | Edit tab 4 (Infra + Lock-in) |
| CNTT | Edit tab 4 (Network/HIS) |
| PTP Khối 1 | Submit Pending Approval |
| VP Block1 | Lock / Withdraw |

---

## 6. Empty/loading/error

- Empty: "Chưa có Tech Spec — tạo từ Procurement Plan".
- 403: "Không đủ quyền xem Lock-in score".
- 409: "Spec đã Locked — không thể sửa, hãy Withdraw + Reissue".

*End of UI/UX Guide v0.1.0 — IMM-02*
