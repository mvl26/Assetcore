# IMM-16 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-16 — Compliance Monitoring & CAPA |
| Phiên bản | 0.1.0 (Wave 2 design) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PLANNED — UI chưa scaffold |
| Tác giả | AssetCore Team |

---

## 0. Tổng quan màn hình

| # | Trang | Frontend Route (Vue) | Frappe Desk URL | Component (PLANNED) |
|---|---|---|---|---|
| 1 | Compliance Dashboard | `/imm16/dashboard` | `/app/imm16-dashboard` | `views/ComplianceDashboard.vue` |
| 2 | Compliance Heatmap | `/imm16/heatmap` | — | `views/ComplianceHeatmap.vue` |
| 3 | Rule List | `/imm16/rules` | `/app/imm-compliance-rule` | `views/RuleListView.vue` |
| 4 | Rule Detail / Edit | `/imm16/rules/:code` | `/app/imm-compliance-rule/{code}` | `views/RuleDetailView.vue` |
| 5 | Finding List | `/imm16/findings` | `/app/imm-compliance-finding` | `views/FindingListView.vue` |
| 6 | Finding Detail | `/imm16/findings/:name` | `/app/imm-compliance-finding/{name}` | `views/FindingDetailView.vue` |
| 7 | Audit List | `/imm16/audits` | `/app/imm-internal-audit` | `views/AuditListView.vue` |
| 8 | Audit Detail (with checklist) | `/imm16/audits/:name` | `/app/imm-internal-audit/{name}` | `views/AuditDetailView.vue` |
| 9 | CAPA List (Kanban) | `/imm16/capa` | `/app/imm-capa` | `views/CapaKanbanView.vue` |
| 10 | CAPA Detail | `/imm16/capa/:name` | `/app/imm-capa/{name}` | `views/CapaDetailView.vue` |
| 11 | Scorecard List | `/imm16/scorecards` | `/app/imm-compliance-scorecard` | `views/ScorecardListView.vue` |
| 12 | Scorecard Detail | `/imm16/scorecards/:name` | — | `views/ScorecardDetailView.vue` |
| 13 | Management Review | `/imm16/management-review/:name` | `/app/imm-management-review/{name}` | `views/MgmtReviewView.vue` |
| 14 | Waive Modal | (modal) | — | `components/imm16/WaiveFindingModal.vue` |
| 15 | Effectiveness Check Modal | (modal) | — | `components/imm16/EffectivenessCheckModal.vue` |

State management: `frontend/src/stores/imm16Store.ts` (Pinia).

---

## 1. Compliance Dashboard (`ComplianceDashboard.vue`)

### 1.1 Route & Component

| Item | Value |
|---|---|
| Route | `/imm16/dashboard` |
| API | `get_dashboard_stats`, `get_capa_aging`, `get_overdue_actions` |
| Permission | Tổ HC-QLCL, Workshop Head, VP Block1/2, Trưởng phòng, CMMS Admin |

### 1.2 Layout wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│ IMM-16 Compliance & CAPA Dashboard                       [Tháng 4/2026 ▼]│
│ ──────────────────────────────────────────────────────────────────────── │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│ │ Compliance  │ │ Findings    │ │ CAPA        │ │ Mgmt Review │          │
│ │ Score       │ │ Open        │ │ Open/Overdue│ │ Quý này     │          │
│ │  87.5%      │ │   24        │ │  18 / 5     │ │ ⚠️ Pending  │          │
│ │  ▲ +2.3 pp  │ │ ⚠️ 3 Crit   │ │ ⚠️ 1 Crit   │ │ Hạn 30/06   │          │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
│                                                                          │
│ ┌────── Trend 12 tháng (line) ─────────┐ ┌──── Top Module Yếu ────────┐ │
│ │                                       │ │                            │ │
│ │   90 ┤    ╭──╮                        │ │  IMM-11  ████████  72%     │ │
│ │      │   ╱    ╰──╮                    │ │  IMM-15  █████████ 78%     │ │
│ │   80 ┤  ╱         ╰──╮      ╭───      │ │  IMM-08  ███████   82%     │ │
│ │      │ ╱             ╰─────╯          │ │  IMM-09  ████████  85%     │ │
│ │   70 ┴────────────────────────────    │ │  IMM-05  █████████ 92%     │ │
│ │      Jun ... ... ... ... ... May      │ │                            │ │
│ └───────────────────────────────────────┘ └────────────────────────────┘ │
│                                                                          │
│ ┌──── CAPA Aging ──────┐ ┌──── Findings gần đây ───────────────────┐    │
│ │  0-7d:    ██  6      │ │ FND-2026-0042  IMM-08  ICU      High  ⏱  │    │
│ │  8-30d:   ███ 8      │ │ FND-2026-0041  IMM-11  CT      Critical ⏱│    │
│ │  31-60d:  ██  3      │ │ FND-2026-0040  IMM-05  OR      Medium  ⏱ │    │
│ │  61-90d:  █   1      │ │ ...                                      │    │
│ │  >90d:        0      │ └──────────────────────────────────────────┘    │
│ └──────────────────────┘                                                 │
│                                                                          │
│ [Xem Heatmap →] [Xem CAPA Board →] [Xem Audit list →]                    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.3 KPI cards

| KPI | API field | Click action |
|---|---|---|
| Compliance Score | `kpis.overall_compliance_pct` | Mở Scorecard tháng hiện tại |
| Findings Open | `kpis.findings_open` | Filter list status=Open/Under Review |
| CAPA Open/Overdue | `kpis.capa_open / capa_overdue` | Mở CAPA Kanban |
| Mgmt Review | `kpis.mr_quarterly_status` | Mở MR quý hiện tại |

### 1.4 Status indicator MR card

| `mr_quarterly_status` | Màu | Hiển thị |
|---|---|---|
| Done | Xanh | ✅ "Đã hoàn tất" + ngày |
| Pending | Vàng | ⏳ "Sẽ tổ chức" + hạn |
| Overdue | Đỏ | ❌ "Quá hạn — block KPI publish" |

---

## 2. Compliance Heatmap (`ComplianceHeatmap.vue`)

### 2.1 Route & Component

| Item | Value |
|---|---|
| Route | `/imm16/heatmap` |
| API | `get_compliance_heatmap` |
| Permission | All authenticated |

### 2.2 Layout

```
┌────────────────────────────────────────────────────────────────────┐
│ Compliance Heatmap — Tháng 4/2026               [Period ▼] [Export]│
│ ────────────────────────────────────────────────────────────────── │
│                                                                    │
│              ICU    OR    ER    CT    Internal  Pediatric          │
│  IMM-04   │  92  │ 88  │ 85  │ 90  │   95     │  91  │             │
│  IMM-05   │  95  │ 92  │ 88  │ 90  │   97     │  94  │             │
│  IMM-06   │  88  │ 85  │ 80  │ 82  │   90     │  87  │             │
│  IMM-08   │  92  │ 78★ │ 85  │ 70★ │   88     │  82  │             │
│  IMM-09   │  85  │ 80  │ 78  │ 75★ │   90     │  88  │             │
│  IMM-11   │  78★ │ 72★ │ 80  │ 65★ │   85     │  80  │             │
│  IMM-12   │  88  │ 82  │ 85  │ 78★ │   92     │  88  │             │
│  IMM-15   │  90  │ 85  │ 82  │ 85  │   92     │  88  │             │
│                                                                    │
│  Legend: ≥90 🟢   80-89 🟡   70-79 🟠   <70 🔴   ★ = có Critical    │
│                                                                    │
│  Click cell → drill-down list_findings filtered                    │
└────────────────────────────────────────────────────────────────────┘
```

### 2.3 Color scale

| Score | Màu | Hex |
|---|---|---|
| ≥ 90 | Xanh | #22c55e |
| 80-89 | Vàng | #eab308 |
| 70-79 | Cam | #f97316 |
| < 70 | Đỏ | #ef4444 |

Hover cell → tooltip `{module, dept, score%, findings_count, top_rules}`.

Click cell → navigate `/imm16/findings?filters={"source_module":"IMM-08","responsible_dept":"OR","period":"2026-04"}`.

---

## 3. Rule List & Detail

### 3.1 Rule List (`RuleListView.vue`)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Compliance Rules                                  [+ Tạo Rule mới]   │
│ ──────────────────────────────────────────────────────────────────── │
│  Filter: [Module ▼] [Category ▼] [Severity ▼] [Active ☑]   [Tìm]    │
│                                                                      │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Mã              | Tên                  | Mod   | Sev  | Freq    │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │ R-IMM08-PM-90   | PM compliance < 90%  | IMM-08 | High | Monthly│ │
│ │ R-IMM05-EXP     | Doc hết hạn          | IMM-05 | Med  | Daily  │ │
│ │ R-IMM11-CAL-OOT | Calibration OOT      | IMM-11 | Crit | Real   │ │
│ │ ...                                                              │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

**Permission:** Chỉ Tổ HC-QLCL + CMMS Admin được thấy nút `+ Tạo Rule mới`.

### 3.2 Rule Detail / Edit

Form layout 4 section:

```
┌──────────────────────────────────────────────────────┐
│ Rule: R-IMM08-PM-COMP-90                Active: [✓] │
│  v1.2  (prev: 1.1)                                  │
│ ──────────────────────────────────────────────────── │
│ ┌─ Định danh ──────────────────────────────────┐    │
│ │ Mã*: R-IMM08-PM-COMP-90                       │    │
│ │ Tên*: PM Compliance < 90%                     │    │
│ │ Module*: [IMM-08 ▼]   Category*: [PM ▼]       │    │
│ │ Severity*: [High ▼]                           │    │
│ └───────────────────────────────────────────────┘    │
│ ┌─ Threshold ───────────────────────────────────┐   │
│ │ JSON*:                                         │   │
│ │ {                                              │   │
│ │   "metric": "pm_compliance_pct",               │   │
│ │   "op": "<",                                   │   │
│ │   "value": 90                                  │   │
│ │ }                                              │   │
│ └────────────────────────────────────────────────┘   │
│ ┌─ Đánh giá ─────────────────────────────────────┐  │
│ │ Frequency*: [Monthly ▼]                         │  │
│ │ Owner Role: [Workshop Head ▼]                   │  │
│ │ QMS Doc Ref: PR-IMMIS-08-01                     │  │
│ │ Regulatory: ISO 13485 §7.5.1                    │  │
│ └─────────────────────────────────────────────────┘  │
│ ┌─ Change Control (BR-16-05) ────────────────────┐  │
│ │ Tóm tắt thay đổi*: (reqd nếu sửa threshold/sev)│  │
│ │ [textarea                                       ] │  │
│ │ Lịch sử versions: v1.0 (2026-01-15) | v1.1 ... │  │
│ └─────────────────────────────────────────────────┘  │
│                          [Hủy]  [Lưu]  [Deactivate] │
└──────────────────────────────────────────────────────┘
```

VR-11 enforce: nếu user thay đổi `threshold_definition` hoặc `severity`, FE bật field `change_summary` reqd + cảnh báo "Đây là change control — version sẽ bump lên".

---

## 4. Finding List & Detail

### 4.1 Finding List (`FindingListView.vue`)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Compliance Findings                      [+ Tạo Manual] [Export CSV]   │
│ ────────────────────────────────────────────────────────────────────── │
│  Filter: [Status ▼] [Severity ▼] [Module ▼] [Dept ▼] [Asset...]  [Tìm]│
│                                                                        │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ # | Mã              | Rule         | Asset       | Sev    | State│ │
│ ├───────────────────────────────────────────────────────────────────┤ │
│ │ 1 | FND-2026-0042   | R-IMM08-PM-90| AC-2026-001| 🔴 High| Under │ │
│ │ 2 | FND-2026-0041   | R-IMM11-OOT  | AC-2026-014| 🚨 Crit| Open  │ │
│ │ 3 | FND-2026-0040   | R-IMM05-EXP  | AC-2026-007| 🟡 Med | Resolved│ │
│ │ ...                                                                │ │
│ └────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Severity badge

| Severity | Badge |
|---|---|
| Low | Gray "Low" |
| Medium | Yellow "🟡 Medium" |
| High | Orange "🔴 High" |
| Critical | Red pulse "🚨 Critical" |

### 4.3 Status badge

| State | Badge |
|---|---|
| Open | Yellow "Open" |
| Under Review | Blue "🔍 Under Review" |
| Confirmed NC | Red "❌ Confirmed NC" |
| False Positive | Gray "FP" |
| Waived | Purple "🛡️ Waived" |
| Resolved | Green "✅ Resolved" |
| Closed | Gray "📦 Closed" |

### 4.4 Finding Detail

Layout 3 column:

| Section | Nội dung |
|---|---|
| Tóm tắt | Rule, Severity, Asset, Dept, Detected at, Source record (Dynamic Link) |
| Đánh giá | current_value vs threshold_value (chart hoặc table) |
| Hành động | Buttons theo state (xem matrix bên dưới) |

#### Actions matrix (Finding)

| Button | Visible khi | Endpoint |
|---|---|---|
| Confirm NC | state = Under Review, role IN {Tổ HC-QLCL, Internal Auditor} | `confirm_finding` |
| Mark False Positive | state = Under Review, role IN {Tổ HC-QLCL, Internal Auditor} | `mark_false_positive` |
| Waive (chỉ VP Block2) | state = Under Review, role = VP Block2 | mở `WaiveFindingModal` |
| Open CAPA | state = Confirmed NC, role IN approval roles | `link_to_capa` |
| Xem CAPA | `capa_ref` set | navigate `/imm16/capa/{capa_ref}` |

---

## 5. Waive Finding Modal (`WaiveFindingModal.vue`)

### 5.1 Trigger & Permission

| Item | Value |
|---|---|
| Trigger | Finding Detail → button "Waive" |
| Permission | VP Block2, CMMS Admin (BR-16-06) |
| API | `waive_finding` |

### 5.2 Layout

```
┌──────────────────────────────────────────────────┐
│ Miễn áp dụng Finding (Waive)                [✕]  │
│ ──────────────────────────────────────────────── │
│ Finding:        FND-2026-0042 (locked)            │
│ Rule:           R-IMM08-PM-COMP-90                │
│ Severity:       🔴 High                           │
│                                                   │
│ Lý do miễn*:    [textarea — tối thiểu 50 ký tự]  │
│                                                   │
│ Bằng chứng*:    📎 [Chọn file...]                 │
│                                                   │
│ Hết hiệu lực miễn*: [📅 2026-12-31]               │
│                  (sau ngày này, finding tự re-open)│
│                                                   │
│ ⚠ Lưu ý: Hành động này yêu cầu role VP Block2     │
│   và sẽ được ghi audit trail (BR-16-06).          │
│                                                   │
│              [Hủy]  [Xác nhận Waive]              │
└──────────────────────────────────────────────────┘
```

VR-04 enforce: reason ≥ 50, evidence reqd, expiry > today.

---

## 6. CAPA Kanban (`CapaKanbanView.vue`)

### 6.1 Route & Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ CAPA Board                                       [+ Tạo CAPA mới] [Filter]│
│ ──────────────────────────────────────────────────────────────────────── │
│ ┌─────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ ┌─────────┐ │
│ │ Draft   │ │Investigating│ │ Action Plan │ │ Implementation│ │Verifica.│ │
│ │  (3)    │ │   (5)       │ │    (4)      │ │     (8)       │ │  (2)    │ │
│ ├─────────┤ ├─────────────┤ ├─────────────┤ ├──────────────┤ ├─────────┤ │
│ │ CAPA-... │ │ CAPA-...   │ │ CAPA-...   │ │ CAPA-...     │ │CAPA-... │ │
│ │ 🚨 Crit  │ │ 🔴 High    │ │ 🟡 Med     │ │ 🔴 High      │ │🚨 Crit  │ │
│ │ Asset    │ │ ICU dept   │ │ OR dept    │ │ Owner: ...   │ │Eff. due:│ │
│ │ Due: 5d  │ │ Due: 3d ⏱  │ │ Due: 12d   │ │ Steps: 3/5   │ │ 7d      │ │
│ └─────────┘ └─────────────┘ └─────────────┘ └──────────────┘ └─────────┘ │
│                                                                          │
│   ──────── Closed (12) ────────         ──── Re-opened (1) ────          │
│   (collapse)                            (collapse)                       │
└──────────────────────────────────────────────────────────────────────────┘
```

**Drag & drop:** Cho phép drag card sang state mới — gọi `advance_capa_state` (server validate VR-05/06/07/12). Nếu fail → toast lỗi và revert.

### 6.2 Card layout

```
┌─────────────────────┐
│ CAPA-2026-00007│
│ 🚨 Critical          │
│ ─────────────────── │
│ Problem: PM compli- │
│ ance ICU thấp 78%   │
│                     │
│ 👤 nguyenvana        │
│ 📅 Due: 2026-05-20  │
│ ⏱ 3 ngày quá hạn    │
│                     │
│ Steps: 2/4 ✓        │
│ [Xem chi tiết]      │
└─────────────────────┘
```

Overdue → border đỏ + icon ⏱.

---

## 7. CAPA Detail (`CapaDetailView.vue`)

### 7.1 Layout

Tab navigation: `[Tóm tắt] [Phân tích] [Hành động] [Action Steps] [Verification] [Lịch sử]`

```
┌────────────────────────────────────────────────────────────────┐
│ CAPA: CAPA-2026-00007        [Re-open] [Save] [Advance ▼]│
│ Status: Implementation     Risk: 🚨 Critical                    │
│ ────────────────────────────────────────────────────────────── │
│ [Tóm tắt●] [Phân tích] [Hành động] [Steps] [Verification] [Hist]│
│                                                                │
│ ┌─ Tóm tắt ─────────────────────────────────────────────────┐ │
│ │ Source: Compliance Finding → FND-2026-0042                 │ │
│ │ Asset: AC-ASSET-2026-0001  Dept: ICU                       │ │
│ │ Action Owner: nguyenvana                                    │ │
│ │ Due: 2026-05-20            Reopen count: 0                 │ │
│ │ Problem statement:                                          │ │
│ │   "PM compliance khoa ICU tháng 4 đạt 78%, dưới ngưỡng    │ │
│ │    90% được quy định bởi PR-IMMIS-08-01. Liên quan 12      │ │
│ │    PM jobs đến hạn nhưng chưa thực hiện."                  │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                │
│ ┌─ Phân tích Root Cause ────────────────────────────────────┐ │
│ │ Method: ⦿ 5-Why  ○ Fishbone  ○ FMEA  ○ FTA                │ │
│ │ Analysis:                                                   │ │
│ │   Why 1: PM bị trễ → thiếu nhân sự                        │ │
│ │   Why 2: Thiếu nhân sự → nghỉ ốm, không backup            │ │
│ │   ...                                                       │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                │
│ ┌─ Action Steps ────────────────────────────────────────────┐ │
│ │ # | Mô tả               | Owner       | Plan      | Status│ │
│ │ 1 | Tuyển bổ sung KTV  | hr@hosp.vn  | 2026-05-15| Done ✓│ │
│ │ 2 | Lên lịch PM lại    | nguyenvana  | 2026-05-25| InProg│ │
│ │ 3 | Cross-train 2 KTV  | nguyenvana  | 2026-06-10| Pending│ │
│ │ 4 | Audit follow-up   | qlcl@hosp.vn | 2026-07-01| Pending│ │
│ │                                          [+ Thêm step]    │ │
│ └────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### 7.2 Advance state dropdown

Dropdown `[Advance ▼]` show next valid states với guard:

| Current → Next | Validation FE preview |
|---|---|
| Draft → Investigating | — |
| Investigating → Action Plan | VR-05 (root_cause_method); VR-12 (due_date) |
| Action Plan → Implementation | Tất cả action_steps có owner + planned_date |
| Implementation → Verification | Tất cả action_steps status="Done" |
| Verification → Closed | Mở `EffectivenessCheckModal` (BR-16-03, VR-07) |

---

## 8. Effectiveness Check Modal (`EffectivenessCheckModal.vue`)

```
┌──────────────────────────────────────────────────┐
│ Effectiveness Check                          [✕] │
│ ──────────────────────────────────────────────── │
│ CAPA: CAPA-2026-00007 (locked)             │
│ Verification period: 2026-06-01 → 2026-07-01     │
│                                                   │
│ Kết quả*:                                         │
│   ⦿ Effective       — Root cause đã loại bỏ      │
│   ○ Not Effective   — Vấn đề tái phát            │
│                                                   │
│ Bằng chứng*:    📎 [Chọn file evidence...]        │
│                                                   │
│ Ghi chú:        [textarea]                        │
│                                                   │
│ ⚠ Nếu Not Effective: CAPA sẽ Re-open (Investigating)│
│   và reopen_count += 1 (BR-16-03)                │
│                                                   │
│           [Hủy]  [Xác nhận]                       │
└──────────────────────────────────────────────────┘
```

---

## 9. Audit Detail (`AuditDetailView.vue`)

### 9.1 Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ Audit: A-2026-Q2-MAINT                       Status: In Progress    │
│ Lead: nguyenvana   Team: 3 auditors                                  │
│ Scope: IMM-08, IMM-11   Depts: ICU, OR, CT                           │
│ Plan: 2026-05-15 → 2026-05-22                                        │
│ ──────────────────────────────────────────────────────────────────── │
│ [Plan ✓] [In Progress ●] [Reporting] [Closed]                        │
│                                                                      │
│ ┌─ Checklist ─────────────────────────────────────────────────────┐│
│ │ # | Clause     | Requirement              | Status   | Finding   ││
│ │ 1 | §7.5.1.1   | PM theo lịch khoa ICU   | ✅ OK    | —         ││
│ │ 2 | §7.5.1.2   | Tài liệu HD bảo trì      | ❌ MajNC | FND-..0050││
│ │ 3 | §7.5.6     | Calibration cycle CT    | ⚠️ MinNC| FND-..0051││
│ │ 4 | §8.5       | CAPA cho Major NC trước | ✅ OK    | —         ││
│ │ ...                                                              ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│ ⚠ Còn 1 Major NC (FND-..0050) chưa link CAPA                         │
│   → Block "Close Audit" cho đến khi link đủ (BR-16-04)               │
│                                                                      │
│ [Lưu checklist] [Sang Reporting]                                     │
└──────────────────────────────────────────────────────────────────────┘
```

### 9.2 Close audit gate

Button [Close Audit] disable + tooltip nếu còn Major NC chưa link CAPA. Server VR-08 enforce.

---

## 10. Scorecard Detail (`ScorecardDetailView.vue`)

### 10.1 Layout (Draft state — pre-publish)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Scorecard: SCR-2026-04-0001               Status: Draft       │
│ Period: April 2026   Scope: Hospital                                 │
│ ──────────────────────────────────────────────────────────────────── │
│ ┌─ Tổng quan ───────────────────────────────────┐                   │
│ │ Score:        87.5%   ▲ +2.3 pp so tháng trước│                   │
│ │ Total rules:  148                              │                   │
│ │ Compliant:    130                              │                   │
│ │ Non-comp:     18                               │                   │
│ │ CAPA open:    18  (overdue 5)                  │                   │
│ └────────────────────────────────────────────────┘                   │
│                                                                      │
│ ┌─ By Module ──────────────────────────────────┐                    │
│ │ IMM-04  ████████████ 95%                     │                    │
│ │ IMM-05  ████████████ 92%                     │                    │
│ │ IMM-06  ██████████   87%                     │                    │
│ │ IMM-08  █████████    82%                     │                    │
│ │ IMM-09  █████████    85%                     │                    │
│ │ IMM-11  ████████     72% ⚠                   │                    │
│ │ IMM-12  ██████████   88%                     │                    │
│ │ IMM-15  ██████████   90%                     │                    │
│ └──────────────────────────────────────────────┘                    │
│                                                                      │
│ ┌─ By Department ──────────────────────────────┐                    │
│ │ ICU     ████████████ 92%                     │                    │
│ │ OR      ██████████   81%                     │                    │
│ │ CT      ████████     74% ⚠                   │                    │
│ │ ER      █████████    85%                     │                    │
│ │ ...                                          │                    │
│ └──────────────────────────────────────────────┘                    │
│                                                                      │
│ ⚠ Quý 1/2026 Management Review: ✅ Done (12/04)                      │
│                                                                      │
│ [Reviewer Sign-off] [Publish Scorecard] [Export PDF]                │
└──────────────────────────────────────────────────────────────────────┘
```

### 10.2 Sau publish — immutable mode

Banner: "🔒 Đã publish ngày {published_at} bởi {approved_by_for_review}. Scorecard không thể sửa (BR-16-07). Tạo restate mới nếu cần."

Mọi field read-only. Hiện thêm button [Tạo Restate] nếu user có role.

### 10.3 Publish guard

Button [Publish Scorecard] disable + tooltip nếu quý trước thiếu MR (BR-16-08, VR-10):
> "⚠ Quý 1/2026 chưa có Management Review status=Closed. Block publish theo BR-16-08."

---

## 11. Management Review (`MgmtReviewView.vue`)

### 11.1 Layout

8 section theo ISO 13485 §5.6 inputs/outputs:

```
┌──────────────────────────────────────────────────────────────────┐
│ Management Review: MR-2026-0002    Status: Draft         │
│ Quarter: Q2-2026   Chair: VP Block2                              │
│ Review date: 2026-06-25                                          │
│ ──────────────────────────────────────────────────────────────── │
│ ┌─ Inputs ──────────────────────────────────────────────────┐   │
│ │ • Scorecard ref: SCR-2026-05-0001 (87.5%)           │   │
│ │ • Audit summary: 2 audit closed, 8 NC, 2 Major + 6 Minor   │   │
│ │ • CAPA summary: 18 open / 22 closed / 1 reopen             │   │
│ │ • CAPA effectiveness: 91% Effective rate                    │   │
│ │ • Customer complaints: ...                                  │   │
│ │ • Training compliance: ...                                  │   │
│ │ • Risk review: ...                                          │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌─ Output Actions ───────────────────────────────────────────┐  │
│ │ # | Action                          | Owner    | Due       │  │
│ │ 1 | Đẩy mạnh PM IMM-08              | WS Head  | 2026-09-30│  │
│ │ 2 | Cập nhật rule R-IMM11-OOT       | QLCL     | 2026-07-15│  │
│ │ 3 | Tổ chức training calibration    | Biomed   | 2026-08-31│  │
│ │                                       [+ Thêm action]      │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│ ┌─ QMS Changes Decided ──────────────────────────────────────┐ │
│ │ [textarea]                                                  │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Minutes Doc: 📎 [Upload]                                         │
│ Next review date: 📅 2026-09-25                                  │
│                                                                  │
│ [Lưu Draft] [Mark as Held] [Finalize (VP Block2)]                │
└──────────────────────────────────────────────────────────────────┘
```

### 11.2 Finalize button

Visible chỉ với VP Block2/CMMS Admin. Action → status `Minutes Approved` → `Closed`.

---

## 12. UX Patterns chung

### 12.1 Toast / Notification

| Loại | Màu | Nội dung mẫu |
|---|---|---|
| Success | Xanh | "✅ CAPA đã chuyển sang Implementation" |
| Warning | Vàng | "⚠️ CAPA Critical này đã quá hạn 3 ngày" |
| Error | Đỏ | Hiển thị `response.error.message` (tiếng Việt từ VR/`_err`) |

### 12.2 Empty states

| Page | Empty message |
|---|---|
| Finding List | "Không có finding nào trong khoảng đã chọn." |
| CAPA Kanban | "Chưa có CAPA. [+ Tạo mới]" |
| Audit List | "Chưa có audit. [+ Tạo Audit]" |
| Heatmap | "Chưa có dữ liệu compliance cho period này." |

### 12.3 Loading states

Skeleton loader cho list/grid + heatmap. Spinner cho actions advance/publish/finalize.

### 12.4 Realtime updates

Subscribe `frappe.realtime.on('imm16:finding_created', ...)` trên Dashboard + Finding List để live append. Subscribe `imm16:capa_state_changed` cho Kanban auto-move card.

### 12.5 Responsive

- Desktop ≥ 1280px: Full layout
- Tablet 768-1279px: Heatmap scroll horizontal, Kanban scroll horizontal
- Mobile < 768px: Dashboard cards stack vertical; Heatmap chuyển sang list view

---

## 13. Permission-driven UI

| UI Element | Hide khi |
|---|---|
| `+ Tạo Rule` | role NOT IN {Tổ HC-QLCL, CMMS Admin} |
| Button [Waive] trên Finding | role NOT IN `_WAIVE_ROLES` (chỉ VP Block2 + CMMS Admin) |
| Button [Confirm NC] / [Mark FP] | role NOT IN {Tổ HC-QLCL, Internal Auditor} |
| Button [Publish Scorecard] | role NOT IN `_PUBLISH_SCORECARD_ROLES` |
| Button [Finalize MR] | role NOT IN `_FINALIZE_MR_ROLES` |
| Button [Close Audit] | role NOT IN `_CLOSE_AUDIT_ROLES` |
| Button [Effectiveness Check] | role NOT IN {Tổ HC-QLCL, CMMS Admin} |
| Button [Re-open CAPA] | role NOT IN {Tổ HC-QLCL, CMMS Admin} |
| Tab Dashboard | role NOT IN {Tổ HC-QLCL, Workshop Head, VP Block1/2, Trưởng phòng, CMMS Admin} |

---

## 14. Accessibility

| Yêu cầu | Implementation |
|---|---|
| Keyboard navigation | Tab order qua form fields, Enter submit, Esc close modal |
| ARIA labels | Buttons, status badges có `aria-label` tiếng Việt |
| Color contrast | Heatmap & badge màu đảm bảo WCAG AA (4.5:1) |
| Color-blind safe | Heatmap có icon ★ + score số kèm màu (không chỉ dựa màu) |
| Screen reader | Toast + modal sử dụng `role="alert"` / `role="dialog"` |
| Drag-drop alternative | CAPA Kanban có dropdown [Advance ▼] cho keyboard users |
