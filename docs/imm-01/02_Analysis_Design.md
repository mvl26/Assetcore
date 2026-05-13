# 02 — Phân tích thiết kế nghiệp vụ — IMM-01 Đánh giá Nhu cầu & Dự toán

> ⚠️ Module PLANNED — Wave 2. Chưa triển khai.

| Mục | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán (Needs Assessment & Budget Estimation) |
| Phạm vi | Per-module |
| Owner | BA + System Analyst |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |
| Chuẩn tham chiếu | WHO HTM Needs Assessment 2011/2025, ISO 13485 §7.1, NĐ 98/2021/NĐ-CP §32, Luật Đấu thầu 22/2023 |

---

# Phần I — Module Overview

## I.0. Khảo sát hiện trạng (As-Is)

Tham chiếu: WHO HTM *Needs assessment for medical devices* (chương 2 — Current practice in needs assessment) + Architecture §"Khối A. KHỐI 1" (line 244) — IMM-01 thuộc khối Hoạch định, owner **PTP Khối 1 + Nhóm KH-TC** (line 265, 268).

**Bối cảnh khảo sát:**

| Chiều khảo sát | Hiện trạng tại bệnh viện | Khoảng cách so với WHO HTM Needs Assessment |
|---|---|---|
| Kênh tiếp nhận đề xuất | Email, công văn giấy, đề nghị miệng tại giao ban | Không có biểu mẫu chuẩn, không có mã định danh, khó truy ngược |
| Lập danh mục thiết bị đề xuất | Excel rời do KH-TC tổng hợp thủ công | WHO HTM yêu cầu inventory-driven needs (gắn với asset registry) |
| Chấm điểm ưu tiên | Định tính, dựa quan điểm cá nhân | WHO HTM khuyến nghị chấm điểm đa tiêu chí (clinical impact, risk, utilization, replacement signal, compliance, budget fit) |
| Tính tổng chi phí sở hữu | Chỉ ước CAPEX, không có OPEX 5 năm | WHO HTM Annex 4 yêu cầu TCO = CAPEX + OPEX (vận hành, vật tư, nhân lực, hiệu chuẩn, decommission) |
| Đối chiếu Replacement với Decommission | Không liên thông IMM-13 | WHO HTM yêu cầu replacement signal phải xuất phát từ end-of-life evidence |
| Dự báo nhu cầu | Không có; phục vụ mua sắm năm sau lập rời từng phòng | Luật Đấu thầu 22/2023 yêu cầu kế hoạch tổng hợp, Demand Forecast là input đấu thầu tập trung |
| Audit trail quyết định đầu tư | Không có; biên bản họp giấy | NĐ 98/2021/NĐ-CP §32 + ISO 13485 §4.2.5 yêu cầu hồ sơ bất biến, retention ≥ 10 năm |

**Hệ quả pain points:** xem §II.2.

**Nguồn dữ liệu khảo sát:** phỏng vấn PTP Khối 1, KH-TC Officer, TCKT Officer; review 12 đề xuất mua sắm năm trước; đối chiếu QC-IMMIS-01 (Architecture §"Mã QC nền").

## I.1. Pitch

Bệnh viện hiện nay tiếp nhận đề xuất mua thiết bị y tế qua email hoặc văn bản không có quy trình chuẩn — không có chấm điểm ưu tiên, không tính tổng chi phí sở hữu, không đối chiếu nguồn vốn. IMM-01 chuẩn hoá toàn bộ vòng đời tiếp nhận nhu cầu: từ đề xuất lâm sàng, chấm điểm đa tiêu chí, lập dự toán CAPEX+OPEX 5 năm, đến tổng hợp Procurement Plan được BGĐ phê duyệt. Mục tiêu: mọi Needs Request đều truy xuất được, được xếp hạng minh bạch, và chỉ chuyển sang IMM-02 khi có Plan ở trạng thái Approved (docstatus=1).

## I.2. Vị trí trong WHO HTM lifecycle

| Phase | Chạm? | Ghi chú |
|---|---|---|
| **Needs Assessment** | ✅ **chính** | IMM-01 = intake gateway — toàn bộ needs flow qua đây |
| Procurement | ✅ Output | Procurement Plan (Approved) → trigger IMM-02, IMM-03 |
| Install | — | — |
| Operation | ✅ Input | IMM-07 utilization + downtime → replacement signal |
| Maintenance | — | — |
| Decommission | ✅ Input | IMM-13 Decommission Plan phải có cho replacement type |

Input: Đề xuất khoa lâm sàng, IMM-07 Performance Tracking (utilization), IMM-13 Decommission Plan, IMM-10 Compliance Gap.
Output: Procurement Plan (Approved) → IMM-02 (Tech Spec), IMM-03 (Vendor/PO); Demand Forecast → IMM-15, IMM-17.

## I.3. Stakeholders & Actors

| Vai trò | Frappe Role | Quan tâm chính | Tần suất | Loại |
|---|---|---|---|---|
| Department User (KTV/ĐD trưởng khoa) | `IMM Clinical User` | Tạo Draft Needs Request, đính kèm clinical justification | Per request | Primary |
| Clinical Head (Trưởng khoa) | `IMM Clinical User` (head subset) | Submit Draft → Submitted | Per request | Primary |
| HTM Reviewer | `IMM HTM Engineer` (Wave 2 mới) | Review/Score clinical_impact + risk | Daily | Primary |
| KH-TC Officer | `IMM Planning Officer` (Wave 2 mới) | Chấm điểm, tạo Procurement Plan | Weekly | Primary |
| TCKT Officer | `IMM Finance Officer` (Wave 2 mới) | Build Budget Estimate, xác nhận funding_source | Per request | Secondary |
| PTP Khối 1 | `IMM Department Head` (Wave 1) | Workflow steward, trình BGĐ | Weekly | Approver |
| VP Block1 / BGĐ | `IMM Board Approver` (Wave 2 mới) | Approve / Reject (terminal) | Per request | Approver |
| CMMS Admin | `IMM System Admin` (Wave 1) | Cấu hình master, override | Ad-hoc | Secondary |
| CMMS Auto (Scheduler) | System | Overdue check, demand forecast, envelope alert | Auto | System |

## I.4. Scope

**In-scope:**
- 3 Primary DocTypes: `IMM Needs Request`, `IMM Procurement Plan`, `IMM Demand Forecast`
- 5 Child tables: `Needs Priority Scoring`, `Budget Estimate Line`, `Procurement Plan Line`, `Forecast Driver` + reuse `IMM Audit Trail`
- Workflow 8 states, 10 transitions
- 6 Validation Rules (VR-01-01 → VR-01-06), 5 Gates (G01 → G05)
- 14+ REST API endpoints
- Frontend list + detail + create cho 3 primary DocType
- 3 Scheduler jobs (daily overdue, monthly forecast, weekly envelope alert)
- Dashboard KPI 6 chỉ số

**Out-of-scope:**
- Soạn thông số kỹ thuật chi tiết → IMM-02
- Đánh giá nhà cung cấp, đấu thầu, ký HĐ → IMM-03
- Lắp đặt nghiệm thu → IMM-04
- Tích hợp BHYT real-time (chỉ ghi nhận tay)
- HTA chuyên sâu (tham chiếu, không build lại)
- Tích hợp ERP TCKT real-time — V2

**Assumptions:**
- IMM-07 Performance Tracking đã có dữ liệu utilization trước khi IMM-01 live
- IMM-13 Decommission Plan đã tồn tại cho các asset cần replacement
- Scoring weights được seed fixture trước khi go-live

**Dependencies:**
- IMM-07: `get_asset_kpi_12m(asset)` — fetch utilization/downtime cho replacement signal
- IMM-13: `get_active_decom_plan(asset)` — validate VR-01-02
- IMM-10: Hook compliance gap → `compliance_driven=1`
- IMM-02: `draft_from_plan(plan)` — output action sau Approved

## I.5. KPI mục tiêu

| KPI | Định nghĩa | Target | Đo ở đâu |
|---|---|---|---|
| Lead time intake → Approved | avg(approved_date − request_date) | < 45 ngày | `dashboard_kpis` |
| % Needs Request đúng thủ tục G01 | pass_g01 / total_submitted | ≥ 95% | `dashboard_kpis` |
| Budget envelope utilization | Σ approved_capex / quarterly_envelope | 70–95% | `dashboard_kpis` |
| Replacement-signal coverage | replacement_requests / decommissioned_assets | ≥ 80% | `dashboard_kpis` |
| Demand Forecast accuracy | 1 − abs(forecast − actual) / actual | ≥ 85% | Demand Forecast doc |
| Backlog > 30 ngày | count Submitted/Reviewing > 30d | giảm dần | `dashboard_kpis` |

## I.6. Ràng buộc Compliance

| Quy định | Yêu cầu áp lên module | Doc tham chiếu |
|---|---|---|
| NĐ 98/2021/NĐ-CP §32 | Kế hoạch đầu tư trang thiết bị y tế phải lập và duyệt | Procurement Plan workflow |
| WHO HTM Needs Assessment §3.2 | Clinical justification bắt buộc | BR-01-01: clinical_justification ≥ 200 ký tự |
| WHO HTM §2.4 | Utilization data 12 tháng bắt buộc cho Replacement | G01 gate |
| WHO HTM Annex 4 | Total Cost of Ownership = CAPEX + OPEX | Budget Estimate CAPEX + OPEX 5y |
| ISO 13485 §7.1 | Planning of product realization | Workflow + Gates |
| ISO 13485 §4.2.5 | Audit trail bất biến | IMM Audit Trail immutable |
| Luật Đấu thầu 22/2023 | Kế hoạch dự báo nhu cầu phục vụ đấu thầu tập trung | Demand Forecast |

## I.7. Rủi ro & Biện pháp giảm thiểu

| ID | Rủi ro | Mức (L/M/H) | Tác động | Biện pháp |
|---|---|---|---|---|
| RSK-01-01 | Đề xuất ảo / trùng lặp giữa các khoa cho cùng asset cần thay thế | M | Double-allocation budget, lãng phí | VR-01-01 (1 Asset = 1 NR Active); G01 yêu cầu utilization data 12 tháng từ IMM-07 |
| RSK-01-02 | Replacement không có Decommission Plan IMM-13 → mua mới mà không thanh lý | H | Vi phạm NĐ98 §32, audit fail | VR-01-02 hard-block; tham chiếu IMM-13 mandatory cho request_type=Replacement |
| RSK-01-03 | Chấm điểm cảm tính, thiên vị giữa khoa | M | Ưu tiên sai, mất minh bạch | G02 đủ 6/6 tiêu chí weighted; HTM Reviewer + KH-TC Officer 4-eyes |
| RSK-01-04 | Vượt budget envelope quý do nhiều phiếu được duyệt độc lập | H | Vỡ kế hoạch tài chính | G04 hard-cap khi `enforce_envelope=1`; soft warning > 80% |
| RSK-01-05 | Phiếu submitted rồi để treo > 30 ngày | M | Lead time KPI fail | Scheduler `check_pending_request_overdue` daily 02:00; email PTP Khối 1 + KH-TC |
| RSK-01-06 | Demand Forecast lệch thực tế > 15% → đấu thầu tập trung sai dự báo | M | Vi phạm Luật Đấu thầu 22/2023 | KPI Forecast accuracy ≥ 85%; review tháng giữa KH-TC Officer + Workshop |
| RSK-01-07 | Hồ sơ đính kèm clinical justification mất hoặc bị sửa | H | Vi phạm ISO 13485 §4.2.5 | IMM Audit Trail bất biến (NFR-01-06); backup daily 30-day (NFR-01-08) |
| RSK-01-08 | Role mới (HTM Reviewer, KH-TC Officer, Finance Officer, Board Approver) chưa được đào tạo trước go-live | M | Workflow tắc nghẽn | IMM-06 Training prerequisite; UAT đầy đủ 8 actor scenarios |

## I.8. Roadmap & Đợt triển khai

Theo Architecture §"Đợt triển khai" (line 276–278), IMM-01 thuộc **Đợt 2** với phạm vi: *"Nhu cầu và dự toán; hồ sơ kỹ thuật; vendor management; training; spare parts; compliance scorecard"*. Điều kiện chuyển giai đoạn từ Đợt 1: *"Đã có QMS, dashboard nguồn tin cậy và change control"*.

| Giai đoạn | Phạm vi IMM-01 | Phụ thuộc | Trạng thái |
|---|---|---|---|
| **Đợt 1 (Pre-req)** | IMM-04, 05, 08, 09, 11, 12 hoàn tất → Asset registry, hồ sơ pháp lý, PM/CM, calibration ổn định | Asset registry + IMM Audit Trail shared | ✅ Live (Wave 1) |
| **Đợt 2 — IMM-01 v1 (current)** | 3 Primary DocTypes, 8 workflow states, 14+ endpoints, FE list/detail/create, 3 scheduler jobs, dashboard 6 KPI | IMM-04/05/08/09/11/12 (Đợt 1); IMM-06 training; QMS + change control | ✅ Live (Wave 2) |
| **Đợt 2 — Tích hợp** | Output `draft_from_plan(plan)` → IMM-02 Tech Spec; Demand Forecast → IMM-15 Spare Parts | IMM-02, IMM-03, IMM-15, IMM-16 (cùng Đợt 2) | ✅ Live cùng Wave 2 |
| **Đợt 3 — Mở rộng** | Hook IMM-07 Performance Tracking (utilization 12m real-time); IMM-10 Compliance Gap → `compliance_driven=1`; IMM-13 Decommission Plan link replacement; IMM-17 predictive forecast | IMM-07, IMM-10, IMM-13, IMM-14, IMM-17 (Đợt 3) | 🟡 Planned — chờ Đợt 3 BE scaffold |
| **V2 (post-Đợt 3)** | Tích hợp ERP TCKT real-time; HTA chuyên sâu; BHYT real-time | Roadmap dài hạn | ⏳ Backlog |

**Điều kiện chuyển sang Đợt 3:** đã có data lineage, đủ chất lượng dữ liệu utilization từ IMM-07 và Decommission Plan từ IMM-13, cơ chế management review qua IMM-16.

---

# Phần II — Quy trình nghiệp vụ (BPMN)

## II.1. As-Is process

Khoa lâm sàng gửi đề xuất thiết bị qua email/văn bản → PTP Khối 1 gom vào danh sách không chuẩn hóa → TCKT lập dự toán riêng lẻ → BGĐ xem xét không có điểm ưu tiên định lượng. Không có SLA, không trace được lý do phê duyệt hay bác, không dự báo được nhu cầu.

## II.2. Pain points

| # | Pain | Tác động |
|---|---|---|
| 1 | Không có chấm điểm ưu tiên → thiết bị quan trọng có thể bị bỏ qua | Nguy cơ lâm sàng, vi phạm WHO HTM |
| 2 | Dự toán thiếu OPEX → vượt ngân sách năm thứ 2-3 | Chi phí vận hành không kiểm soát |
| 3 | Replacement không gắn Decommission Plan → double-allocation | Lãng phí, audit không pass |
| 4 | Không có demand forecast → đấu thầu tập trung không có cơ sở | Vi phạm Luật Đấu thầu 22/2023 |
| 5 | Không có audit trail → không chứng minh được quyết định đầu tư khi kiểm tra | Rủi ro pháp lý, vi phạm ISO 13485 |

## II.3. To-Be process (BPMN text)

```
Swimlane: Department User / Clinical Head
  [Tạo Draft NR] → (VR-03 clinical_justification ≥ 200) → [Submit Draft]
  → G01 gate (utilization data nếu Replacement) → [Submitted]

Swimlane: HTM Reviewer / KH-TC Officer
  [Reviewing NR] → [Chấm điểm 6 tiêu chí]
  → G02 gate (6/6 scoring rows + weighted_score) → [Prioritized]
  ← (hoặc Yêu cầu bổ sung → Draft)

Swimlane: TCKT Officer
  [Lập Budget Estimate] → G03 gate (CAPEX + OPEX 5y) → G04 gate (envelope check)
  → [Budgeted]

Swimlane: PTP Khối 1
  [Trình BGĐ] → [Pending Approval]

Swimlane: VP Block1 / BGĐ
  → G05 gate (board_approver + funding_source) → [Approved] (docstatus=1)
  ← hoặc [Rejected] / [Yêu cầu chỉnh dự toán]

Swimlane: KH-TC Officer (sau Approved)
  [Roll into Procurement Plan] → [Generate IMM-02 Tech Spec Drafts]

Swimlane: Scheduler (monthly)
  [Generate Demand Forecast] → [DF-YYYY published] → IMM-15, IMM-17
```

## II.4. Decision points

| Điểm | Câu hỏi | Quy tắc |
|---|---|---|
| Tạo NR | request_type = Replacement? | Có → phải có replacement_for_asset + Decommission Plan (VR-01-02) |
| Submit | G01 pass? | clinical_justification + utilization_pct (nếu Replacement/Upgrade) |
| Prioritize | G02 pass? | 6/6 scoring rows + weighted_score computed |
| Budget | G03 pass? | total_capex > 0 + 5 OPEX years present |
| Budget | G04 pass? | tổng allocated ≤ budget envelope (soft warning / hard block) |
| Approve | G05 pass? | board_approver + funding_source set |
| Reject | Rejection reason set? | Bắt buộc nhập rejection_reason khi Reject |

## II.5. Exception flows

**E1 — Vượt budget envelope (G04 soft):**
TCKT nhận warning khi tổng dự toán > 80% envelope quý. Ghi nhận cảnh báo, có thể tiếp tục. Khi vượt 100% + `enforce_envelope=1` → hard block, yêu cầu điều chỉnh.

**E2 — Replacement thiếu Decommission Plan (VR-01-02):**
VR-01-02 block save khi request_type=Replacement mà replacement_for_asset không có IMM-13 plan ở trạng thái Pending/Approved. Department User phải tạo Decommission Plan IMM-13 trước.

**E3 — Backlog quá 30 ngày:**
Scheduler `check_pending_request_overdue` (daily 02:00) phát hiện phiếu ở Submitted/Reviewing quá 30 ngày → email PTP Khối 1 và KH-TC Officer để nhắc xử lý.

## II.6. RACI matrix

| Hoạt động | Department User | Clinical Head | HTM Reviewer | KH-TC | TCKT | PTP Khối 1 | VP Block1 | Scheduler |
|---|---|---|---|---|---|---|---|---|
| Tạo Draft NR | R/A | C | — | — | — | I | — | — |
| Submit NR | C | R/A | — | — | — | I | — | — |
| Review + Score | — | — | R/A | C | — | I | — | — |
| Chuyển Prioritized | — | — | C | R/A | — | I | — | — |
| Lập Budget Estimate | — | — | — | C | R/A | I | — | — |
| Trình BGĐ | — | — | — | C | C | R/A | I | — |
| Approve / Reject | — | — | — | I | I | C | R/A | — |
| Roll into Plan | — | — | — | R/A | C | I | — | — |
| Overdue check | — | — | — | I | — | I | — | R/A |
| Demand Forecast | — | — | — | I | — | I | — | R/A |

---

# Phần III — Use Case Specification

## III.1. Use Case Diagram (tổng quát)

```
Actor: Clinical Head → UC-01 Tạo Needs Request
Actor: HTM Reviewer → UC-02 Review & Score NR
Actor: KH-TC Officer → UC-03 Tạo Procurement Plan, UC-05 Xem Demand Forecast
Actor: TCKT Officer → UC-04 Lập Budget Estimate
Actor: VP Block1 → UC-06 Approve / Reject
Actor: Scheduler (system) → UC-07 Overdue Check, UC-08 Generate Demand Forecast
UC-01 <<include>> Submit NR
UC-06 <<extend>> Yêu cầu chỉnh dự toán [score thấp]
```

## III.2. Actor catalog

| Actor | Loại | Mô tả | Goal chính |
|---|---|---|---|
| Clinical Head | Primary | Trưởng khoa lâm sàng | Có thiết bị đáp ứng nhu cầu khám chữa bệnh |
| HTM Reviewer | Primary | Nhóm HTM kỹ thuật | Đánh giá đúng mức độ ưu tiên đầu tư |
| KH-TC Officer | Primary | Kế hoạch - Tài chính | Kế hoạch mua sắm khả thi trong budget |
| TCKT Officer | Secondary | Tài chính kế toán | Dự toán đúng TCO |
| VP Block1 | Approver | BGĐ / Phó Trưởng phòng Block 1 | Đầu tư đúng ưu tiên chiến lược |
| Scheduler | System | Frappe scheduler | Cảnh báo kịp thời, dự báo tự động |

## III.3. Use Case Specifications (key UCs)

### UC-01: Tạo Needs Request

| Mục | Giá trị |
|---|---|
| ID | UC-IMM01-01 |
| Brief | Clinical Head tạo phiếu đề xuất thiết bị, gửi đến HTM Reviewer |
| Primary actor | Clinical Head |
| Pre-condition | Đăng nhập với role IMM Clinical User; IMM Device Model tồn tại |
| Post-condition | NR ở Submitted; ALE "submitted" ghi; email gửi PTP Khối 1 + KH-TC |
| Trigger | Khoa có nhu cầu mua mới / thay thế / nâng cấp thiết bị |

**Main flow:**

| Bước | Actor | System |
|---|---|---|
| 1 | Clinical Head mở form Needs Request mới | Form hiển thị với requesting_department auto-fill |
| 2 | Chọn request_type, device_model_ref, quantity, target_year | device_category auto-fetch từ model |
| 3 | Nhập clinical_justification ≥ 200 ký tự | — |
| 4 | Nếu Replacement: chọn replacement_for_asset | Auto-fetch utilization_pct_12m từ IMM-07 |
| 5 | Nhấn "Gửi đề xuất" | G01 validate (utilization nếu Replacement); VR-01-02 kiểm tra Decom Plan |
| 6 | — | Workflow state Draft → Submitted; ALE "Submitted" ghi; email gửi |

### UC-06: Approve Needs Request

| Mục | Giá trị |
|---|---|
| ID | UC-IMM01-06 |
| Brief | VP Block1 phê duyệt phiếu ở Pending Approval |
| Primary actor | VP Block1 |
| Pre-condition | NR ở Pending Approval; G05: board_approver + funding_source đã set |
| Post-condition | docstatus=1, state Approved; NR gom vào Procurement Plan nếu config auto-roll |

---

# Phần IV — Functional Specifications

## IV.1. User Stories & Acceptance Criteria

### US-01-001 — Tạo Needs Request hợp lệ (New)

Là **Clinical Head**, tôi muốn **tạo phiếu đề xuất thiết bị mới** để **khoa có thiết bị đáp ứng nhu cầu khám chữa bệnh**.

Priority: Must | Estimate: 5SP

**AC-1 — Tạo NR hợp lệ:**
```gherkin
Given tôi là Clinical Head của khoa "ICU"
When tôi mở form Needs Request và chọn request_type="New", device_model_ref, clinical_justification (≥ 200 ký tự)
And tôi nhập requesting_department="ICU", quantity=2, target_year=2027
And tôi nhấn "Gửi đề xuất"
Then phiếu chuyển từ Draft → Submitted
And lifecycle_event "Submitted" được ghi với actor=tôi
And email thông báo gửi PTP Khối 1 + KH-TC Officer
```

**AC-2 — Thiếu clinical_justification:**
```gherkin
Given tôi nhập clinical_justification chỉ 50 ký tự
When tôi nhấn Lưu
Then hệ thống throw "VR-01-03: clinical_justification phải ≥ 200 ký tự"
```

### US-01-002 — Replacement phải link Decommission Plan

Là **KTV khoa**, khi **báo hỏng nặng thiết bị X**, tôi muốn **tạo Needs Request thay thế và link sang Decommission Plan** để đảm bảo traceability.

**AC-1 — Có Decommission Plan:**
```gherkin
Given Asset "ABG-001" có IMM-13 Decommission Plan trạng thái "Pending"
When tôi tạo Needs Request type="Replacement" với replacement_for_asset="ABG-001"
Then VR-02 pass và phiếu lưu thành công
```

**AC-2 — Thiếu Decommission Plan:**
```gherkin
Given Asset không có Decommission Plan
When tôi cố gắng Submit
Then VR-02 throw "VR-01-02: Replacement request yêu cầu Decommission Plan IMM-13 ở trạng thái Pending/Approved"
```

### US-01-010 — Chấm điểm 6 tiêu chí

Là **HTM Reviewer**, tôi muốn **chấm điểm 6 tiêu chí cho phiếu** để **xếp loại P1–P4 minh bạch**.

```gherkin
Given phiếu ở Reviewing
When tôi điền 6 scoring rows (clinical_impact=5, risk=5, utilization_gap=4, replacement_signal=5, compliance_gap=3, budget_fit=3)
Then weighted_score = 4.30 được auto-compute
And priority_class = "P1" hiển thị
And không thể chuyển Prioritized nếu thiếu 1/6 tiêu chí (G02)
```

### US-01-020 — Lập dự toán CAPEX + OPEX 5 năm

Là **TCKT Officer**, tôi muốn **lập dự toán CAPEX + OPEX 5 năm** để **có view tổng chi phí sở hữu**.

```gherkin
Given phiếu ở Prioritized
When tôi nhập budget_lines: 5 dòng CAPEX + 5×6 dòng OPEX
Then total_capex và total_opex_5y tự tính
And nếu thiếu OPEX year nào → G03 fail "Budget Estimate phải có cả CAPEX + OPEX 5 năm"
```

### US-01-030 — Phê duyệt với funding_source

Là **VP Block1**, tôi muốn **duyệt/bác phiếu kèm lý do và funding_source**.

```gherkin
Given phiếu ở Pending Approval
When tôi nhập board_approver="self", funding_source="NSNN" và nhấn "Approved"
Then phiếu chuyển Approved (docstatus=1)
And lifecycle_event "Approved" ghi với approver, funding_source, approval_date
```

### US-01-040 — Xem Procurement Plan tổng hợp

Là **KH-TC Officer**, tôi muốn **xem Procurement Plan tổng hợp các Needs Request đã duyệt** để **lập kế hoạch mua sắm minh bạch**.

```gherkin
When tôi mở Procurement Plan PP-26-001
Then thấy danh sách plan_items với priority_rank giảm dần weighted_score
And tổng allocated_budget không vượt envelope đã set
And có thể "Generate IMM-02 Spec Drafts" tạo loạt phiếu Tech Spec rỗng
```

## IV.2. Business Rules

| ID | Rule | Implement ở | Test |
|---|---|---|---|
| BR-01-01 | Mỗi NR phải có requesting_department + clinical_justification ≥ 200 ký tự | `_vr03_clinical_justification()` before_insert | TC-02 |
| BR-01-02 (G01) | Utilization data 12 tháng bắt buộc nếu request_type=Replacement/Upgrade | `validate_gate_g01()` | TC-09 |
| BR-01-03 (VR-01) | 1 Asset chỉ có 1 Needs Request Active thay thế tại 1 thời điểm | `_vr01_unique_active_request_per_asset()` | TC-— |
| BR-01-04 (G02) | Priority scoring đủ 6/6 tiêu chí + weighted_score tính đúng | `compute_priority_score()` + `validate_gate_g02()` | TC-12 |
| BR-01-05 (G03) | Budget Estimate phải có CAPEX + OPEX 5 năm; thiếu OPEX bị block | `validate_gate_g03()` | TC-16 |
| BR-01-06 (G04) | Tổng dự toán không vượt budget envelope quý (soft warning / hard cap) | `validate_gate_g04()` | TC-17/18 |
| BR-01-07 (G05) | board_approver + funding_source bắt buộc trước Approved | `validate_gate_g05()` | TC-19 |
| BR-01-08 | Replacement request phải link Decommission Plan IMM-13 (Pending/Approved) | `_vr02_replacement_requires_decom_plan()` | TC-03/04 |

## IV.3. State Machine

| State | doc_status | Type | Mô tả | Gate |
|---|---|---|---|---|
| Draft | 0 | Success | NR mới tạo hoặc trả về | — |
| Submitted | 0 | Warning | Đã gửi, chờ HTM Review | G01 |
| Reviewing | 0 | Warning | HTM đang rà soát | — |
| Prioritized | 0 | Success | Đã chấm điểm xong | G02 |
| Budgeted | 0 | Success | Dự toán xong | G03 + G04 |
| Pending Approval | 0 | Warning | Chờ BGĐ phê duyệt | — |
| Approved | 1 | Success | Được duyệt (terminal positive) | G05 |
| Rejected | 1 | Danger | Bị bác (terminal negative) | — |

---

# Phần V — Yêu cầu phi chức năng

## V.1. Bảng NFR

| NFR-ID | Nhóm | Yêu cầu | Target | Đo ở đâu |
|---|---|---|---|---|
| NFR-01-01 | Performance | Load list 1000 Needs Request | < 2s | `list_needs_requests` P95 |
| NFR-01-02 | Performance | Submit phiếu + validate toàn bộ | < 1.5s | `submit_needs_request` P95 |
| NFR-01-03 | Retention | Audit trail retention | ≥ 10 năm (NĐ98) | IMM Audit Trail policy |
| NFR-01-04 | i18n | Label/error message tiếng Việt | 100% | UI + API error messages |
| NFR-01-05 | Security | Permission bám role thực, không dùng System Manager cho nghiệp vụ | RULE-F05 | Role check mọi endpoint |
| NFR-01-06 | Integrity | Audit trail bất biến — cấm sửa lifecycle_events row đã có | VR-01-06 | IMM Audit Trail DocPerm |
| NFR-01-07 | Security | API authentication Frappe session + API key | Must | Auth header check |
| NFR-01-08 | Availability | Backup hồ sơ đính kèm | Daily, 30-day retention | Frappe backup config |
| NFR-01-09 | Scalability | 10k Needs Request với index query | < 2s | DB index `idx_nr_state_dept` |
| NFR-01-10 | Usability | Desktop-first; form chạy trên Chrome/Edge mới nhất | ≥ 1024px width | Manual test |
