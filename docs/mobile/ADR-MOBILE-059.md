# ADR-MOBILE-059 — `getUserCompetencies` (`imm06.get_user_competencies`) curate vào OAS mirror (**CR-34 · MỞ NHÁNH IMM-06 (Đào tạo & Năng lực)** — bồi ĐÚNG 1 GET-read path trả HỒ SƠ NĂNG LỰC của 1 nhân viên (`{user, items[]}`) cho màn "Năng lực của tôi"; **module IMM-06 LẦN ĐẦU vào mirror** (0 endpoint imm06 hiện có) + **tag `training` MỚI** (15th) + **schema-family `UserCompetenc*` MỚI**; **CONTRACT-ONLY** — backend LIVE `@api/imm06.py:189` + service `@services/imm06.py:1527`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-059 |
| Phase | C — API contract (codegen-ready) — CONTRACT-ONLY (0 `.py` runtime) |
| Ngày | 2026-07-15 |
| Tác giả | BA (spec + curate YAML + guard test) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; `200`-oneOf KHÔNG discriminator) · **precedent flat-object read inline-oneOf 3-tầng Envelope→Data→Item ∈ `_MVP_READ_ENVELOPE`**: **ADR-MOBILE-056/057/058** (`getPmDashboardStats`/`getCalibrationKpis`/`getRepairKpis`) · **precedent typed query-param**: CR-05 · **precedent Check-quirk chiều READ (`is_expired` integer enum[0,1])**: CR-01 · **precedent module-tag MỚI khi mở module** (`commissioning` IMM-04 / `inventory` IMM-15 / `compliance` IMM-16) · **domain SoT**: Core Doc IMM-06 [`../imm-06/05_API_Specification.md`](../imm-06/05_API_Specification.md) §III Group C (C.2 `get_user_competencies`) + `04_Backend_Design.md` §V.1 (compute expiry/is_expired) + BR-06-15/16 |

---

## 1. Bối cảnh

Màn **"Năng lực của tôi"** (self-service, IMM-06) trên mobile hiển thị **danh sách hồ sơ năng lực** của nhân viên đang đăng nhập (KTV/operator xem chứng nhận thiết bị của mình; supervisor tra của người khác qua `?user=`): mỗi dòng = 1 (user × device_model × training_program) với cấp năng lực, trạng thái vòng đời, ngày đạt/hết hạn, số ngày còn lại (âm = quá hạn), cờ đã-hết-hạn, điểm đánh giá gần nhất.

Endpoint `get_user_competencies` **ĐÃ LIVE** @web-BE (KHÔNG build `.py` mới) ⇒ round này **CONTRACT-ONLY**: curate 1 path + 3 schema + 1 tag MỚI vào mirror, **0** `.py`/reload/migrate. Đây là **endpoint IMM-06 ĐẦU TIÊN** trong mirror (0 endpoint imm06 hiện có) ⇒ mở tag domain `training` MỚI (15th) + schema-family `UserCompetenc*` MỚI (đối-xứng cách IMM-04 mở `commissioning`, IMM-15 mở `inventory`, IMM-16 mở `compliance`).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler @`api/imm06.py:188-191` = bare `@frappe.whitelist()` (KHÔNG `allow_guest`, KHÔNG `rbac.require`), gọi wrapper `_run`:
  ```python
  @frappe.whitelist()
  def get_user_competencies(user: str = "") -> dict:
      """GET /api/method/assetcore.api.imm06.get_user_competencies"""
      return _run(svc.get_user_competencies, user or frappe.session.user)
  ```
- `_run` @`api/imm06.py:34-42` = wrapper envelope chuẩn: `_guard()` (Guest → `ServiceError(UNAUTHORIZED)`) → `_ok(fn(...))` / `except ServiceError → _err(...)` / `except Exception → _err("Lỗi server", INTERNAL)`. **⇒ handler CÓ nhánh `_err`** (KHÔNG bare single-shape) ⇒ **200 = oneOf [Envelope, Error]** Decision-B (giải quyết câu hỏi acceptance "route-by-value nếu handler có nhánh `_err`").
- `_ok(data)` @`utils/response.py:79-93` = **`{"success": True, "data": data}`** — envelope 2-tầng. `_err(...)` @`:95` = `{"success": False, "error", "code", "http_status", ...}`.
- Service `get_user_competencies(user)` @`services/imm06.py:1527-1546` return-dict VERBATIM:
  ```python
  target_user = user or frappe.session.user
  rows, _ = UserCompetencyRepo.list(
      filters={"user": target_user},
      fields=["name", "device_model", "training_program", "competency_level",
              "workflow_state", "achieved_date", "expiry_date",
              "days_until_expiry", "is_expired", "last_assessment_score"],
      order_by="expiry_date asc", page_size=500)
  return {"user": target_user, "items": rows}       # :1546
  ```
  ⇒ payload `_ok`-wrap = `{"success": true, "data": {"user": <str>, "items": [<10-field row>...]}}`.
- Kiểu 10 field grounded @doctype `imm_user_competency.json` + compute @`services/imm06.py:1018-1044`:
  - `name` Data (docname, always) · `device_model` Link→IMM Device Model (RAW id, nullable) · `training_program` Link→IMM Training Program (RAW id, nullable) · `competency_level` **Select** `Trainee\nOperator\nSenior Operator\nTrainer` (no-default → nullable) · `workflow_state` Link→Workflow State (canonical từ **workflow JSON**, KHÔNG Select) · `achieved_date`/`expiry_date` Date (nullable) · `days_until_expiry` Int `date_diff(expiry, today)` (SIGNED — âm=quá hạn; NOT-NULL default 0 khi expiry chưa compute @`:1043`) · `is_expired` **Check** `1 if diff<0 else 0` (int 0/1 chiều READ @`:1044`, NOT-NULL) · `last_assessment_score` Float (no-default → nullable).
  - `workflow_state` canonical = 6 state @`imm_06_competency_workflow.json`: `[Pending Assessment, Active, Expiring, Expired, Suspended, Revoked]` (SoT là **workflow JSON** — acceptance ghi "enum theo Select" là gần-đúng: field là Link→Workflow State, enum lấy từ định-nghĩa workflow).

---

## 2. Quyết định

### (a) 200 = **inline `oneOf [UserCompetenciesEnvelope, Error]`** (Decision-B, 0 discriminator) — 3-tầng Envelope→Data→Item

`data` = **`UserCompetenciesData` OBJECT PHẲNG** `{user, items[]}` — KHÔNG pagination, KHÔNG list-envelope (mảng `items` nhúng trong object phẳng, giống `RepairKpisData.root_cause_breakdown[]` ADR-058 §2(b)). Route 2 nhánh MÁY-ĐỌC bằng CLOSED-SCHEMA + disjoint required-set (`UserCompetenciesEnvelope` `req[success,data]` vs `Error` `req[success,error,code,http_status]`), theo `body.success` — mirror bộ-ba Dashboard-KPI. Vào **`_MVP_READ_ENVELOPE`** (inline oneOf, KHÔNG response-component); **∉ `_MVP_LIST_ENVELOPE`** (flat-object read, KHÔNG paginated `data.data[]`/`data.items[]` + `total_count`/`page` — `page_size=500` chốt-cứng @`:1544`, 0 param page ⇒ GIỮ 13). **Invariant `count==rows` KHÔNG áp** — 0 endpoint count-đối-ứng (self-scope 1 user).

> **⚠️ SELF-CORRECTION vs acceptance đề-mục (BA chốt — Core Doc là quyết định cuối):** Đề-mục CR-34 khai **2 schema** — `UserCompetencyListItem` + `UserCompetenciesResponse ({user, items})` là **oneOf-member TRỰC-TIẾP** của 200 (closed-count 203→205). **SAI-nguồn**: handler wrap qua `_ok` @`utils/response.py:81` ⇒ wire THẬT = `{success:true, data:{user, items}}` — **KHÔNG** `{user, items}` trần. Khai `{user, items}` làm oneOf-member = contract nói sai bytes-on-wire (thiếu tầng `{success, data}`). **100% precedent read** (`_MVP_READ_ENVELOPE`: `QrResolveEnvelope`/`AssetDetailEnvelope`/`PmWorkOrderDetailEnvelope`/…/`RepairKpisEnvelope`) model FULL envelope qua schema `*Envelope`. ⇒ **CHỐT 3 schema** (`*ListItem` + `*Data` + `*Envelope`), 200 = oneOf [`UserCompetenciesEnvelope`, Error]. `UserCompetenciesData` = đúng cái đề-mục gọi "UserCompetenciesResponse" (đổi tên → `*Data` cho đồng-nhất family Pm/Cal/Repair). **closed-count += 3** (KHÔNG +2) — baseline "203" ở đề-mục **STALE** (live grep `additionalProperties:false` ≈ 213 sau CR-31a/b/c); BE **re-derive @source TRƯỚC bump**.

### (b) 3 schema CLOSED (`additionalProperties:false`) — VERBATIM return-dict, 0 invention

- **`UserCompetencyListItem`** — EXACT **10 prop** = 10 field select @`services/imm06.py:1539-1541`; `required` = **CẢ 10** (mọi key always-emit — `get_all` trả đủ mọi field select, null khi rỗng). Kiểu:
  - `name` `type:string` (docname) — non-null.
  - `workflow_state` `type:string`, `enum:[Pending Assessment, Active, Expiring, Expired, Suspended, Revoked]` — non-null (workflow luôn set state).
  - `days_until_expiry` `type:integer` **SIGNED** (âm=quá hạn @`:1043`) — non-null (Int default 0).
  - `is_expired` `type:integer`, `enum:[0, 1]` (**Check-quirk chiều READ** — int 0/1 KHÔNG boolean; precedent CR-01) — non-null.
  - `device_model` `type:string`, `nullable:true` (Link RAW id — enrich `device_model_name` DEFERRED, xem §2(d)).
  - `training_program` `type:string`, `nullable:true` (Link RAW id).
  - `competency_level` `type:string`, `enum:[Trainee, Operator, Senior Operator, Trainer]`, `nullable:true` (Select no-default — pre-assessment có thể rỗng; BE: nếu validator strict → thêm `null` vào enum).
  - `achieved_date` `type:string`, `format:date`, `nullable:true`.
  - `expiry_date` `type:string`, `format:date`, `nullable:true`.
  - `last_assessment_score` `type:number`, `nullable:true` (Float no-default).
- **`UserCompetenciesData`** — `{user: string (non-null), items: array<UserCompetencyListItem>}`, `required:[user, items]`. `items` **RỖNG hợp-lệ** khi user 0 năng lực (array always-emit ⇒ ∈ required).
- **`UserCompetenciesEnvelope`** — `{success:{type:boolean, enum:[true]}, data:$ref UserCompetenciesData}`, `required:[success, data]`.

### (c) operationId `getUserCompetencies` (DOMAIN), **tag `training` MỚI (15th)** + typed param `user`

- **tag `training`** = **module-domain tag MỚI** (chưa thuộc 14 tag hiện có: `work-order`/`asset`/`incident`/`calibration`/`notification`/`pm`/`auth`/`user`/`commissioning`/`account`/`repair`/`push`/`inventory`/`compliance`). Precedent mở module → mở tag: IMM-04→`commissioning`, IMM-15→`inventory`, IMM-16→`compliance`. IMM-06 = Đào tạo & Năng lực ⇒ `training`.
- **1 typed query-param `user`** (`in:query`, `required:false`, `type:string`) — precedent CR-05 typed-query. **KHÔNG khai `default:` YAML** — backend default ĐỘNG `frappe.session.user` (`user or frappe.session.user` @`api/imm06.py:190`), KHÔNG hằng ⇒ static-default drift. Signature `get_user_competencies(user: str = "")` @`:189` — annotation `str`, default `""` (empty-string) ⇒ `type:string` + `required:false`. **KHÔNG requestBody** (GET-read).
- naming-guard: family `UserCompetenc*` (= `UserCompetencyListItem` ∪ `UserCompetenciesData` ∪ `UserCompetenciesEnvelope`, ĐÚNG 3) ∩ existing schemas == ∅ (grep-verify; KHÔNG đụng `Competency`-prefix khác vì chưa có).

### (d) enrich `device_model_name` **CỐ Ý DEFERRED** (follow-on — backend change + reload = HARD-STOP)

`device_model` khai `type:string` = **Link id RAW** (vd `MDL-MON-PHILIPS-X3`), KHÔNG kèm `device_model_name` display. Service `get_user_competencies` @`:1527` **KHÔNG** enrich display-name (khác `get_competency` @`:1584` CÓ `device_model_name`/`user_full_name`). Thêm `device_model_name` = **sửa `.py`** (thêm field enrich vào return-dict) ⇒ gunicorn `--preload` reload = **HARD-STOP USER** (memory `gunicorn_preload_staleness`) ⇒ vi phạm CONTRACT-ONLY. ⇒ **DEFERRED sang follow-on round** (backend enrich + reload + curate `device_model_name` `type:string, nullable:true` vào `UserCompetencyListItem` = 11 prop). Round này FE tự resolve name từ id (hoặc để id) — LL-FE-6 (không leak id) áp ở follow-on, KHÔNG round contract-only này.

### (e) 403 = SINGLE-SHAPE `Forbidden` **dispatcher-ONLY** (bare `@whitelist`, 0 cap-403 in-handler)

Handler bare `@frappe.whitelist()` @`:188` KHÔNG `allow_guest` ⇒ guest/no-token trip **dispatcher-403** (`PermissionError`, HTTP-403 status-line) TRƯỚC `_run`; bearer-expired → **401**. **0 `rbac.require` in-handler** ⇒ KHÔNG cap-403 reachable ⇒ 403-slot SINGLE `Forbidden` (mirror `getRepairKpis`/`getPmDashboardStats`, KHÁC `closeWorkOrder` cap-REACHABLE). **ĐỐI XỨNG A16**: path ∈ `_MVP_BUSINESS_PATHS` ⇒ `_PATHS_REQUIRE_401` ∧ `_PATHS_REQUIRE_403` tự +1 (401==403 GIỮ). status-set `[200, 401, 403]`. *(Lưu-ý `_guard()` trong `_run` raise `UNAUTHORIZED` cho Guest đến TRÊN HTTP-200 body `Error` — belt-and-suspenders; dispatcher-403 fire TRƯỚC cho bare-whitelist no-allow_guest ⇒ guest thực-tế = 403 status-line, KHÔNG 200. Contract khai 401/403 dispatcher, KHÔNG bịa 200-guest.)*

> **🔓 OPEN — authz cross-user (follow-on, KHÔNG chặn contract-only):** `?user=<người-khác>` trả năng lực người khác cho MỌI caller authenticated (`UserCompetencyRepo.list` filter `{user}` — KHÔNG `rbac.require`, KHÔNG kiểm `user==session.user ∨ supervisor`). Doc C.2 CŨ ghi "nếu user param != session.user → cần `_SIGNOFF_ROLES`" là **aspirational/stale** (handler LIVE KHÔNG enforce). Contract vòng này khai **AS-IS TRUTHFUL** (KHÔNG bịa 403 cross-user không tồn tại). Flag `T-IMM06-AUTHZ` cho BA/BE review: có nên gate cross-user? = **backend change** (HARD-STOP reload) ⇒ follow-on, KHÔNG round này.

### (f) CONTRACT-ONLY — 0 `.py`/reload/migrate

`get_user_competencies` + service **ĐÃ LIVE** @source ⇒ `git diff` round này = CHỈ `docs/mobile/*` (yaml + ADR-059 + 04-api-contract §8.53) + `docs/imm-06/*` (Core Doc binding — fix C.2 stale + cross-ref) + `assetcore/tests/test_mobile_oas.py` + `assetcore/tests/test_mobile_docset.py` (guard). **0** file `.py` runtime, **0** gunicorn reload (KHÔNG HARD-STOP — `[AUTO]`), **0** `bench migrate`, **0** git commit (working-tree để USER review).

---

## 3. Guard test (`test_mobile_oas.py` — class RIÊNG `TestMobileGetUserCompetenciesContract`, **7 TC a..g**)

Skeleton acceptance là 6 TC (a..f); **+1 TC** (→ 7) do SELF-CORRECTION envelope (schema `*Envelope` tách khỏi `*Data` — TC-g). Map:

- **a** — path `/api/method/assetcore.api.imm06.get_user_competencies` tồn tại + CHỈ GET + opId `getUserCompetencies` camelCase UNIQUE; path/opId-count == **90** (89→90).
- **b** — 3 schema CLOSED (`additionalProperties:false`): `UserCompetencyListItem` + `UserCompetenciesData` + `UserCompetenciesEnvelope`. *(acceptance ghi 2 → CORRECTED 3, §2(a).)*
- **c** — `UserCompetencyListItem` prop-set == ĐÚNG 10 (`SET==`) {name, device_model, training_program, competency_level, workflow_state, achieved_date, expiry_date, days_until_expiry, is_expired, last_assessment_score}; `required` == cả 10; kiểu đúng: 4 non-null (name/workflow_state/days_until_expiry/is_expired) + 6 `nullable:true` (device_model/training_program/competency_level/achieved_date/expiry_date/last_assessment_score); `achieved_date`/`expiry_date` `format:date`.
- **d** — `is_expired` `type:integer` `enum:[0,1]` (KHÔNG boolean) ∧ `days_until_expiry` `type:integer` (KHÔNG format/nullable) ∧ `competency_level` `enum:[Trainee,Operator,Senior Operator,Trainer]` ∧ `workflow_state` `enum:[Pending Assessment,Active,Expiring,Expired,Suspended,Revoked]` (6 state — grounded workflow JSON).
- **e** — ĐÚNG 1 query-param `user` (`in:query`, `type:string`, `required:false`, **KHÔNG `default`**); KHÔNG requestBody; **live-introspect parity** `inspect.signature(imm06.get_user_competencies).parameters=={'user'}` ∧ `default == ""` (empty-string).
- **f** — tag `[training]` (tag MỚI 15th — assert KHÔNG ∈ 14 tag cũ; distinct-tag-set trước = 14).
- **g** *(SELF-CORRECTION +1)* — 200 inline oneOf ĐÚNG 2 `[UserCompetenciesEnvelope, Error]` 0-discriminator (success enum disjoint `[true]`/`[false]`); `UserCompetenciesData` CLOSED `required:[user,items]` (`user` string, `items` `type:array` items `$ref UserCompetencyListItem`); `UserCompetenciesEnvelope` CLOSED `required:[success,data]` (`success.enum==[true]`, `data.$ref`==UserCompetenciesData); ∈ `_MVP_BUSINESS_PATHS` ∧ `_PATHS_REQUIRE_401` ∧ `_PATHS_REQUIRE_403` ∧ `_MVP_READ_ENVELOPE`; ∉ `_MVP_LIST_ENVELOPE`; slot `{200,401,403}` (401 `Unauthorized401` + 403 `Forbidden` SINGLE); naming-guard `UserCompetenc*` ĐÚNG 3 ∩ existing == ∅ + 0 dangling $ref.

### Bulk-bump bookkeeping (reconcile — ⚠️ grep-verify @source TRƯỚC bump; đa-phiên race memory `multi_session_concurrency`)

Baseline grounded @source 2026-07-15 **sau CR-31c/ADR-058** — BE **grep-verify từng literal @source ngay trước bump** (phiên khác có thể đã dời):

- `_EXPECTED_TEST_COUNT` 811 → **818** (+7); `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 811 → **818**.
- cross-file `test_mobile_docset.py`: `_GUARD_SUITE_SUM` 954 → **961**; `_MOBILE_OAS_TOTAL` 980 → **987**; delta var `user_competencies_delta = 7` mới (+ trừ trong chuỗi `pre_fc3_six` nếu six-module-sum SSoT chạm — GIỮ bất biến).
- path/opId-count 89 → **90** (bump MỌI literal count-assertion: `len(paths)/len(ids)/len(set(ids))/len(ops)` + snapshot backward-compat opId-diff +1) — grep `== 89` @source.
- `c5` / `_PARITY_BUSINESS_PATHS` 78 → **79** (401/403 symmetry +1 do ∈ `_MVP_BUSINESS_PATHS`).
- `_MVP_READ_ENVELOPE` += `{get_user_competencies_path: '#/components/schemas/UserCompetenciesEnvelope'}` (+1); `_MVP_LIST_ENVELOPE` **GIỮ 13**.
- `_EXPECTED` += `{'/api/method/assetcore.api.imm06.get_user_competencies': ('get', 'getUserCompetencies')}` (line 219 map).
- `_MVP_BUSINESS_PATHS` (line 2250 tuple) += path get_user_competencies (comment nêu read-envelope + tag training + {200,401,403}).
- **closed-schema count += 3** (NOT +2; live baseline re-derive @source — grep `additionalProperties: false` ≈ 213 → ≈ 216; đề-mục "203→205" STALE).
- distinct operation-tag 14 → **15** (thêm `training`) — nếu có guard đếm distinct tag @docset; nếu KHÔNG (chỉ per-op assert) → bỏ qua.

**SSoT:** `api/imm06.py:188` (`_run` wrapper) + `services/imm06.py:1527-1546` (return-dict `{user, items}`) + `utils/response.py:79` (`_ok`→`{success,data}`) + `imm_user_competency.json` (10-field type) + `imm_06_competency_workflow.json` (6 workflow_state canonical).

---

## 4. Hệ quả

- **+**: màn "Năng lực của tôi" codegen-ready (typed model `UserCompetenciesData`/`UserCompetencyListItem`); FE mobile bind list-năng-lực theo **server-flag** (`is_expired` int 0/1 + `days_until_expiry` signed — KHÔNG re-derive client-clock, memory `overdue_server_flag_ssot`).
- **+**: **MỞ NHÁNH IMM-06** (endpoint đầu) + tag `training` (15th) + family `UserCompetenc*` — hạ tầng cho follow-on IMM-06 (`getCompetency`/`listCompetencies`/CTA sign-off/revoke…).
- **+**: false-green chặn bằng live-signature parity (`{user}` default `""`) + no-orphan + 10-field VERBATIM `SET==` + `is_expired` int-enum guard (KHÔNG boolean) + envelope-3-tầng closed.
- **−/đánh đổi**: `device_model` = id RAW (enrich `device_model_name` DEFERRED §2(d) — backend+reload); authz cross-user AS-IS (flag `T-IMM06-AUTHZ` §2(e)). Cả 2 = follow-on có-chủ-đích, KHÔNG round này. Đổi sau = 1 ADR mới Supersede (KHÔNG xoá 059).
- **KHÔNG** đổi workflow / DocType / migrate / reload (CONTRACT-ONLY, backend LIVE). Working-tree để USER review — KHÔNG git commit/push.

### Alternatives loại

| Phương án | Lý do loại |
|---|---|
| `UserCompetenciesResponse = {user, items}` làm oneOf-member 200 TRỰC-TIẾP (đề-mục CR-34, 2 schema) | Wire THẬT = `{success:true, data:{user,items}}` qua `_ok` @`response.py:81` — bare `{user,items}` nói sai bytes; 100% precedent read = `*Envelope`. ⇒ 3 schema (`*ListItem`+`*Data`+`*Envelope`), §2(a). |
| closed-count 203 → 205 (+2) | Baseline 203 STALE (live ≈213 sau CR-31a/b/c); +3 schema. Re-derive @source. |
| enrich `device_model_name` ngay vòng này (11 prop) | Sửa `.py` return-dict ⇒ gunicorn reload HARD-STOP USER — vi phạm CONTRACT-ONLY. DEFERRED §2(d). |
| `is_expired` `type:boolean` | Check field chiều READ = int 0/1 (precedent CR-01) — boolean = SAI-nguồn codegen. |
| `days_until_expiry` `nullable:true` | Int NOT-NULL default 0 @Frappe (@`:1043` chỉ set khi expiry có, else DB-default 0) — non-null integer signed. |
| `competency_level`/`workflow_state` `type:string` TRẦN (không enum) | Select/workflow canonical → codegen `String` free-form; formal-hoá enum (grounded doctype Select + workflow JSON) như CR-08 enum-parity. |
| `workflow_state` enum lấy từ "Select doctype" (như acceptance) | Field là **Link→Workflow State**, KHÔNG Select; canonical = 6 state @`imm_06_competency_workflow.json` (SoT workflow). |
| coi endpoint là list (∈ `_MVP_LIST_ENVELOPE`, paginated) | `page_size=500` chốt-cứng, 0 param page/total_count, shape `{user, items}` object phẳng — read-envelope ∉ list (mirror `RepairKpisData` embedded array). |
| tag `user`/`asset` (reuse) hoặc `dashboard` MỚI | Domain = Đào tạo & Năng lực (IMM-06) ⇒ tag module `training` (precedent mở-module IMM-04/15/16); `user`=account, KHÔNG khớp. |
| khai `default: <session.user>` YAML cho param `user` | Default backend ĐỘNG `frappe.session.user` @`:190` — static-default drift. |
| gate 403 cross-user trong contract | Handler LIVE KHÔNG enforce (0 `rbac.require`) — bịa 403 = contract sai-nguồn; AS-IS truthful + flag follow-on §2(e). |
| status-line 404/4xx | Decision-B — lỗi TRÊN HTTP-200 body Error (`_run` `_err`). |

**Accepted.**
