# IMM-12 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-12 — Sự cố (Incident / RCA / CAPA)** |
| Wave | 1 |
| Trạng thái | ✅ Live — Code deployed (BE + FE + DocTypes) |
| Số file | 8 (5 template chuẩn + 3 deployment docs) |
| Cập nhật cuối | 2026-07-14 (Round 32 CR-24 [BA spec] `report_incident` idempotency `client_request_id` — mobile write-outbox: đóng cửa sổ re-drain outbox tạo phiếu sự cố TRÙNG (NĐ98 audit-integrity). Core Doc: DocType `Incident Report` +field `client_request_id` (Data, `search_index:1` NON-UNIQUE index, `hidden/read_only/no_copy`); service `report_incident` +param optional `client_request_id` → SELECT-before-insert scope `(client_request_id, reported_by)` early-return phiếu cũ TRƯỚC insert/`_log`/lifecycle-event ⇒ 0 double audit/event; rỗng→tạo mới NGUYÊN VẸN (backward-compat 100%). OAS mirror `ReportIncidentRequest` +prop optional `client_request_id` (∉ required; **COUPLED** handler-parity test 13e ⇒ KHÔNG pure-yaml, land ATOMIC cùng handler-param). **Self-Correction:** `ReportIncidentRequest` HIỆN OPEN (KHÔNG có `additionalProperties:false` @yaml:3239-3271, cố ý cho 8 param Phase-C pending) ⇒ GIỮ OPEN, KHÔNG đóng. BR-12-25 + ADR-IMM12-09 (app-guard+index NON-UNIQUE, loại DB-UNIQUE vì `""` collide) + TC-12-IDEMP-01..06 (RED-before). File đụng: 02/04/05/07/README. Trước đó Round 39 CR-WF-12-REOPEN mobile Trục B: curate `reopenIncident` (`imm12.reopen_incident`) vào OAS mirror `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — mở lại điều tra `Resolved → In Progress`, ĐÓNG NỐT bộ nút Chi tiết sự cố F2 (companion `closeIncident` đã curate). 1 path MỚI (POST, tag `incident`, opId `reopenIncident`; path-count 74→75) + 1 schema MỚI `ReopenIncidentRequest` `{name req, reason req}` `additionalProperties:false` — **`reason` REQUIRED** (KHÁC `StartWorkRequest`/`CloseIncidentRequest` optional-notes); success **REUSE `IncidentActionEnvelope`** (data 2-key `{name, status:'In Progress'}` — mirror `startWork`, KHÁC `resolve`/`close` 3-key RIÊNG); 200 = `oneOf [IncidentActionEnvelope | Error]` Decision-B route-by-VALUE `body.success`; 403 = SINGLE-SHAPE `Forbidden` (dispatcher-403; in-handler cap-403 `_can_close` phủ bởi nhánh Error 200-oneOf — mirror `closeIncident`). CONTRACT-ONLY pure-yaml (BE LIVE `api/imm12.py:371` + `services/imm12.py:713`, covered `test_imm12.py:3199`; 0 `.py` runtime / 0 reload / 0 migrate); `test_mobile_oas`+`test_mobile_docset`+`test_imm12` GREEN. ADR-MOBILE-006. Trước đó Round 38 CR-WF-12-RCA-ENTRY: surface cạnh workflow "Yêu cầu RCA" (Resolved → RCA Required) thành CTA server-driven — cấp driver THẬT cho `allowed_transitions['RCA Required']` đang advertise-mà-câm. Endpoint MỚI `request_rca(name, rca_reason)` qua `apply_workflow("Yêu cầu RCA")` (mirror `_advance_incident_after_rca`, KHÔNG `db.set_value`) + sync `status` Select + idempotent RCA reuse (`create_rca` guard trước 409) + audit `_log` (Resolved→RCA Required, KHÔNG event_type mới, precedent reopen D4); precondition `status≠Resolved`→`IMM12_REQUEST_RCA_BAD_STATE` (422 MSG MỚI, KHÔNG dùng `IMM12_BAD_STATE`=409) + `rca_reason` blank→`IMM12_RCA_REASON_REQUIRED`; cap-gate `compliance.submit` ({Compliance Manager, Super Admin} ⊆ workflow allowed → KHÔNG false-clickable; rbac.can+`_MSG_FORBIDDEN`, KHÔNG leak). **KHÔNG đổi `_VALID_TRANSITIONS`/workflow JSON/DocPerm** (state edge đã reconciled Round 12) ⇒ INVARIANT `TestIncidentAllowedTransitions` + admin-override 22/22 GREEN + 0 `bench migrate`. FE `canRequestRca = can('compliance.submit') && status==='Resolved' && allowed_transitions.includes('RCA Required')` + nút "Yêu cầu phân tích RCA" + modal `rca_reason` + refetch (stepper nhánh RCA Required, badge). ENTRY↔EXIT khép kín với `_advance_incident_after_rca` (auto-close sau RCA Completed, đã build). ADR-IMM12-RCA-ENTRY + BR-12-24 + TC-12-REQRCA-01..06. Trước đó Round 30 CR-WF-12-RCA desk↔endpoint parity: bịt asymmetry RBAC luồng RCA — Corrective Manager có `corrective.write` (gọi được `start_rca`/`submit_rca`) nhưng workflow desk "Bắt đầu/Hoàn thành phân tích RCA" thiếu row role ⇒ desk chặn. Fix = THÊM 1 row `Corrective Manager` vào 2 transition đó trong **cả** `imm_12_rca_workflow.json` + `fixtures/workflow.json` (role-set mỗi action quản-RCA = {Corrective User, Corrective Manager, System Manager, AssetCore Super Admin}; "Hủy RCA" giữ nguyên); + INVARIANT `INV-RCA-PARITY-A/B/C` (SSoT⇄workflow codomain · desk⊇endpoint-cap ĐỘNG qua rbac · fixture==source) làm luật chống tái-drift; live-sync qua fixture re-import (backfill KHÔNG thêm Corrective Manager), KHÔNG `bench migrate`; ADR-IMM12-RCA-PARITY mở rộng ADR-RCA-CTA D2 (lần trước chỉ vá "Hủy RCA"). Trước đó Round 18 SLA-detail-parity / CR-21: bồi 2 property `is_response_breached`+`is_resolution_breached` (cờ SLA derived-live, description VERBATIM `IncidentListItem`) vào schema `IncidentDetail` OAS mirror — parity badge "Tình trạng SLA" màn Chi tiết F2; CONTRACT-ONLY (BE `_enrich_sla_breach` + `test_imm12` LIVE), 0 `.py`/reload/migrate; ADR-MOBILE-036 + §17 closure. Trước đó 2026-07-11 Round 12 CR-WF-12: đối soát SSoT `_VALID_TRANSITIONS` (incident) ⇄ `imm_12_incident_workflow.json` — fix 2 drift [(a) thêm `Resolved→In Progress` surface "Mở lại điều tra" BR-12-23 · (b) gỡ `In Progress→RCA Required` dead-edge] + EXCEPTION_EDGES `{RCA Required→Closed}` auto-advance + INVARIANT guard `TestIncidentAllowedTransitions` / ADR-IMM12-INCIDENT-CTA; KHÔNG đụng workflow JSON → admin-override GREEN. Trước đó Round 9 RCA server-driven CTA BR-12-19..22 / ADR-IMM12-RCA-CTA; CR-21 round 4 `is_*_breached`; BR-12-17/18 ảnh hiện trường NĐ98) |
| Khối kiến trúc | C. KHỐI 3 |
| Đợt triển khai | 1 |
| Owner | PTP Khối 2 · Workshop / Nhóm TBYT |

> File index của module IMM-12. Template docs (`02–06`) đã được cross-check với codebase thực tế và cập nhật.
> Files cũ (`IMM-12_*.md`) đã archive vào `docs/architecture/archive/imm-12/`.

---

## Template chuẩn (v4.1+ — cross-checked vs codebase)

| File | Mô tả | Trạng thái |
|---|---|---|
| [`02_Analysis_Design.md`](./02_Analysis_Design.md) | Module overview · Business process · Use case · Functional specs · NFR | ✅ Live |
| [`03_Diagrams.md`](./03_Diagrams.md) | ERD · Class diagram · Sequence diagram · Package diagram | ✅ Live |
| [`04_Backend_Design.md`](./04_Backend_Design.md) | DocType · Workflow · Service layer · API layer · Scheduler · Integration | ✅ Live — corrected |
| [`05_API_Specification.md`](./05_API_Specification.md) | API catalog · Response envelope · Error codes · 14 actual endpoints | ✅ Live — corrected |
| [`06_Frontend_Design.md`](./06_Frontend_Design.md) | Sitemap · Actual .vue files · API client · Status states | ✅ Live — corrected |

---

## ADR — Quyết định kiến trúc

| ADR | Phạm vi | Trạng thái |
|---|---|---|
| [`ADR-IMM12-REPORT-FAILURE.md`](./ADR-IMM12-REPORT-FAILURE.md) | **V4-GATE Báo hỏng e2e từ quét QR** — D1 cap-gate `corrective.create` 3-tier parity (đóng lỗ leo quyền P1) · D2 canonical lifecycle `incident_reported` + provenance `source` · D3 FE field-lock + source · D4 scope-guard | ✅ Accepted (2026-06-08) |

> ADR là quyết định cuối cho slice tương ứng. Khi mâu thuẫn doc ↔ ADR → ADR thắng. Liên quan: `../imm-00/ADR-IMM00-QR-SCAN-ACTION.md`, `../imm-00/ADR-IMM00-ASSETCODE.md`.

---

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File cũ (reference) | Ghi chú |
|---|---|---|
| 02 Analysis_Design | `IMM-12_Module_Overview.md` + `IMM-12_Functional_Specs.md` | Đã gộp và chuẩn hóa vào 02 |
| 03 Diagrams | `IMM-12_Technical_Design.md` §4 ERD + §5 State Machines | Đã tách riêng vào 03 + Data Dictionary |
| 04 Backend_Design | `IMM-12_Technical_Design.md` §2–§3 (Service, Controller, hooks) | Đã chuẩn hóa vào 04 |
| 05 API_Specification | `IMM-12_API_Interface.md` | Updated envelope `{success, data}` chuẩn |
| 06 Frontend_Design | `IMM-12_UI_UX_Guide.md` | Updated theo template v4.1 |

---

## Files hiện có

### Template chuẩn (cross-checked vs codebase)
- [`02_Analysis_Design.md`](./02_Analysis_Design.md)
- [`03_Diagrams.md`](./03_Diagrams.md)
- [`04_Backend_Design.md`](./04_Backend_Design.md) — corrected DocType names, states, service functions, API layer
- [`05_API_Specification.md`](./05_API_Specification.md) — corrected: 14 actual endpoints, corrected request fields
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — corrected: actual .vue filenames, actual status states

### Deployment docs
- [`07_Testing_QA.md`](./07_Testing_QA.md) — Test plan + Security + Code quality
- [`08_Deployment.md`](./08_Deployment.md) — Deployment + QMS Mapping
- [`09_Release.md`](./09_Release.md) — User guide + Release notes + Traceability

### Archived (moved)
> Files cũ (`IMM-12_*.md`) đã được archive vào [`docs/architecture/archive/imm-12/`](../../architecture/archive/imm-12/).

---

## Roadmap chuẩn hóa

- [x] Tạo **`02_Analysis_Design.md`** — Module overview · Business process · Use case · Functional specs · NFR
- [x] Tạo **`03_Diagrams.md`** — ERD · Class · Sequence (3 diagrams) · Package
- [x] Tạo **`04_Backend_Design.md`** — DocType · Workflow · Service · API · Scheduler · Integration
- [x] Tạo **`05_API_Specification.md`** — Catalog · Envelope chuẩn `{success, data}` · Error codes
- [x] Tạo **`06_Frontend_Design.md`** — Sitemap · Mockup · Components · Store · Copy
- [x] ✅ Implement BE: `services/imm12.py` + `api/imm12.py` + DocType JSONs (incident_report, imm_rca_record, imm_capa_record, imm_rca_five_why_step, imm_rca_related_incident)
- [x] ✅ Implement FE: Vue components (7 views: IncidentList/Create/Detail, RCADetail, CAPAList/Detail, IMM12Dashboard) + API client (`api/imm12.ts`)
- [x] ✅ Cross-check docs vs codebase + corrections applied (2026-05-08)
- [x] ✅ Archive old source files → `docs/architecture/archive/imm-12/`
- [ ] UAT execution

---

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm12.py` · `assetcore/api/imm12.py` ✅
- Codebase ground truth (FE): `frontend/src/api/imm12.ts` ✅
- DocTypes: `assetcore/assetcore/doctype/incident_report/` · `imm_rca_record/` · `imm_capa_record/` · `imm_rca_five_why_step/` · `imm_rca_related_incident/`
- LIVE foundation: `assetcore/services/imm00.py` · `assetcore/api/imm00.py`
- Archive (old reference docs): `docs/architecture/archive/imm-12/`

---

*Module index — cập nhật 2026-05-08 sau khi cross-check codebase và archive files cũ.*
