> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# INTEGRATION TEST HARNESS PLAN — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + QA

---

## 1. Mục tiêu
Bộ test harness chạy được tự động + manual cho mọi integration Wave 1 + chuẩn bị Wave 2.

## 2. Phạm vi Wave 1

| Integration | Test loại |
|-------------|-----------|
| ERPNext core | Unit + integration |
| SSO | E2E auth flow |
| Email gateway | Unit (template render) + integration (Mailpit) |
| SMS gateway (W1.5) | Mock test + 1 lần real test |
| Migration tool | Unit + dry-run + production-like UAT |
| Outbox dispatcher | Integration + chaos test |
| Inbound webhook framework | Integration |

## 3. Test Tools

| Loại | Tool |
|------|------|
| API contract | Prism (OpenAPI mock), Schemathesis |
| HTTP testing | Postman/Newman, k6 |
| FHIR validation | HAPI FHIR Validator |
| Webhook testing | Mockbin, RequestBin (DEV) |
| Email | Mailpit / MailHog |
| Performance | k6 / Locust |
| Security | OWASP ZAP, Trivy |
| Chaos | toxiproxy (giả lập timeout/lag) |

## 4. Test Suites

### 4.1 ERPNext core hooks
- Test `Purchase Receipt on_submit` → tạo MA draft.
- Test `Stock Entry on_submit` linked WO → cập nhật cost.
- Test sync MA ↔ Asset 2 chiều (location, custodian).
- Test reconciliation cron daily.

### 4.2 OAuth2 / SSO
- Login flow internal user.
- Login flow external vendor.
- Token refresh.
- Token revoke.
- Scope enforcement.

### 4.3 Email Notification
- Render template với context.
- Send via Mailpit; verify content.
- Quiet hours respected.
- Dedupe key works.

### 4.4 Outbound Webhook
- Subscribe + dispatcher delivers.
- HMAC sign verify.
- Retry on 5xx; success on retry.
- Dead-letter after 3 fails.
- Replay manual.
- Idempotency from subscriber side (using event_id).

### 4.5 Inbound Webhook
- Valid HMAC accepted.
- Invalid HMAC rejected.
- Timestamp lệch > 5p rejected.
- Schema invalid → 422.
- Domain handler dispatches correctly.

### 4.6 Migration tool
- Pre-validate report sạch.
- Dry-run DEV.
- Production-like UAT.
- Rollback test.

### 4.7 SLA monitor
- WO breach SLA tested với mock time.
- Pause window respected.
- Escalation chain test.

### 4.8 Performance
- k6 scenario:
  - 200 concurrent users browsing list views.
  - 1000 webhook outbound/phút.
  - 5000 lifecycle event ingest/phút.
- Target: NFR-P-* met.

### 4.9 Security
- OWASP Top 10 scan.
- Pen-test trước go-live.
- API fuzz test (Schemathesis).

### 4.10 Chaos Engineering
- Tắt Redis 5 phút → graceful degradation.
- Tắt outbound webhook target → outbox accumulate, không mất event.
- DB primary lock → failover to replica (DR).

## 5. Test data

- Synthetic dataset cho DEV.
- Anonymized snapshot cho UAT.
- Fixtures cho automated test (5-10 asset, 20 WO, 10 document).

## 6. CI/CD integration

- Unit + integration test chạy mỗi PR.
- E2E nightly trên DEV.
- Performance test weekly trên STAGING.
- Security scan weekly.

## 7. Reporting
- Test report tự động sau mỗi run (GitHub Actions / Jenkins).
- Coverage report bằng pytest-cov.
- Dashboard QA: pass rate, flaky tests, performance trend.

## 8. Acceptance criteria
- Unit test coverage ≥ 70% Wave 1.
- Integration test pass rate 100%.
- Performance NFR met.
- Pen-test 0 high/critical open.
- Chaos test pass cho 3 scenario.
