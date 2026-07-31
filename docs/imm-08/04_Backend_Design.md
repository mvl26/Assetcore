# 04 — Thiết kế Backend — IMM-08 Bảo trì định kỳ (PM)

| Mục | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phạm vi | Per-module |
| Owner | Tech Lead / BE Lead |
| Liên kết | [02 Analysis & Design](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) |
| Cập nhật | 2026-05-27 |

---

## 1. Tổng quan kiến trúc

IMM-08 bám kiến trúc **3-tier strict**: API (`api/imm08.py`) → Service (`services/imm08.py`) → Repository (`repositories/pm_repo.py`). Controller `pm_work_order.py` / `pm_schedule.py` chỉ delegate sang service (`validate_work_order`, `handle_work_order_submit`). API layer là thin wrapper dùng `_handle / _ok / _err`. Scheduler `generate_pm_work_orders_from_schedule` chạy daily.

```
Browser/Client
    │ HTTP (token/sid)
    ▼
api/imm08.py            ← 24 endpoints, thin wrapper (_handle/_ok/_err)
    │
    ▼
services/imm08.py       ← business logic (PMStatus / PMScheduleStatus enums)
    │
    ▼
repositories/pm_repo.py ← 4 Repo (Schedule / WO / Template / TaskLog)
    │
    ▼
Frappe ORM + MariaDB    ← 8 DocTypes (xem §2)
```

> **Quy ước ngôn ngữ:** Code/fieldname tiếng Anh · Field label tiếng Việt · Error message tiếng Việt qua `frappe._()` · DTO mirror FE TypeScript types

---

## 2. Domain Model — DocType

### 2.1 PM Schedule

- **Naming:** `format:PMS-{asset_ref}-{pm_type}` → unique per (asset, pm_type)
- **Submittable:** No — master record
- **Track changes:** Yes

| Trường | Type | Required | Default | Validation |
|---|---|---|---|---|
| `asset_ref` | Link → Asset | ✓ | — | search_index |
| `pm_type` | Select | ✓ | — | Quarterly/Semi-Annual/Annual/Ad-hoc |
| `status` | Select | — | Active | Active/Paused/Suspended |
| `pm_interval_days` | Int | ✓ | — | > 0 |
| `checklist_template` | Link → PM Checklist Template | ✓ | — | BR-08-01 |
| `alert_days_before` | Int | — | 7 | ≥ 0 |
| `responsible_technician` | Link → User | — | — | default KTV khi tạo WO |
| `last_pm_date` | Date | — | — | controller advance sau on_submit |
| `next_due_date` | Date | — | — | list_view, controller compute |
| `created_from_commissioning` | Link → Asset Commissioning | — | — | read_only, IMM-04 fill |

**Permissions sơ bộ:** PM Manager / AssetCore System User / System Manager = full · PM User / Corrective Manager / AssetCore Auditor = R

### 2.2 PM Checklist Template

- **Naming:** `format:PMCT-{asset_category}-{pm_type}`
- **Submittable:** No

| Trường | Type | Required | Notes |
|---|---|---|---|
| `template_name` | Data | ✓ | list_view |
| `asset_category` | Link → Asset Category | ✓ | search_index |
| `pm_type` | Select | ✓ | same options |
| `version` | Data | — | default "1.0" |
| `checklist_items` | Table → PM Checklist Item | ✓ | child table |

### 2.3 PM Work Order

- **Naming:** `PM-WO-.YYYY.-.#####`
- **Submittable:** Yes (docstatus 0→1 khi Completed)
- **Track changes:** Yes

| Trường | Type | Required | Notes |
|---|---|---|---|
| `asset_ref` | Link → Asset | ✓ | search_index |
| `pm_schedule` | Link → PM Schedule | ✓ | — |
| `pm_type` | Data | — | read_only, copy từ Schedule |
| `wo_type` | Select | — | Preventive/Corrective, default Preventive |
| `status` | Select | ✓ | 7 states, default Open |
| `is_late` | Check | — | read_only, controller compute |
| `due_date` | Date | ✓ | — |
| `completion_date` | Date | — | read_only, auto on_submit |
| `assigned_to` | Link → User | — | KTV |
| `overall_result` | Select | — | Pass/Pass with Minor Issues/Fail |
| `checklist_results` | Table → PM Checklist Result | — | child |
| `source_pm_wo` | Link → PM Work Order | conditional | `mandatory_depends_on: wo_type==='Corrective'` BR-08-02 |
| `attachments` | Attach Multiple | — | bắt buộc khi Class III BR-08-06 |

**Permissions:**

| Role | R | W | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| PM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| AssetCore System User | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PM User | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Corrective Manager | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| AssetCore Auditor | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

### 2.4 PM Task Log

- **Naming:** autoname hash
- **`in_create: 1`** — chặn update sau insert (BR-08-10)
- **Permissions:** all roles Read · PM Manager / AssetCore System User có Create · **KHÔNG có Write / Delete**

| Trường | Type | Required | Notes |
|---|---|---|---|
| `asset_ref` | Link → Asset | ✓ | search_index |
| `pm_work_order` | Link → PM Work Order | ✓ | — |
| `completion_date` | Date | ✓ | — |
| `is_late` | Check | — | mirror từ WO |
| `days_late` | Int | — | `date_diff(completion, due)` |
| `next_pm_date` | Date | — | `completion + interval` |
| `summary` | Text | — | mirror `technician_notes` |

---

## 3. Workflow (State Machine)

File fixture: `assetcore/workflow/imm_08_pm_work_order_workflow.json` (optional — hiện enforce qua controller + scheduler)

**States:**

<!-- allow_edit role đồng bộ source-of-truth `assetcore/assetcore/workflow/imm_08_pm_workflow.json` (reconcile vòng 8, 2026-05-29). -->

| State | Style | docstatus | allow_edit role |
|---|---|---|---|
| Open | Warning | 0 | PM User |
| In Progress | Primary | 0 | PM User |
| Pending–Device Busy | Warning | 0 | PM User |
| Overdue | Danger | 0 | System Manager |
| Completed | Success | 1 | System Manager |
| Halted–Major Failure | Danger | 0 | System Manager |
| Cancelled | Secondary | 2 | System Manager |

**Transitions:**

| From | To | Action label | Allowed role | Trigger |
|---|---|---|---|---|
| (insert) | Open | — | Scheduler | `tasks.generate_pm_work_orders` |
| Open / Overdue | In Progress | Phân công KTV | PM Manager | `assign_technician` |
| In Progress | Completed | Hoàn thành PM | PM User | `submit_pm_result` → `wo.submit()` |
| In Progress | Halted–Major Failure | Báo lỗi Major | PM User | `report_major_failure` |
| In Progress / Overdue | Pending–Device Busy | Hoãn lịch | PM Manager | `reschedule_pm` |
| Any (Open/In Progress) | Cancelled | Hủy | PM Manager | `on_cancel` |

**SSoT trạng-thái-kế-hợp-lệ — `_PM_VALID_TRANSITIONS` (server-driven CTA):**

`services/imm08.py:_PM_VALID_TRANSITIONS: dict[str, list[str]]` = map tập-trung GROUNDED chính xác `assetcore/assetcore/workflow/imm_08_pm_workflow.json` (7 state / 13 transition). `get_work_order(name)` emit `allowed_transitions = _PM_VALID_TRANSITIONS.get(wo.status, [])` vào detail dict → màn detail (web + mobile) render nút workflow **theo server**.

| Status hiện tại | `allowed_transitions[]` |
|---|---|
| `Open` | `In Progress`, `Overdue`, `Cancelled` |
| `Overdue` | `In Progress`, `Cancelled` |
| `In Progress` | `Completed`, `Halted–Major Failure`, `Pending–Device Busy`, `Cancelled` |
| `Pending–Device Busy` | `In Progress`, `Cancelled` |
| `Halted–Major Failure` | `In Progress`, `Cancelled` |
| `Completed` (terminal, docstatus=1) | `[]` |
| `Cancelled` (terminal) | `[]` |

> **ADR-IMM08-CTA — Server-driven CTA cho màn PM-detail (2026-06-16).**
> - **Context:** Trước round này CHỈ `IncidentDetail` (IMM-12, R3) emit `allowed_transitions[]`; `PmWorkOrderDetail`/Repair/Calibration KHÔNG → màn detail BUỘC hardcode `status → button` phía client (anti-pattern lifecycle/RBAC **dead-gate**, memory `factory_rounds_1_25`): client tự suy CTA, dễ lệch khi workflow đổi.
> - **Decision:** Bồi map tập-trung `_PM_VALID_TRANSITIONS` (1 SSoT) + emit `allowed_transitions[]` ở `get_work_order` — MIRROR pattern `imm12._VALID_TRANSITIONS` + `get_incident_detail` (R3). Schema mobile `array<string>` **KHÔNG enum-bound cứng** (né drift khi workflow đổi); codomain-check ở guard **phía service** (KHÔNG schema-enum).
> - **Consequences:** Client (web + codegen mobile) render CTA theo server → đổi workflow chỉ sửa 1 nơi (map + workflow JSON, guard SSoT-divergence chặn lệch). KHÔNG đụng workflow-engine / submit / start logic; handler signature `getPmWorkOrder` 0 đổi; KHÔNG path mới.
> - **Alternatives:** (a) giữ client-side state-gate — REJECTED (dead-gate, drift). (b) enum-bound `allowed_transitions.items` ở schema — REJECTED (schema phải sửa mỗi lần workflow đổi → drift-risk; codomain đã check ở guard service). (c) trả full transition-object {action,role} — DEFERRED (MVP chỉ cần next-state cho CTA; role-gate đã ở dispatcher/cap).

**Controller hooks:**

```python
# assetcore/assetcore/doctype/pm_work_order/pm_work_order.py
class PMWorkOrder(Document):
    def validate(self):
        from assetcore.services.imm08 import validate_work_order
        validate_work_order(self)   # gộp BR-08-02 / 06 / 08

    def on_submit(self):
        from assetcore.services.imm08 import handle_work_order_submit
        handle_work_order_submit(self)
```

---

## 4. Service Layer

File: `assetcore/services/imm08.py`

### Public functions

| Function | Input | Output | Side effect |
|---|---|---|---|
| `validate_work_order(doc)` | PM Work Order doc | None | raise ServiceError (BR-08-02/06/08/**19** gộp). Khi `doc.status ∈ {Completed, Halted–Major Failure}`: **guard bảng-kiểm-RỖNG TRƯỚC vòng lặp** — `if not (doc.checklist_results or []): nthrow_in_hook(MSG.IMM08_CHECKLIST_EMPTY)` (BR-08-19, bịt lỗ vacuous-pass) → rồi vòng lặp thiếu-result (BR-08-08 `IMM08_CHECKLIST_INCOMPLETE`) → duration (BR-08-09) → sticker (BR-08-10). Precedence EMPTY > INCOMPLETE. |
| `compute_next_pm_date(completion_date, interval=None)` | str/date + int? | `str` | None — **SoT DUY NHẤT** cho ngày PM kế tiếp (BR-08-03). `= add_days(getdate(completion_date), effective_interval)`; `effective_interval = interval nếu interval and interval > 0, else PM_DEFAULT_INTERVAL_DAYS (=90)`. Anchor LUÔN là `completion_date`, KHÔNG bao giờ `nowdate()`. Mọi write-site PHẢI gọi hàm này — CẤM inline lại `add_days(...)`. |
| `handle_work_order_submit(doc)` | PM Work Order doc | None | set completion, advance PM Schedule, sync Asset, ghi PM Task Log, tạo CM nếu Fail-Major. `next_pm_date` (Asset + PM Task Log) = `compute_next_pm_date(doc.completion_date, sched_interval)` |
| `submit_result(name, ..., client_request_id="")` | str + kwargs | dict `{name,new_status,is_late,next_pm_date,cm_wo_created}` | đóng WO, chuyển status `Completed`. Field trả về `next_pm_date` = `compute_next_pm_date(wo.completion_date, sched_interval)` — **byte-for-byte == PM Schedule.next_due_date đã persist == AC Asset.next_pm_date == PM Task Log.next_pm_date**. **Idempotency (BR-08-18 / ADR-IMM08-IDEMPOTENCY-01)**: param optional `client_request_id`. Rỗng ⇒ legacy (WO `docstatus==1` → `nthrow(IMM08_ALREADY_SUBMITTED)`). Non-empty ⇒ nhánh already-submitted **re-read terminal state → trả CÙNG payload 5-key**, KHÔNG áp lại side-effect (completion_date/next_pm_date KHÔNG drift, CM WO count KHÔNG tăng). Race cùng key: 1 winner commit `wo.submit()`, loser bắt exception va-chạm → re-read → trả payload winner (KHÔNG rò `IMM08_ALREADY_SUBMITTED`/'must be unique'). **KHÔNG DocField mới, KHÔNG migrate**. **Anti-drop idx (BR-08-20, OPTIONAL BE-2)**: khi `wo.checklist_results` ≥1 dòng, nếu `result_map` (từ payload) chứa `idx` KHÔNG khớp dòng nào (`len(result_map) > applied`) → `nthrow(MSG.IMM08_CHECKLIST_IDX_UNKNOWN)` (KHÔNG drop câm). Guard IDX bỏ qua khi WO 0-dòng (nhường cổng EMPTY). |
| `report_major_failure(pm_wo_name, *, failure_description)` | str + str | dict | set `Halted–Major Failure`, gọi `_create_cm_wo_from_failure` |
| `reschedule(name, *, new_date, reason)` | str + str + str | dict | chuyển `Pending–Device Busy`, lưu reason |
| `generate_pm_work_orders_from_schedule()` | — | dict | scheduler daily: tạo WO mới + đánh `Overdue` |
| `backfill_pm_schedules_for_due_assets()` | — | dict | scheduler daily: tạo PM Schedule cho Asset đến hạn chưa có lịch |
| `create_pm_schedule_from_commissioning(doc)` | Asset Commissioning doc | str / None | tạo PM Schedule khi commissioning submit |
| `create_pm_schedule_from_asset(asset_doc, method)` | AC Asset doc | str / None | hook AC Asset.after_insert → tạo PM Schedule nếu `is_pm_required=1` |
| `apply_template_to_category_assets(template_name)` | str | dict `{template, asset_category, created, skipped, errors}` | bulk-tạo PM Schedule cho mọi asset cùng danh mục; bỏ qua asset đã có lịch cùng `pm_type` |
| `get_dashboard_stats(*, year, month)` | int, int | dict | BR-08-13 — `kpis` tách 2 khối phạm vi: THÁNG (`total_scheduled`, `completed_on_time`, `overdue_in_month`, `pending_in_month`, `compliance_rate_pct` null-safe, `avg_days_late`) + GLOBAL (`overdue`=`count_overdue_pm()`, RC-10). Population THÁNG = WO **không-Cancelled** (`scheduled`, INV-PM-KPI-6). INV-PM-KPI-1..3,6 (§4.1.4) |
| `get_calendar(*, year, month, ...)` | int, int, ... | dict | — |
| `get_due_pm_schedules(days=30, limit=50)` | int, int | dict `{items, threshold_days}` | **CR-28b F8 "Nhắc việc" nửa-PM** — read-only list LỊCH PM sắp/quá hạn. Filter 3-clause `[status="Active", next_due_date is set, next_due_date <= add_days(today,days)]` (NULL-coerce guard BẮT BUỘC — mirror bẫy `get_due_calibrations`), `order_by next_due_date asc`, `page_size=limit`; enrich `asset_name` (`AssetRepo.get_value`, mirror `list_schedules`); derive `days_left = date_diff(next_due_date, today)` signed. return rows-key **`items`** (KHÔNG `data`), KHÔNG pagination. VERBATIM mirror `imm11.get_due_calibrations` — nguồn KHÁC (`PM Schedule.next_due_date` vs `AC Asset.next_calibration_date`). Spec đầy đủ §05 §0.1.5 + ADR-IMM08-DUEPM + [`ADR-MOBILE-054`](../mobile/ADR-MOBILE-054.md). ⚠️ NEW `.py` → worker reload PENDING USER. |
| `is_pm_overdue(status, due_date, ref_date=None)` | str, date, date? | `bool` | None — pure SoT predicate (BR-08-11), `due_date < today` strict + status ∈ overdue-source |
| `due_soon_filter(window_end, ref_date=None)` | date, date? | `dict` | None — pure SoT window filter builder (BR-08-12), `{due_date: [between, [ref_date, window_end]], status: [not in, [Completed, Cancelled]]}` |
| `count_overdue_pm(user=None)` | str? | `int` | None — counter dùng chung KPI/dashboard (BR-08-11), đếm `status == Overdue` |
| `attach_pm_checklist_photo(work_order_name, checklist_item_idx, filedata=None, filename="", content_type="")` | str, int, bytes?, str, str | dict `{file_url, file_name, checklist_item_idx}` | **BR-08-15/16 (mobile CR-14/G6)** — đính ảnh bằng chứng per-mục checklist PM (NĐ98 Class C/D). Thứ tự reject TRƯỚC File.insert: exists(WO)→NOT_FOUND · permission (assigned/write)→FORBIDDEN · idx→row VALIDATION · file present/content-type/size/max-count VALIDATION. Success: `File.insert(is_private=1, attached_to='PM Work Order', attached_to_field=f"checklist_results.photo.{idx}")` → `frappe.db.set_value("PM Checklist Result", row.name, "photo", file_url)` (**KHÔNG `wo.save()`** — tránh re-validate BR-08-08/docstatus) → `create_lifecycle_event(pm_checklist_photo_attached)` (hard-req, event throw→rollback) → commit. §05 #11 + ADR-IMM08-PHOTO-01/02. Đối xứng `imm12.attach_incident_photo`. |
| `_pm_checklist_photos(work_order_name, checklist_item_idx)` | str, int | `list[{file_url, file_name}]` | None — **SoT DUY NHẤT** cho ảnh của 1 mục checklist (mirror `_scene_photos` imm12). Query `File` private theo bộ-3 (`attached_to_doctype="PM Work Order"`, `attached_to_name`, `attached_to_field=f"checklist_results.photo.{idx}"`) `order_by creation asc`, lọc đuôi `.jpg/.jpeg/.png`. CÙNG helper dùng cho max-count check LẪN mọi liệt kê per-item ⇒ invariant **count==rows**. 1 query, KHÔNG N+1. |
| `_assert_can_attach_pm_photo(wo)` | PM Work Order doc | None | raise `ServiceError(FORBIDDEN)` nếu `wo.assigned_to != session.user` AND KHÔNG `frappe.has_permission("PM Work Order","write",doc=wo)` (BR-08-15; tái dùng IDOR-guard row-level `pm_work_order_has_permission`). |
| `get_work_order(name)` | str | `dict` | Chi tiết 1 PM WO (màn detail web + mobile `getPmWorkOrder`). CR-74: khuôn 3 lớp ROLE→EXISTS→ROW (`05 §12`). **AC-CR-77:** trả **THÊM** `available_actions: [4×AvailableAction]` (server-driven CTA; derive `_build_pm_available_actions(wo)`, READ-ONLY) **cạnh** `allowed_transitions` (**GIỮ NGUYÊN 100%** — giá trị + thứ tự + overlay CR-45b). Xem §4.3 + `05 §13` |
| `_build_pm_available_actions(wo)` | PM Work Order doc | `list[dict]` (4× `{key,label,route,enabled,reason}`) | **AC-CR-77** — SSoT 4 CTA server-driven `[start_work, submit_result, reschedule, report_major_failure]`; `enabled = transition_allowed ∩ has_cap ∩ business_gate`; `route=""`; reason VI 3 bậc; READ-ONLY (0 I/O ghi, 0 query thêm). `Cancelled` KHÔNG BAO GIỜ là action (không có endpoint). Xem §4.3.3 + ADR-IMM08-CTA-01/02/03 (`05 §13`) |
| `_pm_checklist_has_items(doc)` | PM Work Order doc | `bool` | **AC-CR-77** — BR-08-19 boolean SSoT (`len(checklist_results) > 0`). DÙNG CHUNG `validate_work_order` (enforce `IMM08_CHECKLIST_EMPTY`) + `_build_pm_available_actions.submit_result.business_gate` (advertise) ⇒ advertise == enforce. READ-ONLY. Xem §4.3.2 |

### ADR-IMM08-IDEMPOTENCY-01 — Idempotency `submit_pm_result` neo trên terminal-state của WO (KHÔNG DocField, KHÁC CR-24)

- **Status**: Accepted
- **Date**: 2026-07-18
- **Context**: Mobile write-outbox re-drain `submit_pm_result` khi *response success rớt mạng* (server ĐÃ complete WO nhưng client chưa persist payload → re-POST cùng body). Legacy: submit lần 2 lên WO `docstatus==1` → `nthrow(MSG.IMM08_ALREADY_SUBMITTED)` (`services/imm08.py:974`, in-handler HTTP-200 Error envelope) — với re-drain thì đây là lỗi "đã chốt" GIẢ, và nếu WO còn re-open được sẽ **drift `completion_date`/`next_pm_date`** (anchor BR-08-03) + **double-spawn CM WO**. Cần idempotent replay. **CR-24** (report_incident IMM-12) giải cùng lớp bằng **unique DocField `client_request_id` + `bench migrate`**. Nhưng acceptance đề mục này **cấm schema/DocField mới ⇒ cấm migrate**.
- **Decision**: Idempotency neo trên **trạng thái TERMINAL của chính PM Work Order** — KHÔNG field mới. `wo.name` LÀ idempotency key ở tầng resource; "biên nhận" bền của lần submit đầu = `docstatus==1` + `status=Completed` + `completion_date` đã persist + Corrective WO đã link qua `source_pm_wo`. Param optional **`client_request_id: str = ""`** (thêm CUỐI signature) là **caller-intent gate**: non-empty ⇒ nhánh already-submitted chuyển từ raise → **re-read state persist → dựng lại ĐÚNG payload 5-key `{name,new_status,is_late,next_pm_date,cm_wo_created}` → return success** (KHÔNG áp lại side-effect); rỗng ⇒ hành vi byte-identical legacy (raise). **Race** (2 request cùng key trên WO `docstatus==0`): 1 winner commit `wo.submit()`; loser bắt exception va-chạm (stale-doc / `DocstatusTransitionError` / duplicate) → **convert sang re-read terminal** → trả payload winner. KHÔNG rò `IMM08_ALREADY_SUBMITTED`/'must be unique'.
- **Alternatives**:
  - **(A) CR-24-style unique DocField `client_request_id` + migrate** — LOẠI: acceptance cấm schema/migrate; và WO ĐÃ có terminal-state bền = natural idempotency record đủ dùng (KHÁC report_incident: mỗi call mint doc MỚI, không có natural key sẵn) ⇒ thêm field là persist thừa.
  - **(B) `frappe.cache()`/Redis dedup-lock key `(wo_name, client_request_id)`** — LOẠI làm cơ chế CHÍNH: không bền qua worker-restart, và thừa vì terminal-state re-read đã đủ đúng. BE CÓ THỂ thêm như in-flight lock TÙY CHỌN để giảm noise exception-va-chạm, KHÔNG bắt buộc bởi contract.
- **Consequences**:
  - KHÔNG `bench migrate`, KHÔNG schema change ⇒ deploy = **worker reload** (`--preload`, HARD-STOP user) — KHÔNG cần reload-doctype.
  - Idempotency scope theo natural key `wo.name` ⇒ `(wo_name, client_request_id)` KHÔNG nhiễm chéo giữa WO khác nhau.
  - `completion_date` KHÔNG drift trên replay (re-read field persist; `next_pm_date` re-derive deterministic ⇒ cùng giá trị). CM WO count KHÔNG tăng (`find_one`, KHÔNG create).
  - **Đánh đổi**: vì KHÔNG lưu key, server KHÔNG verify `client_request_id` của replay == key đã complete WO. Chấp nhận: outbox re-POST cùng body (`item.id` bền) ⇒ replay luôn mang key khớp; và trả terminal-payload cho MỌI keyed-submit lên WO đã Completed là phản hồi an toàn/không phá (submit lên WO Completed vốn không phải thao tác mutating hợp lệ). Cần strict key-binding ⇒ Supersede bằng ADR CR-24-style field.
  - **Divergence với CR-24 là CHỦ ĐÍCH** — KHÔNG "đồng bộ" 2 module bằng cách thêm field cho IMM-08.

### ADR-IMM08-CHECKLIST-EMPTY-01 — Mã lỗi RIÊNG cho bảng-kiểm-rỗng (KHÔNG reuse `IMM08_CHECKLIST_INCOMPLETE`)

- **Status**: Accepted
- **Date**: 2026-07-19
- **Context**: Cổng BR-08-08 (`validate_work_order`) lặp `for item in (doc.checklist_results or [])` để bắt mục thiếu `result`. Khi WO có **0 dòng** checklist (tạo template-less / template 0 mục / BR-08-01 "phải có template" rò lọt ở đường ad-hoc), vòng lặp **vacuous-pass** ⇒ WO chuyển `Completed` + `handle_work_order_submit` sinh **PM Task Log KHÔNG bằng chứng công việc**, advance `next_pm_date` — nghiệm-thu-giả một lần PM chưa từng làm. Vi phạm CLAUDE.md §5 (mọi nghiệp vụ phải có record) + NĐ98 (hồ sơ bảo trì Class C/D). Cần **chặn** hoàn thành khi bảng kiểm rỗng.
- **Decision**: Thêm **guard riêng TRƯỚC vòng lặp** trong `validate_work_order` (`if not (doc.checklist_results or []): nthrow_in_hook(MSG.IMM08_CHECKLIST_EMPTY)`) + **mã lỗi MỚI** `IMM08_CHECKLIST_EMPTY` (≠ `IMM08_CHECKLIST_INCOMPLETE`). Fire qua `nthrow_in_hook` (DocType hook) → `frappe.ValidationError` → `submit_result` `except` wrap `ServiceError(VALIDATION)`; `wo.save()` rollback ⇒ **status giữ + docstatus=0**, MỌI side-effect (task-log/date/schedule) ở `handle_work_order_submit` post-submit KHÔNG chạm. **Reload-only** (KHÔNG DocField, KHÔNG migrate).
- **Alternatives**:
  - **(A) Reuse `IMM08_CHECKLIST_INCOMPLETE`** — LOẠI: template dùng `{item}` interpolation ("Mục '{item}' chưa điền") — bảng kiểm rỗng KHÔNG có item để nêu tên ⇒ message vô nghĩa; và **root-cause khác nhau** → INCOMPLETE = KTV quên điền (fix: điền nốt), EMPTY = WO thiếu bảng kiểm mẫu (fix: gắn template — lỗi cấu hình/BR-08-01, khác owner). Trộn 1 mã ⇒ FE/mobile/analytics không phân biệt được để triage.
  - **(B) Chặn ở tầng tạo WO (BR-08-01) thay vì cổng hoàn thành** — GIỮ như phòng-thủ tầng trên nhưng KHÔNG đủ: đường ad-hoc/template-0-mục vẫn tạo được WO 0-dòng; cổng hoàn thành là **hàng rào cuối** chống nghiệm-thu-giả bất kể WO lọt vào bằng đường nào. 2 tầng bổ trợ, không thay thế.
  - **(C) Auto-seed 1 dòng checklist mặc định khi rỗng** — LOẠI: che giấu lỗi cấu hình + tạo bằng chứng giả (dòng rỗng nội dung) = tệ hơn chặn.
- **Consequences**:
  - FE PM Detail: khi `message_code==IMM08-CHECKLIST-EMPTY` hiển thị hint "Chưa gắn bảng kiểm mẫu" + disable nút "Xác nhận hoàn thành" (khác toast "điền nốt mục" của INCOMPLETE). Xem `06_Frontend_Design.md`.
  - **Kèm** ADR anti-drop: mã `IMM08_CHECKLIST_IDX_UNKNOWN` (BR-08-20) cho drift idx payload — cùng nguyên tắc "làm lỗi loud, không câm". Precedence 3 mã: EMPTY(0-dòng) > IDX_UNKNOWN(≥1-dòng + idx lệch) > INCOMPLETE(≥1-dòng + idx khớp + thiếu result) — **mutually exclusive by row-count + payload-vs-rows**.
  - **Đánh đổi**: +1 (hoặc +2 với BR-08-20) mã trong `messages.py` + regen `frontend/src/i18n/messages.ts` (`gen_fe_messages.py`). KHÔNG schema/migrate.

**Constants (đầu file, mirror imm12 §40-50):**
```python
MAX_PM_CHECKLIST_PHOTOS = 5              # per mục checklist (mirror MAX_INCIDENT_PHOTOS)
MAX_PM_CHECKLIST_PHOTO_BYTES = 10 * 1024 * 1024
_PM_PHOTO_CONTENT_TYPES = ("image/jpeg", "image/jpg", "image/png")
_PM_PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png")
_EVENT_PM_CHECKLIST_PHOTO_ATTACHED = "pm_checklist_photo_attached"
# messages VN (Decision-B fields): _MSG_PM_PHOTO_MISSING / _NOT_IMAGE / _TOO_LARGE / _MAX / _IDX_INVALID / _FORBIDDEN
```

> **Field liên quan (ĐÃ tồn tại — KHÔNG migration schema):** `pm_checklist_result.photo` (`Attach`, permlevel=0) child của `PM Work Order.checklist_results`. Round này chỉ **ghi** vào field sẵn có + **thêm 1 option enum** `pm_checklist_photo_attached` vào `asset_lifecycle_event.json` (xem §6).

### Validators

```python
def _validate_checklist_complete(doc) -> None:
    """BR-08-08/19: bảng kiểm phải có mục VÀ mọi mục phải có result."""
    # BR-08-19 (guard rỗng TRƯỚC vòng lặp) — chặn nghiệm-thu-giả khi 0 dòng.
    # KHÔNG có guard này → vòng lặp vacuous-pass → WO Completed không bằng chứng.
    if not (doc.checklist_results or []):
        nthrow_in_hook(MSG.IMM08_CHECKLIST_EMPTY)   # → IMM08-CHECKLIST-EMPTY (422)
    # BR-08-08 (≥1 dòng): mọi mục phải có result.
    for row in doc.checklist_results:
        if not row.result:
            nthrow_in_hook(MSG.IMM08_CHECKLIST_INCOMPLETE, item=row.description)

def _validate_photo_for_high_risk(doc) -> None:
    """BR-08-06: Asset Class III phải có ảnh."""
    risk = frappe.db.get_value("Asset", doc.asset_ref, "custom_risk_class")
    if risk in ("III", "C", "D") and not doc.attachments:
        raise ServiceError(
            ErrorCode.VALIDATION,
            frappe._(f"Thiết bị nguy cơ cao (Class {risk}) bắt buộc upload ảnh trước/sau PM (BR-08-06).")
        )
```

### Error handling pattern

```python
from assetcore.services.shared.constants import ErrorCode
from assetcore.services.shared.errors import ServiceError

def handle_work_order_submit(doc) -> None:
    """Trigger on_submit: chốt completion, advance PM Schedule, sync Asset,
    ghi PM Task Log, sinh CM nếu Fail-Major."""
    if doc.docstatus != 1:
        raise ServiceError(ErrorCode.BAD_STATE, "PM Work Order chưa được Submit.")
    _set_completion(doc)
    _update_pm_schedule(doc)
    _update_asset_fields(doc)
    _create_pm_task_log(doc)
    _handle_failures(doc)
```

---

## 4.1 SoT — "PM đến hạn (due-soon)" vs "PM quá hạn (overdue)" (BR-08-11 / BR-08-12)

> **Self-Correction (vòng 23).** Trước fix có **2 định nghĩa cửa-sổ due-soon phân kỳ**:
> - KPI `pm_due_next7` (`api/dashboard.py:87`) đếm `due_date BETWEEN [today, today+7]` AND status NOT IN [Completed, Cancelled] — cửa sổ **có cận dưới** `today`.
> - Drill `/pm/work-orders?due_before=today+7` → `services/imm08.py::_normalize_filters` dịch thành `due_date <= today+7` — **KHÔNG có cận dưới** → mọi WO quá hạn (`due_date < today`, chưa Completed/Cancelled) lọt vào danh sách drill nhưng KHÔNG được KPI đếm.
>
> Hệ quả: số trên thẻ "PM đến hạn" ≠ số dòng khi click drill (drill là superset gồm cả overdue). Test cũ `test_d_be_18`/dashboard chỉ assert *route* của drill, không assert *convergence* — hợp-thức-hoá divergence.
>
> **Quyết định:** hợp nhất về **1 predicate cửa-sổ due-soon** dùng CHUNG cho KPI count + drill filter. `_normalize_filters(due_before=X)` PHẢI sinh `due_date BETWEEN [today, X]` (cận dưới = today, KHÔNG còn `<= X`). WO quá hạn KHÔNG còn thuộc due-soon — nó thuộc thẻ "PM quá hạn" (`pm_overdue`, status == Overdue) → hai tập **disjoint** (giống mô hình IMM-11 overdue vs due_soon, round 9).

### 4.1.1 Hằng + helper SoT (pure, không I/O)

```python
# services/imm08.py — module-level constant (1 hằng, KHÔNG hardcode "7" rải rác)
PM_DUE_SOON_WINDOW_DAYS = 7

def due_soon_filter(window_end, ref_date=None) -> dict:
    """SoT (BR-08-12): filter dict cho 'PM đến hạn (due-soon)' — dùng CHUNG bởi
    KPI count (dashboard.pm_due_next7) và drill list (_normalize_filters(due_before)).

    Cửa sổ = [ref_date, window_end] (cả 2 biên inclusive). status NOT IN
    [Completed, Cancelled] (đến hạn = chưa hoàn tất). WO quá hạn (due_date <
    ref_date) NẰM NGOÀI — thuộc tập overdue (BR-08-11, is_pm_overdue), disjoint.

    Args:
        window_end: cận trên cửa sổ (str/date) — KPI truyền today+PM_DUE_SOON_WINDOW_DAYS;
                    drill truyền due_before verbatim từ query.
        ref_date: cận dưới = mốc hôm nay (mặc định nowdate()).

    Returns:
        dict filter: {"due_date": ["between", [ref, window_end]],
                      "status": ["not in", [PMStatus.COMPLETED, PMStatus.CANCELLED]]}
    """
    ref = ref_date or nowdate()
    return {
        "due_date": ["between", [ref, window_end]],
        "status": ["not in", [PMStatus.COMPLETED, PMStatus.CANCELLED]],
    }
```

**Boundary chốt (BR-08-12):**

| `due_date` | Phân loại | Lý do |
|---|---|---|
| `today` | **DUE_SOON** (trong cửa sổ) | inclusive cận dưới |
| `today+7` | **DUE_SOON** (trong cửa sổ) | inclusive cận trên |
| `today+8` | NGOÀI cửa sổ | quá cận trên |
| `today-1` | NGOÀI due-soon → **OVERDUE** (BR-08-11) | `due_date < today` |
| bất kỳ + status ∈ {Completed, Cancelled} | luôn NGOÀI | đã hoàn tất/hủy |

### 4.1.2 Consumer dùng chung (count == drill, INVARIANT)

- **`_normalize_filters(due_before=X)`** PHẢI gọi `due_soon_filter(window_end=X)` thay vì literal `due_date <= X`. Output: `due_date BETWEEN [today, X]` + status NOT IN [Completed, Cancelled]. (cũ: `out["due_date"] = ["<=", due_before]` — XÓA cận-dưới-thiếu này.)
- **`api/dashboard.py` `pm_due_next7`** PHẢI gọi `due_soon_filter(next7)` (import từ `services.imm08`) — KHÔNG inline literal `{"due_date": ["between", [today_str, next7]], "status": [...]}`.
- **Persona block `dashboard.py:589` `pm_week`** (Kỹ thuật viên dashboard) cũng đếm cửa sổ `[today, today+7]` — PHẢI gọi cùng helper `due_soon_filter(add_days(today(), 7), ref_date=today())` (cộng filter `assigned_to=me`). Nếu cố ý giữ riêng phải ghi chú lý do.
- **INVARIANT đo được:** với MỌI dataset, `count(KPI pm_due_7d) == số dòng list khi drill ?due_before=today+7` (byte-for-byte cùng tập). WO quá hạn KHÔNG xuất hiện trong drill due-soon → thuộc thẻ `pm_overdue` (status==Overdue). Hai tập **disjoint** (overdue ∩ due-soon = ∅).
- **Grep guard:** 0 literal inline window cho PM due-soon còn sót ngoài `due_soon_filter`. `api/dashboard.py` không còn `{due_date: [between, [today_str, next7]]}` viết tay cho PM; kiểm cả persona `pm_week`.

### 4.1.3 Quan hệ với overdue SoT (BR-08-11 — đã có sẵn)

`is_pm_overdue(status, due_date, ref_date)` (đã tồn tại) định nghĩa overdue: `due_date < today` (strict) AND status ∈ `OVERDUE_SOURCE_STATES` {Open, In Progress, Pending–Device Busy}. Cron `check_pm_overdue` set `status=Overdue` theo predicate này; `count_overdue_pm()` đếm `status == Overdue`; drill `?overdue=1` (`_normalize_filters(overdue=1)`) trả cùng tập. Due-soon (BR-08-12) và overdue (BR-08-11) **disjoint by construction**: due-soon yêu cầu `due_date >= today`, overdue yêu cầu `due_date < today`.

### 4.1.4 Dashboard KPI — đồng nhất phạm vi tháng vs toàn-hệ-thống (BR-08-13, vòng 10)

> **Self-Correction (vòng 10).** RC-10 (vòng trước) đã đúng khi đổi `kpis.overdue` thành `count_overdue_pm()` **global** để khớp launcher widget + drill `?overdue=1`. NHƯNG sửa đó để lại **mâu thuẫn phạm vi không-đối-soát-được**: `get_dashboard_stats` đặt 1 field **toàn-hệ-thống** (`overdue`) đứng cạnh các field **bó-trong-tháng** (`total_scheduled`, `completed_on_time`, `compliance_rate_pct`) trong CÙNG dict `kpis` → FE render chung 1 strip. Phản ví dụ: tháng không có WO due nào nhưng còn 5 WO Overdue từ tháng trước → strip hiện "Tổng lên lịch: 0" cạnh "Quá hạn: 5" → người xem KHÔNG cách nào đối-soát (5 từ đâu ra khi tổng = 0?). Đồng thời `compliance_rate_pct = 0.0` khi `total==0` gây hiểu nhầm "tuân thủ 0%" trong khi thực ra "không có gì để đo".
>
> **Quyết định:** tách `kpis` thành **2 khối phạm vi** trong cùng payload, mỗi field có phạm vi DUY NHẤT & nhãn rõ ở FE. KHÔNG bỏ `overdue` global (giữ RC-10), THÊM `overdue_in_month` + `pending_in_month` cho khối tháng, và đổi `compliance_rate_pct` thành **null-safe**.

**Hai khối phạm vi (cùng payload `get_dashboard_stats(year, month)`):**

> **Self-Correction (vòng 25 — INV-PM-KPI-6).** Thiết kế gốc định nghĩa `total_scheduled = len(wos)` (MỌI status) và `pending_in_month = total − on_time − overdue_in_month` là **phần dư phủ kín mọi status còn lại** — chủ ý gồm cả `Cancelled-in-window`. Đây là **lỗi thiết kế gốc**: WO `Cancelled` (đã hủy chủ động, KHÔNG còn nghĩa vụ thực hiện) bị (a) tính vào MẪU compliance ⇒ kéo tụt `compliance_rate_pct` giả (vd 1/4=25.0 thay vì 1/3=33.3), và (b) rơi vào `pending_in_month` ⇒ phantom "chưa xong" không bao giờ ai làm. **Khắc phục:** loại `Cancelled` khỏi MẪU (`total_scheduled`) và mọi bucket tháng. Population mới = **WO không-Cancelled trong tháng** (`scheduled`).

**Population CHỐT (vòng 25):** `scheduled = [w for w in wos if w["status"] != PMStatus.CANCELLED]`. `total_scheduled = len(scheduled)`. Mọi field khối-tháng (mẫu, tử, các bucket) suy TỪ `scheduled` — KHÔNG từ `wos` thô. `Cancelled` KHÔNG vào bất kỳ bucket nào (không completed, không overdue, không pending).

| Field | Phạm vi | Định nghĩa BE |
|---|---|---|
| `total_scheduled` | **THÁNG** | `len(scheduled)` = số WO `due_date BETWEEN [start_month, end_month]` ∧ `status != Cancelled` (mẫu compliance — KHÔNG còn `len(wos)`) |
| `completed_on_time` | **THÁNG** | `⊆ scheduled`: `status==Completed ∧ !is_late` (tử compliance) |
| `overdue_in_month` | **THÁNG** | `⊆ scheduled`: `status==Overdue ∧ due_date trong tháng` — đếm TỪ `scheduled` đã lọc, KHÔNG gọi `count_overdue_pm()` |
| `pending_in_month` | **THÁNG** | `total_scheduled − completed_in_month − overdue_in_month` (phần dư trên population đã-loại-Cancelled; trừ TẤT CẢ Completed (on-time + late), KHÔNG chỉ on-time → Completed-late KHÔNG rơi vào pending; `Cancelled` đã ngoài `total_scheduled` nên cũng KHÔNG rơi vào đây) |
| `compliance_rate_pct` | **THÁNG** | `round(completed_on_time/total_scheduled*100, 1)` nếu `total_scheduled>0`, ngược lại **`None`** (FE '—') |
| `avg_days_late` | **THÁNG** | trung bình `date_diff(completion, due)` của WO completed-late trong tháng (KHÔNG đổi) |
| `overdue` | **TOÀN HỆ THỐNG** | `count_overdue_pm()` (RC-10, GIỮ NGUYÊN) — status==Overdue mọi thời gian; khớp launcher + drill `?overdue=1` |

> **Lưu ý phạm vi (OUT-of-scope vòng 25):** `Halted–Major Failure` (lỗi nặng → CM) GIỮ counted trong population (kết cục PM **không-tuân-thủ thật**, rơi vào `pending_in_month` như cũ). CHỈ loại `Cancelled`. `count_overdue_pm()` global + quy tắc `is_late` + shape/field-name KHÔNG đổi.

**INVARIANT đo được (BR-08-13):**
- **INV-PM-KPI-1:** `total_scheduled >= completed_on_time + overdue_in_month + pending_in_month` (luôn, mọi dataset). Đẳng thức chỉ khi KHÔNG có Completed-late; khi có Completed-late thì WO đó là phần "dôi" (đã hoàn thành nhưng KHÔNG on-time, KHÔNG overdue, KHÔNG pending — đã trừ qua `completed_in_month`) ⇒ vế phải `< total_scheduled`. `pending_in_month` là phần-dư trên population đã-loại-Cancelled → bất biến `≥` giữ kể cả khi xuất hiện status mới. ⇒ `overdue_in_month <= total_scheduled` luôn đúng. KHÔNG còn `Cancelled` lọt vào bất kỳ bucket nào.
- **INV-PM-KPI-2:** `overdue` (global) độc lập, KHÔNG ràng buộc với `total_scheduled`; có thể `overdue > total_scheduled` (chính xác về ngữ nghĩa — global ⊋ tháng) NHƯNG hai field ở 2 khối khác nhau, FE KHÔNG đặt chung strip.
- **INV-PM-KPI-3:** tử & mẫu compliance CÙNG `scheduled` (đã loại Cancelled); `total_scheduled==0 ⇒ compliance=None`.
- **INV-PM-KPI-6 (loại Cancelled khỏi mẫu — vòng 25):** WO `status==Cancelled` KHÔNG vào `total_scheduled`, KHÔNG vào MẪU compliance, KHÔNG vào `pending_in_month`/`overdue_in_month`/`completed_on_time`. Hệ quả đo được:
  - Tháng `{1 Completed on-time, 1 Completed late, 1 Overdue, 1 Cancelled}` → `total_scheduled==3` (KHÔNG 4), `compliance_rate_pct==round(1/3*100,1)==33.3` (cũ sai `1/4==25.0`), `completed_on_time==1`, `overdue_in_month==1`, `pending_in_month==0` (`3 − 2 completed − 1 overdue = 0`; Completed-late nằm trong `completed_in_month`, KHÔNG pending; Cancelled ngoài mẫu).
  - Tháng chỉ-Cancelled (vd 2 Cancelled, 0 khác) → `total_scheduled==0` ⇒ `compliance_rate_pct==None` (KHÔNG `0.0`), `pending_in_month==0`, `overdue_in_month==0`.
  - **No-regression:** tháng KHÔNG có Cancelled → mọi KPI GIỮ NGUYÊN giá trị như trước fix (Cancelled-free path bất biến — vì `scheduled == wos` khi không có Cancelled).
  - `trend_6months[*].rate` dùng CÙNG predicate loại-Cancelled (`t = số WO không-Cancelled trong tháng`) — cùng 1 SoT với tile compliance tháng hiện tại. `count_overdue_pm()` global + `is_late` + shape/field-name KHÔNG đổi.

**Implementation (delta so với `get_dashboard_stats` hiện tại, services/imm08.py:858):**

```python
# INV-PM-KPI-6: population khối-tháng = WO KHÔNG-Cancelled (loại WO đã hủy khỏi mẫu).
# Cancelled = đã hủy chủ động, KHÔNG còn nghĩa vụ → không kéo compliance, không phantom pending.
scheduled = [w for w in wos if w["status"] != PMStatus.CANCELLED]
total = len(scheduled)                                    # = total_scheduled (KHÔNG còn len(wos))
completed = [w for w in scheduled if w["status"] == PMStatus.COMPLETED]
on_time   = [w for w in completed if not w["is_late"]]
# THÁNG: đếm overdue TỪ scheduled (due_date trong tháng, đã loại Cancelled) — KHÔNG dùng count_overdue_pm()
overdue_in_month = sum(1 for w in scheduled if w["status"] == PMStatus.OVERDUE)
completed_in_month = len(completed)                       # TẤT CẢ Completed (on-time + late)
pending_in_month = total - completed_in_month - overdue_in_month  # phần dư → INV-PM-KPI-1 (Completed-late KHÔNG vào pending; Cancelled ngoài mẫu)
# GLOBAL (RC-10, giữ nguyên): khớp launcher + drill ?overdue=1
overdue_global = count_overdue_pm()
compliance_rate = round(len(on_time) / total * 100, 1) if total else None  # null-safe (INV-PM-KPI-3/6)
# avg_days_late: tính từ completed (đã trên scheduled) — Cancelled không có completion_date hợp lệ, không đổi
...
# trend_6months: t = số WO KHÔNG-Cancelled trong tháng (CÙNG predicate với tile — INV-PM-KPI-6)
#   month_scheduled = [w for w in month_wos if w["status"] != PMStatus.CANCELLED]
#   t = len(month_scheduled); rate = round(c_on / t * 100, 1) if t else 0.0
return {
    "kpis": {
        "total_scheduled":     total,             # = len(scheduled), KHÔNG còn Cancelled
        "completed_on_time":   len(on_time),
        "overdue_in_month":    overdue_in_month,
        "pending_in_month":    pending_in_month,
        "compliance_rate_pct": compliance_rate,   # number | None
        "avg_days_late":       avg_days_late,
        "overdue":             overdue_global,    # GLOBAL — KHÔNG đổi (RC-10)
    },
    "trend_6months": trend,
}
```

> `avg_days_late` KHÔNG đổi ngữ nghĩa (INV-PM-KPI-6 no-regression). `trend_6months[*].rate` dùng CÙNG mẫu loại-Cancelled (`t = số WO không-Cancelled trong tháng`) — KHÔNG để trend lệch chuẩn so với tile compliance tháng hiện tại (cùng 1 SoT predicate). Drill từ tile "Quá hạn (toàn hệ thống)" vẫn route `?overdue=1` → `count_overdue_pm()`.

---

## 4.2 SoT — "Ngày PM kế tiếp" (next_pm_date / next_due_date) (BR-08-03)

> **Self-Correction (vòng 1).** Thiết kế gốc của BR-08-03 chỉ ghi công thức (`next_pm_date = completion_date + interval`, KHÔNG due_date) NHƯNG **không bắt buộc 1 nguồn-sự-thật-duy-nhất** → implementation đã trôi thành **3 bản inline phân kỳ trên 2 trục**:
>
> | Write-site | Anchor (mốc) | Default interval khi `pm_interval_days` rỗng/0 |
> |---|---|---|
> | `update_pm_schedule_after_completion` (:452-453) → persist `PM Schedule.next_due_date` | `completion_date` ✅ | `or 90` ✅ |
> | `handle_work_order_submit` (:253-256, :269) → set `AC Asset.next_pm_date` + `PM Task Log.next_pm_date` | `completion_date` ✅ | `or 0` ❌ |
> | `submit_result` (:622-623) → field `next_pm_date` API trả về | `nowdate()` ❌ | `or 0` ❌ |
>
> **2 hệ quả divergence thật:**
> 1. **Anchor lệch (`nowdate()` vs `completion_date`):** khi PM hoàn thành trễ / backdated (`completion_date != today`), `submit_result` trả `next_pm_date` tính từ HÔM NAY, trong khi `PM Schedule.next_due_date` (đã persist) tính từ `completion_date` → API trả 1 ngày, DB lưu 1 ngày khác → KTV thấy lịch kế tiếp mâu thuẫn với phản hồi vừa nhận. Vi phạm trực tiếp mệnh đề BR-08-03 "KHÔNG dùng due_date" (và mặc nhiên KHÔNG dùng nowdate).
> 2. **Default lệch (`or 0` vs `or 90`):** khi `pm_interval_days` rỗng/0, `PM Schedule.next_due_date` nhảy `+90` ngày, nhưng `AC Asset.next_pm_date` chỉ `+0` = `completion_date` (hôm nay) → asset LẬP TỨC bị scheduler `backfill_pm_schedules_for_due_assets` coi là **PM-overdue giả** (`next_pm_date <= today`) trong khi PM Schedule báo còn 90 ngày. Báo động sai + tạo lịch trùng.
>
> **Quyết định:** hợp nhất về **1 helper SoT `compute_next_pm_date`** + **1 hằng `PM_DEFAULT_INTERVAL_DAYS = 90`**. Mọi write-site gọi CHUNG — KHÔNG inline lại `add_days(...)`, KHÔNG dùng literal `90`, KHÔNG dùng `nowdate()` làm anchor.

### 4.2.1 Hằng + helper SoT (pure, không I/O)

```python
# services/imm08.py — module-level constant (1 hằng, KHÔNG literal 90 rải rác)
PM_DEFAULT_INTERVAL_DAYS = 90

def compute_next_pm_date(completion_date, interval=None) -> str:
    """SoT DUY NHẤT (BR-08-03): ngày PM kế tiếp = completion_date + interval hiệu lực.

    INVARIANT anchor: LUÔN dùng completion_date (mốc hoàn thành thực tế của WO),
    KHÔNG bao giờ nowdate(). Khi PM hoàn thành trễ/backdated, giá trị này phải
    bằng nhau byte-for-byte ở MỌI nơi: PM Schedule.next_due_date (persist),
    AC Asset.next_pm_date, PM Task Log.next_pm_date, và field next_pm_date mà
    submit_result trả về.

    INVARIANT default: interval hiệu lực = interval nếu interval và interval > 0,
    else PM_DEFAULT_INTERVAL_DAYS (=90). Khi pm_interval_days rỗng/0, schedule —
    asset — API CÙNG nhảy +90 ngày → asset KHÔNG còn hiện PM-overdue giả trong khi
    schedule báo 90 ngày.

    Args:
        completion_date: mốc hoàn thành WO (str/date) — anchor BẮT BUỘC.
        interval: số ngày chu kỳ PM (int/None). None hoặc <= 0 → dùng default 90.

    Returns:
        str: ngày PM kế tiếp (chuỗi YYYY-MM-DD do add_days trả về).
    """
    effective = interval if interval and interval > 0 else PM_DEFAULT_INTERVAL_DAYS
    return add_days(getdate(completion_date), effective)
```

### 4.2.2 Consumer dùng chung (4 write-site, INVARIANT byte-for-byte)

| Write-site | TRƯỚC (inline, phân kỳ) | SAU (gọi SoT) |
|---|---|---|
| `update_pm_schedule_after_completion` | `interval = sched.pm_interval_days or 90; sched.next_due_date = add_days(getdate(completion_date), interval)` | `sched.next_due_date = compute_next_pm_date(completion_date, sched.pm_interval_days)` |
| `handle_work_order_submit` → `AC Asset.next_pm_date` | `sched_interval = ... or 0; _add_days(doc.completion_date, sched_interval)` | `compute_next_pm_date(doc.completion_date, sched_interval)` |
| `handle_work_order_submit` → `PM Task Log.next_pm_date` | `_add_days(doc.completion_date, sched_interval)` | `compute_next_pm_date(doc.completion_date, sched_interval)` |
| `submit_result` → field trả về | `add_days(nowdate(), sched_interval)` (anchor SAI) | `compute_next_pm_date(wo.completion_date, sched_interval)` |
| `PM Schedule.before_save` (controller — **PERSISTER thực sự** của `next_due_date`) | `interval = pm_interval_days or 0; next_due_date = add_days(last_pm_date, interval)` (inline, `or 0` ⇒ interval=0 bỏ qua recompute → giá trị cũ kẹt) | `next_due_date = compute_next_pm_date(last_pm_date, pm_interval_days)` (anchor=last_pm_date, default trong helper) |

- `sched_interval` ở `handle_work_order_submit` / `submit_result` truyền `pm_interval_days` **THÔ** từ PM Schedule (có thể rỗng/0/None) — KHÔNG còn `or 0` / `or 90` tại call-site; việc chọn default 90 nằm DUY NHẤT trong `compute_next_pm_date`.
- **Latent 4th site (controller persister):** `PM Schedule.before_save` chạy SAU service-layer set `next_due_date` và RECOMPUTE từ `last_pm_date` (== `completion_date` sau PM). Trước đây dùng inline `add_days(last_pm_date, pm_interval_days or 0)` → là nguồn phân kỳ ẩn (đặc biệt khi `pm_interval_days=0`: nhánh `if last_pm_date and interval` bị bỏ qua, để giá trị cũ kẹt). Nay đi qua `compute_next_pm_date` → đồng nhất default 90 + anchor=last_pm_date với toàn bộ SoT. Lazy-import `compute_next_pm_date` trong `before_save` (tránh circular).
- **INVARIANT byte-for-byte:** sau 1 lần submit WO, với MỌI `completion_date` (kể cả backdated) và MỌI `pm_interval_days` (kể cả 0/rỗng):
  `submit_result.next_pm_date == PM Schedule.next_due_date (persist) == AC Asset.next_pm_date == PM Task Log.next_pm_date`.
- **Grep guard (PASS bắt buộc):**
  - 0 occurrence `add_days(nowdate(), <interval>)` cho next_pm_date/next_due_date ở BẤT KỲ đâu (anchor nowdate bị cấm cho ngày PM kế tiếp).
  - 0 occurrence inline `add_days(...completion_date.../last_pm_date..., interval)` cho next_pm_date/next_due_date NGOÀI thân `compute_next_pm_date` (chỉ còn trong helper + docstring) — kể cả `PM Schedule.before_save`.
  - 0 literal `90` cho interval ngoài hằng `PM_DEFAULT_INTERVAL_DAYS`; 0 `or 0` / `or 90` rải rác ở call-site (service + controller). _Lưu ý:_ `create_pm_schedule_from_asset` còn `pm_interval_days or 0` để CHỌN `pm_type` (qua `_PM_TYPE_FROM_INTERVAL`) — KHÔNG phải tính next-date, nằm ngoài phạm vi BR-08-03.

### 4.2.3 Quan hệ với BR-08-05 (is_late) và overdue (BR-08-11)

`compute_next_pm_date` chỉ tính NGÀY KẾ TIẾP, độc lập với `is_late` (BR-08-05: `is_late = completion_date > due_date`). Khi anchor đã đúng = `completion_date`, asset chỉ bị scheduler coi PM-overdue khi `next_pm_date <= today` THẬT (đến hạn) — không còn overdue-giả do `+0`. Default 90 đảm bảo asset thiếu cấu hình `pm_interval_days` vẫn có chu kỳ hợp lý thay vì kẹt ở hôm nay.

---

## 4.3 `_build_pm_available_actions` — SSoT CTA server-driven màn chi tiết phiếu PM (AC-CR-77) 🟢 ĐÃ LAND (2026-07-26)

> ✅ Land ĐÚNG khuôn dưới đây. Dòng THẬT: hằng `:163-209` · `_pm_checklist_has_items` **:212-229** · `_build_pm_available_actions` **:231-302** · wire `get_work_order` **:1058** · 4 điểm chạm §4.3.4 land ĐỦ (1 emit · 2 `validate_work_order:530` · 3 `reschedule:1501` · 4 `assign_technician:1257`). Test: `test_imm08::TestPmAvailableActions` 14 TC (TC-PMCTA-01..14).

> Hợp đồng đầy đủ + bảng chân trị + bất biến + ADR-IMM08-CTA-01/02/03: [`05 §13`](./05_API_Specification.md). Mục này chỉ mô tả **cấu trúc code** để BE dán vào `assetcore/services/imm08.py`.

### 4.3.1 Hằng + SSoT (module-level, đặt cạnh `_PM_VALID_TRANSITIONS` `:127` / `RESCHEDULE_CTA_STATES` `:153`)

```python
# services/imm08.py — import BỔ SUNG (hiện CHƯA có): rbac
from assetcore.services.shared import rbac

# ── SSoT cap của 4 endpoint ghi (advertise & enforce đọc CÙNG 1 chỗ) ──────────
# GIÁ TRỊ PHẢI == rbac.require(...) trong api/imm08.py (110/120/145/157). CẤM literal thứ 2.
_CAP_PM_WRITE = "pm.write"          # assign_technician :114 · report_major_failure :151
_CAP_PM_SUBMIT = "pm.submit"        # submit_pm_result :129
_CAP_PM_RESCHEDULE = "pm.reschedule"  # reschedule_pm :158

# ── Tập status mà «Hoãn lịch» có nghĩa (ADR-IMM08-CTA-02) ────────────────────
# = mọi status KHÔNG-terminal, dẫn xuất TỪ SSoT map (thêm state vào map → tự vào đây).
# DÙNG CHUNG cho advertise (_build_pm_available_actions) LẪN enforce (reschedule()).
# INVARIANT (test): RESCHEDULE_CTA_STATES ⊆ RESCHEDULE_ACTION_STATES (neo với CR-45b).
RESCHEDULE_ACTION_STATES = frozenset(_PM_VALID_TRANSITIONS) - {
    PMStatus.COMPLETED, PMStatus.CANCELLED,
}

# ── Reason VI (CHỈ khi enabled=False) — 3 bậc: transition > capability > business ──
# HẰNG, KHÔNG f-string: nội suy mã status ('In Progress'…) = rò tiếng Anh ra UI.
_PM_ACTION_REASON_TRANSITION = (
    "Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu")
_PM_ACTION_REASON_CAPABILITY = "Bạn không có quyền thực hiện thao tác này"
_PM_ACTION_REASON_NO_TECHNICIAN = "Phiếu chưa được phân công kỹ thuật viên"
_PM_ACTION_REASON_CHECKLIST_EMPTY = (
    "Chưa có mục bảng kiểm — không thể nghiệm thu phiếu bảo trì định kỳ")

# ── SSoT 4 CTA (thứ tự = thứ tự render FE) ───────────────────────────────────
# `endpoint` = tên hàm THẬT trong assetcore/api/imm08.py — guard INV-PMCTA-4 resolve
# ĐỘNG + kiểm `fn in frappe.whitelisted`. Không có endpoint ⇒ KHÔNG có CTA (vì sao
# 'Cancelled' vắng mặt dù là đích hợp lệ trong _PM_VALID_TRANSITIONS — ADR-IMM08-CTA-01).
_PM_ACTION_SPECS: tuple[dict, ...] = (
    {"key": "start_work", "label": "Bắt đầu bảo trì", "endpoint": "assign_technician",
     "target": PMStatus.IN_PROGRESS, "from": (PMStatus.OPEN, PMStatus.OVERDUE),
     "cap": _CAP_PM_WRITE},
    {"key": "submit_result", "label": "Hoàn thành bảo trì", "endpoint": "submit_pm_result",
     "target": PMStatus.COMPLETED, "from": (PMStatus.IN_PROGRESS,),
     "cap": _CAP_PM_SUBMIT},
    {"key": "reschedule", "label": "Hoãn lịch", "endpoint": "reschedule_pm",
     "target": PMStatus.PENDING_BUSY, "from": tuple(sorted(RESCHEDULE_ACTION_STATES)),
     "cap": _CAP_PM_RESCHEDULE},
    {"key": "report_major_failure", "label": "Báo lỗi nghiêm trọng",
     "endpoint": "report_major_failure", "target": PMStatus.HALTED_MAJOR,
     "from": (PMStatus.IN_PROGRESS,), "cap": _CAP_PM_WRITE},
)
```

### 4.3.2 Predicate dùng chung advertise ⇔ enforce

```python
def _pm_checklist_has_items(doc) -> bool:
    """BR-08-19 boolean SSoT — phiếu có ≥1 mục bảng kiểm.

    DÙNG CHUNG: validate_work_order (ENFORCE — `if not _pm_checklist_has_items(doc):
    nthrow_in_hook(MSG.IMM08_CHECKLIST_EMPTY)`, thay guard inline `:379-380`) và
    _build_pm_available_actions.submit_result.business_gate (ADVERTISE) ⇒ thẻ/nút là
    TẤM GƯƠNG của validator, không phải bản diễn giải thứ hai.
    """
    return bool(doc.checklist_results or [])
```

### 4.3.3 `_build_pm_available_actions(wo) -> list[dict]`

```python
def _build_pm_available_actions(wo) -> list[dict]:
    """AC-CR-77 — 4 CTA server-driven; enabled = transition ∩ cap ∩ business.

    Mirror imm12._build_incident_available_actions / imm00._build_available_actions.
    READ-ONLY: chỉ đọc wo.status / wo.assigned_to / wo.checklist_results + rbac.can.
    Bất biến D9: enabled False ⟹ reason != "" (mọi status, kể cả '' và mã lạ);
    enabled True ⟹ reason == "". Shape = AvailableAction {key,label,route,enabled,reason}.
    """
    status = wo.status or ""
    valid_targets = _PM_VALID_TRANSITIONS.get(status, [])
    actions: list[dict] = []
    for spec in _PM_ACTION_SPECS:
        if spec["key"] == "reschedule":
            # ADR-IMM08-CTA-02: service-action NGOÀI workflow ⇒ KHÔNG xét target ∈ map
            # (workflow không có Open→Pending / Overdue→Pending) và KHÔNG đọc overlay.
            transition_ok = status in RESCHEDULE_ACTION_STATES
        else:
            transition_ok = spec["target"] in valid_targets and status in spec["from"]
        has_cap = rbac.can(spec["cap"])
        business_ok, business_reason = True, ""
        if spec["key"] == "start_work" and not wo.assigned_to:
            business_ok, business_reason = False, _PM_ACTION_REASON_NO_TECHNICIAN
        elif spec["key"] == "submit_result" and not _pm_checklist_has_items(wo):
            business_ok, business_reason = False, _PM_ACTION_REASON_CHECKLIST_EMPTY
        enabled = bool(transition_ok and has_cap and business_ok)
        if enabled:
            reason = ""
        elif not transition_ok:
            reason = _PM_ACTION_REASON_TRANSITION
        elif not has_cap:
            reason = _PM_ACTION_REASON_CAPABILITY
        else:
            reason = business_reason or _PM_ACTION_REASON_TRANSITION  # fallback an toàn
        actions.append({"key": spec["key"], "label": spec["label"], "route": "",
                        "enabled": enabled, "reason": reason})
    return actions
```

### 4.3.4 Điểm chạm còn lại (4 chỗ — nhỏ, KHÔNG đổi hành vi công khai)

| # | Chỗ sửa | Nội dung | Rủi ro |
|---|---|---|---|
| 1 | `get_work_order` (`:895-903`) | thêm `"available_actions": _build_pm_available_actions(wo)` **cạnh** `allowed_transitions`. `allowed_transitions` **KHÔNG đổi 1 ký tự** (A6) | 0 — additive |
| 2 | `validate_work_order` (`:379-380`) | thay `if not (doc.checklist_results or []):` bằng `if not _pm_checklist_has_items(doc):` | 0 — cùng biểu thức |
| 3 | `reschedule` (`:1335-1336`) | thay `if wo.status in (PMStatus.COMPLETED, PMStatus.CANCELLED):` bằng `if wo.status not in RESCHEDULE_ACTION_STATES:` (giữ nguyên `validation(...)` + literal message) | 0 — **cùng tập status bị chặn**, verify bằng INV-PMCTA-8 |
| 4 | `assign_technician` (`:1092`) | thêm ngay sau load: `if not (technician or "").strip(): raise validation("Phải chọn kỹ thuật viên trước khi bắt đầu bảo trì")` ⇒ khớp `business_gate` của `start_work` (advertise == enforce) | thấp — hiện call rỗng **âm thầm** flip WO sang `In Progress` với `assigned_to` trống (lỗ dữ liệu). KHÔNG dùng MSG-code mới (né coupling `gen_fe_messages`) |

**Không làm trong vòng này:** nới `assign_technician` cho `Pending–Device Busy`/`Halted–Major Failure` (B1) · guard status cho `report_major_failure` (B3) · chặn `reschedule` ở `Halted–Major Failure` (B4) — xem `05 §13.10`.

---

## 4.4 `_ALLOWED_FILTER_KEYS` — SSoT khoá `filters` của `list_pm_work_orders` (AC-CR-79) 🔴 SPEC

> Hợp đồng đầy đủ + 3 ADR: [`05_API_Specification.md §14`](./05_API_Specification.md). Mục này chỉ là **code-shape**.

### 4.4.1 Helper CHUNG — `assetcore/services/shared/filters.py` (cạnh `pop_search`)

**Một** nơi biết cách raise; **mỗi module** tự khai tập khoá của mình ⇒ không có bản chép tay thứ hai.

```python
_MAX_ECHOED_KEYS = 5
_SAFE_KEY_RE = re.compile(r"\A[A-Za-z0-9_]{1,64}\Z")


def _safe_key(k: str) -> str:
    """Chuẩn hoá khoá do CLIENT gửi trước khi ĐƯA VÀO message trả về.

    Khoá lọc hợp lệ luôn là identifier. Bất kỳ thứ gì khác (chuỗi rỗng, khoảng
    trắng, ký tự SQL/HTML, >64 ký tự) ⇒ KHÔNG phản chiếu nguyên văn — tránh biến
    message lỗi thành kênh reflected-content.
    """
    s = str(k)
    return s if _SAFE_KEY_RE.match(s) else "<khoá không hợp lệ>"


def assert_allowed_filter_keys(f: dict | None, allowed: frozenset[str]) -> None:
    """Chặn khoá `filters` KHÔNG thuộc whitelist của module — 400 IN-ENVELOPE.

    Vì sao tồn tại: `frappe.get_list(filters={<khoá lạ>: …})` ném
    `OperationalError(1054, "Unknown column 'tab<DocType>.<khoá>' in 'WHERE'")`,
    mà `utils/api_handler.handle` CỐ Ý không bắt Exception chung (`:44-49`) ⇒ lỗi
    INPUT thoát ra **HTTP-500 KHÔNG có `body.success`** và **lộ tên bảng/cột SQL**.

    Args:
        f: filter dict SAU parse_json/vendor-scope/mine/search injection.
        allowed: whitelist của module (`_ALLOWED_FILTER_KEYS`).

    Raises:
        ServiceError: `code=INVALID_PARAMS`, `http_status=400`,
            `message_code=MSG.VAL_INVALID_FILTER_KEY`.
    """
    unknown = sorted(set(f or {}) - allowed)
    if not unknown:
        return
    shown = [_safe_key(k) for k in unknown[:_MAX_ECHOED_KEYS]]
    if len(unknown) > _MAX_ECHOED_KEYS:
        shown.append(f"(và {len(unknown) - _MAX_ECHOED_KEYS} khoá khác)")
    nthrow(
        MSG.VAL_INVALID_FILTER_KEY,
        invalid_keys=", ".join(shown),
        allowed_keys=", ".join(sorted(allowed)),
    )
```

- **`sorted()`** cả 2 vế ⇒ message **DETERMINISTIC** (test/diff/cache ổn định — cùng lý do `open_repair_filter` dùng `sorted`).
- **Không** echo giá trị filter (chỉ tên khoá) — giá trị có thể là dữ liệu người bệnh/thiết bị.
- `nthrow` import **trong thân hàm** hoặc top-file tuỳ vòng-import hiện có của `filters.py` — **kiểm tra circular trước** (`shared/filters.py` đang không import `utils.notify`).

### 4.4.2 Hằng SSoT — `services/imm08.py` (module-level, đặt cạnh `_PM_LIST_FIELDS` `:783`)

```python
# AC-CR-79 — SSoT DUY NHẤT tập khoá `filters` được honor bởi `list_work_orders`.
# Khoá ngoài tập này ⇒ 400 IN-ENVELOPE (KHÔNG còn OperationalError 1054 → HTTP-500
# lộ `tabPM Work Order.<cột>`). OAS `PmWorkOrderFilters` + guard `cr79_*` ĐỌC/SO
# THẲNG hằng này — KHÔNG chép tay lần hai. Mỗi khoá có consumer THẬT (`05 §14.3`);
# thêm khoá CHỈ khi có consumer + TC.
_ALLOWED_FILTER_KEYS = frozenset({
    # ── cột THẬT trên `PM Work Order` ────────────────────────────────────────
    "name", "status", "asset_ref", "assigned_to", "supervisor",
    "pm_type", "wo_type", "due_date", "completion_date",
    "overall_result", "is_late", "source_pm_wo",
    # ── khoá ẢO (bị pop/dịch TRƯỚC khi xuống `frappe.get_list`) ─────────────
    "overdue",        # → `_normalize_filters` :461 → status == Overdue
    "due_before",     # → `due_soon_filter` (BR-08-12) → cửa-sổ `due_date`
    "overdue_live",   # → `_list_pm_overdue_live` :931 (chip mobile "Quá hạn")
    "search",         # → `pop_search` (OR-LIKE name/asset_ref + asset_name)
})
```

**Khoảng ngày KHÔNG có khoá riêng** — dùng toán tử `_OP_TOKENS` (`:447`) trên `due_date`:
`{"due_date": ["between", ["2026-01-01","2026-12-31"]]}` (ADR-IMM08-FILTERKEY-03).

### 4.4.3 Điểm cắm — **1 dòng**, TRƯỚC `run_rowscoped`

```python
def list_work_orders(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    # AC-CR-79: validate khoá TRƯỚC pop `overdue_live` / `pop_search` /
    # `_normalize_filters` ⇒ 4 khoá ảo còn nguyên trong dict lúc kiểm (nên chúng
    # PHẢI ∈ whitelist) và ngữ nghĩa của chúng KHÔNG đổi (AC5). Đặt NGOÀI
    # `run_rowscoped` vì `ServiceError` ≠ `PermissionError` — không bị nhánh 403 nuốt.
    assert_allowed_filter_keys(filters, _ALLOWED_FILTER_KEYS)
    return run_rowscoped(_list_work_orders, filters, page=page, page_size=page_size)
```

`_list_work_orders` (`:928`) **KHÔNG đổi 1 dòng nào** ⇒ payload success byte-identical (INV-FKEY-1).

### 4.4.4 MSG registry — `assetcore/utils/messages.py`

```python
    VAL_INVALID_FILTER_KEY = "VAL-INVALID-FILTER-KEY"   # cạnh VAL_INVALID_PARAMS :70
```

```python
    MSG.VAL_INVALID_FILTER_KEY: {
        "title": "Bộ lọc không hợp lệ",
        "template": ("Bộ lọc chứa khoá không được hỗ trợ: {invalid_keys}. "
                     "Các khoá hợp lệ: {allowed_keys}."),
        "action_hint": ("Bỏ các khoá lọc không hợp lệ rồi thử lại. Nếu bạn không tự "
                        "đặt bộ lọc này, hãy tải lại trang."),
        "severity": "warning",
        "http_status": 400,
    },
```

`http_status=400` ⇒ `_bucket_for` (`utils/notify.py:53`) map sang **`ErrorCode.INVALID_PARAMS`** — **không**
thêm bucket mới (ADR-IMM08-FILTERKEY-02). Sau khi thêm: chạy `python3 scripts/gen_fe_messages.py` rồi
`python3 scripts/gen_fe_messages.py --check` phải **OK** (parity `frontend/src/i18n/messages.ts`).

### 4.4.5 Ranh giới đo được

| Bất biến | Kiểm bằng |
|---|---|
| `filters` rỗng/absent ⇒ **không** lỗi | INV-FKEY-4 |
| malformed JSON vẫn `VAL-INVALID-PARAMS` (đường `parse_json` cũ) | INV-FKEY-5 |
| khoá `apply_vendor_scope` bơm ∈ whitelist, **tính TỪ** `_VENDOR_SCOPE_FIELD_MAP` | INV-FKEY-3 / AC4 |
| message **không** chứa `Unknown column` / `tabPM Work Order` / `OperationalError` / `SELECT` | AC1 assert phủ định |

---

## 4b. Repository Layer

File `assetcore/repositories/pm_repo.py` định nghĩa 4 repository extends `BaseRepository`:

| Repo | DocType | Dùng cho |
|---|---|---|
| `PMScheduleRepo` | `PM Schedule` | CRUD + scheduler query (`status=Active`, `next_due_date<=today+alert`) |
| `PMWorkOrderRepo` | `PM Work Order` | CRUD + dashboard / calendar aggregate |
| `PMChecklistTemplateRepo` | `PM Checklist Template` | Template CRUD + clone vào WO |
| `PMTaskLogRepo` | `PM Task Log` | Audit-final insert sau khi WO Completed |

Service `imm08.py` gọi qua repository (`PMWorkOrderRepo.set_values`, `PMWorkOrderRepo.get`, …) — không `frappe.db.*` thô trừ ở scheduler `generate_pm_work_orders_from_schedule` (idempotency check).

Idempotency key scheduler: `(pm_schedule, status NOT IN [Completed, Cancelled])` — xem `generate_pm_work_orders_from_schedule` line 175.

---

## 5. API Layer

File: `assetcore/api/imm08.py`

Pattern thin wrapper dùng `_handle / _ok / _err`:

```python
import frappe
from assetcore.utils.helpers import _handle, _ok, _err, _parse_json
from assetcore.services import imm08 as service

@frappe.whitelist()
def list_pm_work_orders(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    parsed = _parse_json(filters, field_name="filters", default={})
    return _handle(service.list_pm_work_orders, parsed, int(page), int(page_size))

@frappe.whitelist(methods=["POST"])
def assign_technician(name: str, technician: str, scheduled_date: str = None) -> dict:
    return _handle(service.assign_technician, name, technician, scheduled_date)

@frappe.whitelist(methods=["POST"])
def submit_pm_result(name: str, checklist_results: str = "[]",
                     overall_result: str = "", technician_notes: str = "",
                     pm_sticker_attached: int = 0, duration_minutes: int = 0) -> dict:
    results = _parse_json(checklist_results, field_name="checklist_results", default=[])
    return _handle(service.submit_pm_result, name, results, overall_result,
                   technician_notes, pm_sticker_attached, duration_minutes)

@frappe.whitelist(methods=["POST"])
def reschedule_pm(name: str, new_date: str, reason: str) -> dict:
    if not reason or len(reason.strip()) < 5:
        return _err("Lý do hoãn lịch là bắt buộc (tối thiểu 5 ký tự).", "VALIDATION")
    return _handle(service.reschedule_pm, name, new_date, reason)
```

**Helper `_handle`:**

```python
def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "IMM-08 API Error")
        return _err("Lỗi hệ thống. Vui lòng thử lại.", "INTERNAL")
```

> **⚡ Verb-flip `assign_technician` (Mobile-BE binding — ADR-IMM08-MOB-01 / ADR-MOBILE-012):** code-sketch trên đã khai `@frappe.whitelist(methods=["POST"])` cho `assign_technician` (đúng doc-intent có sẵn) NHƯNG **source thật `api/imm08.py:46` vẫn còn bare `@frappe.whitelist()`** (nhận GET) — **verb-parity gap R33 BỎ SÓT** (R33 đã flip `submit_pm_result` `imm08.py:54` + 3 write-action imm11, SÓT `assign_technician`; sibling imm08 của `add_measurement` imm11 — ADR-MOBILE-011). `assign_technician` là **write-action DISPATCH** (status Open/Overdue→In Progress + asset→Under Maintenance, KHÔNG idempotent ⇒ POST đúng-semantics). **Hành động (BE Bước 4):** flip ĐÚNG 1 dòng decorator `api/imm08.py:46` bare→`@frappe.whitelist(methods=['POST'])` (signature/body/`rbac.require('pm.write')` `:49` UNCHANGED) ⇒ source khớp doc + mobile-contract POST ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()`. Mobile contract đầy đủ: [`05_API_Specification.md §0.1.1`](./05_API_Specification.md) + [`docs/mobile/04-api-contract.md §8.25`](../mobile/04-api-contract.md) + [`docs/mobile/ADR-MOBILE-012.md`](../mobile/ADR-MOBILE-012.md). Sau flip cần USER reload gunicorn `--preload` (LIVE reject GET 405) — HARD-STOP USER, KHÔNG curl-verify LIVE (LL-DEPLOY-07).

---

## 6. Audit Trail

| Trigger | Entry type | Actor | Payload |
|---|---|---|---|
| WO on_submit (Completed) | PM Task Log insert | KTV | asset, pm_type, completion, is_late, overall_result |
| Fail-Major submit | PM Task Log + CM WO insert | KTV | failure_description, failed_items |
| Overdue scheduler | db.set_value log | System | status=Overdue, days_overdue |
| Reschedule | technician_notes append | Workshop Manager | old_date → new_date, reason |
| **Đính ảnh mục checklist PM** (BR-08-16) | **`Asset Lifecycle Event` `pm_checklist_photo_attached`** | KTV / assigned | `asset=wo.asset_ref`, `root_doctype="PM Work Order"`, `root_record=WO`, `notes="Đính ảnh mục <idx>: <filename>"` — **hard-req** (commit cùng File, event throw→rollback, KHÔNG swallow) |

Hash chain: sử dụng Frappe native `track_changes` trên PM Work Order. PM Task Log immutable (`in_create=1`) là audit-final record.

> **⚡ Enum change (deploy — HARD-STOP USER, KHÔNG chặn test):** thêm option **`pm_checklist_photo_attached`** vào Select `event_type` của `Asset Lifecycle Event` (`assetcore/assetcore/doctype/asset_lifecycle_event/asset_lifecycle_event.json`) — nối tiếp `incident_photo_attached` (Vòng 1). Ghi `event_type` ngoài Select sẽ bị nuốt/throw → BẮT BUỘC mở enum trước khi LIVE. Deploy: `bench --site miyano reload-doctype "Asset Lifecycle Event"` + `clear-cache`. Test seed event qua `create_lifecycle_event` (không phụ thuộc reload live). Xem **ADR-IMM08-PHOTO-02** (`05 §2 #11`).

---

## 7. Background jobs / Scheduler

Đăng ký trong `assetcore/hooks.py`:

```python
scheduler_events = {
    "daily": [
        "assetcore.services.imm08.backfill_pm_schedules_for_due_assets",
        "assetcore.services.imm08.generate_pm_work_orders_from_schedule",
    ],
}

doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            # ...
        ],
    },
    "AC Asset": {
        "after_insert": "assetcore.services.imm08.create_pm_schedule_from_asset",
    },
    "PM Work Order": {
        "validate": "assetcore.services.imm16.gate_wo_submit",
        "on_submit": "assetcore.services.imm16.eval_imm08_09_realtime",
    },
}
```

| Job | Tần suất | Hook | Mục đích |
|---|---|---|---|
| `backfill_pm_schedules_for_due_assets` | Daily | `services.imm08` | Tạo PM Schedule cho Asset đến hạn nhưng chưa có lịch (safety net) |
| `generate_pm_work_orders_from_schedule` | Daily | `services.imm08` | Sinh PM WO mới từ PM Schedule đến hạn + đánh `Overdue` cho WO quá ngày |

**Idempotency key:** trong service đã check `(pm_schedule, status NOT IN [Completed, Cancelled])` → skip nếu đã tồn tại.

---

## 8. Integration

**Module nội bộ:**
- IMM-04 → IMM-08 (Pattern A): `Asset Commissioning.on_submit` → `assetcore.services.imm08.create_pm_schedule_from_commissioning` tạo PM Schedule đầu tiên (xem `hooks.py` §doc_events).
- AC Asset → IMM-08 (Pattern A): `AC Asset.after_insert` → `assetcore.services.imm08.create_pm_schedule_from_asset` tạo PM Schedule ngay khi Asset được tạo nếu `is_pm_required=1`.
- IMM-08 (backfill scheduler): `backfill_pm_schedules_for_due_assets` daily — safety net tạo PM Schedule cho Asset chưa có lịch.
- IMM-08 → IMM-09: Halted–Major Failure hoặc Fail-Major → `_create_cm_wo_from_failure(doc, priority)` insert một `Asset Repair` (doctype CM, không phải PM Work Order) với `source_pm_wo` liên kết. Function nằm trong `services/imm08.py`.
- IMM-08 ↔ IMM-16 (Pattern C compliance gate): `PM Work Order.validate` gọi `imm16.gate_wo_submit(doc, method=None)` — gate raise ServiceError nếu CAPA Critical chặn. `on_submit` gọi `imm16.eval_imm08_09_realtime` để cập nhật scorecard.
- IMM-08 → Notification Framework (E5, Pattern A — vòng 7): `PM Work Order.on_update` → `assetcore.services.notifications.notify_escalation`. Khi WO chuyển VÀO state escalation (`Halted–Major Failure`: `doc_status=0`, VÀO bởi PM User, GỠ bởi System Manager) → báo supervisor + System Manager để can thiệp. Engine đọc Workflow metadata động (KHÔNG hard-code tên state). Spec: `docs/imm-00/04_Backend_Design.md §III.1b-5`.

**Bên ngoài:**
- Frappe Email Queue: daily summary + escalation email

---

## 9. Migration & Patch

| Patch | Path | Mục đích |
|---|---|---|
| Wave 1 (current) | deploy via `bench migrate` | DocTypes + roles fixtures |
| Wave 2 (planned) | `assetcore/patches/v3_0/imm08_align_to_ac_asset.py` | Migrate `Link→Asset` sang `Link→AC Asset`, cập nhật field paths |

Fixtures: roles (`Workshop Head`, `HTM Technician`, `VP Block2`, `CMMS Admin`, `Biomed Engineer`) tại `fixtures/roles.json`.

---

## 10. Non-functional

**Concurrency:** Frappe optimistic lock qua `doc.modified` check — 2 KTV không thể submit cùng WO.

**Caching:** Dashboard stats không cache hiện tại — xem xét Redis cache TTL 5 phút nếu latency > 800ms.

**Logging:**
```python
frappe.logger("imm08").info(f"PM WO {wo_name} submitted by {frappe.session.user}")
frappe.logger("imm08").warning(f"Skip PM WO for {asset} — Out of Service")
```

**Idempotency:** Scheduler `generate_pm_work_orders` kiểm tra existing WO trước khi insert.

---

## DoD — File 04 hoàn chỉnh

- [x] Quy ước ngôn ngữ BE: code tiếng Anh + field label tiếng Việt
- [x] 6 DocType nêu đầy đủ trường + naming + permissions
- [x] Quan hệ liên DocType vẽ rõ
- [x] State machine + transitions định nghĩa
- [x] Mọi mutation map về service function với type hints
- [x] Mọi error raise qua `ServiceError(ErrorCode.X, "msg tiếng Việt")`
- [x] API layer dùng `_handle / _ok / _err`
- [x] Audit trail trigger liệt kê
- [x] Index DB cho query nóng
- [x] 2 background job đăng ký rõ
- [x] Integration IMM-04 + IMM-09 liệt kê
- [x] Patch path xác định
