---
title: "BR_VR-04 — Non-Conformance Release Block"
tags: [BusinessRule, IMM04, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `VR-04` — Non-Conformance Release Block

> #BusinessRule | Module: `IMM-04` | DocType: [[Asset Commissioning]]

## Definition

Không thể phát hành nếu còn Phiếu NC (Asset QA Non Conformance) với resolution_status = Open.

## Trigger

```
validate() khi workflow_state = Clinical_Release
```

## Blocking Behaviour

Throw kèm danh sách NC chưa đóng.

## Code Reference

`asset_commissioning.py::block_release_if_nc_open()`

## Linked DocType

[[Asset Commissioning]]
