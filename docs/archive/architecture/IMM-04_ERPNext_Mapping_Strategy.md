# Trình chiếu Mapping: ERPNext Core ↔ Custom DocType (IMM-04)

Tài liệu này xác định ranh giới giữa việc "Dùng Đồ Có Sẵn Đầu Tư" (Core Modules) và "Tác Tạo Bản Mới" (Custom DocTypes) để không phá vỡ nhân dữ liệu gốc của ERPNext mà vẫn đạt tiêu chuẩn y tế sâu sắc.

---

## A. Bảng Mapping Core ↔ Custom (Đối chiếu Nghiệp vụ)

| Nghiệp vụ IMM-04 | DocType Lõi ERP (Core) | Custom DocType (Đề xuất) | Phán quyết Thiết kế (Design Decision) |
|---|---|---|---|
| Chứa thông tin Máy chủ | `Asset`, `Item` | (Dùng Core, Extends) | Mọi báo cáo tài chính của thế giới kế toán đều neo vào `Asset`. Bắt buộc phải xài Core. Mở rộng (add custom fields) cho nó. |
| Quản lý vị trí Cài đặt | `Location`, `Department` | (Dùng Core) | Giữ nguyên gốc. Khi luân chuyển sẽ sinh bảng `Asset Movement`. |
| Cập nhật Hồ sơ CO/CQ | `File` / `Attachment` | `Installation_Doc_Record` (Bảng con Custom) | ERPNext có module Quality nhưng làm phẳng. Ta nhúng attachment thẳng vào grid form của luồng Lắp Đặt. |
| Ghi nhận KQ Test dòng | *Không có* | `Asset_Baseline_Test` (Bảng con Custom) | ERPNext không hề có khái niệm đo lường "Baseline" từ lúc xuất xưởng. Buộc phải tạo child table nằm trong phiếu Lắp đặt. |
| Lưu vết quy trình Lắp máy | *`Asset Capitalization`* | `Asset_Commissioning` (Mẹ) | Bảng của ERP quá đơn sơ (chủ yếu ghi giá tiền). Rút tủy thay thế bằng bảng Custom DocType khổng lồ chứa Workflow QMS. |
| Báo cáo máy hỏng DOA | `Quality Inspection` | `Asset_QA_Non_Conformance` | Dùng DocType độc lập để theo dõi vòng đời riêng của rác DOA trả nhà thầu. |

---

## B. Danh sách Field bổ sung (Override) trên lõi `Asset`

Việc tiêm thẳng mũi Kim vào bảng `Asset` của ERPNext là **RỦI RO CAO** vì ảnh hưởng đến nâng cấp Version. Các Extra Field này sẽ được đóng gói bằng phương thức `Custom Field` của Frappe (Nằm lơ lửng ngoài Core codebase):

1. `custom_moh_uuid` (Data): Mã định danh Quốc gia Bộ Y Tế quản lý.
2. `custom_vendor_serial` (Data, Unique): Dãy số NSX in gầm máy. ERPNext có sẵn cột Serial but chúng ta buộc nó Unique.
3. `custom_clinical_risk_class` (Select): Mức A, B, C, D (Tiêu chuẩn MDD). Phục vụ chặn Gate duyệt giá trị cao.
4. `custom_installation_date` (Date): Ngày thực tế hãng lột siêu ghim điện.
5. `custom_commissioning_form` (Link): Cột quan trọng nhất. Giữ chìa khóa FK móc về tờ Phiếu `Asset_Commissioning`.

---

## C. Danh sách Custom DocType cần gò hàn (Tạo mới)

Thay vì xôi hỏng bỏng không, System Admin Frappe sẽ tạo đúng 3 bảng này cho IMM-04:

1. **`Asset Commissioning Process`** (DocType Mẹ - Master Form). Submittable. Nuôi mầm sống từ State 1 đến State 10.
2. **`Commissioning Checklist`** (DocType Con - Dạng Grid Lưới). Chứa bảng đo đạc dòng điện, đo đạc môi trường, khí, mạng. Đi kèm thuộc tính `is_pass`.
3. **`Asset Initial Non-Conformance`** (DocType độc lập). Submittable. Sinh ra để bóc rác DOA. Tách riêng để Kỹ sư sửa chữa có Form gõ Note giải trình trả hàng mà không làm kẹt luồng Tờ Khai Chính của Kế toán.

---

## D. Giải thích: Vì sao lại vứt bỏ Core ERPNext cho Luồng Lắp Đặt?

*Lý do tại sao không dùng core thuần:*
ERPNext tư duy Mua Sắm Rất Đơn Giản: Nhập kho (`Purchase Receipt`) xong -> Đẻ thẳng luôn ra `Asset` (hoặc qua nút Create Asset). 

**NHƯNG TRONG MEDICAL DOMAIN**: 1 khối sắt MRI nằm trong kho **KHÔNG PHẢI LÀ TÀI SẢN HOẠT ĐỘNG!** Nó chưa có giấy phép phóng xạ, nó chưa được test rò điện. Khối MRI đó nếu đẻ ngay thành `Asset` với Status `In_Use` thì Bác sĩ nhào vô X-Ray gây chết bệnh nhân, Kế toán nhào vô Đếm ngày Khấu Hao -> **Toàn bộ hệ thống sụp đổ độ tin cậy.**

**Đó là lý do `Asset Commissioning Process` tồn tại.** Nó đóng vai trò "Chiếc Bơm Tiền Kỳ" (Pre-requisite Gate). Máy trôi trong bơm này suốt 15 ngày với 10 Workflow States. Khi nào Bơm Nhả Kíp Nổ (Release Gate) thì lệnh Code `frappe.insert('Asset')` mới được hô hoàn. Tài sản được khai sinh trong sạch, đủ giấy chứng nhận QA.

---

## E. Khuyến nghị triển khai kỹ thuật (Best Practices trên Frappe)

1. **Sử dụng `Server Script` Document Event:** Tại DocType `Asset_Commissioning`, dùng hook `on_submit`.
   - Pseudo: `doc.create_core_asset_record()`. Hàm này copy rụp toàn bộ serial nhảy thẳng sang Module Core.
2. **Ẩn Nút Core:** Dùng `Client Script` và `Permission Level` để Disable triệt để nút bấm `[+] Create Asset` tay trên thanh Toolbar của ERPNext. Bóp nghẹt lỗ hổng sinh thiết bị ảo.
3. **Child Table vs Independent:** Việc thiết kế `Non-Conformance` là DocType Độc Lập thay vì Child Table là quyết định mang tính Chiến lược Dữ Liệu! Bởi vì 1 sự cố NC cần có người Resolve (Fix), cần Comment History của riêng nó. Nếu vứt vào Child-Table, NC bị tắt tiếng nói quản trị.
