# ADR-MOBILE-047 — `reportIncident` idempotency key `client_request_id` (**CR-24 · BE-OWNED mechanism + OAS property-add** — đóng cửa sổ re-drain outbox tạo phiếu sự cố **TRÙNG** khi response `report_incident` rớt mạng; bồi 1 **property OPTIONAL** `client_request_id` vào schema `ReportIncidentRequest` (∉ `required[]`) + hiện thực dedupe backend (DocType field unique index → dedupe O(1) index-seek + race-handler `UniqueValidationError`); **KHÁC ADR-021..046 (contract-only pure-yaml path-add)**: ADR này CÓ đụng `.py` + DocType + **`bench migrate`** (tạo cột + unique index) — **HARD-STOP USER reload gunicorn** cho đường HTTP live; NĐ98 audit-integrity: call trùng **KHÔNG** double lifecycle event `incident_reported` + **KHÔNG** double IMM Audit Trail)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-047 |
| Phase | C — API contract (codegen-ready) + BE mechanism |
| Ngày | 2026-07-14 |
| Tác giả | BE (Frappe) — factory CR-24 |
| **Status** | **Accepted** |
| Bám quyết định | **CR-24** (idempotency `client_request_id` cho `report_incident`) · Handoff [`HANDOFF-CORE-DEV-CR24-idempotency.md`](./HANDOFF-CORE-DEV-CR24-idempotency.md) (client-side outbox drain — repo `assetcore-mobile`) · [`07-offline-sync.md`](./07-offline-sync.md) (outbox re-drain) · [`08-security-compliance.md`](./08-security-compliance.md) (provenance + audit-trail NĐ98) · **ADR-MOBILE-001** (Decision-B route-by-VALUE, Error envelope HTTP-200) · **ADR-MOBILE-027 §8.34 `attachIncidentPhoto`** (F2 báo hỏng IMM-12 sibling path) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (@2026-07-14): DocType `Incident Report` field `client_request_id` (`Data`, `read_only`, `no_copy`, `set_only_once`, **`unique:1`**) @`assetcore/assetcore/doctype/incident_report/incident_report.json:414` — cột DB `varchar(140) NULL UNI` (verify `SHOW COLUMNS`/`SHOW INDEX` sau `bench migrate`; nullable ⇒ nhiều phiếu KHÔNG-khoá lưu NULL, MariaDB unique cho phép nhiều NULL → backward-compat). Service `assetcore/services/imm12.py`: helper `_dedupe_lookup(client_request_id)` @**450** (index-seek `frappe.db.get_value("Incident Report", {"client_request_id": key}, ["name","status","severity"], as_dict=True)` → shape create-response `{name,status,severity}` hoặc `None`); `report_incident(..., *, client_request_id: str = "")` @**468/484**; **dedupe pre-check** `existing = _dedupe_lookup(client_request_id); if existing: return existing` @**499-501** (TRƯỚC mọi validation/new_doc → 0 lifecycle/0 audit lần 2); persist `if client_request_id: doc.client_request_id = client_request_id` @**544-545** (rỗng → KHÔNG set → NULL); **race-handler** `try: doc.insert() except frappe.UniqueValidationError: frappe.clear_last_message(); winner = _dedupe_lookup(...); if winner: return winner` @**548-559** (concurrent re-drain 2 request cùng key → unique DB chặn → re-read → return winner, KHÔNG raise). API `assetcore/api/imm12.py`: `report_incident(..., client_request_id: str = "")` @**88/102** (KHÔNG `str|None` → tránh HTTP 417) → `handle(svc_report, ..., client_request_id=client_request_id)` @**131**. OAS `ReportIncidentRequest.properties.client_request_id: {type: string}` @`openapi/assetcore-mobile.openapi.yaml:3271` (∉ `required[]`; schema GIỮ open). Narrative: [`04-api-contract.md`](./04-api-contract.md) §8.3 `reportIncident` (idempotency).

---

## Context

Mobile app dùng **write-outbox** offline (repo `assetcore-mobile`, `07-offline-sync.md`): thao tác "Báo hỏng thiết bị" (F2, IMM-12) khi mất mạng được enqueue vào SQLite, drain lại khi có mạng. Cửa sổ **residual** còn hở: server ĐÃ tạo `Incident Report` nhưng **response rớt mạng** trước khi client nhận `name` + persist resume-marker `incidentName` → lần re-drain kế **re-POST** `report_incident` → **phiếu sự cố #2 trùng**. Vì mỗi phiếu sự cố sinh 1 **lifecycle event `incident_reported`** (trục §10) + 1 dòng **IMM Audit Trail** (hash-chain), phiếu trùng **làm bẩn vết audit NĐ98** (2 event/2 audit row cho 1 sự cố thực).

Resume-marker `incidentName` (client) đóng case *"response ĐÃ về"*; **`client_request_id` đóng case *"response BỊ MẤT"*** — 2 cơ chế bù nhau, KHÔNG thay thế (Handoff §3). Client gửi khoá bền `item.id` (UUID mint 1 lần lúc enqueue, ổn định qua mọi re-drain) → server dedupe theo khoá → re-POST trả `name` phiếu đã tạo thay vì insert #2.

**KHÁC ADR-021..046 (contract-only pure-yaml):** ADR này là **BE-OWNED** — hiện thực cơ chế dedupe THẬT ở backend (DocType field + service + API param) + **1 property-add OAS** (client tiêu thụ). CÓ đụng `.py` + DocType JSON + `bench migrate` (tạo cột + unique index) ⇒ **KHÔNG [AUTO]** — đường HTTP live cần **USER reload gunicorn (`--preload`)** (HARD-STOP). `bench --site miyano run-tests` re-import ⇒ test xanh nhưng endpoint HTTP chưa live tới khi reload.

**Cơ-chế (đã VERIFY @source):**

### DocType field `client_request_id` — `Data` unique nullable
- `{fieldname: client_request_id, fieldtype: Data, read_only:1, no_copy:1, set_only_once:1, unique:1}` @`incident_report.json:414`. `bench migrate` → cột `varchar(140) NULL UNI` + BTREE unique index (→ dedupe **O(1) index-seek**, KHÔNG full-table scan).
- **Backward-compat qua NULL:** phiếu KHÔNG-khoá → field không set → **NULL**; MariaDB unique index cho phép **nhiều NULL** ⇒ mỗi call không-khoá = 1 phiếu riêng (precedent: `AC Asset.gmdn_code` unique optional — 520/525 NULL, 0 empty-string). `doc.client_request_id = key` CHỈ khi `key` truthy @`imm12.py:544-545`.

### Service dedupe — 2 lớp (pre-check + unique-constraint race-handler)
- **Lớp 1 (pre-insert dedupe):** `_dedupe_lookup(key)` @`imm12.py:450` → nếu tồn tại, `return existing` @`:501` **TRƯỚC** khối tạo → 0 `new_doc`, 0 lifecycle `incident_reported`, 0 audit. Xử lý ~100% ca thực (outbox re-drain tuần tự).
- **Lớp 2 (race concurrent):** `try doc.insert() except frappe.UniqueValidationError` @`:548-559` → unique DB chặn 2 request cùng key in-flight đồng thời → `frappe.clear_last_message()` (dọn msgprint "must be unique") → `_dedupe_lookup` re-read → `return winner`, KHÔNG raise ra client, KHÔNG tạo phiếu trùng. Defense-in-depth (belt-and-suspenders).

### Backward-compat 100%
Request KHÔNG `client_request_id` (hoặc rỗng) → `_dedupe_lookup("")` return `None` → flow tạo-mới NGUYÊN VẸN (mỗi call = 1 phiếu). Signature thêm **keyword-only param default `""`** ⇒ 0 breaking call-site (test/hook/curl cũ chạy nguyên).

## Decision

**Bồi 1 property OPTIONAL `client_request_id: {type: string}` vào `ReportIncidentRequest.properties` (∉ `required[]`) + hiện thực dedupe backend (DocType unique field + service 2-lớp + API pass-through).**

1. **OAS** — `ReportIncidentRequest.properties.client_request_id` @`yaml:3271`: `type: string`, description grounded verbatim docstring (nêu "idempotency"). **∉ `required[]`** (GIỮ EXACT 4 `[asset,incident_type,severity,description]`). **Schema GIỮ OPEN** (`additionalProperties` KHÔNG set) — xem Alternatives F. Handler-parity: `client_request_id ∈ inspect.signature(imm12.report_incident)` ⇒ MỌI yaml-prop ⊆ live-params (guard 13g GIỮ xanh).
2. **API** @`imm12.py:102`: `client_request_id: str = ""` (KHÔNG `str|None` → tránh HTTP 417 coercion) → pass-through `handle(svc_report, ..., client_request_id=client_request_id)` @`:131`.
3. **Service** @`imm12.py:484`: keyword-only `client_request_id: str = ""`; dedupe pre-check @`:499-501`; persist-if-truthy @`:544-545`; race-handler `UniqueValidationError` @`:548-559`.
4. **DocType** @`incident_report.json:414`: `Data` unique read_only no_copy set_only_once → `bench migrate` tạo cột + unique index.

**Blast-radius:** +1 OAS property (additive) + `.py` service/API + 1 DocType field + `bench migrate`. **KHÔNG [AUTO]** — USER reload gunicorn cho HTTP live.

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | HTTP header `Idempotency-Key` thay body-field | SAI transport: Frappe RPC `form_dict` KHÔNG route header sạch (§9) — body-field `client_request_id` nhất-quán json+form. |
| B | `search_index:1` (index thường) thay `unique:1` | Mất lớp-2 race-handler: không có DB unique constraint ⇒ 2 re-drain concurrent cùng qua pre-check → 2 phiếu. `unique:1` (nullable) đóng khe race + vẫn backward-compat qua NULL. |
| C | `unique:1` + lưu `""` cho phiếu không-khoá | VỠ backward-compat: 2 phiếu không-khoá cùng `""` → unique violation. Frappe lưu Data rỗng → NULL (verify gmdn_code precedent) ⇒ chỉ set khi truthy, để NULL khi rỗng. |
| D | TTL/expiry cho khoá (dedupe cửa sổ thời gian) | Over-engineer cho MVP: khoá sống cùng record, dedupe exact-match toàn-thời-gian (đơn giản + đúng — client UUID collision-free). |
| E | Dedupe pre-check ĐỦ (bỏ race-handler) | Hở khe concurrent re-drain (2 request in-flight cùng key qua pre-check trước khi bên nào commit). Giữ CẢ 2 lớp (pre-check + unique race-handler). |
| F | Đóng schema `additionalProperties:false` (như task/handoff giả định) | SAI @source: `ReportIncidentRequest` CỐ Ý **open** — 8 field optional server-nhận (`fault_code`/`workaround_applied`/`clinical_impact`/…) CHƯA bồi vào schema (giữ surface tối thiểu); đóng `false` → codegen strict reject form-encoded client gửi 8 field đó → vỡ. Guard 13k assert `additionalProperties != False`. *(Task/handoff ghi "additionalProperties:false GIỮ" là GIẢ ĐỊNH SAI về schema này — flag open-issue.)* |
| G | `client_request_id ∈ required[]` | SAI: online-first happy-path (KHÔNG outbox) KHÔNG có `item.id` ⇒ required sẽ vỡ call-path cũ. OPTIONAL — backward-compat. |
| ✅ H | property OPTIONAL + DocType unique nullable + service 2-lớp (pre-check + race-handler) + backward-compat NULL | Grounded 1:1 source; dedupe O(1) index-seek; race-safe; backward-compat 100%; NĐ98 audit-integrity (0 double lifecycle/audit); Decision-B intact; guard RED-before/GREEN-after. |

## Consequences

- **(+)** Đóng residual window CR-24: re-drain outbox cùng `client_request_id` → 1 phiếu, call trùng trả `name` phiếu đã tạo (KHÔNG insert #2). **NĐ98 audit-integrity:** call trùng **KHÔNG** double lifecycle event `incident_reported` + **KHÔNG** double IMM Audit Trail (TC2 assert `cho asset == 1` + `audit row cho phiếu == 1`).
- **(+)** **Backward-compat 100%:** request KHÔNG khoá → tạo-mới nguyên vẹn (NULL, multi-NULL hợp lệ). Signature keyword-only default `""` ⇒ 0 breaking call-site.
- **(+)** **Dedupe O(1) index-seek** (`unique` → BTREE index) — KHÔNG full-table scan. **Race-safe** (lớp-2 unique constraint + `UniqueValidationError` handler).
- **(+)** **Contract additive** (Hyrum/One-Version): property OPTIONAL, `required[]` GIỮ EXACT 4, schema GIỮ open, handler-parity ⊆ live-params. Client codegen sinh `client_request_id?: string` (snake_case) — chữ-ký `reportIncident(reportIncidentRequest)` KHÔNG đổi (Handoff §4-A) ⇒ 0 breaking call-site mobile.
- **(−)** **KHÔNG [AUTO] — HARD-STOP USER reload gunicorn (`--preload`):** ADR này đụng `api/imm12.py` + `services/imm12.py` + DocType + `bench migrate` (tạo cột + unique index). `bench run-tests` re-import ⇒ test xanh NHƯNG endpoint HTTP chưa live tới khi USER reload gunicorn. Client `api:gen` (Handoff §2 precondition) chỉ chạy sau khi property land OAS (đã land vòng này).
- **(−)** **`ReportIncidentRequest` schema OPEN** (KHÔNG closed) — KHÁC giả định "additionalProperties:false GIỮ" trong task/Handoff §2. Guard 13k khoá invariant OPEN (chống ai đó đóng schema → vỡ 8 field optional server-nhận form-encoded). *(open-issue: nếu muốn đóng, phải bồi ĐỦ 8 field optional vào schema trước — ngoài scope CR-24.)*
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `704→707` (test_mobile_oas, +3 TC class `TestMobileReportIncidentIdempotencyContract` 13i/13j/13k) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `704→707` + `_GUARD_SUITE_SUM` `847→850` + `_MOBILE_OAS_TOTAL` `873→876` + transition-baseline delta-var `idempotency_cr24_delta=3` (giữ `pre_fc3_six==191`) + 2 hardcoded `_EXPECTED_TEST_COUNT==704` `704→707` + ADR balance `46→47` (ADR-047 + README row). CONTRACT-guard property-add ⇒ **0 path/opId mới** (path-count/c5/parity KHÔNG đổi).

---

## Handoff BE/Test (Bước-4 — ĐÃ XONG, KHÔNG [AUTO] — reload gunicorn)

> **BE-OWNED — KHÔNG contract-only:** đã đụng `api/imm12.py` (@88/102/131) + `services/imm12.py` (@450/484/499-501/544-545/548-559) + `incident_report.json` (@414) + `bench migrate`. **HARD-STOP: USER reload gunicorn (`--preload`)** cho HTTP live. Không commit (HARD-STOP user). DoD VERIFY: `bench --site miyano run-tests --module assetcore.tests.imm12.test_imm12` = **'Ran 131 OK' THẬT** (6 TC mới TC1-6; RED-before neutralize CR-24 → TC1/TC2/TC5/TC6 FAIL → restore → GREEN) · `.test_mobile_oas` = **'Ran 707 OK'** (self-count guard 707==707 + TC7 contract) · `.test_mobile_docset` = **'Ran 9 OK'** (balance ADR 47==47, transition-baseline `pre_fc3_six==191`).

**(1) DocType** (`incident_report.json`) — ĐÃ BỒI: field `client_request_id` (`Data` unique read_only no_copy set_only_once) + `field_order`. `bench migrate` → cột `varchar(140) NULL UNI` + BTREE unique index.

**(2) Service/API** (`services/imm12.py` + `api/imm12.py`) — ĐÃ BỒI: `_dedupe_lookup` helper + `report_incident` param `client_request_id` + dedupe pre-check + persist-if-truthy + race-handler `UniqueValidationError`; API pass-through `handle(...)`.

**(3) OAS** (`openapi/assetcore-mobile.openapi.yaml`) — ĐÃ BỒI: property `client_request_id: {type:string}` vào `ReportIncidentRequest.properties` (∉ required, schema OPEN).

**(4) test_mobile_oas.py** — ĐÃ BỒI: +1 TC class `TestMobileReportIncidentIdempotencyContract` (13i property present+string+desc / 13j optional+required-EXACT-4 / 13k schema-OPEN+handler-parity); `_EXPECTED_TEST_COUNT` `704→707` + 2 hardcoded assert `704→707`. test_imm12.py: +1 class `TestReportIncidentIdempotency` (TC1-6, RED-before proven).

**(5) test_mobile_docset.py** — ĐÃ BỒI: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `704→707` · `_GUARD_SUITE_SUM` `847→850` · `_MOBILE_OAS_TOTAL` `873→876` + delta `idempotency_cr24_delta=3` (giữ `pre_fc3_six==191`). ADR-MOBILE-047 registered README (balance 47==47).

**(6) docs narrative** — ĐÃ XONG: `04-api-contract.md` §8.3 `reportIncident` (idempotency `client_request_id`) + README ADR-row (ADR-MOBILE-047, balance 46→47) + Handoff [`HANDOFF-CORE-DEV-CR24-idempotency.md`](./HANDOFF-CORE-DEV-CR24-idempotency.md) (client-side).

**CR-24 ĐÓNG (BE): re-drain outbox cùng `client_request_id` → 1 phiếu sự cố, 0 double lifecycle/audit — NĐ98 audit-integrity giữ nguyên.**
