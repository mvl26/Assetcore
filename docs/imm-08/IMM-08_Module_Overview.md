# IMM-08 — Bảo trì Định kỳ (Preventive Maintenance)
## Module Overview

**Module:** IMM-08
**Version:** 1.0
**Ngày:** 2026-04-17
**Trạng thái:** NOT CODED — Tài liệu thiết kế (Docs Only)
**Wave:** Wave 1

---

## 1. Mục đích Module

IMM-08 quản lý toàn bộ vòng đời bảo trì định kỳ (PM) thiết bị y tế: từ lập lịch tự động, phân công kỹ thuật viên, thực hiện theo checklist chuẩn, đến cập nhật lịch PM kỳ tiếp theo. Module đảm bảo không có thiết bị nào bị bỏ sót bảo trì và mọi hành động đều có audit trail đầy đủ.

---

## 2. Trạng thái Triển khai

| Hạng mục | Trạng thái |
|---|---|
| DocType | Chưa tạo |
| Workflow | Chưa cấu hình |
| Backend Logic | Chưa code |
| Frontend | Chưa code |
| API | Chưa code |
| Test | Chưa viết |

---

## 3. Vị trí trong Asset Lifecycle

```
IMM-04 (Lắp đặt) → IMM-05 (Hồ sơ) → Asset "Active"
                                             │
                                    IMM-08: PM Schedule
                                             │
                        ┌────────────────────┤
                        │                    │
                  Không lỗi           Lỗi phát sinh
                        │                    │
               PM hoàn thành        IMM-09 (CM WO)
               Next PM scheduled    hoặc IMM-12
```

**Quan hệ module:**
- **IMM-04** → cung cấp `commissioning_date` làm baseline PM đầu tiên
- **IMM-05** → cung cấp Service Manual và checklist template nguồn
- **IMM-09** → nhận CM WO khi PM phát hiện lỗi (Major/Minor Failure)
- **IMM-11** → Calibration có thể tích hợp vào PM nếu cùng kỳ
- **IMM-12** → Corrective Maintenance khi PM Major Failure

---

## 4. DocTypes cần tạo

| DocType | Naming Series | Mục đích | Trường chính |
|---|---|---|---|
| **PM Schedule** | `PMS-{YYYY}-{#####}` | Lưu lịch PM định kỳ cho từng asset | `asset_ref`, `pm_type`, `interval_days`, `next_due_date`, `last_pm_date` |
| **PM Checklist Template** | `PMCT-{category}-{type}` | Template checklist theo Asset Category + PM Type | `asset_category`, `pm_type`, `checklist_items` (child table) |
| **PM Work Order** | `WO-PM-{YYYY}-{#####}` | Lệnh công việc PM cho từng lần thực hiện | `pm_schedule_ref`, `asset_ref`, `assigned_ktv`, `due_date`, `completion_date`, `is_late`, `checklist` (child), `result_summary` |
| **PM Task Log** | `PMLOG-{YYYY}-{#####}` | Hồ sơ lịch sử mỗi lần PM hoàn thành (immutable) | `pm_wo_ref`, `asset_ref`, `completion_date`, `ktv`, `result`, `is_late`, `next_pm_date` |

---

## 5. Workflow States

| State | Mô tả | Actor | Trigger |
|---|---|---|---|
| **Open** | WO vừa được tạo bởi scheduler | CMMS Auto | `next_due_date <= today` |
| **Assigned** | Workshop Manager đã phân công KTV | Workshop Manager | Chọn KTV, xác nhận lịch |
| **In Progress** | KTV đang thực hiện PM | KTV HTM | KTV confirm bắt đầu |
| **Pending – Device Busy** | Khoa phòng chưa sẵn sàng | KTV / Workshop | Khoa phòng từ chối |
| **Overdue** | Quá due_date chưa hoàn thành | CMMS Scheduler | `today > due_date AND status in (Open, In Progress)` |
| **Halted – Major Failure** | PM dừng vì lỗi nghiêm trọng | KTV HTM | KTV báo cáo Major Failure |
| **Completed** | PM hoàn thành, checklist 100% | KTV HTM | Submit WO thành công |
| **Cancelled** | Hủy có lý do ghi nhận | Workshop Manager | Hoãn vô thời hạn hoặc asset disposed |

---

## 6. Business Rules

| Mã | Rule | Kiểm soát |
|---|---|---|
| **BR-08-01** | PM WO phải có Checklist Template theo Asset Category trước khi tạo | Validate template exists on WO creation — block nếu thiếu |
| **BR-08-02** | CM WO phát sinh từ PM phải có `source_pm_wo` bắt buộc | `source_pm_wo` mandatory khi CM WO type = From PM |
| **BR-08-03** | `next_pm_date = completion_date + interval` — KHÔNG tính từ due_date | Auto-calculate on WO Submit |
| **BR-08-04** | Asset status `Out of Service` không được tạo PM WO mới | Workflow condition check on WO creation |
| **BR-08-05** | PM WO hoàn thành sau due_date bị đánh dấu `is_late = True` | `is_late = (completion_date > due_date)` on Submit |
| **BR-08-06** | Thiết bị Class III bắt buộc upload ảnh trước/sau PM | File attachment mandatory check by risk class |
| **BR-08-07** | Mỗi loại PM (annual, quarterly) là 1 PM Schedule độc lập | `pm_type` phân biệt — không gộp lịch |
| **BR-08-08** | Checklist phải hoàn thành 100% trước khi Submit WO | Validate all items filled before Submit |

---

## 7. Tính toán Ngày PM

### PM đầu tiên (từ IMM-04)
```
first_pm_date = commissioning_date + pm_interval_days
```
Trigger: `on_submit` của Asset Commissioning.

### PM tiếp theo (từ completion)
```
next_pm_date = completion_date + pm_interval_days
```
Điều kiện: PM WO status = "Completed".

### Overdue Detection (daily scheduler)
```
if today > due_date AND wo.status in ("Open", "In Progress"):
    wo.status = "Overdue"
    send_alert(workshop_manager, ptp)
```

### Slippage Tolerance
| Mức trễ | Hành động |
|---|---|
| ≤ 7 ngày | Cảnh báo vàng — tiếp tục bình thường |
| 8–30 ngày | Cảnh báo đỏ — escalate PTP Khối 2 |
| > 30 ngày | Critical — leo thang BGĐ, ghi compliance log |

---

## 8. Scheduler Jobs

| Job | Tần suất | Mô tả |
|---|---|---|
| `create_pm_work_orders` | Hàng ngày 00:30 | Query PM Schedules có `next_due_date <= today`, tạo WO tự động |
| `check_pm_overdue` | Hàng ngày 06:00 | Cập nhật WO status = Overdue, gửi alert theo slippage tolerance |
| `update_pm_compliance_kpi` | Hàng tuần | Tính PM Compliance Rate cho dashboard |

---

## 9. Integration Points

| Từ / Đến | Loại | Dữ liệu truyền |
|---|---|---|
| **IMM-04 → IMM-08** | Event hook `on_submit` | `commissioning_date` → tạo PM Schedule, tính `first_pm_date` |
| **IMM-08 → IMM-09** | Auto-create CM WO | `source_pm_wo`, mô tả lỗi, asset_ref khi Major/Minor Failure |
| **IMM-08 → IMM-11** | Manual / Rule-based | Trigger Calibration WO nếu PM type yêu cầu kiểm định cùng kỳ |
| **IMM-05 → IMM-08** | Reference | Service Manual → nguồn tạo Checklist Template |

---

## 10. KPI Definitions

| KPI | Công thức | Mục tiêu |
|---|---|---|
| **PM Compliance Rate** | `Count(WO completed on time) / Count(WO scheduled) × 100%` | ≥ 95% |
| **PM Overdue Rate** | `Count(WO is_late = True) / Count(WO completed) × 100%` | ≤ 5% |
| **PM Slippage Average** | `Avg(completion_date - due_date)` cho WO trễ | ≤ 3 ngày |
| **Checklist Compliance** | `Count(WO 100% checklist) / Count(WO submitted) × 100%` | 100% |

---

## 11. Dependencies

| Dependency | Lý do |
|---|---|
| IMM-04 (Asset Commissioning) | Cung cấp `commissioning_date` baseline |
| IMM-05 (Asset Document) | Service Manual nguồn cho checklist template |
| Asset DocType (ERPNext core) | Cập nhật `last_pm_date`, `next_pm_date`, `status` |
| Frappe Scheduler | Chạy daily job tạo WO và overdue check |
| Holiday List (ERPNext) | Loại trừ ngày lễ trong tính toán lịch |

---

## 12. QMS Mapping

| Yêu cầu | WHO HTM | ISO 9001:2015 | Ghi chú |
|---|---|---|---|
| PM interval theo manufacturer | WHO Maintenance §5.3.1 | §8.5.1 | Template per Asset Category |
| Work Order system bắt buộc | WHO CMMS §3.2.3 | §8.5.1 | PM WO với checklist |
| PM compliance tracking | WHO HTM 2025 §6.2 | §9.1 | KPI = on-time / total |
| Hồ sơ PM immutable | WHO Maintenance §5.3.5 | §7.5 | PM Task Log không xóa được |
| Phát hiện lỗi → CM | WHO HTM 2025 §5.3.4 | §10.2 | CM WO có `source_pm_wo` |
| Audit trail đầy đủ | WHO HTM 2025 §6.4 | §7.5.3 | Timestamp + user mọi hành động |
