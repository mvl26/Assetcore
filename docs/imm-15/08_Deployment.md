# IMM-15 — Deployment

> ✅ Wave 2 IMPLEMENTED. Code đã trên `feature/hieuc/wave-2` (commit `4b4b0db`). Deploy gắn với release tag `v1.0.0-rc.2`.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 1.0.0-rc.2 |
| Template | 08 Deployment |
| Ngày cập nhật | 2026-05-14 |
| Trạng thái | IMPLEMENTED — Wave 2 |
| Phụ thuộc bắt buộc | AC Inventory Backbone Wave 1 LIVE |

---

## §0 — Wired Artefacts (CURRENT, 2026-05-14)

### Hooks (verified `assetcore/hooks.py` — 2026-05-18)

`doc_events`:
- `PM Work Order` → `before_submit`: `assetcore.services.imm15.reserve_for_pm`
- `Asset Repair` → `before_submit`: `assetcore.services.imm15.reserve_for_repair`
- `AC Asset` → `on_update`: `assetcore.services.imm15.flag_obsolete_on_decommission`

> Lưu ý: DocType key thực tế là `"PM Work Order"` và `"Asset Repair"` — không phải `"IMM PM Work Order"` / `"IMM Repair Work Order"` / `"IMM CM Work Order"` như các draft trước ghi.

`scheduler_events`:
- daily: `check_low_stock_and_alert`, `check_critical_spare_breach`, `check_expiring_batches`, `compute_inventory_kpis`
- monthly: `generate_spare_demand_forecast`
- cron `0 3 1 1,4,7,10 *` (quarterly): `reclassify_abc`

### Fixtures (verified `assetcore/fixtures/`)

- `imm15_custom_fields.json` — Custom Field bundle (7 CFs trên AC Spare Part)
- `workflow.json`, `workflow_state.json`, `workflow_action_master.json` — chứa state machine Spare Allocation, Stock Cycle Count, Spare Part Forecast
- `role.json`, `role_profile.json` — IMM Storekeeper / Workshop Lead / QA Officer

### DocType folders (verified `assetcore/assetcore/doctype/`)

`imm_spare_allocation`, `imm_spare_allocation_item`, `imm_stock_cycle_count`, `imm_stock_cycle_count_item`, `imm_cycle_count_item`, `imm_spare_part_forecast`, `imm_spare_forecast_item`, `imm_critical_spare_watchlist`, `imm_spare_batch`, `imm_spare_alternative`, `imm_device_spare_part`, `ac_spare_part`, `ac_spare_part_stock`, `ac_stock_movement(_item)`, `ac_warehouse`, `ac_uom(_conversion)`.

### Patches

`assetcore/patches.txt` hiện không chứa entry IMM-15 riêng — schema được load qua fixture + DocType JSON. Nếu cần data migration sau này thì viết patch `assetcore.patches.v3_2.NNN_*` và bổ sung vào `patches.txt`.

> ⚠️ Các section §I–§VI dưới đây là deployment plan template — giữ làm checklist. Đối chiếu với §0 nếu có khác biệt, §0 là source-of-truth.

---

## §I — Pre-Deploy Checklist

### I.1 Prerequisites (MANDATORY)

> IMM-15 **không thể deploy** nếu AC Backbone Wave 1 chưa LIVE.

| # | Điều kiện | Verify |
|---|---|---|
| PRE-01 | AC Spare Part, AC Spare Part Stock, AC Stock Movement (+Item), AC Warehouse, AC UOM đã LIVE | `bench --site [site] console` → `frappe.db.table_exists("tabAC Spare Part")` |
| PRE-02 | `assetcore/api/inventory.py` (~30 endpoints) hoạt động | Smoke test GET `list_spare_parts` |
| PRE-03 | `assetcore/services/inventory.py` (bao gồm `check_low_stock`, `get_available_qty`) LIVE | Unit test pass |
| PRE-04 | Frontend `views/inventory/` (11 màn) đã build và accessible | Browse `/imm15/spares` → redirect đến live view |
| PRE-05 | Frappe v15.x, Python ≥ 3.11, MariaDB 10.11+, Node 18 LTS | `bench --version` |
| PRE-06 | IMM-08 PM, IMM-09 Repair, IMM-12 CM đã ổn định (hooks cần) | Verify workflows active |
| PRE-07 | Redis đang chạy (realtime + cache) | `redis-cli ping` |
| PRE-08 | Celery workers đang chạy (scheduler jobs) | `bench doctor` |
| PRE-09 | QC Hold warehouse đã tạo trong AC Warehouse | `frappe.db.exists("AC Warehouse", "QC-Hold")` |
| PRE-10 | Backup PROD DB đã xác nhận | `bench --site [site] backup --with-files` |
| PRE-11 | Staging deploy đã pass (tất cả unit + UAT-P0) | CI/CD badge xanh |
| PRE-12 | QMS sign-off (BA Lead + Dev Lead + QA Lead) | `07_Testing_QA.md §III.5` ký đủ |

---

## §II — Environment Configuration

### II.1 DEV

```json
{
  "site_config": {
    "imm15_enable_batch_tracking": false,
    "imm15_emergency_override_roles": ["IMM Workshop Lead", "IMM Operations Manager"],
    "imm15_breach_email_recipients": ["workshop-head@test.local"],
    "imm15_low_stock_email_recipients": ["storekeeper@test.local"],
    "imm15_qc_hold_warehouse": "QC-Hold-DEV",
    "imm15_abc_a_threshold_pct": 80,
    "imm15_abc_b_threshold_pct": 95,
    "imm15_forecast_methods_enabled": ["Moving_Avg", "PM_Driven"],
    "imm15_kpi_snapshot_enabled": true,
    "imm15_debug_mode": true
  }
}
```

### II.2 STAGING

```json
{
  "site_config": {
    "imm15_enable_batch_tracking": false,
    "imm15_emergency_override_roles": ["IMM Workshop Lead", "IMM Operations Manager"],
    "imm15_breach_email_recipients": ["qa-team@staging.local", "workshop-head@staging.local"],
    "imm15_low_stock_email_recipients": ["storekeeper@staging.local"],
    "imm15_qc_hold_warehouse": "QC-Hold",
    "imm15_abc_a_threshold_pct": 80,
    "imm15_abc_b_threshold_pct": 95,
    "imm15_forecast_methods_enabled": ["Moving_Avg", "PM_Driven"],
    "imm15_kpi_snapshot_enabled": true,
    "imm15_debug_mode": false
  }
}
```

### II.3 PRODUCTION

```json
{
  "site_config": {
    "imm15_enable_batch_tracking": false,
    "imm15_emergency_override_roles": ["IMM Workshop Lead", "IMM Operations Manager"],
    "imm15_breach_email_recipients": [
      "workshop-head@hospital.vn",
      "vp-block1@hospital.vn",
      "cmms-admin@hospital.vn"
    ],
    "imm15_low_stock_email_recipients": [
      "storekeeper@hospital.vn",
      "workshop-head@hospital.vn"
    ],
    "imm15_qc_hold_warehouse": "AC-WH-QC-HOLD",
    "imm15_abc_a_threshold_pct": 80,
    "imm15_abc_b_threshold_pct": 95,
    "imm15_forecast_methods_enabled": ["Moving_Avg", "PM_Driven"],
    "imm15_kpi_snapshot_enabled": true,
    "imm15_debug_mode": false,
    "imm15_audit_trail_retention_years": 10
  }
}
```

---

## §III — Migration Patches

### III.1 Patch Order (patches.txt)

```
# IMM-15 Wave 2
assetcore.patches.v3_201.add_imm15_custom_fields_to_ac_spare_part
assetcore.patches.v3_202.create_imm_spare_allocation_doctype
assetcore.patches.v3_203.create_imm_stock_cycle_count_doctype
assetcore.patches.v3_204.create_imm_spare_part_forecast_doctype
assetcore.patches.v3_205.create_imm_critical_spare_watchlist_doctype
assetcore.patches.v3_206.create_imm_spare_alternative_doctype
assetcore.patches.v3_207.register_imm15_workflows
assetcore.patches.v3_208.extend_ac_stock_movement_reference_type
assetcore.patches.v3_209.backfill_part_class_from_is_critical
assetcore.patches.v3_210.register_imm15_scheduler_jobs
```

### III.2 Patch Details

#### v3_201: Custom Fields on AC Spare Part

```python
# assetcore/patches/v3_201/add_imm15_custom_fields_to_ac_spare_part.py
"""
Add 7 IMM-15 custom fields to AC Spare Part.
Risk: Low — additive only, no existing data modification.
Rollback: Remove custom fields via Customize Form or reverse fixture.
"""
import frappe

def execute():
    fixture_path = frappe.get_app_path("assetcore", "fixtures", "imm15_custom_fields.json")
    with open(fixture_path) as f:
        import json
        fields = json.load(f)
    for field_def in fields:
        if not frappe.db.exists("Custom Field", field_def.get("name")):
            frappe.get_doc(field_def).insert(ignore_permissions=True)
    frappe.db.commit()
```

**Risk**: Low — additive.  
**Rollback**: `frappe.delete_doc("Custom Field", "AC Spare Part-imm_part_class")` (repeat for each field).

---

#### v3_202: IMM Spare Allocation DocType

```python
# assetcore/patches/v3_202/create_imm_spare_allocation_doctype.py
"""
Create IMM Spare Allocation and IMM Spare Allocation Item DocTypes.
Risk: Low — new tables, no existing data touched.
Rollback: frappe.delete_doc("DocType", "IMM Spare Allocation") — drops table.
"""
import frappe

def execute():
    frappe.reload_doctype("IMM Spare Allocation")
    frappe.reload_doctype("IMM Spare Allocation Item")
```

**Risk**: Low — new DocType.  
**Rollback**: Remove DocType JSON + `frappe.delete_doc("DocType", ...)`.

---

#### v3_203: IMM Stock Cycle Count DocType

```python
# assetcore/patches/v3_203/create_imm_stock_cycle_count_doctype.py
"""
Create IMM Stock Cycle Count and IMM Cycle Count Item DocTypes.
Risk: Low — new tables.
"""
import frappe

def execute():
    frappe.reload_doctype("IMM Stock Cycle Count")
    frappe.reload_doctype("IMM Cycle Count Item")
```

---

#### v3_204: IMM Spare Part Forecast DocType

```python
# assetcore/patches/v3_204/create_imm_spare_part_forecast_doctype.py
"""
Create IMM Spare Part Forecast and IMM Spare Forecast Item.
Note: distinct from IMM Demand Forecast (IMM-01, category-level).
"""
import frappe

def execute():
    frappe.reload_doctype("IMM Spare Part Forecast")
    frappe.reload_doctype("IMM Spare Forecast Item")
```

---

#### v3_205: IMM Critical Spare Watchlist DocType

```python
# assetcore/patches/v3_205/create_imm_critical_spare_watchlist_doctype.py
import frappe

def execute():
    frappe.reload_doctype("IMM Critical Spare Watchlist")
```

---

#### v3_206: IMM Spare Alternative Child DocType

```python
# assetcore/patches/v3_206/create_imm_spare_alternative_doctype.py
import frappe

def execute():
    frappe.reload_doctype("IMM Spare Alternative")
```

---

#### v3_207: Register Workflows

```python
# assetcore/patches/v3_207/register_imm15_workflows.py
"""
Load IMM-15 Allocation and Cycle Count workflow JSONs.
Risk: Medium — affects doc routing if workflow states conflict.
Rollback: Delete workflow docs + set workflow_state field to null.
"""
import frappe
import json, os

def execute():
    for wf_file in [
        "imm_15_allocation_workflow.json",
        "imm_15_cycle_count_workflow.json",
    ]:
        path = frappe.get_app_path("assetcore", "workflow", wf_file)
        with open(path) as f:
            wf_doc = json.load(f)
        if frappe.db.exists("Workflow", wf_doc.get("name")):
            frappe.get_doc("Workflow", wf_doc.get("name")).update(wf_doc).save()
        else:
            frappe.get_doc(wf_doc).insert(ignore_permissions=True)
    frappe.db.commit()
```

**Risk**: Medium.  
**Rollback**: Set workflow `is_active = 0`.

---

#### v3_208: Extend AC Stock Movement Reference Type

```python
# assetcore/patches/v3_208/extend_ac_stock_movement_reference_type.py
"""
Add "IMM Spare Allocation" and "IMM Stock Cycle Count" to
AC Stock Movement.reference_type Select options via Property Setter.
Risk: Low — additive option; no data schema change.
"""
import frappe

def execute():
    ps_name = "AC Stock Movement-reference_type-options"
    existing = frappe.db.get_value("Property Setter", ps_name, "value") or ""
    additions = ["IMM Spare Allocation", "IMM Stock Cycle Count"]
    existing_list = [x.strip() for x in existing.splitlines() if x.strip()]
    for add in additions:
        if add not in existing_list:
            existing_list.append(add)
    new_value = "\n".join(existing_list)
    if frappe.db.exists("Property Setter", ps_name):
        frappe.db.set_value("Property Setter", ps_name, "value", new_value)
    else:
        frappe.get_doc({
            "doctype": "Property Setter",
            "name": ps_name,
            "doc_type": "AC Stock Movement",
            "field_name": "reference_type",
            "property": "options",
            "value": new_value,
            "property_type": "Text",
        }).insert(ignore_permissions=True)
    frappe.db.commit()
```

**Risk**: Low — additive option.  
**Rollback**: Remove added options from Property Setter.

---

#### Schema note — Register IMM-15 event_type slug (vòng 12, CR-WF-15-AUDIT · ADR-IMM-15-09)

Thêm 6 slug domain (`cycle_count_posted`, `allocation_created/approved/issued/returned/cancelled`) vào field `event_type` của `imm_audit_trail.json`. `IMM Audit Trail` là DocType **AssetCore sở hữu** ⇒ sửa TRỰC TIẾP `options` trong JSON, **KHÔNG** cần Property Setter/patch (Property Setter chỉ dùng cho field của DocType không-sở-hữu như `AC Stock Movement`).

**Deploy step (MANDATORY):** sau khi sửa JSON → `bench --site <site> migrate` (hoặc `bench --site <site> reload-doc assetcore doctype imm_audit_trail`) để sync JSON→DB. ⚠️ **TRƯỚC khi migrate, Select validation vẫn dùng options CŨ** ⇒ INVARIANT test `TestImm15AuditEventTypeParity` RED + emit slug bị nuốt. Chạy migrate rồi mới GREEN. Không cần data-migration (chỉ mở rộng enum, additive — dòng audit cũ không bị ảnh hưởng).
**Risk**: Low — additive enum. **Rollback**: gỡ 6 slug khỏi JSON options + migrate (dòng audit đã ghi vẫn giữ giá trị — không cascade).

---

#### v3_209: Backfill Part Class from is_critical

```python
# assetcore/patches/v3_209/backfill_part_class_from_is_critical.py
"""
Backfill imm_part_class for existing AC Spare Part records:
  is_critical = 1  → imm_part_class = "Critical"
  is_critical = 0  → imm_part_class = "Consumable" (default; manual review advised)
Risk: Medium — updates existing records. Verify after deploy.
Rollback: SET imm_part_class = NULL WHERE imm_part_class IS NOT NULL (if patch 201 ran first)
"""
import frappe

def execute():
    # Critical parts
    frappe.db.sql("""
        UPDATE `tabAC Spare Part`
        SET `imm_part_class` = 'Critical'
        WHERE `is_critical` = 1
          AND (`imm_part_class` IS NULL OR `imm_part_class` = '')
    """)
    # Non-critical → Consumable (default; ops team to manually reclassify Major/Tool)
    frappe.db.sql("""
        UPDATE `tabAC Spare Part`
        SET `imm_part_class` = 'Consumable'
        WHERE `is_critical` = 0
          AND (`imm_part_class` IS NULL OR `imm_part_class` = '')
    """)
    frappe.db.commit()
```

**Risk**: Medium — updates existing records.  
**Rollback**: `UPDATE tabAC Spare Part SET imm_part_class = NULL`.  
**Post-deploy action**: Workshop Head reviews "Consumable" backfilled records; manually reclassify to "Major" or "Tool" as needed.

---

#### v3_210: Register Scheduler Jobs

```python
# assetcore/patches/v3_210/register_imm15_scheduler_jobs.py
"""
Ensure IMM-15 scheduler entries are registered in hooks.py.
Actual hook registration is via hooks.py — this patch verifies tasks module.
"""
import frappe

def execute():
    from assetcore import tasks as t
    assert hasattr(t, "check_low_stock_alerts"), "check_low_stock_alerts missing"
    assert hasattr(t, "check_critical_spare_breach"), "check_critical_spare_breach missing"
    assert hasattr(t, "compute_inventory_kpis"), "compute_inventory_kpis missing"
    assert hasattr(t, "generate_spare_demand_forecast"), "generate_spare_demand_forecast missing"
    frappe.logger("imm15").info("IMM-15 scheduler tasks verified")
```

---

## §IV — Deploy Sequence

```bash
# 1. Backup
bench --site [site] backup --with-files
echo "Backup completed: $(date)"

# 2. Pull latest code
git -C /home/frappe/frappe-bench/apps/assetcore pull origin master

# 3. Install/update dependencies
bench setup requirements --apps assetcore

# 4. Build frontend assets
bench build --app assetcore

# 5. Run migrations (patches v3_201..v3_210)
bench --site [site] migrate

# 6. Clear cache
bench --site [site] clear-cache
bench --site [site] clear-website-cache

# 7. Reload affected DocTypes
bench --site [site] reload-doctype "AC Spare Part"
bench --site [site] reload-doctype "IMM Spare Allocation"
bench --site [site] reload-doctype "IMM Stock Cycle Count"
bench --site [site] reload-doctype "IMM Spare Part Forecast"
bench --site [site] reload-doctype "IMM Critical Spare Watchlist"

# 8. Restart services
bench restart
sudo supervisorctl restart all

# 9. Run smoke tests (see §V)
python /home/frappe/frappe-bench/apps/assetcore/scripts/smoke_test_imm15.py

# 10. Verify scheduler registration
bench --site [site] execute assetcore.tasks.compute_inventory_kpis
```

---

## §V — Smoke Tests

```python
# scripts/smoke_test_imm15.py
"""IMM-15 post-deploy smoke tests. Run after bench migrate + restart."""
import frappe
import sys

frappe.init(site="[site]")
frappe.connect()

PASS = []
FAIL = []

def check(label, condition, detail=""):
    if condition:
        PASS.append(label)
        print(f"  PASS  {label}")
    else:
        FAIL.append(label)
        print(f"  FAIL  {label} — {detail}")

# 1. AC Backbone tables present
check(
    "AC Spare Part table exists",
    frappe.db.table_exists("tabAC Spare Part"),
)
check(
    "AC Spare Part Stock table exists",
    frappe.db.table_exists("tabAC Spare Part Stock"),
)
check(
    "AC Stock Movement table exists",
    frappe.db.table_exists("tabAC Stock Movement"),
)

# 2. IMM-15 new tables present
for dt in [
    "IMM Spare Allocation",
    "IMM Spare Allocation Item",
    "IMM Stock Cycle Count",
    "IMM Cycle Count Item",
    "IMM Spare Part Forecast",
    "IMM Critical Spare Watchlist",
]:
    check(f"{dt} table exists", frappe.db.table_exists(f"tab{dt}"))

# 3. Custom fields present on AC Spare Part
for field in ["imm_part_class", "imm_abc_class", "imm_lead_time_days", "imm_traceability_required"]:
    check(
        f"AC Spare Part.{field} exists",
        frappe.db.has_column("tabAC Spare Part", field),
    )

# 4. Workflows active
for wf in ["IMM-15 Allocation Workflow", "IMM-15 Cycle Count Workflow"]:
    check(
        f"Workflow '{wf}' active",
        frappe.db.get_value("Workflow", wf, "is_active") == 1,
        "Workflow not found or inactive",
    )

# 5. API importable
try:
    from assetcore.api import imm15 as _imm15_api
    check("assetcore.api.imm15 importable", True)
except ImportError as e:
    check("assetcore.api.imm15 importable", False, str(e))

# 6. Service importable
try:
    from assetcore.services import imm15 as _imm15_svc
    check("assetcore.services.imm15 importable", True)
except ImportError as e:
    check("assetcore.services.imm15 importable", False, str(e))

# 7. Scheduler tasks present
try:
    from assetcore import tasks as _tasks
    check("tasks.check_critical_spare_breach", hasattr(_tasks, "check_critical_spare_breach"))
    check("tasks.compute_inventory_kpis", hasattr(_tasks, "compute_inventory_kpis"))
except ImportError as e:
    check("assetcore.tasks importable", False, str(e))

# 8. Property Setter for AC Stock Movement reference_type
ps_value = frappe.db.get_value(
    "Property Setter", "AC Stock Movement-reference_type-options", "value"
) or ""
check(
    "AC Stock Movement.reference_type includes IMM Spare Allocation",
    "IMM Spare Allocation" in ps_value,
    "Property Setter not applied",
)

# Summary
print(f"\nSmoke test: {len(PASS)} PASS / {len(FAIL)} FAIL")
if FAIL:
    print(f"Failed: {FAIL}")
    sys.exit(1)
sys.exit(0)
```

---

## §VI — Rollback Plan

### VI.1 Rollback Triggers

| Condition | Action |
|---|---|
| Smoke test FAIL (any item) | Immediate rollback |
| Patch v3_209 causes data corruption | Selective rollback + data restore |
| Workflow conflict with IMM-08/09/12 | Deactivate IMM-15 workflows, hotfix |
| API 500 errors > 1% in first 30 min | Full rollback |

### VI.2 Rollback Steps

```bash
# 1. Restore DB backup
bench --site [site] restore /path/to/backup.sql.gz

# 2. Revert code
git -C /home/frappe/frappe-bench/apps/assetcore checkout <prev-commit>

# 3. Rebuild
bench build --app assetcore
bench --site [site] migrate
bench restart

# 4. Verify LIVE AC Backbone still working
curl -s "https://[site]/api/method/assetcore.api.inventory.list_spare_parts" \
  -H "Authorization: token [token]" | python3 -c "import json,sys; d=json.load(sys.stdin); print('OK' if d.get('message',{}).get('success') else 'FAIL')"
```

---

## §VII — QMS Mapping

### VII.1 Compliance Requirements

| Yêu cầu | Nguồn | IMM-15 Implementation |
|---|---|---|
| Identification & Traceability | ISO 13485 §7.5.8 | `imm_traceability_required` + batch_no/serial_no enforce; Allocation links WO + AC Stock Movement |
| Infrastructure (storage) | ISO 13485 §6.3 | `imm_storage_condition` field; alert khi kho không phù hợp |
| Parts & Supplies Management | WHO HTM 4.5 | Critical Spare Watchlist + min stock + lead-time + breach detection |
| CAPA Trigger | ISO 13485 §8.5 | BR-15-04 (critical breach), BR-15-05 (variance > 5%) → auto-seed CAPA |
| Audit Trail | ISO 13485 §4.2.5, NĐ98 | IMM Audit Trail immutable + Frappe Version + AC Stock Movement submitted |
| Regulatory Compliance | NĐ 98/2021 | Spare gắn với device có ĐK lưu hành; kế thừa qua IMM Device Spare Part |
| Document Control | ISO 13485 §4.2.3 | PR/WI/BM/HS documents (§VII.2) |
| Change Control | ISO 13485 §7.3.9 | Patch-based deploy; workflow fixture version-controlled in git |
| Corrective Action Tracking | ISO 13485 §8.5.2 | CAPA seeded by service → tracked in IMM-16 |
| Statistical Techniques | ISO 13485 §8.1 | ABC classification, MAPE forecast metric |

### VII.2 QMS Documents to Update

| Loại | Mã | Tên | Deadline |
|---|---|---|---|
| Procedure | PR-IMMIS-15-01 | Quy trình quản lý phụ tùng chiến lược | T-14 |
| Procedure | PR-IMMIS-15-02 | Quy trình cấp phát phụ tùng theo Work Order | T-7 |
| Procedure | PR-IMMIS-15-03 | Quy trình kiểm kê chu kỳ | T-7 |
| Procedure | PR-IMMIS-15-04 | Quy trình dự báo nhu cầu & tái đặt hàng | T-7 |
| Work Instruction | WI-IMMIS-15-01 | HDCV tạo phiếu cấp phát | T-7 |
| Work Instruction | WI-IMMIS-15-02 | HDCV cấp phát khẩn (Emergency Override) | T-7 |
| Work Instruction | WI-IMMIS-15-03 | HDCV kiểm kê chu kỳ (tablet workflow) | T-7 |
| Work Instruction | WI-IMMIS-15-04 | HDCV trả phụ tùng (QC gate) | T-7 |
| Work Instruction | WI-IMMIS-15-05 | HDCV ABC review hàng quý | T-7 |
| Form | BM-IMMIS-15-01 | Biểu mẫu phiếu kiểm kê chu kỳ | T-14 |
| Record | HS-LOG-IMMIS-15 | Hồ sơ log allocation + override | Ongoing |
| Record | HS-REC-IMMIS-15 | Hồ sơ kiểm kê chu kỳ | Ongoing |
| KPI | KPI-DASH-IMMIS-15 | Dashboard KPI tồn kho (8 KPIs) | T+7 |

---

## §VIII — KPIs

| KPI | Công thức | Target | Frequency | Dashboard field |
|---|---|---|---|---|
| Stock Turnover (year) | `consumed_value_year / avg_inventory_value` | ≥ 4 | Monthly | `stock_turnover_year` |
| Days-on-Hand (avg) | `avg_qty_on_hand / daily_consumption × 365` | 30-60d (Critical: 60-90d) | Weekly | `days_on_hand_avg` |
| Stock-out Incidents / month | Số WO bị block do thiếu spare | ≤ 2 | Monthly | `stockout_incidents_30d` |
| Critical Breach Hours / month | Tổng giờ Watchlist breach | 0 | Daily | `critical_breach_hours_30d` |
| Cycle Count Accuracy % | `1 - Σ|variance_qty| / Σsystem_qty` | ≥ 98% | Per count | `cycle_accuracy_pct` |
| Forecast MAPE | `mean(|actual-forecast|/actual) × 100` | ≤ 25% | Quarterly | `forecast_mape_q` |
| Emergency Override / month | Số lần bypass BR-15-03 | ≤ 3 | Monthly | `emergency_override_count_30d` |
| Spare Cost per Asset (VND) | `consumed_value_asset / asset_count` | Trend | Monthly | `spare_cost_per_asset` |

---

## §IX — Risk Register

| # | Risk | Likelihood | Impact | Owner | Mitigation |
|---|---|---|---|---|---|
| R-15-01 | Patch v3_209 backfill sai imm_part_class → watchlist breach false alerts | Medium | High | Dev Lead | Manual review sau deploy; smoke test item count |
| R-15-02 | Workflow conflict: IMM-15 Allocation state chồng lên IMM-08 PM WO submit hook | Low | Critical | Dev Lead | Test on staging với real IMM-08 WO; rollback plan §VI |
| R-15-03 | Property Setter v3_208 làm hỏng LIVE AC Stock Movement tạo mới | Low | High | Dev Lead | Test staging; smoke test SE creation after deploy |
| R-15-04 | Emergency Override bị dùng sai → compliance violation | Medium | High | QA Lead | VR-15-10 enforce dual approver; audit trail immutable; weekly report |
| R-15-05 | Scheduler check_critical_spare_breach chạy sai giờ → email flood | Low | Medium | CMMS Admin | Verify cron expression; test với `bench execute` trước |

---

## §X — Training & Communication Plan

| Milestone | Nội dung | Audience | Format |
|---|---|---|---|
| T-14 | Thông báo kế hoạch deploy | All users | Email |
| T-7 | Training session: Allocation flow + Cycle Count | Storekeeper, Workshop Head, Biomed, HTM Tech | Zoom + demo STAGING |
| T-7 | Training: Emergency Override policy (VR-15-10) | Workshop Head, VP Block 1 | In-person |
| T-1 | Go/No-go meeting | Dev + QA + Ops | Meeting |
| T=0 (deploy) | Deploy off-peak (00:00-06:00) | — | — |
| T+1 | Support hotline available | All | Slack + phone |
| T+7 | Post-launch review meeting | Dev + Ops + QA | Meeting |
| T+30 | KPI baseline review (first month data) | Workshop Head, VP B1, Accountant | Dashboard review |

### Audit Readiness Checklist

| Item | Status |
|---|---|
| IMM Audit Trail captures all 10 action types (§VII.1 TC-15-13) | ☐ Verified |
| Immutable audit records (no delete permission) | ☐ Verified |
| Emergency Override dual-approver enforced (VR-15-10) | ☐ Verified |
| Traceability batch_no enforce (VR-15-02) | ☐ Verified |
| QMS document set published in document control system | ☐ Done |
| KPI dashboard accessible to QA Officer and Management | ☐ Verified |
| AC Stock Movement reference_type includes IMM Spare Allocation | ☐ Verified |

---

*IMM-15 Module — Wave 2 IMPLEMENTED. Deployment v1.0.0-rc.2. Cập nhật 2026-05-18.*
