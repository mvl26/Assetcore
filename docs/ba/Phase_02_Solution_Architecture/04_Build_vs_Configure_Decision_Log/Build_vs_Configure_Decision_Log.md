> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# BUILD vs CONFIGURE — DECISION LOG (ADR Index)

**Phiên bản:** 1.0
**Owner:** SA Lead
**Quy ước:** Mỗi quyết định kiến trúc lớn → 1 ADR mã `ADR-XXXX`.

---

## 1. ADR Template

```
ADR-XXXX: <Tiêu đề>
Status: Proposed / Approved / Superseded by ADR-YYYY / Deprecated
Date: yyyy-mm-dd
Context: bối cảnh, ràng buộc, vấn đề cần giải.
Decision: chọn gì.
Consequences: hệ quả tích cực, tiêu cực, rủi ro, action follow-up.
Alternatives considered: liệt kê + lý do bị loại.
```

---

## 2. ADR baseline Wave 1

### ADR-0001 — Lập custom app `assetcore` thay vì sửa core
- **Status:** Approved
- **Context:** Logic HTM/QMS sâu, không thể nhét vào core ERPNext mà không phá nâng cấp.
- **Decision:** Tạo custom app `assetcore` riêng; KHÔNG sửa schema core.
- **Consequences:** + Dễ nâng cấp; + Tách responsibility. − Cần bridging DocType giữa core và custom.
- **Alternatives:** Fork ERPNext (loại — chi phí maintain quá cao); hard-customize core (loại — vi phạm best practice).

### ADR-0002 — `AC Medical Asset` là entity riêng, không sửa ERPNext `Asset`
- **Status:** Approved
- **Context:** ERPNext Asset thiên về kế toán/khấu hao; không có khái niệm criticality/risk_class/state machine HTM.
- **Decision:** `AC Medical Asset` là entity HTM gốc; link 1-1 với ERPNext `Asset` cho tài chính.
- **Consequences:** + Tách trách nhiệm; − Cần đồng bộ 2 chiều một số field (location, custodian).
- **Alternatives:** Custom field trên ERPNext Asset (loại — lặp business logic); Replace Asset (loại — phá nâng cấp).

### ADR-0003 — Unified Work Order Engine (1 DocType cho mọi loại WO)
- **Status:** Approved
- **Context:** PM, CM, Cal, Inspection, Install có ~80% schema và operation giống nhau.
- **Decision:** 1 DocType `AC Work Order` với field `wo_type`; xây dựng workflow chung, branch theo type.
- **Consequences:** + Đơn giản hóa engine + KPI; − Một số field type-specific phải conditionally hiển thị (UI complexity).
- **Alternatives:** Tách 5 DocType (loại — lặp logic, KPI khó tổng hợp).

### ADR-0004 — Lifecycle Event Engine làm SoR cho audit
- **Status:** Approved
- **Context:** Cần audit trail nhất quán xuyên engine.
- **Decision:** DocType `AC Lifecycle Event` (immutable) lưu mọi event quan trọng; consumer pull từ outbox.
- **Consequences:** + Truy vết đầy đủ; − Cost storage tăng — bù bằng cold archive sau 5 năm.
- **Alternatives:** Chỉ dùng Frappe Version (loại — không đủ ngữ nghĩa nghiệp vụ).

### ADR-0005 — Document Engine tách 2 lớp (Document Record vs QMS Artifact)
- **Status:** Approved
- **Context:** Document Record có metadata như license/cal cert; QMS Artifact có 4-tier control khác hẳn.
- **Decision:** 2 DocType riêng, chia sẻ helper versioning.
- **Consequences:** + Workflow rõ; − Cần linkage chặt giữa Artifact và Record.

### ADR-0006 — E-signature dùng plugin Frappe + tích hợp HSM nội bộ tùy chọn
- **Status:** Approved
- **Context:** Một số quy trình QMS-critical bắt buộc e-signature có pháp lý.
- **Decision:** Pha 1 dùng Frappe e-signature + audit log; pha 2 tích hợp HSM nếu BV có CA nội bộ.
- **Consequences:** + Khởi chạy nhanh; − Cần upgrade pha 2 cho audit pháp lý cao cấp.

### ADR-0007 — Modular monolith thay vì micro-services
- **Status:** Approved
- **Context:** Frappe vận hành tốt nhất ở dạng monolith; team nhỏ.
- **Decision:** 1 site Frappe + custom app, micro-service chỉ cho IoT/predictive Wave 3.
- **Consequences:** + Đơn giản; − Khó scale nếu dữ liệu cực lớn.

### ADR-0008 — Mobile UI dạng PWA thay vì native app
- **Status:** Approved
- **Context:** Cần triển khai nhanh trên đa thiết bị.
- **Decision:** PWA dùng Frappe Wave/Frappe UI; tận dụng QR scan API browser.
- **Consequences:** + Phát hành nhanh; − Native feature giới hạn (NFC/RFID có thể cần native sau).

### ADR-0009 — Storage QMS-critical trên bucket WORM (immutable)
- **Status:** Approved
- **Context:** Audit yêu cầu bằng chứng không bị thay đổi.
- **Decision:** Triển khai MinIO (hoặc tương đương) với object lock cho QMS evidence.
- **Consequences:** + Audit-ready; − Tăng phức tạp ops.

### ADR-0010 — Lifecycle Event là phương tiện duy nhất để publish outbound
- **Status:** Approved
- **Context:** Tránh nhiều cơ chế webhook rời rạc.
- **Decision:** Outbound webhook chỉ subscribe vào Lifecycle Event.
- **Consequences:** + Một nguồn; − Trễ khi sự kiện chậm publish.

### ADR-0011 — Cron + RQ background workers cho scheduling (PM/Cal/Alert)
- **Status:** Approved
- **Decision:** Dùng Frappe Background Jobs (RQ) + cron daily.
- **Consequences:** + Tận dụng hạ tầng Frappe; − Cần monitor queue depth.

### ADR-0012 — Multi-site federation hoãn đến Wave 3
- **Status:** Approved
- **Context:** Wave 1/2 chỉ 1 site BV.
- **Decision:** Thiết kế DocType có `facility` để chuẩn bị; build federation sau.

### ADR-0013 — Naming convention prefix `AC ` cho mọi custom DocType
- **Status:** Approved
- **Context:** Tránh đụng tên với core ERPNext.
- **Decision:** Prefix `AC ` + Pascal case.

### ADR-0014 — Vendor portal là external user role với scoped permission
- **Status:** Approved
- **Decision:** Tận dụng Frappe Website User + Role `AC Vendor Service Engineer` + User Permission per asset/WO.

### ADR-0015 — KPI mọi widget bắt buộc drill-down
- **Status:** Approved
- **Decision:** UX guideline: không chấp nhận widget không drill-down (xem Phase 06).

---

## 3. Mục lục custom item Wave 1 (build list)

| Loại | Tên | Mức custom |
|------|-----|------------|
| App | `assetcore` | New |
| DocType custom | AC Medical Asset, AC Device Model, AC Asset Identifier, AC Location, AC Custodian Assignment, AC Manufacturer | New |
| DocType custom | AC Work Order, AC Work Order Task, AC Work Order Spare Item, AC PM Plan, AC Calibration Plan, AC Calibration Record, AC Failure Report | New |
| DocType custom | AC Document Record, AC QMS Artifact | New |
| DocType custom | AC Nonconformity, AC CAPA, AC CAPA Action, AC Compliance Case, AC Risk Entry, AC Change Control Request, AC Audit, AC Management Review | New |
| DocType custom | AC Lifecycle Event, AC Event Type | New |
| DocType custom | AC Metric Definition, AC Dashboard Snapshot, AC Dashboard Widget, AC Alert Rule | New |
| DocType custom | AC Stand-Down Record, AC Asset Movement, AC Decommission Record, AC Disposal Record, AC Contract, AC Service Provider, AC Spare Part | New (một phần Wave 2) |
| Custom field on ERPNext Asset | `assetcore_link` (link `AC Medical Asset`) | Custom |
| Custom field on ERPNext Item | `is_medical_device` | Custom |
| Custom field on ERPNext Stock Entry | `linked_work_order` | Custom |
| Custom hooks | on_submit Purchase Receipt → tạo MA draft | New hook |
| Workflow | Per submittable DocType | New |
| Server scripts | Validators (BR-001..) | New |
| Print formats | License Cert, Cal Cert, WO Report, Asset Profile | New |
| Reports | 25 KPI Wave 1 | New |
| API endpoints | OpenAPI v1 | New |

---

## 4. Cấu hình thuần (no-code) — KHÔNG custom

- Core: Item, Supplier, Purchase, Stock, Asset Category, Warehouse, User, Role, Print, Email Template, Notification.
- Tận dụng Frappe: Workflow Action, Auto Assignment, Notification Settings, Dashboard, Document Naming, Number Card, Module Onboarding.

---

## 5. Quy tắc thay đổi

- Mỗi ADR mới phải qua ARB (Phase_00/04).
- Override ADR phải tạo ADR mới với status "Supersedes".
- Không silent change.
