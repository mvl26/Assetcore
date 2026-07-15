# 04 — Backend Design — IMM-06 Đào tạo & Quản lý năng lực

| Mục | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phiên bản tài liệu | 0.1.0 |
| Ngày cập nhật | 2026-05-08 |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |

> ✅ Implemented (Wave 2). Code ground truth: `assetcore/services/imm06.py`, `assetcore/api/imm06.py`, workflow fixtures `imm_06_session_workflow.json` + `imm_06_competency_workflow.json`, DocTypes `imm_training_program/session/participant` + `IMM User Competency`.

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
| 6 | trainer_ref | Link | Giảng viên (registry) | IMM Trainer | — | — |
| 7 | instructor | Link | Giảng viên nội bộ (User) | User | — | — |
| 8 | instructor_external_name | Data | Tên giảng viên bên ngoài | — | — | — |
| 9 | instructor_external_org | Data | Tổ chức | — | — | — |
| 10 | duration_planned_hours | Float | Thời lượng dự kiến (giờ) | — | * | — |
| 11 | duration_actual_hours | Float | Thời lượng thực tế (giờ) | — | — | — |
| 12 | training_materials | Attach | Tài liệu đào tạo | — | — | — |
| 13 | qms_session_record | Attach | Biên bản buổi học | — | — | — |
| 14 | evaluation_method | Small Text | Phương pháp đánh giá | — | — | — |
| 15 | status_remarks | Small Text | Ghi chú | — | — | — |
| 16 | participants | Table | Học viên | IMM Training Participant | — | — |

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
| 10 | result | Select | Kết quả (display) | Đạt / Không đạt | — | 1 |
| 11 | competency_record | Link | Competency Record | IMM User Competency | — | — |
| 12 | remarks | Small Text | Ghi chú | — | — | — |
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
| 11 | recertification_due_date | Date | Ngày cần tái chứng nhận | computed = SoT `compute_competency_dates()` — INVARIANT: expiry − 60d (xem §V.1) | — | 1 |
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

> ✅ Implemented — `assetcore/services/imm06.py` (1533 LOC, 2026-05-18). Snippets bên dưới thể hiện contract key.

**Catalog đầy đủ public functions (tóm tắt):**

| Group | Function | Mô tả |
|---|---|---|
| Program | `list_training_programs`, `get_training_program`, `create_training_program`, `update_training_program`, `list_programs`, `get_program`, `create_program`, `update_program` | CRUD chương trình đào tạo |
| Session | `list_training_sessions`, `create_training_session`, `start_training_session`, `complete_training_session` | Core session lifecycle |
| Session API | `list_sessions`, `get_session`, `create_session`, `confirm_session`, `enroll_participants`, `remove_participant`, `complete_session`, `cancel_session`, `verify_session`, `close_session` | API wrappers + participant management |
| Competency | `list_user_competencies`, `get_user_competencies`, `signoff_competency_by_name`, `revoke_competency_with_capa`, `recertify_competency`, `suspend_competency` (Vòng 26), `restore_competency` (Vòng 26), `create_competency_from_session`, `archive_old_competency` | Competency lifecycle |
| Gates | `validate_user_authorized_for_asset`, `get_asset_operator_coverage` | Cross-module gates (IMM-04, IMM-08/09/11/12) |
| Analytics | `get_dashboard_stats`, `get_competency_gaps_by_dept`, `get_expiring_competencies`, `generate_gap_report` | Dashboard + reports |
| Validators | `validate_target_device_set`, `validate_passing_score_range`, `validate_validity_range`, `validate_instructor_present`, `validate_min_participants_for_confirm`, `compute_overall_results`, `set_computed_competency_fields` | VR enforcement |
| Scheduler | `check_expiring_competencies`, `auto_expire_competencies`, `check_recertification_due`, `generate_weekly_gap_report`, `handle_user_dept_change` | Auto-jobs |
| Utilities | `invalidate_authorization_cache`, `_create_competency_record` (private) | Helpers |

```python
# assetcore/services/imm06.py

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
        - expiry_date, recertification_due_date = compute_competency_dates(
              achieved_date, validity_months)  # SoT §V.1 — INVARIANT expiry−60d
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
        - Recompute (nếu thiếu) qua compute_competency_dates(achieved_date,
              validity_months) — SoT §V.1, INVARIANT expiry−60d
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

## §V.1 SoT — Pure helper tính ngày năng lực (BR-06-13)

> **Self-Correction 2026-06-03 (Vòng 22):** Trước đây `recertification_due_date` được tính bằng **2 công thức khác nhau** rải rác 6 nơi → cùng một record nhận giá trị lệch 1–2 ngày tùy code path (creation/signoff vs recertify). Đây là lỗi thiết kế gốc (Core Doc không chốt 1 quy ước). Nay chốt **DUY NHẤT 1 SoT**.

**INVARIANT (quy ước duy nhất, không đổi):**

```
recertification_due_date = expiry_date − 60 ngày
expiry_date              = achieved_date + validity_months tháng
```

**Vì sao chọn "expiry − 60 ngày"** (không phải "achieved + (validity − 2) tháng"):
- Khớp filter của scheduler `check_recertification_due`: `add_days(nowdate(), 60)` — lead time đo bằng **ngày**, không phải tháng.
- Khớp docstring scheduler (`services/imm06.py:1477`) và mốc reminder T−90/−60/−30 đo bằng ngày.
- "60 ngày" là hằng số cố định; "validity − 2 tháng" trôi 0–2 ngày theo độ dài tháng (28/30/31) → nguồn gốc divergence.

**Hàm SoT** (đặt tại `assetcore/services/imm06.py`, type-hinted + docstring, ghi rõ INVARIANT):

```python
RECERT_LEAD_DAYS = 60  # INVARIANT — lead time tái chứng nhận, đo bằng ngày

def compute_competency_dates(achieved_date, validity_months: int) -> dict:
    """SoT DUY NHẤT cho expiry_date + recertification_due_date.

    INVARIANT: recertification_due_date = expiry_date − RECERT_LEAD_DAYS (60 ngày).
    Mọi write-site (creation, signoff recompute, controller before_save,
    recertify_from_session, set_computed_competency_fields, compute_expiry_dates)
    PHẢI gọi hàm này — KHÔNG inline add_days(expiry,-60) hay add_months(achieved, validity-2).

    Returns: {"expiry_date": <date>, "recertification_due_date": <date>}
    """
    expiry = add_months(achieved_date, int(validity_months))
    return {
        "expiry_date": expiry,
        "recertification_due_date": add_days(expiry, -RECERT_LEAD_DAYS),
    }
```

**6 write-site phải gọi SoT** (sau refactor không còn literal formula nào ngoài SoT):

| # | Site (file:line cũ) | Formula cũ | Hành động |
|---|---|---|---|
| 1 | `services/imm06.py:217` `_create_competency_record` | A: `add_days(expiry,-60)` | gọi `compute_competency_dates()` |
| 2 | `services/imm06.py:315` signoff recompute | A: `add_days(expiry,-60)` | gọi `compute_competency_dates()` |
| 3 | `imm_user_competency.py:24` `before_save` | A: `add_days(expiry,-60)` | gọi `compute_competency_dates()` |
| 4 | `services/imm06.py:712` `set_computed_competency_fields` | B: `add_months(achieved, validity-2)` | gọi `compute_competency_dates()` |
| 5 | `services/imm06.py:727` `compute_expiry_dates` | B: `add_months(achieved, validity-2)` | gọi `compute_competency_dates()` |
| 6 | `services/imm06.py:1320` `recertify_from_session` | B: `add_months(achieved, validity-2)` | gọi `compute_competency_dates()` |

**Idempotency:** save lặp lại không đổi giá trị khi `achieved_date`/`validity_months` không đổi (cùng input → cùng output). Controller `before_save` và service compute hook KHÔNG ghi 2 giá trị khác nhau cho cùng record.

**Grep guard (acceptance):** `0` occurrence của `add_days(<expiry>, -60)` và `add_months(<achieved>, <validity>-2)` cho field `recertification_due_date` ngoài thân hàm SoT.

> **Lưu ý dead-code:** `set_computed_competency_fields` (#4) và `compute_expiry_dates` (#5) hiện **chưa wire** vào `hooks.py::doc_events` hay controller (live save-path là `before_save` #3). Vẫn refactor để đồng bộ + tránh tái phát nếu sau này wire. Nếu BE muốn xóa dead-code thay vì refactor → ghi chú delta + giữ ≥1 hàm public ổn định.

---

## §V.2 SoT — Predicate LIVE "Sắp hết hạn / Đã hết hạn" (BR-06-14)

> **Self-Correction 2026-06-04 (Vòng 20):** lỗi thiết kế gốc — **count-vs-drill divergence**. `get_dashboard_stats` đếm KPI "Sắp hết hạn"/"Đã hết hạn" bằng `frappe.db.count(workflow_state==Expiring/Expired)` (cờ thuần), nhưng drill `get_expiring_competencies` lọc LIVE theo `expiry_date`. Scheduler chỉ stamp `workflow_state=Expiring` đúng mốc 60/30 ngày và `Expired` khi quá hạn (và có thể lỡ phiên) → cờ workflow_state KHÔNG phản ánh đúng thực-tại date-derived → **tile lệch list**, che năng lực hết hạn còn gắn cờ `Active`. Nay chốt **DUY NHẤT 1 predicate LIVE** dùng chung cho KPI count lẫn drill.

**INVARIANT (predicate duy nhất, date-derived, đo bằng `today` runtime):**

```
EXPIRY_WINDOW_DAYS = 60   # KHỚP default get_expiring_competencies(days=60)

expiring(c) ⟺ c.workflow_state ∈ {Active, Expiring}
            ∧ c.expiry_date ∈ [today, today + EXPIRY_WINDOW_DAYS]      # window đóng 2 đầu

expired(c)  ⟺ c.workflow_state ∈ {Active, Expiring, Expired}
            ∧ c.expiry_date < today                                    # quá hạn, gồm cả late-scheduler
```

- **Revoked / Suspended LOẠI hoàn toàn** (terminal/tạm-ngưng — không bao giờ đếm vào expiring/expired).
- `expired` gồm cả `workflow_state=Active` (scheduler `auto_expire_competencies` lỡ phiên) → **không undercount cửa-sổ-trễ-scheduler**.
- `expiring` gồm cả `workflow_state=Active` có `expiry_date` trong 45 ngày (chưa trúng mốc 60/30 nên scheduler chưa stamp `Expiring`) → tile khớp drill.

**Vì sao chọn predicate LIVE thay vì cờ workflow_state:**
- Cờ `workflow_state` là **trạng-thái-rời-rạc** chỉ đổi tại mốc scheduler (90/60/30/quá-hạn) → trễ pha so với thời gian thực; KPI dashboard phải phản ánh thực-tại NGAY (NĐ98 — operator quá hạn không được hiển thị "Đang hiệu lực").
- `get_expiring_competencies` **đã** là LIVE date-derived; chốt 1 predicate để **card == drill** (đo được).

**2 helper SoT** (đặt tại `assetcore/services/imm06.py`, type-hinted + docstring, trả `dict` filter dùng cho `frappe.get_all` / `frappe.db.count`):

```python
EXPIRY_WINDOW_DAYS = 60  # INVARIANT — cửa sổ "sắp hết hạn", KHỚP get_expiring_competencies default

def _expiring_competency_filter() -> dict:
    """SoT predicate LIVE 'Sắp hết hạn' (BR-06-14).

    expiring(c) ⟺ workflow_state ∈ {Active, Expiring}
                ∧ expiry_date ∈ [today, today + EXPIRY_WINDOW_DAYS].
    Dùng CHUNG cho KPI count (get_dashboard_stats) lẫn drill (get_expiring_competencies).
    KHÔNG đếm theo cờ workflow_state==Expiring thuần.
    """
    today = nowdate()
    return {
        "workflow_state": ["in", [CompetencyStatus.ACTIVE, CompetencyStatus.EXPIRING]],
        "expiry_date": ["between", [today, add_days(today, EXPIRY_WINDOW_DAYS)]],
    }

def _expired_competency_filter() -> dict:
    """SoT predicate LIVE 'Đã hết hạn' (BR-06-14).

    expired(c) ⟺ workflow_state ∈ {Active, Expiring, Expired}
               ∧ expiry_date < today (gồm cả late-scheduler vẫn Active).
    Loại Revoked/Suspended. KHÔNG đếm theo cờ workflow_state==Expired thuần.
    """
    return {
        "workflow_state": ["in", [CompetencyStatus.ACTIVE, CompetencyStatus.EXPIRING,
                                  CompetencyStatus.EXPIRED]],
        "expiry_date": ["<", nowdate()],
    }
```

**Write-site / read-site phải dùng SoT (delta so với bản trước):**

| # | Site | Trước (lỗi) | Sau (SoT) |
|---|---|---|---|
| 1 | `get_dashboard_stats().competencies.expiring` | `_count(workflow_state==Expiring)` | `_count("IMM User Competency", _expiring_competency_filter())` |
| 2 | `get_dashboard_stats().competencies.expired` | `_count(workflow_state==Expired)` | `_count("IMM User Competency", _expired_competency_filter())` |
| 3 | `get_expiring_competencies(days)` | filter inline `[Active,Expiring] ∧ between[today, today+days]` | giữ shape; khi `days==EXPIRY_WINDOW_DAYS` filter **bằng** `_expiring_competency_filter()` (parity). Vẫn nhận `days` tham số (drill 90/365) nhưng default = `EXPIRY_WINDOW_DAYS`. |

> **Giữ nguyên `competencies.active`:** KPI `.active` vẫn `_count(workflow_state==Active)` (tổng đang-hiệu-lực theo cờ) — KHÔNG đổi. Chỉ `.expiring` / `.expired` chuyển sang predicate LIVE. (Tránh hiểu nhầm: `.active` và `.expiring` có thể overlap về tập record — `.active` là tổng cờ Active, `.expiring` là tập con date-derived sắp hết hạn; đây là 2 KPI khác mục đích, không yêu cầu disjoint.)

**INVARIANT đo được (acceptance test):**

```
∀ dataset:  get_dashboard_stats()["competencies"]["expiring"] == len(get_expiring_competencies(EXPIRY_WINDOW_DAYS))
```

- Năng lực `expiry_date` trong 45 ngày + `workflow_state=Active` (scheduler chưa stamp Expiring) → PHẢI đếm vào `expiring` **và** xuất hiện trong drill.
- Năng lực `expiry_date < today` + `workflow_state=Active` (scheduler lỡ phiên) → PHẢI đếm vào `expired` (không undercount).
- Năng lực `workflow_state ∈ {Revoked, Suspended}` → KHÔNG bao giờ đếm vào expiring/expired (kiểm cả 2 phía).

**Scheduler BẤT BIẾN:** `check_expiring_competencies` / `auto_expire_competencies` GIỮ NGUYÊN — vẫn stamp `workflow_state` (phục vụ workflow transition + Alert Log idempotent + email + `_invalidate_auth_cache`). `CompetencyStatus.AUTHORIZED = (Active, Expiring)` và auth-cache gating (`get_asset_operator_coverage`, `check_user_authorization`) BẤT BIẾN — chỉ KPI/drill chuyển sang predicate LIVE.

**No N+1 / no schema migration:** dùng `frappe.db.count(filters)` + `frappe.get_all` 1 query mỗi predicate; `expiry_date` / `days_until_expiry` / `is_expired` đã tồn tại (field #11/#23/#24 §III) — KHÔNG cần migration.

---

## §V Controller Hooks (lifecycle)

> ✅ Implemented — controllers wire vào `validate`/`before_save`/`on_update` của Program/Session/Competency.
> **Refactor 2026-06-03:** `before_save` gọi SoT `compute_competency_dates()` (xem §V.1) thay vì inline formula.

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
            from assetcore.services.imm06 import compute_competency_dates
            dates = compute_competency_dates(self.achieved_date, self.validity_months)
            self.expiry_date = dates["expiry_date"]
            self.recertification_due_date = dates["recertification_due_date"]  # SoT — INVARIANT expiry−60d

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
| Bắt đầu | **Planned, Confirmed** | In Progress | IMM Training Officer, IMM Biomed Technician |
| Hoàn thành | In Progress | Completed | IMM Training Officer, IMM Biomed Technician |
| Verify | Completed | Verified | IMM Workshop Lead, IMM System Admin |
| Đóng | Verified | Closed | IMM Workshop Lead, IMM System Admin |
| Hủy | **Planned, Confirmed** | Cancelled | IMM Training Officer, IMM System Admin |

> BR-06-12: Chỉ Hủy được ở **Planned/Confirmed** (buổi chưa diễn ra). Không thể Hủy từ **In Progress, Completed, Verified hoặc Closed**: buổi đã bắt đầu (In Progress) → dùng luồng Hoàn thành; competency phát hành ở Completed → hủy sẽ mồ côi bản ghi năng lực.
> "Bắt đầu" cho phép TỪ CẢ Planned (bỏ qua bước Xác nhận) — xác nhận là tùy chọn; xem ADR-IMM-06-02.
> ⚠️ **Self-Correction (Vòng 28 — CR-WF-06-SESSION):** bảng CŨ ghi "Hủy | Planned, Confirmed, **In Progress**" và code-block §VI.1a CŨ ghi `IN_PROGRESS: [COMPLETED, CANCELLED]` — **LỆCH code + workflow JSON**: guard THẬT `cancel_session` (imm06.py:1431) chỉ cho `_session_source_states(CANCELLED)` = **{Planned, Confirmed}** (msg "Chỉ có thể hủy... Planned hoặc Confirmed"), và `imm_06_session_workflow.json` **KHÔNG** có cạnh `In Progress→Cancelled`. Reconcile guard Vòng 28 khoá map ≡ workflow (8 cạnh) → doc nay khớp SoT: In Progress KHÔNG hủy được.

---

### §VI.1a — SSoT máy trạng thái Session: `_SESSION_VALID_TRANSITIONS` (Vòng 7)

**Vấn đề gốc (Self-Correction):** máy trạng thái Session được enforce ở **service layer** (không dùng Frappe Workflow JSON để transition — xem 07 §III.4), nên "trạng thái kế hợp lệ" phải là **một Single Source of Truth** mà cả BE (guard) lẫn FE (gate nút) đọc chung. Trước Vòng 7, map này là dict cục bộ `_transitions` **bên trong** `get_session()` và **thiếu** `In Progress` ở khóa `Planned` → FE (nếu gate theo map) ẩn nút "Bắt đầu" ở Planned dù `start_training_session` (imm06.py:242) cho phép → **desync "BE cho phép, UI chặn"**.

**Quyết định:** Hoist thành **hằng module-level** `_SESSION_VALID_TRANSITIONS: dict[str, list[str]]` trong `assetcore/services/imm06.py`, liệt kê **đủ 7 state** (2 terminal → `[]`). `get_session()` và test invariant đọc cùng hằng này.

```python
# assetcore/services/imm06.py — SSoT máy trạng thái Session (module-level)
_SESSION_VALID_TRANSITIONS: dict[str, list[str]] = {
    SessionStatus.PLANNED:     [SessionStatus.CONFIRMED, SessionStatus.IN_PROGRESS, SessionStatus.CANCELLED],
    SessionStatus.CONFIRMED:   [SessionStatus.IN_PROGRESS, SessionStatus.CANCELLED],
    SessionStatus.IN_PROGRESS: [SessionStatus.COMPLETED],   # KHÔNG Cancelled (Self-Correction Vòng 28)
    SessionStatus.COMPLETED:   [SessionStatus.VERIFIED],
    SessionStatus.VERIFIED:    [SessionStatus.CLOSED],
    SessionStatus.CLOSED:      [],   # terminal
    SessionStatus.CANCELLED:   [],   # terminal
}
# get_session(): data["allowed_transitions"] = _SESSION_VALID_TRANSITIONS.get(data["workflow_state"], [])
```

**Bijection CTA → next-state (để test invariant map↔guard):**

| CTA (API) | Service fn | next-state T | Guard cho phép TỪ state | Có trong map[s] khi |
|---|---|---|---|---|
| `confirm_session` | `confirm_session` | Confirmed | `== Planned` | s = Planned |
| `start_session` | `start_training_session` | In Progress | `in (Planned, Confirmed)` | s ∈ {Planned, Confirmed} |
| `complete_session` | `complete_training_session` | Completed | `== In Progress` | s = In Progress |
| `verify_session` | `verify_session` | Verified | `== Completed` | s = Completed |
| `close_session` | `close_session` | Closed | `== Verified` | s = Verified |
| `cancel_session` | `cancel_session` | Cancelled | `in (Planned, Confirmed)` — imm06.py:1431 `_session_source_states(CANCELLED)` | s ∈ {Planned, Confirmed} |

**INVARIANT (map↔guard KHÔNG drift)** — với mọi state `s` và mọi CTA có next-state `T`:
`T ∈ _SESSION_VALID_TRANSITIONS[s]  ⟺  service_của_T KHÔNG ném guard-error (BAD_STATE) khi doc ở state s`.
Test bắt drift 2 chiều (xem 07 §III.4 `TestSessionTransitionInvariant`).

**Thay đổi CODE cần thiết (Self-Correction, ngoài hoist map):**
1. `cancel_session` (imm06.py:1215) — MỞ RỘNG guard chặn thêm `VERIFIED`: `if doc.workflow_state in (COMPLETED, VERIFIED, CLOSED, CANCELLED): raise BAD_STATE`. Trước Vòng 7 guard **thiếu VERIFIED** → cho hủy buổi đã Verified, **vi phạm BR-06-12** (spec đã có sẵn) và làm drift map[Verified]=[Closed]. Đây là sửa code cho khớp spec, không đổi spec.
2. `start_training_session` — GIỮ NGUYÊN (đã cho `in (Confirmed, Planned)`); chỉ map + FE cần đồng bộ.

#### ADR-IMM-06-02: "Bắt đầu" cho phép từ Planned (xác nhận là tùy chọn)
- **Status**: Accepted · **Date**: 2026-07-10
- **Context**: `start_training_session` (imm06.py:242) từ đầu đã cho phép `workflow_state in (Confirmed, Planned)`. FE lại gate `state==='Confirmed'` → ẩn nút "Bắt đầu" ở Planned. Buổi khẩn/nhỏ có thể bắt đầu ngay không cần bước Xác nhận (VR-05 ≥1 học viên chỉ chặn ở Xác nhận).
- **Decision**: Coi guard BE là SoT — "Bắt đầu" hợp lệ từ **Planned HOẶC Confirmed**. Đưa `In Progress` vào `map[Planned]`; FE gate bằng `allowedTransitions.includes('In Progress')`.
- **Alternatives**: (a) Thắt BE chỉ cho Confirmed→In Progress — loại: mất khả năng bắt đầu nhanh, và đổi hành vi service đang chạy. (b) Giữ desync — loại: nút chết, vi phạm GATE-8/LL-FE-51.
- **Consequences**: Xác nhận (Confirmed) trở thành **tùy chọn** trong luồng. Khi bắt đầu thẳng từ Planned, **VR-05 (≥1 học viên) KHÔNG được enforce ở Bắt đầu** (chỉ ở Xác nhận). *(Cần khảo sát)*: có cần thêm guard "≥1 học viên" cho `start_training_session` không → backlog, không thuộc Vòng 7.

#### ADR-IMM-06-03: `allowed_transitions` server-driven — lớp state-machine tách khỏi lớp quyền
- **Status**: Accepted · **Date**: 2026-07-10
- **Context**: FE hardcode `state==='X'` cho 6 CTA (GATE-8/LL-FE-51 anti-pattern: dead-gate + dễ drift với BE).
- **Decision**: BE tính `allowed_transitions` từ `_SESSION_VALID_TRANSITIONS` và trả trong `get_session` (Decision-B envelope `{success,data}`). FE gate **2 lớp AND**: `allowedTransitions.includes('<next-state>')` (state-machine) **&&** `<capability>` (quyền). `allowed_transitions` KHÔNG thay thế gate quyền — gọi API trực tiếp vẫn bị `_require_training_officer()` (training.write) chặn.
- **Alternatives**: Suy ra transition từ Frappe Workflow JSON — loại: transition Session enforce ở service, không qua workflow engine (07 §III.4); đọc 2 nguồn sẽ drift.
- **Consequences**: Thêm 1 field enriched trong `get_session`; mọi thay đổi state-machine chỉ sửa 1 hằng. FE có thể **nghiêm hơn** BE ở lớp quyền (vd Confirm gate `training.submit` trong khi BE chỉ đòi `training.write`) — chấp nhận (an toàn). *(Cần khảo sát)*: có nên nâng BE confirm/verify/close lên `training.submit` cho khớp FE không → backlog.

---

### §VI.1b — Reconcile invariant map ⇄ workflow JSON: `_SESSION_EXCEPTION_EDGES` == ∅ (Vòng 28 — CR-WF-06-SESSION)

**Vấn đề gốc.** `_SESSION_VALID_TRANSITIONS` (SoT enforce + CTA server-driven) và `imm_06_session_workflow.json` (desk/admin-override) là **2 nguồn** mô tả CÙNG máy trạng thái buổi đào tạo. §VI.1a chỉ chốt invariant map↔service-guard (TC6) — **thiếu** invariant map↔workflow-JSON. Thêm/bớt 1 cạnh ở JSON (vd wire thêm `In Progress→Cancelled`) mà quên map (hoặc ngược lại) → drift ÂM THẦM: CTA hiện/ẩn lệch với transition desk. Đây là SSoT-map hardcode **CUỐI CÙNG** của IMM-06 chưa reconcile-vs-workflow (competency đã đóng ở §VI.2b / Vòng 26).

**Quyết định (reconcile 2-chiều, EXCEPTION_EDGES rỗng).** Thêm invariant `test_session_allowed_transitions_matches_workflow` (parity R26 `test_competency_allowed_transitions_matches_workflow`): so tập cạnh distinct `(state, next_state)` giữa map và workflow JSON.

```python
# assetcore/tests/test_imm06.py — hằng test-level TƯỜNG MINH (imm06.py CHỈ +comment, 0 runtime logic)
_SESSION_EXCEPTION_EDGES: frozenset = frozenset()   # 0 ngoại lệ — TƯƠNG PHẢN competency (4 cạnh)

workflow_pairs = {(t["state"], t["next_state"]) for t in wf["transitions"]}   # role-expanded → set gom
map_pairs = {(s, n) for s, ns in _SESSION_VALID_TRANSITIONS.items() for n in ns}
assert workflow_pairs.symmetric_difference(map_pairs) == _SESSION_EXCEPTION_EDGES   # == ∅
```

**8 cạnh 2 bên khớp HỆT** (verified @source, python set-diff trên JSON THẬT + map): `Planned→{Confirmed, In Progress, Cancelled}` · `Confirmed→{In Progress, Cancelled}` · `In Progress→Completed` · `Completed→Verified` · `Verified→Closed`. sym-diff = ∅ (0 orphan, 0 unsurfaced).

**Vì sao session 0 EXCEPTION_EDGES (TƯƠNG PHẢN competency 4 — §VI.2b):**

| | Session | Competency |
|---|---|---|
| Map value | next-STATE (đích cụ thể) | nhãn ACTION (Sign-off/Revoke/…) |
| scheduler-auto edge | KHÔNG có | 3 (Active→Expiring/Expired, Expiring→Expired) |
| create-new edge | KHÔNG có | 1 (recertify sinh doc mới ở Pending) |
| `_XXX_EXCEPTION_EDGES` | **∅ (frozenset())** | 4 cạnh |

Máy trạng thái buổi đào tạo **100% CTA người dùng** (confirm/start/complete/verify/close/cancel) — không transition do scheduler tự chạy, không action sinh record mới — nên MỌI cạnh workflow ánh xạ 1:1 vào map.

- **Grounding 2-chiều (0 orphan):** mọi action-label workflow (`Xác nhận/Bắt đầu/Hoàn thành/Verify/Đóng/Hủy`) có cạnh `(state→next_state) ∈ map`; mọi cạnh map `∈ workflow`. Anti-drift nhãn: label lạ trong JSON → `assertIn(t["action"], _SESSION_WF_ACTION_LABELS)` RED.
- **RED-before demo (verified @output):** tạm gỡ `In Progress` khỏi `map[Planned]` → sym-diff = `{('Planned','In Progress')}` ≠ ∅ → RED, message: `map ⇄ workflow divergent [('Planned', 'In Progress')] != EXCEPTION_EDGES [] — cạnh lạ = drift SSoT↔workflow` (CTA "Bắt đầu" ẩn ở buổi Planned dù workflow còn cạnh). Restore → GREEN.
- **KHÔNG sửa `imm_06_session_workflow.json`** (map đã khớp hệt JSON sẵn có) ⇒ admin-override invariant GIỮ NGUYÊN (`test_workflow_admin_override` 10/10) + 0 migrate. Chỉ `+comment` vào imm06.py (0 runtime logic) + test + doc ⇒ 0 gunicorn reload.

#### ADR-IMM-06-08: Reconcile invariant map ⇄ workflow JSON qua `_SESSION_EXCEPTION_EDGES` == ∅
- **Status**: Accepted · **Date**: 2026-07-13
- **Context**: map `_SESSION_VALID_TRANSITIONS` (SoT CTA) và `imm_06_session_workflow.json` (desk) là 2 nguồn cùng mô tả state-machine buổi đào tạo; §VI.1a chỉ chốt map↔service-guard, chưa chốt map↔JSON → drift âm thầm khả dĩ. Là SSoT-map hardcode cuối của IMM-06 chưa có reconcile-vs-workflow.
- **Decision**: Khai `_SESSION_EXCEPTION_EDGES` tường minh == `frozenset()` (0 ngoại lệ) + invariant `symmetric_difference(workflow_pairs, map_pairs) == EXCEPTION_EDGES`. Hằng đặt ở **test file** (imm06.py chỉ +comment — round này ràng buộc 0 .py runtime logic).
- **Alternatives**: (a) Không guard, prose "đã khớp" — loại: không chống drift tương lai. (b) Đặt `_SESSION_EXCEPTION_EDGES` như hằng runtime trong imm06.py — loại: dead constant runtime + vi phạm ràng buộc "0 .py runtime logic / 0 reload". (c) Cho EXCEPTION_EDGES ≠ ∅ để "nới" — loại: session không có scheduler-auto/create-new nên mọi cạnh lệch = drift THẬT, không có ngoại lệ chính đáng.
- **Consequences**: Drift 2-chiều bất khả (thêm/bớt cạnh 1 phía mà quên phía kia → RED). Khi thêm transition tương lai PHẢI cập nhật CẢ map lẫn JSON (nếu là CTA) HOẶC khai exception có lý do (nếu scheduler-auto/create-new — hiện chưa có). Parity đầy đủ với IMM-12 (vòng 12) / IMM-16 (vòng 14) / competency §VI.2b (vòng 26).

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

> ⚠️ **Self-Correction (Vòng 15) — bảng trên là hành vi CŨ, đã siết.** Nguồn-đích enforce THẬT nay theo SoT `_COMPETENCY_VALID_TRANSITIONS` (§VI.2a): **Thu hồi** chỉ từ `{Active, Expiring, Expired, Suspended}` (bỏ `Pending Assessment` — trước đây chỉ chặn `Revoked`); **Tái chứng nhận** từ `{Expiring, Expired}` (thêm guard state — service cũ KHÔNG kiểm state nguồn). Quyền enforce = capability `training.submit` (không hardcode role-name) — xem ADR-IMM-06-04.
>
> ⚠️ **Self-Correction (Vòng 26) — Tạm ngưng / Khôi phục là "hidden-transition-câm" đã hiện thực.** Hai cạnh **Tạm ngưng** (`Active → Suspended`) và **Khôi phục** (`Suspended → Active`) ĐÃ khai trong `imm_06_competency_workflow.json` (allowed = **PM Manager, Training Manager, AssetCore Super Admin, System Manager** — KHÔNG phải "IMM Workshop Lead / IMM Training Officer" như bảng CŨ) nhưng TRƯỚC Vòng 26 **THIẾU service + API + CTA** ⇒ bất khả thao tác từ app dù đủ quyền. Vòng 26 SURFACE 2 cạnh này vào SSoT `_COMPETENCY_VALID_TRANSITIONS` (`Active += Suspend`, `Suspended = [Restore, Revoke]`) + service `suspend_competency`/`restore_competency` + endpoint C.5/C.6 + CTA `CompetencyDetailView`. Chi tiết §VI.2b + ADR-IMM-06-05/06/07.

---

### §VI.2a — SSoT máy trạng thái Competency: `_COMPETENCY_VALID_TRANSITIONS` (Vòng 15)

**Vấn đề gốc (Self-Correction — parity §VI.1a).** Ba CTA vòng đời năng lực (Sign-off / Thu hồi / Tái chứng nhận) được enforce ở **service layer** (dùng `flags.ignore_workflow_status_check = True` + set state trực tiếp, KHÔNG chạy Frappe Workflow transition — xem divergence bên dưới). Trước Vòng 15:
1. **State-guard rời rạc / thiếu**: `signoff_competency` chặn đúng (`state != Pending → BAD_STATE`); `revoke_competency` chỉ chặn `state == Revoked` (⇒ **revoke được cả `Pending Assessment`** — vô nghĩa vì chưa có gì để thu hồi); `recertify_competency` **KHÔNG có guard state nguồn** (chạy từ mọi state). → FE phải hardcode danh sách state (`CompetencyDetailView.vue:30-40`) = dead-gate + drift với BE (GATE-8/LL-FE-51 anti-pattern).
2. **Không có `allowed_transitions` server-driven** cho detail view (khác `get_session`).

**Quyết định.** Hoist **1 hằng module-level** `_COMPETENCY_VALID_TRANSITIONS: dict[str, list[str]]` trong `assetcore/services/imm06.py`, liệt kê **đủ 6 state** (Revoked terminal → `[]`). `get_competency()` (endpoint MỚI) và 3 service-guard đọc **cùng** hằng này. **KHÁC `_SESSION_VALID_TRANSITIONS`**: value là **nhãn ACTION** (`"Sign-off" / "Revoke" / "Recertify"`), KHÔNG phải next-state — vì lifecycle năng lực là "hành động trên record" (revoke/recertify có side-effect tạo doc mới), không map 1:1 CTA→next-state như session.

> **Tên hằng THẬT trong code** (grounding `services/imm06.py:117-146`): `COMPETENCY_SIGNOFF`/`COMPETENCY_REVOKE`/`COMPETENCY_RECERTIFY` (+ Vòng 26: `COMPETENCY_SUSPEND`/`COMPETENCY_RESTORE`); helper đọc-nguồn = `_competency_states_allowing(action)` (KHÔNG phải `_assert_competency_action` — minh hoạ dưới giữ tên rút gọn cho dễ đọc). BE code theo tên THẬT.

```python
# assetcore/services/imm06.py — hằng module-level (SSoT, Vòng 15 + Vòng 26)
COMP_ACTION_SIGNOFF   = "Sign-off"
COMP_ACTION_REVOKE    = "Revoke"
COMP_ACTION_RECERTIFY = "Recertify"
COMP_ACTION_SUSPEND   = "Suspend"     # Vòng 26 (JSON label "Tạm ngưng")
COMP_ACTION_RESTORE   = "Restore"     # Vòng 26 (JSON label "Khôi phục")

# Map PHẢI khớp EXACT guard state ở service layer (invariant test test_imm06
# TC-COMP chống drift — parity TC6 session). value = nhãn ACTION (KHÁC session=state).
# Vòng 26: Active += Suspend; Suspended = [Restore, Revoke] (thứ tự ỔN ĐỊNH — test list-eq).
_COMPETENCY_VALID_TRANSITIONS: dict[str, list[str]] = {
    CompetencyStatus.PENDING:   [COMP_ACTION_SIGNOFF],
    CompetencyStatus.ACTIVE:    [COMP_ACTION_REVOKE, COMP_ACTION_SUSPEND],
    CompetencyStatus.EXPIRING:  [COMP_ACTION_RECERTIFY, COMP_ACTION_REVOKE],
    CompetencyStatus.EXPIRED:   [COMP_ACTION_RECERTIFY, COMP_ACTION_REVOKE],
    CompetencyStatus.SUSPENDED: [COMP_ACTION_RESTORE, COMP_ACTION_REVOKE],
    CompetencyStatus.REVOKED:   [],                     # terminal
}

def _assert_competency_action(state: str, action: str) -> None:
    """Guard: action hợp lệ từ `state`? (đọc SoT — drift bất khả)."""
    if action not in _COMPETENCY_VALID_TRANSITIONS.get(state, []):
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"Không thể '{action}' ở trạng thái '{state}'",
        )
```

**Áp dụng guard (mỗi service fn gọi ngay sau khi fetch doc):**

| Service fn | Guard gọi | State nguồn hợp lệ (từ SoT) |
|---|---|---|
| `signoff_competency` | guard `state ∈ _competency_states_allowing(SIGNOFF)` | `Pending Assessment` |
| `revoke_competency` | guard `state ∈ _competency_states_allowing(REVOKE)` | `Active`, `Expiring`, `Expired`, `Suspended` |
| `recertify_competency` | guard `old.workflow_state ∈ _competency_states_allowing(RECERTIFY)` | `Expiring`, `Expired` |
| `suspend_competency` (Vòng 26) | guard `state ∈ _competency_states_allowing(SUSPEND)` | `Active` |
| `restore_competency` (Vòng 26) | guard `state ∈ _competency_states_allowing(RESTORE)` | `Suspended` |

**Invariant (đo được — AC4):**
`action ∈ _COMPETENCY_VALID_TRANSITIONS[s]  ⟺  service_của_action KHÔNG ném BAD_STATE khi doc ở state s`. (Có thể ném `VALIDATION`/`NOT_FOUND` như recertify thiếu session Completed / participant Fail — phân biệt bằng `ErrorCode`, KHÔNG tính drift.)

**`get_competency()` emit (parity `get_session()` imm06.py:1005):**
```python
data["allowed_transitions"] = list(
    _COMPETENCY_VALID_TRANSITIONS.get(data.get("workflow_state", ""), [])
)
# Cờ quyền — action khả dụng khi (state cho phép) ∧ (đủ capability). Vòng 26:
# lọc theo allowed để cờ khớp EXACT cả 2 lớp (parity can_revoke — chống dead-control).
_can = rbac.can("training.submit")
data["can_signoff"]   = (COMP_ACTION_SIGNOFF   in allowed) and _can
data["can_revoke"]    = (COMP_ACTION_REVOKE    in allowed) and _can
data["can_recertify"] = (COMP_ACTION_RECERTIFY in allowed) and _can
data["can_suspend"]   = (COMP_ACTION_SUSPEND   in allowed) and _can   # Vòng 26
data["can_restore"]   = (COMP_ACTION_RESTORE   in allowed) and _can   # Vòng 26
```

> Grounding: code THẬT `get_competency` (imm06.py:1440) đã lọc `(ACTION in allowed) and _has_submit` cho 3 cờ hiện hữu; Vòng 26 chỉ THÊM 2 cờ `can_suspend`/`can_restore` cùng công thức.

**Divergence workflow JSON (documented, KHÔNG block).** `imm_06_competency_workflow.json` khai báo `Tái chứng nhận: Expired → Active` (chỉ Expired, target Active). Nhưng service `recertify_competency` KHÔNG chạy transition đó — nó **tạo IMM User Competency mới** (state `Pending Assessment`) từ session Refresher đã `Completed` + mark bản cũ → `Expired`, dùng `ignore_workflow_status_check`. ⇒ Workflow JSON là **tham chiếu thứ cấp**; **SoT enforce = `_COMPETENCY_VALID_TRANSITIONS`**. Cạnh `Expiring→Tái chứng nhận` (map có, JSON không) + 3 cạnh scheduler-auto (JSON có, map không) nay được khai TƯỜNG MINH thành `_COMPETENCY_EXCEPTION_EDGES` và verify bằng reconcile invariant — xem §VI.2b.

---

### §VI.2b — Tạm ngưng / Khôi phục + Reconcile invariant map ⇄ workflow JSON (Vòng 26)

**Vấn đề gốc (CR-WF-06-COMP — "hidden-transition-câm").** `imm_06_competency_workflow.json` khai 2 cạnh `Tạm ngưng` (`Active → Suspended`) và `Khôi phục` (`Suspended → Active`) cho Training/PM Manager/Super Admin/System Manager, nhưng **THIẾU service + API + CTA** → user đủ quyền vẫn KHÔNG thao tác được từ app (nút không tồn tại). SSoT `_COMPETENCY_VALID_TRANSITIONS` (Vòng 15) bỏ sót 2 cạnh này ⇒ `get_competency.allowed_transitions` không bao giờ chứa `Suspend`/`Restore` ⇒ FE (gate 2-lớp AND) không render nút. Đồng thời map ⇄ JSON chưa có invariant bảo vệ nên drift âm thầm.

**Quyết định (surface + reconcile).**
1. **SURFACE** 2 cạnh vào SSoT (đã cập nhật §VI.2a): `Active += Suspend`, `Suspended = [Restore, Revoke]` (thứ tự ổn định). ⇒ `allowed_transitions[Active] ⊇ {Suspend}`, `allowed_transitions[Suspended] == [Restore, Revoke]`.
2. **2 service transition mới** (parity `revoke_competency` imm06.py:464):

| Fn | Chuyển | reason | Guard state (SoT) | Audit action → event_type | Cache |
|---|---|---|---|---|---|
| `suspend_competency(name, reason)` | `Active → Suspended` | **BẮT BUỘC** (rỗng → `VALIDATION`/422) | `_competency_states_allowing(SUSPEND) = {Active}`; nguồn≠Active → `BAD_STATE`/409 | `SUSPENDED` → `competency_suspended` | `_invalidate_auth_cache(user, model)` (Suspended ∉ AUTHORIZED ⇒ mất authorization) |
| `restore_competency(name)` | `Suspended → Active` | — (không cần) | `_competency_states_allowing(RESTORE) = {Suspended}`; nguồn≠Suspended → `BAD_STATE`/409 | `RESTORED` → `competency_restored` | `_invalidate_auth_cache(user, model)` (Active ∈ AUTHORIZED ⇒ tái cấp) |

- **Thứ tự kiểm** (giống revoke): `NOT_FOUND`(404) → guard state `BAD_STATE`(409) → (suspend) `reason` rỗng `VALIDATION`(422) → mutate `workflow_state` với `doc.flags.ignore_workflow_status_check = True` → save → invalidate cache → `_log_competency_audit(name, doc.user, "SUSPENDED"|"RESTORED", reason)` → `frappe.db.commit()`.
- **reason KHÔNG lưu field riêng**: ghi vào `IMM Audit Trail.change_summary` (qua `_log_competency_audit` note) — KHÔNG thêm `suspend_reason` field (tránh permlevel-strip trap + schema churn; audit là bản ghi bất biến đủ traceability NĐ98). `suspended_until` (Date, doctype §II.4:197) NGOÀI scope CR này (không có tạm-ngưng-có-hạn ở acceptance).
- **Capability gate ở API layer** (parity revoke api:224): `if not rbac.can("training.submit"): return _err(..., ErrorCode.FORBIDDEN)` TRƯỚC khi gọi service ⇒ thiếu quyền → `FORBIDDEN`/403 in-handler HTTP-200 envelope, **KHÔNG chạm `workflow_state`** (chưa vào service). Xem 05 §C.5/C.6.

3. **⚠️ REQUIRED — thêm 2 option vào Select `event_type` (IMM Audit Trail).** `_log_competency_audit` gọi `log_audit_event(event_type=f"competency_{action.lower()}")` → insert `IMM Audit Trail` với `event_type ∈ {competency_suspended, competency_restored}`. Field `event_type` là **Select** (`imm_audit_trail.json`) — hiện có `competency_signoff/revoked/recertified/auto_expired` NHƯNG **KHÔNG có** `competency_suspended`/`competency_restored`. Frappe validate Select strict ⇒ giá trị ngoài options → `ValidationError` → `_log_competency_audit` nuốt exception (try/except → `frappe.log_error`) ⇒ **audit rớt CÂM** (latent NĐ98 gap). ⇒ **PHẢI thêm** `competency_suspended` + `competency_restored` vào Select options `event_type` của `IMM Audit Trail` doctype (kèm reload/migrate để DB meta nhận option — nếu không audit test sẽ RED "no audit row"). Đây là schema-change bắt buộc (Ask-first đã CHỐT trong CR).

**Reconcile INVARIANT (gate merge — parity IMM-12 vòng-12 / IMM-16 vòng-14).** Khai 1 hằng module-level:

```python
# assetcore/services/imm06.py — nhãn ACTION (map) → nhãn action workflow JSON (Vietnamese)
_COMPETENCY_ACTION_JSON_LABEL = {
    COMP_ACTION_SIGNOFF:   "Sign-off",
    COMP_ACTION_REVOKE:    "Thu hồi",
    COMP_ACTION_RECERTIFY: "Tái chứng nhận",
    COMP_ACTION_SUSPEND:   "Tạm ngưng",     # Vòng 26
    COMP_ACTION_RESTORE:   "Khôi phục",      # Vòng 26
}
# Cạnh (state, json_action) TỒN TẠI ở đúng MỘT phía (map XOR workflow) — khai tường minh.
# WHY mỗi cạnh: 3 scheduler-auto (không có CTA người dùng) + 1 create-new (recertify sinh
# doc mới thay vì chạy transition). KHÔNG được rỗng, KHÔNG được chứa Suspend/Restore.
_COMPETENCY_EXCEPTION_EDGES = frozenset({
    ("Active",   "Đánh dấu sắp hết hạn"),   # Active→Expiring  — scheduler auto (check_expiring)
    ("Active",   "Hết hạn"),                # Active→Expired   — scheduler auto (auto_expire)
    ("Expiring", "Hết hạn"),                # Expiring→Expired — scheduler auto (auto_expire)
    ("Expiring", "Tái chứng nhận"),         # map-only — recertify create-new (JSON khai từ Expired)
})
```

**Invariant (đo được):** với `wf_keys = {(t.state, t.action) ∀ transition ∈ JSON}` và `map_keys = {(state, _COMPETENCY_ACTION_JSON_LABEL[a]) ∀ (state, a) ∈ map}`:

```
symmetric_difference(wf_keys, map_keys) == _COMPETENCY_EXCEPTION_EDGES
```

- **Verified @source** (python set-diff trên JSON THẬT + map sau-fix): sym-diff = đúng 4 cạnh trên = `_COMPETENCY_EXCEPTION_EDGES`. WF-only = 3 scheduler; MAP-only = `(Expiring, Tái chứng nhận)`.
- **RED-before** (gỡ `Suspend` khỏi `map[Active]` và/hoặc `Restore` khỏi `map[Suspended]`): sym-diff mọc thêm `(Active, "Tạm ngưng")` / `(Suspended, "Khôi phục")` ∉ EXCEPTION_EDGES ⇒ test RED (chống drift 2-chiều).
- Workflow JSON là role-expanded 33 transition / **11 cạnh distinct** `(state, action, next_state)` — invariant so trên `(state, action)` (role-independent).

**KHÔNG sửa `imm_06_competency_workflow.json`** (2 cạnh Suspend/Restore đã có sẵn + đã có `AssetCore Super Admin`/`System Manager`) ⇒ admin-override invariant 22/22 GIỮ NGUYÊN + 0 migrate cho workflow.

---

#### ADR-IMM-06-05: Surface Tạm ngưng / Khôi phục vào SSoT (đóng hidden-transition-câm)

- **Status**: Accepted
- **Date**: 2026-07-13
- **Context**: 2 cạnh workflow `Tạm ngưng`/`Khôi phục` đã khai trong JSON nhưng thiếu service/API/CTA; map SSoT bỏ sót ⇒ nút không render (parity vấn đề vòng-12 reopen_incident, vòng-14 start_review). Suspended cần **có đường quay lại** Active (khác Revoked terminal) — pause có thể đảo ngược.
- **Decision**: THÊM `Suspend` vào `map[Active]`, `Restore` vào `map[Suspended]`; hiện thực `suspend_competency`/`restore_competency` (parity revoke: guard-from-SoT + audit + cache-invalidate) + endpoint C.5/C.6 + CTA server-driven. Gate = `training.submit` (parity revoke — gỡ/tái authorization vận hành thiết bị = Manager-grade, NĐ98).
- **Alternatives**: (a) Gỡ 2 cạnh khỏi JSON cho khớp map cũ — **Loại**: mất năng lực nghiệp vụ hợp lệ (tạm ngưng KTV nghỉ phép/điều tra mà không thu hồi vĩnh viễn) + đổi workflow JSON = HARD-STOP migrate + phá admin-override. (b) Giữ desync — **Loại**: nút chết, vi phạm GATE-8/LL-FE-51.
- **Consequences**: +2 service fn, +2 endpoint, +2 CTA, +2 cờ `can_suspend`/`can_restore`, +2 Select option `event_type`. `map[Suspended]` chuyển từ terminal-ish `[Revoke]` → `[Restore, Revoke]` (giờ có 2 lối ra). Reason suspend chỉ ở audit (không field mới).

#### ADR-IMM-06-06: Reconcile invariant map ⇄ workflow JSON qua `_COMPETENCY_EXCEPTION_EDGES`

- **Status**: Accepted
- **Date**: 2026-07-13
- **Context**: map (SoT enforce/CTA) và workflow JSON (desk/admin-override) là 2 nguồn — divergent âm thầm (recertify create-new + scheduler-auto). Vòng 15 chỉ ghi chú prose "documented, KHÔNG block" → không có guard.
- **Decision**: Khai `_COMPETENCY_EXCEPTION_EDGES` tường minh (4 cạnh, mỗi cạnh có lý do scheduler-auto / create-new) + invariant `symmetric_difference(wf_keys, map_keys) == EXCEPTION_EDGES`. Test gate-merge (parity IMM-12/16).
- **Alternatives**: (a) Chỉ assert `map_keys ⊆ wf_keys` — **Loại**: không bắt được cạnh workflow-only (scheduler) lẫn map-only (recertify) đồng thời; symmetric-difference bắt CẢ HAI chiều. (b) Đồng bộ JSON = map (thêm `Expiring→Tái chứng nhận`, bỏ scheduler edges) — **Loại**: scheduler edges cần cho desk/auto; recertify là create-new không phải transition thật.
- **Consequences**: Drift 2-chiều bất khả (thêm/bớt cạnh 1 phía mà không cập nhật phía kia hoặc EXCEPTION_EDGES → RED). Khi thêm transition tương lai phải cập nhật CẢ map/JSON HOẶC khai exception có lý do.

#### ADR-IMM-06-07: Quá tải state "Suspended" (auto-archive vs manual-suspend) — ranh giới restore

- **Status**: Accepted
- **Date**: 2026-07-13
- **Context**: `Suspended` được dùng ở **2 ngữ cảnh**: (a) **manual** — Training Manager tạm ngưng KTV (CR này); (b) **auto-archive** — `archive_old_competency` (imm06.py:534, BR-06-11) set bản cũ `Active → Suspended` khi 1 competency mới cùng `(user, device_model)` được sign-off. `restore_competency` (`Suspended → Active`) không phân biệt 2 nguồn ⇒ khôi phục 1 bản auto-archived có thể tạo **2 competency Active trùng `(user, model)`**.
- **Decision**: Giữ `restore_competency` tối giản theo acceptance (`Suspended → Active`, gate `training.submit`); **KHÔNG** thêm guard chặn tự động trong CR này. Rủi ro trùng-Active giao **phán đoán Training Manager** (họ thấy bản ghi + lịch sử trước khi khôi phục) — ghi nhận là **known limitation**.
- **Alternatives**: (a) restore chặn nếu tồn tại bản Active mới hơn cùng `(user, model)` → re-archive/blocked — **hoãn** (ngoài acceptance; sẽ mở backlog nếu vận hành phát sinh trùng). (b) Tách state `Archived` riêng khỏi `Suspended` — **Loại (scope)**: đổi enum + workflow + migrate dữ liệu, quá lớn cho CR.
- **Consequences**: **Boundary (Never)** cho BE/FE: KHÔNG tự động re-activate hàng loạt bản Suspended; restore là thao tác đơn lẻ có chủ đích. **Backlog** `[ROADMAP]`: nếu cần, thêm duplicate-active guard vào `restore_competency` (invariant "≤1 Active per (user, device_model)").

---

#### ADR-IMM-06-04: Thống nhất `training.submit` cho cả 3 CTA vòng đời năng lực (sửa privilege asymmetry)

- **Status**: Accepted
- **Date**: 2026-07-10
- **Context**: 3 CTA năng lực đang gate **2 capability KHÁC nhau** → privilege asymmetry + FE dead-control 403:
  - `signoff_competency` (api:195) gate `rbac.can("training.submit")` → `("IMM Training Session", "delete")` → DocPerm delete=1 = **Super Admin, Training Manager** (Manager-grade, R18 fix).
  - `revoke_competency`/`recertify_competency` (api:213,219) KHÔNG gate ở API; service gate `_require_training_officer()` → `rbac.can("training.write")` → auto-gen `("IMM Training Program", "write")` → DocPerm write=1 = **Super Admin, Training Manager, và Training User** (lỏng hơn!).
  - Hệ quả: **Training User** (không phải manager) **thu hồi/tái chứng nhận được** năng lực KTV (gỡ authorization vận hành thiết bị — NĐ98 an toàn), nhưng **KHÔNG sign-off được**. Bất đối xứng: hành động nhạy hơn (revoke) lại gate lỏng hơn. `imm_06_competency_workflow.json` cũng ghi "Thu hồi"/"Tái chứng nhận" allowed = Training Manager + Super Admin (KHÔNG Training User) → service `training.write` sai ý định.
  - FE `CompetencyDetailView.vue:33-40` gate cả 3 bằng `can('training.submit')`, LỆCH với BE `training.write` cho revoke/recertify → dead-control (FE ẩn nút với Training User dù BE cho phép) / desync.
  - ⚠️ Đây KHÔNG phải "lỗ RBAC mở" (mọi user login KHÔNG revoke được — service `training.write` đã chặn plain `AssetCore System User`). Framing chính xác = **asymmetry**, không phải open-hole. (Self-Correction so với đề mục gốc.)
- **Decision**: Thống nhất **cả 3 CTA năng lực gate DUY NHẤT `training.submit`** (Manager-grade). Enforce 2 lớp:
  1. **API** (parity signoff, in-handler HTTP-200 FORBIDDEN envelope): `revoke_competency`/`recertify_competency` thêm inline `if not rbac.can("training.submit"): return _err("Chỉ Training Manager / Super Admin được …", ErrorCode.FORBIDDEN)` TRƯỚC `_run` — giống signoff:204.
  2. **Service** (defense-in-depth, cùng capability): trong `revoke_competency` (418) và `recertify_competency` (1416), thay `_require_training_officer()` → `rbac.require("training.submit")`. **KHÔNG đụng** helper dùng chung `_require_training_officer` (session transitions confirm/verify/close vẫn giữ `training.write` — ngoài scope).
  3. `get_competency` trả `can_signoff/can_revoke/can_recertify = rbac.can("training.submit")` → cờ FE khớp EXACT gate BE (chống dead-control 403).
- **Alternatives**:
  - (a) Chỉ thêm API gate, giữ service `training.write`: net-gate = `training.submit AND training.write`. Vì mọi role có Session-delete đều có Program-write (Super Admin/Training Manager), hiện tương đương — NHƯNG phụ thuộc invariant DocPerm ngầm (fragile, một thay đổi DocPerm tương lai làm lệch). **Loại** — không single-capability rõ ràng.
  - (b) Hạ signoff xuống `training.write` cho khớp revoke: **Loại** — sai chiều least-privilege; gỡ authorization thiết bị y tế PHẢI Manager-grade (NĐ98).
  - (c) Hardcode role-name (`if "Training Manager" in roles`): **Loại** — anti-pattern RBAC dead-gate (memory `asset_list_count_drill…` + LL-BE); phải capability-based.
- **Consequences**:
  - **Training User MẤT quyền revoke/recertify** (chỉ còn tạo/sửa program/session qua `training.write`) — đúng ý định workflow JSON + NĐ98. Đây là thay đổi hành vi có chủ đích; nêu trong Release Notes.
  - **AC3 không cần bổ sung mapping**: `AssetCore Super Admin` đã có `training.submit` (IMM Training Session DocPerm delete=1 — verified fixture). `training.submit ⊇ AssetCore Super Admin` ✅.
  - `CAP_SET_VERSION` **KHÔNG đổi** (không thêm/bớt cap key — chỉ đổi call-site) → FE persisted-caps không cần invalidate.
  - Đóng backlog "*(Cần khảo sát)*" ở ADR-IMM-06-03 (nâng BE lên `training.submit` cho khớp FE) — cho phạm vi 3 CTA năng lực.

---

## §VII Schedulers (`assetcore/services/imm06.py`)

> ✅ Implemented — service entries thực tế trong `assetcore/services/imm06.py` (KHÔNG ở `assetcore/tasks.py` — module không có file đó). Tên hàm ground truth (đã đăng ký trong `hooks.py:scheduler_events`):
> - daily: `check_expiring_competencies`, `auto_expire_competencies`, `check_recertification_due`
> - weekly: `generate_weekly_gap_report`
>
> Pseudocode bên dưới giữ nguyên ngữ nghĩa nhưng tên hàm tham chiếu theo ground truth.

### Job 1: `check_expiring_competencies()` — Daily 02:00

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

### Job 2: `auto_expire_competencies()` — Daily 02:30

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

### Job 4: `generate_weekly_gap_report()` — Weekly Monday 02:00

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

> ✅ Implemented trong `assetcore/hooks.py` (verify khi sync fixtures).

```python
# assetcore/hooks.py — entries thực tế cho IMM-06 (đã đăng ký, Wave-2)

scheduler_events = {
    "daily": [
        # ... existing entries ...
        # IMM-06 Training & Competency
        "assetcore.services.imm06.check_expiring_competencies",
        "assetcore.services.imm06.auto_expire_competencies",
        # IMM-06 recertification check
        "assetcore.services.imm06.check_recertification_due",
    ],
    "weekly": [
        # IMM-06 weekly gap report
        "assetcore.services.imm06.generate_weekly_gap_report",
    ],
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
-- DDL — verify đã apply qua bench migrate (DocType đã ship Wave 2)

CREATE INDEX idx_comp_user_model_state
  ON `tabIMM User Competency` (user, device_model, workflow_state);

CREATE INDEX idx_comp_state_expiry
  ON `tabIMM User Competency` (workflow_state, expiry_date);

CREATE INDEX idx_comp_dept_state_model
  ON `tabIMM User Competency` (department_at_assessment, workflow_state, device_model);

CREATE UNIQUE INDEX idx_alert_unique
  ON `tabIMM Competency Alert Log` (competency, alert_date, milestone);
```
