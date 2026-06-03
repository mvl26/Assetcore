# Báo cáo Kiểm thử AssetCore v0.0.2 — Tổng kết Lỗi & Vấn đề
**Dự án:** AssetCore — Phần mềm quản lý vòng đời thiết bị y tế  
**Ứng dụng:** Bệnh Viện Nhi Đồng 1  
**Phiên bản:** v0.0.2  
**Ngày kiểm thử:** 26/05/2026  
**Người kiểm thử:** Claude (Automated Browser Testing)  
**Môi trường:** http://localhost:3000  

---

## Tóm tắt

| Mức độ | Số lượng |
|---|---|
| 🔴 Critical (Nghiêm trọng) | 3 |
| 🟠 High (Cao) | 5 |
| 🟡 Medium (Trung bình) | 6 |
| 🔵 Low (Thấp) | 4 |
| ⚠️ Under Development | 4 IMM |
| **Tổng lỗi** | **18** |

---

## 🔴 Critical — Nghiêm trọng

---

### BUG-001 · Button "Phê duyệt" gây treo browser (CDP Timeout)

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-00 · Kế hoạch mua sắm |
| **URL** | `/procurement-plans/PP-26-00009` |
| **Mức độ** | 🔴 Critical |
| **Loại** | Performance / Timeout |

**Mô tả:**  
Khi click button **"Phê duyệt"** trên trang chi tiết kế hoạch mua sắm (trạng thái Bản nháp), Chrome DevTools Protocol (CDP) timeout sau 30 giây. Toàn bộ tab browser bị đóng băng (frozen), không thể tương tác. Thử lại bằng JavaScript execution cũng timeout (45,000ms).

**Bước tái hiện:**
1. Truy cập `/procurement-plans`
2. Click "Chi tiết →" vào một kế hoạch trạng thái "Bản nháp"
3. Click button **"Phê duyệt"** (màu xanh, góc trên phải)
4. Tab browser đóng băng, không phản hồi sau 30+ giây

**Nguyên nhân phân tích:**  
API call phê duyệt (`POST /api/procurement-plans/:id/approve`) không trả về response trong thời gian cho phép. Có thể do: (1) thiếu timeout handling ở frontend, (2) backend xử lý transaction quá nặng hoặc deadlock DB, (3) thiếu loading state/spinner dẫn đến không có feedback cho user.

**Tác động:**  
Workflow phê duyệt kế hoạch mua sắm bị chặn hoàn toàn. Không thể đưa kế hoạch từ "Bản nháp" → "Đã phê duyệt" qua UI.

---

### BUG-002 · Soát xét quản lý hiển thị sai năm "Q1-2099"

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-16 · Theo dõi tuân thủ → Soát xét quản lý |
| **URL** | `/compliance/mr` và `/compliance/mr/:id` |
| **Mức độ** | 🔴 Critical |
| **Loại** | Data Integrity / Seed Data Error |

**Mô tả:**  
Toàn bộ **39 bản ghi** trong danh sách Soát xét quản lý đều hiển thị cột **"Quý" = "Q1-2099"** — một năm không thực tế (73 năm trong tương lai). Khi mở chi tiết, trường "Quý" xác nhận giá trị "Q1-2099". Đây ảnh hưởng 100% dữ liệu của module.

**Bước tái hiện:**
1. Truy cập `/compliance/mr`
2. Quan sát cột "QUỶ" — tất cả rows hiển thị "Q1-2099"
3. Click bất kỳ bản ghi → chi tiết cũng hiển thị "Quý: Q1-2099"

**Nguyên nhân phân tích:**  
Lỗi trong **dữ liệu seed** (seeding script): trường `review_quarter` hoặc `period` được gán giá trị mặc định sai (`2099-Q1` thay vì năm hiện tại). Hoặc lỗi **format/parse ngày** — backend lưu đúng nhưng frontend parse sai format ISO date thành năm 2099.

**Tác động:**  
Toàn bộ chức năng Soát xét quản lý (Management Review) hiển thị dữ liệu sai. Không thể phân biệt các kỳ soát xét khác nhau. Vi phạm yêu cầu ISO 13485 về truy xuất hồ sơ quản lý.

---

### BUG-003 · Sidebar hiển thị lỗi "Trang này không thuộc module nào" khi navigate trực tiếp qua URL

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | Nhiều module (IMM-04, IMM-08, IMM-11...) |
| **URL** | `/commissioning/:id`, `/pm/schedules`, `/pm/templates`, `/calibration/:id` v.v. |
| **Mức độ** | 🔴 Critical |
| **Loại** | Navigation / State Hydration |

**Mô tả:**  
Khi navigate trực tiếp đến URL của một trang con (deep link), sidebar hiển thị thông báo lỗi **"Trang này không thuộc module nào. Mở Launcher để chọn module."** kèm button "Mở Launcher". Sau 2–3 giây, sidebar tự load lại và hiển thị đúng. Trạng thái này tồn tại ngắn nhưng gây mất navigation và UX xấu. Nghiêm trọng hơn: trên một số trang (`/pm/schedules`), button "Thêm lịch PM" bị **disabled (mờ)** trong suốt thời gian sidebar chưa load.

**Bước tái hiện:**
1. Từ trình duyệt, nhập trực tiếp URL `http://localhost:3000/pm/schedules`
2. Sidebar hiển thị "Trang này không thuộc module nào"
3. Button "+ Thêm lịch PM" bị disabled
4. Sau 2–3s, sidebar load đúng nhưng button vẫn disabled

**Nguyên nhân phân tích:**  
Module context/store chưa được khởi tạo trước khi component render. Ứng dụng phụ thuộc vào **client-side navigation** (SPA routing) để set module context, nhưng khi reload/deep-link trực tiếp thì context bị mất. Thiếu server-side hoặc URL-based module detection để khởi tạo context đúng.

**Tác động:**  
Deep link sharing bị broken. User bị mất orientation khi mở link trực tiếp. Button hành động bị disabled có thể làm user nghĩ tính năng không khả dụng.

---

## 🟠 High — Cao

---

### BUG-004 · Cột "KHOA" và "TCO 5Y" hiển thị sai trong bảng NR của Kế hoạch mua sắm

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-00 · Kế hoạch mua sắm |
| **URL** | `/procurement-plans/PP-26-00009` |
| **Mức độ** | 🟠 High |
| **Loại** | Data Display / Missing Field Mapping |

**Mô tả:**  
Trong bảng "Danh sách Needs Request đã gom" của chi tiết kế hoạch mua sắm, cột **KHOA hiển thị "—"** mặc dù NR-26-05-00013 có khoa "Phòng Mổ số 2" (hiển thị đúng ở trang detail NR). Cột **TCO 5Y cũng hiển thị "0 đ"** trong khi giá trị thực tế là **4.930.000.000 đ** (4.93 tỷ).

**Bước tái hiện:**
1. Truy cập `/procurement-plans/PP-26-00009`
2. Xem bảng "Danh sách Needs Request đã gom"
3. Quan sát cột KHOA = "—" và TCO 5Y = "0 đ"
4. So sánh với `/needs-requests/NR-26-05-00013` → Khoa = "Phòng Mổ số 2", TCO = 4.93 tỷ

**Nguyên nhân phân tích:**  
API endpoint trả về dữ liệu NR trong kế hoạch thiếu join với bảng khoa/phòng và thiếu populate trường TCO. Frontend mapping field name không khớp (`department` vs `department_name`, `tco_5y` vs `tco`).

**Tác động:**  
Ban lãnh đạo xem kế hoạch mua sắm không thấy được tổng TCO chính xác → quyết định ngân sách sai. Thiếu thông tin khoa → không biết NR từ khoa nào.

---

### BUG-005 · Tab Benchmark của hồ sơ kỹ thuật "Đã chốt" không có dữ liệu

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-02 · Hồ sơ kỹ thuật |
| **URL** | `/tech-specs/TS-26-00008` (tab 4. Benchmark) |
| **Mức độ** | 🟠 High |
| **Loại** | Missing Data / Workflow Gap |

**Mô tả:**  
Hồ sơ kỹ thuật TS-26-00008 đã qua đủ các bước workflow ("Đã so sánh thị trường", "Đã đánh giá rủi ro", "Đã chốt") nhưng **tab 4. Benchmark hiển thị "Chưa có ứng viên nào"**. Dữ liệu benchmark (so sánh thị trường) không được lưu/hiển thị dù workflow đã completed.

**Bước tái hiện:**
1. Truy cập `/tech-specs/TS-26-00008`
2. Click tab **"4. Benchmark"**
3. Hiển thị "Chưa có ứng viên nào" — trống hoàn toàn

**Nguyên nhân phân tích:**  
Có thể dữ liệu benchmark chưa được seed vào hồ sơ này, hoặc API `GET /tech-specs/:id/benchmark` trả về array rỗng. Workflow "Đã so sánh thị trường" được đánh dấu là completed nhưng không có dữ liệu thực tế backing step đó.

**Tác động:**  
Mâu thuẫn logic: workflow nói "Đã so sánh thị trường" nhưng không có dữ liệu benchmark. Kiểm toán viên và người dùng không thể xem kết quả so sánh thị trường.

---

### BUG-006 · Buổi đào tạo "Đã lập kế hoạch" không có học viên và thiếu action button

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-06 · Đào tạo & Năng lực → Buổi đào tạo |
| **URL** | `/imm06/sessions/TRN-2026-00008` |
| **Mức độ** | 🟠 High |
| **Loại** | Missing Feature / UX Gap |

**Mô tả:**  
Buổi đào tạo TRN-2026-00008 có trạng thái "Đã lập kế hoạch", thời lượng thực tế 38h, nhưng: (1) **Số học viên = 0**, không có cơ chế thêm học viên, (2) **Giảng viên (IMM Trainer) = "—"** mặc dù có giảng viên nội bộ, (3) **Không có action button** nào (không có "Bắt đầu đào tạo", "Hoàn thành", "Thêm học viên"). Trang chỉ hiển thị thông tin tĩnh.

**Bước tái hiện:**
1. Truy cập `/imm06/sessions`
2. Click vào TRN-2026-00008
3. Quan sát: Học viên = 0, không có button hành động

**Nguyên nhân phân tích:**  
(1) Chức năng thêm/quản lý học viên chưa được implement. (2) Field "Giảng viên (IMM Trainer)" chưa được bind với data source. (3) Action buttons cho workflow session chưa được phát triển.

**Tác động:**  
Không thể ghi nhận danh sách học viên tham gia → không tracking được năng lực nhân viên sau đào tạo → hồ sơ năng lực (Competency records) không có cơ sở.

---

### BUG-007 · Phiếu hiệu chuẩn không có action button để bắt đầu/hoàn thành

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-11 · Hiệu năng & Hiệu chuẩn |
| **URL** | `/calibration/CAL-2026-00016` |
| **Mức độ** | 🟠 High |
| **Loại** | Missing Feature / Workflow Gap |

**Mô tả:**  
Phiếu hiệu chuẩn CAL-2026-00016 (trạng thái "Đã lên lịch") không có button hành động workflow nào — không có "Bắt đầu hiệu chuẩn", "Nhập kết quả", "Hoàn thành", "Pass/Fail". Trạng thái nói "chuyển trạng thái qua các nút thao tác bên dưới" nhưng không có nút nào. Trường "Ngày thực hiện" bỏ trống.

**Bước tái hiện:**
1. Truy cập `/calibration` → Click CAL-2026-00016
2. Scroll toàn bộ trang → không thấy action button nào

**Nguyên nhân phân tích:**  
Hướng dẫn "chuyển trạng thái qua các nút bên dưới" là placeholder text chưa được implement. Có thể workflow buttons đang phát triển hoặc bị ẩn do điều kiện permission/state.

**Tác động:**  
Không thể thực hiện chu trình hiệu chuẩn end-to-end: "Đã lên lịch" → "Đang hiệu chuẩn" → "Hoàn thành (Pass/Fail)". Dashboard báo 0% compliance do không có record hoàn thành.

---

### BUG-008 · Kế hoạch bảo trì (/pm/schedules) trống và không thể tạo lịch

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-08 · Bảo trì định kỳ → Kế hoạch bảo trì |
| **URL** | `/pm/schedules` |
| **Mức độ** | 🟠 High |
| **Loại** | Missing Data + Button Disabled |

**Mô tả:**  
Trang "Lịch bảo trì định kỳ" hiển thị **"Tổng 0 lịch"** mặc dù hệ thống có 10 PM Work Orders đã được thực hiện (một số đã "Hoàn thành"). Không có dữ liệu schedule nào. Button "+ Thêm lịch PM" ở góc trên phải bị **disabled (màu mờ)** khi sidebar chưa load đúng context.

**Bước tái hiện:**
1. Navigate trực tiếp tới `/pm/schedules`
2. Quan sát: "Tổng 0 lịch", button "+ Thêm lịch PM" disabled

**Nguyên nhân phân tích:**  
(1) Schedules chưa được seed dù WOs đã có. (2) Button bị disable do sidebar context lỗi (liên quan BUG-003). PM Work Orders được tạo trực tiếp, không qua schedule, nên schedule table rỗng.

**Tác động:**  
Không có lịch PM định kỳ → hệ thống không tự động tạo WO theo lịch → tỷ lệ tuân thủ PM 33.3% không cải thiện được.

---

## 🟡 Medium — Trung bình

---

### BUG-009 · Mã QR nội bộ "Chưa sinh" trên thiết bị đã lắp đặt

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-04 · Lắp đặt, Định danh |
| **URL** | `/commissioning/ACC-26-05-00005` |
| **Mức độ** | 🟡 Medium |
| **Loại** | Missing Feature / Data |

**Mô tả:**  
Trường "Mã QR Nội bộ Bệnh viện" hiển thị **"Chưa sinh"** trên phiếu commissioning ACC-26-05-00005 dù thiết bị đã được lắp đặt và có Serial Number. Không có button "Sinh QR" hay cơ chế tự động generate QR code.

**Nguyên nhân phân tích:**  
Quy trình sinh QR code chưa được trigger tự động khi commissioning hoàn thành, hoặc chưa có button manual generate.

**Tác động:**  
Chức năng "Quét mã QR" (`/qr-scan`) không hoạt động được vì thiết bị chưa có QR. Mất truy xuất nhanh thiết bị qua QR.

---

### BUG-010 · Mã Bộ Y tế (BYT) trống trên phiếu commissioning

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-04 · Lắp đặt, Định danh |
| **URL** | `/commissioning/ACC-26-05-00005` |
| **Mức độ** | 🟡 Medium |
| **Loại** | Missing Data / Compliance |

**Mô tả:**  
Trường "Mã Bộ Y tế (Bộ Y tế)" trống hoàn toàn trên tất cả phiếu commissioning được kiểm tra. Đây là mã đăng ký thiết bị y tế bắt buộc theo quy định của Bộ Y tế Việt Nam.

**Nguyên nhân phân tích:**  
Dữ liệu seed không có mã đăng ký BYT. Hoặc field này chưa được tích hợp vào form nhập liệu ban đầu.

**Tác động:**  
Vi phạm tiêu chí G01 "Hồ sơ đi kèm" (đã đánh dấu ✗). Không thể hoàn thiện quy trình commissioning đúng pháp lý.

---

### BUG-011 · Năng lực nhân viên (Competency) thiếu trường kết quả đánh giá

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-06 · Năng lực → Chi tiết năng lực |
| **URL** | `/imm06/competencies/COMP-2026-00067` |
| **Mức độ** | 🟡 Medium |
| **Loại** | Missing Data / Incomplete Record |

**Mô tả:**  
Hồ sơ năng lực COMP-2026-00067 (Chu Hiếu, Vận hành viên cao cấp, trạng thái "Chờ đánh giá") có các trường **"Điểm tổng cuối", "Điểm lý thuyết", "Điểm thực hành"** đều hiển thị **"—"**. Cũng không có "Người phê duyệt" và "Ngày phê duyệt". Không có action button để nhập điểm hay phê duyệt.

**Nguyên nhân phân tích:**  
Kết quả đánh giá chưa được liên kết với buổi đào tạo. Chức năng nhập điểm đánh giá sau đào tạo chưa implement.

**Tác động:**  
Trạng thái "Chờ đánh giá" kéo dài vô thời hạn. Không có bằng chứng năng lực nhân viên cho kiểm toán ISO.

---

### BUG-012 · Dashboard IMM-11 báo 0% compliance dù có lịch hiệu chuẩn

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-11 · Hiệu chuẩn → Dashboard |
| **URL** | `/calibration/dashboard` |
| **Mức độ** | 🟡 Medium |
| **Loại** | Metric Calculation / Logic Error |

**Mô tả:**  
Dashboard hiệu chuẩn báo **"Tỷ lệ tuân thủ: 0%"** và **"0/2 đúng hạn"**. Tuy nhiên có 22 lịch hiệu chuẩn đang hoạt động và 4 phiếu đã tạo. Số liệu 0% không phản ánh thực tế.

**Nguyên nhân phân tích:**  
Tỷ lệ tuân thủ được tính dựa trên phiếu "Đã hoàn thành trong kỳ" — do BUG-007 không có action button hoàn thành, mẫu số luôn = 0, dẫn đến 0%.

**Tác động:**  
KPI sai → báo cáo compliance sai → ảnh hưởng quyết định quản lý.

---

### BUG-013 · PM Dashboard báo tỷ lệ tuân thủ 33.3% không nhất quán

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-08 · Bảo trì định kỳ → Dashboard |
| **URL** | `/pm/dashboard` |
| **Mức độ** | 🟡 Medium |
| **Loại** | Metric Inconsistency |

**Mô tả:**  
Dashboard PM báo **"Tỷ lệ tuân thủ: 33.3%"** với "1 Hoàn thành đúng hạn / 3 Tổng lên lịch". Tuy nhiên danh sách Lệnh bảo trì có **10 WOs**, phần lớn "Hoàn thành". Số liệu dashboard không khớp với dữ liệu thực tế.

**Nguyên nhân phân tích:**  
Dashboard chỉ tính WOs trong **tháng hiện tại** (tháng 5/2026) nhưng không hiển thị rõ phạm vi lọc này cho user, gây hiểu lầm.

**Tác động:**  
User hiểu nhầm 33.3% là tỷ lệ tổng thể thay vì tháng hiện tại → đánh giá sai năng lực bảo trì.

---

### BUG-014 · Tên template PM checklist dùng ký tự kỹ thuật thay vì tên người dùng

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-08 · Bảo trì định kỳ → Mẫu bảng kiểm |
| **URL** | `/pm/templates` |
| **Mức độ** | 🟡 Medium |
| **Loại** | UX / Data Naming |

**Mô tả:**  
Tên template trong danh sách hiển thị dưới dạng **"Checklist PM Quý — Thiet-bi-Chan-doan-Hinh-anh"** (dùng slug kỹ thuật). Danh mục tài sản cũng hiển thị dạng slug: "Thiet-bi-Chan-doan-Hinh-anh" thay vì "Thiết bị chẩn đoán hình ảnh".

**Nguyên nhân phân tích:**  
Frontend hiển thị trực tiếp field `category_slug` thay vì `category_name` khi render tên template. Thiếu display name mapping.

**Tác động:**  
UX khó đọc, không thân thiện với kỹ thuật viên không quen kỹ thuật hệ thống.

---

## 🔵 Low — Thấp

---

### BUG-015 · URL /purchase-orders trả về 404

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-03 · Đơn hàng mua |
| **URL** | `/purchase-orders` (404) · URL đúng: `/purchases` |
| **Mức độ** | 🔵 Low |
| **Loại** | Routing / URL Convention |

**Mô tả:**  
URL `/purchase-orders` trả về 404 Not Found. URL thực tế là `/purchases`. Không có redirect từ URL cũ sang URL mới. Không nhất quán với convention của các module khác (`/procurement-plans`, `/vendor-evaluations`, v.v.).

**Nguyên nhân phân tích:**  
Thiếu route alias hoặc redirect rule. Convention đặt tên URL không thống nhất.

---

### BUG-016 · Danh sách Phiếu Nghiệm thu hiển thị skeleton 2–3 giây khi load trực tiếp

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-04 · Tiếp nhận & Lắp đặt |
| **URL** | `/commissioning/:id` |
| **Mức độ** | 🔵 Low |
| **Loại** | Performance / Loading State |

**Mô tả:**  
Khi navigate trực tiếp qua URL đến chi tiết commissioning, trang hiển thị skeleton loading trong 2–3 giây trước khi render nội dung. Trong thời gian này, nội dung chính không hiển thị.

**Nguyên nhân phân tích:**  
API call để fetch commissioning detail chậm, hoặc React component chờ async data fetch trước khi render. Thiếu SSR/hydration hoặc cache.

---

### BUG-017 · Cột "Scorecard" trong danh sách Soát xét quản lý luôn trống

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | IMM-16 · Soát xét quản lý |
| **URL** | `/compliance/mr` |
| **Mức độ** | 🔵 Low |
| **Loại** | Missing Data / Feature |

**Mô tả:**  
Cột "SCORECARD" trong danh sách soát xét quản lý hiển thị "—" với tất cả 39 bản ghi. Scorecard không được liên kết với Management Review session.

**Nguyên nhân phân tích:**  
Chức năng liên kết Scorecard → Management Review chưa implement hoặc chưa có data.

---

### BUG-018 · Hợp đồng dịch vụ trống dù có 4 nhà cung cấp và nhiều thiết bị

| Thuộc tính | Chi tiết |
|---|---|
| **Module** | Tài sản & Đối tác → Hợp đồng dịch vụ |
| **URL** | `/service-contracts` |
| **Mức độ** | 🔵 Low |
| **Loại** | Missing Seed Data |

**Mô tả:**  
Trang "Hợp đồng dịch vụ" hiển thị **"Tổng 0 hợp đồng"** mặc dù hệ thống có 4 nhà cung cấp đang hoạt động, 4 thiết bị, và các phiếu sửa chữa tham chiếu đến dịch vụ nhà cung cấp.

**Nguyên nhân phân tích:**  
Dữ liệu service contract chưa được seed. Đây là module master data nhưng chưa có dữ liệu mẫu để demo.

---

## ⚠️ Modules đang phát triển (Đang phát triển)

| IMM | Tên module | Trạng thái |
|---|---|---|
| IMM-07 | Theo dõi hiệu suất | Đang phát triển — card có badge, không navigate được |
| IMM-10 | Hậu kiểm & Tuân thủ | Đang phát triển — card có badge, không navigate được |
| IMM-13 | Ngừng sử dụng & Điều chuyển | Đang phát triển — card có badge, không navigate được |
| IMM-14 | Giải nhiệm thiết bị | Đang phát triển — card có badge, không navigate được |
| IMM-17 | Phân tích dự đoán | Đang phát triển — card có badge, không navigate được |

---

## Tổng hợp theo module

| Module | Lỗi | Bug IDs |
|---|---|---|
| IMM-00 Kế hoạch mua sắm | 2 | BUG-001, BUG-004 |
| IMM-02 Hồ sơ kỹ thuật | 1 | BUG-005 |
| IMM-04 Lắp đặt & Định danh | 3 | BUG-003, BUG-009, BUG-010 |
| IMM-06 Đào tạo & Năng lực | 2 | BUG-006, BUG-011 |
| IMM-08 Bảo trì định kỳ | 3 | BUG-003, BUG-008, BUG-013, BUG-014 |
| IMM-11 Hiệu chuẩn | 2 | BUG-007, BUG-012 |
| IMM-16 Tuân thủ & Quản lý | 3 | BUG-002, BUG-017 |
| Toàn hệ thống | 1 | BUG-003 |
| Master Data | 2 | BUG-015, BUG-018 |

---

## Khuyến nghị ưu tiên sửa

### Sprint tiếp theo (Critical — phải sửa ngay)
1. **BUG-001** — Fix timeout/freeze khi click Phê duyệt: thêm loading state, timeout handling, và error boundary
2. **BUG-002** — Fix dữ liệu seed "Q1-2099": kiểm tra migration script và seed data cho bảng management_reviews
3. **BUG-003** — Fix sidebar hydration: detect module từ URL pattern, initialize store server-side hoặc tách module context init ra khỏi navigation event

### Sprint 2 (High — ảnh hưởng workflow)
4. **BUG-004** — Fix field mapping KHOA và TCO trong API procurement plan NR list
5. **BUG-005** — Seed benchmark data cho TS đã chốt, hoặc hiển thị warning nếu thiếu
6. **BUG-006** — Implement add trainee và action buttons cho Training Session
7. **BUG-007** — Implement action buttons workflow cho Calibration record
8. **BUG-008** — Fix button disable state và seed PM schedules data

---

*Báo cáo được tạo tự động bằng browser automation testing.*  
*Ngày xuất: 26/05/2026*
