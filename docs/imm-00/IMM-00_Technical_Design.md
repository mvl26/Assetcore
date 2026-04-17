# IMM-00 Foundation / Master Data — Technical Design

**Module:** IMM-00  
**Version:** 1.0.0  
**Date:** 2026-04-17  
**Author:** AssetCore Team  
**Status:** Approved for Implementation

---

## Table of Contents

1. [ERD — Entity Relationship Diagram](#1-erd--entity-relationship-diagram)
2. [Data Dictionary](#2-data-dictionary)
3. [Service Layer Design](#3-service-layer-design)
4. [Controller Design](#4-controller-design)
5. [hooks.py Additions](#5-hookspy-additions)
6. [Custom Fields JSON Fixture](#6-custom-fields-json-fixture)
7. [State Machine — CAPA Workflow](#7-state-machine--capa-workflow)
8. [Database Indexes](#8-database-indexes)
9. [Exception Catalog](#9-exception-catalog)

---

## 1. ERD — Entity Relationship Diagram

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                         ERPNext Core DocTypes                                  ║
║                                                                                  ║
║  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    ║
║  │    Asset     │   │   Supplier   │   │   Location   │   │  Department  │    ║
║  │  (tabAsset)  │   │(tabSupplier) │   │(tabLocation) │   │(tabDepartm.) │    ║
║  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘    ║
║         │                  │                   │                  │             ║
╚═════════╪══════════════════╪═══════════════════╪══════════════════╪═════════════╝
          │                  │                   │                  │
          │ 1:1              │ 1:1               │ 1:1              │
          │                  │                   │                  │
          ▼                  ▼                   ▼                  │
   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐         │
   │ IMM Asset    │   │ IMM Vendor   │   │ IMM Location │         │
   │  Profile     │   │  Profile     │   │    Ext       │         │
   │(IMM-ASP-...) │   │(IMM-VND-...) │   │(IMM-LOC-...) │         │
   └──────┬───────┘   └──────┬───────┘   └──────────────┘         │
          │ N:1              │ 1:N                                  │
          │                  │                                      │
          │            ┌─────┴──────────────┐                      │
          │            │  IMM Authorized    │                      │
          │            │   Technician       │                      │
          │            │  (child table)     │                      │
          │            └────────────────────┘                      │
          │                                                         │
          │ N:1                                                     │
          ▼                                                         │
   ┌──────────────┐                                                 │
   │  IMM Device  │◄────────────────────────────────────────────── │
   │    Model     │  N:1  (imm_department → Department)            │
   │(IMM-MDL-...) │                                                 │
   └──────┬───────┘                                                 │
          │ 1:N                                                      │
          │                                                          │
   ┌──────┴─────────────┐                                           │
   │  IMM Device        │                                           │
   │  Spare Part        │                                           │
   │  (child table)     │                                           │
   └────────────────────┘                                           │
                                                                    │
   ┌──────────────────────────────────────────────────────────────┐ │
   │                    IMM Audit Trail                           │ │
   │             (tabIMM Audit Trail — append-only)               │ │
   │  asset(Link→Asset) · source_doctype · source_name            │ │
   │  event_type · from_status → to_status · actor                │ │
   └──────────────────────────────────────────────────────────────┘ │
                                                                    │
   ┌──────────────────────────────────────────────────────────────┐ │
   │                    IMM CAPA Record                           │ │
   │             (tabIMM CAPA Record — Submittable)               │ │
   │  asset(Link→Asset) · severity · status · assigned_to(User)  │─┘
   │  source_doctype · source_name · due_date · closed_at         │
   └──────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────┐
   │                    IMM SLA Policy                            │
   │             (tabIMM SLA Policy — by policy_name)             │
   │  priority · risk_class · response_hours · resolution_hours   │
   │  escalation_hours · apply_to_modules (multi-select)          │
   └──────────────────────────────────────────────────────────────┘

Cardinality Summary:
  Asset                1 ──── 1   IMM Asset Profile
  Asset                1 ──── N   IMM Audit Trail
  Asset                1 ──── N   IMM CAPA Record
  IMM Device Model     1 ──── N   IMM Asset Profile (via imm_device_model on Asset)
  IMM Device Model     1 ──── N   IMM Device Spare Part (child)
  IMM Vendor Profile   1 ──── 1   Supplier
  IMM Vendor Profile   1 ──── N   IMM Authorized Technician (child)
  IMM Location Ext     1 ──── 1   Location
  IMM SLA Policy       1 ──── N   Work Orders / Events (lookup, not FK)
```

---

## 2. Data Dictionary

### 2.1 IMM Device Model (`tabIMM Device Model`)

Naming series: `IMM-MDL-.YYYY.-.####`

| Field | DB Column | Type | Length | Nullable | Default | Index | Description |
|---|---|---|---|---|---|---|---|
| name | name | varchar | 140 | NO | — | PK | Auto-generated: IMM-MDL-2026-0001 |
| model_name | model_name | varchar | 140 | NO | — | YES (unique w/ manufacturer) | Tên model thiết bị |
| manufacturer | manufacturer | varchar | 140 | NO | — | YES | Nhà sản xuất |
| device_category | device_category | varchar | 140 | YES | — | YES | Danh mục thiết bị (IEC/ECRI) |
| medical_class | medical_class | varchar | 20 | NO | Class I | NO | Class I / Class II / Class III |
| risk_class | risk_class | varchar | 20 | NO | Low | YES | Low / Medium / High / Critical |
| gmdn_code | gmdn_code | varchar | 20 | YES | — | YES | Mã GMDN quốc tế |
| byt_reg_no | byt_reg_no | varchar | 140 | YES | — | YES | Số QLSP/Số đăng ký BYT |
| byt_reg_expiry | byt_reg_expiry | date | — | YES | — | YES | Ngày hết hạn đăng ký BYT |
| country_of_origin | country_of_origin | varchar | 140 | YES | — | NO | Nước sản xuất |
| life_expectancy_years | life_expectancy_years | int | 11 | YES | 10 | NO | Tuổi thọ kỳ vọng (năm) |
| pm_interval_months | pm_interval_months | int | 11 | YES | 12 | NO | Chu kỳ bảo trì định kỳ (tháng) |
| calibration_interval_months | calibration_interval_months | int | 11 | YES | 12 | NO | Chu kỳ hiệu chuẩn (tháng) |
| requires_calibration | requires_calibration | tinyint | 1 | NO | 0 | NO | Cần hiệu chuẩn không? |
| default_vendor | default_vendor | varchar | 140 | YES | — | NO | Link → Supplier |
| default_sla_policy | default_sla_policy | varchar | 140 | YES | — | NO | Link → IMM SLA Policy |
| technical_spec_url | technical_spec_url | text | — | YES | — | NO | URL tài liệu kỹ thuật |
| notes | notes | text | — | YES | — | NO | Ghi chú nội bộ |
| is_active | is_active | tinyint | 1 | NO | 1 | YES | Còn sử dụng |
| creation | creation | datetime | — | NO | — | NO | Frappe standard |
| modified | modified | datetime | — | NO | — | NO | Frappe standard |
| owner | owner | varchar | 140 | NO | — | NO | Frappe standard |
| modified_by | modified_by | varchar | 140 | NO | — | NO | Frappe standard |

**Child table:** `IMM Device Spare Part` (see §2.8)

---

### 2.2 IMM Asset Profile (`tabIMM Asset Profile`)

Naming series: `IMM-ASP-.YYYY.-.####`  
Constraint: 1:1 with `tabAsset` — unique index on `asset`.

| Field | DB Column | Type | Length | Nullable | Default | Index | Description |
|---|---|---|---|---|---|---|---|
| name | name | varchar | 140 | NO | — | PK | Auto-generated |
| asset | asset | varchar | 140 | NO | — | UNIQUE | Link → Asset |
| device_model | device_model | varchar | 140 | YES | — | YES | Link → IMM Device Model |
| lifecycle_status | lifecycle_status | varchar | 30 | NO | Active | YES | Active / Under Repair / Calibrating / Out of Service / Decommissioned |
| calibration_status | calibration_status | varchar | 30 | YES | Not Required | NO | In Tolerance / Out of Tolerance / Not Required / Overdue |
| medical_class | medical_class | varchar | 20 | YES | — | NO | Class I / Class II / Class III (inherited from model) |
| risk_class | risk_class | varchar | 20 | YES | — | YES | Low / Medium / High / Critical |
| manufacturer_sn | manufacturer_sn | varchar | 140 | YES | — | YES | Số serial nhà sản xuất |
| udi_code | udi_code | varchar | 200 | YES | — | YES | Mã UDI (GS1/HIBC) |
| gmdn_code | gmdn_code | varchar | 20 | YES | — | NO | Mã GMDN |
| byt_reg_no | byt_reg_no | varchar | 140 | YES | — | NO | Số đăng ký BYT của lô thiết bị này |
| byt_reg_expiry | byt_reg_expiry | date | — | YES | — | YES | Ngày hết hạn đăng ký |
| installation_date | installation_date | date | — | YES | — | NO | Ngày lắp đặt |
| commissioning_date | commissioning_date | date | — | YES | — | NO | Ngày nghiệm thu |
| warranty_expiry_date | warranty_expiry_date | date | — | YES | — | YES | Ngày hết bảo hành |
| last_pm_date | last_pm_date | date | — | YES | — | NO | Ngày PM gần nhất (auto-sync) |
| next_pm_date | next_pm_date | date | — | YES | — | YES | Ngày PM tiếp theo |
| last_calibration_date | last_calibration_date | date | — | YES | — | NO | Ngày hiệu chuẩn gần nhất |
| next_calibration_date | next_calibration_date | date | — | YES | — | YES | Ngày hiệu chuẩn tiếp theo |
| responsible_tech | responsible_tech | varchar | 140 | YES | — | NO | Link → User |
| department | department | varchar | 140 | YES | — | YES | Link → Department |
| vendor | vendor | varchar | 140 | YES | — | NO | Link → Supplier |
| notes | notes | text | — | YES | — | NO | Ghi chú |
| creation | creation | datetime | — | NO | — | NO | Frappe standard |
| modified | modified | datetime | — | NO | — | NO | Frappe standard |

---

### 2.3 IMM Vendor Profile (`tabIMM Vendor Profile`)

Naming series: `IMM-VND-.YYYY.-.####`

| Field | DB Column | Type | Length | Nullable | Default | Index | Description |
|---|---|---|---|---|---|---|---|
| name | name | varchar | 140 | NO | — | PK | Auto-generated |
| supplier | supplier | varchar | 140 | NO | — | UNIQUE | Link → Supplier |
| company_name | company_name | varchar | 200 | NO | — | YES | Tên công ty đầy đủ |
| short_name | short_name | varchar | 50 | YES | — | NO | Tên viết tắt |
| vendor_type | vendor_type | varchar | 30 | YES | — | NO | OEM / Distributor / Service Only / Spare Parts |
| country | country | varchar | 140 | YES | — | NO | Quốc gia |
| website | website | varchar | 200 | YES | — | NO | Website |
| primary_contact_name | primary_contact_name | varchar | 140 | YES | — | NO | Tên người liên hệ chính |
| primary_contact_phone | primary_contact_phone | varchar | 30 | YES | — | NO | Điện thoại liên hệ |
| primary_contact_email | primary_contact_email | varchar | 200 | YES | — | NO | Email liên hệ |
| support_hotline | support_hotline | varchar | 30 | YES | — | NO | Hotline hỗ trợ kỹ thuật |
| contract_no | contract_no | varchar | 140 | YES | — | YES | Số hợp đồng bảo hành/dịch vụ |
| contract_start | contract_start | date | — | YES | — | NO | Ngày bắt đầu hợp đồng |
| contract_expiry | contract_expiry | date | — | YES | — | YES | Ngày hết hạn hợp đồng |
| service_scope | service_scope | text | — | YES | — | NO | Phạm vi dịch vụ theo hợp đồng |
| response_sla_hours | response_sla_hours | int | 11 | YES | 24 | NO | SLA phản hồi (giờ) |
| resolution_sla_hours | resolution_sla_hours | int | 11 | YES | 72 | NO | SLA xử lý (giờ) |
| byt_import_license | byt_import_license | varchar | 140 | YES | — | NO | Giấy phép nhập khẩu BYT |
| byt_license_expiry | byt_license_expiry | date | — | YES | — | YES | Ngày hết hạn giấy phép |
| rating | rating | decimal | 5,2 | YES | — | NO | Đánh giá hiệu suất nhà cung cấp (0–5) |
| notes | notes | text | — | YES | — | NO | Ghi chú |
| is_active | is_active | tinyint | 1 | NO | 1 | YES | Còn hợp đồng |
| creation | creation | datetime | — | NO | — | NO | Frappe standard |
| modified | modified | datetime | — | NO | — | NO | Frappe standard |

**Child table:** `IMM Authorized Technician` (see §2.7)

---

### 2.4 IMM Location Ext (`tabIMM Location Ext`)

Naming series: `IMM-LOC-.YYYY.-.####`

| Field | DB Column | Type | Length | Nullable | Default | Index | Description |
|---|---|---|---|---|---|---|---|
| name | name | varchar | 140 | NO | — | PK | Auto-generated |
| location | location | varchar | 140 | NO | — | UNIQUE | Link → Location |
| location_code | location_code | varchar | 30 | YES | — | YES | Mã phòng/khu vực nội bộ |
| location_type | location_type | varchar | 30 | YES | — | NO | ICU / OT / Ward / Lab / Radiology / Admin / Warehouse |
| building | building | varchar | 140 | YES | — | YES | Tòa nhà |
| floor | floor | varchar | 20 | YES | — | NO | Tầng |
| department | department | varchar | 140 | YES | — | YES | Link → Department phụ trách |
| responsible_user | responsible_user | varchar | 140 | YES | — | NO | Link → User |
| capacity_devices | capacity_devices | int | 11 | YES | — | NO | Số thiết bị tối đa |
| environment_requirements | environment_requirements | text | — | YES | — | NO | Yêu cầu môi trường (nhiệt độ, độ ẩm) |
| electrical_standard | electrical_standard | varchar | 50 | YES | — | NO | Tiêu chuẩn điện (IEC 60601, v.v.) |
| is_clinical | is_clinical | tinyint | 1 | NO | 1 | NO | Khu vực lâm sàng |
| notes | notes | text | — | YES | — | NO | Ghi chú |
| creation | creation | datetime | — | NO | — | NO | Frappe standard |
| modified | modified | datetime | — | NO | — | NO | Frappe standard |

---

### 2.5 IMM SLA Policy (`tabIMM SLA Policy`)

Naming: by `policy_name` field (human-readable key).

| Field | DB Column | Type | Length | Nullable | Default | Index | Description |
|---|---|---|---|---|---|---|---|
| name | name | varchar | 140 | NO | — | PK | = policy_name (slug) |
| policy_name | policy_name | varchar | 140 | NO | — | UNIQUE | Tên chính sách SLA |
| priority | priority | varchar | 20 | NO | — | YES | Critical / High / Medium / Low |
| risk_class | risk_class | varchar | 20 | YES | — | YES | Low / Medium / High / Critical |
| response_hours | response_hours | decimal | 10,2 | NO | 4 | NO | Thời gian phản hồi (giờ) |
| resolution_hours | resolution_hours | decimal | 10,2 | NO | 48 | NO | Thời gian xử lý (giờ) |
| escalation_hours | escalation_hours | decimal | 10,2 | YES | 72 | NO | Thời gian leo thang (giờ) |
| apply_to_modules | apply_to_modules | text | — | YES | — | NO | JSON array: ["IMM-08","IMM-09","IMM-11"] |
| business_hours_only | business_hours_only | tinyint | 1 | NO | 0 | NO | Chỉ tính giờ hành chính |
| notify_roles | notify_roles | text | — | YES | — | NO | JSON array: role names |
| escalate_to | escalate_to | varchar | 140 | YES | — | NO | Link → User nhận leo thang |
| description | description | text | — | YES | — | NO | Mô tả chính sách |
| is_active | is_active | tinyint | 1 | NO | 1 | YES | Đang áp dụng |
| creation | creation | datetime | — | NO | — | NO | Frappe standard |
| modified | modified | datetime | — | NO | — | NO | Frappe standard |

---

### 2.6 IMM Audit Trail (`tabIMM Audit Trail`)

Append-only. No Delete permission for any role. No Update after insert.

| Field | DB Column | Type | Length | Nullable | Default | Index | Description |
|---|---|---|---|---|---|---|---|
| name | name | varchar | 140 | NO | — | PK | Auto hash-based ID |
| asset | asset | varchar | 140 | NO | — | YES | Link → Asset |
| source_doctype | source_doctype | varchar | 140 | NO | — | YES | DocType gốc tạo sự kiện |
| source_name | source_name | varchar | 140 | NO | — | YES | Tên record nguồn |
| event_type | event_type | varchar | 50 | NO | — | YES | installed / commissioned / pm_completed / repaired / failure_reported / retired / status_changed / capa_opened / capa_closed |
| from_status | from_status | varchar | 50 | YES | — | NO | Trạng thái trước |
| to_status | to_status | varchar | 50 | YES | — | NO | Trạng thái sau |
| actor | actor | varchar | 140 | NO | — | YES | Link → User thực hiện |
| event_timestamp | event_timestamp | datetime | — | NO | — | YES | Thời điểm sự kiện (UTC) |
| remarks | remarks | text | — | YES | — | NO | Ghi chú bổ sung |
| integrity_hash | integrity_hash | varchar | 64 | NO | — | NO | SHA-256 hash của nội dung record |
| creation | creation | datetime | — | NO | — | YES | Frappe standard |
| modified | modified | datetime | — | NO | — | NO | Frappe standard |

---

### 2.7 IMM CAPA Record (`tabIMM CAPA Record`)

Naming series: `CAPA-.YYYY.-.#####`  
Submittable DocType.

| Field | DB Column | Type | Length | Nullable | Default | Index | Description |
|---|---|---|---|---|---|---|---|
| name | name | varchar | 140 | NO | — | PK | CAPA-2026-00001 |
| asset | asset | varchar | 140 | NO | — | YES | Link → Asset |
| source_doctype | source_doctype | varchar | 140 | NO | — | NO | DocType khởi tạo CAPA |
| source_name | source_name | varchar | 140 | NO | — | NO | Record nguồn |
| severity | severity | varchar | 20 | NO | Medium | YES | Critical / High / Medium / Low |
| status | status | varchar | 30 | NO | Draft | YES | Draft / Open / In Progress / Pending Verification / Closed / Cancelled |
| docstatus | docstatus | int | 1 | NO | 0 | NO | 0=Draft, 1=Submitted, 2=Cancelled |
| title | title | varchar | 200 | NO | — | NO | Tiêu đề CAPA |
| description | description | text | NO | — | — | NO | Mô tả vấn đề chi tiết |
| root_cause | root_cause | text | — | YES | — | NO | Phân tích nguyên nhân gốc rễ |
| corrective_action | corrective_action | text | — | YES | — | NO | Hành động khắc phục |
| preventive_action | preventive_action | text | — | YES | — | NO | Hành động phòng ngừa |
| assigned_to | assigned_to | varchar | 140 | YES | — | YES | Link → User phụ trách |
| due_date | due_date | date | — | YES | — | YES | Hạn hoàn thành |
| closed_at | closed_at | datetime | — | YES | — | NO | Thời điểm đóng CAPA |
| closed_by | closed_by | varchar | 140 | YES | — | NO | Link → User đóng CAPA |
| verification_result | verification_result | varchar | 30 | YES | — | NO | Effective / Not Effective / Partially Effective |
| verification_remarks | verification_remarks | text | — | YES | — | NO | Ghi chú xác minh |
| risk_reduction | risk_reduction | decimal | 5,2 | YES | — | NO | Mức giảm rủi ro sau xử lý (%) |
| is_overdue | is_overdue | tinyint | 1 | NO | 0 | YES | Cờ quá hạn (cập nhật bởi scheduler) |
| creation | creation | datetime | — | NO | — | NO | Frappe standard |
| modified | modified | datetime | — | NO | — | NO | Frappe standard |
| owner | owner | varchar | 140 | NO | — | NO | Frappe standard |

---

### 2.8 IMM Authorized Technician (child table of IMM Vendor Profile)

`tabIMM Authorized Technician`

| Field | DB Column | Type | Length | Nullable | Default | Index | Description |
|---|---|---|---|---|---|---|---|
| name | name | varchar | 140 | NO | — | PK | Row ID (auto) |
| parent | parent | varchar | 140 | NO | — | YES | FK → tabIMM Vendor Profile.name |
| parenttype | parenttype | varchar | 140 | NO | — | NO | "IMM Vendor Profile" |
| parentfield | parentfield | varchar | 140 | NO | — | NO | "authorized_technicians" |
| idx | idx | int | 11 | NO | — | NO | Row order |
| tech_name | tech_name | varchar | 140 | NO | — | NO | Tên kỹ thuật viên |
| tech_phone | tech_phone | varchar | 30 | YES | — | NO | Điện thoại |
| tech_email | tech_email | varchar | 200 | YES | — | NO | Email |
| certification_no | certification_no | varchar | 140 | YES | — | NO | Số chứng chỉ kỹ thuật |
| certification_expiry | certification_expiry | date | — | YES | — | NO | Ngày hết hạn chứng chỉ |
| specialization | specialization | varchar | 200 | YES | — | NO | Chuyên môn thiết bị |
| is_active | is_active | tinyint | 1 | NO | 1 | NO | Còn hoạt động |

---

### 2.9 IMM Device Spare Part (child table of IMM Device Model)

`tabIMM Device Spare Part`

| Field | DB Column | Type | Length | Nullable | Default | Index | Description |
|---|---|---|---|---|---|---|---|
| name | name | varchar | 140 | NO | — | PK | Row ID (auto) |
| parent | parent | varchar | 140 | NO | — | YES | FK → tabIMM Device Model.name |
| parenttype | parenttype | varchar | 140 | NO | — | NO | "IMM Device Model" |
| parentfield | parentfield | varchar | 140 | NO | — | NO | "spare_parts" |
| idx | idx | int | 11 | NO | — | NO | Row order |
| item_code | item_code | varchar | 140 | NO | — | NO | Link → Item |
| part_name | part_name | varchar | 200 | NO | — | NO | Tên phụ tùng |
| part_number | part_number | varchar | 140 | YES | — | NO | Mã phụ tùng gốc (OEM) |
| category | category | varchar | 50 | YES | — | NO | Consumable / Spare / Critical Spare |
| pm_replacement | pm_replacement | tinyint | 1 | NO | 0 | NO | Thay thế trong PM định kỳ |
| replacement_interval_months | replacement_interval_months | int | 11 | YES | — | NO | Chu kỳ thay thế (tháng) |
| unit_of_measure | unit_of_measure | varchar | 20 | YES | Nos | NO | Đơn vị |
| estimated_cost | estimated_cost | currency | — | YES | — | NO | Giá ước tính |
| notes | notes | text | — | YES | — | NO | Ghi chú |

---

## 3. Service Layer Design

File: `assetcore/services/imm00.py`

```python
# Copyright (c) 2026, AssetCore Team and contributors
# Service layer for IMM-00 Foundation / Master Data
"""
Service layer cho module IMM-00 (Foundation/Master Data).

Tất cả business logic của IMM-00 được tập trung tại đây.
Controller chỉ được phép gọi hàm từ module này — không chứa logic.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate, add_months, getdate, date_diff


# ─────────────────────────────────────────────────────────────────────────────
# IMM Device Model
# ─────────────────────────────────────────────────────────────────────────────

def create_device_model(data: dict[str, Any]) -> str:
    """Tạo IMM Device Model mới, kiểm tra trùng tên + nhà sản xuất trước khi lưu."""
    _assert_unique_model(data.get("model_name", ""), data.get("manufacturer", ""))
    doc = frappe.get_doc({"doctype": "IMM Device Model", **data})
    doc.insert(ignore_permissions=False)
    return doc.name


def update_device_model(model_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Cập nhật thông tin IMM Device Model và trả về record đã cập nhật."""
    doc = frappe.get_doc("IMM Device Model", model_name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


def _assert_unique_model(model_name: str, manufacturer: str) -> None:
    """Raise ValidationError nếu combination model_name + manufacturer đã tồn tại."""
    if frappe.db.exists(
        "IMM Device Model",
        {"model_name": model_name, "manufacturer": manufacturer}
    ):
        frappe.throw(
            _("Tên model đã tồn tại cho nhà sản xuất này"),
            frappe.ValidationError,
            title=_("Trùng lặp Model"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# IMM Asset Profile
# ─────────────────────────────────────────────────────────────────────────────

def create_asset_profile(asset_name: str, data: dict[str, Any]) -> str:
    """Tạo IMM Asset Profile 1:1 với Asset; ném lỗi ASP-001 nếu đã tồn tại."""
    if frappe.db.exists("IMM Asset Profile", {"asset": asset_name}):
        frappe.throw(
            _("Tài sản này đã có hồ sơ IMM"),
            frappe.ValidationError,
            title=_("Trùng hồ sơ IMM"),
        )
    doc = frappe.get_doc({
        "doctype": "IMM Asset Profile",
        "asset": asset_name,
        **data,
    })
    doc.insert(ignore_permissions=False)
    return doc.name


def update_asset_profile(asset_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Cập nhật IMM Asset Profile theo asset_name và trả về dict đã lưu."""
    profile_name = _get_profile_name_or_throw(asset_name)
    doc = frappe.get_doc("IMM Asset Profile", profile_name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


def sync_lifecycle_status(
    asset_name: str,
    new_status: str,
    actor: str,
    remarks: str = "",
) -> None:
    """
    Đồng bộ lifecycle_status giữa tabAsset và IMM Asset Profile,
    ghi Audit Trail tự động.
    """
    _valid_statuses = {
        "Active", "Under Repair", "Calibrating", "Out of Service", "Decommissioned"
    }
    if new_status not in _valid_statuses:
        frappe.throw(
            _("Trạng thái không hợp lệ: {0}").format(new_status),
            frappe.ValidationError,
        )

    # Read current status from Asset Profile
    profile_name = _get_profile_name_or_throw(asset_name)
    from_status = frappe.db.get_value("IMM Asset Profile", profile_name, "lifecycle_status")

    if from_status == new_status:
        return  # No change — idempotent

    # Update Asset Profile
    frappe.db.set_value("IMM Asset Profile", profile_name, "lifecycle_status", new_status)

    # Sync 16 custom fields on tabAsset
    frappe.db.set_value("Asset", asset_name, "imm_lifecycle_status", new_status)

    # Audit Trail
    log_audit_event(
        asset=asset_name,
        source_doctype="IMM Asset Profile",
        source_name=profile_name,
        event_type="status_changed",
        from_status=from_status,
        to_status=new_status,
        actor=actor,
        remarks=remarks,
    )


def _get_profile_name_or_throw(asset_name: str) -> str:
    """Trả về name của IMM Asset Profile theo asset; ném lỗi nếu chưa tồn tại."""
    profile_name = frappe.db.get_value("IMM Asset Profile", {"asset": asset_name}, "name")
    if not profile_name:
        frappe.throw(
            _("Không tìm thấy hồ sơ IMM cho tài sản: {0}").format(asset_name),
            frappe.DoesNotExistError,
        )
    return profile_name


# ─────────────────────────────────────────────────────────────────────────────
# IMM Audit Trail
# ─────────────────────────────────────────────────────────────────────────────

def log_audit_event(
    asset: str,
    source_doctype: str,
    source_name: str,
    event_type: str,
    from_status: str,
    to_status: str,
    actor: str,
    remarks: str = "",
) -> str:
    """
    Ghi một bản ghi Audit Trail bất biến; trả về name của bản ghi vừa tạo.

    Hàm này là entry point duy nhất để ghi Audit Trail —
    KHÔNG insert trực tiếp vào tabIMM Audit Trail từ nơi khác.
    """
    ts = now_datetime()
    payload = (
        f"{asset}|{source_doctype}|{source_name}|{event_type}"
        f"|{from_status}|{to_status}|{actor}|{ts}"
    )
    integrity_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    doc = frappe.get_doc({
        "doctype": "IMM Audit Trail",
        "asset": asset,
        "source_doctype": source_doctype,
        "source_name": source_name,
        "event_type": event_type,
        "from_status": from_status,
        "to_status": to_status,
        "actor": actor,
        "event_timestamp": ts,
        "remarks": remarks,
        "integrity_hash": integrity_hash,
    })
    doc.insert(ignore_permissions=True)  # append-only, skip perm check
    return doc.name


# ─────────────────────────────────────────────────────────────────────────────
# IMM CAPA Record
# ─────────────────────────────────────────────────────────────────────────────

def create_capa(
    asset: str,
    source_doctype: str,
    source_name: str,
    severity: str,
    description: str,
    title: str = "",
    assigned_to: str = "",
    due_date: str | None = None,
) -> str:
    """
    Tạo IMM CAPA Record mới ở trạng thái Draft và trả về name.

    Tự động ghi Audit Trail event_type='capa_opened'.
    """
    _valid_severities = {"Critical", "High", "Medium", "Low"}
    if severity not in _valid_severities:
        frappe.throw(
            _("Mức độ nghiêm trọng không hợp lệ: {0}").format(severity),
            frappe.ValidationError,
        )

    if not due_date:
        days_map = {"Critical": 7, "High": 14, "Medium": 30, "Low": 60}
        from frappe.utils import add_days
        due_date = add_days(nowdate(), days_map.get(severity, 30))

    doc = frappe.get_doc({
        "doctype": "IMM CAPA Record",
        "asset": asset,
        "source_doctype": source_doctype,
        "source_name": source_name,
        "severity": severity,
        "title": title or description[:100],
        "description": description,
        "status": "Open",
        "assigned_to": assigned_to or frappe.session.user,
        "due_date": due_date,
    })
    doc.insert(ignore_permissions=False)

    log_audit_event(
        asset=asset,
        source_doctype="IMM CAPA Record",
        source_name=doc.name,
        event_type="capa_opened",
        from_status="",
        to_status="Open",
        actor=frappe.session.user,
        remarks=f"Severity: {severity}",
    )
    return doc.name


def close_capa(
    capa_name: str,
    verification_result: str,
    remarks: str,
) -> None:
    """
    Đóng IMM CAPA Record: set status=Closed, ghi closed_at/closed_by, Submit doc, Audit Trail.
    """
    _valid_results = {"Effective", "Not Effective", "Partially Effective"}
    if verification_result not in _valid_results:
        frappe.throw(
            _("Kết quả xác minh không hợp lệ: {0}").format(verification_result),
            frappe.ValidationError,
        )

    doc = frappe.get_doc("IMM CAPA Record", capa_name)
    if doc.status in ("Closed", "Cancelled"):
        frappe.throw(
            _("CAPA đã được đóng hoặc huỷ, không thể thao tác thêm."),
            frappe.ValidationError,
        )

    from_status = doc.status
    doc.status = "Closed"
    doc.verification_result = verification_result
    doc.verification_remarks = remarks
    doc.closed_at = now_datetime()
    doc.closed_by = frappe.session.user
    doc.save()
    doc.submit()

    log_audit_event(
        asset=doc.asset,
        source_doctype="IMM CAPA Record",
        source_name=capa_name,
        event_type="capa_closed",
        from_status=from_status,
        to_status="Closed",
        actor=frappe.session.user,
        remarks=f"Result: {verification_result} | {remarks}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# IMM SLA Policy
# ─────────────────────────────────────────────────────────────────────────────

def get_sla_policy(priority: str, risk_class: str) -> dict[str, Any]:
    """
    Tra cứu SLA Policy phù hợp nhất theo priority và risk_class.

    Ưu tiên match cả hai; fallback về match priority only.
    Trả về {} nếu không tìm thấy.
    """
    # Try exact match first
    record = frappe.db.get_value(
        "IMM SLA Policy",
        {"priority": priority, "risk_class": risk_class, "is_active": 1},
        ["name", "response_hours", "resolution_hours", "escalation_hours",
         "business_hours_only", "escalate_to", "notify_roles"],
        as_dict=True,
    )
    if record:
        return record

    # Fallback: priority only
    record = frappe.db.get_value(
        "IMM SLA Policy",
        {"priority": priority, "risk_class": ["in", ["", None]], "is_active": 1},
        ["name", "response_hours", "resolution_hours", "escalation_hours",
         "business_hours_only", "escalate_to", "notify_roles"],
        as_dict=True,
    )
    return record or {}


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler Tasks
# ─────────────────────────────────────────────────────────────────────────────

def check_vendor_contract_expiry() -> None:
    """
    [Scheduler: daily] Gửi cảnh báo khi hợp đồng nhà cung cấp sắp hết hạn (30/7/1 ngày).
    """
    thresholds = [30, 7, 1]
    today = getdate(nowdate())

    records = frappe.db.get_all(
        "IMM Vendor Profile",
        filters={"is_active": 1, "contract_expiry": ["!=", ""]},
        fields=["name", "company_name", "contract_expiry", "primary_contact_email"],
    )

    for r in records:
        if not r.contract_expiry:
            continue
        days_left = date_diff(r.contract_expiry, today)
        if days_left in thresholds:
            _send_expiry_notification(
                subject=_("Hợp đồng nhà cung cấp sắp hết hạn: {0}").format(r.company_name),
                message=_("Hợp đồng với {0} sẽ hết hạn sau {1} ngày (ngày {2}).").format(
                    r.company_name, days_left, r.contract_expiry
                ),
                recipients=_get_role_emails("CMMS Admin"),
                reference_doctype="IMM Vendor Profile",
                reference_name=r.name,
            )


def check_byt_registration_expiry() -> None:
    """
    [Scheduler: daily] Cảnh báo khi đăng ký BYT của Device Model hoặc Asset Profile sắp hết hạn.
    """
    thresholds = [90, 30, 7]
    today = getdate(nowdate())

    # Check Device Model
    models = frappe.db.get_all(
        "IMM Device Model",
        filters={"byt_reg_expiry": ["!=", ""], "is_active": 1},
        fields=["name", "model_name", "manufacturer", "byt_reg_expiry"],
    )
    for m in models:
        if not m.byt_reg_expiry:
            continue
        days_left = date_diff(m.byt_reg_expiry, today)
        if days_left in thresholds:
            _send_expiry_notification(
                subject=_("Đăng ký BYT sắp hết hạn: {0} - {1}").format(
                    m.manufacturer, m.model_name
                ),
                message=_("Số đăng ký BYT của model {0} ({1}) hết hạn sau {2} ngày.").format(
                    m.model_name, m.manufacturer, days_left
                ),
                recipients=_get_role_emails("CMMS Admin"),
                reference_doctype="IMM Device Model",
                reference_name=m.name,
            )


def check_capa_overdue() -> None:
    """
    [Scheduler: daily] Đánh dấu is_overdue=1 và gửi thông báo leo thang cho CAPA quá hạn.
    """
    today = nowdate()

    overdue_capas = frappe.db.get_all(
        "IMM CAPA Record",
        filters={
            "status": ["in", ["Open", "In Progress"]],
            "due_date": ["<", today],
            "is_overdue": 0,
        },
        fields=["name", "asset", "title", "assigned_to", "due_date", "severity"],
    )

    for capa in overdue_capas:
        frappe.db.set_value("IMM CAPA Record", capa.name, "is_overdue", 1)
        _send_expiry_notification(
            subject=_("CAPA quá hạn: {0}").format(capa.name),
            message=_("CAPA [{0}] cho tài sản {1} đã quá hạn từ ngày {2}.").format(
                capa.name, capa.asset, capa.due_date
            ),
            recipients=[capa.assigned_to] + _get_role_emails("QA Risk Team"),
            reference_doctype="IMM CAPA Record",
            reference_name=capa.name,
        )


def sync_asset_profile_status() -> None:
    """
    [Scheduler: daily] Đồng bộ lifecycle_status từ IMM Asset Profile lên custom fields của Asset.

    Chạy để phục hồi nhất quán dữ liệu sau khi có migration hoặc import hàng loạt.
    """
    profiles = frappe.db.get_all(
        "IMM Asset Profile",
        fields=["name", "asset", "lifecycle_status", "calibration_status",
                "next_pm_date", "next_calibration_date", "last_pm_date",
                "last_calibration_date"],
    )
    for p in profiles:
        if not p.asset:
            continue
        frappe.db.set_value("Asset", p.asset, {
            "imm_lifecycle_status": p.lifecycle_status,
            "imm_calibration_status": p.calibration_status,
            "imm_next_pm_date": p.next_pm_date,
            "imm_last_pm_date": p.last_pm_date,
            "imm_next_calibration_date": p.next_calibration_date,
            "imm_last_calibration_date": p.last_calibration_date,
        }, update_modified=False)


# ─────────────────────────────────────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_role_emails(role: str) -> list[str]:
    """Trả về danh sách email của user thuộc role chỉ định."""
    users = frappe.db.get_all(
        "Has Role",
        filters={"role": role, "parenttype": "User"},
        fields=["parent"],
    )
    emails = []
    for u in users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email:
            emails.append(email)
    return emails


def _send_expiry_notification(
    subject: str,
    message: str,
    recipients: list[str],
    reference_doctype: str,
    reference_name: str,
) -> None:
    """Gửi thông báo email về sự kiện hết hạn; bỏ qua nếu recipients rỗng."""
    if not recipients:
        return
    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        reference_doctype=reference_doctype,
        reference_name=reference_name,
        now=True,
    )


def get_asset_kpi_summary(asset_name: str) -> dict[str, Any]:
    """
    Tổng hợp KPI MTD cho một tài sản: số WO, CAPA mở, ngày PM/calibration kế tiếp.
    """
    from frappe.utils import get_first_day, get_last_day

    mtd_start = get_first_day(nowdate())

    wo_count = frappe.db.count(
        "PM Work Order",
        filters={"asset": asset_name, "creation": [">=", mtd_start]},
    )
    open_capa = frappe.db.count(
        "IMM CAPA Record",
        filters={"asset": asset_name, "status": ["in", ["Open", "In Progress"]]},
    )

    profile = frappe.db.get_value(
        "IMM Asset Profile",
        {"asset": asset_name},
        ["lifecycle_status", "next_pm_date", "next_calibration_date",
         "last_pm_date", "last_calibration_date", "calibration_status"],
        as_dict=True,
    )

    return {
        "asset": asset_name,
        "lifecycle_status": profile.get("lifecycle_status") if profile else None,
        "calibration_status": profile.get("calibration_status") if profile else None,
        "mtd_work_orders": wo_count,
        "open_capa_count": open_capa,
        "next_pm_date": str(profile.get("next_pm_date") or "") if profile else None,
        "next_calibration_date": str(profile.get("next_calibration_date") or "") if profile else None,
        "last_pm_date": str(profile.get("last_pm_date") or "") if profile else None,
        "last_calibration_date": str(profile.get("last_calibration_date") or "") if profile else None,
    }
```

---

## 4. Controller Design

### 4.1 IMM Device Model Controller

File: `assetcore/assetcore/doctype/imm_device_model/imm_device_model.py`

```python
# Copyright (c) 2026, AssetCore Team and contributors
"""Controller cho IMM Device Model — chỉ gọi service layer."""
from __future__ import annotations

import frappe
from frappe.model.document import Document
from assetcore.services import imm00


class IMMDeviceModel(Document):
    """IMM Device Model — master data cấu hình thiết bị y tế."""

    def validate(self) -> None:
        """Validate: kiểm tra unique model_name + manufacturer (khi update)."""
        if not self.is_new():
            # On update, check for duplicates excluding self
            existing = frappe.db.get_value(
                "IMM Device Model",
                {
                    "model_name": self.model_name,
                    "manufacturer": self.manufacturer,
                    "name": ["!=", self.name],
                },
                "name",
            )
            if existing:
                frappe.throw(
                    frappe._("Tên model đã tồn tại cho nhà sản xuất này"),
                    frappe.ValidationError,
                )

    def before_save(self) -> None:
        """before_save: chuẩn hoá dữ liệu trước khi lưu."""
        if self.model_name:
            self.model_name = self.model_name.strip()
        if self.manufacturer:
            self.manufacturer = self.manufacturer.strip()
        if self.gmdn_code:
            self.gmdn_code = self.gmdn_code.strip().upper()
        # Ensure requires_calibration is consistent with interval
        if not self.requires_calibration:
            self.calibration_interval_months = None
```

---

### 4.2 IMM Asset Profile Controller

File: `assetcore/assetcore/doctype/imm_asset_profile/imm_asset_profile.py`

```python
# Copyright (c) 2026, AssetCore Team and contributors
"""Controller cho IMM Asset Profile — 1:1 với Asset."""
from __future__ import annotations

import frappe
from frappe.model.document import Document
from assetcore.services import imm00


class IMMAssetProfile(Document):
    """IMM Asset Profile — hồ sơ mở rộng HTM cho mỗi tài sản."""

    def validate(self) -> None:
        """Validate: enforce 1:1 constraint và consistency của dates."""
        if self.is_new():
            if frappe.db.exists("IMM Asset Profile", {"asset": self.asset, "name": ["!=", self.name]}):
                frappe.throw(
                    frappe._("Tài sản này đã có hồ sơ IMM"),
                    frappe.ValidationError,
                )
        self._validate_date_consistency()

    def on_update(self) -> None:
        """on_update: sync lifecycle_status lên custom fields của tabAsset."""
        if self.has_value_changed("lifecycle_status"):
            frappe.db.set_value(
                "Asset", self.asset, "imm_lifecycle_status", self.lifecycle_status,
                update_modified=False,
            )
        _sync_dates_to_asset(self)

    def after_insert(self) -> None:
        """after_insert: sync toàn bộ IMM custom fields lên tabAsset ngay sau tạo mới."""
        _sync_dates_to_asset(self)
        imm00.log_audit_event(
            asset=self.asset,
            source_doctype="IMM Asset Profile",
            source_name=self.name,
            event_type="profile_created",
            from_status="",
            to_status=self.lifecycle_status or "Active",
            actor=frappe.session.user,
            remarks="IMM Asset Profile khởi tạo",
        )

    def _validate_date_consistency(self) -> None:
        """Kiểm tra next_pm_date >= last_pm_date và tương tự cho calibration."""
        from frappe.utils import getdate
        if self.last_pm_date and self.next_pm_date:
            if getdate(self.next_pm_date) <= getdate(self.last_pm_date):
                frappe.throw(
                    frappe._("Ngày PM tiếp theo phải sau ngày PM gần nhất"),
                    frappe.ValidationError,
                )
        if self.last_calibration_date and self.next_calibration_date:
            if getdate(self.next_calibration_date) <= getdate(self.last_calibration_date):
                frappe.throw(
                    frappe._("Ngày hiệu chuẩn tiếp theo phải sau ngày hiệu chuẩn gần nhất"),
                    frappe.ValidationError,
                )


def _sync_dates_to_asset(profile: IMMAssetProfile) -> None:
    """Đồng bộ các trường ngày tháng từ Profile lên custom fields của tabAsset."""
    frappe.db.set_value("Asset", profile.asset, {
        "imm_lifecycle_status": profile.lifecycle_status,
        "imm_calibration_status": profile.calibration_status,
        "imm_last_pm_date": profile.last_pm_date,
        "imm_next_pm_date": profile.next_pm_date,
        "imm_last_calibration_date": profile.last_calibration_date,
        "imm_next_calibration_date": profile.next_calibration_date,
        "imm_device_model": profile.device_model,
        "imm_responsible_tech": profile.responsible_tech,
        "imm_department": profile.department,
    }, update_modified=False)
```

---

### 4.3 IMM CAPA Record Controller

File: `assetcore/assetcore/doctype/imm_capa_record/imm_capa_record.py`

```python
# Copyright (c) 2026, AssetCore Team and contributors
"""Controller cho IMM CAPA Record — Submittable."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from assetcore.services import imm00


class IMMCAPARecord(Document):
    """IMM CAPA Record — Corrective and Preventive Action (QMS-mandated)."""

    def validate(self) -> None:
        """Validate: required fields by status, due_date logic, severity."""
        _valid_severities = {"Critical", "High", "Medium", "Low"}
        if self.severity not in _valid_severities:
            frappe.throw(_("Mức độ nghiêm trọng không hợp lệ: {0}").format(self.severity))

        if not self.title:
            frappe.throw(_("Tiêu đề CAPA là bắt buộc"))

        if self.status in ("In Progress", "Pending Verification"):
            if not self.assigned_to:
                frappe.throw(_("CAPA ở trạng thái {0} cần có người phụ trách").format(self.status))
            if not self.root_cause:
                frappe.throw(_("Phân tích nguyên nhân gốc rễ là bắt buộc khi CAPA đang xử lý"))

    def before_submit(self) -> None:
        """before_submit: chỉ cho phép Submit khi status=Closed và có verification_result."""
        if self.status != "Closed":
            frappe.throw(
                _("Chỉ có thể nộp CAPA khi trạng thái là 'Closed'. Hiện tại: {0}").format(self.status),
                frappe.ValidationError,
            )
        if not self.verification_result:
            frappe.throw(_("Kết quả xác minh là bắt buộc trước khi nộp CAPA"))
        if not self.corrective_action:
            frappe.throw(_("Hành động khắc phục là bắt buộc trước khi nộp CAPA"))

    def on_submit(self) -> None:
        """on_submit: ghi Audit Trail capa_closed với verification_result."""
        imm00.log_audit_event(
            asset=self.asset,
            source_doctype="IMM CAPA Record",
            source_name=self.name,
            event_type="capa_closed",
            from_status="Closed",
            to_status="Submitted",
            actor=frappe.session.user,
            remarks=f"Verification: {self.verification_result}",
        )

    def on_cancel(self) -> None:
        """on_cancel: đặt status=Cancelled và ghi Audit Trail."""
        self.db_set("status", "Cancelled")
        imm00.log_audit_event(
            asset=self.asset,
            source_doctype="IMM CAPA Record",
            source_name=self.name,
            event_type="capa_cancelled",
            from_status=self.status,
            to_status="Cancelled",
            actor=frappe.session.user,
        )
```

---

### 4.4 IMM Audit Trail Controller

File: `assetcore/assetcore/doctype/imm_audit_trail/imm_audit_trail.py`

```python
# Copyright (c) 2026, AssetCore Team and contributors
"""Controller cho IMM Audit Trail — append-only, không cho phép update/delete."""
from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document


class IMMAuditTrail(Document):
    """
    IMM Audit Trail — bản ghi bất biến.

    - Không có on_update / before_save hook (không cho phép sửa).
    - Không có on_trash hook (Delete bị chặn ở permission level).
    - before_insert tính và xác minh integrity_hash.
    """

    def before_insert(self) -> None:
        """before_insert: tính integrity_hash nếu chưa có; verify nếu đã có."""
        payload = (
            f"{self.asset}|{self.source_doctype}|{self.source_name}"
            f"|{self.event_type}|{self.from_status}|{self.to_status}"
            f"|{self.actor}|{self.event_timestamp}"
        )
        expected_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if self.integrity_hash and self.integrity_hash != expected_hash:
            frappe.throw(
                _("Integrity hash không khớp — bản ghi Audit Trail bị giả mạo"),
                frappe.SecurityException,
            )
        self.integrity_hash = expected_hash
```

---

## 5. hooks.py Additions

Thêm vào `assetcore/hooks.py` (các phần liên quan IMM-00):

```python
# ──────────────────────────────────────────────
# Fixtures — IMM-00 additions
# ──────────────────────────────────────────────
fixtures = [
    # ... (existing fixtures) ...
    {"dt": "Custom Field", "filters": [["dt", "in", ["Asset"]]]},
    {"dt": "IMM Device Model"},
    {"dt": "IMM SLA Policy"},
    # Roles added by IMM-00
    {"dt": "Role", "filters": [["name", "in", [
        "HTM Technician",
        "Biomed Engineer",
        "Workshop Head",
        "QA Risk Team",
        "CMMS Admin",
    ]]]},
]

# ──────────────────────────────────────────────
# Document Events — IMM-00 hooks
# ──────────────────────────────────────────────
doc_events = {
    # ... (existing hooks) ...

    # Sync custom fields when Asset is saved
    "Asset": {
        "after_insert": "assetcore.services.imm00.on_asset_insert",
    },

    # Audit Trail — prevent any modification after insert
    "IMM Audit Trail": {
        "before_save": "assetcore.services.imm00.block_audit_trail_update",
    },

    # CAPA — sync overdue flag on save
    "IMM CAPA Record": {
        "before_save": "assetcore.services.imm00.mark_capa_overdue_flag",
    },

    # Asset Profile — sync to Asset on save
    "IMM Asset Profile": {
        "on_update": "assetcore.services.imm00.on_asset_profile_update",
        "after_insert": "assetcore.services.imm00.on_asset_profile_insert",
    },
}

# ──────────────────────────────────────────────
# Scheduler Events — IMM-00 jobs
# ──────────────────────────────────────────────
scheduler_events = {
    "daily": [
        # ... (existing daily jobs) ...
        "assetcore.services.imm00.check_vendor_contract_expiry",     # IMM-00: hợp đồng NCC
        "assetcore.services.imm00.check_byt_registration_expiry",    # IMM-00: đăng ký BYT
        "assetcore.services.imm00.check_capa_overdue",               # IMM-00: CAPA quá hạn
        "assetcore.services.imm00.sync_asset_profile_status",        # IMM-00: đồng bộ status
    ],
    # ... (existing hourly/monthly) ...
}
```

---

## 6. Custom Fields JSON Fixture

File: `assetcore/fixtures/custom_field_asset_imm.json`

```json
[
  {
    "dt": "Asset",
    "fieldname": "imm_section_break",
    "label": "Thông tin HTM / IMM",
    "fieldtype": "Section Break",
    "insert_after": "asset_category",
    "collapsible": 0
  },
  {
    "dt": "Asset",
    "fieldname": "imm_device_model",
    "label": "Model Thiết bị (IMM)",
    "fieldtype": "Link",
    "options": "IMM Device Model",
    "insert_after": "imm_section_break",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 0,
    "in_standard_filter": 1
  },
  {
    "dt": "Asset",
    "fieldname": "imm_asset_profile",
    "label": "Hồ sơ IMM",
    "fieldtype": "Link",
    "options": "IMM Asset Profile",
    "insert_after": "imm_device_model",
    "read_only": 1,
    "reqd": 0,
    "in_list_view": 0,
    "description": "Tự động liên kết khi tạo IMM Asset Profile"
  },
  {
    "dt": "Asset",
    "fieldname": "imm_col_break_1",
    "fieldtype": "Column Break",
    "insert_after": "imm_asset_profile"
  },
  {
    "dt": "Asset",
    "fieldname": "imm_medical_class",
    "label": "Phân loại Y tế",
    "fieldtype": "Select",
    "options": "\nClass I\nClass II\nClass III",
    "insert_after": "imm_col_break_1",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 0,
    "in_standard_filter": 1
  },
  {
    "dt": "Asset",
    "fieldname": "imm_risk_class",
    "label": "Mức độ rủi ro",
    "fieldtype": "Select",
    "options": "\nLow\nMedium\nHigh\nCritical",
    "insert_after": "imm_medical_class",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 0,
    "in_standard_filter": 1
  },
  {
    "dt": "Asset",
    "fieldname": "imm_identifier_section",
    "label": "Định danh Thiết bị",
    "fieldtype": "Section Break",
    "insert_after": "imm_risk_class",
    "collapsible": 1
  },
  {
    "dt": "Asset",
    "fieldname": "imm_byt_reg_no",
    "label": "Số đăng ký BYT",
    "fieldtype": "Data",
    "insert_after": "imm_identifier_section",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 0
  },
  {
    "dt": "Asset",
    "fieldname": "imm_manufacturer_sn",
    "label": "Số Serial Nhà sản xuất",
    "fieldtype": "Data",
    "insert_after": "imm_byt_reg_no",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 1
  },
  {
    "dt": "Asset",
    "fieldname": "imm_col_break_2",
    "fieldtype": "Column Break",
    "insert_after": "imm_manufacturer_sn"
  },
  {
    "dt": "Asset",
    "fieldname": "imm_udi_code",
    "label": "Mã UDI",
    "fieldtype": "Data",
    "insert_after": "imm_col_break_2",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 0,
    "description": "Unique Device Identifier (GS1 / HIBC)"
  },
  {
    "dt": "Asset",
    "fieldname": "imm_gmdn_code",
    "label": "Mã GMDN",
    "fieldtype": "Data",
    "insert_after": "imm_udi_code",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 0
  },
  {
    "dt": "Asset",
    "fieldname": "imm_status_section",
    "label": "Trạng thái Vận hành",
    "fieldtype": "Section Break",
    "insert_after": "imm_gmdn_code",
    "collapsible": 0
  },
  {
    "dt": "Asset",
    "fieldname": "imm_lifecycle_status",
    "label": "Trạng thái Vòng đời",
    "fieldtype": "Select",
    "options": "\nActive\nUnder Repair\nCalibrating\nOut of Service\nDecommissioned",
    "insert_after": "imm_status_section",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 1,
    "in_standard_filter": 1,
    "bold": 1
  },
  {
    "dt": "Asset",
    "fieldname": "imm_calibration_status",
    "label": "Trạng thái Hiệu chuẩn",
    "fieldtype": "Select",
    "options": "\nIn Tolerance\nOut of Tolerance\nNot Required\nOverdue",
    "insert_after": "imm_lifecycle_status",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 0,
    "in_standard_filter": 1
  },
  {
    "dt": "Asset",
    "fieldname": "imm_col_break_3",
    "fieldtype": "Column Break",
    "insert_after": "imm_calibration_status"
  },
  {
    "dt": "Asset",
    "fieldname": "imm_department",
    "label": "Khoa/Phòng",
    "fieldtype": "Link",
    "options": "Department",
    "insert_after": "imm_col_break_3",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 1,
    "in_standard_filter": 1
  },
  {
    "dt": "Asset",
    "fieldname": "imm_responsible_tech",
    "label": "KTV Phụ trách",
    "fieldtype": "Link",
    "options": "User",
    "insert_after": "imm_department",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 0
  },
  {
    "dt": "Asset",
    "fieldname": "imm_pm_section",
    "label": "Lịch Bảo trì & Hiệu chuẩn",
    "fieldtype": "Section Break",
    "insert_after": "imm_responsible_tech",
    "collapsible": 1
  },
  {
    "dt": "Asset",
    "fieldname": "imm_last_pm_date",
    "label": "Ngày PM gần nhất",
    "fieldtype": "Date",
    "insert_after": "imm_pm_section",
    "read_only": 1,
    "reqd": 0,
    "in_list_view": 0,
    "description": "Tự động cập nhật bởi IMM-08"
  },
  {
    "dt": "Asset",
    "fieldname": "imm_next_pm_date",
    "label": "Ngày PM tiếp theo",
    "fieldtype": "Date",
    "insert_after": "imm_last_pm_date",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 0,
    "in_standard_filter": 1
  },
  {
    "dt": "Asset",
    "fieldname": "imm_col_break_4",
    "fieldtype": "Column Break",
    "insert_after": "imm_next_pm_date"
  },
  {
    "dt": "Asset",
    "fieldname": "imm_last_calibration_date",
    "label": "Ngày hiệu chuẩn gần nhất",
    "fieldtype": "Date",
    "insert_after": "imm_col_break_4",
    "read_only": 1,
    "reqd": 0,
    "in_list_view": 0,
    "description": "Tự động cập nhật bởi IMM-11"
  },
  {
    "dt": "Asset",
    "fieldname": "imm_next_calibration_date",
    "label": "Ngày hiệu chuẩn tiếp theo",
    "fieldtype": "Date",
    "insert_after": "imm_last_calibration_date",
    "read_only": 0,
    "reqd": 0,
    "in_list_view": 0
  }
]
```

---

## 7. State Machine — CAPA Workflow

### 7.1 States and Transitions Table

| From State | Trigger / Action | To State | Actor | Guard Condition |
|---|---|---|---|---|
| (new) | create_capa() | Open | Any HTM role | asset exists, severity valid |
| Open | Assign + start work | In Progress | Assigned Tech | root_cause entered |
| Open | cancel() | Cancelled | QA Risk Team / CMMS Admin | docstatus = 0 only |
| In Progress | Submit for verification | Pending Verification | Assigned Tech | corrective_action + preventive_action entered |
| In Progress | cancel() | Cancelled | QA Risk Team / CMMS Admin | docstatus = 0 only |
| Pending Verification | Verify effective | Closed (Effective) | Biomed Engineer / QA | verification_result = Effective |
| Pending Verification | Verify not effective | Open (re-opened) | Biomed Engineer / QA | verification_result = Not Effective → reset to In Progress |
| Pending Verification | Verify partial | Closed (Partial) | Biomed Engineer / QA | verification_result = Partially Effective |
| Closed | submit() | Submitted (docstatus=1) | CMMS Admin | status = Closed, verification_result set |
| Submitted | cancel() | Cancelled (docstatus=2) | System Manager only | irreversible |

### 7.2 State Machine ASCII Diagram

```
                            ┌─────────────────────────────┐
                            │          (new)               │
                            └──────────────┬──────────────┘
                                           │ create_capa()
                                           │ [asset valid, severity valid]
                                           ▼
                            ┌─────────────────────────────┐
                  ┌────────►│           Open              │◄────────────┐
                  │         └──────────────┬──────────────┘             │
                  │                        │ assign + root_cause         │
                  │                        ▼                             │ Not Effective
                  │         ┌─────────────────────────────┐             │
                  │         │       In Progress            │             │
                  │         └──────────────┬──────────────┘             │
                  │ cancel() │             │ corrective +                │
                  │ (QA/Admin)│            │ preventive entered          │
                  │          ▼             ▼                             │
                  │  ┌───────────┐  ┌─────────────────────────────┐    │
                  │  │ Cancelled │  │    Pending Verification      │────┘
                  │  └───────────┘  └──────────────┬──────────────┘
                  │         ▲                       │
                  │         │ cancel() (QA/Admin)   │ verify
                  │         │                       │
                  └─────────┴───────────────────────┤
                                                    │
                           ┌─────────────────────── ├──────────────────────┐
                           │ Effective              │ Partially Effective   │
                           ▼                        ▼                       │
              ┌────────────────────┐  ┌────────────────────┐               │
              │ Closed (Effective) │  │  Closed (Partial)  │               │
              └─────────┬──────────┘  └──────────┬─────────┘               │
                        │                        │                          │
                        └─────────┬──────────────┘                          │
                                  │ submit()                                 │
                                  │ [CMMS Admin]                             │
                                  ▼
                     ┌────────────────────────────┐
                     │   Submitted (docstatus=1)  │
                     └────────────────────────────┘
```

---

## 8. Database Indexes

```sql
-- IMM Asset Profile
ALTER TABLE `tabIMM Asset Profile`
  ADD UNIQUE INDEX `idx_asp_asset` (`asset`),
  ADD INDEX `idx_asp_device_model` (`device_model`),
  ADD INDEX `idx_asp_lifecycle_status` (`lifecycle_status`),
  ADD INDEX `idx_asp_next_pm_date` (`next_pm_date`),
  ADD INDEX `idx_asp_next_calibration_date` (`next_calibration_date`),
  ADD INDEX `idx_asp_warranty_expiry` (`warranty_expiry_date`),
  ADD INDEX `idx_asp_byt_reg_expiry` (`byt_reg_expiry`),
  ADD INDEX `idx_asp_department` (`department`);

-- IMM Audit Trail
ALTER TABLE `tabIMM Audit Trail`
  ADD INDEX `idx_aud_asset_ts` (`asset`, `event_timestamp`),
  ADD INDEX `idx_aud_source` (`source_doctype`, `source_name`),
  ADD INDEX `idx_aud_event_type` (`event_type`),
  ADD INDEX `idx_aud_actor` (`actor`),
  ADD INDEX `idx_aud_creation` (`creation`);

-- IMM CAPA Record
ALTER TABLE `tabIMM CAPA Record`
  ADD INDEX `idx_capa_asset_status` (`asset`, `status`),
  ADD INDEX `idx_capa_assigned_due` (`assigned_to`, `due_date`),
  ADD INDEX `idx_capa_severity` (`severity`),
  ADD INDEX `idx_capa_overdue` (`is_overdue`, `status`),
  ADD INDEX `idx_capa_source` (`source_doctype`, `source_name`);

-- IMM Device Model
ALTER TABLE `tabIMM Device Model`
  ADD UNIQUE INDEX `idx_mdl_name_mfr` (`model_name`, `manufacturer`),
  ADD INDEX `idx_mdl_risk_class` (`risk_class`),
  ADD INDEX `idx_mdl_byt_reg_expiry` (`byt_reg_expiry`),
  ADD INDEX `idx_mdl_device_category` (`device_category`),
  ADD INDEX `idx_mdl_gmdn_code` (`gmdn_code`);

-- IMM Vendor Profile
ALTER TABLE `tabIMM Vendor Profile`
  ADD UNIQUE INDEX `idx_vnd_supplier` (`supplier`),
  ADD INDEX `idx_vnd_contract_expiry` (`contract_expiry`),
  ADD INDEX `idx_vnd_is_active` (`is_active`),
  ADD INDEX `idx_vnd_byt_license_expiry` (`byt_license_expiry`);

-- IMM Location Ext
ALTER TABLE `tabIMM Location Ext`
  ADD UNIQUE INDEX `idx_loc_location` (`location`),
  ADD INDEX `idx_loc_building` (`building`),
  ADD INDEX `idx_loc_department` (`department`),
  ADD INDEX `idx_loc_location_type` (`location_type`);

-- IMM SLA Policy
ALTER TABLE `tabIMM SLA Policy`
  ADD UNIQUE INDEX `idx_sla_policy_name` (`policy_name`),
  ADD INDEX `idx_sla_priority_risk` (`priority`, `risk_class`),
  ADD INDEX `idx_sla_is_active` (`is_active`);

-- IMM Authorized Technician (child)
ALTER TABLE `tabIMM Authorized Technician`
  ADD INDEX `idx_tech_parent` (`parent`),
  ADD INDEX `idx_tech_cert_expiry` (`certification_expiry`);

-- IMM Device Spare Part (child)
ALTER TABLE `tabIMM Device Spare Part`
  ADD INDEX `idx_spare_parent` (`parent`),
  ADD INDEX `idx_spare_item_code` (`item_code`);
```

**Index Rationale:**

| Table | Index | Justification |
|---|---|---|
| IMM Asset Profile | `(asset)` UNIQUE | 1:1 enforcement at DB level |
| IMM Asset Profile | `(next_pm_date)` | Daily scheduler query for upcoming PM |
| IMM Audit Trail | `(asset, event_timestamp)` | Timeline queries per asset |
| IMM Audit Trail | `(source_doctype, source_name)` | Reverse lookup from any record |
| IMM CAPA Record | `(asset, status)` | Dashboard open CAPA count per asset |
| IMM CAPA Record | `(assigned_to, due_date)` | Overdue CAPA query by assignee |
| IMM Device Model | `(model_name, manufacturer)` UNIQUE | Duplicate prevention at DB level |

---

## 9. Exception Catalog

| Code | HTTP Equiv | Vietnamese Message | Trigger | DocType |
|---|---|---|---|---|
| MDL-001 | 400 | Tên model đã tồn tại cho nhà sản xuất này | Duplicate `model_name` + `manufacturer` on insert/update | IMM Device Model |
| MDL-002 | 400 | Model không tồn tại hoặc đã bị vô hiệu hoá | `get_doc` trả về None hoặc `is_active=0` | IMM Device Model |
| MDL-003 | 400 | Mã GMDN không hợp lệ (phải là chuỗi 5–6 ký tự số) | GMDN format validation | IMM Device Model |
| MDL-004 | 400 | Chu kỳ hiệu chuẩn cần được nhập khi thiết bị yêu cầu hiệu chuẩn | `requires_calibration=1` nhưng interval trống | IMM Device Model |
| ASP-001 | 400 | Tài sản này đã có hồ sơ IMM | Duplicate `asset` on insert | IMM Asset Profile |
| ASP-002 | 404 | Không tìm thấy hồ sơ IMM cho tài sản này | `get_profile_name` trả về None | IMM Asset Profile |
| ASP-003 | 400 | Ngày PM tiếp theo phải sau ngày PM gần nhất | `next_pm_date <= last_pm_date` | IMM Asset Profile |
| ASP-004 | 400 | Ngày hiệu chuẩn tiếp theo phải sau ngày hiệu chuẩn gần nhất | `next_calibration_date <= last_calibration_date` | IMM Asset Profile |
| ASP-005 | 400 | Tài sản đang Decommissioned — không thể tạo lệnh công việc | `lifecycle_status = Decommissioned` khi validate_asset_for_operations | IMM Asset Profile |
| ASP-006 | 400 | Tài sản đang Out of Service — cần phê duyệt đặc biệt | `lifecycle_status = Out of Service` khi tạo WO thường | IMM Asset Profile |
| VND-001 | 400 | Nhà cung cấp này đã có hồ sơ IMM Vendor | Duplicate `supplier` on insert | IMM Vendor Profile |
| VND-002 | 400 | Hợp đồng đã hết hạn — không thể chỉ định cho lệnh công việc mới | `contract_expiry < today` khi assign vendor to WO | IMM Vendor Profile |
| VND-003 | 400 | KTV chưa được cấp chứng chỉ hợp lệ cho thiết bị này | `certification_expiry < today` hoặc trống | IMM Authorized Technician |
| LOC-001 | 400 | Địa điểm này đã có hồ sơ IMM Location Ext | Duplicate `location` on insert | IMM Location Ext |
| SLA-001 | 404 | Không tìm thấy SLA Policy phù hợp với priority và risk_class | `get_sla_policy` trả về {} | IMM SLA Policy |
| SLA-002 | 400 | SLA Policy đã bị vô hiệu hoá | `is_active=0` khi lookup | IMM SLA Policy |
| AUD-001 | 403 | Bản ghi Audit Trail không thể chỉnh sửa sau khi tạo | `on_update` bị gọi trên IMM Audit Trail | IMM Audit Trail |
| AUD-002 | 403 | Xoá bản ghi Audit Trail bị nghiêm cấm | Delete được thử | IMM Audit Trail |
| AUD-003 | 400 | Integrity hash không khớp — bản ghi Audit Trail bị giả mạo | Hash mismatch trong `before_insert` | IMM Audit Trail |
| CAPA-001 | 400 | Mức độ nghiêm trọng không hợp lệ | `severity` không trong tập hợp hợp lệ | IMM CAPA Record |
| CAPA-002 | 400 | CAPA đã được đóng hoặc huỷ, không thể thao tác thêm | `close_capa()` trên closed/cancelled CAPA | IMM CAPA Record |
| CAPA-003 | 400 | Kết quả xác minh là bắt buộc trước khi nộp CAPA | `before_submit` thiếu `verification_result` | IMM CAPA Record |
| CAPA-004 | 400 | Hành động khắc phục là bắt buộc trước khi nộp CAPA | `before_submit` thiếu `corrective_action` | IMM CAPA Record |
| CAPA-005 | 400 | CAPA ở trạng thái X cần có người phụ trách | `assigned_to` trống khi status In Progress | IMM CAPA Record |
| CAPA-006 | 400 | Kết quả xác minh không hợp lệ | `verification_result` không trong tập hợp hợp lệ | IMM CAPA Record |
| STS-001 | 400 | Trạng thái không hợp lệ | `new_status` không trong tập trạng thái hợp lệ | sync_lifecycle_status |
| BULK-001 | 400 | Danh sách import không được rỗng | `bulk_update_device_model` nhận items=[] | imm00 API |
| BULK-002 | 400 | Vượt quá giới hạn import (tối đa 500 bản ghi mỗi lần) | `len(items) > 500` | imm00 API |
