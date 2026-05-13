> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# TEST CASE LIBRARY — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QA Lead

---

## 1. Phân loại test

| Loại | Mục đích |
|------|---------|
| Unit | Logic Python module / hooks |
| Integration | Hooks giữa engine + API |
| E2E (UI) | Flow qua Frappe Desk + Mobile |
| Workflow | State transitions |
| Permission | Role + User Permission |
| Performance | NFR-P-* |
| Security | Auth, AuthZ, audit, e-sign |
| Migration | DQ + dry-run |

## 2. Cấu trúc test case

| Field | Mô tả |
|-------|-------|
| TC ID | `TC-XXX-YYY` |
| Module | IMM module |
| Linked story / criterion | – |
| Type | Unit/Integration/E2E… |
| Pre-conditions | – |
| Steps | – |
| Expected | – |
| Negative cases | – |
| Severity if fail | Critical/High/Medium/Low |
| Automation tag | Yes/No |

## 3. Mẫu Test Cases (chọn lọc Wave 1)

### TC-MA-001 (Unit)
- Story: US-001
- Steps: tạo MA với asset_code không hợp lệ.
- Expected: ASSETCORE_VALIDATION_FAILED.

### TC-MA-002 (Integration)
- Story: US-001 Scenario 2.
- Steps: submit Purchase Receipt với item is_medical_device=1, qty=2, no serial.
- Expected: 2 MA draft created, basic fields prefilled, LE chưa publish.

### TC-MA-003 (Workflow)
- Story: US-003 Scenario 1.
- Pre: asset state=installed, IQ/OQ/PQ approved.
- Steps: QMS Officer commission with e-sign.
- Expected: state=commissioned, LE-04 published, signature record.

### TC-MA-004 (Permission)
- Story: US-001 Scenario 4.
- Pre: user role=AC Clinical User.
- Steps: attempt POST /assets.
- Expected: 403.

### TC-WO-001 (Workflow)
- Story: US-022.
- Pre: PM Plan effective, next_due tomorrow + 14d.
- Steps: trigger PM Scheduler cron.
- Expected: WO PM planned, alert sent.

### TC-WO-002 (E2E mobile)
- Story: US-023.
- Pre: WO PM assigned to Technician.
- Steps: scan QR → start → tick task → submit.
- Expected: state=completed, evidence attached, LE-46 published.

### TC-WO-003 (Negative)
- Story: US-023.
- Steps: scan wrong asset (different from WO).
- Expected: warning "Asset không khớp WO", block start.

### TC-FR-001 (Mobile + Integration)
- Story: US-031 Scenario 1.
- Steps: Clinical User mobile scan QR → submit FR Critical.
- Expected: FR + WO CM created, SLA timer started, SMS to KS BME.

### TC-FR-002 (Auto-merge)
- Story: US-031 Scenario 2.
- Pre: FR existing on same asset within 60 min.
- Steps: submit duplicate FR.
- Expected: new FR state=merged, links to existing.

### TC-CM-001 (Recurring CAPA)
- Story: US-036.
- Pre: 2 WO CM closed within 90d on asset X.
- Steps: close 3rd WO CM.
- Expected: CAPA auto-opened, owner = QMS Officer.

### TC-CAL-001 (Cal Pass)
- Story: US-043 Scenario 1.
- Steps: Cal Lab enters measurements + cert.
- Expected: state=approved, asset.next_calibration_due updated, LE-08.

### TC-CAL-002 (Cal Fail)
- Story: US-043 Scenario 2.
- Expected: asset auto-stand-down, CAPA opened, alert sent.

### TC-DOC-001 (License lifecycle)
- Story: US-005.
- Steps: upload license, review, approve, effective.
- Expected: state transitions correct, LE-05 published, expiry alert configured.

### TC-DOC-002 (License expiry alert)
- Story: US-062.
- Pre: license expiry = T + 30d.
- Steps: cron run at T.
- Expected: NTF-015 sent.

### TC-CAPA-001 (Effectiveness)
- Story: US-053.
- Steps: actions closed, effectiveness check at 30/60/90d, all pass.
- Expected: CAPA closed at 90d, LE-25.

### TC-RECALL-001 (Bulk recall)
- Story: US-055.
- Steps: open Compliance Case Recall, identify scope (model X), bulk create WO.
- Expected: 1 WO/asset, disclosure timer set, NTF-047 sent.

### TC-AUDIT-001 (Immutability)
- Story: US-104.
- Steps: attempt UPDATE Lifecycle Event.
- Expected: rejected by trigger.

### TC-PERM-001 (Vendor scope)
- Pre: vendor account, scoped to WO-... assigned.
- Steps: vendor list assets.
- Expected: chỉ thấy assets trong scope WO assigned.

### TC-INT-001 (ERPNext sync)
- Story: US-081.
- Steps: change MA location, run sync job.
- Expected: ERPNext Asset.location updated within 5 min.

### TC-PERF-001 (List view)
- NFR: NFR-P-01.
- Pre: 5k MA records.
- Steps: open list view, apply filter.
- Expected: p95 ≤ 1.5s.

### TC-SEC-001 (Pen-test)
- Steps: run OWASP ZAP scan.
- Expected: 0 high/critical open.

### TC-MIG-001 (Dry-run)
- Steps: run migration on DEV with sample 5k assets.
- Expected: > 95% success, < 5% warning, 0 error in scope.

(Tổng dự kiến ~ 250-300 test case Wave 1.)

## 4. Tự động hóa

- Unit / Integration: pytest + Frappe testing framework.
- E2E desktop: Cypress / Playwright.
- E2E mobile: Detox / Appium.
- API contract: Schemathesis.
- Performance: k6.
- Security: OWASP ZAP.

## 5. Coverage target Wave 1
- Unit: ≥ 70% coverage.
- Integration: 100% engine API.
- E2E: cover top 30 flows (MA lifecycle, WO PM/CM/Cal, Doc, CAPA, Recall, Mobile FR, Validate).
- Performance: NFR-P-* met.
- Security: pen-test pass.

## 6. Test data fixtures
- 50 device models, 200 assets, 50 documents, 100 WO history (PM/CM/Cal mix), 20 CAPA, 5 Compliance Cases, 1 Recall scenario.

## 7. Tiêu chí nghiệm thu
- 250+ TC documented.
- 70% automated.
- Pass rate 100% trên CI nightly.
- Manual exploratory test cho mobile.
