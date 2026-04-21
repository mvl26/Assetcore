---
title: "IMM-08 — Preventive Maintenance (PM)"
tags: [Module, AssetCore, Wave1, IMM08]
generated: "2026-04-17 17:23"
---

# IMM-08 — Preventive Maintenance (PM)

```mermaid
flowchart LR
    IN["📥 Input\nPM Schedule + Asset ID"] --> PROC["IMM-08 Process"]
    PROC --> OUT["📤 Output\nPM Work Order (immutable after submit) + Next Due Date update"]
    PROC --> SLA["⏱ SLA\nnext_due_date = completion_date + interval_days (BR-08)"]
```

## Summary

| Field | Value |
|-------|-------|
| **Module** | `IMM-08` |
| **Actor** | HTM Technician / Biomed Engineer |
| **Primary DocType** | [[PM Work Order (pending implementation)]] |
| **SLA** | next_due_date = completion_date + interval_days (BR-08) |
| **KPI** | PM Compliance Rate, MTBF, On-time PM % |

## Input / Output

- **Input:** PM Schedule + Asset ID
- **Output:** PM Work Order (immutable after submit) + Next Due Date update

## Workflow States

`Scheduled → In Progress → Completed / Deferred`

## Business Rules

- [[BR_BR-SLA-PM]] — PM Next Due Date Calculation
