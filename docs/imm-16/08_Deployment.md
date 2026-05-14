# IMM-16 — Triển khai & Tuân thủ (Deployment & QMS)

| Mục | Giá trị |
|---|---|
| Module | **IMM-16 — Compliance Monitoring & CAPA** |
| Phiên bản | 1.0.0-rc.2 |
| Ngày cập nhật | 2026-05-14 |
| Owner | DevOps + Tech Lead + QMS Officer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [Module Overview](./IMM-16_Module_Overview.md) |
| Wave | 2 — IMPLEMENTED |

> ✅ IMPLEMENTED — Wave 2. Code đã merge trên `feature/hieuc/wave-2` (commit `4b4b0db`). Tài liệu này song hành với release tag `v1.0.0-rc.2`.

---

## §0 — Wired Artefacts (CURRENT, 2026-05-14)

### Hooks (verified `assetcore/hooks.py`)

`doc_events`:
- `IMM Compliance Rule`, `IMM Compliance Finding`, `IMM CAPA Record` — `validate`, `before_submit`, `on_update` mapped to `assetcore.services.imm16.compliance_rule_validate / compliance_finding_validate / capa_record_validate / capa_record_before_submit / capa_record_on_update`
- `IMM Internal Audit` — `validate`: `validate_internal_audit`, `on_update`: `on_update_internal_audit`
- `IMM Compliance Scorecard` — `validate`: `validate_scorecard_immutability`
- WO submit gate: `validate`: `gate_wo_submit` (IMM PM Work Order, IMM Repair Work Order)
- Real-time eval: `eval_imm04_realtime`, `eval_imm05_realtime`, `eval_imm08_09_realtime`, `eval_imm11_realtime`

`scheduler_events`:
- hourly: `evaluate_all_compliance_rules`, `check_capa_due`, `check_audit_milestones`, `run_compliance_evaluation_hourly`
- daily: `update_compliance_scorecard`
- weekly: `run_compliance_evaluation_weekly`, `check_management_review_due`

### Fixtures (verified `assetcore/fixtures/`)

- `imm16_custom_field_capa_record.json` — CAPA Record Custom Field
- `workflow.json`, `workflow_state.json`, `workflow_action_master.json` — state machines Rule, Finding, CAPA, Internal Audit, Management Review, Scorecard
- `role.json` — IMM QA Officer, IMM Auditor, IMM Management Reviewer

### DocType folders (verified `assetcore/assetcore/doctype/`)

`imm_compliance_rule`, `imm_compliance_finding`, `imm_compliance_scorecard`, `imm_capa_record`, `imm_capa_action_step`, `imm_internal_audit`, `imm_supplier_audit`, `imm_audit_checklist_item`, `imm_management_review`, `imm_scorecard_module_row`, `imm_scorecard_department_row`, `imm_vendor_scorecard`, `audit_finding`, `scorecard_kpi_row`.

### Patches

`assetcore/patches.txt` không chứa entry IMM-16 riêng — DocType + Custom Field load qua fixture. Data migration tương lai bổ sung `assetcore.patches.v3_2.NNN_*` nếu cần.

> ⚠️ Các section còn lại là deployment plan template — §0 là source-of-truth.

---

# Phần I — Deployment Plan

## I.1 Pre-deployment Checklist

> ⚠️ Pending implementation — Wave 3

**Điều kiện tiên quyết:** IMM-04, IMM-08, IMM-09 đã ở trạng thái GA (IMM-16 phụ thuộc cross-module gate).

Thực hiện trước mỗi window deploy (T = giờ deploy):

| Hạng mục | Deadline | Responsible | Status |
|---|---|---|---|
| PR merged, CI green (unit + integration + lint) | T-48h | Dev | ☐ |
| UAT pass (12 scenario UAT-IMM16-01..12, 0 Blocker) | T-48h | QA Lead | ☐ |
| Security sign-off (§V STRIDE trong 07_Testing_QA) | T-48h | QA/Security | ☐ |
| IMM-08 & IMM-09 validate hook confirmed unchanged | T-48h | Dev Lead | ☐ |
| QMS review pass (§II file này) | T-24h | QMS Officer | ☐ |
| User Guide + Release Notes viết xong | T-24h | BA/Tech Writer | ☐ |
| Backup production DB < 24h | T-2h | DevOps | ☐ |
| Communication email T-48h gửi users | T-48h | PM | ☐ |
| Rollback tested trên staging | T-24h | DevOps | ☐ |
| Staging deploy thành công + smoke test pass | T-24h | Dev + QA | ☐ |
| Baseline Compliance Rules fixture seeded + verified | T-24h | Dev | ☐ |
| Workflows 4 IMM-16 active trên staging | T-24h | Dev | ☐ |
| On-call engineer confirmed | T-1h | Dev Lead | ☐ |

## I.2 Stack & Versioning

> ⚠️ Pending implementation — Wave 3

| Component | Phiên bản yêu cầu | Phiên bản hiện tại (prod) |
|---|---|---|
| Frappe | v15.x (latest stable) | v15.x |
| Python | 3.11+ | 3.11.x |
| Node.js | 20 LTS | 20.x |
| MariaDB | 10.6+ | 10.6.x |
| Redis | 7.x | 7.x |
| App `assetcore` | v1.1.0 (IMM-16 GA — Wave 3) | v1.0.x |
| IMM-04 | GA | Required dependency |
| IMM-08 | GA | Required dependency (cross-module gate) |
| IMM-09 | GA | Required dependency (cross-module gate) |

Cập nhật `assetcore/__init__.py`:

```python
# ⚠️ Pending implementation — Wave 3
__version__ = "1.1.0"  # IMM-16 General Availability — Wave 3
```

## I.2b Cấu Hình Môi Trường

> ⚠️ Pending implementation — Wave 3

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
| nginx max body size | 50 MB | 50 MB | 50 MB |
| Supervisor programs | 4 (web×2, worker×2) | 6 (web×2, worker×4) | 10 (web×4, worker×6) |
| Domain | `dev.assetcore.local` | `staging.assetcore.vn` | `assetcore.vn` |
| SSL cert | Self-signed | Let's Encrypt | Let's Encrypt (wildcard) |
| Firewall | Dev: open | Staging: 80/443+22 | Prod: 443 only + WAF |

**Environment variables bổ sung cho IMM-16:**

```bash
# ⚠️ Pending implementation — Wave 3
# .env / site_config.json bổ sung:
IMM16_EVALUATION_BATCH_SIZE=200      # số rule/batch khi chạy monthly eval
IMM16_ESCALATION_RETRY_HOURS=24      # cadence gửi escalation email
IMM16_SCORECARD_CACHE_TTL_SECONDS=3600  # cache heatmap 1h
IMM16_AUDIT_TRAIL_HASH_ALG=sha256    # hash algorithm cho audit chain
```

## I.3 Deployment Artefacts

> ⚠️ Pending implementation — Wave 3

### Patch files

| Patch | File | Mô tả | Idempotent? |
|---|---|---|---|
| `v4_0.add_imm16_custom_fields_capa` | `assetcore/patches/v4_0/add_imm16_custom_fields_capa.py` | Thêm custom fields `workflow_state_imm16`, `root_cause_method`, `effectiveness_result`, `reopen_count`, ... vào `IMM CAPA Record` | ✅ `frappe.db.has_column` check |
| `v4_0.create_imm16_doctypes` | `assetcore/patches/v4_0/create_imm16_doctypes.py` | Tạo 5 DocType mới: `IMM Compliance Rule`, `IMM Compliance Finding`, `IMM Internal Audit`, `IMM Compliance Scorecard`, `IMM Management Review` | ✅ `frappe.db.table_exists` |
| `v4_0.add_imm16_db_indexes` | `assetcore/patches/v4_0/add_imm16_db_indexes.py` | Tạo 9 DB indexes bao gồm UNIQUE INDEX idempotency (rule, source_record, evaluation_date) | ✅ `CREATE INDEX IF NOT EXISTS` |
| `v4_0.migrate_capa_record_workflow_state` | `assetcore/patches/v4_0/migrate_capa_record_workflow_state.py` | Map `IMM CAPA Record` hiện có → thêm `workflow_state_imm16` field từ `status` field hiện hành (batch 200/run) | ✅ skip nếu đã migrated |
| `v4_0.seed_imm16_compliance_rules_baseline` | `assetcore/patches/v4_0/seed_imm16_compliance_rules_baseline.py` | Seed ≥ 40 baseline Compliance Rules từ fixture `imm16_compliance_rules_baseline.json` | ✅ `if not frappe.db.exists` |

Đăng ký trong `assetcore/patches.txt` (thứ tự cố định, không đổi sau khi release).

### Chi tiết patch quan trọng: migrate_capa_record_workflow_state

```python
# assetcore/patches/v4_0/migrate_capa_record_workflow_state.py
# ⚠️ Pending implementation — Wave 3

"""
Migrate existing IMM CAPA Record documents to populate the new
workflow_state_imm16 custom field from the existing status field.

Mapping:
    status="Open"         → workflow_state_imm16="Investigating"
    status="In Progress"  → workflow_state_imm16="Implementation"
    status="Closed"       → workflow_state_imm16="Closed"
    (others)              → workflow_state_imm16="Draft"

Idempotent: skip records where workflow_state_imm16 already set.
Batch: 200 records per iteration.
"""

import frappe


def execute():
    STATUS_MAP = {
        "Open": "Investigating",
        "In Progress": "Implementation",
        "Closed": "Closed",
    }
    DEFAULT_STATE = "Draft"

    if not frappe.db.has_column("IMM CAPA Record", "workflow_state_imm16"):
        frappe.log_error("Column workflow_state_imm16 not found — run add_imm16_custom_fields_capa first")
        return

    total = frappe.db.count("IMM CAPA Record", {"workflow_state_imm16": ("is", "not set")})
    if total == 0:
        return  # already migrated

    batch_size = 200
    offset = 0

    while True:
        records = frappe.db.get_all(
            "IMM CAPA Record",
            filters={"workflow_state_imm16": ("is", "not set")},
            fields=["name", "status"],
            limit=batch_size,
            order_by="creation asc",
        )
        if not records:
            break

        for rec in records:
            new_state = STATUS_MAP.get(rec.status, DEFAULT_STATE)
            frappe.db.set_value("IMM CAPA Record", rec.name, "workflow_state_imm16", new_state)

        frappe.db.commit()
        offset += batch_size
```

### Fixtures cần import

```bash
# ⚠️ Pending implementation — Wave 3
bench --site assetcore.local import-fixtures --app assetcore
```

Fixtures:
- `Role` (thêm role `Internal Auditor` nếu chưa có)
- `Role Profile`
- `Workflow` — 4 workflows IMM-16:
  - `IMM Compliance Finding Workflow`
  - `IMM CAPA Record Extended Workflow`
  - `IMM Compliance Scorecard Workflow`
  - `IMM Internal Audit Workflow`
- `Workflow State`, `Workflow Action Master`
- `Custom Field` — custom fields trên `IMM CAPA Record`
- `IMM Compliance Rule` (baseline ≥ 40 rules)
- `Workspace` (IMM-16 workspace entry)

### Frontend build

```bash
# ⚠️ Pending implementation — Wave 3
cd apps/assetcore/frontend
npm ci
npm run build
bench build --app assetcore
```

### New dependencies

| Dependency | Loại | Version | Lý do |
|---|---|---|---|
| (không có thêm Python dep) | — | — | IMM-16 dùng libraries hiện có |
| (không có thêm npm dep) | — | — | Vue 3 + Pinia + TanStack đã có |

## I.4 Deploy Sequence

> ⚠️ Pending implementation — Wave 3

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
git pull origin main  # hoặc release/v1.1.0 branch

# 5. Setup requirements
./env/bin/pip install -e apps/assetcore

# 6. Frontend build
cd apps/assetcore/frontend && npm ci && npm run build
bench build --app assetcore

# 7. Migrate + patches (order: custom_fields → doctypes → indexes → migrate_capa → seed_rules)
bench --site assetcore.local migrate

# 8. Import fixtures
bench --site assetcore.local import-fixtures --app assetcore

# 9. Verify UNIQUE INDEX tồn tại
bench --site assetcore.local execute \
  "frappe.db.sql('SHOW INDEX FROM \`tabIMM Compliance Finding\` WHERE Key_name LIKE \"%idempotent%\"')"

# 10. Clear cache + restart
bench --site assetcore.local clear-cache
bench restart

# 11. Tắt maintenance mode
bench --site assetcore.local set-maintenance-mode off

# 12. Smoke test (§I.6)
```

### Production (giống staging + thêm)

- Chạy trong maintenance window: 23:00 - 02:00 (thứ 6 → thứ 7).
- Backup off-site (S3) ngay trước khi pull code.
- On-call engineer trực từ T đến T+4h.
- Nếu smoke test fail sau 30 phút → rollback ngay (§I.7).

## I.5 Schema Migration Risk

> ⚠️ Pending implementation — Wave 3

| Thay đổi | Risk | Mitigation |
|---|---|---|
| Thêm custom fields nullable vào `IMM CAPA Record` | Low | `frappe.db.has_column` check; nullable + default null |
| Tạo 5 DocType mới | Low | `frappe.db.table_exists` check |
| UNIQUE INDEX `(rule, source_record, evaluation_date)` | Medium | Chạy staging dry-run; INDEX trên bảng mới (chưa có data) |
| Migrate `IMM CAPA Record` existing records | Medium | Batch 200/run + idempotent check; staging dry-run trước |
| Seed ≥ 40 Compliance Rules | Low | `if not frappe.db.exists` check |

**Long-running migration** (patch `migrate_capa_record_workflow_state`):
- Ước tính record: ≤ 500 CAPA records (Wave 1-2 dev data).
- Batch size: 200 records/iteration với `frappe.db.commit()` sau mỗi batch.
- Lock policy: Không lock table; chạy trong maintenance mode.
- Dry-run: Chạy trên staging với count verify trước/sau.

## I.6 Smoke Test Sau Deploy

> ⚠️ Pending implementation — Wave 3

| Step | Cách | Expected |
|------|---|---|
| 1 | Đăng nhập `admin` vào site | Login thành công |
| 2 | Mở workspace `IMM Compliance` | Workspace load, IMM-16 trong sidebar |
| 3 | Mở `/imm16` (Dashboard) | Dashboard load, không JS error console |
| 4 | Gọi `list_compliance_rules` API | `{"success": true, "data": {"rules": [...], "total": ...}}` |
| 5 | Gọi `get_dashboard_stats` API | Response có `total_findings`, `open_capa_count`, `compliance_rate` |
| 6 | Gọi `get_compliance_heatmap` API | Matrix module × dept trả về |
| 7 | Verify 4 Workflow IMM-16 active | `frappe.get_doc("Workflow", "IMM Compliance Finding Workflow")` tồn tại |
| 8 | Verify baseline Rules seeded | `frappe.db.count("IMM Compliance Rule", {"is_active": 1}) >= 40` |
| 9 | Verify UNIQUE INDEX | `SHOW INDEX FROM tabIMM Compliance Finding` có `idx_imm16_finding_idempotent` |
| 10 | Verify cross-module gate | `check_asset_compliance_status(asset=some_asset)` trả về `{"blocked": false}` (không raise) |
| 11 | Verify schedulers | `bench --site assetcore.local scheduled-jobs` có `run_compliance_evaluation_monthly` |
| 12 | Verify CAPA custom fields | `IMM CAPA Record` form có field `workflow_state_imm16` |
| 13 | Permission test | `test_auditor` login → không thấy nút [Tạo Rule] |
| 14 | Frontend assets load | `/assets/assetcore/` không 404 |

## I.7 Rollback Plan

> ⚠️ Pending implementation — Wave 3

### Trigger conditions

- Login hoàn toàn không được (tất cả users).
- IMM-08 / IMM-09 WO Submit bị chặn sai bởi cross-module gate (BR-16-09 regression).
- Migration gây data corruption trong `IMM CAPA Record`.
- Critical permission bug (user thấy CAPA/Finding không được phép).
- API 5xx rate > 5% trong 10 phút đầu.

### Quick rollback < 15 phút

```bash
# 1. Bật maintenance mode
bench --site assetcore.local set-maintenance-mode on

# 2. Restore DB từ backup
bench --site assetcore.local restore /path/to/backup_before_deploy.sql.gz

# 3. Checkout commit cũ
git checkout v1.0.x-last-stable  # version trước IMM-16

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

Khi đã có user mutation (Finding/CAPA tạo giữa deploy và rollback):
- Xuất records mới trước khi restore: `bench --site ... export-doctype "IMM Compliance Finding" ...`
- Sau hotfix, re-import manually với review từng record.
- Hotfix branch: `hotfix/imm16-v1.1.1`.

## I.8 Communication

**T-48h — Email trước deploy:**
> Kính gửi người dùng AssetCore,
> Hệ thống sẽ nâng cấp lúc 23:00 [ngày X] → 02:00 [ngày X+1]. Tính năng mới: Module IMM-16 Giám sát Tuân thủ & CAPA. Hệ thống tạm ngừng 30-60 phút. Vui lòng hoàn tất công việc trước 22:30. Liên hệ: [support@hospital.vn]

**Trong deploy — Status:**
> Hệ thống đang bảo trì, dự kiến hoàn thành lúc 02:00. Cập nhật: [status.assetcore.vn]

**T+1h sau deploy — Email hoàn tất:**
> Hệ thống AssetCore đã hoàn tất nâng cấp phiên bản 1.1.0. Tính năng mới: Module IMM-16 Giám sát Tuân thủ & CAPA. Xem User Guide: [link]. Báo lỗi: [support@hospital.vn]

## I.9 Monitoring & Alerting (T+24h)

> ⚠️ Pending implementation — Wave 3

| Metric | Ngưỡng cảnh báo | Tool |
|---|---|---|
| Error rate API imm16 | > 1% requests 5xx | Nginx log + Frappe error log |
| `run_compliance_evaluation_monthly` duration | > 120s | Frappe scheduler log |
| `get_compliance_heatmap` p95 | > 2s | Frappe slow query log |
| `check_asset_compliance_status` p99 | > 200ms | APM / slow query |
| UNIQUE INDEX violation (duplicate finding attempt) | Bất kỳ error | Frappe error log — EXPECTED behavior (idempotency working) |
| CAPA escalation scheduler fail | Job không chạy > 2h | Frappe scheduler log |
| Audit trail hash verify fail | Bất kỳ | Email `CMMS Admin` |
| DB CPU | > 80% trong 5 phút | Server monitoring |

## I.10 Post-deployment Checklist

> ⚠️ Pending implementation — Wave 3

- [ ] Git tag tạo: `git tag v1.1.0 -m "IMM-16 General Availability — Wave 3"`
- [ ] Release Notes cập nhật version thực tế + ngày deploy
- [ ] Traceability matrix (`09_Release.md §III`) chốt cột `Released-in = v1.1.0`
- [ ] Backup config lưu off-site sau deploy thành công
- [ ] Post-mortem nếu có incident trong maintenance window
- [ ] Run first monthly compliance evaluation: `bench execute assetcore.tasks.run_compliance_evaluation_monthly`
- [ ] Verify first Finding auto-created trong staging environment
- [ ] Retro sprint kế: note improvement cho deploy lần sau

---

# Phần II — QMS / Compliance Mapping

## II.1 Cấu Trúc QMS Reference

| Cấp | Tên | Vai trò | ID format |
|---|---|---|---|
| QC | Quality Charter | Chính sách chất lượng cấp tổ chức | QC-XXXX |
| PR | Procedure | Quy trình chuẩn (SOP) per module | PR-IMM16-XXX |
| WI | Work Instruction | Hướng dẫn thao tác cho end-user | WI-IMM16-XXX |
| BM | Business Master | Master data + change control | (DocType name) |
| HS | Historical Snapshot | Bản ghi lịch sử không thể sửa | (IMM Audit Trail records) |
| KPI | Key Performance Indicator | Đo lường hiệu quả | KPI-IMM16-XXX |

## II.2 Trace Yêu Cầu Pháp Lý

> ⚠️ Pending implementation — Wave 3

### NĐ98/2021/NĐ-CP — Trang thiết bị y tế

| Điều/Khoản | Yêu cầu | Áp lên module qua | Doc/Code reference |
|---|---|---|---|
| Điều 15.2 — Hồ sơ TTBYT | Lưu trữ hồ sơ thiết bị ≥ 5 năm | `IMM Audit Trail` immutable hash chain | `assetcore/utils/lifecycle.py` |
| Điều 21 — Kiểm soát chất lượng | Hệ thống theo dõi tuân thủ quy trình bảo trì | `IMM Compliance Finding` auto-detect qua scheduler | `services/imm16_rule_evaluator.py` |
| Điều 22 — Bảo dưỡng, sửa chữa | Thiết bị không tuân thủ phải có hành động khắc phục | BR-16-04: NC Finding phải link CAPA | `services/imm16_capa.py` |
| Điều 25 — Kiểm tra, giám sát | Kiểm toán nội bộ định kỳ và hành động phòng ngừa | `IMM Internal Audit` + CAPA full lifecycle | DocType `IMM Internal Audit` |

### Quyết định 3107/QĐ-BYT — Danh mục TTBYT

| Khoản | Yêu cầu | Áp lên module qua |
|---|---|---|
| Phân loại Class I/II/III | Compliance rules được cấu hình theo risk class | `IMM Compliance Rule.applicable_risk_classes` + findings per asset |
| Thiết bị Class III | Critical findings phải có CAPA và block WO (BR-16-09) | `check_asset_compliance_status()` gate |

### WHO HTM 2025 — Health Technology Management

| Section | Yêu cầu | Áp lên module qua | Code reference |
|---|---|---|---|
| §4.2 — QMS Integration | HTM phải tích hợp CAPA loop | `IMM CAPA Record` extended workflow | `doc_events` in `hooks.py` |
| §5.5 — Compliance Monitoring | Đo lường tuân thủ định kỳ và báo cáo | Monthly scorecard + quarterly MR | `tasks.py: update_compliance_scorecard` |
| §6.4 — Non-conformance | NC phải được ghi nhận, phân tích, khắc phục | Finding → CAPA lifecycle (US-16-03..06) | `services/imm16_capa.py` |
| §7.1 — Internal Audit | Internal audit cycle có checklist và auto-finding | `IMM Internal Audit` + `IMM Audit Checklist Item` | `services/imm16_audit.py` |
| §7.3 — Management Review | Review quý về compliance performance | `IMM Management Review` + gate publish scorecard | `services/imm16_mr.py` |

### ISO 13485:2016 — Medical Devices QMS

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| §8.4 — Phân tích dữ liệu | Phân tích xu hướng compliance, KPI trend | `trend_vs_prev_month` trong Scorecard + Heatmap |
| §8.5.2 — Hành động khắc phục (CAPA) | CAPA phải có RCA, kế hoạch, verification | 6-state CAPA workflow; VR-05 (RCA), VR-06 (effectiveness) |
| §8.5.3 — Hành động phòng ngừa | Compliance rule proactive monitoring | Scheduler monthly eval trước khi vấn đề leo thang |
| §5.6 — Management Review | Ban lãnh đạo review compliance định kỳ | `IMM Management Review` quarterly gate (BR-16-08) |
| §4.2.4 — Kiểm soát hồ sơ | Hồ sơ compliance lưu trữ đủ | `IMM Compliance Finding` + `IMM Audit Trail` immutable |

## II.3 QMS Artefact Tạo Bởi Module

> ⚠️ Pending implementation — Wave 3

### PR (Procedure)

| ID | Tên | File | Workflow trong code |
|---|---|---|---|
| PR-IMM16-001 | Quy trình khai báo và quản lý Compliance Rule | `docs/imm-16/09_Release.md §I.5.a` | `IMM Compliance Rule` change control (version + change_summary) |
| PR-IMM16-002 | Quy trình xử lý Finding: xem xét, NC/FP/Waive | `docs/imm-16/09_Release.md §I.5.b` | `IMM Compliance Finding Workflow` |
| PR-IMM16-003 | Quy trình CAPA: khởi tạo, điều tra, kế hoạch, xác minh | `docs/imm-16/09_Release.md §I.5.c` | `IMM CAPA Record Extended Workflow` |
| PR-IMM16-004 | Quy trình Internal Audit nội bộ định kỳ | `docs/imm-16/09_Release.md §I.5.d` | `IMM Internal Audit Workflow` |
| PR-IMM16-005 | Quy trình phát hành Compliance Scorecard + MR | `docs/imm-16/09_Release.md §I.5.e` | `IMM Compliance Scorecard Workflow` + MR gate |

### WI (Work Instruction)

| ID | Tên | Audience | File |
|---|---|---|---|
| WI-IMM16-001 | Hướng dẫn tạo và cấu hình Compliance Rule | Tổ HC-QLCL | `09_Release.md §I.6.a` |
| WI-IMM16-002 | Hướng dẫn xem xét Finding và xác nhận NC | Tổ HC-QLCL + Internal Auditor | `09_Release.md §I.6.b` |
| WI-IMM16-003 | Hướng dẫn miễn trừ Finding (Waive) | VP Block2 | `09_Release.md §I.6.c` |
| WI-IMM16-004 | Hướng dẫn tạo và theo dõi CAPA | Workshop Head + Trưởng phòng | `09_Release.md §I.6.d` |
| WI-IMM16-005 | Hướng dẫn thực hiện Internal Audit | Internal Auditor | `09_Release.md §I.6.e` |
| WI-IMM16-006 | Hướng dẫn đọc Compliance Scorecard & Heatmap | VP Block2 + Tổ HC-QLCL | `09_Release.md §I.6.f` |
| WI-IMM16-007 | Hướng dẫn Management Review quý | VP Block2 | `09_Release.md §I.6.g` |

### BM (Business Master)

| Master data | Owner thay đổi | Change control |
|---|---|---|
| `IMM Compliance Rule` (≥40 baseline rules) | Tổ HC-QLCL | Version + change_summary bắt buộc (BR-16-05); fixture PR review |
| Escalation matrix (email recipients per level/severity) | CMMS Admin | Site config + code change |
| `IMM SLA Policy` (nếu link CAPA SLA) | Tech Lead | Fixture + PR review |

### HS (Historical Snapshot)

| ID | Source | Retention | Format |
|---|---|---|---|
| HS-IMM16-001 | `IMM Audit Trail` per Finding/CAPA action | ≥ 5 năm (NĐ98 Điều 15) | JSON hash chain, immutable |
| HS-IMM16-002 | `IMM Compliance Finding` submitted records | ≥ 5 năm | Frappe record, no-delete |
| HS-IMM16-003 | `IMM CAPA Record` all versions (Frappe Version) | ≥ 5 năm | Frappe Version + track_changes=1 |
| HS-IMM16-004 | `IMM Compliance Scorecard` published (immutable) | ≥ 5 năm | `is_published=1`, write=0 |
| HS-IMM16-005 | `IMM Internal Audit` + checklist items | ≥ 5 năm | Frappe submittable, amend only |

### KPI

| ID | Tên | Công thức | Tần suất | Owner báo cáo |
|---|---|---|---|---|
| KPI-IMM16-001 | Overall Compliance Rate | `(total_findings − nc_count) / total_findings × 100%` | Tháng | Tổ HC-QLCL |
| KPI-IMM16-002 | CAPA Closure Rate | `COUNT(CAPA Closed trong kỳ) / COUNT(CAPA mở trong kỳ) × 100%` | Tháng | Tổ HC-QLCL |
| KPI-IMM16-003 | CAPA On-time Rate | `COUNT(CAPA Closed trước due_date) / COUNT(CAPA Closed) × 100%` | Tháng | VP Block2 |
| KPI-IMM16-004 | CAPA Reopen Rate | `COUNT(CAPA reopen_count > 0) / COUNT(CAPA Closed) × 100%` | Tháng | Tổ HC-QLCL |
| KPI-IMM16-005 | Critical Finding Response Time | `AVG(first_action_date − finding_date)` cho Critical findings | Tuần | VP Block2 |
| KPI-IMM16-006 | Compliance Trend | `score_pct tháng này − score_pct tháng trước` | Tháng | VP Block2 |
| KPI-IMM16-007 | Audit Finding Rate | `COUNT(Finding từ audit) / COUNT(checklist items) × 100%` | Theo audit | Tổ HC-QLCL |

API: `get_dashboard_stats` + `get_capa_aging` + `get_compliance_heatmap` trong `api/imm16.py`.

## II.4 Document Control

Workflow PR/WI qua DocType `Asset Document` (IMM-05):

```
Draft → Reviewed → Approved → Effective → Obsolete
```

- **Change control**: Mọi thay đổi PR/WI tạo phiên bản mới; phiên bản cũ → Obsolete.
- **CAPA linkage**: Nếu PR thay đổi do CAPA → link `capa_ref` vào `Asset Document`.
- **Training**: Khi PR/WI Effective → trigger notification cho audience role (IMM-06).
- **IMM Compliance Rule change control**: Riêng Rule versioning (rule_code level) là built-in vào `IMM Compliance Rule` DocType (version field, change_summary — BR-16-05).

## II.5 Traceability Compliance → Code

> ⚠️ Pending implementation — Wave 3

| Yêu cầu | Test case | Code/DocType | Audit evidence |
|---|---|---|---|
| NĐ98 Điều 22 — Hành động khắc phục | UAT-IMM16-04 (Confirm NC + Open CAPA) | BR-16-04: `link_finding_to_capa()` | `IMM Compliance Finding.capa_ref` set |
| NĐ98 Điều 15.2 — Lưu trữ ≥ 5 năm | §VII unit test `test_audit_chain` | `IMM Audit Trail` immutable | `verify_audit_chain()` pass |
| WHO HTM §6.4 — NC → CAPA | UAT-IMM16-05 (CAPA lifecycle) | 6-state CAPA workflow | `IMM CAPA Record.workflow_state_imm16` |
| WHO HTM §5.5 — Compliance Monitoring | UAT-IMM16-09 (Scorecard sinh) | `ScorecardAggregator.compute()` | `IMM Compliance Scorecard.score_pct` |
| ISO 13485 §8.5.2 — Effectiveness | UAT-IMM16-05 Step 8 (Effectiveness Check) | VR-06: `effectiveness_result` bắt buộc | `IMM CAPA Record.effectiveness_result + evidence` |
| ISO 13485 §5.6 — Management Review | UAT-IMM16-10 (MR Gate) | BR-16-08: `_check_quarterly_mr_gate()` | `IMM Management Review.status=Closed` |
| BR-16-09 — Cross-module gate | UAT-IMM16-11 (WO Submit blocked) | `ComplianceGate.check_asset_compliance_status()` | `check_asset_compliance_status response.blocked=true` |

## II.6 Audit / Inspection Readiness

Khi auditor đến (cơ quan y tế, kiểm định):

- [ ] Truy xuất Finding theo asset < 2 phút: `/imm16/findings?asset=...`
- [ ] Verify audit chain 1 click: `verify_audit_chain(asset)` từ admin console
- [ ] Compliance Scorecard lịch sử: `/imm16/scorecards` — filter theo period
- [ ] CAPA chưa đóng: `/imm16/capa?status=!Closed`
- [ ] Compliance Heatmap current quarter: `/imm16/heatmap`
- [ ] Rule version history: `IMM Compliance Rule` detail → Version tab
- [ ] Role assignment: User Management → `Has Role` per user
- [ ] Internal Audit reports: `IMM Internal Audit` list → filter `status=Closed` → download audit_report

**URL truy cập nhanh khi audit:**
- Dashboard: `/imm16`
- Findings: `/imm16/findings`
- CAPA: `/imm16/capa`
- Heatmap: `/imm16/heatmap`
- Scorecards: `/imm16/scorecards`
- Rules: `/imm16/rules`
- Audit Trail: Admin → `IMM Audit Trail` doctype list

## II.7 Training & Roll-out

> ⚠️ Pending implementation — Wave 3

| Audience | Nội dung | Thời lượng | WI tham chiếu |
|---|---|---|---|
| Tổ HC-QLCL | Quản lý Rule, xem xét Finding, xác nhận NC, CAPA oversight, Scorecard publish | 4h | WI-IMM16-001..004, WI-IMM16-006 |
| Internal Auditor | Xem xét Finding, thực hiện Internal Audit, hoàn thành checklist | 3h | WI-IMM16-002, WI-IMM16-005 |
| Workshop Head | Tạo và theo dõi CAPA (action owner) | 2h | WI-IMM16-004 |
| Biomed Engineer | Xem CAPA được assign; hiểu cross-module gate | 1h | WI-IMM16-004 §action_steps |
| VP Block2 | Waive Finding, Close Audit, Publish Scorecard, Finalize MR, đọc Dashboard | 2h | WI-IMM16-003, WI-IMM16-006, WI-IMM16-007 |
| Trưởng phòng | Tạo CAPA cho dept, xem Finding của dept | 1h | WI-IMM16-004 |
| CMMS Admin | Cấu hình Rule, Escalation, User roles, Monitor schedulers | 2h | WI-IMM16-001 + admin guide |

Training record lưu qua DocType `Training Record` (IMM-06). Bắt buộc hoàn tất trước go-live.

## II.8 Risk Register (Compliance)

> ⚠️ Pending implementation — Wave 3

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Rule threshold sai → Finding bỏ sót / false alarm | Medium | High | VR-01 validate; peer review khi thêm rule; UAT-IMM16-02 | Tổ HC-QLCL |
| Idempotency fail → duplicate Finding → KPI sai | Low | High | UNIQUE INDEX `(rule, source_record, evaluation_date)` + integration test | Tech Lead |
| Scorecard formula sai → báo cáo quản lý sai | Low | Critical | Unit test deterministic formula; staging verify vs manual calc | QA Lead |
| Cross-module gate (BR-16-09) block sai WO → vận hành gián đoạn | Low | Critical | Unit test gate; UAT-IMM16-11; roll-back plan | Tech Lead |
| CAPA re-open loop không kiểm soát → compliance stall | Medium | Medium | reopen_count tracking + escalation matrix L3+ | VP Block2 |
| Audit trail bị tamper (pháp lý) | Low | Critical | Hash chain IMM Audit Trail + regular verify job | CMMS Admin |
| Scheduler fail im lặng → Finding không sinh → compliance không detect | Medium | High | Frappe scheduler log + alerting (§I.9) | DevOps |
| Published Scorecard bị sửa → bằng chứng kiểm toán sai | Low | Critical | VR-09 validate + DocPerm write=0 sau publish | Tech Lead |

## II.9 Sign-off QMS

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| QMS Officer | | | |
| Tech Lead | | | |
| Module Owner (IMM-16) | | | |
| Tổ HC-QLCL Lead | | | |
| VP Block2 | | | |
| (Nếu cần) Legal / Pháp chế | | | |

---

## DoD — Hoàn chỉnh

### I. Deployment Plan

- [x] Pre-deploy checklist đầy đủ (13 mục, bao gồm dependency IMM-04/08/09)
- [x] 5 patch files + đăng ký `patches.txt`
- [x] Chi tiết patch `migrate_capa_record_workflow_state` với code stub
- [x] Fixtures cần import liệt kê
- [x] Cấu hình môi trường 3 môi trường (dev/staging/prod)
- [x] Environment variables bổ sung IMM-16
- [x] Deploy sequence staging + production documented
- [x] Smoke test 14 step (bao gồm cross-module gate verify)
- [x] Rollback < 15 phút có script
- [x] Communication template T-48h + trong + T+1h
- [x] Monitoring 8 metric + ngưỡng alert
- [ ] On-call schedule confirmed (fill trước go-live)
- [x] Reviewed bởi DevOps + Tech Lead

### II. QMS Mapping

- [x] NĐ98/2021 ≥ 4 điều khoản đối chiếu
- [x] WHO HTM ≥ 5 section đối chiếu
- [x] ISO 13485 ≥ 5 điều đối chiếu
- [x] PR 5 + WI 7 tạo cho major workflows
- [x] HS retention 5 năm cho audit-relevant (5 HS)
- [x] KPI 7 metric có công thức + tần suất + owner
- [x] Audit-readiness checklist ≥ 8 mục + URL nhanh
- [x] Training plan cho mọi 7 role
- [x] Risk register 8 mục với mitigation
- [x] Sign-off section sẵn sàng
