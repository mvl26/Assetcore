---
title: "BR_BR-07 — Auto-Import Document Set"
tags: [BusinessRule, IMM04IMM05, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `BR-07` — Auto-Import Document Set

> #BusinessRule | Module: `IMM-04 → IMM-05` | DocType: [[Asset Commissioning]]

## Definition

US-03: Tự động import toàn bộ commissioning_documents có status=Received sang IMM-05 (Asset Document) dưới dạng Draft.

## Trigger

```
on_submit() — sau khi mint_core_asset()
```

## Blocking Behaviour

N/A — auto-create, log error nếu thất bại.

## Code Reference

`asset_commissioning.py::create_initial_document_set()`

## Linked DocType

[[Asset Commissioning]]
