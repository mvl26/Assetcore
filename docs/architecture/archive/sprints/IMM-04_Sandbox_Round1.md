# Kế hoạch Triển khai Sandbox Vòng 1 — IMM-04
# Chiến lược: Configuration-First | Demo End-to-End Luồng Chính

**Phiên bản:** 1.0 | **Ngày:** 2026-04-15
**Mục tiêu Sandbox:** Chạy được luồng Nhận Thiết bị → Kiểm tra → Release mà người dùng thực tế thao tác được, TRƯỚC KHI viết một dòng Python.

---

## NGUYÊN TẮC CONFIGURATION-FIRST

```
Ưu tiên 1: Dùng công cụ UI của ERPNext (DocType Builder, Workflow, Role Manager)
Ưu tiên 2: Dùng Custom Script nhẹ (Client Script trên UI)
Ưu tiên 3: Chỉ viết Server Script khi validation quan trọng KHÔNG làm được bằng UI
Ưu tiên 4: Mock thủ công những gì phức tạp → để vòng 2 làm đúng
```

---

## PHẦN 1 — CẤU HÌNH ĐƯỢC BẰNG CÔNG CỤ ERPNEXT CHUẨN

*Không cần viết code. Làm hoàn toàn qua giao diện quản trị ERPNext.*

| # | Hạng mục | Công cụ ERPNext | Ghi chú |
|---|---|---|---|
| 1.1 | Tạo 6 Custom Roles | **Role Manager** (`/app/role`) | HTM Technician, Biomed Engineer, Workshop Head, VP Block2, QA Risk Team, CMMS Admin |
| 1.2 | Tạo DocType `Asset Commissioning` | **DocType Builder** (`/app/doctype`) | Submittable, module AssetCore, autoname IMM04-.YY.-.MM.-.##### |
| 1.3 | Tạo DocType `Commissioning Checklist` | **DocType Builder** | `Is Table = 1`, gắn vào bảng mẹ |
| 1.4 | Tạo DocType `Asset QA Non Conformance` | **DocType Builder** | Submittable, naming DOA-.YY.-.##### |
| 1.5 | Tạo Workflow `imm_04_workflow` | **Workflow Builder** (`/app/workflow`) | 11 states, gắn vào Asset Commissioning |
| 1.6 | Cấu hình Permission cho 3 DocType | **Role Permissions Manager** | Theo Permission Matrix đã thiết kế |
| 1.7 | Thêm Custom Fields vào Core `Asset` | **Custom Field** (`/app/custom-field`) | 3 fields: `custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref` |
| 1.8 | Cấu hình field `.depends_on` và `.mandatory_depends_on` | **DocType Builder → Field properties** | `amend_reason` chỉ hiện khi `amended_from` có giá trị |
| 1.9 | Cấu hình `fetch_from` cho `is_radiation_device` | **DocType Builder** | Fetch từ `master_item.custom_is_radiation` tự động |
| 1.10 | Set Naming Series trong DocType | **DocType Builder → Autoname** | Format: `IMM04-.YY.-.MM.-.#####` |

---

## PHẦN 2 — CẦN CUSTOM DOCTYPE (Files JSON + migrate)

*Cần tạo file `.json` và chạy `bench migrate`. KHÔNG cần viết logic Python ở vòng 1.*

| # | Hạng mục | Cách thực hiện | Lý do không làm được bằng UI thuần |
|---|---|---|---|
| 2.1 | DocType `Commissioning Document Record` (bảng kiểm hồ sơ) | Tạo JSON, migrate | Child Table phức tạp với field `is_mandatory`, `doc_type`, `status` — cần đặt chuẩn để Workflow Condition đọc được |
| 2.2 | Naming series `IMM04-.YY.-.MM.-` output format | JSON + autoname field | Frappe UI Naming Series đôi khi không đáng tin dùng cho format phức tạp — an toàn hơn khi chốt trong JSON |
| 2.3 | `search_index = 1` cho `vendor_serial_no` | Cần vào JSON trực tiếp | DocType Builder UI không expose search_index checkbox |
| 2.4 | Permission Level (perm level 1) cho field `penalty_amount` | JSON DocType hoặc Custom Field | UI không cho set perm level cho từng field riêng lẻ |

---

## PHẦN 3 — CẦN SCRIPT (Tối thiểu cho Sandbox)

*Chỉ viết những script QUAN TRỌNG — mà thiếu thì demo không chạy được.*

### 3A. SERVER SCRIPT (Bắt buộc — 3 cái thôi)

| # | Script | Lý do không thể bỏ qua | Thời gian viết |
|---|---|---|---|
| S-01 | **VR-01: Chặn trùng Serial Number** | Nếu không có → demo sẽ cho tạo 2 máy cùng Serial → mất tín nhiệm với người dùng | ~1h |
| S-02 | **VR-04: Chặn Release khi còn NC Open** | Rule cốt lõi của QMS; không có thì Release Gate vô nghĩa | ~1h |
| S-03 | **on_submit: Mint Asset** | Nếu không có → Release xong không có Asset → Demo vỡ | ~2h |

### 3B. CLIENT SCRIPT (UI — 2 cái cần thiết)

| # | Script | Lý do | Thời gian viết |
|---|---|---|---|
| C-01 | **Dynamic field visibility** theo workflow_state | Không có → Form nhìn "chết" — Tab Baseline hiện ngay từ Draft gây rối | ~2h |
| C-02 | **Cảnh báo màu đỏ khi Fail** trong Grid Checklist | Feedback trực quan cho KTV; không có → Demo thiếu chuyên nghiệp | ~1h |

### 3C. SCRIPT BỎ QUA Ở VÒNG 1 (Defer)

| Script | Lý do defer | Vòng nào |
|---|---|---|
| VR-03a: Bắt ghi chú khi Fail | Có thể mock: KTV tự điền; Training nhắc nhở | Vòng 2 |
| VR-07: Auto-Hold bức xạ | Mock bằng tay: QA Officer tự chuyển Hold | Vòng 2 |
| VR-05: Warn thiếu Manual | Không ảnh hưởng luồng chính | Vòng 2 |
| tasks.py Cronjob aging | Cần scheduler setup; không cần cho demo | Vòng 2 |
| `_notify_purchasing_dept()` | Email/ZNS setup phức tạp | Vòng 2 |

---

## PHẦN 4 — HẠNG MỤC MOCK/MANUAL Ở VÒNG 1

*Chấp nhận làm thủ công trong Sandbox để tập trung vào luồng chính.*

| # | Hạng mục | Cách Mock | Ghi chú để Vòng 2 |
|---|---|---|---|
| 4.1 | Clinical Hold tự động cho thiết bị bức xạ | QA Officer tự bấm nút chuyển state sang Clinical_Hold khi thấy `is_radiation=1` | V2: Viết `validate_radiation_hold()` |
| 4.2 | Ghi chú bắt buộc khi Baseline Fail | Training KTV: tự giác điền; QA review | V2: Viết VR-03a trong validate |
| 4.3 | Sinh mã QR nội bộ (`internal_tag_qr`) | KTV tự gõ theo quy ước `BV-DEPT-YYYY-SEQ` | V2: Viết `_generate_internal_qr()` |
| 4.4 | Notification/Email sau Release | PM thông báo miệng hoặc chat cho Kế toán | V2: Viết `_notify_purchasing_dept()` |
| 4.5 | Cronjob cảnh báo SLA | Theo dõi thủ công trên List View có filter | V2: Viết `tasks.py` + scheduler |
| 4.6 | Dashboard Widgets | Dùng ERPNext List View + filter thay Dashboard chính thức | V2: Build Workspace Widgets |
| 4.7 | API Barcode endpoint | Demo quét QR bằng URL gõ tay trên trình duyệt | V2: Test thực tế với súng scanner |

---

## PHẦN 5 — THỨ TỰ CẤU HÌNH TRONG SANDBOX

Thực hiện ĐÚNG THỨ TỰ này để tránh dependency error:

```
NGÀY 1 — Nền tảng (Foundation)
════════════════════════════════
 Bước 1: Tạo 6 Custom Roles  (/app/role)
 Bước 2: Tạo DocType `Commissioning Checklist` (Child Table — tạo TRƯỚC bảng mẹ)
 Bước 3: Tạo DocType `Commissioning Document Record` (Child Table — tạo TRƯỚC bảng mẹ)
 Bước 4: Tạo DocType `Asset QA Non Conformance`
 Bước 5: Tạo DocType `Asset Commissioning` (bảng mẹ — gắn Child Tables)
 Bước 6: bench migrate

NGÀY 2 — Workflow & Permission
════════════════════════════════
 Bước 7:  Tạo Workflow `imm_04_workflow` (11 states + transitions)
 Bước 8:  Gắn Workflow vào Asset Commissioning DocType
 Bước 9:  Set Role Permissions cho Asset Commissioning
 Bước 10: Set Role Permissions cho Asset QA Non Conformance
 Bước 11: Thêm Custom Fields vào Core Asset  (/app/custom-field)
 Bước 12: Tạo 6 User test + gán Role

NGÀY 3 — Scripts & Verify
════════════════════════════════
 Bước 13: Viết + deploy Server Script S-01 (VR-01 Unique Serial)
 Bước 14: Viết + deploy Server Script S-02 (VR-04 Block NC Open)
 Bước 15: Viết + deploy Server Script S-03 (on_submit Mint Asset)
 Bước 16: Viết + deploy Client Script C-01 (Field visibility)
 Bước 17: Viết + deploy Client Script C-02 (Grid coloring)
 Bước 18: Chạy Verify Checklist (Phần 6 bên dưới)
 Bước 19: Chạy Simulation với dữ liệu mẫu
```

---

## PHẦN 6 — CHECKLIST VERIFY SAU CẤU HÌNH

*Thực hiện sau khi xong Ngày 3. Người verify: QA Lead + Dev Lead.*

### 6A. Kiểm tra DocType

| # | Hạng mục | Cách verify | Đạt? |
|---|---|---|---|
| V-01 | 3 DocType xuất hiện trong menu AssetCore | Vào `/app/asset-commissioning` không lỗi 404 | ☐ |
| V-02 | Form Asset Commissioning có đủ field theo spec | So sánh UI với field list trong doctypes.md | ☐ |
| V-03 | Tab "Baseline Tests" hiện lưới Commissioning Checklist | Nhấp vào Tab, lưới render không lỗi | ☐ |
| V-04 | Naming series sinh đúng format `IMM04-26-04-00001` | Tạo form mới, Save, kiểm tra ID | ☐ |
| V-05 | `is_radiation_device` fetch tự động từ Item | Chọn Item có radiation=1, field tự tick | ☐ |

### 6B. Kiểm tra Workflow

| # | Hạng mục | Cách verify | Đạt? |
|---|---|---|---|
| V-06 | Form mới mở ra ở state `Draft` | New form → trạng thái = Draft | ☐ |
| V-07 | Workflow buttons xuất hiện đúng state | Ở Draft có nút "Submit for Verify" | ☐ |
| V-08 | Chuyển state Draft → Pending_Doc_Verify thành công | Bấm nút, state đổi, không lỗi | ☐ |
| V-09 | HTM Technician không thấy nút Approve Release | Login bằng account HTM Tech; ở state Clinical_Release không có nút Submit | ☐ |
| V-10 | VP Block2 thấy nút Approve Release | Login bằng VP Block2; thấy nút Submit ở state Clinical_Release | ☐ |

### 6C. Kiểm tra Server Scripts

| # | Hạng mục | Cách verify | Đạt? |
|---|---|---|---|
| V-11 | VR-01: Trùng Serial bị block | Nhập SN đã tồn tại → lỗi đỏ hiện ra, không Save được | ☐ |
| V-12 | VR-04: NC Open block Release | Tạo NC Open, thử Release → lỗi đỏ "Còn NC chưa xử lý" | ☐ |
| V-13 | on_submit mint Asset | Submit phiếu ở state Clinical_Release → Asset mới xuất hiện trong `/app/asset` | ☐ |
| V-14 | `final_asset` được ghi ngược về phiếu | Mở lại phiếu sau Submit → field `final_asset` có giá trị | ☐ |

### 6D. Kiểm tra luồng end-to-end (Demo Run)

| # | Hạng mục | Cách verify | Đạt? |
|---|---|---|---|
| V-15 | Chạy luồng xanh hoàn chỉnh từ Draft → Clinical_Release | Theo Simulation Log: tất cả state chuyển thành công | ☐ |
| V-16 | Chạy luồng NC: Tạo NC → Close → Release thành công | Tạo NC, đóng NC, Release → Asset sinh ra | ☐ |
| V-17 | Xác nhận dữ liệu Asset có đủ 3 custom fields | Mở Asset vừa tạo, scroll tìm `custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref` | ☐ |

**Điều kiện đạt Sandbox Vòng 1:** V-01 đến V-17 tất cả ☑️ — Không cần 100% perfect, không có Severity-1 (tắt luồng chính).

---

## TÓM TẮT QUYẾT ĐỊNH CONFIGURATION-FIRST

| Loại | Số lượng Vòng 1 | Số lượng Defer Vòng 2 |
|---|---|---|
| Cấu hình UI thuần (Phần 1) | 10 hạng mục | — |
| Custom DocType JSON (Phần 2) | 4 hạng mục | — |
| Server Script | 3 script (P0) | 4 script (defer) |
| Client Script | 2 script | — |
| Mock thủ công | — | 7 hạng mục (đến V2) |
| **Tổng công sức Vòng 1** | **~3 ngày** | **Vòng 2: ~2 ngày** |
