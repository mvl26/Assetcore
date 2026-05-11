# 08 — Deployment & QMS Mapping

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Per-module |
| Owner | DevOps + QMS Officer |
| Liên kết | 04 Backend · 07 Testing · 09 Release |

---

# Phần I — Deployment Plan

## I.1. Pre-deployment checklist

- [ ] Test coverage gate pass (file 07 §IV.2)
- [ ] CI pipeline green (lint + test + build)
- [ ] DocType JSON committed: `AC KPI Snapshot`, `AC Replacement Signal`, `AC KPI Threshold Config`
- [ ] Workflow JSON committed: `assetcore/workflow/imm_07_replacement_signal_workflow.json`
- [ ] Patch committed: `assetcore/patches/v1/00x_create_imm07_doctypes.py`, `00x_seed_threshold_config.py`
- [ ] `patches.txt` đăng ký patch
- [ ] Fixtures export: role IMM07 User/Manager, threshold config seed
- [ ] `hooks.py` cập nhật `scheduler_events`
- [ ] Docs README + 02–09 review xong
- [ ] BA sign-off ngưỡng KPI

## I.2. Deployment order

```
1. Backup site (bench --site <s> backup --with-files)
2. git pull + bench update --no-backup --reset
3. bench --site <s> migrate           # chạy patch
4. bench --site <s> install-app assetcore  # nếu lần đầu
5. bench --site <s> import-fixtures
6. bench build --app assetcore
7. bench --site <s> clear-cache
8. supervisorctl restart all
9. Smoke test (§I.5)
```

## I.3. Environment matrix

| Env | Site | DB | Mục đích |
|---|---|---|---|
| Dev | `dev.assetcore.local` | local MariaDB | Dev daily |
| Staging | `staging.assetcore.miyano.vn` | dedicated MariaDB | UAT + integration test |
| Production | `<bv>.assetcore.miyano.vn` | dedicated MariaDB + replica | Vận hành thật |

## I.4. Configuration

- `common_site_config.json`:
  - `scheduler_enabled: 1`
  - `background_workers: 4` (đảm bảo cron compute không nghẽn)
- Site config:
  - `imm07.compute_window_minutes: 60` (override nếu cần test)
  - `imm07.retention_hourly_days: 30`
  - `imm07.retention_daily_years: 1`

## I.5. Smoke test (post-deploy)

| Step | Expected |
|---|---|
| GET `list_kpi_snapshots` | 200 + `{success: true}` |
| Trigger compute manual `bench execute assetcore.services.imm07.compute_kpi_snapshot --kwargs '{"window":"1h"}'` | Insert ≥ 1 snapshot |
| Cron tick 1h waited | Tự động sinh snapshot |
| Verify chain 1 asset có ≥ 5 snapshot | `{valid: true}` |
| FE cockpit load | < 2s, render KPI |

## I.6. Rollback

- Backup file `<site>-<timestamp>-database.sql.gz` (giữ ≥ 7 ngày)
- Rollback step:
  1. `bench --site <s> restore <backup>`
  2. `git checkout <previous-tag>`
  3. `bench update --no-backup --reset`
  4. `supervisorctl restart all`
- Patch IMM-07 idempotent — re-run an toàn

## I.7. Monitoring

- Frappe Scheduler log → tail `logs/scheduler.log` filter `imm07`
- Custom Health Check: `bench --site <s> execute assetcore.services.imm07.check_event_source_health` chạy mỗi 30 phút
- Metrics export (roadmap): Prometheus exporter cho `imm07_compute_duration_seconds`, `imm07_snapshot_inserted_total`

---

# Phần II — QMS Mapping

> Bám `Ho_so_kien_truc_IMMIS.md` dòng 342–346 — IMM-07 thuộc nhóm tài liệu QMS điện tử/IMMIS/07-* và BI/IMMIS.

## II.1. Document tree (mã chuẩn)

| Loại | Mã | Tên tài liệu | Chủ sở hữu | Nơi lưu |
|---|---|---|---|---|
| QC L1 (parent) | QC-IMMIS-04 | Quản trị vận hành & bảo trì TBYT | Trưởng phòng | QMS điện tử/IMMIS/L1 |
| PR/SOP | PR-IMMIS-07-01 | Quy trình thu thập & chuẩn hóa KPI/KRI vận hành | CMMS/IMMIS, Nhóm HTM | QMS điện tử/IMMIS/07-* |
| PR/SOP | PR-IMMIS-07-02 | Quy trình xử lý replacement signal | CMMS/IMMIS, Nhóm HTM | QMS điện tử/IMMIS/07-* |
| PR/SOP | PR-IMMIS-07-03 | Quy trình verify hash chain & data quality | CNTT, Auditor | QMS điện tử/IMMIS/07-* |
| WI | WI-IMMIS-07-01 | Hướng dẫn xem cockpit & drill-down | Nhóm HTM | QMS điện tử/IMMIS/07-* |
| WI | WI-IMMIS-07-02 | Hướng dẫn acknowledge / suppress signal | Trưởng phòng | QMS điện tử/IMMIS/07-* |
| WI | WI-IMMIS-07-03 | Hướng dẫn cấu hình ngưỡng KPI | Nhóm HTM | QMS điện tử/IMMIS/07-* |
| WI | WI-IMMIS-07-04 | Hướng dẫn xuất báo cáo KPI tháng/quý | CMMS/IMMIS | QMS điện tử/IMMIS/07-* |
| BM | BM-IMMIS-07-01 | Biểu mẫu báo cáo KPI vận hành tháng | CMMS/IMMIS | QMS điện tử/IMMIS/07-* |
| HS | HS-LOG-IMMIS-07-01 | Nhật ký scheduler compute KPI | CNTT | QMS điện tử/IMMIS/07-* |
| HS | HS-REC-IMMIS-07-01 | Hồ sơ KPI snapshot (audit chain) | CMMS/IMMIS | QMS điện tử/IMMIS/07-* |
| HS | HS-REP-IMMIS-07-01 | Báo cáo KPI tháng/quý gửi lãnh đạo | Trưởng phòng | QMS điện tử/IMMIS/07-* |
| KPI-DASH | KPI-DASH-IMMIS-07 | Dashboard cockpit hiệu suất | CMMS/IMMIS, BI | BI/IMMIS |

## II.2. Compliance mapping

| Quy định | Yêu cầu | Đáp ứng IMM-07 |
|---|---|---|
| NĐ98/2021 | Lưu hồ sơ vận hành ≥ 5 năm | Snapshot retention monthly forever; audit chain |
| NĐ98/2021 | Truy xuất audit | Verify chain endpoint cho Auditor |
| WHO HTM Maintenance Programme | Đo MTBF/MTTR/Availability | KPI BR-01..04 |
| WHO Inventory & Maintenance 2025 | Baseline KPI có audit | KPI snapshot insert-only + hash chain |
| ISO 13485 (nếu áp) | Document control | PR/WI/BM workflow Effective/Obsolete (tuân thủ chung BV) |

## II.3. Document control workflow

- PR/WI/BM phát hành theo workflow chuẩn (Draft → Reviewed → Approved → Effective → Obsolete) — tuân thủ ISO 13485 BV.
- Mỗi version document có effective_date + revision history.
- Người ban hành: Trưởng phòng VT-TBYT; người duyệt cuối: Lãnh đạo BV.

## II.4. Training plan

| Đối tượng | Nội dung | Tần suất | Tài liệu |
|---|---|---|---|
| Trưởng phòng | Cockpit + xử lý signal | 1 lần go-live | WI-IMMIS-07-01, WI-IMMIS-07-02 |
| Nhóm HTM | Drill-down + cấu hình ngưỡng | 1 lần + ôn tập 6 tháng | WI-IMMIS-07-01, WI-IMMIS-07-03 |
| CNTT | Vận hành scheduler + verify chain | 1 lần | PR-IMMIS-07-03 |
| Auditor | Verify chain + đối chiếu báo cáo | 1 lần + theo lịch audit | PR-IMMIS-07-03 |

`[BA cần bổ sung]`: lịch đào tạo cụ thể theo BV.

---

# Phần III — Cấu hình môi trường thực nghiệm

## III.1. Test data pipeline

- Generator script: `assetcore/scripts/seed_imm07_demo.py` — sinh 30 ngày event giả lập cho 5 asset
- Reset script: `bench --site staging execute assetcore.scripts.reset_imm07_demo`

## III.2. UAT environment

- Site staging snapshot data thật ẩn danh (asset name + serial mask)
- 3 user role (Trưởng phòng, KTV, Auditor) seed sẵn

## III.3. Performance test (smoke)

- Tool: `locust` hoặc `k6`
- Scenario: 50 concurrent user load cockpit + 10 concurrent verify_chain
- Pass: p95 ≤ 600ms cho list endpoint

---

## DoD — File 08

- [x] Pre-deploy checklist
- [x] Deployment order step-by-step
- [x] Env matrix dev/staging/prod
- [x] Config rõ key
- [x] Smoke test
- [x] Rollback plan
- [x] Monitoring
- [x] QMS document tree đầy đủ mã (PR/WI/BM/HS/KPI-DASH)
- [x] Compliance mapping NĐ98 + WHO HTM
- [x] Training plan
- [ ] DevOps + QMS Officer sign-off
