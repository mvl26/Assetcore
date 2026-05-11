# 04 — Thiết kế Backend (Backend Design)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Per-module |
| Owner | Tech Lead / BE Lead |
| Liên kết | 02 Analysis · 03 Diagrams · 05 API |

> Bám 3-tier strict (API → Service → Repository → DocType). Bộ doc này là hợp đồng giữa Tech Lead và BE Dev.

---

## 1. Tổng quan kiến trúc

```
[Frappe Scheduler / FE] → api/imm07.py → services/imm07.py → repositories/{kpi,replacement_signal,threshold_config}_repo.py → DocType
                                                ↓
                                       services/lifecycle.py (audit chain)
```

> Quy ước ngôn ngữ BE (bám 01 §IV.1.b):
> - Code (function/class/var/file): **tiếng Anh** (snake_case / PascalCase)
> - DocType fieldname: **tiếng Anh** (`asset`, `availability`, `mtbf_hours`)
> - DocType field label: **tiếng Việt** (`Thiết bị`, `Tỷ lệ sẵn sàng`, `MTBF (giờ)`)
> - Enum value: tiếng Anh (`Open`, `Acknowledged`); label hiển thị qua i18n
> - DTO mirror với FE TypeScript types (`frontend/src/types/imm07.ts`)

---

## 2. Domain Model — DocType

### 2.1. AC KPI Snapshot

| Trường | Type | Required | Default | Validation |
|---|---|---|---|---|
| `asset` | Link → AC Asset | ✓ | – | exists |
| `window_start` | Datetime | ✓ | – | < window_end |
| `window_end` | Datetime | ✓ | – | – |
| `granularity` | Select | ✓ | `hourly` | `hourly|daily|monthly` |
| `availability` | Float (precision 4) | – | 0 | 0 ≤ x ≤ 1 |
| `utilization` | Float (precision 4) | – | 0 | 0 ≤ x ≤ 1 |
| `mtbf_hours` | Float | – | 0 | ≥ 0 |
| `mttr_hours` | Float | – | 0 | ≥ 0 |
| `repair_count` | Int | – | 0 | ≥ 0 |
| `incident_count` | Int | – | 0 | ≥ 0 |
| `planned_downtime_hours` | Float | – | 0 | ≥ 0 |
| `unplanned_downtime_hours` | Float | – | 0 | ≥ 0 |
| `data_quality` | Select | ✓ | `Ok` | `Ok|Stale|Empty|Anomaly` |
| `prev_hash` | Data (64) | – | – | hex SHA-256 |
| `hash` | Data (64) | ✓ | – | hex SHA-256 |
| `note` | Long Text | – | – | – |

- **Naming series**: `KPI-.YYYY.-.MM.-.#####`
- **Indexes**: `(asset, window_start, granularity)` UNIQUE; `(window_start)`; `(data_quality)`
- **Permissions sơ bộ**: `IMM07 User` (read), `IMM07 Manager` (read+write), `System Manager` (full)

### 2.2. AC Replacement Signal

| Trường | Type | Required | Default | Validation |
|---|---|---|---|---|
| `asset` | Link → AC Asset | ✓ | – | exists |
| `triggering_snapshot` | Link → AC KPI Snapshot | ✓ | – | exists |
| `state` | Select | ✓ | `Open` | `Open|Acknowledged|Suppressed|Closed` |
| `reason` | Small Text | ✓ | – | not empty |
| `raised_at` | Datetime | ✓ | now | – |
| `acknowledged_at` | Datetime | – | – | – |
| `acknowledged_by` | Link → User | – | – | – |
| `closure_reference` | Dynamic Link | – | – | (IMM-13) |
| `note` | Long Text | – | – | – |

- **Naming series**: `RPLS-.YYYY.-.#####`
- **Indexes**: `(asset, state)`; `(state, raised_at)`

### 2.3. AC KPI Threshold Config

| Trường | Type | Required | Default |
|---|---|---|---|
| `asset_class` | Data | ✓ | – |
| `mtbf_hours_min` | Float | ✓ | – |
| `min_age_years` | Int | ✓ | 7 |
| `min_repair_count_12m` | Int | ✓ | 3 |
| `cooldown_days` | Int | ✓ | 30 |
| `enabled` | Check | ✓ | 1 |

- **Naming series**: `KPICFG-.#####`
- **Permissions**: chỉ `IMM07 Manager` + `System Manager` ghi.

`[BA cần bổ sung]`: ngưỡng cụ thể theo nhóm GMDN (xem `docs/gmdn/Quyết định 3107_QĐ-BYT.md`).

### 2.4. Quan hệ liên DocType

```
AC Asset (master) ─┬─< AC KPI Snapshot
                   └─< AC Replacement Signal ──> AC KPI Snapshot (triggering)
AC KPI Threshold Config (cấu hình rule) ─ áp dụng theo asset_class
AC Lifecycle Event ─ source data + emit khi signal raised
```

---

## 3. Workflow

### 3.1. AC Replacement Signal Workflow

- **File fixture**: `assetcore/workflow/imm_07_replacement_signal_workflow.json`

| State | Style | docstatus | Editable | Allow_edit role |
|---|---|---|---|---|
| Open | Warning | 0 | Yes | System Manager |
| Acknowledged | Primary | 1 | No | – |
| Suppressed | Danger | 2 | No | – |
| Closed | Success | 1 | No | – |

| From | To | Action | Allowed role | Condition |
|---|---|---|---|---|
| Open | Acknowledged | Acknowledge | IMM07 Manager | – |
| Open | Suppressed | Suppress (false-positive) | IMM07 Manager | reason required |
| Acknowledged | Closed | Close | IMM07 Manager | có closure_reference (IMM-13) hoặc lý do dismiss |

### 3.2. AC KPI Snapshot

KHÔNG có workflow JSON — record bất biến (insert-only). docstatus luôn 1 sau insert. Update chỉ qua patch + audit.

### 3.3. Controller hooks

```python
# assetcore/assetcore/doctype/ac_replacement_signal/ac_replacement_signal.py
class ACReplacementSignal(Document):
    def validate(self):
        from assetcore.services.imm07 import validate_replacement_signal
        validate_replacement_signal(self)

    def on_update_after_submit(self):
        from assetcore.services.imm07 import on_signal_state_change
        on_signal_state_change(self)
```

```python
# assetcore/assetcore/doctype/ac_kpi_snapshot/ac_kpi_snapshot.py
class ACKpiSnapshot(Document):
    def before_insert(self):
        from assetcore.services.imm07 import validate_snapshot
        validate_snapshot(self)
```

---

## 4. Service Layer — `assetcore/services/imm07.py`

### 4.1. Public functions

| Function | Input | Output | Side effect |
|---|---|---|---|
| `compute_kpi_snapshot(window: str = "1h")` | window key | `{count: int, skipped: int}` | INSERT KPI snapshot rows; emit Lifecycle Event |
| `list_kpi_snapshots(filters: dict, page: int, page_size: int)` | filters | `{items, total, page}` | – |
| `get_kpi_snapshot(name: str)` | name | DTO | – |
| `detect_replacement_signal(snapshot_name: str)` | snapshot | Signal DTO \| None | INSERT signal; notify; emit event |
| `acknowledge_signal(name: str, note: str = "")` | signal name | DTO | UPDATE state; emit event |
| `suppress_signal(name: str, reason: str)` | – | DTO | – |
| `verify_chain(asset: str)` | asset | `(valid: bool, broken_at: str \| None)` | – |
| `list_replacement_signals(filters, page, page_size)` | – | `{items, total, page}` | – |
| `get_threshold_config(asset_class: str)` | – | DTO | – |
| `update_threshold_config(payload: dict)` | – | DTO | – |

### 4.2. Validators (private)

- `_validate_window(start, end)`: end > start, end ≤ now
- `_validate_kpi_range(snapshot)`: 0 ≤ availability/utilization ≤ 1; flag DATA_ANOMALY
- `_validate_event_completeness(events)`: cảnh báo nếu module nguồn ngừng feed > 1h
- `_check_signal_cooldown(asset, days)`: BR IMM07-BR-04

### 4.3. State machine (replacement signal)

Dùng Workflow JSON (§3.1) — service chỉ delegate qua `frappe.workflow.apply_workflow`.

### 4.4. Error handling

```python
from assetcore.services.shared.constants import ErrorCode
from assetcore.services.shared.errors import ServiceError

def acknowledge_signal(name: str, note: str = "") -> dict:
    """Acknowledge a Replacement Signal (Open → Acknowledged)."""
    sig = ReplacementSignalRepo.get(name)
    if not sig:
        raise ServiceError(ErrorCode.NOT_FOUND, "Không tìm thấy tín hiệu thay thế")
    if sig.state != "Open":
        raise ServiceError(ErrorCode.BAD_STATE, "Chỉ acknowledge được khi đang Open")
    # ... apply workflow
    return {"name": sig.name, "state": "Acknowledged"}
```

ErrorCode dùng: `NOT_FOUND`, `BAD_STATE`, `VALIDATION`, `INVALID_PARAMS`, `FORBIDDEN`, `DUPLICATE`, `INTERNAL`.

---

## 4b. Repository Layer

File `assetcore/repositories/kpi_repo.py`, `replacement_signal_repo.py`, `threshold_config_repo.py`.

```python
class KpiRepo:
    @staticmethod
    def insert_snapshot(payload: dict) -> Document:
        doc = frappe.get_doc({"doctype": "AC KPI Snapshot", **payload})
        doc.insert(ignore_permissions=False)
        return doc

    @staticmethod
    def list(filters: dict, page: int = 1, page_size: int = 50) -> tuple[list, int]:
        offset = (page - 1) * page_size
        rows = frappe.get_all("AC KPI Snapshot",
            filters=filters,
            fields=["name", "asset", "window_start", "window_end",
                    "availability", "utilization", "mtbf_hours", "mttr_hours",
                    "data_quality"],
            limit_start=offset, limit_page_length=page_size,
            order_by="window_start desc")
        total = frappe.db.count("AC KPI Snapshot", filters=filters)
        return rows, total

    @staticmethod
    def list_events_for_window(asset: str, start, end) -> list:
        return frappe.get_all("AC Lifecycle Event",
            filters={"asset": asset, "timestamp": ["between", [start, end]]},
            fields=["name", "event_type", "timestamp", "root_record"],
            order_by="timestamp asc")

    @staticmethod
    def last_snapshot(asset: str, granularity: str) -> dict | None:
        rows = frappe.get_all("AC KPI Snapshot",
            filters={"asset": asset, "granularity": granularity},
            fields=["name", "window_end", "hash"],
            limit_page_length=1, order_by="window_end desc")
        return rows[0] if rows else None
```

```python
class ReplacementSignalRepo:
    @staticmethod
    def has_open_signal(asset: str, cooldown_days: int) -> bool:
        cutoff = frappe.utils.add_days(frappe.utils.now_datetime(), -cooldown_days)
        return bool(frappe.db.exists("AC Replacement Signal",
            {"asset": asset, "state": "Open", "raised_at": [">=", cutoff]}))
```

---

## 5. API Layer — `assetcore/api/imm07.py`

```python
import frappe
from assetcore.services import imm07 as service
from assetcore.api._helpers import _handle, _ok, _err, _parse_json

@frappe.whitelist()
def list_kpi_snapshots(filters: str = "{}", page: int = 1, page_size: int = 50):
    parsed = _parse_json(filters, field_name="filters", default={})
    return _handle(service.list_kpi_snapshots, parsed, int(page), int(page_size))

@frappe.whitelist()
def get_kpi_snapshot(name: str):
    return _handle(service.get_kpi_snapshot, name)

@frappe.whitelist(methods=["POST"])
def acknowledge_signal(name: str, note: str = ""):
    return _handle(service.acknowledge_signal, name, note)

@frappe.whitelist(methods=["POST"])
def suppress_signal(name: str, reason: str):
    return _handle(service.suppress_signal, name, reason)

@frappe.whitelist()
def list_replacement_signals(filters: str = "{}", page: int = 1, page_size: int = 50):
    parsed = _parse_json(filters, field_name="filters", default={})
    return _handle(service.list_replacement_signals, parsed, int(page), int(page_size))

@frappe.whitelist(methods=["POST"])
def verify_chain(asset: str):
    return _handle(service.verify_chain, asset)

@frappe.whitelist()
def get_threshold_config(asset_class: str):
    return _handle(service.get_threshold_config, asset_class)

@frappe.whitelist(methods=["POST"])
def update_threshold_config(payload: str):
    parsed = _parse_json(payload, field_name="payload", default={})
    return _handle(service.update_threshold_config, parsed)
```

> Mọi endpoint vào API Catalog file 05 §0. Envelope chuẩn `{success, data}` / `{success: false, error, code}`. HTTP status luôn 200.

---

## 6. Audit Trail

| Trigger | Entry type | Actor | Payload |
|---|---|---|---|
| Insert AC KPI Snapshot | `kpi_snapshot_created` | system | `{asset, window_start, window_end, hash}` |
| Insert AC Replacement Signal | `replacement_signal_raised` | system | `{asset, signal_name, reason}` |
| Acknowledge | `replacement_signal_acknowledged` | user | `{signal_name, by}` |
| Suppress | `replacement_signal_suppressed` | user | `{signal_name, by, reason}` |
| Close | `replacement_signal_closed` | user | `{signal_name, closure_reference}` |
| Threshold config update | `kpi_threshold_updated` | user | `{config_name, before, after}` |

**Hash chain**: SHA-256 trên canonical JSON `(prev_hash, asset, window_start, window_end, availability, utilization, mtbf_hours, mttr_hours)`. `prev_hash` lấy từ `KpiRepo.last_snapshot(asset, granularity).hash`.

**Verify endpoint**: `verify_chain(asset)` → re-compute từng snapshot tuần tự, return `(valid, broken_at)`.

---

## 7. Background jobs / Scheduler

Đăng ký `assetcore/hooks.py:scheduler_events`:

| Job | Tần suất | Hook | Mục đích |
|---|---|---|---|
| `imm07.compute_hourly` | hourly | `assetcore.services.imm07.compute_kpi_snapshot("1h")` | Snapshot hourly |
| `imm07.compute_daily` | daily (00:30) | `compute_kpi_snapshot("1d")` | Aggregate daily |
| `imm07.compute_monthly` | monthly (1st 01:00) | `compute_kpi_snapshot("1m")` | Aggregate monthly |
| `imm07.purge_retention` | daily (02:00) | `purge_snapshots_by_retention()` | Hourly > 30d → drop; daily > 1y → drop |
| `imm07.health_check_source` | every 30 min | `check_event_source_health()` | Alert CNTT khi source stale |

```python
# hooks.py snippet
scheduler_events = {
    "hourly": ["assetcore.services.imm07.compute_kpi_snapshot"],
    "daily": [
        "assetcore.services.imm07.compute_kpi_snapshot_daily",
        "assetcore.services.imm07.purge_snapshots_by_retention",
    ],
    "cron": {
        "0 1 1 * *": ["assetcore.services.imm07.compute_kpi_snapshot_monthly"],
        "*/30 * * * *": ["assetcore.services.imm07.check_event_source_health"],
    },
}
```

---

## 8. Integration

### 8.1. Module nội bộ

| Hướng | Module | Cơ chế |
|---|---|---|
| Input | IMM-04, IMM-08, IMM-09, IMM-11, IMM-12 | Đọc `AC Lifecycle Event` (read-only) |
| Output | IMM-13 | Replacement signal feed; IMM-13 link `closure_reference` |
| Output | IMM-16 | KPI feed cho compliance scorecard (read-only API) |
| Output | IMM-17 | Snapshot time-series feed cho ML (export job) |

### 8.2. Bên ngoài

- **Email/SMS notification** qua Frappe Notification framework — gửi Trưởng phòng khi signal raised
- **BI/IMMIS dashboard** — `KPI-DASH-IMMIS-07`: export read-only API cho BI tool
- KHÔNG tích hợp HIS/FHIR (không liên quan clinical)

---

## 9. Migration & Patch

- Patch path:
  - `assetcore/patches/v1/00x_create_imm07_doctypes.py` — tạo 3 DocType
  - `assetcore/patches/v1/00x_seed_threshold_config.py` — seed config mặc định theo nhóm GMDN
- Đăng ký `patches.txt`
- Fixtures cần export khi schema ổn định:
  - `AC KPI Threshold Config` (default seed) — fixture `kpi_threshold_config.json`
  - Workflow `imm_07_replacement_signal_workflow.json`
  - Custom roles `IMM07 User`, `IMM07 Manager`

---

## 10. Non-functional

- **Concurrency**: scheduler hourly — đảm bảo không 2 job cùng lúc bằng `frappe.cache().lock("imm07.compute", timeout=300)`. Snapshot có UNIQUE `(asset, window_start, granularity)` → DB tự reject duplicate.
- **Caching**: cache `get_threshold_config(asset_class)` TTL 10 phút (key: `imm07:threshold:<class>`); invalidate khi update config.
- **Logging**: `frappe.logger("imm07")` — INFO cho compute summary, WARNING cho stale source, ERROR cho compute fail.
- **Idempotency**: compute job idempotent theo (asset, window_start) — chạy lại không tạo duplicate.

---

## DoD — File 04

- [x] Quy ước ngôn ngữ BE
- [x] DocType field + naming + permissions sơ bộ (3 DocType)
- [x] Quan hệ liên DocType
- [x] Workflow JSON cho Replacement Signal
- [x] Service function-based + type hints
- [x] Repository layer (3 repo)
- [x] Mọi error qua ServiceError
- [x] API layer dùng `_handle/_ok/_err`
- [x] Audit trail trigger đầy đủ (6 trigger)
- [x] Index DB cho query nóng
- [x] Background job đăng ký rõ (5 job)
- [x] Integration nội + ngoại
- [x] Patch path xác định
- [ ] Reviewed bởi BE Lead + DBA + (FE Lead khi mirror DTO sang `frontend/src/types/imm07.ts`)
