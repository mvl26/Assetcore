# IMM-06 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phiên bản | 0.1.0 (Wave 2 — DRAFT) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PLANNED |
| Tác giả | AssetCore Team |

---

## 1. Overview

### 1.1 Layered architecture

```
Request (HTTP / Workflow Action / Scheduler / Cross-module hook)
    │
    ▼
API Layer  (assetcore/api/imm06.py — ~19 endpoints, @frappe.whitelist())
    │
    ▼
Service Layer  (assetcore/services/imm06.py)   ◀── BUILD MỚI, không lặp tech-debt IMM-05
    │   - create_competency_from_session()
    │   - compute_operator_coverage()
    │   - generate_gap_report()
    │   - trigger_recertification()
    │   - validate_user_authorization()
    │
    ▼
Controller (assetcore/.../doctype/imm_*/...py)
    │   validate(), before_save(), on_update(), on_trash()
    │   12 VR + business hooks
    │
    ▼
Frappe ORM → MariaDB
    │   tabIMM Training Program
    │   tabIMM Training Session
    │   tabIMM Training Participant   (child of Session)
    │   tabIMM User Competency
    │   tabIMM Competency Gap Report
    │   tabIMM Competency Alert Log   (idempotent log scheduler)
    ▼
Side effects:
  - Frappe Version (auto, track_changes=1)
  - IMM Audit Trail (cross-cutting log cho revoke/suspend/sign-off)
  - Asset Document (IMM-05) — certificate file
  - Email Notification (Frappe Notification Settings)
```

> **Design principle:** Tách service layer từ đầu — controller chỉ orchestrate, business logic phức tạp (auto-create competency, gap calc, recert) nằm trong `services/imm06.py` để dễ test và refactor. Đây là điểm khác biệt với IMM-05 (đang nợ tech-debt).

### 1.2 Files

| File | Vai trò |
|---|---|
| `assetcore/assetcore/doctype/imm_training_program/imm_training_program.json` | DocType schema |
| `assetcore/assetcore/doctype/imm_training_program/imm_training_program.py` | Controller (`IMMTrainingProgram` class) |
| `assetcore/assetcore/doctype/imm_training_session/imm_training_session.json` | DocType schema |
| `assetcore/assetcore/doctype/imm_training_session/imm_training_session.py` | Controller (`IMMTrainingSession`) |
| `assetcore/assetcore/doctype/imm_training_participant/imm_training_participant.json` | Child DocType |
| `assetcore/assetcore/doctype/imm_user_competency/imm_user_competency.json` | DocType schema |
| `assetcore/assetcore/doctype/imm_user_competency/imm_user_competency.py` | Controller (`IMMUserCompetency`) |
| `assetcore/assetcore/doctype/imm_competency_gap_report/imm_competency_gap_report.json` | DocType schema |
| `assetcore/assetcore/doctype/imm_competency_alert_log/imm_competency_alert_log.json` | Log idempotent scheduler |
| `assetcore/assetcore/workflow/imm_06_session_workflow.json` | Workflow Session |
| `assetcore/assetcore/workflow/imm_06_competency_workflow.json` | Workflow Competency |
| `assetcore/services/imm06.py` | Service layer |
| `assetcore/api/imm06.py` | REST endpoints |
| `assetcore/tasks.py` | Scheduler functions (4 jobs) |

---

## 2. DocType Schemas

### 2.1 IMM Training Program (`tabIMM Training Program`)

**Config:**

| Property | Value |
|---|---|
| name | IMM Training Program |
| module | AssetCore |
| autoname | `field:program_code` |
| naming_rule | By fieldname |
| is_submittable | 0 |
| track_changes | 1 |
| title_field | `program_name` |
| sort_field | `modified` |
| search_fields | `program_code,program_name,target_device_model` |

**Fields:**

#### Section: Định danh

| # | fieldname | fieldtype | label | options | reqd | in_list_view |
|---|---|---|---|---|:---:|:---:|
| 1 | program_code | Data | Mã chương trình | unique | * | 1 |
| 2 | program_name | Data | Tên chương trình | — | * | 1 |
| 3 | description | Text | Mô tả | — | — | — |

#### Section: Phạm vi áp dụng

| # | fieldname | fieldtype | options | reqd |
|---|---|---|---|:---:|
| 4 | target_device_model | Link | IMM Device Model | — |
| 5 | target_device_category | Link | AC Asset Category | — |
| 6 | is_mandatory_for_operation | Check | — | — |

> Tối thiểu 1 trong (`target_device_model`, `target_device_category`) phải set — VR enforce.

#### Section: Loại & nội dung

| # | fieldname | fieldtype | options | reqd | default |
|---|---|---|---|:---:|---|
| 7 | training_type | Select | Initial / Refresher / Advanced / Certification | * | Initial |
| 8 | content_outline | Text Editor | — | * | — |
| 9 | duration_hours | Float | — | * | 8 |

#### Section: Hiệu lực

| # | fieldname | fieldtype | reqd | default |
|---|---|---|:---:|---|
| 10 | validity_period_months | Int | * | 24 |
| 11 | requires_recertification | Check | — | 1 |

#### Section: Đánh giá

| # | fieldname | fieldtype | options | reqd | default |
|---|---|---|---|:---:|---|
| 12 | assessment_method | Select | Theory / Practical / Both | * | Both |
| 13 | passing_score_pct | Float | — | * | 70 |
| 14 | instructor_qualification_required | Data | — | — | — |

#### Section: QMS & Trạng thái

| # | fieldname | fieldtype | options | default |
|---|---|---|---|---|
| 15 | qms_doc_ref | Link | Asset Document | — |
| 16 | is_active | Check | — | 1 |

**Permissions:**

| Role | read | write | create | delete |
|---|:---:|:---:|:---:|:---:|
| Tổ HC-QLCL | 1 | 1 | 1 | — |
| Workshop Head | 1 | — | — | — |
| Biomed Engineer | 1 | — | — | — |
| HTM Technician | 1 | — | — | — |
| CMMS Admin | 1 | 1 | 1 | 1 |
| Clinical Head | 1 | — | — | — |

---

### 2.2 IMM Training Session (`tabIMM Training Session`)

**Config:**

| Property | Value |
|---|---|
| autoname | `TRN-.YYYY.-.#####` |
| is_submittable | 0 |
| track_changes | 1 |
| title_field | `training_program` |
| sort_field | `session_date` (DESC) |
| search_fields | `training_program,instructor,location` |

**Fields:**

#### Section: Liên kết & Trạng thái

| # | fieldname | fieldtype | options | reqd | read_only |
|---|---|---|---|:---:|:---:|
| 1 | workflow_state | Link | Workflow State | — | 1 |
| 2 | training_program | Link | IMM Training Program | * | — |
| 3 | session_date | Date | — | * | — |
| 4 | session_type | Select | Onsite / Online / Hybrid | * | — |
| 5 | location | Data | — | — | — |

#### Section: Giảng viên

| # | fieldname | fieldtype | options | reqd |
|---|---|---|---|:---:|
| 6 | instructor | Link | User | — |
| 7 | instructor_external_name | Data | — | — |
| 8 | instructor_external_org | Data | — | — |

> Tối thiểu 1 trong (`instructor`, `instructor_external_name`) reqd — VR enforce.

#### Section: Thời lượng

| # | fieldname | fieldtype | reqd | read_only |
|---|---|---|:---:|:---:|
| 9 | duration_planned_hours | Float | * | — |
| 10 | duration_actual_hours | Float | — | — |

#### Section: Tài liệu & Kết quả

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 11 | training_materials | Attach | — |
| 12 | qms_session_record | Attach | — |
| 13 | evaluation_method | Small Text | — |
| 14 | status_remarks | Small Text | — |

#### Section: Học viên

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 15 | participants | Table | IMM Training Participant |

**Permissions:**

| Role | read | write | create | submit | cancel |
|---|:---:|:---:|:---:|:---:|:---:|
| Tổ HC-QLCL | 1 | 1 | 1 | 1 | 1 |
| Workshop Head | 1 | 1 | — | 1 | — |
| Biomed Engineer | 1 | 1 | 1 | — | — |
| HTM Technician | 1 | 1 | — | — | — |
| CMMS Admin | 1 | 1 | 1 | 1 | 1 |

---

### 2.3 IMM Training Participant (Child of Session)

**Config:**

| Property | Value |
|---|---|
| istable | 1 |
| autoname | `hash` |

**Fields:**

| # | fieldname | fieldtype | options | reqd | in_list_view |
|---|---|---|---|:---:|:---:|
| 1 | user | Link → User | — | * | 1 |
| 2 | department | Link → AC Department | — | — | 1 |
| 3 | role_at_session | Data | — | — | — |
| 4 | attendance_pct | Float (0-100) | — | — | 1 |
| 5 | theory_score | Float (0-100) | — | — | 1 |
| 6 | practical_score | Float (0-100) | — | — | 1 |
| 7 | overall_result | Select | Pass / Fail / Conditional | — | 1 |
| 8 | certificate_issued | Check | — | — | — |
| 9 | retake_required | Check | — | — | — |
| 10 | competency_record | Link → IMM User Competency (read_only) | — | — | — |
| 11 | remarks | Small Text | — | — | — |

---

### 2.4 IMM User Competency (`tabIMM User Competency`)

**Config:**

| Property | Value |
|---|---|
| autoname | `COMP-.YYYY.-.#####` |
| is_submittable | 0 |
| track_changes | 1 |
| title_field | `user` |
| sort_field | `expiry_date` (ASC) |
| search_fields | `user,device_model,training_program` |

**Fields:**

#### Section: Liên kết

| # | fieldname | fieldtype | options | reqd | read_only |
|---|---|---|---|:---:|:---:|
| 1 | workflow_state | Link | Workflow State | — | 1 |
| 2 | user | Link | User | * | — |
| 3 | device_model | Link | IMM Device Model | * | — |
| 4 | training_program | Link | IMM Training Program | * | — |
| 5 | training_session | Link | IMM Training Session | — | 1 |
| 6 | department_at_assessment | Link | AC Department | — | 1 |

#### Section: Cấp độ & Hiệu lực

| # | fieldname | fieldtype | options | reqd | default | read_only |
|---|---|---|---|:---:|---|:---:|
| 7 | competency_level | Select | Trainee / Operator / Senior Operator / Trainer | * | Operator | — |
| 8 | achieved_date | Date | — | * | — | — |
| 9 | validity_months | Int | — | — | 24 | — |
| 10 | expiry_date | Date | — | — | — | 1 (computed) |
| 11 | recertification_due_date | Date | — | — | — | 1 (computed = expiry - 60d) |

#### Section: Đánh giá

| # | fieldname | fieldtype | read_only |
|---|---|---|:---:|
| 12 | last_assessment_score | Float | 1 |
| 13 | theory_score | Float | 1 |
| 14 | practical_score | Float | 1 |

#### Section: Sign-off

| # | fieldname | fieldtype | options | read_only |
|---|---|---|---|:---:|
| 15 | supervisor_signoff | Link | User | 1 |
| 16 | signoff_date | Date | — | 1 |
| 17 | certificate_file | Link | Asset Document | — |

#### Section: Thu hồi

| # | fieldname | fieldtype | options | read_only |
|---|---|---|---|:---:|
| 18 | revoke_reason | Small Text | — | — |
| 19 | revoke_capa_ref | Link | CAPA | — |
| 20 | revoked_by | Link | User | 1 |
| 21 | revoked_date | Datetime | — | 1 |
| 22 | suspended_until | Date | — | — |

#### Section: Status meta (computed)

| # | fieldname | fieldtype | read_only |
|---|---|---|:---:|
| 23 | days_until_expiry | Int | 1 |
| 24 | is_expired | Check | 1 |

**Permissions:**

| Role | read | write | create | delete |
|---|:---:|:---:|:---:|:---:|
| Tổ HC-QLCL | 1 | 1 | 1 | — |
| Workshop Head | 1 | 1 | 1 | — |
| Department Manager | 1 | 1 (own dept) | — | — |
| Clinical Head | 1 (own dept) | — | — | — |
| Biomed Engineer | 1 | — | — | — |
| Operator (self via filter) | 1 (own) | — | — | — |
| CMMS Admin | 1 | 1 | 1 | 1 |

---

### 2.5 IMM Competency Gap Report (`tabIMM Competency Gap Report`)

**Config:**

| Property | Value |
|---|---|
| autoname | `GAP-.YYYY.-.#####` |
| is_submittable | 0 |
| track_changes | 0 |

**Fields:**

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 1 | report_date | Date (default today, read_only) | — |
| 2 | scope | Select | Hospital-wide / Department / Device Class |
| 3 | scope_filter_value | Data | — |
| 4 | total_assets_class3 | Int | — |
| 5 | assets_with_gap_count | Int | — |
| 6 | gap_details | Long Text (JSON) | — |
| 7 | summary_table | Table → IMM Gap Detail Row | — |

`IMM Gap Detail Row` (child): department, device_class, total_assets, total_competent_users, required_min, gap_count, missing_users.

---

### 2.6 IMM Competency Alert Log (`tabIMM Competency Alert Log`)

Idempotent log cho scheduler — đảm bảo không tạo trùng alert cùng ngày.

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 1 | competency | Link → IMM User Competency | — |
| 2 | alert_date | Date | — |
| 3 | milestone | Select | 90 / 60 / 30 / 0 |
| 4 | alert_level | Select | Info / Warning / Critical / Danger |
| 5 | sent_to | Small Text (json users) | — |

**Unique constraint:** `(competency, alert_date, milestone)`.

---

## 3. Custom Fields (cross-module)

| Doctype | fieldname | fieldtype | Lý do |
|---|---|---|---|
| User | `competency_summary_html` | Text Editor (read_only) | Render HTML hiển thị competency tóm tắt trên User profile |
| AC Asset | `custom_operator_coverage_count` | Int (computed daily) | Cache kết quả `compute_operator_coverage` để dashboard nhanh |
| AC Asset | `custom_operator_coverage_status` | Select (OK / Insufficient) | Cache cho IMM-04 gate |

> Lưu ý: rút kinh nghiệm IMM-05 v3 — đối với truy vấn cao tần (gate) NÊN cache; đối với báo cáo (gap) tính on-the-fly. Cache được scheduler refresh mỗi đêm hoặc invalidate khi competency thay đổi (`on_update` hook).

---

## 4. Validation Rules

Implement trong `IMMUserCompetency.validate()` và `IMMTrainingSession.validate()` và `IMMTrainingProgram.validate()`:

| VR | Method | DocType | Trigger | Logic |
|---|---|---|---|---|
| VR-01 | `vr_01_expiry_after_achieved` | Competency | validate | `expiry_date > achieved_date` |
| VR-02 | `vr_02_passing_score_range` | Program | validate | `0 < passing_score_pct ≤ 100` |
| VR-03 | `vr_03_validity_range` | Program | validate | `1 ≤ validity_period_months ≤ 60` |
| VR-04 | `vr_04_instructor_qualified` | Session | validate | User của `instructor` có role match `program.instructor_qualification_required` |
| VR-05 | `vr_05_min_participants_for_confirm` | Session | before_save | `workflow_state="Confirmed"` ⇒ `len(participants) ≥ 1` |
| VR-06 | `vr_06_scores_required_complete` | Session | before_save (transition Complete) | `program.assessment_method="Both"` ⇒ mọi participant có theory_score AND practical_score |
| VR-07 | `vr_07_signoff_required_active` | Competency | before_save (transition Active) | `supervisor_signoff` reqd |
| VR-08 | `vr_08_capa_required_for_incident_revoke` | Competency | revoke API | nếu `revoke_reason` chứa keyword in {"incident","sự cố"} ⇒ `revoke_capa_ref` reqd |
| VR-09 | `vr_09_attendance_range` | Participant | validate | `0 ≤ attendance_pct ≤ 100` |
| VR-10 | `vr_10_session_date_not_past` | Session | validate (on create) | `session_date ≥ today` (trừ flag `is_backdated=1` cho nhập lịch sử) |
| VR-11 | `vr_11_target_device_model_active` | Program | validate | `target_device_model` exist + `is_active=1` |
| VR-12 | `vr_12_competency_level_match_type` | Competency | validate | `(training_type=Initial → level=Operator)`, `(Advanced → Senior Operator)`, `(Certification → Trainer)` |

---

## 5. Service Layer (`assetcore/services/imm06.py`)

Business methods chính:

```python
def create_competency_from_session(session_name: str) -> list[str]:
    """
    Khi Session.complete: tạo IMM User Competency cho mọi participant Pass.
    Returns: list of new competency names.
    Mỗi competency: status='Pending Assessment', achieved_date=session_date,
    expiry_date=session_date + program.validity_period_months,
    recertification_due_date=expiry_date - 60d.
    """

def signoff_competency(competency_name: str, supervisor_user: str) -> dict:
    """
    Supervisor sign-off — chuyển Pending Assessment → Active.
    Validate VR-07. Set supervisor_signoff, signoff_date.
    Trigger: gửi email cho user, archive_old_competency() (BR-06-11).
    """

def archive_old_competency(user: str, device_model: str, exclude: str) -> int:
    """
    Khi competency mới Active: tìm competency cùng (user × device_model) đang Active
    ngoại trừ self → set status='Suspended' với suspended_until=expiry_date_old.
    """

def compute_operator_coverage(asset: str) -> dict:
    """
    Returns: {asset, device_model, department, operator_count, required_min, gate_pass}.
    operator_count = COUNT(IMM User Competency
       WHERE device_model=asset.device_model AND department_at_assessment=asset.location
       AND status='Active').
    required_min = 2 if asset.class='III' else 1.
    """

def validate_user_authorization(user: str, device_model: str) -> dict:
    """
    Hook gọi từ IMM-08/09/12.
    Returns: {authorized: bool, competency_name, status, expiry_date, reason}.
    Cached (5 min TTL) qua frappe.cache.
    """

def trigger_recertification(competency_name: str) -> str | None:
    """
    Tạo placeholder Refresher Session + add user vào participants.
    Returns: session_name nếu tạo mới, None nếu đã có.
    """

def generate_gap_report(scope: str = "Hospital-wide") -> str:
    """
    Tính ma trận department × device_class.
    Tạo IMM Competency Gap Report record, trả về name.
    """
```

---

## 6. Controller hooks (lifecycle)

```python
class IMMUserCompetency(Document):
    def validate(self):
        self.vr_01_expiry_after_achieved()
        self.vr_07_signoff_required_active()
        self.vr_12_competency_level_match_type()
        self.set_computed_fields()  # days_until_expiry, is_expired

    def before_save(self):
        if self.workflow_state == "Active" and not self.expiry_date:
            self.expiry_date = add_months(self.achieved_date, self.validity_months)
            self.recertification_due_date = add_days(self.expiry_date, -60)

    def on_update(self):
        if self.has_value_changed("workflow_state"):
            from assetcore.services.imm06 import (
                archive_old_competency, invalidate_authorization_cache)
            if self.workflow_state == "Active":
                archive_old_competency(self.user, self.device_model, exclude=self.name)
            invalidate_authorization_cache(self.user, self.device_model)
            log_audit_trail(self, action="STATUS_CHANGE", ...)

    def on_trash(self):
        frappe.throw(_("BR-06-09: Không được phép xóa Competency. "
                       "Vui lòng dùng Suspend hoặc Revoke."))


class IMMTrainingSession(Document):
    def validate(self):
        self.vr_04_instructor_qualified()
        self.vr_05_min_participants_for_confirm()
        self.vr_10_session_date_not_past()

    def before_save(self):
        if self.workflow_state == "Completed":
            self.vr_06_scores_required_complete()
            self.compute_overall_results()  # Pass/Fail per participant

    def on_update(self):
        if self.has_value_changed("workflow_state") and self.workflow_state == "Completed":
            from assetcore.services.imm06 import create_competency_from_session
            new_competencies = create_competency_from_session(self.name)
            self.notify_supervisors_for_signoff(new_competencies)


class IMMTrainingProgram(Document):
    def validate(self):
        self.vr_02_passing_score_range()
        self.vr_03_validity_range()
        self.vr_11_target_device_model_active()

    def on_update(self):
        # BR-06-04: change control
        critical_fields = ("content_outline", "passing_score_pct",
                           "assessment_method", "duration_hours")
        if any(self.has_value_changed(f) for f in critical_fields):
            self.flag_recertification_needed()  # tạo Document Request style task
```

---

## 7. Schedulers — `assetcore/tasks.py`

### 7.1 `check_competency_expiry()` — Daily 02:00

```
For each milestone IN (90, 60, 30):
    target_date = today + milestone days
    Query IMM User Competency
        WHERE workflow_state='Active' AND expiry_date=target_date
    For each comp:
        If IMM Competency Alert Log exists (comp, today, milestone): skip
        Else:
            Create Alert Log
            Set comp.workflow_state='Expiring' (90d trigger)
            Email user + supervisor (Department Manager) + Workshop Head (theo level)
```

### 7.2 `auto_expire_competency()` — Daily 02:30

```
Query IMM User Competency WHERE workflow_state IN ('Active','Expiring')
    AND expiry_date < today
For each comp:
    comp.workflow_state = 'Expired'
    log_audit_trail(comp, action='AUTO_EXPIRE')
    invalidate_authorization_cache(comp.user, comp.device_model)
    Email user + Workshop Head
```

### 7.3 `check_recertification_due()` — Daily 03:00

```
Query Competency WHERE workflow_state='Active'
    AND recertification_due_date <= today + 60 days
For each comp:
    If no Refresher Session 'Planned' for (program, user) in next 60d:
        services.imm06.trigger_recertification(comp.name)
Send digest email Tổ HC-QLCL "X người cần tái chứng nhận trong 60 ngày"
```

### 7.4 `generate_competency_gap_report()` — Weekly Mon 02:00

```
For dept in all departments:
    For class in (II, III):
        coverage = compute coverage(dept, class)
        gap = required_min - coverage
        if gap > 0: append to gap_details
Create IMM Competency Gap Report
Email Workshop Head + VP Block2 với link
```

---

## 8. Workflow JSON Sketches

### 8.1 `imm_06_session_workflow.json`

**States (7):** Planned, Confirmed, In Progress, Completed, Verified, Closed, Cancelled.

**Transitions:**

| action | from → to | allowed |
|---|---|---|
| Xác nhận | Planned → Confirmed | Tổ HC-QLCL, CMMS Admin |
| Bắt đầu | Confirmed → In Progress | Tổ HC-QLCL, Biomed Engineer (instructor) |
| Hoàn thành | In Progress → Completed | Tổ HC-QLCL, Biomed Engineer |
| Verify | Completed → Verified | Workshop Head, CMMS Admin |
| Đóng | Verified → Closed | Workshop Head, CMMS Admin |
| Hủy | Planned/Confirmed → Cancelled | Tổ HC-QLCL, CMMS Admin |

`workflow_state_field = "workflow_state"`. `is_active = 1`.

### 8.2 `imm_06_competency_workflow.json`

**States (6):** Pending Assessment, Active, Expiring, Expired, Suspended, Revoked.

**Transitions:**

| action | from → to | allowed |
|---|---|---|
| Sign-off | Pending Assessment → Active | Department Manager, Workshop Head, Tổ HC-QLCL |
| (auto) | Active → Expiring | Scheduler check_competency_expiry |
| (auto) | Active/Expiring → Expired | Scheduler auto_expire_competency |
| Tạm ngưng | Active → Suspended | Workshop Head, Tổ HC-QLCL |
| Khôi phục | Suspended → Active | Workshop Head, Tổ HC-QLCL |
| Thu hồi | * (≠ Revoked) → Revoked | Tổ HC-QLCL, CMMS Admin |
| Tái chứng nhận (re-link) | Expired → Active | Service `trigger_recertification` after new session Pass |

---

## 9. Hooks.py registration

```python
# assetcore/hooks.py

scheduler_events = {
    "daily": [
        # IMM-05 (existing)
        "assetcore.tasks.check_document_expiry",
        "assetcore.tasks.update_asset_completeness",
        "assetcore.tasks.check_overdue_document_requests",
        # IMM-06 NEW
        "assetcore.tasks.check_competency_expiry",
        "assetcore.tasks.auto_expire_competency",
        "assetcore.tasks.check_recertification_due",
    ],
    "cron": {
        # IMM-06: weekly Monday 02:00
        "0 2 * * 1": [
            "assetcore.tasks.generate_competency_gap_report",
        ],
    },
}

doc_events = {
    "User": {
        "on_update": "assetcore.services.imm06.handle_user_dept_change",
    },
}

fixtures = [
    # ...
    {"dt": "Workflow", "filters": [["name", "in",
        ["IMM-06 Session Workflow", "IMM-06 Competency Workflow"]]]},
    {"dt": "Workflow State", "filters": [["name", "in",
        ["Planned","Confirmed","In Progress","Completed","Verified","Closed",
         "Cancelled","Pending Assessment","Active","Expiring","Expired",
         "Suspended","Revoked"]]]},
]
```

---

## 10. Database Indexes

| Bảng | Cột | Lý do |
|---|---|---|
| tabIMM User Competency | `user` | get_user_competencies — self-service |
| tabIMM User Competency | `device_model` | check_user_authorization |
| tabIMM User Competency | `workflow_state` | scheduler queries |
| tabIMM User Competency | `expiry_date` | check_competency_expiry, dashboard |
| tabIMM User Competency | `department_at_assessment` | gap report, coverage |
| tabIMM Training Session | `training_program` | session list |
| tabIMM Training Session | `session_date` | scheduler reminders |
| tabIMM Competency Alert Log | (competency, alert_date, milestone) UNIQUE | idempotent |

**Composite indexes (manual SQL):**

```sql
CREATE INDEX idx_comp_user_model_state
  ON `tabIMM User Competency` (user, device_model, workflow_state);

CREATE INDEX idx_comp_state_expiry
  ON `tabIMM User Competency` (workflow_state, expiry_date);

CREATE INDEX idx_comp_dept_state_model
  ON `tabIMM User Competency` (department_at_assessment, workflow_state, device_model);

CREATE UNIQUE INDEX idx_alert_unique
  ON `tabIMM Competency Alert Log` (competency, alert_date, milestone);
```

---

## 11. Integration Points

### 11.1 IMM-04 ← IMM-06 (Clinical_Release gate)

```python
# Trong assetcore/.../doctype/asset_commissioning/asset_commissioning.py
def validate(self):
    # ... existing GW-2 IMM-05 ...
    if self.workflow_state == "Clinical_Release":
        from assetcore.services.imm06 import compute_operator_coverage
        coverage = compute_operator_coverage(self.asset)
        if not coverage["gate_pass"]:
            frappe.throw(_(
                "BR-06-07: Asset Class III tại {dept} cần tối thiểu {min} "
                "operator có Active competency (hiện có {count})."
            ).format(**coverage))
```

### 11.2 IMM-08/09/12 → IMM-06 (Authorization gate)

```python
# Trong assetcore/.../doctype/work_order/work_order.py (IMM-08 etc)
def validate_assignee(self):
    from assetcore.services.imm06 import validate_user_authorization
    asset = frappe.get_doc("AC Asset", self.asset)
    result = validate_user_authorization(self.assigned_to, asset.device_model)
    if not result["authorized"]:
        frappe.throw(_(
            "BR-06-01: Kỹ thuật viên {user} chưa có Active competency "
            "cho thiết bị này. Lý do: {reason}"
        ).format(user=self.assigned_to, reason=result["reason"]))
```

### 11.3 IMM-06 → IMM-05 (Certificate file)

Khi Session.complete → tạo Asset Document `doc_category="Training"`, `is_model_level=1` per program (không gắn 1 asset cụ thể), file = `qms_session_record`. Hoặc per-user: file certificate cá nhân lưu trong `competency.certificate_file` Link sang Asset Document.

### 11.4 IMM-10 → IMM-06 (CAPA → Revoke)

CAPA action item type `revoke_competency` → khi CAPA submit, hệ thống auto-call `revoke_competency` API với reason + CAPA ref. Cross-module integration tại `assetcore/services/imm10.py` (Wave 3).

---

## 12. ERD

```
┌──────────────────────────┐    ┌──────────────────────────┐
│ IMM Training Program     │ 1─*│ IMM Training Session     │
│  program_code (PK)       │    │  TRN-...          │
│  target_device_model ──┐ │    │  workflow_state          │
│  validity_period_months│ │    │  participants (Table) ─┐ │
│  passing_score_pct     │ │    └──────────────────────┬─┘ │
└────────────────────────┼─┘                           │   │
                         │                             │   │
                         ▼ Link                        ▼   │
┌──────────────────────────┐                ┌──────────────────────┐
│ IMM Device Model         │                │ IMM Training         │
│  (existing master)       │                │ Participant (child)  │
└──────────────────────────┘                │  user, scores,       │
                         ▲                  │  overall_result,     │
                         │ Link             │  competency_record ──┼─┐
                         │                  └──────────────────────┘ │
                ┌────────┴─────────────────────────────────┐         │
                │                                          ▼         │
                │              ┌──────────────────────────────┐      │
                │              │ IMM User Competency          │ ◀────┘
                │              │  COMP-...             │
                │              │  user, device_model,         │
                │              │  workflow_state, expiry_date │
                │              │  supervisor_signoff          │
                │              │  certificate_file ─┐         │
                │              └────────────────────┼─────────┘
                │                                   │
                ▼                                   ▼
        ┌────────────────┐               ┌──────────────────────┐
        │ AC Asset       │               │ Asset Document       │
        │ device_model ──┘               │ (IMM-05)             │
        │ class (II/III) │               │  doc_category=Training│
        └────────────────┘               └──────────────────────┘

        ┌────────────────────────┐         ┌──────────────────────────┐
        │ IMM Competency Alert   │         │ IMM Competency Gap Report│
        │ Log                    │         │ (auto weekly)            │
        │ (idempotent)           │         │  department × class      │
        └────────────────────────┘         └──────────────────────────┘
```

---

## 13. State Diagrams

### 13.1 Training Session

```
   ┌─────────┐
   │ Planned │ ◀── create_session
   └────┬────┘
        │ "Xác nhận" (Tổ HC-QLCL)
        ▼
  ┌───────────┐
  │ Confirmed │ ──"Hủy"──┐
  └────┬──────┘          │
       │ "Bắt đầu"       │
       ▼                 │
  ┌───────────┐          │
  │ In Progress │────────┤
  └────┬────────┘        │
       │ "Hoàn thành" + scores
       ▼                 │
  ┌────────────┐         │
  │ Completed  │  → auto_create_competency()
  └────┬───────┘         │
       │ Workshop verify │
       ▼                 │
  ┌──────────┐           ▼
  │ Verified │     ┌────────────┐
  └────┬─────┘     │ Cancelled  │ (terminal)
       │ Đóng      └────────────┘
       ▼
  ┌────────┐
  │ Closed │ (read-only)
  └────────┘
```

### 13.2 User Competency

```
                ┌────────────────────┐
                │ Pending Assessment │ ◀── auto from Session.complete (Pass)
                └────────┬───────────┘
                         │ "Sign-off" (Supervisor)
                         ▼
                    ┌────────┐
                    │ Active │ ────────────────┐
                    └───┬────┘                 │
                        │                      │
              T-90 days │                      │ "Tạm ngưng"
                        ▼                      ▼
                   ┌──────────┐          ┌───────────┐
                   │ Expiring │          │ Suspended │ ──"Khôi phục"──┐
                   └────┬─────┘          └───────────┘                │
                        │ T+0 (auto)                                  │
                        ▼                                             │
                   ┌─────────┐                                        │
                   │ Expired │ ──── "Tái chứng nhận" (new session)    │
                   └────┬────┘                                        │
                        │                                             │
                        │  "Thu hồi" (yêu cầu reason + CAPA)           │
                        ▼                                             │
                   ┌─────────┐ ◀───────────────────────────────────────┘
                   │ Revoked │  (terminal — không quay về Active được)
                   └─────────┘
```

---

## 14. Caching Strategy

`validate_user_authorization()` được gọi MỖI khi assign WO → cao tần. Sử dụng `frappe.cache`:

```python
def validate_user_authorization(user, device_model):
    cache_key = f"imm06:auth:{user}:{device_model}"
    cached = frappe.cache.get_value(cache_key)
    if cached is not None:
        return cached
    # ... compute ...
    frappe.cache.set_value(cache_key, result, expires_in_sec=300)  # 5 min TTL
    return result

def invalidate_authorization_cache(user, device_model):
    frappe.cache.delete_value(f"imm06:auth:{user}:{device_model}")
```

Cache invalidate trong `IMMUserCompetency.on_update` và scheduler `auto_expire_competency`.

---

## 15. Migration Notes

| Phase | Hành động |
|---|---|
| Pre-go-live | Thu thập dữ liệu lịch sử competency từ Excel HR/QC → import qua `bench execute` script với flag `is_backdated=1` (bypass VR-10) |
| Go-live | Chạy `bench migrate`; verify fixtures workflow + workflow_state; seed Training Programs cho top 20 device models |
| Post go-live | Chạy `generate_competency_gap_report` lần đầu để có baseline gap |

**Backfill script template:**

```python
# scripts/imm06_backfill_competency.py
import frappe, csv
def run():
    with open("competency_legacy.csv") as f:
        for row in csv.DictReader(f):
            comp = frappe.get_doc({
                "doctype": "IMM User Competency",
                "user": row["user"],
                "device_model": row["device_model"],
                "training_program": row["program_code"],
                "achieved_date": row["achieved_date"],
                "validity_months": int(row["validity_months"]),
                "competency_level": row["level"],
                "supervisor_signoff": row["supervisor"],
                "signoff_date": row["signoff_date"],
                "workflow_state": "Active",
                "is_backdated": 1,
            })
            comp.flags.ignore_validate = False
            comp.insert(ignore_permissions=True)
```

---

## 16. Testing Strategy

| Test type | Target | Coverage |
|---|---|---|
| Unit (controller + service) | 12 VR + 6 service methods | ≥ 90% |
| API | 19 endpoints (success + error paths) | 100% endpoints |
| Workflow | Session 6 transitions + Competency 7 transitions | 100% |
| Scheduler | 4 jobs idempotent | Manual run + assertion |
| Integration | IMM-04 gate, IMM-08 WO assign block, IMM-10 CAPA→revoke | UAT script |
| Performance | `validate_user_authorization` 1000 calls/min | P95 < 200ms |

Test files (TBD): `assetcore/assetcore/doctype/imm_user_competency/test_imm_user_competency.py`, `assetcore/services/test_imm06.py`.
