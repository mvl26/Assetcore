# BÁO CÁO KIỂM THỬ ASSETCORE v0.0.2
## Bệnh viện Nhi Đồng 1 — Kiểm thử toàn diện 13 module
**Ngày kiểm thử:** 27/05/2026  
**Người kiểm thử:** Administrator  
**Môi trường:** localhost:3000 (Development)  
**Phiên bản:** AssetCore v0.0.2  

---

## TỔNG QUAN

| Mức độ | Số lỗi |
|--------|--------|
| 🔴 CRITICAL | 3 |
| 🟠 HIGH | 14 |
| 🟡 MEDIUM | 10 |
| 🔵 LOW | 5 |
| **TỔNG** | **32** |

---

## CHI TIẾT LỖI

### BUG-001 — CRITICAL: Không lưu được tham số đo lường trong Hiệu chuẩn
- **Module:** IMM-11 · Hiệu chuẩn  
- **URL:** /calibration/CAL-2026-00016  
- **Input:** Click "+ Thêm tham số" → nhập Tham số="Axial Resolution", Đơn vị="mm", Danh định="0.5", Dung sai="10", Đo được="0.48" → Click "Lưu"  
- **Output mong muốn:** Tham số đo lường được lưu và hiển thị trong bảng  
- **Output thực tế:** Trang reload lại đầu, mục "Tham số đo lường" vẫn hiển thị "Chưa có tham số đo." — dữ liệu mất hoàn toàn  
- **Mô tả lỗi:** Button "Lưu" không lưu được dữ liệu tham số đo lường. Không có thông báo lỗi hay xác nhận. Ảnh hưởng toàn bộ quy trình hiệu chuẩn thiết bị y tế.

---

### BUG-002 — CRITICAL: Deadlock phê duyệt đề xuất nhu cầu — trường funding_source không thể điền qua UI
- **Module:** IMM-01 · Đề xuất nhu cầu  
- **URL:** /needs-requests/NR-26-05-00017  
- **Input:** Trạng thái "Chờ phê duyệt" → Click "Phê duyệt" → Nhập "Administrator" → Click "Xác nhận phê duyệt"  
- **Output mong muốn:** Đề xuất được phê duyệt, chuyển sang trạng thái "Đã duyệt"  
- **Output thực tế:** Lỗi "G05: Thiếu trường bắt buộc trước Submit: funding_source" — không thể phê duyệt  
- **Mô tả lỗi:** Trường funding_source bắt buộc khi phê duyệt nhưng: (1) Không có UI để điền ở bước Dự toán (nút "Chỉnh sửa dự toán" biến mất sau khi hoàn tất dự toán), (2) API update_needs_request không lưu trường này (trả về success nhưng không save), (3) Chỉ có thể giải quyết bằng frappe.client.save trực tiếp. Deadlock nghiêm trọng ngăn toàn bộ luồng phê duyệt.

---

### BUG-003 — CRITICAL: SLA Compliance tính sai — WO quá hạn 332 giờ vẫn báo 100%
- **Module:** IMM-09 · Sửa chữa  
- **URL:** /cm/dashboard và /cm/work-orders/WO-CM-2026-00014  
- **Input:** Xem dashboard sửa chữa  
- **Output mong muốn:** SLA Compliance phản ánh tỷ lệ phiếu hoàn thành trong SLA thực tế  
- **Output thực tế:** Dashboard hiển thị "SLA Compliance: 100%" trong khi WO-CM-2026-00014 đã trôi qua 332.2 giờ so với SLA 24 giờ (quá hạn 13.8 ngày). Biểu đồ 6 tháng hiển thị "SLA 0%" mỗi tháng mâu thuẫn với KPI 100%.  
- **Mô tả lỗi:** Logic tính SLA Compliance sai nghiêm trọng. Có thể do: (1) Chỉ tính các phiếu đã hoàn thành, bỏ qua phiếu đang mở, (2) Hoặc công thức tính ngược. Gây hiểu nhầm nghiêm trọng cho quản lý.

---

### BUG-004 — HIGH: Nhãn tiếng Anh trong validation error — tên trường kỹ thuật hiện thị
- **Module:** IMM-01 · Đề xuất nhu cầu  
- **URL:** /needs-requests/NR-26-05-00016  
- **Input:** Click "Tiếp nhận rà soát" khi lý do lâm sàng < 200 ký tự  
- **Output mong muốn:** Thông báo lỗi: "Lý do lâm sàng phải ≥ 200 ký tự (hiện X ký tự)"  
- **Output thực tế:** "VR-01-03: clinical_justification phải ≥ 200 ký tự (hiện 117)."  
- **Mô tả lỗi:** Tên trường kỹ thuật "clinical_justification" hiện thị thay vì nhãn tiếng Việt. Cần map sang "Lý do lâm sàng".

---

### BUG-005 — HIGH: Dropdown "Loại sự cố" và "Severity" toàn tiếng Anh
- **Module:** IMM-12 · Sự cố & RCA  
- **URL:** /incidents/new  
- **Input:** Mở form Báo cáo sự cố, xem dropdown Loại sự cố và Severity  
- **Output mong muốn:** Hiển thị các tùy chọn tiếng Việt: "Hỏng hóc", "Sự cố an toàn", "Suýt xảy ra", "Trục trặc"; và "Thấp", "Trung bình", "Cao", "Nghiêm trọng"  
- **Output thực tế:** Loại sự cố: "Failure", "Safety Event", "Near Miss", "Malfunction"; Severity: "Low", "Medium", "High", "Critical"  
- **Mô tả lỗi:** Toàn bộ các tùy chọn trong 2 dropdown quan trọng đều bằng tiếng Anh, không phù hợp với người dùng bệnh viện Việt Nam.

---

### BUG-006 — HIGH: Nhiều nhãn tiếng Anh trong IMM-08 Bảo trì định kỳ
- **Module:** IMM-08 · Bảo trì định kỳ  
- **URL:** /pm/work-orders và /pm/work-orders/PM-WO-2026-00029  
- **Input:** Xem danh sách và chi tiết phiếu bảo trì  
- **Output mong muốn:** Tất cả nhãn bằng tiếng Việt  
- **Output thực tế:** Loại PM: "Quarterly", "Semi-Annual"; Mức rủi ro: "Medium"; Loại phiếu: "Preventive"; Xu hướng biểu đồ: "Compliance"  
- **Mô tả lỗi:** Nhiều thuộc tính hiển thị tiếng Anh: Loại PM nên là "Hàng quý"/"Nửa năm", Mức rủi ro nên là "Trung bình", Loại phiếu nên là "Bảo trì phòng ngừa", biểu đồ nên là "Xu hướng Tuân thủ".

---

### BUG-007 — HIGH: Quyền hạn sai — Administrator không thể hoàn thành bảo trì
- **Module:** IMM-08 · Bảo trì định kỳ  
- **URL:** /pm/work-orders/PM-WO-2026-00029  
- **Input:** Điền đủ checklist 3/3 (100%) + ghi chú kỹ thuật + thời gian 45 phút → Click "Hoàn thành bảo trì"  
- **Output mong muốn:** Phiếu bảo trì hoàn thành, trạng thái chuyển sang "Hoàn thành"  
- **Output thực tế:** Tooltip hiển thị "Bạn không có quyền hoàn thành bảo trì" — không thể thực hiện  
- **Mô tả lỗi:** Tài khoản Administrator có đầy đủ quyền (PM User, PM Manager) nhưng vẫn không thể hoàn thành bảo trì. Lỗi phân quyền nghiêm trọng ảnh hưởng toàn bộ luồng bảo trì.

---

### BUG-008 — HIGH: KPI "Quyết định mua sắm" sai — tất cả hiển thị 0 dù có 3 bản ghi
- **Module:** IMM-03 · Đánh giá nhà cung cấp (Quyết định mua sắm)  
- **URL:** /procurement-decisions  
- **Input:** Xem trang danh sách quyết định mua sắm  
- **Output mong muốn:** KPI phản ánh đúng: "Đã ký hợp đồng: 3"  
- **Output thực tế:** "Đã trao thầu: 0", "Chờ phê duyệt: 0", "Đã phát hành đơn hàng: 0" — tất cả bằng 0 dù có 3 bản ghi "Đã ký hợp đồng"  
- **Mô tả lỗi:** Trạng thái "Đã ký hợp đồng" không được ánh xạ vào bất kỳ KPI card nào. Danh sách cũng thiếu dữ liệu: cột "NHÀ CUNG CẤP TRÚNG THẦU" và "GIÁ TRÚNG THẦU" hiển thị "—" dù bản ghi chi tiết có đầy đủ thông tin.

---

### BUG-009 — HIGH: Dropdown chọn kế hoạch mua sắm không hoạt động khi click chuột
- **Module:** IMM-02 · Thông số kỹ thuật  
- **URL:** /tech-specs/new  
- **Input:** Click vào dropdown "Chọn kế hoạch mua sắm đã duyệt" → Click chọn "PP-26-00006"  
- **Output mong muốn:** PP-26-00006 được chọn, danh sách đề xuất hiện ra  
- **Output thực tế:** Dropdown reset về trạng thái ban đầu "— Chọn kế hoạch —", không có gì xảy ra  
- **Mô tả lỗi:** Sự kiện onChange của dropdown không kích hoạt khi click chuột trực tiếp. Chỉ hoạt động khi dùng công cụ tự động hóa (select element). Lỗi event handler trong Vue/React component.

---

### BUG-010 — HIGH: Error message sửa chữa hiển thị tiếng Anh lẫn tiếng Việt
- **Module:** IMM-09 · Sửa chữa  
- **URL:** /cm/work-orders/WO-CM-2026-00014/diagnose  
- **Input:** Click "Lưu chẩn đoán" khi thiếu dữ liệu  
- **Output mong muốn:** Thông báo lỗi hoàn toàn bằng tiếng Việt  
- **Output thực tế:** "Error: Value missing for Asset Repair: Mô tả lỗi"  
- **Mô tả lỗi:** "Error:", "Asset Repair:" là tiếng Anh. Nên là "Lỗi: Thiếu thông tin trong Phiếu sửa chữa: Mô tả lỗi".

---

### BUG-011 — HIGH: Nhãn tiếng Anh trong phân tích nguyên nhân hỏng (IMM-09 dashboard)
- **Module:** IMM-09 · Sửa chữa  
- **URL:** /cm/dashboard  
- **Input:** Xem dashboard tổng quan sửa chữa  
- **Output mong muốn:** "Phân tích nguyên nhân hỏng" hiển thị nhãn tiếng Việt  
- **Output thực tế:** "Software", "Wear and Tear", "Electrical" đều bằng tiếng Anh  
- **Mô tả lỗi:** Biểu đồ phân tích nguyên nhân hỏng dùng giá trị chuỗi từ DB làm nhãn, không có ánh xạ tiếng Việt. Cần: "Phần mềm", "Hao mòn", "Điện".

---

### BUG-012 — HIGH: Nhãn tiếng Anh trong danh sách RCA và các tag trên IMM-12
- **Module:** IMM-12 · Sự cố & RCA  
- **URL:** /incidents/dashboard  
- **Input:** Xem dashboard tổng quan sự cố  
- **Output mong muốn:** Tất cả tag/label tiếng Việt  
- **Output thực tế:** "Critical Incident", "Major Incident", "RCA Required" đều tiếng Anh; KPI "Critical" tiếng Anh; Incident "High" badge tiếng Anh  
- **Mô tả lỗi:** Loại sự cố và mức độ được lưu tiếng Anh trong DB, không được dịch khi hiển thị.

---

### BUG-013 — HIGH: Nhãn tiếng Anh trong vai trò chấm điểm IMM-03
- **Module:** IMM-03 · Đánh giá nhà cung cấp  
- **URL:** /vendor-evaluations/VE-26-00004 (tab Chấm điểm)  
- **Input:** Xem tab "Chấm điểm" trong chi tiết đánh giá NCC  
- **Output mong muốn:** Vai trò chấm điểm hiển thị tiếng Việt  
- **Output thực tế:** "IMM HTM Engineer", "IMM Finance Officer", "IMM Risk Officer" — tất cả tiếng Anh  
- **Mô tả lỗi:** Vai trò hệ thống hiện nguyên tên tiếng Anh, không có nhãn tiếng Việt.

---

### BUG-014 — HIGH: Trạng thái tài sản trong dropdown IMM-12 toàn tiếng Anh
- **Module:** IMM-12 · Sự cố  
- **URL:** /incidents/new (dropdown chọn thiết bị)  
- **Input:** Click vào trường "Thiết bị" trong form Báo cáo sự cố  
- **Output mong muốn:** Trạng thái hiển thị: "Đang hoạt động", "Ngừng hoạt động", "Đã bàn giao", "Đã thanh lý"  
- **Output thực tế:** "Active", "Out of Service", "Commissioned", "Decommissioned"  
- **Mô tả lỗi:** Trạng thái tài sản không được dịch sang tiếng Việt trong dropdown chọn thiết bị.

---

### BUG-015 — HIGH: Không có chức năng Sửa/Xóa cho Đề xuất nhu cầu ở trạng thái Nháp
- **Module:** IMM-01 · Đề xuất nhu cầu  
- **URL:** /needs-requests/NR-26-05-00016  
- **Input:** Xem chi tiết đề xuất ở trạng thái "Nhập" (Draft)  
- **Output mong muốn:** Có nút "Sửa" và "Xóa" để người dùng chỉnh sửa/hủy đề xuất  
- **Output thực tế:** Chỉ có nút "Gửi đề xuất". Không có nút sửa hay xóa. URL /needs-requests/{id}/edit trả về 404.  
- **Mô tả lỗi:** Thiếu chức năng CRUD cơ bản — người dùng không thể sửa nội dung đề xuất sau khi tạo.

---

### BUG-016 — HIGH: update_needs_request API không lưu trường funding_source
- **Module:** IMM-01 · Đề xuất nhu cầu (Backend)  
- **URL:** API /api/method/assetcore.api.imm01.update_needs_request  
- **Input:** POST với body {"name": "NR-26-05-00017", "funding_source": "NSNN"}  
- **Output mong muốn:** funding_source được lưu vào database  
- **Output thực tế:** API trả về {"success": true} nhưng giá trị funding_source vẫn là "" trong database  
- **Mô tả lỗi:** API bỏ qua (silently ignores) trường funding_source — không validate, không lưu, không báo lỗi. Gây ra deadlock BUG-002 vì không có cách nào set funding_source qua UI.

---

### BUG-017 — HIGH: Phê duyệt "Phát hành PO" gây treo trang (timeout)
- **Module:** IMM-03 · Quyết định mua sắm  
- **URL:** /procurement-decisions/PD-26-00005  
- **Input:** Click "Phát hành PO"  
- **Output mong muốn:** PO được phát hành, trạng thái chuyển sang "Đã phát hành đơn hàng"  
- **Output thực tế:** Page freeze hoàn toàn trong >30 giây, phải navigate đi chỗ khác để recover  
- **Mô tả lỗi:** Button "Phát hành PO" gây treo trang (có thể do API call không có timeout, vòng lặp vô hạn, hoặc deadlock DB).

---

### BUG-018 — MEDIUM: Nội dung tiếng Anh trong form Benchmark IMM-02
- **Module:** IMM-02 · Thông số kỹ thuật  
- **URL:** /tech-specs/TS-26-00007 (tab Benchmark)  
- **Input:** Xem tab Benchmark  
- **Output mong muốn:** Mô tả và gợi ý bằng tiếng Việt  
- **Output thực tế:** "Hệ thống sẽ recommend ứng viên có `weighted_score` cao nhất theo `weighting_scheme`." — tên trường kỹ thuật bằng tiếng Anh dùng backtick  
- **Mô tả lỗi:** Gợi ý kỹ thuật dùng tên trường backend thay vì nhãn tiếng Việt.

---

### BUG-019 — MEDIUM: Tab "Non Conformance" tiếng Anh trong IMM-04
- **Module:** IMM-04 · Lắp đặt & Nghiệm thu  
- **URL:** /commissioning/ACC-26-05-00007  
- **Input:** Xem chi tiết phiếu nghiệm thu  
- **Output mong muốn:** Tab có tên tiếng Việt "Sự không phù hợp"  
- **Output thực tế:** Tab hiển thị "Non Conformance" tiếng Anh; breadcrumb hiển thị "Non-Conformance"  
- **Mô tả lỗi:** Tab và breadcrumb dùng tên kỹ thuật tiếng Anh không nhất quán với nội dung bên trong.

---

### BUG-020 — MEDIUM: Tag NC category "Other" tiếng Anh trong IMM-04
- **Module:** IMM-04 · Lắp đặt & Nghiệm thu  
- **URL:** /commissioning/ACC-26-05-00007/nc  
- **Input:** Tạo NC với loại "Khác", xem danh sách NC  
- **Output mong muốn:** Tag hiển thị "Khác"  
- **Output thực tế:** Tag hiển thị "Other"  
- **Mô tả lỗi:** Loại NC "Other" lưu bằng tiếng Anh trong DB, không được dịch khi hiển thị.

---

### BUG-021 — MEDIUM: "Pending Parts" và "Firmware Change Request" tiếng Anh trong IMM-09
- **Module:** IMM-09 · Sửa chữa  
- **URL:** /cm/work-orders/WO-CM-2026-00014/diagnose  
- **Input:** Xem form chẩn đoán  
- **Output mong muốn:** "Cần vật tư — chuyển trạng thái Chờ linh kiện"; "sẽ yêu cầu tạo Yêu cầu cập nhật Firmware"  
- **Output thực tế:** "Cần vật tư — chuyển trạng thái Pending Parts"; "(sẽ yêu cầu tạo Firmware Change Request)"  
- **Mô tả lỗi:** Trạng thái kỹ thuật và loại yêu cầu bằng tiếng Anh lẫn trong câu tiếng Việt.

---

### BUG-022 — MEDIUM: Kết quả hiệu chuẩn "Pass" tiếng Anh trong IMM-11
- **Module:** IMM-11 · Hiệu chuẩn  
- **URL:** /calibration/CAL-2026-00016  
- **Input:** Thêm tham số đo lường với giá trị trong ngưỡng cho phép  
- **Output mong muốn:** Kết quả hiển thị "Đạt"  
- **Output thực tế:** Kết quả hiển thị "Pass"  
- **Mô tả lỗi:** Kết quả tự động tính toán ("Pass"/"Fail") không được dịch sang tiếng Việt ("Đạt"/"Không đạt").

---

### BUG-023 — MEDIUM: Loại hiệu chuẩn "In-House"/"External" tiếng Anh trong IMM-11
- **Module:** IMM-11 · Hiệu chuẩn  
- **URL:** /calibration  
- **Input:** Xem danh sách hiệu chuẩn, cột "LOẠI"  
- **Output mong muốn:** "Nội bộ", "Bên ngoài"  
- **Output thực tế:** "In-House", "External"  
- **Mô tả lỗi:** Giá trị dropdown loại hiệu chuẩn không được dịch sang tiếng Việt.

---

### BUG-024 — MEDIUM: "Traceability ref" là nhãn tiếng Anh trong IMM-11
- **Module:** IMM-11 · Hiệu chuẩn  
- **URL:** /calibration/{id}  
- **Input:** Xem chi tiết phiếu hiệu chuẩn  
- **Output mong muốn:** Nhãn tiếng Việt "Tham chiếu truy xuất"  
- **Output thực tế:** "Traceability ref"  
- **Mô tả lỗi:** Nhãn trường tiếng Anh không phù hợp với người dùng bệnh viện.

---

### BUG-025 — MEDIUM: KPI "Pass rate: 0%" sai khi chưa có dữ liệu (0/0 ≠ 0%)
- **Module:** IMM-11 · Hiệu chuẩn  
- **URL:** /calibration  
- **Input:** Xem KPI Pass rate khi "Đã qua: 0, Thất bại: 0"  
- **Output mong muốn:** Hiển thị "N/A" hoặc "—" khi chưa có dữ liệu hoàn thành  
- **Output thực tế:** "0%" — gây hiểu lầm "không có gì đạt yêu cầu"  
- **Mô tả lỗi:** Tính toán 0/0 = 0% thay vì N/A.

---

### BUG-026 — MEDIUM: Dashboard IMM-12 KPI mâu thuẫn — Chờ RCA hiện 0 dù có 6 RCA đang mở
- **Module:** IMM-12 · Sự cố & RCA  
- **URL:** /incidents/dashboard  
- **Input:** Xem dashboard khi có 6 RCA đang mở (RCA Required)  
- **Output mong muốn:** "Chờ RCA: 6"  
- **Output thực tế:** "Chờ RCA: 0" trong khi widget "RCA đang mở" hiển thị 6 hồ sơ  
- **Mô tả lỗi:** KPI "Chờ RCA" tính từ bảng khác hoặc điều kiện khác so với widget "RCA đang mở".

---

### BUG-027 — MEDIUM: "IMM Storekeeper" là tiêu đề tiếng Anh trong IMM-15
- **Module:** IMM-15 · Tồn kho  
- **URL:** /inventory  
- **Input:** Xem trang chủ tồn kho  
- **Output mong muốn:** Tiêu đề bằng tiếng Việt: "Quản lý kho phụ tùng"  
- **Output thực tế:** "IMM Storekeeper — Tổng quan"  
- **Mô tả lỗi:** "Storekeeper" là tiếng Anh. Sidebar cũng có "Watchlist" tiếng Anh.

---

### BUG-028 — MEDIUM: Benchmark form có thể sửa dù Tech Spec đã "Đã chốt"
- **Module:** IMM-02 · Thông số kỹ thuật  
- **URL:** /tech-specs/TS-26-00007 (tab Benchmark)  
- **Input:** Click "+ Thêm ứng viên" khi trạng thái hồ sơ là "Đã chốt"  
- **Output mong muốn:** Form bị khóa, không thể thêm ứng viên  
- **Output thực tế:** Form thêm ứng viên mở bình thường, cho phép nhập liệu  
- **Mô tả lỗi:** Bảo vệ trạng thái "Đã chốt" không hoạt động trong tab Benchmark. Dữ liệu có thể bị thay đổi sau khi đã chốt.

---

### BUG-029 — LOW: Tên trang "Tạo Incident Report" — tiêu đề trang và button tiếng Anh lẫn Việt
- **Module:** IMM-12 · Sự cố  
- **URL:** /incidents/new  
- **Input:** Mở form Báo cáo sự cố  
- **Output mong muốn:** "Tạo Báo cáo Sự cố" và button "Tạo báo cáo"  
- **Output thực tế:** "Tạo Incident Report" cả tiêu đề và button  
- **Mô tả lỗi:** Tên form và button chính dùng tiếng Anh "Incident Report".

---

### BUG-030 — LOW: Nhãn trạng thái mâu thuẫn "Nhập" vs "Bản nháp" cho cùng trạng thái Draft
- **Module:** IMM-01 · Đề xuất nhu cầu  
- **URL:** /needs-requests/NR-26-05-00016  
- **Input:** Đề xuất sau khi "Yêu cầu bổ sung" trở về Draft  
- **Output mong muốn:** Nhất quán tên trạng thái  
- **Output thực tế:** Workflow bar hiển thị "Nhập" nhưng badge góc phải hiển thị "Bản nháp" cho cùng một trạng thái  
- **Mô tả lỗi:** Hai nhãn khác nhau cho cùng trạng thái gây nhầm lẫn cho người dùng.

---

### BUG-031 — LOW: Cột bị cắt ngắn không thể đọc trong IMM-04
- **Module:** IMM-04 · Lắp đặt & Nghiệm thu  
- **URL:** /commissioning  
- **Input:** Xem danh sách phiếu nghiệm thu  
- **Output mong muốn:** Cột MODEL THIẾT BỊ và NHÀ CUNG CẤP hiển thị đầy đủ hoặc có tooltip  
- **Output thực tế:** "Dräger Evita ..." và "Công ty TNH..." — cắt ngắn không đọc được  
- **Mô tả lỗi:** Chiều rộng cột quá hẹp, không có tooltip khi hover.

---

### BUG-032 — LOW: "CAPA" dùng tiếng Anh trong IMM-16 Tuân thủ
- **Module:** IMM-16 · Tuân thủ  
- **URL:** /compliance/findings/{id}  
- **Input:** Xem chi tiết phát hiện tuân thủ  
- **Output mong muốn:** "Hành động khắc phục liên kết", "Chưa có hành động khắc phục"  
- **Output thực tế:** "CAPA liên kết", "Chưa có CAPA"; sidebar cũng hiển thị "CAPA"  
- **Mô tả lỗi:** "CAPA" (Corrective and Preventive Action) là từ viết tắt tiếng Anh, nên dịch sang tiếng Việt cho người dùng phổ thông.

---

## DỮ LIỆU THỬ NGHIỆM ĐÃ TẠO

| Loại | Mã | Mô tả | Trạng thái |
|------|-----|--------|------------|
| Đề xuất nhu cầu | NR-26-05-00017 | Mua máy gây mê Khoa Mổ (1.2 tỷ VND) | Đã duyệt → PP-26-00007 |
| Hiệu chuẩn | CAL-2026-00016 | Siêu âm Philips EPIQ 7 | Đang thực hiện |
| NC nghiệm thu | NC-26-05-00002 | Thiếu nhãn hóa tiếng Việt | Đã đóng |
| Sự cố | IR-2026-0130 (ước) | Máy siêu âm Philips EPIQ 7 lỗi E-042 | Mới mở |
| Chẩn đoán CM | WO-CM-2026-00014 | Máy bơm tiêm B. Braun | Đang chẩn đoán |

---

## LUỒNG KINH DOANH ĐÃ KIỂM THỬ

### Luồng đầy đủ IMM-01 → IMM-02 → IMM-03 → IMM-04 (Asset Lifecycle)
1. ✅ **IMM-01**: Tạo đề xuất NR-26-05-00017 → Gửi → Rà soát → Chấm điểm → Lập dự toán → Trình BGĐ → **Phê duyệt** (sau khi fix deadlock funding_source) → Thêm vào PP-26-00007
2. ✅ **IMM-02**: Xem danh sách TS-26-00007/08/09 đã được sinh từ kế hoạch PP-26-00006; Test "Sinh từ kế hoạch" (dropdown bug)
3. ✅ **IMM-03**: Xem đánh giá VE-26-00004/05/06; Xem quyết định PD-26-00005/06/07 (Đã ký hợp đồng)
4. ✅ **IMM-04**: Xem nghiệm thu ACC-26-05-00007; Sửa (edit mode); Tạo NC (NC-26-05-00002); Đóng NC

### Luồng vận hành tài sản
5. ✅ **IMM-08**: Xem 10 phiếu PM; Hoàn thành checklist 3/3 (100%); Phát hiện lỗi quyền
6. ✅ **IMM-09**: Xem CM dashboard; Click WO-CM-2026-00014; Bắt đầu chẩn đoán (lỗi mixed English)
7. ✅ **IMM-11**: Xem 4 phiếu hiệu chuẩn; Test thêm tham số (BUG-001 confirmed)
8. ✅ **IMM-12**: Tạo sự cố mới (Philips EPIQ 7 lỗi E-042, High severity)
9. ✅ **IMM-15**: Xem dashboard tồn kho (713 triệu VND, 4 phụ tùng tồn thấp)
10. ✅ **IMM-16**: Xem 3 phát hiện tuân thủ; Xem FND-2026-00004 (78 < ngưỡng 90)

---

*Báo cáo tạo ngày 27/05/2026 bởi hệ thống kiểm thử tự động AssetCore*
