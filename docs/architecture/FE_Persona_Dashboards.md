# FE Persona Dashboards — Core Doc (Single Source of Truth)

| Mục | Giá trị |
|---|---|
| Phạm vi | Cross-cutting FE shell + dashboard (KHÔNG thuộc 1 IMM-XX) |
| Owner | BA + FE Tech Lead |
| Trạng thái | In Progress — Phase 2 |
| Cập nhật | 2026-05-29 |
| Tham chiếu | `FE_Persona_Navigation.md` (Phase 1), prototype `docs/fe/common/dashboard-*.html`, `api/dashboard.py`, `frontend/src/constants/personas.ts`, `frontend/src/composables/usePersona.ts` |

> Đây là spec BE/FE phải code khớp 100% và QA viết test theo. Mọi drift code↔doc = blocking, reconcile doc trước. Tiếp nối Phase 1 (`FE_Persona_Navigation.md §8` liệt kê "Redesign nội dung 8 dashboard" là Phase 2).

---

## 1. Mục tiêu

Thay **một** trang `/dashboard` dùng chung (HTM Command Center hiện tại) bằng **8 dashboard theo persona**. Mỗi persona thấy đúng widget/KPI nghiệp vụ của mình theo prototype `docs/fe/common/dashboard-{persona}.html`.

### 1.1 Nguyên tắc BẮT BUỘC

1. **Dashboard phải truy về source thật** (CLAUDE.md §5 "Dashboard phải truy về source"). KHÔNG hardcode một con số nào. Mọi widget map tới một service function đã verify (§4) hoặc một field DocType thật.
2. **Persona KHÔNG phải security boundary** (kế thừa `FE_Persona_Navigation.md §1.1`). Endpoint `get_persona_dashboard` vẫn để DocPerm + capability của BE quyết định user đọc được record nào; persona chỉ chọn *layout/widget set*. User đổi `ac_persona` sang persona không đủ quyền → `derivePersonas` đã loại ở Phase 1; kể cả gọi thẳng endpoint, mọi count/list vẫn đi qua `frappe.get_all`/service function tôn trọng permission → KHÔNG leak.
3. **Không leak mã hệ thống** (WAVE2-RECURRING-BUGS): mọi `workflow_state`, `status`, role code, severity hiển thị qua display-name tiếng Việt. Status sync: badge dùng cùng nguồn map với list/detail view.
4. **Tái sử dụng Phase 1**: `personas.ts` (PersonaCode, getPersona) + `usePersona.ts` (current persona reactive). KHÔNG định nghĩa lại catalog persona.

---

## 2. Kiến trúc render (FE)

- Giữ **một route** `/dashboard` (không tạo 8 route). `DashboardView.vue` trở thành **router-shell**: đọc `usePersona().current.code` và render component persona tương ứng.
- 8 view persona đặt tại `frontend/src/views/dashboard/personas/{Code}DashboardView.vue` (Code = Admin/Opsmgr/Workshop/Tech/Clinical/Doc/Store/Qa).
- Widget tái sử dụng (component dùng chung) tại `frontend/src/components/dashboard/`:
  - `KpiCard.vue` (label, value, foot, accent) — KHÔNG render giá trị giả khi loading (skeleton).
  - `StatusDonutChart.vue` (đã có) — phân bổ trạng thái.
  - `ListCard.vue` (table/list generic: cột + rows + link).
  - `BarsCard.vue` (chart cột cho KPI theo tháng).
  - `TimelineCard.vue` (sự kiện gần đây / audit trail).
- Data fetch: TanStack Query, `queryKey: ['persona-dashboard', personaCode]`, gọi **một** endpoint `get_persona_dashboard(persona)`. Đổi persona → đổi queryKey → refetch. Có loading skeleton + error state, KHÔNG hiển thị số 0 giả khi chưa load.

> Lý do gộp về 1 endpoint server-side thay vì FE gọi 5 endpoint/persona: (a) tránh N+1 request, (b) scope bảo mật tập trung tại BE, (c) FE đơn giản — 1 query/persona.

---

## 3. Endpoint contract (BE)

```
GET api/method/assetcore.api.dashboard.get_persona_dashboard?persona=<code>
  input : persona ∈ {admin,opsmgr,workshop,tech,clinical,doc,store,qa}
  output: _ok({ persona, generated_at, kpis: [...], sections: {...} })
          persona không hợp lệ → _ok payload rỗng an toàn (kpis: [], sections: {})
                                  (KHÔNG raise — FE shell tối thiểu)
```

- Envelope `_ok`/`_err` theo `utils/response.py` (chuẩn dự án).
- `kpis`: list card chuẩn hoá `{ key, label_vi, value, foot_vi, tone }` với `tone ∈ {primary,info,ok,warn,danger}` (khớp class prototype `.kpi.primary/.warn/...`).
- `sections`: dict các khối phụ (bảng/list/chart/timeline) — key theo persona (§5).
- **Mọi value lấy từ service function đã verify (§4) — không literal số.**
- Hàm fan-out theo persona đặt trong `api/dashboard.py` (orchestration), gọi service layer hiện có (không nhồi business logic mới vào api layer; nếu cần aggregate mới → thêm vào `services/immXX.py`).
- Reuse tối đa `get_overview()` (đã trả assets/commissioning/documents/pm/cm/calibration/incidents/capa + lifecycle_breakdown + recent_*).

---

## 4. Nguồn dữ liệu đã verify (KHÔNG được mock)

| Domain | Service function (file:def) | Field/khoá dùng |
|---|---|---|
| Asset counts + lifecycle + recent | `api/dashboard.get_overview` | `assets.*`, `lifecycle_breakdown`, `recent_incidents`, `recent_pm` |
| PM / CM / Calib / Incident / CAPA / Docs / Commissioning | `api/dashboard.get_overview` | `pm.*`, `cm.*`, `calibration.*`, `incidents.*`, `capa.*`, `documents.*`, `commissioning.*` |
| KPI bảo trì (MTTR, SLA, repeat-fail, open WO) | `services/imm09.get_kpis(year, month)` | `kpis.mttr_avg_hours`, `kpis.sla_compliance_pct`, `kpis.repeat_failure_count`, `kpis.open_wos` |
| KPI MTBF / uptime rollup | `services/imm00.rollup_asset_kpi` (scheduler ghi field trên AC Asset) | `AC Asset` KPI fields (đọc tổng hợp) |
| Calibration KPI | `services/imm11.get_kpis(year, month)` | (calib pass-rate, due) |
| Spare parts KPI + low-stock + allocations + cycle | `services/imm15.get_dashboard_stats`, `get_low_stock_alerts`, `list_allocations`, `list_cycle_counts` | `low_stock_alerts`, `pending_allocations`, `pending_cycle_counts`, allocation rows |
| Compliance score / findings / audits | `services/imm16.get_current_scorecard`, `list_compliance_findings`, `list_internal_audits` | scorecard `overall_score`, finding rows, audit rows |
| Năng lực KTV | `services/imm06.list_user_competencies`, `get_asset_operator_coverage` | competency rows |
| Needs (đề xuất) | `services/imm01` (list NR + priority/score) | NR rows, urgency, workflow_state |
| Commissioning gate | `api/imm04` / `get_overview.commissioning` | gate state |
| User counts (admin) | `api/user.py` | total/active/disabled/pending users |

> Nếu một widget mockup KHÔNG có nguồn thật (vd "audit-chain PASS/FAIL" cho admin, "vendor engineers count"): BE phải bổ sung getter đọc dữ liệu thật (audit chain verify từ `utils/lifecycle.py`; vendor count từ role assignment) HOẶC tạm ẩn widget đó với ghi chú TODO trong Core Doc. **TUYỆT ĐỐI không literal số.**

---

## 5. Layout + widget→source theo persona

Mỗi mục: KPI cards (hàng đầu) + sections. Tất cả map tới §4. Số trong prototype HTML chỉ là minh hoạ — bỏ, thay bằng giá trị thật.

### 5.1 `admin` — Quản trị viên IT (`dashboard-admin.html`)
- KPI: Tổng người dùng (`api/user`), Chờ phê duyệt user (`api/user`), Audit chain trạng thái (`utils/lifecycle` verify), Vendor Engineer (role assignment count).
- Sections: bảng `users_pending` (user chờ duyệt), `audit_recent` timeline (`get_overview.recent_*` / audit log).

### 5.2 `opsmgr` — Trưởng phòng VT-TTBYT (`dashboard-opsmgr.html`)
- KPI: Thiết bị đang hoạt động + uptime (`get_overview.assets` + imm00 rollup), PM đến hạn 7 ngày + quá hạn (`get_overview.pm`), Sự cố mở Critical (`get_overview.incidents`), Đề xuất chờ duyệt (`imm01`).
- Sections: `today_tasks` (gộp incident critical + PM overdue + NR chờ + calib due), `asset_status_breakdown` (donut, `lifecycle_breakdown`), `maintenance_kpi_6m` (bars, `imm09.get_kpis` + MTBF/MTTR/uptime), `recent_events` timeline.
- **Read-only oversight (2026-06-02):** opsmgr là vai trò **giám sát** → được cấp **READ-ONLY** trên 3 module vận hành để KPI drill-down sang list xem được: PM Work Order (`pm.read`/imm08), Asset Repair (`repair.read`/imm09), Incident Report + RCA + QA NC (`corrective.read`/imm12). **CHỈ read** — không write/create/delete/submit/workflow. Cơ chế: thêm DocPerm `read=1` (mọi cờ ghi=0) cho role nền của profile `Commissioning Manager` (role này **độc quyền** thuộc Role Profile "Trưởng phòng VT-TTBYT" → không rò sang persona khác). Nhờ đó `canAccessDrill` (FE) thấy capability → KPI `pm_due_7d`, `incidents_critical`, donut severity, bars CM (SLA/WO/lặp lỗi) render **clickable** thay vì card tĩnh.

### 5.3 `workshop` — Trưởng xưởng kỹ thuật (`dashboard-workshop.html`)
- KPI: WO chờ phân công PM/CM (`get_overview.pm/cm`), WO trong tuần, PM Compliance % (imm08), SLA vi phạm (`imm09.get_kpis.sla_compliance_pct` → derive breach).
- Sections: `wo_to_assign` table, `tech_competency` (`imm06.list_user_competencies`), `pm_compliance_bars`, `calibration_due_30d` (`get_overview.calibration`).

### 5.4 `tech` — Kỹ thuật viên (`dashboard-tech.html`)
- KPI: Việc hôm nay, PM trong tuần, CM khẩn cấp, Hoàn tất tháng + MTTR — tất cả filter theo **technician = current user** (PM/CM service filtered by assignee).
- Sections: `my_wo_today` table, `week_calendar` (PM/CM/Cal due theo ngày), `my_spare_requests` (`imm15.list_allocations` filter requested_by = me).

### 5.5 `clinical` — Trưởng khoa lâm sàng (`dashboard-clinical.html`)
- KPI: Thiết bị khoa, Sự cố đang xử lý, NR đã nộp, Chờ nghiệm thu — filter theo **department của user**.
- Sections: `dept_incidents` table, `dept_needs` table (`imm01` dept-scoped), `awaiting_clinical_release` (`imm04` Clinical_Release pending).

### 5.6 `doc` — Cán bộ hồ sơ (`dashboard-doc.html`)
- KPI: Tài liệu chờ duyệt, Sắp hết hạn 90 ngày, Nghiệm thu đang xử lý, NC mở (`get_overview.documents` + `commissioning`).
- Sections: `docs_expiring` table, `commissioning_queue` (gate detail từ imm04).

### 5.7 `store` — Thủ kho phụ tùng (`dashboard-store.html`)
- KPI: Tổng giá trị tồn (`imm15.get_dashboard_stats`), Dưới định mức (`low_stock_alerts`), Cấp phát đang xử lý (`pending_allocations`), Kiểm kê đang đếm (`pending_cycle_counts`).
- Sections: `below_min` table (`get_low_stock_alerts`), `pending_allocations` table (`list_allocations` status REQUESTED/APPROVED).

### 5.8 `qa` — Cán bộ QA / Kiểm toán (`dashboard-qa.html`)
- KPI: CAPA Overdue (`get_overview.capa.overdue`), CAPA In Progress (`get_overview.capa.open`), RCA chưa hoàn tất (imm12/incident), Compliance Score (`imm16.get_current_scorecard`).
- Sections: `capa_todo` table, `compliance_findings` table (`list_compliance_findings`), `calibration_fail` (imm11 fail → CAPA), `internal_audits` (`list_internal_audits`).

---

## 6. Acceptance Criteria

1. Route `/dashboard` render đúng dashboard của `usePersona().current.code`; đổi persona → đổi dashboard ngay (reactive, không reload).
2. 8 view persona tồn tại; mỗi view render KPI + sections theo §5, nhãn tiếng Việt.
3. `get_persona_dashboard(persona)` trả payload từ service thật (§4); KHÔNG có literal số liệu trong code BE/FE.
4. Persona không hợp lệ → payload rỗng an toàn, FE không crash.
5. Anti-leak: không hiển thị raw `workflow_state`/`status`/role code/severity — chỉ display-name VI; badge dùng cùng map với list view (status sync).
6. Bảo mật: user thiếu quyền đọc record → count/list tương ứng = 0/rỗng (DocPerm tôn trọng), không leak data persona khác.
7. Không regression: FE build + typecheck + lint xanh; vitest xanh; `bench run-tests` (BE nếu chạm) xanh.
8. Loading state là skeleton (không số 0 giả); error state hiển thị thông báo, không trắng trang.

## 7. OUT-of-scope (Phase 2)

- Redesign module list/detail/form theo `docs/fe/` (Phase 3+).
- Realtime websocket refresh dashboard (polling/refetch thủ công là đủ).
- Tạo DocType/role/DocPerm mới (chỉ đọc; thêm getter read-only nếu widget thiếu nguồn).
- Export/PDF dashboard.

## 8. Test cases (viết trước — TDD)

### 8.1 BE (`bench run-tests`)
| ID | Mô tả | Kỳ vọng |
|---|---|---|
| D-BE-1 | `get_persona_dashboard('opsmgr')` | KPI asset/pm/incident khớp `get_overview` cùng thời điểm |
| D-BE-2 | `get_persona_dashboard('store')` | `low_stock_alerts`/`pending_allocations` khớp `imm15.get_dashboard_stats` |
| D-BE-3 | `get_persona_dashboard('qa')` | compliance score khớp `imm16.get_current_scorecard` |
| D-BE-4 | persona không hợp lệ `'zzz'` | payload rỗng an toàn, không raise |
| D-BE-5 | user thiếu quyền IMM-15 gọi `'store'` | rows rỗng/scoped, không leak |
| D-BE-6 | Mọi value là số tính từ DB | không field nào hardcode (review) |

### 8.2 FE (`vitest`)
| ID | Mô tả | Kỳ vọng |
|---|---|---|
| D-FE-1 | `DashboardView` shell với `current='opsmgr'` | render `OpsmgrDashboardView` |
| D-FE-2 | `current='store'` | render `StoreDashboardView` |
| D-FE-3 | KPI labels của mỗi persona | đúng nhãn VI §5 |
| D-FE-4 | payload có raw status code | hiển thị display-name VI, không raw code |
| D-FE-5 | loading | skeleton, không số 0 giả |
| D-FE-6 | error từ API | hiển thị error state, không trắng trang |
| D-FE-7 | queryKey theo persona | đổi persona → refetch (key đổi) |

---

## 9. Drill-down / Data-linking contract (Phase 2.1 — Round 1+)

> **Nguyên tắc:** mỗi số liệu trên dashboard phải truy về source (CLAUDE.md §5).
> Drill-down hiện thực hoá điều này ở UX: click một KPI/segment → mở **list view
> đã pre-apply filter** đúng tập dữ liệu sinh ra con số đó. Không có "con số chết".

### 9.1 `drill` descriptor (BE → FE)

KPI card và mỗi segment chart drillable mang một descriptor:

```
drill: {
  route: "<vue route path>",     # ví dụ "/assets"
  query: { <key>: <canonical> }  # ví dụ { lifecycle_status: "Active" }
} | null
```

- `_kpi(key, label_vi, value, foot_vi, tone, drill=None)` — thêm tham số optional `drill`.
  KPI không drill được → `drill = null` (FE render card tĩnh, không link).
- `lifecycle_breakdown` (donut source) mỗi entry mang thêm `code` = **canonical
  lifecycle_status** (English) song song `state`/label hiển thị.

### 9.2 Canonical value rule (BẮT BUỘC — chống drift VI↔EN)

- Donut/breakdown hiển thị **nhãn VI** (`_STATUS_LABELS_VI`), nhưng filter ở list view
  `AssetListView` nhận **canonical code English** (`Active`, `Under Repair`,
  `Calibrating`, `Out of Service`, `Commissioned`, `Decommissioned`).
- BE phải cung cấp canonical code trong `drill.query` / `lifecycle_breakdown[].code`
  — **KHÔNG** đẩy nhãn VI vào query (list filter sẽ match rỗng → con số click ra 0 dòng).
- Một nguồn sự thật cho map: hằng `_STATUS_LABELS_VI` (đảo ngược khi cần), KHÔNG
  hardcode chuỗi VI rời rạc ở nhiều chỗ.

### 9.3 Destination list view phải đọc query (BẮT BUỘC)

- `AssetListView` (và mọi list view đích) **đọc `route.query` on mount** và pre-apply
  vào `filters` trước `fetchList`: keys `lifecycle_status`, `department`,
  `asset_category`, `gmdn_code`, `search`.
- Watch `route.query` để khi điều hướng drill-down lần 2 (cùng route, query khác)
  filter cập nhật lại.
- Query không hợp lệ (giá trị lạ) → list trả rỗng an toàn + chip filter vẫn hiện để
  user xoá (không crash, không bỏ qua filter im lặng).

### 9.4 Round 1 scope (data-linking)

| Nguồn (persona) | Widget | Drill tới |
|---|---|---|
| opsmgr / admin | KPI "Thiết bị đang hoạt động" | `/assets?lifecycle_status=Active` |
| opsmgr | Donut `asset_status_breakdown` segment | `/assets?lifecycle_status=<code segment>` |
| opsmgr | KPI "Sự cố mở (Critical)" | `/incidents/list?severity=Critical&status=open` *(Round ≥2 khi IncidentList đọc query)* |

> Round 2-5 mở rộng: PM/CM/calibration/incident/inventory KPI + bars → list view tương ứng,
> sau khi mỗi list view đích đã đọc query (gate như §9.3).

### 9.4.1 Round 2 scope (incident drill-down)

| Nguồn (persona) | Widget | Drill tới | Ghi chú round-trip |
|---|---|---|---|
| opsmgr | KPI "Sự cố mở (Critical)" | `/incidents/list?severity=Critical` | KPI đếm `severity=Critical ∧ status∈{Open,Under Investigation}` (compound). List filter `severity=Critical` đơn lẻ → tập **bao** KPI (gồm cả Critical đã đóng). Người dùng vẫn lọc thêm `status` trong list. Không claim count khớp tuyệt đối cho KPI compound — §9.5 #10 chỉ ràng buộc KPI single-filter. |

- `IncidentListView` đọc `route.query`: keys `severity`, `status`, `asset` (gate §9.3).
- Donut/segment incident (nếu thêm) dùng cùng canonical code rule §9.2.

### 9.4.2 Round 3 scope (PM/CM work-order drill-down)

| Nguồn (persona) | Widget | Drill tới | Round-trip |
|---|---|---|---|
| workshop | KPI "PM quá hạn" | `/pm/work-orders?status=Overdue` | KPI = `count_overdue_pm()` (WO.status='Overdue'); list filter `status=Overdue` → khớp single-filter (§9.5 #10). |

- `PMWorkOrderListView` đọc `route.query.status` + `asset` (gate §9.3, đã có `asset`).
- `CMWorkOrderListView` đọc `route.query.status` + `priority` + `asset` (gate §9.3).
- Status canonical PHẢI khớp WO status enum (`Overdue`, `Open`, `In Progress`…) —
  KHÔNG nhãn VI (PM_STATUSES/CM_STATUSES value là canonical English).

### 9.4.3 Round 4 scope (UI redesign + calibration gate)

- **UI redesign (yêu cầu "đẹp"):** thêm `DashboardSection.vue` (header accent emerald,
  card `rounded-2xl` + hairline border + shadow nhẹ). `KpiCard` nâng cấp typography
  (value `2rem`, uppercase label, hover lift + arrow chip). `PersonaDashboardShell`
  nhịp lưới rộng hơn (`max-w-[1600px]`, gap 5–7). Mọi contract widget GIỮ NGUYÊN.
- **Calibration gate (§9.3):** `CalibrationListView` đọc thêm `route.query.status` +
  `result` (đã có `asset`) → sẵn sàng drill status-based.
- **Quyết định chống vá triệu chứng (Strict Rule #3):** KPI calib `calib_due`/
  `calib_overdue` là **date-window** (≤30d / quá hạn), KHÔNG map sang `status` đơn lẻ.
  KHÔNG ép drill `status=` cho KPI date-based (sẽ lệch count, vi phạm §9.5 #10).
  Drill date-window đúng cần list hỗ trợ filter `due_before`/`overdue` → để Round ≥5.

### 9.4.4 Round 6 scope (date-window drill — hoàn tất §9.4.3 deferred)

- **Root-cause fix:** `get_overview` đếm `calib_due`/`calib_overdue` bằng field
  **`next_due_date`** (đúng), trước đây dùng `next_calibration_date` (column KHÔNG
  tồn tại trên `IMM Calibration Schedule` → `OperationalError` bị `try/except` nuốt
  → KPI âm thầm sai). SSOT cho drill-down date-window.
- **BE virtual filter (SSOT, không vá triệu chứng):**
  - `imm11.list_schedules`: `due_before` → `next_due_date <= X`; `overdue` (truthy) →
    `next_due_date < today`. Drill list khớp predicate KPI.
  - `imm08.list_work_orders`: `due_before` → `due_date <= X` + `status not in
    [Completed,Cancelled]`; `overdue` → `status == Overdue` (cron `check_pm_overdue`
    là SSOT, WO là operational record duy nhất — CLAUDE.md §11).

| Nguồn (persona) | Widget | Drill tới | Round-trip |
|---|---|---|---|
| workshop | KPI `calib_due` | `/calibration/schedules?due_before=<today+30>` | list `next_due_date≤today+30` ⊇ KPI `[today,today+30]` (superset hợp lệ §9.4.1) |
| workshop | KPI `pm_overdue` (đã có) | `/pm/work-orders?status=Overdue` | khớp |
| opsmgr | KPI `pm_due_7d` | `/pm/work-orders?due_before=<today+7>` | list `due_date≤today+7 & chưa hoàn tất` ⊇ KPI `[today,today+7] & mở` |

- **Quy tắc canonical-value (§9.5 #10):** KPI date-based KHÔNG ép `status=`. Drill bằng
  cửa sổ ngày để list là **superset hợp lệ** của KPI (KPI là `[today, today+N]`, list là
  `≤ today+N` — bao gồm cả quá hạn). Chip filter hiển thị "Đến hạn trước \<ngày\>" / "Quá hạn".

### 9.4.5 Round 7 scope (spare-part low-stock drill)

- **BE:** `inventory.list_spare_parts(low_stock=1)` → chỉ parts có ≥1 stock row
  `qty_on_hand < min_stock_level` (`_low_stock_part_ids()`). Fail-closed: không có part
  low → sentinel `__none__` (match nothing), KHÔNG bỏ filter.
- **Drift fix (canonical-value):** `is_low_stock` flag chuyển từ *tổng-qty-toàn-kho < min*
  sang *bất-kỳ-row < min* để KHỚP KPI store `low_stock` (`_count_low_stock`) và filter
  `low_stock=1`. Một nguồn sự thật duy nhất — chip, row-flag, KPI đồng bộ.

| Nguồn (persona) | Widget | Drill tới | Round-trip |
|---|---|---|---|
| store | KPI `low_stock` | `/spare-parts?low_stock=1` | KPI đếm stock-row dưới min; list = parts distinct dưới min (subset part-granularity, documented) |

### 9.4.6 Round 8 scope (severity donut + bar-card drill)

- **Severity donut (opsmgr):** section `incident_severity_breakdown` (BE) — mỗi entry
  `{severity, code, label_vi, count}`, `code` canonical (Critical/High/Medium/Low).
  FE thêm `StatusDonutChart` thứ 2 "Sự cố theo mức độ" → segment-click route
  `/incidents/list?severity=<code>`. Round-trip: tổng breakdown == số incident mở.
- **Bar-card drill:** `BarsCard` thêm optional per-bar `drill` + render `RouterLink` khi có.
  `maintenance_kpi.drills` (BE descriptor):

| Bar | Drill tới | Ghi chú |
|---|---|---|
| SLA (%) | `/cm/work-orders?sla_breached=1` | CM vi phạm SLA |
| WO mở | `/cm/work-orders?status=Open` | CM đang mở |
| Lặp lỗi | `/cm/work-orders?is_repeat_failure=1` | CM lỗi lặp |
| MTTR (h) | — (KHÔNG drill) | metric thời lượng, không có list 1-1 (§9.5 #10) |

- **CM list filter mở rộng:** `CMWorkOrderListView` đọc thêm `route.query.sla_breached`,
  `is_repeat_failure` → pass virtual key tới BE (real field trên Asset Repair). Chip
  "Vi phạm SLA" / "Lỗi lặp lại".

### 9.4.7 Round 9 scope (remaining workshop KPI drill)

| Nguồn (persona) | Widget | Drill tới | Quyết định |
|---|---|---|---|
| workshop | KPI `cm_sla_breached` | `/cm/work-orders?sla_breached=1` | list tập bao KPI (§9.4.1); dùng filter R8 đã có |
| workshop | KPI `wo_to_assign` | — (KHÔNG drill) | **COMPOUND** PM open + CM open (2 doctype) → 1 list không khớp count → `drill=None` (§9.5 #10). Section table `wo_to_assign` liệt kê PM WO chi tiết. |

- **Canonical-value rule (chống vá triệu chứng):** KPI gộp nhiều nguồn/doctype KHÔNG
  được bịa drill về 1 list (count sẽ lệch). Để `drill=None` + cung cấp section table
  thay thế. `cm_sla_breached` đơn nguồn → drill 1-1 hợp lệ.

### 9.4.8 Round 10 scope (polish — every KPI drillable HOẶC documented)

**Wired round này (qa persona):**
- `list_capas(not_closed=1)` → status NOT IN [Closed] (khớp KPI `capa_open`).
- `list_capas(overdue=1)` → not-closed + due_date < today (khớp KPI `capa_overdue`).
- KPI `capa_open` → `/capas?not_closed=1`; `capa_overdue` → `/capas?overdue=1`.

**Inventory drill state đầy đủ (32 KPI / 8 persona) — drillable HOẶC lý do (§9.5 #10):**

| Persona | KPI | Drill | Lý do nếu KHÔNG drill |
|---|---|---|---|
| opsmgr | active_assets | /assets?lifecycle_status=Active | — |
| opsmgr | pm_due_7d | /pm/work-orders?due_before | — |
| opsmgr | incidents_critical | /incidents/list?severity=Critical | — |
| opsmgr | needs_pending | — | Draft (docstatus=0) chờ duyệt; needs list chưa hỗ trợ filter docstatus drill (backlog) |
| workshop | cm_sla_breached | /cm/work-orders?sla_breached=1 | — |
| workshop | pm_overdue | /pm/work-orders?status=Overdue | — |
| workshop | calib_due | /calibration/schedules?due_before | — |
| workshop | wo_to_assign | — | **COMPOUND** PM+CM 2 doctype (§9.4.7); section table backing |
| store | low_stock | /spare-parts?low_stock=1 | — |
| store | pending_alloc | — | section `pending_allocations` table backing; allocations list filter drill = backlog |
| store | pending_cycle | — | cycle-count đang đếm; chưa có list view filter trạng thái drill (backlog) |
| store | stockout_30d | — | metric window 30d trên stock; không có list 1-1 |
| qa | capa_overdue | /capas?overdue=1 | — |
| qa | capa_open | /capas?not_closed=1 | — |
| qa | rca_incomplete | — | predicate COMPOUND (mở AND rca_required AND root_cause trống); section findings backing |
| qa | compliance_score | — | điểm số scorecard, KHÔNG phải tập record → không có list |
| tech | today_jobs/pm_week/cm_urgent/done_30d | — | metric CÁ NHÂN ("của tôi"); section `my_wo_today`/`my_cm` table đã liệt kê chi tiết |
| clinical | dept_assets/inc_open/nr_submitted/awaiting_release | — | scope theo khoa (fail-closed §5.5); section `dept_incidents`/`dept_needs` backing; drill cần truyền dept → backlog |
| doc | docs_pending/docs_expiring/comm_pending/comm_open_nc | — | section `docs_expiring`/`commissioning_queue` table backing; drill filter chuyên biệt = backlog |
| admin | total_users/pending_users/vendor_engineers | /user-profiles[?...] | **CẬP NHẬT §9.4.9** — admin có `data.admin` → drill sang quản lý user filtered |
| admin | audit_chain | /audit-trail | **CẬP NHẬT §9.4.9** — status PASS/FAIL → mở Nhật ký Kiểm toán (không filter; viewer toàn cục) |

> **Nguyên tắc:** KPI KHÔNG drill khi (a) metric không phải tập record (score/status),
> (b) compound nhiều doctype, (c) personal/scoped — và LUÔN có **section table backing**
> để user vẫn xem được chi tiết. KHÔNG bịa drill 1-list cho count compound (§9.5 #10).
> Các ô "backlog" là ứng viên drill round sau (cần thêm filter list chuyên biệt).

### 9.5 Acceptance bổ sung (drill-down)

9. KPI/segment có `drill` → render clickable (RouterLink), click điều hướng đúng
   `route` + `query`; KPI không drill → card tĩnh (không link, không con trỏ pointer giả).
10. List view đích pre-apply filter từ query on mount; tổng số dòng hiển thị khớp con
    số đã click (cùng thời điểm dữ liệu) — round-trip nhất quán.
11. Query dùng canonical code (không nhãn VI); chip filter hiển thị nhãn VI tương ứng.
12. **Drill gating = capability (`canAccessDrill`):** KPI drill chỉ clickable khi user
    có `<domain>.read` của route đích (mirror bước 4 `resolveRouteAccess`). Thiếu cap →
    card tĩnh, KHÔNG đẩy `/unauthorized`. **opsmgr (2026-06-02):** nay có
    `pm.read` (imm08), `repair.read` (imm09), `corrective.read` (imm12) read-only →
    các KPI vận hành của opsmgr (PM đến hạn, Sự cố Critical, donut severity, bars CM)
    PHẢI clickable và drill sang list filtered xem được. opsmgr KHÔNG có write/create
    các module này → trong list không thấy nút duyệt/sửa/tạo (read-only đúng vai giám sát).

**Canonical persona → capabilities (drill-relevant, 2026-06-02):**
| Persona / Role Profile | Read caps liên quan drill | Ghi chú |
|---|---|---|
| opsmgr / "Trưởng phòng VT-TTBYT" | `data.read`, `needs.read`, `spec.read`, `procurement.read`, `commissioning.read`, **`pm.read`**, **`repair.read`**, **`corrective.read`** | 3 cap **in đậm** = oversight read-only mới; không kèm write |
| workshop / "Trưởng xưởng kỹ thuật" | full CRUD `pm/repair/calibration/corrective` | manager 4 module bảo trì |

### 9.6 Test cases drill-down (viết trước — TDD)

**BE (`bench run-tests`)**
| ID | Mô tả | Kỳ vọng |
|---|---|---|
| D-BE-7 | `get_persona_dashboard('opsmgr')` KPI "active" | có `drill.query.lifecycle_status == "Active"` (canonical, không VI) |
| D-BE-8 | `lifecycle_breakdown` entries | mỗi entry có `code` canonical khớp filter list, không rỗng |
| D-BE-9 | KPI không drill (vd footer info) | `drill is None`, không bịa route |

**FE (`vitest`)**
| ID | Mô tả | Kỳ vọng |
|---|---|---|
| D-FE-8 | `KpiCard` có `kpi.drill` | render `<RouterLink>` với `to` = {path, query} |
| D-FE-9 | `KpiCard` không `drill` | render `<div>` tĩnh, không link |
| D-FE-10 | `StatusDonutChart` click segment | emit `segment-click` kèm `{ label, code, value }` |
| D-FE-11 | `AssetListView` mount với `route.query.lifecycle_status='Active'` | filter pre-apply, `fetchList` gọi với `lifecycle_status:'Active'`, chip hiện nhãn VI |
| D-FE-12 | `AssetListView` đổi query lần 2 | watch → re-apply filter mới |

---

## 9.4.9 Admin dashboard interactivity (Session 2026-06-02, R1–R10)

> **Bug user báo (2026-06-02):** dashboard `admin` các khối "Người dùng · Phân quyền ·
> Master data · Audit chain" + "Hoạt động gần đây" CHỈ NHÌN ĐƯỢC, không click.
> Root cause: (1) 4 KPI admin gọi `_kpi(...)` KHÔNG truyền `drill=` → BE gửi descriptor
> null → `KpiCard` render tĩnh; (2) `TimelineCard`/`ListCard` render `<span>`, KHÔNG có
> điều hướng row-level → feed "Hoạt động gần đây" không truy về source (vi phạm CLAUDE.md
> §5 "Dashboard truy về source", §10 lifecycle event root_record); (3) subtitle
> "Người dùng · Phân quyền · Master data · Audit chain" là **text trang trí** (PageHeader
> subtitle) — user tưởng là tile bấm được.

**Quyết định BA (admin = full quyền `data.admin`, KHÔNG bị gate capability như opsmgr):**

| # | Widget admin | Loại | → Drill target | Match | Round |
|---|---|---|---|---|---|
| 1 | KPI `total_users` "Tổng người dùng" | KPI | `/user-profiles` | superset (toàn bộ user) | R1 |
| 2 | KPI `pending_users` "Chờ phê duyệt" | KPI | `/user-profiles?approval_status=Pending` | khớp (đếm `imm_approval_status=Pending`; list filter cùng field) | R1 |
| 3 | KPI `audit_chain` "Chuỗi audit" | KPI status | `/audit-trail` | non-filter (status PASS/FAIL không phải tập record; mở viewer toàn cục) | R1 |
| 4 | KPI `vendor_engineers` "Vendor Engineer" | KPI | `/user-profiles?role=Vendor Engineer` | khớp (đếm `Has Role`; list filter `role`) | R1 |
| 5 | Section `users_pending` ListCard | row | `/user-profiles/:user` mỗi dòng | row→detail | R3 |
| 6 | Section `audit_recent` TimelineCard | row | `/incidents/:asset` (root_record) mỗi dòng | row→source (§10) | R2 |
| 7 | Subtitle 4 pillar | hub tiles | `/user-profiles` · `/admin/roles` · master-data hub · `/audit-trail` | nav tiles thật | R4 |

- **Canonical-value (§9.2):** `approval_status=Pending`, `role=Vendor Engineer` là canonical
  code English/raw role-name khớp filter list — KHÔNG đẩy nhãn VI. `pending_users` BE đếm
  `imm_registration_status=Pending` (custom field) NHƯNG list filter dùng `imm_approval_status`;
  hai field này đồng nghĩa "chờ duyệt" → BA xác nhận drill dùng `approval_status=Pending`
  (field list view hỗ trợ). Round-trip: nếu lệch (do field khác) → superset hợp lệ, không claim khớp tuyệt đối.
- **Gate §9.3:** `UserProfileListView` + `AuditTrailListView` PHẢI đọc `route.query` on mount
  (trước đây chưa) → pre-apply filter. `UserProfileListView` keys: `approval_status`, `role`,
  `department`, `search`. `AuditTrailListView` keys: `asset`, `event_type`, `search`.
- **Capability:** admin profile có `data.admin` → `canAccessDrill('/user-profiles')` &
  `('/audit-trail')` đều pass (admin bypass + `data.admin`). `/audit-trail` route cần
  `audit.read`; DRILL_MODULE_RULES map `/audit-trail`→imm16→`compliance.read` (drift cũ).
  Thêm rule `/user-profiles`→system (null cap) + sửa `/audit-trail` không gate sai. Admin bypass nên live OK; sửa để persona khác (qa có audit.read) cũng drill đúng.

## 9.7 Row-level drill (section ListCard / TimelineCard) — Session R2, R3, R9

> Mở rộng §9.1 (drill KPI) xuống **row** của section table/timeline: mỗi dòng dữ liệu là
> một record thật → click mở detail record nguồn (CLAUDE.md §5, §10 root_record).

- `ListCard` thêm optional prop `rowTo?: (row) => RouterLocationRaw | null`. Khi trả non-null
  → render `<RouterLink>` bọc row (hoặc cell `name`); null → row tĩnh (giữ hành vi cũ).
- `TimelineCard` thêm optional prop `rowTo?: (row) => RouterLocationRaw | null` tương tự;
  mỗi `<li>` thành link khi có target. Source ưu tiên: `root_record`/`asset` → route module
  tương ứng (incident→`/incidents/:asset` hoặc `/incidents/list?asset=`, wo→`/pm|cm/...`).
- **Gate:** row-drill cũng đi qua `canAccessDrill(route.path, can)` — thiếu cap → row tĩnh
  (KHÔNG link /unauthorized). Mirror §9.5 #12.
- **Non-drill row hợp lệ:** dòng không có record nguồn nhận diện được (`root_record` trống) →
  `rowTo` trả null → tĩnh; KHÔNG bịa link.

## 9.8 Master-data hub (admin pillar §9.4.9 #7) — Session R4

- Subtitle trang trí → thay bằng **section "Lối tắt quản trị"** (DashboardSection) gồm 4 nav
  tile thật: Người dùng (`/user-profiles`), Phân quyền (`/admin/roles`), Dữ liệu gốc (hub),
  Nhật ký Kiểm toán (`/audit-trail`).
- "Dữ liệu gốc" là **hub** (không 1 route) → tile mở popover/section sub-link: Device Model
  (`/device-models`), Nhà cung cấp (`/suppliers`), Hợp đồng dịch vụ (`/service-contracts`).
  Hoặc render 3 tile master phẳng. BA chọn: render phẳng 3 master tile (đơn giản, không popover).
- Mỗi tile gate `canAccessDrill` (admin pass hết). Component `NavTileCard.vue` (mới, dùng chung).

## 9.9 Persona drill expansion (R5–R8) — tech/clinical/doc/store

> Đóng backlog §9.4.8 "0 KPI drillable" cho personas còn tĩnh, HOẶC document non-drill có lý do.

| Persona | KPI | R | Drill / non-drill |
|---|---|---|---|
| tech | `today_jobs`/`pm_week` | R5 | `/pm/work-orders?assignee=me&...` nếu list hỗ trợ `assignee`; nếu KHÔNG → giữ section table backing (personal scope) |
| tech | `cm_urgent` | R5 | `/cm/work-orders?priority=High` nếu khớp; else non-drill |
| clinical | `inc_open` | R6 | `/incidents/list?department=<dept>&status=Open` nếu list hỗ trợ `department`; else non-drill (scoped) |
| clinical | `nr_submitted` | R6 | needs list nếu hỗ trợ; else non-drill |
| doc | `docs_expiring` | R7 | `/documents?expiring=1` nếu list hỗ trợ; else non-drill (section backing) |
| doc | `docs_pending` | R7 | `/documents?status=Pending` nếu khớp; else non-drill |
| store | `pending_alloc`/`pending_cycle` | R8 | inventory list filter nếu hỗ trợ; else document non-drill (đã có section backing) |

> **Quy tắc R5–R8:** CHỈ wire drill khi list view đích THỰC SỰ hỗ trợ filter key (đọc query,
> count khớp/superset §9.5 #10). Nếu list chưa hỗ trợ → KHÔNG bịa drill; ghi rõ "backlog:
> cần thêm filter X vào list Y" và giữ section table backing. Verify từng list view trước khi wire.
