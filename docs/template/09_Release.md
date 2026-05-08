# 09 — Phát hành (Release: User Guide + Release Notes + Traceability)

| Mục | Giá trị |
|---|---|
| Module | IMM-`<XX>` |
| Phạm vi | Per-module |
| Owner | PM + BA + Tech Writer |
| Liên kết | tất cả file 02-08 trong template |

> **Mục đích**: Tài liệu phát hành ra khách hàng — hướng dẫn end-user (tiếng Việt), release notes thay đổi, traceability matrix audit-ready. R3 chốt khi release.

---

# Phần I — User Guide (Hướng dẫn sử dụng)

> **Ngôn ngữ**: Tiếng Việt 100% (cứng). Ngôn ngữ thường, không jargon, có screenshot.

## I.1. Giới thiệu
**Viết gì**: 3 mục con —
- Module dùng để làm gì (2-3 đoạn ngôn ngữ thường)
- Trước khi bắt đầu — bạn cần gì (account, browser, màn hình, mạng)
- Đăng nhập (3 step + screenshot)

## I.2. Nhận biết bạn đang ở đâu
**Viết gì**: Hub / Sidebar / Topbar — annotation 1-4 trên screenshot. Module marker chấm màu.

## I.3. Các vai trò
**Viết gì**: Bảng `Vai trò · Bạn làm gì?` — 1-2 dòng mỗi role.

## I.4. Quy trình chính
**Viết gì**: ASCII diagram dòng chảy chuẩn (① → ② → ③ → ...). Nối tới các section §I.5+ chi tiết.

## I.5. Thao tác per role
**Viết gì**: Mỗi role có 1 sub-section. Cấu trúc:
- Khi nào làm?
- Các bước (numbered, ngôn ngữ thường, mỗi step 1-2 dòng)
- Screenshot tham khảo
- Mẹo / cảnh báo (nếu có)

Cover tối thiểu: KTV tạo + chẩn đoán + đóng, Sup phân công + duyệt, Approver duyệt chi phí cao, Auditor verify chain.

## I.6. Bảng điều khiển (Dashboard)
**Viết gì**: Mô tả từng KPI + ý nghĩa trend (mũi tên ↑↓). Screenshot.

## I.7. FAQ
**Viết gì**: 5-8 câu hỏi thực tế từ end-user. Cover edge case (SLA hết hạn, tạo nhầm WO, vendor không account, không thấy nút, dashboard sai số liệu, concurrent error).

## I.8. Phím tắt & Mã trạng thái
**Viết gì**: 2 bảng — phím tắt (⌘K, Esc, ⌘S, Tab) + mã trạng thái workflow (cheat sheet).

## I.9. Liên hệ hỗ trợ
**Viết gì**: Bảng `Vấn đề · Liên hệ`. Đăng nhập / lỗi PM / quy trình / role / khẩn cấp.

## I.10. Lịch sử cập nhật tài liệu
**Viết gì**: Bảng `Phiên bản · Ngày · Thay đổi · Owner`.

---

# Phần II — Release Notes

> **Audience**: End-user, Admin, đối tác tích hợp. Ngôn ngữ end-user, KHÔNG copy commit log.

## II.1. Tóm tắt
**Viết gì**: 2-3 câu hấp dẫn nhưng đúng. Highlight tính năng lớn nhất + downtime.

## II.2. Tính năng mới
**Viết gì**: Mỗi tính năng 1 sub-section. Format: tên + role hưởng lợi + 2-3 câu mô tả + 3-5 bullet điểm chính + link User Guide section + screenshot.

## II.3. Cải tiến (Improvements)
**Viết gì**: Bảng `Mô tả · Module · Tác động`.

## II.4. Sửa lỗi (Bug fixes)
**Viết gì**: Bảng `Mã issue · Mô tả · Severity (Critical/Major/Minor)`.

## II.5. Thay đổi không backward-compat (Breaking)
**Viết gì**: Mỗi breaking 1 sub-section: Trước · Sau · Tác động · Migration (auto/manual).

## II.6. Deprecations
**Viết gì**: Bảng `Item · Lý do · Hỗ trợ đến · Thay thế`.

## II.7. Yêu cầu nâng cấp
**Viết gì**: 4 mục con — Stack version, Migration auto, Migration thủ công admin, Training (audience + thời lượng + WI).

## II.8. Downtime / Compatibility / Known issues
**Viết gì**: 3 mục —
- Downtime: bao lâu, khung giờ, lý do
- Khả năng tương thích: bảng browser, mobile, API client cũ
- Known issues: bảng `Vấn đề · Workaround · Fix dự kiến`

## II.9. Liên kết & Lịch sử versioning
**Viết gì**:
- Liên kết: User Guide, Functional Specs, Deployment Plan, báo lỗi, demo
- Lịch sử: bảng 5 release gần nhất

---

# Phần III — Traceability Matrix

> **Mục đích**: Một bảng nối **Requirement → Design → Code → Test → Release**. Auditor hỏi → đáp 1 dòng.

## III.1. Cách dùng
**Viết gì**: 3 quy tắc — (a) Mỗi User Story (02 §IV) / Business Rule / Compliance req (08 §II) có 1 dòng, (b) Cell phải trỏ tới artefact concrete (commit/PR/file/test ID/version), (c) Cập nhật xuyên suốt lifecycle, chốt khi release.

## III.2. Matrix chính
**Viết gì**: Bảng cột:
`Req ID · Loại (Story/Rule/Edge case/Compliance) · Mô tả ngắn · Doc ref · Design / Code · Test ID · UAT ID · PR · Released in · Status`

Status legend: ⬜ Not started · 🟡 In progress · 🟠 Blocked · ✅ Done · ❌ Cancelled · 🔄 Reopened

## III.3. Reverse lookup
**Viết gì**: Bảng `Test ID · Requirement(s) cover`. Dùng khi review test PR ("Test này test cái gì?").

## III.4. Coverage gaps
**Viết gì**: Sau khi điền, scan dòng có ⬜/🟠/cell trống. Bảng `Req ID · Thiếu gì? · Owner · Deadline`.
**Mẹo**: Trước go-live, mọi req Must/Should phải có hàng đủ.

## III.5. Cập nhật quy ước
**Viết gì**: Bảng `Khi · Ai update · Cell nào`. BA thêm row khi 02 có req mới; Tech Lead điền Code; Dev điền PR; QA điền Test ID; PM điền Released-in.

## III.6. Audit-readiness — quick links
**Viết gì**: 2-3 ví dụ câu hỏi auditor + cách trace ngược qua matrix.

## III.7. Bảng thống kê thông tin ứng dụng (Application statistics)
**Viết gì**: Bảng `Hạng mục · Số lượng · Ghi chú` để định lượng kết quả module. Cover (chọn các hạng mục áp dụng):
- Số DocType (master + child)
- Số Workflow JSON
- Số API endpoint
- Số FE view / page
- Số FE component (common + module-specific)
- Số test case (unit + integration + E2E + UAT)
- Coverage % (BE service / DocType / API / FE)
- LOC (lines of code) per BE / FE
- Số role + role profile
- Số ADR đã viết
- Số sprint hoàn thành
- Velocity trung bình

**Mẹo**: Bảng dùng để pitch / báo cáo / điền vào file 11 Final Report Chương 4.3.2 (Kết quả đạt được).

---

## DoD — File 09 hoàn chỉnh

### I. User Guide
- [ ] Tiếng Việt 100%, không jargon
- [ ] ≥ 5 screenshot UI thực tế
- [ ] Cover mọi role (≥ 3) với hướng dẫn step-by-step
- [ ] FAQ ≥ 5 câu thực tế
- [ ] Phím tắt + cheat sheet trạng thái
- [ ] Reviewed bởi BA + đại diện end-user

### II. Release Notes
- [ ] Tóm tắt 2-3 câu user-friendly
- [ ] Mỗi tính năng có role hưởng lợi
- [ ] Bug fix trace tới issue tracker
- [ ] Breaking change có migration path
- [ ] Yêu cầu nâng cấp + migration thủ công rõ
- [ ] Reviewed bởi PM + Tech Lead + BA

### III. Traceability Matrix + Bảng thống kê
- [ ] Mọi User Story / Business Rule / Compliance req có dòng
- [ ] Mỗi dòng ✅ có ≥ 4 cell điền: Doc ref, Code, Test ID, UAT ID, PR
- [ ] Reverse lookup table cập nhật
- [ ] Coverage gaps liệt kê — không còn ⬜ trước go-live
- [ ] **Bảng thống kê thông tin ứng dụng** đầy đủ (≥ 8 hạng mục: DocType, API, view, test case, coverage, LOC, role, sprint)
- [ ] Reviewed bởi PM + Tech Lead + QA Lead
