# Báo cáo: Rà soát & Hardening Kiến trúc Toàn diện (IMM-04)

**Đơn vị thực hiện:** Solution Architect & QA Lead
**Phạm vi:** Tổng kiểm tra chéo (Cross-check) 11 bản lề phân tích của Module IMM-04.
**Mục tiêu:** Nhận diện điểm mù (Blind spots), bịt lỗ hổng vòng lặp (Loophole) và củng cố bê tông (Hardening) cho hệ điều hành IMMIS.

---

## I. Phân Tích 12 Tiêu chí Đánh giá Mù (Blind Spots Audit)

1. **Thiếu workflow state nào không?** CÓ. Tại khúc trả hàng DOA, chưa có State `Pending_Vendor_Pickup`. Việc để đồ rác lăn lóc ở `Non_Conformance` mãi mãi mà không chốt ai tới khuân đi ở Khoa là điểm hở.
2. **Có transition nào mâu thuẫn không?** CÓ. Transition từ `Pending_Doc_Verify` (hồ sơ lỗi) văng về `Draft` có thể khiến Kho Vận không biết đường nào mà giao.
3. **Có gộp sai thực thể dữ liệu không?** Chút xíu ở Mạch `Commissioning Checklist`. Nếu gộp nhầm Test Kỹ thuật mạng lưới (Site) với Baseline (Dòng rò) vào một Grid chung sẽ bị conflict quyền của Actor (Anh Đo Cơ Điện vs Kỹ Sư Sinh Hóa khác nhau).
4. **Có thiếu actor thật nào không?** THIẾU. **Bộ phận Kế toán / Mua sắm (Purchasing)**. Hệ thống Release xong mà Purchasing không nhận được Noti thanh khoản Cọc HĐ đợt 2 thì rất phi lý. Kế toán Mua sắm phải là một Actor nhận Signal.
5. **Có thiếu evidence record nào không?** CÓ. Chữ ký số từ Kỹ sư hãng (Vendor) điền Biên bản lắp đặt bằng File giấy cần một Child-Table riêng cho họ kí tay (E-Signature) chứ không phải chỉ mình anh Biomed Viện kí.
6. **Có bước nào chưa có audit trail không?** Hiện tại việc Vendor dời lịch thi công (Installation Date) bị bỏ nhỏ. Action này cần bắt Audit Lock.
7. **Có gate nào chưa đủ mạnh để block release không?** CÓ. Ở Rule VR-04, tuy chặn Submit nếu dính thẻ NC, nhưng thẻ NC DOA nếu lỡ tay ấn "Closed" thì chả có ai duyệt vòng 2.
8. **Lỗ hổng Permission Matrix?** Nếu User là KTV HTM lại đi Cấu hình nhầm Item Asset (Master Data) có thuộc tính "Không áp dụng đo lường bức xạ" thì lưới Tự động đá thẻ `Clinical_Hold` bị vô hiệu hóa! Root Master Data Item buộc phải chốt phân quyền.
9. **Có validation đang để hở?** Việc nhập Serial Number bằng tay ở State 5 (Identification). Nhập bằng bàn phím sẽ 100% xảy ra Human Error "O" thành "0".
10. **Dashboard mất trace gốc?** Metric Đo lường SLA Lắp đặt tính bằng Ngày nhập Kho. Đáng lẽ phải dùng Date Timestamp của Frappe tại Node 3 (To_Be_Installed).
11. **Operating Architecture Vi phạm?** Module này cõng luôn việc đánh giá Rủi Ro Tài Sản (Risk Matrix). Đây là việc nặng quá. Risk Assessment nên tách hẳn ra một Form CĐ khác phụ trợ.
12. **Nên đẩy gì sang module khác?** Quá trình đo "Sự cố vỡ vỏ nhựa nhưng không ảnh hưởng cốt lõi - Pass kèm Condition" nên để IMM-05 (CMMS) lo lúc Bảo trì 3 tháng đầu, không nên bắt dính vào IMM-04 vì sẽ nghẽn Khoa cần xài máy gấp.

---

## II. Bảng Danh sách Issue & Hardening Plan (Fixes)

| ID | Issue (Lỗ hổng) | Mức độ | Tác động nếu không sửa | Đề xuất chỉnh sửa Hardening |
|---|---|---|---|---|
| `#01` | Form Báo DOA vô thừa nhận (Thiếu Actor Vendor pickup) | **Medium** | Rác máy móc nằm chật khoa, cản trở ca mổ. | Sinh State `Pending_Vendor_Pickup` để theo dõi ngày Hãng lấy Tủ đi. Đánh KPI Phạt Hãng. |
| `#02` | Kỹ thuật viên TBYT "Chạm" Master Data Item thay đổi Class Bức xạ để lọt Gate | **High** | Máy X-Quang lọt sàng ko đo kiểm nhà nước. Gây nguy hiểm sinh mạng y tế. | **Hardening Permission:** Phân quyền Dữ liệu Chủ (Master Data Item) chỉ `CMMS_Admin` hoặc `Board` được tạo. IMM-04 Read-only. |
| `#03` | Thiếu tín hiệu xả nợ cuối vòng cho Khối Purchasing (Kế Toán) | **High** | Kho đọng tiền tỉ, hãng dọa cắt dịch vụ. | **Hardening Event:** Chèn thêm actor `Purchasing` vào luồng Notification khi Event `imm04.release.approved` nổ bùng. |
| `#04` | Sai số con người khi nhập Serial Number định danh | **High** | Tra vết máy sai bét, bảo mật Barcode nát | **Hardening Rule:** Thêm luật Lớp Client `VR-08`: Field Serial phải Validate đúng RegEx, HOẶC bắt buộc Focus Mode cho súng Laser Scanner nhập. |
| `#05` | Sai giới hạn thẩm định (Site Check vs Baseline Test) bị gộp vào 1 lưới | **Low** | UX xấu, khó cho Cơ điện và HTM nhập liệu. | **Hardening DB:** Tách Form Lưới thành 2 Child-Tables Riêng biệt: 1 cái của Cơ-Điện-Nước. 1 Cái của Y Sinh (Baseline Tâm Thu). |

---

## III. Phiên bản thiết kế sau Hardening (Bản Mệnh Lệnh Định Đoạt)

Với các nâng cấp Bông gòn Kẽm Gai (Hardening) bên trên:

1. **Thiết kế DB:** Form Commissioning tách 2 Child-Table cho 2 khối Cơ điện và KTV Y Sinh nhập riêng biệt.
2. **Quyền Hạn:** Nhổ cỏ tận gốc quyền can thiệp vào Mảng Thông số Mặc định trên Form `Item` (Master) của kỹ thuật viên. QMS chỉ vững khi gốc Master KHÔNG THỂ BỊ THAY ĐỔI vì lười biếng.
3. **UX Nhập liệu:** Thiết kế UI phải Force Keyboard Lock tại màn hình `Identification` để KTV bắt buộc phải nổ cò bắn Súng Laser QR tránh rác "O" với "0".
4. **Vòng khép kín Thanh toán Hợp đồng:** Một Webhook (Event Stream) thứ ba sẽ được kéo thẳng về khoang máy của Kế toán để bật Còi báo "Trích quỹ giải ngân đợt 2" cho chiếc Máy vừa rớt cái tem Clinical Ready xong.

**Kết luận Reviewer:** Sau khi dặm lại tàn dư 5 Issue trên, bản thiết kế 18 điếm cốt lõi của "Chương 4 Lịch Sử Y Khoa" IMM-04 System Architecture chính thức trở thành tấm khiên Thép Kim Cương, miễn nhiễm với mọi mưu mẹo vận hành!
