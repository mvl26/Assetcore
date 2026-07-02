# ADR-MOBILE-006 — POST-action contract pattern (route-by-VALUE + 403 SINGLE-SHAPE) cho lifecycle-transition endpoint

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-006 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-16 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | Decision-B (closed-schema oneOf route-by-VALUE) · C6/C7 (200 oneOf [Env, Error] ở response-content-schema) · A16 (401/403 status-class split) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm12.py`, `assetcore/services/imm12.py`, `assetcore/assetcore/doctype/incident_report/incident_report.json`). Contract: [`04-api-contract.md §10`](./04-api-contract.md).

---

## Context

Vòng 12 bồi path `acknowledgeIncident` (`POST /api/method/assetcore.api.imm12.acknowledge_incident`, opId `acknowledgeIncident`) vào contract mobile — đây là **POST-action lifecycle ĐẦU TIÊN** (`Open → Acknowledged`, `svc_acknowledge` `services/imm12.py:451,469`). Mục đích: màn incident-detail (`getIncident`, C6-DETAIL) đang là **dead-end read-only** — KTV mở chi tiết sự cố nhưng KHÔNG có endpoint để hành động (tiếp nhận/phân công). `acknowledgeIncident` mở nút "Tiếp nhận" + thiết lập **mẫu chung cho mọi POST-action** kế tiếp (`start_work`/`resolve`/`close`/`cancel`/`create_rca`).

Khi đặc tả, phân biệt 3 loại endpoint nghiệp vụ đã có trong contract:

- **create** (`reportIncident`/`createPmWorkOrder`/`createRepairWorkOrder`/`createCalibration`) — tạo bản ghi mới, body 4-field bắt buộc, 200 = oneOf `[<Created>Envelope, Error]`.
- **read** (`getIncident`/...) + **list** (`listIncidents`/...) — đọc, 200 = oneOf `[<Detail|List>Envelope, Error]`.
- **action** (MỚI) — chuyển trạng-thái trên bản-ghi-đã-tồn-tại; khoá = `name`, KHÔNG tạo mới.

`acknowledge_incident(name, notes='', assigned_to='')` (`api/imm12.py:234`) khác create ở 2 điểm hợp đồng cần quyết định:

1. **Shape `data` của success envelope.** `svc_acknowledge` return `{"name": name, "status": doc.status}` (`services/imm12.py:469`) — CHỈ 2 key, KHÔNG `severity` (khác `ReportIncidentResponse` 3-key). `status` sau transition = `"Acknowledged"`.
2. **Mô hình 403.** Handler có HAI nhánh 403 giống `report_incident`: (a) dispatcher-403 (guest/no-token, `@whitelist(methods=['POST'])` trip TRƯỚC `handle()` → HTTP-403 THẬT + `FrappeRawError`); (b) in-handler cap-403 (`if not _can_investigate(): return _err(_MSG_FORBIDDEN, 403)` `imm12.py:240-241` → HTTP-200 + Error envelope, route-by-`body.http_status`).

`report_incident` model 403 = **DUAL-SHAPE** `ReportIncidentForbidden` (oneOf `[Error, FrappeRawError]`) — gom CẢ HAI nhánh vào slot 403. Câu hỏi: action-endpoint có nên copy DUAL-403 không?

## Decision

**(1) Action-envelope route-by-VALUE (C6/C7), tái dùng được.** 200 = oneOf `[IncidentActionEnvelope, Error]` ở TẦNG response-content-schema (KHÔNG nhồi vào envelope), `0 discriminator`, cả 2 branch `additionalProperties:false`, `success` enum disjoint `[true]`/`[false]`. `IncidentActionEnvelope.data` = **`IncidentActionResponse` closed `{name, status}`** — khai đúng `svc_acknowledge:469` (2-key, KHÔNG `severity`). `status` enum = Select-canonical 7-state `@incident_report.json` (post-ack = `Acknowledged`). Đặt tên **`IncidentActionEnvelope`/`IncidentActionResponse`** (KHÔNG `Acknowledge*`) để **tái dùng** cho `start_work`/`resolve`/`close` khi bồi sau — cùng `{name, status}` data-shape, chỉ khác `status` đích.

**(2) `requestBody` INLINE, KHÔNG component.** `application/json` `$ref AcknowledgeIncidentRequest` (`required: true`, no `$ref`-sibling). KHÁC create body (component `*Body` có CẢ `application/json` + `application/x-www-form-urlencoded`): action body chỉ 1 schema, INLINE đủ + gọn. `AcknowledgeIncidentRequest` closed `{name REQUIRED, notes/assigned_to optional default ''}` — khớp signature `acknowledge_incident(name, notes='', assigned_to='')` (`name` positional ⇒ required; 2 còn lại default ⇒ optional).

**(3) 403 = SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`, chỉ `FrappeRawError`). **KHÁC `reportIncident` DUAL-403.** Lý do: in-handler cap-403 (`imm12.py:241`) trả HTTP-200 + Error envelope ⇒ **ĐÃ được phủ bởi nhánh `Error` của 200-oneOf** (client route theo `body.http_status==403`). Do đó slot `403` (status-line THẬT) CHỈ cần model nhánh dispatcher-403 (guest/no-token) = single `FrappeRawError`. Cách này **sạch hơn** DUAL-403: client route 403 đơn-nhánh theo HTTP-status-line, không phải `oneOf`-match 2 shape ở slot 403. `report_incident` giữ DUAL-403 vì là path Phase-C ĐẦU TIÊN (di sản G-REQBODY trước khi pattern C6/C7 chín); action-endpoint áp pattern mới gọn hơn — KHÔNG hồi-tố `report_incident` round này (forward-reserve).

**(4) 401 = `Unauthorized401`; response slot CHỈ `{200, 401, 403}`.** KHÔNG bịa status-line key `404/409/422` — lỗi nghiệp vụ in-handler (invalid-transition BR-12 / IDOR / cap-403) arrive HTTP-200 + Error body, route theo `body.http_status`, đã gom vào nhánh `Error` của 200-oneOf.

## Consequences

- **Tích cực:** Mẫu POST-action chuẩn-hoá — 6 action `imm12` còn lại (`start_work`/`resolve_incident`/`close_incident`/`cancel_incident`/`create_rca`) + action module khác (PM/CM/Cal transition) copy y nguyên (chỉ đổi requestBody + status-đích). `IncidentActionEnvelope` dùng lại cho `imm12` action cùng `{name, status}` shape ⇒ ít schema, codegen gọn. 403 đơn-nhánh = client routing đơn giản hơn.
- **Tiêu cực / nợ:** Contract có HAI cách model 403 (DUAL ở `report_incident`, SINGLE ở action) — chấp nhận tạm: ghi rõ ở ADR + comment YAML để tránh "tưởng quên". **Forward-reserve Phase-E:** cân nhắc hồi-tố `report_incident` về SINGLE-403 (in-handler cap-403 vốn đã phủ bởi 200-oneOf) cho nhất-quán — đụng guard `test_mob_oas_12` + `TestMobileReportIncidentBody`, để Phase-E.
- **Pure-yaml:** BE handler `acknowledge_incident` + service + role-gate (`_can_investigate=rbac.can(corrective.investigate)`) ĐÃ tồn tại `@imm12.py:233` — KHÔNG sửa `.py`, KHÔNG reload gunicorn, KHÔNG migrate. Live HTTP cần USER reload (HARD-STOP, ngoài vòng này).

## Alternatives (đã loại)

1. **Copy DUAL-403 `ReportIncidentForbidden` cho action** — LOẠI: thừa. In-handler cap-403 đã phủ bởi 200-oneOf Error ⇒ slot 403 chỉ cần dispatcher-403 single. DUAL-403 buộc client `oneOf`-match 2 shape ở slot 403 không cần thiết.
2. **Đặt tên `AcknowledgeIncidentEnvelope`/`AcknowledgeIncidentResponse`** (mirror `ReportIncident*`) — LOẠI: không tái dùng được cho `start_work`/`resolve`/`close` (cùng `{name,status}` data). Tên `IncidentAction*` generic ⇒ 1 schema phủ mọi action.
3. **`requestBody` component `AcknowledgeIncidentBody` (như create)** — LOẠI round này: action body 1-schema, INLINE đủ; component + `application/x-www-form-urlencoded` là để khớp Frappe `form_dict` cho create (nhiều field) — action `name`-khoá gửi JSON đủ. Nếu sau cần form-encoded cho mobile, nâng lên component (forward-reserve).
4. **Khai status-line key `404/409/422` ở action** — LOẠI: lỗi nghiệp vụ in-handler đến trên HTTP-200 (quirk `handle()` + `_err`), KHÔNG set status-line ⇒ key đó = dead-deser. Đã phủ bởi nhánh `Error` của 200-oneOf (route-by-`body.http_status`).
