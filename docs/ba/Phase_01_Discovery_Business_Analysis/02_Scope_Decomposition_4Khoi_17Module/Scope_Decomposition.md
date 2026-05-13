> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# SCOPE DECOMPOSITION — 4 KHỐI / 17 MODULE IMM

**Phiên bản:** 1.0
**Owner:** BA Lead
**Tham chiếu:** IMMIS CH1, AssetCore Blueprint

---

## Cấu trúc cho mỗi module

Mỗi module được mô tả theo 6 trường:
1. **Mục tiêu vận hành**
2. **Actor chính**
3. **Record nguồn** (input)
4. **Record phát sinh** (output)
5. **Liên kết upstream / downstream**
6. **Wave**

---

## KHỐI A — PLANNING & PROCUREMENT

### IMM-01 — Đánh giá nhu cầu và dự toán
- **Mục tiêu:** Ghi nhận và đánh giá có hệ thống nhu cầu đầu tư thiết bị từ khoa lâm sàng/cơ quan quản lý; ước lượng dự toán; lập kế hoạch đầu tư.
- **Actor:** Trưởng khoa lâm sàng (đề xuất), Trưởng VTTBYT, Phòng KHTH, Phòng KTTC, BGĐ.
- **Record nguồn:** Bản đề xuất nhu cầu khoa, định mức kỹ thuật, kế hoạch chiến lược BV.
- **Record phát sinh:** `AC Need Assessment`, `AC Lifecycle Event: need_registered`, kế hoạch đầu tư thường niên.
- **Liên kết:** Upstream — kế hoạch BV. Downstream — IMM-02 spec build.
- **Wave:** 2.

### IMM-02 — Thông số kỹ thuật và phân tích thị trường
- **Mục tiêu:** Xây dựng spec kỹ thuật chuẩn cho từng thiết bị/lô; quét thị trường; đánh giá khả thi kỹ thuật và tài chính.
- **Actor:** Kỹ sư BME, BA thiết bị, Phòng VTTBYT, Vendor được mời.
- **Record nguồn:** Need Assessment (IMM-01), spec mẫu, khảo sát thị trường.
- **Record phát sinh:** `AC Technical Specification`, `AC Market Scan`, hồ sơ chuẩn bị mời thầu.
- **Liên kết:** Upstream IMM-01. Downstream IMM-03.
- **Wave:** 2.

### IMM-03 — Đánh giá NCC và quyết định mua sắm
- **Mục tiêu:** Lựa chọn vendor; quyết định mua sắm; tạo Purchase Order trên ERPNext.
- **Actor:** Phòng VTTBYT, Phòng KTTC, BGĐ, Hội đồng đấu thầu, Pháp chế.
- **Record nguồn:** Spec (IMM-02), hồ sơ vendor, báo giá.
- **Record phát sinh:** `AC Vendor Evaluation`, `AC Procurement Decision`, **ERPNext Purchase Order**, `AC Lifecycle Event: procurement_approved`.
- **Liên kết:** Downstream — IMM-04 (sau khi nhận hàng).
- **Wave:** 2.

---

## KHỐI B — DEPLOYMENT & IMPLEMENTATION

### IMM-04 — Lắp đặt, định danh và kiểm tra ban đầu **[WAVE 1]**
- **Mục tiêu:** Tiếp nhận hàng → lắp đặt → định danh (mã, QR, RFID) → IQ/OQ/PQ → đưa vào registry.
- **Actor:** Vendor (lắp đặt), Kỹ sư BME, KTV thiết bị, Trưởng khoa nhận, QMS Officer (IQ/OQ/PQ).
- **Record nguồn:** ERPNext Purchase Receipt, Procurement Decision, manual thiết bị.
- **Record phát sinh:** `AC Medical Asset` (1 record/thiết bị), `AC Asset Identifier`, `AC Installation Record`, `AC IQ/OQ/PQ Record`, `AC Lifecycle Event: installed`, `commissioned`.
- **Liên kết:** Upstream IMM-03 / Purchase Receipt. Downstream IMM-05 + IMM-06.
- **Wave:** **1**.

### IMM-05 — Đăng ký, cấp phép và hồ sơ **[WAVE 1]**
- **Mục tiêu:** Quản lý hồ sơ pháp lý, giấy phép lưu hành, chứng nhận CE/FDA, đăng ký nội bộ; theo dõi hạn dùng.
- **Actor:** Phòng VTTBYT, Pháp chế, QMS Officer.
- **Record nguồn:** Tài liệu pháp lý vendor, thông báo Bộ Y tế.
- **Record phát sinh:** `AC Document Record` (license/certification), gắn vào `AC Medical Asset`; `AC Lifecycle Event: license_registered`.
- **Liên kết:** Upstream IMM-04. Downstream IMM-06 (release-for-use).
- **Wave:** **1**.

### IMM-06 — Đào tạo người dùng
- **Mục tiêu:** Tổ chức đào tạo người dùng; ghi competency; release-for-use.
- **Actor:** Vendor trainer, QMS Officer, Trưởng khoa lâm sàng, KTV.
- **Record nguồn:** Manual, training plan vendor, kế hoạch đào tạo BV.
- **Record phát sinh:** `AC Training Session`, `AC Training Attendance`, `AC Competency Assessment`, `AC Lifecycle Event: released_for_use`.
- **Liên kết:** Upstream IMM-05. Downstream IMM-07/08.
- **Wave:** 2 (release-for-use logic được nối Wave 1 nhưng training catalog ở Wave 2).

---

## KHỐI C — OPERATIONS & MAINTENANCE

### IMM-07 — Theo dõi hiệu suất
- **Mục tiêu:** Đo uptime, utilization, performance index; chỉ ra thiết bị bất thường.
- **Actor:** Trưởng VTTBYT, Trưởng khoa, Phòng KHTH.
- **Record nguồn:** Work Order, Downtime, Utilization log (HIS/IoT nếu có).
- **Record phát sinh:** Metric snapshot, `AC Performance Alert`.
- **Liên kết:** Cross-cut với IMM-08/09/12.
- **Wave:** 2.

### IMM-08 — Bảo trì định kỳ (PM) **[WAVE 1]**
- **Mục tiêu:** Lập PM Plan; tự động sinh WO theo lịch; thực hiện; validate; đóng PM.
- **Actor:** Kỹ sư BME, KTV, Vendor service engineer (theo hợp đồng), QMS Officer (validate).
- **Record nguồn:** Manual, vendor manual, contract.
- **Record phát sinh:** `AC PM Plan`, `AC Work Order` (type=PM), `AC Lifecycle Event: pm_completed`.
- **Liên kết:** Downstream — IMM-12 nếu phát hiện hỏng trong PM.
- **Wave:** **1**.

### IMM-09 — Sửa chữa, phụ tùng và cập nhật phần mềm **[WAVE 1]**
- **Mục tiêu:** Quản lý sửa chữa thực tế, tiêu thụ phụ tùng, cập nhật firmware/software.
- **Actor:** Kỹ sư BME, KTV, Vendor SE, kho phụ tùng.
- **Record nguồn:** WO type CM, hợp đồng cung cấp phụ tùng.
- **Record phát sinh:** `AC Work Order Spare Item`, **ERPNext Stock Entry**, `AC Software Update Record`.
- **Liên kết:** Cross-cut WO Engine.
- **Wave:** **1**.

### IMM-10 — Hậu kiểm và tuân thủ
- **Mục tiêu:** Theo dõi adverse event, vigilance, post-market surveillance, kiểm tra tuân thủ định kỳ.
- **Actor:** QMS Officer, Trưởng VTTBYT, Pháp chế, BGĐ.
- **Record nguồn:** Báo cáo sự cố, kiểm tra Bộ Y tế, recall vendor.
- **Record phát sinh:** `AC Compliance Case`, `AC CAPA`, `AC Lifecycle Event: recalled` (nếu).
- **Liên kết:** Cross-cut với CAPA Engine.
- **Wave:** 2.

### IMM-11 — Hiệu năng và hiệu chuẩn **[WAVE 1]**
- **Mục tiêu:** Quản lý chu kỳ hiệu chuẩn nội bộ/external; lưu certificate.
- **Actor:** Calibration Lab Engineer, Vendor calibration, QMS Officer.
- **Record nguồn:** Manual, tiêu chuẩn IEC/ISO.
- **Record phát sinh:** `AC Calibration Plan`, `AC Calibration Record`, `AC Calibration Certificate` (Document), `AC Lifecycle Event: calibrated`.
- **Liên kết:** Cross-cut WO Engine.
- **Wave:** **1**.

### IMM-12 — Bảo trì khắc phục (CM) **[WAVE 1]**
- **Mục tiêu:** Xử lý báo hỏng, sửa chữa, đóng case, root cause, gắn CAPA nếu cần.
- **Actor:** Người báo hỏng (BS/ĐD/KTV), Kỹ sư BME, KTV, Vendor SE.
- **Record nguồn:** Failure report (qua mobile/web/Zalo bot).
- **Record phát sinh:** `AC Failure Report`, `AC Work Order` (type=CM), `AC Downtime Record`, `AC Root Cause`, `AC Lifecycle Event: failure_reported`, `repaired`.
- **Liên kết:** Downstream IMM-09 phụ tùng; có thể trigger IMM-13 nếu nặng.
- **Wave:** **1**.

### IMM-15 — Theo dõi tồn kho phụ tùng
- **Mục tiêu:** Quản lý spare master, tồn kho, reorder; gắn với BOM thiết bị.
- **Actor:** Kho phụ tùng, Kỹ sư BME, mua hàng.
- **Record nguồn:** ERPNext Stock + custom spare master.
- **Record phát sinh:** `AC Spare Part`, ERPNext Stock Entry, ERPNext Reorder.
- **Liên kết:** Tích hợp ERPNext Stock module.
- **Wave:** 2.

### IMM-16 — Theo dõi tuân thủ
- **Mục tiêu:** Dashboard giấy phép sắp hết hạn, PM/Cal quá hạn, training quá hạn, recall hot.
- **Actor:** QMS Officer, Trưởng VTTBYT, BGĐ.
- **Record nguồn:** Tổng hợp từ Document, WO, CAPA, Lifecycle Event.
- **Record phát sinh:** Dashboard snapshot, alert.
- **Liên kết:** Cross-cut với Metric Engine.
- **Wave:** 2.

### IMM-17 — Phân tích dự đoán
- **Mục tiêu:** Dự đoán failure, chu kỳ PM tối ưu, optimization phụ tùng.
- **Actor:** Data Scientist (BV / Vendor), Trưởng VTTBYT.
- **Record nguồn:** WO history, telemetry, environment.
- **Record phát sinh:** Predictive metric, anomaly alert.
- **Wave:** 3.

---

## KHỐI D — END-OF-LIFE MANAGEMENT

### IMM-13 — Ngừng sử dụng và điều chuyển
- **Mục tiêu:** Stand-down (tạm ngưng), điều chuyển giữa khoa/site.
- **Actor:** Trưởng VTTBYT, Trưởng khoa cũ/mới, Kế toán tài sản.
- **Record nguồn:** Quyết định điều chuyển, biên bản đánh giá.
- **Record phát sinh:** `AC Asset Movement`, `AC Lifecycle Event: stand_down` / `transferred`.
- **Liên kết:** Cập nhật location/custodian; đồng bộ ERPNext Asset.
- **Wave:** 2.

### IMM-14 — Giải nhiệm thiết bị
- **Mục tiêu:** Quyết định giải nhiệm, xử lý thanh lý/donation/destruction; closeout regulatory.
- **Actor:** Trưởng VTTBYT, Phòng KTTC, Pháp chế, QMS Officer.
- **Record nguồn:** Đánh giá kỹ thuật, hết hạn sử dụng, không tuân thủ.
- **Record phát sinh:** `AC Decommission Record`, `AC Disposal Record`, `AC Lifecycle Event: retired`, `disposed`; ERPNext Asset Disposal.
- **Wave:** 2.

---

## Ma trận liên kết module

| Module | Phụ thuộc upstream | Cung cấp xuôi | Wave |
|--------|-------------------|---------------|------|
| IMM-01 | – | IMM-02 | 2 |
| IMM-02 | IMM-01 | IMM-03 | 2 |
| IMM-03 | IMM-02 | IMM-04 (qua PR) | 2 |
| IMM-04 | IMM-03 / PR | IMM-05, IMM-06 | **1** |
| IMM-05 | IMM-04 | IMM-06, IMM-16 | **1** |
| IMM-06 | IMM-05 | release_for_use | 2 |
| IMM-07 | WO history | dashboard | 2 |
| IMM-08 | Asset+Manual | IMM-12 nếu fail | **1** |
| IMM-09 | IMM-12 / IMM-08 | Stock | **1** |
| IMM-10 | Asset, alerts | CAPA | 2 |
| IMM-11 | Asset+Standard | Cert | **1** |
| IMM-12 | Failure report | IMM-09 | **1** |
| IMM-13 | Asset | Movement | 2 |
| IMM-14 | Asset | Disposal | 2 |
| IMM-15 | WO + BOM | Stock | 2 |
| IMM-16 | Doc, WO, CAPA | Dashboard | 2 |
| IMM-17 | History | Predictive | 3 |

## Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| BA Lead |  |  |
| SA Lead |  |  |
| Trưởng VTTBYT |  |  |
| QMS Lead |  |  |
