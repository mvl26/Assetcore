# IMM-16 — Phát hành (User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | **IMM-16 — Giám sát Tuân thủ & CAPA** |
| Phiên bản | 1.0.0 |
| Ngày phát hành | Pending (Wave 3) |
| Owner | PM + BA + Tech Writer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) · [Module Overview](./IMM-16_Module_Overview.md) |
| Wave | 3 — PLANNED |

> ⚠️ Pending implementation — Wave 3. Tài liệu này là draft — nội dung chính thức sẽ finalize sau UAT pass.

---

# Phần I — Hướng Dẫn Sử Dụng

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.

## I.1 Giới Thiệu

Module **Giám sát Tuân thủ & CAPA (IMM-16)** giúp Tổ HC-QLCL và Ban lãnh đạo theo dõi mức độ tuân thủ quy trình bảo trì thiết bị y tế trên toàn cơ sở, phát hiện sai lệch sớm và thực hiện hành động khắc phục (CAPA) hiệu quả.

Hệ thống tự động phát hiện các vấn đề tuân thủ hàng tháng và tạo **Phát hiện (Finding)**. Mỗi Finding có thể dẫn đến **Hành động khắc phục (CAPA)** với chu trình đầy đủ: điều tra nguyên nhân gốc, lập kế hoạch, thực hiện, xác minh hiệu quả. Toàn bộ được tổng hợp trong **Bảng điểm Tuân thủ** hàng tháng và **Review Ban lãnh đạo** hàng quý.

**Trước khi bắt đầu, bạn cần:**
- Tài khoản hệ thống AssetCore (liên hệ IT nếu chưa có)
- Trình duyệt Chrome hoặc Edge phiên bản mới nhất
- Kết nối mạng nội bộ bệnh viện
- Màn hình tối thiểu 1280×800 (khuyến nghị 1920×1080)

**Đăng nhập:**
1. Mở trình duyệt, truy cập: `https://assetcore.vn`
2. Nhập tên đăng nhập và mật khẩu do IT cấp
3. Bấm **Đăng nhập** → vào màn hình **Giám sát Tuân thủ**

## I.2 Nhận Biết Bạn Đang Ở Đâu

Màn hình chính IMM-16 gồm các khu vực:

```
┌─────────────────────────────────────────────────────────┐
│  ① Thanh trên — Tìm kiếm, thông báo, tài khoản          │
├──────────┬──────────────────────────────────────────────┤
│          │  ③ Dashboard Tuân thủ (mặc định)             │
│ ②        │  ┌─────────────────────────────────────────┐ │
│ Sidebar  │  │  KPI cards + Heatmap + CAPA Kanban       │ │
│ (menu)   │  └─────────────────────────────────────────┘ │
│          │                                               │
│ - Dashboard│                                            │
│ - Finding │                                             │
│ - CAPA   │                                              │
│ - Audit  │                                              │
│ - Scorecard│                                            │
│ - Rules  │                                              │
└──────────┴──────────────────────────────────────────────┘
```

- **① Topbar**: Chuông thông báo sẽ rung khi CAPA của bạn sắp đến hạn.
- **② Sidebar**: Chọn **"Giám sát Tuân thủ"** hoặc **"IMM-16"** để vào module.
- **③ Dashboard**: Tổng quan compliance rate, số Finding mở, CAPA quá hạn, Heatmap.

## I.3 Các Vai Trò

| Vai trò | Bạn làm gì trong module này? |
|---|---|
| **Tổ HC-QLCL** | Quản lý Compliance Rule, xem xét Finding, xác nhận NC, tạo CAPA, publish Scorecard |
| **Kiểm toán viên nội bộ** | Thực hiện Internal Audit, hoàn thành checklist, xem Finding |
| **Trưởng xưởng kỹ thuật** | Tạo và thực hiện CAPA được assign cho xưởng |
| **Kỹ thuật viên BME** | Xem CAPA được assign; biết thiết bị đang bị block nếu có CAPA Critical |
| **Phó Trưởng phòng Vật tư (VP Block2)** | Miễn trừ Finding (Waive), đóng Audit, publish Scorecard, Finalize Management Review, xem Dashboard tổng quan |
| **Trưởng phòng** | Tạo và theo dõi CAPA cho khoa phòng |
| **CMMS Admin** | Cấu hình hệ thống, phân quyền, giám sát scheduler |

## I.4 Quy Trình Chính

```
① Hệ thống tự động phát hiện vấn đề
   (chạy đầu mỗi tháng)
         │
         ▼
② Phát hiện (Finding) được tạo tự động
   (Tổ HC-QLCL nhận thông báo)
         │
         ▼
③ Tổ HC-QLCL xem xét Finding
   │
   ├──► Xác nhận NC → ④ Tạo CAPA
   │
   ├──► Đánh dấu False Positive → Finding đóng
   │
   └──► Miễn trừ (Waive) — chỉ VP Block2
              ↓ approved
         Finding → Waived

④ CAPA Lifecycle
   Draft → Điều tra → Lập kế hoạch
        → Thực hiện → Xác minh
        → ✅ Đóng (nếu Hiệu quả)
        → 🔄 Mở lại (nếu Không Hiệu quả)
              │
              ▼
⑤ Bảng điểm Tuân thủ (tháng)
   (hệ thống tự tạo đầu tháng)
         │
         ▼
⑥ VP Block2 Publish Scorecard
   (cần có Management Review quý trước)
         │
         ▼
⑦ Management Review Quý
   (Tổ HC-QLCL chuẩn bị → VP Block2 Finalize)
```

## I.5 Thao Tác Theo Vai Trò

### a. Tổ HC-QLCL — Quản lý Compliance Rule

**Khi nào làm?** Khi cần thêm tiêu chí tuân thủ mới hoặc điều chỉnh ngưỡng hiện có.

**Các bước tạo Rule mới:**
1. Vào menu **"Quy tắc Tuân thủ"** → bấm **"Tạo Rule mới"**
2. Điền **Mã Rule** (vd: `PM-COMPLIANCE-90`), **Tên Rule**
3. Chọn **Module nguồn** (vd: IMM-08 Bảo trì định kỳ)
4. Chọn **Danh mục** và **Mức độ nghiêm trọng** (Thấp/Trung/Cao/Nghiêm trọng)
5. Cấu hình **Ngưỡng đánh giá** — ví dụ: `tỷ lệ tuân thủ PM < 90%`
6. Chọn **Tần suất đánh giá** (Hàng tháng/Hàng tuần)
7. Bấm **Lưu**

> ⚠️ **Quan trọng:** Nếu bạn sửa Rule hiện có, hệ thống yêu cầu điền **"Tóm tắt thay đổi"**. Đây là yêu cầu kiểm soát thay đổi bắt buộc — phiên bản Rule sẽ tự tăng.

---

### b. Tổ HC-QLCL — Xem xét Finding

**Finding** xuất hiện trong danh sách mỗi đầu tháng sau khi hệ thống chạy đánh giá. Mỗi Finding cho thấy khoa phòng nào, vấn đề gì, mức độ nào.

**Các bước xem xét:**
1. Vào **"Phát hiện (Findings)"** → lọc `Trạng thái = Mới`
2. Bấm vào Finding để xem chi tiết: thiết bị nào, giá trị thực tế vs ngưỡng, khoa phòng
3. Bấm một trong các nút hành động:
   - **[Xem xét]** → Finding chuyển sang *Đang xem xét*
   - **[Xác nhận NC]** → Xác nhận đây là không phù hợp thực sự → cần mở CAPA
   - **[Đánh dấu FP]** → Đây là cảnh báo sai → Finding đóng
4. Nếu xác nhận NC → bấm **[Mở CAPA]** để tạo hành động khắc phục

> 💡 **Mẹo:** Dùng Heatmap để xem tổng quan theo khoa phòng × module — ô màu đỏ cần xử lý ngay.

---

### c. VP Block2 — Miễn trừ Finding (Waive)

Chỉ VP Block2 được phép miễn trừ Finding. Dùng khi có lý do hợp lệ để tạm không xử lý Finding.

**Các bước:**
1. Mở Finding đang ở trạng thái *Đang xem xét*
2. Bấm **[Miễn trừ]**
3. Điền **Lý do miễn trừ** (tối thiểu 50 ký tự — mô tả cụ thể lý do)
4. **Tải lên bằng chứng** (tài liệu PDF hoặc hình ảnh)
5. Chọn **Ngày hết hạn miễn trừ** (phải là ngày trong tương lai)
6. Bấm **Xác nhận** → Finding chuyển sang *Đã miễn trừ*

> ⚠️ **Lưu ý:** Miễn trừ không đồng nghĩa với xóa vấn đề. Finding vẫn được ghi lại trong hệ thống và hiển thị trong Scorecard.

---

### d. Tổ HC-QLCL / Trưởng phòng / Trưởng xưởng — Quản lý CAPA

**CAPA (Corrective and Preventive Action)** là hành động khắc phục có cấu trúc 6 bước.

**Quy trình CAPA:**

```
[Bản nháp] → [Đang điều tra] → [Kế hoạch hành động]
           → [Đang thực hiện] → [Đang xác minh]
           → ✅ [Đã đóng] HOẶC 🔄 [Mở lại]
```

**Bước 1 — Tạo CAPA:**
1. Từ Finding đã xác nhận NC → bấm **[Mở CAPA]**
2. Điền **Mô tả vấn đề**, chọn **Mức độ rủi ro**, **Người phụ trách**, **Hạn hoàn thành**
3. Bấm **Tạo** → CAPA tạo ở trạng thái *Bản nháp*

**Bước 2 — Điều tra:**
1. Người phụ trách bấm **[Bắt đầu điều tra]**
2. Chọn **Phương pháp phân tích nguyên nhân** (5-Why, Fishbone, RCA...)
3. Điền phân tích chi tiết

**Bước 3 — Lập kế hoạch:**
1. Bấm **[Lập kế hoạch hành động]**
2. Thêm từng **Bước hành động** với người phụ trách + ngày dự kiến

**Bước 4 — Thực hiện:**
1. Thực hiện từng bước; đánh dấu **Hoàn thành** khi xong

**Bước 5 — Xác minh:**
1. Bấm **[Chuyển sang Xác minh]**
2. Bấm **[Kiểm tra Hiệu quả]**, chọn:
   - **Hiệu quả** + tải lên bằng chứng → CAPA **Đóng** ✅
   - **Không Hiệu quả** + tải lên bằng chứng → CAPA **Mở lại** 🔄 (quay về Điều tra)

> ⚠️ **Quan trọng:** Không thể đóng CAPA mà không có kết quả kiểm tra hiệu quả. Nếu CAPA bị mở lại quá 3 lần → hệ thống tự leo thang lên VP Block2.

---

### e. Kiểm toán viên nội bộ — Thực hiện Internal Audit

**Khi nào làm?** Khi được phân công tham gia đoàn kiểm toán nội bộ định kỳ.

**Các bước:**
1. Vào **"Kiểm toán nội bộ"** → mở audit được assign
2. Xem **Phạm vi kiểm toán** (modules, khoa phòng)
3. Đối với từng **mục checklist**:
   - Chọn kết quả: **Phù hợp / NC Nhỏ / NC Lớn / Không áp dụng**
   - Ghi chú phát hiện cụ thể
   - Nếu NC → hệ thống tự tạo Finding liên kết
4. Sau khi hoàn thành tất cả mục → báo Trưởng đoàn để đóng audit

> 💡 **Lưu ý:** NC Lớn phải được mở CAPA trước khi đóng audit — trưởng đoàn (VP Block2) sẽ kiểm tra điều này.

---

### f. VP Block2 — Xem Dashboard & Publish Scorecard

**Dashboard** cho bạn thấy tổng quan tuân thủ toàn cơ sở:
- **Compliance Rate**: tỷ lệ tuân thủ tổng hợp (%)
- **Heatmap**: ô màu sắc theo module × khoa phòng (xanh = tốt, đỏ = cần xử lý)
- **CAPA Kanban**: các CAPA đang ở từng giai đoạn
- **CAPA sắp hết hạn**: cần theo dõi

**Publish Scorecard:**
1. Vào **"Bảng điểm"** → mở Scorecard tháng hiện tại (trạng thái *Bản nháp*)
2. Xem lại `score_pct`, phân tích theo module và khoa phòng
3. Kiểm tra **xu hướng** so với tháng trước
4. Bấm **[Công bố]** → Scorecard chính thức; không thể sửa sau khi công bố

> ⚠️ **Điều kiện để Công bố:** Quý trước phải có Management Review đã đóng. Nếu chưa có → hệ thống thông báo lỗi và hướng dẫn tạo MR.

---

### g. VP Block2 — Management Review Quý

Management Review (MR) là cuộc họp quý về tuân thủ của Ban lãnh đạo.

**Các bước:**
1. Tổ HC-QLCL tạo **MR mới** với kỳ quý (vd: Q1/2026)
2. Gắn Scorecards, báo cáo Finding, CAPA summary vào MR
3. Điền kết quả thảo luận, quyết định
4. VP Block2 bấm **[Finalize]** → MR **Đóng**

> ⚠️ **Quan trọng:** Không có MR Đóng của quý trước → không thể Publish Scorecard tháng đầu quý mới.

## I.6 Câu Hỏi Thường Gặp (FAQ)

**Q: Tôi thấy Finding "Đã miễn trừ" — có nghĩa là gì?**
A: VP Block2 đã duyệt cho phép tạm bỏ qua vấn đề này với lý do cụ thể, trong thời gian giới hạn. Finding vẫn được tính trong Scorecard nhưng không yêu cầu CAPA.

**Q: CAPA của tôi bị "Mở lại" — phải làm gì?**
A: Kết quả kiểm tra hiệu quả cho thấy vấn đề chưa được giải quyết triệt để. Quay lại bước Điều tra, tìm nguyên nhân sâu hơn và đề xuất biện pháp khắc phục mới.

**Q: Tôi không thể Submit Work Order vì hệ thống báo "thiết bị bị block"?**
A: Thiết bị đang có CAPA mức "Nghiêm trọng" chưa được đóng. Liên hệ Tổ HC-QLCL để kiểm tra CAPA liên quan đến thiết bị đó. Khi CAPA được đóng thành công, Work Order sẽ được phép Submit trở lại.

**Q: Scorecard tháng này chưa thấy — phải làm gì?**
A: Scorecard được tạo tự động vào đầu mỗi tháng bởi hệ thống. Nếu đã qua ngày 3 mà chưa có → liên hệ CMMS Admin kiểm tra scheduler.

**Q: Tôi muốn sửa Scorecard đã Công bố — được không?**
A: Không thể sửa Scorecard đã Công bố (tính bất biến của hồ sơ). Nếu cần điều chỉnh, bấm **[Tạo bản điều chỉnh]** — hệ thống sẽ tạo Scorecard mới liên kết với bản gốc.

**Q: Compliance Rule tôi muốn sửa nhưng hệ thống yêu cầu "Tóm tắt thay đổi" — có thể bỏ qua không?**
A: Không. Đây là yêu cầu kiểm soát thay đổi bắt buộc. Mọi thay đổi Rule phải có lý do. Điền tóm tắt ngắn gọn (vd: "Tăng ngưỡng từ 85% lên 90% theo khuyến nghị WHO").

**Q: Sao Finding xuất hiện cho cùng 1 vấn đề mỗi tháng?**
A: Hệ thống đánh giá tuân thủ mỗi tháng. Nếu vấn đề chưa được khắc phục (CAPA chưa đóng), Finding mới sẽ được tạo cho tháng tiếp theo. Hãy ưu tiên đóng CAPA liên quan.

**Q: Tôi muốn xem lịch sử tất cả hành động trên một CAPA — ở đâu?**
A: Mở CAPA → tab **"Lịch sử hoạt động"** — toàn bộ thay đổi trạng thái, người thực hiện, và thời điểm được ghi lại đầy đủ.

---

# Phần II — Release Notes

> ⚠️ Pending implementation — Wave 3. Release Notes sẽ hoàn chỉnh sau ngày go-live.

## II.1 Version 1.0.0 — IMM-16 General Availability

**Ngày phát hành:** Pending (Wave 3)
**Phiên bản AssetCore:** 1.1.0

### Tính năng mới

| Tính năng | Mô tả | User Story |
|---|---|---|
| Compliance Rule Engine | Khai báo quy tắc tuân thủ có phiên bản, change control bắt buộc | US-16-01 |
| Auto-detect Finding | Hệ thống tự phát hiện vi phạm tuân thủ hàng tháng, idempotent | US-16-02 |
| Finding Lifecycle | Quy trình xem xét Open → Under Review → Confirmed NC / False Positive / Waived | US-16-03 |
| CAPA Extended Workflow | Chu trình CAPA 6 trạng thái với kiểm tra hiệu quả bắt buộc | US-16-04 |
| CAPA Escalation | Tự động leo thang email theo mức độ rủi ro × số ngày quá hạn | US-16-05 |
| Waive Finding | VP Block2 có thể miễn trừ Finding với bằng chứng và ngày hết hạn | US-16-06 |
| Compliance Heatmap | Bản đồ tuân thủ module × khoa phòng với drill-down | US-16-07 |
| Internal Audit | Chu trình kiểm toán nội bộ với checklist + auto-create Finding | US-16-08 |
| Compliance Scorecard | Bảng điểm tuân thủ hàng tháng tự động, immutable sau publish | US-16-09 |
| Management Review | Review quý ban lãnh đạo với gate publish Scorecard | US-16-10 |
| Cross-module Gate | BR-16-09: Block WO Submit IMM-08/09 nếu CAPA Critical chưa đóng | BR-16-09 |
| Compliance Dashboard | KPI cards: compliance rate, CAPA aging, trend, open findings count | — |

### DocType mới

| DocType | Naming | Submittable |
|---|---|---|
| IMM Compliance Rule | rule_code (autoname) | Không |
| IMM Compliance Finding | FND-.YYYY.-.##### | Không |
| IMM Internal Audit | AUD-INT-.YYYY.-.##### | Có |
| IMM Compliance Scorecard | SCR-.YYYY.-.MM.-.##### | Không |
| IMM Management Review | MR-.YYYY.-.##### | Có |

### Custom Fields bổ sung vào IMM CAPA Record

| Field | Label | Type |
|---|---|---|
| `workflow_state_imm16` | Trạng thái IMM-16 | Link → Workflow State |
| `root_cause_method` | Phương pháp phân tích nguyên nhân | Select |
| `root_cause_analysis` | Phân tích nguyên nhân gốc | Long Text |
| `effectiveness_result` | Kết quả kiểm tra hiệu quả | Select |
| `effectiveness_evidence` | Bằng chứng hiệu quả | Attach |
| `reopen_count` | Số lần mở lại | Int (read-only) |
| `waive_reason` | Lý do miễn trừ (nếu applicable) | Text |

### Workflows mới

- `IMM Compliance Finding Workflow` (5 states)
- `IMM CAPA Record Extended Workflow` (6 states — extends existing)
- `IMM Compliance Scorecard Workflow` (2 states: Draft → Published)
- `IMM Internal Audit Workflow` (4 states)

### API Endpoints mới

30 endpoints trong `assetcore/api/imm16.py` — xem `05_API_Specification.md §3` đầy đủ.

### Scheduler Jobs mới

| Job | Schedule | Mô tả |
|---|---|---|
| `run_compliance_evaluation_monthly` | 1st of month 00:05 | Đánh giá tất cả rule active |
| `run_compliance_evaluation_daily` | Daily 00:10 | Rule có frequency=Daily |
| `update_compliance_scorecard` | 2nd of month 02:00 | Tạo Scorecard tháng |
| `check_capa_due` | Daily 08:00 | Leo thang email CAPA quá hạn |
| `check_audit_milestones` | Daily 08:15 | Cảnh báo audit milestone |
| `check_quarterly_mr_reminder` | Weekly Mon 09:00 | Nhắc MR quý |
| `verify_audit_chain_daily` | Daily 03:00 | Verify hash chain integrity |

### Breaking Changes

Không có breaking change với module hiện có. IMM CAPA Record được **extend** (không replace). IMM-08 và IMM-09 cần bổ sung `validate_*` hook gọi `check_asset_compliance_status()` trong `doc_events`.

### Known Issues / Limitations

| # | Vấn đề | Workaround | Fix dự kiến |
|---|---|---|---|
| LIM-01 | Heatmap không có dữ liệu tháng đầu tiên sau go-live | Hiển thị "Chưa có dữ liệu" | Tháng tiếp theo sau eval |
| LIM-02 | Scorecard không thể tạo nếu không có Finding nào | `score_pct = 100%` mặc định | v1.1.x |
| LIM-03 | Escalation email chỉ hỗ trợ SMTP; chưa có Slack/Teams | Dùng SMTP | v1.2.x |

---

# Phần III — Traceability Matrix

> ⚠️ Pending implementation — Wave 3. Cột `Released-in` sẽ điền sau go-live.

| ID | Loại | Mô tả | Test Case | Released-in |
|---|---|---|---|---|
| US-16-01 | User Story | Khai báo Compliance Rule với change control | UAT-IMM16-01, UAT-IMM16-02 | — |
| US-16-02 | User Story | Auto-detect Finding hàng tháng, idempotent | UAT-IMM16-03 | — |
| US-16-03 | User Story | Xem xét Finding: NC / FP / Waive | UAT-IMM16-04, UAT-IMM16-07 | — |
| US-16-04 | User Story | CAPA lifecycle 6 trạng thái + effectiveness | UAT-IMM16-05, UAT-IMM16-06 | — |
| US-16-05 | User Story | Escalation matrix tự động | §II unit test (CAPA escalation) | — |
| US-16-06 | User Story | Waive Finding với approval VP | UAT-IMM16-07 | — |
| US-16-07 | User Story | Compliance Heatmap + drill-down | UAT-IMM16-12 | — |
| US-16-08 | User Story | Internal Audit cycle | UAT-IMM16-08 | — |
| US-16-09 | User Story | Scorecard sinh + publish + immutability | UAT-IMM16-09 | — |
| US-16-10 | User Story | Management Review quý + gate | UAT-IMM16-10 | — |
| BR-16-01 | Business Rule | Idempotent Finding upsert | UAT-IMM16-03 Step 4 | — |
| BR-16-02 | Business Rule | Escalation matrix theo severity × overdue | §II unit `TestCAPAHookValidation` | — |
| BR-16-03 | Business Rule | Not Effective → re-open CAPA | UAT-IMM16-06 | — |
| BR-16-04 | Business Rule | Major NC phải có CAPA trước close audit | UAT-IMM16-08 Step 5 | — |
| BR-16-05 | Business Rule | Rule change control + version bump | UAT-IMM16-01 Step 4, §II TestRuleChangeControl | — |
| BR-16-06 | Business Rule | Chỉ VP Block2 được Waive | UAT-IMM16-07 Step 1,7 | — |
| BR-16-07 | Business Rule | Published Scorecard immutable | UAT-IMM16-09 Step 6 | — |
| BR-16-08 | Business Rule | Quarterly MR gate publish Scorecard | UAT-IMM16-10 | — |
| BR-16-09 | Business Rule | Cross-module gate block WO Submit | UAT-IMM16-11 | — |
| BR-16-10 | Business Rule | Audit trail bắt buộc mọi action | §VI DocPerm + TC-16 | — |
| VR-01 | Validation | Threshold JSON phải có metric/op/value | UAT-IMM16-02 | — |
| VR-04 | Validation | Waive: reason≥50, evidence, expiry>today | UAT-IMM16-07 Steps 3-5 | — |
| VR-05 | Validation | root_cause_method bắt buộc → Action Plan | UAT-IMM16-05 Step 2 | — |
| VR-06 | Validation | effectiveness_result bắt buộc → Closed | UAT-IMM16-05 Step 7 | — |
| VR-07 | Validation | Không close khi effectiveness=Not Effective | UAT-IMM16-06 Step 2 | — |
| VR-08 | Validation | Major NC phải có CAPA trước close audit | UAT-IMM16-08 Step 5 | — |
| VR-09 | Validation | Published Scorecard read-only | UAT-IMM16-09 Step 6 | — |
| VR-10 | Validation | MR gate quarterly | UAT-IMM16-10 Step 2 | — |
| VR-11 | Validation | Rule change yêu cầu change_summary | UAT-IMM16-01 + §II TestRuleChangeControl | — |
| VR-12 | Validation | due_date phải > today | UAT-IMM16-05 Step 3 | — |
| NFR-01 | Non-functional | Monthly eval < 120s (1000 rules × 500 assets) | §VII Performance Benchmarks | — |
| NFR-02 | Non-functional | Heatmap API < 2s p95 | §VII Performance Benchmarks | — |
| NFR-03 | Non-functional | Gate API < 200ms p99 | §VII Performance Benchmarks | — |
| NFR-04 | Non-functional | Audit trail immutable | §V STRIDE + HS-IMM16-001 | — |
| SEC-01 | Security | @frappe.whitelist() mọi endpoint | §V SEC-01 | — |
| SEC-02 | Security | Sensitive actions → IMM Audit Trail | §V SEC-02 | — |
| SEC-03 | Security | Published Scorecard write=0 | §V SEC-03 | — |

---

## Phụ lục: Glossary (Từ điển thuật ngữ IMM-16)

| Thuật ngữ | Tiếng Việt | Giải thích |
|---|---|---|
| Compliance Rule | Quy tắc Tuân thủ | Tiêu chí đánh giá tuân thủ được khai báo trong hệ thống |
| Finding | Phát hiện | Kết quả đánh giá phát hiện vi phạm; có thể là NC hoặc False Positive |
| NC | Không phù hợp (Non-Conformance) | Vi phạm tiêu chí tuân thủ được xác nhận |
| False Positive | Cảnh báo sai | Finding được đánh giá là không phải NC thực |
| Waived | Đã miễn trừ | Finding được VP cho phép tạm bỏ qua với lý do và thời hạn |
| CAPA | Hành động Khắc phục & Phòng ngừa | Corrective and Preventive Action — chu trình xử lý NC |
| Effectiveness | Hiệu quả | Kết quả đánh giá xem CAPA có thực sự giải quyết vấn đề không |
| Scorecard | Bảng điểm Tuân thủ | Tổng hợp chỉ số tuân thủ hàng tháng |
| Management Review (MR) | Review Ban lãnh đạo | Cuộc họp quý của Ban lãnh đạo về hiệu quả tuân thủ |
| Internal Audit | Kiểm toán nội bộ | Đánh giá định kỳ do Kiểm toán viên nội bộ thực hiện |
| Heatmap | Bản đồ nhiệt | Biểu đồ màu sắc module × khoa phòng thể hiện mức tuân thủ |
| Threshold | Ngưỡng | Giá trị giới hạn để xác định tuân thủ hay không |
| Idempotent | Bất biến lần gọi | Chạy đánh giá nhiều lần cùng ngày chỉ tạo 1 Finding |
| RCA | Phân tích nguyên nhân gốc | Root Cause Analysis — phương pháp như 5-Why, Fishbone |
| Restate | Điều chỉnh lại | Tạo phiên bản Scorecard mới khi cần sửa sau publish |
