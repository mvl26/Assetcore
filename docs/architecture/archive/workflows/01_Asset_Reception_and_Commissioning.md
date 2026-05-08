# Workflow Design: Asset Reception & Commissioning

**Phân hệ:** AssetCore (ERPNext)
**Tiến trình:** Procurement → Deployment (Tiếp nhận → Lập kế hoạch lắp đặt → Chạy thử → Đào tạo)
**Căn cứ:** SOP từ `SOP_ALL.md` (BM01.01.01 đến BM01.03.01)

Kiến trúc DocType: Sử dụng 1 DocType CORE `Asset Commissioning Process` làm bộ khung quản lý xuyên suốt, tích hợp các child data.

---

## 1. Workflow States (Các trạng thái)

| Trạng thái | Thuộc tính | Ý nghĩa |
|---|---|---|
| **Draft** | Atomic | Lập kế hoạch tiếp nhận tài sản từ Hợp đồng/PO. Đang chờ phê duyệt để tiến hành. |
| **Pending Document Review** | Atomic | Cán bộ TBYT/HCQT kiểm tra danh mục Hồ sơ/Tài liệu đi kèm (CO, CQ, manual...). |
| **Pending Site Handover** | Atomic | Bàn giao hàng hóa về chân công trình. Kiểm tra ngoại quan, số lượng thiết bị. |
| **Pending Site Preparation** | Atomic | Kiểm tra điều kiện lắp đặt (điện, nước, khí, không gian, chống nhiễu...). |
| **Installing & Commissioning** | Atomic | Kỹ sư hãng tiến hành lắp đặt, chạy thử. Ghi chép nhật ký, thông số đo kiểm. |
| **Pending Training** | Atomic | Hệ thống vận hành tốt, tiến hành lập kế hoạch và đào tạo người sử dụng. |
| **Completed** | Final | Chu trình hoàn thành. Tài sản chính thức "Active" trong hệ thống ERPNext. |
| **Rejected** | Terminal | Hàng hóa không đạt chất lượng/chứng từ sai lệnh nặng. Trả về NCC. |
| **Rework** | Transient | Đánh dấu cần khắc phục/bổ sung (giấy tờ, linh kiện) ở bất kỳ khâu nào. |

---

## 2. State Machine (Bảng chuyển đổi trạng thái)

| Từ Trạng thái (From) | Đến Trạng thái (To) | Hành động kích hoạt (Action) | Vai trò thực hiện (Role) | Căn cứ biểu mẫu SOP |
|---|---|---|---|---|
| `Draft` | `Pending Document Review` | Submit Plan | HCQT / TBYT | BM01.01.01 |
| `Pending Document Review` | `Pending Site Handover` | Verify Documents | HCQT / TBYT | BM01.01.02 |
| `Pending Document Review` | `Rework` | Request Missing Docs | HCQT / TBYT | |
| `Pending Site Handover` | `Pending Site Preparation` | Handover Confirmed | User Dept, Supervisor | BM01.01.03 |
| `Pending Site Handover` | `Rejected` | Reject (Hỏng, thiếu nặng) | HCQT, TBYT, Hội đồng | |
| `Pending Site Preparation` | `Installing & Commissioning` | Conditions Met | User Dept, HCQT | BM01.02.01 & BM01.02.02 |
| `Installing & Commissioning` | `Pending Training` | Commissioning Passed | TBYT, NGOẠI(NCC) | BM01.02.03 & BM01.02.04 |
| `Installing & Commissioning` | `Rework` | Commissioning Failed | TBYT | |
| `Pending Training` | `Completed` | Training Done | User Dept | BM01.03.01 |
| `Rework` | `Pending Document Review` / v.v. | Re-Submit | NCC (Vendor) | (Tuỳ vào khâu lỗi) |

---

## 3. DocType Design (Thiết kế Dữ liệu & Quan hệ)

### 3.1. DocType chính: `Asset Commissioning Process`
**Loại:** Submittable DocType.
- `naming_series`: `ACP-.YYYY.-.#####`
- `reference_po`: Link(Purchase Order)
- `contract_no`: Data
- `vendor`: Link(Supplier)
- `target_department`: Link(Department)
- `supervisor_company`: Link(Supplier) - *Tư vấn giám sát (nếu có)*
- `workflow_state`: Link(Workflow State) - Hiện trạng tiến trình
- Mảng thông tin đánh giá tổng thể (Tổng kết quá trình chạy thử).

### 3.2. Child Tables (Bảng con)
Thay vì tạo quá nhiều DocType độc lập sinh rác hệ thống, chúng ta lưu trữ dạng Child-table trực thuộc quá trình:
1. **`Asset Commissioning Document` (BM01.01.02)**: Tài liệu pháp lý, CO, CQ, HDSD (Có/Không, links file).
2. **`Asset Commissioning Item` (BM01.01.03)**: Danh mục thiết bị (Item Code, Model, Serial, Qty, Ghi chú ngoại quan).
3. **`Asset Installation Condition` (BM01.02.02)**: Bảng kiểm các điều kiện lắp (Điện, nước, khí gốc...).
4. **`Asset Commissioning Log` (BM01.02.03/04)**: Nhật ký công việc và thông số thiết kế / đo kiểm thực tế. Đánh giá Đạt/Không đạt theo từng thông số.

---

## 4. Event Model (Mô hình Sự kiện)

- **On PO Submit**: Tự động webhook hoặc Server Script sinh 01 bản ghi `Asset Commissioning Process` gán với Vendor và PO đó, trạng thái `Draft`.
- **On State `Pending Site Preparation`**: Trigger cấp phát Asset Tag (Mã tài sản cố định/Barcode) trong bảng Asset của ERPNext với trạng thái `In transit` / `Draft`. (Thiết bị đã chính thức đổ bộ).
- **On State `Completed`**: Kích hoạt Status của bản ghi ERPNext Asset tương ứng thành `Submitted` / `Active`. Cập nhật `Available for Use Date`.

---

## 5. Permission Matrix (Ma trận Phân quyền)

| Role (Vai trò hệ thống) | Quyền trên DocType | Phạm vi truy cập trạng thái |
|---|---|---|
| **System Manager** | Read, Write, Submit, Cancel | Full Access |
| **Asset Manager (TBYT/HCQT)** | Read, Write, Submit | Được quyền kích hoạt chuyển tất cả các trạng thái từ `Draft` -> `Training`. |
| **Asset User (Khoa, Phòng)** | Read, (Hạn chế Write) | Chỉ được xác nhận ở các trạng thái `Site Preparation` và `Training`. |
| **Vendor / Tư vấn GS** (Guest) | Read, Write (Qua Web Portal) | Chỉ update File/Log tại `Installing & Commissioning`, hoặc Upload tài liệu lúc `Pending Document Review`. |

---

## 6. Validation Rules (Quy tắc kiểm tra hợp lệ)

1. **Document Validation**: Nếu chuyển sang `Pending Site Handover`, code Frappe sẽ đếm toàn bộ dòng trong bảng child `Document` bắt buộc. Nếu `is_mandatory=1` mà chưa tick `status="Đạt"` hoặc không có file đính kèm -> Throw Error.
2. **Serial Number Requirement**: Khi kết thúc `Pending Site Handover`, 100% các mặt hàng phải có khai báo Serial Number.
3. **Commissioning Protocol**: Chuyển từ `Installing & Commissioning` sang bước tiếp theo bắt buộc phải có chữ ký scan/ đính kèm PDF của "Biên bản chạy thử" (BM01.02.04).
4. **QMS QA Validation**: Với các thiết bị X-Quang, CT, MRT, khi Commissioning bắt buộc phải đính kèm chứng chỉ đo lường/Bức xạ an toàn điện. Không có -> Throw Error.

---

## 7. API / Giao tiếp sự kiện hệ thống (System Events)

- Giao tiếp với **ERPNext Asset Module**:
  - `frappe.get_doc("Asset")`: Xây dựng các records Asset tự động.
  - Tự động map `Item Code`, `Serial Number` từ quá trình `Asset Commissioning Process` sang `Asset`.
- Giao tiếp với **QMS Module** (Nếu có): Cập nhật Checklist audit log sang module Quản lý Chất lượng.

---

## 8. QMS Controls (Kiểm soát chất lượng & Audit)

- **Audit Trail**: Hệ thống tự động ghi nhận Timestamp (người duyệt, thời điểm) cho từng nút chuyển trạng thái của State Machine. Mọi thao tác đều không được phép ghi đè (Append Only Log trên Timeline ERPNext).
- **Approval Checklists**:
  - BM01.01.02 (Bảng kiểm hồ sơ) là checklist bắt buộc để unlock Node 2.
  - BM01.02.02 (Bảng kiểm điều kiện) là checklist bắt buộc để unlock Node 4.
- **SLA**:
  - Document Review: Max 03 ngày làm việc.
  - Commissioning: Theo kế hoạch tại chi tiết ngày từ `Asset Commissioning Plan`, quá thời hạn sẽ push thông báo "Overdue" vào dashboard ban Giám Đốc.
