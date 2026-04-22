# Kịch bản Conference Room Pilot (CRP) — IMM-04
# Lắp đặt, Định danh và Kiểm tra Ban đầu Thiết bị Y tế
# Hệ thống: AssetCore / IMMIS v1.0

---

**Mã tài liệu:** ASSETCORE-IMM04-CRP-v1.0
**Ngày tổ chức dự kiến:** ____/____/2026
**Địa điểm:** Phòng họp __________________ | Thời lượng: **4 giờ**
**Hình thức:** Trình chiếu màn hình thực tế trên Sandbox + Thảo luận nhóm

---

## PHẦN 1 — MỤC TIÊU BUỔI PILOT

### 1.1 Mục tiêu chính
Xác nhận với các bên liên quan rằng hệ thống AssetCore đã cấu hình đúng theo quy trình thực tế của bệnh viện — **trước khi tiến hành UAT chính thức**. Phát hiện sớm các điểm chưa phù hợp, giảm thiểu rủi ro thất bại trong UAT.

### 1.2 Câu hỏi trung tâm cần trả lời sau CRP

| # | Câu hỏi | Đáp án mong đợi |
|---|---|---|
| Q1 | Hệ thống có hỗ trợ đúng quy trình tiếp nhận thiết bị của viện không? | Có — hoặc Có với điều chỉnh nhỏ |
| Q2 | Các gate kiểm soát có đặt đúng chỗ và đủ mạnh không? | Có |
| Q3 | Người dùng các phòng ban có thao tác được không? | Có — cần training tối thiểu |
| Q4 | Có điểm nào cần điều chỉnh cấp hình trước UAT không? | Liệt kê ra danh sách |

---

## PHẦN 2 — DANH SÁCH THÀNH PHẦN THAM GIA

| Vai trò | Đại diện | Phòng / Ban | Ghi chú |
|---|---|---|---|
| **Chủ trì CRP** | Project Manager | IT / AssetCore Team | Điều phối toàn bộ buổi |
| **Demo Lead** | Developer / Solution Architect | AssetCore Team | Thao tác trực tiếp trên sandbox |
| **Nghiệp vụ TBYT** | Trưởng phòng TBYT | Phòng Vật tư TBYT | Xác nhận đúng quy trình thực tế |
| **Kỹ thuật viên HTM** | KTV đại diện | Tổ Kỹ thuật TBYT | Test thao tác nhập liệu thực tế |
| **Trưởng Workshop** | Trưởng Kỹ sư | Workshop TBYT | Xác nhận quy trình kiểm tra điện |
| **PTP Khối 2** | Phó Trưởng Phòng | Phòng phụ trách Khối 2 | Xác nhận quy trình phê duyệt |
| **QA / QLCL** | Cán bộ QLCL | Phòng Hành chính QLCL | Xác nhận kiểm soát chất lượng |
| **Kế toán** | Kế toán trưởng TBYT | Phòng Tài chính | Xác nhận kết nối với tài sản kế toán |
| **IT Hỗ trợ** | IT Admin | Phòng CNTT | Hỗ trợ kỹ thuật trong buổi |

**Yêu cầu tối thiểu:** Ít nhất 5/9 vai trò có mặt, bắt buộc có Nghiệp vụ TBYT + PTP Khối 2.

---

## PHẦN 3 — AGENDA (Chương trình buổi CRP)

| Thời gian | Nội dung | Người thực hiện | Thời lượng |
|---|---|---|---|
| 08:30–08:45 | Khai mạc, giới thiệu mục tiêu CRP | PM | 15 phút |
| 08:45–09:00 | Thuyết minh tổng quan luồng IMM-04 (Slide) | Solution Architect | 15 phút |
| 09:00–09:45 | **Demo TC-01:** Luồng Xanh đầy đủ | Demo Lead + KTV HTM | 45 phút |
| 09:45–10:00 | Thảo luận TC-01 + Ghi nhận ý kiến | PM | 15 phút |
| 10:00–10:10 | *Giải lao* | — | 10 phút |
| 10:10–10:40 | **Demo TC-02+03:** Thiếu hồ sơ + Site Gate | Demo Lead | 30 phút |
| 10:40–11:15 | **Demo TC-04+05:** Inspection Fail → NC → Re-inspect → Release | Demo Lead | 35 phút |
| 11:15–11:30 | Thảo luận + Q&A tổng thể | PM + Tất cả | 15 phút |
| 11:30–11:50 | Điền Form Ghi nhận Issue (từng người) | Tất cả | 20 phút |
| 11:50–12:00 | Tổng hợp Issue, phân loại, kết luận Sign-off | PM + Architect | 10 phút |

---

## PHẦN 4 — SCRIPT DEMO CHI TIẾT

### DEMO 1: Luồng Xanh (TC-01) — 45 phút

**Dữ liệu dùng:** Máy thở Philips V60, PO-2026-0041, SN: VNT-PHL-20260001

| Bước | Màn hình | Thao tác Demo Lead | Điểm nhấn giải thích |
|---|---|---|---|
| D1.1 | Login | Đăng nhập bằng account `KTV HTM` | "KTV chỉ có quyền giới hạn — không thấy nút Approve" |
| D1.2 | Menu AssetCore | Vào **Tiếp nhận Thiết bị Mới** | "Đây là điểm khởi đầu duy nhất — không có con đường tắt nào" |
| D1.3 | Form Draft | Chọn PO-2026-0041 | "Hệ thống tự điền Nhà cung cấp và Model từ PO" |
| D1.4 | Tab Hồ sơ | Tick đủ CO, CQ. Upload file giả | "Mỗi hồ sơ bắt buộc phải đính kèm file — không tick suông" |
| D1.5 | Bấm Submit | Chuyển state → `Pending_Doc_Verify` | "Hệ thống đã ghi nhận thời gian bắt đầu vào SLA timer" |
| D1.6 | Site Check | Điền Checklist Mặt bằng — All Pass | "Cơ điện + KTS viện cùng ký vào bảng này" |
| D1.7 | Installing | Kỹ sư hãng log tiến độ | "Hệ thống tự ghi thời gian bắt đầu lắp — không back-date được" |
| D1.8 | Identification | Quét/gõ SN: `VNT-PHL-20260001` | "Nếu SN đã tồn tại → hệ thống báo lỗi ngay" |
| D1.9 | Baseline Test | Điền 5 chỉ tiêu — All Pass (màu xanh) | "Từng dòng tô màu xanh/đỏ theo kết quả" |
| D1.10 | Login VP Block2 | Đổi account sang PTP Khối 2 | "Chỉ Lãnh đạo Khối mới thấy nút phê duyệt cuối" |
| D1.11 | Submit Release | Bấm Submit → Thông báo Asset tạo | "🎉 Asset AST-2026-XXXXX xuất hiện trong danh sách Tài sản" |
| D1.12 | Mở Asset | Xem Asset vừa tạo → click `custom_comm_ref` | "Click vào link → nhảy về phiếu gốc → Trace-back đầy đủ" |

**Câu hỏi xác nhận sau Demo 1:**
- *(Hỏi KTV HTM):* Bước nhập hồ sơ trông có quen không? Có thiếu loại chứng từ nào viện thường dùng không?
- *(Hỏi PTP Khối 2):* Nút phê duyệt cuối có đủ thông tin để ra quyết định không?
- *(Hỏi Kế toán):* Khi Asset được tạo, thông tin gì còn thiếu để phòng Kế toán nhập Khấu hao?

---

### DEMO 2: Thiếu Hồ sơ (TC-02) — 15 phút

| Bước | Thao tác | Điểm nhấn |
|---|---|---|
| D2.1 | Tạo form mới, chỉ tick CO — bỏ trống CQ | — |
| D2.2 | Bấm Submit | "Hệ thống **chặn toàn bộ** — không cho qua dù KTV muốn" |
| D2.3 | Upload CQ → Submit lại | "Submit lần 2 → thành công → SLA timer bắt đầu" |

**Câu hỏi xác nhận:**
- *(Hỏi Phòng TBYT):* Ngoài CO và CQ, viện còn yêu cầu loại giấy tờ nào khác không thể thiếu?

---

### DEMO 3: Inspection Fail → NC → Release (TC-04 & TC-05) — 35 phút

| Bước | Thao tác | Điểm nhấn |
|---|---|---|
| D3.1 | Điền Baseline — Dòng rò 4.8mA, chọn Fail, để trống Ghi chú | "Hệ thống yêu cầu ghi chú nguyên nhân — không bỏ trống được" |
| D3.2 | Điền Ghi chú → Submit | "State nhảy về Re_Inspection — không Release được" |
| D3.3 | Bấm "Báo cáo DOA" | "NC phiếu được tạo — sẽ theo dõi độc lập" |
| D3.4 | Thử bấm Release khi NC đang Open | "Hệ thống chặn VR-04 — không thể qua mặt" |
| D3.5 | Đóng NC (Fixed) → Đo lại 1.1mA Pass | "NC đóng + Baseline Pass → đèn xanh" |
| D3.6 | VP Block2 Release | "Asset tạo thành công dù có Re-inspection" |
| D3.7 | Mở NC đã đóng | "Lịch sử đầy đủ: Original fail + résolution — không bị xóa" |

**Câu hỏi xác nhận:**
- *(Hỏi Trưởng Workshop):* Các chỉ tiêu đo điện trong lưới Baseline có đủ, có đúng tên không? Viện đo thêm gì?
- *(Hỏi QA QLCL):* Phiếu NC có đủ thông tin để truy cứu trách nhiệm nhà thầu không?

---

## PHẦN 5 — TIÊU CHÍ ĐẠT / KHÔNG ĐẠT CRP

Buổi CRP được coi là **ĐẠT** khi tất cả tiêu chí bắt buộc (★) đều có xác nhận "Đồng ý":

| # | Tiêu chí | Bắt buộc? | Kết quả |
|---|---|---|---|
| CR-01 | Luồng từ Draft → Release → Asset chạy thông suốt | ★ | ☐ Đồng ý / ☐ Không |
| CR-02 | Gate VR-02 (thiếu C/Q) chặn đúng, không bypass được | ★ | ☐ Đồng ý / ☐ Không |
| CR-03 | Gate VR-04 (NC Open) chặn Release đúng | ★ | ☐ Đồng ý / ☐ Không |
| CR-04 | Asset được tạo tự động sau khi Release | ★ | ☐ Đồng ý / ☐ Không |
| CR-05 | Traceability: Click từ Asset → về phiếu gốc IMM-04 | ★ | ☐ Đồng ý / ☐ Không |
| CR-06 | Permission: KTV HTM không thấy nút Approve Release | ★ | ☐ Đồng ý / ☐ Không |
| CR-07 | Các loại hồ sơ trong Checklist phù hợp quy trình viện | ★ | ☐ Đồng ý / ☐ Không |
| CR-08 | Các chỉ tiêu đo điện Baseline phù hợp thực tế | ★ | ☐ Đồng ý / ☐ Không |
| CR-09 | Giao diện đủ rõ để người dùng không cần hỏi liên tục | — | ☐ Đồng ý / ☐ Không |
| CR-10 | Kế toán nhận được tín hiệu sau khi Release | — | ☐ Đồng ý / ☐ Không |

**Kết luận CRP:**
- ☐ **ĐẠT** — CR-01 đến CR-08 đều = Đồng ý → Tiến hành UAT
- ☐ **ĐẠT CÓ ĐIỀU KIỆN** — Có ≤ 2 tiêu chí ★ chưa đạt, có plan fix trong 3 ngày
- ☐ **KHÔNG ĐẠT** — Có ≥ 3 tiêu chí ★ chưa đạt → Cần điều chỉnh và CRP lại

---

## PHẦN 6 — BIỂU MẪU GHI NHẬN ISSUE

*Mỗi người tham gia điền 1 biểu mẫu riêng. Thu thập và tổng hợp trước khi kết thúc.*

---

**Người ghi:** _________________________ **Vai trò:** _________________

| Issue # | Mô tả vấn đề | Màn hình / Bước | Phân loại | Tác động | Đề xuất xử lý |
|---|---|---|---|---|---|
| 1 | | | ☐ Critical ☐ Major ☐ Minor ☐ Enhancement | | |
| 2 | | | ☐ Critical ☐ Major ☐ Minor ☐ Enhancement | | |
| 3 | | | ☐ Critical ☐ Major ☐ Minor ☐ Enhancement | | |
| 4 | | | ☐ Critical ☐ Major ☐ Minor ☐ Enhancement | | |
| 5 | | | ☐ Critical ☐ Major ☐ Minor ☐ Enhancement | | |

**Đánh giá tổng thể của bạn về hệ thống:**
☐ Sẵn sàng UAT ngay &nbsp;&nbsp; ☐ Cần điều chỉnh nhỏ trước UAT &nbsp;&nbsp; ☐ Cần làm lại đáng kể

**Ý kiến bổ sung:** _______________________________________________

---

## PHẦN 7 — PHÂN LOẠI ISSUE

| Mức | Ký hiệu | Định nghĩa | Tác động | Hành động bắt buộc |
|---|---|---|---|---|
| **Critical** | 🔴 | Luồng chính bị chặn hoàn toàn hoặc dữ liệu bị sai nghiêm trọng | Không demo/test được | Fix trong **24h** — Go-Live Blocker |
| **Major** | 🟠 | Chức năng quan trọng hoạt động sai nhưng có workaround; quy trình bị ảnh hưởng đáng kể | Ảnh hưởng UAT | Fix trong **3 ngày** — Trước UAT |
| **Minor** | 🟡 | Chức năng phụ sai nhỏ hoặc UX chưa tối ưu; workaround dễ dàng | Không chặn demo | Fix trong **Sprint tiếp theo** |
| **Enhancement** | 🔵 | Đề xuất cải tiến, không phải lỗi; hệ thống hoạt động đúng nhưng có thể tốt hơn | Không ảnh hưởng | Đưa vào **Backlog v1.1** |

### Ví dụ phân loại chuẩn

| Mô tả Issue | Phân loại đúng | Lý do |
|---|---|---|
| "Bấm Submit không ra Asset — hệ thống lỗi 500" | 🔴 Critical | Tắt luồng chính |
| "Field CQ thiếu trong Checklist hồ sơ của viện" | 🟠 Major | Sẽ block real UAT data |
| "Label tiếng Việt bị sai chính tả ở 1 chỗ" | 🟡 Minor | UX nhỏ, không ảnh hưởng |
| "Nên thêm filter theo tháng ở listview" | 🔵 Enhancement | Ý tưởng cải tiến |
| "Chưa có export Excel danh sách thiết bị" | 🔵 Enhancement | Ngoài scope v1.0 |

---

## PHẦN 8 — CHECKLIST SIGN-OFF NỘI BỘ

*Ký sau khi buổi CRP kết thúc và issue đã được tổng hợp.*

### 8A. Tổng hợp Issue

| Loại | Số lượng | Đã có plan fix? |
|---|---|---|
| 🔴 Critical | | ☐ Có ☐ Chưa |
| 🟠 Major | | ☐ Có ☐ Chưa |
| 🟡 Minor | | ☐ Có ☐ Chưa |
| 🔵 Enhancement | | Đưa vào backlog |

### 8B. Quyết định

☐ **Tiến hành UAT** — Không có Critical; Major có plan fix trước UAT

☐ **Điều chỉnh trước UAT** — Fix Critical/Major trong _____ ngày → schedule lại

☐ **CRP Lần 2** — Cần thiết kế lại đáng kể → họp lại sau Sprint ____

### 8C. Bảng Ký

| Vai trò | Họ tên | Chữ ký | Ngày |
|---|---|---|---|
| **Chủ trì CRP (PM)** | | | |
| **Đại diện Nghiệp vụ TBYT** | | | |
| **Trưởng Workshop** | | | |
| **PTP Khối 2** | | | |
| **QA / QLCL** | | | |
| **Kế toán** | | | |
| **Solution Architect** | | | |

---

*Tài liệu này được ban hành bởi Tổ Dự án AssetCore.*
*Lưu trữ tại: `docs/sprints/IMM-04_CRP_Script.md`*
