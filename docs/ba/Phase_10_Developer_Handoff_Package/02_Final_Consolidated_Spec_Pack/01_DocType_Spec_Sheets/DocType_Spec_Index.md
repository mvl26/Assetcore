> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DOCTYPE SPEC INDEX — WAVE 1

**Tham chiếu:** Phase_03 / 05_DocType_Specification_Sheet (chi tiết). File này là index nhanh.

---

## Master DocTypes
1. AC Manufacturer
2. AC Location (Tree)
3. AC Device Model
4. AC Service Provider
5. AC Spare Part (Wave 2 đầy đủ; Wave 1 placeholder)
6. AC Contract (cơ bản)

## Asset Registry
7. AC Medical Asset
8. AC Asset Identifier
9. AC Custodian Assignment

## Document & QMS
10. AC Document Record
11. AC QMS Artifact

## Lifecycle Event
12. AC Event Type
13. AC Lifecycle Event (immutable)

## Work Order Engine
14. AC Failure Report
15. AC Work Order
16. AC Work Order Task (child)
17. AC Work Order Spare Item (child)
18. AC PM Plan
19. AC Calibration Plan
20. AC Calibration Record
21. AC IQ-OQ-PQ Record
22. AC Software Update Record
23. AC Inspection Record
24. AC Installation Request

## Compliance / CAPA / Audit
25. AC Nonconformity
26. AC CAPA
27. AC CAPA Action (child)
28. AC Compliance Case
29. AC Risk Entry
30. AC Change Control Request
31. AC Audit
32. AC Management Review

## Movement / End-of-life
33. AC Asset Movement
34. AC Stand-Down Record
35. AC Decommission Record
36. AC Disposal Record

## Training
37. AC Training Session
38. AC Training Record (child)

## Metric / Dashboard / Alert
39. AC Metric Definition
40. AC Dashboard Snapshot
41. AC Dashboard Widget
42. AC Alert Rule

## Migration / Audit Support
43. AC Migration Batch
44. AC Migration Row (child)
45. AC Data Quality Issue

## Webhook / Integration
46. AC Webhook Subscription
47. AC Webhook Dead Letter

## Custom fields trên ERPNext core
- Item: `is_medical_device`, `risk_class`, `criticality`, `htm_device_model`
- Asset: `assetcore_link`, `htm_state_mirror`
- Supplier: `is_service_provider`
- Stock Entry: `linked_work_order`
- Purchase Receipt Item: `auto_create_assetcore_asset`
- Department: `is_clinical`
- Employee: `assetcore_role`

---

## Naming series (Phase_00/07 §2.3)
| DocType | Series |
|---------|--------|
| AC Medical Asset | `MA-.YYYY.-.####` |
| AC Work Order | `WO-.YYYY.-.######` |
| AC Lifecycle Event | `LCE-.YYYY.-.########` |
| AC Document Record | `DOC-.YYYY.-.######` |
| AC QMS Artifact | `QMS-<TIER>-.YYYY.-.####` |
| AC CAPA | `CAPA-.YYYY.-.####` |
| ... | (xem Phase_03/04) |

## Submittable status
| DocType | Submittable |
|---------|-------------|
| AC Medical Asset | Yes |
| AC Document Record | Yes |
| AC QMS Artifact | Yes |
| AC Work Order | Yes |
| AC PM Plan, Calibration Plan | Yes |
| AC Calibration Record | Yes |
| AC Failure Report | Yes |
| AC Lifecycle Event | No (immutable) |
| AC NC, CAPA, Compliance Case, Risk Entry, Change Control, Audit, Management Review | Yes |
| AC Asset Movement, Stand-Down, Decommission, Disposal | Yes |
| AC Custodian Assignment | Yes |
| AC Training Session | Yes |

## Dependency build order (theo Phase_09/02)
Master → Asset Registry → Document/QMS → Lifecycle Event → WO Engine → Compliance → Movement → Metric → Mobile → Integration.
