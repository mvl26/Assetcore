# IMM-04 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE — 31/32 UAT PASS |
| Tác giả | AssetCore Team |

---

## 1. Overview

### 1.1 Layer Architecture

```
HTTP Request
      │
      ▼
API Layer  (assetcore/api/imm04.py — 17 whitelisted endpoints)
      │   _ok / _err envelope; permission check; payload parse
      ▼
Service Layer  (assetcore/services/imm04.py)
      │   business rules, gates, lifecycle event logging
      ▼
Controller  (assetcore/assetcore/doctype/asset_commissioning/asset_commissioning.py)
      │   before_insert / before_save / validate / on_submit / on_cancel
      ▼
Frappe ORM → MariaDB (tabAsset Commissioning + 3 child tables + Asset QA Non Conformance)
      │
      ▼
Side Effects:
  • AC Asset insert (create_ac_asset) — AssetCore native DocType, first-class HTM fields
  • IMM-05 Asset Document Draft (create_initial_document_set, graceful skip)
  • Realtime publish (imm04_asset_released, imm04_notify_purchasing)
  • Lifecycle Event row (immutable VR-06)
```

### 1.2 ERD

```
                        ┌──────────────────────┐
                        │  Purchase Order      │ (ERPNext)
                        └──────────┬───────────┘
                                   │ po_reference
                                   ▼
   ┌────────────────────────────────────────────────────┐
   │   Asset Commissioning  (IMM04-YY-MM-#####)         │
   │   workflow_state, docstatus, vendor_serial_no,     │
   │   internal_tag_qr, risk_class, final_asset…        │
   └────────────────────────────────────────────────────┘
        │ baseline_tests          │ commissioning_documents     │ lifecycle_events
        ▼                         ▼                              ▼
   ┌──────────────────┐   ┌────────────────────────────┐   ┌──────────────────────┐
   │ Commissioning    │   │ Commissioning Document     │   │ Asset Lifecycle      │
   │   Checklist      │   │   Record                   │   │   Event (immutable)  │
   └──────────────────┘   └────────────────────────────┘   └──────────────────────┘

   ┌────────────────────────────────────┐
   │ Asset QA Non Conformance           │ ─── ref_commissioning ───► Asset Commissioning
   │ (NC-YY-MM-#####, submittable)      │
   └────────────────────────────────────┘

   on_submit(Asset Commissioning)
        ├──► Asset (ERPNext, custom_vendor_serial / custom_internal_qr / custom_comm_ref)
        └──► Asset Document × N (IMM-05 Draft, source_module="IMM-04")
```

---

## 2. DocType Schema

### 2.1 `Asset Commissioning` (`tabAsset Commissioning`)

**Autoname:** `IMM04-.YY.-.MM.-.#####`  
**is_submittable:** 1 · **track_changes:** 1 · **track_views:** 1  
**Module:** AssetCore  
**Workflow:** `IMM-04 Workflow` (state field `workflow_state`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `workflow_state` | Link → Workflow State | — | read_only, in_list_view, in_standard_filter |
| `po_reference` | Link → Purchase Order | YES | search_index, in_list_view |
| `master_item` | Link → Item | YES | in_list_view |
| `vendor` | Link → Supplier | YES | |
| `clinical_dept` | Link → Department | YES | |
| `expected_installation_date` | Date | YES | |
| `reception_date` | Date | — | auto-set today() trong `initialize_commissioning` |
| `installation_date` | Datetime | — | read_only; auto-set khi vào state Installing (`before_save`) |
| `vendor_engineer_name` | Data | — | |
| `commissioned_by` | Link → User | — | KTV phụ trách |
| `is_radiation_device` | Check | — | read_only; fetch_from `master_item.custom_is_radiation` |
| `risk_class` | Select `A\nB\nC\nD\nRadiation` | — | auto-fetch từ `Item.custom_risk_class` |
| `radiation_license_no` | Data | — | |
| `doa_incident` | Check | — | flag set bởi `report_doa` / `create_nc_from_form` |
| `clinical_head` | Link → User | — | |
| `qa_officer` | Link → User | — | |
| `board_approver` | Link → User | — | G06 — bắt buộc trước Clinical Release |
| `facility_checklist_pass` | Check | — | G02 |
| `commissioning_date` | Date | — | read_only |
| `overall_inspection_result` | Select `Pass\nFail\nConditional Pass` | — | read_only; set bởi `submit_baseline_checklist` |
| `vendor_serial_no` | Data | YES | search_index; UNIQUE (VR-01) |
| `internal_tag_qr` | Data | — | read_only; auto-sinh `BV-{DEPT}-{YYYY}-{SEQ}` khi vào Identification |
| `custom_moh_code` | Data | — | Mã BYT (manual) |
| `site_photo` | Attach Image | — | Bắt buộc nghiệp vụ (không enforce JSON) |
| `installation_evidence` | Attach | — | |
| `qa_license_doc` | Attach | — | Bắt buộc nếu `is_radiation_device=1` (VR-07) |
| `handover_doc` | Attach | — | |
| `baseline_tests` | Table → Commissioning Checklist | YES | Tab "Kết quả Kiểm tra An toàn" |
| `commissioning_documents` | Table → Commissioning Document Record | — | Tab "Hồ sơ Đi kèm" |
| `amend_reason` | Small Text | COND | reqd nếu `amended_from` |
| `final_asset` | Link → Asset | — | read_only; set bởi `mint_core_asset` |
| `lifecycle_events` | Table → Asset Lifecycle Event | — | read_only; immutable |
| `amended_from` | Link → Asset Commissioning | — | auto |

### 2.2 `Commissioning Checklist` (child)

| Field | Type | Required | Notes |
|---|---|---|---|
| `parameter` | Data | YES | in_list_view |
| `is_critical` | Check | — | default 0 |
| `measurement_type` | Select `Numeric\nPass/Fail\nVisual` | — | |
| `measured_val` | Float | — | in_list_view |
| `expected_min`, `expected_max` | Float | — | |
| `unit` | Data | — | in_list_view |
| `test_result` | Select `Pass\nFail\nN/A` | YES | in_list_view |
| `na_applicable` | Check | — | |
| `fail_note` | Text | — | depends_on `test_result == 'Fail'` |

### 2.3 `Commissioning Document Record` (child)

| Field | Type | Required | Notes |
|---|---|---|---|
| `doc_type` | Select (CO/CQ/Packing List/Manual/Warranty/Training/Other) | YES | in_list_view |
| `doc_number` | Data | — | |
| `is_mandatory` | Check | — | default 1; in_list_view |
| `status` | Select (Pending/Received/Missing/Rejected/Waived) | YES | default Pending; in_list_view |
| `received_date` | Date | — | depends_on status=Received |
| `expiry_date` | Date | — | check 30-day warning |
| `file_url` | Attach | — | |
| `remarks` | Small Text | — | |

### 2.4 `Asset Lifecycle Event` (child, immutable)

| Field | Type | Required | Notes |
|---|---|---|---|
| `event_type` | Select (State Transition / Document Upload / Release / Cancel / Non-Conformance / Baseline Test / Identification / Handover) | YES | |
| `from_status`, `to_status` | Data | — | |
| `actor` | Link → User | YES | |
| `event_timestamp` | Datetime | YES | |
| `ip_address` | Data | — | read_only; capture từ request |
| `remarks` | Text | — | |
| `root_record` | Data | — | read_only; tên parent |

VR-06 enforce: `_vr06_immutable_lifecycle_events()` block edit row đã có (compare `actor`, `event_type`).

### 2.5 `Asset QA Non Conformance` (`tabAsset QA Non Conformance`)

**Autoname:** `format:NC-.YY.-.MM.-.#####` · **is_submittable:** 1 · **track_changes:** 1

| Field | Type | Required | Notes |
|---|---|---|---|
| `ref_commissioning` | Link → Asset Commissioning | YES | search_index, in_list_view |
| `nc_type` | Select `DOA\nMissing\nCrash\nOther` | YES | in_list_view |
| `severity` | Select `Minor\nMajor\nCritical` | — | in_list_view |
| `resolution_status` | Select `Open\nUnder Review\nResolved\nClosed\nTransferred` | YES | default Open |
| `transfer_to_capa` | Check | — | flag handoff QMS |
| `description` | Small Text | YES | |
| `root_cause` | Text | — | reqd khi close (API) |
| `damage_proof` | Attach Image | COND | mandatory_depends_on `nc_type == 'DOA'` |
| `resolution_note` | Text | — | |
| `return_to_vendor_ref` | Data | — | |
| `penalty_amount` | Currency | — | permlevel 1 (BGĐ) |
| `closed_by` | Link → User | — | |
| `closed_date` | Date | — | |

---

## 3. Validation Rules — Implementation

| VR | Function | File | Trigger |
|---|---|---|---|
| VR-01 | `validate_unique_serial()` (controller) + `_vr01_unique_serial_number()` (service) | `asset_commissioning.py`, `services/imm04.py` | `validate()` |
| VR-02 (G01) | `validate_gate_g01(doc)` | `services/imm04.py` | `validate()` (chỉ chạy khi state ≠ Draft/Pending Doc Verify) |
| VR-03 (G03) | `validate_checklist_completion()` (controller) + `validate_gate_g03(doc)` (service) | both | `validate()` (state ∈ Initial Inspection / Re Inspection / Clinical Release) |
| VR-04 (G05) | `block_release_if_nc_open()` + `validate_gate_g05_g06(doc)` | both | `validate()` (state = Clinical Release) |
| VR-05 | `_vr05_risk_class_change_warning(doc)` | `services/imm04.py` | `validate()` (msgprint, không block) |
| VR-06 | `_vr06_immutable_lifecycle_events(doc)` | `services/imm04.py` | `validate()` |
| VR-07 | `validate_radiation_hold()` | controller | `validate()` |
| G06 | `validate_gate_g05_g06()` (kiểm tra `board_approver`) | service | `validate()` |
| BR-07 / GW-2 | `_gw2_check_document_compliance()` | controller | `validate()` (state ∈ Clinical_Release / Pending_Release) |
| VR-Backdate | `validate_backdate()` | controller | `validate()` |
| VR-DocExpiry | `_validate_document_expiry(doc)` | service | `validate()` |

---

## 4. Lifecycle Hooks (Controller)

| Hook | Method | Logic |
|---|---|---|
| `before_insert` | `before_insert()` (Python) + `assetcore.services.imm04.initialize_commissioning` (hooks.py) | Set defaults, fetch risk_class, populate mandatory docs |
| `before_save` | `before_save()` | Set `installation_date = now()` khi vào Installing; sinh `internal_tag_qr` khi vào Identification |
| `validate` | `validate()` | Chạy chuỗi VR + Gate (xem §3) |
| `on_submit` | `on_submit()` | Yêu cầu state = `Clinical_Release` → `mint_core_asset()` → `create_initial_document_set()` → log lifecycle event "Release" → `fire_release_event()` |
| `on_cancel` | `on_cancel()` | Block nếu `final_asset` đã có; chỉ cho cancel ở Draft / Non Conformance / Return To Vendor; log "Cancel" event |

### 4.1 `mint_core_asset()` (controller)

Tạo `Asset` với:
- `item_code = doc.master_item`
- `asset_name = "{master_item} — {vendor_serial_no}"`
- `available_for_use_date = today()`
- `gross_purchase_amount = 1` (placeholder — kế toán cập nhật)
- `custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref`

`flags.ignore_mandatory = True`, `flags.ignore_links = True`. Lưu `final_asset` qua `db_set` (commit ngay).

### 4.2 `create_initial_document_set()` (controller)

Cho mỗi row `commissioning_documents` có `status = "Received"`:

```
DOC_CATEGORY_MAP = {
  "CO": "QA", "CQ": "QA", "Packing": "QA",
  "Manual": "Technical", "Warranty": "QA",
  "License": "Legal", "Training": "Training", "Other": "Technical",
}
```

→ tạo `Asset Document` Draft với `source_commissioning = doc.name`, `source_module = "IMM-04"`, `visibility = "Public"`.

Nếu có `qa_license_doc` → tạo thêm 1 Asset Document `doc_type_detail = "Giấy phép bức xạ"`, `doc_category = "Legal"`, `visibility = "Internal_Only"`.

Graceful skip nếu `tabAsset Document` chưa tồn tại.

### 4.3 `_gw2_check_document_compliance()`

Block Submit nếu `final_asset` không có `Asset Document` với `doc_type_detail = "Chứng nhận đăng ký lưu hành"` ở `workflow_state = "Active"` và không phải Exempt.

### 4.4 `fire_release_event()`

`frappe.publish_realtime("imm04_asset_released", payload, user=session.user)` + notify mọi user có role `Purchase User` qua `imm04_notify_purchasing`.

---

## 5. hooks.py

```python
fixtures = [
  {"dt": "Workflow", "filters": [["name", "in", ["IMM-04 Workflow", "IMM-05 Document Workflow"]]]},
  {"dt": "Required Document Type"},
  {"dt": "Custom Field", "filters": [["dt", "in", ["Asset"]]]},
]

doc_events = {
  "Asset Commissioning": {
    "before_insert": "assetcore.services.imm04.initialize_commissioning",
  },
  "IMM CAPA Record":   { "on_submit": "assetcore.services.imm00.on_capa_submit" },
}

scheduler_events = {
  "daily": [
    "assetcore.services.imm04.check_commissioning_overdue",
    "assetcore.tasks.check_clinical_hold_aging",
    "assetcore.tasks.check_commissioning_sla",
    # ... (IMM-00, IMM-05, IMM-08, IMM-09)
  ],
}
```

---

## 6. State Machine — `workflow_state`

```
                ┌────────┐
                │ Draft  │◄────── Yêu cầu bổ sung tài liệu
                └───┬────┘
       Gửi kiểm tra │
                    ▼
        ┌────────────────────────┐
        │  Pending Doc Verify    │ G01: mandatory docs
        └───────────┬────────────┘
       Xác nhận đủ │
                   ▼
        ┌────────────────────────┐    Báo cáo sự cố
        │   To Be Installed      │─────────────────┐
        └───────────┬────────────┘                 │
       Bắt đầu lắp │                               ▼
                   ▼                      ┌──────────────────┐
        ┌────────────────────────┐  DOA   │ Non Conformance  │
        │     Installing         │───────►└──┬───────────────┘
        └───────────┬────────────┘    Khắc │  │ Trả lại NCC
       Lắp đặt xong│                  phục │  │
                   ▼                       │  ▼
        ┌────────────────────────┐         │  ┌──────────────────┐
        │   Identification       │ ◄───────┘  │ Return To Vendor │ (terminal)
        │   (auto-sinh QR)       │            └──────────────────┘
        └───────────┬────────────┘
       Bắt đầu KT  │
                   ▼
        ┌────────────────────────┐
        │   Initial Inspection   │ G03: 100% Pass/N/A
        └─┬────┬────┬────────────┘
   Lỗi    │    │    │ Class C/D/Radiation
   baseline    │    └─────────────────►┌────────────────┐
          │    │                       │ Clinical Hold  │ G04 (qa_license_doc)
          ▼    │                       └───┬────────────┘
   ┌────────────────┐                  Gỡ │
   │ Re Inspection  │                     ▼
   └──────┬─────────┘             (re-route)
       Phê duyệt  │
       sau tái KT │
                  ▼
        ┌────────────────────────┐ G05: no Open NC
        │   Clinical Release     │ G06: board_approver
        │   (docstatus=1)        │ BR-07: GW-2
        │   → Asset minted       │ TERMINAL
        └────────────────────────┘
```

---

## 7. Schedulers

| Function | File | Tần suất | Logic |
|---|---|---|---|
| `check_commissioning_overdue` | `services/imm04.py` | Daily | docstatus=0, state ∉ {Clinical Release, Return To Vendor}, reception_date < today−30 → email Workshop Head |
| `check_clinical_hold_aging` | `assetcore/tasks.py` | Daily | Phiếu Clinical Hold > N ngày → email QA Officer |
| `check_commissioning_sla` | `assetcore/tasks.py` | Daily | SLA lắp đặt vi phạm → email |

---

## 8. Fixtures

| Fixture | Path | Nội dung |
|---|---|---|
| Workflow | `assetcore/assetcore/workflow/imm_04_workflow.json` | 11 states, 22 transitions |
| Required Document Type | seed via `Required Document Type` DocType | CO, CQ, Manual, Warranty, License, Radiation License |
| Custom Field cho Asset | exported in `fixtures/custom_field.json` | `custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref`, `custom_risk_class`, `custom_is_radiation` |

---

## 9. Indexes & MariaDB

| Table | Column | Loại index |
|---|---|---|
| `tabAsset Commissioning` | `po_reference` | search_index (B-tree) |
| `tabAsset Commissioning` | `vendor_serial_no` | search_index (B-tree); UNIQUE enforce ở app layer |
| `tabAsset Commissioning` | `workflow_state` | in_standard_filter (B-tree) |
| `tabAsset QA Non Conformance` | `ref_commissioning` | search_index (B-tree) |

Khuyến nghị bổ sung composite (chưa có trong JSON):

- `(workflow_state, docstatus, reception_date)` — phục vụ `check_commissioning_overdue` và dashboard.
- `(final_asset)` — tra ngược từ Asset.

---

## 10. Permissions (DocType `Asset Commissioning`)

| Role | Create | Read | Write | Submit | Cancel | Amend | Print | Export |
|---|---|---|---|---|---|---|---|---|
| HTM Technician | ✓ | ✓ | ✓ | — | — | — | ✓ | — |
| Biomed Engineer | — | ✓ | ✓ | — | — | — | ✓ | — |
| Workshop Head | — | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| VP Block2 | — | ✓ | — | ✓ | ✓ | — | ✓ | ✓ |
| QA Risk Team | — | ✓ | ✓ | — | — | — | — | — |

---

## 11. Migration Steps (deploy / upgrade)

1. `bench --site <site> migrate` — apply DocType JSON (Asset Commissioning, 3 child, NC).
2. Import workflow: `bench --site <site> import-doc assetcore/assetcore/workflow/imm_04_workflow.json` (hoặc qua fixtures khi `bench migrate`).
3. Đảm bảo Custom Fields trên `Asset` đã import (`custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref`).
4. Seed `Required Document Type`: CO, CQ, Manual, Warranty, License, Radiation License.
5. Tạo Role: `HTM Technician, Biomed Engineer, Vendor Engineer, QA Officer, Workshop Head, VP Block2, CMMS Admin, QA Risk Team` (nếu chưa có).
6. (Optional) Config Print Format `Biên bản Bàn giao` cho `generate_handover_pdf`.
7. Reload DocType: `bench --site <site> reload-doctype "Asset Commissioning"`.
8. Smoke test: tạo 1 phiếu via `create_commissioning`, chạy hết workflow → Submit, verify `final_asset` được tạo và `imm04_asset_released` event publish.

---

## 12. Known Technical Debt

| Item | Severity | Note |
|---|---|---|
| Workflow state mixed naming (`Clinical Release` vs `Clinical_Release`) | LOW | Service code dùng underscore form ở vài chỗ; FE/workflow JSON dùng space form. Cần chuẩn hoá 1 chuẩn duy nhất. |
| `mint_core_asset` không rollback transaction nếu IMM-05 import fail | MEDIUM | Hiện chỉ log, asset đã tạo. Cần wrap try/except + savepoint. |
| `vendor_serial_no` UNIQUE chỉ enforce ở app layer (không có DB UNIQUE constraint) | MEDIUM | Race condition khả dĩ. Nên thêm UNIQUE index nullable. |
| Print Format Biên bản chưa config | MEDIUM | `generate_handover_pdf` trả URL nhưng PDF có thể fail. |
| PM auto-create không trigger | HIGH | `fire_release_event` đã bắn nhưng IMM-08 chưa subscribe (UAT TC-32 FAIL). |

*End of Technical Design v2.0.0 — IMM-04*
