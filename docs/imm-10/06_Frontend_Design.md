> ⚠ **[ROADMAP — Wave 3 / Chưa scaffold]**
> Module IMM-10 (Post-Market Surveillance / Hậu kiểm) chưa có code: không có `assetcore/services/imm10.py`, không có `assetcore/api/imm10.py`.
> Nội dung file này là **dự kiến**, sẽ chốt khi sprint Wave 3 mở và phụ thuộc IMM-16 (Compliance Rule Engine) GA trước.

# IMM-10 — Frontend Design

| Mục | Giá trị |
|---|---|
| Module | IMM-10 — Hậu kiểm và tuân thủ |
| Đợt | 3 |
| Trạng thái | Skeleton (FE chưa scaffold) |
| Cập nhật | 2026-05-10 |

> Stack: **Vue 3 + TypeScript + Pinia + Vue Router + TanStack Query + TailwindCSS** (theo `assetcore-fe-module` SKILL). Mock-up wireframe sẽ render trong Sprint Wave 3 — file này chốt sitemap, cascade, validation rules.

---

## I. Sitemap (route)

| Path | Component | Permission |
|---|---|---|
| `/compliance` | `ComplianceDashboard.vue` | IMM QA Officer, BGĐ, PTP Khối 2 |
| `/compliance/cases` | `ComplianceCaseList.vue` | IMM QA Officer, BGĐ |
| `/compliance/cases/new` | `ComplianceCaseCreate.vue` | IMM QA Officer |
| `/compliance/cases/:id` | `ComplianceCaseDetail.vue` | scope theo permission_query_conditions |
| `/compliance/cases/:id/scope` | `ScopeFinder.vue` (modal hoặc tab) | IMM QA Officer |
| `/compliance/cases/:id/disclosure` | `DisclosurePanel.vue` | IMM Document Officer |
| `/compliance/cases/:id/actions` | `BulkRecallActions.vue` | IMM QA Officer + Workshop Lead |
| `/compliance/cases/:id/effectiveness` | `EffectivenessCheckPanel.vue` | IMM QA Officer |
| `/compliance/capa-tracker` | `CAPATracker.vue` | IMM QA Officer + BGĐ |

Navigation: thêm group **"Hậu kiểm"** trong sidebar, dưới group "QMS" — refer `frontend/src/router/` Wave 1/2 cho pattern.

---

## II. Component Tree (high level)

```
ComplianceDashboard
├── KPISummaryCards (open cases, breach risk, CAPA overdue, recall completion %)
├── DisclosureTimerWidget (countdown 48h cho case Disclosure Pending)
├── RecentCasesTable
└── EffectivenessCheckCalendar

ComplianceCaseDetail
├── CaseHeader (case_no, severity badge, workflow state)
├── Tabs
│   ├── OverviewTab
│   ├── ScopeTab — AffectedAssetsTable
│   ├── DisclosureTab — DisclosureLogTimeline
│   ├── ActionsTab — BulkRecallActions
│   ├── CAPATab — link tới IMM CAPA Record
│   ├── AuditTrailTab — IMM Audit Trail viewer
│   └── EffectivenessTab
└── WorkflowActionBar (apply_workflow buttons)
```

(Pattern mirror `IMM-09 RepairDetail` và `IMM-12 IncidentDetail` — refer `frontend/src/views/imm09/` và `frontend/src/views/imm12/`.)

---

## III. Cascade fields (form Compliance Case)

| Field | Phụ thuộc | Hành vi |
|---|---|---|
| `case_type` | — | Enum dropdown: Recall / FSCA / PMS Signal |
| `severity` | — | Enum: Low / Medium / High / Critical |
| `disclosure_required` | derived from `severity` + `source` | True nếu severity ≥ High AND source = vendor/regulator |
| `vendor` | — | Link `AC Supplier` |
| `model` | `vendor` | Filter `IMM Device Model` theo vendor (cascade) |
| `lot_range_from` / `lot_range_to` | `model` | Hint từ lịch sử lot đã import |
| `serial_range_from` / `serial_range_to` | `model` | Validate format theo model (regex) |
| `mfg_date_from` / `mfg_date_to` | — | Date picker, validate from ≤ to |
| `action_required` | `case_type` | Recall → Replace/Quarantine; FSCA → Update Software/Update Setting/Additional Training |

(Cascade refer skill `assetcore-fe-module` §"Cascade fields" — chuẩn dùng `useFieldCascade` composable nếu có.)

---

## IV. Validation rules (FE-side, mirror BR/VR)

| Rule | UI behavior |
|---|---|
| VR-10-01 — disclosure_due_at = recall_confirmed_at + 48h | Auto-fill, readonly, hiện countdown |
| VR-10-04 — case_type required | Disable submit if empty |
| VR-10-05 — source ≥ 1 ref | Show inline error nếu không có vendor_notice / regulator_doc / internal_signal |
| BR-10-02 — không submit nếu scope rỗng | Submit button disabled cho đến khi `find_scope` chạy thành công |
| BR-10-04 — đóng case yêu cầu 100% WO closed | Action "Đóng case" disabled với tooltip giải thích |
| BR-10-06 — CAPA preventive bắt buộc cho severity ≥ High | Tab CAPA hiển thị warning nếu chưa link CAPA |

Validation message tiếng Việt — refer i18n key `imm10.*` trong `frontend/src/i18n/`.

---

## V. State management (Pinia)

```ts
// frontend/src/stores/imm10.ts  (skeleton)
export const useComplianceStore = defineStore('imm10', () => {
  const cases = ref<ComplianceCase[]>([]);
  const activeCase = ref<ComplianceCase | null>(null);
  const dashboard = ref<DashboardSummary | null>(null);

  // Server state qua TanStack Query (useQuery / useMutation),
  // Pinia chỉ giữ UI state + selected filters.
  return { cases, activeCase, dashboard };
});
```

API call dùng TanStack Query — refer `frontend/src/queries/` Wave 1/2 cho pattern.

```ts
// frontend/src/queries/imm10.ts  (skeleton)
export const useCaseQuery = (id: Ref<string>) =>
  useQuery({ queryKey: ['imm10','case', id], queryFn: () => api.imm10.getCase(id.value) });
```

---

## VI. UI Patterns đặc thù

### VI.1 — Disclosure timer

Component `<DisclosureTimer :due-at="case.disclosure_due_at" />`:
- Đếm ngược live (cập nhật mỗi giây).
- Color shift: xanh (>24h) → vàng (12–24h) → đỏ pulse (<12h) → đỏ flash (breach).
- Click → mở `DisclosurePanel`.

### VI.2 — Affected Assets table

Bulk actions:
- Select all / select by criteria (model / lot).
- Bulk update `action_required`, `action_status`.
- Export CSV (cho công văn vendor).

### VI.3 — CAPA Tracker view

Filter: severity, source module (IMM-09/11/12/10), status, owner, days overdue.
Color row theo SLA: green (within), yellow (≤7 ngày), red (overdue).

### VI.4 — Compliance Dashboard

KPI cards (refer §I.5 của `02_Analysis_Design.md`):
- Open Cases (count + breakdown by severity)
- Disclosure breach risk (cases với <12h tới due)
- CAPA overdue
- Recall completion rate (last 30/90 days)
- Effectiveness check pass rate

---

## VII. Design system

Tuân thủ `docs/res/design-frontend.md` — typography / spacing / color token dùng chung. KHÔNG đặt color hex cứng trong component IMM-10.

Severity color mapping (đề xuất):
- Low: gray-500
- Medium: blue-500
- High: orange-500
- Critical: red-600 + pulse animation

(Lock chính thức trong design-system review trước khi implement.)

---

## VIII. Mockup

*(Wireframe / mockup PNG sẽ ship trong Sprint Wave 3 — UX team thiết kế. Tham chiếu `docs/ba/Phase_06_UX_Screen_Dashboard_Design/` cho pattern.)*

---

## IX. i18n (vi-VN)

Toàn bộ label tiếng Việt. Key namespace `imm10.*`. Sample:

```yaml
imm10:
  case_type:
    Recall: "Thu hồi"
    FSCA: "Hành động khắc phục an toàn"
    "PMS Signal": "Tín hiệu hậu kiểm"
  severity:
    Low: "Thấp"
    Medium: "Trung bình"
    High: "Cao"
    Critical: "Nghiêm trọng"
  action:
    open_case: "Mở case"
    find_scope: "Tìm phạm vi"
    lock_scope: "Khoá phạm vi"
    send_disclosure: "Gửi công văn"
    bulk_create_wo: "Tạo lệnh thu hồi hàng loạt"
    close_case: "Đóng case"
```

---

*Cập nhật: 2026-05-10. Skeleton — wireframe + i18n đầy đủ ship Sprint Wave 3. Stack: Vue 3 + Pinia + TanStack Query (refer `assetcore-fe-module`).*
