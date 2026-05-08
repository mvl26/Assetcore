# KPI / KRI METRIC DICTIONARY — ASSETCORE (v3)

> **Reconciled to v3 codebase — 2026-05-07.** KPI thực tế tính trong `services/imm00.rollup_asset_kpi` (monthly), `services/imm09.update_asset_mttr_avg` (MTTR), `api/dashboard.get_overview` (live), `api/dashboard.get_dashboard_data` (full). Tham chiếu: `docs/ba/00_RECONCILIATION_v3.md`.

**Phiên bản:** 3.0
**Owner:** Tech Lead + BA Lead
**Áp dụng:** Wave 1 + Wave 2 đã ship

---

## 1. Convention

| Khía cạnh | Quy ước |
|---|---|
| **Metric ID** | `MET-<MODULE>-<NN>` — vd `MET-IMM08-01`, `MET-IMM09-MTTR` |
| **Storage** | Computed at-runtime (FE pull qua API) **HOẶC** rollup monthly (`services/imm00.rollup_asset_kpi`) |
| **Source** | DocType + filter SQL/ORM |
| **Refresh** | live (mỗi request), daily, weekly, monthly, quarterly |
| **Owner role** | Role chịu trách nhiệm cải thiện metric |

---

## 2. KPI Asset Registry / Foundation (IMM-00)

| ID | Metric | Công thức | Source | Refresh | Target | Owner |
|---|---|---|---|---|---|---|
| MET-IMM00-01 | Tổng số `AC Asset` Active | `count(workflow_state = 'Active')` | `AC Asset` | live | – | Operations Manager |
| MET-IMM00-02 | Tỷ lệ asset Out of Service | `count(Out of Service) / count(*)` | `AC Asset` | live | < 5% | Operations Manager |
| MET-IMM00-03 | Asset không có `IMM Device Model` | `count(device_model IS NULL)` | `AC Asset` | live | 0 | HTM Engineer |
| MET-IMM00-04 | GMDN coverage | `count(gmdn_status='OK') / count(*)` | `AC Asset` | live | ≥ 95% | HTM Engineer |
| MET-IMM00-05 | Audit chain integrity rate | `count(verify_audit_chain pass) / count(asset)` | `IMM Audit Trail` | weekly | 100% | Auditor |

---

## 3. KPI Procurement / Planning (IMM-01/02/03)

| ID | Metric | Công thức | Source | Refresh | Target | Owner |
|---|---|---|---|---|---|---|
| MET-IMM01-01 | Số Needs Request đang chờ duyệt | `count(workflow_state IN pending*)` | `IMM Needs Request` | live | – | Planning Officer |
| MET-IMM01-02 | Time-to-approve Needs (avg) | `avg(approval_at - submit_at)` | `IMM Needs Request` | weekly | ≤ 14 ngày | Operations Manager |
| MET-IMM01-03 | Budget envelope utilization | `sum(approved_value) / total_budget` | `IMM Procurement Plan` | weekly | ≤ 100% | Finance Officer |
| MET-IMM02-01 | Tỷ lệ Tech Spec locked đúng hạn | `count(locked_on_time) / count(submitted)` | `IMM Tech Spec` | weekly | ≥ 90% | HTM Engineer |
| MET-IMM02-02 | Benchmark freshness | `count(updated_within_180d) / count(*)` | `IMM Market Benchmark` | weekly | ≥ 80% | HTM Engineer |
| MET-IMM02-03 | High-severity lock-in risk count | `count(severity='High')` | `IMM Lock-in Risk Assessment` | live | < 5 | Risk Officer |
| MET-IMM03-01 | AVL active count | `count(workflow_state='Approved')` | `IMM AVL Entry` | live | – | Procurement Officer |
| MET-IMM03-02 | AVL expiring soon (60d) | `count(valid_until ≤ today+60)` | `IMM AVL Entry` | daily | (alert) | Procurement Officer |
| MET-IMM03-03 | Procurement decision time-to-award (avg) | `avg(award_at - decision_create)` | `IMM Procurement Decision` | monthly | ≤ 30 ngày | Procurement Officer |
| MET-IMM03-04 | Vendor scorecard avg | `avg(IMM Vendor Scorecard.total_score)` | `IMM Vendor Scorecard` | quarterly | ≥ 75/100 | Procurement Officer |

---

## 4. KPI Commissioning / Documents (IMM-04/05)

| ID | Metric | Công thức | Source | Refresh | Target | Owner |
|---|---|---|---|---|---|---|
| MET-IMM04-01 | Time-to-commission (avg) | `avg(release_at - install_start_at)` | `Asset Commissioning` | monthly | ≤ 14 ngày | HTM Engineer |
| MET-IMM04-02 | Tỷ lệ commissioning có Non Conformance | `count(NC raised) / count(submitted)` | `Asset Commissioning` + `Asset QA Non Conformance` | monthly | < 10% | HTM Engineer |
| MET-IMM04-03 | DOA rate | `count(DOA reported) / count(submitted)` | `Asset Commissioning` | monthly | < 2% | Procurement Officer |
| MET-IMM05-01 | Document compliance % | `count(active in-required-types) / count(required)` | `Asset Document` + `Required Document Type` | daily | ≥ 95% | Document Officer |
| MET-IMM05-02 | Documents expiring 60d | `count(expiry_date ≤ today+60)` | `Asset Document` | daily | (alert) | Document Officer |
| MET-IMM05-03 | Document Request open count | `count(status='Pending')` | `Document Request` | live | – | Document Officer |
| MET-IMM05-04 | Time-to-approve document (avg) | `avg(approved_at - submitted_at)` | `Asset Document` | weekly | ≤ 5 ngày | Document Officer |

---

## 5. KPI Preventive Maintenance (IMM-08)

| ID | Metric | Công thức | Source | Refresh | Target | Owner |
|---|---|---|---|---|---|---|
| MET-IMM08-01 | PM compliance % | `count(completed_on_time) / count(due)` | `PM Work Order` | monthly | ≥ 80% | Workshop Lead |
| MET-IMM08-02 | PM overdue count | `count(workflow_state='Overdue')` | `PM Work Order` | live | (alert) | Workshop Lead |
| MET-IMM08-03 | Avg PM completion time | `avg(completed_at - start_at)` | `PM Work Order` | monthly | ≤ 4 giờ | Biomed Technician |
| MET-IMM08-04 | PM-driven major failure rate | `count(report_major_failure) / count(completed)` | `PM Work Order` | monthly | < 1% | HTM Engineer |
| MET-IMM08-05 | PM auto-WO created vs scheduled | `count(WO from schedule) / count(due schedule)` | scheduler `imm08.generate_pm_work_orders_from_schedule` log | daily | 100% | System Admin |

---

## 6. KPI Repair / CM (IMM-09)

| ID | Metric | Công thức | Source | Refresh | Target | Owner |
|---|---|---|---|---|---|---|
| MET-IMM09-MTTR | MTTR (Mean Time To Repair) | `avg(close_at - open_at)` per repair | `Asset Repair` | monthly via `services/imm09.update_asset_mttr_avg` | ≤ 8 giờ (priority High) | Workshop Lead |
| MET-IMM09-MTBF | MTBF (Mean Time Between Failures) | `avg(time gap between failures)` per asset | `Asset Repair` + `Incident Report` | monthly via `services/imm00.rollup_asset_kpi` | ≥ 720h (30d) | HTM Engineer |
| MET-IMM09-01 | Open repair count | `count(workflow_state NOT IN closed)` | `Asset Repair` | live | – | Workshop Lead |
| MET-IMM09-02 | SLA breach count (hourly) | `count(is_overdue=1)` | `Asset Repair` | hourly via `services/imm09.check_repair_sla_breach` | < 5% | Workshop Lead |
| MET-IMM09-03 | Repair > 7 ngày count | `count(open_at ≤ today-7 AND state ≠ closed)` | `Asset Repair` | daily | < 3 | Workshop Lead |
| MET-IMM09-04 | Repeat failure rate (30d) | `count(asset has ≥2 repair in 30d)` | `Asset Repair` (`services/imm09.check_repeat_failure`) | weekly | < 5% asset | HTM Engineer |
| MET-IMM09-05 | Cannot Repair count | `count(workflow_state='Cannot Repair')` | `Asset Repair` | monthly | < 2% repairs | Workshop Lead |

---

## 7. KPI Calibration (IMM-11)

| ID | Metric | Công thức | Source | Refresh | Target | Owner |
|---|---|---|---|---|---|---|
| MET-IMM11-01 | Calibration compliance % | `count(within validity) / count(asset requires cal)` | `IMM Asset Calibration` + `AC Asset` | daily via `services/imm11.check_calibration_expiry` | ≥ 95% | QA Officer |
| MET-IMM11-02 | Calibration expiring 30d | `count(next_cal_due ≤ today+30)` | `AC Asset` | daily | (alert) | QA Officer |
| MET-IMM11-03 | Calibration fail rate | `count(workflow_state='Failed') / count(*)` | `IMM Asset Calibration` | monthly | < 5% | Biomed Technician |
| MET-IMM11-04 | Time-to-cal (avg) | `avg(cert_received - sent_to_lab)` | `IMM Asset Calibration` | monthly | ≤ 14 ngày | QA Officer |

---

## 8. KPI Incident / RCA / CAPA (IMM-12)

| ID | Metric | Công thức | Source | Refresh | Target | Owner |
|---|---|---|---|---|---|---|
| MET-IMM12-01 | Incident count (severity High+) | `count(severity IN High,Critical)` | `Incident Report` | live | (downward trend) | QA Officer |
| MET-IMM12-02 | Incident time-to-acknowledge | `avg(ack_at - report_at)` | `Incident Report` | daily | ≤ 1 giờ | Workshop Lead |
| MET-IMM12-03 | Incident time-to-resolve | `avg(resolved_at - report_at)` | `Incident Report` | weekly | ≤ 24h (High) | Workshop Lead |
| MET-IMM12-04 | RCA coverage rate | `count(RCA exists) / count(severity High+)` | `Incident Report` + `IMM RCA Record` | weekly | ≥ 95% | QA Officer |
| MET-IMM12-05 | CAPA open count | `count(IMM CAPA Record state ≠ closed)` | `IMM CAPA Record` | live | – | QA Officer |
| MET-IMM12-06 | CAPA overdue | `count(due_date < today AND state ≠ closed)` | `IMM CAPA Record` (`services/imm00.check_capa_overdue`) | daily | 0 | QA Officer |
| MET-IMM12-07 | CAPA close-on-time rate | `count(closed_on_time) / count(closed)` | `IMM CAPA Record` | monthly | ≥ 90% | QA Officer |
| MET-IMM12-08 | CAPA recurrence rate | `count(reopened) / count(closed)` | `IMM CAPA Record` | monthly | < 5% | QA Officer + Risk Officer |
| MET-IMM12-09 | Chronic failure asset count | `count(asset with ≥3 incidents/90d)` | `services/imm12.detect_chronic_failures` | daily | < 5 asset | HTM Engineer |

---

## 9. KPI Compliance / Contracts / Inventory (cross)

| ID | Metric | Công thức | Source | Refresh | Target | Owner |
|---|---|---|---|---|---|---|
| MET-IMM00-CONTRACT-01 | Service contract expiring 90d | `count(end_date ≤ today+90)` | `Service Contract` | daily via `services/imm00.check_service_contract_expiry` | (alert) | Procurement Officer |
| MET-IMM00-CONTRACT-02 | Vendor contract expiry overdue | `count(end_date < today AND active)` | `Service Contract` | daily | 0 | Procurement Officer |
| MET-IMM00-INSURANCE-01 | Insurance expiring 60d | `count(expiry_date ≤ today+60)` | (asset insurance fields) | daily | (alert) | Finance Officer |
| MET-IMM00-INV-01 | Spare part below reorder | `count(qty ≤ reorder_qty)` | `AC Spare Part Stock` | daily via `services/inventory.check_low_stock` | 0 critical | Storekeeper |
| MET-IMM00-DEPRECIATION-01 | Asset depreciation due | `count(schedule.due_date ≤ today)` | `AC Asset Depreciation Schedule` | monthly via `services/depreciation.run_due_depreciation` | – | Finance Officer |

---

## 10. KRI (Key Risk Indicators)

| ID | KRI | Threshold | Action khi vượt |
|---|---|---|---|
| KRI-01 | % Asset Out of Service > 8% | escalate Operations Manager + create Risk entry |
| KRI-02 | Audit chain integrity fail (any) | escalate IT + Auditor; freeze writes cho asset đó |
| KRI-03 | CAPA recurrence > 10% | review trigger source; escalate Risk Officer |
| KRI-04 | PM compliance < 70% | escalate Workshop Lead; mandatory review |
| KRI-05 | Calibration compliance < 90% | escalate QA Officer; prioritize backlog |
| KRI-06 | Chronic failure ≥ 5 asset | escalate HTM Engineer; trigger Risk Assessment |
| KRI-07 | Vendor scorecard < 60/100 | escalate Procurement Officer; consider AVL suspension |
| KRI-08 | Incident High+ tăng > 20% MoM | escalate Operations Manager + QA Officer |

---

## 11. Aggregation by dimension

Mọi KPI có thể slice theo:
- **Department** (`AC Department`)
- **Location** (`AC Location` hierarchy)
- **Asset Category** (`AC Asset Category`)
- **Device Model** (`IMM Device Model`)
- **Vendor / Supplier** (`AC Supplier`)
- **Risk Class** (1/2a/2b/3)
- **Period** (day, week, month, quarter, year)

API hỗ trợ filter qua params trong `api/dashboard.get_dashboard_data` và `api/imm0X.dashboard_kpis`.

---

## 12. Storage strategy

| Pattern | Khi nào | Implementation |
|---|---|---|
| **Live compute** (mỗi request) | KPI nhỏ (count, simple filter) | API trực tiếp query |
| **Monthly rollup** | KPI agg lớn / time-series | `services/imm00.rollup_asset_kpi` chạy monthly 1st 06:00; ghi vào field trên asset (vd `mttr_avg_12m`) |
| **Hourly check** | SLA / breach detection | `services/imm09.check_repair_sla_breach` |
| **Daily snapshot** (đề xuất) | Trend / dashboard time-series | (BA gốc đề xuất `AC Dashboard Snapshot` — chưa implement; hiện compute live) |

---

## 13. Tham chiếu

- Service: `assetcore/services/imm00.py` (rollup), `imm09.py` (MTTR), `imm00.py` (CAPA, contract checks).
- API: `assetcore/api/dashboard.py`, `api/imm0X.dashboard_kpis()`.
- Scheduler: `assetcore/hooks.py.scheduler_events`.
- Mapping BA gốc: `docs/ba/00_RECONCILIATION_v3.md`.

---

## 14. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Tech Lead |  | 2026-05-07 |
| BA Lead |  | 2026-05-07 |
| QA Officer |  | 2026-05-07 |
| Operations Manager |  | 2026-05-07 |
