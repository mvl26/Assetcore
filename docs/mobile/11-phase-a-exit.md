# 11 — Phase-A EXIT GATE: Traceability matrix · Phase-B prereqs · Checklist go/no-go A→B

| Mục | Giá trị |
|---|---|
| Initiative | **AssetCore Mobile** — backend-for-mobile (repo này) + APK native (repo riêng) |
| Vai trò file | **Cổng thoát (exit gate) Phase A** — traceability 6 flow MVP + gom Phase-B prereqs + checklist go/no-go A→B |
| Phase | **PHASE A — Kiến trúc & Feasibility** (đóng phase) |
| Owner | BA Lead + System Architect (mobile) |
| Trạng thái docs | Stable (exit-ready) |
| Cập nhật | 2026-06-09 |

> **Đây là tài liệu CHỐT Phase A.** Mục đích: chứng minh hợp đồng mobile-BE đã **truy vết được đầu-cuối** (màn → endpoint thật → capability → operationId → offline-class → push-event → trạng thái STUB), gom mọi **điều kiện tiên quyết Phase B** đang rải rác thành 1 danh sách, và đưa ra **checklist go/no-go A→B đo được** để quyết định mở Phase B.
> Mọi `file:line`/`operationId` đã verify tại source **Frappe v15.107.2** (2026-06-09). KHÔNG bịa, KHÔNG sao chép lại nội dung nguồn — chỉ TRỎ NGƯỢC `file:section`.

> **Chỉ mục docset:** [`00-overview.md`](./00-overview.md) · [`01-architecture.md`](./01-architecture.md) · [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) · [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`04-api-contract.md`](./04-api-contract.md) · [`05-personas-mvp.md`](./05-personas-mvp.md) · [`06-push-fcm.md`](./06-push-fcm.md) · [`07-offline-sync.md`](./07-offline-sync.md) · [`08-security-compliance.md`](./08-security-compliance.md) · [`09-native-repo-guide.md`](./09-native-repo-guide.md) · [`10-deploy-ops.md`](./10-deploy-ops.md) · [`12-phase-b-preflight.md`](./12-phase-b-preflight.md) · [`README.md`](./README.md) · [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)

---

## 0. Mục tiêu / Out-of-scope / Lý do cấp số 11

### 0.1 Mục tiêu (in-scope)

1. **Traceability matrix 6 flow MVP** (§1): mỗi flow D-MVP truy được đầy đủ chuỗi `màn → endpoint (file:line @source) → capability (rbac.py) → operationId (OpenAPI) → offline-class → push-event → STUB-status`.
2. **Phase-B prereqs/blocker hợp nhất** (§2): gom các điều kiện tiên quyết đang rải rác (02 feasibility · 03 §4 OAuth Client · 08 §4 security · 10 runbook) thành **1 danh sách** — mỗi mục TRỎ NGƯỢC `file:section` nguồn.
3. **Checklist go/no-go A→B đo được** (§3): tick-box kiểm chứng được, tách rõ **đã-đạt (Phase A)** vs **chờ-USER (Phase B)**.
4. **KPI / acceptance exit** (§4).

### 0.2 Out-of-scope (KHÔNG làm ở doc này)

| KHÔNG làm | Vì sao |
|---|---|
| Impl bất kỳ code/endpoint/DocType | doc-only; impl thuộc Phase C/D/E |
| Sửa `openapi/*.yaml` (path / operationId / security / schema) | OpenAPI đã đóng băng ở A10 (15/15 operationId) + A5 (2 device-token); doc này CHỈ ĐỌC |
| Bồi 9 path nghiệp vụ STUB | giữ STUB cho Phase C (bồi request/response schema thật) |
| Thêm ErrorCode / capability mới | `CAPABILITY_MAP` = SSoT (`rbac.py`); dựng "hệ quyền thứ 2" bị cấm (`ADR-MOBILE-001 b`) |
| Thực thi go-live (OAuth Client / allow_cors / host / FCM / reload) | HARD-STOP USER (`10-deploy-ops.md §0.1`) |
| Sao chép lại nội dung 02/03/08/10 | chỉ TRỎ NGƯỢC `file:section` (chống drift + nhân đôi) |

### 0.3 Lý do cấp số `11`

Theo convention chống-trùng số ở [`00-overview.md §6`](./00-overview.md): số đã cấp = `00`…`10` (overview→deploy-ops). **Số kế tiếp khả dụng = `11`** (KHÔNG ghi đè `00-10`). File này cấp `11-phase-a-exit.md`; sau khi cấp, **số kế tiếp = `12-…`**. ADR vẫn theo dãy riêng `ADR-MOBILE-<NNN>` (`001-004` đã cấp) — doc này KHÔNG sinh ADR mới (không có quyết định kiến trúc mới, chỉ tổng hợp).

---

## 1. Traceability matrix — 6 flow MVP (D-MVP)

> **Nguồn chân lý từng cột:**
> - **Màn:** [`05-personas-mvp.md §3`](./05-personas-mvp.md) (bảng MÀN↔API) + §4 (offline) + §5 (cap).
> - **Endpoint + `file:line`:** verify @source `assetcore/api/*.py` (grep `^def …`, Frappe v15.107.2, 2026-06-09).
> - **Capability:** `assetcore/services/shared/rbac.py` `CAPABILITY_MAP` — phiên bản `v97.c30c69b8974d` (bench-verified). KHÔNG thêm cap. **GUARD máy-đọc (A14):** ánh xạ endpoint→capability + binding `(DocType, ptype)` của matrix này được **kiểm chứng tự động** bởi `assetcore/tests/test_mobile_capability_map.py` (`TC-MOB-CAP-01..06`) — introspect `CAPABILITY_MAP` (SSoT) ⇒ cap thiếu / đổi-binding / cap-creep / version-drift = hard-fail. KHÔNG còn "manually verified".
> - **operationId:** [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (15/15 path, A10) — convention [`04-api-contract.md §8.1`](./04-api-contract.md). Contract-integrity (0 dangling `$ref` + orphan allow-list RESERVED, codegen-able) = [`04-api-contract.md §8.2`](./04-api-contract.md) (A12, guard `TC-MOB-OAS-09/10`).
> - **Offline-class:** [`05-personas-mvp.md §4`](./05-personas-mvp.md) (3 nhãn) → đặc tả [`07-offline-sync.md §1`](./07-offline-sync.md).
> - **Push-event:** [`06-push-fcm.md §3.2`](./06-push-fcm.md) (E1-E5 + SLA) + §4.2 (deep-link).
> - **STUB-status:** trạng thái trong OpenAPI (auth = FILLED A2; 9 nghiệp vụ + 2 device-token = STUB, schema bồi Phase C/E).
>
> **A13 — error-response coverage (KHÔNG đổi STUB-status; chỉ thêm response máy-đọc).** Cột STUB-status ở matrix dưới phản ánh `data`/`requestBody` (200-schema) — KHÔNG đổi: 9 nghiệp vụ + 2 device-token VẪN STUB tới Phase C/E. NGOÀI ra, A13 đã wire **error-response declare tường minh** vào OpenAPI (không thuộc cột STUB-status):
> - **`401`→`Unauthorized401`** lên **toàn bộ 12 path MVP** (10 nghiệp vụ STUB `resolve_qr_token`/`get_asset_scan_info`/`get_asset`/`report_incident`/`create_pm_work_order`/`create_repair_work_order`/`create_calibration`/`list_pm_work_orders`/`list_repair_work_orders`/`list_incidents` + 2 device-token đã có từ A5) — bearer hết hạn → refresh/re-auth ([`ADR-MOBILE-001.md (e)`](./ADR-MOBILE-001.md) · [`04-api-contract.md §4/§5`](./04-api-contract.md)).
> - **`429`→`RateLimited429`** lên **ĐÚNG 2 path `@rate_limit` THẬT**: `resolve_qr_token` (`imm00.py:311`) + `get_asset_scan_info` (`imm00.py:354`). KHÔNG path khác (chỉ 2 GET QR có `@rate_limit` MVP).
> - **3 auth path** (authorize/get_token/revoke) GIỮ NGUYÊN (302/200 — Frappe core, KHÔNG `@rate_limit` ⇒ KHÔNG 429; [`08-security-compliance.md §1 T1`](./08-security-compliance.md)). **404/422** GIỮ Phase C (phụ thuộc requestBody/asset-lookup). Guard: `TC-MOB-OAS-11` ([`04-api-contract.md §8.2`](./04-api-contract.md)).

### Flow 1 — Đăng nhập OAuth2 (MVP #1)

| Màn (05 §) | Endpoint (`/api/method/<dotted>`) | `file:line` @source | Capability (rbac.py) | operationId | offline-class | push-event | STUB-status |
|---|---|---|---|---|---|---|---|
| `LoginView` › authorize | `frappe.integrations.oauth2.authorize` | `frappe/integrations/oauth2.py:75` | — (allowed_roles OAuth Client) | `authorizeOAuth` | online-only | — | **FILLED** (A2 — parameters+responses) |
| `LoginView` › get_token | `frappe.integrations.oauth2.get_token` | `frappe/integrations/oauth2.py:124` | — (PKCE S256) | `getOAuthToken` | online-only | — | **FILLED** (A2 — requestBody+responses) |
| `LoginView` › revoke (logout) | `frappe.integrations.oauth2.revoke_token` | `frappe/integrations/oauth2.py:145` | — (RFC 7009) | `revokeOAuthToken` | online-only | — | **FILLED** (A2 — requestBody+responses) |

> Auth = WIRE provider Frappe (KHÔNG tự viết OAuth — `D-AUTH`). Quyền THỰC vào sau khi bearer→`set_user`→RBAC (§Flow 2-5). Chi tiết sequence a→f: [`03-auth-oauth2.md §1`](./03-auth-oauth2.md).

### Flow 2 — Quét QR → hồ sơ thiết bị (MVP #2)

| Màn (05 §) | Endpoint | `file:line` @source | Capability (rbac.py) | operationId | offline-class | push-event | STUB-status |
|---|---|---|---|---|---|---|---|
| `QrScanView` → resolve | `assetcore.api.imm00.resolve_qr_token` | `api/imm00.py:312` | `asset.read` → `("AC Asset","read")` | `resolveQrToken` | read-cache-ok (decode client-side) | — | **STUB** (Phase C) |
| `AssetScanInfoView` | `assetcore.api.imm00.get_asset_scan_info` | `api/imm00.py:355` | `asset.read` | `getAssetScanInfo` | read-cache-ok | E4 calibration_due deep-link đích (`06 §4.2`) | **STUB** (Phase C) |
| `AssetDetailView` | `assetcore.api.imm00.get_asset` | `api/imm00.py:271` | `asset.read` (IDOR-guard vendor) | `getAsset` | read-cache-ok | — | **STUB** (Phase C) |

> `resolve_qr_token` (`imm00.py:312`) + `get_asset_scan_info` (`imm00.py:355`) cùng gate `rbac.require("asset.read")`; `resolve_qr_token` thêm `@rate_limit(30/60s/IP)` (BR-00-29). `get_asset` (`imm00.py:271`) permission-aware + `assert_vendor_can_access` (IDOR). Cờ overdue server-flag (`pm_overdue`/`calibration_overdue`) đính kèm response — FE CHỈ render cờ (`overdue_server_flag_ssot`).

### Flow 3 — Báo hỏng (MVP #3)

| Màn (05 §) | Endpoint | `file:line` @source | Capability (rbac.py) | operationId | offline-class | push-event | STUB-status |
|---|---|---|---|---|---|---|---|
| `IncidentCreateView` | `assetcore.api.imm12.report_incident` | `api/imm12.py:71` | `corrective.create` → `("Incident Report","create")` | `reportIncident` | idempotent-write-needed | **E3** `incident_created` (`notify_incident_created` def `notifications.py:506` → fan-out `:562`) → deep-link `assetcore://incident/<name>` | **Phase-C-requestBody** (rời STUB — requestBody THẬT 4 field, `04 §8.3`; response `data` 200 vẫn STUB → Phase-C kế) |

> `report_incident` POST-only, gate `corrective.create` qua `_can_report()` (`_CAP_REPORT="corrective.create"`, `imm12.py:55`) TRƯỚC handle (parity 3-tier; persona `corrective.read-only` → 403 VI sạch, no-leak — `05 §1.3`). `source=mobile` (coerce) → vẫn emit lifecycle + audit (NĐ98). Idempotency-key = việc Phase E (`07 §2`).
>
> **C-REQBODY-REPORTINCIDENT (Phase-C):** path **đầu tiên rời STUB** — bồi `requestBody` THẬT `required:[asset, incident_type, severity, description]` (Select-canonical enum @`incident_report.json`; `source` server-coerce NGOÀI body — `imm12.py:83`). Hợp đồng + bảng field: [`04-api-contract.md §8.3`](./04-api-contract.md). Response surface `200/401/403` GIỮ nguyên (chỉ THÊM requestBody). Guard `TC-MOB-OAS-13`.

### Flow 4 — Yêu cầu PM / CM / Hiệu chuẩn (MVP #4)

| Màn (05 §) | Endpoint | `file:line` @source | Capability (rbac.py) | operationId | offline-class | push-event | STUB-status |
|---|---|---|---|---|---|---|---|
| `PMWorkOrderCreateView` | `assetcore.api.imm08.create_pm_work_order` | `api/imm08.py:91` | `pm.create` → `("PM Work Order","create")` | `createPmWorkOrder` | idempotent-write-needed | **E1** assignment (`notify_assignment` def `notifications.py:416` → fan-out `:452`) → `assetcore://wo/pm/<name>` | **STUB** (Phase C) |
| `CMCreateView` | `assetcore.api.imm09.create_repair_work_order` | `api/imm09.py:36` | `repair.create` → `("Asset Repair","create")` | `createRepairWorkOrder` | idempotent-write-needed | **E1** assignment → `assetcore://wo/cm/<name>` | **STUB** (Phase C) |
| `CalibrationCreateView` | `assetcore.api.imm11.create_calibration` | `api/imm11.py:90` | `calibration.create` → `("IMM Asset Calibration","create")` | `createCalibration` | idempotent-write-needed | **E4** calibration_due (`notify_calibration_due` def `notifications.py:578` → fan-out `:627`) → `assetcore://asset/<asset_name>` | **STUB** (Phase C) |

> Cả 3 POST-only, gate `rbac.require("<domain>.create")` ở api-tier (`imm08.py:92` · `imm09.py:40` · `imm11.py:95`). Push channel #3 chèn 1-điểm tại `_dispatch:366` (`06 §3.3`) — mọi event tự có push, in-app/email GIỮ NGUYÊN (`06 §3.1`). Deep-link = HỢP ĐỒNG đề xuất, route native chốt Phase D (`06 §4.2`).

### Flow 5 — "Phiếu của tôi" (MVP #5)

| Màn (05 §) | Endpoint | `file:line` @source | Capability (rbac.py) | operationId | offline-class | push-event | STUB-status |
|---|---|---|---|---|---|---|---|
| `MyWorkOrdersView` › PM | `assetcore.api.imm08.list_pm_work_orders` | `api/imm08.py:28` | `pm.read` → `("PM Work Order","read")` | `listPmWorkOrders` | read-cache-ok | — | **Phase-C-list-read** (pagination param + 200→`WorkOrderList` `data.data[]`; `04 §8.4`) |
| `MyWorkOrdersView` › CM | `assetcore.api.imm09.list_repair_work_orders` | `api/imm09.py:21` | `repair.read` → `("Asset Repair","read")` | `listRepairWorkOrders` | read-cache-ok | — | **Phase-C-list-read** (pagination param + 200→`WorkOrderList` `data.data[]`; `04 §8.4`) |
| `MyWorkOrdersView` › Báo hỏng | `assetcore.api.imm12.list_incidents` | `api/imm12.py:197` | `corrective.read` → `("Incident Report","read")` | `listIncidents` | read-cache-ok | — | **Phase-C-list-read** (pagination param + 200→`IncidentList` `data.items[]`; `04 §8.4`) |

> **C-LISTREAD (Phase-C list-read):** 3 list path **rời STUB** (nối tiếp `report_incident` write-direction) — bồi **pagination query-param** (`page`/`page_size` cả 3 + `filters` JSON-string imm08/09 + `status`/`severity`/`asset`/`open` imm12, đúng signature LIVE) + **200→list-envelope THẬT**. rows-key PHÂN BIỆT @source: imm08/09 → `data.data[]` (`WorkOrderListEnvelope`), imm12 → `data.items[]` (`IncidentListEnvelope`) — quyết định [`ADR-MOBILE-001 (g)`](./ADR-MOBILE-001.md) + bảng [`04-api-contract.md §6.2/§8.4`](./04-api-contract.md). Response `401/403` GIỮ nguyên; KHÔNG `requestBody` (GET). Guard `TC-MOB-OAS-14`. **Known-gap:** ~~scope `reported_by`~~ **ĐÓNG cho `listIncidents`** qua param `mine=1` (`IncidentMine`, [ADR-MOBILE-015](./ADR-MOBILE-015.md)); còn lại Phase-E — chuẩn-hoá 1 rows-key + scope `assigned_to` (PM/CM).

> 3 list permission-aware (scope theo user; `count==rows` invariant — `asset_list_count_drill_technician`). Caps `*.read` resolve qua DocPerm read theo user (`05 §5`).

### Flow 6 — Push (MVP #6)

| Màn (05 §) | Endpoint | `file:line` @source | Capability (rbac.py) | operationId | offline-class | push-event | STUB-status |
|---|---|---|---|---|---|---|---|
| `(APK lifecycle)` đăng ký token | `assetcore.api.mobile.v1.register_device_token` | *(CHƯA impl — Phase E; spec `06 §2`)* | self-scope (KHÔNG cap mới; bám DocPerm `AC Mobile Device Token` — `06 §2.3`) | `registerDeviceToken` | online-only | (kênh push — không nhận push để đăng ký) | **STUB** (Phase E — name đóng băng A5) |
| `(APK logout/gỡ)` thu hồi token | `assetcore.api.mobile.v1.unregister_device_token` | *(CHƯA impl — Phase E; spec `06 §2.5`)* | self-scope | `unregisterDeviceToken` | online-only | (kênh push) | **STUB** (Phase E — name đóng băng A5) |

> Push là **kênh thứ 3** chèn tại `_dispatch` (`06 §3`), KHÔNG endpoint nghiệp vụ riêng để "nhận". 2 endpoint trên = vòng đời device-token (register/unregister) — `file:line` CHƯA tồn tại (đúng kỳ vọng: Phase E impl); name + operationId đã đóng băng A5 để codegen ổn định. Cơ chế = FCM Admin SDK trực tiếp (`ADR-MOBILE-002`).

### 1.7 Đối soát tổng (acceptance matrix)

- **6/6 flow MVP** đều có ≥1 dòng truy vết đầy đủ 7 cột. ✅
- **9 endpoint nghiệp vụ verify @source** (imm00×3, imm12×2, imm08×2, imm09×2, imm11×1) — `file:line` khớp grep `^def …` (xem §1 từng flow). ✅
- **3 endpoint auth** (oauth2 authorize/get_token/revoke) verify @source `frappe/integrations/oauth2.py:75/124/145`. ✅
- **15/15 operationId** trong matrix khớp 15 path `openapi/assetcore-mobile.openapi.yaml` (3 auth FILLED + 6 nghiệp vụ STUB + `report_incident` Phase-C-requestBody + 3 list Phase-C-list-read + 2 device-token STUB) — 0 bịa, 0 thừa. ✅
- **A13 error-response coverage** (máy-đọc, không đổi STUB-status): 12/12 path MVP declare `401`; ĐÚNG 2 path `@rate_limit` declare `429`; *(tại A13)* 0 path declare 404/422. Guard `TC-MOB-OAS-11` GREEN; orphan 11→10 (RateLimited429 hết orphan). ✅
- **C-REQBODY (Phase-C, write-direction):** `report_incident` rời STUB — `requestBody` THẬT 4 field (`04 §8.3`). Guard `TC-MOB-OAS-13` GREEN; *(tại C-REQBODY)* orphan GIỮ 10. ✅
- **C-LISTREAD (Phase-C, read-direction):** 3 list path rời STUB — pagination param + 200→list-envelope (rows-key PHÂN BIỆT `data.data[]` vs `data.items[]`; `04 §6.2/§8.4` + `ADR-MOBILE-001 (g)`). Guard `TC-MOB-OAS-14` GREEN; orphan 10→9 (`PaginatedListEnvelope` tách 2 envelope, hết orphan). Known-gap Phase-E: chuẩn-hoá 1 rows-key. ✅
- **G-REQBODY (Phase-C — đóng 4 contract-gap codegen `report_incident`):** (1) `requestBody.content` oneOf `application/json`+`application/x-www-form-urlencoded` (Frappe RPC `form_dict`); (2) `403` dual-shape `ReportIncidentForbidden` `oneOf [Error, FrappeRawError]` (in-handler cap-403 HTTP-200+Error `imm12.py:96` ≠ dispatcher-403 HTTP-403+FrappeRawError `__init__.py:876`); (3) `04 §9` vd Guest 401→**403**; (4) wire `404`→`NotFound404` (asset∄ `imm12.py:361`) + `422`→`Unprocessable422` (BR-12-01 `imm12.py:359`) + `200`→`ReportIncidentCreated` (`ReportIncidentResponse {name,status,severity}` `imm12.py:410`). Guard `TC-MOB-OAS-11/12/13` GREEN; **orphan 9→7** (`NotFound404`/`Unprocessable422` rời RESERVED — `04 §8.2`). Status-set `report_incident` = `[200,401,403,404,422]`. ✅

---

## 2. Phase-B prereqs / blocker — danh sách hợp nhất

> Mục này GOM mọi điều kiện tiên quyết/blocker Phase B đang rải rác khắp docset thành **1 danh sách**. Mỗi mục **TRỎ NGƯỢC `file:section` nguồn — KHÔNG sao chép lại nội dung** (chống drift). **Mọi mục đều HARD-STOP USER** (DB write / `site_config` / nginx / reload) — agent KHÔNG thực thi.

| # | Điều kiện tiên quyết / blocker | Hiện trạng (verified) | Nguồn (file:section) | Chủ thể |
|---|---|---|---|---|
| B-1 | **Tạo `OAuth Client`** (grant=Authorization Code · response_type=Code · PKCE-ready · `redirect_uris`=native-scheme `assetcore://oauth/callback` · `allowed_roles`=field-tech least-priv) — **token-response CONTRACT nay GUARDED** (B1: `OAuthError400` + get_token 200-keys + revoke empty-200 source-characterized → `TC-MOB-OAUTH-TOKEN-*`); **provisioning record vẫn HARD-STOP USER** | `OAuth Client` count = **0**; pre-flight `verify_oauth_client()` → `ready=false` | [`03-auth-oauth2.md §4`](./03-auth-oauth2.md) (checklist field thật) · **[`03-auth-oauth2.md §2 / §2.3.1`](./03-auth-oauth2.md) (token-response passthrough B1)** · [`04-api-contract.md §5b`](./04-api-contract.md) · [`02-deploy-feasibility.md §7.4`](./02-deploy-feasibility.md) · runbook [`10-deploy-ops.md §1`](./10-deploy-ops.md) · pre-flight verifier [`12-phase-b-preflight.md`](./12-phase-b-preflight.md) | USER |
| B-2 | **Bật CORS** `site_config.allow_cors` = LIST origin tường minh (CẤM `'*'` ở prod vì Frappe echo `Allow-Credentials:true`) | `allow_cors = None` (TẮT) | [`02-deploy-feasibility.md §3 / §7.1`](./02-deploy-feasibility.md) · [`08-security-compliance.md §4 (b) / §1 T3`](./08-security-compliance.md) · runbook [`10-deploy-ops.md §2`](./10-deploy-ops.md) | USER |
| B-3 | **Public HTTPS host** (reverse-proxy nginx + TLS + domain + HTTP→HTTPS redirect) cho OAuth redirect + bearer-over-HTTPS + QR deep-link | nginx dev HTTP:80 `server_name` rỗng | [`02-deploy-feasibility.md §4 / §7.2`](./02-deploy-feasibility.md) · [`08-security-compliance.md §4 (b) / §1 T7`](./08-security-compliance.md) · runbook [`10-deploy-ops.md §3`](./10-deploy-ops.md) | USER |
| B-4 | **QR deep-link host** `site_config.assetcore_qr_base_url` = host HTTPS công khai (nếu không, camera điện thoại KHÔNG mở deep-link) | `assetcore_qr_base_url = None` | [`02-deploy-feasibility.md §4.2 / §7.3`](./02-deploy-feasibility.md) · runbook [`10-deploy-ops.md §3`](./10-deploy-ops.md) | USER |
| B-5 | **Rate-limit OAuth2 tầng nginx** (`limit_req` cho `/api/method/frappe.integrations.oauth2.*`) — Frappe core KHÔNG có rate-limit cho oauth2 (T1 brute-force) | `grep rate_limit` trên oauth2.py = **0** | [`08-security-compliance.md §1 T1 / §4 (b)`](./08-security-compliance.md) · `ADR-MOBILE-004 (a)` · runbook [`10-deploy-ops.md §3b`](./10-deploy-ops.md) | USER |
| B-6 | **FCM server credentials** trong `site_config` (`fcm_service_account_path` / `fcm_project_id`, NGOÀI repo, KHÔNG commit/log/API) — cho kênh push #3 (Phase E) | CHƯA có; relay Frappe Cloud KHÔNG air-gapped | [`02-deploy-feasibility.md §0 / §7.7`](./02-deploy-feasibility.md) · [`06-push-fcm.md §5.2`](./06-push-fcm.md) · `ADR-MOBILE-002` · runbook [`10-deploy-ops.md §4`](./10-deploy-ops.md) | USER |
| B-7 | **Reload gunicorn + `bench migrate`** (nếu đổi cap) + reload nginx — `--preload` ⇒ `site_config`/cap-set chỉ LIVE ở HTTP SAU reload (+ bust `ac_caps::*`) | gunicorn `--preload` đang chạy | [`02-deploy-feasibility.md §8.8`](./02-deploy-feasibility.md) · [`10-deploy-ops.md §6.2 (reload) / §0`](./10-deploy-ops.md) | USER |
| B-8 | **Decision: scope ↔ capability** — giữ scope coarse (`all openid`, quyền vẫn đúng nhờ RBAC) HAY map scope→capability-group | scope coarse; quyền THỰC = DocPerm/capability theo user | [`02-deploy-feasibility.md §7.5`](./02-deploy-feasibility.md) · [`03-auth-oauth2.md §3.2`](./03-auth-oauth2.md) · `ADR-MOBILE-004 (b)` | USER (quyết định) — Phase A khuyến nghị giữ coarse |

> **Lưu ý:** B-6/B-7 phục vụ Phase E (push) nhưng phải provision ở Phase B (HARD-STOP USER) nên gom tại đây. B-8 là **quyết định** (không phải thao tác) — Phase A đã khuyến nghị giữ scope coarse vì RBAC capability là gate cuối (1 SSoT — `ADR-MOBILE-001 b`).

---

## 3. Checklist go/no-go A→B (đo được — tick-box)

> Mỗi dòng là điều kiện **kiểm chứng được**. **(A) đã-đạt = Phase A self-verified** (agent tick được, có bằng chứng). **(B) chờ-USER = Phase B HARD-STOP** (agent KHÔNG tick hộ — chỉ liệt kê; USER tick khi thực thi xong).

### 3.1 (A) ĐÃ-ĐẠT — Phase A (self-verified, có bằng chứng)

- [x] **A-1** 13 chương đánh số (`00`–`12`) + 4 ADR (`001`–`004`) + README đầy đủ — `ls docs/mobile/*.md` = 18 file (13 chương `00`–`12` + README + 4 ADR). **GUARDED máy-đọc (A15):** index↔filesystem parity + ADR registration kiểm chứng tự động bởi `assetcore/tests/test_mobile_docset.py` (`TC-MOB-DOC-01..03`) — đếm động bằng glob (KHÔNG hardcode), thêm/xoá chương mà quên cập nhật index §1 = test ĐỎ.
- [x] **A-2** 3 quyết định nền `D-AUTH` / `D-MVP` / `D-STACK` chốt + in nguyên tại [`00-overview.md §2`](./00-overview.md) (KHÔNG re-litigate).
- [x] **A-3** OpenAPI **15/15 path CÓ `operationId`** (camelCase verbNoun, unique, codegen-able) — convention [`04-api-contract.md §8.1`](./04-api-contract.md); guard `test_mobile_oas` **GREEN** (11 test — A12/A13 mở rộng từ 8).
- [x] **A-4** **9 endpoint nghiệp vụ + 3 auth** verify @source `file:line` thật (Frappe v15.107.2) — matrix §1, 0 bịa.
- [x] **A-5** Capability mỗi flow khớp `CAPABILITY_MAP` (`v97.c30c69b8974d`) — **guarded `TC-MOB-CAP-*` (`test_mobile_capability_map.py`)** thay cho "bench-verified manual": 10 endpoint MVP ↔ matrix §1 ↔ SSoT `rbac.py` được kiểm chứng tự động (binding `(DocType, ptype)` khớp · 0 cap mới · `len==97` · version đóng băng). KHÔNG thêm cap, KHÔNG hệ quyền thứ 2 (`ADR-MOBILE-001 b`). Mức guard = **matrix↔SSoT binding** (KHÔNG re-implement gate; list-endpoint gate nằm trong service/handle là CHỦ Ý).
- [x] **A-6** Offline-class per-màn (3 nhãn `read-cache-ok`/`idempotent-write-needed`/`online-only`) gán đủ — [`05 §4`](./05-personas-mvp.md) → đặc tả [`07-offline-sync.md`](./07-offline-sync.md) + `ADR-MOBILE-003`.
- [x] **A-7** Push 6-event → FCM (kênh #3 tại `_dispatch`) đặc tả + deep-link native — [`06-push-fcm.md`](./06-push-fcm.md) + `ADR-MOBILE-002` (in-app/email GIỮ NGUYÊN).
- [x] **A-8** Security threat model 7 mối (T1–T7) + NĐ98 audit-from-mobile — [`08-security-compliance.md`](./08-security-compliance.md) + `ADR-MOBILE-004`.
- [x] **A-9** **Mọi blocker Phase B đã liệt kê (§2, B-1…B-8) + chủ thể = USER** — không còn prereq rải rác chưa gom.
- [x] **A-10** Handoff repo native (skeleton + sinh client từ OpenAPI + ENV + OAuth wiring) — [`09-native-repo-guide.md`](./09-native-repo-guide.md).
- [x] **A-11** Runbook go-live numbered steps (§1–§5) + checklist + smoke curl + rollback — [`10-deploy-ops.md`](./10-deploy-ops.md).
- [x] **A-12** Doc-only no-regression: `test_oas_generator` (49) + `test_oas_signatures` (11) + `test_mobile_oas` (11) + `test_mobile_preflight` (9) **GREEN** (KHÔNG đụng code/yaml path/operationId).
- [x] **A-14** Endpoint↔capability binding GUARD máy-đọc: `test_mobile_capability_map` (`TC-MOB-CAP-01..06`) **GREEN** (6 test) — 10 endpoint MVP ↔ matrix §1 ↔ SSoT `rbac.py`; binding `(DocType, ptype)` khớp · 0 cap mới (`len==97`) · version đóng băng `v97.c30c69b8974d` (drift doc↔source = test ĐỎ). Claim A-5 'manually verified' → 'guarded'.
- [x] **A-15** **Docset-integrity GUARDED (`test_mobile_docset` 5/5)** — `assetcore/tests/test_mobile_docset.py` (`TC-MOB-DOC-01..05`) **GREEN** (5 test): (1) FS↔index parity 13 chương `NN-*.md` ↔ §1 (đếm động glob, 0 mồ côi/0 treo); (2) ADR registration 4 ADR + openapi yaml liệt kê/tham chiếu README; (3) link-health — mọi link `./`/`../` resolve (baseline 405 link / 0 broken); (4) no-placeholder NGOÀI code-fence (`TODO/TBD/FIXME/XXX/<...>/lorem`); (5) mỗi chương non-empty + ≥1 H1. Biến tiêu chí exit "docset đầy đủ + 0 broken link" từ prose thành claim máy-đọc — đóng kín tầng **navigation** (đối xứng tầng **contract**: `test_mobile_oas`/`test_mobile_capability_map`/`test_mobile_preflight`). Edit Phase B/C/D phá parity/link/placeholder = test ĐỎ.

### 3.2 (B) CHỜ-USER — Phase B (HARD-STOP — agent KHÔNG tick)

- [ ] **B-1** Tạo `OAuth Client` (Auth Code + PKCE + redirect native-scheme + allowed_roles least-priv) — §2 B-1.
- [ ] **B-2** `site_config.allow_cors` = LIST origin (KHÔNG `'*'`) — §2 B-2.
- [ ] **B-3** Public HTTPS host (reverse-proxy + TLS + domain + HTTP→HTTPS) — §2 B-3.
- [ ] **B-4** `site_config.assetcore_qr_base_url` = host HTTPS công khai — §2 B-4.
- [ ] **B-5** nginx `limit_req` cho `oauth2.*` (rate-limit tầng ngoài) — §2 B-5.
- [ ] **B-6** FCM creds trong `site_config` (NGOÀI repo) — §2 B-6 *(phục vụ Phase E push)*.
- [ ] **B-7** `bench migrate` (nếu đổi cap) + reload gunicorn + reload nginx — §2 B-7.
- [ ] **B-8** Chốt quyết định scope↔capability (khuyến nghị giữ coarse) — §2 B-8.
- [ ] **B-verify** Smoke curl SAU reload: `get_token` trả `access_token+refresh_token+expires_in=3600` + bearer call `get_asset_scan_info` trả HTTP-200 envelope chuẩn — [`10-deploy-ops.md §6.3`](./10-deploy-ops.md).

### 3.3 Quyết định go/no-go

> **GO Phase B khi:** toàn bộ §3.1 (A-1…A-12 + A-14 + A-15) ✅ **đã-đạt** (Phase A đóng) — đây là điều kiện cần của exit gate. §3.2 (B-*) là **việc Phase B**, KHÔNG phải điều kiện chặn exit Phase A (chúng là output của Phase B).
>
> **Trạng thái hiện tại (2026-06-09):** §3.1 **14/14 ✅** (A-1…A-12 + A-14 + A-15) → **Phase A exit-ready / 🟢 hoàn tất**. Mọi tầng docset nay có guard máy-đọc: **contract** (`test_mobile_oas` yaml · `test_mobile_capability_map` rbac · `test_mobile_preflight` oauth) + **navigation** (`test_mobile_docset` index/link/ADR/placeholder — A15). Orchestrator có thể mở Phase B (provisioning, HARD-STOP USER).

---

## 4. KPI / Acceptance exit

| Tiêu chí exit | Đo bằng | Mục tiêu | Trạng thái |
|---|---|---|---|
| Traceability 6 flow MVP đầy đủ 7 cột | §1 (đếm dòng) | 6/6 flow, ≥1 dòng/flow | ✅ |
| Endpoint verify @source (file:line) | grep `^def …` khớp matrix | 9 nghiệp vụ + 3 auth = 12, 0 bịa | ✅ |
| operationId khớp OpenAPI | so matrix ↔ yaml | 15/15 path | ✅ |
| Capability khớp SSoT | **guard `TC-MOB-CAP-*`** introspect matrix ↔ `CAPABILITY_MAP` | 100% (v97.c30c69b8974d), 0 cap mới, binding khớp | ✅ (guarded `test_mobile_capability_map.py`) |
| Phase-B prereqs hợp nhất + trỏ nguồn | §2 (đếm + check link) | mọi blocker gom 1 danh sách, chủ thể=USER | ✅ |
| Checklist go/no-go đo được + tách A vs B | §3 | (A) 13/13 self-verified · (B) liệt kê HARD-STOP | ✅ |
| Mọi link `./`/`../` resolve, 0 placeholder, 0 dead-link, FS↔index parity | **guard `TC-MOB-DOC-01..05`** (`test_mobile_docset.py`) | GREEN (5) — 405 link / 0 broken · 13 chương ↔ index · 0 placeholder | ✅ (guarded `test_mobile_docset.py` — A15) |
| No-regression (doc-only) | `test_oas_generator`+`test_oas_signatures`+`test_mobile_oas`+`test_mobile_preflight` | GREEN (49+11+11+9) | ✅ |
| Capability-binding guard máy-đọc (A14) | `test_mobile_capability_map` (`TC-MOB-CAP-01..06`) | GREEN (6) — matrix↔SSoT binding, 0 drift | ✅ |
| Docset-integrity guard máy-đọc (A15) | `test_mobile_docset` (`TC-MOB-DOC-01..05`) | GREEN (5) — index↔FS parity · link-health · ADR registration · no-placeholder | ✅ |

> **KHÔNG bịa baseline:** chỉ số vận hành thật (latency mobile, tỉ lệ retry idempotent, brute-force chặn) *(Cần khảo sát baseline khi có traffic thật — Phase F)*.

---

## Tham chiếu chéo

- **Tổng quan + 3 quyết định nền + convention số:** [`00-overview.md`](./00-overview.md) §2 · §4 · §6
- **Index hub + map Phase A→F:** [`README.md`](./README.md) §1 · §2
- **Persona + MÀN↔API + offline-class + cap per-màn (nguồn matrix §1):** [`05-personas-mvp.md`](./05-personas-mvp.md) §3 · §4 · §5
- **Auth deep-dive + OAuth Client checklist (prereq B-1):** [`03-auth-oauth2.md`](./03-auth-oauth2.md) §1 · §4
- **Feasibility blockers (prereq B-2..B-4, B-8):** [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) §3 · §4 · §7
- **Security go-live checklist (prereq B-5):** [`08-security-compliance.md`](./08-security-compliance.md) §4 · `ADR-MOBILE-004`
- **Runbook go-live numbered steps + smoke (prereq B-1..B-7):** [`10-deploy-ops.md`](./10-deploy-ops.md) §1–§6
- **Pre-flight verifier B-1 (B0-PREFLIGHT — kiểm OAuth Client thành hợp đồng chạy được):** [`12-phase-b-preflight.md`](./12-phase-b-preflight.md) (`verify_oauth_client()` READ-ONLY → `ready`/`blockers`; chấm 7 điều kiện B-1)
- **Push 6-event + FCM creds (prereq B-6):** [`06-push-fcm.md`](./06-push-fcm.md) §3 · §5.2 · `ADR-MOBILE-002`
- **Offline/sync đặc tả (offline-class):** [`07-offline-sync.md`](./07-offline-sync.md) · `ADR-MOBILE-003`
- **OpenAPI (operationId source):** [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (15 path) — convention [`04-api-contract.md §8.1`](./04-api-contract.md)
- **RBAC SSoT (capability):** `../../assetcore/services/shared/rbac.py` (`CAPABILITY_MAP`, `v97.c30c69b8974d`)
- **Guard endpoint↔capability (A14 — matrix §1 ↔ SSoT):** `../../assetcore/tests/test_mobile_capability_map.py` (`TC-MOB-CAP-01..06`) — kiểm chứng tự động binding `(DocType, ptype)` của matrix §1 khớp `rbac.py` + anti-cap-creep + version đóng băng `v97.c30c69b8974d` (drift doc↔source = test ĐỎ). Cross-link 2 chiều: guard ↔ §1 (matrix) ↔ [`03-auth-oauth2.md §3.2`](./03-auth-oauth2.md).
- **Endpoint nghiệp vụ @source:** `../../assetcore/api/imm00.py` · `imm08.py` · `imm09.py` · `imm11.py` · `imm12.py`
- **Provider OAuth2 @source:** `../../../frappe/frappe/integrations/oauth2.py`
