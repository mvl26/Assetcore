# 05 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Base URL | `/api/method/assetcore.api.imm12.<function>` |
| Auth | Frappe session HOẶC `Authorization: token <key>:<secret>` |
| Cập nhật | 2026-05-27 |
| Trạng thái | ✅ Live — `assetcore/api/imm12.py` deployed (14 endpoint) |

---

## 0. API Catalog

✅ Tất cả IMM-12 endpoint đã implement trong `assetcore/api/imm12.py`.

| # | Endpoint (actual @frappe.whitelist name) | Method | Mô tả | Role guard | US |
|---|---|---|---|---|---|
| 1 | `assetcore.api.imm12.report_incident` | POST | Tạo Incident Report. **CR-24 (Round 32):** +param optional `client_request_id` — idempotency mobile write-outbox (gửi non-empty → gọi lặp trả phiếu đã tạo, KHÔNG trùng). Xem §1a | **`corrective.create`** (V4 D1) | US-12-01 |
| 2 | `assetcore.api.imm12.get_incident` | GET | Chi tiết 1 IR (calls `get_incident_detail`) | authenticated | US-12-07 |
| 3 | `assetcore.api.imm12.list_incidents` | GET | List IR với filter (`status`/`severity`/`asset`/`open`/**`mine`**) + pagination. `mine=1` scope `reported_by==session.user` (tab "Báo hỏng của tôi" MVP-5c — §2 #3 "list_incidents — filter mine" + ADR-IMM12-05) | authenticated | US-12-07 |
| 4 | `assetcore.api.imm12.acknowledge_incident` | POST | Open → Acknowledged (hoặc → In Progress) | ROLES_INVESTIGATE | US-12-02 |
| 5 | `assetcore.api.imm12.resolve_incident` | POST | In Progress → Resolved + auto RCA cho High/Critical | ROLES_INVESTIGATE | US-12-02 |
| 6 | `assetcore.api.imm12.close_incident` | POST | Resolved → Closed (validate RCA Completed) | ROLES_CLOSE | US-12-02 |
| 6b | `assetcore.api.imm12.reopen_incident` | POST | **Mở lại điều tra:** `Resolved → In Progress` (BR-12-23, CR-WF-12). `reason` required. Audit IMM Audit Trail (Resolved→In Progress) | cap **`incident.close`** (`_can_close`, parity Close) | US-12-02 |
| 6c | `assetcore.api.imm12.request_rca` | POST | **Yêu cầu phân tích RCA:** `Resolved → RCA Required` (BR-12-24, CR-WF-12-RCA-ENTRY). `rca_reason` required. Qua `apply_workflow("Yêu cầu RCA")` + sync `status`; idempotent RCA reuse; audit IMM Audit Trail (Resolved→RCA Required) | cap **`compliance.submit`** (rbac.can + `_MSG_FORBIDDEN`, parity ack/close) | US-12-03 |
| 7 | `assetcore.api.imm12.cancel_incident` | POST | Huỷ IR (false alarm) | ROLES_INVESTIGATE | US-12-02 |
| 8 | `assetcore.api.imm12.create_rca` | POST | Tạo IMM RCA Record liên kết IR | ROLES_INVESTIGATE | US-12-03 |
| 9 | `assetcore.api.imm12.get_rca` | GET | Chi tiết 1 IMM RCA Record **+ `allowed_transitions[]` + `can_manage_rca` (0/1)** (server-driven CTA, BR-12-19) | authenticated | US-12-07 |
| 10 | `assetcore.api.imm12.submit_rca` | POST | Hoàn thành RCA → auto create IMM CAPA Record. **CHỈ từ `RCA In Progress`** (BR-12-21, chặn nhảy-cóc) | cap `corrective.write` | US-12-03 |
| 9b | `assetcore.api.imm12.start_rca` | POST | **Bắt đầu phân tích:** `RCA Required → RCA In Progress` (BR-12-20). Audit `rca_started` | cap `corrective.write` | US-12-03 |
| 10b | `assetcore.api.imm12.cancel_rca` | POST | **Hủy RCA:** `{RCA Required, RCA In Progress} → Cancelled` (BR-12-22), `reason` required. Audit `rca_cancelled` | cap `corrective.write` | US-12-03 |
| 11 | `assetcore.api.imm12.get_chronic_failures` | GET | Danh sách asset chronic (≥3/90d) | authenticated | US-12-04 |
| 12 | `assetcore.api.imm12.get_dashboard` | GET | Dashboard: stats + active + rcas + chronic | authenticated | US-12-05 |
| 13 | `assetcore.api.imm12.get_incident_stats` | GET | KPI counts per status+severity | authenticated | US-12-05 |
| 14 | `assetcore.api.imm12.get_asset_incident_history` | GET | Incident history của 1 asset (`asset` required + `limit` default 10) → `{asset, items[]}` (9-field/dòng `name,incident_type,severity,status,reported_at,fault_code,closed_date,linked_capa,rca_record` @`services/imm12.py:838-843`; KHÔNG pagination) | authenticated | US-12-07 |
| 15 | `assetcore.api.imm12.attach_incident_photo` | POST (multipart) | Đính **ảnh bằng chứng hiện trường** (NĐ98) vào 1 Incident Report → File private + 1 lifecycle event `incident_photo_attached`. Permission = **reporter HOẶC `incident.write`** trên chính phiếu đó (§2 #15 + BR-12-17). Mobile CR-17/G6 (endpoint DUY NHẤT còn thiếu trong contract). | reporter OR `incident.write` | US-12-08 |

> 📱 **Mobile-BE contract (FLOW-2 device-profile):** endpoint #14 đã bồi vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (opId `getAssetIncidentHistory`, 200 = oneOf `[AssetIncidentHistoryEnvelope, Error]` closed-schema route-by-VALUE `body.success`; envelope `data.required=[asset,items]` **KHÔNG pagination** — KHÁC `IncidentListEnvelope`; element `AssetIncidentHistoryItem` EXACT 9 prop, 0 Check field ⇒ né int-vs-bool trap). Lấp dead-end màn hồ-sơ-thiết-bị sau `getAssetScanInfo`. Spec đầy đủ: [`docs/mobile/04-api-contract.md §8.18`](../mobile/04-api-contract.md).

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
| `CONFLICT` | 409 | warning | `IMM12_RCA_ALREADY_EXISTS` | — | Incident đã có RCA Record (create_rca idempotent) |
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
4. **RCA idempotent reuse:** `if not (doc.rca_record and frappe.db.exists(_DT_RCA, doc.rca_record)): create_rca(name)` — GUARD trước khi gọi (`create_rca` raise 409 nếu đã có → KHÔNG tạo trùng). Reuse `rca_record` sẵn (vd Critical đã auto-tạo ở `resolve_incident`).
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
> `python scripts/gen_fe_messages.py` để regen `frontend/src/i18n/messages.ts`.

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
