# IMM-08 — Phát hành (User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | **IMM-08 — Bảo trì Định kỳ (Preventive Maintenance)** |
| Phiên bản | 1.0.0 |
| Ngày phát hành | 2026-05-08 |
| Owner | PM + BA + Tech Writer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) · [Functional Specs](./IMM-08_Functional_Specs.md) |
| Cập nhật | 2026-05-14 |

---

# Phần I — Hướng Dẫn Sử Dụng

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.

## I.1. Giới Thiệu

Module **Bảo trì định kỳ (IMM-08)** giúp đội ngũ kỹ thuật y tế quản lý toàn bộ lịch bảo trì phòng ngừa cho thiết bị y tế — từ khi thiết bị được bàn giao cho đến khi nghỉ hưu.

Hệ thống tự động tạo phiếu bảo trì khi đến hạn, cảnh báo khi trễ hạn, và ghi lại đầy đủ kết quả mỗi lần bảo trì. Khi phát hiện lỗi trong quá trình bảo trì, hệ thống tự động tạo phiếu sửa chữa liên kết, đảm bảo không bỏ sót bất kỳ vấn đề nào.

**Trước khi bắt đầu, bạn cần:**
- Tài khoản hệ thống AssetCore (liên hệ IT nếu chưa có)
- Trình duyệt Chrome hoặc Edge phiên bản mới nhất (trên máy tính hoặc tablet)
- Kết nối mạng nội bộ bệnh viện

**Đăng nhập:**
1. Mở trình duyệt, truy cập: `https://assetcore.vn`
2. Nhập tên đăng nhập và mật khẩu do IT cấp
3. Bấm **Đăng nhập**

## I.2. Nhận Biết Bạn Đang Ở Đâu

Màn hình chính gồm 3 khu vực:

```
┌─────────────────────────────────────────────────┐
│  ① Thanh trên (Topbar) — Tìm kiếm, thông báo   │
├────────┬────────────────────────────────────────┤
│        │  ③ Vùng nội dung chính                 │
│ ②     │  (Danh sách / Chi tiết / Dashboard /    │
│ Sidebar│   Lịch bảo trì)                        │
│ (menu) │                                         │
└────────┴────────────────────────────────────────┘
```

- **② Sidebar**: Tìm **"Bảo trì định kỳ"** hoặc **"PM"** để vào IMM-08.
- Module IMM-08 có 3 mục chính: **Danh sách phiếu**, **Lịch bảo trì** (Calendar), và **Dashboard**.

## I.3. Các Vai Trò

| Vai trò | Bạn làm gì trong module này? |
|---|---|
| **Quản lý xưởng (Workshop Manager)** | Phân công kỹ thuật viên, xem lịch, hoãn lịch khi thiết bị bận, theo dõi tổng quan |
| **Kỹ thuật viên HTM (KTV)** | Nhận phiếu bảo trì được phân công, thực hiện kiểm tra theo checklist, báo cáo kết quả |
| **Phó Trưởng phòng VTTBYT** | Theo dõi Dashboard KPI, nhận cảnh báo khi thiết bị quá hạn bảo trì |

## I.4. Quy Trình Chính

```
① Đến hạn bảo trì → Hệ thống tự tạo phiếu PM
   (Scheduler tự động, mỗi sáng 06:00)
      │
      ▼
② Quản lý xưởng phân công KTV
      │
      ▼
③ KTV nhận phiếu, mang thiết bị vào xưởng
      │
      ▼
④ KTV điền checklist (kiểm tra từng hạng mục)
      │
      ├──► Tất cả Đạt → ⑤ Hoàn tất bảo trì
      │
      ├──► Phát hiện lỗi nhỏ → ⑤ Hoàn tất + Tạo phiếu sửa chữa (tự động)
      │
      └──► Phát hiện lỗi lớn → ⑥ Báo lỗi Major → Thiết bị tạm dừng sử dụng
                                                   + Phiếu sửa chữa khẩn (tự động)
```

**Lịch PM tiếp theo:**
> Hệ thống tự tính từ **ngày hoàn tất thực tế** (không phải ngày dự kiến) — đảm bảo chu kỳ PM luôn đúng.

## I.5. Thao Tác Theo Vai Trò

### a. Quản lý xưởng — Phân công và theo dõi

**Khi nào làm?** Mỗi sáng kiểm tra phiếu PM mới + xử lý phiếu quá hạn.

**Phân công kỹ thuật viên:**
1. Vào **Bảo trì → Danh sách phiếu** → filter *Chờ phân công (Open)*
2. Mở phiếu PM cần xử lý
3. Bấm **"Phân công"**, chọn KTV phù hợp
4. KTV nhận thông báo tự động

**Hoãn lịch khi thiết bị bận:**
1. Mở phiếu PM → bấm **"Hoãn lịch"**
2. Chọn ngày mới, nhập lý do hoãn (bắt buộc, tối thiểu 5 ký tự)
3. Lưu — phiếu chuyển sang *Chờ thiết bị*

**Xem lịch tổng quan:**
- Vào **Bảo trì → Lịch bảo trì** để xem theo tháng/tuần
- Màu sắc: 🟡 Chờ phân công · 🟢 Đang tiến hành · 🔴 Quá hạn · ⚫ Hoàn tất
- Click vào lịch để xem chi tiết và phân công nhanh

### b. Kỹ thuật viên — Thực hiện bảo trì

**Khi nào làm?** Sau khi nhận thông báo được phân công phiếu PM.

**Các bước:**
1. Đăng nhập, vào **Bảo trì → Phiếu của tôi** — danh sách phiếu được phân công
2. Mở phiếu → checklist hiển thị các hạng mục cần kiểm tra
3. Thực hiện kiểm tra thực tế trên thiết bị theo từng hạng mục
4. Điền kết quả: **Đạt / Lỗi nhỏ / Lỗi lớn** cho mỗi hạng mục
   - Nếu chọn Lỗi → bắt buộc nhập mô tả lỗi
5. Tích **"Đã gắn tem PM"** và nhập thời gian thực hiện
6. Đối với **thiết bị Class III**: chụp ảnh trước và sau khi bảo trì (bắt buộc)
7. Bấm **"Hoàn tất"** — hệ thống ghi nhận và cập nhật lịch PM kế tiếp

> ⚠️ **Lưu ý quan trọng:** Tất cả hạng mục trong checklist phải được điền kết quả trước khi hoàn tất. Không bỏ trống.

---

**Báo cáo lỗi nghiêm trọng (Lỗi lớn):**

Khi phát hiện lỗi có thể ảnh hưởng đến an toàn bệnh nhân:
1. Chọn hạng mục bị lỗi → **Lỗi lớn** + nhập mô tả chi tiết
2. Bấm **"Báo cáo lỗi nghiêm trọng"**
3. Xác nhận → thiết bị tự động chuyển sang *Tạm dừng sử dụng*
4. Phiếu sửa chữa khẩn được tạo tự động — quản lý xưởng và phó trưởng phòng nhận cảnh báo

> ⚠️ **Chú ý:** Thiết bị đang *Tạm dừng sử dụng* không được sử dụng cho bệnh nhân cho đến khi sửa chữa xong và được tái kích hoạt.

## I.6. Bảng Điều Khiển (Dashboard)

Vào **Bảo trì → Dashboard** để xem tổng quan:

| Chỉ số | Ý nghĩa | Trend tốt |
|---|---|---|
| **Tỷ lệ đúng hạn PM** | % phiếu hoàn tất trước ngày dự kiến | ↑ Tăng |
| **Phiếu quá hạn** | Số phiếu chưa hoàn tất sau ngày dự kiến | ↓ Giảm về 0 |
| **Trễ hạn trung bình** | Số ngày trung bình bị trễ | ↓ Giảm |
| **Tỷ lệ phủ sóng PM** | % thiết bị có lịch PM được theo dõi | ↑ Tăng về 100% |
| **Tỷ lệ lỗi Major** | % phiếu kết thúc bằng lỗi nghiêm trọng | ↓ Giảm |

Biểu đồ **Trend 6 tháng**: so sánh tỷ lệ đúng hạn theo tháng. Click vào cột để xem danh sách phiếu tháng đó.

## I.7. Câu Hỏi Thường Gặp

**Q: Tôi không thấy phiếu PM trong danh sách?**
> A: Phiếu PM được tạo tự động mỗi sáng 06:00 khi đến hạn (trước 7 ngày). Nếu phiếu chưa xuất hiện, kiểm tra lịch bảo trì trong **Lịch bảo trì** — nếu còn màu xám là chưa đến ngưỡng tạo phiếu.

**Q: Checklist trống — không có hạng mục nào?**
> A: Hệ thống cần template checklist cho loại thiết bị này. Liên hệ Quản lý xưởng để tạo template trước khi KTV có thể thực hiện PM.

**Q: Tôi đã điền xong nhưng nút "Hoàn tất" vẫn bị mờ (disabled)?**
> A: Kiểm tra xem còn hạng mục nào chưa điền kết quả. Đối với thiết bị Class III, kiểm tra đã upload ảnh chưa. Thanh tiến trình phải đạt 100%.

**Q: Thiết bị đang bị bệnh nhân sử dụng — không bảo trì được hôm nay?**
> A: Dùng tính năng "Hoãn lịch" (yêu cầu quyền Quản lý xưởng) — nhập lý do và ngày mới. Phiếu chuyển sang trạng thái *Chờ thiết bị*.

**Q: Tôi báo lỗi Major nhưng thiết bị vẫn đang dùng ở phòng mổ?**
> A: Ngay sau khi báo lỗi Major, hệ thống gửi cảnh báo khẩn cho Quản lý xưởng và Phó trưởng phòng. Khoa phòng cần được thông báo ngay để dừng sử dụng thiết bị. Liên hệ Quản lý xưởng để phối hợp.

**Q: Dashboard hiển thị tỷ lệ đúng hạn thấp — tại sao?**
> A: Tỷ lệ đúng hạn = số phiếu hoàn tất trước ngày dự kiến / tổng số phiếu. Xem bảng "Quá hạn" để xác định phiếu nào cần ưu tiên xử lý.

**Q: Lịch PM kế tiếp tính sai?**
> A: Lịch PM kế tiếp = ngày hoàn tất thực tế + chu kỳ bảo trì (không phải ngày dự kiến). Đây là đúng theo quy định — chu kỳ tính từ lần bảo trì cuối thực sự.

## I.8. Phím Tắt & Mã Trạng Thái

| Phím | Chức năng |
|---|---|
| `⌘K` / `Ctrl+K` | Tìm kiếm nhanh toàn hệ thống |
| `Esc` | Đóng popup |
| `Tab` | Chuyển hạng mục checklist tiếp theo |
| `Ctrl+S` | Lưu bản nháp |

**Cheat sheet trạng thái phiếu PM:**

| Trạng thái | Ý nghĩa | Màu |
|---|---|---|
| Chờ phân công | Phiếu mới tạo, chưa giao KTV | 🟡 Vàng |
| Đang tiến hành | KTV đang thực hiện bảo trì | 🔵 Xanh |
| Chờ thiết bị | Hoãn lịch, chờ thiết bị rảnh | ⚪ Xám |
| Quá hạn | Đã qua ngày dự kiến, chưa hoàn tất | 🔴 Đỏ |
| Hoàn tất | Bảo trì xong, Task Log ghi nhận | 🟢 Xanh lá |
| Dừng – Lỗi lớn | Phát hiện lỗi nghiêm trọng, đang chờ sửa | ⛔ Đỏ đậm |
| Đã hủy | Phiếu bị hủy có lý do | ❌ Xám |

## I.9. Liên Hệ Hỗ Trợ

| Vấn đề | Liên hệ |
|---|---|
| Không đăng nhập được, quên mật khẩu | IT Helpdesk: ext. 1234 hoặc it@hospital.vn |
| Lỗi hiển thị, tính năng không hoạt động | Support AssetCore: support@assetcore.vn |
| Câu hỏi về quy trình bảo trì, lịch PM | Quản lý xưởng VTTBYT |
| Lỗi Major thiết bị quan trọng (Class III) | Hotline: 0903.xxx.xxx (24/7) |

## I.10. Lịch Sử Cập Nhật Tài Liệu

| Phiên bản | Ngày | Thay đổi | Owner |
|---|---|---|---|
| 1.0.0 | 2026-05-08 | Phát hành lần đầu — Module IMM-08 GA | BA Lead |

---

# Phần II — Release Notes

## II.1. Tóm Tắt

Phiên bản 1.0.0 (2026-05-08) đưa module **Bảo trì định kỳ (IMM-08)** vào vận hành chính thức. Module tự động hóa toàn bộ chu kỳ PM cho thiết bị y tế — từ tạo phiếu tự động đến phát hiện lỗi và kết nối với module sửa chữa — đảm bảo không thiết bị nào bị bỏ sót bảo trì và mọi lỗi đều được xử lý kịp thời. Downtime dự kiến 30-60 phút trong cửa sổ bảo trì đêm.

## II.2. Tính Năng Mới

### Lập lịch và tự động tạo phiếu PM (Quản lý xưởng + Hệ thống)

Hệ thống tự động tạo phiếu PM vào mỗi sáng 06:00 khi đến hạn (trước 7 ngày). Không thiết bị nào bị bỏ sót. Thiết bị đang Out of Service được tự động bỏ qua.

- Tự động tạo phiếu theo `PM Schedule` của từng thiết bị
- Checklist tự điền từ template chuẩn theo loại thiết bị
- Email thông báo Workshop Head mỗi ngày có phiếu mới
- Idempotent: không tạo phiếu trùng lặp

[→ Hướng dẫn: §I.5.a]

### Checklist kỹ thuật + Xử lý lỗi tự động (KTV HTM)

KTV điền checklist theo tiêu chuẩn nhà sản xuất. Khi phát hiện lỗi, hệ thống tự tạo phiếu sửa chữa liên kết — không cần thao tác thủ công.

- Checklist clone từ template chuẩn per asset_category × pm_type
- Kết quả: Đạt / Lỗi nhỏ / Lỗi lớn — Lỗi bắt buộc có mô tả
- Thiết bị Class III: bắt buộc upload ảnh trước/sau PM
- Lỗi nhỏ → tự tạo CM WO priority Medium
- Lỗi lớn → tự tạo CM WO priority Critical + Asset Out of Service

[→ Hướng dẫn: §I.5.b]

### Cảnh báo quá hạn + Leo thang (Hệ thống)

Scheduler 08:00 mỗi ngày phát hiện phiếu quá hạn và gửi email theo mức độ leo thang: Workshop Head (≤7 ngày), VP Block2 (8-30 ngày), BGĐ (>30 ngày).

- Tự động đánh dấu Overdue khi qua ngày dự kiến
- Leo thang email theo ngưỡng ngày
- Dashboard real-time hiển thị phiếu quá hạn màu đỏ

[→ Hướng dẫn: §I.6]

### Calendar + Dashboard KPI (Quản lý xưởng + VP Block2)

Xem lịch PM theo tháng với màu sắc trực quan. Dashboard hiển thị tỷ lệ đúng hạn, xu hướng 6 tháng, và drill-down theo thiết bị.

- Calendar tháng/tuần với filter theo KTV
- 5 KPI cards + trend chart 6 tháng
- Tỷ lệ đúng hạn = (phiếu on-time / tổng) × 100
- Click thiết bị → lịch sử PM đầy đủ

[→ Hướng dẫn: §I.6]

## II.3. Cải Tiến

| Mô tả | Module | Tác động |
|---|---|---|
| Asset Commissioning submit → tự tạo PM Schedule đầu tiên | IMM-04 Integration | Không cần tạo thủ công PM Schedule khi có thiết bị mới |
| CM WO tự động có `source_pm_wo` link về PM gốc | IMM-09 Integration | Truy xuất ngược từ phiếu sửa chữa về PM phát hiện lỗi |
| Asset.custom_pm_status cập nhật realtime | IMM-00 Integration | Dashboard tổng hợp luôn hiển thị đúng trạng thái PM |

## II.4. Sửa Lỗi

| Mã issue | Mô tả | Severity |
|---|---|---|
| (Module mới — không có bug fix release này) | — | — |

## II.5. Thay Đổi Không Backward-compat

Không có thay đổi breaking cho người dùng hiện tại. IMM-08 là module mới hoàn toàn trong Wave 1.

**Ảnh hưởng đến Asset Commissioning (IMM-04):** Từ v1.0.0, khi submit Asset Commissioning sẽ tự động tạo PM Schedule đầu tiên. Commissioning records cũ không bị ảnh hưởng.

## II.6. Deprecations

Không có.

## II.7. Yêu Cầu Nâng Cấp

**Stack version:** Không thay đổi (Frappe v15, Python 3.11, Node 20).

**Migration tự động:** Patch `v3_0.*` chạy tự động khi `bench migrate`. Xem chi tiết §I.3 trong `08_Deployment.md`.

**Migration thủ công (Admin + Workshop Head):**
1. Tạo `PM Checklist Template` cho mọi `asset_category` đang active trước go-live
2. Tạo `PM Schedule` thủ công cho các thiết bị đã commissioning trước v1.0.0 (nếu chưa có)
3. Seed initial `next_due_date` dựa trên lịch PM giấy hiện tại

**Training bắt buộc:** 4 role phải hoàn tất training trước khi sử dụng. Xem `08_Deployment.md §II.7`.

## II.8. Downtime / Compatibility / Known Issues

**Downtime:** 30-60 phút trong maintenance window 23:00-02:00 ngày deploy.

**Khả năng tương thích:**

| Môi trường | Hỗ trợ |
|---|---|
| Chrome ≥ 120 | ✅ |
| Edge ≥ 120 | ✅ |
| Firefox ≥ 121 | ✅ |
| Safari ≥ 17 | ✅ |
| Tablet (Android/iPad — checklist mobile) | ✅ khuyến nghị dùng tablet |
| Mobile phone 375px | ✅ (giới hạn — khuyến nghị tablet) |

**Known issues:**

| Vấn đề | Workaround | Fix dự kiến |
|---|---|---|
| Mobile offline checklist (IndexedDB queue) chưa hỗ trợ | Đảm bảo WiFi trong khi điền checklist | v2.1 |
| Holiday list integration chưa có (tính due_date không trừ ngày lễ) | Điều chỉnh `next_due_date` thủ công nếu trùng lễ | v2.2 |
| Rate limit `report_major_failure` chưa cấu hình | — | v1.0.1 |

## II.9. Liên Kết & Lịch Sử Versioning

- User Guide: §I file này
- Functional Specs: [IMM-08_Functional_Specs.md](./IMM-08_Functional_Specs.md)
- Deployment Plan: [08_Deployment.md](./08_Deployment.md)
- Báo lỗi: `support@assetcore.vn` hoặc GitHub Issues

| Version | Ngày | Nội dung |
|---|---|---|
| 1.0.0 | 2026-05-08 | IMM-08 General Availability (Wave 1) |

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
| US-08-01 | Story | Tự động tạo PM WO khi đến hạn | Func Specs §3 | `tasks.py: generate_pm_work_orders()` | `TestGeneratePMWorkOrders: test_creates_wo_when_due` | UAT-IMM08-01 | #imm08-core | v1.0.0 | ✅ |
| US-08-02 | Story | KTV điền checklist + submit Completed | Func Specs §3 | `api/imm08.py: submit_pm_result()` | `test_submit_pm_result_happy` | UAT-IMM08-02 | #imm08-core | v1.0.0 | ✅ |
| US-08-03 | Story | Major Failure → Asset Out of Service | Func Specs §3 | `api/imm08.py: report_major_failure()` | `test_on_submit_fail_major_out_of_service` | UAT-IMM08-05 | #imm08-core | v1.0.0 | ✅ |
| US-08-04 | Story | PM Overdue + email leo thang | Func Specs §3 | `tasks.py: check_pm_overdue()` | `TestCheckPMOverdue` | UAT-IMM08-03 | #imm08-core | v1.0.0 | ✅ |
| US-08-05 | Story | Block tạo PM cho Asset Out of Service | Func Specs §3 | `tasks.generate_pm_work_orders()` BR-08-04 skip | `TestGeneratePMWorkOrders: test_skip_when_out_of_service` | UAT-IMM08-01 | #imm08-core | v1.0.0 | ✅ |
| US-08-06 | Story | Reschedule PM khi thiết bị bận | Func Specs §3 | `api/imm08.py: reschedule_pm()` | `TestReschedule: test_happy` | UAT-IMM08-06 | #imm08-core | v1.0.0 | ✅ |
| US-08-07 | Story | IMM-04 commissioning auto-tạo PM Schedule | Func Specs §3 | `services/imm04.py: on_submit hook` | `test_imm04_hook_creates_pm_schedule` | UAT-IMM08-07 | #imm08-core | v1.0.0 | ✅ |
| US-08-08 | Story | Dashboard KPI | Func Specs §3 | `api/imm08.py: get_pm_dashboard_stats()` | `test_get_dashboard_stats` | UAT-IMM08-08 | #imm08-core | v1.0.0 | ✅ |
| BR-08-01 | Rule | PM WO cần Checklist Template | Module Overview §7 | `generate_pm_work_orders()` skip + email | `TestGeneratePMWorkOrders: test_skip_no_template` | UAT-IMM08-01 | #imm08-core | v1.0.0 | ✅ |
| BR-08-02 | Rule | CM WO phải có source_pm_wo | Module Overview §7 | `_validate_cm_source()` | `TestValidateCmSource: test_no_source_raises` | UAT-IMM08-04 | #imm08-core | v1.0.0 | ✅ |
| BR-08-03 | Rule | next_pm_date = completion_date + interval | Module Overview §7 | `_update_pm_schedule()` | `TestUpdatePMSchedule: test_uses_completion_not_due` | UAT-IMM08-02 step 6 | #imm08-core | v1.0.0 | ✅ |
| BR-08-04 | Rule | Out of Service → block PM WO | Module Overview §7 | `generate_pm_work_orders()` skip | `TestGeneratePMWorkOrders: test_skip_when_out_of_service` | UAT-IMM08-01, 05 | #imm08-core | v1.0.0 | ✅ |
| BR-08-05 | Rule | is_late = (completion > due) | Module Overview §7 | `_set_completion()` | `TestIsLate` | UAT-IMM08-02, 03 | #imm08-core | v1.0.0 | ✅ |
| BR-08-06 | Rule | Class III bắt buộc ảnh | Module Overview §7 | `_validate_photo_for_high_risk()` | `TestValidatePhoto: test_class3_no_photo_raises` | UAT-IMM08-05 step 2 | #imm08-core | v1.0.0 | ✅ |
| BR-08-07 | Rule | PM Schedule unique per (asset, pm_type) | Module Overview §7 | Naming `PMS-{asset}-{pm_type}` | `TestValidators: test_unique_pm_schedule` | (naming test) | #imm08-core | v1.0.0 | ✅ |
| BR-08-08 | Rule | Checklist 100% có result trước Submit | Module Overview §7 | `_validate_checklist_complete()` | `TestValidateChecklist: test_empty_result_raises` | UAT-IMM08-02 step 3 | #imm08-core | v1.0.0 | ✅ |
| BR-08-09 | Rule | Fail-Minor → CM Medium; Fail-Major → CM Critical + OOS | Module Overview §7 | `_handle_failures()` | `TestHandleFailures` | UAT-IMM08-04, 05 | #imm08-core | v1.0.0 | ✅ |
| BR-08-10 | Rule | PM Task Log immutable | Module Overview §7 | `in_create=1` + DocPerm no-write | `test_pm_task_log_immutable_after_create` | UAT-IMM08-02 step 8 | #imm08-core | v1.0.0 | ✅ |
| NĐ98/Điều 22 | Compliance | Phiếu bảo trì cho mọi action | 08 §II.2 | BR-08-01 enforce | UAT-IMM08-01, 02 | UAT-IMM08-02 | #imm08-core | v1.0.0 | ✅ |
| NĐ98/Điều 22.1 | Compliance | Kế hoạch PM định kỳ | 08 §II.2 | `PM Schedule` + scheduler | UAT-IMM08-01 | UAT-IMM08-01 | #imm08-core | v1.0.0 | ✅ |
| NĐ98/Điều 23 | Compliance | Hỏng nặng → Out of Service | 08 §II.2 | BR-08-09 + BR-08-04 | UAT-IMM08-05 | UAT-IMM08-05 | #imm08-core | v1.0.0 | ✅ |
| WHO HTM §5.3 | Compliance | PM theo checklist chuẩn | 08 §II.2 | BR-08-01 template + BR-08-08 100% | `TestValidateChecklist` | UAT-IMM08-02 | #imm08-core | v1.0.0 | ✅ |
| WHO HTM §5.3.2 | Compliance | PM từ completion_date không từ due_date | 08 §II.2 | BR-08-03 | `TestUpdatePMSchedule` | UAT-IMM08-02 | #imm08-core | v1.0.0 | ✅ |
| ISO 13485 §4.2.4 | Compliance | Hồ sơ PM lưu trữ đủ | 08 §II.2 | `PM Task Log` `in_create=1` | `test_audit_trail_immutable` | UAT-IMM08-02 step 8 | #imm08-core | v1.0.0 | ✅ |
| SEC-IMM08-01 | Security | KTV chỉ thấy/submit WO của mình | 07 §III.1 | `permissions.py: pm_work_order_query()` | `test_no_permission_operator` | UAT-IMM08-10 | #imm08-core | v1.0.0 | ✅ |
| SEC-IMM08-02 | Security | PM Task Log không thể tamper | 07 §III.3 | `in_create=1` + DocPerm | `test_pm_task_log_immutable_after_create` | UAT-IMM08-02 step 8 | #imm08-core | v1.0.0 | ✅ |

## III.3. Reverse Lookup

| Test ID | Requirement(s) cover |
|---|---|
| `TestGeneratePMWorkOrders: test_creates_wo_when_due` | US-08-01, BR-08-01, NĐ98/Điều 22.1 |
| `TestGeneratePMWorkOrders: test_skip_when_out_of_service` | US-08-05, BR-08-04 |
| `TestGeneratePMWorkOrders: test_idempotent_no_duplicate` | US-08-01, BR-08-01 |
| `TestUpdatePMSchedule: test_uses_completion_not_due` | US-08-02, BR-08-03, WHO HTM §5.3.2 |
| `TestHandleFailures: test_fail_major_creates_critical_cm` | US-08-03, BR-08-09, NĐ98/Điều 23 |
| `TestIsLate: test_late_when_completion_after_due` | US-08-02, BR-08-05 |
| `TestValidateChecklist: test_empty_result_raises` | US-08-02, BR-08-08, WHO HTM §5.3 |
| `TestValidatePhoto: test_class3_no_photo_raises` | US-08-03, BR-08-06 |
| `test_pm_task_log_immutable_after_create` | BR-08-10, ISO 13485 §4.2.4, SEC-IMM08-02 |
| `test_audit_chain_intact` | NĐ98/Điều 15.2, SEC-IMM08-02 |
| `test_audit_chain_breaks_on_tamper` | SEC-IMM08-02 |

## III.4. Coverage Gaps

Sau rà soát matrix, không có req Must/Should còn ⬜ trước v1.0.0. Gaps roadmap:

| Req ID | Thiếu gì? | Owner | Deadline |
|---|---|---|---|
| Mobile offline checklist (IndexedDB) | Feature chưa implement | Dev IMM-08 | v2.1 |
| Holiday list integration | Feature chưa implement | Dev IMM-08 | v2.2 |
| Rate limit `report_major_failure` | Security roadmap | DevOps | v1.0.1 |
| Pentest report `docs/security/` | Report chưa upload | Security | Trước go-live |
| Calibration WO integration (IMM-11) | Out of scope Wave 1 | BA | Wave 2 |

## III.5. Cập Nhật Quy Ước

| Khi | Ai update | Cell nào |
|---|---|---|
| Có req mới (User Story / BR) | BA Lead | Thêm dòng, điền `Req ID`, `Loại`, `Mô tả`, `Doc ref` |
| Design xong | Tech Lead | Điền `Design / Code` |
| PR merged | Dev | Điền `PR` |
| Test case viết xong | Dev/QA | Điền `Test ID` |
| UAT pass | QA Lead | Điền `UAT ID` + status ✅ |
| Release | PM | Điền `Released-in` + chốt status |

## III.6. Audit-readiness — Quick Links

**Auditor hỏi:** "Làm sao chứng minh máy thở đã được bảo trì định kỳ đúng hạn trong năm 2026?"

Trace: `PM Schedule.history → PM Work Order list filter asset=X, year=2026 → PM Task Log per WO (immutable) → is_late flag → compliance_rate_pct`

---

**Auditor hỏi:** "Lỗi phát hiện trong bảo trì tháng 3 đã được xử lý như thế nào?"

Trace: `PM Work Order PM-WO-2026-xxxxx → checklist_results[Fail-Minor] → CM Work Order source_pm_wo=PM-WO-2026-xxxxx → CM WO status=Completed`

---

**Auditor hỏi:** "Thiết bị Class III có bắt buộc kiểm tra theo checklist không?"

Trace: `BR-08-01: PM Checklist Template bắt buộc → BR-08-08: 100% results → BR-08-06: Class III photo bắt buộc → PM Work Order.docstatus=1 (submitted, immutable)`

## III.7. Bảng Thống Kê Thông Tin Ứng Dụng

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| DocType (master/config) | 2 | `PM Schedule`, `PM Checklist Template` |
| DocType (operational) | 1 | `PM Work Order` |
| DocType (audit) | 1 | `PM Task Log` (immutable, `in_create=1`) |
| DocType (child) | 2 | `PM Checklist Item`, `PM Checklist Result` |
| Workflow JSON | 0 | PM WO dùng `status` field (workflow state machine trong controller) |
| API endpoint | 9 | `list_pm_work_orders, get_pm_work_order, assign_technician, submit_pm_result, report_major_failure, reschedule_pm, cancel_pm_wo, get_pm_dashboard_stats, get_pm_kpis` |
| FE view / page | 4 | `PMDashboardView`, `PMCalendarView`, `PMWorkOrderListView`, `PMWorkOrderDetailView` |
| FE store | 1 | `stores/imm08.ts` |
| Service function | 10 | `generate_pm_work_orders, check_pm_overdue, validate_checklist_complete, validate_photo_for_high_risk, validate_cm_source, update_pm_schedule, handle_failures, set_completion, create_pm_task_log, reschedule_pm` |
| Scheduler job | 2 | `generate_pm_work_orders` (daily 06:00), `check_pm_overdue` (daily 08:00) |
| Business Rule | 10 | BR-08-01 → BR-08-10 |
| Validation Rule | 10 | VR-08-01 → VR-08-10 |
| Role áp dụng | 5 | Workshop Head, HTM Technician, Biomed Engineer, VP Block2, CMMS Admin |
| Test case unit | ~40 | 10 test class × ~4 case avg |
| UAT scenario | 10 | UAT-IMM08-01 → 10 |
| User Story | 8 | US-08-01 → 08-08 |
| LOC BE (controller + tasks) | ~350 | Không tính comments |
| LOC API (`api/imm08.py`) | ~200 | 9 endpoints |
| LOC FE (4 views + 1 store) | ~1,200 | Ước tính |
| Sprint hoàn thành (Wave 1) | 2 | Sprint 3-4, mỗi sprint 2 tuần |

---

## DoD — Hoàn chỉnh

### I. User Guide
- [x] Tiếng Việt 100%, không jargon
- [x] Mô tả tất cả 3 role với hướng dẫn step-by-step
- [x] Dashboard KPI có giải thích trend
- [x] FAQ 7 câu thực tế (checklist, offline, major failure, hoãn lịch)
- [x] Cheat sheet trạng thái phiếu PM + phím tắt
- [ ] ≥ 5 screenshot UI thực tế (cần chụp trên staging trước go-live)
- [ ] Reviewed bởi BA + đại diện end-user (Workshop Manager)

### II. Release Notes
- [x] Tóm tắt 2-3 câu user-friendly
- [x] 4 tính năng mới có role hưởng lợi
- [x] Known issues + workaround documented
- [x] Breaking change: IMM-04 hook, migration thủ công documented
- [x] Downtime và compatibility table
- [ ] Reviewed bởi PM + Tech Lead + BA

### III. Traceability Matrix + Bảng Thống Kê
- [x] 26 dòng: 8 User Story + 10 BR + 3 NĐ98 + 2 WHO HTM + 1 ISO + 2 Security
- [x] Mọi dòng ✅ có ≥ 4 cell điền
- [x] Reverse lookup table (11 dòng)
- [x] Coverage gaps liệt kê (5 gaps, đều là roadmap — không có Must còn ⬜)
- [x] Bảng thống kê 18 hạng mục
- [ ] Reviewed bởi PM + Tech Lead + QA Lead
