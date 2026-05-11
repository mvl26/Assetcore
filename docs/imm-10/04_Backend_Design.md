# IMM-10 — Backend Design

| Mục | Giá trị |
|---|---|
| Module | IMM-10 — Hậu kiểm và tuân thủ |
| Đợt | 3 |
| Trạng thái | Skeleton (BE chưa scaffold) |
| Cập nhật | 2026-05-10 |

> File này là **skeleton**. DocType field, workflow JSON cụ thể, service signature chi tiết sẽ được scaffold trong Sprint Wave 3 sau khi IMM-16 ready. Các giá trị `*(Thiết kế trong sprint Wave 3)*` không được tự ý fill nếu chưa có user story chốt.

---

## I. DocType (dự kiến)

Tham chiếu skill `assetcore-doctype-designer` + CONVENTIONS §1. 3 prefix song song: `AC ` (master), `IMM ` (module-only), không prefix (cross-module).

### I.1 — DocType mới

| DocType | Submittable | Naming | Mục đích |
|---|---|---|---|
| `IMM Compliance Case` | Yes | `CC-.YYYY.-.#####` *(Sprint Wave 3 — chốt naming series)* | Bản ghi case post-market: Recall / FSCA / PMS Signal |
| `IMM Affected Asset` (child of Compliance Case) | — | — | Danh sách asset trong scope + action_required |
| `IMM Disclosure Log` (child) | — | — | Log gửi công văn tới regulator |
| `IMM Effectiveness Check` (child hoặc standalone) | *(Sprint Wave 3)* | — | Check 30/60/90 ngày sau close |
| `IMM Recall Action Template` | No | `field:template_name` | Template communication / công văn |

*(Field detail — fieldname, fieldtype, mandatory, link target — Thiết kế trong sprint Wave 3 sau khi BA chốt user stories.)*

### I.2 — DocType reuse (bắt buộc)

| DocType | Wave | Vai trò trong IMM-10 |
|---|---|---|
| `AC Asset` | 1 | Master scope finder query |
| `IMM Device Model` | 1 | Scope by model |
| `AC Supplier` | 2 | Vendor liaison |
| `IMM CAPA Record` | 1 | CAPA preventive cho case (link parent_case) |
| `Incident Report` | 1 | Source PMS signal |
| `IMM RCA Record` | 1 | RCA chronic failure |
| `IMM Audit Trail` | 1 | Hash chain audit (R-04) |
| `Asset Lifecycle Event` | 1 | Event `recall_initiated`, `case_closed` |
| `PM Work Order` | 1 | Bulk WO type=Recall (qua IMM-08) |
| `Asset Repair` | 1 | Bulk WO action=Replace/Repair (qua IMM-09) |
| `Asset Transfer` | 1 | Reconcile lịch sử điều chuyển khi auto-scope |

> **Quy tắc (R-01, R-06)**: KHÔNG tham chiếu DocType ERPNext. KHÔNG tự đặt prefix `AssetCore `. Field mới mở rộng IMM CAPA Record (link parent_case) dùng Custom Field qua fixtures.

---

## II. Service Layer (3-tier)

Tham chiếu CONVENTIONS §2 + skill `assetcore-be-module`. Cấu trúc chuẩn:

```
assetcore/api/imm10.py             # whitelist + validate input
assetcore/services/imm10.py        # business logic
assetcore/repositories/compliance_case_repo.py   # data access
```

### II.1 — Module skeleton

```python
# assetcore/services/imm10.py  (skeleton — Sprint Wave 3)
def open_case(payload: dict) -> str: ...
def find_scope(case: str) -> dict: ...
def lock_scope(case: str) -> None: ...
def start_disclosure_timer(case: str) -> None: ...
def send_disclosure(case: str, regulator: str, doc_no: str) -> None: ...
def bulk_create_recall_wo(case: str, wo_type: str = "PM") -> list[str]: ...
def close_case(case: str, approver: str) -> None: ...
def schedule_effectiveness_check(case: str) -> None: ...
def list_capa_tracker(filters: dict) -> list[dict]: ...
```

*(Signature chi tiết, return shape, error handling — Thiết kế trong sprint Wave 3.)*

### II.2 — Lifecycle / Audit integration (R-04, R-05)

Mọi mutation trên Compliance Case PHẢI gọi:

```python
from assetcore.utils.lifecycle import log_audit_event, create_lifecycle_event

log_audit_event(
    asset=None,                          # case-level audit, asset có thể None
    event_type="compliance.case.opened", # hoặc .scope_locked, .disclosure_sent, .closed
    actor=frappe.session.user,
    ref_doctype="IMM Compliance Case",
    ref_name=case_no,
    change_summary="...",
)

create_lifecycle_event(
    asset=affected_asset,
    event_type="recall_initiated",       # hoặc recall_completed, fsca_applied
    root_doctype="IMM Compliance Case",
    root_record=case_no,
)
```

(API duy nhất — không insert `IMM Audit Trail` thẳng.)

### II.3 — Repository pattern

```python
# assetcore/repositories/compliance_case_repo.py  (skeleton)
class ComplianceCaseRepo:
    def get(self, name: str): ...
    def list(self, filters: dict, limit: int = 50): ...
    def list_open(self): ...
    def list_breach(self): ...
    def save(self, doc): ...
```

(Mirror pattern `repair_repo.py` đã có — refer `assetcore/repositories/repair_repo.py`.)

---

## III. Workflow

### III.1 — Workflow `IMM-10 Compliance Workflow`

DocType: `IMM Compliance Case`. State naming Title Case có space (R-10).

| State | docstatus | Type | Allowed roles (transition out) |
|---|---|---|---|
| Draft | 0 | Default | IMM QA Officer |
| Scope Identification | 0 | Warning | IMM QA Officer |
| Disclosure Pending | 0 | Danger | IMM QA Officer, IMM Document Officer (Pháp chế) |
| Action Pending | 0 | Warning | IMM QA Officer, IMM Workshop Lead |
| Escalated | 0 | Danger | IMM Operations Manager (BGĐ) |
| Verifying | 0 | Primary | IMM QA Officer |
| Closed | 1 | Success | IMM Operations Manager + IMM QA Officer |
| Effectiveness Check | 1 | Warning | IMM QA Officer (read; system schedules) |

**Transitions (overview)** — chi tiết action label tiếng Việt sẽ scaffold:

| From | To | Action (VN) | Role |
|---|---|---|---|
| Draft | Scope Identification | Xác nhận tín hiệu | IMM QA Officer |
| Scope Identification | Disclosure Pending | Khóa scope (regulatory) | IMM QA Officer |
| Scope Identification | Action Pending | Khóa scope (nội bộ) | IMM QA Officer |
| Disclosure Pending | Action Pending | Đã gửi công văn | IMM Document Officer |
| Disclosure Pending | Escalated | Quá 48h | (System) |
| Action Pending | Verifying | Hoàn tất 100% asset | IMM Workshop Lead |
| Verifying | Closed | Phê duyệt đóng | IMM Operations Manager |
| Closed | Effectiveness Check | (System scheduler) | — |

*(Workflow JSON file `imm_10_compliance_workflow.json` — Thiết kế trong sprint Wave 3, refer skill `assetcore-workflow-builder`.)*

---

## IV. Hooks

Tham chiếu `assetcore/hooks.py` Wave 1/2 layout.

### IV.1 — doc_events (dự kiến)

```python
# Bổ sung vào hooks.py khi Sprint Wave 3
doc_events = {
    "IMM Compliance Case": {
        "validate": "assetcore.services.imm10.validate_case",
        "on_submit": [
            "assetcore.services.imm10.on_case_submit_audit",
            "assetcore.services.imm10.publish_lifecycle_events",
        ],
    },
    "Incident Report": {
        "after_insert": "assetcore.services.imm10.subscribe_chronic_failure_signal",
    },
    "IMM Asset Calibration": {
        "on_submit": "assetcore.services.imm10.subscribe_calibration_fail_signal",
    },
}
```

### IV.2 — scheduler_events (dự kiến)

| Tần suất | Job | Mục đích |
|---|---|---|
| hourly | `imm10.check_disclosure_breach` | BR-10-05 — escalation 48h |
| daily | `imm10.run_effectiveness_check` | Nhắc check 30/60/90 ngày |
| daily | `imm10.detect_chronic_failure_signals` | Aggregate IMM-09/12 → mở PMS Signal |
| weekly | `imm10.capa_tracker_alert` | Cảnh báo CAPA quá hạn |
| monthly | `imm10.feed_management_review` | Đẩy entry sang IMM-16 Management Review |

### IV.3 — permission_query_conditions

Compliance Case sensitive — không phải role nào cũng đọc được. Permission scope:

- `IMM QA Officer`, `IMM Operations Manager`: full đọc.
- `IMM Workshop Lead`, `IMM Biomed Technician`: chỉ đọc case có asset thuộc scope phụ trách.
- `Vendor Engineer`: chỉ đọc affected_assets liên quan tới chính vendor đó (filter qua `vendor` field).
- Khoa lâm sàng: chỉ đọc case `severity ≥ High` đã `Action Pending` trở đi.

```python
# assetcore/permissions.py  (dự kiến bổ sung)
permission_query_conditions = {
    ...,
    "IMM Compliance Case": "assetcore.permissions.compliance_case_query",
}
```

(Logic chi tiết refer skill `assetcore-security` + CONVENTIONS §5.)

### IV.4 — Fixtures (dự kiến)

```
assetcore/fixtures/
├── imm10_compliance_workflow.json     (Workflow + Workflow State + Workflow Action Master)
├── imm10_recall_action_template.json  (template công văn disclosure)
└── imm10_sla_policy.json              (SLA: 48h disclosure, 30 ngày recall completion)
```

---

## V. Dependency với IMM-16

IMM-10 KHÔNG tự định nghĩa Compliance Rule chung. Module **đăng ký** rule chuyên biệt vào engine của [IMM-16](../imm-16/README.md):

| Rule code (dự kiến) | Trigger | Hành động |
|---|---|---|
| `DISCLOSURE_BREACH_48H` | Compliance Case `disclosure_due_at` quá hạn | Tạo Compliance Finding sang IMM-16 + alert BGĐ |
| `RECALL_COMPLETION_OVERDUE` | Case mở > 30 ngày, completion < 100% | Finding warning |
| `EFFECTIVENESS_CHECK_MISSED` | Check 30/60/90 ngày không thực hiện trong 14 ngày deadline | Finding |
| `CHRONIC_FAILURE_DETECTED` | ≥3 incident cùng model trong 90 ngày | Tự mở Compliance Case PMS Signal |

(Mapping với IMM-16 Compliance Rule Engine — refer `docs/imm-16/04_Backend_Design.md`.)

---

## VI. Idempotency & Side-effect notes

- `bulk_create_recall_wo` PHẢI idempotent — re-call không tạo WO trùng (check `case_ref` field trên WO).
- Disclosure send là one-shot — `disclosure_sent_at` set rồi không gọi lại; muốn gửi bổ sung phải mở revision case.
- Effectiveness check scheduler check `last_run_at` để không tạo task trùng.

*(Test idempotency theo CONVENTIONS §6 — refer `07_Testing_QA.md` §V.)*

---

*Cập nhật: 2026-05-10. Skeleton — chi tiết DocType field + Workflow JSON sẽ scaffold trong Sprint Wave 3 sau khi IMM-16 GA.*
