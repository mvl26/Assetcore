# IMM-17 — Phân tích dự đoán
## Functional Specifications

**Phiên bản:** 1.0.0
**Ngày tạo:** 2026-04-24
**Tác giả:** BA Team / HTM Domain
**Trạng thái:** Draft

---

## 1. Use Cases

### UC-17-01 — Failure Risk Dashboard

| Thuộc tính | Chi tiết |
|---|---|
| **Tên** | Xem Dashboard Rủi ro Hỏng hóc |
| **Actor** | Nhóm HTM, Trung tâm Đổi mới sáng tạo, Tổ QLCL & Risk |
| **Kích hoạt** | User mở màn hình Predictive Cockpit; hoặc nhận alert email với link trực tiếp |
| **Mô tả** | Hiển thị toàn bộ fleet dưới dạng risk heatmap, với danh sách thiết bị nguy cơ cao nhất, KPIs tổng quan, và active alerts cần xử lý |

**Luồng chính:**
1. User đăng nhập và điều hướng đến `/imm17/cockpit`
2. System load prediction results từ lần chạy model gần nhất (≤ 7 ngày)
3. Hiển thị risk heatmap với màu sắc theo tier: Xanh/Vàng/Cam/Đỏ
4. Hiển thị danh sách Top 10 assets nguy cơ cao nhất
5. Hiển thị Active Alerts cần acknowledge
6. User có thể click vào asset để drill-down chi tiết (→ UC-17-09)

**Luồng phụ:**
- Nếu prediction data > 7 ngày cũ: hiển thị warning banner "Dữ liệu dự đoán cũ — chạy lại để cập nhật"
- Nếu asset không đủ data: hiển thị badge "Không đủ dữ liệu" thay vì risk score

**Điều kiện kết thúc:** User xem được dashboard và có thể điều hướng đến chi tiết

---

### UC-17-02 — PM Optimization Recommendations

| Thuộc tính | Chi tiết |
|---|---|
| **Tên** | Xem và xử lý đề xuất tối ưu lịch PM |
| **Actor** | Nhóm HTM (Biomedical Engineer) |
| **Kích hoạt** | User mở màn hình PM Optimization sau khi nhận notification |

**Luồng chính:**
1. User điều hướng đến `/imm17/pm-optimization`
2. System hiển thị danh sách recommendations, sort theo confidence (cao → thấp)
3. Mỗi recommendation gồm: asset, current interval, recommended interval, delta %, rationale, confidence score
4. User review từng recommendation:
   - **Accept** → tạo Change Request đến HTM Manager (không tự thay đổi Maintenance Plan)
   - **Reject** → ghi lý do, archive recommendation
   - **Defer** → snooze 30 ngày
5. Mọi action ghi vào audit log

**Business Rules áp dụng:** BR-17-03, BR-17-06, BR-17-08

---

### UC-17-03 — Spare Parts Demand Forecast

| Thuộc tính | Chi tiết |
|---|---|
| **Tên** | Xem dự báo nhu cầu phụ tùng thay thế |
| **Actor** | Nhóm Kho, Workshop |
| **Kích hoạt** | User mở màn hình Spare Forecast; hoặc trước chu kỳ đặt hàng |

**Luồng chính:**
1. User chọn time range (mặc định: 3 tháng tới)
2. System hiển thị forecast table: Part Number, Part Name, Forecasted Demand/month, Current Stock, Reorder Point, Recommended Order Qty
3. Các parts được highlight nếu current stock < reorder point
4. User có thể filter theo device model, department, hoặc criticality
5. User có thể export sang Excel cho quy trình mua sắm

**Điều kiện đặc biệt:** Nếu part có < 5 giao dịch lịch sử → hiển thị "Insufficient history — manual estimation required"

---

### UC-17-04 — Budget Forecast 12 Tháng

| Thuộc tính | Chi tiết |
|---|---|
| **Tên** | Xem và xuất dự báo ngân sách bảo trì 12 tháng |
| **Actor** | KH-TC (Finance/Planning), BGĐ |
| **Kích hoạt** | Đầu quý/năm cho chu kỳ lập kế hoạch ngân sách |

**Luồng chính:**
1. User điều hướng đến `/imm17/budget-forecast`
2. System hiển thị 12-month rolling forecast:
   - Stacked bar chart: PM cost / CM cost / Calibration cost / Parts cost
   - Confidence interval band (upper/lower bounds)
   - Comparison với actual spend year-to-date
3. User có thể điều chỉnh assumptions (inflation %, fleet changes) → xem tác động (→ UC-17-06)
4. User export báo cáo PDF/Excel cho trình BGĐ

---

### UC-17-05 — Replacement Candidate Report

| Thuộc tính | Chi tiết |
|---|---|
| **Tên** | Xem báo cáo thiết bị cần xem xét thanh lý/thay thế |
| **Actor** | Nhóm HTM, KH-TC, BGĐ |
| **Kích hoạt** | Monthly review; hoặc khi replacement score > threshold |

**Luồng chính:**
1. User điều hướng đến `/imm17/replacement-candidates`
2. System hiển thị assets với score > 60, sort theo score descending
3. Mỗi asset hiển thị: Score, Recommended Action, Age, TCO, Downtime %, Key Drivers
4. User có thể click "Initiate Decommission Review" → tạo IMM-13 record (với approval workflow)
5. User có thể export list cho budget planning

---

### UC-17-06 — What-If Analysis

| Thuộc tính | Chi tiết |
|---|---|
| **Tên** | Phân tích kịch bản What-If |
| **Actor** | Nhóm HTM, KH-TC, Trung tâm Đổi mới sáng tạo |
| **Kích hoạt** | Khi cân nhắc thay đổi chính sách bảo trì hoặc lập kế hoạch |

**Luồng chính:**
1. User điều hướng đến `/imm17/what-if`
2. User tạo scenario mới:
   - Đặt tên scenario
   - Chọn loại thay đổi: PM interval / Fleet composition / Parts cost / Staffing
   - Nhập giá trị thay đổi (% hoặc tuyệt đối)
   - Chọn scope (all assets / specific department / specific model)
3. System chạy simulation và hiển thị:
   - Expected impact lên: failure rate, maintenance cost, downtime, spare demand
   - Comparison: Before vs. After side-by-side
   - Risk trade-offs
4. User có thể save scenario và share với colleagues
5. User có thể export kết quả

**Ví dụ scenarios:**
- "Nếu giảm PM interval 20% cho ventilators → tăng bao nhiêu chi phí?"
- "Nếu thay thế 10 infusion pumps cũ → tiết kiệm bao nhiêu CM cost?"
- "Nếu tăng spare buffer 50% → giảm bao nhiêu downtime?"

---

### UC-17-07 — Predictive Alert Configuration

| Thuộc tính | Chi tiết |
|---|---|
| **Tên** | Cấu hình ngưỡng cảnh báo dự đoán |
| **Actor** | Tổ QLCL & Risk, Trung tâm Đổi mới sáng tạo |
| **Kích hoạt** | Initial setup; hoặc khi cần tune alert sensitivity |

**Luồng chính:**
1. User vào Settings > Predictive Alert Configuration
2. User xem Threshold Matrix hiện tại
3. User chỉnh ngưỡng cho từng alert type:
   - Failure Risk: High threshold (mặc định: 70), Critical threshold (mặc định: 85)
   - PM Optimization: Min delta to recommend (mặc định: 15%)
   - Replacement: Recommend threshold (mặc định: 75)
4. User config escalation: ai nhận alert, channel (email/in-app), SLA để acknowledge
5. System lưu config với effective date và audit log
6. User có thể simulate: "với ngưỡng này, bao nhiêu alerts hiện tại sẽ fire?"

---

### UC-17-08 — Model Performance Review

| Thuộc tính | Chi tiết |
|---|---|
| **Tên** | Review hiệu suất và độ chính xác của predictive models |
| **Actor** | Trung tâm Đổi mới sáng tạo, Tổ QLCL & Risk |
| **Kích hoạt** | Monthly; hoặc khi nhận notification về accuracy drop |
| **Tần suất** | Monthly mandatory review |

**Luồng chính:**
1. User mở Model Performance Review screen
2. System hiển thị cho mỗi model:
   - Accuracy metrics: True Positive Rate, False Positive Rate, Precision, Recall
   - Trend over last 6 months
   - Data quality score (% assets với sufficient data)
   - Confidence score distribution
3. User review và sign off (QMS requirement)
4. Nếu accuracy < target: user escalate cho investigation
5. Record được lưu vào HS-REC-IMMIS-17-01

---

### UC-17-09 — Drill-Down từ Prediction đến Source Records

| Thuộc tính | Chi tiết |
|---|---|
| **Tên** | Truy vết từ prediction đến dữ liệu nguồn |
| **Actor** | Nhóm HTM, Workshop |
| **Kích hoạt** | User click vào risk score hoặc prediction detail |

**Luồng chính:**
1. User click vào asset trong heatmap hoặc risk list
2. System mở Asset Risk Detail View
3. User thấy breakdown: mỗi factor đóng góp bao nhiêu vào risk score
4. User click vào factor (ví dụ: "High repair cost") → system hiển thị linked CM records
5. User có thể click vào từng record để mở detail trong IMM-09
6. Full traceability: từ prediction → indicator → source records

---

### UC-17-10 — Export Báo cáo cho BGĐ

| Thuộc tính | Chi tiết |
|---|---|
| **Tên** | Xuất báo cáo tổng hợp Predictive Analytics cho BGĐ |
| **Actor** | KH-TC, Tổ QLCL & Risk |
| **Kích hoạt** | Cuối tháng / quý |

**Luồng chính:**
1. User chọn Export Report > Monthly Predictive Analytics Report
2. User chọn time period và scope (all departments / selected)
3. System generate PDF/Excel gồm:
   - Executive Summary (risk overview, top concerns)
   - Fleet Health Scorecard
   - Budget Forecast vs. Actual
   - Top 10 Replacement Candidates
   - Action Items & Recommendations
   - Model Accuracy Report (QMS)
4. User preview và confirm
5. System tạo HS-REP-IMMIS-17-02 record với audit trail
6. User download hoặc email trực tiếp

---

## 2. Business Rules

### BR-17-01 — Data Sufficiency Requirement

**Mô tả:** Prediction model chỉ được chạy khi đủ dữ liệu lịch sử.

**Rule:**
```
FOR failure_risk_prediction:
    REQUIRE: asset.install_date <= (today - 6 months)
    REQUIRE: COUNT(pm_records WHERE asset = X) >= 2
    OR COUNT(cm_records WHERE asset = X) >= 2
    ELSE: prediction_result.status = "INSUFFICIENT_DATA"
          prediction_result.risk_score = NULL
          prediction_result.confidence = 0

FOR pm_optimization:
    REQUIRE: asset.install_date <= (today - 12 months)
    REQUIRE: COUNT(completed_pm_records WHERE asset = X) >= 4
    ELSE: skip, flag for review after next PM cycle

FOR budget_forecast:
    REQUIRE: fleet.size >= 10 assets
    REQUIRE: cost_records spanning >= 12 months
```

---

### BR-17-02 — Confidence Interval Bắt buộc

**Mô tả:** Mọi prediction output phải đính kèm confidence indicator. Không có prediction nào được hiển thị mà không có confidence level.

**Rule:**
```
prediction.confidence_level ∈ [Low (< 60%), Medium (60–80%), High (> 80%)]
prediction.confidence_score = FLOAT (0.0–1.0)
IF prediction.confidence_score < 0.5:
    display_prominent_warning = True
    color_indicator = GREY (not red/orange — avoid false alarm)
```

---

### BR-17-03 — Prediction Không Tự Tạo Work Order

**Mô tả:** Prediction là recommendation, không action. Hệ thống KHÔNG tự tạo Work Order, KHÔNG tự cập nhật Maintenance Plan, KHÔNG tự tạo Spare Parts Request.

**Rule:**
```
ON prediction_generated:
    CREATE: IMM Predictive Alert (recommendation only)
    DO NOT: create_work_order()
    DO NOT: update_maintenance_plan()
    DO NOT: create_purchase_request()

Tất cả actions phải được khởi tạo bởi user với quyền phù hợp.
```

---

### BR-17-04 — Audit Trail Bắt buộc cho Alerts

**Mô tả:** Mọi alert được tạo ra phải có đầy đủ audit trail theo WHO governance requirement.

**Rule:**
```
EVERY IMM Predictive Alert MUST record:
    - created_at: timestamp (giây)
    - asset: link
    - alert_type: enum
    - severity: enum
    - prediction_run: link to IMM Prediction Run
    - input_snapshot: JSON (các giá trị indicators tại thời điểm tạo alert)
    - model_version: string
    - acknowledged_by: user link (nullable)
    - acknowledged_at: timestamp (nullable)
    - action_taken: text (nullable)
    - closed_by, closed_at: (nullable)
```

---

### BR-17-05 — Model Refresh Schedule

**Mô tả:** Prediction models phải được chạy lại theo lịch để đảm bảo freshness.

**Rule:**
```
Scheduled jobs:
    WEEKLY (Monday 06:00): run_all_predictions()
        - Run failure risk for all eligible assets
        - Run replacement candidate scoring
        - Update budget forecast
    
    DAILY (06:30): check_prediction_alerts()
        - Check if any existing High/Critical alerts unacknowledged > 48h
        - Escalate to manager if SLA breached

    MONTHLY (1st Monday): model_accuracy_review_notification()
        - Notify Trung tâm Đổi mới sáng tạo to conduct monthly review
```

---

### BR-17-06 — Minimum Delta cho PM Optimization

**Mô tả:** Chỉ tạo PM optimization recommendation khi delta đủ lớn để có nghĩa.

**Rule:**
```
pm_recommendation_delta = abs(recommended_interval - current_interval) / current_interval
IF pm_recommendation_delta < 0.15 (15%):
    DO NOT create recommendation (noise suppression)
IF pm_recommendation_delta >= 0.15:
    CREATE recommendation with:
        - delta_pct
        - rationale
        - confidence
        - supporting_data_count (số failure events phân tích)
```

---

### BR-17-07 — Replacement Score Trigger

**Mô tả:** Khi replacement score vượt threshold, phải tạo alert và notification cho HTM Manager.

**Rule:**
```
IF replacement_score > 75:
    CREATE: IMM Predictive Alert (type=REPLACEMENT_CANDIDATE, severity=HIGH)
    NOTIFY: HTM Manager
    RECOMMEND: "Xem xét khởi tạo quy trình IMM-13 Decommission Review"
    
IF replacement_score > 90:
    severity = CRITICAL
    NOTIFY: HTM Manager + KH-TC
    SLA acknowledgment: 24 hours
```

---

### BR-17-08 — Giới hạn Điều chỉnh PM Interval

**Mô tả:** Đề xuất điều chỉnh PM interval không được vượt quá giới hạn an toàn.

**Rule:**
```
recommended_interval >= manufacturer_minimum_interval (nếu có)
recommended_interval <= manufacturer_maximum_interval × 1.5
recommended_interval >= 7 days (minimum absolute)
recommended_interval <= 365 days (maximum absolute for regular PM)

IF recommendation violates above bounds:
    CLAMP to nearest valid value
    ADD warning: "Adjustment limited by safety constraint"
```

---

### BR-17-09 — Spare Forecast Anomaly Detection

**Mô tả:** Phát hiện và flag consumption anomalies trước khi đưa vào forecast.

**Rule:**
```
FOR each part, each month:
    z_score = (monthly_consumption - rolling_avg) / rolling_std
    IF abs(z_score) > 3:
        flag as ANOMALY
        EXCLUDE from forecast baseline (hoặc dùng median thay thế)
        ADD note: "Tháng X có consumption bất thường — đã loại khỏi baseline"
```

---

### BR-17-10 — Data Staleness Warning

**Mô tả:** Cảnh báo khi dữ liệu nguồn không được cập nhật.

**Rule:**
```
FOR each data source module:
    IF last_record_date < (today - 30 days):
        ADD data_quality_warning to dashboard
        INCLUDE in model confidence calculation (penalize)
        
IF most_recent_prediction_run > 7 days ago:
    SHOW banner: "Dữ liệu dự đoán đã cũ. Lần chạy cuối: [date]. Cập nhật mới nhất sẽ có vào [next_scheduled_run]."
```

---

### BR-17-11 — What-If Scope Validation

**Mô tả:** What-if analysis phải có scope rõ ràng và giới hạn để tránh sai lệch.

**Rule:**
```
what_if_scenario.change_magnitude <= 100% (không cho phép > 2x thay đổi)
what_if_scenario.scope MUST be specified (not null)
what_if_scenario results:
    MUST include confidence interval
    MUST note assumptions used
    MUST NOT be used as budget commitment (advisory only)
    MUST expire after 90 days (re-run required for planning)
```

---

### BR-17-12 — Role-Based Access cho Sensitive Data

**Mô tả:** Chi phí và financial data trong predictions chỉ hiển thị cho users có quyền.

**Rule:**
```
Financial data (cost figures, budget forecast, TCO):
    VISIBLE to: KH-TC, Giám đốc, QLCL
    HIDDEN (replaced with "N/A") for: Workshop technicians (basic role)
    
Alert acknowledgment:
    HTM Engineer: acknowledge High alerts
    HTM Manager: acknowledge Critical alerts
    
Model configuration:
    ONLY: Trung tâm Đổi mới sáng tạo, System Admin
```

---

## 3. Alert Types và Escalation Rules

### Alert Type Matrix

| Alert Type | Trigger Condition | Severity | SLA Acknowledge | Escalation (nếu không ack) |
|---|---|---|---|---|
| `FAILURE_RISK_HIGH` | Risk score 70–84 | High | 48 giờ | HTM Manager |
| `FAILURE_RISK_CRITICAL` | Risk score ≥ 85 | Critical | 4 giờ | HTM Manager + Trưởng Khoa |
| `PM_OPTIMIZATION_AVAILABLE` | PM delta ≥ 15% | Info | 7 ngày | None |
| `SPARE_REORDER_REQUIRED` | Stock < reorder point | Medium | 72 giờ | Trưởng Kho |
| `SPARE_STOCKOUT_RISK` | Forecasted stockout trong 14 ngày | High | 24 giờ | Trưởng Kho + HTM Manager |
| `BUDGET_OVERRUN_FORECAST` | Forecast > budget 20% | High | 48 giờ | KH-TC |
| `REPLACEMENT_CANDIDATE` | Score 75–89 | High | 5 ngày | HTM Manager |
| `REPLACEMENT_URGENT` | Score ≥ 90 | Critical | 24 giờ | HTM Manager + BGĐ |
| `MODEL_LOW_ACCURACY` | Accuracy < 60% trong 30 ngày | Medium | 3 ngày | Trung tâm Đổi mới sáng tạo |
| `DATA_INSUFFICIENT` | < 80% fleet có sufficient data | Medium | 7 ngày | Data team |

### Escalation Flow

```
Alert Created (severity=Critical)
    │
    ├── T+0:  In-app notification → Primary Owner
    ├── T+4h: Email reminder nếu chưa acknowledge
    ├── T+8h: Escalate to Manager (in-app + email)
    └── T+24h: Escalate to Trưởng Phòng / BGĐ + flag in QMS log
    
Alert Created (severity=High)
    │
    ├── T+0:  In-app notification → Primary Owner
    ├── T+24h: Email reminder nếu chưa acknowledge
    └── T+48h: Escalate to Manager
```

---

## 4. Threshold Configuration Matrix

Các ngưỡng này là mặc định và có thể được cấu hình qua UC-17-07:

| Parameter | Default | Min | Max | Unit | Description |
|---|---|---|---|---|---|
| `failure_risk_high_threshold` | 70 | 50 | 90 | score | Ngưỡng High risk |
| `failure_risk_critical_threshold` | 85 | 70 | 95 | score | Ngưỡng Critical risk |
| `pm_optimization_min_delta` | 15 | 5 | 30 | % | Delta tối thiểu để tạo PM recommendation |
| `pm_interval_max_extension` | 50 | 10 | 100 | % | Giới hạn tối đa tăng interval |
| `spare_reorder_buffer_days` | 14 | 7 | 30 | days | Buffer lead time cho reorder point |
| `replacement_review_threshold` | 75 | 60 | 90 | score | Ngưỡng tạo Replacement alert |
| `replacement_urgent_threshold` | 90 | 80 | 95 | score | Ngưỡng Urgent replacement |
| `budget_overrun_alert_pct` | 20 | 10 | 50 | % | % vượt budget forecast để tạo alert |
| `model_min_accuracy_target` | 70 | 50 | 90 | % | Accuracy target cho Model review |
| `data_sufficiency_min_months` | 6 | 3 | 12 | months | Lịch sử tối thiểu để chạy model |
| `prediction_freshness_days` | 7 | 1 | 14 | days | Sau bao nhiêu ngày hiển thị warning staleness |
| `alert_dedup_window_hours` | 72 | 24 | 168 | hours | Không tạo alert trùng cho cùng asset/type |

---

*File tiếp theo: IMM-17_Technical_Design.md*
