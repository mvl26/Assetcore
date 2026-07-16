# IMM-09 — API Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | **IMM-09 — Corrective Maintenance / Repair** |
| Phiên bản tài liệu | 1.0 |
| Ngày cập nhật | 2026-05-14 |
| Trạng thái | Chuẩn hóa từ IMM-09_API_Interface.md |
| Base path | `assetcore.api.imm09` |
| URL pattern | `/api/method/assetcore.api.imm09.<function>` |

---

## §1 Tổng quan

### §1.1 Response Envelope

**Thành công:**

```json
{
  "success": true,
  "data": { /* payload */ }
}
```

**Lỗi:**

```json
{
  "success": false,
  "error": "Thông báo lỗi tiếng Việt",
  "code": "CM-XXX"
}
```

> Helpers `_ok(data)` / `_err(code, msg)` tại `assetcore/utils/helpers.py`.
> Frappe wraps toàn bộ phản hồi trong `message`. FE parse: `response.json().message`.

### §1.2 Authentication

| Phương thức | Header / Cookie |
|---|---|
| API Token | `Authorization: token <api_key>:<api_secret>` |
| Session (FE SPA) | `Cookie: sid=<session_id>` |

User không có Role hợp lệ → HTTP 403 + `CM-010`.

### §1.3 Phân trang

```json
{
  "data": [ /* items */ ],
  "pagination": { "page": 1, "page_size": 20, "total": 137, "total_pages": 7 }
}
```

`page` 1-based, `page_size` mặc định 20.

### §1.4 API Catalog

| # | Function | Method | Permission | Mô tả |
|---|---|---|---|---|
| 3.1 | `list_repair_work_orders` | GET | Tất cả có đăng nhập | Danh sách WO + filter + phân trang (+ `mine=1` self-scope `assigned_to` — tab "Phiếu CM của tôi" MVP-5b; + `search` OR-LIKE `name`/`asset_code`/`asset_name` toàn tập — CR-18/BR-09-LISTSEARCH) |
| 3.2 | `get_repair_work_order` | GET | Tất cả có đăng nhập | Chi tiết WO + asset_info enriched |
| 3.3 | `create_repair_work_order` | POST | Workshop Manager / CMMS Admin | Tạo WO mới |
| 3.4 | `assign_technician` | POST | Workshop Manager | Phân công Kỹ thuật viên |
| 3.5 | `submit_diagnosis` | POST | KTV HTM | Nộp chẩn đoán |
| 3.6 | `request_spare_parts` | POST | KTV HTM / Kho | Cập nhật stock_entry_ref |
| 3.7 | `start_repair` | POST | KTV HTM | Bắt đầu sửa chữa |
| 3.8 | `close_work_order` | POST | KTV HTM / Workshop Manager | Đóng WO → Pending Inspection (Completed) hoặc Cannot Repair |
| 3.9 | `confirm_inspection` | POST | Dept Head / QA Officer | Nghiệm thu: Pending Inspection → Completed (submit docstatus=1) |
| 3.10 | `get_repair_kpis` | GET | PTP / Manager | KPI tháng hiện tại |
| 3.11 | `get_mttr_report` | GET | PTP / Manager | MTTR trend + breakdown 6 tháng |
| 3.12 | `search_spare_parts` | GET | KTV HTM | Tìm kiếm vật tư (Item) |
| 3.13 | `get_asset_repair_history` | GET | Tất cả có đăng nhập | Lịch sử sửa chữa 1 thiết bị |

---

## §2 Whitelist & Permission Matrix

| Function | Whitelist | Roles |
|---|---|---|
| `list_repair_work_orders` | `@frappe.whitelist()` | All authenticated |
| `get_repair_work_order` | `@frappe.whitelist()` | All authenticated |
| `create_repair_work_order` | `@frappe.whitelist()` | Workshop Manager, CMMS Admin |
| `assign_technician` | `@frappe.whitelist()` | Workshop Manager |
| `submit_diagnosis` | `@frappe.whitelist()` | KTV HTM, Workshop Manager |
| `request_spare_parts` | `@frappe.whitelist(methods=["POST"])` | KTV HTM, Workshop Manager, Kho vật tư |
| `start_repair` | `@frappe.whitelist(methods=["POST"])` | KTV HTM, Workshop Manager |
| `close_work_order` | `@frappe.whitelist()` | KTV HTM, Workshop Manager, CMMS Admin |
| `attach_repair_checklist_photo` | `@frappe.whitelist(methods=["POST"])` (multipart) | assigned KTV OR `repair.write` (assignee/DocPerm write trên Asset Repair) |
| `get_repair_kpis` | `@frappe.whitelist()` | PTP Khối 2, Workshop Manager, CMMS Admin |
| `get_mttr_report` | `@frappe.whitelist()` | PTP Khối 2, Workshop Manager, CMMS Admin |
| `search_spare_parts` | `@frappe.whitelist()` | KTV HTM, Workshop Manager, Kho vật tư |
| `get_asset_repair_history` | `@frappe.whitelist()` | All authenticated |

---

## §3 Endpoint Specifications

### 3.1 `list_repair_work_orders`

**Mô tả:** Lấy danh sách Asset Repair WO với filter động và phân trang.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.list_repair_work_orders` |

**Query params:**

| Param | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `filters` | JSON string | Không | Filter Frappe-style: exact, `["in",[...]]`, `[">=",val]`, `["like","%x%"]` |
| `mine` | int (`0\|1`) | Không | **`mine=1`** → self-scope `assigned_to == session.user` (tab "Phiếu CM của tôi" — MyWorkOrdersView, MVP-5b). AND với mọi key trong `filters`. **`mine=0`/absent (mặc định 0)** = hành vi cũ BYTE-IDENTICAL (permission-aware — web-FE `RepairWorkOrderListView` KHÔNG đổi). Xem `04_Backend_Design.md §3.6` ADR-IMM09-LISTMINE + mobile ADR-MOBILE-017. |
| `search` | string | Không | default `""`; free-text OR-LIKE trên `name` (mã lệnh CM) / `asset_code` / `asset_name` — case-insensitive, TOÀN tập mọi trang (CR-18 — xem BR-09-LISTSEARCH + ADR-IMM09-SEARCH-01). `""`/absent ⇒ list BYTE-IDENTICAL baseline. AND với `filters`/`mine`/vendor-scope. |
| `page` | int | Không | Trang hiện tại (mặc định 1) |
| `page_size` | int | Không | Kích thước trang (mặc định 20) |

> **📱 Mobile-BE contract (list-element `status`/`priority` enum-parity — CR-08, mobile Trục B, 2026-07-13):** phần tử `data.data[]` được mirror trong OpenAPI mobile [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) schema **`RepairWorkOrderListItem`** (C3-split, 21 field). CR-08 **formal-hoá `enum`** cho 2 property `status` + `priority` (trước round là `type:string` TRẦN → codegen `String` free-form): `status.enum` = 9 giá trị `RepairStatus` VERBATIM `[Open, Assigned, Diagnosing, Pending Parts, In Repair, Pending Inspection, Completed, Cannot Repair, Cancelled]` (**bằng-hệt** precedent `CreateRepairWorkOrderResponse.status`, 1 SoT — KHÔNG chế enum mới), `priority.enum` = `[Normal, Urgent, Emergency]`. Nguồn contract-truthful: `services/imm09.py::list_work_orders` trả `status`/`priority` **CANONICAL** (∈ `_LIST_WO_FIELDS` qua `get_all` — 0 transform; enricher chỉ ĐỌC `status` để derive `sla_paused`). **CONTRACT-ONLY** (0 `.py`/reload/migrate — pure-yaml + test): grounding `set(enum)==set(asset_repair.json Select options)` đọc TRỰC TIẾP doctype; zero-footprint `additionalProperties:false` + `required:['name']` + tổng property 21 GIỮ. Chi tiết + Alternatives: [ADR-MOBILE-037](../mobile/ADR-MOBILE-037.md) + [`04-api-contract.md §6.3`](../mobile/04-api-contract.md).

> **BR-09-LISTMINE (self-scope opt-in):** `mine` là **filter ứng-dụng**, KHÔNG phải hàng-rào-bảo-mật — read-gating GIỮ DocPerm `repair.read` + `permission_query_conditions` `asset_repair_query` (`permissions.py:115`) + `apply_vendor_scope`. Inject `f["assigned_to"]=frappe.session.user` ở API-layer **SAU** `apply_vendor_scope`, **TRƯỚC** `handle(svc.list_work_orders)` (mirror `api/imm08.py::list_pm_work_orders`). Invariant **count==rows**: `count_with_or` + `get_all` (`BaseRepository.list`) dùng CÙNG `filters` dict (đã có `assigned_to`) ⇒ `pagination.total == len(data.data)`. Với KTV thì `asset_repair_query` đã tự scope `assigned_to` (mine thừa nhưng vô hại — AND idempotent); với senior/QA (`asset_repair_query` trả `""` → thấy tất cả) thì `mine=1` thu hẹp về "của tôi" = use-case chính của tab.

> **BR-09-LISTSEARCH (free-text search phía SERVER — CR-18, ĐỐI XỨNG BR-08-17):** param `search` (string, optional) → OR-LIKE `name` (mã lệnh CM = PK `Asset Repair`) / `asset_code` / `asset_name` (2 field trên **AC Asset**, link `asset_ref`), TOÀN tập mọi trang (thay lọc client-side chỉ-trang-đã-tải + gỡ search-trap).
> - **Điểm inject:** discrete param → `api/imm09.py::list_repair_work_orders` inject `f["search"]=search.strip()` **CHỈ khi** non-empty, **SAU** `apply_vendor_scope` + `mine` (đối xứng `mine`). Trống ⇒ KHÔNG đụng `f` ⇒ byte-identical.
> - **Dịch → `or_filters` @service:** `services/imm09.py::list_work_orders` gọi SSoT `pop_search(base, ["name"], link_search={"asset_ref": ("AC Asset", ["asset_code","asset_name"])})` **TRƯỚC** `_normalize_filters`/`_apply_open_drill` (tránh `Unknown column 'tabAsset Repair.search'`). Trả `["name","like","%<esc>%"]` (PK CM) + `["asset_ref","in",<AC Asset khớp asset_code/asset_name/name>]` (resolve 1 lần, cap 500).
> - **Escape (SSoT `escape_like_term`):** `%`→`\%`, `_`→`\_` trước bọc `%…%`, áp CẢ `name` LẪN link-lookup ⇒ khớp literal, chống wildcard-injection/DoS.
> - **AND-combine KHÔNG nới quyền:** `search` AND với `status`/`priority`/`asset_ref`/`open_repair_filter` + `mine`(`assigned_to`) + vendor-scope(`asset_ref IN […]`). KTV `mine=1`/Vendor KHÔNG thấy phiếu ngoài scope dù khớp `search`. Link-lookup AC Asset `ignore_permissions=True` chỉ resolve id text-match; phạm vi phiếu VẪN do `filters`+`permission_query`/vendor.
> - **INVARIANT count==rows:** `or_filters` (id link đã resolve) dựng 1 lần → thread CÙNG cho `count_with_or`(`get_list`)+`get_all` ⇒ `pagination.total == số phiếu thực khớp` mọi trang (test `page_size` nhỏ vẫn đúng tổng). KHÔNG resolve id riêng cho count vs rows.
> - **⚠ VERIFY BE Bước-4 (bất đối xứng PQC rows-vs-count — như PM):** rows = `frappe.get_all` (KHÔNG áp `permission_query_conditions`) vs count = `count_with_or`→`frappe.get_list` (CÓ áp `asset_repair_query` = `assigned_to==user`). Read-all persona khớp; **vendor** (`apply_vendor_scope` inject `asset_ref IN […]` KHÁC predicate pqc `assigned_to`) có thể count < rows + rò phiếu ngoài `assigned_to` (latent baseline, không do CR-18). BE chốt: rows cũng qua `get_list` (áp pqc) HOẶC canh explicit-filter khớp pqc; thêm regression count==rows persona vendor (search rỗng + có search). Nếu là bug baseline → tách finding riêng, KHÔNG mở rộng scope CR-18.
> - **Nhánh live `sla_breached_live`:** `search` pop TRƯỚC rẽ nhánh; `or_filters` forward vào `_fetch_all_repair_rows`/`_list_sla_breached_live` để chip "Quá hạn SLA" + search compose đúng, count==rows giữ trong tập lọc live.
> - **Recall cap 500 asset/term** → count==rows vẫn giữ (chung id đã cap), recall giảm = `[ROADMAP]` streaming (ADR-IMM00-LIST-SCOPE §4b).

#### ADR-IMM09-SEARCH-01: `search` discrete param + `pop_search`/`escape_like_term` SSoT (CR-18)

- **Status**: Accepted — Date 2026-07-10. Đối xứng PM `ADR-IMM08-SEARCH-01` + tái dùng `ADR-IMM00-SEARCH-ESCAPE`; dùng CHUNG `pop_search`/`escape_like_term`/`BaseRepository.list(or_filters)`.
- **Context**: FE `CMWorkOrderListView` lọc client-side chỉ trang đã tải (`filteredWOs`) → KTV bỏ sót phiếu trang sau. `asset_code`/`asset_name` trên AC Asset (link `asset_ref`). Ràng buộc: count==rows, byte-identical baseline khi trống, KHÔNG nới quyền, chống wildcard-injection/DoS.
- **Decision**: 1 discrete query-param `search` (default `""`) → inject `f["search"]` @api khi non-empty → `pop_search` @service → `or_filters` (parent `name` + link-lookup AC Asset) đã escape → `RepairRepo.list(or_filters=…)` thread chung count+rows.
- **Alternatives**: (A) client-filter → search-trap không sửa được → loại. (B) raw `%term%` không escape → wildcard-injection/DoS → loại. (C) endpoint `search_repair_work_orders` riêng → +1 path, nhân đôi enrich/scope → loại. (D) full-text MATCH…AGAINST → schema migration + đổi count semantics → `[ROADMAP]`.
- **Consequences**: blast-radius = 1 param @api + 1 nhánh `pop_search` @service + forward `or_filters` vào nhánh `sla_breached_live`; count==rows giữ; backward-compat khi trống; recall cap 500 = `[ROADMAP]`; `search` là filter ứng-dụng (bảo mật read vẫn do DocPerm/`asset_repair_query`+vendor-scope).

> **DELTA vòng này (CR-18):** (1) Query-params table thêm `search`; (2) BR-09-LISTSEARCH + ADR-IMM09-SEARCH-01 mới. **BE Bước-4:** `api/imm09.py::list_repair_work_orders(filters, mine, search: str = "", page, page_size)` (inject `f["search"]` khi non-empty); `services/imm09.py::list_work_orders` (pop `search`→`or_filters` qua `pop_search` TRƯỚC `_normalize_filters`, forward vào `_list_sla_breached_live`); `services/shared/filters.py::pop_search` (escape + list display-field); `api/openapi_overrides.py` (khai `search` cho `list_repair_work_orders` + mirror `docs/mobile/openapi/*.yaml`); tests `test_imm09` (count==rows-paginated + escape-literal + AND-vendor/mine + byte-identical-empty). **FE Bước-4:** `CMWorkOrderListView.vue` (server refetch debounce+reset page=1, gỡ `filteredWOs`+search-trap, giữ chip); `api/imm09.ts::listRepairWorkOrders` (+`search`); `stores/imm09.ts::fetchWorkOrders` (forward `search`).

**Ví dụ request:**

```bash
curl -G "https://acme.local/api/method/assetcore.api.imm09.list_repair_work_orders" \
  -H "Authorization: token KEY:SECRET" \
  --data-urlencode 'filters={"status":["in",["Open","Assigned"]],"priority":"Urgent"}' \
  --data-urlencode 'page=1' --data-urlencode 'page_size=20'
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "data": [
      {
        "name": "WO-CM-2026-00042",
        "asset_ref": "AC-ASSET-2026-00042",
        "asset_name": "Máy thở Drager Evita V800",
        "repair_type": "Corrective",
        "priority": "Urgent",
        "status": "Pending Parts",
        "open_datetime": "2026-04-14 07:15:00",
        "completion_datetime": null,
        "mttr_hours": null,
        "sla_breached": 0,
        "is_sla_breached": false,
        "parts_hold_hours": 12.5,
        "sla_paused": true,
        "is_repeat_failure": 0,
        "assigned_to": "ktv.anha@hospital.vn",
        "root_cause_category": "Electrical",
        "risk_class": "Class III"
      }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
  }
}
```

**Fields trả về:** `name`, `asset_ref`, `asset_name`, `repair_type`, `priority`, `status`, `open_datetime`, `completion_datetime`, `mttr_hours`, `sla_breached`, `is_sla_breached` *(derive live — BR-09-07 LIVE: `bool(sla_breached) or _row_is_live_overdue`; BR-09-10: elapsed clock-stop ⇒ WO ở Pending Parts KHÔNG live-overdue oan)*, `parts_hold_hours` *(tổng giờ đã hold — BR-09-10)*, `sla_paused` *(derive: `status == "Pending Parts"` ⇒ SLA đang tạm dừng; FE hiện badge "Chờ phụ tùng — SLA tạm dừng")*, `is_repeat_failure`, `assigned_to`, `root_cause_category`, `risk_class`, `sla_target_hours`.

> **BR-09-10 (clock-stop):** `mttr_hours` BE gửi đã trừ thời gian Pending Parts (`= (completion−open) − parts_hold_hours`). FE render **verbatim** — KHÔNG tự tính lại từ `open_datetime`/`completion_datetime` (transport-agnostic). `parts_hold_started` là field nội bộ (chỉ phục vụ tính toán BE) — KHÔNG cần expose ra API list.

---

### 3.2 `get_repair_work_order`

**Mô tả:** Chi tiết đầy đủ 1 WO, bao gồm `asset_info` enriched từ AC_Asset.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.get_repair_work_order` |

**Query params:** `?name=WO-CM-2026-00042`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "asset_ref": "AC-ASSET-2026-00042",
    "asset_name": "Máy thở Drager Evita V800",
    "asset_category": "Ventilator",
    "risk_class": "Class III",
    "serial_no": "DRG-2024-001234",
    "incident_report": "IR-2026-00123",
    "source_pm_wo": null,
    "repair_type": "Corrective",
    "priority": "Urgent",
    "status": "In Repair",
    "open_datetime": "2026-04-14 07:15:00",
    "assigned_datetime": "2026-04-14 08:30:00",
    "sla_target_hours": 24.0,
    "mttr_hours": null,
    "sla_breached": 0,
    "is_sla_breached": false,
    "parts_hold_hours": 0.0,
    "sla_paused": false,
    "is_repeat_failure": 0,
    "assigned_to": "ktv.anha@hospital.vn",
    "diagnosis_notes": "Tụ điện C12 phồng và cháy",
    "root_cause_category": "Electrical",
    "spare_parts_used": [
      {
        "item_code": "CAP-100UF-25V",
        "qty": 2,
        "unit_cost": 25000,
        "total_cost": 50000,
        "stock_entry_ref": "STE-2026-00456"
      }
    ],
    "repair_checklist": [],
    "firmware_updated": 0,
    "asset_info": {
      "asset_name": "Máy thở Drager Evita V800",
      "asset_category": "Ventilator",
      "lifecycle_status": "Under Repair",
      "risk_classification": "Class III",
      "manufacturer_sn": "DRG-2024-001234",
      "department": "ICU-01",
      "location": "LOC-A3"
    },
    "allowed_transitions": ["Pending Inspection", "Cannot Repair", "Cancelled"]
  }
}
```

**`allowed_transitions[]` (server-driven CTA — mirror Incident R3 / PM R21):** danh sách **trạng-thái-kế hợp lệ** từ `status` hiện tại (ở ví dụ trên `status="In Repair"` → `[Pending Inspection, Cannot Repair, Cancelled]`). FE render nút workflow trên màn repair-detail **theo field này** — KHÔNG hardcode `status → button`. SSoT = `_REPAIR_VALID_TRANSITIONS` (`services/imm09.py`), grounded edge-by-edge `imm_09_repair_workflow.json` (9 state / 15 transition). Terminal `Completed`/`Cannot Repair`/`Cancelled` → `[]` (read-only, không nút). Field **optional** (emit-luôn nhưng KHÔNG trong `required`); client cũ bỏ qua an toàn. Chi tiết map + ADR-IMM09-CTA: xem `04_Backend_Design.md §3.1`.

| `status` | `allowed_transitions[]` |
|---|---|
| Open | `[Assigned, Cancelled]` |
| Assigned | `[Diagnosing, Cancelled]` |
| Diagnosing | `[In Repair, Pending Parts, Cancelled]` |
| Pending Parts | `[In Repair, Cancelled]` |
| In Repair | `[Pending Inspection, Cannot Repair, Cancelled]` |
| Pending Inspection | `[Completed, In Repair, Cancelled]` |
| Completed / Cannot Repair / Cancelled | `[]` (terminal) |

**Lỗi:** `CM-011` (404) nếu WO không tồn tại.

---

### 3.3 `create_repair_work_order`

**Mô tả:** Tạo mới Asset Repair WO, validate nguồn (BR-09-01), kiểm tra duplicate (BR-09-05), tính SLA target, tạo Asset Lifecycle Event `repair_opened`.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.create_repair_work_order` |

**Request body:**

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `asset_ref` | string | Có | Link đến AC_Asset |
| `repair_type` | string | Có | `"Corrective"` / `"Emergency"` / `"Warranty"` |
| `priority` | string | Có | `"Normal"` / `"Urgent"` / `"Emergency"` |
| `failure_description` | string | Có | Mô tả sự cố ban đầu |
| `incident_report` | string | Có* | Link đến Incident Report (bắt buộc nếu không có `source_pm_wo`) |
| `source_pm_wo` | string | Có* | Link đến PM Work Order nguồn (bắt buộc nếu không có `incident_report`) |

\* Phải có ít nhất một trong hai.

```json
{
  "asset_ref": "AC-ASSET-2026-00042",
  "repair_type": "Corrective",
  "priority": "Urgent",
  "failure_description": "Máy thở không tạo được áp suất, báo alarm E-04",
  "incident_report": "IR-2026-00123",
  "source_pm_wo": ""
}
```

**Side-effects:**
1. Validate BR-09-01 (nguồn) + BR-09-05 (kiểm tra duplicate WO active).
2. Tính `sla_target_hours` qua `get_sla_target(risk_class, priority)`.
3. Insert Asset Repair với `status = "Open"`, `open_datetime = now()`.
4. `frappe.db.set_value("Asset", asset_ref, "status", "Under Repair")`.
5. Tạo Asset Lifecycle Event `event_type = "repair_opened"`.
6. `frappe.db.commit()`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Open",
    "sla_target_hours": 24.0
  }
}
```

**Lỗi:**

| Code | Mô tả |
|---|---|
| `CM-001` | Thiếu cả `incident_report` và `source_pm_wo` |
| `CM-002` | Asset đã có WO active |
| `CM-009` | `asset_ref` không tồn tại |
| `CM-014` | `incident_report` truyền non-empty nhưng không tồn tại (R26, `code='VALIDATION_ERROR'` http 422). FK rỗng = standalone OK. |
| `CM-015` | `source_pm_wo` truyền non-empty nhưng không tồn tại (R26, `code='VALIDATION_ERROR'` http 422). FK rỗng = standalone OK. |

---

### 3.4 `assign_technician`

**Mô tả:** Phân công KTV cho WO đang ở trạng thái `Open`.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.assign_technician` |

**Request body:**

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `name` | string | Có | WO name |
| `technician` | string | Có | Email KTV |
| `priority` | string | Không | Override priority nếu cần |

```json
{
  "name": "WO-CM-2026-00042",
  "technician": "ktv.anha@hospital.vn",
  "priority": "Urgent"
}
```

**Side-effects:**
- Chỉ thực hiện khi `status = "Open"`.
- **Dispatch-validation gate (R25):** `technician` PHẢI thoả 3 điều kiện AND — (1) tồn tại trong DocType `User`, (2) `enabled == 1`, (3) repair-capable (`frappe.has_permission("Asset Repair", "write", user=technician)` — capability, KHÔNG so tên role). Gate chạy TRƯỚC khi set/save.
- Nếu hợp lệ: Set `assigned_to`, `assigned_by = frappe.session.user`, `assigned_datetime = now()`, `status = "Assigned"`.
- Nếu KHÔNG hợp lệ: KHÔNG mutate (`assigned_to` giữ nguyên, `status` GIỮ `Open`).

**Response 200 (thành công):**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Assigned",
    "assigned_to": "ktv.anha@hospital.vn"
  }
}
```

**Response 200 (technician không hợp lệ — Error-on-HTTP-200):**

```json
{
  "success": false,
  "error": "Không thể giao việc cho 'khong-ton-tai@nope.invalid' — tài khoản không tồn tại, đã bị khoá, hoặc không có quyền sửa chữa.",
  "code": "VALIDATION_ERROR",
  "http_status": 422
}
```

**Lỗi:**
- `IMM09-BAD-STATE` (`code=BAD_STATE`, 409) nếu status không phải `"Open"`.
- `IMM09-INVALID-TECHNICIAN` (`code=VALIDATION_ERROR`, 422) nếu technician không tồn tại / disabled / không có quyền sửa chữa (R25 dispatch-validation gate).

> **Mobile-BE contract:** path tương ứng có trong `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (opId `assignTechnician`) — response 3-key `{name,status,assigned_to}` qua `AssignTechnicianEnvelope` RIÊNG (KHÔNG reuse `RepairActionEnvelope` 2-key). Lỗi nghiệp vụ (gồm `IMM09-INVALID-TECHNICIAN`) đến HTTP-200 + nhánh `Error` của `200 = oneOf [AssignTechnicianEnvelope, Error]` (KHÔNG schema mới). Quyết định thiết kế: ADR-IMM09-ASSIGN (DISPATCH) + ADR-IMM09-VALIDATE-TECH (validation gate) — file `04_Backend_Design.md` §3.2/§3.3.

---

### 3.5 `submit_diagnosis`

**Mô tả:** KTV nộp kết quả chẩn đoán — xác định nguyên nhân gốc rễ và nhu cầu vật tư.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.submit_diagnosis` |

**Request body:**

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `name` | string | Có | WO name |
| `diagnosis_notes` | string | Có | Mô tả kỹ thuật chẩn đoán |
| `needs_parts` | int | Có | `1` = cần vật tư (→ Pending Parts), `0` = không cần (→ In Repair) |

```json
{
  "name": "WO-CM-2026-00042",
  "diagnosis_notes": "Tụ điện C12 trên board nguồn bị phồng và cháy. Thay tương đương CAP-100UF-25V.",
  "needs_parts": 1
}
```

**Side-effects:**
- Chỉ thực hiện khi `status IN ("Assigned", "Diagnosing")` — sai trạng thái → `IMM09_BAD_STATE` (`http_status 409`/`code CONFLICT`, `services/imm09.py:935`); WO không tồn tại → `IMM09_NOT_FOUND` (`http_status 404`/`code NOT_FOUND`). Cả 2 là **lỗi-nghiệp-vụ trên HTTP-200 + Error envelope** (route theo `body.http_status`).
- Set `diagnosis_notes` (`services/imm09.py:937` — chỉ field này; **KHÔNG** set `root_cause_category` ở action này).
- Nếu `needs_parts = 1` → `status = "Pending Parts"` **+ `enter_parts_hold(doc)`: stamp `parts_hold_started = now()` (BR-09-10, INV-CM-HOLD-2) + ALE `parts_hold_started`** (SLA bắt đầu tạm dừng, `services/imm09.py:941-942`).
- Nếu `needs_parts = 0` → `status = "In Repair"` (`services/imm09.py:938`).
- Sinh ALE `event_type = "diagnosis_submitted"` (`services/imm09.py:945`).
- Service trả EXACT `{name, status}` (`services/imm09.py:950`) — Mobile-BE contract REUSE `RepairActionEnvelope`/`RepairActionResponse` (mirror `startRepair`; xem [`docs/mobile/04-api-contract.md §8.11-bis`](../mobile/04-api-contract.md)).

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Pending Parts"
  }
}
```

**Lỗi:** `CM-012` (status không hợp lệ cho transition) ⇒ MSG `IMM09_BAD_STATE` (`http_status 409`/`code CONFLICT`, `utils/messages.py:641-646`); WO không tồn tại ⇒ `IMM09_NOT_FOUND` (`http_status 404`/`code NOT_FOUND`). Lỗi-nghiệp-vụ = **in-handler HTTP-200 + Error envelope** (KHÔNG raise→HTTP-4xx).

---

### 3.6 `request_spare_parts`

**Mô tả:** Gắn phiếu xuất kho (`stock_entry_ref`) vào các dòng vật tư của WO.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.request_spare_parts` |

**Request body:**

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `name` | string | Có | WO name |
| `parts` | JSON string | Có | List `[{"item_code": "...", "stock_entry_ref": "..."}]` |

```json
{
  "name": "WO-CM-2026-00042",
  "parts": "[{\"item_code\":\"CAP-100UF-25V\",\"stock_entry_ref\":\"STE-2026-00456\"}]"
}
```

**Side-effects:**
- Cập nhật `stock_entry_ref` trên các row `spare_parts_used` khớp `item_code` (đếm `updated`).
- Nếu `status = "Pending Parts"` → **`exit_parts_hold(doc, until=now())`: cộng `parts_hold_hours += (now − parts_hold_started)`, reset `parts_hold_started=null` (BR-09-10, INV-CM-HOLD-2/3) + ALE `parts_hold_resumed`** (SLA tiếp tục chạy) → chuyển sang `"In Repair"`.
- **Gate-2 IMM-09 → IMM-15 (cross-module, non-blocking):** tạo `IMM Spare Allocation` trạng thái `Requested` để spare-part truy về kho (`services/imm09.py:991-1016`, lazy-import `imm15.create_allocation` — Pattern B). CHỈ tạo khi có item (`spare_part`/`item_code`) **và** tìm được `warehouse` từ `AC Spare Part Stock`. Bọc `try/except` → thất bại chỉ `frappe.log_error`, KHÔNG vỡ action. `allocation` = name allocation mới (hoặc `null`).

> Lưu ý: Endpoint chỉ gắn chứng từ, không tạo spare part row mới. Các row phải được thêm qua FE form trước.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "In Repair",
    "updated": 1,
    "allocation": "ALLOC-2026-00017"
  }
}
```

**Trường trả về (EXACT 4-key, grounded `services/imm09.py:1018-1019`):** `name` (string), `status` (RepairStatus 9-state — `In Repair` nếu rời `Pending Parts`, ngược lại giữ nguyên), `updated` (integer — số row gắn được `stock_entry_ref`), `allocation` (string|null — name `IMM Spare Allocation` Gate-2, `null` nếu không tạo).

**Lỗi:** WO không tồn tại ⇒ `IMM09_NOT_FOUND` (`code=NOT_FOUND`, `http_status=404`, `services/imm09.py:976`) — lỗi-nghiệp-vụ = **in-handler HTTP-200 + Error envelope** (KHÔNG raise→HTTP-4xx).

> 📱 **Cross-ref Mobile-BE contract (repair spare-parts sub-flow):** endpoint này được surface trong OpenAPI mobile [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) tại path `/api/method/assetcore.api.imm09.request_spare_parts` (opId **`requestSpareParts`**, **POST-only `@frappe.whitelist(methods=["POST"])` `api/imm09.py:77` SẴN @source — CLEAN POST, KHÔNG verb-divergence/backlog**). 200 = `oneOf [RequestSparePartsEnvelope, Error]` (route-by-VALUE `body.success`, 0 discriminator); `data` = **`RequestSparePartsResponse`** closed 4-key `{name, status, updated, allocation}` (`required[name,status]`; `updated` integer; `allocation` string|null nullable). **⚠️ Schema RIÊNG — KHÔNG reuse `RepairActionResponse` 2-key `{name,status}`** dù cùng domain repair: service trả thêm `updated` + `allocation` (4-key) ⇒ C3-split field-disjoint (Self-Correction: forward-reservation §8.11 contract-doc ghi reuse cho `request_spare_parts` SAI — service THẬT 4-key). **Dual-rbac**: cap-gate `repair.write` (`api/imm09.py:79`) + service `repair.create` (`services/imm09.py:973`) — đều in-handler cap-403 (phủ bởi nhánh Error 200-oneOf). Slot `{200,401,403}`; 403 SINGLE-SHAPE dispatcher-403. `IMM09_NOT_FOUND` (404) arrive HTTP-200 + Error. Chi tiết hợp đồng + ADR: [`docs/mobile/04-api-contract.md §8.23`](../mobile/04-api-contract.md) + [`ADR-MOBILE-010.md`](../mobile/ADR-MOBILE-010.md) + `04_Backend_Design.md §3.5`.

---

### 3.7 `start_repair`

**Mô tả:** Chuyển WO sang trạng thái `In Repair` khi KTV bắt đầu sửa chữa thực tế.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.start_repair` |

**Request body:**

```json
{ "name": "WO-CM-2026-00042" }
```

**Side-effects:**
- Chỉ thực hiện khi `status IN ("Assigned", "Diagnosing", "Pending Parts")`.
- Nếu đang `"Pending Parts"` → **`exit_parts_hold(doc, until=now())` (BR-09-10) chốt khoảng hold + ALE `parts_hold_resumed`** trước khi đổi status.
- Set `status = "In Repair"`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "In Repair"
  }
}
```

**Lỗi:** `CM-012` (status không hợp lệ cho transition) ⇒ MSG `IMM09_BAD_STATE` (`http_status 409`/`code CONFLICT`, `utils/messages.py:641-646`); WO không tồn tại ⇒ `IMM09_NOT_FOUND` (`http_status 404`/`code NOT_FOUND`). Lỗi-nghiệp-vụ = **in-handler HTTP-200 + Error envelope** (KHÔNG raise→HTTP-4xx).

---

### 3.8 `close_work_order`

**Mô tả:** KTV hoàn thành sửa chữa → WO chuyển sang `Pending Inspection` (chờ nghiệm thu cấp khoa). Sau đó cần `confirm_inspection` để chốt "Completed". Mode thứ hai là `Cannot Repair`.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.close_work_order` |

**Request body:**

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `name` | string | Có | WO name |
| `repair_summary` | string | Có* | Tóm tắt kết quả sửa chữa (mode Completed) |
| `root_cause_category` | string | Có* | Phân loại nguyên nhân gốc rễ |
| `dept_head_name` | string | Có* | Họ tên trưởng khoa phòng xác nhận (BR-09-04) |
| `checklist_results` | JSON string | Có* | List `[{idx, test_description, result, measured_value}]` |
| `spare_parts` | JSON string | Không | Cập nhật bổ sung vật tư (list SparePartRow) |
| `firmware_updated` | int | Không | `1` = có cập nhật firmware |
| `firmware_change_request` | string | Không | FCR name (bắt buộc nếu `firmware_updated=1`) |
| `cannot_repair` | int | Không | `1` = không thể sửa chữa |
| `cannot_repair_reason` | string | Có** | Lý do không thể sửa (bắt buộc nếu `cannot_repair=1`) |

\* Bắt buộc khi `cannot_repair = 0`.
\*\* Bắt buộc khi `cannot_repair = 1`.

**Mode Completed — request:**

```json
{
  "name": "WO-CM-2026-00042",
  "repair_summary": "Đã thay tụ C12, đo điện áp đầu ra board nguồn 24V DC ± 0.5V — đạt.",
  "root_cause_category": "Electrical",
  "dept_head_name": "BS. CK2 Nguyễn Văn Hùng",
  "checklist_results": "[{\"idx\":1,\"test_description\":\"Điện áp đầu vào\",\"result\":\"Pass\",\"measured_value\":\"218V\"}]",
  "spare_parts": "[]",
  "firmware_updated": 0,
  "firmware_change_request": "",
  "cannot_repair": 0,
  "cannot_repair_reason": ""
}
```

**Side-effects (mode `cannot_repair=0`):**
1. Set các trường từ body (`repair_summary`, `root_cause_category`, `dept_head_name`, `checklist_results`, `spare_parts`, `firmware_*`).
2. `status = "Pending Inspection"` — **WO chưa submit ở bước này**.
3. ALE `event_type = "repair_pending_inspection"`.
4. **Đọc `asset_status` LIVE** cho response (KHÔNG đổi trạng thái asset ở bước này) — xem "Response contract (parity shape)" bên dưới.

> Nghiệm thu thực sự xảy ra ở `confirm_inspection` (endpoint 3.9).

**Response 200 (mode Pending Inspection):**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Pending Inspection",
    "mttr_hours": null,
    "sla_breached": 0,
    "asset_status": "Under Repair"
  }
}
```

> `mttr_hours` = `null` ở nhánh này — MTTR chỉ tính ở `complete_repair()` (chạy khi `confirm_inspection` submit). `sla_breached` = cờ doc hiện tại (0 mặc định, hoặc 1 nếu scheduler đã stamp). `asset_status` = trạng thái LIVE của asset (thường `Under Repair`, đọc SSoT — KHÔNG hardcode).

**Side-effects (Cannot Repair mode):**
1. Nếu đang `"Pending Parts"` → **`exit_parts_hold(doc, until=now())` (BR-09-10, INV-CM-HOLD-5)** chốt khoảng hold cuối + ALE `parts_hold_resumed` (audit đầy đủ; WO không tính MTTR nhưng vẫn ghi trọn khoảng hold).
2. Set `cannot_repair_reason`, `status = "Cannot Repair"`.
3. `transition_asset_status(→ "Out of Service")` (= `AssetStatus.OUT_OF_SERVICE`, casing chính xác **"Out of Service"** — chữ `of` viết thường).
4. ALE `event_type = "cannot_repair"`.
5. **Đọc `asset_status` LIVE** sau transition (trả `"Out of Service"`) — cùng SSoT với nhánh happy.

**Response 200 (Cannot Repair):**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Cannot Repair",
    "mttr_hours": null,
    "sla_breached": null,
    "asset_status": "Out of Service"
  }
}
```

> `mttr_hours` / `sla_breached` = `null` ở nhánh này — WO không hoàn thành sửa chữa nên **không tính MTTR** (2 field thêm CHỈ để parity key-set với nhánh happy, giá trị = `doc.mttr_hours` / `doc.sla_breached`, thường `null`/chưa set). `asset_status` = trạng thái LIVE sau transition = `"Out of Service"`.

#### Response contract — parity shape (CR-13b, mobile Trục B)

**INVARIANT hợp đồng (bắt buộc test):** cả 2 nhánh return của `close_work_order` phải trả **CÙNG key-set — superset đúng 5 khoá**:

```
set(keys happy) == set(keys cannot_repair) == {name, status, mttr_hours, sla_breached, asset_status}
```

Không nhánh nào được thiếu/thừa khoá so với contract. Bảng chi tiết từng field:

| Field | Kiểu (OAS) | Nhánh happy (Pending Inspection) | Nhánh cannot_repair (Cannot Repair) |
|---|---|---|---|
| `name` | string | WO name | WO name |
| `status` | string (enum 2 giá trị `[Pending Inspection, Cannot Repair]`) | `"Pending Inspection"` | `"Cannot Repair"` |
| `mttr_hours` | number, **nullable** | `doc.mttr_hours` (thường `null` — MTTR tính ở `confirm_inspection`) | `doc.mttr_hours` (`null` — không tính MTTR) |
| `sla_breached` | integer enum `[0,1]`, **nullable** | `doc.sla_breached` (0 mặc định / 1 nếu scheduler stamp) | `doc.sla_breached` (`null`/chưa set) |
| `asset_status` | **string, nullable** ⟵ **MỚI (CR-13b)** | LIVE `lifecycle_status` (thường `Under Repair`) | LIVE `lifecycle_status` sau transition = `Out of Service` |

**Nguồn `asset_status` = SSoT LIVE (KHÔNG hardcode):** đọc trực tiếp trạng thái asset qua `frappe.db.get_value("AC Asset", doc.asset_ref, "lifecycle_status")` (hoặc `AssetRepo.get_value(doc.asset_ref, "lifecycle_status")` — cùng SSoT như `complete_repair` `services/imm09.py:732`). Lý do KHÔNG hardcode: `lifecycle_status` của AC Asset do **nhiều process** quản (calib-fail → OoS+CAPA, decommission…) — xem BR-09-09 (root-cause `04 §restore có điều kiện`). Nhánh happy asset vẫn `Under Repair` (WO → Pending Inspection, chưa restore); nhánh cannot_repair vừa transition sang `Out of Service` nên LIVE-read == `"Out of Service"`. Khuyến nghị BE: một tail dùng chung dựng đủ 5 khoá, chỉ `status` khác giữa 2 nhánh (chống drift key-set).

**OAS `CloseWorkOrderResponse` — khai `asset_status` (bịt vi phạm `additionalProperties: false`):** schema hiện đóng 4 khoá `{name, status, mttr_hours, sla_breached}` (`test_mobile_oas.py:_CLOSE_WORK_ORDER_DATA_KEYS`) → nhánh cannot_repair emit `asset_status` **KHÔNG được khai** ⇒ vi phạm `additionalProperties:false` của contract mobile. CR-13b thêm property `asset_status` (`type: string`, `nullable: true`) vào `CloseWorkOrderResponse` → backend KHÔNG còn emit field bị cấm. `mttr_hours` (`number`, nullable) + `sla_breached` (`integer` enum[0,1], nullable) đã nullable sẵn — giữ nguyên. `required` giữ `[name, status]` (3 field còn lại nullable, không bắt buộc). Đồng bộ: hằng test `_CLOSE_WORK_ORDER_DATA_KEYS` thêm `asset_status`; example ở `api/openapi_overrides.py` `imm09.close_work_order` (`:955-975`) thêm `asset_status` vào block `response`.

> ⚠️ **KHÔNG đụng `confirm_inspection` / `ConfirmInspectionResponse`** — endpoint 3.9 giữ 4-key `{name, status, mttr_hours, sla_breached}` (schema RIÊNG, C3-split, `status.enum=[Completed]`). CR-13b chỉ chạm `close_work_order` / `CloseWorkOrderResponse`. Không endpoint/behavior nào khác đổi. Xem **ADR-IMM09-CLOSE-PARITY** (`04 §3`).

**Lỗi trong submit (Completed mode):**

| Code | HTTP | Mô tả |
|---|---|---|
| `CM-003` | 422 | Spare parts row thiếu `stock_entry_ref` |
| `CM-004` | 422 | `stock_entry_ref` không tồn tại trong DB |
| `CM-005` | 422 | `firmware_updated=1` nhưng không có FCR linked |
| `CM-006` | 422 | FCR linked status ≠ `"Approved"` |
| `CM-007` | 422 | Checklist row chưa điền `result` |
| `CM-008` | 422 | Checklist có row `result = "Fail"` |
| `CM-013` | 400 | Thiếu `dept_head_name` |

---

### 3.9 `confirm_inspection`

**Mô tả:** Nghiệm thu sau sửa chữa — bước kiểm soát chất lượng cuối. Chuyển WO từ `Pending Inspection` → `Completed` (submit docstatus=1), kích hoạt `complete_repair()` để tính MTTR, SLA, và **restore Asset có điều kiện** (BR-09-09): Asset → Active **CHỈ khi** asset đang `Under Repair`; nếu đang `Out of Service`/`Decommissioned` (hold governance khác) thì giữ nguyên — WO vẫn đóng được bình thường.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.confirm_inspection` |

**Role:** `CAN_APPROVE_DEP` (Dept Head / QA Officer / Workshop Manager)

**Request body:**

```json
{ "name": "WO-CM-2026-00042" }
```

**Side-effects:**
1. Kiểm tra status = "Pending Inspection", role `CAN_APPROVE_DEP`.
2. Set `dept_head_confirmation_datetime = now()`.
3. `doc.submit()` → `before_submit` (validate BR-09-02/03/04) → `on_submit` → `complete_repair()`.
4. `complete_repair()`: set `completion_datetime`; **BR-09-10 (clock-stop):** nếu `parts_hold_started` còn non-null (đóng WO khi đang Pending Parts) → `exit_parts_hold(doc, until=completion_datetime)` chốt khoảng hold cuối TRƯỚC (INV-CM-HOLD-5); rồi `mttr_hours = repair_elapsed_hours(doc, completion_datetime)` (= `(completion−open) − parts_hold_hours`, KHÔNG phải calendar time thô) + `sla_breached = is_sla_breached(elapsed, sla_target) OR sla_breached`; **restore Asset có điều kiện (BR-09-09):** đọc `prev_status` → (A) `Under Repair` → transition Active; (B) `Out of Service`/prev khác → giữ nguyên (không override hold); (C) `Decommissioned` → bỏ qua restore (terminal, không raise). MỌI nhánh ghi 1 ALE `repair_completed`. KHÔNG nhánh nào làm vỡ `on_submit` (INV-09-RESTORE-1).
5. Nếu `root_cause_category` chứa từ khóa lặp lại ("lặp lại", "recurring", "chronic"...) → tự động gọi `imm12.detect_chronic_failures()` (non-blocking).
6. BR-11: nếu thiết bị yêu cầu hiệu chuẩn → tạo CAL WO recalibration (`create_post_repair_calibration`, non-blocking) — GIỮ NGUYÊN.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Completed",
    "mttr_hours": 18.5,
    "sla_breached": 0
  }
}
```

**Errors:**

| Code | HTTP | Mô tả |
|---|---|---|
| `NOT_FOUND` | 404 | WO không tồn tại (`IMM09_NOT_FOUND` `services/imm09.py:1101`; `messages.py:639`) |
| `BAD_STATE` | 409 | WO không ở trạng thái "Pending Inspection" (`IMM09_BAD_STATE` `services/imm09.py:1102`; `messages.py:646` — xung-đột TRẠNG THÁI, KHÔNG 422) |
| `FORBIDDEN` | 403 | Không có quyền `repair.submit` (cap-gate `rbac.require` `api/imm09.py:105`) |

> 📱 **Cross-ref Mobile-BE contract (flow-5 acceptance):** endpoint này được surface trong OpenAPI mobile [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) tại path `/api/method/assetcore.api.imm09.confirm_inspection` (opId **`confirmInspection`**, POST-only). Đây là **action TERMINAL-THẬT** đóng dead-end CUỐI chuỗi repair: `closeWorkOrder` chỉ đưa WO về `Pending Inspection` (NON-terminal); `getRepairWorkOrder.allowed_transitions[]` surface CTA `Completed` nhưng KHÔNG có endpoint để thực thi → `confirmInspection` lấp. 200 = `oneOf [ConfirmInspectionEnvelope, Error]` (route-by-VALUE `body.success`, 0 discriminator); `data` = **`ConfirmInspectionResponse`** closed 4-key `{name, status, mttr_hours, sla_breached}` (`required[name,status]`), `status.enum=[Completed]` (single-value INVARIANT), `sla_breached` integer enum[0,1] (KHÔNG boolean). **Schema RIÊNG, KHÔNG reuse `CloseWorkOrderResponse`** — C3-split cross-action: `status` 1-value `[Completed]` ≠ 2-value `[Pending Inspection, Cannot Repair]`; **và sau CR-13b** `CloseWorkOrderResponse` mang 5-key (thêm `asset_status`) trong khi `ConfirmInspectionResponse` giữ 4-key `{name,status,mttr_hours,sla_breached}` (KHÔNG `asset_status`) ⇒ shape KHÁC hẳn, càng KHÔNG reuse. Cap-gate `repair.submit` (phê-duyệt-chất-lượng) **KHÁC `repair.create`** (KTV). 2 lỗi nghiệp vụ in-handler (`IMM09_NOT_FOUND` 404 + `IMM09_BAD_STATE` 409) arrive **HTTP-200 + Error envelope** (quirk §5, KHÔNG status-line). Chi tiết hợp đồng + ADR: [`docs/mobile/04-api-contract.md §8.20`](../mobile/04-api-contract.md) + [`ADR-MOBILE-009.md`](../mobile/ADR-MOBILE-009.md).

---

### 3.10 `attach_repair_checklist_photo` — Đính ảnh bằng chứng theo TỪNG mục checklist sửa chữa (NĐ98) 🟢 LIVE (BE+service @source · mobile OAS §8.36 CR-15)

> **Mục tiêu (mobile CR-15/G6):** KTV thực hiện sửa chữa tại hiện trường chụp ảnh bằng chứng cho **từng mục checklist nghiệm thu** (vd đo điện trở đất, test dòng rò, kiểm tra cơ khí) → đính **trực tiếp vào đúng mục** của Asset Repair làm **bằng chứng NĐ98** cho thiết bị **Class C/D**. **Đối xứng** `imm08.attach_pm_checklist_photo` (Vòng 2) + `imm12.attach_incident_photo` (Vòng 1) — CÙNG pattern write-path multipart + File private + lifecycle-hard-req + Decision-B; **KHÁC**: module IMM-09, doctype `Asset Repair`, child `Repair Checklist`, và **discriminator = Frappe child `idx`** (Repair Checklist KHÔNG có field STT domain như PM Checklist Result — xem ADR-IMM09-PHOTO-01).

**Endpoint:** `POST assetcore.api.imm09.attach_repair_checklist_photo`

**Request — `multipart/form-data`** (KHÁC mọi endpoint imm09 khác dùng JSON/form_dict):

| Phần | Nguồn | Bắt buộc | Ghi chú |
|---|---|---|---|
| `work_order_name` | form-field / query (`frappe.form_dict`) | ✅ | tên Asset Repair (WO) đang mở |
| `checklist_item_idx` | form-field (`frappe.form_dict`) → `int()` | ✅ | **Frappe child `idx`** của hàng `repair_checklist` (1-based); parse-fail (sentinel −1) / không khớp `idx` → `VALIDATION` |
| `file` | `frappe.request.files["file"]` (binary) | ✅ | ảnh JPG/PNG; đọc `upload.stream.read()` (mirror `imm08.attach_pm_checklist_photo` `api/imm08.py:70-79`) |

**Response 200 — success (Decision-B):**
```jsonc
{ "success": true, "data": { "file_url": "/private/files/repair_xxx.jpg", "file_name": "repair_xxx.jpg", "checklist_item_idx": 2 } }
```

**Side-effects khi success (BR-09-15 + BR-09-16):**
1. Sinh **đúng 1** `File` **private** (`attached_to_doctype="Asset Repair"`, `attached_to_name=<WO>`, `is_private=1`, `content=filedata`, `decode=False`).
2. Ghi `file_url` vào field `repair_checklist[idx].photo` bằng **`frappe.db.set_value("Repair Checklist", <row.name>, "photo", file_url, update_modified=False)`** — **KHÔNG** `doc.save()` trên Asset Repair (anti-pattern #10: tránh re-chạy `validate_repair_checklist_complete` → BR-09-04 chưa-đủ-Pass sẽ throw khi checklist đang dở, và tránh docstatus lock/đổi `workflow_state`; `photo` permlevel=0 nên không strip). Read-back: `get_repair_work_order(WO).repair_checklist[idx].photo == file_url` (`get_work_order` KHÔNG đổi — `doc.as_dict()` đã trả `repair_checklist[].photo`).
3. Sinh **đúng 1** `Asset Lifecycle Event` `event_type="repair_checklist_photo_attached"` (`asset=wo.asset_ref`, `actor=frappe.session.user`, `timestamp=now`, `root_doctype="Asset Repair"`, `root_record=<WO>`, `notes="Đính ảnh mục #<idx>: <filename>"`) — evidence trail NĐ98, **hard-requirement KHÔNG swallow**: gọi `create_lifecycle_event` (canonical) TRỰC TIẾP, **KHÔNG** qua wrapper `_log_lifecycle_event` (vốn try/except-swallow). Event throw → File.insert + set_value rollback (chưa commit) ⇒ **không orphan, không silent** (đối xứng imm12/imm08).

**Bảng lỗi (tất cả in-handler HTTP-200 + Error envelope — Decision-B, KHÔNG raise→4xx):**

| Nhánh | `success` | `code` | `http_status` (metadata envelope) | `fields` | File tạo? |
|---|---|---|---|---|---|
| **Guest/no-token** | — | — | **403 (dispatcher)** | — | ❌ (chặn TRƯỚC service; `@frappe.whitelist(methods=["POST"])` KHÔNG `allow_guest`) |
| WO không tồn tại | `false` | `NOT_FOUND` | 404 | — | ❌ |
| Không phải KTV được giao **VÀ** không `repair.write` | `false` | `FORBIDDEN` | 403 | — | ❌ (in-handler cap-403; check TRƯỚC khi tạo File) |
| `checklist_item_idx` thiếu / không parse int / KHÔNG khớp child `idx` nào | `false` | `VALIDATION` | 422 | `{file: "Không tìm thấy mục checklist trong lệnh sửa chữa này"}` | ❌ |
| Thiếu `file` | `false` | `VALIDATION` | 422 | `{file: "Thiếu tệp ảnh"}` | ❌ |
| Content-type ∉ {image/jpeg, image/jpg, image/png} (`_REPAIR_PHOTO_CONTENT_TYPES` **3 giá-trị** `services/imm09.py:131`) | `false` | `VALIDATION` | 422 | `{file: "Tệp phải là ảnh JPG hoặc PNG"}` | ❌ |
| Size > cap (`MAX_REPAIR_CHECKLIST_PHOTO_BYTES` = 10 MB, `:130`) | `false` | `VALIDATION` | 422 | `{file: "Ảnh vượt quá dung lượng cho phép (tối đa 10 MB)"}` | ❌ |
| Mục đã có ảnh (`len(_repair_checklist_item_photos(row)) >= MAX_REPAIR_CHECKLIST_PHOTOS=1`, `:129`) | `false` | `VALIDATION` | 422 | `{file: "Mỗi mục checklist chỉ đính 1 ảnh"}` | ❌ |
| **Ảnh hỏng / đứt-truyền** (`UnidentifiedImageError\|OSError` khi Frappe `File.before_insert`→`strip_exif`→`PIL.Image.open` — bytes rác/cắt-cụt dù content-type hợp lệ; `services/imm09.py:1222-1233`) | `false` | `VALIDATION` | 422 | `{file: "Tệp ảnh bị lỗi hoặc không đọc được, vui lòng chụp/chọn lại."}` | ❌ (PIL fail TRONG `before_insert` TRƯỚC db_insert+write_file ⇒ KHÔNG orphan; `row.photo` chưa set) |

> **HEIC/HEIF (chốt cross-module — canonical ADR-IMM08-PHOTO-04):** allowlist BE **GIỮ** `{image/jpeg, image/jpg, image/png}` (`_REPAIR_PHOTO_CONTENT_TYPES` **3 giá-trị**, `services/imm09.py:131` — `image/jpg` là alias JPEG, KHÔNG mở HEIC). iPhone chụp HEIC/HEIF **PHẢI được app mobile transcode → JPEG TRƯỚC upload** (fix tại-nguồn, 0 dependency BE, JPEG xem được trong web-audit). BE-transcode (pillow-heif) = `[ROADMAP]` fallback (measure-first); mở-allowlist-nhận-HEIC = **loại** (HEIC không render trên trình duyệt). Chi tiết + alternatives: `docs/imm-08/05_API_Specification.md` ADR-IMM08-PHOTO-04.

**2 loại 403 (DONE-gate spec-contract — mirror imm08/imm12):**
- **dispatcher-403** = Guest/no-token → chặn TRƯỚC khi vào service (POST-@whitelist không `allow_guest` → Frappe dispatcher trả 403 thật, có status-line). Đây KHÔNG phải lỗi nghiệp vụ.
- **in-handler cap-403** = đã đăng nhập nhưng không phải KTV được giao và thiếu `repair.write` → `ServiceError(FORBIDDEN)` surface Decision-B **HTTP-200** body `code=FORBIDDEN`, `http_status=403` (metadata trong envelope, KHÔNG status-line). **KHÔNG leak** raw cap.

**Thứ tự thực thi (BẮT BUỘC — mọi nhánh reject TRƯỚC khi ghi File):** exists(WO) NOT_FOUND → permission (assignee/`repair.write`) FORBIDDEN → resolve `checklist_item_idx`→child-row (idx hợp lệ) VALIDATION → file present VALIDATION → content-type VALIDATION → size VALIDATION → max-count VALIDATION → `File.insert(is_private=1)` (**corrupt-guard**: `UnidentifiedImageError|OSError`→VALIDATION 422 TRONG `before_insert`, TRƯỚC db_insert ⇒ không orphan) → `db.set_value(row.photo)` → `create_lifecycle_event(repair_checklist_photo_attached)` → `frappe.db.commit()` → `_ok`. **KHÔNG commit trước khi emit event** (giữ rollback-on-throw).

**Permission model (BR-09-15) — mirror `_assert_can_attach_pm_photo` (imm08):**
```
is_assignee = (wo.assigned_to == frappe.session.user)
has_write   = frappe.has_permission("Asset Repair", ptype="write", doc=wo, user=frappe.session.user)
allowed     = is_assignee OR has_write
```
- `frappe.has_permission(..., doc=wo)` áp CẢ role-DocPerm write (Repair Manager / Repair User / Super Admin) LẪN row-level hook `ac_asset_repair_query`/vendor-scope ⇒ **tái dùng IDOR-guard** — Vendor Engineer / KTV ngoài `assigned_to` → `has_write=False` → FORBIDDEN.
- KTV được giao luôn được đính ảnh cho chính WO của mình (bằng chứng hiện trường do chính họ thực hiện — đối xứng reporter trong `attach_incident_photo`).

**Boundaries (Always / Never):**
- **Always:** File `is_private=1` (NĐ98 — ảnh thiết bị y tế KHÔNG public); check permission + idx + validation + max-count TRƯỚC `File.insert`; emit ĐÚNG 1 lifecycle event `repair_checklist_photo_attached` per success (hard-req, KHÔNG swallow); ghi `row.photo` bằng `db.set_value(update_modified=False)` (KHÔNG `doc.save()`); dùng CÙNG helper `_repair_checklist_item_photos(row)` cho cả max-count check LẪN read-side hiển thị (invariant **count==rows**).
- **Never:** tạo File ở nhánh reject; `is_private=0`; `doc.save()` trên Asset Repair để set photo (re-validate BR-09-04 khi checklist chưa xong → false-error + đổi `workflow_state`); `raise frappe.throw`→HTTP-4xx cho lỗi nghiệp vụ (phải Decision-B HTTP-200); dùng wrapper `_log_lifecycle_event` (swallow) cho event evidence; dùng event ngoài `repair_checklist_photo_attached` (giá trị ngoài Select `Asset Lifecycle Event` bị nuốt/throw); commit trước khi emit event (mất rollback-on-throw); leak raw cap trong message FORBIDDEN; đổi shape `get_repair_work_order` vòng này (chỉ đọc `r.photo` sẵn có).

> 📱 **Cross-ref Mobile-BE contract (CR-15/G6 — path multipart THỨ BA, hoàn tất bộ-ba):** endpoint này được surface trong OpenAPI mobile [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) tại path `/api/method/assetcore.api.imm09.attach_repair_checklist_photo` (opId **`attachRepairChecklistPhoto`**, POST-only, **tag `work-order`**). requestBody = **`multipart/form-data` DUY NHẤT** (`$ref AttachRepairChecklistPhotoRequest` closed 3-part `[work_order_name, checklist_item_idx:integer, file:{format:binary}]`); 200 = **`oneOf [AttachRepairChecklistPhotoEnvelope, Error]`** (route-by-VALUE `body.success`, 0 discriminator); `data` = **`AttachRepairChecklistPhotoResponse`** closed EXACT 3-key `{file_url, file_name, checklist_item_idx:integer}` (**ĐỒNG `AttachPmChecklistPhotoResponse` 3-prop NHƯNG schema RIÊNG — naming-guard 3-way; KHÁC `AttachIncidentPhotoResponse` 2-prop**). Slot `{200,401,403}`; **403 SINGLE-SHAPE `Forbidden`** (dispatcher-403 guest/no-token — in-handler cap-403 arrive HTTP-200 + Error). 8 nhánh lỗi in-handler (`Error.http_status` ⊇ {403,404,422}, gồm idx-row + corrupt-guard) arrive **HTTP-200 + Error envelope** (Decision-B, KHÔNG status-line). Chi tiết hợp đồng + ADR: [`docs/mobile/04-api-contract.md §8.36`](../mobile/04-api-contract.md) + [`ADR-MOBILE-030.md`](../mobile/ADR-MOBILE-030.md).

> ✍️ **Self-Correction (2026-07-11, verify-before-claim @source khi curate mobile OAS §8.36):** (1) allowlist content-type = **3 giá-trị** `_REPAIR_PHOTO_CONTENT_TYPES = ("image/jpeg","image/jpg","image/png")` `services/imm09.py:131` (doc cũ ghi 2 giá-trị `{image/jpeg, image/png}` @`:129` — sửa +`image/jpg` alias + line-ref 129→131); (2) **thêm nhánh lỗi #8 corrupt-guard** `UnidentifiedImageError|OSError` @`services/imm09.py:1222-1233` vào bảng lỗi (đối xứng imm08/imm12 — trước bị sót); (3) header status 🟡 SPEC → 🟢 LIVE (handler @`api/imm09.py:58` + service @`services/imm09.py:1162` ĐÃ trên đĩa). KHÔNG đụng `.py` — chỉ đồng-bộ doc với source.

### ADR-IMM09-PHOTO-01: Lưu ảnh bằng chứng sửa chữa = Frappe `File` private attach vào Asset Repair; discriminator per-mục = **Frappe child `idx`**; SoT = `row.photo` (Attach đơn trị, max 1/mục)
- **Status**: Accepted · **Date**: 2026-07-09
- **Context**: NĐ98 (thiết bị Class C/D) đòi ảnh bằng chứng **theo từng mục** checklist sửa chữa; `repair_checklist.photo` là field `Attach` **đơn trị** đã tồn tại (KHÔNG schema-change). **KHÁC imm08**: `Repair Checklist` (child của Asset Repair) **KHÔNG có** field STT domain `checklist_item_idx` (chỉ có `test_description/test_category/expected_value/measured_value/result/notes/photo`) — trong khi PM Checklist Result CÓ. `get_repair_work_order` đã trả `repair_checklist[].photo` (qua `doc.as_dict()`). `_apply_checklist` (`services/imm09.py:1247`) đã dùng Frappe child `idx` làm khóa cập-nhật hàng (`row.idx == r.get("idx")`).
- **Decision**: (1) store = Frappe `File` private, attach vào **parent WO** (`attached_to_doctype='Asset Repair'`, `attached_to_name=WO`, KHÔNG attach vào child-row). (2) discriminator per-mục = **Frappe child `idx`** (1-based) — `_find_repair_checklist_row(wo, idx)` duyệt `wo.repair_checklist` khớp `int(r.idx)==idx` (KHÔNG N+1: list con đã load). (3) SoT ảnh/mục = `row.photo` (đơn trị, `db.set_value(update_modified=False)`) — `_repair_checklist_item_photos(row)` trả `[{file_url}]`/`[]` = **1 SoT** cho max-count(=1) + read-side hiển thị ⇒ count==rows. `MAX_REPAIR_CHECKLIST_PHOTOS=1` (mirror imm08 CODE, KHÔNG mirror bản mô tả cũ imm08 doc multi-photo-discriminator).
- **Alternatives**: (A) thêm field STT domain `checklist_item_idx` vào Repair Checklist để mirror imm08 1:1 → schema-change + migration + backfill hàng cũ, trong khi Frappe child `idx` đã đủ ổn định cho checklist append-only (không reorder/xóa hàng giữa flow) → loại (over-engineering). (B) attach File vào child-row (`attached_to_doctype='Repair Checklist'`, `attached_to_name=row.name`) → child-row name là hash + resolve permission trên child doctype phức tạp + trái parity imm08 → loại. (C) multi-photo/mục qua File-query discriminator → phức tạp hơn, task chỉ cần `populate repair_checklist.photo` (đơn trị) → loại.
- **Consequences**: 0 field mới / 0 child table / 0 migration schema; `MAX_REPAIR_CHECKLIST_PHOTOS=1` (đính ảnh thứ 2 vào mục đã có ảnh → VALIDATION); `row.photo` hiển thị làm thumbnail. **Đánh đổi (ghi rõ):** discriminator = Frappe child `idx` chỉ ổn định khi hàng checklist KHÔNG bị reorder/xóa sau khi tạo (đúng với luồng CM: checklist clone từ template/append lúc close, không xóa hàng giữa chừng). Nếu tương lai cho phép xóa hàng checklist giữa flow → phải chuyển discriminator sang `row.name` (child docname) — ghi backlog, ngoài scope vòng này.

### ADR-IMM09-PHOTO-02: Audit đính ảnh sửa chữa = canonical `Asset Lifecycle Event` `repair_checklist_photo_attached` (thêm option Select) — hard-requirement, KHÔNG dùng wrapper swallow
- **Status**: Accepted · **Date**: 2026-07-09
- **Context**: NĐ98 đòi evidence trail cho mọi thao tác trên hồ sơ sửa chữa; `Asset Lifecycle Event.event_type` là Select enum cố định (`asset_lifecycle_event.json`); `repair_checklist_photo_attached` CHƯA có trong options (hiện có `repair_opened`, `repair_completed`, `incident_photo_attached` Vòng 1, `pm_checklist_photo_attached` Vòng 2…). **Bẫy nội bộ IMM-09:** wrapper `_log_lifecycle_event` (`services/imm09.py:543`) **try/except-swallow** exception (audit best-effort cho các transition thường) — nếu tái dùng cho event evidence sẽ **mất bằng chứng im lặng**.
- **Decision**: (1) **THÊM option `repair_checklist_photo_attached`** vào Select `event_type` của `Asset Lifecycle Event` (KHÔNG migration field khác — chỉ mở enum → deploy `bench reload-doctype "Asset Lifecycle Event"`, HARD-STOP USER, KHÔNG chặn test vì test seed event trực tiếp). (2) emit canonical `create_lifecycle_event(...)` (`utils/lifecycle.py`) **TRỰC TIẾP** ở success-path, **hard-requirement** (trong transaction, commit cùng File + set_value), **KHÔNG** đi qua wrapper `_log_lifecycle_event` swallow — đây là **bản ghi bằng chứng** không được mất im lặng. Mirror imm12 `incident_photo_attached` / imm08 `pm_checklist_photo_attached`.
- **Alternatives**: (A) tái dùng `repair_completed`/`repair_opened` → sai nghĩa (đính ảnh ≠ hoàn thành/mở sửa chữa), loại. (B) dùng wrapper `_log_lifecycle_event` (swallow) cho tiện → mất evidence im lặng khi throw, vi phạm NĐ98, loại. (C) audit best-effort try/except riêng → cùng lỗi (B), loại.
- **Consequences**: enum +1; deploy cần reload-doctype 1 lần; test seed event bằng `create_lifecycle_event` không phụ thuộc reload live (không chặn `run-tests`). Đánh đổi: enum drift phải đồng bộ với `docs/mobile` nếu mobile map event-type.

---

### 3.11 `get_repair_kpis`

**Mô tả:** KPI bảo trì sửa chữa trong tháng: MTTR, SLA compliance, repeat failure, backlog.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.get_repair_kpis` |

**Query params:** `?year=2026&month=4` (mặc định = tháng hiện tại)

**Response 200:**

```json
{
  "success": true,
  "data": {
    "kpis": {
      "total_completed": 14,
      "mttr_avg_hours": 18.5,
      "sla_compliance_pct": 85.7,
      "repeat_failure_count": 2,
      "open_wos": 12
    },
    "root_cause_breakdown": [
      { "category": "Electrical", "count": 7 },
      { "category": "Mechanical", "count": 4 },
      { "category": "Software", "count": 2 },
      { "category": "User Error", "count": 1 }
    ]
  }
}
```

> 📱 **Cross-ref Mobile-BE contract (Dashboard-KPI R1c — `getRepairKpis`, CR-31c HOÀN-TẤT-TRIAD, 2026-07-15):** endpoint này được surface trong OpenAPI mirror `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — path `GET /api/method/assetcore.api.imm09.get_repair_kpis`, opId **`getRepairKpis`**, tag `work-order`, cho màn "Bảng chỉ số sửa chữa (CM)". Quyết định kiến trúc: [`../mobile/ADR-MOBILE-058.md`](../mobile/ADR-MOBILE-058.md) + spec [`../mobile/04-api-contract.md`](../mobile/04-api-contract.md) §8.52.
> - **HÌNH DẠNG RIÊNG** trong bộ-ba Dashboard-KPI: SINGLE khối `kpis` (5-key) **+ `root_cause_breakdown[]`** — KHÔNG `trend_6months` (KHÁC `getPmDashboardStats`/ADR-056) + CÓ `root_cause_breakdown` (KHÁC `getCalibrationKpis`/ADR-057 single-kpis). Grounded VERBATIM `services/imm09.py::get_kpis` @`:1713-1725`.
> - **`mttr_avg_hours` & `sla_compliance_pct` = number NON-nullable** (`round(...) if total else 0` @`:1698-1700` — LUÔN number, KHÔNG null-guard; mirror Cal `pass_rate_pct`, ĐỐI-NGHỊCH Pm `compliance_rate_pct` nullable). `open_wos` = COUNT khớp drill `/cm/work-orders` (§7.2/BR-09-08 INVARIANT card==drill).
> - **Query-param `year`/`month` = `type:string`** (signature `get_repair_kpis(year: str = "", month: str = "")` @`api/imm09.py:167` — KHÁC `getCalibrationKpis` `integer` vì `imm11` dùng `year=None`); `required:false`, không khai `default:` (BE default động `getdate(nowdate())`).
> - 4 schema closed: `RepairKpis` (5-key) / `RepairRootCauseItem` (schema MỚI — `{category,count}`) / `RepairKpisData` (`{kpis, root_cause_breakdown}`) / `RepairKpisEnvelope`. 200 = `oneOf [RepairKpisEnvelope, Error]` Decision-B. **CONTRACT-ONLY** (handler LIVE @source, 0 `.py`/reload/migrate).

---

### 3.12 `get_mttr_report`

**Mô tả:** MTTR trend 6 tháng, First-Time Fix Rate, backlog phân theo khoa phòng.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.get_mttr_report` |

**Query params:** `?year=2026&month=4` (mặc định = tháng hiện tại)

**Response 200:**

```json
{
  "success": true,
  "data": {
    "mttr_avg": 18.5,
    "first_fix_rate": 85.7,
    "backlog_count": 12,
    "cost_per_repair": 450000,
    "mttr_trend": [
      { "month": "2025-11", "value": 22.0 },
      { "month": "2025-12", "value": 19.5 },
      { "month": "2026-01", "value": 25.1 },
      { "month": "2026-02", "value": 21.0 },
      { "month": "2026-03", "value": 20.6 },
      { "month": "2026-04", "value": 18.5 }
    ],
    "backlog_by_dept": [
      { "dept": "ICU", "count": 5 },
      { "dept": "OR", "count": 4 },
      { "dept": "Radiology", "count": 3 }
    ]
  }
}
```

**Ghi chú:**
- `first_fix_rate` = `(1 − tỷ lệ is_repeat_failure) × 100`.
- `cost_per_repair` = avg `total_parts_cost` của WO Completed trong tháng.

---

### 3.13 `search_spare_parts`

**Mô tả:** Tìm kiếm vật tư (từ DocType `IMM Device Spare Part`) để thêm vào WO.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.search_spare_parts` |

**Query params:** `?query=tụ&limit=10` (default limit=10; tối thiểu 2 ký tự mới trả kết quả)

**Response 200:**

```json
{
  "success": true,
  "data": [
    {
      "item_code": "CAP-100UF-25V",
      "item_name": "Tụ điện 100uF 25V",
      "manufacturer_part_no": "CAP-100UF-25V",
      "qty": 1,
      "uom": "Cái",
      "unit_cost": 25000,
      "total_cost": 25000,
      "stock_entry_ref": "",
      "notes": "",
      "idx": 0
    }
  ]
}
```

> **Ghi chú:** Source là `tabIMM Device Spare Part`, tìm theo `part_name` LIKE hoặc `manufacturer_part_no` LIKE. FE `CMPartsView.vue` gọi qua `searchSpareParts()` từ `@/api/imm09`. Query `< 2` ký tự → trả `[]` rỗng (guard `services/imm09.py:1224`). Số dòng cap bởi `limit` (SQL `LIMIT`, KHÔNG pagination).

> 📱 **Cross-ref Mobile-BE contract (repair spare-parts sub-flow):** endpoint này được surface trong OpenAPI mobile [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) tại path `/api/method/assetcore.api.imm09.search_spare_parts` (opId **`searchSpareParts`**, **GET** — bare `@frappe.whitelist()` `api/imm09.py:123` nhận GET, read-only picker cho repair-detail). 200 = `oneOf [SearchSparePartsEnvelope, Error]` (route-by-VALUE `body.success`, 0 discriminator); `data` = **array `<SearchSparePartItem>` RAW** (KHÔNG pagination — `_ok(list)` wrap, cap bởi `limit`; mirror `getAssetIncidentHistory` no-pagination NHƯNG data là list trần, KHÁC `{asset,items}`). `[]` rỗng hợp lệ (query<2 hoặc không match — **KHÔNG 404**). `SearchSparePartItem` `additionalProperties:false` EXACT 10 prop `{item_code, item_name, manufacturer_part_no, qty, uom, unit_cost, total_cost, stock_entry_ref, notes, idx}` (`required[item_code]`) grounded `services/imm09.py:1237-1246` — **0 boolean/Check field** ⇒ 0 prop `integer enum[0,1]` (không int-vs-bool trap; `qty`/`idx` integer, `unit_cost`/`total_cost` number). **Slot `{200,401}` — KHÔNG 403**: handler api-level **KHÔNG `rbac.require`** (`api/imm09.py:123-125` chỉ `handle(svc.search_spare_parts, ...)`) ⇒ không in-handler cap-403; Guest → dispatcher-401/403 (read-only picker). Chi tiết hợp đồng + ADR: [`docs/mobile/04-api-contract.md §8.22`](../mobile/04-api-contract.md) + [`ADR-MOBILE-010.md`](../mobile/ADR-MOBILE-010.md) + `04_Backend_Design.md §3.5`.

---

### 3.14 `get_asset_repair_history`

**Mô tả:** Lịch sử tất cả WO sửa chữa đã hoàn thành của một thiết bị, dùng cho traceability và phát hiện tái hỏng.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.get_asset_repair_history` |

**Query params:** `?asset_ref=AC-ASSET-2026-00042&limit=10`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "asset_ref": "AC-ASSET-2026-00042",
    "history": [
      {
        "name": "WO-CM-2026-00042",
        "repair_type": "Corrective",
        "priority": "Urgent",
        "open_datetime": "2026-04-14 07:15:00",
        "completion_datetime": "2026-04-15 14:30:00",
        "mttr_hours": 31.25,
        "sla_breached": 1,
        "root_cause_category": "Electrical",
        "repair_summary": "Thay tụ C12 trên board nguồn..."
      }
    ]
  }
}
```

**Ghi chú:** Chỉ trả về WO có `docstatus = 1` (đã Submit). Sort theo `open_datetime desc`. `limit` mặc định 10.

---

### 3.15 Firmware Change Request — transition endpoint (BR-09-18/19/20, Vòng 10) ✅ BUILT (BE/FE Bước-4)

> **Đóng ASYMMETRY + lỗ bảo mật:** thay `05 §10.2` cũ *("`approve_firmware_fcr` — quản lý qua Frappe Desk form, chưa có custom endpoint")*. FCR có state machine SERVER-controlled `_FCR_VALID_TRANSITIONS` (§04 §3.1-bis). Status **chỉ đổi** qua endpoint transition dưới đây; `update_firmware_cr` (CRUD chung) **STRIP** field điều khiển.

**Vị trí endpoint (BE-FE naming contract):** 1 endpoint dispatcher `transition_firmware_cr(name, action, reason)` đặt ở **`api/imm00.py`** (co-locate cạnh CRUD firmware list/get/create/update/delete đã có ở đây; khớp path FE gọi `frontend/src/api/imm00.ts::transitionFirmwareCr` = `assetcore.api.imm00.transition_firmware_cr`). Controller mỏng → delegate `services/imm09.py::transition_firmware_cr` (business logic + audit co-locate cạnh firmware repair logic, lazy-import né circular). *(Refinement từ bản 🟡 SPEC 4-endpoint: gộp 1 dispatcher action-based để khớp FE đã build + One-Version; state machine/capability/event GIỮ NGUYÊN.)*

**Endpoint:** `POST /api/method/assetcore.api.imm00.transition_firmware_cr` — body `{name, action, reason?}`.

| `action` | Cạnh | Capability | Side-effect | Lifecycle Event |
|---|---|---|---|---|
| `submit` | Draft → Pending Approval | `repair.write` | — | — |
| `approve` | Pending Approval → Approved | **`firmware.approve`** | set `approved_by`, `approved_datetime` | `firmware_cr_approved` |
| `deploy` | Approved → Applied | `repair.write` | set `applied_datetime` | `firmware_deployed` |
| `rollback` | Applied → Rolled Back | **`firmware.approve`** | reqd `reason` → `rollback_reason` | `firmware_rolled_back` |

**Request:** `submit`/`approve`/`deploy` → `{name, action}`; `rollback` → `{name, action:"rollback", reason}` (reqd — rỗng → `VALIDATION`). `action` ngoài 4 giá trị → `INVALID_PARAMS`.

**Response 200 (success):** `{"success": true, "data": {"name": "FCR-2026-00007", "status": "Approved"}}` (route-by-VALUE `body.success`; FE reload `get_firmware_cr` sau đó để lấy `allowed_transitions`/`can_approve` mới).

**Response 200 (business error — in-handler HTTP-200 + Error envelope, KHÔNG raise→4xx):**

| Tình huống | `code` | Thông điệp VN |
|---|---|---|
| Repair User bấm Duyệt/Hoàn tác (thiếu `firmware.approve`) | `FORBIDDEN` | "Bạn không có quyền phê duyệt yêu cầu đổi firmware" |
| Chuyển ngoài `_FCR_VALID_TRANSITIONS` (nhảy-cóc/lùi) | `BAD_STATE` | "Không thể chuyển yêu cầu đổi firmware từ '{from}' sang '{to}'" |
| `action="rollback"` thiếu `reason` | `VALIDATION` | "Lý do hoàn tác là bắt buộc" |
| `action` không hợp lệ | `INVALID_PARAMS` | "Hành động không hợp lệ cho yêu cầu đổi firmware" |
| FCR không tồn tại | `NOT_FOUND` | "Không tìm thấy yêu cầu đổi firmware" |

> **2 loại 403 (DONE-gate):** Guest/no-token gõ POST @whitelist → **dispatcher-403** (trước handler, re-auth). User đã đăng nhập thiếu quyền duyệt → **business error → HTTP-200 Error envelope** (`code=FORBIDDEN`, show-msg inline), KHÔNG 403-line. Xem ADR-IMM09-FCR-03 (§04).

**`get_firmware_cr` (api/imm00.py) — enrich (Vòng 10):** thêm 2 field vào `data`:

```json
{
  "success": true,
  "data": {
    "name": "FCR-2026-00007", "asset_ref": "AC-ASSET-2026-00042",
    "status": "Pending Approval", "version_before": "1.2.0", "version_after": "1.3.1",
    "allowed_transitions": ["Approved"],
    "can_approve": true
  }
}
```

- `allowed_transitions[]` = `_FCR_VALID_TRANSITIONS.get(status,[])` **đã LỌC** theo capability caller (Repair User xem FCR Pending Approval → `[]`; Manager → `["Approved"]`). `can_approve` = **boolean** `true/false` theo `rbac.can("firmware.approve")` (BE trả `bool(...)` — FE web so `=== true`, KHÔNG int `1/0`). FE gate nút CHỈ theo 2 field này — KHÔNG hardcode `fcr.status==='X'` (BR-09-20).

**`update_firmware_cr` (api/imm00.py) — hardened (Vòng 10):** STRIP `_FCR_CONTROLLED_FIELDS = {status, approved_by, approved_datetime, applied_datetime, rollback_reason}` khỏi payload → **status KHÔNG BAO GIỜ đổi qua CRUD chung** (dù caller gửi `status=Approved`). Field tự do (`change_notes`/`source_reference`/`version_*` khi Draft) vẫn sửa được. Test: gọi `update_firmware_cr(name, status='Approved')` → assert `status` giữ nguyên (TC-FCR-CRUD-GUARD-01).

---

## §4 Error Code Catalog

> **Cột `message_code`** (Sprint Notification 2026-05-29) trỏ vào registry
> `assetcore/utils/messages.py:MESSAGES`. BE raise qua `nthrow(MSG.<code>, **ctx)`;
> handler `api_handler.handle()` tự hydrate `title/severity/action_hint` từ registry
> rồi đưa vào envelope `_err`. FE đọc `messageCode` → `useNotify().fromError()`.
> Xem §11 Notification Contract.

| Code | HTTP | Severity | `message_code` (MSG.*) | Business Rule | Mô tả |
|---|---|---|---|---|---|
| `CM-001` | 400 | warning | `IMM09_SOURCE_REQUIRED` | BR-09-01 | WO thiếu cả `incident_report` và `source_pm_wo` |
| `CM-002` | 409 | warning | `IMM09_ASSET_HAS_OPEN_WO` | BR-09-05 | Asset đã có WO active (status ≠ Completed / Cannot Repair / Cancelled) |
| `CM-003` | 422 | warning | `IMM09_SPARE_NO_STOCK_ENTRY` | BR-09-02 | Spare parts row thiếu `stock_entry_ref` |
| `CM-004` | 422 | warning | `IMM09_STOCK_ENTRY_NOT_FOUND` | BR-09-02 | `stock_entry_ref` không tồn tại trong DB |
| `CM-005` | 422 | warning | `IMM09_FCR_REQUIRED` | BR-09-03 | `firmware_updated=1` nhưng không có FCR linked |
| `CM-006` | 422 | warning | `IMM09_FCR_NOT_APPROVED` | BR-09-03 | FCR linked status ≠ `"Approved"` |
| `CM-007` | 422 | warning | `IMM09_CHECKLIST_INCOMPLETE` | BR-09-04 | Checklist row chưa điền `result` |
| `CM-008` | 422 | warning | `IMM09_CHECKLIST_FAILED` | BR-09-04 | Checklist có row `result = "Fail"` |
| `CM-009` | 404 | warning | `IMM09_ASSET_NOT_FOUND` | — | `asset_ref` không tồn tại |
| `CM-010` | 403 | warning | `AUTH_FORBIDDEN` | — | User không có quyền (role mismatch) |
| `CM-011` | 404 | warning | `IMM09_NOT_FOUND` | — | WO `name` không tồn tại |
| `CM-012` | 422 | warning | `IMM09_BAD_STATE` | — | Transition status không hợp lệ |
| `CM-013` | 400 | warning | `IMM09_DEPT_HEAD_REQUIRED` | — | Thiếu `dept_head_name` khi close mode Completed |
| `CM-014` | 422 | warning | `IMM09_INCIDENT_REPORT_NOT_FOUND` | BR-09-CREATE-FK | `incident_report` truyền non-empty nhưng Incident Report không tồn tại (R26, gate `create_work_order`; `code='VALIDATION_ERROR'` override). FK rỗng → standalone hợp lệ (KHÔNG lỗi). |
| `CM-015` | 422 | warning | `IMM09_SOURCE_PM_WO_NOT_FOUND` | BR-09-CREATE-FK | `source_pm_wo` truyền non-empty nhưng PM Work Order không tồn tại (R26, gate `create_work_order`; `code='VALIDATION_ERROR'` override). FK rỗng → standalone hợp lệ (KHÔNG lỗi). |
| _(success)_ | 200 | success | `IMM09_CREATE_SUCCESS` | — | Tạo WO thành công (envelope `_ok`, không phải lỗi) |

**Quy tắc severity (chốt cho sprint này):**
- `warning` = lỗi nghiệp vụ user tự sửa được (validation, bad-state, not-found) → toast vàng, GIỮ form, không reload.
- `error` = lỗi hệ thống (`SYS-*`) → toast đỏ.
- `critical` = chặn vì tuân thủ NĐ98 / SLA breach (`IMM09_SLA_EXPIRED`, compliance gate) → modal blocking.
- `success` = thao tác thành công → toast xanh, có thể đóng form.
- `info` = thông tin trung tính (vd tái hỏng cảnh báo non-blocking).

---

## §5 FE ↔ BE Error Mapping

| BE code | FE xử lý |
|---|---|
| `CM-001` | Toast đỏ "Phải có Incident Report hoặc PM Work Order nguồn" |
| `CM-002` | Toast đỏ + link đến WO đang mở của thiết bị |
| `CM-003` | Highlight dòng vật tư thiếu phiếu xuất kho màu đỏ |
| `CM-004` | Hiển thị ⚠ cạnh ô `stock_entry_ref` không hợp lệ |
| `CM-005` | Nhắc "Cần tạo Firmware Change Request trước khi hoàn thành" |
| `CM-006` | Nhắc "FCR chưa được phê duyệt" + link đến FCR |
| `CM-007` / `CM-008` | Highlight dòng checklist chưa đủ / có Fail |
| `CM-010` | Redirect về trang 403 |
| `CM-011` | Trang 404 "Phiếu sửa chữa không tồn tại" |
| `CM-012` | Toast "Không thể thực hiện hành động ở trạng thái hiện tại" |

---

## §6 TypeScript Types

```typescript
// types/imm09.ts

export type RepairStatus =
  | 'Open'
  | 'Assigned'
  | 'Diagnosing'
  | 'Pending Parts'
  | 'In Repair'
  | 'Pending Inspection'
  | 'Completed'
  | 'Cannot Repair'
  | 'Cancelled'

export interface RepairWO {
  name: string
  asset_ref: string
  asset_name: string
  asset_category: string
  risk_class: string
  serial_no: string
  incident_report: string | null
  source_pm_wo: string | null
  repair_type: string
  priority: 'Normal' | 'Urgent' | 'Emergency'
  status: RepairStatus
  open_datetime: string
  assigned_datetime: string | null
  completion_datetime: string | null
  sla_target_hours: number
  mttr_hours: number | null
  sla_breached: boolean
  is_repeat_failure: boolean
  is_warranty_claim: boolean
  assigned_to: string | null
  diagnosis_notes: string | null
  root_cause_category: string | null
  spare_parts_used: SparePartRow[]
  total_parts_cost: number
  repair_checklist: ChecklistRow[]
  firmware_updated: boolean
  firmware_change_request: string | null
  dept_head_name: string | null
  asset_info?: AssetInfo
}

export interface SparePartRow {
  idx: number
  item_code: string
  item_name: string
  qty: number
  uom: string
  unit_cost: number
  total_cost: number
  stock_entry_ref: string | null
}

export interface ChecklistRow {
  idx: number
  test_description: string
  test_category: string
  result: 'Pass' | 'Fail' | 'N/A' | null
  measured_value: string | null
  expected_value: string | null
  notes: string | null
}

export interface AssetInfo {
  asset_name: string
  asset_category: string
  lifecycle_status: string
  risk_classification: string
  manufacturer_sn: string
  department: string | null
  location: string | null
}

export interface RepairKpis {
  total_completed: number
  mttr_avg_hours: number
  sla_compliance_pct: number
  repeat_failure_count: number
  open_wos: number
}

export interface MttrReport {
  mttr_avg: number
  first_fix_rate: number
  backlog_count: number
  cost_per_repair: number
  mttr_trend: { month: string; value: number }[]
  backlog_by_dept: { dept: string; count: number }[]
}
```

---

## §7 Webhook Events (Realtime)

| Channel | Trigger | Payload | Subscriber |
|---|---|---|---|
| `cm_sla_breached` | Scheduler hourly phát hiện WO vượt SLA | `{"wo": "WO-CM-...", "asset": "AC-ASSET-..."}` | KTV được gán (`assigned_to`) |

Phát qua `frappe.publish_realtime(channel, payload, user=assigned_to)`. FE subscribe trong `stores/imm09.ts` qua socket event `cm_sla_breached`.

### §7.1 Dashboard KPI `cm_sla_breached` ↔ drill list — live-SoT canonical-value rule (BR-09-07 LIVE)

KPI thẻ `cm_sla_breached` ('SLA vi phạm', `api/dashboard.py`) và list drill khi click thẻ (`/cm/work-orders?sla_breached=1`) PHẢI đếm **cùng một tập WO** — lệch sẽ làm số trên thẻ ≠ số dòng list (canonical-value rule, mất niềm tin người dùng).

#### Self-Correction — bug thiết kế gốc (đếm cờ stale → undercount cửa-sổ-trễ-scheduler)

Bản trước định nghĩa tập canonical = `_count("Asset Repair", {"sla_breached": 1})` — **chỉ đếm cờ đã stamp**. Cờ `sla_breached` chỉ được set bởi (a) `complete_repair()` lúc đóng WO, hoặc (b) scheduler hourly `check_repair_sla_breach()`. ⇒ một WO **đang mở** vừa vượt hạn 1–59 phút (`open_datetime + sla_target_hours < now()`) nhưng scheduler CHƯA quét tới sẽ có `sla_breached = 0` ⇒ **KHÔNG được đếm** trên card cho đến đầu giờ kế tiếp = **undercount cửa-sổ-trễ-scheduler**. Manager nhìn thấy 0 trong khi thực tế đã có 1 WO breach SLA. → **Sửa Core Doc TRƯỚC:** chuyển sang **live SoT predicate** (đồng dạng IMM-12 BR-12-09).

#### Định nghĩa tập canonical LIVE (SoT)

Một WO tính là "SLA vi phạm" nếu thuộc **một trong hai** nhánh **loại trừ nhau** (mutually-exclusive — né OR/double-count):

| Nhánh | Predicate | Ngữ nghĩa |
|---|---|---|
| **(1) Cờ lịch sử monotonic** | `sla_breached = 1` | Sự thật đã chốt — WO Completed vi phạm (mttr ≥ target) hoặc đã được scheduler stamp. KHÔNG bao giờ lật 0. |
| **(2) Live-overdue đang mở (cờ chưa kịp stamp)** | `open_repair_filter()` ∧ `sla_breached = 0` ∧ `open_datetime + sla_target_hours < now()` | WO **đang mở** đã quá hạn nhưng scheduler chưa quét. `open_repair_filter()` loại tự nhiên terminal (Completed/Cannot Repair/Cancelled). |

- **KPI count (SoT helper `cm_sla_breach_count()` tại `services/imm09.py`):**
  `count(sla_breached=1)` + `count(sla_breach_live_filter() ∧ sla_breached=0)` — 2 nhánh exclusive (cờ=1 và cờ=0), không bao giờ chồng ⇒ **idempotent vs scheduler**: chạy cùng tập trước/sau khi scheduler stamp ⇒ count KHÔNG đổi (1 WO chỉ tính 1 lần dù vừa live-overdue vừa cờ=1).
- **Drill (`_drill("/cm/work-orders", sla_breached="1")`):** `list_work_orders({"sla_breached": 1})` → enrich per-row `is_sla_breached` LIVE (cờ thô ?? live-overdue-derive) ⇒ độ dài list == count card trên **cùng tập live đúng** (không lệch ở cửa-sổ-trễ).

#### Invariants (acceptance đo được)

| ID | Invariant |
|---|---|
| INV-CM-SLA-1 | WO OPEN có `open_datetime + sla_target_hours < now()` nhưng `sla_breached=0` (chưa scheduler) → card 'SLA vi phạm' đếm **+1 NGAY** (không đợi scheduler hourly). |
| INV-CM-SLA-2 (idempotent) | Chạy cùng tập trước & sau khi scheduler stamp cờ → `cm_sla_breached` KHÔNG đổi (no double-count: 1 WO tính 1 lần). |
| INV-CM-SLA-3 (no-regression cờ lịch sử) | WO Completed có `sla_breached=1` (monotonic) VẪN đếm như cũ; WO Completed trong-hạn (`sla_breached=0`, mttr<target) KHÔNG đếm. |
| INV-CM-SLA-4 (terminal loại tự nhiên) | WO terminal (Cannot Repair/Cancelled) quá hạn nhưng `sla_breached=0` → KHÔNG phantom-count vào card open-breach (chỉ open WO + completed-flag-historical đếm). |
| INV-CM-SLA-5 (card == drill LIVE) | Độ dài list `/cm/work-orders?sla_breached=1` (sau `list_work_orders` enrich `is_sla_breached` live) == số card 'SLA vi phạm' — invariant giữ NHƯNG nay trên tập live đúng, không lệch ở cửa-sổ-trễ. |

> **Phân biệt với KPI khác:** nếu nghiệp vụ cần thẻ "SLA breach **đang mở** thuần" (loại completed-flag-historical), đó là KPI KHÁC (`cm_sla_breached_open`, chỉ nhánh (2) ∪ open-cờ=1) — KHÔNG dùng chung label/count với card này. *(Cần khảo sát: hiện chỉ có 1 card hợp nhất.)*

### §7.2 Dashboard KPI `cm_open` ↔ drill list — canonical-value rule (BR-09-08)

KPI thẻ "CM đang mở" (`cm_open`, `get_overview` → `cm.open`) và drill-down list "đang sửa chữa" (`get_dashboard_data` → `active_repairs`) PHẢI đếm **cùng một tập WO**. Số trên thẻ == số dòng list khi user click — nếu lệch, mất niềm tin dashboard.

**Định nghĩa tập canonical (SoT):** "Asset Repair đang mở" ⟺ `status NOT IN REPAIR_TERMINAL_STATES` với `REPAIR_TERMINAL_STATES = {Completed, Cannot Repair, Cancelled}` (định nghĩa DUY NHẤT tại `services/imm09.py`). `Cannot Repair` là **TERMINAL** (thiết bị không cứu được → Out of Service, đồng hồ SLA dừng) — KHÔNG phải đang mở. KHÔNG có literal ma `'Closed'` (DocType enum chỉ có `Open|Assigned|Diagnosing|Pending Parts|In Repair|Pending Inspection|Completed|Cannot Repair|Cancelled`).

- KPI count: `_count("Asset Repair", open_repair_filter())` — dùng filter builder SoT.
- Drill SQL: `WHERE r.status NOT IN (...)` build từ `sorted(REPAIR_TERMINAL_STATES)` (parametrized, byte-for-byte khớp `open_repair_filter()`).
- Persona KTV: `my_cm` = `open_repair_filter({assigned_to})`; `cm_urgent` = `open_repair_filter({assigned_to, priority:'P1'})`.
- SLA engine (`services/notifications.py`): `_REPAIR_TERMINAL_STATUS` là **alias-import** của `imm09.REPAIR_TERMINAL_STATES` (1 SoT, không 2 frozenset song song).

> Acceptance đo được: 1 Asset Repair ở `Cannot Repair` KHÔNG tính vào `cm_open` VÀ KHÔNG xuất hiện trong `active_repairs` → card == drill (cùng tập).

---

## §8 Endpoint ↔ Business Rule Mapping

| Endpoint | Business Rule áp dụng |
|---|---|
| `create_repair_work_order` | BR-09-01 (nguồn), BR-09-05 (no duplicate), BR-09-06 (SLA tính) |
| `assign_technician` | State machine: Open → Assigned |
| `submit_diagnosis` | State machine: Assigned/Diagnosing → Pending Parts/In Repair |
| `request_spare_parts` | BR-09-02 (gắn stock_entry_ref) |
| `start_repair` | State machine |
| `close_work_order` (Completed) | BR-09-02 (stock entry), BR-09-03 (FCR), BR-09-04 (checklist) — chuyển sang Pending Inspection |
| `confirm_inspection` | Nghiệm thu: role CAN_APPROVE_DEP → submit doc → complete_repair() → MTTR/SLA/ALE |
| `attach_repair_checklist_photo` | BR-09-15 (permission + validation reject-before-insert), BR-09-16 (lifecycle `repair_checklist_photo_attached` hard-req + read-back parity + count==rows) — NĐ98 evidence Class C/D |
| `close_work_order` (Cannot Repair) | BR-09-05 (Asset → Out of Service) |
| `get_repair_kpis` / `get_mttr_report` | BR-09-07 (theo dõi KPI MTTR) |
| `get_asset_repair_history` | Audit trail + BR-09-06 (detect repeat failure) |

---

## §9 Smoke Test Playbook

```bash
BASE="https://acme.local/api/method/assetcore.api.imm09"
AUTH="Authorization: token KEY:SECRET"

# 1. Tạo WO
curl -s -X POST "$BASE.create_repair_work_order" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"asset_ref":"AC-ASSET-0001","repair_type":"Corrective","priority":"Urgent",
       "failure_description":"Không khởi động","incident_report":"IR-0001","source_pm_wo":""}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin)['message']; print(d['data']['name'])"

WO="WO-CM-2026-00001"

# 2. Phân công KTV
curl -s -X POST "$BASE.assign_technician" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"$WO\",\"technician\":\"ktv@hospital.vn\"}" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['message']['data']['status'])"

# 3. Nộp chẩn đoán
curl -s -X POST "$BASE.submit_diagnosis" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"$WO\",\"diagnosis_notes\":\"Hỏng cầu chì\",\"needs_parts\":0}" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['message']['data']['status'])"

# 4. Đóng WO → Pending Inspection
curl -s -X POST "$BASE.close_work_order" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"$WO\",\"repair_summary\":\"Đã thay cầu chì\",\"root_cause_category\":\"Electrical\",
       \"dept_head_name\":\"BS Hùng\",\"checklist_results\":\"[]\",\"cannot_repair\":0}" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['message']['data']['status'])"
# expect: Pending Inspection

# 5. Nghiệm thu → Completed
curl -s -X POST "$BASE.confirm_inspection" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"$WO\"}" | python3 -c \
  "import sys,json; d=json.load(sys.stdin)['message']['data']; print(d['status'], d['mttr_hours'])"
# expect: Completed <float>

# 6. Kiểm tra KPI
curl -s -G "$BASE.get_repair_kpis" -H "$AUTH" \
  --data-urlencode "year=2026" --data-urlencode "month=4" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['message']['data']['kpis'])"
```

---

## §10 Implementation Notes

### §10.1 Path map docs ↔ code (v2.0)

| Docs cũ (v1) | Code thực tế (v2.0) |
|---|---|
| `create_repair_wo` | `create_repair_work_order` |
| `submit_repair_result` | Gộp vào `close_work_order` |
| `complete_repair` | Tách 2 bước: `close_work_order(cannot_repair=0)` → Pending Inspection, rồi `confirm_inspection` → Completed |
| `mark_cannot_repair` | `close_work_order(cannot_repair=1)` |
| `get_repair_wo` | `get_repair_work_order` |
| `get_repair_list` | `list_repair_work_orders` |
| `get_repair_backlog` | Trích từ `get_mttr_report.backlog_*` |

### §10.2 Implementation status

| Hạng mục | Trạng thái |
|---|---|
| `search_spare_parts` endpoint | ✅ Đã implement — `api/imm09.py` + `services/imm09.py` + FE `@/api/imm09.searchSpareParts()` |
| `submit_firmware_cr` / `approve_firmware_cr` / `deploy_firmware_cr` / `rollback_firmware_cr` | 🟡 SPEC Vòng 10 (§3.15) — transition SERVER-controlled `_FCR_VALID_TRANSITIONS` (`api/imm09.py` + `services/imm09.py`); status KHÔNG còn đổi qua Desk/CRUD chung. Deploy sau code: `reload-doctype "Asset Lifecycle Event"` (3 event enum) + worker reload + `after_migrate invalidate_capabilities()` (cap `firmware.approve`). |
| `update_firmware_cr` status-strip | 🟡 SPEC Vòng 10 — STRIP `_FCR_CONTROLLED_FIELDS` khỏi CRUD chung (BR-09-19b) |
| MTTR theo working hours | Hiện tính calendar time; cần util `get_working_hours_between` khi cần chính xác hơn |

### §10.3 `ignore_permissions` & `ignore_links`

Production cần review: `doc.flags.ignore_links = True` và `save(ignore_permissions=True)` hiện dùng để tránh lỗi trong môi trường test. Bật đầy đủ permission check trước khi go-live.

---

## §11 Notification Contract (Sprint Notification 2026-05-29) — SINGLE SOURCE OF TRUTH

Mọi tương tác IMM-09 trả về **envelope chuẩn** đã chuẩn hoá BE → FE. FE KHÔNG
hardcode câu chữ — chỉ đọc `messageCode` rồi render qua `useNotify`.

### §11.1 Envelope shape

Success (`_ok`):
```json
{ "ok": true, "data": { ... } }
```
Lỗi (`_err`, hydrate từ registry qua `api_handler.handle()`):
```json
{
  "ok": false,
  "error": {
    "code": "BAD_STATE",                 // ErrorCode bucket (coarse)
    "message": "Không thể thực hiện khi lệnh sửa chữa đang ở trạng thái 'Completed'.",
    "message_code": "IMM09-BAD-STATE",   // MSG.* key → FE tra registry
    "severity": "warning",                // success|info|warning|error|critical
    "title": "Sai trạng thái lệnh sửa chữa",
    "action_hint": "Chỉ áp dụng khi lệnh đang ở trạng thái Open.",
    "context": { "state": "Completed", "expected": "Open" },
    "http_status": 409
  }
}
```

**Bất biến (contract):** mọi error envelope IMM-09 PHẢI có `message_code`, `severity`,
`title`. Không còn `frappe.throw(_("..."))` thô leak message Frappe ra FE.

### §11.2 Danh mục MSG cần bổ sung vào `utils/messages.py`

5 mã IMM09 đã có (`IMM09_NOT_FOUND`, `IMM09_BAD_STATE`, `IMM09_ASSET_LOCKED`,
`IMM09_SLA_EXPIRED`, `IMM09_CREATE_SUCCESS`). Sprint này thêm **9 mã mới**:

| MSG.* | code (kebab) | severity | http | title | template (VI) | action_hint |
|---|---|---|---|---|---|---|
| `IMM09_SOURCE_REQUIRED` | `IMM09-SOURCE-REQUIRED` | warning | 400 | Thiếu nguồn lệnh sửa chữa | Lệnh sửa chữa nguồn `{source_type}` yêu cầu liên kết {required_doc}. | Chọn bản ghi nguồn tương ứng trước khi tạo lệnh. |
| `IMM09_ASSET_HAS_OPEN_WO` | `IMM09-ASSET-HAS-OPEN-WO` | warning | 409 | Thiết bị đang có lệnh mở | Thiết bị đang có lệnh sửa chữa đang mở: {existing}. | Đóng lệnh sửa chữa hiện tại trước khi tạo lệnh mới. |
| `IMM09_SPARE_NO_STOCK_ENTRY` | `IMM09-SPARE-NO-STOCK-ENTRY` | warning | 422 | Vật tư thiếu phiếu xuất kho | Vật tư '{item_name}' (dòng {idx}) chưa có phiếu xuất kho. | Tạo phiếu xuất kho cho vật tư này rồi thử lại. |
| `IMM09_STOCK_ENTRY_NOT_FOUND` | `IMM09-STOCK-ENTRY-NOT-FOUND` | warning | 422 | Phiếu xuất kho không tồn tại | Phiếu xuất kho '{stock_entry_ref}' không tồn tại. | Kiểm tra lại mã phiếu xuất kho. |
| `IMM09_FCR_REQUIRED` | `IMM09-FCR-REQUIRED` | warning | 422 | Cần yêu cầu đổi firmware | Cập nhật firmware yêu cầu phải có Yêu cầu đổi Firmware (FCR) được phê duyệt. | Tạo và phê duyệt FCR trước khi hoàn thành lệnh. |
| `IMM09_FCR_NOT_APPROVED` | `IMM09-FCR-NOT-APPROVED` | warning | 422 | FCR chưa được phê duyệt | FCR '{fcr}' chưa được phê duyệt (trạng thái: {status}). | Chờ FCR được phê duyệt rồi thử lại. |
| `IMM09_CHECKLIST_INCOMPLETE` | `IMM09-CHECKLIST-INCOMPLETE` | warning | 422 | Checklist chưa hoàn tất | Mục kiểm tra #{idx} '{test_description}' chưa điền kết quả. | Điền đầy đủ kết quả các mục kiểm tra trước khi hoàn thành. |
| `IMM09_CHECKLIST_FAILED` | `IMM09-CHECKLIST-FAILED` | warning | 422 | Có mục kiểm tra chưa đạt | Mục kiểm tra #{idx} '{test_description}' chưa Pass — không thể hoàn thành. | Khắc phục và đánh giá lại mục kiểm tra này trước khi hoàn thành. |
| `IMM09_ASSET_NOT_FOUND` | `IMM09-ASSET-NOT-FOUND` | warning | 404 | Không tìm thấy thiết bị | Không tìm thấy thiết bị: {asset}. | Kiểm tra lại mã thiết bị trong danh mục tài sản. |
| `IMM09_DEPT_HEAD_REQUIRED` | `IMM09-DEPT-HEAD-REQUIRED` | warning | 400 | Thiếu người nghiệm thu | Cần nhập tên trưởng khoa/phòng nghiệm thu khi đóng lệnh hoàn thành. | Nhập tên người nghiệm thu rồi thử lại. |
| `IMM09_INCIDENT_REPORT_NOT_FOUND` | `IMM09-INCIDENT-REPORT-NOT-FOUND` | warning | 422 | Không tìm thấy báo cáo sự cố | Không tìm thấy báo cáo sự cố nguồn: {incident_report}. | Chọn báo cáo sự cố từ danh sách, hoặc để trống nếu tạo phiếu sửa chữa độc lập. |
| `IMM09_SOURCE_PM_WO_NOT_FOUND` | `IMM09-SOURCE-PM-WO-NOT-FOUND` | warning | 422 | Không tìm thấy lệnh bảo trì nguồn | Không tìm thấy lệnh bảo trì định kỳ nguồn: {source_pm_wo}. | Chọn lệnh bảo trì từ danh sách, hoặc để trống nếu tạo phiếu sửa chữa độc lập. |

> **R26 (create_work_order FK gate):** 2 mã trên thêm cho referential-integrity gate 2 optional Link FK. Service gọi `nthrow(..., error_code=ErrorCode.VALIDATION_ERROR)` ⇒ envelope `code='VALIDATION_ERROR'` (KHÔNG `BUSINESS_RULE` mặc-định-422) + `http_status=422`. Xem ADR-IMM09-CREATE-FK (04 §3.4).

> Lưu ý content: tuân `messages.py` §quy chuẩn — Chủ thể + Hậu quả + Hành động,
> không từ kỹ thuật, không đổ lỗi user. Sau khi thêm vào `messages.py`, chạy
> `python scripts/gen_fe_messages.py` để regen `frontend/src/i18n/messages.ts`.

### §11.3 BE migration checklist (cho assetcore-be)

- `services/imm09.py`: thay 11 `frappe.throw(_(...))` → `nthrow(MSG.IMM09_*, **ctx)`;
  các `raise ServiceError(...)` NOT_FOUND/BAD_STATE hiện có → bổ sung `message_code=MSG.*`.
- `api/imm09.py`: bỏ `_handle`/`_err`/`_parse_json` cục bộ → dùng
  `from assetcore.utils.api_handler import handle, parse_json`.
- Giữ nguyên `frappe.publish_realtime` cho SLA breach (§7) — không thay đổi.
- Audit trail (`log_lifecycle_event`) KHÔNG đổi — message framework chỉ chuẩn hoá phản hồi user.

### §11.4 FE migration checklist (cho assetcore-fe)

- Views `repair/*` + `incident/*` (nếu chạm IMM-09): thay `toast.error(msg)` / hardcode
  success → `notify.fromError(e)` trong catch, `notify.fromOk(resp)` hoặc
  `notify.show({ code: MSG.IMM09_CREATE_SUCCESS, ctx })` khi thành công.
- KHÔNG còn `try/catch` tự build string từ `e.message` BE.

---

*End of IMM-09 API Specification v1.0 — Corrective Maintenance.*
*Notification Contract §11 added 2026-05-29 (Sprint chuẩn hoá thông báo).*
