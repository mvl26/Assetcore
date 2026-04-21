---
title: "BR_IMM05-VR-07 — Legal/Certification Requires Expiry Date"
tags: [BusinessRule, IMM05, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `IMM05-VR-07` — Legal/Certification Requires Expiry Date

> #BusinessRule | Module: `IMM-05` | DocType: [[Asset Document]]

## Definition

Tài liệu pháp lý bắt buộc có expiry_date (NĐ 98/2021 mandate).

## Trigger

```
validate() khi doc_category ∈ {Legal, Certification}
```

## Blocking Behaviour

Throw VR-07.

## Code Reference

`asset_document.py::vr_07_legal_requires_expiry()`

## Linked DocType

[[Asset Document]]
