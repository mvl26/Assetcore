---
title: "BR_BR-12-P1 — P1 Incident SLA Escalation"
tags: [BusinessRule, IMM12, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `BR-12-P1` — P1 Incident SLA Escalation

> #BusinessRule | Module: `IMM-12` | DocType: [[Corrective Work Order (pending)]]

## Definition

P1: Response SLA = 120 phút. Quá hạn → L1 escalate Workshop Head. Quá hạn + 30 phút → L2 escalate VP Block2.

## Trigger

```
tasks.py scheduler (hourly)
```

## Blocking Behaviour

sendmail + publish_realtime theo level.

## Code Reference

`tasks.py (planned)`

## Linked DocType

[[Corrective Work Order (pending)]]
