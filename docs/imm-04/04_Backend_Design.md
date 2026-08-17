# 04 — Thiết kế Backend (Backend Design)

| Mục | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phạm vi | Per-module |
| Owner | Tech Lead / BE Lead |
| Liên kết | 02 Analysis & Design · 03 Diagrams · 05 API |

> **Mục đích**: Hợp đồng giữa Tech Lead và BE Dev — implementation chi tiết: DocType, workflow, hooks, service, scheduler, audit, integration, patches.

---

## 1. Tổng quan kiến trúc

Bám 3-tier strict: **API → Service → DocType → ORM**.

```
HTTP Request
      │
      ▼
API Layer  (assetcore/api/imm04.py — 33 endpoints)
      │   _ok / _err envelope; permission check; payload parse
      ▼
Service Layer  (assetcore/services/imm04.py)
      │   business rules, gates, lifecycle event logging
      ▼
Controller  (assetcore/doctype/asset_commissioning/asset_commissioning.py)
      │   before_insert / before_save / validate / on_submit / on_cancel
      ▼
Frappe ORM → MariaDB
      │
      ▼
Side Effects:
  • AC Asset insert (create_ac_asset — trong services/imm04.py)
  • Document transfer sang IMM-05 (_transfer_commissioning_documents_to_asset)
  • Depreciation schedule (services/depreciation.generate_schedule)
  • Realtime publish (imm04_asset_released)
  • Lifecycle Event row (immutable VR-06)
```

> **Quy ước ngôn ngữ BE:**
> - Code (function, class, variable): **tiếng Anh** snake_case / PascalCase
> - DocType **fieldname**: tiếng Anh (`vendor_serial_no`, `board_approver`)
> - DocType **field label** (Frappe form): **tiếng Việt** (`Số serial NCC`, `Người phê duyệt BGĐ`)
> - **Enum value**: tiếng Anh (`Clinical Release`); label tiếng Việt qua i18n
> - Naming series: tiếng Anh + số (`ACC-.YY.-.MM.-.#####`)
> - DTO mirror FE TypeScript types 1-1 — sai lệch = bug

---

## 2. Domain Model — DocType

### 2.1 `Asset Commissioning`

**Autoname:** `ACC-.YY.-.MM.-.#####` | **is_submittable:** 1 | **track_changes:** 1 | **track_views:** 1

**Workflow:** `IMM-04 Workflow` (state field: `workflow_state`)

| Trường | Type | Required | Default | Validation |
|---|---|---|---|---|
| `workflow_state` | Link Workflow State | — | Draft | read_only |
| `po_reference` | Link AC Purchase | YES | — | PO exists + not Cancelled |
| `master_item` | Link IMM Device Model | YES | — | device model exists |
| `vendor` | Link AC Supplier | YES | — | exists |
| `clinical_dept` | Link AC Department | YES | — | exists |
| `expected_installation_date` | Date | YES | — | ≥ today |
| `reception_date` | Date | — | today() auto-set | ≤ today |
| `installation_date` | Datetime | — | auto khi Installing | read_only |
| `vendor_serial_no` | Data | YES (Identification) | — | UNIQUE (VR-01) |
| `internal_tag_qr` | Data | — | auto-sinh BV-DEPT-YYYY-SEQ | read_only |
| `is_radiation_device` | Check | — | 0 | read_only, fetch_from item |
| `risk_class` | Select A/B/C/D/Radiation | — | — | VR-05 warning khi đổi |
| `board_approver` | Link User | YES (before Clinical Release) | — | G06 — cấp atomic qua `transition_state(…, board_approver=…)` khi transition CR-bound (BR-04-12, §5.4); 4-eyes SoD |
| `qa_license_doc` | Attach | COND | — | reqd nếu radiation (VR-07) |
| `final_asset` | Link AC Asset | — | — | set by create_ac_asset() on submit |
| `baseline_tests` | Table Commissioning Checklist | YES | — | G03: 100% Pass/N/A |
| `commissioning_documents` | Table Commissioning Document Record | — | — | G01: mandatory Received/Waived |
| `lifecycle_events` | Table Asset Lifecycle Event | — | — | VR-06: immutable ⚠️ field in field_order but missing from JSON fields array — add definition manually |
| `docstatus` | Int | — | 0 | 0=Draft, 1=Submitted, 2=Cancelled |

**Naming series:** `ACC-.YY.-.MM.-.#####` (YY=năm 2 số, MM=tháng 2 số)

**Permissions sơ bộ:**

| Role | Create | Read | Write | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| HTM Technician | ✓ | ✓ | ✓ | — | — | — |
| Biomed Engineer | — | ✓ | ✓ | — | — | — |
| Workshop Head | — | ✓ | — | ✓ | ✓ | ✓ |
| VP Block2 | — | ✓ | — | ✓ | ✓ | — |
| QA Risk Team | — | ✓ | ✓ | — | — | — |

**Indexes DB:**
- `po_reference` — search_index
- `vendor_serial_no` — search_index (khuyến nghị thêm UNIQUE)
- `workflow_state` — in_standard_filter
- Composite (khuyến nghị): `(workflow_state, docstatus, reception_date)`

---

## 3. Workflow

**File fixture:** `assetcore/assetcore/workflow/imm_04_workflow.json`
**Workflow name:** `IMM-04 Workflow`
**workflow_state_field:** `workflow_state`

**States — tên chính xác trong workflow_state field:**

> Lưu ý: workflow_state values dùng **space** (không phải underscore) — xác nhận từ `imm_04_workflow.json`, `services/imm04.py` constants, và `types/imm04.ts` (`WorkflowState` enum). Tech debt naming đã được resolve.

| workflow_state value | Style | docstatus | Gate |
|---|---|---|---|
| `Draft` | Success | 0 | — |
| `Pending Doc Verify` | Warning | 0 | G01 |
| `To Be Installed` | Success | 0 | G02 |
| `Installing` | Success | 0 | — |
| `Identification` | Success | 0 | VR-01 |
| `Initial Inspection` | Success | 0 | G03 |
| `Non Conformance` | Warning | 0 | — |
| `Clinical Hold` | Warning | 0 | G04 |
| `Re Inspection` | Success | 0 | — |
| `Clinical Release` | Success | 1 | G05+G06+GW-2 (terminal) |
| `Return To Vendor` | Danger | 1 | terminal negative |

Service code constants: `_STATE_CLINICAL_RELEASE = "Clinical Release"`, `_STATE_INITIAL_INSPECTION = "Initial Inspection"`, `_STATE_RE_INSPECTION = "Re Inspection"`, `_TERMINAL_STATES = {"Clinical Release", "Return To Vendor"}` — đồng bộ giá trị space giữa service layer, workflow config, và FE types.

**Overdue-SLA SoT (BR-04-10):** `OVERDUE_DAYS = 30` là **module-constant** (KHÔNG inline literal 30 ở ≥2 nơi). Date-anchor chốt = `reception_date` (theo KPI-04-01). Một helper SoT duy nhất:

```python
OVERDUE_DAYS = 30  # SLA threshold — single source, no inline literal
_OVERDUE_ANCHOR = "reception_date"  # date-anchor chốt (Core Doc KPI-04-01 §I.5)

def overdue_commissioning_filter(today: str | None = None) -> dict:
    """SoT predicate cho 'phiếu quá hạn SLA' — dùng chung scheduler + KPI + list drill.

    Trả filter dict thuần (frappe.db filter syntax) để cả 3 call-site cùng một định nghĩa.
    """
    cutoff = add_days(today or nowdate(), -OVERDUE_DAYS)
    return {
        _OVERDUE_ANCHOR: ("<", cutoff),
        "workflow_state": ("not in", list(_TERMINAL_STATES)),
        "docstatus": ("!=", 2),
    }
```

> ⚠️ Self-Correction (vòng 32): `get_dashboard_stats().overdue_sla` trước đây dùng `expected_installation_date` + `docstatus != 2`, còn `check_commissioning_overdue` dùng `reception_date` + `docstatus = 0` → **divergence**. Hợp nhất về `overdue_commissioning_filter()` (anchor `reception_date`, `docstatus != 2`) cho cả 3 call-site. Lưu ý hệ quả: scheduler cũ chỉ alert Draft (`docstatus=0`); SoT mới gồm cả phiếu đã Submit chưa terminal (`docstatus != 2`) — đúng định nghĩa "phiếu chưa Clinical Release vẫn đang chạy SLA". `_send_overdue_alert` tính `days_open = date_diff(nowdate(), <reception_date>)` từ **cùng anchor**.

**Transitions (rút gọn từ codebase `imm_04_workflow.json`):**

| From → To | Ghi chú |
|---|---|
| `Draft` → `Pending Doc Verify` | Gửi kiểm tra tài liệu |
| `Pending Doc Verify` → `To Be Installed` | Xác nhận đủ tài liệu |
| `Pending Doc Verify` → `Draft` | Yêu cầu bổ sung |
| `To Be Installed` → `Installing` | Bắt đầu lắp đặt |
| `To Be Installed` → `Non Conformance` | Báo cáo sự cố trước lắp đặt |
| `Installing` → `Identification` | Lắp đặt hoàn thành |
| `Installing` → `Non Conformance` | Báo cáo DOA |
| `Identification` → `Initial Inspection` | Bắt đầu kiểm tra |
| `Initial Inspection` → `Clinical Release` | Phê duyệt phát hành |
| `Initial Inspection` → `Clinical Hold` | Giữ lâm sàng |
| `Clinical Hold` → `Clinical Release` | Gỡ giữ lâm sàng |
| `Non Conformance` → `Return To Vendor` | Trả lại NCC |

> Bảng trên **rút gọn** (12/15 cạnh). File `imm_04_workflow.json` = **11 state, 71 transition-row → 15 cạnh distinct** (`(state, action, next_state)`). Verify: `python3 -c "import json;print(len(json.load(open('assetcore/assetcore/workflow/imm_04_workflow.json'))['transitions']))"` = **71** (45 → **71 transition-row** (2026-07-22, ADR-CORE-01: +26 row cấp transition cho `Commissioning Manager`/`Commissioning User` — 2 vai trò CÓ DocPerm write/submit nhưng trước đó vắng mặt ở MỌI transition; **số cạnh distinct GIỮ 15**)). 3 cạnh không có trong bảng rút gọn: `Non Conformance → To Be Installed` (Khắc phục xong), `Re Inspection → Clinical Release` (Phê duyệt sau tái kiểm), `Initial Inspection → Re Inspection` (Báo cáo lỗi baseline) — có đủ ở State Machine `02 §IV.3`.

### 3.1. INVARIANT — Workflow-Surface Integrity (CR-WF-04-SURFACE · silent-CTA-loss guard)

**Bối cảnh (silent-CTA-loss).** Mọi nút hành động nghiệm thu (CTA) trên FE sinh từ `allowed_transitions`, trả về bởi service `_get_workflow_transitions(doc_name)` (`services/imm04.py:723`). Hàm resolve workflow bằng **hằng lookup literal**, trong khối `try … except`:

```python
# services/imm04.py:34, 667-680  (ground truth — CR này KHÔNG được sửa)
_DT = "Asset Commissioning"                          # == workflow.document_type

def _get_workflow_transitions(doc_name: str) -> list[dict]:
    user_roles = frappe.get_roles(frappe.session.user)
    current_state = frappe.db.get_value(_DT, doc_name, "workflow_state")
    try:
        workflow = frappe.get_doc("Workflow", "IMM-04 Workflow")   # ← hằng lookup :671
    except frappe.DoesNotExistError:
        return []                                                  # ← silent CTA loss
    return [
        {"action": t.action, "next_state": t.next_state, "allowed_role": t.allowed}
        for t in workflow.transitions
        if t.state == current_state and t.allowed in user_roles
    ]
```

**Lỗ hổng.** Nếu ai đó (a) rename Workflow trong `imm_04_workflow.json` / `fixtures/workflow.json`, (b) đổi hằng lookup `"IMM-04 Workflow"` @:671 sang giá trị khác, hoặc (c) drift `_DT` khỏi `document_type` của workflow → `frappe.get_doc` raise `DoesNotExistError` → `return []` **CÂM** → toàn bộ CTA nghiệm thu biến mất, **KHÔNG test nào bắt**. Guard toàn cục `test_workflow_admin_override` **KHÔNG bắt**: nó `glob` file JSON (`assetcore/assetcore/workflow/*.json`) và đọc bất kỳ `name` nào có trong file để kiểm admin-role — **không hề biết hằng-lookup của service** ⇒ rename lọt câm.

**Invariants (regression-lock ở TẦNG MODULE — bổ sung, KHÔNG thay guard toàn cục):**

| ID | Invariant | Ground |
|---|---|---|
| **INV-04-WF-1** (resolve + document_type) | `frappe.get_doc("Workflow", "IMM-04 Workflow")` KHÔNG raise **VÀ** `workflow.document_type == assetcore.services.imm04._DT` (`== "Asset Commissioning"`). Bắt cả rename lẫn drift `_DT`. | `services/imm04.py:34,727` |
| **INV-04-WF-2** (admin-override mọi cạnh) | MỌI distinct `(state, action, next_state)` trong `imm_04_workflow.json` (**71 transition-row → 15 cạnh distinct**) có `"AssetCore Super Admin"` ∈ tập `allowed`. QTV duyệt được mọi cạnh nghiệm thu. Verified 15/15 (2026-07-14). | `imm_04_workflow.json` |
| **INV-04-WF-3** (live-wiring emit⊆file) | `_get_workflow_transitions(<phiếu Draft>)` gọi bởi `AssetCore Super Admin` → list **KHÁC rỗng**, và **mọi** `entry.next_state ∈` tập Draft-out next_states parse từ file (`{"Pending Doc Verify"}`). Emit service khớp file, không stale. | `services/imm04.py:723` ⇄ file |
| **INV-04-WF-4** (không false-permissive) | User **role-nghèo** (không role nào ∈ `allowed` của cạnh Draft-out) → `_get_workflow_transitions` trả **subset chặt** (⊆ tập của Super Admin, thường rỗng). CTA không rò rỉ vượt quyền. | filter `t.allowed in user_roles` |

**Boundaries.**
- **Always:** guard là **test-only** (module `assetcore.tests.imm04.test_imm04`), 0 chạm runtime `.py` → 0 reload / 0 migrate. Đọc hằng qua `import assetcore.services.imm04` + parse-file JSON (oracle độc lập), assert THẬT trên workflow **live** (DB) + emit service **live**.
- **Never:** KHÔNG "sửa" hành vi `return []` trong core ở CR này (giữ nguyên `services/imm04.py:723-736`). KHÔNG nới lộ quyền / hardcode để test xanh giả. KHÔNG dựa vào `test_workflow_admin_override` để phủ lỗ này.
- **[ROADMAP] observability (tách khỏi core — HARD-STOP USER):** thay `return []` câm bằng `frappe.log_error(...)` trước khi return để lỗi **quan-sát-được** là **thay đổi runtime** → cần reload worker → **KHÔNG auto-apply** trong CR test-only này. Ghi backlog, chờ USER quyết.

### ADR-IMM-04-01: Guard workflow-surface ở TẦNG MODULE thay vì mở rộng guard toàn cục

- **Status:** Accepted · **Date:** 2026-07-14
- **Context:** `test_workflow_admin_override` (guard toàn cục) đảm bảo mọi cạnh của mọi workflow có admin-role, nhưng nó **glob file JSON theo `name`** — không biết hằng-lookup literal `"IMM-04 Workflow"` mà service `_get_workflow_transitions` dùng để `get_doc`. Rename workflow, đổi hằng lookup, hoặc drift `_DT` ⇒ `except DoesNotExistError: return []` nuốt lỗi ⇒ mất CÂM toàn bộ CTA nghiệm thu, 0 test bắt.
- **Decision:** Thêm guard **module-local** `TestImm04WorkflowSurfaceIntegrity` trong `test_imm04` khoá 4 invariant INV-04-WF-1..4 — couple **hằng-lookup service ⇄ workflow live (DB) ⇄ file JSON ⇄ emit `_get_workflow_transitions`**. Đổi bất kỳ đầu nào (hằng @:671 sai HOẶC `name` trong `imm_04_workflow.json`) → guard FAIL (RED-before/GREEN-after).
- **Alternatives (loại):** (1) Mở rộng `test_workflow_admin_override` đọc hằng service — loại: guard toàn cục phải app-agnostic (multi-app site), không nên nhét literal per-module. (2) Bỏ hằng literal, đọc `document_type`→lookup động — loại: đổi runtime `.py` (reload/HARD-STOP), ngoài scope test-only. (3) `log_error` thay `return []` — loại khỏi core CR này (runtime change → HARD-STOP USER), giữ ở [ROADMAP].
- **Consequences:** +1 test class `TestImm04WorkflowSurfaceIntegrity` (5 TC), N 57→62; 0 runtime change; lỗ rename/drift `_DT`/silent-`return[]` được khoá ở tầng module. Trade-off: guard hardcode literal `"IMM-04 Workflow"` — chấp nhận vì đó chính là **hợp đồng cần freeze** (đổi 1 phía mà không đổi test = FAIL, đúng mục tiêu).

**Lifecycle hooks (controller chỉ delegate):**

```python
# assetcore/assetcore/doctype/asset_commissioning/asset_commissioning.py
class AssetCommissioning(Document):
    def validate(self):
        from assetcore.services.imm04 import validate_commissioning
        validate_commissioning(self)

    def before_insert(self):
        from assetcore.services.imm04 import initialize_commissioning
        initialize_commissioning(self)

    def before_save(self):
        # Set installation_date khi vào Installing; sinh internal_tag_qr khi vào Identification
        from assetcore.services.imm04 import before_save_commissioning
        before_save_commissioning(self)

    def on_submit(self):
        # Yêu cầu state = Clinical Release
        self.create_ac_asset()
        self.create_initial_document_set()
        from assetcore.services.imm04 import log_lifecycle_event
        log_lifecycle_event(self, "Release", self.workflow_state, "Clinical Release", "")
        self.fire_release_event()

    def on_cancel(self):
        from assetcore.services.imm04 import handle_commissioning_cancel
        handle_commissioning_cancel(self)
```

---

## 4. Service Layer

**File:** `assetcore/services/imm04.py`

**Public functions:**

| Function | Input | Output | Side effect |
|---|---|---|---|
| `initialize_commissioning(doc)` | Document | None | Set reception_date, fetch risk_class, populate mandatory docs |
| `validate_commissioning(doc)` | Document | None | Chạy VR-01 → VR-07 + Gate checks |
| `validate_gate_g01(doc)` | Document | None | Raise ServiceError nếu mandatory docs không đủ. **CR-76:** thân hàm gọi predicate SSoT `g01_missing_mandatory_docs()` + `g01_waiver_granted()` — state-guard/thứ tự/nhánh raise **giữ nguyên** (§5.6.2) |
| `g01_missing_mandatory_docs(doc)` | Document | list[str] | **Predicate thuần** (BR-04-15): `doc_type` của hồ sơ bắt buộc chưa `Received`/`Waived`. 0 side-effect, KHÔNG raise |
| `g01_waiver_granted(doc)` | Document | bool | **Predicate thuần**: `documents_incomplete=1` ∧ `documents_incomplete_note`.strip() != '' — nhánh giải trình của BR-04-02 |
| `gate_g01_blockers(doc)` | Document | list[str] | **Predicate thuần**: `[]` = cổng G01 KHÔNG chặn (kể cả nhờ giải trình). Dùng bởi thẻ cổng |
| `gate_g03_blockers(doc)` / `gate_g03_ok(doc)` | Document | list[str] / bool | **Predicate thuần** dùng hằng SSoT `_G03_PASSING` (`:49`) + `.strip()`. `gate_g03_ok ⟺ not (blocking or not baseline_rows)` của pre-check BR-04-13 |
| `gate_g04_applies(doc)` | Document | bool | **Predicate SSoT «cổng G04 có áp dụng không»** (BR-04-17 · AC-CR-85): `is_radiation_device` **hoặc** `risk_class == 'Radiation'`. **Nơi DUY NHẤT** trong vùng cổng G04 được đọc `is_radiation_device`. Dùng chung bởi VR-07 + `gate_g04_ok` + thẻ. Xem §5.7 |
| `gate_g04_ok(doc)` / `gate_g06_ok(doc)` | Document | bool | **Predicate thuần** mirror VR-07 (`validate_radiation_hold`) và điều kiện `board_approver` của `validate_gate_g05_g06`. AC-CR-85: `gate_g04_ok = not gate_g04_applies(doc) or bool(qa_license_doc)` |
| `evaluate_gate_status(name)` | string | dict (8 khoá) | **Entrypoint đọc** thẻ cổng — khuôn 3 lớp ROLE→EXISTS→ROW + `@rowscoped` (BR-04-16). Trả `g01_docs · g01_waived · g02_facility · g03_baseline · g04_radiation · g04_applicable · g05_nc · g06_approver` (`g04_applicable` additive AC-CR-85 — §5.7.1 P2). Xem §5.6.3 + §5.7 |
| `validate_gate_g03(doc)` | Document | None | ⚠️ **DEAD CODE** — `AssetCommissioning.validate()` KHÔNG gọi hàm này (0 call-site production; chỉ `tests/test_imm04.py` import). Nguồn chặn baseline THẬT ở save-time = `AssetCommissioning.validate_checklist_completion()` (`asset_commissioning.py:97-134`). Giữ lại làm helper + thu hẹp state-set về `Clinical Release` (bỏ `Re Inspection`) — xem §5.5.0 SC#3 |
| `submit_baseline_checklist(name, results)` | string + list | dict | Ghi nhận bảng kiểm cơ sở (UPSERT-by-parameter). State cho phép = `{Initial Inspection, Re Inspection}` (BR-04-14). Verdict **dẫn xuất** `Pass`\|`Fail` (BR-04-04e) — **KHÔNG raise khi có Fail**; raise `VALIDATION` khi `tests_recorded == 0` (BR-04-04a/d). Response 5-key `{name, overall_result, tests_recorded, failed_parameters, clinical_hold_required}`. KHÔNG đụng `workflow_state`. Xem §5.5 |
| `validate_gate_g05_g06(doc)` | Document | None | Save-time hook (defense-in-depth): raise nếu Open NC tồn tại hoặc thiếu board_approver (`nthrow_in_hook` → 417 legacy). Pre-check Decision-B ở `transition_state` chặn TRƯỚC cho path trực tiếp — xem §5.4 |
| `transition_state(name, action, board_approver="")` | string + optional | dict | Áp workflow transition. **BR-04-12:** khi transition có `next_state == Clinical Release` → pre-check `board_approver` (thiếu ⇒ ServiceError `IMM04-GATE-G06-APPROVER` Decision-B) + 4-eyes `assert_distinct_signers` (cấp mới) + set field TRƯỚC `apply_workflow`/`save`. Action không CR-bound ⇒ tham số bỏ qua (backward-compat). Response +key `board_approver`. **BR-04-13:** pre-check **G03 chạy TRƯỚC G06** — còn dòng `test_result ∉ {Pass, N/A}` (hoặc checklist rỗng) ⇒ ServiceError `IMM04-GATE-G03-BASELINE` (422, `context.failed`), raise TRƯỚC `apply_workflow` ⇒ state/docstatus KHÔNG đổi. Xem §5.4 + §5.5 |
| `submit_commissioning(name)` | string | dict | Guard `Clinical Release` + `commissioning.submit` cap → `doc.submit()` (docstatus=1). `on_submit` + `hooks.py` doc_events phát PM (IMM-08) + Calibration (IMM-11) schedule. Đích cuối mạch `Needs→Operation` |
| `check_auto_clinical_hold(doc)` | Document | bool | Trả True nếu risk_class ∈ {C,D,Radiation} |
| `log_lifecycle_event(doc, event_type, from_s, to_s, remarks)` | Document + strings | None | Append lifecycle event row |
| `handle_commissioning_cancel(doc)` | Document | None | Block cancel nếu final_asset tồn tại |
| `overdue_commissioning_filter(today=None)` | str?/None | dict | **SoT** predicate "quá hạn SLA" (BR-04-10): `{reception_date < today−OVERDUE_DAYS, workflow_state NOT IN _TERMINAL_STATES, docstatus != 2}`. Pure, no side effect — dùng chung 3 call-site |
| `check_commissioning_overdue()` | — | None | Email Workshop Head phiếu quá hạn — gọi `overdue_commissioning_filter()` (KHÔNG inline `reception_date<cutoff`); `_send_overdue_alert` tính `days_open` từ cùng anchor (scheduler daily — ⚠️ CHƯA đăng ký trong hooks.py) |
| `_stamp_commissioning_date(doc)` (private) | Document | None | **SoT** stamp Clinical-Release date (BR-04-11). **Idempotent:** `if not doc.commissioning_date: doc.commissioning_date = nowdate()` (set khi NULL, KHÔNG ghi đè). Gọi bởi cả 3 write-path SAU khi `doc.workflow_state == _STATE_CLINICAL_RELEASE` được xác lập. Pure đối với mọi field khác. KHÔNG @whitelist (chỉ internal). Mutate doc in-memory — caller chịu trách nhiệm persist (`doc.save`/`doc.submit` đã có sẵn trong từng write-path) |
| `submit_for_approval(commissioning, approver, stage, remarks)` | string + params | dict | Gửi phê duyệt nội bộ (Wave-2 approval flow) |
| `approve_pending(commissioning, decision, remarks)` | string + params | dict | Duyệt/từ chối phiếu đang chờ |
| `list_my_pending_approvals()` | — | list | Danh sách phiếu chờ duyệt của user hiện tại |
| `create_commissioning_from_purchase(purchase_name, device_idx)` | string + int | dict | Tạo phiếu từ PO |
| `get_commissioning_origin(asset_name)` | string | dict | Truy ngược asset → commissioning |
| `get_form_context(name)` | string | dict | Full context cho form view (FE) |
| `search_link(doctype, query, page_length)` | string | list | Frappe link search helper |
| `get_users_by_role(role, search, limit)` | string | list | Danh sách user theo Role |
| `get_gate_status(name)` | string | dict | Trạng thái cổng G01–G06 cho 1 phiếu. **CR-76:** tầng 1 chỉ còn `_handle(svc.evaluate_gate_status, name)` — 0 logic cổng, gác quyền 3 lớp trong service, +1 khoá additive `g01_waived` (§5.6) |
| `retry_mint_asset(name)` | string | dict | Tạo lại AC Asset nếu on_submit bị lỗi |
| `get_lifecycle_timeline(name)` | string | list | Timeline lifecycle events (FE) |

**Validators (private):**
- `_vr01_unique_serial_number(doc)` — UNIQUE check cross-table
- `_vr05_risk_class_change_warning(doc)` — msgprint (không block)
- `_vr06_immutable_lifecycle_events(doc)` — block edit existing rows
- `_validate_document_expiry(doc)` — throw nếu expired; warn nếu <30 ngày
- `validate_backdate(doc)` — installation_date ≥ PO transaction_date

**Error handling:**

```python
# assetcore/services/imm04.py
from assetcore.services.shared.constants import ErrorCode
from assetcore.services.shared.errors import ServiceError

def validate_gate_g01(doc) -> None:
    """Validate Gate G01: all mandatory documents must be Received or Waived."""
    missing = [
        row.doc_type
        for row in doc.commissioning_documents
        if row.is_mandatory and row.status not in ("Received", "Waived")
    ]
    if missing:
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"VR-02 (Gate G01): Chưa đủ tài liệu bắt buộc. Còn thiếu: {', '.join(missing)}"
        )

def _vr01_unique_serial_number(doc) -> None:
    """VR-01: vendor_serial_no must be unique across Asset + Commissioning."""
    if not doc.vendor_serial_no:
        return
    existing = frappe.db.get_value(
        "Asset Commissioning",
        {"vendor_serial_no": doc.vendor_serial_no, "name": ("!=", doc.name), "docstatus": ("!=", 2)},
        "name"
    )
    if existing:
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"VR-01: Serial Number '{doc.vendor_serial_no}' đã được đăng ký cho phiếu {existing}."
        )
```

---

## 4b. Repository Layer

**Pattern:** Wrap `frappe.get_all` / `frappe.get_doc` trong class hoặc module functions riêng — service không gọi ORM raw trực tiếp.

```python
# assetcore/repositories/imm04_repo.py (hoặc inline trong services/imm04.py)

class CommissioningRepo:
    @staticmethod
    def get(name: str):
        if not frappe.db.exists("Asset Commissioning", name):
            return None
        return frappe.get_doc("Asset Commissioning", name)

    @staticmethod
    def list_open(filters: dict, page: int = 1, page_size: int = 20):
        base_filters = {"docstatus": ("!=", 2), **filters}
        offset = (page - 1) * page_size
        rows = frappe.get_all(
            "Asset Commissioning",
            filters=base_filters,
            fields=["name", "workflow_state", "vendor", "master_item", "modified"],
            limit=page_size,
            start=offset,
            order_by="modified desc"
        )
        total = frappe.db.count("Asset Commissioning", filters=base_filters)
        return rows, total

    @staticmethod
    def get_open_nc_count(commissioning_name: str) -> int:
        return frappe.db.count(
            "Asset QA Non Conformance",
            {"ref_commissioning": commissioning_name, "resolution_status": "Open"}
        )
```

**Methods cần có:**
- `get(name)` — lấy 1 phiếu theo name
- `list_open(filters, page, page_size)` — list phiếu + pagination
- `get_open_nc_count(commissioning_name)` — đếm NC chưa đóng (G05)
- `check_sn_exists(vendor_serial_no, exclude_name)` — VR-01

---

## 5. API Layer

**File:** `assetcore/api/imm04.py`

**Pattern thin wrapper + _handle/_ok/_err:**

```python
# assetcore/api/imm04.py
from assetcore.utils.helpers import _ok, _err, _handle, _parse_json
import assetcore.services.imm04 as service

@frappe.whitelist(methods=["POST"])
def create_commissioning(data: str = "{}") -> dict:
    payload = _parse_json(data, field_name="data", default={})
    return _handle(service.create_commissioning_from_api, payload)

@frappe.whitelist()
def list_commissioning(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    parsed = _parse_json(filters, field_name="filters", default={})
    return _handle(service.list_commissioning, parsed, int(page), int(page_size))

@frappe.whitelist(methods=["POST"])
def submit_commissioning(name: str) -> dict:
    return _handle(service.submit_commissioning, name)

@frappe.whitelist(methods=["POST"])
def assign_identification(name: str, vendor_serial_no: str,
                          internal_tag_qr: str = "", custom_moh_code: str = "") -> dict:
    return _handle(service.assign_identification, name, vendor_serial_no, internal_tag_qr, custom_moh_code)
```

**Helper `_handle`:**

```python
def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except Exception as e:
        frappe.log_error(title="IMM-04 API Error", message=str(e))
        return _err("Lỗi hệ thống. Vui lòng thử lại.", ErrorCode.INTERNAL)
```

> **Quy chuẩn cứng:**
> - Mọi endpoint vào API Catalog (file 05 §0)
> - Response success: `_ok(data)` → `{"success": true, "data": ...}`
> - Response error: `_err(msg_vi, code)` → `{"success": false, "error": ..., "code": ...}`
> - Service raise `ServiceError(ErrorCode.X, "msg tiếng Việt")`
> - `@frappe.whitelist(methods=["POST"])` cho mọi mutation
> - Input JSON parse qua `_parse_json()` — throw `ServiceError(INVALID_PARAMS)` nếu malformed

### 5.1. Overdue-SLA drill — KPI ↔ list cùng SoT (BR-04-10)

Cả 3 call-site phải dùng `overdue_commissioning_filter()`; KHÔNG nhân bản predicate.

**`get_dashboard_stats().kpis.overdue_sla`** — count thuần từ helper:

```python
"overdue_sla": frappe.db.count(_DT, overdue_commissioning_filter()),  # KHÔNG inline filter
```

**`list_commissioning(filters, ...)` — tham số ảo `overdue=1`:**

```python
_ALLOWED_FILTER_KEYS = frozenset({...})          # raw column keys (KHÔNG chứa 'overdue')
_VIRTUAL_FILTER_KEYS = frozenset({"overdue"})     # virtual: AND thêm SoT, không phải column

def list_commissioning(filters: dict, page=1, page_size=20) -> dict:
    safe_filters = {k: v for k, v in filters.items() if k in _ALLOWED_FILTER_KEYS}
    if "docstatus" not in safe_filters:
        safe_filters["docstatus"] = ("!=", 2)
    # Virtual 'overdue=1' → AND thêm SoT predicate (KHÔNG clobber filter khác).
    # reception_date của SoT ghi đè mọi reception_date người dùng truyền (overdue thắng).
    if _is_truthy(filters.get("overdue")):
        safe_filters.update(overdue_commissioning_filter())
    ...
```

**Quy tắc:**
- `'overdue'` nằm trong tập key **được nhận** (whitelist ảo riêng) — KHÔNG lọt qua `_ALLOWED_FILTER_KEYS` như raw column (tránh `WHERE overdue = 1` → SQL error / luôn rỗng).
- `safe_filters.update(...)` chỉ thêm/ghi đè 3 khoá SoT (`reception_date`, `workflow_state`, `docstatus`); các filter khác (`master_item`, `clinical_dept`, `vendor_serial_no`...) **giữ nguyên** → drill kết hợp được.
- Chấp nhận `overdue ∈ {1, "1", true}` qua helper truthy; `0/""/absent` → bỏ qua.

**INVARIANT (kiểm thử trên data-live):**
`get_dashboard_stats().kpis.overdue_sla == list_commissioning({"overdue": 1}, page=1, page_size=N).pagination.total` — card count == drill rows, **byte-for-byte**. Cùng `nowdate()` trong một request nên cùng cutoff.

**KHÔNG đổi (trong scope BR-04-10):** `pending_count`, `hold_count`, `open_nc_count` giữ nguyên — chỉ `overdue_sla` đổi anchor (`expected_installation_date` → `reception_date`). `released_this_month` được re-anchor riêng trong §5.2 (BR-04-11).

### 5.2. "Bàn giao tháng này" — stamp + KPI re-anchor cùng SoT (BR-04-11)

**Bài toán (lỗi thiết kế gốc):** `get_dashboard_stats().kpis.released_this_month` đếm theo `modified >= first_day_of_month`. `modified` là timestamp Frappe tự cập nhật mỗi lần `.save()` → phiếu Released **tháng trước** mà bị edit (sửa note / upload doc / re-approve) **tháng này** lập tức bị kéo vào `released_this_month` → KPI throughput thổi phồng. Đồng thời phiếu chưa có cột thời điểm bàn giao thật: field `commissioning_date` (Date, read_only) tồn tại trên DocType nhưng **chưa write-path nào stamp** — `approve_clinical_release` chỉ đọc `doc.commissioning_date or nowdate()` ở return value (line ~1470), không persist.

**Fix — 2 vế, cùng anchor `commissioning_date`:**

**(a) Stamp tại 3 write-path** — gọi `_stamp_commissioning_date(doc)` SAU khi `workflow_state` đã thành `Clinical Release`, TRƯỚC `doc.save()`/`doc.submit()`:

```python
def _stamp_commissioning_date(doc) -> None:
    """SoT (BR-04-11): set commissioning_date = ngày vào Clinical Release.
    Idempotent — KHÔNG ghi đè giá trị đã có (re-submit/re-approve/edit giữ ngày gốc)."""
    if doc.workflow_state == _STATE_CLINICAL_RELEASE and not doc.commissioning_date:
        doc.commissioning_date = nowdate()
```

Wiring (chính xác, dùng symbol THẬT đã verify trong imm04.py):
- **`transition_state(name, action)`** — sau `frappe.model.workflow.apply_workflow(doc, action)` (line ~1074) và TRƯỚC `doc.save(...)` (line ~1076): chèn `_stamp_commissioning_date(doc)`. Khi action đưa phiếu vào Clinical Release, doc.save persist commissioning_date cùng lượt (cùng khối auto-mint `create_ac_asset` đã có).
- **`submit_commissioning(name)`** — phiếu PHẢI đã ở `Clinical Release` (guard line ~1121). Stamp TRƯỚC `doc.submit()` (line ~1148): `_stamp_commissioning_date(doc)` (submit persist). Bảo hiểm cho phiếu vào Clinical Release từ trước fix mà chưa stamp.
- **`approve_clinical_release(...)`** — phiếu đã ở Clinical Release (guard line ~1447). Stamp TRƯỚC `doc.save(ignore_permissions=True)` (line ~1464): `_stamp_commissioning_date(doc)`. Return value đổi `str(doc.commissioning_date or nowdate())` → `str(doc.commissioning_date)` (sau stamp luôn non-NULL).

> ⚠️ Idempotency: 3 path có thể nối tiếp nhau trên cùng phiếu (transition → approve → submit). Guard `not doc.commissioning_date` đảm bảo chỉ path ĐẦU TIÊN chạm Clinical Release ghi ngày; các path sau no-op → ngày bàn giao bất biến. KHÔNG `update_modified=False` cần thiết (stamp đi cùng save/submit hợp lệ của chính write-path).

**(b) KPI re-anchor** trong `get_dashboard_stats()` — đổi count `released_this_month` từ `modified` sang `commissioning_date` trong cửa sổ tháng:

```python
first_day = get_first_day(nowdate())
today = nowdate()
...
"released_this_month": frappe.db.count(_DT, {
    "workflow_state": _STATE_CLINICAL_RELEASE, "docstatus": 1,
    "commissioning_date": ("between", [str(first_day), str(today)]),
}),
```

> ⚠️ Dùng **MỘT** tuple `("between", [first_day, today])` cho cột `commissioning_date` — KHÔNG tách 2 predicate cùng key `commissioning_date` trong filter dict (dict key trùng bị overwrite, chỉ còn 1 bound). Pattern `["between", [...]]` đã proven trong codebase: `imm05.py:361/409`, `imm06.py:1461`. `frappe.db.count` truyền filters qua cùng query-builder với `get_all` → `between` hợp lệ.

- `("between", [first_day, today])` ⟺ `commissioning_date >= first_day AND <= today` (inclusive 2 đầu). `commissioning_date` NULL → `BETWEEN` loại tự nhiên (NULL không thỏa) → phiếu legacy NULL **không** crash, **không** lọt count (BR-04-11c).
- Cùng `nowdate()` trong một request → `first_day`/`today` ổn định cho cả card lẫn drill list.

**INVARIANT đo được (mirror §5.1, SoT-aligned):**
`released_this_month == count({workflow_state==Clinical Release, docstatus==1, commissioning_date ∈ [first_day, today]})` == số rows drill list `Clinical Release` lọc cùng cửa sổ tháng. Card == drill.

**KHÔNG đổi:** shape của `get_dashboard_stats()` (key `released_this_month` giữ nguyên type `int`/number); `states_breakdown`, `recent_list`, các KPI khác bất biến. KHÔNG schema migration (field đã có). Backfill phiếu Clinical Release legacy `commissioning_date` NULL = **optional, ngoài scope** (nếu cần: patch set `commissioning_date = modified` hoặc `creation` cho rows `workflow_state=Clinical Release AND commissioning_date IS NULL` — KHÔNG bắt buộc cho task này).

---

### 5.3. Baseline verdict — chặn Pass-giả + UPSERT-by-parameter (BR-04-04 · silent-completion lens)

> ⚠️ **SUPERSEDED một phần bởi §5.5 (2026-07-24).** Vế **`BR-04-04c`** dưới đây ("bất kỳ `test_result=='Fail'` → raise `VALIDATION`, KHÔNG set Pass") là **lỗi thiết kế gốc** — nó chặn persist ⇒ phép đo KHÔNG ĐẠT không lưu được và phiếu không vào nổi `Re Inspection`. Thay bằng **BR-04-04e** ở §5.5 (verdict dẫn xuất `Pass|Fail`, luôn persist). Các vế **a / b / d GIỮ NGUYÊN** và vẫn là spec chuẩn.

**Bài toán (lỗi thiết kế gốc — Self-Correction).** `submit_baseline_checklist` (`services/imm04.py:1493-1512`) chốt nghiệm thu Initial Inspection. Bản cũ có **2 lỗ silent-completion**:

1. **Pass-giả với 0 phép đo.** Nếu `doc.baseline_tests` rỗng (phiếu tạo KHÔNG pre-seed child) AND `results` rỗng → vòng lặp update không chạy, `fails == []` → nhảy thẳng `overall_inspection_result = "Pass"`. Phiếu **Pass mà chưa đo gì** — false-success câm. (Spec-root: EC-04-06 cũ ghi "*không block submit nếu không có test nào*" — nay đảo, xem 02 §IV.5.)
2. **Drop câm parameter chưa seed.** Vòng lặp chỉ duyệt `doc.baseline_tests` **có sẵn** rồi map theo `parameter`; `result` cho parameter **chưa có row** bị **bỏ qua hoàn toàn** — không append, không persist. KTV đo tại hiện trường (phiếu không pre-seed) → kết quả biến mất câm.

Ngoài ra response chỉ trả 3-key, không có tín hiệu *đã ghi bao nhiêu phép đo thực* → FE/mobile không phân biệt "Pass thật (N đo)" vs "Pass rỗng".

**Fix — 4 vế (BR-04-04a..d), thứ tự bắt buộc:**

```python
def submit_baseline_checklist(name: str, results: list) -> dict:
    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")
    if doc.workflow_state != _STATE_INITIAL_INSPECTION:                       # 2 loại 403: cap-403 ở api-layer (rbac.require) — đây là state-guard 200-Error
        raise ServiceError(ErrorCode.INVALID_PARAMS,
            f"Chỉ submit checklist khi ở {_STATE_INITIAL_INSPECTION}")

    # BR-04-04a — chặn Pass-giả: phải có ÍT NHẤT 1 nguồn phép đo (row seeded HOẶC result gửi lên).
    if not (doc.baseline_tests or results):
        raise ServiceError(ErrorCode.VALIDATION,
            "BR-04-04: Không thể nghiệm thu — chưa có phép đo baseline nào. "
            "Nhập kết quả đo trước khi nộp.")

    # BR-04-04b — UPSERT-by-parameter: áp result vào row có sẵn; parameter CHƯA có row → APPEND.
    existing = {row.parameter: row for row in (doc.baseline_tests or [])}
    for r in results:
        param = (r.get("parameter") or "").strip()
        if not param:                                    # parameter reqd=1 → skip rỗng (tránh mandatory-fail on save)
            continue
        target = existing.get(param)
        if target is None:
            target = doc.append("baseline_tests", {"parameter": param})
            existing[param] = target
        target.measured_val = r.get("measured_val")      # Float — Frappe coerce; KHÔNG ép "" (khác bản cũ)
        target.test_result = r.get("test_result", "")
        target.fail_note = r.get("fail_note", "")

    # Persist upsert TRƯỚC verdict → re-get thấy measured_val+test_result cho MỌI nhánh (kể cả Fail), không mất dữ liệu đo.
    doc.save(ignore_permissions=True)

    # tests_recorded = số row THỰC có test_result (Pass/Fail/N/A) — KHÔNG len(results) mù.
    recorded = [row for row in (doc.baseline_tests or []) if (row.test_result or "").strip()]
    tests_recorded = len(recorded)

    # BR-04-04c — Fail bất kỳ (kể cả row vừa append) → raise, liệt kê parameter, KHÔNG set Pass.
    fails = [row.parameter for row in recorded if row.test_result == "Fail"]
    if fails:
        raise ServiceError(ErrorCode.VALIDATION,
            f"BR-04-04: Thông số sau không đạt: {', '.join(fails)}. Phiếu phải chuyển về Re Inspection.")

    # BR-04-04d — overall 'Pass' CHỈ khi tests_recorded > 0 (đóng auto-Pass câm cho phiếu có row nhưng 0 row ghi test_result).
    if tests_recorded == 0:
        raise ServiceError(ErrorCode.VALIDATION,
            "BR-04-04: Không thể nghiệm thu Pass — 0 phép đo được ghi nhận.")

    is_high_risk = check_auto_clinical_hold(doc)
    doc.overall_inspection_result = "Pass"
    doc.save(ignore_permissions=True)
    return {"name": doc.name, "overall_result": "Pass",
            "tests_recorded": tests_recorded, "clinical_hold_required": is_high_risk}
```

**Grounding (verified, KHÔNG đoán):**
- Child DocType `Commissioning Checklist` (istable=1): `parameter` **reqd=1** ⇒ `doc.append(..., {"parameter": param})` với `param` non-empty là hợp lệ; **skip `param` rỗng** để không vỡ mandatory khi `doc.save`. `test_result` = Select `""/Pass/Fail/N/A` (giá trị chuẩn là **`N/A`**, không phải "N-A"). `measured_val` = **Float** ⇒ truyền `r.get("measured_val")` (số hoặc None) — KHÔNG ép `""` như bản cũ (`:1447`).
- `check_auto_clinical_hold(doc)` (`services/imm04.py:405`) trả `bool` (Class C/D/Radiation) — bất biến.
- **Persist-trước-verdict** là chủ ý: ServiceError lỗi-nghiệp-vụ được api-handler bắt → **HTTP-200 + Error envelope** (Decision-B, KHÔNG raise→4xx), request kết thúc "thành công" ⇒ `doc.save` đã chạy được commit → re-get thấy dữ liệu đo ở **cả** nhánh Fail lẫn Pass. Nhánh Fail giữ `overall_inspection_result` ≠ `Pass`.

**Boundaries:**
- **Always:** giữ state-guard `_STATE_INITIAL_INSPECTION`; append CHỈ khi `parameter` non-empty; `overall_inspection_result='Pass'` ⟺ `tests_recorded > 0`; response 4-key `{name, overall_result, tests_recorded, clinical_hold_required}`; audit entry `baseline_test` ghi kèm `tests_recorded`.
- **Never:** set `Pass` khi `tests_recorded==0`; drop `result` có parameter chưa seed; trả `tests_recorded = len(results)` mù; đổi `overall_inspection_result` sang `Pass` khi còn `Fail`; thêm `@frappe.whitelist` mới (endpoint `submit_baseline_checklist` ĐÃ tồn tại `api/imm04.py:155` — **0 whitelist mới** ⇒ `test_oas_baseline` KHÔNG bị đụng).

#### ADR-IMM-04-02: Baseline verdict UPSERT + `tests_recorded` là SSoT thay vì tin `len(results)`
- **Status**: Accepted
- **Date**: 2026-07-19
- **Context**: Nghiệm thu là **cổng an toàn NĐ98 / WHO HTM §5.1.2** (incoming inspection) — Pass = thiết bị được đưa vào lâm sàng. Phiếu có thể vào Initial Inspection với `baseline_tests` **rỗng** (transition Identification→Initial Inspection không seed child; KTV đo phát sinh tại hiện trường). Logic cũ (update-in-place các row seeded) vừa auto-Pass khi rỗng, vừa drop câm đo mới.
- **Decision**: (1) Verdict `Pass` phải gắn với **số phép đo thực ghi** — dùng `tests_recorded` (đếm row có `test_result`) làm SSoT, `Pass` ⟺ `tests_recorded > 0`. (2) Áp **UPSERT-by-parameter**: parameter chưa có row → append + persist. (3) Persist upsert **trước** khi phán verdict để dữ liệu đo không mất ở nhánh Fail.
- **Alternatives**: (a) *Seed `baseline_tests` từ Device Model spec khi vào Initial Inspection* — loại: cần master-data spec đầy đủ mọi model (chưa có), và không phủ đo phát sinh ngoài spec; (b) *Trả `tests_recorded = len(results)`* — loại: `results` chứa param rỗng/trùng/không ghi verdict ⇒ đếm phồng, tái tạo false-success ở tầng số liệu.
- **Consequences**: Response +1 key `tests_recorded` (additive — client cũ bỏ qua field mới). Mobile OAS mirror (`SubmitBaselineChecklistResponse` hiện CLOSED 3-key, cite `imm04.py:1456`) cần **re-mirror thành 4-key sau khi BE land** (owner mobile-mirror; grounded-argspec: chỉ curate khi field có ở `@source`). KHÔNG schema migration (child field đã có). KHÔNG whitelist mới.

---

### 5.4. Gỡ deadlock `board_approver` — cấp người duyệt 4-mắt NGAY trong transition (BR-04-12 · Self-Correction vòng 5)

**Bài toán (lỗi thiết kế gốc — deadlock không lối thoát cho path trực tiếp / mobile):**

Gate **G06** yêu cầu `board_approver` non-empty tại **thời điểm** `workflow_state` trở thành `Clinical Release`. Gate này chạy trong `validate()` hook (`validate_gate_g05_g06`, `services/imm04.py:391`) — tức **lúc `doc.save()`**. Nhưng con đường trực tiếp duy nhất để chuyển phiếu vào Clinical Release là `transition_state(name, action)` — **KHÔNG có tham số `board_approver`**. Đường duy nhất để *ghi* `board_approver` là `approve_clinical_release(commissioning, board_approver, …)`, mà hàm này lại **đòi phiếu ĐÃ ở `Clinical Release`** (`imm04.py:1520`). ⇒ Vòng chết:

```
transition → Clinical Release  ──(save)──►  gate G06: "board_approver là bắt buộc" → 417 thô
approve_clinical_release        ──(guard)──►  "phiếu phải ở Clinical Release" → không thể tới
```

Hệ quả: KTV/app mobile gọi `transition_state("Phê duyệt phát hành")` từ `Initial Inspection` với baseline 100% Pass/N/A, 0 NC Open → **luôn `417` (nút chết)**. Thiết bị KHÔNG BAO GIỜ vào lâm sàng qua path trực tiếp ⇒ AC Asset không sinh ⇒ **PM schedule (IMM-08) + Calibration schedule (IMM-11) không được phát** ⇒ đứt mạch `Needs→Operation`, vi phạm quản trị vòng đời + NĐ98 (thiết bị vận hành không có governance bảo trì/hiệu chuẩn).

> Đường vòng `submit_for_approval → approve_pending` (Wave-2 inbox) CÓ set `board_approver = current_user` trước `apply_workflow` (`imm04.py:1810`), nhưng đòi 2 lượt API + có `pending_approver` được gán — KHÔNG phải path mà mobile/`transition_state` dùng. Deadlock vẫn tồn tại cho path trực tiếp.

**Fix — `transition_state(name, action, board_approver="")` cấp người duyệt ATOMIC ngay trong transition. 5 vế (BR-04-12a..e), thứ tự bắt buộc:**

```python
def transition_state(name: str, action: str, board_approver: str = "") -> dict:
    # ... (NOT_FOUND + has_permission("write") + allowed-action check GIỮ NGUYÊN) ...
    allowed = _get_workflow_transitions(name)          # đã có: list[dict]{action,next_state,allowed_role}
    # ... action ∈ allowed_actions else INVALID_PARAMS (giữ nguyên) ...
    doc = frappe.get_doc(_DT, name)

    # BR-04-12: CHỈ xử lý board_approver khi transition đưa phiếu VÀO Clinical Release.
    #           next_state đọc từ chính transition đang thực thi (KHÔNG hardcode action).
    target_state = next((t["next_state"] for t in allowed if t["action"] == action), None)
    is_cr_bound = target_state == _STATE_CLINICAL_RELEASE

    if is_cr_bound:
        effective_approver = board_approver or doc.board_approver          # BR-04-12a
        if not effective_approver:                                        # BR-04-12b — STRUCTURED, KHÔNG 417
            raise ServiceError(
                ErrorCode.VALIDATION,
                render(MSG.IMM04_GATE_G06_APPROVER)[1],                   # message VI đã render
                http_status=422,
                message_code=MSG.IMM04_GATE_G06_APPROVER,                 # "IMM04-GATE-G06-APPROVER"
                context={"missing": ["board_approver"]},
            )
        if board_approver:                                                # BR-04-12c — 4-eyes CHỈ khi caller cấp mới
            assert_distinct_signers(                                      # raise FORBIDDEN → state KHÔNG đổi, field KHÔNG ghi
                doc, "clinical_head", "qa_officer", "owner", "pending_approver",
                candidate_user=board_approver, candidate_field="board_approver",
            )
            doc.board_approver = board_approver                           # BR-04-12d — set TRƯỚC apply_workflow/save
    # else: board_approver BỎ QUA hoàn toàn (BR-04-12e — backward-compat)

    prev_state = doc.workflow_state
    frappe.model.workflow.apply_workflow(doc, action)                     # gate G06 lúc save GIỜ pass (approver đã set)
    log_lifecycle_event(doc, action, prev_state, doc.workflow_state)
    _stamp_commissioning_date(doc)
    doc.save(ignore_permissions=False)
    # ... auto-mint create_ac_asset khi Clinical Release (GIỮ NGUYÊN) ...
    return {"name": name, "action_applied": action,
            "new_state": doc.workflow_state, "docstatus": doc.docstatus,
            "final_asset": doc.final_asset, "board_approver": doc.board_approver}
```

**Registry — MSG entry MỚI (additive, `utils/messages.py`):**

```python
# class MSG:
IMM04_GATE_G06_APPROVER = "IMM04-GATE-G06-APPROVER"
# MESSAGES dict:
MSG.IMM04_GATE_G06_APPROVER: {
    "title": "Chưa chọn người phê duyệt Ban Giám đốc",
    "template": "Gate G06: Phải chọn Người Phê duyệt Ban Giám đốc (board_approver) "
                "trước khi Phát hành Lâm sàng.",
    "action_hint": "Chọn người phê duyệt Ban Giám đốc rồi gửi lại yêu cầu phát hành.",
    "severity": "warning",
    "http_status": 422,
},
```

> Vì sao entry MỚI (không tái dùng `IMM04_BOARD_APPROVER_REQUIRED = "IMM04-BOARD-APPROVER-REQUIRED"`): acceptance chốt `message_code == "IMM04-GATE-G06-APPROVER"` + `context={missing:['board_approver']}` để FE map đúng control người-duyệt. Entry cũ (`IMM04-BOARD-APPROVER-REQUIRED`) vẫn do **hook save-time** `validate_gate_g05_g06` dùng (defense-in-depth cho write-path khác) — **GIỮ NGUYÊN, KHÔNG đổi value** (tránh vỡ FE/test tham chiếu chuỗi cũ).

**Hai tầng cổng G06 (in-handler pre-check vs save-time hook) — phân vai rõ:**

| Tầng | Vị trí | Khi nào fire | Kết quả |
|---|---|---|---|
| **Pre-check (MỚI)** | `transition_state` (command, trước `apply_workflow`) | Mọi action CR-bound qua path trực tiếp/mobile | **ServiceError → Decision-B HTTP-200 `success:false`** `message_code=IMM04-GATE-G06-APPROVER`, `context.missing=['board_approver']` |
| **Save-time hook (GIỮ)** | `validate_gate_g05_g06` (`validate()`) | Bất kỳ write-path nào đưa phiếu vào Clinical Release mà thiếu approver (last-resort) | `nthrow_in_hook(IMM04_BOARD_APPROVER_REQUIRED)` → 417 legacy |

Ở happy-path direct/mobile, pre-check chặn TRƯỚC `save` ⇒ hook 417 **không bao giờ chạm** cho case thiếu approver. Hook chỉ còn là lưới an toàn cho path không đi qua `transition_state`.

**Grounding (verified, KHÔNG đoán):**
- `board_approver` = `Link User`, **đã tồn tại** trên DocType (`04 §2.1`, `asset_commissioning.json`) ⇒ **KHÔNG schema migration**.
- `_get_workflow_transitions` (`imm04.py:664`) trả `{"action","next_state","allowed_role"}` ⇒ `next_state` đọc trực tiếp, KHÔNG hardcode. 3 cạnh CR-bound (verify workflow JSON): `Initial Inspection→"Phê duyệt phát hành"`, `Clinical Hold→"Gỡ giữ lâm sàng"`, `Re Inspection→"Phê duyệt sau tái kiểm"` — cả 3 hưởng fix.
- `assert_distinct_signers` (`services/shared/scope.py:17`) raise `ServiceError(FORBIDDEN)` + bypass `AssetCore Super Admin`; signer_fields khớp `approve_clinical_release` (`imm04.py:1529`): `clinical_head, qa_officer, owner, pending_approver` (candidate_field=`board_approver` được loại khỏi self-check).
- Envelope Decision-B: `api_handler.handle` bắt `ServiceError` → `_err` trả dict `success:false` **trong body HTTP-200** (KHÔNG set `frappe.local.response.http_status_code`) ⇒ đúng "in-handler HTTP-200 + Error envelope", KHÔNG raw 4xx/417.
- Path end-to-end: sau `Clinical Release`, `submit_commissioning(name)` → `doc.submit()` → `docstatus==1` → `on_submit` (`asset_commissioning.py:47`) + **`hooks.py:194-197` doc_events `on_submit`** phát `imm08.create_pm_schedule_from_commissioning` + `imm11.create_calibration_schedule_from_commissioning`. Deadlock gỡ ⇒ mạch `Needs→Operation` thông.

**Boundaries:**
- **Always:** chỉ chạm `board_approver` khi `target_state == _STATE_CLINICAL_RELEASE`; set approver **TRƯỚC** `apply_workflow`/`save`; 4-eyes `assert_distinct_signers` chạy **TRƯỚC** khi ghi field (fail ⇒ state bất biến + field KHÔNG ghi); lỗi thiếu approver = **ServiceError Decision-B** (`message_code=IMM04-GATE-G06-APPROVER`, `context.missing=['board_approver']`), HTTP-200 `success:false`; `next_state` đọc từ transition đang chạy; response thêm key `board_approver` (additive).
- **Never:** dùng `frappe.throw`/`nthrow_in_hook` cho case thiếu approver ở path này (→ 417 thô — cấm); ghi `board_approver` khi action KHÔNG CR-bound (backward-compat: param bị bỏ qua); bỏ qua 4-eyes khi caller cấp approver mới; đổi value chuỗi `IMM04-BOARD-APPROVER-REQUIRED` cũ; thêm `@frappe.whitelist` mới (endpoint `transition_state` ĐÃ tồn tại `api/imm04.py:92` — **0 whitelist mới**); đụng mobile OAS (op `transition_state` KHÔNG có trong `assetcore-mobile.openapi.yaml` — op-count baseline & `test_mobile_oas` **KHÔNG đổi**).

#### ADR-IMM-04-03: Cấp `board_approver` atomic trong `transition_state` (in-handler pre-check) thay vì tách RPC 2-bước
- **Status**: Accepted
- **Date**: 2026-07-23
- **Context**: Gate G06 (`board_approver` reqd) chạy ở `validate()` (save-time), nhưng path trực tiếp/mobile chỉ có `transition_state(name, action)` không mang approver; `approve_clinical_release` lại đòi đã-ở-Clinical-Release ⇒ deadlock (thiết bị không vào lâm sàng ⇒ IMM-08/11 schedule không phát ⇒ đứt vòng đời + hở NĐ98). Là **cổng nghiệm thu NĐ98 / WHO HTM Commissioning-Acceptance**: buộc giữ 4-mắt (SoD) đồng thời phải phá deadlock.
- **Decision**: Thêm tham số **optional** `board_approver` vào `transition_state`; khi (và CHỈ khi) transition đang thực thi có `next_state == Clinical Release` thì (a) pre-check presence → thiếu ⇒ ServiceError Decision-B `IMM04-GATE-G06-APPROVER`; (b) 4-eyes `assert_distinct_signers` nếu cấp mới; (c) ghi `board_approver` TRƯỚC `apply_workflow`/`save` để gate hook pass cùng lượt. Ngoài CR-bound: bỏ qua tham số (backward-compat).
- **Alternatives**:
  - (a) *Nới `approve_clinical_release` bỏ guard "phải ở Clinical Release" để nó tự transition* — loại: nó `doc.submit()` luôn (gộp release+submit), phá tách bạch "vào Clinical Release" ↔ "Submit sinh Asset"; và nó là endpoint riêng, không giải cho caller `transition_state` (mobile) hiện hữu.
  - (b) *Bỏ gate G06 khỏi `validate()`, chỉ enforce ở `submit_commissioning`* — loại: mất defense-in-depth; phiếu có thể nằm ở Clinical Release thiếu approver (state không nhất quán với BR).
  - (c) *Bắt buộc luôn đi qua inbox `submit_for_approval → approve_pending`* — loại: ép 2 lượt API + gán `pending_approver` cho luồng nghiệm thu-tại-hiện-trường mobile; UX nút-chết vẫn còn nếu KTV muốn tự chọn người duyệt.
- **Consequences**: `transition_state` +1 tham số optional (additive — caller cũ không truyền ⇒ hành vi non-CR y hệt; CR-bound thiếu approver **nâng cấp** 417→Decision-B, KHÔNG coi là breaking vì là lỗi nghiệp vụ). Response +1 key `board_approver` (additive). +1 MSG entry registry. `api/imm04.py:92` `transition_state` thêm param passthrough (0 whitelist mới). KHÔNG migration, KHÔNG OAS. Hai tầng G06 (pre-check + hook) cùng tồn tại — pre-check thắng ở path trực tiếp.

---

### 5.5. Fail-path baseline — ghi nhận KHÔNG ĐẠT · mở lại Tái kiểm · gate G03 structured (BR-04-04e/f · BR-04-13 · BR-04-14 · Self-Correction vòng 1 mobile Spec 58 / CR-54 §2)

> **SUPERSEDE cục bộ:** mục này **thay thế vế `BR-04-04c`** ở §5.3 (bản cũ: "bất kỳ `test_result=='Fail'` → raise `VALIDATION`, KHÔNG set Pass"). Các vế **a/b/d GIỮ NGUYÊN** (silent-completion guard còn hiệu lực). §5.3 vẫn là spec chuẩn cho phần còn lại.

#### 5.5.0. Ba lỗi thiết kế gốc (Self-Correction)

**SC#1 — Nhầm "ghi nhận phép đo" với "phê duyệt nghiệm thu" (lỗi thiết kế gốc, nghiêm trọng nhất).**
`submit_baseline_checklist` là thao tác **ghi dữ liệu đo kiểm hiện trường**, KHÔNG phải cổng phê duyệt. Bản hiện tại raise `ServiceError(VALIDATION, "BR-04-04: Thông số sau không đạt…")` **TRƯỚC `doc.save()`** (`services/imm04.py:1541-1543`) ⇒ **0 dòng nào được persist**. Hệ quả nghiệp vụ: **phép đo KHÔNG ĐẠT — bằng chứng bắt buộc của incoming inspection (WHO HTM §5.1.2 · NĐ98/2021 nghĩa vụ lưu hồ sơ kiểm tra khi tiếp nhận)** — **không thể lưu vào hệ thống**. KTV đo ra 9.9 µA (vượt ngưỡng) thì con số đó biến mất; phiếu vĩnh viễn không có vết KHÔNG ĐẠT. Đây là **mất dữ liệu tuân thủ**, không phải "chặn an toàn": cổng an toàn thật nằm ở ranh giới **vào `Clinical Release`** (xem SC#3 + BR-04-13), không ở ô nhập liệu.

**SC#2 — State-guard tạo dead-end vĩnh viễn.**
`if doc.workflow_state != _STATE_INITIAL_INSPECTION: raise INVALID_PARAMS` (`services/imm04.py:1521-1522`). Workflow **có** cạnh `Initial Inspection --Báo cáo lỗi baseline--> Re Inspection` (`imm_04_workflow.json`, khai cho 6 vai trò), nhưng ở `Re Inspection` **KHÔNG endpoint nào sửa được `baseline_tests`** (`save_commissioning` có nhánh `_apply_baseline_updates` nhưng chỉ update in-place các dòng đã có; `submit_baseline_checklist` bị chặn state). ⇒ Phiếu vào Tái kiểm là **kẹt vĩnh viễn**: không đo lại được ⇒ không bao giờ đạt ⇒ không bao giờ tới `Clinical Release` ⇒ **đứt mạch `Needs→Operation`** (AC Asset không sinh ⇒ IMM-08 PM + IMM-11 hiệu chuẩn không được phát).

**SC#3 — ⚠️ FACT-CORRECTION: `validate_gate_g03` là DEAD CODE, KHÔNG phải nguồn 417.**
Đề mục vòng quy 417 của nút "Báo cáo lỗi baseline" cho `validate_gate_g03` (`services/imm04.py:382-389`). **Sai — đã verify.** `validate_gate_g03` có **0 call-site production**:

```
grep -rn "validate_gate_g03" --include=*.py .   # chỉ khớp: services/imm04.py (def) + tests/test_imm04.py (import)
```

Controller `AssetCommissioning.validate()` (`asset_commissioning.py:33-46`) gọi `validate_gate_g01`, `validate_gate_g05_g06` — **KHÔNG gọi `validate_gate_g03`**. Nguồn 417 THẬT là method controller **`validate_checklist_completion()`** (`asset_commissioning.py:97-134`), chạy khi `workflow_state ∈ {Initial Inspection, Re Inspection, Clinical Release}` với 4 nhánh `frappe.throw` trần (→ `ValidationError` → HTTP 417 ngoài envelope Decision-B):

| Dòng | Điều kiện | Thông điệp |
|---|---|---|
| `:102-106` | `not self.baseline_tests` (checklist rỗng) | VR-03 |
| `:111-115` | dòng bất kỳ có `test_result` rỗng | VR-03a |
| `:118-123` | dòng `Fail` thiếu `fail_note` | VR-03a |
| `:129-134` | có dòng `Fail` **AND** `state == Clinical Release` | VR-03b |

**Chuỗi nhân quả thật của "nút chết" AC3:** SC#1 chặn persist ⇒ `baseline_tests` rỗng hoặc còn dòng `test_result` rỗng ⇒ `transition_state("Báo cáo lỗi baseline")` chạy `apply_workflow` → `doc.save()` → `validate()` ở `Re Inspection` → **`:102` hoặc `:111` throw** → 417. **Sửa SC#1 (persist Fail kèm `fail_note`) là ĐỦ để mở nút** — dòng `:129` chỉ chặn ở `Clinical Release`, KHÔNG chặn `Re Inspection`. ⇒ **KHÔNG cần sửa `validate_checklist_completion`** ⇒ `test_imm04_baseline_silent_completion` (assert VR-03/VR-03a **có** raise ở `Initial Inspection`) **giữ XANH** (AC5).

**SC#4 — ⚠️ FACT-CORRECTION: IMM-04 KHÔNG ghi `Asset Lifecycle Event`.**
Đề mục vòng yêu cầu transition sinh *"1 `Asset Lifecycle Event`"*. **Sai với hiện trạng IMM-04** — `Asset Commissioning` **không khai** child table `lifecycle_events` (chỉ có Section Break trong JSON), nên `doc.append("lifecycle_events", …)` **no-op câm**; RC-05 đã chuyển sang ghi vào **`IMM Audit Trail`** (SHA-256 hash-chain) — xem `log_lifecycle_event` (`services/imm04.py:409-481`, docstring RC-05). Bản ghi thực tế sinh bởi `transition_state`:

| Field | Giá trị |
|---|---|
| doctype | **`IMM Audit Trail`** *(KHÔNG phải `Asset Lifecycle Event`)* |
| `event_type` | `"State Change"` *(hằng — KHÔNG phải tên action)* |
| `ref_doctype` / `ref_name` | `"Asset Commissioning"` / `doc.name` |
| `change_summary` | tên action, vd `"Báo cáo lỗi baseline"` (vì `remarks=""`) |
| `from_status` / `to_status` | `Initial Inspection` / `Re Inspection` |
| `asset` | `doc.final_asset` — **rỗng `""` trước khi phát hành** |

⇒ **Test AC3 phải assert trên `IMM Audit Trail`** với filter `{ref_doctype: "Asset Commissioning", ref_name: <name>, to_status: "Re Inspection"}` — KHÔNG `Asset Lifecycle Event` (sẽ đỏ oan), và **KHÔNG** "sửa" bằng cách thêm child table vào `asset_commissioning.json` (⇒ cần `bench migrate` = **HARD-STOP USER**). Lưu ý thêm: `log_lifecycle_event` bọc `try/except` **best-effort** — audit lỗi KHÔNG chặn transition, nên đây là assertion "có ghi", không phải invariant chặn.

#### 5.5.1. Thiết kế đích — `submit_baseline_checklist` = ghi nhận, verdict là DẪN XUẤT

```python
_BASELINE_ENTRY_STATES = (_STATE_INITIAL_INSPECTION, _STATE_RE_INSPECTION)   # BR-04-14
_G03_PASSING = ("Pass", "N/A")                                                # SSoT verdict Pass/N-A

def submit_baseline_checklist(name: str, results: list) -> dict:
    doc = CommissioningRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy: {name}")
    # BR-04-14 — mở nhánh Tái kiểm: Re Inspection ĐƯỢC nộp lại (đo lại). Ngoài 2 state
    # này vẫn chặn (Draft/Installing… không có nghiệp vụ đo kiểm cơ sở).
    if doc.workflow_state not in _BASELINE_ENTRY_STATES:
        raise ServiceError(
            ErrorCode.INVALID_PARAMS,
            f"Chỉ nộp bảng kiểm khi ở {' hoặc '.join(_BASELINE_ENTRY_STATES)}. "
            f"Hiện tại: {doc.workflow_state}",
        )

    # BR-04-04b — UPSERT-by-parameter (GIỮ NGUYÊN §5.3): update dòng có sẵn, APPEND
    # parameter chưa seed. KHÔNG drop câm.
    existing = {row.parameter: row for row in (doc.baseline_tests or [])}
    tests_recorded = 0
    for r in results:
        param = (r.get("parameter") or "").strip()
        if not param:
            continue
        row = existing.get(param) or doc.append("baseline_tests", {"parameter": param})
        existing[param] = row
        row.measured_val = r.get("measured_val", "")
        row.test_result = r.get("test_result", "")
        row.fail_note = r.get("fail_note", "")
        if row.test_result:
            tests_recorded += 1

    # BR-04-04a+d — silent-completion guard GIỮ NGUYÊN: 0 phép đo THỰC ⇒ raise TRƯỚC
    # save, KHÔNG persist, KHÔNG set verdict giả. (AC5)
    if tests_recorded == 0:
        raise ServiceError(
            ErrorCode.VALIDATION,
            "BR-04-04: Chưa ghi nhận kết quả kiểm tra baseline nào — không thể "
            "nghiệm thu. Nhập ≥1 phép đo (test_result) trước khi nộp.",
        )

    # BR-04-04e (MỚI — thay BR-04-04c) — verdict DẪN XUẤT, KHÔNG raise.
    failed_parameters = [
        row.parameter for row in (doc.baseline_tests or [])
        if (row.test_result or "").strip() == "Fail"
    ]
    overall = "Fail" if failed_parameters else "Pass"

    is_high_risk = check_auto_clinical_hold(doc)
    doc.overall_inspection_result = overall          # Select đã có option 'Fail' — KHÔNG đụng JSON
    doc.save(ignore_permissions=True)                # ⇒ dòng Fail PERSIST (AC1)
    return {
        "name": doc.name,
        "overall_result": overall,                   # 'Pass' | 'Fail'
        "tests_recorded": tests_recorded,
        "failed_parameters": failed_parameters,      # MỚI — [] khi Pass
        "clinical_hold_required": is_high_risk,
    }
```

**Bất biến:** endpoint **KHÔNG** gọi `apply_workflow` ⇒ `workflow_state` **KHÔNG đổi** (vẫn `Initial Inspection` / `Re Inspection`) dù verdict là `Fail`. Chuyển trạng thái là hành động RIÊNG của người dùng (`transition_state("Báo cáo lỗi baseline")`) — tách bạch *ghi nhận dữ liệu* ↔ *chuyển trạng thái* (AC1).

**Không đụng schema:** `overall_inspection_result` là `Select` với options `\nPass\nFail\nConditional Pass` (`asset_commissioning.json`) — value `Fail` **đã hợp lệ sẵn**. `read_only: 1` chỉ chặn UI, không chặn server-side set. ⇒ **0 DocType/workflow JSON change ⇒ 0 `bench migrate`** (AC7).

#### 5.5.2. Gate G03 chuyển lên ranh giới transition — structured 422 (BR-04-13)

Cổng an toàn KHÔNG được nới (AC4). Chèn pre-check vào `transition_state` **TRƯỚC `apply_workflow`**, cùng vị trí và cùng khuôn với pre-check G06 (§5.4), **G03 chạy TRƯỚC G06** (thiết bị chưa đạt đo kiểm thì không cần hỏi người duyệt):

```python
target_state = next((t["next_state"] for t in allowed if t["action"] == action), None)
if target_state == _STATE_CLINICAL_RELEASE:
    # BR-04-13 (G03) — CHẶN mọi đường vào Clinical Release khi baseline chưa đạt.
    # Bao phủ CẢ 3 cạnh CR-bound: 'Phê duyệt phát hành' (Initial Inspection),
    # 'Phê duyệt sau tái kiểm' (Re Inspection), 'Gỡ giữ lâm sàng' (Clinical Hold).
    blocking = [
        row.parameter for row in (doc.get("baseline_tests") or [])
        if (row.test_result or "").strip() not in _G03_PASSING
    ]
    if blocking or not doc.get("baseline_tests"):
        raise ServiceError(
            ErrorCode.VALIDATION,
            render(MSG.IMM04_GATE_G03_BASELINE, failed=", ".join(blocking) or "(chưa có phép đo nào)")[1],
            http_status=422,
            message_code=MSG.IMM04_GATE_G03_BASELINE,
            context={"failed": blocking},
        )
    # … pre-check G06 board_approver (§5.4) giữ nguyên, chạy SAU G03 …
```

- **Điều kiện chặn = `test_result ∉ {Pass, N/A}`** (một danh sách duy nhất `failed`) — phủ cả `Fail` **và** dòng chưa ghi kết quả, đúng ngữ nghĩa G03 "100% Pass/N/A". Checklist rỗng cũng chặn (`failed: []`, message dùng nhãn "(chưa có phép đo nào)").
- **Raise TRƯỚC `apply_workflow` + trước mọi `doc.save`** ⇒ `workflow_state` **KHÔNG đổi**, `docstatus` **KHÔNG đổi**, `board_approver` **KHÔNG bị ghi** (AC4).
- **Envelope:** `ServiceError` đi qua `api_handler.handle` → `_err(...)` ⇒ **HTTP-200 + Error envelope** `{success:false, error, code:"VALIDATION", http_status:422, message_code:"IMM04-GATE-G03-BASELINE", context:{failed:[...]}, title/action_hint/severity}` (Decision-B — `http_status` là **field body**, KHÔNG status-line; xem `utils/api_handler.py:54-73` + `utils/response.py:95`). ⇒ **hết 417 câm** (AC4).
- **Hook save-time = defense-in-depth, KHÔNG phải đường reachable.** `validate_checklist_completion():129-134` (VR-03b) vẫn chặn `Fail` ở `Clinical Release`; nó chỉ chạy nếu pre-check bị bypass. GIỮ NGUYÊN, KHÔNG sửa (AC5).
- **`validate_gate_g03` (dead code):** thu hẹp state-set về `(_STATE_CLINICAL_RELEASE,)` — **bỏ `_STATE_RE_INSPECTION`** để gỡ bẫy tiềm ẩn nếu sau này ai đó wire nó vào `validate()`. 4 test hiện có (`tests/test_imm04.py::TestGateG03`) dùng state `Clinical Release` và `To Be Installed` ⇒ **không đổi kết quả** (AC7).

#### 5.5.3. Delta MSG registry + parity FE (AC6)

`assetcore/utils/messages.py` — thêm **1 constant + 1 entry** (additive; entry cũ `IMM04_BASELINE_FAILED` **GIỮ NGUYÊN** cho hook defense-in-depth):

```python
    # BR-04-13 (ADR-IMM-04-05): gate G03 pre-check in-handler ở transition CR-bound
    # → Decision-B envelope (KHÔNG 417). Mã RIÊNG (không tái dùng IMM04-BASELINE-FAILED)
    # vì mang context={failed:[...]} cho FE map đúng dòng bảng kiểm.
    IMM04_GATE_G03_BASELINE = "IMM04-GATE-G03-BASELINE"
```

```python
    MSG.IMM04_GATE_G03_BASELINE: {
        "title": "Chưa đạt cổng đo kiểm cơ sở",
        "template": "Gate G03: Không thể phát hành lâm sàng — thông số chưa đạt: {failed}.",
        "action_hint": "Chuyển phiếu sang Tái kiểm (nút “Báo cáo lỗi baseline”), đo lại các thông số chưa đạt rồi phê duyệt.",
        "severity": "warning",
        "http_status": 422,
    },
```

Sau đó **BẮT BUỘC** `python scripts/gen_fe_messages.py` (AST-parse `utils/messages.py` → `frontend/src/locales/messages.ts` + `messages.types.ts`, **AUTO-GENERATED — cấm sửa tay**). Bỏ bước này ⇒ FE rơi về toast `SYS-500` "liên hệ IT" (class-of-bug đã ghi ở STATE Blocker#1). Lượt regen này cũng đồng thời đóng backlog `IMM09-SELF-INSPECT-FORBIDDEN` nếu code đó đã có trong `messages.py`.

#### 5.5.4. Boundaries

- **Always:** giữ nguyên BR-04-04 **a/b/d** (0 phép đo ⇒ raise `VALIDATION`, KHÔNG persist verdict); `overall_inspection_result` là **dẫn xuất** từ `baseline_tests` sau upsert; `submit_baseline_checklist` **KHÔNG** đụng `workflow_state`; gate G03 raise **TRƯỚC** `apply_workflow`/`doc.save`, dùng `ServiceError` structured (`http_status=422`, `message_code`, `context.failed`); G03 chạy **trước** G06; regen `messages.ts` bằng generator; verify bằng `bench … run-tests` module-isolated.
- **Never:** raise khi có `Fail` trong `submit_baseline_checklist` (đó chính là bug); set `overall_inspection_result='Pass'` khi còn dòng `Fail`; set verdict khi `tests_recorded == 0`; dùng `frappe.throw`/`nthrow_in_hook` cho gate G03 ở path service (→ 417 thô — **cấm**); sửa `validate_checklist_completion` (phá `test_imm04_baseline_silent_completion`); nới VR-03b (Fail vẫn phải chặn `Clinical Release`); đụng `asset_commissioning.json` / `commissioning_checklist.json` / `imm_04_workflow.json` (⇒ sẽ cần `bench migrate` = HARD-STOP USER); thêm `@frappe.whitelist` mới (`submit_baseline_checklist` `api/imm04.py:155`, `transition_state` `api/imm04.py:92` **đã tồn tại** ⇒ `test_oas_baseline` bất biến); sửa `frontend/src/locales/messages.ts` bằng tay.

#### ADR-IMM-04-04: `submit_baseline_checklist` = ghi nhận dữ liệu, verdict là DẪN XUẤT (không phải cổng phê duyệt)

- **Status**: Accepted
- **Date**: 2026-07-24
- **Context**: Nghiệm thu lắp đặt là **incoming inspection** theo WHO HTM (giai đoạn Installation & Commissioning) và nghĩa vụ lưu hồ sơ kiểm tra khi tiếp nhận theo **NĐ98/2021** *(article cụ thể: `[UNVERIFIED]` — cần đối chiếu `docs/gmdn/Quyết định *.md`)*. Kết quả **KHÔNG ĐẠT** là **bằng chứng phải lưu**, không phải "input không hợp lệ". Thiết kế cũ raise trước `doc.save()` ⇒ dữ liệu KHÔNG ĐẠT không tồn tại trong hệ thống; đồng thời chặn luôn mọi lối vào `Re Inspection` (workflow có cạnh nhưng không có cách đạt tiền đề).
- **Decision**: Tách **ghi nhận** khỏi **phê duyệt**. `submit_baseline_checklist` luôn persist (khi có ≥1 phép đo thực) và trả verdict dẫn xuất `Pass|Fail` + `failed_parameters[]`; cổng an toàn G03 chuyển lên **ranh giới transition vào `Clinical Release`** (BR-04-13), enforce ở tầng service bằng `ServiceError` structured 422.
- **Alternatives**:
  - (a) *Giữ raise, thêm endpoint riêng `record_baseline_failure`* — loại: 2 endpoint cho cùng một hành vi ghi bảng kiểm, FE/mobile phải phân nhánh trước khi biết kết quả đo; và vẫn không giải được dead-end `Re Inspection`.
  - (b) *Cho `save_commissioning` ghi `baseline_tests` ở `Re Inspection`* — loại: `_apply_baseline_updates` update in-place (không upsert), không tính `tests_recorded`, không trả verdict ⇒ tái tạo đúng lớp lỗi drop-câm §5.3 đã đóng.
  - (c) *Tự động `apply_workflow` sang `Re Inspection` ngay khi verdict = Fail* — loại: trộn ghi-dữ-liệu với chuyển-trạng-thái; KTV mất quyền đo lại tại chỗ trước khi chốt; và workflow transition có RBAC riêng (6 vai trò) ≠ cap `commissioning.write`.
- **Consequences**: Response `submit_baseline_checklist` **3-key → 5-key** (`overall_result` mở enum `Pass|Fail`, `+failed_parameters`) — **additive**, client cũ đọc `name`/`overall_result`/`clinical_hold_required` không vỡ, nhưng client nào **giả định `overall_result` luôn `Pass`** phải sửa (mobile OAS §22 đang khai `enum: [Pass]` — xem `05_API_Specification.md §24`). FE web phải render nhánh Fail (badge + CTA "Báo cáo lỗi baseline"). KHÔNG migration, KHÔNG whitelist mới.

#### ADR-IMM-04-05: Gate G03 enforce ở tầng service (transition boundary) thay vì hook save-time

- **Status**: Accepted (bổ sung cho ADR-IMM-04-03 cùng khuôn)
- **Date**: 2026-07-24
- **Context**: Hook `validate()` chỉ có `frappe.throw`/`nthrow_in_hook` ⇒ HTTP **417** nằm NGOÀI envelope Decision-B; FE/mobile không đọc được `message_code`/`context` ⇒ toast rơi về `SYS-500`. Cùng lúc, hook chạy **sau** `apply_workflow` nên khi throw thì trạng thái in-memory đã đổi (rollback dựa vào transaction, khó suy luận).
- **Decision**: Pre-check G03 ở `services/imm04.transition_state` **trước** `apply_workflow`, raise `ServiceError(VALIDATION, http_status=422, message_code=IMM04-GATE-G03-BASELINE, context={"failed":[...]})`. Giữ hook `validate_checklist_completion` (VR-03b) làm **defense-in-depth** cho các path không đi qua service.
- **Alternatives**: (a) *Đổi `nthrow_in_hook` sang ServiceError trong hook* — loại: Frappe hook không đi qua `api_handler.handle`, `ServiceError` sẽ propagate thành **500**; (b) *Đặt điều kiện vào `imm_04_workflow.json` (`condition`)* — loại: chạm workflow JSON ⇒ cần `bench migrate` (HARD-STOP USER) và thông điệp lỗi của Frappe workflow-condition không mang `message_code`/`context`.
- **Consequences**: Hai tầng G03 cùng tồn tại (pre-check thắng ở path reachable, hook là lưới cuối). +1 MSG entry ⇒ **bắt buộc regen `messages.ts`**. `transition_state` dài thêm ~10 dòng, 0 tham số mới, 0 whitelist mới, 0 migration.

---

### 5.6. Thẻ cổng G01–G06 nói ĐÚNG cổng thật + read-gate 3 lớp (BR-04-15 · BR-04-16 · CR-76 · Self-Correction vòng 5)

> **Một câu:** thẻ «Điều kiện bàn giao» phải là **tấm gương** của cổng chặn — không phải một bản diễn giải thứ hai. Mọi khác biệt giữa "thẻ nói" và "server chặn" là **lỗi thiết kế gốc**, sửa ở Core Doc trước.

#### 5.6.0. Ba lỗi thiết kế gốc (Self-Correction — verify @source 2026-07-26)

| # | Lỗi | Bằng chứng | Hậu quả nghiệp vụ |
|---|---|---|---|
| **E1** | **G01 báo oan khi 0 hồ sơ bắt buộc.** `g01 = all(...) if mandatory else False` (`api/imm04.py:257`) — danh sách rỗng ⇒ **hằng `False`**, trong khi `validate_gate_g01` (`services/imm04.py:353`) tính `missing` rồi `if not missing: return` ⇒ **CHO QUA** | `api/imm04.py:256-257` vs `services/imm04.py:363-368` | Phiếu hợp lệ (loại thiết bị không yêu cầu hồ sơ đi kèm) hiển thị **đỏ vĩnh viễn**; người duyệt mất niềm tin vào thẻ ⇒ **bỏ qua cả 6 cổng** (thẻ trở thành nhiễu, không phải kiểm soát) |
| **E2** | **G01 báo oan khi đã có giải trình thiếu hồ sơ.** Validator cho qua khi `documents_incomplete=1` ∧ `documents_incomplete_note` không rỗng (`services/imm04.py:370-377`); thẻ **không biết** nhánh này ⇒ vẫn đỏ | `api/imm04.py:256-257` (0 tham chiếu `documents_incomplete`) | Thực tế NĐ98: CO/CQ về chậm sau thiết bị là thường xuyên; quy trình đã có đường giải trình, nhưng UI nói "chưa đạt" ⇒ người dùng đi tìm cách "làm cho xanh" thay vì dùng đúng đường giải trình |
| **E3** | **G03 nhân bản literal `("Pass","N/A")`.** Hằng SSoT `_G03_PASSING` (`services/imm04.py:49`) dùng ở pre-check BR-04-13 (`services/imm04.py:1212-1225`); tầng api chép lại literal + **không `.strip()`** | `api/imm04.py:264` vs `services/imm04.py:49,1216-1219` | Thêm/bớt 1 giá trị hợp lệ ở SSoT ⇒ thẻ và cổng **lệch câm**; dòng `" Pass"` (có khoảng trắng) ⇒ thẻ đỏ nhưng server cho qua |
| **E4** | **`get_gate_status` KHÔNG gác quyền.** Không `rbac.require`, không `frappe.has_permission(doc=…)`, không `@rowscoped`; `frappe.get_doc` **không** kiểm quyền (`frappe/model/document.py:36` — RC-9.1 của ADR-IMM00-LIST-SCOPE §9) | `api/imm04.py:246-252` | Dán `?name=` là đọc được tình trạng hồ sơ/đo kiểm/NC/người ký của **phiếu bất kỳ** — cùng lớp IDOR-đọc mà CR-74 đã đóng cho 4 GET-detail khác (OWASP A01) |

#### 5.6.1. Bảng cổng ⇔ enforcement (SSoT — verify @source 2026-07-26)

| Cổng | Ý nghĩa nghiệp vụ | Enforcement THẬT (nơi chặn) | Trạng thái được gác | Có chặn? |
|---|---|---|---|---|
| **G01** `g01_docs` | Hồ sơ bắt buộc đã nhận **hoặc** có giải trình hợp lệ | `validate_gate_g01()` `services/imm04.py:473` (hook `validate`, `asset_commissioning.py:41`) | mọi state **trừ** `Draft` / `Pending Doc Verify` | ✅ |
| **G02** `g02_facility` | Cơ sở hạ tầng đạt yêu cầu | **KHÔNG CÓ** — `facility_checklist_pass` chỉ là field ghi nhận (`_EDITABLE_FIELDS` `services/imm04.py:113`), 0 validator/pre-check tham chiếu | — | ❌ **THAM KHẢO** |
| **G03** `g03_baseline` | 100% phép đo baseline ∈ `_G03_PASSING` **và** có ≥1 phép đo | pre-check **BR-04-13** trong `transition_state()` `services/imm04.py:1358-1366` (SSoT hằng `_G03_PASSING` `:52`, predicate `gate_g03_blockers()` `:408` / `gate_g03_ok()` `:420`) | mọi transition có `next_state == Clinical Release` | ✅ |
| **G04** `g04_radiation` (+ `g04_applicable`) | Cổng **không áp dụng** (không phát bức xạ) **hoặc** đã có giấy phép Cục ATBXHN | `AssetCommissioning.validate_radiation_hold()` (VR-07) `asset_commissioning.py:80-91` — **AC-CR-85**: VR-07 và verdict đọc CHUNG `gate_g04_applies()` | `Clinical Release` / `Pending Release` | ✅ (parity đúng; **AC-CR-85** thêm cờ `g04_applicable` vì verdict một mình không phân biệt nổi «không áp dụng» với «đã đạt» — §5.7) |
| **G05** `g05_nc` | Không còn NC **đang mở** chặn phát hành | `validate_gate_g05_g06()` `services/imm04.py:538` qua `_count_open_ncs()` `:491` | `Clinical Release` | ✅ (parity **đã đúng sẵn** — CR-54 §3) |
| **G06** `g06_approver` | Đã chỉ định người phê duyệt BGĐ | `validate_gate_g05_g06()` `services/imm04.py:538` (predicate `gate_g06_ok()` `:436`) + pre-check BR-04-12b `:1312-1320` | `Clinical Release` | ✅ |

> ⚠️ **`validate_gate_g03()` (`services/imm04.py:507`) KHÔNG phải enforcement của G03.** Nó **chưa bao giờ được wire** vào `AssetCommissioning.validate()` (kiểm tra `asset_commissioning.py:36-47`: chỉ gọi `validate_gate_g01` và `validate_gate_g05_g06`) và dùng predicate **HẸP HƠN** (`test_result == "Fail"` — bỏ sót dòng **rỗng**/giá trị lạ). CR-76 **KHÔNG chạm** hàm này (AC7 zero-behavior-change); chênh lệch predicate ghi vào backlog `[BA] ratify` — xem §5.6.6.

> 🔢 **Số dòng ở bảng §5.6.1 là dòng SAU khi BE land CR-76** (verify bằng AST 2026-07-26: `g01_missing_mandatory_docs` `:372` · `g01_waiver_granted` `:388` · `gate_g01_blockers` `:400` · `gate_g03_blockers` `:408` · `gate_g03_ok` `:420` · `gate_g04_ok` `:430` · `gate_g06_ok` `:436` · `evaluate_gate_status` `:522`). Bảng **§5.6.0** cố ý GIỮ số dòng **trước** refactor — đó là bằng chứng tại thời điểm phát hiện lỗi, không phải con trỏ tra cứu.

#### 5.6.2. Thiết kế đích — MỘT predicate cho mỗi cổng

Trích xuất **predicate thuần** (pure function, 0 side-effect, 0 `throw`) trong `services/imm04.py`; enforcement gọi nó **sau** state-guard của mình, display gọi nó **trực tiếp**:

```python
# ─── Gate predicates — SSoT dùng chung enforcement ⇄ display (BR-04-15) ────────
def g01_missing_mandatory_docs(doc) -> list[str]:
    """doc_type của hồ sơ BẮT BUỘC chưa `Received`/`Waived` (THÔ — chưa xét giải trình)."""

def g01_waiver_granted(doc) -> bool:
    """`documents_incomplete` = 1 ∧ `documents_incomplete_note`.strip() != '' (BR-04-02 nhánh giải trình)."""

def gate_g01_blockers(doc) -> list[str]:
    """[] = KHÔNG chặn. missing != [] ∧ chưa giải trình ⇒ trả danh sách chặn."""

def gate_g03_blockers(doc) -> list[str]:
    """parameter của dòng có (test_result or '').strip() ∉ _G03_PASSING."""

def gate_g03_ok(doc) -> bool:
    """bool(baseline_tests) ∧ not gate_g03_blockers(doc)  ⟺  not (blocking or not baseline_rows)."""

def gate_g04_applies(doc) -> bool:                       # AC-CR-85 — SSoT «cổng có áp dụng»
    """bool(is_radiation_device) or risk_class == 'Radiation'  — nơi DUY NHẤT đọc cờ bức xạ."""

def gate_g04_ok(doc) -> bool:
    """not gate_g04_applies(doc) or bool(qa_license_doc)  — mirror VR-07 (AC-CR-85 §5.7)."""

def gate_g06_ok(doc) -> bool:
    """bool(doc.board_approver)."""

# G05 giữ nguyên SSoT ĐÃ CÓ: _count_open_ncs(name) == 0   (services/imm04.py:402)
```

Refactor call site — **diff = trích xuất thuần, KHÔNG đổi nhánh raise nào** (AC7):

| Hàm | Trước | Sau |
|---|---|---|
| `validate_gate_g01` `:353` | tính `missing` inline; `if doc.get("documents_incomplete") and (…note…).strip(): msgprint; return` | `missing = g01_missing_mandatory_docs(doc)` · `if g01_waiver_granted(doc): msgprint; return` — **state-guard, thứ tự, message, nhánh `nthrow_in_hook` giữ nguyên byte-for-byte** |
| pre-check BR-04-13 `:1156-1169` | list-comp inline dùng `_G03_PASSING` | `blocking = gate_g03_blockers(doc)`; **giữ nguyên** `if blocking or not baseline_rows:` và toàn bộ `ServiceError(...)` |
| `validate_gate_g05_g06` `:417` | `if not doc.board_approver:` | `if not gate_g06_ok(doc):` |
| `validate_radiation_hold` (VR-07) | — | **KHÔNG đụng** (Ask-first: chạm controller = blast-radius ngoài AC; card dùng `gate_g04_ok` đã mirror đúng predicate) |

**INVARIANT INV-GATE-PARITY (bất biến phải chứng minh bằng test):** với mọi fixture trong ma trận `07 §III.4e`, đặt phiếu ở **trạng thái mà cổng được gác** (§5.6.1 cột 4):

```
get_gate_status(name).data[gXX] is True   ⟺   enforcement tương ứng KHÔNG raise
```

hai chiều, cho `gXX ∈ {g01_docs, g03_baseline, g05_nc, g06_approver}`.

> 📐 **Vì sao phải nói "ở trạng thái được gác":** `validate_gate_g01` **return sớm** ở `Draft`/`Pending Doc Verify`. Nếu thẻ copy y nguyên state-guard, phiếu `Draft` thiếu hồ sơ sẽ **xanh** rồi **đỏ đột ngột** ngay khi chuyển trạng thái — đúng lớp "xanh giả" mà CR-76 đang khử. **Chốt:** thẻ mang ngữ nghĩa **pre-flight (as-if-armed)** — trả lời *"nếu chuyển trạng thái bây giờ, cổng này có chặn không?"*, nên **KHÔNG** áp state-guard. Bất biến parity vì thế phát biểu trên nhánh *armed*. Xem ADR-IMM-04-06.

#### 5.6.3. `evaluate_gate_status()` — khuôn 3 lớp ROLE → EXISTS → ROW (BR-04-16, mirror CR-74 §9.4)

Chuyển toàn bộ tính toán từ tầng api xuống service (tầng api chỉ còn `_handle`):

```python
@rowscoped                                            # PermissionError → Error envelope 403 trên HTTP-200
def evaluate_gate_status(name: str) -> dict:
    assert_doctype_read_permission(_DT)               # L0 ROLE — TRƯỚC exists (0 existence-oracle, D9)
    doc = CommissioningRepo.get(name)                 # L1 EXISTS
    if not doc:
        nthrow(MSG.IMM04_NOT_FOUND, name=name)        # 404 trong body (Decision-B)
    assert_can_read_doc(_DT, doc)                     # L2 ROW — hook asset_commissioning_has_permission
    return { ...7 khoá... }
```

```python
# api/imm04.py — tầng 1 KHÔNG còn logic cổng
@frappe.whitelist()
def get_gate_status(name: str) -> dict:
    return _handle(svc.evaluate_gate_status, name)
```

- `Asset Commissioning` **có đủ cả hai hook** (`permission_query_conditions` `hooks.py:443` + `has_permission` `hooks.py:454`) ⇒ L2 có hiệu lực thật, **không** suy biến như `IMM Asset Calibration` (D10).
- **Guard tĩnh G5a** (`tests/test_rowscope_scope_guard.py`) quét mọi `get_*` trong `services/imm*.py` load doc row-scoped: hàm mới `evaluate_gate_status` **không** khớp tiền tố `get_`/`list_` nên G5a *có thể* không thấy → **BE PHẢI** thêm cặp `("services/imm04.py", "evaluate_gate_status")` vào **`_CR76_NAMED_DETAIL_GATES`** (vế *named*, mirror `_CR74_NAMED_DETAIL_GATES`) để guard ghim đích danh. **TUYỆT ĐỐI KHÔNG** thêm cặp này vào `_DETAIL_READ_UNGATED_BACKLOG` (allowlist **chỉ-giảm**; thêm dòng = mở lại lỗ IDOR-đọc — AC5).
- `get_form_context` / `get_barcode_lookup` (2 dòng còn lại của B10) **ngoài phạm vi vòng này** — giữ nguyên trong allowlist.

#### 5.6.4. Hợp đồng response — 7 khoá (6 cũ + 1 additive)

| Khoá | Kiểu | Nguồn | Ghi chú |
|---|---|---|---|
| `g01_docs` | `boolean` | `not gate_g01_blockers(doc)` | **true** = cổng không chặn (kể cả nhờ giải trình) |
| `g01_waived` | `boolean` | `g01_waiver_granted(doc) and bool(g01_missing_mandatory_docs(doc))` | **MỚI (additive)** — true ⇒ đạt **nhờ giải trình**, UI phải nói khác "đủ hồ sơ" |
| `g02_facility` | `boolean` | `bool(doc.facility_checklist_pass)` | **THAM KHẢO** — 0 enforcement |
| `g03_baseline` | `boolean` | `gate_g03_ok(doc)` | baseline rỗng ⇒ `false` |
| `g04_radiation` | `boolean` | `gate_g04_ok(doc)` | N/A-hoá ở UI khi không phải thiết bị bức xạ |
| `g05_nc` | `boolean` | `_count_open_ncs(name) == 0` | chỉ NC `Open` mới chặn (BR-04-13/CR-54 §3) |
| `g06_approver` | `boolean` | `gate_g06_ok(doc)` | |

- **`boolean` THẬT** (Python `bool()`/`all()`), **KHÔNG** phải Frappe Check `integer 0/1` — mobile đã cảnh báo đúng điểm này ở CR-53 §1.
- **Additive**: client cũ đọc 6 khoá cũ **không vỡ**; `g01_waived` chỉ thêm.
- Nhánh lỗi (`FORBIDDEN` 403 · `NOT_FOUND` 404) **KHÔNG** chứa bất kỳ khoá `g0*` nào.

#### 5.6.5. Boundaries

- **Always:** một predicate cho mỗi cổng, dùng chung enforcement ⇄ display · thẻ mang ngữ nghĩa **BLOCKING-parity** (`true` = không chặn) · L0 ROLE chạy **trước** EXISTS · lỗi nghiệp vụ = **in-handler HTTP-200 + Error envelope** (KHÔNG raise → 4xx status-line) · `_G03_PASSING` là nguồn duy nhất của tập kết quả đạt · verify bằng `bench --site miyano run-tests` module-isolated (`timeout` tool ≥ 600000ms — kill giữa chừng làm nhiễm DB, xem LL).
- **Ask-first:** đổi enforcement `validate_radiation_hold`/`validate_gate_g03` để dùng predicate chung (chạm controller / đổi predicate hẹp→rộng) · thêm enforcement cho **G02** (hiện là cổng tham khảo) · siết `_count_open_ncs` sang `!= 'Closed'` (blocker #4 trong STATE — **chưa ratify**).
- **Never:** thêm/bớt **bất kỳ** nhánh chặn nào trong `transition_state` / `validate_gate_*` / `AssetCommissioning.validate` · để literal `("Pass","N/A")` ở tầng api · trả **list rỗng/`False` câm** thay cho 403 (anti-pattern dead-gate) · thêm dòng vào `_DETAIL_READ_UNGATED_BACKLOG` · đụng `asset_commissioning.json` / `imm_04_workflow.json` (⇒ `bench migrate` = HARD-STOP USER) · thêm `@frappe.whitelist` mới (`get_gate_status` `api/imm04.py:246` **đã tồn tại** ⇒ `test_oas_baseline` bất biến).

#### 5.6.6. Backlog mở ra (KHÔNG làm vòng này)

| # | Việc | Ưu tiên |
|---|---|---|
| C1 | `validate_gate_g03()` (`:386`) chưa wire + predicate **hẹp hơn** pre-check (`== 'Fail'` vs `∉ _G03_PASSING`) ⇒ hoặc wire + hợp nhất predicate, hoặc **xoá** hàm chết. Đổi = đổi hành vi chặn ⇒ vòng riêng | P1 · [BA] ratify |
| C2 | **G02** `facility_checklist_pass` có nên trở thành cổng chặn thật (NĐ98 điều kiện lắp đặt)? Nếu có → thêm enforcement + đổi nhãn UI | P2 · [BA] ratify |
| C3 | 2 dòng còn lại của B10 (`get_form_context` · `get_barcode_lookup`) — cùng khuôn 3 lớp | P1 · [BE] |
| C4 | Thẻ G05 bộc lộ **số NC non-Open + link** ("Đạt — 1 NC đang xử lý, không chặn") | P2 · [FE] |

#### ADR-IMM-04-06: Thẻ cổng dùng CHÍNH predicate enforcement, ngữ nghĩa BLOCKING-parity (pre-flight)

- **Status**: Accepted
- **Date**: 2026-07-26
- **Context**: Thẻ «Điều kiện bàn giao» được viết **lần hai** ở tầng api (`api/imm04.py:254-278`) trong khi cổng thật sống ở service/hook. Ba lệch đã lộ (E1/E2/E3 §5.6.0) — cùng **class-of-bug** với G05 đã sửa ở CR-54 §3 (thẻ đếm `!= 'Closed'`, validator đếm `== 'Open'`). Lệch **báo oan** nguy hiểm hơn lệch báo lỏng: người duyệt học được rằng thẻ "hay sai" ⇒ bỏ qua toàn bộ 6 cổng, kiểm soát an toàn trở thành trang trí.
- **Decision**: (1) Mỗi cổng có **đúng một** predicate thuần trong `services/imm04.py`; enforcement và display **cùng gọi** nó. (2) Ngữ nghĩa thẻ = **BLOCKING-parity**: `true` = "cổng KHÔNG chặn", **không** phải "đã hoàn tất". (3) Thẻ đánh giá **pre-flight (as-if-armed)** — không copy state-guard của validator, để không có "xanh rồi đỏ" khi đổi trạng thái. (4) Cổng **không có** enforcement (G02) phải được **khai báo tường minh là tham khảo** ở cả OAS lẫn UI.
- **Alternatives**:
  - (a) *Giữ 2 bản logic, thêm test so sánh* — loại: test chỉ bắt được lệch **đã biết**; predicate mới thêm ở một phía vẫn trôi. Cấu trúc phải làm cho lệch **bất khả thi**, không chỉ *bị phát hiện*.
  - (b) *Thẻ gọi thẳng validator trong `try/except`* — loại: validator có **side-effect** (`frappe.msgprint` cảnh báo hết hạn hồ sơ, log) và mang state-guard; gọi để "thử xem có raise không" biến một endpoint **đọc** thành thứ phát sinh `_server_messages` + phụ thuộc thứ tự hook. Ngoài ra `validate_gate_g05_g06` gộp 2 cổng ⇒ không tách được nguyên nhân.
  - (c) *Copy y nguyên state-guard vào thẻ (parity "tuyệt đối" theo nghĩa đen)* — loại: sinh ra "xanh giả" ở `Draft` (§5.6.2), đúng thứ UI đang cần khử.
- **Consequences**: `api/imm04.py::get_gate_status` mất toàn bộ logic (còn `_handle`) ⇒ dễ review. Response **+1 khoá additive** `g01_waived` ⇒ OAS mobile + FE type + FE nhãn phải cập nhật cùng vòng. Thẻ **đổi giá trị quan sát được** ở 2 ca (0 hồ sơ bắt buộc; đã giải trình) — đây là **sửa lỗi báo oan**, không phải nới cổng: enforcement **không đổi một dòng nhánh raise** nào.

#### ADR-IMM-04-07: `get_gate_status` gác quyền như một GET-detail (khuôn 3 lớp CR-74), không phải endpoint "chỉ đọc trạng thái"

- **Status**: Accepted (áp dụng ADR-IMM00-DETAIL-READ-01/02/03 cho IMM-04)
- **Date**: 2026-07-26
- **Context**: `get_gate_status` bộc lộ tình trạng hồ sơ pháp lý, kết quả đo kiểm an toàn, tồn tại NC và việc đã/chưa có người ký của **một phiếu cụ thể** — đủ để suy ra tình trạng tuân thủ của thiết bị. Hiện **0 gate** (E4 §5.6.0) và `frappe.get_doc` **không** kích hoạt hook `has_permission` (RC-9.1). Ngoài ra `_err(msg, 404)` cho `name` không tồn tại **trước** mọi kiểm tra quyền ⇒ endpoint trở thành **existence-oracle** cho naming-series.
- **Decision**: Áp **nguyên khuôn** ROLE → EXISTS → ROW + `@rowscoped` (CR-74 §9.4). Read-gate của thẻ cổng **== read-gate của phiếu** — không có "chế độ đọc lỏng cho dữ liệu tóm tắt".
- **Alternatives**: (a) *Chỉ `rbac.require("commissioning.read")`* — loại: capability là **role-scope**, không phải **row-scope**; vendor/KTV khác khoa vẫn đọc chéo. (b) *Trả 6 khoá `false` khi thiếu quyền* — loại: silent-deny = anti-pattern dead-gate (không phân biệt "chưa đạt" với "không được xem"), và vẫn rò *tồn tại phiếu*. (c) *Gate trong `BaseRepository.get`* — loại: siết luôn scheduler/domain-logic (đúng cảnh báo B12), cần tham-số-hoá `scope=` — vòng riêng.
- **Consequences**: Persona thiếu DocPerm read `Asset Commissioning` **mất** thẻ cổng (nhận 403 in-envelope) — cần đối chiếu danh sách persona (blocker B2 của §8.10/§9.9 vẫn mở). FE **bắt buộc** render nhánh 403 thành thông báo tiếng Việt, **KHÔNG** logout, **KHÔNG** màn trắng. Endpoint đổi từ `_ok/_err` trực tiếp sang `_handle` ⇒ envelope lỗi nay **có** `message_code`/`context` (mobile CR-53 §1 yêu cầu đúng điểm này).

---

### 5.7. Cổng G04 gác ĐÚNG 1 domain — predicate SSoT `gate_g04_applies` (BR-04-17 · AC-CR-85 · Self-Correction thiết kế gốc)

> **Nguồn:** AC-CR-85 (nội bộ) · đóng mobile CR-58. **Trạng thái:** spec chốt ở Bước-2, BE land ở Bước-4.
> Slice contract (OAS + guard) **đã đóng** ở Bước-2 — xem `05 §24.6.5`–`§24.6.6`.

#### 5.7.0. Lỗi thiết kế gốc (verify @source 2026-07-27)

`check_auto_clinical_hold` (**toạ độ TRƯỚC land**: `services/imm04.py:571-576`; sau land: `services/imm04.py:616-632`) làm **hai việc không liên quan nhau** trong 5 dòng:

```python
def check_auto_clinical_hold(doc: Document) -> bool:
    """VR-07: Return True if device needs Clinical Hold (Class C/D/Radiation)."""
    high_risk = doc.risk_class in ("C", "D", "Radiation") if doc.risk_class else bool(doc.is_radiation_device)
    if high_risk:
        doc.is_radiation_device = 1     # ← GHI ĐÈ SAI (câu lệnh phải GỠ)
    return high_risk
```

1. **Trả về** "phiếu có thuộc nhóm nguy cơ cao không" — dùng cho `clinical_hold_required` (`services/imm04.py:1774`). **Đúng, giữ nguyên.**
2. **Ghi đè** `doc.is_radiation_device = 1` cho **mọi** phiếu `risk_class ∈ {C, D}` — kể cả thiết bị **không hề phát bức xạ**. **Sai, phải gỡ.**

Ba hệ quả đã chứng minh trên source:

| # | Hệ quả | Chứng cứ |
|---|---|---|
| H1 | **Đảo ngược SSoT của chính field.** `is_radiation_device` khai `read_only: 1` + `fetch_from: master_item.is_radiation_device` (`asset_commissioning.json`) ⇒ SSoT là Device Model. Frappe áp `fetch_from` trong `_validate_links()` **trước** `run_before_save_methods()` (`frappe/model/document.py:413-414` khi save, `:302-309` khi insert) ⇒ giá trị fetch đúng bị `validate()` ghi đè ngay sau đó. Người dùng **không có đường sửa lại**: field `read_only` và `is_radiation_device` **không** nằm trong `_EDITABLE_FIELDS` (`services/imm04.py:113-127`). | `document.py:302/309/413/414` · `asset_commissioning.json` fields · `services/imm04.py:113-127` |
| H2 | **Deadlock pháp lý.** VR-07 (**trước land** `asset_commissioning.py:80-91`; sau land `asset_commissioning.py:82-100`) đọc `self.is_radiation_device` ⇒ phiếu Class C/D không bức xạ, khi vào `Clinical Release`/`Pending Release`, bị throw «chưa có Giấy phép của Cục An toàn Bức xạ Hạt nhân». Giấy phép đó **không thể tồn tại** cho máy không phát bức xạ ⇒ lối thoát duy nhất của người dùng là **upload giấy tờ SAI** vào `qa_license_doc` — tức bơm rác vào hồ sơ pháp lý NĐ98. | `asset_commissioning.py:82-100` (sau land) · `services/imm04.py:465` |
| H3 | **Dữ liệu sai lan ra ngoài module.** `is_radiation_device` bị bơm `1` chảy vào `get_commissioning` (`services/imm04.py:993`), `get_barcode_lookup` → `device.is_radiation` (`services/imm04.py:1158`) và khoá filter `is_radiation_device` (`services/imm04.py:134`) ⇒ danh sách "thiết bị bức xạ" của bệnh viện đếm **thừa** toàn bộ Class C/D. | `services/imm04.py:134/993/1158` |

**Gộp SAI 2 domain pháp lý** (đây là gốc rễ, không phải lỗi code cẩu thả):

| Domain | Văn bản | Nghĩa vụ | Gác bởi | Hồ sơ |
|---|---|---|---|---|
| Nhóm nguy cơ Class C/D | **NĐ 98/2021/NĐ-CP** (02 §I.6, Điều 28-32) | Chứng nhận đăng ký lưu hành hợp lệ trước sử dụng lâm sàng | **GW-2** `_gw2_check_document_compliance()` (`asset_commissioning.py:311-350`) qua IMM-05 `Asset Document` | «Chứng nhận đăng ký lưu hành» / «Giấy phép nhập khẩu» (+ nhánh `is_exempt`) |
| Phát bức xạ ion hoá | **NĐ 142/2020/NĐ-CP** (02 §I.6, Điều 25-27) | Giấy phép tiến hành công việc bức xạ | **VR-07** `validate_radiation_hold()` | Giấy phép **Cục An toàn Bức xạ Hạt nhân** (`qa_license_doc`) |

02 §I.6 đã tách đúng 2 dòng này **từ đầu** — code mới là chỗ trôi. Vì vậy đây là **Self-Correction đưa code về đúng Core Doc**, không phải nới cổng.

#### 5.7.1. Predicate SSoT — `gate_g04_applies`

```python
def gate_g04_applies(doc: Document) -> bool:
    """Cổng G04 CÓ áp dụng cho phiếu này không (SSoT — VR-07 · verdict · thẻ dùng CHUNG).

    True ⟺ thiết bị phát bức xạ (`is_radiation_device`, gương của Device Model qua
    `fetch_from`) HOẶC người dùng phân loại phiếu là `risk_class == 'Radiation'`.
    Đây là **nơi duy nhất** trong vùng cổng G04 được đọc `is_radiation_device`.
    """
    return bool(doc.get("is_radiation_device")) or doc.get("risk_class") == "Radiation"
```

**Vì sao có vế `risk_class == 'Radiation'`** (nếu bỏ là **suy giảm an toàn thật**): hôm nay mọi phiếu `risk_class='Radiation'` đều bị `check_auto_clinical_hold` bơm cờ `1` nên VR-07 luôn gác. Gỡ ghi đè mà **không** thêm vế này ⇒ phiếu do người dùng phân loại `Radiation` trên một Device Model chưa gắn cờ sẽ **mất** cổng giấy phép. Vế thứ hai giữ nguyên hành vi chặn → **0 ô nào của ma trận VR-07 bị nới**.

3 điểm tiêu thụ — **tất cả** gọi predicate, **không** đọc lại field:

| # | Nơi | Sửa thành | Ghi chú |
|---|---|---|---|
| P1 | `gate_g04_ok(doc)` (`services/imm04.py:458-465` — trước land `:430-433`) | `return not gate_g04_applies(doc) or bool(doc.get("qa_license_doc"))` | Verdict — ngữ nghĩa BLOCKING-parity giữ nguyên |
| P2 | `evaluate_gate_status(name)` (`services/imm04.py:552-613`) | `+ "g04_applicable": gate_g04_applies(doc)` (additive, sau `g04_radiation`) | 7 khoá cũ **bất biến** |
| P3 | `AssetCommissioning.validate_radiation_hold()` (`asset_commissioning.py:82-100` — trước land `:80-91`) | `if imm04_svc.gate_g04_applies(self) and self.workflow_state in (...) and not self.qa_license_doc:` | Bỏ `self.is_radiation_device`; **state-guard + câu message giữ NGUYÊN** |

`check_auto_clinical_hold` chỉ **gỡ đúng 2 dòng** `if high_risk: doc.is_radiation_device = 1`; biểu thức `high_risk` (kể cả nhánh fallback `else bool(doc.is_radiation_device)` khi `risk_class` rỗng) **giữ nguyên từng ký tự** ⇒ `clinical_hold_required` bất biến.

#### 5.7.2. Bất biến INV-G04-1 (2 chiều)

∀ phiếu:

1. `gate_g04_applies(doc) == False` ⇒ `gate_g04_ok(doc) == True` (⇒ `g04_radiation = true`) **VÀ** VR-07 **không bao giờ** throw — ở mọi `workflow_state`, mọi `qa_license_doc`.
2. `gate_g04_applies(doc) == True` ⇒ `gate_g04_ok(doc) == bool(qa_license_doc)` **VÀ** VR-07 throw **đúng khi** `not qa_license_doc` ∧ `workflow_state ∈ {Clinical Release, Pending Release}`.

⇒ **advertise == enforce** trên toàn ma trận 5 `risk_class` × 2 `qa_license_doc` = 10 ô. Tổ hợp `{g04_applicable: false, g04_radiation: false}` là **BẤT KHẢ** — nếu quan sát được thì BE lỗi (guard `cr85_d` khai đúng câu này trong OAS).

#### 5.7.3. Guard "1 diễn giải" — đo bằng AST, KHÔNG bằng `grep -c` toàn file

`grep -c 'is_radiation_device' services/imm04.py` **không dùng được** làm thước đo: file có 8 lần xuất hiện hợp lệ **ngoài** vùng cổng — toạ độ THẬT sau land: `_CREATE_FIELDS:106` · `_ALLOWED_FILTER_KEYS:134` · `_autofill_from_device_model:255/266-267` · detail dict `:993` · `_LIST_FIELDS:1141` / `get_barcode_lookup:1158` · fallback `check_auto_clinical_hold:632` (chưa kể các lần nhắc trong docstring `gate_g04_applies:433-436` và `check_auto_clinical_hold:620-626` — thêm một lý do nữa để KHÔNG đếm bằng `grep`). Thước đo đúng là **AST-scoped** (đã land trong `cr85_g`):

- **Vùng cổng G04** = `{gate_g04_ok, evaluate_gate_status}` (service) ∪ `{validate_radiation_hold}` (controller) — **0** lần xuất hiện `is_radiation_device`.
- `gate_g04_applies` — **đúng 1** lần đọc.
- `check_auto_clinical_hold` — **0** phép **GHI** `doc.is_radiation_device` (phép **đọc** ở fallback được giữ, xem 5.7.1).

#### 5.7.4. Boundaries

- **Always**: dùng `gate_g04_applies` ở cả 3 điểm P1/P2/P3 · giữ nguyên chuỗi message VR-07 (người dùng đã quen, i18n đã dịch) · giữ `clinical_hold_required` bất biến 12/12 ô (5.7.5) · additive-only trên response.
- **Ask first**: đổi định nghĩa predicate (thêm/bớt vế) · đổi state-guard VR-07 · gỡ nhánh fallback `else bool(is_radiation_device)` của `check_auto_clinical_hold`.
- **Never**: `bench migrate` / sửa `asset_commissioning.json` (mọi field đã tồn tại — đây là thay đổi **thuần logic**) · đổi/bỏ 1 trong 7 khoá cũ của `evaluate_gate_status` · thêm bất kỳ chỗ nào đọc `is_radiation_device` để quyết định cổng G04 · "bù" bằng cách cho VR-07 chặn theo `risk_class ∈ {C,D}` (đó chính là bug — nghĩa vụ Class C/D thuộc GW-2) · sửa `_autofill_from_device_model` (`:266-267`) — writer hợp lệ, cùng chiều với `fetch_from`, ngoài scope.

#### 5.7.5. Ma trận không-suy-giảm cho `check_auto_clinical_hold` — **12 ô, không phải 10**

`risk_class` có **6** giá trị quan sát được (5 enum + **rỗng/None**), không phải 5. Nhánh `else bool(doc.is_radiation_device)` **chỉ chạy khi `risk_class` rỗng** ⇒ ma trận 5×2 của acceptance **không chạm nhánh đó lần nào**; nếu chốt 10 ô, ai đó xoá nhánh fallback vẫn xanh 10/10. Ma trận chốt:

| `risk_class` | `is_radiation_device` | `check_auto_clinical_hold` trả về | Nhánh chạy |
|---|---|---|---|
| `A` | 0 / 1 | `False` / `False` | enum |
| `B` | 0 / 1 | `False` / `False` | enum |
| `C` | 0 / 1 | `True` / `True` | enum |
| `D` | 0 / 1 | `True` / `True` | enum |
| `Radiation` | 0 / 1 | `True` / `True` | enum |
| **`''` (rỗng)** | **0 / 1** | **`False` / `True`** | **fallback — 2 ô mà 5×2 bỏ sót** |

Giá trị **giống hệt trước fix ở cả 12 ô** ⇒ Clinical Hold routing không đổi một ô nào.

#### 5.7.6. Toạ độ THẬT sau land (BE Bước-4 — verify @source 2026-07-27)

| Symbol | File | Dòng (sau land) | Vai trò |
|---|---|---|---|
| `gate_g04_applies` | `services/imm04.py` | **430-455** | predicate SSoT — nơi DUY NHẤT của vùng cổng đọc cờ bức xạ (`:455`) |
| `gate_g04_ok` | `services/imm04.py` | **458-465** | P1 verdict — `not gate_g04_applies(doc) or bool(qa_license_doc)` (`:465`) |
| `evaluate_gate_status` | `services/imm04.py` | **554-613** | P2 thẻ — khoá `g04_applicable` ở `:610` (additive, ngay sau `g04_radiation:608`) |
| `check_auto_clinical_hold` | `services/imm04.py` | **616-632** | BR-04-05a — 0 phép GHI cờ; biểu thức `high_risk` giữ nguyên (`:632`) |
| `validate_radiation_hold` | `assetcore/doctype/asset_commissioning/asset_commissioning.py` | **82-100** | P3 VR-07 — gọi `imm04_svc.gate_g04_applies(self)` (`:92`) |

**Bằng chứng chạy thật** (module-isolated, `timeout` ≥ 600000ms — KHÔNG `bench migrate`, KHÔNG curl):
`test_imm04` **110 OK** (97 baseline + 13 TC mới) · `test_mobile_oas` **1015 OK** · `test_mobile_docset` **9 OK** ·
`test_rowscope_docperm_gate` **22 OK** · `test_imm04_baseline_fail_path` **11 OK** ·
`test_imm04_baseline_silent_completion` **9 OK** · `test_imm05` **91 OK**.
Mutation M1–M7: xem `07 §III.4f.4` (7/7 ĐỎ, khôi phục `md5sum` khớp).

⚠️ **Siết guard phát sinh khi chạy M4** (không phải nới): `cr85_g` đo `emits` bằng `ast.dump` cả hàm
⇒ docstring của `evaluate_gate_status` có nhắc tên khoá nên **xoá khoá khỏi response vẫn XANH**
(vacuous). Đã đổi sang đọc **khoá thật của dict `return`** + thêm helper `_cr85_called_names`
(khẳng định "tính qua predicate SSoT" đo bằng `ast.Call`, không bằng prose). Số TC **giữ 1015**
(siết assertion ≠ thêm TC ⇒ 3 counter `test_mobile_docset` không đổi).

#### ADR-IMM-04-08: Cổng G04 gác **hiện tượng vật lý** (phát bức xạ), KHÔNG gác **nhóm nguy cơ**

- **Status**: Accepted (Self-Correction — code trôi khỏi 02 §I.6 vốn đã tách đúng)
- **Date**: 2026-07-27
- **Context**: `check_auto_clinical_hold` bơm `is_radiation_device = 1` cho mọi Class C/D. Trên giấy tờ điều này có vẻ "an toàn hơn" (thêm một cổng hồ sơ cho thiết bị nguy cơ cao), nhưng cổng đó đòi **sai loại giấy tờ**: Giấy phép Cục ATBXHN là hồ sơ của NĐ 142/2020 cho nguồn bức xạ, không phải hồ sơ NĐ98 của thiết bị Class C/D. Kết quả thực tế là deadlock + áp lực nộp giấy tờ sai vào hồ sơ pháp lý.
- **Decision**: G04 chỉ áp dụng khi thiết bị **thực sự phát bức xạ** (`is_radiation_device`, SSoT = Device Model) hoặc được phân loại tường minh `risk_class == 'Radiation'`. Nghĩa vụ hồ sơ của Class C/D **đã** có cổng riêng đúng loại: **GW-2** (BR-04-08) yêu cầu «Chứng nhận đăng ký lưu hành» `Active` hoặc `is_exempt` trong IMM-05.
- **Alternatives**:
  - (a) *Giữ ghi đè, thêm nút "miễn trừ" cho Class C/D không bức xạ* — loại: thêm một nhánh miễn trừ cho một cổng **lẽ ra không được kích hoạt**; đồng thời hợp thức hoá dữ liệu `is_radiation_device` sai trên toàn hệ (H3).
  - (b) *Đổi nhãn `qa_license_doc` thành "giấy phép chung"* — loại: một ô đính kèm cho hai loại hồ sơ pháp lý khác nhau ⇒ hồ sơ NĐ98 và hồ sơ bức xạ trộn lẫn, không audit được (ISO 13485 §7.5).
  - (c) *Bỏ luôn `risk_class == 'Radiation'` khỏi predicate cho "gọn"* — loại: suy giảm an toàn thật (5.7.1).
- **Consequences**: **Nới có chủ đích đúng 1 lớp phiếu** — Class C/D **không bức xạ**, `qa_license_doc` rỗng: trước bị VR-07 chặn, nay không. Đây là **gỡ cổng sai loại**, không phải bỏ kiểm soát: phiếu đó vẫn phải qua G01/G03/G05/G06 và **GW-2**. ⚠️ Đã ghi nhận **giới hạn của GW-2** (không do vòng này gây ra, xem backlog B-CR85-2): `_gw2_check_document_compliance` thoát sớm khi `final_asset` chưa có (`asset_commissioning.py:325-327`), mà `final_asset` chỉ được set trong `on_submit` ⇒ ở lần vào `Clinical Release` đầu tiên GW-2 **im lặng bỏ qua**. Không được dùng câu "GW-2 đã che" để tuyên bố an toàn tuyệt đối cho Class C/D — phải đóng B-CR85-2 mới nói được. Dữ liệu tồn: phiếu cũ đã bị bơm `is_radiation_device = 1` giữ nguyên trong DB cho tới lần `save()` kế tiếp (khi đó `fetch_from` trả về giá trị Device Model) — **không** viết patch backfill trong vòng này (xem B-CR85-1).

#### ADR-IMM-04-09: Verdict + cờ áp-dụng là **hai khoá**, không phải một enum 3 giá trị

- **Status**: Accepted (áp khuôn `g01_waived` của ADR-IMM-04-06)
- **Date**: 2026-07-27
- **Context**: `g04_radiation = true` mang **hai nghĩa khác hẳn nhau**: «đã có giấy phép» và «cổng không áp dụng». Client buộc phải suy nghĩa thứ hai từ **nguồn thứ hai** (`doc.is_radiation_device` trong payload phiếu) — và nguồn đó chính là thứ đang sai (H1).
- **Decision**: Phơi thêm khoá `boolean` **additive** `g04_applicable`, tính bằng **chính** `gate_g04_applies`. Client đọc **cặp** `(g04_applicable, g04_radiation)` theo LUẬT ĐỌC 3 TRẠNG THÁI (`05 §24.6.3`).
- **Alternatives**:
  - (a) *Đổi `g04_radiation` thành enum `not_applicable|ok|blocked`* — loại: **breaking change** trên khoá client đang wire; và phá ngữ nghĩa BLOCKING-parity đồng nhất của 6 cổng (ADR-IMM-04-06) chỉ vì một cổng.
  - (b) *Để client tự suy từ `is_radiation_device`* — loại: đúng class-of-bug "display ⇔ enforcement parity" đã đóng 4 lần (CR-54 G05 · CR-76 G01/G03 · AC-CR-77 · AC-CR-78). Thẻ phải là **tấm gương** của validator, không phải bản diễn giải thứ hai.
  - (c) *Trả kèm cả `qa_license_doc` để client tự dựng câu chữ* — loại: đẩy luật nghiệp vụ sang client, mỗi client dựng một kiểu.
- **Consequences**: `GateStatus` 7 → **8 khoá** (`required` 8/8 vì luôn emit). OAS + FE type + FE nhãn phải cập nhật cùng vòng. FE **phải** có nhánh fallback khi khoá vắng (BE stale) — xem `06 §G04-3STATE`.

---

## 6. Audit Trail

| Trigger | Entry type | Actor | Payload lưu |
|---|---|---|---|
| `create_commissioning` | `commissioning_created` | session.user | from=None, to=Draft |
| Transition state | `state_transition` | session.user | from=prev_state, to=new_state, action |
| `assign_identification` | `identification` | session.user | vendor_serial_no, internal_tag_qr |
| `submit_baseline_checklist` | `baseline_test` | session.user | overall_result (`Pass`\|`Fail`), tests_recorded, failed_parameters (§5.5) |
| `approve_clinical_release` → Submit | `release` | session.user | final_asset, commissioning_date |
| NC created | `non_conformance` | session.user | nc_name, nc_type |
| NC closed | `nc_closed` | session.user | nc_name, resolution_note |
| `on_cancel` | `cancel` | session.user | reason |

**Hash chain:** Sử dụng `Asset Lifecycle Event` child table với field `ip_address`. VR-06 enforce immutability bằng cách so sánh snapshot trong `validate()`. Không có SHA-256 hash chain tại thời điểm v2 — planned cho v3.

**Verify:** Xem `lifecycle_events` child table trực tiếp. API `get_form_context` trả đầy đủ `lifecycle_events[]`.

---

## 7. Background jobs / Scheduler

| Job | Tần suất | Trạng thái đăng ký | Mục đích |
|---|---|---|---|
| `assetcore.services.imm04.check_commissioning_overdue` | daily | **ĐÃ đăng ký** trong `hooks.py:scheduler_events["daily"]` (2026-06-03) | Email Workshop Head phiếu quá hạn SLA (reception_date < today−OVERDUE_DAYS) |
| `assetcore.tasks.check_clinical_hold_aging` | daily | *(Not yet implemented — module không có `assetcore/tasks.py`)* | Email QA Officer phiếu Clinical Hold quá N ngày |
| `assetcore.tasks.check_commissioning_sla` | daily | *(Not yet implemented)* | SLA vi phạm |

> Ground truth `assetcore/hooks.py` (2026-06-03): `check_commissioning_overdue` đã được đăng ký trong `scheduler_events["daily"]` (cùng SoT `overdue_commissioning_filter()` với dashboard KPI + list drill). 2 job `clinical_hold_aging` / `commissioning_sla` vẫn backlog (chưa cài):

```python
scheduler_events = {
    "daily": [
        "assetcore.services.imm04.check_commissioning_overdue",  # ✅ registered 2026-06-03
        # 2 job clinical_hold_aging / commissioning_sla — backlog, chưa cài
    ],
}
```

**Logic `check_commissioning_overdue` (dùng SoT — BR-04-10):**

```python
def check_commissioning_overdue() -> None:
    """Daily: email Workshop Head for commissioning quá hạn SLA.

    Dùng SoT `overdue_commissioning_filter()` — KHÔNG inline `reception_date<cutoff`
    để scheduler-alert / KPI count / list drill luôn cùng định nghĩa.
    """
    overdue = frappe.get_all(
        "Asset Commissioning",
        filters=overdue_commissioning_filter(),
        fields=["name", "vendor", "workflow_state", "reception_date", "commissioned_by"],
    )
    for comm in overdue:
        # days_open tính từ CÙNG anchor đã chốt (reception_date)
        _send_overdue_alert(comm, date_diff(nowdate(), comm["reception_date"]))
```

---

## 8. Integration

**Module nội bộ:**

| Module | Chiều | Cơ chế |
|---|---|---|
| IMM-03 (Purchase Order) | IN | `po_reference` Link; `get_po_details()` auto-fill |
| IMM-05 (Asset Document) | OUT | `create_initial_document_set()` khi on_submit |
| IMM-04 ← IMM-05 | IN | GW-2 gate: query Asset Document Active cho asset |
| IMM-08 (PM Schedule) | OUT (TODO) | `fire_release_event()` publish `imm04_asset_released` — IMM-08 chưa subscribe |
| IMM-12 / QMS | OUT | `Asset QA Non Conformance.transfer_to_capa` flag |

**doc_events trong hooks.py (Wave-2 ground truth):**

```python
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            "assetcore.services.imm11.create_calibration_schedule_from_commissioning",
            "assetcore.services.imm16.eval_imm04_realtime",
        ],
    },
}
```

> `before_insert` / `validate` cho Asset Commissioning KHÔNG đi qua `doc_events` mà gắn trực tiếp trong controller `assetcore/assetcore/doctype/asset_commissioning/asset_commissioning.py` (`def before_insert(self): imm04_svc.initialize_commissioning(self)` + `def validate(self): imm04_svc.validate_commissioning(self)`). Đây là pattern chuẩn AssetCore (controller delegates to service).

**Fixtures liên quan IMM-04** (trong `assetcore/fixtures/workflow.json` + `assetcore/fixtures/role_profile.json`): `IMM-04 Workflow` + Workflow States (`Pending Doc Verify`, `To Be Installed`, `Installing`, `Identification`, `Initial Inspection`, `Non Conformance`, `Clinical Hold`, `Re Inspection`, `Clinical Release`, `Return To Vendor`).

---

## 8.1. QR cấp tài sản (Asset-level QR) — tương thích ngược với commissioning

> **Quyết định cuối:** [`./ADR-001-asset-qr.md`](./ADR-001-asset-qr.md). Tóm tắt tác động lên IMM-04 — schema/contract chi tiết ở [`../imm-00/04_Backend_Design.md`](../imm-00/04_Backend_Design.md) §II.1.8.

**Bối cảnh:** QR cấp tài sản (`AC Asset.qr_token` + deep-link `/a/<token>`) là cơ chế MỚI ở IMM-00 registry, **song song** với QR cấp commissioning đang có ở IMM-04 (`internal_tag_qr`).

| QR cũ (IMM-04 commissioning) | QR mới (IMM-00 asset) |
|---|---|
| Field `Asset Commissioning.internal_tag_qr` = `BV-{DEPT}-{YYYY}-{SEQ}` | Field `AC Asset.qr_token` = `secrets.token_urlsafe(16)` |
| Sinh ở `assign_identification` (`services/imm04.py:575`) | Sinh `before_insert` mọi asset (3-tier ở IMM-00) |
| Encode **chuỗi tag** (scanner-wedge gõ tay/đầu đọc) | Encode **URL** `/a/<token>` (camera điện thoại quét → màn info) |
| Đoán được (DEPT+YYYY+SEQ tuần tự) + doc-bound | Enumeration-safe + idempotent + sống ở cấp tài sản |

**Quy tắc tương thích ngược (ADR-001 D6):**
- **GIỮ NGUYÊN field** `internal_tag_qr` + `assign_identification` / `generate_internal_qr` / `get_barcode_lookup` (`services/imm04.py:575,1406,977`) — KHÔNG breaking change. Field vẫn read-only + scanner-wedge lookup theo `internal_tag_qr` vẫn chạy. Nhãn tag-string đã in vẫn quét được bằng đầu đọc.
- Vòng A (A1→A6) **KHÔNG đụng** logic QR của IMM-04. Hai cơ chế chạy song song trong giai đoạn chuyển tiếp.

#### 8.1.1 — Dedup `generate_qr_label` → deep-link asset (CHỐT vòng 13 / B-3 — ADR-001 §D6.1)

> **Quyết định cuối:** [`./ADR-001-asset-qr.md`](./ADR-001-asset-qr.md) §D6.1. Đây là **delta DUY NHẤT** vòng 13 trên IMM-04 — chỉ contract nhãn của `generate_qr_label`, KHÔNG field/cap/DocType/enum/patch mới.

**RC dedup:** trước vòng 13 có 2 đường QR quét-được trên 1 thiết bị → (1) `generate_qr_label` mã hoá `internal_tag_qr` tuần tự + `scan_url=/app/asset-commissioning/<name>` (desk); (2) deep-link asset `/a/<token>` enumeration-safe. Sau vòng 13: **CHỈ còn (2)**.

`generate_qr_label` ủy quyền (delegate) việc dựng deep-link sang helper QR cấp asset của IMM-00 — **KHÔNG copy-paste** logic sinh token/URL:

```python
# services/imm04.py::generate_qr_label — sau check permission + internal_tag_qr
# Ưu tiên gọi 1 entry point public (tránh import symbol private _build_qr_url cross-module):
from assetcore.services.imm00 import build_asset_label_data  # lazy import (Pattern B)

qr_url = None
if doc.final_asset:
    # build_asset_label_data nội bộ đã: ensure_asset_qr_token (idempotent — token-less → sinh
    # + emit qr_generated 1 lần) → _build_qr_url(token) (get_url("/a/{token}"), host từ site config).
    qr_url = build_asset_label_data(doc.final_asset)["qr_url"]
# (Tương đương: token = ensure_asset_qr_token(doc.final_asset); qr_url = _build_qr_url(token))

return {
    "qr_value": doc.internal_tag_qr,    # GIỮ — FE fallback khi qr_url rỗng + tương thích nhãn cũ
    "qr_url": qr_url,                   # MỚI: deep-link tuyệt đối /a/<token> hoặc None (phiếu chưa mint asset)
    "label": { ... },                   # GIỮ nguyên các field nhãn
    "docs_url": ...,                    # GIỮ nguyên (không trong scope)
    # scan_url: BỎ HẲN (desk-login) — thay bằng qr_url
}
```

| # | Quy tắc | Chi tiết |
|---|---|---|
| 1 | `qr_url` khi có `final_asset` | Chuỗi tuyệt đối `/a/<token>` qua `ensure_asset_qr_token(final_asset)` + `_build_qr_url`. 1 helper duy nhất (dedup THẬT). |
| 2 | Edge token-less | Phiếu CHƯA có `final_asset` → `qr_url=None`, KHÔNG gọi `ensure_asset_qr_token`, KHÔNG throw. Nhãn fallback `commissioning_id`. |
| 3 | `scan_url` desk → BỎ | Field `scan_url=/app/asset-commissioning/<name>` xoá khỏi contract; FE đọc `qr_url`. |
| 4 | `docs_url` | GIỮ nguyên — ngoài scope. |
| 5 | RBAC | GIỮ `has_permission("Asset Commissioning","read")`. `ensure_asset_qr_token` chỉ set token, KHÔNG nâng quyền. |
| 6 | Lifecycle | KHÔNG double-emit `qr_generated` (ensure idempotent). KHÔNG emit `label_printed` (đó là `mark_label_printed` POST). |

**Endpoint QR cấp asset (A2/A3 — CHỐT ownership ở IMM-00 registry, KHÔNG IMM-04):**

**Endpoint QR cấp asset (A2/A3 — CHỐT ownership ở IMM-00 registry, KHÔNG IMM-04):**
- **Ownership chốt:** endpoint QR asset-bound đặt ở **`api/imm00.py` + `services/imm00.py`** (cùng nhà `AC Asset.qr_token` + `ensure_asset_qr_token` + `resolve_qr_token`). IMM-04 chỉ tham chiếu chéo — KHÔNG host logic QR asset. Spec đầy đủ: [`../imm-00/04_Backend_Design.md`](../imm-00/04_Backend_Design.md) §II.1.8b + [`../imm-00/05_API_Specification.md`](../imm-00/05_API_Specification.md).
- `assetcore.api.imm00.get_asset_label_data(asset)` / `get_asset_label_data_batch(assets)` → trả payload nhãn (`name, asset_code, device_model_name, location_name, lifecycle_status, qr_url`); **READ-ONLY về sự kiện in** (KHÔNG emit `label_printed`). Khác `generate_qr_label` (commissioning-bound, `internal_tag_qr`) — endpoint mới asset-bound (`qr_url = /a/<token>`).
- `assetcore.api.imm00.mark_label_printed(assets)` (POST) → emit lifecycle `label_printed` + audit, 1 event / asset / lần in.
- `assetcore.api.imm00.resolve_qr_token(token)` (A2 — V3, **đã có**): IMM-00 ownership. RBAC `asset.read`. Xem ADR-001 D2/D4.
- **A3 KHÔNG đụng IMM-04** `generate_qr_label`/`internal_tag_qr`. **Dedup CHỐT ở vòng 13 (§8.1.1):** `generate_qr_label` thêm `qr_url=/a/<token>` (tái dùng `ensure_asset_qr_token`+`_build_qr_url`), bỏ `scan_url` desk — field `internal_tag_qr` vẫn GIỮ.

---

## 9. Migration & Patch

**Patch path:** `assetcore/patches/v2/001_imm04_initial_setup.py`

**Đăng ký trong `patches.txt`:**
```
assetcore.patches.v2.001_imm04_initial_setup
```

**Migration steps:**
1. `bench --site <site> migrate` — apply DocType JSON
2. Import workflow fixture: `imm_04_workflow.json`
3. Seed `Required Document Type`: CO, CQ, Manual, Warranty, License, Radiation License
4. Import Custom Fields trên `Asset`: `custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref`
5. Tạo Role nếu chưa có: HTM Technician, Biomed Engineer, Vendor Engineer, QA Officer, Workshop Head, VP Block2

---

## 10. Non-functional

**Concurrency:**
- `vendor_serial_no` unique: app-layer check (VR-01) + khuyến nghị DB UNIQUE index (tech-debt)
- `create_ac_asset()`: dùng `db_set` commit ngay; cần wrap savepoint để rollback nếu IMM-05 import fail

**Caching:**
- `get_dashboard_stats()`: không cache hiện tại; recommend Redis cache TTL 5 phút
- `get_po_details()`: không cache; PO data ít thay đổi → TTL 1 phút acceptable

**Logging:**
- INFO: mọi lifecycle event created
- WARNING: VR-05 risk_class change, overdue phiếu
- ERROR: `create_ac_asset` fail, `create_initial_document_set` exception

**Idempotency:**
- `generate_qr_label()`: idempotent — `internal_tag_qr` đã có → trả giá trị hiện tại; `qr_url` (vòng 13) dựng qua `ensure_asset_qr_token` (idempotent — không sinh token thừa, không double-emit `qr_generated`)
- `create_initial_document_set()`: graceful skip nếu document đã tồn tại (`source_commissioning` check)

---

## 11. §ROWSCOPE — `list_commissioning`: MỘT ENGINE row-scoped (AC-CR-98) + `apply_vendor_scope` GIAO (AC-CR-106)

> **SSoT (BE đọc TRƯỚC KHI sửa mã, đừng suy diễn từ mục này):** [`../imm-00/ADR-IMM00-LIST-SCOPE.md §10`](../imm-00/ADR-IMM00-LIST-SCOPE.md) — `§10.4` đại số phép giao (8 shape) · `§10.5` bảng 9 bước của `list_commissioning` · `§10.6` semantics lỗi · `§10.7` Boundaries · `§10.8/§10.9` acceptance + nơi đặt test. Test map: [`07 §VIII`](./07_Testing_QA.md). FE: [`06 §11`](./06_Frontend_Design.md).

**Tóm tắt đủ để không code sai (chi tiết ở §10):**

| Điều | Trước 2026-07-30 | Sau |
|---|---|---|
| Đếm | `frappe.db.count(_DT, query_filters)` (`services/imm04.py:1076`) — **bỏ** `permission_query_conditions` | `count_with_or(_DT, query_filters, None)` (`services/shared/filters.py:236`) — `frappe.get_list` |
| Đọc | `frappe.get_all(_DT, …)` (`:1079-1083`) — **bỏ** row-scope | `frappe.get_list(_DT, …)`, **cùng** `query_filters`, cùng `pg["page_size"]` |
| Enrich nhãn | 5 × `frappe.get_all` | 4 lookup **GIỮ** `get_all` (DocType không row-scoped ⇒ đổi = **mất nhãn**); riêng **`AC Asset`** (`:1116`) đổi sang `get_list` vì **có** hook (`hooks.py:440`) |
| Vendor-scope | `filters[field] = ["in", assigned]` — **GÁN**, ghi đè caller (`services/shared/scope.py:174`) | **GIAO** caller ∩ assigned; ra **luôn** `["in", <list>]`; rỗng ⇒ `["in", ["__none__"]]`; **dict-in → dict-out** |

**Giữ nguyên tuyệt đối:** ROLE gate `frappe.has_permission(_DT,"read",throw=True)` (`:1055`, **2 lớp cùng tồn tại** ROLE + ROW) · whitelist `_ALLOWED_FILTER_KEYS` (`:132-137`) · mặc định `docstatus != 2` (`:1060-1061`) · virtual `overdue=1` → filter-list form (`:1067-1072`) · khoá trả về `{"items", "pagination"}` (`:1133`) · predicate `asset_commissioning_query` (`permissions.py:137-149`) **từng ký tự**.

**Cấm (§10.7):** ❌ `count_ignore_permissions` · ❌ né guard G4 bằng `frappe.db.get_value(s)` · ❌ đổi kiểu trả về `apply_vendor_scope` · ❌ thêm dòng vào `_RAW_QUERY_UNGATED_BACKLOG` (`tests/test_rowscope_scope_guard.py:89-107`, 17 → **16** sau vòng này).

**Nợ CÓ TÊN mở ra, KHÔNG land vòng này:** `AC-CR-99` (ô đếm chưa loại `docstatus==2`) · `AC-CR-107` (op không-giao-được đang fail-closed câm, chưa 400 in-envelope) · `AC-CR-108` (`vendor_engineer_name` là `Data`, không phải `Link → User` ⇒ nhánh vendor thực chất `owner`-only) · `AC-CR-109` (alias DocType hiệu chuẩn) · `AC-CR-110` (`_ORDER_MODIFIED` `:139` thiếu tiebreaker `name desc`).

### 11.1 Nhánh `overdue=1` = **shape thứ hai** của cùng predicate (AC-CR-112) + refresh cite theo đĩa 2026-07-30

> Quyết định: [`../imm-00/ADR-IMM00-LIST-SCOPE.md §11`](../imm-00/ADR-IMM00-LIST-SCOPE.md) (`ADR-IMM00-LIST-SCOPE-07` · `INV-COMM-SCOPE-5/6`) · TC: [`07 §IX`](./07_Testing_QA.md). **Vòng AC-CR-112 KHÔNG đổi mã prod theo kế hoạch** — chỉ chạy test + thêm TC; mọi sửa prod phải là root-cause của một ĐỎ thật.

`list_commissioning` có **2 shape** predicate và **1 đường đếm/đọc**:

| Shape | Khi nào | Biến | Đi tiếp vào |
|---|---|---|---|
| `dict` | mặc định | `safe_filters` | `count_with_or` → `frappe.get_list` |
| **list-form** `[[doctype, field, op, val], …]` | `_is_truthy(filters.get("overdue"))` (`:1101`) → `_dict_to_list_filters` (`:1102`) + append 3 điều kiện SoT `overdue_commissioning_filter()` (`:1103-1105`) | `query_filters` | **CÙNG** `count_with_or` (`:1113`) → **CÙNG** `frappe.get_list` (`:1116`) |

- `count_with_or(doctype, filters: dict | list | None, or_filters)` (`services/shared/filters.py:236-288`) nhận **cả hai** shape ⇒ bất biến `count == rows` là bất biến của **hàm**, không của một shape (`ADR-IMM00-LIST-SCOPE-07`). **CẤM** `frappe.db.count` / `count_ignore_permissions` ở `:1113` cho **cả hai** nhánh.
- Tham số ảo **mới** (vd `mine`, `due_soon`) mở nhánh shape mới ⇒ **bắt buộc** kèm TC dưới persona row-scoped (`07 §IX.2` là khuôn).
- Anchor overdue: `_OVERDUE_ANCHOR = "reception_date"` (`:64`) · `OVERDUE_DAYS = 30` (`:63`). **Bẫy fixture:** `reception_date` NULL ⇒ `< cutoff` là FALSE ⇒ 0 dòng ⇒ assert **vacuous**.

**Refresh cite (bảng §11 phía trên viết theo dòng lúc chốt AC-CR-98; giá trị ĐO LẠI hôm nay — tin số dưới đây):**

| Anchor | Cite cũ trong §11 | **Trên đĩa 2026-07-30** |
|---|---|---|
| `def list_commissioning` | `:1053` | **`:1055`** |
| ROLE gate `has_permission(_DT,"read",throw=True)` | `:1055` | **`:1088`** |
| `_ALLOWED_FILTER_KEYS` | `:132-137` | **`:133-138`** |
| mặc định `docstatus != 2` | `:1060-1061` | **`:1093-1094`** |
| virtual `overdue=1` → list-form | `:1067-1072` | **`:1101-1105`** |
| đếm (`count_with_or`) | `:1076` (bản `db.count` cũ) | **`:1113`** |
| đọc (`frappe.get_list`) | `:1079-1083` (bản `get_all` cũ) | **`:1116-1120`** |
| enrich `AC Asset` qua `get_list` | `:1116` | **`:1159`** |
| trả về `{"items","pagination"}` | `:1133` | **`:1176`** |
| `_ORDER_MODIFIED` | `:139` | **`:140`** |

---

## DoD — File 04 hoàn chỉnh

- [x] Quy ước ngôn ngữ BE: code tiếng Anh + field label tiếng Việt
- [x] DocType đầy đủ trường + naming + permissions sơ bộ
- [x] Workflow 11 states + transition matrix
- [x] Service layer public functions liệt kê + error handling pattern
- [x] Repository layer methods liệt kê
- [x] API layer thin wrapper với `_handle/_ok/_err`
- [x] Mọi error raise qua `ServiceError(ErrorCode.X, msg tiếng Việt)`
- [x] Audit trail trigger liệt kê
- [x] Scheduler jobs đăng ký
- [x] Integration nội bộ + ngoại bộ
- [x] Migration steps
- [x] Non-functional: concurrency, caching, logging, idempotency
