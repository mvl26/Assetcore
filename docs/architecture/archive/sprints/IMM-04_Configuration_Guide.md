# Hướng dẫn Cấu hình Chi tiết IMM-04 (Step-by-Step Configuration Guide)
# Nền tảng: ERPNext / Frappe Framework

**Dự án:** AssetCore v1.0
**Dành cho:** System Admin / Người dùng triển khai cấu hình
**Mục tiêu:** Tự tay cấu hình luồng IMM-04 từ giao diện UI của ERPNext mà không cần can thiệp code (trừ các Server Script quan trọng liệt kê bên dưới).

---

## 1. HƯỚNG DẪN TẠO DOCTYPE (DATA MODELS)

Sử dụng công cụ **DocType List** (`/app/doctype`) và bấm **Add DocType**.

### Bước 1.1: Tạo Child Table `Commissioning Checklist` (Bảng đo điện)
*Phải tạo Child Table trước để gắn vào bảng mẹ sau.*
- **Name:** Commissioning Checklist
- **Module:** AssetCore
- **Is Table:** ☑️ (Rất quan trọng)
- **Fields:**
  1. `parameter` (Data) - Label: "Thông số / Tiêu chí", In List View: ☑️, Mandatory: ☑️
  2. `measured_val` (Float) - Label: "Giá trị Đo được", In List View: ☑️
  3. `unit` (Data) - Label: "Đơn vị", In List View: ☑️
  4. `test_result` (Select) - Label: "Kết quả", Options: `Pass\nFail`, Mandatory: ☑️
  5. `fail_note` (Text) - Label: "Ghi chú Lỗi"

### Bước 1.2: Tạo DocType mẹ `Asset Commissioning`
- **Name:** Asset Commissioning
- **Module:** AssetCore
- **Is Submittable:** ☑️
- **Track Changes:** ☑️ (Kích hoạt Audit Trail)
- **Track Views:** ☑️
- **Naming Rule:** Expression
- **Auto Name:** `format:IMM04-.YY.-.MM.-.#####`
- **Fields Quan trọng (cấu hình kỹ theo loại):**
  - **Link fields:** `po_reference` (Link → Purchase Order), `master_item` (Link → Item), `vendor` (Link → Supplier), `clinical_dept` (Link → Department). Đánh dấu Mandatory (Bắt buộc).
  - **Read-only fields:** `is_radiation_device` (Check) → Set `fetch_from` = `master_item.custom_is_radiation`. Đánh dấu Read Only.
  - **Barcode field:** `vendor_serial_no` (Data) → Đánh dấu Mandatory. Set `search_index=1`.
  - **Checklist table:** Thêm field `baseline_tests` (Table), Options: `Commissioning Checklist`.
  - **System field:** `final_asset` (Link → Asset), Read Only.
  - **Dependency field:** `amend_reason` (Small Text) → Set `Depends On` = `eval:doc.amended_from`. Đánh dấu Mandatory Depends On (`eval:doc.amended_from`).

### Bước 1.3: Thêm Custom Fields vào thư viện Core
Truy cập **Custom Field** (`/app/custom-field`):
1. **Document:** `Item` | **Fieldname:** `custom_is_radiation` | **Type:** Check | **Label:** Thiết bị có bức xạ.
2. **Document:** `Asset` | **Fieldname:** `custom_vendor_serial` | **Type:** Data | **Label:** Serial Vendor.
3. **Document:** `Asset` | **Fieldname:** `custom_comm_ref` | **Type:** Link (Options: `Asset Commissioning`) | **Label:** Ref IMM04.

---

## 2. HƯỚNG DẪN TẠO WORKFLOW (STATE MACHINE)

Truy cập **Workflow List** (`/app/workflow`) → **Add Workflow**:
- **Name:** `IMM-04 Workflow`
- **Document Type:** `Asset Commissioning`
- **Is Active:** ☑️

### Bước 2.1: Cấu hình States (Các trạng thái)
Thêm vào bảng **States**, gán Doc Status tương ứng (0: Báp nháp/Sửa được, 1: Submit/Khóa, 2: Cancel):
| State | Doc Status | Allow Edit for Role |
|---|---|---|
| Draft | 0 | HTM Technician |
| Pending_Doc_Verify | 0 | HTM Technician |
| To_Be_Installed | 0 | HTM Technician |
| Installing | 0 | HTM Technician |
| Identification | 0 | HTM Technician |
| Initial_Inspection | 0 | Biomed Engineer |
| Re_Inspection | 0 | Biomed Engineer |
| Clinical_Release | 0 | VP Block2 |
| Clinical_Hold | 0 | QA Risk Team |
| Clinical_Release_Success | 1 | (Chỉ xem) |
| Cancelled | 2 | CMMS Admin |

### Bước 2.2: Cấu hình Transitions (Chuyển trạng thái)
Thêm vào bảng **Transitions** (Điều kiện chuyển):
| State From | Action (Label Nút) | State To | Allowed Role |
|---|---|---|---|
| Draft | Gửi Duyệt Hồ Sơ | Pending_Doc_Verify | HTM Technician |
| Pending_Doc_Verify | Duyệt Hồ Sơ Thành Công | To_Be_Installed | HTM Technician |
| To_Be_Installed | Đạt Điều kiện Mặt bằng | Installing | HTM Technician |
| Installing | Hoàn tất Lắp ráp | Identification | HTM Technician |
| Identification | Cấp ID Thành công | Initial_Inspection | HTM Technician |
| Initial_Inspection | Test Pass | Clinical_Release | Biomed Engineer |
| Initial_Inspection | Test Fail | Re_Inspection | Biomed Engineer |
| Re_Inspection | Test Pass Lần 2 | Clinical_Release | Biomed Engineer |
| Clinical_Release | Phê duyệt Phát hành | Clinical_Release_Success | **VP Block2** (Cực quan trọng) |

---

## 3. HƯỚNG DẪN CẤU HÌNH PERMISSION (PHÂN QUYỀN)

### Bước 3.1: Tạo Role
Vào **Role List** (`/app/role`), thêm `HTM Technician`, `Biomed Engineer`, `Workshop Head`, `VP Block2`, `QA Risk Team`, `CMMS Admin`.

### Bước 3.2: Gán quyền theo DocType
Vào **Role Permissions Manager** (`/app/permission-manager`):
- Chọn Document Type: `Asset Commissioning`
- **HTM Technician:** Create: ☑️, Read: ☑️, Write: ☑️. Submit: ❌, Cancel: ❌.
- **VP Block2:** Create: ❌, Read: ☑️, Write: ❌, Submit: ☑️.
- **QA Risk Team:** Create: ❌, Read: ☑️, Write: ❌. Ở Level 0 (toàn bộ field). Tạo quyền Level 1 riêng cho QA để chỉnh `qa_license_doc`.

### Bước 3.3: Khóa tài sản lõi (A7 Critical Fix)
- Chọn Document Type: `Item`
- Bỏ quyền Write của `HTM Technician` với field `custom_is_radiation` (Dùng Property Setter hoặc Level Permission).

---

## 4. HƯỚNG DẪN TẠO VALIDATION (RULE ENGINE)

*Dù cấu hình bằng UI, một số Rule khóa cứng đòi hỏi Server Script (Python). Admin vào máy chủ chạy lệnh cập nhật hoặc import Custom Scripts nếu cho phép.*

### Bước 4.1: Block Release & Bắt buộc Dữ liệu
Logic phải áp dụng vào hàm `validate()` của controller chặn trước khi lưu hoặc Submit.
- **Quy tắc 1 (Bắt buộc Dữ liệu Baseline):** Nếu State = `Initial_Inspection` và `baseline_tests` trống → Ném lỗi `frappe.throw("Không được để trống")`.
- **Quy tắc 2 (Xử lý Fail Baseline - VR03):** Duyệt qua list `baseline_tests`. Nếu có `test_result == 'Fail'` mà `fail_note` rỗng → Block save.
- **Quy tắc 3 (Block Release - VR04):** Khi Transition bấm `Phê duyệt Phát hành`, đếm số record `Asset QA Non Conformance` có `ref_commissioning` là phiếu hiện tại và `status = 'Open'`. Nếu > 0 → Ném lỗi chặn Submit.

---

## 5. HƯỚNG DẪN TẠO AUDIT TRAIL (LOG VÀ TRACEABILITY)

**Log gì, ở đâu?**
1. **Lịch sử sửa đổi Version (Dữ liệu cũ/mới):** 
   - *Cách làm:* Ở bước 1.2, đánh dấu tick `Track Changes` = 1.
   - *Nơi lưu:* Frappe tự lưu ở bảng `Version`. Hiển thị dưới cùng Document trong "Changelog / Timeline".
2. **Lịch sử duyệt (State transitions):**
   - *Cách làm:* Bật Workflow tự động sinh log.
   - *Nơi lưu:* Trong Workflow Action log, hiển thị thẳng ở Timeline (Thấy rõ ai, giờ nào bấm đổi State từ Draft → Installing).
3. **Traceability về Kế toán:** 
   - *Cách làm:* Viết Hook `on_submit` để dùng lệnh `frappe.get_doc({...}).insert()` nhằm tạo `Asset`. Update `doc.final_asset = new_asset.name`.
   - *Nơi lưu:* Link trực tiếp nằm trong giao diện phiếu IMM04, click hyperlink nhảy sang Asset tương ứng chứa QR ID và Barcode.

---

## 6. DANH SÁCH KIỂM TRA (CHECKLIST) VERIFY SAU CONFIG

Sau khi Setup xong, đi theo kịch bản này để Validate. (Check toàn bộ = Pass → Config thành công):

- ☐ **VC-01 (DocType):** Có menu `Asset Commissioning`. Bấm tạo mới hiện giao diện chuẩn. Label tiếng Việt hiển thị chính xác.
- ☐ **VC-02 (ID Config):** Khi Save tạm form, số ID tự động hiển thị dạng `IMM04-26-04-xxxxx`.
- ☐ **VC-03 (Field Dependencies):** Test thử check `amended_from`, kiểm tra field `Lý do Amend` có bật trạng thái bắt buộc đỏ (Red Asterisk) không.
- ☐ **VC-04 (Role Access):** Đăng nhập với User có vai trò `HTM Technician`. Mở Item Máy X-Quang, đảm bảo KHÔNG THỂ thay đổi tick ở dòng "Thiết bị có bức xạ".
- ☐ **VC-05 (Grid Checklist):** Ở lưới Baseline, nhập 1 dòng chọn "Fail". Bấm lưu rỗng ô "Ghi chú". Hệ thống phải BÁO LỖI CHẶN LẠI ngay lập tức.
- ☐ **VC-06 (Workflow Route):** Tạo 1 phiếu giả, bấm thử Action Button. Nút ở State Draft phải là `Gửi Duyệt Hồ Sơ`. Trạng thái chuyển đổi nhịp nhàng.
- ☐ **VC-07 (Permission Gate):** Mở 1 phiếu đã đến cửa `Clinical_Release` bằng Account `HTM Technician`. Đảm bảo KHÔNG CÓ NÚT Approve Phát hành (Chỉ có PTP Khối 2 mới nhìn thấy).
- ☐ **VC-08 (Audit):** Đổi thử số Serial của phiếu Draft, F5 load lại web, kéo xuống dưới cùng để xác nhận Log đã ghi rõ: *"Ông A đổi Serial từ 123 -> 456 lúc 10h00"*.
- ☐ **VC-09 (End-to-end):** Hoàn tất toàn bộ quy trình Submit bằng PTP Khối 2. Sang module Kế toán/Kho (`/app/asset`) tìm thử đúng Serial thiết bị đó xem đã xuất hiện với trạng thái "In Use" hay chưa.

---
*Tài liệu dành cho Technical Configurator. Các vấn đề liên quan Deploy/Python Code không nhắc lại trong bộ Framework setup tự động này.*
