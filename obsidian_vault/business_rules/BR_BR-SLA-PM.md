---
title: "BR_BR-SLA-PM — PM Next Due Date Calculation"
tags: [BusinessRule, IMM08, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `BR-SLA-PM` — PM Next Due Date Calculation

> #BusinessRule | Module: `IMM-08` | DocType: [[PM Work Order (pending)]]

## Definition

Next Due Date = Completion Date + Interval (ngày thực hoàn thành, KHÔNG phải ngày dự kiến). Đảm bảo lịch bám thực tế.

## Trigger

```
on_submit() của PM Work Order
```

## Blocking Behaviour

N/A — tính toán trường next_due_date.

## Code Reference

`services/imm08.py (planned)`

## Linked DocType

[[PM Work Order (pending)]]
