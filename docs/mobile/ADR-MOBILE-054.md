# ADR-MOBILE-054 — `getDuePmSchedules` (`imm08.get_due_pm_schedules`) build + curate vào OAS mirror (**CR-28b · MỞ NHÁNH F8 "Nhắc việc" nửa-PM** — bồi ĐÚNG 1 GET-list-read path trả LỊCH PM (PM Schedule) sắp/quá hạn ≤ N ngày, ĐÓNG nửa PM còn CHẾT của màn "Nhắc việc" (nửa Hiệu chuẩn `getDueCalibrations`/ADR-MOBILE-049 đã LIVE); nguồn `PM Schedule.next_due_date` (**KHÁC** calib dùng `AC Asset.next_calibration_date`); `days_left` server-derived signed; KHÔNG pagination `{items, threshold_days}`; ⚠️ endpoint MỚI — có `.py` runtime, **KHÁC** ADR-MOBILE-049 CONTRACT-ONLY)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-054 |
| Phase | C — API contract (codegen-ready) + BE build (service + handler mới) |
| Ngày | 2026-07-15 |
| Tác giả | BA (spec) → BE (Bước-4 build + curate) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; oneOf KHÔNG discriminator) · **SIBLING trực-tiếp**: **ADR-MOBILE-049** (`getDueCalibrations` — nửa Hiệu-chuẩn CÙNG màn "Nhắc việc" F8, CÙNG shape KHÔNG-pagination `{items, threshold_days}`, `days_left` signed) · **precedent bare-@whitelist read dispatcher-only 403**: ADR-043 family (`listTransfers`/`listDepartments`/`listLocations`) · Core Doc IMM-08 [`docs/imm-08/05_API_Specification.md`](../imm-08/05_API_Specification.md) §0.1.5 + `ADR-IMM08-DUEPM` |

---

## 1. Bối cảnh

Màn **F8 "Nhắc việc"** trên mobile gom 2 danh sách để KTV ưu tiên đi làm:

- **Nửa Hiệu chuẩn** — `getDueCalibrations` (ADR-MOBILE-049) — ✅ LIVE.
- **Nửa PM** — **CHẾT** cho tới round này. Cần 1 list LỊCH PM (PM Schedule) **sắp/quá hạn** ≤ N ngày.

Khác `getDueCalibrations` (endpoint đã LIVE @web-BE → curate CONTRACT-ONLY), **`get_due_pm_schedules` CHƯA tồn tại** ⇒ Bước-4 BE **build service + handler MỚI** rồi mới curate OAS. NEW `.py` ⇒ worker reload = **HARD-STOP USER** (test qua `bench run-tests` fresh-load nên vẫn xanh; **0** `bench migrate`).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Pattern mirror = `get_due_calibrations` @`services/imm11.py:1393-1421`:
  ```python
  today = nowdate(); threshold = add_days(today, int(days))
  rows, _ = AssetRepo.list(
      filters=[["lifecycle_status","not in",[DECOMMISSIONED]],
               ["next_calibration_date","is","set"],
               ["next_calibration_date","<=",threshold]],
      fields=[...6...], order_by=_ORDER_NEXT_CAL_ASC, page_size=int(limit))
  for r in rows: r["days_left"] = date_diff(nd, today_d) if nd else None
  return {"items": rows, "threshold_days": int(days)}
  ```
  Handler @`api/imm11.py:202-203` = bare `@frappe.whitelist()` → `return handle(svc.get_due_calibrations, int(days), int(limit))`.
- Nguồn PM (KHÁC calib): `PM Schedule.next_due_date` (SoT lịch PM, BR-08-03). DocType `pm_schedule.json` fields: `asset_ref` (Link AC Asset) · `pm_type` (Select 4) · `status` (Select `Active/Paused/Suspended`) · `next_due_date` (Date) · `last_pm_date` (Date, CÓ THỂ NULL) · `responsible_technician` (Link User, optional).
- `PMScheduleStatus.ACTIVE` @`services/imm08.py:228`; enrich `asset_name` pattern = `list_schedules` @`services/imm08.py:1326-1327` (`AssetRepo.get_value(asset_ref, "asset_name") or ""`); `add_days`/`date_diff`/`getdate`/`nowdate` đã import @`services/imm08.py:9`; `PMScheduleRepo`/`AssetRepo` đã import.

---

## 2. Quyết định

### (a) 200 = **oneOf `[DuePmScheduleListEnvelope, Error]`** (Decision-B, 0 discriminator) — KHÔNG pagination

`data` = **`{items[], threshold_days}` CHÍNH XÁC 2 key** (return-shape mirror `getDueCalibrations`). `DuePmScheduleListPage` **KHÔNG có `pagination` `$ref`** — điểm PHÂN BIỆT vs `PmScheduleListEnvelope` (§catalog #11 `{data[], pagination}`). Vẫn vào `_MVP_LIST_ENVELOPE` (200 = oneOf [Env, Error] `handle()`-contract), KHÔNG `_MVP_SINGLE_LIST_ENVELOPE`. **Invariant `count==rows` KHÔNG áp** (handler KHÔNG surface count/pagination; rows = trang-đầu `limit` sort `next_due_date asc`).

### (b) operationId `getDuePmSchedules` (DOMAIN), tag `pm`

opId camelCase theo domain (mirror `getDueCalibrations`). tag **`pm`** = REUSE tag của `getPmWorkOrder` @YAML (read-endpoint IMM-08) — **KHÔNG** `work-order` (đó là tag các write-action `assignPmTechnician`/`reschedulePm`). naming-guard `DuePmSchedule*` ∩ (`PmSchedule*` ∪ `PmWorkOrder*`) == ∅.

### (c) `DuePmScheduleListItem` = **CLOSED (`additionalProperties:false`) EXACT 9 prop** — 7 Repo-field ∪ `asset_name` enrich ∪ `days_left` derive

`{name, asset_ref, asset_name, pm_type, status, next_due_date, last_pm_date, responsible_technician, days_left}`. `required:[name]`, 8 field khác optional. **Nullable KHÁC nhau — grounding từng field, KHÔNG copy đồng loạt:**

- `days_left` = `type:integer` signed **NON-nullable** (âm = quá hạn) — filter `["next_due_date","is","set"]` loại NULL ⇒ nhánh `else None` DEAD ⇒ dùng trực-tiếp (server SSoT overdue, KHÔNG client-clock).
- `next_due_date` = `format:date` **NON-nullable** — filter is-set đảm bảo.
- `last_pm_date` = `format:date` **`nullable:true`** — lịch mới tạo từ commissioning chưa từng chạy PM ⇒ NULL hợp-lệ. Khai NON-nullable = strict codegen reject-valid row → CRASH.
- `responsible_technician` = **`nullable:true`** — Link User optional.
- **0 field Check ⇒ 0 `integer enum[0,1]`/`boolean`** ⇒ MIỄN CR-01 int-vs-bool coercion (mirror `DueCalibrationListItem`).
- Chỉ `DuePmScheduleListEnvelope` = CLOSED `{success:[true], data:$ref DuePmScheduleListPage}` (route-by-VALUE `body.success` an-toàn).

### (d) Filter 3-clause — `status=='Active'` + `next_due_date is set` (NULL-coerce guard) + `<= threshold`

- `status=='Active'` LOẠI Paused/Suspended (positive-form rõ hơn `not in` — PMScheduleStatus 3-state).
- **`["next_due_date","is","set"]` BẮT BUỘC** — Frappe query-builder render `<= threshold` thành `ifnull(next_due_date, '0001-01-01') <= threshold` ⇒ nếu KHÔNG loại NULL, lịch chưa-set-ngày coerce `'0001-01-01'` LỌT filter, sort ASC lên đầu, lấp kín `limit`, đẩy lịch overdue thật khỏi list (SAI KPI — mirror bẫy `get_due_calibrations`). Lịch chưa-có-ngày KHÔNG phải "đến hạn".
- `order_by next_due_date asc`, `page_size=int(limit)`.

### (e) 403 = SINGLE-SHAPE `Forbidden` **dispatcher-ONLY** (bare `@whitelist`, 0 cap-403)

Handler bare `@frappe.whitelist()` KHÔNG `allow_guest`, KHÔNG `rbac.require` ⇒ guest/no-token trip dispatcher-403 TRƯỚC `handle()`; KHÔNG có in-handler cap-403 reachable. Mirror `getDueCalibrations`/`listTransfers` (ADR-043 family). status-set `[200, 401, 403]`.

### (f) ⚠️ CÓ `.py` runtime change (KHÁC ADR-MOBILE-049 CONTRACT-ONLY)

Đây là điểm KHÁC CỐT-LÕI vs ADR-MOBILE-049: `getDueCalibrations` curate pure-yaml (endpoint LIVE). `getDuePmSchedules` **build MỚI** service + handler ⇒ `git diff` gồm `api/imm08.py` + `services/imm08.py` + YAML + 2 test file. NEW `.py` ⇒ **worker reload = HARD-STOP USER** (KHÔNG tự reload, KHÔNG curl-verify LIVE — LL-DEPLOY-07); `bench run-tests` fresh-load nên guard vẫn xanh; **0** `bench migrate` (0 DocType change).

---

## 3. Path + param

```
/api/method/assetcore.api.imm08.get_due_pm_schedules  (GET, opId getDuePmSchedules, tag [pm])
  param days:  in:query, required:false, schema.type:integer, default 30
  param limit: in:query, required:false, schema.type:integer, default 50
  200: response oneOf [DuePmScheduleListEnvelope, Error]
  401: $ref Unauthorized401   403: $ref Forbidden (SINGLE-SHAPE dispatcher-only)
```

- Đặt block path **liền sau** `getDueCalibrations` (hoặc cụm IMM-08) trong `paths:`; 3 schema đặt **liền sau** `DueCalibration*` trong `components.schemas:` — giữ cụm "Nhắc việc" F8 liền mạch.

---

## 4. Guard test (`test_mobile_oas.py` — class RIÊNG `TestMobileDuePmSchedulesContract`, 7 TC a..g)

ĐỐI XỨNG `TestMobileDueCalibrationsContract`:

- **a** — path tồn tại + CHỈ GET + opId `getDuePmSchedules` + tag `[pm]`; ∈ `_MVP_BUSINESS_PATHS` + `_MVP_LIST_ENVELOPE`; ∉ `_MVP_SINGLE_LIST_ENVELOPE`.
- **b** — ĐÚNG 2 typed query-param `days`/`limit` (integer, default 30/50, `required:false`); KHÔNG requestBody; 0 param `filters`/`mine`/`page`.
- **c** — `DuePmScheduleListItem` CLOSED, `required:[name]`, EXACT 9 prop {name,asset_ref,asset_name,pm_type,status,next_due_date,last_pm_date,responsible_technician,days_left} — 0 field thừa/thiếu.
- **d** — `days_left` `integer` NON-nullable ∧ `next_due_date` NON-nullable (anti dead-branch) ∧ `last_pm_date` nullable ∧ `responsible_technician` nullable (anti false-non-null); 0 Check integer-enum.
- **e** — `DuePmScheduleListPage` CLOSED, `required:[items,threshold_days]` **CHÍNH XÁC 2-key KHÔNG `pagination`** (điểm KHÁC `PmScheduleListEnvelope`).
- **f** — 200 oneOf ĐÚNG 2 `[DuePmScheduleListEnvelope, Error]` 0-discriminator + `DuePmScheduleListEnvelope` CLOSED `{success:enum[true], data:$ref}`; slot `{200,401,403}`.
- **g** — naming-guard `DuePmSchedule*` ∩ (`PmSchedule*`∪`PmWorkOrder*`) == ∅ + **live-signature parity** `inspect.signature(imm08.get_due_pm_schedules).parameters == {days, limit}`.

### Bulk-bump bookkeeping (reconcile — grep-verify @source TRƯỚC bump)

- `_EXPECTED_TEST_COUNT` 767 → **774** (+7).
- path/opId 84 → **85**; `c5` / `_PARITY_BUSINESS_PATHS` 73 → **74**; `_MVP_LIST_ENVELOPE` 12 → **13** (thêm entry `_DUE_PM_SCHEDULES_PATH → DuePmScheduleListEnvelope` + ĐỊNH NGHĨA path-const mới); membership `_MVP_BUSINESS_PATHS` (401/403 symmetry) tự +1.
- cross-file `test_mobile_docset.py`: `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 767 → **774**; `_GUARD_SUITE_SUM` 910 → **917**; `_MOBILE_OAS_TOTAL` 936 → **943**.
- ⚠️ Baseline **84/767/73/12/910/936 grounded @source 2026-07-15** — đa-phiên race (multi_session_concurrency): BE **grep-verify @source** ngay trước bump, đừng tin số học.

### BE-unit (`test_imm08.py` — TDD, RED-trước do handler∄)

- happy-path: 200 `{items, threshold_days}`, mỗi item 9-field, `threshold_days` echo `days`.
- NULL-coerce guard: lịch `next_due_date=NULL` KHÔNG lọt (mirror bẫy calib).
- status-filter: lịch Paused/Suspended KHÔNG lọt (chỉ Active).
- `days_left` signed: lịch overdue (`next_due_date < today`) → `days_left` âm.
- empty-window: `days=0` → chỉ trả lịch `next_due_date <= today`.

---

## 5. Hệ quả

- **+**: nửa PM màn "Nhắc việc" codegen-ready; FE mobile bind list PM due + `days_left` badge (server SSoT) + lọc client-side "PM của tôi" theo `responsible_technician`. ĐỐI XỨNG hoàn-chỉnh nửa-Calib ⇒ màn "Nhắc việc" đủ 2 nửa.
- **+**: false-green chặn bằng live-signature parity + no-orphan + 9-field-VERBATIM + nullable-per-field guard.
- **−/đánh đổi**: có `.py` MỚI (KHÁC ADR-MOBILE-049 pure-yaml) ⇒ **worker reload = HARD-STOP USER** trước khi LIVE. `bench run-tests` fresh-load vẫn xanh nên guard/CI KHÔNG chặn; chỉ HTTP-live cần reload.
- **KHÔNG** đổi workflow / DocType / migrate. Working-tree để USER review — KHÔNG git commit/push.
