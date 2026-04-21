---
title: "BR_IMM05-VR-02 — Unique Document Number"
tags: [BusinessRule, IMM05, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `IMM05-VR-02` — Unique Document Number

> #BusinessRule | Module: `IMM-05` | DocType: [[Asset Document]]

## Definition

doc_number phải duy nhất theo (asset_ref, doc_type_detail). Nếu là version mới thì tăng version field.

## Trigger

```
validate()
```

## Blocking Behaviour

Throw VR-02 nếu trùng.

## Code Reference

`asset_document.py::vr_02_unique_doc_number()`

## Linked DocType

[[Asset Document]]
