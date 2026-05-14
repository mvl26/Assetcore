# 04 — Thiết kế Backend (IMM-07 — Theo dõi hiệu suất)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Trạng thái | Skeleton — BE chưa scaffold (Wave 3) |
| Cập nhật | 2026-05-10 |

---

## 1. Tổng quan kiến trúc

IMM-07 tuân thủ pattern 3-tier AssetCore (CONVENTIONS §2):
- **Controller** (DocType `.py`) → dispatch.
- **Service** (`assetcore/services/imm07.py`) → business logic (build snapshot, verify, rule eval).
- **Repository** (`assetcore/repositories/imm07_repo.py`) → data access events nguồn + snapshot.

Scheduler (Frappe `scheduler_events`) trigger build snapshot theo chu kỳ.

## 2. Domain Model — DocType (đề xuất)

| DocType | Mô tả 1 dòng |
|---|---|
| `AC KPI Catalog` | Master KPI: code, công thức, đơn vị, ngưỡng cảnh báo |
| `AC KPI Snapshot` | Bản chốt KPI theo chu kỳ + scope, có trạng thái verify |
| `AC KPI Value` | Child table của Snapshot — giá trị từng KPI + event_ids nguồn |
| `AC Performance Rule` | Quy tắc phát replacement signal (KPI + threshold + N chu kỳ) |
| `AC Replacement Signal` | Cảnh báo thay thế thiết bị, có trạng thái xử lý |

Field detail (fieldname/type/link/mandatory) — *(Thiết kế trong sprint Wave 3 sprint 1, refer skill `assetcore-doctype-designer`)*.

## 3. Workflow

- `AC KPI Snapshot` có workflow: `Draft → Computed → Verified → Closed` (+ `Reopened` exception).
- `AC Replacement Signal`: `Open → Reviewing → Resolved | Dismissed`.

State machine chi tiết (allow_edit role, transitions, docstatus mapping) — *(Thiết kế trong sprint Wave 3, refer skill `assetcore-workflow-builder`)*.

## 4. Service Layer

File dự kiến: `assetcore/services/imm07.py`. Trách nhiệm:
- `build_snapshot(period, scope)` — tổng hợp event nguồn → snapshot.
- `verify_snapshot(snapshot, verifier)` — chuyển trạng thái verified, kiểm tra 4-mắt.
- `evaluate_rules(snapshot)` — quét rule, tạo signal nếu vượt ngưỡng.
- `close_signal(signal, resolution)` — đóng signal kèm lý do.

Service tách validator, business rule, orchestration — refer CONVENTIONS §2.

## 4b. Repository Layer

File dự kiến: `assetcore/repositories/imm07_repo.py`. Trách nhiệm:
- `load_events(period, scope)` — query `AC Lifecycle Event` từ IMM-04/08/09/11/12.
- `save_snapshot(snapshot)` — insert + child rows atomic.
- `find_open_signals(asset)` — dedupe.

Không chứa business logic. Refer CONVENTIONS §2.

## 5. API Layer

File dự kiến: `assetcore/api/imm07.py`. Endpoint chi tiết liệt kê tại [05_API_Specification.md](./05_API_Specification.md). Mọi method dùng decorator `@frappe.whitelist()` + envelope chuẩn (CONVENTIONS §3).

## 6. Audit Trail

- Mọi chuyển trạng thái Snapshot/Signal sinh `AC Lifecycle Event` (event_type: `kpi_snapshot_verified`, `replacement_signal_raised`, …).
- Verify ghi `verified_by` + `verified_at` (immutable).
- Refer Architecture §"Lớp QMS" cho quy ước log.

## 7. Background jobs / Scheduler

`hooks.py` `scheduler_events`:
- `daily`: build snapshot chu kỳ ngày (asset 24/7).
- `weekly`: build snapshot tuần.
- `monthly` (cron đầu tháng): build snapshot tháng + evaluate rule.

*(Cấu hình thực tế — Wave 3 sprint 2)*.

## 8. Integration

- **Inbound** từ: IMM-04 (asset master), IMM-08/09/11/12 (lifecycle event).
- **Outbound** tới: IMM-13 (replacement signal feed), IMM-16 (compliance scorecard), IMM-17 (predictive feature store).
- Cơ chế: shared `AC Lifecycle Event` + Frappe doc events. Không gọi cross-module API trực tiếp.

## 9. Migration & Patch

Scaffold lần đầu tại Wave 3. Patch path: `assetcore/patches/wave3/imm07_*.py`. Không có migration từ data legacy (module mới hoàn toàn).

## 10. Non-functional

- Build snapshot ≤ 5 phút cho 5.000 asset (NFR §V.1).
- Snapshot bất biến sau verify (BR-07-02).
- Audit trail bắt buộc (NĐ98).

---

## DoD — File 04 (IMM-07)

- [x] DocType list (tên + mô tả 1 dòng)
- [x] Service / Repository skeleton
- [x] Workflow state list
- [x] Scheduler hook plan
- [ ] *(Pending Wave 3 scaffold: field detail, workflow JSON, service body)*
