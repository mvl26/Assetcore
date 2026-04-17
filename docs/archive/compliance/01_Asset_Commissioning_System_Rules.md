# System Executable Rules: Asset Reception & Commissioning

**Căn cứ văn bản:** BM01.01.02 (Bảng kiểm hồ sơ tài liệu) & BM01.02.02 (Danh mục kiểm tra điều kiện lắp đặt).
**Bối cảnh:** Quy tắc cấu hình System-Logic trên ERPNext đáp ứng chuẩn của WHO/Bộ Y Tế đối với khâu Tiếp nhận & Lắp đặt tài sản (AssetCore - Commissioning).

---

## 1. Cơ cấu biểu mẫu Digital (Checklist Structure)

Hệ thống số hóa các Checkbox và lựa chọn trạng thái trên form thành Child-Tables:

**Bảng: `Document Checklist Table`** (Số hóa BM01.01.02)
- Hàng 1: Hợp đồng/Đơn hàng (PO)
- Hàng 2: Báo giá trúng thầu
- Hàng 3: CO (Xuất xứ)
- Hàng 4: CQ (Chất lượng)
- Hàng 5: Packing List/Tờ khai hải quan
- Hàng 6: Giấy ủy quyền, Warranty form
- Hàng 7: Báo cáo an toàn bức xạ (Chỉ xuất hiện khi Loại Sinh phẩm/Máy = Bức xạ)

**Bảng: `Installation Condition Checklist Table`** (Số hóa BM01.02.02)
- Điều kiện Điện (Ac source)
- Điều kiện Khí (Gas supply)
- Điều kiện Mặt bằng (Floor Space & Loading weight)
- Điều kiện Môi trường (Nhiệt độ, độ ẩm chuẩn TCVN)
- Điều kiện Chống nhiễu bức xạ (Chì/Gương chì)

---

## 2. Validation Rules (Quy tắc Validate hệ thống)

Để đảm bảo mọi quy trình "No manual-only steps", hệ thống gắn Hook vào Nút Chuyển Trạng Thái:

- **Hard Validation (Chặn cứng/Báo lỗi):**
  - **`V1`**: Khi chuyển từ `Draft` -> `Pending Site Handover`: Nếu có bất kỳ dòng nào trong bảng `Document Checklist Table` có `is_mandatory = 1` MÀ `status = "Chưa nhận" / "Không có"`, Hệ thống văng lỗi *`frappe.throw("Thiếu giấy tờ pháp lý bắt buộc: [Tên tài liệu]")`*. Không lưu thao tác.
  - **`V2`**: Khi chuyển từ `Pending Site Handover` -> `Installing`: Tất cả các mặt hàng khai báo trong `Item List` BẮT BUỘC phải điền mục `Serial Number`.
  - **`V3`**: Không thể đóng / Complete nếu `Installation Condition Checklist Table` vẫn còn dòng tick "Không đạt" (`is_met = 0`). Nguy cơ cháy nổ nếu lắp đặt.

- **Soft Validation (Cảnh báo mềm):**
  - **`V4`**: Thiếu file đính kèm/Scan của Manual sử dụng/Bảo trì. Cho phép đi tiếp nhưng Popup cảnh báo màu vàng: *"Hãy đảm bảo Vendor sẽ bổ sung Manual trước khi bước vào giai đoạn Pending Training"*.

---

## 3. Approval Matrix (Ma trận phê duyệt logic)

| Cấp duyệt (Role) | Chức năng (Node) | Điều kiện kích hoạt Logic duyệt |
|---|---|---|
| **Cán bộ TBYT** | `Verify Document` | Nút [Approve] chỉ hiển thị nếu User nằm trong danh sách tổ công tác TBYT và đã điền đủ bảng Checklist. |
| **Phụ trách Khoa/Phòng**| `Confirm Handover` | Nút [Confirm] chỉ Send Email yêu cầu cấp quyền mở tới Trưởng khoa của *Đúng* cái Khoa Đích (`Receiving Department`). |
| **Kỹ sư Hãng/Vendor**| `Log Installation` | Hệ thống tự trigger gửi Link kèm Access Token (hạn 48h) qua mail Vendor để vào tick bảng "Đã Lắp xong & Thỏa điều kiện". |

---

## 4. Báo cáo Tệp đính kèm bắt buộc (Required Documents) 

| Node / Trạng thái | Yêu cầu phải Upload PDF/Images đính kèm |
|---|---|
| `Pending Document Review` | Phải đính kèm CO/CQ bản gốc bản scan PDF do hải quan / hãng cấp. Kiểm tra bằng `frappe.db.count("File") > 0`. |
| `Pending Site Handover` | Bắt buộc phải ký điện tử chữ ký của Trưởng khoa và đại diện nhận hàng (BM01.01.03). |
| `Installing` | Bắt buộc đính kèm File Ảnh `JPG/PNG` chân thực của mặt bằng thi công & Lỗi phát sinh (nếu có). |

---

## 5. Compliance Rules (Quy tắc tuân thủ pháp lý)

- **Mandatory Requirements:**
  - CO/CQ là giấy tờ pháp lý tối thượng của thiết bị y tế nhập khẩu. Không thỏa hiệp (Không bao giờ gỡ code Required).
- **Optional Requirements:**
  - Tư vấn giám sát: Optional. Nếu Field `Tư vấn giám sát` bị None/Null -> Ẩn toàn bộ Form lấy chữ ký/Duyệt của đối tượng này ra khỏi luồng (System Logic: `eval: doc.supervisor`).

---

## 6. Exception Handling (Xử lý các ca bất thường)

- Nếu Biên bản nghiệm thu lắp đặt bị trễ (Quá thời hạn hẹn của Vendor):
  - **Logic:** `Trigger Daily Scheduled Job`
  - Nếu `cur_date > expected_end_date` MÀ `status = "Installing"`: Gửi mail khiếu nại Escalation tới Giám đốc Sale của Vendor (Tự fetch theo field Address Email).
- Nếu Máy hỏng/rơi vỡ ngay trong quá trình Bàn giao chân công trình:
  - Nút chuyển hướng (Rework Route): `Return to Vendor`. Cập nhật tự động thẻ Item về kho Tạm giữ & sinh ra cảnh báo trên Asset module.

---

## 7. Audit Requirements (Truy xuất nguồn gốc & Audit log)

Hệ thống AssetCore bắt buộc phải thực thi Audit:
- **What is logged:**
  - `owner` (Người tạo form) và `ip_address` thực tế tạo ra đơn từ mạng ngoài hay mạn LAN viện.
  - `% Tracking`: Toàn bộ các thay đổi trên `Document Checklist Table` (Ngày 1: Check không có CQ -> Ngày 2: Sửa lại thành Đã có CQ). Phải ghi log lại Version 1 và Version 2. Cấm thao tác Xóa (Delete) các record table bằng lệnh cứng, chỉ có trạng thái (Cancel).
- Data Timestamp phải dùng `frappe.utils.now()` từ Server để tránh Kỹ sư chỉnh thời gian local trên máy tính lách luật SLA.

---

## 8. Risk points and Control points

| Risk (Rủi ro quy trình) | Control System Logic (Tầm soát Hệ thống) |
|---|---|
| Kỹ sư bỏ qua checklist điện, nhắm mắt tick "Đạt" và lắp máy gỡ cháy | **Hạn chế:** Hệ thống yêu cầu chụp ảnh Bảng điện/Dòng đo đính kèm vào đúng hàng rào Checklist `Điện` đó. Nếu thiếu ảnh, văng `Soft Validation`. |
| Hãng đưa máy trôi nổi, sai Serial Number báo phế | **Hard Code Barcode:** Khi máy quét Serial bằng Barcode Scanner tại cửa Handover, đối chiếu qua string API `Item Model`. Khác ID định dạng -> Bấm còi báo lỗi `Invalid SN Form`. |
| Trưởng phòng bận, giam chờ duyệt quá lâu | Tự động sinh `Assignment` vào luồng Notification ERPNext của Role `TBYT_Manager`. Đóng dấu "SLA: 24hrs". Quá hạn chuyển đỏ. |
