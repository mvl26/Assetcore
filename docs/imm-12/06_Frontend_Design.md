# 06 — Frontend Design

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phạm vi | Per-module |
| Owner | FE Lead |
| Cập nhật | 2026-05-18 |
| Trạng thái | ✅ Live — Vue components + store + 14 endpoint API đã build |

---

## 1. Sitemap

Routes and component names are based on **actual Vue files** in `frontend/src/views/incident/`.

> Path prefix thực tế = `/incidents/...` (xem `frontend/src/router/index.ts`). Module key `imm12` được map qua regex `/^\/incidents/` → `imm12` cho sidebar.

| Route (actual) | Vue Component (actual filename) | Role Guard | Status |
|---|---|---|---|
| `/incidents` (redirect) | → `/incidents/dashboard` | Any | ✅ Live |
| `/incidents/dashboard` | `views/incident/IMM12DashboardView.vue` | Workshop Lead, QA, Ops Manager | ✅ Live |
| `/incidents/list` | `views/incident/IncidentListView.vue` | Any | ✅ Live |
| `/incidents/new` | `views/incident/IncidentCreateView.vue` | Reporting User, Workshop Lead | ✅ Live |
| `/incidents/:id` | `views/incident/IncidentDetailView.vue` | Any (actions per role) | ✅ Live |
| `/rca` | `views/incident/RCAListView.vue` | Workshop Lead, QA Officer, Compliance Manager | 🆕 3b (mockup `docs/fe/12-incident/rca-list.html`) |
| `/rca/:id` | `views/incident/RCADetailView.vue` | Workshop Lead, QA Officer | ✅ Live |
| `/capa` | `views/incident/CAPAListView.vue` | Any | ✅ Live |
| `/capa/:id` | `views/incident/CAPADetailView.vue` | Any (close: QA Officer only) | ✅ Live |

**Sidebar nav config (`frontend/src/constants/modules.ts`):**
```typescript
{
  id: 'imm12', code: 'IMM-12',
  label: 'Bảo trì khắc phục',
  description: 'Triage sự cố, escalation, RCA, SLA corrective',
  icon: 'shield',
  to: '/incidents/dashboard',
  roles: [...TECH_ROLES, Roles.CLINICAL, Roles.QA, Roles.DEPT_HEAD, Roles.DEPT_DEPUTY],
}
```

---

## 2. Mockups

### 2.1 Incident List (`/incidents/list`)

```text
┌─────────────────────────────────────────────────────────────────┐
│  SỰ CỐ THIẾT BỊ                              [+ Báo cáo sự cố] │
│                                                                  │
│  Severity [All ▼]  Status [Open+InProg ▼]  Asset [...]  [Clear] │
│  ─────────────────────────────────────────────────────────────  │
│  IR Code         Asset               Severity   Status   Aged   │
│  ─────────────────────────────────────────────────────────────  │
│  IR-2026-0042   Máy thở Drager E.  🔴 Critical  In Prog  3h    │
│  IR-2026-0041   Siêu âm GE Vivid   🟠 High      Open     1h    │
│  IR-2026-0040   ECG cấp cứu        🟡 Medium    Resolved  1d   │
│  ─────────────────────────────────────────────────────────────  │
│  67 records                                  [← 1 2 3 4 →]     │
└─────────────────────────────────────────────────────────────────┘
```

**API:** `list_incidents` · **State:** `useImm12Store.incidents` · **Filter defaults:** `status in [Open, Acknowledged, In Progress]` (actual states từ `services/imm12.py`: Open / Acknowledged / In Progress / Resolved / RCA Required / Closed / Cancelled)

#### 2.1.a Workflow stepper + action buttons (D3 — SINGLE SOURCE cho FE)

State machine BE thật (khớp `imm_12_incident_workflow.json` + `_VALID_TRANSITIONS`). Stepper detail render 6 node tuyến chính; `RCA Required` là nhánh; `Cancelled` là terminal phụ.

`Open → Acknowledged → In Progress → Resolved → Closed` (+ `Resolved → RCA Required → Closed`)

| Status hiện tại | Nút hiển thị (label VN) | Action API | Transition | Role allowed |
|---|---|---|---|---|
| Open | "Tiếp nhận" | `acknowledge_incident` | Open → **Acknowledged** | Corrective Manager |
| Open | "Hủy sự cố" | `cancel_incident` | Open → Cancelled | System Manager |
| Acknowledged | "Bắt đầu xử lý" | `start_work` | Acknowledged → **In Progress** | Corrective User |
| Acknowledged | "Hủy sự cố" | `cancel_incident` | Acknowledged → Cancelled | System Manager |
| In Progress | "Đánh dấu đã giải quyết" | `resolve_incident` | In Progress → Resolved | Corrective User |
| In Progress | "Hủy sự cố" | `cancel_incident` | In Progress → Cancelled | System Manager |
| Resolved | **"Yêu cầu phân tích RCA"** | **`request_rca`** | **Resolved → RCA Required** | **Compliance Manager / AssetCore Super Admin (cap `compliance.submit`)** |
| Resolved | "Đóng sự cố" | `close_incident` | Resolved → Closed | System Manager / Workshop Lead / QA Officer |
| Resolved | **"Mở lại điều tra"** | **`reopen_incident`** | **Resolved → In Progress** | **System Manager / AssetCore Super Admin (cap `incident.close`)** |
| RCA Required | "Mở RCA" (link) → đóng sau khi RCA Completed | `close_incident` (gated BR-12-02) | RCA Required → Closed | System Manager |

> **D3 chốt (Self-Correction BE):** `acknowledge_incident()` PHẢI set `Open → Acknowledged` (KHÔNG nhảy thẳng In Progress). Thêm action `start_work()` cho `Acknowledged → In Progress`. FE stepper align mô hình 2 bước này. Đây là root-cause fix, KHÔNG vá ở FE.
> BR-12-02: High/Critical hoặc Chronic → nút "Đóng sự cố" ở RCA Required bị block đến khi RCA `Completed`.
>
> **BR-12-23 (Round 12, CR-WF-12) — nút "Mở lại điều tra":** SSoT = `allowed_transitions` (server-driven, GATE-8/LL-FE-51). Gate `canReopen = can('incident.close') && form.status === 'Resolved' && allowed_transitions.includes('In Progress')` — **KHÔNG hardcode role-name**, đọc `allowed_transitions` từ `get_incident_detail` (nay chứa `'In Progress'` khi Resolved sau fix drift a). Bấm → modal nhập `reason` (bắt buộc) → `reopenIncident({name, reason})` (POST envelope Decision-B, parity `closeIncident`) → `invalidateQueries(imm12Keys.detail(name))`. API client mới `reopenIncident` trong `api/imm12.ts`. *Never*: render nút theo `status===` literal hoặc role-name; *Always*: đọc `allowed_transitions`, disable khi thiếu cap.
>
> **BR-12-24 (Round 38, CR-WF-12-RCA-ENTRY) — nút "Yêu cầu phân tích RCA":** SSoT = `allowed_transitions` (server-driven, GATE-8/LL-FE-51 — đối xứng "Mở lại điều tra"). Gate `canRequestRca = can('compliance.submit') && form.status === 'Resolved' && allowed_transitions.includes('RCA Required')` — **KHÔNG hardcode `status===` literal, KHÔNG hardcode role-name**. `allowed_transitions[Resolved]` vốn đã chứa `'RCA Required'` (từ Round 12) — round này bổ driver THẬT (nút + endpoint) cho advertise "câm" đó (đóng hidden-CTA). `can('compliance.submit')` đọc từ cap-map auth store (`compliance.submit` ∈ `CAPABILITY_MAP` auto-gen). Đặt nút "Yêu cầu phân tích RCA" trong cụm workflow-actions (cạnh "Đánh giá đã giải quyết"/"Mở lại điều tra"), gate `v-if="canRequestRca"`. Bấm → modal nhập `rca_reason` (bắt buộc — nút xác nhận `:disabled` khi `!rca_reason.trim()`, KHÔNG gọi endpoint) → `requestRca(name, rca_reason)` (POST envelope Decision-B, parity `reopenIncident`) → `await load()`/`invalidateQueries(imm12Keys.detail(name))` refetch. **Sau refetch:** `status` → `'RCA Required'` ⇒ badge "Cần phân tích RCA" cập nhật + stepper hiện nhánh `RCA Required` (đã render `v-if="form.status === 'RCA Required'"`) + section RCA hiện RCA Record vừa link. API client mới `requestRca(name, rca_reason)` trong `api/imm12.ts` (`POST ${BASE}.request_rca`). *Never*: render theo `status===`/role-name; *Always*: `allowed_transitions` + `can(cap)`, disable khi thiếu cap. **KHÁC nút "Tạo phân tích nguyên nhân gốc"** (`doCreateRca`/`createRca`, gate `needsRca`=rca_required∧!rca_record, cho KTV): `request_rca` là hành động governance đổi status Incident, `create_rca` chỉ tạo record RCA.

#### 2.1.a Server-driven CTA — render 6 nút vòng đời từ `available_actions[]` (CR-39, GATE-8/LL-FE-51) 🟡 SPEC (FE Bước-4)

**Vấn đề:** `IncidentDetailView.vue` hiện gate 6 nút vòng đời bằng **predicate-mirror** (hardcode `status===X`, `can(cap)`, tự suy BR-12-02) → FE tính khác BE ⇒ nút hiện nhưng bấm ra **403/422 sau khi bấm** (advertise≠enforce) + drift khi BE đổi cap/transition. Fix theo GATE-8/LL-FE-51: **render CTA từ `available_actions[]` do BE trả** (`get_incident_detail`, `05 §18`) — mỗi phần tử đã có `enabled`+`reason`, FE **chỉ render**, KHÔNG tự suy.

- **Nguồn:** `available_actions` (6 phần tử `{key, label, enabled, reason}`, thứ tự cố định `[acknowledge, start_work, resolve, close, reopen, cancel]`) từ payload `getIncident`. Type `IncidentDetail` += `available_actions?: AvailableAction[]`.
- **Render:** map `available_actions` → nút; `label` = nhãn BE (KHÔNG hardcode chuỗi VI ở FE); `:disabled="!action.enabled"`; khi disabled hiển thị `action.reason` (tooltip/inline) — **không** dead-button không lý do. Bấm nút `enabled` → gọi endpoint tương ứng theo `key` (`acknowledge_incident`/`start_work`/`resolve_incident`/`close_incident`/`reopen_incident`/`cancel_incident`; các nút cần `reason`/notes → mở modal như hiện tại) → `invalidateQueries(imm12Keys.detail(name))` refetch.
- **Boundaries** — *Never*: gate nút bằng `status===X` literal / role-name / tự suy BR-12-02 ở FE (predicate-mirror — nguồn lỗi 403-sau-khi-bấm); hardcode nhãn VI (dùng `label` BE). *Always*: đọc `available_actions` server-driven; disable + show `reason` khi `!enabled`; refetch sau action. **Fallback** payload cũ chưa có `available_actions` (transition): giữ gate `allowed_transitions`+`can(cap)` hiện có (đọc `available_actions ?? <gate cũ>`) — KHÔNG vỡ khi BE Bước-4 chưa deploy.
- **Quan hệ với CTA khác:** "Tạo phân tích nguyên nhân gốc" (`createRca`, gate `needsRca`) + "Yêu cầu phân tích RCA" (`requestRca`, BR-12-24) + RCA CTA (`get_rca.allowed_transitions`/`can_manage_rca`, §2.4.a) **KHÔNG** thuộc 6 CTA vòng đời incident — giữ nguyên. `available_actions` chỉ thay predicate-mirror của **6 nút vòng đời chính**.
- **Test (Bước-4):** `frontend/src/views/incident/incidentActionCtaGating.test.ts` — mount combo `(status, available_actions)` assert nút enabled/disabled + reason render đúng + không nút ngoài 6 key + `label` từ payload (KHÔNG hardcode). `vue-tsc` sạch.

### 2.2 New Incident Form (`/incidents/list/new`)

```text
┌─────────────────────────────────────────────────────────────────┐
│  BÁO CÁO SỰ CỐ THIẾT BỊ                          [Hủy] [Gửi]  │
│                                                                  │
│  Section 1: Thiết bị                                            │
│  Thiết bị *          [Search AC Asset ▼]  (KHOÁ nếu source=qr-scan) │
│  Khoa phòng          [Auto-fill from Asset]                     │
│                                                                  │
│  Section 2: Mô tả sự cố                                         │
│  Mã lỗi *            [Select fault_code ▼]                      │
│  Mức độ *            ◉ Thấp  ○ TB  ○ Cao  ○ Nghiêm trọng        │
│  (value enum BE: Low / Medium / High / Critical — KHÔNG Minor/Major) │
│  Mô tả sự cố *       [Textarea 5 rows]                          │
│  Workaround?         ☑ Đã chuyển bệnh nhân sang thiết bị khác  │
│  Ảnh đính kèm        [Upload — drag & drop]                     │
│                                                                  │
│  Section 3: Tác động lâm sàng (hiển thị khi severity=Critical) │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ ⚠️ THIẾT BỊ HỖ TRỢ SỰ SỐNG — BẮT BUỘC ĐIỀN              │ │
│  │ Tác động lâm sàng *  [Textarea — clinical_impact]         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2.a V4-GATE — Field-lock + source propagation từ quét QR (BR-12-16, D3) ✅ CHỐT

> **ADR:** `ADR-IMM12-REPORT-FAILURE.md` D3. **Gap (verify tại source):** `IncidentCreateView.vue` prefill `?asset` đúng (`:13`,`:29-30`) NHƯNG `SmartSelect` (`:91`) **luôn editable**; KHÔNG đọc `route.query.source`; `reportIncident({...})` (`:54-65`) KHÔNG có `source`.

**CHỐT FE delta (đo được):**
1. **Đọc source (whitelist):** `const source = route.query.source === 'qr-scan' ? 'qr-scan' : 'manual'` (mọi giá trị khác → `manual`).
2. **Khoá field Thiết bị:** `lockAsset = source === 'qr-scan' && !!form.asset` → `<SmartSelect v-model="form.asset" :disabled="lockAsset" />`. Khi khoá → helper VI dưới ô: *"Thiết bị đã xác định từ mã QR — không thể đổi"*.
   - CHỈ khoá khi `source==='qr-scan'` **VÀ** có `asset` từ query. source=qr-scan nhưng KHÔNG có asset (lạ) → **KHÔNG khoá** (fallback editable, tránh user kẹt).
3. **Truyền source:** thêm `source` vào `ReportIncidentPayload` (`api/imm12.ts`: `source?: 'manual'|'qr-scan'`) + `reportIncident({ ..., source })`.
4. **SmartSelect `disabled` prop:** *(Cần khảo sát)* nếu `SmartSelect.vue` chưa nhận `disabled` → FE task thêm pass-through `:disabled` xuống control (disabled THẬT cho a11y + chặn đổi). Không disable được → fallback render read-only text + hidden value (miễn user KHÔNG đổi được).

**NO-regression:** `/incidents/new` không query (hoặc nút "Tạo" từ list) ⇒ `source='manual'`, ô Thiết bị **editable y như hiện tại**. Test FE 2 nhánh (qr-scan→khoá+source / no-source→editable+manual).

**Luồng deep-link (D3 ↔ ADR-IMM00-QR-SCAN-ACTION D3):** màn quét QR → nút "Báo hỏng" → `router.push({name:'IncidentCreate', query:{asset:<name>, source:'qr-scan'}})` → view này khoá asset + gắn source. `<name>`=`asset_code` (invariant `asset_code==name`). KHÔNG truyền raw `qr_token`.

### 2.3 Incident Detail (`/incidents/list/:name`)

```text
┌─────────────────────────────────────────────────────────────────┐
│  IR-2026-0042              ● RCA REQUIRED        [Actions ▼]    │
│  Máy thở Drager Evita 800 — ICU               🔴 CRITICAL       │
│                                                                  │
│  Tabs: [Thông tin] [Timeline] [Repair WO] [RCA] [CAPA]          │
│  ─────────────────────────────────────────────────────────────  │
│  Tab: Thông tin                                                  │
│    Asset: ACC-ASSET-2026-0012                                   │
│    Mã lỗi: VENT_ALARM_HIGH                                      │
│    Báo cáo bởi: nurse1@hospital.vn — 08:12 18/04/2026          │
│    Tiếp nhận: workshop_lead@hospital.vn — 08:35 18/04/2026     │
│    KTV phụ trách: ktv.nguyen@hospital.vn                        │
│    Tác động: "Bệnh nhân phụ thuộc, đã chuẩn bị bóng ambu"      │
│                                                                  │
│  Actions (Workshop Lead, status=RCA Required):                  │
│    [Mở RCA-2026-0012]                                           │
│                                                                  │
│  Tab: Timeline (IncidentTimeline component)                     │
│    08:12 Open    | nurse1     | Incident created                │
│    08:35 Ack.    | wl.lead    | Assigned to KTV Nguyễn          │
│    11:45 Resolved| wl.lead    | Sensor replaced + calibrate     │
│    11:46 RCA Req | System     | Auto-triggered (Critical)       │
│    12:03 Ảnh     | ktv.nguyen | Đính ảnh bằng chứng: scene.jpg  │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3.a Ảnh bằng chứng hiện trường (`scene_photos`) — BR-12-17/18 🟡 SPEC

```text
│  ─── Ảnh hiện trường (bằng chứng NĐ98)  3/5 ─────────────────── │
│   [🖼 scene_a][🖼 scene_b][🖼 scene_c]        [+ Đính ảnh]      │
```
- **Nguồn:** `get_incident_detail(name).scene_photos: [{file_url, file_name}]` (`[]` khi rỗng → hiện empty-state "Chưa có ảnh bằng chứng"). Ảnh là **private** → render qua endpoint file-serve có phiên (KHÔNG hot-link public).
- **Nút "Đính ảnh"** = `<input type=file accept="image/jpeg,image/png">` → `POST attach_incident_photo` (multipart `file` + `incident_name`) → success `{file_url, file_name}` → invalidate query detail → gallery +1. **Ẩn/disable nút** khi `scene_photos.length >= 5` (tooltip "Tối đa 5 ảnh") + khi user KHÔNG phải reporter và KHÔNG có `incident.write` (gate theo capability, KHÔNG hardcode role-name — anti dead-gate).
- **Feedback lỗi (Decision-B):** `code=VALIDATION` → toast + gắn `fields.file` dưới input (vd "Tệp phải là ảnh JPG hoặc PNG", "Tối đa 5 ảnh"); `code=FORBIDDEN` → toast "Không có quyền thực hiện hành động này". KHÔNG blank màn.
- **Parity mobile:** cùng `scene_photos` + cùng endpoint `attach_incident_photo` (mobile `IncidentDetailView` gallery + máy ảnh) — web KHÔNG rò field web-only khác.

#### 2.3.b Tình trạng SLA (`is_*_breached` derived — server-flag) — BR-12-13 / mobile CR-21 🟡 SPEC

```text
│  ─── Tình trạng SLA ──────────────────────────────────────────  │
│    Phản hồi:  [Trong hạn]                                        │
│    Xử lý:     [⚠ Vi phạm SLA xử lý]   (badge đỏ, cùng list)     │
```
- **Nguồn (SoT server-flag):** `get_incident_detail(name)` trả `is_response_breached` / `is_resolution_breached` (int 0|1, derive LIVE — `05 §17`). FE đọc **`form.is_response_breached ?? form.response_breached`** và **`form.is_resolution_breached ?? form.resolution_breached`** (ưu tiên derived; fallback cờ thô cho payload transition). **TUYỆT ĐỐI KHÔNG so ngày client-clock** — KHÔNG `Date.now()` / `new Date(due_at)` compare (memory `overdue_server_flag_ssot`: overdue là server-flag, FE chỉ render).
- **2 dòng:** `Phản hồi` (response) + `Xử lý` (resolution). Mỗi dòng:
  - cờ **truthy** (=1) → badge **"Vi phạm SLA tiếp nhận" / "Vi phạm SLA xử lý"** — **TÁI DÙNG `SlaBreachBadge`** (cùng component + cùng SSoT `SLA_BREACH_LABEL`/`SLA_BREACH_BADGE_CLASS` như `IncidentListView.vue:279-280`), badge chỉ render loại đang breach.
  - cờ **falsy** (=0) → pill trung tính **"Trong hạn"** (SSoT label mới, vd `SLA_OK_LABEL = 'Trong hạn'` trong `constants/labels.ts`; class xám `bg-slate-100 text-slate-600`). `SlaBreachBadge` hiện tại KHÔNG render khi cờ=0 → để hiện "Trong hạn" cho từng dòng, FE **hoặc** thêm prop tùy chọn `always`+`okLabel` vào `SlaBreachBadge` (render "Trong hạn" khi cờ falsy) **hoặc** wrap: `<SlaBreachBadge v-if="flag"/>` else pill "Trong hạn". **Không đổi hành vi mặc định** của `SlaBreachBadge` ở list (props tên giữ nguyên, mặc định vẫn ẩn khi cờ=0).
- **KHÔNG leak** chuỗi BE thô (`is_*_breached`/`response_breached`/`breached`) ra DOM — chỉ nhãn VI qua SSoT (anti-leak `wave2_ui_bugs`).
- **Parity mobile (CR-21):** mobile `IncidentDetailView` hiện cùng 2 dòng, đọc cùng 2 derived flags — web KHÔNG rò field web-only khác.

#### 2.3.c Thông tin xử lý (tên người, KHÔNG email thô) + trạng thái thiết bị LIVE — CR-40 🟡 SPEC (FE Bước-4)

```text
│  ─── Thông tin xử lý ─────────────────────────────────────────  │
│    Người báo hỏng:  Bs. Nguyễn Văn A        (KHÔNG bs.nguyen@…) │
│    Người xử lý:     KTV Trần Thị B                              │
│    Trạng thái thiết bị:  [● Ngừng vận hành]  (badge, LIVE)      │
```
- **Nguồn (SoT server-enrich):** `get_incident_detail(name)` trả `reporter_name`/`assigned_to_name` (`User.full_name`) + `asset_lifecycle_status` (`AC Asset.lifecycle_status` LIVE) — `05 §19`.
- **Hết rò email thô (U7/UI-FIX-05):** panel "Thông tin xử lý" đọc **`form.reporter_name ?? form.reported_by`** và **`form.assigned_to_name ?? form.assigned_to`** (ưu tiên tên; fallback id CHỈ cho payload cũ chưa enrich / user thiếu full_name). **TUYỆT ĐỐI KHÔNG** render thẳng `reported_by`/`assigned_to` (email/user-id thô) khi đã có tên. Cùng họ lỗ rò raw-email của transfer panel (Open thread §🔥 approval-inbox P2 FE) — audit các panel approval-processing khác cho cùng lỗi.
- **Trạng thái thiết bị LIVE (U1):** badge đọc `form.asset_lifecycle_status` → nhãn VI qua **SSoT enum lifecycle** (KHÔNG hardcode; dịch `Out of Service`→"Ngừng vận hành", `Active`→"Đang vận hành"… — memory `ui_copy_language_policy`). Mục tiêu: KTV rút máy khỏi vận hành THẤY ngay máy đã bị khoá (acknowledge High/Critical đẩy `Out of Service`, BR-12-04). `asset_lifecycle_status` rỗng/null (phiếu no-asset) → **ẩn dòng** (KHÔNG render badge trống).
- **KHÔNG leak** chuỗi BE thô (`asset_lifecycle_status` mã canonical, `reported_by` email) ra DOM — chỉ nhãn VI qua SSoT (anti-leak `wave2_ui_bugs` + `ui_copy_language_policy`). **KHÔNG** so ngày / client-clock (field là snapshot server-flag, FE chỉ render).
- **Parity mobile (CR-40):** mobile `IncidentDetailView` hiện cùng 3 giá trị, đọc cùng 3 field enrich — web KHÔNG rò field web-only khác.

### 2.4 RCA Form (`/rca/:id`)

```text
┌─────────────────────────────────────────────────────────────────┐
│  RCA-2026-0012           ● RCA IN PROGRESS     [Submit RCA →]   │
│  Asset: Máy thở Drager Evita 800 — Trigger: Critical Incident   │
│  Hạn: 25/04/2026 (còn 7 ngày)                                   │
│                                                                  │
│  Phương pháp *   ◉ 5-Why   ○ Fishbone   ○ Other                 │
│                                                                  │
│  ─── RCAFiveWhyEditor component ──────────────────────────────  │
│  Why 1: Tại sao alarm P_HIGH?  → [Sensor sai số]               │
│  Why 2: Tại sao sensor sai số? → [Drift do nhiệt độ]            │
│  Why 3: Tại sao nhiệt độ cao?  → [HVAC không ổn định]           │
│  Why 4: Tại sao HVAC không ổn? → [Maintenance HVAC trễ]         │
│  Why 5: Tại sao maintenance trễ? → [Không có schedule trong CMMS│
│  ──────────────────────────────────────────────────────────────  │
│  Nguyên nhân gốc *  [Sensor degraded do nhiệt độ ICU vượt 28°C] │
│  Yếu tố đóng góp    [HVAC không ổn định 3 tháng qua]            │
│  Corrective         [Thay sensor + calibrate]                   │
│  Preventive         [PM HVAC tích hợp vào CMMS, 1 tháng/lần]   │
│                                                                  │
│  ⓘ Submit sẽ tự động tạo CAPA Record qua imm00.create_capa()    │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.4.a Server-driven CTA — gỡ dead-gate hardcode `rca.status===` (GATE-8 / LL-FE-51, BR-12-19) 🆕 SPEC

`RCADetailView.vue` hiện gate action bằng `isCompleted = rca.status === 'Completed'` (`:43`) và chỉ có 1 nút "Hoàn thành RCA" (`v-if="!isCompleted"`) → cho phép submit thẳng từ `RCA Required` (nhảy-cóc, BUG BR-12-21) và KHÔNG có nút "Bắt đầu phân tích"/"Hủy RCA". Sửa theo GATE-8/LL-FE-51: **render CTA từ `allowed_transitions` + `can_manage_rca` do BE trả (`get_rca`), status CHỈ dùng cho badge**.

**Ma trận nút (điều kiện = `can_manage_rca === 1 && đích ∈ allowed_transitions`):**

| Nút | Đích | Action | Hiện khi status |
|---|---|---|---|
| **Bắt đầu phân tích RCA** | `RCA In Progress` | `startRca({name})` | `RCA Required` |
| **Hoàn thành RCA** | `Completed` | `submitRca({...})` | `RCA In Progress` |
| **Hủy RCA** | `Cancelled` | `cancelRca({name, reason})` | `RCA Required` \| `RCA In Progress` |
| _(không nút)_ | — | — | `Completed` \| `Cancelled` (`allowed_transitions=[]`) |

- **Boundaries** — *Never*: gate nút bằng `rca.status === 'X'` literal; gate bằng role-name; so ngày client-clock. *Always*: đọc `allowed_transitions`/`can_manage_rca` từ payload `get_rca`; nút disabled khi `can_manage_rca===0`; sau mỗi action `invalidateQueries(imm12Keys.rcaDetail(name))` để re-fetch allowed_transitions mới.
- **Editability form** (5-Why + root_cause + corrective/preventive): editable khi `can_manage_rca && allowed_transitions.includes('Completed')` (⟺ status = `RCA In Progress` — phái sinh từ SERVER, KHÔNG hardcode `=== 'Completed'`). `Completed`/`Cancelled` → read-only.
- **Nhãn trạng thái** (badge): dùng `rcaStatusLabel(rca.status)` (`constants/labels.ts:437-440` — `RCA Required→'Cần phân tích'`, `RCA In Progress→'Đang phân tích'`, `Completed→'Đã hoàn tất'`, `Cancelled→'Đã hủy'`). ĐÃ có full VI, KHÔNG lộ mã state thô (AC6).
- **API client mới** trong `api/imm12.ts`: `startRca(payload:{name})`, `cancelRca(payload:{name,reason})` — POST envelope Decision-B (parity `submitRca`). Type `RCADetail` += `allowed_transitions?: string[]` (đã có `:43`) + `can_manage_rca?: number`.
- **Test** (AC7): `frontend/src/views/incident/tests/RCADetailView.ctaGating.test.ts` — mount với các combo `(status, allowed_transitions, can_manage_rca)` assert đúng nút hiện/ẩn + không nút khi terminal + `can_manage_rca=0` disable. `vue-tsc` sạch.

---

## 3. Components

> Views implemented: `IncidentListView.vue`, `IncidentCreateView.vue`, `IncidentDetailView.vue`, `RCADetailView.vue`, `CAPAListView.vue`, `CAPADetailView.vue`, `IMM12DashboardView.vue`.

| Component | Props | Mô tả |
|---|---|---|
| `SeverityBadge.vue` | `severity: "Low"\|"Medium"\|"High"\|"Critical"` | Color badge với icon (DocType `Incident Report.severity` có 4 mức Low/Medium/High/Critical) |
| `IncidentStatusBadge.vue` | `status: string` | Actual states: Open / Acknowledged / In Progress / Resolved / RCA Required / Closed / Cancelled |
| `CAPAStatusBadge.vue` | `status: string` | CAPA status badge |
| `RCAFiveWhyEditor.vue` | `modelValue: FiveWhyStep[]` | Steps use `{why_number, why_question, why_answer}` (actual field names) |
| `CAPACloseDialog.vue` | `capaName: string`, `@close` | Modal close CAPA |
| `IncidentTimeline.vue` | `incidentName: string` | Audit trail timeline |
| `ClinicalImpactWarning.vue` | `severity: string` | Banner for Critical severity |
| `SlaBreachBadge.vue` (BR-12-09; binding-source ĐỔI ở BR-12-13) | `responseBreached?: 0\|1`, `resolutionBreached?: 0\|1` | Badge đỏ "Vi phạm SLA". Component KHÔNG đổi (props giữ tên). **Parent ĐỔI nguồn**: bind field **derived LIVE** `ir.is_response_breached`/`ir.is_resolution_breached` thay cờ thô `response_breached`/`resolution_breached` (BR-12-13 — badge hiện ngay khi quá hạn, KHÔNG đợi scheduler). Render 1 badge / 1 loại =1; không loại nào → render gì cả (`v-if`). Nhãn tiếng Việt qua SSoT, KHÔNG leak "breached"/English. |

### 3.1 SLA breach badge — i18n SSoT (BR-12-09) + binding LIVE (BR-12-13)

> **Anti-leak (memory wave2_ui_bugs / formatters SSoT):** KHÔNG hiển thị chuỗi BE thô `response_breached`/`resolution_breached`/`is_*_breached`/`breached`. Thêm SSoT vào `frontend/src/constants/labels.ts` (KHÔNG hardcode trong component):

```typescript
// labels.ts — SLA breach (IMM-12). Nhãn KPI giữ VI 'Vi phạm SLA tiếp nhận/xử lý'.
export const SLA_BREACH_LABEL = {
  response:   'Vi phạm SLA tiếp nhận',
  resolution: 'Vi phạm SLA xử lý',
} as const
export const SLA_BREACH_BADGE_CLASS = 'bg-red-100 text-red-700 ring-1 ring-red-200'
```

**Nơi hiển thị (cả 2 — verify count khớp tile, không divergence):**
- `IncidentListView.vue` — chip/badge cạnh severity (`:279-280` mobile + `:347-348` desktop): bind **derived** `:response-breached="ir.is_response_breached"` + `:resolution-breached="ir.is_resolution_breached"` (ĐỔI từ cờ thô `ir.response_breached`/`ir.resolution_breached` — BR-12-13). `v-if` wrapper (`:342`) cũng đổi sang `ir.is_response_breached || ir.is_resolution_breached`. BE `list_incidents` trả 2 field derived (xem `05_API DELTA`).
- `IMM12DashboardView.vue` — 2 stat card đọc `store.dashboard.stats.sla_response_breached` / `sla_resolution_breached` (nhãn "Vi phạm SLA tiếp nhận" / "Vi phạm SLA xử lý") — KPI giá trị nay là LIVE count (BR-12-13, BE-driven, binding KHÔNG đổi). Badge trong panel `active_incidents` (`:165` v-if + `:170-171`) cũng đổi sang `ir.is_response_breached`/`ir.is_resolution_breached`.
- `IncidentDetailView.vue` — section **"Tình trạng SLA"** (2 dòng Phản hồi/Xử lý), đọc `form.is_response_breached ?? form.response_breached` + `form.is_resolution_breached ?? form.resolution_breached` (server-flag, KHÔNG client-clock — BR-12-13 / mobile CR-21, xem `§2.3.b`). Reuse `SlaBreachBadge` cho nhánh breach; pill "Trong hạn" cho nhánh còn hạn.

**Divergence guard (FE test, BR-12-13):** số trên 2 stat card == số row có badge tương ứng trong list/active_incidents (cùng nguồn LIVE: tile = `sla_breach_count`, badge = `is_*_breached`, cùng predicate BE). **INV-SLA-5:** dựng row có `is_resolution_breached=1` nhưng `resolution_breached=0` (cờ thô) ⇒ badge VẪN hiện (đọc derived, KHÔNG cờ thô) — RED-prove: revert binding về cờ thô ⇒ badge ẩn ⇒ FAIL. Vitest assert label render từ `SLA_BREACH_LABEL` (KHÔNG chứa substring "breach"/"breached" tiếng Anh trong DOM). `vue-tsc` xanh.

### 2.5 Card "Đang mở" — SoT open-set + drill (BR-12-11) — DELTA vòng 21

`IMM12DashboardView.vue` card đầu tiên (hiện bind `stats.open` + nhãn 'Mới mở' + bare `/incidents/list`) PHẢI đổi để khớp SoT BE `open_incident_filter()`:

| Thuộc tính | TRƯỚC (sai) | SAU (BR-12-11) |
|---|---|---|
| Binding count | `stats.open ?? 0` | `stats.open_total ?? 0` (count cả Acknowledged + RCA Required, không chỉ Open) |
| Nhãn card | literal `'Mới mở'` | `INCIDENT_OPEN_FILTER_LABEL` (= 'Đang mở', SSoT `constants/labels.ts:327` round-18) — KHÔNG hardcode literal mới |
| Drill `@click` | `router.push('/incidents/list')` | `router.push('/incidents/list?open=1')` (hoặc object `{ path:'/incidents/list', query:{ open:'1' } }`) |
| "Xem tất cả" của "Sự cố đang xử lý" | `router.push('/incidents/list')` | `router.push('/incidents/list?open=1')` |

**Invariant (FE test BẮT BUỘC):** card count (`stats.open_total`) == số dòng list sau khi drill `/incidents/list?open=1` (list loại Closed/Cancelled/Resolved). Vì `active_incidents` BE đã dùng cùng `open_incident_filter()`, số dòng "Sự cố đang xử lý" (≤10) cũng phản ánh đúng open-set.

**Phân biệt 2 khái niệm nhãn (KHÔNG nhầm):**
- `incidentStatusLabel('Open')` = 'Mới mở' — nhãn **trạng thái từng-state** (giữ nguyên, dùng cho badge per-row + WorkflowStepper). KHÔNG đổi.
- `INCIDENT_OPEN_FILTER_LABEL` = 'Đang mở' — nhãn **filter ảo open-set** (card open_total + chip drill). Đây là cái card "Đang mở" dùng.

**Type delta (`api/imm12.ts`):** thêm `open_total: number` vào cả `interface IncidentStats` (line 75) và `interface DashboardStats` (line 229) — khớp BE service `get_incident_stats()` trả `open_total`. Backward-compat: GIỮ `open` + `investigating` (consumer khác còn đọc).

### 2.6 KPI strip severity = open-set (BR-12-11b) — DELTA vòng 29

KPI strip `IncidentListView.vue` `kpiItems` (computed, line ~50-64) — 4 tile trên filter bar. 2 tile severity hiện bind count GLOBAL mọi-status (`stats.critical` / `stats.high`) ⇒ **mâu thuẫn thị giác strip-vs-table** khi user drill `?open=1` hoặc `?severity=High` (bảng chỉ open-set, strip vẫn đếm cả Closed/Cancelled/Resolved). Phải bind theo SoT open-set BE (`stats.critical_open` / `stats.high_open`):

| Tile | TRƯỚC (sai) | SAU (BR-12-11b) |
|---|---|---|
| 'Sự cố nghiêm trọng' | `stats.critical` (global) | binding `stats.critical_open ?? 0` (open-set); nhãn → **'Sự cố nghiêm trọng đang mở'** |
| 'Sự cố mức cao' | `stats.high` (global) | binding `stats.high_open ?? 0` (open-set); nhãn → **'Sự cố mức cao đang mở'** |
| 'Lặp lại (Chronic)' | `stats.chronic` | binding KHÔNG đổi; giá trị = LIVE nhóm (BR-12-12, §2.7), KHÔNG còn cờ stale |
| 'Đã đóng' | `stats.closed` | KHÔNG đổi |

- Strip KHÔNG còn đọc `stats.critical` / `stats.high` global (2 key đó GIỮ ở type cho donut/consumer cũ, nhưng strip không bind).
- Nhãn làm rõ ngữ nghĩa **open-set** → tránh user hiểu nhầm là tổng toàn cục. (Nếu dự án có SSoT label store, ưu tiên hằng số thay literal — nhưng strip này dùng literal cục bộ trong `kpiItems`, theo pattern hiện hữu của 4 tile.)

**Invariant (FE test BẮT BUỘC):** trên `/incidents/list?open=1` (data live: 1 Critical-open + 2 High-open trong open-set), tile 'Sự cố nghiêm trọng đang mở' == số dòng Critical trong bảng == 1; tile 'Sự cố mức cao đang mở' == số dòng High == 2. KHÔNG còn 0/0 (bug alias chết cũ) hay số global gồm Closed. Vitest assert: tile value đọc `critical_open`/`high_open`, KHÔNG `critical`/`high`.

**Type delta (`api/imm12.ts`):** thêm `critical_open?: number` + `high_open?: number` vào `interface IncidentStats` (+ `DashboardStats` cho parity vì `get_dashboard().stats == get_incident_stats()`). Optional (forward-compat, strip fallback `?? 0`). GIỮ `critical` + `high` global.

### 2.7 KPI tile "Lặp lại (Chronic)" = LIVE SoT — kill tile-vs-panel divergence (BR-12-12) — DELTA vòng 3/50

Vấn đề thiết kế gốc (Self-Correction): trên **dashboard sự cố** (`IMM12DashboardView.vue`), tile *"Lặp lại (Chronic)"* (`:106`) bind `stats.chronic ?? 0`, còn panel danh sách chronic ngay dưới (`:221-234`) render `chronicFailures` = `store.dashboard?.chronic_failures`. Hai nguồn LỆCH:

- **Tile** đọc `stats.chronic` — BE cũ đếm cờ stale `chronic_failure_flag` (số incident-rows-có-cờ, monotone, không reset khi aged-out).
- **Panel** đọc `chronic_failures` — BE `get_chronic_failures()` đếm nhóm `(asset, fault_code)` LIVE trong 90d.

⇒ **mâu thuẫn thị giác trên CÙNG 1 màn hình**: tile báo "6" (cờ tích lũy) trong khi panel chỉ liệt kê 1 nhóm live.

**Fix = BE-driven (FE binding KHÔNG đổi cấu trúc):** sau BR-12-12, BE `stats.chronic = chronic_failure_count() = len(get_chronic_failures())` ⇒ tile và panel cùng SoT. FE giữ nguyên binding `stats.chronic ?? 0` (`:106`) — chỉ **ý nghĩa giá trị** đổi (live nhóm thay vì cờ). KHÔNG cần đổi `api/imm12.ts` type (`chronic: number` đã đúng), KHÔNG đổi template binding.

| Tile | Binding | Ghi chú |
|---|---|---|
| 'Lặp lại (Chronic)' (`IMM12DashboardView.vue:106`) | `stats.chronic ?? 0` — **KHÔNG đổi binding** | giá trị giờ = số nhóm live (BR-12-12), KHÔNG còn cờ stale |
| Panel chronic (`:221-234`) | `store.dashboard?.chronic_failures` — KHÔNG đổi | nguồn `get_chronic_failures()` |

**Invariant (FE test BẮT BUỘC, ≥1 RED-proven cho tile binding):** trên 1 payload `getDashboard()` mock, `stats.chronic == chronic_failures.length` ⇒ tile render đúng số == số dòng panel. Vitest assert:
- tile text == `stats.chronic` == `dashboard.chronic_failures.length` (không drift trên cùng render).
- **RED-prove:** mock payload với `stats.chronic = 6` (giả lập BE stale cũ) nhưng `chronic_failures.length = 1` ⇒ test invariant FAIL (6 ≠ 1) ⇒ chứng minh test bắt được divergence. Với payload đúng SoT (`stats.chronic = 1`, `chronic_failures.length = 1`) ⇒ GREEN.
- (Tùy chọn) assert tile binding đọc `stats.chronic` (KHÔNG hardcode `chronic_failures.length` ở tile — tile vẫn lấy từ stats, đúng pattern; invariant đảm bảo 2 nguồn = nhau).

**Badge per-row "Lặp lại" GIỮ NGUYÊN — KHÔNG regression (`IncidentListView.vue:271/:317`):** badge bind `ir.chronic_failure_flag` per-row — đánh dấu incident *từng thuộc* cụm chronic (lifecycle riêng của cờ, BR-12-03 audit/RCA grouping). KHÔNG đổi binding, KHÔNG phụ thuộc tile. FE test no-regression: badge vẫn render cho incident có `chronic_failure_flag==1` kể cả khi tile dashboard chronic == 0 (cụm đã aged-out). Strip KPI `IncidentListView.vue::kpiItems` tile 'Lặp lại (Chronic)' (`:65`) bind `stats.chronic` cũng tự hưởng SoT live (KHÔNG đổi binding).

**Design tokens — Severity (4 mức theo DocType):**
```typescript
// tokens/severity.ts
export const severityTokens = {
  Low:      { bg: "bg-slate-50",   border: "border-slate-500",  text: "text-slate-700",  icon: "·"  },
  Medium:   { bg: "bg-yellow-50",  border: "border-yellow-600", text: "text-yellow-700", icon: "i"  },
  High:     { bg: "bg-orange-50",  border: "border-orange-600", text: "text-orange-700", icon: "!"  },
  Critical: { bg: "bg-red-50",     border: "border-red-600",    text: "text-red-700",    icon: "!!" },
} as const
```

**Design tokens — Status badge (khớp `_VALID_TRANSITIONS` trong `services/imm12.py`):**
```typescript
export const incidentStatusTokens = {
  Open:           { color: "gray",   icon: "o" },
  Acknowledged:   { color: "blue",   icon: ">" },
  "In Progress":  { color: "indigo", icon: "~" },
  Resolved:       { color: "green",  icon: "v" },
  "RCA Required": { color: "amber",  icon: "?" },
  Closed:         { color: "slate",  icon: "x" },
  Cancelled:      { color: "red",    icon: "-" },
} as const
```

---

## 4. Pinia Store — `useImm12Store`

> ✅ Store đã hiện hữu tại `frontend/src/stores/imm12.ts`. Các view trong `views/incident/` cũng có thể gọi trực tiếp `api/imm12.ts` qua composable khi không cần state chia sẻ. Skeleton dưới đây phản ánh interface store.
>
> **DELTA type (BR-12-09):** `types/imm12.ts::IncidentReport` thêm `response_breached?: 0|1` + `resolution_breached?: 0|1` (khớp field BE `list_incidents`/`get_incident_detail`). Dashboard `stats` type thêm `sla_response_breached: number` + `sla_resolution_breached: number`.
>
> **DELTA type (BR-12-13, vòng 4):** `api/imm12.ts::IncidentReport` (+ shape `active_incidents` row) thêm `is_response_breached?: 0|1` + `is_resolution_breached?: 0|1` (field **derived LIVE** từ BE — badge bind field này thay cờ thô). Cờ thô `response_breached`/`resolution_breached` GIỮ trong type (backward-compat). `stats.sla_response_breached`/`sla_resolution_breached` (đã có) giữ nguyên `number` — chỉ ngữ nghĩa giá trị đổi sang LIVE count (BE-driven), binding KHÔNG đổi.
>
> **DELTA type (BR-12-11, vòng 21):** `api/imm12.ts::IncidentStats` + `DashboardStats` thêm `open_total: number` (count SoT `open_incident_filter()`). Card "Đang mở" bind `stats.open_total`; KHÔNG xoá `open`/`investigating`.
>
> **DELTA type (BR-12-11b, vòng 29):** `api/imm12.ts::IncidentStats` + `DashboardStats` thêm `critical_open?: number` + `high_open?: number` (count SoT `open_incident_filter()∧severity`). KPI strip `IncidentListView.vue` tile severity bind `stats.critical_open ?? 0` / `stats.high_open ?? 0` + nhãn 'đang mở'; KHÔNG xoá `critical`/`high` global. Xem §2.6.

```typescript
// src/stores/imm12.ts  (actual file — interface tham khảo)
import { defineStore } from "pinia"
import { ref, computed } from "vue"
import type { IncidentReport, CAPARecord, RCARecord, ChronicFailure } from "@/types/imm12"

export const useImm12Store = defineStore("imm12", () => {
  // ─── State ───────────────────────────────────────────────
  const incidents       = ref<IncidentReport[]>([])
  const activeIncident  = ref<IncidentReport | null>(null)
  const capaList        = ref<CAPARecord[]>([])
  const rcaList         = ref<RCARecord[]>([])
  const activeRCA       = ref<RCARecord | null>(null)
  const chronicFailures = ref<ChronicFailure[]>([])
  const loading         = ref(false)
  const error           = ref<string | null>(null)

  // ─── Computed ────────────────────────────────────────────
  const openIncidents = computed(() =>
    incidents.value.filter((ir) => !["Closed", "Cancelled"].includes(ir.status))
  )
  const criticalIncidents = computed(() =>
    openIncidents.value.filter((ir) => ir.severity === "Critical")
  )
  const overdueCAPAs = computed(() =>
    capaList.value.filter((c) => c.status === "Overdue")
  )

  // ─── Actions ─────────────────────────────────────────────
  async function reportIncident(payload: NewIncidentPayload): Promise<string> {
    loading.value = true
    const res = await useApi().run("assetcore.api.imm12.report_incident", payload)
    incidents.value.unshift(res.data)
    loading.value = false
    return res.data.name
  }

  async function acknowledgeIncident(name: string, assignedTo: string, notes = "") {
    const res = await useApi().run("assetcore.api.imm12.acknowledge_incident",
      { name, assigned_to: assignedTo, notes })
    _patchIncident(name, res.data)
  }

  async function resolveIncident(name: string, resolutionNotes: string) {
    const res = await useApi().run("assetcore.api.imm12.resolve_incident",
      { name, resolution_notes: resolutionNotes })
    _patchIncident(name, res.data)
    return res.data  // may include rca_record
  }

  async function closeIncident(name: string) {
    const res = await useApi().run("assetcore.api.imm12.close_incident", { name })
    _patchIncident(name, res.data)
  }

  async function submitRCA(payload: SubmitRCAPayload): Promise<string> {
    const res = await useApi().run("assetcore.api.imm12.submit_rca", payload)
    return res.data.linked_capa
  }

  // CAPA — uses IMM-00 LIVE endpoints
  async function closeCAPA(payload: CloseCAPAPayload) {
    await useApi().run("assetcore.api.imm00.close_capa", payload)
    const idx = capaList.value.findIndex((c) => c.name === payload.capa_name)
    if (idx !== -1) capaList.value[idx].status = "Closed"
  }

  function _patchIncident(name: string, data: Partial<IncidentReport>) {
    const idx = incidents.value.findIndex((ir) => ir.name === name)
    if (idx !== -1) Object.assign(incidents.value[idx], data)
    if (activeIncident.value?.name === name) Object.assign(activeIncident.value, data)
  }

  return {
    incidents, activeIncident, capaList, rcaList, activeRCA,
    chronicFailures, loading, error,
    openIncidents, criticalIncidents, overdueCAPAs,
    reportIncident, acknowledgeIncident, resolveIncident,
    closeIncident, submitRCA, closeCAPA,
  }
}, { persist: false })
```

---

## 5. Vue Query Keys

```typescript
// src/api/queryKeys.ts
export const imm12Keys = {
  all:            ["imm12"] as const,
  incidents:      () => [...imm12Keys.all, "incidents"] as const,
  incident:       (name: string) => [...imm12Keys.incidents(), name] as const,
  rca:            () => [...imm12Keys.all, "rca"] as const,
  rcaDetail:      (name: string) => [...imm12Keys.rca(), name] as const,
  capa:           () => [...imm12Keys.all, "capa"] as const,
  capaDetail:     (name: string) => [...imm12Keys.capa(), name] as const,
  chronic:        () => [...imm12Keys.all, "chronic"] as const,
  dashboard:      (year: number, month: number) =>
                    [...imm12Keys.all, "dashboard", year, month] as const,
}
```

**Invalidate rules:**
| Action | Invalidate |
|---|---|
| `reportIncident` | `imm12Keys.incidents()` |
| `acknowledgeIncident`, `resolveIncident`, `closeIncident` | `imm12Keys.incident(name)` + `imm12Keys.incidents()` |
| `submitRCA` | `imm12Keys.rcaDetail(name)` + `imm12Keys.capa()` + `imm12Keys.incident(ir)` |
| `closeCAPA` | `imm12Keys.capaDetail(name)` + `imm12Keys.capa()` |

---

## 6. API Pattern

**File:** `frontend/src/api/imm12.ts` ✅ LIVE — base URL `/api/method/assetcore.api.imm12`

**Exported functions (actual):**
- `listIncidents(params)` → `{pagination, items: IncidentDetail[]}`
- `getIncident(name)` → `IncidentDetail`
- `acknowledgeIncident(name, notes, assigned_to)` → `{name, status}`
- `resolveIncident(name, resolution_notes, root_cause)` → `{name, status, linked_capa?}`
- `closeIncident(name, verification_notes)` → `{name, status, closed_date?}`
- `getIncidentStats()` → `IncidentStats`
- `reportIncident(data: ReportIncidentPayload)` → `{name, status, severity}` — **V4 D3:** `ReportIncidentPayload` THÊM `source?: 'manual'|'qr-scan'` (provenance, default manual ở BE).
- `cancelIncident(name, reason)` → `{name, status}`
- `createRca(incident_name, rca_method)` → `{name, status}`
- `getRca(name)` → `RCADetail`
- `submitRca(data: SubmitRcaPayload)` → `{name, status, linked_capa?}` (serializes `five_why_steps` to JSON string)
- `getAssetIncidentHistory(asset, limit)` → `{asset, items}`
- `getChronicFailures()` → `{items: ChronicFailure[]}`
- `getDashboard()` → `DashboardData`

**Corrected cascade watch (actual field `incident_type`, not `fault_description`):**
```typescript
// IncidentCreateView.vue
watch(() => form.severity, (val) => {
  if (val !== "Critical") {
    form.clinical_impact = ""
  }
  showClinicalImpact.value = val === "Critical"
})
```

---

## 7. Copy & Feedback

| State | Component | Copy tiếng Việt |
|---|---|---|
| Empty (Incident List) | IncidentListView | "Chưa có sự cố nào được ghi nhận." · CTA: "Báo cáo sự cố" |
| Empty (CAPA List) | CAPAListView | "Không có CAPA nào đang mở." |
| Empty (Chronic) | ChronicFailureView | "Không phát hiện lỗi mãn tính trong 90 ngày qua." |
| Loading | All lists | Skeleton placeholder (table rows) |
| Error (network) | All | Toast đỏ "Không thể tải dữ liệu. Vui lòng thử lại." + [Retry] |
| Error (BUSINESS_RULE: BR-12-01) | IncidentFormView | Inline: "Sự cố Critical bắt buộc mô tả tác động lâm sàng" |
| Error (BAD_STATE: BR-12-02) | IncidentDetailView | Modal: "Không thể đóng sự cố khi RCA chưa hoàn thành. Mở RCA-2026-0012 →" |
| Success (create IR) | IncidentFormView | Toast xanh "Sự cố đã ghi nhận" + redirect → `/incidents/list/:name` |
| Success (close CAPA) | CAPAFormView | Modal "CAPA đã đóng — audit đã ghi nhận." |
| Critical alert | App shell banner | 🔴 "Sự cố Critical đang mở: [IR-2026-0042] — Máy thở Drager E. — ICU" |

---

## 7.1 AC-CR-83 — lỗi hồ sơ RCA hiển thị **dưới đúng ô nhập** (`RCADetailView.vue`)

**Hiện trạng (verify 2026-07-27):** `submit()` (`frontend/src/views/incident/RCADetailView.vue:105-126`) chỉ làm `err.value = e.message` ⇒ mọi lỗi rơi vào **một** dải đỏ ở đầu trang; KTV bỏ trống ô «Why 3» không biết ô nào sai. Đường dẫn dữ liệu **đã sẵn sàng**: `helpers.ts::hydrateApiError` gán `ApiError.fields` từ envelope; `frappePost` ném đúng `ApiError` đó. FE chỉ chưa **đọc** nó.

### Hợp đồng render

| Khoá `fields` | Neo vào | `data-testid` |
|---|---|---|
| `five_why_steps.<n>` | ngay **dưới** textarea `#why-a-<n>` (dòng «Why n») | `rca-field-error-why-<n>` |
| `five_why_steps` | dưới **tiêu đề** khối "Phân tích 5-Why" | `rca-field-error-five-why` |
| `root_cause` | dưới `#rca-root-cause` | `rca-field-error-root-cause` |
| `corrective_action` | dưới `#rca-corrective` (**tên tham số GHI** — KHÔNG `corrective_action_summary`) | `rca-field-error-corrective` |
| `assigned_to` | dải cảnh báo trên cụm CTA (hồ sơ chưa phân công) | `rca-field-error-assigned-to` |

### Quy tắc bắt buộc

1. **State riêng** `fieldErrors = ref<Record<string,string>>({})`; `submit()` set từ `e instanceof ApiError ? (e.fields ?? {}) : {}`; **xoá** ở đầu mỗi lần submit và khi `load()` thành công.
2. **Nút «Hoàn thành RCA» KHÔNG được biến mất** sau lỗi — chỉ `saving=false`. (Nút hiện gate bằng `canComplete` từ `allowed_transitions`; lỗi field-level KHÔNG chạm gate đó — INV-RCA-7.)
3. **Không đánh mất thông điệp tổng**: `err.value` vẫn hiện `e.message` (câu tiếng Việt từ registry). `fields` là **bổ sung**, không thay thế.
4. **Cấm rò chuỗi kỹ thuật**: DOM sau lỗi KHÔNG được chứa `Traceback`, `ValidationError`, `_server_messages`, tên module Python. Chỉ echo `ApiError.message` khi có `code` (envelope Decision-B); shape lạ ⇒ câu chung "Có lỗi máy chủ, vui lòng thử lại." (parity `attachIncidentPhoto`, `api/imm12.ts:214-231`).
5. **`aria-describedby`**: mỗi textarea có lỗi phải trỏ tới id của thông điệp (`why-a-<n>-error`, …) + `role="alert"` để screen-reader đọc ngay.
6. **Neo theo `why_number`, KHÔNG theo chỉ số mảng** — nhãn người dùng thấy là «Why n» (ADR-IMM12-14). Khoá lạ / `n` không khớp dòng nào ⇒ **đẩy xuống dải tổng**, tuyệt đối không nuốt im lặng.

> ⚠️ Khoá `corrective_action` là **tên tham số GHI**. FE đang bind `v-model="correctiveAction"` rồi gửi `corrective_action` — đúng; nhưng field **đọc** khi `load()` là `res.corrective_action_summary` (`RCADetailView.vue:62`). Đừng "thống nhất" 2 tên: đó là bất đối xứng CÓ THẬT của BE (CR-52 quirk 2).

---

## 8. Accessibility

- Severity badges: icon + text label (không chỉ màu) — WCAG AA contrast
- `aria-label` cho action buttons: `aria-label="Tiếp nhận sự cố IR-2026-0042"`
- Focus trap trong `CAPACloseDialog` và Cancel Confirm modal
- `role="alert"` cho Critical banner (screen reader announces immediately)
- Keyboard navigation: Tab qua mọi action; Enter submit form; Esc đóng modal

---

## DoD — File 06 hoàn chỉnh

- [x] Sitemap (8 routes) — actual Vue files: IncidentListView · IncidentCreateView · IncidentDetailView · RCADetailView · CAPAListView · CAPADetailView · IMM12DashboardView
- [x] Sidebar nav TypeScript config
- [x] 4 ASCII mockups (List · New Form · Detail · RCA Form)
- [x] Component table (7 components với props — corrected actual state names)
- [x] Design tokens: severity (4 levels: Low/Medium/High/Critical) + status badge (5 actual states)
- [x] Pinia store `useImm12Store` (design spec — verify if store actually implemented separately)
- [x] Vue Query keys + invalidate rules
- [x] ✅ API client `api/imm12.ts` with 14 exported functions
- [x] Corrected cascade watch (incident_type field, not fault_description)
- [x] Copy / feedback table (8 states)
- [x] Accessibility checklist
- [ ] Playwright E2E tests
- [ ] Reviewed bởi FE Lead + UX
