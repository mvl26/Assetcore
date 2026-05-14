# Master Test Data — IMM-04 Sandbox & UAT
# Dữ liệu mẫu sẵn sàng nhập vào hệ thống AssetCore

**Phiên bản:** 1.0 | **Ngày:** 2026-04-15
**Mục đích:** Cung cấp bộ dữ liệu tham chiếu chuẩn để chạy test nội bộ (UT, INT) và hỗ trợ UAT.

---

## BẢNG 0 — DỮ LIỆU MASTER (Nhập trước, dùng chung cho mọi kịch bản)

### 0A. Item / Device Model

| Item Code | Item Name | Item Group | `custom_is_radiation` | Ghi chú |
|---|---|---|---|---|
| `VENT-PHL-V60` | Máy thở ICU Philips V60 | Medical Equipment | 0 | Không bức xạ |
| `XRAY-SIE-DR300` | Máy X-Quang Siemens DR300 | Medical Equipment | 1 | **Có bức xạ** |
| `US-GEN-LOGIQ` | Máy siêu âm GE Logiq E10 | Medical Equipment | 0 | Không bức xạ |
| `MON-DRE-V12` | Máy Monitor Drager Infinity V12 | Medical Equipment | 0 | Không bức xạ |
| `SYRIN-BBR-PERFUSOR` | Bơm tiêm điện BBraun Perfusor | Medical Equipment | 0 | Thiết bị class B |

### 0B. Supplier / Vendor

| Supplier Name | Supplier Group | Người liên hệ | Số điện thoại |
|---|---|---|---|
| Công ty TNHH Philips Việt Nam | Medical Equipment Supplier | Nguyễn Minh Khoa | 0901-234-567 |
| Công ty CP Siemens Healthineers VN | Medical Equipment Supplier | Trần Văn Hải | 0902-345-678 |
| Công ty TNHH GE Healthcare VN | Medical Equipment Supplier | Lê Thị Mai | 0903-456-789 |

### 0C. Department (Khoa/Phòng)

| Department Name | Ghi chú |
|---|---|
| Khoa Hồi Sức Tích Cực (ICU) | Phòng 301, Nhà A |
| Khoa Chẩn Đoán Hình Ảnh | Phòng X-Quang 1, Nhà B |
| Khoa Ngoại Tổng Hợp | Phòng 205, Nhà C |

### 0D. Purchase Order (Tạo trước khi nhập Commissioning)

| PO Name | Supplier | Item | Qty | Transaction Date |
|---|---|---|---|---|
| `PO-2026-0041` | Công ty TNHH Philips Việt Nam | `VENT-PHL-V60` | 1 | 2026-04-01 |
| `PO-2026-0042` | Công ty CP Siemens Healthineers VN | `XRAY-SIE-DR300` | 1 | 2026-04-03 |
| `PO-2026-0043` | Công ty TNHH GE Healthcare VN | `US-GEN-LOGIQ` | 1 | 2026-04-05 |
| `PO-2026-0044` | Công ty TNHH Philips Việt Nam | `MON-DRE-V12` | 2 | 2026-04-07 |
| `PO-2026-0045` | Công ty CP Siemens Healthineers VN | `SYRIN-BBR-PERFUSOR` | 1 | 2026-04-10 |

---

## KỊCH BẢN TC-01 — HAPPY PATH (Luồng Xanh Thần Thánh)

**Mục đích:** Xác nhận toàn bộ luồng chính chạy thông suốt từ Draft → Release → Asset.

### Thông tin chính

| Trường | Giá trị |
|---|---|
| **Commissioning ID** | `IMM04-26-04-00001` *(auto-generate)* |
| **PO Reference** | `PO-2026-0041` |
| **Model Thiết bị** | Máy thở ICU Philips V60 (`VENT-PHL-V60`) |
| **Nhà cung cấp** | Công ty TNHH Philips Việt Nam |
| **Khoa nhận** | Khoa Hồi Sức Tích Cực (ICU) |
| **Serial Hãng (NSX)** | `VNT-PHL-20260001` |
| **Ngày hẹn lắp** | 2026-04-17 |
| **Kỹ sư hãng** | Nguyễn Minh Khoa |
| **is_radiation** | Không (0) |
| **State khởi đầu** | `Draft` |

### Bảng kiểm Hồ sơ (Commissioning Document Record)

| Loại Tài liệu | Trạng thái | Bắt buộc? | File Đính kèm |
|---|---|---|---|
| CO (Chứng nhận Xuất xứ) | ✅ Received | Có | `CO_Philips_V60_Test.pdf` |
| CQ (Chứng nhận Chất lượng) | ✅ Received | Có | `CQ_Philips_V60_BYT_Test.pdf` |
| Catalog / Datasheet | ✅ Received | Không | `Catalog_V60.pdf` |
| Manual Bảo trì HDSD | ✅ Received | Không | `Manual_V60_VN.pdf` |

### Baseline Test Data (Commissioning Checklist)

| # | Thông số | Giá trị Đo được | Đơn vị | Kết quả |
|---|---|---|---|---|
| 1 | Điện trở tiếp địa | 0.28 | Ω | ✅ **Pass** (< 0.5 Ω) |
| 2 | Dòng rò điện máy | 1.1 | mA | ✅ **Pass** (< 2.0 mA) |
| 3 | Khởi động hệ điều hành | — | — | ✅ **Pass** |
| 4 | Hiệu chỉnh oxy (SpO2) | 98.5 | % | ✅ **Pass** (96–100%) |
| 5 | Báo động hết pin | — | — | ✅ **Pass** |

### Kết quả mong đợi

| Bước | Kết quả mong đợi |
|---|---|
| Sau Submit hồ sơ | State = `Pending_Doc_Verify` → chuyển `To_Be_Installed` không lỗi |
| Sau gắn tag QR | State = `Initial_Inspection`; `vendor_serial_no = VNT-PHL-20260001` |
| Sau điền Baseline (All Pass) | State cho phép chuyển sang `Clinical_Release` |
| Sau VP_Block2 Submit | **Asset `AST-2026-XXXXX` được tạo**, status `In Use`; `final_asset` có giá trị |

---

## KỊCH BẢN TC-02 — THIẾU HỒ SƠ (Doc Gate Failure)

**Mục đích:** Xác nhận hệ thống chặn đúng khi thiếu C/Q bắt buộc.

### Thông tin chính

| Trường | Giá trị |
|---|---|
| **PO Reference** | `PO-2026-0043` |
| **Model** | Máy siêu âm GE Logiq E10 (`US-GEN-LOGIQ`) |
| **Nhà cung cấp** | Công ty TNHH GE Healthcare VN |
| **Khoa nhận** | Khoa Ngoại Tổng Hợp |
| **State khởi đầu** | `Draft` |

### Bảng kiểm Hồ sơ — THIẾU CỐ TÌNH

| Loại Tài liệu | Trạng thái | Bắt buộc? |
|---|---|---|
| CO (Chứng nhận Xuất xứ) | ✅ Received | Có |
| CQ (Chứng nhận Chất lượng) | ❌ **Missing** | **Có — BẮT BUỘC** |
| Manual Bảo trì HDSD | ❌ Missing | Không |

### Kết quả mong đợi

| Bước | Kết quả mong đợi |
|---|---|
| Bấm "Gửi Duyệt Hồ Sơ" | ❌ **Lỗi đỏ VR-02:** "Không thể tiến hành bàn giao. Thiếu C/Q bắt buộc!" |
| State sau khi bị block | Giữ nguyên `Draft` — không chuyển được |
| Upload bổ sung C/Q → Submit lại | ✅ State chuyển sang `Pending_Doc_Verify` → tiếp tục bình thường |
| Thiếu Manual (non-mandatory) | ⚠️ Toast vàng VR-05 cảnh báo — KHÔNG block |

---

## KỊCH BẢN TC-03 — ĐIỀU KIỆN LẮP ĐẶT CHƯA ĐẠT (Site Gate Failure)

**Mục đích:** Xác nhận không thể bàn giao mặt bằng khi hạ tầng critical chưa đạt.

### Thông tin chính

| Trường | Giá trị |
|---|---|
| **PO Reference** | `PO-2026-0044` |
| **Model** | Máy Monitor Drager V12 (`MON-DRE-V12`) |
| **Khoa nhận** | Khoa Hồi Sức Tích Cực (ICU) |
| **State khởi đầu** | `To_Be_Installed` *(hồ sơ đã OK từ bước trước)* |

### Site Readiness Checklist — CỐ TÌNH FAIL 1 MỤC CRITICAL

| # | Hạng mục | Kết quả Đo | Kết quả | is_critical |
|---|---|---|---|---|
| 1 | Nguồn điện 220V ổn định | 223V | ✅ Pass | Có |
| 2 | Khí trung tâm (Air + O2) | Đủ áp | ✅ Pass | Có |
| 3 | Nhiệt độ phòng | 24°C | ✅ Pass | Không |
| 4 | **Nối đất tiếp địa** | **1.8 Ω** | ❌ **Fail** | **Có — CRITICAL** |
| 5 | Diện tích thoáng | 8m² | ✅ Pass | Không |

### Kết quả mong đợi

| Bước | Kết quả mong đợi |
|---|---|
| Bấm "Xác nhận Mặt bằng Đạt" | ❌ **Lỗi VR-06:** "Nối đất tiếp địa chưa đạt (1.8 Ω). Không thể bàn giao mặt bằng!" |
| State sau khi bị block | Giữ nguyên `To_Be_Installed` |
| Đội cơ điện sửa xong → đo lại 0.3 Ω → Submit lại | ✅ State chuyển sang `Installing` |

---

## KỊCH BẢN TC-04 — INSPECTION FAIL → MỞ NC (DOA Path)

**Mục đích:** Xác nhận hệ thống chặn Release và tạo NC khi test điện rớt.

### Thông tin chính

| Trường | Giá trị |
|---|---|
| **PO Reference** | `PO-2026-0042` |
| **Model** | Máy X-Quang Siemens DR300 (`XRAY-SIE-DR300`) |
| **Nhà cung cấp** | Công ty CP Siemens Healthineers VN |
| **Khoa nhận** | Khoa Chẩn Đoán Hình Ảnh |
| **Serial Hãng** | `XRY-SIE-20260001` |
| **is_radiation** | **Có (1)** |
| **State khởi đầu** | `Initial_Inspection` *(đã qua các gate trước)* |

### Baseline Test Data — CỐ TÌNH FAIL

| # | Thông số | Giá trị Đo được | Đơn vị | Kết quả | Ghi chú Fail |
|---|---|---|---|---|---|
| 1 | Điện trở tiếp địa | 0.35 | Ω | ✅ Pass | — |
| 2 | Dòng rò điện máy | **4.8** | mA | ❌ **Fail** | Vượt ngưỡng >2.0mA. Má nối đất nắp hông bị lỏng. KTS hãng đã được thông báo. |
| 3 | Bộ phát tia X — khởi động | — | — | ✅ Pass | — |
| 4 | Che chắn phóng xạ (phantom test) | 0.12 | mSv/h | ✅ Pass | < 0.5 mSv/h |

### Phiếu NC cần tạo (Asset QA Non Conformance)

| Trường | Giá trị |
|---|---|
| **NC ID** | `DOA-26-00014` *(auto)* |
| **ref_commissioning** | ID của phiếu IMM-04 trên |
| **nc_type** | `DOA` |
| **description** | Dòng rò điện 4.8mA vượt ngưỡng WHO (giới hạn 2.0mA). Má nối đất nắp hông bị lỏng. |
| **damage_proof** | *(Đính kèm ảnh chụp đầu kẹp nối đất)* |
| **resolution_status** | `Open` |

### Kịch bản bức xạ thêm: Clinical Hold

| Điều kiện | Hành động Mock Vòng 1 |
|---|---|
| `is_radiation = 1` và chưa có `qa_license_doc` | QA Officer tự bấm chuyển state → `Clinical_Hold` |
| Upload `Giấy_phep_Cuc_ATBXHN_SIE_DR300.pdf` | QA Officer bấm chuyển ra khỏi `Clinical_Hold` |

### Kết quả mong đợi

| Bước | Kết quả mong đợi |
|---|---|
| Điền Baseline với dòng 2 = Fail, không ghi Ghi chú | ❌ VR-03a block: "Bắt buộc ghi chú nguyên nhân" |
| Điền Ghi chú xong → Submit | ❌ VR-03b block: "Còn tiêu chí Fail — không thể Release" |
| State sau block | `Re_Inspection` (không phải Release) |
| Tạo NC DOA-26-00014 | NC record có status `Open` xuất hiện |
| Thử bấm Release khi NC đang Open | ❌ VR-04 block: "Còn NC chưa xử lý" |

---

## KỊCH BẢN TC-05 — RE-INSPECTION PASS → RELEASE (Full Rework Cycle)

**Mục đích:** Xác nhận chu trình Fail → Sửa → Re-test → Release hoàn chỉnh.

### Thông tin chính

*Tiếp nối từ TC-04 — cùng phiếu, sau khi kỹ sư Siemens siết lại má nối đất.*

| Trường | Giá trị |
|---|---|
| **Commissioning ID** | *(Cùng phiếu của TC-04)* |
| **State khởi đầu** | `Re_Inspection` |
| **Người thực hiện** | Biomed Engineer + Vendor Tech Siemens |

### Baseline Test Data Lần 2 (Re-inspection) — ALL PASS

| # | Thông số | Giá trị Đo LẦN 2 | Đơn vị | Kết quả |
|---|---|---|---|---|
| 1 | Điện trở tiếp địa | 0.22 | Ω | ✅ **Pass** |
| 2 | Dòng rò điện máy | **1.1** | mA | ✅ **Pass** (đã sửa — giảm từ 4.8 xuống 1.1) |
| 3 | Bộ phát tia X — khởi động | — | — | ✅ **Pass** |
| 4 | Che chắn phóng xạ (phantom test) | 0.10 | mSv/h | ✅ **Pass** |

### Cập nhật NC Before Release

| Trường NC | Giá trị Cập nhật |
|---|---|
| **resolution_status** | `Fixed` |
| **resolution_note** | Đã siết lại má nối đất nắp hông phải. Đo lại dòng rò: 1.1mA — đạt chuẩn WHO. |

### Kiểm tra Release Gate

| Điều kiện | Trạng thái |
|---|---|
| Tất cả Baseline Test Lần 2 = Pass | ✅ |
| NC DOA-26-00014 đã đóng (Fixed) | ✅ |
| Giấy phép Cục ATBXHN đã upload | ✅ *(Thực hiện ở TC-04 phần Hold)* |
| Không còn NC nào status = Open | ✅ |

### Hành động Release

| Actor | Hành động | Tool |
|---|---|---|
| VP Block2 (`phamvancuong`) | Đăng nhập, mở phiếu ở state `Clinical_Release` | ERPNext UI |
| VP Block2 | Kiểm tra tất cả điều kiện đã xanh → Bấm Submit | Workflow Action Button |
| System | Auto-tạo Asset | Server Hook `on_submit` |

### Kết quả mong đợi

| Bước | Kết quả mong đợi |
|---|---|
| Sau khi đóng NC và điền Baseline Lần 2 | Không còn thông báo lỗi VR-03, VR-04 |
| VP Block2 Submit | ✅ **Asset `AST-2026-XXXXX`** tạo ra với `status = In Use` |
| Về phiếu Commissioning | Field `final_asset` = `AST-2026-XXXXX` |
| Mở Asset vừa tạo | Có `custom_vendor_serial = XRY-SIE-20260001`; `custom_comm_ref` link về phiếu IMM-04 |
| Drill-down ngược | Click `custom_comm_ref` → mở phiếu gốc → click NC tab → thấy NC đã Fixed |

---

## BẢNG TỔNG HỢP 5 KỊCH BẢN

| ID | Tên Kịch bản | PO | Thiết bị | Serial | State Bắt đầu | KPI Rule Test | Kết quả Cuối |
|---|---|---|---|---|---|---|---|
| **TC-01** | Happy Path | PO-2026-0041 | Philips V60 | VNT-PHL-20260001 | Draft | Luồng xanh đầy đủ | ✅ Asset tạo thành công |
| **TC-02** | Thiếu C/Q | PO-2026-0043 | GE Logiq E10 | *(chưa gán)* | Draft | VR-02 Block | ❌ Blocked → ✅ sau khi bổ sung |
| **TC-03** | Site Gate Fail | PO-2026-0044 | Drager V12 | *(chưa gán)* | To_Be_Installed | VR-06 Block | ❌ Blocked → ✅ sau sửa tiếp địa |
| **TC-04** | Inspection Fail + NC | PO-2026-0042 | Siemens DR300 | XRY-SIE-20260001 | Initial_Inspection | VR-03 + VR-04 | ❌ Fail + NC Opened |
| **TC-05** | Re-inspection + Release | *(Tiếp TC-04)* | Siemens DR300 | XRY-SIE-20260001 | Re_Inspection | Check all gates | ✅ Asset tạo sau Release |

---

## GHI CHÚ NHẬP DỮ LIỆU VÀO SANDBOX

1. **Nhập theo thứ tự:** Item → Supplier → PO → Commissioning Form.
2. **File đính kèm:** Dùng PDF giả hoặc file ảnh bất kỳ để test; không cần file thật.
3. **Barcode Scanner:** Gõ tay Serial Number trong Sandbox (không cần súng thật ở vòng 1).
4. **Radiation Mock:** TC-04 — Vòng 1 chưa có Auto-Hold, QA Officer tự chuyển state.
5. **Mỗi kịch bản:** Nên thực hiện trên một phiếu riêng để tránh ảnh hưởng nhau.
