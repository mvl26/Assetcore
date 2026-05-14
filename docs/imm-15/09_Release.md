# IMM-15 — Release & User Guide

> ✅ Implemented — Wave 2 (feature/hieuc/wave-2). Đợi UAT sign-off để cut v1.0.0.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 1.0.0-rc.2 |
| Template | 09 Release |
| Ngày cập nhật | 2026-05-14 |
| Trạng thái | IMPLEMENTED — Wave 2 (chờ UAT) |

---

## §I — Hướng dẫn sử dụng (Tiếng Việt)

### Phân quyền theo vai trò

| Vai trò | Quyền chính | Màn hình chính |
|---|---|---|
| Thủ kho (IMM Storekeeper) | Tạo allocation, Pick & Issue, Kiểm kê, Trả phụ tùng | SpareItemsList, AllocationList, CycleCountList |
| Trưởng Phân xưởng (Workshop Head) | Duyệt allocation, Duyệt kiểm kê, Override Emergency, Duyệt forecast, Quản lý Watchlist | AllocationDetail, CycleCountDetail, ForecastView, WatchlistView, Dashboard |
| Kỹ sư Biomedical (Biomed Tech) | Tạo allocation request | AllocationCreate, AllocationList |
| Kỹ thuật viên HTM (HTM Technician) | Tạo allocation request, Hỗ trợ kiểm kê | AllocationCreate, CycleCountDetail |
| QA Officer (Tổ HC-QLCL) | Xác minh kiểm kê, Theo dõi audit | CycleCountDetail, Dashboard |
| Phó Trưởng Khối (VP Block 1 / Operations Manager) | Approve override Emergency, Approve forecast, Quản lý Watchlist | Dashboard, WatchlistView, ForecastView |
| Kế toán (Accountant) | Đọc Dashboard KPI, Báo cáo giá trị | Dashboard |
| CMMS Admin | Toàn quyền | Tất cả |

---

### Vai trò: Thủ kho (IMM Storekeeper)

#### Xem danh sách phụ tùng

1. Truy cập **Phụ tùng Y tế** trên menu bên trái
2. Sử dụng bộ lọc: **Phân hạng** (Critical/Major/Consumable/Tool), **ABC**, **Chỉ hàng sắp hết**
3. Xem màu tồn kho:
   - Xanh ✅ — đủ hàng (≥ 2 × min)
   - Vàng ⚠ — cần theo dõi (min ≤ qty < min × 2)
   - Cam 🟠 — dưới mức tối thiểu
   - Đỏ 🔴 — hết hàng
   - Đỏ đậm 🚨 — vi phạm Watchlist Critical

#### Thực hiện Pick và Issue phiếu cấp phát

1. Vào **Phiếu cấp phát phụ tùng** → mở phiếu đã **Đã duyệt**
2. Click **[Pick]** — xác nhận phụ tùng đã sẵn sàng lấy từ kệ
3. Click **[Issue]**:
   - Nếu phụ tùng có **Traceability** (icon 🔖): bắt buộc nhập **batch_no** hoặc **serial_no**
   - Xác nhận → hệ thống tự tạo Phiếu xuất kho (AC Stock Movement), tồn kho cập nhật tức thì
4. Khi phiếu chuyển sang **Đã cấp** ✅ → thao tác hoàn tất

#### Trả phụ tùng (sau khi sử dụng)

1. Mở phiếu cấp phát trạng thái **Đã cấp**
2. Click **[Trả phụ tùng]**
3. Chọn số lượng và tình trạng:
   - **Tốt (Good)** → nhập kho lại kho xuất ban đầu
   - **Hỏng (Damaged)** → hệ thống tự chuyển vào **kho QC Hold** để kiểm tra
4. Xác nhận → hệ thống tạo Phiếu nhập kho tương ứng

#### Tạo phiên kiểm kê chu kỳ

1. Vào **Kiểm kê chu kỳ** → click **[+ Tạo phiên kiểm kê]**
2. Chọn **Kho**, **Loại kiểm kê** (Toàn phần / ABC-A hàng tháng / Cycle / Spot), **Danh sách phụ tùng**
3. Hệ thống tự điền **Số lượng hệ thống** từ tồn kho hiện tại
4. Click **[Bắt đầu đếm]** → trạng thái chuyển sang **Đang đếm**
5. Nhập **Số lượng đếm thực tế** cho từng dòng:
   - Hỗ trợ quét QR code để tự chuyển đến đúng dòng phụ tùng
   - Chênh lệch tự tính sau 0.8 giây
   - Dòng chênh lệch > 5%: highlight đỏ → **bắt buộc nhập Nguyên nhân** và đánh dấu **CAPA**
6. Click **[Hoàn tất đếm]** → chuyển sang Đã review (Trưởng Phân xưởng sẽ post kết quả)

---

### Vai trò: Trưởng Phân xưởng (Workshop Head)

#### Duyệt phiếu cấp phát

1. Vào **Phiếu cấp phát phụ tùng** → lọc **Trạng thái: Yêu cầu**
2. Mở phiếu → xem chi tiết phụ tùng, Work Order liên kết, tồn kho hiện tại
3. Click **[Approve]** → phiếu chuyển sang **Đã duyệt**, Thủ kho nhận thông báo
4. Hoặc click **[Hủy]** kèm lý do nếu yêu cầu không hợp lệ

#### Duyệt Emergency Override

Khi Thủ kho gặp tình huống tồn kho = 0 nhưng cần cấp khẩn cho thiết bị Critical:

1. Hệ thống hiện modal **Emergency Override — Cấp phát khẩn**
2. Bạn (Workshop Head) là **Approver 1** (tự động)
3. Chọn **Approver 2** — phải là người khác, thuộc nhóm `_OVERRIDE_ROLES` (VP Block 1 hoặc CMMS Admin)
4. Nhập **Lý do khẩn cấp** (tối thiểu 30 ký tự)
5. Đính kèm văn bản nếu có
6. Click **[Xác nhận Override & Issue]**

> ⚠️ Hành động này ghi vĩnh viễn vào Audit Trail với nhãn `EMERGENCY_OVERRIDE`. Tránh lạm dụng — KPI "Override/tháng" được theo dõi và báo cáo lên Management.

#### Post kết quả kiểm kê

1. Mở phiếu kiểm kê trạng thái **Đã review**
2. Xem tổng hợp chênh lệch — các dòng đỏ có CAPA
3. Xác nhận **Người xác minh (verified_by)** — phải là người khác với người đếm
4. Click **[Post]** → hệ thống:
   - Tạo Phiếu điều chỉnh kho (AC Stock Movement Adjustment) cho các dòng có chênh lệch
   - Cập nhật tồn kho thực tế
   - Tạo CAPA (link IMM-16) cho từng dòng chênh lệch lớn

#### Quản lý Critical Spare Watchlist

1. Vào **Critical Spare Watchlist** → click **[+ Thêm entry]**
2. Chọn **Thiết bị Critical**, **Phụ tùng** (bắt buộc loại Critical), **Kho**, **Min on-hand**
3. Nhập lý do (ghi vào Audit Trail)
4. Khi tồn kho phụ tùng < min_on_hand → hệ thống tự gửi cảnh báo đỏ qua email

---

### Vai trò: Kỹ sư Biomedical / HTM Technician

#### Tạo phiếu cấp phát phụ tùng

1. Vào **Phiếu cấp phát phụ tùng** → click **[+ Tạo Phiếu mới]**
2. Chọn **Loại Work Order** (PM / CM / Repair) và **WO Ref** → thiết bị tự điền
3. Chọn **Kho xuất** và **Mức ưu tiên**:
   - **Thông thường** — quy trình bình thường
   - **Khẩn** — ưu tiên xử lý nhanh
   - **Khẩn cấp** — khi thiết bị Critical đang hỏng
4. Thêm phụ tùng cần dùng → hệ thống kiểm tra tồn kho ngay (cột OK? / ⚠ MR)
5. Click **[Tạo & Gửi duyệt]** → gửi cho Trưởng Phân xưởng xét duyệt
6. Theo dõi trạng thái trong danh sách phiếu

> Lưu ý: Kỹ sư KHÔNG thể tự Approve hoặc Issue phiếu của mình.

---

### Vai trò: QA Officer (Tổ HC-QLCL)

#### Xác minh kiểm kê

1. Vào **Kiểm kê chu kỳ** → lọc trạng thái **Đang đếm** hoặc **Đã review**
2. Mở phiếu → kiểm tra các dòng chênh lệch
3. Xem **Nguyên nhân** và **CAPA** đã được ghi chú chưa
4. Nếu phát hiện thiếu sót → thông báo Trưởng Phân xưởng trước khi Post

#### Theo dõi Dashboard KPI

1. Vào **Dashboard Tồn kho** → xem 6 KPI chính
2. Click vào tile **Critical Breach** → xem danh sách vi phạm Watchlist
3. Click vào tile **Cycle Accuracy** → xem danh sách kiểm kê đã Post

---

### Vai trò: Kế toán (Accountant)

1. Truy cập **Dashboard Tồn kho** (read-only)
2. Xem KPI: Turnover/năm, Days-on-Hand, Giá trị tồn kho
3. Xuất báo cáo nếu cần — liên hệ CMMS Admin

---

## §II — Glossary trạng thái (Tiếng Việt)

### Phiếu cấp phát phụ tùng (IMM Spare Allocation)

| Trạng thái | Ý nghĩa | Người xử lý tiếp theo |
|---|---|---|
| Yêu cầu | Đã tạo, chờ duyệt | Trưởng Phân xưởng |
| Đã duyệt | Đã phê duyệt, Thủ kho pick hàng | Thủ kho |
| Đã pick | Hàng đã sẵn sàng tại kệ | Thủ kho (Issue) |
| Đã cấp | Đã xuất kho, AC Stock Movement tạo | (Kỹ sư sử dụng) |
| Đã trả | Phụ tùng đã trả về kho | — |
| Đã hủy | Phiếu bị hủy | — |

### Phiên kiểm kê chu kỳ (IMM Stock Cycle Count)

| Trạng thái | Ý nghĩa | Người xử lý tiếp theo |
|---|---|---|
| Lên kế hoạch | Đã tạo phiên, chưa bắt đầu đếm | Thủ kho |
| Đang đếm | Đang nhập số lượng đếm thực tế | Thủ kho |
| Đã review | Hoàn tất đếm, chờ Trưởng Phân xưởng xác nhận | Trưởng Phân xưởng |
| Đã post | Kết quả đã xác nhận, tồn kho đã điều chỉnh | — |

### Dự báo nhu cầu phụ tùng (IMM Spare Part Forecast)

| Trạng thái | Ý nghĩa |
|---|---|
| Nháp | Hệ thống tạo tự động, chưa duyệt |
| Đã duyệt | Đã phê duyệt, hiển thị danh sách reorder |

---

## §III — FAQ

### Q1: Tại sao tôi không thể Issue phiếu cấp phát?

**Trả lời:** Có một số nguyên nhân:
- Phiếu chưa ở trạng thái **Đã pick** (phải qua Approve → Pick trước)
- Bạn chưa có quyền Issue (chỉ Thủ kho và Operations Manager được Issue)
- Phụ tùng có bật **Traceability** → phải nhập `batch_no` hoặc `serial_no` trước khi Issue
- Tồn kho không đủ và chưa kích hoạt Emergency Override

Kiểm tra thông báo lỗi hiển thị bên dưới nút Issue — lỗi sẽ chỉ rõ nguyên nhân cụ thể bằng tiếng Việt.

---

### Q2: Emergency Override hoạt động như thế nào?

**Trả lời:** Emergency Override cho phép cấp phát phụ tùng khi tồn kho = 0 trong trường hợp thiết bị Critical bị hỏng khẩn cấp.

Quy trình:
1. Phiếu phải có **Urgency = Khẩn cấp** (Emergency)
2. Phụ tùng phải thuộc loại **Critical**
3. Cần **2 người phê duyệt khác nhau** từ nhóm cho phép (Trưởng Phân xưởng + VP Block 1)
4. Phải nhập lý do cụ thể (tối thiểu 30 ký tự)
5. Hành động ghi vĩnh viễn vào Audit Trail với nhãn `EMERGENCY_OVERRIDE`

Hành động này được theo dõi — mục tiêu ≤ 3 lần/tháng. Lạm dụng sẽ ảnh hưởng điểm KPI và được báo cáo lên Ban Quản lý.

---

### Q3: Hệ thống báo "Chênh lệch lớn — bắt buộc nhập nguyên nhân" khi kiểm kê?

**Trả lời:** Khi chênh lệch giữa số đếm thực tế và số hệ thống vượt **5%** hoặc vượt **5.000.000 VND**, hệ thống yêu cầu:
- Nhập **Nguyên nhân** (dropdown: Hư hỏng / Mất mát / Sai nhập liệu / Hết hạn / Khác)
- Ghi **Ghi chú** chi tiết
- Đánh dấu **Cần CAPA** (tự động tick nếu vượt ngưỡng)

Sau khi Post kiểm kê, hệ thống tự tạo phiếu CAPA trong IMM-16 cho từng dòng chênh lệch lớn.

---

### Q4: Khi nào hệ thống gửi email cảnh báo?

**Trả lời:** Hệ thống gửi email tự động trong các tình huống:

| Tình huống | Người nhận | Thời điểm |
|---|---|---|
| Tồn kho dưới mức tối thiểu | Thủ kho + Trưởng Phân xưởng | Hàng ngày 02:00 |
| Critical Spare Watchlist bị vi phạm (breach) | Trưởng Phân xưởng + VP Block 1 + CMMS Admin | Hàng ngày 02:30 (tức thì nếu breach) |
| Phụ tùng sắp hết hạn (nếu bật Batch tracking) | Thủ kho | Hàng ngày 03:00 |
| Emergency Override được thực hiện | Trưởng Phân xưởng + VP Block 1 | Tức thì sau Override |

Nếu không nhận được email, kiểm tra với CMMS Admin về cấu hình email của tài khoản.

---

### Q5: Sự khác nhau giữa "Phụ tùng Critical" và "Watchlist Critical" là gì?

**Trả lời:**
- **Phụ tùng Critical** (`imm_part_class = Critical`): Phụ tùng được phân loại là quan trọng nhất về mặt giá trị và tầm quan trọng cho hoạt động thiết bị. Ví dụ: X-ray Tube, MRI Coil.
- **Watchlist Critical**: Quy tắc theo dõi cụ thể cho một cặp **Thiết bị + Phụ tùng** với mức tồn kho tối thiểu phải duy trì. Nếu tồn kho thực tế < mức tối thiểu → hệ thống báo động.

Một phụ tùng Critical có thể có nhiều Watchlist entries cho nhiều thiết bị khác nhau.

---

### Q6: Tại sao người Verify kiểm kê phải khác người Đếm?

**Trả lời:** Đây là yêu cầu phân quyền (VR-15-11) theo nguyên tắc **Segregation of Duties** của ISO 13485. Người đếm không được tự xác minh kết quả của mình để đảm bảo tính khách quan và tránh gian lận. Trưởng Phân xưởng hoặc QA Officer sẽ đóng vai trò người xác minh.

---

### Q7: "Dự báo nhu cầu phụ tùng" khác gì với "Dự báo nhu cầu mua sắm" (IMM-01)?

**Trả lời:**
- **Dự báo nhu cầu phụ tùng (IMM-15)** — cấp độ phụ tùng cụ thể (`IMM Spare Part Forecast`, mã `SFC-…`): Dự báo từng loại phụ tùng sẽ tiêu thụ bao nhiêu trong quý tới, từ đó đề xuất reorder point và safety stock. Phục vụ quản lý kho.
- **Dự báo nhu cầu mua sắm (IMM-01)** — cấp độ danh mục thiết bị (`IMM Demand Forecast`, mã `DF-…`): Dự báo nhu cầu mua sắm thiết bị mới cho kế hoạch năm. Phục vụ lập kế hoạch đầu tư.

Hai loại không liên quan và không thể gộp chung.

---

## §IV — Release Notes

### v1.0.0-rc.2 — Wave 2 sync (2026-05-14)

Sync cuối với branch `feature/hieuc/wave-2`. Tổng hợp các fix/optimize đã merge:

- **BE**: 21 endpoint trong `assetcore/api/imm15.py` đã wire qua wrapper `_handle()` envelope `{success, data}`. Service `assetcore/services/imm15.py` (~1270 dòng) phủ 6 service group (allocation, cycle count, forecast, watchlist, dashboard, alerts).
- **BE fix**: chỉnh `imm_spare_batch/imm_spare_batch.py` (controller validate). `api/imm00.py` sửa naming/gating helpers liên quan asset–spare linkage.
- **Hooks**: dùng namespace phẳng `assetcore.services.imm15.<fn>` (xem 04 §V). Scheduler: daily 4 jobs + monthly forecast + cron quarterly ABC.
- **Gate**: `IMM PM Work Order.before_submit` → `reserve_for_pm`; `IMM CM Work Order.before_submit` → `reserve_for_repair` (cùng tham gia gate IMM-16 `gate_wo_submit`).
- **FE**: `frontend/src/api/imm15.ts` + `frontend/src/stores/imm15.ts` (defineStore composition-API). 13 view files dưới `frontend/src/views/inventory/` đã LIVE. Router dùng path domain (`/inventory`, `/spare-parts`, `/stock-movements`, `/warehouses`).
- **Sidebar**: entry IMM-15 trong `MODULE_NAV` của `AppSidebar.vue`; tile trong `LauncherView.vue`.
- **Wave-2 housekeeping**: bỏ suffix `Store` ở filename (`imm15Store.ts` → `imm15.ts`), chuẩn hoá toast/error envelope, fix list-view loading/error states.

### v1.0.0 — original target

Tổng quan

IMM-15 v1.0.0 là lần phát hành đầu tiên của module **Theo dõi tồn kho phụ tùng y tế chiến lược**. Module này xây dựng trên nền tảng AC Inventory Backbone (Wave 1) đã hoạt động.

**Thời gian downtime deploy**: Dự kiến 2-4 giờ (00:00-06:00 ngày deploy).

### Tính năng mới

| # | Tính năng | Mô tả |
|---|---|---|
| F-01 | Phân hạng phụ tùng IMM | 7 Custom Fields mới trên AC Spare Part: Part Class, ABC, XYZ, Lead Time, Safety Stock, Traceability, Storage Condition |
| F-02 | Phiếu cấp phát phụ tùng | Workflow 6-state (Yêu cầu → Duyệt → Pick → Cấp → Trả → Hủy) bắt buộc link Work Order |
| F-03 | Cấp phát khẩn (Emergency Override) | Cơ chế bypass tồn kho với phê duyệt kép cho Critical spare |
| F-04 | Traceability bắt buộc | Enforce batch_no/serial_no khi Issue phụ tùng có `imm_traceability_required=1` |
| F-05 | Kiểm kê chu kỳ | Workflow 4-state với QR scan, variance auto-compute, CAPA auto-seed |
| F-06 | Critical Spare Watchlist | Breach detection hàng ngày + email khẩn + CAPA seed tự động |
| F-07 | Dự báo nhu cầu phụ tùng (part-level) | Snapshot quý với reorder recommendation |
| F-08 | Phân loại ABC/XYZ tự động | Scheduler hàng quý phân hạng theo consumption value |
| F-09 | Dashboard KPI tồn kho | 6 KPI + Consumption trend 90 ngày + realtime update |

### Cải tiến (so với trạng thái trước khi có IMM-15)

| Hạng mục | Trước | Sau |
|---|---|---|
| Tracking cấp phát phụ tùng | Thủ công (Excel) | Tự động qua workflow, link WO |
| Kiểm kê | Thủ công, không có audit | Hệ thống hóa, CAPA auto-seed |
| Cảnh báo tồn kho Critical | Email thủ công | Scheduler tự động hàng ngày |
| Dự báo tái đặt hàng | Không có | Forecast quý + reorder list |

### Breaking Changes

| # | Thay đổi | Ảnh hưởng | Mitigation |
|---|---|---|---|
| BC-01 | AC Stock Movement.reference_type mở rộng (Property Setter) | LIVE AC Stock Movement KHÔNG thay đổi data; chỉ thêm option mới | Patch v3_208 additive — backward compat |
| BC-02 | Patch v3_209 backfill `imm_part_class` từ `is_critical` | Spare part cũ có `is_critical=0` sẽ bị gán `Consumable` | Workshop Head review sau deploy; manual reclassify Major/Tool |

### Known Issues (v1.0.0)

| # | Issue | Priority | Workaround |
|---|---|---|---|
| KI-01 | `IMM Spare Batch` (batch/lot tracking) chưa build — scheduler `check_expiring_batches` là no-op | P2 | Dùng batch tracking thủ công của ERPNext nếu cần; Wave 3.1 build |
| KI-02 | Auto Material Request khi Approve forecast chưa có — chỉ hiển thị reorder list | P2 | Ops Manager tạo `AC Purchase` thủ công theo danh sách; Wave 3.1 automate |
| KI-03 | Mobile layout Cycle Count chưa optimize cho màn hình < 360px | P3 | Dùng tablet (≥ 768px) cho kiểm kê |

### Compatibility

| Thành phần | Version yêu cầu |
|---|---|
| Python | ≥ 3.11 |
| Frappe | 15.x |
| ERPNext | 15.x |
| MariaDB | ≥ 10.11 |
| Node.js | 18 LTS |
| Redis | ≥ 6.2 |
| AC Inventory Backbone | Wave 1 LIVE (bắt buộc) |

---

## §V — Traceability Matrix

### V.1 Ma trận truy nguyên

| ID | Loại | Mô tả | Doc ref | Design | Code | Test ID | UAT ID | Status |
|---|---|---|---|---|---|---|---|---|
| F-01 | FR | Spare master extension (7 CF) | Functional §1.1 | 04_Backend §II | `fixtures/imm15_custom_fields.json` | TestImm15ValidationRules | UAT-IMM15-01 | PLANNED |
| F-02 | FR | Critical Spare Watchlist | Functional §1.1 | 04_Backend §V.4 | `services/imm15.py:WatchlistService` | TestImm15WatchlistService | UAT-IMM15-07 | PLANNED |
| F-03 | FR | Allocation theo Work Order | Functional §1.1 | 04_Backend §V.1 | `services/imm15.py:AllocationService` | TestImm15AllocationService | UAT-IMM15-01,02 | PLANNED |
| F-04 | FR | Issue / Return QC gate | Functional §1.1 | 04_Backend §V.1 | `AllocationService.return_items` | TestImm15AllocationService.test_return_items_damaged | UAT-IMM15-05 | PLANNED |
| F-05 | FR | Cycle Count 4-state | Functional §1.1 | 04_Backend §V.2 | `services/imm15.py:CycleCountService` | TestImm15CycleCountService | UAT-IMM15-06 | PLANNED |
| F-06 | FR | Variance CAPA | Functional §1.1 | 02_Analysis §VII | `CycleCountService.post_cycle_count` | TestImm15CycleCountService.test_capa_seeded | UAT-IMM15-06 | PLANNED |
| F-07 | FR | Demand Forecast part-level | Functional §1.1 | 04_Backend §V.3 | `services/imm15.py:ForecastService` | TestImm15ForecastService | UAT-IMM15-08 | PLANNED |
| F-08 | FR | ABC/XYZ reclassification | Functional §1.1 | 04_Backend §VI | `tasks.reclassify_abc_xyz` | TestImm15ABCReclassification | UAT-IMM15-11 | PLANNED |
| F-09 | FR | Low-stock & Breach alert | Functional §1.1 | 04_Backend §VI | `tasks.check_low_stock_alerts`, `tasks.check_critical_spare_breach` | TestImm15WatchlistService | UAT-IMM15-07,11 | PLANNED |
| F-10 | FR | Emergency override dual-approval | Functional §1.1 | 02_Analysis §III | `AllocationService.issue_allocation` + override payload | TestImm15ValidationRules.test_vr15_10 | UAT-IMM15-04 | PLANNED |
| F-11 | FR | Traceability batch_no enforce | Functional §1.1 | 05_API §V impl note | `AllocationService._validate_traceability` | TestImm15ValidationRules.test_vr15_02 | UAT-IMM15-03 | PLANNED |
| F-12 | FR | Reorder recommendation | Functional §1.1 | 04_Backend §V.3 | `ForecastService.approve_forecast` | TestImm15ForecastService.test_approve | UAT-IMM15-08 | PLANNED |
| F-13 | FR | Dashboard KPI | Functional §1.1 | 06_Frontend §II.11 | `api/imm15.get_dashboard_stats` | TestImm15API.test_get_dashboard_kpis | UAT-IMM15-14 | PLANNED |
| F-14 | FR | Audit Trail | Functional §1.1 | 04_Backend §VIII | `AuditWriter.write` | TestImm15AuditTrail | UAT-IMM15-13 | PLANNED |
| BR-15-01 | BR | Allocation link WO (non-Emergency) | Functional §4 | 02_Analysis §VI | `AllocationService.create_allocation` validate | TestImm15ValidationRules.test_vr15_01 | UAT-IMM15-09 | PLANNED |
| BR-15-02 | BR | Traceability required | Functional §4 | 02_Analysis §VI | controller `before_submit` | TestImm15ValidationRules.test_vr15_02 | UAT-IMM15-03 | PLANNED |
| BR-15-03 | BR | Insufficient stock → throw / Emergency bypass | Functional §4 | 02_Analysis §VI | `AllocationService.issue_allocation` | TestImm15ValidationRules.test_vr15_03 | UAT-IMM15-04 | PLANNED |
| BR-15-04 | BR | Critical breach → CAPA + email | Functional §4 | 04_Backend §VI | `tasks.check_critical_spare_breach` | TestImm15WatchlistService.test_breach_seeds_capa | UAT-IMM15-07 | PLANNED |
| BR-15-05 | BR | Variance > 5% → CAPA + root_cause | Functional §4 | 02_Analysis §VI | `CycleCountService.finish_counting` | TestImm15ValidationRules.test_vr15_04 | UAT-IMM15-06 | PLANNED |
| BR-15-06 | BR | ABC reclassification quarterly | Functional §4 | 04_Backend §VI | `tasks.reclassify_abc_xyz` | TestImm15ABCReclassification | UAT-IMM15-11 | PLANNED |
| BR-15-07 | BR | Forecast Approved gate | Functional §4 | 04_Backend §V.3 | `ForecastService.approve_forecast` | TestImm15ForecastService.test_draft_no_mr | UAT-IMM15-08 | PLANNED |
| BR-15-08 | BR | Return QC gate (Damaged → QC Hold) | Functional §4 | 04_Backend §V.1 | `AllocationService.return_items` | TestImm15AllocationService.test_return_damaged | UAT-IMM15-05 | PLANNED |
| BR-15-09 | BR | Decommission obsolete review | Functional §4 | 04_Backend §VII | IMM-13 hook | (IMM-13 test) | — | PLANNED |
| BR-15-10 | BR | Audit trail mọi action | Functional §4 | 04_Backend §VIII | `AuditWriter.write` | TestImm15AuditTrail (7 tests) | UAT-IMM15-13 | PLANNED |
| VR-15-01 | VR | Allocation WO required | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-09 | PLANNED |
| VR-15-02 | VR | Traceability batch_no | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-03 | PLANNED |
| VR-15-03 | VR | Insufficient stock | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-09 | PLANNED |
| VR-15-04 | VR | Variance root_cause | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-06 | PLANNED |
| VR-15-05 | VR | Urgency enum | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-09 | PLANNED |
| VR-15-07 | VR | Reorder ≥ safety stock | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-08 | PLANNED |
| VR-15-08 | VR | qty_returned ≤ qty_issued | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-05 | PLANNED |
| VR-15-09 | VR | Watchlist Critical only | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-09 | PLANNED |
| VR-15-10 | VR | Emergency dual approver | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-04 | PLANNED |
| VR-15-11 | VR | verified_by ≠ counted_by | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-06 | PLANNED |
| VR-15-12 | VR | Forecast method whitelist | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-08 | PLANNED |
| VR-15-13 | VR | warehouse_from active | Functional §6 | 02_Analysis §VII | validate | unit test | UAT-IMM15-09 | PLANNED |
| NFR-15-01 | NFR | P95 list spare < 2s | Functional §7 | — | `list_spare_parts` | k6 load test | — | PLANNED |
| NFR-15-02 | NFR | P95 check_availability < 300ms | Functional §7 | — | `check_part_availability` | TestImm15API.test_check_p95 | — | PLANNED |
| NFR-15-03 | NFR | Concurrent issue atomic | Functional §7 | 04_Backend note | `services.inventory._upsert_stock` FOR UPDATE | k6 concurrency test | — | PLANNED |
| NFR-15-07 | NFR | Data retention ≥ 10 years | Functional §7 | 08_Deployment §II.3 | `imm15_audit_trail_retention_years` config | — | — | PLANNED |
| RULE-F01 | Arch | No duplicate AC Spare Part DocType | Module_Overview §9 | 04_Backend §I | fixture only | code review | — | PLANNED |
| RULE-F02 | Arch | No parallel stock table | Module_Overview §9 | 04_Backend §I | service layer | code review | — | PLANNED |
| RULE-F03 | Arch | All movements via AC Stock Movement | Module_Overview §9 | 04_Backend §I | `AllocationService`, `CycleCountService` | TestImm15AllocationService.test_creates_stock_movement | UAT-IMM15-02 | PLANNED |
| RULE-F04 | Arch | IMM DocType LINK only via stock_movement_ref | Module_Overview §9 | 04_Backend §I | all allocation/cycle services | code review | — | PLANNED |

### V.2 Coverage Summary

| Loại | Tổng | Có test/UAT | Coverage |
|---|---|---|---|
| FR (Feature) | 14 | 14 | 100% |
| BR (Business Rules) | 10 | 10 | 100% |
| VR (Validation Rules) | 13 | 13 | 100% |
| NFR | 12 | 4 (unit + k6) | 33% |
| Architecture Rules | 5 | 5 (code review) | 100% |

NFR coverage (33%) tăng lên khi có k6 load test chạy đủ trong CI/CD pipeline.

### V.3 Traceability Update Conventions

| Khi nào | Ai cập nhật | Cách cập nhật |
|---|---|---|
| Thêm feature mới | Dev + BA | Thêm dòng mới vào §V.1 |
| Thay đổi VR | Dev + BA | Cập nhật dòng VR tương ứng; bump version doc |
| Test fail → fix | Dev + QA | Cập nhật cột "Code", đổi Status từ PLANNED → DONE |
| UAT sign-off | QA Lead | Cập nhật cột "UAT ID" + Status → DONE |
| Release | Dev Lead | Cập nhật §IV Release Notes; tag git v1.x.0 |

---

## §VI — Keyboard Shortcuts & Tips

| Tình huống | Phím tắt / Mẹo |
|---|---|
| Cycle Count: chuyển sang dòng tiếp | Nhấn `Enter` sau khi nhập counted_qty |
| Cycle Count: quét QR phụ tùng | Dùng máy scan QR → tự chuyển đến đúng dòng |
| Tìm kiếm phụ tùng nhanh | Nhập mã OEM, item_code, hoặc tên trong ô tìm kiếm |
| Kiểm tra tồn kho khi tạo phiếu | Hệ thống tự kiểm tra (debounce 500ms) khi nhập item |
| Xem Audit Trail của phiếu | Click icon lịch sử (Frappe Version) ở góc phải form |

---

## §VII — Thông tin hỗ trợ

| Kênh | Liên hệ | Giờ hỗ trợ |
|---|---|---|
| Slack `#assetcore-support` | CMMS Admin | 07:00-18:00 |
| Email | cmms-admin@hospital.vn | Trong ngày |
| Điện thoại khẩn | Workshop Head on-call | 24/7 (Emergency override) |
| Bug report | GitHub Issues / Jira | Bất kỳ lúc nào |

---

*IMM-15 Module — Wave 2 IMPLEMENTED. Release & User Guide v1.0.0-rc.2. Cập nhật 2026-05-14.*
