# IMM-06 — Triển khai & Tuân thủ (Deployment & QMS)

| Mục | Giá trị |
|---|---|
| Module | **IMM-06 — Đào tạo & Quản lý Năng lực (Training & Competency)** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | DevOps + Tech Lead + QMS Officer |
| Liên kết | [07 Testing QA](./07_Testing_QA.md) · [Module Overview](./IMM-06_Module_Overview.md) |

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
| App `assetcore` | v1.1.0 (IMM-06 GA) | (upgrade từ 1.0.x) |

Cập nhật `assetcore/__init__.py`:
```python
__version__ = "1.1.0"  # IMM-06 General Availability (Wave 2)
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
| `v3_2.add_imm06_doctypes` | `assetcore/patches/v3_2/add_imm06_doctypes.py` | Scaffold 5 DocTypes (Program, Session, Participant, Competency, Gap Report) | ✅ `frappe.db.table_exists` check |
| `v3_2.add_imm06_alert_log` | `assetcore/patches/v3_2/add_imm06_alert_log.py` | Tạo DocType `IMM Competency Alert Log` (idempotency tracker) | ✅ |
| `v3_2.seed_imm06_roles` | `assetcore/patches/v3_2/seed_imm06_roles.py` | Insert Role `Tổ HC-QLCL` + `Role Profile` IMM-06 | ✅ `if not frappe.db.exists` |
| `v3_2.add_imm08_09_12_auth_hook` | `assetcore/patches/v3_2/add_imm08_09_12_auth_hook.py` | Thêm `validate_user_authorization` hook vào `before_assign_technician` của IMM-08/09/12 | ✅ flag check |
| `v3_2.add_imm04_coverage_gate` | `assetcore/patches/v3_2/add_imm04_coverage_gate.py` | Hook `get_asset_operator_coverage` vào IMM-04 Clinical_Release transition | ✅ |

Đăng ký trong `assetcore/patches.txt` (thứ tự cố định, không đổi).

### Fixtures cần re-import

```bash
bench --site assetcore.local import-fixtures --app assetcore
```

Fixtures: `Role`, `Role Profile`, `Has Role`, `Workflow` (IMM-06 Session Workflow + IMM-06 Competency Workflow), `Workflow State`, `Workflow Action Master`, `Workspace`.

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
| (không có mới) | — | — | IMM-06 dùng libraries hiện có |

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

# 7. Migrate + patches (thứ tự: v3_2.*)
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
| Thêm 5 DocType mới | Low | `frappe.db.table_exists` check trong patch |
| Thêm 4 Scheduler jobs vào `tasks.py` | Low | Idempotent — chỉ chạy 1 lần/ngày theo cron |
| Hook `before_assign_technician` IMM-08/09/12 | Medium | Flag check in patch; dry-run staging trước; test backward compat với WO existing |
| Hook IMM-04 Clinical_Release gate | Medium | Gate chỉ apply cho transition mới; WO existing không bị ảnh hưởng |
| Role mới `Tổ HC-QLCL` | Low | `if not frappe.db.exists` + fixture idempotent |

**Long-running migration** — không có: IMM-06 là module mới hoàn toàn, không cần migrate data cũ. Nếu bệnh viện có lịch sử competency ngoài hệ thống → nhập thủ công qua bulk import script (xem `scripts/bulk_import/import_competency_history.py`).

## I.6. Smoke Test Sau Deploy

| Step | Cách | Expected |
|---|---|---|
| 1 | Đăng nhập `admin` vào site | Login thành công, hub hiển thị |
| 2 | Mở workspace `IMM Operations` | Module IMM-06 có trong sidebar |
| 3 | Mở `/imm06/programs` (List view) | Danh sách Programs load, không JS error |
| 4 | Tạo 1 Training Program test (không submit) | Form hiển thị đúng, validation hoạt động |
| 5 | Mở `/imm06/sessions` | Session list load |
| 6 | Gọi `list_programs` API | `{"success": true, "data": {...}}` |
| 7 | Gọi `get_dashboard_stats` API | Response đúng format, KPI fields hiện diện |
| 8 | Kiểm tra Workflow IMM-06 Session | `frappe.get_doc("Workflow", "IMM-06 Session Workflow")` tồn tại |
| 9 | Kiểm tra Workflow IMM-06 Competency | `frappe.get_doc("Workflow", "IMM-06 Competency Workflow")` tồn tại |
| 10 | Kiểm tra Scheduler jobs | `bench --site assetcore.local scheduled-jobs` có `check_competency_expiry`, `auto_expire_competency`, `check_recertification_due`, `generate_competency_gap_report` |
| 11 | Frontend assets load | `/assets/assetcore/imm06*` không 404 |
| 12 | Permission test | Operator login → chỉ thấy competency của chính mình |
| 13 | Authorization gate test | `check_user_authorization` trả đúng cho Active/Expired user |

## I.7. Rollback Plan

### Trigger conditions

- Login hoàn toàn không được (tất cả users).
- Hook IMM-08/09/12 gây lỗi khi assign technician (critical path).
- Hook IMM-04 gate block toàn bộ commissioning (sai logic).
- API 5xx rate > 5% trong 10 phút đầu.

### Quick rollback < 15 phút

```bash
# 1. Bật maintenance mode
bench --site assetcore.local set-maintenance-mode on

# 2. Restore DB từ backup
bench --site assetcore.local restore /path/to/backup_before_deploy.sql.gz

# 3. Checkout commit cũ
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

Khi đã có user mutation (competency sign-off trong cửa sổ giữa deploy và rollback):
- Xuất records mới tạo trước khi restore: `bench --site ... export-doctype "IMM User Competency" ...`
- Sau hotfix, re-import manually.
- Hotfix branch: `hotfix/imm06-v1.1.1`.

## I.8. Communication

**T-48h — Email trước deploy:**
> Kính gửi người dùng AssetCore,
> Hệ thống sẽ nâng cấp lúc 23:00 [ngày X] → 02:00 [ngày X+1]. Tính năng mới: Module IMM-06 Đào tạo & Quản lý Năng lực. Hệ thống tạm ngừng khoảng 30-60 phút. Vui lòng hoàn tất công việc trước 22:30. Liên hệ: [support@hospital.vn]

**Trong deploy — Status:**
> Hệ thống đang bảo trì, dự kiến hoàn thành lúc 02:00. Cập nhật realtime: [status.assetcore.vn]

**T+1h sau deploy — Email hoàn tất:**
> Hệ thống AssetCore đã hoàn tất nâng cấp phiên bản 1.1.0. Tính năng mới: Module IMM-06 Đào tạo & Quản lý Năng lực. Xem User Guide: [link]. Báo lỗi: [support@hospital.vn]

## I.9. Monitoring & Alerting (T+24h)

| Metric | Ngưỡng cảnh báo | Tool |
|---|---|---|
| Error rate API imm06 | > 1% requests 5xx | Nginx log + Frappe error log |
| `check_user_authorization` failure rate (WO assign blocked) | > 10% trong 1h | Frappe access log |
| Scheduler `check_competency_expiry` không chạy | > 2h delay | Frappe scheduler log |
| DB CPU | > 80% trong 5 phút | Server monitoring |
| Disk usage | > 80% | Server monitoring |
| Audit chain verify fail | Bất kỳ | Email CMMS Admin |
| Gap report violation Class III | Weekly GAP report | Email Workshop Head + VP Block2 |

## I.10. Post-deployment Checklist

- [ ] Git tag tạo: `git tag v1.1.0 -m "IMM-06 General Availability (Wave 2)"`
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
| QC | Quality Charter | Chính sách chất lượng cấp tổ chức | QC-XXXX |
| PR | Procedure | Quy trình chuẩn (SOP) per module | PR-IMM06-XXX |
| WI | Work Instruction | Hướng dẫn thao tác cho end-user | WI-IMM06-XXX |
| BM | Business Master | Master data + change control | (DocType name) |
| HS | Historical Snapshot | Bản ghi lịch sử không thể sửa | (IMM Audit Trail records) |
| KPI | Key Performance Indicator | Đo lường hiệu quả | KPI-IMM06-XXX |

## II.2. Trace Yêu Cầu Pháp Lý

### NĐ98/2021/NĐ-CP — Trang thiết bị y tế

| Điều/Khoản | Yêu cầu | Áp lên module qua | Doc/Code reference |
|---|---|---|---|
| §35 — Điều kiện người vận hành | Người vận hành TTBYT Class II/III phải được đào tạo có chứng nhận | BR-06-01: `check_user_authorization()` gate | `services/imm06.py` |
| §35 — Hồ sơ đào tạo | Lưu trữ hồ sơ đào tạo người vận hành | `IMM Training Session` submittable + `IMM User Competency` no-delete | DocType lifecycle |
| Điều 15.2 — Lưu trữ hồ sơ | ≥ 10 năm sau user nghỉ việc (NFR-06-06) | `IMM Audit Trail` immutable hash chain | `assetcore/utils/lifecycle.py` |
| Điều 22 — Bảo dưỡng, sửa chữa | KTV thực hiện bảo dưỡng phải đủ năng lực | BR-06-01 hook trong IMM-08/09/12 assign | `services/imm08.py: validate_user_authorization` |

### WHO HTM 2025 — Health Technology Management

| Section | Yêu cầu | Áp lên module qua | Code reference |
|---|---|---|---|
| HTM 4.4 — Training & Competence | Operator đủ năng lực trước khi vận hành | BR-06-01 + BR-06-05 sign-off gate | `check_user_authorization()` |
| Annex 5 — Training Program | Chương trình đào tạo chuẩn với đánh giá | `IMM Training Program` (curriculum) + `IMM Training Session` (delivery) | DocType fields |
| Annex 5 — Recertification | Tái chứng nhận định kỳ trước expiry | BR-06-03: Scheduler `check_recertification_due` + `auto_expire_competency` | `tasks.py` |
| §4.3 — KPI | Đo training compliance KPI | `get_dashboard_stats()` — coverage per dept, expiring count | `api/imm06.py` |

### ISO 13485:2016 — Medical Devices QMS

| Điều | Yêu cầu | Áp lên module qua |
|---|---|---|
| §6.2 — Competence, Awareness, Training | Đảm bảo nhân viên đủ năng lực | BR-06-05: sign-off bắt buộc trước Active; BR-06-03: auto-expire |
| §7.3 — Design Change Control | Thay đổi nội dung đào tạo phải kiểm soát | BR-06-04: Program critical field change → trigger recert |
| §8.5.2 — CAPA | Năng lực bị thu hồi do lỗi vận hành cần CAPA | BR-06-06: `revoke_competency` yêu cầu `revoke_capa_ref` nếu incident |
| §4.2.5 — Control of Records | Mọi hành động có hồ sơ | BR-06-08: `track_changes=1` + `IMM Audit Trail` |
| §4.2 — Document Control | Curriculum (PR/WI) qua document control | `qms_doc_ref` Link sang IMM-05 Asset Document |

## II.3. QMS Artefact Tạo Bởi Module

### PR (Procedure)

| ID | Tên | File | Workflow trong code |
|---|---|---|---|
| PR-IMM06-001 | Quy trình tổ chức đào tạo và đánh giá năng lực | `docs/imm-06/09_Release.md §I.4` (user guide) | Session Workflow Planned→Closed |
| PR-IMM06-002 | Quy trình tái chứng nhận năng lực định kỳ | `IMM-06_Functional_Specs.md §BR-06-03` | Scheduler recert + Refresher session |
| PR-IMM06-003 | Quy trình thu hồi và tạm ngưng năng lực | `IMM-06_Functional_Specs.md §BR-06-06` | `revoke_competency` + CAPA linkage |

### WI (Work Instruction)

| ID | Tên | Audience | File |
|---|---|---|---|
| WI-IMM06-001 | Hướng dẫn tạo và quản lý chương trình đào tạo | Tổ HC-QLCL | `09_Release.md §I.5.a` |
| WI-IMM06-002 | Hướng dẫn lập lịch và thực hiện buổi đào tạo | Tổ HC-QLCL + Biomed Engineer | `09_Release.md §I.5.b` |
| WI-IMM06-003 | Hướng dẫn phê duyệt (sign-off) năng lực | Department Manager / Workshop Head | `09_Release.md §I.5.c` |
| WI-IMM06-004 | Hướng dẫn xem hồ sơ năng lực cá nhân | HTM Technician / Operator | `09_Release.md §I.5.d` |
| WI-IMM06-005 | Hướng dẫn xem Dashboard đào tạo & gap report | Workshop Head / VP Block2 | `09_Release.md §I.6` |

### BM (Business Master)

| Master data | Owner thay đổi | Change control |
|---|---|---|
| `IMM Training Program` (curriculum master) | Tổ HC-QLCL | BR-06-04 + fixture + PR review + QMS Officer approval |
| `IMM Device Model` (device classification) | Workshop Head | `IMM Device Model` workflow |
| `AC Department` | CMMS Admin | Fixture + migration |

### HS (Historical Snapshot)

| ID | Source | Retention | Format |
|---|---|---|---|
| HS-IMM06-001 | `IMM Audit Trail` per Competency lifecycle | ≥ 10 năm (NĐ98 §35) | JSON hash chain, immutable |
| HS-IMM06-002 | `IMM Training Session` Completed/Verified | ≥ 10 năm | Frappe record, no-delete |
| HS-IMM06-003 | `IMM User Competency` (mọi trạng thái, kể cả Revoked) | ≥ 10 năm | Frappe record, on_trash blocked |
| HS-IMM06-004 | `IMM Competency Alert Log` (idempotency + history) | ≥ 5 năm | Frappe record |

### KPI

| ID | Tên | Công thức | Tần suất | Owner báo cáo |
|---|---|---|---|---|
| KPI-IMM06-001 | % Nhân viên có năng lực per khoa | `COUNT(Active) / COUNT(required) × 100%` per dept | Tuần | Workshop Head |
| KPI-IMM06-002 | Số năng lực sắp hết hạn (90d) | `COUNT(Expiring within 90d)` | Tuần | Workshop Head |
| KPI-IMM06-003 | Tỷ lệ hoàn thành đào tạo | `COUNT(Pass) / COUNT(enrolled) × 100%` | Tháng | Tổ HC-QLCL |
| KPI-IMM06-004 | Tỷ lệ đạt trung bình (pass rate) | `AVG(overall_pass_pct)` per program | Tháng | Tổ HC-QLCL |
| KPI-IMM06-005 | Gap coverage Class III | `COUNT(dept vi phạm BR-06-07) / COUNT(dept total)` | Tuần (weekly report) | Workshop Head + VP Block2 |

API: `get_dashboard_stats` trong `api/imm06.py`.

## II.4. Document Control

Workflow PR/WI qua DocType `Asset Document` (IMM-05):

```
Draft → Reviewed → Approved → Effective → Obsolete
```

- **Change control**: Mọi thay đổi PR/WI tạo phiên bản mới; phiên bản cũ chuyển Obsolete.
- **CAPA linkage**: Nếu PR thay đổi do CAPA (IMM-12) → link `capa_ref` vào `Asset Document`.
- **Training notification**: Khi PR/WI Effective → trigger notification Tổ HC-QLCL tạo training session cho audience.

## II.5. Traceability Compliance → Code

| Yêu cầu | Test case | Code/DocType | Audit evidence |
|---|---|---|---|
| NĐ98 §35 — Chứng nhận vận hành | TC-06-009 (UAT-03) | BR-06-05: `signoff_competency()` | `IMM User Competency.supervisor_signoff` + Audit Trail |
| NĐ98 Điều 15.2 — Lưu trữ ≥ 10 năm | `test_audit_chain_intact` | `IMM Audit Trail` immutable | `verify_audit_chain()` pass |
| WHO HTM 4.4 — Authorization gate | TC-06-011 (UAT-04) | BR-06-01: `check_user_authorization()` | `IMM User Competency.status = Active` |
| WHO HTM Annex 5 — Recertification | TC-06-013-015 (UAT-06) | BR-06-03: `auto_expire_competency()`, `check_recertification_due()` | `Competency Alert Log` + Expired status |
| ISO 13485 §8.5.2 — CAPA for revoke | TC-06-018 (UAT-07) | BR-06-06: `revoke_competency()` + VR-08 | `IMM User Competency.revoke_capa_ref` |

## II.6. Audit / Inspection Readiness

Khi auditor đến (cơ quan y tế, kiểm định):

- [ ] Truy xuất competency của user bất kỳ < 5 phút: `get_user_competencies?user=...`
- [ ] Verify audit chain 1 click: `verify_audit_chain(asset)` từ console
- [ ] Coverage Class III per khoa: `get_competency_gaps_by_dept` → filter Class III
- [ ] Training sessions đã thực hiện: Session list filter `status=Closed` → export CSV
- [ ] CAPA chưa đóng liên quan revoke: `revoke_capa_ref` list filter open
- [ ] Role assignment: User Management → filter role Tổ HC-QLCL

**URL truy cập nhanh khi audit:**
- Program list: `/imm06/programs`
- Session list: `/imm06/sessions`
- Competency list: `/imm06/competencies`
- Dashboard: `/imm06/dashboard`
- Audit trail: Admin → `IMM Audit Trail` doctype list

## II.7. Training & Roll-out

| Audience | Nội dung | Thời lượng | WI tham chiếu |
|---|---|---|---|
| Tổ HC-QLCL | Tạo Program, schedule Session, revoke, dashboard | 3h | WI-IMM06-001, WI-IMM06-005 |
| Biomed Engineer | Hướng dẫn Instructor: chấm điểm, complete session | 2h | WI-IMM06-002 |
| Department Manager | Sign-off competency khoa | 1h | WI-IMM06-003 |
| Workshop Head | Verify session, gap report, escalation | 1.5h | WI-IMM06-002, WI-IMM06-005 |
| HTM Technician / Operator | Self-service portal: xem hồ sơ, lịch recert | 30 phút | WI-IMM06-004 |

Training record lưu qua module IMM-06 chính (self-referential training cho system users). Bắt buộc hoàn tất trước go-live Wave 2.

## II.8. Risk Register (Compliance)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| User vận hành Class III khi competency đã Expired (không phát hiện) | Medium | Critical | BR-06-01 gate + BR-06-03 auto-expire + check_user_authorization mỗi WO assign | Tech Lead + Tổ HC-QLCL |
| Recertification bị bỏ sót → thiết bị Class III không có đủ operator (BR-06-07) | Medium | High | Weekly gap report + escalation email Workshop Head + VP Block2 | Workshop Head |
| Revoke không có CAPA khi liên quan incident → mất traceability pháp lý | Low | High | VR-08 enforce tại service layer | Tổ HC-QLCL |
| Program thay đổi nội dung quan trọng không trigger re-cert → user vận hành theo quy trình cũ | Low | High | BR-06-04: `on_update` hook compare critical fields | Tech Lead |
| Audit trail bị tamper → mất bằng chứng pháp lý | Low | Critical | IMM Audit Trail immutable + verify endpoint + regular hash verify | QA Officer |
| Competency data mất sau migration (import lịch sử) | Low | High | Bulk import script có dry-run + validation report trước khi commit | DevOps + Tổ HC-QLCL |

## II.9. Sign-off QMS

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| QMS Officer | | | |
| Tech Lead | | | |
| Module Owner (Tổ HC-QLCL Lead) | | | |
| (Nếu cần) Legal / Pháp chế | | | |

---

## DoD — Hoàn chỉnh

### I. Deployment Plan
- [x] Pre-deploy checklist đầy đủ (10 mục)
- [x] 5 patch files + đăng ký `patches.txt`
- [x] Fixtures cần import liệt kê
- [x] Cấu hình môi trường 3 môi trường (dev/staging/prod)
- [x] Deploy sequence staging + production documented
- [x] Smoke test 13 step
- [x] Rollback < 15 phút có script
- [x] Communication template T-48h + trong + T+1h
- [x] Monitoring 7 metric + ngưỡng alert
- [ ] On-call schedule confirmed (fill trước go-live)
- [x] Reviewed bởi DevOps + Tech Lead

### II. QMS Mapping
- [x] NĐ98/2021 ≥ 4 điều khoản đối chiếu
- [x] WHO HTM ≥ 4 section đối chiếu
- [x] ISO 13485 ≥ 5 điều đối chiếu
- [x] PR 3 + WI 5 tạo cho major workflows
- [x] HS retention 10 năm cho audit-relevant (4 HS)
- [x] KPI 5 metric có công thức + tần suất + owner
- [x] Audit-readiness checklist ≥ 6 mục
- [x] Training plan cho mọi 5 role
- [x] Risk register 6 mục với mitigation
- [x] Sign-off section sẵn sàng
