# ADR-MOBILE-013 — PM→CM escalation contract (`reportMajorFailure` POST, đóng nút "Báo lỗi nghiêm trọng" PM-detail) — `ReportMajorFailureResponse` RIÊNG 4-key `{pm_wo, new_status, cm_wo_created, asset_status}` (`new_status` = **PMStatus** "Halted–Major Failure", `asset_status` = "Out of Service") + **VERB-FLIP-THIS-ROUND** (bare `@whitelist` → `methods=['POST']`) + **SIGNATURE-FIX** (DROP `failed_item_indexes` — handler↔service mismatch gây `TypeError`→HTTP-500)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-013 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-28 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | ADR-MOBILE-006 (POST-action route-by-VALUE + 403 SINGLE-SHAPE) · ADR-MOBILE-011/012 §(VERB-FLIP-THIS-ROUND discipline + C3-split RIÊNG-schema) · Decision-B (closed-schema oneOf) · C6/C7 (200 oneOf [Env, Error]) · VERB-PARITY CLOSURE R33 (`_PARITY_VERB_ALLOWLIST`→`set()`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm08.py`, `assetcore/services/imm08.py`, `assetcore/services/shared/constants.py`, `assetcore/utils/messages.py`, `assetcore/tests/test_mobile_oas.py`, `assetcore/tests/test_imm08.py`, `assetcore/tests/test_oas_d12_error_surface.py`, `assetcore/tests/test_oas_d15_external_docs.py`, `assetcore/tests/test_oas_d17_action_enum.py`). Contract: [`04-api-contract.md`](./04-api-contract.md). Core Doc IMM-08: `docs/imm-08/05_API_Specification.md §0.1.2` + `§5` + `04_Backend_Design.md §5`.

---

## Context

Màn **`PMWorkOrderDetailView`** (mobile MVP-flow-4) có action-set **THIN**. Ngoài `assignPmTechnician` (DISPATCH — ADR-MOBILE-012) và `submitPmResult` (✅), KTV/Workshop Head khi PM phát hiện **thiết bị hỏng nặng** cần **leo thang ngay**: dừng PM + tạo CM khẩn + đặt asset **Out of Service** — KHÔNG quay về web-FE. Section "major-failure-section" trên detail render nút "Báo lỗi nghiêm trọng (→ CM)" nhưng **không có endpoint mobile-contract** ⇒ dead-end. Đây là **escalation cross-module** PM(IMM-08) → CM(IMM-09, Asset Repair khẩn) + Incident(IMM-12). **KHÁC** `assignPmTechnician` (dispatch cùng-domain) / `addMeasurement` (IMM-11) / `occurred_datetime` (field IMM-12). Vòng này bồi **1 path** (path/opId **44→45**), `info.version` GIỮ `0.1.0-skeleton`, 0 dangling `$ref`.

Service THẬT `report_major_failure(pm_wo_name, *, failure_description)` (`services/imm08.py:744`): guard 404 nếu WO∄ (`nthrow(MSG.IMM08_WO_NOT_FOUND)` `:747`); set PM WO `status=PMStatus.HALTED_MAJOR` (`:749`); `_transition_asset(wo.asset_ref, AssetStatus.OUT_OF_SERVICE, pm_wo_name)` (`:750` — asset → "Out of Service" + **sinh Lifecycle Event audit**); `RepairRepo.create({failure_description, repair_type:"Breakdown", priority:"Emergency", source_pm_wo, ...})` (`:752-762` — **CM WO khẩn**); email khẩn Workshop Head + VP Block2 (`:761-777`); IMM-12 incident best-effort (`:778-790`); return **4-key** `{pm_wo, new_status, cm_wo_created, asset_status}` (`:792-797`).

`reportMajorFailure` có **3 điểm hợp đồng** cần quyết định:

1. **VERB-FLIP-THIS-ROUND.** Handler `report_major_failure` (`api/imm08.py:74`) hiện **bare `@frappe.whitelist()`** ⇒ runtime BE **nhận cả GET** — nhưng đây là write KHÔNG idempotent (**mỗi call tạo 1 CM WO + đặt asset OOS + sinh Incident + gửi email** — KHÔNG hợp GET-semantics). ⚠️ **Core Doc IMM-08 đã khai POST từ lâu** (`05_API_Specification.md §0` catalog row #5 = "POST") ⇒ doc đi trước code. Flip ĐÚNG 1 dòng decorator (`api/imm08.py:74`) ⇒ POST-only @source ⇒ **KHÔNG verb-divergence** ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()` rỗng.
2. **🐞 SIGNATURE-FIX (handler↔service mismatch — lỗi thiết-kế-gốc).** Handler cũ (`api/imm08.py:75-83`) nhận `failed_item_indexes: str = "[]"`, `parse_json` nó, rồi **truyền `failed_item_indexes=failed` vào `svc.report_major_failure`** — trong khi service signature `(pm_wo_name, *, failure_description)` (`:744`) **KHÔNG nhận** keyword này ⇒ **`TypeError: report_major_failure() got an unexpected keyword argument 'failed_item_indexes'`** → `handle()` bọc thành HTTP-500 (hoặc unhandled) **mỗi call** (RED-before). Field `failed_item_indexes` là tàn dư: service + §200 (`04_Backend_Design.md`) + web-FE đều bỏ qua. ⇒ **DROP** param + `parse_json` + pass-through ở handler → align signature ⇒ hết `TypeError`/500. Request-contract đồng bộ DROP field (`additionalProperties:false`).
3. **`ReportMajorFailureResponse` RIÊNG 4-key.** Return THẬT `{pm_wo, new_status, cm_wo_created, asset_status}` (`:792-797`). `new_status` = **PMStatus** 7-state, value-sau-escalate literal **"Halted–Major Failure"** (`PMStatus.HALTED_MAJOR` `:49,794` — **en-dash**, copy byte-khớp). `asset_status` = "Out of Service" (`AssetStatus.OUT_OF_SERVICE` `constants.py:94` `:796`). RIÊNG — KHÔNG reuse envelope action nào khác (4-key cross-module-escalation duy nhất).

## Decision

**(1) `reportMajorFailure` — POST path mới, schema RIÊNG `ReportMajorFailureResponse` 4-key.** Thêm 1 path `POST /api/method/assetcore.api.imm08.report_major_failure` opId **`reportMajorFailure`** (UNIQUE camelCase), tag `work-order`, summary `[MVP-4] Báo lỗi nghiêm trọng PM → CM khẩn + Asset Out of Service`. `ReportMajorFailureResponse` closed (`additionalProperties:false`) **EXACT 4 prop** `{pm_wo string, new_status string, cm_wo_created string, asset_status string}` `required[pm_wo, new_status, cm_wo_created, asset_status]` (cả 4 luôn trả — `services/imm08.py:792-797`). `ReportMajorFailureEnvelope` closed `required[success,data]`, `success enum[true]`, `data = $ref ReportMajorFailureResponse`. 200 = oneOf `[ReportMajorFailureEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 nhánh closed + `success` enum disjoint `[true]`/`[false]`.

**(2) `new_status` = PMStatus 7-state, example "Halted–Major Failure"; `asset_status` example "Out of Service".** `new_status.enum` = **PMStatus-canonical** `[Open, In Progress, Completed, Overdue, Cancelled, "Halted–Major Failure", "Pending–Device Busy"]` (`services/imm08.py:43-50` — đủ 7 state để codegen sinh đúng máy-trạng-thái), `example: "Halted–Major Failure"` (`PMStatus.HALTED_MAJOR` `:49,794`). Lưu ý **en-dash (–)** trong "Halted–Major Failure"/"Pending–Device Busy" — copy byte-khớp source (KHÔNG hyphen-minus). `asset_status` `type:string` `example: "Out of Service"`.

**(3) `requestBody` — INLINE (path-level), content `application/json` only, required EXACT 2 `[pm_wo_name, failure_description]` (DROP `failed_item_indexes`).** `ReportMajorFailureRequest` closed (`additionalProperties:false`) `required` EXACT = `[pm_wo_name, failure_description]` (2 positional KHÔNG default @`api/imm08.py:74` SAU fix). Cả 2 prop = `type:string`. `requestBody.required:true`. **KHÔNG** đưa `failed_item_indexes` (service KHÔNG nhận — xem Context §2).

**(4) VERB-FLIP-THIS-ROUND + SIGNATURE-FIX — flip bare→`methods=['POST']` + DROP `failed_item_indexes` NGAY.** Flip decorator `api/imm08.py:74` `@frappe.whitelist()` → `@frappe.whitelist(methods=['POST'])`. Đồng thời sửa handler body: signature → `report_major_failure(pm_wo_name, failure_description)` (bỏ `failed_item_indexes`), bỏ block `parse_json(failed_item_indexes, ...)`, gọi `handle(svc.report_major_failure, pm_wo_name, failure_description=failure_description)` (bỏ kwarg `failed_item_indexes=`). `rbac.require('pm.write')` `:77` UNCHANGED. Sau flip POST-only at source ⇒ KHÔNG vào `_PARITY_VERB_ALLOWLIST` (giữ `set()`).

**(5) 403 SINGLE-SHAPE + slot `{200,401,403}`.** 403 = SINGLE-SHAPE `Forbidden` (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token trip TRƯỚC `handle()`); in-handler cap-403 (`rbac.require('pm.write')` `api/imm08.py:77`) đã PHỦ bởi nhánh `Error` của 200-oneOf → slot 403 KHÔNG schema mới. 401 = `Unauthorized401` SINGLE-SHAPE. `reportMajorFailure` **∈ `_MVP_BUSINESS_PATHS`** **VÀ ∈ `_MVP_ACTION_ENVELOPE`** (map `→ ReportMajorFailureEnvelope`) ⇒ 401∧403 symmetry tự cân (test so SET, +1 cả 2 slot).

**(6) `IMM08_WO_NOT_FOUND` (404) Error-on-HTTP-200 (ARRIVE nhánh Error, KHÔNG status-line).** WO∄ → `nthrow(MSG.IMM08_WO_NOT_FOUND, name=pm_wo_name)` (`services/imm08.py:747`) ⇒ Error `code=NOT_FOUND http_status=404` (`messages.py:556`), đến trên **HTTP-200** (quirk §5). Client route theo `body.http_status` ∈ bounded enum `{400,401,403,404,409,413,422,429,500}` (R11) — **enum ĐÃ ⊇ {404}, KHÔNG đổi enum**. KHÁC `assignPmTechnician` (404/409/422): `report_major_failure` CHỈ guard 404 (KHÔNG bad-state — escalate được từ mọi state đang-PM). KHÔNG mở schema/slot status-line mới.

## Alternatives (rejected)

- **(a) giữ `failed_item_indexes` ở request "để FE log" + mở rộng service nhận thêm** — bịa field service KHÔNG dùng (service + §200 + web-FE đều bỏ qua); mở signature service không cần thiết. Loại — DROP field cả request LẪN handler (align signature).
- **(b) bọc `try/except TypeError` ở handler nuốt lỗi `failed_item_indexes`** — che lỗi thiết kế, vẫn rủi-ro-500 với input khác; KHÔNG sửa root-cause. Loại — fix signature gốc.
- **(c) reuse envelope action khác (vd CreateRepairWorkOrderCreatedEnvelope)** — return PM-escalation 4-key `{pm_wo, new_status, cm_wo_created, asset_status}` là shape DUY NHẤT (cross-module: pm_wo + cm_wo_created + asset_status). Reuse → codegen sai field. Loại — RIÊNG closed 4-key.
- **(d) `new_status` literal-single `enum:[Halted–Major Failure]`** — escalate chỉ set HALTED_MAJOR nên có thể bound 1-value; NHƯNG return `wo.status` field PMStatus → khai đủ 7-state an-toàn-forward (mirror assignPmTechnician). Giữ enum 7-state, example "Halted–Major Failure".
- **(e) đẩy verb-flip → backlog + vào `_PARITY_VERB_ALLOWLIST`** — R33 đã đóng allowlist về `set()`; tái-mở = đi ngược closure. Flip 1-dòng rẻ hơn. Loại — flip-this-round.
- **(f) requestBody `oneOf json+form`** — action đơn-record (mirror `assignPmTechnician`/repair `assignTechnician` INLINE json-only). Loại — json-only INLINE.
- **(g) khai status-line 404 cho `reportMajorFailure`** — WO∄ arrive HTTP-200 + Error (route `body.http_status`), KHÔNG status-line (quirk §5). Slot GIỮ `{200,401,403}`. Loại.

## Consequences

- Mobile đóng **escalation PM→CM** trên PM-detail: KTV phát hiện hỏng nặng → nút "Báo lỗi nghiêm trọng (→ CM)" gọi được; sau call PM WO → "Halted–Major Failure" + asset → "Out of Service" + CM WO khẩn tạo (`cm_wo_created` để client deeplink sang repair-detail).
- Path/opId **44→45** (`reportMajorFailure` 45). `info.version` GIỮ `0.1.0-skeleton`. 0 dangling `$ref`. Tất cả 45/45 operationId camelCase frozen.
- Codegen sinh: `reportMajorFailure(pm_wo_name, failure_description)` → `ReportMajorFailureResponse` (đọc `new_status`/`cm_wo_created`/`asset_status` cập nhật UI + deeplink CM). `new_status.enum` = PMStatus 7-state.
- **⚠️ KHÔNG PURE-YAML (Hyrum) — đụng `api/imm08.py:74-83`** (verb-flip 1 dòng + DROP ~6 dòng param/parse/pass-through). Flip GET→POST shifts runtime `x-assetcore-stats` (1 GET→POST; total GIỮ). ⇒ **re-baseline @source bằng `bench execute generate_spec`** (KHÔNG tin số học): re-read `get_count`/`post_count` → cập nhật `test_oas_d12_error_surface.py` (`_BASELINE_GET`/`_BASELINE_POST`) + `test_oas_d15_external_docs.py` + `test_oas_d17_action_enum.py`; re-verify ALL 13 `test_oas_*`. `_PARITY_VERB_ALLOWLIST` GIỮ `set()`.
- **CM-WO-FIELD-FIX (cùng escalation, lộ khi BE-unit gọi handler — 2 bug runtime thật độc lập với handler `TypeError`)**: `report_major_failure` tạo CM WO (`RepairRepo.create` `services/imm08.py:752`) sai 2 chỗ: (1) KHÔNG set `failure_description` — `Asset Repair.failure_description` là field **mandatory** (`asset_repair.json reqd:1`) ⇒ `MandatoryError` khi insert; (2) `repair_type="Emergency"` KHÔNG hợp lệ — Select-options = `{Corrective, Breakdown, Warranty Repair}` ⇒ `ValidationError`. Cả 2 → HTTP-500 mỗi escalation. Sửa: thêm `"failure_description": failure_description` (mirror `imm09.create_repair_work_order:840`) + `repair_type="Breakdown"` (lỗi nặng = hỏng đột xuất; độ-khẩn ở `priority="Emergency"` ∈ `{Normal, Urgent, Emergency}`). BE-unit gọi HANDLER (KHÔNG service-only) chính là cái phơi cả chuỗi bug tầng-trên.
- **SIGNATURE-FIX hệ quả**: handler hết `TypeError`/500. Guard `TestMobileReportMajorFailureContract` (a..i) trong `test_mobile_oas` (`_EXPECTED_TEST_COUNT` bump từ **417**) + path-count 44→45; `test_imm08` thêm BE-unit happy-path (gọi handler → 200 envelope 4-key — **RED-before do `TypeError`, GREEN-after fix**) + missing-WO 404. `test_mobile_docset` (reconcile `_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL`/`_GUARD_SUITE_EXPECTED`) + `test_mobile_security_gate` (no-regress) GREEN @source.
- **HARD-STOP USER:** KHÔNG reload/migrate/commit. Sau USER reload gunicorn `--preload` → LIVE `report_major_failure` reject GET(405); trước reload stale worker còn nhận GET — **KHÔNG curl-verify LIVE** (LL-DEPLOY-07). KHÔNG curl IP `192.168.10.101`.

---

## Liên kết

- ADR-MOBILE-006 — POST-action route-by-VALUE + 403 SINGLE-SHAPE (mẫu kế thừa).
- ADR-MOBILE-011 — `addMeasurement` VERB-FLIP-THIS-ROUND discipline + C3-split RIÊNG-schema.
- ADR-MOBILE-012 — `assignPmTechnician` (sibling PM-detail action; cùng VERB-FLIP + C3-split pattern). `reportMajorFailure` = escalation kế tiếp cùng màn.
- VERB-PARITY CLOSURE R33 (2026-06-27) — flip write-action + `_PARITY_VERB_ALLOWLIST`→`set()`; `report_major_failure` = gap imm08 còn sót.
- Core Doc IMM-08: `docs/imm-08/05_API_Specification.md §0.1.2` + `§5` · `docs/imm-08/04_Backend_Design.md §5`.
- Contract: `04-api-contract.md`.
