---
title: "Expiry Alert Log"
module: "IMM-05"
tags: [DocType, AssetCore, IMM05]
generated: "2026-04-17 17:23"
aliases: ["expiry_alert_log"]
---

# Expiry Alert Log

> **Module:** `IMM-05` | **App:** `assetcore` | **Generated:** 2026-04-17 17:23

## Entity Relationship

```mermaid
erDiagram
    EXPIRY_ALERT_LOG {
        string name PK "Document ID"
        string asset_document UK "Tài liệu"
        string asset_ref UK "Tài sản"
        string doc_type_detail "Loại Tài liệu"
        date expiry_date UK "Ngày hết hạn"
        int days_remaining UK "Số ngày còn lại"
        string alert_level UK "Mức cảnh báo"
        date alert_date UK "Ngày gửi cảnh báo"
    }
    ASSET_DOCUMENT {
        string name PK
    }
    EXPIRY_ALERT_LOG }o--|| ASSET_DOCUMENT : "asset_document"
    ASSET {
        string name PK
    }
    EXPIRY_ALERT_LOG }o--|| ASSET : "asset_ref"
```

## Overview

Immutable log of document expiry notifications. Created by daily scheduler at 90/60/30/0 day thresholds. Read-only after creation.

## Fields

| Fieldname | Type | Label | Required | Options/Link |
|-----------|------|-------|----------|-------------|
| `asset_document` | `Link` | Tài liệu | ✅ | [[Asset Document]] |
| `asset_ref` | `Link` | Tài sản | ✅ | [[Asset]] |
| `doc_type_detail` | `Data` | Loại Tài liệu |  |  |
| `expiry_date` | `Date` | Ngày hết hạn | ✅ |  |
| `days_remaining` | `Int` | Số ngày còn lại | ✅ |  |
| `alert_level` | `Select` | Mức cảnh báo | ✅ | Info
Warning
Critical
Danger |
| `alert_date` | `Date` | Ngày gửi cảnh báo | ✅ |  |
| `notified_users` | `Small Text` | Đã thông báo |  |  |

## Outgoing Links (Link Fields)

- `asset_document` → [[Asset Document]] *(required)*
- `asset_ref` → [[Asset]] *(required)*

## Related DocTypes

- [[Asset]]
- [[Asset Document]]
