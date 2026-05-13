# IMM-06 — User Training & Competency Management

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — Đào tạo người dùng & Quản lý năng lực |
| Phiên bản | 0.3 — re-aligned via WAVE2_ALIGNMENT_BLOCK23 |
| Ngày cập nhật | 2026-05-05 |
| **Source of truth** | **`docs/WAVE2_ALIGNMENT_BLOCK23.md` v1.0.0 — đọc trước**. Ghi đè: naming series là **mã dữ liệu domain** (`TRN-…`, `COMP-…`, `GAP-…` — KHÔNG nhúng số module); Frappe Role names (`IMM Training Officer` thay "Tổ HC-QLCL"); gate IMM-04 ở transition `commissioned→activated` (không có "Clinical_Release" trong Asset Lifecycle Event); patches `v3_2.00x`. |
| Alignment note | `AC Authorized Technician` (child của `AC Supplier`) là vendor-side authorized technician dùng cho IMM-03 (AVL/contract) — **out of scope** của IMM-06. IMM-06 quản lý đào tạo & năng lực của **nhân sự nội bộ** (operator, KTV HTM, biomed engineer) sử dụng/vận hành thiết bị. |
| Trạng thái | PLANNED — chưa implement (Wave 2 / Block 2 — Deployment & Implementation) |
| Tác giả | AssetCore Team |
| Owner nghiệp vụ | Tổ HC-QLCL & Risk + Workshop (Phân xưởng) |

---

## 1. Mục đích

IMM-06 là **lớp kiểm soát năng lực vận hành** trong vòng đời WHO HTM. Module bảo đảm:

> *"Người dùng đủ năng lực **trước khi vận hành**, có **tái đào tạo định kỳ** và **kiểm soát quyền sử dụng** theo trạng thái competency."*

**Đặc điểm:**

| Đặc tính | Nội dung |
|---|---|
| Vai trò trong WHO HTM | Training & competence (HTM 4.4 — Operation phase) — gate cho clinical use |
| Vị trí lifecycle | Block 2 (Deployment) — chạy ngay sau IMM-05 (Registration) và trước IMM-04 Clinical_Release; tiếp tục theo dõi xuyên suốt vận hành |
| Liên kết module | Là **gate điều kiện** cho IMM-04 (Clinical_Release ≥N operator competent), IMM-08 (PM technician), IMM-09 (Repair), IMM-12 (Corrective) |
| Compliance | ISO 13485:2016 §6.2 (Competence/Awareness/Training), WHO HTM Annex 5, NĐ 98/2021/NĐ-CP §35 |
| Phạm vi audit | Mọi training session, đánh giá, cấp/thu hồi competency phải có record + audit trail |

**Tại sao bắt buộc?**

Theo NĐ 98 §35 và WHO HTM, *"thiết bị y tế Class II/III chỉ được vận hành bởi người đã được đào tạo có chứng nhận"*. Trước IMM-06, năng lực người dùng được quản lý ngoài hệ thống (file Excel, sổ giấy) → không truy vết, không cảnh báo hết hạn, không gate được Work Order. IMM-06 chuyển toàn bộ vào hệ thống AssetCore.

### 1.1 Phạm vi thay đổi vs hệ thống hiện tại

- **Đã có (reuse, không sửa):** `AC Authorized Technician` (child của `AC Supplier`) — danh sách KTV được vendor uỷ quyền (vendor-side), thuộc IMM-03 AVL/contract; **độc lập** với IMM-06 (IMM-06 quản lý đào tạo nhân sự **nội bộ** vận hành/sử dụng thiết bị, không phải vendor tech). `IMM Audit Trail` (cross-cutting, reuse). `AC Asset`, `AC Department` (reuse cho Link references trong Competency / Participant / Gap Report).
- **Thêm mới hoàn toàn:** `IMM Training Program`, `IMM Training Session`, `IMM Training Participant` (child), `IMM User Competency`, `IMM Competency Gap Report`, `IMM Expiry Alert Log`; `services/imm06.py`, `api/imm06.py`; 4 scheduler jobs trong `tasks.py`; 2 workflow JSON (Session, Competency).
- **Cross-module gate đã hỗ trợ:** `services/imm08.py`, `services/imm09.py`, `services/imm12.py` — IMM-06 sẽ thêm hook `validate_user_authorization` trong `before_assign_technician` của các Work Order service tương ứng (không sửa core, chỉ extend).

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│                  Frappe Framework v15                            │
│   Workflow Engine · User · Scheduler · ORM · Notification        │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                      AssetCore App                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │       IMM-06 User Training & Competency Management       │   │
│  │                                                          │   │
│  │  DocTypes:                                               │   │
│  │    • IMM Training Program       (master curriculum)      │   │
│  │    • IMM Training Session       (delivered event)        │   │
│  │    • IMM Training Participant   (child of Session)       │   │
│  │    • IMM User Competency        (per user × model)       │   │
│  │    • IMM Competency Gap Report  (auto, weekly)           │   │
│  │                                                          │   │
│  │  API:        assetcore/api/imm06.py  (~17 endpoints)     │   │
│  │  Controller: assetcore/.../doctype/imm_*/...py           │   │
│  │  Workflows:  workflow/imm_06_session_workflow.json       │   │
│  │              workflow/imm_06_competency_workflow.json    │   │
│  │  Scheduler:  tasks.py                                    │   │
│  │     • check_competency_expiry        daily 02:00         │   │
│  │     • auto_expire_competency         daily 02:30         │   │
│  │     • check_recertification_due      daily 03:00         │   │
│  │     • generate_competency_gap_report weekly Mon 02:00    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│   Tích hợp:                                                      │
│     IMM-04 ─▶ IMM-06  (commissioning yêu cầu ≥N operator competent)│
│     IMM-06 ─▶ IMM-04  (Clinical_Release gate qua check_user_authorization)│
│     IMM-06 ─▶ IMM-08/09/12  (validate technician trước assign WO)│
│     IMM-05 ◀─ IMM-06  (lưu certificate file dạng Asset Document) │
│     IMM-10 ─▶ IMM-06  (incident → trigger competency review/CAPA)│
│     IMM-16 ◀─ IMM-06  (compliance dashboard consume training %)  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Tổng quan

| DocType | Naming | Vai trò |
|---|---|---|
| IMM Training Program | `field:program_code` | Master curriculum — định nghĩa chương trình đào tạo cho 1 Device Model / Category |
| IMM Training Session | `TRN-.YYYY.-.#####` | Sự kiện đào tạo thực tế đã/đang/sẽ tổ chức |
| IMM Training Participant | child table | Học viên trong 1 session — điểm theory/practical, attendance, kết quả |
| IMM User Competency | `COMP-.YYYY.-.#####` | Hồ sơ năng lực: 1 user × 1 device_model — trạng thái Active/Expired/Suspended/Revoked |
| IMM Competency Gap Report | `GAP-.YYYY.-.#####` | Báo cáo auto-generated weekly — list khoa/asset thiếu operator |

### 3.2 Cấu trúc field nhóm — IMM Training Program

| Section | Field chính |
|---|---|
| Định danh | `program_code`, `program_name`, `description` |
| Phạm vi áp dụng | `target_device_model` (Link → IMM Device Model), `target_device_category`, `is_mandatory_for_operation` |
| Loại & nội dung | `training_type` (Initial / Refresher / Advanced / Certification), `content_outline`, `duration_hours` |
| Hiệu lực | `validity_period_months` (default 24), `requires_recertification` |
| Đánh giá | `assessment_method` (Theory / Practical / Both), `passing_score_pct` (default 70), `instructor_qualification_required` |
| QMS | `qms_doc_ref` (Link WI/PR document) |

### 3.3 Cấu trúc field nhóm — IMM Training Session

| Section | Field chính |
|---|---|
| Liên kết | `training_program` (Link), `session_date`, `location`, `session_type` (Onsite/Online/Hybrid) |
| Giảng viên | `instructor` (Link User, internal), `instructor_external_name`, `instructor_external_org` |
| Thời lượng | `duration_planned_hours`, `duration_actual_hours` |
| Tài liệu | `training_materials` (Attach), `qms_session_record` |
| Trạng thái | `workflow_state`, `status_remarks` |
| Học viên | `participants` (Table → IMM Training Participant) |

### 3.4 Cấu trúc field nhóm — IMM User Competency

| Section | Field chính |
|---|---|
| Liên kết | `user` (Link User), `device_model` (Link), `training_program`, `training_session` |
| Cấp độ | `competency_level` (Trainee / Operator / Senior Operator / Trainer) |
| Hiệu lực | `achieved_date`, `expiry_date`, `recertification_due_date`, `validity_months` |
| Trạng thái | `status` (Pending Assessment / Active / Expiring / Expired / Suspended / Revoked) |
| Đánh giá | `last_assessment_score`, `theory_score`, `practical_score` |
| Phê duyệt | `supervisor_signoff` (Link User), `signoff_date`, `certificate_file` |
| Thu hồi | `revoke_reason`, `revoke_capa_ref`, `revoked_by`, `revoked_date` |

**Tổng:** ~30 fields trên Competency, ~25 trên Session, ~15 trên Program. Chi tiết tại `IMM-06_Technical_Design.md` §2.

---

## 4. Service Functions / API Endpoints

File: `assetcore/api/imm06.py` — ~17 endpoints whitelist:

| # | Endpoint | Method | Caller |
|---|---|---|---|
| 1 | `list_programs` | GET | UI list curriculum master |
| 2 | `get_program` | GET | UI program detail |
| 3 | `create_program` | POST | Tổ HC-QLCL tạo curriculum |
| 4 | `update_program` | POST | Edit curriculum (trigger BR-06-04) |
| 5 | `list_sessions` | GET | UI session list, dashboard |
| 6 | `get_session` | GET | UI session detail |
| 7 | `create_session` | POST | Schedule training mới |
| 8 | `confirm_session` | POST | Workflow Planned → Confirmed |
| 9 | `complete_session` | POST | Đóng session + auto-tạo Competency cho người Pass |
| 10 | `cancel_session` | POST | Hủy session |
| 11 | `list_competencies` | GET | UI list, filter user/dept/status |
| 12 | `get_user_competencies` | GET | Self-service user xem hồ sơ |
| 13 | `get_asset_operator_coverage` | GET | Số operator competent per asset (cho IMM-04 gate) |
| 14 | `get_competency_gaps_by_dept` | GET | Dashboard ma trận khoa × class |
| 15 | `get_expiring_competencies` | GET | Báo cáo sắp hết hạn N ngày |
| 16 | `revoke_competency` | POST | Thu hồi competency (yêu cầu reason + CAPA link nếu có) |
| 17 | `recertify_competency` | POST | Tạo recert session/cập nhật expiry |
| 18 | `get_dashboard_stats` | GET | KPI dashboard |
| 19 | `check_user_authorization` | GET | **Hook nội bộ** — IMM-08/09/12 gọi để validate technician trước assign WO |

> Service layer `services/imm06.py` sẽ được tạo từ đầu (không lặp tech-debt như IMM-05). Business logic phức tạp (auto-create competency từ session, gap calculation, recertification flow) tách ra service function thuần — controller chỉ orchestrate.

---

## 5. Workflow & Schedulers

### 5.1 Workflow — IMM Training Session

| State | Type | Allow Edit |
|---|---|---|
| Planned | Default | Tổ HC-QLCL, Workshop Head |
| Confirmed | Warning | Tổ HC-QLCL |
| In Progress | Warning | Instructor, Tổ HC-QLCL |
| Completed | Success | Tổ HC-QLCL, Workshop Head |
| Verified | Success | Workshop Head |
| Closed | Default | (read-only) |
| Cancelled | Danger | (terminal) |

### 5.2 Workflow — IMM User Competency

| State | Type | Trigger |
|---|---|---|
| Pending Assessment | Warning | Auto-tạo từ Session khi participant Pass |
| Active | Success | Supervisor sign-off |
| Expiring | Warning | Scheduler set khi ≤ 90 ngày trước expiry |
| Expired | Danger | Scheduler set khi `expiry_date < today` |
| Suspended | Warning | Manual (tạm ngưng — không thu hồi) |
| Revoked | Danger | Manual (yêu cầu reason + có thể CAPA) — terminal |

### 5.3 Transitions chính

| Module | Action | From → To | Allowed Roles |
|---|---|---|---|
| Session | Xác nhận | Planned → Confirmed | Tổ HC-QLCL |
| Session | Bắt đầu | Confirmed → In Progress | Instructor, Tổ HC-QLCL |
| Session | Hoàn thành | In Progress → Completed | Instructor, Tổ HC-QLCL |
| Session | Verify | Completed → Verified | Workshop Head |
| Session | Đóng | Verified → Closed | Workshop Head, CMMS Admin |
| Session | Hủy | * → Cancelled | Tổ HC-QLCL, CMMS Admin |
| Competency | Sign-off | Pending Assessment → Active | Supervisor (Department Manager / Workshop Head) |
| Competency | (auto) | Active → Expiring | Scheduler `check_competency_expiry` |
| Competency | (auto) | Active/Expiring → Expired | Scheduler `auto_expire_competency` |
| Competency | Tạm ngưng | Active → Suspended | Workshop Head, Tổ HC-QLCL |
| Competency | Thu hồi | * → Revoked | Tổ HC-QLCL, CMMS Admin (BR-06-06) |

### 5.4 Scheduler Jobs — `assetcore/tasks.py`

| Job | Lịch | Hành vi | Đối tượng nhận email |
|---|---|---|---|
| `check_competency_expiry` | Daily 02:00 | Quét Active competency tại mốc 90/60/30 ngày trước `expiry_date` → set status=Expiring; gửi email user + supervisor; idempotent qua `Competency Alert Log` | User, Department Manager, Workshop Head (theo mốc) |
| `auto_expire_competency` | Daily 02:30 | Active/Expiring với `expiry_date < today` → status=Expired; tự động hủy quyền vận hành (BR-06-03) | User, Workshop Head |
| `check_recertification_due` | Daily 03:00 | Quét competency có `recertification_due_date <= today + 60d` → tạo placeholder Training Session (Planned) hoặc gửi reminder Tổ HC-QLCL | Tổ HC-QLCL, Workshop Head |
| `generate_competency_gap_report` | Weekly Mon 02:00 | Tính coverage operator per (department × device_class) → tạo `IMM Competency Gap Report`; mark assets vi phạm BR-06-07 | Workshop Head, VP Block2 |

---

## 6. Roles & Permissions

| Role | Training Program | Training Session | User Competency | Quyền chính |
|---|---|---|---|---|
| HTM Technician | R | R/W (own session) | R (own) | Tham gia training; xem hồ sơ chính mình |
| Biomed Engineer | R | R/W/C | R/W | Có thể là instructor; xem competency để assign WO |
| Tổ HC-QLCL (Training Officer) | R/W/C | R/W/C/Cancel | R/W/C/Revoke | Owner module — quản lý curriculum, schedule, revoke |
| Workshop Head | R | R/W/Verify | R/W/Suspend/Revoke | Verify session; sign-off competency; nhận escalation |
| Clinical Head | R | R | R (own dept) | Xem competency của khoa mình; phê duyệt operator nội khoa |
| Department Manager | R | R | R/W (sign-off own staff) | Sign-off competency cho cán bộ thuộc khoa |
| CMMS Admin | Full | Full | Full | Quản trị, override |
| Trainee/Operator | R | R (own) | R (own) | Self-service portal — xem chứng nhận của mình |
| VP Block2 | R | R | R | Nhận escalation gap report |

**Visibility rule:** User chỉ tự xem hồ sơ chính mình + competency người trong khoa (Clinical Head / Department Manager). Tổ HC-QLCL, Workshop Head, CMMS Admin xem toàn hệ thống.

---

## 7. Business Rules

| ID | Business Rule | Enforce |
|---|---|---|
| BR-06-01 | Operator chỉ được giao WO vận hành Class II/III nếu có Active competency cho `device_model` của Asset; áp dụng IMM-08 / IMM-09 / IMM-12 | `check_user_authorization()` gọi từ controller các module WO; trả `FORBIDDEN` |
| BR-06-02 | Mọi training session phải có instructor đủ qualification (validate theo `program.instructor_qualification_required`) | `IMMTrainingSession.validate()` — VR-04 |
| BR-06-03 | Re-certification bắt buộc trước expiry — Expired → block tự động không thể assign WO | Scheduler `auto_expire_competency` + BR-06-01 |
| BR-06-04 | Khi Training Program thay đổi nội dung trọng yếu → trigger re-cert cho mọi user cùng program (change control ISO 13485) | Hook `IMMTrainingProgram.on_update` so sánh field `content_outline`, `passing_score_pct` → tạo Document Request style flag |
| BR-06-05 | Mỗi participant phải có theory + practical score và supervisor sign-off trước khi competency Active | `IMMUserCompetency.validate()` — VR-06; workflow transition Pending Assessment → Active gated |
| BR-06-06 | Competency revoke yêu cầu lý do + CAPA link nếu liên quan incident | `revoke_competency` API — VR-08; nếu `revoke_capa_ref` empty và root cause là incident → throw |
| BR-06-07 | Asset Class III → tối thiểu 2 operator có Active competency tại khoa sử dụng (redundancy) | `generate_competency_gap_report` weekly + IMM-04 Clinical_Release gate qua `get_asset_operator_coverage` |
| BR-06-08 | Audit trail mọi thay đổi competency (status, expiry, sign-off, revoke) | Frappe `track_changes=1` + `IMM Audit Trail` log custom cho revoke/suspend |
| BR-06-09 | Không xóa cứng competency record (kể cả expired) — chỉ cho phép Suspended/Revoked | `on_trash()` throw |
| BR-06-10 | Khi user thay đổi khoa (department) → competency vẫn giữ nguyên nhưng `department_at_assessment` lưu lại; gap report tính lại | Hook trên User update |

---

## 8. Dependencies

| Module | Chiều | Liên kết |
|---|---|---|
| IMM-04 Installation | OUT | Clinical_Release gate gọi `get_asset_operator_coverage(asset)` — block nếu không đủ N operator competent (mặc định N=2 cho Class III) |
| IMM-05 Document Repository | IN | Certificate file (PDF) lưu thông qua Asset Document `doc_category=Training` |
| IMM-08 PM | OUT | Trước assign technician, gọi `check_user_authorization(user, asset.device_model)` |
| IMM-09 Repair | OUT | Tương tự IMM-08 |
| IMM-12 Corrective | OUT | Tương tự IMM-08 |
| IMM-10 Compliance Dashboard / IMM-16 | OUT | Cung cấp `training_compliance_pct`, `coverage_class3_pct` cho dashboard |
| IMM-11 Calibration | OUT | Calibration technician validate qualification qua check_user_authorization |
| IMM Audit Trail (cross-cutting) | OUT | Mọi revoke/suspend ghi log |
| Frappe `User` | IN | Source of truth cho `user`, `instructor` Link |
| Frappe `Notification` | IN | Email template cho expiry alert |

---

## 9. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| 5 DocTypes (Program, Session, Participant, Competency, Gap Report) | PLANNED | Schema đã thiết kế; chưa scaffold |
| 2 Workflow (Session, Competency) | PLANNED | JSON sketch tại Technical Design §8 |
| ~19 API endpoints | PLANNED | Đặc tả tại API doc |
| Validation Rules VR-01 → VR-12 | PLANNED | Tại Functional Spec §6 |
| 4 Scheduler jobs | PLANNED | tasks.py chưa có IMM-06 entries |
| Service layer `services/imm06.py` | PLANNED | Sẽ build từ đầu (không lặp tech-debt IMM-05) |
| Frontend UI (List, Detail, Create, Self-service portal, Dashboard) | PLANNED | Wireframe tại UI/UX doc |
| Email notification template | PLANNED | Template Vietnamese cho 90/60/30/0d và recert reminder |
| Integration hook (IMM-04 gate, IMM-08/09/12 WO assign) | PLANNED | Hook contract đã đặc tả |
| Auto-create competency từ Session.complete | PLANNED | Logic tại Technical Design §5 |
| UAT Script | PLANNED | TC-06-001 → TC-06-024 |

**Wave 2 mục tiêu:** đưa toàn bộ hạng mục PLANNED lên LIVE trước Q3/2026, kết hợp đào tạo nội bộ Tổ HC-QLCL về việc nhập dữ liệu lịch sử competency hiện tại.

---

## 10. QMS Mapping

| Yêu cầu | Nguồn | Cách đáp ứng |
|---|---|---|
| Competence, Awareness, Training | ISO 13485:2016 §6.2 | Training Program (curriculum); Training Session (delivery record); User Competency (evidence) |
| Người vận hành đủ năng lực | NĐ 98/2021/NĐ-CP §35 | BR-06-01 gate + audit trail |
| Lifecycle training plan | WHO HTM Annex 5 | Validity period + scheduler recertification |
| Change control khi update training content | ISO 13485 §4.1.4 + §7.3 | BR-06-04 trigger re-cert |
| Document control của curriculum | ISO 13485 §4.2 | `qms_doc_ref` Link sang IMM-05 (WI document) |
| CAPA khi revoke vì lỗi vận hành | ISO 13485 §8.5.2 | BR-06-06 + `revoke_capa_ref` |
| Audit trail mọi action | ISO 13485 §4.2.5 | Frappe Version + IMM Audit Trail |
| KPI training compliance | WHO HTM (KPI sets) | Dashboard `% users competent per dept`, `coverage Class III` |

**QMS document map:**

| QMS doc | Code | Vai trò |
|---|---|---|
| Procedure | PR-IMMIS-06-01 | Quy trình tổ chức đào tạo & đánh giá năng lực |
| Procedure | PR-IMMIS-06-02 | Quy trình tái chứng nhận năng lực định kỳ |
| Procedure | PR-IMMIS-06-03 | Quy trình thu hồi năng lực vận hành (revoke/suspend) |
| Work Instruction | WI-IMMIS-06-01..05 | HDSD: tạo Program, schedule Session, chấm điểm, sign-off, gap review |
| Form | BM-IMMIS-06-01 | Phiếu đánh giá học viên (theory + practical) |
| Record | HS-LOG-IMMIS-06-01, HS-REC-IMMIS-06-01, HS-REP-IMMIS-06-01 | Log alert, Record session, Report gap |
| KPI Dashboard | KPI-DASH-IMMIS-06 | Dashboard chỉ số đào tạo & năng lực |
