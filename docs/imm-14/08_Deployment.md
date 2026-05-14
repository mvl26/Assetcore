# 08 — Deployment (IMM-14 Giải nhiệm thiết bị)

| Mục | Giá trị |
|---|---|
| Module | IMM-14 — Giải nhiệm thiết bị |
| Phạm vi | Deploy plan + Fixture + QMS Mapping + Rollback |
| Owner | DevOps + QLCL Officer |
| Liên kết | [04 Backend](./04_Backend_Design.md) · [09 Release](./09_Release.md) |

> Module thuộc **Đợt 3** (Architecture line 278). Triển khai sau khi data lineage và QMS đã ổn định ở Đợt 1+2.

---

## 1. Môi trường

| Env | Site | Mục đích | Người duyệt deploy |
|---|---|---|---|
| Dev | dev.assetcore.local | Code + unit test + workflow smoke | BE Lead |
| Staging | staging.assetcore.\<khách hàng> | UAT + performance | BA + QA |
| Production | \<site khách hàng> | Run thật | DevOps + Trưởng phòng VT-TBYT |

Deploy theo skill `.claude/skills/assetcore-deployment/SKILL.md` — KHÔNG bypass.

---

## 2. Pre-requisite (Đợt 3)

- Đợt 1 (IMM-04, 05, 08, 09, 11, 12) đã go-live: registry asset ổn định, hồ sơ pháp lý đã có, WO engine chạy.
- Đợt 2 (IMM-15 phụ tùng + IMM-16 tuân thủ) đã go-live: kho phụ tùng đối soát được.
- IMM-13 (Đợt 3 — cùng đợt) đã deploy trước IMM-14 *(IMM-14 phụ thuộc cứng vào IMM-13 Decommission Decision)*.
- Bench version ≥ Frappe v15 production stable.

---

## 3. Deploy plan

### 3.1. Order of operation

1. `bench --site <site> migrate` — apply DocType mới (`IMM Asset Closure`, `IMM Reconciliation Line`, `IMM Sanitization Item`, `IMM Closure Document`).
2. Import fixture (xem §4) — workflow JSON, role, permission, sanitization template.
3. `bench build` — FE bundle có route `/imm-14`.
4. Restart supervisor: `bench restart`.
5. Run smoke test: tạo + approve 1 closure trên staging.
6. Toggle feature flag `imm14_enabled=true` cho production.

### 3.2. Patches

Liệt kê patch dự kiến trong `assetcore/patches.txt`:

- `assetcore.patches.v3_0.add_asset_has_patient_data` — thêm field `has_patient_data` vào `AC Asset`, default false.
- `assetcore.patches.v3_0.create_imm14_role` — tạo role `IMM-14 Approver`, `IMM-14 DPO`, `IMM-14 Accountant`, `IMM-14 HTM Engineer`, `IMM-14 Storekeeper`, `IMM-14 QLCL Officer`.
- `assetcore.patches.v3_0.migrate_legacy_closure` — optional, chạy thủ công, import asset đã thanh lý trước go-live.

*(Tên patch chốt sprint W3-4.)*

---

## 4. Fixture

Fixtures cần install — đặt tại `assetcore/fixtures/`:

| File | Nội dung |
|---|---|
| `imm14_workflow.json` | Workflow `IMM Asset Closure` (8 state, transitions) |
| `imm14_role.json` | 6 role IMM-14 + DocPerm |
| `imm14_sanitization_template.json` | Template checklist theo classification A/B/C/D |
| `imm14_print_format.json` | Closure Report A4 PDF |
| `imm14_dashboard.json` | Dashboard `End-of-life Cockpit` |
| `imm14_workspace.json` | Workspace shortcut menu IMM-14 |

Hooks export trong `hooks.py` `fixtures = [...]`. *(Sprint W3-4 — hiện `hooks.py` chưa có — sẽ append khi scaffold.)*

---

## 5. QMS Mapping

Theo `Ho_so_kien_truc_IMMIS.md` line 414 (QC-IMMIS-04) + line 425–430 (QMS doc tree IMM-14).

| QMS code | Tên tài liệu | Artifact trong AssetCore | Nơi lưu |
|---|---|---|---|
| QC-IMMIS-04 | Chính sách ngừng sử dụng, điều chuyển, giải nhiệm và đóng vòng đời asset | `docs/imm-14/02_Analysis_Design.md` + workflow JSON | QMS điện tử/IMMIS/L1 |
| PR-IMMIS-14-01 | SOP Khởi tạo closure record từ Decommission Decision | UC-14-01 + service `create_from_decision` | QMS điện tử/IMMIS/14-* |
| PR-IMMIS-14-02 | SOP Đối soát kho – kế toán – hồ sơ trước closure | UC-14-04, UC-14-05, UC-14-06 + ReconciliationService | QMS điện tử/IMMIS/14-* |
| PR-IMMIS-14-03 | SOP Phê duyệt closure và đóng vòng đời asset | UC-14-07 + finalize + lifecycle event | QMS điện tử/IMMIS/14-* |
| WI-IMMIS-14-01 → 04 | Hướng dẫn công việc giải nhiệm | Help text trong UI + tooltip + user guide [09](./09_Release.md) | QMS điện tử/IMMIS/14-* |
| BM-IMMIS-14-01 | Biểu mẫu Closure Report | Print Format `imm_14_closure_report` | QMS điện tử/IMMIS/14-* |
| HS-LOG-IMMIS-14-01 | Nhật ký giải nhiệm | `IMM Audit Trail` filter doctype = IMM Asset Closure | QMS điện tử/IMMIS/14-* |
| HS-REC-IMMIS-14-01, 02 | Hồ sơ closure record + sanitization | `IMM Asset Closure` (submitted) + `IMM Sanitization Item` | DB + S3 attachment |
| HS-REP-IMMIS-14-01 | Báo cáo end-of-life | Dashboard `/imm-14/dashboard` + export PDF | BI/IMMIS |
| KPI-DASH-IMMIS-14 | Dashboard cockpit IMM-14 | `/imm-14/dashboard` | BI/IMMIS |

Owner: Nhóm HTM, KH-TC, Nhóm Kho, CMMS/IMMIS, CNTT, QLCL.

---

## 6. Permission seed (production)

Sau install fixture, gán role:

| Role | Gán cho user nhóm |
|---|---|
| IMM-14 HTM Engineer | Workshop / Tổ TBYT (3–5 người) |
| IMM-14 Storekeeper | Kho trung tâm (1–2 người) |
| IMM-14 Accountant | Phòng KH-TC / TCKT (2 người) |
| IMM-14 DPO | CNTT / DPO (1 người) |
| IMM-14 QLCL Officer | Tổ HC-QLCL & Risk (1–2 người) |
| IMM-14 Approver | Trưởng phòng VT-TBYT (1 người) |

DevOps verify ma trận role × user trước go-live.

---

## 7. Backup & Rollback

### 7.1. Backup

Trước migrate:

```bash
bench --site <site> backup --with-files
```

Lưu vào `/backups/imm14-pre-migrate-YYYYMMDD/`.

### 7.2. Rollback plan

Nếu phát hiện lỗi nghiêm trọng sau go-live:

1. Toggle feature flag `imm14_enabled=false` — ẩn route + endpoint.
2. Nếu cần rollback DB: restore backup gần nhất (≤24h trước) — chỉ chấp nhận nếu chưa có closure thật được duyệt.
3. Nếu đã có closure thật: KHÔNG rollback DB; thay bằng patch hot-fix.
4. Notify stakeholders (Trưởng phòng + KH-TC + QLCL) trong 1 giờ.

### 7.3. Disaster recovery

- Closure record giữ ≥10 năm theo NĐ98 → backup hàng ngày + replicate offsite.
- Print Format PDF closure report attach mỗi closure submitted (immutable artifact).

---

## 8. Smoke validation post-deploy

Checklist 10 mục — DevOps chạy ngay sau deploy:

- [ ] Route `/imm-14` load 200, list page render.
- [ ] Tạo closure draft từ 1 decision IMM-13 staging.
- [ ] Workflow state machine đầy đủ 8 state visible.
- [ ] DocType `IMM Asset Closure` có đúng số field theo design.
- [ ] Permission: HTM Engineer KHÔNG approve được; Department Head approve được.
- [ ] Sanitization template load đúng theo classification.
- [ ] Print Format Closure Report xuất PDF không lỗi font tiếng Việt.
- [ ] Dashboard `/imm-14/dashboard` load <3s.
- [ ] Hook `imm14_asset_closed` emit + IMM-15 cron nhận.
- [ ] Audit Trail có log finalize sau khi approve test.

---

## 9. Release versioning

- Module IMM-14 release dưới major version `v3.x` của AssetCore (`v3.0.0` cho Đợt 3 GA).
- Tag git: `v3.0.0-imm14-ga`.
- Release note đặt tại [09 Release](./09_Release.md).

---

*Hết file 08. Deployment runbook chi tiết viết khi sprint W3-4 close — refer skill `assetcore-deployment`.*
