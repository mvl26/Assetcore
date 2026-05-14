# IMM-00 v3 — Compatibility Analysis: IMM-04/05/08/09/11/12

| Thuộc tính | Giá trị |
|---|---|
| Ngày phân tích | 2026-04-18 |
| Kiến trúc tham chiếu | IMM-00 v3 (Frappe-only, không ERPNext) |
| Phạm vi | BE code (api/, services/, doctype/) + Docs (docs/imm-xx/) |
| Kết luận nhanh | BE ~85% tương thích · Docs ~55% tương thích |

---

## 1. Bối cảnh — IMM-00 v3 Breaking Changes

IMM-00 v3 đã thay đổi kiến trúc căn bản so với v2:

| Hạng mục | v2 (cũ) | v3 (mới) |
|---|---|---|
| Dependency | ERPNext v15 | **Chỉ Frappe Framework v15** |
| DocType tài sản | ERPNext `Asset` + 16 `custom_imm_*` fields | **`AC Asset`** — HTM fields first-class |
| NCC | ERPNext `Supplier` | **`AC Supplier`** |
| Vị trí | ERPNext `Location` + `IMM Location Ext` sidecar | **`AC Location`** |
| Khoa/Phòng | ERPNext `Department` + sidecar | **`AC Department`** |
| Phân loại TB | ERPNext `Asset Category` | **`AC Asset Category`** |
| Hồ sơ HTM | `IMM Asset Profile` (sidecar 1:1) | **Bỏ** — fields nằm trực tiếp trên AC Asset |
| Sync job | `sync_asset_profile_status()` daily | **Bỏ** — không cần sync nữa |
| Status change | `update_asset_lifecycle_status()` | **`transition_asset_status()`** |
| Lifecycle log | inline trong service | **`Asset Lifecycle Event`** (standalone DocType) |
| Sự cố | Chưa có | **`Incident Report`** DocType (mới) |
| Utils | Inline helpers | **`assetcore/utils/{response,lifecycle,email,pagination}.py`** |

---

## 2. BE Code — Phân tích tương thích

### 2.1 ✅ TƯƠNG THÍCH — Không cần sửa

#### IMM-04 (Asset Commissioning)

| File | Đánh giá | Ghi chú |
|---|---|---|
| `services/imm04.py` | ✅ | `_DOCTYPE_AC_ASSET = "AC Asset"` · `create_ac_asset()` tạo `AC Asset` đúng · link đúng `IMM Device Model` · dùng `assetcore.utils.lifecycle.create_lifecycle_event` |
| DocType `asset_commissioning` | ✅ | Là AssetCore native DocType, không phụ thuộc ERPNext Asset |
| DocType `asset_qa_non_conformance` | ✅ | Link sang `Asset Commissioning`, không link ERPNext core |
| DocType `commissioning_checklist` | ✅ | Child table, no ERPNext dependency |
| DocType `commissioning_document_record` | ✅ | Child table |

**Lý do tương thích:** `services/imm04.py` đã được refactor dùng `AC Asset` và `assetcore.utils.lifecycle`. `create_ac_asset()` build đúng payload cho `AC Asset` fields (manufacturer_sn, udi_code, medical_device_class, risk_classification, lifecycle_status, is_pm_required...).

---

#### IMM-08 (PM)

| File | Đánh giá | Ghi chú |
|---|---|---|
| `api/imm08.py` | ✅ | `_DT_AC_ASSET = "AC Asset"` · `asset_ref → AC Asset` đúng |
| DocType `pm_work_order` | ✅ | `asset_ref → AC Asset` confirmed từ JSON |
| DocType `pm_schedule` | ✅ | `asset_ref → AC Asset` confirmed |
| DocType `pm_checklist_item` | ✅ | Child table, không ERPNext dep |
| DocType `pm_checklist_result` | ✅ | Child table |
| DocType `pm_task_log` | ✅ | Append-only log |

---

#### IMM-09 (Repair/CM)

| File | Đánh giá | Ghi chú |
|---|---|---|
| `services/imm09.py` | ✅ | `_DOCTYPE_AC_ASSET = "AC Asset"` · `set_asset_under_repair()` dùng `AC Asset` đúng · `_create_lifecycle_event()` gọi lifecycle utils |
| `api/imm09.py` | ✅ | `_DOCTYPE_AC_ASSET = "AC Asset"` · Asset Repair → AC Asset link đúng |
| DocType `asset_repair` | ✅ | `asset_ref → AC Asset` confirmed từ JSON |
| DocType `repair_checklist` | ✅ | Child table |
| DocType `spare_parts_used` | ✅ | Child table |

---

#### Incident Report (IMM-12 foundation)

| File | Đánh giá | Ghi chú |
|---|---|---|
| `incident_report.py` | ✅ | Import đúng: `from assetcore.services.imm00 import create_lifecycle_event, create_capa` |
| DocType `incident_report` | ✅ | `asset → AC Asset` confirmed từ JSON |

---

### 2.2 ⚠️ CẦN SỬA — Không tương thích với v3

#### IMM-05 (Registration/Document) — 2 lỗi SQL nghiêm trọng

**Lỗi 1 — `api/imm05.py` dòng 338:**
```sql
-- HIỆN TẠI (broken):
FROM `tabAsset` a
WHERE a.status = 'In Use'

-- ĐÚNG (v3):
FROM `tabAC Asset` a
WHERE a.lifecycle_status = 'Active'
```

**Lỗi 2 — `api/imm05.py` dòng 411:**
```sql
-- HIỆN TẠI (broken):
FROM `tabAsset` a WHERE a.status = 'In Use' AND a.location IS NOT NULL

-- ĐÚNG (v3):
FROM `tabAC Asset` a WHERE a.lifecycle_status IN ('Active', 'Under Repair') AND a.location IS NOT NULL
```

**Lỗi 3 — `api/imm05.py` cả hai queries** dùng `custom_document_status` — trong v3 field này là `document_status` (first-class trên AC Asset, không có prefix `custom_`):
```sql
-- HIỆN TẠI (broken):
SUM(CASE WHEN IFNULL(a.custom_document_status,'') = 'Compliant' ...)

-- ĐÚNG (v3):
SUM(CASE WHEN IFNULL(a.document_status,'') = 'Compliant' ...)
```

**Impact:** `get_compliance_by_dept()` endpoint sẽ crash với `Table 'tabAsset' doesn't exist` khi không có ERPNext.

---

#### IMM-04 Search Helper — DocType mapping sai

**`api/imm04.py` dòng 840:**
```python
# HIỆN TẠI (broken):
"Supplier": {
    "label_field": "supplier_name",
    ...
},
"Department": {
    "label_field": "department_name",
    ...
},

# ĐÚNG (v3):
"AC Supplier": {
    "label_field": "supplier_name",
    ...
},
"AC Department": {
    "label_field": "department_name",
    ...
},
```

**Impact:** Autocomplete field `vendor` và `department` trên form commissioning sẽ query sai DocType → không có data hoặc crash.

---

#### DocType `asset_document` — Link sai Department

**`asset_document.json` field `clinical_dept`:**
```json
{
  "fieldname": "clinical_dept",
  "fieldtype": "Link",
  "options": "Department"   ← ERPNext Department
}
```

**Phải sửa thành:**
```json
{
  "options": "AC Department"
}
```

**Impact:** Link field không resolve được, dropdown trống khi không có ERPNext.

---

#### DocType `pm_checklist_template` — Link sai Asset Category

**`pm_checklist_template.json` field `asset_category`:**
```json
{
  "fieldname": "asset_category",
  "options": "Asset Category"   ← ERPNext Asset Category
}
```

**Phải sửa thành:**
```json
{
  "options": "AC Asset Category"
}
```

**Impact:** PM Checklist Template không link được loại thiết bị đúng.

---

### 2.3 Tóm tắt BE Code

| Module | API | Service | DocTypes | Trạng thái |
|---|---|---|---|---|
| IMM-04 | ⚠️ (search helper DocType sai) | ✅ | ✅ | Sửa nhỏ |
| IMM-05 | ❌ (2 raw SQL + custom_ prefix) | — | ⚠️ (clinical_dept) | Sửa quan trọng |
| IMM-08 | ✅ | ✅ | ⚠️ (pm_checklist_template) | Sửa nhỏ |
| IMM-09 | ✅ | ✅ | ✅ | Sẵn sàng |
| IMM-11 | Chưa có api/imm11.py | Chưa có | Chưa có | Chưa build |
| IMM-12 | Chưa có api/imm12.py | Chưa có | ✅ incident_report | Chưa build |

**Mức độ nghiêm trọng BE:**
- ❌ **Blocker**: `api/imm05.py` SQL queries (`tabAsset` + `custom_document_status`) — crash ngay
- ⚠️ **High**: `api/imm04.py` search helper Supplier/Department mapping
- ⚠️ **Medium**: `asset_document.json` → Department, `pm_checklist_template.json` → Asset Category

---

## 3. Docs — Phân tích tương thích

### 3.1 IMM-04 Docs

| File | Tình trạng | Chi tiết vấn đề |
|---|---|---|
| `IMM-04_Technical_Design.md` | ⚠️ Cũ | Dòng 34: "ERPNext Asset insert" → phải là "AC Asset" · Dòng 260: `IMM Asset Profile on_update` hook (bị xóa trong v3) |
| `IMM-04_Module_Overview.md` | ⚠️ Cũ | Mô tả luồng tạo ERPNext Asset, không đề cập AC Asset |
| `IMM-04_Functional_Specs.md` | ⚠️ Nhẹ | User stories vẫn đúng logic, chỉ cần update tên DocType |
| `IMM-04_API_Interface.md` | ⚠️ Cũ | Endpoint signatures cần verify với v3 utils/_ok/_err |
| `IMM-04_UAT_Script.md` | ⚠️ Cũ | Test data dùng ERPNext Asset ID, phải thay bằng `AC-ASSET-*` |

---

### 3.2 IMM-05 Docs

| File | Tình trạng | Chi tiết vấn đề |
|---|---|---|
| `IMM-05_Technical_Design.md` | ❌ Lỗi | Không đề cập breaking change `tabAsset` → `tabAC Asset`, không có field `document_status` trên AC Asset |
| `IMM-05_Module_Overview.md` | ⚠️ Cũ | References ERPNext `Location` thay vì `AC Location` |
| `IMM-05_API_Interface.md` | ⚠️ Cũ | `get_compliance_by_dept` không phản ánh broken SQL đã biết |

---

### 3.3 IMM-08 Docs

| File | Tình trạng | Chi tiết vấn đề |
|---|---|---|
| `IMM-08_Technical_Design.md` | ✅ Khá tốt | DocType links đúng AC Asset. Chỉ cần update `pm_checklist_template → AC Asset Category` |
| `IMM-08_Functional_Specs.md` | ✅ | Logic đúng |
| `IMM-08_UAT_Script.md` | ⚠️ Nhẹ | Asset ID format cần update thành `AC-ASSET-*` |

---

### 3.4 IMM-09 Docs

| File | Tình trạng | Chi tiết vấn đề |
|---|---|---|
| `IMM-09_Technical_Design.md` | ⚠️ Cũ | Dòng 388: "Migrate từ v1 (extend ERPNext Asset Repair) sang v2" — lịch sử cũ, cần update thành v3 context |
| Còn lại | ✅ | Logic sửa chữa đúng, không phụ thuộc ERPNext |

---

### 3.5 IMM-11 Docs — CRITICAL: Nhiều lỗi nhất

| File | Tình trạng | Chi tiết vấn đề |
|---|---|---|
| `IMM-11_Technical_Design.md` | ❌ **Sai hoàn toàn** | Dùng `custom_imm_last_calibration_date`, `custom_imm_next_calibration_date`, `custom_imm_calibration_status` xuyên suốt **10+ chỗ** |

**Danh sách field sai trong IMM-11_Technical_Design.md:**

| Dòng | Field sai (v2) | Field đúng (v3 — AC Asset first-class) |
|---|---|---|
| 56–58 | `custom_imm_last_calibration_date` | `last_calibration_date` |
| 56–58 | `custom_imm_next_calibration_date` | `next_calibration_date` |
| 56–58 | `custom_imm_calibration_status` | `calibration_status` |
| 259–261 | Cả 3 fields trên | Như trên |
| 393–402 | Query `AC Asset` bằng `custom_imm_next_calibration_date` | `next_calibration_date` |
| 409, 459 | `set_value("AC Asset", ..., "custom_imm_calibration_status", ...)` | `"calibration_status"` |
| 424–426 | 3 fields | 3 fields first-class |
| 645, 739–743 | Tất cả `custom_imm_*` calibration | First-class equivalents |

**Impact:** Nếu code IMM-11 được viết theo doc này → tất cả `frappe.db.set_value` và queries sẽ fail vì các `custom_imm_*` columns đã bị xóa khỏi tabAsset (và tabAC Asset không có prefix `custom_`).

---

### 3.6 IMM-12 Docs

| File | Tình trạng | Chi tiết vấn đề |
|---|---|---|
| `IMM-12_Technical_Design.md` | ⚠️ Cũ | Dòng 43, 177: `update_asset_lifecycle_status()` → phải là `transition_asset_status()` (v3 rename) |
| `IMM-12_Module_Overview.md` | ⚠️ | Không đề cập `Incident Report` DocType (đã tạo trong v3) |
| `IMM-12_Functional_Specs.md` | ✅ | Logic đúng |

---

### 3.7 Tóm tắt Docs

| Module | Overview | Tech Design | Functional | API | UAT |
|---|---|---|---|---|---|
| IMM-04 | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ |
| IMM-05 | ⚠️ | ❌ | ✅ | ⚠️ | ⚠️ |
| IMM-08 | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| IMM-09 | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| IMM-11 | ⚠️ | ❌ | ⚠️ | ⚠️ | ❌ |
| IMM-12 | ⚠️ | ⚠️ | ✅ | ✅ | ✅ |

---

## 4. Danh sách Fix ưu tiên

### Priority 1 — Blocker (phải fix trước khi chạy)

| # | File | Vấn đề | Fix |
|---|---|---|---|
| B-01 | `api/imm05.py:338` | `FROM \`tabAsset\`` | Thay bằng `FROM \`tabAC Asset\`` |
| B-02 | `api/imm05.py:411` | `FROM \`tabAsset\`` | Thay bằng `FROM \`tabAC Asset\`` |
| B-03 | `api/imm05.py:338,411` | `custom_document_status` | Thay bằng `document_status` |
| B-04 | `docs/imm-11/IMM-11_Technical_Design.md` | 10+ chỗ `custom_imm_*` calibration fields | Update toàn bộ thành first-class field names |

### Priority 2 — High (chạy được nhưng logic sai)

| # | File | Vấn đề | Fix |
|---|---|---|---|
| H-01 | `api/imm04.py:840` | `"Supplier"`, `"Department"` DocType | Đổi thành `"AC Supplier"`, `"AC Department"` |
| H-02 | `asset_document.json` | `clinical_dept → Department` | Đổi thành `AC Department` |
| H-03 | `pm_checklist_template.json` | `asset_category → Asset Category` | Đổi thành `AC Asset Category` |
| H-04 | `docs/imm-12/IMM-12_Technical_Design.md:43,177` | `update_asset_lifecycle_status()` | Đổi thành `transition_asset_status()` |

### Priority 3 — Medium (docs không block code, cần sync)

| # | File | Vấn đề | Fix |
|---|---|---|---|
| M-01 | `docs/imm-04/IMM-04_Technical_Design.md:34` | "ERPNext Asset insert" | Cập nhật thành "AC Asset" |
| M-02 | `docs/imm-04/IMM-04_Technical_Design.md:260` | `IMM Asset Profile on_update` hook | Xóa — hook này đã bỏ trong v3 |
| M-03 | `docs/imm-05/IMM-05_Technical_Design.md` | SQL không phản ánh fix B-01..03 | Cập nhật sau khi fix code |
| M-04 | `docs/imm-11/IMM-11_UAT_Script.md` | Test cases dùng `custom_imm_*` fields | Rewrite với first-class field names |
| M-05 | Tất cả `*_UAT_Script.md` | Asset ID format `AST-xxxxx` | Đổi thành `AC-ASSET-*` |
| M-06 | `docs/imm-12/IMM-12_Module_Overview.md` | Không đề cập `Incident Report` DocType | Thêm mô tả DocType mới |

---

## 5. Module chưa build (IMM-11, IMM-12 BE)

| Module | Docs | BE Code | Trạng thái |
|---|---|---|---|
| IMM-11 (Calibration) | ⚠️ Có nhưng lỗi field names | ❌ Không có `api/imm11.py`, `services/imm11.py` | Phải rebuild docs trước rồi mới code |
| IMM-12 (Incident/CM) | ⚠️ Cần update | ❌ Không có `api/imm12.py`, `services/imm12.py` (chỉ có `incident_report.py` controller) | Cần tạo service + API layer |

**IMM-11 phụ thuộc AC Asset fields:**
```python
# Đúng (v3 — first-class fields trên AC Asset):
frappe.db.set_value("AC Asset", asset, {
    "last_calibration_date": basis_date,
    "next_calibration_date": next_date,
    "calibration_status": "On Schedule",
})

# Sai (v2 — custom_imm_ đã bị xóa):
frappe.db.set_value("AC Asset", asset, {
    "custom_imm_last_calibration_date": basis_date,
    ...
})
```

---

## 6. Kết luận

### Mức độ tương thích tổng thể

| Layer | Tương thích | Ghi chú |
|---|---|---|
| BE — IMM-04 | 90% ✅ | 1 fix nhỏ (search helper) |
| BE — IMM-05 | 60% ⚠️ | 2 SQL blocker + 1 DocType JSON |
| BE — IMM-08 | 95% ✅ | 1 fix nhỏ (pm_checklist_template) |
| BE — IMM-09 | 98% ✅ | Gần như sẵn sàng |
| BE — IMM-11 | 0% ❌ | Chưa build |
| BE — IMM-12 | 40% ⚠️ | Có incident_report, thiếu service + API |
| Docs — IMM-04 | 70% ⚠️ | Tech Design cần update |
| Docs — IMM-05 | 55% ⚠️ | Technical Design broken |
| Docs — IMM-08 | 90% ✅ | Chỉ UAT cần update |
| Docs — IMM-09 | 85% ✅ | Tốt |
| Docs — IMM-11 | 20% ❌ | Phải rewrite Tech Design |
| Docs — IMM-12 | 75% ⚠️ | Function name rename |

### Thứ tự ưu tiên hành động

```
1. Fix BE blocker: api/imm05.py (SQL + custom_ prefix)        [1 ngày]
2. Fix BE high:    api/imm04.py + 2 DocType JSONs              [2 giờ]
3. Rewrite docs:   IMM-11_Technical_Design.md (critical)       [4 giờ]
4. Update docs:    IMM-12_Technical_Design.md (function rename) [1 giờ]
5. Build BE:       api/imm11.py + services/imm11.py            [3 ngày]
6. Build BE:       api/imm12.py + services/imm12.py            [2 ngày]
7. Update UAT:     Tất cả *_UAT_Script.md (AC-ASSET- prefix)   [2 giờ]
```

### Go/No-Go Wave 1

| Module | Go? | Điều kiện |
|---|---|---|
| IMM-04 | ✅ Go | Fix H-01 (search helper) |
| IMM-05 | ⚠️ Fix trước | Fix B-01/B-02/B-03/H-02 |
| IMM-08 | ✅ Go | Fix H-03 (pm_checklist_template JSON) |
| IMM-09 | ✅ Go | Sẵn sàng |
| IMM-11 | ❌ No-Go | Rewrite docs → build BE |
| IMM-12 | ⚠️ Partial | Incident Report có, thiếu full service/API |
