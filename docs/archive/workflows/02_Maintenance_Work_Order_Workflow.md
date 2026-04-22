# Workflow Design: CMMS - Maintenance Work Order (Quy trình Quản lý Bảo trì và Báo hỏng)

**Phân hệ:** AssetCore (ERPNext CMMS)
**Tiến trình:** Operation → Maintenance 
**Căn cứ:** Dựa trên chuẩn "WHO - Computerized maintenance management system"
**Đối tượng:** Các công tác sửa chữa đột xuất (Báo hỏng / Corrective Maintenance) và Bảo trì dự phòng (Preventive Maintenance).

Kiến trúc DocType: 
Sử dụng DocType `Maintenance Work Order`.

---

## 1. Workflow States (Các trạng thái)

| Trạng thái | Thuộc tính | Ý nghĩa |
|---|---|---|
| **Draft / Reported** | Atomic | Khởi tạo sự cố (Báo hỏng) hoặc lệnh bảo trì định kỳ tự động. Đang chờ Phòng TBYT tiếp nhận. |
| **Assigned** | Atomic | Lãnh đạo Phòng TBYT đã phân công kỹ sư phụ trách / Hoặc kỹ sư tự tiếp nhận. |
| **In Progress** | Atomic | Kỹ sư đang thực hiện việc kiểm tra, sửa chữa hoặc bảo trì. |
| **Pending Spares** | Atomic | Tạm dừng: Cần thay thế vật tư/linh kiện nhưng kho không có sẵn, cần làm lệnh mua. |
| **Pending Vendor** | Atomic | Tạm dừng: Lỗi vượt khả năng nội bộ, cần chờ chuyên gia của Hãng/Nhà thầu ngoài vào xử lý. |
| **Completed** | Final | Sự cố đã khắc phục xong. Thiết bị hoạt động tốt. Khoa sử dụng đã nghiệm thu. |
| **Cannot Repair / Decommission**| Terminal | Thiết bị hỏng nặng, linh kiện 단 chủng, hoặc chi phí vượt quá giới hạn. Đề xuất Thanh lý. |
| **Rejected** | Terminal | Báo hỏng sai, hoặc yêu cầu không hợp lệ. Hủy phiếu. |

---

## 2. State Machine (Bảng chuyển đổi trạng thái)

| Từ Trạng thái (From) | Đến Trạng thái (To) | Hành động kích hoạt (Action) | Vai trò thực hiện (Role) |
|---|---|---|---|
| `Draft / Reported` | `Assigned` | Assign (Giao việc) | TBYT Manager |
| `Assigned` | `In Progress` | Start Work (Bắt đầu) | TBYT Technician |
| `In Progress` | `Completed` | Fix & Confirm (Nghiệm thu) | TBYT Technician / User |
| `In Progress` | `Pending Spares` | Check Spares (Thiếu đồ) | TBYT Technician |
| `In Progress` | `Pending Vendor` | Call Vendor (Gọi hãng) | TBYT Manager / Technician |
| `In Progress` | `Cannot Repair` | Propose Decom (Xin thanh lý)| TBYT Manager |
| `Pending Spares` | `In Progress` | Spares Received (Đã có đồ)| TBYT Technician |
| `Pending Vendor` | `Completed` | Vendor Fixed (Hãng sửa xong)| TBYT Manager |
| `Reported / Assigned`| `Rejected` | Reject (Hủy yêu cầu) | TBYT Manager |

---

## 3. DocType Design (Thiết kế Dữ liệu & Quan hệ)

### 3.1. DocType chính: `Maintenance Work Order`
**Loại:** Submittable DocType.
- `naming_series`: `WO-.YYYY.-.#####`
- `maintenance_type`: Select (Corrective / Preventive / Calibration)
- `asset`: Link(Asset) - Thiết bị cần xử lý.
- `reported_by`: Link(User) -> Khoa phòng.
- `assigned_to`: Link(User) -> Kỹ sư phụ trách.
- `failure_description`: Text (Mô tả lỗi hoặc hiện tượng).
- `maintenance_status`: Link(Workflow State).
- `down_time_hours`: Float (Tính toán số giờ ngưng hoạt động đo đếm thực tế).

### 3.2. Child Tables (Bảng con)
1. **`Work Order Tasks`**: Danh sách checklist công việc bảo trì (Rất quan trọng với Preventive Maintenance theo manual NSX). Phải tick hoàn thành từng bước.
2. **`Work Order Spares Usage`**: Link tới bảng Vật tư (Item). Khi chọn và submit, hệ thống xuất kho trừ lượng linh kiện tương ứng.
3. **`Work Order Timesheet`**: Nhật ký thời gian nhân công (Kỹ sư A làm 3 tiếng, ngày x... để tính chi phí sửa chữa).

---

## 4. Event Model & API (Mô hình Sự kiện)

- **On Create (PM)**: Scheduled Job hàng ngày của ERPNext sẽ quét bảng `Maintenance Schedule` của từng tài sản. Nếu Asset (Tiêm truyền, MRI) đến hạn PM (vd: trước N ngày), sinh tự động WO trạng thái `Reported`, send email tới Phòng TBYT.
- **On State `Reported`**: Kích hoạt việc đổi trạng thái của bản ghi Asset gốc (Equipment) từ `Active` sang `Out of Order` hoặc `Under Maintenance` (Cảnh báo các khoa không sử dụng thiết bị).
- **On State `Pending Spares`**: Tự động sinh `Material Request` (Phiếu yêu cầu mua/rút vật tư) có Reference tới WO này.
- **On State `Completed`**: 
   - Đưa trạng thái Asset trở lại `Active`.
   - Tính toán và cộng dồn chi phí `Cost` (gồm linh kiện + nhân công) vào thẻ Tài sản để tính Total Cost of Ownership (TCO).

---

## 5. Permission Matrix (Ma trận Phân quyền)

| Role (Vai trò hệ thống) | Quyền trên DocType | Ghi chú |
|---|---|---|
| **System Manager** | Full Access | |
| **Asset Manager (TBYT)**| Read, Write, Submit, Assign| Được phép Approve, chuyển tới Pending Vendor hoặc Decommission.|
| **Asset Technician** | Read, Write | Update Logs, Parts, Start Work, xin chuyển sang Pending Spares. |
| **Asset User (Điều dưỡng)** | Create, Read | Gửi Report (Báo hỏng) qua Portal, View State để biết máy đang sửa tới đâu.|

---

## 6. Validation Rules (Quy tắc kiểm tra hợp lệ)

1. **Resolution Mandatory**: Trước khi ấn nút `Completed`, kỹ sư BẮT BUỘC phải điền trường `Resolution / Action Taken` (Chi tiết cách khắc phục). Phương thức này giúp QA kiểm soát và AI sau này học được Knowledge Base.
2. **Spares Validation**: Không thể đưa linh kiện vào `Spares Usage` nếu mặt hàng đó không đủ số lượng trong kho (Ngoại trừ việc tích hợp với Purchase Receipt ngay tại thời điểm).
3. **Approval Validation**: Nếu TBYT đánh dấu WO là `Cannot Repair / Decommission`, hệ thống bắt buộc bắt đính kèm file "Báo cáo đánh giá kỹ thuật lỗi nội bộ".

---

## 7. QMS Controls (Kiểm soát chất lượng & Audit)

- **Audit Log/Trail**:
  - Đo thời gian Reaction Time: Khoảng cách từ `Reported` tới `Assigned` (SLA: < 2 giờ).
  - Đo thời gian Downtime / Repair Time: Khoảng cách từ `Reported` tới `Completed`.
- Nếu Mean Time to Repair (MTTR) lố hạn của SLA, thẻ ghi sẽ hiện màu Đỏ (Overdue) đập vào mắt Trưởng phòng.
- **Vendor Tracking**: Khi gọi `Pending Vendor`, QMS sẽ đo thời gian phản hồi của nhà cung cấp. Điều này phục vụ chỉ tiêu chấm điểm nhà cung cấp cuối năm.
