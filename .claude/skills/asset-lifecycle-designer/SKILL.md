---
name: asset-lifecycle-designer
description: Design complete lifecycle workflows for medical device events in AssetCore — states, transitions, triggers, SLA rules, audit trail, WHO HTM alignment
type: skill
---

# Asset Lifecycle Designer — AssetCore

## What This Skill Does

Given a device lifecycle event or phase, design a **complete lifecycle workflow** with states, transitions, actors, SLA rules, audit trail entries, and WHO HTM alignment.

## Input

User provides one of:

- Event name: `"PM completed"` or `"device failure reported"`
- Phase: `"Commissioning (IMM-04)"`
- Question: `"What happens when a device fails calibration?"`

## Output Format

### 1. Lifecycle Context

```text
Event: <name>
Phase: Needs → Procurement → Installation → Operation → Maintenance → Decommission
Module: IMM-XX
Trigger: <what initiates this event>
Actor: <role who triggers it>
```

### 2. State Machine

```text
States:
  <state_1>: <description>
  <state_2>: <description>
  ...

Transitions:
  <from> --[action: actor]--> <to>
    Guard: <condition that must be true>
    Side effect: <what happens automatically>
    SLA: <time limit if applicable>
```

### 3. Lifecycle Event Record

Every state transition must create a Lifecycle Event record:

```text
LifecycleEvent {
  asset: <asset.name>
  event_type: <installed | commissioned | pm_completed | failure_reported | repaired | retired | ...>
  timestamp: <datetime>
  actor: <frappe.session.user>
  from_state: <previous workflow state>
  to_state: <new workflow state>
  root_record: <DocType.name that triggered this>
  notes: <optional>
}
```

### 4. SLA Rules

| Transition | SLA | Escalation | Breach Action |
| --- | --- | --- | --- |
| reported → assigned | 2h (Critical) / 4h (High) | Notify Workshop Head | Set sla_status=Breached |
| assigned → resolved | 4h (Critical) / 48h (Medium) | Notify CMMS Admin | CAPA trigger |

### 5. Notifications

```text
On <state>:
  Notify: <role/user>
  Channel: Email / In-app / Both
  Template: <what the notification says>
  Condition: <optional — only if ...>
```

### 6. Integration Points

What other modules are affected by this lifecycle event?

```text
Triggers:
  → Create Work Order (if action required)
  → Update Asset.status
  → Update Maintenance Plan.last_completed
  → Fire CAPA (if breach condition)
  → Update KPI counters
```

### 7. WHO HTM Alignment

Map each state to the WHO HTM lifecycle phase:

- Needs Assessment
- Procurement
- Incoming Inspection
- Commissioning & Acceptance
- Operation & Use
- Maintenance (PM / CM / Calibration)
- Decommissioning & Disposal

### 8. Implementation Checklist

- [ ] All states defined in Frappe Workflow DocType
- [ ] All transitions have role guards
- [ ] Every transition fires a Lifecycle Event record
- [ ] SLA deadline set on enter of actionable state
- [ ] SLA check runs via scheduled task (every hour)
- [ ] Notifications configured per state
- [ ] Dashboard KPI updated on terminal state
- [ ] Audit trail complete (no gaps between states)

## Core Lifecycle Events (Reference)

| Event Type | Trigger | From State | To State |
| --- | --- | --- | --- |
| received | GRN created | — | In_Receiving |
| inspection_passed | Acceptance test OK | In_Receiving | Ready_to_Commission |
| commissioned | Commissioning doc approved | Ready_to_Commission | In_Service |
| pm_scheduled | Maintenance Plan active | In_Service | In_Service |
| pm_completed | Work Order closed | PM_In_Progress | In_Service |
| failure_reported | Incident created | In_Service | Out_of_Service |
| repair_completed | CM Work Order closed | Under_Repair | In_Service |
| calibration_expired | Date passed | In_Service | Pending_Calibration |
| calibration_done | Calibration WO closed | Pending_Calibration | In_Service |
| decommissioned | Decommission approved | In_Service | Decommissioned |

## Step-by-Step Execution

1. Identify the triggering event and its IMM module
2. Map current asset state before the event
3. Define all possible resulting states
4. Draw the state machine with transitions and guards
5. Define SLA rules for each actionable state
6. Specify the Lifecycle Event record fields for each transition
7. List notifications per state
8. List integration side effects
9. Map to WHO HTM phase
10. Output implementation checklist
