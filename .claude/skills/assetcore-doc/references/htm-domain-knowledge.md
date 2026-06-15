# HTM Domain Knowledge — WHO HTM / NĐ98 / GMDN

Khi user hỏi về WHO HTM stage, NĐ98, GMDN, hoặc compliance requirement — dùng phần này để ground quyết định thiết kế trước khi code.

## WHO HTM Lifecycle — 6 giai đoạn

| # | WHO Stage | Description | IMM Modules |
|---|---|---|---|
| 1 | Needs Assessment | Nhu cầu lâm sàng, gap, thay thế | IMM-01 |
| 2 | Procurement | Spec, đấu thầu, PO | IMM-02, IMM-03 |
| 3 | Installation & Commissioning | Tiếp nhận, IQ/OQ/PQ, clinical release | IMM-04, IMM-05 |
| 4 | Operation & Use | Đào tạo người dùng | IMM-06 |
| 5 | Maintenance | PM, CM, calibration, incident, spare parts | IMM-08, IMM-09, IMM-11, IMM-12, IMM-15 |
| 6 | Decommission | Retire, dispose, transfer, write-off | IMM-13, IMM-14 |
| ✱ | Cross-cutting | Foundation + governance | IMM-00, IMM-16, IMM-17 |

**Design rule:** feature không fit stage nào → có thể thuộc IMM-00 (master data) hoặc IMM-16 (governance).

## NĐ98/2021 — Yêu cầu AssetCore thực thi

| NĐ98 Requirement | Trong code |
|---|---|
| Đăng ký lưu hành | IMM-05 `Asset Registration` — số đăng ký + hạn |
| Phân loại (Class A/B/C/D) | `AC Asset.risk_class` → drive PM frequency IMM-08 |
| Truy xuất nguồn gốc (UDI/Serial) | `AC Asset.serial_no` unique + SHA-256 audit chain |
| Hồ sơ thiết bị | IMM-05 doc expiry tracking |
| Calibration Class B/C/D | IMM-11 mandatory schedule auto-created on commissioning |
| Incident reporting | IMM-12 submittable within statutory window |
| CAPA on serious adverse event | IMM-16 CAPA auto-created from severity=Critical |

## Asset risk classification

| NĐ98 Class | AssetCore value | Operational impact |
|---|---|---|
| A (Low) | `Low` | PM tiêu chuẩn, không bắt buộc calibration |
| B (Medium) | `Medium` | PM + calibration recommended |
| C (High) | `High` | Mandatory calibration, photo evidence (BR-08-06) |
| D (Critical) | `Critical` | All of above + redundancy + 24h CAPA SLA |

## GMDN

Taxonomy chuẩn cho thiết bị y tế (ISO 15225). AssetCore dùng GMDN code trên `Device Model`, không phải `AC Asset`.
- Reference: `docs/gmdn/`
- Field: `Device Model.gmdn_code`

## Compliance Mapping — Business Rules → Regulation

| Business Rule | Module | Regulation |
|---|---|---|
| BR-04-01: IQ/OQ/PQ checklist 100% trước clinical release | IMM-04 | NĐ98 Article 33 |
| BR-05-03: Doc expiry <30 ngày → warning | IMM-05 | NĐ98 doc continuity |
| BR-08-06: PM Class C/D cần photo evidence | IMM-08 | ISO 13485 §7.5 |
| BR-11-02: Failed calibration → tạo CM | IMM-11 | ISO 17025 §7.10 + NĐ98 Article 56 |
| BR-12-04: Critical incident CAPA SLA = 24h | IMM-12/16 | NĐ98 Article 67 |
| BR-16-09: Open Critical CAPA blocks WO submit | IMM-16 | ISO 13485 §8.5.2 |

## Domain Glossary

| Vietnamese | English | HTM canonical |
|---|---|---|
| Thiết bị | Asset | Equipment |
| Bảo trì định kỳ | PM | Preventive Maintenance |
| Sửa chữa | CM | Corrective Maintenance |
| Hiệu chuẩn | Calibration | Calibration |
| Sự cố | Incident | Adverse Event |
| CAPA | CAPA | Corrective & Preventive Action |
| Sự kiện vòng đời | Lifecycle Event | Lifecycle Event |
| Lệnh công việc | Work Order (WO) | Work Order |

## 5 câu hỏi kiểm tra trước khi thiết kế

1. Feature này thuộc **WHO HTM stage** nào?
2. **NĐ98 article** nào mandate hoặc constrain điều này?
3. **Stakeholder** nào owns workflow step này?
4. **Lifecycle event** nào feature này sẽ produce?
5. **Regulatory consequence** nếu data sai là gì?
