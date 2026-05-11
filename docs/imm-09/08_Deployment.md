# IMM-09 — Triển khai & Tuân thủ (Deployment & QMS)

| Mục | Giá trị |
|---|---|
| Module | **IMM-09 — Sửa chữa (Corrective Maintenance)** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | DevOps + Tech Lead + QMS Officer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [Module Overview](./IMM-09_Module_Overview.md) |

---

# Phần I — Deployment Plan

## I.1. Pre-deployment Checklist

Thực hiện trước mỗi window deploy (T = giờ deploy):

| Hạng mục | Deadline | Responsible | Status |
|---|---|---|---|
| PR merged, CI green (unit + integration + lint) | T-48h | Dev | ☐ |
| UAT pass (12 scenario, 0 Blocker) | T-48h | QA Lead | ☐ |
| Security sign-off (§III trong 07_Testing_QA) | T-48h | QA/Security | ☐ |
| QMS review pass (§II file này) | T-24h | QMS Officer | ☐ |
| User Guide + Release Notes viết xong | T-24h | BA/Tech Writer | ☐ |
| Backup production DB < 24h | T-2h | DevOps | ☐ |
| Communication email T-48h gửi users | T-48h | PM | ☐ |
| Rollback tested trên staging | T-24h | DevOps | ☐ |
| Staging deploy thành công + smoke test pass | T-24h | Dev + QA | ☐ |
| On-call engineer confirmed | T-1h | Dev Lead | ☐ |

## I.2. Stack & Versioning

| Component | Phiên bản yêu cầu | Phiên bản hiện tại (prod) |
|---|---|---|
| Frappe | v15.x (latest stable) | v15.x |
| Python | 3.11+ | 3.11.x |
| Node.js | 20 LTS | 20.x |
| MariaDB | 10.6+ | 10.6.x |
| Redis | 7.x | 7.x |
| App `assetcore` | v1.0.0 (IMM-09 GA) | (upgrade từ 0.9.x) |

Cập nhật `assetcore/__init__.py`:
```python
__version__ = "1.0.0"  # IMM-09 General Availability
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
| Backup target | Local `/backups` | Local + S3 bucket `assetcore-staging` | Local + S3 bucket `assetcore-prod` + off-site |
| Domain | `dev.assetcore.local` | `staging.assetcore.vn` | `assetcore.vn` |
| SSL cert | Self-signed | Let's Encrypt | Let's Encrypt (wildcard) |
| Firewall | Dev: open | Staging: 80/443 + 22 only | Prod: 443 only + WAF |

## I.3. Deployment Artefacts

### Patch files

| Patch | File | Mô tả | Idempotent? |
|---|---|---|---|
| `v3_0.add_imm09_sla_fields` | `assetcore/patches/v3_0/add_imm09_sla_fields.py` | Thêm `sla_target_hours`, `mttr_hours`, `sla_breached` vào `Asset Repair` | ✅ `frappe.db.has_column` check |
| `v3_0.add_firmware_change_request` | `assetcore/patches/v3_0/add_firmware_change_request.py` | Tạo DocType `Firmware Change Request` + fields | ✅ |
| `v3_0.seed_sla_policy` | `assetcore/patches/v3_0/seed_sla_policy.py` | Insert `IMM SLA Policy` records (Class I/II/III × 3 priority) | ✅ `if not frappe.db.exists` |
| `v3_0.migrate_old_repair_status` | `assetcore/patches/v3_0/migrate_old_repair_status.py` | Map trạng thái cũ → workflow state mới (batch 200/run) | ✅ skip if already migrated |

Đăng ký trong `assetcore/patches.txt` (thứ tự cố định, không đổi).

### Fixtures cần re-import

```bash
bench --site assetcore.local import-fixtures --app assetcore
```

Fixtures: `Role`, `Role Profile`, `Has Role`, `Workflow` (IMM-09 Repair Workflow), `Workflow State`, `Workflow Action Master`, `IMM SLA Policy`, `Workspace`.

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
| (không có mới) | — | — | IMM-09 dùng libraries hiện có |

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

# 7. Migrate + patches
bench --site assetcore.local migrate

# 8. Import fixtures
bench --site assetcore.local import-fixtures --app assetcore

# 9. Clear cache + restart
bench --site assetcore.local clear-cache
bench restart

# 10. Tắt maintenance mode
bench --site assetcore.local set-maintenance-mode off

# 11. Smoke test (§I.6)
```

### Production (giống staging + thêm)

- Chạy trong maintenance window: 23:00 - 02:00 (thứ 6 → thứ 7).
- Backup off-site (S3) ngay trước khi pull code.
- On-call engineer trực từ T đến T+4h.
- Nếu smoke test fail sau 30 phút → rollback ngay (§I.7).

## I.5. Schema Migration Risk

| Thay đổi | Risk | Mitigation |
|---|---|---|
| Thêm column nullable `sla_target_hours` | Low | `frappe.db.add_column` + default null |
| Thêm column nullable `mttr_hours` | Low | (same) |
| Thêm column boolean `sla_breached` | Low | Default 0 |
| Thêm DocType `Firmware Change Request` (mới) | Low | `frappe.db.table_exists` check |
| Migrate workflow state cũ → mới | Medium | Batch 200/run + idempotent check + dry-run staging trước |

**Long-running migration** (patch `migrate_old_repair_status`):
- Ước tính record: ≤ 1000 WO (Wave 1 dev data).
- Batch size: 200 records/iteration với `frappe.db.commit()` sau mỗi batch.
- Lock policy: Không lock table; chạy trong maintenance mode.
- Dry-run: `--dry-run` flag trên staging → xem log không có error.

## I.6. Smoke Test Sau Deploy

| Step | Cách | Expected |
|---|---|---|
| 1 | Đăng nhập `admin` vào site | Login thành công, hub hiển thị |
| 2 | Mở workspace `IMM Operations` | Workspace load, module IMM-09 có trong sidebar |
| 3 | Mở `/imm-09` (List view) | Danh sách WO load, không có JS error console |
| 4 | Tạo 1 WO test (không submit) | Form hiển thị đúng, auto-fill hoạt động |
| 5 | Gọi `list_repair_work_orders` API | `{"success": true, "data": {...}}` |
| 6 | Gọi `get_repair_kpis` API | Response đúng format, có `mttr_avg`, `sla_compliance_rate` |
| 7 | Kiểm tra workflow IMM-09 | `frappe.get_doc("Workflow", "IMM-09 Repair Workflow")` tồn tại |
| 8 | Kiểm tra SLA Policy | 9 records `IMM SLA Policy` (3 class × 3 priority) tồn tại |
| 9 | Audit trail verify | `verify_audit_chain(some_asset)` = True |
| 10 | Cron jobs registered | `bench --site assetcore.local scheduled-jobs` có `check_repair_sla_breach` |
| 11 | Frontend assets load | `/assets/assetcore/` không 404 |
| 12 | Permission test | KTV login → chỉ thấy WO được assign |

## I.7. Rollback Plan

### Trigger conditions

- Login hoàn toàn không được (tất cả users).
- Migration gây data corruption (verify bằng record count trước/sau).
- Critical permission bug (user thấy data không được phép).
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

Khi đã có user mutation (WO tạo trong cửa sổ giữa deploy và rollback):
- Xuất WO mới tạo trước khi restore: `bench --site ... export-doctype "Asset Repair" ...`
- Sau hotfix, re-import manually.
- Hotfix branch: `hotfix/imm09-v1.0.1`.

## I.8. Communication

**T-48h — Email trước deploy:**
> Kính gửi người dùng AssetCore,
> Hệ thống sẽ nâng cấp lúc 23:00 [ngày X] → 02:00 [ngày X+1]. Tính năng mới: Module IMM-09 Sửa chữa (CM). Hệ thống tạm ngừng trong khoảng 30-60 phút. Vui lòng hoàn tất công việc trước 22:30. Liên hệ: [support@hospital.vn]

**Trong deploy — Status:**
> Hệ thống đang bảo trì, dự kiến hoàn thành lúc 02:00. Cập nhật realtime: [status.assetcore.vn]

**T+1h sau deploy — Email hoàn tất:**
> Hệ thống AssetCore đã hoàn tất nâng cấp phiên bản 1.0.0. Tính năng mới: Module IMM-09 Sửa chữa. Xem User Guide: [link]. Báo lỗi: [support@hospital.vn]

## I.9. Monitoring & Alerting (T+24h)

| Metric | Ngưỡng cảnh báo | Tool |
|---|---|---|
| Error rate API imm09 | > 1% requests 5xx | Nginx log + Frappe error log |
| Login fail rate | > 10 lần / phút | Frappe login log |
| API p95 `list_repair_work_orders` | > 2 s | Frappe slow query log |
| DB CPU | > 80% trong 5 phút | Server monitoring (htop / CloudWatch) |
| Disk usage | > 80% | Server monitoring |
| Audit chain verify fail | Bất kỳ | Email `IMM System Admin` |
| SLA scheduler fail | Job không chạy > 2h | Frappe scheduler log |

## I.10. Post-deployment Checklist

- [ ] Git tag tạo: `git tag v1.0.0 -m "IMM-09 General Availability"`
- [ ] Release Notes cập nhật version thực tế + ngày deploy
- [ ] Traceability matrix (`09_Release.md §III`) chốt cột `Released-in = v1.0.0`
- [ ] Backup config lưu off-site sau deploy thành công
- [ ] Post-mortem nếu có incident trong maintenance window
- [ ] Retro sprint kế: note improvement cho deploy lần sau

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu Trúc QMS Reference

| Cấp | Tên | Vai trò | ID format |
|---|---|---|---|
| QC | Quality Charter | Chính sách chất lượng cấp tổ chức | QC-XXXX |
| PR | Procedure | Quy trình chuẩn (SOP) per module | PR-IMM09-XXX |
| WI | Work Instruction | Hướng dẫn thao tác cho end-user | WI-IMM09-XXX |
| BM | Business Master | Master data + change control | (DocType name) |
| HS | Historical Snapshot | Bản ghi lịch sử không thể sửa | (IMM Audit Trail records) |
| KPI | Key Performance Indicator | Đo lường hiệu quả | KPI-IMM09-XXX |

## II.2. Trace Yêu Cầu Pháp Lý

### NĐ98/2021/NĐ-CP — Trang thiết bị y tế

| Điều/Khoản | Yêu cầu | Áp lên module qua | Doc/Code reference |
|---|---|---|---|
| Điều 15.2 — Hồ sơ TTBYT | Lưu trữ hồ sơ thiết bị ≥ 5 năm | `IMM Audit Trail` immutable hash chain | `assetcore/utils/lifecycle.py` |
| Điều 22 — Bảo dưỡng, sửa chữa | Mỗi hoạt động sửa chữa phải có phiếu ghi | `Asset Repair` DocType + submit | `assetcore/assetcore/doctype/asset_repair/` |
| Điều 22.3 — Phụ tùng thay thế | Phụ tùng sử dụng có chứng từ xuất kho | BR-09-02: `stock_entry_ref` bắt buộc | `services/imm09.py: validate_spare_parts_stock_entries()` |
| Điều 23 — Không đủ điều kiện | Thiết bị hỏng không sửa được phải ghi rõ lý do | `cannot_repair_reason` field + `Asset.status = Out of Service` | `services/imm09.py: _mark_cannot_repair()` |

### Quyết định 3107/QĐ-BYT — Danh mục TTBYT

| Khoản | Yêu cầu | Áp lên module qua |
|---|---|---|
| Phân loại Class I/II/III | Thiết bị phân loại đúng rủi ro | `risk_class` field trên `AC Asset` + SLA matrix |
| Thiết bị Class III | Sửa chữa Class III cần ưu tiên và kiểm tra nghiêm ngặt | SLA Emergency 4h + bắt buộc `Repair Checklist` Pass 100% |

### WHO HTM 2025 — Health Technology Management

| Section | Yêu cầu | Áp lên module qua | Code reference |
|---|---|---|---|
| §5.4.2 — CM Initiation | CM WO phải có nguồn khởi tạo rõ ràng (incident hoặc PM failure) | BR-09-01: `incident_report` OR `source_pm_wo` | `validate_repair_source()` |
| §6.1 — MTTR | Đo MTTR, so sánh với benchmark | `mttr_hours` tính sau Submit; `get_mttr_report()` API | `complete_repair()` |
| §6.3 — Spare Parts | Vật tư sử dụng có traceability | BR-09-02: `stock_entry_ref` | `validate_spare_parts_stock_entries()` |
| §7.2 — Software/Firmware | Thay đổi firmware qua change control | BR-09-03: `Firmware Change Request` Approved | `validate_firmware_change_request()` |
| §3.3.1 — Asset Status | Trạng thái thiết bị phản ánh thực tế (Under Repair / Active) | BR-09-05: asset status gắn liền workflow | `set_asset_under_repair()`, `complete_repair()` |

### ISO 13485:2016 — Medical Devices QMS

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| 8.5 — Hành động khắc phục | Lỗi lặp lại cần CAPA | BR-09-06: `is_repeat_failure` → khuyến nghị CAPA (IMM-12) |
| 7.5.4 — Tài sản khách hàng | Thiết bị của bệnh viện được bảo vệ khi sửa chữa | `asset_ref` foreign key bắt buộc, `assigned_to` audit |
| 4.2.4 — Kiểm soát hồ sơ | Hồ sơ sửa chữa lưu trữ đủ | `Asset Repair` submittable + immutable sau submit |

## II.3. QMS Artefact Tạo Bởi Module

### PR (Procedure)

| ID | Tên | File | Workflow trong code |
|---|---|---|---|
| PR-IMM09-001 | Quy trình tiếp nhận và xử lý yêu cầu sửa chữa | `docs/imm-09/09_Release.md §I.4` (user guide) | IMM-09 Repair Workflow states Open→Completed |
| PR-IMM09-002 | Quy trình kiểm soát firmware thiết bị y tế | `docs/imm-09/IMM-09_Functional_Specs.md §BR-09-03` | `Firmware Change Request` workflow |
| PR-IMM09-003 | Quy trình nghiệm thu sau sửa chữa | `docs/imm-09/IMM-09_Functional_Specs.md §BR-09-04` | Checklist 100% Pass + dept head confirm |

### WI (Work Instruction)

| ID | Tên | Audience | File |
|---|---|---|---|
| WI-IMM09-001 | Hướng dẫn tạo phiếu sửa chữa | Workshop Manager | `09_Release.md §I.5.a` |
| WI-IMM09-002 | Hướng dẫn chẩn đoán và yêu cầu vật tư | IMM Biomed Technician | `09_Release.md §I.5.b` |
| WI-IMM09-003 | Hướng dẫn xác nhận nghiệm thu | IMM Department Head | `09_Release.md §I.5.d` |
| WI-IMM09-004 | Hướng dẫn xem MTTR Report | IMM Operations Manager | `09_Release.md §I.6` |

### BM (Business Master)

| Master data | Owner thay đổi | Change control |
|---|---|---|
| `IMM SLA Policy` (SLA matrix 9 entries) | Tech Lead | Fixture + PR review + QMS Officer approval |
| `AC Asset` risk_class | IMM Workshop Lead | `AC Asset Lifecycle` workflow |
| `AC Spare Part` catalog | IMM Storekeeper | Inventory module |

### HS (Historical Snapshot)

| ID | Source | Retention | Format |
|---|---|---|---|
| HS-IMM09-001 | `IMM Audit Trail` per WO | ≥ 5 năm (NĐ98 Điều 15) | JSON hash chain, immutable |
| HS-IMM09-002 | `Asset Lifecycle Event` repair_opened/completed | ≥ 5 năm | Frappe record, no-delete |
| HS-IMM09-003 | `Asset Repair` submitted record | ≥ 5 năm | Frappe submittable, amend only |

### KPI

| ID | Tên | Công thức | Tần suất | Owner báo cáo |
|---|---|---|---|---|
| KPI-IMM09-001 | MTTR trung bình | `AVG(mttr_hours)` per tháng, per risk class | Tháng | IMM Operations Manager |
| KPI-IMM09-002 | SLA Compliance Rate | `COUNT(WO sla_breached=0) / COUNT(WO closed) × 100%` | Tuần | IMM Operations Manager |
| KPI-IMM09-003 | Repeat Failure Rate | `COUNT(WO is_repeat_failure=1) / COUNT(WO total) × 100%` | Tháng | IMM QA Officer |
| KPI-IMM09-004 | WO Cannot Repair Rate | `COUNT(Cannot Repair) / COUNT(total) × 100%` | Tháng | IMM Workshop Lead |
| KPI-IMM09-005 | Thời gian phân công trung bình | `AVG(assigned_datetime - open_datetime)` | Tuần | IMM Workshop Lead |

API: `get_repair_kpis` + `get_mttr_report` trong `api/imm09.py`.

## II.4. Document Control

Workflow PR/WI qua DocType `Asset Document` (IMM-05):

```
Draft → Reviewed → Approved → Effective → Obsolete
```

- **Change control**: Mọi thay đổi PR/WI tạo phiên bản mới; phiên bản cũ chuyển Obsolete.
- **CAPA linkage**: Nếu PR thay đổi do CAPA → link `capa_ref` vào `Asset Document`.
- **Training**: Khi PR/WI Effective → trigger training notification cho audience (IMM-06).

## II.5. Traceability Compliance → Code

| Yêu cầu | Test case | Code/DocType | Audit evidence |
|---|---|---|---|
| NĐ98 Điều 22.3 — Chứng từ vật tư | TC-09-04 (UAT-04) | BR-09-02: `validate_spare_parts_stock_entries()` | `IMM Audit Trail` record + `Spare Parts Used.stock_entry_ref` |
| NĐ98 Điều 15.2 — Lưu trữ ≥ 5 năm | `test_audit_chain_intact` | `IMM Audit Trail` immutable | `verify_audit_chain()` pass |
| WHO HTM §5.4.2 — CM source | TC-09-02 (UAT-02) | BR-09-01: `validate_repair_source()` | `Asset Repair.incident_report / source_pm_wo` |
| WHO HTM §6.1 — MTTR | UAT-IMM09-05 | `complete_repair()` + `get_mttr_report()` | `Asset Repair.mttr_hours` field |
| ISO 13485 §8.5 — CAPA for repeat | UAT-IMM09-08 | BR-09-06: `check_repeat_failure()` | `Asset Repair.is_repeat_failure = 1` |

## II.6. Audit / Inspection Readiness

Khi auditor đến (cơ quan y tế, kiểm định):

- [ ] Truy xuất WO theo asset bất kỳ < 5 phút: `get_asset_repair_history?asset=...`
- [ ] Verify audit chain 1 click: `verify_audit_chain(asset)` từ console
- [ ] KPI quarter: Dashboard MTTR Report → filter theo quý
- [ ] Document control: `Asset Document` list filter `status=Effective` → xem PR/WI hiện hành
- [ ] CAPA chưa đóng: IMM-12 CAPA list filter `status != Closed`
- [ ] Role assignment: `frappe.get_all("Has Role", ...)` hoặc User Management
- [ ] SLA history: WO list filter `sla_breached=1` → export CSV

**URL truy cập nhanh khi audit:**
- WO list: `/imm-09`
- Dashboard: `/imm-09/dashboard`
- MTTR report: `/imm-09/mttr-report`
- Audit trail: Admin → `IMM Audit Trail` doctype list

## II.7. Training & Roll-out

| Audience | Nội dung | Thời lượng | WI tham chiếu |
|---|---|---|---|
| IMM Workshop Lead | Tạo WO, phân công, duyệt FCR, xem Dashboard | 2h | WI-IMM09-001, WI-IMM09-004 |
| IMM Biomed Technician | Chẩn đoán, yêu cầu vật tư, sửa chữa, checklist | 3h | WI-IMM09-002 |
| IMM Storekeeper | Gắn Stock Entry vào WO | 1h | WI-IMM09-002 §parts |
| IMM Department Head | Xác nhận nghiệm thu | 30 phút | WI-IMM09-003 |
| IMM Operations Manager | Xem MTTR Report, Dashboard KPI | 1h | WI-IMM09-004 |

Training record lưu qua DocType `Training Record` (IMM-06). Bắt buộc hoàn tất trước go-live.

## II.8. Risk Register (Compliance)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| WO tạo không có nguồn (không trace được lý do hỏng) | Medium | High | BR-09-01 enforce tại service layer + UI validation | Tech Lead |
| Vật tư dùng không có chứng từ (thất thoát, không audit được) | Low | High | BR-09-02 block submit khi thiếu `stock_entry_ref` | IMM Storekeeper |
| Firmware thay đổi không kiểm soát (security + patient safety) | Low | Critical | BR-09-03: FCR Approved bắt buộc | IMM Workshop Lead |
| MTTR không được đo → không biết device performance | Medium | Medium | `complete_repair()` auto-calc + `check_repair_sla_breach()` hourly | IMM Operations Manager |
| Audit chain bị tamper (pháp lý, kiện tụng) | Low | Critical | IMM Audit Trail immutable + verify endpoint + regular hash verify | IMM QA Officer |
| Lỗi lặp lại không phát hiện → thiết bị nguy hiểm | Medium | High | BR-09-06: auto-flag + CAPA recommendation | IMM QA Officer |

## II.9. Sign-off QMS

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| QMS Officer | | | |
| Tech Lead | | | |
| Module Owner (IMM-09) | | | |
| (Nếu cần) Legal / Pháp chế | | | |

---

## DoD — Hoàn chỉnh

### I. Deployment Plan
- [x] Pre-deploy checklist đầy đủ (10 mục)
- [x] 4 patch files + đăng ký `patches.txt`
- [x] Fixtures cần import liệt kê
- [x] Cấu hình môi trường 3 môi trường (dev/staging/prod)
- [x] Deploy sequence staging + production documented
- [x] Smoke test 12 step
- [x] Rollback < 15 phút có script
- [x] Communication template T-48h + trong + T+1h
- [x] Monitoring 7 metric + ngưỡng alert
- [ ] On-call schedule confirmed (fill trước go-live)
- [x] Reviewed bởi DevOps + Tech Lead

### II. QMS Mapping
- [x] NĐ98/2021 ≥ 4 điều khoản đối chiếu
- [x] WHO HTM ≥ 5 section đối chiếu
- [x] ISO 13485 ≥ 3 điều đối chiếu
- [x] PR 3 + WI 4 tạo cho major workflows
- [x] HS retention 5 năm cho audit-relevant (3 HS)
- [x] KPI 5 metric có công thức + tần suất + owner
- [x] Audit-readiness checklist ≥ 6 mục
- [x] Training plan cho mọi 5 role
- [x] Risk register 6 mục với mitigation
- [x] Sign-off section sẵn sàng
