> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DEVOPS PLAN — ASSETCORE

**Phiên bản:** 1.0
**Owner:** DevOps Lead + Tech Lead

---

## 1. Repository
- Mono-repo `assetcore` (custom Frappe app).
- Branching:
  - `main`: production-ready.
  - `develop`: integration.
  - `feature/<wave>-<module>-<short>`.
  - `hotfix/<ticket>`.
  - `release/<wave>-x.y.z`.
- Tag: `v1.0.0` Wave 1 GA.

## 2. CI Pipeline (mỗi PR)

```yaml
stages:
  - lint
  - unit-test
  - integration-test
  - security-scan
  - build
```

- Lint: `flake8`, `black`, `isort`, frappe app linter.
- Unit test: `pytest` với coverage ≥ 70%.
- Integration test: pytest-frappe.
- Security: Trivy (container), Dependabot, TruffleHog.
- Build: docker image (nếu container) hoặc bench package.

## 3. CD Pipeline

```
Merge to develop ──► Auto deploy DEV
                        │
                        ▼
              Smoke test pass
                        │
                        ▼
              Manual approval ──► Deploy UAT
                        │
                        ▼
              Wave UAT pass + sign-off
                        │
                        ▼
              Manual approval ──► Deploy STAGING
                        │
                        ▼
              Cutover rehearsal pass
                        │
                        ▼
              CCB approval ──► Deploy PROD
                        │
                        ▼
              Smoke test PROD + monitor
```

## 4. Code review
- Mỗi PR cần ≥ 1 reviewer (≥ 2 cho PR đụng QMS-critical).
- Checklist:
  - DocType change → ADR / CR khi cần.
  - Permission change → security review.
  - Migration script → idempotent.
  - Tests added.
  - Documentation updated.

## 5. Versioning
- Semver: MAJOR.MINOR.PATCH.
- Wave 1 GA = `v1.0.0`.
- Hotfix tăng PATCH.
- Tính năng tăng MINOR.

## 6. Release management
- Release notes (CHANGELOG.md).
- Migration scripts versioned.
- Rollback plan cho mỗi release.
- Schedule: PROD release window weekend.

## 7. Configuration management
- `.env` không commit.
- Vault cho PROD/STAGING secrets.
- Frappe site_config.json templated.

## 8. Quality gates
- Coverage ≥ 70% Wave 1 (≥ 80% Wave 2).
- 0 high/critical lint warning.
- 0 failing tests on `develop`.
- Security scan pass.

## 9. Issue tracking
- Tool: GitHub Issues / Jira.
- Mỗi PR link issue.
- Sprint board tracking.

## 10. Documentation
- README per module.
- API docs auto-generated từ OpenAPI.
- ADR ở `docs/adr/`.
- Onboarding doc cho dev mới.

## 11. Backup & Restore drill
- Quý.
- Verify hash chain audit log post-restore.

## 12. DR drill
- Quý.
- Failover to DR site test.

## 13. Hotfix workflow
- Branch `hotfix/<ticket>` từ main.
- Fast-track review.
- CR cho CCB nếu critical.
- Cherry-pick to develop.

## 14. Tooling stack
- Source: GitHub / GitLab.
- CI/CD: GitHub Actions / GitLab CI / Jenkins.
- Artifact: container registry / package store.
- Monitoring: Prometheus + Grafana.
- Logs: Loki / ELK.
- Secret: Vault.
- IaC: Ansible / Terraform (cho Nginx/Linux).

## 15. Tiêu chí nghiệm thu DevOps Plan
- Pipeline CI/CD chạy thông suốt.
- Coverage gate enforced.
- Deploy DEV → UAT → STAGING → PROD test pass.
- Rollback drill thành công.
- Documentation đầy đủ.
