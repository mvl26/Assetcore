# IMM-17 — Phân tích & Thiết kế (Analysis & Design)

| Mục | Giá trị |
|---|---|
| Module | IMM-17 — Phân tích dự đoán (Predictive Analytics) |
| Khối | C. KHỐI 3 — Vận hành |
| Đợt | 3 (Predictive cockpit) |
| Trạng thái | Draft — BE chưa scaffold |
| Cập nhật | 2026-05-10 |

> Tài liệu này là từ-scratch. Tất cả số liệu KPI, threshold, accuracy chưa có baseline thực tế — đánh dấu *(Cần khảo sát baseline)*. Field DocType, endpoint shape chỉ liệt kê tên + mô tả 1 dòng; chi tiết sẽ thiết kế trong sprint Wave 3.

---

## I.0 Khảo sát hiện trạng (As-Is)

### Bối cảnh
Trước khi có IMM-17, các quyết định bảo trì/thay thế dựa vào:
- Lịch PM cố định (định kỳ theo thời gian, không theo tình trạng thực).
- Phản ứng sau sự cố (corrective sau khi đã hỏng → downtime cao).
- Kinh nghiệm cá nhân của KTV BME / Trưởng VTTBYT.

### Hạn chế
- Không có chỉ số dự báo → replacement signal phát hiện muộn.
- PM cycle "một-cỡ-cho-tất-cả" gây lãng phí và bỏ sót thiết bị có nguy cơ cao.
- Tồn kho phụ tùng không tối ưu (over-stock hoặc out-of-stock).
- Không tận dụng được lượng dữ liệu lifecycle/work-order/calibration đã tích lũy.

### Cơ hội (đầu vào IMM-17)
Sau Wave 1 + Wave 2, hệ thống đã có:
- `Asset Lifecycle Event` immutable, append-only (mọi sự kiện vòng đời).
- `IMM Audit Trail` SHA-256 hash chain.
- WO history (PM, CM, Calibration) đầy đủ trường timestamp, kết quả, chi phí.
- KPI snapshot từ IMM-07 (availability, utilization, downtime).

→ Đủ điều kiện xây lớp predictive analytics + model governance + what-if.

---

## I.1 Pitch

> Tạo lớp **predictive analytics** lên trên kho dữ liệu vận hành để dự báo **failure**, đề xuất **chu kỳ PM tối ưu**, **optimization phụ tùng** và phát hiện **replacement signal** sớm — chuyển insight thành hành động vận hành thông qua cảnh báo, tạo Work Order tự động và what-if simulation cho Trưởng VTTBYT.

(Nguồn: Architecture line 258 — "Tạo lớp predictive analytics, model governance, what-if analysis và chuyển insight thành hành động vận hành.")

---

## I.2 Lifecycle Phase

IMM-17 hoạt động **xuyên suốt** giai đoạn Operation (sau commissioning, trước decommissioning):

```
Needs → Procurement → Installation → [Operation ← IMM-17 ←] → Decommission
                                          ↑
                              feeds insight + signal back to:
                                IMM-07 (KPI), IMM-08 (PM cycle),
                                IMM-09 (CM prep), IMM-15 (spare),
                                IMM-13 (replacement decision)
```

Không tạo state mới trên `AC Asset` mà **đề xuất** action cho các module xuôi dòng.

---

## I.3 Stakeholders

| Actor | Vai trò | Tham chiếu Architecture |
|---|---|---|
| Trưởng phòng VT,TBYT | Đọc cockpit + duyệt replacement signal | §"Vai trò triển khai" (line 265) |
| PTP phụ trách Khối 2 | Owner module IMM-17 | line 267 |
| Tổ HC-QLCL & Risk | Validate model output, audit | line 268 |
| Data Scientist (BV / Vendor) | Train/maintain model, tuning | BA Scope_Decomposition §IMM-17 |
| Trưởng VTTBYT | Tiếp nhận signal, ra hành động | line 265 |
| CMMS/IMMIS team | Vận hành pipeline + scheduler job | line 270 |
| Vendor ML service | (Wave 3+) Cung cấp model qua INT-13 | BA Integration_Landscape §INT-13 |

---

## I.4 Scope

### In-scope (Wave 3 đợt đầu)
- Pipeline tổng hợp dữ liệu lifecycle/WO/calibration thành **feature set** cho model.
- DocType lưu **predictive insight** (failure score, replacement signal, recommended PM cycle).
- Scheduler job định kỳ (weekly) tính `replacement_signal_calc` (đã được khai báo trong BA workflow doc).
- Cockpit UI hiển thị top-N asset có nguy cơ + drill-down lịch sử.
- Action wiring: từ insight → tạo PM Work Order / Incident / Replacement Review (gọi service IMM-08/09/13).
- Model governance: version, training dataset snapshot, audit trail mỗi inference.

### Out-of-scope (defer)
- IoT telemetry real-time (cần INT-13 + IoT gateway → Wave 3 cuối / Wave 4).
- Deep learning / neural network model — Wave 3 đợt đầu chỉ dùng statistical / classical ML.
- Federated learning across multi-site — Wave 4.
- What-if cho budget planning (cross IMM-01) — sprint riêng sau khi model ổn định.

---

## I.5 KPI / KRI

| Mã | Chỉ số | Công thức | Target | Tần suất |
|---|---|---|---|---|
| KPI-17-01 | Failure prediction precision | TP / (TP + FP) trong cửa sổ 30 ngày | ≥ 0.70 *(Cần khảo sát baseline)* | Hàng tháng |
| KPI-17-02 | Failure prediction recall | TP / (TP + FN) | ≥ 0.60 *(Cần khảo sát baseline)* | Hàng tháng |
| KPI-17-03 | Replacement signal lead time | Ngày từ signal → quyết định IMM-13 | ≥ 60 ngày trước EoL *(Cần khảo sát)* | Hàng quý |
| KPI-17-04 | PM cycle optimization saving | (PM cũ - PM gợi ý) × cost / năm | *(Cần khảo sát baseline)* | Hàng quý |
| KPI-17-05 | Spare demand forecast MAPE | mean absolute percentage error | ≤ 25% *(Cần khảo sát)* | Hàng tháng |
| KRI-17-01 | Model drift | Feature distribution shift score | < ngưỡng cảnh báo *(Cần khảo sát)* | Hàng tuần |
| KRI-17-02 | Insight ignored rate | % insight không được action sau 14 ngày | ≤ 30% *(Cần khảo sát)* | Hàng tháng |

> Toàn bộ baseline phải khảo sát sau khi có ≥6 tháng dữ liệu sản xuất từ IMM-07/08/09/11/12.

---

## I.6 Compliance / NĐ98 / WHO HTM

- **WHO HTM — chương Performance & Replacement signal**: bắt buộc có cơ chế phát hiện thiết bị suy giảm hiệu năng để lên kế hoạch thay thế. IMM-17 hiện thực hoá yêu cầu này.
- **NĐ98/2021 (mã GMDN)**: predictive insight không thay đổi phân loại A/B/C/D, nhưng *kết quả* có thể là input cho hồ sơ post-market surveillance (IMM-10).
- **Audit trail**: mọi inference + signal phải được ghi vào `IMM Audit Trail` (hash chain) với event_type chuyên biệt — không sửa, không xoá.
- **Model governance**: mỗi phiên bản model được lưu version + dataset snapshot reference; kết quả gắn `model_version` để truy nguyên.
- **Không quyết định tự động**: insight chỉ là khuyến nghị. Mọi action vận hành (tạo WO, đề xuất replacement) phải có người duyệt theo workflow gốc của module xuôi dòng.

---

## I.7 Functional Requirements (FR)

| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-17-01 | Tổng hợp feature từ Asset Lifecycle Event + WO history | Must |
| FR-17-02 | Sinh `AC Predictive Insight` per asset + per kỳ chạy | Must |
| FR-17-03 | Phát signal `replacement_signal_emitted` qua Lifecycle Event | Must |
| FR-17-04 | Hiển thị cockpit top-N asset rủi ro + filter theo khoa/loại | Must |
| FR-17-05 | Action: tạo PM Work Order theo insight | Should |
| FR-17-06 | Action: tạo Incident Report nếu signal severity = High | Should |
| FR-17-07 | What-if: thay PM cycle → ước lượng failure probability | Should |
| FR-17-08 | Model versioning + dataset snapshot reference | Must |
| FR-17-09 | Audit trail mọi inference | Must |
| FR-17-10 | Vendor ML service integration (INT-13) | Could (Wave 3 cuối) |

## I.8 Non-Functional Requirements (NFR)

| ID | Loại | Yêu cầu |
|---|---|---|
| NFR-17-01 | Performance | Pipeline weekly hoàn tất < 30 phút cho 5,000 asset *(Cần khảo sát)* |
| NFR-17-02 | Reliability | Scheduler job retry ≥ 2 lần khi fail, alert nếu fail 3 lần |
| NFR-17-03 | Auditability | 100% inference có audit record, hash chain verify pass |
| NFR-17-04 | Explainability | Mỗi insight phải có `contributing_factors` (top features) |
| NFR-17-05 | Security | Vendor ML service chỉ nhận dataset đã anonymise (không PHI/PII) |
| NFR-17-06 | Maintainability | Model retrain định kỳ (quarterly) + on-demand khi drift |
| NFR-17-07 | Fairness | Không bias theo khoa/vendor — kiểm tra qua slice metrics |

---

## II. BPMN — Predictive Pipeline (Overview)

```
[Cron: Sunday 07:00] (đã khai báo: replacement_signal_calc 0 7 * * 0)
        │
        ▼
[1. Extract] ─ pull from:
        ├─ Asset Lifecycle Event (append-only)
        ├─ PM Work Order history (IMM-08)
        ├─ Asset Repair history (IMM-09)
        ├─ IMM Asset Calibration (IMM-11)
        ├─ Incident Report + RCA (IMM-12)
        └─ KPI snapshot (IMM-07 — nếu đã có)
        │
        ▼
[2. Feature engineering]
        - MTBF rolling, MTTR rolling
        - Calibration drift slope
        - Incident frequency last 90/180 days
        - Cumulative downtime
        - Age vs expected lifecycle
        │
        ▼
[3. Inference]
        - Load model (current version)
        - Score per asset → failure_score, replacement_score
        - Generate contributing_factors
        │
        ▼
[4. Persist]
        - Insert AC Predictive Insight (1 record / asset / run)
        - Log audit event (immutable)
        - If replacement_score >= threshold:
              → create Lifecycle Event "replacement_signal_emitted"
              → notify Trưởng VTTBYT
        │
        ▼
[5. Cockpit refresh]
        - Frontend revalidate query (TanStack)
```

---

## III. Use Cases (overview)

### UC-17-01 — Cron predictive run
- **Actor**: System scheduler.
- **Pre**: Có ≥1 asset active.
- **Flow**: Step 1–4 ở BPMN trên.
- **Post**: ≥1 `AC Predictive Insight` mới + audit record.

### UC-17-02 — Trưởng VTTBYT xem cockpit
- **Actor**: IMM Operations Manager.
- **Pre**: Đã có insight được sinh trong 7 ngày gần nhất.
- **Flow**: Vào dashboard → filter theo khoa/loại → drill-down 1 asset → xem contributing factors → quyết định action.
- **Post**: Có thể tạo PM WO / Incident / Replacement Review.

### UC-17-03 — Acknowledge replacement signal
- **Actor**: IMM Operations Manager / IMM HTM Engineer.
- **Pre**: Có signal `replacement_signal_emitted` chưa xử lý.
- **Flow**: Mở insight → review evidence → chọn "Mở Replacement Review" (chuyển sang IMM-13) hoặc "Bỏ qua + ghi lý do".
- **Post**: Audit trail ghi quyết định + actor.

### UC-17-04 — Data Scientist deploy model mới
- **Actor**: Data Scientist + IMM System Admin.
- **Pre**: Model đã pass validation offline (precision/recall đạt target).
- **Flow**: Upload artifact → đăng ký version → activate → inference từ run kế tiếp dùng version mới.
- **Post**: `model_version` trên insight tăng; audit record cho thay đổi.

### UC-17-05 — What-if PM cycle (Wave 3 sau)
- **Actor**: IMM HTM Engineer.
- **Pre**: Model đã ổn định.
- **Flow**: Chọn asset → đặt giả định PM cycle = X tháng → xem ước lượng failure probability.
- **Post**: Có thể export báo cáo what-if (không thay đổi state thật).

---

## IV. Cross-module integration

| Source | Cung cấp cho IMM-17 | Hình thức |
|---|---|---|
| IMM-07 KPI snapshot | availability, utilization, downtime | Read DocType (TBD trong sprint IMM-07) |
| IMM-08 PM history | WO completed/overdue, checklist result | Read `PM Work Order` |
| IMM-09 Repair history | MTTR, spare consumed, fault category | Read `Asset Repair` |
| IMM-11 Calibration | Out-of-tolerance trend | Read `IMM Asset Calibration` |
| IMM-12 Incident/RCA | Chronic flag, severity | Read `Incident Report`, `IMM RCA Record` |
| IMM-17 → IMM-08 | Đề xuất PM cycle mới | Service call (tạo PM Schedule) |
| IMM-17 → IMM-09 | Đề xuất CM trước khi hỏng | Service call (tạo Asset Repair draft) |
| IMM-17 → IMM-13 | Replacement signal | Lifecycle Event + UI link |
| IMM-17 → IMM-15 | Spare demand forecast | Read-only output (Wave 3 cuối) |

> Chi tiết wiring trong `04_Backend_Design.md`.

---

## V. Rủi ro & Giả định

### Rủi ro
- **Chất lượng dữ liệu thấp** → insight không tin cậy. Mitigation: gate "đủ ≥12 tháng dữ liệu" trước khi go-live.
- **Model drift** → KRI-17-01 + retrain quarterly.
- **Bias theo khoa/vendor** → slice metrics + fairness review.
- **User không hành động trên insight** → KRI-17-02 + dashboard nhắc.

### Giả định
- IMM-07 đã ship KPI snapshot DocType trước khi IMM-17 go-live.
- Volume asset ≤ 10,000 trong giai đoạn Wave 3 đầu (chưa cần distributed compute).
- Vendor ML service (nếu dùng) tuân thủ data residency của BV.

---

## VI. Ràng buộc thiết kế

- KHÔNG modify ERPNext core (tuân R-01 CLAUDE.md `ba/`).
- 3-tier strict (R-02): API → Service → Controller.
- Mọi state-equivalent (như emit signal) phải qua Lifecycle Event API duy nhất.
- Audit trail bắt buộc cho mọi inference (R-04).
- Model retrain → ghi audit + version, không xoá lịch sử.
