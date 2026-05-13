> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# TRANSACTIONAL RECORDS LIST — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead

---

## 1. Mục đích
Liệt kê đầy đủ DocType "transactional" (record vận hành) — phân biệt với master data — Wave 1 + 2.

## 2. Wave 1 (bắt buộc)

| DocType | Submittable | Naming | Mục đích |
|---------|-------------|--------|----------|
| AC Medical Asset | Yes | `MA-.YYYY.-.####` | State machine vòng đời |
| AC Asset Identifier | No | `AID-.YYYY.-.######` | Quản lý nhiều ID/asset |
| AC Custodian Assignment | Yes | `CUS-.YYYY.-.######` | Lịch sử custodian |
| AC Document Record | Yes | `DOC-.YYYY.-.######` | Hồ sơ pháp lý + tài liệu |
| AC QMS Artifact | Yes | `QMS-<TIER>-.YYYY.-.####` | Tài liệu QMS 4 tầng |
| AC PM Plan | Yes | `PMP-.YYYY.-.####` | Kế hoạch PM |
| AC Calibration Plan | Yes | `CPL-.YYYY.-.####` | Kế hoạch Cal |
| AC Calibration Record | Yes | `CAL-.YYYY.-.######` | Kết quả Cal |
| AC Failure Report | Yes | `FR-.YYYY.-.######` | Báo hỏng |
| AC Work Order | Yes | `WO-.YYYY.-.######` | WO PM/CM/Cal/Inspection/Install |
| AC Work Order Task | No (child) | – | Checklist trong WO |
| AC Work Order Spare Item | No (child) | – | Phụ tùng dùng trong WO |
| AC Lifecycle Event | No (immutable) | `LCE-.YYYY.-.########` | Audit + outbox |
| AC Nonconformity | Yes | `NC-.YYYY.-.####` | Phát hiện không phù hợp |
| AC CAPA | Yes | `CAPA-.YYYY.-.####` | Hành động corrective/preventive |
| AC CAPA Action | No (child) | – | Action chi tiết |
| AC Compliance Case | Yes | `CMP-.YYYY.-.####` | Vấn đề tuân thủ |
| AC Risk Entry | Yes | `RSK-.YYYY.-.####` | Mục rủi ro |
| AC Change Control Request | Yes | `CR-.YYYY.-.####` | Yêu cầu kiểm soát thay đổi |
| AC Audit | Yes | `AUD-.YYYY.-.####` | Internal/External audit |
| AC Management Review | Yes | `MR-.YYYY.-.####` | Soát xét lãnh đạo |
| AC Dashboard Snapshot | No | `SNP-.YYYY.-.######` | Snapshot KPI |
| AC Alert Rule | Yes | `AR-.YYYY.-.####` | Định nghĩa alert |
| AC Asset Movement | Yes | `MOV-.YYYY.-.####` | Điều chuyển |
| AC Stand-Down Record | Yes | `SD-.YYYY.-.####` | Tạm ngưng |
| AC Decommission Record | Yes | `DEC-.YYYY.-.####` | Giải nhiệm |
| AC Disposal Record | Yes | `DIS-.YYYY.-.####` | Thanh lý/donation |
| AC Training Session | Yes | `TS-.YYYY.-.####` | Đào tạo |
| AC Training Record | No (child) | – | Tham dự đào tạo |
| AC Software Update Record | Yes | `SU-.YYYY.-.####` | Cập nhật firmware/SW |
| AC Inspection Record | Yes | `INS-.YYYY.-.####` | Kiểm tra ngoài PM/Cal |
| AC Installation Request | Yes | `IR-.YYYY.-.####` | Yêu cầu lắp đặt |
| AC IQ-OQ-PQ Record | Yes | `IOPQ-.YYYY.-.####` | IQ/OQ/PQ |

## 3. Wave 2 bổ sung

| DocType | Submittable | Naming |
|---------|-------------|--------|
| AC Need Assessment | Yes | `NA-.YYYY.-.####` |
| AC Technical Specification | Yes | `TS-.YYYY.-.####` |
| AC Market Scan | Yes | `MS-.YYYY.-.####` |
| AC Vendor Evaluation | Yes | `VE-.YYYY.-.####` |
| AC Procurement Decision | Yes | `PD-.YYYY.-.####` |
| AC Recall Case (Compliance subtype) | Yes (parent CMP) | – |
| AC Spare Part | Yes | `SP-.YYYY.-.####` |
| AC Performance Alert | Yes | `PA-.YYYY.-.####` |
| AC Vigilance Report | Yes | `VR-.YYYY.-.####` |

## 4. Wave 3

| DocType | Submittable | Naming |
|---------|-------------|--------|
| AC Predictive Insight | No | `PI-.YYYY.-.######` |
| AC IoT Telemetry Snapshot | No | `IOT-.YYYY.-.########` |
| AC Federation Event | No | `FED-.YYYY.-.######` |

## 5. Quan hệ submitter / approver

(Tham chiếu Phase_01/10 Approval Authority Matrix.)

## 6. Audit class per record

| Loại | Audit class mặc định |
|------|----------------------|
| AC Medical Asset | critical |
| AC Document Record (LEGAL/CALCERT/QMS) | QMS-critical |
| AC Document Record (manual/training) | info |
| AC QMS Artifact | QMS-critical |
| AC Work Order | critical |
| AC CAPA / Compliance Case / Recall | QMS-critical |
| AC Lifecycle Event | bản thân là audit |
| AC Decommission/Disposal | QMS-critical |
| AC Movement / Stand-Down | critical |
| AC Risk / Change Control / Audit / Management Review | QMS-critical |

## 7. Tiêu chí nghiệm thu
- DocType list lock; mọi DocType mới ngoài list phải qua ARB.
- Naming series test pass (no collision).
- Submittable + Cancellable đúng theo nghiệp vụ.
