# UI Prototype Wireframe (IMM-04)
# Thiết kế Layout Dạng Text / Pseudo-HTML

**Phân hệ:** AssetCore v1.0
**Mục tiêu:** Thể hiện rõ khối Logic (Khối ẩn/hiện, Vị trí nút, Nơi hiện Cảnh báo đỏ/vàng) theo từng Màn hình của Hệ thống. Không chú trọng CSS, chú trọng cấu trúc Khung Xương (Wireframe).

---

## 1. MÀN HÌNH FORM CHÍNH: `ASSET COMMISSIONING` (Quyển Sổ Xử Lý Hiện Trường)
*Màn hình hiển thị cho KTV HTM / Biomed Engineer.*

```text
================================================================================
[ ERPNext Navbar ] 🔔 (Alert: 0)  |  User: HTM Technician
================================================================================
Breadcrumb: Hệ thống > Lắp đặt TBYT > IMM04-26-04-00001
--------------------------------------------------------------------------------
[ Header Area ]
[ State Badge: INITIAL_INSPECTION ] (Màu Vàng) 

⚠️ [ Warning Toast ]: "Gõ tay Serial! Cảnh báo có thể sai số so với Barcode Scanner."

[ Action Buttons ]:  [ LƯU YÊU CẦU ]   |   [ GỬI BÁO CÁO TEST NHÁP ] (Primary)
                     [ + Báo Cáo DOA (Sự Cố DOA) ] (Nút Bổ Trợ Xám)
--------------------------------------------------------------------------------
[ Section 1: Thông tin Lõi (Bị READ-ONLY khóa xám ở State Hiện tại) ]
 Item Model      : [ Máy thở ICU V60 - ReadOnly ]     | Vendor  : [ Philips VN - ReadOnly ]
 PO Ref          : [ PO-2026-0041 - ReadOnly ]        | Đơn Giá : [ *************** ] (Bị Giấu)
 Khoa Sử Dụng    : [ Khoa ICU - ReadOnly ]            | 
 ☑ [x] Là Thiết Bị CÓ Tia Phóng Xạ Bức Xạ (Red Highlight Label)

--------------------------------------------------------------------------------
[ TABS NAVIGATION ]
[ Thông tin Mua Sắm ]  |  [ Hồ Sơ C/Q ]  |  [ Mặt Bằng ]  |  [* ĐO LƯỜNG & CHẨN ĐOÁN *] (Active)
--------------------------------------------------------------------------------
[ Tab Active Body: Baseline Checklist Đo Điện ]
(Chỉ hiện Rõ ở State Initial Inspection. Các máy không có Serial Không Thể Mở Tab này)

* Chỉ Tiêu Đo Điện An Toàn (Mandatory):
+--------------------+----------------+---------+----------+-----------------------------+
| Hạng Mục           | Trị Số Đo (In) | Đơn Vị  | Đánh Giá | Note Lỗi DOA (Bắt buộc)     |
+--------------------+----------------+---------+----------+-----------------------------+
| Rò điện vỏ (µA)    | [ 150        ] | µA      | [ PASS ▼]| [ Khóa Xám không cho Edit ] |
| Trở Kháng Đất (Ω)  | [ 1.8        ] | Ω       | [ FAIL ▼]| [ Kẹp tiếp địa gãy ngàm ](*)|
| Khởi Động O2 (%)   | [ 99         ] | %       | [ PASS ▼]| [                         ] |
+--------------------+----------------+---------+----------+-----------------------------+
| + Add Row | (Bị Ẩn bởi Client Script để cấm User tự chế bài Đo)

[ Cục Quản Trị Cảnh Báo An Toàn ]
< Giấy Phép Cục Bức Xạ ATBXHN > : [ Drop PDF File Here ] (Required do Cờ Phóng xạ = 1)
--------------------------------------------------------------------------------
[ Footer Timeline Log ]
- 10:00 - Tạo mới Draft (Bởi User A)
- 10:15 - Cập nhật Serial_No = VNT-PHL-123 (Bởi User A)
================================================================================
```

---

## 2. MÀN HÌNH TỐC ĐỘ: `FAST APPROVAL SCREEN` (Phê Duyệt Lãnh Đạo Khối)
*Màn hình Triệt Tiêu Tiếng Ồn Chữ Nghĩa, dành cho `VP Block2`.*

```text
================================================================================
[ ERPNext Navbar ] 🔔 (Alert: 2)  |  User: Vice President
================================================================================
Breadcrumb: Inbox Ký Duyệt > Chờ Giải Quyết Lắp Đặt > IMM04-26-04-00001
--------------------------------------------------------------------------------
🔴 [ ERROR BOX (THROW) ]: Lãnh Đạo không Thể Ký Form Này Lúc Này! 
   "Lý do: Lưới Kỹ Thuật đang bị dính Lỗi 'Trở Kháng Đất' = FAIL. Đề nghị Mời Hãng Quay Lại"

[ Cụm Action Buttons Gác Khoá (Chỉ hiện khi Form đạt 100% PASS) ]
[ REJECT - Trả Kho ]   |   [ ✔️ APPROVED & GENERATE ASSET (PHÊ DUYỆT) ] (Nút Bự Xanh)
--------------------------------------------------------------------------------
[ OVERVIEW CARD (Khối Thông Tin Khổng Lồ Dễ Đọc) ]
+------------------------------------------------------------------------------+
| MÁY THỞ ICU V60 (Philips VN)                                                 |
| Trị Giá Lô Nhập: 850,000,000 VNĐ                                             |
| Serial Nhận: VNT-PHL-123                                                     |
|                                                                              |
| KẾT QUẢ ĐÁNH GIÁ CHẤT LƯỢNG: [ NGHIÊM TRỌNG: CÓ DOA CHƯA XỬ LÝ NGÀY QUA ]    |
| TÌNH TRẠNG GIẤY TỜ BỨC XẠ  : [ CHƯA CẬP NHẬT PDF CỤC BỨC XẠ ]                |
+------------------------------------------------------------------------------+

[ HỒ SƠ ẢNH VÀ CHỨNG CHỈ (Click để xem Nhanh) ]
🔗 [CQ_Origin.pdf]   🔗 [Ảnh_Máy.png]
================================================================================
```

---

## 3. MÀN HÌNH NGOẠI LỆ: `TICKET DOA NC RECORD` (Cửa Sổ Hứng Lỗi)
*Giao diện mở Pop-up hoặc New Tab khi Có Máy Test Rớt hoặc Thiếu Linh Kiện trong Thùng.*

```html
<!-- Cấu trúc Pseudo HTML Hiển Thị Đập Vào Mắt -->
<div class="form-container exception-route">
  <div class="red-banner">
    <h2>MẪU BÁO CÁO CHẤT LƯỢNG HÀNG DOA DƯỚI MỨC CƠ SỞ (TICKET)</h2>
    <span class="status-badge badge-OPEN">TRẠNG THÁI: TÌNH TRẠNG MỞ CHỜ XỬ LÝ</span>
  </div>

  <div class="row">
    <div class="col-6">
      <label>Link Gốc Trỏ Lại Máy Nhập: </label> <a>IMM04-26-04-00001</a> (Read-Only)
    </div>
    <div class="col-6">
      <label>Mã Lỗi Khởi Điểm: </label> <select disabled><option>Sự Cố Thiếu Vỏ Điện/Đo Mạch</option></select>
    </div>
  </div>

  <div class="image-proof-box">
    <h4>Bằng Chứng Thiệt Hại Mặt Thường / Đứt Nối</h4>
    <div class="upload-zone dashed-border">
       <img src="day-dien-dut.jpg" width="100px">
    </div>
  </div>

  <div class="vendor-reply-section">
    <h4>Biên Bản Làm Việc Ràng Buộc Penalty (Chỉ VP Block 2 Được Sửa Mức Tiền)</h4>
    <textarea rows="4" readonly>Hãng Philips Xác Nhận Do Lỗi Vận Chuyển Đội Bốc Sứ VN, Hẹn Chiều T4 Mang Pin Mới Lên Lắp Bù.</textarea>
    <label>Mức Tiền Phạt Lưu Kho: </label> <input type="number" class="locked-admin-field" value="0">
  </div>
</div>
```

---

## 4. MÀN HÌNH TỔNG QUAN: `DASHBOARD METRICS` (Mặt Trận Số Liệu)
*Bàn làm việc của Quản Lý, Hiện Bảng Chỉ Số Sống Của Bệnh Viện Mảng Tài Sản.*

```text
================================================================================
  QUẢN TRỊ TRUNG TÂM BÀN GIAO THIẾT BỊ Y TẾ DOLLAR-RATE                     🔍
================================================================================

[ BOX CẢNH BÁO KHẨN ĐỎ LỬA (CRITICAL HOLD) ] 
> ĐANG CÓ ( 03 ) THIẾT BỊ NẰM CHẾT Ở TRẠNG THÁI [CLINICAL_HOLD] 
> TIỀM ẨN THIỆT HẠI: 3,5 TỈ VNĐ - ĐỀ NGHỊ BỔ SUNG LICENSE BỨC XẠ GẤP CỨU MÁY!

+-----------------+  +-----------------+  +------------------+  +------------------+
| MÁY CHỜ DUYỆT   |  | MÁY ĐANG LẮP RÁP|  | PHIẾU DOA MỞ LỖI |  | AVG TIME RELEASE |
|      05         |  |      12         |  |      01          |  |      3.2 Ngày    |
+-----------------+  +-----------------+  +------------------+  +------------------+

[ BỊỂU ĐỒ BAR CHART: NHÀ THẦU CÓ TỈ LỆ RỚT TEST DOA NHIỀU NHẤT QUÝ NÀY ]
^ Trục Lỗi
|       
|       [Siemens]
|          |     
| [GE]     |     [Philips]
|   |      |        |
|###|######|########|###
+--------------------------------> Vendor Name

[ BẢNG MÀU LƯU VẾT TRỄ NẢI MẶT BẰNG (TABLE LIST) ]
+-------------------+---------------+------------------+------------------+
| Mã IMM04 Trễ Nhịp | Hãng Mua      | Hẹn Lắp Mặt Bằng | Đang Kẹt Ở Cửa   |
+-------------------+---------------+------------------+------------------+
| IMM04-26-04-00021 | Hóa Sinh X    | 24/03/2026 ⚠️    | To_Be_Installed  |
| IMM04-26-04-00088 | Laser Mỹ      | 01/04/2026 ⚠️    | Installing       |
+-------------------+---------------+------------------+------------------+
```
