---
name: assetcore-htm-domain
description: |
  Provide HTM (Healthcare Technology Management) domain knowledge — WHO HTM lifecycle, NĐ98/2021 Vietnam medical device regulation, GMDN nomenclature, lifecycle stage to IMM module mapping, regulatory traceability. Use whenever the user asks about "WHO HTM", "NĐ98", "GMDN code", "lifecycle stage", "medical device classification", "compliance mapping", "lifecycle Needs→Decommission", "phân loại thiết bị y tế", "vòng đời thiết bị", "tuân thủ NĐ98", "regulatory requirement". Use this skill to ground design decisions in healthcare regulation.
---

# AssetCore HTM Domain Knowledge

Bridge engineers without healthcare background to the medical-device domain. AssetCore is **not** a generic CMMS — every architectural choice is grounded in WHO HTM lifecycle and Vietnamese NĐ98/2021 regulation. Use this skill to ground design decisions before they become tech debt.

## Purpose

Engineers frequently propose changes that look reasonable from a software perspective but break a regulatory invariant (e.g., "let's let users edit calibration dates" → violates NĐ98 traceability). This skill provides the domain context to:

- Map a proposed feature to the WHO HTM lifecycle stage it belongs to
- Identify regulatory requirements (NĐ98, ISO 13485, ISO 17025) that constrain a design
- Translate Vietnamese clinical/operational terms to engineering concepts
- Decide which IMM module owns a given business rule

## When to invoke

Trigger phrases:
- "What WHO HTM stage is this?"
- "Does NĐ98 require this?"
- "How is GMDN used here?"
- "Phân loại thiết bị Class B/C/D"
- "Vòng đời thiết bị y tế"
- "Tuân thủ NĐ98 cho calibration"
- "Compliance mapping for IMM-XX"
- "Regulatory requirement for incident reporting"

## WHO HTM Lifecycle — 6 stages

The single most important framework. Every IMM module belongs to exactly one lifecycle stage (except cross-cutting modules).

| # | WHO Stage | Description | IMM Modules |
|---|---|---|---|
| 1 | Needs Assessment | Identify clinical needs, capacity gaps, replacement triggers | IMM-01 |
| 2 | Procurement | Specify, tender, contract, purchase order | IMM-02, IMM-03 |
| 3 | Installation & Commissioning | Receive, install, IQ/OQ/PQ, clinical release | IMM-04, IMM-05 |
| 4 | Operation & Use | User training, day-to-day clinical operation | IMM-06 |
| 5 | Maintenance | PM, CM, calibration, incident, spare-parts management | IMM-08, IMM-09, IMM-11, IMM-12, IMM-15 |
| 6 | Decommission | Retire, dispose, transfer, asset write-off | IMM-13, IMM-14 |
| ✱ | Cross-cutting | Foundational data + governance — touch all stages | IMM-00 (Master), IMM-16 (Compliance/CAPA), IMM-17 (Reporting/KPI) |

**Design rule:** when a proposed feature doesn't fit any single stage, it likely belongs to IMM-00 (master data) or IMM-16 (governance) — not to whichever module brought it up.

## NĐ98/2021 — Vietnam Medical Device Regulation

Vietnam's primary medical-device regulation. AssetCore must enforce these in code.

### Core requirements that AssetCore implements

| NĐ98 Requirement | Where enforced in code |
|---|---|
| Đăng ký lưu hành (Registration) | IMM-05 — `Asset Registration` DocType requires registration number + expiry |
| Phân loại thiết bị (Class A/B/C/D) | `AC Asset.risk_class` field; classification drives PM frequency in IMM-08 |
| Truy xuất nguồn gốc (UDI/Serial) | `AC Asset.serial_no` is `unique: 1` and `reqd: 1`; lifecycle events SHA-256 chained |
| Hồ sơ thiết bị (Device Documentation) | IMM-05 doc expiry tracking — calibration cert, registration cert, manual |
| Calibration cho Class III/IV (B/C/D in NĐ98 terms) | IMM-11 mandatory calibration schedule auto-created on commissioning |
| Incident reporting | IMM-12 `Incident Report` — must be submittable within statutory window |
| CAPA on serious adverse event | IMM-16 CAPA auto-created from severity-Critical incidents |

### Asset risk classification (NĐ98 Class)

| NĐ98 Class | English | AssetCore field value | Operational impact |
|---|---|---|---|
| A | Low risk | `Low` | Standard PM cycle, no calibration |
| B | Medium risk | `Medium` | PM + recommended calibration |
| C | High risk | `High` | Mandatory calibration, photo evidence per BR-08-06 |
| D | Critical risk (life-support) | `Critical` | All of above + redundancy check + 24h CAPA SLA |

**Don't** invent your own class scheme. Map to A/B/C/D.

## GMDN — Global Medical Device Nomenclature

Standard taxonomy for medical devices (ISO 15225). AssetCore uses GMDN codes on `Device Model`, not on `AC Asset` (one model = one GMDN; many assets share a model).

- Reference data location: `docs/gmdn/`
- Field: `Device Model.gmdn_code` (Data field, optional but recommended for Class B+)
- Use case: regulatory reports must group assets by GMDN, not by internal `device_type`

## Compliance Mapping — IMM Business Rules → Regulation Source

When writing or auditing a business rule, cite the regulatory source. Examples from current code:

| Business Rule | Module | Regulation source |
|---|---|---|
| BR-04-01: IQ/OQ/PQ checklist must be 100% before clinical release | IMM-04 | NĐ98 Article 33 (Installation requirements) |
| BR-05-03: Doc expiry within 30 days → warning | IMM-05 | NĐ98 documentation continuity |
| BR-08-06: PM tasks on Class C/D need photo evidence | IMM-08 | ISO 13485 §7.5 (Production controls) |
| BR-11-02: Failed calibration auto-creates CM (IMM-09) | IMM-11 | ISO 17025 §7.10 + NĐ98 Article 56 |
| BR-12-04: Critical incident CAPA SLA = 24h | IMM-12 / IMM-16 | NĐ98 Article 67 (Adverse event reporting) |
| BR-16-09: Open Critical CAPA blocks new WO submission | IMM-16 | ISO 13485 §8.5.2 (CAPA) |

When you add a new BR, append it to the relevant `docs/imm-XX/02_business_rules.md` and cite the regulation. **A BR without a source is suspicious** — the team should challenge it.

## Domain glossary — Vietnamese ↔ English ↔ HTM term

| Vietnamese | English | HTM canonical term |
|---|---|---|
| Thiết bị | Asset | Equipment |
| Mẫu thiết bị | Device Model | Make/Model |
| Bảo trì định kỳ | PM | Preventive Maintenance |
| Sửa chữa | CM | Corrective Maintenance |
| Hiệu chuẩn | Calibration | Calibration |
| Kiểm định | Verification | Performance Verification |
| Sự cố | Incident | Adverse Event |
| Phân tích nguyên nhân gốc | RCA | Root Cause Analysis |
| Hành động khắc phục & phòng ngừa | CAPA | Corrective & Preventive Action |
| Sự kiện vòng đời | Lifecycle Event | Lifecycle Event |
| Mã định danh duy nhất | UDI | Unique Device Identifier |
| Lệnh công việc | Work Order (WO) | Work Order |
| Lắp đặt nghiệm thu | Commissioning | Installation Qualification (IQ) |
| Đào tạo người dùng | User Training | Operator Training |
| Cho phép sử dụng lâm sàng | Clinical Release | Release for Clinical Use |
| Loại bỏ / Thanh lý | Decommission / Disposal | Decommissioning |

When writing user-facing labels in DocType JSON, **use Vietnamese**. When naming code identifiers, **use English HTM canonical** (`pm_work_order`, not `bao_tri_dinh_ky`). See `../CONVENTIONS.md` §6.

## Module-to-stakeholder map

Every IMM module has a primary stakeholder (the role that owns the workflow). Designs that conflict with stakeholder ownership cause adoption failures.

| Module | Primary stakeholder (Vietnamese title) | English role |
|---|---|---|
| IMM-01 (Needs) | Trưởng khoa lâm sàng | Clinical Department Head |
| IMM-02/03 (Procurement) | Phòng Vật tư | Procurement Officer |
| IMM-04 (Installation) | Kỹ thuật viên Y sinh (BME) | Biomed Technician |
| IMM-05 (Registration) | Phòng QLTBYT | HTM Office |
| IMM-06 (Training) | BME + Trưởng khoa | BME + Dept. Head |
| IMM-08 (PM) | Tổ trưởng Xưởng | Workshop Lead |
| IMM-09 (CM/Repair) | Tổ trưởng Xưởng + BME | Workshop Lead + BME |
| IMM-11 (Calibration) | BME + bên hiệu chuẩn ngoài | BME + External Calibrator |
| IMM-12 (Incident) | Người dùng cuối + QA/QMS | End User + QA Officer |
| IMM-13/14 (Decommission) | Phòng QLTBYT + Kế toán | HTM Office + Accounting |
| IMM-15 (Spare) | Thủ kho | Storekeeper |
| IMM-16 (Compliance/CAPA) | QA/QMS Officer | Quality Officer |

## When in doubt — questions to ask

Before committing to a design, ask:

1. **Which WHO HTM stage** does this feature belong to? (If "more than one" → it's likely cross-cutting and belongs to IMM-00 / IMM-16.)
2. **Which NĐ98 article** mandates or constrains this? (If none → is the feature actually required, or is it gold-plating?)
3. **Which stakeholder role** owns this workflow step? (If unclear → talk to BA before coding.)
4. **What lifecycle event** should this produce? (If none → audit trail will have a gap.)
5. **What is the regulatory consequence** of this data being wrong? (Drives validation strictness.)

## How to verify a regulation claim

If unsure about a regulatory requirement:

1. Check `docs/architecture/Ho_so_kien_truc_IMMIS.md` — full architecture spec with regulatory citations
2. Check `docs/ba/` — BA phase docs with stakeholder interviews
3. Check `docs/WHO/` — WHO HTM Series source material
4. Check `docs/gmdn/` — GMDN nomenclature reference
5. Ask the BA team — never invent a regulation citation

## References

- `docs/WHO/` — WHO HTM Series (lifecycle, governance, KPIs)
- `docs/gmdn/` — GMDN nomenclature
- `docs/ba/` — Business Analyst phase docs (interviews, requirements)
- `docs/architecture/Ho_so_kien_truc_IMMIS.md` — full architecture spec
- `docs/imm-XX/02_business_rules.md` — per-module BR catalog with regulatory citations
- CLAUDE.md §13 (Data & Compliance) and §16 (Domain Terms)
- `../CONVENTIONS.md` — naming + layer rules
