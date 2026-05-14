# IMM-08 — Triển khai & Tuân thủ (Deployment & QMS)

| Mục | Giá trị |
|---|---|
| Module | **IMM-08 — Bảo trì Định kỳ (Preventive Maintenance)** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-14 |
| Owner | DevOps + Tech Lead + QMS Officer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [Module Overview](./IMM-08_Module_Overview.md) |

---

# Phần I — Deployment Plan

## I.1. Pre-deployment Checklist

Thực hiện trước mỗi window deploy (T = giờ deploy):

| Hạng mục | Deadline | Responsible | Status |
|---|---|---|---|
| PR merged, CI green (unit + integration + lint) | T-48h | Dev | ☐ |
| UAT pass (10 scenario, 0 Blocker, UAT-01/02/03/05 bắt buộc Pass) | T-48h | QA Lead | ☐ |
| Security sign-off (§III trong 07_Testing_QA) | T-48h | QA/Security | ☐ |
| QMS review pass (§II file này) | T-24h | QMS Officer | ☐ |
| User Guide + Release Notes viết xong | T-24h | BA/Tech Writer | ☐ |
| Backup production DB < 24h | T-2h | DevOps | ☐ |
| Communication email T-48h gửi users | T-48h | PM | ☐ |
| Rollback tested trên staging | T-24h | DevOps | ☐ |
| Staging deploy thành công + smoke test pass | T-24h | Dev + QA | ☐ |
| On-call engineer confirmed | T-1h | Dev Lead | ☐ |
| PM Checklist Template seeded cho mọi asset_category đang active | T-24h | Workshop Head + Admin | ☐ |

## I.2. Stack & Versioning

| Component | Phiên bản yêu cầu | Phiên bản hiện tại (prod) |
|---|---|---|
| Frappe | v15.x (latest stable) | v15.x |
| Python | 3.11+ | 3.11.x |
| Node.js | 20 LTS | 20.x |
| MariaDB | 10.6+ | 10.6.x |
| Redis | 7.x | 7.x |
| App `assetcore` | v1.0.0 (IMM-08 GA) | (upgrade từ 0.9.x) |

Cập nhật `assetcore/__init__.py`:
```python
__version__ = "1.0.0"  # IMM-08 General Availability (Wave 1)
```

## I.2b. Cấu Hình Môi Trường Thực Nghiệm

| Thành phần | Dev | Staging | Production |
|---|---|---|---|
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| CPU | 4 core | 8 core | 16 core |
| RAM | 8 GB | 16 GB | 32 GB |
| Disk SSD | 100 GB | 200 GB | 500 GB NVMe |
| MariaDB buffer pool | 2 GB | 8 GB | 16 GB |
| MariaDB max_connections | 100 | 200 | 300 |
| Redis maxmemory | 512 MB | 2 GB | 4 GB |
| Redis eviction policy | allkeys-lru | allkeys-lru | allkeys-lru |
| nginx worker processes | 2 | 4 | 8 |
| nginx max body size | 50 MB | 50 MB | 50 MB |
| Python venv path | `/home/frappe/frappe-bench` | (same) | (same) |
| Bench branch | version-15 | version-15 | version-15 |
| Supervisor programs | 4 (web×2, worker×2) | 6 (web×2, worker×4) | 10 (web×4, worker×6) |
| Backup target | Local `/backups` | Local + S3 `assetcore-staging` | Local + S3 `assetcore-prod` + off-site |
| Domain | `dev.assetcore.local` | `staging.assetcore.vn` | `assetcore.vn` |
| SSL cert | Self-signed | Let's Encrypt | Let's Encrypt (wildcard) |
| Firewall | Dev: open | Staging: 80/443 + 22 | Prod: 443 only + WAF |

## I.3. Deployment Artefacts

### Patch files

| Patch | File | Mô tả | Idempotent? |
|---|---|---|---|
| `v3_0.add_imm08_doctypes` | `assetcore/patches/v3_0/add_imm08_doctypes.py` | Scaffold 6 DocTypes (PM Schedule, PM Checklist Template, PM Checklist Item, PM Work Order, PM Checklist Result, PM Task Log) | ✅ `frappe.db.table_exists` check |
| `v3_0.add_pm_custom_asset_fields` | `assetcore/patches/v3_0/add_pm_custom_asset_fields.py` | Thêm `custom_last_pm_date`, `custom_next_pm_date`, `custom_pm_status` vào ERPNext `Asset` | ✅ `frappe.db.has_column` check |
| `v3_0.add_imm04_pm_hook` | `assetcore/patches/v3_0/add_imm04_pm_hook.py` | Hook `on_submit` Asset Commissioning → tạo PM Schedule đầu | ✅ flag check |
| `v3_0.seed_pm_checklist_templates` | `assetcore/patches/v3_0/seed_pm_checklist_templates.py` | Insert PM Checklist Template mẫu cho các asset_category phổ biến | ✅ `if not frappe.db.exists` |
| `v3_0.migrate_pm_status_fields` | `assetcore/patches/v3_0/migrate_pm_status_fields.py` | Backfill `custom_pm_status` cho Asset records existing (batch 200/run) | ✅ skip if already set |

Đăng ký trong `assetcore/patches.txt` (thứ tự cố định, không đổi).

### Fixtures cần re-import

```bash
bench --site assetcore.local import-fixtures --app assetcore
```

Fixtures: `Role`, `Role Profile`, `Has Role`, `Workspace`, `Custom Field` (Asset PM fields).

### Frontend build

```bash
cd apps/assetcore/frontend
npm ci
npm run build
bench build --app assetcore
```

### New dependencies

| Dependency | Loại | Version | Lý do |
|---|---|---|---|
| (không có mới) | — | — | IMM-08 dùng libraries hiện có |

## I.4. Deploy Sequence

### Staging (T-1 ngày)

```bash
# 1. SSH vào staging server
ssh frappe@staging.assetcore.vn

# 2. Bật maintenance mode
bench --site assetcore.local set-maintenance-mode on

# 3. Backup DB
bench --site assetcore.local backup --with-files

# 4. Pull code
cd frappe-bench
git pull origin main  # hoặc release branch

# 5. Setup requirements
./env/bin/pip install -e apps/assetcore

# 6. Frontend build
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore

# 7. Migrate + patches (thứ tự: v3_0.*)
bench --site assetcore.local migrate

# 8. Import fixtures
bench --site assetcore.local import-fixtures --app assetcore

# 9. Clear cache + restart
bench --site assetcore.local clear-cache
bench restart

# 10. Tắt maintenance mode
bench --site assetcore.local set-maintenance-mode off

# 11. Seed PM Checklist Templates cho staging
bench --site assetcore.local execute assetcore.scripts.seed.seed_pm_templates

# 12. Smoke test (§I.6)
```

### Production (giống staging + thêm)

- Chạy trong maintenance window: 23:00 - 02:00 (thứ 6 → thứ 7).
- Backup off-site (S3) ngay trước khi pull code.
- On-call engineer trực từ T đến T+4h.
- Nếu smoke test fail sau 30 phút → rollback ngay (§I.7).
- Sau deploy thành công: Workshop Head seed PM Checklist Templates production cho từng asset_category.

## I.5. Schema Migration Risk

| Thay đổi | Risk | Mitigation |
|---|---|---|
| Thêm 6 DocType mới | Low | `frappe.db.table_exists` check trong patch |
| Thêm custom fields vào ERPNext `Asset` | Low | `frappe.db.has_column` + default null |
| Hook `on_submit` Asset Commissioning | Medium | Test backward compat với Commissioning records hiện tại; flag check idempotent |
| Backfill `custom_pm_status` (Asset existing) | Medium | Batch 200/run + idempotent + dry-run staging trước |
| 2 Scheduler jobs trong `tasks.py` | Low | Idempotent; chỉ tạo WO khi `next_due_date <= today + alert_days_before` |

**Long-running migration** (patch `migrate_pm_status_fields`):
- Ước tính record: ≤ 500 Asset (Wave 1 data).
- Batch size: 200 records/iteration với `frappe.db.commit()` sau mỗi batch.
- Lock policy: Không lock table; chạy trong maintenance mode.
- Dry-run: `--dry-run` flag trên staging → xem log không có error.

## I.6. Smoke Test Sau Deploy

| Step | Cách | Expected |
|---|---|---|
| 1 | Đăng nhập `admin` vào site | Login thành công, hub hiển thị |
| 2 | Mở workspace `IMM Operations` | Module IMM-08 (PM) có trong sidebar |
| 3 | Mở `/pm/work-orders` (List view) | Danh sách PM WO load, không JS error |
| 4 | Mở `/pm/calendar` | Calendar tháng hiện tại load |
| 5 | Mở `/pm/dashboard` | Dashboard load, KPI cards hiển thị |
| 6 | Gọi `list_pm_work_orders` API | `{"success": true, "data": {...}}` |
| 7 | Gọi `get_pm_dashboard_stats?year=2026&month=5` | Response đúng format |
| 8 | Kiểm tra Custom Fields trên Asset | `custom_last_pm_date`, `custom_next_pm_date`, `custom_pm_status` tồn tại |
| 9 | Kiểm tra PM Checklist Template | Tồn tại ≥ 1 template cho asset_category phổ biến |
| 10 | Cron jobs registered | `bench --site assetcore.local scheduled-jobs` có `generate_pm_work_orders` (06:00) và `check_pm_overdue` (08:00) |
| 11 | Chạy test scheduler (manual) | `bench --site assetcore.local execute assetcore.tasks.generate_pm_work_orders` không lỗi |
| 12 | Frontend assets load | `/assets/assetcore/imm08*` không 404 |
| 13 | Hook IMM-04 verify | `frappe.get_doc("Asset Commissioning Event")` tồn tại hook `on_submit` |

## I.7. Rollback Plan

### Trigger conditions

- Login hoàn toàn không được (tất cả users).
- Asset Commissioning submit bị lỗi do hook IMM-08 (critical — block commissioning mới).
- Scheduler tạo PM WO trùng lặp (data corruption).
- API 5xx rate > 5% trong 10 phút đầu.

### Quick rollback < 15 phút

```bash
# 1. Bật maintenance mode
bench --site assetcore.local set-maintenance-mode on

# 2. Restore DB từ backup
bench --site assetcore.local restore /path/to/backup_before_deploy.sql.gz

# 3. Checkout commit cũ
git checkout v0.9.x-last-stable

# 4. Rebuild frontend (nếu cần)
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore

# 5. Clear cache + restart
bench --site assetcore.local clear-cache
bench restart

# 6. Tắt maintenance mode + verify
bench --site assetcore.local set-maintenance-mode off
```

### Forward fix

Khi đã có user mutation (PM WO submitted trong cửa sổ giữa deploy và rollback):
- Xuất PM WO mới tạo trước khi restore.
- Sau hotfix, re-import manually.
- Hotfix branch: `hotfix/imm08-v1.0.1`.

## I.8. Communication

**T-48h — Email trước deploy:**
> Kính gửi người dùng AssetCore,
> Hệ thống sẽ nâng cấp lúc 23:00 [ngày X] → 02:00 [ngày X+1]. Tính năng mới: Module IMM-08 Bảo trì định kỳ (PM). Hệ thống tạm ngừng khoảng 30-60 phút. Vui lòng hoàn tất công việc trước 22:30. Liên hệ: [support@hospital.vn]

**Trong deploy — Status:**
> Hệ thống đang bảo trì, dự kiến hoàn thành lúc 02:00. Cập nhật realtime: [status.assetcore.vn]

**T+1h sau deploy — Email hoàn tất:**
> Hệ thống AssetCore đã hoàn tất nâng cấp phiên bản 1.0.0. Tính năng mới: Module IMM-08 Bảo trì định kỳ. Xem User Guide: [link]. Báo lỗi: [support@hospital.vn]

## I.9. Monitoring & Alerting (T+24h)

| Metric | Ngưỡng cảnh báo | Tool |
|---|---|---|
| Error rate API imm08 | > 1% requests 5xx | Nginx log + Frappe error log |
| Scheduler `generate_pm_work_orders` không chạy | > 2h delay | Frappe scheduler log |
| Scheduler `check_pm_overdue` không chạy | > 2h delay | Frappe scheduler log |
| WO trùng lặp (idempotent fail) | Bất kỳ | Custom monitor script |
| DB CPU | > 80% trong 5 phút | Server monitoring |
| Disk usage (photo attachments) | > 80% | Server monitoring |
| Major Failure alert | Bất kỳ | Email Workshop Head + VP Block2 |
| API p95 `list_pm_work_orders` | > 2 s | Frappe slow query log |

## I.10. Post-deployment Checklist

- [ ] Git tag tạo: `git tag v1.0.0 -m "IMM-08 General Availability (Wave 1)"`
- [ ] Release Notes cập nhật version thực tế + ngày deploy
- [ ] Traceability matrix (`09_Release.md §III`) chốt cột `Released-in = v1.0.0`
- [ ] Workshop Head seed PM Checklist Templates production
- [ ] Backup config lưu off-site sau deploy thành công
- [ ] Post-mortem nếu có incident trong maintenance window

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu Trúc QMS Reference

| Cấp | Tên | Vai trò | ID format |
|---|---|---|---|
| QC | Quality Charter | Chính sách chất lượng cấp tổ chức | QC-XXXX |
| PR | Procedure | Quy trình chuẩn (SOP) per module | PR-IMM08-XXX |
| WI | Work Instruction | Hướng dẫn thao tác cho end-user | WI-IMM08-XXX |
| BM | Business Master | Master data + change control | (DocType name) |
| HS | Historical Snapshot | Bản ghi lịch sử không thể sửa | (PM Task Log + IMM Audit Trail) |
| KPI | Key Performance Indicator | Đo lường hiệu quả | KPI-IMM08-XXX |

## II.2. Trace Yêu Cầu Pháp Lý

### NĐ98/2021/NĐ-CP — Trang thiết bị y tế

| Điều/Khoản | Yêu cầu | Áp lên module qua | Doc/Code reference |
|---|---|---|---|
| Điều 22 — Bảo dưỡng định kỳ | Mỗi hoạt động bảo trì phải có phiếu ghi | `PM Work Order` submittable + `PM Task Log` immutable | DocType lifecycle |
| Điều 22.1 — Kế hoạch bảo trì | Lập kế hoạch PM định kỳ | `PM Schedule` per asset × pm_type; scheduler auto-create WO | `tasks.generate_pm_work_orders` |
| Điều 15.2 — Hồ sơ lưu trữ | ≥ 5 năm | `PM Task Log` + `IMM Audit Trail` immutable | `assetcore/utils/lifecycle.py` |
| Điều 23 — Thiết bị không đủ điều kiện | Thiết bị hỏng nặng phải ghi rõ + dừng sử dụng | BR-08-09 Fail-Major → Asset Out of Service + Halted–Major Failure | `pm_work_order._handle_failures()` |

### WHO HTM 2025 — Health Technology Management

| Section | Yêu cầu | Áp lên module qua | Code reference |
|---|---|---|---|
| §5.3 — Preventive Maintenance | PM được lên lịch, thực hiện theo checklist chuẩn | BR-08-01: `PM Checklist Template` bắt buộc; scheduler auto-create | `tasks.generate_pm_work_orders` |
| §5.3.2 — PM Scheduling | Lịch PM tiếp theo tính từ ngày hoàn tất (không từ ngày dự kiến) | BR-08-03: `next_pm_date = completion_date + interval` | `pm_work_order._update_pm_schedule()` |
| §5.3.4 — CM from PM | Lỗi phát hiện trong PM phải tạo CM WO có nguồn truy xuất | BR-08-09: `source_pm_wo` bắt buộc | `pm_work_order._handle_failures()` |
| §6.1 — KPI | PM Compliance Rate, MTTR được đo và báo cáo | `get_pm_dashboard_stats` API | `api/imm08.py` |

### ISO 13485:2016 — Medical Devices QMS

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| §7.5.1 — Controlled Conditions | Thiết bị y tế được bảo trì trong điều kiện kiểm soát | PM Checklist bắt buộc 100% + photo Class III |
| §7.6 — Control of Monitoring Equipment | Thiết bị đo lường được kiểm tra định kỳ | PM Schedule tích hợp với calibration check |
| §4.2.4 — Control of Records | Hồ sơ PM lưu đủ | PM Task Log immutable + IMM Audit Trail |
| §8.2.3 — Monitoring and Measurement | KPI PM compliance đo định kỳ | `get_pm_dashboard_stats` + trend 6 tháng |

## II.3. QMS Artefact Tạo Bởi Module

### PR (Procedure)

| ID | Tên | File | Workflow trong code |
|---|---|---|---|
| PR-IMM08-001 | Quy trình bảo trì định kỳ thiết bị y tế | `docs/imm-08/09_Release.md §I.4` (user guide) | PM WO Open→Completed |
| PR-IMM08-002 | Quy trình xử lý lỗi phát hiện trong PM | `IMM-08_Functional_Specs.md §BR-08-09` | Fail-Minor/Major → CM WO |
| PR-IMM08-003 | Quy trình hoãn lịch PM và quản lý thiết bị bận | `IMM-08_Functional_Specs.md §US-08-06` | `reschedule_pm` + Pending–Device Busy state |

### WI (Work Instruction)

| ID | Tên | Audience | File |
|---|---|---|---|
| WI-IMM08-001 | Hướng dẫn thực hiện PM trên tablet/điện thoại | HTM Technician | `09_Release.md §I.5.b` |
| WI-IMM08-002 | Hướng dẫn báo cáo lỗi Major Failure | HTM Technician | `09_Release.md §I.5.b` (§IV) |
| WI-IMM08-003 | Hướng dẫn phân công và giám sát PM | Workshop Manager | `09_Release.md §I.5.a` |
| WI-IMM08-004 | Hướng dẫn xem Dashboard PM KPI | VP Block2 | `09_Release.md §I.6` |

### BM (Business Master)

| Master data | Owner thay đổi | Change control |
|---|---|---|
| `PM Checklist Template` (per asset_category × pm_type) | Workshop Head | `PM Checklist Template` review + QMS Officer sign-off |
| `PM Schedule` (per asset) | CMMS Admin | Created auto từ IMM-04; manual override cần QMS Officer |
| Asset `custom_risk_class` | Workshop Head | `Asset` lifecycle workflow |

### HS (Historical Snapshot)

| ID | Source | Retention | Format |
|---|---|---|---|
| HS-IMM08-001 | `PM Task Log` per WO completion | ≥ 5 năm (NĐ98 Điều 15) | Frappe record, `in_create=1`, immutable |
| HS-IMM08-002 | `IMM Audit Trail` per PM lifecycle event | ≥ 5 năm | JSON hash chain, immutable |
| HS-IMM08-003 | `PM Work Order` submitted record | ≥ 5 năm | Frappe submittable, amend only |

### KPI

| ID | Tên | Công thức | Tần suất | Owner báo cáo |
|---|---|---|---|---|
| KPI-IMM08-001 | PM Compliance Rate | `COUNT(WO on_time) / COUNT(WO completed) × 100%` | Tháng | VP Block2 |
| KPI-IMM08-002 | PM Overdue Count | `COUNT(WO status=Overdue)` | Tuần | Workshop Head |
| KPI-IMM08-003 | Tỷ lệ trễ trung bình | `AVG(days_late) khi is_late=True` | Tháng | Workshop Head |
| KPI-IMM08-004 | PM Coverage Rate | `COUNT(Asset có PM Schedule active) / COUNT(Asset total)` | Tháng | VP Block2 |
| KPI-IMM08-005 | Major Failure Rate | `COUNT(Halted–Major Failure) / COUNT(WO completed) × 100%` | Tháng | VP Block2 + BGĐ |

API: `get_pm_dashboard_stats` + `get_pm_kpis` trong `api/imm08.py`.

## II.4. Document Control

Workflow PR/WI qua DocType `Asset Document` (IMM-05):

```
Draft → Reviewed → Approved → Effective → Obsolete
```

- **Change control**: PM Checklist Template thay đổi → version mới; phiên bản cũ Obsolete.
- **CAPA linkage**: Checklist thay đổi do Major Failure lặp lại → link `capa_ref`.
- **Training notification**: Khi PM Checklist Template mới Effective → trigger notification cho Workshop Head + HTM Technician qua IMM-06.

## II.5. Traceability Compliance → Code

| Yêu cầu | Test case | Code/DocType | Audit evidence |
|---|---|---|---|
| NĐ98 Điều 22 — Phiếu bảo trì | TC-08-02 (UAT-02) | `PM Work Order` submittable | `PM Task Log` record + `PM Work Order.docstatus=1` |
| NĐ98 Điều 22.1 — Kế hoạch PM | TC-08-01 (UAT-01) | `PM Schedule` + `tasks.generate_pm_work_orders` | `PM Schedule.next_due_date` tự cập nhật |
| NĐ98 Điều 23 — Out of Service | TC-08-05 (UAT-05) | BR-08-09: `_handle_failures()` | `Asset.status=Out of Service` + `PM WO.status=Halted` |
| WHO HTM §5.3.2 — BR-08-03 | TC-08-02 step 6 | `_update_pm_schedule()` | `PM Schedule.next_due_date = completion_date + interval` |
| ISO 13485 §4.2.4 — Hồ sơ lưu trữ | `test_audit_trail_immutable` | `PM Task Log` `in_create=1` | PM Task Log no-write DocPerm |

## II.6. Audit / Inspection Readiness

Khi auditor đến (cơ quan y tế, kiểm định):

- [ ] Truy xuất lịch sử PM của asset bất kỳ < 5 phút: `get_pm_history?asset=...`
- [ ] Verify PM Task Log immutable: thử sửa → bị block
- [ ] KPI compliance quarter: Dashboard → filter theo quý → export CSV
- [ ] Template checklist hiện hành: `PM Checklist Template` list filter `is_active=1`
- [ ] WO Major Failure: filter `status=Halted–Major Failure` → xem CM WO liên quan
- [ ] Role assignment: User Management → filter role Workshop Head, HTM Technician

**URL truy cập nhanh khi audit:**
- PM WO list: `/pm/work-orders`
- Calendar: `/pm/calendar`
- Dashboard: `/pm/dashboard`
- PM Task Log: Admin → `PM Task Log` doctype list

## II.7. Training & Roll-out

| Audience | Nội dung | Thời lượng | WI tham chiếu |
|---|---|---|---|
| Workshop Head | Phân công, Calendar, reschedule, giám sát KPI | 2h | WI-IMM08-003, WI-IMM08-004 |
| HTM Technician | Thực hiện PM, điền checklist mobile, báo cáo lỗi | 3h | WI-IMM08-001, WI-IMM08-002 |
| VP Block2 | Xem Dashboard KPI, nhận escalation email | 30 phút | WI-IMM08-004 |
| CMMS Admin | Cấu hình PM Schedule, template, fixtures | 1h | (Internal training) |

Training record lưu qua DocType `Training Record` (IMM-06). Bắt buộc hoàn tất trước go-live.

## II.8. Risk Register (Compliance)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| PM Checklist Template chưa tạo cho 1 asset_category → scheduler skip tạo WO | Medium | High | BR-08-01: email Admin khi skip; checklist trước go-live | Workshop Head + Admin |
| next_pm_date tính sai (từ due_date thay vì completion_date) → lệch lịch PM | Low | High | BR-08-03: enforce tại service layer `_update_pm_schedule()` | Tech Lead |
| Major Failure không cập nhật Asset Out of Service → tiếp tục tạo PM WO | Low | Critical | BR-08-09 + BR-08-04: enforce tại controller + scheduler skip check | Tech Lead |
| PM Task Log bị sửa → mất bằng chứng pháp lý | Low | Critical | `in_create=1` + DocPerm no-write + audit chain verify | QA Officer |
| Overdue không gửi email leo thang đúng cấp | Medium | Medium | Test UAT-03 bắt buộc; monitoring scheduler log | DevOps |

## II.9. Sign-off QMS

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| QMS Officer | | | |
| Tech Lead | | | |
| Module Owner (Workshop Manager) | | | |
| (Nếu cần) Legal / Pháp chế | | | |

---

## DoD — Hoàn chỉnh

### I. Deployment Plan
- [x] Pre-deploy checklist đầy đủ (11 mục — thêm template seed)
- [x] 5 patch files + đăng ký `patches.txt`
- [x] Fixtures cần import liệt kê
- [x] Cấu hình môi trường 3 môi trường (dev/staging/prod)
- [x] Deploy sequence staging + production documented
- [x] Smoke test 13 step
- [x] Rollback < 15 phút có script
- [x] Communication template T-48h + trong + T+1h
- [x] Monitoring 8 metric + ngưỡng alert
- [ ] On-call schedule confirmed (fill trước go-live)
- [x] Reviewed bởi DevOps + Tech Lead

### II. QMS Mapping
- [x] NĐ98/2021 ≥ 4 điều khoản đối chiếu
- [x] WHO HTM ≥ 4 section đối chiếu
- [x] ISO 13485 ≥ 4 điều đối chiếu
- [x] PR 3 + WI 4 tạo cho major workflows
- [x] HS retention 5 năm cho audit-relevant (3 HS)
- [x] KPI 5 metric có công thức + tần suất + owner
- [x] Audit-readiness checklist ≥ 6 mục
- [x] Training plan cho mọi 4 role
- [x] Risk register 5 mục với mitigation
- [x] Sign-off section sẵn sàng
