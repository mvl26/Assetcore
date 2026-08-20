# ADR-MOBILE-057 — `getCalibrationKpis` (`imm11.get_calibration_kpis`) curate vào OAS mirror (**CR-31b · Dashboard KPI R1 (IMM-11)** — bồi ĐÚNG 1 GET-read path trả BỘ CHỈ SỐ HIỆU CHUẨN phạm-vi THÁNG (`kpis` 6-key) cho màn "Bảng chỉ số hiệu chuẩn"; **SIBLING của `getPmDashboardStats`/ADR-056** trong surface Dashboard-KPI (Trục B); **CONTRACT-ONLY** — backend LIVE `@api/imm11.py:146` + service `@services/imm11.py:1171`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-057 |
| Phase | C — API contract (codegen-ready) — CONTRACT-ONLY (0 `.py` runtime) |
| Ngày | 2026-07-15 |
| Tác giả | BA (spec) → BE (Bước-4 curate YAML + guard test) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; `200`-oneOf KHÔNG discriminator) · **precedent surface Dashboard-KPI + flat-object read inline-oneOf ∈ `_MVP_READ_ENVELOPE`**: **ADR-MOBILE-056** (`getPmDashboardStats` — endpoint ĐẦU surface; SIBLING trực-tiếp) · **precedent tag `calibration` cho read IMM-11**: `getCalibration`/`listCalibrations`/`getDueCalibrations`/`sendToLab` (yaml:11539/14204/14426/12615) · **domain SoT**: Core Doc IMM-11 [`../imm-11/05_API_Specification.md`](../imm-11/05_API_Specification.md) §0.1.10 + §12 (`get_calibration_kpis`) + §6.1 (canonical-value rule KPI==drill) |

---

## 1. Bối cảnh

Surface **"Bảng chỉ số hiệu chuẩn"** (Dashboard KPI, IMM-11) trên mobile hiển thị **1 khối 6 chỉ số** hiệu chuẩn phạm-vi THÁNG cho quản-lý xưởng / PTP Khối 2 / CMMS Admin:

- `total_this_month` — tổng phiếu hiệu chuẩn `scheduled_date` trong tháng.
- `completed` — số phiếu ĐẠT (Passed ∪ Conditional Pass).
- `failed` — số phiếu KHÔNG ĐẠT (Failed).
- `pass_rate_pct` — tỉ lệ đạt `completed/total × 100` (round 1).
- `overdue_assets` — số THIẾT BỊ (distinct) quá hạn hiệu chuẩn (toàn-hệ, SoT schedule).
- `due_soon_assets` — số THIẾT BỊ (distinct) sắp đến hạn (cửa-sổ 30 ngày).

Endpoint `get_calibration_kpis` **ĐÃ LIVE** @web-BE (KHÔNG build `.py` mới) ⇒ round này **CONTRACT-ONLY**: curate 1 path + 3 schema vào mirror, **0** `.py`/reload/migrate. Đây là endpoint Dashboard-KPI **THỨ HAI** (SIBLING của `getPmDashboardStats`/ADR-056, endpoint ĐẦU); `getRepairKpis` (IMM-09) = **forward-reserve** vòng kế. Mỗi KPI-endpoint đơn-module theo module-tag riêng (`pm`/`calibration`/`work-order`) — "màn Bảng chỉ số" là **FE-composition** (FE gom nhiều call module-tag thành 1 màn), KHÔNG API-tag (đối-xứng ADR-056 §2(b)).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler @`api/imm11.py:146-153` = bare `@frappe.whitelist()` (GET, KHÔNG `allow_guest`, KHÔNG `rbac.require`):
  ```python
  @frappe.whitelist()
  def get_calibration_kpis(year: int = None, month: int = None) -> dict:
      now = datetime.date.today()
      return handle(
          svc.get_kpis,
          int(year) if year else now.year,
          int(month) if month else now.month,
      )
  ```
- Service `get_kpis(year, month)` @`services/imm11.py:1171-1201` return-dict VERBATIM @`:1192-1201`:
  ```python
  total     = CalibrationRepo.count({"scheduled_date": between})                     # :1177 → int
  completed = CalibrationRepo.count({..., "status": ("in",[PASSED, COND_PASSED])})   # :1178 → int
  failed    = CalibrationRepo.count({..., "status": FAILED})                         # :1182 → int
  overdue_assets = len(_overdue_asset_ids())                                         # :1188 → int
  due_soon       = len(_due_soon_asset_ids())                                        # :1189 → int
  pass_rate = round((completed / total * 100), 1) if total else 0.0                  # :1190 → number, else=0.0
  return {
      "kpis": {
          "total_this_month": total,        # :1194 int
          "completed":        completed,    # :1195 int
          "failed":           failed,       # :1196 int
          "pass_rate_pct":    pass_rate,    # :1197 number NON-nullable (else=0.0)
          "overdue_assets":   overdue_assets,# :1198 int (COUNT distinct-asset — KHÔNG list)
          "due_soon_assets":  due_soon,     # :1199 int (COUNT distinct-asset — KHÔNG list)
      }
  }                                          # :1192-1201 — SINGLE khối `kpis`, KHÔNG `trend_6months`, KHÔNG `period`
  ```
- `handle(...)` @`utils/api_handler.py:33` → `_ok(dict)`/`_err(...)` — envelope hợp-đồng chuẩn (Decision-B: lỗi nghiệp-vụ TRÊN HTTP-200 body `Error`).
- Domain-SoT: IMM-11 `05_API_Specification.md` §6.1 (canonical-value rule) đã chốt `overdue_assets`/`due_soon_assets` = **COUNT distinct-asset** (`len(_overdue_asset_ids())`/`len(_due_soon_asset_ids())`) khớp drill `?overdue=1`/`?due_soon=1` (BR-11-08/09). ⚠️ **§12 example cũ STALE** (7-key compliance-report + `period` + `overdue_assets[]` LIST) — Self-Correct đồng-bộ về 6-key LIVE (xem §5).

---

## 2. Quyết định

### (a) 200 = **inline `oneOf [CalibrationKpisEnvelope, Error]`** (Decision-B, 0 discriminator)

`data` = **`CalibrationKpisData` OBJECT PHẲNG** `{kpis}` — KHÔNG pagination, KHÔNG list-envelope. Route 2 nhánh MÁY-ĐỌC bằng CLOSED-SCHEMA + disjoint required-set (Env `req[success,data]` vs Error `req[success,error,code,http_status]`), theo `body.success` — mirror `getPmDashboardStats`/`getAssetKpi` (flat-object read). Vào **`_MVP_READ_ENVELOPE`** (inline oneOf, KHÔNG response-component); **KHÔNG** `_MVP_LIST_ENVELOPE` (dashboard read ≠ list ⇒ GIỮ NGUYÊN 13). **Invariant `count==rows` KHÔNG áp** (0 list, 0 pagination — `overdue_assets`/`due_soon_assets` là COUNT scalar, drill-parity chốt ở domain §6.1 KHÔNG ở contract này).

### (b) **SINGLE khối `kpis` — KHÔNG `trend_6months`** (điểm KHÁC CỐT-LÕI vs `PmDashboardStats`/ADR-056)

`CalibrationKpisData` = `{kpis: $ref CalibrationKpis}`, `required:[kpis]` — **CHỈ 1 key**. `get_kpis` @`:1192-1201` trả **DUY NHẤT** `{"kpis": {...}}` (KHÔNG `trend_6months`, KHÔNG `period`) ⇒ contract VERBATIM. Đây là **anti-drift** so với `PmDashboardStats` `{kpis, trend_6months}` (ADR-056) — copy-paste PM-shape mà thêm `trend_6months` = **bịa field service KHÔNG trả** ⇒ codegen sinh property luôn `null`/absent, deser drift. Tách schema wrapper RIÊNG `CalibrationKpisData` (KHÔNG inline `kpis` thẳng vào Envelope) để: (1) đối-xứng cấu-trúc 3-tầng Envelope→Data→Kpis của `getPmDashboardStats` (Envelope→Stats→Kpis) ⇒ guard-family nhất quán; (2) đặt tên `Data` (KHÔNG `Stats`) làm rõ **payload chỉ có `kpis`, KHÔNG có block xu-hướng** — naming phản-ánh sự-khác-biệt.

### (c) operationId `getCalibrationKpis` (DOMAIN), **tag `calibration`** — KHÔNG `dashboard`

tag **`calibration`** = REUSE tag mọi read-endpoint IMM-11 (`getCalibration`/`listCalibrations`/`getDueCalibrations`/`sendToLab` — yaml:11539/14204/14426/12615). **Loại tag `dashboard` MỚI**: (1) 100% precedent mirror dùng **module-domain tag** — 0 tag theo-màn-hình; (2) `getPmDashboardStats`→`pm`, `getCalibrationKpis`→`calibration`, forward-reserve `getRepairKpis`→`work-order` là **đơn-module** ⇒ mỗi cái module-tag; "màn Bảng chỉ số" = **FE-composition**; (3) đồng-nhất quyết định ADR-056 §2(b). naming-guard: schema `CalibrationKpis*` ∩ (`Calibration*` ∪ `CalibrationDetail*` ∪ `DueCalibration*` ∪ `SubmitCalibration*` ∪ `CreateCalibration*` ∪ `CancelCalibration*` ∪ `SendToLab*` ∪ `ReceiveCertificate*` ∪ `AddMeasurement*`) == ∅ (grep-verify prefix `CalibrationKpis` = 0 collision @yaml — chỉ xuất-hiện trong comment "forward-reserve"; **`CalibrationKpis` ≠ `CalibrationDetail`@8932** — namespace + domain khác).

### (d) 3 schema CLOSED (`additionalProperties:false`) — VERBATIM return-dict, 0 invention, **6 key ĐỀU ∈ required**

- **`CalibrationKpis`** — EXACT **6 prop** VERBATIM `@services/imm11.py:1194-1199`, `required` = **CẢ 6** (mọi key always-emit vô-điều-kiện):
  - `total_this_month`, `completed`, `failed`, `overdue_assets`, `due_soon_assets` = `type:integer` (count/len LUÔN trả int; `overdue_assets`/`due_soon_assets` = **COUNT scalar** `len(...)` @`:1188-1189` — KHÔNG array).
  - `pass_rate_pct` = `type:number` **NON-nullable** ∧ **∈ `required`** — `round((completed/total*100),1) if total else 0.0` @`:1190` ⇒ nhánh `else` = `0.0` (LUÔN number, KHÔNG `None`). **ĐIỂM KHÁC CỐT-LÕI vs `PmDashboardKpis.compliance_rate_pct`** (nullable ∉ required — PM return `None` khi mẫu 0). Ở đây `else 0.0` ⇒ **KHÔNG `nullable`, ∈ required**.
  - `required` = **6 key** `[total_this_month, completed, failed, pass_rate_pct, overdue_assets, due_soon_assets]` (KHÔNG key nào ngoài — 0 field nullable).
- **`CalibrationKpisData`** — `{kpis: $ref CalibrationKpis}`, `required:[kpis]`, **KHÔNG có key `trend_6months`** (§2(b)).
- **`CalibrationKpisEnvelope`** — `{success:{type:boolean, enum:[true]}, data:$ref CalibrationKpisData}`, `required:[success, data]`.

### (e) 2 typed query-param `year`+`month` (integer, `required:false`) — **KHÔNG khai `default:` trong YAML**

pattern CR-05 typed-query-param + precedent 1:1 `getPmDashboardStats`/ADR-056 §2(d) NHƯNG **KHÔNG** `default:` — backend default = **`datetime.date.today()` year/month động** (`now.year`/`now.month` @`api/imm11.py:148-152`), KHÔNG hằng-số. Signature `get_calibration_kpis(year=None, month=None)` @`:147` (cả 2 default `None`) ⇒ `required:false`. Khai `default: 2026` (static) → codegen ép client GỬI năm chốt-cứng → drift stale, override server-default động. `required:false` + no-default ⇒ client omit → server tự dùng tháng hiện-tại. `month` mô-tả range 1–12 ở `description` (KHÔNG hard `enum`/`min`/`max` — tránh over-constrain, mirror ADR-056).

### (f) 403 = SINGLE-SHAPE `Forbidden` **dispatcher-ONLY** (bare `@whitelist`, 0 cap-403)

Handler bare `@frappe.whitelist()` @`:146` KHÔNG `allow_guest`, KHÔNG `rbac.require` ⇒ guest/no-token trip **dispatcher-403** (`PermissionError`, HTTP-403 raw `FrappeRawError`) TRƯỚC `handle()`; bearer-expired → **401** (`AuthenticationError`). KHÔNG in-handler cap-403 reachable ⇒ 403-slot SINGLE `Forbidden` (mirror `getPmDashboardStats`/`getDueCalibrations`/`getAssetKpi`, KHÁC `sendToLab`/`cancelCalibration` cap-REACHABLE). **ĐỐI XỨNG A16**: path vào `_MVP_BUSINESS_PATHS` ⇒ `_PATHS_REQUIRE_401` ∧ `_PATHS_REQUIRE_403` tự +1 (đếm 401==403 GIỮ NGUYÊN). status-set `[200, 401, 403]`.

### (g) CONTRACT-ONLY — 0 `.py`/reload/migrate

`get_calibration_kpis` + `get_kpis` **ĐÃ LIVE** @source ⇒ `git diff` round này = CHỈ `docs/mobile/*` (yaml + ADR + README + 04-api-contract) + `docs/imm-11/*` (Core Doc binding + Self-Correct §12) + `assetcore/tests/guards/test_mobile_oas.py` + `assetcore/tests/guards/test_mobile_docset.py` (guard). **0** file `.py` runtime, **0** gunicorn reload (KHÔNG HARD-STOP USER — `[AUTO]`), **0** `bench migrate`.

---

## 3. Path + schema (copy-ready cho BE Bước-4)

Đặt block path **liền sau** cụm IMM-11 read (`getDueCalibrations`) hoặc cụm Dashboard-KPI (`getPmDashboardStats`) trong `paths:`; 3 schema đặt **liền sau** `CalibrationDetail*` (hoặc cụm `PmDashboard*`) trong `components.schemas:`.

```yaml
# paths:
/api/method/assetcore.api.imm11.get_calibration_kpis:
  get:
    tags: [calibration]
    operationId: getCalibrationKpis
    summary: '[Bảng chỉ số hiệu chuẩn] Bộ chỉ số hiệu chuẩn theo tháng — dashboard-read'
    description: >
      imm11.get_calibration_kpis(year=None, month=None) — 2 typed query-param (KHÔNG default
      YAML; backend default datetime.date.today() year/month @api/imm11.py:148). 200 =
      CalibrationKpisData {kpis (6-key theo tháng)} — SINGLE khối kpis, KHÔNG trend_6months
      (KHÁC getPmDashboardStats). pass_rate_pct = number NON-nullable (else=0.0 @services/imm11.py:1190).
      overdue_assets/due_soon_assets = COUNT distinct-asset (len(_overdue/_due_soon_asset_ids)), KHÔNG list;
      drill-parity KPI==rows chốt domain §6.1 BR-11-08/09. Bare @whitelist → GET, KHÔNG cap-gate
      (guest dispatcher-403 / bearer-expired 401).
    parameters:
      - name: year
        in: query
        required: false
        schema: { type: integer }
        description: >
          Năm (YYYY) của khối tháng. Bỏ trống ⇒ backend dùng năm hiện tại (datetime.date.today().year
          @api/imm11.py:148) — KHÔNG khai default YAML (default động, không hằng).
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
          200 bộ chỉ số hiệu chuẩn. oneOf 2 nhánh CLOSED-SCHEMA disjoint required-set (KHÔNG discriminator —
          read-path): (a) CalibrationKpisEnvelope {success:true, data:CalibrationKpisData}; (b) Error
          {success:false, code, http_status} — lỗi nghiệp-vụ / 401 guest arrive HTTP-200. Route theo body.success.
        content:
          application/json:
            schema:
              oneOf:
                - $ref: '#/components/schemas/CalibrationKpisEnvelope'
                - $ref: '#/components/schemas/Error'
      '401': { $ref: '#/components/responses/Unauthorized401' }
      '403': { $ref: '#/components/responses/Forbidden' }

# components.schemas:
CalibrationKpisEnvelope:
  type: object
  additionalProperties: false
  description: '200 success envelope getCalibrationKpis — _ok(CalibrationKpisData). imm11.py:1192.'
  properties:
    success: { type: boolean, enum: [true] }
    data: { $ref: '#/components/schemas/CalibrationKpisData' }
  required: [success, data]

CalibrationKpisData:
  type: object
  additionalProperties: false
  description: >
    Payload bộ chỉ số hiệu chuẩn (màn "Bảng chỉ số hiệu chuẩn") — services/imm11.py:1192-1201.
    SINGLE khối kpis LUÔN emit ⇒ required. KHÔNG có trend_6months (KHÁC PmDashboardStats — service
    trả duy nhất {"kpis": {...}}).
  properties:
    kpis: { $ref: '#/components/schemas/CalibrationKpis' }
  required: [kpis]

CalibrationKpis:
  type: object
  additionalProperties: false
  description: >
    6 chỉ số hiệu chuẩn phạm-vi THÁNG — services/imm11.py:1194-1199. CẢ 6 always-emit ∈ required
    (0 field nullable). pass_rate_pct NON-nullable (else=0.0, KHÁC PmDashboardKpis.compliance_rate_pct
    nullable). overdue_assets/due_soon_assets = COUNT distinct-asset (KHÔNG list).
  properties:
    total_this_month:
      type: integer
      description: 'Tổng phiếu hiệu chuẩn scheduled_date trong tháng (CalibrationRepo.count). imm11.py:1177/1194.'
    completed:
      type: integer
      description: 'Số phiếu ĐẠT (status ∈ [Passed, Conditional Pass]) trong tháng. imm11.py:1178/1195.'
    failed:
      type: integer
      description: 'Số phiếu KHÔNG ĐẠT (status == Failed) trong tháng. imm11.py:1182/1196.'
    pass_rate_pct:
      type: number
      description: >
        Tỉ lệ đạt = completed / total_this_month × 100 (round 1). 0.0 khi total_this_month==0
        (else=0.0 @imm11.py:1190 — NON-nullable, KHÁC PmDashboardKpis.compliance_rate_pct=null).
    overdue_assets:
      type: integer
      description: >
        COUNT distinct THIẾT BỊ quá hạn hiệu chuẩn toàn-hệ = len(_overdue_asset_ids()) @imm11.py:1188.
        Khớp drill /calibration/schedules?overdue=1 (KPI==#asset, §6.1 BR-11-08). SCALAR — KHÔNG array.
    due_soon_assets:
      type: integer
      description: >
        COUNT distinct THIẾT BỊ sắp đến hạn (cửa-sổ 30 ngày) = len(_due_soon_asset_ids()) @imm11.py:1189.
        Khớp drill /calibration/schedules?due_soon=1 (KPI==#asset, §6.1 BR-11-09). SCALAR — KHÔNG array.
  required:
    - total_this_month
    - completed
    - failed
    - pass_rate_pct
    - overdue_assets
    - due_soon_assets
```

---

## 4. Guard test (`test_mobile_oas.py` — class RIÊNG `TestMobileGetCalibrationKpisContract`, 9 TC a..i)

ĐỐI XỨNG `TestMobileGetPmDashboardStatsContract`:

- **a** — path tồn tại + CHỈ GET + opId `getCalibrationKpis` + tag `[calibration]`; ∈ `_MVP_BUSINESS_PATHS` + `_MVP_READ_ENVELOPE`; ∉ `_MVP_LIST_ENVELOPE`.
- **b** — ĐÚNG 2 typed query-param `year`/`month` (`type:integer`, `required:false`, **KHÔNG `default` key trong schema** — anti static-default drift); KHÔNG requestBody; 0 param khác (`page`/`filters`/`days`/`mine`).
- **c** — `CalibrationKpis` CLOSED, EXACT **6 prop** {total_this_month,completed,failed,pass_rate_pct,overdue_assets,due_soon_assets} — 0 thừa/thiếu; `required` == **cả 6** (0 field ngoài required); 5 field `integer` + `pass_rate_pct` `number`.
- **d** — `pass_rate_pct` **NON-nullable** ∧ ∈ `required` (anti false-null — nhánh else=0.0; ĐỐI-NGHỊCH `PmDashboardKpis.compliance_rate_pct` nullable ∉ required); 0 field `nullable:true`; 0 field Check integer-enum/boolean; `overdue_assets`/`due_soon_assets` = `integer` (COUNT scalar, KHÔNG `type:array`).
- **e** — `CalibrationKpisData` CLOSED, `required:[kpis]` (CHỈ 1 key); `kpis.$ref`==CalibrationKpis; **KHÔNG có property `trend_6months`** (anti-drift vs PmDashboardStats — assert `'trend_6months' not in properties`).
- **f** — `CalibrationKpisEnvelope` CLOSED, `required:[success,data]`, `success.enum==[true]`, `data.$ref`==CalibrationKpisData.
- **g** — 200 inline oneOf ĐÚNG 2 `[CalibrationKpisEnvelope, Error]` 0-discriminator; slot `{200,401,403}` (401 `Unauthorized401` + 403 `Forbidden` SINGLE-shape).
- **h** — 3 schema mới KHÔNG orphan (Envelope←response, Data←Envelope, Kpis←Data) + 0 dangling; membership reconcile (path/opId +1; `c5`/`_PARITY_BUSINESS_PATHS` +1; `_MVP_READ_ENVELOPE` +1; `_MVP_LIST_ENVELOPE` GIỮ NGUYÊN).
- **i** — naming-guard `CalibrationKpis*` ∩ (`CalibrationDetail*`∪`DueCalibration*`∪`SubmitCalibration*`∪`CreateCalibration*`∪`CancelCalibration*`∪`SendToLab*`∪`ReceiveCertificate*`∪`AddMeasurement*`) == ∅ + **live-signature parity** `inspect.signature(imm11.get_calibration_kpis).parameters == {year, month}`.

**TC hiện có tự phủ (0 TC mới):** `TC-MOB-OAS-09` (0 dangling — 3 schema đều $ref'd) · `TC-MOB-OAS-10` (0 orphan mới) · `TC-MOB-OAS-11` (401 coverage — auto qua `_MVP_BUSINESS_PATHS`) · `TC-MOB-OAS-12` (getCalibrationKpis declare CẢ 401+403 — auto qua `_PATHS_REQUIRE_401`==`_PATHS_REQUIRE_403`).

### Bulk-bump bookkeeping (reconcile — ⚠️ grep-verify @source TRƯỚC bump)

- `_EXPECTED_TEST_COUNT` 792 → **801** (+9); `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 792 → **801**.
- cross-file `test_mobile_docset.py`: `_GUARD_SUITE_SUM` 935 → **944**; `_MOBILE_OAS_TOTAL` 961 → **970**.
- path/opId 87 → **88**; `c5` / `_PARITY_BUSINESS_PATHS` 76 → **77**; `_MVP_READ_ENVELOPE` +1 (ĐỊNH NGHĨA `_CALIBRATION_KPIS_PATH` const + entry `→ #/components/schemas/CalibrationKpisEnvelope`); `_MVP_LIST_ENVELOPE` **GIỮ NGUYÊN 13** (dashboard read ≠ list); membership `_MVP_BUSINESS_PATHS` (401/403 symmetry) tự +1 (thêm tuple `("get","getCalibrationKpis")`).
- ⚠️ **Baseline 87/792/76/13/935/961 grounded @source 2026-07-15 (sau CR-31a/ADR-056)** — đa-phiên race (memory `multi_session_concurrency`): BE **grep-verify @source ngay trước bump**, đừng tin số học. Verify next-free ADR số (kỳ vọng 057 — nếu bị chiếm, dời + reconcile README).

---

## 5. Hệ quả

- **+**: màn "Bảng chỉ số hiệu chuẩn" codegen-ready (typed model `CalibrationKpisData`/`CalibrationKpis`); FE mobile bind 6-tile theo server-flag (`pass_rate_pct` LUÔN number; `overdue_assets`/`due_soon_assets` COUNT khớp drill §6.1 — KHÔNG re-derive client-clock, memory `overdue_server_flag_ssot`).
- **+**: HOÀN THIỆN thêm 1 endpoint surface **Dashboard-KPI** (Trục B) sau `getPmDashboardStats` — CÙNG khuôn (inline oneOf read, module-tag riêng, closed-schema VERBATIM); `getRepairKpis` forward-reserve.
- **+**: false-green chặn bằng live-signature parity + no-orphan + 6-key VERBATIM + `trend_6months`-absent guard (TC-e) + `pass_rate_pct` NON-null guard (TC-d, đối-nghịch PM).
- **+ Self-Correction domain**: §12 `05_API_Specification.md` example cập-nhật từ 7-key STALE (`compliance_rate_pct`/`total_scheduled`/`out_of_tolerance_rate_pct`/`capa_*`/`avg_days_sent_to_cert` + `period` + `overdue_assets[]` LIST) → **6-key LIVE** khớp `get_kpis` @source (đồng-bộ với §6.1 vốn đã đúng). Contract mirror KHÔNG cross-ref shape sai.
- **−/đánh đổi**: tag `calibration` (KHÔNG `dashboard`) ⇒ 3 KPI-endpoint ở 3 tag module — màn dashboard là FE-composition (chấp-nhận, đúng precedent ADR-056/device-profile). Đổi sau = 1 ADR mới Supersede (KHÔNG xoá 057). Wrapper `CalibrationKpisData` (naming lệch `PmDashboardStats`) = có-chủ-đích (payload chỉ `kpis`, làm rõ 0 trend).
- **KHÔNG** đổi workflow / DocType / migrate / reload (CONTRACT-ONLY, backend LIVE). Working-tree để USER review — KHÔNG git commit/push.

### Alternatives loại

| Phương án | Lý do loại |
|---|---|
| thêm `trend_6months` cho parity `PmDashboardStats` | `get_kpis` @`:1192-1201` trả DUY NHẤT `{"kpis":{...}}` — bịa field service KHÔNG trả; codegen sinh property luôn absent/null → drift. |
| `pass_rate_pct` `nullable:true` ∉ required (copy `compliance_rate_pct` PM) | Nhánh else = `0.0` (LUÔN number) @`:1190` — nullable = SAI-nguồn; ∈ required. ĐỐI-NGHỊCH CHỦ-ĐÍCH với PM (`None` khi mẫu 0). |
| `overdue_assets`/`due_soon_assets` = `type:array` (list asset, như §12 STALE) | LIVE = `len(...)` COUNT scalar @`:1188-1189` — array = shape cũ đã bỏ; drill-parity chốt §6.1 (KPI==#asset), KHÔNG nhồi list vào KPI card. |
| tag `dashboard` (MỚI) | Fork module-domain taxonomy (100% precedent module-tag); siblings đơn-module ⇒ mỗi cái module-tag; "màn dashboard" = FE-composition. ADR-056 §2(c) chốt. |
| inline `kpis` thẳng vào Envelope (bỏ `CalibrationKpisData`) | Phá đối-xứng 3-tầng Envelope→Data→Kpis của `getPmDashboardStats`; acceptance chốt schema `CalibrationKpisData` RIÊNG. |
| khai `default: <year/month>` trong YAML | Default backend = `datetime.date.today()` ĐỘNG @`:148`, KHÔNG hằng; static default → client gửi năm chốt-cứng drift stale, override server. |
| response-component (như `DueCalibrationList`) | read flat-object dùng **inline** oneOf (mirror `getPmDashboardStats`/`getAssetKpi`); ∈ `_MVP_READ_ENVELOPE` KHÔNG list-envelope. |
| ∈ `_MVP_LIST_ENVELOPE` | dashboard KPI ≠ list (0 rows/pagination) — GIỮ 13. |
| status-line 404/4xx | Decision-B — lỗi TRÊN HTTP-200 body Error. |
| 403 dual-shape (như `sendToLab`/`cancelCalibration`) | 0 `rbac.require` in-handler ⇒ chỉ dispatcher-403 SINGLE `Forbidden`. |
| bịa/thêm/bớt field vs return-dict | VERBATIM 6-key @source; 0 invention. |

**Accepted.**
