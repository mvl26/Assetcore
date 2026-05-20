# IMM-11 — Triển khai & Tuân thủ (Deployment & QMS)

| Mục | Giá trị |
|---|---|
| Module | **IMM-11 — Hiệu chuẩn (Calibration)** |
| Phiên bản | 1.1.0 |
| Ngày cập nhật | 2026-05-18 |
| Owner | DevOps + Tech Lead + QMS Officer |
| Trạng thái | ✅ Live — code đã deploy. Checklist + rollback giữ ở mức playbook chuẩn cho release tiếp theo. |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [Module Overview](./IMM-11_Module_Overview.md) |

---

# Phần I — Deployment Plan

## I.1. Pre-deployment Checklist

> Module IMM-11 đã LIVE (code deploy Wave 1). Checklist dưới đây là playbook chuẩn cho các release tiếp theo (patch, minor upgrade).

| Hạng mục | Deadline | Responsible | Status |
|---|---|---|---|
| DocType JSON + controller code merged, CI green | T-48h | Dev | ☐ |
| Service layer (`services/imm11.py`) unit tests pass ≥ 85% | T-48h | Dev | ☐ |
| UAT pass (10 scenario, 0 Blocker) | T-48h | QA Lead | ☐ |
| Security sign-off (§III trong 07_Testing_QA) | T-48h | QA/Security | ☐ |
| QMS review pass (§II file này) | T-24h | QMS Officer | ☐ |
| User Guide + Release Notes viết xong | T-24h | BA/Tech Writer | ☐ |
| Backup production DB < 24h | T-2h | DevOps | ☐ |
| Communication email T-48h gửi users | T-48h | PM | ☐ |
| Rollback tested trên staging | T-24h | DevOps | ☐ |
| Staging deploy thành công + smoke test pass | T-24h | Dev + QA | ☐ |
| On-call engineer confirmed | T-1h | Dev Lead | ☐ |

## I.2. Stack & Versioning

| Component | Phiên bản yêu cầu | Ghi chú |
|---|---|---|
| Frappe | v15.x (latest stable) | Không thay đổi |
| Python | 3.11+ | Không thay đổi |
| Node.js | 20 LTS | Không thay đổi |
| MariaDB | 10.6+ | Không thay đổi |
| Redis | 7.x | Không thay đổi |
| App `assetcore` | v1.1.0 (IMM-11 GA) ✅ Live | Upgrade từ v1.0.0 (IMM-09) |

Cập nhật `assetcore/__init__.py` khi patch release tiếp theo:
```python
__version__ = "1.1.0"  # IMM-11 General Availability
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
| nginx worker processes | 2 | 4 | 8 |
| nginx max body size | **100 MB** | **100 MB** | **100 MB** |
| Python venv path | `/home/frappe/frappe-bench` | (same) | (same) |
| Bench branch | version-15 | version-15 | version-15 |
| Supervisor programs | 4 (web×2, worker×2) | 6 (web×2, worker×4) | 10 (web×4, worker×6) |
| Backup target | Local `/backups` | Local + S3 `assetcore-staging` | Local + S3 `assetcore-prod` + off-site |
| Domain | `dev.assetcore.local` | `staging.assetcore.vn` | `assetcore.vn` |
| SSL cert | Self-signed | Let's Encrypt | Let's Encrypt (wildcard) |
| Firewall | Dev: open | Staging: 80/443 + 22 | Prod: 443 only + WAF |

> **Lưu ý quan trọng:** `nginx max body size` tăng lên **100 MB** (so với 50 MB của IMM-09) để hỗ trợ upload Certificate PDF. Cần cập nhật nginx config trên mọi môi trường.

## I.3. Deployment Artefacts

> Artefacts đã deploy trong Wave 1. Section này là reference cho rollback/upgrade patch tiếp theo.

### Patch files (cần tạo)

| Patch | File | Mô tả | Idempotent? |
|---|---|---|---|
| `v3_1.create_imm_calibration_schedule` | `assetcore/patches/v3_1/create_imm_calibration_schedule.py` ⚠️ | Tạo DocType `IMM Calibration Schedule` + migrate existing data | ✅ `frappe.db.table_exists` check |
| `v3_1.create_imm_asset_calibration` | `assetcore/patches/v3_1/create_imm_asset_calibration.py` ⚠️ | Tạo DocType `IMM Asset Calibration` + child `IMM Calibration Measurement` | ✅ |
| `v3_1.add_calibration_fields_to_asset` | `assetcore/patches/v3_1/add_calibration_fields_to_asset.py` ⚠️ | Thêm `calibration_status`, `next_calibration_date`, `last_calibration_date` vào `AC Asset` | ✅ `frappe.db.has_column` check |
| `v3_1.add_calibration_required_to_device_model` | `assetcore/patches/v3_1/add_calibration_required_to_device_model.py` ⚠️ | Thêm `calibration_required`, `calibration_interval_days`, `calibration_type_default` vào `IMM Device Model` | ✅ |
| `v3_1.seed_calibration_sla_policy` | `assetcore/patches/v3_1/seed_calibration_sla_policy.py` ⚠️ | Insert `IMM SLA Policy` cho calibration overdue escalation | ✅ `if not frappe.db.exists` |

Đăng ký trong `assetcore/patches.txt` (thứ tự cố định, không đổi).

### Fixtures cần re-import (khi implement)

```bash
bench --site assetcore.local import-fixtures --app assetcore
```

Fixtures: `Role`, `Role Profile`, `Has Role`, `Workflow` (IMM-11 Calibration Workflow), `Workflow State`, `Workflow Action Master`, `Workspace`, `Custom Field` (AC Asset cal fields, IMM Device Model cal fields).

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
| (không có mới) | — | — | IMM-11 dùng libraries hiện có + Frappe file upload built-in |

### Hooks cần đăng ký (trong `hooks.py`)

⚠️ Pending — thêm khi Sprint 11.3 hoàn thành:

```python
# hooks.py — thêm vào doc_events
doc_events = {
    # ... existing ...
    "IMM Commissioning": {
        "on_submit": "assetcore.services.imm11.create_calibration_schedule_from_commissioning"
    },
    "Asset Repair": {  # IMM-09
        "on_submit": [
            # ... existing handlers ...
            "assetcore.services.imm11.create_post_repair_calibration"
        ]
    }
}

# Schedulers — thêm vào scheduler_events
scheduler_events = {
    # ... existing ...
    "daily": [
        "assetcore.services.imm11.create_due_calibration_wos",     # 06:00
        "assetcore.services.imm11.check_calibration_expiry",        # 06:30
    ]
}
```

## I.4. Deploy Sequence

### Staging (T-1 ngày) — khi implement xong

```bash
# 1. SSH vào staging server
ssh frappe@staging.assetcore.vn

# 2. Bật maintenance mode
bench --site assetcore.local set-maintenance-mode on

# 3. Backup DB
bench --site assetcore.local backup --with-files

# 4. Pull code
cd frappe-bench
git pull origin main

# 5. Setup requirements
./env/bin/pip install -e apps/assetcore

# 6. Frontend build
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore

# 7. Migrate + patches (v3_1.*)
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

### Production — giống staging + thêm

- Chạy trong maintenance window: 23:00 - 02:00 (thứ 6 → thứ 7).
- Backup off-site (S3) ngay trước khi pull code.
- On-call engineer trực từ T đến T+4h.
- Nếu smoke test fail sau 30 phút → rollback ngay (§I.7).

## I.5. Schema Migration Risk

⚠️ Risk assessment dựa trên đặc tả — cần review lại sau khi schema thực tế được thiết kế.

| Thay đổi | Risk | Mitigation |
|---|---|---|
| Tạo DocType mới `IMM Calibration Schedule` | Low | New table; không ảnh hưởng data cũ |
| Tạo DocType mới `IMM Asset Calibration` | Low | New table |
| Tạo child DocType `IMM Calibration Measurement` | Low | New table |
| Thêm custom fields vào `AC Asset` (3 fields) | Low | `frappe.db.add_column` + default null |
| Thêm fields vào `IMM Device Model` | Low | Default null |
| Migrate existing commissioning → tạo Calibration Schedule | Medium | Batch 200/run + idempotent + dry-run staging trước |

**Long-running migration** (create schedules from existing commissioning records):
- Ước tính record: ≤ 500 commissioning records (Wave 1 data).
- Batch size: 200 records/iteration với `frappe.db.commit()` sau mỗi batch.
- Lock policy: Không lock table; chạy trong maintenance mode.
- Dry-run: `--dry-run` flag trên staging trước.

## I.6. Smoke Test Sau Deploy

⚠️ Commands bên dưới hoạt động sau khi module implement xong.

| Step | Cách | Expected |
|---|---|---|
| 1 | Đăng nhập `admin` vào site | Login thành công, hub hiển thị |
| 2 | Mở workspace `IMM Operations` | Workspace load, module IMM-11 có trong sidebar |
| 3 | Mở `/imm-11` (List view) | Danh sách CAL load, không có JS error console |
| 4 | Tạo 1 CAL test (không submit) | Form hiển thị đúng, auto-fill từ asset hoạt động |
| 5 | Gọi `list_calibrations` API | `{"success": true, "data": {...}}` |
| 6 | Gọi `get_calibration_compliance_report` API | Response đúng format |
| 7 | Kiểm tra workflow IMM-11 | `frappe.get_doc("Workflow", "IMM-11 Calibration Workflow")` tồn tại |
| 8 | Kiểm tra custom fields trên AC Asset | `calibration_status`, `next_calibration_date`, `last_calibration_date` tồn tại |
| 9 | Audit trail verify | `verify_audit_chain(some_asset)` = True |
| 10 | Cron jobs registered | `bench --site assetcore.local scheduled-jobs` có `create_due_calibration_wos`, `check_calibration_expiry` |
| 11 | Frontend assets load | `/assets/assetcore/` không 404 |
| 12 | Permission test | Technician login → chỉ thấy CAL được assign |
| 13 | nginx upload test | Upload PDF 20 MB → không lỗi 413 |

## I.7. Rollback Plan

### Trigger conditions

- Login hoàn toàn không được (tất cả users).
- Migration gây data corruption trên `AC Asset` (verify `calibration_status` không null cho assets không có schedule).
- Critical permission bug.
- API 5xx rate > 5% trong 10 phút đầu.

### Quick rollback < 15 phút

```bash
# 1. Bật maintenance mode
bench --site assetcore.local set-maintenance-mode on

# 2. Restore DB từ backup
bench --site assetcore.local restore /path/to/backup_before_deploy.sql.gz

# 3. Checkout commit cũ
git checkout v1.0.0-last-stable

# 4. Rebuild frontend
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore

# 5. Clear cache + restart
bench --site assetcore.local clear-cache
bench restart

# 6. Tắt maintenance mode + verify
bench --site assetcore.local set-maintenance-mode off
```

### Forward fix

Khi đã có user mutation (CAL records tạo trong cửa sổ giữa deploy và rollback):
- Xuất CAL records mới tạo trước khi restore.
- Hotfix branch: `hotfix/imm11-v1.1.1`.

## I.8. Communication

**T-48h — Email trước deploy:**
> Kính gửi người dùng AssetCore,
> Hệ thống sẽ nâng cấp lúc 23:00 [ngày X]. Tính năng mới: Module IMM-11 Hiệu chuẩn. Hệ thống tạm ngừng ~60 phút. Hoàn tất công việc trước 22:30. Liên hệ: [support@hospital.vn]

**T+1h sau deploy:**
> Hệ thống đã hoàn tất nâng cấp v1.1.0. Tính năng mới: Module IMM-11 Hiệu chuẩn. Xem User Guide: [link].

## I.9. Monitoring & Alerting (T+24h)

⚠️ Cấu hình sau khi module deploy.

| Metric | Ngưỡng cảnh báo | Tool |
|---|---|---|
| Error rate API imm11 | > 1% requests 5xx | Nginx log + Frappe error log |
| Upload fail rate (cert PDF) | > 5% | Frappe file upload log |
| API p95 `list_calibrations` | > 2 s | Frappe slow query log |
| DB CPU | > 80% trong 5 phút | Server monitoring |
| Disk usage (certificate PDFs) | > 80% | Server monitoring |
| Scheduler `create_due_calibration_wos` fail | Job không chạy > 26h | Frappe scheduler log |
| Audit chain verify fail | Bất kỳ | Email `IMM System Admin` |

## I.10. Post-deployment Checklist

- [ ] Git tag tạo: `git tag v1.1.0 -m "IMM-11 Calibration General Availability"` ⚠️ Pending
- [ ] Release Notes cập nhật version thực tế + ngày deploy ⚠️ Pending
- [ ] Traceability matrix (`09_Release.md §III`) chốt `Released-in = v1.1.0` ⚠️ Pending
- [ ] Backup config lưu off-site sau deploy thành công
- [ ] Verify nginx body size = 100 MB trên tất cả environments
- [ ] Post-mortem nếu có incident trong maintenance window

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu Trúc QMS Reference

| Cấp | Tên | Vai trò | ID format |
|---|---|---|---|
| QC | Quality Charter | Chính sách chất lượng cấp tổ chức | QC-XXXX |
| PR | Procedure | Quy trình chuẩn (SOP) per module | PR-IMM11-XXX |
| WI | Work Instruction | Hướng dẫn thao tác cho end-user | WI-IMM11-XXX |
| BM | Business Master | Master data + change control | (DocType name) |
| HS | Historical Snapshot | Bản ghi lịch sử không thể sửa | (IMM Audit Trail records) |
| KPI | Key Performance Indicator | Đo lường hiệu quả | KPI-IMM11-XXX |

## II.2. Trace Yêu Cầu Pháp Lý

### NĐ 98/2021/NĐ-CP — Trang thiết bị y tế

| Điều/Khoản | Yêu cầu | Áp lên module qua | Doc/Code reference |
|---|---|---|---|
| Điều 38 — Kiểm định, hiệu chuẩn | Mọi TTBYT đo lường phải được hiệu chuẩn định kỳ | `IMM Calibration Schedule` + scheduler auto-create WO | `services/imm11.py: create_due_calibration_wos()` |
| Điều 39 K.1 — Lab ISO/IEC 17025 | Lab hiệu chuẩn phải được công nhận ISO/IEC 17025 | BR-11-01: `lab_supplier.iso_17025_certified = 1` | `validate_lab_iso_17025()` |
| Điều 39 K.2 — Traceability đo lường | Kết quả đo phải truy xuất về chuẩn quốc gia/quốc tế | `traceability_reference` field bắt buộc (In-House) + accreditation number (External) | VR-11-03, VR-11-07 |
| Điều 40 K.1 — Xử lý thiết bị hiệu chuẩn không đạt | Thiết bị OOT phải ngừng sử dụng ngay | BR-11-02: auto `transition_asset_status(→ Out of Service)` | `handle_calibration_fail()` |
| Điều 40 K.3 — Lưu trữ hồ sơ ≥ 7 năm | Hồ sơ hiệu chuẩn lưu tối thiểu 7 năm | `IMM Asset Calibration` submittable immutable + `IMM Audit Trail` | `services/imm11.py: on_submit` |

### WHO HTM 2025 — Health Technology Management

| Section | Yêu cầu | Áp lên module qua | Code reference |
|---|---|---|---|
| §5.4.2 — Calibration interval | Hiệu chuẩn theo IFU và `calibration_interval_days` | Scheduler tạo WO 30 ngày trước due_date | `create_due_calibration_wos()` |
| §5.4.3 — Lab competence | Lab phải có năng lực được công nhận (ISO/IEC 17025) | BR-11-01 enforce | `validate_lab_iso_17025()` |
| §5.4.4 — Measurement traceability | Kết quả truy xuất về chuẩn | `traceability_reference` / accreditation number | VR-11-07, VR-11-03 |
| §5.4.5 — Fail → CAPA | Thiết bị fail cal phải có CAPA | BR-11-02: `create_capa()` bắt buộc | `handle_calibration_fail()` |
| §5.4.6 — Lookback assessment | Fail 1 asset → assess toàn bộ cùng model | BR-11-03: `perform_lookback_assessment()` | `perform_lookback_assessment()` |
| §6.4 — Record retention | Hồ sơ HTM lưu ≥ 7 năm | Immutable records + audit trail | ISO 13485:4.2.5 enforce |

### ISO 13485:2016 — Medical Devices QMS

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| §7.6 — Control of monitoring and measuring equipment | Thiết bị đo lường phải được hiệu chuẩn định kỳ; kết quả truy xuất | `IMM Calibration Schedule` + `IMM Asset Calibration` lifecycle |
| §8.5.2 — Corrective action | Fail calibration → CAPA bắt buộc | BR-11-02: `handle_calibration_fail()` |
| §8.5.3 — Preventive action | Lookback để phòng ngừa | BR-11-03: `perform_lookback_assessment()` |
| §4.2.5 — Control of records | Hồ sơ hiệu chuẩn bất biến, lưu trữ đủ | BR-11-05: submittable + block cancel |

### ISO/IEC 17025 — Calibration Laboratory Competence

| Section | Yêu cầu | Áp lên module qua |
|---|---|---|
| §6.5 — Metrological traceability | Measurement traceability tới SI units | `traceability_reference` field + accreditation number |
| §7.8.2 — Calibration certificate | Certificate phải có đủ thông tin | BR-11-01: `certificate_file`, `lab_accreditation_number`, `certificate_number` bắt buộc |

### NĐ 86/2016/NĐ-CP — Đo lường

| Điều/Khoản | Yêu cầu | Áp lên module qua |
|---|---|---|
| Điều 14 — Kiểm định, hiệu chuẩn | TTBYT đo lường phải kiểm định/hiệu chuẩn theo ĐLVN | `IMM Calibration Schedule` interval theo IFU + ĐLVN |
| Điều 15 — Cơ quan thực hiện | Lab phải đủ năng lực theo quy định nhà nước | BR-11-01 check `iso_17025_certified` |

## II.3. QMS Artefact Tạo Bởi Module

### PR (Procedure)

⚠️ Pending — tạo sau khi module implement và test pass.

| ID | Tên | Mô tả | Workflow trong code |
|---|---|---|---|
| PR-IMM11-001 ⚠️ | Quy trình lập lịch và thực hiện hiệu chuẩn TTBYT | SOP từ Commissioning đến cert lưu trữ | IMM-11 Calibration Workflow states |
| PR-IMM11-002 ⚠️ | Quy trình xử lý kết quả hiệu chuẩn không đạt (OOT) | SOP OOS + CAPA + Lookback | `handle_calibration_fail()` + CAPA lifecycle |
| PR-IMM11-003 ⚠️ | Quy trình lựa chọn và quản lý lab hiệu chuẩn | SOP vetting lab ISO/IEC 17025 | `AC Supplier` với iso_17025_certified flag |

### WI (Work Instruction)

⚠️ Pending — tạo sau khi User Guide (`09_Release.md`) hoàn chỉnh.

| ID | Tên | Audience | Ref |
|---|---|---|---|
| WI-IMM11-001 ⚠️ | Hướng dẫn tạo phiếu hiệu chuẩn External | IMM Technician | `09_Release.md §I.5.a` |
| WI-IMM11-002 ⚠️ | Hướng dẫn nhập kết quả và upload certificate | IMM Technician | `09_Release.md §I.5.b` |
| WI-IMM11-003 ⚠️ | Hướng dẫn xử lý CAPA và Lookback | IMM QA Officer | `09_Release.md §I.5.c` |
| WI-IMM11-004 ⚠️ | Hướng dẫn xem Compliance Report | IMM Operations Manager | `09_Release.md §I.6` |

### BM (Business Master)

| Master data | Owner thay đổi | Change control |
|---|---|---|
| `AC Supplier` (Calibration Labs, `iso_17025_certified`) | IMM Storekeeper | Fixture + PR review + QMS Officer approval |
| `IMM Device Model` (`calibration_interval_days`, `calibration_required`) | IMM Workshop Lead | DocType change log + QMS Officer |
| `IMM Calibration Schedule` (interval override per asset) | IMM Workshop Lead | `IMM Calibration Schedule` write log |

### HS (Historical Snapshot)

| ID | Source | Retention | Format |
|---|---|---|---|
| HS-IMM11-001 | `IMM Audit Trail` per CAL event | ≥ 7 năm (NĐ98 + ISO 13485) | JSON hash chain, immutable |
| HS-IMM11-002 | `Asset Lifecycle Event` cal events | ≥ 7 năm | Frappe record, no-delete |
| HS-IMM11-003 | `IMM Asset Calibration` submitted record | ≥ 7 năm | Submittable, amend only |
| HS-IMM11-004 | Certificate PDF (`certificate_file`) | ≥ 7 năm | File attachment, no-delete |

### KPI

| ID | Tên | Công thức | Tần suất | Owner báo cáo |
|---|---|---|---|---|
| KPI-IMM11-001 | Calibration Compliance Rate | `Completed on time / Total scheduled × 100%` | Tháng | IMM Operations Manager |
| KPI-IMM11-002 | Out-of-Tolerance (OOT) Rate | `Failed CAL / Total CAL × 100%` | Tháng | IMM QA Officer |
| KPI-IMM11-003 | CAPA Closure Rate (30 ngày) | `Closed within 30d / Total opened × 100%` | Tháng | IMM QA Officer |
| KPI-IMM11-004 | Certificate Coverage | `Assets với cert valid / Total calibratable assets × 100%` | Tuần | IMM Workshop Lead |
| KPI-IMM11-005 | Avg Lead Time (Sent → Cert Received) | `AVG(certificate_date − sent_date)` | Tháng | IMM Workshop Lead |

API: `get_calibration_compliance_report` + `get_due_calibrations` trong `api/imm11.py` ✅ (đã deploy — xem `05_API_Specification.md`).

## II.4. Document Control

Workflow PR/WI qua DocType `Asset Document` (IMM-05):

```
Draft → Reviewed → Approved → Effective → Obsolete
```

- **Change control**: Thay đổi BR-11-01 (tiêu chí lab) hoặc BR-11-04 (cách tính ngày) phải qua PR/WI mới + QMS Officer approve.
- **CAPA linkage**: Nếu PR thay đổi do CAPA từ lookback → link `capa_ref` vào `Asset Document`.

## II.5. Traceability Compliance → Code

⚠️ Pending — điền cột Code/DocType sau khi implement.

| Yêu cầu | Test case | Code/DocType | Audit evidence |
|---|---|---|---|
| NĐ98 Điều 39 K.1 — Lab ISO 17025 | UAT-IMM11-02 (step 2) | BR-11-01: `validate_lab_iso_17025()` ⚠️ | `IMM Asset Calibration.lab_supplier.iso_17025_certified` |
| NĐ98 Điều 40 K.1 — OOT → OOS | UAT-IMM11-04 (step 4) | BR-11-02: `handle_calibration_fail()` ⚠️ | `AC Asset.lifecycle_status = Out of Service` |
| WHO HTM §5.4.6 — Lookback | UAT-IMM11-04 (step 5) | BR-11-03: `perform_lookback_assessment()` ⚠️ | CAPA.lookback_assets |
| BR-11-04 — next_cal = cert_date + interval | UAT-IMM11-03 (step 4) | `handle_calibration_pass()` ⚠️ | `AC Asset.next_calibration_date` |
| ISO 13485 §4.2.5 — Immutable records | UAT-IMM11-07 (step 2, 3) | BR-11-05: block cancel + on_cancel raise ⚠️ | `IMM Asset Calibration` docstatus=1 no-cancel |

## II.6. Audit / Inspection Readiness

Khi auditor đến (Sở Y tế, kiểm tra ISO 13485):

- [ ] Truy xuất toàn bộ hồ sơ cal của 1 asset bất kỳ < 5 phút: `get_asset_calibration_history?asset=...` ⚠️ Pending
- [ ] Verify audit chain 1 click: `verify_audit_chain(asset)` từ console
- [ ] KPI compliance tháng: `/imm-11/report/compliance` → filter theo tháng ⚠️ Pending
- [ ] Certificate archive: `IMM Asset Calibration` list filter status=Passed → download cert files
- [ ] CAPA chưa đóng: `IMM CAPA Record` list filter `status != Closed`
- [ ] Role assignment: User Management → IMM roles
- [ ] Overdue list: Asset list filter `calibration_status = Overdue` ⚠️ Pending

## II.7. Training & Roll-out

⚠️ Pending — thực hiện trước go-live.

| Audience | Nội dung | Thời lượng | WI tham chiếu |
|---|---|---|---|
| IMM Workshop Lead | Tạo schedule, chọn lab, phân công KTV, xem Dashboard | 2h | WI-IMM11-001, WI-IMM11-004 ⚠️ |
| IMM Technician | Gửi lab, nhận cert, nhập measurements, submit | 3h | WI-IMM11-001, WI-IMM11-002 ⚠️ |
| IMM QA Officer | Review CAPA, Lookback, Close CAPA | 2h | WI-IMM11-003 ⚠️ |
| IMM Operations Manager | Xem Compliance Report, Dashboard KPI | 1h | WI-IMM11-004 ⚠️ |

Training record lưu qua DocType `Training Record` (IMM-06). Bắt buộc hoàn tất trước go-live.

## II.8. Risk Register (Compliance)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Thiết bị OOT tiếp tục dùng mà chưa xử lý | Medium | Critical | BR-11-02 auto OOS + CAPA; email alert QA Officer | IMM QA Officer |
| Lab không có ISO/IEC 17025 được chọn | Low | High | BR-11-01 validate `iso_17025_certified = 1` tại service layer | IMM Workshop Lead |
| `next_calibration_date` tính sai (từ due_date thay vì cert_date) | Low | Medium | BR-11-04 enforce tại `handle_calibration_pass()`; unit test | IMM Technician |
| Lookback không phát hiện thiết bị nguy cơ | Low | High | BR-11-03: `perform_lookback_assessment()` bắt buộc; CAPA không Close được khi Pending | IMM QA Officer |
| Certificate PDF không lưu được (disk full, upload lỗi) | Medium | High | nginx max body size 100 MB; disk monitoring alert 80%; S3 backup | DevOps |
| CAPA không được đóng kịp (> 30 ngày) | Medium | Medium | Scheduler `check_capa_overdue` daily; email alert; Dashboard KPI | IMM QA Officer |

## II.9. Sign-off QMS

⚠️ Điền khi QMS review hoàn tất (khi implement xong).

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| QMS Officer | | | |
| Tech Lead | | | |
| Module Owner (IMM-11) | | | |
| (Nếu cần) Legal / Pháp chế | | | |

---

## DoD — Hoàn chỉnh

### I. Deployment Plan
- [x] Pre-deploy checklist đầy đủ (11 mục)
- [x] 5 patch files xác định + đăng ký `patches.txt` flow
- [x] Fixtures cần import liệt kê
- [x] Cấu hình môi trường 3 môi trường (dev/staging/prod)
- [x] nginx max body size 100 MB documented
- [x] Deploy sequence staging + production documented
- [x] Smoke test 13 step (bao gồm upload test)
- [x] Rollback < 15 phút có script
- [x] Communication template documented
- [x] Monitoring 7 metric + ngưỡng alert
- [x] hooks.py registration documented
- [ ] On-call schedule confirmed (fill trước go-live)
- [ ] Patch files thực sự tạo ⚠️ Pending implementation
- [ ] Reviewed bởi DevOps + Tech Lead ⚠️ Pending

### II. QMS Mapping
- [x] NĐ98/2021 ≥ 5 điều khoản đối chiếu
- [x] WHO HTM ≥ 6 section đối chiếu
- [x] ISO 13485 ≥ 4 điều đối chiếu
- [x] ISO/IEC 17025 ≥ 2 section đối chiếu
- [x] NĐ 86/2016 documented
- [x] PR 3 + WI 4 định nghĩa (pending tạo actual)
- [x] HS retention 7 năm cho 4 loại audit-relevant records
- [x] KPI 5 metric có công thức + tần suất + owner
- [x] Audit-readiness checklist ≥ 6 mục
- [x] Training plan cho 4 role
- [x] Risk register 6 mục với mitigation
- [x] Sign-off section sẵn sàng
- [ ] PR/WI documents thực sự tạo ⚠️ Pending
