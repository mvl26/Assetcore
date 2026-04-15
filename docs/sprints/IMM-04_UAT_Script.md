# BIÊN BẢN KIỂM THỬ NGƯỜI DÙNG (UAT)
# Module: IMM-04 — Lắp Đặt, Định Danh và Kiểm Tra Ban Đầu Thiết Bị Y Tế
# Hệ thống: AssetCore / IMMIS — Quản lý Vòng Đời Trang Thiết Bị Bệnh Viện

---

**Đơn vị triển khai:** Phòng Vật Tư / Tổ Kỹ Thuật Trang Thiết Bị Y Tế
**Phiên test:** ____/____/2026
**Phiên bản hệ thống:** AssetCore v1.x
**Trạng thái:** ☐ Đang test &nbsp;&nbsp; ☐ Hoàn thành &nbsp;&nbsp; ☐ Cần làm lại

---

## HƯỚNG DẪN CHUNG

Tài liệu này hướng dẫn từng bước thao tác trên hệ thống AssetCore để đảm bảo mọi chức năng hoạt động đúng nghiệp vụ thực tế của bệnh viện.

- **Trước khi bắt đầu:** Đăng nhập đúng tài khoản theo vai trò được giao.
- **Khi gặp lỗi:** Chụp màn hình → ghi vào cột "Kết quả thực tế" → báo cáo lại cho bộ phận IT.
- **Dữ liệu test:** Sử dụng dữ liệu mẫu đã chuẩn bị sẵn trong môi trường UAT, **không dùng dữ liệu thật**.

---

## KỊCH BẢN 01 — TIẾP NHẬN THIẾT BỊ VÀ KIỂM TRA HỒ SƠ

**Mục tiêu:** Xác nhận hệ thống cho phép cán bộ TBYT lập phiếu tiếp nhận thiết bị mới, đối chiếu hồ sơ CO/CQ và kẹp lại khi thiếu giấy tờ bắt buộc.

**Người thực hiện:** Cán bộ Phòng TBYT (Vai trò: Kỹ Thuật Viên HTM)

**Dữ liệu đầu vào:**
- Máy thở ICU Ventilator — Hãng: Philips, SN: `VNT-PHL-20260001`
- Lệnh mua hàng số: `PO-2026-0041`
- Hồ sơ đi kèm: Có CO ✓ — **THIẾU C/Q** ✗

| # | Bước Thao Tác | Kết Quả Mong Đợi | Kết Quả Thực Tế | Đạt/Không |
|---|---|---|---|---|
| 1 | Đăng nhập hệ thống bằng tài khoản KTV HTM. Vào menu **Trang Thiết Bị → Tiếp Nhận Thiết Bị Mới**. | Màn hình Form Tiếp Nhận IMM-04 hiện ra. | | ☐ |
| 2 | Tại ô **Lệnh mua hàng**, gõ hoặc chọn `PO-2026-0041`. Hệ thống tự điền Nhà cung cấp và Model máy. | Thông tin hãng và loại máy tự hiện đúng. | | ☐ |
| 3 | Vào mục **Hồ sơ đi kèm**. Tick ✓ mục "CO đã nhận". Để trống mục "C/Q đã nhận". | Ô C/Q hiển thị chưa tích. | | ☐ |
| 4 | Bấm nút **Gửi Duyệt Hồ Sơ** để chuyển sang bước tiếp theo. | **Hệ thống hiện thông báo lỗi màu đỏ:** "Chưa nhận đủ Giấy chứng nhận chất lượng (C/Q). Không thể tiến hành bàn giao máy. Vui lòng liên hệ Nhà cung cấp bổ sung". | | ☐ |
| 5 | Upload file scan giả C/Q vào ô đính kèm. Tick ✓ mục "C/Q đã nhận". Bấm lại **Gửi Duyệt Hồ Sơ**. | Hệ thống chuyển trạng thái sang **"Chờ bàn giao chân công trình"**. Không có lỗi. | | ☐ |

**Ghi chú của người test:** _____________________________________________

---

## KỊCH BẢN 02 — CHUẨN BỊ MẶT BẰNG VÀ KHỞI ĐỘNG LẮP ĐẶT

**Mục tiêu:** Kiểm tra hệ thống chặn lắp máy khi điều kiện hạ tầng (điện, khí, mặt bằng) chưa đạt yêu cầu.

**Người thực hiện:** Kỹ Sư TBYT (Vai trò: Biomed Engineer) + Đại diện Khoa ICU (Vai trò: Clinical Head)

**Dữ liệu đầu vào:** Phiếu tiếp nhận từ Kịch bản 01 đang ở trạng thái "Chờ bàn giao chân công trình".

| # | Bước Thao Tác | Kết Quả Mong Đợi | Kết Quả Thực Tế | Đạt/Không |
|---|---|---|---|---|
| 1 | Kỹ sư TBYT mở phiếu tiếp nhận. Vào tab **Kiểm tra điều kiện lắp đặt**. | Bảng checklist điều kiện hạ tầng hiện ra: Điện 3 pha, Khí trung tâm, Nhiệt độ phòng, Nối đất tiếp địa. | | ☐ |
| 2 | Điền kết quả đo: Điện ✓, Khí ✓, Nhiệt độ ✓. Tại mục **Nối đất tiếp địa** để trạng thái **Không đạt**. | Hàng "Nối đất tiếp địa" hiển thị màu đỏ, trường Ghi chú bắt buộc phải điền. | | ☐ |
| 3 | Bấm **Xác nhận Mặt bằng Đạt** để kỹ sư hãng vào lắp. | **Hệ thống từ chối:** "Điều kiện mặt bằng chưa đủ. Mục Nối đất tiếp địa chưa đạt. Vui lòng hoàn thiện hạ tầng trước khi bàn giao mặt bằng cho Nhà cung cấp". | | ☐ |
| 4 | Sửa kết quả Nối đất thành **Đạt** (sau khi đội cơ điện bệnh viện xử lý). Bấm lại **Xác nhận Mặt bằng Đạt**. | Trạng thái chuyển sang **"Đang lắp đặt"**. Hệ thống ghi nhận thời gian bắt đầu lắp đặt tự động. | | ☐ |

**Ghi chú của người test:** _____________________________________________

---

## KỊCH BẢN 03 — LẮP ĐẶT VÀ ĐỊNH DANH THIẾT BỊ

**Mục tiêu:** Xác nhận kỹ sư hãng có thể log tiến độ lắp đặt, và hệ thống gán mã định danh chính xác — chặn mã bị trùng lặp.

**Người thực hiện:** Kỹ Sư Hãng Philips (Vai trò: Vendor Technician)

**Dữ liệu đầu vào:** Phiếu đang ở trạng thái "Đang lắp đặt". Serial Number thật: `VNT-PHL-20260001`.

| # | Bước Thao Tác | Kết Quả Mong Đợi | Kết Quả Thực Tế | Đạt/Không |
|---|---|---|---|---|
| 1 | Kỹ sư hãng đăng nhập bằng tài khoản được cấp. Mở phiếu lắp đặt. Bấm **Hoàn tất lắp đặt cơ khí**. | Hệ thống mở ra Tab **Định danh thiết bị**. | | ☐ |
| 2 | Tại ô **Serial Hãng**, dùng súng Barcode quét tem có nội dung `VNT-PHL-20260001`. | Mã tự điền vào ô. Không gõ tay được (bàn phím bị khóa). | | ☐ |
| 3 | Thử lại bằng một Serial Number khác đã tồn tại trong hệ thống từ lần nhập kho trước: `VNT-PHL-99999`. | **Hệ thống từ chối:** "Mã Serial này đã được đăng ký cho thiết bị [TEN-MAY-CU]. Vui lòng kiểm tra lại tem máy hoặc liên hệ phòng TBYT!". | | ☐ |
| 4 | Quét lại đúng `VNT-PHL-20260001`. Hệ thống sinh mã QR nội bộ bệnh viện tự động. Bấm **Lưu định danh**. | Một mã QR dạng `BV-ICU-2026-001` được tạo ra. Màn hình hiển thị preview nhãn để in dán lên máy. | | ☐ |

**Ghi chú của người test:** _____________________________________________

---

## KỊCH BẢN 04 — KIỂM TRA AN TOÀN BAN ĐẦU (Baseline Test)

**Mục tiêu:** Kiểm tra quy trình đo kiểm an toàn điện. Hệ thống phải chặn cấp phát tài sản khi có chỉ số rớt chuẩn.

**Người thực hiện:** Kỹ Sư TBYT (Biomed Engineer)

**Dữ liệu đầu vào:** Phiếu đang ở trạng thái "Kiểm tra ban đầu".

| # | Bước Thao Tác | Kết Quả Mong Đợi | Kết Quả Thực Tế | Đạt/Không |
|---|---|---|---|---|
| 1 | Mở Tab **Kết quả đo kiểm an toàn**. Thấy lưới bảng với các tiêu chí: Dòng rò, Điện trở tiếp địa, Kiểm tra khởi động OS. | Bảng hiện đủ các hàng tiêu chí cần đo. | | ☐ |
| 2 | Điền kết quả đo thực tế vào từng hàng. Tại mục **Dòng rò điện**, điền `4.8 mA` (vượt ngưỡng cho phép 2.0 mA). Chọn kết quả: **Không đạt**. | Hàng chuyển màu đỏ. Ô **Ghi chú lỗi** bắt buộc hiện ra. | | ☐ |
| 3 | Để trống ô Ghi chú lỗi. Bấm **Lưu kết quả đo**. | **Hệ thống từ chối lưu:** "Vui lòng mô tả nguyên nhân và biện pháp xử lý tại mục Ghi chú cho tiêu chí đang Không đạt". | | ☐ |
| 4 | Điền ghi chú: "Dòng rò vượt mức do kẹp nối đất lỏng. Đã siết lại và đo lại sẽ thực hiện vào ngày mai". Lưu thành công. Bấm **Gửi kết quả đo kiểm**. | Phiếu chuyển sang trạng thái **"Tạm dừng — Chờ kiểm tra lại"**. Hệ thống **KHÔNG** cho phép phát hành tài sản. | | ☐ |
| 5 | Đo lại lần 2, điền `1.2 mA` (đạt). Chọn kết quả: **Đạt cho tất cả tiêu chí**. Bấm **Gửi kết quả đo kiểm**. | Phiếu chuyển sang trạng thái **"Chờ phê duyệt phát hành"**. | | ☐ |

**Ghi chú của người test:** _____________________________________________

---

## KỊCH BẢN 05 — PHÊ DUYỆT PHÁT HÀNH (Clinical Release)

**Mục tiêu:** Xác nhận chỉ Phó/Trưởng Phòng Khối 2 mới có quyền ký phát hành thiết bị vào sử dụng, và hệ thống tự động tạo thẻ Tài sản sau khi duyệt.

**Người thực hiện:** Phó Trưởng Phòng Khối 2 (Vai trò: VP_Block2)

**Dữ liệu đầu vào:** Phiếu đang ở trạng thái "Chờ phê duyệt phát hành". Toàn bộ test đã Pass.

| # | Bước Thao Tác | Kết Quả Mong Đợi | Kết Quả Thực Tế | Đạt/Không |
|---|---|---|---|---|
| 1 | Đăng nhập bằng tài khoản PTP Khối 2. Vào Hộp thư thông báo. | Có thông báo đang chờ duyệt: "Phiếu lắp đặt VNT-PHL-20260001 đã sẵn sàng để phê duyệt phát hành". | | ☐ |
| 2 | Mở phiếu. Xem lại kết quả đo kiểm và hồ sơ. Bấm nút **Phê duyệt Phát hành**. | Hộp xác nhận xuất hiện: "Bạn xác nhận phát hành thiết bị này vào sử dụng tại Khoa ICU?". | | ☐ |
| 3 | Xác nhận đồng ý. | Hệ thống tự động: (1) Tạo thẻ Tài sản mới trong ERPNext với trạng thái **"Đang sử dụng"**. (2) Khóa toàn bộ phiếu lắp đặt — không ai sửa được nữa. (3) Hiển thị số mã tài sản mới được cấp. | | ☐ |
| 4 | Đăng nhập lại bằng tài khoản KTV HTM. Thử sửa trường **Ngày lắp đặt** trên phiếu đã duyệt. | **Tất cả trường đều bị khóa**. Không có nút Sửa. Dữ liệu chỉ được xem và in. | | ☐ |

**Ghi chú của người test:** _____________________________________________

---

## KỊCH BẢN 06 — THIẾT BỊ BỨC XẠ PHẢI QUA KIỂM ĐỊNH NHÀ NƯỚC

**Mục tiêu:** Với máy X-Quang, hệ thống phải tự động yêu cầu giấy phép Cục An toàn Bức xạ trước khi cho phép phát hành.

**Người thực hiện:** Kỹ Sư TBYT + Cán bộ Phòng Pháp chế/HC-QLCL

| # | Bước Thao Tác | Kết Quả Mong Đợi | Kết Quả Thực Tế | Đạt/Không |
|---|---|---|---|---|
| 1 | Tạo phiếu lắp đặt mới cho **Máy X-Quang kỹ thuật số** (Item có đánh dấu Bức xạ = Có). | Khi chọn Model máy, ô **Thiết bị có bức xạ** tự tick. | | ☐ |
| 2 | Hoàn thành toàn bộ các bước từ hồ sơ → lắp đặt → đo kiểm (tất cả đạt). Bấm **Phát hành**. | Hệ thống **KHÔNG** cho phép phát hành. Chuyển sang trạng thái **"Tạm giữ — Chờ giấy phép bức xạ"**. Hiện thông báo: "Thiết bị phát tia bức xạ cần có Giấy phép hoạt động của Cục An toàn Bức xạ Hạt nhân. Vui lòng upload đính kèm văn bản." | | ☐ |
| 3 | Cán bộ Pháp chế upload file scan giấy phép Cục ATBXHN. Bấm **Xác nhận đã có giấy phép**. | Trạng thái chuyển sang **"Chờ phê duyệt phát hành"**. Quy trình tiếp tục bình thường. | | ☐ |

**Ghi chú của người test:** _____________________________________________

---

## TỔNG HỢP KẾT QUẢ UAT

| Kịch bản | Số Test | Đạt | Không Đạt | Ghi chú |
|---|---|---|---|---|
| KB01 — Tiếp nhận & Hồ sơ | 5 | | | |
| KB02 — Mặt bằng Lắp đặt | 4 | | | |
| KB03 — Lắp đặt & Định danh | 4 | | | |
| KB04 — Kiểm tra an toàn | 5 | | | |
| KB05 — Phê duyệt Phát hành | 4 | | | |
| KB06 — Thiết bị Bức xạ | 3 | | | |
| **TỔNG** | **25** | | | |

**Kết luận UAT:** ☐ Đạt — Cho phép đưa vào vận hành &nbsp;&nbsp; ☐ Chưa đạt — Cần sửa và test lại

---

## BẢNG KÝ XÁC NHẬN

| Vai trò | Họ tên | Chức vụ | Chữ ký | Ngày |
|---|---|---|---|---|
| **Người test chính** (KTV TBYT) | | | | |
| **Người giám sát** (Trưởng Workshop) | | | | |
| **Đại diện Nghiệp vụ** (PTP Khối 2) | | | | |
| **QA Lead** | | Phòng Hành Chính QLCL | | |
| **QMS Reviewer** | | Tổ Quản lý Chất lượng | | |
| **Phê duyệt triển khai** (IT/Dev Lead) | | | | |
