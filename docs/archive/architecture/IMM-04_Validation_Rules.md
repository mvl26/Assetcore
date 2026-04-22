# Thiết kế Rule Engine (Bộ Tầm Soát Validation) - IMM-04

Tài liệu này dịch ngược các bài toán chống gian lận (Business Rules) thành các tập luật Validation kỹ thuật, nhằm hướng dẫn Developer viết `Client Scripts` (JS) và `Server Scripts` (Python) đính trực tiếp vào lõi ERPNext/Frappe.

---

## A. Rule Catalog (Danh mục Tập Luật)

| Mã Rule | Tên Luật | Phân loại | Mục tiêu bảo vệ |
|---|---|---|---|
| `VR-01` | Chống Trùng Mã Định Danh (Unique ID) | **Hard** | Bảo vệ Master Asset. 1 Serial Hãng chỉ tồn tại 1 Máy trong Viện. |
| `VR-02` | Chặn đứng Bàn Giao thiếu C/O, C/Q | **Hard** | Bảo vệ ranh giới QMS `Doc_Verify`. |
| `VR-03` | Rào Cản Baseline Test (100% Pass) | **Hard** | Chống lại rủi ro phóng điện/tai nạn lâm sàng. |
| `VR-04` | Quét NC tồn đọng trước Release | **Hard** | Cấm phát hành tài sản nếu rác (Non-Conformance) chưa dọn (Bấm Resolve). |
| `VR-05` | Cảnh báo Thiếu Sách HDSD | *Soft-Warn*| Cho qua, nhưng nổ Pop-up vàng cảnh cáo. |
| `VR-06` | Truy vấn Lý do Amend | **Hard** | Bảo vệ Vết Kiểm Toán (Audit Trail) khi Sửa hồ sơ đã Submit. |
| `VR-07` | Đá văng sang Clinical Hold | **Auto-Action** | Nếu Item thuộc Bức Xạ -> Tự động chuyển làn sang Máy Trạng Thái đóng băng (Hold). |

---

## B. Validation Matrix (Luật ngầm định)

Đặc tả Logic Condition cho từng tập luật:

| Mã Rule | Cú kích hoạt (Event) | Điều kiện kích nổ (Pass/Fail) | Hành động (Action) | Thông báo Lỗi UI (`frappe.throw`) | Triển khai cốt lõi Frappe |
|---|---|---|---|---|---|
| `VR-01` | Save (Form Identification) | `frappe.db.exists("Asset", {"vendor_sn": doc.sn})` | Hủy thao tác Save | "Lỗi VR-01: Serial Number này đã từng được gán cho một cái máy khác. Vui lòng quét lại bằng súng Barcode!" | `Server Side` (Python) |
| `VR-02` | Chuyển Node -> `To_Be_Installed` | Tồn tại `Child.mandatory == 1` VÀ `Child.status == 'No'` | Hủy chuyển Node | "Lỗi VR-02: Không thể dỡ máy khi thiếu Giấy tờ Bản Gốc (C/O, C/Q)." | `Workflow Condition` |
| `VR-03` | Chuyển Node -> `Clinical_Release` | Field `is_pass` tại Grid Baseline Test == 'Fail' | Hủy Submite/Release | "Lỗi VR-03: Rớt tiêu chuẩn an toàn dòng rò. Trạng thái đã bị ép về Clinical Hold!" | `Server Side` (Python Hook)|
| `VR-04` | Bấm nút Submit (Release) | `frappe.db.count("NC", filters={"ref": doc.name, "status": "Open"}) > 0` | Chặn Submit | "Lỗi VR-04: Hệ thống phát hiện đang tồn tại Phiếu Báo Lỗi DOA chưa được khắc phục. Gỡ kẹt Phiếu NC đó rồi tính tiếp!" | `Server Side` (Python) |
| `VR-05` | Chuyển Node -> `To_Be_Installed` | Field Manual == 'Missing' | Bât Toast Message | `frappe.msgprint("Warning: Chưa nhận được Sách HDSD. Hãy đòi Vendor sớm!", indicator="orange")` | `Client Side` (JS) |
| `VR-06` | Bấm nút [Amend] Document | Document is 'Amended' | Ép bật Pop-up Dialogue | "Hãy Gõ lý do tại sao bạn lại Hủy tờ kiểm tra gốc để Test lại lần 2?" | `Client Side` (Form JS) |

---

## C. Mapping Rule ↔ DocType ↔ State

Lưới lưới bủa vây của Bộ Luật:

| Áp dụng lên State nào? | DocType chịu trận | Chặn bắt Luật Nào |
|---|---|---|
| `Pending_Doc_Verify` | Trang Chính `Asset Commissioning` | `VR-02` (Thiếu hồ sơ), `VR-05` (Missing HDSD). |
| `Identification` | Trang Chính `Asset Commissioning` | `VR-01` (Trùng Barcode/Serial). |
| `Initial_Inspection`| Lưới `Baseline Testing Grid` | `VR-03` (Rớt Test Chỉ số đo), `VR-07` (Đá văng Clinical Hold). |
| Lúc bấm Gỡ `Clinical_Hold` | Trang Chính `Asset Commissioning` | Kiểm tra Form License PDF có Empty(). Nếu trống CẤM GỠ. |
| `Clinical_Release_Gate`| Mọi DocType dán với Record Mẹ | `VR-04` (Còn thẻ phạt NC chưa xử lý). |

---

## D. Đề xuất Lớp Triển khai trong Frappe (Deployment Framework Layer)

Để tối ưu Big Data, Frappe/ERPNext phân rẽ các luật này như sau:

1. **Client Side (Trình Dịch Giao diện - JS):**
   - Viết bằng Script trong mảng `Custom Script` UI. 
   - Nhiệm vụ: Xử lý các Soft-Validation (`VR-05`) hoặc Bật Form Ghi Chú Amend (`VR-06`). Cho Code chạy phía trình duyệt tiết kiệm Server. Chỉ cần hàm `frappe.ui.form.on()`.
2. **Server Side (Trình Chặn Lõi - Python Document Hooks):**
   - Viết trực tiếp trong `frappe/hooks.py` thông qua `doc_events = {"Asset Commissioning": {"validate": "path.to.check_unique_sn"}}`. 
   - Nhiệm vụ: Thực thu `VR-01`, `VR-03`, `VR-04`. Không một con Hacker nào hoặc API từ Tool ngoài nào có thể chọc thẳng DB mà vượt qua được lớp Hook vững như bàn thạch này. Database SQL được bảo vệ tĩnh.
3. **Workflow Condition (Động cơ Máy trạng thái):**
   - Dùng thanh Workflow Visual Built-in của ERPNext.
   - Gõ điều kiện vào Cột Rule Condition: `doc.mandatory_docs_completed == 1`. 
   - Cách này để Giám Đốc non-code dễ dàng vào tắt/mở luật khi BV đổi quy chế mà không cần gọi Developer.
4. **Scheduled Job Task (Cronjob):**
   - Lập trịch `1 Hour / Lần`: Quét các Record nào bị kẹt ở mạng `Clinical_Hold` quá 5 ngày mà chưa Upload chứng nhận Bức Xạ. Nếu phát hiện -> Push Alert Mail (Webhook) chửi thằng phân phối Hãng ngâm giấy tờ.
