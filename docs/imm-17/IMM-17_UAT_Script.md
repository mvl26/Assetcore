# IMM-17 — Phân tích dự đoán
## UAT Script (User Acceptance Testing)

**Phiên bản:** 1.0.0
**Ngày tạo:** 2026-04-24
**Module:** IMM-17 — Predictive Analytics
**Đợt triển khai:** Đợt 3
**QMS ref:** PR-IMMIS-17-04 (Quy trình kiểm thử và nghiệm thu IMM-17)

---

## 1. Điều kiện tiên quyết (Pre-conditions)

### 1.1 Dữ liệu fixture bắt buộc

Trước khi chạy UAT, hệ thống phải có dữ liệu lịch sử tối thiểu:

| Loại dữ liệu | Yêu cầu tối thiểu | DocType nguồn |
|---|---|---|
| Assets trong vận hành | ≥ 15 assets, thuộc ≥ 3 categories | `AC Asset` |
| Lịch sử PM | ≥ 12 tháng, ≥ 2 chu kỳ/asset | `PM Work Order` |
| Lịch sử sửa chữa | ≥ 30 CM/repair records | `Asset Repair`, `Incident Report` |
| Lịch sử hiệu chuẩn | ≥ 2 lần/asset (cho assets cần cal) | `IMM Asset Calibration` |
| Giao dịch phụ tùng | ≥ 24 tháng consumption history | `AC Stock Movement` |
| Chi phí bảo trì | Có cost data trong WO | `PM Work Order`, `Asset Repair` |

### 1.2 Tài khoản cần chuẩn bị

| Tài khoản | Role Frappe | Dùng cho TC |
|---|---|---|
| `uat_htmgr@hospital.vn` | IMM Operations Manager | TC-01 đến TC-15 |
| `uat_biomed@hospital.vn` | IMM Technician | TC-05, TC-06, TC-15 |
| `uat_storekeeper@hospital.vn` | IMM Storekeeper | TC-07, TC-08 |
| `uat_qaoff@hospital.vn` | IMM QA Officer | TC-18, TC-19 |
| `uat_director@hospital.vn` | IMM Department Head | TC-10, TC-17 |

### 1.3 Cấu hình hệ thống

- Scheduler đã chạy ít nhất 1 lần `run_all_predictions()`
- `IMM Alert Config` đã cấu hình ngưỡng mặc định
- Prediction results không cũ hơn 7 ngày

---

## 2. Test Cases

### NHÓM A — Failure Risk Dashboard (TC-01 → TC-04)

---

#### TC-01 — Xem Predictive Cockpit Dashboard

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-01 |
| **Tiêu đề** | Hiển thị Risk Dashboard đầy đủ |
| **Actor** | HTM Manager (`uat_htmgr@hospital.vn`) |
| **Module** | UC-17-01 |
| **Điều kiện** | Prediction đã chạy, data ≤ 7 ngày |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Đăng nhập với `uat_htmgr`, điều hướng đến `/imm17/cockpit` | Trang Predictive Cockpit load thành công |
| 2 | Quan sát Risk Heatmap | Hiển thị grid các assets, màu sắc phân tầng: Xanh (low) / Vàng (medium) / Cam (high) / Đỏ (critical) |
| 3 | Quan sát danh sách "Top 10 High Risk" | Hiển thị ≥ 1 asset, mỗi row có: asset name, risk score (0-100), risk tier badge, last updated |
| 4 | Quan sát KPI summary panel | Hiển thị: tổng assets monitored, % high-risk, total active alerts, model last run timestamp |
| 5 | Quan sát Active Alerts section | Nếu có alerts chưa acknowledge: hiển thị danh sách với severity badge |
| 6 | Click vào 1 asset trên heatmap | Điều hướng đến Asset Risk Detail view của asset đó |

**Kết quả thực tế:** _______________________________________________

**Pass / Fail:** ☐ Pass  ☐ Fail

**Ghi chú:** _______________________________________________

---

#### TC-02 — Hiển thị cảnh báo khi dữ liệu dự đoán cũ

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-02 |
| **Tiêu đề** | Warning banner khi prediction > 7 ngày |
| **Actor** | HTM Manager |
| **Điều kiện** | Thay đổi `last_run_date` của prediction run gần nhất sang ngày 8 ngày trước |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Vào DB: `UPDATE imm_prediction_run SET creation = DATE_SUB(NOW(), INTERVAL 8 DAY) WHERE name = (SELECT name FROM imm_prediction_run ORDER BY creation DESC LIMIT 1)` | — |
| 2 | Load `/imm17/cockpit` | Banner cảnh báo vàng xuất hiện: "⚠ Dữ liệu dự đoán đã cũ (8 ngày) — Nhấn 'Cập nhật' để chạy lại" |
| 3 | Click nút "Cập nhật" | Trigger `POST /api/method/assetcore.api.imm17.trigger_prediction_run` |
| 4 | Đợi hoàn thành (polling) | Banner biến mất, dashboard refresh với data mới |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

#### TC-03 — Drill-down từ Risk Score về source records

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-03 |
| **Tiêu đề** | Truy nguyên risk score về bản ghi nguồn |
| **Actor** | HTM Manager |
| **Business Rule** | BR-17-09: Mọi prediction phải truy nguyên được về source records |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Click vào asset có risk score cao (≥ 70) trên cockpit | Mở Asset Risk Detail view |
| 2 | Quan sát Risk Score Breakdown panel | Hiển thị breakdown: Age factor (x%), Failure freq factor (x%), Cost factor (x%), Downtime factor (x%), với weight % cho mỗi factor |
| 3 | Click vào "Failure Frequency" factor | Dropdown/panel hiển thị danh sách các CM/Incident records đã contribute vào factor này với link trực tiếp |
| 4 | Click vào 1 Incident Record link | Điều hướng đến IMM-12 Incident Detail view của record đó |
| 5 | Quay lại, click "Maintenance Cost" factor | Hiển thị WO records với cost data |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

#### TC-04 — Asset không đủ dữ liệu lịch sử

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-04 |
| **Tiêu đề** | Xử lý asset thiếu data (< 6 tháng history) |
| **Actor** | HTM Manager |
| **Business Rule** | BR-17-01: Prediction chỉ run khi đủ data |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Tạo 1 asset mới qua IMM-04 (chưa có PM/CM history) | Asset tồn tại với lifecycle_status = Active |
| 2 | Load `/imm17/cockpit`, tìm asset mới | Asset hiển thị với badge "Chưa đủ dữ liệu" (màu xám), không có risk score số |
| 3 | Click vào asset đó | Asset Risk Detail view hiển thị: "Thiết bị cần ≥ 6 tháng dữ liệu vận hành để phân tích. Hiện có: X tháng." |
| 4 | Kiểm tra API: `GET .../get_asset_risk_score?asset=<new_asset>` | Response: `{ "ok": false, "error": "INSUFFICIENT_DATA", "months_available": X, "months_required": 6 }` |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

### NHÓM B — PM Optimization (TC-05 → TC-06)

---

#### TC-05 — Xem và xử lý đề xuất tối ưu PM

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-05 |
| **Tiêu đề** | Review và Accept PM Optimization Recommendation |
| **Actor** | Biomedical Engineer (`uat_biomed@hospital.vn`) |
| **Business Rule** | BR-17-03: Accept chỉ tạo Change Request, không tự sửa PM Schedule |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Điều hướng đến `/imm17/pm-optimization` | Danh sách recommendations load, sort theo confidence DESC |
| 2 | Tìm recommendation có confidence ≥ 70% | Row hiển thị: Asset, Current Interval, Recommended Interval, Delta, Rationale text, Confidence % |
| 3 | Click "Accept" trên 1 recommendation | Modal xác nhận hiện ra: "Xác nhận gửi Change Request đến HTM Manager?" |
| 4 | Confirm | Change Request tạo thành công. Notification gửi đến HTM Manager. Status recommendation → "Pending Review". |
| 5 | Kiểm tra audit log | Action "accept_pm_recommendation" được ghi với actor, timestamp, asset, old_interval, new_interval |
| 6 | Kiểm tra IMM-08 PM Schedule | PM interval KHÔNG thay đổi (change request chưa approved) |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

#### TC-06 — Reject PM Recommendation với lý do

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-06 |
| **Tiêu đề** | Reject recommendation và ghi lý do |
| **Actor** | Biomedical Engineer |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Click "Reject" trên 1 recommendation | Modal hiện ra với textarea "Lý do từ chối" (required) |
| 2 | Để trống lý do, click Confirm | Validation error: "Vui lòng nhập lý do từ chối" |
| 3 | Nhập lý do: "Thiết bị đang trong hợp đồng bảo trì với nhà cung cấp, interval theo HĐ" | — |
| 4 | Click Confirm | Recommendation status → "Rejected", hiển thị reason, archived khỏi main list |
| 5 | Kiểm tra audit log | Action "reject_pm_recommendation" với lý do được ghi đầy đủ |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

### NHÓM C — Spare Parts Forecast (TC-07 → TC-08)

---

#### TC-07 — Xem dự báo nhu cầu phụ tùng

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-07 |
| **Tiêu đề** | Spare Parts Demand Forecast — 3 tháng |
| **Actor** | Storekeeper (`uat_storekeeper@hospital.vn`) |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Điều hướng đến `/imm17/spare-forecast` | Trang load với default range 3 tháng tới |
| 2 | Quan sát forecast table | Mỗi row: Part Code, Part Name, Forecasted Demand/month, Current Stock, Reorder Point, Recommended Order Qty, Confidence |
| 3 | Quan sát rows bị highlight đỏ | Các part có Current Stock < Reorder Point → highlight cảnh báo |
| 4 | Filter theo Device Model = "Máy theo dõi bệnh nhân XYZ" | Table lọc chỉ còn parts liên quan đến model đó |
| 5 | Click "Export Excel" | File `.xlsx` tải về với đúng dữ liệu đang hiển thị |
| 6 | Tìm part có < 5 giao dịch lịch sử | Badge "Insufficient history" hiển thị, không có số forecast |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

#### TC-08 — Kiểm tra logic forecast với dữ liệu đã biết

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-08 |
| **Tiêu đề** | Validate forecast accuracy với historical data |
| **Actor** | QA Officer |
| **Mục đích** | Xác minh model không bị bug — forecast phải hợp lý với consumption thực tế |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Chọn 1 part có consumption history đủ 12 tháng | — |
| 2 | Tính thủ công: average consumption 6 tháng gần nhất | — |
| 3 | So sánh với Forecasted Demand/month trong UI | Forecast phải nằm trong khoảng ±30% so với average thực tế (acceptable tolerance) |
| 4 | Call API: `GET .../get_spare_demand_forecast?part_code=<X>&months=3` | Response chứa: `forecast_by_month`, `confidence_interval_low`, `confidence_interval_high`, `historical_avg` |
| 5 | Xác nhận `historical_avg` trong response khớp với tính tay | Sai số ≤ 5% (rounding acceptable) |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

### NHÓM D — Budget Forecast (TC-09 → TC-10)

---

#### TC-09 — Xem Budget Forecast 12 tháng

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-09 |
| **Tiêu đề** | Budget Forecast — rolling 12 tháng |
| **Actor** | HTM Manager |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Điều hướng đến `/imm17/budget-forecast` | Biểu đồ line chart 12 tháng hiển thị |
| 2 | Quan sát chart | Có 2 series: PM Cost forecast (xanh) + CM Cost forecast (đỏ) + Total line (đen). Mỗi tháng có confidence band (shaded area) |
| 3 | Hover vào tháng bất kỳ | Tooltip: tháng, PM cost, CM cost, total, confidence range |
| 4 | Click "Chi tiết theo Device Category" | Breakdown table theo category: ICU / OR / General Ward... |
| 5 | Click "Export PDF" | PDF báo cáo tải về với header: "Dự báo Ngân sách Bảo trì — IMMIS" |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

#### TC-10 — Quyền truy cập Budget Forecast

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-10 |
| **Tiêu đề** | Chỉ Department Head mới thấy tổng ngân sách |
| **Actor** | Director (`uat_director@hospital.vn`) vs Technician |
| **Business Rule** | BR-17-11: Budget data restricted theo role |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Đăng nhập `uat_biomed` (Technician), vào `/imm17/budget-forecast` | Trang load nhưng tổng số tiền bị ẩn — chỉ thấy % change và trend direction |
| 2 | Đăng nhập `uat_director` (Dept Head), vào cùng URL | Trang load đầy đủ với số tiền VNĐ cụ thể |
| 3 | Kiểm tra API với Technician token | `GET .../get_budget_forecast` → response không có trường `amount_vnd`, chỉ có `trend_pct` |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

### NHÓM E — Replacement Candidates (TC-11 → TC-12)

---

#### TC-11 — Xem và xuất báo cáo Replacement Candidates

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-11 |
| **Tiêu đề** | Replacement Candidate Report — top assets cần xem xét thay thế |
| **Actor** | HTM Manager |
| **Business Rule** | BR-17-05: Score ≥ 70 → flag review; ≥ 90 → suggest IMM-13 trigger |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | `GET .../get_replacement_candidates` | Response: danh sách assets sort theo score DESC, mỗi item có `score`, `score_breakdown`, `age_years`, `total_cost_ownership`, `downtime_pct`, `failure_count_12m` |
| 2 | Trong UI, mở Replacement Candidates page | Danh sách assets với score badge màu: Xám (<50), Vàng (50-69), Cam (70-89), Đỏ (≥90) |
| 3 | Tìm asset có score ≥ 90 | Có nút "Đề xuất Ngừng sử dụng" → link mở IMM-13 Create form pre-filled với asset |
| 4 | Click "Đề xuất Ngừng sử dụng" | Redirect sang `/imm13/suspensions/new?asset=<asset_name>` với trường asset đã điền sẵn |
| 5 | Click "Export" | Báo cáo Excel/PDF tải về với đầy đủ dữ liệu |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

#### TC-12 — Kiểm tra chính xác Replacement Score

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-12 |
| **Tiêu đề** | Validate replacement score formula |
| **Actor** | QA Officer |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Chọn 1 asset, ghi lại: age_years, repair_cost_12m, asset_value, downtime_pct_12m, failure_count_12m | — |
| 2 | Tính tay: `Score = (age_factor×25) + (cost_factor×30) + (downtime_factor×25) + (failure_factor×20)` theo công thức trong Technical Design §4.1 | Kết quả tính tay = X |
| 3 | Lấy score từ API | Score API = Y |
| 4 | So sánh X vs Y | Sai số ≤ 1 điểm (do rounding) |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

### NHÓM F — What-If Analysis (TC-13 → TC-15)

---

#### TC-13 — Tạo và chạy What-If Scenario

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-13 |
| **Tiêu đề** | What-If: tăng PM interval 20% → impact tới failure rate |
| **Actor** | HTM Manager |
| **Business Rule** | BR-17-07: What-if không thay đổi production data |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Điều hướng đến `/imm17/what-if` | Scenario Builder form hiển thị |
| 2 | Chọn Scenario Type: "PM Interval Change" | Form hiện: Asset Category selector, Current Interval (auto-fill), New Interval input, Time Horizon (months) |
| 3 | Điền: Category = "Máy theo dõi bệnh nhân", New Interval = +20%, Time Horizon = 12 tháng | — |
| 4 | Click "Chạy phân tích" | Loading indicator hiển thị. Sau ≤ 30 giây: kết quả xuất hiện |
| 5 | Quan sát kết quả | Hiển thị: Projected Failure Rate Change (%), Projected CM Cost Change (VNĐ), Risk Level Change (pie chart so sánh before/after) |
| 6 | Kiểm tra production data | PM Schedules trong IMM-08 KHÔNG bị thay đổi |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

#### TC-14 — Lưu và so sánh nhiều Scenarios

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-14 |
| **Tiêu đề** | Lưu 2 scenarios và so sánh side-by-side |
| **Actor** | HTM Manager |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Chạy Scenario A: PM Interval +20% (từ TC-13) | Có kết quả |
| 2 | Click "Lưu Scenario" → đặt tên "Kéo dài PM 20%" | Scenario lưu thành công với ID |
| 3 | Tạo Scenario B: PM Interval -10% (giảm interval) | Chạy và lưu "Tăng tần suất PM 10%" |
| 4 | Click "So sánh Scenarios" → chọn cả 2 | Bảng so sánh side-by-side: Scenario A vs Scenario B, so sánh: projected failures, CM cost, risk distribution |
| 5 | Click "Export so sánh" | PDF/Excel tải về với cả 2 scenarios |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

#### TC-15 — What-If với Asset cụ thể

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-15 |
| **Tiêu đề** | What-If cho 1 asset đơn lẻ — thay đổi assignment technician |
| **Actor** | Workshop Lead |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Mở Asset Risk Detail của asset có risk cao | — |
| 2 | Click "What-If Analysis" trên asset này | What-If form pre-filled với asset đó |
| 3 | Scenario Type: "Assign Dedicated Technician" | Model dự đoán: nếu có KTV chuyên trách → projected failure response time giảm X% |
| 4 | Chạy | Kết quả: SLA compliance projected improvement, MTTR change |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

### NHÓM G — Alert System (TC-16 → TC-17)

---

#### TC-16 — Cấu hình ngưỡng cảnh báo và nhận alert

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-16 |
| **Tiêu đề** | Configure alert threshold → trigger alert → acknowledge |
| **Actor** | HTM Manager |
| **Business Rule** | BR-17-04: Audit trail bắt buộc cho mọi alert generated |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Gọi `POST .../configure_alert_threshold` với `{ "alert_type": "FAILURE_RISK", "threshold": 60, "severity": "HIGH" }` | Response 200: alert config saved |
| 2 | Trigger prediction run | — |
| 3 | Gọi `GET .../get_active_alerts` | Response chứa alerts cho tất cả assets có risk score ≥ 60 |
| 4 | Quan sát cockpit dashboard | Alerts hiển thị trong Active Alerts section với severity badge |
| 5 | Click "Acknowledge" trên 1 alert | Modal: nhập ghi chú. Submit → alert status = Acknowledged. Biến khỏi unacknowledged list |
| 6 | Kiểm tra `IMM Predictive Alert` DocType | Record tồn tại với đầy đủ: asset, alert_type, severity, generated_at, acknowledged_by, acknowledged_at, note |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

#### TC-17 — Escalation alert lên Department Head

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-17 |
| **Tiêu đề** | Alert severity CRITICAL tự động escalate lên Director |
| **Actor** | System (auto) → Director |
| **Business Rule** | BR-17-10: CRITICAL alert → email escalation trong 24h |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Cấu hình: `{ "alert_type": "FAILURE_RISK", "threshold": 90, "severity": "CRITICAL" }` | — |
| 2 | Update 1 asset để risk score ≥ 90 (inject via test fixture) | — |
| 3 | Trigger prediction run | — |
| 4 | Kiểm tra email inbox của `uat_director@hospital.vn` | Email nhận được: "CRITICAL Alert — [Asset Name] — Risk Score: 92/100 — Action Required" |
| 5 | Click link trong email | Redirect đến Asset Risk Detail của asset đó |
| 6 | Kiểm tra audit log | Alert generation event được ghi: asset, score, alert_type, notified_to (Director email) |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

### NHÓM H — Model Accuracy & Governance (TC-18 → TC-19)

---

#### TC-18 — Xem Model Accuracy Metrics

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-18 |
| **Tiêu đề** | Model Performance Review — accuracy và bias check |
| **Actor** | QA Officer (`uat_qaoff@hospital.vn`) |
| **Business Rule** | BR-17-08: Model accuracy phải ≥ 70% trên 90-day lookback |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Gọi `GET .../get_model_accuracy_metrics` | Response: `{ "failure_prediction_accuracy_90d": X%, "pm_recommendation_acceptance_rate": Y%, "forecast_mape": Z%, "last_evaluation_date": "..." }` |
| 2 | Quan sát UI: Model Performance section trong cockpit | Hiển thị accuracy gauge, acceptance rate, data quality score |
| 3 | Nếu accuracy < 70%: kiểm tra warning | Banner đỏ: "Model accuracy dưới ngưỡng — cần review dữ liệu đầu vào" |
| 4 | Kiểm tra `IMM Prediction Run` DocType | Mỗi run có: `input_data_quality_score`, `assets_analyzed`, `alerts_generated`, `run_duration_sec` |
| 5 | Audit trail: gọi `GET .../get_prediction_history` | Trả về 10 runs gần nhất với đầy đủ metadata |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

#### TC-19 — Kiểm tra Audit Trail của Prediction

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-19 |
| **Tiêu đề** | Audit trail đầy đủ cho mọi prediction output |
| **Actor** | QA Officer |
| **WHO requirement** | WHO 2025: clinical decision support tools phải có audit trail |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Chọn 1 `IMM Prediction Result` bất kỳ | — |
| 2 | Kiểm tra record có đủ fields | `prediction_run` (link), `asset`, `model_version`, `risk_score`, `confidence_low`, `confidence_high`, `input_data_snapshot` (JSON), `generated_at` |
| 3 | Kiểm tra `input_data_snapshot` | JSON chứa: tuổi thiết bị, số lần hỏng 12 tháng, tổng chi phí, downtime % đã dùng để tính score |
| 4 | Mô phỏng review 1 năm sau: có thể reconstruct tại sao score = X? | Dựa vào `input_data_snapshot`, tính lại score theo công thức → phải ra đúng score gốc |
| 5 | Kiểm tra Frappe Document History | Không có record nào bị xóa hay sửa sau khi tạo (immutable) |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

### NHÓM I — Edge Cases (TC-20)

---

#### TC-20 — Hệ thống thiếu toàn bộ historical data

| Trường | Chi tiết |
|---|---|
| **ID** | TC-17-20 |
| **Tiêu đề** | Graceful degradation khi không đủ data để chạy model |
| **Actor** | HTM Manager |
| **Business Rule** | BR-17-01, BR-17-12: fail gracefully, không crash |

**Các bước thực hiện:**

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Xóa toàn bộ prediction results (test env only) | — |
| 2 | Load `/imm17/cockpit` | Trang hiển thị với empty state đẹp: "Chưa có dữ liệu phân tích — Nhấn 'Chạy phân tích lần đầu'" |
| 3 | Click "Chạy phân tích lần đầu" | Spinner hiển thị. Backend chạy `run_all_predictions()` |
| 4 | Sau khi xong: nếu < 30% assets đủ data | Toast warning: "Chỉ có X% thiết bị đủ dữ liệu để phân tích. Kết quả có thể chưa đầy đủ." |
| 5 | Gọi API với asset không tồn tại | `GET .../get_asset_risk_score?asset=NONEXISTENT` → HTTP 404, `{ "error": "ASSET_NOT_FOUND" }` |
| 6 | Kiểm tra không có unhandled exceptions | Server logs không có 500 errors |

**Pass / Fail:** ☐ Pass  ☐ Fail

---

## 3. Acceptance Criteria (Điều kiện Nghiệm thu)

### 3.1 Functional

| Tiêu chí | Đánh giá |
|---|---|
| Tất cả 20 TC đạt Pass | ☐ |
| Risk heatmap hiển thị đúng màu cho tất cả risk tiers | ☐ |
| Drill-down từ risk score → source records hoạt động | ☐ |
| What-if KHÔNG thay đổi production data | ☐ |
| Alerts được ghi đầy đủ vào audit trail | ☐ |
| Model accuracy ≥ 70% trên 90-day lookback | ☐ |

### 3.2 Governance & Compliance

| Tiêu chí | Đánh giá |
|---|---|
| Mọi prediction có `input_data_snapshot` để reconstruct | ☐ |
| Prediction results immutable sau khi generated | ☐ |
| CRITICAL alerts trigger escalation email trong 24h | ☐ |
| Budget data restricted: chỉ IMM Department Head thấy số tiền | ☐ |
| Export hoạt động: Excel (spare), PDF (budget, replacement) | ☐ |

### 3.3 Performance

| Tiêu chí | Ngưỡng | Đánh giá |
|---|---|---|
| Dashboard load time | ≤ 3 giây | ☐ |
| Prediction run (full fleet) | ≤ 5 phút | ☐ |
| What-if analysis | ≤ 30 giây | ☐ |
| API response time | ≤ 1 giây (p95) | ☐ |

### 3.4 Non-Functional

| Tiêu chí | Đánh giá |
|---|---|
| Hệ thống không crash khi thiếu data | ☐ |
| Empty states hiển thị thông báo rõ ràng | ☐ |
| Tất cả predictions có confidence interval | ☐ |
| No unhandled 500 errors trong server logs | ☐ |

---

## 4. Execution Log

| TC ID | Ngày chạy | Người chạy | Kết quả | Defect ID | Ghi chú |
|---|---|---|---|---|---|
| TC-17-01 | | | | | |
| TC-17-02 | | | | | |
| TC-17-03 | | | | | |
| TC-17-04 | | | | | |
| TC-17-05 | | | | | |
| TC-17-06 | | | | | |
| TC-17-07 | | | | | |
| TC-17-08 | | | | | |
| TC-17-09 | | | | | |
| TC-17-10 | | | | | |
| TC-17-11 | | | | | |
| TC-17-12 | | | | | |
| TC-17-13 | | | | | |
| TC-17-14 | | | | | |
| TC-17-15 | | | | | |
| TC-17-16 | | | | | |
| TC-17-17 | | | | | |
| TC-17-18 | | | | | |
| TC-17-19 | | | | | |
| TC-17-20 | | | | | |

---

## 5. Sign-off

| Vai trò | Họ tên | Ngày | Ký xác nhận |
|---|---|---|---|
| BA / Test Lead | | | |
| HTM Manager (nghiệm thu nghiệp vụ) | | | |
| QA Officer (kiểm tra compliance) | | | |
| CMMS Admin (kiểm tra kỹ thuật) | | | |

---

*Tài liệu này thuộc phụ lục QMS: HS-REP-IMMIS-17-01 — Biên bản nghiệm thu IMM-17*
*Controlled copy: Có | Nơi lưu: QMS điện tử/IMMIS/17-* | Phiên bản: 1.0.0*
