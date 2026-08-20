# ADR-MOBILE-014 — PM reschedule contract (`reschedulePm` POST, **ĐÓNG NỐT** action-set `PMWorkOrderDetailView` — nút "Hoãn lịch (thiết bị bận)") — `ReschedulePmResponse` RIÊNG closed 4-key `{name, old_date, new_date, status}` (`status` = **PMStatus** "Pending–Device Busy" en-dash, mirror `services/imm08.py:50,817`) + **ATOMIC-THIS-ROUND** (KHÔNG verb-flip, KHÔNG signature-fix — handler ĐÃ `methods=['POST']` + signature ĐÃ khớp service)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-014 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-28 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | ADR-MOBILE-006 (POST-action route-by-VALUE + 403 SINGLE-SHAPE) · ADR-MOBILE-012/013 (action-set `PMWorkOrderDetailView` — C3-split RIÊNG-schema, sibling PM-detail) · Decision-B (closed-schema oneOf) · C6/C7 (200 oneOf [Env, Error]) · VERB-PARITY CLOSURE R33 (`_PARITY_VERB_ALLOWLIST`→`set()`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm08.py`, `assetcore/services/imm08.py`, `assetcore/services/shared/rbac.py`, `assetcore/services/shared/constants.py`, `assetcore/utils/messages.py`, `assetcore/tests/guards/test_mobile_oas.py`, `assetcore/tests/imm08/test_imm08.py`, `assetcore/tests/guards/test_oas_d12_error_surface.py`, `assetcore/tests/guards/test_oas_d15_external_docs.py`, `assetcore/tests/guards/test_oas_d17_action_enum.py`). Contract: [`04-api-contract.md`](./04-api-contract.md). Core Doc IMM-08: `docs/imm-08/05_API_Specification.md §0.1.3` + `§8` + `04_Backend_Design.md`.

---

## Context

Màn **`PMWorkOrderDetailView`** (mobile MVP-flow-4) có action-set **THIN**. Sau khi §0.1.1 (`assignPmTechnician` DISPATCH — ADR-MOBILE-012) và §0.1.2 (`reportMajorFailure` ESCALATION — ADR-MOBILE-013) đã wire, action-set còn **đúng 1 nút dead-end**: "Hoãn lịch (thiết bị bận)". Workshop Head/KTV mở `getPmWorkOrder` detail thấy **thiết bị đang dùng** (ca cấp cứu/ca mổ) đúng ngày PM → cần **hoãn lịch** + ghi lý do bắt buộc ngay tại màn (KHÔNG quay về web-FE). Section "reschedule-section" render nút nhưng **không có endpoint mobile-contract** ⇒ dead-end. Đây là **RESCHEDULE cùng-domain PM** (status → `Pending–Device Busy`) — **KHÁC** `assignPmTechnician` (dispatch cùng-domain, status → In Progress) / `reportMajorFailure` (escalation cross-module PM→CM). Vòng này bồi **1 path** (path/opId **45→46**) ⇒ **action-set `PMWorkOrderDetailView` ĐÓNG NỐT** (0 nút dead-end), `info.version` GIỮ `0.1.0-skeleton`, 0 dangling `$ref`.

Service THẬT `reschedule(name, *, new_date, reason)` (`services/imm08.py:807`): guard `if not reason or len(reason.strip()) < 5: raise validation("Lý do hoãn lịch là bắt buộc (tối thiểu 5 ký tự)")` (`:808-812` helper `errors.py:62` → `http_status=422`, RECONCILED vòng-2 — xem addendum cuối); WO∄ → `nthrow(MSG.IMM08_WO_NOT_FOUND, name=name)` (`:813` → 404); chụp `old_date = str(wo.due_date)` (`:815`); `wo.due_date = new_date` (`:816`); `wo.status = PMStatus.PENDING_BUSY` (`:817`); append `wo.technician_notes` `[Hoãn lịch {old}→{new}]: {reason}` (`:818`); `PMWorkOrderRepo.save(wo)` (`:819`); **nếu** WO đang `In Progress` → `_transition_asset(wo.asset_ref, AssetStatus.ACTIVE, wo.name)` (`:821-822` — asset khôi phục "Active" + **sinh Lifecycle Event audit**); return **4-key** `{name, old_date, new_date, status}` (`:823`).

`reschedulePm` có **3 điểm hợp đồng** cần quyết định:

1. **🟢 ATOMIC-THIS-ROUND (KHÔNG verb-flip + KHÔNG signature-fix).** KHÁC sibling §0.1.1/§0.1.2: handler `reschedule_pm` (`api/imm08.py:86`) **ĐÃ** `@frappe.whitelist(methods=['POST'])` (đã flip round trước) **VÀ** signature `reschedule_pm(name, new_date, reason)` (`:87`) **ĐÃ** khớp service `reschedule(name, *, new_date, reason)` (`:807`) — handler chỉ `rbac.require("pm.reschedule")` (`:88`) + `handle(svc.reschedule, name, new_date=new_date, reason=reason)` (`:89`). ⇒ **KHÔNG có gap source**: round này **KHÔNG đụng `api`/`service` 1 dòng nào** → PURE-YAML+test. `_PARITY_VERB_ALLOWLIST` GIỮ `set()`. ⚠️ Core Doc IMM-08 đã khai POST + response 4-key từ lâu (`05_API_Specification.md §0` catalog row #6 + `§8`) ⇒ doc đi trước code; round này = đưa contract mobile khớp source-intent ĐÃ-CÓ.
2. **`ReschedulePmRequest` closed 3-required + `reason.minLength:5` + `new_date.format:date`.** Signature `(name, new_date, reason)` 3 positional KHÔNG default. `reason.minLength: 5` **mirror guard service** `len(reason.strip()) < 5` (`:808`) ⇒ codegen sinh client-side guard ≥5 khớp service → giảm round-trip 422. `new_date.format: date` ⇒ codegen sinh kiểu Date (YYYY-MM-DD, đi vào `wo.due_date`).
3. **`ReschedulePmResponse` RIÊNG closed 4-key date-pair.** Return THẬT `{name, old_date, new_date, status}` (`:823`). Đây là shape **date-pair DUY NHẤT** (`old_date`/`new_date` — KHÔNG envelope action nào khác có). `status` = **PMStatus** 7-state, value-sau-hoãn literal **"Pending–Device Busy"** (`PMStatus.PENDING_BUSY` `:50,817` — **en-dash U+2013**, copy byte-khớp, KHÔNG hyphen-minus U+002D). RIÊNG — KHÔNG reuse `AssignPmTechnician*`/`ReportMajorFailure*`.

## Decision

**(1) `reschedulePm` — POST path mới, schema RIÊNG `ReschedulePmResponse` 4-key.** Thêm 1 path `POST /api/method/assetcore.api.imm08.reschedule_pm` opId **`reschedulePm`** (UNIQUE camelCase), tag `work-order`, summary `[MVP-4] Hoãn lịch PM (thiết bị đang dùng) → Pending–Device Busy`. `ReschedulePmResponse` closed (`additionalProperties:false`) **EXACT 4 prop** `{name string, old_date string, new_date string, status string}` `required[name, old_date, new_date, status]` (cả 4 luôn trả — `services/imm08.py:823`). `ReschedulePmEnvelope` closed `required[success,data]`, `success enum[true]`, `data = $ref ReschedulePmResponse`. 200 = oneOf `[ReschedulePmEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 nhánh closed + `success` enum disjoint `[true]`/`[false]`.

**(2) `status` = PMStatus 7-state, example "Pending–Device Busy" (en-dash).** `status.enum` = **PMStatus-canonical** `[Open, In Progress, Completed, Overdue, Cancelled, "Halted–Major Failure", "Pending–Device Busy"]` (`services/imm08.py:43-50` — đủ 7 state để codegen sinh đúng máy-trạng-thái), `example: "Pending–Device Busy"` (`PMStatus.PENDING_BUSY` `:50,817`). Lưu ý **en-dash (–) U+2013** trong "Pending–Device Busy"/"Halted–Major Failure" — copy byte-khớp source (KHÔNG hyphen-minus U+002D).

**(3) `requestBody` — INLINE (path-level), content `application/json` only, required EXACT 3 `[name, new_date, reason]` (`reason.minLength:5`, `new_date.format:date`).** `ReschedulePmRequest` closed (`additionalProperties:false`) `required` EXACT = `[name, new_date, reason]` (3 positional KHÔNG default @`api/imm08.py:87`). `name`/`reason` = `type:string`; `reason` thêm `minLength: 5` (mirror service guard `:808`); `new_date` = `type:string, format:date`. `requestBody.required:true`.

**(4) ATOMIC-THIS-ROUND — KHÔNG verb-flip, KHÔNG signature-fix, KHÔNG đụng `api`/`service`.** Handler `api/imm08.py:86` ĐÃ `methods=['POST']` + signature ĐÃ khớp service ⇒ round chỉ +YAML +test. `_PARITY_VERB_ALLOWLIST` GIỮ `set()` (reschedule_pm POST-only @source từ trước).

**(5) 403 SINGLE-SHAPE + slot `{200,401,403}`.** 403 = SINGLE-SHAPE `Forbidden` (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token trip TRƯỚC `handle()`); in-handler cap-403 (`rbac.require('pm.reschedule')` `api/imm08.py:88`) đã PHỦ bởi nhánh `Error` của 200-oneOf → slot 403 KHÔNG schema mới. 401 = `Unauthorized401` SINGLE-SHAPE. `reschedulePm` **∈ `_MVP_BUSINESS_PATHS`** **VÀ ∈ `_MVP_ACTION_ENVELOPE`** (map `→ ReschedulePmEnvelope`) ⇒ 401∧403 symmetry tự cân (test so SET, +1 cả 2 slot). **Lưu ý cap-name `pm.reschedule`** (`rbac.py:94` → `("PM Work Order","write")`) — KHÁC sibling `pm.write`, nhưng cùng surface dispatcher-403/cap-403 nên slot KHÔNG đổi.

**(6) 2 guard Error-on-HTTP-200 — `Error.http_status ⊇ {404,422}` (ARRIVE nhánh Error, KHÔNG status-line).** (a) `reason` < 5 ký tự → `validation(...)` helper (`services/imm08.py:809` → `services/shared/errors.py:62` = `ServiceError(VALIDATION, ..., http_status=422)`) ⇒ Error `code=VALIDATION http_status=422` (canonical `_HTTP_FOR_CODE[VALIDATION]=422` `utils/response.py:61` — **vòng-2 RECONCILE, xem addendum cuối**); (b) WO∄ → `nthrow(MSG.IMM08_WO_NOT_FOUND, name=name)` (`:813`) ⇒ Error `code=NOT_FOUND http_status=404`. Cả 2 đến trên **HTTP-200** (quirk §5). Client route theo `body.http_status` ∈ bounded enum `{400,401,403,404,409,413,422,429,500}` (R11) — **enum ĐÃ ⊇ {404,422}, KHÔNG đổi enum/Error schema**. KHÁC `reportMajorFailure` (chỉ 404): reschedule có thêm guard 422 (reason<5). KHÔNG mở schema/slot status-line mới.

## Alternatives (rejected)

- **(a) reuse `AssignPmTechnician*`/`ReportMajorFailure*` envelope** — return reschedule 4-key `{name, old_date, new_date, status}` là shape **date-pair DUY NHẤT** (`old_date`/`new_date` không envelope nào khác có). Reuse → codegen sai field. Loại — RIÊNG closed 4-key.
- **(b) `reason` KHÔNG `minLength`** — service guard `len(strip)<5 → VALIDATION 422` (`:808`); bỏ `minLength:5` → codegen mất client-guard ⇒ FE đẩy reason rỗng/ngắn → 422 round-trip thừa. Loại — `minLength:5` mirror service.
- **(c) `status` literal-single `enum:[Pending–Device Busy]`** — reschedule chỉ set PENDING_BUSY nên có thể bound 1-value; NHƯNG return `wo.status` field PMStatus → khai đủ 7-state an-toàn-forward (mirror §0.1.1/§0.1.2). Giữ enum 7-state, example "Pending–Device Busy".
- **(d) VERB-FLIP / sửa handler "cho đồng bộ sibling"** — handler `reschedule_pm` `api/imm08.py:86` ĐÃ `methods=['POST']` + signature ĐÃ khớp service (`:807`) ⇒ KHÔNG có gap. Đụng api/service = phá ATOMIC + shift `generate_spec` stat vô cớ. Loại — round PURE-YAML+test.
- **(e) `new_date` `type:string` trần (KHÔNG `format:date`)** — `wo.due_date` là Date; `format:date` cho codegen sinh kiểu Date + validate YYYY-MM-DD. Loại — giữ `format:date`.
- **(f) requestBody `oneOf json+form`** — action đơn-record (mirror `assignPmTechnician`/`reportMajorFailure` INLINE json-only). Loại — json-only INLINE.
- **(g) khai status-line 404/422 cho `reschedulePm`** — WO∄/reason<5 arrive HTTP-200 + Error (route `body.http_status`), KHÔNG status-line (quirk §5). Slot GIỮ `{200,401,403}`. Loại.

## Consequences

- Mobile **ĐÓNG NỐT** action-set `PMWorkOrderDetailView`: nút "Hoãn lịch (thiết bị bận)" gọi được; sau call PM WO → "Pending–Device Busy" + (nếu đang In Progress) asset khôi phục "Active". Action-set `{createPmWorkOrder → assignPmTechnician → submitPmResult → reportMajorFailure → reschedulePm}` đầy đủ — **0 nút dead-end**.
- Path/opId **45→46** (`reschedulePm` 46). `info.version` GIỮ `0.1.0-skeleton`. 0 dangling `$ref`. Tất cả 46/46 operationId camelCase frozen + UNIQUE.
- Codegen sinh: `reschedulePm(name, new_date, reason)` → `ReschedulePmResponse` (đọc `old_date`/`new_date`/`status` cập nhật UI lịch PM). `status.enum` = PMStatus 7-state; `reason` client-guard ≥5; `new_date` kiểu Date.
- **🟢 ATOMIC — KHÔNG đụng `api/imm08.py`/`services/imm08.py`** (KHÁC ADR-013 PURE-YAML-vi-phạm-Hyrum). ⇒ `generate_spec` `x-assetcore-stats` get/post **UNCHANGED** ⇒ `test_oas_d12_error_surface.py`/`test_oas_d15_external_docs.py`/`test_oas_d17_action_enum.py` **RE-VERIFY @source** bằng `bench execute generate_spec` (kỳ vọng count KHÔNG đổi → **KHÔNG re-baseline** trừ khi phát hiện drift — KHÁC R36 phải re-baseline do verb-flip shift 1 GET→POST). `_PARITY_VERB_ALLOWLIST` GIỮ `set()`.
- **Guard bump**: `TestMobileReschedulePmContract` (a..h ≥8 TC) trong `test_mobile_oas` (`_EXPECTED_TEST_COUNT` bump) + path-count 45→46; `test_imm08` +3 BE-unit (happy-path 200 envelope 4-key · reason<5 → VALIDATION 422 · missing-WO → NOT_FOUND 404). `test_mobile_docset` (reconcile counters + **ADR-MOBILE-014 đăng ký README** cho `TC-MOB-DOC` parity glob) + `test_mobile_security_gate` (no-regress) GREEN @source.
- **`Error.http_status ⊇ {404,422}`** ĐÃ trong bounded enum R11 → **KHÔNG đổi `Error` schema** (404=WO∄, 422=reason<5).
- **HARD-STOP USER:** KHÔNG migrate/commit. *(⚠️ vòng-2: điểm "KHÔNG cần reload" LẬT — xem RECONCILE dưới: đụng `services/imm08.py:809` ⇒ LIVE-effect → USER reload gunicorn `--preload`.)* KHÔNG curl-verify LIVE (LL-DEPLOY-07). KHÔNG curl IP `192.168.10.101`.

---

## RECONCILE (vòng 2, 2026-06-28) — BE honor 422 (đóng OPEN ISSUE Round-1)

> Addendum cho ADR-MOBILE-014. KHÔNG supersede schema/path/envelope/cap (giữ nguyên Accepted). CHỈ lật điểm **"ATOMIC = KHÔNG đụng service"** + chốt **http_status reason<5 = 422**. Đồng bộ Core Doc `docs/imm-08/05_API_Specification.md §0.1.3` (`ADR-IMM08-MOB-03-R2`).

- **OPEN DRIFT (R37)** → **RECONCILED**: R37 khai `reason`<5 → 422 nhưng chốt "ATOMIC KHÔNG đụng service"; service `:809` raise raw `ServiceError(ErrorCode.VALIDATION, msg)` → default `http_status=400` (`errors.py:36`), KHÔNG 422 ⇒ doc đúng (422) / code lệch (400). BE-unit trung thực assert 400 + flag [BA].
- **Quyết định: BE=422 theo canonical `_HTTP_FOR_CODE` SSoT** (`utils/response.py:61` `ErrorCode.VALIDATION → 422`). Đúng-1-dòng `services/imm08.py:809`: raw `ServiceError(ErrorCode.VALIDATION, msg)` → `validation(msg)` helper (`errors.py:62` = `http_status=422`) HOẶC kwarg `http_status=422`.
- **Blast-radius = 1 raise** (`:809`). KHÔNG đổi default `ServiceError.__init__` (`errors.py:36`); các VALIDATION raise khác trong `imm08` (assign_technician/create_adhoc/set-status…) GIỮ **400** (regression-fence). Mirror tiền lệ IMM-09 (`test_imm09.py:1683-1685` code×status ngoại-lệ-có-chủ-đích). Reconcile toàn-cục = `[ROADMAP]`.
- **OpenAPI UNCHANGED**: 422 ĐÃ ∈ `Error.http_status` bounded-enum (`assetcore-mobile.openapi.yaml:597`); `generate_spec` get=232/post=256/total=488 **UNCHANGED** (http_status = giá-trị-runtime, KHÔNG ảnh hưởng static spec) ⇒ `test_oas_d12/d15/d17` re-verify @source, **KHÔNG re-baseline**.
- **Test delta**: `test_imm08.py::test_reschedule_reason_too_short_validation_422_envelope` assert `http_status` `400 → 422` + comment "DRIFT/SOURCE-TRUTH 400" → "RECONCILED 422". `test_imm08`/`test_imm08_pm_overdue`/`test_mobile_oas`/`test_mobile_docset` GREEN @source bằng `bench --site miyano run-tests`.
- **Deploy gate**: LIVE-effect (sửa `services/imm08.py`) ⇒ **HARD-STOP USER reload gunicorn `--preload`**. Verify SOURCE-TRUTH qua `bench run-tests`, KHÔNG curl IP `192.168.10.101` (LL-DEPLOY-07). KHÔNG commit/migrate.

---

## Liên kết

- ADR-MOBILE-006 — POST-action route-by-VALUE + 403 SINGLE-SHAPE (mẫu kế thừa).
- ADR-MOBILE-012 — `assignPmTechnician` (sibling PM-detail action; VERB-FLIP + C3-split). Mắt-xích-GIỮA action-set.
- ADR-MOBILE-013 — `reportMajorFailure` (sibling PM-detail action; VERB-FLIP + SIGNATURE-FIX). Escalation kế tiếp cùng màn.
- VERB-PARITY CLOSURE R33 (2026-06-27) — `_PARITY_VERB_ALLOWLIST`→`set()`; `reschedule_pm` ĐÃ POST-only @source (KHÔNG nằm trong gap — round ATOMIC).
- Core Doc IMM-08: `docs/imm-08/05_API_Specification.md §0.1.3` + `§8` · `docs/imm-08/04_Backend_Design.md`.
- Contract: `04-api-contract.md`.
