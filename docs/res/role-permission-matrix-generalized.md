# Ma trận phân quyền AssetCore — Bảng chức năng tổng quát (Generalized)

> **Mục đích**: Rút gọn danh mục chức năng chi tiết (thường ở mức từng thao tác / từng nút bấm) thành các **đơn vị phân quyền tổng quát** để xây dựng ma trận role hệ thống.
>
> **Nguyên tắc tổng quát hóa**:
> - 1 dòng = 1 **đơn vị phân quyền** (permission unit) — gom các thao tác cùng đối tượng nghiệp vụ + cùng cấp quyết định vào 1 dòng.
> - Tách dòng khi: (a) khác **actor / chủ thể quyết định**, (b) khác **state máy duyệt**, (c) khác **DocType nguồn**.
> - Gộp các thao tác CRUD trên cùng 1 DocType / 1 nghiệp vụ vào 1 dòng — ô quyền dùng ký hiệu CRUD chuẩn.
>
> **Nguồn**:
> - Danh mục chi tiết: `docs/res/Ma tran phan quyen Role.xlsx` + `role-permission-matrix-realigned.md`
> - Hệ thống đang triển khai: 13 module IMM (IMM-00, 01, 02, 03, 04, 05, 06, 08, 09, 11, 12, 15, 16)
>
> **Ngày tổng hợp**: 2026-05-25
>
> **Phạm vi**: 18 nhóm chức năng × ~70 đơn vị phân quyền (rút từ ~150 thao tác chi tiết). Ô role để trống — BV NĐ1 / PMO tự điền.

---

## 1. Quy ước ký hiệu

| Ký hiệu | Ý nghĩa                                    |
| ------- | ------------------------------------------ |
| **X**   | Toàn quyền (Create + Read + Update + Delete + Submit) |
| **R**   | Chỉ xem (Read)                             |
| **C**   | Tạo + Xem (Create + Read)                  |
| **U**   | Sửa + Xem (Update + Read, không tạo mới)   |
| **A**   | Phê duyệt / từ chối (Approve workflow)     |
| **S**   | Nộp / Submit (đẩy state machine)           |
| (trống) | Không có quyền                             |

> Một dòng có thể ghi nhiều ký hiệu (vd. **C + S** = Tạo và Nộp duyệt; **R + A** = Xem và Duyệt).

---

## 2. Vai trò trong ma trận

| Vai trò             | Mô tả                                                            |
| ------------------- | ---------------------------------------------------------------- |
| **TP-VT**           | Trưởng phòng Vật tư – Trang thiết bị y tế                        |
| **KS-KTV**          | Kỹ sư / Kỹ thuật viên sửa chữa – bảo trì                         |
| **KP-SD**           | Khoa phòng sử dụng (người dùng cuối)                             |
| **TC-KT**           | Tài chính – Kế toán                                              |
| **TK-VT**           | Thủ kho vật tư – phụ tùng                                        |
| **MS-DT**           | Mua sắm / Đấu thầu                                               |
| **BGD**             | Ban Giám đốc                                                     |
| **IT-QTHT**         | Quản trị hệ thống (IT)                                           |

---

## 3. Ma trận phân quyền — Bảng chức năng tổng quát

| Nhóm chức năng | Chức năng (tổng quát) | TP-VT | KS-KTV | KP-SD | TC-KT | TK-VT | MS-DT | BGD | IT-QTHT |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **A1. Tài sản & Vòng đời thiết bị** | Quản lý hồ sơ thiết bị (CRUD + cập nhật trạng thái vòng đời + gán Serial / QR) | | | | | | | | |
| | Xem dòng thời gian & KPI thiết bị (timeline, uptime, MTBF, MTTR) | | | | | | | | |
| | Quản lý khấu hao thiết bị (lập + theo dõi lịch khấu hao) | | | | | | | | |
| **A2. Danh mục dữ liệu nền** | Quản lý danh mục cơ cấu tổ chức (Khoa / Phòng ban, Vị trí lắp đặt, Đơn vị đo) | | | | | | | | |
| | Quản lý danh mục thiết bị (Phân loại, Model / dòng máy, GMDN) | | | | | | | | |
| | Quản lý đối tác (Nhà cung cấp + Hợp đồng dịch vụ & bảo hành) | | | | | | | | |
| | Điều chuyển nội bộ thiết bị | | | | | | | | |
| | Nhập dữ liệu hàng loạt (Import Wizard — toàn bộ DocType nền) | | | | | | | | |
| **A3. Kho phụ tùng — Nền tảng** | Quản lý kho vật tư & danh mục phụ tùng (CRUD Warehouse + Spare Part) | | | | | | | | |
| | Theo dõi tồn kho & ghi nhận chuyển kho (Nhập / Xuất / Điều chuyển) | | | | | | | | |
| **B1. Đề xuất nhu cầu & Ngân sách** | Lập & chấm điểm phiếu nhu cầu thiết bị (6 tiêu chí → P1–P4) | | | | | | | | |
| | Phê duyệt / từ chối nhu cầu thiết bị | | | | | | | | |
| | Lập kế hoạch mua sắm & dự toán ngân sách CAPEX + OPEX 5 năm | | | | | | | | |
| | Xem dự báo nhu cầu thiết bị (Demand Forecast) | | | | | | | | |
| **B2. Thông số kỹ thuật & Phân tích thị trường** | Soạn thông số kỹ thuật + yêu cầu kỹ thuật chi tiết (manual + bulk import) | | | | | | | | |
| | So sánh thị trường ≥3 ứng viên + đánh giá tương thích hạ tầng (Net/HIS/PACS/LIS/Power/HVAC) | | | | | | | | |
| | Đánh giá rủi ro phụ thuộc nhà cung cấp (5 dimensions Lock-in) | | | | | | | | |
| | Khóa Spec + phát hành phiên bản mới (rút lại + versioning + chuyển IMM-03) | | | | | | | | |
| | Quản lý tài liệu đính kèm thông số kỹ thuật | | | | | | | | |
| **B3. Đánh giá NCC & Quyết định mua sắm** | Tạo đánh giá NCC + mời ứng viên + tiếp nhận báo giá | | | | | | | | |
| | Chấm điểm tiêu chí (Kỹ thuật / Thương mại / Tài chính / Tuân thủ) + audit NCC | | | | | | | | |
| | Ra quyết định mua sắm & sinh PO | | | | | | | | |
| | Quản lý AVL — danh sách NCC được phê duyệt (5 states + expiry) | | | | | | | | |
| | Quản lý hồ sơ NCC mở rộng + chứng chỉ (ISO / GMP / …) | | | | | | | | |
| | Xem scorecard NCC theo quý | | | | | | | | |
| **B4. Đơn mua hàng (PO)** | Tạo & nhận hàng PO vào kho | | | | | | | | |
| | Phê duyệt / hủy PO | | | | | | | | |
| **C1. Lắp đặt & Nghiệm thu** | Tạo phiếu nghiệm thu / lắp đặt từ PO + ghi nhận lắp đặt thực tế (checklist + Serial + baseline) | | | | | | | | |
| | Kiểm tra hồ sơ pháp lý đầu vào (Gate G01) | | | | | | | | |
| | Tạm dừng & cho phép sử dụng lâm sàng (Clinical Hold / Release) | | | | | | | | |
| | Phê duyệt cuối + bàn giao thiết bị (auto-mint AC Asset) + in biên bản | | | | | | | | |
| | Ghi nhận & đóng lỗi không phù hợp (Non-Conformance / DOA) | | | | | | | | |
| **C2. Hồ sơ thiết bị** | Upload + quản lý tài liệu thiết bị (versioning + miễn trừ NĐ98) | | | | | | | | |
| | Phê duyệt / từ chối tài liệu thiết bị (auto archive bản cũ) | | | | | | | | |
| | Tạo yêu cầu tài liệu (deadline + escalation) | | | | | | | | |
| | Xem kho hồ sơ + cấu hình loại tài liệu bắt buộc | | | | | | | | |
| **C3. Đào tạo & Năng lực** | Quản lý chương trình + lịch buổi đào tạo + giảng viên | | | | | | | | |
| | Thực hiện + chấm điểm + hoàn tất buổi đào tạo | | | | | | | | |
| | Phê duyệt năng lực (Supervisor Sign-off + tái chứng nhận + thu hồi sau sự cố) | | | | | | | | |
| | Xem dashboard ma trận năng lực thiếu | | | | | | | | |
| **D1. Bảo trì định kỳ (PM)** | Lập lịch + quản lý checklist mẫu PM | | | | | | | | |
| | Phân công + dời lịch kỹ sư PM | | | | | | | | |
| | Thực hiện + nộp kết quả PM (gồm báo cáo hư hỏng nghiêm trọng phát sinh) | | | | | | | | |
| | Xem dashboard PM (KPI + lịch tháng + lịch sử theo thiết bị) | | | | | | | | |
| **D2. Sửa chữa (CM)** | Tạo + phân công lệnh sửa chữa (từ sự cố / PM dừng) | | | | | | | | |
| | Nộp chẩn đoán hư hỏng + yêu cầu cấp phát phụ tùng + thay đổi firmware | | | | | | | | |
| | Đóng lệnh sửa chữa (checklist 100% Pass hoặc "Không thể sửa") | | | | | | | | |
| | Xác nhận nghiệm thu sửa chữa từ khoa sử dụng | | | | | | | | |
| | Xem dashboard MTTR & lịch sử sửa chữa | | | | | | | | |
| **D3. Hiệu chuẩn / Kiểm định** | Lập lịch + phân công kỹ sư hiệu chuẩn | | | | | | | | |
| | Thực hiện + nhập kết quả đo (dung sai) + nộp kết quả hiệu chuẩn | | | | | | | | |
| | Bàn giao thiết bị ra ngoài + nhận chứng chỉ hiệu chuẩn | | | | | | | | |
| **D4. Sự cố & Phân tích nguyên nhân** | Báo cáo sự cố thiết bị (Initial Report) | | | | | | | | |
| | Tiếp nhận + xử lý + hủy sự cố (SLA <30 phút tiếp nhận, Critical <4h / Major <24h) | | | | | | | | |
| | Tạo + nộp phân tích nguyên nhân gốc (5-Why / Fishbone) | | | | | | | | |
| | Đóng CAPA + đóng sự cố (bắt buộc nguyên nhân + khắc phục + phòng ngừa) | | | | | | | | |
| | Xem dashboard sự cố + cảnh báo hư hỏng mãn tính (≥3 sự cố / 90 ngày) | | | | | | | | |
| **D5. Tồn kho phụ tùng — Nghiệp vụ** | Tạo yêu cầu cấp phát phụ tùng theo Work Order | | | | | | | | |
| | Phê duyệt cấp phát thường + cấp phát khẩn cấp (dual approval) | | | | | | | | |
| | Xuất kho + ghi nhận trả phụ tùng về kho | | | | | | | | |
| | Lập + hoàn tất kiểm kê chu kỳ | | | | | | | | |
| | Quản lý danh sách phụ tùng đặc biệt (watchlist trọng yếu + thay thế tương đương + lô / hạn dùng) | | | | | | | | |
| | Lập + phê duyệt dự báo nhu cầu phụ tùng theo tháng | | | | | | | | |
| **E1. Tuân thủ & QMS** | Khai báo + quản lý quy tắc tuân thủ (versioned) | | | | | | | | |
| | Ghi nhận / xác nhận / đóng vi phạm + miễn trừ vi phạm (có phê duyệt + ngày hết hạn) | | | | | | | | |
| | Quản lý CAPA toàn vòng đời + kiểm tra hiệu lực | | | | | | | | |
| | Lập kế hoạch + thực hiện + đóng Audit nội bộ | | | | | | | | |
| | Sinh + publish Scorecard tuân thủ tháng + Họp xem xét lãnh đạo (ISO 13485 quarterly) | | | | | | | | |
| | Xem heatmap tuân thủ theo module × khoa + kiểm tra tuân thủ của thiết bị | | | | | | | | |
| **F1. Báo cáo & Dashboard** | Xem dashboard nghiệp vụ (Tổng quan + PM + CM/MTTR + Hiệu chuẩn + Sự cố + Tuân thủ) | | | | | | | | |
| | Xuất báo cáo KPI thiết bị (MTBF / MTTR / Uptime) | | | | | | | | |
| **G1. Quản trị hệ thống** | Quản lý hồ sơ người dùng | | | | | | | | |
| | Phê duyệt user đăng ký mới + gán Role / Quyền | | | | | | | | |
| | Xem nhật ký audit hệ thống | | | | | | | | |
| | Cấu hình chính sách SLA | | | | | | | | |

---

## 4. Hướng dẫn điền ma trận

### 4.1. Cách đọc 1 dòng

Mỗi dòng là một **đơn vị phân quyền**. Khi điền role:
- Ô **trống** = role không thấy / không thao tác được chức năng.
- Ô **R** = role chỉ xem (không tạo, không sửa, không duyệt).
- Ô **C / U / X** = role được CRUD ở các mức tăng dần.
- Ô **A** = role có quyền phê duyệt (workflow approver).
- Ô **S** = role có quyền nộp / submit (push state machine sang state tiếp).

### 4.2. Quy tắc phân tách 4-eyes

Với các chức năng yêu cầu **2 cấp** (vd. cấp phát khẩn cấp dual approval, phê duyệt mua sắm > ngưỡng), KHÔNG gán **A** cho cùng 1 role 2 lần — tách thành 2 role khác nhau (ví dụ: KS-KTV nộp, TP-VT duyệt cấp 1, BGD duyệt cấp 2).

### 4.3. Quy tắc Khoa phòng sử dụng (KP-SD)

KP-SD theo thiết kế **không có quyền sửa data master** — chỉ có:
- **C**: Tạo phiếu báo sự cố + xác nhận nghiệm thu sửa chữa.
- **R**: Xem hồ sơ + lịch sử thiết bị thuộc khoa của mình (user-scope filter).
- **S**: Nộp yêu cầu (đề xuất nhu cầu, document request, training feedback).

KP-SD **không bao giờ** có **U / X / A** trên data master (IMM-00 / 01 / 02 / 03 / 04).

### 4.4. Quy tắc IT-QTHT

IT-QTHT chỉ có quyền trên nhóm **G1 (Quản trị hệ thống)**. Trên các nhóm nghiệp vụ A–F, IT-QTHT mặc định **R** (debug + hỗ trợ) — không có **C / U / X / A / S**.

### 4.5. Module IMM tương ứng (trace về code)

| Mã nhóm | Module IMM trong code              |
| ------- | ---------------------------------- |
| A1, A2  | IMM-00 (Master Data + Asset Core)  |
| A3      | IMM-00 (Inventory backbone)        |
| B1      | IMM-01 (Needs & Budget)            |
| B2      | IMM-02 (Tech Spec)                 |
| B3      | IMM-03 (Vendor Eval & Procurement) |
| B4      | IMM-00 (PO) hoặc ERPNext Purchase  |
| C1      | IMM-04 (Commissioning)             |
| C2      | IMM-05 (Asset Document)            |
| C3      | IMM-06 (Training & Competency)     |
| D1      | IMM-08 (Preventive Maintenance)    |
| D2      | IMM-09 (Corrective / Repair)       |
| D3      | IMM-11 (Calibration)               |
| D4      | IMM-12 (Incident & RCA)            |
| D5      | IMM-15 (Inventory Operations)      |
| E1      | IMM-16 (Compliance & QMS)          |
| F1      | Cross-module (Dashboards)          |
| G1      | Frappe core + AssetCore RBAC       |

---

## 5. Tổng kết

| Thống kê                                  | Giá trị     |
| ----------------------------------------- | ----------- |
| Số nhóm chức năng                         | **18**      |
| Số đơn vị phân quyền                      | **~70**     |
| Mức rút gọn so với danh mục chi tiết gốc  | ~150 → ~70 (giảm 53%) |
| Số vai trò                                | **8**       |
| Số ô cần điền (~70 × 8)                  | **~560**    |

> File này là **template** — sau khi BV NĐ1 / PMO điền xong các ô role, sẽ:
> 1. Đối chiếu ngược với `role-permission-matrix-realigned.md` (level chi tiết) để map về DocPerm cụ thể.
> 2. Sinh fixture `assetcore/fixtures/custom_doc_perm.json` + `assetcore/fixtures/role.json`.
> 3. Apply qua `bench --site <site> migrate` → áp dụng phân quyền vào DB.

---

**File path**: `docs/res/role-permission-matrix-generalized.md`
**Liên quan**:
- `docs/res/role-permission-matrix-realigned.md` (chi tiết theo DocType)
- `docs/res/role-redesign-module-based.md` (RBAC design rationale)
- `docs/res/user-scope-filter-analysis.md` (KP-SD scope filter)
- `docs/res/Ma tran phan quyen Role.xlsx` (file gốc BV NĐ1)
