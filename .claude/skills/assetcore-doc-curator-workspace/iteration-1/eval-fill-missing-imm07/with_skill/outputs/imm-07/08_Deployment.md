# 08 — Triển khai & Tuân thủ (Deployment & QMS)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Deploy plan + QMS mapping |
| Owner | DevOps + QMS Risk |
| Liên kết | [04 Backend](./04_Backend_Design.md) · [09 Release](./09_Release.md) |

---

# Phần I — Deployment Plan

## I.1. Pre-deployment checklist

- [ ] BE coverage ≥ 85% service.
- [ ] FE build pass.
- [ ] IMM-04, 08, 09, 11 đã deploy ổn định ≥ 30 ngày trên site đích.
- [ ] Fixture KPI definition + threshold default đã review.
- [ ] Cron schedule đã thống nhất với DevOps (02:00 đêm không trùng job khác).

## I.2. Stack & versioning

- Frappe v15, ERPNext v15, Python 3.11+, MariaDB 10.6+.
- AssetCore version mục tiêu cho IMM-07 release: `v3.x.0` (Wave 3).

## I.2b. Cấu hình môi trường thực nghiệm (Environment configuration)

| Env | Frappe Site | Cron enabled | Notes |
|---|---|---|---|
| Dev | `dev.assetcore.local` | No (chạy thủ công) | Seed 100 asset test |
| Staging | `staging.assetcore.<bv>.vn` | Yes | Mirror prod data |
| Production | `<bv>.assetcore.vn` | Yes | Backup trước deploy |

Variable cần set:
- `imm07_compute_window_hours` = 24 (default)
- `imm07_replacement_check_enabled` = 1
- `imm07_audit_chain_verify_cron` = `0 5 * * 0`

## I.3. Deployment artefacts

- App: `assetcore` v3.x.
- Fixture: `assetcore/fixtures/imm07_kpi_definitions.json`, `imm07_replacement_thresholds.json` *(Sprint Wave 3)*.
- Patch: `v3_x/seed_imm07_kpi_definitions.py`.
- Workflow JSON: `assetcore/workflow/imm_07_replacement_signal_workflow.json`, `imm_07_threshold_approval_workflow.json`.

## I.4. Deploy sequence

1. `bench --site <site> backup`.
2. `git pull` + `bench setup requirements`.
3. `bench --site <site> migrate`.
4. `bench --site <site> install-app assetcore` (nếu site mới).
5. Import fixture: `bench --site <site> import-fixture --app assetcore`.
6. `bench restart`.
7. Smoke test (xem I.6).

## I.5. Schema migration risk

| Risk | Mitigation |
|---|---|
| Tạo bảng `tab IMM Performance Metric` lớn → khoá DDL lâu | Migrate vào off-peak; pre-create index sau |
| Patch seed KPI conflict với data manual | Patch idempotent, check exists trước insert |

## I.6. Smoke test sau deploy

- API `/cockpit_summary` trả `{success: true}`.
- Cron compute_metrics chạy thử với `--dry-run` 1 asset.
- Workflow Replacement Signal hiện đầy đủ state trong DocPerm.

## I.7. Rollback plan

1. `bench --site <site> restore <backup>`.
2. `git checkout <previous-tag>`.
3. `bench restart`.
Threshold rollback: re-import fixture cũ.

## I.8. Communication

- Pre: thông báo Trưởng phòng + WS Lead 3 ngày.
- Maintenance window: ≤ 2h, off-peak (đêm).
- Post: gửi email summary + link cockpit.

## I.9. Monitoring & alerting (T+24h)

- Watch scheduler log cron 02:00.
- Watch error log cho `IMM07_*` codes.
- Verify hash chain manual ngày đầu.

## I.10. Post-deployment

- Day 1: spot check cockpit với QA.
- Day 7: review số signal sinh ra (kỳ vọng < 5% asset).
- Day 30: retrospective + tune threshold.

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu trúc QMS reference

Theo Architecture line 342–346 — IMMIS-07 có:

- QC nền: `QC-IMMIS-03` (chính sách vận hành, bảo trì, tuân thủ, dữ liệu).
- PR/SOP: `PR-IMMIS-07-01..03`.
- WI: `WI-IMMIS-07-01..04`.
- BM: `BM-IMMIS-07-01`.
- HS: `HS-LOG-IMMIS-07-01; HS-REC-IMMIS-07-01; HS-REP-IMMIS-07-01`.
- KPI-DASH: `KPI-DASH-IMMIS-07`.

## II.2. Trace yêu cầu pháp lý

| Yêu cầu | Nguồn | Implement ở | Bằng chứng |
|---|---|---|---|
| Lưu hồ sơ vận hành ≥ 5 năm | NĐ98/2021 | DocType `IMM Performance Metric` retention | Backup + archive policy |
| Drill-down về record nguồn | WHO HTM | API `drill_down` | Test UAT-IMM07-02 |
| Audit hash chain | Nội bộ + WHO HTM | Service `verify_chain` | UT-IMM07-S-06/07 |
| Phân tách trách nhiệm | ISO 13485 | RBAC matrix III.1 | Workflow maker/checker |

## II.3. QMS artefact tạo bởi module

| Loại | Mã | Sinh khi |
|---|---|---|
| HS-LOG | `HS-LOG-IMMIS-07-01` | Mỗi cron run |
| HS-REC | `HS-REC-IMMIS-07-01` | Mỗi snapshot |
| HS-REP | `HS-REP-IMMIS-07-01` | Mỗi báo cáo BYT export |

## II.4. Document control

KPI Definition + Threshold là controlled documents — workflow Effective/Obsolete + version.

## II.5. Traceability compliance → code

| QMS doc | Code reference |
|---|---|
| `PR-IMMIS-07-01` Compute KPI | `assetcore/services/imm07.py:compute_metrics` |
| `PR-IMMIS-07-02` Verify chain | `assetcore/services/imm07.py:verify_chain` |
| `PR-IMMIS-07-03` Replacement signal | `assetcore/services/imm07.py:transition_signal` |
| `WI-IMMIS-07-01..04` | User guide [09 §I](./09_Release.md) |

## II.6. Audit / inspection readiness

- Hash chain verifiable on-demand qua API.
- Snapshot immutable (BR-01).
- Export báo cáo PDF kèm hash header.

## II.7. Training & roll-out

- Trưởng phòng + WS Lead: 2 giờ training (cockpit + signal workflow).
- KTV + Khoa LS: 30 phút (drill-down + data quality ticket).
- QMS Risk: 1 giờ (verify chain + audit export).

## II.8. Risk register (compliance)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Số liệu KPI sai dùng cho báo cáo BYT | Trung bình | Cao | Hash chain + verify cron + hold report nếu chain fail |
| Threshold thay đổi không qua approval | Thấp | Cao | Workflow maker/checker enforced |

## II.9. Sign-off

- [ ] BA Lead
- [ ] Tech Lead
- [ ] DevOps
- [ ] QMS Risk Officer
- [ ] Trưởng phòng VT-TBYT (đại diện end-user)
