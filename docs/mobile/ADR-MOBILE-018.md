# ADR-MOBILE-018 — `markAllAsRead` (BULK read-receipt) — ĐÓNG NỐT notification-center action-set (tab "Thông báo" › nút "Đánh dấu tất cả đã đọc") sau `markNotificationAsRead` single — contract GROUNDED 1:1 endpoint LIVE `layout.mark_all_as_read`

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-018 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-29 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-009** (C3-split cross-domain — `*Response` RIÊNG khi field-set THẬT khác) · **§D-OAS-MARKNOTIFREAD** (FLOW-6 read-receipt single — precedent trực-tiếp) · ADR-MOBILE-001 (d — OpenAPI = hợp đồng máy-đọc) · Core Doc IMM-00 `05_API_Specification.md §III.21` + `ADR-IMM00-OPENAPI.md §D-OAS-MARKALLREAD` |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/layout.py:120-134`, `assetcore/tests/test_mobile_oas.py`, `assetcore/tests/test_mobile_docset.py`). Contract: [`04-api-contract.md`](./04-api-contract.md). Core Doc IMM-00: [`../imm-00/05_API_Specification.md`](../imm-00/05_API_Specification.md) §III.21 + [`../imm-00/ADR-IMM00-OPENAPI.md`](../imm-00/ADR-IMM00-OPENAPI.md) §D-OAS-MARKALLREAD.

---

## Context

Tab **"Thông báo"** (notification-center mobile) cần đóng-nốt action-set sau khi FLOW-6 read-receipt single `markNotificationAsRead` (ADR §D-OAS-MARKNOTIFREAD) đã landed: user mở/tap 1 thông-báo → flip `read=1`. Còn thiếu **nút "Đánh dấu tất cả đã đọc"** — thao-tác BULK xoá badge chưa-đọc **một-phát** thay vì tap từng cái. Đây là **mắt-xích CUỐI** của notification-center action-set.

Endpoint nguồn **ĐÃ LIVE**: `assetcore.api.layout.mark_all_as_read` (`api/layout.py:120-134`) — whitelist từ trước, web-FE bell đã dùng. Vòng này **CONTRACT-ONLY**: bồi 1 path vào mobile yaml để codegen sinh client; **KHÔNG đụng `.py`** (KHÔNG reload gunicorn, KHÔNG migrate).

**Cơ-chế hiện hữu (đã VERIFY @source):**
- `@frappe.whitelist(methods=["POST"])` @`:120` — **CLEAN POST** (KHÔNG verb-divergence, KHÔNG state-mutation qua GET/CSRF) ⇒ KHÔNG vào `_PARITY_VERB_ALLOWLIST`.
- `def mark_all_as_read()` @`:121` — **0-PARAM** ⇒ codegen sinh no-arg POST ⇒ **KHÔNG requestBody**. Live-sig parity: `inspect.signature(layout.mark_all_as_read).parameters == {}` (anti-drift).
- Guest-guard @`:124-125`: `if user == "Guest": return _err(_MSG_NOT_LOGGED_IN, 401)` ⇒ in-handler 401 ARRIVE **HTTP-200** body nhánh Error (route theo `http_status`, KHÔNG status-line).
- `frappe.db.sql("UPDATE tabNotification Log SET read=1 WHERE for_user=%s AND read=0", (user,))` @`:127-131` → `affected = ROW_COUNT()` @`:132` → `_ok({"updated_rows": affected})` @`:134`. Scope SQL `WHERE for_user=session.user` ⇒ **KHÔNG lookup-by-name** ⇒ **KHÔNG 404/409**.

## Decision

**Bồi 1 path POST `markAllAsRead` GROUNDED 1:1 `layout.mark_all_as_read:120-134`, +2 schema RIÊNG (`MarkAllReadEnvelope`/`MarkAllReadResponse`), 0 requestBody, slot `{200,401,403}`, Decision-B route-by-VALUE 0-discriminator.** Mirror cấu-trúc `markNotificationAsRead` (precedent FLOW-6) NHƯNG 3 điểm KHÁC grounded @source:

1. **OpenAPI** — path `/api/method/assetcore.api.layout.mark_all_as_read` › `post` › `operationId: markAllAsRead` (dotted-tail == opId, camelCase regex, UNIQUE). **KHÔNG requestBody** (0-param @`:121` ⇒ codegen no-arg POST). `200 = oneOf [MarkAllReadEnvelope | Error]` CLOSED-SCHEMA disjoint required-set + `success.enum` đối-lập (`[true]`/`[false]`) — route-by-VALUE `body.success` (Decision-B, 0 discriminator). Slot CHỈ `{200,401,403}`. Path-count **46→47**, opId **46→47**.

2. **`MarkAllReadResponse`** — EXACT **1-prop** `{updated_rows: integer}` GROUNDED `_ok({"updated_rows": affected})` @`:134`. `updated_rows` = **GENUINE integer count** (0..N) **KHÔNG enum[0,1]** — phân biệt rõ với `read` int-enum của `NotificationListItem`/`MarkNotificationReadResponse` (cờ Check 2-giá-trị). Mirror `AddMeasurementResponse.measurement_count` (R34 — genuine count). `additionalProperties:false`, `required [updated_rows]`. **KHÔNG field `status`** (Notification Log KHÔNG có `workflow_state` ⇒ KHÔNG reuse `*ActionResponse` — **C3-split cross-domain**, ADR-MOBILE-009).

3. **403 SINGLE-SHAPE `Forbidden`** (guest/no-token = dispatcher `PermissionError` HTTP-403 status-line). `401 = Unauthorized401` (FrappeRawError bearer-expired); in-handler guest @`:124-125` đến **HTTP-200** Error (route theo `http_status`). **KHÔNG 404/409** (scope SQL `WHERE for_user=session.user`, no lookup-by-name) — KHÁC `markNotificationAsRead` (có 404 Notification∄ + cap-403 owner-guard đến trên HTTP-200).

**Phạm vi:** path vào `_MVP_BUSINESS_PATHS` ⇒ 401∧403 symmetry SET tự +1 (test so SET, KHÔNG literal). `mark_all_as_read` có trong runtime `generate_spec` verb POST + security authed khớp YAML ⇒ KHÔNG vào `_PARITY_VERB_ALLOWLIST` (runtime parity 25a..e). **CONTRACT-ONLY**: `git diff --stat api/*.py + services/*.py + layout.py = TRỐNG` (BE endpoint đã LIVE).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | KHÔNG có nút "Đánh dấu tất cả đã đọc", chỉ single `markNotificationAsRead` | UX kém — tab Thông báo nhiều mục chưa-đọc → user phải tap từng cái; badge chưa-đọc không bao giờ về 0 một-phát. Endpoint bulk ĐÃ LIVE @source, không bồi contract = dead-end. |
| B | Reuse `MarkNotificationReadResponse` / 1 `*ActionResponse` chung | Field-set KHÁC: bulk trả `{updated_rows}` (đếm), single trả `{name, read}` (echo 1 record). Ép chung = nhồi field giả (bịa data source KHÔNG phát). C3-split = schema RIÊNG (ADR-MOBILE-009). |
| C | `updated_rows` enum `[0,1]` (mirror `read`) | SAI semantics — `updated_rows` là ĐẾM thật 0..N (ROW_COUNT() @`:132`), không phải cờ Check 2-giá-trị. enum `[0,1]` cắt cụt giá-trị wire-thật ≥2 ⇒ strict-codegen deser CRASH khi N≥2. GENUINE integer mới đúng. |
| D | Khai requestBody `{}` (empty object) | Handler 0-param @`:121` ⇒ codegen no-arg POST. requestBody rỗng = field rác + sai live-sig parity (`inspect.signature=={}`). KHÔNG requestBody mới khớp source. |
| E | Khai slot 404/409 | Scope SQL `WHERE for_user=session.user` — KHÔNG lookup-by-name ⇒ KHÔNG đường-đi 404/409. Khai = contract nói dối (claim error-mode không tồn tại). |
| ✅ F | Path POST no-body, `MarkAllReadResponse` 1-key `{updated_rows}` GENUINE integer, slot `{200,401,403}`, C3-split RIÊNG | Grounded 1:1 source; blast-radius = +1 path +2 schema (PURE-YAML); codegen sinh client `markAllAsRead()` no-arg trả `updated_rows:int`. |

## Consequences

- **(+)** Notification-center action-set ĐÓNG TRỌN: `markNotificationAsRead` (single, tap 1 mục) + `markAllAsRead` (bulk, nút "tất cả") ⇒ 0 dead-end; badge chưa-đọc giảm cả 2 đường.
- **(+)** Contract GROUNDED 1:1 source — `updated_rows` GENUINE count khớp `ROW_COUNT()` @`:132`; live-sig parity `inspect.signature=={}` chống drift.
- **(+)** **CONTRACT-ONLY** — `git diff` api/services/layout = TRỐNG ⇒ KHÔNG reload gunicorn, KHÔNG migrate; `generate_spec` get/post/total UNCHANGED (runtime introspect đã có `mark_all_as_read` từ trước — yaml mobile chỉ catch-up); `test_oas_d12/d15/d17` RE-VERIFY (KHÔNG re-baseline).
- **(+)** Decision-B intact (0 discriminator); 0 dangling `$ref`; path-count 46→47 + opId 46→47 (đếm thật, không literal); roadmap §3.1 claim "47 path" khớp `len(spec.paths)`.
- **(−)** `markAllAsRead` là META-action read-receipt (đánh-dấu đã-đọc), **KHÔNG sinh Lifecycle Event** nghiệp-vụ (read-receipt ≠ asset event — đúng như `markNotificationAsRead`). Notification Log flip `read` cờ, không thuộc asset lifecycle (CLAUDE.md §10).

**RED-before (Bước-4 chứng minh):** sau khi BA bồi path + 2 schema, `TestMobileMarkAllReadContract` (a..g+i, 8 TC) chạy GREEN; `_EXPECTED_TEST_COUNT` 439→447; `TestMobileOasCountSelfVerify` GREEN; `test_mobile_docset` `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 439→447 + `_GUARD_SUITE_SUM` 582→590 + `_MOBILE_OAS_TOTAL` 608→616 + `markall_action_delta=8` trong transition narrative (pre_fc3_six baseline=191 GIỮ) ⇒ `TestMobileGuardSuiteCountParity` GREEN. Path-count toàn-suite 46→47; `d12/d15/d17` get/post UNCHANGED.
