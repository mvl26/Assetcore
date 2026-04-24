# IMM-13 — Ngừng sử dụng và Điều chuyển (UAT Script)

| Thuộc tính    | Giá trị                                      |
|---------------|----------------------------------------------|
| Module        | IMM-13 — UAT Script                          |
| Phiên bản     | 2.0.0                                        |
| Ngày cập nhật | 2026-04-24                                   |
| Tổng test     | 20 test cases                                |
| Tester        | QA Team + HTM Manager + CMMS Admin           |

---

## Pre-conditions: Fixture Data

### Users cần tạo

| Username | Email | Role Frappe |
|---|---|---|
| `htm_manager` | `htm@benhvien.vn` | IMM HTM Manager |
| `biomed_eng` | `biomed@benhvien.vn` | IMM Biomed Engineer |
| `qa_officer` | `qa@benhvien.vn` | IMM QA Officer |
| `finance_khtc` | `finance@benhvien.vn` | IMM Finance |
| `network_mgr` | `network@benhvien.vn` | IMM Network Manager |
| `vp_block2` | `vp@benhvien.vn` | IMM VP Block2 |
| `cmms_admin` | `admin@benhvien.vn` | IMM CMMS Admin |

### AC Assets cần tạo

| Asset Name | Mô tả | Status | Location | Ghi chú fixture |
|---|---|---|---|---|
| `ECG-2019-003` | ECG 12-lead Nihon Kohden ECG-1550 | Active | Khoa Tim mạch | Không có WO mở; purchase_date = 7.2 năm trước; expected_life_years = 7 |
| `XRAY-005` | Máy X-Quang Shimadzu | Active | Khoa CĐHA | Có WO-CM-26-00123 ở status "In Repair" |
| `VENT-2018-007` | Máy thở Hamilton T1 | Active | ICU | failure_count_12m = 7; maintenance_cost_ratio = 81.8%; retirement candidate |
| `USG-2023-015` | Siêu âm GE Logiq E10 mới | Active | Khoa Nội | Mới 1.2 năm; không đủ điều kiện retirement candidate |
| `XRAY-BIO-001` | X-Quang cũ có nguồn phóng xạ | Active | Khoa CĐHA | biological_hazard = True trong test |
| `XRAY-DATA-002` | Hệ thống PACS cũ | Active | Khoa CĐHA | data_destruction_required = True trong test |

### Locations cần tạo

| Location | Mô tả |
|---|---|
| `Khoa Tim mạch` | Khoa Tim mạch — tầng 3 nhà A |
| `Khoa Cấp cứu` | Khoa Cấp cứu — tầng 1 nhà B |
| `ICU` | Phòng hồi sức tích cực |
| `Kho tạm HTM` | Kho tạm lưu trữ thiết bị ngừng sử dụng |

---

## Acceptance Criteria (DONE Definition)

Một test case được coi là PASSED khi:
1. Tất cả expected results đều match với actual results
2. Audit trail (Asset Lifecycle Event) được ghi chính xác
3. Không có exception/traceback trong Frappe error log
4. UI hiển thị đúng state, đúng action buttons cho role tương ứng

---

## TC-01: Happy Path — Tạo phiếu ngừng sử dụng thành công

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-01 |
| **Title** | Tạo Decommission Request thành công cho thiết bị EOL |
| **Actor** | HTM Manager (`htm@benhvien.vn`) |
| **Priority** | Critical |
| **Pre-condition** | Asset `ECG-2019-003` có status Active, không có WO mở, không có DR đang mở |

**Steps:**
1. Đăng nhập với role HTM Manager
2. Navigate tới `/imm13/suspensions/new`
3. Tại field Thiết bị: tìm và chọn `ECG-2019-003`
4. Xác nhận asset card hiển thị: Model, vị trí, tuổi 7.2 năm, tổng chi phí BT
5. Chọn `Lý do ngừng` = "End of Life"
6. Nhập `Chi tiết lý do` = "Máy ECG 7 năm, mainboard hỏng, không còn phụ tùng từ nhà sản xuất."
7. Chọn `Tình trạng` = "Non-functional"
8. Để tất cả toggle Tuân thủ ở OFF
9. Click `[Lưu nháp]`

**Expected Result:**
- Phiếu `DR-26-04-00001` được tạo với `workflow_state = Draft`
- Toast: "Phiếu DR-26-04-00001 đã được tạo thành công."
- Redirect về `/imm13/suspensions/DR-26-04-00001`
- ALE `suspension_initiated` được ghi với actor = `htm@benhvien.vn`
- Suspension checklist có 7 default items

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-02: Business Rule BR-13-01 — Chặn tạo khi có Work Order mở

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-02 |
| **Title** | Hệ thống ngăn tạo DR khi asset còn WO đang mở |
| **Actor** | HTM Manager |
| **Priority** | Critical |
| **Pre-condition** | Asset `XRAY-005` có WO-CM-26-00123 ở trạng thái "In Repair" |

**Steps:**
1. Navigate `/imm13/suspensions/new`
2. Chọn asset `XRAY-005`
3. Xác nhận inline warning xuất hiện: "Còn 1 Work Order đang mở — không thể tạo DR"
4. Điền các fields còn lại (suspension_reason, reason_details)
5. Click `[Lưu nháp]`

**Expected Result:**
- Error banner hiển thị ngay khi chọn asset: "Còn 1 Work Order đang mở (WO-CM-26-00123)"
- Khi click Lưu nháp: lỗi `ACTIVE_WO_EXISTS`: "Không thể ngừng sử dụng: Thiết bị XRAY-005 còn 1 Work Order đang mở (WO-CM-26-00123). Đóng tất cả Work Order trước."
- Phiếu không được tạo
- Không có ALE nào được ghi

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-03: Business Rule BR-13-02 — Chặn tạo DR trùng lặp

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-03 |
| **Title** | Không thể tạo DR thứ hai cho asset đã có DR đang xử lý |
| **Actor** | HTM Manager |
| **Priority** | High |
| **Pre-condition** | TC-01 đã pass; DR-26-04-00001 đang ở state Draft cho ECG-2019-003 |

**Steps:**
1. Navigate `/imm13/suspensions/new`
2. Chọn asset `ECG-2019-003`
3. Điền fields và click `[Lưu nháp]`

**Expected Result:**
- Lỗi `DUPLICATE_DR`: "Đã có phiếu DR-26-04-00001 đang xử lý cho thiết bị ECG-2019-003."
- Phiếu thứ 2 không được tạo

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-04: Happy Path — Hoàn thành đánh giá kỹ thuật

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-04 |
| **Title** | Biomed Engineer hoàn thành đánh giá kỹ thuật thành công |
| **Actor** | HTM Manager (gửi), Biomed Engineer (đánh giá) |
| **Priority** | Critical |
| **Pre-condition** | DR-26-04-00001 ở state Draft |

**Steps:**
1. HTM Manager mở DR-26-04-00001 → Action panel: click `[Gửi đánh giá kỹ thuật]`
2. Xác nhận state = "Pending Tech Review"
3. Đăng nhập với Biomed Engineer (`biomed@benhvien.vn`)
4. Mở DR-26-04-00001 → Tab Chi tiết → Action panel đánh giá KT
5. Điền:
   - Kỹ sư: `biomed@benhvien.vn`
   - Tình trạng: "Non-functional"
   - Residual Risk Level: "Low"
   - Residual Risk Notes: "Thiết bị không có nguồn phóng xạ, không có nguy cơ sinh học."
   - Ghi chú KT: "Mainboard ECG cháy hoàn toàn. Nhà sản xuất không còn support phụ tùng."
   - Tuổi TL còn lại: 0 tháng
6. Click `[Hoàn thành đánh giá kỹ thuật]`

**Expected Result:**
- State chuyển sang "Under Replacement Review"
- Toast: "Đánh giá kỹ thuật hoàn thành. Phiếu đã chuyển sang giai đoạn Review thay thế."
- ALE `tech_review_completed` ghi với actor = biomed@benhvien.vn
- Notification email gửi HTM Manager và Finance

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-05: Happy Path — Điều chuyển hoàn tất

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-05 |
| **Title** | Toàn bộ luồng điều chuyển nội viện thành công |
| **Actor** | HTM Manager, Network Manager, CMMS Admin |
| **Priority** | Critical |
| **Pre-condition** | Tạo DR mới cho asset `USG-2023-015` (chưa qua DR nào); hoàn thành đánh giá KT |

**Steps:**
1. Tạo DR cho `USG-2023-015`, gửi đánh giá KT
2. Biomed hoàn thành KT với residual_risk_level = "Medium"
3. HTM Manager mở Review → chọn outcome = "Transfer"
4. Điền: transfer_to_location = "Khoa Cấp cứu", receiving_officer = "nurse@benhvien.vn"
5. Click `[Lưu quyết định]` → state = "Approved for Transfer"
6. Network Manager mở DR → `[Bắt đầu điều chuyển]` → state = "Transfer In Progress"
7. Hoàn thành tất cả checklist items
8. Click `[Hoàn thành điều chuyển]`
9. CMMS Admin submit phiếu

**Expected Result:**
- State = "Transferred"
- `AC Asset USG-2023-015.location` = "Khoa Cấp cứu"
- `AC Asset USG-2023-015.status` = "Transferred"
- ALE `transferred` ghi với from_location = "Khoa Nội", to_location = "Khoa Cấp cứu"
- Asset Movement record được tạo trong ERPNext
- Notification gửi Khoa Cấp cứu

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-06: Business Rule BR-13-06 — Residual Risk bắt buộc

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-06 |
| **Title** | Không thể hoàn thành đánh giá KT khi chưa điền Residual Risk Level |
| **Actor** | Biomed Engineer |
| **Priority** | High |
| **Pre-condition** | Có DR ở state "Pending Tech Review" |

**Steps:**
1. Biomed Engineer mở DR ở state "Pending Tech Review"
2. Điền reviewer, condition, tech_review_notes nhưng **bỏ qua** residual_risk_level
3. Click `[Hoàn thành đánh giá kỹ thuật]`

**Expected Result:**
- Lỗi `RESIDUAL_RISK_MISSING`: "Lỗi BR-13-06: Bắt buộc đánh giá mức độ rủi ro còn lại (Residual Risk Level) trước khi hoàn thành đánh giá kỹ thuật."
- State không thay đổi
- Field residual_risk_level highlight đỏ

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-07: Business Rule BR-13-03 — Bio-hazard clearance bắt buộc

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-07 |
| **Title** | DR với biological_hazard phải có bio_hazard_clearance |
| **Actor** | HTM Manager |
| **Priority** | High |
| **Pre-condition** | Tạo DR mới cho `XRAY-BIO-001` |

**Steps:**
1. Tạo DR cho `XRAY-BIO-001`
2. Bật toggle `Nguy hại sinh học = ON`
3. Để trống trường `Biện pháp xử lý sinh học`
4. Click `[Lưu nháp]`

**Expected Result:**
- Lỗi `BIO_HAZARD_CLEARANCE_MISSING`: "Lỗi BR-13-03: Bắt buộc khai báo biện pháp xử lý an toàn sinh học tại trường 'Bio-Hazard Clearance'."
- Phiếu không được lưu
- Field bio_hazard_clearance hiển thị border đỏ

**Steps 2 (Positive):**
1. Điền `bio_hazard_clearance` = "Đã vệ sinh theo QT-VSSH-001, giao cho đơn vị xử lý chất thải y tế."
2. Click `[Lưu nháp]`

**Expected Result 2:**
- Phiếu được lưu thành công với biological_hazard = True và bio_hazard_clearance filled

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-08: Business Rule BR-13-05 — Data Destruction phải confirm trước Submit

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-08 |
| **Title** | Không thể submit DR có data_destruction_required = True khi chưa confirm xóa dữ liệu |
| **Actor** | CMMS Admin |
| **Priority** | High |
| **Pre-condition** | DR-XRAY-DATA với data_destruction_required = True ở state "Pending Decommission", approved = True |

**Steps:**
1. CMMS Admin mở DR có data_destruction_required = True
2. Đảm bảo data_destruction_confirmed = False
3. Click `[Submit - Hoàn tất ngừng sử dụng]`

**Expected Result:**
- Lỗi `DATA_DESTRUCTION_NOT_CONFIRMED`: "Lỗi BR-13-05: Thiết bị có dữ liệu bệnh nhân cần xóa. Phải xác nhận đã xóa dữ liệu (data_destruction_confirmed) trước khi Submit."
- Submit bị chặn

**Steps 2 (Positive):**
1. Tích checkbox `data_destruction_confirmed = True`
2. Click Submit

**Expected Result 2:**
- Submit thành công → state = "Completed"

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-09: Business Rule BR-13-08 — High Value cần VP Approval

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-09 |
| **Title** | DR với book_value > 500M cần VP Block2 approve trước khi submit |
| **Actor** | CMMS Admin, VP Block2 |
| **Priority** | High |
| **Pre-condition** | Tạo DR với current_book_value = 650,000,000; ở state "Pending Decommission", approved = False |

**Steps:**
1. CMMS Admin cố submit DR chưa có VP approval
2. Xác nhận bị chặn
3. VP Block2 approve DR
4. CMMS Admin submit lại

**Expected Result (Step 1-2):**
- Lỗi `VP_APPROVAL_REQUIRED`: "Lỗi BR-13-08: Giá trị sổ sách > 500 triệu VNĐ. Bắt buộc có phê duyệt VP Block2 trước khi Submit."

**Expected Result (Step 4):**
- Submit thành công

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-10: Business Rule BR-13-11 — Từ chối phải có lý do

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-10 |
| **Title** | Không thể hủy phiếu DR khi chưa điền rejection_reason |
| **Actor** | CMMS Admin |
| **Priority** | Medium |
| **Pre-condition** | Có DR ở state Draft hoặc Pending Tech Review |

**Steps:**
1. CMMS Admin gọi `cancel_suspension_request` với rejection_reason = ""
2. Hoặc: VP Block2 click `[Từ chối]` mà không điền lý do trong modal

**Expected Result:**
- Lỗi `REJECTION_REASON_MISSING`: "Lỗi BR-13-11: Bắt buộc nhập lý do từ chối."
- State không thay đổi

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-11: Workflow Transition — Từ chối tại bước kỹ thuật

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-11 |
| **Title** | Biomed Engineer từ chối → DR Cancelled, asset không đổi status |
| **Actor** | Biomed Engineer |
| **Priority** | High |
| **Pre-condition** | DR ở state "Pending Tech Review" |

**Steps:**
1. Biomed Engineer mở phiếu
2. Click `[Từ chối - Có thể sửa chữa]`
3. Modal xác nhận: điền `rejection_reason` = "Thiết bị vẫn có khả năng sửa mainboard. Đề xuất chuyển sang IMM-09."
4. Confirm từ chối

**Expected Result:**
- State = "Cancelled"
- `AC Asset ECG-2019-003.status` giữ nguyên = "Active" (KHÔNG đổi)
- ALE `tech_review_rejected` được ghi
- Notification gửi HTM Manager với rejection_reason
- Phiếu hiển thị read-only với rejection_reason

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-12: Workflow Transition — VP Từ chối → Cancelled

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-12 |
| **Title** | VP Block2 từ chối → DR Cancelled, asset giữ nguyên |
| **Actor** | VP Block2 |
| **Priority** | High |
| **Pre-condition** | DR ở state "Pending Decommission" |

**Steps:**
1. VP Block2 mở phiếu
2. Click `[Từ chối - Hủy phiếu]`
3. Điền `rejection_reason` = "Thiết bị có thể điều chuyển cho cơ sở y tế tuyến dưới. Đề xuất IMM-13 với outcome Transfer."
4. Confirm

**Expected Result:**
- State = "Cancelled"
- Asset.status = "Active" (không đổi)
- ALE `suspension_rejected` được ghi
- HTM Manager nhận notification với lý do

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-13: Workflow Transition — Chuỗi đầy đủ Retire → Completed

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-13 |
| **Title** | Toàn bộ workflow Retire từ Draft đến Completed (golden path) |
| **Actor** | Tất cả actors |
| **Priority** | Critical |
| **Pre-condition** | Asset `VENT-2018-007` không có WO mở; tạo mới để test |

**Steps:**
1. HTM Manager tạo DR cho VENT-2018-007 → Gửi đánh giá KT
2. Biomed hoàn thành KT (residual_risk_level = Low) → Under Replacement Review
3. HTM Manager vào Replacement Review → outcome = Retire, replacement_needed = No
4. Lưu quyết định → Pending Decommission
5. VP Block2 approve
6. HTM Manager + Biomed hoàn thành tất cả 7 checklist items
7. CMMS Admin submit → Completed

**Expected Result:**
- Mỗi state transition có ALE tương ứng (tổng 6 ALE)
- Asset.status = "Suspended"
- IMM-14 record được auto-create
- Không có exception trong Frappe log

**Kiểm tra ALE chain:**
| # | event_type | actor role |
|---|---|---|
| 1 | suspension_initiated | HTM Manager |
| 2 | tech_review_completed | Biomed Engineer |
| 3 | replacement_review_completed | HTM Manager |
| 4 | suspension_approved | VP Block2 |
| 5 | suspended | CMMS Admin |
| 6 | imm14_triggered | System |

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-14: Workflow Transition — Không thể tạo WO sau khi Retire

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-14 |
| **Title** | Asset đã Suspended không thể tạo Work Order mới (BR-13-12) |
| **Actor** | HTM Manager |
| **Priority** | High |
| **Pre-condition** | TC-13 pass; VENT-2018-007.status = "Suspended" |

**Steps:**
1. HTM Manager cố tạo PM Work Order cho asset VENT-2018-007

**Expected Result:**
- Validation error: "Không thể tạo Work Order cho thiết bị đã ngừng sử dụng (Suspended)."

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-15: Workflow Transition — Kiểm tra Permission Matrix

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-15 |
| **Title** | Mỗi role chỉ thực hiện được action trong phạm vi quyền |
| **Actor** | Finance (`finance@benhvien.vn`) |
| **Priority** | High |
| **Pre-condition** | Có DR ở state "Pending Tech Review" |

**Steps:**
1. Finance login → mở DR ở "Pending Tech Review"
2. Kiểm tra: không có action button "Hoàn thành đánh giá KT" (chỉ Biomed mới có)
3. Finance thử gọi API `submit_technical_review` trực tiếp

**Expected Result:**
- UI không hiển thị action button đánh giá KT cho Finance role
- API trả về lỗi 403: `PERMISSION_DENIED`

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-16: Integration — IMM-12 Chronic Failure → Auto-flag Retirement Candidate

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-16 |
| **Title** | IMM-12 chronic failure tự động flag thiết bị là Retirement Candidate |
| **Actor** | System (Scheduler), HTM Manager (xem) |
| **Priority** | High |
| **Pre-condition** | Asset `VENT-2018-007` có 7 CM Work Orders Completed trong 12 tháng; Scheduler job enabled |

**Steps:**
1. Chạy scheduler job: `bench execute assetcore.services.imm13.check_retirement_candidates`
2. Kiểm tra `AC Asset VENT-2018-007.is_retirement_candidate`
3. Kiểm tra notification gửi HTM Manager
4. HTM Manager mở dashboard `/imm13/dashboard`
5. Xác nhận VENT-2018-007 xuất hiện trong bảng Retirement Candidates

**Expected Result:**
- `VENT-2018-007.is_retirement_candidate = 1`
- `VENT-2018-007.retirement_flag_reason` = "Số lần hỏng 12 tháng: 7 (ngưỡng: 5)"
- Notification email gửi HTM Manager
- Dashboard hiển thị VENT-2018-007 với risk_score ≥ 75

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-17: Integration — IMM-13 Transfer → IMM-14 Không trigger

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-17 |
| **Title** | Khi outcome = Transfer, IMM-14 KHÔNG được tạo (chỉ trigger khi Retire) |
| **Actor** | CMMS Admin |
| **Priority** | High |
| **Pre-condition** | TC-05 (Transfer flow) đã pass |

**Steps:**
1. Kiểm tra sau khi TC-05 completed
2. Query: `frappe.get_all("Asset Archive Record", filters={"asset": "USG-2023-015"})`

**Expected Result:**
- Không có `Asset Archive Record` nào được tạo cho `USG-2023-015`
- Response: empty list
- IMM-14 chỉ được trigger khi `outcome = "Retire"` (TC-13 verify)

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-18: Integration — IMM-13 Retire → IMM-14 Auto-create

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-18 |
| **Title** | Khi outcome = Retire và submit, IMM-14 record được tạo tự động |
| **Actor** | System (on_submit) |
| **Priority** | Critical |
| **Pre-condition** | TC-13 (full Retire workflow) đã pass |

**Steps:**
1. Sau khi TC-13 completed, query:
   ```python
   frappe.get_all("Asset Archive Record", 
       filters={"asset": "VENT-2018-007"},
       fields=["name", "status", "suspension_request", "archive_date"])
   ```
2. Mở IMM-14 record từ link trong DR Completed view

**Expected Result:**
- Tồn tại 1 `Asset Archive Record` với:
  - `asset = VENT-2018-007`
  - `suspension_request = DR-26-04-00xxx`
  - `status = Draft`
  - `retention_years = 10`
  - `archive_date = today`
- Link `[Xem IMM-14 →]` hiển thị đúng trong DR Detail view
- ALE `imm14_triggered` được ghi

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-19: Dashboard & Reporting — Metrics Accuracy

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-19 |
| **Title** | Dashboard metrics chính xác sau khi hoàn thành các TC |
| **Actor** | HTM Manager |
| **Priority** | Medium |
| **Pre-condition** | TC-01 đến TC-18 đã chạy; biết số phiếu Completed, Transferred, Cancelled |

**Steps:**
1. Gọi API `GET get_dashboard_metrics?year=2026`
2. Mở `/imm13/dashboard`
3. So sánh số liệu với manual count

**Expected Result:**
- `suspended_ytd` = số phiếu outcome=Retire/Suspend đã Completed
- `transferred_ytd` = số phiếu Transferred
- `retirement_candidates_count` ≥ 1 (VENT-2018-007)
- `avg_days_to_complete` > 0
- `residual_risk_distribution` tổng = tổng phiếu Completed + Transferred
- Charts hiển thị đúng (không có empty/NaN)
- KRI alerts hiển thị đúng (nếu có vi phạm ngưỡng)

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## TC-20: Dashboard & Reporting — Transfer History

| Trường | Nội dung |
|---|---|
| **ID** | TC-13-20 |
| **Title** | API get_transfer_history trả về lịch sử điều chuyển chính xác |
| **Actor** | HTM Manager (via API hoặc UI) |
| **Priority** | Medium |
| **Pre-condition** | TC-05 đã pass (USG-2023-015 đã Transferred đến Khoa Cấp cứu) |

**Steps:**
1. Gọi API: `GET get_transfer_history?asset=USG-2023-015`
2. Gọi API: `GET get_transfer_history?to_location=Khoa Cấp cứu`
3. Gọi API filter ngày: `GET get_transfer_history?from_date=2026-04-01&to_date=2026-04-30`

**Expected Result (Step 1):**
```json
{
  "success": true,
  "data": {
    "rows": [{
      "asset": "USG-2023-015",
      "from_location": "Khoa Nội",
      "to_location": "Khoa Cấp cứu",
      "handover_confirmed": true
    }],
    "total": 1
  }
}
```

**Expected Result (Step 2):**
- Trả về tất cả transfers đến Khoa Cấp cứu (bao gồm USG-2023-015)

**Expected Result (Step 3):**
- Trả về transfers trong tháng 4/2026

**Actual Result:** `_______________`
**Pass / Fail:** `[ ]`

---

## Test Execution Summary

| Phase | TCs | Pass | Fail | Not Run |
|---|---|---|---|---|
| Happy Path (TC-01 → TC-05) | 5 | | | |
| Business Rules (TC-06 → TC-10) | 5 | | | |
| Workflow Transitions (TC-11 → TC-15) | 5 | | | |
| Integration (TC-16 → TC-18) | 3 | | | |
| Dashboard & Reporting (TC-19 → TC-20) | 2 | | | |
| **Tổng** | **20** | | | |

---

## Sign-off

| Vai trò | Tên | Ngày | Chữ ký |
|---|---|---|---|
| Test Lead (HTM Manager) | | | |
| QA Officer | | | |
| CMMS Admin | | | |
| Module Owner | | | |

---

*End of UAT Script v2.0.0 — IMM-13 Ngừng sử dụng và Điều chuyển | 20 Test Cases*
