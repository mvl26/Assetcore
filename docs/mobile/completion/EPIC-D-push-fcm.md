# EPIC-D — Push FCM (impl) · Backend-for-Mobile Completion

| Mục | Giá trị |
|---|---|
| Initiative | AssetCore Mobile — backend-for-mobile (repo UI native tách riêng) |
| EPIC | **EPIC-D — Push FCM** (ID KHOÁ — KHÔNG đổi) |
| Vai trò file | Bộ "BE COMPLETION" — chốt task AUTO/HARD-STOP để hoàn thiện lớp BE kênh #3 push |
| Bám quyết định | D-AUTH (OAuth2+refresh) · D-MVP (field-tech) · D-STACK (native) — `../00-overview.md §2` · **ADR-MOBILE-002** (cơ chế push) |
| Phụ thuộc | **EPIC-B** (B3 device-token + bearer→`set_user`) · **EPIC-G** (FCM creds `site_config`) — xem §1.3 |
| Owner | BA Lead (spec) + BE (impl) + QA (test) |
| Trạng thái | Spec đóng — impl chờ AUTO (factory) + HARD-STOP USER (creds/migrate/reload) |
| Cập nhật | 2026-06-11 |

> **Vùng spec gốc (HỢP ĐỒNG, KHÔNG re-litigate):** [`../06-push-fcm.md`](../06-push-fcm.md) (327 dòng, A5) + [`../ADR-MOBILE-002.md`](../ADR-MOBILE-002.md) (Accepted — FCM Admin SDK HTTP v1 TRỰC TIẾP, KHÔNG relay Frappe Cloud). EPIC-D = biến spec đó thành task kiểm-được.
> **Mọi `file:line` đối chiếu source THẬT** (`assetcore/services/notifications.py`, `hooks.py`, `permissions.py`, OpenAPI yaml) — KHÔNG bịa field/endpoint/cap.
> **Chỉ mục completion:** [`EPIC-C-api-contract.md`](./EPIC-C-api-contract.md) · [`EPIC-B-auth-provisioning.md`](./EPIC-B-auth-provisioning.md) · **EPIC-D (file này)** · [`EPIC-G-golive-hardening.md`](./EPIC-G-golive-hardening.md) · [`EPIC-V-codegen-verification.md`](./EPIC-V-codegen-verification.md) · roadmap tổng: [`../13-be-completion-roadmap.md §6`](../13-be-completion-roadmap.md)

---

## 1. Scope & Mục tiêu

### 1.1 Mục tiêu (DoD EPIC-D)

> **Báo hỏng → kỹ thuật viên được giao nhận PUSH** (kênh #3 FCM), test xanh (mock FCM + audit + self-scope).

Đây là **flow-6** của MVP field-tech 6-flow (`../00-overview.md §2 D-MVP`). EPIC-D hoàn thiện lớp BE để repo native nhận push thật:
- Endpoint **đăng ký/thu hồi** FCM device-token (per user/device) + DocType lưu (registry tự quản, KHÔNG lệ thuộc relay).
- Wire **kênh #3 push** vào engine notification 7-event (`services/notifications.py::_dispatch`) — **CHỈ THÊM**, KHÔNG phá in-app/email.
- Sender FCM HTTP v1 đọc creds từ `site_config` (USER set).

### 1.2 Trong scope / Ngoài scope

| Trong scope EPIC-D | Ngoài scope (post-MVP / EPIC khác) |
|---|---|
| DocType `AC Mobile Device Token` (7 field, autoname=hash, UNIQUE fcm_token) | Offline-sync / conflict policy → **post-MVP** (`../07-offline-sync.md`) |
| Service + API `register/unregister_device_token` (bearer, self-service) | Notification inbox list/read endpoint (Phase D/E — `../06-push-fcm.md §5.5`) |
| RBAC wiring self-scope + vendor isolation (bám SSoT `permissions.py`) | Manager/duyệt push, đa-module mở rộng → **post-MVP** |
| Kênh #3 push trong `_dispatch` (phủ cả 7 event qua 1 điểm fan-out) | Tạo Firebase project / set creds `site_config` → **D3 [HARD-STOP USER]** |
| Sender `utils/fcm.py` (HTTP v1 + ký SA) + invalidate-on-401 | `bench migrate` (DocType) + `bench restart` (api/_dispatch) → **[HARD-STOP USER]** §4 |
| Rate-limit register (chống spam) + audit NĐ98 register/unregister | Library install (firebase-admin) — BE KHÔNG cài lib (HARD-STOP) |
| Test mock-FCM (dedup/spoof/self-scope/invalidate/fan-out/audit) | — |

### 1.3 Bất biến (BẮT BUỘC — `../06-push-fcm.md §3.1`)

> **Push = KÊNH THỨ 3, CHỈ THÊM.** Kênh 1 (in-app Notification Log `notifications.py:385`) + Kênh 2 (email `_safe_sendmail` `:407-409`) **GIỮ NGUYÊN**. Push chèn SAU 2 kênh trong cùng `_dispatch`, cùng danh sách `users` đã dedupe (`:377`) + cùng `doc` reference (`:381-382`). **Lỗi FCM KHÔNG vỡ in-app/email** (fail-safe — pattern `_safe_sendmail` `utils/helpers.py:59`).

---

## 2. Actor

| Actor | Vai trò trong EPIC-D | Tham chiếu |
|---|---|---|
| **Kỹ thuật viên hiện trường (field-tech)** | APK lấy `fcm_token` từ SDK → gọi `register_device_token` (bearer); nhận push khi được giao sự cố/WO; tap → mở deep-link màn native; opt-out per-device | `../05-personas-mvp.md §1` · `../06-push-fcm.md §0.3` |
| **AssetCore BE (Frappe)** | Lưu token (DocType AC Mobile Device Token); khi event xảy ra → `_dispatch` fan-out kênh #3 gửi FCM tới token `enabled=1` của recipient; invalidate-on-401 | `services/notifications.py::_dispatch:366` |
| **FCM (Google Firebase Cloud Messaging)** | Hạ tầng đẩy thực; BE gọi FCM HTTP v1 bằng service-account creds trong `site_config` | `../ADR-MOBILE-002.md` |
| **Admin / System Manager** | Xem TẤT CẢ device-token (quản trị/thu hồi); user thường chỉ thấy token của mình (RBAC §6) | `../06-push-fcm.md §2.3` |
| **USER (vận hành go-live)** | Set FCM creds `site_config` (D3) + `bench migrate`/`restart` — **HARD-STOP** | §4 + `../10-deploy-ops.md §4` |

---

## 3. Hiện trạng (file:line CHÍNH XÁC)

### 3.1 Engine notification — 1 điểm fan-out, CHỈ 2 kênh (CHƯA có push)

| Sự thật | file:line | Ghi chú |
|---|---|---|
| `_dispatch(users, subject, message, doc)` = điểm fan-out DUY NHẤT | `services/notifications.py:366` | Chèn kênh #3 TẠI ĐÂY phủ cả 7 event |
| Kênh 1 in-app `enqueue_create_notification` | `notifications.py:385` | Notification Log Alert = audit NĐ98 (bất biến) |
| Kênh 2 email `_safe_sendmail` cho `_user_wants_email()==True` | `notifications.py:407-409` (toggle `:251`) | Chỉ user bật email |
| Dedupe `users` (drop empty) | `notifications.py:377` | Push tái dùng list này — KHÔNG resolve recipient lần 2 |
| `document_type`/`document_name` của doc (cho data payload) | `notifications.py:381-382` | Feed `data.doctype`/`data.name` payload §5 |
| **KHÔNG có kênh push** | grep `fcm`/`push` trong `notifications.py` = 0 | Xác minh 2026-06-11 |

### 3.2 7 event đi qua `_dispatch` (7 call-site — `grep -n "_dispatch(" notifications.py`)

| # | Dispatch fn (def) | Trigger | Call-site `_dispatch` | Recipient |
|---|---|---|---|---|
| E1 | `notify_assignment` (`notifications.py:416`) | WO gán KTV (PM WO / Asset Repair on_update+on_submit) | `:452` | `assigned_to` |
| E2 | `notify_approval_pending` (`:461`) | doc VÀO state cần duyệt (động từ Workflow meta) | `:498` | approver |
| **E3** | **`notify_incident_created` (`:506`)** | **Incident Report after_insert = MVP trigger BÁO HỎNG** | **`:562`** | **`assigned_to` / fallback `reported_by`** |
| E4 | `notify_calibration_due` (`:578`) | scheduler calibration_status → Due Soon/Overdue (IMM-11) | `:627` | `responsible_technician` / fallback `custodian` |
| E5 | `notify_escalation` (`:752`) | WO VÀO state escalation (IMM-08 Halted/Major Failure) | `:791` | supervisor + role quản trị |
| SLA-a | `_emit_sla_notification` (`:907`) | scheduler SLA-breach Asset Repair (warning/breach IMM-09) | `:931` | recipient WO |
| SLA-b | `_emit_incident_sla_notification` (`:1072`) | scheduler SLA-breach sự cố (tiếp nhận/xử lý IMM-12) | `:1116` | recipient sự cố |

> **7 call-site = `:452 :498 :562 :627 :791 :931 :1116`.** Kênh #3 chèn 1 lần trong thân `_dispatch:366` ⇒ phủ cả 7 — KHÔNG sửa từng call-site (chống drift, §6.3 roadmap).

### 3.3 E3 báo hỏng (DoD flow) — đã wired, đã dedupe recipient

| Sự thật | file:line |
|---|---|
| `notify_incident_created` wired `Incident Report` after_insert | `hooks.py:270` |
| Recipient = `resolve_recipients(doc, "assigned_to")` (KTV được giao) | `notifications.py:526` |
| Fallback `reported_by` (self-confirm) khi chưa phân công ai | `notifications.py:535` |
| → `_dispatch(recipients, subject, message, doc)` | `notifications.py:562` |
| Incident enrich `assigned_to_name`/`reporter_name` (list) | `services/imm12.py:294-307` |

> **Ý nghĩa cho DoD:** khi incident có `assigned_to` (KTV được giao) → kênh #3 (sau khi chèn) bắn push tới token `enabled=1` của KTV đó. **0 dòng E3 cần sửa** — push tự đến qua `_dispatch`.

### 3.4 GAPS chặn flow-6 (CHƯA tồn tại)

| Gap | Bằng chứng |
|---|---|
| DocType `AC Mobile Device Token` CHƯA tạo | folder `assetcore/doctype/ac_mobile_device_token/` ∄ (grep doctype `device`/`fcm`/`push` = chỉ `imm_device_model`/`imm_device_spare_part`/`ac_purchase_device_item`) |
| `register/unregister_device_token` = STUB OpenAPI, KHÔNG Python impl | yaml `:1565` (registerDeviceToken) · `:1582` (unregisterDeviceToken); folder `api/mobile/v1/` ∄ (chỉ `api/mobile/preflight.py`) |
| RBAC self-scope CHƯA đăng ký | `hooks.py:390/397` hiện chỉ có `Incident Report` query/has_permission — KHÔNG có `AC Mobile Device Token` |
| Kênh #3 push CHƯA chèn `_dispatch` | §3.1 (grep fcm/push = 0) |
| Sender FCM HTTP v1 CHƯA có | `utils/fcm.py` ∄; KHÔNG lib firebase-admin/google-auth; KHÔNG đọc `site_config.fcm_*` |
| Audit register/unregister (NĐ98 §5.4) chưa wire | — |
| Rate-limit register (chống spam §5.3) chưa impl | pattern có sẵn `@rate_limit` `api/imm00.py:311/354` |
| **Phụ thuộc EPIC-B:** bearer→`set_user` reach `api/mobile/v1` chưa e2e | xem **EPIC-B B3** + §8 rủi ro |

---

## 4. Tasks (D1–D7)

> **Quy ước tag:** `[AUTO]` = factory tự đóng (doc/impl-không-deploy + test) · `[HARD-STOP USER]` = `site_config`/FCM creds/`bench migrate`/`bench restart` (BE KHÔNG tự chạy). **Dependency** ghi rõ EPIC+task. **Same-commit wiring gate:** định nghĩa gate/hook → cùng commit PHẢI wire `hooks.py` (Pattern A `assetcore-doc`).

### D1 — DocType AC Mobile Device Token

- **Mô tả:** tạo DocType registry token push (7 field theo `../06-push-fcm.md §2.1`). autoname=`hash` (§2.2 — token KHÔNG làm PK vì dài + rotate). `track_changes=1` (audit modify). UNIQUE trên `fcm_token` (§2.4 — dedup). Field: `user` Link→User reqd · `fcm_token` Data/Long Text UNIQUE reqd · `platform` Select `android`/`ios` reqd · `device_label` Data · `app_version` Data · `last_seen` Datetime · `enabled` Check default 1.
- **Files (Create):** `assetcore/doctype/ac_mobile_device_token/__init__.py` · `.../ac_mobile_device_token.json` · `.../ac_mobile_device_token.py` (controller delegate — logic ở service, CLAUDE.md §15). DocPerm: `System Manager` read-all + role field-tech self (read/write/create/delete own).
- **Acceptance (kiểm-được):**
  - `[AUTO test]` `bench --site miyano run-tests --module assetcore.tests.test_mobile_device_token` (TC schema: 7 field tồn tại đúng type, autoname=hash, `fcm_token` unique).
  - `[HARD-STOP USER]` `bench --site miyano migrate` (tạo bảng) — BE KHÔNG chạy.
- **Owner:** [BE] (impl) · [QA] (test schema).
- **Tag:** `[AUTO impl]` + `[HARD-STOP USER migrate]`.
- **Dependencies:** — (độc lập về định nghĩa; bảng cần migrate USER).

### D2 — Service mobile_device_token (3-tier)

- **Mô tả:** service-layer 3-tier register/unregister/invalidate. `register_device_token(*, fcm_token, platform, device_label='', app_version='')` **ÉP `user=frappe.session.user`** (KHÔNG nhận `user` từ client — chặn spoof §6/`../06 §5.3`); **UPSERT dedup theo `fcm_token`** (§2.4: token tồn tại → cập nhật `user`/`platform`/`device_label`/`app_version`/`last_seen`/`enabled=1`, KHÔNG tạo record mới; đổi `user` cùng token = re-bind sạch). `unregister_device_token(fcm_token)` set `enabled=0` GIỮ record cho audit (§2.5). `invalidate_token(fcm_token)` (gọi từ sender khi FCM 401/UNREGISTERED). **Require bearer** (đã login) — KHÔNG cap mới (self-service §2.3). Gọi `log_audit_event` cho register/unregister (NĐ98 §5.4).
- **Files (Create):** `assetcore/services/mobile_device_token.py`.
- **Acceptance:** `[AUTO test]` `bench --site miyano run-tests --module assetcore.tests.test_mobile_device_token` (TC: upsert-dedup giữ 1 record/token; ÉP `user=session` (truyền `user=victim` KHÔNG đổi chủ); unregister → `enabled=0` record CÒN; invalidate → `enabled=0`).
- **Owner:** [BE].
- **Tag:** `[AUTO]`.
- **Dependencies:** **D1** (DocType). Bearer→`set_user` từ **EPIC-B B1/B3** (e2e cloud chờ EPIC-B).

### D3 — FCM credentials site_config

- **Mô tả:** USER đặt service-account credentials cho FCM HTTP v1 vào `site_config.json`: `fcm_service_account_path` (đường dẫn file JSON SA — KHÔNG commit) + `fcm_project_id`. Cùng nhóm config go-live với `allow_cors`/`assetcore_qr_base_url`/`host_name` (EPIC-G §5.1). Đăng ký Firebase project + cho phép outbound HTTPS `fcm.googleapis.com`. **TUYỆT ĐỐI KHÔNG:** commit creds vào repo; KHÔNG trả creds qua bất kỳ API nào; KHÔNG log creds (`../06 §5.2`). Rollback xoay key khi lộ (Firebase console).
- **Files (Modify, do USER):** `<bench>/sites/miyano/site_config.json` (KHÔNG trong repo). Runbook: [`../10-deploy-ops.md §4`](../10-deploy-ops.md).
- **Acceptance:** `[HARD-STOP USER]` `bench --site miyano execute frappe.get_conf` (hoặc kiểm `frappe.conf.fcm_project_id` non-empty) → có `fcm_service_account_path` + `fcm_project_id`; outbound HTTPS `fcm.googleapis.com` reachable từ host.
- **Owner:** [BA] (runbook + verify checklist) · USER (execute).
- **Tag:** `[HARD-STOP USER]` (site_config + FCM creds + Firebase project).
- **Dependencies:** — (độc lập; chặn D5/D6 chạy THẬT). Cùng nhóm knob EPIC-G.

### D4 — API mobile/v1 register/unregister + OpenAPI typed

- **Mô tả:** handler `register/unregister_device_token` trong namespace `api/mobile/v1` (`@frappe.whitelist(methods=["POST"])`, **KHÔNG `allow_guest`** — cần bearer). Function-name = `operationId` (`registerDeviceToken`/`unregisterDeviceToken` — FROZEN yaml `:1568/:1585`). Gọi service D2. Gỡ 2 path khỏi `_STUB_PATHS` trong `test_mobile_oas`; bồi requestBody `DeviceTokenRequest` (`fcm_token` reqd · `platform` enum `android`/`ios` reqd · `device_label?` · `app_version?`) `oneOf` json+form (Frappe RPC `form_dict`) + response 200 typed `oneOf[Created|Error]` (in-handler error → nhánh Error, đồng pattern 3 create EPIC-C). Cập nhật `ADR-IMM00-OPENAPI` + `../04-api-contract.md`.
- **Files (Create):** `assetcore/api/mobile/v1/__init__.py` · `assetcore/api/mobile/v1/device_token.py`. **(Modify):** `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (gỡ STUB `:1565/:1582`, bồi requestBody/response) · `assetcore/tests/test_mobile_oas.py` (`_STUB_PATHS` + assert typed) · `docs/mobile/04-api-contract.md` · `docs/imm-00/ADR-IMM00-OPENAPI.md`.
- **Acceptance:**
  - `[AUTO]` `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` (2 path rời `_STUB_PATHS`; requestBody/response typed; 0 dangling `$ref`).
  - `[AUTO→V]` `openapi-generator` (Dart/Kotlin) sinh method `registerDeviceToken`/`unregisterDeviceToken` 0-error (thuộc **EPIC-V**; chờ toolchain `[HARD-STOP USER]`).
  - `[HARD-STOP USER]` `bench restart`/reload (gunicorn `--preload`) MỚI live HTTP.
- **Owner:** [BE] (handler) · [BA] (yaml/04/ADR).
- **Tag:** `[AUTO impl + yaml]` + `[HARD-STOP USER reload]`.
- **Dependencies:** **D2** (service). yaml typed-pattern bám **EPIC-C** (oneOf+discriminator).

### D5 — Sender utils/fcm.py (FCM HTTP v1)

- **Mô tả:** sender gửi 1 message FCM HTTP v1. Đọc `site_config` (`fcm_service_account_path`/`fcm_project_id` từ **D3**); ký OAuth2 service-account → POST `https://fcm.googleapis.com/v1/projects/<project_id>/messages:send`. Library: REST HTTP v1 + tự ký SA (stdlib + `requests`) HOẶC `firebase-admin` — **quyết Phase E kèm test; KHÔNG cài lib ở round doc** (BE KHÔNG cài lib — HARD-STOP). Lỗi `UNREGISTERED`/HTTP 404 `messaging/registration-token-not-registered` → gọi `invalidate_token()` (D2 §2.5). **KHÔNG log credentials.**
- **Files (Create):** `assetcore/utils/fcm.py`.
- **Acceptance:** `[AUTO test]` `bench --site miyano run-tests --module assetcore.tests.test_mobile_device_token` (TC mock FCM: build message đúng shape §5; 401/UNREGISTERED → `invalidate_token` gọi đúng 1 lần; creds đọc từ conf KHÔNG hard-code; KHÔNG xuất creds ra log).
- **Owner:** [BE].
- **Tag:** `[AUTO impl]` (lib install + creds chạy THẬT = **D3 [HARD-STOP USER]**).
- **Dependencies:** **D3** (creds chạy thật) · **D2** (`invalidate_token`).

### D6 — Chèn kênh #3 push vào _dispatch + rate-limit register

- **Mô tả:** chèn kênh #3 trong thân `_dispatch` (`notifications.py:366`) **SAU** kênh 1 (`:385`) + kênh 2 (`:407-409`): per `user` trong list đã dedupe (`:377`) → tra device-token `enabled=1` của user → gọi sender D5 với payload §5. **Fail-safe BẮT BUỘC:** bọc `try/except` + `frappe.log_error` (pattern `_safe_sendmail`) — lỗi FCM KHÔNG vỡ in-app/email (§1.3). 1 điểm chèn ⇒ phủ cả 7 event (E1–E7). Thêm rate-limit endpoint register (`@rate_limit` pattern `api/imm00.py:311/354`) chống spam đăng ký (`../06 §5.3/§5.5`).
- **Files (Modify):** `assetcore/services/notifications.py` (`_dispatch` chèn kênh #3 — KHÔNG sửa call-site) · `assetcore/api/mobile/v1/device_token.py` (thêm `@rate_limit` register).
- **Acceptance:**
  - `[AUTO test]` `bench --site miyano run-tests --module assetcore.tests.test_mobile_device_token` (TC: `_dispatch` mock-FCM bắn push CHỈ tới token `enabled=1` của recipient; token `enabled=0` bị bỏ; FCM raise → in-app/email VẪN gửi (fail-safe)).
  - `[AUTO regression]` `bench --site miyano run-tests --module assetcore.tests.test_notification_framework && bench --site miyano run-tests --module assetcore.tests.test_notifications && bench --site miyano run-tests --module assetcore.tests.test_imm12_notify` (kênh 1+2 KHÔNG đổi hành vi — 0 regression).
  - `[HARD-STOP USER]` `bench restart`/reload MỚI live HTTP.
- **Owner:** [BE].
- **Tag:** `[AUTO impl]` + `[HARD-STOP USER reload]`.
- **Dependencies:** **D5** (sender) · **D2** (tra token). DoD flow đi qua **E3** (`:562`, §3.3).

### D7 — RBAC wiring + test suite + DoD báo-hỏng→push

- **Mô tả:** wire self-scope + vendor isolation cho `AC Mobile Device Token` (KHÔNG dựng hệ quyền thứ 2, §6). Đăng ký `hooks.py::permission_query_conditions` (self-scope `user==frappe.session.user`) + `hooks.py::has_permission` (vendor isolation pattern `_VENDOR_ROLE` `permissions.py:46/90/188`) — **Same-commit wiring gate** (định nghĩa hàm + wire hooks cùng commit). Test suite end-to-end DoD: **báo hỏng (E3) → KTV được giao nhận push** (mock FCM) + audit record + self-scope.
- **Files (Create):** `assetcore/tests/test_mobile_device_token.py`. **(Modify):** `assetcore/permissions.py` (2 hàm `ac_mobile_device_token_query` + `ac_mobile_device_token_has_permission`) · `assetcore/hooks.py` (`permission_query_conditions` + `has_permission` thêm `AC Mobile Device Token`) · `assetcore/tests/test_mobile_oas.py` (gỡ 2 STUB — đồng D4).
- **Acceptance:**
  - `[AUTO test]` `bench --site miyano run-tests --module assetcore.tests.test_mobile_device_token` (TC DoD: tạo Incident `assigned_to=KTV-A`, KTV-A có token `enabled=1` → after_insert E3 → `_dispatch` mock-FCM gửi push tới token KTV-A đúng 1 lần; KTV-B token KHÔNG nhận; audit register/unregister sinh record; self-scope: user-B KHÔNG `get_list` thấy token user-A).
  - `[AUTO]` `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` (xanh sau gỡ STUB).
  - `[HARD-STOP USER]` `bench migrate` + `bench restart` (RBAC hook + DocType live).
- **Owner:** [BE] (RBAC) · [QA] (test DoD).
- **Tag:** `[AUTO impl + test]` + `[HARD-STOP USER migrate/reload]`.
- **Dependencies:** **D1** (DocType) · **D2** (service+audit) · **D6** (kênh #3). Vendor pattern bám `permissions.py`.

### 4.1 Bảng tổng tag + dependency

| Task | Tag | Owner | Phụ thuộc | Acceptance lệnh chính |
|---|---|---|---|---|
| D1 DocType | `[AUTO]`+`[HARD-STOP migrate]` | [BE]/[QA] | — | `run-tests test_mobile_device_token` |
| D2 Service | `[AUTO]` | [BE] | D1 · EPIC-B B1/B3 (bearer) | `run-tests test_mobile_device_token` |
| D3 FCM creds | `[HARD-STOP USER]` | [BA]/USER | — | `bench execute frappe.get_conf` |
| D4 API + yaml | `[AUTO]`+`[HARD-STOP reload]` | [BE]/[BA] | D2 · EPIC-C (oneOf) | `run-tests test_mobile_oas` |
| D5 Sender | `[AUTO]` | [BE] | D2 · D3 (chạy thật) | `run-tests test_mobile_device_token` |
| D6 Kênh #3 | `[AUTO]`+`[HARD-STOP reload]` | [BE] | D5 · D2 | `run-tests test_notification_framework` + `test_mobile_device_token` |
| D7 RBAC+DoD | `[AUTO]`+`[HARD-STOP migrate/reload]` | [BE]/[QA] | D1·D2·D6 | `run-tests test_mobile_device_token` |

---

## 5. Data model / Schema

### 5.1 DocType AC Mobile Device Token (D1)

| Field | Type | Bắt buộc | Mô tả | Nguồn |
|---|---|---|---|---|
| `user` | Link → User | ✔ | Chủ token. Mặc định = `frappe.session.user` lúc register (server ÉP, KHÔNG nhận từ client) | `../06 §2.1` |
| `fcm_token` | Data (Long Text nếu >140) | ✔ | FCM registration token (SDK cấp). **UNIQUE** (dedup) | `../06 §2.4` |
| `platform` | Select `android`/`ios` | ✔ | Nền tảng. MVP android trước | `../06 §2.1` |
| `device_label` | Data | ✘ | Nhãn thiết bị (hiển thị khi user quản lý token) | — |
| `app_version` | Data | ✘ | Phiên bản APK (debug/migration payload) | — |
| `last_seen` | Datetime | ✘ | Lần cuối token sống (cập nhật mỗi register/push OK) | — |
| `enabled` | Check (default 1) | ✔ | Cờ opt-in/opt-out + invalidate. `0` ⇒ KHÔNG gửi push | `../06 §2.5` |

- **autoname:** `hash` (system PK). **UNIQUE** constraint trên `fcm_token`. `track_changes=1`.
- **KHÔNG bịa thêm field.** Nếu D-impl cần `device_id` ổn định (re-bind khi token rotate) → bổ sung kèm RED test, ghi delta vào `../06 §2.1`.

### 5.2 DeviceTokenRequest (D4 — requestBody typed)

| Field | Type | Bắt buộc | Enum/ràng buộc |
|---|---|---|---|
| `fcm_token` | string | ✔ | non-empty |
| `platform` | string | ✔ | enum `android`/`ios` (Select-canonical 1:1 §5.1) |
| `device_label` | string | ✘ | — |
| `app_version` | string | ✘ | — |

- `content` = `oneOf` `application/json` + `application/x-www-form-urlencoded` (Frappe RPC đọc `form_dict`). Response 200 `oneOf[Created|Error]` (in-handler error → Error, đồng pattern EPIC-C).

### 5.3 Payload FCM HTTP v1 (D5/D6 — `../06 §4.1`)

```jsonc
{
  "message": {
    "token": "<fcm_token của 1 device enabled>",
    "notification": {
      "title": "<title VI ngắn>",   // = subject _dispatch dựng, strip HTML
      "body":  "<body VI ≤1000 ký tự, strip HTML>"
    },
    "data": {                        // data-only → APK tự điều hướng
      "doctype":  "Incident Report", // = _dispatch document_type (notifications.py:381)
      "name":     "INC-2026-0042",   // = _dispatch document_name (:382)
      "event":    "incident_created",// mã event (E1..E7/sla)
      "deeplink": "assetcore://incident/INC-2026-0042"  // §5.4
    },
    "android": { "priority": "high" } // incident/SLA-breach=high; PM-due=normal
  }
}
```

- **title/body** tái dùng `subject`/`message` mà `_dispatch` đã dựng (cùng nội dung in-app/email) → strip HTML cho push, body ≤1000 ký tự.
- **data-only routing:** deep-link trong `data` (KHÔNG chỉ `notification`) để APK điều hướng cả foreground/background.

### 5.4 Deep-link → route native (`data.deeplink`, `../06 §4.2`)

| event (E#) | doctype | deeplink (đề xuất) | Màn native |
|---|---|---|---|
| E1 assignment | PM WO / Asset Repair | `assetcore://wo/<pm\|cm>/<name>` | Chi tiết phiếu được gán |
| E3 incident_created | Incident Report | `assetcore://incident/<name>` | Chi tiết sự cố (DoD flow) |
| E4 calibration_due | AC Asset | `assetcore://asset/<asset_name>` | Hồ sơ thiết bị |
| E5 escalation | PM Work Order | `assetcore://wo/pm/<name>` | Chi tiết WO escalation |
| SLA-a/b | Asset Repair / Incident Report | `assetcore://wo/cm/<name>` · `assetcore://incident/<name>` | Phiếu sắp/đã vi phạm SLA |

- BE chỉ phát `doctype/name/event/deeplink` (KHÔNG ép route native cụ thể — repo native chốt route Phase D, `../06 §4.2`).

---

## 6. Security & Audit (RBAC / token / NĐ98)

### 6.1 RBAC — bám SSoT, KHÔNG dựng hệ quyền thứ 2 (D7)

| Chủ thể | Quyền trên AC Mobile Device Token | Thực thi |
|---|---|---|
| User thường (field-tech) | CHỈ token của mình (`user==frappe.session.user`) | `permission_query_conditions` self-scope (pattern `permissions.py` WO `reported_by`/`assigned_to`) |
| Admin / System Manager | Xem TẤT CẢ token (thu hồi token nghi ngờ) | role `System Manager` (Frappe built-in) — KHÔNG cap mới |
| Vendor Engineer | Isolation: chỉ token của chính họ | `has_permission` pattern `_VENDOR_ROLE` `permissions.py:46/90/188` |

- **KHÔNG thêm capability vào `CAPABILITY_MAP`** cho register/unregister: self-service (user thao tác token CHÍNH MÌNH) → gate bằng **bearer (đã login) + row-level self-scope**, KHÔNG cần cap nghiệp vụ (`../06 §2.3`).

### 6.2 Token / credential threat model (`../06 §5.3`)

| Threat | Vector | Chặn (EPIC-D) |
|---|---|---|
| Spoof register cho user khác | client gửi `user=<nạn nhân>` | **D2:** server ÉP `user=frappe.session.user` (KHÔNG nhận `user`); self-scope (D7) → không tạo/sửa token user khác |
| Token leak | `fcm_token` user A lộ | push KHÔNG chứa secret (chỉ doctype/name/VI text); lộ token = tối đa nhận push trùng, KHÔNG leo quyền |
| Đánh cắp server-key | lộ FCM SA | **D3:** creds CHỈ trong `site_config`, KHÔNG qua API/log/repo; rò = xoay key Firebase |
| Token chết gửi rác | token unregister | **D5:** invalidate-on-401 tự `enabled=0` |
| Spam register | 1 user spam nhiều token | **D6:** dedup theo `fcm_token` (D2) + rate-limit register |

### 6.3 Audit NĐ98 (D2/D7)

- **register/unregister_device_token** PHẢI sinh **audit trail** (NĐ98 — truy xuất ai-đăng-ký-thiết-bị-nào-khi-nào). DocType bất biến (`track_changes=1` + Frappe doc metadata create/modify/owner) + `log_audit_event`; cần chain mạnh hơn → bồi SHA-256 chain `utils/lifecycle.py` theo pattern action nghiệp vụ.
- **Notification Log (kênh 1) GIỮ là bằng chứng gửi** — push KHÔNG thay (`../06 §3.1/§5.4`). Bản ghi "đã thông báo" ở Notification Log, KHÔNG phụ thuộc FCM nhận hay không.

### 6.4 DONE-gate spec-contract (LL-BE-42..49)

- register/unregister cần **bearer** → guest/no-token = **dispatcher-403** (trip trước handler). Lỗi nghiệp vụ (token không hợp lệ) = **in-handler HTTP-200 + Error envelope** (KHÔNG raise→4xx) — đồng pattern EPIC-C. yaml response 200 `oneOf[Created|Error]`.

---

## 7. Tham chiếu

- **Spec gốc (HỢP ĐỒNG):** [`../06-push-fcm.md`](../06-push-fcm.md) (§2 DocType · §3 MAP 7-event · §4 payload/deep-link · §5 threat/audit) · **ADR:** [`../ADR-MOBILE-002.md`](../ADR-MOBILE-002.md) (FCM Admin SDK direct, KHÔNG relay)
- **Roadmap tổng:** [`../13-be-completion-roadmap.md §6`](../13-be-completion-roadmap.md) (EPIC-D) · §4.3 (B3 device-token gap) · §8 (Blockers AUTO/HARD-STOP)
- **EPIC chéo:** **EPIC-B** [`EPIC-B-auth-provisioning.md`](./EPIC-B-auth-provisioning.md) (B3 device-token + bearer→`set_user`) · **EPIC-C** [`EPIC-C-api-contract.md`](./EPIC-C-api-contract.md) (oneOf+discriminator pattern cho D4) · **EPIC-G** [`EPIC-G-golive-hardening.md`](./EPIC-G-golive-hardening.md) (FCM creds cùng nhóm knob site_config) · **EPIC-V** [`EPIC-V-codegen-verification.md`](./EPIC-V-codegen-verification.md) (codegen D4 path)
- **Engine (chèn kênh #3):** `assetcore/services/notifications.py::_dispatch:366` (7 call-site `:452 :498 :562 :627 :791 :931 :1116`; E3 `:506→:562`) · `assetcore/utils/helpers.py:59` (`_safe_sendmail` fail-safe pattern)
- **Hooks wiring:** `assetcore/hooks.py:270` (E3 Incident after_insert) · `:390/:397` (query/has_permission hiện chỉ Incident — D7 thêm AC Mobile Device Token)
- **RBAC SSoT:** `assetcore/permissions.py:46/90/188` (vendor `_VENDOR_ROLE` + self-scope pattern) · `assetcore/services/shared/rbac.py`
- **OpenAPI STUB:** `docs/mobile/openapi/assetcore-mobile.openapi.yaml:1565` (registerDeviceToken) · `:1582` (unregisterDeviceToken) · `assetcore/tests/test_mobile_oas.py` (`_STUB_PATHS`)
- **Go-live runbook FCM creds:** [`../10-deploy-ops.md §4`](../10-deploy-ops.md)
- **Security toàn cảnh mobile:** [`../08-security-compliance.md`](../08-security-compliance.md) (T4 token storage) · [`../ADR-MOBILE-004.md`](../ADR-MOBILE-004.md)
- **WHO HTM / NĐ98:** push = kênh cảnh báo vận hành stage 5 Maintenance (rút ngắn "thời gian tới hiện trường"); NĐ98 audit register/unregister = thao tác có hệ quả an ninh → record bắt buộc (`../06 §0.4`)

---

## 8. Rủi ro

| # | Rủi ro | Tác động | Giảm thiểu |
|---|---|---|---|
| R1 | **Phụ thuộc EPIC-B chưa đóng** — bearer→`set_user` chưa e2e reach `api/mobile/v1` | register fail trên cloud → flow-6 KHÔNG chạy | Chốt EPIC-B B1 (OAuth Client preflight ready) + B3 trước khi D2/D7 chạy THẬT; test D2 dùng session giả lập (không cần bearer thật) |
| R2 | **FCM creds chưa set (D3 HARD-STOP USER)** | D5/D6 KHÔNG gửi push thật (chỉ mock test xanh) | Test impl dùng mock FCM (xanh KHÔNG cần creds); go-live block cho tới D3 done; runbook `../10 §4` |
| R3 | **Library FCM chưa chọn** (firebase-admin vs REST tự-ký SA) | risk lệch impl D5; BE KHÔNG cài lib round doc | Quyết Phase E kèm test; nếu firebase-admin → install = **[HARD-STOP USER]** (BE KHÔNG cài lib) |
| R4 | **Kênh #3 lỗi làm vỡ in-app/email** | event chính (báo hỏng) miss notification | **BẮT BUỘC** try/except + `log_error` quanh push (D6 §1.3); regression test kênh 1+2 (D6 acceptance) — RED nếu push raise lan ra |
| R5 | **gunicorn `--preload` staleness** — sửa `notifications.py`/`api/mobile` chỉ live `run-tests`, CHƯA live HTTP | push không bắn trên prod dù test xanh | `bench restart`/reload = **[HARD-STOP USER]** sau D4/D6/D7 (LL-DEPLOY-01/04); doc nêu rõ, BE KHÔNG chạy |
| R6 | **Token spoof / leak** | leo quyền / spam | D2 ÉP `user=session` + self-scope (D7) + rate-limit (D6) + invalidate-on-401 (D5) — §6.2 |
| R7 | **double-notify nếu chèn push per-event** thay vì 1 điểm | push trùng | Chèn DUY NHẤT trong `_dispatch:366` (D6), KHÔNG sửa 7 call-site (§3.2) |
| R8 | **migrate DocType + bust cache chưa chạy** | RBAC hook/DocType không live HTTP | `bench migrate` = **[HARD-STOP USER]** (Blocker §8 roadmap #2); doc nêu, BE KHÔNG chạy |
