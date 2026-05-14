# HỒ SƠ NGHIỆM THU MODULE IMM-04
# Hệ thống: AssetCore / IMMIS
# Phân hệ: IMM-04 — Lắp đặt, Định danh và Kiểm tra Ban đầu Thiết bị Y tế

---

**Mã hồ sơ:** ASSETCORE-IMM04-ACCEPT-v1.0
**Ngày ban hành:** 2026-04-15
**Phiên bản hệ thống:** AssetCore v1.0
**Trạng thái:** ☐ Dự thảo &nbsp;&nbsp; ☐ Đang xem xét &nbsp;&nbsp; ☐ **Đã phê duyệt**

---

## MỤC LỤC

1. Tóm tắt Module
2. Workflow & State Machine
3. Danh sách DocType
4. Permission Matrix
5. Rule Engine
6. Test Case
7. UAT Script (Tóm tắt)
8. Traceability Matrix
9. QMS Compliance Check
10. Open Issues (Vấn đề còn mở)
11. Bảng Ký Duyệt

---

## 1. TÓM TẮT MODULE

### 1.1 Mục tiêu
Module IMM-04 kiểm soát toàn bộ quá trình "nhập tịch" thiết bị y tế: từ thời điểm thiết bị tiếp cận chân công trình tại bệnh viện cho đến khi được gán định danh đa lớp, vượt qua kiểm định an toàn kỹ thuật và chính thức được phép đưa vào phục vụ lâm sàng.

**Nguyên tắc cốt lõi:** Không một thiết bị nào được sinh ra trong hệ thống tài sản (Asset) nếu chưa trải qua cổng kiểm định IMM-04. Mọi nỗ lực tạo Asset trực tiếp đều bị chặn hệ thống.

### 1.2 Phạm vi
| Ranh giới | Chi tiết |
|---|---|
| **Bắt đầu** | Thiết bị đến chân công trình, PO đã hoàn tất |
| **Kết thúc** | Asset chính thức được tạo với trạng thái `In Use` trên ERPNext |
| **Giao với IMM-03** | Nhận Signal từ Kho: hàng đã rời kho trung tâm |
| **Giao với IMM-05** | Baseline test data được truyền sang làm chuẩn bảo trì |
| **Giao với IMM-08** | Nếu DOA vĩnh viễn, trigger luồng Thanh lý |

### 1.3 Thành phần chính
- **3 DocType tùy chỉnh** (Custom)
- **11 Workflow States**
- **8 Business Events** (3 Immutable)
- **8 Validation Rules** (VR-01 → VR-08)
- **25 Requirements** được truy xuất đầy đủ

---

## 2. WORKFLOW & STATE MACHINE

### 2.1 Danh sách Trạng thái

| Mã State | Tên Trạng thái | Loại | Tác nhân chịu trách nhiệm |
|---|---|---|---|
| `S01` | Draft | Khởi tạo | HTM Technician |
| `S02` | Pending_Doc_Verify | Gate kiểm soát | HTM Technician |
| `S03` | To_Be_Installed | Chờ | Vendor Technician |
| `S04` | Installing | Vận hành | Vendor Technician |
| `S05` | Identification | Định danh | Biomed Engineer |
| `S06` | Initial_Inspection | Gate QA | Biomed Engineer |
| `S07` | Non_Conformance | Ngoại lệ | Biomed Eng / Vendor |
| `S08` | Clinical_Hold | Đóng băng | QA Officer |
| `S09` | Re_Inspection | Tái thẩm định | Biomed Engineer |
| `S10` | Clinical_Release_Success | Terminal ✅ | VP_Block2 |
| `S11` | Return_To_Vendor | Terminal ❌ | VP_Block2 / Board |

### 2.2 State Machine Chính (Luồng xanh)
```
Draft → Pending_Doc_Verify → To_Be_Installed → Installing
      → Identification → Initial_Inspection → Clinical_Release_Success
```

### 2.3 Luồng Ngoại lệ
```
Any State → Non_Conformance → (Fix) → Installing / Re_Inspection
Initial_Inspection → Re_Inspection → Clinical_Release_Success
Initial_Inspection → Clinical_Hold → (Upload License) → Clinical_Release_Success
Non_Conformance → Return_To_Vendor  [TERMINAL]
```

### 2.4 Cổng kiểm soát (Gates)
| Gate | Tại Node | Điều kiện tối thiểu |
|---|---|---|
| **Doc Gate** | `Pending_Doc_Verify` | CO + CQ đã nhận (mandatory) |
| **Site Gate** | `To_Be_Installed` | Mọi điều kiện hạ tầng critical = Đạt |
| **QA Gate** | `Initial_Inspection` | Tất cả Baseline Test = Pass |
| **Hold Gate** | `Clinical_Hold` | Upload giấy phép Cục ATBXHN |
| **Release Gate** | `Clinical_Release_Success` | Không còn NC Open + Board/VP ký duyệt |

---

## 3. DANH SÁCH DOCTYPE

| # | Tên DocType | Technical Name | Loại | Submittable |
|---|---|---|---|---|
| 1 | Asset Commissioning Process | `asset_commissioning` | Custom — Lõi IMM-04 | **Có** |
| 2 | Commissioning Checklist | `commissioning_checklist` | Custom — Child Table | Không |
| 3 | Asset QA Non Conformance | `asset_qa_nc` | Custom — Độc lập | **Có** |
| 4 | Asset *(mở rộng)* | `asset` | ERPNext Core + Custom Fields | Có (Core) |

### Fields mở rộng thêm vào Core `Asset`
| Field | Label | Mục đích |
|---|---|---|
| `custom_vendor_sn` | Serial Hãng | Định danh lớp 2 |
| `custom_internal_qr` | QR Nội bộ BV | Định danh lớp 1 |
| `custom_comm_ref` | Link về phiếu Commissioning | Khóa Traceability ngược |

---

## 4. PERMISSION MATRIX

| Actor | Read | Create | Edit | Submit | Cancel | Amend | Ghi chú |
|---|---|---|---|---|---|---|---|
| `HTM Technician` | ✅ | ✅ | ✅ (giới hạn node) | ❌ | ❌ | ❌ | Không được tự approve |
| `Biomed Engineer` | ✅ | ❌ | ✅ (Baseline, Tags) | ❌ | ❌ | ❌ | Write chỉ ở node test |
| `VP_Block2` | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | Quyền phát hành tối cao |
| `QA_Risk_Team` | ✅ | ❌ | ✅ (License only) | ❌ | ❌ | ❌ | Gỡ Clinical Hold |
| `Workshop Head` | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | Rút, sửa, Amend |
| `Vendor Tech` | ✅ | ❌ | ✅ (node Installing) | ❌ | ❌ | ❌ | Portal access |
| `CMMS Admin` | ✅ | ❌ | ✅ (debug) | ❌ | ❌ | ❌ | Không bypass business rules |

**Field-level restriction đặc biệt:**
- `final_asset`: Read-only tuyệt đối — chỉ System ghi
- `is_radiation_device`: Read-only với mọi role trừ Admin
- `damage_proof`: Bắt buộc (reqd) khi NC type = DOA

---

## 5. RULE ENGINE (Tóm tắt)

| Mã | Mô tả | Loại | Tầng | Hành động khi Fail |
|---|---|---|---|---|
| VR-01 | Serial Number phải duy nhất toàn hệ thống | Hard | Server | `frappe.throw` — Block Save |
| VR-02 | CO, CQ bắt buộc trước khi bàn giao | Hard | Workflow | Block Transition |
| VR-03a | Ghi chú bắt buộc khi tiêu chí Fail | Hard | Server | Block Save |
| VR-03b | Không Release nếu còn Fail trong Grid | Hard | Server | Force → Re_Inspection |
| VR-04 | Không Release nếu còn NC Open | Hard | Server | `frappe.throw` — Block Submit |
| VR-05 | Cảnh báo thiếu Manual HDSD | Soft | Client | Toast màu vàng |
| VR-06 | Không lắp nếu điều kiện hạ tầng Failed | Hard | Workflow | Block Transition |
| VR-07 | Auto-Hold máy bức xạ | Auto | Server | Force → Clinical_Hold |
| VR-08 | Bắt buộc quét Barcode, không nhập tay Serial | Hard | Client | Keyboard lock |

---

## 6. TEST CASE (Tóm tắt)

| Nhóm | Số lượng | Trạng thái |
|---|---|---|
| Unit Test | 3 | Cần chạy sau khi code xong |
| Integration Test | 2 | Cần môi trường staging đầy đủ |
| UAT | 10 | Cần người dùng thực tế thực hiện |
| **Tổng** | **15** | — |

**Test cases bắt buộc PASS trước nghiệm thu:**

| ID | Tình huống kiểm tra |
|---|---|
| UT-01 | Chặn trùng Serial Number |
| UT-02 | Chặn Release khi thiếu giấy phép bức xạ |
| UT-03 | Bắt buộc ghi chú khi Baseline Fail |
| INT-01 | Luồng xanh đầy đủ từ nhận hàng → tạo Asset |
| INT-02 | Luồng DOA → Return Vendor |
| UAT-K2-01 | VP_Block2 không Release được máy Fail |
| UAT-K2-02 | Không tạo Asset tay trên Core |
| UAT-TM-01 | KTV Lách luật thiếu C/Q bị chặn |
| UAT-TM-02 | Không sửa được dữ liệu sau Submit |
| UAT-WS-01 | Workshop Head bị chặn khi còn NC Open |

---

## 7. UAT SCRIPT (Tóm tắt kết quả)

| Kịch bản | Actors | Số Test Steps | Kết quả |
|---|---|---|---|
| KB01 — Tiếp nhận & Hồ sơ | KTV HTM | 5 | ☐ |
| KB02 — Mặt bằng Lắp đặt | Biomed Eng + Clinical Head | 4 | ☐ |
| KB03 — Lắp đặt & Định danh | Vendor Tech | 4 | ☐ |
| KB04 — Kiểm tra an toàn | Biomed Eng | 5 | ☐ |
| KB05 — Phê duyệt Phát hành | VP_Block2 | 4 | ☐ |
| KB06 — Thiết bị Bức xạ | KTV + QA | 3 | ☐ |
| **Tổng** | | **25** | ☐ |

*Chi tiết từng bước xem tại: `docs/sprints/IMM-04_UAT_Script.md`*

---

## 8. TRACEABILITY MATRIX (Tóm tắt)

| Chỉ số | Giá trị |
|---|---|
| Tổng số Requirements | 25 |
| Fully Covered ✅ | 18 (72%) |
| Partial Coverage ⚠️ | 7 (28%) |
| Gap ❌ | 0 (0%) |

**7 Requirements PARTIAL cần hoàn thiện trước Go-Live:**

| REQ ID | Nội dung còn thiếu |
|---|---|
| REQ-09 | Test case cho `custom_moh_code` |
| REQ-20 | Server-side guard chống tạo Asset tay |
| REQ-21 | Test case verify Audit Trail Lock |
| REQ-22 | Report Query KPI Avg Time to Release |
| REQ-23 | Dashboard Widget "Active Hold" |
| REQ-25 | Test case kịch bản Cronjob quá hạn |

*Chi tiết xem tại: `docs/sprints/IMM-04_Traceability_Matrix.md`*

---

## 9. QMS COMPLIANCE CHECK

| # | Hạng mục | Kết quả | Mức độ |
|---|---|---|---|
| 1 | Audit Trail | ⚠️ Partial | Medium |
| 2 | Approval Matrix | ⚠️ Partial | Medium |
| 3 | Change Control | ⚠️ Partial | Medium |
| 4 | Digital Evidence | ⚠️ Partial | Medium |
| 5 | Traceability Dashboard→Record | ⚠️ Partial | Low |
| **6** | **Role-Based Access Control** | **❌ FAIL** | **🚨 CRITICAL** |
| 7 | Post-Submit Data Integrity | ⚠️ Partial | Medium |

**Kết luận QMS:** ❌ Chưa đủ điều kiện Go-Live

*Chi tiết xem tại: `docs/compliance/IMM-04_QMS_Audit_Report.md`*

---

## 10. OPEN ISSUES (Vấn đề còn mở)

| # | Mã Action | Mô tả | Mức | Owner | Hạn |
|---|---|---|---|---|---|
| 1 | **A7 🚨** | **Khóa field `is_radiation` với role thường — GO-LIVE BLOCKER** | Critical | Dev Lead | Sprint 2 |
| 2 | A1 | Capture IP Address trong Event Payload | Medium | Backend Dev | Sprint 2 |
| 3 | A2 | Hook audit log khi Vendor đổi `installation_date` | Medium | Backend Dev | Sprint 2 |
| 4 | A3 | Thêm field `amend_reason` bắt buộc | Medium | Backend Dev | Sprint 2 |
| 5 | A4 | Custom hook track Child Table version | Medium | Backend Dev | Sprint 2 |
| 6 | A5 | Bắt buộc ảnh xác nhận mặt bằng | Medium | Backend Dev | Sprint 2 |
| 7 | A6 | Bắt buộc Vendor upload Evidence sau lắp | Medium | Backend Dev | Sprint 2 |
| 8 | A8 | UAT Test Case cho kịch bản `is_radiation` bypass | Critical | QA Lead | Sprint 2 |
| 9 | A9 | Report Query cho KPI Avg Time to Release + DOA Rate | Low | Report Dev | Sprint 3 |
| 10 | A10 | Test API authentication + rate limiting | Medium | QA Lead | Sprint 3 |

**Quyết định nghiệm thu:**
- ☐ **Duyệt có điều kiện** — Cho phép triển khai sau khi đóng A7 + A8
- ☐ **Từ chối** — Yêu cầu hoàn thành toàn bộ Sprint 2 trước khi xem xét lại
- ☐ **Duyệt hoàn toàn** *(Không khả dụng — còn Critical Issue)*

---

## 11. BẢNG KÝ DUYỆT

| Vai trò | Họ và Tên | Đơn vị | Chữ ký | Ngày |
|---|---|---|---|---|
| **Chủ nhiệm dự án** | | Phòng TBYT | | |
| **Kiến trúc giải pháp** | | Tổ Kỹ thuật AssetCore | | |
| **Trưởng nhóm Dev** | | IT / Phát triển Phần mềm | | |
| **QA Lead** | | Phòng Hành chính QLCL | | |
| **QMS Reviewer** | | Tổ Quản lý Chất lượng | | |
| **Đại diện Nghiệp vụ** | | PTP Khối 2 / TBYT | | |
| **Phê duyệt cuối (Go/No-Go)** | | Ban Giám đốc | | |

---

*Hồ sơ này được sinh từ hệ thống AssetCore Documentation System.*
*Mọi tài liệu chi tiết được lưu trữ tại: `/apps/assetcore/docs/`*
*Phiên bản kiểm soát: Git tag `imm04-acceptance-v1.0`*
