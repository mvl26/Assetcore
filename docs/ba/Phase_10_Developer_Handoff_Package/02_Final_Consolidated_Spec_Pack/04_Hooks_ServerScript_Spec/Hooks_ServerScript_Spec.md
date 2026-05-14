> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# HOOKS & SERVER SCRIPT SPEC — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** Tech Lead

---

## 1. Vị trí & quy ước
- File path: `assetcore/<domain>/<doctype>/<event>.py`.
- Function naming: `on_<event>_<doctype>` hoặc `validate_<doctype>`.
- Đăng ký trong `assetcore/hooks.py`.

## 2. doctype_events (sample registration)

```python
doc_events = {
    "AC Medical Asset": {
        "before_save": "assetcore.asset_registry.medical_asset.validations.before_save",
        "before_submit": "assetcore.asset_registry.medical_asset.workflow.before_submit",
        "on_submit": "assetcore.asset_registry.medical_asset.workflow.on_submit",
        "on_update_after_submit": "assetcore.asset_registry.medical_asset.workflow.on_update_after_submit",
        "before_cancel": "assetcore.asset_registry.medical_asset.workflow.before_cancel",
    },
    "AC Document Record": {
        "before_save": "assetcore.documents.document_record.validations.before_save",
        "on_submit": "assetcore.documents.document_record.workflow.on_submit",
    },
    "AC Work Order": {
        "before_save": "assetcore.work_management.work_order.validations.before_save",
        "before_submit": "assetcore.work_management.work_order.workflow.before_submit",
        "on_submit": "assetcore.work_management.work_order.workflow.on_submit",
    },
    "AC Failure Report": {
        "on_submit": "assetcore.work_management.failure_report.workflow.on_submit",
    },
    "AC Calibration Record": {
        "on_submit": "assetcore.work_management.calibration_record.workflow.on_submit",
    },
    "AC CAPA": {
        "before_submit": "assetcore.compliance.capa.workflow.before_submit",
        "on_submit": "assetcore.compliance.capa.workflow.on_submit",
    },
    "Purchase Receipt": {
        "on_submit": "assetcore.integration.erpnext.purchase_receipt.on_submit",
    },
    "Stock Entry": {
        "on_submit": "assetcore.integration.erpnext.stock_entry.on_submit",
    },
    "Asset": {
        "on_update": "assetcore.integration.erpnext.asset.on_update",
    },
}
```

## 3. Cron / Scheduled jobs

```python
scheduler_events = {
    "daily": [
        "assetcore.documents.document_record.cron.expire_documents",
        "assetcore.documents.document_record.cron.expiry_alert",
        "assetcore.work_management.pm_scheduler.run",
        "assetcore.work_management.calibration_scheduler.run",
        "assetcore.compliance.compliance_detector.scan_pm_overdue",
        "assetcore.compliance.compliance_detector.scan_cal_overdue",
        "assetcore.compliance.compliance_detector.scan_license_expired_in_use",
        "assetcore.metrics.snapshot.daily_snapshot",
        "assetcore.qms.artifact.cron.next_review_alert",
        "assetcore.integration.erpnext.recon.run",
        "assetcore.dq.audit.daily_audit",
    ],
    "hourly": [
        "assetcore.lifecycle.dispatcher.run",  # outbox
    ],
    "cron": {
        "*/1 * * * *": [
            "assetcore.sla.monitor.tick",  # SLA monitor mỗi phút
        ],
        "0 * * * *": [
            "assetcore.metrics.snapshot.hourly_snapshot",  # nếu cần
        ],
        "0 0 1 * *": [
            "assetcore.metrics.snapshot.monthly_snapshot",
        ]
    },
}
```

## 4. Permission queries (custom)

```python
permission_query_conditions = {
    "AC Medical Asset": "assetcore.permissions.medical_asset.permission_query",
    "AC Work Order": "assetcore.permissions.work_order.permission_query",
    "AC Document Record": "assetcore.permissions.document.permission_query",
    "AC Lifecycle Event": "assetcore.permissions.lifecycle.permission_query",
}

has_permission = {
    "AC Work Order": "assetcore.permissions.work_order.has_permission",
}
```

## 5. Server script samples

### 5.1 Before save AC Medical Asset
```python
def before_save(doc, method):
    # Validate asset_code regex
    import re
    if not re.match(r"^[A-Z0-9]{2,4}-[A-Z]{2,5}-[A-Z0-9]{2,5}-\d{4,8}$", doc.asset_code or ""):
        frappe.throw("Asset code không hợp lệ theo Naming Convention")
    # FK existence
    if doc.device_model and not frappe.db.exists("AC Device Model", doc.device_model):
        frappe.throw("Device Model không tồn tại")
    # Block edit asset_code post-commission
    if doc.has_value_changed("asset_code") and doc.state in ("commissioned", "released_for_use"):
        frappe.throw("Asset code không thể đổi sau commission")
```

### 5.2 On submit Failure Report → tạo WO CM
```python
def on_submit(doc, method):
    wo = frappe.get_doc({
        "doctype": "AC Work Order",
        "wo_type": "CM",
        "medical_asset": doc.medical_asset,
        "priority": map_severity_to_priority(doc.severity),
        "severity": doc.severity,
        "location": doc.location,
        "linked_failure_report": doc.name,
        "planned_start_at": frappe.utils.now(),
    })
    wo.insert()
    wo.submit()
    # Update FR
    doc.linked_wo = wo.name
    doc.db_set("linked_wo", wo.name)
    # Publish LE
    publish_event("failure_reported", subject=doc.medical_asset, source=doc.name, payload={
        "severity": doc.severity,
        "linked_wo": wo.name,
    })
```

### 5.3 Cron PM scheduler
```python
def run():
    today = frappe.utils.today()
    plans = frappe.get_all("AC PM Plan",
        filters={"state": "approved"},
        fields=["name", "medical_asset", "frequency", "lead_time_days", "tasks_template"])
    for plan in plans:
        next_due = compute_next_due(plan)
        if (next_due - today).days <= plan.lead_time_days:
            if not wo_exists_in_window(plan, next_due):
                create_wo_pm(plan, next_due)
```

### 5.4 Lifecycle Event publisher
```python
def publish(event_type, subject, source, payload, evidence_refs=None):
    # Validate payload schema
    schema = frappe.get_doc("AC Event Type", event_type).expected_payload_schema
    validate_jsonschema(payload, schema)
    # Insert immutable
    le = frappe.get_doc({
        "doctype": "AC Lifecycle Event",
        "event_type": event_type,
        "occurred_at": frappe.utils.now(),
        "actor_user": frappe.session.user,
        "actor_role": get_actor_role(),
        "subject_doctype": subject["doctype"],
        "subject_name": subject["name"],
        "source_doctype": source["doctype"] if source else "",
        "source_name": source["name"] if source else "",
        "payload": json.dumps(payload),
        "evidence_refs": evidence_refs or [],
        "audit_class": resolve_audit_class(event_type),
    })
    le.insert(ignore_permissions=True)
    return le
```

### 5.5 PR.on_submit → tạo MA draft
```python
def on_submit(doc, method):
    for item in doc.items:
        if item.is_medical_device:
            for i in range(int(item.qty)):
                ma = frappe.get_doc({
                    "doctype": "AC Medical Asset",
                    "device_model": item.htm_device_model,
                    "serial_no": item.serial_no or auto_serial(item, i),
                    "facility": resolve_facility(doc),
                    "department": item.target_department,
                    "criticality": item.criticality or "C",
                    "risk_class": item.risk_class,
                    "state": "draft",
                    "imported_from_legacy": 0,
                })
                ma.insert(ignore_permissions=True)
```

## 6. ACL service `ERPNextAssetSync`

```python
def sync_ma_to_asset(ma_name):
    ma = frappe.get_doc("AC Medical Asset", ma_name)
    if not ma.erpnext_asset:
        return
    asset = frappe.get_doc("Asset", ma.erpnext_asset)
    asset.location = ma.location
    asset.custodian = ma.custodian_user
    asset.htm_state_mirror = ma.state
    asset.save(ignore_permissions=True)
```

## 7. Tiêu chí nghiệm thu Hooks/Server Script
- 100% hooks Wave 1 implement.
- Cron jobs chạy đúng giờ.
- Test coverage ≥ 70%.
- Permission queries enforce row-level.
- Lifecycle Event publisher single source.
