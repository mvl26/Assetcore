# IMM-02 — Phát hành (User Guide + Release Notes + Traceability)

> **Wave 2 — Live.** Bundle phát hành cùng IMM-01 / IMM-03 trên nhánh `feature/hieuc/wave-2`.

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường (Tech Spec & Market Analysis)** |
| Phiên bản | 0.0.2 |
| Ngày phát hành | 2026-05-27 (đồng bộ với app 0.0.2) |
| Chính sách versioning | Tuân theo `assetcore/__init__.py = 0.0.2`; module docs đồng bộ phiên bản app. |
| Owner | PM + BA + Tech Writer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) · [02 Analysis & Design](./02_Analysis_Design.md) |

---

# Phần I — Hướng Dẫn Sử Dụng

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.

## I.1. Giới Thiệu

Module **Đặc tả Kỹ thuật & Phân tích Thị trường (IMM-02)** là bước tiếp theo sau khi Kế hoạch mua sắm (IMM-01) được phê duyệt. Module giúp bệnh viện:

- Soạn thảo yêu cầu kỹ thuật chi tiết cho từng thiết bị cần mua.
- Khảo sát và so sánh ít nhất 3 thiết bị tương đương trên thị trường.
- Đánh giá khả năng lắp đặt trong môi trường bệnh viện (điện, khí y tế, mạng, không gian).
- Kiểm soát nguy cơ phụ thuộc vào một nhà cung cấp duy nhất (lock-in risk).
- Khóa hồ sơ kỹ thuật để chuyển sang giai đoạn đấu thầu (IMM-03).

**Trước khi bắt đầu, bạn cần:**
- Tài khoản hệ thống AssetCore và quyền truy cập module Đặc tả kỹ thuật
- Kế hoạch mua sắm (IMM-01) đã được Phó Giám đốc phê duyệt
- Chrome hoặc Edge phiên bản mới nhất, kết nối mạng nội bộ

## I.2. Các Vai Trò

| Vai trò | Bạn làm gì trong module này? |
|---|---|
| **Kỹ thuật viên HTM (HTM Engineer)** | Soạn yêu cầu kỹ thuật, thêm tài liệu, gửi rà soát |
| **Phụ trách KH-TC** | Nhập thông tin benchmark thị trường (≥ 3 thiết bị) |
| **Nhóm QA/Rủi ro** | Đánh giá hạ tầng bệnh viện và nguy cơ lock-in |
| **Phó Trưởng phòng VTTBYT (PTP Khối 1)** | Điều phối quy trình, trình duyệt |
| **Phó Giám đốc / BGĐ (VP Block1)** | Phê duyệt và khóa hồ sơ kỹ thuật |

## I.3. Quy Trình Chính

```
① Kế hoạch mua sắm được phê duyệt (IMM-01)
      │
      ▼ Hệ thống tự động tạo hồ sơ kỹ thuật
② HTM Engineer soạn yêu cầu kỹ thuật
   (≥ 8 yêu cầu bắt buộc, có phương pháp kiểm tra)
      │
      ▼ Gửi rà soát [Cổng G01]
③ KH-TC nhập benchmark thị trường
   (≥ 3 thiết bị so sánh)
      │
      ▼ Hoàn tất benchmark [Cổng G02]
④ Nhóm QA/Rủi ro đánh giá hạ tầng + lock-in
   (6 hạng mục hạ tầng + 5 chiều rủi ro)
      │
      ▼ Hoàn tất đánh giá [Cổng G03]
⑤ PTP Khối 1 trình duyệt BGĐ
      │
      ▼ Phê duyệt [Cổng G04]
⑥ Hồ sơ kỹ thuật được KHÓA
   → Chuyển sang đấu thầu IMM-03
```

## I.4. Thao Tác Theo Vai Trò

### a. HTM Engineer — Soạn yêu cầu kỹ thuật

**Khi nào làm?** Sau khi nhận thông báo Kế hoạch mua sắm được phê duyệt — hệ thống tự tạo hồ sơ kỹ thuật ở trạng thái *Nháp*.

**Các bước:**
1. Vào menu **Đặc tả kỹ thuật** → Tìm hồ sơ ở trạng thái *Nháp*
2. Mở hồ sơ → Tab **"Yêu cầu kỹ thuật"**
3. Kiểm tra yêu cầu đã được điền sẵn từ mẫu (nếu có)
4. Thêm/chỉnh sửa yêu cầu: chọn Nhóm, nhập Thông số, Giá trị/Phạm vi, Phương pháp kiểm tra
5. Đảm bảo: **ít nhất 8 yêu cầu bắt buộc** và **mọi yêu cầu bắt buộc phải có phương pháp kiểm tra**
6. Tải lên tài liệu (datasheet, tiêu chuẩn kỹ thuật) ở tab Tổng quan
7. Bấm **"Gửi rà soát"** → hồ sơ chuyển sang KH-TC

> ⚠️ **Lưu ý:** Phương pháp kiểm tra là bắt buộc cho mọi yêu cầu "Bắt buộc" (Mandatory). Không điền → hệ thống không cho gửi rà soát.

> 💡 **Mẹo:** Dùng **"Import Excel"** để nhập nhiều yêu cầu cùng lúc (tải mẫu Excel từ hệ thống).

### b. KH-TC — Nhập benchmark thị trường

**Khi nào làm?** Sau khi nhận thông báo hồ sơ đang ở trạng thái *Đang rà soát*.

**Các bước:**
1. Mở hồ sơ → Tab **"Benchmark"**
2. Bấm **"Thêm ứng viên"**, nhập thông tin cho mỗi thiết bị so sánh:
   - Nhà sản xuất, Model, Quốc gia
   - % Đáp ứng yêu cầu kỹ thuật (tính tự động hoặc nhập thủ công)
   - Giá tham chiếu + Nguồn giá (báo giá nhà cung cấp / đấu thầu công khai / website)
   - Mức độ hỗ trợ kỹ thuật (Tier 1/2/3)
   - Đại lý tại Việt Nam
3. Nhập **ít nhất 3 ứng viên** so sánh
4. Điều chỉnh trọng số so sánh (% Kỹ thuật / % Giá / % Hỗ trợ / % Thương hiệu) nếu cần
5. Hệ thống tự chọn ứng viên được khuyến nghị (điểm cao nhất)
6. Bấm **"Hoàn tất benchmark"** → hồ sơ chuyển sang Nhóm QA

> ⚠️ **Lưu ý:** Phải có ít nhất 3 ứng viên. Chỉ nhập 2 → hệ thống không cho chuyển bước.

### c. Nhóm QA/Rủi ro — Đánh giá hạ tầng và lock-in

**Khi nào làm?** Sau khi nhận thông báo hồ sơ đang ở trạng thái *Đã benchmark*.

**Đánh giá hạ tầng (6 hạng mục):**
1. Mở hồ sơ → Tab **"Hạ tầng + Lock-in"** → phần Hạ tầng
2. Điền trạng thái hiện tại và yêu cầu cho mỗi hạng mục:
   - **Điện**: điện áp, công suất
   - **Khí y tế**: O2, khí nén y tế, chân không
   - **Mạng/CNTT**: băng thông, giao thức
   - **HIS-PACS-LIS**: phiên bản HL7/FHIR, kết nối hệ thống
   - **Điều hòa**: nhiệt độ, độ ẩm yêu cầu
   - **Không gian**: diện tích, bố trí
3. Chọn trạng thái: Tương thích / Cần nâng cấp / Cần nâng cấp lớn / Không áp dụng
4. Nếu "Cần nâng cấp": điền chi phí ước tính và thời hạn nâng cấp

**Đánh giá lock-in (5 chiều):**
1. Vào phần Lock-in Risk
2. Chấm điểm 1-5 cho 5 chiều: Giao thức, Tiêu hao, Phần mềm, Phụ tùng, Dịch vụ
3. Hệ thống tự tính điểm lock-in tổng hợp (hiển thị biểu đồ radar)
4. Nếu điểm cao (> ngưỡng): bắt buộc nhập **Kế hoạch giảm thiểu** và tải bằng chứng lên
5. Bấm **"Hoàn tất đánh giá"** → hồ sơ chuyển sang PTP Khối 1

> ⚠️ **Lưu ý (CNTT):** Mục Mạng/CNTT và HIS-PACS-LIS do bộ phận CNTT đánh giá và xác nhận.

### d. VP Block1 — Phê duyệt và khóa hồ sơ

**Khi nào làm?** Khi nhận thông báo hồ sơ đang *Chờ phê duyệt*.

**Các bước:**
1. Mở hồ sơ → Xem tổng quan 4 tab
2. Kiểm tra điểm lock-in và kế hoạch giảm thiểu (nếu có)
3. Bấm **"Phê duyệt"** → Hồ sơ KHÓA — không thể sửa thêm
4. Hệ thống tự chuyển sang giai đoạn đấu thầu (IMM-03)

> ⚠️ **Sau khi KHÓA**: Hồ sơ trở thành tài liệu pháp lý không thể sửa. Nếu cần thay đổi → bấm "Rút hồ sơ" (nhập lý do) → Rồi "Tái phát hành" (tạo phiên bản mới v2.0).

## I.5. Bảng Điều Khiển (Dashboard)

| KPI | Ý nghĩa | Mục tiêu |
|---|---|---|
| **Thời gian xử lý trung bình** | Số ngày từ Nháp → Khóa | < 30 ngày |
| **% Spec đủ ≥ 3 benchmark** | Tỷ lệ hồ sơ đã benchmark | 100% |
| **Điểm lock-in trung bình** | Mức độ phụ thuộc nhà cung cấp | ≤ 2.5 / 5 |
| **Tỷ lệ làm lại** | % hồ sơ quay về Nháp | < 20% |
| **Hồ sơ quá hạn** | Số hồ sơ Nháp > 30 ngày | Giảm dần |

## I.6. Câu Hỏi Thường Gặp

**Q: Hệ thống tự tạo hồ sơ kỹ thuật — tôi có phải làm gì không?**
> A: Hồ sơ được tạo tự động từ Kế hoạch mua sắm được duyệt (IMM-01). Bạn (HTM Engineer) sẽ nhận thông báo và cần bổ sung/chỉnh sửa yêu cầu kỹ thuật cho phù hợp với thiết bị thực tế.

**Q: Spec đã bị khóa nhưng cần thay đổi — phải làm sao?**
> A: Dùng chức năng **"Rút hồ sơ"** (nhập lý do) → Sau đó **"Tái phát hành"** để tạo phiên bản mới (v2.0). Phiên bản cũ vẫn được lưu trữ đầy đủ.

**Q: Điểm lock-in là gì và mức nào là nguy hiểm?**
> A: Điểm lock-in (1-5) đo mức độ phụ thuộc vào một nhà cung cấp. ≤ 2.5 là bình thường. 2.5-3.5 cần chú ý. > 3.5 là nguy cơ cao — bắt buộc có kế hoạch giảm thiểu mới được khóa hồ sơ.

**Q: Tôi là HTM Engineer nhưng không thấy điểm lock-in trong hồ sơ?**
> A: Điểm lock-in là thông tin nhạy cảm, chỉ hiển thị với Nhóm QA/Rủi ro, VP Block1 và Quản trị viên. Đây là thiết kế cố ý để bảo vệ tính khách quan trong đánh giá.

**Q: Hồ sơ đã ở trạng thái Khóa nhưng thông số kỹ thuật thực tế đã thay đổi — làm gì?**
> A: Báo cáo VP Block1 để "Rút hồ sơ" với lý do cụ thể. HTM Engineer sau đó "Tái phát hành" tạo v2.0, cập nhật thông số mới và nộp lại toàn bộ quy trình.

## I.7. Phím Tắt & Mã Trạng Thái

| Trạng thái | Ý nghĩa |
|---|---|
| Nháp | Hồ sơ vừa tạo, HTM Engineer đang soạn |
| Đang rà soát | Đang chờ KH-TC nhập benchmark |
| Đã benchmark | Benchmark xong, QA/Rủi ro đang đánh giá |
| Đã đánh giá rủi ro | Đánh giá xong, chờ trình duyệt |
| Chờ phê duyệt | Đang chờ VP Block1 duyệt |
| Đã khóa | Hồ sơ chính thức, không thể sửa |
| Đã rút | Hồ sơ bị rút, có thể tái phát hành |

---

# Phần II — Release Notes

## II.1. Tóm Tắt

Wave 2 đưa module **Đặc tả Kỹ thuật & Phân tích Thị trường (IMM-02)** vào vận hành đồng thời với IMM-01 + IMM-03. Module chuẩn hóa quy trình soạn thảo ĐKTKT theo chuẩn WHO HTM và ISO 13485, đảm bảo tính khách quan trong benchmark thị trường và kiểm soát nguy cơ lock-in nhà cung cấp.

**Commit chính (nhánh `feature/hieuc/wave-2`):**

| Commit | Mô tả |
|---|---|
| `d2279ab` | Add module IMM-01, IMM-02, IMM-03 (BE skeleton + workflow) |
| `4a3ad1c` | Resolve conflicts và sync Wave 2 với global formatters |
| `d56c0cd` | Fix bug Wave 1 & 2, enhance AI agents |
| `810179e` | feat (BE+FE): add module 1,2,3, update UI dashboard `/launcher` |
| `82a9607` | fix (FE): Modal create new needs-requests, sidebar, filter IMM-1/2/3 |
| `fce3655` | fix(FE): update fullname user + list view một số page |

## II.2. Tính Năng Mới

### Soạn yêu cầu kỹ thuật (HTM Engineer)

Soạn ĐKTKT theo cấu trúc chuẩn với 8 nhóm tiêu chí (Hiệu suất, An toàn, Kết nối, Điện, Cơ học, Phần mềm, Dịch vụ, Tuân thủ).

- Nhập thủ công từng yêu cầu hoặc import hàng loạt từ Excel (tối đa 200 dòng/lần)
- Áp dụng mẫu có sẵn theo danh mục thiết bị (10 mẫu: Life Support, Imaging, Monitoring...)
- 4 cổng kiểm soát (G01-G04) đảm bảo chất lượng trước khi tiến bước

[→ Hướng dẫn: §I.5.a]

### Benchmark thị trường khách quan (KH-TC)

So sánh ≥ 3 thiết bị cùng loại với tính điểm tự động dựa trên trọng số có thể điều chỉnh.

- % Đáp ứng yêu cầu kỹ thuật tính tự động (so sánh với mandatory requirements)
- Trọng số linh hoạt: Kỹ thuật / Giá / Hỗ trợ / Thương hiệu
- Hệ thống tự chọn ứng viên được khuyến nghị
- Lưu giá tham chiếu với nguồn thông tin rõ ràng (chống tranh chấp đấu thầu)

[→ Hướng dẫn: §I.5.b]

### Đánh giá hạ tầng toàn diện (QA Risk + CNTT)

6 hạng mục hạ tầng bắt buộc, phát hiện sớm chi phí nâng cấp trước khi ký hợp đồng.

- Điện / Khí y tế / Mạng-CNTT / HIS-PACS-LIS / HVAC / Không gian
- Tự động tạo task chuẩn bị lắp đặt (IMM-04) khi phát hiện "Cần nâng cấp"
- Tổng chi phí nâng cấp ước tính tự động tổng hợp

[→ Hướng dẫn: §I.5.c]

### Kiểm soát lock-in risk (QA Risk Team)

Đánh giá 5 chiều nguy cơ phụ thuộc nhà cung cấp, biểu đồ radar trực quan.

- 5 chiều: Giao thức, Tiêu hao, Phần mềm, Phụ tùng, Dịch vụ (có trọng số theo chuẩn bệnh viện)
- Điểm lock-in tính tự động; ngưỡng cảnh báo có thể cấu hình
- Permlevel bảo vệ: chỉ QA Risk / VP Block1 thấy điểm lock-in (HTM Engineer không thấy)

[→ Hướng dẫn: §I.5.c]

## II.3. Cải Tiến

| Mô tả | Module | Tác động |
|---|---|---|
| Tự động trigger từ IMM-01 Plan Approved | IMM-01 Integration | Không cần tạo thủ công; giảm sai sót |
| Tự động trigger IMM-03 khi Locked | IMM-03 Integration | Vendor Evaluation seed sẵn; quy trình liền mạch |
| Tự động register IMM-10 Risk khi lock-in cao | IMM-10 Integration | Risk Register luôn cập nhật |

## II.4. Known Issues

| Vấn đề | Workaround | Fix dự kiến |
|---|---|---|
| Bulk import tối đa 200 dòng/lần (limit hiện tại) | Chia nhỏ file Excel | v1.2.1 |
| LockInRadar chưa export được PDF | Chụp màn hình hoặc export data CSV | v1.3.0 |

## II.5. Yêu Cầu Nâng Cấp

- **Phụ thuộc**: IMM-01 phải deployed và stable (v1.1.0+)
- **Migration tự động**: Patch `v1_2_0.*` chạy qua `bench migrate`
- **Training bắt buộc**: 5 role hoàn tất training trước go-live (xem `08_Deployment.md §II.7`)

---

# Phần III — Traceability Matrix

## III.1. Cách Dùng

- Status: ⬜ Not started · 🟡 In progress · 🟠 Blocked · ✅ Done · ❌ Cancelled

## III.2. Matrix Chính

| Req ID | Loại | Mô tả ngắn | Doc ref | Design / Code | Test ID | UAT ID | PR | Released in | Status |
|---|---|---|---|---|---|---|---|---|---|
| US-02-001 | Story | Tạo Tech Spec từ Plan Line | Func Specs §3.1 | `services/imm02.py: draft_from_plan()` | `TestDraftFromPlan: test_draft_creates_spec` | UAT-IMM02-01 | #imm02-core | v1.0.0 | ⬜ |
| US-02-010 | Story | Soạn requirements mandatory + test_method | Func Specs §3.2 | `services/imm02.py: _vr03_test_method_present()` | `TestVR03TestMethod: test_mandatory_needs_method` | UAT-IMM02-02, UAT-IMM02-03 | #imm02-core | v1.0.0 | ⬜ |
| US-02-011 | Story | G01 block nếu thiếu test_method | Func Specs §3.2 | `validate_gate_g01()` | `TestGateG01: test_gate_g01_fails_missing_test_method` | UAT-IMM02-03 | #imm02-core | v1.0.0 | ⬜ |
| US-02-020 | Story | Nhập ≥ 3 candidates benchmark | Func Specs §3.3 | `services/imm02.py: validate_benchmark()` | `TestVR04BenchmarkMin3: test_fail_2_candidates` | UAT-IMM02-04, UAT-IMM02-05 | #imm02-core | v1.0.0 | ⬜ |
| US-02-030 | Story | Đánh giá 6 mục infra | Func Specs §3.4 | `_vr05_infra_completeness()`, `validate_gate_g03()` | `TestGateG03: test_gate_g03_passes_6_items` | UAT-IMM02-06, UAT-IMM02-07 | #imm02-core | v1.0.0 | ⬜ |
| US-02-040 | Story | Tính lock-in score 5 chiều | Func Specs §3.5 | `services/imm02.py: compute_lock_in()` | `TestComputeLockIn: test_compute_correct_weights` | UAT-IMM02-08, UAT-IMM02-09 | #imm02-core | v1.0.0 | ⬜ |
| US-02-050 | Story | Lock spec → trigger IMM-03 | Func Specs §3.6 | `services/imm02.py: lock_spec()` | `TestLockSpec: test_lock_triggers_imm03` | UAT-IMM02-09 | #imm02-core | v1.0.0 | ⬜ |
| US-02-060 | Story | Withdraw + Reissue versioning | Func Specs §3.7 | `withdraw_spec()`, `reissue_spec()` | `TestReissue: test_reissue_creates_new_version` | UAT-IMM02-11, UAT-IMM02-12 | #imm02-core | v1.0.0 | ⬜ |
| BR-02-01 | Rule | 1 plan_line ↔ 1 Active Tech Spec | Module Overview §8 | `_vr01_unique_per_plan_line()` | `TestDraftFromPlan: test_vr01_duplicate_raises` | UAT-IMM02-01 | #imm02-core | v1.0.0 | ⬜ |
| BR-02-02 | Rule | ≥ 8 mandatory requirements | Module Overview §8 | G01: `validate_gate_g01()` | `TestGateG01: test_gate_g01_fails_mandatory_count` | UAT-IMM02-02 | #imm02-core | v1.0.0 | ⬜ |
| BR-02-03 | Rule | Mandatory phải có test_method | Module Overview §8 | `_vr03_test_method_present()` | `TestVR03TestMethod` | UAT-IMM02-03 | #imm02-core | v1.0.0 | ⬜ |
| BR-02-04 | Rule | ≥ 3 benchmark candidates | Module Overview §8 | G02: `validate_gate_g02()` | `TestVR04BenchmarkMin3` | UAT-IMM02-04 | #imm02-core | v1.0.0 | ⬜ |
| BR-02-05 | Rule | 6/6 infra domains | Module Overview §8 | G03: `validate_gate_g03()` | `TestGateG03` | UAT-IMM02-06 | #imm02-core | v1.0.0 | ⬜ |
| BR-02-06 | Rule | lock-in score ≤ threshold OR mitigation | Module Overview §8 | G04: `validate_gate_g04()` | `TestGateG04` | UAT-IMM02-08, UAT-IMM02-09 | #imm02-core | v1.0.0 | ⬜ |
| BR-02-07 | Rule | Locked spec chỉ sửa qua Withdraw+Reissue | Module Overview §8 | `before_save` docstatus=1 check | `TestReissue: test_locked_spec_cannot_be_edited` | UAT-IMM02-10 | #imm02-core | v1.0.0 | ⬜ |
| ISO 13485 §7.3.2 | Compliance | Requirements documented | 08 §II.2 | Tech Spec Requirement child table | `TestVR02MandatoryMin` | UAT-IMM02-02 | #imm02-core | v1.0.0 | ⬜ |
| ISO 13485 §7.3.3 | Compliance | Design verification test_method | 08 §II.2 | `_vr03_test_method_present()` | `TestVR03TestMethod` | UAT-IMM02-03 | #imm02-core | v1.0.0 | ⬜ |
| ISO 13485 §7.3.7 | Compliance | Design change control | 08 §II.2 | Withdraw+Reissue pattern | `TestReissue: test_reissue_creates_new_version` | UAT-IMM02-11 | #imm02-core | v1.0.0 | ⬜ |
| WHO HTA §4.2 | Compliance | ≥ 3 model comparison | 08 §II.2 | BR-02-04: G02 | `TestVR04BenchmarkMin3` | UAT-IMM02-04 | #imm02-core | v1.0.0 | ⬜ |
| WHO Procurement Ch.3 | Compliance | Performance + Safety + Service spec | 08 §II.2 | Requirement groups + test_method | `TestGateG01` | UAT-IMM02-02 | #imm02-core | v1.0.0 | ⬜ |
| NĐ98/Điều 29 | Compliance | Không ưu ái nhà cung cấp cụ thể | 08 §II.2 | Lock-in Risk bắt buộc (G04) | `TestGateG04` | UAT-IMM02-08 | #imm02-core | v1.0.0 | ⬜ |
| NĐ98/Điều 15.2 | Compliance | Lưu trữ ≥ 5 năm | 08 §II.2 | `IMM Audit Trail` immutable | `test_audit_trail_logged_all_transitions` | UAT-IMM02-12 | #imm02-core | v1.0.0 | ⬜ |
| LĐT/Điều 43 | Compliance | HSMT có ĐKTKT | 08 §II.2 | Tech Spec Locked → IMM-03 trigger | `TestLockSpec: test_lock_triggers_imm03` | UAT-IMM02-09 | #imm02-core | v1.0.0 | ⬜ |
| SEC-IMM02-01 | Security | Permlevel: lock_in_score ẩn với HTM Eng | 07 §III.2 | `permlevel=1` field + API filter | `test_lock_in_score_hidden_from_htm_engineer` | UAT-IMM02-08 | #imm02-core | v1.0.0 | ⬜ |
| SEC-IMM02-02 | Security | Audit chain không tamper | 07 §III.1 | `IMM Audit Trail` no-delete | `test_audit_chain_breaks_on_tamper` | — | #imm02-core | v1.0.0 | ⬜ |

## III.3. Reverse Lookup

| Test ID | Requirement(s) cover |
|---|---|
| `TestDraftFromPlan: test_draft_creates_spec` | US-02-001 |
| `TestDraftFromPlan: test_vr01_duplicate_raises` | US-02-001, BR-02-01 |
| `TestVR03TestMethod: test_mandatory_needs_method` | US-02-010, BR-02-03, ISO 13485 §7.3.3 |
| `TestGateG01: test_gate_g01_fails_mandatory_count` | US-02-010, BR-02-02 |
| `TestGateG01: test_gate_g01_fails_missing_test_method` | US-02-011, BR-02-03 |
| `TestVR04BenchmarkMin3: test_fail_2_candidates` | US-02-020, BR-02-04, WHO HTA §4.2 |
| `TestGateG03: test_gate_g03_passes_6_items` | US-02-030, BR-02-05 |
| `TestComputeLockIn: test_compute_correct_weights` | US-02-040 |
| `TestGateG04` | US-02-040, BR-02-06, NĐ98/Điều 29 |
| `TestLockSpec: test_lock_triggers_imm03` | US-02-050, LĐT/Điều 43 |
| `TestReissue: test_reissue_creates_new_version` | US-02-060, ISO 13485 §7.3.7 |
| `TestReissue: test_locked_spec_cannot_be_edited` | BR-02-07 |
| `test_lock_in_score_hidden_from_htm_engineer` | SEC-IMM02-01 |
| `test_audit_trail_logged_all_transitions` | NĐ98/Điều 15.2 |

## III.4. Coverage Gaps

| Req ID | Thiếu gì? | Owner | Deadline |
|---|---|---|---|
| Bulk import > 200 rows | Upload limit chưa nâng | Dev IMM-02 | v1.2.1 |
| LockInRadar PDF export | Chart export chưa hỗ trợ | Dev FE | v1.3.0 |
| Pentest report `docs/security/` | Report chưa upload | Security | Trước go-live |
| Rate limit `bulk_import_requirements` | Security roadmap | DevOps | v1.2.1 |

## III.5. Bảng Thống Kê Thông Tin Ứng Dụng

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| DocType (chính) | 3 | `IMM Tech Spec`, `IMM Market Benchmark`, `IMM Lock-in Risk Assessment` |
| DocType (child) | 5 | `Tech Spec Requirement`, `Benchmark Candidate`, `Infra Compatibility Item`, `Lock-in Risk Item`, `Tech Spec Document` |
| Workflow JSON | 1 | `IMM-02 Spec Workflow` — 7 states, 9 transitions (xem 04 §V.2) |
| API endpoint | 16 | `list_tech_specs, get_tech_spec, create_tech_spec, draft_from_plan, update_tech_spec, add_requirement, bulk_import_requirements, transition_workflow, get_market_benchmark, get_lock_in_assessment, lock_spec, withdraw_spec, reissue_spec, submit_benchmark, submit_lock_in_assessment, dashboard_kpis` |
| FE view / page | 3 | `TechSpecListView`, `TechSpecCreateView`, `TechSpecDetailView` (Benchmark + Lock-in detail embed trong Tech Spec Detail) |
| FE store | 1 | `stores/imm02.ts` — Pinia store id `imm02` |
| Service function | 23 | xem `assetcore/services/imm02.py`: 4 lifecycle hooks + 4 VR + 4 Gate + 2 rollup + 2 benchmark/lockin validator + 2 weighting helper + 2 requirement helper + 2 scheduler + `_check_workflow_gates_ts` |
| Scheduler job | 2 | Daily `check_overdue_drafts`, Weekly `benchmark_freshness_alert` (xem `hooks.py`) |
| Business Rule | 7 | BR-02-01 → BR-02-07 |
| Role áp dụng | 7 | HTM Engineer, Planning Officer, Risk Officer, System Admin, Dept Head, Board Approver, System Admin (CNTT) |
| Test case unit | ~45 | 15 test class × ~3 case avg |
| UAT scenario | 12 | UAT-IMM02-01 → 12 |
| LOC BE (`services/imm02.py`) | ~420 | Ước tính |
| LOC API (`api/imm02.py`) | ~240 | 14 endpoints |
| LOC FE (views + store) | ~2,200 | Ước tính 5 views + 1 store + 6 components |
| Sprint hoàn thành (Wave 2) | 4 | Sprint 9-12 (sau IMM-01) |
| User Story | 8 | US-02-001, 010, 011, 020, 030, 040, 050, 060 |

---

## DoD — Hoàn chỉnh

### I. User Guide
- [x] Tiếng Việt 100%, không jargon
- [x] Mô tả tất cả 5 role với hướng dẫn step-by-step
- [x] Dashboard KPI có giải thích mục tiêu
- [x] FAQ 5 câu thực tế
- [x] Cheat sheet trạng thái
- [ ] ≥ 5 screenshot UI thực tế (chụp trên staging trước go-live)
- [ ] Reviewed bởi BA + đại diện HTM Engineer + QA Risk Team

### II. Release Notes
- [x] Tóm tắt 2-3 câu user-friendly
- [x] 4 tính năng mới có role hưởng lợi
- [x] Known issues + workaround
- [x] Breaking change: không có
- [x] Phụ thuộc IMM-01 documented
- [ ] Reviewed bởi PM + Tech Lead + BA

### III. Traceability Matrix + Bảng Thống Kê
- [x] 25 dòng: 8 User Story + 7 BR + 7 Compliance + 3 Security
- [x] Mọi dòng có ≥ 4 cell điền (status ⬜ Wave 2)
- [x] Reverse lookup (14 entries)
- [x] Coverage gaps liệt kê (4 gaps, roadmap)
- [x] Bảng thống kê 17 hạng mục
- [ ] Reviewed bởi PM + Tech Lead + QA Lead
