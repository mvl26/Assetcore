# Báo cáo Đánh giá Kiến trúc: Asset Reception & Commissioning (Review Report)

**Reviewer:** Senior HTM + CMMS Architect
**Đối tượng Review:** Tài liệu `01_Asset_Reception_and_Commissioning.md` và Data Model tương ứng.
**Ngày đánh giá:** Hiện hành.

Dưới góc độ Kiến trúc sư thiết kế nghiêm ngặt về HTM Lifecycle, tôi đã tiến hành "soi" lại chính sách vòng đời và phát hiện một số lỗ hổng thiết kế có thể gây mâu thuẫn hệ thống. Dưới đây là kết quả Audit:

---

## 1. Danh sách Issue & Khuyến nghị (Review Findings)

| ID | Vấn đề phát hiện (Issue) | Tiêu chí vi phạm | Mức độ nguy hiểm (Severity) | Đề xuất sửa chữa (Suggested Fix) |
|---|---|---|---|---|
| **#01** | **Thiếu trạng thái (Missing states) đối với nhóm tài sản "Miễn đào tạo"**: Nếu thiết bị là nhiệt kế hoặc giường y tế thường (không cần Pending Training), luồng bị tắc nghẽn hoặc bắt buộc phải chạy qua nút Training thừa thãi. | Missing States | **Medium** | Bổ sung Skip logic (Tự động bypass): Nếu trường `is_training_required = 0` trên form Item thì tự nhảy từ `Installing` -> `Completed`.
| **#02** | **Thiếu vòng lặp Calibration (Kiểm định gốc) trước khi nghiệm thu:** Trang thiết bị y tế (nhất là nhóm X-Quang, gây mê) phải có giấy chứng nhận Kiểm định/Hiệu chuẩn do bên thứ 3 cấp sau khi Lắp đặt xong. Chu trình nhảy từ Lắp đặt thẳng sang Đào tạo là sai chuẩn WHO. | Violation of HTM lifecycle | **High** | Chèn thêm trạng thái `Pending Calibration / Verification` xen giữa `Installing` và `Pending Training`. Bắt buộc Upload giấy chứng nhận đo lường. |
| **#03** | **Cơ chế Hủy/Từ chối khuyết điểm (Broken transitions):** Nếu ấn nút `Rejected` tại khâu "Bàn giao chân công trình", luồng bị đóng cứng lại tại Terminal State. Nhưng trên ERP, Purchase Order (PO) vẫn đang treo, Kế toán không thể hủy PO. | Broken transitions / Data inconsistency| **High** | Khi chuyển trạng thái `Rejected`, gắn Server Script tự động gửi tín hiệu Cancel liên kết đến PO origin gốc (Nếu chưa thanh toán), hoặc sinh lệnh `Purchase Return`. |
| **#04** | **Quyền hạn phê duyệt ẩn chứa Rủi ro (Missing QMS control):** Vai trò `Asset Manager (TBYT)` được toàn quyền chuyển qua nút `Completed`. Tuy nhiên, với thiết bị có rủi ro cao (Class C, D), QMS đòi hỏi thêm chữ ký của Giám đốc/Phó Giám đốc chuyên môn. | Missing QMS | **Medium** | Tích hợp hệ thống phân cấp (Approval Matrix Matrix): Nếu `risk_class = "High"`, bổ sung 1 node trung gian `Pending Director Approval` trước khi được phép sang `Completed`. |
| **#05** | **Giao nhận thiếu Biên bản gốc lưu trữ (Audit):** Dữ liệu đang được thao tác dưới dạng click tick (Bảng checklist). Audit Trail chỉ ghi nhận User click, nhưng thiếu giá trị pháp lý bản cứng. | Missing audit trail / Compliance | **Low** | Sinh cơ chế `Print Format` tự động của Frappe ra file PDF từ các Checkbox. Bắt chữ ký điện tử hoặc in ra ký sống chụp dán lại trong Form `Completed`. |

---

## 2. Kết luận Tổng quan (Architect Conclusion)

Bản thiết kế cốt lõi tốt (Đáp ứng khoảng 80% luồng cơ bản) nhưng nếu mang lên áp dụng cho Bệnh viện hạng 1 hoặc Bệnh viện có chứng chỉ JCI sẽ **bị Failure ở công đoạn Đánh giá rủi ro thiết bị và Calibration**. 

- **Hành động khắc phục (Action Required):** Cần cập nhật lại file `01_Asset_Reception_and_Commissioning.md` để bổ sung nhánh quy trình phụ `Pending Calibration` và tinh chỉnh script sửa 4 lỗi còn lại trên hệ thống Frappe Data Model.
