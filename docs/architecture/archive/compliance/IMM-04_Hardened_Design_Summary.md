# IMM-04 Hardened Design Summary (Phiên bản Đóng Rắn sau Pilot)
# Phục vụ: Kiểm định Thiết kế trước UAT

**Phiên bản:** 1.0 - Hardened
**Ngày báo cáo:** 2026-04-15
**Tài liệu Cơ sở:** Báo cáo Triage [IMM-04_Issue_Triage.md](file:///home/adminh/frappe-bench/apps/assetcore/docs/compliance/IMM-04_Issue_Triage.md)

---

## 1. TỔNG QUAN PHIÊN BẢN HARDENED

Sau khi trải qua các đợt Sandbox và CRP, chúng tôi đã phân loại **22 issues** và thực hiện **Gap Closure** đóng băng cấu trúc. "IMM-04 Hardened Version" là thiết kế đã được gia cố để không bị xuyên thủng bởi các hành vi bypass nghiệp vụ, đảm bảo 100% tài sản đi qua cửa ngõ phải được kiểm duyệt QMS.

- **Issue đã đóng (Fix-now) trước UAT:** 14/14 (Bao gồm lỗi Architecture, Permission, VR-07 Auto Hold).
- **Issue chuyển qua Defer (Sprint tới):** 8/22 (Đa số là báo cáo Report, Custom CSS UX và tính năng Email không trọng yếu).

---

## 2. CÁC ĐIỂM GIA CỐ CHÍNH (Hardening Changes)

Dựa trên nguyên tắc ưu tiên hệ thống chặt chẽ để nghiệm thu:

### 2.1 Cập nhật Workflow & Rule (Đã cấu hình trong Source)
1. **Khóa tử huyệt Release (ISS-03):** Chốt cứng Actor `VP Block2` trên Transition `Phê duyệt Phát hành`. Các Roles còn lại như HTM Technician dù thấy Nút bấm hay mò ra URL thao tác cũng bị Server ERPNext đánh bật (Throw `HTTP 403 Forbidden`).
2. **Kích hoạt Lỗ đen Clinical Hold (ISS-02):** Logic mã nguồn đã gắn hàm `validate_radiation_hold()`. Hễ check box Bức xạ = Yes, mà Field Document Giấy phép rỗng, thiết bị vĩnh viễn bị giam ở nút Hold, không thể nhích sang lâm sàng (Chặn QMS Risk mức cao nhất).
3. **VR-08 Lock Cứng Serial (ISS-06):** Script Client không còn là Alert màu vàng, mà đổi thành `frappe.validated = false` cấm Save nếu Serial bị nhập từ bàn phím ở tốc độ chậm (Ngăn chống thói quen gõ tay gây sai số hệ thống Kế toán).

### 2.2 Cập nhật Data Model
1. **Req-02b (Tài liệu tối thượng):** Field "Biên bản Bàn giao Mặt Bằng" được gán quyền `Is_Mandatory = 1`. Lách mất cửa lưu trữ tạm (Draft).
2. **Naming Series An Toàn:** Củng cố mã tự sinh bù số O. Format `IMM04-26-04-00001` (Giúp Sorting Table và Audit chuẩn ISO 9001).
3. **Traceability Index (ISS-09):** Field ID của Ticket Báo Hỏng DOA đã được mở khóa hiển thị ngay trên lưới NC View, Trưởng Workshop bấm 1 chạm là truy lại được Ticket Khai sinh. Đóng khoảng trống Tracking.

---

## 3. PHÂN LOẠI ẢNH HƯỞNG NGHIỆM THU

*Điều này cam kết Hệ thống khi Go-Live nếu có "lỗi nhỏ" cũng không phải là Cớ để ngâm Ký Duyệt UAT.*

| Hạng Mục | Cần cho Nghiệm thu? | Trạng thái ở bản Hardened |
|---|---|---|
| **Dữ liệu Asset Core vỡ/sai lệch** | 🔴 Chặn nghiệm thu | ✅ 100% Safe (Đã bọc Transaction). |
| **Bypass Permission, lách Role** | 🔴 Chặn nghiệm thu | ✅ 100% Safe (Đã Fix ISS-03). |
| **Quy tắc QMS bị vô hiệu hóa** | 🔴 Chặn nghiệm thu | ✅ 100% Safe (VR-07, VR-01 Hardened). |
| Màn hình hiển thị quá nhiều trường bị thừa | Vàng (Không chặn) | UX Tạm chấp nhận, sẽ gom chung đợt update Form V1.1. |
| Mất Notification (ZNS, Email, Alert nội bộ) | Khaki (Không chặn) | Bypass (Chỉ ảnh hưởng quy trình giao tiếp, không ảnh hưởng Database). UAT sẽ dùng phương pháp Communication thủ công để mô phỏng. |

---

## 4. KẾT LUẬN ĐÓNG BĂNG SCOPE V1.0

Bộ Thiết kế (Spec), Data Model, Workflow Transitions và Server Scripts của Module IMM-04 hiện tại được bảo vệ dưới Nhãn **"IMM-04 Hardened Version"**. 

Bất kỳ yêu cầu thêm Field mới (Contract_No, Warranty_Expire...), thay đổi quy trình Thẩm định thứ 3, hoặc đổi màu sắc Notification Report sẽ bị từ chối triệt để và tự động Đưa sang Backlog của Module nâng cấp (V1.1), trừ khi ảnh hưởng trực tiếp đến Quyết toán Tài chính của Kế toán Viện.
