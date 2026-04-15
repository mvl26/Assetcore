# Workflow States: IMM-04 (Installation & Initial Inspection)

Tài liệu này bóc tách chuẩn xác bộ trạng thái (Workflow States) của máy trạng thái thiết bị y tế tại khâu IMM-04 theo định dạng `Prompt 02`.

---

## 1. Phân loại Trạng thái đặc thù
- **Trạng thái Gate kiểm soát (Chốt chặn):** `Pending_Doc_Verify`, `Initial_Inspection`.
- **Trạng thái Hold (Đóng băng):** `Clinical_Hold` (Tạm dừng không được phép đi tiếp cho đến khi có Cục Đo Lường thẩm định).
- **Trạng thái Non-conformance (Lỗi biệt lập):** `Non_Conformance` (Khi phát sinh DOA hoặc thiếu linh kiện trầm trọng không rớt vào Hold mốc).
- **Trạng thái Re-inspection (Tái thẩm định):** `Re_Inspection` (Sau khi rớt bài test tủ, tiến hành Fix lỗi và phải kiểm tra lại vòng 2).
- **Trạng thái Terminal (Điểm kết thúc vĩnh viễn):** `Clinical_Release_Success` (Thành công nạp lõi), `Return_To_Vendor` (Hủy bỏ/Trả hàng vĩnh viễn).
- **Trạng thái Quay lui (Loopback Allow):** `Re_Inspection` (được phép lui về `Installing` nếu sửa không được), `Non_Conformance` (nếu khắc phục xong có thể đẩy lại vào `Pending_Doc_Verify`).

---

## 2. Bảng Mô tả Workflow States Chuẩn (State Machine Definition)

| STT | Mã State | Tên State (Name) | Mô tả (Description) | Actor chính | Điều kiện vào State (Entry) | Điều kiện ra khỏi State (Exit) | Là Gate? | Sinh Hồ sơ? |
|---|---|---|---|---|---|---|---|---|
| 1 | `S01` | **Draft_Reception** | Nháp lập kế hoạch dỡ hàng. | TBYT Officer | Nhận lệnh cấp PO từ luồng Procurement. | Bấm nút Submit Form. | Không | Không |
| 2 | `S02` | **Pending_Doc_Verify** | Kiểm tra danh mục hồ sơ giấy tờ (CO/CQ/Packing List). | TBYT Officer | Sau khi Submit form `Draft`. | Đã tick đủ 100% tài liệu `Bắt buộc`. | **CÓ** (Doc Gate)| Có (Upload bản Scan)|
| 3 | `S03` | **To_Be_Installed** | Hộp vật lý đã nằm ở khoa, chờ Kỹ sư hãng tháo Seal. | Clinical Head | Pass bước hồ sơ, Khoa lâm sàng ký nhận hàng nắp hộp. | Hãng bấm nút Start Job. | Không | Bảng giao hàng|
| 4 | `S04` | **Installing** | Kỹ sư hãng thao tác cài đặt, kéo cáp, thiết lập dòng rò tĩnh. | Vendor Tech | Sau khi `Start Job`. | Hoàn tất cài đặt hoặc Báo lỗi mạch. | Không | Log thi công |
| 5 | `S05` | **Identification** | Nhập Serial, UID, dán mã Barcode nội bộ lên thân máy. | Biomed Eng | Vendor báo đã cài đặt xong. | Không được trùng lập UID trong DB. | Không | Có (Định danh)|
| 6 | `S06` | **Initial_Inspection** | Kỹ sư TBYT đánh giá chỉ số Baseline (An toàn điện+Calibration). | Biomed Eng | Sau khi dán Barcode xong.| Mọi chỉ số Baseline Test = 'Pass'. | **CÓ** (QA Gate) | Có (Form Baseline) |
| 7 | `S07` | **Non_Conformance** | Phát sinh lỗi DOA lúc vừa bật máy / Thiếu linh kiện. | Biomed Eng / Vendor | Nút `Report DOA` bị kích hoạt ở mọi State từ S03-S06. | Đã khắc phục / đổi máy. (Quay lui về S02 hoặc S04). | Không | Có (Biên bản DOA)|
| 8 | `S08` | **Clinical_Hold** | Phanh kỹ thuật. Thường do máy phát tia X chờ giấy phép. | QA Officer | `Initial_Inspection` Pass cấu trúc, nhưng cần 1 chữ ký ngoài. | Có File "Giấy cấp phép hoạt động". | **CÓ** (Hold Gate)| Có (Giấy KS Bức Xạ)|
| 9 | `S09` | **Re_Inspection** | Trạng thái test lại vòng 2 sau khi máy từng bị rớt ở Initial test. | Biomed Eng | Từ `Non_Conformance` hoặc rớt test S06 mà đã sửa xong.| Tương tự S06. Pass để đi tiếp. | Không | Log Retest định dạng mới|
| 10 | `S10` | **Clinical_Release_Success** | Gate release. Khởi động vòng đời thiết bị với trạng thái Active | Board/CEO | Board bấm Duyệt ở node `Inspection/Hold` hợp lệ. | **TERMINAL STATE**. (Khóa hồ sơ) | **CÓ** (Release)| Biên bản Bàn giao & Sổ TS |
| 11 | `S11` | **Return_To_Vendor** | Loại bỏ thiết bị ra khỏi hệ thống, trả hàng phá hợp đồng do lỗi nặng. | Board | Không thể qua máy `Non_Conformance` hoặc `Re_inspection` Failed N lần.| **TERMINAL STATE**. (Khóa hồ sơ) | Không | BB Trả Hàng |
