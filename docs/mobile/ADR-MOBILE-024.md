# ADR-MOBILE-024 — Account/Profile (`getMyProfile` / `updateMyProfile` / `changeMyPassword`) — curate 3 endpoint màn "Tài khoản" (mobile.v1 / IMM-00 auth-profile) vào mobile contract + đóng CR-20

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-024 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-11 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator) · **device-token (EPIC-D D4)** (mobile.v1 self-service bearer-gated: slot `{200,401,403}`, ∉ `_MVP_BUSINESS_PATHS`/c5, re-export path-resolvability) · Core Doc IMM-00 [`04_Backend_Design.md`](../imm-00/04_Backend_Design.md) + [`05_API_Specification.md`](../imm-00/05_API_Specification.md) · [`03-auth-oauth2.md`](./03-auth-oauth2.md) (self-service profile) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/mobile/v1/profile.py:78-181`, `assetcore/api/mobile/v1/__init__.py`, `assetcore/api/auth.py:24,310`, `assetcore/api/user.py` (`change_my_password`), `assetcore/utils/response.py` (`_ok`/`_err`/`ErrorCode`), `assetcore/tests/guards/test_mobile_oas.py`, `assetcore/tests/guards/test_mobile_docset.py`). Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§8.30 Account/Profile).

---

## Context

App mobile field-tech có màn **"Tài khoản"** (self-service hồ sơ + đổi mật khẩu) — 3 hành động: (1) xem hồ sơ của chính mình, (2) sửa họ tên / số điện thoại, (3) đổi mật khẩu. 3 endpoint THIN wrapper **ĐÃ LIVE** trong `assetcore/api/mobile/v1/profile.py` (viết vòng trước, re-export ở `mobile/v1/__init__.py`) nhưng **CHƯA có trong OAS mirror** → codegen client mobile không sinh được method. Đây là hạng mục còn treo trong **CR-20** (Account/Profile contract sync). Vòng này **curate 3 path** vào `assetcore-mobile.openapi.yaml` + đóng closed-schema, giữ contract-test xanh — **CONTRACT-ONLY**: KHÔNG đụng `.py` (profile.py + __init__.py đã LIVE) ⇒ KHÔNG reload gunicorn, KHÔNG migrate.

**Cơ-chế hiện hữu (đã VERIFY @source):**

### `profile.py` — THIN wrapper DELEGATE (KHÔNG reimplement business rule)
- `get_my_profile()` `@frappe.whitelist()` @`:89-101` — **bare** (KHÔNG `allow_guest`), **0 param** (user ÉP `frappe.session.user`). DELEGATE `auth.get_user_profile()` rồi project GỌN `_build_my_profile` @`:78-86`. Trả `_ok(MyProfile 7-key)`.
- `update_my_profile(full_name="", phone="", **_ignore)` `@frappe.whitelist(methods=["POST"])` @`:104-132`. DELEGATE `auth.update_my_profile()` (đọc `form_dict`, allowlist `_SELF_EDITABLE={full_name, phone}` @`api/auth.py:24,310`). Thành công → re-project `MyProfile` ĐẦY ĐỦ (Q-C). Lỗi validate → `_err(VALIDATION, fields=...)` HTTP-200.
- `change_my_password(old_password="", new_password="", **_ignore)` `@frappe.whitelist(methods=["POST"])` @`:149-181`. DELEGATE `user.change_my_password` (verify cũ / len≥8 / chặn old==new / `update_password`). Thành công → `_ok({reauth_required: False})` @`:173`. Lỗi → `_err(VALIDATION, fields={old_password|new_password})`.

### `_build_my_profile` (`profile.py:78-86`) — payload SSoT
Trả **EXACT 7 key** (VERBATIM): `full_name`, `email`, `phone` (nullable), `roles[]`, `role_labels[]`, `department` (nullable), `department_name` (nullable). LOẠI mọi field web-only (`permissions`/`hr_docname`/`imm_approval_status`/`designation`/`user_image`/khối `profile` lồng).

### Envelope + Error (`utils/response.py`)
`_ok(data)` → `{success:true, data}`; `_err(msg, code, fields)` → `{success:false, error, code, http_status, ...}`. Decision-B (§ADR-MOBILE-001): lỗi nghiệp vụ trả **HTTP-200 + Error envelope** (KHÔNG raise→4xx). `ErrorCode` KHÔNG có `INVALID_PASSWORD`/`WEAK_PASSWORD` ⇒ mọi lỗi password/hồ-sơ dùng `VALIDATION` (422) + `fields`.

### 2 loại 403 (mirror mobile-BE contract gotcha)
- **dispatcher-403** (guest/no-token): bare/POST `@whitelist` KHÔNG `allow_guest` ⇒ `is_whitelisted` raise `PermissionError` HTTP-403 status-line THẬT TRƯỚC handler. Đây là 403 khai trong OAS (`Forbidden` single-shape).
- in-handler `_err(UNAUTHORIZED)` @`profile.py:100` chỉ đạt nếu request tới được handler dưới danh nghĩa Guest — KHÔNG áp vì dispatcher chặn trước (bearer-gated). ⇒ 403-slot CHỈ giữ dispatcher-403 (KHÔNG dual-shape như `reportIncident`).

### `reauth_required` (Q-A) = False
`update_password(user, pwd)` gọi với `logout_all_sessions` mặc-định False (`frappe/utils/password.py:117,150`) ⇒ cookie `sid` HIỆN TẠI KHÔNG bị vô hiệu ⇒ mobile GIỮ phiên, KHÔNG ép re-login. ⇒ `reauth_required` = GENUINE `boolean` False (KHÔNG int-enum trap).

## Decision

**Curate 3 path GROUNDED 1:1 `mobile.v1.profile.*`, +6 schema RIÊNG, response slot `{200,401,403}`, 200 = `oneOf [<Envelope>, Error]` closed route-by-VALUE.** Tag `account`. Path-count **53→56**, opId **53→56** (đếm thật = 56, DUY NHẤT, camelCase). CONTRACT-ONLY (pure-yaml).

1. **`getMyProfile`** — `GET /api/method/assetcore.api.mobile.v1.get_my_profile` › `operationId: getMyProfile`. KHÔNG `requestBody` (GET, 0-param). live-sig parity `inspect.signature(get_my_profile) == {}` (`**_ignore` VAR_KEYWORD loại). 200 = `oneOf [MyProfileEnvelope, Error]` closed. slot `{200,401,403}`.

2. **`updateMyProfile`** — `POST .../update_my_profile` › `operationId: updateMyProfile`. `requestBody` = `UpdateMyProfileRequest` (json, CHỈ `{full_name, phone}` — cả 2 optional partial). live-sig parity `{full_name, phone}`. 200 = `oneOf [MyProfileEnvelope, Error]` closed. slot `{200,401,403}`.

3. **`changeMyPassword`** — `POST .../change_my_password` › `operationId: changeMyPassword`. `requestBody` = `ChangeMyPasswordRequest` (json, `required [old_password, new_password]`, `new_password.minLength:8`). live-sig parity `{old_password, new_password}`. 200 = `oneOf [ChangeMyPasswordEnvelope, Error]` closed. slot `{200,401,403}`.

4. **6 schema RIÊNG** (tất cả `additionalProperties:false`):
   - `MyProfile` — EXACT 7 prop VERBATIM `_build_my_profile:78-86`, `required` = cả 7; `phone`/`department`/`department_name` nullable; `roles`/`role_labels` array-of-string.
   - `MyProfileEnvelope` — `required [success, data]`, `success.enum [true]`, `data $ref MyProfile` (dùng CHUNG cho getMyProfile + updateMyProfile — cả 2 trả hồ sơ đầy đủ).
   - `ChangeMyPasswordData` — `required [reauth_required]`, `reauth_required` GENUINE `boolean`.
   - `ChangeMyPasswordEnvelope` — `required [success, data]`, `success.enum [true]`, `data $ref ChangeMyPasswordData`.
   - `UpdateMyProfileRequest` — CHỈ `{full_name, phone}` (KHÔNG `department` — READ-ONLY `_SELF_EDITABLE auth.py:24`), cả 2 optional.
   - `ChangeMyPasswordRequest` — `required [old_password, new_password]`, `new_password.minLength:8`.

**Phạm vi membership-set (test_mobile_oas):** 3 path ∈ `_ACCOUNT_PATHS` → ∈ `_PATHS_REQUIRE_401` + `_PATHS_REQUIRE_403` (401/403 symmetry +3) · **∉ `_MVP_BUSINESS_PATHS` / c5 envelope-maps** (mirror device-token — self-service account, KHÔNG field-tech WO flow; guard `c5 == _MVP_BUSINESS_PATHS` GIỮ 45) · **∉ `_MVP_READ_ENVELOPE`/`_MVP_ACTION_ENVELOPE`** · ∈ `_RATE_LIMIT_SOURCE_MAP` (KHÔNG `@rate_limit` ⇒ VẮNG khỏi `_PATHS_REQUIRE_429`, chống bịa 429). **CONTRACT-ONLY**: `git diff` `api/mobile/v1/profile.py` + `__init__.py` phần account = **TRỐNG** (BE LIVE) ⇒ KHÔNG reload gunicorn, KHÔNG migrate. 53 path hiện-hữu byte-identical; `d12/d15/d17` generator baseline KHÔNG đụng (pure mobile-yaml).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | KHÔNG curate, để 3 endpoint LIVE nhưng thiếu contract | Codegen client mobile KHÔNG sinh method → màn "Tài khoản" phải gọi tay/hardcode URL → drift + KHÔNG type-safe. Endpoint LIVE @source, bồi contract = codegen-ready ngay. CR-20 treo. |
| B | Đưa 3 path vào `_MVP_BUSINESS_PATHS` + c5 envelope-maps | SAI phân loại — account là self-service (mirror device-token), KHÔNG field-tech WO flow. Vào c5 làm vỡ guard `c5 == _MVP_BUSINESS_PATHS` (45). Device-token precedent: self-service mobile.v1 có 200-oneOf NHƯNG ∉ c5. `_ACCOUNT_PATHS` bucket riêng → 401/403 symmetry giữ nguyên tính đối-xứng. |
| C | `reauth_required` = `integer enum[0,1]` (mirror Check-field) | `reauth_required` KHÔNG phải Frappe Check — là Python `bool` literal `False` @`profile.py:173`. `boolean` faithful; int-enum sẽ nói dối shape. |
| D | `UpdateMyProfileRequest` khai thêm `department`/`roles` | `_SELF_EDITABLE = {full_name, phone}` @`api/auth.py:24` — delegate DROP mọi key ngoài allowlist (chống spoof §6.2). Khai `department` = contract cho phép field client KHÔNG bao giờ tác dụng → hiểu lầm. CHỈ 2 field self-editable. |
| E | 200 = SINGLE `$ref Envelope` (mirror `getAssetPmHistory`) | KHÁC read-history: `update`/`change` CÓ nhánh `_err` in-handler (VALIDATION 422) trả HTTP-200 + Error; `get_my_profile` có `_err` guest reserved. ⇒ `oneOf [Env, Error]` phản-ánh đúng error-mode (Decision-B). SINGLE sẽ giấu nhánh Error. |
| F | Đổi mật khẩu → HTTP-4xx khi sai (raise) | Vi phạm Decision-B (ADR-MOBILE-001): lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope, mobile route theo `body.success`/`fields`, KHÔNG status-line. `_err(VALIDATION)` HTTP-200 faithful @`profile.py:177-180`. |
| ✅ G | 3 path, 6 schema RIÊNG, 200-oneOf closed, `_ACCOUNT_PATHS` bucket, slot `{200,401,403}`, `reauth_required` boolean, request CHỈ self-editable | Grounded 1:1 source; blast-radius = +3 path +6 schema (PURE-YAML); codegen sinh 3 method đúng shape; mirror device-token architecture (self-service, ∉ c5); Decision-B intact; đóng CR-20. |

## Consequences

- **(+)** Màn "Tài khoản" mobile có contract codegen-ready: `getMyProfile` / `updateMyProfile` / `changeMyPassword` type-safe client. CR-20 (Account/Profile sync) ĐÓNG.
- **(+)** Contract GROUNDED 1:1 source — `MyProfile` 7-key VERBATIM `_build_my_profile`; live-sig parity 3 hàm (`{}` / `{full_name,phone}` / `{old_password,new_password}`, VAR_KEYWORD loại) chống drift; `reauth_required boolean` + request-schema CHỈ self-editable phản-ánh đúng `_SELF_EDITABLE`.
- **(+)** **CONTRACT-ONLY** — `git diff` `api/mobile/v1/profile.py` + `__init__.py` = TRỐNG (đã LIVE vòng trước) ⇒ KHÔNG reload gunicorn, KHÔNG migrate; `d12/d15/d17` UNCHANGED (pure mobile-yaml). 53 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator); 0 dangling `$ref` (6 schema mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`/`Error`). 2 loại 403 tách rõ: OAS khai dispatcher-403 (`Forbidden` single-shape); in-handler cap-403 KHÔNG áp (bearer-gated, dispatcher chặn trước).
- **(−)** Account paths ∉ `_MVP_BUSINESS_PATHS`/c5 (self-service, mirror device-token) — dùng `_ACCOUNT_PATHS` bucket riêng để giữ 401/403 symmetry mà KHÔNG phá guard `c5 == _MVP_BUSINESS_PATHS` (45). Người bồi path account kế PHẢI thêm vào `_ACCOUNT_PATHS`, KHÔNG `_MVP_BUSINESS_PATHS`.
- **(−)** `getMyProfile.200` khai nhánh Error dạng RESERVED (get_my_profile chỉ `_err` guest, dispatcher chặn trước) — giữ 200-oneOf đồng-dạng update/change cho codegen uniform; KHÔNG là dead-branch nguy hiểm (Error closed disjoint).
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `503→512` (test_mobile_oas, +9 TC class `TestMobileAccountProfileContract` a..i) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `503→512` + `_GUARD_SUITE_SUM` `646→655` + `_MOBILE_OAS_TOTAL` `672→681` + `account_profile_delta=9` (test_mobile_docset reconcile `pre_fc3_six==191` bất biến).

---

## Đã thực thi (Bước-4 ATOMIC — handoff BE/Test)

> CONTRACT-ONLY — KHÔNG đụng `api/*.py`/`services/*.py`. `bench --site miyano run-tests` các suite mobile (`test_mobile_oas` 512 OK · `test_mobile_docset` 9 OK · `test_mobile_preflight` 26 OK · `test_mobile_capability_map` 6 OK) GREEN.

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`):
- +3 path account (GET `getMyProfile` / POST `updateMyProfile` / POST `changeMyPassword`, tag `account`); slot `{200,401,403}` (`401 Unauthorized401`, `403 Forbidden`); 200 = `oneOf [<Envelope>, Error]` closed 0-discriminator.
- +6 schema (`MyProfile`, `MyProfileEnvelope`, `ChangeMyPasswordData`, `ChangeMyPasswordEnvelope`, `UpdateMyProfileRequest`, `ChangeMyPasswordRequest`) — tất cả `additionalProperties:false`. Tái-dùng `Unauthorized401`/`Forbidden`/`Error`. 0 orphan, 0 dangling.

**(2) test_mobile_oas.py**: path/opId count `53→56` (~97 site) + backward-compat relative-count reconcile (`getAssetPmHistory` 52→55, `transfer` 51→54); +`_GET_MY_PROFILE_PATH`/`_UPDATE_MY_PROFILE_PATH`/`_CHANGE_MY_PASSWORD_PATH`/`_ACCOUNT_PATHS` constants + 3 `_EXPECTED` entries + `_PATHS_REQUIRE_401/403` (+`_ACCOUNT_PATHS`) + `_RATE_LIMIT_SOURCE_MAP` (+3, no-rate-limit); +1 TC class `TestMobileAccountProfileContract` (a..i, 9 TC); `_EXPECTED_TEST_COUNT` `503→512`.

**(3) test_mobile_docset.py**: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `503→512` · `_GUARD_SUITE_SUM` `646→655` · `_MOBILE_OAS_TOTAL` `672→681` · `account_profile_delta=9` reconcile (`pre_fc3_six==191`). ADR-MOBILE-024 registered README (TC-MOB-DOC-02).

**(4) docs narrative**: `04-api-contract.md` (§8.30 Account/Profile) + README ADR-row (ADR-MOBILE-024) + Core Doc [`05_API_Specification.md`](../imm-00/05_API_Specification.md).

**BACKLOG (vòng kế):** `logoutUser` (`layout.logout_user` POST LIVE) — self-service session teardown, đối xứng account. FE web-type sync `frontend/src/api/*` cho account (nếu app web dùng chung).
