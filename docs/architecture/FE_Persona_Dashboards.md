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
