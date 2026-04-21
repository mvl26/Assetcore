---
title: "BR_VR-01 — Serial Number Uniqueness"
tags: [BusinessRule, IMM04, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `VR-01` — Serial Number Uniqueness

> #BusinessRule | Module: `IMM-04` | DocType: [[Asset Commissioning]]

## Definition

Vendor Serial Number phải duy nhất trên toàn hệ thống — kiểm tra trong cả `tabAsset` (custom_vendor_serial) và `tabAsset Commissioning` (docstatus != 2).

## Trigger

```
validate()
```

## Blocking Behaviour

Throw ValidationError khi trùng serial.

## Code Reference

`asset_commissioning.py::validate_unique_serial()`

## Linked DocType

[[Asset Commissioning]]
