# IMM-06 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phiên bản | 0.1.0 (Wave 2 — DRAFT) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PLANNED |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | ISO 13485:2016 §6.2, WHO HTM Annex 5, NĐ 98/2021/NĐ-CP §35 |

---

## 1. Scope

### 1.1 In Scope

| # | Chức năng | Mô tả |
|---|---|---|
| F-01 | Curriculum master | Tạo/sửa/xóa (soft) Training Program theo Device Model / Category |
| F-02 | Schedule training | Lập kế hoạch Training Session theo Program — onsite/online/hybrid |
| F-03 | Quản lý học viên | Add/remove participant, theo dõi attendance, chấm theory + practical score |
| F-04 | Auto-create competency | Khi Session.complete: tự sinh `IMM User Competency` cho mọi participant Pass |
| F-05 | Sign-off competency | Supervisor (Department Manager / Workshop Head) duyệt → Pending Assessment → Active |
| F-06 | Tracking expiry | Scheduler đánh dấu Expiring/Expired theo `expiry_date` + `validity_period_months` |
| F-07 | Recertification flow | Auto-create placeholder session 60 ngày trước expiry; reminder Tổ HC-QLCL |
| F-08 | Revoke / Suspend | Thu hồi tạm thời (Suspended) hoặc vĩnh viễn (Revoked) — yêu cầu reason / CAPA |
| F-09 | Authorization gate | API `check_user_authorization` được IMM-04/08/09/12 gọi để validate |
| F-10 | Operator coverage | API `get_asset_operator_coverage` — đếm Active competency per asset (BR-06-07 redundancy Class III) |
| F-11 | Gap report | Auto weekly: ma trận khoa × class — assets vi phạm coverage |
| F-12 | Self-service portal | User xem competency của chính mình + lịch tái chứng nhận |
| F-13 | Dashboard KPI | % competent per dept, expiring 90d, completion rate, pass rate, gap count |
| F-14 | Audit trail | Mọi thay đổi competency có record (Frappe Version + IMM Audit Trail) |
| F-15 | Certificate file | Lưu chứng nhận PDF dưới dạng Asset Document (IMM-05 doc_category=Training) |

### 1.2 Out of Scope

| # | Chức năng | Module phụ trách |
|---|---|---|
| 1 | LMS (e-learning content delivery, video) | Hệ thống LMS riêng — IMM-06 chỉ ghi nhận hoàn thành |
| 2 | Quản lý ngân sách đào tạo | Tài chính (out-of-system) |
| 3 | Đánh giá hiệu suất công việc tổng thể (HR) | HR system |
| 4 | Cấp phát thẻ ID vật lý | An ninh / hành chính |
| 5 | E-signature số (ký số trên certificate) | v0.2 (Wave 3) |

### 1.3 Phạm vi thay đổi vs hệ thống hiện tại

- **Đã có (reuse, không sửa):** `AC Authorized Technician` (child của `AC Supplier`) — vendor-side authorized technicians dùng cho IMM-03 (AVL/contract); **độc lập** với IMM-06 (IMM-06 quản lý đào tạo **nhân sự nội bộ** sử dụng/vận hành thiết bị, không phải vendor tech). `IMM Audit Trail` (reuse). `AC Asset`, `AC Department` (reuse cho Link references).
- **Thêm mới hoàn toàn:** `IMM Training Program`, `IMM Training Session`, `IMM Training Participant` (child), `IMM User Competency`, `IMM Competency Gap Report`, `IMM Expiry Alert Log`; `services/imm06.py`; `api/imm06.py`; 4 scheduler jobs; 2 workflows (Session, Competency).
- **Cross-module gate đã hỗ trợ:** `services/imm08.py`, `services/imm09.py`, `services/imm12.py` — IMM-06 thêm hook `validate_user_authorization` trong `before_assign_technician` của các Work Order service.

---

## 2. Actors

| Actor | Vị trí thực tại BV | Quyền chính | Trách nhiệm |
|---|---|---|---|
| Trainee / Operator | Bác sĩ, điều dưỡng, KTV vận hành thiết bị | R (own competency) | Tham gia training; xác nhận attendance; xem chứng nhận |
| HTM Technician | KTV HTM | R/W (own session) | Có thể là instructor cho training cấp 1 |
| Biomed Engineer | Kỹ sư Biomedical | R/W/C training | Instructor cho training kỹ thuật; xem competency để assign WO |
| Tổ HC-QLCL (Training Officer) | Tổ HC-QLCL — Owner module | R/W/C, Approve, Cancel, Revoke | Owner — quản lý curriculum, schedule, đánh giá, revoke |
| Workshop Head | Trưởng Phân xưởng | R/W, Verify, Sign-off, Suspend/Revoke | Verify session đã hoàn thành; sign-off competency cấp khoa kỹ thuật |
| Clinical Head | Trưởng Khoa lâm sàng | R (own dept) | Phê duyệt operator nội khoa; nhận gap report của khoa |
| Department Manager | Trưởng phòng/khoa hành chính | R/W (sign-off own staff) | Sign-off competency cho cán bộ thuộc khoa |
| VP Block2 | Phó Khối 2 | R, nhận escalation | Nhận gap report toàn viện; phê duyệt ngoại lệ |
| CMMS Admin | IT / CMMS | Full | Quản trị, override, force action |
| System (Scheduler) | — | system-only | Auto-Expiring, auto-Expired, gap report, recert reminder |

---

## 3. User Stories (Gherkin)

### US-06-01 — Tạo Training Program (curriculum)

```gherkin
As Tổ HC-QLCL,
I want tạo Training Program cho 1 Device Model,
So that mọi training session sau này tham chiếu chuẩn đúng.

Scenario: Tạo program hợp lệ
  Given tôi có role "Tổ HC-QLCL" và Device Model "MDL-MON-PHILIPS-X3" tồn tại
  When tôi POST create_program với
    {program_code="TRN-MON-INIT-01", program_name="Đào tạo cơ bản Monitor Philips X3",
     target_device_model="MDL-MON-PHILIPS-X3", training_type="Initial",
     duration_hours=8, validity_period_months=24, passing_score_pct=70,
     assessment_method="Both", instructor_qualification_required="Biomed Engineer"}
  Then response.success = true
  And program.name = "TRN-MON-INIT-01"
  And program.is_mandatory_for_operation = 1 (default cho Initial)
```

### US-06-02 — Schedule Training Session

```gherkin
As Tổ HC-QLCL,
I want lập lịch 1 Training Session cho 15 học viên,
So that buổi training được tổ chức và quản lý.

Scenario: Schedule + invite participant
  Given Training Program "TRN-MON-INIT-01" đã Active
  When tôi POST create_session với
    {training_program="TRN-MON-INIT-01", session_date="2026-05-20",
     location="Phòng đào tạo F3", instructor="biomed1@hosp.vn",
     session_type="Onsite", duration_planned_hours=8,
     participants=[{user, department, role_at_session}]×15}
  Then session.workflow_state = "Planned"
  And session.name khớp regex "^TRN-2026-\d{4}$"
  And mọi participant có status "Invited"
```

### US-06-03 — Confirm & Run Session

```gherkin
As Tổ HC-QLCL / Instructor,
I want confirm session và bắt đầu training,
So that workflow chuyển sang In Progress.

Scenario: Workflow transitions
  Given session ở "Planned"
  When tôi action "Xác nhận" (Tổ HC-QLCL)
  Then state → "Confirmed"
  When instructor action "Bắt đầu"
  Then state → "In Progress"
  And email reminder gửi cho mọi participant
```

### US-06-04 — Chấm điểm & Complete Session

```gherkin
As Instructor (Biomed Engineer),
I want nhập attendance + theory + practical score cho mọi participant,
So that hệ thống xác định Pass/Fail và auto-create competency.

Scenario: Complete với pass/fail logic
  Given session ở "In Progress" với 15 participants
  When tôi điền theory_score, practical_score, attendance_pct cho mỗi người
  And action "Hoàn thành" (POST complete_session)
  Then mỗi participant có overall_result computed:
    - attendance_pct >= 80% AND avg(theory, practical) >= passing_score_pct → "Pass"
    - else → "Fail"
  And với mỗi Pass → tạo IMM User Competency status="Pending Assessment"
  And session.workflow_state = "Completed"
  And gửi email cho supervisor (Department Manager) yêu cầu sign-off
```

### US-06-05 — Supervisor Sign-off Competency

```gherkin
As Department Manager / Workshop Head,
I want sign-off competency của cán bộ thuộc khoa,
So that competency chuyển sang Active và user được phép vận hành.

Scenario: Sign-off thành công
  Given competency "COMP-2026-0042" status="Pending Assessment"
  And user thuộc khoa của tôi
  When tôi action sign-off
  Then competency.workflow_state = "Active"
  And competency.supervisor_signoff = session.user
  And competency.signoff_date = today
  And competency.expiry_date = achieved_date + validity_period_months
  And email "Bạn đã được cấp năng lực vận hành ..." gửi cho user
```

### US-06-06 — Cảnh báo hết hạn (Scheduler)

```gherkin
As System,
I check competency expiry mỗi ngày,
So that user và supervisor được nhắc kịp thời tái chứng nhận.

Scenario: Mốc cảnh báo
  Given competency Active có expiry_date
  When scheduler check_competency_expiry chạy
  Then days_remaining IN (90, 60, 30) → status="Expiring"
       sinh Competency Alert Log (idempotent)
       email user + supervisor (90=Info, 60=Warning, 30=Critical)
  And days_remaining < 0 → scheduler auto_expire_competency set status="Expired"
  And email "Năng lực đã hết hạn" gửi user, Workshop Head
```

### US-06-07 — Authorization Gate (IMM-08/09/12 hook)

```gherkin
As IMM-08 PM controller,
When assign technician vào WO,
I check_user_authorization để bảo đảm technician đủ năng lực.

Scenario: Technician đủ năng lực
  Given user "ktv1@hosp.vn" có Active competency cho device_model "MDL-MON-PHILIPS-X3"
  And asset của WO có device_model = "MDL-MON-PHILIPS-X3"
  When IMM-08 gọi check_user_authorization(user, asset.device_model)
  Then response.authorized = true

Scenario: Technician thiếu năng lực
  Given user không có Active competency
  When IMM-08 gọi check_user_authorization
  Then response.authorized = false, code = "NOT_AUTHORIZED"
  And IMM-08 throw "Kỹ thuật viên chưa có năng lực vận hành thiết bị này"
```

### US-06-08 — Operator Coverage Gate (IMM-04 Clinical_Release)

```gherkin
As IMM-04 controller,
When commissioning chuyển sang Clinical_Release,
I gate qua get_asset_operator_coverage để chặn nếu thiếu redundancy.

Scenario: Class III thiếu operator
  Given asset class III tại khoa ICU
  And chỉ có 1 user Active competency tại ICU
  When IMM-04 gate gọi get_asset_operator_coverage(asset)
  Then response.operator_count = 1
  And response.required_min = 2 (Class III)
  And response.gate_pass = false
  And IMM-04 block Submit với reason "BR-06-07: Cần ≥2 operator competent..."
```

### US-06-09 — Recertification Flow

```gherkin
As System,
60 ngày trước expiry, I tạo placeholder Training Session (Refresher),
So that Tổ HC-QLCL có sẵn task lập lịch.

Scenario: Auto recert reminder
  Given competency Active với recertification_due_date = today + 60d
  When scheduler check_recertification_due chạy
  Then nếu chưa có Refresher session Planned cho program/user trong 60d:
    Tạo IMM Training Session status="Planned", session_type="Refresher"
    Add user vào participants
  And email Tổ HC-QLCL "X người cần tái chứng nhận trong 60 ngày"
```

### US-06-10 — Revoke Competency

```gherkin
As Tổ HC-QLCL / CMMS Admin,
When phát hiện sai phạm vận hành dẫn tới incident,
I revoke competency với reason + CAPA link,
So that user lập tức mất quyền vận hành.

Scenario: Revoke với CAPA
  Given user có Active competency và liên quan tới Incident "INC-2026-0033"
  When tôi POST revoke_competency với
    {name, revoke_reason="Vi phạm quy trình vận hành — incident X",
     revoke_capa_ref="CAPA-2026-0011"}
  Then competency.status = "Revoked"
  And revoked_by, revoked_date set
  And IMM Audit Trail log "Revoke" với metadata
  And bất kỳ WO open nào assign cho user → flagged + email Workshop Head

Scenario: Revoke thiếu CAPA khi root cause là incident
  Given có incident liên quan
  When revoke với revoke_capa_ref empty
  Then VR-08 throw "Revoke do incident phải có CAPA reference"
```

### US-06-11 — Self-service portal

```gherkin
As Operator (Trainee),
I want xem hồ sơ năng lực của chính mình,
So that biết những thiết bị nào mình được phép vận hành + lịch tái chứng nhận.

Scenario: Xem competency
  Given tôi có 3 competency Active + 1 Expiring
  When GET get_user_competencies(user=session.user)
  Then trả về array 4 records
  And mỗi record có days_until_expiry, recertification_due_date
  And UI hiện badge cảnh báo cho Expiring
```

### US-06-12 — Gap Dashboard

```gherkin
As Workshop Head / VP Block2,
I want xem ma trận gap khoa × device class,
So that đánh giá rủi ro vận hành toàn viện.

Acceptance:
  KPI-01 % users competent per dept
  KPI-02 expiring within 90d count
  KPI-03 training completion rate (last 90d)
  KPI-04 average pass rate
  Matrix: rows=Department, cols=Device Class (II/III), cells=#competent / #required
  Click cell → list assets vi phạm BR-06-07
```

---

## 4. Business Rules

| ID | Rule | Enforce | Chuẩn |
|---|---|---|---|
| BR-06-01 | Operator chỉ được giao WO Class II/III nếu có Active competency cho device_model | `check_user_authorization` gọi từ IMM-08/09/12 | NĐ 98 §35 |
| BR-06-02 | Training session phải có instructor đủ qualification | `IMMTrainingSession.validate()` VR-04 | ISO 13485 §6.2 |
| BR-06-03 | Re-certification bắt buộc trước expiry — Expired → block tự động | Scheduler `auto_expire_competency` + BR-06-01 | WHO HTM |
| BR-06-04 | Program update nội dung trọng yếu → trigger re-cert toàn user | Hook `IMMTrainingProgram.on_update` | ISO 13485 §7.3 |
| BR-06-05 | Competency Active yêu cầu theory + practical score + supervisor sign-off | VR-06 + workflow gate | ISO 13485 §6.2 |
| BR-06-06 | Revoke yêu cầu lý do + CAPA nếu liên quan incident | VR-08 + `revoke_competency` API | ISO 13485 §8.5.2 |
| BR-06-07 | Class III asset → ≥ 2 operator Active per khoa | Weekly `generate_competency_gap_report` + IMM-04 gate | Internal SOP |
| BR-06-08 | Audit trail mọi thay đổi (status/expiry/sign-off/revoke) | Frappe Version + IMM Audit Trail | ISO 13485 §4.2.5 |
| BR-06-09 | Không xóa cứng competency — chỉ Suspended/Revoked | `on_trash()` throw | NĐ 98 |
| BR-06-10 | User đổi khoa → giữ competency, lưu `department_at_assessment` | Hook trên User update | Internal |
| BR-06-11 | Một user có thể nhiều competency level cho cùng device_model — chỉ giữ 1 Active | `archive_old_competency` trên on_update | Internal |
| BR-06-12 | Session đã Verified không thể Cancel — chỉ Closed | Workflow constraint | Internal |

---

## 5. Permission Matrix

| Action | Operator | HTM Tech | Biomed | Tổ HC-QLCL | Workshop Head | Clinical Head | Dept Manager | CMMS Admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Read own competency | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Read dept competencies | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ (own) | ✅ (own) | ✅ |
| Read all competencies | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Create Program | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Create Session | ❌ | ✅ (assist) | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Confirm Session | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Start Session (Instructor) | ❌ | ✅ (if instructor) | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Complete Session | ❌ | ❌ | ✅ (if instructor) | ✅ | ❌ | ❌ | ❌ | ✅ |
| Verify Session | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| Sign-off Competency | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ (own dept) | ✅ (own dept) | ✅ |
| Suspend | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Revoke | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Recertify | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |

---

## 6. Validation Rules

| VR ID | Field / Trigger | Rule | Error Message (vi) |
|---|---|---|---|
| VR-01 | `expiry_date`, `achieved_date` (Competency) | `expiry_date > achieved_date` | "VR-01: Ngày hết hạn phải sau ngày đạt năng lực." |
| VR-02 | `passing_score_pct` (Program) | `0 < x ≤ 100` | "VR-02: Điểm đạt phải trong khoảng 1-100." |
| VR-03 | `validity_period_months` (Program) | `1 ≤ x ≤ 60` | "VR-03: Hiệu lực phải trong khoảng 1-60 tháng." |
| VR-04 | `instructor` (Session) | Có role match `program.instructor_qualification_required` | "VR-04: Giảng viên không đủ điều kiện theo Program." |
| VR-05 | `participants` (Session) khi `workflow_state="Confirmed"` | Tối thiểu 1 participant | "VR-05: Phải có ít nhất 1 học viên trước khi xác nhận." |
| VR-06 | `theory_score`, `practical_score` (Participant) khi Session.complete | Cả 2 reqd nếu `program.assessment_method="Both"` | "VR-06: Vui lòng nhập điểm lý thuyết và thực hành." |
| VR-07 | `supervisor_signoff` khi Competency chuyển Active | reqd | "VR-07: Cần chữ ký của cán bộ giám sát trước khi kích hoạt." |
| VR-08 | `revoke_capa_ref` khi `revoke_reason` chứa keyword "incident"/"sự cố" | reqd | "VR-08: Thu hồi do sự cố vận hành phải có CAPA reference." |
| VR-09 | `attendance_pct` (Participant) | `0 ≤ x ≤ 100` | "VR-09: Tỷ lệ tham dự phải trong khoảng 0-100%." |
| VR-10 | `session_date` (Session) | `≥ today` khi tạo (nếu không phải backdate session) | "VR-10: Ngày training không được trong quá khứ (trừ trường hợp nhập lịch sử)." |
| VR-11 | `target_device_model` (Program) | Phải tồn tại và `is_active=1` | "VR-11: Model thiết bị không hợp lệ hoặc đã ngừng sử dụng." |
| VR-12 | `competency_level` (Competency) | IN {Trainee, Operator, Senior Operator, Trainer} và phù hợp `training_type` | "VR-12: Cấp độ năng lực không tương thích với loại đào tạo." |

---

## 7. Non-Functional Requirements

| ID | Category | Yêu cầu | Target |
|---|---|---|---|
| NFR-06-01 | Performance — list | `list_competencies` 5k records | P95 < 1.5s |
| NFR-06-02 | Performance — gate | `check_user_authorization` (called by WO) | P95 < 200ms (cached) |
| NFR-06-03 | Scheduler reliability | Idempotent | Competency Alert Log unique theo (competency, alert_date, milestone) |
| NFR-06-04 | Audit | Mọi action track | `track_changes=1` + IMM Audit Trail |
| NFR-06-05 | Availability | Giờ hành chính | 99.5% |
| NFR-06-06 | Data retention | Sau user nghỉ việc | ≥ 10 năm (NĐ98) |
| NFR-06-07 | i18n | Error messages | `frappe._()` tiếng Việt |
| NFR-06-08 | API contract | Response chuẩn | `_ok()` / `_err()` |
| NFR-06-09 | Concurrent users | Đồng thời | 50 users |
| NFR-06-10 | Notification SLA | Email expiry | Gửi trong 1h sau scheduler tick |
| NFR-06-11 | Self-service portal | Mobile responsive | < 768px hoạt động đầy đủ |
| NFR-06-12 | Bulk operations | Add 100 participants | < 5s |

---

## 8. End-to-End Flows

### 8.1 Flow A — New device commissioning với operator training

```
[IMM-04 GW-1 Commissioning Initiated]
        │
        ▼
[Tổ HC-QLCL tạo Training Program TRN-X-INIT-01]   (US-06-01)
        │
        ▼
[Schedule Session với 5 operator]                   (US-06-02)
        │
        ▼
[Confirmed → In Progress → Completed]               (US-06-03 → 04)
        │
        ▼
[5 Pending Assessment Competency tự sinh]
        │
        ▼
[Department Manager sign-off → 5 Active]            (US-06-05)
        │
        ▼
[IMM-04 GW-2 Clinical_Release: get_asset_operator_coverage(asset)
 → operator_count=5, required_min=2 → gate_pass=true]
        │
        ▼
[Asset commissioned LIVE]
```

### 8.2 Flow B — Recertification cycle

```
[Active Competency expiry_date = T]
        ▼
T-90: scheduler check_competency_expiry → status="Expiring", email Info
T-60: idem → email Warning + auto-create Refresher Session (Planned)
T-30: idem → email Critical, escalate Workshop Head
T+0:  scheduler auto_expire_competency → status="Expired"
        │
        ▼
[User mất quyền — IMM-08/09/12 không cho assign WO]
        │
        ▼
[Tổ HC-QLCL chạy Refresher Session]
        │
        ▼
[Pass → tạo Competency mới (BR-06-11 archive cũ) → Active]
```

### 8.3 Flow C — Revoke do incident

```
[Incident IMM-10 INC-2026-0033 root cause = operator error]
        ▼
[CAPA-2026-0011 mở, action item = "thu hồi competency user X"]
        ▼
[Tổ HC-QLCL: revoke_competency(name, reason, capa_ref=CAPA-2026-0011)]  (US-06-10)
        ▼
[VR-08 pass → status="Revoked", revoked_by, revoked_date set]
        ▼
[Audit Trail log; mọi WO open assign user X → flagged]
        ▼
[Workshop Head review → reassign WO]
```

---

## 9. Acceptance Criteria

Tổng hợp scenarios chính (chi tiết tại UAT Script):

| ID | Scenario | Pass criterion |
|---|---|---|
| AC-01 | Tạo Program hợp lệ | Program saved, code đúng |
| AC-02 | Schedule Session với participants | Session "Planned" + naming series đúng |
| AC-03 | Complete Session → auto-create Competency | N người Pass → N Competency "Pending Assessment" |
| AC-04 | Sign-off Active | Workflow chuyển, expiry_date computed đúng |
| AC-05 | Scheduler 90/60/30 alert | Status "Expiring" + Alert Log idempotent |
| AC-06 | Auto-expire | Status "Expired" khi past due |
| AC-07 | check_user_authorization gate | true cho user Active, false cho Expired/Revoked/None |
| AC-08 | get_asset_operator_coverage | Class III thiếu → gate_pass=false |
| AC-09 | Revoke với CAPA | Pass; thiếu CAPA khi keyword incident → VR-08 throw |
| AC-10 | Self-service portal | User chỉ thấy competency của chính mình |
| AC-11 | Gap report weekly | Mỗi Mon 02:00 sinh report mới |
| AC-12 | BR-06-04 program update trigger re-cert | Tạo placeholder session cho mọi user |

---

## 10. Glossary

| Thuật ngữ | Nghĩa |
|---|---|
| Training Program | Chương trình đào tạo chuẩn (curriculum) cho 1 device model/category |
| Training Session | Sự kiện đào tạo cụ thể đã/đang/sẽ tổ chức |
| Competency | Năng lực đã đạt của 1 user × 1 device model |
| Recertification | Tái chứng nhận định kỳ trước khi competency hết hạn |
| Sign-off | Phê duyệt cuối cùng của supervisor để competency chuyển Active |
| Coverage | Số operator competent per asset/department — chỉ số redundancy |
| Gap Report | Báo cáo khoa × class còn thiếu năng lực |
| Authorization Gate | API `check_user_authorization` chặn assign WO khi user không đủ năng lực |
| Validity Period | Số tháng hiệu lực của competency tính từ achieved_date |
| Refresher | Loại training_type tái đào tạo (không cần học lại từ đầu) |
