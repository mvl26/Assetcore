---
title: "BR_IMM05-VR-08 — File Format Validation"
tags: [BusinessRule, IMM05, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `IMM05-VR-08` — File Format Validation

> #BusinessRule | Module: `IMM-05` | DocType: [[Asset Document]]

## Definition

Chỉ chấp nhận định dạng PDF, JPG, JPEG, PNG, DOCX.

## Trigger

```
validate() khi file_attachment IS SET
```

## Blocking Behaviour

Throw VR-08 nếu sai định dạng.

## Code Reference

`asset_document.py::vr_08_file_format_check()`

## Linked DocType

[[Asset Document]]
