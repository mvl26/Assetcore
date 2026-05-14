# WAVE PLAN — ASSETCORE (v3)

> **Reconciled to v3 codebase — 2026-05-07.** Wave 1 + Wave 2 đã ship; còn lại là Wave 3 (predictive + IoT) và 1 phần Wave 2 chưa làm.

**Phiên bản:** 3.0
**Owner:** PMO + Tech Lead + BA Lead
**Ngày:** 2026-05-07

---

## 1. Nguyên tắc chia Wave

1. **Vòng đời cốt lõi trước** (Asset Registry + WO Engine + Document Engine + Audit Trail).
2. **Procurement & Planning đi cùng** (Wave 2 đã được kéo lên ship cùng Wave 1 thay vì để sau).
3. **QMS từ Wave 1**: audit trail SHA-256 chain, RCA, CAPA đã chạy.
4. **Tích hợp HIS/LIS/PACS** đẩy về Wave 3 (chưa khảo sát đủ).
5. **Predictive analytics + IoT** ở Wave 3.

---

## 2. Wave 1 — Lifecycle Core (đã ship)

**Module:** IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12.

**DocType + Workflow chính:**
- `Asset Commissioning` (workflow `IMM-04 Workflow`, 11 states)
- `Asset Document` (workflow `IMM-05 Document Workflow`, 6 states) + `Document Request`, `Required Document Type`, `Expiry Alert Log`
- `PM Work Order` (workflow `IMM-08 PM Workflow`, 7 states) + `PM Schedule`, `PM Checklist Template/Item/Result`, `PM Task Log`
- `Asset Repair` (workflow `IMM-09 Repair Workflow`, 9 states) + `Repair Checklist`, `Spare Parts Used`, `Asset Transfer`
- `IMM Asset Calibration` (workflow `IMM-11 Calibration Workflow`, 8 states) + `IMM Calibration Schedule`, `IMM Calibration Measurement`
- `Incident Report` (workflow `IMM-12 Incident Workflow`, 7 states) + `IMM RCA Record` (workflow `IMM-12 RCA Workflow`) + `IMM CAPA Record` + `Asset QA Non Conformance`

**Foundation đi kèm (IMM-00):**
- `AC Asset` + workflow `AC Asset Lifecycle` (8 states)
- `Asset Lifecycle Event` (event log) + `IMM Audit Trail` (SHA-256 chain)
- 19 IMM roles + role profiles + module profiles
- `IMM SLA Policy` fixture
- 16 scheduler jobs (CAPA/contract/document/calibration/PM expiry checks, depreciation, KPI rollup, …)

**Service layer:** `assetcore/services/imm00.py` ... `imm12.py`.
**API layer:** `assetcore/api/imm00.py` ... `imm12.py` + auth, dashboard, layout, inventory, purchase.

---

## 3. Wave 2 — Procurement & Planning (đã ship)

**Module:** IMM-01, IMM-02, IMM-03.

**DocType + Workflow chính:**
- IMM-01 Needs & Plan: `IMM Needs Request` (workflow `IMM-01 Needs Workflow`, 8 states / 24 transitions), `IMM Procurement Plan` (workflow `IMM-01 Plan Workflow`, 4 states), `IMM Demand Forecast` + `Forecast Driver`, `Needs Priority Scoring`, `Procurement Plan Line`, `Budget Estimate Line`
- IMM-02 Spec & Benchmark: `IMM Tech Spec` (workflow `IMM-02 Spec Workflow`, 7 states) + `Tech Spec Requirement/Document`, `IMM Market Benchmark` + `Benchmark Candidate`, `IMM Lock-in Risk Assessment` + `Lock-in Risk Item`, `Infra Compatibility Item`, `Firmware Change Request`
- IMM-03 Vendor & Decision: `IMM AVL Entry` (workflow `IMM-03 AVL Workflow`, 5 states) + `Vendor Cert`, `IMM Vendor Evaluation` (workflow `IMM-03 Vendor Eval Workflow`, 5 states) + `Vendor Eval Candidate/Criterion`, `Vendor Quotation Line`, `IMM Supplier Audit` + `Audit Finding`, `IMM Vendor Scorecard` + `Scorecard KPI Row`, `IMM Procurement Decision` (workflow `IMM-03 Decision Workflow`, 9 states)
- Procurement output: `AC Purchase` + `AC Purchase Item` + `AC Purchase Device Item` (`AC Purchase` validate hook bắt buộc link về `IMM Procurement Decision`)
- Stock: `AC Stock Movement` (+ `AC Stock Movement Item`) — auto mark purchase received qua `services/purchase.py`

**Service layer:** `assetcore/services/imm01.py`, `imm02.py`, `imm03.py`.
**Scheduler:** check pending request overdue, budget envelope alert, benchmark freshness, AVL/audit/decision overdue, monthly demand forecast, quarterly vendor scorecard.

---

## 4. Wave 2 — Phần còn lại (chưa ship)

| Module | Mô tả | Trạng thái |
|---|---|---|
| **IMM-06 Training** | Training session, attendance, link release-for-use | chưa làm |
| **IMM-07 Performance Monitoring** | Dashboard mở rộng, KPI tracking | chưa làm (KPI rollup foundation đã có ở `imm00`) |
| **IMM-10 Post-market Surveillance** | Báo cáo cảnh báo NSX, FSCA tracking | chưa làm |
| **IMM-13 Stand-down/Transfer** | (1 phần qua `Asset Transfer` + `AC Asset Lifecycle.Out of Service`) | 1 phần |
| **IMM-14 Decommission/Disposal** | Workflow multi-level + báo cáo thanh lý | (state `Decommissioned` đã có; cần workflow tách) |
| **IMM-15 Spare Parts Master** | Master + reorder logic | foundation đã có (`AC Spare Part`, `AC Spare Part Stock`); cần reorder rule |
| **IMM-16 Compliance Dashboard** | Dashboard tổng hợp tuân thủ | chưa làm |

---

## 5. Wave 3 — Optimization, Predictive & Federation

**Module:** IMM-17 + integrations.

**Phạm vi:**
- IMM-17 Predictive analytics — failure prediction, optimal PM frequency.
- IoT telemetry ingest (MQTT/HTTP) cho thiết bị có cảm biến.
- HIS/LIS/PACS integration (read-only) qua FHIR — chưa khảo sát đủ trong Wave 1/2.
- Multi-site federation (mạng bệnh viện).
- AI-assisted root cause cho CM (gợi ý nguyên nhân + spare).

**Mốc:** chưa lock — phụ thuộc Wave 1/2 hypercare.

---

## 6. Bản đồ phụ thuộc (đã ship)

```
WAVE 1 (Lifecycle Core)            WAVE 2 (Procurement & Planning)
─────────────────────────          ─────────────────────────────────
Asset Lifecycle Event              IMM-01 Needs Request
IMM Audit Trail (SHA-256)               │
   │                                   ▼
   ▼                              IMM-01 Procurement Plan
AC Asset                               │
   │                                   ▼
   ▼                              IMM-02 Tech Spec
IMM-04 Asset Commissioning             │
   │                                   ▼
   ▼                              IMM-02 Market Benchmark + Lock-in Risk
IMM-05 Asset Document                  │
   │                                   ▼
   ▼                              IMM-03 AVL → Vendor Evaluation
PM Work Order  ◄── IMM-08              │
   │                                   ▼
   ▼                              IMM-03 Procurement Decision
Asset Repair  ◄── IMM-09               │
   │                                   ▼
   ▼                              AC Purchase ─► AC Stock Movement
IMM Asset Calibration ◄── IMM-11
   │
   ▼
Incident Report ─► IMM RCA Record ─► IMM CAPA Record ◄── IMM-12

WAVE 2 PHẦN CÒN LẠI (chưa ship)
─────────────────────────────────
IMM-06 Training, IMM-07 Performance, IMM-10 Post-market,
IMM-13 Stand-down, IMM-14 Decommission, IMM-15 Spare master,
IMM-16 Compliance dashboard

WAVE 3 (Predict & Federate)
─────────────────────────────────
IMM-17 Predictive · IoT real-time · FHIR integration · Multi-site
```

---

## 7. Tiêu chí ra Wave (Wave Exit Criteria)

| Wave | Tiêu chí thoát | Trạng thái |
|---|---|---|
| Wave 1 | UAT pass 100% Golden Scenarios IMM-04/05/08/09/11/12; audit trail chain hợp lệ; PM compliance ≥ 80%; downtime baseline 4 tuần | đã đạt (UAT scripts: `assetcore/scripts/uat/uat_imm*.py`) |
| Wave 2 (đã ship) | UAT IMM-01/02/03; tích hợp Needs → Plan → Spec → Vendor → Decision → AC Purchase → AC Stock Movement chạy đầu-cuối; quarterly Vendor Scorecard chạy | đã đạt |
| Wave 2 (còn lại) | IMM-06/07/10/13/14/15/16 | pending |
| Wave 3 | Predictive deploy ≥ 1 model với accuracy baseline; FHIR integration ổn định 30 ngày; multi-site rollout 1 cơ sở | pending |

---

## 8. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Sponsor |  |  |
| PMO |  |  |
| Tech Lead |  | 2026-05-07 |
| BA Lead |  | 2026-05-07 |
| QMS Officer |  | 2026-05-07 |
