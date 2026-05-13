# Wave 2 Alignment — IMM-06 / IMM-15 / IMM-16 (Block 2 & 3)

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-05 |
| Trạng thái | LIVE — phải đọc trước khi triển khai IMM-06 / IMM-15 / IMM-16 |
| Phạm vi | Hiệu chỉnh tài liệu IMM-06 (Training & Competency), IMM-15 (Spare Parts Inventory), IMM-16 (Compliance & CAPA) cho khớp **Wave 1 + Wave 2 batch 1 thực tế** trên codebase |
| Tài liệu cùng cấp | `WAVE2_ALIGNMENT.md` (cho IMM-01/02/03) — **đọc cả hai** trước khi viết code |

---

## 0. Mục đích

Bộ docs IMM-06 / 15 / 16 ở phiên bản v0.2 đã align ~92 % với codebase, nhưng còn 6 nhóm sai lệch hệ thống. Tài liệu này là **bản ghi đè bắt buộc** — khi triển khai 3 module này, mọi điểm trong file `IMM-{06,15,16}_*.md` phải được đọc theo bảng bên dưới (không cần sửa thủ công ở từng file). Coi đây là source of truth cuối cùng cho Block 2 & 3.

Nguyên tắc xuyên suốt giữ nguyên từ `WAVE2_ALIGNMENT.md` §1–§13 (single Frappe module `AssetCore`, audit qua `IMM Audit Trail`, envelope `{success, data|error, code}`, ErrorCode enum, hooks.py không có key `quarterly`).

---

## 1. Naming series — domain prefix, KHÔNG nhúng số module

**Nguyên tắc:** Naming series là **mã dữ liệu** mô tả bản chất bản ghi (Training Session, CAPA, Allocation…), KHÔNG phải tiền tố module phát triển. "IMM-06" / "IMM-15" / "IMM-16" chỉ là số định danh module trong tài liệu phát triển — không xuất hiện trong mã dữ liệu nghiệp vụ.

Wave 1 đã chứng minh quy ước này: `CAPA-.YYYY.-.#####`, `RCA-.YYYY.-.####`, `NC-.YY.-.MM.-.#####`, `ALE-.YYYY.-.#######`, `AC-SP-.YYYY.-.####`, `AC-SM-.YYYY.-.#####`, `AC-PUR-.YYYY.-.#####` — tiền tố luôn là viết tắt **tên loại dữ liệu**.

**Quy ước chuẩn cho Block 2/3 (đã apply vào docs ngày 2026-05-05):**

| DocType | Naming series | Diễn giải |
|---|---|---|
| IMM Training Session | `TRN-.YYYY.-.#####` | Training Session |
| IMM User Competency | `COMP-.YYYY.-.#####` | User Competency |
| IMM Competency Gap Report | `GAP-.YYYY.-.#####` | Gap Report |
| IMM Spare Allocation | `SAL-.YYYY.-.#####` | Spare Allocation |
| IMM Stock Cycle Count | `CYC-.YYYY.-.#####` | Cycle Count |
| IMM Spare Part Forecast | `SFC-.YYYY.-.#####` | Spare Forecast (phân biệt `IMM Demand Forecast` IMM-01) |
| IMM Spare Batch | `BAT-.YYYY.-.#####` | Lot/expiry |
| IMM Compliance Finding | `FND-.YYYY.-.#####` | Compliance Finding |
| IMM Internal Audit | `AUD-INT-.YYYY.-.#####` | Internal Audit (phân biệt `IMM Supplier Audit` legacy `SA-…`) |
| IMM Compliance Scorecard | `SCR-.YYYY.-.MM.-.#####` | Scorecard tháng |
| IMM Management Review | `MR-.YYYY.-.#####` | Management Review |

Hash thống nhất 5 chữ số (`.#####`); year prefix `.YYYY.` (4 chữ số) trừ legacy giữ nguyên `.YY.`.

**Master DocType (config, ít bản ghi):** giữ `field:<code>` autoname (vd `IMM Training Program.program_code`, `IMM Critical Spare Watchlist.watchlist_name`, `IMM Compliance Rule.rule_code`) — không cần series.

### 1.1 Refactor Wave 2 batch 1 + IMM-04 — đã đổi cùng đợt

DocType LIVE đã được rename về domain-only ngày 2026-05-05 (records cũ giữ tên cũ; records mới dùng prefix mới):

| DocType | Cũ | Mới |
|---|---|---|
| Asset Commissioning | `IMM04-.YY.-.MM.-.#####` | `ACC-.YY.-.MM.-.#####` |
| IMM Needs Request | `IMM01-NR-.YY.-.MM.-.#####` | `NR-.YY.-.MM.-.#####` |
| IMM Procurement Plan | `IMM01-PP-.YY.-.#####` | `PP-.YY.-.#####` |
| IMM Demand Forecast | `IMM01-DF-.YYYY.-.#####` | `DF-.YYYY.-.#####` |
| IMM Tech Spec | `IMM02-TS-.YY.-.#####` | `TS-.YY.-.#####` |
| IMM Market Benchmark | `IMM02-MB-.YY.-.#####` | `MB-.YY.-.#####` |
| IMM Lock-in Risk Assessment | `IMM02-LR-.YY.-.#####` | `LR-.YY.-.#####` |
| IMM Vendor Evaluation | `IMM03-VE-.YY.-.#####` | `VE-.YY.-.#####` |
| IMM Procurement Decision | `IMM03-PD-.YY.-.#####` | `PD-.YY.-.#####` |
| IMM AVL Entry | `IMM03-AVL-.YYYY.-.#####` | `AVL-.YYYY.-.#####` |
| IMM Supplier Audit | `IMM03-SA-.YY.-.#####` | `SA-.YY.-.#####` |
| IMM Vendor Scorecard | `format:VS-{period_year}-Q{period_quarter}-{supplier}` | giữ nguyên (đã domain-only) |

**Reuse — không động:** `CAPA-.YYYY.-.#####`, `IMM-AUD-.YYYY.-.#######`, `RCA-.YYYY.-.####`, `AC-SP-.YYYY.-.####`, `AC-SM-.YYYY.-.#####`, `AC-WH-{####}`, `AC-PUR-.YYYY.-.#####`, `IMM-MDL-.YYYY.-.####`, `ALE-.YYYY.-.#######`, `NC-.YY.-.MM.-.#####`, `CAL-.YYYY.-.#####`, `CAL-SCH-.YYYY.-.#####`, `FCR-.YYYY.-.#####`, `PM-WO-.YYYY.-.#####`, `WO-CM-.YYYY.-.#####`.

**Records LIVE tại thời điểm rename:** `Asset Commissioning IMM04-26-05-00001`, `IMM Needs Request IMM01-NR-26-05-00001` — giữ nguyên `name`, không migrate. Counter của series mới bắt đầu từ 1.

**Master DocType (config, ít bản ghi):** giữ `field:<code>` autoname (vd `IMM Training Program.program_code`, `IMM Critical Spare Watchlist.watchlist_name`, `IMM Compliance Rule.rule_code`) — không cần series.

---

## 2. Patches version prefix — dùng `v3_2` (không phải `v15_07`)

Codebase hiện tại (`assetcore/patches.txt`) dùng cây phiên bản `v3_x`:

| Prefix | Phạm vi |
|---|---|
| `v3_0.00x` | Wave 0/1 foundation |
| `v3_1.00x` | Wave 2 batch 1 — IMM-01/02/03 |
| **`v3_2.00x`** | **Wave 2 batch 2 — IMM-06 / IMM-15 / IMM-16 (lần này)** |

`WAVE2_ALIGNMENT.md` v1.0.0 §11 viết `v15_05/06/07` — đó là số phiên bản hình thức theo Frappe v15, **không khớp với chuẩn `v3_x` đang dùng trong `patches.txt`**. Khi triển khai, đăng ký theo `v3_2`.

| Patch | Đăng ký trong `patches.txt` |
|---|---|
| `assetcore.patches.v3_2.001_install_imm06` | Bootstrap IMM Training Program/Session/Participant/Competency/Gap Report + 2 workflow JSON |
| `assetcore.patches.v3_2.002_install_imm15_custom_fields` | 7 CF + child `IMM Spare Alternative` lên `AC Spare Part`; Property Setter `AC Stock Movement.reference_type` thêm 2 option |
| `assetcore.patches.v3_2.003_install_imm15` | DocType IMM Spare Allocation (+ Item) / Cycle Count (+ Item) / Critical Spare Watchlist / Spare Part Forecast (+ Item) + 2 workflow JSON |
| `assetcore.patches.v3_2.004_install_imm16_capa_extension` | 11 CF lên `IMM CAPA Record` (gồm `imm_action_plan` table) + 2 CF lên `Audit Finding`; mở rộng `source_type` Select; **không** redesign |
| `assetcore.patches.v3_2.005_install_imm16` | DocType IMM Compliance Rule / Finding / Internal Audit / CAPA Action Step / Compliance Scorecard / Management Review + child phụ trợ + 4 workflow JSON (CAPA-extended là EXTENSION qua workflow_state, không break dữ liệu) |
| `assetcore.patches.v3_2.006_seed_compliance_rules` | Seed ≥40 Compliance Rule baseline |
| `assetcore.patches.v3_2.007_migrate_capa_workflow_state` | Map record `IMM CAPA Record` cũ: `status=In Progress` → `workflow_state=Investigating` (mặc định); refine theo presence của `imm_rca_ref` / `imm_action_plan` |

---

## 3. Frappe Role names — IMM-06 phải dùng nhãn Role chuẩn

13 Role Wave 1 + 6 Role Wave 2 batch 1 đã định nghĩa (xem `WAVE2_ALIGNMENT.md` §6):

`IMM System Admin`, `IMM Operations Manager`, `IMM QA Officer`, `IMM Auditor`, `IMM Department Head`, `IMM Deputy Department Head`, `IMM Workshop Lead`, `IMM Biomed Technician`, `IMM Technician`, `IMM Storekeeper`, `IMM Document Officer`, `IMM Clinical User`, `Vendor Engineer`, `IMM Planning Officer`, `IMM Finance Officer`, `IMM HTM Engineer`, `IMM Procurement Officer`, `IMM Risk Officer`, `IMM Board Approver`.

Docs IMM-06 viết "Tổ HC-QLCL", "Workshop Head", "Biomed Engineer", "Clinical Head", "Department Manager", "VP Block2", "CMMS Admin" — đó là **nhãn tổ chức**, không phải Frappe Role. Map cho Permission JSON:

| Docs ghi | Frappe Role |
|---|---|
| Tổ HC-QLCL / Training Officer | **`IMM Training Officer`** (mới — Wave 2 batch 2) |
| Workshop Head | `IMM Workshop Lead` |
| Biomed Engineer | `IMM Biomed Technician` |
| Clinical Head | `IMM Clinical User` (read-own-dept) hoặc `IMM Department Head` cho phê duyệt |
| Department Manager | `IMM Department Head` |
| HTM Technician | `IMM Technician` |
| Trainee / Operator | `IMM Clinical User` (self-service) |
| CMMS Admin | `IMM System Admin` |
| VP Block1 / VP Block2 | `IMM Board Approver` |

**Role mới cần thêm cho Block 2 & 3** (qua patch `v3_2.008_add_block23_roles` — tách ra để rollback an toàn):

| Role mới | Module | Vai trò |
|---|---|---|
| `IMM Training Officer` | IMM-06 owner — quản lý curriculum, schedule, sign-off, revoke |
| `IMM Compliance Officer` | IMM-16 — quản lý Compliance Rule / Finding / Internal Audit / Scorecard / MR |
| `IMM Internal Auditor` | IMM-16 — sub-role cho audit cycle |

IMM-15 đã dùng đúng tên Role chuẩn (`IMM Storekeeper`, `IMM Workshop Lead`, …) — không cần map.
IMM-16 đã ổn — chỉ cần thêm `IMM Compliance Officer` + `IMM Internal Auditor`.

---

## 4. Asset Lifecycle Event — 15 enum cụ thể, KHÔNG có "Clinical_Release"

`Asset Lifecycle Event.event_type` đang LIVE với 15 option:
`commissioned, activated, pm_started, pm_completed, repair_opened, repair_completed, calibration_started, calibration_passed, calibration_failed, incident_reported, out_of_service, restored, decommissioned, transferred, registered`.

Docs IMM-06 §2/§8 nói "IMM-04 Clinical_Release gate" — **không có event này**. Đọc thành:

- **Gate IMM-06 → IMM-04** thực hiện ở bước transition `commissioned` → `activated` của `AC Asset` (qua `services/imm04.py.activate_asset` hoặc tương đương). Service IMM-04 trước khi cho phép `activated` gọi `services.imm06.get_asset_operator_coverage(asset)` → nếu thiếu N operator competent thì throw `BUSINESS_RULE` với message "Yêu cầu ≥ N operator có Active competency cho device_model trước khi activate".
- **Cross-module gate IMM-06 → IMM-08 / IMM-09 / IMM-12 / IMM-11**: hook tại service WO trước assign technician, gọi `services.imm06.check_user_authorization(user, asset.device_model)` → trả `FORBIDDEN` nếu không pass.

Không cần thêm event_type mới cho `Asset Lifecycle Event`. Mọi thay đổi competency ghi `IMM Audit Trail` (cross-cutting) — không tạo "Training Lifecycle Event".

---

## 5. IMM-15 — Property Setter mở rộng `AC Stock Movement.reference_type`

`AC Stock Movement.reference_type` hiện LIVE chỉ có 4 option: `Asset Repair`, `PM Work Order`, `AC Purchase`, `Manual`. IMM-15 cần link vào `IMM Spare Allocation` và `IMM Stock Cycle Count` qua field `reference_type` + `reference_name`.

**Cách làm:** Property Setter trong patch `v3_2.002_install_imm15_custom_fields` mở rộng options:

```
Asset Repair
PM Work Order
AC Purchase
Manual
IMM Spare Allocation
IMM Stock Cycle Count
```

KHÔNG sửa `ac_stock_movement.json` core. RULE-F03/F04 vẫn áp dụng: IMM-15 transaction submit → sinh 1 `AC Stock Movement` submitted (audit trail của AC layer); IMM-15 chỉ giữ `stock_movement_ref` Link.

`Spare Parts Used` (child của Asset Repair / IMM-09 WO) — giữ nguyên backward compat. Khi `IMM Spare Allocation` Issued sinh `AC Stock Movement`, `Spare Parts Used.stock_entry_ref` cập nhật sang `AC Stock Movement.name` (string, không phải Link cứng — phù hợp schema hiện tại).

---

## 6. IMM-16 — Custom field `imm_action_plan` table cần child DocType riêng

`IMM CAPA Record` đã LIVE; IMM-16 thêm 11 CF (xem IMM-16 Module Overview §2.2). Trong số đó, `imm_action_plan` là Table → cần tạo child DocType `IMM CAPA Action Step` **trước** khi đăng ký CF table. Thứ tự patch:

1. `v3_2.005_install_imm16` — tạo `IMM CAPA Action Step` (child, fields: `step_no`, `action_description`, `owner`, `planned_date`, `completed_date`, `evidence`, `status`).
2. `v3_2.004_install_imm16_capa_extension` — depends on step 1; thêm 11 CF lên `IMM CAPA Record` + 2 CF lên `Audit Finding` + mở rộng `source_type` Select (Property Setter): thêm `Audit Finding`, `Compliance Finding`, `Management Review`.

Sửa thứ tự trong `patches.txt`: `005` chạy trước `004` (hoặc đổi tên để giữ thứ tự alphabet đúng):

| Đề xuất rename | Lý do |
|---|---|
| `v3_2.004_install_imm16` | Tạo DocType (gồm `IMM CAPA Action Step`) |
| `v3_2.005_install_imm16_capa_extension` | Sau khi child có sẵn, thêm CF table |

Dependency chain trong patch handler phải explicit (`frappe.reload_doc` cho child trước khi tạo CF).

CAPA workflow extension dùng `workflow_state` field (đã có sẵn trong `imm_capa_record.json`) — KHÔNG đổi field `status` cũ; mapping cũ→mới như IMM-16 Module Overview §5.1.

---

## 7. Reuse vs new — bản chốt 3 module

### IMM-06 (Block 2 — Deployment & Implementation)

| Reuse (LIVE) | New (PLANNED Wave 2 batch 2) |
|---|---|
| `IMM Audit Trail`, `AC Asset`, `AC Department`, `IMM Device Model`, `Asset Document` (cho certificate file dạng IMM-05), Frappe `User` | DocType: `IMM Training Program`, `IMM Training Session`, `IMM Training Participant` (child), `IMM User Competency`, `IMM Competency Gap Report` |
| `services/imm00.py.log_audit_event` | Service: `services/imm06.py` (12+ functions: schedule/complete session, auto-create competency, gap calc, recert flow, `check_user_authorization`, `get_asset_operator_coverage`) |
| Hook trong `services/imm04.py` (commissioning → activated) | API: `assetcore/api/imm06.py` (~19 endpoints) |
| Hook trong `services/imm08.py`, `imm09.py`, `imm11.py`, `imm12.py` | Workflow: `imm_06_session_workflow.json`, `imm_06_competency_workflow.json` |
| | Scheduler: 4 entry trong `tasks.py` (daily 02:00/02:30/03:00 + weekly Mon 02:00) |
| | Role mới: `IMM Training Officer` |

### IMM-15 (Block 3 — Operations & Maintenance)

| Reuse (LIVE) | New (PLANNED) |
|---|---|
| `AC Spare Part` (master), `AC Spare Part Stock` (bin), `AC Stock Movement` (+ Item), `AC Warehouse`, `AC UOM` (+ Conversion), `IMM Device Spare Part`, `Spare Parts Used` | CF trên `AC Spare Part`: `imm_part_class`, `imm_abc_class`, `imm_xyz_class`, `imm_lead_time_days`, `imm_safety_stock_days`, `imm_traceability_required`, `imm_storage_condition`, `imm_alternative_parts` (table → `IMM Spare Alternative`) |
| `services/inventory.py` (10 fn: get_stock_row, get_available_qty, _upsert_stock, validate_stock_movement, apply_stock_movement, reverse_stock_movement, check_low_stock, get_stock_overview, search_parts) | DocType: `IMM Spare Allocation` (+ Item), `IMM Stock Cycle Count` (+ Item), `IMM Critical Spare Watchlist`, `IMM Spare Part Forecast` (+ Item), `IMM Spare Alternative` (child), `IMM Spare Batch` (gated) |
| `api/inventory.py` (~36 endpoints) | Service: `services/imm15.py` (allocation, cycle count, forecast, watchlist, audit) |
| Frontend `views/inventory/` (11 màn) | API: `api/imm15.py` (~16 endpoint mới) |
| `IMM Audit Trail` | Workflow: `imm_15_allocation_workflow.json`, `imm_15_cycle_count_workflow.json` |
| | Scheduler: 5 entry (1 wrap LIVE `inventory.check_low_stock` + 4 mới); ABC reclass quý → `cron` `0 3 1 1,4,7,10 *` |
| | Property Setter: `AC Stock Movement.reference_type` thêm 2 option |

`IMM Spare Part Forecast` (part-level, IMM-15) ≠ `IMM Demand Forecast` (category-level, IMM-01) — giữ tách bạch, naming khác.

### IMM-16 (Block 3 — Operations & Maintenance, governance layer)

| Reuse (LIVE) | New (PLANNED) |
|---|---|
| `IMM CAPA Record` (`CAPA-.YYYY.-.#####`), `Audit Finding` (child), `IMM Audit Trail`, `IMM RCA Record` + `IMM RCA Five Why Step`, `IMM Supplier Audit` (riêng — vendor-side, IMM-03), `Asset QA Non-Conformance` | DocType: `IMM Compliance Rule`, `IMM Compliance Finding`, `IMM Internal Audit`, `IMM CAPA Action Step` (child của `imm_action_plan`), `IMM Compliance Scorecard`, `IMM Management Review`, child phụ trợ (`IMM Audit Checklist Item`, `IMM Scorecard Module Row`, `IMM Scorecard Department Row`, `IMM MR Attendee`, `IMM MR Output Action`) |
| `services/imm00.py.create_capa / close_capa / check_capa_overdue / log_audit_event / verify_audit_chain` | CF trên `IMM CAPA Record` (11 field) + CF trên `Audit Finding` (2 field) + mở rộng `source_type` Select |
| `services/imm12.py._DT_CAPA = "IMM CAPA Record"` (đã wire) | Service: `services/imm16.py` (rule evaluator, scorecard aggregator, escalation, gate `check_asset_compliance_status`) |
| Hook gate IMM-08 / IMM-09 / IMM-13 / IMM-14 (đặt trong service hiện hữu) | API: `api/imm16.py` (~30 endpoint) |
| | Workflow: 3 mới (Finding, Internal Audit, MR) + 1 EXTEND CAPA qua `workflow_state` field (KHÔNG đổi field `status` cũ) |
| | Scheduler: 5 entry (`run_compliance_evaluation`, `update_compliance_scorecard`, `check_capa_due`, `check_audit_milestones`, `check_management_review_due`); MR check chạy weekly Mon 08:00 |
| | Role mới: `IMM Compliance Officer`, `IMM Internal Auditor` |
| | Migration: map `status=In Progress` → `workflow_state=Investigating` (script `v3_2.007_migrate_capa_workflow_state`) |

---

## 8. Hooks scheduler — append 14 entry mới (KHÔNG ghi đè)

`hooks.py` Wave 1 + Wave 2 batch 1 đã có ~17 entry. Wave 2 batch 2 thêm vào:

```python
# scheduler_events =
"daily": [
    # ... entries hiện hữu giữ nguyên ...

    # IMM-06
    "assetcore.services.imm06.check_competency_expiry",        # 02:00
    "assetcore.services.imm06.auto_expire_competency",         # 02:30
    "assetcore.services.imm06.check_recertification_due",      # 03:00

    # IMM-15
    "assetcore.services.imm15.check_low_stock_alerts",         # wrap inventory.check_low_stock
    "assetcore.services.imm15.check_critical_spare_breach",
    "assetcore.services.imm15.check_expiring_batches",         # gated
    "assetcore.services.imm15.compute_inventory_kpis",

    # IMM-16
    "assetcore.services.imm16.run_compliance_evaluation",
    "assetcore.services.imm16.check_capa_due",                 # extends imm00.check_capa_overdue
    "assetcore.services.imm16.check_audit_milestones",
],
"weekly": [
    "assetcore.services.imm06.generate_competency_gap_report", # Mon 02:00
    "assetcore.services.imm16.check_management_review_due",    # Mon 08:00
],
"monthly": [
    "assetcore.services.imm15.generate_spare_demand_forecast", # 1st 02:00
    "assetcore.services.imm16.update_compliance_scorecard",    # 1st 03:00
],
"cron": {
    "0 3 1 1,4,7,10 *": [
        "assetcore.services.imm15.recompute_abc_class",        # quarterly
    ],
},
```

`hourly` realtime evaluation cho IMM-16 rule (evaluation_frequency=hourly) đăng ký riêng trong `hourly` key nếu có.

---

## 9. API envelope, ErrorCode — giống Wave 1

3 module bắt buộc dùng `_ok` / `_err` từ `assetcore/utils/helpers.py` và ErrorCode enum từ `assetcore/services/shared/constants.py`. Code mới không được tạo class ErrorCode riêng.

App-level error code phụ trợ (vd `MR_MISSING_QUARTERLY`, `REQUIRE_OVERRIDE`) **được phép** nhưng phải đi kèm `code` chuẩn trong response (`code=BUSINESS_RULE`, `error="MR_MISSING_QUARTERLY: …"`). Client chỉ branch theo `code` chuẩn; `error` chứa thông tin con người + sub-code.

---

## 10. Definition of Done — bổ sung cho IMM-06 / 15 / 16

Mỗi module ngoài DoD trong Functional Specs còn phải:

- [ ] Naming series đã rename theo §1 (`IMM06-…`, `IMM15-…`, `IMM16-…`, no-dash, 5-digit hash).
- [ ] Patches đăng ký dưới `v3_2.00x` trong `patches.txt`; thứ tự đảm bảo child DocType tạo trước CF table (§6).
- [ ] Reuse `IMM CAPA Record` / `IMM Audit Trail` / `IMM RCA Record` / `AC Spare Part` family / `IMM Device Model` / `AC Asset` / `Asset Document` (không tạo trùng).
- [ ] Property Setter mở rộng `AC Stock Movement.reference_type` (IMM-15) — không sửa core JSON.
- [ ] Role mới (`IMM Training Officer` / `IMM Compliance Officer` / `IMM Internal Auditor`) tạo qua fixture trong patch riêng (`v3_2.008_add_block23_roles`).
- [ ] Permission JSON dùng đúng tên Frappe Role (Wave 1 + 6 role Wave 2 batch 1 + 3 role mới); KHÔNG dùng nhãn tổ chức.
- [ ] Audit ghi qua `IMM Audit Trail` (cross-cutting); KHÔNG tạo lifecycle event DocType riêng cho training/compliance.
- [ ] Asset Lifecycle Event chỉ ghi với 15 enum hiện có; gate IMM-06 nằm ở transition `commissioned → activated` của IMM-04 (§4).
- [ ] CAPA workflow extension qua `workflow_state` (KHÔNG break field `status` cũ); migration patch map record cũ.
- [ ] Hook + scheduler append vào `hooks.py` (§8); `quarterly` dùng `cron` expression.
- [ ] Envelope `_ok` / `_err` + ErrorCode enum chuẩn; app-level code chỉ ở `error` message.
- [ ] Tất cả message lỗi và label tiếng Việt.
- [ ] Frontend route đặt theo `/imm06/*`, `/imm15/*`, `/imm16/*` (giữ nhất quán với Wave 2 batch 1: `/imm01/*`, `/imm02/*`, `/imm03/*`).

---

## 11. Quy trình đọc tài liệu Block 2 & 3

Khi triển khai một trong 3 module:

1. Đọc `WAVE2_ALIGNMENT.md` (Wave 2 batch 1 — chuẩn nền).
2. Đọc file này (`WAVE2_ALIGNMENT_BLOCK23.md`) — ghi đè cụ thể cho 06/15/16.
3. Đọc `IMM-{06|15|16}_Module_Overview.md` (đã ở v0.2 — gần align).
4. Đọc `IMM-{06|15|16}_Functional_Specs.md` → `Technical_Design.md` → `API_Interface.md` → `UI_UX_Guide.md` → `UAT_Script.md`.
   → Áp dụng các thay đổi §1–§10 mỗi khi gặp ký hiệu lệch (đặc biệt naming series và Frappe Role names trong IMM-06).
5. Khi viết code, dùng `services/imm04.py` + `api/imm04.py` + `services/inventory.py` làm template tham chiếu.

---

## 12. Changelog

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| 1.0.0 | 2026-05-05 | Phát hành alignment cho IMM-06 / IMM-15 / IMM-16 — đối chiếu docs v0.2 với Wave 1 + Wave 2 batch 1 LIVE. Sửa naming series, patches version (`v3_2`), Frappe Role names IMM-06, gate IMM-06↔IMM-04, Property Setter IMM-15, thứ tự patch IMM-16 CAPA extension. |

---

*End of Wave 2 Alignment — Block 2 & 3 v1.0.0*
