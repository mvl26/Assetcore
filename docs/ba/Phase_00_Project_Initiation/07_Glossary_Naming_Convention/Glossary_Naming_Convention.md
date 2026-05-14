# GLOSSARY & NAMING CONVENTION — ASSETCORE (v3, Frappe-only)

> **Reconciled to v3 codebase — 2026-05-07.** Mọi quy ước cũ về `AC ` prefix thống nhất, ERPNext sync, custom field on Item/Asset đã không còn áp dụng. Xem `docs/ba/00_RECONCILIATION_v3.md` cho mapping đầy đủ.

**Phiên bản:** 3.0
**Owner:** Tech Lead + BA Lead
**Áp dụng:** AssetCore custom app (Frappe v15, **không** dùng ERPNext)
**Ngôn ngữ:** Tiếng Anh cho mã (DocType / field / role / state); tiếng Việt cho **action label** workflow & UI label.

---

## 1. Glossary nghiệp vụ

### 1.1 Khung HTM/IMMIS
| Thuật ngữ | Định nghĩa | Tham chiếu |
|---|---|---|
| HTM | Healthcare Technology Management | WHO |
| IMMIS | Inventory and Maintenance Management Information System | WHO HTM |
| IMM-XX | Mã 17 module IMM (đã ship 10 module: 00, 01, 02, 03, 04, 05, 08, 09, 11, 12) | AssetCore Blueprint |
| Lifecycle | Vòng đời thiết bị "cradle-to-grave" |  |
| Cradle-to-grave | Từ Needs → Procurement → Installation → Operation → Maintenance → Decommission |  |

### 1.2 Quản lý vận hành
| Thuật ngữ | Định nghĩa | DocType thực tế |
|---|---|---|
| Asset | Bản thể tài sản cụ thể | `AC Asset` |
| Device Model | Catalog model thiết bị | `IMM Device Model` |
| Supplier / Vendor | Nhà cung cấp | `AC Supplier` |
| Service Provider | Cung cấp dịch vụ bảo trì/hiệu chuẩn | `AC Supplier` (có phân loại) |
| Service Contract | Hợp đồng dịch vụ | `Service Contract` (+ `Service Contract Asset`) |
| Location | Phân cấp địa điểm | `AC Location` |
| Department | Khoa | `AC Department` |
| Custodian | Người trông giữ thiết bị | field `custodian_user` trên `AC Asset` |
| Owner Department | Khoa sở hữu | field `department` trên `AC Asset` |
| Criticality | Mức trọng yếu (A/B/C) | field trên `AC Asset` |

### 1.3 Bảo trì / Hiệu chuẩn / Sửa chữa
| Thuật ngữ | Định nghĩa | DocType thực tế |
|---|---|---|
| PM (Preventive Maintenance) | Bảo trì định kỳ | `PM Work Order` (instance), `PM Schedule` (kế hoạch) |
| CM (Corrective Maintenance) | Sửa chữa khắc phục | `Asset Repair` |
| Calibration | Hiệu chuẩn | `IMM Asset Calibration` (instance), `IMM Calibration Schedule` |
| Inspection | Kiểm tra IQ/OQ/PQ commissioning | `Asset Commissioning` + `Commissioning Checklist` |
| Incident / Failure Report | Báo cáo sự cố / hư hỏng | `Incident Report` |
| Spare Part | Phụ tùng thay thế | `AC Spare Part` (master), `AC Spare Part Stock`, `Spare Parts Used` (per-WO) |
| BOM phụ tùng | BOM theo Device Model | `IMM Device Spare Part` (child) |
| MTTR / MTBF / Uptime / Downtime | KPI vận hành | tính trong `services/imm00.py` |

### 1.4 Tuân thủ / QMS / Audit
| Thuật ngữ | Định nghĩa | DocType thực tế |
|---|---|---|
| QMS | Quality Management System | (artifact track qua `Asset Document`; chưa tách Tier system) |
| QC / PR / WI / BM | 4 tầng tài liệu QMS | (track qua `Asset Document` + classification) |
| CAPA | Corrective Action and Preventive Action | `IMM CAPA Record` |
| RCA | Root Cause Analysis (5-Why) | `IMM RCA Record` (+ `IMM RCA Five Why Step`, `IMM RCA Related Incident`) |
| NC | Nonconformity | `Asset QA Non Conformance` |
| Recall / FSCA | Thu hồi / Field Safety Corrective Action | gộp vào incident workflow |
| Change Control | Kiểm soát thay đổi | `Firmware Change Request` (firmware) |
| Risk Register | Sổ rủi ro lock-in | `IMM Lock-in Risk Assessment` (+ `Lock-in Risk Item`) |
| Audit Trail | Vết kiểm toán | `IMM Audit Trail` (chuỗi SHA-256 immutable) |
| Lifecycle Event | Sự kiện vòng đời tài sản | `Asset Lifecycle Event` |
| Vendor Audit | Audit nhà cung cấp | `IMM Supplier Audit` (+ `Audit Finding`) |
| E-signature | Ký điện tử | re-auth workflow action (chưa hard-code, đang spec) |

### 1.5 Procurement / Planning
| Thuật ngữ | DocType thực tế |
|---|---|
| Needs Request | `IMM Needs Request` |
| Demand Forecast | `IMM Demand Forecast` |
| Procurement Plan | `IMM Procurement Plan` |
| Tech Spec | `IMM Tech Spec` |
| Market Benchmark | `IMM Market Benchmark` |
| AVL (Approved Vendor List) | `IMM AVL Entry` (+ `Vendor Cert`) |
| Vendor Evaluation | `IMM Vendor Evaluation` |
| Vendor Scorecard | `IMM Vendor Scorecard` |
| Procurement Decision | `IMM Procurement Decision` |
| Purchase Order | `AC Purchase` |
| Stock Movement (GR/Issue) | `AC Stock Movement` |

### 1.6 Frappe / Platform
| Thuật ngữ | Định nghĩa |
|---|---|
| DocType | Định nghĩa kiểu dữ liệu trong Frappe |
| Naming Series | Quy tắc đánh số tự động (field `naming_series` hoặc `autoname`) |
| Workflow | Máy trạng thái với JSON config |
| Hooks | `assetcore/hooks.py` — đăng ký event handler |
| Service layer | `assetcore/services/imm<NN>.py` — business logic |
| API layer | `assetcore/api/imm<NN>.py` — `@frappe.whitelist()` REST |
| Permission Query | `assetcore/permissions.py` — row-level filter |
| Role Profile / Module Profile | Bundle role; fixture `role_profile.json` |
| Workspace | Frappe v15 workspace UI; có `IMM Operations` |

---

## 2. Naming Convention

### 2.1 DocType — 3 prefix song song
Code thực tế dùng **3 nhóm prefix** (không phải 1 như BA gốc giả định):

| Loại | Prefix | Ví dụ DocType | Folder snake |
|---|---|---|---|
| **Foundation / master** không gắn IMM module cụ thể | `AC <Name>` | `AC Asset`, `AC Supplier`, `AC Location`, `AC Department`, `AC Spare Part`, `AC Purchase`, `AC Stock Movement`, `AC UOM`, `AC Warehouse` | `ac_asset`, `ac_supplier`, … |
| **Module-specific** chỉ tồn tại trong 1 IMM-XX | `IMM <Name>` | `IMM Needs Request`, `IMM Tech Spec`, `IMM AVL Entry`, `IMM Vendor Evaluation`, `IMM CAPA Record`, `IMM RCA Record`, `IMM Asset Calibration`, `IMM Audit Trail`, `IMM SLA Policy`, `IMM Device Model` | `imm_needs_request`, `imm_capa_record`, … |
| **Cross-module / shared** lifecycle | (không prefix) | `Asset Lifecycle Event`, `Asset Commissioning`, `Asset Document`, `Asset Repair`, `Asset Transfer`, `Incident Report`, `PM Work Order`, `PM Schedule`, `Service Contract`, `Vendor Cert`, `Audit Finding`, `Document Request` | `asset_lifecycle_event`, `incident_report`, … |

**Module Frappe**: tất cả nằm trong **1 module duy nhất** `AssetCore`.

### 2.2 Field naming
- **Snake_case** ngắn gọn, ổn định.
- FK Link: `<entity>` — `asset`, `device_model`, `supplier`, `location`.
- Date: `*_date` — `pm_due_date`, `expiry_date`.
- Datetime: `*_at` — `released_at`, `performed_at`.
- Boolean: `is_*` / `has_*` — `is_critical`, `has_calibration_required`.
- State: dùng field chuẩn Frappe `workflow_state` (KHÔNG đặt tên field `state` riêng).
- Reference: `ref_doctype` + `ref_name` (cho audit trail).

### 2.3 Naming Series (đầu mã)
| Module / DocType | Mã | Pattern |
|---|---|---|
| `IMM Needs Request` | `NR-` | `NR-.YY.-.MM.-.#####` |
| `IMM Procurement Plan` | `PP-` | `PP-.YY.-.#####` |
| `IMM Demand Forecast` | `DF-` | `DF-.YYYY.-.#####` |
| `IMM Tech Spec` | `TS-` | `TS-.YY.-.#####` |
| `IMM Market Benchmark` | `MB-` | `MB-.YY.-.#####` |
| `IMM Lock-in Risk Assessment` | `LR-` | `LR-.YY.-.#####` |
| `Firmware Change Request` | `FCR-` | `FCR-.YYYY.-.#####` |
| `IMM AVL Entry` | `AVL-` | `AVL-.YYYY.-.#####` |
| `IMM Vendor Evaluation` | `VE-` | `VE-.YY.-.#####` |
| `IMM Supplier Audit` | `SA-` | `SA-.YY.-.#####` |
| `IMM Procurement Decision` | `PD-` | `PD-.YY.-.#####` |
| `Asset Commissioning` | `ACC-` | `ACC-.YY.-.MM.-.#####` |
| `Asset Document` | `DOC-` | `format:DOC-{asset_ref}-{YYYY}-{####}` |
| `Document Request` | `DOCREQ-` | `format:DOCREQ-{YYYY}-{MM}-{####}` |
| `Expiry Alert Log` | `EAL-` | `format:EAL-{YYYY}-{MM}-{#####}` |
| `PM Work Order` | `PM-WO-` | `PM-WO-.YYYY.-.#####` |
| `PM Schedule` | `PMS-` | `format:PMS-{asset_ref}-{pm_type}-{####}` |
| `PM Checklist Template` | `PMCT-` | `format:PMCT-{asset_category}-{####}` |
| `Asset Repair` (CM) | `WO-CM-` | `WO-CM-.YYYY.-.#####` |
| `IMM Asset Calibration` | `CAL-` | `CAL-.YYYY.-.#####` |
| `IMM Calibration Schedule` | `CAL-SCH-` | `CAL-SCH-.YYYY.-.#####` |
| `Asset QA Non Conformance` | `NC-` | `format:NC-.YY.-.MM.-.#####` |
| `IMM Vendor Scorecard` | `VS-` | `format:VS-{period_year}-Q{period_q}-{supplier}` |
| `AC Warehouse` | `AC-WH-` | `format:AC-WH-{####}` |

> Các DocType khác (vd `Incident Report`, `IMM CAPA Record`, `IMM RCA Record`, `AC Asset`) đặt qua field `naming_series:` — pattern xem JSON từng DocType.

### 2.4 Workflow & State
- **Workflow name:**
  - `IMM-<NN> <Tên>` cho workflow gắn module → vd `IMM-08 PM Workflow`, `IMM-12 Incident Workflow`.
  - `AC <Tên>` cho workflow shared → vd `AC Asset Lifecycle`.
- **State name:** Title Case có space → `Pending Review`, `In Progress`, `Cannot Repair`, `Re Inspection`, `Pending–Device Busy`.
  - **KHÔNG** dùng snake_case như BA gốc đề xuất.
- **Action label:** **tiếng Việt có dấu** → `Bắt đầu sửa chữa`, `Phê duyệt`, `Yêu cầu RCA`, `Hoàn thành PM`, `Linh kiện đã nhận - bắt đầu sửa`.

### 2.5 Role
- **Internal:** prefix `IMM ` (có space) — `IMM System Admin`, `IMM HTM Engineer`, `IMM QA Officer`, `IMM Operations Manager`.
- **External:** `Vendor Engineer` (không prefix).
- Bundle qua **Role Profile** (`IMM - <Title>`) và **Module Profile** (`IMM - Standard|Admin|Vendor`).

### 2.6 Service / API path
- API endpoint: `/api/method/assetcore.api.imm<NN>.<action>` cho RPC; hoặc REST qua `@frappe.whitelist(methods=["POST"|"GET"])`.
- Service module: `assetcore.services.imm<NN>.<function>`.
- Helper utils: `assetcore.utils.lifecycle.log_audit_event`, `assetcore.utils.email.*`, `assetcore.utils.pagination.*`.

### 2.7 Audit / Lifecycle
- **Audit chain:** mọi thao tác có ý nghĩa pháp lý → `assetcore.utils.lifecycle.log_audit_event(asset, event_type, ...)` → ghi `IMM Audit Trail` với `hash_sha256` + `prev_hash`.
- **Lifecycle event:** sự kiện vòng đời (install, commission, decommission, …) → `create_lifecycle_event(asset, event_type, ...)` → ghi `Asset Lifecycle Event`.
- Verify: `verify_audit_chain(asset_name)`.

### 2.8 Asset Tag / QR
- **Asset Code:** field `asset_code` trên `AC Asset` (theo `naming_series` của DocType).
- **QR payload:** URL deep-link → mở record trên FE Vue `/asset/<name>`.
- **RFID:** field `rfid_tag` trên `AC Asset`.

### 2.9 File / Attachment
- Frappe `File` DocType. Tên file convention: `<doctype>_<name>_<purpose>_<yyyymmdd>.<ext>`.

---

## 3. Quy ước đa ngôn ngữ
- **Mã (DocType, field, role, workflow state):** tiếng Anh.
- **Workflow action label:** tiếng Việt có dấu.
- **UI label / form label:** tiếng Việt.
- **Print Format:** tiếng Việt mặc định, song ngữ khi cần audit.

---

## 4. Quy tắc thay đổi naming
- Đổi tên DocType / field → migration patch trong `assetcore/patches/v<X_Y>/` + cập nhật `patches.txt`.
- Field deprecate → giữ field cũ + flag `deprecated=1` 1 wave trước khi xóa.
- Đổi role name → cập nhật `fixtures/role_profile.json` + role profile + module profile + permission DocPerm.
- Mọi đổi tên log vào commit message + cập nhật `00_RECONCILIATION_v3.md`.

---

## 5. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Tech Lead |  | 2026-05-07 |
| BA Lead |  | 2026-05-07 |
| QMS Officer |  | 2026-05-07 |
