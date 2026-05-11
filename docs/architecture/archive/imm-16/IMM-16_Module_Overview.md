# IMM-16 — Compliance Monitoring & CAPA

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-16 — Theo dõi Tuân thủ & CAPA |
| Phiên bản | 0.3.0 — re-aligned via WAVE2_ALIGNMENT_BLOCK23 |
| Ngày cập nhật | 2026-05-05 |
| **Source of truth** | **`docs/WAVE2_ALIGNMENT_BLOCK23.md` v1.0.0 — đọc trước**. Ghi đè: naming series là **mã dữ liệu domain** (`FND-…`, `AUD-INT-…`, `SCR-…`, `MR-…` — KHÔNG nhúng số module; reuse `CAPA-…` cho CAPA Record); thứ tự patch (tạo `IMM CAPA Action Step` child trước khi thêm CF table `imm_action_plan`); Role mới (`IMM Compliance Officer`, `IMM Internal Auditor`); patches `v3_2.00x`; migration `workflow_state` cho CAPA cũ. |
| Trạng thái | PARTIAL — CAPA core đã LIVE; compliance/audit/scorecard PLANNED |
| Tác giả | AssetCore Team |

---

## Changelog

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| 0.1.0 | 2026-05-04 | Bản thiết kế ban đầu — đề xuất `IMM CAPA` DocType mới. |
| 0.2.0 | 2026-05-04 | **Alignment with existing CAPA backbone.** Reuse `IMM CAPA Record` (đã LIVE), `Audit Finding` (child, đã LIVE), `IMM RCA Record` (đã LIVE), `IMM Audit Trail` (hash-chain, đã LIVE). Loại bỏ `IMM CAPA` mới; thay bằng custom-field extension. CAPA workflow extend (thêm `Investigating`, `Action Plan`) thay vì redesign. |

---

## 1. Mục đích

IMM-16 là **Compliance & CAPA Backbone** của AssetCore — tổng hợp **tín hiệu tuân thủ nội bộ** từ mọi module IMM khác (IMM-04 doc completeness, IMM-05 doc expiry, IMM-08 PM compliance, IMM-09/12 SLA, IMM-11 calibration validity, IMM-15 stock breach, IMM-06 training compliance), chạy **Internal Audit theo cycle**, quản lý vòng đời **Non-Conformance (NC) và CAPA** trên nền `IMM CAPA Record` đã có, sinh **Compliance Scorecard** và phục vụ **Management Review** theo chu kỳ ISO 13485 §5.6.

| Đặc tính | Nội dung |
|---|---|
| Vai trò trong WHO HTM | Quality Management — Internal governance & continual improvement (HTM 5.4) |
| Wave / Block | Wave 2 — Block 3 (Operations & Maintenance) |
| Compliance | ISO 13485:2016 §8.2.4 (Internal Audit), §8.5 (CAPA), §5.6 (Management Review); WHO HTM 5.4; NĐ 98/2021/NĐ-CP §35-§38 |
| Phạm vi audit | Mọi finding/CAPA/audit/scorecard versioned + audit trail bắt buộc qua `IMM Audit Trail` (hash chain); Scorecard published bất biến |
| Owners | Tổ HC-QLCL & Risk (primary), CMMS/IMMIS, PTP1, PTP2 |

---

## 2. Phạm vi thay đổi vs hệ thống hiện tại

### 2.1 Đã có (REUSE — không thiết kế lại)

| Artefact | Trạng thái | Vai trò trong IMM-16 |
|---|---|---|
| `IMM CAPA Record` (DocType, submittable, naming `CAPA-.YYYY.-.#####`) | LIVE | **CAPA backbone**. Mọi tham chiếu "IMM CAPA" trong tài liệu này map về DocType này. |
| `Audit Finding` (child DocType — severity Minor/Major/Critical, category Quality/Compliance/Delivery/Documentation, capa_action/owner/due/status) | LIVE | Child table dùng chung cho `IMM Supplier Audit` (đã có) **và** `IMM Internal Audit` (mới — Phần §3.3). |
| `IMM Audit Trail` (naming `IMM-AUD-.YYYY.-.#######`, hash chain `hash_sha256` + `prev_hash`) | LIVE | Hệ thống audit trail bất biến cho mọi state-change của Finding/CAPA/Audit/Scorecard/MR. |
| `IMM RCA Record` (submittable) + `IMM RCA Five Why Step` (child) | LIVE | Hạ tầng RCA — IMM-16 KHÔNG re-implement 5-Why; CAPA Record link tới RCA qua custom field `imm_rca_ref`. |
| `IMM Supplier Audit` | LIVE | **Tách biệt** — vendor-side audit thuộc IMM-03 / supplier qualification. Không nhầm với `IMM Internal Audit` của IMM-16. |
| `Asset QA Non-Conformance` | LIVE | Đã có; có thể trở thành `source_type="Non-Conformance"` của IMM CAPA Record. |
| `services/imm00.py` (`create_capa`, `close_capa`, `check_capa_overdue`) | LIVE | Service layer dùng chung — IMM-12 đã wire qua `_DT_CAPA = "IMM CAPA Record"`. IMM-16 reuse + extend. |

### 2.2 Mở rộng (CUSTOM FIELDS — không sửa core JSON)

| Target DocType | Custom field | Type / Options | Mục đích |
|---|---|---|---|
| IMM CAPA Record | `imm_root_cause_method` | Select: `5-Why`/`Fishbone`/`FMEA`/`FTA`/`Other` | Đánh dấu phương pháp RCA (VR-05) |
| IMM CAPA Record | `imm_correction_immediate` | Text | Hành động khắc phục tức thời (correction — phân biệt với `corrective_action` nhắm root cause) |
| IMM CAPA Record | `imm_action_plan` | Table → `IMM CAPA Action Step` (mới) | Kế hoạch hành động chi tiết theo bước |
| IMM CAPA Record | `imm_effectiveness_check_date` | Date | Ngày verify hiệu quả |
| IMM CAPA Record | `imm_effectiveness_evidence` | Attach | Bằng chứng hiệu quả |
| IMM CAPA Record | `imm_change_control_ref` | Data | Tham chiếu change control (BR-16-04) |
| IMM CAPA Record | `imm_risk_level` | Select: `Low`/`Medium`/`High`/`Critical` | Rời `severity` field — risk-based prioritization |
| IMM CAPA Record | `imm_compliance_finding_ref` | Link → `IMM Compliance Finding` | Liên kết từ Finding tới CAPA |
| IMM CAPA Record | `imm_audit_finding_ref` | Data | Tham chiếu Audit Finding row (parent_audit + idx) |
| IMM CAPA Record | `imm_rca_ref` | Link → `IMM RCA Record` | Reuse RCA hạ tầng có sẵn (5-Why, Fishbone) |
| IMM CAPA Record | `imm_reopen_count` | Int default 0 | Số lần re-open do effectiveness fail |
| IMM CAPA Record | `source_type` (extend Select options) | Thêm: `Audit Finding`, `Compliance Finding`, `Management Review` | Source type mở rộng |
| Audit Finding | `imm_finding_link` | Link → `IMM Compliance Finding` | Cross-ref Audit Finding ↔ Compliance Finding |
| Audit Finding | `imm_capa_link` | Link → `IMM CAPA Record` | Thay thế text loose `capa_action` bằng link cứng |

### 2.3 Thêm mới (PLANNED)

| Artefact | Loại | Vai trò |
|---|---|---|
| `IMM Compliance Rule` | DocType (master, versioned) | Khai báo rule declarative |
| `IMM Compliance Finding` | DocType | Bản ghi auto-detected non-compliance |
| `IMM Internal Audit` | DocType | Audit nội bộ (reuse `Audit Finding` child) |
| `IMM CAPA Action Step` | Child DocType | Step trong kế hoạch hành động — table thuộc Custom Field `imm_action_plan` của CAPA Record |
| `IMM Compliance Scorecard` | DocType (immutable sau publish) | Snapshot tháng |
| `IMM Management Review` | DocType | Hồ sơ họp Management Review |
| `IMM Scorecard Module Row`, `IMM Scorecard Department Row`, `IMM MR Attendee`, `IMM MR Output Action` | Child DocTypes phụ trợ | — |
| `assetcore/api/imm16.py` | API module | ~30 whitelisted endpoints |
| `assetcore/services/imm16.py` | Service | Rule engine, scorecard aggregator, escalation, gate |
| 5 scheduler entries trong `tasks.py` | Scheduler | Eval rule, scorecard, CAPA due, audit milestones, MR due |
| 4 workflow JSON | Workflow | Finding, Audit, **CAPA-extended** (xem §5.1), MR |

### 2.4 Phân biệt module (CRITICAL)

| Module | Phạm vi | DocType chính |
|---|---|---|
| **IMM-16** (module này) | Internal compliance, audit, CAPA, management review | IMM CAPA Record (reuse), IMM Compliance Rule/Finding/Scorecard/MR (mới), IMM Internal Audit (mới — reuse `Audit Finding` child) |
| IMM-10 | EXTERNAL post-market — recall / FSCA / vigilance | (riêng) — recall có thể tạo CAPA nội bộ → cross-link vào IMM-16 |
| IMM-03 | Supplier qualification & vendor-side audit | `IMM Supplier Audit` (LIVE) — **không** nhầm với `IMM Internal Audit` |
| IMM-12 | Corrective workflow, RCA cho incident | Đã wire `IMM CAPA Record` qua `services/imm12.py` (`_DT_CAPA = "IMM CAPA Record"`) — IMM-16 mở rộng cùng record này |

---

## 3. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│                  Frappe Framework v15                            │
│   Workflow Engine · Version DocType · Scheduler · Notification   │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                      AssetCore App                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │       IMM-16 Compliance Monitoring & CAPA                │   │
│  │                                                          │   │
│  │  REUSE (LIVE):                                           │   │
│  │    • IMM CAPA Record       (CAPA-.YYYY.-.#####)          │   │
│  │    • Audit Finding         (child — Supplier+Internal)   │   │
│  │    • IMM Audit Trail       (IMM-AUD-.YYYY.-.#######)     │   │
│  │    • IMM RCA Record + 5-Why Step                         │   │
│  │    • services/imm00.py: create_capa / close_capa         │   │
│  │                                                          │   │
│  │  NEW (PLANNED):                                          │   │
│  │    • IMM Compliance Rule       (master, versioned)       │   │
│  │    • IMM Compliance Finding    (FND-...)          │   │
│  │    • IMM Internal Audit        (AUD-INT-...)          │   │
│  │    • IMM CAPA Action Step      (child of CAPA Record)    │   │
│  │    • IMM Compliance Scorecard  (SCR-...)          │   │
│  │    • IMM Management Review     (MR-...)           │   │
│  │                                                          │   │
│  │  EXTEND via Custom Fields:                               │   │
│  │    • IMM CAPA Record  (+11 fields, +3 source_type opts)  │   │
│  │    • Audit Finding    (+2 fields)                        │   │
│  │                                                          │   │
│  │  API:        assetcore/api/imm16.py  (~30 endpoints)     │   │
│  │  Service:    assetcore/services/imm16.py                 │   │
│  │  Workflow:   workflow/imm_16_*.json (4 workflows;        │   │
│  │              CAPA workflow EXTENDS existing 4-state)     │   │
│  │  Scheduler:  tasks.py  (5 entries)                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│   Tích hợp IN (consume):                                         │
│     IMM-04 ──▶ IMM-16  (doc completeness, GW gate failures)      │
│     IMM-05 ──▶ IMM-16  (doc expiry, exempt records)              │
│     IMM-06 ──▶ IMM-16  (training/competency expiry)              │
│     IMM-08 ──▶ IMM-16  (PM compliance % per dept)                │
│     IMM-09 ──▶ IMM-16  (SLA breach, repeat failures)             │
│     IMM-11 ──▶ IMM-16  (calibration overdue / OOT)               │
│     IMM-12 ──▶ IMM-16  (đã share IMM CAPA Record)                │
│     IMM-15 ──▶ IMM-16  (critical spare breach)                   │
│     IMM-10 ──▶ IMM-16  (external recall → internal NC)           │
│                                                                  │
│   Tích hợp OUT (provide):                                        │
│     IMM-16 ──▶ IMM-08/09  (gate WO Submit nếu CAPA Crit Open —   │
│                            hook trong services/imm08.py + imm09) │
│     IMM-16 ──▶ IMM-13/14  (block decommission nếu audit/CAPA mở) │
│     IMM-16 ──▶ IMM-17     (compliance trend signal)              │
│     IMM-16 ──▶ QMS Layer  (Management Review report)             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. DocTypes

### 4.1 Reuse — IMM CAPA Record (CAPA backbone — LIVE)

| Thuộc tính | Giá trị |
|---|---|
| Naming | `CAPA-.YYYY.-.#####` (đã có) |
| Submittable | 1 (đã có) |
| Track changes | 1 (đã có) |
| Source type | Existing: `Incident Report / Non-Conformance / Complaint / PM Work Order / IMM Asset Calibration / Asset Repair`. **Extend (Custom Field option):** `Audit Finding`, `Compliance Finding`, `Management Review`. |
| Status | `Open / In Progress / Pending Verification / Closed / Overdue` (đã có) — IMM-16 thêm 2 sub-state qua workflow_state Link (xem §5.1). |
| Severity | `Minor / Major / Critical` (đã có). IMM-16 thêm Custom Field `imm_risk_level` (`Low/Medium/High/Critical`) để phục vụ risk-based prioritization. |
| Custom fields IMM-16 | 11 field (xem §2.2) |

### 4.2 Reuse — Audit Finding (child — LIVE)

Hiện embedded trong `IMM Supplier Audit`. IMM-16 reuse cho `IMM Internal Audit` (cùng schema). Custom Field thêm: `imm_finding_link`, `imm_capa_link`.

### 4.3 Mới — Primary DocTypes

| DocType | Naming | Mô tả |
|---|---|---|
| IMM Compliance Rule | `field:rule_code` | Master config rule khai báo (declarative) — versioned qua change control |
| IMM Compliance Finding | `format:FND-.YYYY.-.#####` | Bản ghi non-compliance phát hiện auto/manual |
| IMM Internal Audit | `format:AUD-INT-.YYYY.-.#####` | Cycle audit nội bộ — reuse `Audit Finding` child |
| IMM Compliance Scorecard | `format:SCR-.YYYY.-.MM.-.#####` | Snapshot tháng — immutable sau publish |
| IMM Management Review | `format:MR-.YYYY.-.#####` | Hồ sơ họp Management Review (quý) |

### 4.4 Mới — Child DocTypes

| DocType | Parent (qua Custom Field table) | Mô tả |
|---|---|---|
| IMM CAPA Action Step | `IMM CAPA Record.imm_action_plan` (Custom Field) | step_no, action_description, owner, planned_date, completed_date, evidence, status |
| IMM Audit Checklist Item | `IMM Internal Audit.checklist_items` | Đã giữ thiết kế ban đầu (clause_ref, finding_status, linked_finding) |
| IMM Scorecard Module Row | Scorecard | — |
| IMM Scorecard Department Row | Scorecard | — |
| IMM MR Attendee | Management Review | — |
| IMM MR Output Action | Management Review | — |

> RCA: KHÔNG re-model 5-Why trong CAPA. Liên kết qua `imm_rca_ref` → `IMM RCA Record` đã LIVE.

---

## 5. Workflow & Schedulers

### 5.1 Workflow CAPA — EXTEND existing (KHÔNG break dữ liệu)

Hiện tại `IMM CAPA Record.status` = `Open / In Progress / Pending Verification / Closed / Overdue`.

IMM-16 cần workflow chi tiết hơn (Investigating / Action Plan / Verification). Giải pháp: **giữ field `status` cũ** + thêm 2 workflow_state mới qua `workflow_state` Link (đã có trong schema). Migration mapping:

| New workflow_state | Existing `status` mapped | Ghi chú |
|---|---|---|
| Open | Open | Ban đầu khi tạo |
| Investigating | In Progress | Đang phân tích root cause |
| Action Plan | In Progress | Đã có RCA, đang lập kế hoạch |
| Implementation | In Progress | Đang thực hiện action steps |
| Verification | Pending Verification | Đợi effectiveness check |
| Closed | Closed | Đã verify Effective |
| Re-opened | Open | reopen_count ++ (Custom Field `imm_reopen_count`) |

> Migration: Bản ghi cũ `In Progress` map mặc định sang workflow_state `Investigating` (giả định bảo thủ) — script patch sẽ set `workflow_state` dựa theo presence của RCA/action_plan.

### 5.2 Các workflow song song

| Workflow | Loại | States |
|---|---|---|
| `IMM-16 Finding Workflow` | Mới | Open → Under Review → (Confirmed NC \| False Positive \| Waived) → Resolved → Closed |
| `IMM-16 Audit Workflow` | Mới | Planned → In Progress → Reporting → Closed |
| `IMM-16 CAPA Workflow` | **Extend** existing | Open → Investigating → Action Plan → Implementation → Verification → Closed (Re-opened nếu effectiveness fail) |
| `IMM-16 Mgmt Review Workflow` | Mới | Draft → Held → Minutes Approved → Closed |

### 5.3 Scheduler Jobs — `assetcore/tasks.py`

| Job | Lịch | Hành vi | Đối tượng nhận email |
|---|---|---|---|
| `run_compliance_evaluation` | Realtime hook + Hourly + Daily 00:15 | Đọc IMM Compliance Rule active theo `evaluation_frequency`, chạy evaluator, upsert Finding (idempotent theo rule+source_record+date) | Owner role của rule |
| `update_compliance_scorecard` | Monthly 1st 03:00 | Aggregate findings của tháng trước, sinh Scorecard Draft, gửi reviewer sign-off | Tổ HC-QLCL, VP Block2 |
| `check_capa_due` (IMM-16) | Daily 02:00 | CAPA Record quá `due_date` → escalate; Critical >7d quá hạn → VP Block2 + Trưởng phòng. **Lưu ý:** dùng chung `imm00.check_capa_overdue` đã có; IMM-16 thêm escalation matrix. | Action Owner, Workshop Head, VP Block2, Trưởng phòng |
| `check_audit_milestones` | Daily 02:30 | Cảnh báo Lead Auditor 7 ngày trước `planned_start`; alert nếu In Progress quá deadline | Lead Auditor, Tổ HC-QLCL |
| `check_management_review_due` | Weekly Monday 08:00 | Cảnh báo nếu quý chưa có Management Review | VP Block2, Tổ HC-QLCL, Trưởng phòng |

---

## 6. Roles & Permissions

| Role | Compliance Rule | Finding | Audit | CAPA Record | Scorecard | Mgmt Review |
|---|---|---|---|---|---|---|
| Tổ HC-QLCL / IMM QA Officer | R/W/C | R/W/C | R/W/C | R/W/C (đã có) | R/W/C | R/W/C |
| Internal Auditor (sub-role) | R | R/W | R/W | R | R | R |
| Workshop Head | R | R/W | R | R/W | R | R |
| Biomed Engineer | R | R/W | R | R/W (đã có) | R | — |
| HTM Technician | R | R | — | R/W (action step) | — | — |
| VP Block2 | R | R/W (Waive) | R/W (Close approve) | R/W (Close approve) | R/W (Sign) | R/W/C (Chair) |
| VP Block1 | R | R | R | R | R | R |
| Trưởng phòng | R | R | R | R/W (action owner) | R | R |
| CMMS Admin | Full | Full | Full | Full | Full | Full |

> Quyền IMM CAPA Record giữ nguyên 12 role đã định nghĩa trong JSON hiện tại. IMM-16 chỉ bổ sung permission cho DocType mới.

---

## 7. Business Rules

| ID | Business Rule | Enforce |
|---|---|---|
| BR-16-01 | Mọi Finding severity ≥ High phải mở CAPA Record trong 5 ngày làm việc | `check_capa_due` scheduler + Finding controller `validate()` |
| BR-16-02 | CAPA Critical chưa close trong 30 ngày → escalate VP Block2 + Trưởng phòng | `check_capa_due` |
| BR-16-03 | CAPA Record chỉ Close khi `effectiveness_check = Effective`; Not Effective → Re-open + thêm action | CAPA `validate()` (đã có field `effectiveness_check`) + IMM-16 thêm guard |
| BR-16-04 | Audit Major NC bắt buộc CAPA Record + change control link nếu thay đổi master data/process (qua `imm_change_control_ref`) | `close_audit` validator |
| BR-16-05 | IMM Compliance Rule thay đổi (threshold/severity) → đi qua change control (versioned) | Rule controller `before_save()` snapshot `previous_version` |
| BR-16-06 | Waiver chỉ chấp nhận với approval VP Block2 + lý do bằng chứng + expiry date | `waive_finding` API role check |
| BR-16-07 | Scorecard published immutable; muốn sửa → tạo phiên bản restate mới | Controller `validate()` block edit nếu `is_published=1` |
| BR-16-08 | Mỗi quý ≥1 Management Review; missed → block KPI publication | `check_management_review_due` + scorecard publish guard |
| BR-16-09 | Asset có CAPA Record `imm_risk_level=Critical` AND `status` IN (Open, In Progress, Pending Verification) → block IMM-08/09 Submit Work Order. Hook tại `services/imm08.py.validate_*` và `services/imm09.py.validate_*` gọi `check_asset_compliance_status`. | IMM-08/09 service validate |
| BR-16-10 | Mọi thay đổi Finding/CAPA/Audit/Scorecard ghi lên `IMM Audit Trail` (hash chain) + Frappe Version | `track_changes=1` (đã có trên CAPA Record) + `imm00.log_audit_event` |

---

## 8. Dependencies

| Module | Chiều | Liên kết |
|---|---|---|
| IMM-04 Installation | IN | Doc completeness, commissioning gate failures → Compliance Rule evaluator |
| IMM-05 Documents | IN | Doc expiry alerts, exempt records → Finding |
| IMM-06 Training | IN | Training/competency expiry & gaps |
| IMM-08 PM | IN/OUT | PM compliance % feed in; CAPA Critical block WO submit feed out (hook `services/imm08.py`) |
| IMM-09 Repair | IN/OUT | SLA breaches feed in; gate WO submit feed out (hook `services/imm09.py`) |
| IMM-10 Post-market | IN | External recall/FSCA → tự động tạo Internal NC |
| IMM-11 Calibration | IN | Calibration overdue / out-of-tolerance → Finding |
| IMM-12 Corrective | IN/OUT | Đã share `IMM CAPA Record` qua `services/imm12.py._DT_CAPA`. RCA tái dùng `IMM RCA Record`. |
| IMM-13/14 Decommission | OUT | Block decommission nếu asset có audit/CAPA OPEN |
| IMM-15 Spare Parts | IN | Critical spare breach, cycle count variance |
| IMM-17 Predictive | OUT | Compliance trend signal feed cho predictive model |

---

## 9. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| `IMM CAPA Record` (DocType) | **LIVE** | Submittable, naming `CAPA-.YYYY.-.#####`, đã wired bởi IMM-12. |
| `Audit Finding` (child) | **LIVE** | Embedded trong IMM Supplier Audit; reuse cho IMM Internal Audit. |
| `IMM Audit Trail` (hash chain) | **LIVE** | `IMM-AUD-.YYYY.-.#######`. |
| `IMM RCA Record` + 5-Why Step | **LIVE** | Reuse cho RCA của CAPA. |
| `services/imm00.py` create/close CAPA | **LIVE** | — |
| Custom Fields trên IMM CAPA Record (11 fields) | PLANNED | Patch + fixture |
| Custom Fields trên Audit Finding (2 fields) | PLANNED | Patch |
| `IMM Compliance Rule` | PLANNED | Schema design v0.2 |
| `IMM Compliance Finding` | PLANNED | Schema design v0.2 |
| `IMM Internal Audit` | PLANNED | Reuse Audit Finding child |
| `IMM CAPA Action Step` (child) | PLANNED | Mới |
| `IMM Compliance Scorecard` | PLANNED | — |
| `IMM Management Review` | PLANNED | — |
| 4 Workflows (Finding/Audit/CAPA-extended/MR) | PLANNED | CAPA workflow là EXTENSION (xem §5.1) |
| `assetcore/api/imm16.py` (~30 endpoints) | PLANNED | Operate on existing CAPA Record |
| `assetcore/services/imm16.py` | PLANNED | Rule evaluator + scorecard + escalation + gate |
| 5 Scheduler entries | PLANNED | `tasks.py` chưa có entry IMM-16 |
| Frontend UI Vue (`/imm16/*`) | PLANNED | — |
| Email notification template | PLANNED | 6 loại alert |
| Compliance Rule seed (≥40 rule baseline) | PLANNED | Fixture |
| Integration gate IMM-08/09 (BR-16-09) | PLANNED | Hook trong `services/imm08.py` + `services/imm09.py` validate functions |
| Migration patch: workflow_state cho CAPA Record cũ | PLANNED | Map In Progress → Investigating mặc định |

---

## 10. QMS Mapping

| Yêu cầu | Nguồn | Cách đáp ứng |
|---|---|---|
| Internal Audit | ISO 13485 §8.2.4 | IMM Internal Audit DocType + checklist + audit cycle scheduler |
| CAPA | ISO 13485 §8.5 | IMM CAPA Record (LIVE) + extension fields (root_cause_method, action_plan, effectiveness) + RCA link |
| Management Review | ISO 13485 §5.6 | IMM Management Review DocType + quarterly cadence + minute approval |
| Quality Management | WHO HTM 5.4 | Compliance Scorecard + KPI dashboard |
| Post-market obligation | NĐ 98 §35-§38 | Cross-link với IMM-10 (external recall → internal NC) |
| Document Control | ISO 13485 §4.2 | Rule versioned, Scorecard immutable, audit trail qua IMM Audit Trail |
| Risk Management | ISO 14971 (qua QMS) | `imm_risk_level` Custom Field trên CAPA Record + Risk review trong Management Review |

**QMS Documents linked:**

| Loại | Mã | Mô tả |
|---|---|---|
| Procedure (PR) | PR-IMMIS-16-01 | Quy trình Internal Audit |
| Procedure | PR-IMMIS-16-02 | Quy trình CAPA (kết hợp với hệ CAPA Record có sẵn) |
| Procedure | PR-IMMIS-16-03 | Quy trình Management Review |
| Procedure | PR-IMMIS-16-04 | Quy trình Compliance Monitoring |
| Work Instruction | WI-IMMIS-16-01..05 | HDCV cho rule evaluation, audit checklist, root cause (link RCA Record), effectiveness check, scorecard |
| Form (BM) | BM-IMMIS-16-01 | Biểu mẫu CAPA (in từ IMM CAPA Record + extension) |
| Record / Log / Report | HS-LOG/REC/REP-IMMIS-16 | Hồ sơ + log audit (IMM Audit Trail) + báo cáo |
| KPI Dashboard | KPI-DASH-IMMIS-16 | Dashboard KPI compliance |
