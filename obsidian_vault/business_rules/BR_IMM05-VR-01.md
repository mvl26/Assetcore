---
title: "BR_IMM05-VR-01 — Expiry After Issued Date"
tags: [BusinessRule, IMM05, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `IMM05-VR-01` — Expiry After Issued Date

> #BusinessRule | Module: `IMM-05` | DocType: [[Asset Document]]

## Definition

expiry_date phải sau issued_date.

## Trigger

```
validate()
```

## Blocking Behaviour

Throw VR-01 nếu expiry_date <= issued_date.

## Code Reference

`asset_document.py::vr_01_expiry_after_issued()`

## Linked DocType

[[Asset Document]]
