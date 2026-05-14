# Build Plan — IMM-04 Implementation
# AssetCore / IMMIS | Phiên bản: 1.0 | Ngày: 2026-04-15

Bảng này phân rã Implementation Baseline v1.0 thành các gói công việc (Work Packages) sẵn sàng giao Sprint. Mỗi WP có mã duy nhất, đầu ra rõ ràng, ước lượng độ phức tạp và điều kiện hoàn thành.

---

## Thang đo Độ phức tạp

| Ký hiệu | Mức | Ý nghĩa |
|---|---|---|
| 🟢 S | Simple | ≤ 2h, không phụ thuộc kỹ năng đặc biệt |
| 🟡 M | Medium | 2–8h, cần hiểu business logic |
| 🔴 L | Large | 1–3 ngày, nhiều tầng phụ thuộc |
| ⚫ XL | Extra Large | > 3 ngày, cần architect review |

---

## 1. DATA MODEL (WP-DM)

| Mã | Mô tả | Đầu ra | Phụ thuộc | Vai trò | Độ phức tạp | Điều kiện Hoàn thành |
|---|---|---|---|---|---|---|
| WP-DM-01 | Xác định và đặt tên 3 Custom DocType | Sơ đồ Entity tên kỹ thuật xác nhận | Baseline ERD | BA Lead | 🟢 S | BA và Architect đã ký duyệt DocType list |
| WP-DM-02 | Thiết kế field list `asset_commissioning` | File spec field mapping (30+ fields) | WP-DM-01 | Backend Dev | 🟡 M | Field list được review, không còn thiếu sót theo ERD |
| WP-DM-03 | Thiết kế field list `commissioning_checklist` (Child Table) | Spec Child Table (5 fields + deps) | WP-DM-01 | Backend Dev | 🟢 S | Child Table có đủ: parameter, measured_val, test_result, fail_note |
| WP-DM-04 | Thiết kế field list `asset_qa_nc` | Spec NC DocType + perm level cho penalty | WP-DM-01 | Backend Dev | 🟢 S | Có field penalty ở perm level 1 (chỉ lãnh đạo thấy) |
| WP-DM-05 | Xác định Custom Fields bổ sung vào Core `Asset` | Danh sách 3 custom fields + mapping | WP-DM-01 | Backend Dev + Architect | 🟡 M | 3 fields (`custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref`) không xung đột với ERPNext core |
| WP-DM-06 | Thiết kế Naming Series cho 2 Submittable DocType | Naming format document | WP-DM-02, DM-04 | Backend Dev | 🟢 S | `IMM04-.YY.-.MM.-.#####` và `DOA-.YY.-.#####` sinh đúng và không trùng |

---

## 2. DOCTYPE CONFIGURATION (WP-DC)

| Mã | Mô tả | Đầu ra | Phụ thuộc | Vai trò | Độ phức tạp | Điều kiện Hoàn thành |
|---|---|---|---|---|---|---|
| WP-DC-01 | Tạo file `asset_commissioning.json` chuẩn Frappe | File JSON DocType deployable | WP-DM-02 | Backend Dev | 🟡 M | `bench migrate` không lỗi; Form hiện đúng trên UI |
| WP-DC-02 | Tạo file `commissioning_checklist.json` (Child Table) | File JSON `istable=1` | WP-DM-03 | Backend Dev | 🟢 S | Child Table bắt buộc (reqd=1) và render đúng lưới |
| WP-DC-03 | Tạo file `asset_qa_nc.json` | File JSON NC DocType Submittable | WP-DM-04 | Backend Dev | 🟢 S | NC có thể Submit, có perm level trên penalty field |
| WP-DC-04 | Thêm Custom Fields vào Core Asset qua Fixture | File fixture JSON cho Custom Field | WP-DM-05 | Backend Dev | 🟡 M | `bench migrate` + custom fields xuất hiện trên form Asset; không ghi đè field gốc |
| WP-DC-05 | Cấu hình `search_index` cho fields quan trọng | Xác nhận Index SQL | WP-DC-01 | Backend Dev | 🟢 S | `vendor_serial_no` có search_index=1; Query scan 1M rows < 50ms |

---

## 3. WORKFLOW CONFIGURATION (WP-WF)

| Mã | Mô tả | Đầu ra | Phụ thuộc | Vai trò | Độ phức tạp | Điều kiện Hoàn thành |
|---|---|---|---|---|---|---|
| WP-WF-01 | Tạo Workflow JSON `imm_04_workflow` (11 states) | File `imm_04_workflow.json` importable | WP-DC-01 | Backend Dev | 🔴 L | 11 states đúng tên; chuyển state thủ công trên UI không lỗi |
| WP-WF-02 | Config transition Happy Path (Draft → Release) | Transition matrix đã test | WP-WF-01 | Backend Dev | 🟡 M | Chạy simulation INT-01 không bị kẹt ngoài ý muốn |
| WP-WF-03 | Config transition ngoại lệ (NC, Hold, Re-inspection) | Transition exception paths test pass | WP-WF-01 | Backend Dev | 🔴 L | Simulation INT-02 (DOA path) chạy đúng; không có dead-state |
| WP-WF-04 | Gắn Workflow vào DocType, kiểm tra docstatus | DocType có `workflow_state` field | WP-WF-01, DC-01 | Backend Dev | 🟢 S | Submit button chỉ xuất hiện đúng state và đúng role |
| WP-WF-05 | Tạo Workflow Condition rules (doc.field checks) | Condition expressions cho từng gate | WP-WF-01 | Backend Dev | 🟡 M | Gate Doc-Verify, Site, Release hoạt động theo VR-02 và VR-04 |

---

## 4. PERMISSION AND ROLE (WP-PR)

| Mã | Mô tả | Đầu ra | Phụ thuộc | Vai trò | Độ phức tạp | Điều kiện Hoàn thành |
|---|---|---|---|---|---|---|
| WP-PR-01 | Tạo 6 Custom Roles trong ERPNext | Roles xuất hiện trong Role Manager | — | CMMS Admin / Sys Admin | 🟢 S | 6 roles: HTM Technician, Biomed Engineer, Workshop Head, VP Block2, QA Risk Team, CMMS Admin |
| WP-PR-02 | Cấu hình Role Permission cho `asset_commissioning` | DocType Permission records | WP-PR-01, DC-01 | Backend Dev | 🟡 M | Permission Matrix: HTM Tech không Submit được; VP Block2 Submit được |
| WP-PR-03 | Cấu hình Role Permission cho `asset_qa_nc` | DocType Permission records | WP-PR-01, DC-03 | Backend Dev | 🟢 S | penalty_amount chỉ VP Block2 thấy (perm level 1) |
| WP-PR-04 | **[CRITICAL A7]** Khóa `custom_is_radiation` trên Item DocType với role thường | Custom Field permission level | WP-PR-01 | Backend Dev + QMS | 🟡 M | KTV HTM không thể sửa is_radiation; QMS verify bằng test case UAT-TM-02 |
| WP-PR-05 | Gán User test vào đúng Role cho UAT | Checklist User-Role assignment | WP-PR-01 | CMMS Admin | 🟢 S | Mỗi actor UAT có đúng 1 Role; không user nào có 2 Role conflict |

---

## 5. VALIDATION AND SERVER SCRIPT (WP-VS)

| Mã | Mô tả | Đầu ra | Phụ thuộc | Vai trò | Độ phức tạp | Điều kiện Hoàn thành |
|---|---|---|---|---|---|---|
| WP-VS-01 | Viết `validate_unique_serial()` (VR-01) | Python method trong controller | WP-DC-01 | Backend Dev | 🟡 M | UT-01 PASS — Trùng SN ném lỗi đúng; SN khác nhau cho qua |
| WP-VS-02 | Viết `validate_checklist_completion()` (VR-03a,b) | Python method + test | WP-DC-01, 02 | Backend Dev | 🟡 M | UT-03 PASS — Thiếu fail_note bị block; all-pass cho chuyển Release |
| WP-VS-03 | Viết `block_release_if_nc_open()` (VR-04) | Python method + test | WP-DC-03 | Backend Dev | 🟡 M | UT-02 PASS — NC Open → block Release; NC Closed → cho qua |
| WP-VS-04 | Viết `validate_radiation_hold()` (VR-07) Auto-Hold | Python method + test | WP-DC-01, PR-04 | Backend Dev | 🟡 M | KB06 PASS — Bức xạ + không có license → tự động chuyển Clinical_Hold |
| WP-VS-05 | Viết `validate_backdate()` (chống back-date) | Python validation | WP-DC-01 | Backend Dev | 🟢 S | Ngày lắp < ngày PO → throw lỗi; ngày hợp lệ → pass |
| WP-VS-06 | Viết `before_save()` — auto-set installation_date | Python hook | WP-DC-01 | Backend Dev | 🟢 S | Khi chuyển sang Installing, `installation_date` tự điền NOW; không cho sửa tay |
| WP-VS-07 | Viết `mint_core_asset()` trong `on_submit()` | Python method mint Asset | WP-DC-01, DM-05 | Backend Dev | 🔴 L | INT-01 PASS — Asset được tạo đúng; `final_asset` được ghi ngược; không lỗi nếu chạy 2 lần |
| WP-VS-08 | Viết Client Script JS VR-05, VR-08 (soft warn + barcode) | `.js` file | WP-DC-01 | Frontend Dev | 🟡 M | Thiếu Manual → toast vàng; Serial < 4 ký tự → warn barcode; bức xạ → toast đỏ |

---

## 6. EVENT LOGGING (WP-EL)

| Mã | Mô tả | Đầu ra | Phụ thuộc | Vai trò | Độ phức tạp | Điều kiện Hoàn thành |
|---|---|---|---|---|---|---|
| WP-EL-01 | Bật `track_changes=1` và `track_views=1` | Config trong JSON DocType | WP-DC-01 | Backend Dev | 🟢 S | Mỗi thay đổi field có Version history trong Document Log |
| WP-EL-02 | Viết `fire_release_event()` real-time publish | Python method + test | WP-VS-07 | Backend Dev | 🟡 M | Event `imm04.release.approved` xuất hiện trong browser console khi Release |
| WP-EL-03 | Viết hook audit log khi Vendor đổi `installation_date` | `before_save` hook bổ sung | WP-VS-06 | Backend Dev | 🟡 M | Thay đổi ngày lắp đặt tạo ra 1 dòng log với old_value, new_value, actor |
| WP-EL-04 | Viết `_notify_purchasing_dept()` sau Release | Python method gửi notification | WP-VS-07 | Backend Dev | 🟢 S | Sau Submit, users có role "Purchase User" nhận in-app notification |
| WP-EL-05 | Xác nhận 3 event IMMUTABLE không thể xóa | QA verification | WP-EL-02 | QA Lead | 🟡 M | Admin không thể Delete Version Log cho events: inspection.passed, nc.opened, release.approved |

---

## 7. UI / FORM LAYOUT (WP-UI)

| Mã | Mô tả | Đầu ra | Phụ thuộc | Vai trò | Độ phức tạp | Điều kiện Hoàn thành |
|---|---|---|---|---|---|---|
| WP-UI-01 | Cấu hình Tab, Section, Column Break trên form | Form layout đẹp, đúng logic | WP-DC-01 | Frontend Dev | 🟡 M | Form có 2 Tab (Baseline, Documents); Section header rõ ràng theo từng giai đoạn |
| WP-UI-02 | Dynamic field visibility theo `workflow_state` | JS `_update_field_visibility()` | WP-WF-01, DC-01 | Frontend Dev | 🔴 L | Tab Baseline chỉ hiển thị khi state = Initial_Inspection trở đi; Section ID ẩn ở Draft |
| WP-UI-03 | Thêm nút "Báo cáo DOA" trên toolbar | Custom button JS | WP-DC-03 | Frontend Dev | 🟡 M | Nút xuất hiện đúng (chỉ ở state Installing); Click mở Prompt dialog; tạo NC thành công |
| WP-UI-04 | Màu hóa hàng trong Grid Checklist (Xanh/Đỏ) | JS grid row coloring | WP-DC-02 | Frontend Dev | 🟢 S | Pass row = nền xanh nhạt; Fail row = nền đỏ nhạt ngay khi chọn |
| WP-UI-05 | Setup Workspace Dashboard IMM-04 trên Frappe | Workspace page với 3 Widget | WP-EL-02, VS-07 | Frontend Dev | 🟡 M | 3 Widgets hoạt động: SLA Hit-Rate, Active Hold Count, Open NC Count |

---

## 8. REPORTS / DASHBOARD (WP-RD)

| Mã | Mô tả | Đầu ra | Phụ thuộc | Vai trò | Độ phức tạp | Điều kiện Hoàn thành |
|---|---|---|---|---|---|---|
| WP-RD-01 | Viết `get_dashboard_stats()` API endpoint | REST endpoint trả JSON | WP-DC-01, 03 | Backend Dev | 🟡 M | `/api/method/assetcore.api.get_dashboard_stats` trả đúng 3 metrics |
| WP-RD-02 | Viết Report Query: Avg Time to Release | Frappe Report (Query Report) | WP-EL-02 | Report Dev | 🔴 L | Report hiển thị avg days nhóm theo Vendor; có filter theo tháng |
| WP-RD-03 | Viết Report Query: DOA Rate by Vendor | Frappe Report | WP-DC-03 | Report Dev | 🟡 M | Report đếm NC=DOA nhóm theo Vendor; drill-down về NC record |
| WP-RD-04 | Viết API `get_commissioning_by_barcode()` | REST endpoint tra QR | WP-DC-01 | Backend Dev | 🟡 M | Quét QR thật → trả đúng JSON device history trong < 200ms |
| WP-RD-05 | Build Number Cards trên Workspace | 3 card HTML/JS | WP-RD-01 | Frontend Dev | 🟢 S | Cards cập nhật realtime khi data thay đổi |

---

## 9. TEST PREPARATION (WP-TP)

| Mã | Mô tả | Đầu ra | Phụ thuộc | Vai trò | Độ phức tạp | Điều kiện Hoàn thành |
|---|---|---|---|---|---|---|
| WP-TP-01 | Chuẩn bị dữ liệu mẫu (Seed Data) cho test | Script hoặc fixture seed data | WP-DC-01 đến 03 | QA Lead | 🟡 M | 5 PO, 3 Vendor, 3 Item (1 bức xạ, 2 thường) đã có trong DB test |
| WP-TP-02 | Tạo User test cho 6 Actors | 6 User accounts trong hệ thống | WP-PR-01, PR-05 | CMMS Admin | 🟢 S | Mỗi User đăng nhập được; đúng quyền theo Permission Matrix |
| WP-TP-03 | Chạy Unit Test UT-01, UT-02, UT-03 | Test report + pass/fail | WP-VS-01 đến 04 | QA Lead | 🟡 M | 3/3 UT PASS với không có workaround |
| WP-TP-04 | Chạy Integration Test INT-01 (Happy Path) | Test report end-to-end | WP-WF-01 đến 05, VS-01 đến 07 | QA Lead | 🔴 L | Asset được tạo tự động sau Submit; final_asset có giá trị |
| WP-TP-05 | Chạy Integration Test INT-02 (DOA Path) | Test report DOA flow | WP-DC-03, WF-03 | QA Lead | 🟡 M | NC được tạo; không có Asset nào được Mint |
| WP-TP-06 | Ghi chép và phân loại Bug từ test nội bộ | Bug report Severity 1/2/3 | WP-TP-03 đến 05 | QA Lead | 🟡 M | 0 bug Severity 1 (Critical) tồn đọng trước UAT |

---

## 10. UAT SUPPORT (WP-UA)

| Mã | Mô tả | Đầu ra | Phụ thuộc | Vai trò | Độ phức tạp | Điều kiện Hoàn thành |
|---|---|---|---|---|---|---|
| WP-UA-01 | Phát tài liệu UAT Script cho người dùng | File `IMM-04_UAT_Script.md` + In ra giấy | WP-TP-01, TP-02 | PM / QA Lead | 🟢 S | Mỗi actor nhận đúng bản hướng dẫn theo vai trò |
| WP-UA-02 | Hỗ trợ thực hiện KB01–KB06 cùng người dùng | Biên bản UAT có chữ ký 6 bên | WP-UA-01, TP-04, TP-05 | PM + QA Lead | 🔴 L | 25/25 Test Steps PASS hoặc được giải thích; Biên bản có đủ chữ ký |
| WP-UA-03 | Tổng hợp Bug UAT và fix loop | Bug fix report + re-test | WP-UA-02 | Backend Dev + QA | 🔴 L | 0 Severity 1 bug; Severity 2 có plan fix trong 3 ngày |
| WP-UA-04 | Verify Critical Issue A7 (is_radiation permission) | Test report A7 + QMS sign-off | WP-PR-04 | QMS Reviewer | 🟡 M | KTV HTM không sửa được is_radiation; QMS ký xác nhận |
| WP-UA-05 | Họp Hội đồng Nghiệm thu và ký biên bản | Biên bản nghiệm thu có chữ ký Ban GĐ | WP-UA-02, UA-03, UA-04 | PM + Ban GĐ | 🟡 M | Hội đồng họp; Biên bản ký đầy đủ; Git tag `imm04-release-v1.0` tạo |

---

## Tổng hợp Sprint Allocation

| Sprint | Work Packages | Mục tiêu Milestone |
|---|---|---|
| **Sprint 1** | WP-DM-01→06, WP-DC-01→05, WP-WF-01→05, WP-PR-01→05 | Cấu hình xong + Workflow chạy được |
| **Sprint 2** | WP-VS-01→08, WP-EL-01→05, WP-UI-01→03 | Chạy được validation + Event log |
| **Sprint 3** | WP-UI-04→05, WP-RD-01→05, WP-TP-01→06 | UI hoàn chỉnh + Qua test nội bộ |
| **Sprint 4** | WP-UA-01→05 | Qua UAT + Ký nghiệm thu → Go-Live |
