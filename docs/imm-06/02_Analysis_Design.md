# 02 — Phân tích thiết kế nghiệp vụ — IMM-06 Đào tạo & Quản lý năng lực

| Mục | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phạm vi | Per-module |
| Owner | BA + System Analyst |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |
| Chuẩn tham chiếu | ISO 13485:2016 §6.2, WHO HTM Annex 5, NĐ 98/2021/NĐ-CP §35 |

> ⚠️ Module PLANNED — Wave 2. Chưa triển khai. Tài liệu này là thiết kế spec.

---

# Phần I — Module Overview

## I.0. Khảo sát hiện trạng (As-Is)

Tại các bệnh viện Khối 2 hiện nay, hồ sơ đào tạo & năng lực vận hành thiết bị y tế Class II/III được quản lý **ngoài hệ thống**:

- **Excel + sổ giấy**: Tổ HC-QLCL lưu danh sách training session, attendance, điểm số trong file Excel; certificate giấy ký tay → cất tủ. Không truy vết được "tại thời điểm T, user X đã/chưa có competency cho thiết bị Y" một cách định lượng.
- **Email + Google Calendar**: Lịch training session phát qua email; reminder thủ công; không có cơ chế nhắc tái chứng nhận trước expiry. Khi Workshop Lead phân công Work Order (PM/CM/Calibration), không có gate kiểm tra năng lực — phụ thuộc trí nhớ của trưởng phân xưởng.
- **Mất kết nối với clinical release**: IMM-04 (Commissioning) hiện không thể "khóa" Clinical Release theo điều kiện đủ operator competent — vì không có nguồn dữ liệu năng lực tin cậy để gate.
- **Không có audit trail khi thu hồi**: Khi xảy ra incident do operator error, việc "thu hồi quyền vận hành" của user X chỉ là quyết định miệng; không có bản ghi pháp lý đối chiếu khi thanh tra Sở Y tế (NĐ 98 §35).

**Bảng so sánh As-Is vs To-Be (IMM-06):**

| Khía cạnh | As-Is (Excel + giấy) | To-Be (IMM-06) |
|---|---|---|
| Curriculum | File Word/PDF rời rạc | DocType `IMM Training Program` versioned, gắn `target_device_model` |
| Session schedule | Email + Google Calendar | DocType `IMM Training Session` workflow 7 states, audit-able |
| Attendance & điểm | Excel | Child table `IMM Training Participant`, auto Pass/Fail |
| Certificate | PDF/giấy ký tay | DocType `IMM User Competency` workflow 6 states, e-trace |
| Cảnh báo hết hạn | Không có | Scheduler T-90/-60/-30/0d, idempotent alert log |
| Authorization gate | Quyết định miệng | API `check_user_authorization` cached 5 min, P95<200ms |
| Thu hồi sau incident | Không bản ghi | API `revoke_competency` + CAPA link bắt buộc (VR-08) |
| Gap report | Thủ công | Scheduler weekly, ma trận department × device class |

**Nguồn dữ liệu khảo sát**: phỏng vấn Tổ HC-QLCL, Workshop Lead, Department Manager tại bệnh viện pilot; audit file Excel hiện hành; đối chiếu sổ ký nhận đào tạo nội viện.

## I.1. Pitch

Thiết bị y tế Class II/III tại bệnh viện hiện chỉ được vận hành bởi người được đào tạo có chứng nhận theo NĐ 98 §35 và WHO HTM, nhưng toàn bộ hồ sơ đào tạo và năng lực đang nằm ngoài hệ thống — file Excel, sổ giấy, email — không truy vết, không cảnh báo hết hạn, không thể gate được Work Order. IMM-06 chuyển toàn bộ vòng đời đào tạo & năng lực vào AssetCore: từ thiết kế curriculum → tổ chức training session → chấm điểm → cấp năng lực → cảnh báo hết hạn → tái chứng nhận → thu hồi khi sự cố. Module bảo đảm: *"Người dùng đủ năng lực trước khi vận hành, có tái đào tạo định kỳ và kiểm soát quyền sử dụng theo trạng thái competency."*

## I.2. Vị trí trong WHO HTM lifecycle

| Phase | Chạm? | Ghi chú |
|---|---|---|
| Needs | — | — |
| Procurement | — | — |
| Install | ✅ | Cần operator competent trước commissioning (IMM-04 gate) |
| **Operation** | ✅ **chính** | Training & Competence (HTM 4.4) — gate cho clinical use |
| **Maintenance** | ✅ | Validate technician trước assign WO (IMM-08/09/12) |
| Decommission | — | — |

**Wave 2 — PLANNED.** Chạy ngay sau IMM-05 (Registration) và trước IMM-04 Clinical Release. Tiếp tục theo dõi xuyên suốt vòng đời vận hành.

Input: Device Model (master), User (nhân sự), Incident Report (IMM-10 trigger CAPA → revoke).
Output: IMM User Competency (hồ sơ năng lực), IMM Competency Gap Report, Authorization gate kết quả cho IMM-04/08/09/12.

## I.3. Stakeholders & Actors

| Actor | Vị trí thực tại BV | Quyền chính | Trách nhiệm |
|---|---|---|---|
| Tổ HC-QLCL (IMM Training Officer) | Tổ HC-QLCL — Owner module | R/W/C, Approve, Cancel, Revoke | Quản lý curriculum, schedule, đánh giá, revoke |
| IMM Workshop Lead | Trưởng Phân xưởng | R/W, Verify, Sign-off, Suspend/Revoke | Verify session; sign-off competency; nhận escalation |
| IMM Biomed Technician | Kỹ sư Biomedical | R/W/C training | Instructor training kỹ thuật; xem competency để assign WO |
| HTM Technician | KTV HTM | R/W (own session) | Tham gia training; có thể instructor cấp 1 |
| Trainee / Operator | Bác sĩ, điều dưỡng, KTV vận hành | R (own competency) | Tham gia training; xem chứng nhận |
| Clinical Head | Trưởng Khoa lâm sàng | R (own dept) | Xem competency khoa mình; nhận gap report |
| Department Manager | Trưởng phòng/khoa hành chính | R/W (sign-off own staff) | Sign-off competency cho cán bộ thuộc khoa |
| VP Block2 | Phó Khối 2 | R, nhận escalation | Nhận gap report toàn viện; phê duyệt ngoại lệ |
| IMM System Admin | IT / CMMS | Full | Quản trị, override |
| System (Scheduler) | — | system-only | Auto-Expiring, auto-Expired, gap report, recert reminder |

## I.4. Scope

**In-scope:**
- 6 DocTypes: IMM Training Program, IMM Training Session, IMM Training Participant (child), IMM User Competency, IMM Competency Gap Report, IMM Competency Alert Log
- 2 Workflow: Session (7 states), Competency (6 states)
- 19 REST endpoints
- 12 Business Rules (BR-06-01 → BR-06-12), 12 Validation Rules (VR-01 → VR-12)
- 4 Scheduler jobs: check_competency_expiry (daily 02:00), auto_expire_competency (daily 02:30), check_recertification_due (daily 03:00), generate_competency_gap_report (weekly Mon 02:00)
- Service layer `services/imm06.py` — xây mới hoàn toàn
- Frontend: 14 routes Vue 3 + Pinia store `imm06Store.ts`
- Authorization gate cho IMM-04 (Clinical Release), IMM-08/09/11/12 (WO assign)
- Gap report weekly — ma trận department × device class

**Out-of-scope:**
- LMS (e-learning, video delivery) — hệ thống LMS riêng; IMM-06 chỉ ghi nhận hoàn thành
- Quản lý ngân sách đào tạo — Tài chính (out-of-system)
- Đánh giá hiệu suất công việc tổng thể (HR system)
- E-signature số trên certificate (Wave 3)
- `AC Authorized Technician` (child `AC Supplier`) — vendor-side, thuộc IMM-03

**Dependencies:**
- IMM-04: Clinical Release gate gọi `compute_operator_coverage(asset)`
- IMM-05: Certificate file lưu qua Asset Document `doc_category=Training`
- IMM-08/09/11/12: `validate_user_authorization(user, device_model)` trước assign WO
- IMM-10 (Wave 3): CAPA action item → trigger revoke
- IMM Audit Trail (cross-cutting), AC Asset, AC Department (reuse)

> *I.5 KPI mục tiêu* và *I.6 Ràng buộc Compliance* — **chuyển sang `_REPORT.md`** (yêu cầu workshop BA để chốt baseline + trace mapping NĐ98/WHO HTM/ISO 13485 cho từng KPI). Light-touch không tự sinh số liệu.

## I.7. Risk & Open questions

**Bảng Risk (theo light-touch — chỉ liệt kê risk có cơ sở từ scope đã chốt):**

| # | Risk | Likelihood | Impact | Giảm thiểu |
|---|---|---|---|---|
| R-06-01 | Authorization gate (`check_user_authorization`) bị gọi tần suất cao (mỗi assign WO) → DB bottleneck | High | High | Cache 5-min TTL theo (user, device_model); invalidate khi competency thay đổi (NFR-06-02) |
| R-06-02 | Scheduler `auto_expire_competency` chạy đúng T+0 nhưng email gateway chậm → user không biết đã mất quyền, vẫn cố vận hành | Medium | High | Gate là DB status — không phụ thuộc email. Email chỉ là kênh nhắc thứ cấp; UI portal cập nhật realtime |
| R-06-03 | Department Manager không sign-off kịp → competency mắc kẹt ở `Pending Assessment`, gate IMM-04 không pass | Medium | Medium | Reminder email theo SLA 3 ngày; escalate Workshop Lead sau 7 ngày |
| R-06-04 | BR-06-04 (program thay đổi nội dung trọng yếu → re-cert hàng loạt) gây sốc operations nếu trigger không kiểm soát | Low | High | Thay đổi `content_outline` đi qua workflow Approve riêng của Program; chỉ trigger re-cert sau khi Workshop Lead duyệt |
| R-06-05 | Class III asset thiếu redundancy operator (BR-06-07) ở các khoa nhỏ — block IMM-04 Clinical Release vô thời hạn | Medium | High | Cho phép VP Block2 override với `risk_acceptance_note` (audit trail); kèm action item HC-QLCL train thêm operator |

**Open questions (cần workshop BA):**

| # | Open question | Owner | Deadline |
|---|---|---|---|
| OQ-06-01 | Định nghĩa "competent" cho mỗi `device_model` — passing_score_pct chuẩn (70? 80?) khác nhau theo Class? | Tổ HC-QLCL + Workshop Lead | Trước Wave 2 sprint 1 |
| OQ-06-02 | Thời hạn `validity_period_months` mặc định cho từng nhóm thiết bị (Class II vs III, vendor-trained vs in-house)? | HC-QLCL + Block 2 | Trước Wave 2 sprint 1 |
| OQ-06-03 | Có cấp competency theo `serial` (per-asset) hay chỉ theo `device_model`? Ảnh hưởng đến gate IMM-08/09/12. | Workshop Lead | Trước Wave 2 sprint 2 |
| OQ-06-04 | Quy tắc phân quyền sign-off khi user thuộc 2 khoa (rotate / kiêm nhiệm)? | HR + HC-QLCL | Trước Wave 2 sprint 2 |
| OQ-06-05 | Có tích hợp e-signature / chứng chỉ số ngay Wave 2 không (hay đẩy Wave 3)? | IT + QLCL | Wave-planning |

## I.8. Roadmap thực thi

> *Sprint plan dự kiến — chốt chi tiết tại workshop BA Wave 2.*

| Sprint | Hạng mục | Owner | Status |
|---|---|---|---|
| W2-S1 | Scaffold 6 DocType + 2 Workflow JSON; fixture role + permission | BE + Doctype Designer | Planned |
| W2-S2 | Service `services/imm06.py` — curriculum + session + competency core; 19 endpoint API skeleton | BE module | Planned |
| W2-S3 | Authorization gate (`check_user_authorization`) + cache layer; hook IMM-08/09/11/12 + IMM-04 Clinical Release | BE + Integration | Planned |
| W2-S4 | 4 Scheduler job (expiry, auto-expire, recert, gap report); IMM Competency Alert Log idempotent | BE | Planned |
| W2-S5 | Frontend 14 routes (admin + self-service portal); Pinia store `imm06Store.ts`; mobile responsive | FE module | Planned |
| W2-S6 | UAT script (10 scenario) + security review (DocPerm, permlevel, RBAC); training Tổ HC-QLCL | QA + HC-QLCL | Planned |
| W2-S7 | Pilot deploy 1 bệnh viện; thu thập baseline KPI (đầu vào cho I.5 — workshop BA chốt số liệu thật) | DevOps + BA | Planned |

---

# Phần II — Quy trình nghiệp vụ (BPMN)

## II.1. Flow A — New device commissioning với operator training

```
[IMM-04 GW-1: Commissioning Initiated]
        │
        ▼
[Tổ HC-QLCL tạo Training Program TRN-X-INIT-01]   (US-06-01)
        │
        ▼
[Schedule Training Session với N operator]          (US-06-02)
        │
        ▼
[Planned → Confirmed → In Progress → Completed]    (US-06-03 → 04)
│   Instructor nhập điểm theory + practical + attendance
│   System tính Pass/Fail per participant
        │
        ▼
[N Pass → N IMM User Competency (Pending Assessment) tự sinh]
        │
        ▼
[Department Manager / Workshop Head sign-off]       (US-06-05)
        │  Validate VR-07, set expiry_date = achieved + validity_months
        ▼
[N Competency → Active]
        │
        ▼
[IMM-04 GW-2 "Clinical Release":
 get_asset_operator_coverage(asset)
 → operator_count >= required_min → gate_pass = true]
        │
        ▼
[Asset commissioned LIVE — người dùng được phép vận hành]
```

**Swim-lane:** Tổ HC-QLCL (curriculum + schedule) | Instructor (chấm điểm) | Department Manager (sign-off) | IMM-04 Controller (gate) | System (auto-create competency, email)

## II.2. Flow B — Recertification cycle

```
[Active Competency — expiry_date = T]
        │
T−90d: scheduler check_competency_expiry
        → status = "Expiring"
        → tạo IMM Competency Alert Log (idempotent)
        → email User + Supervisor (Info)
        │
T−60d: idem
        → email User + Workshop Head (Warning)
        → nếu chưa có Refresher Session Planned:
            services.imm06.trigger_recertification(comp.name)
            → tạo IMM Training Session Planned
        │
T−30d: idem
        → email Critical, escalate Workshop Head
        │
T+0:  scheduler auto_expire_competency
        → status = "Expired"
        → invalidate_authorization_cache
        → email "Năng lực đã hết hạn" → User, Workshop Head
        │
[User mất quyền — IMM-08/09/12 không cho assign WO]
        │
[Tổ HC-QLCL chạy Refresher Session đã tạo sẵn]
        │
[Pass → Competency mới (BR-06-11: archive cũ) → sign-off → Active]
```

**Decision points:**
- T−60d: có Refresher Session Planned chưa? Nếu rồi → chỉ gửi reminder, không tạo duplicate
- T+0: scheduler idempotent — không auto-Expired nếu đã có status khác (Revoked/Suspended)

## II.3. Flow C — Revoke do incident

```
[Incident IMM-10: INC-2026-0033 root cause = operator error]
        │
        ▼
[CAPA-2026-0011 mở — action item: "thu hồi competency user X"]
        │
        ▼
[Tổ HC-QLCL: POST revoke_competency
 {name, revoke_reason="Vi phạm quy trình — incident X",
  revoke_capa_ref="CAPA-2026-0011"}]    (US-06-10)
        │
        ▼
[VR-08: keyword check pass (CAPA ref provided)]
        │
        ▼
[status = "Revoked", revoked_by, revoked_date set
 invalidate_authorization_cache
 IMM Audit Trail log action="REVOKE"]
        │
        ▼
[WO open assign cho user X → flagged + email Workshop Head]
        │
        ▼
[Workshop Head review → reassign WO sang KTV khác]
        │
        ▼
[User cần tái đào tạo từ đầu — mở Training Session mới (không tự động)]
```

---

# Phần III — Use Case Specification

## III.1. Use Case Stories (Gherkin format)

### US-06-01 — Tạo Training Program (curriculum)

```gherkin
As Tổ HC-QLCL,
I want tạo Training Program cho 1 Device Model,
So that mọi training session sau này tham chiếu chuẩn đúng.

Scenario: Tạo program hợp lệ
  Given tôi có role "IMM Training Officer" và Device Model "MDL-MON-PHILIPS-X3" tồn tại
  When tôi POST create_program với
    {program_code="TRN-MON-INIT-01", program_name="Đào tạo cơ bản Monitor Philips X3",
     target_device_model="MDL-MON-PHILIPS-X3", training_type="Initial",
     duration_hours=8, validity_period_months=24, passing_score_pct=70,
     assessment_method="Both", instructor_qualification_required="Biomed Engineer"}
  Then response.success = true
  And program.name = "TRN-MON-INIT-01"
  And program.is_mandatory_for_operation = 1 (default cho Initial)

Scenario: VR-02 — điểm đạt ngoài khoảng hợp lệ
  Given tôi điền passing_score_pct = 110
  When tôi POST create_program
  Then response.success = false
  And response.error contains "VR-02: Điểm đạt phải trong khoảng 1-100"
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
  And session.name khớp regex "^TRN-2026-\d{5}$"
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
As Instructor (IMM Biomed Technician),
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
As Department Manager / IMM Workshop Lead,
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
  And email "Năng lực đã hết hạn" gửi user, IMM Workshop Lead
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

### US-06-08 — Operator Coverage Gate (IMM-04 Clinical Release)

```gherkin
As IMM-04 controller,
When commissioning chuyển sang Clinical Release,
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
As Tổ HC-QLCL / IMM System Admin,
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
  And bất kỳ WO open nào assign cho user → flagged + email IMM Workshop Lead

Scenario: Revoke thiếu CAPA khi root cause là incident
  Given có incident liên quan
  When revoke với revoke_capa_ref empty
  Then VR-08 throw "VR-08: Thu hồi do sự cố vận hành phải có CAPA reference"
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
As IMM Workshop Lead / VP Block2,
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

# Phần IV — Functional Requirements

## IV.1. Business Rules

| ID | Business Rule | Enforce | Chuẩn |
|---|---|---|---|
| BR-06-01 | Operator chỉ được giao WO vận hành Class II/III nếu có Active competency cho `device_model` của Asset; áp dụng IMM-08/09/11/12 | `check_user_authorization()` gọi từ controller WO tương ứng; trả `FORBIDDEN` | NĐ 98 §35 |
| BR-06-02 | Mọi training session phải có instructor đủ qualification (validate theo `program.instructor_qualification_required`) | `IMMTrainingSession.validate()` — VR-04 | ISO 13485 §6.2 |
| BR-06-03 | Re-certification bắt buộc trước expiry — Expired → block tự động không thể assign WO | Scheduler `auto_expire_competency` + BR-06-01 | WHO HTM |
| BR-06-04 | Khi Training Program thay đổi nội dung trọng yếu (`content_outline`, `passing_score_pct`, `assessment_method`, `duration_hours`) → trigger re-cert cho mọi user cùng program | Hook `IMMTrainingProgram.on_update` so sánh field → tạo flag / Document Request task | ISO 13485 §4.1.4, §7.3 |
| BR-06-05 | Mỗi participant phải có theory + practical score và supervisor sign-off trước khi competency Active | `IMMUserCompetency.validate()` — VR-06; workflow transition Pending Assessment → Active gated | ISO 13485 §6.2 |
| BR-06-06 | Competency revoke yêu cầu lý do (≥30 ký tự) + CAPA link nếu liên quan incident | `revoke_competency` API — VR-08; nếu `revoke_capa_ref` empty và reason chứa keyword → throw | ISO 13485 §8.5.2 |
| BR-06-07 | Asset Class III → tối thiểu 2 operator có Active competency tại khoa sử dụng (redundancy) | `generate_competency_gap_report` weekly + IMM-04 Clinical Release gate qua `get_asset_operator_coverage` | Internal SOP |
| BR-06-08 | Audit trail mọi thay đổi competency (status, expiry, sign-off, revoke) | Frappe `track_changes=1` + `IMM Audit Trail` log custom cho revoke/suspend | ISO 13485 §4.2.5 |
| BR-06-09 | Không xóa cứng competency record (kể cả expired) — chỉ cho phép Suspended/Revoked | `on_trash()` throw | NĐ 98 |
| BR-06-10 | Khi user thay đổi khoa (department) → competency vẫn giữ nguyên nhưng `department_at_assessment` lưu lại; gap report tính lại | Hook trên User update (`handle_user_dept_change`) | Internal |
| BR-06-11 | Một user có thể nhiều competency cho cùng device_model — chỉ giữ 1 Active (mới active → archive cũ) | `archive_old_competency()` trong `signoff_competency` | Internal |
| BR-06-12 | Session đã Verified không thể Cancel — chỉ Closed | Workflow constraint + API `cancel_session` check | Internal |
| BR-06-13 | `recertification_due_date` tính từ **DUY NHẤT 1 SoT** `compute_competency_dates(achieved_date, validity_months)` — INVARIANT `= expiry_date − 60 ngày`. Mọi write-site (creation / signoff / before_save / recertify / compute hooks) gọi chung SoT; cùng input → cùng recert date bất kể code path (idempotent). Cấm inline `add_days(expiry,-60)` hay `add_months(achieved, validity-2)` ngoài SoT. | `compute_competency_dates()` trong `services/imm06.py`; grep guard 0 literal; scheduler `check_recertification_due` lọc theo recert date này | WHO HTM (lead-time tái chứng nhận) |
| BR-06-14 | Trạng thái **"Sắp hết hạn" / "Đã hết hạn"** của năng lực là **predicate LIVE date-derived DUY NHẤT** (không phải cờ `workflow_state` thuần). INVARIANT: `expiring(c) ⟺ workflow_state ∈ {Active, Expiring} ∧ expiry_date ∈ [today, today+EXPIRY_WINDOW_DAYS]` và `expired(c) ⟺ workflow_state ∈ {Active, Expiring, Expired} ∧ expiry_date < today`; `EXPIRY_WINDOW_DAYS=60` (khớp default `get_expiring_competencies`). Hai helper `_expiring_competency_filter()` / `_expired_competency_filter()` là SoT chung cho **CẢ** KPI count (`get_dashboard_stats`) **LẪN** drill list (`get_expiring_competencies`) — KHÔNG đếm `frappe.db.count(workflow_state==Expiring/Expired)` thuần. Đo được: `kpis.competencies.expiring == len(get_expiring_competencies(60))` với MỌI tập dữ liệu (card == drill). Revoked/Suspended KHÔNG bao giờ bị đếm. Scheduler `check_expiring_competencies` / `auto_expire_competencies` GIỮ NGUYÊN (vẫn stamp `workflow_state` phục vụ workflow + alert log + auth-cache invalidate). | `_expiring_competency_filter()` / `_expired_competency_filter()` trong `services/imm06.py`; `get_dashboard_stats().competencies.{expiring,expired}` + `get_expiring_competencies()` cùng dùng; test invariant card==drill | NĐ 98 §35 (operator-competency phải LIVE — hết hạn không được hiển thị "Đang hiệu lực") |

> **Self-Correction 2026-06-03 (Vòng 22):** lỗi gốc — 2 công thức recert song song (A: expiry−60d; B: achieved+(validity−2)tháng) lệch 1–2 ngày → scheduler eligibility lệch theo code path. Chốt SoT "expiry − 60 ngày" (khớp filter `add_days(nowdate(),60)`). Chi tiết 6 write-site: `04_Backend_Design.md §V.1`.

> **Self-Correction 2026-06-04 (Vòng 20):** lỗi gốc — **count-vs-drill divergence** (BR-06-14). KPI tile "Sắp hết hạn"/"Đã hết hạn" của `get_dashboard_stats` đếm theo cờ `workflow_state==Expiring/Expired` thuần (scheduler chỉ stamp đúng mốc 60/30 ngày & quá-hạn), trong khi drill `get_expiring_competencies` lọc LIVE `Active/Expiring ∧ expiry_date∈[today,today+60]` → **tile lệch list**. Hậu quả: (a) năng lực `expiry_date` trong 45 ngày (chưa trúng mốc 60/30 nên scheduler chưa stamp `Expiring`) bị **undercount** khỏi tile nhưng lại xuất hiện trong drill; (b) năng lực `expiry_date < today` mà scheduler `auto_expire_competencies` lỡ phiên (vẫn `Active`) bị **undercount** khỏi "Đã hết hạn" — operator quá hạn vẫn hiển thị "Đang hiệu lực" → **rủi ro NĐ98** (giao WO vận hành cho người chưa tái chứng nhận). Chốt SoT LIVE date-derived (2 helper dùng chung KPI + drill). Scheduler KHÔNG đụng — chỉ KPI/drill chuyển sang predicate live. Chi tiết: `04_Backend_Design.md §V.2`.

## IV.2. Validation Rules

| VR ID | Field / Trigger | Rule | Error Message (vi) |
|---|---|---|---|
| VR-01 | `expiry_date`, `achieved_date` (Competency) | `expiry_date > achieved_date` | "VR-01: Ngày hết hạn phải sau ngày đạt năng lực." |
| VR-02 | `passing_score_pct` (Program) | `0 < x ≤ 100` | "VR-02: Điểm đạt phải trong khoảng 1-100." |
| VR-03 | `validity_period_months` (Program) | `1 ≤ x ≤ 60` | "VR-03: Hiệu lực phải trong khoảng 1-60 tháng." |
| VR-04 | `instructor` (Session) | Có role match `program.instructor_qualification_required` | "VR-04: Giảng viên không đủ điều kiện theo Program." |
| VR-05 | `participants` (Session khi `workflow_state="Confirmed"`) | Tối thiểu 1 participant | "VR-05: Phải có ít nhất 1 học viên trước khi xác nhận." |
| VR-06 | `theory_score`, `practical_score` (Participant khi Session.complete) | Cả 2 reqd nếu `program.assessment_method="Both"` | "VR-06: Vui lòng nhập điểm lý thuyết và thực hành." |
| VR-07 | `supervisor_signoff` khi Competency chuyển Active | reqd | "VR-07: Cần chữ ký của cán bộ giám sát trước khi kích hoạt." |
| VR-08 | `revoke_capa_ref` khi `revoke_reason` chứa keyword "incident"/"sự cố"/"tai nạn"/"sai phạm" | reqd | "VR-08: Thu hồi do sự cố vận hành phải có CAPA reference." |
| VR-09 | `attendance_pct` (Participant) | `0 ≤ x ≤ 100` | "VR-09: Tỷ lệ tham dự phải trong khoảng 0-100%." |
| VR-10 | `session_date` (Session on create) | `≥ today` (trừ flag `is_backdated=1` cho nhập lịch sử) | "VR-10: Ngày training không được trong quá khứ (trừ trường hợp nhập lịch sử)." |
| VR-11 | `target_device_model` (Program) | Phải tồn tại và `is_active=1` | "VR-11: Model thiết bị không hợp lệ hoặc đã ngừng sử dụng." |
| VR-12 | `competency_level` (Competency) | IN {Trainee, Operator, Senior Operator, Trainer} và phù hợp `training_type` | "VR-12: Cấp độ năng lực không tương thích với loại đào tạo." |

---

# Phần V — Non-Functional Requirements

| ID | Category | Yêu cầu | Target |
|---|---|---|---|
| NFR-06-01 | Performance — list | `list_competencies` với 5k records | P95 < 1.5s |
| NFR-06-02 | Performance — gate | `check_user_authorization` (high-frequency call từ WO) | P95 < 200ms (cached 5 min TTL) |
| NFR-06-03 | Scheduler reliability | Idempotent — không tạo trùng alert | Competency Alert Log unique theo (competency, alert_date, milestone) |
| NFR-06-04 | Audit | Mọi action có record | `track_changes=1` + IMM Audit Trail cho revoke/suspend/sign-off |
| NFR-06-05 | Availability | Giờ hành chính | 99.5% uptime |
| NFR-06-06 | Data retention | Sau user nghỉ việc | ≥ 10 năm (NĐ 98) |
| NFR-06-07 | i18n | Error messages | `frappe._()` tiếng Việt — FE hiển thị trực tiếp `response.error` |
| NFR-06-08 | API contract | Response chuẩn | `{"success": true, "data": {...}}` / `{"success": false, "error": "...", "code": "..."}` |
| NFR-06-09 | Concurrent users | Đồng thời | 50 concurrent users |
| NFR-06-10 | Notification SLA | Email expiry | Gửi trong 1 giờ sau scheduler tick |
| NFR-06-11 | Self-service portal | Mobile responsive | < 768px hoạt động đầy đủ (operator xem hồ sơ trên điện thoại) |
| NFR-06-12 | Bulk operations | Add 100 participants vào session | < 5s |
