# Thiết Kế Tích Hợp UI ↔ Backend (Integration Map)
# Kết Nối Luồng Giao Diện với Hệ thống Lõi ERPNext / Frappe (IMM-04)

**Phân hệ:** AssetCore v1.0
**Nguyên lý Thiết kế:** AssetCore đi theo chủ nghĩa **"Lực đẩy Backend"** (Backend-Driven UI). Mọi quyết định hiển thị, cấm/cho phép trên UI Client đều phải lấy thông số trạng thái từ DocType Controller (Python), không phó mặc rủi ro cho JavaScript bảo vệ.

---

## 1. MAPPING LUỒNG TRỌNG ĐIỂM (UI ↔ BACKEND)

Bảng phân tích Dữ liệu Đi - Về của các Màn Hình.

| Giao diện UI Thao Tác | Hành Động User Click | DocType Đi Đích Chịu Trận | Trigger API / Server Event |
|---|---|---|---|
| **Bảng Lắp Hồ sơ Nháp** | Quét Barcode dán vô TextBox `vendor_serial` | `Asset Commissioning` | `frappe.client.get_value()` đâm chéo kiểm tra `Asset` toàn viện xem ID Barcode này đã tổn tại chưa. Update Field: Tự sinh mã QR nội bộ. | 
| **Action: Submit Màn hình** | Click Workflow Button: `Phê duyệt Phát hành` | `Asset Commissioning` | Cập nhật Docstatus lên State `1`. Kéo theo Auto-Trigger chạy Code Backend của hàm Python `mint_core_asset()` giấu trong File `Asset_Commissioning.py`. |
| **Grid Baseline Test** | Gõ trị số dòng điện = 4.5 mA | `Commissioning Checklist` (Child) | Update DB bảng Child. Lưới UI Cảnh báo Đỏ `Fail`. | 
| **Box Tác vụ Khẩn Tiện Ích** | Click Nút Tự Chế: `Báo DOA Hỏng Trả Máy` | Nhảy Giao thức Call API sang Doc `Asset QA Non Conformance` | Client Call API `frappe.new_doc()` kéo Data (Tên Máy, Model, Mã Lỗi Rò Điện) từ Form Cha Copy dán sang Tạo ngay một Tờ Ticket Ngoại lệ Mới. |

---

## 2. PHÂN TÁCH GIAO DIỆN (Nơi Nào Chắn Logic JS, Nơi Nào Dùng UI Gốc)

Dự án tuyệt đối không phí phạm React/Vuejs để viết lại những gì Standard Frappe đã có. Chỉ nới gọng kiềm ở nơi thật sự cần thiết.

### 2.1 Thành phần dùng 100% Standard ERPNext Form (UI Chuẩn)
- **Form Kế toán (Asset Mẹ):** Sau khi máy thả về Kho, KTV/Kho nhìn trên Giao Diện Asset Mặc định. Chịu Backend Logic của Phân hệ `Erpnext_Asset`.
- **Form PO Mua Sắm / Menu Item / Khoá Mật:** Mặc định xài chuẩn.

### 2.2 Thành phần xài Standard Form nhưng "Bọc Thép" Client Script (JS)
- **Asset Commissioning:** Xài giao diện gốc. Nhưng ép dính 01 File `asset_commissioning.js` bự: 
   - Script 1: Giấu tất cả các Nút "Remove Row", "Add Row" của cái Bảng Checklist Test (Sợ KTV tự xóa Lưới chỉ tiêu quy định Viện để khỏi cần đo điện).
   - Script 2: Ẩn hiện các Tab Nền (Tab 1, Tab 2, Tab 3) theo Chu kỳ `doc.workflow_state` để KTV khỏi bấm nhầm.
- **Asset QA Non Conformance:** Xài giao diện gốc. JS bọc thép trường `Penalty_Amount` - Cấm tiệt Cậu IT hay KTV táy máy đổi tiền bồi thường sửa chữa.

### 2.3 Thành phần Khuyên Nên Xài Page Vuốt Chạm Custom (Tuơng lai V1.1)
- **App Máy Tính Bảng Chuyên Dụng Quét Mã QR Kho / Hiện Trường Lắp Ráp:** 1 Custom Page `Scanner_Box` tích hợp Camera API Device thuần, nhét riêng Code VueJS gọi qua RestAPI Frappe. Khi KTV tít Laser vô Thùng Hàng, Web tự Call `/api/method/assetcore.api.get_commissioning_by_barcode` thay vì Bắt User mở Giao diện Cồng kềnh Của ERPNext.

---

## 3. MAPPING HỆ THỐNG MẪU VALIDATION BẢO VỆ CHÉO KÉP (UI vs Backend)

Không tin Client. Client vỡ thì Server Đỡ Bằng Lưới Lọc Rác.

| Tên Validation (QMS Block) | Validation Chặn Trên UI (JS Dialog) | Validation Chặn Sau Cùng Trên Server (Phython Validate) |
|---|---|---|
| **Chặn Test Điện (Fail) Mất Note** | JS tự quét Vòng Lặp. Nếu thấy Grid Test = "Fail" mà Note DOA Đang Trống >> Quăng Toast Msg Vàng Yêu cầu điền đi. (Làm Mịn UI). | Hàm Def Python `validate()`. Nếu Dữ liệu Cố tình Save bị đẩy lên rác. Cắt ngang Server không Lưu Database. Quăng Trả `Frappe.throw("Thiếu Ghi Chú Lỗi Kiểm Định Dòng Rò")`. |
| **Giải Cứu Bức Xạ Holds**| Click File Kéo Thả `qa_license_doc`. Giao diện Cục Holds Đỏ bay mất đổi sang Form Trắng. Trực quan Thấy Luôn. | Hàm Python Check Điều Khoản (Is_radiation == 1) + is_null(`qa_license_doc`). Phạt 403 Forbidden nếu Vẫn cố Nhồi Máy Đi. |
| **Quyền Phê Duyệt Cuối Bằng Mọi Giá** | Workflow File Ẩn Cục Action Button "Release Phát Hành" Nếu User_Role không phải "VP Block 2". User không biết sự tồn tại của Nút này. | Hook Server "Has_Role" & Method Submit Của ERPNext Đứng Chặn Tường Lửa API. Bất kì Cú Call Terminal/Postman Nào Gắn Script "Release_State" đều dính Trả Về Exception "QMS Not Authorized Action". |

---

## 4. TÓM TẮT ĐẦU MỤC SCRIPT TÍCH HỢP QUAN TRỌNG

**🔹 Nhóm Client Script (JS):** Mượt mà hóa Trải Nghiệm Mắt.
- JS_Visiblility_Controller: Toggle ẩn hiện Tab dựa theo Enum list state hiện thời.
- Trigger_Button_NC: Inject 1 nút Bấm Báo Cáo Hỏng Nhanh Ở góc trên Tab Test Bảng điện. `frappe.route_options = {"ref_comm": frm.doc.name}`.
- Block_Scanner_Mouse: Hàm Event Khóa Field Barcode `vendor_serial` tránh Gõ bằng Bàn Phím, Nếu phát hiện Gõ Mảng Kí tự tốc độ chậm (<15ms per Chars) >>> Reject Data (Để ép dùng Máy Barcode Laser Cầm Tay). 

**🔹 Nhóm Server Script (Python):** Hạt Nhân Tạo Năng Lượng 
- Phython_Doc_Submit: `on_submit` event. Lôi API Độc lập `assetcore.create_asset()` chạy Lệnh Gen File Mã Chứng từ Mới. Sinh xong thì update link dán về Gốc (Two-ways Binding Liên Kết Dữ Liệu Chéo).
- Python SLA Cronjob: Hàm lặp tự gọi mỗi đêm quét vòng For qua tất cả Phiếu có Cờ State = To_Be_Installed nằm trơ lại 3 ngày qua. Gửi HTTP Rest API bắn tin nhắn về Điện Thoại Hội Trưởng.

---

## 5. CẢNH BÁO: ĐIỂM DỄ GÃY DATA SYNC CAO ĐỘ (FAIL-POINT RISK)

1. **Transaction Create_Asset Rớt Đáy Mạng (Rủi ro Lớn Nhất):** Lúc `VP Block 2` bấm Release Phê duyệt. Backend Python bắt đầu Cắt Form Commissioning sang State Đóng Băng và Khởi sinh Code Gọi Đệ đẻ Ra Cái `Tài Sản Asset` Cho Kế Toán. Xui thay Server Lag Database mất kết nối giữa chừng => Phiếu Lắp đặt bị Khoá nhưng Máy Lại Chưa Thấy Tồn Tạo Dưới Kho >> Sẽ Gây Mâu Thuẫn Quyền Lợi Hai Khoa Lớn Nhất (Y Tế - Hành Chính Kho). Giải Phát: Bọc hàm Tạo Đôi này vô chung 1 Cụm Rollback của SQL Framework (Atomic Transaction Call). 1 Chết Chết Cả 2.
2. **Kéo Thay Đổi Asset Sinh Trước Chạy Thụt Lùi:** Lỡ Bấm Nhầm Release. Có Lão Kế toán Nào rảnh Tay Xóa nhầm Ticket Báo Cáo DOA trên hệ Thống Lõi. Traceability bị đứt link Ref do Thằng con biến mất làm Form cha Mồ coi Tham Chiếu.
