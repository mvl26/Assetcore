---
title: "BR_GW-2 — IMM-05 Document Compliance Gateway"
tags: [BusinessRule, IMM04IMM05, AssetCore]
generated: "2026-04-17 17:23"
---

# BR `GW-2` — IMM-05 Document Compliance Gateway

> #BusinessRule | Module: `IMM-04 → IMM-05` | DocType: [[Asset Commissioning]]

## Definition

Thiết bị phải có Chứng nhận đăng ký lưu hành (Active) trong IMM-05 hoặc được đánh dấu Exempt (NĐ 98/2021) trước khi Submit.

## Trigger

```
validate() khi workflow_state ∈ {Clinical_Release, Pending_Release} AND final_asset IS SET
```

## Blocking Behaviour

Throw kèm message 'GW-2 Compliance Block'.

## Code Reference

`asset_commissioning.py::_gw2_check_document_compliance()`

## Linked DocType

[[Asset Commissioning]]
