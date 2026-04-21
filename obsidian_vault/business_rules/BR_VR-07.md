---
title: "BR_VR-07 — Radiation Device License Hold"
tags: [BusinessRule, IMM04, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `VR-07` — Radiation Device License Hold

> #BusinessRule | Module: `IMM-04` | DocType: [[Asset Commissioning]]

## Definition

Thiết bị bức xạ / tia X bắt buộc upload Giấy phép Cục An toàn Bức xạ Hạt nhân trước khi release.

## Trigger

```
validate() khi is_radiation_device = True AND workflow_state ∈ {Clinical_Release, Pending_Release}
```

## Blocking Behaviour

Throw VR-07 nếu qa_license_doc trống.

## Code Reference

`asset_commissioning.py::validate_radiation_hold()`

## Linked DocType

[[Asset Commissioning]]
