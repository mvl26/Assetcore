# IMM-05 — Triển khai & Tuân thủ (Deployment & QMS)

| Mục | Giá trị |
|---|---|
| Module | **IMM-05 — Asset Document Repository** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | DevOps + Tech Lead + QMS Officer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [Module Overview](./IMM-05_Module_Overview.md) |

---

# Phần I — Deployment Plan

## I.1. Pre-deployment Checklist

Thực hiện trước mỗi window deploy (T = giờ deploy):

| Hạng mục | Deadline | Responsible | Status |
|---|---|---|---|
| PR merged, CI green (unit + integration + lint) | T-48h | Dev | ☐ |
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

| Component | Phiên bản yêu cầu | Phiên bản hiện tại (prod) |
|---|---|---|
| Frappe | v15.x (latest stable) | v15.x |
| Python | 3.11+ | 3.11.x |
| Node.js | 20 LTS | 20.x |
| MariaDB | 10.6+ | 10.6.x |
| Redis | 7.x | 7.x |
| App `assetcore` | v2.0.0 (IMM-05 wave với IMM-04) | (upgrade từ v1.x) |

Cập nhật `assetcore/__init__.py`: IMM-05 deploy cùng wave với IMM-04 — version `2.0.0`.

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
| nginx max body size | **25 MB** (file upload limit IMM-05) | 25 MB | 25 MB |
| Python venv path | `/home/frappe/frappe-bench` | (same) | (same) |
| Bench branch | version-15 | version-15 | version-15 |
| Supervisor programs | 4 (web×2, worker×2) | 6 (web×2, worker×4) | 10 (web×4, worker×6) |
| Backup target | Local `/backups` | Local + S3 `assetcore-staging` | Local + S3 `assetcore-prod` + off-site |
| Domain | `dev.assetcore.local` | `staging.assetcore.vn` | `assetcore.vn` |
| SSL cert | Self-signed | Let's Encrypt | Let's Encrypt (wildcard) |
| Firewall | Dev: open | Staging: 80/443 + 22 only | Prod: 443 only + WAF |
| File storage path | `private/files/` | `private/files/` | `private/files/` |

> **Lưu ý đặc thù IMM-05:** File attachments (PDF/JPG/PNG) lưu trong `private/files/` — không accessible qua public URL. `nginx max body size` phải match với `max_attachments_size` trong `frappe.conf`.

## I.3. Deployment Artefacts

### Patch files

| Patch | File | Mô tả | Idempotent? |
|---|---|---|---|
| `v2_0.add_imm05_asset_document_doctype` | `assetcore/patches/v2_0/add_imm05_asset_document_doctype.py` | Tạo DocType `Asset Document` + 30 fields | ✅ `frappe.db.table_exists` check |
| `v2_0.add_imm05_document_request_doctype` | `assetcore/patches/v2_0/add_imm05_document_request_doctype.py` | Tạo DocType `Document Request` | ✅ |
| `v2_0.add_imm05_required_doc_type_doctype` | `assetcore/patches/v2_0/add_imm05_required_doc_type_doctype.py` | Tạo DocType `Required Document Type` master | ✅ |
| `v2_0.seed_imm05_workflow` | `assetcore/patches/v2_0/seed_imm05_workflow.py` | Import `IMM-05 Document Workflow` JSON (6 states) | ✅ `if not frappe.db.exists("Workflow", ...)` |
| `v2_0.seed_required_document_types_imm05` | `assetcore/patches/v2_0/seed_required_document_types_imm05.py` | Seed CO/CQ/Manual/License/Radiation License master records | ✅ `if not frappe.db.exists` |
| `v2_0.add_asset_completeness_custom_fields` | `assetcore/patches/v2_0/add_asset_completeness_custom_fields.py` | Thêm `custom_doc_completeness_pct`, `custom_document_status`, `custom_nearest_expiry` vào ERPNext Asset | ✅ `frappe.db.has_column` check |

Đăng ký trong `assetcore/patches.txt` (thứ tự cố định, không đổi).

### Fixtures cần re-import

```bash
bench --site assetcore.local import-fixtures --app assetcore
```

Fixtures: `Role`, `Role Profile`, `Has Role`, `Workflow` (IMM-05 Document Workflow), `Workflow State`, `Workflow Action Master`, `Custom Field` (Asset completeness fields), `Workspace`.

### Scheduler registration

Đảm bảo `hooks.py` có scheduler entries sau:

```python
scheduler_events = {
    "daily": [
        "assetcore.tasks.check_document_expiry",       # 00:30
        "assetcore.tasks.update_asset_completeness",    # 01:00
        "assetcore.tasks.check_overdue_document_requests",
    ]
}
```

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
| (không có mới) | — | — | IMM-05 dùng libraries hiện có |

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
git pull origin main

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
# 12. Test scheduler thủ công
bench --site assetcore.local execute assetcore.tasks.check_document_expiry
```

### Production (giống staging + thêm)

- Chạy trong maintenance window: 23:00 - 02:00 (thứ 6 → thứ 7).
- Backup off-site (S3) ngay trước khi pull code.
- Verify nginx `client_max_body_size 25m;` và Frappe `max_file_size` config.
- On-call engineer trực từ T đến T+4h.
- Nếu smoke test fail sau 30 phút → rollback ngay (§I.7).

## I.5. Schema Migration Risk

| Thay đổi | Risk | Mitigation |
|---|---|---|
| Tạo DocType `Asset Document` (mới) | Low | `frappe.db.table_exists` check |
| Tạo DocType `Document Request` (mới) | Low | (same) |
| Tạo DocType `Required Document Type` (mới) | Low | (same) |
| Thêm 3 Custom Fields vào ERPNext Asset | Medium | `frappe.db.has_column` check; nullable fields; no ALTER big table |
| Import Workflow 6 states | Low | guard check |

**Long-running migration:**
- Patch `update_asset_completeness` chạy trên tất cả Assets sau deploy.
- Ước tính: ≤ 500 Assets (Wave 1 dev data).
- Batch size: 200 assets/iteration với `frappe.db.commit()` sau mỗi batch.
- Chạy sau migrate: `bench --site ... execute assetcore.tasks.update_asset_completeness`

## I.6. Smoke Test Sau Deploy

| Step | Cách | Expected |
|---|---|---|
| 1 | Đăng nhập `admin` vào site | Login thành công |
| 2 | Mở workspace `IMM Operations` | Module IMM-05 có trong sidebar |
| 3 | Mở `/app/asset-document` (List view) | Danh sách load, không JS error |
| 4 | Tạo 1 Asset Document test (không submit) | Form hiển thị đúng, visibility selector hiển thị |
| 5 | Gọi `list_documents` API | `{"success": true, "data": {...}}` |
| 6 | Gọi `get_dashboard_stats` API | Response đúng format, KPI fields đầy đủ |
| 7 | Kiểm tra Workflow IMM-05 | `frappe.get_doc("Workflow", "IMM-05 Document Workflow")` tồn tại |
| 8 | Kiểm tra Required Document Type | ≥ 5 records (CO, CQ, Manual, License, Radiation License) |
| 9 | Kiểm tra Custom Fields trên Asset | `custom_doc_completeness_pct`, `custom_document_status` tồn tại |
| 10 | Cron jobs registered | `bench --site ... scheduled-jobs` có `check_document_expiry` + `update_asset_completeness` |
| 11 | File upload test | Upload PDF < 25 MB thành công |
| 12 | Permission test | Clinical Head login → không thấy Internal_Only docs |

## I.7. Rollback Plan

### Trigger conditions

- Login hoàn toàn không được.
- Migration gây data corruption (record count không khớp).
- IMM-04 GW-2 gate hoạt động sai sau deploy (block tất cả hoặc không block gì).
- File upload bị reject không đúng format.
- API 5xx rate > 5% trong 10 phút đầu.

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

Khi đã có user upload documents trong cửa sổ giữa deploy và rollback:
- Xuất Asset Document records trước khi restore.
- Sau hotfix, re-import + re-verify approval workflow.
- Hotfix branch: `hotfix/imm05-v2.0.1`.

## I.8. Communication

**T-48h — Email trước deploy:**
> Kính gửi người dùng AssetCore,
> Hệ thống sẽ nâng cấp lúc 23:00 [ngày X] → 02:00 [ngày X+1]. Tính năng mới: Module IMM-05 Quản lý Hồ sơ Thiết bị (Document Repository). Hệ thống tạm ngừng khoảng 30-60 phút. Liên hệ: [support@hospital.vn]

**Trong deploy — Status:**
> Hệ thống đang bảo trì, dự kiến hoàn thành lúc 02:00. Cập nhật realtime: [status.assetcore.vn]

**T+1h sau deploy — Email hoàn tất:**
> Hệ thống AssetCore đã hoàn tất nâng cấp phiên bản 2.0.0. Tính năng mới: Module IMM-05 Quản lý Hồ sơ Thiết bị — upload, duyệt, cảnh báo hết hạn tự động. Xem User Guide: [link]. Báo lỗi: [support@hospital.vn]

## I.9. Monitoring & Alerting (T+24h)

| Metric | Ngưỡng cảnh báo | Tool |
|---|---|---|
| Error rate API imm05 | > 1% requests 5xx | Nginx log + Frappe error log |
| File upload fail rate | > 5 lần / giờ | Frappe error log |
| Scheduler `check_document_expiry` fail | Job không chạy > 2h | Frappe scheduler log |
| Scheduler `update_asset_completeness` fail | Job không chạy > 24h | Frappe scheduler log |
| DB CPU | > 80% trong 5 phút | htop / CloudWatch |
| Disk usage (private/files/) | > 80% | Server monitoring |
| Documents expired (unexpected batch) | > 20 trong 1 giờ | Email QMS Officer |

## I.10. Post-deployment Checklist

- [ ] Git tag tạo: `git tag v2.0.0 -m "IMM-04 + IMM-05 General Availability — Wave 1"`
- [ ] Release Notes cập nhật version thực tế + ngày deploy
- [ ] Traceability matrix (`09_Release.md §III`) chốt `Released-in = v2.0.0`
- [ ] Backup config lưu off-site sau deploy thành công
- [ ] Chạy `update_asset_completeness` thủ công để khởi tạo completeness cho Assets cũ
- [ ] Post-mortem nếu có incident trong maintenance window

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu Trúc QMS Reference

| Cấp | Tên | Vai trò | ID format |
|---|---|---|---|
| QC | Quality Charter | Chính sách quản lý hồ sơ thiết bị | QC-XXXX |
| PR | Procedure | Quy trình kiểm soát tài liệu per module | PR-IMM05-XXX |
| WI | Work Instruction | Hướng dẫn upload/approve/archive | WI-IMM05-XXX |
| BM | Business Master | Required Document Type master + change control | `Required Document Type` DocType |
| HS | Historical Snapshot | Lịch sử version tài liệu bất biến | `Expiry Alert Log` + Frappe Version |
| KPI | Key Performance Indicator | Tỷ lệ tuân thủ hồ sơ, sắp hết hạn | KPI-IMM05-XXX |

## II.2. Trace Yêu Cầu Pháp Lý

### NĐ98/2021/NĐ-CP — Trang thiết bị y tế

| Điều/Khoản | Yêu cầu | Áp lên module qua | Doc/Code reference |
|---|---|---|---|
| Điều 15.1 — Hồ sơ TTBYT | Lưu đầy đủ hồ sơ kỹ thuật, pháp lý | `Asset Document` per-asset kho hồ sơ tập trung | DocType schema + Required Document Type |
| Điều 15.2 — Lưu trữ ≥ 5 năm | Không xóa hồ sơ trong 5 năm | BR-05-02: `on_trash()` block | `asset_document.py: on_trash()` |
| Điều 18 — Đăng ký lưu hành | TTBYT phải có đăng ký BYT trước sử dụng | BR-05-07: GW-2 gate + `is_expired` block | `_gw2_check_document_compliance()` trong IMM-04 |
| Điều 19 — Cập nhật hồ sơ | Hồ sơ phải cập nhật khi thay đổi | BR-05-01: version control + auto-archive cũ | `archive_old_versions()` |

### Thông tư 46/2017/TT-BYT — Kiểm định TTBYT

| Khoản | Yêu cầu | Áp lên module qua |
|---|---|---|
| Điều 4 — Giấy chứng nhận kiểm định | TTBYT phải có giấy chứng nhận kiểm định hiệu lực | `doc_category = Certification` + expiry tracking + scheduler alert |
| Điều 8 — Chu kỳ kiểm định | Cảnh báo trước khi hết hạn kiểm định | BR-05-03: expiry alert 90/60/30/0 ngày |

### WHO HTM 2025 — Health Technology Management

| Section | Yêu cầu | Áp lên module qua | Code reference |
|---|---|---|---|
| §3.2 — Documentation | Hệ thống lưu trữ tài liệu tập trung per-device | `Asset Document` per-asset + `is_model_level` | DocType fields |
| Annex 7 — Record retention | Tài liệu kỹ thuật lưu suốt vòng đời + 5 năm sau loại bỏ | BR-05-02 + `on_trash` block | `asset_document.py` |
| §6.4 — Document control | Version control, không xóa phiên bản cũ | BR-05-01: archive cũ (không xóa) khi phiên bản mới Active | `archive_old_versions()` |
| §3.4 — Compliance tracking | Theo dõi tỷ lệ tuân thủ hồ sơ theo khoa | `update_asset_completeness()` + `get_compliance_by_dept()` | `tasks.py` + `api/imm05.py` |

### ISO 13485:2016 — Medical Devices QMS

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| §4.2 — Documentation requirements | Document control system bắt buộc | Toàn bộ module IMM-05: workflow + version + audit |
| §4.2.4 — Control of records | Hồ sơ phải readable, identifiable, retrievable | `Asset Document` naming format + `get_document_history()` |
| §4.2.5 — Document control | Approve trước khi effective; phiên bản lỗi thời phải archive | BR-05-01 + workflow Draft→Active + archive old |
| §7.3.10 — DHF/DMR | Device History File và Device Master Record | Per-asset kho hồ sơ + Required Document Type master |

## II.3. QMS Artefact Tạo Bởi Module

### PR (Procedure)

| ID | Tên | File | Workflow trong code |
|---|---|---|---|
| PR-IMM05-001 | Quy trình kiểm soát tài liệu thiết bị y tế | `docs/imm-05/09_Release.md §I.4` | IMM-05 Document Workflow Draft→Active |
| PR-IMM05-002 | Quy trình cảnh báo và gia hạn giấy phép TTBYT | `docs/imm-05/IMM-05_Functional_Specs.md §BR-05-03` | Scheduler 90/60/30/0 ngày |
| PR-IMM05-003 | Quy trình miễn trừ hồ sơ (Exempt NĐ98) | `docs/imm-05/IMM-05_Functional_Specs.md §BR-05-08` | `mark_exempt` API + `is_exempt` flow |

### WI (Work Instruction)

| ID | Tên | Audience | File |
|---|---|---|---|
| WI-IMM05-001 | Hướng dẫn upload và gửi duyệt tài liệu | HTM Technician | `09_Release.md §I.5.a` |
| WI-IMM05-002 | Hướng dẫn phê duyệt và từ chối tài liệu | Biomed Engineer, Tổ HC-QLCL | `09_Release.md §I.5.b` |
| WI-IMM05-003 | Hướng dẫn theo dõi và gia hạn hồ sơ sắp hết hạn | Workshop Head | `09_Release.md §I.6` |
| WI-IMM05-004 | Hướng dẫn xử lý miễn trừ hồ sơ NĐ98 | Tổ HC-QLCL | `09_Release.md §I.5.c` |

### BM (Business Master)

| Master data | Owner thay đổi | Change control |
|---|---|---|
| `Required Document Type` (5 loại) | CMMS Admin + QMS Officer | Fixture + PR review + QMS Officer approval |
| `Asset.custom_document_status` computed field | System (scheduler) | Auto-update, không edit thủ công |
| Visibility policy (`_INTERNAL_ONLY_ROLES`) | Tech Lead | Code review + QMS Officer sign-off |

### HS (Historical Snapshot)

| ID | Source | Retention | Format |
|---|---|---|---|
| HS-IMM05-001 | `Asset Document` Archived/Expired records | ≥ 5 năm (NĐ98 Điều 15) | Frappe record, no-delete |
| HS-IMM05-002 | `Expiry Alert Log` per document | ≥ 5 năm | Frappe record, idempotent |
| HS-IMM05-003 | Frappe `Version` DocType per Asset Document | ≥ 5 năm | Auto-tracked by Frappe |
| HS-IMM05-004 | `IMM Audit Trail` approve/reject events | ≥ 5 năm | JSON hash chain |

### KPI

| ID | Tên | Công thức | Tần suất | Owner báo cáo |
|---|---|---|---|---|
| KPI-IMM05-001 | Tỷ lệ hồ sơ đầy đủ (Completeness) | `COUNT(assets doc_completeness_pct=100) / COUNT(total) × 100%` | Tuần | Workshop Head |
| KPI-IMM05-002 | Số tài liệu sắp hết hạn 30 ngày | `COUNT(Active, days_until_expiry ≤ 30)` | Tuần | QMS Officer |
| KPI-IMM05-003 | Số tài liệu đã hết hạn | `COUNT(workflow_state=Expired)` | Ngày | Workshop Head |
| KPI-IMM05-004 | Thời gian phê duyệt trung bình | `AVG(approval_date - submit_date)` | Tháng | QMS Officer |
| KPI-IMM05-005 | Compliance % theo khoa | `COUNT(Compliant assets) / COUNT(total per dept) × 100%` | Tháng | VP Block2 |

API: `get_dashboard_stats` + `get_compliance_by_dept` trong `api/imm05.py`.

## II.4. Document Control

Module IMM-05 **tự thân là hệ thống document control** — nhưng các PR/WI mô tả IMM-05 được kiểm soát qua:

```
Draft → Pending Review → Active → Archived/Obsolete
```

- **Change control**: Mọi thay đổi `Required Document Type` master (thêm loại hồ sơ mới) → PR review + QMS Officer approval + Fixture update + deploy.
- **CAPA linkage**: Nếu phát hiện hồ sơ bị expire gây sự cố → CAPA record trong IMM-12, link về `Asset Document`.

## II.5. Traceability Compliance → Code

| Yêu cầu | Test case | Code/DocType | Audit evidence |
|---|---|---|---|
| NĐ98 Điều 15.2 — Không xóa hồ sơ | UAT-IMM05-04 | BR-05-02: `on_trash()` raise | Archived doc vẫn tồn tại sau test delete |
| TT 46/2017 — Cảnh báo kiểm định | UAT-IMM05-05 | BR-05-03: `check_document_expiry()` | `Expiry Alert Log` records với alert_level |
| WHO HTM §6.4 — Version control | UAT-IMM05-03 | BR-05-01: `archive_old_versions()` | Old doc `workflow_state = Archived`, `superseded_by` set |
| ISO 13485 §4.2.5 — Approve trước effective | UAT-IMM05-01 | Workflow Draft → Pending Review → Active | `approved_by` + `approval_date` ghi nhận |
| NĐ98 Điều 18 — GW-2 license gate | UAT-IMM05-10 | BR-05-07: `_gw2_check_document_compliance()` | IMM-04 block nếu thiếu Active license |

## II.6. Audit / Inspection Readiness

Khi auditor đến (BYT, Sở Y tế):

- [ ] Truy xuất tài liệu theo asset bất kỳ < 5 phút: `get_asset_documents?asset=ACC-...`
- [ ] Xem lịch sử version: `get_document_history?name=DOC-...`
- [ ] Kiểm tra completeness toàn bộ bệnh viện: `get_dashboard_stats` → `compliance_by_dept`
- [ ] Danh sách hồ sơ sắp hết hạn: `get_expiring_documents?days=90`
- [ ] Verify không có hồ sơ bị xóa (tất cả đều Archived, không missing)
- [ ] GW-2 compliance: `get_compliance_by_dept` → filter assets `document_status = Incomplete`

**URL truy cập nhanh khi audit:**
- Document list: `/app/asset-document`
- Dashboard: `/imm-05/dashboard`
- Expiry report: `/imm-05/expiry-report`

## II.7. Training & Roll-out

| Audience | Nội dung | Thời lượng | WI tham chiếu |
|---|---|---|---|
| HTM Technician | Upload, điền metadata, gửi duyệt | 1h | WI-IMM05-001 |
| Biomed Engineer | Approve/Reject, version control | 1h | WI-IMM05-002 |
| Tổ HC-QLCL | Approve, mark exempt, quản lý license | 2h | WI-IMM05-002, WI-IMM05-004 |
| Workshop Head | Dashboard, cảnh báo hết hạn, cancel/amend | 1h | WI-IMM05-003 |
| VP Block2 | Xem KPI compliance, nhận escalation | 30 phút | WI-IMM05-003 |

Training record lưu qua DocType `Training Record` (IMM-06). Bắt buộc hoàn tất trước go-live.

## II.8. Risk Register (Compliance)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Giấy phép BYT hết hạn mà không ai biết → thiết bị vẫn dùng | Medium | Critical | BR-05-03 scheduler alert 90/60/30/0 ngày + email Workshop Head + Biomed | QMS Officer |
| Hồ sơ bị xóa cứng (mất evidence khi thanh tra) | Low | Critical | BR-05-02 `on_trash` block + no Delete DocPerm | Tech Lead |
| GW-2 bị bypass → thiết bị thiếu license vào vận hành | Low | Critical | BR-05-07 + test UAT-10 + IMM-04 gate test | Tech Lead |
| Internal_Only doc lộ ra ngoài | Low | High | `_apply_visibility_filter()` + test UAT-08 | Tech Lead |
| Version control bị bỏ qua (approve doc mà không archive cũ) | Low | Medium | BR-05-01: `archive_old_versions()` tự động on_approve | Dev |
| Required Document Type master thay đổi không kiểm soát | Low | High | Change control fixture + PR review + QMS approval | CMMS Admin |

## II.9. Sign-off QMS

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| QMS Officer | | | |
| Tech Lead | | | |
| Module Owner (IMM-05) | | | |
| (Nếu cần) Legal / Pháp chế | | | |

---

## DoD — Hoàn chỉnh

### I. Deployment Plan
- [x] Pre-deploy checklist đầy đủ (10 mục)
- [x] 6 patch files + đăng ký `patches.txt`
- [x] Fixtures cần import liệt kê
- [x] Scheduler registration trong `hooks.py` documented
- [x] Cấu hình môi trường 3 môi trường với nginx body size + file storage path
- [x] Deploy sequence staging + production documented
- [x] Smoke test 12 step
- [x] Rollback < 15 phút có script
- [x] Communication template T-48h + trong + T+1h
- [x] Monitoring 7 metric + ngưỡng alert
- [ ] On-call schedule confirmed (fill trước go-live)
- [x] Reviewed bởi DevOps + Tech Lead

### II. QMS Mapping
- [x] NĐ98/2021 ≥ 4 điều khoản đối chiếu
- [x] TT 46/2017/TT-BYT đối chiếu
- [x] WHO HTM ≥ 4 section đối chiếu
- [x] ISO 13485 ≥ 4 điều đối chiếu
- [x] PR 3 + WI 4 tạo cho major workflows
- [x] HS retention 5 năm cho audit-relevant (4 HS)
- [x] KPI 5 metric có công thức + tần suất + owner
- [x] Audit-readiness checklist ≥ 6 mục
- [x] Training plan cho mọi 5 role
- [x] Risk register 6 mục với mitigation
- [x] Sign-off section sẵn sàng
