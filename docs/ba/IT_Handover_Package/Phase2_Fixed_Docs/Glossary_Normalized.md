> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# GLOSSARY NORMALIZED — ASSETCORE WAVE 1

**Phiên bản:** 2.0 (Phase 2 Consolidated)
**Owner:** SA Lead + BA Lead + Tech Lead
**Ngôn ngữ:** Tên code (tiếng Anh, snake_case), Label hiển thị (Tiếng Việt)
**Áp dụng:** Xây dựng Wave 1 + IT handover

---

## 1. DOCTYPES NORMALIZED — Master Data & Transactions

### 1.1 Master Data DocTypes

| Code Name | Vietnamese Label | DocType | Submittable | Naming Series | Module |
|-----------|------------------|---------|-------------|---------------|--------|
| AC Manufacturer | Nhà sản xuất thiết bị | AC Manufacturer | No | `MFR-.####` | Asset Registry |
| AC Location | Vị trí / Địa điểm | AC Location | No | tree-type | Asset Registry |
| AC Device Model | Mẫu thiết bị | AC Device Model | No | `model_code` | Asset Registry |
| AC Service Provider | Nhà cung cấp dịch vụ | AC Service Provider | No | `SP-.####` | Asset Registry |
| AC Contract | Hợp đồng | AC Contract | Yes | `CNT-.YYYY.-.####` | Asset Registry |

### 1.2 Asset Registry DocTypes

| Code Name | Vietnamese Label | DocType | Submittable | Naming Series | Module |
|-----------|------------------|---------|-------------|---------------|--------|
| AC Medical Asset | Tài sản y tế | AC Medical Asset | Yes | `MA-.YYYY.-.####` | Asset Registry |
| AC Asset Identifier | Mã định danh tài sản | AC Asset Identifier | No | `AID-.YYYY.-.######` | Asset Registry |
| AC Custodian Assignment | Gán người trông giữ | AC Custodian Assignment | Yes | `CUS-.YYYY.-.######` | Asset Registry |
| AC Asset Movement | Di chuyển tài sản | AC Asset Movement | Yes | `MOV-.YYYY.-.####` | Asset Registry |
| AC Stand-Down Record | Biên bản tạm ngừng | AC Stand-Down Record | Yes | `SD-.YYYY.-.####` | Asset Registry |
| AC Decommission Record | Biên bản giải nhiệm | AC Decommission Record | Yes | `DEC-.YYYY.-.####` | Asset Registry |
| AC Disposal Record | Biên bản thanh lý | AC Disposal Record | Yes | `DIS-.YYYY.-.####` | Asset Registry |

### 1.3 Document & QMS DocTypes

| Code Name | Vietnamese Label | DocType | Submittable | Naming Series | Module |
|-----------|------------------|---------|-------------|---------------|--------|
| AC Document Record | Hồ sơ tài liệu | AC Document Record | Yes | `DOC-.YYYY.-.######` | Document QMS |
| AC QMS Artifact | Tài liệu QMS | AC QMS Artifact | Yes | `QMS-<TIER>-.YYYY.-.####` | Document QMS |

### 1.4 Work Order Engine DocTypes

| Code Name | Vietnamese Label | DocType | Submittable | Naming Series | Module |
|-----------|------------------|---------|-------------|---------------|--------|
| AC Failure Report | Báo cáo sự cố | AC Failure Report | Yes | `FR-.YYYY.-.######` | Work Order |
| AC Work Order | Phiếu công việc | AC Work Order | Yes | `WO-.YYYY.-.######` | Work Order |
| AC Work Order Task | Công việc chi tiết | AC Work Order Task | No | — | Work Order |
| AC Work Order Spare Item | Phụ tùng sử dụng | AC Work Order Spare Item | No | — | Work Order |
| AC PM Plan | Kế hoạch bảo trì định kỳ | AC PM Plan | Yes | `PMP-.YYYY.-.####` | Maintenance |
| AC PM Task Detail | Chi tiết công việc PM | AC PM Task Detail | No | — | Maintenance |
| AC Calibration Plan | Kế hoạch hiệu chuẩn | AC Calibration Plan | Yes | `CPL-.YYYY.-.####` | Calibration |
| AC Calibration Record | Biên bản hiệu chuẩn | AC Calibration Record | Yes | `CAL-.YYYY.-.######` | Calibration |
| AC Calibration Measurement | Số đo hiệu chuẩn | AC Calibration Measurement | No | — | Calibration |
| AC IQ OQ PQ Record | Biên bản IQ/OQ/PQ | AC IQ OQ PQ Record | Yes | `IQPQ-.YYYY.-.####` | Commissioning |

### 1.5 Compliance & Quality DocTypes

| Code Name | Vietnamese Label | DocType | Submittable | Naming Series | Module |
|-----------|------------------|---------|-------------|---------------|--------|
| AC Failure Analysis | Phân tích nguyên nhân sự cố | AC Failure Analysis | No | — | Work Order |
| AC Nonconformity | Sự không phù hợp | AC Nonconformity | Yes | `NC-.YYYY.-.####` | Compliance |
| AC CAPA | Biện pháp khắc phục và phòng ngừa | AC CAPA | Yes | `CAPA-.YYYY.-.####` | Compliance |
| AC CAPA Action | Hành động CAPA | AC CAPA Action | No | — | Compliance |
| AC Compliance Case | Vụ việc tuân thủ | AC Compliance Case | Yes | `CMP-.YYYY.-.####` | Compliance |
| AC Risk Entry | Mục rủi ro | AC Risk Entry | Yes | `RSK-.YYYY.-.####` | Compliance |
| AC Change Control Request | Yêu cầu kiểm soát thay đổi | AC Change Control Request | Yes | `CCR-.YYYY.-.####` | Compliance |
| AC Audit | Kiểm toán nội bộ | AC Audit | Yes | `AUD-.YYYY.-.####` | Compliance |
| AC Management Review | Soát xét lãnh đạo | AC Management Review | Yes | `MRV-.YYYY.-.####` | Compliance |

### 1.6 Dashboard & Metrics DocTypes

| Code Name | Vietnamese Label | DocType | Submittable | Naming Series | Module |
|-----------|------------------|---------|-------------|---------------|--------|
| AC Metric Definition | Định nghĩa chỉ số | AC Metric Definition | No | `MET-W1-####` | Dashboard |
| AC Dashboard Snapshot | Ảnh chụp bảng điều khiển | AC Dashboard Snapshot | No | auto | Dashboard |
| AC Dashboard Widget | Thành phần bảng điều khiển | AC Dashboard Widget | No | — | Dashboard |
| AC Alert Rule | Quy tắc cảnh báo | AC Alert Rule | No | — | Dashboard |

### 1.7 Infrastructure DocTypes

| Code Name | Vietnamese Label | DocType | Submittable | Naming Series | Module |
|-----------|------------------|---------|-------------|---------------|--------|
| AC Lifecycle Event | Sự kiện vòng đời | AC Lifecycle Event | No | `LCE-.YYYY.-.########` | Asset Core |
| AC Event Type | Loại sự kiện | AC Event Type | No | — | Asset Core |
| AssetCore Settings | Cài đặt AssetCore | AssetCore Settings | No | — | Asset Core |

## 2. FIELD NAMING CONVENTION — Normalized

| Loại field | Pattern | Ví dụ Code | Ví dụ Label |
|----------|---------|-----------|-----------|
| Link to DocType | `<entity>` | `medical_asset` | Tài sản y tế |
| Date field | `*_date` | `pm_due_date` | Ngày đến hạn PM |
| Datetime field | `*_at` | `released_for_use_at` | Ngày giờ phát hành |
| Boolean flag | `is_*` / `has_*` | `is_critical` | Quan trọng |

## 3. ROLES NORMALIZED

| Role Code | Vietnamese Label | Permission Scope | Notes |
|-----------|------------------|-----------------|-------|
| AC Asset Manager | Trưởng/Phó VTTBYT | Toàn hệ thống asset + WO CM | Quyết định release, decommission |
| AC BME Engineer | Kỹ sư BME | Asset + WO + PM Plan + Cal Plan | Thiết kế WO, cấu hình PM/Cal |
| AC Technician | KTV thiết bị | WO assigned + asset trong scope | Thực hiện WO, nhập kết quả |
| AC QMS Officer | Chuyên viên QLCL | QMS Artifact, CAPA, NC, Document | Thực hiện QMS daily |
| AC QMS Lead | Trưởng QLCL | Toàn bộ QMS + approval Tier 1/2 | Duyệt, kết thúc CAPA, NC |
| AC Department Head | Trưởng khoa | Asset + WO (riêng khoa) | Duyệt movement, phê duyệt asset |
| AC Clinical User | Người dùng cuối khoa | Asset + Failure Report (khoa mình) | Submit FR, view asset |
| AC Finance Officer | Kế toán / KTTC | Asset financial fields + Cost tracking | Ghi nhận chi phí, depreciation |
| AC Legal Officer | Pháp chế / Pháp lý | Document Record (LEGAL) + Decommission | Xử lý hồ sơ pháp lý |
| AC Auditor | Kiểm toán nội bộ | Toàn bộ (read-only) + Lifecycle Event | Kiểm tra tuân thủ |
| AC Executive Viewer | BGĐ / Ban giám đốc | Dashboard + filtered detail | Xem KPI, override |
| AC System Admin | Quản trị hệ thống | Toàn hệ thống | Config + admin |

## 4. WORKFLOW STATES NORMALIZED

### AC Medical Asset Workflow
- `draft` → `installed` → `commissioned` → `released_for_use` → `stand_down` → `retired` → `disposed`

### AC Work Order Workflow
- `draft` → `planned` → `assigned` → `in_progress` → `paused` → `completed` → `validated` → `closed`

### AC Document Record Workflow
- `draft` → `review` → `approved` → `effective` → `under_review` → `revised` → `expired` / `obsolete`

### AC CAPA Workflow
- `draft` → `approved` → `in_progress` → `effectiveness_pending` → `closed` / `reopened`

## 5. LIFECYCLE EVENT CODES NORMALIZED

| LE Code | Event Type | Vietnamese Description | Trigger |
|---------|-----------|----------------------|---------|
| LE-01 | created | Tạo bản ghi | AC Medical Asset.insert |
| LE-03 | installed | Lắp đặt hoàn tất | MA state→installed |
| LE-04 | commissioned | Được kích hoạt | MA state→commissioned |
| LE-05 | document_effective | Tài liệu có hiệu lực | DocRecord state→effective |
| LE-06 | released_for_use | Phát hành sử dụng | MA state→released_for_use |
| LE-08 | calibrated | Hiệu chuẩn | CalRecord state→approved |
| LE-09 | failure_reported | Báo cáo sự cố | FR.on_submit |
| LE-14 | stand_down | Tạm ngừng vận hành | MA state→stand_down |
| LE-15 | decommissioned | Giải nhiệm | MA state→retired |
| LE-16 | disposed | Thanh lý | MA state→disposed |
| LE-41 | wo_planned | WO được dự kiến | WO state→planned |
| LE-42 | wo_assigned | WO được giao | WO state→assigned |
| LE-48 | wo_closed | WO đóng | WO state→closed |
| LE-49 | sla_breached | Vi phạm SLA | SLA monitor |

## 6. SELECT FIELD ENUMS

### AC Medical Asset — criticality
- A: Rất quan trọng
- B: Quan trọng
- C: Bình thường
- D: Thấp

### AC Work Order — priority
- Critical: Nguy hiểm (≤24h)
- High: Cao (≤3 ngày)
- Medium: Trung bình (≤7 ngày)
- Low: Thấp (≤30 ngày)

### AC Failure Report — severity
- Critical: Nguy hiểm → 30 min SLA
- High: Cao → 2h SLA
- Medium: Trung bình → 1 ngày SLA
- Low: Thấp → 3 ngày SLA

---

**Status:** Ready for Wave 1 IT handover
