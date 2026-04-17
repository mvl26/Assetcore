# IMM-12 — Module Overview

## Incident Reporting & SLA Management

**Module:** IMM-12
**Version:** 1.0
**Ngày:** 2026-04-17
**Trạng thái:** NOT CODED — chưa triển khai
**Wave:** Wave 1 (Deployment)

---

## 1. Mục đích & Phạm vi

IMM-12 quản lý toàn bộ vòng đời của một sự cố thiết bị y tế: từ lúc người dùng báo cáo đến khi đóng hồ sơ với đầy đủ audit trail.

Module đảm nhiệm:

- **Incident Reporting** — tiếp nhận sự cố từ bất kỳ khoa phòng nào, bất kỳ thời điểm nào
- **SLA Enforcement** — theo dõi 24/7, cảnh báo tự động, leo thang theo cấp bậc
- **Chronic Failure Detection** — phát hiện mẫu hỏng hóc tái diễn, kích hoạt RCA tự động
- **Root Cause Analysis (RCA)** — bắt buộc với P1/P2, có cấu trúc 5-Why / Fishbone
- **Downtime Tracking** — tính và cộng dồn thời gian ngừng hoạt động lên Asset

Không bao gồm: thực hiện sửa chữa (IMM-09), bảo trì định kỳ (IMM-08), hiệu chuẩn (IMM-11).

---

## 2. Trạng thái triển khai

| Thành phần | Trạng thái |
|---|---|
| DocType: Incident Report | Chưa tạo |
| DocType: SLA Compliance Log | Chưa tạo |
| DocType: RCA Record | Chưa tạo |
| Service Layer: services/imm12.py | Chưa tạo |
| Scheduler hooks (hooks.py) | Chưa cấu hình |
| API endpoints (api/imm12.py) | Chưa tạo |
| Frontend components | Chưa tạo |
| Custom fields trên Asset | Chưa thêm |

---

## 3. SLA Matrix

Tất cả SLA áp dụng **24/7 — không pause** theo giờ hành chính (BR-12-02).

| Priority | Điều kiện | Response | Resolution | Escalation |
|---|---|---|---|---|
| **P1 Critical** | Thiết bị hỗ trợ sự sống (máy thở, monitor ICU, máy lọc máu) hỏng hoặc báo alarm quan trọng | 30 phút | 4 giờ | BGĐ + PTP (Email + SMS) |
| **P2 High** | Thiết bị chẩn đoán quan trọng (siêu âm, nội soi, X-quang, ECG) — không có thiết bị thay thế | 2 giờ | 8 giờ | PTP Khối 2 (Email) |
| **P3 Medium** | Thiết bị không quan trọng tức thì — có thể hoãn hoặc dùng thiết bị khác | 4 giờ | 24 giờ | Workshop Manager (Email) |
| **P4 Low** | Lỗi nhỏ, có workaround, không ảnh hưởng trực tiếp đến bệnh nhân | 8 giờ | 72 giờ | KTV HTM (In-app) |

**Ngưỡng cảnh báo sớm:** 80% SLA time → sla_status = "At_Risk" → cảnh báo nội bộ trước khi breach.

---

## 4. Workflow States

```
New → Acknowledged → In_Progress → Resolved → Closed
                                       └──(P1/P2 hoặc chronic)──► RCA_Required → Closed
New → Cancelled
```

| State | Trigger | Actor | Auto-action |
|---|---|---|---|
| New | IR submit | Reporting User | SLA timer bắt đầu |
| Acknowledged | Workshop Mgr xác nhận | Workshop Manager | response_at set; priority set; recalculate SLA deadlines |
| In_Progress | Repair WO mở và assign | Workshop Manager | IR.repair_wo linked |
| Resolved | Repair WO completed | KTV HTM / WM | resolved_at set; downtime_hours tính; trigger_rca_if_required() |
| RCA_Required | P1/P2 Resolved hoặc chronic | System | RCA Record auto-created |
| Closed | RCA Completed (nếu cần) + repair_wo Completed | Workshop Manager / PTP | closed_at set; Asset.open_incident_count -= 1 |
| Cancelled | False alarm / duplicate | Workshop Manager | Lý do bắt buộc; SLA log ghi cancel |

---

## 5. Business Rules (BR-12-01 đến BR-12-05)

| Mã | Rule | Cơ chế kiểm soát |
|---|---|---|
| BR-12-01 | P1 phải Acknowledged trong 30 phút — nếu không, auto-escalate BGĐ + PTP | Scheduler 30 phút; sla_response_breached = True |
| BR-12-02 | SLA timer 24/7 tuyệt đối — không pause theo giờ hành chính | Tính bằng giờ thực (timedelta), không có business hours logic |
| BR-12-03 | ≥3 incidents cùng fault_code trên cùng asset trong 90 ngày → auto-open RCA (chronic failure) | Scheduler daily 02:00: detect_chronic_failures() |
| BR-12-04 | P1/P2: bắt buộc RCA sau Resolved — không thể Close khi RCA chưa Completed | validate() block Close; rca_required flag |
| BR-12-05 | Mỗi SLA breach → ghi SLA Compliance Log — không thể xóa hoặc sửa | is_immutable = True; no delete permission trên DocType |

---

## 6. DocTypes cần tạo

| DocType | Naming | Type | Ghi chú |
|---|---|---|---|
| `Incident Report` | IR-YYYY-##### | Submittable | Record chính của module |
| `SLA Compliance Log` | Auto | Non-submittable | Immutable audit log |
| `RCA Record` | RCA-YYYY-##### | Submittable | Root Cause Analysis |
| `RCA Related Incident` | — | Child Table | Child của RCA Record |

Custom fields cần thêm vào `Asset`:

- `custom_total_downtime_hours` (Float)
- `custom_open_incident_count` (Int)
- `custom_last_incident_date` (Date)
- `custom_chronic_failure_flag` (Check)
- `custom_sla_compliance_rate_ytd` (Float)
- `custom_mttr_days` (Float)

---

## 7. Integration Points

| Từ | Đến | Trigger | Mô tả |
|---|---|---|---|
| IMM-12 | IMM-09 | IR Acknowledged | Tạo Corrective Maintenance WO (Asset Repair) |
| IMM-08 | IMM-12 | PM phát hiện lỗi major | Tạo IR P2 tự động từ PM Work Order |
| IMM-11 | IMM-12 | Calibration failure với clinical impact | Tạo IR P2 tự động |
| IMM-12 | Asset | IR P1/P2 Acknowledged | Asset.status → Out_of_Service |
| IMM-12 | Asset | IR Resolved | Cộng dồn downtime_hours; cập nhật last_incident_date |
| IMM-12 | Asset Lifecycle Event | Mọi state change | Tạo event với from_status / to_status / actor |

---

## 8. Dependencies

| Module / DocType | Cần gì | Ghi chú |
|---|---|---|
| IMM-04 (Installation) | Asset phải tồn tại và có status Active | Tiền điều kiện tạo IR |
| IMM-05 (Registration) | Thông tin location, department, risk_class trên Asset | Auto-fill khi tạo IR |
| IMM-09 (Asset Repair) | DocType Asset Repair phải tồn tại | IR link sang repair_wo |
| Frappe User | reported_by, acknowledged_by, assigned_to, resolved_by | Permission check theo role |
| Frappe Scheduler | Chạy check_sla_breaches mỗi 30 phút; detect_chronic_failures mỗi ngày 02:00 | hooks.py cần cấu hình |
| Frappe Email | frappe.sendmail cho escalation và daily report | Email account phải được cấu hình |

---

## 9. QMS Mapping

| Yêu cầu IMM-12 | WHO HTM 2025 | ISO 9001:2015 | NĐ98/2021 |
|---|---|---|---|
| Incident reporting system | §5.3.4 | §8.7 Nonconforming outputs | Điều 38 |
| SLA tracking & compliance | §6.2 | §9.1.1 Monitoring and measurement | Điều 36 |
| RCA bắt buộc P1/P2 | §5.3.4 | §10.2 Corrective action | Điều 38 |
| Chronic failure detection | §5.4 | §10.2.1(b) Eliminate causes | — |
| SLA breach immutable log | §6.4 | §7.5.3 Control of documented information | Điều 7 |
| Lifecycle Event mọi state change | §6.4 | §7.5.1 Documented information | Điều 7 |
| RCA completion tracking (KPI) | §5.4 | §10.2.2 Retain documented information | — |

---

## 10. KPI & Metrics

| KPI | Định nghĩa | Nguồn dữ liệu | Mục tiêu |
|---|---|---|---|
| SLA Response Compliance (%) | IR đáp ứng response SLA / tổng IR | SLA Compliance Log | ≥ 95% |
| SLA Resolution Compliance (%) | IR giải quyết trong SLA / tổng IR | SLA Compliance Log | ≥ 90% |
| P1 SLA Compliance (%) | P1 IR đáp ứng cả response + resolution SLA | SLA Compliance Log | 100% |
| MTTR (Mean Time to Resolve) | Trung bình (resolved_at - reported_at) theo tháng | Incident Report | Giảm dần |
| Chronic Failure Rate | Số asset có chronic flag / tổng asset active | Asset (custom_chronic_failure_flag) | 0 asset |
| RCA Completion On-Time (%) | RCA hoàn thành trước due_date / tổng RCA | RCA Record | ≥ 95% |
| Open P1/P2 Incidents | Số IR P1/P2 đang mở hiện tại | Incident Report | 0 mục tiêu |
