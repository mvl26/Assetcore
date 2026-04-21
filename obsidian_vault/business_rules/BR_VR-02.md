---
title: "BR_VR-02 — Required Documents Gate"
tags: [BusinessRule, IMM04, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `VR-02` — Required Documents Gate

> #BusinessRule | Module: `IMM-04` | DocType: [[Asset Commissioning]]

## Definition

Các hồ sơ bắt buộc CO và CQ phải có status = 'Received' trước khi bàn giao máy.

## Trigger

```
validate() khi workflow_state ∈ {Pending_Handover, Installing, Identification, Initial_Inspection, Re_Inspection, Pending_Release, Clinical_Release}
```

## Blocking Behaviour

Throw ValidationError nếu CQ hoặc CO != Received.

## Code Reference

`asset_commissioning.py::validate_required_documents()`

## Linked DocType

[[Asset Commissioning]]
