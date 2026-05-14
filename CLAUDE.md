# ASSETCORE — CLAUDE PROJECT CONTEXT

---

## 1. What This Is

AssetCore là hệ thống quản lý vòng đời thiết bị y tế (HTM) xây trên ERPNext (Frappe).

KHÔNG phải CMMS đơn lẻ → là operating architecture quản trị toàn lifecycle:
Needs → Procurement → Installation → Operation → Maintenance → Decommission
(WHO HTM lifecycle)

---

## 2. Tech Stack

- Python (Frappe / ERPNext v15)
- MariaDB
- Frappe UI
- REST / OpenAPI / FHIR
- Claude Code

---

## 3. Key Commands

Run system: `bench start`
Run tests: `bench --site \[site] run-tests`
Migrate: `bench migrate`
Install app: `bench --site \[site] install-app assetcore`

---

## 4. Project Structure (Logical)

/apps/assetcore/

- doctype/ → data model
- workflows/ → workflow config
- services/ → business logic
- api/ → integration
- events/ → lifecycle events
- reports/ → dashboard
- tests/ → unit tests
- docs/ → BA + architecture

---

## 5. Architecture Principles (CRITICAL)

- ERPNext Asset = registry only (NOT full HTM)
- Không modify core → chỉ extend
- Tách đúng: Item ≠ Model ≠ Asset ≠ Event ≠ Work Order
- Mọi nghiệp vụ phải có record (audit trail)
- Dashboard phải truy về source
- Workflow + SLA là bắt buộc

---

## 6. System Layers

User → Workflow → Business (IMM) → Data → Integration → Analytics → QMS

---

## 7. Module Structure

A. Planning: IMM-01→03
B. Deployment: IMM-04→06
C. Operation: IMM-07→12,15–17
D. End-of-Life: IMM-13→14

---

## 8. Wave 1 Scope

IMM-04 (Installation)
IMM-05 (Registration)
IMM-08 (PM)
IMM-09 (Repair)
IMM-11 (Calibration)
IMM-12 (Corrective)

---

## 9. Domain Model

Master:

- Device Model, Vendor, Location, Contract

Operational:

- Asset, Work Order, Maintenance Plan, Incident, Spare Part

Governance:

- QMS Document, CAPA, Risk, SLA

---

## 10. Core Concept — Lifecycle Event

Trục trung tâm hệ thống:

Event gồm:
asset, event_type, timestamp, actor, from→to status, root_record

Ví dụ:
installed, commissioned, pm_completed, failure_reported, repaired, retired

→ đảm bảo traceability

---

## 11. CMMS Core

Work Order = engine trung tâm:

- PM, CM, Calibration, Inspection

Không có action ngoài Work Order

---

## 12. QMS Integration (MANDATORY)

QC → PR → WI → BM → HS → KPI

Bắt buộc:

- Document control
- Change control
- CAPA
- Audit trail

---

## 13. Data & Compliance

- UDI / serial tracking
- Device nomenclature
- WHO HTM + NĐ98

Data phải:

- versioned
- auditable
- traceable

---

## 14. Integration

- FHIR (clinical)
- OpenAPI (system)

Connect:
HIS / EMR / LIS / RIS / PACS / Insurance

---

## 15. Code Style

- Type hints cho mọi function
- Bắt buộc docstring
- Naming theo domain (vd: `maintenance\_schedule`)
- Không viết logic trong controller → dùng service layer

---

## 16. Domain Terms

- Asset = thiết bị thực
- Model = cấu hình
- Work Order = lệnh công việc
- PM = bảo trì định kỳ
- CM = sửa chữa
- Calibration = hiệu chuẩn
- Lifecycle Event = sự kiện vòng đời

---

## 17. Workflow for New Features

1. Confirm requirement
2. Design theo lifecycle (NOT UI)
3. Viết test trước (TDD)
4. Implement
5. Run test
6. Tạo DocType + Workflow + API
7. Update CLAUDE.md nếu có pattern mới

---

## 18. Output Rules (MANDATORY)

Luôn include:

- Module (IMM-xx)
- Actor
- Input / Output
- Data model
- Workflow
- Audit trail
- KPI (nếu có)

---

## 19. Do NOT

- Hardcode logic
- Build UI trước workflow
- Bỏ audit trail
- Gộp domain sai
- Modify ERPNext core

---

## 20. Do ALWAYS

- Design theo lifecycle
- Sinh record cho mọi action
- Tách domain rõ
- Gắn workflow + SLA
- Đảm bảo traceability

---

## 21. Maintenance Rule

- Giữ file < 200 lines
- Chỉ giữ thông tin lâu dài
- Update khi có pattern mới
- Không chứa: API key / log / runtime data
