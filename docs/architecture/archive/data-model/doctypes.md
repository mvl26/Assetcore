# Bộ Đặc Tả Phát Triển Phần Mềm (DEV SPEC) - Tối đa Hóa (IMM-04)

Tài liệu này dịch chuyển thiết kế thành thông số ERPNext/Frappe thuần túy để Dev có thể config và code mà không cần tư duy lại logic BA.

---

## 1. Cấu hình thực thể (DocType Config)

| Tên Giao Diện (Label)| Tên Technical (`snake_case`) | Module | Submittable? | Workflow Gắn vào | Core / Custom |
|---|---|---|---|---|---|
| Asset Commissioning Process | `asset_commissioning` | `assetcore` | **Yes** | `imm_04_workflow` | Custom Mới |
| Commissioning Checklist | `commissioning_checklist` | `assetcore` | No (Child) | Không | Custom Mới |
| Asset QA Non Conformance | `asset_qa_nc` | `assetcore` | **Yes** | Luồng NC độc lập | Custom Mới |
| Asset | `asset` | `assets` | Yes | Kế thừa Frappe | Mở rộng (Custom Fields)|

---

## 2. Field mapping (Chi tiết Từng Field)

### 2.1 DocType: `asset_commissioning`
Mục tiêu: Quản lý vỏ hộp trạng thái nhập thiết bị y tế.

| `fieldname` | `label` | `fieldtype` | `options` | `reqd` | `read_only` (Theo State) |
|---|---|---|---|---|---|
| `po_reference` | Purchase Order | Link | `Purchase Order` | 1 | Edit ở `Draft`. Read-only từ `Pending_Doc_Verify` trở đi. |
| `master_item` | Model Nhập kho | Link | `Item` | 1 | Edit ở `Draft`. Read-only từ `Pending_Doc_Verify`. |
| `vendor` | Đơn Vị Cung Cấp | Link | `Supplier` | 1 | Edit ở `Draft`. Read-only từ `Pending_Doc_Verify`. |
| `expected_installation_date`| Ngày hẹn Lắp Mặc định | Date | | 1 | Read-only sau `To_Be_Installed`. |
| `installation_date`| Ngày Khởi đọ Lắp ráp | Datetime | | 0 | Chỉ Edit tại `Installing`. Khi `identification` chuyển Date này thành Read-only. |
| `is_radiation_device` | Bức Xạ / Tia X | Check | | 0 | Fetch từ `item.custom_is_radiation`. Read-only 100%. |
| `vendor_serial_no` | Serial Hãng | Data | | 1 | Chỉ Edit ở `Identification`. |
| `internal_tag_qr` | QR Nội bộ BV | Data | | 1 | Chỉ Edit ở `Identification`. |
| `baseline_tests` | Lưới Check điện | Table | `commissioning_checklist`| 1 | Chỉ Write ở `Initial_Inspection`. Khóa khi qua Gate. |
| `qa_license_doc` | Giấy phép BYT/Cục | Attach | | 0 | Bắt buộc đính kèm (Required via JS) khi từ `Clinical_Hold` đi ra. |
| `final_asset` | Asset Đích sinh ra | Link | `Asset` | 0 | `Read Only = 1` mọi lúc mọi nơi. Nhận Value từ Server Hook cấp. |

### 2.2 DocType: `asset_qa_nc` 
Mục tiêu: Lưu trữ phiếu Vỡ hàng DOA độc lập. Đi kèm Timeline Comment chửi thệ Hãng.

| `fieldname` | `label` | `fieldtype` | `options` | `reqd` | `read_only` (Theo State) |
|---|---|---|---|---|---|
| `ref_commissioning` | Móc Về Lệnh Lắp | Link | `asset_commissioning` | 1 | Edit lúc Create. Sau khi Save -> Read-Only. |
| `nc_type` | Loại Biến Cố | Select | DOA\nMissing\nCrash | 1 | Edit lúc Tạo. |
| `damage_proof` | Ảnh Bằng Chứng | Attach Image | | 1 | - |
| `resolution_status` | Trạng thái khắc phục | Select | Open\nFixed\nReturn | 1 | Được phép Edit tới khi Closed. |
| `penalty_amount` | Phạt Hãng | Currency | | 0 | Chỉ Role Ban Lãnh Đạo Nhìn/Edit. |

### 2.3 Core DocType Overlay: Bổ sung trên `Asset`
Sử dụng công cụ `Custom Field` list trong ERPNext để ném thêm vào bảng Asset lõi. Đừng code gộp Core file.

| `fieldname` | `label` | `fieldtype` | `options` | Nguồn Data Đổ Về |
|---|---|---|---|---|
| `custom_vendor_sn` | Serial Sản Xuất | Data | | Copy từ `asset_commissioning.vendor_serial_no` qua API Mint. |
| `custom_internal_qr`| Mã Chống Trộm BV | Data | | Copy từ `asset_commissioning.internal_tag_qr`. |
| `custom_comm_ref` | Truy Vết Khai Sinh | Link | `asset_commissioning`| Đóng ID cái Phiếu đẻ ra tài sản này vào đây để Audit ngược. |

---

## 3. Workflow config (`imm_04_workflow`)

Config hệ thống máy trạng thái (Sử dụng module Workflow list của ERPNext):

| Trạng Thái Đầu (`state`) | `docstatus` | `allow edit` (Role thao tác) | `transition` (Hành động nút bấm) | Tiếp Trạng Thái (`next_state`) | Cảnh báo / Auto Code |
|---|---|---|---|---|---|
| `Draft` | 0 (Saved) | `HTM Technician`| Submit | `Pending_Doc_Verify` | |
| `Pending_Doc_Verify`| 0 | `HTM Technician`| Verify_Pass | `To_Be_Installed` | Kiểm tra thiếu file -> Văng Error. |
| `To_Be_Installed` | 0 | `Vendor` | Start_Work | `Installing` | Chặn nếu Khoa rút phép Tải điện. |
| `Installing` | 0 | `Vendor` | Assemble_Done| `Identification` | Thả ngày lắp đặt Log. |
| `Identification` | 0 | `Biomed Engineer`| Tag_Scanned | `Initial_Inspection` | Chặn Save nếu SN trùng DB. |
| `Initial_Inspection`| 0 | `Biomed Engineer`| Fail_Test | `Re_Inspection` | Bắt buộc ghi Log Fail. |
| `Initial_Inspection`| 0 | `Biomed Engineer`| Release_Pass | `Clinical_Release` | Trigger Script bơm New Asset. |
| `Clinical_Release` | 1 (Submitted)| **Khóa Mọi Nơi** | Cancel | Đẩy sang Trạng thái Hủy hỏng. |

---

## 4. Permission config (Role - Read/Write/Submit)

Bảo mật RBAC tại `Role Permissions Manager` (Frappe Config):

| Role ID (Hệ Thống) | `read` | `write` | `submit` | `cancel` | `amend` | Ghi chú Giới hạn Field (Perm Level) |
|---|---|---|---|---|---|---|
| `HTM Technician` | Y | Y | N | N | N | Level 1: Khóa field Tiền. Không có quyền bấm `Approve` chốt đơn Release. |
| `Workshop Head` | Y | N | Y | Y | Y | Khóa Edit các Field Thô. Quyền rút đơn Cancel DOA. |
| `VP_Block2` | Y | N | Y | Y | N | Thẩm quyền tối cao Ký Duyệt nút Lệnh cuối. |
| `QA_Risk_Team` | Y | Y | N | N | N | Chỉ cho Write tại Upload Giấy phép. |

---

## 5. Server Script / Hook cần viết

Vị trí code: Trỏ vào File `asset_commissioning.py`

- **[validate] (Hook Chặn Rác Input):**
  1. Nếu nhập `vendor_serial_no`: Query SQL vào bảng lõi `Asset`. Trùng SN -> Gọi `frappe.throw("Trùng Serial Hãng")`.
  2. Bắt lưới Đo lỗi: Nếu có 1 hàng Child `test_result` == "Fail" -> Nếu user cố đổi Status -> Gọi Exception Block.

- **[on_submit] (Hook Bắn Tín Hiệu Khởi Tạo Thực Thể Cố Định):**
  Lấy dữ liệu `vendor_serial_no`, `master_item`, `clinical_dept`, Tạo Object Document mới bằng `frappe.get_doc` cho DocType `Asset`. 
  Lưu ý set status bằng `In Use`. 
  Cài đặt `new_asset.insert(ignore_permissions=True)`.
  Chặn Catch Data Error nếu Insert Fails (Ví dụ thiếu Khấu Hao Kế toán).

- **[scheduled_job] (Hook Cron Task):**
  Viết func `check_aging_hold()`. Query lấy các Record có State = `Clinical_Hold` và Tuổi > N ngày. Nếu đúng -> Trigger Email Alert. Ném vào `hooks.py` dòng `scheduler_events: {"daily": [...]}`.

---

## 6. Naming Series (Mã Đếm Format)

- Naming Form File `Asset Commissioning`: `IMM04-.YY.-.MM.-.#####` (Mẫu đếm thời gian).
- Naming Form Bài Thẻ Phạt `Non Conformance`: `DOA-.YY.-.#####` (Báo mã Lỗi đỏ).
- **Lưu ý Code**: Không dùng Naming bằng SN Hãng làm ID (Vì Hãng hay có ký tự đặc biệt lởm khởm như Dấu Gạch/ Dấu Ngã gây gãy Query).

---

## 7. Index / Performance concern

Đưa ra yêu cầu trực tiếp cho Backend Dev:
1. Trong File DocType Mẹ, Field `vendor_serial_no` phải tick Checkbox `Search Index`. Lý do: Lúc quét Barcode rà soát thiết bị trùng trên 1,000,000 máy sẽ ngốn cực lớn tài nguyên RDS. Đánh Index là bắt buộc để B-Tree xử lý nhanh Tích Tắc.
2. Field `workflow_state` Frappe tự sinh Data-Index theo Cấu trúc Frappe default.
3. Không làm Nested Select quá nhiều tầng ở Cột Reference (Tránh làm cháy Page Load Time khi Kế Toán view Lịch Sử PO).
