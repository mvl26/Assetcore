> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# SPRINT BACKLOG — WAVE 1

**Phiên bản:** 1.0
**Owner:** PMO + Tech Lead
**Sprint length:** 2 tuần. Velocity giả định: 50 SP/sprint với team 4-6 dev + 1 QA + 1 BA.

---

## 1. Tổng quan
- ~ 90 user stories Wave 1, ~ 350 SP.
- 7 sprint build + 2 sprint UAT/cutover + hypercare.
- Buffer 10% trên mỗi sprint.

## 2. Sprint Plan

### Sprint 1 — Foundation (50 SP)
- US-001 Tạo MA manual (8)
- US-002 Identifier QR/RFID (5)
- US-010 Migration tool foundation (13)
- US-082 PR.on_submit hook (5)
- US-101 Admin dashboard skeleton (5)
- US-102 Role + permission setup (3)
- US-104 Audit trail engine + e-sig (8)
- (Buffer 3)

**DoD:** ERD lock, DocType core created, naming series, permission baseline, e-sig wired.

### Sprint 2 — Document Engine + License (50 SP)
- US-005 License upload + state machine (5)
- US-061 Document versioning + supersede (8)
- US-051 QMS Artifact 4 tier core (8)
- US-062 License expiry alert cron (3)
- US-063 Export evidence pack (5)
- US-007 Asset timeline view (3)
- US-091 Mobile FR offline foundation (13)
- (Buffer 5)

**DoD:** Document Layer + QMS Layer đầy đủ chu trình; mobile shell sẵn.

### Sprint 3 — Asset Lifecycle Complete (50 SP)
- US-003 Commission (5)
- US-004 Release for use (5)
- US-006 Stand-down + resume (5)
- US-008 Asset Movement (5)
- US-081 MA ↔ ERPNext Asset sync (8)
- US-007 Audit timeline drill-down (3)
- US-009 Department Head dashboard (3)
- US-022 PM Scheduler cron (5)
- US-021 PM Plan create (5)
- (Buffer 6)

**DoD:** State machine MA hoàn chỉnh; PM scheduler chạy; sync ERPNext.

### Sprint 4 — PM Execution + KPI (50 SP)
- US-023 Mobile PM execution (8)
- US-024 QMS validate WO (3)
- US-025 PM Compliance Dashboard (5)
- US-071 Asset Manager Home Dashboard (8)
- US-072 QMS Officer Home Dashboard (5)
- US-073 Executive Dashboard (8)
- US-074 KPI snapshot monthly (5)
- US-075 Audit search (3)
- (Buffer 5)

**DoD:** PM end-to-end mobile + dashboard, KPI Wave 1 25 metrics.

### Sprint 5 — CM + Failure + CAPA (50 SP)
- US-031 Mobile FR submit (8)
- US-032 Auto-create CM WO (5)
- US-033 Triage + execute repair (5)
- US-034 Spare consumption WO (5)
- US-035 Root cause field (3)
- US-036 Recurring failure → CAPA (5)
- US-037 Downtime tracking (3)
- US-038 SLA escalation (3)
- US-052 NC + CAPA core (5)
- (Buffer 8)

**DoD:** CM E2E + CAPA chu trình + SLA monitor.

### Sprint 6 — Calibration + CAPA Effectiveness (50 SP)
- US-041 Calibration Plan (5)
- US-042 Auto-WO Cal (3)
- US-043 Cal Record + cert (5)
- US-044 Cal Pass/Fail workflow (3)
- US-053 CAPA effectiveness check (8)
- US-054 Compliance Case (8)
- US-056 Training tracker (5)
- US-057 Risk Register (5)
- US-058 Change Control (5)
- (Buffer 3)

**DoD:** Calibration full + CAPA effectiveness + Compliance Case + Risk + Change Control.

### Sprint 7 — Recall + Mobile + Hardening (50 SP)
- US-055 Recall workflow + bulk WO (13)
- US-083 Webhook outbound (5)
- US-084 REST API + OpenAPI (5)
- US-092 Biometric login (5)
- US-093 Push notification (5)
- US-103 Migration tool production (13)
- (Buffer 4)

**DoD:** Recall workflow + integration outbound + migration tool đầy đủ.

### Sprint 8 — UAT Sprint + Bug fix (mix)
- UAT scenarios test theo Phase_08/05_UAT_Skeleton.
- Bug fix Critical/High.

### Sprint 9 — UAT + Performance + Security
- Performance test pass.
- Pen-test pass.
- Final UAT sign-off.

### Sprint 10 — Cutover + Hypercare
- Migration production.
- Go-live.
- Hypercare 4 tuần (vào cycle này).

## 3. Theo dõi tiến độ
- Burn-down chart per sprint.
- Velocity tracker.
- Story-level estimation review tại Planning.
- Daily standup.
- Sprint review + retro.

## 4. Risk per sprint
- Sprint 1-3 phụ thuộc data migration mockup → block test → mitigation: synthetic dataset.
- Sprint 4-5 phụ thuộc UI/UX feedback nhanh.
- Sprint 7 risk lớn nhất: integration + migration đồng thời.

## 5. Tiêu chí nghiệm thu Sprint Backlog
- Lock 7 sprint build.
- 100% story có acceptance criteria + estimate.
- Velocity ≤ 110% capacity.
- Buffer 10% sprint.
