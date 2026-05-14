# Kiến trúc UI theo Hướng Trạng thái & Actor (IMM-04)
# Thiết kế Giao diện Tập trung vào Trải nghiệm Người dùng (UX-Driven Architecture)

**Dự án:** AssetCore v1.0
**Nguyên tắc cốt lõi:** Thay vì sử dụng menu phân mảnh truyền thống, hệ thống UI của IMM-04 được thiết kế tập trung xoay quanh **Actor (Người dùng)**, **State (Trạng thái Workflow)** và **Task (Tiến trình Công việc)**. Khi một Actor đăng nhập, hệ thống TỰ ĐỘNG mang những công việc thuộc đúng state của họ lên màn hình chính.

---

## 1. PHÂN LOẠI UI TỔNG QUAN

Hệ thống cung cấp 4 dải UI giải quyết 4 bài toán khác biệt trong luồng nghiệm thu thiết bị:

| Loại UI | Định nghĩa & Mục đích | Workspace chính |
|---|---|---|
| 🟢 **Task UI (Primary)** | Nơi nhập liệu, bóc dỡ lô hàng, tick checklist. Dành cho người thực thi trực tiếp tại hiện trường. | Workspace KTV, Cửa sổ Checklist Form. |
| 🔵 **Review UI (Primary)** | Giao diện gọn gàng, read-only 80%, chỉ lộ ra các con số quan trọng (Giá tiền, Test kết quả fail/pass) và 1 Nút bấm TO: Approve / Reject. | Giao diện Lãnh đạo Khối. |
| 🟠 **Exception UI (Secondary)**| Giao diện xử lý khủng hoảng (Máy đập vỡ, rò điện, thiếu C/Q). Chứa form ghi nhận nguyên nhân, upload ảnh, đòi bồi thường hãng. | Form Báo cáo DOA (NC Record Form). |
| 🟣 **Monitoring UI (Secondary)**| Giao diện tổng quan cho Quản lý. Dashboard Dashboard đếm số máy đang Lắp, số máy bị Hold, đo đếm SLA. | Workspace Quản lý (Workshop Head / QA). |

---

## 2. KIẾN TRÚC UI THEO ACTOR (AI NHÌN THẤY GÌ KHI LOGIN?)

### ACTOR 1: Kỹ thuật viên (HTM Technician) - Dân "Chân tay"
- **Mục tiêu:** Cần thao tác cực nhanh, gọn, ít chữ. 
- **Màn hình khi Login:** Một bảng danh sách "Máy đang dở dang cần xử lý".
- **Hành động (Interaction Unit):** 
  - *Tạo mới:* Mở form (ID tự sinh) -> Gõ số PO -> Hệ thống điền hộ thông tin. 
  - *Tick hồ sơ:* Bảng `Task UI` đánh dấu tick CO, CQ. 
  - *Quét Barcode:* Trải nghiệm máy tính bảng: Chĩa súng quét Barcode thẳng vào field -> Hệ thống tự Save.
- **UI không xuất hiện:** Hoàn toàn không nhìn thấy View Phê duyệt hay Nút Approve.

### ACTOR 2: Kỹ sư Sinh y (Biomed Engineer) - Dân "Đo Lường"
- **Mục tiêu:** Tập trung vào bảng thông số kỹ thuật (Kẹp điện trở, soi dòng rò bức xạ).
- **Màn hình khi Login:** Danh sách Thiết bị ở Gate `Initial_Inspection`.
- **Hành động (Interaction Unit):**
  - Mở phiếu -> Cửa sổ UI tự động bôi mờ các Tab Thủ tục giấy tờ của KTV, chỉ bật sáng Tab **"Baseline Checklist"** (Task UI).
  - Điền trị số: Nhập số -> UI tự đổi màu Row (Xanh = Pass / Đỏ = Fail).
  - *Exception Unit:* Nếu chọn Fail, UI bung ra Popup "Báo cáo Sự cố (DOA)" bắt buộc kéo thả ảnh chụp thiết bị hỏng. Bấm gửi báo cáo.

### ACTOR 3: Phó Trưởng Phòng Khối 2 (VP Block2) - Người "Ký Duyệt"
- **Mục tiêu:** Lãnh đạo bận rộn, không có thời gian đọc từng tờ giấy, chỉ cần xem kết luận.
- **Màn hình khi Login:** **Review UI** (Giống hòm thư In-box). Cảnh báo số lượng máy ở cổng `Clinical_Release`.
- **Hành động (Interaction Unit):**
  - Mở phiếu. Form UI bị thu ngắn lại tối đa: Chỉ hiển thị Header (Trạm, Vendor, Serial) và Tab Kết quả test tổng (Pass Toàn Bộ).
  - Góc phải/dưới cùng là 2 Nút Action: **[PHÊ DUYỆT ĐƯA VÀO SỬ DỤNG]** (Màu xanh đậm) / **[CANCEL DO LỖI QMS]** (Màu xám).

### ACTOR 4: Đội QA / QLCL (Risk Team) - Người "Cầm Trịch Quy Trình"
- **Mục tiêu:** Canh gác tử huyệt (ATBXHN).
- **Màn hình khi Login:** **Monitoring UI** đẻ ra List máy có nguy cơ cao ở state `Clinical_Hold` (Màu cam/đỏ).
- **Hành động:** 
  - Kéo thả giấy phép vào `qa_license_doc` -> Giải cứu thiết bị khỏi Hold, Trả mạch về cho Biomed.

---

## 3. MAPPING UI ↔ WORKFLOW STATE

Mỗi State của hệ thống ERPNext được khoác một "Chiếc áo giao diện UI" riêng. Các Tab không liên quan sẽ bị giấu đi theo Script đã dựng:

| Workflow State | Cửa sổ / Tab Hiển Thị Trên Form | Loại UI Thiết Kế | Trọng tâm Tương tác |
|---|---|---|---|
| `Draft` | Tab 1: **Thông tin Chung & Mua Sắm** | Task UI (Thu thập Info) | Gõ PO, điền Tên Kỹ sư hãng |
| `Pending_Doc_Verify` | Tab 2: **Checklist C/Q, Bàn Giao** | Task UI (Tick Checkbox) | Thả ảnh, Checkbox hồ sơ CQ |
| `To_Be_Installed` | Tab 3: **Checklist Mặt Bằng Điện** | Task UI (Verification) | Phối hợp KTV + Cơ điện check nguồn điện |
| `Identification` | Cụm Field: **Định Danh / Barcode** | Task UI (Input tốc độ cao) | Quét Laser SN_Vendor, Auto-sinh QR |
| `Initial_Inspection` <br> `Re_Inspection` | Tab 4: **Baseline Tests** | Task UI (Nhập liệu kỹ thuật) | Lưới Metric đo lường, Tự đổi màu theo Pass/Fail |
| `Clinical_Hold` | Field Box: **Cục ATBXHN** | Exception UI (Giải cứu) | Chỉ sáng 1 ô Upload file License. Toàn bộ form Freeze. |
| State có Mở `NC` | Giao diện **Phiếu Báo Hỏng DOA** riêng biệt | Exception UI (Xử lý Khủng hoảng) | Theo dõi lịch sử cãi vã, thay thế, sửa chữa máy |
| `Clinical_Release` | Thu gọn Toàn Bộ Form (Header + Kết quả) | Review UI (Ký duyệt) | Workflow Button (Approve) bự, nằm chính giữa/góc phải |

---

## 4. DANH SÁCH MÀN HÌNH PRIMARY (TÓM GỌN)

Chốt lại, IMM-04 có 3 Giao diện làm việc (Workspace) độc lập, không xài chung Menu:

1. **Giao diện Tiếp nhận Hiện Trường (KTV + Kỹ Sư):**
   - URL: `/app/asset-commissioning`
   - Nhiệm vụ: Xử lý dữ liệu thô, biến máy đóng thùng thành 1 Phiếu hồ sơ hoàn chỉnh. (Bao gồm các form điền Baseline đỏ/xanh, Barcode quét).

2. **Giao diện Phê duyệt Lãnh Đạo (VP Block2):**
   - URL: Cấu hình `List View` chỉ Filter state `Clinical_Release`.
   - Nhiệm vụ: Lướt, Read-only và Bấm nút "Phê duyệt" liên hoàn trong vòng 5 phút mỗi sáng ký duyệt.

3. **Giao diện Xử Lý Sự Cố Vi Phạm Chất Lượng (DOA NC Record):**
   - URL: `/app/asset-qa-non-conformance` 
   - Nhiệm vụ: Nơi Biomed cãi nhau với kỹ sư Nhà Thầu. Ghi rõ máy hỏng cái gì, hãng hứa đền cái gì, có penalty hay không. Đây là rào chắn thứ 2 không để máy rò điện rớt xuống khu lâm sàng. 
