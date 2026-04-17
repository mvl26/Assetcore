# Data Model: CMMS Maintenance Work Order (Quản lý Bảo trì và Báo hỏng)

Dựa trên tài liệu Workflow `02_Maintenance_Work_Order_Workflow.md` vừa được xây dựng, tôi thiết kế tiếp mô hình cấu trúc dữ liệu Data Model trên hệ thống ERPNext/Frappe.

## 1. Main DocType: `Maintenance Work Order`
- **Module:** AssetCore / CMMS
- **DocType Type:** Submittable (Có submit state)
- **Naming Rule:** Biểu thức ngẫu nhiên hỗn hợp hậu tố `WO-.YYYY.-.#####`
- **Track Changes:** `Yes` (Kích hoạt Audit Trail tự động của Frappe)
- **Track Views:** `Yes`

### Field List (Bảng thông tin chính)

| Fieldname | Label | Type | Req | Description | Status Mapping |
|---|---|---|---|---|---|
| `workflow_state` | Trạng thái luồng | Link (Workflow State)| Yes | Map chặt với luồng CMMS | Bắt buộc mọi state |
| `maintenance_type` | Loại công việc | Select | Yes | Các giá trị: Khắc phục sự cố (Corrective), Bảo trì dự phòng (Preventive), Kiểm định (Calibration) | `Reported` / `Draft` |
| `asset` | Mã thiết bị | Link (Asset) | Yes | Chọn thẻ Tài sản/Equipment đang bị lỗi | Tất cả báo cáo |
| `reported_by` | Người yêu cầu | Link (User) | Yes | Nhân viên y tế/Điều dưỡng báo hỏng | Lúc Submit |
| `assigned_to` | Kỹ sư xử lý | Link (User) | No | Phân công sửa chữa (Assigned) | Bắt buộc tại `Assigned` |
| `failure_desc` | Mô tả sự cố | Small Text | Yes | Triệu chứng gặp phải do người dùng mô tả | `Reported` |
| `breakdown_date` | Giờ báo hỏng | Datetime | Yes | Timestamp sinh ra tự động để tính SLA | Khởi tạo |
| `completion_date` | Giờ nghiệm thu | Datetime | No | Tự động điền ngày giờ khi Completed | Tại `Completed` |
| `downtime_hours` | Thời gian ngưng | Float | No | Field dạng Read Only tính bằng công thức `completion - breakdown` (Trừ đi khoảng thời gian pending linh kiện) | |
| `resolution` | Cách khắc phục | Text | No | Log lịch sử để AI/Kỹ sư học tập | Bắt buộc tại `Completed` |

## 2. Child Tables

Đi sâu vào module Work Order để thực thi các nghiệp vụ bảo trì, ta cần các bảng con:

### Child 1: `Work Order Tasks` (Biểu mẫu Checklist bảo trì)
- Rất quan trọng đối với Preventive Maintenance để đảm bảo các bước (VD: tra dầu, đo rò rỉ điện, thổi bụi... được thực hiện đầy đủ).
| Fieldname | Label | Type | Req | Description |
|---|---|---|---|---|
| `task_description` | Nội dung Checklist | Text | Yes | Mô tả công việc kéo từ Schedule gốc |
| `is_completed` | Đạt | Check | No | Kỹ sư tick tay |
| `task_result` | Chỉ số đo được | Data | No | Nếu yêu cầu điền thông số kV/mA... |

### Child 2: `Work Order Spares Usage` (Quản lý Linh kiện/Vật tư)
- Giao tiếp cực mạnh với module Stock (Kho Bệnh viện).
| Fieldname | Label | Type | Req | Description |
|---|---|---|---|---|
| `item_code` | Vật tư/Linh kiện | Link (Item) | Yes | Mã linh kiện cần thu/xuất |
| `qty` | Số lượng | Float | Yes | |
| `warehouse` | Chuyển từ Kho | Link (Warehouse)| Yes | Mặc định xuất từ kho Kỹ thuật TBYT |
| `actual_cost` | Chi phí linh kiện | Currency | No | Read/Only lấy từ giá vốn của Item |

## 3. Relationships & Traceability

1. **Link to Asset (Truy xuất vòng đời thiết bị):** Khi kỹ sư/người quản lý mở tab `Maintenance` trên bất kỳ DocType Asset nào, hệ thống phải list toàn bộ các `Maintenance Work Order` có `Asset = Item gốc` đó. Từ đó tính ra TCO (Total Cost of Ownership).
2. **Link to Vendor/Contract:** Một số thiết bị có Hợp đồng bảo trì toàn vẹn dữ liệu (Full-service contract). Ta móc `contract_no` = Link (Purchase Receipt / Contract). Hệ thống sẽ Check Box nếu Hợp đồng còn hiệu lực `is_under_warranty` để không tính phí nội bộ.
3. **Materials Integration:** Khi Submit phiếu WO mà Child Table `Spares Usage` có dữ liệu -> Bắn API chạy hàm `frappe.new_doc('Stock Entry')` (Loại Material Issue) để trừ chính xác hệ thống tồn kho kho linh kiện y tế.

## 4. Permission Matrix

| Role | Read | Write | Submit | Approve/Chuyển Node |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Quản trị viên tối cao. |
| `CMMS Manager` (Trưởng TBYT) | Yes | Yes | Yes | Có quyền chuyển từ TẤT CẢ các state. Ra quyết định cuối `Decommission` hoặc `Pending Vendor`. |
| `CMMS Technician` (Kỹ sư) | Yes | Hạn chế | No | Chỉ edit được các cột Child Table Checklist/Spare Parts và field `Resolution`. Đẩy node về `Pending Spares` hoặc `Completed`. |
| `End User` (Khoa, Điều dưỡng) | Yes | Khởi tạo | No | Đọc để theo dõi tiến độ sửa chữa máy (Track status). Khởi tạo `Reported`. |

---

> [!CAUTION]
> Thiết kế bắt buộc Kỹ sư nhập đầy đủ nội dung mục **Resolution (Cách khắc phục)** có thể gây khó khăn lúc đầu triển khai, nhưng đây là chìa khóa then chốt của QMS và tạo ra ngân hàng Knowledge Base cho Bệnh viện. Không thỏa hiệp tắt trường bắt buộc này.
