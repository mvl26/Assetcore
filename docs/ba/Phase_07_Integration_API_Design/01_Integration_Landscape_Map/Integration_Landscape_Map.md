> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# INTEGRATION LANDSCAPE MAP — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + IT Lead

---

## 1. Mục tiêu
Vẽ rõ AssetCore tương tác với hệ sinh thái BV; xác định Wave triển khai cho mỗi tích hợp; lock in/out scope và phương thức.

## 2. Bản đồ tổng

```
                        ┌──────────────────────┐
                        │     AssetCore        │
                        │  (Frappe + Custom)   │
                        └──┬─────────┬─────────┘
                           │         │
   ┌───────────────────────┘         └──────────────────────┐
   │ Wave 1                                                 │ Wave 2
   ▼                                                        ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐
│ ERPNext core  │  │ SSO IdP        │  │ Email/SMS    │  │ HIS / EMR       │
│ (Item, Asset, │  │ (Azure AD/     │  │ Gateway      │  │ (FHIR Device,   │
│  PR, Stock)   │  │  Keycloak)     │  │ (Frappe SMTP │  │  Location)      │
└───────────────┘  └────────────────┘  │  + Viettel)  │  └─────────────────┘
                                       └──────────────┘
   ┌───────────────────────────────────────────────────────────────┐
   │ Wave 2                                                        │
   ▼                                                               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ LIS / RIS / PACS│  │ ERP Finance     │  │ HR / Payroll    │  │ BHYT/BHXH       │
│ (FHIR ServiceReq│  │ (Asset disposal,│  │ (Department,    │  │ (báo cáo TBYT   │
│  Observation,   │  │  capitalization)│  │  Employee sync) │  │  nếu áp dụng)   │
│  Device usage)  │  │                 │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘

   ┌───────────────────────────────────────────────────────────────┐
   │ Wave 3                                                        │
   ▼                                                               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ IoT Telemetry   │  │ Predictive      │  │ Mobile Wave 3   │  │ Public Reporting│
│ (MQTT/HTTP from │  │ ML Service      │  │ federation      │  │ Bộ Y tế Vigil. │
│  Imaging/Lab)   │  │                 │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 3. Danh mục tích hợp

| ID | Hệ thống | Wave | Hướng | Phương thức | Phạm vi dữ liệu |
|----|---------|------|-------|-------------|-----------------|
| INT-01 | ERPNext core (cùng site) | 1 | Bidirectional | Frappe hooks/server scripts | Item, Asset, Purchase Receipt, Stock Entry, Department |
| INT-02 | SSO IdP | 1 | Inbound auth | OAuth2/OIDC | User identity |
| INT-03 | Email gateway | 1 | Outbound | SMTP | Notification |
| INT-04 | SMS gateway | 1.5 | Outbound | HTTPS API (Viettel/MobiFone) | Critical alerts |
| INT-05 | HIS/EMR | 2 | Inbound + Outbound | FHIR R4 (Device, Location, Practitioner) | Device registry sync, Location |
| INT-06 | LIS | 2 | Inbound + Outbound | FHIR (Device, ServiceRequest, Observation) | Lab device link |
| INT-07 | RIS/PACS | 2 | Outbound | FHIR (Device) + DICOM modality worklist (chỉ tham khảo) | Imaging device link |
| INT-08 | ERP Finance (nếu tách khỏi ERPNext) | 2 | Outbound | REST OpenAPI | Disposal accounting |
| INT-09 | HR system | 2 | Inbound | REST/CSV import | Employee, Department |
| INT-10 | BHYT / Bộ Y tế reporting portal | 2 | Outbound | Manual export → portal | Báo cáo định kỳ |
| INT-11 | Vendor portals (donor/manufacturer) | 2 | Inbound | REST/Webhook | Recall notifications |
| INT-12 | IoT broker | 3 | Inbound | MQTT/HTTPS | Telemetry, alarms |
| INT-13 | Predictive ML service | 3 | Outbound | REST | Training data; consume predictions |
| INT-14 | DR multi-site federation | 3 | Bidirectional | Webhook outbox | Federated lifecycle event |

## 4. Patterns

| Pattern | Áp dụng |
|---------|--------|
| **Outbox** | Mọi outbound webhook xuất phát từ Lifecycle Event |
| **Inbound webhook** | Nhận event từ vendor / HIS / IoT |
| **Bulk file** | Migration / báo cáo định kỳ |
| **Synchronous REST** | Query thông tin cụ thể (asset profile, license check) |
| **FHIR mapping** | HIS/LIS/PACS dữ liệu y tế |
| **Background job** | Cron-based reconciliation (MA ↔ ERPNext Asset) |

## 5. Trans-organization concerns

- Hợp đồng tích hợp với mỗi đối tác (DPA, SLA).
- Đầu mối liên hệ kỹ thuật tại mỗi đối tác.
- Khảo sát thực tế trước khi lock contract.
- Versioning API (v1, v2…).

## 6. Đo lường tích hợp

- Latency p95 inbound/outbound.
- Error rate.
- Outbox depth.
- Reconciliation lag (MA ↔ Asset).
- Signature verification fail rate.

## 7. Tiêu chí nghiệm thu Landscape
- Mọi tích hợp Wave 1 lock được phương thức + owner đối tác.
- Survey sheet cho mỗi tích hợp Wave 2 đã chuẩn bị.
- Sequence diagram cho integration Wave 1 đầy đủ.
