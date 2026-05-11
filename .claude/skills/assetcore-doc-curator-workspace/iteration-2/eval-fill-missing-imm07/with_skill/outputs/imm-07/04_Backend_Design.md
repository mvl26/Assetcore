# IMM-07 — Thiết kế Backend

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Trạng thái | Skeleton (BE chưa scaffold — Wave 3) |

## I. DocType dự kiến

Field detail và schema JSON *(Thiết kế trong Sprint Wave 3.1, refer `assetcore-doctype-designer` skill)*. Tại thời điểm này chỉ liệt kê DocType + 1 dòng mục đích.

| DocType | Mục đích |
|---|---|
| IMM Performance Record | Bản ghi KPI tổng hợp theo asset × kỳ (tháng/quý) |
| IMM KPI Definition | Định nghĩa công thức KPI, có version |
| IMM KPI Definition Version | Version history của định nghĩa, audit trail thay đổi |
| IMM Data Quality Flag | Cờ dữ liệu thiếu / outlier cần review |
| IMM Replacement Signal | Tín hiệu phát hiện thiết bị xuống cấp, đưa sang IMM-13 |
| IMM Performance Threshold | Cấu hình ngưỡng cảnh báo theo loại thiết bị |

Reference: tuân thủ naming convention `IMM <Domain> <Entity>` (CONVENTIONS.md §1) và link tới `AC Asset`, `Department`, `IMM Device Model` đã có từ IMM-04/05.

## II. Service layer (3-tier)

Tuân thủ kiến trúc API → Service → Repository (CONVENTIONS.md §2). Skeleton:

```
assetcore/
├── api/imm07.py             # endpoint whitelist (mỏng, không logic)
├── services/imm07.py        # business logic: aggregator, KPI calc, signal
├── repositories/
│   └── performance_repo.py  # truy vấn dữ liệu nguồn (PM/CM/Cal)
```

Service chính dự kiến:
- `PerformanceAggregatorService.run_nightly()` — orchestrator scheduler.
- `KpiCalculatorService.compute(asset, period)` — pure function, dễ test.
- `DataQualityGateService.evaluate(record)` — flag missing/outlier.
- `ReplacementSignalService.evaluate(asset)` — so ngưỡng và phát signal.

Method signature đầy đủ *(Thiết kế trong Sprint Wave 3.1)*.

## III. Workflow

| DocType | State machine | Tham chiếu |
|---|---|---|
| IMM Replacement Signal | Open → Acknowledged → Reviewing → Resolved/Dismissed | `03_Diagrams.md` §V |
| IMM Data Quality Flag | Open → Verified / Ignored | *(Sprint Wave 3.1)* |
| IMM KPI Definition Version | Draft → Approved → Active → Retired | *(Sprint Wave 3.2)* |

Workflow JSON chi tiết (states + transitions + roles) refer `assetcore-workflow-builder` skill khi scaffold.

## IV. Hooks

Dự kiến trong `hooks.py`:

- `scheduler_events.daily`:
  - `assetcore.services.imm07.run_nightly_aggregation`
- `doc_events`:
  - `IMM Performance Record.on_update` → audit trail (CONVENTIONS §5)
  - `IMM KPI Definition.before_save` → enforce versioning rule

Detail config *(Sprint Wave 3.1)*.

## V. Dependency với module khác

| Module nguồn | Dữ liệu tiêu thụ |
|---|---|
| IMM-08 PM | PM completion, planned downtime |
| IMM-09 Repair | Repair start/end, parts replaced |
| IMM-11 Calibration | Calibration result, certificate validity |
| IMM-12 Corrective | Incident downtime, MTTR raw |
| IMM-04 Asset | Asset master, device model class |

| Module đích | Dữ liệu phát |
|---|---|
| IMM-13 Decommission | Replacement signal |
| IMM-17 Predictive | KPI history dataset |
| Dashboard điều hành | KPI aggregated |

## VI. ErrorCode

Theo `ErrorCode` chuẩn (refer `services/shared/constants.py`). Code cụ thể cho IMM-07 *(thêm khi BE scaffold)*. Không bịa constants tại doc này.

## VII. Permission

RBAC theo CONVENTIONS §5. Role mapping dự kiến:
- `IMM-07 KPI Owner` (PTP Khối 2) — read all, write KPI definition.
- `IMM-07 Data Steward` (HC-QLCL) — read all, verify data quality flag.
- `IMM-07 Department Viewer` (Trưởng khoa) — read theo khoa.
- `IMM-07 Executive Viewer` (BGĐ) — read all (aggregated only).
- `IMM-07 Technician` (Workshop) — manual override + justification.

DocPerm matrix chi tiết *(Sprint Wave 3.1)*.
