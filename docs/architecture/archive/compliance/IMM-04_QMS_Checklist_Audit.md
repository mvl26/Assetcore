# Thiết kế Hệ thống QMS: Checklist, Approval Matrix & Audit Rule (IMM-04)

Tài liệu này bóc xuất các văn bản SOP thực địa cứng ngắc và chuyển tải chúng thành ma trận kiểm soát số học (QMS Digital Control Matrix), phục vụ Module **IMM-04**.

---

## A. Danh mục Checklist Số hóa (Checklist Catalog)

Thay vì điền giấy, AssetCore gói gọn các SOP thành 3 loại Checklist tĩnh ghim trên DocType:

| Tên Checklist (Digital Name) | Biểu mẫu gốc | Thời điểm kích hoạt (Trigger State) | Actor Điền | Actor Duyệt | Mức độ bắt buộc |
|---|---|---|---|---|---|
| `Doc_Verify_Checklist` | BM01.01.02 | `Pending_Doc_Verify` | TBYT Officer | TBYT Head | **Tuyệt đối** (Gate) |
| `Site_Ready_Checklist` | BM01.02.02 | `Pending_Site_Verify` | Biomed Eng. | Clinical Head | **Tuyệt đối** (Gate) |
| `Initial_Baseline_Checklist` | BM02 (Mẫu đo) | `Initial_Inspection` | Biomed Eng. | Chief Eng. | **Tuyệt đối** (Gate) |

---

## B. Bảng Cấu trúc Item Checklist (Checklist Logic Lưới)

Với từng dòng bên trong Child-Table của hệ thống, các rào cản thao tác UX/UI như sau:

| Hạng mục kiểm tra (Checklist Item) | Kiểu trả lời (Answer Type) | Bắt buộc Ảnh (Need Photo) | Chú thích khi Fail (Fail Note Req.) | Kích hoạt NC khi Fail (Raise NC) |
|---|---|---|---|---|
| **I. Doc_Verify_Checklist** | | | | |
| C/O (Nguồn gốc xuất xứ) gốc | Select (Có/ Không/ N/A) | Không | Không | Sinh **NC** (Tạm giữ) |
| C/Q (Chất lượng) gốc | Select | Không | Không | Sinh **NC** |
| Hướng dẫn bảo trì NSX | Select | Không | Yêu cầu ghi lý do thiếu | Không (Soft-Warning) |
| **II. Site_Ready_Checklist** | | | | |
| Nối đất tiếp địa < 0.5 Omh | Float input | **BẮT BUỘC CHỤP** | Cần ghi chú phương án | Khóa không cho lắp |
| Nguồn điện ổn định 220V | Checkbox | Nhạy cảm, Không cần | Không | Sinh **NC** (Báo kỹ thuật viện) |
| **III. Initial_Baseline_Checklist** | | | | |
| Kiểm tra dòng rò tĩnh | Float (mA) | Nhạy cảm, Không cần | **BẮT BUỘC ĐIỀN** | Sinh **NC** System Fail |
| Test khởi động OS máy | Select (Pass/Fail DOA) | **BẮT BUỘC CHỤP LỖI** | **BẮT BUỘC ĐIỀN** | Sinh **NC** DOA (Báo Hãng) |

---

## C. Approval Matrix (Tích hợp Ký duyệt các form ở IMM-04)

Bảng chi định các tầng lớp cấp duyệt (Levels of Approval):

| Hồ sơ / Cột mốc cần ký | Role duyệt mức 1 | Role duyệt mức 2 (Nếu Value > 1 Tỉ) | Trạng thái sau Approve |
|---|---|---|---|
| `Bản nghiệm thu mặt bằng thi công` | TBYT Head | (Không yêu cầu) | Chuyển `To_Be_Installed` |
| `Biên bản Baseline Test Pass` | Biomed Eng. | Chief Engineer | Cho phép chọn Release |
| `Biên bản DOA vĩnh viễn (Return)` | Chief Engineer | Hospital Board / Director | Lock System -> Trả về |
| `Lệnh gỡ Hold máy bức xạ` | QA Officer | (Không yêu cầu) | Update License -> Pass |

---

## D. Audit Rule Matrix (Quy tắc kiểm toán & Khóa dữ liệu)

Dữ liệu y tế liên quan đến an toàn tính mạng không thể thay đổi sau khi chốt chặn bị gài.

| Tên Hồ sơ (Document Type) | Khóa vĩnh viễn (Lock on Submit?) | Version Control / Controlled Copy? | Vết Kiểm toán (Audit Requirement) |
|---|---|---|---|
| `Doc_Verify_Checklist` | Tự động Log Version | Có. Lưu vết Version History Frappe. | Lưu vết Version "Từ Chưa có -> Thành Có CO". Vĩnh viễn. |
| `Installation_Daily_Log` | Được sửa tự do khi `Installing` | Không yêu cầu | Lưu vết User tạo dòng comment, ngày giờ. |
| `Initial_Baseline_Checklist`| **Lock 100% khi qua `Release`**| **Controlled Copy** (Cấm sửa trực tiếp) | Cấm gỡ Unlock. Chỉ cho phép dùng nút [Amend] (Tạo bản nháp v2 và Cancel bản v1). |

---

## E. Rule liên thông: Checklist → Workflow → NC → Re-inspection

(Đây là đoạn mã Pseudo-C để kỹ sư lập trình Server Scripts Frappe hình dung)

1. **Kháng lệnh Gate:**
   Mỗi khi Cán bộ nhấn Nút Chuyển Trạng Thái `Send to Install` tại lưới (Site Ready Check): 
   Hệ thống lục soát Checklist: Nếu Tồn tại 1 item có `[X] Kích hoạt NC khi Fail` đang bị trả lời là "Failed": Hệ thống hủy tác vụ chuyển luồng, quăng Exception lên màn hình đỏ rực.

2. **Quy tắc đẻ rác vòng đời Non-Conformance (NC):**
   Tại mốc `Initial_Inspection` (Bước Kỹ sư đo Baseline rò điện).
   Nếu Kỹ sư nhập "Giá trị dòng rò thực tế > 3.0mA" (Fail):
   - **Checklist Event:** Row Status đổi màu đỏ "FAILED". Bật Pop-up bắt Kỹ sư gõ "Ghi chú khi Fail" bằng Textarea.
   - **Workflow Event:** Tự động đá State Machine văng khỏi luồng chính, mắc kẹt vào State: `Non_Conformance`.
   - **Notification Event:** Bắn Email ghim cảnh báo đến Vendor `[MÃ MÁY X] Test Thất bại. Yêu cầu Fix.`

3. **Mồi hồi sinh (Re-inspection Rule):**
   Đang ở `Non_Conformance`, Hãng sửa xong và kỹ sư Bấm nút [Fixed]:
   - **Checklist Event:** Hệ thống không cho phép Clear cái Result = 'Fail' cũ đi. (Vi phạm luật Audit mục C). Thay vào đó, Tool tạo tự động một Child-Table Version Test thứ 2 (Re-test) trống trơn kề bên.
   - **Workflow Event:** Bơm State hiện hành về `Re_Inspection`. Chờ Kỹ sư vào điền kết quả vào Table Test 2. Lặp lại vòng check.
