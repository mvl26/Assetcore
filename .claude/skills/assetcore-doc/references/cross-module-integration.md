# Cross-Module Integration Patterns

Dùng phần này **trước** khi viết code chạm >1 IMM module.

## Module dependency graph

```
IMM-00 (Master / Foundation) ── shared services + lifecycle helpers
     │
     ├── IMM-01 → IMM-02 → IMM-03 → IMM-04
     │
     ├── IMM-04 → IMM-05 (Registration)
     │       ├──→ IMM-08 (PM Schedule auto-created)
     │       └──→ IMM-11 (Calibration Schedule for Class B+)
     │
     ├── IMM-08 → IMM-09 (PM finds defect → CM)
     ├── IMM-09 → IMM-15 (consumes spare parts)
     ├── IMM-11 → IMM-09 (failed cal → CM)
     ├── IMM-12 → IMM-09 (CM) + IMM-16 (CAPA)
     ├── IMM-06 → IMM-04 (Clinical Release gate)
     └── IMM-16 ─── gates ─→ IMM-08, IMM-09, IMM-04
```

Circular edges forbidden — nếu thấy trong design, dùng event hoặc shared module.

## Pattern A — Event-driven hooks (ít coupling nhất)

```python
# hooks.py
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_for_asset",
            "assetcore.services.imm11.create_calibration_schedule_if_needed",
            "assetcore.services.imm16.register_compliance_baseline",
        ]
    },
}
```

**Rules:**
- Listener phải handle `docstatus=2` (cancel/amend)
- Listener phải idempotent
- Signature bắt buộc: `def listener(doc, method=None)` — Real bug: thiếu `method=None` → TypeError
- **Same-commit wiring rule**: định nghĩa gate function → cùng commit PHẢI wire vào `hooks.py::doc_events`

## Pattern B — Direct service-to-service (lazy import)

```python
# services/imm04.py
def commission_asset(asset_name: str, operator_user: str) -> dict:
    from assetcore.services.imm06 import validate_user_authorized_for_asset  # lazy import
    if not validate_user_authorized_for_asset(operator_user, asset_name):
        raise ServiceError(ErrorCode.BUSINESS_RULE, "Chưa được đào tạo")
```

**Rules:**
- Luôn lazy-import bên trong function body
- Truyền primary key (string `name`), không truyền live `Document` objects
- Callee phải define stable contract

## Pattern C — Compliance gates (IMM-16 blocks everything)

```python
# services/imm09.py
def create_repair(asset_ref: str, **kwargs) -> dict:
    from assetcore.services.imm16 import gate_wo_submit
    gate_wo_submit(asset_ref, wo_type="CM")   # raises ServiceError if blocked
```

**Rules:**
- Gate functions never return data — chỉ raise hoặc pass
- Caller gọi gate **trước** bất kỳ DB write nào

## Pattern D — Asset status propagation

```python
from assetcore.services.imm00 import transition_asset_status
from assetcore.services.shared import AssetStatus

transition_asset_status(asset_name, AssetStatus.OUT_OF_SERVICE, root_record=repair_doc.name)
```

**KHÔNG BAO GIỜ** `frappe.db.set_value("AC Asset", name, "status", ...)` trực tiếp.

## Pattern E — Shared enums

| Enum | Path |
|---|---|
| `Roles` | `services/shared/constants.py` |
| `ErrorCode` | `services/shared/constants.py` |
| `AssetStatus` | `services/shared/constants.py` |

Module-local Status (`RepairStatus`, `PMStatus`) ở trong file service riêng. Nếu 2 module cùng cần — promote lên `services/shared/constants.py`.

## Cross-module integration bugs phổ biến

| Bug | Symptom | Fix |
|---|---|---|
| Circular import | `ImportError` khi `bench start` | Lazy-import bên trong function |
| Hook fires on cancel | Phantom records, duplicate audit rows | Check `doc.docstatus == 1` trong listener |
| Status string drift | "Active" vs "ACTIVE" fail silently | Dùng `AssetStatus.ACTIVE` constant |
| CAPA deadlock | WO cần để đóng CAPA, nhưng CAPA block WO | Thêm `wo_type="CAPA_REMEDIATION"` exception |
| Stale Document object | Changes không persist | Pass primary keys, reload với `frappe.get_doc` |
| Listener swallows error | Submit OK nhưng downstream effect miss | Không `except: pass` trong listener |

## Khi KHÔNG integrate

- **IMM-17 Reporting** đọc denormalized snapshots — không gọi live service functions từ report
- **FHIR adapter** là one-way outbound — không để FHIR import gọi thẳng IMM-09
- **Nếu cross-module call tạo cycle** → dùng event (Pattern A)

## Hooks.py audit checklist

Bất cứ khi nào chạm `hooks.py`:
- [ ] Mọi `doc_events` entry trỏ đến function thực tế trong service
- [ ] Mọi listener handle `docstatus` đúng
- [ ] Mọi `scheduler_events` function là module-scoped (không leading underscore)
- [ ] Listener documented trong `docs/imm-<YY>/04_workflow.md`
- [ ] Listener idempotent
- [ ] Fixture exports vẫn include workflow/role/custom field mới
