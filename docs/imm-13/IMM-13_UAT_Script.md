# IMM-13 — Thanh lý Thiết bị Y tế (UAT Script)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-13 — UAT Script |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Tổng test cases | 20 |

---

## Điều kiện tiên quyết

- Hệ thống đã có dữ liệu: AC Asset `MRI-2024-001` (status Active), `XRAY-005` (có WO mở)
- Users test: `htm@hosp.vn` (HTM Manager), `biomed@hosp.vn` (Biomed Engineer), `finance@hosp.vn` (Finance Director), `vp@hosp.vn` (VP Block2), `admin@hosp.vn` (CMMS Admin)

---

## TC-01: Tạo phiếu thanh lý cơ bản

| | |
|---|---|
| **Mô tả** | Tạo phiếu Decommission Request thành công |
| **Actor** | HTM Manager |
| **Precondition** | MRI-2024-001 active, không có WO mở |
| **Steps** | 1. Mở `/decommission/create` → 2. Chọn asset MRI-2024-001 → 3. Chọn reason "End of Life" → 4. Nhập reason_details → 5. Bấm Tạo |
| **Expected** | DR-26-04-00001 created, status=Draft |
| **Status** | TODO |

## TC-02: VR-01 — Block tạo khi có WO mở

| | |
|---|---|
| **Mô tả** | Hệ thống chặn tạo phiếu khi thiết bị còn WO mở |
| **Actor** | HTM Manager |
| **Precondition** | XRAY-005 có WO-CM-2026-00123 ở trạng thái In Repair |
| **Steps** | Tạo DR cho XRAY-005 |
| **Expected** | Lỗi VR-01: "Không thể thanh lý: Thiết bị XRAY-005 còn 1 lệnh..." |
| **Status** | TODO |

## TC-03: Gửi đánh giá kỹ thuật

| | |
|---|---|
| **Mô tả** | HTM Manager gửi phiếu sang Technical Review |
| **Steps** | 1. Mở DR-26-04-00001 ở Draft → 2. Bấm "Gửi đánh giá kỹ thuật" |
| **Expected** | Status = Technical Review, notification gửi Biomed Engineer |
| **Status** | TODO |

## TC-04: Hoàn thành đánh giá kỹ thuật

| | |
|---|---|
| **Actor** | Biomed Engineer |
| **Steps** | Điền technical_reviewer, review_notes → Bấm "Hoàn thành" |
| **Expected** | Status = Financial Valuation |
| **Status** | TODO |

## TC-05: Từ chối tại bước kỹ thuật

| | |
|---|---|
| **Actor** | Biomed Engineer |
| **Steps** | Bấm "Từ chối" với lý do |
| **Expected** | Status = Rejected, asset.status không đổi |
| **Status** | TODO |

## TC-06: Định giá tài chính

| | |
|---|---|
| **Actor** | Finance Director |
| **Steps** | Điền finance_reviewer, current_book_value=150000000, estimated_disposal_value=20000000 → Hoàn thành |
| **Expected** | Status = Pending Approval |
| **Status** | TODO |

## TC-07: VR-02 — Cảnh báo ngưỡng Board (book value > 500M)

| | |
|---|---|
| **Steps** | Điền current_book_value = 600000000 |
| **Expected** | Warning: "Giá trị sổ sách > 500 triệu VNĐ — cần phê duyệt BGĐ" |
| **Status** | TODO |

## TC-08: Phê duyệt Board

| | |
|---|---|
| **Actor** | VP Block2 |
| **Steps** | Điền approved_by, approval_notes → Phê duyệt |
| **Expected** | Status = Board Approved |
| **Status** | TODO |

## TC-09: Từ chối phê duyệt

| | |
|---|---|
| **Actor** | VP Block2 |
| **Steps** | Bấm "Từ chối" với lý do |
| **Expected** | Status = Rejected |
| **Status** | TODO |

## TC-10: Bắt đầu thực thi thanh lý

| | |
|---|---|
| **Actor** | HTM Manager |
| **Steps** | Bấm "Bắt đầu thực thi" |
| **Expected** | Status = Execution |
| **Status** | TODO |

## TC-11: Hoàn thành checklist item

| | |
|---|---|
| **Steps** | Đánh dấu checklist_item "Thu hồi thiết bị" là completed |
| **Expected** | Item.completed = True, Item.completion_date = today |
| **Status** | TODO |

## TC-12: VR-03 — Bio-hazard không có clearance

| | |
|---|---|
| **Steps** | Set biological_hazard = True, để bio_hazard_clearance trống → Save |
| **Expected** | Lỗi VR-03: "Bắt buộc khai báo biện pháp xử lý an toàn sinh học" |
| **Status** | TODO |

## TC-13: VR-04 — Regulatory clearance required

| | |
|---|---|
| **Steps** | Set regulatory_clearance_required = True, không upload file → Save |
| **Expected** | Lỗi VR-04: "Bắt buộc upload file giấy phép thanh lý" |
| **Status** | TODO |

## TC-14: VR-05 — Data destruction required không confirmed

| | |
|---|---|
| **Steps** | Set data_destruction_required = True, data_destruction_confirmed = False → Submit |
| **Expected** | Lỗi VR-05: "Phải xác nhận đã xoá dữ liệu trước khi Submit" |
| **Status** | TODO |

## TC-15: Submit thành công → Asset Decommissioned

| | |
|---|---|
| **Actor** | CMMS Admin |
| **Precondition** | Tất cả VR pass, status = Execution |
| **Steps** | Submit phiếu |
| **Expected** | Status = Completed, AC Asset.status = Decommissioned, ALE "decommissioned" được tạo |
| **Status** | TODO |

## TC-16: Auto-create IMM-14 Archive Record

| | |
|---|---|
| **Precondition** | TC-15 pass |
| **Expected** | Asset Archive Record AAR-26-00001 được tạo tự động với asset = MRI-2024-001, status = Draft |
| **Status** | TODO |

## TC-17: Dashboard stats

| | |
|---|---|
| **Steps** | GET /api/method/assetcore.api.imm13.get_dashboard_stats |
| **Expected** | decommissioned_ytd > 0, avg_days_to_complete > 0 |
| **Status** | TODO |

## TC-18: get_asset_decommission_eligibility — eligible

| | |
|---|---|
| **Steps** | GET eligibility cho MRI-2024-001 (WO đã đóng) |
| **Expected** | eligible = true |
| **Status** | TODO |

## TC-19: get_asset_decommission_eligibility — not eligible

| | |
|---|---|
| **Steps** | GET eligibility cho XRAY-005 (WO mở) |
| **Expected** | eligible = false, reasons có WO names |
| **Status** | TODO |

## TC-20: List với filter

| | |
|---|---|
| **Steps** | GET list_decommission_requests?status=Technical Review |
| **Expected** | Chỉ trả về phiếu có status = Technical Review |
| **Status** | TODO |

---

*End of UAT Script v1.0.0 — IMM-13 | 20 Test Cases*
