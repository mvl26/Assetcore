# IMM-17 — Deployment

| Mục | Giá trị |
|---|---|
| Module | IMM-17 — Phân tích dự đoán |
| Đợt | 3 (Predictive cockpit) |
| Trạng thái | Plan |
| Cập nhật | 2026-05-10 |

---

## 1. Pre-conditions (data layer gate)

IMM-17 KHÔNG được deploy production trước khi:
- Wave 1 (IMM-04, 05, 08, 09, 11, 12) đã ổn định ≥6 tháng production.
- IMM-07 KPI snapshot đã ship + có ≥6 tháng dữ liệu chất lượng.
- Audit chain verify pass cho ≥100 asset đại diện.
- Có policy management review predictive output (theo Architecture điều kiện chuyển Đợt 3).

→ Nếu chưa đủ điều kiện: deploy **dry-run** môi trường staging, không activate cron production.

---

## 2. Migration / Patch

| Bước | File | Mục đích |
|---|---|---|
| 1 | `assetcore/patches/v3_x/add_predictive_doctypes.py` | Tạo `AC Predictive Insight`, `IMM Predictive Model`, `IMM Predictive Run Log` |
| 2 | `assetcore/patches/v3_x/seed_predictive_event_types.py` | Bổ sung event_type vào `services/shared/constants.py` |
| 3 | `assetcore/patches/v3_x/wire_imm17_scheduler.py` | Thêm scheduler entry vào `hooks.py` |
| 4 | `assetcore/patches/v3_x/seed_default_thresholds.py` | Seed threshold mặc định (severity High/Med/Low) |

> Patch path cụ thể chốt khi sprint, phải chạy `bench --site <site> migrate` để áp dụng.

---

## 3. Fixtures cần export / import

- `IMM Predictive Model` (1 record bootstrap version `v0.0.1` Inactive)
- `Role Profile` mới: `IMM - Data Scientist` (nếu cần)
- Scheduler events trong `hooks.py` (không phải fixture, deploy qua code)

---

## 4. Hooks change

Thêm vào `hooks.py` ở Wave 3:
- `scheduler_events.weekly` += `assetcore.services.imm17.run_weekly_pipeline`
- `scheduler_events.daily` += `assetcore.services.imm17.check_drift` (tuỳ chọn)

> KHÔNG bật scheduler cho đến khi DoD ở `07_Testing_QA.md` §8 đạt.

---

## 5. Deployment steps (production)

1. `git pull` đến tag chứa Wave 3 IMM-17.
2. `bench --site <site> migrate` (chạy patch).
3. `bench --site <site> install-app` không cần (assetcore đã cài).
4. `bench --site <site> import-fixtures` (Role Profile mới).
5. `bench build` (FE bundle bổ sung).
6. `bench restart`.
7. **Smoke**: chạy `bench --site <site> execute assetcore.services.imm17.run_for_asset --kwargs "{'asset_name': '<sample>'}"` và verify 1 insight + 1 audit.
8. Activate cron: deploy với `scheduler_enabled = true` (đã có sẵn cho site, không cần đổi).
9. Theo dõi 1 tuần đầu: run log status, alert nếu fail.

---

## 6. Rollback plan

- Disable cron entry IMM-17 trong `hooks.py` (revert commit) → `bench restart`.
- KHÔNG xoá `AC Predictive Insight` đã sinh (giữ audit).
- KHÔNG xoá `Asset Lifecycle Event` đã emit `replacement_signal_emitted` (immutable, R-05).
- Nếu phát hiện bug nghiêm trọng → set `IMM Predictive Model` Active → Inactive, đợi fix.

---

## 7. Monitoring & alerting

| Signal | Ngưỡng | Action |
|---|---|---|
| Pipeline run fail | ≥3 fail liên tiếp | Email IMM System Admin + Operations Manager |
| Pipeline duration | > NFR-17-01 (30 phút) | Warning, profile job |
| Model drift KRI-17-01 | Vượt threshold | Email Data Scientist, mở issue retrain |
| Audit chain verify fail | bất kỳ asset | Critical alert — pause pipeline |
| Insight ignored rate (KRI-17-02) | > 30% / tháng | Trưởng VTTBYT review process |

---

## 8. QMS mapping (theo Architecture §"Lớp QMS")

| Tài liệu QMS | Mã dự kiến | Mục đích |
|---|---|---|
| Procedure (PR) | `PR-IMMIS-17-01` | Quy trình vận hành lớp predictive (cron + ack + retrain) |
| Work Instruction (WI) | `WI-IMMIS-17-01` | Hướng dẫn HTM Engineer xử lý insight |
| WI | `WI-IMMIS-17-02` | Hướng dẫn Data Scientist deploy model |
| Form (BM) | `BM-IMMIS-17-01` | Biểu mẫu validation report khi activate model |
| Log (HS-LOG) | `HS-LOG-IMMIS-17-01` | Run log + audit chain |
| Report (HS-REP) | `HS-REP-IMMIS-17-01` | Báo cáo predictive performance hàng quý |
| KPI dashboard | `KPI-DASH-IMMIS-17` | Cockpit + KPI 17-01 → 17-05 |

> Mã chính thức do Tổ HC-QLCL & Risk cấp khi đăng ký vào QMS điện tử.

---

## 9. Change control

Mọi thay đổi:
- Threshold severity → cần phê duyệt Trưởng VTTBYT + Tổ HC-QLCL.
- Activate model version mới → cần validation report + duyệt System Admin.
- Sửa/disable scheduler → cần phê duyệt Operations Manager.

→ Tuân R-09 (không hardcode), R-04 (audit), Architecture §"Lớp QMS".

---

## 10. Cấu hình staging vs production

| Item | Staging | Production |
|---|---|---|
| Cron | Bật, chạy weekly | Bật sau khi DoD đạt |
| Vendor ML INT-13 | Stub | Real (Wave 3 cuối) |
| Threshold | Có thể tuning | Lock, đổi qua change control |
| Model retrain | On-demand | Quarterly + on-drift |
