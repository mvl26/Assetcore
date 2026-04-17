# IMM-08 — UAT Test Script
## Kịch bản kiểm thử chấp nhận người dùng

**Module:** IMM-08 — Preventive Maintenance  
**Version:** 1.0  
**Ngày:** 2026-04-17  
**Môi trường:** UAT / Staging  
**Người phê duyệt:** Workshop Manager, PTP Khối 2

---

## Dữ liệu seed cần chuẩn bị trước UAT

```python
# Chạy trên bench console trước khi bắt đầu UAT
# 1. Asset có PM Schedule với next_due_date = hôm nay
# 2. Asset có PM Schedule với next_due_date = 10 ngày trước (overdue)
# 3. PM Checklist Template cho category "Mechanical Ventilator"
# 4. User roles: KTV HTM, Workshop Manager, PTP Khối 2
```

| Mã seed | Thiết bị | PM Type | next_due_date | Ghi chú |
|---|---|---|---|---|
| SEED-PM-01 | ACC-ASS-UAT-001 | Quarterly | Hôm nay | Case chuẩn |
| SEED-PM-02 | ACC-ASS-UAT-002 | Annual | -10 ngày | Case trễ hạn |
| SEED-PM-03 | ACC-ASS-UAT-003 | Quarterly | Hôm nay | Case fail sau PM |
| SEED-PM-04 | ACC-ASS-UAT-004 | Quarterly | Hôm nay | Case thiết bị Out of Service |

---

## TC-PM-01: Tự động tạo PM Work Order

**Loại:** Case chuẩn  
**Actor:** CMMS Scheduler → Workshop Manager  
**Mục tiêu:** Xác nhận scheduler tạo WO tự động khi PM đến hạn  
**Thiết bị seed:** SEED-PM-01

| Bước | Hành động | Dữ liệu đầu vào | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|---|
| 1 | Chạy scheduler thủ công: `bench --site miyano execute assetcore.tasks.generate_pm_work_orders` | — | Không có lỗi | ☐ |
| 2 | Truy cập `/pm/work-orders`, tìm WO cho ACC-ASS-UAT-001 | — | PM-WO mới có status = "Open", due_date = hôm nay | ☐ |
| 3 | Kiểm tra Workshop Manager nhận notification | — | Có notification "PM Work Order mới được tạo" | ☐ |
| 4 | Mở PM Calendar `/pm/calendar` | — | SEED-PM-01 hiển thị trên ngày hôm nay với màu vàng 🟡 | ☐ |
| 5 | Chạy scheduler lần 2 (idempotent test) | — | **Không** tạo WO mới thứ 2 cho SEED-PM-01 | ☐ |

**Kết quả tổng hợp TC-PM-01:** ☐ Pass  ☐ Fail  
**Ghi chú:**

---

## TC-PM-02: Phân công và thực hiện PM đúng hạn (Case chuẩn)

**Loại:** Case chuẩn — Happy Path  
**Actor:** Workshop Manager → KTV HTM  
**Mục tiêu:** Hoàn thành PM WO đầy đủ, lịch tự động cập nhật  
**Tiền điều kiện:** TC-PM-01 Pass, PM-WO tồn tại cho SEED-PM-01

| Bước | Hành động | Dữ liệu đầu vào | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|---|
| 1 | Workshop Manager vào `/pm/work-orders`, mở WO của SEED-PM-01 | — | WO hiển thị đầy đủ checklist từ template | ☐ |
| 2 | Assign KTV HTM cho WO | User: `ktv_test@hospital.vn` | WO.assigned_to được cập nhật, KTV nhận notification | ☐ |
| 3 | Đăng nhập với tài khoản KTV, truy cập WO | — | WO hiển thị trong danh sách "Được phân công cho tôi" | ☐ |
| 4 | KTV điền từng mục checklist với kết quả Pass | Tất cả = Pass, giá trị đo trong range | Progress bar đạt 100% | ☐ |
| 5 | KTV điền ghi chú tổng thể và thời gian | Notes: "Hoàn thành bình thường", Time: 45 phút | Form hợp lệ, nút "Hoàn thành" enable | ☐ |
| 6 | KTV tích "Đã gắn sticker PM" | ✓ | Checkbox checked | ☐ |
| 7 | KTV bấm "Hoàn thành" | — | WO.status = "Completed", completion_date = today | ☐ |
| 8 | Kiểm tra PM Schedule | — | `last_pm_date = today`, `next_due_date = today + 90` | ☐ |
| 9 | Kiểm tra PM Task Log | — | Log entry mới: timestamp, KTV, result=Pass, is_late=False | ☐ |
| 10 | Kiểm tra Asset custom fields | — | `custom_last_pm_date = today`, `custom_next_pm_date = today+90`, `custom_pm_status = "On Schedule"` | ☐ |
| 11 | Kiểm tra Calendar | — | Event chuyển màu xanh 🟢, next PM xuất hiện đúng ngày | ☐ |

**Kết quả tổng hợp TC-PM-02:** ☐ Pass  ☐ Fail  
**Ghi chú:**

---

## TC-PM-03: PM Work Order trễ hạn (Overdue)

**Loại:** Case trễ hạn  
**Actor:** CMMS Scheduler → Workshop Manager → PTP Khối 2  
**Mục tiêu:** Xác nhận cơ chế phát hiện trễ, cảnh báo leo thang  
**Thiết bị seed:** SEED-PM-02 (next_due_date = 10 ngày trước)

| Bước | Hành động | Dữ liệu đầu vào | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|---|
| 1 | Tạo PM WO cho SEED-PM-02 (nếu chưa có) | — | WO với due_date = 10 ngày trước, status = "Open" | ☐ |
| 2 | Chạy: `bench --site miyano execute assetcore.tasks.check_pm_overdue` | — | WO.status = "Overdue" | ☐ |
| 3 | Kiểm tra Dashboard `/pm/dashboard` | — | SEED-PM-02 xuất hiện trong bảng "Quá hạn" màu đỏ 🔴 | ☐ |
| 4 | Kiểm tra notification Workshop Manager | — | Alert "PM quá hạn 10 ngày" gửi đến Workshop Manager | ☐ |
| 5 | Kiểm tra notification PTP | — | Alert gửi PTP vì > 7 ngày | ☐ |
| 6 | Kiểm tra Calendar view | — | Event màu đỏ 🔴 trên ngày due_date (10 ngày trước) | ☐ |
| 7 | Truy cập WO, kiểm tra warning banner | — | Banner đỏ: "PM QUÁ HẠN 10 NGÀY" với nút [Hoãn lịch] | ☐ |
| 8 | KTV hoàn thành WO trễ (submit) | Tất cả = Pass | WO.status = "Completed", **is_late = True**, days_late = 10 | ☐ |
| 9 | Kiểm tra PM Task Log | — | Log: is_late=True, days_late=10, next_pm_date = today+90 | ☐ |
| 10 | Kiểm tra PM compliance KPI sau | — | Compliance rate giảm (1 WO Late trong tháng) | ☐ |

**Kết quả tổng hợp TC-PM-03:** ☐ Pass  ☐ Fail  
**Ghi chú:**

---

## TC-PM-04: PM phát hiện lỗi Minor

**Loại:** Case ngoại lệ — Minor Failure  
**Actor:** KTV HTM → Workshop Manager  
**Mục tiêu:** PM hoàn thành nhưng tạo CM WO tham chiếu  
**Thiết bị seed:** SEED-PM-01 (sau khi reset về Open)

| Bước | Hành động | Dữ liệu đầu vào | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|---|
| 1 | KTV mở PM WO, điền đa số mục = Pass | 9/10 = Pass | Progress 90% | ☐ |
| 2 | Đánh dấu 1 mục là "Fail – Minor" | Mục không phải Critical | Form vẫn cho phép tiếp tục | ☐ |
| 3 | Nhập mô tả lỗi | "Bộ lọc bụi bị xé rách nhẹ, cần thay thế" | Mô tả được lưu | ☐ |
| 4 | Hoàn thành các mục còn lại = Pass | — | Progress 100%, nút "Hoàn thành" enable | ☐ |
| 5 | Chọn overall_result = "Pass with Minor Issues" | — | Dropdown hiển thị đúng | ☐ |
| 6 | Submit WO | — | WO.status = "Completed" | ☐ |
| 7 | Kiểm tra CM WO tự động tạo | — | CM WO mới với source_pm_wo = PM WO này | ☐ |
| 8 | Kiểm tra CM WO có đủ thông tin | — | wo_type = Corrective, asset_ref đúng, priority = Normal | ☐ |
| 9 | Kiểm tra Asset.status | — | Vẫn "Active" (không bị ảnh hưởng bởi minor failure) | ☐ |

**Kết quả tổng hợp TC-PM-04:** ☐ Pass  ☐ Fail  
**Ghi chú:**

---

## TC-PM-05: PM phát hiện lỗi Major

**Loại:** Case ngoại lệ — Major Failure  
**Actor:** KTV HTM → Workshop Manager → PTP  
**Mục tiêu:** PM bị halt, thiết bị ngừng vận hành, CM WO khẩn  
**Thiết bị seed:** SEED-PM-03

| Bước | Hành động | Dữ liệu đầu vào | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|---|
| 1 | KTV mở PM WO cho SEED-PM-03 | — | Checklist hiển thị đầy đủ | ☐ |
| 2 | Đánh dấu mục Critical là "Fail – Major" | Mục is_critical = True | Warning hiện: "Đây là mục quan trọng!" | ☐ |
| 3 | Kiểm tra nút "Hoàn thành" | — | Nút **disabled**, chỉ hiện "Báo lỗi Major 🔴" | ☐ |
| 4 | Bấm "Báo lỗi Major" | — | Dialog xác nhận mở | ☐ |
| 5 | Nhập mô tả lỗi | "Compressor hỏng hoàn toàn, không tạo được áp suất" | Form hợp lệ | ☐ |
| 6 | Xác nhận báo lỗi | — | PM WO.status = "Halted – Major Failure" | ☐ |
| 7 | Kiểm tra Asset.status | — | Asset.status = "Out of Service" | ☐ |
| 8 | Kiểm tra CM WO khẩn | — | CM WO tạo với priority = "Critical", source_pm_wo = PM WO | ☐ |
| 9 | Kiểm tra notification | — | Alert gửi ngay Workshop Manager + PTP + khoa phòng | ☐ |
| 10 | Thử tạo PM WO mới cho SEED-PM-03 | — | **Blocked**: "Thiết bị đang Out of Service" | ☐ |
| 11 | Sau khi CM hoàn thành, restore asset | Asset.status = "Active" | PM WO mới có thể tạo | ☐ |

**Kết quả tổng hợp TC-PM-05:** ☐ Pass  ☐ Fail  
**Ghi chú:**

---

## TC-PM-06: Block PM cho thiết bị Out of Service

**Loại:** Case nghiệp vụ — BR-08-04  
**Actor:** CMMS Scheduler  
**Mục tiêu:** Xác nhận BR-08-04 — không tạo WO khi asset Out of Service  
**Thiết bị seed:** SEED-PM-04 (set status = "Out of Service" trước)

| Bước | Hành động | Dữ liệu đầu vào | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|---|
| 1 | Set SEED-PM-04 Asset.status = "Out of Service" | `frappe.db.set_value("Asset", "ACC-ASS-UAT-004", "status", "Out of Service")` | Done | ☐ |
| 2 | Chạy `generate_pm_work_orders` | — | **Không** tạo WO cho SEED-PM-04 | ☐ |
| 3 | Restore Asset.status = "Active" | — | Done | ☐ |
| 4 | Chạy lại `generate_pm_work_orders` | — | WO được tạo bình thường | ☐ |

**Kết quả tổng hợp TC-PM-06:** ☐ Pass  ☐ Fail  
**Ghi chú:**

---

## TC-PM-07: Calendar View và Điều phối lịch

**Loại:** UI/UX  
**Actor:** Workshop Manager  
**Mục tiêu:** Xác nhận calendar hiển thị đúng và reschedule hoạt động

| Bước | Hành động | Dữ liệu đầu vào | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|---|
| 1 | Truy cập `/pm/calendar` | — | Calendar tháng hiện tại với các WO được màu hóa | ☐ |
| 2 | Chuyển sang tuần view | [Tuần] button | WO theo ngày trong tuần hiển thị | ☐ |
| 3 | Click vào WO event | — | Drawer slide-in hiển thị chi tiết WO | ☐ |
| 4 | Filter theo KTV | KTV: ktv_test | Chỉ hiện WO của KTV đó | ☐ |
| 5 | Reschedule WO (hoãn 3 ngày) | new_date = today + 3, reason = "Device busy" | Dialog xác nhận, WO.due_date cập nhật | ☐ |
| 6 | Kiểm tra lý do hoãn được ghi lại | — | reschedule_reason lưu trong WO | ☐ |

**Kết quả tổng hợp TC-PM-07:** ☐ Pass  ☐ Fail  
**Ghi chú:**

---

## TC-PM-08: PM Dashboard KPI

**Loại:** Reporting  
**Actor:** PTP Khối 2  
**Mục tiêu:** Xác nhận KPI tính toán chính xác

| Bước | Hành động | Dữ liệu đầu vào | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|---|
| 1 | Truy cập `/pm/dashboard` | — | Dashboard load đủ 5 KPI cards | ☐ |
| 2 | Kiểm tra Compliance Rate | Sau khi chạy TC-PM-02, 03, 04, 05 | Rate = (WO completed on time) / (total scheduled) × 100% | ☐ |
| 3 | Kiểm tra bảng "Quá hạn" | — | Chỉ hiện WO có status = Overdue | ☐ |
| 4 | Kiểm tra trend 6 tháng | — | Biểu đồ có dữ liệu từ tháng hiện tại trở về | ☐ |
| 5 | Filter theo tháng khác | [Tháng 3/2026 ▼] | Dashboard cập nhật theo tháng được chọn | ☐ |

**Kết quả tổng hợp TC-PM-08:** ☐ Pass  ☐ Fail  
**Ghi chú:**

---

## TC-PM-09: PM Schedule tự động tạo từ IMM-04

**Loại:** Integration test (IMM-04 → IMM-08)  
**Actor:** KTV HTM (commissioning) → CMMS  
**Mục tiêu:** Xác nhận khi commissioning submit → PM Schedule tự động tạo

| Bước | Hành động | Dữ liệu đầu vào | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|---|
| 1 | Tạo và submit Asset Commissioning mới | Asset category = "Mechanical Ventilator" | Commissioning submitted | ☐ |
| 2 | Kiểm tra PM Schedule | — | PM Schedule mới tạo với asset = vừa commissioning | ☐ |
| 3 | Kiểm tra PM Schedule đúng interval | — | pm_interval_days theo template của category | ☐ |
| 4 | Kiểm tra first_pm_date | — | `next_due_date = commissioning_date + interval` | ☐ |
| 5 | Kiểm tra `created_from_commissioning` | — | Link tới đúng commissioning record | ☐ |

**Kết quả tổng hợp TC-PM-09:** ☐ Pass  ☐ Fail  
**Ghi chú:**

---

## TC-PM-10: Mobile Checklist UX

**Loại:** Mobile UX  
**Actor:** KTV HTM (trên điện thoại)  
**Mục tiêu:** Xác nhận trải nghiệm mobile hoạt động đúng

| Bước | Hành động | Device | Kết quả kỳ vọng | Pass/Fail |
|---|---|---|---|---|
| 1 | Mở WO trên điện thoại (375px viewport) | Android Chrome | Layout mobile hiển thị một mục/màn hình | ☐ |
| 2 | Nút Pass/Fail đủ lớn (≥48px) | — | Tap không bị nhầm nút | ☐ |
| 3 | Swipe để chuyển mục | Swipe right/left | Chuyển sang mục tiếp theo/trước | ☐ |
| 4 | Chụp ảnh tích hợp | Camera button | Camera mở, ảnh tự gắn vào mục | ☐ |
| 5 | Mất kết nối giữa chừng | Tắt WiFi sau khi điền 5/10 mục | Dữ liệu lưu offline | ☐ |
| 6 | Khôi phục kết nối | Bật WiFi lại | Dữ liệu sync, tiếp tục từ mục 6 | ☐ |

**Kết quả tổng hợp TC-PM-10:** ☐ Pass  ☐ Fail  
**Ghi chú:**

---

## Tổng hợp kết quả UAT

| Test Case | Mô tả | Kết quả | Người ký |
|---|---|---|---|
| TC-PM-01 | Tự động tạo PM WO | ☐ Pass / ☐ Fail | |
| TC-PM-02 | PM hoàn thành đúng hạn | ☐ Pass / ☐ Fail | |
| TC-PM-03 | PM trễ hạn & cảnh báo | ☐ Pass / ☐ Fail | |
| TC-PM-04 | PM phát hiện lỗi Minor | ☐ Pass / ☐ Fail | |
| TC-PM-05 | PM phát hiện lỗi Major | ☐ Pass / ☐ Fail | |
| TC-PM-06 | Block PM cho Out of Service | ☐ Pass / ☐ Fail | |
| TC-PM-07 | Calendar & Reschedule | ☐ Pass / ☐ Fail | |
| TC-PM-08 | Dashboard KPI | ☐ Pass / ☐ Fail | |
| TC-PM-09 | Tích hợp IMM-04 → IMM-08 | ☐ Pass / ☐ Fail | |
| TC-PM-10 | Mobile Checklist UX | ☐ Pass / ☐ Fail | |

**Ngưỡng chấp nhận (Definition of Done):**
- ≥ 8/10 Test Cases Pass
- TC-PM-01, 02, 03, 05 bắt buộc Pass (core functionality)
- Không có Critical bug chưa được xử lý

---

## Điều kiện thất bại & Escalation

| Tình huống | Hành động |
|---|---|
| TC-PM-05 (Major Failure) không block WO mới | Blocker — không release |
| TC-PM-03 (Overdue) không gửi alert PTP | Major — phải fix trước release |
| TC-PM-09 (IMM-04 integration) fail | Blocker — PM Schedule không tồn tại |
| Calendar view không hiển thị đúng màu | Minor — có thể release với workaround |
| Mobile offline sync không hoạt động | Minor — document limitation, fix in next sprint |

---

*Tài liệu này được tạo bởi AssetCore Team — 2026-04-17*  
*Cần ký phê duyệt trước khi bắt đầu thực thi UAT.*
