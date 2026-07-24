# 04 — Thiết kế Backend (Backend Design)

| Mục | Giá trị |
|---|---|
| Module | IMM-11 — Hiệu chuẩn (Calibration) |
| Phạm vi | Per-module |
| Owner | Tech Lead / BE Lead |
| Liên kết | 02 Analysis & Design · 03 Diagrams · 05 API |
| Cập nhật | 2026-05-14 |
| Trạng thái | ✅ Live — `services/imm11.py` và `api/imm11.py` đã implement |

---

## 1. Tổng quan kiến trúc

IMM-11 bám kiến trúc 3-tier strict của AssetCore:

```
FE Vue 3
    │ REST @frappe.whitelist
    ▼
api/imm11.py          ← thin wrapper: parse → service → _ok/_err
    │
    ▼
services/imm11.py     ← business logic: BR-11-xx, tolerance compute
    │          │
    ▼          ▼
IMM-11        services/imm00.py   ← KHÔNG reimplement: transition_asset_status,
DocTypes      (LIVE)                  create_capa, log_audit_event, etc.
```

**Quy ước ngôn ngữ BE:**
- Code (function, class, variable): tiếng Anh snake_case
- DocType `fieldname`: tiếng Anh (`asset`, `calibration_type`, `overall_result`)
- DocType field `label`: tiếng Việt (`Thiết bị`, `Loại hiệu chuẩn`, `Kết quả tổng`)
- Enum value: tiếng Anh (`External`, `In-House`, `Passed`, `Failed`)
- Error message: tiếng Việt (user-facing)

---

## 2. Domain Model — DocType

### 2.1 IMM Calibration Schedule ✅ DocType: `imm_calibration_schedule`

- **Naming:** `CAL-SCH-.YYYY.-.#####`
- **Type:** Non-submittable

| Trường | Type | Required | Default | Validation |
|---|---|---|---|---|
| `asset` | Link AC Asset | ✓ | — | must be Active |
| `device_model` | Link IMM Device Model | ✓ | auto-fetch | — |
| `calibration_type` | Select | ✓ | External | External, In-House |
| `interval_days` | Int | ✓ | từ Device Model | > 0 |
| `last_calibration_date` | Date | ✗ | auto | Set on pass |
| `next_due_date` | Date | ✓ | computed | last + interval |
| `preferred_lab` | Link AC Supplier | ✗ | — | iso_17025_certified=1 |
| `is_active` | Check | ✓ | 1 | — |

**Indexes:** `(asset, is_active)`, `(next_due_date, is_active)`

### 2.2 IMM Asset Calibration ✅ DocType: `imm_asset_calibration`

Child table: **IMM Calibration Measurement** (`imm_calibration_measurement`) — linked via `measurements` child table field.

- **Naming:** `CAL-.YYYY.-.#####`
- **Type:** Submittable

| Trường | Type | Required | Default | Validation |
|---|---|---|---|---|
| `asset` | Link AC Asset | ✓ | — | `validate_asset_for_operations` (trừ recal) |
| `calibration_type` | Select | ✓ | — | External, In-House |
| `status` | Select | ✓ | Scheduled | 8 states |
| `overall_result` | Select | ✗ | — | Computed `before_submit` |
| `lab_supplier` | Link AC Supplier | Conditional | — | External: iso_17025_certified=1 |
| `certificate_file` | Attach | Conditional | — | External Submit |
| `certificate_date` | Date | Conditional | — | ≤ today; External Pass |
| `lab_accreditation_number` | Data | Conditional | — | External Submit |
| `technician` | Link User | ✓ | — | — |
| `measurements` | Table | ✓ | — | ≥1 row |
| `is_recalibration` | Check | ✗ | 0 | — |
| `amendment_reason` | Small Text | Conditional | — | Amend |
| `capa_record` | Link IMM CAPA Record | ✗ | Auto | Set by service on Fail |

**Permission query (IMM Technician):**
```python
"`tabIMM Asset Calibration`.`technician` = '{user}' OR `tabIMM Asset Calibration`.`assigned_by` = '{user}'"
```

---

## 3. Workflow

**File:** `assetcore/assetcore/workflow/imm_11_calibration_workflow.json` (document_type = `IMM Asset Calibration`, workflow_state_field = `workflow_state`)

| State | Style | docstatus | allow_edit role |
|---|---|---|---|
| Scheduled | Primary | 0 | Workshop Lead, Technician |
| Sent to Lab | Warning | 0 | Technician |
| In Progress | Warning | 0 | Technician |
| Certificate Received | Primary | 0 | Technician |
| Passed | Success | 1 | — |
| Failed | Danger | 1 | — |
| Conditionally Passed | Warning | 1 | — |
| Cancelled | Danger | 2 | — |

Actual transitions (from `imm_11_calibration_workflow.json`):

| From | To | Action label (tiếng Việt) | Allowed role | Condition |
|---|---|---|---|---|
| Scheduled | In Progress | Bắt đầu hiệu chuẩn | Technician | calibration_type=In-House |
| Scheduled | Sent to Lab | Gửi phòng hiệu chuẩn | Technician | calibration_type=External |
| Scheduled | Cancelled | Hủy lịch | Workshop Lead | docstatus=0 |
| In Progress | Passed | Đạt hiệu chuẩn | Technician | overall_result=Passed |
| In Progress | Failed | Không đạt hiệu chuẩn | Technician | overall_result=Failed |
| In Progress | Conditionally Passed | Đạt có điều kiện | Technician | overall_result=Conditionally Passed |
| In Progress | Cancelled | Hủy hiệu chuẩn | Technician | — |
| Sent to Lab | Certificate Received | Nhận chứng chỉ | Technician | — |
| Certificate Received | Passed | Phê duyệt đạt | Workshop Lead / QA | — |
| Certificate Received | Failed | Phê duyệt không đạt | Workshop Lead / QA | — |
| Certificate Received | Conditionally Passed | Phê duyệt có điều kiện | Workshop Lead / QA | — |
| Failed | Conditionally Passed | CAPA hoàn tất - chuyển có điều kiện | QA Officer | CAPA Closed + recal Pass |

> ⚠️ **Data-quality note (workflow JSON):** `imm_11_calibration_workflow.json` chứa **13 dòng `transitions[]`** nhưng chỉ **12 cạnh duy nhất (unique edges)** — cạnh `Failed → Conditionally Passed` bị **lặp 2 lần** (cùng `state`/`next_state`/`action` "CAPA hoàn tất - chuyển có điều kiện", index 11 + 12). Bảng §3 ở trên (12 dòng) là **đúng theo ngữ nghĩa** (12 cạnh unique). Đây là dòng thừa trong JSON nguồn — KHÔNG đổi semantics state-machine. Guard test (xem §3.1) so map BE với codomain JSON **theo SET (tự dedup)** ⇒ không lệch; assertion đếm thô giữ `len(transitions)==13` (count thật JSON), CÓ ghi chú "13 thô = 12 unique". *(Cần khảo sát: có nên dọn dòng lặp trong JSON ở round riêng — ngoài scope vòng này vì sẽ chạm migration/fixture; flag `[ROADMAP]`.)*

### 3.1 `_CAL_VALID_TRANSITIONS` — server-driven CTA map (allowed_transitions[])

**Mục đích:** `get_calibration(name)` emit thêm key `allowed_transitions: list[str]` để client (mobile `getCalibration`) render nút workflow màn calibration-detail **theo SERVER**, KHÔNG hardcode `status → button` ở client (anti-pattern dead-gate / RBAC-drift). Đây là thành viên **THỨ TƯ và CUỐI** của họ `allowed_transitions[]` — sau `IncidentDetail` (imm12.py:778, R3) + `PmWorkOrderDetail` (imm08.py:651, R21) + `RepairWorkOrderDetail` (imm09.py:773, R22) — **ĐÓNG KÍN ASYMMETRY R3**: cả 4 `*Detail` đều emit `allowed_transitions[]`.

**Map (keyed BẰNG `CalibrationResult.*` constants — KHÔNG string literal):**

```python
# assetcore/services/imm11.py  (mirror imm09.py:83 R22 / imm08.py:80 R21)
# Keyed BẰNG CalibrationResult.* (services/shared/constants.py:112) — KHÔNG literal.
# Codomain GROUNDED edge-by-edge imm_11_calibration_workflow.json transitions[]
# (8 state / 13 transition thô = 12 unique edge). Terminal Passed/Conditionally
# Passed/Cancelled → [] (0 outgoing). Guard test chốt SSoT-divergence (map↔workflow
# theo SET) + codomain ⊆ CalibrationResult enum (chống typo/drift).
_CAL_VALID_TRANSITIONS: dict[str, list[str]] = {
    CalibrationResult.SCHEDULED: [
        CalibrationResult.IN_PROGRESS,
        CalibrationResult.SENT_TO_LAB,
        CalibrationResult.CANCELLED,
    ],
    CalibrationResult.IN_PROGRESS: [
        CalibrationResult.PASSED,
        CalibrationResult.FAILED,
        CalibrationResult.COND_PASSED,
        CalibrationResult.CANCELLED,
    ],
    CalibrationResult.SENT_TO_LAB: [CalibrationResult.CERT_RECEIVED],
    CalibrationResult.CERT_RECEIVED: [
        CalibrationResult.PASSED,
        CalibrationResult.FAILED,
        CalibrationResult.COND_PASSED,
    ],
    CalibrationResult.FAILED: [CalibrationResult.COND_PASSED],
    CalibrationResult.PASSED: [],          # terminal (docstatus=1)
    CalibrationResult.COND_PASSED: [],     # terminal (docstatus=1)
    CalibrationResult.CANCELLED: [],       # terminal (docstatus=2)
}
```

**Emit (mirror R21/R22):**

```python
# services/imm11.py:get_calibration — thêm 1 key vào dict return (KHÔNG đổi signature)
data["allowed_transitions"] = _CAL_VALID_TRANSITIONS.get(doc.status, [])
return data
```

**Boundaries:**
- **Always:** key `allowed_transitions` LUÔN emit (kể cả `[]` khi terminal); keyed bằng `CalibrationResult.*`; codomain ⊆ `CalibrationResult` enum; FE render CTA theo list này (KHÔNG suy diễn client-side).
- **Never:** ❌ đổi signature `get_calibration(name)` · ❌ đổi handler `api/imm11.py:81` (vendor IDOR guard `assert_vendor_can_access` + `handle(svc.get_calibration, name)` GIỮ nguyên — field mới chảy qua envelope tự động) · ❌ đưa `allowed_transitions` vào `required` của contract · ❌ string-literal key · ❌ enum-bound cứng `items` trong yaml (né drift).

#### ADR-IMM11-04: `allowed_transitions[]` server-driven CTA cho getCalibration

- **Status:** Accepted — 2026-06-16 (đóng kín ASYMMETRY R3; mirror ADR R3/R21/R22 của Incident/PM/Repair)
- **Context:** Mobile `getCalibration` detail cần biết "từ status hiện tại được phép chuyển sang state nào" để render nút workflow. 3 *Detail kia (Incident/PM/Repair) đã emit `allowed_transitions[]`; CalibrationDetail là *Detail DUY NHẤT còn THIẾU ⇒ ASYMMETRY. Client KHÔNG được hardcode `status→button` (dead-gate: workflow đổi → FE lệch âm thầm).
- **Decision:** Thêm map module-level `_CAL_VALID_TRANSITIONS` (dict keyed `CalibrationResult.*`) + emit `data["allowed_transitions"]` trong `get_calibration` (chỉ thêm 1 key vào dict return). KHÔNG đổi signature/handler. Contract `CalibrationDetail` thêm property `allowed_transitions: array<string>`, NOT-required, `additionalProperties:true` GIỮ.
- **Alternatives:** (a) FE hardcode `status→button` — LOẠI: dead-gate, drift khi workflow đổi. (b) Endpoint riêng `getCalibrationTransitions` — LOẠI: thừa round-trip; allowed_transitions là thuộc tính của chính doc-detail (mirror 3 *Detail kia). (c) enum-bound cứng `items.enum` trong yaml — LOẠI: drift khi workflow thêm state; codomain-check để ở guard test phía service (`test_imm11`).
- **Consequences:** (+) 4/4 *Detail đối xứng, FE render CTA thống nhất 1 pattern. (+) Guard test SSoT-divergence (map↔workflow JSON theo SET) bắt drift sớm. (−) Workflow JSON có 1 cạnh lặp (`Failed→Conditionally Passed` ×2) ⇒ guard so theo SET (tự dedup), count thô giữ 13 — phải ghi chú rõ (xem note §3). (−) Live HTTP cần reload gunicorn (`--preload`) để key mới hiện — guard in-process KHÔNG cần (HARD-STOP user).

**Controller hooks (delegate-only):**

```python
# assetcore/assetcore/doctype/imm_asset_calibration/imm_asset_calibration.py  ✅ EXISTS
# Controller delegates on_submit → service layer handles Pass/Fail branching
# Pass path: services.imm11.handle_calibration_pass(cal_doc)
# Fail path: services.imm11.handle_calibration_fail(cal_doc)
```

### 3.2. Dual-track lockstep `workflow_state ⇄ status` + INVARIANT (round 18 — CR-WF-11-CAL)

**Desync gốc (bug — KHÔNG phải dual-track có chủ đích).** DocType `IMM Asset Calibration` có **2 field song song**: `status` (Select, default `'Scheduled'`, 8 option) + `workflow_state` (Link → `Workflow State`, default `None`). Workflow `imm_11_calibration_workflow.json` **is_active=1**, bound qua `workflow_state_field="workflow_state"`. MỌI service-action calibration đặt `doc.status` qua `CalibrationRepo.update_fields` (= `doc.save()`) / `.create` / `.submit` NHƯNG **KHÔNG chạm `doc.workflow_state`**. Trên `doc.save()`, `validate_workflow` thấy `workflow_state` KHÔNG đổi (đọng `'Scheduled'`) ⇒ return sớm, 0 transition. Hệ quả: `status` marches nhưng `workflow_state` **đọng `'Scheduled'` (state khởi tạo) vĩnh viễn**.

RED đo được (acceptance): tạo phiếu External → `send_to_lab` → `status='Sent to Lab'` nhưng `workflow_state='Scheduled'`. Trên **desk**, workflow-engine `get_transitions(doc)` đọc `workflow_state='Scheduled'` → chỉ hiện nút của `Scheduled` (→ In Progress / Sent to Lab / Cancelled) — SAI, vì phiếu THỰC đã ở `Sent to Lab`. ⇒ QTV/AssetCore Super Admin **không điều hành phiếu qua workflow-engine** dù đủ quyền (đây là triệu chứng CR).

**Cơ chế fix (lockstep) — SAU mỗi transition-fn, sync `workflow_state = status`:**

```python
# assetcore/services/imm11.py — helper DRY (mirror IMM-16 §III.B.2 / IMM-12 imm12.py:797/938/1568).
# frappe.db.set_value BYPASS validate_workflow (ghi SQL trực tiếp, 0 validate cycle).
def _lockstep_cal_workflow_state(name: str, status: str) -> None:
    frappe.db.set_value(_DT_CAL, name, {"workflow_state": status}, update_modified=False)

# Gọi SAU mỗi write-path status (6 điểm), value = status CUỐI CÙNG của phiếu:
#   create_calibration      → Scheduled      (imm11.py:1083)
#   update_calibration      → doc.status     (patch.status, thường In Progress; imm11.py:1108)
#   send_to_lab             → Sent to Lab    (imm11.py:1285)
#   receive_certificate     → In Progress    (imm11.py:1327)  ⚠️ KHÔNG phải Certificate Received
#   cancel_calibration      → Cancelled      (imm11.py:1356)
#   submit_calibration      → doc.status     (KHÔNG đổi; controller chỉ set overall_result — OoS scope)
```

- **Vì sao `frappe.db.set_value` (KHÔNG `doc.save()` set cả 2):** Frappe v15 `model/workflow.py::validate_workflow` **raise `WorkflowPermissionError`** khi `doc.save()` đổi `workflow_state` sang state KHÔNG kề (không có edge từ state cũ). `receive_certificate` nhảy `Sent to Lab → In Progress` — workflow chỉ có cạnh `Sent to Lab → Certificate Received`, **0 cạnh `Sent to Lab → In Progress`** ⇒ `doc.save()` sẽ throw. `db.set_value` ghi SQL trực tiếp, KHÔNG chạy validate cycle ⇒ an toàn cho multi-hop (kể cả trên doc `docstatus=1` sau `submit_calibration`). (Lý do code cũ KHÔNG throw: `workflow_state` đọng `Scheduled→Scheduled` ⇒ `validate_workflow` return sớm `current==next`.)
- **Boundaries — Always:** cả 6 write-path status (`create`/`update`/`send_to_lab`/`receive_certificate`/`cancel`/`submit`) đặt CẢ 2 track lockstep. **Never:** ❌ đổi `workflow_state` calibration qua `doc.save()` (trip validate_workflow) · ❌ sửa `imm_11_calibration_workflow.json` / `fixtures/workflow.json` (HARD-STOP reload/migrate — gate admin-override `test_workflow_admin_override` GREEN KHÔNG được phá) · ❌ nhồi cạnh mới `Sent to Lab → In Progress` vào workflow JSON để "khớp" `receive_certificate`.
- **Scope hẹp — CHỈ field `workflow_state`:** lockstep đồng bộ đúng `workflow_state` ⇄ `status`. KHÔNG đụng `docstatus` (Frappe ledger). Terminal `Passed/Failed/Conditionally Passed` (docstatus=1) + `Cancelled` (docstatus=2) cột workflow-JSON là tình trạng CŨ — vòng này chỉ lockstep các status **service-reachable** (§INV-11-B), KHÔNG buộc docstatus khớp.

**INVARIANT guard (RED-before / GREEN-after) — `test_imm11` (§07 AT-11-LOCKSTEP + INV-11):**

```python
# INV-11-A (name-parity): mọi giá trị status Select == tên state workflow (1-1).
#   set(status Select options)  ==  set(states[] imm_11_calibration_workflow.json)  ==  8
#   ⇒ lockstep `workflow_state := status` LUÔN ghi 1 tên Workflow State hợp lệ.
# INV-11-B (service-reachable ⊆ states): S_svc ⊆ states[] name-parity.
#   S_svc = {Scheduled, In Progress, Sent to Lab, Cancelled}  (4 — grounded 6 write-path)
# INV-11-C (lockstep behavioral): drive từng transition service rồi đọc lại DB
#   db.get_value('IMM Asset Calibration', name, 'workflow_state') == status.
```

- **S_svc GROUNDED = {Scheduled, In Progress, Sent to Lab, Cancelled}** — chính xác 4 giá trị mà 6 write-path đặt vào `status`. **Self-Correction (⚠️ quan trọng):** acceptance liệt kê "service-reachable {…, Certificate Received, …}" là **KHÔNG chính xác** — `receive_certificate` đặt `status = In Progress` (imm11.py:1327), **KHÔNG** đặt `Certificate Received`. `'Certificate Received'` là **workflow-state**: chỉ tới được qua **desk workflow-action** "Nhận chứng chỉ" (`Sent to Lab → Certificate Received`), 0 service-driver đặt `status` = giá trị này. Nó vẫn ∈ `states[]` (INV-11-A đủ), nhưng KHÔNG ∈ S_svc ⇒ INV-11-C chỉ drive 4 giá trị service-produced.
- **RED-before:** với code chưa fix, AT-11-LOCKSTEP dừng ở assertion sau `send_to_lab`: `workflow_state='Scheduled' != status='Sent to Lab'` (chứng minh desk-desync). **GREEN-after:** mọi transition `workflow_state == status`.
- **get_transitions phản ánh state HIỆN TẠI (acceptance #3):** sau `send_to_lab` (đã fix), `frappe.model.workflow.get_transitions(doc)` trả cạnh của `'Sent to Lab'` (→ Certificate Received), KHÔNG phải của `'Scheduled'` ⇒ admin/QTV thấy đúng nút workflow tiếp theo trên desk.

**OUT-OF-SCOPE (backlog — KHÔNG làm vòng này):**
1. `submit_calibration` KHÔNG tự advance `status` sang `Passed/Failed/Conditionally Passed` — controller `on_submit` chỉ set `overall_result` + asset/CAPA (imm11.py:31-35). 3 terminal-state + KPI `status`-filter `[Passed, Conditionally Passed]` (imm11.py:1161) là **bug thứ cấp riêng** (status vẫn `In Progress` sau submit).
2. **Reverse-sync desk → service:** sau fix, tại `workflow_state='Sent to Lab'` desk hiện nút "Nhận chứng chỉ" → nếu admin bấm QUA workflow-engine, `workflow_state → Certificate Received` nhưng `status` giữ `Sent to Lab` (desk KHÔNG gọi `receive_certificate` service) ⇒ desync ngược. Vòng này chỉ đóng chiều **service → workflow_state** (desync gốc được báo). Chiều desk → service cần workflow-transition-handler riêng — `[ROADMAP]`.

#### ADR-IMM11-06: Calibration dual-track lockstep `workflow_state ⇄ status` (đóng desync)

- **Status:** Accepted — mirror **ADR-IMM-16-05** (IMM-16 Finding) + **IMM-12** (`imm12.py:797/938/1568`). SUPERSEDE giả định ngầm "workflow_state calibration là track song song decorative, service KHÔNG chạm".
- **Date:** 2026-07-13
- **Context:** `imm_11_calibration_workflow.json` **is_active=1**; 6 service write-path đặt `doc.status` KHÔNG chạm `doc.workflow_state` ⇒ workflow_state đọng `'Scheduled'` trong khi status marches → admin/QTV không điều hành phiếu qua workflow-engine desk (get_transitions đọc sai state).
- **Decision:** SAU mỗi transition-fn, `frappe.db.set_value(_DT_CAL, name, {"workflow_state": <status cuối>}, update_modified=False)` (helper `_lockstep_cal_workflow_state`). 8 giá trị `CalibrationResult`/`status`-Select == 8 tên state workflow EXACT (INV-11-A) ⇒ lockstep 1-1 hợp lệ.
- **Alternatives:**
  - *`doc.save()` set cả `status` + `workflow_state`* — LOẠI: `validate_workflow` raise `WorkflowPermissionError` khi đổi `workflow_state` sang state không-kề (`receive_certificate`: `Sent to Lab → In Progress` 0 edge). `db.set_value` bypass validate.
  - *Đi qua `apply_workflow` engine (walk từng cạnh)* — LOẠI: over-engineering; `Sent to Lab → In Progress` không có đường workflow; buộc hop qua `Certificate Received` vô nghĩa cho luồng service.
  - *Thêm cạnh `Sent to Lab → In Progress` vào workflow JSON* — LOẠI: sửa `imm_11_calibration_workflow.json`/fixtures = HARD-STOP reload/migrate + rủi ro phá gate admin-override.
- **Consequences:**
  - (+) Đóng desync: `workflow_state == status` sau mỗi transition; workflow_state truthful cho desk workflow-engine + `permission_query_conditions`.
  - (+) INVARIANT INV-11-A/B/C (§3.2) chống drift status Select ⇄ workflow states.
  - (−) KHÔNG đóng reverse-sync desk → service (backlog #2) + KHÔNG advance terminal sau submit (backlog #1).
  - (0) KHÔNG migration schema, KHÔNG đổi workflow JSON/fixtures, KHÔNG đụng FE (FE calibration đọc `allowed_transitions`/`status`, KHÔNG đọc `workflow_state` — verified grep=none), KHÔNG đụng gate admin-override.

---

## 4. Service Layer

**File:** `assetcore/services/imm11.py` ✅ LIVE

### Public functions (implemented)

| Function | Input | Output | Side effect |
|---|---|---|---|
| `create_calibration_schedule_from_commissioning(doc)` | Commissioning doc | `str` (sched_name) or None | Insert `IMM Calibration Schedule` + `log_audit_event` |
| `create_post_repair_calibration(asset_name)` | str | `str` or None | Insert `IMM Asset Calibration` (`is_recalibration=1`) |
| `create_due_calibration_wos()` | — | `int` (count created) | Scheduler: Insert draft `IMM Asset Calibration` per due Schedule (threshold 30 days) |
| `check_calibration_expiry()` | — | None | Scheduler: **rollup cache + FULL-SET reconcile** `AC Asset.calibration_status` TỪ SoT schedule (`§4.1.3`). Phạm vi = UNION(asset có active schedule, asset có `calibration_status != ''`). **BR-11-10** stale-clear: hết active schedule → reset `Not Required`. **BR-11-11** preserve terminal `Calibration Failed` khi `lifecycle_status = Out of Service`. Idempotent (chạy 2× = nhau). `notifications.notify_calibration_due(asset, old, new)` (E4) chỉ khi status đổi (anti-spam). Spec: `docs/imm-00/04_Backend_Design.md §III.1b-2`. |
| `_reconcile_calibration_status(asset, old, derived)` | str, str, str? | `str` | None — pure decision per-asset (`§4.1.3`): FAILED-preserve / SoT derived / stale→NOT_REQUIRED |
| `_nonempty_cache_asset_ids()` | — | `set[str]` | None — asset có `calibration_status != ''` (để reconcile thăm CẢ asset hết active schedule, BR-11-10) |
| `is_calibration_overdue(next_due, ref_date)` | date, date? | `bool` | None — pure SoT predicate (`§4.1.1`), `next_due < today` strict |
| `is_calibration_due_soon(next_due, ref_date)` | date, date? | `bool` | None — pure SoT predicate, `today <= next_due <= today+30` inclusive |
| `_overdue_asset_ids(ref_date)` / `_due_soon_asset_ids(ref_date)` | date? | `set[str]` | None — SoT tập asset de-dup (`§4.1.2`), JOIN schedule active + asset không decommissioned |
| `handle_calibration_pass(cal_doc)` | `IMM Asset Calibration` doc | None | Advance `CalibrationSchedule.next_due_date = basis+interval` (BR-11-04) + **ghi ASSET-cache `{calibration_status, next_calibration_date, last_calibration_date}` theo ROLLUP đa-lịch qua `_apply_asset_calibration_rollup()` (BR-11-13, §4.1.7) — KHÔNG hardcode ON_SCHEDULE 1-lịch** + ghi ALE `calibration_passed`; restore CÓ ĐIỀU KIỆN: `Calibrating → Active` luôn; `Out of Service → Active` CHỈ qua `_can_restore_from_oos()` (BR-11-12, §4.1.5). KHÔNG raise ở nhánh restore. |
| `_apply_asset_calibration_rollup(asset, basis)` | str, str | None | Ghi ASSET-cache 3 field theo rollup worst-of-all + `MIN(next_due_date)` (BR-11-13, §4.1.7). Dùng CÙNG SoT `_calibration_status_asset_ids` → ROLLUP-CONSISTENCY với `check_calibration_expiry`. Bounded query (no N+1). |
| `_asset_min_next_due(asset)` | str | `str?` | `MIN(next_due_date)` trên MỌI active schedule của asset (1 aggregate query). None nếu hết active schedule. §4.1.7. |
| `_can_restore_from_oos(asset, cal)` | str, `IMM Asset Calibration` doc | `bool` | None — pure predicate (BR-11-12, §4.1.5): True ⟺ chủ-hold OoS == `IMM Asset Calibration` (ALE mới nhất vào OoS) ∧ 0 hold khác mở (Incident IMM-12 / Repair WO IMM-09 / PM WO OoS-finding IMM-08). MỌI nhánh ép Active-từ-OoS đi qua đây (grep-guard SoT). |
| `_latest_oos_root_doctype(asset)` | str | `str?` | None — đọc ALE mới nhất `to_status='Out of Service'` của asset → trả `root_doctype` (chủ-hold). None nếu không có. |
| `_oos_hold_note(asset, source_label)` | str, str | `str` | None — dựng note VI `giữ Ngừng hoạt động do hạng mục khác (<nguồn>)` cho ALE giữ-OoS. |
| `handle_calibration_fail(cal_doc)` | `IMM Asset Calibration` doc | None | OOS transition + `create_capa()` (severity Major) + lookback + auto-report IMM-12 incident + **hạ MỌI active `Schedule.next_due_date` về basis-date (due-now, BR-11-08b §4.1.6)** — asset rơi vào overdue/due-soon SoT, hết mask ON_SCHEDULE; null-safe (0 schedule → no-op) |
| `perform_lookback_assessment(device_model, exclude_asset)` | str, str | `list[str]` | Read-only: assets same device_model in Active status |
| `list_schedules(filters, page, page_size)` | dict, int, int | `{data, pagination}` | None |
| `get_schedule(name)` | str | dict | None |
| `create_schedule(asset, calibration_type, interval_days, ...)` | kwargs | `{name, next_due_date}` | Insert `IMM Calibration Schedule` |
| `update_schedule(name, patch)` | str, dict | `{name}` | Patch allowed fields only |
| `delete_schedule(name)` | str | `{name, deleted}` | Blocked if submitted calibrations exist |
| `list_calibrations(filters, page, page_size)` | dict, int, int | `{data, pagination}` | Mỗi row + `is_overdue`/`is_due_soon` (int 0/1) derive server-side qua predicate chung trên row.`next_calibration_date` (BR-11-14, §4.1.8). KHÔNG thêm query DB (field đã có trong `fields=[...]`). |
| `get_calibration(name)` | str | dict | + key `allowed_transitions: list[str]` = `_CAL_VALID_TRANSITIONS.get(doc.status, [])` (server-driven CTA, §3.1) + `is_overdue`/`is_due_soon` (int 0/1) derive server-side trên `data["next_calibration_date"]` (BR-11-14, §4.1.8). KHÔNG đổi signature `get_calibration(name)`; KHÔNG đổi handler `api/imm11.py:81`. |
| `create_calibration(asset, calibration_type, scheduled_date, technician, ...)` | kwargs | `{name, status}` | Insert `IMM Asset Calibration` + **lockstep `workflow_state='Scheduled'` (§3.2)** |
| `update_calibration(name, patch)` | str, dict | `{name, status}` | Asset → Calibrating when status in (In Progress, Sent To Lab) + **lockstep `workflow_state=doc.status` (§3.2)**. **+ `measurements` child-diff (BR-11-16 / §4.1.10):** patch chứa key `measurements` (mảng) ⇒ nhánh RIÊNG (ngoài `_UPDATE_ALLOWED`): **replace-set** (reload count==payload count) + sanitize 6-field + `pass_fail`/`out_of_tolerance` server-compute qua `_compute_measurement_results` (SSoT, STRIP client verdict). Guard `docstatus==0` ∧ `status ∈ ACTIVE_STATUSES`; `docstatus==1`→`IMM11_ALREADY_SUBMITTED`(409); draft-ngoài-ACTIVE→`IMM11_MEASUREMENTS_NOT_EDITABLE`(409). Patch KHÔNG có `measurements` ⇒ scalar-path Y NGUYÊN (0 regression). Return-shape `{name,status}` KHÔNG đổi. |
| `submit_calibration(name, client_request_id="")` | str, kwargs | `{name, status, overall_result, next_calibration_date}` | Triggers controller on_submit → Pass/Fail handlers + **lockstep `workflow_state=doc.status` (KHÔNG đổi status; §3.2)**. **+ idempotency dedup (BR-11-17 / §4.1.11 — CR-24-CAL-SUBMIT, op#6 write-family closure):** `resolved_key` (SHARED `resolve_idempotency_key`, body `client_request_id` thắng header `X-Idempotency-Key`) truthy ⇒ dedup qua `frappe.cache()` scoped `(name, resolved_key)` TTL 24h — replay CÙNG khoá **THẮNG** state-guard `docstatus==1`, trả VERBATIM `{name, status, overall_result, next_calibration_date}` lần-đầu (KHÔNG re-submit, KHÔNG double `_lockstep`/ALE). Rỗng ⇒ NO-OP legacy → `docstatus==1` vẫn `IMM11_ALREADY_SUBMITTED`. **Cache-store, KHÔNG DocField, KHÔNG migrate.** |
| `add_measurement(name, parameter_name, unit, ..., client_request_id="")` | str, kwargs | `{name, measurement_count}` | Append to `measurements` child table. **+ idempotency dedup (BR-11-15 / §4.1.9):** `resolved_key` (param `client_request_id` thắng header `X-Idempotency-Key`) truthy ⇒ dedup qua `frappe.cache()` scoped `(name, resolved_key)` TTL 24h — HIT trả VERBATIM `{name, measurement_count}` lần-đầu (KHÔNG append/save/tăng count); rỗng ⇒ NO-OP legacy. Guard `docstatus==1` KHÔNG-khoá vẫn `IMM11_ALREADY_SUBMITTED`. **Cache-store, KHÔNG DocField, KHÔNG migrate.** |
| `send_to_lab(name, sent_date, lab_supplier, lab_contract_ref)` | str, kwargs | `{name, status, sent_date}` | Status → Sent To Lab + Asset → Calibrating + **lockstep `workflow_state='Sent to Lab'` (§3.2)** |
| `receive_certificate(name, certificate_file, certificate_number, ...)` | str, kwargs | `{name, status, certificate_number}` | Status → **In Progress** (⚠️ KHÔNG Certificate Received — §3.2 Self-Correction) + **lockstep `workflow_state='In Progress'`** |
| `cancel_calibration(name, reason)` | str, str | `{name, status}` | Status → Cancelled + Asset → Active if was Calibrating + **lockstep `workflow_state='Cancelled'` (§3.2)** |
| `get_due_calibrations(days, limit)` | int, int | `{items, threshold_days}` | None — item 7-field {name,asset_name,device_model,location,next_calibration_date,calibration_status,`days_left`}; `days_left` signed int (âm=quá hạn) **non-nullable** (`else None` @`services/imm11.py:1420` là dead-branch — filter `next_calibration_date is set`@1409 loại NULL). Mobile-contract binding = `getDueCalibrations` (read-list KHÔNG-pagination, §05 §0.1.9 + ADR-IMM11-DUECAL) |
| `get_asset_history(asset, limit)` | str, int | `{asset, history}` | None |
| `get_kpis(year, month)` | int, int | `{kpis: {...}}` | None |
| `get_dashboard()` | — | `{kpis, overdue_assets, due_soon_assets, capa_open_list, period}` | None |

### Key implementation notes

- Service uses `ServiceError(ErrorCode.X, "msg tiếng Việt")` — raised to API layer, caught by `_handle()`.
- `_UPDATE_ALLOWED` whitelist controls patchable **scalar** fields in `update_calibration()`. **`measurements` KHÔNG thuộc `_UPDATE_ALLOWED`** — xử lý ở nhánh child-diff RIÊNG (replace-set, §4.1.10 / BR-11-16). KHÔNG thêm `measurements` vào whitelist này (sẽ mất semantics replace-set + SSoT recompute).
- `_CALIBRATING_TRIGGER_STATUSES = {In Progress, Sent To Lab}` — transitions Asset → Calibrating when status enters these.
- `CalibrationResult` constants (from `services.shared`): SCHEDULED, IN_PROGRESS, SENT_TO_LAB, PASSED, FAILED, COND_PASSED, CANCELLED plus ACTIVE_STATUSES set.
- `CalibrationStatus` constants: ON_SCHEDULE (`"On Schedule"`), DUE_SOON (`"Due Soon"`), OVERDUE (`"Overdue"`), FAILED (`"Calibration Failed"`, terminal), NOT_REQUIRED (`"Not Required"`, neutral/stale-clear) — written to `AC Asset.calibration_status`. FE phải map ĐỦ 5 giá trị literal này sang nhãn VI (06_Frontend_Design §badge) — KHÔNG để rò EN.
- IMM-12 cross-module: `handle_calibration_fail` auto-calls `imm12.report_incident(...)` with fault_code=`"CAL_FAIL"` (wrapped in try/except, non-blocking).

---

## 4.1 SoT predicate — "calibration due / overdue" (BR-11-08 / BR-11-09)

> **Self-Correction.** Trước fix có **2 nguồn ngày phân kỳ**: dashboard đếm `IMM Calibration Schedule.next_due_date` (không lọc `is_active`/decommissioned → đếm dư), còn IMM-11 KPI/drill đếm `AC Asset.calibration_status` derive từ `AC Asset.next_calibration_date` (field KHÁC, NULL với asset minted → KPI=0). Hợp nhất về **1 predicate + 1 date-field + 1 tập filter**.

### 4.1.1 Hằng + predicate thuần (pure, không I/O)

```python
# services/imm11.py — module-level constants
CAL_DUE_SOON_WINDOW_DAYS = 30      # 1 hằng dùng chung MỌI nơi (KHÔNG hardcode "30" rải rác)
_CAL_AUTH_DATE_FIELD = "next_due_date"   # authoritative date = Schedule.next_due_date

def is_calibration_overdue(next_due, ref_date=None) -> bool:
    """OVERDUE ⟺ next_due < today (strict <). None → False (không có hạn = không quá hạn)."""
    if not next_due:
        return False
    ref = getdate(ref_date) if ref_date else getdate(nowdate())
    return getdate(next_due) < ref

def is_calibration_due_soon(next_due, ref_date=None) -> bool:
    """DUE_SOON ⟺ today <= next_due <= today + CAL_DUE_SOON_WINDOW_DAYS (cả 2 biên inclusive).
    Loại trừ overdue (overdue ưu tiên). None → False."""
    if not next_due:
        return False
    ref = getdate(ref_date) if ref_date else getdate(nowdate())
    nd = getdate(next_due)
    return ref <= nd <= add_days(ref, CAL_DUE_SOON_WINDOW_DAYS)
```

Boundary chốt: `next_due == today` → **DUE_SOON** (KHÔNG overdue); `next_due == today+30` → **DUE_SOON** (inclusive); `next_due == today+31` → ON_SCHEDULE; `next_due == today-1` → OVERDUE.

### 4.1.2 Tập filter SoT (dùng chung dashboard + IMM-11)

Mọi consumer đếm/list theo cùng JOIN + filter:

```python
# Schedule active + asset KHÔNG decommissioned. De-dup theo asset (BR-11-09).
_NOT_DECOMMISSIONED = ("not in", [AssetStatus.DECOMMISSIONED])

def _overdue_asset_ids(ref_date=None) -> set[str]:
    """SoT: tập DISTINCT asset có >=1 active schedule overdue, asset không decommissioned."""
    ref = ref_date or nowdate()
    rows = frappe.db.sql("""
        SELECT DISTINCT s.asset
        FROM `tabIMM Calibration Schedule` s
        JOIN `tabAC Asset` a ON a.name = s.asset
        WHERE s.is_active = 1
          AND s.next_due_date < %(ref)s
          AND a.lifecycle_status != %(decom)s
    """, {"ref": ref, "decom": AssetStatus.DECOMMISSIONED}, as_dict=True)
    return {r["asset"] for r in rows}

def _due_soon_asset_ids(ref_date=None) -> set[str]:
    """SoT: tập DISTINCT asset có >=1 active schedule due trong [today, today+30],
    LOẠI những asset đã overdue (overdue ưu tiên — không double-tally)."""
    ref = ref_date or nowdate()
    window_end = add_days(ref, CAL_DUE_SOON_WINDOW_DAYS)
    rows = frappe.db.sql("""
        SELECT DISTINCT s.asset
        FROM `tabIMM Calibration Schedule` s
        JOIN `tabAC Asset` a ON a.name = s.asset
        WHERE s.is_active = 1
          AND s.next_due_date >= %(ref)s AND s.next_due_date <= %(end)s
          AND a.lifecycle_status != %(decom)s
    """, {"ref": ref, "end": window_end, "decom": AssetStatus.DECOMMISSIONED}, as_dict=True)
    return {r["asset"] for r in rows} - _overdue_asset_ids(ref_date)
```

- **De-dup (BR-11-09):** `SELECT DISTINCT s.asset` → 1 asset có nhiều active schedule overdue chỉ đếm **1 lần theo asset**. `len(_overdue_asset_ids())` == KPI card == số dòng drill (drill cũng group theo asset).
- **Count == drill:** `get_calibration_kpis().overdue_assets == len(_overdue_asset_ids())`; drill `/calibration/schedules?overdue=1` trả CÙNG tập asset (de-dup). Tương tự `due_soon_assets == len(_due_soon_asset_ids())`; drill `?due_soon=1` (cửa-sổ-2-biên `next_due BETWEEN [today, today+30]` + `asset IN _due_soon_asset_ids()`) tái lập CHÍNH XÁC tập KPI — KHÔNG cần post-filter `next_due >= today`. (Param `due_before=X` là cutoff-tùy-ý tập-BAO legacy, GỒM cả overdue — KHÔNG dùng cho card due-soon. `_normalize_schedule_filters` ưu tiên `overdue` > `due_soon` > `due_before`; cả 3 nhánh GIAO caller `asset IN` scope thay vì clobber → vendor-scope an toàn.)
- **Dashboard parity:** `dashboard.py` `calib_overdue = len(_overdue_asset_ids())` và `calib_due = len(_due_soon_asset_ids())` (import từ `services.imm11`) → tổng dashboard == module overdue/due_soon (cùng SoT, KHÔNG lệch).

### 4.1.3 `check_calibration_expiry` — rollup cache + FULL-SET reconcile (BR-11-10 / BR-11-11)

> **Self-Correction (vòng 33).** Bản cũ duyệt CHỈ `rollup.items()` = tập asset CÓ active schedule (`_calibration_status_asset_ids`). Hệ quả 2 lỗi:
> - **BUG-1 stale-never-cleared:** asset từng `Overdue`/`Due Soon`, sau đó lịch DUY NHẤT bị `is_active=0`/xóa → biến mất khỏi rollup map → vòng quét KHÔNG bao giờ thăm lại → cache giữ `Overdue` **vĩnh viễn** (badge ma).
> - **BUG-2 FAILED-clobber:** asset `handle_calibration_fail` set `calibration_status = Calibration Failed` (terminal, `lifecycle_status = Out of Service`, CAPA mở). Nếu lịch vẫn `is_active=1` và quá hạn, rollup map trả `Overdue` cho asset đó → ghi đè **mất terminal FAILED**.
>
> **Chốt:** phạm vi reconcile = **UNION** (asset có ≥1 active schedule) ∪ (asset có `calibration_status != ''`). Rollup iterate TOÀN tập → không cache row nào bị bỏ sót. Thêm 2 guard: **preserve terminal FAILED** + **stale-clear về neutral**.

```python
def check_calibration_expiry() -> None:
    """Scheduler daily — rollup cache AC Asset.calibration_status TỪ SoT schedule,
    reconcile FULL-SET (BR-11-10 stale-clear + BR-11-11 FAILED-preserve).

    Phạm vi = UNION(asset có >=1 active schedule, asset có calibration_status != '').
    Idempotent: chạy 2× cho kết quả như nhau; notify chỉ khi status THỰC SỰ đổi."""
    from assetcore.services import notifications      # lazy — tránh circular

    rollup = _calibration_status_asset_ids()           # map: asset -> derived status (CHỈ active-sched)
    cached = _nonempty_cache_asset_ids()               # set: asset có calibration_status != '' hiện tại
    for asset_name in (set(rollup) | cached):          # UNION — không bỏ sót cache row nào
        old = AssetRepo.get_value(asset_name, "calibration_status") or ""
        new = _reconcile_calibration_status(asset_name, old, rollup.get(asset_name))
        if new == old:
            continue                                   # idempotent — không ghi, không notify lại
        AssetRepo.set_values(asset_name, {"calibration_status": new})
        try:
            notifications.notify_calibration_due(asset_name, old, new)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "imm11 notify_calibration_due")


def _reconcile_calibration_status(asset_name, old, derived):
    """Quyết định giá trị cache mới cho 1 asset (pure decision, không I/O ngoài 1 lookup status).

    - derived = giá trị từ SoT schedule (None nếu asset KHÔNG còn active schedule).
    - BR-11-11 FAILED-preserve: old == FAILED ∧ asset Out of Service → giữ FAILED (terminal).
      Recal Pass (handle_calibration_pass) là CON ĐƯỜNG DUY NHẤT rời FAILED → set ON_SCHEDULE.
    - derived có giá trị (asset còn active schedule) → dùng derived (Overdue/DueSoon/OnSchedule).
    - derived None (BR-11-10 stale-clear): KHÔNG còn active schedule → reset neutral NOT_REQUIRED.
    """
    if old == CalibrationStatus.FAILED:
        lifecycle = AssetRepo.get_value(asset_name, "lifecycle_status")
        if lifecycle == AssetStatus.OUT_OF_SERVICE:
            return CalibrationStatus.FAILED               # BR-11-11 preserve terminal
    if derived is not None:
        return derived                                    # còn active schedule → SoT rollup
    return CalibrationStatus.NOT_REQUIRED                  # BR-11-10 stale-clear → neutral


def _nonempty_cache_asset_ids() -> set[str]:
    """Tập asset có calibration_status != '' (cache khác rỗng) — để reconcile thăm CẢ
    asset không-còn-trong-rollup (lịch deactivate/xóa) → stale-clear (BR-11-10)."""
    rows = frappe.db.sql(
        "SELECT name FROM `tabAC Asset` "
        "WHERE calibration_status IS NOT NULL AND calibration_status != ''",
        as_dict=True,
    )
    return {r["name"] for r in rows}
```

**Quyết định reconcile per-asset (decision table):**

| `old` (cache) | `lifecycle_status` | `derived` (SoT rollup) | → `new` | Rule |
|---|---|---|---|---|
| `Calibration Failed` | `Out of Service` | bất kỳ | `Calibration Failed` (giữ) | BR-11-11 preserve |
| `Calibration Failed` | KHÔNG Out of Service | có giá trị | `derived` | recal Pass đã đưa về Active → cho rollup tiếp quản |
| bất kỳ ≠ FAILED | bất kỳ | `Overdue`/`Due Soon`/`On Schedule` | `derived` | SoT rollup bình thường |
| `Overdue`/`Due Soon`/`On Schedule`/`Not Required` | bất kỳ (≠ OoS-FAILED) | `None` (hết active schedule) | `Not Required` | BR-11-10 stale-clear |
| `''` (rỗng) | bất kỳ | `None` | `''` (giữ rỗng) | không có gì để clear — bỏ qua, không notify |

- **Idempotency + anti-spam (giữ nguyên, mở rộng):** chỉ `set_values` + `notify_calibration_due` khi `new != old`. Cả nhánh stale-clear (Overdue→Not Required) và preserve (FAILED→FAILED) đều idempotent: lần 2 `new == old` → no-op, không notify. Reset stale (`Overdue → Not Required`) là chuyển RA khỏi Due Soon/Overdue → `notify_calibration_due` không spam (chỉ notify khi chuyển VÀO Due Soon/Overdue — xem `docs/imm-00/04_Backend_Design.md §III.1b-2`).
- **SoT count KHÔNG đổi:** `_overdue_asset_ids` / `_due_soon_asset_ids` / `_calibration_status_asset_ids` GIỮ NGUYÊN byte-for-byte. Fix CHỈ chạm write-path cache trong `check_calibration_expiry` (+ 2 helper mới `_reconcile_calibration_status`, `_nonempty_cache_asset_ids`). KPI/drill/dashboard parity (BR-11-08/09) không bị ảnh hưởng → `test_dashboard` + `test_imm11` SoT-cases không regress.
- `AC Asset.calibration_status` vẫn **chỉ là cache** hiển thị nhanh trên trang asset detail/list — KPI/drill/dashboard KHÔNG đọc nó (đọc SoT trực tiếp).

### 4.1.4 `get_calibration_kpis` / `get_dashboard` — đọc SoT

`overdue_assets = len(_overdue_asset_ids())`, `due_soon_assets = len(_due_soon_asset_ids())` (KHÔNG còn `AssetRepo.count({"calibration_status": OVERDUE})`). Danh sách overdue/due_soon top-N trong `get_dashboard` lấy theo cùng tập asset (JOIN schedule SoT) order by `next_due_date asc`. **Shape KPI/dashboard KHÔNG đổi** bởi BR-11-12 (§4.1.5) — guard chỉ chạm write-path lifecycle, không chạm read-path KPI.

### 4.1.5 `handle_calibration_pass` — restore-guard liên-module (BR-11-12)

> **BUG (Self-Correction):** nhánh `elif cal_doc.is_recalibration and current_status == OUT_OF_SERVICE: _transition_asset(asset, ACTIVE, ...)` ép Active VÔ ĐIỀU KIỆN trên mọi recal Pass. `Out of Service` là trạng thái dùng chung nhiều module → recal Pass force-restore xoá hold của Incident/Repair/PM (force-override liên-module) và đưa thiết bị chưa-an-toàn lại lâm sàng. FIX: thêm predicate `_can_restore_from_oos`, mọi nhánh ép Active-từ-OoS đi qua predicate; nhánh `Calibrating → Active` GIỮ NGUYÊN.

**Cấu trúc nhánh restore (sau khi ghi ALE `calibration_passed` + cập nhật dates):**

```python
# imm11.py — handle_calibration_pass (nhánh restore, thay block elif is_recalibration cũ)
current_status = AssetRepo.get_value(cal_doc.asset, "lifecycle_status")
# ALE 'calibration_passed' đã ghi from=to=current_status (audit luôn có record).

if current_status == AssetStatus.CALIBRATING:
    # Nhánh A — GIỮ NGUYÊN (BR đúng): Calibrating → Active (transition tự ghi ALE 'activated').
    _transition_asset(cal_doc.asset, AssetStatus.ACTIVE, cal_doc.name,
                      reason=f"Calibration passed — {cal_doc.name}")
elif current_status == AssetStatus.OUT_OF_SERVICE:
    # Nhánh B — restore CÓ ĐIỀU KIỆN (BR-11-12). MỌI ép-Active-từ-OoS đi qua predicate.
    if _can_restore_from_oos(cal_doc.asset, cal_doc):
        _transition_asset(cal_doc.asset, AssetStatus.ACTIVE, cal_doc.name,
                          reason=f"Recalibration Pass — hold hiệu chuẩn giải toả, không hold khác — {cal_doc.name}")
    else:
        # GIỮ OoS — ghi 1 ALE giữ-trạng-thái với hold-note (KHÔNG transition, KHÔNG raise).
        src = _hold_source_label(cal_doc.asset)   # 'Sự cố (IMM-12)' | 'Sửa chữa (IMM-09)' | 'Bảo trì (IMM-08)' | 'hiệu chuẩn còn hold khác'
        create_lifecycle_event(
            asset=cal_doc.asset, event_type="calibration_passed",
            actor=frappe.session.user,
            from_status=current_status, to_status=current_status,
            root_doctype=CalibrationRepo.DOCTYPE, root_record=cal_doc.name,
            notes=_oos_hold_note(cal_doc.asset, src),
        )
# else: prev ∈ {Decommissioned, …} → KHÔNG ép Active (no-raise). ALE 'calibration_passed' đầu hàm đã đủ audit.
```

> ⚠️ **Lưu ý ALE-kép:** ALE `calibration_passed` (from=to=current) đã ghi ở đầu `handle_calibration_pass` cho MỌI Pass. Nhánh giữ-OoS KHÔNG cần ghi ALE thứ 2 nếu hold-note đã được nhồi vào ALE đầu. **Quyết định BA:** nhồi `_oos_hold_note(...)` vào `notes` của ALE đầu khi prev==OoS ∧ ¬restore → đúng AC-11-16/17 "ghi 1 ALE `calibration_passed` from=OoS to=OoS + hold-note" (1 ALE, KHÔNG trùng). BE chọn 1 trong 2 cách (nhồi note vào ALE đầu HOẶC tách như snippet) miễn KẾT QUẢ = đúng 1 ALE giữ-OoS có hold-note. Test AC-11-18 đếm ALE để chặn double-write.

**Predicate `_can_restore_from_oos`:**

```python
def _can_restore_from_oos(asset: str, cal_doc) -> bool:
    """BR-11-12 — True ⟺ recal Pass được phép đưa asset Out of Service → Active.

    Điều kiện AND:
      1. Chủ-hold OoS == chuỗi hiệu chuẩn: ALE mới nhất đưa asset VÀO 'Out of Service'
         có root_doctype == 'IMM Asset Calibration' (_latest_oos_root_doctype).
      2. KHÔNG còn hold governance khác mở của asset:
         - Incident mở  : open_incident_filter() (IMM-12, lazy import)
         - Repair WO mở : open_repair_filter()   (IMM-09, lazy import)
         - PM WO OoS-finding mở: PM Work Order status NOT IN [Completed, Cancelled]
           + asset đã bị PM đẩy OoS (ALE root_doctype='PM Work Order').
    Pure read-only; KHÔNG raise. Bất kỳ điều kiện fail → False (giữ OoS).
    """
```

**Nguồn hold ↔ `root_doctype` (de-conflict liên-module):**

| Module | `root_doctype` ALE vào OoS | "đang mở" predicate | Stable contract reuse |
|---|---|---|---|
| IMM-11 (calibration) | `IMM Asset Calibration` | (chủ-hold điều kiện 1) | — |
| IMM-12 (incident) | `Incident Report` | `open_incident_filter()` | `services.imm12.open_incident_filter` (lazy import) |
| IMM-09 (repair) | `Asset Repair` | `is_repair_open()` / `open_repair_filter()` | `services.imm09.open_repair_filter` (lazy import) |
| IMM-08 (PM-finding) | `PM Work Order` | `status NOT IN [Completed, Cancelled]` | `PMWorkOrderRepo` filter |

- **Pattern B (cross-module)**: lazy-import `open_incident_filter` / `open_repair_filter` BÊN TRONG function body (tránh circular import — xem assetcore-doc Phần 3 Pattern B). Truyền `asset` (string PK), KHÔNG truyền Document.
- **No-raise (INV-11-RESTORE-1)**: predicate + nhánh restore KHÔNG raise; nếu asset đã `Decommissioned` giữa chừng, `current_status` ≠ OUT_OF_SERVICE → rơi vào nhánh else (no-op transition) → on_submit Pass luôn đóng được (AC-11-18).
- **Idempotent**: `transition_asset_status` đã guard `prev == to_status → return` (imm00.py:105) → chạy lại cùng cal Pass KHÔNG tạo ALE `activated` trùng. ALE `calibration_passed` from=to là append-only audit (1 lần / submit).
- **Grep-guard SoT (AC-11-18)**: trong `handle_calibration_pass`, KHÔNG còn nhánh `_transition_asset(..., ACTIVE, ...)` từ prev=OoS NGOÀI block `if _can_restore_from_oos(...)`. Test ràng buộc: 0 đường ép Active-từ-OoS bỏ qua predicate.

### 4.1.6 `handle_calibration_fail` — Schedule due-now write (BR-11-08b)

> **Self-Correction (RC-FAIL-DUENOW).** `handle_calibration_fail` hiện set `calibration_status=FAILED` (cache) + transition OoS + CAPA + lookback + Incident NHƯNG **không chạm `Schedule.next_due_date`**. Vì KPI/drill đếm theo SoT schedule date (BR-11-08, KHÔNG đọc cache), schedule giữ ngày-tương-lai → asset FAIL bị KPI xếp ON_SCHEDULE (mask gap). Thêm 1 write-path **trong cùng** `handle_calibration_fail` để hạ MỌI active schedule về basis-date (due-now).

**Basis-date (dùng chung PASS):**
```python
basis = cal_doc.certificate_date or cal_doc.actual_date or nowdate()
```
Đúng 1 nguồn — `handle_calibration_pass` (line ~552) advance = `basis + interval`; FAIL set = `basis` (due-now). Không drift.

**Write-path (đặt SAU `transition_asset_status(... OUT_OF_SERVICE ...)` trong `handle_calibration_fail`):**
```python
# BR-11-08b: hạ MỌI active schedule của asset về due-now (basis <= today) →
# asset rơi vào overdue/due-soon set (SoT), KHÔNG còn ON_SCHEDULE.
# Theo ASSET (không chỉ cal_doc.calibration_schedule) — asset Class B+ có thể
# có nhiều loại calibration → nhiều schedule active; tất cả phải due-now.
active_scheds, _ = CalibrationScheduleRepo.list(
    filters={"asset": cal_doc.asset, "is_active": 1},
    fields=["name"], page_size=10_000,
)
for s in active_scheds:                          # null-safe: rỗng → no-op
    CalibrationScheduleRepo.set_values(s["name"], {"next_due_date": basis})
```

**Invariants:**
- **INV-FAIL-DUENOW-1 (due-now):** sau FAIL, ∀ active schedule của asset có `next_due_date == basis <= today` → asset ∈ `_overdue_asset_ids()` (basis<today) ∪ `_due_soon_asset_ids()` (basis==today). KPI overdue_assets/due_soon_assets đếm asset; count == drill (BR-11-08).
- **INV-FAIL-DUENOW-2 (theo asset, 1 batch):** dùng `CalibrationScheduleRepo.list({asset, is_active=1})` (1 query) + loop set_values — KHÔNG N+1 trên list; KHÔNG giới hạn ở `cal_doc.calibration_schedule` (cal có thể không gắn schedule, hoặc asset có schedule loại khác).
- **INV-FAIL-DUENOW-3 (null-safe / idempotent):** 0 active schedule → loop rỗng → no-op, KHÔNG raise; CAPA + Incident + lookback (đường FAIL hiện hữu) KHÔNG đổi. Resubmit/amend cùng basis → bất biến.
- **INV-FAIL-DUENOW-4 (không ép vòng đời khác):** chỉ ghi `next_due_date`; `lifecycle_status` giữ Out of Service (do transition trên), `calibration_status` giữ FAILED (BR-11-11). KHÔNG đổi state machine, KHÔNG đổi `is_active` (schedule vẫn active → vẫn được KPI đếm).
- **INV-FAIL-DUENOW-5 (khép kín):** recalibration Pass sau đó (`handle_calibration_pass`) advance `next_due_date = basis + interval` (tương lai) → asset rời overdue/due-soon → ON_SCHEDULE. Vòng đời fail→due-now→pass→on-schedule khép kín.

**PASS không đổi bởi BR-11-08b (regression xanh):** fix BR-11-08b CHỉ thêm write-path vào nhánh FAIL; SoT `Schedule.next_due_date` của nhánh PASS (advance `= basis + interval`) byte-for-byte bất biến. ⚠️ ASSET-cache của PASS (`calibration_status` / `next_calibration_date`) ĐƯỢC sửa riêng ở **§4.1.7 (BR-11-13)** — KHÔNG do BR-11-08b; 2 fix độc lập, không trộn.

### 4.1.7 `handle_calibration_pass` — Asset-cache ROLLUP đa-lịch (BR-11-13)

> **Self-Correction (RC-PASS-ROLLUP).** `handle_calibration_pass` ghi ASSET-cache `{calibration_status: ON_SCHEDULE (hardcode), next_calibration_date: add_days(basis, interval)}` = trạng-thái/hạn của **CHỈ schedule vừa Pass**, bỏ qua active schedule KHÁC. Trong khi `check_calibration_expiry` rollup cache từ MỌI active schedule (`_calibration_status_asset_ids`, worst-of). → 2 write-path cùng ghi 1 cache field theo 2 logic ≠ → asset multi-schedule: badge "Đúng lịch" sau Pass while dashboard SoT vẫn Overdue + asset rớt khỏi `get_due_calibrations` (filter cache `next_calibration_date`). Mirror của BR-11-08b. Chi tiết RC: `02_Analysis_Design.md §BR-11-13`.

**Helper rollup (tái dùng SoT — KHÔNG copy logic):**
```python
def _asset_min_next_due(asset_name: str) -> str | None:
    """MIN(next_due_date) trên MỌI active schedule của asset (1 query bounded).
    None nếu asset không còn active schedule với next_due_date."""
    row = frappe.db.sql(
        """
        SELECT MIN(next_due_date) AS min_due
        FROM `tabIMM Calibration Schedule`
        WHERE asset = %(a)s AND is_active = 1 AND next_due_date IS NOT NULL
        """,
        {"a": asset_name}, as_dict=True,
    )
    return (row[0]["min_due"] if row and row[0]["min_due"] else None)


def _apply_asset_calibration_rollup(asset_name: str, basis: str) -> None:
    """Ghi ASSET-cache 3 field theo ROLLUP đa-lịch (BR-11-13). Gọi SAU khi schedule
    vừa Pass đã advance next_due_date (để rollup thấy date mới). CÙNG SoT
    `_calibration_status_asset_ids` mà check_calibration_expiry dùng → ROLLUP-CONSISTENCY.
    """
    status = _calibration_status_asset_ids().get(
        asset_name, CalibrationStatus.ON_SCHEDULE)   # worst-of-all; fallback ON_SCHEDULE
    min_due = _asset_min_next_due(asset_name)         # hạn gần nhất thật (MỌI active sched)
    AssetRepo.set_values(asset_name, {
        "last_calibration_date": basis,
        "next_calibration_date": min_due,             # MIN, KHÔNG next của 1 lịch
        "calibration_status": status,                 # rollup, KHÔNG hardcode ON_SCHEDULE
    })
```
> **N+1 note:** `_calibration_status_asset_ids()` là 3 set-query toàn-tập (đã có, KHÔNG per-asset loop) + `_asset_min_next_due` 1 aggregate-query → rollup 1 asset = **4 query bounded**, độc lập số schedule. Nếu BE thấy build map toàn-tập chỉ cho 1 asset là phí, có thể viết `_asset_rollup_status(asset)` chạy CÙNG predicate (`is_calibration_overdue`/`is_calibration_due_soon`) trên đúng schedule của 1 asset (≤2 query) — miễn KẾT QUẢ == `_calibration_status_asset_ids()[asset]` (INV-PASS-ROLLUP-1 là invariant chốt, không ràng buộc cách viết).

**Thay block hardcode trong `handle_calibration_pass` (services/imm11.py:563-567):**
```python
# CŨ (XÓA) — hardcode 1-lịch:
# AssetRepo.set_values(cal_doc.asset, {
#     "last_calibration_date": basis_date,
#     "next_calibration_date": next_date,
#     "calibration_status": CalibrationStatus.ON_SCHEDULE,
# })

# MỚI — ghi schedule vừa Pass TRƯỚC (advance next_due_date), RỒI rollup ASSET-cache:
CalibrationRepo.set_values(cal_doc.name, {"next_calibration_date": next_date})  # phiếu — GIỮ
if cal_doc.calibration_schedule:
    CalibrationScheduleRepo.set_values(cal_doc.calibration_schedule, {
        "last_calibration_date": basis_date,
        "next_due_date": next_date,                  # BR-11-04 — SoT schedule advance, GIỮ
    })
_apply_asset_calibration_rollup(cal_doc.asset, basis_date)  # BR-11-13 — cache rollup đa-lịch
```
> ⚠️ **Thứ tự bắt buộc:** `_apply_asset_calibration_rollup` phải chạy SAU `CalibrationScheduleRepo.set_values(...next_due_date=next_date)` để rollup đọc được date đã advance của schedule vừa Pass (nếu chạy trước, rollup thấy date cũ → sai cho happy-path 1-lịch). ALE `calibration_passed` + restore-guard 3-nhánh (§4.1.5) chạy SAU rollup, KHÔNG đổi.

**Invariants:**
- **INV-PASS-ROLLUP-1 (status == SoT):** sau PASS, `AC Asset.calibration_status == _calibration_status_asset_ids().get(asset, ON_SCHEDULE)`. Multi-schedule còn lịch overdue → `Overdue` (KHÔNG ON_SCHEDULE).
- **INV-PASS-ROLLUP-2 (next == MIN):** `AC Asset.next_calibration_date == MIN(next_due_date)` trên MỌI active schedule → asset KHÔNG rớt khỏi `get_due_calibrations` khi còn lịch sớm hơn.
- **INV-PASS-ROLLUP-3 (idempotent scheduler):** `check_calibration_expiry()` ngay sau PASS → `_reconcile_calibration_status` thấy `new == old` → no-write, no-notify (no flip-flop badge). Vì PASS-cache và scheduler-cache cùng nguồn `_calibration_status_asset_ids`.
- **INV-PASS-ROLLUP-4 (happy-path bất biến):** asset 1-lịch → schedule duy nhất sau advance có `next_due > today+30` → rollup `ON_SCHEDULE`, `MIN` = chính `basis+interval` → cache y hệt cũ (`On Schedule` + `add_days(basis, interval)`).
- **INV-PASS-ROLLUP-5 (BR-11-04/12 bất biến):** `Schedule.next_due_date` (vừa Pass) = `basis+interval`; `CalibrationRepo.next_calibration_date` set như cũ; ALE `calibration_passed` (1 record) + restore-guard 3-nhánh KHÔNG đổi. BR-11-13 CHỈ chạm 3 field ASSET-cache.
- **INV-PASS-ROLLUP-6 (no N+1):** rollup 1 asset = số query bounded (≤4), độc lập số schedule — KHÔNG loop per-schedule SQL.

---

### 4.1.8 Read-side derived flags — `is_overdue` / `is_due_soon` per record (BR-11-14)

> **Bối cảnh (server-flag SSoT — mobile-BE CR-02, MVP-flow-5).** KTV mở phiếu hiệu chuẩn trên mobile (`getCalibration`) hoặc duyệt danh sách (`listCalibrations`) cần biết NGAY phiếu này **quá hạn / sắp hạn** để ưu tiên — KHÔNG được so `next_calibration_date` với đồng-hồ-thiết-bị (client-clock drift / lệch múi giờ → KTV coi thiết bị quá hạn là còn hạn → dùng thiết bị đo chưa hiệu chuẩn trên bệnh nhân → sai số đo + vi phạm NĐ98). Cờ phải **derive SERVER-SIDE**, consumer CHỈ render. Đối xứng `calibration_overdue` của `get_asset_scan_info` (imm00, CR-21) + `is_response_breached`/`is_resolution_breached` của incident-detail (imm12, INV-SLA-5). Ref bền: `memory/overdue_server_flag_ssot.md`.

**Hành vi (dùng LẠI predicate thuần §4.1.1 — KHÔNG re-implement, KHÔNG thêm query DB):**

```python
# services/imm11.py — trong list_calibrations, VÒNG `for r in rows` đã có (imm11.py:1012-1015)
# và trong get_calibration, sau khi build `data` (imm11.py:1023-1029).
# next_calibration_date đã nằm trong fields=[...] (list) / doc.as_dict() (detail) → 0 query mới.
ref = getdate(nowdate())                       # 1 ref-date server, tính 1 lần / call
nd  = r.get("next_calibration_date")           # list: row-field ; detail: data["next_calibration_date"]
r["is_overdue"]  = int(is_calibration_overdue(nd, ref))     # bool → int 0/1
r["is_due_soon"] = int(is_calibration_due_soon(nd, ref))    # bool → int 0/1
```

- **Nguồn ngày = `next_calibration_date` của CHÍNH bản ghi hiệu chuẩn** (field `IMM Asset Calibration.next_calibration_date`), KHÔNG phải `Schedule.next_due_date` SoT của KPI/drill (`_overdue_asset_ids`). Đây là 2 câu hỏi KHÁC nhau — xem **ADR-IMM11-05**.
- **Ma trận (predicate §4.1.1 đã bảo đảm loại-trừ-lẫn-nhau):**
  | `next_calibration_date` | `is_overdue` | `is_due_soon` |
  |---|---|---|
  | `< today` (strict) | 1 | 0 |
  | `∈ [today, today + CAL_DUE_SOON_WINDOW_DAYS]` (2 biên inclusive) | 0 | 1 |
  | `> today + CAL_DUE_SOON_WINDOW_DAYS` | 0 | 0 |
  | `None` (chưa có hạn — vd phiếu Scheduled/In Progress) | 0 | 0 |

  Overdue ưu tiên: ngày `< today` bị biên-dưới của `is_calibration_due_soon` loại → 2 cờ KHÔNG BAO GIỜ cùng `1`.

**Invariants:**
- **INV-CALFLAG-1 (parity list == detail, kiểu INV-SLA-5):** với cùng bản ghi X và CÙNG ref-date, `list_calibrations` row-X.`{is_overdue,is_due_soon}` == `get_calibration(X)`.`{is_overdue,is_due_soon}`. Đảm bảo vì cả 2 gọi CÙNG predicate trên CÙNG field `next_calibration_date`, ref = `nowdate()` server. (Test cố định ref-date để loại race qua-nửa-đêm.)
- **INV-CALFLAG-2 (int, không bool):** cờ là `int` `0`/`1` (bọc `int(...)`) — mirror `is_recalibration`/`is_response_breached` (Open#1 int-vs-bool; codegen Dart/Kotlin so `== 1`, KHÔNG deser bool).
- **INV-CALFLAG-3 (no new query / no leak):** `next_calibration_date` đã được `list`/`get` trả sẵn → derive là pure-Python. KHÔNG thêm field web-only mới (2 cờ có trong CẢ mobile contract lẫn web-FE — handler dùng chung, §05 §0.1.5).

#### ADR-IMM11-05: Cờ record-level dùng `next_calibration_date` (record), KHÔNG dùng Schedule-SoT `_overdue_asset_ids`

- **Status**: Accepted
- **Date**: 2026-07-09
- **Context**: IMM-11 đã có 2 khái-niệm-ngày: (a) `IMM Calibration Schedule.next_due_date` = SoT cho KPI/dashboard/drill "**ASSET nào** quá hạn" (`_overdue_asset_ids`, de-dup theo asset, lọc active-schedule + không-decommissioned); (b) `IMM Asset Calibration.next_calibration_date` = hạn hiệu chuẩn kế tiếp ghi trên **BẢN GHI** hiệu chuẩn. `listCalibrations`/`getCalibration` trả **bản ghi**, nên cờ phải trả lời "**bản ghi này** quá hạn/sắp hạn không".
- **Decision**: Cờ `is_overdue`/`is_due_soon` cho list/detail derive từ `next_calibration_date` của CHÍNH record qua predicate chung `is_calibration_overdue`/`is_calibration_due_soon` (§4.1.1). KHÔNG join Schedule, KHÔNG gọi `_overdue_asset_ids`.
- **Alternatives bác**: (1) Map cờ record về Schedule-SoT `_overdue_asset_ids` → sai ngữ nghĩa (asset-level ≠ record-level) + thêm N query JOIN Schedule per list-page (vi phạm "KHÔNG thêm query DB"). (2) Re-implement so-ngày inline trong list/detail → nhân đôi predicate, drift `CAL_DUE_SOON_WINDOW_DAYS`.
- **Consequences**: 2 cờ record-level phản ánh đúng hạn của bản ghi (rõ nhất trên phiếu đã `Passed` có `next_calibration_date`; phiếu chưa hoàn thành → `None` → cả 2 = 0). KHÁC predicate của `get_asset_scan_info` (imm00 `_is_calibration_overdue` — **exempt-aware** theo `lifecycle_status`, asset-scoped): 2 nơi cùng "server-derived, consumer render" nhưng phạm-vi khác — KHÔNG hợp nhất (record-flag = độ-tuân-thủ-lịch của bản ghi; scan-flag = trạng-thái asset có miễn-trừ). Đối xứng về PATTERN, không về predicate.

---

### 4.1.9 `add_measurement` idempotency dedup — cache-store (BR-11-15 / CR-24-CAL)

> Mirror IMM-08 CR-24-PM (`services/imm08.py:974-1105`, `submit_result` cache-store). Đóng cửa-sổ re-drain write-outbox tạo **dòng đo TRÙNG**. **Cache-store `frappe.cache()` — KHÔNG DocField mới, KHÔNG `bench migrate`** (khác `report_incident`/CR-24 dùng cột unique + migrate).

**Hằng + helper (thêm vào `services/imm11.py`):**

```python
_CAL_MEASUREMENT_IDEMPOTENCY_TTL = 86400  # giây (24h) = cửa sổ re-drain write-outbox

def _cal_measurement_cache_key(cal_name: str, resolved_key: str) -> str:
    """Khoá cache dedup add_measurement — scoped theo (cal_name, resolved_key)."""
    return f"cal_add_measurement::{cal_name}::{resolved_key}"

def _cal_measurement_cache_get(cache_key: str) -> dict | None:
    # BẮT BUỘC expires=True: bypass layer frappe.local.cache — pre-check MISS nhét None
    # vào local, set_value(expires_in_sec) chỉ ghi Redis ⇒ re-drain CÙNG process trả
    # None-shadow nếu đọc mặc-định (mirror services/imm08.py:988-1001).
    return frappe.cache().get_value(cache_key, expires=True)

def _cal_measurement_cache_set(cache_key: str, payload: dict) -> None:
    frappe.cache().set_value(cache_key, payload, expires_in_sec=_CAL_MEASUREMENT_IDEMPOTENCY_TTL)

def _resolve_measurement_idempotency_key(client_request_id: str) -> str:
    """Nguồn khoá: param client_request_id THẮNG header X-Idempotency-Key.
    Cả hai vắng/rỗng → '' (NO-OP dedup). Header đọc case-insensitive (Werkzeug);
    alias 'Idempotency-Key' (component A6) đọc thêm, X- ưu tiên — ADR-IMM11-07."""
    if client_request_id:
        return client_request_id
    return (frappe.get_request_header("X-Idempotency-Key")
            or frappe.get_request_header("Idempotency-Key") or "")
```

**Chèn vào `add_measurement(name, *, ..., client_request_id: str = "")` (giữ nguyên body cũ, bọc dedup):**

1. `resolved_key = _resolve_measurement_idempotency_key(client_request_id)`; `cache_key = _cal_measurement_cache_key(name, resolved_key) if resolved_key else None`.
2. **Pre-check** (nếu `cache_key`): `cached = _cal_measurement_cache_get(cache_key)`; HIT (`is not None`) → **`return cached`** (đứng TRƯỚC `CalibrationRepo.get` — 0 side-effect, 0 audit).
3. Load doc (`CalibrationRepo.get`); `∄` → `nthrow(MSG.IMM11_CAL_NOT_FOUND)` (KHÔNG đổi).
4. `docstatus == 1`: nếu `cache_key` → re-read cache (winner-reread race); HIT → `return cached`; else/MISS → `nthrow(MSG.IMM11_ALREADY_SUBMITTED)` (**guard KHÔNG nới** — không-khoá luôn rơi vào nhánh này).
5. `doc.append("measurements", {...})` + `CalibrationRepo.save(doc)` (legacy y nguyên).
6. `payload = {"name": doc.name, "measurement_count": len(doc.measurements)}`.
7. Nếu `cache_key`: `_cal_measurement_cache_set(cache_key, payload)` (SAU save, TRƯỚC return).
8. `return payload`.

**Invariants (test `TC-11-IDEMP-*`):**
- **INV-IDEMP-1 (replay):** 2 call cùng key/phiếu → `count(measurements)==1`; payload#2 == payload#1 (byte); 0 save thứ-2 (append đứng SAU return-cache).
- **INV-IDEMP-2 (no-op):** key `''` → mỗi call append (count 1→2); cache KHÔNG touch (`cache_key is None`).
- **INV-IDEMP-3 (distinct keys):** `K1`≠`K2` cùng phiếu → 2 dòng.
- **INV-IDEMP-4 (source-precedence):** param thắng header; header-only → dùng header; cả hai vắng → NO-OP.
- **INV-IDEMP-5 (guard intact):** `docstatus==1` + no-key → `IMM11_ALREADY_SUBMITTED`.
- **INV-IDEMP-6 (race):** `docstatus==1` + key khớp cache → trả cached (KHÔNG lỗi); key không khớp → giữ lỗi.
- **INV-IDEMP-7 (dedup theo khoá KHÔNG theo params):** cùng key + params khác → vẫn trả cached-đầu (KHÔNG append params-mới).

> ⚠️ **Coupling BE-owned slice:** thêm param `client_request_id` vào signature `add_measurement` (api + service) ⇒ OAS `AddMeasurementRequest` phải +prop `client_request_id` (default `''`, optional, ∉ required) VÀ live-sig guard `test_mobile_oas` (`inspect.signature(imm11.add_measurement)` 7→8 param) phải cập nhật **cùng lượt** với `.py` (guard live-signature-parity, HANDLER-PARITY). ⇒ đây là slice **[BE]-owned** (mirror §8.14a IMM-08 cache-store), KHÔNG contract-only. Sửa `api/imm11.py` dưới gunicorn `--preload` ⇒ **USER reload** cho HTTP-live (HARD-STOP); DoD = `bench run-tests test_imm11` XANH (KHÔNG curl).

#### ADR-IMM11-07: `add_measurement` idempotency = cache-store `(cal_name, resolved_key)`, param `client_request_id` thắng header `X-Idempotency-Key`

- **Status**: Accepted
- **Date**: 2026-07-19
- **Context**: `add_measurement` write KHÔNG idempotent (append+save) — mobile write-outbox re-drain (mất mạng giữa request↔response) tạo dòng đo TRÙNG (CR-24-CAL / HANDOFF HIGH-2 "ca sắc nhất"). Cần dedup NHƯNG (a) KHÔNG đổi shape return `{name,measurement_count}` (Hyrum), (b) KHÔNG nới guard `IMM11_ALREADY_SUBMITTED`, (c) web-desk/client-cũ (không gửi khoá) phải y nguyên. Có 2 tiền lệ: IMM-12 `report_incident` = **DocField unique + migrate** (dedup theo bản-ghi-tạo-mới); IMM-08 `submit_result` = **`frappe.cache()` cache-store, KHÔNG migrate** (dedup replay-response cho action-on-existing-doc).
- **Decision**: chọn **cache-store** (mirror IMM-08) vì `add_measurement` là action-on-existing-doc trả response ổn định để replay (KHÔNG tạo doc mới cần cột-unique). Khoá scoped `(cal_name, resolved_key)` TTL 24h. Nguồn khoá: **param `client_request_id` (body) THẮNG** header `X-Idempotency-Key` — param là transport chính (ADR-MOBILE-047: body-field nhất quán json+form, mobile outbox thực gửi); header là forward-compat cho drain middleware-based (A6 §3). Đọc cache `expires=True`.
- **Alternatives bác**: (a) **DocField unique trên child `IMM Calibration Measurement`** → cần `bench migrate` + unique index trên child-table (phức tạp, child KHÔNG có naming ổn định), + reject phía DB thay replay-response → phải bắt `UniqueValidationError` re-read; cache-store nhẹ hơn cho action-replay. (b) **Chỉ header, bỏ param** → nghịch ADR-MOBILE-047 (form_dict header không route sạch cho codegen client) + acceptance yêu cầu param. (c) **Chỉ param, bỏ header** → mất forward-compat với drain middleware-based §9/A6. (d) **Dedup theo hash(params)** → sai hợp đồng write-outbox (1 outbox-item = 1 khoá cố định; phép đo lặp hợp lệ cùng-giá-trị sẽ bị chặn nhầm).
- **Consequences**: +param `client_request_id` signature (api+service) ⇒ OAS `AddMeasurementRequest` +prop + live-sig guard 7→8 (BE-owned coupled slice). KHÔNG DocField/KHÔNG migrate. **Naming-divergence cần reconcile:** acceptance + Stripe de-facto = `X-Idempotency-Key`; component A6 (`docs/mobile/openapi` parameter `IdempotencyKey`, `07-offline-sync §3`) hiện đặt `Idempotency-Key` (KHÔNG `X-`). BE đọc CẢ hai (`X-` ưu tiên) để robust; **backlog:** chốt 1 tên chung ở A6 component (đề xuất giữ `X-Idempotency-Key` cho path write nghiệp-vụ, hoặc cập nhật spec A6). Sửa `api/imm11.py` dưới `--preload` → USER reload (HARD-STOP). Nhất quán họ CR-24 (imm08 cache-store / imm12 DocField).

---

### 4.1.10 `update_calibration` — `measurements` child-diff replace-set (BR-11-16 / RC-MEAS-DATALOSS)

> **Self-Correction (RC-MEAS-DATALOSS).** `update_calibration` (`services/imm11.py:1122`) lọc patch qua `clean_patch = {k:v for k,v in patch.items() if k in _UPDATE_ALLOWED}`. `_UPDATE_ALLOWED` (`:1113`) là whitelist **scalar** KHÔNG có `measurements` ⇒ mảng dòng đo web gửi bị DROP CÂM (data-loss). Fix: thêm nhánh child-diff RIÊNG, giữ đường scalar bất biến khi `measurements` vắng.

**Nguồn SSoT tính `pass_fail`/`out_of_tolerance`** = parent controller `IMMAssetCalibration._compute_measurement_results()` (`assetcore/doctype/imm_asset_calibration/imm_asset_calibration.py:84-99`), gọi trong `validate()` — CHÍNH đường mà `add_measurement → CalibrationRepo.save()` đã kích hoạt. KHÔNG viết lại logic tolerance ở service.

**Chèn vào `update_calibration(name, patch)` (giữ nguyên đường scalar cũ):**

```python
# BR-11-16: tách measurements RA KHỎI patch scalar TRƯỚC bộ lọc _UPDATE_ALLOWED.
has_measurements = "measurements" in patch
raw_measurements = patch.get("measurements")           # có thể là [] (xoá hết) — vẫn hợp lệ

doc = CalibrationRepo.get(name)
if not doc:
    nthrow(MSG.IMM11_CAL_NOT_FOUND, name=name)
if doc.docstatus == 1:
    nthrow(MSG.IMM11_ALREADY_SUBMITTED)                  # 409 — measurements KHÔNG mutate
if has_measurements and doc.status not in CalibrationResult.ACTIVE_STATUSES:
    nthrow(MSG.IMM11_MEASUREMENTS_NOT_EDITABLE)          # 409 — draft Cancelled/verdict

clean_patch = {k: v for k, v in patch.items() if k in _UPDATE_ALLOWED}
if not clean_patch and not has_measurements:            # NO_FIELDS chỉ khi CẢ HAI rỗng
    nthrow(MSG.IMM11_NO_FIELDS)

# --- áp scalar (giữ hành vi cũ) + child-diff trên CÙNG doc → 1 save atomic ---
for k, v in clean_patch.items():
    doc.set(k, v)
if has_measurements:
    _MEAS_INPUT = ("parameter_name", "unit", "nominal_value",
                   "tolerance_positive", "tolerance_negative", "measured_value")
    rows = [{f: r.get(f) for f in _MEAS_INPUT} for r in (raw_measurements or [])]
    # STRIP pass_fail/out_of_tolerance/name/doctype/parent — server là SSoT verdict.
    doc.set("measurements", rows)                        # replace-set (Frappe diff: upsert+delete)
CalibrationRepo.save(doc)                                # → validate() → _compute_measurement_results (SSoT)
# ... phần asset-Calibrating side-effect + _lockstep_cal_workflow_state GIỮ NGUYÊN ...
return {"name": doc.name, "status": doc.status}          # shape KHÔNG đổi
```

> ⚠️ **Backward-compat**: khi `measurements` VẮNG, nhánh trên tương đương đường cũ (`clean_patch` áp qua doc.save) — nhưng nếu muốn byte-đối-byte đúng đường `CalibrationRepo.update_fields(name, clean_patch)` cũ, BE có thể giữ `update_fields` cho case-vắng và CHỈ chuyển sang doc-save khi `has_measurements`. Ràng buộc SPEC: **`measurements` vắng ⇒ 0 khác biệt quan sát** (AC-11-39). Latitude thuộc BE; invariant là hành vi, KHÔNG là dòng code.

**Invariants (test `TestUpdateCalibrationMeasurements`, RED→GREEN):**
- **INV-MEASDIFF-1 (persist / anti-data-loss):** `update_calibration(name,{measurements:[N]})` trên draft → `get_calibration(name).measurements` = N dòng với input-field đúng. (AC-11-34; RED hiện tại = 0 dòng.)
- **INV-MEASDIFF-2 (SSoT compute):** dòng `measured_value` ngoài ±tolerance → `pass_fail='Fail'`/`out_of_tolerance=1` dù client gửi `Pass`/`0` (strip + recompute). (AC-11-35)
- **INV-MEASDIFF-3 (replace-set count):** reload count == payload count (bỏ dòng → remove; thêm dòng → insert). (AC-11-36)
- **INV-MEASDIFF-4 (guard submit):** `docstatus==1` → `IMM11_ALREADY_SUBMITTED` (409) + child table byte-bất-biến. (AC-11-37)
- **INV-MEASDIFF-5 (guard status):** `docstatus==0` ∧ `status ∉ ACTIVE_STATUSES` → `IMM11_MEASUREMENTS_NOT_EDITABLE` (409). (AC-11-38)
- **INV-MEASDIFF-6 (backward-compat):** patch không-`measurements` ⇒ hành vi cũ; patch chỉ-`measurements` ⇒ KHÔNG `IMM11_NO_FIELDS`. (AC-11-39)
- **INV-MEASDIFF-7 (idempotent):** lưu CÙNG mảng 2 lần → cùng count (replace-set idempotent; KHÔNG cần `client_request_id`). (AC-11-40)

**Coupling: 0 OAS / 0 live-sig.** `update_calibration` dùng `**kwargs` (signature KHÔNG đổi khi thêm key `measurements`) VÀ **KHÔNG có mặt trong mobile OAS** (`docs/mobile/openapi/*.yaml` grep = 0) ⇒ KHÔNG `test_mobile_oas`/`test_mobile_docset` coupling — KHÁC `add_measurement` (BE-owned slice §4.1.9). Đây là slice **BR/service/FE thuần** (+1 MSG). Sửa `services/imm11.py` (+ nếu chạm `api/imm11.py`) dưới `--preload` → USER reload cho HTTP-live (HARD-STOP); **DoD = `bench --site miyano run-tests` module-isolated `test_imm11` XANH** (KHÔNG curl). MSG mới `IMM11_MEASUREMENTS_NOT_EDITABLE` thêm ở `utils/messages.py` (+ catalog `05 §1.3`).

#### ADR-IMM11-08: `update_calibration` `measurements` = replace-set child-diff, server-authoritative pass_fail/out_of_tolerance

- **Status**: Accepted
- **Date**: 2026-07-20
- **Context**: web `CalibrationDetailView.save()` gửi mảng `measurements` trong `updateCalibration` nhưng `_UPDATE_ALLOWED` strip nó → KTV nhập N dòng → reload 0 dòng (data-loss, RC-MEAS-DATALOSS). Cần persist bulk N dòng (thêm/sửa/xoá) trong 1 lần Lưu, server chấm Pass/Fail (KHÔNG tin client), giữ backward-compat caller scalar cũ + guard đã-submit.
- **Decision**: thêm nhánh **child-diff replace-set** trong `update_calibration` (tách `measurements` khỏi `_UPDATE_ALLOWED`): payload `measurements` = TẬP mong-muốn đầy-đủ → `doc.set("measurements", sanitized_rows)` + `doc.save()`; `pass_fail`/`out_of_tolerance` recompute qua SSoT controller `_compute_measurement_results` (CÙNG `add_measurement`), strip verdict client. Guard `docstatus==0` ∧ `status ∈ ACTIVE_STATUSES`.
- **Alternatives bác**: (a) **FE gọi `add_measurement` per-row** → chỉ append, KHÔNG diễn đạt EDIT/DELETE dòng lưới, N round-trip, append non-idempotent (cần khoá CR-24). (b) **Thêm `measurements` vào `_UPDATE_ALLOWED`** → filter scalar sẽ gán thẳng list KHÔNG qua sanitize/replace-set/SSoT → verdict client lọt + KHÔNG xoá được dòng. (c) **Upsert-only (không xoá dòng bỏ khỏi payload)** → KHÔNG khớp UX lưới "xoá dòng rồi Lưu" + invariant count==payload vỡ. (d) **Endpoint mới `set_measurements`** → thêm surface API + FE re-wire; `update_calibration` đã là đường Lưu của web-detail, tái dùng sạch hơn.
- **Consequences**: +1 nhánh service + 1 MSG (`IMM11_MEASUREMENTS_NOT_EDITABLE`), 0 DocField/0 migrate (child DocType đủ field), 0 OAS/0 live-sig (kwargs + không-mobile-mirror). Replace-set **tự idempotent** ⇒ web-outbox re-drain an toàn KHÔNG cần `client_request_id` (khác BR-11-15 append). Return `{name,status}` bất biến (Hyrum-safe); FE PHẢI re-fetch `get_calibration` để render pass_fail server (06_Frontend_Design). Mỗi lần Lưu draft cũng recompute `overall_result` (preview) — verdict thật vẫn chốt ở `submit_calibration`/`before_submit` (bất biến). `add_measurement` (mobile per-row) GIỮ NGUYÊN — 2 đường ghi phép đo song song, cùng SSoT compute.

---

### 4.1.11 `submit_calibration` idempotency dedup — cache-store, replay THẮNG state-guard (BR-11-17 / CR-24-CAL-SUBMIT — op#6 write-family CLOSURE)

> **Op CUỐI của họ CR-24 write-family** (đóng nốt sau `submit_result`/`close_work_order`/`add_measurement`/`report_incident`/`attach_*_photo`). Mirror **IMM-08 CR-24-PM `submit_result`** (`services/imm08.py:1074-1112`) — cùng hình dạng "action COMPLETION nâng `docstatus 0→1`, replay-cache **THẮNG** guard `docstatus==1`". **Cache-store `frappe.cache()` — KHÔNG DocType/DocField mới, KHÔNG `bench migrate`.** Nguồn khoá = **SHARED `assetcore.utils.idempotency.resolve_idempotency_key`** (KHÔNG helper cục-bộ như §4.1.9 — op này khép họ nên dùng thẳng util chung; imm08/09/12/00 đã dùng).

**Vì sao khác `add_measurement` (§4.1.9):** `add_measurement` append child-row (doc còn `docstatus==0`), replay đứng TRƯỚC guard nên guard hầu như không đụng. `submit_calibration` **nâng `docstatus 0→1`** — sau call#1 thành công, doc đã `docstatus==1`; call#2 CÙNG khoá phải **thắng** state-guard `IMM11_ALREADY_SUBMITTED` (đọc cache trả VERBATIM), còn call#2 **KHÔNG khoá** thì state-guard vẫn raise (backward-compat NO-OP). Đây chính là điểm "replay THẮNG state-guard".

**Hằng + helper (thêm vào `services/imm11.py`; import `from assetcore.utils.idempotency import resolve_idempotency_key`):**

```python
_CAL_SUBMIT_IDEMPOTENCY_TTL = 86400  # giây (24h) = cửa sổ re-drain write-outbox

def _cal_submit_cache_key(cal_name: str, resolved_key: str) -> str:
    """Khoá cache dedup submit_calibration — scoped theo (cal_name, resolved_key)."""
    return f"cal_submit::{cal_name}::{resolved_key}"

def _cal_submit_cache_get(cache_key: str) -> dict | None:
    # BẮT BUỘC expires=True: bypass frappe.local.cache shadow (mirror §4.1.9 / imm08:988-1001).
    return frappe.cache().get_value(cache_key, expires=True)

def _cal_submit_cache_set(cache_key: str, payload: dict) -> None:
    frappe.cache().set_value(cache_key, payload, expires_in_sec=_CAL_SUBMIT_IDEMPOTENCY_TTL)
```

**Bọc dedup quanh body `submit_calibration(name, client_request_id: str = "")` (giữ nguyên logic cũ):**

1. `resolved_key = resolve_idempotency_key(client_request_id)` (SHARED — body param thắng header `X-Idempotency-Key`/alias `Idempotency-Key`; cả hai vắng → `""`); `cache_key = _cal_submit_cache_key(name, resolved_key) if resolved_key else None`.
2. **Pre-check** (nếu `cache_key`): `cached = _cal_submit_cache_get(cache_key)`; HIT (`is not None`) → **`return cached`** (đứng TRƯỚC `CalibrationRepo.get` — 0 side-effect, 0 submit, 0 lockstep, 0 ALE).
3. Load doc (`CalibrationRepo.get`); `∄` → `nthrow(MSG.IMM11_CAL_NOT_FOUND, name=name)` (KHÔNG đổi).
4. `docstatus == 1` (**replay THẮNG state-guard**): nếu `cache_key` → re-read cache (winner-reread race — winner concurrent CÙNG khoá đã submit+cache GIỮA pre-check và đây); HIT → `return cached`; else/MISS/KHÔNG-khoá → `nthrow(MSG.IMM11_ALREADY_SUBMITTED)` (**guard KHÔNG nới** — no-key luôn rơi nhánh này = backward-compat).
5. `doc = CalibrationRepo.submit(name)` + `_lockstep_cal_workflow_state(doc.name, doc.status)` (legacy y nguyên — §3.2 dual-track lockstep).
6. `payload = {"name": doc.name, "status": doc.status, "overall_result": doc.overall_result, "next_calibration_date": str(doc.next_calibration_date or "")}`.
7. Nếu `cache_key`: `_cal_submit_cache_set(cache_key, payload)` (SAU submit+lockstep, TRƯỚC return ⇒ replay byte-đối-byte).
8. `return payload`.

**Invariants (test `TestSubmitCalibrationIdempotency` / `TC-11-IDEMP-SUBMIT-*`):**
- **INV-IDEMP-SUBMIT-1 (replay-wins-state-guard):** 2 call CÙNG khoá/phiếu → call#2 trả payload#1 byte-đối-byte, **KHÔNG raise `IMM11_ALREADY_SUBMITTED`**, `docstatus` giữ 1, KHÔNG double `_lockstep`/ALE (không re-run `CalibrationRepo.submit`).
- **INV-IDEMP-SUBMIT-2 (no-op backward-compat):** 2 call **KHÔNG khoá** (header vắng + body rỗng) → call#2 `nthrow IMM11_ALREADY_SUBMITTED` (hành vi web-desk/client-cũ y hệt hôm nay).
- **INV-IDEMP-SUBMIT-3 (dedup CHỈ đúng-khoá):** call#1 `K1` (success) → call#2 `K2` KHÁC → `nthrow IMM11_ALREADY_SUBMITTED` (KHÔNG nuốt câm re-submit khác khoá — chống dedup quá rộng).
- **INV-IDEMP-SUBMIT-4 (source-precedence):** body `client_request_id` thắng header `X-Idempotency-Key`; header-only → dùng header; cả hai vắng → NO-OP.
- **INV-IDEMP-SUBMIT-5 (not-found intact):** phiếu `∄` → `IMM11_CAL_NOT_FOUND` (pre-check MISS → get → not-found, KHÔNG bị dedup che).
- **INV-IDEMP-SUBMIT-6 (race winner-reread):** `docstatus==1` + khoá khớp cache → trả cached (KHÔNG lỗi); khoá không khớp/vắng → giữ `IMM11_ALREADY_SUBMITTED`.

> ⚠️ **Coupling BE-owned slice (KHÔNG contract-only, KHÔNG đóng ở Bước-2 doc-layer):** thêm param `client_request_id` vào signature `submit_calibration` (api + service) ⇒ live-sig guard `test_mobile_oas` TC-i (`test_mob_oas_submitcal_i_request_body_matches_live_signature`, hằng `_SUBMIT_CAL_REQUEST_PROPS`) assert `inspect.signature(imm11.submit_calibration) == {name}` **EXACT** ⇒ SẼ ĐỎ trừ khi cập nhật `_SUBMIT_CAL_REQUEST_PROPS {name}→{name, client_request_id}` (+ TC-b) **VÀ** OAS `SubmitCalibrationRequest` += prop `client_request_id` (default `''`, optional, ∉ required, `additionalProperties:false` GIỮ) — cả 3 (`.py` + OAS + guard) PHẢI land **cùng lượt** (mirror §4.1.9 / IMM-08 `submit_pm_result` CR-24-PM). Xem **Self-Correction §0.1.4-IDEMP-SUBMIT** ở `05_API_Specification.md` (acceptance "KHÔNG sửa openapi.yaml / test_mobile_oas GIỮ XANH-unchanged" là SAI căn cứ). Sửa `api/imm11.py` dưới gunicorn `--preload` ⇒ **USER reload** cho HTTP-live (HARD-STOP); DoD = `bench --site miyano run-tests` module-isolated `test_imm11` XANH (KHÔNG curl — LL-DEPLOY-07).

#### ADR-IMM11-09: `submit_calibration` idempotency = cache-store `(cal_name, resolved_key)` replay-wins-state-guard, dùng SHARED `resolve_idempotency_key`

- **Status**: Accepted
- **Date**: 2026-07-20
- **Context**: `submit_calibration` là action COMPLETION nâng `docstatus 0→1` + `_lockstep_cal_workflow_state` + (controller on_submit) handlers Pass/Fail + CAPA/asset/ALE — write KHÔNG idempotent. Mobile write-outbox re-drain (mất mạng giữa request↔response) có thể gọi LẠI ⇒ call#2 hiện tại **raise `IMM11_ALREADY_SUBMITTED`** (`services/imm11.py:1205-1206`, guard `docstatus==1`) → app coi là lỗi thật dù call#1 đã thành công (bằng chứng hiệu chuẩn ISO 17025 §7.8 / NĐ98 đã ghi). Đây là op CUỐI của họ CR-24 write-family; 2 tiền lệ: IMM-08 `submit_result` = `frappe.cache()` cache-store replay-wins-state-guard (KHÔNG migrate); IMM-12 `report_incident` = DocField unique + migrate (dedup tạo-doc-mới).
- **Decision**: chọn **cache-store mirror IMM-08 `submit_result`** — `submit_calibration` là action-on-existing-doc, replay cần **THẮNG** state-guard `docstatus==1` (khác `add_measurement` §4.1.9 replay đứng trước guard). Khoá scoped `(cal_name, resolved_key)` TTL 24h. Nguồn khoá = **SHARED `assetcore.utils.idempotency.resolve_idempotency_key`** (body `client_request_id` THẮNG header) — op này khép họ nên dùng thẳng util chung (imm08/09/12/00 đã dùng), KHÔNG copy helper cục-bộ như §4.1.9 (helper cục-bộ `_resolve_measurement_idempotency_key` = tiền lệ trước khi tách util; migrate nó sang shared = backlog riêng, KHÔNG đụng vòng này). Đọc cache `expires=True`. Cache-set SAU submit, TRƯỚC return.
- **Alternatives bác**: (a) **Nới guard `docstatus==1` → return-success-silently khi doc đã submit** (không khoá) → nuốt câm MỌI re-submit kể cả 2 KTV khác nhau bấm trùng → mất phát-hiện xung-đột (INV-IDEMP-SUBMIT-2/3 vỡ). (b) **Chỉ header, bỏ param** → acceptance yêu cầu body-param + `resolve_idempotency_key` KHÔNG đọc được body nếu signature không nhận param (Frappe `get_newargs` nuốt kwarg lạ — LL-BE-63). (c) **DocField unique** → cần `bench migrate` + doc đã `docstatus==1` (submitted) không amend dễ; cache-store nhẹ hơn cho replay action-on-existing. (d) **`**kwargs` thay param tường-minh** → live-sig guard vẫn ĐỎ (`params.keys()` có `kwargs` ≠ `{name}`) + KHÔNG né được OAS coupling; vô ích.
- **Consequences**: +param `client_request_id` signature (api+service) ⇒ **coupled slice** OAS `SubmitCalibrationRequest` +prop + guard `_SUBMIT_CAL_REQUEST_PROPS {name}→{name, client_request_id}` (TC-b + TC-i) land cùng `.py`. KHÔNG DocField/KHÔNG migrate. `SubmitCalibrationResponse`/Envelope/path/opId/verb **KHÔNG đổi** (dedup không lọt response — response shape bất biến). `oas_baseline.BASELINE_TOTAL` GIỮ (0 whitelist mới). **Self-Correction** vs acceptance: xem `05 §0.1.4-IDEMP-SUBMIT` + `ADR-IMM11-MOB-06`. Sửa `api/imm11.py` dưới `--preload` → USER reload (HARD-STOP). Nhất quán họ CR-24 (imm08 cache-store submit-family).

---

## 4b. Repository Layer

**Files:** `assetcore/repositories/calibration_repo.py` (CalibrationRepo, CalibrationScheduleRepo) ✅ LIVE

Repos live in `assetcore/repositories/` (not inline in services/imm11.py). Service imports:
```python
from assetcore.repositories.calibration_repo import CalibrationRepo, CalibrationScheduleRepo
from assetcore.repositories.asset_repo import AssetRepo, DeviceModelRepo, CapaRepo
```

Key repo methods used by service: `get`, `create`, `list`, `set_values`, `update_fields`, `submit`, `save`, `delete`, `exists`, `count`, `find_one`.

Idempotency guard in `create_due_calibration_wos`: checks `CalibrationRepo.exists({calibration_schedule: s.name, status: ("in", ACTIVE_STATUSES)})` before inserting.

---

## 5. API Layer

**File:** `assetcore/api/imm11.py` ✅ LIVE — imports from `assetcore.utils.helpers` (`_ok`, `_err`)

**Actual @frappe.whitelist functions (see 05_API_Specification.md for full specs):**

| Function | Method | Description |
|---|---|---|
| `list_calibration_schedules(filters, page, page_size)` | GET | List schedules with pagination |
| `get_calibration_schedule(name)` | GET | Single schedule |
| `create_calibration_schedule(asset, calibration_type, interval_days, preferred_lab, next_due_date)` | POST | Create schedule |
| `update_calibration_schedule(name, **kwargs)` | POST | Update schedule fields |
| `delete_calibration_schedule(name)` | POST | Delete (if no submitted cals) |
| `list_calibrations(filters, mine, page, page_size)` | GET | List calibrations with pagination (+ `mine=1` self-scope `technician` — §5.1) |
| `get_calibration(name)` | GET | Single calibration detail |
| `create_calibration(asset, calibration_type, scheduled_date, technician, ...)` | POST | Create calibration WO |
| `update_calibration(name, **kwargs)` | POST | Update allowed scalar fields **+ `measurements` child-diff replace-set** (BR-11-16 / §4.1.10 — server-compute pass_fail, guard `docstatus==0`∧`status∈ACTIVE_STATUSES`) |
| `submit_calibration(name)` | POST | Submit (triggers Pass/Fail handler) |
| `add_measurement(name, parameter_name, unit, nominal_value, ...)` | POST | Add measurement row |
| `get_calibration_kpis(year, month)` | GET | Monthly KPI report |
| `get_calibration_dashboard()` | GET | Full dashboard (KPIs + lists) |
| `get_asset_calibration_history(asset, limit)` | GET | Asset calibration history |
| `send_to_lab(name, sent_date, lab_supplier, lab_contract_ref)` | POST | External: → Sent To Lab |
| `receive_certificate(name, certificate_file, certificate_number, certificate_date, ...)` | POST | External: → In Progress |
| `cancel_calibration(name, reason)` | POST | Cancel pre-submit |
| `get_due_calibrations(days, limit)` | GET | Assets due ≤ N days |

> **Pattern:** All responses via `_ok(data)` / `_err(msg, code)` from `assetcore.utils.helpers`. HTTP always 200. Service raise `ServiceError(ErrorCode.X, "msg tiếng Việt")` caught by `_handle()`.

> ⚡ **VERB-FLIP `add_measurement` (R34 — ADR-IMM11-MOB-03 / ADR-MOBILE-011, xem `05_API_Specification.md §0.1.4`):** cột Method = **POST** ở trên là verb-INTENT (write-action: append child-row, KHÔNG idempotent). Decorator THẬT `api/imm11.py:120` hiện **bare `@frappe.whitelist()`** (nhận cả GET — verb-parity gap R33 BỎ SÓT). **Fix R34 = flip ĐÚNG 1 dòng** `api/imm11.py:120` → `@frappe.whitelist(methods=['POST'])` (signature `:121-123` + body `:124-132` + `rbac.require('calibration.write')` `:124` UNCHANGED; `git diff api/imm11.py` = 1 dòng decorator). Mirror `create_calibration` `:89` / `submit_calibration` `:114` (đã flip @R33). Sau flip POST-only ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()`. Cần USER reload gunicorn `--preload` để LIVE reject GET(405) — guard in-process KHÔNG cần (HARD-STOP USER).

---

### 5.1 Mobile-BE contract — `listCalibrations` self-scope `mine` (đóng-nốt quartet phiếu-của-tôi: tab "Phiếu hiệu chuẩn của tôi" MVP-5d)

**Vấn đề gốc (contract nói dối — đối-xứng A2 known-gap):** OpenAPI `listCalibrations` summary `[MVP-5d] Hiệu chuẩn của tôi` ĐÃ hứa semantics "của tôi", NHƯNG `list_calibrations(filters, page, page_size)` (`api/imm11.py:71`) **KHÔNG có cơ chế** scope theo `technician` — chỉ `parse_json(filters)` (`:72-75`, in-try/except → `_err` Error-trên-HTTP-200) + `apply_vendor_scope("Calibration Record")` (`:76`) rồi `handle(svc.list_calibrations, …)` (`:77`). ⇒ tab trả **mọi** Calibration Record mà quyền đọc cho phép (kể cả phiếu giao KTV khác), KHÔNG self-scope. Đối-xứng PM (ADR-MOBILE-016) / CM (ADR-MOBILE-017) / Incident (ADR-MOBILE-015) — đây là **mắt-xích THỨ TƯ đóng-nốt quartet** phiếu-của-tôi của MyWorkOrdersView.

**5-câu-hỏi domain:** (stage HTM) Operation/Maintenance — calibration/performance; (NĐ98) traceability hiệu chuẩn gắn ĐÚNG KTV thực hiện (chứng chỉ truy được người chịu trách nhiệm); (stakeholder) KTV field-tech mobile + Calibration Manager/QA web; (lifecycle event) calibration tạo với `technician` reqd (`services/imm11.py:1052`); (hậu quả nếu data sai) tab hiển thị phiếu người khác → KTV nhầm việc, nhưng **KHÔNG leak quyền** vì read-gating GIỮ DocPerm — `mine` chỉ là filter hiển thị.

| Khía cạnh | Quyết định | Evidence |
|---|---|---|
| Param | `mine: int = 0` (`0\|1`), chèn GIỮA `filters`↔`page` (mirror `imm08.py:29` / `imm09.py:22`); inject @api SAU `apply_vendor_scope("Calibration Record")`, TRƯỚC `handle(svc.list_calibrations)` | `api/imm11.py:71,76-77` |
| Injection | `if int(mine or 0): f["technician"] = frappe.session.user` — **cột `technician`** (KHÁC PM/CM `assigned_to`) | `imm_asset_calibration.json:131` (Link `User`, reqd) |
| count==rows | `count_with_or` + `get_all` (`BaseRepository.list base.py:65-71`) dùng CÙNG `filters` dict (đã có `technician`); list_calibrations KHÔNG truyền `or_filters` ⇒ `count_with_or`=`frappe.db.count` thuần. Calibration Record **KHÔNG có** `permission_query_conditions` riêng ⇒ KHÔNG có nhánh count/rows lệch | `repositories/base.py:48-76`, `hooks.py:388` |
| Backward-compat | `mine=0`/absent ⇒ `filters` BYTE-IDENTICAL baseline (web-FE `CalibrationListView` KHÔNG đổi) | — |
| Contract | OpenAPI REUSE `components/parameters/WorkOrderMine` (R38) — **0 component mới**; param-set `{WorkOrderFilters,Page,PageSize}`→+`WorkOrderMine`=4; path-count GIỮ 47 | `docs/mobile/openapi/assetcore-mobile.openapi.yaml`, `docs/mobile/ADR-MOBILE-019.md` |

**Boundaries:**

| | |
|---|---|
| **Always** | `mine` ANDed với mọi key trong `filters` JSON-blob (vd `{"status":"Scheduled"}`, `{"calibration_type":"External"}`). Inject `technician=session.user` @api SAU `apply_vendor_scope`. count==rows giữ (cùng filters dict). `mine=0`/absent = baseline byte-identical. REUSE `WorkOrderMine` (KHÔNG component mới). Signature LIVE `['filters','mine','page','page_size']`. |
| **Never** | KHÔNG inject `assigned_to` (Calibration Record không có cột này — PHẢI `technician`). KHÔNG tạo component `CalibrationMine` (shape trùng `WorkOrderMine`). KHÔNG thêm endpoint `list_my_calibrations` (+path). KHÔNG auto-scope qua `permission_query_conditions` (Calibration hiện KHÔNG có; thêm sẽ vỡ view Manager/QA). KHÔNG coi `mine` là security-boundary (read-gating vẫn DocPerm `calibration.read` + `apply_vendor_scope`). KHÔNG đụng `services/imm11.py`/`repositories/`. |

**ADR-IMM11-LISTMINE — `listCalibrations` self-scope qua param opt-in `mine` (REUSE `WorkOrderMine`, inject cột `technician` @api SAU `apply_vendor_scope`)**

- **Status:** Accepted · **Date:** 2026-06-29 · đối-xứng ADR-MOBILE-016/017 (PM/CM) — xem mobile `docs/mobile/ADR-MOBILE-019.md`.
- **Context:** `list_calibrations` summary hứa "của tôi" nhưng không có cơ chế scope `technician` (claim suông). Tab "Phiếu hiệu chuẩn của tôi" (MVP-5d) cần self-scope. `WorkOrderMine` đã tồn tại từ R38 (PM) — cùng shape int 0|1. CAL filters là JSON-blob `parse_json` @api (như PM/CM, KHÁC imm12 discrete).
- **Decision:** REUSE `WorkOrderMine` + `$ref` vào `listCalibrations.parameters` + generalize description (PM/CM→PM/CM/CAL, ghi rõ cột scope khác theo list); `api/imm11.py` thêm `mine: int = 0` GIỮA filters↔page + `if int(mine or 0): f["technician"]=frappe.session.user` SAU `apply_vendor_scope`. KHÔNG đụng service/repo.
- **Alternatives (rejected):** (a) inject `assigned_to` mirror PM/CM — SAI source (Calibration Record không có cột `assigned_to`, KTV = `technician`); (b) endpoint riêng — +path, nhân đôi enrich (asset_name/lab_name/technician_name); (c) component `CalibrationMine` mới — shape trùng `WorkOrderMine`, vỡ "0 component mới"; (d) `permission_query_conditions` auto-scope — Calibration hiện không có, thêm sẽ vỡ view Manager/QA cần thấy tất cả; (e) seed @service — CAL filters parse @api, inject @api blast-radius nhỏ hơn.
- **Consequences:** contract trung thực; `mine=0` backward-compat đo được; count==rows giữ; path-count 47 + 0 component mới ⇒ `generate_spec` get/post/total UNCHANGED (`test_oas_d12/d15/d17` re-verify, KHÔNG re-baseline). **Quartet phiếu-của-tôi ĐÓNG TRỌN** (Incident/PM/CM/Calibration). Ghi rõ tiền-lệ "1 component `WorkOrderMine`, cột scope per-op khác" — param shape là contract, column-mapping (`assigned_to`/`technician`/`reported_by`) là chuyện @api-handler. `mine` = filter ứng-dụng KHÔNG-phải-security-boundary.

---

## 6. Audit Trail

| Trigger | Entry type | Actor | Payload |
|---|---|---|---|
| Schedule tạo từ IMM-04 | `calibration_scheduled` | System | `{sched_name, asset, interval}` |
| Bàn giao lab | `calibration_sent_to_lab` | KTV | `{cal_name, lab_supplier, sent_date}` |
| Nhận chứng chỉ | `certificate_received` | KTV | `{cal_name, certificate_date, certificate_number}` |
| Submit Pass | `calibration_completed` | KTV | `{cal_name, overall_result, next_calibration_date}` |
| Submit Fail | `calibration_failed` | System | `{cal_name, capa_ref, lookback_count}` |
| CAPA Closed + recal | `calibration_conditionally_passed` | System | `{capa_ref, new_cal_name}` |

**Hash chain:** SHA-256(canonical JSON payload + `prev_hash`). Verify qua `imm00.verify_audit_chain()`.

---

## 7. Background jobs / Scheduler

| Job | Tần suất | Hook | Mục đích |
|---|---|---|---|
| `create_due_calibration_wos` | Daily 06:00 | `scheduler_events.daily` | Tạo draft CAL WO cho Schedule due ≤ 30 ngày |
| `check_calibration_expiry` | Daily 06:30 | `scheduler_events.daily` | Rollup cache `calibration_status` từ SoT schedule (§4.1.3); notify khi chuyển VÀO Due Soon/Overdue (anti-spam, chỉ khi status đổi) |
| `check_capa_overdue` (IMM-00) | Daily 02:00 | IMM-00 | CAPA Open > due_date → Overdue + email QA |

**hooks.py registration (actual `assetcore/hooks.py`):**

```python
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            "assetcore.services.imm11.create_calibration_schedule_from_commissioning",
            "assetcore.services.imm16.eval_imm04_realtime",
        ],
    },
    "IMM Asset Calibration": {
        "on_submit": "assetcore.services.imm16.eval_imm11_realtime",
    },
    # Note: `create_post_repair_calibration` KHÔNG dùng doc_events.
    # IMM-09 service tự gọi nó qua Pattern B (direct service-to-service lazy import)
    # trong `services/imm09.py`.
}

scheduler_events = {
    "daily": [
        "assetcore.services.imm11.create_due_calibration_wos",   # threshold 30 days
        "assetcore.services.imm11.check_calibration_expiry",     # Overdue/DueSoon/OnSchedule
    ],
}
```

---

## 8. Integration

### Module nội bộ

| Module | Chiều | Trigger | Function |
|---|---|---|---|
| IMM-04 Installation | IN | `Asset Commissioning` doc_events.on_submit (hooks.py) | `create_calibration_schedule_from_commissioning()` |
| IMM-09 Repair | IN | `services/imm09.py` gọi trực tiếp (Pattern B lazy import, không qua hooks.py) | `create_post_repair_calibration(asset_name)` |
| IMM-00 Foundation | OUT | Mọi action nghiệp vụ | `transition_asset_status`, `create_capa`, `log_audit_event`, `create_lifecycle_event` |
| IMM-12 Incident | OUT | Cal Fail → auto-create Incident | `imm12.report_incident(fault_code="CAL_FAIL")` — non-blocking |
| IMM-16 Compliance | OUT | `IMM Asset Calibration.on_submit` (hooks.py doc_events) | `imm16.eval_imm11_realtime` — cập nhật compliance scorecard sau mỗi submit |

---

## 9. Migration & Patch

| Sprint | Patch | Path |
|---|---|---|
| 11.1 | Create IMM Calibration Schedule DocType | `assetcore/patches/v3/001_create_imm_calibration_schedule.py` |
| 11.1 | Create IMM Asset Calibration + Measurement DocType | `assetcore/patches/v3/002_create_imm_asset_calibration.py` |
| 11.1 | Custom fields on AC Asset (calibration_status, last/next_calibration_date) | `assetcore/patches/v3/003_add_calibration_fields_to_ac_asset.py` |
| 11.4 | Workflow JSON fixture | fixtures, không cần patch |
| 11.4 | Permission fixtures | `assetcore/fixtures/imm11_permissions.json` |

---

## 10. Non-functional

**Concurrency:** Frappe `modified` check (optimistic lock) — `TimestampMismatchError` → `ServiceError(CONFLICT, "Record đã được cập nhật bởi người dùng khác")`.

**Idempotency:** Scheduler `create_due_calibration_wos` kiểm tra `has_open_calibration()` trước khi insert — safe to retry.

**Caching:** Dashboard KPI cache TTL = 5 phút. Invalidate khi có IMM Asset Calibration Submit mới.

**Logging:** `frappe.logger("imm11")` với `request_id` + actor + `cal_name`.

---

## DoD — File 04 hoàn chỉnh

- [x] DocType nêu đầy đủ trường + naming + permissions sơ bộ
- [x] Quan hệ liên DocType rõ
- [x] Workflow states + transitions định nghĩa
- [x] Mọi mutation map về 1 service function (type hints)
- [x] Repository layer liệt kê method (`get`, `list`, `get_active_schedule`, `has_open_calibration`)
- [x] Mọi error raise qua `ServiceError(ErrorCode.X, msg tiếng Việt)`
- [x] API layer dùng `_handle / _ok / _err` envelope
- [x] Audit trail entry liệt kê đủ trigger
- [x] Background job đăng ký rõ
- [x] Integration nội bộ liệt kê
- [x] Patch path xác định
- [x] ✅ Implemented — `services/imm11.py` + `api/imm11.py` + DocType JSONs exist
- [ ] Reviewed bởi BE Lead + DBA
