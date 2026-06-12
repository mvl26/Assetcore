# ADR-MOBILE-004 — Mô hình bảo mật backend cho mobile

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-004 |
| Phase | A — Kiến trúc & Feasibility (A7 — Security & Compliance) |
| Ngày | 2026-06-09 |
| Tác giả | BA Lead + System Architect (mobile) + Security reviewer |
| **Status** | **Accepted** |
| Bám quyết định | D-AUTH · D-MVP · D-STACK (`00-overview.md §2`) · ADR-MOBILE-001 |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source **Frappe v15.107.2** (read-only). Đặc tả threat model + checklist đầy đủ: [`08-security-compliance.md`](./08-security-compliance.md). ADR này chốt **mô hình**; doc 08 chốt **chi tiết**.

---

## Context

Initiative mobile mở **bề mặt tấn công mới** so với web SPA (cookie+CSRF+same-origin): endpoint OAuth2 public-facing, bearer token trên thiết bị di động (mất/trộm), native HTTP-client gọi thẳng API. Khảo sát read-only tại source phát hiện 3 điểm cần chốt mô hình bảo mật TRƯỚC khi Phase B provision public host:

1. **4 endpoint OAuth2** (`authorize`/`get_token`/`revoke_token`/`introspect_token`) đều `allow_guest=True` và **KHÔNG có `@rate_limit`** — `oauth2.py:74/:123/:144/:205` (grep `rate_limit` = 0 match). Brute-force/DoS không bị chặn ở core.
2. **CORS** luôn echo `Access-Control-Allow-Credentials: true` + `Origin` khi `allow_cors` được set — `app.py:283-284`; nhánh lọc list-origin BỎ QUA khi value = `'*'` — `app.py:275`. Wildcard prod = lỗ.
3. **Bearer→`set_user(token.user)`** — `auth.py:667` — chạy request dưới user thật ⇒ quyền/audit phụ thuộc HOÀN TOÀN vào DocPerm + lifecycle-chain hiện hữu (nếu hiểu sai = lỗ IDOR/scope).

Quyết định cốt lõi cần chốt: **(1)** chặn thiếu-sót-core ở đâu (sửa core vs tầng ngoài)? **(2)** có dựng hệ quyền thứ 2 cho mobile không? **(3)** xử lý CORS thế nào cho prod?

---

## Decision

### (a) Rate-limit OAuth2 ở TẦNG NGOÀI (nginx/reverse-proxy) — KHÔNG sửa Frappe core

4 endpoint oauth2 thiếu `@rate_limit` ở core (`oauth2.py:74/:123/:144/:205`). **KHÔNG patch `frappe/`** (nguyên tắc no-core-modify — CLAUDE.md §5). Chặn brute-force/DoS (T1) bằng `limit_req` của nginx cho location `/api/method/frappe.integrations.oauth2.*` (req/IP + burst), thực thi go-live (Phase B — HARD-STOP USER). PKCE S256 + short-code-TTL giảm giá trị đoán code.

### (b) 1 SSoT quyền — KHÔNG dựng hệ quyền thứ 2 cho mobile (kế thừa ADR-001 b)

Bearer→`set_user(token.user)` (`auth.py:667`) đặt `frappe.session.user` = KTV thật ⇒ **DocPerm + `permission_query_conditions` + RBAC capability (`rbac.py:156-168`) + vendor isolation (`permissions.py`) áp NGUYÊN VẸN** = chính lớp bảo vệ web. IDOR (T2) + scope-leo-quyền (T5) chặn bởi gate-cuối này. **Scope OAuth = gate THÔ on/off** (`oauth.py:51-56`), KHÔNG phải quyền thực. Mobile KHÔNG có lớp uỷ quyền song song. Hệ quả: KHÔNG cấp token cho tài khoản dùng-chung (giữ actor audit đúng).

### (c) CORS = list origin tường minh — CẤM wildcard `'*'` ở prod

Vì `app.py:275` chỉ lọc origin khi `allow_cors != "*"`, set `'*'` = mọi origin gửi credential được phép (T3). Chốt: `frappe.conf.allow_cors` = **list host hợp pháp** ở prod. Native KHÔNG dính CORS (D-STACK — không browser) ⇒ KHÔNG bật wildcard chỉ vì mobile. Config go-live (Phase B — HARD-STOP USER).

### (d) Audit NĐ98 từ mobile = chuỗi hiện hữu, KHÔNG thêm field/đường audit

Action-từ-mobile sinh audit qua `set_user(token.user)`→`log_audit_event` (`lifecycle.py:33`)→hash-chain SHA-256 (`lifecycle.py:9/:18/:97/:110-113`), actor = KTV thật (KHÔNG service-account). Mobile tái dùng NGUYÊN service nghiệp vụ (ADR-001 c) ⇒ cùng đường audit web. **KHÔNG** thêm field/đường audit mới cho mobile.

---

## Alternatives considered

| Phương án | Vì sao LOẠI |
|---|---|
| Patch `frappe/integrations/oauth2.py` thêm `@rate_limit` | Vi phạm no-core-modify; vỡ khi nâng cấp Frappe. Tầng nginx tách bạch + bền hơn. |
| Dựng hệ quyền thứ 2 (scope→capability mapping cứng cho mobile) | 2 SSoT = drift + lỗ hổng (web/mobile lệch quyền). Bearer→set_user đã đủ — DocPerm là gate cuối. |
| Bật `allow_cors='*'` cho tiện (mobile + web đều qua) | T3: mọi origin credential-echo. Native KHÔNG cần CORS ⇒ wildcard chỉ tăng rủi ro web. |
| Thêm bảng audit riêng cho mobile / service-account chung | Phá truy-xuất-đúng-actor NĐ98; nhân đôi đường audit = nguồn drift. Chuỗi hiện hữu đã đúng actor. |
| TTL access-token dài (đỡ refresh) | Cửa sổ token-leak (T4) rộng hơn. Giữ 3600s + refresh-rotation + revoke (ADR-001 A7). |

---

## Consequences

**Tích cực:**

- Bề mặt mobile có threat-model SSoT (T1–T7) + mitigation phân nhóm rõ trách nhiệm (đã-có / config-USER / repo-native) — `08 §1,§3`.
- KHÔNG nợ kỹ thuật core (rate-limit/CORS ở tầng ngoài — nâng cấp Frappe an toàn).
- 1 SSoT quyền ⇒ KHÔNG privilege-drift web↔mobile; audit NĐ98 đúng actor tự nhiên.

**Ràng buộc / phải làm:**

- **Phase B (HARD-STOP USER):** nginx rate-limit oauth2.*, `allow_cors` list-origin, HTTPS/TLS, OAuth Client least-privilege scope-set, creds `site_config`. Agent KHÔNG tự thực thi.
- **PROD TẮT `allow_error_traceback` (System Setting=0)** (HARD-STOP USER) — chống leak traceback/SQL ở body 401/403/429 (T-leak). Gate THẬT = `is_traceback_allowed()` (`response.py:60-65`) đọc `get_system_settings("allow_error_traceback")` (System Setting field `system_settings.json:263`, default 1 = ON ⇒ prod mặc-định LEAK; dùng ở `response.py:36/:182/:190/:203`). **GHI RÕ: gate KHÔNG phải `developer_mode` / `site_config`** — đổi qua desk hoặc `bench execute` (verify `is_traceback_allowed → False`); đồng bộ checklist `08 §4`.
- **Repo native (Phase D):** token Keychain/Keystore, cert-pinning, KHÔNG log token, PKCE S256, revoke khi logout/mất máy.
- **Phase F:** pentest bề mặt OAuth2 + token; baseline KPI bảo mật *(Cần khảo sát khi có traffic thật)*.

**Rủi ro còn lại:**

- Nếu USER quên rate-limit nginx → T1 hở (mitigation = checklist `08 §4` + review go-live).
- Token-leak (T4) phụ thuộc kỷ luật repo native — ngoài kiểm soát repo `assetcore` (mitigation = review code mobile Phase D).

---

## Evidence `file:line` (verify tại source — read-only)

| Claim | Evidence |
|---|---|
| 4 endpoint oauth2 `allow_guest`, KHÔNG rate-limit (T1) | `oauth2.py:74` (authorize), `:123` (get_token), `:144` (revoke_token), `:205` (introspect_token); grep `rate_limit` = 0 |
| Bearer→set_user (T2/T5/audit) | `auth.py:633` (validate_oauth), `:667` (`set_user(token.user)`) |
| RBAC capability gate cuối | `rbac.py:156-168`; vendor isolation `permissions.py:46/:90/:193/:209` |
| CORS credential-echo + wildcard bỏ-lọc (T3) | `app.py:269` (đọc allow_cors), `:275` (nhánh `!= "*"`), `:283-284` (cred:true + echo Origin) |
| PKCE S256 + refresh + revoke (T4) | `oauth.py:89-91`/`:146-164` (PKCE), `:187` (refresh grant); `oauth2.py:144` (revoke RFC 7009) |
| Scope coarse (T5) | `oauth.py:51-54` (validate_scopes), `:56` (get_default_scopes) |
| CSRF-skip bearer (an toàn) | `auth.py:83-98` (validate_csrf_token chỉ throw khi có session csrf) |
| Audit-chain SHA-256 đúng actor (NĐ98) | `lifecycle.py:9` (_compute_hash), `:18` (sha256), `:33` (log_audit_event), `:97`/`:110-113` (verify_audit_chain) |

---

## Tham chiếu chéo

- **Quy trình THỰC THI go-live (runbook) — biến quyết định bảo mật này (rate-limit nginx · CORS list-origin · least-priv OAuth Client · FCM creds) thành numbered steps + checklist + rollback:** [`10-deploy-ops.md`](./10-deploy-ops.md) (§2 CORS · §3 rate-limit nginx · §1 OAuth Client · §4 FCM). ADR-004 = *mô hình bảo mật*; `10` = *execute deploy/ops*.
- Đặc tả bảo mật đầy đủ (threat T1–T7 · NĐ98 audit · 3 nhóm mitigation · checklist · KPI): [`08-security-compliance.md`](./08-security-compliance.md)
- ADR kiến trúc nền (1 SSoT quyền · reuse-endpoint · no session-cookie): [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) (decision b/c/e)
- Auth deep-dive (sequence OAuth · TTL · scope↔capability): [`03-auth-oauth2.md`](./03-auth-oauth2.md)
- Push security (device-token threat): [`06-push-fcm.md`](./06-push-fcm.md) (§5.3)
- Offline/replay (idempotency-key T6): [`07-offline-sync.md`](./07-offline-sync.md) · [`ADR-MOBILE-003.md`](./ADR-MOBILE-003.md)
- Frappe core (read-only, KHÔNG sửa): `frappe/integrations/oauth2.py` · `frappe/auth.py` · `frappe/oauth.py` · `frappe/app.py`
