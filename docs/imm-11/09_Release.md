# IMM-11 — Phát hành (User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | **IMM-11 — Hiệu chuẩn (Calibration)** |
| Phiên bản | 1.1.0 |
| Ngày cập nhật | 2026-05-14 |
| Owner | PM + BA + Tech Writer |
| Trạng thái | ✅ Live — User Guide đối ứng đúng UI hiện tại; screenshot UI sẽ bổ sung sau UAT |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) · [Functional Specs](./IMM-11_Functional_Specs.md) |

---

# Phần I — Hướng Dẫn Sử Dụng

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.
>
> ⚠️ **Lưu ý**: Hướng dẫn này mô tả trải nghiệm **sau khi** IMM-11 được implement và deploy. Hiện tại module chưa có giao diện — nội dung dưới đây là spec cho tài liệu User Guide chính thức.

## I.1. Giới Thiệu

Module **Hiệu chuẩn (IMM-11)** giúp đội ngũ kỹ thuật y tế quản lý toàn bộ chu trình hiệu chuẩn thiết bị đo lường: từ lập lịch tự động, gửi thiết bị đến phòng thí nghiệm được công nhận, nhập kết quả đo, đến lưu trữ chứng chỉ và xử lý kết quả không đạt.

Mọi hoạt động hiệu chuẩn đều được ghi lại thành **phiếu hiệu chuẩn**. Khi kết quả không đạt, hệ thống tự động ngừng sử dụng thiết bị và mở phiếu CAPA để đảm bảo an toàn bệnh nhân.

**Trước khi bắt đầu, bạn cần:**
- Tài khoản hệ thống AssetCore (liên hệ IT nếu chưa có)
- Trình duyệt Chrome hoặc Edge phiên bản mới nhất
- Kết nối mạng nội bộ bệnh viện

**Đăng nhập:**
1. Mở trình duyệt, truy cập: `https://assetcore.vn`
2. Nhập tên đăng nhập và mật khẩu do IT cấp
3. Bấm **Đăng nhập** — hệ thống chuyển về màn hình chính

## I.2. Các Vai Trò

| Vai trò | Bạn làm gì trong module này? |
|---|---|
| **Trưởng xưởng kỹ thuật** | Xem lịch hiệu chuẩn, chọn phòng thí nghiệm, phân công kỹ thuật viên, theo dõi trạng thái |
| **Kỹ thuật viên BME** | Gửi thiết bị đến lab, upload chứng chỉ, nhập tham số đo, xác nhận kết quả |
| **Nhân viên QA** | Xem xét phiếu CAPA khi kết quả không đạt, đánh giá hồi cứu (Lookback), đóng CAPA |
| **Phó Trưởng phòng Vật tư** | Xem báo cáo tuân thủ, tỷ lệ không đạt, Dashboard KPI |

## I.3. Quy Trình Chính

```
① Hệ thống tự lên lịch hiệu chuẩn (từ khi lắp đặt)
      │
      ▼
② Thông báo đến hạn (30 ngày trước)
   (Trưởng xưởng nhận thông báo)
      │
      ▼
③ Tạo phiếu hiệu chuẩn
   (Trưởng xưởng / Kỹ thuật viên)
      │
      ├──► External (Gửi phòng thí nghiệm) ──► ④ Bàn giao thiết bị
      │                                              │
      └──► In-House (Nội bộ) ─────────────────►────┤
                                                    │
                                                    ▼
                                              ⑤ Nhập tham số đo
                                              (Kỹ thuật viên)
                                                    │
                                              ⑥ Upload chứng chỉ (External)
                                                    │
                                              ⑦ Submit kết quả
                                                    │
                              ┌─────────────────────┴──────────────────────┐
                              ▼                                             ▼
                        ✅ Đạt                                        ❌ Không đạt
                   Cập nhật lịch tiếp theo                    Thiết bị → Ngừng dùng
                                                              CAPA tự động mở
                                                              Đánh giá hồi cứu
```

## I.4. Thao Tác Theo Vai Trò

### a. Kỹ thuật viên — Ghi nhận hiệu chuẩn External (gửi lab)

**Khi nào làm?** Khi hệ thống thông báo thiết bị đến hạn hiệu chuẩn và cần gửi đến phòng thí nghiệm ngoài.

**Các bước:**
1. Vào menu **Hiệu chuẩn** → danh sách phiếu của bạn
2. Mở phiếu ở trạng thái *Đã lên lịch*
3. Kiểm tra thông tin thiết bị và phòng thí nghiệm được chọn
4. Bấm **"Gửi đến Lab"** → điền ngày gửi, người bàn giao → Xác nhận
5. Khi nhận về: bấm **"Nhận chứng chỉ"** → upload file PDF chứng chỉ → điền ngày cấp và số chứng chỉ
6. Nhập tham số đo (bảng Kết quả đo): điền giá trị đo thực tế cho từng tham số
7. Kiểm tra màu indicator: ✅ xanh = Đạt, ❌ đỏ = Không đạt
8. Bấm **"Submit kết quả"** — hệ thống tự tính Pass/Fail tổng thể

> ⚠️ **Lưu ý:** Phiếu External bắt buộc phải có chứng chỉ PDF và Số công nhận phòng thí nghiệm (ISO/IEC 17025) mới Submit được.

---

### b. Kỹ thuật viên — Ghi nhận hiệu chuẩn In-House (nội bộ)

**Khi nào làm?** Khi thiết bị được hiệu chuẩn bởi kỹ thuật viên nội bộ với thiết bị chuẩn có traceability.

**Các bước:**
1. Mở phiếu hiệu chuẩn, chọn loại **"Nội bộ"**
2. Điền serial thiết bị chuẩn và tham chiếu traceability (bắt buộc)
3. Nhập tham số đo → Submit
4. Không cần upload chứng chỉ PDF

---

### c. Kỹ thuật viên — Xử lý kết quả Không Đạt

**Khi nào làm?** Một hoặc nhiều tham số đo vượt dung sai — hệ thống hiển thị badge ❌ KHÔNG ĐẠT.

**Sau khi Submit kết quả Không Đạt:**
- Thiết bị tự động chuyển trạng thái **Ngừng sử dụng** — không ai được dùng
- Phiếu CAPA tự động mở → chuyển cho Nhân viên QA xử lý
- Thông báo gửi đến QA Officer và Phó Trưởng phòng

> ⚠️ **Quan trọng:** Không tự ý đưa thiết bị trở lại hoạt động. Chỉ có thể dùng lại sau khi CAPA được đóng VÀ hiệu chuẩn lại đạt.

---

### d. Nhân viên QA — Xử lý CAPA và Lookback

**Khi nào làm?** Sau khi nhận thông báo thiết bị hiệu chuẩn không đạt.

**Các bước:**
1. Vào **Quản lý CAPA** → mở phiếu CAPA liên kết với phiếu hiệu chuẩn
2. Xem danh sách **Thiết bị cùng model cần đánh giá** (Lookback) — hệ thống liệt kê tự động
3. Đánh giá từng thiết bị trong danh sách, điền kết quả: **"Đã xác nhận"** hoặc **"Cần hành động"**
4. Điền **Phân tích nguyên nhân gốc rễ**, **Hành động khắc phục**, **Hành động phòng ngừa**
5. Bấm **"Đóng CAPA"**

> 💡 CAPA không thể đóng nếu Lookback còn ở trạng thái "Đang chờ". Hãy hoàn thành đánh giá hồi cứu trước.

**Sau khi CAPA đóng:**
- Kỹ thuật viên tạo phiếu **Hiệu chuẩn lại** cho thiết bị
- Nếu hiệu chuẩn lại Đạt → thiết bị tự động về **Đang hoạt động**
- Phiếu Lifecycle Event `calibration_conditionally_passed` được ghi

---

### e. Amend (Chỉnh sửa) phiếu đã Submit

**Khi nào làm?** Phát hiện sai sót sau khi phiếu đã Submit (ví dụ: số chứng chỉ nhập sai).

**Lưu ý quan trọng:**
- Phiếu đã Submit **không thể xóa hoặc hủy**
- Chỉ có thể **Amend** (tạo phiếu đính chính) với lý do bắt buộc
- Phiếu cũ vẫn được lưu — đảm bảo audit trail đầy đủ

**Các bước:**
1. Mở phiếu đã Submit → bấm nút **"Đính chính"**
2. Điền **Lý do đính chính** (bắt buộc)
3. Chỉnh sửa thông tin cần sửa → Submit phiếu mới

## I.5. Bảng Điều Khiển (Dashboard)

Vào **Hiệu chuẩn → Dashboard** để xem tổng quan:

| KPI | Ý nghĩa | Trend tốt |
|---|---|---|
| **Tỷ lệ tuân thủ lịch** | % thiết bị được hiệu chuẩn đúng hạn | ↑ Tăng (mục tiêu ≥ 95%) |
| **Tỷ lệ không đạt (OOT)** | % kết quả hiệu chuẩn vượt dung sai | ↓ Giảm (mục tiêu < 5%) |
| **CAPA chưa đóng** | Số phiếu CAPA đang mở | ↓ Giảm |
| **Thiết bị đến hạn (30 ngày)** | Số thiết bị cần hiệu chuẩn trong 30 ngày | Cần lên kế hoạch sớm |
| **Thời gian trung bình nhận chứng chỉ** | Avg ngày từ gửi lab đến nhận cert | ↓ Giảm (mục tiêu ≤ 14 ngày) |

## I.6. Câu Hỏi Thường Gặp

**Q: Thiết bị vừa hiệu chuẩn Không Đạt, có thể tiếp tục dùng tạm không?**
> A: Không. Hệ thống tự động chuyển thiết bị sang trạng thái "Ngừng sử dụng" ngay khi Submit kết quả Không Đạt. Việc dùng thiết bị không đạt hiệu chuẩn vi phạm NĐ 98/2021. Cần mở CAPA và hiệu chuẩn lại trước khi đưa vào dùng.

**Q: Phòng thí nghiệm đối tác không có ISO/IEC 17025 có được không?**
> A: Không. Hệ thống bắt buộc chọn phòng thí nghiệm có chứng nhận ISO/IEC 17025 theo NĐ 98/2021 Điều 39. Liên hệ Trưởng xưởng để cập nhật danh sách lab hợp lệ.

**Q: Tại sao ngày hiệu chuẩn tiếp theo không bằng ngày đến hạn + chu kỳ?**
> A: Ngày hiệu chuẩn tiếp theo được tính từ **ngày cấp chứng chỉ** (không phải ngày đến hạn). Ví dụ: chứng chỉ ngày 24/04/2026, chu kỳ 365 ngày → tiếp theo là 24/04/2027.

**Q: Tôi muốn sửa một tham số đo sau khi đã Submit, làm thế nào?**
> A: Dùng chức năng **Đính chính (Amend)** — điền lý do bắt buộc. Phiếu gốc được giữ nguyên; phiếu đính chính tạo mới với link về phiếu gốc.

**Q: Lookback Assessment là gì? Tôi có phải tự làm không?**
> A: Lookback là đánh giá tất cả thiết bị cùng chủng loại khi 1 thiết bị hiệu chuẩn Không Đạt. Hệ thống tự liệt kê danh sách — QA Officer chỉ cần đánh giá từng thiết bị và ghi kết quả.

**Q: Dashboard hiển thị Compliance Rate = 0%?**
> A: Compliance Rate chỉ tính cho thiết bị có lịch hiệu chuẩn đã đến hạn trong kỳ. Nếu kỳ vừa bắt đầu và chưa có lịch nào đến hạn, = 0% là đúng.

**Q: Nhận được cảnh báo "Thiết bị overdue hiệu chuẩn" nhưng thiết bị vẫn đang hoạt động?**
> A: Hệ thống chỉ cảnh báo — không tự ngừng thiết bị overdue (chỉ ngừng khi Fail). Cần lên kế hoạch hiệu chuẩn ngay. Thiết bị overdue ≥ 30 ngày sẽ leo thang đến Trưởng phòng.

## I.7. Phím Tắt & Mã Trạng Thái

| Phím | Chức năng |
|---|---|
| `⌘K` / `Ctrl+K` | Tìm kiếm nhanh toàn hệ thống |
| `Esc` | Đóng popup / hủy thao tác |
| `Tab` | Chuyển sang trường kế tiếp |
| `Ctrl+S` | Lưu bản nháp |

**Cheat sheet trạng thái phiếu:**

| Trạng thái | Ý nghĩa |
|---|---|
| Đã lên lịch | Phiếu tạo, chờ thực hiện |
| Đã gửi Lab | Thiết bị đang tại phòng thí nghiệm ngoài |
| Đang thực hiện | KTV nội bộ đang đo |
| Đã nhận chứng chỉ | Cert về, chờ nhập số liệu |
| Đạt | Tất cả tham số trong dung sai |
| Không đạt | ≥1 tham số ngoài dung sai → Thiết bị OOS |
| Đạt có điều kiện | CAPA đã đóng + hiệu chuẩn lại đạt |
| Đã hủy | Hủy trước khi Submit |

## I.8. Liên Hệ Hỗ Trợ

| Vấn đề | Liên hệ |
|---|---|
| Không đăng nhập được, quên mật khẩu | IT Helpdesk: ext. 1234 hoặc it@hospital.vn |
| Lỗi hiển thị, tính năng không hoạt động | Support AssetCore: support@assetcore.vn |
| Câu hỏi quy trình, phòng thí nghiệm hợp lệ | Trưởng xưởng kỹ thuật VTTBYT |
| Thiết bị Không Đạt khẩn cấp | QA Officer + Trưởng xưởng: trực tiếp |

## I.9. Lịch Sử Cập Nhật Tài Liệu

| Phiên bản | Ngày | Thay đổi | Owner |
|---|---|---|---|
| 0.1.0-draft | 2026-05-08 | Draft spec — ahead-of-code | BA Lead |
| 1.0.0 | (TBD khi implement) | Phát hành chính thức — Module IMM-11 GA | BA Lead |

---

# Phần II — Release Notes

## II.1. Tóm Tắt

⚠️ **DRAFT** — Release Notes chính thức sẽ được viết khi module implement xong và UAT pass.

Phiên bản 1.1.0 (TBD) sẽ đưa module **Hiệu chuẩn (IMM-11)** vào vận hành. Module quản lý toàn bộ chu trình hiệu chuẩn thiết bị đo lường y tế: lập lịch tự động, theo dõi ngoài/nội bộ, xử lý kết quả không đạt với CAPA bắt buộc và đánh giá hồi cứu (Lookback) theo ISO 13485:2016 và NĐ 98/2021.

## II.2. Tính Năng Mới (khi implement)

### Lịch hiệu chuẩn tự động (Trưởng xưởng)

Hệ thống tự lên lịch hiệu chuẩn từ khi thiết bị được lắp đặt (IMM-04) và tự tạo phiếu công việc 30 ngày trước hạn.

- Lịch tạo tự động từ `Device Model.calibration_interval_days`
- Thông báo email 90/60/30/0 ngày trước hạn
- Scheduler daily 06:00 tạo WO cho lịch đến hạn

[→ Hướng dẫn: §I.5.a]

### Theo dõi External + certificate management (Kỹ thuật viên)

Upload chứng chỉ PDF trực tiếp vào phiếu; validate phòng thí nghiệm ISO/IEC 17025 tự động.

- Validate accreditation number bắt buộc (BR-11-01)
- Upload chứng chỉ PDF gắn vào phiếu
- next_calibration_date tính từ certificate_date (không phải due_date)

[→ Hướng dẫn: §I.4.a]

### Fail → Auto CAPA + Asset OOS + Lookback (QA Officer)

Khi kết quả không đạt, hệ thống tự động ngừng thiết bị và mở CAPA với danh sách thiết bị cùng model cần đánh giá.

- Auto `transition_asset_status(→ Out of Service)` (BR-11-02)
- CAPA tự động tạo với `lookback_required = True`
- Lookback list các asset cùng `device_model` (BR-11-03)

[→ Hướng dẫn: §I.4.d]

### Compliance Dashboard + KPI Report (Phó Trưởng phòng)

Dashboard thời gian thực với tỷ lệ tuân thủ lịch, OOT Rate, CAPA closure rate.

[→ Hướng dẫn: §I.5]

## II.3. Cải Tiến

| Mô tả | Module | Tác động |
|---|---|---|
| Asset `next_calibration_date` tự động cập nhật sau mỗi hiệu chuẩn | IMM-00 Integration | Dashboard asset luôn hiển thị đúng |
| IMM-04 Commissioning → auto tạo Calibration Schedule | IMM-04 Integration | Không bỏ sót thiết bị mới lắp đặt |
| IMM-09 Repair Complete → auto trigger recalibration WO | IMM-09 Integration | Đảm bảo thiết bị đo lường được tái hiệu chuẩn sau sửa chữa |

## II.4. Thay Đổi Không Backward-compat

`AC Asset` thêm 3 custom fields: `calibration_status`, `next_calibration_date`, `last_calibration_date`. Các integration hiện có đọc `AC Asset` không bị ảnh hưởng (fields mới, nullable).

nginx body size tăng lên 100 MB — cần cập nhật config trên tất cả environments.

## II.5. Yêu Cầu Nâng Cấp

**Migration tự động:** Patches `v3_1.*` chạy tự động khi `bench migrate`. Xem chi tiết §I.3 trong `08_Deployment.md`. ⚠️ Pending

**Training bắt buộc:** 4 role phải hoàn tất training trước khi sử dụng. Xem `08_Deployment.md §II.7`. ⚠️ Pending

## II.6. Known Issues (DRAFT)

⚠️ Sẽ cập nhật sau UAT.

| Vấn đề | Workaround | Fix dự kiến |
|---|---|---|
| (chưa có — module chưa implement) | — | — |

## II.7. Downtime / Compatibility

**Downtime dự kiến:** 60 phút trong maintenance window 23:00-02:00 ngày deploy (ước tính — migration nhiều DocType hơn IMM-09).

**Khả năng tương thích:**

| Môi trường | Hỗ trợ |
|---|---|
| Chrome ≥ 120 | ✅ |
| Edge ≥ 120 | ✅ |
| Firefox ≥ 121 | ✅ |
| Safari ≥ 17 | ✅ |
| Mobile (responsive) | ✅ (giới hạn — tablet khuyến nghị cho nhập measurement) |

## II.8. Liên Kết & Lịch Sử Versioning

| Version | Ngày | Nội dung |
|---|---|---|
| 0.1.0-draft | 2026-05-08 | Draft spec — ahead-of-code |
| 1.1.0 | TBD | IMM-11 General Availability |

---

# Phần III — Traceability Matrix

## III.1. Cách Dùng

- Mỗi User Story / Business Rule / Compliance requirement có 1 dòng.
- ⚠️ Cột `Design/Code`, `Test ID`, `UAT ID`, `PR`, `Released-in` sẽ điền khi implement.
- Status: ⬜ Not started · 🟡 In progress · 🟠 Blocked · ✅ Done · ❌ Cancelled

## III.2. Matrix Chính

| Req ID | Loại | Mô tả ngắn | Doc ref | Design / Code | Test ID | UAT ID | PR | Released in | Status |
|---|---|---|---|---|---|---|---|---|---|
| US-11-01 | Story | Xem thiết bị đến hạn 30 ngày | Func Specs §3 | `api/imm11.py: get_due_calibrations()` ⚠️ | `test_get_due_calibrations` ⚠️ | UAT-IMM11-01 | — | — | ⬜ |
| US-11-02 | Story | Nhập tham số đo, auto Pass/Fail | Func Specs §3 | `services/imm11.py: compute_measurement_results()` ⚠️ | `TestMeasurementCompute` ⚠️ | UAT-IMM11-03 | — | — | ⬜ |
| US-11-03 | Story | Upload certificate PDF | Func Specs §3 | DocType `IMM Asset Calibration.certificate_file` ⚠️ | `test_create_external` ⚠️ | UAT-IMM11-02 | — | — | ⬜ |
| US-11-04 | Story | Auto CAPA + OOS khi Fail | Func Specs §3 | `services/imm11.py: handle_calibration_fail()` ⚠️ | `TestCalibrationFail` ⚠️ | UAT-IMM11-04 | — | — | ⬜ |
| US-11-05 | Story | Compliance Rate + OOT Rate report | Func Specs §3 | `api/imm11.py: get_calibration_compliance_report()` ⚠️ | `test_get_compliance_report` ⚠️ | UAT-IMM11-09 | — | — | ⬜ |
| US-11-06 | Story | Lookback cùng device_model khi Fail | Func Specs §3 | `services/imm11.py: perform_lookback_assessment()` ⚠️ | `TestLookback` ⚠️ | UAT-IMM11-04 | — | — | ⬜ |
| US-11-07 | Story | Lịch sử calibration 1 thiết bị | Func Specs §3 | `api/imm11.py: get_asset_calibration_history()` ⚠️ | `test_asset_history` ⚠️ | (TC-11-14) | — | — | ⬜ |
| US-11-08 | Story | Block tạo CAL khi asset OOS (trừ recal) | Func Specs §3 | `services/imm11.py: validate_asset_for_operations()` ⚠️ | `TestAssetGate` ⚠️ | (TC-11 EC) | — | — | ⬜ |
| US-11-09 | Story | Email alert overdue > 30 ngày | Func Specs §3 | `services/imm11.py: check_calibration_expiry()` ⚠️ | `TestExpiryCheck` ⚠️ | UAT-IMM11-08 | — | — | ⬜ |
| BR-11-01 | Rule | External: lab ISO 17025 + cert + accreditation# | Module Overview §7 | `validate_lab_iso_17025()` + `validate_external_certificate()` ⚠️ | `TestLabValidation`, `TestCertificateValidation` ⚠️ | UAT-IMM11-02 (step 2) | — | — | ⬜ |
| BR-11-02 | Rule | Fail → OOS + CAPA bắt buộc | Module Overview §7 | `handle_calibration_fail()` ⚠️ | `TestCalibrationFail: test_fail_sets_asset_oos` ⚠️ | UAT-IMM11-04 (step 4, 5) | — | — | ⬜ |
| BR-11-03 | Rule | Lookback bắt buộc cùng device_model | Module Overview §7 | `perform_lookback_assessment()` ⚠️ | `TestLookback: test_lookback_same_model` ⚠️ | UAT-IMM11-04 (step 5) | — | — | ⬜ |
| BR-11-04 | Rule | next_cal = certificate_date + interval | Module Overview §7 | `handle_calibration_pass()` ⚠️ | `TestNextCalDate` ⚠️ | UAT-IMM11-03 (step 4) | — | — | ⬜ |
| BR-11-05 | Rule | Immutable sau Submit; Amend với reason | Module Overview §7 | `on_cancel` block + `validate_amendment_reason()` ⚠️ | `TestCertificateValidation: test_cancel_blocked` ⚠️ | UAT-IMM11-07 | — | — | ⬜ |
| BR-11-06 | Rule | Decommissioned → suspend Schedule | Module Overview §7 | `transition_asset_status()` cascade (IMM-00) ⚠️ | `TestScheduleCreate: test_suspend_on_decommission` ⚠️ | (TC-11 edge) | — | — | ⬜ |
| BR-11-07 | Rule | `validate_asset_for_operations()` gate | Module Overview §7 | Gate trong `create_calibration()` ⚠️ | `TestAssetGate` ⚠️ | UAT-IMM11 edge cases | — | — | ⬜ |
| NĐ98/Điều 38 | Compliance | Hiệu chuẩn định kỳ bắt buộc | 08 §II.2 | `IMM Calibration Schedule` + scheduler ⚠️ | `TestDueWOs` ⚠️ | UAT-IMM11-08 | — | — | ⬜ |
| NĐ98/Điều 39 K.1 | Compliance | Lab ISO/IEC 17025 | 08 §II.2 | BR-11-01 enforce ⚠️ | `TestLabValidation` ⚠️ | UAT-IMM11-02 | — | — | ⬜ |
| NĐ98/Điều 40 K.1 | Compliance | OOT → ngừng thiết bị | 08 §II.2 | BR-11-02 enforce ⚠️ | `TestCalibrationFail` ⚠️ | UAT-IMM11-04 | — | — | ⬜ |
| WHO HTM §5.4.5 | Compliance | Fail → CAPA bắt buộc | 08 §II.2 | BR-11-02 → `create_capa()` (IMM-00) ⚠️ | `test_fail_creates_capa` ⚠️ | UAT-IMM11-04 | — | — | ⬜ |
| WHO HTM §5.4.6 | Compliance | Lookback assessment | 08 §II.2 | BR-11-03 ⚠️ | `TestLookback` ⚠️ | UAT-IMM11-04 | — | — | ⬜ |
| ISO 13485 §7.6 | Compliance | Kiểm soát thiết bị đo lường | 08 §II.2 | `IMM Calibration Schedule` + full lifecycle ⚠️ | Integration tests ⚠️ | UAT-IMM11-01 → 09 | — | — | ⬜ |
| ISO 13485 §4.2.5 | Compliance | Immutable records | 08 §II.2 | BR-11-05: submittable + block cancel ⚠️ | `test_immutable_after_submit` ⚠️ | UAT-IMM11-07 | — | — | ⬜ |
| SEC-IMM11-01 | Security | Technician chỉ thấy CAL của mình | 07 §III.1 | `permissions.py: cal_permission_query()` ⚠️ | `test_permission_technician_scope` ⚠️ | (UAT permission scenario) | — | — | ⬜ |
| SEC-IMM11-02 | Security | Audit chain không thể tamper | 07 §III.3 | `IMM Audit Trail` DocPerm no-delete (IMM-00) | `test_audit_chain_breaks_on_tamper` ⚠️ | UAT-IMM11-10 | — | — | ⬜ |

## III.3. Reverse Lookup

⚠️ Điền sau khi test cases được implement.

| Test ID | Requirement(s) cover |
|---|---|
| `TestCalibrationFail: test_fail_sets_asset_oos` | US-11-04, BR-11-02, NĐ98/Điều 40 K.1 |
| `TestCalibrationFail: test_fail_creates_capa` | US-11-04, BR-11-02, WHO HTM §5.4.5 |
| `TestLookback: test_lookback_same_model` | US-11-06, BR-11-03, WHO HTM §5.4.6 |
| `TestNextCalDate` | BR-11-04 |
| `TestLabValidation: test_lab_not_certified` | BR-11-01, NĐ98/Điều 39 K.1 |
| `test_immutable_after_submit` | BR-11-05, ISO 13485 §4.2.5 |
| `TestDueWOs: test_idempotent` | FR-11-22, NĐ98/Điều 38 |
| `test_audit_chain_breaks_on_tamper` | SEC-IMM11-02 |

## III.4. Coverage Gaps

⚠️ Toàn bộ module là gap — pending implementation.

| Req ID | Thiếu gì? | Owner | Deadline |
|---|---|---|---|
| US-11-01 → 09 | Tất cả code + tests chưa tạo | Dev IMM-11 | Sprint 11.1 → 11.6 |
| BR-11-01 → 07 | Service layer chưa implement | Dev IMM-11 | Sprint 11.2 |
| Permission fixtures | DocPerm + permission_query chưa tạo | Dev IMM-11 | Sprint 11.4 |
| Frontend views | UI chưa implement | FE IMM-11 | Sprint 11.5 |
| Pentest report | Pending pre-go-live | Security | Trước go-live |
| 2FA | Roadmap Phase 2 | Tech Lead | v2.0 |

## III.5. Bảng Thống Kê Thông Tin Ứng Dụng

⚠️ Số liệu dưới đây là ước tính từ Functional Specs — sẽ cập nhật sau khi implement.

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| DocType (chính) | 2 | `IMM Calibration Schedule`, `IMM Asset Calibration` ⚠️ |
| DocType (child) | 1 | `IMM Calibration Measurement` ⚠️ |
| DocType (reuse IMM-00) | 4 | `IMM CAPA Record`, `Asset Lifecycle Event`, `IMM Audit Trail`, `AC Asset` |
| Workflow JSON | 1 | `IMM-11 Calibration Workflow` — 8 states ⚠️ |
| API endpoint | ~10 | `list, get, create, send_to_lab, receive_cert, submit_results, due_calibrations, history, compliance_report, get_calibration_kpis` ⚠️ |
| FE view / page | ~6 | CalibrationDashboard, CalibrationList, CalibrationDetail, CalibrationCreate, CAPAPanel, ComplianceReport ⚠️ |
| Service function | 8 | `create_calibration_schedule_from_commissioning`, `create_due_calibration_wos`, `check_calibration_expiry`, `handle_calibration_pass`, `handle_calibration_fail`, `perform_lookback_assessment`, `create_post_repair_calibration`, `compute_measurement_results` ⚠️ |
| Scheduler job | 2 | Daily `create_due_calibration_wos`, Daily `check_calibration_expiry` (+ reuse IMM-00 `check_capa_overdue`) ⚠️ |
| Business Rule | 7 | BR-11-01 → BR-11-07 |
| Role áp dụng | 8 | Workshop Lead, Technician, QA Officer, Ops Manager, Dept Head, Storekeeper, Document Officer, System Admin |
| Test case unit | ~35 ⚠️ | 12 test class × ~3 case avg (ước tính) |
| UAT scenario | 10 | UAT-IMM11-01 → 10 |
| User Story | 9 | US-11-01 → 09 |
| Compliance standard | 5 | NĐ98, WHO HTM, ISO 13485, ISO/IEC 17025, NĐ 86/2016 |
| Sprint cần implement | 6 | Sprint 11.1 → 11.6 |

---

## DoD — Hoàn chỉnh

### I. User Guide
- [x] Tiếng Việt 100%, không jargon
- [x] Mô tả tất cả 4 role với hướng dẫn step-by-step
- [x] Dashboard KPI có giải thích trend
- [x] FAQ 7 câu thực tế
- [x] Cheat sheet trạng thái + phím tắt
- [ ] ≥ 5 screenshot UI thực tế ⚠️ Pending (chụp trên staging khi implement)
- [ ] Reviewed bởi BA + đại diện end-user (Workshop Manager) ⚠️ Pending

### II. Release Notes
- [x] Tóm tắt 2-3 câu user-friendly
- [x] 4 tính năng mới có role hưởng lợi
- [x] Known issues placeholder
- [x] Breaking change: nginx 100 MB documented
- [x] Downtime và compatibility table
- [ ] Reviewed bởi PM + Tech Lead + BA ⚠️ Pending khi implement

### III. Traceability Matrix + Bảng Thống Kê
- [x] 25 dòng: 9 User Story + 7 BR + 6 Compliance + 2 Security + 1 FR
- [x] Mọi dòng có Doc ref + ước tính Code + Test ID + UAT ID
- [x] Reverse lookup table (specified)
- [x] Coverage gaps liệt kê (toàn bộ pending — expected cho DRAFT module)
- [x] Bảng thống kê 14 hạng mục
- [ ] Reviewed bởi PM + Tech Lead + QA Lead ⚠️ Pending
