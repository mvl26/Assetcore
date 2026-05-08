# Sơ đồ Cấu trúc Màn hình (Screen Map) IMM-04
# Mapping Giao diện UX theo Trải nghiệm của từng Actor

**Phân hệ:** AssetCore - IMM-04 (Lắp đặt & Thử nghiệm TBYT)
**Ngày lập:** 2026-04-15

---

## 1. MAPPING MÀN HÌNH THEO TỪNG ACTOR

Tùy thuộc vào Role khi Login, người dùng sẽ được điều hướng vào các Workspace (Màn hình chính) mang đậm tính "Cá nhân hóa công việc" của họ, thay vì nhìn thấy toàn bộ Menu chức năng giống nhau. 

### 1.1 Actor 1: Kỹ thuật viên HTM / Biomed Engineer
Là lực lượng nòng cốt xử lý 80% thời lượng của một Phiếu Lắp đặt.

| Loại Màn Hình | Tên Giao Diện | Trạng thái Nhìn Thấy | Nhiệm Vụ Cốt Lõi |
|---|---|---|---|
| **Entry Screen** | Workspace Kanban: Nhiệm vụ tại Hiện Trường | `Draft`, `To_Be_Installed`, `Installing` | Cung cấp cái nhìn góc rộng: Máy nào đang đợi ở sảnh, máy nào đang tháo dỡ thùng. |
| **Xử Lý Chính** | Form Nhập Hồ sơ Bàn Giao | `Draft` -> `Pending_Doc_Verify` | Chụp/Scan tài liệu C/Q của máy đính kèm vào hệ thống. |
| **Xử Lý Chính** | Form Định Danh Barcode | `Identification` | Cắm súng Scanner, tít Laser đẩy Serial_No vào ERP. |
| **Xử Lý Chính** | Lưới Test Kỹ Thuật (Baseline Checklist) | `Initial_Inspection`, `Re_Inspection` | Sử dụng máy đo Dòng rò, đo tiếp địa... nhập thông số kỹ thuật thực tế vào bảng Checklist con. |
| **Exception UI** | Cửa sổ Báo hư/Thiếu Hàng (NC Form DOA) | Khởi phát khi nhập `Fail` vào bảng lưới Test | Viết lý do, chụp ảnh chỗ rò điện, yêu cầu Hãng đổi cáp mới/đổi nguyên máy. |

### 1.2 Actor 2: Trưởng Workshop (Kỹ Sư Trưởng)
Chỉ giám sát và giải quyết tắc nghẽn kỹ thuật từ KTV cấp dưới.

| Loại Màn Hình | Tên Giao Diện | Trạng thái Nhìn Thấy | Nhiệm Vụ Cốt Lõi |
|---|---|---|---|
| **Entry Screen** | Cashboard Ticket Cần Chú Ý | `Re_Inspection`, Phiếu đang dính lô `DOA NC` | Tìm gấp các máy đang kẹt lại không lắp được do thiết bị lỗi, đứt ngầm. Giục Hãng. |
| **Review UI** | Giao diện Xử lý Báo Hỏng (NC Processing) | Form `Asset QA Non Conformance` (Status: Open) | Chát với Hãng, cập nhật hướng fix (Bảo hành/Trả hàng). Khóa ticket NC. |

### 1.3 Actor 3: PTP Khối 2 (Lãnh đạo)
Chỉ thực thi thao tác Approval chốt luồng. Giao diện thiết kế theo triết lý "1 Chạm" (Tránh bắt Lãnh đạo đi tìm form).

| Loại Màn Hình | Tên Giao Diện | Trạng thái Nhìn Thấy | Nhiệm Vụ Cốt Lõi |
|---|---|---|---|
| **Entry Screen** | Inbox Ký Duyệt Chờ Xử Lý | Chỉ hiện các máy ở `Clinical_Release` | Thấy ngay con số "5 Máy chờ Ký Duyệt" hiện to trên Dashboard. |
| **Review UI** | Form Phê duyệt Nhanh (Fast Approve) | Trạng thái: `Clinical_Release` | Mọi trường khác bị sập/che mờ. Màn hình chỉ lộ 3 Field thông tin: MÃ PO + TÊN MÁY + Dòng Tóm tắt "All Passed". Góc phải dưới sáng rực Nút [Phê Duyệt]. |

### 1.4 Actor 4: Phụ trách QA / QMS (Quản lý Chất Lượng)
Đội ngũ gác cổng, cầm thanh kiếm Thượng phương Bảo kiếm Cục Bức Xạ.

| Loại Màn Hình | Tên Giao Diện | Trạng thái Nhìn Thấy | Nhiệm Vụ Cốt Lõi |
|---|---|---|---|
| **Entry Screen** | Rader Cảnh Báo Bức Xạ | Các máy ở state `Clinical_Hold` | Lọc riêng các Item nào có cờ Bức Xạ được khai sinh nhưng Đang Trống Giấy Phép. |
| **Exception UI** | Cổng Giải Cứu Tài Liệu Quan Trọng | Nhấn vào máy đang bị `Hold` | Form chỉ mở khóa một ô File Upload duy nhất: `qa_license_doc`. Thả PDF chứng chỉ an toàn bức xạ vào đây -> Hệ thống tự động đẩy form trở về mạch hoạt động của KTV. |

---

## 2. BẢNG MẪU CHI TIẾT TƯƠNG TÁC DỮ LIỆU CỦA MODULE 

Bảng cấu trúc Input/Output dưới đây mô tả chính xác tương tác của các Nhóm Giao diện đã phân loại với Hệ thống Data (Backend ERPNext).

| ID Screen | Tên Màn Hình Dành Cho User | Thuộc DocType? | Dữ liệu Hiển Thị Ra (Read) | Dữ liệu Nhập Vào (Write/Input) | Dữ liệu Sinh ra Sau Cùng (Output) |
|---|---|---|---|---|---|
| **SCR-ENTRY-KTV** | Dashboard Chờ Việc KTV | `Asset Commissioning` | List phiếu Lắp đặt đang ở trạng thái `Draft`, `Installing`... phân theo tên Khoa đặt máy | Click thao tác trực tiếp, Lọc Filter Barcode | Điều hướng sang Form Chi tiết SCR-FORM-KTV |
| **SCR-FORM-KTV** | Giao diện Xử Lý Nền Tảng | `Asset Commissioning` | Header PO, Model, Vendor. Các Section Khai báo Giấy tờ, Kỹ sư Hãng. | Điền Textbox, Đánh dấu Tick_Box hồ sơ, Thả File PDF, Nút Click Next State. | Dữ liệu thô lưu nháp. Chuyển Form State sang `Initial Inspection`. |
| **SCR-TABLE-TEST** | Bảng Nhập Lưới Chẩn Đoán Điện | `Commissioning Checklist` (Child) | Tên các bài Test chuẩn ISO (Dòng rò, Tiếp Địa đất, Điện áp) | KTV nhập trị số thực (Float Data), Tích thả Drop_down `Pass/Fail` | Cờ cờ Validate: Nếu Toàn Lưới Xanh (Pass) => Form mẹ được quyền chuyển state Release. |
| **SCR-FORM-EXCEPT** | Giao diện Báo Lỗi Khẩn (Ticket) | `Asset QA Non Conformance` | Mã số Máy Lỗi gốc, Tên KTV báo lỗi, Thời gian tạo Ticket. | KTV ghi Mô tả "Lỗi cháy nổ", Thả ảnh Proof. Lãnh đạo nhập Text "Hướng Khắc Phục". | Chặn chết Ticket mẹ không cho đóng hồ sơ nghiệm thu nếu Ticket sự cố DOA này chưa được chuyển Status `Fixed`. |
| **SCR-FORM-REVIEW** | Phê Duyệt Phát Hành 1 Chạm | `Asset Commissioning` | Chỉ lộ Kết Quả Toàn View Test Grid (Tất cả phải Xanh). File Upload C/Q gốc. | Một Nút Click Duy Nhất (Action Button) `Approve`. | Script ngầm `mint_asset()` khởi phát: Gen ra 1 Tài sản (`Asset`) In Use bay thẳng sang Kho/Kế Toán. |
