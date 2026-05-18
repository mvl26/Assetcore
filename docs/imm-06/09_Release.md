# IMM-06 — Phát hành (User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | **IMM-06 — Đào tạo & Quản lý Năng lực (Training & Competency)** |
| Phiên bản | 1.0.0 |
| Ngày phát hành | 2026-05-08 |
| Owner | PM + BA + Tech Writer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) · [Functional Specs](./IMM-06_Functional_Specs.md) |

---

# Phần I — Hướng Dẫn Sử Dụng

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.

## I.1. Giới Thiệu

Module **Đào tạo & Năng lực (IMM-06)** giúp quản lý toàn bộ quá trình đào tạo nhân viên sử dụng thiết bị y tế và theo dõi năng lực vận hành của từng người.

Mọi thao tác — từ lập kế hoạch đào tạo, tổ chức buổi học, cấp chứng nhận năng lực, đến gia hạn hoặc thu hồi khi cần — đều được ghi lại đầy đủ. Hệ thống tự động cảnh báo khi năng lực sắp hết hạn và ngăn chặn kỹ thuật viên chưa được chứng nhận thực hiện bảo trì thiết bị Class II/III.

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
- **② Sidebar**: Menu module. Tìm **"Đào tạo"** hoặc **"Training"** để vào IMM-06.
- **③ Vùng chính**: Danh sách chương trình, lịch đào tạo, hồ sơ năng lực, hoặc Dashboard.
- **Chấm màu xanh lá** ở sidebar = Module Đào tạo đang active.

## I.3. Các Vai Trò

| Vai trò | Bạn làm gì trong module này? |
|---|---|
| **Tổ HC-QLCL (Phụ trách đào tạo)** | Tạo chương trình đào tạo, lập lịch buổi học, theo dõi kết quả, thu hồi/tạm ngưng năng lực khi cần |
| **Kỹ sư y sinh (Biomed Engineer)** | Làm giảng viên, chấm điểm học viên, hoàn tất buổi học |
| **KTV HTM / Người vận hành** | Tham gia đào tạo, xem hồ sơ năng lực và chứng nhận của chính mình |
| **Trưởng khoa / Quản lý khoa** | Phê duyệt (sign-off) năng lực cho nhân viên thuộc khoa mình |
| **Trưởng phân xưởng** | Xác nhận buổi đào tạo đã hoàn thành, xem báo cáo gap năng lực toàn viện |
| **Phó Trưởng phòng VTTBYT** | Theo dõi Dashboard KPI, nhận báo cáo gap hàng tuần |

## I.4. Quy Trình Chính

```
① Lập chương trình đào tạo
   (Tổ HC-QLCL)
      │
      ▼
② Lập lịch buổi đào tạo + Mời học viên
   (Tổ HC-QLCL)
      │
      ▼
③ Xác nhận buổi học
   (Tổ HC-QLCL)
      │
      ▼
④ Bắt đầu giảng dạy
   (Giảng viên / Biomed Engineer)
      │
      ▼
⑤ Chấm điểm + Hoàn tất buổi học
   (Giảng viên)
      │
      ▼
⑥ Hồ sơ năng lực tự sinh cho người Đạt
   (Hệ thống)
      │
      ▼
⑦ Phê duyệt (sign-off) → Năng lực Active
   (Trưởng khoa / Quản lý khoa)
      │
      ▼
⑧ Hệ thống cảnh báo sắp hết hạn (90/60/30 ngày)
   (Scheduler tự động)
      │
      ├──► ⑨ Tổ chức đào tạo tái chứng nhận
      └──► ⑩ Thu hồi nếu cần (Tổ HC-QLCL)
```

## I.5. Thao Tác Theo Vai Trò

### a. Tổ HC-QLCL — Tạo chương trình đào tạo

**Khi nào làm?** Khi có thiết bị mới về, khi tài liệu kỹ thuật thay đổi, hoặc khi cần tổ chức đào tạo tái chứng nhận.

**Tạo Chương trình đào tạo (Training Program):**
1. Vào menu **Đào tạo → Chương trình đào tạo** → bấm **"Tạo mới"**
2. Điền **Mã chương trình** (ví dụ: `TRN-MON-INIT-01`)
3. Chọn **Thiết bị** áp dụng, loại đào tạo (Ban đầu / Tái chứng nhận / Nâng cao)
4. Điền thời lượng, hiệu lực (mặc định 24 tháng), điểm đạt (mặc định 70%)
5. Bấm **"Lưu"** — Chương trình sẵn sàng cho buổi đào tạo

> ⚠️ **Lưu ý:** Nếu sửa điểm đạt hoặc nội dung quan trọng → hệ thống cảnh báo yêu cầu tái chứng nhận toàn bộ người đang có năng lực.

---

**Lập lịch buổi đào tạo (Training Session):**
1. Vào **Đào tạo → Buổi đào tạo** → bấm **"Tạo mới"**
2. Chọn **Chương trình đào tạo** → hệ thống tự điền thông tin
3. Điền ngày, địa điểm, giảng viên
4. Thêm danh sách học viên vào bảng **Học viên**
5. Bấm **"Lưu"** — Buổi học ở trạng thái *Đã lên kế hoạch*
6. Bấm **"Xác nhận"** → email thông báo gửi học viên

### b. Giảng viên (Biomed Engineer) — Chấm điểm và hoàn tất

**Khi nào làm?** Sau khi buổi đào tạo kết thúc thực tế.

**Các bước:**
1. Đăng nhập, vào **Đào tạo → Buổi đào tạo** → tìm buổi học được phân công
2. Bấm **"Bắt đầu"** → trạng thái chuyển sang *Đang diễn ra*
3. Vào tab **Học viên**, điền cho từng người:
   - Tỷ lệ tham dự (%)
   - Điểm lý thuyết
   - Điểm thực hành
   - Hệ thống tự tính Đạt/Không đạt
4. Bấm **"Hoàn tất buổi học"** — hồ sơ năng lực tự sinh cho người Đạt

> 💡 **Mẹo:** Người có tỷ lệ tham dự < 80% tự động Không đạt dù điểm cao.

### c. Trưởng khoa / Quản lý khoa — Phê duyệt năng lực

**Khi nào làm?** Sau khi nhận thông báo có nhân viên vừa hoàn thành đào tạo.

**Các bước:**
1. Vào **Đào tạo → Hồ sơ năng lực** → filter *Chờ phê duyệt*
2. Mở hồ sơ của nhân viên thuộc khoa mình
3. Kiểm tra thông tin điểm số, ngày đạt
4. Bấm **"Phê duyệt"** → Năng lực chuyển sang *Đang hoạt động*
5. Nhân viên nhận email xác nhận

> ⚠️ **Lưu ý:** Bạn chỉ phê duyệt được nhân viên thuộc khoa của mình.

### d. KTV HTM / Người vận hành — Xem hồ sơ cá nhân

**Khi nào làm?** Bất kỳ lúc nào muốn xem chứng nhận hoặc kiểm tra thời hạn.

**Các bước:**
1. Vào menu **Đào tạo → Hồ sơ của tôi** (hoặc `/me/competencies`)
2. Xem danh sách thiết bị bạn được phép vận hành
3. Kiểm tra ngày hết hạn — màu vàng = sắp hết hạn (≤ 90 ngày), đỏ = đã hết hạn
4. Bấm **"Tải chứng nhận"** để lưu PDF

> 💡 **Mẹo:** Hệ thống tự động nhắc nhở qua email khi năng lực còn 90, 60, 30 ngày.

## I.6. Bảng Điều Khiển (Dashboard)

Vào **Đào tạo → Dashboard** để xem tổng quan:

| Chỉ số | Ý nghĩa | Trend tốt |
|---|---|---|
| **% Nhân viên có năng lực (per khoa)** | Tỷ lệ nhân viên đủ điều kiện vận hành | ↑ Tăng |
| **Sắp hết hạn (90 ngày)** | Số năng lực cần gia hạn trong 90 ngày tới | ↓ Giảm |
| **Tỷ lệ hoàn thành đào tạo** | % học viên hoàn thành trong kỳ | ↑ Tăng |
| **Tỷ lệ đạt trung bình** | % học viên đạt điểm qua kỳ | ↑ Tăng |
| **Báo cáo gap Class III** | Số khoa thiếu đủ 2 operator cho Class III | ↓ Giảm về 0 |

Bảng **Gap Năng lực** (ma trận khoa × phân loại thiết bị): click ô có gap để xem danh sách thiết bị bị ảnh hưởng.

## I.7. Câu Hỏi Thường Gặp

**Q: Tôi vừa hoàn thành buổi đào tạo nhưng chưa thấy hồ sơ năng lực?**
> A: Hồ sơ năng lực chỉ tạo khi Giảng viên bấm "Hoàn tất buổi học" và bạn ở diện Đạt. Nếu đã đợi > 30 phút mà chưa có, liên hệ Tổ HC-QLCL để kiểm tra kết quả buổi học.

**Q: Hồ sơ năng lực của tôi ở trạng thái "Chờ phê duyệt" lâu quá?**
> A: Cần Trưởng khoa phê duyệt. Nhắc nhở Trưởng khoa hoặc liên hệ Tổ HC-QLCL để hỗ trợ.

**Q: Tôi nhận email cảnh báo hết hạn nhưng chưa có lịch tái chứng nhận?**
> A: Hệ thống tự tạo buổi học tái chứng nhận dự kiến 60 ngày trước ngày hết hạn. Liên hệ Tổ HC-QLCL nếu chưa thấy lịch.

**Q: Năng lực của tôi bị "Đình chỉ" / "Thu hồi" — tôi cần làm gì?**
> A: Liên hệ ngay Tổ HC-QLCL hoặc Trưởng phân xưởng để biết lý do và hướng xử lý. Trong thời gian đình chỉ/thu hồi, bạn không được giao phiếu bảo trì hay sửa chữa thiết bị loại II/III.

**Q: Tôi muốn xem danh sách thiết bị mình được phép vận hành?**
> A: Vào **Hồ sơ của tôi** — danh sách tất cả thiết bị có năng lực Active sẽ hiển thị.

**Q: Dashboard hiển thị số gap nhưng tôi không biết gap ở khoa nào?**
> A: Click vào ô màu đỏ trong bảng "Gap Năng lực" → danh sách khoa và thiết bị vi phạm hiện ngay.

**Q: Tôi là Biomed Engineer và quên nhập điểm cho 1 học viên. Có sửa được không?**
> A: Khi buổi học còn ở trạng thái *Đang diễn ra*, bạn có thể chỉnh sửa bảng điểm. Sau khi bấm "Hoàn tất", liên hệ Tổ HC-QLCL hoặc CMMS Admin để hỗ trợ.

## I.8. Phím Tắt & Mã Trạng Thái

| Phím | Chức năng |
|---|---|
| `⌘K` / `Ctrl+K` | Tìm kiếm nhanh toàn hệ thống |
| `Esc` | Đóng popup / hủy thao tác hiện tại |
| `Tab` | Chuyển sang trường kế tiếp trong form |
| `Ctrl+S` | Lưu bản nháp |

**Cheat sheet trạng thái buổi đào tạo:**

| Trạng thái | Ý nghĩa |
|---|---|
| Đã lên kế hoạch | Buổi học vừa tạo, chưa xác nhận |
| Đã xác nhận | Đã xác nhận, email gửi học viên |
| Đang diễn ra | Buổi học đang chạy |
| Đã hoàn thành | Giảng viên đã chấm điểm xong |
| Đã xác nhận (Verified) | Trưởng phân xưởng xác nhận |
| Đã đóng | Lưu trữ, không thể sửa |
| Đã hủy | Buổi học bị hủy có lý do |

**Cheat sheet trạng thái năng lực:**

| Trạng thái | Ý nghĩa |
|---|---|
| Chờ phê duyệt | Vừa tốt nghiệp, chờ Trưởng khoa ký |
| Đang hoạt động | Được phép vận hành thiết bị |
| Sắp hết hạn | ≤ 90 ngày trước ngày hết hạn — cần gia hạn |
| Đã hết hạn | Không còn hiệu lực — cần tái chứng nhận |
| Đình chỉ tạm thời | Tạm ngưng có thể phục hồi |
| Đã thu hồi | Thu hồi vĩnh viễn — cần đào tạo lại từ đầu |

## I.9. Liên Hệ Hỗ Trợ

| Vấn đề | Liên hệ |
|---|---|
| Không đăng nhập được, quên mật khẩu | IT Helpdesk: ext. 1234 hoặc it@hospital.vn |
| Lỗi hiển thị, tính năng không hoạt động | Support AssetCore: support@assetcore.vn |
| Câu hỏi về chương trình đào tạo, lịch thi | Tổ HC-QLCL: qlcl@hospital.vn |
| Năng lực bị đình chỉ/thu hồi khẩn cấp | Trưởng phân xưởng: ext. 5678 (8h-17h) |

## I.10. Lịch Sử Cập Nhật Tài Liệu

| Phiên bản | Ngày | Thay đổi | Owner |
|---|---|---|---|
| 1.0.0 | 2026-05-08 | Phát hành lần đầu — Module IMM-06 GA (Wave 2) | BA Lead |

---

# Phần II — Release Notes

## II.1. Tóm Tắt

Phiên bản 1.1.0 (2026-05-08) đưa module **Đào tạo & Quản lý Năng lực (IMM-06)** vào vận hành chính thức trong Wave 2. Module đảm bảo mọi kỹ thuật viên và người vận hành thiết bị y tế đều có chứng nhận năng lực hợp lệ, tự động cảnh báo khi sắp hết hạn, và ngăn chặn phân công người không đủ năng lực vào phiếu bảo trì/sửa chữa. Downtime dự kiến 30-60 phút trong cửa sổ bảo trì đêm.

## II.2. Tính Năng Mới

### Quản lý chương trình đào tạo (Tổ HC-QLCL)

Tạo và quản lý chương trình đào tạo chuẩn theo từng dòng thiết bị. Thay đổi nội dung quan trọng tự động yêu cầu tái chứng nhận toàn bộ người có liên quan.

- Tạo Training Program với đánh giá lý thuyết + thực hành
- Lập lịch Training Session với nhiều học viên, giảng viên
- Quy trình phê duyệt 6 bước: Planned → Confirmed → In Progress → Completed → Verified → Closed
- Change control tự động khi sửa điểm đạt hoặc nội dung (BR-06-04)

[→ Hướng dẫn: §I.5.a]

### Hồ sơ năng lực tự động + phê duyệt (Tổ HC-QLCL + Trưởng khoa)

Hệ thống tự tạo hồ sơ năng lực cho học viên Đạt ngay sau khi buổi học hoàn tất. Trưởng khoa phê duyệt (sign-off) để kích hoạt.

- Auto-create Competency cho N học viên Đạt
- Sign-off theo phân cấp: Trưởng khoa chỉ ký cho nhân viên khoa mình
- Ngày hết hạn tự tính từ ngày đạt + hiệu lực chương trình
- Chứng nhận PDF lưu qua IMM-05 Document Repository

[→ Hướng dẫn: §I.5.b, §I.5.c]

### Cảnh báo hết hạn + tái chứng nhận tự động (Hệ thống tự động)

Scheduler chạy hàng ngày kiểm tra toàn bộ hồ sơ năng lực và gửi cảnh báo đúng thời điểm. 60 ngày trước hết hạn, hệ thống tự tạo buổi đào tạo tái chứng nhận dự kiến.

- Cảnh báo email mốc 90/60/30 ngày (cường độ tăng dần)
- Auto-expire khi quá ngày hết hạn → mất quyền vận hành ngay lập tức
- Auto-create Refresher Session 60 ngày trước hết hạn
- Idempotent: không gửi email trùng lặp cùng ngày

[→ Hướng dẫn: §I.5.d]

### Gate phân công KTV + Dashboard gap năng lực (Workshop Head + VP Block2)

Hệ thống tự động từ chối phân công kỹ thuật viên chưa đủ năng lực vào phiếu bảo trì (IMM-08), sửa chữa (IMM-09), hiệu chuẩn (IMM-11). Dashboard tuần xuất báo cáo gap khoa × phân loại thiết bị.

- Authorization gate: block assign khi competency Expired/Revoked/None
- Operator coverage gate: Class III cần ≥ 2 operator per khoa (BR-06-07)
- Weekly gap report tự động mỗi thứ Hai
- Dashboard: ma trận gap drill-down per khoa, per device class

[→ Hướng dẫn: §I.6]

## II.3. Cải Tiến

| Mô tả | Module | Tác động |
|---|---|---|
| IMM-08/09/11/12 assign technician tích hợp với authorization gate | IMM-06 Integration | Block tự động khi KTV hết hạn năng lực |
| IMM-04 Clinical_Release gate tích hợp operator coverage | IMM-04 Integration | Block commissioning khi khoa chưa đủ operator |
| Hồ sơ năng lực link sang PM Work Order (traceability) | IMM-08 Integration | Truy xuất ngược KTV thực hiện PM có đủ năng lực không |

## II.4. Sửa Lỗi

| Mã issue | Mô tả | Severity |
|---|---|---|
| (Module mới — không có bug fix release này) | — | — |

## II.5. Thay Đổi Không Backward-compat

Không có thay đổi breaking cho người dùng hiện tại. IMM-06 là module mới hoàn toàn trong Wave 2.

**Ảnh hưởng đến IMM-08/09/11/12:** Từ v1.1.0, việc phân công kỹ thuật viên vào Work Order sẽ qua authorization gate. KTV không có competency Active cho device_model tương ứng sẽ bị từ chối. **Hành động cần thiết trước go-live:** Nhập dữ liệu competency lịch sử cho toàn bộ KTV đang vận hành thiết bị Class II/III.

## II.6. Deprecations

Không có.

## II.7. Yêu Cầu Nâng Cấp

**Stack version:** Không thay đổi (Frappe v15, Python 3.11, Node 20).

**Migration tự động:** Patch `v3_2.*` chạy tự động khi `bench migrate`. Xem chi tiết §I.3 trong `08_Deployment.md`.

**Migration thủ công (Admin):**
1. Nhập dữ liệu competency lịch sử qua `scripts/bulk_import/import_competency_history.py`
2. Kiểm tra operator coverage từng khoa trên Dashboard trước go-live
3. Xử lý gap Class III trước khi authorization gate đi vào vận hành

**Training bắt buộc:** 6 role phải hoàn tất training trước khi sử dụng. Thời lượng 30 phút đến 3 giờ tùy role. Xem `08_Deployment.md §II.7`.

## II.8. Downtime / Compatibility / Known Issues

**Downtime:** 30-60 phút trong maintenance window 23:00-02:00 ngày deploy.

**Khả năng tương thích:**

| Môi trường | Hỗ trợ |
|---|---|
| Chrome ≥ 120 | ✅ |
| Edge ≥ 120 | ✅ |
| Firefox ≥ 121 | ✅ |
| Safari ≥ 17 | ✅ |
| Mobile (responsive, self-service portal) | ✅ (< 768px hỗ trợ đầy đủ) |

**Known issues:**

| Vấn đề | Workaround | Fix dự kiến |
|---|---|---|
| E-signature số trên chứng nhận PDF chưa hỗ trợ | Ký tay trên bản in | v0.2 (Wave 3) |
| Rate limit `check_user_authorization` external chưa cấu hình | Hạn chế gọi API từ external integration | v1.1.1 |
| LMS content delivery (video, quiz online) | Dùng LMS riêng, ghi nhận hoàn thành thủ công vào session | Wave 3 |

## II.9. Liên Kết & Lịch Sử Versioning

- User Guide: §I file này
- Functional Specs: [IMM-06_Functional_Specs.md](./IMM-06_Functional_Specs.md)
- Deployment Plan: [08_Deployment.md](./08_Deployment.md)
- Báo lỗi: `support@assetcore.vn` hoặc GitHub Issues

| Version | Ngày | Nội dung |
|---|---|---|
| 1.0.0 | 2026-05-08 | IMM-06 General Availability (Wave 2) |

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
| US-06-01 | Story | Tạo Training Program (curriculum) | Func Specs §3 | `api/imm06.py: create_program()` | `test_create_program_happy` | UAT-IMM06-01 | #imm06-core | v1.1.0 | ✅ |
| US-06-02 | Story | Schedule Training Session | Func Specs §3 | `api/imm06.py: create_session()` | `test_session_before_insert` | UAT-IMM06-02 | #imm06-core | v1.1.0 | ✅ |
| US-06-03 | Story | Confirm + Run Session | Func Specs §3 | Workflow Session transitions | `test_workflow_session_confirm` | UAT-IMM06-02 | #imm06-core | v1.1.0 | ✅ |
| US-06-04 | Story | Chấm điểm + Complete Session → auto-Competency | Func Specs §3 | `services/imm06.py: auto_create_competency_from_session()` | `TestAutoCreateCompetency` | UAT-IMM06-03 | #imm06-core | v1.1.0 | ✅ |
| US-06-05 | Story | Sign-off Competency → Active | Func Specs §3 | `api/imm06.py: signoff_competency()` | `TestSignoff: test_ok_own_dept` | UAT-IMM06-03 | #imm06-core | v1.1.0 | ✅ |
| US-06-06 | Story | Scheduler expiry alert 90/60/30 | Func Specs §3 | `tasks.py: check_competency_expiry()` | `TestExpiry: test_milestone_90` | UAT-IMM06-06 | #imm06-core | v1.1.0 | ✅ |
| US-06-07 | Story | Authorization gate (IMM-08/09/12) | Func Specs §3 | `services/imm06.py: check_user_authorization()` | `TestUserAuthorization` | UAT-IMM06-04 | #imm06-core | v1.1.0 | ✅ |
| US-06-08 | Story | Operator coverage gate (IMM-04) | Func Specs §3 | `services/imm06.py: get_asset_operator_coverage()` | `TestOperatorCoverage` | UAT-IMM06-05 | #imm06-core | v1.1.0 | ✅ |
| US-06-09 | Story | Recertification auto-create Refresher | Func Specs §3 | `tasks.py: check_recertification_due()` | `TestRecertDue` | UAT-IMM06-06 | #imm06-core | v1.1.0 | ✅ |
| US-06-10 | Story | Revoke Competency + CAPA | Func Specs §3 | `api/imm06.py: revoke_competency()` | `TestRevoke` | UAT-IMM06-07 | #imm06-core | v1.1.0 | ✅ |
| US-06-11 | Story | Self-service portal | Func Specs §3 | `api/imm06.py: get_user_competencies()` | `test_list_competencies_as_operator` | UAT-IMM06-09 | #imm06-core | v1.1.0 | ✅ |
| US-06-12 | Story | Gap Dashboard | Func Specs §3 | `api/imm06.py: get_competency_gaps_by_dept()` | `test_get_dashboard_stats` | UAT-IMM06-11 | #imm06-core | v1.1.0 | ✅ |
| BR-06-01 | Rule | WO assign gate: Active competency required | Module Overview §7 | `check_user_authorization()` before_assign | `TestUserAuthorization` | UAT-IMM06-04 | #imm06-core | v1.1.0 | ✅ |
| BR-06-02 | Rule | Instructor phải đủ qualification | Module Overview §7 | `IMMTrainingSession.validate() VR-04` | `test_session_before_insert_validates_instructor` | UAT-IMM06-02 | #imm06-core | v1.1.0 | ✅ |
| BR-06-03 | Rule | Expired → block tự động, recert bắt buộc | Module Overview §7 | `auto_expire_competency()` + BR-06-01 | `TestAutoExpire` | UAT-IMM06-06 | #imm06-core | v1.1.0 | ✅ |
| BR-06-04 | Rule | Program update trigger re-cert | Module Overview §7 | `IMMTrainingProgram.on_update` compare critical fields | `TestProgramUpdate` | UAT-IMM06-08 | #imm06-core | v1.1.0 | ✅ |
| BR-06-05 | Rule | theory + practical + sign-off bắt buộc | Module Overview §7 | VR-06 + VR-07 + workflow gate | `TestSignoff: test_expiry_date_computed` | UAT-IMM06-03 | #imm06-core | v1.1.0 | ✅ |
| BR-06-06 | Rule | Revoke + CAPA khi incident | Module Overview §7 | VR-08 + `revoke_competency()` | `TestRevoke: test_vr08_incident_no_capa` | UAT-IMM06-07 | #imm06-core | v1.1.0 | ✅ |
| BR-06-07 | Rule | Class III ≥ 2 operator per khoa | Module Overview §7 | `get_asset_operator_coverage()` + IMM-04 gate | `TestOperatorCoverage: test_class3_insufficient` | UAT-IMM06-05 | #imm06-core | v1.1.0 | ✅ |
| BR-06-08 | Rule | Audit trail mọi thay đổi competency | Module Overview §7 | `IMM Audit Trail` log via `lifecycle.py` | `test_audit_trail_on_revoke_has_metadata` | UAT-IMM06-12 | #imm06-core | v1.1.0 | ✅ |
| BR-06-09 | Rule | Không xóa cứng competency | Module Overview §7 | `on_trash()` throw | `TestDeletePrevention` | UAT-IMM06-10 | #imm06-core | v1.1.0 | ✅ |
| BR-06-10 | Rule | User đổi khoa → giữ competency | Module Overview §7 | Hook User.on_update | `test_dept_change_keeps_competency` | (manual) | #imm06-core | v1.1.0 | ✅ |
| BR-06-11 | Rule | 1 Active per user×model | Module Overview §7 | `archive_old_competency()` on_update | `TestBR0611` | UAT-IMM06-03 | #imm06-core | v1.1.0 | ✅ |
| BR-06-12 | Rule | Session Verified không thể Cancel | Module Overview §7 | Workflow constraint | `test_workflow_cancel_from_verified_blocked` | UAT-IMM06-02 | #imm06-core | v1.1.0 | ✅ |
| NĐ98/§35 | Compliance | Chứng nhận vận hành TTBYT | 08 §II.2 | BR-06-01 + BR-06-05 | UAT-IMM06-03, 04 | UAT-IMM06-03 | #imm06-core | v1.1.0 | ✅ |
| NĐ98/Điều 15.2 | Compliance | Lưu trữ ≥ 10 năm | 08 §II.2 | `IMM Audit Trail` immutable | `test_audit_chain_intact` | UAT-IMM06-12 | #imm06-core | v1.1.0 | ✅ |
| WHO HTM 4.4 | Compliance | Operator competence gate | 08 §II.2 | BR-06-01 | `TestUserAuthorization` | UAT-IMM06-04 | #imm06-core | v1.1.0 | ✅ |
| WHO HTM Annex 5 | Compliance | Recertification định kỳ | 08 §II.2 | BR-06-03 scheduler | `TestRecertDue` | UAT-IMM06-06 | #imm06-core | v1.1.0 | ✅ |
| ISO 13485 §6.2 | Compliance | Competence, Awareness, Training | 08 §II.2 | BR-06-05 sign-off gate | `TestSignoff` | UAT-IMM06-03 | #imm06-core | v1.1.0 | ✅ |
| ISO 13485 §8.5.2 | Compliance | CAPA for revoke | 08 §II.2 | BR-06-06 VR-08 | `TestRevoke: test_vr08` | UAT-IMM06-07 | #imm06-core | v1.1.0 | ✅ |
| SEC-IMM06-01 | Security | Operator chỉ thấy competency của mình | 07 §III.1 | `permissions.py: user_competency_query()` | `test_list_competencies_as_operator` | UAT-IMM06-09 | #imm06-core | v1.1.0 | ✅ |
| SEC-IMM06-02 | Security | Audit chain không thể tamper | 07 §III.3 | `IMM Audit Trail` DocPerm no-delete | `test_audit_chain_breaks_on_tamper` | UAT-IMM06-12 | #imm06-core | v1.1.0 | ✅ |

## III.3. Reverse Lookup

| Test ID | Requirement(s) cover |
|---|---|
| `TestUserAuthorization: test_authorized_when_active` | US-06-07, BR-06-01, WHO HTM 4.4 |
| `TestUserAuthorization: test_unauthorized_when_expired` | US-06-07, BR-06-01, BR-06-03 |
| `TestAutoCreateCompetency: test_pass_creates_competency` | US-06-04, BR-06-05 |
| `TestSignoff: test_ok_own_dept` | US-06-05, BR-06-05, NĐ98/§35 |
| `TestSignoff: test_wrong_dept_forbidden` | US-06-05, SEC-IMM06-01 |
| `TestExpiry: test_milestone_90` | US-06-06, BR-06-03, WHO HTM Annex 5 |
| `TestAutoExpire: test_past_due_expired` | US-06-06, BR-06-03 |
| `TestOperatorCoverage: test_class3_insufficient` | US-06-08, BR-06-07 |
| `TestRevoke: test_vr08_incident_no_capa` | US-06-10, BR-06-06, ISO 13485 §8.5.2 |
| `TestDeletePrevention: test_active_throws` | BR-06-09, NĐ98/Điều 15.2 |
| `test_audit_chain_intact` | NĐ98/Điều 15.2, SEC-IMM06-02 |
| `test_audit_chain_breaks_on_tamper` | SEC-IMM06-02 |
| `test_list_competencies_as_operator` | SEC-IMM06-01, US-06-11 |

## III.4. Coverage Gaps

Sau rà soát matrix, không có req Must/Should còn ⬜ trước v1.1.0. Gaps roadmap:

| Req ID | Thiếu gì? | Owner | Deadline |
|---|---|---|---|
| E-signature PDF certificate | Chữ ký số chưa implement | Dev IMM-06 | v0.2 (Wave 3) |
| Rate limit `check_user_authorization` | Security roadmap | DevOps | v1.1.1 |
| Pentest report `docs/security/` | Report chưa upload | Security | Trước go-live |
| LMS content delivery | Out of scope Wave 2 | BA | Wave 3 |
| 2FA | Roadmap Phase 2 | Tech Lead | v2.0 |

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

**Auditor hỏi:** "Làm sao chứng minh KTV vận hành máy thở ngày 15/04/2026 có năng lực hợp lệ?"

Trace: `BR-06-01 → check_user_authorization() → IMM User Competency.status = Active → signoff_date, expiry_date → IMM Audit Trail SIGNOFF record`

---

**Auditor hỏi:** "Nếu năng lực KTV hết hạn mà không ai biết thì sao?"

Trace: `BR-06-03 → Scheduler auto_expire_competency() → status = Expired → email Workshop Head → BR-06-01 block WO assign → Competency Alert Log records`

---

**Auditor hỏi:** "Năng lực bị thu hồi vì sự cố có ghi lý do và CAPA không?"

Trace: `BR-06-06 → revoke_competency(reason, capa_ref) → VR-08 enforce CAPA → IMM User Competency.revoke_capa_ref → IMM Audit Trail REVOKE event với metadata`

## III.7. Bảng Thống Kê Thông Tin Ứng Dụng

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| DocType (chính) | 4 | `IMM Training Program`, `IMM Training Session`, `IMM User Competency`, `IMM Competency Gap Report` |
| DocType (child) | 1 | `IMM Training Participant` |
| DocType (utility) | 1 | `IMM Competency Alert Log` (idempotency tracker) |
| Workflow JSON | 2 | `IMM-06 Session Workflow` (7 states) + `IMM-06 Competency Workflow` (6 states) |
| API endpoint | 25 | `list_programs, get_program, create_program, update_program, list_sessions, get_session, create_session, confirm_session, start_session, enroll_participants, remove_participant, complete_session, cancel_session, verify_session, close_session, list_competencies, get_user_competencies, signoff_competency, revoke_competency, recertify_competency, get_dashboard_stats, get_competency_gaps_by_dept, get_expiring_competencies, check_user_authorization, get_asset_operator_coverage` |
| FE view / page | 6 | ProgramListView, ProgramDetail, SessionListView, SessionDetail, CompetencyListView, TrainingDashboard |
| FE store | 1 | `stores/imm06.ts` |
| Service function | 12 | `check_user_authorization, auto_create_competency_from_session, signoff_competency, revoke_competency, check_competency_expiry, auto_expire_competency, check_recertification_due, generate_competency_gap_report, trigger_recertification_on_program_change, get_asset_operator_coverage, archive_old_competency, on_trash` |
| Scheduler job | 4 | `check_expiring_competencies` (daily), `auto_expire_competencies` (daily), `check_recertification_due` (daily), `generate_weekly_gap_report` (weekly Mon) — đã đăng ký trong `hooks.py` |
| Business Rule | 12 | BR-06-01 → BR-06-12 |
| Validation Rule | 12 | VR-01 → VR-12 |
| Role áp dụng | 7 | Tổ HC-QLCL, Biomed Engineer, Workshop Head, Department Manager, Clinical Head, HTM Technician/Operator, CMMS Admin |
| Test case unit | ~50 | 12 test class × ~4 case avg |
| UAT scenario | 12 | UAT-IMM06-01 → 12 |
| User Story | 12 | US-06-01 → 06-12 |
| Sprint hoàn thành (Wave 2) | 3 | Sprint 5-7, mỗi sprint 2 tuần |

---

## DoD — Hoàn chỉnh

### I. User Guide
- [x] Tiếng Việt 100%, không jargon
- [x] Mô tả tất cả 6 role với hướng dẫn step-by-step
- [x] Dashboard KPI có giải thích trend
- [x] FAQ 7 câu thực tế (scheduler, sign-off, revoke, self-service)
- [x] Cheat sheet trạng thái Session + Competency + phím tắt
- [ ] ≥ 5 screenshot UI thực tế (cần chụp trên staging trước go-live)
- [ ] Reviewed bởi BA + đại diện end-user (Tổ HC-QLCL)

### II. Release Notes
- [x] Tóm tắt 2-3 câu user-friendly
- [x] 4 tính năng mới có role hưởng lợi
- [x] Known issues + workaround documented
- [x] Breaking change: authorization gate — action cần thiết trước go-live
- [x] Downtime và compatibility table
- [ ] Reviewed bởi PM + Tech Lead + BA

### III. Traceability Matrix + Bảng Thống Kê
- [x] 31 dòng: 12 User Story + 12 BR + 2 Compliance + 2 WHO HTM + 2 ISO + 2 Security
- [x] Mọi dòng ✅ có ≥ 4 cell điền
- [x] Reverse lookup table (13 dòng)
- [x] Coverage gaps liệt kê (5 gaps, đều là roadmap — không có Must còn ⬜)
- [x] Bảng thống kê 17 hạng mục
- [ ] Reviewed bởi PM + Tech Lead + QA Lead
