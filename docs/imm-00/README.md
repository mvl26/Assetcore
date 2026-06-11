# IMM-00 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-00 — Master / Cross-cutting** |
| Wave | Master |
| Trạng thái | **Live ✅ — docs synced vs code 2026-05-27** · Notification Framework Wave N1 spec'd 2026-05-29 · RC-03 kế thừa luật khấu hao Category→Asset spec'd 2026-06-03 (FR-00-47..52 / BR-00-18..21) · RC-04 per-asset self-heal `regenerate_depreciation_schedule` (FR-00-53..55 / BR-00-22) · RC-05 `bulk_regenerate_by_category` về SoT (FR-00-56..58 / BR-00-23) · RC-06 SoT `effective_book_value` (BR-05-13) · **RC-07 thanh lý hủy kỳ Pending khấu hao spec'd 2026-06-03 Vòng 8 (FR-00-59..62 / BR-00-24 — schema-delta `event_type+=depreciation_stopped`)** · RC-08 Out of Service PAUSE + RESCHEDULE khấu hao Vòng 9 (FR-00-63..68 / BR-00-25 — no schema-delta) · RC-CAPA-EFF cổng hiệu quả CAPA SoT đơn Vòng 12 (FR-00-59 / BR-00-26) · **RC-09 nhãn sự kiện khôi phục `restored` ĐÚNG 1 — kill double-emit Vòng 14 (FR-00-69 / BR-00-27 — `_lifecycle_event_for(to,from)`, no schema-delta)** |
| Số file hiện có | 8 (numbered 02–09) |
| Cập nhật cuối | 2026-06-11 (**ADR-IMM00-LABEL-PDF [V1-GATE Accepted]:** in nhãn QR qua PDF server-side đúng khổ tem nhiệt 60×100mm — endpoint `print_asset_labels_pdf` trả PDF bytes, QR `pyqrcode` SVG inline encode `qr_url`, options khổ 60×100mm margin0, cap `asset.print`+IDOR+batch200→413, render≠mark-printed audit-on-cancel guard; tái dùng `build_asset_label_data_batch`; KHÔNG chạm gen/rotate/scan/resolve) · 2026-06-09 (**3 ADR nền Phase A/B — Gate THIẾT KẾ Vòng 1 [Accepted]:** `ADR-IMM00-OPENAPI` (auto-gen OpenAPI 3.1 từ `@frappe.whitelist`, 485 ep/22 module, envelope SSoT `utils/response.py:37/:60`, serve `assetcore.api.openapi.spec`+`www/api-docs.html`), `ADR-IMM00-CMDK` (Command Palette ⌘K, registry SSoT từ `MODULE_NAV`+route, gate tái dùng `itemVisible`/`resolveRouteAccess` capability-only, fuzzy/diacritic-fold VI, a11y component riêng), `ADR-IMM00-RESPONSIVE` (mobile-first breakpoint Tailwind sm/md/lg/xl, KHÔNG PWA, pattern table→card + touch≥44px + modal full-screen mobile + DoD vào skill FE) — gate PHÂN TÍCH, KHÔNG đụng code Vòng 1) · 2026-06-08 (**ADR-IMM00-LIST-SCOPE — P1 factory run2:** chốt KTV nội bộ → read-all, Vendor Engineer → GIỮ isolation, INVARIANT `count==rows` permission-aware; gate phân tích, BE thực thi) · 2026-06-05 (Vòng 28 / B — A6-hardening chiều HIỆU CHUẨN: cờ `calibration_overdue` + `next_calibration_date` server-side trên màn quét QR `get_asset_scan_info` — derive `True ⟺ next_calibration_date<nowdate() (strict) ∧ status∉{Out of Service,Decommissioned}`, mirror `_is_pm_overdue`, timezone-safe SSoT ở BE, FE dòng "Hiệu chuẩn kế tiếp" + badge VI "Quá hạn hiệu chuẩn" render-only + a11y; payload +2 field DISTINCT giữ 9 field cũ, `next_calibration_date` là field AC Asset đã có, 0 cap/schema/field/endpoint/enum/patch delta, `CAP_SET_VERSION` v95.3388ee5629c1; FR-00-86 / BR-00-37) · Vòng 27 / B — A6-hardening: cờ `pm_overdue` server-side trên màn quét QR (FR-00-85 / BR-00-36) · Vòng 26 / B — Self-Correction RC-LIST-VENDORCLOBBER: vá HIGH vendor-isolation regression ở `list_assets` (compose AND filter-list form; BR-00-35 mục 6 / FR-00-84) |
| Khối kiến trúc | Cross-cutting (foundation cho A/B/C/D) |
| Owner | — (Cross-cutting — System Architect + BA Lead) |

> File index của module IMM-00. Tài liệu theo template chuẩn `docs/template/` (v4.1+).
> **Source docs (cũ) đã archive tại `docs/architecture/archive/imm-00/`** (7 files).

## Files hiện có (numbered 02–09)

| File | Nội dung | Trạng thái |
|---|---|---|
| [`02_Analysis_Design.md`](./02_Analysis_Design.md) | Phân tích & thiết kế: Module Overview, Architecture Position, Feature Inventory, FR, NFR, BR-00-01→12 | ✅ Live |
| [`03_Diagrams.md`](./03_Diagrams.md) | Sơ đồ: ERD (foundation + inventory), Class diagram, Sequence (SHA-256 chain, transition, scheduler) | ✅ Live |
| [`04_Backend_Design.md`](./04_Backend_Design.md) | Thiết kế backend: 27 DocType schemas (verified), Service layer 22 functions (verified), shared utilities; 20 roles, state machine đầy đủ incl. Draft + Under Maintenance | ✅ Live — synced vs code 2026-05-18 |
| [`05_API_Specification.md`](./05_API_Specification.md) | API spec: 107 whitelisted endpoints (verified), envelope `{success, data}`, permission matrix | ✅ Live — reviewed vs code |
| [`06_Frontend_Design.md`](./06_Frontend_Design.md) | Thiết kế frontend: Design tokens, Sitemap ([BUILT]/[SPEC] labeled); 10+ views built (asset/, master-data/, audit/), 4 Pinia stores (verified) | ✅ Partial — multiple views built |
| [`07_Testing_QA.md`](./07_Testing_QA.md) | Testing & QA: 13 unit tests (TC-S-001→013, corrected), UAT scenarios, STRIDE security, code quality | Live (BE) / Planned (tests) |
| [`08_Deployment.md`](./08_Deployment.md) | Deployment: Thứ tự deploy (IMM-00 first), env config, migration patches, QMS mapping, rollback | ✅ Live |
| [`09_Release.md`](./09_Release.md) | Release: User guide (System Admin), Release Notes v4.0.0, Traceability matrix, Bảng thống kê | ✅ Live |

## Architecture Decision Records (cross-cutting, chạm registry)

- [`./ADR-IMM00-OPENAPI.md`](./ADR-IMM00-OPENAPI.md) — **[R1-GATE Phase A · Accepted 2026-06-09] OpenAPI 3.1 auto-gen từ `@frappe.whitelist`**: D1 introspect = `importlib`+`inspect.signature`+`ast` walk `assetcore.api.*` (485 ep/22 module-file, đếm-thật); D2 ánh xạ `path=/api/method/assetcore.api.<mod>.<fn>` · `method`=GET trừ `methods=['POST']` · `required`=param-no-default · type-hint→JSON-type; D3 2 component SSoT `SuccessEnvelope{success,data}` + `ErrorEnvelope{success,error,code,http_status,fields}` đọc **DUY NHẤT** từ `utils/response.py:37 ErrorCode` + `:60 _HTTP_FOR_CODE`; D4 body-schema bridge `create_*`/`update_*` → `frappe.get_meta(DocType).fields`; D5 override registry `openapi_overrides.py` cho JSON-string param + `list_*`/`get_*` data shape; D6 enrich plan imm00→imm04→imm12; D7 serve = 1 whitelist GET `assetcore.api.openapi.spec` (session-gated, cached) + `www/api-docs.html` (Swagger UI self-host); D8 root `tags[]`+`x-assetcore-stats` đo-tại-generate (chống hardcode); D9-SYNC spec=dẫn-xuất+guard-test chống drift; D9-TAGS canonicalize operation tags (gỡ leak raw module-slug); D10 JSON-string param `format:json` (AST discovery, đếm động); D11 guest-stat SSoT (đếm `security==[]` thay global registry); D12 baseline error-surface (401/403 typed mọi op, baseline-merge curated-WIN); **D13 SERVERS-BLOCK** (root `servers[]` dẫn xuất `frappe.utils.get_url()` bare-origin, chèn info↔components, fail-safe `'/'`, KHÔNG hardcode host — SPEC-READY Vòng 8); **D-PRECOND:** đổi ≥9 union `X|None=None` (imm01:543/559, imm04:106/116/126/156, imm14:39, dashboard:890 + imm01:284-285) → default-rỗng cùng-kiểu TRƯỚC generate. Test-case TDD TC-OAS-01..12 + D8-D13 (TC-OAS-D13-01..06). KHÔNG re-architect BE/DocType, KHÔNG modify core. Gate phân tích — thực thi Vòng 2+.
- [`./ADR-IMM00-CMDK.md`](./ADR-IMM00-CMDK.md) — **[R1-GATE Phase B · Accepted 2026-06-09] Command Palette ⌘K**: D1 registry SSoT = view thứ 2 trên `MODULE_NAV` (`sidebarNav.ts:59`) + route tĩnh không-nav (`router/index.ts`), composable `useCommandRegistry()`, **KHÔNG fork nguồn thứ 3**; D2 gate = TÁI DÙNG `itemVisible` (`sidebarNav.ts:205`) cho nav-entry + `resolveRouteAccess` (`routeAccess.ts:57`) cho route-entry — **capability KHÔNG role-name**, command gated → ẨN (không bao giờ landing `/unauthorized`); D3 search = fuzzy substring+token + diacritic-fold VI (`foldVi` 'bao tri'→'Bảo trì'), KHÔNG thư viện ngoài; D4 bind ⌘K/Ctrl+K qua `useMagicKeys` (`@vueuse/core ^10.9.0` đã có) ở `AppLayout` + nút hint `AppTopBar` (mobile no-keyboard, touch≥44px); D5 a11y = component RIÊNG `CommandPalette.vue` (KHÔNG `BaseModal` thiếu focus-trap): `role=dialog aria-modal` + combobox/listbox + Arrow/Enter/Escape + focus-trap+return-focus; D6 Gần đây (localStorage max5) + Ghim (vẫn lọc cap). 12 test-case TDD (TC-CMDK-01..12). KHÔNG đổi `sidebarNav`/`routeAccess` (chỉ tái dùng export). Gate phân tích — thực thi Vòng 2+.
- [`./ADR-IMM00-RESPONSIVE.md`](./ADR-IMM00-RESPONSIVE.md) — **[R1-GATE Phase B · Accepted 2026-06-09] Mobile-first responsive web (KHÔNG PWA)**: D1 breakpoint chuẩn Tailwind **default** sm640/md768/lg1024/xl1280 (config KHÔNG custom `screens`), mobile-first, KHÔNG PWA (0 service-worker/manifest); D2 5 pattern DoD bắt buộc — P1 list table→card (`hidden sm:block`+`sm:hidden`, đã có ở 37 view), P2 form `grid-cols-1 md:grid-cols-2`, P3 MỌI `<table>` bọc `overflow-x-auto`, P4 tab/chip-bar dài `overflow-x-auto`/`flex-wrap`, P5 touch `min-h-[44px]`; D3 modal full-screen mobile → centered `sm:`+ (⌘K dialog đồng bộ); D4 backlog 4 gap có địa chỉ verified (P2 `AssetDetailView:555` tab-bar + `PersonaDashboardShell:32` KPI tablet; P3 `RCAListView:117` thiếu card + `ListCard:51`); D5 ghi DoD vào skill FE (`assetcore-fe/references/lessons-learned.md` LL-FE-34 + `component-patterns.md` ## Responsive — file `WAVE2-RECURRING-BUGS.md` cũ đã consolidate, home hiện = references/). 10 test-case TDD (TC-RWD-01..10). Light-touch (KHÔNG rewrite 37 view đúng). Gate phân tích — thực thi Vòng 2+.
- [`./ADR-IMM00-ASSETCODE.md`](./ADR-IMM00-ASSETCODE.md) — **[V1-GATE] Semantic & auto-gen Mã tài sản** (`asset_code`=PK) vs **Số serial NSX** (`manufacturer_sn`): D1 không trộn 2 khái niệm; D2 auto-gen khi trống = series counter `AC-ASSET-.YYYY.-.#####` (KHÔNG default-theo-serial); D3 `asset_code` pattern `^[A-Za-z0-9._\-/]+$` · DB-unique · immutable, `manufacturer_sn` app-unique · mutable (chốt KHÔNG nâng DB-unique); D4 nhãn VI "Mã tài sản"/"Số serial NSX" + helper text nguyên văn; D5 invariant `asset_code==name`, KHÔNG backfill, đính chính reserved-prefix thực = `_`/`SI-` (KHÔNG phải `TS-`/`CAT-`). Gate phân tích — KHÔNG đụng code Vòng 1.
- [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) — **QR cấp tài sản**: chốt `AC Asset.qr_token` (schema-delta §II.1.8 trong `04_Backend_Design.md`) + `Asset Lifecycle Event.event_type += qr_generated, label_printed` (§II.6) + patch backfill `v3_2.008` (§IV.3a). RBAC: read-only QR (`resolve_qr_token`/`get_asset_scan_info`/`get_asset`) = `asset.read`; **in nhãn (`get_asset_label_data[_batch]`/`mark_label_printed`) = `asset.print`; rotate (`regenerate_asset_qr_token`) = `asset.qr.rotate`** (D6 EXECUTED Vòng 3 — tách cap, persona vận hành in được; `CAP_SET_VERSION` v95.3388ee5629c1 → **v97.c30c69b8974d**); deep-link `/a/<token>`.
- [`./ADR-IMM00-LIST-SCOPE.md`](./ADR-IMM00-LIST-SCOPE.md) — **[GATE 2026-06-08] Row-scope AC Asset list + INVARIANT `count==rows`** (P1 factory run2: KTV `phamvanduc` thấy "Tổng 1430" nhưng bảng RỖNG): D1 **KTV NỘI BỘ** (`PM/Repair/Calibration/Corrective User` = Role Profile "Kỹ thuật viên") → `ac_asset_query` trả `""` (**read-all**, bỏ scope `responsible_technician`); D2 **Vendor Engineer** (role thủ công nhân sự NCC, KHÔNG thuộc 8 Role Profile) → **GIỮ isolation** `responsible_technician=<safe>` (bất biến CLAUDE.md §5 — đổi nội bộ KHÔNG nới vendor); D3 INVARIANT `count==len(items)` cho MỌI persona → count dùng `frappe.get_list(limit_page_length=0)` permission-aware (KHÔNG `db.count`/`get_all` — gốc lỗi count!=rows). Đồng bộ `ac_asset_has_permission` (KTV read=True). +7 invariant test (INV-3 chứng minh vendor isolated sau fix). Backlog: 4 list endpoint khác (incident/repair/pm/commissioning) cùng lỗ count-vs-permission. Lấp khoảng RC-LIST-VENDORCLOBBER (bỏ sót persona KTV nội bộ).
- [`./ADR-IMM00-QR-SCAN-ACTION.md`](./ADR-IMM00-QR-SCAN-ACTION.md) — **[R1-GATE] Affordance + capability-gate màn quét QR**: D1 action surface 4 CTA (Báo hỏng→IMM-12 `IncidentCreate` `corrective.create` · PM→IMM-08 `PMWorkOrderCreate` `pm.create` · CM→IMM-09 `CMCreate` `repair.create` · Hiệu chuẩn→IMM-11 `CalibrationCreate` `calibration.create`) — **chốt 1 cap SSoT `<domain>.create`**, ghi mismatch route-guard hiện gate `.write`; D2 `available_actions: list[{key,label,route,enabled,reason}]` derive SERVER-SIDE = capability ∩ lifecycle (bảng lifecycle×action: Decommissioned→cấm tất cả; Out of Service→chỉ báo hỏng+CM; Draft→cấm; còn lại full), 1 predicate SSoT, nút disabled+tooltip (KHÔNG render nút chết); D3 deep-link `?asset=<name>&source=qr-scan` (KHÔNG raw `qr_token`); D4 QR-gen `before_insert→_ensure_qr_token` phủ form+import+registration (KHÔNG code import riêng) + backfill legacy idempotent + `_build_qr_url` đã wire site_config; D5 nhãn 5 field (QR+Model+Số serial NSX+Tên+Mã) — gap `build_asset_label_data` thiếu `manufacturer_sn`+`asset_name` + khổ tem 50×30/70×40mm/A4-grid; **D6 ✅ EXECUTED Vòng 3 (2026-06-08):** tách cap `asset.print`→(AC Asset,"print") + `asset.qr.rotate`→(AC Asset,"write") cho persona vận hành (đổi 4 gate `api/imm00.py`, FE router+views, CAP_SET_VERSION v95.3388ee5629c1→v97.c30c69b8974d; KHÔNG hardcode role — gate thuần DocPerm). Gate phân tích D1–D5 — thực thi Vòng 2+; D6 đã thực thi xong.
- [`./ADR-IMM00-LABEL-PDF.md`](./ADR-IMM00-LABEL-PDF.md) — **[V1-GATE BE DONE · V2-GATE FE Accepted 2026-06-11] In nhãn QR qua PDF server-side đúng khổ tem nhiệt 60×100mm** (Phương án A — USER duyệt; window.print()+@page browser KHÔNG đảm bảo khổ tem nhiệt): D1 endpoint MỚI `print_asset_labels_pdf(assets="", preset="tem-60x100")` trả **PDF bytes** (`%PDF-`, `application/pdf` qua `frappe.local.response`), KHÔNG JSON dict; lỗi nghiệp vụ = `_err` HTTP-200 Error envelope; D2 service `render_asset_labels_pdf(names, preset)->bytes` tái dùng `build_asset_label_data_batch` (no N+1) + QR **`pyqrcode` SVG inline** (`qrcode`/`segno` KHÔNG có trong bench — verified; error='M', encode `qr_url` `/a/<token>`) + HTML N block (page-break-after trừ cuối → N asset=N trang) + `get_pdf`; D3 layout ≥5 field (QR+Model+Số serial NSX+Tên+Mã, đồng nhất §D5 ADR-QR-SCAN) + lifecycle dịch VI (no EN-leak); D4 QR server-side encode `qr_url` (KHÔNG raw `qr_token`/URL desk — no-raw-token parity `_strip_qr_token`); D5 khổ tem = options `page-width:60mm`+`page-height:100mm`+4×`margin:0mm`+`Portrait` (bẫy: `prepare_options` default margin 15mm nếu falsy → set `"0mm"` truthy); D6 bảo mật `rbac.require('asset.print')` ĐẦU TIÊN→rate-limit(20/60s)→preset(422)→empty(422)→batch>200(413 SAU rbac no-leak)→IDOR all-or-nothing(403 toàn call) — 2 loại 403 (dispatcher vs in-handler cap); D7 list rỗng→422, asset∄ trong batch→ô lỗi an toàn TRONG PDF (KHÔNG vỡ, KHÔNG 404 all-or-nothing — BA chốt); D8 render PDF KHÔNG ghi `label_printed` (audit chỉ ở `mark_label_printed` GỌI RIÊNG sau in — guard audit-on-cancel); D9 KHÔNG chạm gen/rotate/scan/resolve QR, KHÔNG pip install/bench migrate, site_config `assetcore_label_preset` (Vòng 3). **V2 (luồng in FE):** D10 api client `printAssetLabelsPdf(assets, preset='tem-60x100'): Promise<Blob>` qua axios `api` raw (`responseType:'blob'`, body `JSON.stringify(assets)`+preset, withCredentials+CSRF, batch=1 lời gọi giữ thứ tự; NOT `frappeGet/frappePost` — unwrap JSON không đọc Blob); hằng MỚI `DEFAULT_LABEL_PRESET='tem-60x100'` (TÁCH BIỆT `LABEL_FORMATS` cũ); D11 **content-type guard (Self-Correction cốt lõi):** BE trả HTTP-200 cho CẢ thành công (`application/pdf` blob) LẪN 4 nhánh `_err` (preset/empty-422·IDOR-403·batch-413 = `application/json` envelope) → axios interceptor KHÔNG bắt lỗi HTTP-200 → `extractPdfBlobOrThrow` phát hiện content-type: pdf→resolve Blob / khác→`res.data.text()`→JSON.parse unwrap `{message:{error,code,http_status}}`→ném ApiError VI (TUYỆT ĐỐI KHÔNG đưa JSON-blob cho iframe); cap-403(`rbac.require` RAISE)/dispatcher-403/429 vẫn đi axios interceptor (HTTP-403/429); D12 luồng `<iframe>` ẩn `onload→contentWindow.print()` + preview `BaseModal` embed CHÍNH PDF (WYSIWYG cùng-blob) + `markLabelPrinted` chỉ-on-confirm nút "Đã in xong"/`onafterprint` (audit-on-cancel) + `revokeObjectURL` chống leak + gate `v-if can('asset.print')` + GIỮ luồng `window.print()` cũ song song (ƯU TIÊN PDF cho 60×100). 11 TC-LABEL-PDF TDD (BE) + DoD vitest FE suite (assetDetailQrPrint/AssetLabelPrintView/assetLabelFormat/assetListBatchSelect) 0 regression + test mới GREEN, vue-tsc 0. ⚠️ endpoint PDF CHƯA live HTTP tới khi USER reload gunicorn → Playwright BLOCKED, eval KHÔNG tuyên bố "in thật". BE Vòng 1 DONE, FE Vòng 2, polish Vòng 3.

## Source docs (cũ) — đã archive

Source docs gốc (7 files) đã được move sang `docs/architecture/archive/imm-00/` sau khi review code 2026-05-08:

- `IMM-00_API_Interface.md` — API spec gốc (envelope cũ)
- `IMM-00_Functional_Specs.md` — FR/NFR gốc
- `IMM-00_Inventory_Design.md` — Inventory sub-domain v4 gốc
- `IMM-00_Module_Overview.md` — Module overview gốc
- `IMM-00_Setup_Guide.md` — Setup guide gốc
- `IMM-00_Technical_Design.md` — Technical design gốc (1937 dòng)
- `IMM-00_UI_UX_Guide.md` — UI/UX guide gốc

## Những thay đổi trong review 2026-05-08

Các discrepancy chính được sửa trong lần review này:

**04_Backend_Design.md:**
- DocType catalog: cập nhật từ 18 → 27 DocType (verified vs `assetcore/assetcore/doctype/`)
- DocType path: sửa từ `assetcore/doctype/` → `assetcore/assetcore/doctype/`
- Service functions: cập nhật 10 → 22 functions (thêm transfer, GMDN, scheduler, KPI rollup)
- `transition_asset_status()` return type: sửa từ dict → None
- `services/inventory.py`: xóa section (file không tồn tại trong shared/)
- Import path ServiceError: sửa từ `assetcore.services.exceptions` → `assetcore.services.shared.errors`
- ErrorCode: sửa từ `AC-E001..E012` → string constants (`NOT_FOUND`, `FORBIDDEN`, ...)

**05_API_Specification.md:**
- `transition_asset_status` → `transition_status`
- `get_asset_lifecycle_history` → `get_asset_timeline`
- `search_assets_by_udi`, `get_assets_due_pm` → không tồn tại (removed)
- `get_sla_for` → `resolve_sla_policy`
- `list_audit_events` → `list_audit_trail`
- `get_audit_event` → `get_audit_entry`
- `verify_audit_chain` → `verify_chain`
- `create_capa` → `open_capa`
- `close_capa` → `close_capa_record`
- `list_departments_tree`, `list_locations_tree` → `list_departments`, `list_locations`
- Trigger endpoints: `trigger_check_*` → `trigger_*_check` pattern + GET (không phải POST)
- `update_asset`, `update_supplier`: PUT → POST
- Thêm 8 endpoint groups mới không có trong spec cũ
- `close_incident` → không tồn tại (removed)

**06_Frontend_Design.md:**
- Vue views: chỉ 2 views built (`ReferenceDataView.vue`, `SlaPolicyListView.vue`); sitemap labeled [BUILT]/[SPEC]
- Pinia stores: sửa từ pattern chung → 4 stores thực tế (`useAssetStore`, `useRefDataStore`, `useCapaStore`, `useIncidentStore`)
- API client: sửa từ object-style `imm00Api{}` → named exports; sửa endpoint names
- lifecycle_status colors: thêm đúng values (Commissioned, Calibrating, Under Maintenance)

**07_Testing_QA.md:**
- TC-S-003: `transition_asset_status` return → None (không phải dict); thêm verify downtime log
- TC-S-006: exception type → `frappe.exceptions.ValidationError` (không phải ServiceError)
- TC-S-009: CAPA signature → `due_days: int` (không phải `due_date: str`); xóa `linked_incident`

## Roadmap tiếp theo

- [ ] (Optional) Pentest report upload tại `docs/security/imm00-pentest.md`
- [ ] (Optional) Screenshot UI thực tế trên staging → đính kèm vào `09_Release.md §I`
- [ ] Build còn thiếu: các views [SPEC] trong sitemap

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Codebase ground truth (BE): `assetcore/services/imm00.py` · `assetcore/api/imm00.py` · `assetcore/services/shared/`
- Codebase ground truth (FE): `frontend/src/types/imm00.ts` · `frontend/src/api/imm00.ts` · `frontend/src/stores/imm00.ts`
- Source docs (cũ): `docs/architecture/archive/imm-00/`

---

*IMM-00 là foundation layer — deploy trước mọi module IMM-01→IMM-17.*
