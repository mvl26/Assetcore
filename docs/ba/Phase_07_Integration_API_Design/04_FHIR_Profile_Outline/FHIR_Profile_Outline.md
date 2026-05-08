> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# FHIR PROFILE OUTLINE — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead
**Tham chiếu:** FHIR R4 (https://hl7.org/fhir/R4/)
**Lưu ý:** Profile chi tiết sẽ chỉ chốt sau khi survey HIS/LIS/PACS thực tế (Wave 2).

---

## 1. Resources được dùng

| FHIR Resource | Mục đích trong AssetCore |
|---------------|---------------------------|
| Device | Đại diện thiết bị y tế |
| DeviceDefinition | Catalog model (AC Device Model) |
| DeviceMetric | (Wave 3) telemetry metric |
| Location | Phân cấp Facility/Building/Department/Room |
| Practitioner | User vận hành/maintain |
| Organization | BV / Vendor |
| ServiceRequest | Yêu cầu Cal/Inspection từ HIS |
| Observation | (Wave 3) IoT readings |
| DocumentReference | Hồ sơ (license, manual, cert) |
| Provenance | Audit trail tương đương Lifecycle Event |

## 2. Profile: AssetCore Device (extends FHIR Device)

### 2.1 Constraints
- `identifier` slicing: must include
  - `slice "internal"` system=`http://assetcore/asset_code`
  - `slice "vendor_serial"` system=`http://assetcore/vendor_serial`
  - `slice "qr"` system=`http://assetcore/qr`
- `status` mapping: AC.state → FHIR Device.status
  - `released_for_use` → `active`
  - `stand_down` → `inactive`
  - `retired` → `inactive`
  - `disposed` → `entered-in-error` hoặc resource ẩn
- `type` reference DeviceDefinition (CR-DeviceDefinition).
- `safety` extension: criticality + risk_class.
- `note` field: chứa cảnh báo (nếu in Compliance Case Recall).

### 2.2 Extensions
- `acAssetCriticality` (A/B/C/D).
- `acRiskClass` (1/2a/2b/3).
- `acReplacementSignal` (OK/Watch/Replace).
- `acLastPMDate`, `acNextPMDue`.
- `acLastCalibrationDate`, `acNextCalibrationDue`.

### 2.3 Sample JSON

```json
{
  "resourceType": "Device",
  "id": "MA-2026-0001",
  "identifier": [
    {"system": "http://assetcore/asset_code", "value": "BV01-IMG-CT-000123"},
    {"system": "http://assetcore/vendor_serial", "value": "GE-12345"},
    {"system": "http://assetcore/qr", "value": "..."}
  ],
  "status": "active",
  "manufacturer": "GE Healthcare",
  "modelNumber": "Optima 660",
  "type": {"reference": "DeviceDefinition/DM-OPTIMA660"},
  "location": {"reference": "Location/BV01-B-CDH-P101"},
  "owner": {"reference": "Organization/BV01"},
  "safety": [
    {"coding": [{"system": "...", "code": "criticality:A"}]},
    {"coding": [{"system": "...", "code": "risk_class:2b"}]}
  ],
  "extension": [
    {"url": "http://assetcore/extension/replacementSignal", "valueCode": "OK"},
    {"url": "http://assetcore/extension/lastPMDate", "valueDate": "2026-04-10"},
    {"url": "http://assetcore/extension/nextPMDue", "valueDate": "2026-07-10"}
  ]
}
```

## 3. Profile: AssetCore Location

- `identifier` system=`http://assetcore/location_code`.
- `partOf` chain: Room → Department → Building → Facility.
- `physicalType` map sang AC location_type.

## 4. Profile: AssetCore DocumentReference

- `type` map từ document_type.
- `subject` reference Device.
- `date` = effective_date.
- `author` ref Practitioner / Organization.
- `content.attachment.url` URL file storage.
- `securityLabel` map từ confidentiality.
- `status` map từ Document state.

## 5. Profile: AssetCore Practitioner
- Identifier system: BV employee ID.
- Liên kết `qualification` để map role tới WHO HCP terminology nếu cần.

## 6. Profile: AssetCore Organization
- BV (chủ sở hữu) + Vendor (manufacturer/service provider/calibration lab).
- `type` map sang vai trò.

## 7. Profile: AssetCore ServiceRequest (Wave 2)
- HIS có thể tạo ServiceRequest yêu cầu Cal/Inspection.
- AssetCore consume → tạo WO type=Cal/Inspection.

## 8. Profile: AssetCore Provenance (Wave 2)
- Đại diện audit trail chuẩn FHIR.
- `target` ref Device/DocumentReference/WorkOrder (tùy AC LifecycleEvent.subject).
- `recorded` = LE.occurred_at.
- `agent` = actor.

## 9. Operation hỗ trợ
- `GET Device/{id}` – read.
- `GET Device?identifier=...` – search.
- `POST Device` – tạo (chỉ trong Wave 2 nếu HIS đẩy).
- `GET DocumentReference?subject=Device/{id}` – list.
- `POST ServiceRequest` (HIS đẩy) → trigger AssetCore tạo WO.
- `GET Provenance?target=...` – audit timeline.

## 10. AuthZ
- OAuth2 client_credentials với scope `assetcore.<resource>.<op>`.
- mTLS cho kết nối Bộ Y tế (nếu áp dụng).

## 11. Tiêu chí nghiệm thu FHIR Profile
- 4 profile core (Device, Location, DocumentReference, Practitioner) lock.
- Sample JSON validate qua FHIR validator.
- Gateway/transformer test pass với HIS/LIS/PACS sample.
- Wave 2 chốt operation `GET/SEARCH/POST` cụ thể sau survey.
