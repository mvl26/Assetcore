---
title: "Required Document Type"
module: "IMM-05"
tags: [DocType, AssetCore, IMM05]
generated: "2026-04-17 17:23"
aliases: ["required_document_type"]
---

# Required Document Type

> **Module:** `IMM-05` | **App:** `assetcore` | **Generated:** 2026-04-17 17:23

## Entity Relationship

```mermaid
erDiagram
    REQUIRED_DOCUMENT_TYPE {
        string name PK "Document ID"
        string type_name UK "Tên loại tài liệu"
        string doc_category UK "Nhóm"
        boolean has_expiry "Có ngày hết hạn"
        boolean is_mandatory "Bắt buộc cho mọi Asset"
        string applies_to_item_group "Áp dụng cho nhóm Item"
        boolean applies_when_radiation "Chỉ bắt buộc khi thiết bị bức xạ"
    }
    ITEM_GROUP {
        string name PK
    }
    REQUIRED_DOCUMENT_TYPE }o--|o ITEM_GROUP : "applies_to_item_group"
```

## Overview

Master configuration for mandatory document types per device category. Drives doc_completeness_pct calculation.

## Fields

| Fieldname | Type | Label | Required | Options/Link |
|-----------|------|-------|----------|-------------|
| `type_name` | `Data` | Tên loại tài liệu | ✅ |  |
| `doc_category` | `Select` | Nhóm | ✅ | Legal
Technical
Certification
Training
QA |
| `has_expiry` | `Check` | Có ngày hết hạn |  |  |
| `is_mandatory` | `Check` | Bắt buộc cho mọi Asset |  |  |
| `applies_to_item_group` | `Link` | Áp dụng cho nhóm Item |  | [[Item Group]] |
| `applies_when_radiation` | `Check` | Chỉ bắt buộc khi thiết bị bức xạ |  |  |

## Outgoing Links (Link Fields)

- `applies_to_item_group` → [[Item Group]]

## Related DocTypes

- [[Item Group]]
