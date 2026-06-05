# IMM-05 — Phát hành (User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | **IMM-05 — Asset Document Repository** |
| Phiên bản | 0.0.2 |
| Ngày phát hành | 2026-05-27 |
| Owner | PM + BA + Tech Writer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) · [Module Overview](./IMM-05_Module_Overview.md) |

> **Chính sách versioning:** Tuân theo `assetcore/__init__.py = 0.0.2`; module docs đồng bộ phiên bản app (release cùng nhịp app, không tách module-version).

---

# Phần I — Hướng Dẫn Sử Dụng

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.

## I.1. Giới Thiệu

Module **Hồ sơ Thiết bị (IMM-05)** là kho tài liệu tập trung cho toàn bộ thiết bị y tế trong bệnh viện. Tại đây bạn có thể lưu trữ, theo dõi và quản lý mọi loại tài liệu: giấy phép Bộ Y tế, chứng nhận xuất xứ, hướng dẫn sử dụng, chứng chỉ kiểm định, hồ sơ đào tạo.

Hệ thống tự động nhắc nhở khi tài liệu sắp hết hạn và ngăn sử dụng thiết bị chưa đủ giấy tờ pháp lý — đảm bảo bệnh viện luôn sẵn sàng đối phó với kiểm tra của Sở Y tế, Bộ Y tế.

**Điểm đặc biệt:**
- Hồ sơ **không bao giờ bị xóa** — chỉ lưu trữ (Archived) khi thay thế bằng phiên bản mới
- Cảnh báo **tự động** 90/60/30 ngày trước khi hết hạn
- Mọi thay đổi đều có **lịch sử version** đầy đủ
- Thiết bị Class C/D không được phép vào vận hành nếu thiếu giấy phép lưu hành BYT còn hiệu lực

**Trước khi bắt đầu, bạn cần:**
- Tài khoản hệ thống AssetCore (liên hệ IT nếu chưa có)
- Trình duyệt Chrome hoặc Edge phiên bản mới nhất
- Kết nối mạng nội bộ bệnh viện
- File tài liệu dạng PDF, JPG hoặc PNG (tối đa 25 MB mỗi file)

**Đăng nhập:**
1. Mở trình duyệt, truy cập: `https://assetcore.vn`
2. Nhập tên đăng nhập và mật khẩu do IT cấp
3. Bấm **Đăng nhập** — vào màn hình chính

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

- **② Sidebar**: Tìm **"Hồ sơ thiết bị"** hoặc **"Tài liệu"** để vào IMM-05.
- **Màu sắc badge trạng thái**:
  - Xanh = Đang hiệu lực (Active)
  - Vàng = Chờ duyệt (Pending Review)
  - Đỏ = Hết hạn (Expired) hoặc Từ chối (Rejected)
  - Xám = Lưu trữ (Archived)

## I.3. Các Vai Trò

| Vai trò | Bạn làm gì trong module này? |
|---|---|
| **Nhân viên TBYT (HTM Technician)** | Upload tài liệu mới, điền thông tin, gửi đi duyệt |
| **Kỹ sư/Kỹ thuật viên Biomed** | Phê duyệt hoặc từ chối tài liệu kỹ thuật |
| **Tổ HC-QLCL** | Phê duyệt tài liệu pháp lý, kiểm định; xử lý trường hợp miễn trừ NĐ98 |
| **Trưởng xưởng (Workshop Head)** | Quản lý kho hồ sơ, hủy, xem Dashboard cảnh báo hết hạn |
| **Phó Trưởng phòng VTTBYT (VP Block2)** | Xem KPI tuân thủ, nhận cảnh báo leo thang khi hết hạn |
| **Trưởng khoa (Clinical Head)** | Xem hồ sơ thiết bị thuộc khoa mình (chỉ đọc) |

## I.4. Quy Trình Chính

```
① Nhận tài liệu từ NCC hoặc cơ quan cấp
      │
      ▼
② Upload và điền thông tin tài liệu
   (Nhân viên TBYT)
      │
      ▼
③ Gửi đi duyệt
   (Nhân viên TBYT)
      │
      ▼
④ Phê duyệt (Biomed / Tổ HC-QLCL)
      │
      ├──► Duyệt → Tài liệu "Đang hiệu lực" ──────────────────────┐
      │                                                             │
      └──► Từ chối → Nhân viên TBYT upload lại → Gửi lại ─────────┘
                                                                    │
                                                                    ▼
                                                      ⑤ Hệ thống theo dõi hết hạn
                                                         (Tự động cảnh báo 90/60/30 ngày)
                                                                    │
                                                                    ▼
                                                      ⑥ Cập nhật phiên bản mới
                                                         (Phiên bản cũ → Archived tự động)
```

## I.5. Thao Tác Theo Vai Trò

### a. Nhân viên TBYT — Upload và gửi duyệt tài liệu

**Khi nào làm?** Khi nhận được tài liệu mới từ nhà cung cấp, Bộ Y tế, hoặc khi tài liệu cũ hết hạn cần thay thế.

**Các bước:**
1. Vào menu **Hồ sơ thiết bị** → bấm nút **"Tạo mới"**
2. Chọn **Thiết bị** — hệ thống tự điền khoa, model
3. Chọn **Nhóm tài liệu**: Pháp lý / Kỹ thuật / Kiểm định / Đào tạo / QA
4. Chọn **Loại tài liệu**: chọn từ danh sách (vd: Giấy phép nhập khẩu, Chứng nhận xuất xứ...)
5. Điền **Số hiệu tài liệu**, **Ngày cấp**, **Ngày hết hạn** (nếu có), **Cơ quan cấp**
6. Bấm nút **Upload** → chọn file PDF (tối đa 25 MB)
7. Bấm **Lưu** — tài liệu ở trạng thái *Nháp*
8. Kiểm tra lại thông tin → bấm **"Gửi Duyệt"**

> ⚠️ Sau khi Gửi Duyệt, tài liệu chuyển sang *Chờ duyệt* và các trường bị khóa — không thể sửa thêm. Nếu cần sửa, liên hệ người phê duyệt để họ Từ chối trước.

**Cập nhật phiên bản mới (khi có tài liệu mới hơn):**
1. Tạo tài liệu mới với cùng loại cho cùng thiết bị
2. Điền **Số phiên bản** (ví dụ: "2.0") và **Tóm tắt thay đổi** (bắt buộc từ phiên bản 2.0+)
3. Upload file mới, Gửi Duyệt
4. Sau khi được Duyệt, phiên bản cũ **tự động chuyển sang Lưu trữ** — không cần thao tác thêm

---

### b. Biomed Engineer / Tổ HC-QLCL — Phê duyệt tài liệu

**Khi nào làm?** Khi nhận thông báo "Có tài liệu chờ duyệt".

**Các bước duyệt:**
1. Mở tài liệu đang ở *Chờ duyệt*
2. Kiểm tra: đúng thiết bị, đúng loại, file đọc được, số liệu hợp lệ, không hết hạn
3. Bấm **[Phê Duyệt]** → tài liệu chuyển sang *Đang hiệu lực*

**Nếu tài liệu không đạt:**
1. Bấm **[Từ Chối]** → popup yêu cầu điền lý do (bắt buộc)
2. Điền lý do cụ thể (vd: "File mờ, không đọc được số hiệu")
3. Bấm **Xác nhận** → TBYT nhận thông báo, upload lại

---

### c. Tổ HC-QLCL — Xử lý miễn trừ NĐ98

**Khi nào làm?** Thiết bị không thể có đủ giấy tờ theo quy định (vd: thiết bị nhập từ trước khi NĐ98 có hiệu lực).

**Các bước:**
1. Mở tài liệu hoặc hồ sơ thiết bị
2. Bấm **"Đánh dấu Miễn trừ"**
3. Chọn lý do miễn trừ và upload văn bản miễn trừ
4. Bấm Xác nhận — thiết bị được đánh dấu *Compliant (Exempt)*

> ⚠️ Chỉ Tổ HC-QLCL và CMMS Admin có quyền thực hiện thao tác này.

---

## I.6. Bảng Điều Khiển Cảnh Báo Hết Hạn

Vào **Hồ sơ thiết bị → Dashboard** để xem tổng quan:

| KPI | Ý nghĩa | Hành động cần làm |
|---|---|---|
| **Đang hiệu lực** | Số tài liệu có trạng thái Active | Theo dõi xu hướng |
| **Sắp hết hạn 90 ngày** | Cần chuẩn bị gia hạn trong 3 tháng tới | Lên kế hoạch liên hệ NCC/BYT |
| **Sắp hết hạn 30 ngày** | Khẩn cấp — hết hạn trong tháng tới | Ưu tiên xử lý ngay |
| **Đã hết hạn** | Tài liệu đã quá hạn, thiết bị có thể bị block | Xử lý ngay; xem xét tạm dừng sử dụng thiết bị |
| **Thiếu hồ sơ** | Asset chưa đủ bộ tài liệu theo quy định | Liên hệ TBYT upload |
| **Compliance theo Khoa** | % thiết bị đủ hồ sơ của từng khoa | Làm việc với trưởng khoa về thiết bị thiếu |

> Hệ thống gửi **email cảnh báo tự động** mỗi ngày lúc 00:30 cho Workshop Head và Biomed Engineer khi có tài liệu đạt ngưỡng cảnh báo.

## I.7. Câu Hỏi Thường Gặp

**Q: Tôi thấy thông báo "Cần giấy phép lưu hành BYT" khi nghiệm thu thiết bị — làm sao xử lý?**
> A: Thiết bị Class C hoặc D yêu cầu giấy phép lưu hành từ Bộ Y tế còn hiệu lực trong IMM-05. Liên hệ Tổ HC-QLCL để upload Giấy phép (DOC-...) rồi chờ Phê duyệt. Sau khi Active, có thể tiếp tục nghiệm thu.

**Q: Tôi muốn xóa một tài liệu upload nhầm?**
> A: Hệ thống **không cho phép xóa** hồ sơ thiết bị y tế theo quy định lưu trữ. Nếu upload nhầm ở trạng thái Nháp — liên hệ Workshop Head để hủy bỏ (Archived). Tài liệu vẫn lưu nhưng không hiển thị trong kết quả tìm kiếm mặc định.

**Q: Tại sao tôi không thấy một số tài liệu trong danh sách?**
> A: Một số tài liệu được đánh dấu "Chỉ xem nội bộ" — bạn cần có role phù hợp (Biomed, TBYT, Tổ HC-QLCL, Workshop Head) để thấy. Role Trưởng khoa chỉ thấy tài liệu "Công khai".

**Q: Tài liệu của tôi đang Active nhưng hệ thống báo gần hết hạn?**
> A: Đây là cảnh báo bình thường — hệ thống nhắc bạn chuẩn bị tài liệu mới. Tài liệu vẫn hợp lệ đến hết ngày hết hạn. Hãy upload phiên bản mới và gửi duyệt trước ngày đó.

**Q: Sau khi Approve tài liệu mới, phiên bản cũ đi đâu?**
> A: Phiên bản cũ tự động chuyển sang *Lưu trữ (Archived)* — không mất, vẫn có thể tìm và xem lịch sử. Chỉ phiên bản Active mới nhất được dùng cho các kiểm tra tuân thủ.

**Q: Tôi không thấy nút "Từ chối" hoặc "Phê duyệt" khi mở tài liệu?**
> A: Nút này chỉ hiển thị với role Biomed Engineer hoặc Tổ HC-QLCL, và chỉ khi tài liệu đang ở trạng thái "Chờ duyệt". Nếu bạn có role đúng mà không thấy nút, có thể tài liệu đã được duyệt/từ chối bởi người khác — kiểm tra lại trạng thái.

**Q: Cần upload file nhưng quá 25 MB?**
> A: Nén file PDF (dùng ilovepdf.com hoặc tools tương tự) để giảm dung lượng. Nếu vẫn cần file gốc chất lượng cao, lưu trữ ở nơi khác và ghi URL vào trường ghi chú — liên hệ IT để thảo luận.

## I.8. Phím Tắt & Mã Trạng Thái

| Phím | Chức năng |
|---|---|
| `⌘K` / `Ctrl+K` | Tìm kiếm nhanh toàn hệ thống |
| `Esc` | Đóng popup / hủy thao tác |
| `Tab` | Chuyển sang trường kế tiếp |
| `Ctrl+S` | Lưu bản nháp |

**Cheat sheet trạng thái tài liệu:**

| Trạng thái | Màu | Ý nghĩa |
|---|---|---|
| Nháp (Draft) | Xanh | Đang soạn, chưa gửi duyệt |
| Chờ duyệt (Pending Review) | Vàng | Đã gửi, đang chờ Biomed/QLCL duyệt |
| Đang hiệu lực (Active) | Xanh đậm | Được duyệt, đang có giá trị pháp lý |
| Từ chối (Rejected) | Đỏ | Bị từ chối — cần upload lại |
| Lưu trữ (Archived) | Xám | Phiên bản cũ sau khi có version mới, hoặc bị hủy bỏ |
| Hết hạn | Đỏ đậm | *(Cờ tình trạng, không phải trạng thái workflow)* Đã qua ngày hết hạn — cần gia hạn. Tài liệu vẫn giữ trạng thái workflow của nó (vd: vẫn "Đang hiệu lực") nhưng được đánh dấu đã hết hạn |

## I.9. Liên Hệ Hỗ Trợ

| Vấn đề | Liên hệ |
|---|---|
| Không đăng nhập được, quên mật khẩu | IT Helpdesk: ext. 1234 hoặc it@hospital.vn |
| Lỗi hiển thị, upload không được | Support AssetCore: support@assetcore.vn |
| Câu hỏi quy trình duyệt hồ sơ | Trưởng xưởng VTTBYT hoặc Tổ HC-QLCL |
| Câu hỏi về Giấy phép BYT, miễn trừ NĐ98 | Phòng QLCL |
| Khẩn cấp (thiết bị ICU thiếu giấy tờ, sắp kiểm tra) | Hotline: 0903.xxx.xxx (24/7) |

## I.10. Lịch Sử Cập Nhật Tài Liệu

| Phiên bản | Ngày | Thay đổi | Owner |
|---|---|---|---|
| 2.0.0 | 2026-05-08 | Phát hành lần đầu — Module IMM-05 Wave 1 GA | BA Lead |

---

# Phần II — Release Notes

## II.1. Tóm Tắt

Phiên bản 2.0.0 (2026-05-08) đưa module **Hồ sơ Thiết bị (IMM-05)** vào vận hành chính thức song song với IMM-04. Module quản lý toàn bộ vòng đời tài liệu thiết bị y tế — từ CO/CQ khi nhận hàng đến chứng chỉ kiểm định định kỳ — với cảnh báo hết hạn tự động và kiểm soát phiên bản chặt chẽ theo ISO 13485. Downtime dự kiến 30-60 phút trong cửa sổ bảo trì đêm (deploy cùng IMM-04).

## II.2. Tính Năng Mới

### Kho hồ sơ tập trung (Nhân viên TBYT + Biomed + Tổ HC-QLCL)

Upload và quản lý toàn bộ tài liệu thiết bị y tế: giấy phép, chứng nhận, manual, kiểm định, đào tạo. Quy trình duyệt 2 bước với lịch sử version đầy đủ.

- 5 nhóm tài liệu: Pháp lý / Kỹ thuật / Kiểm định / Đào tạo / QA
- Version control tự động archive phiên bản cũ khi có phiên bản mới được duyệt
- File hỗ trợ: PDF, JPG, PNG (tối đa 25 MB)
- Không bao giờ xóa cứng — BR-05-02 đảm bảo audit trail

[→ Hướng dẫn: §I.5.a, §I.5.b]

### Cảnh báo hết hạn tự động (Workshop Head + VP Block2)

Scheduler chạy hàng ngày lúc 00:30, phát hiện và cảnh báo tài liệu sắp hết hạn theo 4 mốc: 90/60/30/0 ngày.

- Email cảnh báo tự động — không cần kiểm tra thủ công
- Idempotent: không gửi email trùng lặp cùng ngày
- Tự động đánh dấu tài liệu "đã hết hạn" (cờ `is_expired`) khi quá ngày hết hạn — tài liệu hiện ngay trên ô KPI "Đã hết hạn" của dashboard và click vào ra đúng danh sách tài liệu quá hạn (số đếm = số dòng danh sách)
- Dashboard với timeline hết hạn và compliance % theo khoa

[→ Hướng dẫn: §I.6]

### GW-2 Gate — Kiểm soát pháp lý khi nghiệm thu (Tổ HC-QLCL)

Cổng kiểm soát tự động: thiết bị Class C/D không thể vào vận hành nếu thiếu giấy phép lưu hành BYT còn hiệu lực trong IMM-05.

- GW-2 gate trong IMM-04 query real-time sang IMM-05
- Hỗ trợ flow miễn trừ (`is_exempt`) cho thiết bị đặc biệt
- Compliance score tính vào asset `custom_document_status`

[→ Hướng dẫn: §I.5.c]

### Auto-import từ IMM-04 (System)

Khi nghiệm thu thiết bị hoàn tất (Clinical Release), bộ hồ sơ baseline tự động được import vào IMM-05 — không cần tạo lại thủ công.

- CO/CQ/Manual/License từ Commissioning → tạo Asset Document (Draft) tự động
- Link ngược `source_commissioning` và `source_module = "IMM-04"`

## II.3. Cải Tiến

| Mô tả | Module | Tác động |
|---|---|---|
| Asset completeness % tự tính hàng ngày | IMM-05 | Dashboard IMM-10 luôn có số liệu mới nhất |
| Document Request với deadline và leo thang | IMM-05 | Không bỏ sót tài liệu thiếu kéo dài |

## II.4. Sửa Lỗi

| Mã issue | Mô tả | Severity |
|---|---|---|
| (Module mới — không có bug fix release này) | — | — |

## II.5. Thay Đổi Không Backward-compat

Không có thay đổi breaking. Module IMM-05 là module mới hoàn toàn.

Lưu ý: Sau deploy, **GW-2 gate trong IMM-04 được kích hoạt** — các phiếu nghiệm thu mới cho Class C/D sẽ bị block nếu IMM-05 chưa có Active license document. Đây là hành vi mong muốn (by design).

## II.6. Deprecations

Không có.

## II.7. Yêu Cầu Nâng Cấp

**Stack version:** Không thay đổi. Deploy cùng wave với IMM-04 (v2.0.0).

**Migration tự động:** Patch `v2_0.*` chạy tự động. Sau migrate cần chạy thủ công:
```bash
bench --site assetcore.local execute assetcore.tasks.update_asset_completeness
```

**Training bắt buộc:** 5 role phải hoàn tất training trước khi sử dụng. Xem `08_Deployment.md §II.7`.

## II.8. Downtime / Compatibility / Known Issues

**Downtime:** 30-60 phút trong maintenance window 23:00-02:00 ngày deploy (cùng IMM-04).

**Khả năng tương thích:**

| Môi trường | Hỗ trợ |
|---|---|
| Chrome ≥ 120 | ✅ |
| Edge ≥ 120 | ✅ |
| Firefox ≥ 121 | ✅ |
| Safari ≥ 17 | ✅ |
| Mobile (responsive) | ✅ (giới hạn — desktop khuyến nghị để upload file) |

**Known issues:**

| Vấn đề | Workaround | Fix dự kiến |
|---|---|---|
| Email notification template dùng inline string, không dùng Email Template DocType | Email vẫn gửi đúng nội dung | v2.1.0 |
| Service layer `services/imm05.py` chưa tách (tech-debt) | Logic trong controller vẫn đúng | v2.1.0 |
| Dashboard frontend KPI panel chưa build | Dùng API `get_dashboard_stats` trực tiếp | v2.1.0 |

## II.9. Liên Kết & Lịch Sử Versioning

- User Guide: §I file này
- Module Overview: [IMM-05_Module_Overview.md](./IMM-05_Module_Overview.md)
- Deployment Plan: [08_Deployment.md](./08_Deployment.md)
- Báo lỗi: `support@assetcore.vn`

| Version | Ngày | Nội dung |
|---|---|---|
| 2.0.0 | 2026-05-08 | IMM-05 General Availability — Wave 1 |

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
| US-05-01 | Story | Upload + gửi duyệt + approve | Module Overview §4 | `api/imm05.py: create_document(), approve_document()` | `TestVersionControlArchive: test_approve_ok` | UAT-IMM05-01 | #imm05-core | v2.0.0 | ✅ |
| US-05-02 | Story | Reject + gửi lại | Module Overview §4 | `api/imm05.py: reject_document()` | `TestVersionControlArchive: test_reject_requires_reason` | UAT-IMM05-02 | #imm05-core | v2.0.0 | ✅ |
| US-05-03 | Story | Version control archive tự động | Module Overview §4 | `asset_document.py: archive_old_versions()` | `TestVersionControlArchive: test_archive_old_on_new_approve` | UAT-IMM05-03 | #imm05-core | v2.0.0 | ✅ |
| US-05-04 | Story | Block xóa cứng document | Module Overview §4 | `asset_document.py: on_trash()` | `TestDeletePrevention: test_on_trash_raises` | UAT-IMM05-04 | #imm05-core | v2.0.0 | ✅ |
| US-05-05 | Story | Expiry alert scheduler 90/60/30/0 | Module Overview §5.3 | `tasks.py: check_document_expiry()` | `TestCheckDocumentExpiry: test_90d_alert_created` | UAT-IMM05-05 | #imm05-core | v2.0.0 | ✅ |
| US-05-06 | Story | Auto-import từ IMM-04 on Submit | Module Overview §8 | `asset_commissioning.py: create_initial_document_set()` | `test_auto_import_from_imm04_on_submit` | UAT-IMM05-06 | #imm05-core | v2.0.0 | ✅ |
| US-05-07 | Story | GW-2 gate cho IMM-04 | Module Overview §8 | `asset_document.py: _gw2_check_document_compliance()` | `test_gw2_gate_blocks_commissioning` | UAT-IMM05-10 | #imm05-core | v2.0.0 | ✅ |
| US-05-08 | Story | Visibility filter Internal_Only | Module Overview §6 | `asset_document.py: _apply_visibility_filter()` | `TestVisibilityFilter: test_clinical_cannot_see_internal` | UAT-IMM05-08 | #imm05-core | v2.0.0 | ✅ |
| US-05-09 | Story | Dashboard KPIs + compliance by dept | Module Overview §4 | `api/imm05.py: get_dashboard_stats(), get_compliance_by_dept()` | `test_get_dashboard_stats` | UAT-IMM05-09 | #imm05-core | v2.0.0 | ✅ |
| BR-05-01 | Rule | 1 Active per asset+type; archive cũ khi approve mới | Module Overview §7 | `archive_old_versions()` on_update | `TestVersionControlArchive: test_only_one_active` | UAT-IMM05-03 | #imm05-core | v2.0.0 | ✅ |
| BR-05-02 | Rule | Không xóa cứng | Module Overview §7 | `on_trash()` raise | `TestDeletePrevention: test_on_trash_raises` | UAT-IMM05-04 | #imm05-core | v2.0.0 | ✅ |
| BR-05-03 | Rule | Expiry alert idempotent 90/60/30/0 | Module Overview §7 | `check_document_expiry()` scheduler | `TestCheckDocumentExpiry: test_idempotent_same_day` | UAT-IMM05-05 | #imm05-core | v2.0.0 | ✅ |
| BR-05-04 | Rule | Auto-import từ IMM-04 | Module Overview §7 | `create_initial_document_set()` | `test_auto_import_from_imm04_on_submit` | UAT-IMM05-06 | #imm05-core | v2.0.0 | ✅ |
| BR-05-05 | Rule | Required Document Type completeness | Module Overview §7 | `update_asset_completeness()` | `TestUpdateAssetCompleteness: test_incomplete` | UAT-IMM05-09 | #imm05-core | v2.0.0 | ✅ |
| BR-05-07 | Rule | GW-2 gate block commissioning | Module Overview §7 | `_gw2_check_document_compliance()` | `test_gw2_gate_blocks_commissioning` | UAT-IMM05-10 | #imm05-core | v2.0.0 | ✅ |
| BR-05-08 | Rule | Exempt → Compliant (Exempt) | Module Overview §7 | `_compute_document_status()` | `TestExemptComputation: test_exempt_status` | UAT-IMM05-08 | #imm05-core | v2.0.0 | ✅ |
| BR-05-09 | Rule | change_summary bắt buộc v > 1.0 | Module Overview §7 | VR-09 trong `validate()` | `TestChangeSummary: test_v2_requires_summary` | UAT-IMM05-07 | #imm05-core | v2.0.0 | ✅ |
| BR-05-10 | Rule | Internal_Only ẩn non-internal roles | Module Overview §7 | `_apply_visibility_filter()` | `TestVisibilityFilter: test_clinical_cannot_see_internal` | UAT-IMM05-08 | #imm05-core | v2.0.0 | ✅ |
| NĐ98/Điều 15.2 | Compliance | Lưu trữ ≥ 5 năm | 08 §II.2 | BR-05-02: `on_trash()` | UAT-IMM05-04 | UAT-IMM05-04 | #imm05-core | v2.0.0 | ✅ |
| TT 46/Điều 4 | Compliance | Chứng chỉ kiểm định có hạn | 08 §II.2 | BR-05-03: `check_document_expiry()` | `TestCheckDocumentExpiry` | UAT-IMM05-05 | #imm05-core | v2.0.0 | ✅ |
| NĐ98/Điều 18 | Compliance | Giấy phép lưu hành BYT | 08 §II.2 | BR-05-07: GW-2 | UAT-IMM05-10 | UAT-IMM05-10 | #imm05-core | v2.0.0 | ✅ |
| WHO HTM §6.4 | Compliance | Document control + version | 08 §II.2 | BR-05-01: `archive_old_versions()` | UAT-IMM05-03 | UAT-IMM05-03 | #imm05-core | v2.0.0 | ✅ |
| ISO 13485 §4.2.5 | Compliance | Approve trước effective | 08 §II.2 | Workflow Draft → Pending → Active | UAT-IMM05-01 | UAT-IMM05-01 | #imm05-core | v2.0.0 | ✅ |
| SEC-IMM05-01 | Security | Clinical Head không thấy Internal_Only | 07 §III.1 | `_apply_visibility_filter()` | `TestVisibilityFilter` | UAT-IMM05-08 | #imm05-core | v2.0.0 | ✅ |
| SEC-IMM05-02 | Security | HTM Technician không thể self-approve | 07 §III.2 | Workflow role check | `TestWorkflow: test_approve_wrong_role` | UAT-IMM05-08 | #imm05-core | v2.0.0 | ✅ |

## III.3. Reverse Lookup

| Test ID | Requirement(s) cover |
|---|---|
| `TestVersionControlArchive: test_archive_old_on_new_approve` | US-05-03, BR-05-01 |
| `TestDeletePrevention: test_on_trash_raises` | US-05-04, BR-05-02, NĐ98/Điều 15.2 |
| `TestCheckDocumentExpiry: test_90d_alert_created` | US-05-05, BR-05-03, TT 46/Điều 4 |
| `TestCheckDocumentExpiry: test_idempotent_same_day` | BR-05-03 |
| `test_auto_import_from_imm04_on_submit` | US-05-06, BR-05-04 |
| `test_gw2_gate_blocks_commissioning` | US-05-07, BR-05-07, NĐ98/Điều 18 |
| `TestVisibilityFilter: test_clinical_cannot_see_internal` | US-05-08, BR-05-10, SEC-IMM05-01 |
| `TestChangeSummary: test_v2_requires_summary` | BR-05-09 |

## III.4. Coverage Gaps

Sau rà soát matrix, không có req Must/Should còn ⬜ trước v2.0.0. Gaps roadmap:

| Req ID | Thiếu gì? | Owner | Deadline |
|---|---|---|---|
| Email notification template | Dùng Email Template DocType thay inline | Dev IMM-05 | v2.1.0 |
| Service layer refactor | Tách logic từ controller → `services/imm05.py` | Dev | v2.1.0 |
| Dashboard FE component | Build Vue component cho KPI panel | Dev FE | v2.1.0 |
| Rate limit `approve_document` | Security roadmap | DevOps | v2.1.0 |
| Pentest report | Report chưa upload | Security | Trước go-live |

## III.5. Cập Nhật Quy Ước

| Khi | Ai update | Cell nào |
|---|---|---|
| Có req mới | BA Lead | Thêm dòng, điền `Req ID`, `Loại`, `Mô tả`, `Doc ref` |
| Design xong | Tech Lead | Điền `Design / Code` |
| PR merged | Dev | Điền `PR` |
| Test case viết xong | Dev/QA | Điền `Test ID` |
| UAT pass | QA Lead | Điền `UAT ID` + status ✅ |
| Release | PM | Điền `Released-in` + chốt status |

## III.6. Audit-readiness — Quick Links

**Auditor hỏi:** "Giấy phép lưu hành máy CT khoa ICU còn hiệu lực không? Phiên bản nào mới nhất?"

Trace: `Asset ACC-ASS-2026-00001 → IMM-05 list filter asset + doc_type=License → Active record DOC-ACC-... → expiry_date = 2028-06-30 → approved_by = qa.pham + approval_date`

---

**Auditor hỏi:** "Máy thở Drager có đủ hồ sơ theo yêu cầu không?"

Trace: `Asset.custom_document_status = "Compliant" → custom_doc_completeness_pct = 100% → get_asset_documents?asset=ACC-... → group theo category, completeness per Required Document Type`

---

**Auditor hỏi:** "Ai đã phê duyệt chứng nhận kiểm định máy siêu âm năm 2026?"

Trace: `Asset Document DOC-ACC-...-2026-00005 → approved_by = biomed.nguyen → approval_date = 2026-03-15 → IMM Audit Trail hash chain → get_document_history?name=DOC-...`

## III.7. Bảng Thống Kê Thông Tin Ứng Dụng

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| DocType (chính) | 3 | `Asset Document`, `Document Request`, `Required Document Type` |
| DocType (phụ) | 1 | `Expiry Alert Log` |
| Workflow JSON | 1 | `IMM-05 Document Workflow` — 6 states, 8 transitions |
| API endpoint | 16 | `list_documents, get_document, create_document, update_document, submit_for_review, approve_document, reject_document, archive_document, get_asset_documents, get_dashboard_stats, get_expiring_documents, get_compliance_by_dept, get_document_history, create_document_request, get_document_requests, mark_exempt` |
| FE view / page | 5 | DocumentList, DocumentDetail, DocumentCreate, AssetDocumentsTab, Dashboard |
| Scheduler job | 3 | Daily: expiry check (00:30), completeness update (01:00), overdue requests |
| Business Rule | 10 | BR-05-01 → BR-05-10 |
| Validation Rule (controller) | 11 | VR-01 → VR-11 trong `asset_document.py` |
| Role áp dụng | 7 | HTM Technician, Biomed Engineer, Tổ HC-QLCL, Workshop Head, VP Block2, CMMS Admin, Clinical Head |
| Test case unit | ~35 | 11 test class × ~3 case avg |
| UAT scenario | 10 | UAT-IMM05-01 → 10 |
| LOC Controller (`asset_document.py`) | ~400 | Validation/compute_status hooks |
| LOC Service (`services/imm05.py`) | 587 | Đã refactor ra service layer (Wave-2) |
| LOC API (`api/imm05.py`) | 156 | 16 endpoints (whitelist count, 2026-05-18) |
| Scheduler thực tế | 1 | `check_document_expiry` daily (2 job khác trong spec chưa implement) |
| Sprint hoàn thành (Wave 1) | 4 | Sprint 1-4, mỗi sprint 2 tuần |
| User Story | 9 | US-05-01 → 05-09 |

---

## DoD — Hoàn chỉnh

### I. User Guide
- [x] Tiếng Việt 100%, không jargon
- [x] Mô tả tất cả 6 role với hướng dẫn step-by-step
- [x] Dashboard KPI có giải thích + hành động cần làm
- [x] FAQ 7 câu thực tế
- [x] Cheat sheet trạng thái 6 state + màu + phím tắt
- [ ] ≥ 5 screenshot UI thực tế (cần chụp trên staging trước go-live)
- [ ] Reviewed bởi BA + đại diện end-user (Tổ HC-QLCL)

### II. Release Notes
- [x] Tóm tắt 2-3 câu user-friendly
- [x] 4 tính năng mới có role hưởng lợi
- [x] Known issues + workaround documented (email template, service layer, dashboard FE)
- [x] Breaking change: GW-2 gate activation documented
- [x] Downtime và compatibility table
- [ ] Reviewed bởi PM + Tech Lead + BA

### III. Traceability Matrix + Bảng Thống Kê
- [x] 25 dòng: 9 User Story + 8 BR + 5 Compliance + 2 Security
- [x] Mọi dòng ✅ có ≥ 4 cell điền
- [x] Reverse lookup table
- [x] Coverage gaps liệt kê (5 gaps, đều là roadmap — không có Must còn ⬜)
- [x] Bảng thống kê 15 hạng mục
- [ ] Reviewed bởi PM + Tech Lead + QA Lead
