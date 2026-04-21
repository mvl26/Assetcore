---
title: "BR_VR-03 — Baseline Test Completion"
tags: [BusinessRule, IMM04, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `VR-03` — Baseline Test Completion

> #BusinessRule | Module: `IMM-04` | DocType: [[Asset Commissioning]]

## Definition

Toàn bộ tiêu chí an toàn điện (IEC 60601-1) phải có kết quả. Nếu kết quả Fail bắt buộc điền fail_note.

## Trigger

```
validate() khi workflow_state ∈ {Initial_Inspection, Re_Inspection, Clinical_Release}
```

## Blocking Behaviour

VR-03a: Thiếu result. VR-03b: Có Fail nhưng cố Release.

## Code Reference

`asset_commissioning.py::validate_checklist_completion()`

## Linked DocType

[[Asset Commissioning]]
