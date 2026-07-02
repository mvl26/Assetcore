# ADR-MOBILE-020 — `pingSession` (SESSION-PROBE — CSRF warm-up + app-resume who-am-I-lite) — ĐÓNG NỐT cặp session-lifecycle còn lại sau notification quartet (R38-R41) — contract GROUNDED 1:1 endpoint LIVE `layout.ping_session`

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-020 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-29 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-009** (C3-split cross-domain — `*Envelope`/`*Data` RIÊNG khi field-set THẬT khác) · **ADR-MOBILE-001 (d)** (OpenAPI = hợp đồng máy-đọc) · **FLOW-1 BOOTSTRAP `getUserContext`** (precedent allow_guest session who-am-I — KHÁC slot) · Core Doc IMM-00 `05_API_Specification.md` (layout session endpoints) + `ADR-IMM00-OPENAPI.md` |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/layout.py:237-258`, `assetcore/tests/test_mobile_oas.py`, `assetcore/tests/test_mobile_docset.py`). Contract: [`04-api-contract.md`](./04-api-contract.md) §8.1 + MÀN↔API [`05-personas-mvp.md §3`](./05-personas-mvp.md). Narrative: [`13-be-completion-roadmap.md §3.1`](./13-be-completion-roadmap.md).

---

## Context

Reconciliation auth mới nhất chốt **cookie-sid** cho mobile app (KHÔNG token-only). Cookie-sid CẦN một endpoint nhẹ cho 2 nhu cầu session-lifecycle:

1. **App-resume check** — app từ background quay lại foreground → cần xác minh nhanh session còn sống (`authenticated`) + biết `user` hiện tại (who-am-I-lite) mà KHÔNG kéo full `getUserContext` 13-field.
2. **CSRF warm-up** — tiền-đề cho MỌI POST: Frappe set `csrf_token` cookie qua response của endpoint nhẹ này; app đọc `csrf_token` để retry POST sau khi role/session đổi (`clear_sessions()` → sid cũ vô hiệu → token mới @`layout.py:246-248`).

Đây là **mắt-xích CUỐI** của cặp session-lifecycle, đóng-nốt sau notification quartet (R38-R41: `listNotifications`/`markNotificationAsRead`/`markAllAsRead`/`getUnreadNotifications`).

Endpoint nguồn **ĐÃ LIVE**: `assetcore.api.layout.ping_session` (`api/layout.py:237-258`) — whitelist từ trước, web-FE dùng cho CSRF warm-up. Vòng này **CONTRACT-ONLY**: bồi 1 path vào mobile yaml để codegen sinh client; **KHÔNG đụng `.py`** (KHÔNG reload gunicorn, KHÔNG migrate).

**Cơ-chế hiện hữu (đã VERIFY @source):**
- `@frappe.whitelist(allow_guest=True)` @`:237` — **guest ĐƯỢC phép** ⇒ dispatcher KHÔNG raise cap-403 ⇒ **0 đường-đi 403**. Guest gọi → nhận `{authenticated:false}` @HTTP-200.
- `def ping_session()` @`:238` — **0-PARAM** ⇒ codegen sinh no-arg GET ⇒ **KHÔNG requestBody, KHÔNG query parameter**. Live-sig parity: `inspect.signature(layout.ping_session).parameters == {}` (anti-drift, anti-false-green).
- Handler @`:238-258` **LUÔN `return _ok(...)`** — **0 nhánh `_err` in-handler** (KHÁC `get_user_context` có guest-guard `_err(_MSG_NOT_LOGGED_IN, 401)` @`:206-207`). ⇒ **KHÔNG Error branch trên HTTP-200**.
- `csrf_token = (frappe.local.session.data or {}).get("csrf_token") or ""` qua try/except @`:249-253` → fallback `""` ⇒ **string có-thể-rỗng** (KHÔNG nullable, KHÔNG bao giờ thiếu key).
- `_ok({"user": user, "authenticated": user != "Guest", "csrf_token": csrf_token})` @`:254-257` — `authenticated` = **GENUINE Python bool** (`user != "Guest"` @`:256`) ⇒ OpenAPI `type: boolean`, **KHÔNG int-enum[0,1] trap** (KHÁC field gốc Frappe `Check` — đây là biểu-thức bool runtime, mirror `is_late` của `PmSubmitResultResponse`).

## Decision

**Bồi 1 path GET `pingSession` GROUNDED 1:1 `layout.ping_session:237-258`, +2 schema RIÊNG (`PingSessionEnvelope`/`PingSessionData`), 0 requestBody, response slot `{200}` EXACTLY, 200 = SINGLE schema (KHÔNG oneOf [Env, Error]).** Tag align `getUserContext` (KHÔNG tag mới). 3 điểm KHÁC `getUserContext` grounded @source:

1. **OpenAPI** — path `/api/method/assetcore.api.layout.ping_session` › `get` › `operationId: pingSession` (dotted-tail == opId, camelCase regex, UNIQUE). **KHÔNG requestBody, KHÔNG query parameter** (0-param @`:238`). `200 = $ref PingSessionEnvelope` **SINGLE** (KHÔNG `oneOf [Env, Error]` — handler LUÔN `_ok`, 0 `_err`). security global OAuth2. Path-count **48→49**, opId **48→49**.

2. **`PingSessionData`** — closed (`additionalProperties:false`), `required` EXACT **3** = `[user, authenticated, csrf_token]` GROUNDED `_ok({...})` @`:254-257`. Types: `user: string`, `authenticated: **boolean**` (GENUINE bool @`:256` — KHÔNG `integer`/`enum[0,1]`), `csrf_token: string` (có-thể-`''` fallback @`:249-253`, KHÔNG nullable). `PingSessionEnvelope` closed: `success.enum [true]` const-ish + `data` = `$ref PingSessionData`. **C3-split RIÊNG** (ADR-MOBILE-009) — KHÔNG reuse `UserContextData` (13-field khác hẳn).

3. **Response slot `{200}` EXACTLY** — KHÔNG `401` (`allow_guest=True` ∧ KHÔNG in-handler guest-guard — guest nhận `{authenticated:false}` @200), KHÔNG `403` (`allow_guest` ⇒ dispatcher KHÔNG raise cap-403), KHÔNG `429` (0 `@rate_limit`). **KHÁC `getUserContext` `{200,401}`** (có guest-guard `_err(401)` @`:206-207`).

**Phạm vi:** path **∈ `_ALLOW_GUEST_PATHS`** (exempt 401/403 symmetry như `getUserContext`) NHƯNG **slot `{200}`** (test `TestMobilePingSessionContract` assert riêng — phân biệt tường minh với `getUserContext` `{200,401}`) ∧ **∉ `_MVP_BUSINESS_PATHS`** (allow_guest ⇒ KHÔNG 403, vào set sẽ vỡ symmetry) ∧ **∉ `_AUTH_PATHS`**. **CONTRACT-ONLY**: `git diff HEAD -- api/layout.py + services/layout.py` (services/layout.py KHÔNG tồn tại — layout API-only) = **TRỐNG** ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO] thật, né HARD-STOP USER).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | KHÔNG có `pingSession`, app dùng `getUserContext` cho app-resume + CSRF | `getUserContext` 13-field nặng (kéo Employee/profile) + slot `{200,401}` → guest nhận 401 Error mỗi lần resume = noise. `ping_session` LIVE @source, nhẹ, allow_guest → KHÔNG bồi contract = dead-end (cookie-sid app không có CSRF warm-up endpoint). |
| B | `200 = oneOf [PingSessionEnvelope, Error]` (mirror getUserContext/business path) | Handler @`:238-258` LUÔN `_ok`, **0 nhánh `_err`** ⇒ KHÔNG bao giờ có Error branch trên HTTP-200. Khai `oneOf [Env, Error]` = contract nói dối (claim error-mode không tồn tại) + ép codegen route-by-VALUE thừa. SINGLE schema mới source-faithful. |
| C | Khai slot `{200,401}` (mirror getUserContext) | `getUserContext` có guest-guard `_err(401)` @`:206-207`; `ping_session` KHÔNG (allow_guest + LUÔN `_ok`). Khai 401 = bịa error-mode. Guest nhận `{authenticated:false}` @200, KHÔNG 401. |
| D | `authenticated` int-enum `[0,1]` (mirror field Frappe `Check`) | SAI — `authenticated` là biểu-thức bool runtime `user != "Guest"` @`:256` (Python `True`/`False`), KHÔNG phải field DocType `Check`. `type: boolean` đúng wire-shape; int-enum[0,1] → Dart/Kotlin codegen deser SAI (LL-BE-50 int-vs-bool trap). |
| E | Khai requestBody `{}` hoặc query param | Handler 0-param @`:238` ⇒ codegen no-arg GET. requestBody/param = field rác + sai live-sig parity (`inspect.signature=={}`). KHÔNG requestBody/param mới khớp source. |
| F | `csrf_token` nullable | Fallback `or ""` @`:249-253` ⇒ LUÔN là string (có-thể-rỗng), KHÔNG bao giờ `null`/thiếu key. nullable = sai shape. |
| ✅ G | Path GET no-body, `PingSessionData` closed 3-key, slot `{200}` EXACTLY, 200 SINGLE `PingSessionEnvelope`, ∈ `_ALLOW_GUEST_PATHS` ∉ `_MVP_BUSINESS_PATHS` | Grounded 1:1 source; blast-radius = +1 path +2 schema (PURE-YAML); codegen sinh `pingSession()` no-arg trả `{user:string, authenticated:bool, csrf_token:string}`; slot {200}-only khớp allow_guest + LUÔN `_ok`. |

## Consequences

- **(+)** Cặp session-lifecycle ĐÓNG TRỌN cho cookie-sid mobile: `pingSession` (CSRF warm-up + app-resume who-am-I-lite, GET allow_guest) bổ-trợ OAuth `authorize`/`getToken`/`revoke`. App-resume nhẹ (3-field) thay vì kéo `getUserContext` 13-field.
- **(+)** Contract GROUNDED 1:1 source — slot `{200}`-only + 200 SINGLE schema khớp `allow_guest` + handler LUÔN `_ok`; live-sig parity `inspect.signature==={}` chống drift; `authenticated: boolean` chống int-vs-bool trap.
- **(+)** **CONTRACT-ONLY** — `git diff` api/layout.py + services/layout.py = TRỐNG ⇒ KHÔNG reload gunicorn, KHÔNG migrate; `test_oas_generator`/`d12`/`d15`/`d17` UNCHANGED (main imm-00 OAS KHÔNG đụng — pure mobile-yaml).
- **(+)** Decision-B intact (0 discriminator toàn file); 0 dangling `$ref`; path-count 48→49 + opId 48→49 (đếm thật, không literal); roadmap §3.1 claim "49 path" khớp `len(spec.paths)`.
- **(−)** `pingSession` là META-probe session (warm-up/who-am-I), **KHÔNG sinh Lifecycle Event** nghiệp-vụ (session-probe ≠ asset event — CLAUDE.md §10). KHÔNG đọc/ghi DocType nghiệp vụ.

**RED-before (Bước-4 chứng minh):** sau khi bồi path + 2 schema, `TestMobilePingSessionContract` (a..i, 9 TC) chạy GREEN; `_EXPECTED_TEST_COUNT` **458→467**; `TestMobileOasCountSelfVerify` GREEN; `test_mobile_docset` `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 458→467 + `_GUARD_SUITE_SUM` 601→610 + `_MOBILE_OAS_TOTAL` 627→636 + `session_probe_delta=9` trong transition narrative (baseline 191 GIỮ) ⇒ `TestMobileGuardSuiteCountParity` GREEN. Path-count toàn-suite 48→49; `d12/d15/d17` get/post UNCHANGED.

**BACKLOG (vòng kế — KHÔNG làm round này):** `logout_user` (`layout.logout_user` POST @`:262`, LIVE, THIẾU contract) → wire `logoutUser` đóng-nốt cặp session-lifecycle cookie-sid (ping/logout) bổ-trợ OAuth authorize/getToken/revoke. POST slot `{200,401,403}` (KHÁC `pingSession` allow_guest `{200}`); `data` `{logged_out:bool}` | `{already_logged_out:bool}` GROUNDED `_ok` @`:268,272`.
