# IMM-17 — Phân tích dự đoán (Predictive Analytics)
## Module Overview

**Phiên bản:** 1.0.0
**Ngày tạo:** 2026-04-24
**Đợt triển khai:** Đợt 3
**QMS gốc:** QC-IMMIS-03 → PR-IMMIS-17-01 đến 17-04
**Trạng thái:** Draft — chờ review BA/Kiến trúc

---

## 1. Mục đích và Phạm vi

IMM-17 là **lớp intelligence xuyên suốt** toàn bộ hệ thống IMMIS. Module này không thực hiện nghiệp vụ vận hành trực tiếp mà **thu thập, tổng hợp và phân tích dữ liệu** từ tất cả các modules vận hành (IMM-04 đến IMM-15) để:

1. **Dự đoán rủi ro** — phát hiện thiết bị có nguy cơ hỏng trước khi sự cố xảy ra
2. **Tối ưu lịch bảo trì** — đề xuất điều chỉnh chu kỳ PM dựa trên thực tế vận hành
3. **Dự báo nhu cầu** — phụ tùng thay thế và ngân sách bảo trì
4. **Hỗ trợ quyết định thanh lý** — chấm điểm thiết bị cần xem xét thanh lý/thay thế
5. **Phân tích kịch bản** — what-if analysis để đánh giá tác động của thay đổi chính sách

> **Nguyên tắc cốt lõi:** IMM-17 **chỉ đưa ra khuyến nghị** (recommendation), KHÔNG tự động tạo Work Order hay thực hiện hành động. Mọi quyết định vận hành phải có sự phê duyệt của con người.

### Phạm vi

| Trong phạm vi | Ngoài phạm vi |
|---|---|
| Predictive analytics từ dữ liệu lịch sử IMMIS | Machine learning / deep learning phức tạp |
| Rule-based + statistical calculations | Real-time IoT sensor integration |
| Dashboard và báo cáo dự đoán | Automatic work order creation |
| What-if scenario simulation | Clinical decision support (CDSS) |
| Alert và escalation cho rủi ro cao | Integration với HIS/EMR (Phase 2) |

---

## 2. Sơ đồ Luồng Dữ liệu (Data Flow Architecture)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DATA SOURCES — Operational Modules                        ║
╠══════════════════╦══════════════════╦══════════════════╦════════════════════╣
║  IMM-04           ║  IMM-08          ║  IMM-09          ║  IMM-11            ║
║  Installation     ║  Preventive      ║  Corrective      ║  Calibration       ║
║  Records          ║  Maintenance     ║  Maintenance     ║  Records           ║
║  · install date   ║  · PM records    ║  · repair records║  · CAL records     ║
║  · commissioning  ║  · PM compliance ║  · failure codes ║  · drift trends    ║
║  · asset config   ║  · labor hours   ║  · downtime      ║  · pass/fail rate  ║
╚══════════════════╩══════════════════╩══════════════════╩════════════════════╝
╔══════════════════╦══════════════════╦══════════════════╦════════════════════╗
║  IMM-12           ║  IMM-13          ║  IMM-15          ║  IMM-05            ║
║  Incident /       ║  Decommission    ║  Spare Parts     ║  Registration      ║
║  CAPA             ║  · EOL records   ║  · consumption   ║  · warranty data   ║
║  · incident count ║  · cost at EOL   ║  · lead times    ║  · contract SLA    ║
║  · severity       ║  · reason codes  ║  · stock levels  ║  · regulatory info ║
╚══════════════════╩══════════════════╩══════════════════╩════════════════════╝
                                    │
                                    ▼ (read-only, scheduled aggregation)
╔══════════════════════════════════════════════════════════════════════════════╗
║                      IMM-17 ANALYTICS ENGINE                                 ║
║                                                                              ║
║  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  ║
║  │ Data Quality    │  │ Aggregation     │  │ Model Registry              │  ║
║  │ Checker         │  │ Layer           │  │ · version tracking          │  ║
║  │ · completeness  │  │ · MTBF calc     │  │ · accuracy metrics          │  ║
║  │ · min 6 months  │  │ · cost rollup   │  │ · confidence thresholds     │  ║
║  │ · flag low conf │  │ · downtime agg  │  │ · refresh schedule          │  ║
║  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  ║
║           └────────────────────┴───────────────────────────┘                 ║
║                                    │                                          ║
║  ┌─────────────────────────────────▼─────────────────────────────────────┐  ║
║  │                    PREDICTION MODELS (5 modules)                       │  ║
║  │                                                                         │  ║
║  │  [M1] Failure Risk   [M2] PM Optimization  [M3] Spare Demand          │  ║
║  │       Scoring               Engine               Forecast              │  ║
║  │                                                                         │  ║
║  │  [M4] Budget         [M5] Replacement                                  │  ║
║  │       Forecast             Candidate Scoring                           │  ║
║  └─────────────────────────────────┬─────────────────────────────────────┘  ║
║                                    │                                          ║
║  ┌─────────────────────────────────▼─────────────────────────────────────┐  ║
║  │                    What-If Scenario Engine                              │  ║
║  │  "Nếu giảm chu kỳ PM 20% → impact lên downtime & cost là gì?"         │  ║
║  └─────────────────────────────────┬─────────────────────────────────────┘  ║
╚════════════════════════════════════╪═════════════════════════════════════════╝
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
          ┌─────────────────┐ ┌────────────┐ ┌──────────────────┐
          │ Alert Engine    │ │ Dashboards │ │ Recommendations  │
          │ · risk alerts   │ │ · cockpit  │ │ · PM schedule    │
          │ · escalation    │ │ · heatmap  │ │ · spare reorder  │
          │ · notifications │ │ · KPI dash │ │ · budget plan    │
          │ · audit log     │ │ · reports  │ │ → requires human │
          └─────────────────┘ └────────────┘ │   approval       │
                                              └──────────────────┘
```

---

## 3. Năm Predictive Models

### M1 — Failure Risk Scoring

| Thuộc tính | Chi tiết |
|---|---|
| **Mục tiêu** | Xác định thiết bị có nguy cơ hỏng hóc cao trong 30/60/90 ngày tới |
| **Inputs** | MTBF history (IMM-09), downtime frequency (IMM-12), repair cost trend (IMM-09), age (IMM-04), PM compliance rate (IMM-08) |
| **Algorithm** | Weighted risk score (0–100): age_factor × 0.2 + downtime_rate × 0.3 + repair_cost_ratio × 0.25 + pm_compliance_inv × 0.15 + mtbf_decline × 0.10 |
| **Output** | Risk score, risk tier (Low/Medium/High/Critical), confidence level, top 3 contributing factors |
| **Ngưỡng hành động** | Score > 70 → High Alert; Score > 85 → Critical Alert → notify HTM Manager |
| **Min data yêu cầu** | 6 tháng lịch sử, ≥ 2 sự kiện PM hoặc CM |

### M2 — PM Schedule Optimization

| Thuộc tính | Chi tiết |
|---|---|
| **Mục tiêu** | Đề xuất tăng/giảm chu kỳ PM so với lịch mặc định |
| **Inputs** | Failure patterns between PM events (IMM-08/09), utilization rate, PM compliance history (IMM-08), seasonal failure trends |
| **Algorithm** | Compare actual failure interval vs. current PM interval → if failures cluster near PM date: shorten; if PM often finds nothing: lengthen |
| **Output** | Recommended interval (days), delta vs. current (%), confidence, rationale narrative |
| **Giới hạn** | Không tự động cập nhật Maintenance Plan — chỉ recommendation |
| **Min data yêu cầu** | 12 tháng, ≥ 4 PM cycles completed |

### M3 — Spare Parts Demand Forecast

| Thuộc tính | Chi tiết |
|---|---|
| **Mục tiêu** | Dự báo nhu cầu phụ tùng 3 tháng tới cho từng part number |
| **Inputs** | Consumption history (IMM-09/15) 12 tháng, seasonality patterns, fleet size per device model |
| **Algorithm** | Simple moving average (3-month window) với seasonal adjustment factor; flag anomalous consumption |
| **Output** | Forecasted monthly demand, recommended reorder point, recommended order quantity, lead time buffer |
| **Min data yêu cầu** | 6 tháng lịch sử tiêu thụ, ≥ 5 transactions per part |

### M4 — Maintenance Budget Forecast

| Thuộc tính | Chi tiết |
|---|---|
| **Mục tiêu** | Dự báo chi phí bảo trì 12 tháng rolling |
| **Inputs** | Historical PM/CM/CAL costs 24 tháng, asset age distribution, fleet composition changes (IMM-13 retirements, new installations IMM-04) |
| **Algorithm** | Cost trend per device model × fleet composition + seasonality factor + inflation adjustment |
| **Output** | Monthly forecast (12 months), annual total, confidence interval (±%), breakdown by cost category |
| **Min data yêu cầu** | 12 tháng lịch sử chi phí, ≥ 10 assets trong fleet |

### M5 — Replacement Candidate Scoring

| Thuộc tính | Chi tiết |
|---|---|
| **Mục tiêu** | Chấm điểm thiết bị cần xem xét thanh lý/thay thế, trigger IMM-13 review |
| **Inputs** | Age (IMM-04), total cost of ownership (IMM-08/09/11), downtime % (IMM-09/12), failure frequency, repair/replacement cost ratio |
| **Algorithm** | Multi-criteria scoring (0–100): age_score × 0.25 + tco_score × 0.30 + availability_score × 0.25 + failure_freq_score × 0.20 |
| **Output** | Replacement score, recommended action (Monitor/Plan/Urgent Review), projected next 12-month maintenance cost |
| **Ngưỡng hành động** | Score > 75 → recommend IMM-13 Decommission Review initiation |
| **Min data yêu cầu** | 24 tháng vận hành hoặc ≥ 5 CM events |

---

## 4. Actors và Vai trò

| Actor | Vai trò trong IMM-17 |
|---|---|
| **Nhóm HTM (Biomedical Engineers)** | Xem dashboard rủi ro, review PM recommendations, xác nhận/từ chối đề xuất điều chỉnh PM |
| **Workshop (Technicians)** | Xem spare parts forecast, xác nhận consumption data, review alerts cấp thiết bị |
| **Nhóm Kho (Warehouse)** | Xem spare demand forecast, lập kế hoạch mua sắm phụ tùng dựa trên dự báo |
| **KH-TC (Finance/Planning)** | Xem budget forecast 12 tháng, xuất báo cáo cho BGĐ, phân tích what-if ngân sách |
| **Tổ HC-QLCL & Risk** | Review model accuracy, audit trail compliance, configure alert thresholds, QMS oversight |
| **Trung tâm Đổi mới sáng tạo** | Model governance, review prediction accuracy, update thresholds, system health monitoring |

---

## 5. Integration Architecture

### Read Sources (Read-Only)

IMM-17 chỉ ĐỌC dữ liệu, không ghi vào các module nguồn:

```
IMM-04 Installation Records → Asset age, commissioning date, initial value
IMM-05 Registration         → Warranty expiry, vendor contract, regulatory class
IMM-08 PM Records           → PM compliance rate, PM cost, labor hours per PM
IMM-09 CM/Repair Records    → Failure events, repair cost, downtime duration, failure codes
IMM-11 Calibration Records  → CAL pass/fail rate, drift measurements
IMM-12 Incidents            → Incident count by severity, CAPA trigger events
IMM-13 Decommission         → EOL cost data, historical replacement decisions
IMM-15 Spare Parts          → Consumption records, current stock levels, lead times
```

### Write Targets (IMM-17 Internal Only)

```
IMM Prediction Run      → Log của mỗi lần chạy model
IMM Prediction Result   → Kết quả prediction theo asset
IMM Predictive Alert    → Alerts đã generated
IMM What If Scenario    → Kết quả what-if analysis
```

### Write to Other Modules (Notifications Only)

```
→ Frappe Notification  → Alert notifications cho users
→ Frappe ToDo          → Recommended actions (read-only task reference)
(KHÔNG tạo Work Order, KHÔNG tạo Maintenance Plan automatically)
```

---

## 6. KPI Dashboard — KPI-DASH-IMMIS-17

### KPI Chính

| KPI | Định nghĩa | Đơn vị | Target |
|---|---|---|---|
| **Prediction Accuracy Rate** | % predictions (risk score > 70) được xác nhận bởi actual failure trong 90 ngày | % | ≥ 70% |
| **Preventable Failures** | Số failures xảy ra trên assets đã được flagged High/Critical và không được xử lý | Count | Trending down |
| **Cost Avoidance** | Estimated cost saved từ preventive actions triggered bởi IMM-17 alerts | VNĐ/tháng | Track & improve |
| **PM Optimization Coverage** | % assets có đề xuất PM optimization được reviewed | % | ≥ 80% |
| **Alert Response Rate** | % Critical alerts được acknowledged trong SLA (4 giờ) | % | ≥ 95% |
| **Model Confidence Score** | Average confidence level của all active predictions | % | ≥ 75% |
| **Data Sufficiency Rate** | % fleet assets đủ data để chạy prediction models | % | ≥ 85% |

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  KPI-DASH-IMMIS-17 — Predictive Analytics Overview                  │
├────────────┬────────────┬────────────┬────────────┬─────────────────┤
│ Accuracy   │ Preventable│ Cost       │ Alert      │ Data Quality    │
│ Rate       │ Failures   │ Avoidance  │ Response   │ Score           │
│ 73%  ▲     │ 3 this mo  │ 85M VNĐ   │ 97% ✓      │ 88% ✓           │
├────────────┴────────────┴────────────┴────────────┴─────────────────┤
│  RISK HEATMAP — Fleet Overview (color: green/yellow/orange/red)      │
│  [Asset grid with risk scores — see UI spec for detail]              │
├─────────────────────────────────────────────────────────────────────┤
│  Active Alerts (Critical: 2 | High: 8 | Medium: 15)                 │
├─────────────────────────────────────────────────────────────────────┤
│  Budget Forecast (12-month bar chart)  │  Spare Demand Summary       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. QMS Mapping

### Document Hierarchy

```
QC-IMMIS-03  Quality Control — Analytics & Reporting
    └── PR-IMMIS-17-01  Procedure: Chạy và review predictive models
    └── PR-IMMIS-17-02  Procedure: Alert triage và escalation
    └── PR-IMMIS-17-03  Procedure: Model accuracy review định kỳ
    └── PR-IMMIS-17-04  Procedure: What-if analysis và budget planning
        ├── WI-IMMIS-17-01  Work Instruction: Vận hành Failure Risk Dashboard
        ├── WI-IMMIS-17-02  Work Instruction: Review PM Optimization Recommendations
        ├── WI-IMMIS-17-03  Work Instruction: Xử lý Spare Parts Forecast
        ├── WI-IMMIS-17-04  Work Instruction: Budget Forecast report cho BGĐ
        └── WI-IMMIS-17-05  Work Instruction: Chạy What-If Scenario Analysis
            ├── BM-IMMIS-17-01  Biểu mẫu: Predictive Alert Acknowledgment Form
            ├── HS-LOG-IMMIS-17-01  Hồ sơ: Prediction Run Log
            ├── HS-REC-IMMIS-17-01  Hồ sơ: Model Accuracy Review Record
            └── HS-REP-IMMIS-17-02  Hồ sơ: Monthly Predictive Analytics Report
```

### Audit Trail Requirements (WHO Governance)

Mọi prediction output phải có:
- Timestamp chính xác (giây) của lần chạy model
- Input data snapshot (giá trị các indicators tại thời điểm chạy)
- Model version và parameters
- Confidence score
- User đã view/acknowledge alert
- Action taken (hoặc lý do không action)

### Compliance Notes

- **WHO HTM 2025 §7.3**: Predictive maintenance programs phải documented và reviewed định kỳ
- **NĐ98/2021**: Dữ liệu bảo trì thiết bị y tế phải lưu trữ và traceable
- **ISO 13485 §7.5**: Kiểm soát quá trình, không cho phép automatic action mà không có human review

---

## 8. Deployment Prerequisites (Đợt 3)

Trước khi triển khai IMM-17, hệ thống phải có:

| Prerequisite | Nguồn | Tối thiểu |
|---|---|---|
| Installation records | IMM-04 | 100% active assets |
| PM records | IMM-08 | ≥ 12 tháng, ≥ 80% compliance |
| CM/Repair records | IMM-09 | ≥ 6 tháng, đầy đủ failure codes |
| Calibration records | IMM-11 | ≥ 80% calibratable assets |
| Spare consumption records | IMM-15 | ≥ 6 tháng |
| Cost data linked to WO | IMM-08/09 | ≥ 80% WO có cost |
| Asset valuation data | IMM-04/05 | 100% active assets |

---

## 9. Risks và Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Insufficient data quality → low prediction confidence | High (Đợt 3 early) | High | Data sufficiency check trước mọi prediction; flag low-confidence outputs rõ ràng |
| Users over-trust predictions → skip human judgment | Medium | High | UI phải luôn show confidence interval; training cho users; no auto-action |
| Model drift (predictions become inaccurate over time) | Medium | Medium | Weekly accuracy review; monthly model recalibration |
| Alert fatigue (too many non-actionable alerts) | Medium | Medium | Configurable thresholds; alert deduplication; severity tiering |
| Data privacy (cost data sensitive) | Low | Medium | Role-based access; audit log cho mọi data access |

---

*Tài liệu này là phần của bộ tài liệu IMM-17 gồm 6 files: Module Overview, Functional Specs, Technical Design, API Interface, UI/UX Guide, UAT Script.*
