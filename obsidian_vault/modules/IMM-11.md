---
title: "IMM-11 — Calibration"
tags: [Module, AssetCore, Wave1, IMM11]
generated: "2026-04-17 17:23"
---

# IMM-11 — Calibration

```mermaid
flowchart LR
    IN["📥 Input\nDevice under test + Calibration certificate"] --> PROC["IMM-11 Process"]
    PROC --> OUT["📤 Output\nCalibration record (immutable) + Certificate in IMM-05 + Return to Service gate"]
    PROC --> SLA["⏱ SLA\ncertificate expiry tracked in IMM-05"]
```

## Summary

| Field | Value |
|-------|-------|
| **Module** | `IMM-11` |
| **Actor** | Biomed Engineer / External Calibration Body |
| **Primary DocType** | [[Calibration Record (pending implementation)]] |
| **SLA** | certificate expiry tracked in IMM-05 |
| **KPI** | Calibration compliance %, Out-of-tolerance rate |

## Input / Output

- **Input:** Device under test + Calibration certificate
- **Output:** Calibration record (immutable) + Certificate in IMM-05 + Return to Service gate

## Workflow States

`Scheduled → In Progress → Passed / Failed`
