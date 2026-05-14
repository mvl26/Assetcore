# Phân tích Phạm vi Nghiệp vụ: IMM-04 (Lắp đặt, định danh và kiểm tra ban đầu)

Dựa trên tài liệu BA Wave 1 và hồ sơ kiến trúc IMMIS/AssetCore, đây là bản phân tách ranh giới và định hình thiết kế kỹ thuật nghiêm ngặt dành riêng cho module IMM-04.

---

### 1. Mục tiêu
Quản trị quá trình "nhập tịch" của thiết bị y tế từ khi tiếp nhận vật lý đến lúc chính thức được đưa vào mạng lưới tài sản của bệnh viện. Module giúp đảm bảo máy móc được lắp ráp đúng chuẩn, gán định danh đa lớp chính xác, ghi nhận mốc thông số kỹ thuật (baseline) và thiết lập các trạm kiểm duyệt (Gate) rủi ro nhằm tuyệt đối ngăn chặn việc đưa thiết bị nhiễm lỗi, sai thông số hoặc chưa hiệu chuẩn vào phục vụ lâm sàng.

### 2. Phạm vi trong
- Tiếp nhận, đếm số lượng thực tế và đối chiếu phụ kiện từ gói thầu/đơn hàng.
- Rà soát điều kiện hạ tầng nội bộ (điện, nước, khí, không gian) trước khi Hãng tiến hành tác động thiết bị.
- Kỹ sư hãng tiến hành lắp đặt phần cứng, phần mềm.
- Định danh thiết bị: Gán Internal Tag, Barcode/QR, Serial NSX, và mã BYT.
- Khởi tạo Baseline: Tiến hành đo đạc thông số kỹ thuật rạn nứt / tính an toàn / hiệu chuẩn.
- Ghi nhận lỗi DOA (Dead On Arrival) và hướng xử lý trả hàng tại chỗ.
- Quyết định Release Gate (chấp nhận tài sản) hoặc Hold Gate (đóng băng).

### 3. Phạm vi ngoài
Những công việc sau ĐƯỢC CHẶN cứng khỏi IMM-04:
- Quá trình đấu thầu, ra hợp đồng, và vận chuyển ngoại viện (Thuộc Mua sắm/Procurement).
- Thanh toán tài chính, hạch toán vốn kế toán, hay phát hành hóa đơn tài chính (Thuộc Finance/Accounting Module ERP).
- Lên lịch sửa chữa khi máy bị hỏng hóc sau 1 tháng sử dụng (Thuộc IMM-05 Maintenance).
- Đào tạo y bác sĩ cách sử dụng thiết bị (Đây có thể là luồng cắt ngang sang HR/Training Module, không nằm trong tiến trình test phần cứng).

### 4. Giao diện với module khác
- **Với IMM-03 (Inventory/Stock):** IMM-04 chọc vào kho để lấy Master Item và xác nhận "đã rút hàng ra khỏi kho tạm" để kéo về chân công trình.
- **Với IMM-05 (Preventive Maintenance):** Toàn bộ bộ thông số `Baseline Test` được tạo ra ở IMM-04 sẽ được truyền thẳng (Push) sang IMM-05 làm "Ngữ cảnh tiêu chuẩn" để các đợt bảo trì dự phòng đối chiếu mức suy hao.
- **Với IMM-08 (Decommissioning):** Nếu máy DOA (chết ngay lúc mở hộp) và bị trả về Hãng vĩnh viễn, IMM-04 sẽ truyền tín hiệu sang IMM-08 để xóa tên thiết bị đó khỏi vòng đời nội bộ.

### 5. Actor (Diễn viên hệ thống)
- **Kỹ sư TBYT (Biomed Engineer):** Actor chủ lực. Đo kiểm hệ thống, ghi log baseline và quyết định Release.
- **Kỹ sư Hãng (Vendor Tech):** Actor ngoại bộ. Báo cáo tiến độ ráp máy.
- **Trưởng phòng / Trưởng Khoa (Clinical Head):** Bấm xác nhận tài sản hiện diện tại khoa, ký biên bản bàn giao sinh tồn.
- **Đại diện Kiểm định (QA/Regulatory):** Tháo gỡ trạng thái "Clinical Hold" khi chứng nhận từ Cục đo lường được phê chuẩn.

### 6. Input / Output
- **Input chính:** 
  - Đơn đặt hàng (PO) hoặc Packing List từ Hợp đồng mua sắm.
  - Hàng hóa hộp cứng vật lý tại vị trí lắp đặt.
  - Chứng chỉ CO/CQ và Manual đi kèm máy.
- **Output chính:** 
  - `Multi-layer identification_tag` (Gói định danh đầy đủ của máy).
  - Bảng ghi chú Baseline.
  - Status nội bộ của ERPNext chuyển thành `Active Asset`.
- **Hồ sơ bằng chứng (Evidence):** File scan Biên bản Bàn giao & File scan kết quả Test an toàn điện chuẩn (PDF locked).

### 7. Gate kiểm soát (Control Gates)
1. **Site Verification Gate:** Hạ tầng (điện/nước) chưa đạt 100% -> Chặn không cho kỹ sư Hãng dỡ bo mạch máy.
2. **Identity Gate:** Serial Number trùng lặp với DB Bệnh viện -> Chặn, yêu cầu xác minh máy lậu/máy mượn.
3. **Safety / Calibration Gate:** Trượt bất kỳ Baseline Test Parameter nào -> Máy nằm chết gí tại `Clinical Hold` Gate. Không sinh Asset Tag.

### 8. Rule trọng yếu (Business Rules)
- `Rule 01:` **No Override Generation:** Người dùng không được phép vào màn hình Asset của ERPNext để bấm nút [Add New] tài sản lớn bằng tay. Khởi tạo tài sản BẮT BUỘC phải đi qua ống xả của IMM-04.
- `Rule 02:` Máy sinh hiệu chuẩn (Máy chạy hóa chất, thiết bị phóng xạ) không có file chứng minh kiểm chuẩn bên thứ 3 -> Bị treo sống tại `Pending QA Clearance`.
- `Rule 03:` Không xóa Log Data. Lỗi đo đạc chỉ được phép Ghi đè (Amend) hoặc cập nhật (Append), giữ vĩnh viễn dấu vết lịch sử test lúc lắp đặt.

### 9. Phân loại dữ liệu (Data Tripartition)
- **Master Data (Dữ liệu chủ):** Item Code (Model/Hãng), Location (Mã ID khoa phòng), Tài khoản Vendor.
- **Operational Data (Dữ liệu vận hành):** Lịch trình lắp đặt, ngày giờ khui thùng máy, tên ông kỹ sư bắt ốc, tình trạng hỏng hóc xước xát vỏ hộp.
- **Governance/QMS Data (Dữ liệu quản trị):** Form Baseline (để mốc check chéo sau 5 năm), Nhật ký Audit chuyển trạng thái, Chữ ký số từ Giám đốc cho Gate `Release`.

### 10. Giả định mở
- *Giả định 1:* Bệnh viện sử dụng Barcode/QR đa hệ, vì thế form nhập của IMM-04 giả định có hỗ trợ trường đọc kết nối với máy bắn Barcode qua API để tránh nhập nhầm SN dài trên bàn phím.
- *Giả định 2:* Việc thu hồi công nợ Kế toán (kích hoạt báo thanh toán Hợp đồng đợt 2 cho Hãng) mặc định sẽ bắt trigger của hành động sinh ra `Clinical Release` từ IMM-04 này.
