# IMM-08 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | WHO HTM 2025 §5.3, ISO 13485:2016 §7.5, ISO 9001:2015 §8.5.1, NĐ 98/2021 |

---

## 1. Scope

### 1.1 In Scope

| # | Hạng mục |
|---|---|
| 1 | 6 DocTypes (PM Schedule, PM Checklist Template, PM Checklist Item, PM Work Order, PM Checklist Result, PM Task Log) |
| 2 | Auto-create PM Schedule khi `Asset Commissioning` submit (hook IMM-04 → IMM-08) |
| 3 | Scheduler tạo PM Work Order daily theo `next_due_date` + `alert_days_before` |
| 4 | Scheduler đánh dấu Overdue + leo thang theo ngưỡng (≤7d / 8–30d / >30d) |
| 5 | KTV điền checklist (Pass / Fail-Minor / Fail-Major / N/A), submit Work Order |
| 6 | Auto-create CM Work Order (`wo_type = Corrective`, `source_pm_wo`) khi Fail |
| 7 | Major Failure → set Asset `Out of Service` + dừng PM (`Halted–Major Failure`) |
| 8 | PM Task Log immutable cho audit trail |
| 9 | Dashboard KPI (compliance %, overdue, avg days late, trend 6 tháng) |
| 10 | Calendar view tháng/tuần cho Workshop Manager |
| 11 | Reschedule PM (lý do bắt buộc) |

### 1.2 Out of Scope (defer)

| # | Hạng mục | Defer sang |
|---|---|---|
| 1 | Calibration WO | IMM-11 |
| 2 | Spare Parts request workflow | IMM-09 phase 2 |
| 3 | Mobile offline queue (IndexedDB) | IMM-08 v2.1 |
| 4 | Holiday list integration (loại trừ ngày lễ khi tính due_date) | v2.2 |
| 5 | E-signature trên PM completion certificate | QMS phase 2 |

---

## 2. Actors

| Role (system) | Role (nghiệp vụ) | Trách nhiệm chính |
|---|---|---|
| `Workshop Head` | Workshop Manager | Phân công KTV, theo dõi Calendar, reschedule, duyệt template |
| `HTM Technician` | KTV HTM | Thực hiện PM, điền checklist, upload ảnh, submit WO |
| `Biomed Engineer` | Kỹ sư y sinh | Tham vấn template, hỗ trợ Major Failure |
| `VP Block2` | PTP Khối 2 | Giám sát KPI, nhận escalation 8–30 ngày |
| `CMMS Admin` | Quản trị CMMS | Cấu hình template, fixtures, phân quyền |
| System Scheduler | — | Tự động tạo WO, đánh dấu Overdue, gửi email |

---

## 3. User Stories (Gherkin)

### US-08-01 — Tự động tạo PM WO khi đến hạn

```gherkin
Given Asset "AC-ASSET-2026-0003" có PM Schedule "PMS-AC-ASSET-2026-0003-Quarterly"
  với next_due_date = today + 3 (alert_days_before=7)
And Asset.status = "Active"
And PM Checklist Template "PMCT-Ventilator-Quarterly" tồn tại và is_active=1
When scheduler.generate_pm_work_orders chạy
Then 1 PM Work Order được tạo, status = "Open"
And due_date = next_due_date
And checklist_results được clone từ template (n items)
And email gửi tới Workshop Head với subject "[AssetCore] N PM Work Order mới hôm nay"
```

### US-08-02 — KTV điền checklist và submit thành công

```gherkin
Given PM Work Order "PM-WO-2026-00001" có status = "In Progress"
And đã được assign cho ktv1@bv.vn
And tất cả checklist_results.result = "Pass"
When ktv1 gọi POST submit_pm_result với
  overall_result="Pass", technician_notes="OK", pm_sticker_attached=1, duration_minutes=45
Then PM WO status = "Completed", docstatus = 1
And completion_date = today
And is_late = 0 (vì today ≤ due_date)
And PM Task Log mới tạo (immutable)
And PM Schedule.last_pm_date = today, next_due_date = today + pm_interval_days (BR-08-03)
And Asset.custom_last_pm_date = today, custom_next_pm_date = today + interval
```

### US-08-03 — Major Failure → Asset Out of Service

```gherkin
Given PM WO "PM-WO-2026-00003" đang In Progress
When ktv1 gọi POST report_major_failure với failure_description="Compressor không khởi động"
Then PM WO.status = "Halted–Major Failure"
And Asset.status = "Out of Service" (BR-08-04)
And 1 PM Work Order CM mới tạo với wo_type="Corrective", source_pm_wo="PM-WO-2026-00003"
And email khẩn gửi tới Workshop Head + VP Block2
```

### US-08-04 — PM Overdue + leo thang

```gherkin
Given PM WO "PM-WO-2026-00007" có due_date = today - 8 và status = "Open"
When scheduler.check_pm_overdue chạy
Then PM WO.status = "Overdue"
And email leo thang gửi tới VP Block2 (vì 8 ≤ days_overdue ≤ 30)
```

### US-08-05 — Block tạo PM cho Asset Out of Service (BR-08-04)

```gherkin
Given Asset "AC-ASSET-UAT-004" có status = "Out of Service"
And PM Schedule cho asset này có next_due_date = today
When scheduler.generate_pm_work_orders chạy
Then KHÔNG có PM Work Order nào được tạo cho AC-ASSET-UAT-004
And log warning "Skip PM WO creation for AC-ASSET-UAT-004 — Out of Service"
```

### US-08-06 — Reschedule khi thiết bị bận

```gherkin
Given PM WO "PM-WO-2026-00004" có due_date = today
When Workshop Head gọi POST reschedule_pm với
  new_date=today+3, reason="Thiết bị đang dùng cấp cứu"
Then PM WO.status = "Pending–Device Busy"
And due_date = today + 3
And technician_notes append "[Hoãn lịch ... → ...]: ..."
```

### US-08-07 — IMM-04 commissioning auto-tạo PM Schedule

```gherkin
Given Asset Commissioning "ACC-2026-0001" với asset_category = "Mechanical Ventilator"
And PM Checklist Template "PMCT-Ventilator-Quarterly" (interval mặc định 90)
When ACC-2026-0001 được Submit
Then PM Schedule mới tạo với next_due_date = commissioning_date + 90
And created_from_commissioning = "ACC-2026-0001"
```

### US-08-08 — Dashboard KPI

```gherkin
Given trong tháng có 16 PM WO scheduled, 11 completed on-time, 3 late, 2 overdue
When PTP gọi GET get_pm_dashboard_stats?year=2026&month=4
Then trả về kpis.compliance_rate_pct = 68.75
And trả về kpis.overdue = 2
And trend_6months có 6 entry
```

---

## 4. Business Rules

(Trùng với Module Overview §7 — repeat ngắn để tham chiếu nhanh)

| ID | Rule | Severity |
|---|---|---|
| BR-08-01 | Phải có Checklist Template trước khi tạo PM WO | Block |
| BR-08-02 | CM WO phải có `source_pm_wo` | Block |
| BR-08-03 | `next_pm_date = completion_date + interval` (KHÔNG dùng due_date) | Code enforce |
| BR-08-04 | Asset Out of Service → block tạo PM WO | Block |
| BR-08-05 | `is_late = (completion_date > due_date)` | Auto |
| BR-08-06 | Class III/C/D phải upload ảnh | Block submit |
| BR-08-07 | Mỗi pm_type là PM Schedule riêng | Naming uniqueness |
| BR-08-08 | Checklist 100% có result trước Submit | Block submit |
| BR-08-09 | Fail-Minor → CM Medium; Fail-Major → CM Critical + Out of Service | Auto |
| BR-08-10 | PM Task Log immutable | DocType perm |

---

## 5. Permission Matrix

| Action | Workshop Head | CMMS Admin | HTM Technician | Biomed Eng. | VP Block2 |
|---|---|---|---|---|---|
| Tạo PM Schedule | ✅ | ✅ | ❌ | ❌ | ❌ |
| Tạo PM Checklist Template | ✅ | ✅ | ❌ | ❌ | ❌ |
| Phân công KTV (assign_technician) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Reschedule PM | ✅ | ✅ | ❌ | ❌ | ❌ |
| Điền checklist + submit_pm_result | ✅ | ✅ | ✅ (assigned) | ✅ | ❌ |
| Report major failure | ✅ | ✅ | ✅ | ✅ | ❌ |
| Xem Calendar / Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| Xem PM Task Log | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cancel PM WO | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete PM WO | ❌ | ✅ | ❌ | ❌ | ❌ |

---

## 6. Validation Rules

| VR ID | Field / Action | Rule | Error Message (vi) | Mã code |
|---|---|---|---|---|
| VR-08-01 | `pm_schedule.checklist_template` | Bắt buộc trước khi scheduler tạo WO (BR-08-01) | "PM Schedule {name} thiếu checklist template. Vui lòng tạo template cho asset category trước khi PM." | (scheduler skip + email Admin) |
| VR-08-02 | `Asset.status` | ≠ "Out of Service" khi tạo PM WO mới (BR-08-04) | "Thiết bị {asset} đang Out of Service. Không thể tạo PM Work Order." | scheduler skip |
| VR-08-03 | `checklist_results[].result` | 100% có giá trị trước Submit (BR-08-08) | "Tất cả mục checklist phải có kết quả trước khi Submit (BR-08-08). Mục '{description}' chưa điền." | controller throw |
| VR-08-04 | `attachments` | Bắt buộc nếu `Asset.custom_risk_class IN (III, C, D)` (BR-08-06) | "Thiết bị nguy cơ cao (Class {risk}) bắt buộc upload ảnh trước/sau PM (BR-08-06)." | controller throw |
| VR-08-05 | `source_pm_wo` | Bắt buộc khi `wo_type = Corrective` (BR-08-02) | "CM Work Order phải có tham chiếu PM WO gốc (BR-08-02)." | controller throw + `mandatory_depends_on` |
| VR-08-06 | `checklist_results[].notes` | Bắt buộc khi `result IN (Fail–Minor, Fail–Major)` | "Vui lòng nhập mô tả lỗi cho mục Fail." | DocType `mandatory_depends_on` |
| VR-08-07 | PM Schedule | Unique theo `(asset_ref, pm_type)` | "Đã tồn tại PM Schedule {pm_type} cho thiết bị này." | naming format |
| VR-08-08 | `assign_technician` | WO phải ở `Open / Overdue` mới được phân công | "Không thể phân công khi WO ở trạng thái '{status}'." | API guard |
| VR-08-09 | `reschedule_pm.reason` | Bắt buộc, ≥ 5 ký tự | "Lý do hoãn lịch là bắt buộc (tối thiểu 5 ký tự)." | API guard |
| VR-08-10 | `submit_pm_result` | Block nếu `docstatus = 1` | "PM Work Order đã được Submit." | API guard |

---

## 7. Non-Functional Requirements

| NFR ID | Category | Yêu cầu | Target |
|---|---|---|---|
| NFR-08-01 | Scheduler reliability | Job `generate_pm_work_orders` chạy hằng ngày, idempotent | 0 WO trùng cho cùng schedule |
| NFR-08-02 | Performance — list WO | `list_pm_work_orders` (page=20) | P95 < 300 ms với 50k WO |
| NFR-08-03 | Performance — dashboard | `get_pm_dashboard_stats` | P95 < 800 ms |
| NFR-08-04 | Mobile | Checklist hoạt động trên tablet 768px | Manual test trên iPad / Android tablet |
| NFR-08-05 | Photo upload | Max 10 MB/ảnh, max 5 ảnh / WO | Backend validate |
| NFR-08-06 | Audit | PM Task Log không thể sửa/xoá sau insert (BR-08-10) | DB-level perm + `in_create=1` |
| NFR-08-07 | Email | Alert overdue gửi trong 5 phút sau scheduler | Test E2E |
| NFR-08-08 | i18n | Mọi user-facing message dùng `frappe._()` tiếng Việt | Code review |
| NFR-08-09 | Concurrency | 2 KTV không thể đồng thời submit cùng WO | `frappe.model` optimistic lock |

---

## 8. Acceptance Criteria

Wave 1 release IMM-08 được chấp nhận khi:

| # | Tiêu chí | Bằng chứng |
|---|---|---|
| AC-1 | 6 DocTypes deploy thành công, fixtures load | `bench migrate` không lỗi |
| AC-2 | Hook IMM-04 → IMM-08 tự tạo PM Schedule khi commissioning Submit | UAT TC-PM-09 Pass |
| AC-3 | `tasks.generate_pm_work_orders` tạo WO đúng và idempotent | UAT TC-PM-01 Pass |
| AC-4 | KTV submit happy path → PM Task Log + Asset dates cập nhật | UAT TC-PM-02 Pass |
| AC-5 | Overdue scheduler đánh dấu + email leo thang | UAT TC-PM-03 Pass |
| AC-6 | Major Failure → Asset Out of Service + CM WO khẩn | UAT TC-PM-05 Pass |
| AC-7 | BR-08-04 chặn PM cho Out of Service | UAT TC-PM-06 Pass |
| AC-8 | Calendar + Dashboard hiển thị đúng dữ liệu | UAT TC-PM-07, TC-PM-08 Pass |
| AC-9 | ≥ 8/10 UAT cases Pass; TC-PM-01/02/03/05 bắt buộc Pass | UAT report |
| AC-10 | API response chuẩn `_ok / _err` cho mọi 9 endpoint | API contract test |

---

## 9. Glossary

| Thuật ngữ | Nghĩa |
|---|---|
| PM | Preventive Maintenance — bảo trì định kỳ phòng ngừa |
| CM | Corrective Maintenance — sửa chữa khắc phục |
| WO | Work Order — phiếu lệnh công việc |
| KTV | Kỹ thuật viên (HTM Technician) |
| PTP | Phó Trưởng phòng (VP Block2) |
| Sticker PM | Tem dán vật lý trên thiết bị xác nhận đã PM |
| Slippage | Mức trễ so với due_date (days_late) |
| `is_late` | Cờ Boolean: completion_date > due_date |
| `source_pm_wo` | Link từ CM WO ngược về PM WO phát hiện lỗi |

---

*End of Functional Specifications v2.0.0 — IMM-08 Preventive Maintenance*
