---
title: "BR_IMM05-VR-10 — Exempt Fields Required"
tags: [BusinessRule, IMM05, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `IMM05-VR-10` — Exempt Fields Required

> #BusinessRule | Module: `IMM-05` | DocType: [[Asset Document]]

## Definition

Khi đánh dấu miễn đăng ký NĐ98 phải có exempt_reason + exempt_proof.

## Trigger

```
validate() khi is_exempt = True
```

## Blocking Behaviour

Throw VR-10.

## Code Reference

`asset_document.py::vr_10_exempt_fields_required()`

## Linked DocType

[[Asset Document]]
