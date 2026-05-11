# 08 — Triển khai & Tuân thủ (IMM-07 — Theo dõi hiệu suất)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Đợt triển khai | 3 (sau IMM-04/05/08/09/11/12 đã ổn định) |
| Cập nhật | 2026-05-10 |

---

# Phần I — Deployment Plan

## I.1. Pre-deployment checklist

- [ ] Tất cả module nguồn (IMM-04, 08, 09, 11, 12) đã production và sinh `AC Lifecycle Event` đúng schema.
- [ ] Baseline KPI đã khảo sát + chốt KPI catalog.
- [ ] Performance Rule đã thống nhất với QLCL.
- [ ] Test coverage ≥ 70% cho `services/imm07.py`.
- [ ] UAT 7 scenario pass.
- [ ] DocPerm + RBAC reviewed (skill `assetcore-security`).

## I.2. Stack & versioning

- Frappe v15 + ERPNext v15.
- Python 3.12, MariaDB 10.6+.
- Module version: `assetcore` patch level Wave 3.

## I.2b. Cấu hình môi trường

| Env | Mục đích | Schedule build snapshot |
|---|---|---|
| dev | Develop | ad-hoc |
| staging | UAT + perf test | giống prod |
| prod | Vận hành | daily 02:00, weekly Mon 02:30, monthly 1st 03:00 |

## I.3. Deployment artefacts

- DocType JSON: `AC KPI Catalog`, `AC KPI Snapshot`, `AC KPI Value`, `AC Performance Rule`, `AC Replacement Signal`.
- Workflow JSON: `imm_07_kpi_snapshot_workflow.json`, `imm_07_signal_workflow.json`.
- Fixtures: `fixtures/imm07_kpi_catalog.json`, `fixtures/imm07_performance_rule.json`, `fixtures/role.json` (append role nếu cần).
- Code: `services/imm07.py`, `repositories/imm07_repo.py`, `api/imm07.py`.
- FE: `frontend/src/views/imm07/*`, `frontend/src/types/imm07/*`.

*(Sinh khi BE/FE scaffold Wave 3)*.

## I.4. Deploy sequence

1. `bench migrate` — cài DocType + Workflow.
2. `bench --site <site> import-fixtures` — KPI catalog + rule mặc định.
3. Restart supervisor.
4. Smoke test (refer §I.6).
5. Bật scheduler IMM-07 trong `hooks.py`.

## I.5. Schema migration risk

- Module mới — không ảnh hưởng schema cũ.
- Snapshot dữ liệu nhiều: partition table khi >1M rows (Wave 4 nếu cần).

## I.6. Smoke test sau deploy

- Tạo 1 snapshot manual cho 1 asset → check `AC KPI Value` rows.
- Verify snapshot bằng tài khoản QLCL → status Verified.
- Cockpit load.
- Trigger rule eval → signal sinh.

## I.7. Rollback plan

- Disable scheduler trong `hooks.py` → restart supervisor.
- Roll back code: `git revert` patch Wave 3 IMM-07 → `bench migrate`.
- Snapshot data đã sinh giữ lại (read-only); xoá nếu QLCL yêu cầu.

## I.8. Communication

- Thông báo BGĐ + QLCL + Workshop trước go-live 1 tuần.
- Slack/email khi scheduler chạy lần đầu.

## I.9. Monitoring & alerting (T+24h)

- Frappe error log: filter `imm07`.
- Alert: scheduler fail / snapshot status Incomplete kéo dài.
- KPI: số snapshot Computed mỗi ngày.

## I.10. Post-deployment

- Daily standup tuần đầu.
- Hồi cứu UAT bug T+7, T+30.

---

# Phần II — QMS / Compliance Mapping

## II.1. Cấu trúc QMS reference

Theo Architecture line 342–346 (QMS IMMIS-07):

| QMS Layer | Mã | Mô tả |
|---|---|---|
| PR/SOP | PR-IMMIS-07-01..03 | Quy trình theo dõi hiệu suất |
| WI | WI-IMMIS-07-01..04 | Hướng dẫn công việc tổng hợp/verify/handle signal |
| BM | BM-IMMIS-07-01 | Biểu mẫu/checklist KPI |
| HS | HS-LOG-IMMIS-07-01, HS-REC-IMMIS-07-01, HS-REP-IMMIS-07-01 | Nhật ký, hồ sơ, báo cáo |
| KPI-DASH | KPI-DASH-IMMIS-07 | Dashboard cockpit |

## II.2. Trace yêu cầu pháp lý

| Quy định | Yêu cầu | Artefact đáp ứng |
|---|---|---|
| NĐ98/2021 | Lưu vết sự kiện vòng đời | `AC Lifecycle Event` + audit trail Snapshot/Signal |
| WHO HTM | KPI vận hành chuẩn | KPI Catalog + Snapshot |
| QMS nội bộ | Document control | PR/WI/BM/HS-IMMIS-07 |

## II.3. QMS artefact tạo bởi module

- HS-LOG-IMMIS-07-01: log build/verify/close (auto từ event).
- HS-REC-IMMIS-07-01: hồ sơ snapshot (immutable).
- HS-REP-IMMIS-07-01: báo cáo định kỳ ký số (auto export).

## II.4. Document control

KPI catalog + Performance Rule version-controlled qua DocType có `version` + change request workflow (BR-07-05).

## II.5. Traceability compliance → code

| Yêu cầu | Code path |
|---|---|
| Audit trail | `services/imm07.py::_emit_event()` *(Wave 3 implement)* |
| RBAC | `assetcore/fixtures/role.json` + DocPerm trên 5 DocType IMM-07 |
| Verify 4-mắt | `services/imm07.py::verify_snapshot()` |

## II.6. Audit / inspection readiness

- Báo cáo định kỳ PDF ký số sẵn sàng cung cấp khi Sở Y tế kiểm tra.
- Drill-down từ KPI → event → root_record (PM/CM/Cal) đầy đủ.

## II.7. Training & roll-out

- Workshop training: nhập event chuẩn (1h).
- QLCL training: verify + xử lý signal (2h).
- BGĐ: hướng dẫn cockpit (30 phút).

## II.8. Risk register (compliance)

- Risk dữ liệu nguồn không đầy đủ → mitigation: snapshot Incomplete + alert.
- Risk verify trễ → mitigation: SLA 5 ngày làm việc, escalation QLCL trưởng.

## II.9. Sign-off

- QLCL trưởng + CNTT trưởng + BGĐ phụ trách thiết bị.

---

## DoD — File 08 (IMM-07)

- [x] Deployment plan
- [x] Smoke test playbook
- [x] Rollback plan
- [x] QMS mapping (PR/WI/BM/HS/KPI-DASH)
- [ ] *(Pending: production config sau Wave 3 scaffold)*
