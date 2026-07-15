# ADR-MOBILE-056 — `getPmDashboardStats` (`imm08.get_pm_dashboard_stats`) curate vào OAS mirror (**CR-31a · MỞ NHÁNH Dashboard KPI R1 (IMM-07/IMM-08)** — bồi ĐÚNG 1 GET-read path trả BỘ CHỈ SỐ PM (compliance 7-key + trend 6 tháng) cho màn "Bảng chỉ số PM", endpoint ĐẦU TIÊN của surface Dashboard-KPI; forward-reserve `getCalibrationKpis`/`getRepairKpis`; **CONTRACT-ONLY** — backend LIVE `@api/imm08.py:164` + service `@services/imm08.py:1210`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-056 |
| Phase | C — API contract (codegen-ready) — CONTRACT-ONLY (0 `.py` runtime) |
| Ngày | 2026-07-15 |
| Tác giả | BA (spec) → BE (Bước-4 curate YAML + guard test) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; `200`-oneOf KHÔNG discriminator) · **precedent tag `pm` cho read IMM-08**: **ADR-MOBILE-054** §2(b) (`getDuePmSchedules` — tag `pm` REUSE `getPmWorkOrder`, KHÔNG `work-order`) · **precedent flat-object read inline-oneOf ∈ `_MVP_READ_ENVELOPE`**: `getAssetKpi` (yaml:7541/10720) · **precedent nullable-khi-mẫu-0 ∉ required**: `AssetKpi.pm_compliance_pct` (yaml:7574 — TWIN semantic của `compliance_rate_pct`) · **domain SoT**: Core Doc IMM-08 [`../imm-08/05_API_Specification.md`](../imm-08/05_API_Specification.md) endpoint #9 + INV-PM-KPI-1..6 |

---

## 1. Bối cảnh

Surface **"Bảng chỉ số PM"** (Dashboard KPI) trên mobile hiển thị 2 khối cho quản-lý xưởng / VP Block2 / CMMS Admin:

- **7 chỉ số tuân-thủ PM** (compliance %, tổng-lịch, đúng-hạn, quá-hạn-tháng, chờ-tháng, quá-hạn-toàn-hệ, trễ-trung-bình).
- **Xu-hướng 6 tháng** (`trend_6months`) — cột đúng-hạn / tổng theo tháng.

Endpoint `get_pm_dashboard_stats` **ĐÃ LIVE** @web-BE (KHÁC `getDuePmSchedules`/ADR-054 phải build `.py` mới) ⇒ round này **CONTRACT-ONLY**: curate 1 path + 4 schema vào mirror, **0** `.py`/reload/migrate. Đây là endpoint **ĐẦU TIÊN** của surface Dashboard-KPI (Trục B); `getCalibrationKpis` (IMM-11) + `getRepairKpis` (IMM-09) = **forward-reserve** vòng kế (mỗi cái theo module-tag riêng — xem §2(b)).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler @`api/imm08.py:163-168` = bare `@frappe.whitelist()` (GET, KHÔNG `allow_guest`, KHÔNG `rbac.require`):
  ```python
  @frappe.whitelist()
  def get_pm_dashboard_stats(year: int = None, month: int = None) -> dict:
      today = getdate(nowdate())
      return handle(svc.get_dashboard_stats,
                    year=int(year) if year else today.year,
                    month=int(month) if month else today.month)
  ```
- Service `get_dashboard_stats(*, year, month)` @`services/imm08.py:1210-1293` return-dict VERBATIM @`:1279-1293`:
  ```python
  return {
      "kpis": {
          "compliance_rate_pct": compliance_rate,  # round(on_time/total*100,1) if total else None
          "total_scheduled": total,                # len(scheduled)               → int
          "completed_on_time": len(on_time),       # int
          "overdue_in_month": overdue_in_month,    # int (Overdue ∧ due_date ∈ tháng)
          "pending_in_month": pending_in_month,    # int (chưa xong, chưa quá hạn)
          "overdue": overdue_count,                # int (count_overdue_pm() GLOBAL — RC-10)
          "avg_days_late": avg_days_late,          # round(...,1) if late_days else 0.0 → number
      },
      "trend_6months": trend,                      # list[{month,total,on_time,rate}] × 6
  }
  ```
  Mỗi phần-tử `trend` @`:1275-1278`: `{"month": f"{y:04d}-{m:02d}", "total": t, "on_time": c_on, "rate": round(c_on/t*100,1) if t else 0.0}`.
- `handle(...)` @`utils/api_handler.py:33` → `_ok(dict)`/`_err(...)` — envelope hợp-đồng chuẩn (Decision-B: lỗi nghiệp-vụ TRÊN HTTP-200 body `Error`).
- Domain-SoT đã đặc-tả đầy-đủ contract này ở IMM-08 `05_API_Specification.md` (endpoint #9 + INV-PM-KPI-1..6: `compliance_rate_pct=null` khi `total_scheduled==0`; `overdue` GLOBAL bất-biến RC-10; population loại `Cancelled`).

---

## 2. Quyết định

### (a) 200 = **inline `oneOf [PmDashboardStatsEnvelope, Error]`** (Decision-B, 0 discriminator)

`data` = **`PmDashboardStats` OBJECT PHẲNG** `{kpis, trend_6months}` — KHÔNG pagination, KHÔNG list-envelope. Route 2 nhánh MÁY-ĐỌC bằng CLOSED-SCHEMA + disjoint required-set (Env `req[success,data]` vs Error `req[success,error,code,http_status]`), theo `body.success` — mirror `getAssetKpi` (flat-object read). Vào **`_MVP_READ_ENVELOPE`** (inline oneOf, KHÔNG response-component); **KHÔNG** `_MVP_LIST_ENVELOPE` (dashboard read ≠ list ⇒ `_MVP_LIST_ENVELOPE` GIỮ NGUYÊN). **Invariant `count==rows` KHÔNG áp** (0 list, 0 pagination).

### (b) operationId `getPmDashboardStats` (DOMAIN), **tag `pm`** — KHÔNG `dashboard`

tag **`pm`** = REUSE tag `getPmWorkOrder`/`getDuePmSchedules` (mọi read-endpoint IMM-08). **Loại tag `dashboard` MỚI** dù đề mục cho 2 lựa chọn: (1) 100% precedent mirror dùng **module-domain tag** (asset/pm/calibration/work-order/incident/inventory/compliance/notification/commissioning) — 0 tag theo-màn-hình; introduce lone surface-tag = fork taxonomy + phá đồng-nhất assertion tag-per-endpoint; (2) forward-reserve `getCalibrationKpis` (→ `calibration`) / `getRepairKpis` (→ `work-order`) là **đơn-module** ⇒ mỗi cái theo module-tag; "màn Bảng chỉ số" là **FE-composition** (FE gom 3 call module-tag thành 1 màn, Y HỆT device-profile gom nhiều call `asset`), KHÔNG phải API-tag concern; (3) ADR-054 §2(b) đã chốt precedent read-IMM08 = `pm` (KHÔNG `work-order` — đó là tag write-action). naming-guard `PmDashboard*` ∩ (`PmWorkOrder*` ∪ `PmSchedule*` ∪ `DuePmSchedule*`) == ∅.

### (c) 4 schema CLOSED (`additionalProperties:false`) — VERBATIM return-dict, 0 invention

- **`PmDashboardKpis`** — EXACT **7 prop** VERBATIM `@services/imm08.py:1280-1291`:
  - `compliance_rate_pct` = `type:number` **`nullable:true`** ∧ **∉ `required`** — `None` khi `total_scheduled==0` (`round(...) if total else None` @`:1253`). **Precedent 1:1 `AssetKpi.pm_compliance_pct`** (yaml:7574 — CÙNG semantic "null khi mẫu 0", CÙNG idiom `number`+`nullable:true`+∉required). Khai NON-null → strict Dart/Kotlin deser CRASH trên `null` hợp-lệ.
  - `total_scheduled`, `completed_on_time`, `overdue_in_month`, `pending_in_month`, `overdue` = `type:integer` **∈ `required`** (LUÔN emit int vô-điều-kiện).
  - `avg_days_late` = `type:number` **∈ `required`** — `round(...,1) if late_days else 0.0` @`:1254` ⇒ LUÔN number (KHÔNG null; nhánh else = `0.0`).
  - `required` = **6 key** `[total_scheduled, completed_on_time, overdue_in_month, pending_in_month, overdue, avg_days_late]` (chỉ `compliance_rate_pct` ngoài).
- **`PmDashboardTrendItem`** — EXACT **4 prop** `@:1275-1278`, `required` = **cả 4**: `month:string` (`"YYYY-MM"`), `total:integer`, `on_time:integer`, `rate:number` (LUÔN number — `round(...) if t else 0.0`).
- **`PmDashboardStats`** — `{kpis:$ref PmDashboardKpis, trend_6months:array items $ref PmDashboardTrendItem}`, `required:[kpis, trend_6months]` (cả 2 LUÔN emit).
- **`PmDashboardStatsEnvelope`** — `{success:{type:boolean, enum:[true]}, data:$ref PmDashboardStats}`, `required:[success, data]`.

### (d) 2 typed query-param `year`+`month` (integer, `required:false`) — **KHÔNG khai `default:` trong YAML**

pattern CR-05 typed-query-param (mirror `getDueCalibrations` days/limit) NHƯNG **KHÔNG** `default:` — **điểm KHÁC có-chủ-đích**: backend default = **`nowdate()` year/month động** (`today.year`/`today.month` @`api/imm08.py:165-168`), KHÔNG hằng-số. Khai `default: 2026` (static) → codegen ép client GỬI năm chốt-cứng → mỗi năm client drift stale, override server-default động. `required:false` + no-default ⇒ client omit → server tự dùng tháng hiện-tại. `month` mô-tả range 1–12 ở `description` (KHÔNG hard `enum`/`min`/`max` — mirror `getDueCalibrations` no-constraint, tránh over-constrain).

### (e) 403 = SINGLE-SHAPE `Forbidden` **dispatcher-ONLY** (bare `@whitelist`, 0 cap-403)

Handler bare `@frappe.whitelist()` KHÔNG `allow_guest`, KHÔNG `rbac.require` ⇒ guest/no-token trip **dispatcher-403** (`PermissionError` `__init__.py:876`, HTTP-403 raw `FrappeRawError`) TRƯỚC `handle()`; bearer-expired → **401** (`AuthenticationError`). KHÔNG in-handler cap-403 reachable ⇒ 403-slot SINGLE `Forbidden` (mirror `getDueCalibrations`/`getAssetKpi`, KHÁC `report_incident` dual-shape). **ĐỐI XỨNG A16**: path vào `_MVP_BUSINESS_PATHS` ⇒ `_PATHS_REQUIRE_401` ∧ `_PATHS_REQUIRE_403` tự +1 (đếm 401==403 GIỮ NGUYÊN). status-set `[200, 401, 403]`.

### (f) CONTRACT-ONLY — 0 `.py`/reload/migrate

`get_pm_dashboard_stats` + `get_dashboard_stats` **ĐÃ LIVE** @source ⇒ `git diff` round này = CHỈ `docs/mobile/*` (yaml + ADR + README) + `assetcore/tests/test_mobile_oas.py` (guard). **0** file `.py` runtime, **0** gunicorn reload (KHÔNG HARD-STOP USER — `[AUTO]`), **0** `bench migrate`.

---

## 3. Path + schema (copy-ready cho BE Bước-4)

Đặt block path **liền sau** cụm IMM-08 (`get_pm_calendar`/`getDuePmSchedules`) trong `paths:`; 4 schema đặt **liền sau** `AssetKpi*` (hoặc cụm PM) trong `components.schemas:`.

```yaml
# paths:
/api/method/assetcore.api.imm08.get_pm_dashboard_stats:
  get:
    tags: [pm]
    operationId: getPmDashboardStats
    summary: '[Bảng chỉ số PM] Bộ chỉ số tuân thủ PM + xu hướng 6 tháng — dashboard-read'
    description: >
      imm08.get_pm_dashboard_stats(year=None, month=None) — 2 typed query-param (KHÔNG default
      YAML; backend default nowdate year/month @api/imm08.py:165). 200 = PmDashboardStats
      {kpis (7-key compliance), trend_6months (6 phần tử)}. compliance_rate_pct = null khi
      total_scheduled==0 (INV-PM-KPI-3); overdue = count GLOBAL (RC-10, KHÁC overdue_in_month
      bó tháng). Bare @whitelist → GET, KHÔNG cap-gate (guest dispatcher-403 / bearer-expired 401).
    parameters:
      - name: year
        in: query
        required: false
        schema: { type: integer }
        description: >
          Năm (YYYY) của khối tháng. Bỏ trống ⇒ backend dùng năm hiện tại (getdate(nowdate()).year
          @api/imm08.py:165) — KHÔNG khai default YAML (default động, không hằng).
        example: 2026
      - name: month
        in: query
        required: false
        schema: { type: integer }
        description: >
          Tháng (1–12) của khối tháng. Bỏ trống ⇒ backend dùng tháng hiện tại. KHÔNG khai default
          YAML (default động).
        example: 7
    responses:
      '200':
        description: >
          200 bộ chỉ số PM. oneOf 2 nhánh CLOSED-SCHEMA disjoint required-set (KHÔNG discriminator —
          read-path): (a) PmDashboardStatsEnvelope {success:true, data:PmDashboardStats}; (b) Error
          {success:false, code, http_status} — lỗi nghiệp-vụ / cap-403 / 401 guest arrive HTTP-200.
          Route theo body.success.
        content:
          application/json:
            schema:
              oneOf:
                - $ref: '#/components/schemas/PmDashboardStatsEnvelope'
                - $ref: '#/components/schemas/Error'
      '401': { $ref: '#/components/responses/Unauthorized401' }
      '403': { $ref: '#/components/responses/Forbidden' }

# components.schemas:
PmDashboardStatsEnvelope:
  type: object
  additionalProperties: false
  description: '200 success envelope getPmDashboardStats — _ok(PmDashboardStats). imm08.py:1279.'
  properties:
    success: { type: boolean, enum: [true] }
    data: { $ref: '#/components/schemas/PmDashboardStats' }
  required: [success, data]

PmDashboardStats:
  type: object
  additionalProperties: false
  description: >
    Payload bộ chỉ số PM (màn "Bảng chỉ số PM") — services/imm08.py:1279-1293. 2 khối LUÔN emit
    ⇒ required cả 2.
  properties:
    kpis: { $ref: '#/components/schemas/PmDashboardKpis' }
    trend_6months:
      type: array
      description: 'Xu hướng 6 tháng gần nhất (ĐÚNG 6 phần tử, cũ→mới). imm08.py:1256-1278/1292.'
      items: { $ref: '#/components/schemas/PmDashboardTrendItem' }
  required: [kpis, trend_6months]

PmDashboardKpis:
  type: object
  additionalProperties: false
  description: >
    7 chỉ số tuân-thủ PM khối-tháng + toàn-hệ — services/imm08.py:1280-1291. 6 field always-present
    ∈ required; compliance_rate_pct nullable (null khi total_scheduled==0, INV-PM-KPI-3) ∉ required
    (mirror AssetKpi.pm_compliance_pct).
  properties:
    compliance_rate_pct:
      type: number
      nullable: true
      description: >
        % tuân-thủ PM khối-tháng = completed_on_time / total_scheduled × 100 (round 1). null khi
        total_scheduled==0 (INV-PM-KPI-3, imm08.py:1253) — FE render '—'/N-A, KHÔNG 0%. Population
        loại Cancelled (INV-PM-KPI-6).
    total_scheduled:
      type: integer
      description: 'Số WO PM đến-hạn trong tháng (mẫu compliance, loại Cancelled). imm08.py:1283.'
    completed_on_time:
      type: integer
      description: 'WO PM Completed đúng-hạn trong tháng (tử compliance). imm08.py:1284.'
    overdue_in_month:
      type: integer
      description: 'WO status==Overdue ∧ due_date ∈ tháng (⊆ total_scheduled, INV-PM-KPI-1). imm08.py:1285.'
    pending_in_month:
      type: integer
      description: 'WO trong tháng chưa xong ∧ chưa quá hạn (INV-PM-KPI-1). imm08.py:1286.'
    overdue:
      type: integer
      description: >
        ⚠️ count GLOBAL toàn-hệ status==Overdue (count_overdue_pm(), RC-10/INV-PM-KPI-2) — khớp
        launcher widget + drill ?overdue=1. KHÁC overdue_in_month (bó tháng). imm08.py:1289.
    avg_days_late:
      type: number
      description: 'Số ngày trễ trung-bình của WO hoàn-thành-trễ (0.0 khi 0 WO trễ). imm08.py:1290.'
  required:
    - total_scheduled
    - completed_on_time
    - overdue_in_month
    - pending_in_month
    - overdue
    - avg_days_late

PmDashboardTrendItem:
  type: object
  additionalProperties: false
  description: '1 tháng trong trend_6months — services/imm08.py:1275-1278. Cả 4 key LUÔN emit.'
  properties:
    month:
      type: string
      description: 'Tháng "YYYY-MM" (f"{y:04d}-{m:02d}"). imm08.py:1276.'
      example: '2026-07'
    total:
      type: integer
      description: 'Số WO PM đến-hạn tháng đó (loại Cancelled, INV-PM-KPI-6). imm08.py:1273/1276.'
    on_time:
      type: integer
      description: 'WO Completed đúng-hạn tháng đó. imm08.py:1274/1276.'
    rate:
      type: number
      description: '% đúng-hạn tháng đó = on_time/total×100 (round 1; 0.0 khi total==0). imm08.py:1277.'
  required: [month, total, on_time, rate]
```

---

## 4. Guard test (`test_mobile_oas.py` — class RIÊNG `TestMobileGetPmDashboardStatsContract`, 9 TC a..i)

ĐỐI XỨNG `TestMobileGetAssetKpiContract`:

- **a** — path tồn tại + CHỈ GET + opId `getPmDashboardStats` + tag `[pm]`; ∈ `_MVP_BUSINESS_PATHS` + `_MVP_READ_ENVELOPE`; ∉ `_MVP_LIST_ENVELOPE`.
- **b** — ĐÚNG 2 typed query-param `year`/`month` (`type:integer`, `required:false`, **KHÔNG `default` key trong schema** — anti static-default drift); KHÔNG requestBody; 0 param khác (`page`/`filters`/`days`).
- **c** — `PmDashboardKpis` CLOSED, EXACT **7 prop** {compliance_rate_pct,total_scheduled,completed_on_time,overdue_in_month,pending_in_month,overdue,avg_days_late} — 0 thừa/thiếu; `required` == 6 (đúng tập, `compliance_rate_pct` ∉); 5 field `integer` + `compliance_rate_pct`/`avg_days_late` `number`.
- **d** — `compliance_rate_pct` `nullable:true` ∧ ∉ `required` (anti false-non-null); `avg_days_late` NON-nullable ∈ required (anti over-null — nhánh else=0.0); 0 field Check integer-enum/boolean.
- **e** — `PmDashboardTrendItem` CLOSED, EXACT 4 prop {month:string, total:integer, on_time:integer, rate:number}, `required`==cả 4.
- **f** — `PmDashboardStats` CLOSED, `required:[kpis,trend_6months]`; `kpis.$ref`==PmDashboardKpis; `trend_6months.items.$ref`==PmDashboardTrendItem (array).
- **g** — 200 inline oneOf ĐÚNG 2 `[PmDashboardStatsEnvelope, Error]` 0-discriminator + `PmDashboardStatsEnvelope` CLOSED `{success:enum[true], data:$ref PmDashboardStats}`; slot `{200,401,403}` (401 `Unauthorized401` + 403 `Forbidden` SINGLE-shape).
- **h** — 4 schema mới KHÔNG orphan (Envelope←response, Stats←Envelope, Kpis+TrendItem←Stats) + 0 dangling; membership reconcile (path/opId +1; `c5`/`_PARITY_BUSINESS_PATHS` +1; `_MVP_READ_ENVELOPE` +1; `_MVP_LIST_ENVELOPE` GIỮ NGUYÊN).
- **i** — naming-guard `PmDashboard*` ∩ (`PmWorkOrder*`∪`PmSchedule*`∪`DuePmSchedule*`) == ∅ + **live-signature parity** `inspect.signature(imm08.get_pm_dashboard_stats).parameters == {year, month}`.

**TC hiện có tự phủ (0 TC mới):** `TC-MOB-OAS-09` (0 dangling — 4 schema đều $ref'd) · `TC-MOB-OAS-10` (0 orphan mới — allow-list `_RESERVED_ORPHANS` GIỮ NGUYÊN) · `TC-MOB-OAS-11` (401 coverage — auto qua `_MVP_BUSINESS_PATHS`) · **`TC-MOB-OAS-12` (getPmDashboardStats declare CẢ 401+403)** — auto qua `_PATHS_REQUIRE_401`==`_PATHS_REQUIRE_403`==`_MVP_BUSINESS_PATHS`|... (đếm 401==403 GIỮ đối-xứng).

### Bulk-bump bookkeeping (reconcile — ⚠️ grep-verify @source TRƯỚC bump)

- `_EXPECTED_TEST_COUNT` 783 → **792** (+9); `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 783 → **792**.
- cross-file `test_mobile_docset.py`: `_GUARD_SUITE_SUM` 926 → **935**; `_MOBILE_OAS_TOTAL` 952 → **961**.
- path/opId 86 → **87**; `c5` / `_PARITY_BUSINESS_PATHS` 75 → **76**; `_MVP_READ_ENVELOPE` +1 (ĐỊNH NGHĨA `_PM_DASHBOARD_STATS_PATH` const + entry vào set read-envelope); `_MVP_LIST_ENVELOPE` **GIỮ NGUYÊN 13** (dashboard read ≠ list); membership `_MVP_BUSINESS_PATHS` (401/403 symmetry) tự +1.
- ⚠️ **Baseline 86/783/75/13/926/952 grounded @source 2026-07-15 — đa-phiên race** (memory `multi_session_concurrency` + CR-25c submitBaselineChecklist đang in-flight uncommitted): BE **grep-verify @source ngay trước bump**, đừng tin số học. Verify next-free ADR số (kỳ vọng 056 — nếu bị chiếm, dời + reconcile README).

---

## 5. Hệ quả

- **+**: màn "Bảng chỉ số PM" codegen-ready (typed model `PmDashboardStats`/`PmDashboardKpis`/`PmDashboardTrendItem`); FE mobile bind 7-tile + biểu-đồ trend 6 tháng theo server-flag (compliance null→'—'; `overdue` GLOBAL khớp launcher; KHÔNG re-derive client-clock — memory `overdue_server_flag_ssot`).
- **+**: mở surface **Dashboard-KPI** (Trục B) — `getCalibrationKpis`/`getRepairKpis` forward-reserve theo CÙNG khuôn (inline oneOf read, module-tag riêng, closed-schema VERBATIM).
- **+**: false-green chặn bằng live-signature parity + no-orphan + 7-key VERBATIM + nullable-per-field guard (compliance ∉required vs avg_days_late ∈required).
- **−/đánh đổi**: tag `pm` (KHÔNG `dashboard`) ⇒ 3 KPI-endpoint tương-lai nằm ở 3 tag module khác nhau — màn dashboard là FE-composition (chấp-nhận, đúng precedent device-profile). Đổi sau = 1 ADR mới Supersede (KHÔNG xoá 056).
- **KHÔNG** đổi workflow / DocType / migrate / reload (CONTRACT-ONLY, backend LIVE). Working-tree để USER review — KHÔNG git commit/push.

### Alternatives loại

| Phương án | Lý do loại |
|---|---|
| tag `dashboard` (MỚI) | Fork module-domain taxonomy (100% precedent module-tag); forward-reserve siblings đơn-module ⇒ mỗi cái module-tag riêng; "màn dashboard" = FE-composition, KHÔNG API-tag. ADR-054 §2(b) chốt read-IMM08=`pm`. |
| `compliance_rate_pct` NON-nullable ∈ required | `None` khi total==0 (INV-PM-KPI-3) → strict Dart/Kotlin deser CRASH; phá precedent `AssetKpi.pm_compliance_pct`. |
| `avg_days_late` nullable | Nhánh else = `0.0` (LUÔN number) — nullable = sai-nguồn. |
| khai `default: <year/month>` trong YAML | Default backend = `nowdate()` ĐỘNG, KHÔNG hằng; static default → client gửi năm chốt-cứng drift stale, override server. |
| response-component (như `DueCalibrationList`) | read flat-object dùng **inline** oneOf (mirror `getAssetKpi`); ∈ `_MVP_READ_ENVELOPE` KHÔNG list-envelope. |
| ∈ `_MVP_LIST_ENVELOPE` | dashboard stats ≠ list (0 rows/pagination). |
| status-line 404/4xx | Decision-B — lỗi TRÊN HTTP-200 body Error. |
| 403 dual-shape (như report_incident) | 0 `rbac.require` in-handler ⇒ chỉ dispatcher-403 SINGLE `Forbidden`. |
| bịa/thêm/bớt field vs return-dict | VERBATIM 7-key + 4-key trend @source; 0 invention. |

**Accepted.**
