# IMM-13 — Ngừng sử dụng và Điều chuyển (Functional Specifications)

| Thuộc tính    | Giá trị                                              |
|---------------|------------------------------------------------------|
| Module        | IMM-13 — Suspension & Transfer                       |
| Phiên bản     | 2.0.0                                                |
| Ngày cập nhật | 2026-04-24                                           |
| Chuẩn áp dụng | WHO HTM Decommissioning Guide · WHO 2025 §3.2 · NĐ98/2021 |

---

## 1. Phạm vi

IMM-13 quản lý toàn bộ quy trình **ngừng sử dụng lâm sàng** và **điều chuyển** thiết bị y tế:

- Khởi tạo yêu cầu ngừng sử dụng (triggered từ IMM-08/09/11/12 hoặc chủ động)
- Đánh giá kỹ thuật + residual risk assessment
- Review khả năng thay thế thiết bị (replacement review)
- Điều chuyển nội viện hoặc liên cơ sở
- Phê duyệt đa cấp cho các quyết định ngừng/điều chuyển
- Thực thi ngừng sử dụng + cập nhật location (nếu điều chuyển)
- Trigger IMM-14 nếu outcome = Retire/Decommission

**Ngoài phạm vi:**
- Thanh lý vật lý / hủy thiết bị (thuộc IMM-14)
- Đóng hồ sơ kế toán-kho (thuộc IMM-14)
- Sửa chữa (IMM-09), Hiệu chuẩn (IMM-11)

---

## 2. Actors

| Actor | Frappe Role | Mô tả |
|---|---|---|
| HTM Manager | IMM HTM Manager | Người khởi tạo, giám sát toàn quy trình |
| Biomed Engineer | IMM Biomed Engineer | Thực hiện đánh giá kỹ thuật + residual risk |
| QA Officer | IMM QA Officer | Kiểm tra tuân thủ pháp lý, clearance sinh học |
| Finance (KH-TC) | IMM Finance | Review kinh tế, replacement cost analysis |
| Network Manager | IMM Network Manager | Điều phối điều chuyển nội viện / liên cơ sở |
| VP Block2 | IMM VP Block2 | Phê duyệt cấp khối (thiết bị thuộc Block2) |
| CMMS Admin | IMM CMMS Admin | Submit phiếu, trigger IMM-14, quản trị hệ thống |

---

## 3. Use Cases

### UC-13-01: Khởi tạo yêu cầu ngừng sử dụng

**Actor chính:** HTM Manager  
**Trigger:** Thiết bị đến EOL, BER, không tuân thủ, hoặc auto-flagged từ IMM-12  
**Pre-condition:** Asset tồn tại, status không phải Decommissioned, không có DR đang mở

**Luồng chính:**
1. HTM Manager vào `/imm13/suspensions/new`
2. Chọn asset → hệ thống auto-load thông tin (model, tuổi, maintenance cost tích lũy)
3. Nhập `suspension_reason`, `reason_details`, `condition_at_suspension`
4. Điền thông tin tuân thủ (biological_hazard, data_destruction_required, regulatory_clearance_required)
5. Lưu nháp → DR-YY-MM-##### được tạo với state `Draft`
6. Bấm "Gửi đánh giá kỹ thuật" → state chuyển sang `Pending Tech Review`
7. Thông báo tự động gửi Biomed Engineer + QA Officer

**Business Rules áp dụng:** BR-13-01, BR-13-03, BR-13-04, BR-13-05  
**Audit trail:** ALE `suspension_initiated` được ghi

```gherkin
Scenario: Tạo yêu cầu ngừng sử dụng thành công
  Given HTM Manager đăng nhập với role "IMM HTM Manager"
  And Asset "ECG-2019-003" có status "Active" và không có WO mở
  And Không có Decommission Request nào đang mở cho "ECG-2019-003"
  When HTM Manager tạo Decommission Request với:
    | asset              | ECG-2019-003              |
    | suspension_reason  | End of Life               |
    | reason_details     | Máy ECG 7 năm, hỏng mainboard, không có phụ tùng |
    | condition_at_suspension | Non-functional       |
  Then Phiếu DR-26-04-00001 được tạo với state "Draft"
  And ALE "suspension_initiated" được ghi với actor = HTM Manager

Scenario: Ngăn tạo khi còn Work Order mở (BR-13-01)
  Given Asset "XRAY-005" có WO "WO-CM-26-00123" ở trạng thái "In Repair"
  When HTM Manager tạo Decommission Request cho "XRAY-005"
  Then Hệ thống throw lỗi:
    "Không thể ngừng sử dụng: Thiết bị XRAY-005 còn 1 Work Order đang mở (WO-CM-26-00123). Đóng tất cả Work Order trước."
  And Phiếu không được tạo

Scenario: Auto-flag từ IMM-12 chronic failure
  Given IMM-12 scheduler phát hiện asset "VENT-2018-007" có failure_count_12m = 8 (> threshold 5)
  When Scheduler chạy check_retirement_candidates()
  Then Asset "VENT-2018-007" được thêm vào danh sách Retirement Candidates
  And Notification gửi HTM Manager gợi ý tạo DR cho "VENT-2018-007"
```

---

### UC-13-02: Đánh giá kỹ thuật và Residual Risk

**Actor chính:** Biomed Engineer  
**Pre-condition:** DR ở state `Pending Tech Review`

**Luồng chính:**
1. Biomed Engineer nhận notification, mở DR
2. Thực hiện kiểm tra thực tế tại khoa
3. Điền `technical_reviewer`, `tech_review_date`, `tech_review_notes`
4. Điền `condition_assessment` (Poor / Non-functional / Partially Functional / Functional but Obsolete)
5. Điền `residual_risk_level` (Low / Medium / High / Critical) và `residual_risk_notes`
6. Điền `estimated_remaining_life` (tháng)
7. Ghi nhận `asset_age_years`, `maintenance_cost_total`, `downtime_percent_12m`
8. Nếu approve kỹ thuật → state → `Under Replacement Review`; nếu từ chối → `Cancelled`
9. QA Officer kiểm tra clearance sinh học song song (không blocking nếu không phải bio-hazard)

**Business Rules áp dụng:** BR-13-06 (residual risk bắt buộc), BR-13-03  
**Audit trail:** ALE `tech_review_completed` hoặc `tech_review_rejected`

```gherkin
Scenario: Đánh giá kỹ thuật hoàn thành với residual risk
  Given DR-26-04-00001 ở state "Pending Tech Review"
  And Biomed Engineer đã kiểm tra thực tế thiết bị
  When Biomed Engineer điền:
    | technical_reviewer       | biomed@benhvien.vn         |
    | condition_assessment     | Non-functional             |
    | residual_risk_level      | Low                        |
    | residual_risk_notes      | Thiết bị hỏng mainboard, không còn tia bức xạ rủi ro |
    | estimated_remaining_life | 0                          |
  And bấm "Hoàn thành đánh giá kỹ thuật"
  Then State chuyển sang "Under Replacement Review"
  And ALE "tech_review_completed" được ghi
  And Notification gửi HTM Manager + Finance

Scenario: Thiếu residual_risk_level → không cho chuyển trạng thái (BR-13-06)
  Given DR ở state "Pending Tech Review"
  When Biomed Engineer bấm hoàn thành mà chưa điền residual_risk_level
  Then Hệ thống throw lỗi:
    "Lỗi BR-13-06: Bắt buộc đánh giá mức độ rủi ro còn lại (Residual Risk Level) trước khi hoàn thành đánh giá kỹ thuật."
```

---

### UC-13-03: Review thay thế (Replacement Review)

**Actor chính:** HTM Manager, Finance (KH-TC), QA Officer  
**Pre-condition:** DR ở state `Under Replacement Review`

**Luồng chính:**
1. HTM Manager mở màn hình Replacement Review
2. Điền `replacement_needed` (Yes / No / Deferred)
3. Nếu Yes: điền `replacement_device_model`, `replacement_estimated_cost`, `replacement_timeline`
4. Finance điền `current_book_value`, `maintenance_cost_ratio` (auto-calc), `economic_justification`
5. QA Officer xác nhận `regulatory_compliance_status` và upload clearance docs nếu cần
6. HTM Manager chọn `outcome`:
   - `Transfer`: điều chuyển sang đơn vị khác
   - `Suspend`: tạm ngừng, chờ replacement
   - `Retire`: ngừng hẳn → trigger IMM-14
7. Bấm "Quyết định" → chuyển state tương ứng:
   - Transfer → `Approved for Transfer`
   - Suspend/Retire → `Pending Decommission` (cần phê duyệt VP)

**Business Rules áp dụng:** BR-13-07 (replacement review bắt buộc nếu residual_risk=High/Critical), BR-13-08 (economic justification > 500M cần Board)  
**Audit trail:** ALE `replacement_review_completed`

```gherkin
Scenario: Quyết định điều chuyển nội viện
  Given DR-26-04-00001 ở state "Under Replacement Review"
  When HTM Manager chọn outcome = "Transfer" và transfer_to = "Khoa Cấp cứu"
  Then State chuyển sang "Approved for Transfer"
  And ALE "transfer_approved" được ghi
  And Notification gửi Network Manager

Scenario: Quyết định retire → cần phê duyệt VP (BR-13-08)
  Given DR có current_book_value = 650000000 (>500M)
  When HTM Manager chọn outcome = "Retire"
  Then Hệ thống hiển thị warning:
    "Cảnh báo BR-13-08: Giá trị sổ sách > 500 triệu VNĐ. Phiếu này cần phê duyệt của VP Block2 trước khi thực thi."
  And State chuyển sang "Pending Decommission" (chờ VP approve)
```

---

### UC-13-04: Điều chuyển nội viện

**Actor chính:** Network Manager, HTM Manager  
**Pre-condition:** DR ở state `Approved for Transfer`

**Luồng chính:**
1. Network Manager mở DR, điền `Transfer Detail` child table:
   - `transfer_to_location`, `transfer_to_department`, `receiving_officer`
   - `transfer_date`, `transfer_conditions`, `transport_notes`
2. Bấm "Bắt đầu điều chuyển" → state → `Transfer In Progress`
3. Thực hiện điều chuyển vật lý, hoàn thành `Suspension Checklist`
4. Bấm "Hoàn thành điều chuyển" → submit DR → state → `Transferred`
5. on_submit:
   - `asset.location` = `transfer_to_location`
   - `asset.status` = `Transferred`
   - ALE `transferred` được ghi
   - Notification gửi khoa nhận

**Business Rules áp dụng:** BR-13-09 (location phải hợp lệ), BR-13-10 (receiving_officer bắt buộc)  
**Audit trail:** ALE `transfer_started`, `transferred`

```gherkin
Scenario: Điều chuyển hoàn thành thành công
  Given DR-26-04-00001 ở state "Transfer In Progress"
  And Tất cả suspension_checklist items đã completed
  When CMMS Admin submit phiếu
  Then State → "Transferred"
  And AC Asset "ECG-2019-003".location = "Khoa Cấp cứu"
  And AC Asset "ECG-2019-003".status = "Transferred"
  And ALE "transferred" được ghi với from_location và to_location

Scenario: Không thể điều chuyển nếu thiếu receiving_officer (BR-13-10)
  When Network Manager bấm hoàn thành điều chuyển mà chưa điền receiving_officer
  Then Lỗi: "Lỗi BR-13-10: Bắt buộc có người tiếp nhận (receiving_officer) để hoàn thành điều chuyển."
```

---

### UC-13-05: Phê duyệt ngừng sử dụng

**Actor chính:** VP Block2  
**Pre-condition:** DR ở state `Pending Decommission`, outcome = `Suspend` hoặc `Retire`

**Luồng chính:**
1. VP Block2 nhận notification, mở DR
2. Xem xét đánh giá kỹ thuật, residual risk, replacement review
3. Approve → `approved_by`, `approval_date`, `approval_notes` được ghi
4. Bấm "Phê duyệt" → state vẫn là `Pending Decommission` nhưng có `approved = True`
5. CMMS Admin submit → state → `Completed`
6. Nếu VP từ chối → state → `Cancelled`

**Business Rules áp dụng:** BR-13-08 (book_value > 500M cần VP), BR-13-11 (từ chối phải có lý do)  
**Audit trail:** ALE `suspension_approved` hoặc `suspension_rejected`

```gherkin
Scenario: VP Block2 phê duyệt ngừng sử dụng
  Given DR-26-04-00001 ở state "Pending Decommission" với residual_risk_level = Low
  When VP Block2 phê duyệt với notes = "Thiết bị EOL đã 7 năm, đồng ý ngừng."
  Then approved = True, approved_by = VP, approval_date = today
  And ALE "suspension_approved" được ghi
  And Notification gửi CMMS Admin để submit

Scenario: VP từ chối không có lý do (BR-13-11)
  When VP Block2 bấm "Từ chối" mà không điền rejection_reason
  Then Lỗi: "Lỗi BR-13-11: Bắt buộc nhập lý do từ chối."
```

---

### UC-13-06: Thực thi ngừng sử dụng

**Actor chính:** HTM Manager, CMMS Admin  
**Pre-condition:** DR ở `Pending Decommission` với approved = True

**Luồng chính:**
1. HTM Manager hoàn thành `Suspension Checklist`:
   - Thu hồi thiết bị từ khoa sử dụng
   - Gắn nhãn "NGỪNG SỬ DỤNG"
   - Kiểm kê phụ tùng / phụ kiện
   - Xóa dữ liệu bệnh nhân (nếu data_destruction_required)
   - Xử lý sinh học (nếu biological_hazard)
   - Lưu kho tạm / chờ IMM-14
2. CMMS Admin submit DR → state → `Completed`
3. on_submit:
   - `asset.status` = `Suspended`
   - ALE `suspended` được ghi
   - Nếu outcome = `Retire`: auto-create IMM-14 Decommission closure record
4. Notification gửi Finance và Kho để chuẩn bị IMM-14

**Business Rules áp dụng:** BR-13-03, BR-13-04, BR-13-05  
**Audit trail:** ALE `suspended`, `imm14_triggered`

```gherkin
Scenario: Thực thi ngừng thành công → trigger IMM-14
  Given DR-26-04-00001 ở state "Pending Decommission" với outcome = "Retire"
  And approved = True
  And data_destruction_required = True AND data_destruction_confirmed = True
  And biological_hazard = False
  When CMMS Admin submit phiếu
  Then State → "Completed"
  And AC Asset.status = "Suspended"
  And ALE "suspended" được ghi
  And IMM-14 record được tạo tự động với asset = ECG-2019-003
  And Notification gửi Finance + Kho

Scenario: VR-05 — Data destruction chưa confirm → chặn submit
  Given DR có data_destruction_required = True, data_destruction_confirmed = False
  When CMMS Admin cố submit
  Then Lỗi VR-05: "Lỗi VR-05: Thiết bị có dữ liệu bệnh nhân. Phải xác nhận đã xóa dữ liệu (data_destruction_confirmed) trước khi Submit."
```

---

### UC-13-07: Dashboard và Báo cáo

**Actor chính:** HTM Manager, CMMS Admin, VP Block2  
**Màn hình:** `/imm13/dashboard` (Retirement Candidates Dashboard)

**Tính năng:**
1. KPI cards: Suspended YTD, Transferred YTD, Retirement Candidates, Avg Days to Complete
2. Bảng Retirement Candidates: asset, tuổi, maintenance cost ratio, failure count, recommended action
3. Biểu đồ: Suspension by reason, Transfer by destination, Residual Risk distribution
4. Drill-down từ KPI card → danh sách DR liên quan
5. Export báo cáo PDF/Excel

```gherkin
Scenario: Dashboard hiển thị Retirement Candidates
  Given Có 3 assets được flagged là retirement candidates
  When HTM Manager mở Dashboard
  Then Dashboard hiển thị:
    - Retirement Candidates count = 3
    - Bảng listing 3 assets với tuổi, failure count, recommended action
    - Button "Tạo DR" next to mỗi candidate
```

---

### UC-13-08: Xử lý ngoại lệ

**Tình huống ngoại lệ và xử lý:**

| Tình huống | Xử lý |
|---|---|
| Asset có WO mở khi tạo DR | Block tạo, hiển thị lỗi với WO names (BR-13-01) |
| Residual risk = Critical | Warning + bắt buộc QA Officer sign off trước khi proceed |
| Bio-hazard không có clearance | Block save, yêu cầu điền bio_hazard_clearance (BR-13-03) |
| Regulatory doc thiếu | Block save, yêu cầu upload (BR-13-04) |
| Data destruction chưa confirm | Block submit (BR-13-05) |
| VP từ chối → DR cancelled | Asset.status giữ nguyên; HTM Manager được notify để xem xét lại |
| Transfer location không tồn tại | Validation error, yêu cầu chọn location hợp lệ |
| IMM-14 trigger thất bại | on_submit rollback; log error; CMMS Admin nhận cảnh báo |

---

## 4. Business Rules

| BR ID | Mô tả | Enforce tại | Chuẩn áp dụng |
|---|---|---|---|
| BR-13-01 | Không thể tạo DR nếu asset còn Work Order đang mở (PM/CM/Calibration) | `validate()` | WHO HTM §8.1 |
| BR-13-02 | Không thể tạo DR thứ 2 nếu đã có DR active cho cùng asset | `validate()` | CMMS best practice |
| BR-13-03 | `biological_hazard=True` → bắt buộc điền `bio_hazard_clearance` | `validate()` | NĐ98/2021 §15 |
| BR-13-04 | `regulatory_clearance_required=True` → bắt buộc upload `regulatory_clearance_doc` | `validate()` | NĐ98/2021 §16 |
| BR-13-05 | `data_destruction_required=True` → bắt buộc `data_destruction_confirmed=True` trước submit | `before_submit()` | ISO 27001 / TT09/2014 |
| BR-13-06 | `residual_risk_level` bắt buộc điền trước khi hoàn thành Technical Review | Service transition guard | WHO HTM Decommission Guide |
| BR-13-07 | Nếu `residual_risk_level` = High hoặc Critical → `replacement_review` bắt buộc | `validate()` khi chuyển state | WHO HTM §9.2 |
| BR-13-08 | `current_book_value` > 500.000.000 VNĐ → bắt buộc VP Block2 approve trước khi submit retire | `before_submit()` | Quy chế tài chính BV |
| BR-13-09 | `transfer_to_location` phải là Location hợp lệ trong hệ thống | `validate()` | CMMS best practice |
| BR-13-10 | `receiving_officer` bắt buộc khi outcome = Transfer | `validate()` transfer fields | NĐ98/2021 §12 |
| BR-13-11 | Từ chối (Cancelled) bắt buộc có `rejection_reason` | Service action guard | Audit trail requirement |
| BR-13-12 | Sau khi DR Completed với outcome=Retire, asset không được tạo WO mới | `validate()` trên Work Order | CMMS safety lock |

---

## 5. Thresholds & SLA Rules

### 5.1 Retirement Candidate Thresholds (auto-flag criteria)

| Chỉ tiêu | Ngưỡng cảnh báo | Ngưỡng nghiêm trọng | Nguồn dữ liệu |
|---|---|---|---|
| Tuổi thiết bị | ≥ 80% expected_life_years | ≥ 100% expected_life_years | Asset model |
| Tỷ lệ chi phí bảo trì / giá trị mua | ≥ 50% | ≥ 75% | IMM-08/09 records |
| Số lần sửa chữa trong 12 tháng | ≥ 4 lần | ≥ 6 lần (BER threshold) | IMM-09 records |
| Downtime do hỏng hóc (12 tháng) | ≥ 15% | ≥ 25% | IMM-12 records |
| Tỷ lệ utilization | ≤ 20% | ≤ 10% | Usage logs |

### 5.2 SLA Timing Rules

| Bước | SLA | Escalation sau khi quá hạn |
|---|---|---|
| Draft → Pending Tech Review | 3 ngày làm việc | Notify CMMS Admin |
| Pending Tech Review → hoàn thành | 5 ngày làm việc | Escalate HTM Manager |
| Under Replacement Review → quyết định | 7 ngày làm việc | Escalate VP Block2 |
| Approved for Transfer → Transfer In Progress | 5 ngày làm việc | Notify Network Manager |
| Transfer In Progress → Transferred | 15 ngày làm việc | Escalate VP Block2 |
| Pending Decommission → phê duyệt VP | 7 ngày làm việc | Escalate Board |
| Toàn bộ DR Draft → Completed | 45 ngày | Monthly report |

---

## 6. Non-Functional Requirements

| ID | Loại | Yêu cầu |
|---|---|---|
| NFR-13-01 | Audit Trail | Mọi transition phải sinh ALE — bất biến, không xóa được, không sửa sau insert |
| NFR-13-02 | Lưu trữ | Sau Submit, DR record giữ ≥ 10 năm; Asset Lifecycle Events vĩnh viễn |
| NFR-13-03 | Performance | API `get_suspension_request` < 300ms; `get_retirement_candidates` < 1s |
| NFR-13-04 | Quyền truy cập | Chỉ CMMS Admin mới Submit; mỗi role chỉ edit fields thuộc domain của mình |
| NFR-13-05 | Tính toàn vẹn giao dịch | on_submit phải atomic: set asset.status + ALE + optional IMM-14 trigger trong 1 transaction |
| NFR-13-06 | Thông báo | Mọi transition phải gửi notification đến actor tiếp theo trong workflow |
| NFR-13-07 | Offline resilience | Form tạo DR phải cache local nếu mất kết nối, sync khi reconnect |

---

*End of Functional Specifications v2.0.0 — IMM-13 Ngừng sử dụng và Điều chuyển*
