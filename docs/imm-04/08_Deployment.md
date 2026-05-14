# IMM-04 — Triển khai & Tuân thủ (Deployment & QMS)

| Mục | Giá trị |
|---|---|
| Module | **IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | DevOps + Tech Lead + QMS Officer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [Module Overview](./IMM-04_Module_Overview.md) |

---

# Phần I — Deployment Plan

## I.1. Pre-deployment Checklist

Thực hiện trước mỗi window deploy (T = giờ deploy):

| Hạng mục | Deadline | Responsible | Status |
|---|---|---|---|
| PR merged, CI green (unit + integration + lint) | T-48h | Dev | ☐ |
| UAT pass (12 scenario, 0 Blocker; TC-32 documented workaround) | T-48h | QA Lead | ☐ |
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
| App `assetcore` | v2.0.0 (IMM-04 Wave 1 GA) | (upgrade từ v1.x) |

Cập nhật `assetcore/__init__.py`:
```python
__version__ = "2.0.0"  # IMM-04 General Availability — Wave 1
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
| nginx max body size | **25 MB** (file upload limit IMM-04) | 25 MB | 25 MB |
| Python venv path | `/home/frappe/frappe-bench` | (same) | (same) |
| Bench branch | version-15 | version-15 | version-15 |
| Supervisor programs | 4 (web×2, worker×2) | 6 (web×2, worker×4) | 10 (web×4, worker×6) |
| Backup target | Local `/backups` | Local + S3 `assetcore-staging` | Local + S3 `assetcore-prod` + off-site |
| Domain | `dev.assetcore.local` | `staging.assetcore.vn` | `assetcore.vn` |
| SSL cert | Self-signed | Let's Encrypt | Let's Encrypt (wildcard) |
| Firewall | Dev: open | Staging: 80/443 + 22 only | Prod: 443 only + WAF |

> **Lưu ý:** `nginx max body size` phải là 25 MB để IMM-04 file upload (PDF/TIF ≤ 20 MB) + overhead không bị reject.

## I.3. Deployment Artefacts

### Patch files

| Patch | File | Mô tả | Idempotent? |
|---|---|---|---|
| `v2_0.add_imm04_commissioning_doctype` | `assetcore/patches/v2_0/add_imm04_commissioning_doctype.py` | Tạo DocType `Asset Commissioning` + 3 child tables | ✅ `frappe.db.table_exists` check |
| `v2_0.add_imm04_nc_doctype` | `assetcore/patches/v2_0/add_imm04_nc_doctype.py` | Tạo DocType `Asset QA Non Conformance` | ✅ |
| `v2_0.seed_imm04_workflow` | `assetcore/patches/v2_0/seed_imm04_workflow.py` | Import `IMM-04 Workflow` JSON (11 states) | ✅ `if not frappe.db.exists("Workflow", ...)` |
| `v2_0.add_erpnext_asset_custom_fields` | `assetcore/patches/v2_0/add_erpnext_asset_custom_fields.py` | Thêm `custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref` vào ERPNext Asset | ✅ `frappe.db.has_column` check |
| `v2_0.seed_required_document_types` | `assetcore/patches/v2_0/seed_required_document_types.py` | Insert CO/CQ/Manual/License master data | ✅ `if not frappe.db.exists` |

Đăng ký trong `assetcore/patches.txt` (thứ tự cố định, không đổi).

### Fixtures cần re-import

```bash
bench --site assetcore.local import-fixtures --app assetcore
```

Fixtures: `Role`, `Role Profile`, `Has Role`, `Workflow` (IMM-04 Workflow), `Workflow State`, `Workflow Action Master`, `Custom Field` (ERPNext Asset extensions), `Workspace`.

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
| `qrcode` | Python (BE) | ≥ 7.4 | Sinh QR data cho `_generate_internal_qr()` |
| (Node) | — | — | IMM-04 FE dùng libraries hiện có |

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

# 5. Setup requirements (bao gồm qrcode library)
./env/bin/pip install -e apps/assetcore

# 6. Frontend build
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore

# 7. Migrate + patches
bench --site assetcore.local migrate

# 8. Import fixtures (workflow + custom fields)
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
- Verify nginx `client_max_body_size 25m;` trước khi start.
- On-call engineer trực từ T đến T+4h.
- Nếu smoke test fail sau 30 phút → rollback ngay (§I.7).

## I.5. Schema Migration Risk

| Thay đổi | Risk | Mitigation |
|---|---|---|
| Tạo DocType mới `Asset Commissioning` | Low | `frappe.db.table_exists` check; không ảnh hưởng data cũ |
| Tạo DocType mới `Asset QA Non Conformance` | Low | (same) |
| Thêm Custom Fields vào ERPNext Asset | Medium | `frappe.db.has_column` check; nullable fields |
| Import Workflow 11 states | Low | `if not frappe.db.exists("Workflow", ...)` guard |
| Seed Required Document Type master | Low | `if not frappe.db.exists` guard |

**Long-running migration** (nếu có data cũ cần migrate):
- Không có batch migration cho Wave 1 (IMM-04 là module mới).
- Nếu có Asset records cũ từ test: patch `migrate_legacy_assets` — batch 200/run, idempotent.

## I.6. Smoke Test Sau Deploy

| Step | Cách | Expected |
|---|---|---|
| 1 | Đăng nhập `admin` vào site | Login thành công, hub hiển thị |
| 2 | Mở workspace `IMM Operations` | Module IMM-04 có trong sidebar |
| 3 | Mở `/imm-04` (List view) | Danh sách load, không có JS error console |
| 4 | Tạo 1 Commissioning test (không submit) | Form hiển thị đúng, PO auto-fill hoạt động |
| 5 | Gọi `list_commissionings` API | `{"success": true, "data": {...}}` |
| 6 | Gọi `get_dashboard_stats` API | Response đúng format, có `active_count`, `overdue_count` |
| 7 | Kiểm tra Workflow IMM-04 | `frappe.get_doc("Workflow", "IMM-04 Workflow")` tồn tại, 11 states |
| 8 | Kiểm tra Custom Fields trên Asset | `frappe.db.has_column("Asset", "custom_vendor_serial")` = True |
| 9 | Kiểm tra Required Document Type | ≥ 4 records (CO, CQ, Manual, License) tồn tại |
| 10 | Cron jobs registered | `bench --site ... scheduled-jobs` có `check_commissioning_overdue` |
| 11 | Frontend assets load | `/assets/assetcore/` không 404 |
| 12 | Permission test | Vendor Engineer login → không thấy nút "Phê Duyệt Release" |

## I.7. Rollback Plan

### Trigger conditions

- Login hoàn toàn không được (tất cả users).
- Migration gây data corruption (verify bằng record count trước/sau).
- Critical permission bug (Vendor Engineer thấy được board_approver).
- API 5xx rate > 5% trong 10 phút đầu.
- Clinical Release trigger nhưng Asset không tạo (data loss).

### Quick rollback < 15 phút

```bash
# 1. Bật maintenance mode
bench --site assetcore.local set-maintenance-mode on

# 2. Restore DB từ backup
bench --site assetcore.local restore /path/to/backup_before_deploy.sql.gz

# 3. Checkout commit cũ
git checkout v1.x-last-stable

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

Khi đã có user mutation (Commissioning tạo trong cửa sổ giữa deploy và rollback):
- Xuất Commissioning mới trước khi restore: `bench --site ... export-doctype "Asset Commissioning" ...`
- Sau hotfix, re-import manually.
- Hotfix branch: `hotfix/imm04-v2.0.1`.

## I.8. Communication

**T-48h — Email trước deploy:**
> Kính gửi người dùng AssetCore,
> Hệ thống sẽ nâng cấp lúc 23:00 [ngày X] → 02:00 [ngày X+1]. Tính năng mới: Module IMM-04 Lắp đặt & Nghiệm thu Thiết bị Y tế. Hệ thống tạm ngừng trong khoảng 30-60 phút. Vui lòng hoàn tất công việc trước 22:30. Liên hệ: [support@hospital.vn]

**Trong deploy — Status:**
> Hệ thống đang bảo trì, dự kiến hoàn thành lúc 02:00. Cập nhật realtime: [status.assetcore.vn]

**T+1h sau deploy — Email hoàn tất:**
> Hệ thống AssetCore đã hoàn tất nâng cấp phiên bản 2.0.0. Tính năng mới: Module IMM-04 Lắp đặt, Định danh & Kiểm tra Ban đầu. Xem User Guide: [link]. Báo lỗi: [support@hospital.vn]

## I.9. Monitoring & Alerting (T+24h)

| Metric | Ngưỡng cảnh báo | Tool |
|---|---|---|
| Error rate API imm04 | > 1% requests 5xx | Nginx log + Frappe error log |
| Login fail rate | > 10 lần / phút | Frappe login log |
| API p95 `list_commissionings` | > 2 s | Frappe slow query log |
| API p95 `approve_clinical_release` | > 5 s | Frappe slow query log |
| DB CPU | > 80% trong 5 phút | htop / CloudWatch |
| Disk usage (file attachments) | > 80% | Server monitoring |
| Commissioning overdue > 30 ngày | Bất kỳ | Email Workshop Head (scheduler daily) |
| File upload fail | > 5 lần / giờ | Frappe error log |

## I.10. Post-deployment Checklist

- [ ] Git tag tạo: `git tag v2.0.0 -m "IMM-04 General Availability — Wave 1"`
- [ ] Release Notes cập nhật version thực tế + ngày deploy
- [ ] Traceability matrix (`09_Release.md §III`) chốt cột `Released-in = v2.0.0`
- [ ] Backup config lưu off-site sau deploy thành công
- [ ] Post-mortem nếu có incident trong maintenance window
- [ ] Retro sprint kế: note improvement cho deploy lần sau

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu Trúc QMS Reference

| Cấp | Tên | Vai trò | ID format |
|---|---|---|---|
| QC | Quality Charter | Chính sách chất lượng cấp tổ chức | QC-XXXX |
| PR | Procedure | Quy trình chuẩn per module | PR-IMM04-XXX |
| WI | Work Instruction | Hướng dẫn thao tác end-user | WI-IMM04-XXX |
| BM | Business Master | Master data + change control | (DocType name) |
| HS | Historical Snapshot | Bản ghi lifecycle bất biến | (Asset Lifecycle Event records) |
| KPI | Key Performance Indicator | Đo lường hiệu quả | KPI-IMM04-XXX |

## II.2. Trace Yêu Cầu Pháp Lý

### NĐ98/2021/NĐ-CP — Trang thiết bị y tế

| Điều/Khoản | Yêu cầu | Áp lên module qua | Doc/Code reference |
|---|---|---|---|
| Điều 15.2 — Hồ sơ TTBYT | Lưu trữ hồ sơ thiết bị ≥ 5 năm | `Asset Commissioning` submittable + `Asset Lifecycle Event` immutable | `assetcore/services/imm04.py: log_lifecycle_event()` |
| Điều 5 — Phân loại TTBYT | Thiết bị phân loại đúng rủi ro theo 4 nhóm | `risk_class` field (A/B/C/D/Radiation); auto-populate từ Item | `services/imm04.py: initialize_commissioning()` |
| Điều 12 — Nhập khẩu TTBYT | Mỗi TTBYT nhập khẩu phải có CO/CQ/hồ sơ kỹ thuật | BR-04-02 (G01): CO/CQ/Manual bắt buộc trước Install | `validate_gate_g01()` |
| Điều 18 — Đăng ký lưu hành | Class C/D phải có giấy phép lưu hành BYT trước sử dụng | BR-04-05 (VR-07): auto Clinical Hold + BR-04-08 (GW-2) | `check_auto_clinical_hold()`, `_gw2_check_document_compliance()` |

### Quyết định 3107/QĐ-BYT — Danh mục TTBYT theo rủi ro

| Khoản | Yêu cầu | Áp lên module qua |
|---|---|---|
| Phân loại Class C/D | Thiết bị nguy cơ cao phải qua kiểm định | `risk_class = C` hoặc `D` → Clinical Hold bắt buộc (VR-07) |
| Thiết bị bức xạ | Phải có giấy phép theo NĐ 142/2020 | `risk_class = Radiation` → mandatory `qa_license_doc` |

### WHO HTM 2025 — Health Technology Management

| Section | Yêu cầu | Áp lên module qua | Code reference |
|---|---|---|---|
| §3.2 — Device Identification | UDI / serial tracking bắt buộc | BR-04-03: `vendor_serial_no` unique + `internal_tag` sinh | `_vr01_unique_serial_number()`, `_generate_internal_qr()` |
| §3.4 — Documentation | Bộ hồ sơ kỹ thuật đầy đủ trước deploy | BR-04-02 (G01): CO/CQ/Manual/License | `validate_gate_g01()` |
| §5.1.2 — Incoming Inspection | Kiểm tra an toàn điện (IEC 60601-1) | BR-04-04 (G03): 100% baseline Pass/N/A | `validate_gate_g03()` |
| §5.2 — Commissioning Record | Mỗi thiết bị có phiếu commissioning đầy đủ | `Asset Commissioning` DocType — submittable record | `mint_core_asset()` on_submit |
| §5.3 — Asset Registration | Asset được gán ID nội bộ duy nhất | `internal_tag` format `BV-{DEPT}-{YYYY}-{SEQ}` | `_generate_internal_qr()` |

### ISO 13485:2016 — Medical Devices QMS

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| §7.5 — Product and service provision | Asset chỉ được tạo qua pipeline có kiểm soát | BR-04-01: block tạo Asset trực tiếp ERPNext |
| §7.5.1 — Control of production | Baseline test 100% Pass trước release | BR-04-04 (G03): validate_gate_g03() |
| §8.3 — Control of nonconforming product | NC phải đóng trước khi release | BR-04-06 (G05): validate_gate_g05_g06() |
| §4.2.5 — Control of records | Records phải immutable và traceable | VR-06: lifecycle_events không thể sửa |

### NĐ 142/2020/NĐ-CP — Năng lượng nguyên tử

| Khoản | Yêu cầu | Áp lên module qua |
|---|---|---|
| Thiết bị bức xạ phải có giấy phép | Không được sử dụng lâm sàng khi thiếu giấy phép | BR-04-05 + BR-04-08: Clinical Hold + GW-2 block cho risk_class=Radiation |

## II.3. QMS Artefact Tạo Bởi Module

### PR (Procedure)

| ID | Tên | File | Workflow trong code |
|---|---|---|---|
| PR-IMM04-001 | Quy trình tiếp nhận và nghiệm thu TTBYT | `docs/imm-04/09_Release.md §I.4` (user guide) | IMM-04 Workflow Draft→Clinical Release |
| PR-IMM04-002 | Quy trình kiểm tra an toàn điện TTBYT | `docs/imm-04/IMM-04_Functional_Specs.md §BR-04-04` | Baseline checklist G03 |
| PR-IMM04-003 | Quy trình xử lý không phù hợp (DOA/NC) | `docs/imm-04/IMM-04_Functional_Specs.md §BR-04-06` | Non Conformance → Return To Vendor / Resolve |

### WI (Work Instruction)

| ID | Tên | Audience | File |
|---|---|---|---|
| WI-IMM04-001 | Hướng dẫn tạo phiếu nghiệm thu từ PO | HTM Technician | `09_Release.md §I.5.a` |
| WI-IMM04-002 | Hướng dẫn lắp đặt và gán định danh (QR/serial) | Biomed Engineer | `09_Release.md §I.5.b` |
| WI-IMM04-003 | Hướng dẫn đo kiểm an toàn điện baseline | Biomed Engineer | `09_Release.md §I.5.c` |
| WI-IMM04-004 | Hướng dẫn giữ lâm sàng và gỡ Clinical Hold | QA Officer | `09_Release.md §I.5.d` |
| WI-IMM04-005 | Hướng dẫn phê duyệt phát hành thiết bị | VP Block2 / Board | `09_Release.md §I.5.e` |

### BM (Business Master)

| Master data | Owner thay đổi | Change control |
|---|---|---|
| `Required Document Type` (CO/CQ/Manual/License) | CMMS Admin | Fixture + PR review + QMS Officer approval |
| `Commissioning Checklist Template` per item group | Biomed Engineer | CMMS Admin approve |
| `Item` risk_class field | CMMS Admin | Review + QMS Officer approval |

### HS (Historical Snapshot)

| ID | Source | Retention | Format |
|---|---|---|---|
| HS-IMM04-001 | `Asset Lifecycle Event` per Commissioning | ≥ 5 năm (NĐ98 Điều 15) | Child table JSON, VR-06 immutable |
| HS-IMM04-002 | `IMM Audit Trail` global event `commissioned` | ≥ 5 năm | JSON hash chain |
| HS-IMM04-003 | `Asset Commissioning` submitted record | ≥ 5 năm | Frappe submittable, amend only |
| HS-IMM04-004 | `Commissioning Checklist` baseline results | ≥ 5 năm | Locked child table sau submit |

### KPI

| ID | Tên | Công thức | Tần suất | Owner báo cáo |
|---|---|---|---|---|
| KPI-IMM04-001 | Thời gian nghiệm thu trung bình | `AVG(clinical_release_date - reception_date)` per tháng | Tháng | Workshop Head |
| KPI-IMM04-002 | Tỷ lệ thành công Gate G01 lần đầu | `COUNT(trực tiếp qua G01) / COUNT(tổng)` | Tháng | QA Lead |
| KPI-IMM04-003 | Số phiếu quá hạn 30 ngày | `COUNT(open, reception_date < today-30d)` | Tuần | Workshop Head |
| KPI-IMM04-004 | Tỷ lệ Clinical Hold | `COUNT(Clinical Hold) / COUNT(tổng) × 100%` | Tháng | QA Officer |
| KPI-IMM04-005 | Tỷ lệ Return To Vendor | `COUNT(Return To Vendor) / COUNT(tổng) × 100%` | Tháng | Workshop Head |

API: `get_dashboard_stats` trong `api/imm04.py`.

## II.4. Document Control

Workflow PR/WI qua DocType `Asset Document` (IMM-05):

```
Draft → Pending Review → Active → Archived/Obsolete
```

- **Change control**: Mọi thay đổi PR/WI tạo phiên bản mới; phiên bản cũ chuyển Archived.
- **CAPA linkage**: Nếu PR thay đổi do phát hiện lỗi hệ thống → link `capa_ref` vào `Asset Document`.
- **Training**: Khi PR/WI Active → trigger training notification cho audience (IMM-06).

## II.5. Traceability Compliance → Code

| Yêu cầu | Test case | Code/DocType | Audit evidence |
|---|---|---|---|
| NĐ98 Điều 12 — CO/CQ bắt buộc | UAT-IMM04-03 | BR-04-02: `validate_gate_g01()` | `Commissioning Document Record.status = Received` |
| NĐ98 Điều 18 — Giấy phép lưu hành | UAT-IMM04-06 | BR-04-05: `check_auto_clinical_hold()` | Clinical Hold state + License document uploaded |
| WHO HTM §3.2 — Serial unique | UAT-IMM04-04 | BR-04-03: `_vr01_unique_serial_number()` | `Asset.custom_vendor_serial` unique |
| WHO HTM §5.1.2 — Baseline test | UAT-IMM04-05 | BR-04-04: `validate_gate_g03()` | `Commissioning Checklist` all Pass |
| ISO 13485 §7.5 — Asset qua pipeline | UAT-IMM04-02 | BR-04-01: `AssetCommissioning.on_submit()` | `final_asset` link + `Asset.source = IMM-04` |

## II.6. Audit / Inspection Readiness

Khi auditor đến (cơ quan y tế, BYT):

- [ ] Truy xuất phiếu nghiệm thu theo asset bất kỳ < 5 phút: `get_commissioning?name=ACC-...`
- [ ] Verify serial number history 1 click: `get_barcode_lookup?sn=...`
- [ ] Clinical Hold history: filter Commissioning by `workflow_state = Clinical Hold`
- [ ] Document completeness: tab Documents → xem CO/CQ/Manual/License status
- [ ] NC history: `Asset QA Non Conformance` list filter `ref_commissioning = ACC-...`
- [ ] Baseline test results: tab Checklist (read-only) với measured values
- [ ] Lifecycle Events timeline: mọi state change đều có actor + timestamp

**URL truy cập nhanh khi audit:**
- Commissioning list: `/imm-04`
- Dashboard: `/imm-04/dashboard`
- NC list: Admin → `Asset QA Non Conformance`

## II.7. Training & Roll-out

| Audience | Nội dung | Thời lượng | WI tham chiếu |
|---|---|---|---|
| HTM Technician | Tạo phiếu từ PO, upload tài liệu | 2h | WI-IMM04-001 |
| Biomed Engineer | Lắp đặt, gán SN/QR, đo baseline, trigger transition | 3h | WI-IMM04-002, WI-IMM04-003 |
| Vendor Engineer | Xác nhận lắp đặt, báo DOA, portal workflow | 1h | WI-IMM04-002 §vendor |
| QA Officer | Clinical Hold, upload license, gỡ Hold | 1h | WI-IMM04-004 |
| VP Block2 / Board | Phê duyệt release, xem KPIs | 1h | WI-IMM04-005 |
| Workshop Head | Submit/Cancel/Amend, Dashboard | 1h | WI-IMM04-005 §mgmt |

Training record lưu qua DocType `Training Record` (IMM-06). Bắt buộc hoàn tất trước go-live.

## II.8. Risk Register (Compliance)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Asset tạo trực tiếp bỏ qua pipeline IMM-04 (không trace được) | Medium | Critical | BR-04-01: block `Asset.validate()` nếu không có `custom_comm_ref` | Tech Lead |
| Thiết bị Class C/D được dùng lâm sàng trước khi có giấy phép | Low | Critical | BR-04-05 + VR-07: Clinical Hold tự động; GW-2 gate block Submit | QA Officer |
| Serial Number trùng → không trace được history sau sự cố | Medium | High | VR-01: unique check at insert + before_submit | Biomed Engineer |
| Baseline test giả mạo kết quả (ghi Pass nhưng thực tế Fail) | Low | Critical | Checklist locked sau submit; audit trail actor; VR-06 immutable | QA Officer |
| Vendor Engineer truy cập dữ liệu nhạy cảm | Low | Medium | Role restriction + permlevel; Vendor chỉ thấy state Installing/TBI | CMMS Admin |
| Commissioning bị cancel sau khi Asset đã dùng lâm sàng | Low | High | `handle_commissioning_cancel()`: block nếu `final_asset` tồn tại | Tech Lead |

## II.9. Sign-off QMS

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| QMS Officer | | | |
| Tech Lead | | | |
| Module Owner (IMM-04) | | | |
| (Nếu cần) Legal / Pháp chế | | | |

---

## DoD — Hoàn chỉnh

### I. Deployment Plan
- [x] Pre-deploy checklist đầy đủ (10 mục)
- [x] 5 patch files + đăng ký `patches.txt`
- [x] Fixtures cần import liệt kê
- [x] Cấu hình môi trường 3 môi trường (dev/staging/prod) với nginx body size 25 MB
- [x] Deploy sequence staging + production documented
- [x] Smoke test 12 step
- [x] Rollback < 15 phút có script
- [x] Communication template T-48h + trong + T+1h
- [x] Monitoring 8 metric + ngưỡng alert
- [ ] On-call schedule confirmed (fill trước go-live)
- [x] Reviewed bởi DevOps + Tech Lead

### II. QMS Mapping
- [x] NĐ98/2021 ≥ 4 điều khoản đối chiếu
- [x] NĐ 142/2020 (bức xạ) đối chiếu
- [x] WHO HTM ≥ 5 section đối chiếu
- [x] ISO 13485 ≥ 4 điều đối chiếu
- [x] PR 3 + WI 5 tạo cho major workflows
- [x] HS retention 5 năm cho audit-relevant (4 HS)
- [x] KPI 5 metric có công thức + tần suất + owner
- [x] Audit-readiness checklist ≥ 6 mục
- [x] Training plan cho mọi 6 role
- [x] Risk register 6 mục với mitigation
- [x] Sign-off section sẵn sàng
