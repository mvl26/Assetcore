# 08 — Deployment (IMM-13)

| Mục | Giá trị |
|---|---|
| Module | IMM-13 — Ngừng sử dụng và điều chuyển |
| Đợt triển khai | Đợt 3 (theo `architecture` line 278) |
| Trạng thái | Pre-deployment — checklist + QMS mapping |
| Liên kết | [04 Backend](./04_Backend_Design.md) · [09 Release](./09_Release.md) · `assetcore-deployment` skill |

---

## I. Môi trường

| Env | Mục đích | Site | Deploy thủ công / CI |
|---|---|---|---|
| Dev | BE/FE dev daily | `dev.assetcore.local` | thủ công |
| Staging | UAT + integration test | `staging.assetcore.<khách>` | CI auto deploy on `feature/wave-3/*` merge |
| Prod | Bệnh viện production | `<site>.assetcore.<khách>` | release tag, có gate manual |

---

## II. Pre-flight checklist

- [ ] Tag release: `assetcore-v3.x-imm13` (Đợt 3, IMM-13 milestone)
- [ ] Branch merge: feature/wave-3/imm-13 → develop → master
- [ ] DocType JSON 4 file + child + single — passed migrate dry-run
- [ ] Workflow JSON 3 file — load thành công, transition khớp [04 §III](./04_Backend_Design.md#iii-workflow)
- [ ] Fixtures: role + permission `imm_13_*.json` exported và idempotent
- [ ] Test pass 100% (xem [07](./07_Testing_QA.md#ix-test-execution-checklist-release-gate))
- [ ] Backup site trước khi migrate
- [ ] Rollback plan đã viết (xem §VI)

---

## III. Deploy steps

### III.1 Migration

```bash
# Trên server staging/prod, đứng tại frappe-bench
bench --site <site> backup --with-files
bench update --pull --reset
bench --site <site> migrate
bench --site <site> install-app assetcore   # nếu site chưa có
bench --site <site> migrate                  # đảm bảo DocType IMM-13 + workflow load
bench --site <site> clear-cache
bench restart
```

### III.2 Fixtures

```bash
bench --site <site> import-fixtures   # load roles + permissions + naming series
```

Fixtures dự kiến (chốt khi BE scaffold):
- `assetcore/fixtures/role.json` — append 5 role nếu chưa có (IMM-13 phần lớn dùng role chung)
- `assetcore/fixtures/imm_13_workflow.json` — 3 workflow
- `assetcore/fixtures/imm_13_settings.json` — single doctype default values

### III.3 FE build

```bash
cd apps/assetcore/frontend
pnpm install
pnpm run build          # output frontend/dist
bench build --app assetcore
```

### III.4 Restart

```bash
bench restart           # supervisor + nginx reload
```

### III.5 Smoke test (10 phút)

- Login → menu IMM-13 hiển thị.
- Tạo 1 reassignment giả lập (asset test) — full chain Confirm × 2 → Approve → Asset.location đổi.
- Tạo 1 stand-down — Asset → Out of Service.
- Tạo 1 retire proposal — IMM-14 listener nhận.
- Audit chain endpoint trả 200.

---

## IV. QMS Mapping (theo Architecture §"Lớp QMS")

| Mã QMS | Tên tài liệu (dự kiến) | Loại | Tham chiếu file BE/FE |
|---|---|---|---|
| QC-IMMIS-04 | Chính sách quản trị retirement & decommissioning | L1/QC | – |
| PR-IMMIS-13-01 | Quy trình stand-down thiết bị | PR/SOP | `services/imm13.py:stand_down` |
| PR-IMMIS-13-02 | Quy trình điều chuyển nội viện | PR/SOP | `services/imm13.py:request_reassignment` + `commit_reassignment` |
| PR-IMMIS-13-03 | Quy trình replacement review | PR/SOP | `services/imm13.py:create_replacement_review` |
| WI-IMMIS-13-01 | Hướng dẫn KTV nhập đề xuất | WI | UI flow [06 §II.1](./06_Frontend_Design.md) |
| WI-IMMIS-13-02 | Hướng dẫn QA Officer ký residual risk | WI | UI flow [06 §II.4](./06_Frontend_Design.md) |
| BM-IMMIS-13-01 | Mẫu biên bản stand-down | BM | DocType `IMM Asset Reassignment` view |
| BM-IMMIS-13-02 | Mẫu Replacement Review | BM | DocType `IMM Replacement Review` |
| BM-IMMIS-13-03 | Mẫu Residual Risk Assessment (theo WHO §3.2) | BM | DocType `IMM Residual Risk` |
| HS-LOG-IMMIS-13-01 | Nhật ký audit chain các quyết định retirement | HS | Audit Trail hash chain |
| HS-REP-IMMIS-13-01 | Báo cáo retire proposal định kỳ | HS | Endpoint `dashboard_metrics` |
| KPI-DASH-IMMIS-13 | Dashboard IMM-13 (5 KPI) | KPI-DASH | `IMM13Dashboard.vue` |

*(Mã QMS chính thức do Tổ HC-QLCL phát hành — số hiệu trên là đề xuất theo pattern các module có sẵn.)*

---

## V. Permission & Role matrix (deploy gate)

5 role overlap với Wave 1 + Wave 2:
- `IMM HTM Engineer` — đã có (Wave 1)
- `IMM Department Head` — mới hoặc tái dùng từ IMM-04
- `IMM Operations Manager` — đã có
- `IMM QA Officer` — đã có
- `IMM Finance Officer` — mới (cần tạo + DocPerm)
- `IMM Auditor` — đã có

**Deploy step**: kiểm tra `fixtures/role.json` đầy đủ; nếu thiếu role mới → append + `bench import-fixtures`.

---

## VI. Rollback plan

Nếu sau deploy phát hiện bug nghiêm trọng:

1. **Bug code-only (không đụng schema)**: revert commit + `bench update --reset` về tag trước.
2. **Bug schema (DocType field sai / migration sai)**:
   - Restore từ backup `bench --site <site> restore <backup-file>`.
   - Re-deploy version trước.
3. **Bug fixtures (workflow / role)**:
   - Xóa workflow JSON khỏi DocType `Workflow` (manual hoặc patch).
   - Re-import fixtures phiên bản cũ.

**Tiêu chí kích hoạt rollback**: ≥ 1 trong các trigger sau xảy ra trong 24h đầu sau deploy:
- Asset state bị set sai do bug commit_reassignment (data corruption).
- Audit hash chain gãy (verify endpoint return False với hồ sơ vừa tạo).
- > 5 user báo lỗi không submit được (trên log Sentry).

---

## VII. Monitoring & Alerts

- Log: scheduler events `escalate_stale_oos`, `verify_location_consistency`, `retry_handoff_imm14` xuất ra `bench logs`. Alert nếu fail ≥ 3 lần liên tiếp.
- Metric: số reassignment tạo / ngày, số retire proposal pass IMM-14 / tuần — track qua dashboard.
- Sentry (nếu có): all `IMM13_HANDOFF_IMM14_FAIL` → alert ngay.

---

## VIII. Known limitations at deploy

- Multi-site reassignment: chưa hỗ trợ (xem [02 §IV.6 Open issues](./02_Analysis_Design.md#iv6-out-of-scope--open-issues)).
- Bulk reassignment: chưa hỗ trợ.
- Mobile native: chưa.
- Tích hợp HIS để check clinical booking: stub trả về `False` mặc định nếu chưa có HIS gateway.

---

*Deployment doc — cập nhật khi BE scaffold hoàn tất và CI/CD pipeline chuẩn hóa cho Đợt 3.*
