# ADR-IMM12-REPORT-FAILURE — BÁO HỎNG end-to-end từ quét QR: 3-tier cap-gate + canonical lifecycle event + FE field-lock/source

| Mục | Giá trị |
|---|---|
| Trạng thái | **Accepted** ([V4-GATE] — factory báo-hỏng-slice, Vòng 4/10 PHÂN TÍCH) |
| Ngày | 2026-06-08 |
| Phạm vi | IMM-12 (Incident & CAPA) — luồng `report_incident` end-to-end từ màn quét QR; chạm IMM-00 (lifecycle/audit helper) + rbac SSoT |
| Owner | BA Lead + System Architect |
| Liên quan | `docs/imm-00/ADR-IMM00-QR-SCAN-ACTION.md` (D1/D2/D3 — scan-action SSoT, cap `corrective.create`, deep-link `?asset&source=qr-scan`); `docs/imm-00/ADR-IMM00-ASSETCODE.md` (invariant `asset_code==name` → `?asset=<name>` an toàn) |
| Supersedes | Không — đóng 3 gap đã verify tại source trong luồng `report_incident` đang LIVE (KHÔNG đổi workflow/state machine IMM-12) |

> ADR này là **quyết định cuối** cho slice "báo hỏng từ quét QR". Mọi spec ở `docs/imm-12/04_Backend_Design.md`, `05_API_Specification.md`, `06_Frontend_Design.md`, `07_Testing_QA.md` và task BE/FE/QA Vòng 4 phải nhất quán với ADR này. Khi mâu thuẫn → ADR thắng.
>
> **Bản chất GATE:** đây là gate PHÂN TÍCH — Vòng 4-PHÂN-TÍCH KHÔNG đụng code (`.py`/`.vue`/`.ts`). Chỉ chốt cap-gate SSoT + canonical event + provenance + UX field-lock để BE/FE/QA thực thi mà KHÔNG phải hỏi lại. Mỗi task xuống dòng map được tới đúng 1 quyết định D1–D5 (**D5** = G1/CR-16 báo hỏng F2, contract-only, bổ sung factory Vòng 2/5 2026-06-27 — wire `occurred_datetime` vào yaml).

---

## Bối cảnh (vì sao cần GATE này)

**Đề mục [PM] Vòng 4 (raw):** "BÁO HỎNG end-to-end từ quét QR" — đóng kín 3 gap đã verify-tại-source trong luồng `report_incident`:
1. **3-tier VỠ ở BE = lỗ leo quyền P1.** Route-guard FE (`router/index.ts:450` `corrective.create`) + scan-action SSoT (`services/imm00.py:419-420` `corrective.create`) ĐỀU gate `corrective.create`, NHƯNG API+svc `report_incident` (`api/imm12.py:59-84`, `services/imm12.py:321-375`) **CHỈ chặn Guest-401** — KHÔNG gate `corrective.create`. ⇒ user có `corrective.read` (xem được dashboard) NHƯNG KHÔNG có `corrective.create` vẫn tạo được Incident qua API/curl trực tiếp (bypass cả 2 tầng trên).
2. **KHÔNG emit canonical lifecycle event** (vi phạm CLAUDE.md §10). `_log` (`services/imm12.py:208-221`) ghi audit với `event_type="Incident"` generic — KHÔNG phải canonical `incident_reported` (đã ghi ở **doc §6** + đã là Select-option hợp lệ của `Asset Lifecycle Event`). Thiếu trục lifecycle event + thiếu provenance nguồn báo hỏng (qr-scan vs manual).
3. **FE field-lock + source thiếu.** `IncidentCreateView.vue` prefill `?asset` đúng (dòng 13,29-30) NHƯNG `SmartSelect` (dòng 91) **luôn editable**; KHÔNG đọc `route.query.source`; KHÔNG truyền `source` vào `reportIncident` payload.

**Nguy cơ nếu KHÔNG chốt:**
- Gap (1) = **leo quyền** — bất kỳ user đăng-nhập nào (kể cả role chỉ-đọc) tạo được Incident → bẩn dữ liệu nghiệp vụ, có thể auto Out-of-Service tài sản (BR-12-04), vỡ kiểm soát truy cập NĐ98.
- Gap (2) = **vỡ truy xuất nguồn gốc** — không phân biệt được sự kiện "báo hỏng" với audit-row generic, không biết báo hỏng đến từ quét-QR hiện trường hay nhập tay (provenance) → suy giảm audit-trail (CLAUDE.md §5, §10).
- Gap (3) = **toàn vẹn dữ liệu UX** — user (vô tình/cố ý) đổi `asset` sau khi quét QR đúng thiết bị → Incident gắn nhầm tài sản; thiếu `source` ⇒ BE không nhận diện được nguồn để ghi provenance.

**5 câu hỏi domain (assetcore-doc Phần 2):**
1. **WHO HTM stage:** Maintenance (giai đoạn 5) — Incident reporting trong vận hành.
2. **NĐ98:** Điều 67 (incident/sự cố thiết bị — báo cáo trong cửa sổ luật định) + truy xuất nguồn gốc (audit trail bất biến). Kiểm soát truy cập (chỉ vai trò được cấp DocPerm `create` Incident Report mới báo hỏng).
3. **Stakeholder:** KTV TBYT / người vận hành (quét QR → báo hỏng tại hiện trường); Corrective Manager/User (DocPerm); QA Officer (audit/RCA downstream).
4. **Lifecycle event:** `incident_reported` (canonical, đã có trong Select `Asset Lifecycle Event`) — phát sinh lúc `report_incident` thành công, với provenance `source`.
5. **Hậu quả nếu data sai:** leo quyền tạo Incident rác (gap 1); mất trace nguồn báo hỏng + không phân biệt được lifecycle event (gap 2); Incident gắn nhầm asset (gap 3) → mọi RCA/CAPA/SLA downstream trỏ sai thiết bị.

---

## FACTS đã verify tại source (cơ sở quyết định — KHÔNG phỏng đoán)

| # | FACT | Evidence (`file:line`) |
|---|---|---|
| F1 | API `report_incident` CHỈ chặn Guest-401 (`if frappe.session.user == "Guest": return _err(...401)`) rồi `handle(svc_report, ...)` — **KHÔNG gọi `rbac` cap-gate nào**. Tương phản `cancel_incident`/`create_rca` cùng file gọi `_can_investigate()`→403. | `api/imm12.py:59-84` vs `:87-104` |
| F2 | svc `report_incident` cũng KHÔNG gate cap (chỉ BR-12-01 clinical_impact + asset-exists), `doc.flags.ignore_permissions = True` rồi insert. | `services/imm12.py:321-367` |
| F3 | `corrective.create` là cap HỢP LỆ, **auto-gen** từ `_DOMAIN_PRIMARY["Corrective"]="Incident Report"` → `CAPABILITY_MAP["corrective.create"]=("Incident Report","create")`. | `services/shared/rbac.py:72,85-91` |
| F4 | `rbac.require(cap)` mặc định throw `_("Khong du quyen: {0}").format(cap)` → **LEAK raw cap** `corrective.create` vào message (vi phạm AC1 "không leak raw cap"). `rbac.can(cap)` trả bool, KHÔNG raise. | `rbac.py:156-162` (require), `:141-154` (can) |
| F5 | Scan-action SSoT: `report_failure` → route `IncidentCreate`, capability `corrective.create` (1-1 với route-guard). Đây là tầng-1+2 đã đúng. | `services/imm00.py:419-420`; `frontend/src/router/index.ts:450` |
| F6 | `_log` (audit IMM-12) ghi `event_type="Incident"` generic vào `IMM Audit Trail` (hash-chained), KHÔNG ghi `Asset Lifecycle Event`. | `services/imm12.py:208-221` (đặc biệt `:212`) |
| F7 | **Doc↔code drift:** doc §6 đã ghi `report_incident` ⇒ `event_type='incident_reported'`(Minor)/`incident_reported_critical`(Critical) — NHƯNG code F6 chưa thực hiện. | `docs/imm-12/04_Backend_Design.md:442-443` vs F6 |
| F8 | `Asset Lifecycle Event.event_type` là **Select** với options cố định CÓ `incident_reported` (dòng options). **KHÔNG có `failure_reported`** ⇒ ghi `failure_reported` sẽ vi phạm Select validation / cần đổi schema. | `assetcore/.../asset_lifecycle_event.json` (field `event_type` options) |
| F9 | `create_lifecycle_event(asset, event_type, actor, from_status, to_status, root_doctype, root_record, notes)` là helper canonical (`utils/lifecycle.py:72-94`) ghi `Asset Lifecycle Event` — có field `notes` (provenance) + `root_record` (Dynamic Link, PHẢI kèm `root_doctype`). Đã expose qua `imm00.create_lifecycle_event` (`services/imm00.py:82`). | `utils/lifecycle.py:72-94`; `services/imm00.py:82` |
| F10 | Pattern mirror đã có ở IMM-09: wrapper `_log_lifecycle_event(*, asset, event_type, from_status, to_status, root_record, root_doctype, notes)` — bắt buộc truyền `root_doctype` cùng `root_record` nếu không Frappe throw "Root DocType must be set first" → event bị nuốt. | `services/imm09.py:493-514` |
| F11 | `verify_audit_chain(asset)` verify hash-chain trên **`IMM Audit Trail`** (KHÔNG phải `Asset Lifecycle Event`). Lifecycle event KHÔNG hash-chained ⇒ thêm lifecycle event KHÔNG ảnh hưởng chain; sửa `change_summary` của audit-row báo hỏng VẪN phải giữ chain hợp lệ. | `utils/lifecycle.py:97-114` |
| F12 | FE `IncidentCreateView.vue`: prefill `asset` từ `route.query.asset` (`:13`,`:29-30`); `SmartSelect v-model="form.asset"` (`:91`) **luôn editable, KHÔNG có :disabled**; KHÔNG đọc `route.query.source`; `reportIncident({...})` (`:54-65`) KHÔNG có field `source`. | `frontend/src/views/incident/IncidentCreateView.vue:13,29-30,54-65,91` |
| F13 | `ReportIncidentPayload` (FE type) chưa có `source`; `reportIncident(data)` POST `/report_incident`. Không có `IncidentCreateView.test.ts`. | `frontend/src/api/imm12.ts:175-189`; grep test = 0 |
| F14 | `handle()` map `frappe.PermissionError` → HTTP 403 (giống `cancel_incident` đang trả 403). `report_incident` cũng cần đi qua cùng cơ chế. | `assetcore/utils/api_handler.py` (handle/permission mapping); `api/imm12.py:92-93` precedent |

---

## Quyết định (4 quyết định — DỨT KHOÁT, mỗi quyết định 1 dòng + lý do)

### D1 — 3-tier cap-gate parity: BE `report_incident` PHẢI gate `corrective.create` với message VI sạch (đóng lỗ leo quyền P1)

**Quyết định (1 dòng):** API+svc `report_incident` PHẢI chặn `corrective.create` (CÙNG cap với route-guard FE F5 + scan-action SSoT F5) — user thiếu cap → **403** với message VI sạch **KHÔNG leak raw cap**; user có cap → **200 + Incident tạo**.

**Nơi gate (chốt):** thêm gate ở **API tier** (`api/imm12.py::report_incident`, ngay sau Guest-401, TRƯỚC `handle()`), pattern y hệt `cancel_incident` (F1) nhưng cap khác:
```python
_CAP_REPORT = "corrective.create"     # → ("Incident Report","create"), SSoT F3/F5

# trong report_incident, sau Guest-401:
if not rbac.can(_CAP_REPORT):
    return _err(_(_MSG_FORBIDDEN), 403)   # _MSG_FORBIDDEN="Không có quyền thực hiện hành động này"
```

**KHÔNG dùng `rbac.require(_CAP_REPORT)`** — vì `require` leak raw cap vào message (F4) → vi phạm AC1. Dùng `rbac.can(...)` + `_err(_MSG_FORBIDDEN, 403)` (message VI hằng số đã có sẵn `api/imm12.py:39`).

**Defense-in-depth (svc tier — tuỳ chọn, KHÔNG bắt buộc cho AC1 nhưng khuyến nghị):** nếu thêm guard ở svc thì PHẢI dùng cùng message-policy (KHÔNG leak cap). Để **đơn giản + 1 nơi chịu trách nhiệm HTTP**, AC1 chỉ YÊU CẦU gate ở **API tier** (đường HTTP duy nhất). Test parity (QA) chứng minh 3 binding CÙNG cap `corrective.create`.

**Lý do:** F1/F2 cho thấy đường HTTP `report_incident` không gate → bypass. Gate ở API tier đóng đường curl/REST (đường leo quyền thực tế). `rbac.can` (không phải `require`) để kiểm soát message (F4). Cap `corrective.create` là SSoT đã dùng ở 2 tầng kia (F5) → parity 3-tier.

**Bảng parity 3-tier (test tương đẳng — QA chứng minh CÙNG cap):**

| Tier | Vị trí | Cap | Hành vi khi thiếu cap |
|---|---|---|---|
| 1. Route-guard FE | `router/index.ts:450` `IncidentCreate` `requiredCapabilities` | `corrective.create` | redirect /unauthorized (không vào được view) |
| 2. Scan-action SSoT | `services/imm00.py:419-420` `report_failure.capability` | `corrective.create` | nút "Báo hỏng" disabled + tooltip reason |
| 3. Svc/API tier | `api/imm12.py::report_incident` (**THÊM**) | `corrective.create` | **403** VI sạch (curl/REST bypass bị chặn) |

---

### D2 — Canonical lifecycle event `incident_reported` + provenance `source` (KHÔNG dùng `failure_reported`)

**Quyết định (1 dòng):** `report_incident` thành công ⇒ ghi **`Asset Lifecycle Event` với `event_type='incident_reported'`** (canonical, đã có trong Select F8 + đã ghi doc §6 F7) — KHÔNG còn CHỈ generic `event_type='Incident'`; provenance nguồn báo hỏng ghi rõ trong `notes` (lifecycle) + `change_summary` (audit): `source='qr-scan'` → "qr-scan", `source='manual'` (mặc định) → "manual".

**Self-correction so PM-label "failure_reported":** PM đặt tên AC là `failure_reported`, NHƯNG (a) canonical option của `Asset Lifecycle Event.event_type` là **`incident_reported`** (F8 — `failure_reported` KHÔNG có trong Select → ghi sẽ throw/cần đổi schema), (b) doc §6 ĐÃ ghi `incident_reported` (F7). ⇒ **CHỐT dùng `incident_reported`** (đóng đúng intent PM "không còn chỉ generic 'Incident'" mà KHÔNG đổi schema Select). Đây là quyết định BA-gate, ghi rõ để BE/QA KHÔNG đi tìm `failure_reported`.

**`source` param (chốt enum + default):**
- Enum: `{"manual", "qr-scan"}`. **Default = `"manual"`** (mọi đường tạo cũ không truyền source ⇒ manual, NO regression).
- Thêm vào svc `report_incident(..., source: str = "manual")` (keyword-only, sau `reported_by`) + API `report_incident(..., source: str = "manual")`.
- Validate: source ∉ enum → coi như `"manual"` (KHÔNG throw — provenance không phải security gate; tránh 422 cho input lạ). *(Cần khảo sát)* nếu QA muốn strict-enum → mở rule riêng.

**Cách ghi (chốt 2 record — KHÔNG trộn 2 cơ chế):**
1. **Lifecycle event** (trục §10) — `create_lifecycle_event` (qua `imm00`/wrapper local pattern F9/F10):
   ```python
   imm00.create_lifecycle_event(
       asset=asset, event_type="incident_reported",
       actor=actor, from_status=prev_status, to_status="<asset status sau report>",
       root_doctype=_DT_INCIDENT, root_record=doc.name,
       notes=f"Báo hỏng ({_source_label(source)}) — {severity} — {incident_type}",
   )
   ```
   - `root_doctype` BẮT BUỘC kèm `root_record` (F10 — không thì event bị nuốt).
   - `_source_label(source)`: `"qr-scan"`→"qr-scan", else→"manual" (SSoT 1 hàm, KHÔNG inline literal rải rác).
2. **Audit trail** (hash-chain, GIỮ) — `_log` hiện có VẪN ghi `IMM Audit Trail`, nhưng `change_summary` THÊM provenance: `f"Incident reported ({_source_label(source)}) — {severity} — {incident_type}"`. **GIỮ hash-chain hợp lệ** (chỉ đổi nội dung text của row mới, không sửa row cũ — F11). *(Có thể nâng `event_type` của audit-row báo hỏng từ "Incident"→"incident_reported" cho khớp doc §6 — tuỳ BE, KHÔNG bắt buộc cho AC2 vì AC2 đo trên lifecycle event + chain-valid.)*

**AC2 đo (chốt rõ tiêu chí PASS):**
- ≥1 record có `event_type='incident_reported'` cho asset đó sau `report_incident` (query `Asset Lifecycle Event`).
- `notes` (lifecycle) chứa "qr-scan" khi `source='qr-scan'`; chứa "manual" khi `source='manual'`/không truyền.
- `verify_audit_chain(asset)['valid'] == True` (chain KHÔNG vỡ — F11: lifecycle không nằm trong chain, audit-row mới có hash hợp lệ).

**Lý do:** F6/F7 = drift code↔doc; F8 = `failure_reported` không hợp Select; F9/F10 = helper canonical đã sẵn (pattern IMM-09). Tách 2 record (lifecycle = trục §10 có provenance; audit = hash-chain bất biến) đúng kiến trúc — KHÔNG nhồi provenance chỉ vào 1 chỗ.

---

### D3 — FE field-lock + source propagation (qr-scan khoá asset; manual giữ editable)

**Quyết định (1 dòng):** điều hướng `/incidents/new?asset=<name>&source=qr-scan` ⇒ ô **Thiết bị prefill đúng + KHOÁ** (`SmartSelect :disabled=true`, user KHÔNG đổi được) + payload `reportIncident` chứa `source='qr-scan'`; KHÔNG có `source` (hoặc tạo thủ công từ list) ⇒ ô Thiết bị **editable như cũ** + `source='manual'` (NO regression).

**Chốt FE delta (đo được):**
- Đọc `route.query.source`: `const source = route.query.source === 'qr-scan' ? 'qr-scan' : 'manual'` (whitelist, mọi giá trị khác → manual).
- Khoá field: ô Thiết bị `<SmartSelect :disabled="lockAsset" .../>` với `lockAsset = source === 'qr-scan' && !!form.asset`. Khi khoá → hiển thị helper VI "Thiết bị đã xác định từ mã QR — không thể đổi" (chống nhầm).
   - **Điều kiện khoá:** CHỈ khoá khi `source==='qr-scan'` VÀ có `asset` từ query (deep-link hợp lệ). source=qr-scan nhưng KHÔNG có asset (lạ) → KHÔNG khoá (fallback editable, tránh user kẹt không nhập được).
- Truyền source: thêm `source` vào `ReportIncidentPayload` (FE type) + truyền `source: form.value.source` (hoặc biến `source`) trong `reportIncident({...})` (F12/F13).
- **SmartSelect phải hỗ trợ `disabled` prop** — *(Cần khảo sát)* nếu component chưa nhận `disabled` → BE-task FE thêm prop pass-through `:disabled` xuống input/native control (KHÔNG render select chết, dùng disabled thật để a11y + chặn thay đổi). Nếu component không thể disable → fallback render read-only text "<asset>" + hidden value (BA chấp nhận, miễn user KHÔNG đổi được).

**NO-regression (chốt):** đường tạo thủ công (`/incidents/new` không query, hoặc nút "Tạo" từ list) ⇒ `source='manual'`, ô Thiết bị editable y như hiện tại (F12 hành vi cũ giữ nguyên). Test FE phải có cả 2 nhánh.

**Lý do:** F12 = SmartSelect editable + không đọc source + không truyền source. Khoá field khi nguồn QR đã xác định đúng thiết bị (chống gắn nhầm asset) + truyền source để BE ghi provenance (D2). Default manual + editable giữ NO-regression.

---

### D4 — Scope-guard: chỉ đụng file của báo-hỏng-slice; KHÔNG đụng 9 file QR/asset-code + 5 file FE-button vòng 1-3; KHÔNG HARD-STOP ops

**Quyết định (1 dòng):** Vòng 4 thực thi CHỈ chạm đúng các file slice báo-hỏng dưới đây; TUYỆT ĐỐI KHÔNG đụng/khôi phục 9 file QR/asset-code + 5 file FE-button còn uncommitted từ vòng 1-3; KHÔNG git commit/push/merge/reset DB/reload gunicorn/bench restart (HARD-STOP — thuộc user).

**File trong scope (BE/FE/QA Vòng 4):**
| Tier | File | Delta |
|---|---|---|
| BE-API | `assetcore/api/imm12.py` | THÊM cap-gate `corrective.create` ở `report_incident` (D1) + truyền `source` xuống svc (D2) |
| BE-svc | `assetcore/services/imm12.py` | `report_incident(..., source="manual")` + emit `incident_reported` lifecycle event + provenance `notes`/`change_summary` (D2); helper `_source_label` |
| BE-test | `assetcore/tests/test_imm12.py` | AC1 parity (read-only→403 no-leak / create→200) + AC2 (lifecycle `incident_reported` + provenance + chain-valid) |
| FE-view | `frontend/src/views/incident/IncidentCreateView.vue` | đọc `route.query.source`; khoá SmartSelect khi qr-scan; truyền `source` (D3) |
| FE-api | `frontend/src/api/imm12.ts` | `ReportIncidentPayload` +`source?: 'manual'\|'qr-scan'` (D3) |
| FE-test | `frontend/src/views/incident/tests/IncidentCreateView.test.ts` (MỚI) | AC3: qr-scan→khoá+source / no-source→editable+manual |

**File CẤM đụng (uncommitted vòng 1-3):**
- 9 file QR/asset-code: `api/imm00.py`, `tests/test_imm00.py`, `types/imm00.ts`, `AssetDetailView.vue`, `AssetDetailView.overdueFlags.test.ts`, `AssetScanInfoView.vue`(+`.test.ts`), `labels.ts`(+`.test.ts`) — (nhóm SSoT-overdue / absent-vs-null / i18n status-pill).
- 5 file FE-button: `AssetCreateView.vue`(+`.test.ts`), `AssetEditView.vue`(+`.test.ts`), `AssetScanInfoView.vue` (Thao tác nhanh — D1/D2/D3 QR-scan-action) — đã DONE vòng trước.
- **KHÔNG đụng `services/imm00.py`** (scan-action SSoT) — tầng-2 đã đúng (F5). KHÔNG đụng `router/index.ts` (tầng-1 đã đúng). KHÔNG đụng `rbac.py` (cap đã auto-gen F3).

**Lý do:** giữ working-tree review-able; tránh trộn slice; tôn trọng HARD-STOP user (CLAUDE.md §0 no-commit / no-ops).

---

### D5 — G1/CR-16: wire `occurred_datetime` vào contract `ReportIncidentRequest` (báo hỏng F2 · contract-only · handler ĐÃ LIVE)

> **Bổ sung sau (2026-06-27, factory Vòng 2/5 improve).** D5 KHÔNG supersede D1–D4 — đóng drift **handler↔yaml** còn sót: handler đã nhận `occurred_datetime` nhưng OpenAPI contract chưa khai ⇒ mobile codegen không sinh field.

**Quyết định (1 dòng):** THÊM prop `occurred_datetime: { type: string }` (**KHÔNG** `format: date-time`) vào `schemas/ReportIncidentRequest.properties` trong `docs/mobile/openapi/assetcore-mobile.openapi.yaml`; `required` GIỮ EXACT 4 (`occurred_datetime` optional). Chỉ sửa **CONTRACT + guard test** — KHÔNG đụng `api/imm12.py`/`services/imm12.py` (đã wire) ⇒ KHÔNG reload gunicorn (LL-DEPLOY-07).

**FACTS @source (verify phiên này — KHÔNG phỏng đoán):**
- Handler nhận field: `api/imm12.py:83` `occurred_datetime: str = ""` → truyền svc `api/imm12.py:106`.
- Semantics svc: `services/imm12.py:350` (sig) · `:376-380` parse `get_datetime` + future-guard `nthrow(MSG.IMM12_OCCURRED_DATETIME_FUTURE)` `:378-379` · `:382` rỗng → fallback `doc.reported_at`.
- Message: `utils/messages.py:161` (catalog) + `:801` mapping → `http_status=422`, severity `warning`.
- DocType field: `incident_report.json` `occurred_datetime` (`Datetime`).

**Alternatives (loại + lý do):**
- `format: date-time` → **LOẠI**: codegen ép RFC-3339 ISO-`T`, lệch wire-format Frappe space-separated `yyyy-MM-dd HH:mm:ss` (`get_datetime` `services/imm12.py:377`) ⇒ client serialize sai / validator reject.
- Đưa `occurred_datetime` vào `required[]` → **LOẠI**: handler default `=""` (optional); ép required phá NO-regression + lệch live signature (13c đỏ).
- Thêm status-code mới cho future-guard → **LOẠI**: `422` đã declare (`Unprocessable422` §8.3 G-REQBODY); future-guard là nguồn 422 thứ-2 trên cùng path, KHÔNG status mới.

**Consequences (hệ quả + đánh đổi):**
- Mobile-dev sinh được model có `occurred_datetime` ⇒ gửi đúng "thời điểm sự cố thực sự xảy ra" (≠ thời điểm báo).
- KHÔNG path mới (43 GIỮ) · KHÔNG verb-flip (baseline `d12/d15/d17` 234/254 GIỮ) · response surface 200/401/403/404/422 BẤT BIẾN.
- Guard reverse-drift mới (TC-MOB-OAS-13g parity `inspect.signature`) ⇒ chống contract khai field handler KHÔNG nhận.
- Test count: `_EXPECTED_TEST_COUNT` 407→408 · `_GUARD_SUITE_EXPECTED[test_mobile_oas]` +1 · `_MOBILE_OAS_TOTAL` 576→577.

---

## Bàn giao Core Doc — task Vòng 4 map tới đúng 1 quyết định

> Gate code: ADR chốt → BE/FE/QA thực thi. KHÔNG đụng `.py/.vue/.ts` ở Vòng-4-PHÂN-TÍCH.

| Task | Map | Mô tả delta |
|---|---|---|
| **BE-1** | D1 | `api/imm12.py::report_incident`: `if not rbac.can("corrective.create"): return _err(_MSG_FORBIDDEN, 403)` sau Guest-401, TRƯỚC `handle`. KHÔNG `rbac.require` (leak cap). |
| **BE-2** | D2 | `services/imm12.py::report_incident(..., source="manual")`: emit `create_lifecycle_event(event_type="incident_reported", root_doctype=_DT_INCIDENT, root_record=doc.name, notes="Báo hỏng ({source_label}) …")`; `_log` `change_summary` thêm provenance. Helper `_source_label`. API truyền `source` xuống svc. |
| **FE-1** | D3 | `IncidentCreateView.vue`: đọc `route.query.source` (whitelist→manual); `lockAsset = source==='qr-scan' && !!asset`; `<SmartSelect :disabled="lockAsset">` + helper VI; truyền `source` vào `reportIncident`. |
| **FE-2** | D3 | `api/imm12.ts`: `ReportIncidentPayload.source?: 'manual'\|'qr-scan'`. |
| **QA-1** | D1 | Test parity 3-tier: user `corrective.read` không `.create` → API `report_incident` 403, message KHÔNG chứa `'corrective.create'` raw; user có `.create` → 200 + Incident tạo. Assert 3 binding (route-guard / scan-action spec / API gate) CÙNG cap `corrective.create`. |
| **QA-2** | D2 | Test sau report thành công: ≥1 `Asset Lifecycle Event` `event_type='incident_reported'`; `source='qr-scan'`→notes chứa "qr-scan", default→"manual"; `verify_audit_chain(asset)['valid']==True`. |
| **QA-3** | D3 | `IncidentCreateView.test.ts` (MỚI): `?asset=X&source=qr-scan`→SmartSelect disabled + payload `source='qr-scan'`; no-source→SmartSelect editable + `source='manual'`. |
| **BE-3 (F2)** | **D5** | **Contract-only.** `docs/mobile/openapi/assetcore-mobile.openapi.yaml`: THÊM `ReportIncidentRequest.properties.occurred_datetime` (`type:string`, KHÔNG `format`, description nêu wire-format + fallback + future→422); `required` GIỮ EXACT 4. `tests/test_mobile_oas.py`: +TC-MOB-OAS-13g (prop+type+no-format+∉required+parity `inspect.signature`), `_EXPECTED_TEST_COUNT` 407→408. `tests/test_mobile_docset.py`: `_GUARD_SUITE_EXPECTED[test_mobile_oas]` +1 & `_MOBILE_OAS_TOTAL` 576→577. KHÔNG đụng `api/imm12.py`/`services/imm12.py` (đã LIVE) ⇒ KHÔNG reload; verify bằng `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` + `test_mobile_docset`, KHÔNG curl-live (LL-DEPLOY-07). |

---

## Tham chiếu chéo

- API: `assetcore/api/imm12.py::report_incident`
- Service: `assetcore/services/imm12.py::report_incident` / `_log`
- RBAC SSoT: `assetcore/services/shared/rbac.py` (`CAPABILITY_MAP["corrective.create"]`, `can`/`require`)
- Lifecycle/audit helper: `assetcore/utils/lifecycle.py` (`create_lifecycle_event`, `log_audit_event`, `verify_audit_chain`); `assetcore/services/imm00.py:82` (expose)
- Pattern mirror: `assetcore/services/imm09.py:493-514` (`_log_lifecycle_event` wrapper, root_doctype rule)
- Scan-action SSoT (tầng-2 — KHÔNG đụng): `assetcore/services/imm00.py:419-420`
- Route-guard (tầng-1 — KHÔNG đụng): `frontend/src/router/index.ts:450`
- FE: `frontend/src/views/incident/IncidentCreateView.vue`, `frontend/src/api/imm12.ts`
- Lifecycle event Select options: `assetcore/assetcore/doctype/asset_lifecycle_event/asset_lifecycle_event.json` (field `event_type`)
- Core Doc: `docs/imm-12/04_Backend_Design.md` (§6 audit, §5 API), `05_API_Specification.md` (§2 endpoint 1), `06_Frontend_Design.md`, `07_Testing_QA.md`
- ADR liên quan: `docs/imm-00/ADR-IMM00-QR-SCAN-ACTION.md`, `docs/imm-00/ADR-IMM00-ASSETCODE.md`
