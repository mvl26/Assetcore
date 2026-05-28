# BÁO CÁO LỖI - KIỂM THỬ HỆ THỐNG ASSETCORE IMM
**Ngày kiểm thử:** 27/05/2026  
**Người kiểm thử:** QA Tester  
**Hệ thống:** AssetCore v0.0.2 — Bệnh viện Nhi Đồng 1  
**URL gốc:** http://localhost:3000  
**Phạm vi:** Toàn bộ Launcher (13 module hoạt động)

---

## TỔNG KẾT

| Mức độ | Số lỗi |
|--------|--------|
| CRITICAL | 2 |
| HIGH | 7 |
| MEDIUM | 6 |
| LOW | 4 |
| Tổng | 19 |

---

## LỖI CRITICAL

### BUG-001: Lưu đo lường trong IMM-11 không ghi vào database
Module: IMM-11 Hiệu năng & Hiệu chuẩn
Trang: Chi tiết phiếu hiệu chuẩn
URL: http://localhost:3000/calibration/{mã_phiếu}
Input: Nhấn + Thêm tham số, nhập dữ liệu đo lường (Tham số, Đơn vị, Danh định, Dung sai, Đo được), nhấn Lưu
Output mong muốn: Dữ liệu đo lường được lưu vào database
Output thực tế: Hàm save() trong component CalibrationDetail KHÔNG serialize form.measurements vào payload API assetcore.api.imm11.update_calibration. Dữ liệu chỉ tồn tại trong Vue state, không persist xuống DB.
Hậu quả: Nút Gửi duyệt luôn thất bại với lỗi CAL-005 vì server kiểm tra measurements trong DB.
Root cause: Frontend bug - save() function không include form.measurements trong data spread.

### BUG-002: Deadlock logic - không thể phê duyệt đề xuất nhu cầu
Module: IMM-01 Đánh giá nhu cầu & Dự toán
Trang: Chi tiết đề xuất - tab Dự toán
URL: http://localhost:3000/needs-requests/{mã_phiếu}
Input: Phiếu ở trạng thái Chờ phê duyệt, nhấn Phê duyệt, điền Administrator, xác nhận
Output mong muốn: Phiếu chuyển sang Đã duyệt
Output thực tế: Lỗi G05: Thiếu trường bắt buộc trước Submit: funding_source. Khi phiếu đã ở Chờ phê duyệt, nút Chỉnh sửa dự toán biến mất, người dùng không thể điền Nguồn vốn.
Hậu quả: Phiếu bị kẹt vĩnh viễn ở Chờ phê duyệt.
Root cause: Logic lỗi - hệ thống yêu cầu funding_source nhưng khóa chỉnh sửa trước khi validate.

---

## LỖI HIGH

### BUG-003: Thông báo lỗi dùng tên field tiếng Anh
Module: IMM-01
URL: http://localhost:3000/needs-requests/{mã_phiếu}
Input: Nhấn Hoàn tất chấm điểm khi chưa lưu điểm, hoặc Hoàn tất dự toán khi thiếu nguồn vốn
Output mong muốn: Thông báo lỗi bằng tiếng Việt thân thiện
Output thực tế: G02: Thiếu tiêu chí chấm điểm: budget_fit, clinical_impact, compliance_gap, replacement_signal, risk, utilization_gap; G05: Thiếu trường bắt buộc trước Submit: funding_source
Mô tả: Tên field dùng snake_case tiếng Anh thay vì nhãn tiếng Việt.

### BUG-004: Thông báo OPEX dùng số thứ tự thay vì năm thực
Module: IMM-01
URL: http://localhost:3000/needs-requests/{mã_phiếu}
Input: Nhấn Hoàn tất dự toán khi chưa điền đủ 5 năm OPEX
Output mong muốn: thiếu năm: 2026, 2027, 2028, 2029, 2030
Output thực tế: G03: Phải có OPEX 5 năm liên tục - thiếu năm: [1, 2, 3, 4, 5]
Mô tả: Hiển thị index thay vì năm thực gây nhầm lẫn.

### BUG-005: Trọng số chấm điểm bị thay đổi sau khi lưu
Module: IMM-01
URL: http://localhost:3000/needs-requests/{mã_phiếu}
Input: Nhập trọng số 30%, 20%, 20%, 10%, 10%, 10%, nhấn Lưu chấm điểm
Output mong muốn: Trọng số lưu nguyên: 30%, 20%, 20%, 10%, 10%, 10%
Output thực tế: Sau khi lưu, trọng số bị tái phân bổ: 25%, 20%, 15%, 15%, 15%, 10%
Mô tả: Backend tự động tái phân bổ trọng số không có thông báo.

### BUG-006: Trường nhập người duyệt BGĐ không có autocomplete
Module: IMM-01
URL: http://localhost:3000/needs-requests/{mã_phiếu} (dialog phê duyệt)
Input: Nhấn Phê duyệt, điền email không tồn tại
Output mong muốn: Dropdown/autocomplete chọn user có role BGĐ
Output thực tế: Field tự do, nhập email sai → lỗi Could not find Người phê duyệt BGĐ: {email}
Mô tả: UX kém, người dùng không biết email/username hợp lệ.

### BUG-007: Nhãn tiếng Anh trong IMM-08 (PM)
Module: IMM-08
URL: http://localhost:3000/pm/work-orders, http://localhost:3000/pm/work-orders/{mã}
Input: Xem danh sách và chi tiết phiếu bảo trì
Output mong muốn: Tất cả nhãn tiếng Việt
Output thực tế: Loại PM: Quarterly, Semi-Annual; Mức rủi ro: Medium; Loại phiếu: Preventive
Mô tả: Giá trị enum chưa được dịch sang tiếng Việt.

### BUG-008: Button Hoàn thành bảo trì vẫn xanh dù không có quyền
Module: IMM-08
URL: http://localhost:3000/pm/work-orders/PM-WO-2026-00029
Input: Hover lên nút Hoàn thành bảo trì
Output mong muốn: Nút disabled (màu xám) khi không có quyền
Output thực tế: Nút màu xanh lá, chỉ có tooltip Bạn không có quyền hoàn thành bảo trì khi hover
Mô tả: Vi phạm UX - nút cần disabled khi thiếu quyền.

### BUG-009: Nhãn tiếng Anh trong IMM-09 và IMM-12
Module: IMM-09, IMM-12
URL: http://localhost:3000/cm/dashboard, http://localhost:3000/incidents/dashboard
Input: Xem dashboard
Output mong muốn: Tất cả nhãn tiếng Việt
Output thực tế: IMM-09: Software, Wear and Tear, Electrical, Urgent. IMM-12: Critical, Critical Incident, Major Incident, RCA Required
Mô tả: Nhiều giá trị enum chưa localize.

---

## LỖI MEDIUM

### BUG-010: Tổng CAPEX không cập nhật realtime khi nhập
Module: IMM-01
URL: http://localhost:3000/needs-requests/{mã_phiếu}
Input: Nhập đơn giá vào CAPEX
Output mong muốn: Tổng cập nhật ngay
Output thực tế: Tổng hiển thị 0đ đến khi nhấn Lưu dự toán

### BUG-011: IMM-02 tải chậm hơn 3 giây
Module: IMM-02
URL: http://localhost:3000/tech-specs
Input: Điều hướng vào trang
Output mong muốn: Tải < 1 giây
Output thực tế: Hiển thị Đang tải... trong >3 giây

### BUG-012: Cột Điểm phụ thuộc trong danh sách IMM-02 luôn là dash
Module: IMM-02
URL: http://localhost:3000/tech-specs
Input: Xem danh sách
Output mong muốn: Hiển thị điểm phụ thuộc từng hồ sơ
Output thực tế: Tất cả cột ĐIỂM PHỤ THUỘC hiển thị -- trong khi KPI tổng hiển thị 2.40

### BUG-013: Cột bị cắt trong IMM-04
Module: IMM-04
URL: http://localhost:3000/commissioning
Input: Xem danh sách
Output mong muốn: Hiển thị đầy đủ tên cột
Output thực tế: Cột cuối chỉ hiện TÀI (bị truncate)

### BUG-014: Mâu thuẫn SLA 100% vs 0% trong IMM-09
Module: IMM-09
URL: http://localhost:3000/cm/dashboard
Input: Xem dashboard
Output mong muốn: Dữ liệu nhất quán
Output thực tế: KPI card = 100% nhưng biểu đồ 6 tháng đều SLA 0%

### BUG-015: KPI Chờ RCA = 0 nhưng widget RCA đang mở = 6 hồ sơ
Module: IMM-12
URL: http://localhost:3000/incidents/dashboard
Input: Xem dashboard
Output mong muốn: KPI Chờ RCA phản ánh đúng số thực
Output thực tế: KPI = 0, widget liệt kê 6 RCA chưa hoàn thành

---

## LỖI LOW

### BUG-016: Cột OPEX hiển thị Năm 1, 2, 3 thay vì năm thực
Module: IMM-01
URL: http://localhost:3000/needs-requests/{mã_phiếu}
Output thực tế: Năm 1, Năm 2, Năm 3, Năm 4, Năm 5
Output mong muốn: Năm 2026, Năm 2027, Năm 2028, Năm 2029, Năm 2030

### BUG-017: KPI danh sách không cập nhật theo filter
Module: IMM-01
URL: http://localhost:3000/needs-requests
Input: Filter theo trạng thái Đã duyệt
Output thực tế: KPI vẫn tính toàn bộ 6 phiếu dù chỉ hiển thị 3 phiếu

### BUG-018: Module đang phát triển không disable click
Module: Launcher
URL: http://localhost:3000/launcher
Output thực tế: Click vào IMM-07, IMM-10, IMM-13, IMM-14, IMM-17 dẫn đến trang lỗi hoặc trống

### BUG-019: CAL-005 gây nhầm lẫn vì người dùng thấy tham số đã nhập
Module: IMM-11
URL: http://localhost:3000/calibration/{mã_phiếu}
Output thực tế: Lỗi CAL-005 Phải nhập ít nhất 1 tham số đo dù người dùng đã nhập (do BUG-001 không lưu được)
Mô tả: Thông báo lỗi đúng về mặt kỹ thuật nhưng gây nhầm lẫn cho người dùng.

---

## MODULE ĐÃ KIỂM THỬ

IMM-01 /needs-requests - Kiểm thử đầy đủ (toàn bộ workflow từ Draft -> Approved)
IMM-02 /tech-specs - Kiểm thử cơ bản
IMM-03 /vendor-evaluations - Kiểm thử cơ bản
IMM-04 /commissioning - Kiểm thử cơ bản
IMM-05 /documents - Điều hướng cơ bản
IMM-06 /training - Điều hướng cơ bản
IMM-07 - Đang phát triển (không test)
IMM-08 /pm/dashboard và /pm/work-orders - Kiểm thử đầy đủ
IMM-09 /cm/dashboard - Kiểm thử cơ bản
IMM-10 - Đang phát triển (không test)
IMM-11 /calibration - Kiểm thử đầy đủ (từ session trước + session này)
IMM-12 /incidents/dashboard - Kiểm thử cơ bản
IMM-13 - Đang phát triển (không test)
IMM-14 - Đang phát triển (không test)
IMM-15 /inventory - Kiểm thử cơ bản
IMM-16 /compliance/findings - Kiểm thử cơ bản
IMM-17 - Đang phát triển (không test)

## DATA ĐÃ TẠO

NR-26-05-00017: Đề xuất mua máy gây mê Khoa Mổ - trạng thái Chờ phê duyệt (bị deadlock BUG-002)
CAL-2026-00017: Phiếu hiệu chuẩn đã hủy (từ session trước)
CAL-2026-00016: Phiếu hiệu chuẩn đang thực hiện (từ session trước)

---
Báo cáo được tạo: 27/05/2026 - AssetCore v0.0.2
