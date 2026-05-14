# IMM-17 — Release & User Guide

| Mục | Giá trị |
|---|---|
| Module | IMM-17 — Phân tích dự đoán |
| Đợt | 3 |
| Trạng thái | Plan — release notes + user guide template |
| Cập nhật | 2026-05-10 |

---

## 1. Release scope (Wave 3 đợt đầu)

| Hạng mục | Có trong release | Defer |
|---|---|---|
| `AC Predictive Insight` DocType + workflow | ✓ | — |
| `IMM Predictive Model` versioning + activate | ✓ | — |
| Weekly cron `replacement_signal_calc` | ✓ | — |
| Cockpit FE (top-N + drill-down + ack) | ✓ | — |
| What-if PM cycle simulator | ✓ | — |
| IoT telemetry integration (INT-13 ML service) | — | Wave 3 cuối |
| Spare demand forecast (gọi IMM-15) | — | Wave 3 cuối |
| Federated learning multi-site | — | Wave 4 |

---

## 2. User guide tóm tắt

### 2.1 Trưởng VTTBYT / Operations Manager
1. Đăng nhập → menu IMM Operations → "Predictive Cockpit".
2. Xem top-N asset rủi ro tuần này.
3. Click 1 asset → xem contributing factors + lịch sử sự cố.
4. Quyết định:
   - "Mở Replacement Review" → chuyển IMM-13.
   - "Tạo PM Work Order" → chuyển IMM-08.
   - "Bỏ qua" → ghi lý do (bắt buộc).

### 2.2 HTM Engineer
- Sử dụng Cockpit + What-if simulator.
- Hỗ trợ Trưởng VTTBYT phân tích contributing factors.
- Đề xuất điều chỉnh PM cycle dựa trên insight.

### 2.3 Data Scientist
- Train model offline với dataset snapshot (xuất theo PR-IMMIS-17-01).
- Validate (precision/recall theo KPI-17-01/02).
- Đăng ký version qua `register_model` API.
- Phối hợp System Admin activate khi đủ điều kiện.

### 2.4 System Admin
- Theo dõi run logs hàng tuần.
- Activate / retire model version.
- Xử lý alert drift / fail / audit chain break.

### 2.5 Auditor / QA Officer
- Xem run logs + audit trail.
- Verify hash chain định kỳ.
- Báo cáo HS-REP-IMMIS-17-01 hàng quý.

---

## 3. Training plan

| Đối tượng | Nội dung | Thời lượng |
|---|---|---|
| Operations Manager | Đọc cockpit, ra hành động, không over-trust | 2h |
| HTM Engineer | Cockpit + what-if + contributing factors | 4h |
| Data Scientist | Pipeline architecture + model governance | 8h |
| Auditor | Audit chain + KPI verification | 2h |

> Tài liệu training: WI-IMMIS-17-01, WI-IMMIS-17-02 (xem `08_Deployment.md` §8).

---

## 4. Traceability matrix

| Yêu cầu (Architecture / BA) | Đáp ứng |
|---|---|
| Architecture line 258 — "Tạo lớp predictive analytics" | DocType + service + cockpit |
| Architecture line 258 — "model governance" | `IMM Predictive Model` + version + audit |
| Architecture line 258 — "what-if analysis" | UC-17-05 + page `/imm-17/whatif` |
| Architecture line 258 — "chuyển insight thành hành động" | UC-17-03 ack flow → IMM-08/13 |
| Architecture line 278 — Đợt 3 "predictive cockpit" | Page `/imm-17` cockpit |
| Architecture line 278 — gate "data lineage + chất lượng + management review" | §1 Pre-conditions trong `08_Deployment.md` |
| BA Scope_Decomposition §IMM-17 — "Predictive metric, anomaly alert" | `AC Predictive Insight` + replacement_signal event |
| BA Phase_03 §04 — naming `PI-.YYYY.-.######` | DocType naming series |
| BA Tap_4 — `replacement_signal_calc` weekly Sun 07:00 | Scheduler `0 7 * * 0` |
| BA Phase_07 INT-13 — Predictive ML service | Defer Wave 3 cuối |
| WHO HTM Performance & Replacement signal | KPI-17-03 lead time |

---

## 5. Known limitations (release Wave 3 đợt đầu)

- Model classical ML, KHÔNG dùng deep learning / IoT real-time.
- Threshold severity dùng giá trị seed, cần tuning sau 1 quarter.
- Cockpit chỉ hỗ trợ top-N theo replacement_score, chưa có view per-khoa breakdown.
- What-if chỉ simulate PM cycle, chưa simulate budget / replacement.

---

## 6. Roadmap kế tiếp

| Sprint sau go-live | Hạng mục |
|---|---|
| +1 quarter | Tune threshold theo KPI thực tế |
| +2 quarter | Tích hợp INT-13 vendor ML (nếu cần) |
| Wave 3 cuối | Spare demand forecast (IMM-17 ↔ IMM-15) |
| Wave 3 cuối | What-if budget (IMM-17 ↔ IMM-01) |
| Wave 4 | Multi-site federation, deep learning |

---

## 7. Release checklist

- [ ] Tất cả test ở `07_Testing_QA.md` §8 DoD pass.
- [ ] Tài liệu QMS (PR/WI/BM/HS/KPI-DASH) đã ban hành.
- [ ] Training cho 4 nhóm đã hoàn tất.
- [ ] Cron scheduler enabled production sau dry-run staging 4 tuần.
- [ ] Model `v0.x.y` Active + validation report đính kèm.
- [ ] Audit chain verify pass mẫu.
- [ ] Cockpit FE deploy + smoke test.
- [ ] Communication tới Trưởng phòng VT,TBYT + Tổ HC-QLCL.

---

## 8. Sign-off

| Vai trò | Người duyệt |
|---|---|
| Tech Lead | Trưởng nhóm IMMIS / CMMS |
| BA Lead | Nhóm Data + HTM |
| QMS | Tổ HC-QLCL & Risk |
| Sponsor | Trưởng phòng VT,TBYT |
