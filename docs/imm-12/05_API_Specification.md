# 05 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Base URL | `/api/method/assetcore.api.imm12.<function>` |
| Auth | Frappe session HOẶC `Authorization: token <key>:<secret>` |
| Cập nhật | 2026-07-27 |
| Trạng thái | ✅ Live — `assetcore/api/imm12.py` deployed (14 endpoint) |

---

## 0. API Catalog

✅ Tất cả IMM-12 endpoint đã implement trong `assetcore/api/imm12.py`.

| # | Endpoint (actual @frappe.whitelist name) | Method | Mô tả | Role guard | US |
|---|---|---|---|---|---|
| 1 | `assetcore.api.imm12.report_incident` | POST | Tạo Incident Report. **CR-24 (Round 32):** +param optional `client_request_id` — idempotency mobile write-outbox (gửi non-empty → gọi lặp trả phiếu đã tạo, KHÔNG trùng). Xem §1a | **`corrective.create`** (V4 D1) | US-12-01 |
| 2 | `assetcore.api.imm12.get_incident` | GET | Chi tiết 1 IR (calls `get_incident_detail`). **CR-39 (2026-07-23):** response += `available_actions[]` = 6 CTA vòng đời server-driven (§18). **CR-40 (2026-07-24):** response += `reporter_name`/`assigned_to_name`/`asset_lifecycle_status` (§19 — hết rò email thô + hiện trạng thái máy) | authenticated | US-12-07 |
| 3 | `assetcore.api.imm12.list_incidents` | GET | List IR với filter (`status`/`severity`/`asset`/`open`/**`mine`**) + pagination. `mine=1` scope `reported_by==session.user` (tab "Báo hỏng của tôi" MVP-5c — §2 #3 "list_incidents — filter mine" + ADR-IMM12-05) | authenticated | US-12-07 |
| 4 | `assetcore.api.imm12.acknowledge_incident` | POST | Open → Acknowledged (hoặc → In Progress) | ROLES_INVESTIGATE | US-12-02 |
| 5 | `assetcore.api.imm12.resolve_incident` | POST | In Progress → Resolved + auto RCA cho High/Critical | ROLES_INVESTIGATE | US-12-02 |
| 6 | `assetcore.api.imm12.close_incident` | POST | Resolved → Closed (validate RCA Completed) | ROLES_CLOSE | US-12-02 |
| 6b | `assetcore.api.imm12.reopen_incident` | POST | **Mở lại điều tra:** `Resolved → In Progress` (BR-12-23, CR-WF-12). `reason` required. Audit IMM Audit Trail (Resolved→In Progress) | cap **`incident.close`** (`_can_close`, parity Close) | US-12-02 |
| 6c | `assetcore.api.imm12.request_rca` | POST | **Yêu cầu phân tích RCA:** `Resolved → RCA Required` (BR-12-24, CR-WF-12-RCA-ENTRY). `rca_reason` required. Qua `apply_workflow("Yêu cầu RCA")` + sync `status`; idempotent RCA reuse; audit IMM Audit Trail (Resolved→RCA Required) | cap **`compliance.submit`** (rbac.can + `_MSG_FORBIDDEN`, parity ack/close) | US-12-03 |
| 7 | `assetcore.api.imm12.cancel_incident` | POST | Huỷ IR (false alarm) | ROLES_INVESTIGATE | US-12-02 |
| 8 | `assetcore.api.imm12.create_rca` | POST | Tạo IMM RCA Record liên kết IR. Idempotent 409 `IMM12_RCA_ALREADY_EXISTS` khi RCA CÒN SỐNG; **CR-55/BR-12-27**: rca_record trỏ RCA `Cancelled` → tạo RCA MỚI thay thế (re-point) | ROLES_INVESTIGATE | US-12-03 |
| 9 | `assetcore.api.imm12.get_rca` | GET | Chi tiết 1 IMM RCA Record **+ `allowed_transitions[]` + `can_manage_rca` (0/1)** (server-driven CTA, BR-12-19) | authenticated | US-12-07 |
| 10 | `assetcore.api.imm12.submit_rca` | POST | Hoàn thành RCA → auto create IMM CAPA Record. **CHỈ từ `RCA In Progress`** (BR-12-21, chặn nhảy-cóc) | cap `corrective.write` | US-12-03 |
| 9b | `assetcore.api.imm12.start_rca` | POST | **Bắt đầu phân tích:** `RCA Required → RCA In Progress` (BR-12-20). Audit `rca_started` | cap `corrective.write` | US-12-03 |
| 10b | `assetcore.api.imm12.cancel_rca` | POST | **Hủy RCA:** `{RCA Required, RCA In Progress} → Cancelled` (BR-12-22), `reason` required. Audit `rca_cancelled` | cap `corrective.write` | US-12-03 |
| 11 | `assetcore.api.imm12.get_chronic_failures` | GET | Danh sách asset chronic (≥3/90d) | authenticated | US-12-04 |
| 12 | `assetcore.api.imm12.get_dashboard` | GET | Dashboard: stats + active + rcas + chronic | authenticated | US-12-05 |
| 13 | `assetcore.api.imm12.get_incident_stats` | GET | KPI counts per status+severity | authenticated | US-12-05 |
| 14 | `assetcore.api.imm12.get_asset_incident_history` | GET | Incident history của 1 asset (`asset` required + `limit` default 10) → `{asset, items[]}` (9-field/dòng `name,incident_type,severity,status,reported_at,fault_code,closed_date,linked_capa,rca_record` @`services/imm12.py:838-843`; KHÔNG pagination) | authenticated | US-12-07 |
| 15 | `assetcore.api.imm12.attach_incident_photo` | POST (multipart) | Đính **ảnh bằng chứng hiện trường** (NĐ98) vào 1 Incident Report → File private + 1 lifecycle event `incident_photo_attached`. Permission = **reporter HOẶC `incident.write`** trên chính phiếu đó (§2 #15 + BR-12-17). Mobile CR-17/G6 (endpoint DUY NHẤT còn thiếu trong contract). **CR-24 phần dư (vòng 3):** +param optional `client_request_id` — idempotency re-drain ảnh, đóng attachment-dup (B-rel-3). Xem §15a | reporter OR `incident.write` | US-12-08 |

> 📱 **Mobile-BE contract (FLOW-2 device-profile):** endpoint #14 đã bồi vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (opId `getAssetIncidentHistory`, 200 = oneOf `[AssetIncidentHistoryEnvelope, Error]` closed-schema route-by-VALUE `body.success`; envelope `data.required=[asset,items]` **KHÔNG pagination** — KHÁC `IncidentListEnvelope`; element `AssetIncidentHistoryItem` EXACT 9 prop, 0 Check field ⇒ né int-vs-bool trap). Lấp dead-end màn hồ-sơ-thiết-bị sau `getAssetScanInfo`. Spec đầy đủ: [`docs/mobile/04-api-contract.md §8.18`](../mobile/04-api-contract.md).

> 🔒 **DONE-gate spec-contract endpoint #6 `close_incident` (BR-12-02 / ADR-IMM12-RCA-LIVE-SSoT, Round 4 — chống ĐÓNG-GIẢ escalation):**
> - **Gate RCA DERIVE-LIVE từ `severity` (SSoT), KHÔNG cờ STORED `rca_required`.** Predicate = `_needs_rca(doc.severity) OR doc.requires_rca` (mirror workflow JSON `doc.severity in ('High','Critical') or doc.requires_rca==1`). Chặn phiếu Critical/High thiếu RCA `Completed` **kể cả phiếu escalation từ Medium/Low** (`rca_required` ban đầu 0 nhưng gate đọc `severity` LIVE). Bug cũ `_needs_rca(sev) AND rca_required` lọt escalation — đã đóng.
> - **2 gate 1 predicate (không lệch):** service `close_incident` (@711, đường API) + controller hook `validate_incident_close_gate` (@1740, wired `hooks.py:270` `Incident Report.validate` — đường desk/`doc.save`/`apply_workflow`). Cùng predicate ⇒ chặn nhất quán cả 2 đường.
> - **Lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope** (KHÔNG `raise`→HTTP-4xx, KHÔNG status-line): `IMM12_CLOSE_RCA_REQUIRED` (thiếu `rca_record`) / `IMM12_CLOSE_RCA_INCOMPLETE` (RCA `status!=Completed`) — body `success:false`, bucket 422. Phiếu Critical có RCA `Completed` → 200 `status='Closed'` + asset Out of Service → Active. Non-regression Low/Medium thực (`requires_rca=0`) → close 200 bình thường.
> - **KHÔNG thêm `@frappe.whitelist` mới ⇒ `oas_baseline` bất biến (né Blocker#4); `imm_12_incident_workflow.json` bất biến (admin-override GREEN).** Acceptance đầy đủ: `02 §IV.2c` (INV-RCA-LIVE-1..8); backend §3.0.3.

> 🔒 **DONE-gate spec-contract endpoint #6b `reopen_incident` (CR-WF-12, parity `close_incident`):**
> - **Lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope** (`_err`/`handle`) — KHÔNG `raise`→HTTP-4xx: `IMM12_REOPEN_REASON_REQUIRED` (422 bucket, HTTP-200 body), `IMM12_BAD_STATE` (409 bucket, HTTP-200 body) khi status ≠ `Resolved`.
> - **2 loại 403 phân biệt:** (1) **dispatcher-403** — guest/no-token gọi endpoint (whitelist `methods=["POST"]` KHÔNG `allow_guest`) → Frappe từ chối TRƯỚC handler (thực chất handler cũng chặn `session.user=="Guest"` → `_err(401)`); (2) **in-handler cap-403** — có phiên nhưng thiếu cap `incident.close` (`if not _can_close(): return _err(403)`) → HTTP-200 Error envelope `AUTH_FORBIDDEN`. Base user / Corrective User (chỉ `incident.acknowledge`) → cap-403; System Manager / AssetCore Super Admin → OK.

> 📱 **Mobile-BE contract (CR-WF-12-REOPEN · Trục B):** endpoint #6b đã bồi vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (opId `reopenIncident`, POST, tag `incident`; path-count 74 → 75). **REUSE `IncidentActionEnvelope`/`IncidentActionResponse`** (data EXACT 2-key `{name, status:'In Progress'}` @`services/imm12.py:736` — **mirror `startWork`**, KHÁC `resolveIncident`/`closeIncident` 3-key envelope RIÊNG) ⇒ KHÔNG sinh envelope/response schema mới. Schema MỚI **`ReopenIncidentRequest` `{name req, reason req}`** `additionalProperties:false` — **`reason` REQUIRED** (KHÁC `StartWorkRequest`/`CloseIncidentRequest` optional-notes). 200 = `oneOf [IncidentActionEnvelope | Error]` Decision-B route-by-VALUE `body.success` (0 discriminator — 2 nhánh closed disjoint required-set). **403 = SINGLE-SHAPE `Forbidden`** (chỉ dispatcher-403; in-handler cap-403 `_can_close` PHỦ bởi nhánh Error 200-oneOf — **mirror `closeIncident`**, KHÔNG dual-403). Lỗi nghiệp vụ (`IMM12_REOPEN_REASON_REQUIRED` reason rỗng · `IMM12_BAD_STATE` status≠`Resolved`) đến HTTP-200 + Error body qua `handle()`. CONTRACT-ONLY (BE LIVE @`api/imm12.py:371` + `services/imm12.py:713`, covered `test_imm12.py:3199`) — 0 `.py` runtime change / 0 reload / 0 migrate. Spec đầy đủ: `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (§`reopen_incident`), ADR-MOBILE-006 (04 §8.10).

> 🔒 **DONE-gate spec-contract endpoint #6c `request_rca` (CR-WF-12-RCA-ENTRY / BR-12-24, ADR-IMM12-RCA-ENTRY):**
> - **Lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope** (`_err`/`handle`) — KHÔNG `raise`→HTTP-4xx: `IMM12_REQUEST_RCA_BAD_STATE` (**422 bucket**, HTTP-200 body) khi `status ≠ Resolved` — **MSG MỚI, KHÔNG dùng `IMM12_BAD_STATE` (=409)**; `IMM12_RCA_REASON_REQUIRED` (422 bucket) khi `rca_reason` blank. Precondition gate đọc `doc.status` (domain SSoT), **KHÔNG** `workflow_state` (dual-track: sibling dùng `doc.save` ⇒ `workflow_state` có thể lệch). KHÔNG đổi status khi reject.
> - **2 loại 403 phân biệt:** (1) **dispatcher-403** — guest/no-token → Frappe từ chối TRƯỚC handler (handler cũng chặn `session.user=="Guest"` → `_err(401)`); (2) **in-handler cap-403** — có phiên nhưng thiếu cap `compliance.submit` (`if not rbac.can("compliance.submit"): return _err(_MSG_FORBIDDEN, 403)` — **rbac.can, KHÔNG `rbac.require`** → message VN sạch, KHÔNG leak raw cap) → HTTP-200 Error envelope `AUTH_FORBIDDEN`. Base `AssetCore System User` / Corrective User / Compliance User (chỉ create=1) → cap-403; **Compliance Manager, AssetCore Super Admin → OK** (DocPerm submit=1 `IMM CAPA Record`).
> - **Cap ⊆ workflow (anti-dead-gate, KHÔNG false-clickable):** role-set `compliance.submit` = {AssetCore Super Admin, Compliance Manager} ⊆ workflow "Yêu cầu RCA" `allowed` = {Compliance Manager, System Manager, AssetCore Super Admin} ⇒ mọi user qua cap-403 đều `apply_workflow` thành công; FE-shown (`can('compliance.submit')`) == BE-clickable (cùng cap). Residual: pure-`System Manager` (∉ compliance.submit) ẩn nút trên SPA — an toàn (⊆ hẹp, KHÔNG false-clickable), phủ qua Super Admin (QTV) + desk admin-override.
> - **INVARIANT bất biến:** `request_rca` KHÔNG đổi `_VALID_TRANSITIONS` / `imm_12_incident_workflow.json` (state edge `Resolved→RCA Required` đã reconciled Round 12) ⇒ `TestIncidentAllowedTransitions` GREEN + admin-override 22/22 GREEN. `get_incident_detail(Resolved).allowed_transitions` vốn đã chứa `'RCA Required'` — round này bổ **driver THẬT** (endpoint + CTA) cho advertise đó.

> 🔒 **DONE-gate spec-contract endpoint #9b/#10/#10b `start_rca` / `submit_rca` / `cancel_rca` (CR-WF-12-RCA, desk↔endpoint parity):**
> - **Lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope** (`_err`/`handle`) — KHÔNG `raise`→HTTP-4xx: `IMM12_RCA_START_INVALID_STATE` / `IMM12_RCA_SUBMIT_INVALID_STATE` / `IMM12_RCA_CANCEL_INVALID_STATE` (409 bucket, HTTP-200 body); `submit_rca` thiếu `root_cause`/`corrective_action` → 422 bucket (`IMM12_RCA_ROOT_CAUSE_REQUIRED`/…); `cancel_rca` thiếu `reason` → 422.
> - **2 loại 403 phân biệt:** (1) **dispatcher-403** — guest/no-token → Frappe từ chối TRƯỚC handler; (2) **in-handler cap-403** — có phiên nhưng thiếu cap `corrective.write` (`_require_rca_cap("corrective.write")` → `_err(403)` `AUTH_FORBIDDEN`, message VN sạch KHÔNG leak raw cap). Base `AssetCore System User` / Auditor → cap-403; **Corrective User, Corrective Manager, AssetCore Super Admin → OK** (DocPerm write=1 Incident Report).
> - **Desk == endpoint parity (INV-RCA-PARITY-B):** role-set workflow desk cho MỖI action ∈ {Bắt đầu phân tích RCA, Hoàn thành RCA, Hủy RCA} PHẢI `⊇ roles(corrective.write) ∪ {AssetCore Super Admin, System Manager}` = {Corrective User, Corrective Manager, System Manager, AssetCore Super Admin}. Trước fix "Bắt đầu/Hoàn thành" thiếu `Corrective Manager` ⇒ desk chặn dù endpoint cho phép (asymmetry). Fix = thêm role vào workflow source + fixture (04 §3.0.2); `roles(corrective.write)` resolve ĐỘNG qua rbac, KHÔNG hardcode role-name.

---

## 1. Quy ước chung

### 1.1. Response success — format chuẩn AssetCore

```jsonc
{
  "success": true,
  "data": <payload — object / array / null>
}
```

FE đọc `response.data.data` (axios + Frappe lớp ngoài đã wrap).

**HTTP status:** Frappe luôn trả HTTP 200. Phân biệt success/error qua field `success`.

### 1.2. Response error — format chuẩn

```jsonc
{
  "success": false,
  "error": "Thông báo lỗi tiếng Việt",
  "code": "BUSINESS_RULE",
  "fields": {
    "clinical_impact": "Sự cố Critical bắt buộc mô tả tác động lâm sàng"
  }
}
```

### 1.3. Error code catalog (Notification Contract — Sprint 2026-05-29)

> **Cột `message_code`** trỏ vào registry `assetcore/utils/messages.py:MESSAGES`.
> BE raise qua `nthrow(MSG.<code>, **ctx)` (service) / `nthrow_in_hook(MSG.<code>)`
> (DocType hook); handler `api_handler.handle()` tự hydrate `title/severity/action_hint`
> từ registry rồi đưa vào envelope `_err`. FE đọc `messageCode` → `useNotify().fromError()`.
> Xem **§11 Notification Contract** (single source of truth).

| BE bucket (`code`) | HTTP | Severity | `message_code` (MSG.*) | Business Rule | Khi nào |
|---|---|---|---|---|---|
| `NOT_FOUND` | 404 | warning | `IMM12_INCIDENT_NOT_FOUND` | — | Incident Report không tồn tại |
| `NOT_FOUND` | 404 | warning | `IMM12_RCA_NOT_FOUND` | — | RCA Record không tồn tại |
| `NOT_FOUND` | 404 | warning | `IMM12_ASSET_NOT_FOUND` | — | `asset` không tồn tại khi tạo incident |
| `BUSINESS_RULE` | 422 | critical | `IMM12_CLINICAL_IMPACT_REQUIRED` | BR-12-01 | Incident Critical thiếu `clinical_impact` |
| `BUSINESS_RULE` | 422 | warning | `IMM12_RESOLUTION_NOTES_REQUIRED` | — | Resolve thiếu `resolution_notes` |
| `BUSINESS_RULE` | 422 | warning | `IMM12_CANCEL_REASON_REQUIRED` | — | Cancel thiếu lý do hủy |
| `BUSINESS_RULE` | 422 | warning | `IMM12_REOPEN_REASON_REQUIRED` | BR-12-23 | `reopen_incident` thiếu lý do mở lại — VN: "Vui lòng nhập lý do mở lại điều tra" |
| `BUSINESS_RULE` | 422 | warning | `IMM12_RCA_REASON_REQUIRED` | BR-12-24 | `request_rca` thiếu lý do — VN: "Vui lòng nhập lý do yêu cầu phân tích nguyên nhân gốc" (MSG MỚI) |
| `BUSINESS_RULE` | 422 | warning | `IMM12_REQUEST_RCA_BAD_STATE` | BR-12-24 | `request_rca` khi status ≠ `Resolved` — VN: "Chỉ có thể yêu cầu phân tích nguyên nhân gốc khi sự cố đang ở trạng thái Đã giải quyết" (MSG MỚI, **422 — KHÔNG dùng `IMM12_BAD_STATE`=409**) |
| `BUSINESS_RULE` | 422 | warning | `IMM12_RCA_ROOT_CAUSE_REQUIRED` | BR-12-07 | Submit RCA thiếu `root_cause` |
| `BUSINESS_RULE` | 422 | warning | `IMM12_RCA_CORRECTIVE_REQUIRED` | BR-12-07 | Submit RCA thiếu `corrective_action` |
| `CONFLICT` | 409 | warning | `IMM12_RCA_ALREADY_EXISTS` | BR-12-27 | Incident đã có RCA **CÒN SỐNG** (`_has_live_rca`=True; status ∈ {Required, In Progress, Completed}) — `create_rca` idempotent. **CR-55**: rca_record trỏ RCA `Cancelled` KHÔNG raise (tạo RCA mới thay thế) |
| `CONFLICT` | 409 | warning | `IMM12_RCA_ALREADY_COMPLETED` | — | Submit RCA khi RCA đã Completed |
| `CONFLICT` | 409 | warning | `IMM12_RCA_START_INVALID_STATE` | BR-12-20 | `start_rca` khi status ≠ `RCA Required` — VN: "Chỉ có thể bắt đầu phân tích khi phiếu ở trạng thái Cần phân tích" |
| `CONFLICT` | 409 | warning | `IMM12_RCA_SUBMIT_INVALID_STATE` | BR-12-21 | `submit_rca` từ `RCA Required` (nhảy-cóc) — VN: "Chỉ có thể hoàn thành khi phiếu đang ở trạng thái Đang phân tích" |
| `CONFLICT` | 409 | warning | `IMM12_RCA_CANCEL_INVALID_STATE` | BR-12-22 | `cancel_rca` khi status ∈ `{Completed, Cancelled}` — VN: "Chỉ có thể hủy khi phiếu đang hoạt động (Cần phân tích hoặc Đang phân tích)" |
| `BAD_STATE` | 409 | warning | `IMM12_BAD_STATE` | — | State machine transition không hợp lệ (gồm `reopen_incident` khi status ≠ `Resolved` — `_assert_transition`, BR-12-23) |
| `BUSINESS_RULE` | 422 | critical | `IMM12_CLOSE_RCA_REQUIRED` | BR-12-02 / NEG-11 | Đóng IR Major/Critical khi chưa có RCA |
| `BUSINESS_RULE` | 422 | critical | `IMM12_CLOSE_RCA_INCOMPLETE` | BR-12-02 / NEG-11 | Đóng IR Major/Critical khi RCA chưa Completed |
| `FORBIDDEN` | 403 | warning | `AUTH_FORBIDDEN` | — | Không có quyền (role / Permission Query) |
| `INVALID_PARAMS` | 400 | warning | `SYS_INVALID_PARAMS` | — | JSON param malformed (`parse_json`) |
| `INTERNAL` | 500 | error | `SYS_INTERNAL` | — | Lỗi hệ thống unexpected |
| _(success)_ | 200 | success | `IMM12_REPORT_SUCCESS` | — | Tạo incident thành công (envelope `_ok`) |

### 1.4. Mapping FE ↔ BE error code

| BE (`code`) | FE (`ErrorCode`) | Lý do |
|---|---|---|
| `VALIDATION` | `VALIDATION_ERROR` | Field-level inline error |
| `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` | Toast + block action |
| `NOT_FOUND` | `NOT_FOUND` | Redirect 404 |
| `FORBIDDEN` | `FORBIDDEN` | Hide action button |
| `CONFLICT` | `CONFLICT` | Toast warning |
| `BAD_STATE` | `BAD_STATE` | Modal explain + action blocked |
| `INTERNAL` | `INTERNAL_ERROR` | Generic error toast |

### 1.5. Pagination convention

```jsonc
{
  "success": true,
  "data": {
    "data": [...],
    "page": 1,
    "page_size": 20,
    "total": 67,
    "total_pages": 4
  }
}
```

---

## 2. Endpoint chi tiết

### 1. report_incident — Tạo Incident Report ✅ LIVE

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm12.report_incident` |
| Role | **Cap-gate `corrective.create`** (V4-GATE D1) — Guest → 401; authenticated thiếu `corrective.create` → **403** (message VI sạch, KHÔNG leak raw cap) |
| Idempotent | **Conditional (CR-24, Round 32):** No khi `client_request_id` rỗng/thiếu (call-path cũ NGUYÊN VẸN); **Yes** khi gửi `client_request_id` non-empty — re-drain outbox cùng key + cùng reporter → return phiếu đã tạo (KHÔNG insert thứ 2). Xem §1a |

**Request (actual parameters — `fault_description` KHÔNG tồn tại):**
```jsonc
{
  "asset": "ACC-ASSET-2026-00012",           // required
  "incident_type": "Malfunction",            // required (actual field name)
  "severity": "Critical",                    // Low | Medium | High | Critical
  "description": "Máy thở alarm P_HIGH liên tục", // required (actual field: description)
  "fault_code": "VENT_ALARM_HIGH",           // optional
  "clinical_impact": "Bệnh nhân phụ thuộc, đã chuẩn bị bóng ambu", // required if Critical (BR-12-01)
  "workaround_applied": 0,                   // int, not bool
  "patient_affected": 0,
  "patient_impact_description": "",
  "immediate_action": "",
  "linked_repair_wo": "",
  "occurred_datetime": "2026-06-27 08:15:00", // optional — G1/CR-16: thời điểm sự cố THỰC SỰ xảy ra (Frappe wire "yyyy-MM-dd HH:mm:ss", KHÔNG ISO-T); rỗng → fallback reported_at; tương lai → 422
  "source": "qr-scan",                       // V4 D2: provenance enum {manual,qr-scan}; mặc định "manual" nếu thiếu/lạ
  "client_request_id": "a3f1c9e2-…-uuid"     // optional — CR-24: idempotency key mobile write-outbox; rỗng/thiếu → tạo mới thường (§1a)
}
```

> 📱 **Mobile-BE contract (G1/CR-16 — báo hỏng F2, contract-only):** `occurred_datetime` ĐÃ wire vào `ReportIncidentRequest.properties` của `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (`type: string`, **KHÔNG** `format: date-time` — Frappe đọc datetime space-separated `yyyy-MM-dd HH:mm:ss` qua `get_datetime` `services/imm12.py:377`, KHÔNG ISO-8601 `T`). **Optional** (`api/imm12.py:83` default `=""`) ⇒ KHÔNG vào `required[]` (giữ EXACT 4 = `[asset,incident_type,severity,description]`). Rỗng → server fallback `reported_at` (`services/imm12.py:382`); KHÔNG tương lai → 422 `IMM12_OCCURRED_DATETIME_FUTURE` (`services/imm12.py:378-379`; `utils/messages.py:801` `http_status=422`). Spec đầy đủ + test contract (TC-MOB-OAS-13g parity + count bump): [`docs/mobile/04-api-contract.md §8.3a`](../mobile/04-api-contract.md) · ADR D5 [`ADR-IMM12-REPORT-FAILURE.md`](./ADR-IMM12-REPORT-FAILURE.md).

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "IR-2026-0042",
    "asset": "ACC-ASSET-2026-00012",
    "severity": "Critical",
    "status": "Open",
    "reported_at": "2026-04-18T08:12:00+07:00",
    "asset_lifecycle_status": "Out of Service",
    "lifecycle_event": "ALE-2026-0089"
  }
}
```

**Errors:**
| HTTP | Code (BE) | Code (FE) | Khi nào |
|---|---|---|---|
| 401 | `UNAUTHENTICATED` | — | Guest (chưa đăng nhập) |
| **403** | `PERMISSION` | `FORBIDDEN` | **V4 D1:** authenticated thiếu `corrective.create` — message "Không có quyền thực hiện hành động này" (KHÔNG chứa raw cap `corrective.create`) |
| 422 | `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` | Critical + không có clinical_impact (BR-12-01) |
| 422 | `IMM12-OCCURRED-DATETIME-FUTURE` | `BUSINESS_RULE_VIOLATION` | **G1/CR-16:** `occurred_datetime` ở tương lai (`services/imm12.py:378-379`; `messages.py:801`) — nguồn 422 thứ 2 trên path, KHÔNG status mới |
| 422 | `VALIDATION` | `VALIDATION_ERROR` | Thiếu required fields |
| 404 | `NOT_FOUND` | `NOT_FOUND` | Asset không tồn tại |
| **422** | `IMM12-ASSET-DECOMMISSIONED` | `BUSINESS_RULE_VIOLATION` | 🆕 **AC-CR-90 / BR-12-29 — land EC-12-05**: thiết bị `lifecycle_status == 'Decommissioned'`. Kiểm ngay **sau** guard `NOT_FOUND`, **trước** mọi phép gán ⇒ **0** bản ghi / **0** lifecycle event / **0** audit khi bị chặn. **CHỈ** chặn `Decommissioned` — `Out of Service` **vẫn báo được** sự cố (đó thường là lý do thiết bị ngừng dùng) |

**Side effects (mọi severity — V4 D2):**
- `imm00.create_lifecycle_event(asset, "incident_reported", root_doctype="Incident Report", root_record=<IR>, notes="Báo hỏng ({source_label}) — …")` — canonical lifecycle event + provenance.
- `imm00.log_audit_event(...)` `change_summary` thêm provenance `({source_label})` (hash-chain GIỮ).

**Side effects bổ sung (Critical):**
- `imm00.transition_asset_status(asset, "Out of Service")` (BR-12-04)
- Email BGĐ + Workshop Lead

---

### 1a. report_incident — Idempotency `client_request_id` (mobile write-outbox, CR-24 Round 32) 🆕 SPEC (BE Bước-4)

> **Mục tiêu.** Đóng cửa sổ re-drain outbox tạo **phiếu sự cố TRÙNG** (NĐ98 audit-integrity). Client mobile ghi offline vào write-outbox; re-drain khi có mạng lại. Nếu response lần đầu mất SAU khi server đã tạo phiếu → re-drain gửi lại → trùng phiếu + trùng lifecycle event + trùng audit trail. `client_request_id` (UUID client-side, ổn định qua mọi re-drain) khiến gọi lặp = no-op an toàn.

**Param mới:** `client_request_id: str = ""` — OPTIONAL, thêm vào CẢ handler `api/imm12.py::report_incident` VÀ service `services/imm12.py::report_incident` (truyền xuyên suốt).

**Hành vi (BR-12-25):**

| Trường hợp | Kết quả |
|---|---|
| `client_request_id` non-empty, gọi 2× (cùng reporter) | **1 phiếu.** Call thứ 2 → dedupe-hit → return `{name, status, severity}` của phiếu ĐÃ tạo. KHÔNG insert, KHÔNG `_log` (IMM Audit Trail), KHÔNG emit `incident_reported` lifecycle event. |
| `client_request_id` rỗng/thiếu | **Tạo mới NGUYÊN VẸN** — mỗi call = 1 phiếu (guard skip). Backward-compat 100% cho web/desk/call-path cũ. |
| 2 `client_request_id` KHÁC nhau | 2 phiếu riêng biệt. |
| Cùng `client_request_id`, reporter KHÁC | KHÔNG dedupe (scope `(client_request_id, reported_by)`) — thực tế UUID nên không xảy ra. |

**Cơ chế (SSoT §04 §2.1a + ADR-IMM12-09):** SELECT-before-insert ở ĐẦU service — `frappe.db.get_value("Incident Report", {client_request_id, reported_by}, [name,status,severity])`; trúng → early-return. Field `client_request_id` (Data, `search_index:1` → DB index NON-UNIQUE) persist trên `Incident Report`; lookup = index-seek O(1), KHÔNG full-scan.

> ⚠️ **[LANDED-DELTA 2026-07-14 — hiện thực KHÁC spec trên, đã VERIFY @source]:** bản land (ADR-MOBILE-047, Accepted) chốt **GLOBAL-key** (`_dedupe_lookup` `services/imm12.py:450` — KHÔNG lọc `reported_by`) + field **`unique:1` NULL-store** (`incident_report.json` — persist CHỈ khi truthy → NULL, KHÔNG `search_index`) + **race-handler `UniqueValidationError`** (@:549-560). Spec NON-UNIQUE/(key,reported_by) ở đây + ADR-IMM12-09 đã bị **supersede** — xem `04 §2.1a` note + ADR-IMM12-09 Status. Spec mới (photo §15a) bám pattern ĐÃ LAND, không bám spec cũ này.

**📱 Mobile-BE OAS mirror delta (COUPLED — KHÔNG contract-only, land cùng handler ở Bước-4):**
- `docs/mobile/openapi/assetcore-mobile.openapi.yaml` → schema `ReportIncidentRequest.properties`: THÊM
  ```yaml
  client_request_id:
    type: string
    description: >-
      OPTIONAL — idempotency key mobile write-outbox (UUID client-side, ổn định qua re-drain).
      Gửi non-empty ⇒ gọi lặp cùng key trả phiếu đã tạo (KHÔNG trùng). Rỗng/thiếu ⇒ tạo mới thường.
  ```
  `required[]` **GIỮ EXACT 4** `[asset, incident_type, severity, description]` — `client_request_id` KHÔNG vào required (mirror `occurred_datetime`).
- **⚠️ Ràng buộc COUPLING (test_mobile_oas TC-MOB-OAS-13e handler-parity, `test_mobile_oas.py:3636-3650`):** `set(ReportIncidentRequest.properties) ⊆ inspect.signature(imm12.report_incident).parameters`. ⇒ **KHÔNG được** thêm yaml-prop `client_request_id` nếu handler `api/imm12.py::report_incident` CHƯA có param `client_request_id` — nếu không test RED (`DRIFT-ĐẢO`). ⇒ yaml + handler-param **PHẢI land ATOMIC cùng round Bước-4** (đây KHÔNG phải pure-yaml contract-only như các CR trước).
- **⚠️ Self-Correction acceptance (`additionalProperties:false`):** đề mục ghi "additionalProperties:false GIỮ (closed schema)". **KIỂM CHỨNG @source (`yaml:3239-3271`): `ReportIncidentRequest` HIỆN KHÔNG có `additionalProperties` — schema đang OPEN** (mặc định `true`), CỐ Ý (comment yaml:3236-3237: 8 param optional còn lại `fault_code/workaround_applied/...` để Phase-C kế bồi dần; đóng schema bây giờ sẽ chặn các param đang chờ). ⇒ **CHỐT: GIỮ NGUYÊN trạng thái hiện tại (OPEN — KHÔNG thêm `additionalProperties:false`).** Chỉ thêm property `client_request_id`. Đóng schema = scope-creep ngoài CR-24 + rủi ro conflict Phase-C ⇒ Never round này.
- **Test guard cần thêm** (BE Bước-4, đối xứng TC-MOB-OAS-13g `occurred_datetime`): +TC trong `TestMobileReportIncidentBody` assert (a) `client_request_id ∈ properties` type `string`; (b) `∉ required[]` + required GIỮ EXACT 4; (c) handler-parity `client_request_id ∈ live_params`. Bump `_EXPECTED_TEST_COUNT` + `test_mobile_docset` counter (`_GUARD_SUITE_EXPECTED[test_mobile_oas]` + `_MOBILE_OAS_TOTAL` + delta var) — đọc số FRESH tại thời điểm code (multi-session drift; STATE numbers có thể cũ).

**Errors (CR-24 KHÔNG thêm status mới):** dedupe-hit là success path (return phiếu cũ, HTTP-200 envelope). Bảng lỗi §1 giữ nguyên (401/403/422×2/404).

**DoD (acceptance CR-24):** `bench --site miyano run-tests` cho `test_imm12` + `test_mobile_oas` + `test_mobile_docset` → 'Ran N OK' THẬT. **RED-before** (chứng minh test có răng): CHƯA có dedupe → TC gọi 2× cùng key **FAIL** (tạo 2 phiếu). Sau khi land dedupe → GREEN.

---

### 5. resolve_incident — Resolve + auto create RCA ✅ LIVE

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm12.resolve_incident` |
| Role | ROLES_INVESTIGATE |
| Idempotent | Yes (repeat → return current state) |

**Request:**
```jsonc
{
  "name": "IR-2026-0042",
  "resolution_notes": "Đã thay pressure sensor và calibrate lại.",
  "root_cause": ""                           // optional
}
```

**Response success (Low/Medium — no RCA):**
```jsonc
{
  "success": true,
  "data": {
    "name": "IR-2026-0042",
    "status": "Resolved",
    "rca_created": null
  }
}
```

**Response success (High/Critical — RCA auto-created):**
```jsonc
{
  "success": true,
  "data": {
    "name": "IR-2026-0042",
    "status": "Resolved",
    "rca_created": "IMM-RCA-2026-0012"
  }
}
```

> **Note:** Status goes to `"Resolved"` always (not `"RCA Required"`). RCA is auto-created in background. IMM-12 states in actual code: Open → Acknowledged → In Progress → Resolved → Closed (`"Under Investigation"` là alias lịch sử của `In Progress`).

---

### 10. submit_rca — Submit RCA → auto create IMM CAPA Record ✅ LIVE

> **Endpoint is `submit_rca`, NOT `submit_rca_and_create_capa`.**

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm12.submit_rca` |
| Role | ROLES_INVESTIGATE |
| Idempotent | No (409 if already Completed) |

**Request (actual parameters):**
```jsonc
{
  "name": "IMM-RCA-2026-0012",              // required
  "root_cause": "Pressure sensor degraded do nhiệt độ ICU vượt 28°C",  // required (BR-12-07)
  "corrective_action": "Thay sensor + calibrate",   // required (BR-12-07, actual param name)
  "preventive_action": "PM HVAC tích hợp vào CMMS", // optional
  "five_why_steps": "[{\"why_number\":1,\"why_question\":\"Why?\",\"why_answer\":\"...\"}]", // JSON string
  "rca_notes": ""
}
```

> `five_why_steps` is sent as JSON string from FE (serialized by `submitRca()` in imm12.ts).

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "RCA-2026-0012",
    "status": "Completed",
    "completed_date": "2026-04-22",
    "linked_capa": "CAPA-2026-0023",
    "capa_due_date": "2026-05-22"
  }
}
```

**Errors:**
| Code | Khi nào |
|---|---|
| `422` | Thiếu `root_cause` hoặc `corrective_action` (BR-12-07) |
| `409` | RCA đã Completed (`IMM12_RCA_ALREADY_COMPLETED`) |
| `409` | **Gọi từ `RCA Required` — nhảy-cóc bỏ `RCA In Progress` (BR-12-21, `IMM12_RCA_SUBMIT_INVALID_STATE`).** Hành vi cũ cho phép submit thẳng từ `RCA Required` = BUG, nay chặn |
| `404` | IMM RCA Record không tồn tại |
| `403` | in-handler cap-403: thiếu capability `corrective.write` (Decision-B envelope, HTTP-200 body `success:false` — xem §Two-flavor 403) |

**Side effects (BR-12-06 + BR-12-21):**
- `svc00.create_capa(asset, source_type="IMM RCA Record", source_ref=rca.name, severity=...)` → IMM CAPA Record
- Sets `rca.linked_capa` + `incident.linked_capa`
- Audit `_log(...)` change_summary token **`rca_completed`** (`RCA In Progress → Completed`)

**Curl ví dụ:**
```bash
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.submit_rca' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"name":"IMM-RCA-2026-0012","root_cause":"Sensor degraded","corrective_action":"Thay sensor"}'
```

---

### 6c. request_rca — Yêu cầu phân tích RCA (Resolved → RCA Required) 🆕 SPEC

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm12.request_rca` |
| Cap-gate | `compliance.submit` (in-handler cap-403 · rbac.can + `_MSG_FORBIDDEN`, KHÔNG `rbac.require`) |
| Params | `name` (required), `rca_reason` (required) |

**Response success (Decision-B `_ok`):**
```jsonc
{ "success": true, "data": { "name": "INC-2026-00042", "status": "RCA Required", "rca_record": "RCA-2026-0012" } }
```

**Service flow (`services/imm12.py: request_rca`) — mirror `_advance_incident_after_rca`:**
1. `doc = _get_incident(name)` (404 `IMM12_INCIDENT_NOT_FOUND` nếu không tồn tại).
2. **Precondition (đọc `doc.status` — domain SSoT, KHÔNG `workflow_state`):** `status ≠ "Resolved"` → `nthrow(MSG.IMM12_REQUEST_RCA_BAD_STATE)` (422); `rca_reason.strip()` rỗng → `nthrow(MSG.IMM12_RCA_REASON_REQUIRED)` (422). KHÔNG đổi status.
3. `apply_workflow(inc, "Yêu cầu RCA")` (flip `workflow_state` → `RCA Required`), rồi `frappe.db.set_value(_DT_INCIDENT, name, {"status": "RCA Required"}, update_modified=False)` sync Select. Wrap `try/except` + fallback `db.set_value({"workflow_state": "RCA Required", "status": "RCA Required"})` khi `workflow_state` desync (mirror `_advance` except-branch). `frappe.db.commit()`.
4. **RCA idempotent reuse (loại-Cancelled, BR-12-27/ADR-IMM12-11):** `if not _has_live_rca(doc): create_rca(name)` — reuse `rca_record` CHỈ khi RCA CÒN SỐNG (vd Critical đã auto-tạo ở `resolve_incident`, status ∈ {Required, In Progress, Completed}). Nếu rca_record trỏ RCA `Cancelled` (CR-55) ⇒ `_has_live_rca`=False ⇒ `create_rca(name)` tạo RCA MỚI + re-point (KHÔNG tái dùng hồ sơ huỷ). `create_rca` raise 409 nếu đã có RCA sống ⇒ KHÔNG tạo trùng.
5. `_log(name, doc.asset, f"Yêu cầu RCA — {rca_reason[:120]}", "Resolved", "RCA Required")` (IMM Audit Trail — **KHÔNG** thêm option Select `event_type`, precedent reopen D4).
6. `return {"name": name, "status": "RCA Required", "rca_record": <rca.name>}`.

**Errors:**
| Code | Khi nào |
|---|---|
| `422` | `status ≠ Resolved` → `IMM12_REQUEST_RCA_BAD_STATE` (VN "Chỉ có thể yêu cầu phân tích nguyên nhân gốc khi sự cố đang ở trạng thái Đã giải quyết") — **KHÔNG dùng `IMM12_BAD_STATE`=409** |
| `422` | `rca_reason` rỗng/space → `IMM12_RCA_REASON_REQUIRED` |
| `404` | Incident không tồn tại → `IMM12_INCIDENT_NOT_FOUND` |
| `403` | in-handler cap-403 thiếu `compliance.submit`; dispatcher-403 nếu guest/no-token |

**Side effect:** audit IMM Audit Trail (`Resolved → RCA Required`); RCA Record tạo/link (idempotent). **ENTRY** của nhánh `RCA Required` — sau khi hoàn tất RCA (`start_rca` → `submit_rca`), `_advance_incident_after_rca` (EXIT, đã build) auto `apply_workflow("RCA hoàn tất - đóng sự cố")` → Incident `Closed` (loop đóng kín).

**Phân vai với `create_rca` (#8):** `create_rca` (gate `incident.acknowledge`=corrective) = KTV **tạo bản phân tích** RCA, KHÔNG đổi status Incident. `request_rca` (gate `compliance.submit`=governance) = quản trị tuân thủ **chốt sự cố PHẢI qua RCA** (đổi status Resolved→RCA Required, chặn close tới khi RCA Completed — BR-12-02). Hai endpoint phân vai rõ, cùng tồn tại.

---

### 8. create_rca / request_rca — thay hồ sơ RCA đã HỦY (CR-55, BR-12-27, ADR-IMM12-11) 🆕 SPEC

**Vấn đề (deadlock):** Incident High/Critical có `rca_record` trỏ RCA `status='Cancelled'` (do `cancel_rca` BR-12-22) bị KHÓA VĨNH VIỄN: `create_rca` raise 409 (rca_record tồn tại) ⇒ không tạo RCA thay thế; RCA Cancelled không bao giờ → `Completed` ⇒ `close_incident` raise `IMM12_CLOSE_RCA_INCOMPLETE` (BR-12-02) mãi ⇒ asset kẹt `Out of Service`.

**Fix (vị-từ "RCA CÒN SỐNG"):** cả 2 hàm dùng CHUNG helper `_has_live_rca(doc)` = `bool(doc.rca_record) ∧ frappe.db.exists("IMM RCA Record", rca_record) ∧ status != "Cancelled"`.

| Tình huống `rca_record` | `create_rca` | `request_rca` (reuse) |
|---|---|---|
| Không có / không tồn tại | Tạo RCA mới | `create_rca(name)` → tạo mới |
| Trỏ RCA `Cancelled` (**CR-55**) | `_has_live_rca`=False ⇒ **TẠO MỚI** + re-point `rca_record`; Cancelled cũ GIỮ NGUYÊN (audit) | `_has_live_rca`=False ⇒ **TẠO MỚI** (KHÔNG tái dùng huỷ) |
| Trỏ RCA `Required`/`In Progress`/`Completed` (**REGRESSION-GUARD**) | `_has_live_rca`=True ⇒ **raise `IMM12_RCA_ALREADY_EXISTS`** (409, in-handler HTTP-200) | reuse hồ sơ sống, KHÔNG tạo trùng |

> 🔒 **DONE-gate spec-contract (CR-55):** lỗi nghiệp vụ `IMM12_RCA_ALREADY_EXISTS` = **in-handler HTTP-200 + Error envelope** (409 bucket qua `nthrow`/`handle`), KHÔNG `raise`→HTTP-4xx. Cap-403 giữ 2-flavor cũ (dispatcher guest/no-token vs in-handler thiếu cap). KHÔNG field/endpoint/`@frappe.whitelist`/DocPerm mới ⇒ `oas_baseline` bất biến, KHÔNG migrate. Sau RCA mới hoàn tất (`start_rca`→`submit_rca`→`Completed`), `close_incident` High/Critical KHÔNG còn raise `IMM12_CLOSE_RCA_INCOMPLETE`; asset `Out of Service` → `Active` (deadlock gỡ end-to-end).

---

### 9b. start_rca — Bắt đầu phân tích (RCA Required → RCA In Progress) 🆕 SPEC

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm12.start_rca` |
| Cap-gate | `corrective.write` (in-handler cap-403) |
| Params | `name` (required) |

**Response success (Decision-B `_ok`):**
```jsonc
{ "success": true, "data": { "name": "RCA-2026-0012", "status": "RCA In Progress" } }
```

**Errors:**
| Code | Khi nào |
|---|---|
| `409` | status ≠ `RCA Required` → `IMM12_RCA_START_INVALID_STATE` — VN inline "Chỉ có thể bắt đầu phân tích khi phiếu ở trạng thái Cần phân tích" |
| `404` | RCA không tồn tại |
| `403` | in-handler cap-403 thiếu `corrective.write`; dispatcher-403 nếu guest/no-token |

**Side effect:** Audit `_log(...)` token **`rca_started`** (`RCA Required → RCA In Progress`).

---

### 10b. cancel_rca — Hủy RCA ({RCA Required, RCA In Progress} → Cancelled) 🆕 SPEC

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm12.cancel_rca` |
| Cap-gate | `corrective.write` (in-handler cap-403) |
| Params | `name` (required), `reason` (required) |

**Response success (Decision-B `_ok`):**
```jsonc
{ "success": true, "data": { "name": "RCA-2026-0012", "status": "Cancelled" } }
```

**Errors:**
| Code | Khi nào |
|---|---|
| `409` | status ∈ `{Completed, Cancelled}` → `IMM12_RCA_CANCEL_INVALID_STATE` — VN inline "Chỉ có thể hủy khi phiếu đang hoạt động (Cần phân tích hoặc Đang phân tích)" |
| `422` | thiếu `reason` (`IMM12_CANCEL_REASON_REQUIRED`) |
| `404` | RCA không tồn tại |
| `403` | in-handler cap-403 thiếu `corrective.write`; dispatcher-403 nếu guest/no-token |

**Side effect:** Audit `_log(...)` token **`rca_cancelled`**. Hủy RCA của Incident Major/Critical → `rca_status ≠ Completed` ⇒ `close_incident` vẫn chặn (BR-12-02) — hủy KHÔNG mở đường đóng-lách.

---

### 9. get_rca — augment allowed_transitions + can_manage_rca (BR-12-19) 🆕 SPEC

`get_rca(name)` trả thêm 2 field (parity `get_work_order` imm09.py:917) cho FE render CTA server-driven:

```jsonc
{
  "success": true,
  "data": {
    "name": "RCA-2026-0012",
    "status": "RCA In Progress",
    "allowed_transitions": ["Completed", "Cancelled"],   // = _RCA_VALID_TRANSITIONS[status]
    "can_manage_rca": 1,                                  // rbac.can("corrective.write") ? 1 : 0
    "incident_severity": "Critical"
    // ... các field RCA khác (root_cause, five_why_steps, linked_capa, ...)
  }
}
```

Ma trận `allowed_transitions`: `RCA Required → [RCA In Progress, Cancelled]` · `RCA In Progress → [Completed, Cancelled]` · `Completed`/`Cancelled → []`.

---

### Two-flavor 403 (DONE-gate spec-contract) — áp cho start/submit/cancel_rca

| Loại | Khi nào | HTTP | Body |
|---|---|---|---|
| **dispatcher-403** | guest / no-token gọi endpoint POST `@frappe.whitelist()` (không `allow_guest`) | 403 status-line | Frappe re-auth page (KHÔNG Decision-B) |
| **in-handler cap-403** | user đã đăng nhập nhưng thiếu capability `corrective.write` | **HTTP-200** | Decision-B Error envelope `{success:false, error:{code:"AUTH_FORBIDDEN"|"FORBIDDEN", ...}}` — KHÔNG raise→4xx |

> Lỗi nghiệp vụ (sai trạng thái, thiếu param, cap-403) = **in-handler HTTP-200 + Error envelope** (KHÔNG `raise`→HTTP-4xx). Chỉ dispatcher-403 (guest) mới là status-line thật. FE axios interceptor: 200-với-`success:false` → toast VN; KHÔNG echo `exc`/traceback (Finding C).

---

### 11. get_chronic_failures — Danh sách chronic assets ✅ LIVE

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm12.get_chronic_failures` |
| Role | Authenticated |
| Idempotent | Yes |

**Request:** No parameters

**Response success:**
```jsonc
{
  "success": true,
  "data": [
    {
      "asset": "ACC-ASSET-2026-00042",
      "asset_name": "Máy siêu âm GE Vivid E9",
      "department": "Tim mạch",
      "fault_code": "PROBE_DISCONNECT",
      "incident_count": 3,
      "first_incident": "2026-02-15",
      "last_incident": "2026-04-17",
      "rca_record": "RCA-2026-0007",
      "rca_status": "RCA Required",
      "rca_due_date": "2026-05-01",
      "related_incidents": ["IR-2026-0010", "IR-2026-0031", "IR-2026-0055"]
    }
  ]
}
```

---

### 12. get_dashboard — Dashboard ✅ LIVE

> **`get_dashboard` returns `{stats, active_incidents, open_rcas, chronic_failures}` — NOT KPI period breakdown.**

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm12.get_dashboard` |
| Role | Authenticated |
| Idempotent | Yes |

**Request:** No parameters

**Actual response structure:**
```jsonc
{
  "success": true,
  "data": {
    "stats": {
      "total": 42, "open": 5, "investigating": 3, "resolved": 8,
      "closed": 24, "cancelled": 2, "critical": 1, "high": 4,
      "open_total": 9,               // count(open_incident_filter()) = Open+Acknowledged+In Progress+RCA Required — BR-12-11 SoT card-count (KHÔNG chỉ status==Open)
      "critical_open": 1, "high_open": 2,  // count(open_incident_filter()∧severity) — BR-12-11b KPI-strip open-set (Closed/Cancelled/Resolved loại; critical_open<=critical, high_open<=high)
      "rca_pending": 2,
      "chronic": 1,                  // chronic_failure_count() = len(get_chronic_failures()) — BR-12-12 LIVE rolling-window nhóm (asset,fault_code) ≥3/90d; KHÔNG đếm cờ stale chronic_failure_flag. INVARIANT: == len(data.chronic_failures) (cùng SoT)
      "sla_response_breached": 2,    // sla_breach_count("response") = (response_breached=1) OR (đang-mở ∧ response_due_at<now ∧ chưa ack) — BR-12-13 LIVE predicate (KHÔNG còn count cờ stale)
      "sla_resolution_breached": 1   // sla_breach_count("resolution") = (resolution_breached=1) OR (đang-mở ∧ resolution_due_at<now) — BR-12-13 LIVE
    },
    "active_incidents": [...],   // open_incident_filter(): Open + Acknowledged + In Progress + RCA Required, by reported_at desc, top 10 — BR-12-11. MỖI row enrich is_response_breached/is_resolution_breached (0|1, derive LIVE — BR-12-13)
    "open_rcas": [...],          // RCA Required + RCA In Progress, by due_date asc, top 10
    "chronic_failures": [...]    // top 5 chronic groups — INVARIANT stats.chronic == len(chronic_failures) khi ≤5 nhóm (BR-12-12)
  }
}
```

> **SoT open-set guard (BR-12-11):** `stats.open_total` = `count(open_incident_filter())` = số incident ở MỌI state mở `{Open, Acknowledged, In Progress, RCA Required}` — KHÔNG chỉ `status==Open`. `active_incidents` dùng CHÍNH `open_incident_filter()` làm filter ⇒ số dòng (trước cắt limit 10) == `open_total`. FE card "Đang mở" bind `stats.open_total` + drill `/incidents/list?open=1` ⇒ **invariant: card count == số dòng list**.
>
> **Backward-compat:** key `open` (=count status==Open) và `investigating` (=count status==In Progress) GIỮ NGUYÊN cho consumer breakdown từng-state. Vòng 21 chỉ THÊM `open_total`.
>
> **KPI-strip open-set guard (BR-12-11b, vòng 29):** `stats.critical_open` / `stats.high_open` = `count(open_incident_filter({"severity": …}))` — đếm severity CHỈ trong open-set SoT, loại Closed/Cancelled/Resolved. FE KPI strip `IncidentListView.vue` tile "Sự cố nghiêm trọng đang mở" / "Sự cố mức cao đang mở" bind `stats.critical_open ?? 0` / `stats.high_open ?? 0` ⇒ trên drill `/incidents/list?open=1` strip == số dòng severity tương ứng trong bảng (1 Critical / 2 High), KHÔNG còn số global gồm Closed. Key `critical`/`high` (global, mọi-status) GIỮ NGUYÊN cho donut `severity_breakdown` + consumer cũ. Bất biến: `critical_open <= critical`, `high_open <= high`. CHỈ sinh qua `open_incident_filter()` (1 SoT — KHÔNG inline negative-list/tuple mới).
>
> **Chronic SoT guard (BR-12-12, vòng 3/50):** `stats.chronic` = `chronic_failure_count()` = `len(get_chronic_failures())` — đếm **số nhóm `(asset, fault_code)` LIVE** trong cửa sổ trượt 90 ngày (`GROUP BY HAVING >= 3`, `status != Cancelled`), **KHÔNG** đếm cờ bền vững `chronic_failure_flag`. **INVARIANT 1 màn hình:** trên cùng payload, `stats.chronic == len(data.chronic_failures)` (cả hai phái sinh từ `get_chronic_failures()`) ⇒ tile dashboard (`IMM12DashboardView.vue:106`) == panel (`:221-234`), KHÔNG còn 2 con số mâu thuẫn. **Lifecycle:** khi cụm cũ aged-out >90d (cờ vẫn =1 trên incident cũ) ⇒ không còn nhóm live ⇒ `stats.chronic` GIẢM về `0` (định nghĩa cũ "đếm cờ" giữ tile >0 vĩnh viễn = bug đã fix). Cờ `chronic_failure_flag` GIỮ NGUYÊN cho badge per-row *"Lặp lại"* — lifecycle riêng (BR-12-03 audit/RCA grouping), KHÔNG đổi. Endpoint `get_incident_stats()` đã delegate service-layer (round-29) ⇒ key `chronic` mới tự lộ, KHÔNG đụng `api/imm12.py`.
>
> **SLA-breach LIVE SoT guard (BR-12-13, vòng 4):** `stats.sla_response_breached` = `sla_breach_count("response")`, `stats.sla_resolution_breached` = `sla_breach_count("resolution")` — predicate **`(cờ=1) OR (đang-mở ∧ quá-hạn-live)`** (`open_incident_filter()` ∧ `<kind>_due_at < now()`; response kèm `acknowledged_at` unset). **KHÔNG còn** `count(response_breached=1)`/`count(resolution_breached=1)` đơn lẻ → kill **undercount cửa-sổ-trễ-scheduler** (incident vừa quá hạn, cờ chưa stamp vẫn được đếm). **Idempotent:** sau khi scheduler `check_incident_sla_breach()` stamp cờ, KPI KHÔNG đổi (incident đã đếm vì live nay đếm vì cờ — 2 nhánh exclusive). **Terminal exclude:** Cancelled/Closed/Resolved đóng-đúng-hạn KHÔNG phantom-count (chỉ qua nhánh cờ=1 nếu lịch sử từng breach). Endpoint delegate service-layer ⇒ KHÔNG đụng `api/imm12.py`.
>
> **DELTA per-row enrich (BR-12-13):** `list_incidents().items[]` + `get_dashboard().active_incidents[]` MỖI row thêm `is_response_breached` / `is_resolution_breached` (`0|1`) — derive LIVE cùng predicate `sla_breach_filter` trên từng row (in-Python, KHÔNG query thêm). FE đọc field **derived** `is_*_breached` (KHÔNG cờ thô) ⇒ **badge live == tile**. Cờ thô `response_breached`/`resolution_breached` GIỮ trong payload (backward-compat). `list_incidents` field list THÊM `response_due_at`, `resolution_due_at` (đã có `acknowledged_at`+cờ+status); `active_incidents` THÊM `response_due_at`, `resolution_due_at`, `acknowledged_at`. **SELF-CORRECTION (CR-21, round 4 — supersede "out-of-scope"):** bản trước ghi *"`get_incident_detail` giữ expose cờ thô cho trang chi tiết — out-of-scope vòng này"*. CHỐT LẠI: `get_incident_detail` NAY cũng enrich `is_response_breached`/`is_resolution_breached` (derive LIVE, CÙNG helper `_enrich_sla_breach` với list/dashboard) → màn Chi tiết đọc cờ **derived** (server-flag), badge Chi tiết == badge danh sách == tile TẠI CÙNG `now` (INV-SLA-5 mở rộng sang detail). Chi tiết + Boundaries + ADR: **§17**.

Use `get_incident_stats()` endpoint for per-status KPI counts (incl. `open_total` SoT card-count, BR-12-11) — endpoint delegates the service-layer function, returning the same `stats` shape embedded in `get_dashboard`.

---

### 3. list_incidents — filter `mine` (tab "Báo hỏng của tôi", MVP-5c) ✅ SPEC (BE Bước-4)

> **Mục tiêu (A2 known-gap closure):** màn mobile `MyWorkOrdersView` › tab **"Báo hỏng của tôi"** cần CHỈ incident do chính KTV tạo. Contract mobile (`docs/mobile/openapi/…listIncidents`) TRƯỚC vòng này CLAIM "scope reported_by" nhưng `list_incidents` KHÔNG có cơ chế ⇒ **claim suông** (contract nói dối). Vòng này wire param `mine` để contract TRUNG THỰC.

**Param mới:** `mine` (int `0|1`, default `0`, `in:query`) — bổ sung vào `list_incidents(status, severity, asset, open, page, page_size)` → `list_incidents(status, severity, asset, open, mine, page, page_size)`.

| `mine` | Hành vi | Filter áp |
|---|---|---|
| `0` / absent | **UNCHANGED** (backward-compat) — list permission-aware như cũ; web-FE `IncidentListView` KHÔNG đổi | KHÔNG seed `reported_by` |
| `1` | **Scope reported_by** — chỉ incident `reported_by == frappe.session.user` | `extra["reported_by"] = frappe.session.user` |

**BR-12-14 (mine self-scope — application filter, KHÔNG phải security boundary):**
- `mine=1` áp filter `reported_by == frappe.session.user` (giải quyết session ở **service-layer**, KHÔNG ở API — API chỉ forward int).
- **AND với mọi filter khác KỂ CẢ nhánh status return-sớm:** `_build_incident_filters` seed `extra["reported_by"]` **TRƯỚC** quyết định nhánh ⇒ cả 3 nhánh (`if status: return extra` · `if open_only: return open_incident_filter(extra)` · `return extra`) đều mang `reported_by`. Ví dụ: `mine=1&open=1` = incident của tôi đang mở (`reported_by` ∧ `open_incident_filter()` cùng AND); `mine=1&status=Cancelled` = incident của tôi đã huỷ (status branch return-sớm vẫn có `reported_by`).
- **INVARIANT count==rows (INV-12-LIST):** `frappe.db.count(_DT_INCIDENT, filters)` + `frappe.get_all(_DT_INCIDENT, filters)` dùng **CÙNG** `filters` dict đã có `reported_by` ⇒ `pagination.total == len(items)` khi `mine=1`. KHÔNG đếm trên dict khác (chống count-vs-rows drift — memory `asset_list_count_drill_technician`).
- **Blast-radius fence ĐO ĐƯỢC:** `mine=0`/absent ⇒ `filters` BYTE-IDENTICAL với trước vòng này (1 nhánh điều kiện `if mine:` duy nhất). Test fence: incident của reporter khác VẪN xuất hiện khi `mine=0` (chứng minh `reported_by` không bị áp ngầm).
- **Quyền (2 lớp 403 — DONE-gate spec-contract):** `list_incidents` chỉ dispatcher-403 (Guest → 401 in-handler `_err`, guard `api/imm12.py:212` **UNCHANGED**); KHÔNG thêm in-handler cap-403. Read-gating GIỮ qua DocPerm/permission_query "Incident Report" (`corrective.read`). `mine=1` là filter **opt-in** chồng LÊN scope quyền (không thay quyền): KTV `corrective.read` gọi `mine=1` → 200 + chỉ incident của mình ⇒ **KHÔNG leak** incident của reporter khác (vì `reported_by` tường minh, không phụ thuộc get_all bỏ qua permission_query).

**Boundaries (Always / Never):**
- **Always:** seed `reported_by` ở `_build_incident_filters` TRƯỚC mọi `return` (phủ nhánh status); giải quyết `frappe.session.user` ở service-layer; `mine` int `0|1` (mirror `open` — né int-vs-bool trap); contract OpenAPI + cơ-chế khớp nhau.
- **Never:** áp `reported_by` khi `mine=0` (vỡ backward-compat web-FE); đếm `total` trên filters dict khác `get_all` (vỡ count==rows); thêm endpoint mới `list_my_incidents` (+1 path — vỡ "path count UNCHANGED"); auto-scope mọi read theo `reported_by` qua permission_query (vỡ view manager/QA cần thấy TẤT CẢ).

### ADR-IMM12-05: Opt-in `mine` query-param vs endpoint riêng vs permission auto-scope
- **Status**: Accepted · **Date**: 2026-06-28 · đồng-bộ [`ADR-MOBILE-015`](../mobile/ADR-MOBILE-015.md)
- **Context**: tab "Báo hỏng của tôi" (MVP-5c) cần self-scope `reported_by`, NHƯNG web-FE `IncidentListView` (manager/QA) cần thấy mọi incident; contract đã claim "scope reported_by" mà thiếu cơ chế; ràng buộc "path count UNCHANGED" + "count==rows".
- **Decision**: thêm **1 query-param opt-in `mine`** (default 0 = cũ; 1 = filter `reported_by==session.user`) ANDed vào CÙNG `filters` dict.
- **Alternatives**: (A) endpoint riêng `list_my_incidents` → +1 path (vỡ ràng buộc) + nhân đôi pagination/enrich/contract surface → loại. (B) auto-scope mọi read theo `reported_by` qua `permission_query_conditions` → vỡ view manager/QA + đổi security-semantics + count-vs-rows cho persona không-self → loại.
- **Consequences**: blast-radius = 1 nhánh `if mine:` + 1 param; backward-compat tuyệt đối; codegen mobile sinh client truyền `mine=1` cho tab; KHÔNG migration DB. Đánh đổi: `mine` là filter ứng-dụng (KHÔNG phải hàng-rào-bảo-mật) — bảo mật read VẪN do DocPerm/permission_query đảm trách.

> **DELTA vòng này (so với bản trước):** (1) catalog row #3 + signature thêm param `mine`; (2) BR-12-14 + ADR-IMM12-05 mới; (3) đồng bộ contract mobile (OpenAPI `IncidentMine`, `04-api-contract §6.1/§8.4`, ADR-MOBILE-015). **BE Bước-4 delta** (KHÔNG thuộc file doc này): `services/imm12.py` (`_build_incident_filters(..., reported_by="")` seed + `list_incidents(..., mine=0)` resolve session), `api/imm12.py` (`list_incidents(..., mine: int = 0)` forward — guard:212 UNCHANGED), tests (`test_imm12` mine-filter+fence, `test_mobile_oas` IncidentMine param).

---

### 15. attach_incident_photo — Đính ảnh bằng chứng hiện trường (NĐ98) 🟡 SPEC (BE/FE Bước-4)

> **Mục tiêu (mobile CR-17/G6 — endpoint DUY NHẤT còn thiếu trong contract):** KTV hiện trường chụp ảnh sự cố (thiết bị hỏng, hiện trạng phòng máy) → đính **trực tiếp** vào phiếu báo hỏng làm **bằng chứng NĐ98** (evidence trail điều tra sự cố TTBYT). Web-FE `IncidentDetailView` + mobile `IncidentDetailView` cùng đọc `scene_photos` (parity chi tiết). Đây là **write-path multipart** ĐẦU TIÊN của IMM-12.

**Endpoint:** `POST assetcore.api.imm12.attach_incident_photo`

**Request — `multipart/form-data`** (KHÁC mọi endpoint imm12 khác dùng JSON-RPC form_dict):

| Phần | Nguồn | Bắt buộc | Ghi chú |
|---|---|---|---|
| `incident_name` | form-field / query (`frappe.form_dict`) | ✅ | tên Incident Report đang mở |
| `file` | `frappe.request.files["file"]` (binary) | ✅ | ảnh JPG/PNG; đọc `upload.stream.read()` (pattern `imm00.upload_device_model_file` `imm00.py:1576`) |

**Response 200 — success (Decision-B):**
```jsonc
{ "success": true, "data": { "file_url": "/private/files/scene_xxx.jpg", "file_name": "scene_xxx.jpg" } }
```

**Side-effects khi success (BR-12-17 + BR-12-18):**
1. Sinh **đúng 1** `File` **private** (`attached_to_doctype="Incident Report"`, `attached_to_name=<incident>`, `is_private=1`).
2. Sinh **đúng 1** `Asset Lifecycle Event` `event_type="incident_photo_attached"` (`asset=incident.asset`, `actor=frappe.session.user`, `timestamp=now`, `root_doctype="Incident Report"`, `root_record=<incident>`) — evidence trail NĐ98, **KHÔNG ghi im lặng** (KHÔNG try/except-swallow như `incident_reported`; audit là 1 phần của success-unit).

**Bảng lỗi (tất cả in-handler HTTP-200 + Error envelope — Decision-B, KHÔNG raise→4xx):**

| Nhánh | `success` | `code` | `http_status` | `fields` | File tạo? |
|---|---|---|---|---|---|
| **Guest/no-session** | — | — | **403 (dispatcher)** | — | ❌ (chặn TRƯỚC handler; `@frappe.whitelist` KHÔNG `allow_guest`) |
| Không phải reporter **VÀ** không `incident.write` trên phiếu | `false` | `FORBIDDEN` | 403 | — | ❌ (in-handler cap-403; check TRƯỚC khi tạo File) |
| Incident không tồn tại | `false` | `NOT_FOUND` | 404 | — | ❌ |
| Thiếu `file` | `false` | `VALIDATION` | 422 | `{file: "Thiếu tệp ảnh"}` | ❌ |
| Content-type KHÔNG phải ảnh (jpg/png) | `false` | `VALIDATION` | 422 | `{file: "Tệp phải là ảnh JPG hoặc PNG"}` | ❌ |
| Size > cap (`MAX_INCIDENT_PHOTO_BYTES` = 10 MB — **LIVE** `10*1024*1024` `services/imm12.py:48`) | `false` | `VALIDATION` | 422 | `{file: "Ảnh vượt quá dung lượng cho phép (tối đa 10 MB)"}` | ❌ |
| Đã đủ 5 ảnh (`len(scene_photos) >= MAX_INCIDENT_PHOTOS=5`) | `false` | `VALIDATION` | 422 | `{file: "Tối đa 5 ảnh"}` | ❌ |
| Ảnh hỏng / đứt-truyền (`UnidentifiedImageError`\|`OSError` khi `File.insert` → `strip_exif`/PIL `services/imm12.py:1040-1051`) | `false` | `VALIDATION` | 422 | `{file: "Tệp ảnh bị lỗi hoặc không đọc được, vui lòng chụp/chọn lại."}` | ❌ (PIL fail TRONG `before_insert` — TRƯỚC db_insert/write_file ⇒ KHÔNG orphan) |

> **HEIC/HEIF (chốt cross-module — canonical ADR-IMM08-PHOTO-04):** allowlist BE **GIỮ** `{image/jpeg, image/jpg, image/png}` (3 giá-trị — `_INCIDENT_PHOTO_CONTENT_TYPES` `services/imm12.py:49`; `image/jpg` là alias một-số-client gửi). iPhone chụp HEIC/HEIF **PHẢI được app mobile transcode → JPEG TRƯỚC upload** (fix tại-nguồn, 0 dependency BE, JPEG xem được trong web-audit). BE-transcode (pillow-heif) = `[ROADMAP]` fallback (measure-first); mở-allowlist-nhận-HEIC = **loại** (HEIC không render trên trình duyệt). Chi tiết + alternatives: `docs/imm-08/05_API_Specification.md` ADR-IMM08-PHOTO-04. **Lưu ý imm12 MAX=5** (scene-photo cả phiếu, KHÁC imm08/09 MAX=1 per-item) — HEIC policy CHUNG, MAX policy RIÊNG theo domain.

**2 loại 403 (DONE-gate spec-contract):**
- **dispatcher-403** = Guest/no-token → Frappe dispatcher chặn TRƯỚC khi vào handler (status-line 403 thật). Nhất quán mọi endpoint imm12 POST khác.
- **in-handler cap-403** = đã đăng nhập nhưng không phải reporter và thiếu `incident.write` → `_err(_MSG_FORBIDDEN, ErrorCode.FORBIDDEN)` → HTTP-200 body Decision-B `code=FORBIDDEN`, `http_status=403`. **KHÔNG leak** raw cap.

**Thứ tự thực thi (BẮT BUỘC — mọi nhánh reject TRƯỚC khi ghi File):** Guest → exists(incident) → permission (reporter/write) → file present → content-type → size → max-count → `File.insert(is_private=1)` → `create_lifecycle_event(incident_photo_attached)` → `frappe.db.commit()` → `_ok`.

**Permission model (BR-12-17):**
```
is_reporter = (incident.reported_by == frappe.session.user)
has_write   = frappe.has_permission("Incident Report", ptype="write", doc=incident_name)
allowed     = is_reporter OR has_write
```
- `frappe.has_permission(..., doc=...)` áp CẢ role-DocPerm write LẪN row-level `has_permission` hook (vendor isolation) ⇒ **tái dùng IDOR-guard AUTH-10** (`assert_vendor_can_access` `services/shared/scope.py:182` / `api/imm12.py:232`): Vendor Engineer ngoài scope được giao → `has_write=False` → FORBIDDEN.
- Reporter luôn được đính ảnh phiếu của chính mình (bằng chứng do KTV báo hỏng cung cấp).

**Boundaries (Always / Never):**
- **Always:** File `is_private=1` (NĐ98 — ảnh sự cố thiết bị y tế KHÔNG public); check permission + validation + max-count TRƯỚC `File.insert`; emit ĐÚNG 1 lifecycle event `incident_photo_attached` per success (không swallow); `scene_photos` derive read-time từ `File` (KHÔNG denormalize field trên Incident Report → không drift); dùng CÙNG helper `_scene_photos(name)` cho cả max-count check LẪN liệt kê detail (invariant **count==rows**).
- **Never:** tạo File ở nhánh reject; `is_private=0`; raise `frappe.throw`→HTTP-4xx cho lỗi nghiệp vụ (phải Decision-B HTTP-200); dùng `event_type="failure_reported"` (KHÔNG có trong Select `Asset Lifecycle Event`) hay bịa event mới ngoài `incident_photo_attached`; leak raw cap trong message FORBIDDEN; rò field web-only mới ngoài `scene_photos` khi thêm parity.

> 📱 **Mobile-BE contract (CR-17/G6 — path `multipart/form-data` ĐẦU TIÊN của mirror):** `attach_incident_photo` ĐÃ được bồi vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (opId `attachIncidentPhoto`, POST-only, path/opId **58→59**). requestBody = **`multipart/form-data` DUY NHẤT** (`$ref AttachIncidentPhotoRequest` closed `req[incident_name,file]`, `file:{type:string,format:binary}` — **KHÔNG `application/json`/`x-www-form-urlencoded`** vì server đọc `frappe.request.files["file"]`, KHÔNG `form_dict`). **200 = oneOf [`AttachIncidentPhotoEnvelope` \| `Error`]** (Decision-B route-by-VALUE `body.success`, 0 discriminator); `AttachIncidentPhotoResponse` closed EXACT 2-prop `req[file_url,file_name]` (grounded `services/imm12.py:1064`); nhánh `Error.http_status` ⊇ **{403,404,422}** khớp ladder 7 nhánh trên (gồm nhánh **corrupt** @1040-1051). slot `{200,401,403}` — **`403 Forbidden` SINGLE-SHAPE** (dispatcher-403 guest/no-token; in-handler cap-403 đã phủ bởi nhánh Error 200-oneOf ⇒ KHÔNG dual-403 như `reportIncident`; mirror `acknowledgeIncident` ADR-MOBILE-006). Membership `_MVP_BUSINESS_PATHS` + `_MVP_ACTION_ENVELOPE`; media-type guard mở-rộng hằng RIÊNG `_ATTACH_INCIDENT_PHOTO_BODY_MEDIA_TYPES={"multipart/form-data"}`. **CONTRACT-ONLY** (BE LIVE, pure-yaml). Spec đầy đủ + Alternatives + handoff BE: [`docs/mobile/04-api-contract.md §8.33`](../mobile/04-api-contract.md) · [`ADR-MOBILE-027.md`](../mobile/ADR-MOBILE-027.md). Đây là template cho **CR-14/CR-15** (ảnh checklist PM/CM — cùng family multipart, MAX=1/item KHÁC incident MAX=5).

### 15a. attach_incident_photo — Idempotency `client_request_id` (CR-24 phần dư · B-rel-3) 🆕 SPEC (BE Bước-4, vòng 3 2026-07-16)

> **Mục tiêu.** Đóng **cửa sổ attachment-dup** — parity `report_incident` §1a. Mobile drain outbox PHA-2 (đính ảnh theo `photoCursor` sau khi phiếu đã có `incidentName`): nếu response `attach_incident_photo` **rớt mạng SAU khi server đã tạo File**, client không advance cursor → re-drain **re-POST cùng ảnh** → **File TRÙNG + lifecycle event `incident_photo_attached` TRÙNG** (bẩn evidence-trail NĐ98 — 2 event cho 1 bằng chứng thực).
>
> **Vì sao Frappe không tự đóng (backend-confirm (a)):** Frappe **KHÔNG có cơ chế idempotency request-level** cho whitelisted RPC. `File.validate_duplicate_entry` (`frappe/core/doctype/file/file.py:413-441`) khi trùng `content_hash`+`attached_to` CHỈ **reuse `file_url`** (đỡ ghi đĩa) — VẪN insert **ROW File mới** + service VẪN emit **event lần 2** ⇒ không phải idempotency. Phải tự dedupe app-level (precedent ADR-MOBILE-047).

**Param mới (AC1 — land ATOMIC handler + service + OAS + guard, KHÔNG pure-yaml):**

- `api/imm12.py::attach_incident_photo` (@:295): thêm `client_request_id: str = ""` **TƯỜNG MINH** vào signature (hiện bị `**_ignore` nuốt câm — client gửi cũng vô tác dụng). `**_ignore` **GIỮ** (vẫn nuốt kwargs spoof KHÁC). KHÔNG `str|None` (tránh HTTP-417 coercion). Docstring ghi CR-24/B-rel-3. Pass-through: `handle(svc_attach_photo, incident_name, filedata=..., filename=..., content_type=..., client_request_id=client_request_id)`.
- `services/imm12.py::attach_incident_photo` (@:1147): thêm keyword param `client_request_id: str = ""` + dedupe 2 lớp (pre-check + unique race-handler) — thuật toán & field schema: **`04 §2.1b` + ADR-IMM12-10**.

**Hành vi (BR-12-26):**

| Trường hợp | Kết quả |
|---|---|
| Cùng `client_request_id` + CÙNG incident, POST 2× (AC2) | **1 File + 1 lifecycle event.** Call#2 → dedupe-hit → success envelope Decision-B `{success:true, data:{file_url,file_name}}` của File **ĐÃ đính lần 1** (file_url/file_name khớp). KHÔNG insert File, KHÔNG emit `incident_photo_attached` lần 2. Shape response KHÔNG đổi (EXACT 2-key — guard (e) GIỮ). |
| `client_request_id` rỗng/thiếu (AC3) | **At-least-once CŨ NGUYÊN VẸN** — mỗi call tạo File mới (field không set → NULL). Backward-compat 100%: web FE + toàn bộ test imm12 cũ không đổi. |
| Cùng key nhưng **KHÁC incident** (AC4) | **KHÔNG dedupe chéo** — 2 File riêng (dedupe scope = `(incident_name, client_request_id)`; chỉ match File sinh từ đúng flow attach của incident đó — File không mang key/flow khác KHÔNG bao giờ match). |
| 2 key KHÁC nhau, cùng incident | 2 File riêng (2 ảnh khác nhau của cùng phiếu). |
| 2 request CONCURRENT cùng key + cùng incident (race) | 1 File — lớp-2 unique constraint chặn kẻ thua → race-handler re-read → return winner (parity ADR-MOBILE-047 lớp-2). Kẻ thua raise TRƯỚC emit event ⇒ vẫn đúng 1 event. |

**Thứ tự thực thi MỚI (delta vs §15 — chèn 1 bước):** Guest → exists(incident) → permission (reporter/write) → **`dedupe pre-check` (key truthy + trúng → early-return File cũ)** → file present → content-type → size → max-count → `File.insert` (persist scoped key) → `create_lifecycle_event` → `commit` → `_ok`.
- **Dedupe SAU permission:** chặn probe key → leak `file_url` phiếu người khác (khác `report_incident` — ở đó cap-gate `corrective.create` nằm API-tier trước handle).
- **Dedupe TRƯỚC file-present/max-count:** replay của ảnh thứ 5 phải trả success (File đã đính), KHÔNG dội `VALIDATION "Tối đa 5 ảnh"`; idempotent-replay trả kết quả đã ghi bất kể body lần 2.

**Backend-confirm (task AC5 — chi tiết + alternatives: `04 §2.1b` ADR-IMM12-10):**
- **(a)** Frappe KHÔNG có idempotency sẵn (evidence trên) → tự dedupe app-level 2 lớp.
- **(b)** Khoá đi trong **body field `client_request_id`** (multipart form part) — parity `report_incident`; KHÔNG dùng header `Idempotency-Key` (Frappe RPC không route header sạch — ADR-MOBILE-047 Alt-A).
- **(c)** **KHÔNG TTL** — key sống cùng File record (parity ADR-MOBILE-047 Alt-D); File bị xoá → key biến mất → replay sau đó tạo File mới (chấp nhận, ghi Consequences ADR-IMM12-10). 0 cleanup job.

**Key per-photo (client contract — ghi vào OAS description + handoff mobile):** mỗi **ảnh** = 1 key RIÊNG, ổn định qua mọi re-drain của CÙNG ảnh (vd `${item.id}#p${photoCursor}` — item.id outbox + STT ảnh). **KHÔNG tái dùng** key của `report_incident` hay của ảnh khác cùng phiếu — tái dùng ⇒ ảnh sau bị dedupe nhầm thành ảnh trước → **mất ảnh im lặng**.

**📱 OAS mirror delta (COUPLED — guard live-sig parity sẽ RED nếu yaml đi trước handler):**
- `docs/mobile/openapi/assetcore-mobile.openapi.yaml` schema `AttachIncidentPhotoRequest` (@:5260-5282): THÊM property
  ```yaml
  client_request_id:
    type: string
    description: >-
      OPTIONAL — idempotency key per-ảnh (CR-24/B-rel-3, mobile write-outbox re-drain). Cùng key +
      cùng incident gọi lặp ⇒ trả File ĐÃ đính (KHÔNG File/event trùng). Mỗi ảnh 1 key RIÊNG, ổn định
      qua re-drain; KHÔNG tái dùng key ảnh khác (bị dedupe nhầm → mất ảnh). Rỗng/thiếu ⇒ hành vi cũ.
  ```
  `additionalProperties: false` **GIỮ** (schema ĐÓNG — 3 props; **KHÁC** `ReportIncidentRequest` OPEN cố ý §1a); `required[]` **GIỮ EXACT** `[incident_name, file]` — `client_request_id` ∉ required. **Curate mô tả @source VERBATIM** sau khi handler/service land (line-ref thật, không đoán). 0 path/opId mới → **path-count GIỮ 91**.
- **Guard coupling (`test_mobile_oas.py`) — cập nhật CÙNG lượt:**
  1. `_ATTACH_INCIDENT_PHOTO_REQUEST_PROPS` (@:1114) `{incident_name, file}` → `{incident_name, file, client_request_id}`; `_ATTACH_INCIDENT_PHOTO_REQUEST_REQUIRED` (@:1113) **GIỮ** `["file", "incident_name"]` ⇒ guard (c) (@:17265-17271) tự phủ props-EXACT-3 + required-EXACT-2 + closed GIỮ. +assert `client_request_id` type `string`.
  2. Guard (h) live-sig parity (@:17357-17375): non-var params `{incident_name}` → `{incident_name, client_request_id}`; assert `**_ignore` VAR_KEYWORD **GIỮ**.
  3. Khuyến nghị +TC class `TestMobileAttachPhotoIdempotencyContract` (mirror `TestMobileReportIncidentIdempotencyContract` ADR-047: prop-exists / ∉required+closed-GIỮ / handler-parity) — RED-before proof phía contract.
  4. Đồng bộ counter `_EXPECTED_TEST_COUNT` + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` + `_GUARD_SUITE_SUM` + `_MOBILE_OAS_TOTAL` (test_mobile_docset) — **đọc số FRESH tại thời điểm code** (multi-session drift; số trong doc này có thể cũ).
  5. Comment/docstring guard còn line-ref trôi (`api/imm12.py:273/293`, `services/imm12.py:995/1064` — thực tế :295/:314, :1147/:1216) — CHỈ comment, 0 assertion; refresh nếu tiện (cùng loại T2 STATE).

**Errors:** KHÔNG thêm nhánh lỗi mới — dedupe-hit là success path (HTTP-200 envelope). Bảng lỗi §15 giữ nguyên; `Error.http_status` enum không đổi.

**DoD (AC6):** `bench --site miyano run-tests` cho `test_imm12` (TC-12-PHOTO-IDEMP-01..07, xem `07 §III.2`) + `test_mobile_oas` + `test_mobile_docset` → 'Ran N OK' THẬT; **RED-before**: chưa có dedupe → TC-01 FAIL (2 File). FE vitest + vue-tsc PASS (web FE 0 file đổi — kỳ vọng pass nguyên trạng). **Deploy-note:** `.py` đổi → cần **gunicorn reload (`--preload` staleness — HARD-STOP USER, chỉ ghi chú)**; Custom Field fixture → `bench migrate`/`import-fixtures` trên dev (được phép round này) — HTTP live chờ user reload. KHÔNG git commit.

**OUT-OF-SCOPE vòng này (backlog [AUTO] vòng kế):** (1) cùng pattern dedupe cho `attach_pm_checklist_photo` (imm08) + `attach_repair_checklist_photo` (imm09) — cân nhắc generalize helper/registry khi làm (ADR-IMM12-10 Alt-D); (2) idempotency cho `close_work_order`/`submit_pm_result`/`receive_transfer` (contract chỉ khuyến nghị); (3) CR-28b PM server due-filter.

### 16. get_incident_detail — parity `scene_photos[]` (mobile + web) 🟡 SPEC (BE Bước-4)

`get_incident_detail(name)` (endpoint #2 `get_incident`) trả **THÊM** property:
```jsonc
"scene_photos": [ { "file_url": "/private/files/scene_a.jpg", "file_name": "scene_a.jpg" }, ... ]  // [] khi chưa có ảnh
```
- Nguồn: `_scene_photos(name)` = `frappe.get_all("File", filters={attached_to_doctype:"Incident Report", attached_to_name:name, is_private:1}, fields=["file_url","file_name"])` lọc ảnh (`.jpg/.jpeg/.png`). **1 SoT** — chính helper dùng cho max-count trong `attach_incident_photo` ⇒ **count==rows** (số dùng chặn ảnh-thứ-6 == số liệt kê `scene_photos`).
- List rỗng khi chưa đính (KHÔNG null → FE/mobile map an toàn).
- **KHÔNG rò field web-only khác** (chỉ +`scene_photos`; `IncidentDetail` mobile `additionalProperties:true` GIỮ NGUYÊN — xem `04-api-contract §3.2`).
- Mobile contract: `IncidentDetail += scene_photos: array<{file_url,file_name}>` (KHÔNG vào `required`; mirror pattern optional-emit `allowed_transitions`).

### ADR-IMM12-06: Lưu ảnh hiện trường = Frappe `File` private + derive `scene_photos` (KHÔNG child table / KHÔNG denormalize)
- **Status**: Accepted · **Date**: 2026-07-09
- **Context**: cần đính n ảnh bằng chứng NĐ98 vào Incident Report, đọc lại ở cả web + mobile; NĐ98 yêu cầu kiểm soát truy cập ảnh sự cố TTBYT; ràng buộc "endpoint DUY NHẤT còn thiếu" (không nở schema lớn).
- **Decision**: dùng hạ tầng `File` native của Frappe (`is_private=1`, `attached_to_*` trỏ về Incident) làm store; `scene_photos` **derive read-time** trong `get_incident_detail` (KHÔNG lưu mảng URL trên doctype).
- **Alternatives**: (A) child table `incident_photos` (URL rows) → nhân đôi hạ tầng File + tự quản permission/cleanup + drift giữa row và File thật → loại. (B) File public → vỡ kiểm soát truy cập NĐ98 → loại. (C) denormalize `scene_photos` JSON field → drift khi File bị xoá/đổi → loại.
- **Consequences**: 0 field mới trên `Incident Report`; 0 child table; permission ảnh thừa hưởng File-attach của Frappe; cleanup ảnh theo cascade File khi xoá incident. Đánh đổi: mỗi lần detail phải query `File` (n≤5, chi phí ~0).

### ADR-IMM12-07: Audit đính ảnh = canonical `Asset Lifecycle Event` `incident_photo_attached` (thêm option Select) — hard-requirement, KHÔNG best-effort
- **Status**: Accepted · **Date**: 2026-07-09
- **Context**: NĐ98 đòi evidence trail cho MỌI thao tác trên hồ sơ sự cố; `Asset Lifecycle Event.event_type` là **Select enum cố định** (`asset_lifecycle_event.json`) — ghi giá trị ngoài options sẽ throw / bị nuốt (đã ghi nhận ở `04 §6.1`, `services/imm12.py:480`); `incident_photo_attached` CHƯA có trong enum.
- **Decision**: (1) **THÊM option `incident_photo_attached`** vào Select `event_type` của `Asset Lifecycle Event` (schema change → deploy `bench reload-doctype "Asset Lifecycle Event"`); (2) emit canonical lifecycle event ở success-path của `attach_incident_photo`, coi là **hard-requirement** (nằm trong transaction, commit cùng File) — KHÁC `incident_reported` (best-effort try/except-swallow) vì đây là **bản ghi bằng chứng** không được phép mất im lặng.
- **Alternatives**: (A) chỉ ghi `IMM Audit Trail` `event_type="Incident"` generic → không phân biệt được thao tác "đính ảnh" trong timeline + lệch trục §10 → loại. (B) best-effort swallow như `incident_reported` → ảnh đính mà audit rớt im lặng = vi phạm "KHÔNG ghi im lặng" → loại. (C) đặt tên `photo_attached`/`evidence_attached` → kém rõ ngữ cảnh incident → chọn `incident_photo_attached` (đối xứng `incident_reported`).
- **Consequences**: +1 option enum (migration nhẹ, reload-doctype — KHÔNG data migration); timeline thiết bị hiện đúng "Đính ảnh bằng chứng"; test khẳng định **đúng 1** event/lần success; nếu event insert lỗi → cả File rollback (chưa commit) ⇒ không orphan, không silent.

### 17. get_incident_detail — parity cờ SLA-breach DERIVED (`is_response_breached`/`is_resolution_breached`) 🟡 SPEC (BE/FE Bước-4 · mobile CR-21)

> **Mục tiêu (mobile CR-21):** màn **Chi tiết sự cố** (web `IncidentDetailView` + mobile `IncidentDetailView`) hiện tình trạng SLA phải KHỚP danh sách + dashboard **tại cùng thời điểm** — badge Chi tiết KHÔNG được lệch (stale-divergence) khi cờ thô `response_breached`/`resolution_breached` chưa được scheduler stamp. Cách sửa: đưa CÙNG derived-flag `is_*_breached` (đã có ở list/dashboard, BR-12-13) sang response `get_incident_detail`.

**Endpoint:** `GET assetcore.api.imm12.get_incident` (endpoint #2 → service `get_incident_detail(name)`). Auth/handler **KHÔNG đổi**: Guest → 401; đăng nhập → AUTH-10 IDOR guard (`assert_vendor_can_access("Incident Report", name)`, `api/imm12.py:228`) → `handle(_run)` Decision-B `_ok(...)`.

`get_incident_detail(name)` trả **THÊM đúng 2** property (đối xứng `IncidentListItem` đã curate — KHÔNG kéo theo field web-only khác):

```jsonc
"is_response_breached":   0,   // int 0|1 — derive LIVE (== _row_is_breached(row,"response"))
"is_resolution_breached": 1    // int 0|1 — derive LIVE (== _row_is_breached(row,"resolution"))
```

- **Nguồn:** `_enrich_sla_breach([data])` (`services/imm12.py`) — CHÍNH helper dùng cho `list_incidents` + `get_dashboard().active_incidents`. **1 SoT predicate** `_row_is_breached(row, kind, now)` = `(cờ_kind=1)` OR `(status ∈ INCIDENT_OPEN_STATES ∧ <kind>_due_at < now [∧ response: chưa acknowledged_at])`. KHÔNG re-implement predicate ở màn Chi tiết.
- **Cờ thô GIỮ NGUYÊN** trong payload (`response_breached`/`resolution_breached`, backward-compat) — chỉ THÊM 2 derived; consumer KHÔNG còn **buộc** đọc cờ thô stale.

**Invariants (chốt cứng):**

| Invariant | Kỳ vọng |
|---|---|
| **INV-SLA-5** (parity 3 surface) mở rộng sang detail | `get_incident_detail(name).is_*_breached` == `list_incidents()` row cùng `name` == cùng predicate `get_dashboard().active_incidents` — TẠI CÙNG `now` (cùng `_enrich_sla_breach`). Test `test_detail_list_sla_parity` (`test_imm12.py:968`). |
| **INV-SLA-6** (terminal) | Terminal `Cancelled`/`Closed`/`Resolved`: **chỉ** breach qua nhánh cờ=1 (đã từng breach) → `is_*_breached=1`; nếu cờ=0 (đóng đúng hạn) → `is_*_breached=0` dù `due_at` đã quá khứ (KHÔNG live-overdue). |

**Boundaries (Always / Never):**
- **Always:** THÊM đúng 2 field `is_response_breached`/`is_resolution_breached` (int 0|1); derive qua `_enrich_sla_breach` (1 SoT, KHÔNG query thêm per-row); giữ cờ thô cho backward-compat; auth AUTH-10 + envelope Decision-B `_ok` NGUYÊN VẸN.
- **Never:** rò field web-only mới nào khác ngoài 2 derived flags khi thêm parity; re-implement predicate breach ở màn Chi tiết (phải dùng `_row_is_breached`); so ngày **client-clock** ở FE (KHÔNG `Date.now()`/`new Date()` compare `due_at` — server-flag là SoT, memory `overdue_server_flag_ssot`).

**Mobile contract (CR-21):** `IncidentDetail += is_response_breached: integer(0|1)`, `is_resolution_breached: integer(0|1)` (KHÔNG vào `required`; mirror pattern optional-emit `allowed_transitions`/`scene_photos`; `additionalProperties:true` GIỮ). Mobile `IncidentDetailView` cùng đọc 2 derived flags (không client-clock).

> ✅ **Mobile OAS mirror ĐÃ CURATE (Round 18 / SLA-detail-parity, 2026-07-13):** 2 property `is_response_breached` + `is_resolution_breached` (`type:integer` `enum:[0,1]`, `description` **VERBATIM** precedent `IncidentListItem`) đã bồi vào schema `IncidentDetail` của `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (NGAY CẠNH cờ thô `resolution_breached`; tổng property 41→43; `additionalProperties:true` GIỮ; `required` GIỮ `['name']`; path/opId 65 GIỮ + c5 54 GIỮ). **CONTRACT-ONLY** — BE `_enrich_sla_breach([data])` (`services/imm12.py:1132`) + BE test (`test_imm12.py::TestIncidentDetailSlaLive` @948-975) ĐÃ LIVE ⇒ 0 `.py`/reload/migrate. Guard `TestMobileIncidentDetailSlaFlagParity` a..f (`test_mobile_oas` +6 TC, RED-before/GREEN-after strip→"thiếu is_response_breached"): `_EXPECTED_TEST_COUNT` 610→616 · `test_mobile_docset` sync `_GUARD_SUITE_SUM` 753→759 / `_MOBILE_OAS_TOTAL` 779→785. Spec đầy đủ + Alternatives: [`docs/mobile/ADR-MOBILE-036.md`](../mobile/ADR-MOBILE-036.md) · [`docs/mobile/04-api-contract.md §3.2`](../mobile/04-api-contract.md) (note 🔵 INCIDENT-DETAIL cờ SLA-breach DERIVED). **FE Bước-4** (`IncidentDetailView.vue` +section "Tình trạng SLA" đọc `is_*_breached ?? *_breached`, reuse `SlaBreachBadge`, KHÔNG client-clock) VẪN pending.

### ADR-IMM12-08: Màn Chi tiết đọc cờ SLA-breach DERIVED (server-flag) — supersede "detail out-of-scope, đọc cờ thô"
- **Status**: Accepted (supersede ghi chú "out-of-scope vòng này" ở DELTA per-row enrich BR-12-13) · **Date**: 2026-07-09
- **Context**: cờ thô `response_breached`/`resolution_breached` chỉ do scheduler `check_incident_sla_breach()` (hourly) hoặc write-path acknowledge/resolve stamp. Màn Chi tiết đọc cờ thô ⇒ incident vừa quá hạn 1–59′ (scheduler chưa quét) hiện **"Trong hạn"** trong khi danh sách/dashboard (đã derive LIVE ở BR-12-13) hiện **"Quá hạn"** ⇒ 2 surface lệch nhau (stale-divergence) trên cùng 1 phiếu, cùng 1 thời điểm — mâu thuẫn nhìn thấy được.
- **Decision**: `get_incident_detail` gọi CÙNG `_enrich_sla_breach([data])` → surface `is_response_breached`/`is_resolution_breached`. FE màn Chi tiết đọc `is_*_breached ?? *_breached` (ưu tiên derived, fallback cờ thô cho payload cũ chưa enrich) — TÁI DÙNG `SlaBreachBadge` + SSoT label như danh sách. KHÔNG so ngày client-clock.
- **Alternatives**: (A) FE detail tự so `due_at < Date.now()` → vỡ SSoT overdue-server-flag (lệch múi giờ/đồng hồ client, memory `overdue_server_flag_ssot`) → loại. (B) giữ đọc cờ thô ở detail (bản cũ) → stale-divergence như Context → loại. (C) endpoint detail riêng cho SLA → nở surface thừa, 2 nguồn → loại.
- **Consequences**: +2 field derived/detail (chi phí ~0, in-Python, KHÔNG query thêm); badge 3 surface (list/dashboard/detail) đồng nhất tại cùng `now`; mobile CR-21 parity đóng; cờ thô vẫn còn cho consumer cũ. Đánh đổi: consumer detail nên chuyển sang đọc derived (fallback `?? cờ thô` giữ an toàn payload transition).

> **DELTA vòng này (so với bản trước):** (1) catalog +row #15 `attach_incident_photo`; (2) §2 #15 endpoint multipart + bảng-lỗi Decision-B + 2-loại-403 + permission model + Boundaries; (3) §2 #16 `get_incident_detail += scene_photos[]` (count==rows với max-check); (4) ADR-IMM12-06 (File-private store) + ADR-IMM12-07 (lifecycle enum-add). **BE Bước-4 delta** (KHÔNG thuộc file doc): `api/imm12.py` (`attach_incident_photo` handler), `services/imm12.py` (`_scene_photos` helper + `attach_incident_photo` service + `get_incident_detail` += scene_photos + const `MAX_INCIDENT_PHOTOS=5`/`MAX_INCIDENT_PHOTO_BYTES`), `asset_lifecycle_event.json` (+option `incident_photo_attached`), `tests/test_imm12.py` (7 nhánh AC). **Mobile contract delta:** path `attachIncidentPhoto` (multipart) + `IncidentDetail += scene_photos`.

> **DELTA CR-21 (round 4) — SLA-breach parity màn Chi tiết:** (1) §17 mới `get_incident_detail += is_response_breached/is_resolution_breached` (INV-SLA-5 mở rộng detail, INV-SLA-6 terminal, Boundaries no-web-only-leak + no-client-clock); (2) ADR-IMM12-08 (detail đọc derived server-flag, supersede "out-of-scope"); (3) Self-Correction §DELTA per-row enrich. **BE Bước-4 delta:** `services/imm12.py::get_incident_detail` += `_enrich_sla_breach([data])` (đã có trong working-tree, `imm12.py:950`); `api/imm12.py::get_incident` UNCHANGED. **FE Bước-4 delta:** `IncidentDetailView.vue` +section "Tình trạng SLA" (đọc `is_*_breached ?? *_breached`, reuse `SlaBreachBadge`, KHÔNG client-clock — xem `06 §2.3.b`). **Test delta:** `test_imm12.py::TestIncidentDetailSlaLive` (4 nhánh AC-S6 — bổ sung AC#1 resolution-past→1 + AC#4 terminal-cờ=1→1); FE `incidentDetailSlaBadge.test.ts`. **Mobile contract delta:** `IncidentDetail += is_response_breached/is_resolution_breached`.

### 18. get_incident_detail — `available_actions[]` server-driven 6 CTA (CR-39) 🟡 SPEC (BE/FE Bước-4)

> **Mục tiêu (CR-39):** màn **Chi tiết sự cố** (web `IncidentDetailView` + mobile) hiện tại gate 6 nút CTA vòng đời bằng **predicate-mirror ở FE** (hardcode `status===X`, `can(cap)`, và tự suy BR-12-02) → 2 lỗi: (a) FE tính khác BE ⇒ nút hiện nhưng bấm → **lỗi 403/422 sau khi bấm** (advertise≠enforce); (b) drift khi BE đổi cap/transition. Cách sửa (parity `available_actions` của IMM-00 QR-scan + `allowed_transitions`/`can_manage_rca` RCA): BE trả **1 mảng CTA có sẵn `enabled`+`reason`** — FE chỉ render, KHÔNG tự suy.

**Endpoint:** `GET assetcore.api.imm12.get_incident` (endpoint #2 → service `get_incident_detail(name)`). Auth/handler **KHÔNG đổi**: Guest → 401; đăng nhập → AUTH-10 IDOR guard (`assert_vendor_can_access("Incident Report", name)`) → `handle(_run)` Decision-B `_ok(...)`. Envelope shape **KHÔNG đổi** (field additive).

`get_incident_detail(name)` trả **THÊM** property `available_actions`: **mảng ĐÚNG 6 phần tử**, thứ tự **CỐ ĐỊNH** `[acknowledge, start_work, resolve, close, reopen, cancel]`, **LUÔN đủ 6** (kể cả khi `enabled=false`):

```jsonc
"available_actions": [
  { "key": "acknowledge", "label": "Tiếp nhận",           "route": "", "enabled": true,  "reason": "" },
  { "key": "start_work",  "label": "Bắt đầu xử lý",       "route": "", "enabled": false, "reason": "Chỉ bắt đầu xử lý được khi sự cố đã tiếp nhận" },
  { "key": "resolve",     "label": "Đánh dấu đã giải quyết","route": "", "enabled": false, "reason": "Chỉ đánh dấu đã giải quyết khi sự cố đang xử lý" },
  { "key": "close",       "label": "Đóng sự cố",           "route": "", "enabled": false, "reason": "Chỉ đóng được khi sự cố đã được giải quyết" },
  { "key": "reopen",      "label": "Mở lại điều tra",      "route": "", "enabled": false, "reason": "Chỉ mở lại điều tra khi sự cố đã được giải quyết" },
  { "key": "cancel",      "label": "Hủy sự cố",            "route": "", "enabled": true,  "reason": "" }
]
```

- **Shape phần tử = `AvailableAction`** (TÁI DÙNG schema QR-scan `{key, label, route, enabled, reason}` — KHÔNG mint schema mới). `route` **luôn `""`** (CTA nằm **trong màn** Chi tiết, KHÔNG deep-link; `route` giữ trong shape vì schema tái dùng `required` gồm `route`).
- **SSoT = `_build_incident_actions(doc)`** (`services/imm12.py`, gọi trong `get_incident_detail`). Xem `04 §3.0.4` cho spec helper + tuple `_INCIDENT_ACTION_SPECS`.

**`enabled` = `transition_allowed` ∩ `has_cap` ∩ `business_gate`** (3 tầng — parity `_build_available_actions` imm00):

| Tầng | Định nghĩa | Nguồn SSoT |
|---|---|---|
| `transition_allowed` | `cta.target_status ∈ _VALID_TRANSITIONS[doc.status]` **∧** `doc.status ∈ cta.source_states` | `_VALID_TRANSITIONS` (`imm12.py:242`) + `source_states` per-CTA (**xem ADR-IMM12-09** — khử va chạm `start_work`↔`reopen` cùng đích `In Progress`) |
| `has_cap` | `rbac.can(cap)` — `acknowledge/start_work/resolve/cancel → incident.acknowledge` (`_CAP_INVESTIGATE`); `close/reopen → incident.close` (`_CAP_CLOSE`) | **DÙNG ĐÚNG cap-string endpoint ghi** (`api/imm12.py:52-53`). TUYỆT ĐỐI KHÔNG re-literal cap khác (drift = gate nói dối). Khuyến nghị hoist 2 hằng cap về `services/imm12.py` để advertise & enforce đọc **1 SSoT** |
| `business_gate` | CHỈ `close` = BR-12-02 `_close_rca_satisfied(doc)`; 5 CTA còn lại = `True` | `_close_rca_satisfied(doc)` = `not _needs_rca(severity)` OR (`rca_record` set ∧ `rca.status=='Completed'`). **CÙNG predicate** `close_incident()` enforce ⇒ advertise==enforce (§04 §3.0.4) |

**BR-12-02 cho `close.enabled`:** `_needs_rca(doc.severity)` ∧ (`rca_record` rỗng ∨ `rca.status != 'Completed'`) ⇒ `close.enabled=false`, `reason` = "Cần hoàn tất phân tích nguyên nhân gốc (RCA) trước khi đóng sự cố". Khi `rca.status=='Completed'` (và transition+cap đủ) ⇒ `close.enabled=true`, `reason=""`.

**BẤT BIẾN ĐO ĐƯỢC (D9 — parity imm00 `_build_available_actions`):**

| Invariant | Kỳ vọng |
|---|---|
| **INV-CTA-1** (reason ⟺ enabled) | `enabled is False` ⟹ `reason != ""` (câu tiếng Việt) với **MỌI** `status` (kể cả `''` và mã LẠ ngoài enum); `enabled is True` ⟹ `reason == ""`. |
| **INV-CTA-2** (ưu tiên reason) | 3 bậc: **lifecycle/transition > capability > business-gate/unknown**. transition-blocked → reason precondition-CTA; else thiếu cap → reason capability; else (chỉ close) business-gate → reason RCA; fallback unknown (`""` status/mã lạ + đủ cap+transition) → reason chung an toàn (KHÔNG để rỗng). |
| **INV-CTA-3** (đúng 6, thứ tự cố định) | `len(available_actions)==6`, `key` theo thứ tự `[acknowledge, start_work, resolve, close, reopen, cancel]` bất kể `status`. |
| **INV-CTA-4** (advertise==enforce) | `close.enabled==True` ⟺ `close_incident(name)` KHÔNG raise BR-12-02; `<cta>.enabled==True` ⟹ endpoint tương ứng KHÔNG trả 403/`BAD_STATE`. |
| **INV-CTA-5** (READ-ONLY) | Gọi `get_incident_detail` **KHÔNG** tạo IMM Audit Trail / Asset Lifecycle Event / modify doc (`count-before == count-after` cho cả 2 doctype). |

**Boundaries (Always / Never):**
- **Always:** trả đủ 6 CTA thứ tự cố định; `enabled` = 3 tầng qua **SSoT** (`_VALID_TRANSITIONS` + cap-hằng endpoint + `_close_rca_satisfied`); `reason` VI non-empty khi disabled (INV-CTA-1); `route=""`; READ-ONLY tuyệt đối.
- **Never:** hardcode cap-string khác endpoint ghi; re-implement BR-12-02 predicate (phải dùng `_close_rca_satisfied` chung với `close_incident`); suy `enabled` từ role-name (dùng `rbac.can`); ghi audit/lifecycle/modify doc trong nhánh read; đổi shape envelope Decision-B; đổi 5 CTA còn lại theo business_gate (chỉ `close`).

**Mobile contract (CR-39):** `IncidentDetail += available_actions: array<AvailableAction>` (**KHÔNG** vào `required`; additive trên schema MỞ `additionalProperties:true` GIỮ; mirror pattern optional-emit `allowed_transitions`/`scene_photos`/`is_*_breached`; mobile **KHÔNG** bắt buộc `api:gen`, client cũ không ảnh hưởng).

> ✅ **Mobile OAS mirror ĐÃ CURATE (CR-39, 2026-07-23 — CONTRACT-ONLY, BA slice):** property `available_actions` (`type:array`, `items.$ref '#/components/schemas/AvailableAction'`) bồi vào schema `IncidentDetail` (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`, cạnh `allowed_transitions`; property 43→44; `additionalProperties:true` GIỮ; `required` GIỮ `['name']`). Guard `TestMobileIncidentDetailAvailableActionsParity` incact_a..f (`test_mobile_oas` +6 TC — field/array/$ref/optional/open-schema/reuse-AvailableAction; RED-before/GREEN-after): `_EXPECTED_TEST_COUNT` 882→888 + 2 counter-guard hardcode 882→888 · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 882→888 / `_GUARD_SUITE_SUM` 1025→1031 / `_MOBILE_OAS_TOTAL` 1051→1057 / transition-baseline `available_actions_incdetail_delta=6`. **VERIFIED:** `test_mobile_docset` 9/9 GREEN; `test_mobile_oas` — 6 TC mới + count-guard GREEN (2 error tồn dư = `TestMobileSpecParityRuntime`/`addmeas_i` do module `files` chưa map `_CROSSCUT_TAG_MAP`, **owner khác** — KHÔNG do CR-39). **BE Bước-4 (KHÔNG thuộc slice contract):** `services/imm12.py` (+`_build_incident_actions` + `_INCIDENT_ACTION_SPECS` tuple + `_close_rca_satisfied` shared predicate + `get_incident_detail` += `available_actions`; hoist 2 cap-hằng); `tests/test_imm12.py` (nhánh AC INV-CTA-1..5). **FE Bước-4:** `IncidentDetailView.vue` render cụm workflow-CTA từ `available_actions` (§06 §2.1.a), xoá predicate-mirror.

### ADR-IMM12-09: `available_actions` = 3-tầng gate với `source_states` per-CTA (khử va chạm shared-target) + reuse `AvailableAction`
- **Status**: Accepted · **Date**: 2026-07-23
- **Context**: CR-39 muốn `enabled` của mỗi CTA = `transition_allowed ∩ has_cap ∩ business_gate`, với `transition_allowed` neo vào SSoT `_VALID_TRANSITIONS` (chống dead-button). **NHƯNG** `start_work` và `reopen` **cùng đích** `In Progress`: `_VALID_TRANSITIONS[Acknowledged]=[In Progress, Cancelled]` và `_VALID_TRANSITIONS[Resolved]=[Closed, RCA Required, In Progress]` — nếu chỉ dùng `target ∈ _VALID_TRANSITIONS[status]` thì `reopen` sẽ `enabled` **sai** ở `Acknowledged` và `start_work` sẽ `enabled` **sai** ở `Resolved` (cả 2 cùng đích `In Progress` ⇒ cùng transition_allowed). Đây là **thiếu sót của công thức "target ∈ allowed"** trong đề mục gốc — cần Self-Correction.
- **Decision**: mỗi CTA trong `_INCIDENT_ACTION_SPECS` mang thêm `source_states` (tập status mà CTA có nghĩa): `acknowledge={Open}`, `start_work={Acknowledged}`, `resolve={In Progress}`, `close={Resolved}`, `reopen={Resolved}`, `cancel={Open, Acknowledged, In Progress}`. `transition_allowed = (target ∈ _VALID_TRANSITIONS[status]) ∧ (status ∈ source_states)`. Clause 1 giữ SSoT `_VALID_TRANSITIONS` (đổi/gỡ edge → CTA auto-tắt, chống dead-button); clause 2 khử va chạm `start_work`↔`reopen`. TÁI DÙNG schema `AvailableAction` (route=`""`), KHÔNG mint schema riêng cho incident.
- **Alternatives**: (A) chỉ `target ∈ _VALID_TRANSITIONS[status]` → `start_work`/`reopen` bật sai chéo state (BUG) → loại. (B) reverse-map `target→source_states` tự động từ `_VALID_TRANSITIONS` → **bất khả** vì shared-target `In Progress` ambiguous → loại. (C) bỏ 1 trong 2 CTA khỏi mảng tùy state (mảng không cố định 6) → vỡ INV-CTA-3 + FE phải suy lại → loại. (D) mint schema `IncidentAction` riêng → nở surface, trùng shape → loại.
- **Consequences**: `source_states` là SSoT phụ (khai tường minh per-CTA) đi kèm `_VALID_TRANSITIONS` — chi phí: 1 tập nhỏ/CTA + test INV-CTA-4 (advertise==enforce) chốt không lệch với endpoint. Đổi lại: FE gỡ hoàn toàn predicate-mirror; hết lỗi "403-sau-khi-bấm"; drift cap/transition được BE bắt qua guard. `AvailableAction.route` mang giá trị `""` cho incident (schema tái dùng chấp nhận — `route` chỉ có nghĩa cho CTA deep-link QR-scan).

### 19. get_incident_detail — enrich 3 field rẻ (`reporter_name` / `assigned_to_name` / `asset_lifecycle_status`) (CR-40) 🟡 SPEC (BE/FE Bước-4)

> **Mục tiêu (CR-40):** màn **Chi tiết sự cố** (web `IncidentDetailView` + mobile `IncidentDetailView`) hiện có **2 lỗ**: (1) 🔴 **RÒ EMAIL THÔ** — panel "Thông tin xử lý" render `reported_by`/`assigned_to` = **user id thô** (email `bs.nguyen@hospital.vn`) thay vì **họ tên** (U7/UI-FIX-05, cùng họ lỗ rò raw-email của transfer panel — Open thread §🔥 approval-inbox); (2) 🔴 **KTV rút máy khỏi vận hành KHÔNG thấy trạng thái thiết bị** — acknowledge High/Critical đẩy asset `Out of Service` (BR-12-04) nhưng màn Chi tiết KHÔNG hiện trạng thái vòng đời LIVE của máy ⇒ KTV không biết máy đã bị khoá vận hành (U1). Cách sửa: `get_incident_detail` bồi **3 field enrich rẻ** — **REUSE** khuôn user-enrich của `list_incidents` (`_enrich_asset_names`, `imm12.py:444-461`) cho 2 tên người + fetch `AC Asset.lifecycle_status` **SONG SONG** `asset_name` (`imm12.py:1417`) cho trạng thái máy. **Additive · migrate-free · 0 DocType/field/endpoint mới.**

**Endpoint:** `GET assetcore.api.imm12.get_incident` (endpoint #2 → service `get_incident_detail(name)`). Auth/handler **KHÔNG đổi**: Guest → 401; đăng nhập → AUTH-10 IDOR guard (`assert_vendor_can_access("Incident Report", name)`, `api/imm12.py:228`) → `handle(_run)` Decision-B `_ok(...)`. Envelope shape **KHÔNG đổi** (field additive trên schema MỞ `additionalProperties:true`).

`get_incident_detail(name)` trả **THÊM đúng 3** property (KHÔNG kéo field web-only khác):

| Field | Kiểu | Nguồn (SSoT) | Có mặt khi | Fallback / rỗng |
|---|---|---|---|---|
| `reporter_name` | `string` | `User.full_name` của `doc.reported_by` — **REUSE** `_enrich_asset_names([data])` (`imm12.py:452-458`), KHÔNG re-implement predicate | `reported_by` set | full_name rỗng → **raw id** (KHÔNG rò khi full_name tồn tại); `reported_by` rỗng → key **absent** |
| `assigned_to_name` | `string` | `User.full_name` của `doc.assigned_to` — cùng helper `_enrich_asset_names` (`imm12.py:459-460`) | `assigned_to` set | full_name rỗng → **raw id**; `assigned_to` rỗng → key **absent** |
| `asset_lifecycle_status` | `string` (nullable) | `AC Asset.lifecycle_status` của `doc.asset` — **SONG SONG** `asset_name` (`imm12.py:1417`), 1 `db.get_value` chung | `doc.asset` set | phiếu KHÔNG gắn asset → `''`/`None`; endpoint **KHÔNG crash** |

**Boundaries (Always / Never):**
- **Always:** REUSE `_enrich_asset_names` cho `reporter_name`/`assigned_to_name` (1 SSoT với list — không predicate thứ 2); `asset_lifecycle_status` đọc LIVE từ `AC Asset.lifecycle_status` (server SSoT, KHÔNG denormalize); cả 3 field **optional** (∉ `required`); READ-ONLY (KHÔNG audit/lifecycle/modify doc).
- **Never:** KHÔNG rò **email/user-id thô** ra màn Chi tiết khi `full_name` tồn tại (U7 — FE đọc `reporter_name ?? reported_by`); KHÔNG thêm `@frappe.whitelist`/DocType/field/enum (oas_baseline bất biến); KHÔNG `bench migrate`; KHÔNG re-implement user-enrich (drift SSoT); KHÔNG mở rộng sang `list_incidents` (scope đóng kín CHỈ `get_incident_detail`).

**BẤT BIẾN ĐO ĐƯỢC:**

| Invariant | Kiểm chứng |
|---|---|
| **INV-ENR-1** (parity name-enrich với list) | `get_incident_detail(name).reporter_name` == `list_incidents()` row cùng `name` `.reporter_name` (cùng `_enrich_asset_names`, cùng `User.full_name`). |
| **INV-ENR-2** (no-raw-email-leak) | `reported_by` có `full_name` ⟹ `reporter_name == full_name` (KHÔNG == email thô). Idem `assigned_to`/`assigned_to_name`. |
| **INV-ENR-3** (lifecycle LIVE == asset SSoT) | `asset_lifecycle_status == frappe.db.get_value("AC Asset", doc.asset, "lifecycle_status")` tại cùng `now`. Sau acknowledge Critical (BR-12-04 đẩy `Out of Service`) ⟹ `get_incident_detail.asset_lifecycle_status == "Out of Service"`. |
| **INV-ENR-4** (no-asset defensive) | `doc.asset` rỗng ⟹ endpoint KHÔNG raise; `asset_lifecycle_status` ∈ {`''`, `None`, absent}. |
| **INV-ENR-5** (additive, consumer cũ bất biến) | 3 field ∉ `required`; response cũ (không có 3 field) vẫn valid — client cũ/mobile KHÔNG break. |

**BE Bước-4 delta** (KHÔNG thuộc file doc — `services/imm12.py::get_incident_detail`): (a) đổi block `imm12.py:1416-1417` fetch **cả 2** field 1 lần: `data["asset_name"], data["asset_lifecycle_status"] = frappe.db.get_value(_DT_ASSET, doc.asset, ["asset_name", "lifecycle_status"])`; (b) thêm `_enrich_asset_names([data])` (REUSE) để bồi `reporter_name`/`assigned_to_name` (helper cũng set lại `asset_name` cùng giá trị — vô hại). `api/imm12.py::get_incident` UNCHANGED. Chi tiết: `04 §3.0.5`. **Test (Bước-4, `tests/test_imm12.py`):** INV-ENR-1..5 (parity list + no-raw-email + lifecycle-LIVE sau acknowledge Critical + no-asset defensive + additive).

**FE Bước-4 delta** (KHÔNG thuộc file doc): `IncidentDetailView.vue` panel "Thông tin xử lý" đọc `form.reporter_name ?? form.reported_by` + `form.assigned_to_name ?? form.assigned_to` (ưu tiên tên, fallback id cho payload cũ) — hết rò email; thêm badge trạng thái máy đọc `form.asset_lifecycle_status` (nhãn VI qua SSoT enum lifecycle, KHÔNG leak mã thô). Xem `06 §2.3.c`.

**Mobile contract (CR-40):** `IncidentDetail += reporter_name: string`, `assigned_to_name: string`, `asset_lifecycle_status: string(nullable)` (**KHÔNG** vào `required`; additive trên schema MỞ `additionalProperties:true` GIỮ; mirror pattern optional-emit `allowed_transitions`/`scene_photos`/`is_*_breached`/`available_actions`; mobile **KHÔNG** bắt buộc `api:gen`, client cũ không ảnh hưởng).

> ✅ **Mobile OAS mirror ĐÃ CURATE (CR-40, 2026-07-24 — CONTRACT-ONLY, BA slice):** 3 property `reporter_name` + `assigned_to_name` (`type:string`, `description` **VERBATIM** precedent `IncidentListItem` yaml:1436-1441 — cùng `_enrich_asset_names`, 1 SoT) + `asset_lifecycle_status` (`type:string` `nullable:true`, mirror `asset_name`) đã bồi vào schema `IncidentDetail` của `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (cạnh `asset_name`/`reported_by`/`assigned_to`; tổng property 44→47; `additionalProperties:true` GIỮ; `required` GIỮ `['name']`; path/opId/whitelist 0 mới ⇒ `oas_baseline` GIỮ). Guard `TestMobileIncidentDetailEnrichParity` incenrich_a..e (`test_mobile_oas` **+5 TC** — present/type-string/description-verbatim-parity/optional/open-schema-kept; RED-before/GREEN-after): `_EXPECTED_TEST_COUNT` 888→893 (+2 counter-guard hardcode) · property_count test `44→47` · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 888→893 / `_GUARD_SUITE_SUM` 1031→1036 / `_MOBILE_OAS_TOTAL` 1057→1062 / `enrich_incdetail_delta=5` (giữ `pre_fc3_six==191`). **VERIFIED:** `bench --site miyano run-tests` → `test_mobile_oas` **Ran 893 OK** (self-count meta-guard xác nhận 893 test-method THẬT) + `test_mobile_docset` **Ran 9 OK**. **BE Bước-4 (KHÔNG thuộc slice contract, cần USER reload gunicorn `--preload`):** `services/imm12.py::get_incident_detail` (+`_enrich_asset_names([data])` + fetch `lifecycle_status` song song `asset_name`); `tests/test_imm12.py` (INV-ENR-1..5). DoD = `test_imm12` (module-isolated) + `test_mobile_oas` XANH THẬT — KHÔNG curl live.

#### ADR-IMM12-12: `get_incident_detail` REUSE `_enrich_asset_names` cho name-enrich + fetch `lifecycle_status` song song `asset_name`
- **Status**: Accepted · **Date**: 2026-07-24
- **Context**: Màn Chi tiết sự cố rò `reported_by`/`assigned_to` = email thô (U7) và không hiện trạng thái vòng đời máy sau khi acknowledge Critical khoá vận hành (U1). `list_incidents` ĐÃ giải quyết name-enrich qua `_enrich_asset_names` (`imm12.py:444-461`), nhưng `get_incident_detail` là code path RIÊNG (`imm12.py:1414-1446`) tự fetch `asset_name` (`:1417`) và KHÔNG gọi helper enrich ⇒ drift surface (list có `reporter_name`, detail không). `asset_lifecycle_status` chưa tồn tại ở cả hai.
- **Decision**: `get_incident_detail` (a) gọi CHUNG `_enrich_asset_names([data])` để bồi `reporter_name`/`assigned_to_name` (1 SSoT với list — cùng `User.full_name`, cùng fallback raw-id); (b) mở rộng `db.get_value` `asset_name` tại `:1417` để fetch **thêm** `lifecycle_status` trong **cùng 1 query** (song song, không N+1). Cả 3 field OPTIONAL emit-when-set. `asset_lifecycle_status` GIỮ trong `get_incident_detail` (KHÔNG đẩy vào `_enrich_asset_names` chung) ⇒ **KHÔNG** lan sang `list_incidents` (scope đóng kín).
- **Alternatives**: (A) re-implement user-enrich cục bộ trong `get_incident_detail` → predicate thứ 2, drift với list (list đổi map full_name → detail lệch) → loại (vi phạm "REUSE, KHÔNG re-implement"). (B) đẩy `lifecycle_status` vào `_enrich_asset_names` chung → list_incidents cũng phát `asset_lifecycle_status` (nở scope + payload list) → loại (scope CHỈ detail). (C) denormalize `lifecycle_status` lên Incident doc → migrate + drift khi asset đổi trạng thái → loại (server-flag LIVE nguyên tắc `overdue_server_flag_ssot`). (D) FE tự query `AC Asset` để lấy trạng thái → 2 request + FE-side join → loại (đã có `doc.asset` trong payload, thêm 1 field rẻ).
- **Consequences**: 1 field enrich rẻ/surface; `get_incident_detail` chi phí +1 `db.get_value` field (gộp query `asset_name`) + 1 `_enrich_asset_names` (1 query `User` cho ≤2 id). Đổi lại: hết rò email thô (U7), KTV thấy trạng thái máy LIVE (U1), parity name-enrich list↔detail. Additive/migrate-free — consumer cũ bất biến. `asset_lifecycle_status` nullable (defensive khi phiếu no-asset — INV-ENR-4).

---

### 20. get_asset_incident_history — hợp đồng TRUNG THỰC khi cắt: `+total` `+truncated` (CR-69) ✅ BE IMPLEMENTED (2026-07-25)
> 🔌 **CONSUMER (từ 2026-07-30 — AC-CR-102):** caller THẬT ở web-FE = section «Sự cố đã ghi nhận» trong tab «Bản ghi liên quan» màn Chi tiết tài sản (IMM-00) — xem [`docs/imm-00/05 §III.26`](../imm-00/05_API_Specification.md) + [`ADR-IMM00-ASSET-OP-HISTORY`](../imm-00/ADR-IMM00-ASSET-OP-HISTORY.md). **Bất đối xứng khoá là load-bearing**: rows-key **`items`** + asset-key **`asset`** (KHÁC `history`/`asset_ref` của imm08/imm09) — store IMM-12 đọc `res.items`; "đồng bộ hoá" khoá cho đẹp ⇒ FE rỗng **câm** (guard `TC-OPH-B2`). Endpoint **KHÔNG** lọc `docstatus` ⇒ `total` **BẰNG** `count` ô connections (`INV-OPH-16`); đổi điều đó (vd loại `docstatus==2` theo `AC-CR-99`) phải cập nhật cả hai đầu + `docs/imm-00/05 §III.26.4`.


> ✅ **BE Bước-4 ĐÃ LAND** (`services/imm12.py::get_asset_incident_history` — gate quyền §20.1, clamp `cap = clamp_page_size(limit, 10)`, `truncation_meta(len(rows), cap, lambda: frappe.db.count(_DT_INCIDENT, incident_filters))`; **`incident_filters` là CÙNG một object** truyền cho rows ⇒ count KHÔNG THỂ lệch predicate). Khuyến nghị SSoT clamp đã thực hiện: helper `assetcore/utils/pagination.py::clamp_page_size` và `paginate` gọi chính helper đó ⇒ literal `100` ĐÚNG 1 nơi.
>
> 🔁 **DELTA 2026-07-25 (vòng sửa lỗi CR-69):** (1) **GATE quyền** `assert_doctype_read_permission` + `@rowscoped` — xem **§20.1** (lỗ OWASP A01: persona 0-DocPerm-read vẫn đọc được sự cố + `total`); (2) **hist_07 hết vacuous** — seed 12 → **101** (12 < 100 và 12 < 500 cho kết quả y hệt ⇒ TC cũ không phân biệt được có/không clamp); (3) **hist_08 MỚI** phủ nửa cắt của INV-INCH-5 (25 sự cố, `limit=0`); (4) **parity `limit=0` sửa THẬT** ở imm08/imm09 (trước đó doc hứa parity mà code lệch 20-vs-10).
>
> Guard: `assetcore/tests/imm12/test_imm12.py::TestAssetIncidentHistoryTruncation` (**9 TC** — HIST-01/02/03 + int-parity + zero-cost spy `frappe.db.count` 0-lần/1-lần + clamp `limit=0` (2 nhánh) + `limit=500` trên fixture 101) + `assetcore/tests/integration/test_rowscope_docperm_gate.py` (3 TC gate) + `assetcore/tests/guards/test_rowscope_scope_guard.py::G4` (guard tĩnh). FE `.ts` = việc của Bước-4 [FE] (song song).

> **Mục tiêu (CR-69):** tab **"Sự cố"** của màn hồ-sơ-vận-hành thiết bị đang **cắt IM LẶNG** theo `limit` (mặc định 10). Người dùng thấy 10 sự cố và tưởng đã xem hết trong khi máy có 30 — làm hỏng đúng 2 quyết định mà tab này sinh ra để phục vụ: **chronic failure** (BR-12-12, ≥3 sự cố cùng `fault_code`/90 ngày) và hồ sơ theo dõi thiết bị (NĐ98). Quyết định gốc: [`ADR-IMM00-TRUNCATION-SSOT`](../imm-00/ADR-IMM00-TRUNCATION-SSOT.md) (EXTENDS CR-43/46/47).

**Endpoint KHÔNG đổi:** `GET assetcore.api.imm12.get_asset_incident_history` (`api/imm12.py:232` → `services/imm12.py::get_asset_incident_history` `:1521-1530`). Auth/param **GIỮ NGUYÊN**.

> ✅ **`AC-CR-119` (2026-07-30) — cap SOUND của endpoint này là `corrective.read`** → `("Incident Report","read")` (`services/shared/rbac.py`), **khớp đúng** DocType mà truy vấn đọc (`services/imm12.py::_DT_INCIDENT`, gate `assert_doctype_read_permission(_DT_INCIDENT)` `:1731`) ⇒ **KHÔNG cần cap mới** cho IMM-12. Khai chính thức 1 lần ở SSoT `services/shared/connection_meta.py::OP_HISTORY_BRANCH_GATE["incident"] = ("corrective.read", "Incident Report")`, khoá bằng guard `CAPABILITY_MAP[cap] == (doctype, "read")` (`INV-OPH-32`, `assetcore/tests/integration/test_asset_op_history_acl.py`). **Hai loại lỗi quyền phải phân biệt ở FE**: handler chặn `Guest` ⇒ **401** envelope (`api/imm12.py:234-235`, FE redirect login); thiếu DocPerm ⇒ **403 in-envelope trên HTTP-200** (FE **KHÔNG** logout, hiện **trạng thái KHOÁ** `[op-history-locked]`, 0 «Thử lại»). Envelope BE **KHÔNG đổi 1 ký tự**; xem [`docs/imm-00/05 §III.26.7`](../imm-00/05_API_Specification.md) + [`ADR-IMM00-ASSET-OP-HISTORY §11`](../imm-00/ADR-IMM00-ASSET-OP-HISTORY.md).

**Response — 2 khoá MỚI (ADDITIVE) trong `data`:**

```jsonc
{
  "success": true,
  "data": {
    "asset": "AC-ASSET-2026-00042",
    "items": [ /* ≤ limit dòng, mới→cũ — KHÔNG đổi */ ],
    "total": 30,      // COUNT thật trên {asset} @Incident Report TRƯỚC khi cắt
    "truncated": 1
  }
}
```

| Field | Kiểu wire | Nguồn (SSoT) | Ràng buộc |
|---|---|---|---|
| `total` | `integer` ≥ 0 | `frappe.db.count(_DT_INCIDENT, {"asset": asset})` — **lazy**, chỉ chạy khi chạm trần | Cùng predicate + cùng engine (`get_all` raw) với rows |
| `truncated` | `integer` ∈ `{0,1}` | `truncation_meta(len(rows), cap, count_fn)` — `cap = clamp_page_size(limit, 10)` | KHÔNG `boolean`, KHÔNG `None` (CR-01) |

**BE Bước-4 delta** (`services/imm12.py::get_asset_incident_history`) — ✅ đã land:

1. Import SSoT `from assetcore.services.shared.truncation import truncation_meta`.
2. **Chuẩn hoá trần TRƯỚC truy vấn** — `cap = clamp_page_size(limit, 10)` (helper SSoT `assetcore/utils/pagination.py`; `paginate` gọi CHÍNH helper đó ⇒ literal `100` đúng 1 nơi). Tham số thứ 2 = `10` = default của CHÍNH endpoint này (KHÔNG `20` của `paginate`). Dùng `cap` cho **CẢ** `limit_page_length` **LẪN** đối số thứ 2 của `truncation_meta`.
3. `total, truncated = truncation_meta(len(rows), cap, lambda: frappe.db.count(_DT_INCIDENT, incident_filters))` — `incident_filters` là **CÙNG một object** đã truyền cho rows ⇒ count KHÔNG THỂ lệch predicate.
4. `return {"asset": asset, "items": rows, "total": total, "truncated": truncated}`.
5. **GATE quyền (bổ sung 2026-07-25 — xem §20.1)**: `@rowscoped` + `assert_doctype_read_permission(_DT_INCIDENT)` chạy TRƯỚC mọi truy vấn.

> ⚠️ **Bẫy RIÊNG của imm12 — khác imm08/imm09 (INV-TRUNC-LIMIT / ADR §D5):** endpoint này **KHÔNG** đi qua `BaseRepository.list`/`paginate` mà gọi thẳng `frappe.get_all(limit_page_length=limit)`. Frappe hiểu **`limit_page_length=0` là KHÔNG GIỚI HẠN**. Nếu truyền `limit` thô vào `truncation_meta`: `len(rows)=N < 0` là `False` ⇒ gọi `count_fn` ⇒ `total=N > 0` ⇒ **`truncated=1` trong khi KHÔNG dòng nào bị cắt** — báo cắt oan, đúng chiều ngược lại của bẫy imm08. Vì vậy `eff_limit` phải được clamp **trước** truy vấn.
>
> 📌 **Đây là thay đổi hành vi nhỏ, CỐ Ý (ghi để không ai coi là regression):** sau CR-69, `limit=0` **không còn** trả toàn bộ sự cố mà rơi về default `10` (và `limit>100` bị chặn ở `100`). Lý do: (a) 3 tab cùng một màn phải có **cùng ngữ nghĩa `limit`** cho client mobile; (b) `limit_page_length=0` trên thiết bị nhiều sự cố là một đường list **không trần** — rủi ro tải. Không caller nào hiện truyền `0` (`frontend/src/api/imm12.ts::getAssetIncidentHistory` default `10`; OAS khai `default: 10`).
>
> ⚖️ **Parity `limit=0` — CẢI CHÍNH 2026-07-25 (trước đó là lời hứa SAI):** bản đầu §20 viết "đúng như 2 endpoint anh em vốn đã hành xử qua `paginate`". ĐO THẬT: `clamp_page_size(0, 10)` = **10** (imm12) trong khi imm08/imm09 truyền `page_size=int(limit)` → `paginate(total, 1, 0)` → `clamp_page_size(0, **20**)` = **20** ⇒ CÙNG `limit=0` mà tab PM/Sửa-chữa trả **20** dòng còn tab Sự-cố trả **10**. Đã sửa ROOT CAUSE: cả 3 endpoint nay clamp bằng **cùng một** lời gọi `clamp_page_size(limit, 10)` trước khi truyền xuống repo (`services/imm08.py::get_asset_history`, `services/imm09.py::get_asset_history`). Guard: `test_imm08::test_tc_be_08_hist_07` + `test_imm09::test_tc_be_09_hist_05` + `test_imm12::test_tc_be_12_hist_08` (cả 3 ĐỎ khi hoàn nguyên clamp — đã verify bằng mutation).
>
> ✅ Khuyến nghị "tách hằng clamp thành helper SSoT" **ĐÃ THỰC HIỆN**: `assetcore/utils/pagination.py::clamp_page_size` và `paginate` gọi chính helper đó ⇒ literal `100` (`_MAX_PAGE_SIZE`) chỉ còn **một** nơi.

### 20.1 GATE quyền (bổ sung 2026-07-25 — đóng lỗ OWASP A01, `assetcore/services/imm12.py`)

**Lỗ đã có (chứng cứ probe thật):** user `roles=[All, Guest, Desk User, Repair User]` ⇒ `frappe.has_permission('Incident Report','read') == False` và `frappe.get_list('Incident Report', {asset})` **RAISE** `PermissionError`, NHƯNG `get_asset_incident_history(asset, limit=10)` vẫn trả `{'items': 1, 'total': 1}`. Nguyên nhân: endpoint gọi THẲNG `frappe.get_all` ⇒ bỏ **CẢ HAI** trục quyền, trong khi 2 anh em cùng bộ-ba đã gate (imm08 → `ServiceError[FORBIDDEN]`; imm09 → `assert_doctype_read_permission('Asset Repair')`). `Incident Report` chỉ có **5 role** DocPerm read (Auditor / Super Admin / Commissioning Manager / Corrective User / Corrective Manager) ⇒ mọi persona khác đọc lọt. CR-69 làm nặng thêm: `frappe.db.count` cũng không qua permission ⇒ lộ **TỔNG SỐ** sự cố thật vượt ngoài `limit`.

**Hợp đồng sau fix** (ADR-IMM00-LIST-SCOPE §8.3b — ngữ nghĩa `scope="system"`):

| Trục | Trạng thái | Cơ chế |
|---|---|---|
| ROLE-scope (DocPerm `read` trên `Incident Report`) | ✔ **enforce** | `assert_doctype_read_permission(_DT_INCIDENT)` chạy TRƯỚC mọi truy vấn |
| ROW-scope (`permissions.py::incident_report_query`) | ✘ nới **có chủ đích** | D6 device-centric: lịch sử sự cố CỦA THIẾT BỊ (WHO HTM/NĐ98), read-only, KHÔNG nút hành động, KHÔNG dùng làm căn cứ cấp quyền |
| Lỗi quyền | 403 **trên HTTP-200** | `@rowscoped` → `MSG.AUTH_FORBIDDEN` (BR-00-ROWSCOPE-403). KHÔNG 500 câm, KHÔNG list rỗng giả |

- **KHÔNG** chuyển sang `IncidentRepo.list(scope="system")` dù repo tự chạy gate: repo tính `total` **EAGER** (`count_ignore_permissions`) ⇒ phá hợp đồng ZERO-COST của `truncation_meta` (INV-INCH-1: 0 query COUNT khi chưa chạm trần) và làm đỏ TC zero-cost hiện có. Gate tường minh cấp đúng tác dụng còn thiếu, giữ nguyên đường truy vấn lazy.
- **Vendor isolation:** hiện GIỮ được nhưng **chỉ nhờ** DocPerm (Vendor Engineer có 0 read trên `Incident Report`) — clause `asset IN (SELECT … responsible_technician = user)` KHÔNG chạy trên `frappe.get_all`. Guard `test_rowscope_docperm_gate::test_incident_history_vendor_isolated` ghim bất biến này ⇒ nếu [BA] cấp DocPerm read cho Vendor Engineer, test ĐỎ (fail-loud) và endpoint PHẢI chuyển sang row-scope thật.
- **[BA] cần ratify:** (a) xác nhận D6 device-centric áp cho `Incident Report` (đối xứng R5 `imm09.get_asset_history`); (b) nếu muốn KTV nội bộ (PM/Repair/Calibration User) đọc được tab "Sự cố" thì lời giải đúng là **cấp DocPerm read** (như B2 §8.10 của ADR), KHÔNG mở lại lỗ A01.

**Boundaries (Always / Never):**
- **Always:** derive qua SSoT `truncation_meta` · `count_fn` **lazy** (`frappe.db.count` chỉ chạy khi `len(rows) >= cap`) · `count_fn` dùng **ĐÚNG** filter `{asset}` (không thêm/bớt điều kiện so với rows) · `truncated` là `int` · `data.required` GIỮ `[asset, items]` · gate `assert_doctype_read_permission` chạy **TRƯỚC** truy vấn (§20.1).
- **Never:** KHÔNG lọc thêm `status != 'Cancelled'` (hoặc bất kỳ predicate nào) **chỉ ở COUNT** — rows hiện KHÔNG lọc; lệch predicate ⇒ `total` sai im lặng · KHÔNG COUNT vô điều kiện · KHÔNG thêm param/path/opId · KHÔNG đưa 2 khoá vào `required`.

**BẤT BIẾN ĐO ĐƯỢC (test `test_imm12`):**

| Invariant | Kiểm chứng |
|---|---|
| **INV-INCH-1** | 3 sự cố, `limit=10` ⇒ `len(items)==3` ∧ `total==3` ∧ `truncated==0` ∧ **0 query COUNT** phát sinh |
| **INV-INCH-2** | 12 sự cố, `limit=5` ⇒ `len==5` ∧ `total==12` ∧ `truncated==1` |
| **INV-INCH-3** (vừa khít) | ĐÚNG 5 sự cố, `limit=5` ⇒ `total==5` ∧ **`truncated==0`** |
| **INV-INCH-4** (kiểu wire) | `type(total) is int` ∧ `type(truncated) is int` (KHÔNG `isinstance` — `bool ⊂ int` ⇒ false-green) |
| **INV-INCH-5** (clamp `limit=0` — chống báo-cắt-oan) | asset có 3 sự cố, `limit=0` ⇒ `len==3` ∧ `total==3` ∧ **`truncated==0`** (`hist_06`; công thức thô sẽ cho `truncated==1` — báo oan). **Và** asset có 25 sự cố, `limit=0` ⇒ `len(items)==10` ∧ `total==25` ∧ `truncated==1` (`hist_08` — ghim CON SỐ default 10, cũng là parity với imm08/imm09) |
| **INV-INCH-6** (clamp trần trên) | asset có **101** sự cố, `limit=500` ⇒ `len(items)==100` ∧ `total==101` ∧ `truncated==1` (`hist_07`). Fixture PHẢI **> 100**: dưới trần thì "có clamp"/"không clamp" cho kết quả y hệt ⇒ TC vacuous (bản trước seed 12 — false-green, LL-TEST-26) |
| **INV-INCH-7** (additive) | `asset` + `items` GIỮ NGUYÊN key/nội dung (0 breaking) |
| **INV-INCH-8** (gate quyền §20.1) | persona KHÔNG có DocPerm read `Incident Report` (vd `PM User`, `Vendor Engineer`) ⇒ envelope `success:false` (403), **KHÔNG** `items` chứa sự cố, **KHÔNG** khoá `total` (không lộ tổng), **KHÔNG** `PermissionError` trần. Guard: `tests/test_rowscope_docperm_gate.py` (3 TC) + guard tĩnh G4 `tests/test_rowscope_scope_guard.py` (raw `frappe.get_all`/`frappe.db.count` trên DocType row-scoped ở endpoint đọc phải gate) |

**FE Bước-4 delta — `frontend/src/api/imm12.ts:386-390`:**

```ts
export function getAssetIncidentHistory(asset: string, limit = 10) {
  return frappeGet<{ asset: string; items: IncidentDetail[]; total?: number; truncated?: 0 | 1 }>(
    `${BASE}.get_asset_incident_history`, { asset, limit },
  )
}
```

Quy tắc render + lý do 2 khoá là **optional**: xem `../imm-08/05_API_Specification.md §9.2` mục *FE Bước-4 delta* — áp dụng y nguyên, dải cảnh báo "Đang xem một phần lịch sử sự cố — thiết bị có tổng {total} sự cố." **Never:** `any` · `truncated: boolean` · tự suy "còn nữa" bằng `items.length < total`.

---

## 7. Smoke test playbook

```bash
# 1. Tạo Incident Critical (actual field names)
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.report_incident' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"asset":"ACC-ASSET-2026-00012","incident_type":"Malfunction","description":"Alarm P_HIGH liên tục","severity":"Critical","clinical_impact":"Bệnh nhân phụ thuộc","fault_code":"VENT_ALARM_HIGH"}'

# 2. Acknowledge
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.acknowledge_incident' \
  -H 'Authorization: token <key>:<secret>' \
  -d '{"name":"IR-2026-0042","notes":"Đang điều tra"}'

# 3. Resolve → auto create RCA for High/Critical
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.resolve_incident' \
  -H 'Authorization: token <key>:<secret>' \
  -d '{"name":"IR-2026-0042","resolution_notes":"Đã thay sensor"}'

# 4. Submit RCA → auto CAPA (actual param names)
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.submit_rca' \
  -H 'Authorization: token <key>:<secret>' \
  -d '{"name":"IMM-RCA-2026-0012","root_cause":"Sensor degraded","corrective_action":"Thay sensor"}'

# 5. Close Incident
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.close_incident' \
  -H 'Authorization: token <key>:<secret>' \
  -d '{"name":"IR-2026-0042","verification_notes":"Đã xác nhận"}'
```

---

## 11. Notification Contract (Sprint Notification 2026-05-29) — SINGLE SOURCE OF TRUTH

Mọi tương tác IMM-12 trả về **envelope chuẩn** đã chuẩn hoá BE → FE. FE KHÔNG
hardcode câu chữ — chỉ đọc `messageCode` rồi render qua `useNotify`. Contract đã
chốt vòng 1 (pilot IMM-09) — vòng 2 áp dụng cho IMM-12.

### 11.1 Envelope shape

Success (`_ok`):
```json
{ "success": true, "data": { ... } }
```
Lỗi (`_err`, hydrate từ registry qua `api_handler.handle()`):
```json
{
  "success": false,
  "error": "Không thể đóng sự cố mức Critical khi RCA chưa hoàn thành.",
  "code": "BUSINESS_RULE",
  "message_code": "IMM12-CLOSE-RCA-INCOMPLETE",
  "severity": "critical",
  "title": "Chưa thể đóng sự cố",
  "action_hint": "Hoàn thành RCA Record liên kết trước khi đóng sự cố.",
  "context": { "severity": "Critical", "rca": "IMM-RCA-2026-0012" },
  "http_status": 422
}
```

**Bất biến (contract):** mọi error envelope IMM-12 PHẢI có `message_code`, `severity`,
`title`. Không còn `IncidentError` thô và không còn `frappe.throw(_("..."))` leak
message Frappe ra FE. Class `IncidentError` bị loại bỏ — service raise qua
`nthrow(MSG.IMM12_*)`; DocType hook (NEG-11 close gate) raise qua
`nthrow_in_hook(MSG.IMM12_*)`.

### 11.2 Danh mục MSG cần bổ sung vào `utils/messages.py`

13 mã mới + tái dùng 3 mã hệ thống (`AUTH_FORBIDDEN`, `SYS_INVALID_PARAMS`,
`SYS_INTERNAL` — đã có). Severity tuân quy tắc §11.4.

| MSG.* | code (kebab) | severity | http | title | template (VI) | action_hint |
|---|---|---|---|---|---|---|
| `IMM12_INCIDENT_NOT_FOUND` | `IMM12-INCIDENT-NOT-FOUND` | warning | 404 | Không tìm thấy sự cố | Không tìm thấy báo cáo sự cố: {name}. | Kiểm tra lại mã sự cố trong danh sách. |
| `IMM12_RCA_NOT_FOUND` | `IMM12-RCA-NOT-FOUND` | warning | 404 | Không tìm thấy RCA | Không tìm thấy bản phân tích nguyên nhân gốc: {name}. | Kiểm tra lại mã RCA trong danh sách. |
| `IMM12_ASSET_NOT_FOUND` | `IMM12-ASSET-NOT-FOUND` | warning | 404 | Không tìm thấy thiết bị | Không tìm thấy thiết bị: {asset}. | Kiểm tra lại mã thiết bị trong danh mục tài sản. |
| `IMM12_ASSET_DECOMMISSIONED` | `IMM12-ASSET-DECOMMISSIONED` | warning | 422 | Thiết bị đã thanh lý | Không thể báo sự cố cho thiết bị đã thanh lý: {asset}. | Chọn thiết bị đang trong danh mục sử dụng. | 🆕 **AC-CR-90 / BR-12-29** — land EC-12-05 |
| `IMM12_CLINICAL_IMPACT_REQUIRED` | `IMM12-CLINICAL-IMPACT-REQUIRED` | critical | 422 | Thiếu mô tả tác động lâm sàng | Sự cố mức Critical bắt buộc mô tả tác động lâm sàng. | Nhập tác động lâm sàng trước khi báo cáo sự cố nghiêm trọng. |
| `IMM12_RESOLUTION_NOTES_REQUIRED` | `IMM12-RESOLUTION-NOTES-REQUIRED` | warning | 422 | Thiếu ghi chú giải quyết | Cần nhập ghi chú giải quyết khi chuyển sự cố sang Đã xử lý. | Nhập ghi chú giải quyết rồi thử lại. |
| `IMM12_CANCEL_REASON_REQUIRED` | `IMM12-CANCEL-REASON-REQUIRED` | warning | 422 | Thiếu lý do hủy | Cần nhập lý do khi hủy sự cố. | Nhập lý do hủy rồi thử lại. |
| `IMM12_RCA_ROOT_CAUSE_REQUIRED` | `IMM12-RCA-ROOT-CAUSE-REQUIRED` | warning | 422 | Thiếu nguyên nhân gốc rễ | Cần nhập nguyên nhân gốc rễ để hoàn thành RCA. | Nhập nguyên nhân gốc rễ rồi gửi lại RCA. |
| `IMM12_RCA_CORRECTIVE_REQUIRED` | `IMM12-RCA-CORRECTIVE-REQUIRED` | warning | 422 | Thiếu hành động khắc phục | Cần nhập hành động khắc phục để hoàn thành RCA. | Nhập hành động khắc phục rồi gửi lại RCA. |
| `IMM12_RCA_ALREADY_EXISTS` | `IMM12-RCA-ALREADY-EXISTS` | warning | 409 | Sự cố đã có RCA | Sự cố này đã có bản phân tích nguyên nhân gốc: {rca}. | Mở RCA hiện có thay vì tạo mới. |
| `IMM12_RCA_ALREADY_COMPLETED` | `IMM12-RCA-ALREADY-COMPLETED` | warning | 409 | RCA đã hoàn thành | Bản phân tích nguyên nhân gốc này đã hoàn thành. | Không cần gửi lại — RCA đã chốt. |
| `IMM12_BAD_STATE` | `IMM12-BAD-STATE` | warning | 409 | Sai trạng thái sự cố | Không thể chuyển sự cố từ '{from_state}' sang '{to_state}'. | Chỉ thực hiện hành động hợp lệ với trạng thái hiện tại. |
| `IMM12_CLOSE_RCA_REQUIRED` | `IMM12-CLOSE-RCA-REQUIRED` | critical | 422 | Chưa thể đóng sự cố | Sự cố mức {severity} bắt buộc có RCA hoàn tất trước khi đóng. | Tạo và hoàn thành RCA Record trước khi đóng sự cố. |
| `IMM12_CLOSE_RCA_INCOMPLETE` | `IMM12-CLOSE-RCA-INCOMPLETE` | critical | 422 | Chưa thể đóng sự cố | Không thể đóng sự cố mức {severity} khi RCA ({rca}) chưa hoàn thành. | Hoàn thành RCA Record liên kết trước khi đóng sự cố. |
| _(success)_ `IMM12_REPORT_SUCCESS` | `IMM12-REPORT-SUCCESS` | success | 200 | Đã ghi nhận sự cố | Đã ghi nhận báo cáo sự cố {name}. | — |

> Lưu ý content: tuân `messages.py` §quy chuẩn — Chủ thể + Hậu quả + Hành động,
> không từ kỹ thuật, không đổ lỗi user. Sau khi thêm vào `messages.py`, chạy
> `python scripts/gen_fe_messages.py` để regen `frontend/src/locales/messages.ts`.

### 11.3 BE migration checklist (cho assetcore-be)

- `services/imm12.py`: **xóa class `IncidentError`**; 15 `raise IncidentError(...)` →
  `nthrow(MSG.IMM12_*, **ctx)`. Map theo bảng §11.2.
- `services/imm12.py` hook `validate_incident_close_gate` (NEG-11, ~line 888/895):
  2 `frappe.throw(_(...))` → `nthrow_in_hook(MSG.IMM12_CLOSE_RCA_REQUIRED)` /
  `nthrow_in_hook(MSG.IMM12_CLOSE_RCA_INCOMPLETE)`. Đây là DocType `validate` hook
  → BẮT BUỘC dùng `nthrow_in_hook` (không phải `nthrow`).
- `api/imm12.py`: bỏ `IncidentError` import + try/except cục bộ + `_ok`/`_err` thủ công
  → dùng `from assetcore.utils.api_handler import handle, parse_json`. Giữ guard
  Guest→401 và role-check→403 (raise `nthrow(MSG.AUTH_FORBIDDEN)` hoặc giữ `_err` 403
  trước khi gọi `handle`).
- Audit trail (`_log` / `log_lifecycle_event`) KHÔNG đổi — message framework chỉ
  chuẩn hoá phản hồi user. Auto-RCA / auto-CAPA side-effects KHÔNG đổi.

### 11.4 FE migration checklist (cho assetcore-fe)

- Store `stores/imm12.ts`: expose `lastApiError`; mọi action catch → set
  `lastApiError` từ error envelope (giống `stores/imm09.ts`).
- Views `incident/*` + `rca/*`: thay `toast.error(msg)` / hardcode success →
  `notify.fromError(store.lastApiError)` trong catch, `notify.show({ code:
  MSG.IMM12_REPORT_SUCCESS, ctx })` hoặc `notify.fromOk(resp)` khi thành công.
- KHÔNG còn `try/catch` tự build string từ `e.message` BE.

### 11.5 Quy tắc severity (chốt cho IMM-12)

- `warning` = lỗi nghiệp vụ user tự sửa được (validation, bad-state, not-found,
  conflict) → toast vàng, GIỮ form, không reload.
- `critical` = chặn vì tuân thủ NĐ98 (BR-12-01 clinical impact, BR-12-02 / NEG-11
  RCA gate trước khi đóng sự cố Major/Critical) → modal blocking.
- `error` = lỗi hệ thống (`SYS-*`) → toast đỏ.
- `success` = thao tác thành công → toast xanh.

### 11.6 DELTA vòng 21 — SoT open-set wiring (BR-12-11)

**BE — `services/imm12.py` (ground-truth shape mà `get_dashboard.stats` trả):**
- `get_incident_stats()`: THÊM key `"open_total": _count(open_incident_filter())`. GIỮ NGUYÊN `open` (status==Open) + `investigating` (status==In Progress) — backward-compat.
- `get_dashboard()`: `active_incidents` đổi filter từ inline `{"status": ["in", [_STATUS_OPEN, _STATUS_INVESTIGATING]]}` → `open_incident_filter()`. KHÔNG còn tuple status cục bộ cho open-set trong 2 hàm này (grep guard).

**⚠️ SELF-CORRECTION — divergence api-layer (thiết kế gốc sai, đã sửa) ✅ DONE:**
> `api/imm12.py::get_incident_stats()` (whitelisted endpoint FE gọi qua `getIncidentStats()`) TRƯỚC ĐÂY là một **re-implementation cục bộ** KHÁC service-layer: dùng alias chết `"Under Investigation"` (state thực = `In Progress` ⇒ count 0 trên data thật), có inline tuple cho open-set (vi phạm SoT + grep guard), và KHÔNG trả `total/severity/sla_*/open_total`. Vi phạm CLAUDE.md §15 (no logic in controller).
>
> **Quyết định Core Doc (đã thực thi):** endpoint `api/imm12.py::get_incident_stats()` delegate service layer — `return handle(svc_stats)` (giống `get_dashboard` → `handle(svc_dashboard)`); xác minh `api/imm12.py:261-271`. `getIncidentStats()` và `get_dashboard().stats` trả CÙNG shape ⇒ một SoT duy nhất, không drift. Giữ guard Guest→401. **Hệ quả round-29:** vì api-layer đã forward verbatim service shape, mọi key MỚI thêm ở `services/imm12.py::get_incident_stats()` (gồm `critical_open`/`high_open`) tự động lộ ra qua endpoint — KHÔNG cần đụng `api/imm12.py`.

### 11.7 DELTA vòng 29 — KPI strip severity = open-set (BR-12-11b)

**BE — `services/imm12.py::get_incident_stats()`:** THÊM `"critical_open": _count(open_incident_filter({"severity": _SEV_CRITICAL}))` + `"high_open": _count(open_incident_filter({"severity": _SEV_HIGH}))`. GIỮ NGUYÊN `critical`/`high` (global, mọi-status). KHÔNG đụng `api/imm12.py` (đã delegate — xem §11.6). Grep guard: 0 occurrence inline severity-count bỏ qua open-state; `critical_open`/`high_open` CHỈ sinh qua `open_incident_filter()`.

**FE — `frontend/src/`:**
- `api/imm12.ts`: `IncidentStats` + `DashboardStats` thêm `critical_open?: number` + `high_open?: number` (optional — forward-compat khi BE chưa ship; strip fallback `?? 0`).
- `IncidentListView.vue` `kpiItems` (line ~50-64): tile 'Sự cố nghiêm trọng' bind `stats.critical_open ?? 0` (KHÔNG `stats.critical`); tile 'Sự cố mức cao' bind `stats.high_open ?? 0`. Nhãn đổi → 'Sự cố nghiêm trọng đang mở' / 'Sự cố mức cao đang mở' (làm rõ ngữ nghĩa open-set, tránh hiểu nhầm là tổng toàn cục). Tile chronic/closed KHÔNG đổi.

**Invariant FE (test BẮT BUỘC):** trên `?open=1`, strip tile = số dòng severity tương ứng trong bảng (data live → tile 1 / 2, KHÔNG còn 0/0 hay số global gồm Closed).

**Regression gate (round-29):** BE `test_imm12` GREEN + invariant `critical_open==1 ∧ high_open==2` trên data live; `critical_open <= critical`, `high_open <= high`; `open_total` (round-21) KHÔNG đổi; FE `vue-tsc` 0 + vitest GREEN; KHÔNG English/raw-code leak (GATE-1).

**FE — `frontend/src/`:**
- `api/imm12.ts`: `IncidentStats` + `DashboardStats` thêm `open_total: number`.
- `IMM12DashboardView.vue`: card #1 bind `stats.open_total`, nhãn `INCIDENT_OPEN_FILTER_LABEL` ('Đang mở'), drill `/incidents/list?open=1`; "Xem tất cả" của "Sự cố đang xử lý" → `/incidents/list?open=1`.
- KHÔNG đổi `incidentStatusLabel('Open')` ('Mới mở' — nhãn per-state, khác nhãn filter open-set).

**Regression gate:** BE `test_imm12` + `test_dashboard` GREEN; FE `vue-tsc` 0 + vitest toàn bộ; KHÔNG English/raw-code leak (GATE-1).

---

## §21 CR-74 — Read-gate CHI TIẾT báo hỏng (Incident) (`getIncident`) — in-handler 403, ĐÓNG IDOR-đọc

> **SSoT quyết định:** [ADR-IMM00-LIST-SCOPE §9 — INV-ROWSCOPE-DETAIL (CR-74)](../imm-00/ADR-IMM00-LIST-SCOPE.md) · ADR-IMM00-DETAIL-READ-01/02/03 (D8/D9/D10).
> **Trạng thái:** ✅ **RESOLVED-BE 2026-07-25 (Bước-4)** — khuôn 3 lớp LANDED @`services/imm12.py:1406-1491` (`@rowscoped` :1406 · L0 `assert_doctype_read_permission(_DT_INCIDENT)` :1435 · L1 `_get_incident` :1436 · L2 `assert_can_read_doc` :1437 — L0/L2 đặt TRONG `get_incident_detail`, **KHÔNG** trong helper `_get_incident:329` vì helper còn phục vụ đường GHI đã có gate riêng). **0 delta shape** (0 endpoint / 0 param / 0 field / 0 DocType / 0 DocPerm / 0 cap). Test: `test_rowscope_docperm_gate::TestDetailReadGateCR74` + `test_rowscope_invariant::...::test_cr74_02c_*` + guard tĩnh **G5b named** (G5a mù với op này vì doc load qua helper) — `test_imm12` **184 OK**. 🟡 Còn lại: **[FE] B13**.

### §21.1 Vấn đề (verify @source 2026-07-25)

`services/imm12.py:1405` `get_incident_detail` nạp bản ghi bằng `IncidentRepo.get(name)` → `frappe.get_doc` (`repositories/base.py:53-57`). **`frappe.get_doc` KHÔNG kiểm tra quyền** (`frappe/model/document.py:36`; kiểm tra nằm ở `Document.check_permission:227` — không đường nào chạm tới). Gate duy nhất đang có là `assert_vendor_can_access` ở API tier (`api/imm12.py:283-294`), mà hàm này **no-op cho mọi user KHÔNG mang role `Vendor Engineer`** (`services/shared/scope.py:192-193`).

⟹ Hệ quả: (a) persona **0 DocPerm read** trên `Incident Report` vẫn đọc trọn hồ sơ qua URL trực tiếp; (b) KTV **có** DocPerm read vẫn mở được sự cố do người khác báo/được giao — trong khi hook đã đăng ký sẵn ở `hooks.py:450` nhưng **không đường nào gọi tới**.

### §21.2 Hợp đồng SAU CR-74 — 3 lớp theo thứ tự BẮT BUỘC (D9)

| Lớp | Gọi gì | Khi hỏng | Vì sao thứ tự này |
|---|---|---|---|
| **L0 · ROLE** | `assert_doctype_read_permission("Incident Report")` | `frappe.PermissionError` → `@rowscoped` → **HTTP-200** + `Error{success:false, code:"FORBIDDEN", http_status:403}` | Chạy **TRƯỚC** `exists` ⇒ thiếu quyền thì `name` bịa và `name` thật trả **cùng một** 403 ⇒ 0 existence-oracle (tiền lệ `api/imm00.py:483-509`) |
| **L1 · EXISTS** | `IncidentRepo.get(name)` → không có ⇒ `nthrow(`MSG.IMM12_INCIDENT_NOT_FOUND`)` | **HTTP-200** + `Error{code:"NOT_FOUND", http_status:404}` — **GIỮ NGUYÊN** | Chỉ người **CÓ** DocPerm read mới tới được đây ⇒ 404 không còn là kênh dò |
| **L2 · ROW** | `assert_can_read_doc("Incident Report", doc)` → `frappe.has_permission("Incident Report", ptype="read", doc=doc)` | như L0 (**403 in-envelope**) | Dispatch hook `hooks.py:450` (`incident_report_has_permission` `permissions.py:202-220` — KTV chỉ đọc phiếu `reported_by` **hoặc** `assigned_to` == mình; NCC theo `responsible_technician` của asset; senior/auditor `True`) — dùng **doc đã load ở L1** ⇒ **0 query thêm** |

**Bất biến giữ nguyên (A5 — KHÔNG gỡ, KHÔNG thay):** `assert_vendor_can_access("Incident Report", name)` ở API tier **giữ nguyên vị trí + thứ tự**. Hai lớp cùng tồn tại: isolation NCC (API) ∧ read-gate (service). Vendor ngoài scope vẫn **403 in-envelope**, KHÔNG rơi nhánh 500.

### §21.3 Ma trận persona (KHÔNG đổi DocPerm — chỉ mô tả hệ quả)

| Persona | DocPerm read `Incident Report` | Phiếu `reported_by`/`assigned_to` | Kết quả sau CR-74 |
|---|---|---|---|
| `AssetCore Super Admin` / `Corrective Manager` (senior `permissions.py:34-51`) | ✔ | bất kỳ | **200 success** — payload **byte-identical** trước/sau |
| `AssetCore Auditor` | ✔ (read-only) | bất kỳ | **200 success** |
| `Corrective User` (`_TECHNICIAN_ROLES` `permissions.py:50`) | ✔ | **của mình** | **200 success** |
| `Corrective User` | ✔ | **của người khác** | **403 in-envelope** (hook `permissions.py:202-220`) — trước CR-74: **200 + đọc trọn** |
| Persona thiếu DocPerm read (vd `PM User`, `Calibration User`, `Repair User`, `Vendor Engineer`) | ✘ | bất kỳ | **403 in-envelope** (trước CR-74: đọc được trọn hồ sơ) |
| `Vendor Engineer` ngoài scope | (xem B2) | bất kỳ | **403** — lớp API tier, GIỮ NGUYÊN |

> ⚠️ **KHÔNG được "chữa" bằng cách cấp DocPerm/role.** Persona nào **cần** đọc thì mở riêng bằng ratify B2 (ADR §9.9), KHÔNG sửa trong vòng CR-74.

### §21.4 Envelope 403 — hợp đồng client (BR-00-DETAIL-403)

```json
{ "success": false, "error": "Không đủ quyền", "code": "FORBIDDEN", "http_status": 403 }
```

- **HTTP status-line = 200**; client route **theo GIÁ TRỊ** `body.success` / `body.http_status` — **KHÔNG** theo status-line.
- Client **PHẢI hiển thị message** và **KHÔNG logout** (phân biệt dispatcher-403 = hết phiên → re-auth).
- Body **KHÔNG** được chứa bất kỳ field nghiệp vụ nào (`asset` · `clinical_impact` · `severity` · `rca{}` · `scene_photos[]`) — chỉ khoá của `Error` envelope.
- Message hằng `MSG.AUTH_FORBIDDEN` (`utils/messages.py:61` = `"AUTH-403"`) — **KHÔNG** mã lỗi mới.

### §21.5 Test bắt buộc (DoD — `bench --site miyano run-tests --module ...`, KHÔNG curl)

| TC | Điều kiện | Kỳ vọng | INV |
|---|---|---|---|
| `TC-INC-DETAILGATE-01` | user đăng nhập, **0 DocPerm read** `Incident Report` | `success:false` · `code:"FORBIDDEN"` · `http_status:403` trên **HTTP-200**; 0 field nghiệp vụ | INV-DETAIL-1 |
| `TC-INC-DETAILGATE-02` | `Corrective User` có DocPerm read, sự cố `reported_by`/`assigned_to` **của người khác** | **403 in-envelope** (hook row-scope) | INV-DETAIL-2 |
| `TC-INC-DETAILGATE-03` | senior/auditor có DocPerm read | **200**, payload **byte-identical** baseline | INV-DETAIL-4 |
| `TC-INC-DETAILGATE-04` | 0 DocPerm read + `name` **KHÔNG tồn tại** | **403 y hệt** TC-01 (0 existence-oracle) | INV-DETAIL-5 |
| `TC-INC-DETAILGATE-05` | **có** DocPerm read + `name` **KHÔNG tồn tại** | **404 GIỮ NGUYÊN** (`MSG.IMM12_INCIDENT_NOT_FOUND`) | INV-DETAIL-6 |
| `TC-INC-DETAILGATE-06` | vendor ngoài scope | **403** từ API tier, KHÔNG 500 ⇒ 2 lớp cùng tồn tại | INV-DETAIL-7 |

> **BẮT BUỘC `frappe.set_user(<persona thật>)`** — `frappe/permissions.py:107-109` cho Administrator `return True` ngay ⇒ chạy bằng Administrator là **xanh giả**.

### §21.6 Boundaries

**Always** — gate ROLE trước `exists`; gate ROW trên doc đã load; lỗi quyền = HTTP-200 + Error envelope; test bằng persona thật.
**Ask-first** — cấp DocPerm read cho persona đang bị chặn (B2); vendor isolation `Incident Report` hiện dựa HOÀN TOÀN vào DocPerm (B9 §8.10).
**Never** — ❌ sửa `permissions.py` / DocPerm / role JSON để test xanh · ❌ gỡ `assert_vendor_can_access` · ❌ trả `data` rỗng hay 404 thay 403 · ❌ dùng `doc.check_permission()` (msgprint rò `_server_messages`) · ❌ thêm path/opId/param/schema OAS · ❌ đổi shape payload success · ❌ `git commit/push` · `bench migrate` · reload gunicorn (HARD-STOP USER).

## §22 AC-CR-83 — `submit_rca`: 3 ràng buộc hồ sơ RCA HẾT thoát envelope thành **HTTP-417 thô** (đóng mobile **CR-52 §3+§4**, quirk 3 "cao") 🟢 CONTRACT ĐÓNG Bước-2 · 🟢 **BE ĐÃ LAND Bước-4** · FE còn lại

> **Trạng thái:** hợp đồng (OAS mirror + guard `cr83_a..g`) **XANH**; **BE Bước-4 ĐÃ LAND 2026-07-27** — `utils/notify.py` (`nthrow(..., fields=…)`), `utils/messages.py` (+3 entry), `services/imm12.py` (3 predicate SSoT + 2 adapter + PRE-CHECK trong `submit_rca`), `assetcore/doctype/imm_rca_record/imm_rca_record.py` (**6 → 0** `frappe.throw`), `frontend/src/locales/messages.ts` (regen).
> **Bằng chứng test (verbatim):** `test_imm12` **Ran 198 OK** · `test_mobile_oas` **Ran 999 OK** · `test_mobile_docset` **Ran 9 OK** · `gen_fe_messages.py --check` **0 drift**. RED-before đo được: `frappe.exceptions.ValidationError: Bước 3: phải điền đầy đủ câu hỏi và câu trả lời.` (thoát qua `handle` từ `imm_rca_record.py:69`).
> **CÒN LẠI (FE Bước-4):** `frontend/src/views/incident/RCADetailView.vue` đọc `ApiError.fields` và render dưới đúng control — xem `06_Frontend_Design.md §7`.

### §22.0 Bằng chứng lỗi (verify `@source` 2026-07-27 — KHÔNG phải giả định)

| # | Sự thật đo được | Vị trí |
|---|---|---|
| E1 | `submit_rca` gọi `rca.save()` ⇒ chạy hook `validate` của `IMM RCA Record` | `assetcore/services/imm12.py:1093` |
| E2 | `IMMRCARecord.validate()` chạy **3** validator: `_validate_assignment` · `_validate_five_why_when_method_5why` · `_validate_completion_requirements` | `assetcore/assetcore/doctype/imm_rca_record/imm_rca_record.py:14-16` |
| E3 | Cả 3 validator dùng **`frappe.throw` TRẦN** (6 lời gọi, kể cả `on_submit`): dòng `30`, `54`, `64`, `69`, `77`, `79` | `imm_rca_record.py` |
| E4 | `handle()` **CHỈ** bắt `ServiceError`; docstring nói rõ "KHÔNG bắt Exception chung" | `assetcore/utils/api_handler.py:44,52-53` |
| E5 | ⇒ `frappe.ValidationError` bay lên dispatcher Frappe → **HTTP-417 THÔ**: không `body.success`, không `code`, không `message_code`, không `fields` | hệ quả của E3+E4 |
| E6 | `create_rca` **seed sẵn 5 bước** với `why_answer=""` ⇒ hồ sơ nào cũng ở trạng thái "đủ 5 bước, rỗng câu trả lời" | `assetcore/services/imm12.py:962-963` |
| E7 | ⇒ **ca phổ biến NHẤT** (KTV bấm «Hoàn thành» khi còn 1 ô Why trống) rơi ĐÚNG vào E5 | E6 + `imm_rca_record.py:66-71` |
| E8 | FE hiện **không** đọc `fields` ở màn RCA: `submit()` chỉ set `err.value = e.message` | `frontend/src/views/incident/RCADetailView.vue:105-126` |

**Vì sao đây là lỗi hạng "cao" chứ không phải phiền toái UX:** thông điệp 417 đi qua `makeBusinessRuleError` (`frontend/src/api/axios.ts:249-271`); không có `message_code` ⇒ rơi nhánh `parseServerMessages` ⇒ **echo chuỗi máy chủ thô** ra dải đỏ. Cùng lớp bug với backlog P1 "sanitize 417/422 không có `message_code`".

### §22.1 Scope

**Trong phạm vi:** endpoint `assetcore.api.imm12.submit_rca` · 3 ràng buộc hồ sơ RCA (5-Why · phân công · hoàn tất) · registry thông điệp · hook backstop của `IMM RCA Record` · hợp đồng mobile (`submitRca`) · hiển thị lỗi field-level trên `RCADetailView.vue`.

**Ngoài phạm vi (KHÔNG đụng vòng này):** `create_rca` / `start_rca` / `cancel_rca` / `get_rca` (0 ký tự đổi) · chuỗi auto-CAPA + `on_rca_completed` · workflow `IMM RCA Record` · DocType schema (0 field mới) · quyền/DocPerm.

### §22.2 Hợp đồng endpoint `submit_rca` (SAU AC-CR-83)

`POST /api/method/assetcore.api.imm12.submit_rca` — `@frappe.whitelist(methods=["POST"])` `api/imm12.py:195`.

**Cap = HỘI 2 tầng** (thiếu BẤT KỲ tầng nào ⇒ 403 **IN-ENVELOPE** trên HTTP-200):

| Tầng | Capability | Vị trí |
|---|---|---|
| API (in-handler) | `incident.acknowledge` (`_CAP_INVESTIGATE`) | `api/imm12.py:206-207` · hằng `services/imm12.py:265` |
| Service | `corrective.write` (`_CAP_RCA_MANAGE`) | `services/imm12.py:1068` → `_require_rca_cap` `:366-374` |

**Request** (3 bắt buộc positional + 3 optional có default — khớp chữ ký THẬT):

| Field | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `name` | str | ✅ | mã hồ sơ RCA |
| `root_cause` | str | ✅ | rỗng sau `.strip()` ⇒ `IMM12-RCA-ROOT-CAUSE-REQUIRED` |
| `corrective_action` | str | ✅ | **tên tham số GHI** (ghi vào field ĐỌC `corrective_action_summary`) |
| `preventive_action` | str | — | rỗng ⇒ GIỮ giá trị cũ |
| `five_why_steps` | JSON-array | — | rỗng/absent ⇒ dùng bước đang có trên hồ sơ |
| `rca_notes` | str | — | rỗng ⇒ GIỮ giá trị cũ |

> ⚠️ **Bất đối xứng ĐỌC ≠ GHI (CR-52 quirk 2)** — tham số ghi `corrective_action`, field đọc `corrective_action_summary` (`services/imm12.py:1083`). **Khoá `fields` dùng TÊN THAM SỐ GHI.** Lý do: `fields` tồn tại để client neo thông điệp vào **ô nhập**, mà ô nhập trên form gửi đi bằng tên tham số ghi. Dùng tên đọc = neo vào ô không tồn tại = lỗi lại "tàng hình".

**Response success (HTTP-200):** `{"success": true, "data": {"name", "status": "Completed", "linked_capa": <str|null>}}` — `services/imm12.py:1120`. `linked_capa` **nullable**: hồ sơ không gắn incident, hoặc chuỗi CAPA lỗi (đã nuốt + log `:1109-1110`) ⇒ RCA **vẫn** Completed.

**Response lỗi nghiệp vụ — TẤT CẢ trên HTTP-200 + Error envelope** (`utils/response.py::_err`):

| # | `message_code` | `http_status` | `fields` | Nguồn |
|---|---|---|---|---|
| 1 | `IMM12-RCA-FIVE-WHY-INCOMPLETE` 🆕 | 422 | `{"five_why_steps": …}` (thiếu bước) **hoặc** `{"five_why_steps.<why_number>": …}` cho **MỖI** bước khuyết | predicate SSoT §22.3 |
| 2 | `IMM12-RCA-ROOT-CAUSE-REQUIRED` | 422 | `{"root_cause": …}` | `services/imm12.py:1075-1076` (+ `fields`) |
| 3 | `IMM12-RCA-CORRECTIVE-REQUIRED` | 422 | `{"corrective_action": …}` | `services/imm12.py:1077-1078` (+ `fields`) |
| 4 | `IMM12-RCA-ASSIGNEE-REQUIRED` 🆕 | 422 | `{"assigned_to": …}` | predicate SSoT §22.3 |
| 5 | `IMM12-RCA-ALREADY-COMPLETED` | 409 | — (không phải lỗi của một ô nhập) | `services/imm12.py:1071-1072` |

Hai lỗi **không** thuộc nhóm "ràng buộc hồ sơ" và **không** kèm `fields`: `IMM12-RCA-NOT-FOUND` (404 in-envelope) · `BAD_STATE` (409 in-envelope, **không** `message_code` — `_MSG_RCA_SUBMIT_BAD_STATE`).

**Bất biến `count`-đa-lỗi:** với ca "nhiều bước Why khuyết", `fields` chứa **một khoá cho mỗi bước khuyết** (1 `message_code` duy nhất). Ca "thiếu bước" trả **đúng một** khoá `five_why_steps` (không kèm khoá con) — xem INV-RCA-4.

### §22.3 SSoT predicate — 3 hàm dùng chung service ⇄ hook (AC-4)

Đặt trong `assetcore/services/imm12.py` (khối "RCA validation — SSoT dùng chung với controller hook"). **Hook import chính 3 hàm này**; controller **KHÔNG** còn vòng lặp/điều kiện kiểm tra riêng.

```python
def validate_five_why_payload(method: str, steps: list[dict] | None) -> dict | None: ...
def validate_rca_assignment(status: str, assigned_to: str) -> dict | None: ...
def validate_rca_completion(status: str, root_cause: str, corrective_action: str,
                            linked_capa: str = "", *,
                            allow_capa_substitute: bool = True) -> dict | None: ...
```

**Kiểu trả về (giống nhau cho cả 3):** `None` = hợp lệ; vi phạm ⇒
`{"message_code": <MSG.…>, "fields": {<khoá>: <câu VI>}, "context": {<biến template>}}`.

Hai adapter mỏng (cũng trong `services/imm12.py`) để **1 vi phạm ra 2 đường**:

| Adapter | Dùng ở | Hành vi |
|---|---|---|
| `_nthrow_violation(v)` | **service** (`submit_rca`) | `nthrow(v["message_code"], fields=v["fields"], **v["context"])` ⇒ `ServiceError` ⇒ envelope Decision-B **có** `fields` |
| `_nthrow_violation_in_hook(v)` | **controller hook** | `nthrow_in_hook(v["message_code"], **v["context"])` ⇒ `ValidationError` **có** `message_code` (không có `fields` — giới hạn của kênh hook) |

**Ngữ nghĩa từng predicate** (giữ **NGUYÊN VẸN** hành vi hiện hành — không mở rộng phạm vi enforcement):

1. `validate_five_why_payload(method, steps)`
   - `"why" not in (method or "").lower()` ⇒ `None` (giữ đúng điều kiện `imm_rca_record.py:57-59`).
   - `len(steps) < 5` ⇒ `IMM12_RCA_FIVE_WHY_INCOMPLETE`, `fields = {"five_why_steps": "Phương pháp 5 Whys yêu cầu đủ 5 bước phân tích. Hiện có {count}."}`, `context = {"count": len(steps)}`. **Dừng ở đây** (không xét tiếp từng bước).
   - Ngược lại: gom **mọi** bước thiếu `why_question` hoặc `why_answer` ⇒ `fields = {f"five_why_steps.{n}": "Bước {n}: phải điền đầy đủ câu hỏi và câu trả lời."}`, với `n = step["why_number"] or <vị trí 1-based>`; `context = {"steps": "<danh sách n, phân tách dấu phẩy>"}`. Rỗng ⇒ `None`.
   - **Predicate KHÔNG nhận `status`** — cổng trạng thái nằm ở **call-site** (hook đọc `doc.status`, service luôn áp vì đích là `Completed`).
2. `validate_rca_assignment(status, assigned_to)` — `status ∈ {"RCA In Progress","Completed"} ∧ not assigned_to` ⇒ `IMM12_RCA_ASSIGNEE_REQUIRED`, `fields = {"assigned_to": …}`.
3. `validate_rca_completion(...)` — chỉ áp khi `status == "Completed"`; `not root_cause` ⇒ `IMM12_RCA_ROOT_CAUSE_REQUIRED` + `fields.root_cause`; `not corrective_action` **và** (`not allow_capa_substitute` **hoặc** `not linked_capa`) ⇒ `IMM12_RCA_CORRECTIVE_REQUIRED` + `fields.corrective_action`.

**Thứ tự kiểm tra trong `submit_rca`** (fail-fast, một vi phạm mỗi lượt — xem ADR-IMM12-15):

```
_require_rca_cap  →  _get_rca  →  guard trạng thái (đã có)
   →  ① validate_rca_assignment(_RCA_COMPLETED, rca.assigned_to)
   →  ② validate_rca_completion(_RCA_COMPLETED, root_cause, corrective_action,
                                linked_capa="", allow_capa_substitute=False)
   →  ③ validate_five_why_payload(rca.rca_method, five_why_steps or <bước đang có>)
   →  ▸ CHỈ SAU KHI cả 3 hợp lệ mới bắt đầu gán rca.status/root_cause/... (dòng 1080+)
```

**Tập bước hiệu lực (③):** `five_why_steps` nếu **truthy**, ngược lại `[row.as_dict() for row in rca.five_why_steps]` — **giống hệt** ngữ nghĩa `if five_why_steps:` mà `services/imm12.py:1088` đang dùng để quyết định có thay bảng con hay không (một quy tắc, không hai).

### §22.4 Registry thông điệp — delta (`assetcore/utils/messages.py`)

3 mã **mới** (2 cho `fields`, 1 cho hook `on_submit`); 2 mã cũ **giữ nguyên message_code + template** (chỉ được bổ sung `fields` ở tầng raise — hợp đồng cũ KHÔNG đổi, AC-3):

| Hằng | Mã | `http_status` | `severity` | `title` | `template` |
|---|---|---|---|---|---|
| `IMM12_RCA_FIVE_WHY_INCOMPLETE` | `IMM12-RCA-FIVE-WHY-INCOMPLETE` | 422 | `warning` | Hồ sơ 5 Whys chưa đầy đủ | `Phân tích 5 Whys chưa đầy đủ: {detail}.` |
| `IMM12_RCA_ASSIGNEE_REQUIRED` | `IMM12-RCA-ASSIGNEE-REQUIRED` | 422 | `warning` | Chưa phân công người phụ trách | `Phải gán người phụ trách phân tích nguyên nhân gốc trước khi tiến hành.` |
| `IMM12_RCA_SUBMIT_NOT_COMPLETED` | `IMM12-RCA-SUBMIT-NOT-COMPLETED` | 409 | `warning` | Chưa thể chốt hồ sơ | `Chỉ chốt được hồ sơ phân tích nguyên nhân gốc khi đã hoàn thành. Hiện tại: {status}.` |

> `IMM12_RCA_SUBMIT_NOT_COMPLETED` **chỉ** phục vụ hook `on_submit` (`imm_rca_record.py:29-32`) — đường Desk/`doc.submit()`, không nằm trên đường `submit_rca` API.

### §22.5 `nthrow(..., fields=...)` — mở rộng tối thiểu (`assetcore/utils/notify.py`)

Hiện `nthrow(message_code, *, error_code=None, **context)` **không** truyền được `fields`, dù `ServiceError` và `_service_error_to_envelope` đã hỗ trợ đầy đủ (`services/shared/errors.py:43,50` · `utils/api_handler.py:57`). Bổ sung **một** tham số keyword-only:

```python
def nthrow(message_code: str, *, error_code: str | None = None,
           fields: dict | None = None, **context: Any) -> None
```

⇒ chuyển thẳng vào `ServiceError(..., fields=fields)`. **Backward-compatible** (mặc định `None` = hành vi cũ). Ghi chú BE: `fields` trở thành **tên dành riêng**, không dùng được làm biến template `{fields}` — hiện **0** entry registry dùng biến đó.

### §22.6 Controller `IMM RCA Record` — hết `frappe.throw` trần (AC-5)

`assetcore/assetcore/doctype/imm_rca_record/imm_rca_record.py`: **6 → 0** lời gọi `frappe.throw(`.

| Dòng hiện tại | Sau AC-CR-83 |
|---|---|
| `:30` `on_submit` status ≠ Completed | `nthrow_in_hook(MSG.IMM12_RCA_SUBMIT_NOT_COMPLETED, status=self.status)` |
| `:54` thiếu `assigned_to` | `v = validate_rca_assignment(self.status, self.assigned_to)` → `_nthrow_violation_in_hook(v)` |
| `:64` `< 5` bước | `v = validate_five_why_payload(self.rca_method, self.get("five_why_steps"))` (chỉ chạy khi `self.status ∈ {"RCA In Progress","Completed"}`) → `_nthrow_violation_in_hook(v)` |
| `:69` bước thiếu Q/A | *(gộp vào cùng predicate trên — hết vòng lặp riêng)* |
| `:77` thiếu `root_cause` | `v = validate_rca_completion(self.status, self.root_cause, self.corrective_action_summary, self.linked_capa)` → `_nthrow_violation_in_hook(v)` |
| `:79` thiếu corrective/CAPA | *(gộp vào cùng predicate trên)* |

**Import bắt buộc là lazy-import trong thân hàm** (`from assetcore.services.imm12 import …`) — top-level import từ controller sang service gây circular `ImportError` lúc `bench start` (Pattern B, `assetcore-doc` §Cross-module). Tiền lệ đang chạy: `imm_rca_record.py:41` đã lazy-import `on_rca_completed`.

### §22.7 Bất biến (INV)

| ID | Bất biến |
|---|---|
| INV-RCA-1 | Mọi lỗi nghiệp vụ của `submit_rca` đến trên **HTTP-200** + Error envelope. **0** `frappe.ValidationError` thoát ra HTTP-417. |
| INV-RCA-2 | **Một** predicate cho mỗi ràng buộc; service và hook **import cùng symbol**. Sửa 1 chỗ ⇒ cả 2 đổi. |
| INV-RCA-3 | Khoá `fields` cho hành động khắc phục là `corrective_action` (tên **GHI**), không bao giờ là `corrective_action_summary`. |
| INV-RCA-4 | Ca thiếu bước ⇒ `fields` **đúng 1** khoá `five_why_steps`. Ca bước khuyết ⇒ `fields` có **đúng** `k` khoá `five_why_steps.<n>` với `k` = số bước khuyết. |
| INV-RCA-5 | **KHÔNG-MUTATE**: khi bị từ chối, `status` / `root_cause` / `corrective_action_summary` / `completed_by` / `completed_date` giữ **nguyên giá trị trước lệnh** (pre-check chạy trước phép gán đầu tiên). |
| INV-RCA-6 | Hợp đồng cũ bất biến: `IMM12-RCA-ROOT-CAUSE-REQUIRED` / `IMM12-RCA-CORRECTIVE-REQUIRED` **giữ nguyên** `message_code`, `http_status`, `template`; chỉ **thêm** `fields`. |
| INV-RCA-7 | `enabled/allowed_transitions` của `get_rca` **không đổi** — AC-CR-83 không chạm tầng CTA. |
| INV-RCA-8 | Happy path bất biến: 5 bước đủ Q+A ⇒ `Completed` + auto-CAPA + `on_rca_completed` chạy **y như trước**. |
| INV-RCA-9 | Controller RCA có **0** lời gọi `frappe.throw(`; mọi lỗi tối thiểu mang `message_code` + câu tiếng Việt từ registry SSoT. |

### §22.8 Divergence đã biết (ghi nhận — KHÔNG sửa vòng này)

| ID | Divergence | Quyết định |
|---|---|---|
| **D-RCA-1** | Cap `submit_rca` là **hội 2 tầng khác nhau** (`incident.acknowledge` ở API ∩ `corrective.write` ở service) — không phải một capability duy nhất | **Giữ**. Ghi vào hợp đồng để client không suy 1 tầng (advertise rộng hơn enforce). |
| **D-RCA-2** | Hook cho phép `linked_capa` **thay thế** `corrective_action_summary`; service **luôn** đòi `corrective_action` | **Giữ, có chủ đích** (`allow_capa_substitute=False` ở service). API `submit_rca` chính là nơi **nhập** tóm tắt khắc phục; lối thoát `linked_capa` chỉ dành cho hồ sơ Desk đã gắn CAPA sẵn. Đổi = phá AC-3. |
| **D-RCA-3** | `rca_method` Select có **3** giá trị `5-Why / Fishbone / Both`, nhưng predicate `"why" in method.lower()` **chỉ khớp `5-Why`** ⇒ hồ sơ chọn **`Both`** (= 5-Why *và* Fishbone) **không** bị kiểm 5-Why | **KHÔNG sửa vòng này** — mở rộng enforcement làm hồ sơ đang hợp lệ trở thành không hợp lệ (vi phạm AC-6 "không regress"). Tách **AC-CR-83b** (§22.11), cần ratify nghiệp vụ trước. |
| **D-RCA-4** | `start_rca` cố tình dùng `frappe.db.set_value` để **bỏ qua** `validate` (`services/imm12.py:996-1000`) ⇒ hồ sơ có thể vào `RCA In Progress` mà chưa có `assigned_to` | **Giữ** (đúng nghiệp vụ: bắt đầu phân tích thì chưa điền Why). Chính vì vậy `validate_rca_assignment` **phải** được gọi ở service `submit_rca`, không thể trông vào `start_rca`. |

### §22.9 ADR

#### ADR-IMM12-13: Predicate ràng buộc RCA nâng lên **service**, hook giữ vai **backstop**
- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: 3 ràng buộc chỉ sống trong controller hook ⇒ mọi đường API rơi vào `frappe.throw` trần → HTTP-417 ngoài envelope (E1–E5). Không thể vá bằng cách bắt `ValidationError` trong `handle()`: sẽ nuốt **mọi** lỗi hệ thống thành lỗi nghiệp vụ (mất phân biệt 500 thật), và vẫn không có `fields`.
- **Decision**: Tách predicate thành **hàm thuần** trong `services/imm12.py`; `submit_rca` **pre-check** trước khi gán; controller hook **import chính hàm đó** làm backstop cho đường Desk/`doc.save()` trực tiếp.
- **Alternatives**: (a) bắt `ValidationError` trong `api_handler` — loại: nuốt lỗi hệ thống, không có `fields`, không có `message_code`. (b) Bỏ hẳn validator ở controller — loại: mất backstop cho Desk, vi phạm "mọi nghiệp vụ phải có record + enforcement" (CLAUDE.md §19).
- **Consequences**: 1 predicate / 2 điểm gọi ⇒ hết "luật thứ hai". Hook **không** truyền được `fields` (giới hạn kênh `frappe.throw`) — chấp nhận: đường Desk không có form mobile để neo lỗi.

#### ADR-IMM12-14: Khoá `fields` dùng **tên tham số GHI**, không dùng tên field ĐỌC
- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: `corrective_action` (ghi) ≠ `corrective_action_summary` (đọc) — CR-52 quirk 2.
- **Decision**: `fields` luôn khoá theo **tên trong request** (`corrective_action`), và với bảng con thì theo **số hiển thị** (`five_why_steps.<why_number>`).
- **Alternatives**: khoá theo tên field DocType — loại: client không có ô nào tên đó, thông điệp rơi vào hư vô. Khoá theo chỉ số mảng 0-based — loại: lệch 1 với nhãn «Why N» người dùng nhìn thấy.
- **Consequences**: FE map thẳng khoá → `id` control (`rca-corrective`, `why-a-<n>`) không cần bảng dịch. Nếu BE đổi tên tham số ⇒ hợp đồng + FE phải đổi **cùng lúc** (guard `cr83_f` khoá bằng `inspect.signature`).

#### ADR-IMM12-15: Fail-fast **một vi phạm** mỗi lượt, nhưng **gom đủ dòng Why khuyết**
- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: Ba nhóm ràng buộc độc lập; báo cả ba cùng lúc nghe hấp dẫn nhưng buộc phải mint một `message_code` tổng hợp và phá hợp đồng cũ (INV-RCA-6).
- **Decision**: Trả **một** `message_code` (theo thứ tự phân công → hoàn tất → 5-Why); riêng trong nhóm 5-Why thì `fields` gom **mọi** dòng khuyết.
- **Alternatives**: gom cả 3 nhóm vào một envelope — loại: đổi `message_code` cũ = breaking cho client đang route theo mã.
- **Consequences**: KTV bỏ trống 3 ô Why thấy **cả 3** dòng đỏ trong một lần bấm (không phải sửa-thử-lại 3 vòng), nhưng nếu thiếu cả nguyên nhân gốc thì thấy lỗi đó trước.

### §22.10 Hợp đồng mobile (đã land Bước-2)

`docs/mobile/openapi/assetcore-mobile.openapi.yaml` — **paths 108 → 109** · **schemas 283 → 287** · **parameters GIỮ 38**.

| Thành phần | Nội dung |
|---|---|
| Path / opId | `/api/method/assetcore.api.imm12.submit_rca` → `submitRca` (POST-only) |
| Schema mới (4) | `SubmitRcaRequest` (CLOSED, required 3) · `RcaFiveWhyStepInput` (CLOSED, 3 field) · `SubmitRcaResponse` (CLOSED 3-key, `linked_capa` nullable) · `SubmitRcaEnvelope` |
| Slot response | **CHỈ** `{200, 401, 403}` — 404/409/417/422 đến trên HTTP-200 in-envelope ⇒ khai status-line = nhánh chết cho codegen |
| 200 | `oneOf [SubmitRcaEnvelope, Error]` closed-schema, disjoint required-set, **0 discriminator** |
| Mô tả bắt buộc nêu | 5 `message_code` · 5 khoá `fields` khả dĩ · bất đối xứng đọc≠ghi · bất biến **KHÔNG-MUTATE** · **417** (điều không còn xảy ra) |

**Guard** `assetcore/tests/guards/test_mobile_oas.py::TestMobileSubmitRcaContract` — `cr83_a..f`:

| TC | Khoá điều gì |
|---|---|
| `cr83_a` | path + opId + POST-only + đếm 109/287/38 |
| `cr83_b` | request CLOSED · required đúng 3 · **`corrective_action_summary` KHÔNG là property** nhưng **phải được nêu trong mô tả** · `five_why_steps` ∉ required · step CLOSED 3 field |
| `cr83_c` | 200 = `oneOf` đúng 2 nhánh · 0 discriminator · envelope closed · `linked_capa` nullable · slot đúng `{200,401,403}` |
| `cr83_d` | mô tả nêu đủ 5 `message_code` + 5 khoá `fields` + `KHÔNG-MUTATE` + `HTTP-200` + `417` (doc-layer thuần) |
| `cr83_g` 🆕 | **parity ĐẦY ĐỦ hợp đồng ⇄ registry LIVE** (Bước-4 lật từ `cr83_d`): 5/5 `message_code` ∈ `MESSAGES`; `http_status` == 422 cho 4 mã field-level, == 409 cho `IMM12-RCA-ALREADY-COMPLETED`; `template` khác rỗng |
| `cr83_e` | cite-drift: mọi cite `api|services/imm12.py:<dòng> <symbol>` nằm đúng vùng AST; bắt buộc nêu đích danh `submit_rca`, `create_rca`, `_require_rca_cap` |
| `cr83_f` | live-signature parity `inspect.signature(api.imm12.submit_rca)` == property-set hợp đồng; tập không-default == `required` |

> ✅ **Bước-4 ĐÃ THỰC HIỆN (2026-07-27):** `cr83_d` đã LẬT thành `cr83_g` (parity đầy đủ 5/5 mã ∈ registry LIVE + `http_status` + `template` khác rỗng) ⇒ `_EXPECTED_TEST_COUNT` 998 → **999** (+2 echo trong `cancelcal_j`/`receivecert_j`), `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` → **999**, `_GUARD_SUITE_SUM` 1141 → **1142**, `_MOBILE_OAS_TOTAL` 1167 → **1168**, `cr83_submit_rca_envelope_delta` 6 → **7**.
> ✅ Cite `services/imm12.py` trong OAS **đã refresh** theo dòng THẬT (predicate + pre-check làm dịch dòng) — `cr83_e` XANH; kèm 2 cite lân cận cùng module (`get_incident_detail` → `1579-1663`, `get_asset_incident_history` → `1709-1763`).

**Counters đã đồng bộ (Bước-2):** `_EXPECTED_TEST_COUNT` 992 → **998** (+2 echo trong `cancelcal_j`/`receivecert_j`) · `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 992 → **998** · `_GUARD_SUITE_SUM` 1135 → **1141** · `_MOBILE_OAS_TOTAL` 1161 → **1167** · `cr83_submit_rca_envelope_delta = 6`.

### §22.11 Handoff

**[BE] Bước-4 — ✅ HOÀN TẤT 2026-07-27** (tất cả 6 gạch đầu dòng): `services/imm12.py` (3 predicate `:974/:1028/:1043` + 2 adapter `:1074/:1080` + pre-check `submit_rca:1236-1250` + `fields` cho 2 nhánh cũ) · `utils/notify.py` (`nthrow(fields=…)`) · `utils/messages.py` (3 hằng + 3 entry) · `assetcore/doctype/imm_rca_record/imm_rca_record.py` (6 `frappe.throw` → **0**) · `assetcore/tests/imm12/test_imm12.py` (13 TC: `TestRcaSubmitEnvelope` 11 + `TestRcaValidatorSsot` 3, trừ TC-FE) · **refresh cite OAS** + lật `cr83_d` → `cr83_g`. ⚠️ **HARD-STOP còn lại:** `.py` API đã đổi ⇒ **USER phải `bench restart`** (gunicorn `--preload`) trước khi live-verify bằng curl/app.

**[FE] Bước-4** — `RCADetailView.vue` đọc `ApiError.fields` (đã có sẵn đường dẫn: `helpers.ts::hydrateApiError` → `ApiError.fields`) và render dưới đúng control; xem `06_Frontend_Design.md §7`.

**Backlog sinh ra từ vòng này:**

- **AC-CR-83b** *(ratify nghiệp vụ trước)* — `rca_method = "Both"` hiện thoát kiểm 5-Why (D-RCA-3). Cần chốt: `Both` có bắt buộc đủ 5-Why không? Nếu có ⇒ đổi predicate sang **danh sách phương pháp** (`_FIVE_WHY_METHODS = {"5-Why", "Both"}`) + migration cho hồ sơ đang mở.
- **[P2 — BE]** `_MSG_RCA_SUBMIT_BAD_STATE` (409) hiện **không** có `message_code` ⇒ FE không hydrate được `title`/`action_hint`. Cấp mã `IMM12-RCA-SUBMIT-BAD-STATE` trong vòng dọn dẹp riêng (đổi 1 hợp đồng lỗi = 1 CR).
- **[P2 — BE]** Quét cùng khuôn cho 3 controller RCA-adjacent còn `frappe.throw` trần (`imm_capa_record`, `incident_report`, `asset_repair`) — cùng class-of-bug.

### §22.12 Boundaries

**Always** — predicate là **hàm thuần** (không đọc `frappe.session`, không truy vấn DB) để service và hook dùng chung · pre-check chạy **trước** phép gán đầu tiên · `fields` khoá theo **tên tham số GHI** · lỗi nghiệp vụ = HTTP-200 + Error envelope · mọi lỗi tối thiểu có `message_code`.

**Ask-first** — mở rộng phạm vi 5-Why sang `Both` (D-RCA-3) · cấp `message_code` cho `BAD_STATE` · đổi tên tham số `corrective_action` · thêm ràng buộc thứ 4 cho hồ sơ RCA.

**Never** — ❌ bắt `Exception`/`ValidationError` chung trong `handle()` · ❌ dùng `corrective_action_summary` làm khoá `fields` · ❌ để controller giữ bản kiểm tra thứ hai · ❌ đổi `message_code`/`template` của 2 mã cũ · ❌ khai 417/422/409/404 thành slot status-line trong OAS · ❌ gán giá trị lên `rca` rồi mới kiểm tra · ❌ top-level import `services` từ controller · ❌ `git commit/push` · `bench migrate` · reload gunicorn (HARD-STOP USER).


## DoD — File 05 hoàn chỉnh

- [x] API Catalog (§0) — 14 endpoints (actual @frappe.whitelist names from imm12.py)
- [x] Response success format `{"success": true, "data": {...}}`
- [x] Response error format `{"success": false, "error": "...", "code": "..."}`
- [x] Error code catalog (7 codes) + FE mapping
- [x] Endpoint `report_incident`: corrected request schema (incident_type, description — not fault_description)
- [x] Endpoint `resolve_incident`: corrected response (status=Resolved always, rca_created field)
- [x] Endpoint `submit_rca`: corrected params (corrective_action not corrective_action_plan; five_why_steps as JSON string)
- [x] Endpoint `get_chronic_failures`: response với all fields
- [x] Endpoint `get_dashboard`: actual response structure `{stats, active_incidents, open_rcas, chronic_failures}`
- [x] Pagination convention
- [x] Smoke test playbook (5 curl commands, corrected field names)
- [x] ✅ FE types: `frontend/src/api/imm12.ts` (IncidentDetail, RCADetail, ChronicFailure, IncidentStats, DashboardData)
- [ ] Reviewed bởi BE Lead + FE Lead
