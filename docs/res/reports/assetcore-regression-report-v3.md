# AssetCore — Báo cáo Kiểm thử Hồi quy v3
**Ngày:** 26/05/2026 | **Phiên bản:** AssetCore v0.0.2 | **Môi trường:** localhost:3000  
**Mục tiêu:** Kiểm tra lại 20 lỗi từ report v2 — xác nhận đã sửa hay vẫn còn

---

## 📊 KẾT QUẢ TỔNG HỢP (SO SÁNH 3 PHIÊN)

| Bug ID | Mô tả ngắn | v1 | v2 | v3 (hôm nay) |
|--------|-----------|----|----|--------------|
| BUG-001 | Phê duyệt PP freeze | ❌ | 🚫 Không test được | 🚫 Không test được |
| BUG-002 | Q1-2099 trong MR | ❌ | ✅ FIXED | ✅ Confirmed fixed |
| BUG-003 | Sidebar "không thuộc module" | ❌ | ✅ FIXED | ✅ Confirmed fixed |
| BUG-004 | KHOA="—" TCO="0đ" trong PP | ❌ | 🚫 Superseded | 🚫 Superseded by BUG-019 |
| BUG-005 | Benchmark tab trống | ❌ | ✅ FIXED | ✅ Confirmed fixed |
| BUG-006 | Training 0 học viên, no actions | ❌ | ❌ | ❌ STILL PRESENT |
| BUG-007 | Calibration không có action buttons | ❌ | ❌ | ❌ STILL PRESENT |
| BUG-008 | PM schedules nút disabled | ❌ | ⚠️ Partial | ✅ FIXED (header btn works) |
| BUG-009 | QR code "Chưa sinh" | ❌ | ❌ | ❌ STILL PRESENT |
| BUG-010 | Mã Bộ Y tế trống | ❌ | ❌ | ❌ STILL PRESENT |
| BUG-011 | Competency thiếu điểm đánh giá | ❌ | ❌ | ❌ STILL PRESENT |
| BUG-012 | Calibration compliance 0% | ❌ | ❌ | ❌ STILL PRESENT |
| BUG-013 | PM 33.3% không rõ phạm vi | ❌ | ✅ FIXED | ✅ Confirmed fixed |
| BUG-014 | PM template dùng slug trong tên | ❌ | ❌ | ❌ STILL PRESENT |
| BUG-015 | /purchase-orders 404 | ❌ | ✅ FIXED | ✅ Confirmed fixed |
| BUG-016 | Skeleton loading commissioning | ❌ | ✅ FIXED | ✅ Confirmed fixed |
| BUG-017 | Scorecard luôn "—" trong MR | ❌ | ❌ | ❌ STILL PRESENT |
| BUG-018 | Hợp đồng dịch vụ 0 bản ghi | ❌ | ❌ | ❌ STILL PRESENT |
| BUG-019 | PP detail crash DocType Department | 🆕 (v2) | 🔴 CRITICAL | ❌ STILL PRESENT |
| BUG-020 | Supplier hiển thị ID thay vì tên | 🆕 (v2) | ❌ | ❌ STILL PRESENT |

---

## ✅ BUGS ĐÃ ĐƯỢC SỬA HOÀN TOÀN (7 bugs)

| Bug | Mô tả | Từ phiên |
|-----|-------|----------|
| BUG-002 | Q1-2099 → Q2-2026 đúng trong Soát xét quản lý | v2 |
| BUG-003 | Sidebar hydration lỗi khi navigate trực tiếp | v2 |
| BUG-005 | Tab Benchmark trống → nay render đúng | v2 |
| BUG-008 | Nút "+Thêm lịch PM" disabled → nay hoạt động | v2→v3 |
| BUG-013 | PM dashboard 33.3% không rõ phạm vi → có label tháng | v2 |
| BUG-015 | /purchase-orders 404 → redirect về /purchases | v2 |
| BUG-016 | Skeleton loading commissioning detail | v2 |

---

## ❌ BUGS VẪN CÒN TỒN TẠI (11 bugs active)

---

### 🔴 CRITICAL

#### BUG-019 — Kế hoạch mua sắm chi tiết crash
**URL:** `/procurement-plans/{id}` (tất cả ID)  
**Lỗi:** Banner đỏ: `Lỗi: ('DocType', 'Department')` — trang trắng hoàn toàn  
**Ảnh hưởng:** Toàn bộ IMM-00 detail bị mất. Không xem/sửa/duyệt được bất kỳ kế hoạch nào.  
**Nguyên nhân:** Regression — thay đổi schema hoặc API gần đây làm broken reference Department DocType trong ProcurementPlan model.  
**Trạng thái v3:** ❌ VẪN CÒN — Cần fix ngay.

---

### 🟠 HIGH

#### BUG-006 — Training session không có workflow
**URL:** `/imm06/sessions/TRN-2026-00008`  
**Mô tả:** Học viên = 0, không có nút thêm học viên, không có nút bắt đầu/kết thúc buổi học.  
**Nguyên nhân:** Chức năng enroll học viên và workflow buổi đào tạo chưa implement.  
**Trạng thái v3:** ❌ VẪN CÒN

#### BUG-007 — Calibration không có action buttons
**URL:** `/calibration/CAL-2026-00016`  
**Mô tả:** Trạng thái "Đã lên lịch", có hint "chuyển trạng thái qua nút bên dưới" nhưng chỉ có "Quay lại". Không thể bắt đầu/hoàn thành hiệu chuẩn.  
**Nguyên nhân:** Workflow action buttons chưa được render theo role/status.  
**Trạng thái v3:** ❌ VẪN CÒN

#### BUG-011 — Competency thiếu điểm đánh giá
**URL:** `/imm06/competencies/COMP-2026-00067`  
**Mô tả:** Điểm tổng cuối/lý thuyết/thực hành đều "—". Không có nút nhập điểm hay bắt đầu đánh giá.  
**Nguyên nhân:** Cascade từ BUG-006 — học viên chưa được đánh giá vì không có workflow đào tạo.  
**Trạng thái v3:** ❌ VẪN CÒN

---

### 🟡 MEDIUM

#### BUG-009 — QR code "Chưa sinh"
**URL:** `/commissioning/ACC-26-05-00005`  
**Mô tả:** Trường "Mã QR Nội bộ Bệnh viện" = "Chưa sinh" cho thiết bị đã được tiếp nhận.  
**Nguyên nhân:** Logic sinh QR tự động chưa được trigger khi hoàn thành tiếp nhận.  
**Trạng thái v3:** ❌ VẪN CÒN

#### BUG-010 — Mã Bộ Y tế trống
**URL:** `/commissioning/ACC-26-05-00005`  
**Mô tả:** Trường "Mã Bộ Y tế (Bộ Y tế)" bỏ trống, không có giao diện/công cụ để điền.  
**Nguyên nhân:** Thiếu UI input hoặc import tool để nhập mã đăng ký từ Bộ Y tế.  
**Trạng thái v3:** ❌ VẪN CÒN

#### BUG-012 — Calibration compliance 0%
**URL:** `/calibration/dashboard`  
**Mô tả:** Tỷ lệ tuân thủ 0%, 0/2 đúng hạn — không có phiếu nào hoàn thành.  
**Nguyên nhân:** Cascade từ BUG-007 — không thể hoàn thành phiếu vì thiếu action buttons.  
**Trạng thái v3:** ❌ VẪN CÒN

#### BUG-017 — Scorecard luôn "—" trong MR
**URL:** `/compliance/mr`  
**Mô tả:** Cột SCORECARD = "—" cho tất cả 43 bản ghi. Chức năng liên kết Scorecard → MR chưa hoạt động.  
**Nguyên nhân:** Logic ghi kết quả từ `/compliance/scorecard` vào trường Scorecard của MR chưa implement.  
**Trạng thái v3:** ❌ VẪN CÒN

#### BUG-020 — Supplier hiển thị ID thay vì tên
**URL:** `/purchases`  
**Mô tả:** 13/17 đơn hàng hiển thị "AC-SUP-2026-0025" thay vì tên công ty trong cột Nhà cung cấp.  
**Nguyên nhân:** Lỗi JOIN/lookup supplier_name trong list API — chỉ xảy ra với đơn hàng tạo sau 20/5/2026.  
**Trạng thái v3:** ❌ VẪN CÒN

---

### 🟢 LOW

#### BUG-014 — PM Template tên dùng slug
**URL:** `/pm/templates`  
**Mô tả:** Tên hiển thị: "Checklist PM Quý — Thiet-bi-Chan-doan-Hinh-anh" — có slug ASCII không dịch.  
**Nguyên nhân:** Tên template tạo bằng concatenate slug thay vì Vietnamese display name.  
**Trạng thái v3:** ❌ VẪN CÒN

#### BUG-018 — Hợp đồng dịch vụ 0 bản ghi
**URL:** `/service-contracts`  
**Mô tả:** 0 hợp đồng, trang trống. Module đã có UI (Xuất Excel, Import, Tạo mới) nhưng chưa có dữ liệu.  
**Nguyên nhân:** Chưa có dữ liệu seed/demo được nhập.  
**Trạng thái v3:** ❌ VẪN CÒN (data gap)

---

## 🚫 KHÔNG THỂ KIỂM TRA

#### BUG-001 — Phê duyệt gây freeze (bị chặn bởi BUG-019)
Cần fix BUG-019 trước thì mới có thể truy cập trang chi tiết PP để test nút Phê duyệt.

#### BUG-004 — KHOA="—" TCO="0đ" (bị chặn bởi BUG-019)
Cần fix BUG-019 trước.

---

## 🎯 BẢNG ƯU TIÊN SỬA LỖI (CẬP NHẬT v3)

### P1 🔴 Sửa ngay — Blocking
1. **BUG-019** — PP crash `DocType Department` — Toàn bộ IMM-00 detail mất chức năng  
   → Sau khi fix: retest BUG-001 và BUG-004

### P2 🟠 Sprint này — High Impact  
2. **BUG-006** — Training không thể enroll học viên & không có workflow  
3. **BUG-007** — Calibration không có action buttons workflow  
4. **BUG-011** — Năng lực nhân viên không có điểm đánh giá *(cascade từ BUG-006)*

### P3 🟡 Sprint tiếp theo — Medium Impact  
5. **BUG-020** — Supplier hiển thị ID thay tên trong /purchases  
6. **BUG-009** — QR code không tự sinh khi tiếp nhận thiết bị  
7. **BUG-010** — Mã Bộ Y tế thiếu UI nhập liệu  
8. **BUG-017** — Scorecard không liên kết với Management Review  
9. **BUG-012** — 0% calibration compliance *(cascade từ BUG-007)*

### P4 🟢 Backlog — Low Impact  
10. **BUG-014** — Template PM tên dùng slug  
11. **BUG-018** — Hợp đồng dịch vụ thiếu data demo  

---

## 📈 TIẾN ĐỘ SỬA LỖI QUA CÁC PHIÊN

| Phiên | Tổng bugs | Đã sửa | Còn lại | Mới phát hiện |
|-------|-----------|--------|---------|---------------|
| v1 (report gốc) | 18 | 0 | 18 | — |
| v2 (regression 1) | 20 | 6 | 12 | +2 mới |
| **v3 (hôm nay)** | **20** | **7** | **11** | **0 mới** |

**Tỷ lệ fix:** 7/20 = **35%** bugs đã giải quyết  
**Bugs active cần fix:** **11 bugs** (1 Critical, 3 High, 5 Medium, 2 Low)  
**Không có lỗi mới phát sinh trong phiên v3** ✅

---

*Báo cáo tạo tự động — AssetCore Regression Test v3 — 26/05/2026*
