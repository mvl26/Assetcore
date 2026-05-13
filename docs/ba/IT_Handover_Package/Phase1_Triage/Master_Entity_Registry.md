> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# Master Entity Registry — AssetCore Wave 1
**Single Source of Truth for All Entities**

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Owner** | SA Lead + BA Lead + Tech Lead |
| **Last Updated** | 2026-05-06 |
| **Wave** | Wave 1 (IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12) |
| **Status** | Final Consolidated Spec |

---

## SECTION 1: DOCTYPES MANIFEST — Wave 1

**Total: 38 DocTypes** | **Prefix: `AC ` (mandatory)** | **App: `assetcore`** | **Version: Frappe v15**

### 1.1 Foundation / Infrastructure (2 DocTypes)

| # | DocType | Module | Type | Submittable | Naming Series | Notes |
|---|---------|--------|------|-------------|---------------|-------|
| 1 | AC Lifecycle Event | Asset Core | Document | No (immutable) | `LCE-.YYYY.-.########` | Append-only audit log; cannot be updated/deleted post-insert |
| 2 | AC Event Type | Asset Core | Document | No | — | Master list of event codes (LE-03, LE-04, etc.) |

---

### 1.2 Master Data (5 DocTypes)

| # | DocType | Module | Type | Submittable | Naming Series | Notes |
|---|---------|--------|------|-------------|---------------|-------|
| 3 | AC Manufacturer | Asset Registry | Document | No | `MFR-.####` | Equipment manufacturer registry |
| 4 | AC Location | Asset Registry | Document | No | `LOC-.####` | Tree structure: Facility > Building > Department > Room |
| 5 | AC Device Model | Asset Registry | Document | No | `model_code` (unique) | Specification template; linked to ERPNext Item |
| 6 | AC Service Provider | Asset Registry | Document | No | `SP-.####` | Maintenance/calibration vendors (ERPNext Supplier mapping) |
| 7 | AC Contract | Asset Registry | Document | Yes | `CNT-.YYYY.-.####` | Service contracts with vendors |

---

### 1.3 Asset Registry (7 DocTypes)

| # | DocType | Module | Type | Submittable | Naming Series | Notes |
|---|---------|--------|------|-------------|---------------|-------|
| 8 | AC Medical Asset | Asset Registry | Document | Yes | `MA-.YYYY.-.####` | Core HTM entity; 1:1 with ERPNext Asset |
| 9 | AC Asset Identifier | Asset Registry | Document | No | `AID-.YYYY.-.######` | QR/RFID/Barcode codes for single asset |
| 10 | AC Custodian Assignment | Asset Registry | Document | Yes | `CUS-.YYYY.-.######` | User-asset assignment with temporal tracking |
| 11 | AC Asset Movement | Asset Registry | Document | Yes | `MOV-.YYYY.-.####` | Inter-department transfer (multi-level approval) |
| 12 | AC Stand-Down Record | Asset Registry | Document | Yes | `SD-.YYYY.-.####` | Temporary asset removal from service |
| 13 | AC Decommission Record | Asset Registry | Document | Yes | `DEC-.YYYY.-.####` | Planned end-of-life (multi-level approval) |
| 14 | AC Disposal Record | Asset Registry | Document | Yes | `DIS-.YYYY.-.####` | Final disposal/destruction record |

---

### 1.4 Document & QMS Engine (2 DocTypes)

| # | DocType | Module | Type | Submittable | Naming Series | Notes |
|---|---------|--------|------|-------------|---------------|-------|
| 15 | AC Document Record | Document QMS | Document | Yes | `DOC-.YYYY.-.######` | License/SOP/Training/Certificate lifecycle |
| 16 | AC QMS Artifact | Document QMS | Document | Yes | `QMS-<TIER>-.YYYY.-.####` | Quality management documents (Tier 1-4) |

---

### 1.5 Work Order Engine — Unified (8 DocTypes)

| # | DocType | Module | Type | Submittable | Naming Series | Notes |
|---|---------|--------|------|-------------|---------------|-------|
| 17 | AC Failure Report | Work Order | Document | Yes | `FR-.YYYY.-.######` | Equipment malfunction notification |
| 18 | AC Work Order | Work Order | Document | Yes | `WO-.YYYY.-.######` | Unified task (PM/CM/Calibration/IQ-OQ-PQ) |
| 19 | AC Work Order Task | Work Order | Child | — | — | Task checklist items within WO |
| 20 | AC Work Order Spare Item | Work Order | Child | — | — | Parts consumed; links Stock Entry |
| 21 | AC PM Plan | Maintenance | Document | Yes | `PMP-.YYYY.-.####` | Preventive maintenance schedule |
| 22 | AC PM Task Detail | Maintenance | Child | — | — | PM task template items |
| 23 | AC Calibration Plan | Calibration | Document | Yes | `CPL-.YYYY.-.####` | Calibration frequency + standard reference |
| 24 | AC Calibration Record | Calibration | Document | Yes | `CAL-.YYYY.-.######` | Actual calibration result with measurements |

---

### 1.6 Commissioning (1 DocType)

| # | DocType | Module | Type | Submittable | Naming Series | Notes |
|---|---------|--------|------|-------------|---------------|-------|
| 25 | AC IQ OQ PQ Record | Commissioning | Document | Yes | `IQPQ-.YYYY.-.####` | Installation/Operational/Performance Qualification |

---

### 1.7 Compliance / CAPA / Audit (8 DocTypes)

| # | DocType | Module | Type | Submittable | Naming Series | Notes |
|---|---------|--------|------|-------------|---------------|-------|
| 26 | AC Nonconformity | Compliance | Document | Yes | `NC-.YYYY.-.####` | Quality issue identification |
| 27 | AC CAPA | Compliance | Document | Yes | `CAPA-.YYYY.-.####` | Corrective/Preventive Action |
| 28 | AC CAPA Action | Compliance | Child | — | — | Individual action items within CAPA |
| 29 | AC Compliance Case | Compliance | Document | Yes | `CMP-.YYYY.-.####` | Regulatory/recall investigation (48h SLA) |
| 30 | AC Risk Entry | Compliance | Document | Yes | `RSK-.YYYY.-.####` | Risk assessment (open/mitigated/closed) |
| 31 | AC Change Control Request | Compliance | Document | Yes | `CCR-.YYYY.-.####` | Equipment/process change management |
| 32 | AC Audit | Compliance | Document | Yes | `AUD-.YYYY.-.####` | Internal audit schedule + findings |
| 33 | AC Management Review | Compliance | Document | Yes | `MRV-.YYYY.-.####` | Periodic QMS review |

---

### 1.8 Metric / Dashboard Engine (4 DocTypes)

| # | DocType | Module | Type | Submittable | Naming Series | Notes |
|---|---------|--------|------|-------------|---------------|-------|
| 34 | AC Metric Definition | Dashboard | Document | No | `MET-W1-####` | KPI/KRI calculation blueprint (source, logic, frequency) |
| 35 | AC Dashboard Snapshot | Dashboard | Document | No | auto | Time-series metric snapshot (scheduled daily) |
| 36 | AC Dashboard Widget | Dashboard | Document | No | — | Dashboard widget configuration |
| 37 | AC Alert Rule | Dashboard | Document | No | — | Threshold-based notification trigger |

---

### 1.9 Application Settings (1 DocType)

| # | DocType | Module | Type | Submittable | Naming Series | Notes |
|---|---------|--------|------|-------------|---------------|-------|
| 38 | AssetCore Settings | Asset Core | Single | — | — | App-level configuration (via frappe.get_single) |

---

## SECTION 2: ROLES REGISTRY — 18 Roles

**Prefix: `AC ` (mandatory)** | **Default module: Asset Core**

| # | Role | Vietnamese Label | Access Scope | Internal/External | Notes |
|---|------|------------------|--------------|-------------------|-------|
| 1 | AC Asset Manager | Trưởng/Phó VTTBYT | Full asset lifecycle | Internal | VTTBYT director; approve asset state changes |
| 2 | AC BME Engineer | Kỹ sư BME | Technical; PM/WO planning | Internal | Plan, assign, validate WOs |
| 3 | AC Technician | KTV thiết bị | Execute WO tasks | Internal | Complete/update WO state in_progress |
| 4 | AC Calibration Lab Engineer | Kỹ sư hiệu chuẩn | Calibration records | Internal | Perform calibration; linked to Lab/Vendor |
| 5 | AC Spare Warehouse Officer | Quản lý kho phụ tùng | Spare part inventory | Internal | Manage WO Spare Items; Stock Entry |
| 6 | AC QMS Officer | QMS Officer | Document/QMS operations | Internal | Approve documents, artifacts, CAPAs |
| 7 | AC QMS Lead | Trưởng QLCL | QMS oversight | Internal | Close CAPA, approve Tier 1/2 artifacts (e-signature) |
| 8 | AC Department Head | Trưởng khoa | Department assets/WOs | Internal | Approve asset movement (department step) |
| 9 | AC Clinical User | Người dùng cuối khoa | Asset usage + failure report | Internal | Report failures; view own-dept assets |
| 10 | AC Procurement Officer | Mua hàng | PO/PR workflow | Internal | Link contracts; visible to PRs |
| 11 | AC Finance Officer | KTTC | Financial fields + Asset cost | Internal | Approve disposal; view acquisition_cost |
| 12 | AC Legal Officer | Pháp chế | Document review + disposal | Internal | Approve document effective; disposal legal step |
| 13 | AC Auditor (Internal) | Kiểm toán nội bộ | Read-only audit trail | Internal | Full read AC Lifecycle Event; no write/delete |
| 14 | AC Vendor Service Engineer | Vendor SE (External) | Assigned WOs only | External | Execute CM WOs (state in_progress→completed); no cost fields |
| 15 | AC Vendor Calibration | Vendor Cal (External) | Calibration Records | External | Perform calibration; scoped to assigned asset |
| 16 | AC Vendor Trainer | Vendor Trainer (External) | Training sessions | External | Manage training attendance |
| 17 | AC Executive Viewer | BGĐ (read-only) | Dashboard/KPI only | Internal | Dashboard access; cannot create/edit |
| 18 | AC System Admin | IT Admin | Full system | Internal | Frappe admin; role setup; no app delete capability |

---

## SECTION 3: WORKFLOW STATES & TRANSITIONS

**Format:** `<state_name>` (snake_case) | `<display_label>` (Vietnamese) | `[is_initial]` | `[is_final]` | `[is_qms_critical]`

### 3.1 AC Medical Asset Workflow

```
draft ──► installed ──► commissioned ──► released_for_use
                                               │
                                               ├──► stand_down ──► released_for_use
                                               │        └──► retired ──► disposed
                                               └──► retired ──► disposed
   (parallel flag) recalled
```

| State | Label (VI) | Initial | Final | QMS Critical | Trigger | Actor | Side Effect |
|-------|-----------|---------|-------|-------------|---------|-------|-------------|
| `draft` | Nháp | ✓ | – | – | Create | Anyone | – |
| `installed` | Lắp đặt | – | – | – | IQ pass | BME + Supervisor | LE-03 installed |
| `commissioned` | Đưa vào hoạt động | – | – | – | OQ+PQ pass | QMS Officer | LE-04 commissioned |
| `released_for_use` | Phát hành sử dụng | – | – | ✓ | Approve DI-1 | Asset Manager + QMS | LE-06 released_for_use |
| `stand_down` | Tạm dừng | – | – | – | Stand-down approval | Asset Manager | LE-14 stand_down |
| `retired` | Loại biên | – | – | – | Decommission approval | Multi-level | LE-15 retired |
| `disposed` | Thanh lý | – | ✓ | ✓ | Disposal approval | Finance + Legal | LE-16 disposed |
| `recalled` | Thu hồi (flag) | – | – | ✓ | Compliance recall | QMS | LE-12 recalled |

---

### 3.2 AC Document Record Workflow

```
draft ──► review ──► approved ──► effective ──► expired
   │         │          │             │
   │         ▼          ▼             ▼
   ▼     rejected   cancelled     obsolete
cancelled
```

| State | Label (VI) | Initial | Final | QMS Critical | Trigger | Side Effect |
|-------|-----------|---------|-------|-------------|---------|-------------|
| `draft` | Nháp | ✓ | – | – | Create | – |
| `review` | Xét duyệt | – | – | – | Submit | – |
| `approved` | Chấp thuận | – | – | ✓ | Approver action (e-sig) | – |
| `effective` | Có hiệu lực | – | – | ✓ | effective_date reached | LE-05 document_effective |
| `expired` | Hết hạn | – | ✓ | – | expiry_date < today (cron) | LE-29 document_expired |
| `obsolete` | Hủy dùng | – | ✓ | – | Superseded by new version | LE-29 document_obsolete |
| `rejected` | Từ chối | – | ✓ | – | Approver action | – |
| `cancelled` | Hủy | – | ✓ | – | Creator action | – |

---

### 3.3 AC QMS Artifact Workflow

```
draft ─► review ─► approved ─► effective ─► under_review ─► revised
                                 │              │             │
                                 ▼              ▼             ▼
                              obsolete       obsolete     effective (v2)
```

| State | Label (VI) | Initial | Final | QMS Critical | Trigger | Side Effect |
|-------|-----------|---------|-------|-------------|---------|-------------|
| `draft` | Nháp | ✓ | – | – | Create | – |
| `review` | Xét duyệt | – | – | – | Submit | – |
| `approved` | Chấp thuận | – | – | ✓ | Approver chain per Tier (e-sig) | – |
| `effective` | Có hiệu lực | – | – | ✓ | effective_date reached | LE-28 document_published |
| `under_review` | Xét duyệt lại | – | – | – | next_review_date (cron) | – |
| `revised` | Sửa đổi | – | – | – | Author revise submission | – |
| `obsolete` | Hủy dùng | – | ✓ | – | Replaced by new version | LE-29 document_obsolete |

---

### 3.4 AC Work Order Workflow

```
draft ─► planned ─► assigned ─► in_progress ─► completed ─► validated ─► closed
                                    │             │              ▲
                                    ▼             ▼              │
                                 paused        cancelled  validation_required?
                                    │
                                    └─► in_progress (resume)
```

| State | Label (VI) | Initial | Final | QMS Critical | Trigger | Side Effect |
|-------|-----------|---------|-------|-------------|---------|-------------|
| `draft` | Nháp | ✓ | – | – | Create | – |
| `planned` | Kế hoạch | – | – | – | Submit | – |
| `assigned` | Giao việc | – | – | – | Assignment (auto/BME) | LE-42 wo_assigned |
| `in_progress` | Đang thực hiện | – | – | – | Start (Assignee) | LE-43 wo_started |
| `paused` | Tạm dừng | – | – | – | Pause (Assignee) | LE-44 wo_paused |
| `completed` | Hoàn thành | – | – | – | All tasks done (Assignee) | LE-46 wo_completed |
| `validated` | Kiểm chứng | – | – | ✓ | Validate (Validator ≠ executor, e-sig) | LE-47 wo_validated |
| `closed` | Kết thúc | – | ✓ | ✓ | Close (Validator or bypass if validator_required=false) | LE-48 wo_closed + type-specific |
| `cancelled` | Hủy | – | ✓ | – | Cancel (BME, only if state ≤ assigned) | LE-50 wo_cancelled |
| `breach_sla` | SLA vượt (flag) | – | – | – | SLA monitor (auto) | LE-49 sla_breached |

---

### 3.5 AC Failure Report Workflow

```
draft ─► submitted ─► linked_to_wo
            │              │
            ▼              ▼
         rejected       merged
```

| State | Label (VI) | Initial | Final | Trigger | Side Effect |
|-------|-----------|---------|-------|---------|-------------|
| `draft` | Nháp | ✓ | – | Create | – |
| `submitted` | Gửi báo cáo | – | – | Reporter submit | – |
| `linked_to_wo` | Liên kết WO | – | – | System auto-create CM WO | – |
| `merged` | Gộp | – | ✓ | Auto-merge duplicate FR | – |
| `rejected` | Từ chối | – | ✓ | BME reject (false positive) | – |

---

### 3.6 AC Calibration Record Workflow

```
draft ─► performed ─► approved ─► closed
   │         │
   ▼         ▼
cancelled  failed ─► capa_opened
```

| State | Label (VI) | Initial | Final | QMS Critical | Trigger | Side Effect |
|-------|-----------|---------|-------|-------------|---------|-------------|
| `draft` | Nháp | ✓ | – | – | Create | – |
| `performed` | Đo lường | – | – | – | Cal Lab Eng submit | – |
| `approved` | Chấp thuận | – | – | ✓ | QMS Officer approve (pass, e-sig) | LE-08 calibrated |
| `closed` | Kết thúc | – | ✓ | – | QMS Officer close | – |
| `failed` | Thất bại | – | – | – | Cal result Fail | LE-?? calibration_failed |
| `capa_opened` | Mở CAPA | – | – | ✓ | QMS trigger CAPA from fail (e-sig) | Stand-down asset + auto CAPA |
| `cancelled` | Hủy | – | ✓ | – | Cancel | – |

---

### 3.7 AC Nonconformity Workflow

```
draft ─► triaged ─► linked_to_capa ─► closed
   │                       │
   ▼                       ▼
cancelled               closed_no_action
```

| State | Label (VI) | Initial | Final | Trigger |
|-------|-----------|---------|-------|---------|
| `draft` | Nháp | ✓ | – | Create |
| `triaged` | Phân loại | – | – | QMS triage |
| `linked_to_capa` | Liên kết CAPA | – | – | Link to CAPA |
| `closed_no_action` | Đóng (không hành động) | – | ✓ | No CAPA needed |
| `closed` | Đóng | – | ✓ | CAPA closed |
| `cancelled` | Hủy | – | ✓ | Cancel |

---

### 3.8 AC CAPA Workflow

```
draft ─► approved ─► in_progress ─► effectiveness_pending ─► closed
                          │                  │                  │
                          ▼                  ▼                  ▼
                      cancelled          reopened          reopened
```

| State | Label (VI) | Initial | Final | QMS Critical | Trigger | Side Effect |
|-------|-----------|---------|-------|-------------|---------|-------------|
| `draft` | Nháp | ✓ | – | – | Create | – |
| `approved` | Chấp thuận | – | – | ✓ | QMS Lead approve (e-sig) | – |
| `in_progress` | Thực hiện | – | – | – | Start execution | LE-?? capa_started |
| `effectiveness_pending` | Chờ kiểm chứng | – | – | – | Actions complete | – |
| `closed` | Kết thúc | – | ✓ | ✓ | QMS Lead close (e-sig) | LE-?? capa_closed |
| `reopened` | Mở lại | – | – | – | Effectiveness failed | – |
| `cancelled` | Hủy | – | ✓ | – | Cancel | – |

---

### 3.9 AC Compliance Case Workflow

```
open ─► investigating ─► action_in_progress ─► resolved ─► closed
   │                              │
   ▼                              ▼
 cancelled                     escalated
```

| State | Label (VI) | Initial | Final | SLA | Trigger |
|-------|-----------|---------|-------|-----|---------|
| `open` | Mở | ✓ | – | 48h (recall) | Create |
| `investigating` | Điều tra | – | – | – | Start investigation |
| `action_in_progress` | Hành động | – | – | – | Execute corrective action |
| `resolved` | Giải quyết | – | – | – | Actions done |
| `closed` | Đóng | – | ✓ | – | QMS Lead close |
| `escalated` | Báo cáo | – | – | – | Escalate (SLA breach) |
| `cancelled` | Hủy | – | ✓ | – | Cancel |

---

### 3.10 AC Asset Movement Workflow

```
draft ─► submitted ─► approved_dept_old ─► approved_dept_new ─► approved_vttbyt ─► executed ─► closed
```

| State | Label (VI) | Initial | Final | Trigger | Approver |
|-------|-----------|---------|-------|---------|----------|
| `draft` | Nháp | ✓ | – | Create | – |
| `submitted` | Gửi | – | – | Creator submit | – |
| `approved_dept_old` | CĐ cũ chấp thuận | – | – | Dept Head (old) approve | Dept Head (old) |
| `approved_dept_new` | CĐ mới chấp thuận | – | – | Dept Head (new) approve | Dept Head (new) |
| `approved_vttbyt` | VTTBYT chấp thuận | – | – | Asset Manager approve | Asset Manager |
| `executed` | Thực hiện | – | – | Logistics execute | Logistics |
| `closed` | Đóng | – | ✓ | System close after executed | – |

---

### 3.11 AC Stand-Down Record Workflow

```
draft ─► submitted ─► approved ─► active ─► resumed
                                     │
                                     └─► retired
```

| State | Label (VI) | Initial | Final | Trigger |
|-------|-----------|---------|-------|---------|
| `draft` | Nháp | ✓ | – | Create |
| `submitted` | Gửi | – | – | Submit |
| `approved` | Chấp thuận | – | – | Asset Manager approve |
| `active` | Hiệu lực | – | – | Activate |
| `resumed` | Phục hồi | – | ✓ | Resume approval |
| `retired` | Thanh lý | – | ✓ | Retire approval |

---

### 3.12 AC Decommission Record Workflow (multi-level approval)

```
draft ─► qms_approved ─► legal_approved ─► finance_approved ─► executed ─► closed
```

| State | Label (VI) | Initial | Final | Trigger | Approver |
|-------|-----------|---------|-------|---------|----------|
| `draft` | Nháp | ✓ | – | Create | – |
| `qms_approved` | QMS chấp thuận | – | – | QMS Officer approve | QMS Officer |
| `legal_approved` | Pháp chế chấp thuận | – | – | Legal Officer approve (e-sig) | Legal Officer |
| `finance_approved` | KTTC chấp thuận | – | – | Finance Officer approve | Finance Officer |
| `executed` | Thực hiện | – | – | Disposal executed | – |
| `closed` | Đóng | – | ✓ | System close | – |

---

### 3.13 AC Disposal Record Workflow (similar to Decommission)

Same as Decommission with additional disposal certification step.

---

### 3.14 AC Risk Entry Workflow

```
open ─► mitigated ─► closed
   │
   ▼
 accepted
```

| State | Label (VI) | Initial | Final | Trigger |
|-------|-----------|---------|-------|---------|
| `open` | Mở | ✓ | – | Create |
| `mitigated` | Giảm nhẹ | – | – | Execute mitigation |
| `closed` | Đóng | – | ✓ | Close verification |
| `accepted` | Chấp nhận rủi ro | – | – | Risk acceptance |

---

### 3.15 AC Change Control Request Workflow

```
draft ─► assessed ─► approved ─► implemented ─► verified ─► closed
                          │
                          ▼
                       rejected
```

| State | Label (VI) | Initial | Final | Trigger |
|-------|-----------|---------|-------|---------|
| `draft` | Nháp | ✓ | – | Create |
| `assessed` | Đánh giá | – | – | Impact assessment |
| `approved` | Chấp thuận | – | – | Approval (multi-level) |
| `implemented` | Triển khai | – | – | Execute change |
| `verified` | Kiểm chứng | – | – | Verify effectiveness |
| `closed` | Đóng | – | ✓ | Close verification |
| `rejected` | Từ chối | – | ✓ | Reject request |

---

### 3.16 AC Audit & AC Management Review Workflow

**AC Audit:**
```
planned ─► in_progress ─► reported ─► closed
```

**AC Management Review:**
```
scheduled ─► completed
```

---

## SECTION 4: LIFECYCLE EVENT CODES

**Total: 19+ Event Types** | **Format: `LE-XX`** | **Parent DocType: AC Lifecycle Event**

| Code | event_type | Display Label (VI) | Triggered By | Trigger Condition | Category |
|------|------------|-------------------|--------------|-------------------|----------|
| LE-03 | installed | Lắp đặt | AC Medical Asset | state: draft → installed | Asset Lifecycle |
| LE-04 | commissioned | Đưa vào hoạt động | AC Medical Asset | state: installed → commissioned | Asset Lifecycle |
| LE-05 | document_effective | Tài liệu có hiệu lực | AC Document Record | state: approved → effective | Document |
| LE-06 | released_for_use | Phát hành sử dụng | AC Medical Asset | state: commissioned → released_for_use | Asset Lifecycle |
| LE-08 | calibrated | Hiệu chuẩn thành công | AC Calibration Record | state: performed → approved (pass) | Maintenance |
| LE-12 | recalled | Thu hồi | AC Medical Asset | recalled flag set | Compliance |
| LE-14 | stand_down | Tạm dừng sử dụng | AC Medical Asset | state: released_for_use → stand_down | Asset Lifecycle |
| LE-15 | retired | Loại biên | AC Medical Asset | state: (any) → retired | Asset Lifecycle |
| LE-16 | disposed | Thanh lý | AC Medical Asset | state: retired → disposed | Asset Lifecycle |
| LE-28 | document_published | Tài liệu công bố | AC QMS Artifact | state: approved → effective | Document |
| LE-29 | document_obsoleted | Tài liệu hủy dùng | AC Document Record / QMS Artifact | state: any → obsolete | Document |
| LE-42 | wo_assigned | Giao công việc | AC Work Order | state: planned → assigned | Work Order |
| LE-43 | wo_started | Bắt đầu công việc | AC Work Order | state: assigned → in_progress | Work Order |
| LE-44 | wo_paused | Tạm dừng công việc | AC Work Order | state: in_progress → paused | Work Order |
| LE-45 | wo_resumed | Tiếp tục công việc | AC Work Order | state: paused → in_progress | Work Order |
| LE-46 | wo_completed | Hoàn thành công việc | AC Work Order | state: in_progress → completed | Work Order |
| LE-47 | wo_validated | Kiểm chứng công việc | AC Work Order | state: completed → validated | Work Order |
| LE-48 | wo_closed | Kết thúc công việc | AC Work Order | state: validated → closed (or bypass validation) | Work Order |
| LE-49 | sla_breached | Vượt SLA | AC Work Order / AC Compliance Case | SLA monitor (auto) | SLA |
| LE-50 | wo_cancelled | Hủy công việc | AC Work Order | state: (any) → cancelled | Work Order |
| LE-XX | erpnext_sync_in | Đồng bộ từ ERPNext | ERPNext Asset / Stock Entry | Sync service trigger | Integration |
| LE-XX | erpnext_sync_out | Đồng bộ tới ERPNext | AC Medical Asset / AC Decommission | Sync service trigger | Integration |

**Note:** Event codes marked `LE-XX` are placeholders for codes not yet assigned; finalized in AC Event Type seed data.

---

## SECTION 5: NAMING SERIES REGISTRY

**Naming Engine:** Frappe native | **Date format:** `YYYY` (4-digit year)

| DocType | Series Pattern | Example | Counter Reset | Notes |
|---------|----------------|---------|---------------|-------|
| AC Medical Asset | `MA-.YYYY.-.####` | `MA-2026-0001` | Yearly | 4-digit annual counter |
| AC Work Order | `WO-.YYYY.-.######` | `WO-2026-000123` | Yearly | 6-digit annual counter |
| AC PM Plan | `PMP-.YYYY.-.####` | `PMP-2026-0001` | Yearly | 4-digit annual counter |
| AC Calibration Record | `CAL-.YYYY.-.######` | `CAL-2026-000045` | Yearly | 6-digit annual counter |
| AC Calibration Plan | `CPL-.YYYY.-.####` | `CPL-2026-0001` | Yearly | 4-digit annual counter |
| AC Document Record | `DOC-.YYYY.-.######` | `DOC-2026-000001` | Yearly | 6-digit annual counter |
| AC QMS Artifact | `QMS-<TIER>-.YYYY-.####` | `QMS-PR-2026-0007` | Yearly | Tier prefix (PR/OP/WI/WD) + 4-digit counter |
| AC CAPA | `CAPA-.YYYY.-.####` | `CAPA-2026-0014` | Yearly | 4-digit annual counter |
| AC Compliance Case | `CMP-.YYYY.-.####` | `CMP-2026-0003` | Yearly | 4-digit annual counter |
| AC Lifecycle Event | `LCE-.YYYY.-.########` | `LCE-2026-00001234` | Yearly | 8-digit annual counter (high volume) |
| AC Failure Report | `FR-.YYYY.-.######` | `FR-2026-000001` | Yearly | 6-digit annual counter |
| AC Nonconformity | `NC-.YYYY.-.####` | `NC-2026-0001` | Yearly | 4-digit annual counter |
| AC Audit | `AUD-.YYYY.-.####` | `AUD-2026-0001` | Yearly | 4-digit annual counter |
| AC Asset Movement | `MOV-.YYYY.-.####` | `MOV-2026-0001` | Yearly | 4-digit annual counter |
| AC Stand-Down Record | `SD-.YYYY.-.####` | `SD-2026-0001` | Yearly | 4-digit annual counter |
| AC Decommission Record | `DEC-.YYYY.-.####` | `DEC-2026-0001` | Yearly | 4-digit annual counter |
| AC Disposal Record | `DIS-.YYYY.-.####` | `DIS-2026-0001` | Yearly | 4-digit annual counter |
| AC Manufacturer | `MFR-.####` | `MFR-0001` | Global | 4-digit global counter |
| AC Location | `LOC-.####` | `LOC-0001` | Global | 4-digit global counter |
| AC Device Model | `model_code` | `DM-CT-V2.5` | Custom | Unique custom code (not auto) |
| AC Service Provider | `SP-.####` | `SP-0001` | Global | 4-digit global counter |
| AC Asset Identifier | `AID-.YYYY.-.######` | `AID-2026-000001` | Yearly | 6-digit annual counter |
| AC Custodian Assignment | `CUS-.YYYY.-.######` | `CUS-2026-000001` | Yearly | 6-digit annual counter |
| AC Contract | `CNT-.YYYY.-.####` | `CNT-2026-0001` | Yearly | 4-digit annual counter |
| AC IQ OQ PQ Record | `IQPQ-.YYYY.-.####` | `IQPQ-2026-0001` | Yearly | 4-digit annual counter |
| AC Change Control Request | `CCR-.YYYY.-.####` | `CCR-2026-0001` | Yearly | 4-digit annual counter |
| AC Risk Entry | `RSK-.YYYY.-.####` | `RSK-2026-0001` | Yearly | 4-digit annual counter |
| AC Management Review | `MRV-.YYYY.-.####` | `MRV-2026-0001` | Yearly | 4-digit annual counter |
| AC Metric Definition | `MET-W1-####` | `MET-W1-0001` | Wave-based | Wave 1 locked; future waves reuse prefix |

---

## SECTION 6: CUSTOM FIELDS ON ERPNEXT CORE

**Principle:** Never alter ERPNext schema directly; use Custom Field DocType with `module = "AssetCore"`.

### 6.1 Item DocType (Medical Device catalog)

| Field Name | Type | Mandatory | Default | Description | Notes |
|------------|------|-----------|---------|-------------|-------|
| `is_medical_device` | Check | Yes (conditional) | 0 | Mark item as medical device | Used in PR hook trigger |
| `risk_class` | Select | No | – | Options: 1, 2a, 2b, 3 (per NĐ 98/2021) | Maps to Device Model risk_class |
| `criticality` | Select | No | – | Options: A, B, C, D | Maps to Device Model criticality |
| `htm_device_model` | Link AC Device Model | No | – | Link to Device Model spec | 1:1 mapping Item ↔ Device Model |

---

### 6.2 Asset DocType (accounting entity)

| Field Name | Type | Mandatory | Default | Description | Notes |
|------------|------|-----------|---------|-------------|-------|
| `assetcore_link` | Link AC Medical Asset | No | – | 1:1 link to AC Medical Asset | Bidirectional sync |
| `htm_state_mirror` | Data (read-only) | No | – | Mirror of AC Medical Asset.state | Read-only display; synced via hook |

---

### 6.3 Supplier DocType (vendor registry)

| Field Name | Type | Mandatory | Default | Description | Notes |
|------------|------|-----------|---------|-------------|-------|
| `is_service_provider` | Check | No | 0 | Mark supplier as service provider | Links to AC Service Provider |

---

### 6.4 Stock Entry DocType (spare part consumption)

| Field Name | Type | Mandatory | Default | Description | Notes |
|------------|------|-----------|---------|-------------|-------|
| `linked_work_order` | Link AC Work Order | No | – | Link to WO consuming parts | Used for cost tracking |

---

### 6.5 Purchase Receipt Item (child of Purchase Receipt)

| Field Name | Type | Mandatory | Default | Description | Notes |
|------------|------|-----------|---------|-------------|-------|
| `auto_create_assetcore_asset` | Check | No | 1 (if Item.is_medical_device) | Auto-create MA draft on PR submit | Conditional default |

---

### 6.6 Department DocType (organizational structure)

| Field Name | Type | Mandatory | Default | Description | Notes |
|------------|------|-----------|---------|-------------|-------|
| `is_clinical` | Check | No | 0 | Mark department as clinical (user-facing) | Scope for AC Clinical User |

---

### 6.7 Employee DocType (user-staff linkage)

| Field Name | Type | Mandatory | Default | Description | Notes |
|------------|------|-----------|---------|-------------|-------|
| `assetcore_role` | Link Role | No | – | Link to AC custom role | Assign AC role to employee |

---

## SECTION 7: KEY BUSINESS RULES (Top 30)

**Format:** `BR-###` | Extracted from business analysis; enforced via validation rules + server scripts.

| # | Code | Rule | Applied To | Enforcement | Severity |
|---|------|------|-----------|-------------|----------|
| 1 | BR-001 | Asset code must be unique post-commission | AC Medical Asset | DB unique constraint | ERROR |
| 2 | BR-002 | Asset code immutable after state ≥ commissioned | AC Medical Asset | on_update validation | ERROR |
| 3 | BR-003 | Device Model must have risk_class = Asset risk_class | AC Medical Asset | Validate on_submit | ERROR |
| 4 | BR-005 | Facility + Department mandatory | AC Medical Asset | Form mandatory fields | ERROR |
| 5 | BR-006 | Custodian user must be active + assigned to department | AC Medical Asset | Link validation | ERROR |
| 6 | BR-007 | Criticality A asset = stand_down approval only Asset Manager | AC Medical Asset | Workflow condition | WARN |
| 7 | BR-008 | Asset cannot change department while in use (released_for_use) | AC Medical Asset | on_update validation | ERROR |
| 8 | BR-011 | Document Record must have effective_date ≤ today or future | AC Document Record | on_submit validation | ERROR |
| 9 | BR-012 | Document approval chain length ≥ 1 per doc type (Legal/QMS/SOP) | AC Document Record | Workflow config | ERROR |
| 10 | BR-013 | Superseded document state = obsolete (not cancelled) | AC Document Record | Workflow rule | INFO |
| 11 | BR-014 | Document expiry_date must be ≥ effective_date | AC Document Record | on_submit validation | ERROR |
| 12 | BR-015 | QMS Artifact Tier 1/2 approval requires e-signature | AC QMS Artifact | Workflow action | ERROR |
| 13 | BR-021 | PM frequency must align with Device Model default | AC PM Plan | on_submit validation | WARN |
| 14 | BR-022 | PM Plan lead_time ≥ 7 days | AC PM Plan | on_submit validation | ERROR |
| 15 | BR-023 | Asset cannot have conflicting PM schedules | AC PM Plan | DB constraint + validation | ERROR |
| 16 | BR-024 | WO state transitions must follow workflow (no bypass via code) | AC Work Order | Frappe Workflow enforcement | ERROR |
| 17 | BR-025 | WO estimated_hours must be ≥ actual_hours on completion | AC Work Order | on_submit validation | WARN |
| 18 | BR-026 | WO validator ≠ creator (segregation of duty) | AC Work Order | on_submit validation | ERROR |
| 19 | BR-031 | Failure Report asset must exist (not deleted) | AC Failure Report | on_submit validation | ERROR |
| 20 | BR-032 | Failure Report severity ≥ High → auto-create CM WO | AC Failure Report | on_submit hook | AUTO |
| 21 | BR-033 | WO spare items must link valid Items (is_spare=1) | AC Work Order | Child table validation | ERROR |
| 22 | BR-034 | WO actual_cost cannot exceed budget × 1.5 | AC Work Order | on_update validation | WARN |
| 23 | BR-035 | CM WO must link Failure Report or reason mandatory | AC Work Order | on_submit validation | ERROR |
| 24 | BR-036 | PM WO linked_pm_plan cannot be null | AC Work Order | on_submit validation | ERROR |
| 25 | BR-041 | Calibration Plan frequency must align Device Model default | AC Calibration Plan | on_submit validation | WARN |
| 26 | BR-042 | Calibration Record must link Calibration Plan | AC Calibration Record | on_submit validation | ERROR |
| 27 | BR-043 | Calibration fail → auto stand_down asset + auto open CAPA | AC Calibration Record | on_submit hook | AUTO |
| 28 | BR-051 | CAPA actions must link NC or Failure Report | AC CAPA | on_submit validation | ERROR |
| 29 | BR-054 | QMS Artifact effective_date future → cannot approve | AC QMS Artifact | on_submit validation | ERROR |
| 30 | BR-083 | Lifecycle Event immutable post-insert (no update/delete) | AC Lifecycle Event | DB trigger + validation | CRITICAL |

**Additional high-impact rules:**
- **BR-071..074:** Asset movement approval chain (dept old → dept new → asset manager)
- **BR-081..082:** WO SLA breach thresholds (Critical 4h, High 8h, Medium 24h)
- **BR-101..103:** Metric calculation consistency + snapshot audit trail

---

## SECTION 8: MAPPING ERPNEXT CORE → ASSETCORE

**Principle:** AssetCore is overlay layer, not replacement. ERPNext remains System of Record for financials.

### 8.1 Entity Mapping Table

| Business Entity | ERPNext DocType | AssetCore DocType | Primary SoT | Sync Direction |
|-----------------|-----------------|-------------------|-------------|-----------------|
| Medical Device Catalog | Item | AC Device Model | AC Device Model | Device Model → Item |
| Device Instance (physical) | Asset | AC Medical Asset | AC Medical Asset | AC Medical Asset ↔ Asset (2-way) |
| Service Vendor | Supplier | AC Service Provider | AC Service Provider | AC Service Provider ← Supplier (1-way) |
| Maintenance (planning) | _(excluded)_ | AC PM Plan | AC PM Plan | N/A (Asset Maintenance not used) |
| Maintenance (execution) | _(excluded)_ | AC Work Order | AC Work Order | N/A |
| Spare Parts (inventory) | Stock Entry | AC Work Order Spare Item | AC Work Order | SE ← WO (on close) |
| Inspection/QC | _(excluded)_ | AC Calibration Record | AC Calibration Record | N/A (Quality Inspection not used) |

### 8.2 Custom Field Hooks on ERPNext Core

**Hooks enforce unidirectional or bidirectional sync:**

| ERPNext Event | AssetCore Hook | Action | Idempotency |
|---------------|----------------|--------|-------------|
| Purchase Receipt.on_submit + Item.is_medical_device | PR hook | Create AC Medical Asset (draft) | Idempotency key = (PR.name, PR.version) |
| AC Medical Asset.on_submit | MA hook | Update ERPNext Asset.assetcore_link | Idempotency key = (MA.name, MA.version) |
| AC Medical Asset.state = released_for_use | MA hook | Set ERPNext Asset.status = "In Use" | Idempotency key = (MA.name, state) |
| Stock Entry.on_submit + linked_work_order | SE hook | Update AC WO Spare Item.cost_actual | Idempotency key = (SE.name, linked_work_order) |
| Department.on_update | Dept hook | Sync to AC Location if location_link changed | Idempotency key = (Dept.name, Dept.version) |

---

## SECTION 9: IMMUTABILITY & AUDIT RULES

### 9.1 Immutable Fields (cannot be edited post-submit)

| DocType | Field(s) | Reason |
|---------|----------|--------|
| AC Medical Asset | `asset_code`, `serial_no`, `device_model` | HTM traceability |
| AC Lifecycle Event | all | Append-only log |
| AC Document Record | `effective_date`, `doc_type` | Compliance evidence |
| AC Calibration Record | `performed_at`, `measurements` | Audit trail |
| AC Work Order | `wo_type`, `asset_link` | Traceability |

### 9.2 Audit Classes (for compliance tracking)

**All DocTypes audited via Frappe Version + AC Lifecycle Event:**

| Audit Class | DocTypes | Retention |
|-------------|----------|-----------|
| **QMS-Critical** | AC Medical Asset, AC QMS Artifact, AC Calibration Record, AC Document Record, AC CAPA | 7 years |
| **Financial** | AC Medical Asset (cost sync), AC Decommission (disposal cost) | 5 years |
| **Operational** | AC Work Order, AC Failure Report, AC PM Plan | 3 years |
| **System** | AC Lifecycle Event, AssetCore Settings | Permanent |

---

## SECTION 10: TESTING & VALIDATION CHECKLIST

**All DocTypes + Workflows must pass before merge:**

- [ ] Naming Series generates correct format (3 test records per DocType)
- [ ] Mandatory fields block submit (form validation)
- [ ] Workflow transitions enforce role-based permissions (test with + without role)
- [ ] Link fields point to correct target DocType (post-insert verification)
- [ ] Lifecycle Events fire correctly (LCE count verification post-state-change)
- [ ] Immutable fields throw ValidationError on edit post-submit
- [ ] Custom fields on ERPNext core use Custom Field DocType (module = "AssetCore")
- [ ] Permission Matrix matches Frappe DocType Permission setup
- [ ] Hooks idempotency keys prevent double-fire (2 submit tests = 1 LE)
- [ ] E-signature blocks QMS-critical action without e-sig

---

## SECTION 11: CROSS-REFERENCES

| Need | Document | Location |
|------|----------|----------|
| Detailed field spec per DocType | DocType Specification Sheet | Phase_03/05 |
| Workflow state machine diagrams | State Machine Specification | Phase_03/06 |
| ERPNext mapping details | Mapping ERPNext ↔ AssetCore | Phase_03/07 |
| Permission rules per role | Permission Matrix | Phase_04/02 |
| SLA rules | SLA Escalation Rule Catalog | Phase_04/03 |
| Audit requirements | Audit Trail Specification | Phase_04/05 |
| Build dependency order | Build Sequence Dependency Graph | Phase_09/02 |
| Acceptance criteria | Acceptance Criteria Catalog | Phase_08/02 |
| Golden Scenarios E2E | Golden Scenarios E2E | Phase_08/04 |

---

**END OF MASTER ENTITY REGISTRY**

*Version 1.0 | 2026-05-06 | Owner: SA Lead + BA Lead + Tech Lead*  
*Single Source of Truth for AssetCore Wave 1 Implementation*  
*All entities, roles, states, rules consolidated from 9 specification packs.*
