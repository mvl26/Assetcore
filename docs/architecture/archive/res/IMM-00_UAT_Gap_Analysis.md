# IMM-00 Foundation — UAT & Gap Analysis Report

**Module:** IMM-00 Core Foundation  
**Date:** 2026-04-18  
**Author:** AssetCore Team (Claude Code)  
**Status:** 🔴 NOT READY — Blocking gaps exist before UAT sign-off  
**Next Module Gate:** IMM-04 / IMM-08 / IMM-09 blocked until IMM-00 UAT passes

---

## 1. Scope

IMM-00 covers the foundational domain entities that all other modules depend on:

| DocType | Type | Purpose |
|---|---|---|
| AC Asset | Core | Physical device registry |
| AC Supplier | Core | Vendor master |
| AC Location | Core | Physical location tree |
| AC Department | Core | Clinical department |
| AC Asset Category | Core | Device classification |
| IMM Device Model | Governance | Model/config template |
| IMM SLA Policy | Governance | Response time matrix |
| IMM Audit Trail | Governance | Immutable SHA-256 chain |
| IMM CAPA Record | Governance | Corrective & preventive action |
| Asset Lifecycle Event | Governance | State transition log |
| Incident Report | Standalone | Failure/adverse event log |
| IMM Device Spare Part | Child | Spare part catalog per model |
| AC Authorized Technician | Child | Technician authorization per asset |

---

## 2. Implementation Summary

| Layer | Files | Status |
|---|---|---|
| DocType JSONs | 13 doctypes | ✅ All created + migrated to AC Asset |
| Controllers | 11 `.py` controllers | ⚠️ Partial — missing validations |
| Services | `services/imm00.py` | ⚠️ Partial — missing 4 functions |
| API | `api/imm00.py` — 42 endpoints | ✅ Complete |
| Scheduler | hooks.py scheduler entries | 🔴 Missing — 4 jobs not registered |
| Tests | `tests/test_imm00.py` — 24 tests | ⚠️ Partial — covers ~30% of BRs |
| FE API Client | `frontend/src/api/imm00.ts` | ✅ 20 functions |
| FE Types | `frontend/src/types/imm00.ts` | ✅ Complete |
| FE Stores | `frontend/src/stores/imm00.ts` | ✅ 4 stores |
| FE Views | 5 views created | ⚠️ Partial — 8 views missing |

---

## 3. Functional Requirements Coverage

### FR-00-01 → FR-00-38

| FR | Description | Status | Evidence | Gap |
|---|---|---|---|---|
| FR-00-01 | Create AC Asset with mandatory fields | ✅ | DocType JSON + `ac_asset.py` | — |
| FR-00-02 | Asset naming series `ACC-YYYY-.NNNNN` | ✅ | `autoname: ACC-YYYY-.#####` | — |
| FR-00-03 | lifecycle_status state machine | ✅ | `transition_asset_status()` in `imm00.py` | — |
| FR-00-04 | Block invalid lifecycle transitions | ✅ | `_ALLOWED_TRANSITIONS` dict + throw | — |
| FR-00-05 | Lifecycle Event created on every transition | ✅ | `create_lifecycle_event()` called in service | — |
| FR-00-06 | lifecycle_status not directly editable | 🔴 | `ac_asset.py` has NO `validate()` guard | BR-00-02 missing |
| FR-00-07 | AC Asset links to IMM Device Model | ✅ | `device_model` Link field | — |
| FR-00-08 | AC Asset inherits risk_class from Device Model | 🔴 | No auto-inherit logic | Missing in controller |
| FR-00-09 | UDI / manufacturer_sn unique validation | ⚠️ | `imm04.py` checks SN; no UDI uniqueness | UDI check missing |
| FR-00-10 | Supplier CRUD with contact info | ✅ | AC Supplier DocType + CRUD API | — |
| FR-00-11 | Location tree (parent_location) | ✅ | AC Location with `is_group` + `parent_location` | — |
| FR-00-12 | Department linked to Location | ✅ | `location` Link in AC Department | — |
| FR-00-13 | Asset Category with PM/calibration intervals | ✅ | Fields exist in DocType JSON | — |
| FR-00-14 | Device Model with spare parts child table | ✅ | IMM Device Model + IMM Device Spare Part | — |
| FR-00-15 | Device Model risk_class → medical_device_class mapping | 🔴 | BR-00-01 not enforced in controller | Missing validation |
| FR-00-16 | SLA Policy matrix (P1-P4 × risk class) | ✅ | DocType + `get_sla_policy()` service | — |
| FR-00-17 | SLA Policy is_default fallback | ✅ | `get_sla_policy()` fallback logic | — |
| FR-00-18 | IMM Audit Trail created on every state change | ✅ | `create_audit_trail()` service | — |
| FR-00-19 | Audit Trail SHA-256 hash chain | ✅ | `_compute_hash()` + `prev_hash` chain | — |
| FR-00-20 | Audit Trail append-only (no edit/delete) | ✅ | `in_create: 1` + `validate()` blocks | — |
| FR-00-21 | Chain verification endpoint | ✅ | `verify_chain()` in api/imm00.py | — |
| FR-00-22 | CAPA lifecycle (Open → Under Review → Closed/Cancelled) | ✅ | `imm_capa_record.py` workflow | — |
| FR-00-23 | CAPA source_type links to origin record | ✅ | `source_ref` + `source_type` fields | — |
| FR-00-24 | CAPA due_date must be after opened_date | ✅ | `_validate_dates()` with `getdate()` | — |
| FR-00-25 | CAPA overdue alert (daily scheduler) | 🔴 | `check_capa_overdue()` exists but NOT in hooks | Scheduler missing |
| FR-00-26 | CAPA before_submit validates root_cause filled | 🔴 | `before_submit` not implemented | Missing |
| FR-00-27 | Asset KPI rollup (uptime, MTBF, MTTR, PM compliance) | ⚠️ | `get_asset_kpi()` in API exists; `rollup_asset_kpi()` missing | Scheduler missing |
| FR-00-28 | Incident Report create with mandatory fields | ✅ | Incident Report DocType + controller | — |
| FR-00-29 | Incident severity required | ⚠️ | Field exists; no `validate()` throw | VR-00-23 missing |
| FR-00-30 | patient_impact required when patient_affected=1 | 🔴 | `incident_report.py` has no validate() | VR-00-24 missing |
| FR-00-31 | Incident triggers CAPA if severity=Critical | 🔴 | No auto-link logic | VR-00-25 missing |
| FR-00-32 | Asset validate_for_operations check | ⚠️ | `validate_asset_for_operations()` in service; API calls it | Partial |
| FR-00-33 | Technician authorization per asset | ✅ | AC Authorized Technician child table | — |
| FR-00-34 | Permission query: technician sees only own assets | ✅ | `get_permission_query_conditions()` | — |
| FR-00-35 | Vendor contract expiry alert | 🔴 | `check_vendor_contract_expiry()` not in hooks | Scheduler missing |
| FR-00-36 | BYT registration expiry alert | 🔴 | `check_registration_expiry()` not in hooks | Scheduler missing |
| FR-00-37 | Monthly MTTR avg rollup | 🔴 | `rollup_asset_kpi()` not in hooks | Scheduler missing |
| FR-00-38 | Decommission blocks operations | ✅ | `transition_asset_status()` throws if Decommissioned | — |

**FR Coverage: 18 Implemented ✅ | 6 Partial ⚠️ | 14 Missing 🔴**

---

## 4. Business Rules Coverage

| BR | Rule | Status | Evidence | Fix Needed |
|---|---|---|---|---|
| BR-00-01 | Device Model: risk_class derived from medical_device_class | 🔴 | No mapping logic in controller | Add to `imm_device_model.py` validate() |
| BR-00-02 | AC Asset: lifecycle_status only via `transition_asset_status()` | 🔴 | `ac_asset.py` validate() missing guard | Block direct field edit in validate() |
| BR-00-03 | Lifecycle Event immutable (no edit/delete) | ✅ | `asset_lifecycle_event.py` validate() blocks | — |
| BR-00-04 | Audit Trail append-only + hash chain | ✅ | SHA-256 chain in `imm_audit_trail.py` | — |
| BR-00-05 | SLA Policy: only one is_default per (priority, risk_class) | ⚠️ | No validate() uniqueness check | Add to `imm_sla_policy.py` |
| BR-00-06 | CAPA cannot be submitted without root_cause | 🔴 | `before_submit` not implemented | Add to `imm_capa_record.py` |
| BR-00-07 | CAPA overdue = due_date passed + status not Closed | ✅ | `check_capa_overdue()` service exists | Register in hooks |
| BR-00-08 | Incident severity=Critical → auto-open CAPA | 🔴 | No trigger in `incident_report.py` | Add `after_insert` hook |
| BR-00-09 | Decommissioned asset blocks all Work Orders | ✅ | `validate_asset_for_operations()` | — |
| BR-00-10 | Technician sees only assets where responsible_technician = user | ✅ | `get_permission_query_conditions()` | — |

**BR Coverage: 5 ✅ | 2 ⚠️ | 3 🔴**

---

## 5. Validation Rules Coverage

| VR | Rule | Status | Gap |
|---|---|---|---|
| VR-00-01 | asset_name required | ✅ | — |
| VR-00-02 | asset_category required | ✅ | — |
| VR-00-03 | lifecycle_status valid enum | ✅ | Select field |
| VR-00-04 | purchase_date ≤ today | 🔴 | Not validated |
| VR-00-05 | warranty_expiry ≥ purchase_date | 🔴 | Not validated |
| VR-00-06 | calibration_due_date logic | 🔴 | Not validated |
| VR-00-07 | next_pm_date ≥ today on update | 🔴 | Not validated |
| VR-00-08 | manufacturer_sn unique if filled | ✅ | `imm04.py` checks on commissioning |
| VR-00-09 | udi_code format (GS1 pattern) | 🔴 | Not validated |
| VR-00-10 | byt_reg_no unique if filled | 🔴 | Not validated |
| VR-00-11 | Supplier company_name required | ✅ | Mandatory field |
| VR-00-12 | Supplier email format | 🔴 | Not validated |
| VR-00-13 | Location location_name required | ✅ | Mandatory field |
| VR-00-14 | Location no circular parent | 🔴 | Not validated |
| VR-00-15 | Asset Category category_name required | ✅ | Mandatory field |
| VR-00-16 | PM interval > 0 if has_pm_schedule | 🔴 | Not validated |
| VR-00-17 | Device Model model_name required | ✅ | Mandatory field |
| VR-00-18 | Device Model asset_category required | ✅ | Mandatory field |
| VR-00-19 | SLA response_time_hours > 0 | 🔴 | Not validated |
| VR-00-20 | SLA escalation_hours > response_time_hours | 🔴 | Not validated |
| VR-00-21 | CAPA due_date > opened_date | ✅ | `_validate_dates()` with getdate() |
| VR-00-22 | CAPA severity required | ✅ | Mandatory field |
| VR-00-23 | Incident severity required | ⚠️ | Field exists; no validate() throw |
| VR-00-24 | Incident patient_impact required if patient_affected | 🔴 | Missing in controller |
| VR-00-25 | Incident date_of_incident ≤ today | 🔴 | Not validated |
| VR-00-26 | Audit Trail record_id required | ✅ | Mandatory field |
| VR-00-27 | Lifecycle Event asset required | ✅ | Mandatory field |

**VR Coverage: 10 ✅ | 2 ⚠️ | 15 🔴**

---

## 6. API Coverage

All 42 endpoints exist in `api/imm00.py`. Verified by reading source.

| Group | Endpoints | Status |
|---|---|---|
| AC Asset CRUD | list, get, create, update | ✅ |
| Asset transitions | transition_status, validate_for_operations | ✅ |
| Asset analytics | get_timeline, get_kpi | ✅ |
| Reference data | suppliers, locations, departments, categories, device_models, sla_policies | ✅ |
| Audit Trail | list_audit_trail, verify_chain | ✅ |
| CAPA | list_capas, get_capa_overdue, open_capa | ✅ |
| Incident | list_incidents, create_incident | ✅ |

---

## 7. Frontend Coverage

| Screen | Status | File |
|---|---|---|
| Asset List (filter + paginate) | ✅ | `views/AssetListView.vue` |
| Asset Detail (tabs: info/timeline/KPI/audit) | ✅ | `views/AssetDetailView.vue` |
| Asset Create Form | ✅ | `views/AssetCreateView.vue` |
| CAPA List | ✅ | `views/CAPAListView.vue` |
| Incident List | ✅ | `views/IncidentListView.vue` |
| Supplier List | 🔴 | Missing |
| Location Tree | 🔴 | Missing |
| Department List | 🔴 | Missing |
| Device Model List | 🔴 | Missing |
| SLA Matrix View | 🔴 | Missing |
| Audit Trail List | 🔴 | Missing |
| CAPA Detail Form | 🔴 | Missing |
| Incident Create Wizard | 🔴 | Missing |

---

## 8. Test Coverage

Current: **24 tests** across 7 classes.

| Test Class | Tests | Coverage |
|---|---|---|
| TestACAsset | 4 | Naming, transition, lifecycle event, decommission block |
| TestACSupplierloc | 2 | Supplier create, location tree |
| TestIMMDeviceModel | 3 | Create, spare parts, category mandatory |
| TestIMMAuditTrail | 3 | Create on transition, no delete, chain verify |
| TestIMMCapaRecord | 5 | Create, date validation, open via service, close, overdue |
| TestAssetLifecycleEvent | 3 | Create, immutable actor, immutable event_type |
| TestIncidentReport | 4 | Create, severity required, patient_impact required, critical→CAPA |

**Missing test scenarios:** 26+ BR/VR Gherkin scenarios uncovered.

---

## 9. Prioritized Gap List

### 🔴 BLOCKING (must fix before UAT)

| # | Gap | File to Fix | Fix |
|---|---|---|---|
| B-01 | BR-00-02: Direct lifecycle_status edit not blocked | `ac_asset.py` | Add `validate()` that compares `self.lifecycle_status` vs db value and throws if changed without transition |
| B-02 | BR-00-06: CAPA submit without root_cause | `imm_capa_record.py` | Add `before_submit()` checking `root_cause` + `corrective_action` |
| B-03 | BR-00-08: Critical Incident → auto-open CAPA | `incident_report.py` | Add `after_insert()` that calls `create_capa()` if severity=Critical |
| B-04 | VR-00-24: patient_impact required if patient_affected | `incident_report.py` | Add `validate()` |
| B-05 | 4 Scheduler jobs not registered in hooks.py | `hooks.py` | Add `scheduler_events` for daily + monthly jobs |
| B-06 | FR-00-15: Device Model risk mapping | `imm_device_model.py` | Add `validate()` auto-derive risk_class from medical_device_class |

### 🟠 HIGH (fix before next sprint)

| # | Gap | Fix |
|---|---|---|
| H-01 | VR-00-04/05: date validations on AC Asset | Add to `ac_asset.py` validate() |
| H-02 | BR-00-05: SLA Policy uniqueness | Add to `imm_sla_policy.py` validate() |
| H-03 | VR-00-16: PM interval > 0 if has_pm_schedule | Add to `ac_asset_category.py` validate() |
| H-04 | VR-00-19/20: SLA response_time validation | Add to `imm_sla_policy.py` validate() |
| H-05 | FR-00-08: Asset inherits risk_class from Device Model | Add on_update trigger or controller logic |

### 🟡 MEDIUM (nice-to-have for UAT completeness)

| # | Gap | Fix |
|---|---|---|
| M-01 | VR-00-09: UDI GS1 format validation | Regex in `ac_asset.py` |
| M-02 | VR-00-10: byt_reg_no uniqueness | DB exists check |
| M-03 | VR-00-12: Supplier email format | frappe email validate |
| M-04 | VR-00-14: Location circular parent check | Traverse check |
| M-05 | 8 missing FE screens | New Vue components |
| M-06 | 26+ missing test cases | Expand test_imm00.py |

---

## 10. UAT Test Cases (Gherkin)

### TC-IMM00-001: Asset Lifecycle Transition (Happy Path)

```gherkin
Given an AC Asset in "Commissioned" status
When Workshop Technician calls transition_asset_status("Active")
Then AC Asset.lifecycle_status = "Active"
And an Asset Lifecycle Event is created with from="Commissioned", to="Active"
And an IMM Audit Trail entry is created
```

### TC-IMM00-002: Block Direct Status Edit

```gherkin
Given an AC Asset in "Active" status
When a user directly sets lifecycle_status = "Decommissioned" via frappe.set_value
Then frappe.throw is called with "BR-00-02" message
And the Asset remains "Active"
```
**Status: 🔴 FAILING — BR-00-02 not implemented**

### TC-IMM00-003: Block Invalid Transition

```gherkin
Given an AC Asset in "Commissioned" status
When transition_asset_status("Decommissioned") is called
Then frappe.throw is raised with "không hợp lệ" message
And lifecycle_status remains "Commissioned"
```

### TC-IMM00-004: Decommissioned Asset Blocks Operations

```gherkin
Given an AC Asset with lifecycle_status = "Decommissioned"
When validate_asset_for_operations(asset_name) is called
Then frappe.throw is raised
And the calling Work Order cannot be created
```

### TC-IMM00-005: Audit Trail Hash Chain Integrity

```gherkin
Given 3 IMM Audit Trail records for the same asset
When verify_chain(asset_name) is called
Then result.valid = True
And result.record_count = 3
```

### TC-IMM00-006: Tampered Audit Trail Detected

```gherkin
Given an IMM Audit Trail record
When the record's "notes" field is modified directly in DB
And verify_chain is called
Then result.valid = False
And result.broken_at is the tampered record name
```

### TC-IMM00-007: CAPA Submit Without Root Cause

```gherkin
Given an open CAPA Record with root_cause = ""
When the document is submitted
Then frappe.throw is raised "root_cause là bắt buộc"
And docstatus remains 0
```
**Status: 🔴 FAILING — before_submit not implemented**

### TC-IMM00-008: CAPA Overdue Detection

```gherkin
Given a CAPA Record with due_date = yesterday and status = "Open"
When check_capa_overdue() scheduler runs
Then CAPA.is_overdue = 1
And the responsible user receives a realtime alert
```

### TC-IMM00-009: Critical Incident Auto-Opens CAPA

```gherkin
Given a new Incident Report is inserted with severity = "Critical"
When after_insert fires
Then a new IMM CAPA Record is created with source_type = "Incident"
And source_ref = incident_name
And severity = "Critical"
```
**Status: 🔴 FAILING — after_insert not implemented**

### TC-IMM00-010: Patient Impact Required

```gherkin
Given an Incident Report with patient_affected = 1
When validate() runs with patient_impact = ""
Then frappe.throw is raised "patient_impact là bắt buộc"
```
**Status: 🔴 FAILING — validate() not implemented**

### TC-IMM00-011: SLA Policy Lookup (Happy Path)

```gherkin
Given an SLA Policy with priority = "P1", risk_class = "High"
When get_sla_policy("P1", "High") is called
Then the matching policy is returned
```

### TC-IMM00-012: SLA Policy Default Fallback

```gherkin
Given no SLA Policy for priority = "P4", risk_class = "Critical"
But one SLA Policy with is_default = 1 exists
When get_sla_policy("P4", "Critical") is called
Then the default policy is returned
```

### TC-IMM00-013: Device Model Risk Class Mapping

```gherkin
Given a Device Model with medical_device_class = "Class III"
When the model is saved
Then risk_class is automatically set to "High"
```
**Status: 🔴 FAILING — mapping not implemented**

### TC-IMM00-014: Technician Permission Filter

```gherkin
Given Technician user "tech@hospital.vn" logs in
And there are 10 AC Assets, 3 with responsible_technician = "tech@hospital.vn"
When the technician calls list_assets()
Then only 3 assets are returned
```

### TC-IMM00-015: Lifecycle Event Immutability

```gherkin
Given an Asset Lifecycle Event record
When a user tries to change the "actor" field
Then frappe.throw is raised
And the event remains unchanged
```

### TC-IMM00-016: Vendor Contract Expiry Alert (Scheduler)

```gherkin
Given an AC Asset with vendor_contract_expiry = 25 days from now
When the daily scheduler check_vendor_contract_expiry() runs
Then a notification is sent to the responsible technician
```
**Status: 🔴 FAILING — scheduler not registered**

### TC-IMM00-017: BYT Registration Expiry Alert (Scheduler)

```gherkin
Given an AC Asset with byt_reg_expiry = 30 days from now
When check_registration_expiry() runs
Then an email alert is sent to Workshop Manager
```
**Status: 🔴 FAILING — scheduler not registered**

### TC-IMM00-018: Monthly KPI Rollup

```gherkin
Given an AC Asset with 5 completed repair Work Orders in last 12 months
When rollup_asset_kpi() monthly scheduler runs
Then AC Asset.mttr_hours = AVG of last 12 mttr values
And AC Asset.uptime_pct is recalculated
```
**Status: 🔴 FAILING — scheduler not registered**

---

## 11. Action Plan Before UAT Sign-Off

### Sprint IMM-00-Fix (estimated 2–3 days)

#### Day 1 — Blocking fixes

1. `ac_asset.py` — Add `validate()` for BR-00-02 (direct status edit block)
2. `imm_capa_record.py` — Add `before_submit()` for BR-00-06
3. `incident_report.py` — Add `validate()` for VR-00-24 + `after_insert()` for BR-00-08
4. `imm_device_model.py` — Add `validate()` for FR-00-15 risk_class mapping
5. `hooks.py` — Register 4 scheduler jobs

#### Day 2 — High priority + test expansion

6. `imm_sla_policy.py` — Add BR-00-05 uniqueness validation + VR-00-19/20
7. `ac_asset.py` — Add VR-00-04/05/09/10 date + format validations
8. `ac_asset_category.py` — Add VR-00-16 PM interval validation
9. Expand `test_imm00.py` to cover 18 additional test cases (TC-IMM00-002 through -018)

#### Day 3 — FE + manual UAT

10. Build missing FE screens (Supplier List, Location Tree, SLA Matrix minimum)
11. Execute manual UAT walkthroughs for all 18 GherkinTCs
12. Fix regression failures
13. UAT sign-off

---

## 12. UAT Sign-Off Criteria

IMM-00 is UAT-complete when ALL of:

- [ ] All 18 Gherkin test cases pass (automated)
- [ ] 0 🔴 BLOCKING gaps remain
- [ ] `bench run-tests --module assetcore.tests.test_imm00` passes 40+ tests with 0 failures
- [ ] Manual walkthrough of Asset Lifecycle flow (Commissioned → Active → Decommissioned) confirmed
- [ ] Audit Trail chain verify returns `valid=True` after 5+ transitions
- [ ] Scheduler jobs confirmed registered (check `hooks.py` + `bench doctor`)
- [ ] FE: Asset List + Detail + Create screens functional in browser
- [ ] QA Officer review of CAPA workflow (Open → Submit → Close)

---

*Generated: 2026-04-18 | AssetCore v3 | IMM-00 Foundation Module*
