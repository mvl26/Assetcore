# Chi tiết Thiết kế Giao diện Form (Form Layout & UI Behavior)
# Phân hệ IMM-04 - Nhóm DocType Lắp đặt & Bàn giao

**Dự án:** AssetCore v1.0
**Nguyên tắc Thiết kế:** ERPNext Client UI tuân thủ triệt để tính năng `Depends On` (Hiển thị/Ẩn động theo Trạng thái) và `Read Only Depends On` (Khóa Edit động) để điều phối luồng thao tác của User đúng theo Flowchart của IMM-04.

---

## 1. FORM `ASSET COMMISSIONING` (BẢNG MẸ CHÍNH LUỒNG)

Đây là Form rường cột, nắm phiên làm việc của hầu hết mọi diễn tiến Workflow. Form được chia làm **1 Header** và **4 Section Tab**. 

### 1.1 Vùng Tóm tắt Tiêu đề (Header Section)
*Nằm trên cùng (Ngay dưới dải Ribbon Button Ký Duyệt).*

- **Trạng thái Mẫu (Workflow State):** Hiển thị khối Label to rõ (Draft, In-Progress, Release_Hold) góc màn hình. Cờ Đỏ = Lỗi/Hold, Xanh Lá = Pass, Vàng = Đang xử lý.
- Dữ liệu hiển thị (Static/Primary):
  - `master_item`: Mã Mẫu Thiết bị (Link, *Mandatory mọi state*).
  - `vendor`: Nhà cung cấp (Link, *Mandatory*).
  - `po_reference`: Nguồn tham chiếu gốc PO (Link).
  - `final_asset`: Tài sản được gen ra cuối luồng (Link, *Read Only 100%*).

### 1.2 Layout Tab 1: Khởi Tạo Lắp Đặt Sự Cố (Mở khoá ở Phase đầu)
- **Tùy biến hiển thị:** Mở cho phép Edit xuyên suốt trạng thái `< Initial_Inspection`. 
- **Trường Dữ liệu:**
  - `installation_date` (Date, *Mandatory khi State qua To_Be_Installed*).
  - `is_radiation_device` (Checkbox, *Read Only*, Fetch từ Item Core). -> **Highlight Đỏ & Field quan trọng cho Dashboard Cảnh báo.**
  - Nhóm `Định Danh_Barcode` (Section Break):
    - `vendor_serial_no`: *Bắt buộc Focus Nhập liệu* (Mandatory mở khoá ở State: `Identification`). -> **Field quan trọng phục vụ Tra cứu sau này.**
    - `custom_internal_qr`: Dành cho Viện dán tem riêng (Optional).

### 1.3 Layout Tab 2: Hồ Sơ Chất Lượng (Document QMS Tab)
- **Tùy biến hiển thị:** Kích hoạt nhập liệu mạnh nhất lúc State = `Draft` chuẩn bị chuyển sang `Pending_Doc_Verify`.
- **Trường Child Table `Commissioning Document Record`:** 
  - Giao diện dạng Bảng (Grid). Mỗi hàng ép chứa Drop_down: `CO`, `CQ`, `HDSD`. 
  - Khối Status (Select: `Missing`, `Received`).
  - Hộp thạch Upload: `file_doc`. (Script chặn ở `Pending_Doc_Verify` không cho nộp rỗng).
- **Block Khẩn Cấp Bức Xạ:**
  - Field `qa_license_doc` (File Upload): Nằm riêng một dòng dưới đáy Bảng hồ sơ.
  - *Read Only Default*, ngoại trừ User Gắn Role `QA Risk Team` ở State `Clinical_Hold` (Kích hoạt Edit để kéo thả giấy phép thả khóa).

### 1.4 Layout Tab 3: Cụm CheckList Kỹ thuật (Test Baseline Tab)
- **Tùy biến hiển thị:** Hoàn toàn bị giấu đi/Đóng băng khi thiết bị chưa có Serial (Trạng thái < `Initial_Inspection`). Sáng lên chói loá, Mở khoá Data Edit khi State chạm ngưỡng Review (`Initial_Inspection`, `Re_Inspection`).
- **Child Table `Commissioning Checklist`:** 
  - Trải rộng full chiều ngang Grid Form.
  - Input `Giá Trị Thực Đo` (Float).
  - Cột Output Status `Pass/Fail` (Highlight đỏ nếu chữ 'Fail').
  - Cột `Note DOA`: Mở khóa Required nếu Trạng thái báo `Fail`. 

---

## 2. FORM `ASSET QA NON CONFORMANCE` (PHIẾU NGOẠI LỆ / DOA)

Phiếu này không dính dáng đến luồng Sinh Asset (Khác Cha). Mục tiêu dùng lưu vết tranh chấp / Audit Quality / Trực diện Báo Cáo Hội Đồng. Dựng bố cục kiểu Ticket Support.

### Bố cục Layout Đơn Tuyến (1 Màn dọc duy nhất)

| Cụm Layout / Tên Trường | Thiết lập Trạng Thái (UI/UX) | Mục đích Kép (Nghiệp vụ - UI) |
|---|---|---|
| Mã Vạch Liên Kết Bản Mẹ (`ref_commissioning`) | Link Field (Read Only) | Trace ngược lên Tờ khai Sinh Asset Gốc. |
| Loại Sự cố (`nc_type`) | Drop_down (DOA, Missing_Part, Safety_Fail) | Edit ở State Khởi tạo. (Field DashBoard Report đánh giá Độ nát của Hãng cấp). |
| Trạng thái Xử lý (`resolution_status`) | Select (Open, Fixed, Rejected) | **Highlight Label To**. Khoá cứng Field ở Open ngoại trừ Kỹ Sư Trưởng. |
| Ảnh Bằng Chứng (`damage_proof`) | Image Drag-n-Drop Box | Bắt buộc đính kèm Ảnh khi lưu. (Audit Check) |
| Lãnh đạo Đóng Phiếu Chốt Sale (`resolution_note`) | Text Area | Read_Only cho mọi user. Editable đối với Role Hãng / Vice President. (Audit Track Log) |

---

## 3. MAPPING FIELD ↔ BEHAVIOR PHỤ THUỘC WORKFLOW STATE

Công thức ma trận UI để config thuộc tính `Depends_On` (Ẩn/Hiện) và `Read_Only_Depends_On` (Khóa/Mở) trong App Asset Commissioning.

| State / Group | Action Fields Trọng Điểm Cần Edit | Cụm Field Bị Treo Đóng / Ẩn Núp |
|---|---|---|
| **Draft** | Cụm Model, Nhập List Giấy Tờ, Số Lượng | Bảng Lưới Checklist Đo Điện (Ẩn 100%), Ô Ký Serial_No (Read_Only) |
| **Installing** | Lịch Lắp đặt thực tế, Tên Kỹ Sư. | Bảng Checklist bị khóa nháp |
| **Identification**| Trường TextBox `vendor_serial_no` phát sáng. | Khóa Tab Lắp Mua Sắm. |
| **Initial Inspection** / **Re_Insp..** | Sáng Bảng Data Input `baseline_tests`. Sáng Box `Báo Hỏng DOA` nếu Test lỗi. | Khóa Edit Header Model/Vendor (Không cho tráo máy khi đang đi đo điện). |
| **Clinical Release** | Tab Data Grid Nhập xong Bị khóa mờ đi 100%. | Một Rừng CheckBox/Grid/Hồ sơ bị Khóa Ký Đóng Mộc (Khóa chết 100%). Lãnh đạo chỉ nhìn Thấy cái Nút To Nhất "Approve". |

---

## 4. FIELD QUAN TRỌNG ĐỂ CẮM VÀO DASHBOARD / AUDIT

**A. Thiết Kế Phục Vụ Dashboard Thống Kê Giám Đốc:**
- Phải kéo Field `docstatus` vào Biểu Đồ Thể Hiện: Tỉ lệ Thiết bị Thông Quan / Bị Kẹt trên Tổng Số Máy Nhập in Kho.
- Đếm tổng số Record có phát sinh `NC Form` chia / Tổng Số `PO_Ref` nhập trong tháng => Dựng Biểu đồ: **Nhà Thầu Kém Chất Lượng** (Độc quyền QMS).

**B. Thiết Kế Phục Vụ Phân Tích Audit Nhật Ký Sự Kiện:**
- Track Changes Log: File CheckList (Tab 2) và Tab 3 Rất Dễ Bị Sửa lén điểm số Fail -> Pass. Frappe sẽ cắm Version Histoy Tracking cứng ngắt lên toàn bộ form.
- Khi Click Nút Approval: Sinh Log Text ghi đè Event - *"Lãnh Đạo X Duyệt với Chữ Ký Số XYZ lúc hh:mm. Đã Verify NC = 0"*. Tồn tại ở dưới Cùng Section Form (Timeline Log Record).
