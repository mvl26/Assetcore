# IMM-09 — Phát hành (User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | **IMM-09 — Sửa chữa (Corrective Maintenance)** |
| Phiên bản | 1.0.0 |
| Ngày phát hành | 2026-05-08 |
| Owner | PM + BA + Tech Writer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) · [Functional Specs](./IMM-09_Functional_Specs.md) |
| Cập nhật | 2026-05-18 |

---

# Phần I — Hướng Dẫn Sử Dụng

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.

## I.1. Giới Thiệu

Module **Sửa chữa (IMM-09)** giúp đội ngũ kỹ thuật thiết bị y tế quản lý toàn bộ quá trình sửa chữa thiết bị từ lúc tiếp nhận yêu cầu đến khi trả thiết bị về khoa phòng.

Mọi hoạt động sửa chữa đều được ghi lại thành **phiếu sửa chữa**. Bạn có thể theo dõi tiến độ theo thời gian thực, xem lịch sử sửa chữa của từng thiết bị, và kiểm tra chỉ số hiệu quả (MTTR, tỷ lệ đúng hạn).

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
- **② Sidebar**: Menu module. Tìm **"Sửa chữa"** hoặc **"CM"** để vào IMM-09.
- **③ Vùng chính**: Danh sách phiếu, chi tiết phiếu, hoặc Dashboard.
- **Chấm màu cam** ở sidebar = Module Sửa chữa đang active.

## I.3. Các Vai Trò

| Vai trò | Bạn làm gì trong module này? |
|---|---|
| **Trưởng xưởng kỹ thuật** | Tạo phiếu sửa chữa, phân công kỹ thuật viên, duyệt thay thế firmware, hủy phiếu nếu cần |
| **Kỹ thuật viên BME** | Nhận phiếu được phân công, chẩn đoán lỗi, đề xuất vật tư, thực hiện sửa chữa, điền checklist nghiệm thu |
| **Nhân viên kho** | Xuất vật tư theo yêu cầu, ghi nhận chứng từ xuất kho vào phiếu sửa chữa |
| **Trưởng khoa phòng** | Xác nhận nghiệm thu khi kỹ thuật viên bàn giao thiết bị đã sửa xong |
| **Phó Trưởng phòng Vật tư** | Xem báo cáo MTTR, Dashboard KPI, theo dõi hiệu quả sửa chữa |

## I.4. Quy Trình Chính

```
① Sự cố xảy ra
      │
      ▼
② Tiếp nhận & Tạo phiếu sửa chữa
   (Trưởng xưởng)
      │
      ▼
③ Phân công kỹ thuật viên
   (Trưởng xưởng)
      │
      ▼
④ Chẩn đoán lỗi
   (Kỹ thuật viên)
      │
      ├──► Cần vật tư ──► ⑤ Xuất vật tư từ kho
      │                        │
      └──────────────────────► ▼
                           ⑥ Thực hiện sửa chữa
                           (Kỹ thuật viên)
                               │
                               ▼
                           ⑦ Điền checklist nghiệm thu
                           (Kỹ thuật viên)
                               │
                               ▼
                           ⑧ Xác nhận nghiệm thu
                           (Trưởng khoa phòng)
                               │
                               ├──► ✅ Hoàn tất → Thiết bị Active
                               └──► ❌ Không sửa được → Thiết bị Out of Service
```

## I.5. Thao Tác Theo Vai Trò

### a. Trưởng xưởng — Tạo phiếu sửa chữa

**Khi nào làm?** Khi nhận được báo hỏng từ khoa phòng hoặc khi bảo trì định kỳ phát hiện lỗi nghiêm trọng.

**Các bước:**
1. Vào menu **Sửa chữa** → bấm nút **"Tạo mới"** (góc phải trên)
2. Chọn **Thiết bị** — hệ thống tự điền thông tin thiết bị
3. Chọn **Nguồn**: gắn **Báo cáo sự cố** (nếu có) HOẶC **Phiếu bảo trì** (nếu PM phát hiện lỗi)
4. Chọn **Loại sửa chữa** và **Mức độ ưu tiên**
5. Bấm **"Tạo"** — phiếu tạo thành công, trạng thái *Mới tiếp nhận*

> ⚠️ **Lưu ý:** Phiếu bắt buộc phải có nguồn (báo cáo sự cố hoặc phiếu bảo trì). Không có nguồn → hệ thống báo lỗi.

---

**Phân công kỹ thuật viên:**
1. Mở phiếu ở trạng thái *Mới tiếp nhận*
2. Bấm **"Phân công"**, chọn kỹ thuật viên phù hợp
3. Kỹ thuật viên được thông báo tự động qua hệ thống

---

**Duyệt thay đổi firmware (nếu có):**
- Khi KTV báo cần cập nhật firmware → tạo **Phiếu thay đổi firmware**
- Xem xét và duyệt phiếu → KTV mới được điền vào phiếu sửa chữa

### b. Kỹ thuật viên — Chẩn đoán và sửa chữa

**Khi nào làm?** Sau khi nhận thông báo được phân công.

**Các bước:**
1. Vào **Sửa chữa** → danh sách hiển thị các phiếu *của bạn*
2. Mở phiếu → bấm **"Bắt đầu chẩn đoán"**
3. Điền **Nguyên nhân gốc rễ** và **Ghi chú chẩn đoán**, tải ảnh lên nếu cần
4. Nếu cần vật tư: chọn "Cần vật tư = Có" → hệ thống thông báo kho
5. Khi có vật tư: bấm **"Bắt đầu sửa chữa"**
6. Sau khi sửa xong: điền **Checklist nghiệm thu** — tất cả các mục phải *Đạt*
7. Bấm **"Hoàn tất sửa chữa"** — phiếu chuyển sang chờ nghiệm thu

> 💡 **Mẹo:** Bấm vào tên thiết bị để xem lịch sử sửa chữa trước đây.

### c. Nhân viên kho — Xuất vật tư

**Khi nào làm?** Khi nhận thông báo KTV yêu cầu vật tư.

**Các bước:**
1. Mở phiếu sửa chữa đang ở trạng thái *Chờ vật tư*
2. Vào tab **Vật tư sử dụng** → thêm vật tư đã xuất
3. Điền **Mã chứng từ xuất kho** (bắt buộc — không điền không lưu được)
4. Lưu → KTV nhận thông báo vật tư đã sẵn sàng

### d. Trưởng khoa phòng — Xác nhận nghiệm thu

**Khi nào làm?** KTV mang thiết bị về, yêu cầu xác nhận bàn giao.

**Các bước:**
1. Mở phiếu sửa chữa đang *Chờ nghiệm thu*
2. Kiểm tra thiết bị hoạt động bình thường
3. Điền **Tên người xác nhận** và bấm **"Xác nhận nghiệm thu"**
4. Phiếu chuyển trạng thái *Hoàn tất*, thiết bị trở về *Đang hoạt động*

## I.6. Bảng Điều Khiển (Dashboard)

Vào **Sửa chữa → Dashboard** để xem tổng quan:

| KPI | Ý nghĩa | Trend tốt |
|---|---|---|
| **MTTR trung bình** | Thời gian sửa chữa trung bình (giờ) | ↓ Giảm |
| **Tỷ lệ đúng hạn SLA** | % phiếu hoàn tất trong thời gian cam kết | ↑ Tăng |
| **Lỗi lặp lại** | % thiết bị hỏng lần 2+ trong 30 ngày | ↓ Giảm |
| **Phiếu đang mở** | Số phiếu chưa đóng | Tùy theo tình hình thực tế |
| **Tỷ lệ không sửa được** | % phiếu kết thúc bằng "Không sửa được" | ↓ Giảm |

Bấm vào biểu đồ để lọc theo thiết bị, khoa phòng, hoặc khoảng thời gian.

## I.7. Câu Hỏi Thường Gặp

**Q: Tôi không thấy phiếu sửa chữa vừa tạo trong danh sách?**
> A: Kiểm tra bộ lọc trạng thái ở góc trên danh sách — có thể đang lọc "Chỉ phiếu của tôi". Bỏ lọc để thấy tất cả (nếu bạn có quyền).

**Q: Hệ thống báo "Phải có nguồn sửa chữa" khi tạo phiếu?**
> A: Mọi phiếu sửa chữa phải gắn với báo cáo sự cố HOẶC phiếu bảo trì định kỳ. Nếu chưa có báo cáo sự cố, hãy tạo báo cáo trong module Sự cố (IMM-12) trước.

**Q: Checklist không cho submit vì có mục "Không đạt"?**
> A: Tất cả mục checklist phải ở trạng thái "Đạt" mới hoàn tất được phiếu. Nếu thiết bị thực sự không sửa được, dùng tùy chọn "Không sửa được" thay vì submit bình thường.

**Q: Tôi là KTV nhưng không thấy nút "Bắt đầu chẩn đoán"?**
> A: Nút này chỉ hiện khi phiếu đã ở trạng thái "Đã phân công" và được giao cho bạn. Liên hệ Trưởng xưởng để phân công.

**Q: Dashboard hiển thị số liệu MTTR 0?**
> A: MTTR chỉ tính cho phiếu đã *Hoàn tất*. Nếu chưa có phiếu nào hoàn tất trong kỳ, MTTR = 0 là đúng.

**Q: SLA "Hết hạn" màu đỏ nghĩa là gì?**
> A: Thời gian sửa chữa đã vượt quá cam kết theo phân loại thiết bị. Cần ưu tiên xử lý ngay.

**Q: Tôi lỡ tạo phiếu sai asset, có sửa được không?**
> A: Phiếu ở trạng thái *Mới tiếp nhận* vẫn có thể hủy (cần quyền Trưởng xưởng) rồi tạo lại. Sau khi đã phân công, liên hệ Admin.

## I.8. Phím Tắt & Mã Trạng Thái

| Phím | Chức năng |
|---|---|
| `⌘K` / `Ctrl+K` | Tìm kiếm nhanh toàn hệ thống |
| `Esc` | Đóng popup / hủy thao tác hiện tại |
| `Tab` | Chuyển sang trường kế tiếp trong form |
| `Ctrl+S` | Lưu bản nháp |

**Cheat sheet trạng thái phiếu:**

| Trạng thái | Ý nghĩa |
|---|---|
| Mới tiếp nhận | Phiếu vừa tạo, chưa phân công |
| Đã phân công | KTV được giao, thiết bị đang Under Repair |
| Đang chẩn đoán | KTV đang kiểm tra |
| Chờ vật tư | Đang đợi kho xuất phụ tùng |
| Đang sửa chữa | KTV đang thực hiện sửa |
| Chờ nghiệm thu | Sửa xong, đang đợi xác nhận |
| Hoàn tất | Thiết bị đã Active, MTTR ghi nhận |
| Không sửa được | Thiết bị chuyển Out of Service |
| Đã hủy | Phiếu bị hủy có lý do |

## I.9. Liên Hệ Hỗ Trợ

| Vấn đề | Liên hệ |
|---|---|
| Không đăng nhập được, quên mật khẩu | IT Helpdesk: ext. 1234 hoặc it@hospital.vn |
| Lỗi hiển thị, tính năng không hoạt động | Support AssetCore: support@assetcore.vn |
| Câu hỏi quy trình, nghiệp vụ | Trưởng xưởng kỹ thuật VTTBYT |
| Khẩn cấp (thiết bị Class III hỏng, SLA sắp hết) | Hotline: 0903.xxx.xxx (24/7) |

## I.10. Lịch Sử Cập Nhật Tài Liệu

| Phiên bản | Ngày | Thay đổi | Owner |
|---|---|---|---|
| 1.0.0 | 2026-05-08 | Phát hành lần đầu — Module IMM-09 GA | BA Lead |

---

# Phần II — Release Notes

## II.1. Tóm Tắt

Phiên bản 1.0.0 (2026-05-08) đưa module **Sửa chữa khắc phục (IMM-09)** vào vận hành chính thức. Module quản lý toàn bộ vòng đời sửa chữa thiết bị y tế, đo MTTR, và phát hiện lỗi lặp lại tự động. Downtime dự kiến 30-60 phút trong cửa sổ bảo trì đêm.

## II.2. Tính Năng Mới

### Quản lý phiếu sửa chữa (Trưởng xưởng + Kỹ thuật viên)

Tạo và theo dõi phiếu sửa chữa với 9 trạng thái workflow từ tiếp nhận đến hoàn tất. Mọi phiếu truy xuất được đến nguồn sự cố hoặc PM gốc.

- Tạo phiếu từ Incident Report hoặc PM Work Order halted
- Phân công kỹ thuật viên với thông báo tự động
- SLA tự động theo phân loại thiết bị (Class I/II/III) × mức ưu tiên
- Phiếu không thể sửa được → tự động chuyển thiết bị Out of Service

[→ Hướng dẫn: §I.5.a]

### Chẩn đoán và xuất vật tư có chứng từ (Kỹ thuật viên + Kho)

Kỹ thuật viên ghi nhận nguyên nhân, đính kèm ảnh. Vật tư sử dụng phải có mã chứng từ xuất kho — bảo đảm traceability theo NĐ98.

- Ghi nguyên nhân gốc rễ (6 loại)
- Upload ảnh thiết bị hỏng
- Mỗi vật tư gắn chứng từ xuất kho bắt buộc
- Kiểm soát thay đổi firmware qua phiếu duyệt riêng

[→ Hướng dẫn: §I.5.b, §I.5.c]

### Checklist nghiệm thu + Xác nhận trưởng khoa (Kỹ thuật viên + Trưởng khoa)

Hệ thống yêu cầu 100% mục checklist đạt trước khi hoàn tất. Trưởng khoa xác nhận bàn giao trực tiếp trên hệ thống.

- Checklist có thể tùy chỉnh theo danh mục thiết bị
- Block submit nếu còn mục Không đạt
- Chữ ký điện tử trưởng khoa ghi nhận thời gian

[→ Hướng dẫn: §I.5.d]

### MTTR Report + Dashboard KPI (Phó Trưởng phòng VTTBYT)

Dashboard thời gian thực với MTTR trung bình, tỷ lệ SLA, phát hiện lỗi lặp lại.

- MTTR tính tự động theo calendar time sau khi hoàn tất
- Drill-down theo thiết bị, khoa, risk class, khoảng thời gian
- Phát hiện thiết bị hỏng ≥ 2 lần/30 ngày → gợi ý mở CAPA

[→ Hướng dẫn: §I.6]

## II.3. Cải Tiến

| Mô tả | Module | Tác động |
|---|---|---|
| Asset status tự động cập nhật (Under Repair ↔ Active) | IMM-00 Integration | Trạng thái thực tế luôn đúng trên dashboard tổng hợp |
| Scheduler SLA check mỗi giờ | IMM-09 | Cảnh báo kịp thời, không phải kiểm tra thủ công |
| Link PM WO → CM WO tự động | IMM-08 Integration | Truy xuất ngược từ phiếu PM sang phiếu sửa chữa |

## II.4. Sửa Lỗi

| Mã issue | Mô tả | Severity |
|---|---|---|
| (Module mới — không có bug fix release này) | — | — |

## II.5. Thay Đổi Không Backward-compat

Không có thay đổi breaking cho người dùng hiện tại. Module IMM-09 là module mới hoàn toàn.

## II.6. Deprecations

Không có.

## II.7. Yêu Cầu Nâng Cấp

**Stack version:** Không thay đổi (Frappe v15, Python 3.11, Node 20).

**Migration tự động:** Patch `v3_0.*` chạy tự động khi `bench migrate`. Xem chi tiết §I.3 trong `08_Deployment.md`.

**Training bắt buộc:** 5 role phải hoàn tất training trước khi sử dụng. Thời lượng 30 phút đến 3 giờ tùy role. Xem `08_Deployment.md §II.7`.

## II.8. Downtime / Compatibility / Known Issues

**Downtime:** 30-60 phút trong maintenance window 23:00-02:00 ngày deploy.

**Khả năng tương thích:**

| Môi trường | Hỗ trợ |
|---|---|
| Chrome ≥ 120 | ✅ |
| Edge ≥ 120 | ✅ |
| Firefox ≥ 121 | ✅ |
| Safari ≥ 17 | ✅ |
| Mobile (responsive) | ✅ (giới hạn — tablet khuyến nghị) |

**Known issues:**

| Vấn đề | Workaround | Fix dự kiến |
|---|---|---|
| `search_spare_parts` API chưa whitelist (endpoint 3.11) | Dùng API `frappe.client.get_list "Item"` thay thế | v1.0.1 |
| Rate limit `create_repair_work_order` chưa cấu hình | Hạn chế gọi API từ external integration | v1.1.0 |

## II.9. Liên Kết & Lịch Sử Versioning

- User Guide: §I file này
- Functional Specs: [IMM-09_Functional_Specs.md](./IMM-09_Functional_Specs.md)
- Deployment Plan: [08_Deployment.md](./08_Deployment.md)
- Báo lỗi: `support@assetcore.vn` hoặc GitHub Issues

| Version | Ngày | Nội dung |
|---|---|---|
| 1.0.0 | 2026-05-08 | IMM-09 General Availability |

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
| US-09-01 | Story | Tạo CM WO với nguồn bắt buộc | Func Specs §3 | `services/imm09.py: validate_repair_source()` | `test_validate_ok_with_ir`, `test_validate_fail_no_source` | UAT-IMM09-01, UAT-IMM09-02 | #imm09-core | v1.0.0 | ✅ |
| US-09-02 | Story | Phân công KTV theo risk class | Func Specs §3 | `api/imm09.py: assign_technician()` | `TestWorkflow: test_assign_ktv_workshop_lead` | UAT-IMM09-03 | #imm09-core | v1.0.0 | ✅ |
| US-09-03 | Story | KTV chẩn đoán + ghi root cause | Func Specs §3 | `api/imm09.py: submit_diagnosis()` | `TestWorkflow: test_diagnosing_transition` | UAT-IMM09-03 | #imm09-core | v1.0.0 | ✅ |
| US-09-04 | Story | Xuất vật tư có chứng từ | Func Specs §3 | `services/imm09.py: validate_spare_parts_stock_entries()` | `TestSpareParts: test_validate_happy` | UAT-IMM09-04 | #imm09-core | v1.0.0 | ✅ |
| US-09-05 | Story | Firmware change control | Func Specs §3 | `services/imm09.py: validate_firmware_change_request()` | `TestFirmwareCR: test_validate_approved_ok` | UAT-IMM09-07 | #imm09-core | v1.0.0 | ✅ |
| US-09-06 | Story | Checklist nghiệm thu 100% Pass | Func Specs §3 | `services/imm09.py: validate_repair_checklist_complete()` | `TestChecklist: test_all_pass_ok` | UAT-IMM09-05 | #imm09-core | v1.0.0 | ✅ |
| US-09-07 | Story | Phát hiện lỗi lặp lại + CAPA | Func Specs §3 | `services/imm09.py: check_repeat_failure()` | `TestRepeatFailure: test_flag_repeat` | UAT-IMM09-08 | #imm09-core | v1.0.0 | ✅ |
| US-09-08 | Story | Cannot Repair + Asset Out of Service | Func Specs §3 | `services/imm09.py: _mark_cannot_repair()` | `test_on_submit_cannot_repair` | UAT-IMM09-06 | #imm09-core | v1.0.0 | ✅ |
| US-09-09 | Story | MTTR Report + Dashboard KPI | Func Specs §3 | `api/imm09.py: get_mttr_report()`, `get_repair_kpis()` | `test_get_kpis` | UAT-IMM09-11 | #imm09-core | v1.0.0 | ✅ |
| BR-09-01 | Rule | WO phải có ≥ 1 nguồn (IR hoặc PM WO) | Module Overview §7 | `validate_repair_source()` before_insert | `test_validate_fail_no_source` | UAT-IMM09-02 | #imm09-core | v1.0.0 | ✅ |
| BR-09-02 | Rule | Spare Parts phải có stock_entry_ref | Module Overview §7 | `validate_spare_parts_stock_entries()` before_submit | `TestSpareParts: test_validate_fail_missing_ref` | UAT-IMM09-04 | #imm09-core | v1.0.0 | ✅ |
| BR-09-03 | Rule | Firmware update phải có FCR Approved | Module Overview §7 | `validate_firmware_change_request()` before_submit | `TestFirmwareCR: test_validate_fail_draft` | UAT-IMM09-07 | #imm09-core | v1.0.0 | ✅ |
| BR-09-04 | Rule | Checklist 100% Pass trước Submit | Module Overview §7 | `validate_repair_checklist_complete()` before_submit | `TestChecklist: test_fail_one_row` | UAT-IMM09-05 | #imm09-core | v1.0.0 | ✅ |
| BR-09-05 | Rule | Asset status gắn liền workflow | Module Overview §7 | `set_asset_under_repair()`, `complete_repair()` | `test_on_insert_sets_asset_under_repair`, `test_on_submit_complete_repair` | UAT-IMM09-05 | #imm09-core | v1.0.0 | ✅ |
| BR-09-06 | Rule | Repeat failure → is_repeat_failure flag | Module Overview §7 | `check_repeat_failure()` | `TestRepeatFailure: test_flag_repeat` | UAT-IMM09-08 | #imm09-core | v1.0.0 | ✅ |
| BR-09-07 | Rule | SLA breach detect + flag | Module Overview §7 | `complete_repair()`, `check_repair_sla_breach()` | `TestScheduler: test_breach_flag_set` | UAT-IMM09-09 | #imm09-core | v1.0.0 | ✅ |
| NĐ98/Điều 22.3 | Compliance | Chứng từ vật tư ≥ 1 | 08 §II.2 | BR-09-02 enforce | UAT-IMM09-04 | UAT-IMM09-04 | #imm09-core | v1.0.0 | ✅ |
| NĐ98/Điều 15.2 | Compliance | Lưu trữ ≥ 5 năm audit | 08 §II.2 | `IMM Audit Trail` immutable | `test_audit_chain_intact` | UAT-IMM09-12 | #imm09-core | v1.0.0 | ✅ |
| WHO HTM §5.4.2 | Compliance | CM source truy xuất được | 08 §II.2 | BR-09-01 | `test_validate_fail_no_source` | UAT-IMM09-02 | #imm09-core | v1.0.0 | ✅ |
| WHO HTM §6.1 | Compliance | Đo MTTR | 08 §II.2 | `complete_repair()` | `TestComplete: test_mttr_calc` | UAT-IMM09-05 | #imm09-core | v1.0.0 | ✅ |
| ISO 13485 §8.5 | Compliance | CAPA cho repeat failure | 08 §II.2 | BR-09-06 | `TestRepeatFailure` | UAT-IMM09-08 | #imm09-core | v1.0.0 | ✅ |
| SEC-IMM09-01 | Security | KTV chỉ thấy WO của mình | 07 §III.1 | `permissions.py: asset_repair_query()` | `test_permission_ktv_scope` | UAT-IMM09-10 | #imm09-core | v1.0.0 | ✅ |
| SEC-IMM09-02 | Security | Audit chain không thể tamper | 07 §III.3 | `IMM Audit Trail` DocPerm no-delete | `test_audit_chain_breaks_on_tamper` | UAT-IMM09-12 | #imm09-core | v1.0.0 | ✅ |

## III.3. Reverse Lookup

| Test ID | Requirement(s) cover |
|---|---|
| `test_validate_ok_with_ir` | US-09-01, BR-09-01 |
| `test_validate_fail_no_source` | US-09-01, BR-09-01, WHO HTM §5.4.2 |
| `TestSpareParts: test_validate_fail_missing_ref` | US-09-04, BR-09-02, NĐ98/Điều 22.3 |
| `TestFirmwareCR: test_validate_fail_draft` | US-09-05, BR-09-03 |
| `TestChecklist: test_all_pass_ok` | US-09-06, BR-09-04 |
| `TestRepeatFailure: test_flag_repeat` | US-09-07, BR-09-06, ISO 13485 §8.5 |
| `test_on_submit_complete_repair` | US-09-08, BR-09-05, WHO HTM §6.1 |
| `test_audit_chain_intact` | NĐ98/Điều 15.2, SEC-IMM09-02 |
| `test_audit_chain_breaks_on_tamper` | SEC-IMM09-02 |
| `test_permission_ktv_scope` | SEC-IMM09-01 |

## III.4. Coverage Gaps

Sau rà soát matrix, không có req Must/Should còn ⬜ trước v1.0.0. Gaps roadmap:

| Req ID | Thiếu gì? | Owner | Deadline |
|---|---|---|---|
| `search_spare_parts` (API 3.11) | Endpoint chưa whitelist | Dev IMM-09 | v1.0.1 |
| Rate limit `create_repair_work_order` | Security roadmap | DevOps | v1.1.0 |
| Pentest report `docs/security/` | Report chưa upload | Security | Trước go-live |
| 2FA | Roadmap Phase 2 | Tech Lead | v2.0 |

## III.5. Cập Nhật Quy Ước

| Khi | Ai update | Cell nào |
|---|---|---|
| 02 có req mới (User Story / BR) | BA Lead | Thêm dòng, điền `Req ID`, `Loại`, `Mô tả`, `Doc ref` |
| Design xong | Tech Lead | Điền `Design / Code` (file:function) |
| PR merged | Dev | Điền `PR` |
| Test case viết xong | Dev/QA | Điền `Test ID` |
| UAT pass | QA Lead | Điền `UAT ID` + status ✅ |
| Release | PM | Điền `Released-in` + chốt status |

## III.6. Audit-readiness — Quick Links

**Auditor hỏi:** "Làm sao chứng minh vật tư đã sửa chữa máy thở ngày 15/04/2026 đều có chứng từ?"

Trace: `BR-09-02 → validate_spare_parts_stock_entries() → Spare Parts Used.stock_entry_ref → Stock Entry SE-2026-xxxxx`

---

**Auditor hỏi:** "Có thể kiểm tra ai đã xác nhận nghiệm thu thiết bị X không?"

Trace: `Asset Repair WO-CM-2026-xxxxx → dept_head_name + dept_head_confirmation_datetime → IMM Audit Trail record → hash chain verify`

---

**Auditor hỏi:** "Thiết bị hỏng 3 lần trong 30 ngày có được xử lý không?"

Trace: `BR-09-06 → check_repeat_failure() → Asset Repair.is_repeat_failure = 1 → Khuyến nghị IMM CAPA Record`

## III.7. Bảng Thống Kê Thông Tin Ứng Dụng

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| DocType (chính) | 2 | `Asset Repair`, `Firmware Change Request` |
| DocType (child) | 2 | `Spare Parts Used`, `Repair Checklist` |
| Workflow JSON | 1 | `IMM-09 Repair Workflow` — 9 states, 15 transitions |
| API endpoint | 12 | `list, get, create, assign, diagnose, parts, start, close, kpis, mttr, search_parts, history` |
| FE view / page | 8 | CMDashboard, CMList, CMDetail, CMCreate, CMDiagnose, CMParts, CMChecklist, CMMttr |
| FE store | 1 | `stores/imm09.ts` |
| Service function | 12 | `validate_repair_source, check_repeat_failure, complete_repair, ...` (xem Module Overview §4) |
| Scheduler job | 3 | Hourly SLA breach, Daily overdue, Monthly MTTR rollup |
| Business Rule | 7 | BR-09-01 → BR-09-07 |
| Role áp dụng | 6 | Workshop Lead, Biomed Technician, Storekeeper, Dept Head, Ops Manager, QA Officer |
| Test case unit | ~35 | 10 test class × ~3.5 case avg |
| UAT scenario | 12 | UAT-IMM09-01 → 12 |
| LOC BE (`services/imm09.py`) | ~350 | Không tính comments |
| LOC API (`api/imm09.py`) | ~200 | 12 endpoints |
| LOC FE (tất cả views + store) | ~1,800 | Ước tính từ 8 views + 1 store |
| Sprint hoàn thành (Wave 1) | 4 | Sprint 1-4, mỗi sprint 2 tuần |
| User Story | 9 | US-09-01 → 09-09 |

---

## DoD — Hoàn chỉnh

### I. User Guide
- [x] Tiếng Việt 100%, không jargon
- [x] Mô tả tất cả 5 role với hướng dẫn step-by-step
- [x] Dashboard KPI có giải thích trend
- [x] FAQ 7 câu thực tế
- [x] Cheat sheet trạng thái + phím tắt
- [ ] ≥ 5 screenshot UI thực tế (cần chụp trên staging trước go-live)
- [ ] Reviewed bởi BA + đại diện end-user (Workshop Manager)

### II. Release Notes
- [x] Tóm tắt 2-3 câu user-friendly
- [x] 4 tính năng mới có role hưởng lợi
- [x] Known issues + workaround documented
- [x] Breaking change: không có
- [x] Downtime và compatibility table
- [ ] Reviewed bởi PM + Tech Lead + BA

### III. Traceability Matrix + Bảng Thống Kê
- [x] 23 dòng: 9 User Story + 7 BR + 4 Compliance + 3 Security
- [x] Mọi dòng ✅ có ≥ 4 cell điền
- [x] Reverse lookup table
- [x] Coverage gaps liệt kê (4 gaps, đều là roadmap — không có Must còn ⬜)
- [x] Bảng thống kê 15 hạng mục
- [ ] Reviewed bởi PM + Tech Lead + QA Lead
