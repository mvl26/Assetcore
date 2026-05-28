# IMM-04 — Phát hành (User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | **IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu** |
| Phiên bản | 0.0.2 |
| Ngày phát hành | 2026-05-27 |
| Owner | PM + BA + Tech Writer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) · [Functional Specs](./IMM-04_Functional_Specs.md) |

> **Chính sách versioning:** Tuân theo `assetcore/__init__.py = 0.0.2`; module docs đồng bộ phiên bản app (release cùng nhịp app, không tách module-version).

---

# Phần I — Hướng Dẫn Sử Dụng

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.

## I.1. Giới Thiệu

Module **Lắp đặt & Nghiệm thu (IMM-04)** giúp bộ phận kỹ thuật thiết bị y tế quản lý toàn bộ quy trình từ khi nhận thiết bị từ nhà cung cấp đến khi đưa thiết bị vào sử dụng lâm sàng chính thức.

Mọi thiết bị y tế trước khi được sử dụng cho bệnh nhân đều phải đi qua **Phiếu Nghiệm Thu**. Phiếu này ghi lại: kiểm tra hồ sơ giấy tờ, lắp đặt tại vị trí, gán số serial và mã QR nội bộ, đo kiểm tra an toàn điện, và phê duyệt của Ban Giám Đốc. Chỉ sau khi phiếu được duyệt, thiết bị mới tồn tại chính thức trong hệ thống và được phép sử dụng.

**Trước khi bắt đầu, bạn cần:**
- Tài khoản hệ thống AssetCore (liên hệ IT nếu chưa có)
- Trình duyệt Chrome hoặc Edge phiên bản mới nhất
- Kết nối mạng nội bộ bệnh viện
- Màn hình tối thiểu 1024×768 (khuyến nghị 1366×768 trở lên)

**Đăng nhập:**
1. Mở trình duyệt, truy cập địa chỉ: `https://assetcore.vn`
2. Nhập tên đăng nhập và mật khẩu do IT cấp
3. Bấm **Đăng nhập** — hệ thống chuyển về màn hình chính

## I.2. Nhận Biết Bạn Đang Ở Đâu

Màn hình chính gồm 3 khu vực:

```
┌─────────────────────────────────────────────────┐
│  ① Thanh trên (Topbar) — Tìm kiếm, thông báo   │
├────────┬────────────────────────────────────────┤
│        │  ③ Vùng nội dung chính                 │
│ ②     │  (Danh sách / Chi tiết / Dashboard)     │
│ Sidebar│                                         │
│ (menu) │                                         │
└────────┴────────────────────────────────────────┘
```

- **① Topbar**: Nút tìm kiếm nhanh, chuông thông báo, thông tin tài khoản.
- **② Sidebar**: Menu module. Tìm **"Lắp đặt"** hoặc **"Nghiệm thu"** để vào IMM-04.
- **③ Vùng chính**: Danh sách phiếu, chi tiết phiếu, hoặc Dashboard.
- **Chấm màu cam** ở sidebar = Module Lắp đặt đang active.

## I.3. Các Vai Trò

| Vai trò | Bạn làm gì trong module này? |
|---|---|
| **Nhân viên TBYT** | Tạo phiếu nghiệm thu khi nhận hàng từ nhà cung cấp; upload tài liệu CO/CQ/Manual |
| **Kỹ sư/Kỹ thuật viên Biomed** | Thực hiện lắp đặt thực tế; gán số serial và mã QR; đo kiểm tra an toàn điện baseline |
| **Kỹ thuật Vendor (NCC)** | Xác nhận lắp đặt hoàn thành; báo cáo lỗi Dead-On-Arrival (DOA) nếu có |
| **Nhân viên QA** | Xử lý Clinical Hold cho thiết bị Class C/D/Radiation; upload giấy phép Bộ Y tế; gỡ Hold |
| **Trưởng xưởng (Workshop Head)** | Duyệt và nộp phiếu; hủy phiếu khi cần; xem Dashboard tổng quan |
| **Ban Giám Đốc (VP/Board)** | Phê duyệt cuối cùng trước khi thiết bị được đưa vào sử dụng chính thức |

## I.4. Quy Trình Chính

```
① Nhận hàng từ NCC
      │
      ▼
② Tạo Phiếu Nghiệm Thu
   (Nhân viên TBYT — từ Đơn Mua Hàng)
      │
      ▼
③ Kiểm tra & Upload Tài liệu
   (CO, CQ, Manual, Giấy phép)
      │
      ▼ G01 — Đủ tài liệu
④ Lắp đặt Thực tế
   (Kỹ sư Biomed + Vendor)
      │
      ▼
⑤ Định danh Thiết bị
   (Gán Serial Number + Mã QR nội bộ)
      │
      ▼
⑥ Đo kiểm An toàn Điện
   (Kỹ sư Biomed — Baseline Tests)
      │
      ├─► Class C/D/Radiation
      │       │
      │       ▼ VR-07 auto-hold
      │   ⑦ Clinical Hold
      │   (QA Officer upload giấy phép BYT)
      │       │
      └───────▼
          ⑧ Phê duyệt Ban Giám Đốc
             │
             ▼
          ✅ Thiết bị Active — Sẵn sàng lâm sàng
```

## I.5. Thao Tác Theo Vai Trò

### a. Nhân viên TBYT — Tạo phiếu và upload tài liệu

**Khi nào làm?** Khi hàng về kho, có Đơn Mua Hàng được duyệt.

**Các bước tạo phiếu:**
1. Vào menu **Lắp đặt** → bấm nút **"Tạo mới"** (góc phải trên)
2. Chọn **Đơn Mua Hàng** — hệ thống tự điền nhà cung cấp, tên thiết bị, phân loại rủi ro
3. Chọn **Vị trí lắp đặt** (Khoa/Phòng)
4. Chọn **Kỹ sư phụ trách** và **Trưởng khoa nhận hàng**
5. Điền **Ngày nhận hàng** (không được là ngày tương lai)
6. Bấm **"Lưu"** — phiếu tạo thành công với mã `ACC-YY-MM-#####`

> ⚠️ Hệ thống tự tạo danh sách tài liệu bắt buộc dựa trên loại thiết bị. Thiết bị Class C/D/Bức xạ sẽ có thêm hàng "Giấy phép lưu hành BYT".

**Các bước upload tài liệu (Gate G01):**
1. Mở phiếu ở trạng thái *Chờ kiểm tra tài liệu*
2. Vào tab **Tài liệu**
3. Với mỗi hàng tài liệu bắt buộc (CO, CQ, Manual, ...):
   - Bấm "Upload" → chọn file PDF (tối đa 20 MB)
   - Điền Số hiệu, Ngày cấp, Ngày hết hạn (nếu có)
   - Status tự chuyển sang **Received**
4. Khi tất cả tài liệu = Received, bấm **"Xác nhận đủ tài liệu"**

> ⚠️ Tài liệu đã hết hạn sẽ bị hệ thống từ chối. Vui lòng cập nhật tài liệu còn hiệu lực trước khi upload.

---

### b. Kỹ sư Biomed — Lắp đặt và đo kiểm

**Khi nào làm?** Sau khi phiếu ở trạng thái *Chờ lắp đặt*.

**Lắp đặt:**
1. Bấm **"Bắt đầu lắp đặt"** → phiếu chuyển *Đang lắp đặt*
2. Phối hợp với kỹ thuật vendor lắp đặt thiết bị tại vị trí
3. Sau khi xong: bấm **"Lắp đặt hoàn thành"** → chuyển *Định danh*

**Gán Serial Number và Mã QR:**
1. Mở tab **Định danh**
2. Nhập **Số serial nhà sản xuất** (quét barcode USB nếu có scanner)
3. Hệ thống tự kiểm tra serial chưa trùng — hiện ✓ xanh nếu hợp lệ
4. Mã QR nội bộ (`BV-CDHA-2026-001`) tự sinh — in dán lên thiết bị
5. Bấm **"Xác nhận định danh"** → chuyển *Kiểm tra ban đầu*

**Đo kiểm an toàn điện (Baseline Tests):**
1. Mở tab **Checklist Baseline**
2. Điền kết quả đo cho từng mục:
   - **Loại số** (điện áp, dòng rò): nhập giá trị đo được
   - **Loại Pass/Fail**: chọn kết quả
   - Mục đánh dấu ⚡ là **mục quan trọng** — fail sẽ block release
3. Bấm **"Nộp kết quả"**:
   - Tất cả Pass/N/A → có thể tiến đến phê duyệt
   - Có mục quan trọng Fail → tự động chuyển *Tái kiểm*

> 💡 Sau khi nộp, checklist bị khóa — không thể sửa. Nếu cần sửa: liên hệ CMMS Admin.

---

### c. Kỹ thuật Vendor — Xác nhận lắp đặt

**Khi nào làm?** Sau khi kỹ sư biomed mở phiếu *Đang lắp đặt* và yêu cầu xác nhận.

**Các bước:**
1. Đăng nhập bằng tài khoản vendor do IT cấp
2. Mở phiếu được chia sẻ
3. Sau khi lắp đặt hoàn thành: bấm **"Lắp đặt hoàn thành"**
4. Nếu thiết bị lỗi khi mở hộp (DOA): bấm **"Khai báo DOA"** → điền mô tả + upload ảnh

---

### d. QA Officer — Xử lý Clinical Hold

**Khi nào làm?** Khi nhận thông báo hệ thống "Thiết bị Class C/D cần giấy phép BYT".

**Các bước:**
1. Mở phiếu đang *Clinical Hold*
2. Vào tab **Tài liệu** → hàng "Giấy phép lưu hành BYT"
3. Upload file giấy phép (từ Bộ Y tế), điền số hiệu + ngày hết hạn
4. Bấm **"Gỡ Clinical Hold"** → phiếu chuyển sẵn sàng để Ban GĐ duyệt

---

### e. Ban Giám Đốc — Phê duyệt phát hành

**Khi nào làm?** Khi nhận thông báo "Phiếu nghiệm thu chờ phê duyệt BGĐ".

**Các bước:**
1. Mở phiếu đang *Sẵn sàng phát hành*
2. Xem tóm tắt: hồ sơ, baseline tests, SN, QR
3. Điền tên vào **Người phê duyệt BGĐ** và ghi chú (nếu cần)
4. Bấm **"Phê duyệt phát hành"**
5. Thiết bị tự động tạo trong hệ thống với trạng thái **Active** — sẵn sàng lâm sàng

## I.6. Bảng Điều Khiển (Dashboard)

Vào **Lắp đặt → Dashboard** để xem tổng quan:

| KPI | Ý nghĩa | Trend tốt |
|---|---|---|
| **Phiếu đang mở** | Số phiếu chưa kết thúc (không tính Vendor Return) | Theo kế hoạch mua sắm |
| **Quá hạn > 30 ngày** | Phiếu nhận hàng nhưng chưa nghiệm thu > 30 ngày | ↓ Giảm |
| **Clinical Hold** | Phiếu đang chờ QA upload giấy phép | ↓ Giảm nhanh |
| **Tháng này: đã phát hành** | Số thiết bị vào vận hành tháng hiện tại | Theo kế hoạch |
| **Tỷ lệ Return To Vendor** | % phiếu kết thúc bằng trả hàng | ↓ Giảm |

Bấm vào KPI card để xem danh sách chi tiết. Bấm vào tên phiếu để mở chi tiết.

## I.7. Câu Hỏi Thường Gặp

**Q: Tôi không thấy nút "Tạo mới" trong module Lắp đặt?**
> A: Nút Tạo mới chỉ hiển thị với role Nhân viên TBYT. Nếu bạn là Kỹ sư Biomed, bạn có thể mở và chỉnh sửa phiếu nhưng không tạo mới. Liên hệ Trưởng xưởng nếu cần.

**Q: Hệ thống báo "Serial đã được gán cho thiết bị khác" khi nhập SN?**
> A: Mỗi serial chỉ được gán cho 1 thiết bị. Kiểm tra lại nhãn trên thân máy. Nếu serial đúng mà vẫn lỗi, liên hệ CMMS Admin để xem lịch sử thiết bị cũ có cùng SN.

**Q: Checklist có mục không áp dụng (N/A) cho thiết bị của tôi?**
> A: Chọn "N/A" cho mục không áp dụng — hệ thống sẽ tính là đạt. Chỉ chọn N/A khi thực sự không áp dụng (vd: thiết bị chạy pin không có dây tiếp đất).

**Q: Thiết bị Class C của tôi đã qua tất cả kiểm tra nhưng hệ thống không cho phép duyệt?**
> A: Thiết bị Class C tự động vào "Clinical Hold" theo quy định NĐ 98/2021. Cần QA Officer upload Giấy phép lưu hành Bộ Y tế trước khi phê duyệt. Liên hệ phòng QLCL.

**Q: Vendor báo DOA nhưng thiết bị vẫn có thể sửa được — có thể bỏ qua NC không?**
> A: Không. Mọi DOA/NC phải được tạo và xử lý theo quy trình. Sau khi NC đóng với kết quả "Khắc phục xong" thì phiếu mới được tiếp tục. Liên hệ Trưởng xưởng để xử lý.

**Q: Tôi muốn hủy phiếu sau khi đã lắp đặt xong nhưng hệ thống không cho?**
> A: Nếu thiết bị đã được phát hành (Asset đã tạo), không thể hủy phiếu. Nếu chưa phát hành, liên hệ Trưởng xưởng (role Workshop Head) để thực hiện hủy.

**Q: Quét barcode USB nhưng SN không điền vào ô?**
> A: Đảm bảo cửa sổ trình duyệt đang active (click vào trang trước khi quét). Scanner USB HID sẽ điền vào trường đang focus. Thử click vào trang rồi quét lại.

## I.8. Phím Tắt & Mã Trạng Thái

| Phím | Chức năng |
|---|---|
| `⌘K` / `Ctrl+K` | Tìm kiếm nhanh toàn hệ thống |
| `Esc` | Đóng popup / hủy thao tác hiện tại |
| `Tab` | Chuyển sang trường kế tiếp trong form |
| `Ctrl+S` | Lưu bản nháp |

**Cheat sheet trạng thái phiếu:**

| Trạng thái | Ý nghĩa | Ai làm gì tiếp? |
|---|---|---|
| Nháp | Phiếu vừa tạo | TBYT: Gửi kiểm tra tài liệu |
| Chờ kiểm tra tài liệu | Đang upload CO/CQ/Manual/License | TBYT: Upload đủ tài liệu |
| Chờ lắp đặt | Tài liệu đủ, sẵn sàng lắp | Biomed/Vendor: Bắt đầu lắp đặt |
| Đang lắp đặt | Đang lắp đặt thực tế | Biomed/Vendor: Hoàn thành |
| Định danh | Gán SN và QR | Biomed: Xác nhận định danh |
| Kiểm tra ban đầu | Đo baseline | Biomed: Nộp kết quả |
| Không phù hợp | Có lỗi/DOA cần xử lý | Biomed/Vendor: Khắc phục |
| Clinical Hold | Chờ giấy phép BYT | QA Officer: Upload + Gỡ hold |
| Tái kiểm | Baseline fail, đang sửa | Biomed: Sửa và tái kiểm |
| Sẵn sàng phát hành | Chờ BGĐ duyệt | BGĐ: Phê duyệt |
| Đã phát hành | Asset Active — dùng được | — |
| Trả hàng Vendor | TERMINAL — không dùng | — |

## I.9. Liên Hệ Hỗ Trợ

| Vấn đề | Liên hệ |
|---|---|
| Không đăng nhập được, quên mật khẩu | IT Helpdesk: ext. 1234 hoặc it@hospital.vn |
| Lỗi hiển thị, tính năng không hoạt động | Support AssetCore: support@assetcore.vn |
| Câu hỏi quy trình nghiệm thu | Trưởng xưởng VTTBYT |
| Câu hỏi về giấy phép BYT, Clinical Hold | Phòng QLCL |
| Khẩn cấp (thiết bị khoa ICU/OR cần gấp) | Hotline: 0903.xxx.xxx (24/7) |

## I.10. Lịch Sử Cập Nhật Tài Liệu

| Phiên bản | Ngày | Thay đổi | Owner |
|---|---|---|---|
| 2.0.0 | 2026-05-08 | Phát hành lần đầu — Module IMM-04 Wave 1 GA | BA Lead |

---

# Phần II — Release Notes

## II.1. Tóm Tắt

Phiên bản 2.0.0 (2026-05-08) đưa module **Lắp đặt, Định danh & Kiểm tra Ban đầu (IMM-04)** vào vận hành chính thức. Module là **cổng vào** của toàn bộ vòng đời thiết bị y tế — không có phiếu IMM-04 được duyệt, thiết bị không tồn tại trên hệ thống và không được phép sử dụng lâm sàng. Downtime dự kiến 30-60 phút trong cửa sổ bảo trì đêm.

## II.2. Tính Năng Mới

### Quản lý Phiếu Nghiệm Thu (Nhân viên TBYT + Kỹ sư Biomed)

Tạo và theo dõi phiếu nghiệm thu với 11 trạng thái workflow từ nhận hàng đến phát hành. Mỗi phiếu truy xuất ngược về Đơn Mua Hàng gốc.

- Tạo phiếu từ PO với auto-fill đầy đủ thông tin
- Bộ tài liệu bắt buộc (CO/CQ/Manual/License) tự sinh theo loại thiết bị
- Gate G01: block tiến trình nếu thiếu tài liệu bắt buộc
- Upload file PDF (tối đa 20 MB), auto-validate ngày hết hạn

[→ Hướng dẫn: §I.5.a]

### Định danh Thiết bị (Kỹ sư Biomed)

Gán Serial Number duy nhất toàn hệ thống và mã QR nội bộ. Hỗ trợ quét barcode USB HID để điền SN tự động.

- VR-01: kiểm tra SN unique tức thì khi nhập
- Mã QR sinh định dạng `BV-{DEPT}-{YYYY}-{SEQ}`
- Barcode lookup API để tra cứu thiết bị qua QR code

[→ Hướng dẫn: §I.5.b]

### Đo kiểm An toàn Điện Baseline (Kỹ sư Biomed)

Hệ thống checklist đo kiểm có thể cấu hình theo từng loại thiết bị. Gate G03 đảm bảo 100% mục quan trọng đạt trước khi phát hành.

- Template checklist per loại thiết bị (Medical Imaging, Life Support, ...)
- Phân biệt mục quan trọng (critical) và không quan trọng
- Checklist bị khóa sau khi nộp — không thể sửa (audit trail)
- Auto-chuyển Re Inspection nếu có mục critical fail

[→ Hướng dẫn: §I.5.b đoạn Baseline]

### Clinical Hold & Kiểm soát Giấy phép BYT (QA Officer)

Thiết bị Class C, D, và bức xạ tự động vào trạng thái Clinical Hold sau khi qua baseline. Chỉ khi QA Officer xác nhận giấy phép Bộ Y tế hợp lệ thì mới được phép tiến đến phê duyệt.

- Auto-hold theo risk_class (VR-07) — không thể bypass
- GW-2 gate: block phát hành nếu thiếu `Active` document trong IMM-05
- Thông báo tự động gửi QA Officer khi vào Clinical Hold

[→ Hướng dẫn: §I.5.d]

### Phê duyệt BGĐ & Tạo Asset Chính thức (Ban Giám Đốc)

Gate G06 yêu cầu chữ ký số của Ban Giám Đốc trước khi thiết bị chính thức vào hệ thống. Sau khi phê duyệt, Asset tự động tạo và bộ hồ sơ ban đầu chuyển sang IMM-05.

- Bắt buộc board_approver (G06) — không thể Submit nếu thiếu
- Gate G05: block release nếu còn Non Conformance chưa đóng
- On-submit: tạo ERPNext Asset, import sang IMM-05, bắn event cho IMM-08 (PM listener sẽ có trong Wave 2)

[→ Hướng dẫn: §I.5.e]

## II.3. Cải Tiến

| Mô tả | Module | Tác động |
|---|---|---|
| Asset status phản ánh thực tế ngay khi phát hành | IMM-00 Integration | Dashboard tổng hợp luôn đúng |
| Auto-import hồ sơ ban đầu sang IMM-05 | IMM-05 | Không cần tạo lại Document Set thủ công |
| Scheduler cảnh báo phiếu mở > 30 ngày | IMM-04 | Workshop Head nhận email hàng ngày |

## II.4. Sửa Lỗi

| Mã issue | Mô tả | Severity |
|---|---|---|
| (Module mới — không có bug fix release này) | — | — |

## II.5. Thay Đổi Không Backward-compat

Không có thay đổi breaking cho người dùng hiện tại. Module IMM-04 là module mới hoàn toàn.

Lưu ý: sau khi deploy, **không thể tạo Asset ERPNext trực tiếp** cho thiết bị y tế (BR-04-01 enforce). Mọi Asset mới phải qua phiếu IMM-04.

## II.6. Deprecations

Không có.

## II.7. Yêu Cầu Nâng Cấp

**Stack version:** Không thay đổi (Frappe v15, Python 3.11, Node 20). Cần cài thêm Python library `qrcode ≥ 7.4`.

**Migration tự động:** Patch `v2_0.*` chạy tự động khi `bench migrate`. Xem chi tiết §I.3 trong `08_Deployment.md`.

**Training bắt buộc:** 6 role phải hoàn tất training trước khi sử dụng. Thời lượng 1-3 giờ tùy role. Xem `08_Deployment.md §II.7`.

## II.8. Downtime / Compatibility / Known Issues

**Downtime:** 30-60 phút trong maintenance window 23:00-02:00 ngày deploy.

**Khả năng tương thích:**

| Môi trường | Hỗ trợ |
|---|---|
| Chrome ≥ 120 | ✅ |
| Edge ≥ 120 | ✅ |
| Firefox ≥ 121 | ✅ |
| Safari ≥ 17 | ✅ |
| Mobile (responsive) | ✅ (giới hạn — tablet khuyến nghị cho checklist) |

**Known issues:**

| Vấn đề | Workaround | Fix dự kiến |
|---|---|---|
| PM auto-create sau Clinical Release chưa có listener IMM-08 (TC-32 FAIL) | Workshop Head tạo PM Plan thủ công trong IMM-08 | Wave 2 — IMM-08 |
| PDF Print Format "Biên bản Bàn giao" chưa config | Export CSV hoặc chụp màn hình | v2.1.0 |
| QR label PDF chưa có server-side render | FE render + print từ browser | v2.1.0 |

## II.9. Liên Kết & Lịch Sử Versioning

- User Guide: §I file này
- Functional Specs: [IMM-04_Functional_Specs.md](./IMM-04_Functional_Specs.md)
- Deployment Plan: [08_Deployment.md](./08_Deployment.md)
- Báo lỗi: `support@assetcore.vn` hoặc GitHub Issues

| Version | Ngày | Nội dung |
|---|---|---|
| 2.0.0 | 2026-05-08 | IMM-04 General Availability — Wave 1 |

---

# Phần III — Traceability Matrix

## III.1. Cách Dùng

- Mỗi User Story / Business Rule / Compliance requirement có 1 dòng.
- Cell phải trỏ đến artefact cụ thể (file/function/test ID/PR).
- Cập nhật xuyên suốt lifecycle; chốt cột `Released-in` khi release.
- Status: ⬜ Not started · 🟡 In progress · 🟠 Blocked · ✅ Done · ❌ Cancelled

## III.2. Matrix Chính

| Req ID | Loại | Mô tả ngắn | Doc ref | Design / Code | Test ID | UAT ID | PR | Released in | Status |
|---|---|---|---|---|---|---|---|---|---|
| US-04-01 | Story | Tạo Commissioning từ PO | Func Specs §3.1 | `services/imm04.py: initialize_commissioning()` | `TestInitializeCommissioning: test_class_c_adds_license` | UAT-IMM04-01 | #imm04-core | v2.0.0 | ✅ |
| US-04-02 | Story | VR-01 block SN trùng | Func Specs §3.2 | `services/imm04.py: _vr01_unique_serial_number()` | `TestUniqueSerial: test_duplicate_sn_raises` | UAT-IMM04-04 | #imm04-core | v2.0.0 | ✅ |
| US-04-03 | Story | Gate G01 block thiếu tài liệu | Func Specs §3.3 | `services/imm04.py: validate_gate_g01()` | `TestGateG01: test_gate_g01_fail_one_pending` | UAT-IMM04-03 | #imm04-core | v2.0.0 | ✅ |
| US-04-04 | Story | Baseline fail → Re Inspection | Func Specs §3.4 | `services/imm04.py: validate_gate_g03()` | `TestGateG03: test_critical_fail_raises` | UAT-IMM04-05 | #imm04-core | v2.0.0 | ✅ |
| US-04-05 | Story | Clinical Hold Class C/D/Radiation | Func Specs §3.5 | `services/imm04.py: check_auto_clinical_hold()` | `TestRadiationHold: test_class_c_returns_true` | UAT-IMM04-06 | #imm04-core | v2.0.0 | ✅ |
| US-04-06 | Story | Clinical Release tạo Asset + downstream | Func Specs §3.6 | `services/imm04.py: create_erpnext_asset()`, `create_initial_document_set()` | `test_on_submit_mints_asset`, `test_on_submit_creates_document_set` | UAT-IMM04-08 | #imm04-core | v2.0.0 | ✅ |
| US-04-07 | Story | DOA → Non Conformance → Return To Vendor | Func Specs §3.7 | Workflow transition + NC DocType | `TestWorkflow: test_doa_to_return_vendor` | UAT-IMM04-09 | #imm04-core | v2.0.0 | ✅ |
| US-04-08 | Story | Block cancel khi Asset đã tạo | Func Specs §3.8 | `services/imm04.py: handle_commissioning_cancel()` | `test_on_cancel_blocked_if_asset_exists` | UAT-IMM04 (edge) | #imm04-core | v2.0.0 | ✅ |
| BR-04-01 | Rule | Asset chỉ tạo qua IMM-04 pipeline | Module Overview §8 | `AssetCommissioning.on_submit: mint_core_asset()` | `test_block_direct_asset_creation` | UAT-IMM04-02 | #imm04-core | v2.0.0 | ✅ |
| BR-04-02 | Rule | G01: CO/CQ/Manual Received/Waived | Module Overview §8 | `validate_gate_g01()` before transition | `TestGateG01: test_gate_g01_fail_one_pending` | UAT-IMM04-03 | #imm04-core | v2.0.0 | ✅ |
| BR-04-03 | Rule | VR-01: vendor_serial_no unique | Module Overview §8 | `_vr01_unique_serial_number()` validate | `TestUniqueSerial: test_duplicate_sn_raises` | UAT-IMM04-04 | #imm04-core | v2.0.0 | ✅ |
| BR-04-04 | Rule | G03: 100% baseline Pass/N/A | Module Overview §8 | `validate_gate_g03()` before submit | `TestGateG03: test_critical_fail_raises` | UAT-IMM04-05 | #imm04-core | v2.0.0 | ✅ |
| BR-04-05 | Rule | VR-07: auto Clinical Hold C/D/Radiation | Module Overview §8 | `check_auto_clinical_hold()` + workflow | `TestRadiationHold: test_class_d_returns_true` | UAT-IMM04-06 | #imm04-core | v2.0.0 | ✅ |
| BR-04-06 | Rule | G05: No Open NC trước Release | Module Overview §8 | `validate_gate_g05_g06()` | `TestGateG05G06: test_open_nc_raises` | UAT-IMM04-07 | #imm04-core | v2.0.0 | ✅ |
| BR-04-07 | Rule | G06: board_approver bắt buộc | Module Overview §8 | `validate_gate_g05_g06()` | `TestGateG05G06: test_no_approver_raises` | UAT-IMM04-07 | #imm04-core | v2.0.0 | ✅ |
| BR-04-08 | Rule | GW-2: Active IMM-05 doc hoặc Exempt | Module Overview §8 | `_gw2_check_document_compliance()` | `test_gw2_block_without_active_doc` | UAT-IMM04-08 | #imm04-core | v2.0.0 | ✅ |
| NĐ98/Điều 12 | Compliance | CO/CQ bắt buộc khi nhập khẩu | 08 §II.2 | BR-04-02: `validate_gate_g01()` | UAT-IMM04-03 | UAT-IMM04-03 | #imm04-core | v2.0.0 | ✅ |
| NĐ98/Điều 18 | Compliance | Giấy phép lưu hành Class C/D | 08 §II.2 | BR-04-05 + GW-2 | UAT-IMM04-06 | UAT-IMM04-06 | #imm04-core | v2.0.0 | ✅ |
| WHO HTM §3.2 | Compliance | UDI/serial tracking | 08 §II.2 | BR-04-03: `_vr01_unique_serial_number()` | `TestUniqueSerial` | UAT-IMM04-04 | #imm04-core | v2.0.0 | ✅ |
| WHO HTM §5.1.2 | Compliance | Incoming inspection baseline | 08 §II.2 | BR-04-04: `validate_gate_g03()` | `TestGateG03` | UAT-IMM04-05 | #imm04-core | v2.0.0 | ✅ |
| ISO 13485 §7.5 | Compliance | Asset qua pipeline có kiểm soát | 08 §II.2 | BR-04-01 on_submit | `test_on_submit_mints_asset` | UAT-IMM04-02 | #imm04-core | v2.0.0 | ✅ |
| ISO 13485 §8.3 | Compliance | NC phải đóng trước release | 08 §II.2 | BR-04-06: G05 | `TestGateG05G06: test_open_nc_raises` | UAT-IMM04-07 | #imm04-core | v2.0.0 | ✅ |
| SEC-IMM04-01 | Security | VR-06: lifecycle event immutable | 07 §III.3 | `_vr06_immutable_lifecycle_events()` | `test_vr06_immutable_lifecycle_event` | UAT-IMM04-10 | #imm04-core | v2.0.0 | ✅ |
| SEC-IMM04-02 | Security | Vendor chỉ thấy state Installing/TBI | 07 §III.1 | DocPerm + workflow role check | `test_permission_vendor_scope` | UAT-IMM04-11 | #imm04-core | v2.0.0 | ✅ |

## III.3. Reverse Lookup

| Test ID | Requirement(s) cover |
|---|---|
| `test_block_direct_asset_creation` | BR-04-01, ISO 13485 §7.5 |
| `TestGateG01: test_gate_g01_fail_one_pending` | US-04-03, BR-04-02, NĐ98/Điều 12 |
| `TestUniqueSerial: test_duplicate_sn_raises` | US-04-02, BR-04-03, WHO HTM §3.2 |
| `TestGateG03: test_critical_fail_raises` | US-04-04, BR-04-04, WHO HTM §5.1.2 |
| `TestRadiationHold: test_class_c_returns_true` | US-04-05, BR-04-05, NĐ98/Điều 18 |
| `TestGateG05G06: test_open_nc_raises` | BR-04-06, ISO 13485 §8.3 |
| `TestGateG05G06: test_no_approver_raises` | BR-04-07 |
| `test_on_submit_mints_asset` | US-04-06, BR-04-01 |
| `test_vr06_immutable_lifecycle_event` | SEC-IMM04-01 |
| `test_permission_vendor_scope` | SEC-IMM04-02 |

## III.4. Coverage Gaps

Sau rà soát matrix, không có req Must/Should còn ⬜ trước v2.0.0. Gaps roadmap:

| Req ID | Thiếu gì? | Owner | Deadline |
|---|---|---|---|
| PM auto-create (TC-32) | IMM-08 listener chưa implement | Dev IMM-08 | Wave 2 |
| PDF Print Format | Print Format config chưa có | Dev/BA | v2.1.0 |
| QR label PDF server-side | Server-side render | Dev FE | v2.1.0 |
| Rate limit `approve_clinical_release` | Security roadmap | DevOps | v2.1.0 |
| Pentest report `docs/security/` | Report chưa upload | Security | Trước go-live |

## III.5. Cập Nhật Quy Ước

| Khi | Ai update | Cell nào |
|---|---|---|
| Có req mới (User Story / BR) | BA Lead | Thêm dòng, điền `Req ID`, `Loại`, `Mô tả`, `Doc ref` |
| Design xong | Tech Lead | Điền `Design / Code` (file:function) |
| PR merged | Dev | Điền `PR` |
| Test case viết xong | Dev/QA | Điền `Test ID` |
| UAT pass | QA Lead | Điền `UAT ID` + status ✅ |
| Release | PM | Điền `Released-in` + chốt status |

## III.6. Audit-readiness — Quick Links

**Auditor hỏi:** "Làm sao chứng minh thiết bị X-ray phòng CDHA đã qua kiểm tra an toàn điện?"

Trace: `Asset.custom_comm_ref → Asset Commissioning ACC-2026-00023 → tab Checklist → CHK-ELEC-001/002/003 all Pass → actor=biomed.nguyen + timestamp`

---

**Auditor hỏi:** "Giấy phép lưu hành Bộ Y tế của máy CT có còn hiệu lực không?"

Trace: `Asset Commissioning ACC-... → tab Documents → row License → expiry_date = 2028-06-30 → IMM-05: DOC-AC-...-2026-00001 status=Active`

---

**Auditor hỏi:** "Ai đã phê duyệt thiết bị này được đưa vào sử dụng?"

Trace: `Asset Commissioning → board_approver = ceo.nguyen + approval_date → Lifecycle Event event_type=released → IMM Audit Trail hash chain`

## III.7. Bảng Thống Kê Thông Tin Ứng Dụng

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| DocType (chính) | 2 | `Asset Commissioning`, `Asset QA Non Conformance` |
| DocType (child) | 3 | `Commissioning Checklist`, `Commissioning Document Record`, `Asset Lifecycle Event` |
| Workflow JSON | 1 | `IMM-04 Workflow` — 11 states, 15+ transitions |
| Gate | 6 | G01 → G06 |
| Validation Rule | 7 | VR-01 → VR-07 |
| API endpoint | 33 | Đầy đủ trong `05_API_Specification.md` §0 — incl. `get_form_context, list_commissioning, create_commissioning, submit_commissioning, transition_state, assign_identification, submit_baseline_checklist, clear_clinical_hold, retry_mint_asset, approve_clinical_release, submit_for_approval, approve_pending, create_from_purchase, get_lifecycle_timeline, ...` |
| FE view / page | 6+ | CommissioningList, CommissioningDetail, CommissioningCreate, CommissioningChecklist, CommissioningDocs, Dashboard |
| Service function | 12 | `initialize_commissioning, validate_gate_g01/g03/g05_g06, check_auto_clinical_hold, mint_core_asset, ...` |
| Scheduler job | 3 | Daily overdue check, Clinical Hold aging, SLA check |
| Business Rule | 8 | BR-04-01 → BR-04-08 |
| Role áp dụng | 7 | HTM Technician, Biomed Engineer, Vendor Engineer, QA Officer, Workshop Head, VP Block2, CMMS Admin |
| Test case unit | ~40 | 12 test class × ~3-4 case avg |
| UAT scenario | 12 | UAT-IMM04-01 → 12 |
| UAT PASS | 31/32 | TC-32 (PM auto-create) FAIL — known, deferred |
| LOC BE (`services/imm04.py`) | 1692 | Wave-2 hardening đã ship |
| LOC API (`api/imm04.py`) | 309 | 33 endpoints (whitelist count, 2026-05-14) |
| Sprint hoàn thành (Wave 1) | 4 | Sprint 1-4, mỗi sprint 2 tuần |
| User Story | 8 | US-04-01 → 04-08 |

---

## DoD — Hoàn chỉnh

### I. User Guide
- [x] Tiếng Việt 100%, không jargon
- [x] Mô tả tất cả 6 role với hướng dẫn step-by-step
- [x] Dashboard KPI có giải thích trend
- [x] FAQ 7 câu thực tế
- [x] Cheat sheet trạng thái 11 state + phím tắt
- [ ] ≥ 5 screenshot UI thực tế (cần chụp trên staging trước go-live)
- [ ] Reviewed bởi BA + đại diện end-user (HTM Officer)

### II. Release Notes
- [x] Tóm tắt 2-3 câu user-friendly
- [x] 5 tính năng mới có role hưởng lợi
- [x] Known issues + workaround documented (TC-32, PDF format)
- [x] Breaking change: documented (không tạo Asset trực tiếp)
- [x] Downtime và compatibility table
- [ ] Reviewed bởi PM + Tech Lead + BA

### III. Traceability Matrix + Bảng Thống Kê
- [x] 24 dòng: 8 User Story + 8 BR + 5 Compliance + 2 Security
- [x] Mọi dòng ✅ có ≥ 4 cell điền
- [x] Reverse lookup table
- [x] Coverage gaps liệt kê (5 gaps, đều là roadmap)
- [x] Bảng thống kê 15 hạng mục
- [ ] Reviewed bởi PM + Tech Lead + QA Lead
