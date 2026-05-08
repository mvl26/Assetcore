> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# ERD LOGICAL — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + Data Architect
**Wave:** 1 + 2 baseline

---

## 1. Quy ước
- PK = Primary Key (Frappe `name`).
- FK = Foreign Key (Link).
- 1..N: 1 quan hệ với nhiều.
- N..M: nhiều-nhiều qua bảng trung gian (Frappe Child Table).
- Italic = ERPNext core; Bold = AssetCore custom.

## 2. Sơ đồ ERD tổng (Wave 1 + 2)

```
                          ┌─────────────────┐
                          │  AC Manufacturer│
                          └────────┬────────┘
                                   │ 1..N
                                   ▼
   ┌────────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
   │   Item (ERPNext)   │◄1─1┤  AC Device Model │1─►N│ AC Spare Part (BOM)│
   └────────────────────┘    └────────┬─────────┘    └─────────────────────┘
                                      │ 1..N
                                      ▼
                          ┌────────────────────────┐
                          │   AC Medical Asset     │1─►1  Asset (ERPNext)
                          └────────┬───────────────┘
                                   │ 1..N
              ┌───────────┬────────┼────────┬─────────────┐
              ▼           ▼        ▼        ▼             ▼
   ┌─────────────────┐ ┌─────────┐ ┌─────────┐ ┌──────────────────┐
   │AC Asset         │ │AC Custo-│ │AC Loca- │ │AC Document Record│
   │ Identifier (1..N)│ │ dian    │ │ tion    │ │ (1..N qua child) │
   └─────────────────┘ │ Assign- │ │ (link)  │ └──────────────────┘
                       │ ment    │ └─────────┘
                       │ (1..N)  │
                       └─────────┘

   ┌────────────────────┐                  ┌────────────────────┐
   │ AC Medical Asset   │1─►N AC PM Plan  N◄─1 AC Calibration   │
   │                    │                  │ Plan               │
   │                    │1─►N AC Work Order               (1..N)│
   │                    │1─►N AC Failure Report           (1..N)│
   │                    │1─►N AC Lifecycle Event          (1..N)│
   │                    │1─►N AC Asset Movement / Stand-Down /  │
   │                    │     Decommission / Disposal     (1..N)│
   └────────────────────┘

   AC Work Order
       ├──N──► AC Work Order Task (child)
       ├──N──► AC Work Order Spare Item (child) ───► Stock Entry (ERPNext)
       ├──1──► AC PM Plan / Calibration Plan / Failure Report
       ├──N..M──► AC CAPA (linked optional)
       └──1..N──► AC Lifecycle Event

   AC Document Record
       ├──N..M──► AC Medical Asset (qua child link table)
       ├──1..N──► AC Document Version (supersede chain)
       └──N..M──► AC Contract / Vendor

   AC QMS Artifact
       ├──N..M──► linked_processes (modules, doctype)
       ├──1..N──► AC Document Record (instances of biểu mẫu Tier 4)
       └──1..N──► AC Training Records

   AC Lifecycle Event
       ├──N..1──► AC Event Type
       ├──1..1──► subject (Dynamic Link to AC Medical Asset / WO / Document...)
       ├──1..1──► source (Dynamic Link)
       └──N..M──► evidence_refs (file)

   AC CAPA
       ├──N..1──► AC Nonconformity (source_nc 1..N qua child)
       ├──N..1──► AC Compliance Case
       ├──1..N──► AC CAPA Action (child)
       └──1..N──► AC Lifecycle Event

   AC Compliance Case
       ├──N..M──► AC Medical Asset
       ├──N..M──► AC Document Record
       ├──N..M──► AC Work Order
       ├──N..1──► AC CAPA (linked)
       └──1..N──► AC Lifecycle Event

   AC Metric Definition
       ├──1..N──► AC Dashboard Snapshot
       └──1..N──► AC Dashboard Widget
```

## 3. Bảng quan hệ chi tiết

| Quan hệ | Nguồn | Đích | Cardinality | Lý do |
|---------|-------|------|-------------|------|
| MA ← Asset | AC Medical Asset | Asset (ERPNext) | 1..1 | Đồng bộ tài chính |
| MA ← Device Model | AC Medical Asset | AC Device Model | N..1 | Catalog level |
| Device Model ← Item | AC Device Model | Item (ERPNext) | 1..1 | Item template |
| Device Model ← Manufacturer | AC Device Model | AC Manufacturer | N..1 | – |
| MA ← Identifier | AC Medical Asset | AC Asset Identifier | 1..N | Multi-id |
| MA ← Custodian | AC Medical Asset | AC Custodian Assignment | 1..N | Lịch sử |
| MA ← Location | AC Medical Asset | AC Location | N..1 (current) | Location hiện tại |
| MA ← Document | AC Medical Asset | AC Document Record | N..M | Doc shared/single |
| MA ← PM Plan | AC Medical Asset | AC PM Plan | 1..N | Multi-plan/asset |
| MA ← Cal Plan | AC Medical Asset | AC Calibration Plan | 1..N | – |
| WO ← MA | AC Work Order | AC Medical Asset | N..1 | – |
| WO ← PM Plan / Cal Plan / Failure Report | – | – | N..1 | Source |
| WO ← Spare Item | AC Work Order | AC Work Order Spare Item | 1..N (child) | – |
| WO Spare Item ← Stock Entry | – | Stock Entry (ERPNext) | 1..1 | Tiêu thụ |
| LE ← subject | AC Lifecycle Event | Dynamic Link | 1..1 | – |
| LE ← Event Type | AC Lifecycle Event | AC Event Type | N..1 | – |
| CAPA ← NC | AC CAPA | AC Nonconformity | 1..N (qua child) | – |
| CAPA ← Action | AC CAPA | AC CAPA Action | 1..N (child) | – |
| Compliance Case ← MA/Doc/WO | – | – | N..M | – |
| Recall (subtype) ← Affected Assets | AC Compliance Case | AC Medical Asset | N..M | Bulk |
| Risk Entry ← subject | AC Risk Entry | Dynamic Link | 1..1 | – |
| Change Control ← subject | AC Change Control Request | Dynamic Link | 1..N | – |
| QMS Artifact ← Document Record | AC QMS Artifact | AC Document Record | 1..N | Biểu mẫu instance |
| QMS Artifact ← Training | AC QMS Artifact | AC Training Record | 1..N | – |

## 4. Khóa nghiệp vụ (Business Keys)

| DocType | Business key |
|---------|--------------|
| AC Medical Asset | `asset_code` (unique) |
| AC Device Model | `model_code` (unique) |
| AC Manufacturer | `name` (unique) |
| AC Document Record | `(document_type, document_no, version)` (unique) |
| AC QMS Artifact | `(tier, document_no, version)` (unique) |
| AC Lifecycle Event | `(correlation_id, event_type)` đối với event idempotent |
| AC Work Order | `name` series-based |
| AC CAPA | `capa_no` series-based |
| AC Compliance Case | `case_no` series-based |

## 5. Composite indexes (đề xuất)

| DocType | Index |
|---------|-------|
| AC Medical Asset | `(facility, department, state)`, `(criticality, state)` |
| AC Work Order | `(wo_type, state, sla_due_at)`, `(medical_asset, completed_at)` |
| AC Lifecycle Event | `(subject_doctype, subject_name, occurred_at)`, `(event_type, occurred_at)` |
| AC Document Record | `(linked_asset, document_type, expiry_date)`, `(state, expiry_date)` |
| AC CAPA | `(state, severity)`, `(owner_user, state)` |
| AC Compliance Case | `(case_type, state, severity)` |

## 6. Dynamic Link strategy

`AC Lifecycle Event.subject` và `source` là Dynamic Link → flexible nhưng phải:
- Validate target DocType nằm trong whitelist `AC Event Type.allowed_doctypes`.
- Index chéo `(subject_doctype, subject_name)` để truy timeline nhanh.

## 7. Soft delete vs Cancel

- AssetCore không dùng `delete` cho DocType lớn — dùng **Cancel** (Frappe submittable) hoặc state `obsolete`.
- Soft delete chỉ áp dụng cho master data tham chiếu (Manufacturer, Service Provider) khi không còn dùng.
- Lifecycle Event KHÔNG bao giờ xóa.

## 8. Quan hệ với ERPNext core (mapping ngắn)

| AC | ERPNext core | Hướng |
|----|--------------|-------|
| AC Medical Asset | Asset | 1..1 link |
| AC Device Model.item_template | Item | 1..1 |
| Purchase Receipt | (trigger tạo MA draft) | 1..N |
| AC Work Order Spare Item.stock_entry | Stock Entry | 1..1 |
| AC Procurement Decision | Purchase Order | 1..N (Wave 2) |

(Chi tiết tại `07_Mapping_ERPNext_AssetCore`.)

## 9. Lưu ý
- ERD này là **logical** — không định ra cụ thể type/length field; chi tiết nằm trong `05_DocType_Specification_Sheet`.
- Mọi đổi cardinality sau baseline phải qua ARB (ADR mới).
