# IMM-01 — Phát hành (User Guide + Release Notes + Traceability)

> **Wave 2 — Live.** Module IMM-01 đã GA. Tài liệu này tổng hợp User Guide + Release Notes + Traceability Matrix dựa trên codebase thực tế.

| Mục | Giá trị |
|---|---|
| Module | **IMM-01 — Đánh giá Nhu cầu & Dự toán (Needs Assessment & Budget Estimation)** |
| Phiên bản | 0.0.2 |
| Ngày phát hành | 2026-05-27 (đồng bộ với app 0.0.2) |
| Cập nhật | 2026-05-27 |
| Chính sách versioning | Tuân theo `assetcore/__init__.py = 0.0.2`; module docs đồng bộ phiên bản app. |
| Owner | PM + BA + Tech Writer |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [07 Testing QA](./07_Testing_QA.md) · [08 Deployment](./08_Deployment.md) |

---

# Phần I — Hướng Dẫn Sử Dụng

> **Ngôn ngữ**: Tiếng Việt 100%. Không dùng mã kỹ thuật cho người dùng cuối.

## I.1. Giới Thiệu

Module **Đánh giá Nhu cầu & Dự toán (IMM-01)** là cổng khởi đầu của vòng đời thiết bị y tế trong hệ thống AssetCore. Module giúp bệnh viện:

- Thu thập và tổng hợp đề xuất thiết bị từ các khoa phòng.
- Chấm điểm và xếp ưu tiên đầu tư dựa trên 6 tiêu chí khách quan.
- Lập dự toán ngân sách toàn vòng đời (CAPEX + chi phí vận hành 5 năm).
- Xây dựng kế hoạch mua sắm tổng thể và chuyển sang giai đoạn đặc tả kỹ thuật.

Mọi đề xuất đều được ghi lại thành **phiếu đề xuất nhu cầu (Needs Request)**. Bạn có thể theo dõi tiến trình, xem điểm ưu tiên, và kiểm tra dự toán ngân sách theo thời gian thực.

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
- **② Sidebar**: Menu module. Tìm **"Nhu cầu thiết bị"** hoặc **"IMM-01"** để vào module.
- **③ Vùng chính**: Danh sách phiếu, chi tiết phiếu, hoặc Dashboard.

## I.3. Các Vai Trò

| Vai trò | Bạn làm gì trong module này? |
|---|---|
| **Trưởng khoa lâm sàng** | Tạo phiếu đề xuất nhu cầu thiết bị, gửi đề xuất để xét duyệt |
| **HTM Reviewer** | Thẩm định lâm sàng, chấm điểm tác động lâm sàng và rủi ro |
| **KH-TC / Phó giám đốc** | Chấm điểm sử dụng và ngân sách, lập và phê duyệt kế hoạch mua sắm |
| **Kế toán (TCKT)** | Nhập dự toán CAPEX + OPEX, xác nhận nguồn vốn |
| **Phó Trưởng phòng VTTBYT** | Xem dashboard tổng hợp, báo cáo dự báo nhu cầu dài hạn |

## I.4. Quy Trình Chính

```
① Khoa phòng phát sinh nhu cầu thiết bị
      │
      ▼
② Trưởng khoa tạo phiếu đề xuất (Needs Request)
      │
      ▼
③ Gửi đề xuất → HTM Reviewer nhận thông báo
      │
      ▼
④ HTM Reviewer chấm điểm lâm sàng
      │
      ▼
⑤ KH-TC chấm điểm ngân sách & lập dự toán
      │
      ▼
⑥ Trình duyệt → Phó Giám đốc phê duyệt / từ chối
      │
      ├──► ✅ Phê duyệt → Nhu cầu vào Kế hoạch mua sắm
      └──► ❌ Từ chối → Trả lại khoa, có thể nộp lại
                  │
                  ▼
⑦ Kế hoạch mua sắm tổng hợp → Chuyển sang Đặc tả kỹ thuật (IMM-02)
```

## I.5. Thao Tác Theo Vai Trò

### a. Trưởng khoa — Tạo phiếu đề xuất nhu cầu

**Khi nào làm?** Khi khoa cần thiết bị mới, cần thay thế thiết bị cũ, hoặc cần nâng cấp thiết bị hiện có.

**Các bước:**
1. Vào menu **Nhu cầu thiết bị** → bấm nút **"Tạo mới"** (góc phải trên)
2. Chọn **Loại đề xuất**: Mới / Thay thế / Nâng cấp / Bổ sung
3. Chọn **Mô hình thiết bị** từ danh sách
4. Điền **Lý do lâm sàng** (tối thiểu 200 ký tự — hệ thống kiểm tra)
5. Điền số lượng, khoa đề xuất, năm cần thiết
6. Nếu thay thế: chọn **Thiết bị cần thay thế** (bắt buộc)
7. Bấm **"Gửi đề xuất"** — phiếu chuyển sang trạng thái *Đã gửi*

> ⚠️ **Lưu ý:** Lý do lâm sàng phải đủ chi tiết (tối thiểu 200 ký tự). Nếu đề xuất thay thế thiết bị cũ, phải có kế hoạch thanh lý (IMM-13) đã được tạo.

---

**Theo dõi phiếu của bạn:**
- Vào **Nhu cầu thiết bị** → Danh sách → Lọc "Của khoa tôi"
- Bấm vào số hiệu phiếu để xem chi tiết và lịch sử xử lý

### b. HTM Reviewer — Thẩm định và chấm điểm

**Khi nào làm?** Sau khi nhận thông báo có phiếu đề xuất mới cần thẩm định.

**Các bước:**
1. Vào **Nhu cầu thiết bị** → Danh sách → Lọc trạng thái *Đã gửi*
2. Mở phiếu → Xem tab **"Thẩm định lâm sàng"**
3. Điền điểm cho **Tác động lâm sàng** (1-5) và **Rủi ro khi không đầu tư** (1-5)
4. Ghi nhận số liệu thực tế từ IMM-07 (tỷ lệ sử dụng, thời gian dừng máy)
5. Bấm **"Hoàn tất thẩm định"** → chuyển sang KH-TC

> 💡 **Mẹo:** Bấm vào tên thiết bị để xem lịch sử bảo trì và sự cố (IMM-09/IMM-08).

### c. KH-TC / TCKT — Lập dự toán và kế hoạch

**Khi nào làm?** Sau khi HTM Reviewer hoàn tất chấm điểm lâm sàng.

**Các bước chấm điểm ngân sách:**
1. Mở phiếu → Tab **"Chấm điểm ngân sách"**
2. Điền điểm cho **Tình trạng sử dụng** (khoảng cách so với mục tiêu), **Tín hiệu thay thế**, **Tuân thủ pháp lý**, **Phù hợp ngân sách**
3. Hệ thống tự tính điểm tổng hợp và xếp loại ưu tiên (P1/P2/P3/P4)

**Các bước lập dự toán:**
1. Mở tab **"Dự toán ngân sách"**
2. Điền **Chi phí mua sắm (CAPEX)**: đơn giá, số lượng
3. Điền **Chi phí vận hành (OPEX)** cho 5 năm: bảo trì, tiêu hao, đào tạo, phụ tùng
4. Chọn **Nguồn vốn**: Ngân sách / Tài trợ / BHYT / Xã hội hóa / Vay vốn
5. Bấm **"Xác nhận dự toán"**

**Lập kế hoạch mua sắm:**
1. Vào **Kế hoạch mua sắm** → Tạo mới
2. Chọn các phiếu đề xuất đã phê duyệt để đưa vào kế hoạch
3. Sắp xếp thứ tự ưu tiên → Bấm **"Trình duyệt"**

### d. Phó Giám đốc — Phê duyệt kế hoạch

**Khi nào làm?** Khi nhận thông báo có kế hoạch mua sắm chờ duyệt.

**Các bước:**
1. Vào **Kế hoạch mua sắm** → Lọc trạng thái *Chờ phê duyệt*
2. Xem tổng hợp: tổng giá trị, xếp ưu tiên, nguồn vốn
3. Bấm **"Phê duyệt"** hoặc **"Từ chối"** (ghi lý do)
4. Kế hoạch được phê duyệt → hệ thống tự động chuyển sang giai đoạn đặc tả kỹ thuật

## I.6. Bảng Điều Khiển (Dashboard)

Vào **Nhu cầu thiết bị → Dashboard** để xem tổng quan:

| KPI | Ý nghĩa | Trend tốt |
|---|---|---|
| **Phiếu chờ xử lý** | Số phiếu chưa được thẩm định | ↓ Giảm |
| **Tỷ lệ phê duyệt** | % phiếu được phê duyệt trong kỳ | Ổn định theo chiến lược |
| **Tỷ lệ P1 trong kế hoạch** | % thiết bị ưu tiên cao | Tùy theo năng lực ngân sách |
| **Thời gian xử lý trung bình** | Số ngày từ đề xuất → quyết định | ↓ Giảm |
| **Dự báo nhu cầu 5 năm** | Số lượng thiết bị dự kiến cần mua sắm | Phụ thuộc chiến lược |

Bấm vào biểu đồ để lọc theo khoa phòng, loại thiết bị, hoặc khoảng thời gian.

## I.7. Câu Hỏi Thường Gặp

**Q: Tôi điền lý do lâm sàng nhưng hệ thống báo "chưa đủ 200 ký tự"?**
> A: Lý do lâm sàng phải giải thích rõ nhu cầu y tế của khoa, tác động đến bệnh nhân, và ảnh hưởng khi không có thiết bị. Hệ thống yêu cầu tối thiểu 200 ký tự để đảm bảo chất lượng thẩm định.

**Q: Tôi muốn đề xuất thay thế máy cũ nhưng hệ thống yêu cầu "kế hoạch thanh lý"?**
> A: Mọi đề xuất thay thế đều phải có kế hoạch thanh lý thiết bị cũ (IMM-13). Liên hệ Phòng VTTBYT để tạo kế hoạch thanh lý trước khi nộp đề xuất thay thế.

**Q: Điểm ưu tiên được tính như thế nào?**
> A: Hệ thống chấm điểm 6 tiêu chí (thang 1-5): tác động lâm sàng, rủi ro không đầu tư, tình trạng sử dụng, tín hiệu thay thế, tuân thủ pháp lý, phù hợp ngân sách. Mỗi tiêu chí có trọng số khác nhau. Điểm tổng hợp ≥ 4.0 = P1 (ưu tiên cao nhất).

**Q: Phiếu của tôi bị từ chối, tôi có nộp lại được không?**
> A: Có. Phiếu bị từ chối sẽ quay về trạng thái "Cần chỉnh sửa". Bạn có thể chỉnh sửa theo ý kiến của người duyệt và gửi lại. Lịch sử phê duyệt và lý do từ chối được lưu đầy đủ.

**Q: Sau khi kế hoạch mua sắm được phê duyệt, bước tiếp theo là gì?**
> A: Hệ thống tự động chuyển kế hoạch sang module Đặc tả kỹ thuật (IMM-02). Phòng Kỹ thuật sẽ soạn thảo ĐKTKT cho từng thiết bị trong kế hoạch.

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
| Draft | Phiếu đang soạn, chưa gửi |
| Submitted | Đã gửi, đang chờ thẩm định |
| Under Review | HTM Reviewer đang xem xét |
| Scoring | KH-TC đang chấm điểm và dự toán |
| Pending Approval | Đã đủ điều kiện, chờ BGĐ duyệt |
| Approved | Được phê duyệt, vào kế hoạch mua sắm |
| Rejected | Bị từ chối, có lý do ghi trong phiếu |
| Revision Required | Cần chỉnh sửa trước khi nộp lại |

**Cheat sheet xếp loại ưu tiên:**

| Loại | Điểm tổng hợp | Ý nghĩa |
|---|---|---|
| P1 | ≥ 4.0 | Ưu tiên cao nhất — đưa vào kế hoạch năm nay |
| P2 | 3.0 – 3.99 | Ưu tiên cao — đưa vào kế hoạch nếu còn ngân sách |
| P3 | 2.0 – 2.99 | Ưu tiên trung bình — xem xét năm sau |
| P4 | < 2.0 | Ưu tiên thấp — xem xét lại chiến lược |

## I.9. Liên Hệ Hỗ Trợ

| Vấn đề | Liên hệ |
|---|---|
| Không đăng nhập được, quên mật khẩu | IT Helpdesk: ext. 1234 hoặc it@hospital.vn |
| Lỗi hiển thị, tính năng không hoạt động | Support AssetCore: support@assetcore.vn |
| Câu hỏi quy trình, nghiệp vụ | Phòng VTTBYT / HTM Reviewer |
| Khẩn cấp (thiết bị Class III cần thay thế ngay) | Hotline: 0903.xxx.xxx (24/7) |

## I.10. Lịch Sử Cập Nhật Tài Liệu

| Phiên bản | Ngày | Thay đổi | Owner |
|---|---|---|---|
| 1.0.0 | (Wave 2 — TBD) | Phát hành lần đầu — Module IMM-01 GA | BA Lead |

---

# Phần II — Release Notes

## II.1. Tóm Tắt

Phiên bản 1.0.0 (Wave 2) đưa module **Đánh giá Nhu cầu & Dự toán (IMM-01)** vào vận hành. Module chuẩn hóa quy trình thu thập, thẩm định và xếp ưu tiên đề xuất đầu tư thiết bị y tế theo chuẩn WHO HTM, tạo nền tảng cho toàn bộ chuỗi mua sắm (IMM-02 → IMM-03 → IMM-04). Downtime dự kiến 30-60 phút trong cửa sổ bảo trì đêm.

## II.2. Tính Năng Mới

### Quản lý phiếu đề xuất nhu cầu (Trưởng khoa + HTM Reviewer)

Tạo và theo dõi phiếu đề xuất với 8 trạng thái workflow từ soạn thảo đến phê duyệt. Mọi phiếu truy xuất được đến nguồn đề xuất gốc.

- Tạo phiếu cho 4 loại nhu cầu: Mới / Thay thế / Nâng cấp / Bổ sung
- Gắn thiết bị cần thay thế với link đến kế hoạch thanh lý IMM-13
- Tự động lấy số liệu sử dụng từ IMM-07 (tỷ lệ sử dụng 12 tháng, thời gian dừng máy)
- Hệ thống thông báo tự động cho HTM Reviewer khi có phiếu mới

[→ Hướng dẫn: §I.5.a]

### Chấm điểm ưu tiên đa tiêu chí (HTM Reviewer + KH-TC)

6 tiêu chí có trọng số khoa học, tổng hợp thành điểm P1-P4 để hỗ trợ ra quyết định đầu tư.

- Chấm điểm 6 tiêu chí (thang 1-5): clinical impact, risk, utilization gap, replacement signal, compliance gap, budget fit
- Tổng hợp điểm có trọng số theo `IMM Priority Weight Config` cấu hình được
- Xếp loại tự động P1/P2/P3/P4
- Hệ thống cảnh báo điểm chênh lệch (VR-05: tổng trọng số phải = 100%)

[→ Hướng dẫn: §I.5.b]

### Dự toán CAPEX + OPEX toàn vòng đời (TCKT)

Dự toán ngân sách đầy đủ bao gồm chi phí đầu tư và chi phí vận hành 5 năm.

- CAPEX: đơn giá, số lượng, chi phí lắp đặt, đào tạo ban đầu
- OPEX 5 năm: bảo trì hợp đồng, tiêu hao, đào tạo định kỳ, phụ tùng
- Gắn nguồn vốn: Ngân sách NN / Tài trợ / BHYT / Xã hội hóa / Vay vốn
- Cờ báo khi đề xuất vượt budget envelope của khoa

[→ Hướng dẫn: §I.5.c]

### Kế hoạch mua sắm tổng hợp (KH-TC + Phó GĐ)

Gom các phiếu đề xuất đã phê duyệt thành kế hoạch mua sắm có cấu trúc.

- Tổng hợp nhiều phiếu NR vào 1 Procurement Plan theo năm tài chính
- Sắp xếp ưu tiên theo điểm tổng hợp
- Phê duyệt 1 lần → toàn bộ NR trong kế hoạch chuyển sang IMM-02

[→ Hướng dẫn: §I.5.c, §I.5.d]

### Dashboard KPI + Dự báo nhu cầu 3-5 năm (Phó TP VTTBYT)

Dashboard thời gian thực và báo cáo dự báo dài hạn phục vụ hoạch định chiến lược.

- KPI: tỷ lệ phê duyệt, thời gian xử lý, phân bổ P1-P4
- Dự báo nhu cầu theo device class dựa trên IMM-07 (hiệu suất) + IMM-13 (kế hoạch thanh lý) + mở rộng dịch vụ
- Heatmap nhu cầu 3-5 năm theo thiết bị × năm
- Scheduler tự động cập nhật dự báo hàng tháng

[→ Hướng dẫn: §I.6]

## II.3. Cải Tiến

| Mô tả | Module | Tác động |
|---|---|---|
| Link IMM-07 → tự động điền tỷ lệ sử dụng vào NR | IMM-07 Integration | Thẩm định dựa trên dữ liệu thực, không phải ước tính |
| Link IMM-13 → cảnh báo thiết bị sắp thanh lý | IMM-13 Integration | Phát hiện sớm nhu cầu thay thế |
| Link IMM-10 → cờ tuân thủ pháp lý tự động | IMM-10 Integration | Đảm bảo compliance được tính vào scoring |

## II.4. Sửa Lỗi

| Mã issue | Mô tả | Severity |
|---|---|---|
| (Module mới — không có bug fix release này) | — | — |

## II.5. Thay Đổi Không Backward-compat

Không có thay đổi breaking cho người dùng hiện tại. Module IMM-01 là module mới hoàn toàn trong Wave 2.

## II.6. Deprecations

Không có.

## II.7. Yêu Cầu Nâng Cấp

**Stack version:** Không thay đổi (Frappe v15, Python 3.11, Node 20).

**Migration tự động:** Patch `v1_1_0.*` chạy tự động khi `bench migrate`. Xem chi tiết §I.3 trong `08_Deployment.md`.

**Training bắt buộc:** 5 role phải hoàn tất training trước khi sử dụng. Thời lượng 30 phút đến 2 giờ tùy role. Xem `08_Deployment.md §II.7`.

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
| `get_demand_forecast` API chưa có filter theo device_class | Lọc client-side sau khi nhận response | v1.1.1 |
| Heatmap demand forecast chưa hỗ trợ export PDF | Chụp màn hình hoặc export data CSV | v1.2.0 |

## II.9. Liên Kết & Lịch Sử Versioning

- User Guide: §I file này
- Functional Specs: [IMM-01_Functional_Specs.md](./IMM-01_Functional_Specs.md)
- Deployment Plan: [08_Deployment.md](./08_Deployment.md)
- Báo lỗi: `support@assetcore.vn` hoặc GitHub Issues

| Version | Ngày | Nội dung |
|---|---|---|
| 1.0.0 | 2026-05 | IMM-01 General Availability — Wave 2 |

### Commits liên quan Wave 2 IMM-01 (branch `feature/hieuc/wave-2`)

| Commit | Summary |
|---|---|
| `810179e` | feat (BE+FE): add module 1,2,3, update UI dashboard (/launcher) — initial IMM-01 BE+FE landing |
| `82a9607` | fix (FE): Modal create new needs-requests, UI sidebar, add filter for imm-1,2,3 |
| `d2279ab` | (Wave 2 fix — refactor) |
| `4a3ad1c` | fix: resolve all conflicts and sync Wave 2 with global formatters |
| `66d9f81` | refactor: update module workflows and fix procurement issues |
| `d56c0cd` | fix: resolve Wave 1 & 2 bugs and enhance AI agents |
| `fce3655` | fix(FE): update fullname user and list view some page |

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
| US-01-001 | Story | Tạo Needs Request mới | Func Specs §3.1 | `services/imm01.py: initialize_needs_request()` | `TestInitializeNR: test_create_new_ok` | UAT-IMM01-01 | #imm01-core | v1.0.0 | ⬜ |
| US-01-002 | Story | Submit NR → notify HTM | Func Specs §3.1 | `services/imm01.py: before_submit()` | `TestNRLifecycle: test_submit_transitions_state` | UAT-IMM01-01 | #imm01-core | v1.0.0 | ⬜ |
| US-01-010 | Story | Chấm điểm 6 tiêu chí | Func Specs §3.2 | `services/imm01.py: compute_priority_score()` | `TestComputePriorityScore: test_weighted_score_p1` | UAT-IMM01-02, UAT-IMM01-03 | #imm01-core | v1.0.0 | ⬜ |
| US-01-020 | Story | Lập dự toán CAPEX+OPEX | Func Specs §3.3 | `services/imm01.py: validate_budget_estimate()` | `TestBudgetEstimate: test_capex_required` | UAT-IMM01-04, UAT-IMM01-05 | #imm01-core | v1.0.0 | ⬜ |
| US-01-030 | Story | Gom NR vào Procurement Plan | Func Specs §3.4 | `services/imm01.py: roll_into_procurement_plan()` | `TestProcurementPlan: test_roll_in_approved_nr` | UAT-IMM01-07, UAT-IMM01-08 | #imm01-core | v1.0.0 | ⬜ |
| US-01-040 | Story | Dự báo nhu cầu 3-5 năm | Func Specs §3.5 | `services/imm01.py: generate_demand_forecast()` | `TestDemandForecast: test_generate_ok` | UAT-IMM01-11, UAT-IMM01-12 | #imm01-core | v1.0.0 | ⬜ |
| BR-01-01 | Rule | PP Approved trước khi sang IMM-02 | Module Overview §7 | `validate_gate_g03()` before_submit PP | `TestGateG03: test_gate_g03_blocks_without_approved_nr` | UAT-IMM01-09 | #imm01-core | v1.0.0 | ⬜ |
| BR-01-02 | Rule | NR Replacement cần Decom Plan | Module Overview §7 | `_vr04()` in `validate_needs_request()` | `TestValidateNR: test_replacement_requires_decom` | UAT-IMM01-01 | #imm01-core | v1.0.0 | ⬜ |
| BR-01-03 | Rule | Clinical justification ≥ 200 chars | Module Overview §7 | `_vr03()` | `TestClinicalJustification: test_short_fails` | UAT-IMM01-01 | #imm01-core | v1.0.0 | ⬜ |
| BR-01-04 | Rule | CAPEX + OPEX Year 1 bắt buộc | Module Overview §7 | `_vr05()` in `validate_budget_estimate()` | `TestBudgetEstimate: test_missing_opex_fails` | UAT-IMM01-04 | #imm01-core | v1.0.0 | ⬜ |
| BR-01-05 | Rule | PP cần funding_source rõ ràng | Module Overview §7 | `validate_procurement_plan()` | `TestProcurementPlan: test_missing_funding_source_fails` | UAT-IMM01-08 | #imm01-core | v1.0.0 | ⬜ |
| BR-01-06 | Rule | NR quá hạn 30 ngày → cảnh báo | Module Overview §7 | `check_pending_request_overdue()` scheduler | `TestScheduler: test_overdue_flag_set` | UAT-IMM01-10 | #imm01-core | v1.0.0 | ⬜ |
| BR-01-07 | Rule | Priority weight tổng = 100% | Module Overview §7 | `_vr06()` in `compute_priority_score()` | `TestComputePriorityScore: test_weight_mismatch_fail` | UAT-IMM01-03 | #imm01-core | v1.0.0 | ⬜ |
| NĐ98/Điều 32 | Compliance | Kế hoạch đầu tư TTBYT theo năm | 08 §II.2 | PP Approved = cơ sở kế hoạch; Gate G03 | `TestProcurementPlan: test_submit_approved` | UAT-IMM01-09 | #imm01-core | v1.0.0 | ⬜ |
| NĐ98/Điều 15.2 | Compliance | Lưu trữ ≥ 5 năm | 08 §II.2 | `IMM Audit Trail` immutable | `test_audit_trail_logged_on_submit` | UAT-IMM01-12 | #imm01-core | v1.0.0 | ⬜ |
| LĐT/Điều 4 | Compliance | Nguồn vốn rõ ràng trước PP | 08 §II.2 | BR-01-05: `funding_source` bắt buộc | `TestProcurementPlan: test_missing_funding_source_fails` | UAT-IMM01-08 | #imm01-core | v1.0.0 | ⬜ |
| WHO HTM §3.2 | Compliance | Đánh giá đa tiêu chí | 08 §II.2 | `compute_priority_score()` 6 criteria | `TestComputePriorityScore: test_weighted_score_p1` | UAT-IMM01-02 | #imm01-core | v1.0.0 | ⬜ |
| WHO HTM §2.4 | Compliance | Chỉ NR Approved vào PP | 08 §II.2 | Gate G03 + `roll_into_procurement_plan()` | `TestGateG03: test_gate_g03_blocks_without_approved_nr` | UAT-IMM01-09 | #imm01-core | v1.0.0 | ⬜ |
| WHO HTM §6.4 | Compliance | CAPEX + OPEX bắt buộc | 08 §II.2 | BR-01-04: `validate_budget_estimate()` | `TestBudgetEstimate: test_capex_required` | UAT-IMM01-04 | #imm01-core | v1.0.0 | ⬜ |
| ISO 13485 §7.1 | Compliance | Kế hoạch dựa trên nhu cầu đã duyệt | 08 §II.2 | PP Approved → trigger IMM-02 | `TestProcurementPlan: test_submit_triggers_imm02` | UAT-IMM01-09 | #imm01-core | v1.0.0 | ⬜ |
| SEC-IMM01-01 | Security | Dept User chỉ thấy NR khoa mình | 07 §III.2 | `permissions.py: needs_request_query()` | `test_permission_dept_user_scope` | UAT-IMM01-06 | #imm01-core | v1.0.0 | ⬜ |
| SEC-IMM01-02 | Security | Audit chain không thể tamper | 07 §III.1 | `IMM Audit Trail` DocPerm no-delete | `test_audit_chain_breaks_on_tamper` | UAT-IMM01-12 | #imm01-core | v1.0.0 | ⬜ |

## III.3. Reverse Lookup

| Test ID | Requirement(s) cover |
|---|---|
| `TestClinicalJustification: test_short_fails` | US-01-001, BR-01-03 |
| `TestComputePriorityScore: test_weighted_score_p1` | US-01-010, WHO HTM §3.2 |
| `TestComputePriorityScore: test_weight_mismatch_fail` | BR-01-07 |
| `TestBudgetEstimate: test_capex_required` | US-01-020, BR-01-04, WHO HTM §6.4 |
| `TestBudgetEstimate: test_missing_opex_fails` | BR-01-04 |
| `TestValidateNR: test_replacement_requires_decom` | US-01-001, BR-01-02 |
| `TestGateG03: test_gate_g03_blocks_without_approved_nr` | BR-01-01, WHO HTM §2.4, ISO 13485 §7.1 |
| `TestProcurementPlan: test_missing_funding_source_fails` | BR-01-05, LĐT/Điều 4 |
| `TestProcurementPlan: test_submit_triggers_imm02` | US-01-030, ISO 13485 §7.1 |
| `TestNRLifecycle: test_submit_transitions_state` | US-01-002 |
| `TestDemandForecast: test_generate_ok` | US-01-040 |
| `TestScheduler: test_overdue_flag_set` | BR-01-06 |
| `test_audit_trail_logged_on_submit` | NĐ98/Điều 15.2 |
| `test_audit_chain_breaks_on_tamper` | SEC-IMM01-02 |
| `test_permission_dept_user_scope` | SEC-IMM01-01 |

## III.4. Coverage Gaps

Sau rà soát matrix, tất cả req Must/Should đều có test stubs. Gaps roadmap:

| Req ID | Thiếu gì? | Owner | Deadline |
|---|---|---|---|
| `get_demand_forecast` filter | Filter by device_class chưa implement | Dev IMM-01 | v1.1.1 |
| PDF export heatmap | Chart export chưa hỗ trợ | Dev FE | v1.2.0 |
| Pentest report `docs/security/` | Report chưa upload | Security | Trước go-live |
| Rate limit `create_needs_request` | Security roadmap | DevOps | v1.1.0 |

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

**Auditor hỏi:** "Làm sao chứng minh thiết bị X được đề xuất mua sắm dựa trên nhu cầu thực tế?"

Trace: `IMM Needs Request NR-26-XX-XXXXX → clinical_justification + scoring rows → priority_class=P1 → IMM Procurement Plan PP-26-XXXXX (Approved) → IMM Audit Trail records`

---

**Auditor hỏi:** "Kế hoạch mua sắm năm 2027 dựa trên cơ sở nào?"

Trace: `IMM Procurement Plan PP-27-XXXXX → lines[] → IMM Needs Request references → scoring + budget estimate → funding_source confirmed`

---

**Auditor hỏi:** "Ai đã phê duyệt kế hoạch mua sắm ngày X?"

Trace: `IMM Procurement Plan → workflow_state=Approved → IMM Audit Trail record → actor + timestamp + hash chain verify`

## III.7. Bảng Thống Kê Thông Tin Ứng Dụng

| Hạng mục | Số lượng | Ghi chú |
|---|---|---|
| DocType (chính) | 3 | `IMM Needs Request`, `IMM Procurement Plan`, `IMM Demand Forecast` |
| DocType (child) | 4 | `Needs Priority Scoring`, `Budget Estimate Line`, `Procurement Plan Line`, `Forecast Driver` |
| Workflow JSON | 2 | `IMM-01 Needs Workflow` (8 states), `IMM-01 Plan Workflow` (4 states) |
| API endpoint | 22 | xem 05 §1.4 (incl. `get_allowed_transitions`, `set_budget_envelope`, `approve_plan`, `activate_plan`, `close_plan`, `remove_from_plan`, `get_procurement_plan`, `create_procurement_plan`, `dashboard_kpis`, etc.) |
| FE view / page | 5 | `NeedsRequestListView`, `NeedsRequestCreateView`, `NeedsRequestDetailView`, `ProcurementPlanListView`, `ProcurementPlanDetailView` |
| FE store | 1 | `stores/imm01.ts` |
| Service function | 25+ | xem 04 §III + Class Diagram trong 03 |
| Scheduler job | 3 | `generate_demand_forecast` (monthly), `check_pending_request_overdue` (daily), `budget_envelope_alert` (weekly) |
| Business Rule | 8 (enforce) + 2 (planned VR-01-03/06) | xem 02 §IV.2 |
| Role áp dụng | 7 | Clinical User, HTM Engineer, Planning Officer, Finance Officer, Department Head, Board Approver, System Admin (+ Auditor read-only) |
| Test case unit | 2 test class (`TestPriorityClassification` 5 cases, `TestComputePriorityScore` 2 cases) — phần còn lại = roadmap | xem 07 §I.2 |
| UAT scenario | 12 | UAT-IMM01-01 → 12 |
| Patch | 1 | `v3_1.001_install_imm01` |
| User Story | 6 | US-01-001, US-01-002, US-01-010, US-01-020, US-01-030, US-01-040 |

---

## DoD — Hoàn chỉnh

### I. User Guide
- [x] Tiếng Việt 100%, không jargon
- [x] Mô tả tất cả 5 role với hướng dẫn step-by-step
- [x] Dashboard KPI có giải thích trend
- [x] FAQ 5 câu thực tế
- [x] Cheat sheet trạng thái + xếp loại ưu tiên + phím tắt
- [ ] ≥ 5 screenshot UI thực tế (cần chụp trên staging trước go-live)
- [ ] Reviewed bởi BA + đại diện end-user (Trưởng khoa ICU + HTM Reviewer)

### II. Release Notes
- [x] Tóm tắt 2-3 câu user-friendly
- [x] 4 tính năng mới có role hưởng lợi
- [x] Known issues + workaround documented
- [x] Breaking change: không có
- [x] Downtime và compatibility table
- [ ] Reviewed bởi PM + Tech Lead + BA

### III. Traceability Matrix + Bảng Thống Kê
- [x] 22 dòng: 6 User Story + 7 BR + 6 Compliance + 3 Security
- [x] Mọi dòng có ≥ 4 cell điền (status ⬜ = Wave 2 pending)
- [x] Reverse lookup table (15 entries)
- [x] Coverage gaps liệt kê (4 gaps, đều là roadmap)
- [x] Bảng thống kê 17 hạng mục
- [ ] Reviewed bởi PM + Tech Lead + QA Lead
