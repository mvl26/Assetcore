> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# UAT SKELETON — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** PMO + BA Lead + QA Lead

---

## 1. UAT scope
- 6 module Wave 1 (IMM-04, 05, 08, 09, 11, 12).
- 8 Golden Scenarios.
- Cross-cutting: QMS, dashboard, audit trail, mobile, integration ERPNext, migration.

## 2. UAT phases

### 2.1 Pha chuẩn bị
- Setup môi trường UAT.
- Refresh anonymized snapshot từ PROD baseline + migration sample.
- Cấp tài khoản + role + training nhanh cho UAT participants.
- Phát hành UAT Test Charter.

### 2.2 UAT Sprint 1 — Asset Lifecycle + Document
- Module IMM-04, 05.
- Scenarios: GS-01 từng phần, GS-04, GS-08.
- Participants: Asset Manager, BME Engineer, QMS Officer, Pháp chế, BGĐ.

### 2.3 UAT Sprint 2 — PM + Calibration
- Module IMM-08, 11.
- Scenarios: GS-02, GS-05.
- Participants: BME Engineer, KTV, Vendor SE, Cal Lab Eng, QMS, Asset Manager.

### 2.4 UAT Sprint 3 — CM + Spare + CAPA + Recall
- Module IMM-09, 12.
- Scenarios: GS-03, GS-06.
- Participants: Clinical User, BME Engineer, KTV, Vendor SE, Spare Officer, QMS Lead, Pháp chế.

### 2.5 UAT Sprint 4 — End-to-end + Mobile + Migration
- GS-01 đầy đủ, GS-07.
- Mobile testing đa role (Technician, Clinical User).
- Participants: tất cả.

### 2.6 UAT Sign-off
- BGĐ + Trưởng VTTBYT + Trưởng QLCL + Trưởng CNTT.

## 3. Cấu trúc UAT script

| Field | Mô tả |
|-------|-------|
| Scenario ID | GS / TC ID |
| Step | – |
| Action | Người thực hiện |
| Expected | – |
| Actual | – |
| Result | Pass / Fail / Blocked |
| Issue link | – |
| Tester signature | – |

## 4. Defect management

- Severity:
  - Critical: block go-live.
  - High: block GS pass.
  - Medium: workaround có.
  - Low: cosmetic.
- SLA:
  - Critical: fix 24h.
  - High: 5 ngày.
  - Medium/Low: theo backlog.

- Re-test sau fix.

## 5. UAT environment
- UAT site cấu hình giống PROD ngoại trừ data anonymized.
- Mobile devices thực: 3 Android + 2 iOS phổ biến tại BV.
- Vendor SE account thật (test mode).

## 6. Training trước UAT
- Mini training 2h cho mỗi role chính.
- Cheat sheet 1 trang in giấy.
- Helpdesk inbox cho UAT participants.

## 7. Daily UAT review
- Standup 15' mỗi ngày (PMO + BA + QA + Lead participants).
- Burn-down chart UAT scenarios pass/fail.

## 8. Tiêu chí Pass UAT (gate go-live)

| Tiêu chí | Ngưỡng |
|----------|--------|
| GS pass rate | 100% Critical + ≥ 90% Major |
| Defect Critical open | 0 |
| Defect High open | ≤ 3 (có workaround) |
| KPI dashboard real | có dữ liệu 4 tuần |
| Migration in scope | ≥ 95% |
| Mobile UX feedback | ≥ 4/5 |
| Sign-off từ 4 trưởng phòng + BGĐ | có |

## 9. Hypercare follow-up
- 4 tuần sau go-live.
- Daily standup 30'.
- On-call team.
- Track adoption rate (MET-W1-015).

## 10. Tiêu chí nghiệm thu UAT skeleton
- 8 GS có UAT script chi tiết.
- Defect log + re-test workflow.
- Sign-off matrix lock.
- Hypercare plan attached.
