# IMM-01 — Triển khai & Tuân thủ (Deployment & QMS)

> **Wave 2 — Live.** Patch `assetcore.patches.v3_1.001_install_imm01` đã merge và đang là phần của bench migrate path. Fixtures workflow IMM-01 (Needs + Plan) đã ship qua `assetcore/fixtures/workflow.json`.

| Mục | Giá trị |
|---|---|
| Module | **IMM-01 — Đánh giá Nhu cầu & Dự toán (Needs Assessment & Budget Estimation)** |
| Phiên bản | 1.0.0 (Wave 2 GA) |
| Ngày cập nhật | 2026-05-14 |
| Owner | DevOps + Tech Lead + QMS Officer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [README](./README.md) |

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
| App `assetcore` | v1.1.0 (IMM-01 GA, Wave 2) | v1.0.x (Wave 1) |

Cập nhật `assetcore/__init__.py`:
```python
__version__ = "1.1.0"  # IMM-01 General Availability — Wave 2
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
| Firewall | Dev: open | Staging: 80/443 + 22 only | Prod: 443 only + WAF |

## I.3. Deployment Artefacts

### Patch files (thực tế)

| Patch | File | Mô tả | Idempotent? |
|---|---|---|---|
| `v3_1.001_install_imm01` | `assetcore/patches/v3_1/001_install_imm01.py` | Reload 7 DocType (3 primary + 4 child) + upsert 2 workflow JSON từ `assetcore/assetcore/workflow/`: `imm_01_needs_workflow.json`, `imm_01_plan_workflow.json` | ✅ Re-run an toàn — workflow upsert thủ công |

Đăng ký trong `assetcore/patches.txt`:

```
# ── Wave 2 ── IMM-01 / 02 / 03 ─────────────────────────────────────────
assetcore.patches.v3_1.001_install_imm01
assetcore.patches.v3_1.002_install_imm02
assetcore.patches.v3_1.003_install_imm03
assetcore.patches.v3_1.004_seed_assetcore_role_profiles
assetcore.patches.v3_1.005_remove_legacy_imm_role_profiles
```

> Không có patch riêng `seed_priority_weights` — trọng số 6 tiêu chí hardcoded ở `DEFAULT_PRIORITY_WEIGHTS` trong `services/imm01.py` (chưa tách thành master DocType). Cũng không có `backfill_replacement_links` (đó là roadmap khi go-live khách hàng có data legacy).

### Fixtures cần re-import

```bash
bench --site <site> migrate
bench --site <site> import-fixtures --app assetcore   # Frappe v15: hooks fixtures auto-sync khi migrate
```

Fixtures hiện có (xem `assetcore/fixtures/`): `Role` (22 roles), `Role Profile`, `Module Profile`, `IMM SLA Policy`, `Workspace`, `Workflow` (incl. `IMM-01 Needs Workflow`, `IMM-01 Plan Workflow`), `Workflow State`, `Workflow Action Master`. Không có `IMM Priority Weight Config` fixture (weights hardcoded).

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
| (không có mới) | — | — | IMM-01 dùng libraries hiện có; chart heatmap dùng Chart.js đã bundle |

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
git pull origin release/wave-2

# 5. Setup requirements
./env/bin/pip install -e apps/assetcore

# 6. Frontend build
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore

# 7. Migrate + patches (thứ tự: create_doctypes → install_workflow → seed_weights → backfill)
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
- Thông báo người dùng T-48h (email + thông báo in-app).

## I.5. Schema Migration Risk

| Thay đổi | Risk | Mitigation |
|---|---|---|
| Tạo mới `IMM Needs Request` (table mới) | Low | `frappe.db.table_exists` check; không affect table cũ |
| Tạo mới `IMM Procurement Plan` (table mới) | Low | (same) |
| Tạo mới `IMM Demand Forecast` (table mới) | Low | (same) |
| Tạo 4 child tables mới | Low | Tách riêng, foreign key chuẩn Frappe |
| Import Workflow (2 workflow mới) | Low | `frappe.db.exists` check; không ghi đè workflow cũ |
| Seed 6 Priority Weight Config | Low | `if not exists` guard; idempotent |
| Backfill replacement links (batch 100) | Medium | Batch 100/run + `frappe.db.commit()` sau mỗi batch; dry-run staging trước; log failures |

**Long-running patch** (`backfill_replacement_links`):
- Ước tính record: ≤ 500 `IMM Needs Request` (Wave 2 dev/staging data).
- Batch size: 100 records/iteration với commit sau mỗi batch.
- Lock policy: Không lock table; chạy trong maintenance mode.
- Dry-run: `--dry-run` flag trên staging → xem log không có error.

## I.6. Smoke Test Sau Deploy

| Step | Cách | Expected |
|---|---|---|
| 1 | Đăng nhập `admin` vào site | Login thành công, hub hiển thị |
| 2 | Mở workspace `IMM Planning` | Workspace load, module IMM-01 có trong sidebar |
| 3 | Mở `/imm-01` (List Needs Requests) | Danh sách load, không có JS error console |
| 4 | Tạo 1 Needs Request test (không submit) | Form hiển thị đúng, Priority Score section hiện |
| 5 | Gọi `list_needs_requests` API | `{"message": {"success": true, "data": {...}}}` |
| 6 | Gọi `score_needs_request` với NR mẫu + 6 scoring rows | Response có `weighted_score`, `priority_class` |
| 7 | Gọi `dashboard_kpis` API | Response có `backlog_over_30d`, `by_state`, `g01_pass_rate`, `envelope_utilization` |
| 8 | Kiểm tra workflow IMM-01 | `frappe.get_doc("Workflow", "IMM-01 Needs Workflow")` tồn tại; cũng `IMM-01 Plan Workflow` |
| 9 | Kiểm tra Priority Weights | (Hardcoded `DEFAULT_PRIORITY_WEIGHTS` trong service — không có DocType riêng) |
| 10 | Audit trail verify | Tạo NR Replacement → Approve → `IMM Audit Trail` ghi (vì có `replacement_for_asset`). Với New: chỉ Frappe Version. |
| 11 | Cron jobs registered | `bench --site <site> scheduler --help` + `bench show-scheduler-events` có `check_pending_request_overdue` (daily), `budget_envelope_alert` (weekly), `generate_demand_forecast` (monthly) |
| 12 | Frontend assets load | `/needs-requests` và `/procurement-plans` render qua Vue Router |

## I.7. Rollback Plan

### Trigger conditions

- Login hoàn toàn không được (tất cả users).
- Migration gây data corruption (verify bằng record count trước/sau).
- Critical permission bug (user thấy data không được phép).
- API error rate > 5% trong 10 phút đầu.
- Workflow IMM-01 không tồn tại sau migrate.

### Quick rollback < 15 phút

```bash
# 1. Bật maintenance mode
bench --site assetcore.local set-maintenance-mode on

# 2. Restore DB từ backup
bench --site assetcore.local restore /path/to/backup_before_deploy.sql.gz

# 3. Checkout commit cũ (Wave 1 stable)
git checkout v1.0.x-last-stable

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

Khi đã có user mutation (NR tạo trong cửa sổ giữa deploy và rollback):
- Xuất NR mới tạo trước khi restore: `bench --site ... export-doctype "IMM Needs Request" ...`
- Sau hotfix, re-import manually.
- Hotfix branch: `hotfix/imm01-v1.1.1`.

## I.8. Communication

**T-48h — Email trước deploy:**
> Kính gửi người dùng AssetCore,
> Hệ thống sẽ nâng cấp lúc 23:00 [ngày X] → 02:00 [ngày X+1]. Tính năng mới: Module IMM-01 Đánh giá Nhu cầu & Dự toán (Wave 2). Hệ thống tạm ngừng trong khoảng 30-60 phút. Vui lòng hoàn tất công việc trước 22:30. Liên hệ: [support@hospital.vn]

**Trong deploy — Status:**
> Hệ thống đang bảo trì, dự kiến hoàn thành lúc 02:00. Cập nhật realtime: [status.assetcore.vn]

**T+1h sau deploy — Email hoàn tất:**
> Hệ thống AssetCore đã hoàn tất nâng cấp phiên bản 1.1.0 — Wave 2. Tính năng mới: Module IMM-01 Đánh giá Nhu cầu & Dự toán. Xem User Guide: [link]. Báo lỗi: [support@hospital.vn]

## I.9. Monitoring & Alerting (T+24h)

| Metric | Ngưỡng cảnh báo | Tool |
|---|---|---|
| Error rate API imm01 | > 1% requests lỗi | Nginx log + Frappe error log |
| Login fail rate | > 10 lần / phút | Frappe login log |
| API p95 `list_needs_requests` | > 2 s | Frappe slow query log |
| DB CPU | > 80% trong 5 phút | Server monitoring (htop / CloudWatch) |
| Disk usage | > 80% | Server monitoring |
| Audit chain verify fail | Bất kỳ | Email `IMM System Admin` |
| Demand forecast scheduler fail | Job không chạy > 25h | Frappe scheduler log |
| NR overdue scheduler fail | Job không chạy > 25h | Frappe scheduler log |

## I.10. Post-deployment Checklist

- [ ] Git tag tạo: `git tag v1.1.0 -m "IMM-01 General Availability — Wave 2"`
- [ ] Release Notes cập nhật version thực tế + ngày deploy
- [ ] Traceability matrix (`09_Release.md §III`) chốt cột `Released-in = v1.1.0`
- [ ] Backup config lưu off-site sau deploy thành công
- [ ] Post-mortem nếu có incident trong maintenance window
- [ ] Retro sprint kế: note improvement cho deploy lần sau

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu Trúc QMS Reference

| Cấp | Tên | Vai trò | ID format |
|---|---|---|---|
| QC | Quality Charter | Chính sách chất lượng cấp tổ chức | QC-IMMIS-01 |
| PR | Procedure | Quy trình chuẩn (SOP) per module | PR-IMM01-XXX |
| WI | Work Instruction | Hướng dẫn thao tác cho end-user | WI-IMM01-XXX |
| BM | Business Master | Master data + change control | (DocType name) |
| HS | Historical Snapshot | Bản ghi lịch sử không thể sửa | (IMM Audit Trail records) |
| KPI | Key Performance Indicator | Đo lường hiệu quả | KPI-IMM01-XXX |

## II.2. Trace Yêu Cầu Pháp Lý

### NĐ 98/2021/NĐ-CP — Trang thiết bị y tế

| Điều/Khoản | Yêu cầu | Áp lên module qua | Doc/Code reference |
|---|---|---|---|
| Điều 32 — Kế hoạch đầu tư TTBYT | Lập kế hoạch đầu tư TTBYT theo năm dựa trên nhu cầu thực tế và năng lực tài chính | `IMM Procurement Plan` Approved → cơ sở lập kế hoạch đầu tư | `services/imm01.py: validate_procurement_plan()` |
| Điều 15.2 — Hồ sơ TTBYT | Lưu trữ hồ sơ thiết bị ≥ 5 năm | `IMM Audit Trail` immutable hash chain | `assetcore/utils/lifecycle.py` |
| Điều 29 — Điều kiện nhập khẩu | Thiết bị nhập khẩu phải đăng ký lưu hành → Cần đặc tả kỹ thuật trước | BR-01-01: Procurement Plan Approved trước khi chuyển IMM-02 (Spec) | `validate_gate_g03()` + `on_submit_procurement_plan()` |
| Điều 3.9 — Phân loại TTBYT | Đề xuất thiết bị phải ghi rõ phân loại (Class I/II/III/IV) | `device_class` field bắt buộc trên `IMM Needs Request` | `_vr02()` validates device_class |

### Luật Đấu thầu 22/2023/QH15

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| Điều 4 — Phạm vi áp dụng | Mua sắm TTBYT từ nguồn ngân sách phải qua đấu thầu | `funding_source` field + BR-01-05: PP cần nguồn vốn rõ ràng trước phê duyệt |
| Điều 38 — Kế hoạch lựa chọn nhà thầu | Lập kế hoạch lựa chọn nhà thầu trước khi tổ chức đấu thầu | `IMM Procurement Plan` Approved → đầu vào cho IMM-03 (Vendor Eval) |
| Điều 43 — Yêu cầu về HSMT | Hồ sơ mời thầu phải có ĐKTKT (Technical Spec) | PP Approved → trigger tạo Tech Spec IMM-02 |

### WHO HTM 2025 — Health Technology Management

| Section | Yêu cầu | Áp lên module qua | Code reference |
|---|---|---|---|
| §3.2 — Needs Assessment Process | Quy trình đánh giá nhu cầu đa tiêu chí, có tính đến clinical impact, risk, utilization | 6-criteria priority scoring (clinical_impact, risk, utilization_gap, replacement_signal, compliance_gap, budget_fit) | `compute_priority_score()` |
| §2.4 — Technology Selection | Lựa chọn thiết bị phải dựa trên nhu cầu được phê duyệt | BR-01-01: PP Approved trước khi sang IMM-02 | `validate_gate_g03()` |
| Annex 4 — Replacement Criteria | Tiêu chí thay thế dựa trên tuổi thọ, sửa chữa thường xuyên, obsolescence | `request_type = "Thay thế"` + `asset_to_replace` link + replacement signal score | `_vr04()` validates replacement fields |
| §6.4 — Budget Planning | Ngân sách đầu tư phải có CAPEX + OPEX | `IMM Budget Estimate` child table: capex_unit, opex_year_1-5 | `validate_budget_estimate()` |
| §4.1 — Procurement Plan | Nhu cầu phê duyệt phải được gom vào kế hoạch tổng thể | `IMM Procurement Plan` groups approved NR | `roll_into_procurement_plan()` |

### ISO 13485:2016 — Medical Devices QMS

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| §7.1 — Planning of product realization | Kế hoạch đầu tư thiết bị phải dựa trên yêu cầu nghiệp vụ được phê duyệt | `IMM Needs Request` + `IMM Procurement Plan` workflow có gate G03 (PP Approved) |
| §4.2.5 — Control of records | Hồ sơ đánh giá nhu cầu lưu trữ đủ, có thể truy xuất | `IMM Needs Request` submittable + immutable; `IMM Audit Trail` per record |
| §7.3.2 — Design and development inputs | Technical requirements được xác định trước khi phát triển/mua sắm | PP Approved → IMM-02 Tech Spec; Spec must reference Procurement Plan |

## II.3. QMS Artefact Tạo Bởi Module

### PR (Procedure)

| ID | Tên | File | Workflow trong code |
|---|---|---|---|
| PR-IMM01-001 | Quy trình tiếp nhận và đánh giá nhu cầu thiết bị y tế | `docs/imm-01/09_Release.md §I.4` (user guide) | IMM-01 Needs Request Workflow states Draft→Approved |
| PR-IMM01-002 | Quy trình lập và phê duyệt kế hoạch mua sắm thiết bị | `docs/imm-01/IMM-01_Functional_Specs.md §US-01-030` | IMM-01 Procurement Plan Workflow states Draft→Approved |
| PR-IMM01-003 | Quy trình dự báo nhu cầu và lập kế hoạch dài hạn | `docs/imm-01/IMM-01_Functional_Specs.md §US-01-040` | Scheduler monthly + `generate_demand_forecast()` |

### WI (Work Instruction)

| ID | Tên | Audience | File |
|---|---|---|---|
| WI-IMM01-001 | Hướng dẫn tạo phiếu đề xuất nhu cầu thiết bị | Trưởng khoa lâm sàng | `09_Release.md §I.5.a` |
| WI-IMM01-002 | Hướng dẫn chấm điểm ưu tiên và dự toán ngân sách | HTM Reviewer | `09_Release.md §I.5.b` |
| WI-IMM01-003 | Hướng dẫn lập và duyệt kế hoạch mua sắm | Phó Giám đốc / KH-TC | `09_Release.md §I.5.c` |
| WI-IMM01-004 | Hướng dẫn xem Dashboard và báo cáo dự báo nhu cầu | Phó Trưởng phòng VTTBYT | `09_Release.md §I.6` |

### BM (Business Master)

| Master data | Owner thay đổi | Change control |
|---|---|---|
| `IMM Priority Weight Config` (6 bộ trọng số) | Tech Lead + QMS Officer | Fixture + PR review + QMS Officer approval + versioning |
| `AC Asset` (thiết bị nguồn thay thế) | IMM Workshop Lead | `AC Asset Lifecycle` workflow |
| `AC Department` (khoa phòng đề xuất) | HR/Admin | Frappe standard |

### HS (Historical Snapshot)

| ID | Source | Retention | Format |
|---|---|---|---|
| HS-IMM01-001 | `IMM Audit Trail` per Needs Request | ≥ 5 năm (NĐ98 Điều 15) | JSON hash chain, immutable |
| HS-IMM01-002 | `IMM Audit Trail` per Procurement Plan | ≥ 5 năm | Frappe record, no-delete |
| HS-IMM01-003 | `IMM Needs Request` submitted record | ≥ 5 năm | Frappe submittable, amend only |
| HS-IMM01-004 | `IMM Demand Forecast` published record | ≥ 5 năm | Frappe record, no-delete |

### KPI

| ID | Tên | Công thức | Tần suất | Owner báo cáo |
|---|---|---|---|---|
| KPI-IMM01-001 | Tỷ lệ nhu cầu được phê duyệt | `COUNT(NR status=Approved) / COUNT(NR submitted) × 100%` | Tháng | IMM Operations Manager |
| KPI-IMM01-002 | Tỷ lệ ưu tiên P1 trong kế hoạch | `COUNT(PP lines priority_class=P1) / COUNT(PP lines) × 100%` | Quý | KH-TC / TCKT |
| KPI-IMM01-003 | Thời gian trung bình từ tạo NR đến phê duyệt | `AVG(approved_date - creation)` tính bằng ngày | Tháng | IMM Operations Manager |
| KPI-IMM01-004 | Tỷ lệ NR quá hạn xử lý | `COUNT(NR overdue) / COUNT(NR pending) × 100%` | Tuần | IMM Department Head |
| KPI-IMM01-005 | Độ lệch dự báo vs thực tế | `ABS(forecast_qty - actual_qty) / forecast_qty × 100%` per device class | Năm | IMM Operations Manager |
| KPI-IMM01-006 | Tỷ lệ PP chuyển sang Spec đúng hạn | `COUNT(PP → IMM-02 in ≤ 30 days) / COUNT(PP Approved) × 100%` | Quý | Tech Lead + KH-TC |

API: `get_dashboard_kpis` trong `api/imm01.py`.

## II.4. Document Control

Workflow PR/WI qua DocType `Asset Document` (IMM-05):

```
Draft → Reviewed → Approved → Effective → Obsolete
```

- **Change control**: Mọi thay đổi PR/WI tạo phiên bản mới; phiên bản cũ chuyển Obsolete.
- **Priority weight change control**: Thay đổi `IMM Priority Weight Config` → tạo version mới + QMS Officer sign-off + re-run scoring cho NR Draft hiện tại.
- **CAPA linkage**: Nếu PR thay đổi do CAPA → link `capa_ref` vào `Asset Document`.
- **Training**: Khi PR/WI Effective → trigger training notification cho audience (IMM-06).

## II.5. Traceability Compliance → Code

| Yêu cầu | Test case | Code/DocType | Audit evidence |
|---|---|---|---|
| NĐ98 Điều 32 — Kế hoạch đầu tư | UAT-IMM01-08, UAT-IMM01-09 | `validate_procurement_plan()` + Gate G03 | `IMM Procurement Plan` submitted record |
| NĐ98 Điều 15.2 — Lưu trữ ≥ 5 năm | `test_audit_trail_logged_on_submit` | `IMM Audit Trail` immutable | `verify_audit_chain()` pass |
| WHO HTM §3.2 — Multi-criteria scoring | UAT-IMM01-02, UAT-IMM01-03 | `compute_priority_score()` | `IMM Needs Request.priority_score` + scoring rows |
| WHO HTM §2.4 — Approved needs only | UAT-IMM01-09 | BR-01-01: Gate G03 | `IMM Procurement Plan.lines[].needs_request` all Approved |
| Luật Đấu thầu Điều 4 — Nguồn vốn | UAT-IMM01-07, UAT-IMM01-08 | BR-01-05: `validate_budget_estimate()` | `IMM Budget Estimate.funding_source` field |
| ISO 13485 §7.1 — Kế hoạch dựa trên yêu cầu | UAT-IMM01-09 | `on_submit_procurement_plan()` → trigger IMM-02 | `IMM Procurement Plan.linked_tech_specs` |

## II.6. Audit / Inspection Readiness

Khi auditor đến (cơ quan y tế, kiểm định):

- [ ] Truy xuất NR theo thiết bị bất kỳ < 5 phút: `list_needs_requests?device_model=...`
- [ ] Verify audit chain 1 click: `verify_audit_chain(needs_request)` từ console
- [ ] KPI quarter: Dashboard IMM-01 → filter theo quý → export PDF/CSV
- [ ] Document control: `Asset Document` list filter `status=Effective` → xem PR/WI hiện hành
- [ ] Kế hoạch mua sắm theo năm: `IMM Procurement Plan` list filter `fiscal_year=...`
- [ ] Role assignment: `frappe.get_all("Has Role", ...)` hoặc User Management
- [ ] NR quá hạn: NR list filter `status=Pending Approval AND creation < [30 days ago]` → export CSV

**URL truy cập nhanh khi audit:**
- NR list: `/imm-01`
- Dashboard: `/imm-01/dashboard`
- Procurement Plan list: `/imm-01/procurement-plan`
- Demand Forecast: `/imm-01/demand-forecast`
- Audit trail: Admin → `IMM Audit Trail` doctype list filter `root_doctype=IMM Needs Request`

## II.7. Training & Roll-out

| Audience | Nội dung | Thời lượng | WI tham chiếu |
|---|---|---|---|
| Trưởng khoa lâm sàng | Tạo phiếu đề xuất nhu cầu, theo dõi trạng thái | 1h | WI-IMM01-001 |
| HTM Reviewer | Chấm điểm ưu tiên, thẩm định dự toán, điều chỉnh ngoại lệ | 2h | WI-IMM01-002 |
| Phó Giám đốc / KH-TC | Phê duyệt kế hoạch mua sắm, xem báo cáo dự báo | 1h | WI-IMM01-003 |
| Phó Trưởng phòng VTTBYT | Dashboard KPI, báo cáo dự báo nhu cầu dài hạn | 1h | WI-IMM01-004 |
| Kế toán (TCKT) | Xem dự toán CAPEX/OPEX, đối chiếu nguồn vốn | 30 phút | WI-IMM01-003 §budget |

Training record lưu qua DocType `Training Record` (IMM-06). Bắt buộc hoàn tất trước go-live.

## II.8. Risk Register (Compliance)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Nhu cầu không có dữ liệu lâm sàng → scoring sai | Medium | High | VR-01: `clinical_justification` bắt buộc; UAT-IMM01-01 | Tech Lead + Clinical Head |
| Trọng số scoring thay đổi sau khi có NR pending → bất công bằng | Low | Medium | `IMM Priority Weight Config` versioned; scoring dùng version tại thời điểm submit | QMS Officer |
| Dự toán CAPEX thiếu OPEX → kế hoạch ngân sách sai | Medium | High | VR-05: validate CAPEX > 0 AND OPEX Year 1 > 0; BR-01-04 enforce | TCKT + Tech Lead |
| PP Approved nhưng thiếu nguồn vốn rõ ràng → vi phạm Luật Đấu thầu | Low | Critical | BR-01-05: `funding_source` bắt buộc; Gate G05 check | KH-TC + QMS Officer |
| Audit chain bị tamper (pháp lý, kiện tụng) | Low | Critical | IMM Audit Trail immutable + verify endpoint + regular hash verify | IMM QA Officer |
| Demand Forecast scheduler fail → kế hoạch 5 năm không cập nhật | Medium | Medium | Monitoring alert nếu job không chạy > 25h; fallback: trigger thủ công | DevOps + Tech Lead |

## II.9. Sign-off QMS

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| QMS Officer | | | |
| Tech Lead | | | |
| Module Owner (IMM-01) | | | |
| (Nếu cần) KH-TC / TCKT | | | |

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
- [x] Monitoring 8 metric + ngưỡng alert
- [ ] On-call schedule confirmed (fill trước go-live)
- [x] Reviewed bởi DevOps + Tech Lead

### II. QMS Mapping
- [x] NĐ98/2021 ≥ 4 điều khoản đối chiếu
- [x] Luật Đấu thầu 22/2023 ≥ 3 điều đối chiếu
- [x] WHO HTM ≥ 5 section đối chiếu
- [x] ISO 13485 ≥ 3 điều đối chiếu
- [x] PR 3 + WI 4 tạo cho major workflows
- [x] HS retention 5 năm cho audit-relevant (4 HS)
- [x] KPI 6 metric có công thức + tần suất + owner
- [x] Audit-readiness checklist ≥ 6 mục
- [x] Training plan cho mọi 5 role
- [x] Risk register 6 mục với mitigation
- [x] Sign-off section sẵn sàng
