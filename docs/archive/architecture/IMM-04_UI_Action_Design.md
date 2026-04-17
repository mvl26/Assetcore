# Thiết kế Hành vi Giao diện & Nút Điều hướng (UI Action Design)
# Bóc tách Action Button theo Mạng Lưới Trạng Thái (State Machine) IMM-04

**Phân hệ:** AssetCore v1.0
**Nguyên tắc thiết kế Hành vi:** Mọi tương tác chuyển State (Bấm nút) đều bị kiểm soát bởi 3 Gate bảo vệ: **Actor Gate** (chỉ hiển thị đúng người), **Condition Gate** (Dữ liệu chưa sạch sẽ chìm màu/Disable), và **Validation Gate** (Nếu bấm lúc data bẩn sẽ chặn lưu và quăng Error màu đỏ).

---

## 1. BẢNG MAPPING (STATE ➔ UI ACTION)

Bảng này định nghĩa màn hình tại từng State sẽ hiển thị nhóm Nút Tương tác nào.

| State Hiện Tại | Action Buttons Khả Dụng | Rollback / Ngoại Lệ (Exception Button) |
|---|---|---|
| `Draft` | **[ Gửi Duyệt Hồ Sơ ]** | [ Xóa Nháp ] |
| `Pending_Doc_Verify`| **[ Duyệt Hồ Sơ Kỹ Thuật ]** | [ Trả Về Bổ Sung ] |
| `To_Be_Installed` | **[ Đạt Điều Kiện Mặt Bằng ]** | [ Tạm Hoãn Do Mặt Bằng ] |
| `Installing` | **[ Hoàn Tất Lắp Ráp ]** | - |
| `Identification` | **[ Cấp ID Serial ]** | - |
| `Initial_Inspection`| **[ Gửi Báo Cáo Test ]** | **[ Báo Cáo Sự Cố / Lỗi DOA ]** *(Nút Custom JS)* |
| `Re_Inspection` | **[ Gửi Báo Cáo Lần 2 ]** | **[ Báo Cáo Sự Cố DOA ]** |
| `Clinical_Hold` | - | Khớp Giấy Phép -> Form Tự Thoát Hold. |
| `Clinical_Release` | **[ 🏆 Approval Phát Hành ]** | **[ Reject Trả Về Kho ]** |
| `Clinical_Release_Success`| *(Docstatus = 1)* Read Only | [ Amend (Tạo Bản Mới) ] |

---

## 2. DANH SÁCH UX BUTTON & ĐIỀU KIỆN (CONDITIONS + EVENT TRIGGERS)

Danh sách 5 Cụm Nút lõi đại diện cho các Giai đoạn Sinh Tử của Hệ Thống.

### 2.1 Cụm Button: Tiến Trình (Next Step / Submit Flow)
**Tên trên UI:** `Gửi Duyệt...` / `Hoàn Tất...`
- **Ai thấy:** Nhóm `HTM Technician` (Hiện trường), `Biomed Engineer` (Phòng Test).
- **Khi nào Enable:** Enable mặc định, nhưng bị validation tát ngược nếu Fill thiếu Mandatory Field.
- **Trigger Validation:**
	- Bước `Duyệt Hồ Sơ`: Trigger hàm kiểm tra bảng CQ/CO/HDSD không bị null. (Ném Lỗi nếu rỗng).
	- Bước `Cấp ID Serial`: Trigger hàm tra soát chéo toàn DB (VR-01) xem Serial này có đang được khai sinh trên tờ phiếu nào khác không.
	- Bước `Gửi Báo Cáo Test`: Quét Form. Nếu Test_Result = Fail $\rightarrow$ Yêu cầu Dừng $\rightarrow$ Quăng Warning (Bắt buộc dùng tính năng Báo cáo Lỗi). (Ném Lỗi VR-03).
- **Phát sinh Event:** Không tạo Custom_Event bên ngoài ERP. 

### 2.2 Nút: Phê Duyệt Tối Hậu (Approval Release)
**Tên trên UI:** `Approve Release` (Màu Xanh Đậm Bắt Mắt).
- **Ai thấy:** Duy nhất Role `VP Block2` (Role Lãnh Đạo). KTV Hiện trường chịu mù (Không cấp phép hiển thị theo Workflow).
- **Khi nào Enable:** State chạm mốc `Clinical_Release`.
- **Trigger Validation (Gác Cổng Cuối Cùng):**
	- Trigger Rule **VR-04**: Quét tìm bảng `QA_Non_Conformance` chứa ID Phiếu Của Form. Nếu Ticket báo hỏng chưa đóng (Status: Open) thì Tát Lỗi To Màn Hình: "KẾT LUẬN TEST ĐANG CÓ NC (THIẾT BỊ BỊ HOLD). KHÔNG THỂ PHÁT HÀNH!".
- **Phát sinh Event:** 
	1. Trigger Action Script sinh **1 Tài Sản Thực (Asset_Record)** vào Database Kế toán. Bắn Link ghim vào `Final_Asset`.
	2. Emit Socket Event `imm04.release.approved` cho Front-end và Mail Server (Để gửi Alert ZNS).

### 2.3 Nút: Giữ Lại / Cách Ly (Hold System Action)
**Tên trên UI:** (Tự Động) Hệ thống tự đá Form vào Cửa `Clinical_Hold` (Màu Cam Đỏ). Lập tức Đóng băng giao diện Edit thông thường.
- **Trigger Validation Mồi:**
	- Kích hoạt tại Thời khắc Kết thúc Test (Save Validation): Tự động soi Trường Mã Item. Nếu `is_radiation == 1` & Tab `license_doc` == NULL $\rightarrow$ Auto Set Form state = `Clinical_Hold` (Thay vì nhả cho Lãnh Đạo Ký). Ném Message Toast cảnh báo vàng.

### 2.4 Cụm Button: Trả Về / Lỗi Kỹ Thuật (Reject / Exception Throw)
**Tên trên UI:** `Báo Cáo DOA` (Nút Custom Button Javascript Tách Riêng khỏi Workflow).
- **Ai thấy:** `Biomed Engineer`. (Sáng đèn trong khung `Initial_Inspection` và `Re_Inspection`).
- **Nhiệm vụ:** Một Box Confirm Text bay ra: *"Xác nhận tạo Phiếu Xử lý Chất lượng hãng (DOA)*?".
- **Phát sinh Event:** 
	- Router API tạo 1 Document mới tinh dạng `Asset QA Non Conformance`. 
	- Điền vào Ref gốc trỏ về Phiếu IMM04 hiện tại.
	- Save -> Bắn Noti cho Trưởng Khoa. Ném Notification Alert màu đỏ góc màn hình KTV báo Tạo Thành Công Phiếu NC-XX. Đổi UI Action State sang Tab `Re_Inspection`.

---

## 3. THIẾT KẾ MESSAGE & WARNING (THÔNG BÁO) CỦA HỆ THỐNG

Thay vì dùng Alert của hệ điều hành chán ngắt, Hệ thống quăng Log thông tin theo Chuẩn HTML Design Warning của Frappe (`frappe.msgprint` và `frappe.throw`).

| Loại Lệnh Bắn | Hình Thức Hiển Thị (UI Component) | Tình Huống Kích Hoạt (When) | Tác Hại Hệ Thống |
|---|---|---|---|
| **Error Message (Throw)** | Popup Overlay Nền Đỏ (To giữa màn hình), kèm Icon 'X'. Fix xong mới được bấm tiếp. | KTV điền phiếu rác, Bỏ trống C/Q. Quét Trùng Barcode. Ấn duyệt khi có DOA chưa báo cáo Hãng. | Ngắt mạch Chuyển State (Chặn Lưu Data). |
| **Warning Toast** | Dải Banner Nền Vàng trôi nổi Góc Trái (3 giây biến mất). | Thiếu sổ tay HDSD gốc (Thuộc tính: Không bắt buộc). Gõ tay Serial (Cảnh báo bị gõ nhầm < 4 kí tự). | Lưu Data Bình Thường. Gợi ý User coi chừng sai nghiệp vụ. |
| **Confirm Dialog** | Popup Trắng hỏi Yes/No Option (`frappe.confirm`) | KTV Bấm nút "Báo Cáo Sự Cố DOA". Cần Confirm tránh Spam Ticket giả làm kẹt máy. | Tạm ngừng chờ Hành vi Từ User. |
| **Success Alert** | Dải Băng Xanh Lá Góc Phải (Toast Message) | Approve Release Cuối Cùng Thành Công. | Kích hoạt chuỗi Script Chạy Thành Công (Đã tạo Asset Số 1234). |

---
*Mapping trên mô tả toàn bộ vòng Đời Mở khóa Sự Kiện Lõi thuộc IMM-04 dưới lăng kính Chặn Vết Hành Vi của User.*
