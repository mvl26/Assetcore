---
title: "Commissioning Document Record"
module: "IMM-04"
tags: [DocType, AssetCore, IMM04]
generated: "2026-04-17 17:23"
aliases: ["commissioning_document_record"]
---

# Commissioning Document Record

> **Module:** `IMM-04` | **App:** `assetcore` | **Generated:** 2026-04-17 17:23

## Entity Relationship

```mermaid
erDiagram
    COMMISSIONING_DOCUMENT_RECORD {
        string name PK "Document ID"
        string doc_type UK "Loại Tài liệu"
        string status UK "Tình trạng"
        date received_date "Ngày Nhận"
    }
```

## Overview

Child table of Asset Commissioning. Tracks receipt status of each required document (CO, CQ, Packing List, etc.).

## Fields

| Fieldname | Type | Label | Required | Options/Link |
|-----------|------|-------|----------|-------------|
| `doc_type` | `Select` | Loại Tài liệu | ✅ | CO - Chứng nhận Xuất xứ
CQ - Chứng nhận Chất lượng
Packing List
Manual / HDSD
Warranty Card
Training Certificate
Other |
| `status` | `Select` | Tình trạng | ✅ | Pending
Received
Missing |
| `received_date` | `Date` | Ngày Nhận |  |  |
| `remarks` | `Small Text` | Ghi chú |  |  |
