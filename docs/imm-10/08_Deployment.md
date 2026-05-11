# IMM-10 — Deployment

| Mục | Giá trị |
|---|---|
| Module | IMM-10 — Hậu kiểm và tuân thủ |
| Đợt | 3 |
| Trạng thái | Plan (BE chưa scaffold) |
| Cập nhật | 2026-05-10 |

> Plan deploy + QMS mapping. Lệnh `bench` cụ thể chỉ chạy khi BE Sprint Wave 3 ship code.

---

## I. Pre-deploy Checklist

- [ ] IMM-16 (Compliance Engine) đã GA trên site target — IMM-10 phụ thuộc Rule Engine + Management Review.
- [ ] IMM-08, IMM-09 stable (bulk WO route).
- [ ] IMM-12 CAPA chain ổn định (Incident → RCA → CAPA).
- [ ] Master `AC Asset`, `IMM Device Model`, `AC Supplier` có dữ liệu đủ field định danh (model, lot, serial).
- [ ] Role + Role Profile bổ sung (nếu cần) — refer `04_Backend_Design.md` §III.
- [ ] Backup site (`bench backup`) trước migrate.
- [ ] Approval từ Tổ HC-QLCL & PTP Khối 2 (owner module).

---

## II. Deploy sequence (dự kiến)

```bash
# 1. Pull code mới
cd /home/<user>/frappe-bench/apps/assetcore
git fetch && git checkout release/v3.x-imm10

# 2. Backup
bench --site assetcore.local backup --with-files

# 3. Migrate (chạy patch + tạo DocType + Workflow)
bench --site assetcore.local migrate

# 4. Import fixtures
bench --site assetcore.local import-fixtures
# Hoặc explicit: bench --site assetcore.local execute assetcore.setup.install.setup_imm10

# 5. Build FE
cd frontend && npm install && npm run build
cd .. && bench build --app assetcore

# 6. Restart
bench restart   # supervisor: web + scheduler

# 7. Smoke test
bench --site assetcore.local execute assetcore.scripts.uat.uat_imm10.smoke
```

(Lệnh chuẩn refer skill `assetcore-deployment`.)

---

## III. Migration / Patches

| Patch | Mục đích | Khi nào chạy |
|---|---|---|
| `assetcore/patches/v3_x/imm10_create_compliance_case.py` | Tạo DocType + Workflow + Workflow State + Action Master | Migrate lần đầu |
| `assetcore/patches/v3_x/imm10_seed_recall_action_template.py` | Seed template công văn | Sau create DocType |
| `assetcore/patches/v3_x/imm10_register_compliance_rules.py` | Đăng ký 4 rule với IMM-16 engine | Sau IMM-16 ready |

(Patch file thực tế — Sprint Wave 3 ship.)

---

## IV. Fixtures

| File | Nội dung |
|---|---|
| `fixtures/imm10_compliance_workflow.json` | Workflow JSON cho `IMM Compliance Case` |
| `fixtures/imm10_recall_action_template.json` | Template công văn (vi-VN) |
| `fixtures/imm10_sla_policy.json` | `IMM SLA Policy`: 48h disclosure, 30d recall completion, 14d effectiveness check |
| `fixtures/role.json` (append) | Bổ sung role nếu cần (đã có IMM QA Officer, IMM Document Officer trong Wave 1) |

`hooks.py` — append fixture name vào danh sách fixtures khi scaffold.

---

## V. Configuration

| Config | Loại | Giá trị mặc định |
|---|---|---|
| `imm10.disclosure_due_hours` | site_config / SLA Policy | 48 |
| `imm10.recall_completion_target_days` | SLA Policy | 30 |
| `imm10.effectiveness_check_offsets` | SLA Policy | [30, 60, 90] |
| `imm10.chronic_failure_threshold` | site_config | 3 incidents / 90 days / model |
| `imm10.regulator_email_BoYTe` | site_config (secret) | *(Cần set khi deploy production)* |

> KHÔNG hardcode email regulator trong code (R-09). Dùng `frappe.conf` hoặc DocType `IMM SLA Policy`.

---

## VI. QMS Mapping

Tuân thủ Lớp QMS Architecture §"Lớp QMS và governance" (QC → PR → WI → BM → HS → KPI-DASH).

| Mã QMS | Loại | Tên tài liệu / artifact | Owner | Vị trí |
|---|---|---|---|---|
| PR-IMMIS-10-01 | Procedure | Quy trình hậu kiểm và xử lý recall/FSCA | Tổ HC-QLCL | QMS điện tử/IMMIS/10-* |
| PR-IMMIS-10-02 | Procedure | Quy trình theo dõi CAPA xuyên module | Tổ HC-QLCL | QMS điện tử/IMMIS/10-* |
| WI-IMMIS-10-01 | Work Instruction | HD mở Compliance Case từ vendor notice | Tổ HC-QLCL | QMS điện tử/IMMIS/10-* |
| WI-IMMIS-10-02 | Work Instruction | HD soạn công văn disclosure 48h | Pháp chế | QMS điện tử/IMMIS/10-* |
| WI-IMMIS-10-03 | Work Instruction | HD bulk-create recall WO + theo dõi hoàn tất | PTP Khối 2 / Workshop | QMS điện tử/IMMIS/10-* |
| WI-IMMIS-10-04 | Work Instruction | HD effectiveness check 30/60/90 ngày | Tổ HC-QLCL | QMS điện tử/IMMIS/10-* |
| BM-IMMIS-10-01 | Form | Mẫu công văn báo cáo Bộ Y tế (template) | Pháp chế | QMS điện tử/IMMIS/10-* |
| BM-IMMIS-10-02 | Form | Mẫu thông báo nội bộ recall | Tổ HC-QLCL | QMS điện tử/IMMIS/10-* |
| BM-IMMIS-10-03 | Form | Checklist effectiveness check | Tổ HC-QLCL | QMS điện tử/IMMIS/10-* |
| HS-LOG-IMMIS-10-01 | Log | Disclosure log (auto từ system) | (System) | DocType `IMM Disclosure Log` |
| HS-REC-IMMIS-10-01 | Record | Compliance Case record | Tổ HC-QLCL | DocType `IMM Compliance Case` |
| HS-REP-IMMIS-10-01 | Report | Báo cáo hậu kiểm hàng quý → Management Review | Tổ HC-QLCL | BI/IMMIS |
| KPI-DASH-IMMIS-10 | Dashboard | Compliance dashboard | Tổ HC-QLCL | BI/IMMIS |

(Mã QMS theo schema Architecture line ~280–320. Owner: Tổ HC-QLCL & Risk + Pháp chế phối hợp.)

---

## VII. Permission setup post-deploy

```bash
bench --site assetcore.local execute assetcore.setup.setup_core_permissions.setup_imm10_permissions
```

- DocPerm cho `IMM Compliance Case`: IMM QA Officer (CRUD), IMM Operations Manager (RU + approve), Vendor Engineer (R scope), Workshop Lead (R scope + update affected_assets).
- `permission_query_conditions` wire vào `hooks.py` (R-08).

---

## VIII. Smoke test post-deploy

1. Login IMM QA Officer.
2. Mở 1 Compliance Case test (severity=Low, không gửi disclosure thật).
3. Run scope finder trên model có sẵn → confirm trả assets.
4. Lock scope → bulk create 1 WO test → verify WO xuất hiện trong IMM-08/09.
5. Close test case → verify audit trail chain pass (`verify_audit_chain`).
6. Verify scheduler `imm10.check_disclosure_breach` xuất hiện trong `bench --site ... show-config` scheduler list.

---

## IX. Rollback plan

```bash
# 1. Stop scheduler (tránh chạy job nửa chừng)
bench --site assetcore.local set-maintenance-mode on

# 2. Restore DB + files
bench --site assetcore.local restore <backup-file> --with-private-files <files-tar> --with-public-files <public-tar>

# 3. Checkout commit trước
git checkout v3.x-pre-imm10
bench --site assetcore.local migrate
bench restart

# 4. Maintenance off
bench --site assetcore.local set-maintenance-mode off
```

> **Quan trọng**: Không xoá `IMM Audit Trail` rows đã insert (R-04 immutable). Rollback DB sẽ giữ chain — verify lại sau restore.

---

## X. Monitoring

- Scheduler job log: `bench --site ... show-pending-jobs` + Frappe Scheduled Job Log.
- Dashboard breach widget — owner check daily.
- Alert email tới `bgđ@<bv>` khi disclosure breach (refer `imm10.regulator_email_*`).

---

*Cập nhật: 2026-05-10. Plan — lệnh thực tế chạy khi BE/FE Sprint Wave 3 GA. Tuân thủ R-01..R-10 (CLAUDE.md §2 và `docs/ba/CLAUDE.md`).*
