# IMM-09 — Sửa chữa & Bảo trì Khắc phục (Corrective Maintenance)
## Module Overview

**Module:** IMM-09
**Version:** 1.0
**Ngày:** 2026-04-17
**Trạng thái:** NOT CODED — Tài liệu thiết kế (Docs Only)
**Wave:** Wave 1

---

## 1. Mục đích Module

IMM-09 quản lý toàn bộ quy trình sửa chữa thiết bị y tế hỏng hóc: tiếp nhận yêu cầu từ nhiều nguồn, chẩn đoán lỗi, xuất kho phụ tùng có chứng từ, thực hiện sửa chữa, nghiệm thu sau sửa chữa, và trả thiết bị về trạng thái Active. Module đo MTTR theo giờ làm việc thực tế và gắn SLA theo risk class thiết bị.

---

## 2. Trạng thái Triển khai

| Hạng mục | Trạng thái |
|---|---|
| DocType | Chưa tạo (extend Asset Repair của ERPNext) |
| Workflow | Chưa cấu hình |
| Backend Logic | Chưa code |
| Frontend | Chưa code |
| API | Chưa code |
| Test | Chưa viết |

---

## 3. Vị trí trong Asset Lifecycle

```
3 nguồn kích hoạt:

IMM-08 PM Failure ──┐
IMM-12 Incident  ───┼──► IMM-09: CM Work Order ──► Asset "Active"
Yêu cầu thủ công ──┘            │
                                 ├──► IMM-11 Calibration (nếu cần sau SC)
                                 └──► IMM-13/14 EOL (nếu Cannot Repair)
```

**Quan hệ module:**
- **IMM-08** → cung cấp `source_pm_wo` khi PM phát hiện lỗi chuyển CM
- **IMM-05** → cung cấp Service Manual và hồ sơ kỹ thuật để chẩn đoán
- **IMM-11** → Calibration bắt buộc sau sửa chữa nếu thiết bị có đo lường
- **IMM-12** → Sự cố có thể chuyển thành Repair WO IMM-09
- **IMM-13/14** → Khi thiết bị Cannot Repair → EOL process

---

## 4. DocTypes cần tạo / mở rộng

| DocType | Loại | Naming Series | Mục đích | Trường custom thêm |
|---|---|---|---|---|
| **Asset Repair** | Extend ERPNext core | `WO-CM-{YYYY}-{#####}` | WO sửa chữa chính — KHÔNG tạo mới, extend bằng custom fields | `incident_report`, `source_pm_wo`, `risk_class`, `priority`, `diagnosis_notes`, `mttr_hours`, `sla_breached`, `is_repeat_failure`, `firmware_updated`, `firmware_change_request` |
| **Spare Parts Used** | Child table của Asset Repair | — | Liệt kê linh kiện đã sử dụng với chứng từ | `item_code`, `item_name`, `qty`, `uom`, `stock_entry_ref` (bắt buộc) |
| **Repair Checklist** | Child table của Asset Repair | — | Checklist nghiệm thu sau sửa chữa (100% Pass mới Completed) | `check_item`, `expected_result`, `actual_result`, `pass_fail`, `notes` |
| **Firmware Change Request** | DocType mới | `FCR-{YYYY}-{#####}` | Kiểm soát thay đổi firmware — bắt buộc khi update firmware thiết bị | `asset_ref`, `wo_ref`, `version_before`, `version_after`, `change_notes`, `approved_by`, `status` |

---

## 5. Workflow States

| State | Mô tả | Actor | Điều kiện chuyển |
|---|---|---|---|
| **Open** | WO vừa được tạo, chưa phân công | Workshop Manager / CMMS Auto | Tạo WO có nguồn hợp lệ (BR-09-01) |
| **Assigned** | KTV đã được phân công | Workshop Manager | Chọn KTV; Asset → "Under Repair" (BR-09-05) |
| **Diagnosing** | KTV đang chẩn đoán lỗi | KTV HTM | KTV confirm nhận WO |
| **Pending Parts** | Chờ xuất kho phụ tùng | KTV HTM / Kho | KTV yêu cầu vật tư còn thiếu |
| **In Repair** | Đang thực hiện sửa chữa | KTV HTM | Phụ tùng đã đủ hoặc không cần vật tư |
| **Pending Inspection** | Sửa xong, chờ nghiệm thu | KTV HTM | Sửa chữa hoàn tất, trước khi kiểm tra checklist |
| **Completed** | Nghiệm thu pass, thiết bị trả khoa | KTV HTM + Trưởng khoa | Repair Checklist 100% Pass (BR-09-04); Asset → "Active" |
| **Cannot Repair** | Không thể sửa chữa được | Workshop Manager | KTV xác nhận vượt khả năng; trigger IMM-13/14 |
| **Cancelled** | Hủy WO có lý do | Workshop Manager | WO sai hoặc asset disposed trước khi sửa |

---

## 6. Business Rules

| Mã | Rule | Kiểm soát |
|---|---|---|
| **BR-09-01** | CM WO phải có ít nhất một nguồn hợp lệ: `incident_report` HOẶC `source_pm_wo` | Validate on `before_insert` — block nếu thiếu cả hai |
| **BR-09-02** | `Spare Parts Used` phải có `stock_entry_ref` tham chiếu phiếu xuất kho hợp lệ | Validate child table trước Submit WO |
| **BR-09-03** | Firmware update phải tạo `Firmware Change Request` riêng — không update trực tiếp trên Asset | Block Submit nếu `firmware_updated = True` mà không có FCR linked |
| **BR-09-04** | `Repair Checklist` phải 100% Pass trước khi chuyển Completed | Validate all items result = "Pass" on `before_submit` |
| **BR-09-05** | Asset.status = "Under Repair" khi WO → Assigned; chỉ trả về "Active" khi WO Completed | Auto-set Asset.status theo WO transition; block PM/Calibration mới khi Under Repair |

---

## 7. MTTR Calculation

### Công thức
```
MTTR = (completion_datetime - open_datetime) theo giờ làm việc
Giờ làm việc: Thứ 2–6, 07:00–17:00, không tính ngày lễ (Holiday List)
```

### SLA Matrix theo Risk Class

| Risk Class | Priority | MTTR Target | Ngưỡng cảnh báo | Ngưỡng critical |
|---|---|---|---|---|
| Class III (Nguy cơ cao) | Emergency | ≤ 4 giờ | > 2 giờ | > 4 giờ |
| Class III | Urgent | ≤ 24 giờ | > 16 giờ | > 24 giờ |
| Class II | Normal | ≤ 72 giờ | > 48 giờ | > 72 giờ |
| Class I | Normal | ≤ 120 giờ | > 80 giờ | > 120 giờ |

### SLA Scheduler
- Chạy mỗi **1 giờ** — kiểm tra WO đang active (Assigned / Diagnosing / In Repair)
- Cảnh báo khi elapsed ≥ 75% SLA limit
- Escalate khi elapsed ≥ 100% SLA limit: alert PTP + BGĐ (Class III Emergency)

---

## 8. Integration Points

| Từ / Đến | Loại | Dữ liệu truyền |
|---|---|---|
| **IMM-08 → IMM-09** | Auto-create CM WO | `source_pm_wo`, mô tả lỗi, priority = Critical khi Major Failure |
| **IMM-12 → IMM-09** | Link Incident → WO | `incident_report` ref, mô tả sự cố, risk_class |
| **IMM-09 → IMM-11** | Trigger sau Completed | Tạo Calibration WO nếu `asset_category` yêu cầu post-repair calibration |
| **IMM-09 → IMM-13/14** | Trigger khi Cannot Repair | Asset.status = Out of Service, mở EOL process |
| **IMM-09 → Asset** | Auto-update | `last_repair_date`, `status`, `firmware_version`, `mttr_avg_hours` |
| **ERPNext Stock** | Stock Entry ref | `stock_entry_ref` trong Spare Parts Used — xác nhận xuất kho hợp lệ |

---

## 9. KPI Definitions

| KPI | Công thức | Mục tiêu |
|---|---|---|
| **MTTR (tháng)** | `Tổng MTTR tất cả WO hoàn thành / Count(WO Completed)` | Theo SLA matrix |
| **First-Time Fix Rate** | `Count(WO không mở lại trong 30 ngày) / Count(WO Completed) × 100%` | ≥ 85% |
| **Repair Backlog** | `Count(WO status in Open, Assigned, Diagnosing, In Repair)` | ≤ target theo capacity |
| **Parts Cost/Repair** | `Tổng spare_parts_cost / Count(WO Completed)` | Theo ngân sách |
| **SLA Breach Rate** | `Count(WO sla_breached = True) / Count(WO Completed) × 100%` | ≤ 5% |

---

## 10. Dependencies

| Dependency | Lý do |
|---|---|
| IMM-08 (PM Work Order) | Nguồn CM WO khi PM failure; `source_pm_wo` reference |
| IMM-12 (Incident Report) | Nguồn CM WO khi sự cố; `incident_report` reference |
| IMM-11 (Calibration) | Trigger post-repair calibration WO |
| Asset Repair (ERPNext core) | Base DocType — extend không replace |
| Stock Entry (ERPNext core) | `stock_entry_ref` validate xuất kho hợp lệ |
| Holiday List (ERPNext) | Tính MTTR loại trừ ngày lễ |
| IMM-05 (Asset Document) | Service Manual tham khảo khi chẩn đoán |

---

## 11. QMS Mapping

| Yêu cầu | WHO HTM | ISO 9001:2015 | NĐ98 | Ghi chú |
|---|---|---|---|---|
| WO bắt buộc cho mọi sửa chữa | WHO CMMS §3.2.3 | §8.5.1 | Điều 28 | Không có action ngoài WO |
| Traceability nguồn (BR-09-01) | WHO HTM 2025 §5.4.2 | §8.5.2 | Điều 29 | IR hoặc PM WO bắt buộc |
| Spare parts với chứng từ (BR-09-02) | WHO Maintenance §6.3 | §8.4.3 | Điều 31 | Stock Entry bắt buộc |
| Firmware change control (BR-09-03) | WHO HTM 2025 §7.2 | §8.5.6 | Điều 35 | FCR bắt buộc |
| Post-repair acceptance test (BR-09-04) | WHO Maintenance §5.5.3 | §8.6 | Điều 30 | 100% Pass |
| MTTR tracking | WHO HTM 2025 §6.1 | §9.1.1 | Điều 36 | KPI bắt buộc |
| Hồ sơ sửa chữa immutable | WHO Maintenance §5.5.5 | §7.5 | Điều 37 | WO Submitted không xóa được |
| Audit trail mọi thao tác | WHO HTM 2025 §6.4 | §7.5.3 | Điều 40 | Asset Lifecycle Event mỗi bước |
