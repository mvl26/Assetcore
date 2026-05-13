# Thiết kế Data & Logic: IMM-04 (Installation & Initial Inspection)

Tài liệu này dịch ngược các vòng luân chuyển trạng thái thành cấu trúc siêu dữ liệu (DocType, Field, Automation & Permission) phục vụ việc lập trình trực tiếp trên ERPNext/Frappe.

---

## A. Danh sách DocType

1. Tận dụng Core ERPNext **Asset** (Dữ liệu chủ / Master Data): Chỉnh sửa form có sẵn, thêm các trường (fields) kỹ thuật và ID đa lớp.
2. Tận dụng Core ERPNext **Item** (Dữ liệu chủ): Kế thừa danh mục mã máy hãng.
3. Tạo mới Custom **Asset Commissioning Process** (Dữ liệu quản trị QMS): DocType mẹ Submittable ôm trọn luồng quy trình IMM-04.
4. Tạo mới Custom Child Table **Asset Commissioning Document** (Dữ liệu QMS): Bảng lưu giấy tờ đi kèm.
5. Tạo mới Custom Child Table **Baseline Test Result** (Dữ liệu QMS): Bảng lưu kết quả đo đạc an toàn điện/dòng, làm Baseline đối sánh.

---

## B. Bảng field chi tiết (Đặc tả các DocType trọng tâm)

### 1. Custom DocType: `Asset Commissioning Process`
*Vai trò:* Neo giữ toàn bộ quá trình IMM_04. Khóa traceability từ PO tới Asset.

| Fieldname | Label | Kiểu Field | Bắt buộc? | Mô tả (Dữ liệu/Luồng) | Nguồn dữ liệu | Editable ở State |
|---|---|---|---|---|---|---|
| `workflow_state` | Trạng thái luồng | Link | Có | Giữ hệ thống State Machine IMM-04 | Kế thừa Frappe | System Admin |
| `master_item` | Model Thiết bị gốc | Link(Item) | Có | Để trích xuất thông số hãng | Kéo từ PO | `Draft` đến `Pending_Doc_Verify` |
| `po_reference` | Lệnh mua hàng gốc | Link | Không | Traceability khâu Procurement | Kéo từ ERP | `Draft` đến `Pending_Doc_Verify` |
| `vendor` | Nhà cung cấp | Link | Có | Link tới Vendor Tech ráp máy | ERP Supplier | `Draft` đến `Pending_Doc_Verify` |
| `installation_date` | Ngày giờ thi công | Datetime | Có | Cắt băng giờ bắt vít/kéo cáp | User nhập | `To_Be_Installed`, `Installing` |
| `DOA_incident` | Ghi nhận DOA hỏng | Check | Không | Tích vào nếu khui tủ ra đã hỏng | User tick | `Installing` |
| `clinical_dept` | Khoa lâm sàng | Link(Dept) | Có | Khoa sẽ là chủ nhà nhận máy | User chọn | `Draft` |
| `target_asset` | Mã Tài sản Sinh ra | Link(Asset) | Không | **Khóa Traceability vĩnh viễn** | API sinh ra | Chỉ System lúc `Clinical_Release` |

### 2. Custom Child-Table: `Baseline Test Result`
*Vai trò:* Lưu trữ chỉ số khám sức khỏe lần đầu của máy.

| Fieldname | Label | Kiểu Field | Bắt buộc? | Mô tả (Dữ liệu/Luồng) | Nguồn dữ liệu | Editable ở State |
|---|---|---|---|---|---|---|
| `parameter_name` | Tiêu chí test | Data | Có | VD: "Dòng điện dò rỉ", "Chìa khóa an toàn" | Template gốc | `Initial_Inspection` |
| `measured_value` | Số đo thực tế | Float | Không | 1.5, 2.0... (Ghi log baseline) | Máy đo Analyzer| `Initial_Inspection` |
| `is_pass` | Đạt chuẩn QA | Select | Có | Pass/Fail. Nếu có 1 Fail = Máy chết. | Kỹ sư đánh giá| `Initial_Inspection` |

### 3. Core OVERRIDE: `Asset` (Gắn thêm kỹ thuật vào Frappe gốc)
*Vai trò:* Master Data hoàn chỉnh cho Y tế, sở hữu ID đa lớp.

| Fieldname | Label | Kiểu Field | Bắt buộc? | Mô tả | Nguồn dữ liệu | Editable ở State |
|---|---|---|---|---|---|---|
| `custom_qr_internal` | Mã QR Bệnh viện | Data | Có | Lớp giáp 1 (Khóa định danh nội bộ) | Sinh Tự Động | `Identification` (lúc Commissioning)|
| `custom_sn_vendor` | Serial Number NSX | Data | Có | Lớp giáp 2 (Do hãng cung cấp) | Nhập từ Tem thùng| `Identification` |
| `custom_moh_code` | Mã chuẩn BYT | Data | Không| Lớp giáp 3 (Thống kê quốc gia) | User nhập | Mọi lúc |
| `custom_is_radiation`| Bức xạ tia X | Check | Không| Trigger để mở cổng Hold Gate | Map từ Item form | Khóa vĩnh viễn |
| `custom_commissioning_ref`| Link về Form test | Link | Có | **Khóa Traceability ngược về QMS**| API Gán giá trị | Chỉ System lúc `Clinical_Release` |

---

## C. Mapping DocType ↔ State (Chiến lược hiển thị phân đoạn)

Toàn bộ các Field sẽ KHÔNG hiển thị 100% cùng lúc làm rối mắt kỹ sư. 
- Tại State `Draft` & `Pending_Doc_Verify`: Chỉ form nhập Hồ sơ hiển thị (Section 1).
- Chuyển sang State `Installing`: Section Hồ sơ khóa cứng Read-Only. Mở ra Section `Nhật ký thi công lắp đặt` (Hiển thị field `installation_date`, `DOA_incident`).
- Chuyển sang State `Identification`: Mở ra block ID đa lớp.
- Chuyển sang State `Initial_Inspection`: Lưới Grid (Bảng con) `Baseline Test Result` nảy ra bắt nhập chỉ số điện.

---

## D. Permission Matrix sơ bộ (Matrix Role-based)

Trên DocType lõi `Asset Commissioning Process`:

| Quyền hạn | Role (Nghiệp vụ thực) | Read | Write | Submit | Quyền đổi State |
|---|---|---|---|---|---|
| Giao nhận / Thẩm tra | `TBYT Officer` (Nhân viên TBYT) | Yes | Yes (Giới hạn Node 1-3) | No | Được phép nhảy node 1 đến 3. |
| Test kỹ thuật | `Biomed Engineer` (Kỹ sư y sinh)| Yes | Yes (Giới hạn Node 3-6) | No | Điền Test Baseline, chuyển Release hụt, báo DOA. |
| Phê chuẩn pháp lý | `QA Officer` (Cục, Pháp chế) | Yes | No | No | Gỡ trói node `Clinical_Hold` (Nếu máy XQuang). |
| Ký nghiệm thu | `Board/Clinical Head` (Giám đốc) | Yes | No | Yes | Được phép Submit nút `Clinical_Release` (Terminal State đóng băng Data). |
| Trả hàng | `Vendor` (Outside portal) | Yes | Read-Only | No | Chỉ nhìn thấy comment nếu bị cấm. |

---

## E. Validation Rules sơ bộ (Bộ lọc Frappe Backend)

- `Rule 1` **(Chặn Duplicate ID):** Tại State `Identification`, Event Save (Validate): 
  - `if frappe.db.exists("Asset", {"custom_sn_vendor": doc.vendor_sn}): frappe.throw("Serial Number này đã bị nhập ảo vào máy khác trên Server!")`.
- `Rule 2` **(Lưới cản Baseline):** Chặn nhấn nút Tới tại `Initial_Inspection`: 
  - `if (child.is_pass == "Fail" cho bất kỳ child trong doc.baseline_tests): frappe.throw("Không thể duyệt! Máy trượt bài kiểm tra an toàn.") -> Force State về Clinical Hold.`
- `Rule 3` **(Thiết bị rủi ro cao):** Tại thời khắc `Initial_Inspection`:
  - `if doc.is_radiation == True MÀ doc.qa_approval == None`: Lập tức đá luồng qua nhánh `Clinical_Hold` tự động.

---

## F. API / Automation trigger sơ bộ

1. **Trigger Tự sinh `Asset` (Nòng cốt):**
   - **Móc sự kiện:** Khi DocType này Submit (chạm mốc `Clinical_Release_Success`).
   - **Hành động Python Backend:** 
     `new_asset = frappe.new_doc("Asset")`
     Copy toàn bộ ID Mutil-layer, Serial, Model, và Trạng thái Set là `status = "In Use"`. Ghi lưu vào SQL. Tự động trả về cái `asset_id` ngược lại vào file Commissioning (Cột `target_asset`) để đóng vòng Traceability khóa chặt hai chiều.
2. **Trigger Xóa Rác PO (Garbage Error Handling):**
   - **Móc sự kiện:** Khi Trạng thái là `Return_to_Vendor`.
   - **Hành động:** Gọi API `frappe.db.set_value("Purchase Order", po, "status", "Cancelled")` nếu PO chưa hạch toán. Chặn tiền cọc dính chấu. 
3. **Webhook Bắn Notification:**
   - **Móc sự kiện:** Nhảy State `Clinical_Hold` (quá 2 ngày).
   - **Hành động:** Payload Post vào URL Zalo ZNS API gửi ban giám đốc: *"Máy MRI phòng số 1 đang bị kẹp chân lỗi chưa có giấy phép đo lường."*
