# Bộ Chỉ Tiêu Kiểm Thử Chi Tiết (QA & UAT Test Suite) - IMM-04

Tài liệu này là kịch bản (Test Scripts) để phòng QA và các Trưởng Khối/Phòng thử nghiệm trước khi đóng gói Module IMM-04 đưa vào Clinical Use (Sử dụng vận hành y khoa thực tế). 

Định dạng bảng tương thích chuẩn Word-Ready để Export ra tài liệu Đào tạo ISO.

---

## 1. Kịch bản UNIT TEST (Dành cho Developer QA)

Đánh giá mức độ độc lập của từng Logic Server Script & Rule Engine:

| ID | Test Scenario | Pre-condition (Tiền điều kiện) | Test Steps (Bước thực hiện) | Expected Result (Kết quả lý thuyết) | Actual Result | Status |
|---|---|---|---|---|---|---|
| `UT-01` | Test chống trùng Serial Number (Rule `VR-01`) | TRONG hệ thống có 1 máy MRI trùng `custom_vendor_serial = 'X-123'`. | 1. Mở Form IMM-04 mới.<br>2. Ở mục Identify gõ Barcode `X-123`.<br>3. Bấm Save. | Ném lỗi đỏ `frappe.throw`: "Trùng Serial Hãng". Bị hủy thao tác Save. | | |
| `UT-02` | Test bắt buộc File Đính kèm (Bức Xạ) | Form thuộc về Item Máy CT X-Quang (`is_radiation = 1`). Form đang nằm ở state `Clinical_Hold` | 1. Không Upload giấy phép Đo lường.<br>2. Bấm nút [Gỡ Hold / Thả Release]. | Trả lỗi Toast Đỏ: Cấm Releaes vì `qa_license_doc` đang Trống (Null). | | |
| `UT-03` | Test Rule Bắt buộc điền Note khi rớt (Fail Baseline) | Điền Grid Baseline Test với 1 dòng có `test_result = Fail` và `fail_note = Khuyết trắng` | 1. Di chuột ra ngoài hoặc ấn nút Lưu nháp. | Ném Validate Error: "Bắt buộc điền note lỗi vào dòng N". | | |

---

## 2. Kịch bản INTEGRATION TEST (Kiểm Thử Tích Hợp Xuyên Chuỗi)

Kiểm tra sự thông tắc của màng lưới từ Procurement -> Asset.

| ID | Test Scenario | Pre-condition | Test Steps | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|---|
| `INT-01`| Test luồng Xanh Thần Tốc (Happy Path Mượt) | Có 1 PO và Model Item chuẩn. Quyền Admin. | 1. Tạo form, kéo Link PO.<br>2. Tick đủ thẻ C/O, C/Q.<br>3. Nhảy node Install.<br>4. Quét ID Mới Tinh.<br>5. Pass toàn bộ Grid Test điện.<br>6. Ký nút Submit [Release]. | 1. Tờ Lắp Đặt đổi sang Status Submit Tĩnh.<br>2. ERPNext bắn ra một Core Asset mới tinh có Status="In Use", mang ID vừa test. Trace ngược về Form Nháp trên. | | |
| `INT-02`| Test luồng Lỗi DOA và Rớt Nước Mắt (Rework - Hủy bỏ) | Form cài đặt đang ở state `Installing`. Máy là Máy siêu âm. | 1. User ấn nút "Report DOA".<br>2. Trạng thái nhảy qua NC.<br>3. Tech không sửa nổi, User tạo tiếp luồng [Return].<br>4. Chốt Hủy Phá Hợp Đồng. | ERPNext nhảy báo động. KHÔNG có Asset nào được tạo ra. PO bị đánh cờ "Cancelled". | | |

---

## 3. Kịch bản UAT - Người Dùng Cuối (Thử Thách Actor Thật)

*Mục tiêu:* Đóng vai chính xác Kỹ thuật viên (KTV HTM), Trưởng Workshop (KT Trưởng) và PTP Khối 2 để truy soát hệ nhị phân (Permission Override).

### 3.1. Đối Tượng: PTP Khối 2 (Người cầm trịch giải ngân)

| ID | Scenario (Kịch bản vi phạm) | Pre-condition | Steps | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|---|
| `UAT-K2-01` | PTP Khối 2 Release ngầm máy hỏng / Băm Bypass | Login với Account Role `VP_Block2`. Dùng Form máy vừa rớt Tester bị gán mác Failed. | 1. Ép bấm nút Action -> `Release`. | Hệ thống giật Cờ Đỏ `VR-03`. Quyền làm Sếp lớn không Override được rào chắn Kỹ thuật của hệ thống Máy trạng thái. Bị từ chối nhả Asset. | | |
| `UAT-K2-02` | Chặn PTP Khối 2 Mở Mới Tài Sản Ảo | Nhận phong bì, muốn nhét 1 máy vô danh viện cớ tài trợ. | 1. Vào Giao diện Core của `AssetList`.<br>2. Nhấn nút màu Xanh `[+] New Asset`. | Bị giấu mất nút New. Hoặc nhấn vào sẽ bị màn hình cảnh cáo "Bắt buộc đi qua Module IMM-04 để đăng ký thẻ công cộng!". | | |

### 3.2. Đối Tượng: Kỹ thuật viên HTM (Chiến binh dán tem C/O)

| ID | Scenario (Kịch bản vi phạm) | Pre-condition | Steps | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|---|
| `UAT-TM-01` | KTV Lách Luật Hồ Sơ (Thiếu C/Q) | Login: `HTM Tech`. Đang cầm Thẻ Máy thở Mới ở Node `Draft`. | 1. Vào phần List Document.<br>2. Bỏ qua Checkbox "Giấy xuất xưởng (C/Q)".<br>3. Ép nhảy sang bước Lắp Máy. | Bị Nổ Popup vàng: "Chưa hoàn tất C/Q, không thể giao cho Khoa sử dụng máy". Kẹt tại Node cũ. | | |
| `UAT-TM-02` | KTV Sửa Gian Lận Dữ Liệu sau Đánh Giá | Login: `HTM Tech`. Form hiện đã vượt ải xong, có chữ ký của Trưởng Workshop. Trạng thái: Submitted. | 1. Lén mở vào lại Form.<br>2. Tìm ô Lỗi rớt (Fail_Note) định xóa bỏ thay bằng chữ "Máy mượt OK". | Nút `Save` biến mất vĩnh viễn. Field Dữ liệu cứng đơ như in PDF (Read-only Immutable state). | | |
| `UAT-TM-03` | Truy vết Sửa Luật Re-Inspection | Login: `HTM Tech`. Máy rớt test, buộc phải [Amend] tạo bản form v2. | 1. Nhấn nút [Amend].<br>2. Tạo thẻ mới. Cố tình không điền "Lý do hủy bảng v1". | Không thể Save form Amend. Bắt buộc phải hiện vết xước Audit Lịch sử đính kèm File gốc v1 bị Cancellled. | | |

### 3.3. Đối Tượng: Trưởng Workshop / KT Trưởng (Người cầm cân lỗi kỹ thuật)

| ID | Scenario (Kịch bản vi phạm) | Pre-condition | Steps | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|---|
| `UAT-WS-01` | Nút chặn DOA rác rưởi (NC chưa vá) | Login: `Workshop Head`. Máy bị nát 1 ốc DOA, Mở Phạt Hãng thẻ NC (Trạng Thái = Open). Máy vẫn pass Baseline Điện. | 1. Trưởng Nhấn Node -> Releaes Máy vì máy vẫn cắm lên màn hình ngon. | Bắt Còi Hệ Thống Server Python. Ném rào Validation: "Có phiếu lỗi mở NC! Bắt buộc sửa ốc vít (Close NC) mới được nhả máy cho Khoa dùng". | | |
