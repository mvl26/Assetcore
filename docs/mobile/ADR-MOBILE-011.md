# ADR-MOBILE-011 — Calibration measurement-entry contract (`addMeasurement` POST, mắt-xích-GIỮA chuỗi calibration-detail) — `AddMeasurementResponse` RIÊNG 2-key `{name, measurement_count}` (`measurement_count` = GENUINE integer count, KHÔNG enum[0,1]) + **VERB-FLIP-THIS-ROUND** (bare `@whitelist` → `methods=['POST']`, đóng verb-parity gap R33 BỎ SÓT — KHÁC `submitCalibration` §8.15 backlog)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-011 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-27 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | ADR-MOBILE-006 (POST-action route-by-VALUE + 403 SINGLE-SHAPE) · §8.15/ADR-IMM11-MOB-02 (`submitCalibration` C3-split Calibration RIÊNG) · ADR-MOBILE-010 §(4)/(2) (`updated` GENUINE integer count precedent; flip-vs-clean discipline) · Decision-B (closed-schema oneOf) · C6/C7 (200 oneOf [Env, Error]) · VERB-PARITY CLOSURE (R33 2026-06-27: 3 write-action flip `methods=['POST']`, `_PARITY_VERB_ALLOWLIST`→`set()`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm11.py`, `assetcore/services/imm11.py`, `assetcore/tests/test_mobile_oas.py`, `assetcore/tests/test_oas_d12_error_surface.py`, `assetcore/tests/test_oas_d17_action_enum.py`). Contract: [`04-api-contract.md §8.24`](./04-api-contract.md). Core Doc IMM-11: `docs/imm-11/05_API_Specification.md §0.1.4` + `docs/imm-11/04_Backend_Design.md §3.2 / §5 (ADR-IMM11-MOB-03)`.

---

## Context

Tab Calibration MVP-flow-5 mobile có chuỗi 3 mắt-xích: **`createCalibration`** (tạo phiếu — §8.6, ✅ wired) → **`addMeasurement`** (ghi N điểm-đo trước khi chốt — **CÒN THIẾU**) → **`submitCalibration`** (chốt `docstatus 0→1` → tính verdict Passed/Failed/Conditionally Passed — §8.15, ✅ wired). **Mắt-xích-GIỮA `addMeasurement` còn THIẾU** trên mobile-contract ⇒ KTV mở `getCalibration` detail (`Scheduled`/`In Progress`) **không có endpoint nhập điểm-đo** → buộc phải `submitCalibration` trên measurement-set **RỖNG** → `overall_result` tính sai (không có row để so `measured_value` với `nominal_value ± tolerance`). Vòng này bồi **1 path** (path/opId **42→43**), `info.version` GIỮ `0.1.0-skeleton`, 0 dangling `$ref`.

Service THẬT `add_measurement(name, *, parameter_name, unit, nominal_value, tolerance_positive, tolerance_negative, measured_value=None)` (`services/imm11.py:1107`): append 1 row vào child table `measurements` (`services/imm11.py:1115-1122`); guard 404 nếu phiếu∄ (`MSG.IMM11_CAL_NOT_FOUND` `services/imm11.py:1112`) + 409 nếu `docstatus==1` (`MSG.IMM11_ALREADY_SUBMITTED` `services/imm11.py:1114`); return **2-key** `{name, measurement_count}` (`measurement_count = len(doc.measurements)` `services/imm11.py:1124`).

`addMeasurement` khác `submitCalibration` (§8.15) ở **2 điểm hợp đồng** cần quyết định:

1. **VERB-FLIP-THIS-ROUND (KHÁC §8.15 backlog).** Handler `add_measurement` (`api/imm11.py:120`) hiện **bare `@frappe.whitelist()`** ⇒ runtime BE **nhận cả GET** — nhưng đây là write-action (append child-row, **KHÔNG idempotent**: N call = N row; KHÔNG hợp GET-semantics). Đây là **verb-parity gap R33 BỎ SÓT**: R33 (VERB-PARITY CLOSURE 2026-06-27) đã flip 3 write-action (`create_calibration` `api/imm11.py:89` · `submit_calibration` `api/imm11.py:114` · `submit_pm_result` `imm08.py:54`) sang `methods=['POST']` + làm rỗng `_PARITY_VERB_ALLOWLIST`→`set()` — **NHƯNG SÓT `add_measurement`** (cùng module IMM-11, cùng bare-`@whitelist` write-action). ⇒ Vòng này **flip ĐÚNG 1 dòng decorator** (`api/imm11.py:120`) **NGAY** (KHÔNG đẩy backlog như §8.15 từng làm) ⇒ contract POST khớp source POST-only ⇒ **KHÔNG verb-divergence** ⇒ **KHÔNG** vào `_PARITY_VERB_ALLOWLIST` (giữ `set()` rỗng).
2. **`AddMeasurementResponse` 2-key `{name, measurement_count}` — `measurement_count` = GENUINE integer count.** `measurement_count` là **số đếm thật** số row child-table sau append (`len(doc.measurements)` `services/imm11.py:1124`) — KHÔNG phải Check-flag, KHÔNG bounded `[0,1]`. ⇒ khai `type:integer` THUẦN (precedent `updated` của `requestSpareParts` ADR-MOBILE-010 §(2) — số row gắn được, GENUINE integer; KHÔNG enum[0,1] kiểu Check-field Open#1). Schema RIÊNG, KHÔNG reuse `Submit`/`Pm`/`Repair`/`IncidentActionResponse` (field-set `{name,measurement_count}` ≠ mọi action khác).

## Decision

**(1) `addMeasurement` — POST path mới, schema RIÊNG `AddMeasurementResponse` 2-key.** Thêm 1 path `POST /api/method/assetcore.api.imm11.add_measurement` opId `addMeasurement`, tag `calibration`. `AddMeasurementResponse` closed (`additionalProperties:false`) **EXACT 2 prop** `{name string, measurement_count integer}` `required[name, measurement_count]` (cả 2 luôn trả — `services/imm11.py:1124`). `AddMeasurementEnvelope` closed `required[success,data]`, `success enum[true]`, `data = $ref AddMeasurementResponse`. 200 = oneOf `[AddMeasurementEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 nhánh closed + `success` enum disjoint `[true]`/`[false]`. **KHÔNG reuse `SubmitCalibrationResponse`/`*ActionResponse`** (C3-split — field-set riêng).

**(2) `measurement_count` = GENUINE integer count, KHÔNG enum[0,1].** `type:integer` THUẦN (số row `measurements` sau append, `len(doc.measurements)` `services/imm11.py:1124`). **0 boolean/Check prop** trong response ⇒ 0 prop `integer enum[0,1]` (Open#1 int-vs-bool KHÔNG áp — `measurement_count` không phải Check-field, có thể >1). Client hiển thị "đã ghi N điểm-đo". Precedent: `updated`/`requestSpareParts` (ADR-MOBILE-010 §2).

**(3) `requestBody` — `oneOf[json, x-www-form]`, required EXACT 6 + optional `measured_value` nullable.** `AddMeasurementRequest` closed (`additionalProperties:false`) `required` EXACT = `[name, parameter_name, unit, nominal_value, tolerance_positive, tolerance_negative]` (6 tham số KHÔNG default @`api/imm11.py:121-122`) + optional `measured_value` (`type:number, nullable:true` — `measured_value: float = None` @`api/imm11.py:123`). `name`/`parameter_name`/`unit` = `type:string`; `nominal_value`/`tolerance_positive`/`tolerance_negative`/`measured_value` = `type:number`. content **oneOf** `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict` §9 — mirror `createCalibration`/`requestSpareParts`). `requestBody` = `$ref`-ONLY `requestBodies/AddMeasurementBody` (G-OAS-403-DISAMBIG: KHÔNG sibling cạnh `$ref`); `required:true` đặt TRONG component.

**(4) VERB-FLIP-THIS-ROUND — flip bare→`methods=['POST']` NGAY, `_PARITY_VERB_ALLOWLIST` GIỮ `set()` rỗng.** Flip decorator `api/imm11.py:120` `@frappe.whitelist()` → `@frappe.whitelist(methods=['POST'])` — **ĐÚNG 1 dòng** (`git diff api/imm11.py` = đúng 1 dòng decorator; signature `api/imm11.py:121-123` + body `:124-132` + `rbac.require('calibration.write')` `:124` UNCHANGED). Sau flip, `add_measurement` POST-only at source ⇒ contract POST khớp ⇒ **KHÔNG** vào `_PARITY_VERB_ALLOWLIST` (allowlist chỉ dành bare-`@whitelist` write-action **chưa** flip; flip-this-round ⇒ không cần allowlist). Verb-parity full-sweep yaml↔runtime **zero-exception** GIỮ sau khi thêm path POST mới + flip. **KHÁC §8.15/ADR-MOBILE-007** (submitCalibration/submitPmResult từng đẩy flip→backlog + allowlist 3rd-entry — nay đã CLOSED ở R33).

**(5) 403 SINGLE-SHAPE + slot `{200,401,403}`.** 403 = SINGLE-SHAPE `Forbidden` (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token trip TRƯỚC `handle()`); in-handler cap-403 (`rbac.require('calibration.write')` `api/imm11.py:124`) đã PHỦ bởi nhánh `Error` của 200-oneOf → slot 403 KHÔNG schema mới (mirror `submitCalibration`/`startRepair`). 401 = `Unauthorized401` SINGLE-SHAPE. `addMeasurement` **∈ `_MVP_BUSINESS_PATHS`** (cap-gated write) ⇒ 401∧403 symmetry tự cân (test so SET, +1 cả 2 slot).

**(6) `IMM11_CAL_NOT_FOUND` (404) + `IMM11_ALREADY_SUBMITTED` (409) Error-on-HTTP-200 (ARRIVE nhánh Error, KHÔNG status-line).** Phiếu∄ → `nthrow(MSG.IMM11_CAL_NOT_FOUND, name=name)` (`services/imm11.py:1112`) ⇒ Error `code=NOT_FOUND http_status=404`; `docstatus==1` (đã submit) → `nthrow(MSG.IMM11_ALREADY_SUBMITTED)` (`services/imm11.py:1114`) ⇒ Error `code=CONFLICT http_status=409`. CẢ HAI đến trên **HTTP-200** (quirk §5, KHÔNG status-line). Client route theo `body.http_status` ∈ bounded enum `{400,401,403,404,409,413,422,429,500}` (R11) — **enum ĐÃ ⊇ {404,409}, KHÔNG đổi enum**. KHÔNG mở schema/slot status-line mới.

## Alternatives (rejected)

- **(a) reuse `SubmitCalibrationResponse` 4-key / `*ActionResponse` 2-key `{name,status}`** — `add_measurement` trả `{name, measurement_count}` (KHÔNG `status`/`overall_result`); ép `{name,status}` → DROP `measurement_count` (client mất "đã ghi mấy điểm" → thừa re-fetch `getCalibration`) HOẶC bịa `status` KHÔNG có trong return. Lệch source 2-key. Loại.
- **(b) `measurement_count` khai `integer enum[0,1]`** (như Check-field Open#1) — `measurement_count` là số đếm thật `len(doc.measurements)`, có thể >1 (N điểm-đo); bound `[0,1]` = sai-deser khi N≥2. Loại (mirror `updated` ADR-MOBILE-010 §2 GENUINE integer).
- **(c) đẩy verb-flip → backlog + vào `_PARITY_VERB_ALLOWLIST`** (như §8.15 từng làm) — R33 đã đóng allowlist về `set()`; tái-mở allowlist cho add_measurement = đi ngược closure, để lại divergence dây-dưa. Flip 1-dòng rẻ hơn track backlog. Loại — flip-this-round.
- **(d) flip cả hàm khác / đụng >1 dòng** — chỉ `add_measurement` sót R33; flip 1 dòng decorator `api/imm11.py:120`, KHÔNG đụng signature/body/cap. `git diff` >1 dòng = scope-creep. Loại.
- **(e) khai status-line 404/409 cho `addMeasurement`** — lỗi nghiệp vụ in-handler arrive HTTP-200 + Error (route `body.http_status`), KHÔNG status-line (quirk §5). Slot GIỮ `{200,401,403}`. Loại.
- **(f) `requestBody` chỉ `application/json`** (như `submitCalibration` đơn-field §8.15 INLINE) — `addMeasurement` có 6+1 field giống create-path; Frappe RPC nhận cả `x-www-form-urlencoded` (`form_dict` §9). Khai json-only = lệch khả-năng-nhận thật. Loại — oneOf json+form (mirror `createCalibration`/`requestSpareParts`).
- **(g) đưa `measured_value` vào `required`** — signature có default `=None` (`api/imm11.py:123`); KTV có thể ghi tham-số-đo trước, đo-giá-trị sau. `required` 6-field (không `measured_value`). Loại.

## Consequences

- Mobile đóng **mắt-xích-GIỮA** calibration-detail: `createCalibration → addMeasurement (×N) → submitCalibration`. `submitCalibration` nay tính `overall_result` trên measurement-set THẬT (không còn rỗng). KTV mở `getCalibration` (`Scheduled`/`In Progress`) → có nút "Ghi điểm đo".
- Path/opId **42→43** (`addMeasurement` 43). `info.version` GIỮ `0.1.0-skeleton`. 0 dangling `$ref`.
- Codegen sinh: `addMeasurement(name, parameter_name, unit, nominal_value, tolerance_positive, tolerance_negative, measured_value?)` → `AddMeasurementResponse` (đọc `measurement_count` để hiển thị tiến-độ).
- **⚠️ KHÔNG PURE-YAML (Hyrum) — đụng 1 dòng `api/imm11.py:120`.** Flip GET→POST shifts runtime `x-assetcore-stats`: **get 235→234 / post 253→254** (total 488 GIỮ). ⇒ **re-baseline @source** (KHÔNG tin tuyệt đối số acceptance): `test_oas_d12_error_surface.py:43` `_BASELINE_GET 235→234`; `test_oas_d17_action_enum.py:293-294` `get_count 235→234` / `post_count 253→254`; re-verify ALL 13 `test_oas_*` (d8 derive n_post động → self-check). `_PARITY_VERB_ALLOWLIST` GIỮ `set()` (add_measurement POST-only sau flip — KHÔNG vào allowlist).
- Guard: `TestMobileAddMeasurementContract` (a..j) trong `test_mobile_oas` (`_EXPECTED_TEST_COUNT` bump từ **397**); RED-before/GREEN-after chứng minh cho MỌI TC mới. `test_mobile_docset` (9) + `test_mobile_security_gate` (no-regress) + `test_imm11` (no-regress) GREEN @source. Reconcile `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` + `_GUARD_SUITE_SUM` + `_MOBILE_OAS_TOTAL` trong `test_mobile_docset.py` theo delta TC.
- **HARD-STOP USER:** KHÔNG reload/migrate/commit. Sau USER reload gunicorn `--preload` → LIVE `add_measurement` reject GET(405); trước reload stale worker còn nhận GET — **KHÔNG curl-verify LIVE** (LL-DEPLOY-07).
- **Self-Correction docset:** ADR-MOBILE-010 (`requestSpareParts`) tồn tại trên đĩa nhưng CHƯA đăng-ký trong `README.md` bảng ADR (gap round trước) — vòng này đăng-ký CẢ 010 + 011 ⇒ `test_mobile_docset` TC-MOB-DOC-02 (mọi `ADR-MOBILE-*.md` ∈ README) GIỮ GREEN.

---

## Liên kết

- ADR-MOBILE-006 — POST-action route-by-VALUE + 403 SINGLE-SHAPE (mẫu kế thừa).
- ADR-MOBILE-010 — `requestSpareParts` `updated` GENUINE integer count (precedent `measurement_count`) + flip-vs-clean discipline.
- §8.15 / ADR-IMM11-MOB-02 — `submitCalibration` C3-split Calibration RIÊNG (sibling completion-action cùng IMM-11).
- VERB-PARITY CLOSURE R33 (2026-06-27) — 3 write-action flip `methods=['POST']` + `_PARITY_VERB_ALLOWLIST`→`set()`; `add_measurement` = gap BỎ SÓT mà ADR-011 đóng.
- Core Doc IMM-11: `docs/imm-11/05_API_Specification.md §0.1.4` · `docs/imm-11/04_Backend_Design.md §3.2 / §5 (ADR-IMM11-MOB-03)`.
- Contract: `04-api-contract.md §8.24`.
