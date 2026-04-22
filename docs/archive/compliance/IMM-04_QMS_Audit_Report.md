# BÁO CÁO KIỂM ĐỊNH CHẤT LƯỢNG (QMS AUDIT REPORT)
# Module: IMM-04 — Lắp Đặt, Định Danh và Kiểm Tra Ban Đầu
# Hệ thống: AssetCore / IMMIS v1.0

---

**Kiểm định viên:** QMS Auditor — Tổ Quản lý Chất lượng
**Ngày kiểm định:** 2026-04-15
**Phạm vi:** Toàn bộ thiết kế kỹ thuật, tài liệu BA, SPEC, Test Suite và Traceability Matrix của IMM-04
**Tài liệu tham chiếu:**
- IMM-04_Scope_Analysis.md
- IMM-04_State_Machine.md
- IMM-04_DocType_Design.md
- IMM-04_Permission_Matrix.md
- IMM-04_Validation_Rules.md
- IMM-04_Event_Model.md
- IMM-04_QMS_Checklist_Audit.md
- IMM-04_Hardened_Review_Report.md
- IMM-04_Source_Code.md
- IMM-04_UAT_Script.md
- IMM-04_Traceability_Matrix.md

---

## 1. AUDIT TRAIL (Dấu vết kiểm toán)

**Câu hỏi kiểm định:** Mọi hành động nghiệp vụ quan trọng có được ghi lại tự động không? Dấu vết có bất biến (immutable) không? Có lưu đủ: ai làm, lúc nào, từ trạng thái nào, chuyển sang trạng thái nào?

| Hạng mục kiểm tra | Trạng thái | Bằng chứng |
|---|---|---|
| Frappe Track Changes bật cho DocType | ✅ Pass | Thiết kế: `track_changes = 1` — ghi lịch sử mọi field thay đổi |
| Frappe Track Views bật | ✅ Pass | `track_views = 1` — ghi timestamp mỗi lần user mở form |
| Event log khi chuyển Workflow State | ✅ Pass | Event Model định nghĩa 10 sự kiện `imm04.*` với payload chuẩn |
| Event IMMUTABLE sau Submit | ✅ Pass | Events `imm04.inspection.passed`, `imm04.release.approved` được đánh dấu bất biến |
| Lưu IP + Actor + Timestamp | ⚠️ Partial | Frappe lưu actor và timestamp; **IP Address chưa được xác nhận** lưu trong Event Payload |
| Audit log khi Vendor đổi lịch thi công | ⚠️ Partial | Hardening Report (#06) nhận diện gap này nhưng **chưa có Server Script bắt sự kiện đổi `installation_date`** |

**Kết luận mục 1:** ⚠️ **PARTIAL PASS**
**Gap:** Thiếu capture IP Address trong Payload; Thiếu hook audit khi Vendor đổi ngày.
**Action:** Bổ sung `frappe.local.request_ip` vào Event Payload; Thêm `before_save` hook log thay đổi `installation_date`.

---

## 2. APPROVAL MATRIX (Ma trận phê duyệt)

**Câu hỏi kiểm định:** Có đủ các cấp phê duyệt? Quy tắc "4 mắt" có được bảo đảm? Không ai được tự phê duyệt công việc của chính mình?

| Hạng mục kiểm tra | Trạng thái | Bằng chứng |
|---|---|---|
| Có ít nhất 2 cấp phê duyệt cho release | ✅ Pass | Biomed Engineer test → VP_Block2 approve — 2 vai trò khác nhau |
| Người test không thể tự approve | ✅ Pass | Permission Matrix: HTM Tech không có quyền Submit tại node Release |
| Máy bức xạ có cấp duyệt riêng QA | ✅ Pass | QA_Risk_Team có quyền upload và gỡ Clinical Hold |
| Máy giá trị cao (>1 tỷ) cần Board approval | ⚠️ Partial | Approval Matrix đề cập điều kiện value-based approval nhưng **chưa có field `asset_value` trên Form** và **chưa có logic trigger khi vượt ngưỡng** |
| Quy trình DOA terminate cần Board sign-off | ✅ Pass | Return To Vendor: chỉ `Board/VP_Block2` được phép kích hoạt |
| Chữ ký điện tử có timestamp server | ✅ Pass | Frappe Submit dùng server timestamp không thể chỉnh tay |

**Kết luận mục 2:** ⚠️ **PARTIAL PASS**
**Gap:** Logic phê duyệt theo giá trị tài sản (Value-based Approval) chưa được hiện thực hóa trong code.
**Action:** Thêm field `estimated_asset_value` (Currency) vào DocType. Viết Validation: `if value > 1_000_000_000: require Board role for approval`.

---

## 3. KIỂM SOÁT THAY ĐỔI (Change Control)

**Câu hỏi kiểm định:** Khi cần sửa dữ liệu đã được phê duyệt, có quy trình Amend chuẩn không? Bản cũ có được giữ lại không?

| Hạng mục kiểm tra | Trạng thái | Bằng chứng |
|---|---|---|
| Dữ liệu bị khóa sau Submit (`docstatus=1`) | ✅ Pass | Frappe built-in; Kiểm chứng qua UAT KB05-Step4 |
| Có cơ chế Amend tạo version mới | ✅ Pass | Workshop Head có quyền Amend; QMS Rule: version cũ phải bị Cancel, không Delete |
| Bắt buộc ghi lý do Amend | ⚠️ Partial | UAT-TM-03 kiểm tra kịch bản này nhưng **chưa có field `amend_reason` bắt buộc trên form** — hiện chỉ dùng built-in Frappe Comments |
| Cấm Delete record đã Submit | ✅ Pass | Permission Matrix: không role nào có quyền Delete Submitted docs |
| Cấm back-date trường ngày | ✅ Pass | Server Validation Rule thiết kế rõ ràng trong Validation Rules doc |
| Version history của Checklist | ⚠️ Partial | Track Changes bật nhưng **Child Table changes không luôn được track chi tiết trong Frappe mặc định** — cần custom logic |

**Kết luận mục 3:** ⚠️ **PARTIAL PASS**
**Gap:** Thiếu field `amend_reason` bắt buộc; Child Table version tracking chưa chắc chắn.
**Action:** Thêm field `amend_reason` (Small Text, reqd=1) hiển thị khi `is_amended=1`. Viết custom hook track thay đổi trong `commissioning_checklist` Child Table.

---

## 4. BẰNG CHỨNG SỐ (Digital Evidence)

**Câu hỏi kiểm định:** Mỗi bước quan trọng có bắt buộc đính kèm tài liệu/ảnh/chữ ký làm bằng chứng không?

| Bước nghiệp vụ | Bằng chứng yêu cầu | Được enforce trong hệ thống? | Trạng thái |
|---|---|---|---|
| Tiếp nhận hàng | File scan Packing List, CO, CQ | ✅ Có VR-02 chặn nếu thiếu | ✅ Pass |
| Xác nhận mặt bằng | Checklist Site ký số hoặc ảnh đo | ⚠️ Checklist có nhưng **ảnh chụp mặt bằng chưa bắt buộc** | ⚠️ Partial |
| Lắp đặt hoàn tất | Log nhật ký kỹ sư hãng | ⚠️ Có field ghi chú nhưng **không bắt buộc Vendor upload file Evidence** | ⚠️ Partial |
| Kết quả Baseline Test | Form đo điện với số liệu thực | ✅ Bảng Child Table `measured_val` bắt buộc | ✅ Pass |
| DOA / Máy hỏng | Ảnh bằng chứng DOA | ✅ Field `damage_proof` reqd=1 khi NC=DOA | ✅ Pass |
| Giấy phép Bức xạ | File PDF Cục ATBXHN | ✅ `qa_license_doc` bắt buộc khi `is_radiation=1` và có Hold | ✅ Pass |
| Release / Phê duyệt | Chữ ký điện tử Board | ✅ Frappe Submit gắn User identity và server timestamp | ✅ Pass |

**Kết luận mục 4:** ⚠️ **PARTIAL PASS**
**Gap:** Không bắt buộc ảnh xác nhận mặt bằng; Không bắt buộc Vendor upload Evidence sau lắp đặt.
**Action:** Thêm field `site_photo` (Attach Image, reqd=1) trong Site Checklist. Thêm field `installation_evidence` (Attach, reqd=1) tại node `Installing`.

---

## 5. TRACEABILITY DASHBOARD → RECORD (Truy xuất nguồn gốc)

**Câu hỏi kiểm định:** Từ một con số trên Dashboard, người dùng có thể drill-down về tận record gốc không? Không có metric "chết" (không truy được nguồn)?

| KPI / Metric | Nguồn dữ liệu | Có thể drill-down? | Trạng thái |
|---|---|---|---|
| Commissioning SLA Hit-Rate | `expected_installation_date` vs `release_date` từ Event Timestamp | ✅ Click → List view lọc theo Pass/Fail date | ✅ Pass |
| First-Pass Release Rate | `Re_Inspection` count từ `workflow_state` history | ✅ Click → List lọc máy đã Re-inspect | ✅ Pass |
| Active Clinical Hold Count | `workflow_state = Clinical_Hold` | ✅ Click → Danh sách máy đang bị Hold | ✅ Pass |
| Open NC by Vendor | `Asset QA NC` count nhóm theo `vendor` | ✅ Click → NC record → Commissioning form | ✅ Pass |
| Avg Time to Release | `reception_date` vs `release_date` | ⚠️ KPI định nghĩa OK nhưng **chưa có Report Query được viết** | ⚠️ Partial |
| DOA Rate by Vendor | Count `nc_type=DOA` nhóm vendor | ⚠️ **Chưa có Report/Chart cụ thể** | ⚠️ Partial |

**Kết luận mục 5:** ⚠️ **PARTIAL PASS**
**Gap:** 2 KPI (Avg Time to Release và DOA Rate) chưa được viết thành Report Query/Chart trên Frappe.
**Action (Sprint 3):** Viết Report Builder hoặc Query Report cho 2 KPI này; bound vào Dashboard Workspace.

---

## 6. PHÂN QUYỀN ĐÚNG ACTOR THẬT (Role-Based Access Control)

**Câu hỏi kiểm định:** Mỗi actor có đúng quyền hạn — không thừa, không thiếu? Không có role nào có quyền toàn năng?

| Actor | Quyền cần có | Được config đúng? | Rủi ro nếu sai | Trạng thái |
|---|---|---|---|---|
| `HTM Technician` | Read, Write (giới hạn), Create draft | ✅ Đã thiết kế; Không có Submit | Tự phê duyệt → ❌ | ✅ Pass |
| `Biomed Engineer` | Write Baseline Tests, chuyển node Inspect | ✅ Đã thiết kế | Sửa Master Data Item → GAP (xem dưới) | ⚠️ Partial |
| `VP_Block2` | Submit/Approve Release | ✅ Đã thiết kế | — | ✅ Pass |
| `QA_Risk_Team` | Upload License, gỡ Hold | ✅ Đã thiết kế | — | ✅ Pass |
| Master Data Item | Chỉ Admin/Board được Edit | ⚠️ **Chưa xác nhận được set Read-Only với HTM Tech** — Gap từ Hardening #02 | Thay đổi `is_radiation` → máy X-quang lọt lưới Hold → nguy hiểm tính mạng | ❌ **FAIL** |
| `Vendor Technician` | Chỉ Access node `Installing` | ⚠️ Portal access chưa được implement và test | — | ⚠️ Partial |

**Kết luận mục 6:** ❌ **FAIL**
**Gap nghiêm trọng (Critical):** Permission bảo vệ Master Data `Item.custom_is_radiation` chưa được cấu hình và verify. Đây là lỗ hổng an toàn lâm sàng cấp độ CAO.
**Action CRITICAL (Trước Go-Live):** Thiết lập Permission Level trên field `custom_is_radiation` trong Item DocType: chỉ role `System Manager` hoặc `CMMS Admin` được edit. Viết UAT Test Case riêng cho kịch bản này.

---

## 7. KIỂM SOÁT DỮ LIỆU SAU SUBMIT (Post-Submit Data Integrity)

**Câu hỏi kiểm định:** Sau khi phiếu đã được Submit, dữ liệu có thực sự bất biến không? Có lỗ hổng nào cho phép thay đổi "im lặng"?

| Hạng mục kiểm tra | Trạng thái | Bằng chứng |
|---|---|---|
| Tất cả fields bị khóa sau Submit | ✅ Pass | `docstatus=1` — Frappe built-in; Kiểm chứng KB05-Step4 |
| Baseline Test Child-Table bị khóa | ✅ Pass | Child Table inherit lock từ Parent docstatus |
| Không cho Delete records Submitted | ✅ Pass | Permission Matrix không có Delete role |
| Số liệu đo lường không thể Back-date | ✅ Pass | Server Validation chặn `date < po_date` |
| Amend tạo version mới không xóa version cũ | ✅ Pass | Frappe Amend: Cancel old → Create new (amended_from link) |
| API endpoint không thể bypass Submit lock | ⚠️ Partial | Endpoint `@frappe.whitelist()` được thiết kế nhưng **chưa có rate limiting và API authentication verify trong test** |
| Database-level protection (ngoài Frappe) | ⚠️ Partial | Hoàn toàn phụ thuộc Frappe ORM — **không có DB trigger hoặc row-level security** ở tầng MySQL | 

**Kết luận mục 7:** ⚠️ **PARTIAL PASS**
**Gap:** API authentication chưa được test; Không có protection tầng DB (MySQL level).
**Action:** Thêm test case verify API `/api/method/imm04.*` reject unauthorized calls; Document rõ ràng trong Security runbook rằng MySQL access phải bị giới hạn chỉ Frappe service account.

---

## TỔNG HỢP KẾT QUẢ KIỂM ĐỊNH

| # | Hạng mục QMS | Kết quả | Mức độ |
|---|---|---|---|
| 1 | Audit Trail | ⚠️ PARTIAL PASS | Medium |
| 2 | Approval Matrix | ⚠️ PARTIAL PASS | Medium |
| 3 | Change Control | ⚠️ PARTIAL PASS | Medium |
| 4 | Digital Evidence | ⚠️ PARTIAL PASS | Medium |
| 5 | Traceability Dashboard→Record | ⚠️ PARTIAL PASS | Low |
| 6 | Role-Based Access Control | ❌ **FAIL** | **CRITICAL** |
| 7 | Post-Submit Data Integrity | ⚠️ PARTIAL PASS | Medium |

**Kết luận tổng thể: ❌ CHƯA ĐỦ ĐIỀU KIỆN NGHIỆM THU**

---

## ACTION PLAN TRƯỚC NGHIỆM THU

| # | Action | Mức độ | Owner | Sprint | Cần verify bởi |
|---|---|---|---|---|---|
| **A1** | Bổ sung IP Address capture vào Event Payload | Medium | Backend Dev | Sprint 2 | QA Lead |
| **A2** | Thêm hook audit log khi đổi `installation_date` | Medium | Backend Dev | Sprint 2 | QA Lead |
| **A3** | Thêm field `amend_reason` bắt buộc | Medium | Backend Dev | Sprint 2 | QMS Reviewer |
| **A4** | Custom hook track Child Table version changes | Medium | Backend Dev | Sprint 2 | QA Lead |
| **A5** | Bắt buộc ảnh xác nhận mặt bằng (`site_photo`) | Medium | Backend Dev | Sprint 2 | QA Lead |
| **A6** | Bắt buộc Vendor upload Evidence sau lắp đặt | Medium | Backend Dev | Sprint 2 | QA Lead |
| **🚨 A7** | **CRITICAL: Khóa field `is_radiation` trên Item DocType với role thường** | **CRITICAL** | **Dev Lead** | **Sprint 2 — BLOCK GO-LIVE** | **QMS Reviewer + Board** |
| **A8** | Viết UAT Test Case cho kịch bản thay đổi `is_radiation` | Critical | QA Lead | Sprint 2 | QMS Reviewer |
| **A9** | Viết Report Query cho KPI "Avg Time to Release" và "DOA Rate" | Low | Report Dev | Sprint 3 | PTP Khối 2 |
| **A10** | Test API authentication và rate limiting | Medium | QA Lead | Sprint 3 | Security Rev |

---

> [!CAUTION]
> **Action A7 là điều kiện CHẶN CỨNG (Go-Live Blocker).** Nếu field `is_radiation` trên Item Master bị KTV thay đổi, toàn bộ cơ chế Clinical Hold cho thiết bị bức xạ bị vô hiệu hóa. Đây là rủi ro an toàn bệnh nhân cấp độ nghiêm trọng — không được phép Go-Live khi chưa giải quyết.

---

**Kiểm định viên QMS:** _________________________ Ngày: _______

**Xác nhận Team Lead:** _________________________ Ngày: _______

**Phê duyệt Go/No-Go:** _________________________ Ngày: _______
