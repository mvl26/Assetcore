# Issue Triage Report — IMM-04 Sandbox / Pilot / UAT
# Phân loại và Đề xuất Xử lý

**Phiên bản:** 1.0 | **Ngày tổng hợp:** 2026-04-15
**Nguồn issue:** Sandbox Round 1 + Conference Room Pilot (giả lập thực tế)
**Tổng số issue:** 22 | 🔴 Critical: 3 | 🟠 Major: 7 | 🟡 Minor: 8 | 🔵 Enhancement: 4

---

## PHẦN 1 — ISSUE TRIAGE TABLE (Toàn bộ)

| ID | Mô tả Issue | Nhóm | Mức độ | Root Cause Giả định | Hướng Xử lý | Đổi Baseline? | Ảnh hưởng Nghiệm thu? | Defer được? |
|---|---|---|---|---|---|---|---|---|
| **ISS-01** | `bench migrate` lỗi `ModuleNotFoundError: assetcore.assetcore` | workflow | 🔴 Critical | DocType đặt sai đường dẫn — thiếu subfolder `assetcore/` trong Python package | Di chuyển DocType vào `assetcore/assetcore/doctype/`, tạo `__init__.py` | Không | Có — chặn toàn bộ hệ thống | Không |
| **ISS-02** | Workflow state `Clinical_Hold` không tự kích hoạt khi `is_radiation=1` | workflow | 🔴 Critical | Server Script `validate_radiation_hold()` chưa được deploy (defer vòng 1) | Viết và deploy server script VR-07 | Không | Có — thiết bị bức xạ không được kiểm soát | Không |
| **ISS-03** | Nút "Approve Release" vẫn hiện với account HTM Technician | permission | 🔴 Critical | Workflow Transition chưa set đúng `allowed_roles` hoặc Permission Level chưa config | Vào Workflow Editor → set `allowed = VP Block2` tại transition Release | Không | Có — vi phạm QMS authorization | Không |
| **ISS-04** | Form Asset Commissioning thiếu loại tài liệu "Biên bản bàn giao" trong bảng hồ sơ | data | 🟠 Major | Checklist hồ sơ thiết kế theo WHO chuẩn, chưa tích hợp thực tế bệnh viện | Thêm row mặc định "Biên bản bàn giao" vào `Commissioning Document Record` với `is_mandatory=True` | Có — bổ sung Requirement REQ-02b | Có — hồ sơ thiếu → gate bị vượt | Không |
| **ISS-05** | Các chỉ tiêu Baseline Test không đúng với thực tế viện (thiếu "Kiểm tra pin dự phòng") | data | 🟠 Major | Dữ liệu mẫu checklist thiết kế theo WHO generic, chưa lấy ý kiến KTS HTM | Bổ sung parameter "Kiểm tra pin dự phòng" và "Kiểm tra báo động hết O2" vào default rows | Không — là dữ liệu, không cần đổi DocType | Có — KTS không dùng được file thực | Không |
| **ISS-06** | Field `vendor_serial_no` cho phép nhập tay, không ép quét Barcode | validation | 🟠 Major | Client Script VR-08 chỉ warn — không lock keyboard thật sự | Tăng từ warn lên block: kiểm tra nếu field được focus từ keyboard (không phải barcode input) → show error | Không | Có — rủi ro nhập sai Serial | Không |
| **ISS-07** | Sau Submit, phiếu bị khóa nhưng Admin vẫn cancel được từ List View | permission | 🟠 Major | Permission Matrix set `cancel=1` cho CMMS Admin quá rộng | Bỏ quyền Cancel của CMMS Admin; chỉ Workshop Head/VP Block2 được Cancel | Không | Có — lỗ hổng QMS | Không |
| **ISS-08** | Naming series sinh ra `IMM04-26-04-00001` nhưng tháng không có số 0 đệm → `IMM04-26-4-00001` | data | 🟠 Major | Format date trong Frappe naming không auto-pad tháng | Dùng `autoname = "format:IMM04-.YYYY.-.MM.-.#####"` với đúng format code | Không | Có — ID trông không chuẩn, ảnh hưởng QMS | Không |
| **ISS-09** | NC được tạo tự động nhưng không có link ngược rõ ràng về phiếu Commissioning ở List View | UI | 🟠 Major | NC List View chưa có column `ref_commissioning` | Thêm `in_list_view=1` cho field `ref_commissioning` + thêm filter shortcut | Không | Có — traceability bị mờ trên màn hình | Không |
| **ISS-10** | KTV không biết phải upload file hay chỉ tick checkbox cho hồ sơ | training | 🟠 Major | UX thiếu tooltip/hướng dẫn rõ ràng; không bắt buộc file attachment | Thêm `description` rõ ràng cho field; bổ sung mandatory attach file khi status = Received | Không | Có — gate hồ sơ bị lách | Không |
| **ISS-11** | Tab "Kết quả Kiểm tra An toàn" hiện ngay ở state Draft gây rối | UI | 🟡 Minor | `_update_field_visibility()` chưa được deploy hoặc có bug | Deploy Client Script C-01; kiểm tra logic `toggle_display` | Không | Không | Không — nhưng nên fix trước CRP |
| **ISS-12** | Label "Giấy phép BYT / Cục An toàn Bức xạ" dài, bị cắt trên màn hình nhỏ | UI | 🟡 Minor | Label quá dài cho field narrow | Rút gọn: "GP Bức xạ (Cục ATBXHN)" — vẫn đủ hiểu | Không | Không | Có |
| **ISS-13** | Message lỗi VR-01 hiển thị bằng tiếng Anh ("Duplicate Entry") | UI | 🟡 Minor | `frappe.throw` đang để message tiếng Anh | Thay toàn bộ message trong `asset_commissioning.py` sang tiếng Việt | Không | Không | Không — fix lẹ |
| **ISS-14** | Không có cách xem nhanh "tất cả thiết bị của 1 Vendor" từ màn hình Vendor | UI | 🟡 Minor | Chưa có Dashboard Link từ Supplier → Asset Commissioning | Thêm Dashboard Link trong Supplier DocType | Không | Không | Có |
| **ISS-15** | Field `installation_date` auto-set bằng server time nhưng UTC, hiển thị sai giờ VN | data | 🟡 Minor | Frappe server timezone chưa set `Asia/Ho_Chi_Minh` | Set `System Settings → Time Zone = Asia/Ho_Chi_Minh` | Không | Không | Không — fix 5 phút |
| **ISS-16** | Không có thông báo nội bộ khi phiếu quá ngày hẹn lắp đặt | report | 🟡 Minor | Scheduler task `check_commissioning_sla()` chưa được enable | Bật scheduled job trong `hooks.py` + confirm scheduler đang chạy | Không | Không | Có — vòng 2 |
| **ISS-17** | Print Layout phiếu Commissioning trông như form ERPNext mặc định, không phù hợp in và ký | UI | 🟡 Minor | Chưa có Custom Print Format | Tạo Print Format riêng cho Asset Commissioning (dạng bảng ký QMS) | Không | Không | Có — vòng 2 |
| **ISS-18** | Kế toán hỏi: Asset tạo ra thiếu trường `gross_purchase_amount` (giá trị tài sản) | data | 🟡 Minor | `mint_core_asset()` set `gross_purchase_amount = 0` | Fetch giá từ PO (`po_reference → grand_total`) và gán vào Asset | Không | Không — Kế toán có thể điền sau | Có |
| **ISS-19** | Muốn export danh sách thiết bị theo Khoa ra Excel | report | 🔵 Enhancement | Chưa có Report | Tạo Query Report "Danh sách thiết bị theo Khoa" | Không | Không | Có — backlog v1.1 |
| **ISS-20** | Muốn thêm trường "Số hợp đồng bảo hành" vào phiếu Commissioning | scope | 🔵 Enhancement | Requirement chưa được capture trong BA gốc | Thêm field `warranty_contract_no` (Data, optional) | Có — bổ sung field | Không | Có — backlog v1.1 |
| **ISS-21** | Góc nhìn Trưởng Workshop: muốn xem KPI "số ngày trung bình từ nhận → release" | report | 🔵 Enhancement | KPI đã thiết kế (REQ-22) nhưng chưa có Report Query | Viết Query Report theo WP-RD-02 | Không | Không | Có — Sprint 3 |
| **ISS-22** | Cần hướng dẫn sử dụng (SOP ngắn) cho từng actor | training | 🔵 Enhancement | Chưa có tài liệu training cho người dùng cuối | Soạn 3 tờ hướng dẫn 1 trang (1-pager) cho KTV, Workshop Head, VP Block2 | Không | Không | Có — trước Go-Live |

---

## PHẦN 2 — FIX-NOW LIST (Phải xử lý trước UAT Final)

*Tất cả 🔴 Critical và 🟠 Major không defer được.*

| Thứ tự | Issue ID | Mô tả | Owner | ETA | Verify bởi |
|---|---|---|---|---|---|
| **1** | ISS-01 | Fix ModuleNotFoundError — migrate thành công | Backend Dev | **Ngay hôm nay** | Dev Lead |
| **2** | ISS-03 | Khóa Workflow Transition Release — chỉ VP Block2 | Backend Dev | **Ngay hôm nay** | QA Lead |
| **3** | ISS-02 | Deploy VR-07 Auto-Hold bức xạ | Backend Dev | Ngày mai | QMS Reviewer |
| **4** | ISS-13 | Dịch tất cả error message sang tiếng Việt | Backend Dev | Ngày mai | QA Lead |
| **5** | ISS-15 | Set timezone `Asia/Ho_Chi_Minh` | Sys Admin | Ngày mai | Dev Lead |
| **6** | ISS-04 | Bổ sung "Biên bản bàn giao" vào Checklist hồ sơ | Backend Dev | 2 ngày | BA + QMS |
| **7** | ISS-05 | Bổ sung chỉ tiêu Baseline phù hợp viện | Backend Dev + KTS HTM | 2 ngày | Trưởng Workshop |
| **8** | ISS-06 | Tăng VR-08 lên block thay vì warn | Backend Dev | 2 ngày | QA Lead |
| **9** | ISS-07 | Bỏ quyền Cancel cho CMMS Admin | Backend Dev | 2 ngày | QMS Reviewer |
| **10** | ISS-08 | Fix naming series format `MM` có padding | Backend Dev | 2 ngày | Dev Lead |
| **11** | ISS-09 | Thêm `ref_commissioning` column vào NC List View | Backend Dev | 2 ngày | QA Lead |
| **12** | ISS-10 | Bổ sung hướng dẫn + bắt file đính kèm khi hồ sơ Received | Backend Dev | 3 ngày | QA + TBYT |
| **13** | ISS-11 | Deploy Client Script C-01 field visibility | Frontend Dev | 3 ngày | QA Lead |

---

## PHẦN 3 — DEFER LIST (Đưa vào vòng sau)

| Issue ID | Mô tả | Vòng | Lý do Defer |
|---|---|---|---|
| ISS-12 | Rút gọn label bức xạ | Vòng 2 | Không ảnh hưởng chức năng |
| ISS-14 | Dashboard Link từ Supplier | v1.1 | Feature phụ |
| ISS-16 | Enable SLA notification scheduler | Vòng 2 | Cần cấu hình scheduler; mock được |
| ISS-17 | Custom Print Format | Vòng 2 | Vẫn in được bằng default; UX thôi |
| ISS-18 | Fetch giá từ PO vào Asset | Vòng 2 | Kế toán nhập sau được |
| ISS-19 | Report xuất Excel theo Khoa | v1.1 | Enhancement; có list view filter |
| ISS-20 | Field `warranty_contract_no` | v1.1 | Scope mở rộng; cần BA confirm |
| ISS-21 | KPI Avg Days to Release Report | Sprint 3 | Đang nằm trong WP-RD-02 |
| ISS-22 | Tài liệu training 1-pager | Trước Go-Live | Cần sau khi UAT xong |

---

## PHẦN 4 — MUST-HAVE BEFORE UAT FINAL

*Đây là rào chắn cứng — UAT Final KHÔNG ĐƯỢC BẮT ĐẦU khi còn issue nào trong danh sách này.*

| # | Tiêu chí | Issue Liên quan | Trạng thái |
|---|---|---|---|
| M-01 | `bench migrate` thành công — không lỗi module | ISS-01 | ☐ |
| M-02 | KTV HTM không thấy / bấm được nút Approve Release | ISS-03 | ☐ |
| M-03 | Auto-Hold bức xạ hoạt động (VR-07) | ISS-02 | ☐ |
| M-04 | Danh sách hồ sơ đã xác nhận với Phòng TBYT (bao gồm Biên bản bàn giao) | ISS-04 | ☐ |
| M-05 | Danh sách chỉ tiêu Baseline đã xác nhận với Trưởng Workshop | ISS-05 | ☐ |
| M-06 | Tất cả error message hiển thị tiếng Việt | ISS-13 | ☐ |
| M-07 | Timezone đã set đúng `Asia/Ho_Chi_Minh` | ISS-15 | ☐ |
| M-08 | Naming series sinh đúng format (có số 0 đệm tháng) | ISS-08 | ☐ |
| M-09 | Field visibility đúng theo từng workflow state | ISS-11 | ☐ |
| M-10 | NC List View có link rõ về phiếu gốc | ISS-09 | ☐ |

**Ký xác nhận M-01 đến M-10 đã đạt:**

| Vai trò | Họ tên | Ngày | Chữ ký |
|---|---|---|---|
| Dev Lead | | | |
| QA Lead | | | |
| QMS Reviewer | | | |

---

## ĐIỀU CHỈNH BASELINE CẦN LÀM

Chỉ có **1 issue** yêu cầu cập nhật Baseline chính thức:

| Issue | Thay đổi Baseline | Tài liệu cập nhật |
|---|---|---|
| ISS-04 | Bổ sung **REQ-02b**: "Biên bản bàn giao bắt buộc trước khi bàn giao mặt bằng" | `IMM-04_Traceability_Matrix.md` (thêm REQ-02b) + `IMM-04_UAT_Script.md` (KB01 Step 4)  |

> [!IMPORTANT]
> ISS-20 (field warranty_contract_no) cũng cần Baseline change nếu được duyệt — nhưng hiện đang Defer. Đừng mở Baseline cho ISS-20 cho đến khi BA confirm.
