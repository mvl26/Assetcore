# Thiết Kế Dashboard UI & Hệ thống Cảnh Báo (Alert) 
# Định hướng Dữ liệu Quản trị (Data-Driven UX) cho IMM-04

**Phân hệ:** AssetCore v1.0
**Nguyên tắc thiết kế Thống kê:** Dashboard trong ERPNext không phải là trang trí. Nó là Công cụ định hướng dòng tiền (KPI Release) và rủi ro Sinh ngọc (DOA Rate). Thiết kế phân theo từng Role chứ không thiết kế chung 1 màn hình Rác.

---

## 1. LAYOUT DASHBOARD THEO TỪNG ACTOR

Mỗi Actor sẽ có trang chủ truy cập `Workspace` khác nhau khi tiến vào module AssetCore.

### 1.1 Dashboard Lãnh Đạo (PTP Khối 2 / Giám đốc)
**Mục tiêu:** Cắt giảm thủ tục, thúc đẩy tốc độ Đưa Thiết Bị vào Hoạt Động (Release), nhìn nhận năng lực Hãng Thầu.
- **Vị trí trên cùng (Top Number Cards):**
  - Widget 1: **"Thiết bị chờ Ký Duyệt Release"** (Số bự màu Xanh lá).
  - Widget 2: **"Tổng Tỉ lệ Thiết Bị Hỏng DOA Tuần Này"** (Số % màu Cam).
- **Vị trí Giữa (Biểu đồ Cột):** "Thời gian Trung Bình Nhận Máy ➔ Release (Avg. SLA) Phân Theo Khoa".
- **Vị trí Đáy (Data List):** Top 5 Phiếu Lắp Đặt Bị Ngâm Dông Nhất Chờ Duyệt Lãnh Đạo.

### 1.2 Dashboard Đội QA / Quản lý Rủi Ro (QMS)
**Mục tiêu:** Bắt chết các lọt lưới về hồ sơ và An sinh phóng xạ. Phạt nhà thầu.
- **Top Number Cards:**
  - Widget 1: **"SỐ LƯỢNG MÁY BỊ CLINICAL_HOLD"** (Màu Đỏ Khẩn, chớp nháy).
  - Widget 2: **"Phiếu Cảnh Cáo DOA (Open)"** (Màu Vàng).
- **Vị trí Giữa (Biểu đồ Tròn Donut):** "Nguyên nhân Gây Hỏng Khui Thùng". Chia rãnh: Lỗi Điện / Thiếu Linh Kiện / Setup Fail.
- **Vị trí Đáy (Bảng Phạt Penalty):** Bảng tổng hợp số Tiền Phạt (`penalty_amount`) thu được từ Các phiếu DOA trong Quý.

### 1.3 Dashboard Kỹ Ưu / Trưởng Workshop 
**Mục tiêu:** Quản lý lùi luồng, điều quân sửa máy điện.
- **Top Number Cards:**
  - Widget 1: **"Lịch Hẹn Cài Đặt Hôm Nay"** (Màu Xanh Dương).
  - Widget 2: **"Số Máy Cần Re-Inspect (Đo Lại Lần 2)"** (Màu Tím).
- **Vị trí Giữa:** Danh sách Bảng Trực ca KTV nào đang xử lý Ticket nào.

---

## 2. CHI TIẾT TỪNG METRIC & CHUỖI DRILL-DOWN FLOW

Drill-down (Click Click) là linh hồn của Dashboard. Con số không mọc ra vô cớ.

| Tên Metric Widget | Hiển thị Biểu Đồ / Số | Thao tác Click Click Đi Đâu (Drill-Down Flow) | Khớp vào Record Thuộc DocType |
|---|---|---|---|
| **Số Lượng Clinical Hold** | Number Card, Bôi Đỏ rực. (VD: "04"). | Click Con số -> Danh Sách List View tự động gài Filter `Workflow State = Clinical_Hold`. | `Asset Commissioning` |
| **DOA NC Ticket Open** | Number Card, Màu Cam. (VD: "07"). | Click Con số -> Nhảy vào List View, Filter `State = Open`. Click tiếp 1 Ticket vào thẳng Màn hình Tranh Luận Phạt Tiền Nhà Thầu. | `Asset QA Non Conformance` |
| **Phân Bố Máy Theo Vendor**| Biểu đồ Cột (X=Tên Hãng, Y=Số máy nhập) | Click 1 Cột Xanh của "Philips" -> Đổ ra List Các Mã Máy Đang do Philips thầu trong tháng này. | Trích Data từ `po_reference.supplier` |
| **Avg. Time to Release** | Biểu Đồ Đường (Trend Line theo Tuần). | Click vào điểm High-Peak (Đỉnh nợ đọng) lúc T3 -> Bật ra Báo Cáo Query Thống Kê Tổng (Script List Bóc Tách Máy nào nằm kẹt bao nhiêu ngày). | Script đo từ `Creation Date` tới `Release Date`. | 

---

## 3. THIẾT KẾ ALERT CẢNH BÁO (BÁO ĐỘNG HỆ THỐNG GIAO DIỆN)

Hệ thống không chỉ chờ User mở Dashboard, nó còn tự động đánh "chuông" khi thời gian đếm ngược (SLA Timer) chạm ngưỡng.

### Mức 1: Cảnh Báo Treo Giấy Phép Bức Xạ (CRITICAL 🔴)
- **Vị trí hiển thị:** Trên Góc Chuông Notification Right-Top Menu ERPNext. Kèm Gửi Tag vào Email của Trưởng QA.
- **Màu Sắc Icon:** Đỏ Chớp (Pulsing Red)
- **Logic:** Hễ `is_radiation` = True VÀ State rơi vào Cửa `Clinical_Hold` = Bắn Chuông Liên Tục Mỗi 24h.
- **Click Nút Alert:** Mở bung Thẳng Form đó để Hối thúc Tải Document Giấy phép Cục Lên Ngay.

### Mức 2: Cảnh Báo Quá Hạn Hẹn Lắp Mặt Bằng (MAJOR 🟠)
- **Vị trí hiển thị:** Trong In_App Warning Board (Bản tin hệ thống) thuộc Workspace TBYT.
- **Màu Sắc Icon:** Cam / Vàng Đậm.
- **Logic:** `installation_date` < Giá Vị `Now(Date)` VÀ State Mới Chỉ Dừng Ở `Draft` Hoặc `To_Be_Installed`.
- **Click Nút Alert:** Trỏ đến Dashboard Thống kê Lược Đồ Thời gian ngâm Vận đơn. 

### Mức 3: Nhắc Việc Phê Duyệt Cuối Cùng (NORMAL 🔵)
- **Vị trí hiển thị:** Gửi Zalo/Email Đích Danh VP Block 2 vào lúc 8h00 Sáng Hàng Ngày.
- **Màu Sắc Icoin:** Xanh Dương Lịch Sự.
- **Logic:** Bóc Dữ Liệu Các Giao Dịch Dồn Lại Ở Cổng `Clinical_Release` Trong 24H Trở Lại Đây.
- **Click Nút Alert:** Bật thẳng Về `Mục List View Chờ Phê Duyệt Nhanh` (Giao Diện Review Chờ Ký 1 Nút). Tối giản Thao tác.
