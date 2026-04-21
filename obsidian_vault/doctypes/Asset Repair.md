---
title: "Asset Repair"
module: "IMM-09"
tags: [DocType, AssetCore, IMM09]
generated: "2026-04-17 17:23"
aliases: ["asset_repair"]
---

# Asset Repair

> **Module:** `IMM-09` | **App:** `assetcore` | **Generated:** 2026-04-17 17:23

## Entity Relationship

```mermaid
erDiagram
    ASSET_REPAIR {
        string name PK "Document ID"
        string asset UK "Asset"
        string company "Company"
        string naming_series UK "Series"
        datetime failure_date UK "Failure Date"
        string repair_status "Repair Status"
        datetime completion_date "Completion Date"
        string cost_center "Cost Center"
        string project "Project"
        string purchase_invoice "Purchase Invoice"
        boolean capitalize_repair_cost "Capitalize Repair Cost"
        boolean stock_consumption "Stock Consumed During Repair"
        decimal repair_cost "Repair Cost"
    }
    ASSET {
        string name PK
    }
    ASSET_REPAIR }o--|| ASSET : "asset"
    COMPANY {
        string name PK
    }
    ASSET_REPAIR }o--|o COMPANY : "company"
    COST_CENTER {
        string name PK
    }
    ASSET_REPAIR }o--|o COST_CENTER : "cost_center"
    PROJECT {
        string name PK
    }
    ASSET_REPAIR }o--|o PROJECT : "project"
    PURCHASE_INVOICE {
        string name PK
    }
    ASSET_REPAIR }o--|o PURCHASE_INVOICE : "purchase_invoice"
    ASSET_REPAIR }o--|o ASSET_REPAIR : "amended_from"
    ASSET_REPAIR_CONSUMED_ITEM {
        string name PK
    }
    ASSET_REPAIR ||--o{ ASSET_REPAIR_CONSUMED_ITEM : "stock_items"
```

## Overview

ERPNext core Asset Repair record. Tracks corrective maintenance events, repair costs, and spare parts consumed. Maps to **IMM-09** in AssetCore workflow.

## Fields

| Fieldname | Type | Label | Required | Options/Link |
|-----------|------|-------|----------|-------------|
| `asset` | `Link` | Asset | ✅ | [[Asset]] |
| `company` | `Link` | Company |  | [[Company]] |
| `naming_series` | `Select` | Series | ✅ | ACC-ASR-.YYYY.- |
| `failure_date` | `Datetime` | Failure Date | ✅ |  |
| `repair_status` | `Select` | Repair Status |  | Pending
Completed
Cancelled |
| `completion_date` | `Datetime` | Completion Date |  |  |
| `cost_center` | `Link` | Cost Center |  | [[Cost Center]] |
| `project` | `Link` | Project |  | [[Project]] |
| `purchase_invoice` | `Link` | Purchase Invoice |  | [[Purchase Invoice]] |
| `capitalize_repair_cost` | `Check` | Capitalize Repair Cost |  |  |
| `stock_consumption` | `Check` | Stock Consumed During Repair |  |  |
| `repair_cost` | `Currency` | Repair Cost |  |  |
| `stock_items` | `Table` | Stock Items |  | [[Asset Repair Consumed Item]] |
| `total_repair_cost` | `Currency` | Total Repair Cost |  |  |
| `increase_in_asset_life` | `Int` | Increase In Asset Life(Months) |  |  |
| `description` | `Long Text` | Error Description |  |  |
| `actions_performed` | `Long Text` | Actions performed |  |  |
| `downtime` | `Data` | Downtime |  |  |
| `amended_from` | `Link` | Amended From |  | [[Asset Repair]] |

## Outgoing Links (Link Fields)

- `asset` → [[Asset]] *(required)*
- `company` → [[Company]]
- `cost_center` → [[Cost Center]]
- `project` → [[Project]]
- `purchase_invoice` → [[Purchase Invoice]]
- `amended_from` → [[Asset Repair]]

## Child Tables

- `stock_items` → [[Asset Repair Consumed Item]]

## Related DocTypes

- [[Asset]]
- [[Asset Repair]]
- [[Asset Repair Consumed Item]]
- [[Company]]
- [[Cost Center]]
- [[Project]]
- [[Purchase Invoice]]
