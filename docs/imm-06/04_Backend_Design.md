# 04 — Backend Design — IMM-06 Đào tạo & Quản lý năng lực

| Mục | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phiên bản tài liệu | 0.1.0 |
| Ngày cập nhật | 2026-05-08 |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |

> ⚠️ Pending implementation — Wave 2. Tài liệu này là thiết kế spec, chưa có code thực tế.

---

## §I DocType Catalog

| DocType | Autoname | track_changes | is_submittable | Mục đích |
|---|---|---|:---:|:---:|
| IMM Training Program | `field:program_code` | 1 | 0 | Master curriculum — định nghĩa chương trình đào tạo cho 1 Device Model / Category |
| IMM Training Session | `TRN-.YYYY.-.#####` | 1 | 0 | Sự kiện đào tạo thực tế — delivered training event |
| IMM Training Participant | `hash` (child) | 0 | — | Child table của Session — học viên, điểm, kết quả |
| IMM User Competency | `COMP-.YYYY.-.#####` | 1 | 0 | Hồ sơ năng lực 1 user × 1 device model |
| IMM Competency Gap Report | `GAP-.YYYY.-.#####` | 0 | 0 | Báo cáo auto-generated weekly — gap analysis |
| IMM Competency Alert Log | `hash` (auto) | 0 | 0 | Log idempotent scheduler — tránh tạo trùng alert |

---

## §II DocType Schemas

### §II.1 IMM Training Program

**Config:**

| Property | Value |
|---|---|
| module | AssetCore |
| autoname | `field:program_code` |
| naming_rule | By fieldname |
| is_submittable | 0 |
| track_changes | 1 |
| title_field | `program_name` |
| sort_field | `modified` |
| search_fields | `program_code,program_name,target_device_model` |

**Fields:**

| # | fieldname | fieldtype | label | options / note | reqd | in_list_view |
|---|---|---|---|---|:---:|:---:|
| 1 | program_code | Data | Mã chương trình | unique=1 | * | 1 |
| 2 | program_name | Data | Tên chương trình | — | * | 1 |
| 3 | description | Text | Mô tả | — | — | — |
| 4 | target_device_model | Link | Device Model | IMM Device Model | — | 1 |
| 5 | target_device_category | Link | Device Category | AC Asset Category | — | — |
| 6 | is_mandatory_for_operation | Check | Bắt buộc trước vận hành | — | — | — |
| 7 | training_type | Select | Loại đào tạo | Initial / Refresher / Advanced / Certification | * | 1 |
| 8 | content_outline | Text Editor | Nội dung chương trình | — | * | — |
| 9 | duration_hours | Float | Thời lượng (giờ) | default=8 | * | — |
| 10 | validity_period_months | Int | Hiệu lực (tháng) | default=24 | * | — |
| 11 | requires_recertification | Check | Yêu cầu tái chứng nhận | default=1 | — | — |
| 12 | assessment_method | Select | Phương pháp đánh giá | Theory / Practical / Both | * | — |
| 13 | passing_score_pct | Float | Điểm đạt (%) | default=70 | * | — |
| 14 | instructor_qualification_required | Data | Y/c giảng viên | — | — | — |
| 15 | qms_doc_ref | Link | QMS Doc Ref | Asset Document | — | — |
| 16 | is_active | Check | Đang hoạt động | default=1 | — | 1 |

> Tối thiểu 1 trong (`target_device_model`, `target_device_category`) phải set — VR enforce tại validate().

**Permissions:**

| Role | read | write | create | delete |
|---|:---:|:---:|:---:|:---:|
| IMM Training Officer | 1 | 1 | 1 | — |
| IMM Workshop Lead | 1 | — | — | — |
| IMM Biomed Technician | 1 | — | — | — |
| HTM Technician | 1 | — | — | — |
| IMM System Admin | 1 | 1 | 1 | 1 |
| Clinical Head | 1 | — | — | — |
| Department Manager | 1 | — | — | — |

---

### §II.2 IMM Training Session

**Config:**

| Property | Value |
|---|---|
| autoname | `TRN-.YYYY.-.#####` |
| is_submittable | 0 |
| track_changes | 1 |
| title_field | `training_program` |
| sort_field | `session_date` DESC |
| search_fields | `training_program,instructor,location` |

**Fields:**

| # | fieldname | fieldtype | label | options | reqd | read_only |
|---|---|---|---|---|:---:|:---:|
| 1 | workflow_state | Link | Trạng thái | Workflow State | — | 1 |
| 2 | training_program | Link | Chương trình | IMM Training Program | * | — |
| 3 | session_date | Date | Ngày tổ chức | — | * | — |
| 4 | session_type | Select | Hình thức | Onsite / Online / Hybrid | * | — |
| 5 | location | Data | Địa điểm | — | — | — |
| 6 | instructor | Link | Giảng viên nội bộ | User | — | — |
| 7 | instructor_external_name | Data | Tên giảng viên bên ngoài | — | — | — |
| 8 | instructor_external_org | Data | Tổ chức | — | — | — |
| 9 | duration_planned_hours | Float | Thời lượng dự kiến (giờ) | — | * | — |
| 10 | duration_actual_hours | Float | Thời lượng thực tế (giờ) | — | — | — |
| 11 | training_materials | Attach | Tài liệu đào tạo | — | — | — |
| 12 | qms_session_record | Attach | Biên bản buổi học | — | — | — |
| 13 | evaluation_method | Small Text | Phương pháp đánh giá | — | — | — |
| 14 | status_remarks | Small Text | Ghi chú | — | — | — |
| 15 | participants | Table | Học viên | IMM Training Participant | — | — |

> Tối thiểu 1 trong (`instructor`, `instructor_external_name`) reqd — VR enforce.

**Permissions:**

| Role | read | write | create | submit | cancel |
|---|:---:|:---:|:---:|:---:|:---:|
| IMM Training Officer | 1 | 1 | 1 | 1 | 1 |
| IMM Workshop Lead | 1 | 1 | — | 1 | — |
| IMM Biomed Technician | 1 | 1 | 1 | — | — |
| HTM Technician | 1 | 1 | — | — | — |
| IMM System Admin | 1 | 1 | 1 | 1 | 1 |

---

### §II.3 IMM Training Participant (Child Table)

**Config:**

| Property | Value |
|---|---|
| istable | 1 |
| autoname | `hash` |

**Fields:**

| # | fieldname | fieldtype | label | options | reqd | in_list_view |
|---|---|---|---|---|:---:|:---:|
| 1 | user | Link | Học viên | User | * | 1 |
| 2 | department | Link | Khoa/Phòng | AC Department | — | 1 |
| 3 | role_at_session | Data | Vai trò | — | — | — |
| 4 | attendance_pct | Float | Tỷ lệ tham dự (%) | 0-100 | — | 1 |
| 5 | theory_score | Float | Điểm lý thuyết | 0-100 | — | 1 |
| 6 | practical_score | Float | Điểm thực hành | 0-100 | — | 1 |
| 7 | overall_result | Select | Kết quả | Pass / Fail / Conditional | — | 1 |
| 8 | certificate_issued | Check | Đã cấp chứng nhận | — | — | — |
| 9 | retake_required | Check | Cần học lại | — | — | — |
| 10 | competency_record | Link | Hồ sơ năng lực | IMM User Competency | — | — |
| 11 | remarks | Small Text | Ghi chú | — | — | — |

---

### §II.4 IMM User Competency

**Config:**

| Property | Value |
|---|---|
| autoname | `COMP-.YYYY.-.#####` |
| is_submittable | 0 |
| track_changes | 1 |
| title_field | `user` |
| sort_field | `expiry_date` ASC |
| search_fields | `user,device_model,training_program` |

**Fields:**

| # | fieldname | fieldtype | label | options | reqd | read_only |
|---|---|---|---|---|:---:|:---:|
| 1 | workflow_state | Link | Trạng thái | Workflow State | — | 1 |
| 2 | user | Link | Nhân viên | User | * | — |
| 3 | device_model | Link | Device Model | IMM Device Model | * | — |
| 4 | training_program | Link | Chương trình | IMM Training Program | * | — |
| 5 | training_session | Link | Buổi đào tạo | IMM Training Session | — | 1 |
| 6 | department_at_assessment | Link | Khoa tại thời điểm đánh giá | AC Department | — | 1 |
| 7 | competency_level | Select | Cấp độ năng lực | Trainee / Operator / Senior Operator / Trainer | * | — |
| 8 | achieved_date | Date | Ngày đạt | — | * | — |
| 9 | validity_months | Int | Hiệu lực (tháng) | default=24 | — | — |
| 10 | expiry_date | Date | Ngày hết hạn | computed | — | 1 |
| 11 | recertification_due_date | Date | Ngày cần tái chứng nhận | computed = expiry - 60d | — | 1 |
| 12 | last_assessment_score | Float | Điểm tổng hợp | — | — | 1 |
| 13 | theory_score | Float | Điểm lý thuyết | — | — | 1 |
| 14 | practical_score | Float | Điểm thực hành | — | — | 1 |
| 15 | supervisor_signoff | Link | Người phê duyệt | User | — | 1 |
| 16 | signoff_date | Date | Ngày phê duyệt | — | — | 1 |
| 17 | certificate_file | Link | File chứng nhận | Asset Document | — | — |
| 18 | revoke_reason | Small Text | Lý do thu hồi | — | — | — |
| 19 | revoke_capa_ref | Link | CAPA reference | CAPA | — | — |
| 20 | revoked_by | Link | Thu hồi bởi | User | — | 1 |
| 21 | revoked_date | Datetime | Ngày thu hồi | — | — | 1 |
| 22 | suspended_until | Date | Tạm ngưng đến | — | — | — |
| 23 | days_until_expiry | Int | Còn lại (ngày) | computed | — | 1 |
| 24 | is_expired | Check | Đã hết hạn | computed | — | 1 |

**Permissions:**

| Role | read | write | create | delete |
|---|:---:|:---:|:---:|:---:|
| IMM Training Officer | 1 | 1 | 1 | — |
| IMM Workshop Lead | 1 | 1 | 1 | — |
| Department Manager | 1 | 1 (own dept) | — | — |
| Clinical Head | 1 (own dept) | — | — | — |
| IMM Biomed Technician | 1 | — | — | — |
| Operator (self via filter) | 1 (own) | — | — | — |
| IMM System Admin | 1 | 1 | 1 | 1 |

---

### §II.5 IMM Competency Gap Report

**Config:**

| Property | Value |
|---|---|
| autoname | `GAP-.YYYY.-.#####` |
| is_submittable | 0 |
| track_changes | 0 |

**Fields:**

| # | fieldname | fieldtype | label | options |
|---|---|---|---|---|
| 1 | report_date | Date | Ngày báo cáo | default=today, read_only |
| 2 | scope | Select | Phạm vi | Hospital-wide / Department / Device Class |
| 3 | scope_filter_value | Data | Giá trị lọc | — |
| 4 | total_assets_class3 | Int | Tổng assets Class III | — |
| 5 | assets_with_gap_count | Int | Số assets có gap | — |
| 6 | gap_details | Long Text | Chi tiết gap (JSON) | — |
| 7 | summary_table | Table | Bảng tóm tắt | IMM Gap Detail Row (child) |

`IMM Gap Detail Row` (child): `department`, `device_class`, `total_assets`, `total_competent_users`, `required_min`, `gap_count`, `missing_users`.

---

### §II.6 IMM Competency Alert Log

**Config:**

| Property | Value |
|---|---|
| autoname | `hash` |
| is_submittable | 0 |
| track_changes | 0 |

**Fields:**

| # | fieldname | fieldtype | label | options |
|---|---|---|---|---|
| 1 | competency | Link | Competency | IMM User Competency |
| 2 | alert_date | Date | Ngày alert | — |
| 3 | milestone | Select | Mốc (ngày) | 90 / 60 / 30 / 0 |
| 4 | alert_level | Select | Mức độ | Info / Warning / Critical / Danger |
| 5 | sent_to | Small Text | Gửi đến (JSON) | — |

**Unique constraint:** `(competency, alert_date, milestone)` — đảm bảo idempotent, scheduler không tạo trùng.

---

## §III Custom Fields (cross-module)

| DocType | fieldname | fieldtype | Lý do |
|---|---|---|---|
| User | `competency_summary_html` | Text Editor (read_only) | Render HTML hiển thị competency tóm tắt trên User profile |
| AC Asset | `custom_operator_coverage_count` | Int (computed daily) | Cache kết quả `compute_operator_coverage` để dashboard nhanh |
| AC Asset | `custom_operator_coverage_status` | Select (OK / Insufficient) | Cache trạng thái cho IMM-04 Clinical Release gate |

> Cache được scheduler refresh mỗi đêm (`check_competency_expiry`) HOẶC invalidate khi competency thay đổi (`IMMUserCompetency.on_update` hook). Tránh tính on-the-fly cho gate cao tần.

---

## §IV Service Layer (`assetcore/services/imm06.py`)

> ⚠️ Pending implementation — file chưa tồn tại. Build mới hoàn toàn (không lặp tech-debt IMM-05).

```python
# assetcore/services/imm06.py
# ⚠️ Pending implementation — Wave 2

from assetcore.utils.errors import ServiceError, ErrorCode


def create_competency_from_session(session_name: str) -> list[str]:
    """
    Khi Session chuyển sang Completed: tự động tạo IMM User Competency
    cho mọi participant có overall_result='Pass'.

    Args:
        session_name: Tên IMM Training Session đã Completed.

    Returns:
        List[str]: Danh sách tên competency vừa tạo (COMP-YYYY-#####).

    Side effects:
        - Insert IMM User Competency per Pass participant
        - achieved_date = session.session_date
        - expiry_date = achieved_date + program.validity_period_months months
        - recertification_due_date = expiry_date - 60 days
        - workflow_state = 'Pending Assessment'

    Raises:
        ServiceError(ErrorCode.NOT_FOUND): nếu session không tồn tại.
        ServiceError(ErrorCode.VALIDATION): nếu session chưa Completed.
    """


def signoff_competency(competency_name: str, supervisor_user: str) -> dict:
    """
    Supervisor ký duyệt competency: Pending Assessment → Active.

    Args:
        competency_name: Tên IMM User Competency.
        supervisor_user: Email supervisor thực hiện sign-off.

    Returns:
        dict: {name, new_state, expiry_date, recertification_due_date}.

    Side effects:
        - Set supervisor_signoff = supervisor_user, signoff_date = today
        - Compute expiry_date = achieved_date + validity_months
        - Compute recertification_due_date = expiry_date - 60d
        - workflow_state = 'Active'
        - Gọi archive_old_competency(user, device_model, exclude=name) — BR-06-11
        - invalidate_authorization_cache(user, device_model)
        - Log IMM Audit Trail action='SIGNOFF'
        - Gửi email cho user

    Raises:
        ServiceError(ErrorCode.VALIDATION): VR-07 — thiếu supervisor_signoff.
        ServiceError(ErrorCode.BUSINESS_RULE): workflow_state != 'Pending Assessment'.
        ServiceError(ErrorCode.FORBIDDEN): supervisor scope check fail.
    """


def archive_old_competency(user: str, device_model: str, exclude: str) -> int:
    """
    BR-06-11: Khi competency mới Active, tìm các competency cùng
    (user × device_model) đang Active ngoại trừ self → set status='Suspended'.

    Args:
        user: Email người dùng.
        device_model: Tên IMM Device Model.
        exclude: Tên competency vừa Active (không archive).

    Returns:
        int: Số competency đã archive.
    """


def compute_operator_coverage(asset: str) -> dict:
    """
    Tính số operator có Active competency cho asset tại khoa tương ứng.
    Dùng cho IMM-04 Clinical Release gate (BR-06-07).

    Args:
        asset: Tên AC Asset.

    Returns:
        dict: {
            asset, device_model, department,
            operator_count: int,
            operator_users: list[str],
            required_min: int,  # 2 nếu Class III, 1 nếu Class II
            gate_pass: bool,
            asset_class: str
        }

    Raises:
        ServiceError(ErrorCode.NOT_FOUND): nếu asset không tồn tại.
    """


def validate_user_authorization(user: str, device_model: str) -> dict:
    """
    Hook cao tần — được gọi từ IMM-08/09/11/12 trước khi assign WO.
    Cached 5 min TTL qua frappe.cache để đạt NFR-06-02 (P95 < 200ms).

    Args:
        user: Email người dùng cần validate.
        device_model: Tên IMM Device Model của asset trong WO.

    Returns:
        dict: {
            authorized: bool,
            competency: str | None,
            competency_level: str | None,
            status: str,
            expiry_date: str | None,
            days_until_expiry: int | None,
            reason: str | None
        }

    Note:
        - Cache key: f"imm06:auth:{user}:{device_model}"
        - Cache invalidate tại: IMMUserCompetency.on_update + auto_expire_competency scheduler
    """


def trigger_recertification(competency_name: str) -> str | None:
    """
    Tạo placeholder Refresher Training Session và thêm user vào participants.
    Được gọi bởi scheduler check_recertification_due (T-60d).

    Args:
        competency_name: Tên IMM User Competency sắp hết hạn.

    Returns:
        str: session_name nếu tạo mới.
        None: nếu đã có Refresher Session Planned cho program/user trong 60d.

    Side effects:
        - Insert IMM Training Session {workflow_state='Planned', session_type='Refresher'}
        - Add user vào participants
    """


def generate_gap_report(scope: str = "Hospital-wide") -> str:
    """
    Weekly job: tính ma trận coverage (department × device_class).
    Tạo IMM Competency Gap Report record.

    Args:
        scope: "Hospital-wide" | "Department" | "Device Class".

    Returns:
        str: Tên GAP report vừa tạo (GAP-YYYY-#####).

    Side effects:
        - Insert IMM Competency Gap Report
        - Gửi email Workshop Head + VP Block2 với link report

    Raises:
        ServiceError(ErrorCode.INTERNAL): nếu tính toán fail.
    """


def invalidate_authorization_cache(user: str, device_model: str) -> None:
    """
    Xóa cache validate_user_authorization cho (user, device_model).
    Gọi khi: on_update Competency, auto_expire_competency, signoff_competency, revoke_competency.
    """
```

---

## §V Controller Hooks (lifecycle)

> ⚠️ Pending implementation

```python
# assetcore/assetcore/doctype/imm_user_competency/imm_user_competency.py

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
            log_audit_trail(self, action="STATUS_CHANGE", metadata={
                "from": self.get_doc_before_save().workflow_state,
                "to": self.workflow_state
            })

    def on_trash(self):
        frappe.throw(frappe._("BR-06-09: Không được phép xóa Competency. "
                               "Vui lòng dùng Suspend hoặc Revoke."))


# assetcore/assetcore/doctype/imm_training_session/imm_training_session.py

class IMMTrainingSession(Document):
    def validate(self):
        self.vr_04_instructor_qualified()
        self.vr_05_min_participants_for_confirm()
        self.vr_10_session_date_not_past()

    def before_save(self):
        if self.workflow_state == "Completed":
            self.vr_06_scores_required_complete()
            self.compute_overall_results()  # Pass/Fail/Conditional per participant

    def on_update(self):
        if self.has_value_changed("workflow_state") and self.workflow_state == "Completed":
            from assetcore.services.imm06 import create_competency_from_session
            new_competencies = create_competency_from_session(self.name)
            self.notify_supervisors_for_signoff(new_competencies)


# assetcore/assetcore/doctype/imm_training_program/imm_training_program.py

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
            self.flag_recertification_needed()  # tạo Document Request task
```

---

## §VI Workflows

### §VI.1 Workflow — IMM Training Session (7 states)

**File:** `assetcore/assetcore/workflow/imm_06_session_workflow.json`

| State | State Type | Allow Edit Roles |
|---|---|---|
| Planned | Default | IMM Training Officer, IMM Workshop Lead |
| Confirmed | Warning | IMM Training Officer |
| In Progress | Warning | IMM Biomed Technician (instructor), IMM Training Officer |
| Completed | Success | IMM Training Officer, IMM Workshop Lead |
| Verified | Success | IMM Workshop Lead |
| Closed | Default | (read-only) |
| Cancelled | Danger | (terminal) |

**Transition Table:**

| Action | From | To | Allowed Roles |
|---|---|---|---|
| Xác nhận | Planned | Confirmed | IMM Training Officer, IMM System Admin |
| Bắt đầu | Confirmed | In Progress | IMM Training Officer, IMM Biomed Technician |
| Hoàn thành | In Progress | Completed | IMM Training Officer, IMM Biomed Technician |
| Verify | Completed | Verified | IMM Workshop Lead, IMM System Admin |
| Đóng | Verified | Closed | IMM Workshop Lead, IMM System Admin |
| Hủy | Planned, Confirmed | Cancelled | IMM Training Officer, IMM System Admin |

> BR-06-12: Không thể Hủy từ Verified hoặc Closed.

---

### §VI.2 Workflow — IMM User Competency (6 states)

**File:** `assetcore/assetcore/workflow/imm_06_competency_workflow.json`

| State | State Type | Trigger |
|---|---|---|
| Pending Assessment | Warning | Auto-tạo từ Session.complete khi participant Pass |
| Active | Success | Supervisor sign-off |
| Expiring | Warning | Scheduler `check_competency_expiry` khi ≤90 ngày trước expiry |
| Expired | Danger | Scheduler `auto_expire_competency` khi `expiry_date < today` |
| Suspended | Warning | Manual (tạm ngưng — không thu hồi vĩnh viễn) |
| Revoked | Danger | Manual với reason + CAPA — terminal state |

**Transition Table:**

| Action | From | To | Allowed Roles |
|---|---|---|---|
| Sign-off | Pending Assessment | Active | Department Manager, IMM Workshop Lead, IMM Training Officer |
| (auto) | Active | Expiring | Scheduler `check_competency_expiry` |
| (auto) | Active, Expiring | Expired | Scheduler `auto_expire_competency` |
| Tạm ngưng | Active | Suspended | IMM Workshop Lead, IMM Training Officer |
| Khôi phục | Suspended | Active | IMM Workshop Lead, IMM Training Officer |
| Thu hồi | * (≠ Revoked) | Revoked | IMM Training Officer, IMM System Admin |
| Tái chứng nhận | Expired | Active | Service `trigger_recertification` (sau new session Pass + sign-off) |

---

## §VII Schedulers (`assetcore/tasks.py`)

> ⚠️ Pending implementation — 4 jobs cần thêm vào `tasks.py`.

### Job 1: `check_competency_expiry()` — Daily 02:00

**Mục đích:** Quét Active competency tại mốc 90/60/30 ngày trước `expiry_date` → set Expiring, gửi email, idempotent qua Alert Log.

**Email targets:** User (mọi mốc), Department Manager (mọi mốc), IMM Workshop Lead (60d+30d).

**Pseudocode:**

```
For each milestone IN (90, 60, 30):
    target_date = today + milestone days
    competencies = frappe.get_all("IMM User Competency",
        filters={"workflow_state": "Active", "expiry_date": target_date})
    For each comp:
        If Alert Log exists (comp.name, today, milestone): skip (idempotent)
        Else:
            Insert IMM Competency Alert Log
            Set comp.workflow_state = "Expiring"
            Send email (level: 90=Info, 60=Warning, 30=Critical)
            If milestone == 60: trigger_recertification(comp.name) if no Refresher Planned
```

### Job 2: `auto_expire_competency()` — Daily 02:30

**Mục đích:** Tự động set Expired cho competency quá hạn. Vô hiệu hóa quyền vận hành (via cache invalidate).

**Email targets:** User, IMM Workshop Lead.

**Pseudocode:**

```
expired_comps = frappe.get_all("IMM User Competency",
    filters={"workflow_state": ["in", ["Active", "Expiring"]],
             "expiry_date": ["<", today]})
For each comp:
    comp.workflow_state = "Expired"
    log_audit_trail(comp, action="AUTO_EXPIRE")
    invalidate_authorization_cache(comp.user, comp.device_model)
    Send email "Năng lực đã hết hạn" → User, IMM Workshop Lead
```

### Job 3: `check_recertification_due()` — Daily 03:00

**Mục đích:** Tạo placeholder Refresher Session 60 ngày trước `recertification_due_date` + gửi digest cho Tổ HC-QLCL.

**Email targets:** IMM Training Officer (digest), IMM Workshop Lead (digest).

**Pseudocode:**

```
due_comps = frappe.get_all("IMM User Competency",
    filters={"workflow_state": "Active",
             "recertification_due_date": ["<=", add_days(today, 60)]})
created = []
For each comp:
    session = trigger_recertification(comp.name)  # returns None nếu đã có
    if session: created.append(session)
Send digest email Tổ HC-QLCL:
    "{len(due_comps)} người cần tái chứng nhận trong 60 ngày. {len(created)} phiên mới tạo."
```

### Job 4: `generate_competency_gap_report()` — Weekly Monday 02:00

**Mục đích:** Tính coverage operator per (department × device_class) → tạo Gap Report + email.

**Email targets:** IMM Workshop Lead, VP Block2.

**Pseudocode:**

```
report_name = generate_gap_report(scope="Hospital-wide")
Send email IMM Workshop Lead + VP Block2:
    "Gap Report tuần này: {report_name}. [Link xem báo cáo]"
```

---

## §VIII Hooks.py Registration

> ⚠️ Pending implementation — thêm vào `assetcore/hooks.py`

```python
# assetcore/hooks.py — các entries cần thêm cho IMM-06

scheduler_events = {
    "daily": [
        # ... existing IMM-05 entries ...
        # IMM-06 — thêm mới
        "assetcore.tasks.check_competency_expiry",
        "assetcore.tasks.auto_expire_competency",
        "assetcore.tasks.check_recertification_due",
    ],
    "cron": {
        # IMM-06: weekly Monday 02:00 VN time
        "0 2 * * 1": [
            "assetcore.tasks.generate_competency_gap_report",
        ],
    },
}

doc_events = {
    # ... existing entries ...
    "User": {
        "on_update": "assetcore.services.imm06.handle_user_dept_change",
    },
}

fixtures = [
    # ... existing fixtures ...
    {"dt": "Workflow", "filters": [["name", "in",
        ["IMM-06 Session Workflow", "IMM-06 Competency Workflow"]]]},
    {"dt": "Workflow State", "filters": [["name", "in",
        ["Planned", "Confirmed", "In Progress", "Completed", "Verified", "Closed",
         "Cancelled", "Pending Assessment", "Active", "Expiring", "Expired",
         "Suspended", "Revoked"]]]},
]
```

---

## §IX Database Indexes

| Table | Column(s) | Type | Lý do |
|---|---|---|---|
| tabIMM User Competency | `user` | Single | `get_user_competencies` self-service |
| tabIMM User Competency | `device_model` | Single | `check_user_authorization` |
| tabIMM User Competency | `workflow_state` | Single | Scheduler queries |
| tabIMM User Competency | `expiry_date` | Single | `check_competency_expiry`, dashboard |
| tabIMM User Competency | `department_at_assessment` | Single | Gap report, coverage query |
| tabIMM User Competency | `(user, device_model, workflow_state)` | Composite | Auth gate — primary hot path |
| tabIMM User Competency | `(workflow_state, expiry_date)` | Composite | Scheduler daily expiry scan |
| tabIMM User Competency | `(department_at_assessment, workflow_state, device_model)` | Composite | Gap report coverage calculation |
| tabIMM Training Session | `training_program` | Single | Session list by program |
| tabIMM Training Session | `session_date` | Single | Scheduler recert reminders |
| tabIMM Competency Alert Log | `(competency, alert_date, milestone)` | UNIQUE | Idempotent constraint |

**SQL DDL:**

```sql
-- ⚠️ Pending implementation — chạy qua bench migrate sau khi DocType scaffold

CREATE INDEX idx_comp_user_model_state
  ON `tabIMM User Competency` (user, device_model, workflow_state);

CREATE INDEX idx_comp_state_expiry
  ON `tabIMM User Competency` (workflow_state, expiry_date);

CREATE INDEX idx_comp_dept_state_model
  ON `tabIMM User Competency` (department_at_assessment, workflow_state, device_model);

CREATE UNIQUE INDEX idx_alert_unique
  ON `tabIMM Competency Alert Log` (competency, alert_date, milestone);
```
