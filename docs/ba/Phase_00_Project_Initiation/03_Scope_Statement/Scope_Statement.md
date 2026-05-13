> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# SCOPE STATEMENT — ASSETCORE

**Phiên bản:** 1.0
**Ngày:** 2026-05-05
**Owner:** PMO + SA Lead

---

## 1. Mục đích
Khóa rõ in scope / out of scope / future scope theo 4 khối – 17 module IMM, để mọi thiết kế, ước lượng, ưu tiên đều bám 1 baseline duy nhất.

## 2. In Scope — 4 khối / 17 module IMM

### 2.1 Khối A — Planning & Procurement
| Mã | Tên module | In Scope (Wave) | Mô tả ranh giới |
|----|-----------|-----------------|------------------|
| IMM-01 | Đánh giá nhu cầu và dự toán | Wave 2 | Needs assessment, capital planning, feasibility |
| IMM-02 | Thông số kỹ thuật và phân tích thị trường | Wave 2 | Specification building, market scan |
| IMM-03 | Đánh giá NCC và quyết định mua sắm | Wave 2 | Vendor evaluation, decision matrix; tích hợp với Purchase Order ERPNext |

### 2.2 Khối B — Deployment & Implementation
| Mã | Tên module | In Scope (Wave) | Mô tả ranh giới |
|----|-----------|-----------------|------------------|
| IMM-04 | Lắp đặt, định danh, kiểm tra ban đầu | **Wave 1** | IQ/OQ/PQ, asset tagging (mã + QR/RFID), initial inspection |
| IMM-05 | Đăng ký, cấp phép và hồ sơ | **Wave 1** | Hồ sơ pháp lý, license, registration, document binding |
| IMM-06 | Đào tạo người dùng | Wave 2 | Training plan, attendance, competency, release-for-use |

### 2.3 Khối C — Operations & Maintenance
| Mã | Tên module | In Scope (Wave) | Mô tả ranh giới |
|----|-----------|-----------------|------------------|
| IMM-07 | Theo dõi hiệu suất | Wave 2 | Performance KPI, uptime, utilization |
| IMM-08 | Bảo trì định kỳ (PM) | **Wave 1** | PM Plan, scheduling, execution, validation |
| IMM-09 | Sửa chữa, phụ tùng, cập nhật phần mềm | **Wave 1** | Corrective maintenance, spare parts consumption, firmware/software update |
| IMM-10 | Hậu kiểm và tuân thủ | Wave 2 | Post-market surveillance, vigilance, adverse event |
| IMM-11 | Hiệu năng và hiệu chuẩn | **Wave 1** | Calibration plan, internal/external lab, certificate |
| IMM-12 | Bảo trì khắc phục (CM) | **Wave 1** | Failure → repair → close, downtime, root cause |
| IMM-15 | Theo dõi tồn kho phụ tùng | Wave 2 | Spare parts master, reorder, link Stock module ERPNext |
| IMM-16 | Theo dõi tuân thủ | Wave 2 | Compliance dashboard, expiring license, overdue PM/cal |
| IMM-17 | Phân tích dự đoán | Wave 3 | Predictive analytics, ML model on telemetry/work order history |

### 2.4 Khối D — End-of-Life Management
| Mã | Tên module | In Scope (Wave) | Mô tả ranh giới |
|----|-----------|-----------------|------------------|
| IMM-13 | Ngừng sử dụng và điều chuyển | Wave 2 | Stand-down, transfer between department/site |
| IMM-14 | Giải nhiệm thiết bị | Wave 2 | Decommissioning, disposal/donation, regulatory closeout |

## 3. In Scope — Engine trung tâm (cross-module)

| Engine | In Scope | Wave |
|--------|---------|------|
| Asset Registry Layer | Có | Wave 1 |
| Lifecycle Event Engine | Có (event Wave 1 trước, mở rộng dần) | Wave 1 → 3 |
| Unified Work Order Engine | Có (PM, CM, Calibration, Inspection trước; Recall, Retire sau) | Wave 1 → 2 |
| Document & QMS Engine | Có (Document Record + QMS Artifact 4 tầng) | Wave 1 |
| Compliance / CAPA / Audit Engine | Có (CAPA + Compliance case + Recall workflow) | Wave 1.5 → 2 |
| Metric / Dashboard Engine | Có (KPI Wave 1 trước, mở rộng theo module) | Wave 1 → 3 |

## 4. In Scope — Hạ tầng & môi trường

- Triển khai trên ERPNext v15 / Frappe.
- Custom app `assetcore`.
- Môi trường: DEV / UAT / STAGING / PROD + DR site.
- Hạ tầng on-premise (mặc định) — có thể hybrid cloud cho DR.
- Backup, log, audit theo NFR (xem Phase 02).

## 5. Out of Scope (Wave 1)

- Tích hợp sâu HIS/EMR/LIS/RIS/PACS — chỉ thiết kế contract OpenAPI/FHIR, build & UAT ở Wave 2+.
- Quản lý vật tư tiêu hao y tế (consumables) ngoài phụ tùng thiết bị.
- Tài sản không phải TBYT (CNTT, hành chính, xe…).
- IoT telemetry real-time stream — chỉ thiết kế chỗ tiếp nhận, build sau.
- Module dự đoán (IMM-17) — Wave 3.
- Tích hợp BHYT / báo cáo Bộ Y tế tự động — chỉ làm export thủ công ở Wave 1.

## 6. Future Scope (Wave 3+)

- Predictive Maintenance (IMM-17).
- Real-time monitoring qua IoT/MQTT.
- Multi-site federation cho hệ thống bệnh viện vệ tinh.
- AI-assisted root cause analysis trên dữ liệu CM.
- Public-facing patient safety reporting.

## 7. Quy ước Wave

| Wave | Module | Mục tiêu |
|------|--------|----------|
| **Wave 1** | IMM-04, 05, 08, 09, 11, 12 + 6 engine cốt lõi | Có hồ sơ sống cho asset + chu trình PM/CM/Cal/Install/License |
| **Wave 2** | IMM-01, 02, 03, 06, 07, 10, 13, 14, 15, 16 | Khép vòng đời 2 đầu (Procurement + EoL) + Compliance toàn diện |
| **Wave 3** | IMM-17, integration sâu, IoT | Tối ưu hóa, tích hợp & predictive |

## 8. Phụ thuộc trọng yếu

- Phụ thuộc **dữ liệu legacy** từ Excel/giấy → migration template (Phase 03).
- Phụ thuộc **kho hợp đồng và giấy phép** số hóa từ Phòng Pháp chế / VTTBYT.
- Phụ thuộc **ERPNext core** (Item, Asset, Supplier, Stock, Purchase) — không thay thế, chỉ mở rộng.
- Phụ thuộc **chính sách BV** về role, segregation of duty, quy chế thiết bị.

## 9. Ký nghiệm thu phạm vi

| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Sponsor |  |  |
| Trưởng VTTBYT |  |  |
| Trưởng QLCL |  |  |
| Trưởng CNTT |  |  |
| PM |  |  |
