# MAPPING ERPNEXT ↔ ASSETCORE — DEPRECATED (v3)

> ⚠️ **Reconciled to v3 codebase — 2026-05-07.** Kiến trúc đã thay đổi: **AssetCore là app Frappe-only, KHÔNG dependency ERPNext.** File này được giữ lại như historical reference. Các mục về ERPNext sync, custom field on Item/Asset/Supplier, ERPNextAssetSync service đều **out of scope**. Xem `docs/ba/00_RECONCILIATION_v3.md` §0 cho lý do.

**Phiên bản:** 3.0
**Owner:** Tech Lead
**Trạng thái:** DEPRECATED (giữ làm tham chiếu lịch sử)

---

## 0. Lý do thay đổi

Trong design ban đầu (BA pack v1), AssetCore được hình dung là:
- ERPNext core làm System of Record cho `Item`, `Asset`, `Supplier`, `Department`, `Stock Entry`, `Purchase Receipt`.
- AssetCore là *lớp HTM trên ERPNext*, đồng bộ 2 chiều qua hooks.
- `Custom Field` thêm vào DocType core ERPNext (như `is_medical_device`, `risk_class`, `assetcore_link`).

Trong code v3 hiện tại:
- File `assetcore/hooks.py` xác nhận: `override_doctype_class = {}` và comment *"AssetCore is Frappe-only (no ERPNext dep)"*.
- Mọi master data có **DocType custom riêng** (`AC Asset`, `AC Supplier`, `AC Department`, `AC Stock Movement`, `AC Purchase`).
- Không có file nào tham chiếu `Item`, `Asset` (ERPNext), `Supplier` (ERPNext), `Stock Entry`, `Purchase Receipt`.

> **Hệ quả:** mọi quy trình sync 2 chiều, custom field on core, ERPNextAssetSync service **không còn áp dụng**.

---

## 1. Mapping cập nhật (v3, Frappe-only)

| Lĩnh vực HTM | DocType v3 (Frappe-only) | Ghi chú |
|---|---|---|
| Danh mục thiết bị (model spec) | `IMM Device Model` | Master spec kỹ thuật, gắn `AC Asset` |
| Tài sản (instance) | `AC Asset` | Single source of truth — không sync ngoại |
| NCC / Vendor / Service Provider | `AC Supplier` | Gộp với phân loại qua field |
| Hợp đồng dịch vụ | `Service Contract` (+ `Service Contract Asset` child) | – |
| Mua sắm (PO) | `AC Purchase` (+ `AC Purchase Item`, `AC Purchase Device Item`) | Bắt buộc link `IMM Procurement Decision` qua validate hook |
| Tiếp nhận / kho | `AC Stock Movement` (+ `AC Stock Movement Item`) | Auto-mark purchase received qua `services/purchase.py` |
| Phụ tùng | `AC Spare Part` (master) + `AC Spare Part Stock` (tồn kho) + `IMM Device Spare Part` (BOM theo Device Model) + `Spare Parts Used` (per-WO) | – |
| Phòng/Khoa | `AC Department` | – |
| Phân cấp địa điểm | `AC Location` | – |
| UOM | `AC UOM` (+ `AC UOM Conversion`) | – |
| Warehouse | `AC Warehouse` | – |
| Tài liệu hồ sơ | `Asset Document` (+ `Document Request`, `Required Document Type`, `Expiry Alert Log`) | Frappe `File` chỉ làm storage backend |
| Workflow engine | Frappe `Workflow` + `Workflow State` + `Workflow Action Master` | 14 workflow JSON tại `assetcore/assetcore/workflow/` |
| Audit chain | `IMM Audit Trail` (SHA-256) | `assetcore.utils.lifecycle.log_audit_event` |
| Lifecycle event | `Asset Lifecycle Event` | `assetcore.utils.lifecycle.create_lifecycle_event` |
| Email/Notification | Frappe `Email Queue` + `Notification` + `Expiry Alert Log` | – |
| Dashboard | Frappe `Dashboard Chart` + `Number Card` + custom API qua `assetcore/api/dashboard.py` | – |
| Khấu hao | `AC Asset Depreciation Schedule` | Run monthly qua `services/depreciation.py` |
| Permission row-level | Frappe `permission_query_conditions` | 4 handler trong `assetcore/permissions.py` |

---

## 2. Custom field trên ERPNext core — KHÔNG ÁP DỤNG

Mọi mục trong bản gốc về:
- `Item.is_medical_device`, `Item.risk_class`, `Item.criticality`, `Item.htm_device_model`
- `Asset.assetcore_link`, `Asset.htm_state_mirror`
- `Supplier.is_service_provider`
- `Stock Entry.linked_work_order`
- `Purchase Receipt Item.auto_create_assetcore_asset`
- `Department.is_clinical`, `Employee.assetcore_role`

→ **Không tồn tại trong v3.** Các thuộc tính này, nếu cần, là **field bản địa** trên `AC Asset` / `AC Supplier` / `IMM Device Model` / `AC Department`.

---

## 3. Hooks ERPNext-related — KHÔNG ÁP DỤNG

Phần inbound (`Purchase Receipt on_submit`, `Stock Entry on_submit`, `Asset on_submit/on_update`, `Item on_update`, `Department on_update`) và outbound (`AC Medical Asset → Asset`, `AC Decommission Record → Asset Disposal`, …) **không tồn tại** trong `hooks.py` v3.

**Hooks thực tế** (xem `assetcore/hooks.py`):

```python
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            "assetcore.services.imm11.create_calibration_schedule_from_commissioning",
        ],
    },
    "AC Stock Movement": {
        "on_submit": ["assetcore.services.purchase.auto_mark_purchase_received"],
        "on_cancel": ["assetcore.services.purchase.auto_unmark_purchase_received"],
    },
    "AC Purchase": {
        "validate": "assetcore.services.imm03.validate_ac_purchase_imm_link",
    },
}
```

---

## 4. Reconciliation MA ↔ Asset — KHÔNG ÁP DỤNG

Phần "Đồng bộ field giữa MA ↔ Asset" và `ERPNextAssetSync` service trong bản gốc **không tồn tại**. `AC Asset` là single source of truth cho mọi thuộc tính tài sản.

---

## 5. Capabilities Frappe core đang tận dụng

- Naming Series engine.
- Workflow engine (`Workflow`, `Workflow State`, `Workflow Action Master`).
- Email queue + Notification + Auto Email Report.
- Print Format engine.
- Dashboard + Number Card.
- Auto Assignment Rule.
- Frappe `File` + Permission.
- Frappe `Role`, `Role Profile`, `Module Profile`, `User Permission`.
- Frappe Version (audit field changes — bổ sung cho audit chain).
- Frappe Custom Field/Property Setter (cho config, không cho schema core).

---

## 6. Capabilities **KHÔNG** dùng (kế hoạch giữ nguyên)

| Frappe / ERPNext capability | Lý do không dùng |
|---|---|
| ERPNext app toàn bộ | AssetCore là app Frappe-only, độc lập |
| Frappe `Asset Maintenance` | Không có trong Frappe core (là ERPNext) — không liên quan |
| Frappe `Quality Inspection` | Không có trong Frappe core (ERPNext) — thay bằng `Commissioning Checklist` + `IMM Calibration Measurement` |
| `Project` / `Task` thay cho WO | Không có SLA + spare consumption + state machine HTM phù hợp |

---

## 7. Tiêu chí nghiệm thu (cập nhật)

- ✓ AssetCore deploy được với chỉ Frappe v15 (không cài ERPNext).
- ✓ `bench migrate` chạy clean — không có reference đến ERPNext DocType.
- ✓ `IMM Audit Trail.verify_audit_chain` pass cho mọi asset.
- ✓ `permission_query_conditions` test pass cho 4 DocType được wire.

---

## 8. Quyết định

| Quyết định | Lý do | Người duyệt | Ngày |
|---|---|---|---|
| Bỏ dependency ERPNext | Giảm rủi ro upgrade ERPNext, đơn giản hóa stack, AssetCore không cần kế toán phức tạp | Tech Lead | (đã thực hiện trong v3 codebase) |
| Bỏ ERPNextAssetSync service | Không còn cần đồng bộ 2 chiều | Tech Lead | (đã thực hiện) |
| Giữ Frappe core capabilities (Workflow, Permission, Naming, Notification) | Tận dụng tối đa Frappe; không reinvent | Tech Lead | – |

---

## 9. Tham chiếu cho dev mới

- Xem `assetcore/hooks.py` để biết toàn bộ hooks đã wire.
- Xem `assetcore/permissions.py` cho permission query.
- Xem `assetcore/utils/lifecycle.py` cho audit + lifecycle helpers.
- Xem `00_RECONCILIATION_v3.md` cho mapping BA-name → reality.
