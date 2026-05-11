# 04 — Thiết kế Backend (Backend Design)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | DocType + Workflow + Service 3-tier + Hooks + Scheduler |
| Owner | Tech Lead BE |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) |

> Backend IMM-07 tuân thủ kiến trúc 3-tier strict (`API → Service → Repository`) theo `.claude/skills/CONVENTIONS.md` §2. Toàn bộ business logic nằm trong Service layer; DocType controller chỉ giữ validation cấp record.

---

## 1. Tổng quan kiến trúc

3-tier:

- **API layer** (`assetcore/api/imm07.py`): nhận request `@frappe.whitelist()`, parse + delegate Service. Không chứa logic.
- **Service layer** (`assetcore/services/imm07.py`): business rules, compute KPI, transition signal, audit chain.
- **Repository layer** (`assetcore/repositories/performance_repo.py`, `replacement_repo.py`): query DB qua Frappe ORM. Không chứa logic.

Tham chiếu pattern: `.claude/skills/assetcore-be-module/SKILL.md` + `CONVENTIONS.md` §2.

## 2. Domain Model — DocType

| DocType | Type | Naming | Mô tả |
|---|---|---|---|
| `IMM Performance Metric` | Document | `IMM-07-PM-.YYYY.-.MM.-.####` | Snapshot KPI per asset/period |
| `IMM Performance Metric Definition` | Document | `IMM-07-DEF-.YYYY.-.####` | Catalog công thức KPI |
| `IMM Replacement Signal` | Document | `IMM-07-SIG-.YYYY.-.####` | Cảnh báo replacement |
| `IMM Replacement Threshold` | Document | `IMM-07-TH-.YYYY.-.####` | Ngưỡng config (workflow) |

Field-by-field — xem [03 §I.4 Data dictionary](./03_Diagrams.md#i4-data-dictionary-schema-csdl-chi-tiết).

DocType controller (Python) — chỉ validate cấp record:

```python
# assetcore/assetcore/doctype/imm_performance_metric/imm_performance_metric.py
class IMMPerformanceMetric(Document):
    def validate(self):
        # Ngăn chỉnh sửa snapshot đã có hash
        if self.current_hash and self.has_value_changed("value"):
            frappe.throw(_("Snapshot hashed — không thể sửa value."))
```

*(Skeleton — chi tiết `*(Sprint Wave 3)*`.)*

## 3. Workflow

Áp dụng cho 2 DocType: `IMM Replacement Signal` (lifecycle), `IMM Replacement Threshold` (governance).

**Workflow `IMM Replacement Signal`:**

| State | docstatus | Allow edit roles |
|---|---|---|
| Draft | 0 | System |
| Open | 0 | System |
| InReview | 0 | Trưởng phòng |
| ActionPlanned | 0 | Trưởng phòng |
| FalsePositive | 1 | Trưởng phòng |
| Closed | 1 | Trưởng phòng |

| Transition | From → To | Role |
|---|---|---|
| Auto-promote | Draft → Open | System |
| Take | Open → InReview | Trưởng phòng |
| Plan | InReview → ActionPlanned | Trưởng phòng |
| Mark FP | InReview → FalsePositive | Trưởng phòng |
| Close | ActionPlanned → Closed | Trưởng phòng |

**Workflow `IMM Replacement Threshold`** — maker/checker (1 maker `Workshop Lead` + 1 checker `Trưởng phòng`).

Tham chiếu: `.claude/skills/assetcore-workflow-builder/SKILL.md`.

## 4. Service Layer

Pattern (theo `CONVENTIONS.md` §2):

```python
# assetcore/services/imm07.py
"""IMM-07 Performance — service layer."""

from assetcore.repositories.performance_repo import PerformanceRepo
from assetcore.repositories.lifecycle_event_repo import LifecycleEventRepo
from assetcore.services.shared import audit


class PerformanceService:
    def __init__(self, repo: PerformanceRepo, le_repo: LifecycleEventRepo):
        self.repo = repo
        self.le_repo = le_repo

    def compute_metrics(self, date: str) -> dict:
        """Tính snapshot KPI cho mọi asset active."""
        # Implementation — Sprint Wave 3
        ...
```

Service functions chính:

| Function | Mô tả | Caller |
|---|---|---|
| `compute_metrics(date)` | Cron compute toàn bộ asset | Scheduler |
| `recompute_one(asset, date)` | Re-compute 1 asset | API + Admin |
| `drill_down(asset, period, kpi)` | Trả record nguồn | API |
| `transition_signal(name, action, user)` | Lifecycle signal | API |
| `verify_chain(period_start, period_end)` | Audit hash chain | API + Cron weekly |

## 4b. Repository Layer (data access)

```python
# assetcore/repositories/performance_repo.py
class PerformanceRepo:
    def get_active_assets(self) -> list[dict]:
        return frappe.get_all("AC Asset", filters={"status": "Active"}, fields=["name", "department", "asset_class"])

    def save_snapshot(self, payload: dict) -> str: ...
    def get_snapshot(self, asset: str, period_start: str, period_type: str): ...
```

Repository **không** chứa business logic — chỉ query/insert/update.

## 5. API Layer (mức module)

```python
# assetcore/api/imm07.py
import frappe
from assetcore.services.imm07 import PerformanceService

@frappe.whitelist()
def drill_down(asset: str, period_start: str, kpi_code: str):
    svc = PerformanceService(...)
    data = svc.drill_down(asset, period_start, kpi_code)
    return {"success": True, "data": data}
```

Đầy đủ endpoint — xem [05 API Specification](./05_API_Specification.md).

## 6. Audit Trail

- Mỗi snapshot có `current_hash = SHA256(prev_hash || canonical_json(payload))`.
- Mỗi transition signal sinh `IMM Audit Trail` entry.
- Verify chain qua service `verify_chain` — re-compute và so sánh.

## 7. Background jobs / Scheduler

`hooks.py`:

```python
scheduler_events = {
    "cron": {
        "0 2 * * *": ["assetcore.services.imm07.compute_metrics_daily"],
        "0 3 * * 1": ["assetcore.services.imm07.compute_metrics_weekly"],
        "0 4 1 * *": ["assetcore.services.imm07.compute_metrics_monthly"],
        "0 5 * * 0": ["assetcore.services.imm07.verify_chain_weekly"],
    }
}
```

Idempotent: nếu snapshot đã tồn tại cho `(asset, period_start, period_type)` thì skip (hoặc supersede tùy flag).

## 8. Integration

- Read-only từ: `AC Asset` (IMM-04), `AC PM Work Order` (IMM-08), `Asset Repair` (IMM-09), `IMM Asset Calibration` (IMM-11), `Spare Issue` (IMM-15).
- Publish: lifecycle event `performance_snapshot_created`, `replacement_signal_raised`.
- Subscribe: không (IMM-07 là consumer).

## 9. Migration & Patch

Patch khởi tạo: seed `IMM Performance Metric Definition` cho 6 KPI mặc định (availability, utilization, MTBF, MTTR, downtime, % replacement signal).

```python
# assetcore/patches/v3_x/seed_imm07_kpi_definitions.py
def execute():
    # Insert 6 default KPI definitions
    ...
```

*(Patch detail — `*(Sprint Wave 3)*`.)*

## 10. Non-functional

- Cron compute_metrics_daily ≤ 30 phút cho 10k asset.
- API drill_down p95 ≤ 300ms.
- Coverage service ≥ 85% (CONVENTIONS §6).
- Hash chain verify cron weekly + on-demand.
