# Data Model: Asset Commissioning Process (Tiếp nhận & Lắp đặt)

Dựa trên tài liệu Workflow `01_Asset_Reception_and_Commissioning.md`, dưới đây là thiết kế chi tiết cấu trúc bảng dữ liệu (DocType structure) trên nền tảng ERPNext/Frappe.

## 1. Main DocType: `Asset Commissioning Process`
- **Module:** AssetCore
- **DocType Type:** Submittable (Có cơ chế submit giống giao dịch)
- **Naming Rule:** Biểu thức `ACP-.YYYY.-.#####`
- **Track Changes:** `Yes` (Hỗ trợ 100% Audit Trail trên Timeline)
- **Track Views:** `Yes`

### 3. Field List (Bảng thông tin chính)

| Fieldname | Label | Type | Req | Description | Status Mapping (Workflow_state) |
|---|---|---|---|---|---|
| `workflow_state` | Trạng thái luồng | Link (Workflow State) | Yes | Trạng thái hiện tại | Ánh xạ toàn bộ state machine |
| `commissioning_id` | Mã phiên bàn giao | Data | Yes | Autoname tự sinh | Mọi state |
| `po_reference` | Lệnh mua hàng | Link (Purchase Order) | Yes | Tham chiếu gốc quy trình | `Draft` |
| `contract_no` | Số Hợp đồng | Data | No | Tham chiếu điều khoản | `Draft` |
| `supplier` | Nhà cung cấp/Vendor | Link (Supplier) | Yes | Đối tác bàn giao | Mọi state |
| `supervisor` | Tư vấn giám sát | Link (Supplier) | No | Đơn vị GS thứ 3 | Mọi state |
| `receiving_dept` | Khoa phòng nhận | Link (Department) | Yes | Đơn vị sử dụng đầu cuối | `Pending Site Handover` |
| `site_location` | Vị trí lắp đặt | Link (Location) | Yes | Vị trí cụ thể tại viện | `Pending Site Prep` |
| `expected_start_date` | Ngày bắt đầu DK | Date | Yes | Kế hoạch lịch bàn giao | `Draft` |
| `commissioning_end_date` | Ngày kết thúc | Date | No | Ngày chốt bàn giao/Nghiệm thu | `Completed` |
| `final_remarks` | Kết luận đánh giá | Text | No | Đánh giá tổng quan cuối chu trình| `Completed` / `Rejected` |
| `amended_from` | Phiên bản sửa đổi | Link | No | Hỗ trợ hệ thống nếu cần Amend| Trỏ về record nếu huỷ |

## 2. Child Tables

Quy trình phức tạp nên cần lưu trữ thành các Section với nhiều Child Table đính kèm.

### Child 1: `Asset Commissioning Document` (Checklist C/O, C/Q)
- Mảng: Hồ sơ tính pháp lý
| Fieldname | Label | Type | Req | Description |
|---|---|---|---|---|
| `document_type` | Loại Tài liệu | Select (C/O, C/Q, Manual, HDSD...) | Yes | |
| `is_mandatory` | Bắt buộc | Check | No | Nếu tick True, phải có File |
| `status` | Trạng thái nhận | Select (Đạt, Chưa đạt, Không có) | Yes | |
| `attachment` | File đính kèm | Attach / Attach Image | No | Scan bản mềm |

### Child 2: `Asset Commissioning Item` (Kiểm hàng & Lắp đặt)
- Mảng: Hàng hóa thực tế cập bến
| Fieldname | Label | Type | Req | Description |
|---|---|---|---|---|
| `item_code` | Mã Model/Vật tư | Link (Item) | Yes | Tham chiếu Master Item |
| `qty_received` | Số lượng nhận | Float | Yes | |
| `serial_no` | Số Serial (SN) | Data | Yes | Nhập SN cho hệ thống Asset |
| `visual_inspection`| Ngoại quan | Select (Pass, Fail) | Yes | Tình trạng hộp/vỏ máy |
| `generated_asset` | Mã Tài sản đã sinh | Link (Asset) | No | Map ngược về ERP Asset gốc |

### Child 3: `Asset Installation Checklist` (Bảng kiểm điều kiện)
- Mảng: Công tác chuẩn bị hạ tầng điện, nước, phòng óc...
| Fieldname | Label | Type | Req | Description |
|---|---|---|---|---|
| `condition_name` | Hạng mục kiểm tra | Data (VD: Mạng/Điện 3 pha/Khí)| Yes | |
| `is_met` | Đạt yêu cầu | Check | No | |
| `notes` | Chú thích | Text | No | Lỗi thiếu điện/nước... |

## 4. Relationships & Traceability
- **Traceability to Source:** Bản ghi hiện tại móc trực tiếp `po_reference` vào Purchase Order. Khi PO này được thanh toán, kế toán có thể click xem máy cài đặt tới đâu.
- **Traceability to Next Action:** Khi cột `generated_asset` ở Child [Asset Commissioning Item] có giá trị, link này dẫn thẳng vào module Fixed Asset của lõi ERP, mang đầy đủ Serial và Warranty Date thiết lập tại khâu `Completed`.

## 5. Permission Matrix

| Role | Read | Write | Submit | Approve/Transition Nodes |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Full Transitions |
| `Asset Manager` (TBYT) | Yes | Yes | Yes | Tham gia 100% các nút kiểm duyệt. (Document, Handover, Installing). Ký điện tử nút `Completed`. |
| `Asset User` (Trưởng khoa) | Yes | No | No | Chỉ có Action trên nút Xác nhận `Pending Site Handover` & `Pending Training`. |
| `Vendor` (External, Cổng Portal)| Yes | Hạn chế | No | Chỉ Write ở node `Installing` (viết báo cáo) và `Pending Document Review` (Submit form CO CQ). |

---

> [!TIP]
> Việc tạo các trường `workflow_state`, `amended_from` và bật tính năng `Track Changes = 1` bên trong hệ thống Frappe sẽ tự động thỏa mãn nguyên tắc: không ai được quyền xóa dấu vết (Audit Trail). Hệ thống sẽ vĩnh viễn ghi lại "Ai đã chuyển từ Pending Site sang Installing vào ngày giờ nào".
