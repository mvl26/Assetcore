# 08 — Triển khai & Tuân thủ (Deployment & QMS)

| Mục | Giá trị |
|---|---|
| Module | IMM-`<XX>` |
| Phạm vi | Per-module |
| Owner | DevOps + Tech Lead + QMS Officer |
| Sign-off | Trước go-live (gate) |
| Liên kết | `assetcore-deployment` skill · 04 Backend · 07 §III Security |

> **Mục đích**: Kế hoạch deploy chi tiết + QMS / compliance mapping. Rollback < 15 phút khi sự cố. Compliance là gate cuối cùng trước prod.

---

# Phần I — Deployment Plan

## I.1. Pre-deployment checklist
**Viết gì**: Tick-list trước window — PR merged, CI green, UAT pass, Security pass, QMS reviewed, User Guide + Release Notes viết, backup < 24h, communication T-48h, rollback tested ở staging.

## I.2. Stack & versioning
**Viết gì**: Version Frappe/ERPNext/Python/Node/MariaDB/Redis. App version trước/sau. Cập nhật `__init__.py:__version__`.

## I.2b. Cấu hình môi trường thực nghiệm (Environment configuration)
**Viết gì**: Bảng `Thành phần · Phiên bản · Cấu hình`. Cover cả 3 môi trường (dev / staging / prod):
- OS server (Ubuntu/RHEL version)
- CPU / RAM / Disk SSD
- MariaDB version + buffer pool / max connections
- Redis maxmemory + eviction policy
- nginx worker processes + max body size
- Python venv path + bench branch
- Node version + npm registry
- supervisor program count
- Backup target (local + off-site S3 / Drive)
- Network: domain + SSL cert provider + firewall rule

**Mẹo**: Giữ bảng này đồng bộ với `assetcore/docs/architecture/Ho_so_kien_truc_IMMIS.md` nếu có. Khi reproduce ở bệnh viện mới — copy bảng này.

## I.3. Deployment artefacts
**Viết gì**: 4 mục con —
- **Patch files**: bảng `Patch · File · Mô tả · Idempotent?` + đăng ký `patches.txt`
- **Fixtures cần re-import**: role, role_profile, workflow, custom_field
- **Frontend build**: `cd frontend && npm ci && npm run build && bench build --app assetcore`
- **New dependencies** (Python/Node) + lock file update

## I.4. Deploy sequence
**Viết gì**: 2 mục con —
- **Staging** (chạy T-1 ngày): SSH + maintenance + backup + pull code + setup requirements + npm build + bench build + migrate + import fixtures + clear cache + restart + smoke
- **Production**: lặp + maintenance window + backup off-site + on-call

## I.5. Schema migration risk
**Viết gì**: 2 bảng —
- `Change · Risk · Mitigation` (drop/rename/NOT NULL big table/workflow rename/DocPerm tightening)
- Long-running migration (batch 1000 record, idempotent, lock policy)

## I.6. Smoke test sau deploy
**Viết gì**: Bảng `Step · Cách · Expected`. ≥ 10 step (login, hub, dashboard, list, create, transition, audit, API ping, cron registered, frontend assets).

## I.7. Rollback plan
**Viết gì**: 2 mục con —
- **Trigger condition** (login break / data corruption / DB sụp / critical permission bug)
- **Quick rollback < 15 phút**: maintenance + restore DB + checkout commit cũ + rebuild + restart
- **Forward fix** khi đã có user mutation: hotfix branch

## I.8. Communication
**Viết gì**: 3 template — Trước T-48h (email user + tính năng mới), Trong (status page + Slack on-call), Sau T+1h (email hoàn tất + URL + báo lỗi).

## I.9. Monitoring & alerting (T+24h)
**Viết gì**: Bảng `Metric · Ngưỡng cảnh báo · Tool`. Error rate, login fail, API p95, DB CPU, disk, audit verify fail.

## I.10. Post-deployment
**Viết gì**: Tick-list — git tag, Release Notes update thực tế, Traceability chốt cột Released-in, backup config, post-mortem nếu có incident, retro sprint kế.

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu trúc QMS reference
**Viết gì**: Bảng `Cấp · Tên · Vai trò · ID format`. QC (Quality Charter), PR (Procedure), WI (Work Instruction), BM (Business Master), HS (Historical Snapshot), KPI.

## II.2. Trace yêu cầu pháp lý
**Viết gì**: 4-5 mục con cho mỗi quy định:
- **NĐ98/2021/NĐ-CP** — bắt buộc cover
- **Quyết định 3107/QĐ-BYT** (Danh mục TTBYT) — nếu áp
- **WHO HTM** — bắt buộc cover
- **ISO 13485 / ISO 14971** — nếu áp
- **Nội bộ tổ chức** — bệnh viện-specific

Mỗi mục: bảng `Điều/Khoản · Yêu cầu · Áp lên module qua · Doc/Code reference`.

## II.3. QMS artefact tạo bởi module
**Viết gì**: 5 mục con —
- **PR (Procedure)**: bảng `ID · Tên · File · Workflow trong code`
- **WI (Work Instruction)**: bảng `ID · Tên · Audience · File`. Kèm screenshot UI
- **BM (Business Master)**: master data + change-control owner
- **HS (Historical Snapshot)**: bảng `ID · Source · Retention · Format`. NĐ98 ≥ 5 năm
- **KPI**: bảng `ID · Tên · Công thức · Tần suất · Owner báo cáo`

## II.4. Document control
**Viết gì**: Workflow PR/WI Draft → Reviewed → Approved → Effective → Obsolete. Implement qua DocType `Asset Document`. Change-control + CAPA linkage.

## II.5. Traceability compliance → code
**Viết gì**: Bảng `Yêu cầu · Test case · Code/DocType · Audit evidence`. Subset của 09 §III — chỉ compliance row.

## II.6. Audit / inspection readiness
**Viết gì**: Tick-list khi auditor đến — truy xuất WO < 5 phút, verify chain 1 click, KPI quarter, document control hiện Effective + Obsolete, role assignment, CAPA chưa đóng. URL truy cập nhanh.

## II.7. Training & roll-out
**Viết gì**: Bảng `Audience · Nội dung · Thời lượng · WI tham chiếu`. Training record qua DocType `Training Record` (IMM-06).

## II.8. Risk register (compliance)
**Viết gì**: Bảng `Risk · Likelihood · Impact · Mitigation · Owner`. ≥ 4 risk.

## II.9. Sign-off
**Viết gì**: Bảng `Role · Người · Ngày · Chữ ký`. QMS Officer + Tech Lead + Module Owner + (nếu cần) Legal.

---

## DoD — File 08 hoàn chỉnh

### I. Deployment Plan
- [ ] Pre-deploy checklist đầy đủ
- [ ] Patch file + đăng ký `patches.txt`
- [ ] Fixture cần import liệt kê
- [ ] **Cấu hình môi trường thực nghiệm** rõ cho cả 3 môi trường (dev / staging / prod)
- [ ] Sequence chạy được trên staging trước
- [ ] Smoke test ≥ 10 step
- [ ] Rollback < 15 phút khả thi
- [ ] Communication template
- [ ] Monitoring metric + ngưỡng alert
- [ ] On-call schedule
- [ ] Reviewed bởi DevOps + Tech Lead

### II. QMS Mapping
- [ ] Đối chiếu NĐ98 ≥ 3 điều khoản
- [ ] Đối chiếu WHO HTM lifecycle
- [ ] PR/WI tạo cho mọi major workflow
- [ ] HS retention 5 năm cho audit-relevant
- [ ] KPI có công thức + tần suất + owner
- [ ] Audit-readiness checklist ≥ 5 mục
- [ ] Training plan cho mọi role
- [ ] Risk register ≥ 4 mục
- [ ] Sign-off đầy đủ
