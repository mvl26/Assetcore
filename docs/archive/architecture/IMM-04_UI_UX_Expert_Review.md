# Báo cáo Đánh giá UI/UX Chuyên Sâu (Tri-Role Perspective)
# Phân hệ IMM-04: Lắp đặt & Bàn giao TBYT

**Người thực hiện Review:** Hội đồng chéo (UX Expert + KTV HTM + Cán bộ QA/QMS)
**Mục tiêu:** Soi chiếu từng pixel của Giao diện xem có bị hở sườn Logic hay đánh lừa người dùng dẫn đến phá vỡ QMS hay không.

---

## 1. KẾT QUẢ ĐÁNH GIÁ ĐA CHIỀU (8 CÂU HỎI TRỌNG TÂM)

### 1️⃣ Actor có thao tác đúng workflow không?
- **Nhận định (UX Expert):** Đạt 90%. Do chúng ta áp dụng mô hình giấu Nút / Giấu Tab theo State. Người dùng buộc phải đi thẳng luống cày. 
- **Cảnh báo (HTM User):** Thiếu nút 'Refresh' tức thời. Sau khi Kỹ sư đo Test Điện (Grid Baseline) và State chuyển, KTV nếu đang đứng chung 1 phòng nhưng mở trên máy tính khác chưa thấy F5 kịp có thể bị lệch nhịp.

### 2️⃣ Có bước nào dư thừa không? 
- **UX & HTM User:** **CÓ**. Bước *Identification* (Gắn QR/Serial bar-code). Hiện tại KTV phải gõ vào TextBox. Nếu dùng súng quét mã vạch (Barcode Scanner) thì súng sẽ tự chui vào Textbox. Việc bắt KTV ấn nút "Cấp ID Serial" ở State này sau khi quét xong khá thừa.
- **Đề xuất Fix:** Mặc quần đùi Scanner - Khi Scan xong (event kí tự thay đổi nhanh), OnChange sẽ gọi tự Save và Auto-Đẩy State Nhảy vọt lên `Initial Inspection`. Cắt 1 Cú Click.

### 3️⃣ Có field nào gây nhầm lẫn (Ambiguous) không?
- **HTM User:** Field `installation_date` dễ bị hiểu nhầm là "Ngày kế hoạch bắt đầu Lắp" hay "Ngày đã ráp máy xong".
- **QA Reviewer:** Tên đúng theo chuẩn phải là `completed_installation_date` (Ngày kết thúc Lắp).
- **Đề xuất Fix:** Đổi nhãn Label hiển thị sang: "Ngày Hoàn Tất Lắp Ráp & Bàn Giao Mặt Bằng". Mặc định Tự Điền (Auto Now) khi State rời cửa `Installing`.

### 4️⃣ Có thiếu thông tin để ra quyết định Ký Duyệt không?
- **VP Block2 (Sếp Lớn):** Trong Màn hình **Phê Duyệt Cuối Cùng**, sếp chỉ thấy Đống Bảng điện Test Xanh Rì (Pass Pass..). Nhưng Sếp KHÔNG THẤY tổng tiền Vốn Vận đơn Giá Máy Của Cái Mẫu (PO) Này Là Bao Nhiêu. Không dám Ký Khống.
- **Đề xuất Fix:** Chêm một Custom HTML Card ở Header Tổng Hợp: `Số Lượng Nhập (Qty)` | `Tổng Tiền Hóa Đơn Mua (Grand Total từ PO)`. Lãnh đạo nhìn 1 giây biết Máy Trăm Triệu hay Máy 5 Tỷ.

### 5️⃣ Có bước nào dễ thao tác sai lầm (Human Error) không?
- **QA Reviewer:** **CÓ. Cực kì nghiêm trọng!** Bảng Grid C/Q File Chứng Chỉ. KTV Rất hay Quen Tay ấn Save nhưng Quên Bấm Đính Kèm Cục PDF PDF Giấy thật vào cái Dây Link Upload. Dẫn đến Hệ thống Có dòng Record C/Q (Màu Xanh), nhưng chọt vào rỗng Tuếch, không có Chứng chỉ Scan.
- **Đề xuất Fix:** Sẽ Viết Script Hardcore: Nếu Tick C/Q = `Received` thì Bắt buộc `file_doc_links` phải Khác Null (Chứa dải Link CDN). Nếu không chặn Không Cho Gửi Duyệt.

### 6️⃣ Có Logic nào vênh nhịp Workflow không?
- **QA Reviewer:** Logic Khai Báo Lỗi DOA. Khi Test Rớt (Dòng Điện chạm vỏ 5.5mA). Máy nhảy Về State `Re-Inspection` chờ Hãng. Nhưng Lỡ KTV HTM vô tình Trượt Tay xóa béng Phiếu NC Gốc Đi (Chưa bị Khóa DocStatus cứng do Ticket kia nằm mảng độc Lập). Thì Máy này "Sạch Lỗi Hồn Ma".
- **Đề xuất Fix:** Treo Cờ ReadOnly Field Trạng Thái trên Ticket NC. Xóa Quyền Delete Ticket NC Đã được Create khỏi Role Admin luôn. Đã lập Ticket Bêu Rếu Hãng Giao Máy hỏng thì Bắt buộc Vĩnh viễn Phải Nằm Im Trong History để Cuối Năm Trị Tội QMS Ép Rớt Thầu.

### 7️⃣ UI có hỗ trợ Audit Trail không?
- **QA Reviewer:** Đạt Chuẩn. Nút Check_Cbox "Track_Change" Nằm gốc. Kéo Version Trùng Khớp. Lịch Sử Duyệt Bấm Của Lãnh Đạo Được Dán Cứng Xuống Tab Time-line Footer.

### 8️⃣ UI có hỗ trợ QMS Control không?
- **QA Reviewer:** Cụm Gài Lưới `qa_license_doc` Chặn Máy Có Tia X quá xịn. (Auto Hold Cực Ngon). Đạt. Nhưng Cần Đổi Màu Nút [CLinical Hold] Thành Đỏ Gắt Để Gây Hoảng Loạn Cho Đội Nhập Hàng.

---

## 2. BẢNG CHIẾT XUẤT ISSUE CẦN ĐẬP ĐI XÂY LẠI (ISSUE LIST)

Được tổng kết sau buổi Gác chéo UX Hội Đồng:

| Issue ID | Vấn đề UX/UI Phát Hiện | Mức Độ Nghiêm Trọng | Fix Method (Đề xuất Vá) |
|---|---|---|---|
| **UX-01** | QMS Sập Hầm File Rỗng: Chọn "Có C/Q" nhưng quên Đính file PDF C/Q. Form vẫn Pass lọt. | **🔴 CRITICAL** | Ràng Buộc JS (Mandatory If File_link = Null). |
| **UX-02** | Xoá Vết Tích Tội Ác DOA: Ticket NC nằm rải rác dễ bị Admin Can Thiệp Delete. | **🔴 CRITICAL** | Un_Check Quyền `Delete` Ticket DOA NC Đối Với Admin / Đội QA. Không Tẩy Trắng DC. |
| **UX-03** | Lãnh Đạo Ký Mù (Sợ trách nhiệm): Lãnh đạo không thấy Lô Máy đó Giá trị Khủng Bao Nhiêu. | **🟠 MAJOR** | Fetch `Total_Amount` từ PO Link lên thẳng Form Góc Trái View Lãnh Đạo. |
| **UX-04** | Dư nút bấm `Cấp ID Serial Barcode`: Gây chậm luồng trải nghiệm Kho Bãi. | **🟡 MINOR** | Auto Save & Chuyển State khi Độ Dài Barcode > 8 Chars trong Input TextBox. |
| **UX-05** | Label Field `installation_date` Mơ hồ ngôn từ. | **🟡 MINOR** | Renamed `Ngày Hoàn Tất Lắp Ráp & Mặt Bằng`. |

---

## 3. PHIÊN BẢN UI HARDENED (CHÚC BÉ NGỦ NGON - KHÔNG HỞ ĐƯỜNG LÙI)

Phiên bản UI sau vá Lỗi 5 Lưỡi Rìu trên được Định Nghĩa Là **IMM-04 UX Hardened v1.5**. Nó thể hiện sự sắt đá không Nhượng bộ con người của Hệ Thống QMS Y TẾ:

1. **Giao Diện Scanner Auto-Submit:** Chĩa súng bắn Laser, Mã "Tít" Chạy Vèo TextBox, Màn Hình Méo mó 2 giây rồi Bay Thẳng Qua `Initial Inspection`. KTV Rút tay không càn Click Click Mỏi Tay. (Tốc Độ 2s).
2. **Khóa Tù Chung Thân Ticket Rác (DOA NC):** Một Phiếu Hỏng Hóc Khai Sinh, Là Đứng Chết Trân Trọng Lịch Sử, Trưởng Khoa có Xin Nghỉ Mát thì Hãng Bán Sinh Y Vẫn Dính Mác Lịch Sự Rớt Test Lần 1 Bêu Sạm Ngay Giữa List View Giao Diện Kế Toán Không Tẩy Rửa (Căn cứ Phạt Khấu Hao Do Đền Bù).
3. **Giấy Tờ Mù Là Không Nhúng Máy Qua Cửa:** Cần C/Q Là Buộc Cái Form Mốc Đỏ (Asterisk) Đuôi Link Phải Hiện Hình PDF File Nặng Hơn 1 KB. Không Mưu mẹo Đánh Dấu Check "Có" Suông Bằng Chữ Nữa!
4. **Header Bát Vàng (VP Review):** Nắp Sập Hiện rõ "Lô Này Nhập Bao Nhiêu Tỉ Đồng" Ngay góc Màn hình Lãnh Đạo Khối. Ký Xuống Tay Cực kì Nét. 

*Bản đánh Giá UX được Chốt Hoàn Mỹ Khép Lại Toàn Vẹn Hệ Phân Tích UAT Cho Giai đoạn IMM-04.*
