# 05 — API Specification — IMM-16 Compliance Monitoring & CAPA

| Mục | Giá trị |
|---|---|
| Module | IMM-16 — Compliance Monitoring & CAPA |
| Phiên bản tài liệu | 1.0 |
| Ngày cập nhật | 2026-05-08 |
| Trạng thái | PLANNED — chuẩn hóa từ IMM-16_API_Interface.md |
| Base path | `assetcore.api.imm16` |
| URL pattern | `/api/method/assetcore.api.imm16.<function>` |

> ⚠️ Pending implementation — Wave 3

---

## §1 Tổng quan

### §1.1 Response Envelope (AssetCore Standard)

**Mọi endpoint dùng envelope AssetCore — KHÔNG dùng Frappe wrapper `{"message": ...}`.**

**Thành công (HTTP 200):**

```json
{
  "success": true,
  "data": { /* payload */ }
}
```

**Lỗi (HTTP 200 với success=false):**

```json
{
  "success": false,
  "error": "Thông báo lỗi tiếng Việt",
  "code": "FIN-XXX"
}
```

Helpers tại `assetcore/utils/helpers.py`:

```python
def _ok(data: dict) -> dict:
    return {"success": True, "data": data}

def _err(msg: str, code: str = "ERROR") -> dict:
    return {"success": False, "error": msg, "code": code}
```

> **LƯU Ý QUAN TRỌNG:** Frappe framework wrap mọi response trong outer `{"message": ...}`.  
> FE parse: `response.json().message` → `{"success": true, "data": {...}}`.  
> HTTP status luôn là 200. Logic lỗi nằm trong `success` field.

### §1.2 Phân trang

```json
{
  "items": [ /* array */ ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 137,
    "total_pages": 7
  }
}
```

`page` 1-based, `page_size` mặc định 20.

### §1.3 Authentication

| Phương thức | Header / Cookie |
|---|---|
| API Token | `Authorization: token <api_key>:<api_secret>` |
| Session (FE SPA) | `Cookie: sid=<session_id>` |

User không có Role hợp lệ → `{"success": false, "error": "...", "code": "FORBIDDEN"}`.

### §1.4 API Catalog

| # | Function | Method | Roles | Mô tả |
|---|---|---|---|---|
| 3.1.1 | `list_rules` | GET | All authenticated | Danh sách Compliance Rule |
| 3.1.2 | `get_rule` | GET | All authenticated | Chi tiết Rule |
| 3.1.3 | `create_rule` | POST | Tổ HC-QLCL, CMMS Admin | Tạo Rule mới |
| 3.1.4 | `update_rule` | POST | Tổ HC-QLCL, CMMS Admin | Cập nhật Rule (versioned) |
| 3.1.5 | `deactivate_rule` | POST | Tổ HC-QLCL, CMMS Admin | Deactivate Rule |
| 3.2.1 | `list_findings` | GET | All authenticated | Danh sách Finding |
| 3.2.2 | `get_finding` | GET | All authenticated | Chi tiết Finding |
| 3.2.3 | `confirm_finding` | POST | Tổ HC-QLCL, Internal Auditor, CMMS Admin | Confirm NC |
| 3.2.4 | `mark_false_positive` | POST | Tổ HC-QLCL, Internal Auditor, CMMS Admin | Mark False Positive |
| 3.2.5 | `waive_finding` | POST | VP Block2, CMMS Admin | Waive Finding (BR-16-06) |
| 3.2.6 | `link_to_capa` | POST | Tổ HC-QLCL, Workshop Head, CMMS Admin | Link Finding → CAPA |
| 3.3.1 | `list_audits` | GET | All authenticated | Danh sách Internal Audit |
| 3.3.2 | `create_audit` | POST | Tổ HC-QLCL, CMMS Admin | Tạo Audit |
| 3.3.3 | `start_audit` | POST | Lead Auditor, Tổ HC-QLCL, CMMS Admin | Bắt đầu Audit |
| 3.3.4 | `complete_audit_checklist` | POST | Lead Auditor, Internal Auditor, CMMS Admin | Hoàn thành checklist |
| 3.3.5 | `close_audit` | POST | Tổ HC-QLCL, VP Block2, CMMS Admin | Đóng Audit (VR-08) |
| 3.4.1 | `create_capa_from_finding` | POST | Tổ HC-QLCL, Workshop Head, CMMS Admin | Tạo CAPA từ Finding |
| 3.4.2 | `advance_capa_state` | POST | Tổ HC-QLCL, Workshop Head, CMMS Admin | Advance CAPA state |
| 3.4.3 | `perform_effectiveness_check` | POST | Tổ HC-QLCL, CMMS Admin | Effectiveness check |
| 3.4.4 | `reopen_capa` | POST | Tổ HC-QLCL, CMMS Admin | Force reopen CAPA |
| 3.5.1 | `list_scorecards` | GET | All authenticated | Danh sách Scorecard |
| 3.5.2 | `get_current_scorecard` | GET | All authenticated | Scorecard tháng hiện tại |
| 3.5.3 | `get_scorecard_by_period` | GET | All authenticated | Scorecard theo period |
| 3.5.4 | `publish_scorecard` | POST | Tổ HC-QLCL, VP Block2, CMMS Admin | Publish Scorecard |
| 3.6.1 | `list_management_reviews` | GET | All authenticated | Danh sách MR |
| 3.6.2 | `create_management_review` | POST | Tổ HC-QLCL, VP Block2, CMMS Admin | Tạo Management Review |
| 3.6.3 | `finalize_management_review` | POST | VP Block2, CMMS Admin | Finalize MR |
| 3.7.1 | `get_dashboard_stats` | GET | All authenticated | KPI dashboard |
| 3.7.2 | `get_compliance_heatmap` | GET | All authenticated | Heatmap module×dept |
| 3.7.3 | `get_capa_aging` | GET | All authenticated | CAPA aging buckets |
| 3.7.4 | `get_overdue_actions` | GET | All authenticated | Overdue actions |
| 3.8.1 | `check_asset_compliance_status` | GET | All authenticated | Cross-module gate BR-16-09 |

---

## §2 Role Constants

```python
# assetcore/api/imm16.py

_DOCTYPE_RULE     = "IMM Compliance Rule"
_DOCTYPE_FINDING  = "IMM Compliance Finding"
_DOCTYPE_AUDIT    = "IMM Internal Audit"
_DOCTYPE_CAPA     = "IMM CAPA Record"          # LIVE — REUSE
_DOCTYPE_SCORECARD = "IMM Compliance Scorecard"
_DOCTYPE_MR       = "IMM Management Review"
_DOCTYPE_RCA      = "IMM RCA Record"           # LIVE — REUSE

_WAIVE_ROLES              = {"VP Block2", "CMMS Admin"}
_PUBLISH_SCORECARD_ROLES  = {"Tổ HC-QLCL", "VP Block2", "CMMS Admin"}
_FINALIZE_MR_ROLES        = {"VP Block2", "CMMS Admin"}
_CLOSE_AUDIT_ROLES        = {"Tổ HC-QLCL", "VP Block2", "CMMS Admin"}
_CREATE_RULE_ROLES        = {"Tổ HC-QLCL", "CMMS Admin"}
_AUDIT_LEAD_ROLES         = {"Tổ HC-QLCL", "Internal Auditor", "CMMS Admin"}
```

---

## §3 Endpoint Specifications

### §3.1 Compliance Rule (master)

#### 3.1.3 `create_rule`

**Mô tả:** Tạo Compliance Rule mới — validate VR-01/VR-02, set version="1.0", is_active=1.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.create_rule` |

**Request body:**

```json
{
  "rule_data": {
    "rule_code": "R-IMM08-PM-COMP-90",
    "rule_name": "PM Compliance < 90%",
    "source_module": "IMM-08",
    "category": "PM",
    "severity": "High",
    "threshold_definition": {"metric": "pm_compliance_pct", "op": "<", "value": 90},
    "evaluation_frequency": "Monthly",
    "owner_role": "Workshop Head",
    "qms_doc_ref": "PR-IMMIS-08-01",
    "regulatory_reference": "ISO 13485 §7.5.1",
    "effective_date": "2026-05-01"
  }
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "R-IMM08-PM-COMP-90",
    "version": "1.0",
    "is_active": 1
  }
}
```

**Errors:** `FIN-001` (VR-01), `FIN-002` (VR-02), `FIN-003` (create fail), `FORBIDDEN`

#### 3.1.4 `update_rule`

**Mô tả:** Cập nhật Rule — VR-11 enforce change_summary nếu threshold/severity đổi, bump version.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.update_rule` |

```json
{
  "name": "R-IMM08-PM-COMP-90",
  "rule_data": {"severity": "Critical"},
  "change_summary": "Tăng severity do yêu cầu compliance mới của BYT"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "R-IMM08-PM-COMP-90",
    "version": "1.1",
    "previous_version": "1.0"
  }
}
```

**Errors:** `FIN-011` (VR-11: missing change_summary), `FORBIDDEN`

---

### §3.2 Compliance Finding

#### 3.2.1 `list_findings`

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm16.list_findings` |

**Query params:** `filters` (JSON: status, severity, responsible_dept, asset, source_module, date_range), `page`, `page_size`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "FND-2026-00001",
        "rule": "R-IMM08-PM-COMP-90",
        "detected_date": "2026-05-01 03:00:00",
        "asset": "AC-ASSET-2026-0001",
        "responsible_dept": "ICU",
        "severity": "High",
        "status": "Under Review",
        "current_value": "78",
        "threshold_value": "90",
        "capa_ref": null
      }
    ],
    "pagination": {"page": 1, "page_size": 20, "total": 42, "total_pages": 3}
  }
}
```

#### 3.2.5 `waive_finding`

**Mô tả:** Waive Finding — chỉ VP Block2 + VR-04 enforce (BR-16-06).

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.waive_finding` |

```json
{
  "name": "FND-2026-00001",
  "waiver_reason": "Finding này là false alarm do lịch PM đã điều chỉnh kỳ nghỉ Tết...",
  "waiver_evidence": "/files/evidence-waiver-001.pdf",
  "waiver_expiry": "2026-12-31"
}
```

**Validations:**
- Role IN `_WAIVE_ROLES` → else `FIN-006` FORBIDDEN
- `waiver_reason` ≥ 50 chars → else `FIN-004` VR-04
- `waiver_evidence` required → else `FIN-004` VR-04
- `waiver_expiry > today` → else `FIN-004` VR-04

**Response 200:**

```json
{
  "success": true,
  "data": {"name": "FND-2026-00001", "status": "Waived"}
}
```

---

### §3.3 Internal Audit

#### 3.3.4 `complete_audit_checklist`

**Mô tả:** Update checklist items — sinh Finding tự động cho Major/Minor NC.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.complete_audit_checklist` |

```json
{
  "audit_name": "AUD-INT-2026-00001",
  "items": [
    {
      "idx": 1,
      "finding_status": "Major NC",
      "notes": "Tài liệu bảo trì không được cập nhật",
      "clause_ref": "§7.5.1.2"
    },
    {
      "idx": 2,
      "finding_status": "Compliant",
      "notes": "OK"
    }
  ]
}
```

**Hành vi cho item finding_status="Major NC":**
1. Sinh `IMM Compliance Finding` với `severity="High"` (Major→High, Minor→Medium)
2. Set `item.linked_finding = finding.name`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "audit_name": "AUD-INT-2026-00001",
    "items_count": 2,
    "findings_created": 1
  }
}
```

#### 3.3.5 `close_audit`

**Mô tả:** Đóng Audit — VR-08 block nếu còn Major NC chưa link CAPA (BR-16-04).

```json
{
  "name": "AUD-INT-2026-00001",
  "audit_report": "/files/audit-report-q2-2026.pdf"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "AUD-INT-2026-00001",
    "status": "Closed",
    "actual_end": "2026-05-20"
  }
}
```

**Errors:** `FIN-008` (VR-08: còn Major NC chưa CAPA), `FORBIDDEN`

---

### §3.4 CAPA (operate on IMM CAPA Record LIVE)

#### 3.4.1 `create_capa_from_finding`

**Mô tả:** Tạo CAPA Record từ Finding — gọi `services.imm00.create_capa` + set Custom Fields IMM-16.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm16.create_capa_from_finding` |

```json
{
  "finding_name": "FND-2026-00001",
  "imm_risk_level": "High",
  "imm_root_cause_method": "5-Why",
  "responsible": "nguyenvana@hospital.vn",
  "due_date": "2026-06-15"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "capa_name": "CAPA-2026-00007",
    "finding_name": "FND-2026-00001",
    "workflow_state": "Open"
  }
}
```

#### 3.4.2 `advance_capa_state`

**Mô tả:** Advance workflow_state của CAPA Record — server-side VR-05/06/07/12 enforce.

```json
{
  "name": "CAPA-2026-00007",
  "target_state": "Action Plan",
  "payload": {
    "imm_root_cause_method": "5-Why",
    "due_date": "2026-06-15"
  }
}
```

**State-specific validations:**

| target_state | Validation |
|---|---|
| Action Plan | VR-05 `imm_root_cause_method` reqd; VR-12 `due_date > today` |
| Implementation | Tất cả `imm_action_plan` rows có `owner` + `planned_date` |
| Verification | Tất cả `imm_action_plan` rows `status="Done"` |
| Closed | VR-06 `effectiveness_check` reqd; VR-07 phải = "Effective" |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00007",
    "workflow_state": "Action Plan",
    "status": "In Progress"
  }
}
```

#### 3.4.3 `perform_effectiveness_check`

**Mô tả:** Kết quả effectiveness check — Effective → Close; Not Effective → Re-open + imm_reopen_count++.

```json
{
  "name": "CAPA-2026-00007",
  "result": "Effective",
  "effectiveness_evidence": "/files/evidence-capa-eff-001.pdf"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00007",
    "new_state": "Closed",
    "imm_reopen_count": 0
  }
}
```

**Khi Not Effective:**

```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00007",
    "new_state": "Investigating",
    "imm_reopen_count": 1
  }
}
```

---

### §3.5 Compliance Scorecard

#### 3.5.3 `get_scorecard_by_period`

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm16.get_scorecard_by_period` |

**Params:** `year=2026&month=4&scope=Hospital`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "SCR-2026-04-0001",
    "period_year": 2026,
    "period_month": 4,
    "scope": "Hospital",
    "score_pct": 87.5,
    "trend_vs_prev_month": 2.3,
    "score_by_module": [
      {"module": "IMM-08", "score": 91.0},
      {"module": "IMM-11", "score": 72.0}
    ],
    "score_by_department": [
      {"dept": "ICU", "score": 92.0},
      {"dept": "CT", "score": 74.0}
    ],
    "capa_open_count": 18,
    "capa_overdue_count": 5,
    "is_published": 1
  }
}
```

#### 3.5.4 `publish_scorecard`

**Mô tả:** Publish Scorecard — VR-10 gate: quý trước phải có MR Closed (BR-16-08).

```json
{"name": "SCR-2026-04-0001"}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "SCR-2026-04-0001",
    "is_published": 1,
    "published_at": "2026-05-05 09:30:00",
    "approved_by_for_review": "vp2@hospital.vn"
  }
}
```

**Errors:** `FIN-010` (VR-10: quý trước thiếu MR), `FIN-009` (VR-09: đã published), `FORBIDDEN`

---

### §3.6 Management Review

#### 3.6.3 `finalize_management_review`

```json
{
  "name": "MR-2026-00001",
  "minutes_doc": "/files/mr-minutes-q2-2026.pdf",
  "output_actions": [
    {
      "action": "Đẩy mạnh PM IMM-08 tại OR",
      "owner": "wshead@hospital.vn",
      "due_date": "2026-09-30"
    }
  ]
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "MR-2026-00001",
    "status": "Closed",
    "quarter": "Q2-2026"
  }
}
```

---

### §3.7 Dashboard / Reports

#### 3.7.1 `get_dashboard_stats`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "kpis": {
      "overall_compliance_pct": 87.5,
      "findings_open": 24,
      "findings_critical": 3,
      "capa_open": 18,
      "capa_overdue": 5,
      "audits_in_progress": 2,
      "mr_quarterly_status": "Pending"
    },
    "trend_12m": [
      {"month": "2025-06", "score_pct": 82.0},
      {"month": "2026-05", "score_pct": 87.5}
    ],
    "top_modules_low": [
      {"module": "IMM-11", "score": 72.0},
      {"module": "IMM-09", "score": 78.0}
    ],
    "recent_findings": []
  }
}
```

#### 3.7.2 `get_compliance_heatmap`

**Params:** `period_year=2026&period_month=4`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "modules": ["IMM-04","IMM-05","IMM-08","IMM-09","IMM-11","IMM-12","IMM-15"],
    "departments": ["ICU","OR","ER","CT","Internal Med","Pediatric"],
    "matrix": [
      {"module":"IMM-08","dept":"ICU","score":92.0,"findings_count":2},
      {"module":"IMM-08","dept":"OR","score":78.0,"findings_count":5},
      {"module":"IMM-11","dept":"CT","score":65.0,"findings_count":8}
    ]
  }
}
```

---

### §3.8 Cross-module Gate

#### 3.8.1 `check_asset_compliance_status`

**Mô tả:** Gọi bởi `services/imm08.py` + `services/imm09.py` validate_* trước WO Submit; và IMM-13/14 trước decommission.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm16.check_asset_compliance_status` |

**Params:** `asset=AC-ASSET-2026-0001`

**Response blocked:**

```json
{
  "success": true,
  "data": {
    "blocked": true,
    "asset": "AC-ASSET-2026-0001",
    "reasons": [
      {
        "type": "CAPA_CRITICAL_OPEN",
        "ref": "CAPA-2026-00007",
        "status": "In Progress",
        "workflow_state": "Implementation",
        "message": "CAPA Critical chưa close"
      }
    ],
    "active_findings_count": 2,
    "active_capas_count": 1
  }
}
```

**Response not blocked:**

```json
{
  "success": true,
  "data": {
    "blocked": false,
    "active_findings_count": 0,
    "active_capas_count": 0
  }
}
```

---

## §4 Error Code Catalog

| Code | HTTP Analog | Business Rule | Mô tả |
|---|---|---|---|
| `FIN-001` | 422 | VR-01 | Threshold JSON không hợp lệ — thiếu metric/op/value |
| `FIN-002` | 422 | VR-02 | evaluation_frequency không hợp lệ |
| `FIN-003` | 500 | — | Không thể tạo Rule |
| `FIN-004` | 422 | VR-04 | Waiver thiếu lý do/evidence/expiry hợp lệ |
| `FIN-005` | 422 | VR-05 | CAPA phải chọn root_cause_method khi advance to Action Plan |
| `FIN-006` | 403 | BR-16-06 | Role không được phép waive (chỉ VP Block2) |
| `FIN-007` | 422 | VR-07 | CAPA không thể Close khi effectiveness chưa Effective |
| `FIN-008` | 422 | VR-08 | Audit có Major NC chưa link CAPA (BR-16-04) |
| `FIN-009` | 422 | VR-09 | Scorecard đã published — không thể sửa |
| `FIN-010` | 422 | VR-10 | Quý trước thiếu Management Review (BR-16-08) |
| `FIN-011` | 422 | VR-11 | Thay đổi Rule threshold/severity thiếu change_summary |
| `FIN-012` | 422 | VR-12 | CAPA due_date phải sau hôm nay (Action Plan) |
| `FIN-013` | 422 | BR-16-09 | Asset bị block do CAPA Critical OPEN |
| `INVALID_STATE` | 422 | — | Workflow transition không hợp lệ |
| `NOT_FOUND` | 404 | — | DocType không tồn tại |
| `FORBIDDEN` | 403 | — | Role không có quyền |
| `VALIDATION_ERROR` | 422 | — | Generic validation fail |
| `CREATE_ERROR` | 500 | — | Insert exception |
| `MR_MISSING_QUARTERLY` | 422 | BR-16-08 | Alias cho FIN-010 |
| `CAPA_LINK_REQUIRED` | 422 | BR-16-04 | Alias cho FIN-008 |

---

## §5 TypeScript Types

> ⚠️ Pending implementation — Wave 3

```typescript
// frontend/src/types/imm16.ts

// ── Finding ──────────────────────────────────────────────────────────
export type FindingSeverity = 'Low' | 'Medium' | 'High' | 'Critical'

export type FindingStatus =
  | 'Open'
  | 'Under Review'
  | 'Confirmed NC'
  | 'False Positive'
  | 'Resolved'
  | 'Waived'
  | 'Closed'

export interface ComplianceFinding {
  name: string
  rule: string
  detected_date: string
  asset: string | null
  responsible_dept: string | null
  severity: FindingSeverity
  current_value: string | null
  threshold_value: string | null
  status: FindingStatus
  capa_ref: string | null
  waiver_reason: string | null
  waiver_expiry: string | null
  evaluation_date: string
  workflow_state: string
}

// ── CAPA ─────────────────────────────────────────────────────────────
export type CapaWorkflowState =
  | 'Open'
  | 'Investigating'
  | 'Action Plan'
  | 'Implementation'
  | 'Verification'
  | 'Closed'
  | 'Re-opened'

export type CapaRiskLevel = 'Low' | 'Medium' | 'High' | 'Critical'

export interface CapaRecord {
  name: string
  asset: string
  severity: string
  status: string
  workflow_state: CapaWorkflowState
  source_type: string
  source_ref: string | null
  due_date: string | null
  closed_date: string | null
  effectiveness_check: 'Effective' | 'Partially Effective' | 'Not Effective' | null
  imm_root_cause_method: string | null
  imm_risk_level: CapaRiskLevel
  imm_reopen_count: number
  imm_compliance_finding_ref: string | null
  imm_rca_ref: string | null
  imm_action_plan: CapaActionStep[]
}

export interface CapaActionStep {
  step_no: number
  action_description: string
  owner: string | null
  planned_date: string | null
  completed_date: string | null
  status: 'Pending' | 'In Progress' | 'Done' | 'Blocked'
}

// ── Scorecard ─────────────────────────────────────────────────────────
export interface ScoreByModule {
  module: string
  score: number
  findings_count: number
}

export interface ScoreByDepartment {
  dept: string
  score: number
  findings_count: number
}

export interface ComplianceScorecard {
  name: string
  period_year: number
  period_month: number
  scope: 'Hospital' | 'Block' | 'Department'
  score_pct: number
  trend_vs_prev_month: number
  score_by_module: ScoreByModule[]
  score_by_department: ScoreByDepartment[]
  capa_open_count: number
  capa_overdue_count: number
  is_published: boolean
  published_at: string | null
  approved_by_for_review: string | null
  restate_of: string | null
}

// ── Dashboard ─────────────────────────────────────────────────────────
export interface DashboardKpis {
  overall_compliance_pct: number
  findings_open: number
  findings_critical: number
  capa_open: number
  capa_overdue: number
  audits_in_progress: number
  mr_quarterly_status: 'Done' | 'Pending' | 'Overdue'
}

export interface DashboardStats {
  kpis: DashboardKpis
  trend_12m: { month: string; score_pct: number }[]
  top_modules_low: { module: string; score: number }[]
  recent_findings: ComplianceFinding[]
}

// ── Heatmap ────────────────────────────────────────────────────────────
export interface HeatmapCell {
  module: string
  dept: string
  score: number
  findings_count: number
}

export interface ComplianceHeatmap {
  modules: string[]
  departments: string[]
  matrix: HeatmapCell[]
}

// ── Gate ────────────────────────────────────────────────────────────────
export interface GateReason {
  type: 'CAPA_CRITICAL_OPEN'
  ref: string
  status: string
  workflow_state: string
  message: string
}

export interface ComplianceGateResult {
  blocked: boolean
  asset?: string
  reasons?: GateReason[]
  active_findings_count: number
  active_capas_count: number
}

// ── API response helpers ───────────────────────────────────────────────
export interface ApiOk<T> {
  success: true
  data: T
}

export interface ApiErr {
  success: false
  error: string
  code: string
}

export type ApiResult<T> = ApiOk<T> | ApiErr
```

---

## §6 Webhook / Realtime Events

| Event | Trigger | Payload |
|---|---|---|
| `imm16:finding_created` | `upsert_finding()` | `{name, severity, asset, dept}` |
| `imm16:finding_status_changed` | confirm / false_positive / waive | `{name, status, reviewer}` |
| `imm16:capa_created` | `create_capa_from_finding` | `{name, risk_level, source_ref}` |
| `imm16:capa_state_changed` | `advance_capa_state` | `{name, new_state, reopen_count}` |
| `imm16:scorecard_published` | `publish_scorecard` | `{name, period, score_pct}` |
| `imm16:audit_closed` | `close_audit` | `{name, findings_count}` |

Phát qua `frappe.publish_realtime(channel, payload)`. FE subscribe trong `stores/imm16Store.ts`.

---

## §7 Endpoint ↔ Business Rule Mapping

| Endpoint | Business Rules |
|---|---|
| `create_rule` | VR-01 (threshold JSON), VR-02 (frequency) |
| `update_rule` | VR-11 (change_summary khi threshold/severity đổi), BR-16-05 |
| `waive_finding` | VR-04 (reason/evidence/expiry), BR-16-06 (role VP Block2) |
| `close_audit` | VR-08 (Major NC phải có CAPA), BR-16-04 |
| `advance_capa_state(Action Plan)` | VR-05 (root_cause_method), VR-12 (due_date) |
| `advance_capa_state(Closed)` | VR-06 (effectiveness_check), VR-07 (phải Effective), BR-16-03 |
| `perform_effectiveness_check` | BR-16-03 (Re-open nếu Not Effective) |
| `publish_scorecard` | VR-09 (immutable), VR-10 (MR quý trước), BR-16-07, BR-16-08 |
| `check_asset_compliance_status` | BR-16-09 (gate IMM-08/09/13/14) |
