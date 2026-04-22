# IMM-00 — Foundation Module: AssetCore Core DocTypes

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-00 Foundation |
| Phiên bản | 4.0.0 |
| Ngày cập nhật | 2026-04-20 |
| Trạng thái | **Active** — v4 mở rộng: đưa Inventory (Kho vật tư + Phụ tùng + Tồn + Stock Movement) vào scope IMM-00 |
| Tác giả | AssetCore Team |

---

## 1. Mục đích

IMM-00 là **foundation layer tự chứa** của AssetCore — cung cấp toàn bộ DocType lõi, master data, dịch vụ cross-module, governance records cho 17 module IMM-xx kế tiếp.

**Nguyên tắc kiến trúc (bắt buộc):**

| Nguyên tắc | Nội dung |
|---|---|
| Dependency tối thiểu | AssetCore chỉ phụ thuộc **Frappe Framework v15**. Không cài ERPNext cũng chạy được. |
| Kế thừa schema | Các DocType core của AssetCore được **thiết kế dựa theo template schema của ERPNext** (Asset, Supplier, Location…) nhưng **tái tạo native** trong AssetCore với prefix `AC` — không link/extend DocType của ERPNext. |
| Prefix đặt tên | `AC` cho core DocType (AC Asset, AC Supplier…); `IMM` cho governance DocType (IMM Device Model, IMM SLA Policy, IMM Audit Trail, IMM CAPA Record). |
| Không sidecar | HTM metadata là field first-class trên `AC Asset` (không dùng DocType sidecar / Custom Fields). |

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│                  Frappe Framework v15                            │
│   User · Role · File · Comment · Version · Address · Contact     │
│   ToDo · Email Queue · Workflow Engine · ORM · Scheduler         │
└───────────────────────────┬──────────────────────────────────────┘
                            │  chỉ dependency duy nhất
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                      AssetCore App                               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              IMM-00 Foundation Layer                       │  │
│  │                                                            │  │
│  │  Core DocTypes (schema kế thừa ERPNext, tái tạo native):   │  │
│  │    • AC Asset           • AC Supplier                      │  │
│  │    • AC Location        • AC Department                    │  │
│  │    • AC Asset Category                                     │  │
│  │                                                            │  │
│  │  AssetCore-native DocTypes (không có ERPNext equivalent):  │  │
│  │    • IMM Device Model (+ child Spare Part)                 │  │
│  │    • IMM SLA Policy                                        │  │
│  │    • IMM Audit Trail (append-only)                         │  │
│  │    • IMM CAPA Record                                       │  │
│  │    • Asset Lifecycle Event (standalone, append-only)       │  │
│  │    • Incident Report                                       │  │
│  │                                                            │  │
│  │  Services: assetcore/services/imm00.py                     │  │
│  │  Utils:    assetcore/utils/{response,lifecycle,email}.py   │  │
│  │  Schedulers: 4 daily jobs                                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │  IMM-04  │ │  IMM-05  │ │  IMM-08  │ │  IMM-09  │   ...       │
│  │ Install  │ │ Register │ │   PM     │ │  Repair  │             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Core DocTypes — schema kế thừa ERPNext, tái tạo native (5)

| DocType | Naming | Template ERPNext | Mục đích |
|---|---|---|---|
| AC Asset | `AC-ASSET-.YYYY.-.#####` | Asset | Thiết bị y tế (HTM fields first-class: risk_class, lifecycle_status, UDI, GMDN, BYT, next_pm_date…) |
| AC Supplier | `AC-SUP-.YYYY.-.####` | Supplier | NCC, lab hiệu chuẩn, đơn vị bảo trì (+ ISO 17025, authorized_technicians) |
| AC Location | `AC-LOC-.YYYY.-.####` | Location | Khoa/phòng/kho (+ clinical_area_type, infection_control_level) |
| AC Department | `AC-DEPT-.####` | Department | Khoa/phòng sử dụng (đơn vị quản lý, không phải vị trí vật lý) |
| AC Asset Category | by category_name | Asset Category | Phân loại thiết bị (máy xét nghiệm, thiết bị chẩn đoán hình ảnh…) |

### 3.1.1 Inventory DocTypes — v4 mới (5) — xem [IMM-00_Inventory_Design.md](IMM-00_Inventory_Design.md)

| DocType | Naming | Mục đích |
|---|---|---|
| AC Warehouse | `AC-WH-.####` | Kho vật tư (khoa/tầng/phòng lưu trữ phụ tùng) |
| AC Spare Part | `AC-SP-.YYYY.-.####` | Master catalog phụ tùng chuẩn toàn hệ thống (+ min/max stock, đơn giá) |
| AC Spare Part Stock | by `warehouse::spare_part` | Tồn kho thực tế (một dòng cho mỗi cặp kho × phụ tùng) |
| AC Stock Movement | `AC-SM-.YYYY.-.#####` | Phiếu nhập / xuất / chuyển / điều chỉnh kho (có audit trail) |
| AC Stock Movement Item | — (child) | Chi tiết vật tư trong phiếu Stock Movement |

### 3.2 AssetCore-native DocTypes (6)

| DocType | Naming | Mục đích |
|---|---|---|
| IMM Device Model | `IMM-MDL-.YYYY.-.####` | Catalog model/phiên bản thiết bị (master template cho AC Asset) |
| IMM SLA Policy | by policy_name | Ma trận SLA P1–P4 × risk class |
| IMM Audit Trail | `IMM-AUD-.YYYY.-.#######` | Log bất biến SHA-256, cross-module |
| IMM CAPA Record | `CAPA-.YYYY.-.#####` | Corrective/Preventive actions (ISO 13485:8.5) |
| Asset Lifecycle Event | `ALE-.YYYY.-.#######` | Sự kiện vòng đời chuẩn hoá: commissioned, pm_completed, repair_opened, decommissioned… |
| Incident Report | `IR-.YYYY.-.####` | Sự cố thiết bị → trigger CM/CAPA |

### 3.3 Child DocTypes (3)

| Child DocType | Parent | Mục đích |
|---|---|---|
| IMM Device Spare Part | IMM Device Model | BOM — phụ tùng đề xuất cho model (link tới AC Spare Part) |
| AC Authorized Technician | AC Supplier | KTV ủy quyền của NCC |
| AC Stock Movement Item | AC Stock Movement | Chi tiết từng phụ tùng trong phiếu nhập/xuất |

**Tổng: 18 DocTypes** (5 core + 6 governance + 5 inventory + 3 child — có 1 inventory là child: Stock Movement Item).

### 3.4 Scope defer sang giai đoạn kế tiếp

- `AC Purchase Request` (workflow mua phụ tùng khi tồn < min) — **Wave 2**
- `AC Asset Component` (linh kiện đang gắn trên thiết bị với SN riêng) — **Wave 2**

---

## 4. Service Functions

File: `assetcore/services/imm00.py`

| Function | Caller Modules | Mô tả |
|---|---|---|
| `log_audit_event()` | Tất cả IMM modules | Tạo IMM Audit Trail bất biến (SHA-256 chain) |
| `create_lifecycle_event()` | IMM-04, 09, 11, 12, 13 | Tạo Asset Lifecycle Event chuẩn hoá (replace inline creator cũ) |
| `transition_asset_status()` | IMM-09, 12, 13 | Đổi `AC Asset.lifecycle_status` + log event + suspend schedules nếu Decommissioned |
| `get_sla_policy()` | IMM-08, 09, 11 | Tra SLA theo priority × risk_class (fallback is_default) |
| `create_capa()` | IMM-09, 11, 12 | Tạo CAPA Record, gán responsible |
| `close_capa()` | IMM-12, QA Officer | Đóng CAPA (validate corrective + preventive) |
| `validate_asset_for_operations()` | IMM-08, 09, 11 | Gate: block nếu Out of Service / Decommissioned |
| `check_capa_overdue()` | Scheduler daily | Mark Overdue + email QA Officer |
| `check_vendor_contract_expiry()` | Scheduler daily | Cảnh báo HĐ NCC 90/60/30 ngày |
| `check_registration_expiry()` | Scheduler daily | Cảnh báo đăng ký BYT 90/60/30/7 ngày |

**Bỏ so với v2:** `sync_single_asset_profile()`, `sync_asset_profile_status()` — không còn cần vì HTM fields đã nằm trực tiếp trên `AC Asset`.

---

## 5. Utils dùng chung (mới)

File: `assetcore/utils/`

| Module | Export | Dùng ở |
|---|---|---|
| `utils/response.py` | `_ok(data)`, `_err(msg, code)` | Toàn bộ API endpoint |
| `utils/lifecycle.py` | `create_lifecycle_event()`, `transition_status()` | Tất cả service layer |
| `utils/email.py` | `get_role_emails(roles)`, `safe_sendmail(...)` | Scheduler jobs |
| `utils/pagination.py` | `paginate(query, page, page_size)` | List APIs |

---

## 6. Scheduler Jobs

| Job | Tần suất | Logic | Người nhận |
|---|---|---|---|
| `check_capa_overdue` | Daily | CAPA Open + due_date < today → Overdue | assigned_to + IMM QA Officer |
| `check_vendor_contract_expiry` | Daily | contract_end - today in {90,60,30} | IMM Department Head |
| `check_registration_expiry` | Daily | registration_expiry - today in {90,60,30,7} AND NOT Decommissioned | IMM Department Head |
| `rollup_asset_kpi` | Daily | Tính MTTR avg, PM compliance % (reports) | — |

**Bỏ so với v2:** `sync_asset_profile_status` (không còn profile để sync).

---

## 7. Roles & Permissions

| Role | Quyền hạn chính |
|---|---|
| IMM System Admin | Create/Write/Delete mọi DocType AssetCore |
| IMM Department Head | Read/Write AC Asset; nhận cảnh báo scheduler |
| IMM Operations Manager | Read/Write AC Asset, AC Supplier; Read SLA |
| IMM Workshop Lead | Read/Write IMM Device Model, AC Asset; Create CAPA |
| IMM Technician | Read AC Asset; Write PM/Cal dates (chỉ thiết bị được gán) |
| IMM Document Officer | Read all; không Create/Edit |
| IMM Storekeeper | Read/Write AC Supplier |
| IMM QA Officer | Read/Write/Submit CAPA; xem full Audit Trail |

Fixtures: `fixtures/imm_roles.json` (auto-seed qua `bench migrate`).

Permission Query (`permission.py`): IMM Technician chỉ thấy `AC Asset` nơi `responsible_technician = session.user`.

---

## 8. Business Rules nền tảng

| ID | Business Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-00-01 | Class I → Low; Class II → Medium; Class III → High/Critical | `IMMDeviceModel.validate()` | NĐ 98/2021 |
| BR-00-02 | `AC Asset.lifecycle_status` chuyển trạng thái chỉ qua `transition_asset_status()` | Service layer | Internal |
| BR-00-03 | Audit Trail + Lifecycle Event immutable (no Update/Delete perm) | Controller + perm | ISO 13485:7.5.9 |
| BR-00-04 | Decommissioned → suspend tất cả PM/Calibration Schedules | `transition_asset_status()` | WHO HTM |
| BR-00-05 | Out of Service / Decommissioned → block tạo Work Order | `validate_asset_for_operations()` | WHO HTM |
| BR-00-06 | AC Supplier `vendor_type = "Calibration Lab"` → warning nếu thiếu `iso_17025_cert` | `ACSupplier.validate()` | ISO/IEC 17025 |
| BR-00-07 | SLA `response_time_minutes < resolution_time_hours × 60` | `IMMSLAPolicy.validate()` | Internal |
| BR-00-08 | CAPA phải có `corrective_action + root_cause` trước `before_submit` | `IMMCAPARecord.before_submit()` | ISO 13485:8.5 |
| BR-00-09 | CAPA quá `due_date` → auto Overdue qua daily scheduler | `check_capa_overdue()` | Internal |
| BR-00-10 | Mọi thay đổi `lifecycle_status` phải sinh 1 Asset Lifecycle Event | `transition_asset_status()` | Audit trail |

**Bỏ:** BR-00-02 cũ (IMM Asset Profile 1:1) — không còn profile.

---

## 9. Quan hệ với module khác

```text
IMM-00 → IMM-04 (Installation)
  • create_lifecycle_event("commissioned")
  • validate_asset_for_operations() trước bàn giao
  • AC Asset: commissioning_date, commissioning_ref

IMM-00 → IMM-05 (Registration)
  • AC Asset: byt_reg_no, byt_reg_expiry
  • check_registration_expiry() cảnh báo

IMM-00 → IMM-08 (PM)
  • validate_asset_for_operations() gate
  • get_sla_policy() tra SLA
  • create_lifecycle_event("pm_completed")

IMM-00 → IMM-09 (Repair/CM)
  • Incident Report là nguồn tạo Repair Work Order
  • transition_asset_status(Active → Under Repair → Active)
  • create_capa() nếu severity >= Major

IMM-00 → IMM-11 (Calibration)
  • AC Supplier.iso_17025_cert validation
  • AC Asset: next_calibration_date

IMM-00 → IMM-12 (Corrective)
  • create_capa() từ incident
  • transition_asset_status(Active → Out of Service)
```

---

## 10. Roadmap triển khai

| Sprint | Hạng mục | Trạng thái |
|---|---|---|
| 0.1 | 13 DocType JSON + controller + fixtures | 🔜 |
| 0.2 | Services layer (imm00.py) + utils/ | 🔜 |
| 0.3 | Role fixtures + permission.py | 🔜 |
| 0.4 | Scheduler jobs + email templates | 🔜 |
| 0.5 | API layer (api/imm00.py) | 🔜 |
| 0.6 | Test suite (target 70% coverage) | 🔜 |
| 0.7 | FE shell (routing + auth guard + AC Asset form) | 🔜 |

**Break sạch với v2:** Code IMM-08/09 hiện tại đang phụ thuộc ERPNext `Asset`/`Asset Repair`/`Stock Entry` sẽ xoá và viết lại sau khi IMM-00 v3 hoàn tất.
