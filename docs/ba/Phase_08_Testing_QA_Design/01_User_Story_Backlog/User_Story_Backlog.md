> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# USER STORY BACKLOG — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** BA Lead + PMO

---

## Quy ước
- Format: `As <actor>, I want <goal>, so that <benefit>`.
- Mỗi story có ID `US-XXX`, module IMM, priority, estimate (Fibonacci 1/2/3/5/8/13).
- Acceptance criteria chi tiết tại `02_Acceptance_Criteria_Catalog`.

---

## A. Asset Registry & Lifecycle

| ID | Story | Module | Priority | Est |
|----|-------|--------|----------|-----|
| US-001 | As Asset Manager, I want to register a new medical asset (auto from PR or manual) so that I have a single record per device | IMM-04 | Must | 8 |
| US-002 | As BME Engineer, I want to issue QR/RFID identifier so that the device is scannable on-site | IMM-04 | Must | 5 |
| US-003 | As QMS Officer, I want to commission an asset (after IQ/OQ/PQ pass) | IMM-04 | Must | 5 |
| US-004 | As Asset Manager + QMS, I want to release-for-use an asset only when license, training, IQ/OQ/PQ are in place | IMM-04/05/06 | Must | 5 |
| US-005 | As Legal Officer, I want to upload license + track expiry | IMM-05 | Must | 5 |
| US-006 | As Asset Manager, I want to stand-down an asset with reason and resume later | IMM-13 | Must | 5 |
| US-007 | As Auditor, I want to view full lifecycle timeline of any asset | cross | Must | 3 |
| US-008 | As Asset Manager, I want to move an asset between departments with multi-level approval | IMM-13 | Should | 5 |
| US-009 | As Department Head, I want to see assets in my department + alerts | cross | Must | 3 |
| US-010 | As Migration Lead, I want to import assets from legacy Excel | – | Must | 13 |

## B. PM (IMM-08)

| ID | Story | Pri | Est |
|----|-------|-----|-----|
| US-021 | As BME Engineer, I want to create a PM Plan with frequency + tasks template | Must | 5 |
| US-022 | As System, I want to auto-generate WO PM ahead of due date | Must | 5 |
| US-023 | As Technician (mobile), I want to scan QR + execute PM checklist + submit | Must | 8 |
| US-024 | As QMS Officer, I want to validate PM completed for QMS-critical | Must | 3 |
| US-025 | As Asset Manager, I want to see PM Compliance Rate dashboard with drill-down | Must | 5 |

## C. CM / Failure (IMM-09/12)

| ID | Story | Pri | Est |
|----|-------|-----|-----|
| US-031 | As Clinical User, I want to scan QR and submit a failure report (mobile) | Must | 8 |
| US-032 | As System, I want to auto-create a CM WO and assign per rules | Must | 5 |
| US-033 | As BME Engineer + Technician, I want to triage and execute repair | Must | 5 |
| US-034 | As Spare Warehouse Officer, I want to issue spare parts linked to WO | Must | 5 |
| US-035 | As BME Engineer, I want to record root cause when severity ≥ High | Must | 3 |
| US-036 | As System, I want to detect recurring failures (≥3/90d) and auto-open CAPA | Must | 5 |
| US-037 | As Asset Manager, I want to track downtime accurately | Must | 3 |
| US-038 | As System, I want to escalate Critical CM WO if not assigned in 30 min | Must | 3 |

## D. Calibration (IMM-11)

| ID | Story | Pri | Est |
|----|-------|-----|-----|
| US-041 | As BME Engineer, I want to create Calibration Plan | Must | 5 |
| US-042 | As System, I want to auto-generate WO Cal | Must | 3 |
| US-043 | As Cal Lab Engineer, I want to record measurements + issue cert | Must | 5 |
| US-044 | As QMS Officer, I want to approve Cal Pass and stand-down on Fail | Must | 3 |

## E. QMS / CAPA / Compliance

| ID | Story | Pri | Est |
|----|-------|-----|-----|
| US-051 | As QMS Officer, I want to manage QMS Artifact 4 tier | Must | 8 |
| US-052 | As QMS Officer, I want to open NC and convert to CAPA | Must | 5 |
| US-053 | As QMS Officer, I want to manage CAPA action plan + effectiveness check | Must | 8 |
| US-054 | As QMS Lead, I want to manage Compliance Cases (License Expired / PM Overdue / Recall) | Must | 8 |
| US-055 | As QMS Lead, I want to launch a Recall workflow that bulk-creates WO and tracks completion | Should | 13 |
| US-056 | As QMS Officer, I want to track training completion per artifact | Must | 5 |
| US-057 | As Risk Owner, I want to manage Risk Register with mitigation | Must | 5 |
| US-058 | As QMS + CCB, I want to manage Change Control Requests | Must | 5 |

## F. Document & Evidence

| ID | Story | Pri | Est |
|----|-------|-----|-----|
| US-061 | As Legal Officer + QMS, I want to manage documents (license, manual, cal cert) with versioning | Must | 8 |
| US-062 | As System, I want to alert on license expiring 90/60/30/15/7 days | Must | 3 |
| US-063 | As Auditor, I want to export evidence pack for an asset | Must | 5 |

## G. Dashboard & Reports

| ID | Story | Pri | Est |
|----|-------|-----|-----|
| US-071 | As Asset Manager, I want a home dashboard with KPI Wave 1 | Must | 8 |
| US-072 | As QMS Officer, I want a QMS-focused dashboard | Must | 5 |
| US-073 | As Executive, I want a high-level dashboard with drill-down | Must | 8 |
| US-074 | As Asset Manager, I want monthly snapshot and exports | Must | 5 |
| US-075 | As Auditor, I want to search audit trail | Must | 3 |

## H. Integration

| ID | Story | Pri | Est |
|----|-------|-----|-----|
| US-081 | As System, I want to sync AC Medical Asset ↔ ERPNext Asset bidirectionally | Must | 8 |
| US-082 | As System, I want to consume PR.on_submit to auto-create AC Medical Asset draft | Must | 5 |
| US-083 | As Partner, I want to subscribe webhook for selected events (HMAC-signed) | Should | 5 |
| US-084 | As System, I want to provide REST API for asset profile + timeline | Must | 5 |

## I. Mobile

| ID | Story | Pri | Est |
|----|-------|-----|-----|
| US-091 | As Technician (mobile), I want offline mode for FR + WO complete | Must | 13 |
| US-092 | As Mobile user, I want biometric login | Should | 5 |
| US-093 | As Mobile user, I want push notifications for assigned WO | Must | 5 |

## J. Admin / Security / Migration

| ID | Story | Pri | Est |
|----|-------|-----|-----|
| US-101 | As System Admin, I want a system health dashboard | Must | 5 |
| US-102 | As System Admin, I want to manage user / role / permission | Must | 3 |
| US-103 | As Migration Lead, I want migration tool with pre-validate, dry-run, production import | Must | 13 |
| US-104 | As Auditor + Admin, I want immutable audit log + e-signature | Must | 8 |

---

## Tổng kết Wave 1
- ~ 90 stories, tổng estimate ~ 350 story points.
- Sprint 2 tuần với 50 SP/sprint → ~ 7 sprint build.
- Plus testing, training, UAT, hypercare → 14-16 tuần build phase.
