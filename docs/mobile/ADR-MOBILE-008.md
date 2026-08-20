# ADR-MOBILE-008 — Session-bootstrap contract (`getUserContext`): `allow_guest` ⇒ slot {200,401} exempt 401/403 symmetry + INT-VS-BOOL flag contract

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-008 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-16 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | Decision-B (closed-schema oneOf, KHÔNG discriminator) · C7 (200 oneOf [Env, Error] read-path) · A16 (tách 401 expired-bearer vs 403 guest/no-token/thiếu-cap) · C4 (`openid_profile`/`getUserInfo` status-set {200,401} exempt symmetry) · Open#1 (Check-field → `integer enum[0,1]`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/layout.py`). Contract: [`04-api-contract.md §8.19`](./04-api-contract.md). Guard: `assetcore/tests/guards/test_mobile_oas.py::TestMobileGetUserContextContract`.

---

## Context

Vòng 29 bồi path `getUserContext` (`GET /api/method/assetcore.api.layout.get_user_context`, opId `getUserContext`) vào contract mobile — đây là **FLOW-1 BOOTSTRAP** (session who-am-I) ĐẦU TIÊN. **Vấn đề nghiệp vụ:** app home sau login hiện **hardcode "Đã đăng nhập" KHÔNG identity** — session FE chỉ giữ `{email, fullName}` parse từ login-response, KHÔNG có roles/department/persona/profile-completeness. Để render **persona-aware home** + **flow-gating** (ẩn/hiện tính năng theo role; ép hoàn-thiện-profile nếu thiếu khoa-phòng/chức-danh) app cần 1 GET-read "ai-đang-đăng-nhập". Endpoint LIVE whitelisted @`layout.py:188` trả ĐỦ identity (13 field) — CHƯA vòng nào (1-28) bồi.

Handler @`api/layout.py:187-234` có **2 đặc tính khác mọi path MVP-business đã bồi** (createPm/report/list/action), cần quyết định hợp đồng:

1. **`allow_guest=True`** (`api/layout.py:187`). KHÁC 12 path MVP-business (`@whitelist` bearer-gated → Frappe dispatcher chặn Guest/no-token bằng `PermissionError` **403** `is_whitelisted __init__.py:876` TRƯỚC handler). Ở đây Guest **VÀO handler** → handler tự guard `frappe.session.user=='Guest'` → `_err 401` (`api/layout.py:206-207`, body **Error-on-HTTP-200**). ⇒ path này **KHÔNG có dispatcher-403** và KHÔNG có business-403 (read-only identity của chính session). Response slot THẬT = **`{200, 401}` ONLY**.

2. **2 boolean field trong `_ok` payload.** `is_profile_completed` (`bool(department and designation)` `:218`/`:232`) + `has_employee_link` (`emp.get("has_employee_link", False)` `:233`) BE emit **`bool()` Python** (`true`/`false`).

Ràng buộc guard hiện hữu (A16, `test_mob_oas_12`): **mọi path declare 401 (trừ `_AUTH_PATHS`) PHẢI ∈ `_PATHS_REQUIRE_403`** (đối-xứng 401==403 cho MVP-business). Nếu bồi `getUserContext` với slot 401 nhưng KHÔNG 403 mà KHÔNG xử-lý, guard symmetry **VỠ**.

## Decision

**(1) Response slot = `{200, 401}` ONLY — KHÔNG bịa 403.** Source THẬT (`allow_guest=True`, KHÔNG cap-gate, KHÔNG business-403) chỉ phát 200 (đăng nhập) hoặc 401 (Guest in-handler). Thêm slot 403 vào contract = **bịa hợp đồng** (G-OAS rule: KHÔNG khai status BE không phát). 401 = `Unauthorized401` (`$ref FrappeRawError`, **SINGLE-SHAPE uniform** 37-path convention) — dùng component dù body runtime là in-handler Error-on-HTTP-200; mirror `listIncidents`/`getAssetIncidentHistory` (KHÔNG drift sang shape riêng). Prose giải-thích WHY có slot 401 (guest-guard) NHƯNG shape theo convention uniform.

**(2) `allow_guest` path exempt 401/403 MVP-business symmetry qua tập `_ALLOW_GUEST_PATHS`.** Đưa `getUserContext` vào tập exemption MỚI `_ALLOW_GUEST_PATHS` (song song `_AUTH_PATHS`); 2 filter symmetry trong `test_mob_oas_12` (và mọi guard per-path) đổi `p not in _AUTH_PATHS` → `p not in (_AUTH_PATHS | _ALLOW_GUEST_PATHS)`. ⇒ `getUserContext` (declare 401, KHÔNG 403) bị **loại khỏi tập so-sánh** ⇒ symmetry 401==403 của MVP-business **GIỮ đối-xứng**. **MIRROR `openid_profile`/`getUserInfo` (C4)**: cùng status-set `{200,401}` exempt symmetry — NHƯNG `openid_profile` là **Frappe-core oauth** (vào `_AUTH_PATHS`) còn `getUserContext` là **AssetCore-handler** (vào `_ALLOW_GUEST_PATHS` riêng, KHÔNG nhồi `_AUTH_PATHS` vì KHÔNG phải oauth-flow). Khi bồi `allow_guest` path kế → THÊM vào `_ALLOW_GUEST_PATHS`.

**(3) `getUserContext` NOT ∈ `_MVP_BUSINESS_PATHS` / `_MVP_READ_ENVELOPE` / C5-registry.** Đây là **bootstrap/session path** (allow_guest, no vendor-scope, no cap-gate, no audit) ⇒ KHÔNG phải "MVP-business path". (a) Đưa vào `_MVP_BUSINESS_PATHS` sẽ ép 403 symmetry (vỡ — không có 403). (b) Đưa vào `_MVP_READ_ENVELOPE` sẽ phá invariant `C5 == _MVP_BUSINESS_PATHS` (`test_mob_oas_23a`, vì C5-union được assert bằng `_MVP_BUSINESS_PATHS`). Typed-200 oneOf `[UserContextEnvelope, Error]` phủ **độc lập** bởi guard riêng `test_mob_oas_userctx_c`. Đây là **ranh-giới scope rõ ràng** — KHÔNG là thiếu-sót coverage.

**(4) `UserContextData` closed EXACT 13 prop + `required[user]` graceful-degradation.** `additionalProperties:false`, 13 prop GROUNDED `_ok` payload `layout.py:220-234`. Chỉ `user` REQUIRED (LUÔN có khi 200 = `frappe.session.user`); 6 string-field nullable + 2 array `[]` (graceful-degradation: AC User custom-field/Employee có thể vắng — `db.get_value` KHÔNG `get_doc`, trả null KHÔNG throw `:195-204`). `roles`/`imm_roles` = `array items.type:string` (`frappe.get_roles` list, KHÔNG enum cứng — role-set động). 200 = oneOf `[UserContextEnvelope, Error]` closed-schema route-by-VALUE `body.success` (C7, 0 discriminator; mirror `getAssetScanInfo`).

**(5) INT-VS-BOOL TRAP: 2 flag = `integer enum[0,1]` (KHÔNG `type:boolean`) dù BE emit `bool()`.** `is_profile_completed` + `has_employee_link` khai `integer enum[0,1]` để **codegen strict-deser (Dart/Kotlin) nhất quán int-or-bool** toàn contract: nhiều Check-field khác đã là `integer enum[0,1]` (Frappe Check→int 0/1 — vd `IncidentListItem.rca_required`/`chronic_failure_flag`/`patient_affected` §6.3). Giữ 2 flag này `boolean` = **bất nhất** trong contract ⇒ client phải xử-lý 2 kiểu cho cùng-nghĩa cờ. BE emit `true`/`false` (JSON bool) NHƯNG `integer enum[0,1]` deser được `true→1`/`false→0` ở client coerce-layer (Decision-B coerce mềm). Guard `test_mob_oas_userctx_f` chống regress (assert `type:integer` + `enum[0,1]`, KHÔNG `boolean`).

## Consequences

- **Codegen mobile** sinh `getUserContext()` 0-arg (KHÔNG param/body) trả `UserContextEnvelope | Error`. Client route theo `body.success`; nhận 401 (Guest/expired) → refresh token → fail → re-auth (mirror `listIncidents` flow). App home gọi ngay sau login → hydrate persona (`roles`/`imm_roles`/`role_profile_name`) + gate onboarding (`is_profile_completed==1?`).
- **Symmetry 401/403 MVP-business BẤT BIẾN** (12 path declare 401 == 12 path declare 403, trừ `_AUTH_PATHS` ∪ `_ALLOW_GUEST_PATHS`). `getUserContext` + `openid_profile` cùng exempt — KHÔNG vào tập so-sánh.
- **Path/opId count 36→37**; `_EXPECTED_TEST_COUNT 337→346` (+9 TC `TestMobileGetUserContextContract` a..i); docset reconcile `_GUARD_SUITE_SUM 480→489` + `_MOBILE_OAS_TOTAL 506→515`.
- **PURE-YAML**: 0 đụng `api/layout.py` + services (handler + 3 helper LIVE whitelisted, sig nguyên). KHÔNG reload/migrate/commit.

## Alternatives bác

1. **Thêm slot 403 cho `getUserContext` (vào `_MVP_BUSINESS_PATHS`) để khớp symmetry sẵn.** → BÁC: `allow_guest=True` ⇒ KHÔNG dispatcher-403; khai 403 = bịa status BE không phát (G-OAS). Coi nó "business path" sai bản-chất (no cap-gate/vendor-scope/audit).
2. **Nhồi `getUserContext` vào `_AUTH_PATHS` (tái dùng exemption sẵn).** → BÁC: `_AUTH_PATHS` = oauth2.* Frappe-core flow (authorize/get_token/revoke/openid_profile) — dùng cho `_AUTH_EXPECTED_STATUS` map + 429-auth-check. `getUserContext` là AssetCore-handler, KHÔNG oauth-flow ⇒ nhồi vào sẽ làm bẩn ngữ-nghĩa `_AUTH_PATHS` + lọt vào các check auth-specific. Tập `_ALLOW_GUEST_PATHS` RIÊNG = ngữ-nghĩa đúng (AssetCore allow_guest handler).
3. **Khai 2 flag `type:boolean` (khớp 1:1 BE emit).** → BÁC: bất nhất với phần còn lại của contract (Check-field = `integer enum[0,1]`); buộc codegen sinh 2 deser-path cho cùng-nghĩa cờ ⇒ rủi-ro strict-deser crash khi BE/codegen lệch kiểu.
4. **`additionalProperties:true` cho `UserContextData` (forward-compat thêm field).** → BÁC: phá disjoint-required-set với `Error` trong 200-oneOf (route-by-VALUE cần closed-schema 2 nhánh, Decision-B/C7). 13 prop GROUNDED `_ok` payload là tập đóng @source.
