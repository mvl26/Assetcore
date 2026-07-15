# ADR-MOBILE-036 — `getIncident` `IncidentDetail` SLA-flag scan-schema-parity (**CR-21 · SLA-detail-parity** — bồi 2 property `is_response_breached` + `is_resolution_breached` (cờ SLA DERIVED-LIVE `0|1`) vào schema `IncidentDetail` NGAY CẠNH cờ thô `resolution_breached` để đóng typed-contract gap màn **Chi tiết sự cố F2**; parity precedent `IncidentListItem` — badge "Tình trạng SLA" màn Chi tiết PHẢI khớp danh sách/dashboard tại cùng thời điểm, KHÔNG stale-divergence)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-036 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-13 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200 — 200-shape `IncidentDetailEnvelope` `{data: IncidentDetail}` KHÔNG đổi) · **ADR-IMM12-08** (`docs/imm-12/05 §17` — màn Chi tiết đọc cờ SLA-breach DERIVED server-flag, supersede "detail out-of-scope đọc cờ thô"; INV-SLA-5 mở rộng detail + INV-SLA-6 terminal) · **precedent field-parity**: `IncidentListItem.is_response_breached`/`is_resolution_breached` (đã curate — cùng `_enrich_sla_breach`, cùng description) · **precedent optional-emit**: `IncidentDetail.allowed_transitions` (`imm12.py:778`, R3) + `IncidentDetail.scene_photos` (CR-17/G6) — emit-luôn nhưng `required` GIỮ `['name']` · Core Doc IMM-12 narrative [`04-api-contract.md`](./04-api-contract.md) §3.2 (bảng read-envelope `getIncident` + note SLA-flag parity) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (@2026-07-13): service `get_incident_detail(name)` @`assetcore/services/imm12.py:1110` gọi `_enrich_sla_breach([data])` @**1132** (SAU `asset_name`@1128 + `allowed_transitions`@1129) — enrich gán `data["is_response_breached"]` + `data["is_resolution_breached"]` (0|1) qua `_row_is_breached(row, kind, now)` @`imm12.py:209-215` (**CÙNG SoT predicate** với `list_incidents`@982 + `get_dashboard`@1251). `_enrich_sla_breach` set 2 key **vô-điều-kiện** (mọi row → 2 int). `git diff` `services/imm12.py`/`api/imm12.py` vùng `get_incident_detail`/`_enrich_sla_breach` = TRỐNG round NÀY ⇒ backend + BE test (`test_imm12.py::TestIncidentDetailSlaLive` @948-975: `test_get_incident_detail_sla_live`/`_terminal`/`test_detail_list_sla_parity`) ĐÃ LIVE (source-verified), thay đổi CHỈ ở OAS mirror. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (`IncidentDetail.properties.is_response_breached` + `.is_resolution_breached`). Nguồn yêu cầu: `assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` CR-21.

---

## Context

Màn **Chi tiết sự cố F2** (mobile `IncidentDetailView`, mở từ danh sách "Báo hỏng của tôi" hoặc deep-link `assetcore://incident/<name>`) render badge **"Tình trạng SLA"** (Trong hạn / Quá hạn phản hồi / Quá hạn xử lý). Badge này PHẢI khớp badge cùng phiếu ở **danh sách** (`listIncidents` → `IncidentListItem`) và **dashboard** tại **cùng thời điểm** — nếu lệch (stale-divergence), KTV thấy "Trong hạn" ở màn Chi tiết trong khi danh sách hiện "Quá hạn" trên cùng 1 phiếu ⇒ mâu thuẫn nhìn thấy được.

Cội nguồn stale-divergence (đã chốt ADR-IMM12-08): cờ thô `response_breached`/`resolution_breached` (Check @`incident_report.json`) CHỈ do scheduler `check_incident_sla_breach()` (hàng giờ) hoặc write-path acknowledge/resolve **stamp**. Incident vừa quá hạn 1–59′ (scheduler chưa quét) → cờ thô còn `0` dù `response_due_at`/`resolution_due_at` đã quá khứ. Danh sách/dashboard đã sửa (BR-12-13) bằng cách **derive LIVE** cờ `is_response_breached`/`is_resolution_breached` qua `_enrich_sla_breach` (server-flag SoT — KHÔNG so ngày client-clock, memory `overdue_server_flag_ssot`).

Hệ quả contract-gap (CR-21, phát hiện khi so màn Chi tiết vs danh sách):
- Service `get_incident_detail` @`imm12.py:1132` **ĐÃ emit** `is_response_breached`/`is_resolution_breached` (CÙNG helper `_enrich_sla_breach` với list/dashboard, INV-SLA-5) — nhưng schema `IncidentDetail` của OAS mirror **CHƯA khai** 2 property này.
- `IncidentListItem` (danh sách) **đã curate** 2 cờ derived (precedent, `yaml:1272`) ⇒ codegen mobile phơi badge danh sách typed; NHƯNG codegen màn **Chi tiết** KHÔNG có typed access 2 cờ (dù backend trả) ⇒ FE Chi tiết phải đọc field un-typed (`as_dict` passthrough) hoặc rớt về cờ thô stale → tái lệch.
- `IncidentDetail` là **schema MỞ** (`additionalProperties:true` — as_dict surface field), nên 2 cờ **không bị drop** khi deser, NHƯNG codegen typescript-axios chỉ sinh field cho property **khai tường minh** ⇒ typed-contract gap (FE mất autocomplete + type-safety cho badge SLA).

Ràng buộc quyết định:
1. **BE emit vô-điều-kiện, đối xứng `IncidentListItem`** (`_enrich_sla_breach` set 2 int cho mọi row) ⇒ 2 cờ khai `type:integer` `enum:[0,1]`, description **VERBATIM** precedent `IncidentListItem` (1 SoT `_enrich_sla_breach`).
2. **OPTIONAL (∉ `required`)** — mirror `IncidentListItem` (2 cờ derived đều optional; `required` GIỮ `['name']` như `allowed_transitions`/`scene_photos`).
3. **Schema MỞ GIỮ NGUYÊN**: `IncidentDetail.additionalProperties:true` (as_dict passthrough có chủ đích) — **KHÔNG flip `false`** (khác `AssetScanInfo` closed-schema ADR-035).
4. **CONTRACT-ONLY**: service + BE test ĐÃ LIVE @source — thay đổi CHỈ ở OAS mirror, **KHÔNG đụng `.py`, KHÔNG reload worker, KHÔNG migrate**.
5. **KHÔNG drift**: `IncidentDetail` giữ CẢ cờ thô `response_breached`/`resolution_breached` (raw, backward-compat) + hạn `response_due_at`/`resolution_due_at`; path/opId 65 GIỮ + c5 54 GIỮ (schema-FIELD add ≠ path/schema-component mới); tổng property 41→43.

## Decision

Bồi 2 property vào schema `IncidentDetail`, NGAY CẠNH cờ thô `resolution_breached` (nhóm SLA-field liền mạch), **description copy VERBATIM** từ precedent `IncidentListItem`:

### `IncidentDetail.properties.is_response_breached`
- **`type: integer`** + **`enum: [0, 1]`** (Open#1 int-vs-bool — derived int `0|1`, KHÔNG `boolean`).
- **`description` VERBATIM** (khớp byte-for-byte `IncidentListItem.is_response_breached`): *"Cờ SLA phản hồi DERIVED LIVE (0|1) — badge FE đọc field này thay cờ thô (INV-SLA-5). imm12 _enrich_sla_breach."*

### `IncidentDetail.properties.is_resolution_breached`
- **`type: integer`** + **`enum: [0, 1]`**.
- **`description` VERBATIM**: *"Cờ SLA xử lý DERIVED LIVE (0|1) — badge FE đọc field này thay cờ thô (INV-SLA-5). imm12 _enrich_sla_breach."*

### `IncidentDetail.required[]` — KHÔNG đổi
- 2 cờ derived **OPTIONAL** — KHÔNG thêm vào `required` (mirror `IncidentListItem`; `required` GIỮ `['name']`).

### `IncidentDetail.additionalProperties` — KHÔNG đổi
- GIỮ `true` (as_dict passthrough có chủ đích — KHÔNG flip `false`).

### Invariant contract (guard `TestMobileIncidentDetailSlaFlagParity` a..f, `test_mobile_oas`)
- **TC-a** `IncidentDetail.properties` CÓ CẢ `is_response_breached` + `is_resolution_breached` (drift-closed; RED trước bồi → GREEN sau).
- **TC-b** mỗi cờ = `type:integer` + `enum:[0,1]` (int-vs-bool).
- **TC-c** `description` 2 cờ = **VERBATIM** description `IncidentListItem` (parity — cùng `_enrich_sla_breach`, 1 SoT).
- **TC-d** 2 cờ OPTIONAL (∉ `required`; `required` GIỮ `['name']`).
- **TC-e** `additionalProperties:true` GIỮ NGUYÊN + cờ thô (`response_breached`/`resolution_breached`) + hạn (`response_due_at`/`resolution_due_at`) KHÔNG mất.
- **TC-f** tổng property `IncidentDetail` == **43** (41 baseline + 2 cờ derived — KHÔNG thêm/xoá field lạ).
- **RED-before/GREEN-after** chứng minh trên TC-a/TC-c: strip `is_response_breached` → RED (`DRIFT: IncidentDetail schema THIẾU is_response_breached`); bồi lại → GREEN.

## Alternatives

| Phương án | Vì sao LOẠI |
|---|---|
| **A. Giữ nguyên (không bồi property)** | Không đóng CR-21 — service emit 2 cờ derived nhưng schema Chi tiết KHÔNG khai ⇒ codegen mobile mất typed access badge SLA màn Chi tiết; FE rớt về cờ thô stale → tái stale-divergence với danh sách. |
| **B. Bồi property NHƯNG thêm vào `required`** | LỆCH precedent `IncidentListItem` (2 cờ derived đều optional) + phá pattern optional-emit `allowed_transitions`/`scene_photos` (`required` GIỮ `['name']`). Derived-emit ≠ contract-required. |
| **C. Flip `additionalProperties:false`** cho `IncidentDetail` | Phá as_dict passthrough có chủ đích — `IncidentDetail = doc.as_dict()` surface nhiều field động (naming_series/amended_from/child-table…) KHÔNG khai hết; đóng schema = strict codegen crash field web-only. `IncidentDetail` cố ý MỞ (khác `AssetScanInfo` closed ADR-035). |
| **D. Bỏ cờ thô `response_breached`/`resolution_breached`, chỉ giữ derived** | Phá backward-compat (consumer cũ đọc cờ thô); ADR-IMM12-08 chốt **giữ CẢ HAI** (fallback `is_*_breached ?? *_breached` an toàn payload transition). |
| **E. Description tự viết mới (không copy precedent)** | Vi phạm parity — 2 cờ CÙNG `_enrich_sla_breach`, CÙNG ngữ nghĩa với `IncidentListItem`; description lệch = 2 mô tả cho 1 SoT → codegen/doc drift. VERBATIM là đúng. |

## Consequences

- **(+)** Codegen client phơi `is_response_breached: number`/`is_resolution_breached: number` (0|1) ⇒ màn Chi tiết sự cố F2 render badge "Tình trạng SLA" typed, parity danh sách/dashboard tại cùng `now` (INV-SLA-5 mở rộng detail); đóng typed-contract gap.
- **(+)** Property + description khai == BE emit (`_enrich_sla_breach`) + == precedent `IncidentListItem` (TC-a/b/c/f introspect-vs-schema + verbatim-parity) ⇒ contract trung thực @source, chống drift.
- **(+)** SCHEMA-FIELD ADD: path-count **65 GIỮ**, opId **65 GIỮ**, c5 **54 GIỮ**, `additionalProperties:true` GIỮ NGUYÊN, `required` GIỮ `['name']` ⇒ baseline closed-schema sweep + path-count guard + YAML lint + d12/d15/d17 KHÔNG đỏ. Tổng property `IncidentDetail` 41→**43**.
- **(0)** CONTRACT-ONLY: 0 đụng `.py`, 0 reload worker, 0 migrate. Test: `test_mobile_oas` 610→**616** (+6 TC `TestMobileIncidentDetailSlaFlagParity` a..f) · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 610→616 / `_GUARD_SUITE_SUM` 753→**759** / `_MOBILE_OAS_TOTAL` 779→**785** + delta var `sla_detail_parity_delta=6` (transition-baseline doc_09). BE regression `test_imm12` (`TestIncidentDetailSlaLive` @948-975) GREEN — chứng minh SoT `_enrich_sla_breach` KHÔNG đổi.

### Naming guard (∅)
Không thêm schema/component mới ⇒ 0 va chạm tên. 2 property `is_response_breached`/`is_resolution_breached` là field NỘI-BỘ của `IncidentDetail` (đối xứng `IncidentListItem`) — không đăng ký `components/schemas` mới. Cờ thô `response_breached`/`resolution_breached` (raw) GIỮ trong schema (khác tên → KHÔNG đụng).

## Handoff CORE-DEV (native repo — ngoài `assetcore`)

Sau khi regenerate client từ OAS mirror: model `incident-detail.ts` (hoặc tương đương) có `is_response_breached?: number` + `is_resolution_breached?: number` (optional, 0|1). Màn Chi tiết sự cố F2 render badge "Tình trạng SLA" đọc `is_*_breached ?? *_breached` (ưu tiên derived, fallback cờ thô cho payload cũ) — TÁI DÙNG `SlaBreachBadge` + SSoT label như danh sách, **KHÔNG so ngày client-clock** (`Date.now()`/`new Date()` compare `due_at` = anti-pattern, server-flag là SoT). CR-21 → RESOLVED (contract-parity, backend đã ship).
