# IMM-12 — Phát hành (User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | **IMM-12 — Sự cố & CAPA (Incident & Corrective Action)** |
| Phiên bản | 1.2.0 |
| Ngày cập nhật | 2026-05-14 |
| Owner | PM + BA + Tech Writer |
| Trạng thái | ✅ Live — Incident + RCA + CAPA flow đã deploy. User Guide tham chiếu UI thực tế; screenshot bổ sung sau UAT. |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) · [Functional Specs](./IMM-12_Functional_Specs.md) |

---

# Phần I — Hướng Dẫn Sử Dụng

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.
>
> ⚠️ **Lưu ý**: Hướng dẫn này mô tả trải nghiệm **sau khi** IMM-12 extensions được implement và deploy. `Incident Report` cơ bản đã có — nội dung dưới đây bổ sung tính năng phân loại, RCA, CAPA và phát hiện lỗi mãn tính.

## I.1. Giới Thiệu

Module **Sự cố & CAPA (IMM-12)** giúp bệnh viện quản lý toàn bộ vòng đời sự cố thiết bị y tế: từ báo cáo ban đầu của khoa phòng, phân tích nguyên nhân gốc rễ (RCA), đến hành động khắc phục và phòng ngừa (CAPA).

Mọi sự cố đều được ghi lại với đầy đủ thông tin, tự động phân loại mức độ nghiêm trọng, và được xử lý theo quy trình chuẩn ISO 13485:2016 và NĐ 98/2021.

**Thiết bị Critical bị hỏng sẽ tự động được đánh dấu ngừng sử dụng** — bảo đảm an toàn bệnh nhân mà không cần chờ xử lý thủ công.

**Trước khi bắt đầu:**
- Tài khoản AssetCore do IT cấp
- Trình duyệt Chrome hoặc Edge (phiên bản mới nhất)
- Điện thoại hoặc máy tính bảng (Reporting User có thể báo cáo từ mobile)

## I.2. Các Vai Trò

| Vai trò | Bạn làm gì trong module này? |
|---|---|
| **Điều dưỡng / Kỹ thuật viên khoa phòng** | Báo cáo sự cố thiết bị; mô tả triệu chứng và tác động đến bệnh nhân |
| **Trưởng xưởng kỹ thuật** | Tiếp nhận sự cố, phân loại mức độ, phân công xử lý, tạo phân tích RCA |
| **Kỹ thuật viên BME** | Thực hiện sửa chữa; báo cáo kết quả xử lý |
| **Nhân viên QA** | Đóng CAPA sau khi có đủ bằng chứng khắc phục; xác nhận Lookback (nếu có) |
| **Phó Trưởng phòng Vật tư** | Xem Dashboard, theo dõi tỷ lệ sự cố, xuất báo cáo compliance |

## I.3. Phân Loại Mức Độ Sự Cố

| Mức độ | Ý nghĩa | Hành động tự động |
|---|---|---|
| **Minor (Nhỏ)** | Thiết bị hỏng nhưng không ảnh hưởng điều trị; có thể thay thế | Không có hành động tự động |
| **Major (Trung bình)** | Thiết bị hỏng ảnh hưởng đến dịch vụ; không có nguy hiểm ngay lập tức | Tạo RCA bắt buộc sau khi giải quyết |
| **Critical (Nghiêm trọng)** | Nguy hiểm đến bệnh nhân hoặc nhân viên; thiết bị hỗ trợ sống | **Thiết bị ngừng ngay lập tức** + CAPA bắt buộc |

> ⚠️ **Quan trọng:** Khi báo cáo sự cố Critical, bạn **bắt buộc** mô tả tác động đến bệnh nhân (`Tác động lâm sàng`). Hệ thống sẽ từ chối báo cáo nếu bỏ trống.

## I.4. Thao Tác Theo Vai Trò

### a. Điều dưỡng / KTV Khoa Phòng — Báo cáo sự cố

**Khi nào làm?** Khi phát hiện thiết bị hỏng hoặc hoạt động bất thường.

**Các bước:**
1. Mở trình duyệt hoặc app AssetCore, vào **Sự cố → Báo cáo mới**
2. Chọn **Thiết bị** bị hỏng (hệ thống tự điền thông tin)
3. Chọn **Loại lỗi** từ danh sách (ví dụ: "Báo động áp suất cao — Máy thở")
4. Điền **Mô tả triệu chứng** bằng ngôn ngữ thực tế
5. Chọn **Mức độ**: Minor / Major / Critical
6. Nếu Critical: điền **Tác động lâm sàng** (bắt buộc)
7. Bấm **"Gửi báo cáo"** — xác nhận xuất hiện

> 💡 **Báo cáo từ điện thoại:** Vào `assetcore.vn` trên trình duyệt di động — form được tối ưu cho màn hình nhỏ.

**Sau khi báo cáo Critical:** Thiết bị tự động được đánh dấu *Ngừng sử dụng*. Không sử dụng thiết bị cho đến khi nhận thông báo đã xử lý xong.

---

### b. Trưởng xưởng — Tiếp nhận và phân công

**Khi nào làm?** Sau khi nhận thông báo có sự cố mới.

**Các bước:**
1. Mở **Sự cố** → tìm phiếu mới
2. Bấm **"Tiếp nhận"** → chọn Mức độ ưu tiên và Kỹ thuật viên xử lý
3. Phiếu chuyển sang *Đã tiếp nhận* — KTV nhận thông báo

**Sau khi KTV giải quyết xong:**
- Minor: Workshop Lead có thể đóng trực tiếp
- Major/Critical: Phải tạo RCA trước khi đóng

---

### c. Trưởng xưởng / KTV Senior — Phân tích nguyên nhân (RCA)

**Khi nào làm?** Sau khi sự cố Major hoặc Critical được giải quyết; hoặc khi hệ thống phát hiện **lỗi lặp lại mãn tính** (≥3 lần cùng loại lỗi trong 90 ngày).

**Các bước:**
1. Mở phiếu RCA liên kết với sự cố (hệ thống tạo tự động)
2. Điền **Phương pháp phân tích**: 5-Why (5 câu Tại sao) hoặc Fishbone
3. Điền lần lượt từ **Tại sao 1** đến **Tại sao 5**
4. Điền **Nguyên nhân gốc rễ** (kết luận từ phân tích)
5. Điền **Hành động khắc phục** (việc đã làm hoặc sẽ làm)
6. Điền **Hành động phòng ngừa** (để không xảy ra lần sau)
7. Bấm **"Hoàn thành RCA"**

> ⚠️ Không thể đóng phiếu sự cố khi RCA chưa hoàn thành (đối với Major/Critical).

---

### d. Nhân viên QA — Đóng CAPA

**Khi nào làm?** Sau khi RCA hoàn thành và có bằng chứng khắc phục.

**Các bước:**
1. Mở **CAPA** liên kết với phiếu sự cố
2. Xem xét hành động khắc phục + phòng ngừa đã điền
3. Upload **Bằng chứng** (nếu có): ảnh sửa chữa, chứng chỉ hiệu chuẩn lại, v.v.
4. Bấm **"Đóng CAPA"**

> 💡 Chỉ **QA Officer** mới có quyền đóng CAPA — đảm bảo tính độc lập trong xác minh.

---

### e. Lookback — Đánh giá thiết bị cùng loại (nếu có)

Khi 1 thiết bị hiệu chuẩn hoặc hỏng nặng liên quan đến design, hệ thống tự động đề xuất xem xét các thiết bị cùng loại. Quy trình này quản lý chủ yếu qua IMM-11 (hiệu chuẩn) và IMM-12 CAPA.

## I.5. Theo Dõi Sự Cố Mãn Tính

Hệ thống tự động phát hiện khi cùng 1 thiết bị hỏng cùng loại lỗi ≥ 3 lần trong 90 ngày:

- Phiếu RCA được tạo tự động với lý do "Lỗi mãn tính"
- Thiết bị được đánh dấu `Chronic Failure` trên hồ sơ
- Workshop Lead và QA Officer nhận thông báo
- Dashboard hiển thị số thiết bị có lỗi mãn tính

> Đây là tính năng **phòng ngừa** — giúp phát hiện vấn đề hệ thống trước khi trở thành nghiêm trọng.

## I.6. Bảng Điều Khiển (Dashboard)

Vào **Sự cố → Dashboard** để xem tổng quan:

| KPI | Ý nghĩa | Trend tốt |
|---|---|---|
| **MTTR (Thời gian giải quyết trung bình)** | Thời gian từ báo cáo đến giải quyết | ↓ Giảm |
| **RCA đúng hạn (%)** | % RCA hoàn thành trước deadline | ↑ Tăng (mục tiêu ≥ 95%) |
| **CAPA đúng hạn (%)** | % CAPA đóng trước deadline | ↑ Tăng (mục tiêu ≥ 90%) |
| **Sự cố Critical / tháng** | Số sự cố nghiêm trọng | ↓ Giảm |
| **Thiết bị lỗi mãn tính** | Số thiết bị có chronic failure flag | = 0 là mục tiêu lý tưởng |

## I.7. Câu Hỏi Thường Gặp

**Q: Tôi báo cáo nhầm mức độ (ví dụ: chọn Minor thay vì Major). Có sửa được không?**
> A: Sau khi gửi, Trưởng xưởng có thể điều chỉnh mức độ khi Tiếp nhận (Acknowledge). Liên hệ Trưởng xưởng ngay nếu đây là sự cố ảnh hưởng bệnh nhân.

**Q: Thiết bị Critical hỏng, hệ thống ngừng tự động — bệnh nhân đang dùng thiết bị đó phải làm gì?**
> A: Hệ thống đánh dấu "Ngừng sử dụng" trong phần mềm, không tắt thiết bị vật lý. Nhân viên y tế xử lý lâm sàng theo quy trình khẩn cấp của bệnh viện. Đồng thời báo cáo sự cố ngay qua AssetCore.

**Q: Tôi không thấy loại lỗi phù hợp trong danh sách?**
> A: Chọn "Khác" và mô tả chi tiết trong phần Mô tả triệu chứng. Báo Trưởng xưởng để thêm loại lỗi mới vào danh sách nếu gặp thường xuyên.

**Q: Phiếu RCA tự động tạo là gì? Tôi có phải làm không?**
> A: Với sự cố Major/Critical, sau khi giải quyết hệ thống tự tạo phiếu RCA và giao cho Workshop Lead. Workshop Lead (hoặc KTV Senior) có 7 ngày để hoàn thành phân tích. Không hoàn thành đúng hạn → leo thang lên Trưởng phòng.

**Q: CAPA đã đóng nhưng thiết bị vẫn còn "Ngừng sử dụng"?**
> A: Nếu thiết bị Out of Service do sự cố Critical, cần xử lý xong sự cố + CAPA + (nếu cần) hiệu chuẩn lại thì mới Active trở lại. Liên hệ QA Officer để xác nhận trạng thái.

**Q: Tôi là điều dưỡng — vào Dashboard không thấy gì?**
> A: Dashboard chỉ dành cho Workshop Lead, QA Officer và Operations Manager. Điều dưỡng chỉ báo cáo và theo dõi sự cố của khoa mình.

## I.8. Phím Tắt & Mã Trạng Thái

| Phím | Chức năng |
|---|---|
| `⌘K` / `Ctrl+K` | Tìm kiếm nhanh |
| `Esc` | Đóng popup |
| `Tab` | Chuyển sang trường kế tiếp |
| `Ctrl+S` | Lưu bản nháp |

**Cheat sheet trạng thái sự cố:**

| Trạng thái | Ý nghĩa |
|---|---|
| Mới (New) | Báo cáo vừa tạo, chờ tiếp nhận |
| Đã tiếp nhận (Acknowledged) | Workshop Lead đã nhận, đang xử lý |
| Đang xử lý (In Progress) | WO sửa chữa đã gắn vào |
| Cần phân tích (RCA Required) | Giải quyết xong, đang chờ RCA |
| Đã giải quyết (Resolved) | Minor — có thể Close ngay |
| Đã đóng (Closed) | Hoàn tất |
| Đã hủy (Cancelled) | False alarm — không tính SLA |

## I.9. Liên Hệ Hỗ Trợ

| Vấn đề | Liên hệ |
|---|---|
| Không đăng nhập được | IT Helpdesk: ext. 1234 |
| Lỗi hệ thống | Support AssetCore: support@assetcore.vn |
| Câu hỏi quy trình xử lý sự cố | Trưởng xưởng kỹ thuật VTTBYT |
| Khẩn cấp (Critical incident, thiết bị đang dùng hỏng) | Trưởng xưởng + Hotline kỹ thuật: 0903.xxx.xxx (24/7) |

## I.10. Lịch Sử Cập Nhật Tài Liệu

| Phiên bản | Ngày | Thay đổi | Owner |
|---|---|---|---|
| 0.1.0-draft | 2026-05-08 | Draft spec — ahead-of-code | BA Lead |
| 1.0.0 | (TBD khi implement) | Phát hành chính thức — Module IMM-12 GA | BA Lead |

---

# Phần II — Release Notes

## II.1. Tóm Tắt

⚠️ **DRAFT** — Release Notes chính thức sẽ viết khi implement xong và UAT pass.

Phiên bản 1.2.0 (TBD) sẽ nâng cấp module **Sự cố & CAPA (IMM-12)** từ báo cáo sự cố đơn thuần lên quản lý toàn bộ vòng đời: phân loại severity, RCA 5-Why bắt buộc cho Major/Critical, CAPA workflow tự động, và phát hiện lỗi mãn tính. `Incident Report` và `IMM CAPA Record` đã hoạt động từ IMM-00; bản này bổ sung các tính năng đặc thù IMM-12.

## II.2. Tính Năng Mới (khi implement)

### Phân loại mức độ sự cố + Auto OOS Critical (Reporting User + Workshop Lead)

Mỗi sự cố được phân loại Minor/Major/Critical. Critical incident tự động ngừng thiết bị ngay lập tức.

- Severity field + clinical_impact validation (BR-12-01)
- Critical → auto `transition_asset_status(→ Out of Service)` (BR-12-04)
- Clinical impact field bắt buộc cho Critical

[→ Hướng dẫn: §I.3, §I.4.a]

### RCA 5-Why bắt buộc (Workshop Lead / KTV Senior)

Major/Critical incident resolved → RCA tự động tạo với deadline 7 ngày. Không thể đóng phiếu khi RCA chưa xong.

- `RCA Record` DocType với child table `RCA Five Why Step`
- Block Close nếu RCA In Progress (BR-12-02)
- RCA Completed → CAPA auto create (BR-12-06)

[→ Hướng dẫn: §I.4.c]

### Phát hiện lỗi mãn tính tự động (System Scheduler)

Scheduler hàng ngày phát hiện asset có ≥3 incidents cùng fault_code trong 90 ngày → RCA tự động + cảnh báo.

- `detect_chronic_failures()` scheduler daily 02:00 (BR-12-03)
- `chronic_failure_flag` trên asset
- Thông báo Workshop Lead + QA Officer

[→ Hướng dẫn: §I.5]

### Incident Dashboard + CAPA tracking (Operations Manager + QA Officer)

Dashboard thời gian thực: MTTR, RCA on-time, CAPA on-time, Critical incidents/tháng.

[→ Hướng dẫn: §I.6]

## II.3. Tính Năng Đã Có (từ IMM-00, không thay đổi)

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| `Incident Report` DocType cơ bản | ✅ LIVE | Không thay đổi — IMM-12 chỉ extend |
| `IMM CAPA Record` workflow (Open → Closed) | ✅ LIVE | IMM-12 sử dụng qua `imm00.create_capa()` |
| `log_audit_event()` + hash chain | ✅ LIVE | IMM-12 gọi qua, không reimplement |
| `transition_asset_status()` | ✅ LIVE | IMM-12 gọi qua cho Critical auto-OOS |
| `check_capa_overdue` scheduler | ✅ LIVE | Tự động Overdue CAPA quá due_date |

## II.4. Thay Đổi Không Backward-compat

`Incident Report` thêm 5 custom fields (nullable). Existing IR records không bị ảnh hưởng. Tuy nhiên:
- Sau deploy, **Clinical Staff cần training** về severity classification trước khi tạo IR mới.
- Critical IR cũ (trước deploy) sẽ không có `clinical_impact` — đây là historical data, không cần migrate.

## II.5. Yêu Cầu Nâng Cấp

**Migration tự động:** Patches `v3_2.*` chạy khi `bench migrate`. ⚠️ Pending

**Training bắt buộc:** **Đặc biệt cần train Reporting User (Clinical Staff)** về severity classification và clinical_impact field trước go-live. Xem `08_Deployment.md §II.7`.

## II.6. Known Issues (DRAFT)

⚠️ Cập nhật sau UAT.

| Vấn đề | Workaround | Fix dự kiến |
|---|---|---|
| (chưa có — module chưa implement) | — | — |

## II.7. Downtime / Compatibility

**Downtime dự kiến:** 45 phút (ít migration hơn IMM-11 — chủ yếu custom fields + index).

Khả năng tương thích: giống IMM-09 (Chrome/Edge/Firefox/Safari). Mobile: **Reporting User** có thể dùng mobile để báo cáo sự cố.

## II.8. Liên Kết & Lịch Sử Versioning

| Version | Ngày | Nội dung |
|---|---|---|
| 0.1.0-draft | 2026-05-08 | Draft spec — ahead-of-code |
| 1.2.0 | TBD | IMM-12 General Availability |

---

# Phần III — Traceability Matrix

## III.1. Cách Dùng

- Status: ⬜ Not started · 🟡 In progress · 🟠 Blocked · ✅ Done · ❌ Cancelled
- ⚠️ Cột `Design/Code`, `Test ID`, `UAT ID`, `PR`, `Released-in` điền khi implement.

## III.2. Matrix Chính

| Req ID | Loại | Mô tả ngắn | Doc ref | Design / Code | Test ID | UAT ID | PR | Released in | Status |
|---|---|---|---|---|---|---|---|---|---|
| US-12-01 | Story | Reporting User báo cáo sự cố | Func Specs §3 | `services/imm12.py: report_incident()` ⚠️ | `TestReportIncident` ⚠️ | UAT-IMM12-01 | — | — | ⬜ |
| US-12-02 | Story | Workshop Lead Acknowledge + phân công | Func Specs §3 | `services/imm12.py: acknowledge_incident()` ⚠️ | `TestAcknowledge` ⚠️ | UAT-IMM12-02 | — | — | ⬜ |
| US-12-03 | Story | Resolve → Auto trigger RCA | Func Specs §3 | `services/imm12.py: trigger_rca_if_required()` ⚠️ | `TestTriggerRCA` ⚠️ | UAT-IMM12-04 | — | — | ⬜ |
| US-12-04 | Story | QA Officer Close CAPA | Func Specs §3 | `services/imm00.py: close_capa()` (LIVE) + permission check ⚠️ | `TestCAPAGate` ⚠️ | UAT-IMM12-06 | — | — | ⬜ |
| US-12-05 | Story | Scheduler chronic failure detection | Func Specs §3 | `services/imm12.py: detect_chronic_failures()` ⚠️ | `TestChronicDetect` ⚠️ | UAT-IMM12-07 | — | — | ⬜ |
| US-12-06 | Story | Block Close khi RCA chưa Completed | Func Specs §3 | VR-12-03 in `IncidentReport.validate()` ⚠️ | `TestRCAGate` ⚠️ | UAT-IMM12-04 (step 2) | — | — | ⬜ |
| BR-12-01 | Rule | Critical bắt buộc clinical_impact | Module Overview §7 | VR-12-02 in `IncidentReport.validate()` ⚠️ | `TestClinicalImpact` ⚠️ | UAT-IMM12-01 (step 2) | — | — | ⬜ |
| BR-12-02 | Rule | Major/Critical Close bắt buộc RCA Completed | Module Overview §7 | VR-12-03 + workflow gate ⚠️ | `test_close_major_blocked_rca_incomplete` ⚠️ | UAT-IMM12-04 (step 2) | — | — | ⬜ |
| BR-12-03 | Rule | ≥3 incidents same fault_code/90d → RCA + chronic flag | Module Overview §7 | `detect_chronic_failures()` scheduler ⚠️ | `TestChronicDetect: test_idempotent` ⚠️ | UAT-IMM12-07 | — | — | ⬜ |
| BR-12-04 | Rule | Critical → auto OOS | Module Overview §7 | `report_incident()` → `transition_asset_status(OOS)` ⚠️ | `TestCriticalOOS` ⚠️ | UAT-IMM12-01 (step 3) | — | — | ⬜ |
| BR-12-05 | Rule | Mọi transition → IMM Audit Trail | Module Overview §7 | `log_audit_event()` trong mọi `imm12.*` ⚠️ | `TestAuditEveryTransition` ⚠️ | UAT-IMM12-08 | — | — | ⬜ |
| BR-12-06 | Rule | RCA Submit → auto create CAPA | Module Overview §7 | `submit_rca_and_create_capa()` ⚠️ | `TestSubmitRCA` ⚠️ | UAT-IMM12-04 (step 3) | — | — | ⬜ |
| BR-12-07 | Rule | RCA root_cause + rca_method bắt buộc | Module Overview §7 | `RCARecord.before_submit()` ⚠️ | `TestSubmitRCA: test_root_cause_empty_raises` ⚠️ | UAT-IMM12-05 | — | — | ⬜ |
| BR-00-08 | Rule (IMM-00) | CAPA bắt buộc root_cause + corrective + preventive | Module Overview §7 | `IMMCAPARecord.before_submit()` ✅ LIVE | `test_capa_fields_required` ✅ | UAT-IMM12-06 | IMM-00 | IMM-00 | ✅ |
| BR-00-09 | Rule (IMM-00) | CAPA overdue → auto Overdue | Module Overview §7 | `check_capa_overdue()` ✅ LIVE | (IMM-00 tests) ✅ | — | IMM-00 | IMM-00 | ✅ |
| NĐ98/Điều 38 | Compliance | Báo cáo sự cố bắt buộc | 08 §II.2 | `Incident Report` DocType ✅ LIVE + severity extension ⚠️ | `test_report_incident_happy` ⚠️ | UAT-IMM12-01 | — | — | 🟡 |
| NĐ98/Điều 36 | Compliance | Ngừng thiết bị nguy hiểm | 08 §II.2 | BR-12-04: `transition_asset_status(OOS)` ⚠️ | `TestCriticalOOS` ⚠️ | UAT-IMM12-01 | — | — | ⬜ |
| ISO 13485 §8.5.2 | Compliance | RCA + CAPA bắt buộc cho lỗi | 08 §II.2 | BR-12-02 + BR-12-06 ⚠️ | Multiple ⚠️ | UAT-IMM12-04 | — | — | ⬜ |
| ISO 13485 §8.5.3 | Compliance | Preventive action — chronic | 08 §II.2 | BR-12-03: `detect_chronic_failures()` ⚠️ | `TestChronicDetect` ⚠️ | UAT-IMM12-07 | — | — | ⬜ |
| ISO 13485 §7.5.9 | Compliance | Traceability mọi action | 08 §II.2 | BR-12-05 + `IMM Audit Trail` (IMM-00) ✅ | `TestAuditEveryTransition` ⚠️ | UAT-IMM12-08 | — | — | 🟡 |
| ISO 13485 §4.2.5 | Compliance | Immutable records | 08 §II.2 | `IMM Audit Trail` no-delete ✅ LIVE | (IMM-00 tests) ✅ | UAT-IMM12-08 | IMM-00 | IMM-00 | ✅ |
| WHO HTM §5.3.4 | Compliance | Incident reporting system | 08 §II.2 | `Incident Report` workflow ✅ + severity extension ⚠️ | UAT-IMM12-01 | UAT-IMM12-01 | — | — | 🟡 |
| WHO HTM §5.4 | Compliance | Chronic failure detection | 08 §II.2 | BR-12-03 ⚠️ | `TestChronicDetect` ⚠️ | UAT-IMM12-07 | — | — | ⬜ |
| SEC-IMM12-01 | Security | Reporting User chỉ thấy IR khoa mình | 07 §III.1 | `permissions.py: incident_report_query()` ⚠️ | `test_reporting_user_dept_scope` ⚠️ | UAT-IMM12-10 | — | — | ⬜ |
| SEC-IMM12-02 | Security | Audit chain không thể tamper | 07 §III.3 | `IMM Audit Trail` DocPerm no-delete ✅ LIVE | `test_audit_chain_breaks_on_tamper` ⚠️ | UAT-IMM12-08 | IMM-00 | IMM-00 | 🟡 |

## III.3. Reverse Lookup

⚠️ Điền sau khi test cases implement.

| Test ID | Requirement(s) cover |
|---|---|
| `TestReportIncident: test_critical_sets_oos` | US-12-01, BR-12-04, NĐ98/Điều 36 |
| `TestClinicalImpact: test_critical_no_impact_raises` | US-12-01, BR-12-01 |
| `TestTriggerRCA: test_major_triggers_rca` | US-12-03, BR-12-02 |
| `TestRCAGate: test_close_major_blocked` | US-12-06, BR-12-02, ISO 13485 §8.5.2 |
| `TestChronicDetect: test_threshold_met` | US-12-05, BR-12-03, WHO HTM §5.4 |
| `TestChronicDetect: test_idempotent` | BR-12-03 |
| `TestSubmitRCA: test_creates_capa` | BR-12-06, ISO 13485 §8.5.2 |
| `TestAuditEveryTransition` | BR-12-05, ISO 13485 §7.5.9 |

## III.4. Coverage Gaps

| Req ID | Thiếu gì? | Owner | Deadline |
|---|---|---|---|
| US-12-01 → 06 | Code + tests chưa tạo | Dev IMM-12 | Sprint 12.1 → 12.6 |
| BR-12-01 → 07 | `services/imm12.py` chưa implement | Dev IMM-12 | Sprint 12.3 |
| `RCA Record` DocType | Chưa tạo | Dev IMM-12 | Sprint 12.2 |
| Custom fields Incident Report | Chưa add | Dev IMM-12 | Sprint 12.1 |
| Permission fixtures | DocPerm + permission_query chưa tạo | Dev IMM-12 | Sprint 12.4 |
| Frontend views | UI chưa implement | FE IMM-12 | Sprint 12.6 |
| Vigilance reporting BYT (MEDDEV) | Deferred → IMM-15 | PM | IMM-15 roadmap |
| Pentest report | Pending | Security | Trước go-live |

## III.5. Bảng Thống Kê Thông Tin Ứng Dụng

⚠️ Ước tính từ Functional Specs — cập nhật sau implement.

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| DocType đã LIVE (IMM-00) | 4 | `Incident Report`, `IMM CAPA Record`, `IMM Audit Trail`, `Asset Lifecycle Event` |
| DocType đề xuất mới (IMM-12) | 1 | `RCA Record` ⚠️ |
| DocType child mới | 2 | `RCA Five Why Step`, `RCA Related Incident` ⚠️ |
| Custom fields trên Incident Report | 5 | `severity`, `clinical_impact`, `rca_record`, `chronic_failure_flag`, `linked_capa` ⚠️ |
| Workflow JSON (extension) | 1 | Incident Report workflow extension (8 states) ⚠️ |
| API endpoint | ~11 | `list, get, report_incident, acknowledge, resolve, close, submit_rca, detect_chronic, get_kpis, cancel, get_capa` ⚠️ |
| FE view / page | ~6 | IncidentDashboard, IncidentList, IncidentDetail, IncidentCreate, RCAForm, CAPAPanel ⚠️ |
| Service function IMM-12 | 6 | `report_incident, acknowledge_incident, resolve_incident, trigger_rca_if_required, detect_chronic_failures, submit_rca_and_create_capa` ⚠️ |
| Service function từ IMM-00 | 5 | `create_capa, close_capa, log_audit_event, transition_asset_status, check_capa_overdue` ✅ LIVE |
| Scheduler job mới | 1 | `detect_chronic_failures` daily 02:00 ⚠️ |
| Business Rule (IMM-12) | 7 | BR-12-01 → BR-12-07 |
| Business Rule (IMM-00 áp dụng) | 2 | BR-00-08, BR-00-09 |
| Role áp dụng | 6 | Reporting User, Workshop Lead, Biomed Technician, QA Officer, Ops Manager, System Admin |
| Test case unit | ~35 ⚠️ | 11 test class (ước tính) |
| UAT scenario | 10 | UAT-IMM12-01 → 10 |
| User Story | 6 | US-12-01 → 06 |
| Compliance standard | 4 | NĐ98, ISO 13485, WHO HTM, MEDDEV (deferred) |
| Sprint cần implement | 7 | Sprint 12.1 → 12.7 |

---

## DoD — Hoàn chỉnh

### I. User Guide
- [x] Tiếng Việt 100%, không jargon
- [x] Mô tả tất cả 5 role với hướng dẫn step-by-step
- [x] Bảng phân loại severity với hành động tự động
- [x] Dashboard KPI có giải thích trend
- [x] FAQ 6 câu thực tế (bao gồm câu về Critical + bệnh nhân)
- [x] Cheat sheet trạng thái + phím tắt
- [ ] ≥ 5 screenshot UI thực tế ⚠️ Pending
- [ ] Reviewed bởi BA + Clinical Staff representative ⚠️ Pending

### II. Release Notes
- [x] Tóm tắt 2-3 câu
- [x] 4 tính năng mới
- [x] Tính năng đã có từ IMM-00 listed
- [x] Breaking change: custom fields + training requirement documented
- [x] Downtime + compatibility
- [ ] Reviewed bởi PM + Tech Lead ⚠️ Pending

### III. Traceability Matrix + Bảng Thống Kê
- [x] 26 dòng: 6 User Story + 9 BR (IMM-12 + IMM-00) + 8 Compliance + 2 Security + 1 LIVE
- [x] BR-00-08 và BR-00-09 có status ✅ (LIVE từ IMM-00)
- [x] ISO 13485 §4.2.5 + `IMM Audit Trail` có status ✅ (LIVE)
- [x] Reverse lookup table
- [x] Coverage gaps liệt kê (toàn bộ IMM-12 specific pending)
- [x] Bảng thống kê 14 hạng mục; phân biệt LIVE vs Pending
- [ ] Reviewed bởi PM + Tech Lead + QA Lead ⚠️ Pending
