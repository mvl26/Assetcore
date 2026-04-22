# Asset Lifecycle Designer — Examples

## Example 1: Device Failure Reported (IMM-12)

**Input:** `"device failure reported in clinical dept"`

State Machine:

```text
In_Service --[report_failure: Clinical User]--> Out_of_Service
  Guard: asset.docstatus = 1
  Side effect: Create IncidentReport, Create CM Work Order

Out_of_Service --[assign_tech: Workshop Head]--> Under_Repair
  SLA: 4h (High), 2h (Critical)

Under_Repair --[close_work_order: HTM Technician]--> In_Service
  Side effect: Update root_cause, parts_used, repair_time
```

Lifecycle Event on failure:

```text
LifecycleEvent {
  event_type: "failure_reported"
  from_state: "In_Service"
  to_state: "Out_of_Service"
  root_record: "IncidentReport/IR-2026-00123"
}
```

---

## Example 2: PM Completed (IMM-08)

**Input:** `"scheduled PM work order closed"`

State Machine:

```text
In_Service --[generate_wo: Scheduler]--> PM_Scheduled
  Side effect: Create Work Order, set sla_deadline = due_date + 3 days

PM_Scheduled --[start_pm: HTM Technician]--> PM_In_Progress
PM_In_Progress --[complete: HTM Technician]--> In_Service
  Side effect: Update MaintenancePlan.last_completed, set next_due_date
  LifecycleEvent: pm_completed
```

SLA Rules:

| Transition | SLA | Breach |
| --- | --- | --- |
| scheduled → started | due_date | set sla_status=Breached, notify Workshop Head |
| started → completed | due_date + 2 days | CAPA trigger, notify CMMS Admin |

---

## Example 3: Calibration Expiry Flow (IMM-11)

**Input:** `"calibration certificate expires"`

Scheduled task (daily) detects `calibration_expiry_date < today`:

```text
In_Service --[system]--> Pending_Calibration
  Notify: Biomed Engineer, Tổ HC-QLCL
  SLA: Must complete within 30 days or device goes Out_of_Service

Pending_Calibration --[calibration_done: Biomed Engineer]--> In_Service
  Side effect: Update calibration_expiry_date, attach certificate

Pending_Calibration --[sla_breach: System]--> Out_of_Service
  CAPA trigger: "Device operated beyond calibration expiry"
```

WHO HTM Phase: **Maintenance → Calibration sub-phase**
