# IMM-02 — Triển khai & Tuân thủ (Deployment & QMS)

> **Wave 2 — Live.** Patch `assetcore.patches.v3_1.002_install_imm02` đã chạy. Module versioning đi theo `assetcore/__init__.py` (`v3.1.x`).

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường (Tech Spec & Market Analysis)** |
| Phiên bản | 1.0.1 |
| Ngày cập nhật | 2026-05-14 |
| Owner | DevOps + Tech Lead + QMS Officer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [04 Backend Design](./04_Backend_Design.md) |

---

# Phần I — Deployment Plan

## I.1. Pre-deployment Checklist

| Hạng mục | Deadline | Responsible | Status |
|---|---|---|---|
| PR merged, CI green (unit + integration + lint) | T-48h | Dev | ☐ |
| UAT pass (12 scenario, 0 Blocker) | T-48h | QA Lead | ☐ |
| Security sign-off (§III trong 07_Testing_QA) | T-48h | QA/Security | ☐ |
| QMS review pass (§II file này) | T-24h | QMS Officer | ☐ |
| IMM-01 deployed và stable (dependency) | T-48h | Dev Lead | ☐ |
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
| App `assetcore` | v3.1.x (Wave 2 release line) | xem `assetcore/__init__.py` |

> Wave 2 = release line `v3.1` bundle IMM-01 + IMM-02 + IMM-03 cùng lúc (xem `patches.txt`). Không deploy IMM-02 độc lập.

## I.2b. Cấu Hình Môi Trường

| Thành phần | Dev | Staging | Production |
|---|---|---|---|
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| RAM | 8 GB | 16 GB | 32 GB |
| MariaDB buffer pool | 2 GB | 8 GB | 16 GB |
| MariaDB max_connections | 100 | 200 | 300 |
| Redis maxmemory | 512 MB | 2 GB | 4 GB |
| nginx max body size | 10 MB | 10 MB | **10 MB** (cần cho Excel upload bulk import) |
| Backup target | Local | Local + S3 staging | Local + S3 prod + off-site |

## I.3. Deployment Artefacts

### Patch files — Thực tế (Wave 2)

| Patch | File | Mô tả | Idempotent? |
|---|---|---|---|
| `v3_1.002_install_imm02` | `assetcore/patches/v3_1/002_install_imm02.py` | Reload 8 DocType IMM-02 (3 primary + 5 child) qua `frappe.reload_doc`, sau đó upsert `IMM-02 Spec Workflow` (7 states / 9 transitions) + auto-seed `Workflow State` + `Workflow Action Master`. | ✅ — kiểm tra `frappe.db.exists("Workflow", ...)`, set lại states/transitions trước khi save |

Lock-in weights KHÔNG seed qua patch — `DEFAULT_WEIGHTS` được hard-code trong `assetcore.services.imm02` (Protocol 0.30 · Consumable 0.20 · Software 0.20 · Parts 0.15 · Service 0.15). Spec Template DocType chưa tồn tại; field `spec_template_ref` ở `IMM Tech Spec` là `Data` placeholder.

Đăng ký trong `assetcore/patches.txt`:

```
# ── Wave 2 ── IMM-01 / 02 / 03 ──
assetcore.patches.v3_1.001_install_imm01
assetcore.patches.v3_1.002_install_imm02
assetcore.patches.v3_1.003_install_imm03
```

### Fixtures cần re-import

```bash
bench --site assetcore.local import-fixtures --app assetcore
```

Fixtures: `Role`, `Workspace`, `Workflow` (IMM-02 Spec Workflow), `Workflow State`, `Workflow Action Master`, `IMM Lock-in Weight Config`, `IMM Spec Template` (10 templates).

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
| `openpyxl` | Python | ≥ 3.1 | Bulk import requirements từ Excel |
| (Chart.js đã có) | FE | — | LockInRadar dùng Chart.js existing bundle |

Thêm vào `requirements.txt`:
```
openpyxl>=3.1.0
```

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
cd frappe-bench && git pull origin release/wave-2

# 5. Setup requirements (bao gồm openpyxl mới)
./env/bin/pip install -e apps/assetcore

# 6. Frontend build
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore

# 7. Migrate + patches (thứ tự: create_doctypes → install_workflow → seed_weights → seed_templates)
bench --site assetcore.local migrate

# 8. Import fixtures
bench --site assetcore.local import-fixtures --app assetcore

# 9. Clear cache + restart
bench --site assetcore.local clear-cache && bench restart

# 10. Tắt maintenance mode
bench --site assetcore.local set-maintenance-mode off

# 11. Smoke test (§I.6)
```

### Production

- Maintenance window: 23:00 - 02:00 (thứ 6 → thứ 7)
- Backup off-site (S3) ngay trước khi pull code
- On-call engineer trực T → T+4h
- Smoke test fail sau 30 phút → rollback ngay

## I.5. Schema Migration Risk

| Thay đổi | Risk | Mitigation |
|---|---|---|
| Tạo 3 primary DocType mới | Low | `frappe.db.table_exists` guard; không affect tables cũ |
| Tạo 5 child DocType mới | Low | Tách riêng, foreign key chuẩn Frappe |
| Import Workflow 7 states / 8 transitions | Low | `frappe.db.exists` check; không ghi đè |
| Seed 5 lock-in weights | Low | `if not exists` guard |
| Seed 10 spec templates | Low | `if not exists` guard per template |
| Install openpyxl (Python) | Low | `pip install -e` trong maintenance mode |

## I.6. Smoke Test Sau Deploy

| Step | Cách | Expected |
|---|---|---|
| 1 | Login admin vào site | Thành công |
| 2 | Mở workspace `IMM Planning` | Module IMM-02 có trong sidebar |
| 3 | Mở `/imm-02` (Tech Spec List) | Danh sách load, không JS error |
| 4 | Gọi `list_tech_specs` API | `{"success": true, "data": {...}}` |
| 5 | Kiểm tra workflow IMM-02 | `frappe.get_doc("Workflow", "IMM-02 Spec Workflow")` tồn tại |
| 6 | Kiểm tra DEFAULT_WEIGHTS | `python -c "from assetcore.services.imm02 import DEFAULT_WEIGHTS; print(sum(DEFAULT_WEIGHTS.values()))"` = `1.0` (hard-coded, không phải DocType) |
| 7 | Spec Template | `IMM Spec Template` DocType CHƯA tồn tại ở Wave 2 — bỏ qua step này |
| 8 | Gọi `dashboard_kpis` API | Response có 3 field: `by_state`, `avg_lock_in_score`, `backlog_over_30d` (KHÔNG có `total_specs` ở Wave 2) |
| 9 | Test bulk import | Upload Excel 5 rows → imported=5 |
| 10 | Cron jobs registered | `bench scheduled-jobs` có `assetcore.services.imm02.check_overdue_drafts` (daily) và `assetcore.services.imm02.benchmark_freshness_alert` (weekly, theo `hooks.py`) |
| 11 | Permlevel check | HTM Engineer GET spec → không thấy `lock_in_score` |
| 12 | Frontend assets | `/imm-02/dashboard` render, không 404 |

## I.7. Rollback Plan

### Trigger conditions

- Login không được (tất cả users)
- Migration gây data corruption
- Critical permission bug (lock_in_score leak)
- API error rate > 5% trong 10 phút đầu

### Quick rollback < 15 phút

```bash
bench --site assetcore.local set-maintenance-mode on
bench --site assetcore.local restore /path/to/backup_before_deploy.sql.gz
git checkout v1.1.x-last-stable
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore
bench --site assetcore.local clear-cache && bench restart
bench --site assetcore.local set-maintenance-mode off
```

### Forward fix

Hotfix branch: `hotfix/imm02-v1.2.1`. Xuất Tech Spec data trước khi restore nếu có mutation.

## I.8. Communication

**T-48h:** Thông báo nâng cấp v1.2.0 — Module IMM-02 Đặc tả kỹ thuật (Wave 2). Downtime 30-60 phút.

**T+1h:** Hoàn tất nâng cấp. Tính năng mới: Tech Spec, Market Benchmark, Lock-in Risk Assessment. Xem User Guide: [link].

## I.9. Monitoring (T+24h)

| Metric | Ngưỡng | Tool |
|---|---|---|
| Error rate API imm02 | > 1% | Nginx + Frappe error log |
| API p95 `list_tech_specs` | > 1.5s | Frappe slow query log |
| Bulk import timeout | > 10s @ 100 rows | App log |
| Overdue draft scheduler fail | Job > 25h không chạy | Frappe scheduler log |
| Permlevel leak (lock_in_score visible to wrong role) | Bất kỳ | Security alert + immediate rollback |
| Audit chain verify fail | Bất kỳ | Email IMM System Admin |

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu Trúc QMS Reference

| Cấp | Tên | ID format |
|---|---|---|
| QC | Quality Charter | QC-IMMIS-01 |
| PR | Procedure | PR-IMM02-XXX |
| WI | Work Instruction | WI-IMM02-XXX |
| BM | Business Master | (DocType name) |
| HS | Historical Snapshot | (IMM Audit Trail records) |
| KPI | Key Performance Indicator | KPI-IMM02-XXX |

## II.2. Trace Yêu Cầu Pháp Lý

### ISO 13485:2016 — Medical Devices QMS

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| §7.3.2 — Design input | Requirements thiết bị phải được xác định và ghi nhận | `Tech Spec Requirement` child table; mandatory field + test_method |
| §7.3.3 — Design output | Output phải verifiable against input | spec_match_pct trong Benchmark Candidate vs Requirements |
| §7.3.6 — Design verification | Technical spec phải verify được | `test_method` field bắt buộc cho mọi mandatory requirement (VR-02-03) |
| §7.3.7 — Design changes | Thay đổi sau approve phải kiểm soát | BR-02-07: Locked spec chỉ sửa qua Withdraw + Reissue (version bump) |
| §4.2.4 — Control of records | Hồ sơ kỹ thuật lưu trữ đủ | `IMM Tech Spec` submittable + immutable; `IMM Audit Trail` |

### WHO HTA (Health Technology Assessment)

| Section | Yêu cầu | Áp lên module qua |
|---|---|---|
| §4.2 — Comparative analysis | So sánh ≥ 3 model trên thị trường | BR-02-04: Market Benchmark ≥ 3 candidates |
| §4.3 — Technical specification | Spec phải có standard kỹ thuật tham chiếu | `test_method` field cho mỗi requirement |
| §5.1 — Infrastructure | Đánh giá hạ tầng trước mua sắm | BR-02-05: 6 infra domains bắt buộc (G03) |

### WHO Procurement Process Resource Guide

| Chapter | Yêu cầu | Áp lên module qua |
|---|---|---|
| Ch.3 — Specification | ĐKTKT phải mô tả performance + safety + service | requirement groups: Performance, Safety, Service, Compliance |
| Ch.3 §3.4 | ≥ N tiêu chí kỹ thuật bắt buộc với phương pháp kiểm tra | BR-02-02, BR-02-03 (G01) |
| Ch.5 — Market survey | Khảo sát thị trường trước đấu thầu | Market Benchmark ≥ 3 candidates với spec_match + price |

### NĐ 98/2021/NĐ-CP — Trang thiết bị y tế

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| Điều 29 — Đặc tả kỹ thuật | ĐKTKT TTBYT phải cụ thể, không tạo lợi thế độc quyền | BR-02-06: Lock-in Risk Assessment + mitigation khi nguy cơ cao |
| Điều 15.2 — Lưu trữ | Hồ sơ kỹ thuật ≥ 5 năm | `IMM Tech Spec` + `IMM Audit Trail` immutable |

### Luật Đấu thầu 22/2023/QH15

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| Điều 43 — Hồ sơ mời thầu | HSMT phải có ĐKTKT (Technical Spec) | Tech Spec Locked → trigger IMM-03 (cơ sở HSMT) |
| Điều 10 — Đảm bảo cạnh tranh | Không ưu ái thương hiệu cụ thể | spec phải mô tả performance, không ghi thương hiệu; lock-in risk phải kiểm soát |

## II.3. QMS Artefact Tạo Bởi Module

### PR (Procedure)

| ID | Tên | File | Workflow |
|---|---|---|---|
| PR-IMM02-001 | Quy trình soạn thảo thông số kỹ thuật thiết bị y tế | `09_Release.md §I.4` | Tech Spec Workflow Draft→Locked |
| PR-IMM02-002 | Quy trình khảo sát và benchmark thị trường | `09_Release.md §I.5.b` | Reviewing → Benchmarked (G02) |
| PR-IMM02-003 | Quy trình đánh giá và kiểm soát nguy cơ lock-in | `09_Release.md §I.5.c` | Benchmarked → Risk Assessed (G03) |
| PR-IMM02-004 | Quy trình rút và tái phát hành thông số kỹ thuật | `IMM-02_Functional_Specs.md §3.6` | Locked → Withdrawn → Reissue |

### WI (Work Instruction)

| ID | Tên | Audience | File |
|---|---|---|---|
| WI-IMM02-001 | Hướng dẫn tạo và soạn yêu cầu kỹ thuật | HTM Engineer | `09_Release.md §I.5.a` |
| WI-IMM02-002 | Hướng dẫn nhập benchmark thị trường | KH-TC Officer | `09_Release.md §I.5.b` |
| WI-IMM02-003 | Hướng dẫn đánh giá lock-in risk | QA Risk Team | `09_Release.md §I.5.c` |
| WI-IMM02-004 | Hướng dẫn phê duyệt và khóa thông số | VP Block1 | `09_Release.md §I.5.d` |

### HS (Historical Snapshot)

| ID | Source | Retention |
|---|---|---|
| HS-IMM02-001 | `IMM Audit Trail` per Tech Spec | ≥ 5 năm (NĐ98 Điều 15) |
| HS-IMM02-002 | `IMM Tech Spec` submitted (Locked) record | ≥ 5 năm |
| HS-IMM02-003 | `IMM Market Benchmark` submitted record | ≥ 5 năm |
| HS-IMM02-004 | `IMM Lock-in Risk Assessment` submitted record | ≥ 5 năm |

### KPI

| ID | Tên | Công thức | Tần suất | Owner |
|---|---|---|---|---|
| KPI-IMM02-001 | Lead time Draft → Locked | `AVG(lock_date − draft_date)` ngày | Tháng | PTP Khối 1 |
| KPI-IMM02-002 | % Spec có ≥ 3 benchmark | `COUNT(spec benchmark_count≥3) / COUNT(Locked) × 100%` | Tháng | KH-TC |
| KPI-IMM02-003 | Điểm lock-in trung bình | `AVG(lock_in_score)` | Tháng | QA Risk Team |
| KPI-IMM02-004 | Tỷ lệ rework (quay về Draft) | `COUNT(spec returned to Draft) / COUNT(total Drafted) × 100%` | Tháng | HTM Lead |
| KPI-IMM02-005 | % tái sử dụng template | `COUNT(spec with template_ref) / COUNT(total) × 100%` | Quý | Tech Lead |
| KPI-IMM02-006 | Backlog Draft > 30 ngày | `COUNT(spec docstatus=0, age > 30d)` | Tuần | PTP Khối 1 |

## II.4. Risk Register (Compliance)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Spec ghi tên thương hiệu cụ thể → vi phạm đấu thầu | Medium | High | Quy định spec mô tả performance; Lock-in Risk bắt buộc (G04) | QMS Officer + Tech Lead |
| Lock-in score tính sai do weight config sai | Low | Medium | `IMM Lock-in Weight Config` versioned; auto-compute tại service layer; unit test | QMS Officer |
| Benchmark freshness quá hạn → spec lỗi thời | Medium | Medium | Scheduler weekly cảnh báo benchmark > 6 tháng | KH-TC Officer |
| Audit chain bị tamper | Low | Critical | IMM Audit Trail immutable + verify endpoint | IMM QA Officer |
| Permlevel 1 leak (lock_in_score) | Low | High | Frappe permlevel enforcement + automated security test | Tech Lead |
| openpyxl injection qua Excel file | Low | Medium | File type validation (`.xlsx` only), max size 5MB, sandboxed parsing | Tech Lead |

## II.5. Sign-off QMS

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| QMS Officer | | | |
| Tech Lead | | | |
| Module Owner (IMM-02) | | | |
| KH-TC / QA Risk Team | | | |

---

## DoD — Hoàn chỉnh

### I. Deployment Plan
- [x] Pre-deploy checklist đầy đủ (11 mục)
- [x] 4 patch files + đăng ký `patches.txt`
- [x] Fixtures + new Python dependency (openpyxl) documented
- [x] Cấu hình môi trường 3 môi trường
- [x] Deploy sequence staging + production
- [x] Smoke test 12 step
- [x] Rollback < 15 phút có script
- [x] Communication T-48h + T+1h
- [x] Monitoring 6 metric (bao gồm permlevel leak alert)
- [ ] On-call schedule confirmed (fill trước go-live)

### II. QMS Mapping
- [x] ISO 13485 ≥ 5 điều đối chiếu
- [x] WHO HTA ≥ 3 section
- [x] WHO Procurement Guide ≥ 3 chapter
- [x] NĐ 98/2021 ≥ 2 điều
- [x] Luật Đấu thầu 22/2023 ≥ 2 điều
- [x] PR 4 + WI 4 tạo cho major workflows
- [x] HS retention 5 năm (4 HS)
- [x] KPI 6 metric có công thức + tần suất + owner
- [x] Risk register 6 mục với mitigation
- [x] Sign-off section sẵn sàng
