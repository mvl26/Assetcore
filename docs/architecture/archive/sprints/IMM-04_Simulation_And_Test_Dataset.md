# Master Test Dataset & Simulation Log - IMM-04
# Yêu cầu: Xác nhận chạy Simulation 5 Vòng đời Thực tế của Thiết bị

**Phiên bản:** 1.0 | **Ngày cập nhật:** 2026-04-15
**Hệ thống:** AssetCore v1.0
**Mục tiêu:** Data mẫu chuẩn hóa dùng tạo Simulation timeline, giám sát State Transitions, Event rẽ nhánh và lập bảng Log Expected vs Actual khi UAT.

---

## PHẦN 1. MASTER TEST DATASET (Dữ liệu Nhập Hệ thống)

Phải nhập đúng các Master Data này vào hệ thống trước khi bắt đầu Simulator.

### 1.1 Khởi tạo Model & Vendor & Department & PO
- **Models:**
  - `MDL-V60-01` (Máy thở ICU Philips V60) - Is_Radiation: `0`
  - `MDL-XRAY-02` (Máy X-Quang Siemens) - Is_Radiation: `1`
- **Vendors:**
  - `VND-PHL` (Philips VietNam)
  - `VND-SIE` (Siemens Healthineers)
- **Departments (Khoa nhận):** Khoa ICU, Khoa Chẩn đoán Hình ảnh.
- **Purchase Orders:**
  - `PO-2026-01` -> VND-PHL, MDL-V60-01 (Qty: 1)
  - `PO-2026-02` -> VND-SIE, MDL-XRAY-02 (Qty: 1)

### 1.2 Dữ liệu Giao dịch 5 Kịch bản (Scenarios Data)

| ID | Kịch Bản | Item Model | Vendor | PO Ref | Hồ sơ bàn giao nhập vào | Checklist Đo Baseline nhập vào | Serial quét giả định | Setup Ban đầu |
|---|---|---|---|---|---|---|---|---|
| **SC-01** | Happy Path | MDL-V60-01 | VND-PHL | PO-2026-01 | Đủ CO, CQ, HDSD | 5/5 Pass (Dòng rò: 1.1mA) | `SN-PHL-100` | Phiếu mới (Draft) |
| **SC-02** | Thiếu hồ sơ | MDL-V60-01 | VND-PHL | PO-2026-01 | Chỉ có CO, **Thiếu CQ** | (Chưa tới bước này) | (Chưa tới) | Phiếu mới (Draft) |
| **SC-03** | Lắp đặt fail | MDL-V60-01 | VND-PHL | PO-2026-01 | Đủ hồ sơ | CQ Mặt bằng: Tiếp địa fail (1.8Ω) | (Chưa tới) | State = `To_Be_Installed` |
| **SC-04** | Inspect Fail -> NC | MDL-XRAY-02 | VND-SIE | PO-2026-02 | Đủ hồ sơ | Dòng rò 4.5mA -> **Fail** | `SN-SIE-200` | State = `Identification` |
| **SC-05** | Re-inspect -> Pass | MDL-XRAY-02 | VND-SIE | PO-2026-02 | (Đã lưu) | Sửa lại -> Đo lần 2 dòng rò 1.5mA -> **Pass** | `SN-SIE-200` | State = `Re_Inspection` |

---

## PHẦN 2. TIMELINE SIMULATION (Mô phỏng sự kiện, Validation & Transitions)

### SC-01: Happy Path
- **[T=0]** HTM Tech tạo phiếu lưu Draft. Valid: Khớp thông tin PO.
- **[T=1]** Tick 3 file CO, CQ, HDSD. Nhấn Action: `Gửi Duyệt Hồ sơ`.
- **[T=1] Transition:** `Draft` ➔ `Pending_Doc_Verify`. Event: SLA time started.
- **[T=2]** Bấm duyệt hồ sơ ➔ `To_Be_Installed` ➔ Tick mặt bằng ➔ `Installing`.
- **[T=3]** Nhập Name Kỹ sư hãng báo xong ➔ `Identification`.
- **[T=4]** Quét Barcode `SN-PHL-100`. **Validation xảy ra:** VR-01 kiểm tra trùng serial toàn hệ thống (Passed -> Không trùng).
- **[T=4] Transition:** `Identification` ➔ `Initial_Inspection`. Quyền thao tác đẩy sang Biomed Engineer.
- **[T=5]** Biomed Tech điền 5 dòng Pass. Bấm Phát hành.
- **[T=5] Transition:** ➔ `Clinical_Release`. Quyền chuyển sang VP Block 2.
- **[T=6]** VP Block 2 bấm Phê duyệt. Màn hình báo Success.
- **[T=6] System Record Tạo:** Tài sản `AST-MDL-V60...` được mint tự động `(on_submit)`. Phiếu Lock = Submitted. Event `imm04.release.approved` phát ra.

### SC-02: Thiếu Hồ Sơ Bắt buộc (Validation Bắt Lỗi QMS)
- **[T=0]** HTM Tech nhập Draft. Chỉ đánh dấu đã nhận 'CO', bỏ sót/quên click 'CQ' (Dòng này set mandatory).
- **[T=1]** HTM bấm `Gửi Duyệt Hồ Sơ`.
- **[T=1] Validation Xảy ra:** Hàm `validate()` trigger → Chặn lại, hiển thị popup đỏ lỗi: `"Thiếu giấy tờ C/Q bắt buộc"`.
- **[T=1] Kịch bản kết thúc nhánh chặn:** State **giữ nguyên** `Draft`. Không có Event trigger.

### SC-04: Test Điện Rớt (Inspection Fail -> Tạo DOA NC)
- **[T=0]** Khởi điểm: Đã quét Barcode `SN-SIE-200`, State = `Initial_Inspection`. Máy này là *X-Ray có bức xạ*.
- **[T=1]** Biomed Tech điền dòng rò: 4.5 mA -> Chọn kết quả: `Fail`. Bỏ trống ghi chú.
- **[T=1] Validation:** Bấm Lưu, hệ thống **báo lỗi VR-03a** phải điền Ghi chú sửa chữa do chọn Fail.
- **[T=2]** Biomed Tech điền "Rò điện cực C, báo hãng đổi". Báo Lưu.
- **[T=2] Transition:** `Initial_Inspection` ➔ `Re_Inspection` (Không bay lên Clinical Release được).
- **[T=3] Tạo NC Record:** Biomed Tech bấm nút "Báo cáo DOA". Phiếu `Asset QA Non Conformance` (NC-001) được tạo với Status = `Open`.
- **[T=4] Validation (VR-07 Auto Hold Bức Xạ):** Máy X-Ray không có C/Q Bức xạ. Transition rẽ nhánh tự lưu lên `Clinical_Hold` chờ QA Risk Team upload bằng chứng.

### SC-05: Khắc phục & Re-Test Pass (Chuỗi Cứu Hộ Thiết Bị)
- **[T=0]** Tiếp tục SC-04. Kỹ sư Hãng đến thay linh kiện.
- **[T=1]** Biomed Tech mở phiếu NC-001. Điền "Đã đổi nguồn", chuyển Status = `Fixed`, Lưu. Đóng phiếu NC.
- **[T=2]** Biomed Tech quay lại phiếu IMM04 đang ở State `Re_Inspection`. Nhập kết quả Test lần 2 = 1.5mA (Pass).
- **[T=3]** Chọn Action: Gửi kết quả đánh giá lần 2.
- **[T=3] Validation Thực thi:**
  - Lưới Baseline Test: Không còn `Fail` ✅.
  - Check VR-04 (NC Open): Count số phiếu NC-Open = 0 ✅.
- **[T=3] Transition:** Phiếu nhảy vọt lên `Clinical_Release`.
- **[T=4]** VP Block 2 thực hiện Phê duyệt. Asset `AST-XRAY-02...` sinh ra.

---

## PHẦN 3. ĐIỂM DỄ FAIL & ĐIỂM CẦN CHÚ Ý KHI TEST

| Cụm Test | Rủi ro (Điểm dễ Fail) | Cảnh báo khi Thực thi Simulator |
|---|---|---|
| **Barcode (VR-01)** | KTV gõ tay quá êm, cố tình thay 1 kit ký tự dẫn đến Serial trên tem <> Hệ thống | Phải ép sử dụng Barcode Scanner bằng client script khóa Typing. Test thử = copy paste mã thật. |
| **Checklist (VR-03)**| Lưới con (Child Table) bị rỗng. Cứ lưu phứa là trôi state | Cố gắng submit 1 test row rỗng để kiểm chứng nó throw exception Block đúng không. |
| **Quyền Admin (A7)** | Account Admin nhảy vào override state | Cần log out User Full Quyền, giả lập đúng Login của HTM Tech để thử. |
| **Asset Minting** | Server chạy Transaction tạo Asset nhưng mạng rớt -> Data lơ lửng | Test crash internet. Hệ thống Frappe sẽ dùng SQL Rollback, đảm bảo Commissioning Form không báo Submit nếu Asset không Create. |

---

## PHẦN 4. TEMPLATE EXPECTED VS ACTUAL (Mẫu in ra khi ký UAT)

**Tên Kịch Bản TEST:** ________________________ | **Tester:** ___________________

| Test Step (Hành động) | Expected Result (Cần phải thế này) | Actual Result (Chữ ký & Note mộc) | Tình trạng (P/F) |
|---|---|---|---|
| 1. Bỏ trống file hồ sơ C/Q và bấm Submit | Lỗi đỏ báo chặn ở ngay State Draft / Không lên state tiếp | ______________________________ | [ ] |
| 2. Nhập trùng Serial Number `SN-PHL-100` lần 2 | Văng popup "Trùng thiết bị đã nhập tại phiếu..." | ______________________________ | [ ] |
| 3. Cho Test Fail 1 dòng và quên nhập note | Hệ thống chặn không cho Save form (Bôi đỏ dòng Fail) | ______________________________ | [ ] |
| 4. Bỏ qua NC (đang Open) mà bấm nút Approved Release (Account Lãnh đạo) | Hệ thống throw error "Không Release được vì còn NC mở" | ______________________________ | [ ] |
| 5. Chạy đúng Luồng xanh và Submit bằng VP Block 2 | Phiếu khóa (Submitted), tài sản Asset mã AST... sinh ra | ______________________________ | [ ] |

*Ghi chú Issue phát sinh ngoài kịch bản:*
......................................................................................................................................................
......................................................................................................................................................
 
*Sign-off Tester: .......................... | Sign-off QA: ..........................*
