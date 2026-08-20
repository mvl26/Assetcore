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
> - **✅ ĐÃ CHỐT 2026-07-25 (bất đối xứng PQC rows-vs-count) — xem BR-09-LISTSCOPE dưới + [ADR-IMM00-LIST-SCOPE §8](../imm-00/ADR-IMM00-LIST-SCOPE.md).** Cảnh báo "⚠ VERIFY BE Bước-4" của CR-18 đã được xác nhận là **bug THẬT, không chỉ với vendor mà với MỌI KTV nội bộ**: rows = `frappe.get_all` (KHÔNG áp `permission_query_conditions`) vs count = `count_with_or`→`frappe.get_list` (CÓ áp `asset_repair_query` = `assigned_to==user`) ⇒ count < rows **+ rò phiếu người khác**. Quyết định: **rows cũng qua `frappe.get_list`** thông qua `BaseRepository.list(scope="user")` — KHÔNG canh explicit-filter thủ công (dễ drift). Đây là finding riêng (INV-ROWSCOPE), KHÔNG mở rộng scope CR-18.
> - **Nhánh live `sla_breached_live`:** `search` pop TRƯỚC rẽ nhánh; `or_filters` forward vào `_fetch_all_repair_rows`/`_list_sla_breached_live` để chip "Quá hạn SLA" + search compose đúng, count==rows giữ trong tập lọc live.
> - **Recall cap 500 asset/term** → count==rows vẫn giữ (chung id đã cap), recall giảm = `[ROADMAP]` streaming (ADR-IMM00-LIST-SCOPE §4b).

#### ADR-IMM09-SEARCH-01: `search` discrete param + `pop_search`/`escape_like_term` SSoT (CR-18)

- **Status**: Accepted — Date 2026-07-10. Đối xứng PM `ADR-IMM08-SEARCH-01` + tái dùng `ADR-IMM00-SEARCH-ESCAPE`; dùng CHUNG `pop_search`/`escape_like_term`/`BaseRepository.list(or_filters)`.
- **Context**: FE `CMWorkOrderListView` lọc client-side chỉ trang đã tải (`filteredWOs`) → KTV bỏ sót phiếu trang sau. `asset_code`/`asset_name` trên AC Asset (link `asset_ref`). Ràng buộc: count==rows, byte-identical baseline khi trống, KHÔNG nới quyền, chống wildcard-injection/DoS.
- **Decision**: 1 discrete query-param `search` (default `""`) → inject `f["search"]` @api khi non-empty → `pop_search` @service → `or_filters` (parent `name` + link-lookup AC Asset) đã escape → `RepairRepo.list(or_filters=…)` thread chung count+rows.
- **Alternatives**: (A) client-filter → search-trap không sửa được → loại. (B) raw `%term%` không escape → wildcard-injection/DoS → loại. (C) endpoint `search_repair_work_orders` riêng → +1 path, nhân đôi enrich/scope → loại. (D) full-text MATCH…AGAINST → schema migration + đổi count semantics → `[ROADMAP]`.
- **Consequences**: blast-radius = 1 param @api + 1 nhánh `pop_search` @service + forward `or_filters` vào nhánh `sla_breached_live`; count==rows giữ; backward-compat khi trống; recall cap 500 = `[ROADMAP]`; `search` là filter ứng-dụng (bảo mật read vẫn do DocPerm/`asset_repair_query`+vendor-scope).

> **DELTA vòng này (CR-18):** (1) Query-params table thêm `search`; (2) BR-09-LISTSEARCH + ADR-IMM09-SEARCH-01 mới. **BE Bước-4:** `api/imm09.py::list_repair_work_orders(filters, mine, search: str = "", page, page_size)` (inject `f["search"]` khi non-empty); `services/imm09.py::list_work_orders` (pop `search`→`or_filters` qua `pop_search` TRƯỚC `_normalize_filters`, forward vào `_list_sla_breached_live`); `services/shared/filters.py::pop_search` (escape + list display-field); `api/openapi_overrides.py` (khai `search` cho `list_repair_work_orders` + mirror `docs/mobile/openapi/*.yaml`); tests `test_imm09` (count==rows-paginated + escape-literal + AND-vendor/mine + byte-identical-empty). **FE Bước-4:** `CMWorkOrderListView.vue` (server refetch debounce+reset page=1, gỡ `filteredWOs`+search-trap, giữ chip); `api/imm09.ts::listRepairWorkOrders` (+`search`); `stores/imm09.ts::fetchWorkOrders` (forward `search`).

> **BR-09-LISTSCOPE (row-scope của danh sách phiếu CM — CHỐT 2026-07-25, INV-ROWSCOPE):** SSoT quyết định = [`ADR-IMM00-LIST-SCOPE.md` §8](../imm-00/ADR-IMM00-LIST-SCOPE.md) (D4–D7). Tóm tắt ràng buộc cho IMM-09:
>
> - **Predicate row-scope của `Asset Repair` = `assigned_to`** cho KTV nội bộ VÀ vendor (`asset_repair_query`, `permissions.py:113-121`) — **GIỮ NGUYÊN, KHÔNG sửa** (D4). `AC Asset` read-all (D1) **KHÔNG** áp cho phiếu công việc: registry đọc-tham-chiếu ≠ phiếu có hành động ghi.
> - **`list_repair_work_orders` chạy `scope="user"`**: `services/imm09.py::list_work_orders` gọi `RepairRepo.list(..., scope="user")` ⇒ rows qua `frappe.get_list` = **CÙNG DatabaseQuery engine + CÙNG `permission_query_conditions`** với `count_with_or`. Bất biến đo được: **`pagination.total == len(data.data)`** khi `total ≤ page_size`, cho **MỌI persona** (trước fix: KTV thấy `total=2` nhưng 40 dòng).
> - **Bất biến "đọc được ⇒ ghi được"**: với MỌI row KTV nhận từ list, `_assert_can_attach_repair_photo` (`services/imm09.py:1379-1390`) **KHÔNG raise**. Read-gate và write-gate dùng CÙNG predicate `assigned_to` (D5).
> - **Nhánh chip LIVE `sla_breached_live=1`** (`_list_sla_breached_live` → `_fetch_all_repair_rows`) cũng `scope="user"` ⇒ membership chip == badge == số dòng.
> - **Card `cm_sla_breached` ↔ drill (D7)**: `cm_sla_breach_count()` (`services/imm09.py:762`) chuyển permission-aware — nhánh `flagged` đổi `RepairRepo.count` → `count_with_or(...)`, nhánh live truyền `scope="user"`. Nếu KHÔNG làm, drill scoped vs card global ⇒ **phá INV-CM-SLA-5** (§7.1) và tạo lệch MỚI.
> - **`get_asset_repair_history` (§3.14) GIỮ `scope="system"`** — **D6 device-centric**: lịch sử sửa chữa CỦA THIẾT BỊ (read-only, không nút hành động, không dùng làm căn cứ cấp quyền). KTV sắp sửa 1 máy PHẢI đọc được hỏng hóc do đồng nghiệp xử lý trước đó (WHO HTM: traceability gắn vòng đời thiết bị, không gắn danh tính người thực hiện).
>   - **⚠️ CẢI CHÍNH 2026-07-25 (ADR [§8.3b](../imm-00/ADR-IMM00-LIST-SCOPE.md), chờ [BA] ratify hậu kiểm):** `system` = bỏ **ROW-scope**, **KHÔNG** bỏ DocPerm `read` cấp vai-trò. Probe thật trước cải chính: user chỉ có role `PM User` (`has_permission('Asset Repair','read') == False`) gọi `get_asset_repair_history` → `success:true` + đầy đủ `WO-CM-*` (`repair_type`/`mttr_hours`/`root_cause_category`) = **rò dữ liệu (OWASP A01)**. D6 ratify traceability THEO THIẾT BỊ **trong số người được quyền đọc bảng `Asset Repair`**, KHÔNG ratify mở bảng cho vai trò không có DocPerm. Nay endpoint trả **403 envelope trên HTTP-200** cho persona thiếu DocPerm read; muốn họ đọc được ⇒ **cấp DocPerm read** (ADR §8.10 B2), KHÔNG mở lại `get_all` trần.
> - **Lỗi quyền = in-handler 403 trên HTTP-200** (BR-00-ROWSCOPE-403): persona thiếu DocPerm `read` trên `Asset Repair` (`Calibration User`, `Corrective User`, `PM User`, **`Vendor Engineer`**) → `frappe.get_list` raise `PermissionError` → service chuyển `ServiceError(FORBIDDEN, http_status=403)` → `handle()` trả **HTTP-200 + Error envelope**. **KHÔNG** để bubble thành 500; **KHÔNG** trả list rỗng giả. Phân biệt với **dispatcher-403** (guest/no-token, phát TRƯỚC handler → mobile logout).
> - **KHÔNG nới quyền / KHÔNG over-block:** senior (`Repair Manager`/Super Admin/Auditor) vẫn thấy ĐỦ; Vendor Engineer vẫn isolated (D2 bất biến). **TUYỆT ĐỐI KHÔNG nới DocPerm** để chữa test đỏ.
> - **✅ `AC-CR-119` (2026-07-30) — cap SOUND của endpoint này là `repair.read`** → `("Asset Repair","read")` (`services/shared/rbac.py`), **khớp đúng** DocType mà truy vấn đọc (`RepairRepo.DOCTYPE`) ⇒ **KHÔNG cần cap mới** cho IMM-09. Khai chính thức 1 lần ở SSoT `services/shared/connection_meta.py::OP_HISTORY_BRANCH_GATE["cm"] = ("repair.read", "Asset Repair")`, khoá bằng guard `CAPABILITY_MAP[cap] == (doctype, "read")` (`INV-OPH-32`, `assetcore/tests/integration/test_asset_op_history_acl.py`). **Hệ quả consumer (IMM-00):** section «Lần sửa chữa đã hoàn thành» hỏi `repair.read` **TRƯỚC** khi gọi ⇒ persona thiếu DocPerm (`PM User`, `Calibration User`, `Corrective User`, `Vendor Engineer` — bảng trên) **không** còn phát request vô vọng, và nhận **trạng thái KHOÁ** (`[op-history-locked]`, 0 «Thử lại») thay vì dải lỗi đỏ. Envelope BE **KHÔNG đổi 1 ký tự**; xem [`docs/imm-00/05 §III.26.7`](../imm-00/05_API_Specification.md) + [`ADR-IMM00-ASSET-OP-HISTORY §11`](../imm-00/ADR-IMM00-ASSET-OP-HISTORY.md).
> - **[BACKLOG-P1 · cần USER ratify]** Vendor Engineer **thiếu DocPerm `read`** trên `Asset Repair` trong khi contract mobile + `apply_vendor_scope` giả định vendor list được → quyết riêng, KHÔNG xử trong vòng này (ADR §8.10 B2). Cùng nhóm: IDOR detail `RepairRepo.get` → `frappe.get_doc` không tự gọi `has_permission` (B3).

> **DELTA vòng này (INV-ROWSCOPE, 2026-07-25):** (1) bullet "⚠ VERIFY BE Bước-4" của CR-18 → **✅ ĐÃ CHỐT** (ở trên); (2) **BR-09-LISTSCOPE** mới. **BE Bước-4:** `repositories/base.py` (`scope` param) · `services/shared/filters.py` (`count_ignore_permissions`) · `services/imm09.py` (6 call site `RepairRepo.list` khai `scope` tường minh + `cm_sla_breach_count` permission-aware + chuyển `PermissionError`→`ServiceError(FORBIDDEN)`) · `services/notifications.py:1107` (`scope="system"`) · test `assetcore/tests/integration/test_rowscope_invariant.py`. **FE Bước-4:** `CMWorkOrderListView.vue:165` ("Tổng" từ `pagination.total ?? 0`) + vitest guard — xem `06_Frontend_Design.md §VI`.

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
    "repair_checklist": [
      {
        "name": "a1b2c3d4e5",
        "idx": 1,
        "test_description": "Đo điện trở nối đất bảo vệ (protective earth resistance)",
        "test_category": "Electrical",
        "expected_value": "< 0.2 Ω",
        "measured_value": "0.11 Ω",
        "result": "",
        "notes": null,
        "photo": null
      }
    ],
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
    "allowed_transitions": ["Pending Inspection", "Cannot Repair", "Cancelled"],
    "available_actions": [
      {"key": "assign_technician",   "label": "Phân công kỹ thuật viên", "route": "", "enabled": false, "reason": "Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu"},
      {"key": "submit_diagnosis",    "label": "Ghi nhận chẩn đoán",      "route": "", "enabled": false, "reason": "Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu"},
      {"key": "request_spare_parts", "label": "Yêu cầu phụ tùng",        "route": "", "enabled": true,  "reason": ""},
      {"key": "start_repair",        "label": "Bắt đầu sửa chữa",        "route": "", "enabled": false, "reason": "Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu"},
      {"key": "close_work_order",    "label": "Hoàn thành sửa chữa",     "route": "", "enabled": true,  "reason": ""},
      {"key": "confirm_inspection",  "label": "Xác nhận nghiệm thu",     "route": "", "enabled": false, "reason": "Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu"}
    ]
  }
}
```

**`is_sla_breached` — cờ LIVE vi-phạm-SLA (CR-37, mobile parity list↔detail):** `boolean` DERIVED Python-bool tại `get_work_order` qua **CÙNG predicate `_enrich_sla_breach`** của list-item (`bool(sla_breached)` OR `_row_is_live_overdue`; BR-09-10: elapsed clock-stop trừ `parts_hold` ⇒ WO ở Pending Parts KHÔNG live-overdue oan). Emit BÊN CẠNH cờ thô STORED `sla_breached` (`Check` → wire int `0/1`), **GIỮ boolean** (KHÔNG int-0/1 — derived). Badge "Vi phạm SLA" màn detail đọc cờ LIVE này ⇒ KHÔNG trễ tới đầu-giờ-kế của scheduler `check_repair_sla_breach`. **INVARIANT parity:** cờ `is_sla_breached` trên detail == cờ trên list-item cùng record.

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

**`available_actions[]` — 6 CTA server-driven (AC-CR-82, mirror AC-CR-77 nửa PM):** ĐÚNG **6 phần tử**, thứ tự **CỐ ĐỊNH** `[assign_technician, submit_diagnosis, request_spare_parts, start_repair, close_work_order, confirm_inspection]`, **luôn đủ 6** kể cả ở trạng thái terminal (khi đó cả 6 `enabled=false`). Mỗi phần tử = `AvailableAction` `{key,label,route,enabled,reason}`, `route=""` (CTA nằm **trong** màn Chi tiết). `enabled = transition_allowed ∩ has_cap ∩ business_gate`; `enabled=false ⟹ reason` VI **khác rỗng**. **KHÁC ngữ nghĩa** `allowed_transitions` (trạng-thái-kế của máy trạng thái ≠ hành động có đường thực thi) — client mới gate nút bằng **`available_actions`**, `allowed_transitions` giữ nguyên cho client cũ. 👉 Hợp đồng đầy đủ + ma trận 54 ô + 3 ADR: **§15 AC-CR-82** (cuối tài liệu này).

**Lỗi:** `CM-011` (404) nếu WO không tồn tại.

#### `repair_checklist[]` — checklist nghiệm thu CM typed trên wire (CR-65, mobile-BE)

**Vấn đề đóng (CR-65):** `get_work_order` trả `data = doc.as_dict()` (`services/imm09.py:1307`) ⇒ mảng con `repair_checklist` **luôn có mặt** trong payload, nhưng OpenAPI mobile (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`) **chưa khai** field này — nó chỉ "sống" nhờ `additionalProperties: true` của `RepairWorkOrderDetail`. Hệ quả đo được: codegen sinh `Any`/`[String: Any]` ⇒ **chuỗi ĐỌC→ĐÍNH-ẢNH bị đứt typed** vì client phải **tự đoán khoá join** khi gọi `attachRepairChecklistPhoto`. CR-65 khai `repair_checklist: array<RepairChecklistItem>` + component schema mới `RepairChecklistItem`.

**Khoá join (⛓️ mấu chốt):** `repair_checklist[].idx` (Frappe child `idx`, 1-based) là **nguồn DUY NHẤT** của `AttachRepairChecklistPhotoRequest.checklist_item_idx` — service so khớp `int(row.idx) == int(checklist_item_idx)` (`_find_repair_checklist_row` @`services/imm09.py:1358-1366`) vì **Repair Checklist KHÔNG có field STT domain riêng** (khác PM Checklist Result có `checklist_item_idx` là field domain). ⇒ **2 đầu PHẢI cùng `type: integer`** (đọc `idx` · request `checklist_item_idx` · response `checklist_item_idx` — 3-way parity, guard `cr65_d`).

**Schema `RepairChecklistItem`** — grounded 1:1 `assetcore/assetcore/doctype/repair_checklist/repair_checklist.json` (7 field domain) + 2 khoá meta Frappe. **KHÔNG bịa field ngoài DocType** (guard `cr65_c` đọc trực tiếp doctype json).

| Field | Kiểu wire | Nguồn @source | Ghi chú hợp đồng |
|---|---|---|---|
| `name` | string | child row PK (as_dict) | dedupe/diff cục bộ — **KHÔNG** dùng làm khoá đính ảnh |
| `idx` | **integer** (non-null) | Frappe child idx 1-based | ⛓️ khoá join đính ảnh (xem trên) |
| `test_description` | string, nullable | `repair_checklist.json` Data (reqd:1) | dòng seed CR-50 điền sẵn |
| `test_category` | string, nullable | Select `Electrical\|Mechanical\|Software\|Safety\|Performance` | **KHÔNG enum-bound cứng** (né contract-drift khi options doctype đổi) |
| `expected_value` | string, nullable | Data | as-emitted, KHÔNG ép number |
| `measured_value` | string, nullable | Data | KTV nhập hiện trường; as-emitted |
| `result` | string, nullable | Select `Pass\|Fail\|N/A` | **KHÔNG enum cứng** — xem ADR bên dưới |
| `notes` | string, nullable | Text | |
| `photo` | string, nullable | **Attach ĐƠN** | `file_url` private (NĐ98); **KHÔNG array** — `MAX_REPAIR_CHECKLIST_PHOTOS = 1` @`services/imm09.py:348` |

**Boundaries — Always / Never (cho BE/FE/mobile):**

- **Always:** `repair_checklist` emit-luôn (mảng rỗng `[]` với phiếu legacy chưa `backfill_repair_checklists` @`services/imm09.py:2113`); client đính ảnh **chỉ** bằng `idx` đọc từ chính payload này; BR-09-04 (mọi dòng `result == 'Pass'` mới submit được) enforce **server-side** ở `before_submit` (`validate_repair_checklist_complete`).
- **Never:** KHÔNG đưa `repair_checklist` vào `required` của `RepairWorkOrderDetail` (giữ `required: [name]` — client cũ bỏ qua an toàn); KHÔNG đóng `RepairChecklistItem` (`additionalProperties` phải là `true`); KHÔNG khai `result.enum` cứng; KHÔNG khai `photo` là array; KHÔNG suy diễn `idx` từ vị trí mảng phía client (dùng đúng giá trị server phát).

##### ADR-IMM09-CHECKLIST-WIRE-01: `RepairChecklistItem` schema MỞ, `result` không enum, `photo` không array (CR-65)

- **Status**: Accepted — **Date**: 2026-07-25
- **Context**: child rows đến qua `doc.as_dict()` nên **mang cả field meta Frappe** (`parent`/`parenttype`/`parentfield`/`doctype`/`owner`/`creation`/`modified`/`docstatus`); đồng thời `_standard_repair_checklist_rows()` (@`services/imm09.py:80-94`) **cố ý** seed `result=""` cho cả 6 dòng để chặn Frappe `_set_defaults()` tự điền option đầu `'Pass'` (false-green BR-09-04 → thiết bị trả lâm sàng không kiểm tra, vi phạm NĐ98); và BR-09-16 giới hạn **1 ảnh/mục** (`MAX_REPAIR_CHECKLIST_PHOTOS = 1`, SoT liệt-kê `_repair_checklist_item_photos` @`services/imm09.py:1369`).
- **Decision**: (1) `RepairChecklistItem.additionalProperties: true` — mirror precedent `PmChecklistResultItem`; (2) `result`/`test_category` khai `type: string` **không** `enum`; (3) `photo` khai `type: string, nullable: true` (Attach đơn), **không** array; (4) `idx` là `integer` non-null làm khoá join.
- **Alternatives (loại)**: *Closed schema 7-key* → validator/codegen reject payload THẬT (meta Frappe) ⇒ loại. *`result.enum = [Pass, Fail, N/A]`* → **reject 100% phiếu CM mới tạo** (6 dòng seed `result=""`) ⇒ loại; nếu tương lai cần enum thì **bắt buộc** chứa `""`. *`photo: array`* → mobile giả định nhiều ảnh, đính ảnh thứ 2 bị server chặn 422 ⇒ UX sai lệch ⇒ loại.
- **Consequences**: hợp đồng wire nới lỏng (nhiều field nullable) nhưng **contract-truthful**; ràng buộc nghiệp vụ nằm ở service (BR-09-04/16), guard test khoá lại quyết định (7 TC `cr65_a..g`, `test_mobile_oas.py`). 0 file `.py` production, 0 migrate, 0 reload gunicorn.

> 📱 **Cross-ref Mobile-BE contract (CR-65 — nối chuỗi typed đọc→đính-ảnh, 2026-07-25):** `RepairWorkOrderDetail.repair_checklist` = `array` items `$ref '#/components/schemas/RepairChecklistItem'` trong OpenAPI mobile [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml). Zero-footprint: payload GIỮ `additionalProperties: true` + `required: [name]`; `RepairWorkOrderDetailEnvelope` GIỮ CLOSED `{success,data}` + 0 discriminator (route-by-VALUE `body.success`). Đầu kia của chuỗi = §3.10 `attach_repair_checklist_photo` (`AttachRepairChecklistPhotoRequest.checklist_item_idx: integer`, [ADR-MOBILE-030](../mobile/ADR-MOBILE-030.md)). Guard: `assetcore/tests/guards/test_mobile_oas.py::TestMobileRepairChecklistItemTyped` (7 TC).

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
3. **Seed `repair_checklist` 6 dòng danh mục chuẩn (CR-50, ADR-IMM09-SEED-CHECKLIST):** SAU `get_doc({...})` TRƯỚC `insert` → append 6 dòng `{test_description, test_category}` điền sẵn, `result` TRỐNG (KTV nhập sau). Gỡ deadlock `confirm_inspection` 422 cho phiếu CM mobile (checklist không còn rỗng). Xem `04_Backend_Design.md §3.7`.
4. Insert Asset Repair với `status = "Open"`, `open_datetime = now()`.
5. `frappe.db.set_value("Asset", asset_ref, "status", "Under Repair")`.
6. Tạo Asset Lifecycle Event `event_type = "repair_opened"`.
7. `frappe.db.commit()`.

> Response GIỮ shape `{name, status, sla_target_hours}` — seed checklist KHÔNG thêm key vào response (đọc 6 dòng qua `get_repair_work_order`).

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
- Chỉ thực hiện khi `status IN ("Assigned", "Diagnosing")` — sai trạng thái → `IMM09_BAD_STATE` (`http_status 409`/`code CONFLICT`, `services/imm09.py:1110`); WO không tồn tại → `IMM09_NOT_FOUND` (`http_status 404`/`code NOT_FOUND`). Cả 2 là **lỗi-nghiệp-vụ trên HTTP-200 + Error envelope** (route theo `body.http_status`).
- Set `diagnosis_notes` (`services/imm09.py:1112` — chỉ field này; **KHÔNG** set `root_cause_category` ở action này).
- Nếu `needs_parts = 1` → `status = "Pending Parts"` **+ `enter_parts_hold(doc)`: stamp `parts_hold_started = now()` (BR-09-10, INV-CM-HOLD-2) + ALE `parts_hold_started`** (SLA bắt đầu tạm dừng, `services/imm09.py:1116-1117`).
- Nếu `needs_parts = 0` → `status = "In Repair"` (`services/imm09.py:1113`).
- Sinh ALE `event_type = "diagnosis_submitted"` (`services/imm09.py:1120`).
- Service trả EXACT `{name, status}` (`services/imm09.py:1125`) — Mobile-BE contract REUSE `RepairActionEnvelope`/`RepairActionResponse` (mirror `startRepair`; xem [`docs/mobile/04-api-contract.md §8.11-bis`](../mobile/04-api-contract.md)).

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
- **Gate-2 IMM-09 → IMM-15 (cross-module, non-blocking):** tạo `IMM Spare Allocation` trạng thái `Requested` để spare-part truy về kho (`services/imm09.py:1166-1191`, lazy-import `imm15.create_allocation` — Pattern B). CHỈ tạo khi có item (`spare_part`/`item_code`) **và** tìm được `warehouse` từ `AC Spare Part Stock`. Bọc `try/except` → thất bại chỉ `frappe.log_error`, KHÔNG vỡ action. `allocation` = name allocation mới (hoặc `null`).

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

**Trường trả về (EXACT 4-key, grounded `services/imm09.py:1193-1194`):** `name` (string), `status` (RepairStatus 9-state — `In Repair` nếu rời `Pending Parts`, ngược lại giữ nguyên), `updated` (integer — số row gắn được `stock_entry_ref`), `allocation` (string|null — name `IMM Spare Allocation` Gate-2, `null` nếu không tạo).

**Lỗi:** WO không tồn tại ⇒ `IMM09_NOT_FOUND` (`code=NOT_FOUND`, `http_status=404`, `services/imm09.py:1151`) — lỗi-nghiệp-vụ = **in-handler HTTP-200 + Error envelope** (KHÔNG raise→HTTP-4xx).

##### 3.6-bis Gate-2 → IMM-15: điều kiện tạo allocation + 3 nguyên nhân "allocation câm" (chốt 2026-07-25)

`allocation` = `null` **KHÔNG** có nghĩa "không cần cấp phát". Đến 2026-07-25 có **3 nguyên nhân** làm nó luôn `null` trong thực tế:

| ID | Nguyên nhân | `@source` | Trạng thái |
|---|---|---|---|
| **E2** | `spare_part` do FE/gợi ý gửi lên là **mã NSX**, không phải `name` của `AC Spare Part` ⇒ `frappe.db.get_value("AC Spare Part Stock", {"spare_part": …}, "warehouse")` rỗng ⇒ `warehouse=""` ⇒ bỏ qua `create_allocation` | `services/imm09.py:1833-1844` | **SỬA trong CR-73a** (nguồn: `search_spare_parts` phát `spare_part` thật — §3.13-bis) |
| **K4** | Persona KTV **không có** `inventory.write` ⇒ `create_allocation` raise FORBIDDEN, bị `except Exception: log_error` nuốt ⇒ `success:true` + `allocation:null` | `services/imm09.py:1851-1853` · `services/imm15.py:254,1528-1535` | **ADR-IMM09-SPARE-03** — Accepted (thiết kế), thực thi OPTIONAL-IN-ROUND / P1 |
| **K5** | `warehouse` chỉ tra theo **`items[0]`**: nếu phụ tùng đầu tiên chưa có `AC Spare Part Stock` mà phụ tùng thứ hai có ⇒ **cả phiếu** không được cấp phát | `services/imm09.py:1839-1843` | **P1 backlog** — hướng ratify: duyệt `items` theo thứ tự, lấy `warehouse` của **phụ tùng đầu tiên tra được**; vẫn 0 nếu không có phụ tùng nào ⇒ `allocation=null` |

**K6 — liên kết SAI DocType (P1 backlog, ratify hướng sửa):** `create_allocation` ghi cứng `work_order_doctype = "IMM PM Work Order" if work_order_ref else None` (`services/imm15.py:270`), trong khi phiếu gọi từ IMM-09 là **`Asset Repair`**. `IMM Spare Allocation.work_order_doctype` là `Select` có sẵn option `Asset Repair` (`imm_spare_allocation.json`) và `work_order_ref` là `Dynamic Link` trỏ theo trường đó ⇒ mọi allocation sinh từ CM đang **trỏ sai doctype** (sai lệch bị `doc.flags.ignore_links = True` che). Hướng ratify: `create_allocation(..., work_order_doctype: str = "")` — rỗng ⇒ giữ heuristic cũ (0 regression cho IMM-08); IMM-09 truyền `"Asset Repair"`. **Additive, 0 field mới, 0 `bench migrate`.**

> **Quy tắc chấm (Boundaries):** `allocation: null` là **hợp lệ** khi thật sự không có `AC Spare Part Stock` nào cho phụ tùng được yêu cầu. Nhưng **KHÔNG** được dùng `null` để che lỗi quyền (K4). Muốn phơi lý do cho client ⇒ **CR riêng** (shape `RequestSparePartsData` đang là closed 4-key trong OAS mobile — thêm khoá thứ 5 = breaking cho codegen strict). Trong lúc chờ: `frappe.log_error` **PHẢI** giữ nguyên và ghi rõ nguyên nhân (đừng đổi thành `except: pass`).

> 📱 **Cross-ref Mobile-BE contract (repair spare-parts sub-flow):** endpoint này được surface trong OpenAPI mobile [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) tại path `/api/method/assetcore.api.imm09.request_spare_parts` (opId **`requestSpareParts`**, **POST-only `@frappe.whitelist(methods=["POST"])` `api/imm09.py:77` SẴN @source — CLEAN POST, KHÔNG verb-divergence/backlog**). 200 = `oneOf [RequestSparePartsEnvelope, Error]` (route-by-VALUE `body.success`, 0 discriminator); `data` = **`RequestSparePartsResponse`** closed 4-key `{name, status, updated, allocation}` (`required[name,status]`; `updated` integer; `allocation` string|null nullable). **⚠️ Schema RIÊNG — KHÔNG reuse `RepairActionResponse` 2-key `{name,status}`** dù cùng domain repair: service trả thêm `updated` + `allocation` (4-key) ⇒ C3-split field-disjoint (Self-Correction: forward-reservation §8.11 contract-doc ghi reuse cho `request_spare_parts` SAI — service THẬT 4-key). **Dual-rbac**: cap-gate `repair.write` (`api/imm09.py:79`) + service `repair.create` (`services/imm09.py:1148`) — đều in-handler cap-403 (phủ bởi nhánh Error 200-oneOf). Slot `{200,401,403}`; 403 SINGLE-SHAPE dispatcher-403. `IMM09_NOT_FOUND` (404) arrive HTTP-200 + Error. Chi tiết hợp đồng + ADR: [`docs/mobile/04-api-contract.md §8.23`](../mobile/04-api-contract.md) + [`ADR-MOBILE-010.md`](../mobile/ADR-MOBILE-010.md) + `04_Backend_Design.md §3.5`.

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
| `checklist_results` | JSON string | Có* | List `[{idx, result, measured_value?, notes?}]` — **key theo `idx` 1-based** (CR-50, AC4): cập nhật dòng seed sẵn (KHÔNG append trùng), bảo toàn `test_description`/`test_category` dòng seed. Client gửi `result` (Pass/Fail/N/A) cho ĐỦ 6 dòng seed. |
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
1. Set các trường từ body (`repair_summary`, `root_cause_category`, `dept_head_name`, `checklist_results`, `spare_parts`, `firmware_*`). `_apply_checklist` cập nhật dòng seed **theo `idx`** (phiếu seeded luôn non-empty ⇒ idx-update, KHÔNG append; giữ `len==6` + bảo toàn `test_category`/`test_description` — CR-50 AC4).
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

**Nguồn `asset_status` = SSoT LIVE (KHÔNG hardcode):** đọc trực tiếp trạng thái asset qua `frappe.db.get_value("AC Asset", doc.asset_ref, "lifecycle_status")` (hoặc `AssetRepo.get_value(doc.asset_ref, "lifecycle_status")` — cùng SSoT như `complete_repair` `services/imm09.py:907`). Lý do KHÔNG hardcode: `lifecycle_status` của AC Asset do **nhiều process** quản (calib-fail → OoS+CAPA, decommission…) — xem BR-09-09 (root-cause `04 §restore có điều kiện`). Nhánh happy asset vẫn `Under Repair` (WO → Pending Inspection, chưa restore); nhánh cannot_repair vừa transition sang `Out of Service` nên LIVE-read == `"Out of Service"`. Khuyến nghị BE: một tail dùng chung dựng đủ 5 khoá, chỉ `status` khác giữa 2 nhánh (chống drift key-set).

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

**Tiền điều kiện (BR-09-04 — checklist nghiệm thu):** submit CHỈ thành công khi `repair_checklist` **KHÔNG rỗng** và **MỌI dòng `result == "Pass"`** (`validate_repair_checklist_complete` chạy trong `before_submit`). Phiếu CM mới đã được seed 6 dòng chuẩn tại `create_work_order` (CR-50) ⇒ chỉ cần KTV điền hết Pass qua `close_work_order` là submit được (hết deadlock 422 `IMM09_CHECKLIST_INCOMPLETE`). Dòng `result` để trống → `IMM09_CHECKLIST_INCOMPLETE` (422); dòng `result == "Fail"` → `IMM09_CHECKLIST_FAILED` (422). Xem `04_Backend_Design.md §3.7` + AC2/AC3.

**Side-effects:**
1. Kiểm tra status = "Pending Inspection", role `CAN_APPROVE_DEP`.
1-bis. **Segregation-of-duties (BR-09-SOD, CR-41):** đọc "người đóng phiếu" = `actor` của Asset Lifecycle Event mới nhất (`event_type='repair_pending_inspection'`, `root_doctype='Asset Repair'`, `root_record=name`, ORDER BY creation DESC LIMIT 1). Nếu `session.user == closer` (và caller KHÔNG bypass `AssetCore Super Admin`) → **STOP, trả Error `FORBIDDEN` 403** (WO GIỮ Pending Inspection, KHÔNG submit). Check nằm SAU status-gate (BAD_STATE), TRƯỚC `doc.submit()` (INV-CM-SOD-1). `closer` không đọc được (legacy) → fail-open, tiếp tục (INV-CM-SOD-2). Migrate-free — 0 field DocType mới. Xem `04 §5 ADR-IMM09-SOD-INSPECT`.
2. Set `dept_head_confirmation_datetime = now()`.
3. `doc.submit()` → `before_submit` (validate BR-09-02/03/04 — **BR-09-04: checklist non-empty + 100% Pass**) → `on_submit` → `complete_repair()`.
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
| `NOT_FOUND` | 404 | WO không tồn tại (`IMM09_NOT_FOUND` `services/imm09.py:1276`; `messages.py:639`) |
| `BAD_STATE` | 409 | WO không ở trạng thái "Pending Inspection" (`IMM09_BAD_STATE` `services/imm09.py:1277`; `messages.py:646` — xung-đột TRẠNG THÁI, KHÔNG 422) |
| `CHECKLIST_INCOMPLETE` | 422 | BR-09-04 — `repair_checklist` rỗng HOẶC có dòng `result` chưa điền (`IMM09_CHECKLIST_INCOMPLETE`, raise trong `before_submit` qua `validate_repair_checklist_complete`). Sau CR-50 seed, "rỗng" chỉ còn ở phiếu legacy chưa backfill. |
| `CHECKLIST_FAILED` | 422 | BR-09-04 — có dòng `result == "Fail"` (`IMM09_CHECKLIST_FAILED`). |
| `FORBIDDEN` | 403 | **(cap-gate)** Không có quyền `repair.submit` (`rbac.require` `api/imm09.py`) — thiếu năng lực phê duyệt. |
| `FORBIDDEN` | 403 | **(business-rule, BR-09-SOD)** Tự-nghiệm-thu: `session.user` == người đã `close_work_order` (`MSG.IMM09_SELF_INSPECTION`, message VN "Người nghiệm thu phải khác người đóng phiếu."). In-handler HTTP-200 + Error envelope; WO GIỮ Pending Inspection/docstatus=0. |

> **Hai flavor `FORBIDDEN`/403 tại endpoint này** — cùng `code`/`http_status`, KHÁC `message_code`: (1) cap-gate `repair.submit` (thiếu quyền); (2) business-rule SoD (đủ quyền nhưng là chính người đóng phiếu). FE phân nhánh UX qua `message_code`/`message`, KHÔNG chỉ `code`. Cả hai đều là **in-handler HTTP-200 Error** (`nthrow`/`rbac.require` → `handle`), KHÁC dispatcher-403 (guest/no-token, POST @whitelist KHÔNG `allow_guest`).

> 🔗 **Cross-ref IMM-00 Approval Inbox (CR-42) — phiếu 'Pending Inspection' surface trong "Phiếu chờ tôi duyệt".** WO CM ở `Pending Inspection` (docstatus 0) là **nguồn thứ 4 (`imm09`)** của endpoint gộp `get_pending_approvals_inbox` ([`docs/imm-00/05 §III.22`](../imm-00/05_API_Specification.md) + [`ADR-IMM00-APPROVAL-INBOX §D`](../imm-00/ADR-IMM00-APPROVAL-INBOX.md)). Inbox áp **SoD đối xứng ở tầng list** (BR-00-INBOX-03): ẩn WO mà chính `session.user` tự đóng — **tái dùng SSoT `_resolve_wo_closer`** (`services/imm09.py:1956`, CÙNG hàm CR-41 dùng ở đây); closer None → fail-open (vẫn hiện). Gate cap = `repair.submit` (đối xứng cap `confirm_inspection` enforce @`services/imm09.py:1993`). **§BE task (Bước-4, application code):** tạo hằng SSoT `_CAP_SUBMIT = "repair.submit"` @`services/imm09.py` (hiện hardcode 2 chỗ: `services/imm09.py:1993` + `api/imm09.py:182`) + helper batch `_resolve_wo_closers(names)` (1 `get_all` `root_record IN [...]`, no N+1) để imm00 lazy-import. `confirm_inspection` guard (self-inspect) **GIỮ NGUYÊN** — inbox chỉ ẩn dòng, không thay chốt chặn handler (2 tầng độc lập).

> **OAS bất biến (AC6):** `code='FORBIDDEN'` ∈ `Error.code` enum + `403` ∈ `Error.http_status` enum sẵn có trong [`assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (verified) ⇒ nhánh Error mới đã phủ bởi `200 = oneOf [ConfirmInspectionEnvelope, Error]` — **KHÔNG schema/path/tag mới**, `test_mobile_oas` + `oas_baseline` count KHÔNG đổi. (KHÔNG chạm IMM-10 baseline đỏ pre-existing.)

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
| **Ảnh hỏng / đứt-truyền** (`UnidentifiedImageError\|OSError` khi Frappe `File.before_insert`→`strip_exif`→`PIL.Image.open` — bytes rác/cắt-cụt dù content-type hợp lệ; `services/imm09.py:1397-1408`) | `false` | `VALIDATION` | 422 | `{file: "Tệp ảnh bị lỗi hoặc không đọc được, vui lòng chụp/chọn lại."}` | ❌ (PIL fail TRONG `before_insert` TRƯỚC db_insert+write_file ⇒ KHÔNG orphan; `row.photo` chưa set) |

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

> ✍️ **Self-Correction (2026-07-11, verify-before-claim @source khi curate mobile OAS §8.36):** (1) allowlist content-type = **3 giá-trị** `_REPAIR_PHOTO_CONTENT_TYPES = ("image/jpeg","image/jpg","image/png")` `services/imm09.py:131` (doc cũ ghi 2 giá-trị `{image/jpeg, image/png}` @`:129` — sửa +`image/jpg` alias + line-ref 129→131); (2) **thêm nhánh lỗi #8 corrupt-guard** `UnidentifiedImageError|OSError` @`services/imm09.py:1397-1408` vào bảng lỗi (đối xứng imm08/imm12 — trước bị sót); (3) header status 🟡 SPEC → 🟢 LIVE (handler @`api/imm09.py:58` + service @`services/imm09.py:1337` ĐÃ trên đĩa). KHÔNG đụng `.py` — chỉ đồng-bộ doc với source.

### ADR-IMM09-PHOTO-01: Lưu ảnh bằng chứng sửa chữa = Frappe `File` private attach vào Asset Repair; discriminator per-mục = **Frappe child `idx`**; SoT = `row.photo` (Attach đơn trị, max 1/mục)
- **Status**: Accepted · **Date**: 2026-07-09
- **Context**: NĐ98 (thiết bị Class C/D) đòi ảnh bằng chứng **theo từng mục** checklist sửa chữa; `repair_checklist.photo` là field `Attach` **đơn trị** đã tồn tại (KHÔNG schema-change). **KHÁC imm08**: `Repair Checklist` (child của Asset Repair) **KHÔNG có** field STT domain `checklist_item_idx` (chỉ có `test_description/test_category/expected_value/measured_value/result/notes/photo`) — trong khi PM Checklist Result CÓ. `get_repair_work_order` đã trả `repair_checklist[].photo` (qua `doc.as_dict()`). `_apply_checklist` (`services/imm09.py:1422`) đã dùng Frappe child `idx` làm khóa cập-nhật hàng (`row.idx == r.get("idx")`).
- **Decision**: (1) store = Frappe `File` private, attach vào **parent WO** (`attached_to_doctype='Asset Repair'`, `attached_to_name=WO`, KHÔNG attach vào child-row). (2) discriminator per-mục = **Frappe child `idx`** (1-based) — `_find_repair_checklist_row(wo, idx)` duyệt `wo.repair_checklist` khớp `int(r.idx)==idx` (KHÔNG N+1: list con đã load). (3) SoT ảnh/mục = `row.photo` (đơn trị, `db.set_value(update_modified=False)`) — `_repair_checklist_item_photos(row)` trả `[{file_url}]`/`[]` = **1 SoT** cho max-count(=1) + read-side hiển thị ⇒ count==rows. `MAX_REPAIR_CHECKLIST_PHOTOS=1` (mirror imm08 CODE, KHÔNG mirror bản mô tả cũ imm08 doc multi-photo-discriminator).
- **Alternatives**: (A) thêm field STT domain `checklist_item_idx` vào Repair Checklist để mirror imm08 1:1 → schema-change + migration + backfill hàng cũ, trong khi Frappe child `idx` đã đủ ổn định cho checklist append-only (không reorder/xóa hàng giữa flow) → loại (over-engineering). (B) attach File vào child-row (`attached_to_doctype='Repair Checklist'`, `attached_to_name=row.name`) → child-row name là hash + resolve permission trên child doctype phức tạp + trái parity imm08 → loại. (C) multi-photo/mục qua File-query discriminator → phức tạp hơn, task chỉ cần `populate repair_checklist.photo` (đơn trị) → loại.
- **Consequences**: 0 field mới / 0 child table / 0 migration schema; `MAX_REPAIR_CHECKLIST_PHOTOS=1` (đính ảnh thứ 2 vào mục đã có ảnh → VALIDATION); `row.photo` hiển thị làm thumbnail. **Đánh đổi (ghi rõ):** discriminator = Frappe child `idx` chỉ ổn định khi hàng checklist KHÔNG bị reorder/xóa sau khi tạo (đúng với luồng CM: checklist clone từ template/append lúc close, không xóa hàng giữa chừng). Nếu tương lai cho phép xóa hàng checklist giữa flow → phải chuyển discriminator sang `row.name` (child docname) — ghi backlog, ngoài scope vòng này.

### ADR-IMM09-PHOTO-02: Audit đính ảnh sửa chữa = canonical `Asset Lifecycle Event` `repair_checklist_photo_attached` (thêm option Select) — hard-requirement, KHÔNG dùng wrapper swallow
- **Status**: Accepted · **Date**: 2026-07-09
- **Context**: NĐ98 đòi evidence trail cho mọi thao tác trên hồ sơ sửa chữa; `Asset Lifecycle Event.event_type` là Select enum cố định (`asset_lifecycle_event.json`); `repair_checklist_photo_attached` CHƯA có trong options (hiện có `repair_opened`, `repair_completed`, `incident_photo_attached` Vòng 1, `pm_checklist_photo_attached` Vòng 2…). **Bẫy nội bộ IMM-09:** wrapper `_log_lifecycle_event` (`services/imm09.py:718`) **try/except-swallow** exception (audit best-effort cho các transition thường) — nếu tái dùng cho event evidence sẽ **mất bằng chứng im lặng**.
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

**Response 200 (hợp đồng CR-73a — 13 khoá):**

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
      "idx": 0,
      "device_model": "IMM-MDL-2026-0007",
      "device_model_name": "Savina 300",
      "spare_part": "AC-SP-2026-0042"
    }
  ]
}
```

> **Ghi chú:** Source là `tabIMM Device Spare Part` (child table của `IMM Device Model.spare_parts_list` — DocType này KHÔNG có parent nào khác, verify `grep -rn "IMM Device Spare Part" assetcore/assetcore/doctype/*/*.json`), tìm theo `part_name` LIKE hoặc `manufacturer_part_no` LIKE. FE `CMPartsView.vue` + `CMCreateView.vue` gọi qua `searchSpareParts()` từ `@/api/imm09`. Query `< 2` ký tự → trả `[]` rỗng. Số dòng cap bởi `limit` (SQL `LIMIT`, KHÔNG pagination).

---

#### 3.13-bis CR-73(a) — KHÓA NHẬN DẠNG cho gợi ý phụ tùng CM 🔴 SPEC CHỐT 2026-07-25 (BA) · BE/FE **Bước-4**

##### (1) Ba lỗi thiết kế gốc (Self-Correction — [BA] chịu trách nhiệm sửa doc TRƯỚC khi code)

| # | Lỗi | Bằng chứng `@source` (verify 2026-07-25) | Hậu quả nghiệp vụ |
|---|---|---|---|
| **E1** | Row-dict **KHÔNG có khoá nhận dạng model**; SQL `SELECT DISTINCT part_name, manufacturer_part_no, estimated_cost` gộp phụ tùng **trùng tên của 2 model KHÁC NHAU** thành 1 dòng | `services/imm09.py:2283-2293` | KTV chọn "Van PEEP" của máy thở A trong khi phiếu đang sửa máy thở B ⇒ **cấp sai phụ tùng cho thiết bị y tế** (rủi ro an toàn NĐ98, không truy vết được) |
| **E2** | Row-dict **KHÔNG có khoá `AC Spare Part`**; `item_code` = `manufacturer_part_no` (mã NSX), **KHÔNG phải** `name` của `AC Spare Part` | `services/imm09.py:2296` | Gate-2 IMM-09→IMM-15 tra `frappe.db.get_value("AC Spare Part Stock", {"spare_part": <mã NSX>}, "warehouse")` ⇒ **luôn rỗng** ⇒ `warehouse=""` ⇒ **KHÔNG tạo allocation**, mà API **vẫn trả `success:true`** (`services/imm09.py:1839-1853`) = **"allocation câm"** |
| **E3** | Consumer web ép kiểu **bịa** khoá `{name, part_name}` KHÔNG tồn tại trong response | `frontend/src/views/cm/CMCreateView.vue:206-210` (`as unknown as`), dùng ở `:214-218` (`p.name`) | `preRequestParts` được đẩy `{spare_part: undefined}` ⇒ dòng bị `request_spare_parts` bỏ qua (filter `if (p.get("spare_part") or p.get("item_code"))`) ⇒ **yêu cầu phụ tùng biến mất im lặng** |

> ✅ **Cite-drift — ĐÃ XỬ LÝ (BE Bước-4, 2026-07-25):** cite cũ `services/imm09.py:1398-1423` / `:1237-1246` (doc + OAS mobile) đã rot; nay refresh về số dòng đọc-tại-chỗ **sau khi sửa**: hàm `search_spare_parts` @`services/imm09.py:2360-2431`, row literal 13 khoá @`:2224-2237`, 2 helper batch @`:2103-2116` / `:2118-2166`. **Guard chống tái rot đã có**: `test_mobile_oas.py::TestMobileSearchSparePartItemIdentity::test_mob_oas_cr73a_e_source_cites_point_inside_search_spare_parts` parse mọi cite `services/imm09.py:<dòng>` trong schema và assert dòng đó vẫn nằm trong vùng AST của hàm/helper được nêu tên (đây là hiện thực hoá backlog MED 'cite-drift guard' cho ĐÚNG schema này).

##### (2) Row-dict hợp đồng — EXACT 13 khoá (A1: thuần ADDITIVE)

| # | Khoá | Kiểu | Nguồn giá trị | Trạng thái CR-73a |
|---|---|---|---|---|
| 1 | `item_code` | string | `manufacturer_part_no or part_name or ""` | GIỮ NGUYÊN |
| 2 | `item_name` | string | `part_name or ""` | GIỮ NGUYÊN |
| 3 | `manufacturer_part_no` | string | `manufacturer_part_no or ""` | GIỮ NGUYÊN |
| 4 | `qty` | integer | hằng `1` | GIỮ NGUYÊN |
| 5 | `uom` | string | hằng `"Cái"` *(xem Known-defect K1)* | GIỮ NGUYÊN |
| 6 | `unit_cost` | number | `float(estimated_cost or 0)` | GIỮ NGUYÊN |
| 7 | `total_cost` | number | `float(estimated_cost or 0)` | GIỮ NGUYÊN |
| 8 | `stock_entry_ref` | string | hằng `""` | GIỮ NGUYÊN |
| 9 | `notes` | string | hằng `""` | GIỮ NGUYÊN |
| 10 | `idx` | integer | hằng `0` | GIỮ NGUYÊN |
| 11 | **`device_model`** | string | `tabIMM Device Spare Part.parent` (= `name` của `IMM Device Model`) | **MỚI** |
| 12 | **`device_model_name`** | string | `IMM Device Model.model_name` của `device_model`; `""` nếu không resolve | **MỚI** |
| 13 | **`spare_part`** | string | `name` của `AC Spare Part` theo quy tắc §(4); `""` nếu 0 khớp | **MỚI** |

**Invariant khoá (A1):** cả 13 khoá **LUÔN CÓ MẶT** trong mọi row (dict literal vô-điều-kiện). 3 khoá mới kiểu **`str` thuần** — giá trị vắng = `""`, **TUYỆT ĐỐI KHÔNG `None`**, **KHÔNG bỏ khoá** (OAS `additionalProperties:false` + `required` 13 ⇒ `null`/thiếu khoá làm client codegen rớt field hoặc parse-fail).

##### (3) Truy vấn chính — bỏ `DISTINCT`, thêm khoá model, sắp xếp DETERMINISTIC

```sql
SELECT sp.parent AS device_model,
       sp.part_name, sp.manufacturer_part_no, sp.estimated_cost
FROM `tabIMM Device Spare Part` sp
WHERE sp.parenttype = 'IMM Device Model'
  AND (sp.part_name LIKE %(q)s OR sp.manufacturer_part_no LIKE %(q)s)
ORDER BY sp.part_name ASC, sp.parent ASC
LIMIT %(lim)s
```

- **Bỏ `DISTINCT`** (nguyên nhân E1). `parent` vào `SELECT` ⇒ phụ tùng trùng tên ở 2 model ra **2 dòng** (A2).
- **`ORDER BY part_name ASC, sp.parent ASC`** — tie-break bằng `parent` để thứ tự **ổn định** giữa 2 lần gọi (nếu không, `LIMIT` cắt ngẫu nhiên ⇒ test flaky + UX nhảy dòng).
- **`parenttype = 'IMM Device Model'`** — ratify (ADR-IMM09-SPARE-01): `device_model`/`device_model_name` chỉ có nghĩa với parent này; row parenttype khác = dữ liệu mồ côi, không được phát ra với khoá model rỗng.
- **Ngữ nghĩa `limit` ĐỔI** (hệ quả có chủ đích, phải ghi vào release note): trước = "≤N *tên* phụ tùng khác nhau", sau = "≤N *cặp (model, phụ tùng)*". Cùng `limit=10`, danh sách có thể hiển thị ít tên khác nhau hơn. **KHÔNG** bù bằng cách nâng `limit` ngầm — `limit` là tham số client.

##### (4) Quy tắc resolve `spare_part` — DETERMINISTIC, ratify [BA] (A4)

Cho mỗi row gợi ý, `spare_part` = `name` của `AC Spare Part` theo thuật toán **CỐ ĐỊNH** sau (KHÔNG được BE tự chế biến thể):

1. **Ưu tiên 1 — khớp `manufacturer_part_no`**: nếu `row.manufacturer_part_no` non-empty ⇒ tìm `AC Spare Part` có `manufacturer_part_no == row.manufacturer_part_no` **và** `is_active == 1`.
2. **Ưu tiên 2 — fallback `part_name`**: CHỈ khi bước 1 không cho kết quả (0 khớp **hoặc** `manufacturer_part_no` rỗng) ⇒ tìm `AC Spare Part` có `part_name == row.part_name` **và** `is_active == 1`.
3. **Nhiều khớp** ⇒ `order_by name asc`, lấy **phần tử đầu tiên** (name có naming series `AC-SP-.YYYY.-.####` ⇒ "đầu tiên" = bản ghi tạo sớm nhất trong năm sớm nhất — ổn định, không phụ thuộc thứ tự trả về của DB).
4. **0 khớp** ⇒ `spare_part = ""`.
5. So khớp là **EXACT equality**, KHÔNG `LIKE`, KHÔNG normalize hoa/thường ngoài collation mặc định của cột (giữ nguyên hành vi DB — không tự thêm `LOWER()` vì sẽ phá index).

> **Vì sao `is_active=1`**: `AC Spare Part.is_active` (default 1) là cờ ngừng sử dụng; gợi ý một phụ tùng đã ngừng ⇒ allocation tạo ra không bao giờ cấp được. Cite: `assetcore/assetcore/doctype/ac_spare_part/ac_spare_part.json` (field `is_active`, `Check`, default `1`).
>
> **Vì sao ưu tiên `manufacturer_part_no`**: mã NSX là định danh **toàn cầu, 1-1 với vật tư thật**; `part_name` là chuỗi mô tả tiếng Việt do người nhập gõ ⇒ trùng lặp cao (chính là nguyên nhân E1). Trùng tên ≠ cùng vật tư.

##### (5) Ngân sách truy vấn — KHÔNG N+1 (A5)

Ngoài **1 SQL chính** ở §(3), service được phép chạy **TỐI ĐA 3 truy vấn phụ**, **bất kể số dòng trả về**:

| # | Truy vấn phụ | Bắt buộc dạng | Ghi chú |
|---|---|---|---|
| P1 | Batch tên model | `filters={"name": ["in", sorted(set(parents))]}`, `fields=["name","model_name"]` | 1 lần cho TOÀN BỘ trang |
| P2 | Batch resolve theo `manufacturer_part_no` | `filters={"manufacturer_part_no": ["in", [...]], "is_active": 1}`, `fields=["name","manufacturer_part_no"]`, `order_by="name asc"` | 1 lần |
| P3 | Batch resolve fallback theo `part_name` | `filters={"part_name": ["in", [...]], "is_active": 1}`, `fields=["name","part_name"]`, `order_by="name asc"` | 1 lần — **BỎ QUA nếu tập fallback rỗng** (⇒ trường hợp tốt = 2 phụ) |

**Cấm (Never):** gọi `frappe.db.get_value` / `frappe.get_doc` / bất kỳ truy vấn nào **bên trong vòng lặp row**. Guard = test đếm số lần gọi bằng monkeypatch counter (A5) — assert `≤ 3` với fixture ≥ 5 dòng ≥ 2 model.

##### (6) Gate quyền (A6) — role-gate CÓ, row-scope KHÔNG

| Trục | Quyết định | Lý do |
|---|---|---|
| **ROLE-scope** `IMM Device Model` | **BẮT BUỘC** `assert_doctype_read_permission("IMM Device Model")` + decorator `@rowscoped` | `IMM Device Spare Part` là child table ⇒ **không có DocPerm riêng**; quyền đọc thừa kế từ parent DocType. Không gate ⇒ mọi user (kể cả `Vendor Engineer`) đọc được toàn bộ danh mục phụ tùng + giá ước tính của mọi model. |
| **ROW-scope** | **KHÔNG** (master data, không có `permission_query_conditions`) | `IMM Device Model` KHÔNG nằm trong `hooks.permission_query_conditions` (`assetcore/hooks.py:439-447`) ⇒ không có predicate row để áp. |
| **ROLE-scope** `AC Spare Part` / `AC Spare Part Stock` | **KHÔNG gate** — resolve chạy **system-scope** (`ignore_permissions`, chỉ đọc `name` + khoá khớp) | Xem **ADR-IMM09-SPARE-02** — gate ở đây sẽ **khoá đúng người dùng chính** (KTV không có DocPerm trên 2 DocType này). |

**Hình dạng lỗi (Decision-B, bắt buộc):** thiếu quyền ⇒ `@rowscoped` bắt `frappe.PermissionError` → `nthrow(MSG.AUTH_FORBIDDEN)` → **HTTP-200 + Error envelope** `code=FORBIDDEN`, `http_status=403` (`services/shared/permissions.py:87-137`). **KHÔNG** HTTP-500, **KHÔNG** dispatcher-403 (FE sẽ hiểu nhầm là hết phiên và **đăng xuất người dùng**). **TUYỆT ĐỐI KHÔNG** trả `[]` rỗng thay cho 403 (anti-pattern dead-gate: RBAC misconfig chết âm thầm).

**Test cặp bắt buộc (chống khoá nhầm chính người dùng):**

| Ca | User | Kỳ vọng |
|---|---|---|
| A6-neg | user **chỉ** role `Repair User` (**KHÔNG** `AssetCore System User`) ⇒ 0 DocPerm read trên `IMM Device Model` | `ServiceError` FORBIDDEN, **0 dòng rò** |
| A6-pos | persona KTV THẬT = `AssetCore System User` + `Repair User` (theo `setup/role_profile_catalog.py` profile **"Kỹ thuật viên"** = base + `PM User`/`Repair User`/`Calibration User`/`Corrective User`) | kết quả **non-empty**, `spare_part` **non-empty** trên seed có `AC Spare Part` |

> `IMM Device Model` DocPerm read: `AssetCore Super Admin`, `Data Manager`, `Data User`, `AssetCore Auditor`, **`AssetCore System User`** (base role) ⇒ mọi persona AssetCore hợp lệ đều đọc được. Gate này **không** làm hỏng persona nào đang dùng thật.

##### (7) Boundaries (Always / Ask first / Never)

**Always**
- Phát đủ **13 khoá** trong mọi row, 3 khoá mới kiểu `str` (`""` khi vắng).
- Batch hoá 100% truy vấn phụ (≤3), `sorted(set(...))` trước khi `in`.
- `@rowscoped` + `assert_doctype_read_permission("IMM Device Model")` ở đầu hàm.
- `ORDER BY part_name ASC, parent ASC` — thứ tự ổn định.
- Refresh **mọi** cite `@services/imm09.py:<dòng>` trong doc + OAS bằng số dòng **đọc tại chỗ sau khi sửa**.

**Ask first (quay lại [BA]/[PM], KHÔNG tự quyết)**
- Đổi **giá trị** của 10 khoá cũ (kể cả "sửa cho đúng" như `uom` — xem K1).
- Thêm khoá thứ 14, hoặc đổi `spare_part` thành object/nullable.
- Đổi `limit` default, hoặc bù `limit` để "giữ nguyên số tên hiển thị".
- Nới/siết gate quyền khác với §(6).

**Never**
- Truy vấn trong vòng lặp row (N+1).
- Trả `None` hoặc bỏ khoá cho 3 field mới.
- Trả `[]` thay cho lỗi 403.
- Đổi shape `request_spare_parts` (đang là closed 4-key `{name,status,updated,allocation}` trong OAS).
- `bench migrate` (0 DocType/field mới) · `git commit/push` (HARD-STOP user).

##### (8) Delta OAS canonical (A7) — thực thi ở Bước-4 cùng BE

File: `docs/mobile/openapi/assetcore-mobile.openapi.yaml`, schema **`SearchSparePartItem`** (hiện `:1920-1966`).

- `properties`: **10 → 13** — thêm `device_model` (string), `device_model_name` (string), `spare_part` (string). **Cả 3 `type: string`** (KHÔNG `nullable`) — hợp đồng "vắng = `""`".
- `required`: **10 → 13** — thêm đủ 3 khoá mới. *(Bắt buộc: schema `additionalProperties: false` + client codegen strict ⇒ property khai mà thiếu `required` vẫn sinh field optional, nhưng **thiếu khai** = client **rớt** field.)*
- `description` của schema + của từng property mới: cite `@services/imm09.py:<dòng THẬT sau khi sửa>` (KHÔNG chép lại `:1238-1245` đã rot).
- Cập nhật đoạn comment `# EXACT 10 prop …` → 13, và mô tả `SearchSparePartsEnvelope` nếu có nhắc "10 field".
- **KHÔNG** thêm path / operationId / parameter mới ⇒ `oas_baseline` **GIỮ 105**; `components.schemas` **+0 schema** (chỉ property-add).
- **Guard counters — ĐỌC TẠI CHỖ, cộng theo DELTA** (KHÔNG hardcode số của spec này): `_EXPECTED_TEST_COUNT` @`assetcore/tests/guards/test_mobile_oas.py`, `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` + `_GUARD_SUITE_SUM` + `_MOBILE_OAS_TOTAL` @`assetcore/tests/guards/test_mobile_docset.py`. Thêm **N** test-case mới (class `TestMobileSearchSparePartItemIdentity`) ⇒ **cả 4 counter cùng cộng đúng `+N`**. Giá trị đọc lúc chốt spec: `911` / `1054` / `1080` — **nếu file đã khác, tin file** (CR khác có thể landed xen giữa; chấm theo delta, không theo số tuyệt đối — bài học Blocker #2 STATE 2026-07-25).

##### (9) Known defects KHÔNG thuộc DoD vòng này (đã ratify hướng sửa — backlog)

| ID | Vấn đề | Hướng đã ratify | Ưu tiên |
|---|---|---|---|
| **K1** | `uom` hằng `"Cái"` trong khi row có field `uom` thật (`IMM Device Spare Part.uom`, Link `AC UOM`, default `Cái`) ⇒ **giá trị bịa** cho phụ tùng tính theo `Bộ`/`Chiếc`/`Lít` | Lấy `sp.uom or "Cái"`. **KHÔNG làm trong vòng này** vì đổi giá trị khoá cũ ⇒ vi phạm A1 "thuần additive". Cần 1 CR riêng + kiểm tra consumer (`CMPartsView` hiển thị `uom`). | P2 |
| **K2** | LIKE term **không escape** — user gõ `%` hoặc `_` ⇒ wildcard injection (trả toàn bộ bảng, bỏ qua ý định tìm) | Dùng SSoT `assetcore.services.imm00.escape_like_term` (đã có, ADR-IMM09-SEARCH-01 dùng cho `list_repair_work_orders`) | P2 — **OPTIONAL-IN-ROUND** (1 dòng, rủi ro thấp) |
| **K3** | `search_spare_parts` **vô hình** với guard tĩnh G3/G4 vì `_ENTRYPOINT_PREFIXES = ("list_", "get_")` (`tests/test_rowscope_scope_guard.py:57`) — endpoint `search_*` không bị soi gate | Bổ sung `"search_"` vào `_ENTRYPOINT_PREFIXES` **sau khi** §(6) đã land (nếu thêm trước, guard đỏ ngay). Rà `services/inventory.py::search_parts` + `services/imm04.py::search_link` cùng lượt. | P1 — **OPTIONAL-IN-ROUND** |

---

#### ADR-IMM09-SPARE-01: Khoá nhận dạng gợi ý phụ tùng = cặp `(device_model, part)` — bỏ `DISTINCT`

- **Status**: Accepted
- **Date**: 2026-07-25
- **Context**: `search_spare_parts` gợi ý phụ tùng từ child table `IMM Device Spare Part` (danh mục phụ tùng **theo từng model thiết bị**). Truy vấn dùng `SELECT DISTINCT part_name, manufacturer_part_no, estimated_cost` ⇒ hai model khác nhau cùng khai một phụ tùng cùng tên/cùng mã NSX/cùng giá bị **gộp thành 1 dòng**. Danh mục phụ tùng thiết bị y tế trùng tên là chuyện thường (“Van PEEP”, “Cảm biến SpO2”, “Bộ dây thở”), nhưng **linh kiện của model A KHÔNG lắp được cho model B**. Người dùng nhìn 1 dòng thì không có cách nào biết mình đang chọn phụ tùng của model nào.
- **Decision**: Khoá nhận dạng của một gợi ý là **cặp `(device_model, phụ tùng)`**, không phải `part_name`. Bỏ `DISTINCT`; đưa `parent` (= `IMM Device Model.name`) vào `SELECT` và phát ra 2 khoá `device_model` (PK, dành cho máy) + `device_model_name` (nhãn, dành cho người). Lọc `parenttype = 'IMM Device Model'`. Sắp xếp `part_name ASC, parent ASC` để `LIMIT` cắt **ổn định**.
- **Alternatives**:
  - *Giữ `DISTINCT`, thêm cột `device_models` dạng chuỗi nối “A, B”*: loại — không chọn được, không truy vết được, không dùng làm khoá.
  - *Lọc gợi ý theo model của `asset_ref` trên phiếu*: loại **cho vòng này** — `search_spare_parts(query, limit)` không nhận `asset`/`work_order`; thêm tham số = đổi chữ ký + đổi OAS path param + đổi 2 consumer FE. Ghi nhận là hướng đúng về lâu dài (**[ROADMAP] CR-73b**: `search_spare_parts(query, limit, asset_ref?)` lọc/ưu tiên phụ tùng đúng model của thiết bị đang sửa).
- **Consequences**:
  - (+) Khử nhập nhằng đo được: 2 model cùng phụ tùng ⇒ 2 dòng phân biệt (A2).
  - (+) Chuỗi truy vết `gợi ý → model → phiếu` khép kín cho audit NĐ98.
  - (−) **Ngữ nghĩa `limit` đổi**: cùng `limit=10` nay hiển thị ít *tên* khác nhau hơn (bị các cặp trùng tên chiếm chỗ) — phải nêu trong release note; giảm nhẹ bằng CR-73b khi có lọc theo model.
  - (−) Số dòng trả về có thể tăng ⇒ FE **phải** hiển thị `device_model_name` để dòng trùng tên phân biệt được (ràng buộc A8, xem `06_Frontend_Design.md`).

#### ADR-IMM09-SPARE-02: Resolve `spare_part` chạy **system-scope**, chỉ phát khoá chính (PK)

- **Status**: Accepted
- **Date**: 2026-07-25
- **Context**: Để Gate-2 IMM-09→IMM-15 tra được kho, row gợi ý phải mang `name` của `AC Spare Part` (E2). Nhưng DocPerm `AC Spare Part` / `AC Spare Part Stock` chỉ cấp cho `AssetCore Super Admin` / `Inventory Manager` / `Inventory User` / `AssetCore Auditor` (`ac_spare_part.json`, `ac_spare_part_stock.json`). Persona **“Kỹ thuật viên”** = `AssetCore System User` + `PM/Repair/Calibration/Corrective User` (`setup/role_profile_catalog.py:64-67`) — **KHÔNG có role kho nào**. Nếu resolve chạy permission-aware, KTV luôn nhận `spare_part = ""` ⇒ sửa xong mà bug **vẫn còn nguyên trong production**, còn test chạy bằng `Administrator` thì **xanh giả**.
- **Decision**: Resolve `spare_part` chạy **system-scope** (`ignore_permissions`, không role-gate), và **chỉ** phát ra `name` (khoá chính opaque). **KHÔNG** phát bất kỳ trường nghiệp vụ nào của `AC Spare Part` (`unit_cost` của kho, `preferred_supplier`, `min/max_stock_level`, tồn kho, `specifications`) qua endpoint này. Role-gate của endpoint vẫn là `IMM Device Model` (§3.13-bis(6)); mọi thao tác **ghi**/xem tồn vẫn giữ nguyên gate `inventory.*`.
- **Alternatives**:
  - *Gate `assert_doctype_read_permission("AC Spare Part")`*: loại — khoá đúng người dùng chính (KTV), tái lập lỗi “dead-gate” đã có tiền lệ trong dự án.
  - *Cấp DocPerm read `AC Spare Part` cho `AssetCore System User`*: loại **cho vòng này** — mở đọc **toàn bộ** master phụ tùng + giá cho mọi user; là quyết định RBAC cấp hệ thống, cần [PM]/[USER] duyệt riêng, và phải đổi fixture DocPerm (blast-radius lớn hơn hẳn phạm vi CR).
  - *FE tự resolve bằng một endpoint kho riêng*: loại — đẩy join sang client, N+1 qua mạng, và vẫn vướng đúng DocPerm đó.
- **Consequences**:
  - (+) Persona thật (KTV) nhận `spare_part` non-empty ⇒ Gate-2 có nguyên liệu thật, hết “allocation câm” do E2.
  - (+) Bề mặt lộ = **1 chuỗi PK** (`AC-SP-YYYY-####`) không mang thông tin thương mại/tồn kho.
  - (−) Người không có quyền kho vẫn **suy ra được sự tồn tại** của một `AC Spare Part` khớp mã NSX mình gõ. Chấp nhận: người dùng đã biết mã NSX (họ vừa gõ), và đây là danh mục nội bộ bệnh viện, không phải dữ liệu bệnh nhân.
  - (−) Tạo tiền lệ “system-scope lookup phát PK”. Ràng buộc kèm theo: **chỉ** PK, **chỉ** cho join cross-module, và phải ghi ADR như mục này.

#### ADR-IMM09-SPARE-03: Gate-2 IMM-09→IMM-15 — ai được tạo `IMM Spare Allocation` trạng thái `Requested`

- **Status**: **Accepted (thiết kế)** · Thực thi = **OPTIONAL-IN-ROUND / P1 backlog** (nằm NGOÀI DoD A1–A10)
- **Date**: 2026-07-25
- **Context**: Ngay cả khi E2 được sửa, `request_spare_parts` gọi `imm15.create_allocation` → `_require_storekeeper_or_tech()` → `rbac.can("inventory.write")` → `frappe.has_permission("AC Stock Movement", "write")` (`services/imm15.py:1528-1535`, `services/shared/rbac.py:65-103,175-187`). `AC Stock Movement` chỉ cấp write cho `Inventory Manager`/`Inventory User`/`Super Admin` ⇒ **persona KTV luôn bị FORBIDDEN**. Exception bị `except Exception: frappe.log_error(...)` nuốt (`services/imm09.py:1851-1853`) ⇒ API trả `success:true`, `allocation:null`. **Đây là nguyên nhân thứ 3 của “allocation câm”, và là nguyên nhân duy nhất còn sống sót sau khi sửa E2 — trừ khi test chạy bằng `Administrator`.**
- **Decision**: “Tạo phiếu **yêu cầu** cấp phát (`Requested`)” và “**xuất kho**” là hai quyền khác nhau. Yêu cầu được phép bởi **capability phía lệnh công việc** (`repair.create` cho CM, `pm.write` cho PM) — người sửa máy phải tự yêu cầu được vật tư; mọi bước **làm dịch chuyển tồn thật** (`approve` / `issue` / `reject`) **giữ nguyên** gate `inventory.*`. Hiện thực bằng **seam nội bộ** trong `imm15`, KHÔNG nới gate của endpoint whitelisted `create_allocation`:
  - tách phần thân hiện tại thành `_insert_allocation(...)` (không gate);
  - `create_allocation(...)` (public/whitelisted) = `_require_storekeeper_or_tech()` + `_insert_allocation(...)` — **hành vi hiện tại không đổi**;
  - thêm `create_allocation_for_work_order(...)` (**không** whitelist, chỉ cho cross-module gọi) = gate `rbac.can("repair.create") or rbac.can("pm.write")` + ép `allocation_status = Requested` + `_insert_allocation(...)`.
- **Alternatives**:
  - *Cấp `Inventory User` cho Role Profile “Kỹ thuật viên”*: loại — kèm theo cả write `AC Stock Movement`/`AC Spare Part`/`AC Warehouse` (KTV sửa được master kho). Quá rộng.
  - *Giữ nguyên gate, chỉ báo lỗi to hơn*: loại — luồng vẫn chết (KTV phải gọi điện cho thủ kho), vi phạm nguyên tắc “không có hành động ngoài Work Order” + mất audit trail.
  - *Bỏ `try/except` để lỗi nổi lên*: loại **một mình nó** — sẽ biến lỗi cấp phát thành lỗi của cả `request_spare_parts` (mất cả `stock_entry_ref` + `exit_parts_hold`). Đúng hướng là sửa quyền, giữ Gate-2 non-blocking.
- **Consequences**:
  - (+) Luồng “KTV yêu cầu phụ tùng” chạy được **với persona thật** — điều kiện cần để A3 không phải xanh giả.
  - (−) `create_allocation` hiện gọi `_recompute_reserved_for_allocation(doc)` ⇒ phiếu `Requested` **giữ chỗ tồn** (soft-hold). KTV do đó tạo được soft-hold. Giảm thiểu: `work_order_ref` bắt buộc (VR-15-01), `requested_by` ghi trong audit, và thủ kho vẫn là người duyệt/xuất.
  - (−) Chạm `services/imm15.py` (module khác) ⇒ phải chạy thêm `test_imm15` trong DoD nếu thực thi.

#### 3.13-ter Ghi chú thực thi cho [BE]/[FE] — quan hệ giữa A3 và ADR-IMM09-SPARE-03

**A3-bis (BA bổ sung — BẮT BUỘC, chống xanh giả):** ca kiểm thử A3 (`spare_part` non-empty ⇒ `allocation` NON-NULL) phải chạy **theo cặp persona**:

| Ca | Chạy bằng | Kỳ vọng | Ý nghĩa |
|---|---|---|---|
| **A3-a** | `Administrator` | `allocation` NON-NULL | Chứng minh E2 (resolve `spare_part`) đã sửa. |
| **A3-b** | persona KTV thật (`AssetCore System User` + `Repair User`) | `allocation` NON-NULL | Chứng minh luồng **production** chạy. |

- Nếu **A3-b đỏ** vì `inventory.write` ⇒ thực thi ADR-IMM09-SPARE-03 trong vòng này (kèm `test_imm15` vào DoD), **HOẶC** báo ngược [PM] để tách CR. **KHÔNG** được đánh dấu A3 “xanh” khi chỉ có A3-a xanh, và **KHÔNG** được sửa test thành `Administrator` để né.
- **Không được** nới `try/except` thành `except: pass`, cũng **không được** đổi shape 4-key của `request_spare_parts` để nhét lý do lỗi (OAS `RequestSparePartsData` là closed-schema). Muốn phơi lý do ⇒ CR riêng (backlog K4 §3.6).



> 📱 **Cross-ref Mobile-BE contract (repair spare-parts sub-flow):** endpoint này được surface trong OpenAPI mobile [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) tại path `/api/method/assetcore.api.imm09.search_spare_parts` (opId **`searchSpareParts`**, **GET** — bare `@frappe.whitelist()` `api/imm09.py:123` nhận GET, read-only picker cho repair-detail). 200 = `oneOf [SearchSparePartsEnvelope, Error]` (route-by-VALUE `body.success`, 0 discriminator); `data` = **array `<SearchSparePartItem>` RAW** (KHÔNG pagination — `_ok(list)` wrap, cap bởi `limit`; mirror `getAssetIncidentHistory` no-pagination NHƯNG data là list trần, KHÁC `{asset,items}`). `[]` rỗng hợp lệ (query<2 hoặc không match — **KHÔNG 404**). `SearchSparePartItem` `additionalProperties:false` — **CR-73a: EXACT 13 prop** `{item_code, item_name, manufacturer_part_no, qty, uom, unit_cost, total_cost, stock_entry_ref, notes, idx, device_model, device_model_name, spare_part}`, `required` đủ 13 (trước CR-73a: 10 prop, cite `services/imm09.py:1412-1421` đã **rot** — dòng thật `:2089-2114`, xem §3.13-bis(1)) — **0 boolean/Check field** ⇒ 0 prop `integer enum[0,1]` (không int-vs-bool trap; `qty`/`idx` integer, `unit_cost`/`total_cost` number). **Slot `{200,401,403}`**: 403 = **dispatcher-403** cho Guest (bare `@whitelist`, `api/imm09.py:199-201` KHÔNG `rbac.require`). ⚠️ **CR-73a bổ sung một nhánh 403 KHÁC — KHÔNG đổi slot**: service nay gate ROLE-scope `assert_doctype_read_permission('IMM Device Model')` (`services/imm09.py:2387`) dưới `@rowscoped` (`:2169`) ⇒ user đã đăng nhập nhưng thiếu DocPerm nhận **Error envelope `FORBIDDEN`/`http_status:403` TRÊN HTTP-200** (nhánh `Error` của 200-`oneOf` đã có sẵn — client route-by-VALUE `body.success`, **KHÔNG** theo status-line). FE PHẢI hiển thị message, **KHÔNG** logout (phân biệt với dispatcher-403 hết phiên); và **KHÔNG BAO GIỜ** trả `data:[]` câm. Chi tiết hợp đồng + ADR: [`docs/mobile/04-api-contract.md §8.22`](../mobile/04-api-contract.md) + [`ADR-MOBILE-010.md`](../mobile/ADR-MOBILE-010.md) + `04_Backend_Design.md §3.5`.

---

### 3.14 `get_asset_repair_history`
> 🔌 **CONSUMER (từ 2026-07-30 — AC-CR-102):** caller THẬT ở web-FE = section «Lần sửa chữa đã **hoàn thành**» trong tab «Bản ghi liên quan» màn Chi tiết tài sản (IMM-00) — xem [`docs/imm-00/05 §III.26`](../imm-00/05_API_Specification.md) + [`ADR-IMM00-ASSET-OP-HISTORY`](../imm-00/ADR-IMM00-ASSET-OP-HISTORY.md). **Hai điểm ràng buộc**: (1) filter `docstatus=1` là **load-bearing** — tiêu đề section khai đúng «đã hoàn thành», nhờ đó `section.total` (≤) khác `count` ô connections mà **không** chỏi nhau (invariant `INV-OPH-17`); (2) `scope="system"` **giữ** DocPerm read ⇒ persona thiếu quyền nhận **403 envelope trên HTTP-200** và FE PHẢI hiện **trạng thái lỗi**, KHÔNG hiện «Chưa có …». Đổi filter/`fields` ⇒ sửa `docs/imm-00/05 §III.26.3` cùng vòng.


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

#### 3.14-bis `get_asset_repair_history` — hợp đồng TRUNG THỰC khi cắt: `+total` `+truncated` (CR-69) ✅ BE IMPLEMENTED (2026-07-25)

> ✅ **BE Bước-4 ĐÃ LAND** (`services/imm09.py::get_asset_history` `:2056-2080` — import SSoT `:32`, `history, pg = RepairRepo.list(scope="system", ...)` GIỮ NGUYÊN scope/comment R5-D6, `truncation_meta(len(history), int(pg["page_size"]), lambda: int(pg["total"]))` `:2077-2078`). Guard: `assetcore/tests/imm09/test_imm09.py::TestAssetRepairHistoryTruncation` (4 TC — HIST-01/02/03 + **HIST-04 phiếu `docstatus=0` KHÔNG lọt vào `total`**, chống lệch predicate) — `test_imm09` **207 OK**. FE `.ts` = việc của Bước-4 [FE] (song song).

> **Mục tiêu (CR-69):** tab **"Lịch sử sửa chữa"** của màn hồ-sơ-vận-hành thiết bị đang **cắt IM LẶNG** theo `limit`. Hệ quả nghiệp vụ nặng nhất nằm ở đây: KTV/kỹ sư trưởng dùng chính danh sách này để quyết định **sửa tiếp hay đề nghị thanh lý** (WHO HTM *Decommission*; hồ sơ thiết bị NĐ98). Thấy 10 lần hỏng ≠ biết máy đã hỏng 34 lần. Quyết định gốc: [`ADR-IMM00-TRUNCATION-SSOT`](../imm-00/ADR-IMM00-TRUNCATION-SSOT.md) (EXTENDS CR-43/46/47).

**Endpoint KHÔNG đổi:** `GET assetcore.api.imm09.get_asset_repair_history` (`api/imm09.py:195` → `services/imm09.py::get_asset_history` `:2055-2068`). Auth/param/`scope="system"` (R5/D6 device-centric) **GIỮ NGUYÊN**.

**Response — 2 khoá MỚI (ADDITIVE) trong `data`:**

```jsonc
{
  "success": true,
  "data": {
    "asset_ref": "AC-ASSET-2026-00042",
    "history": [ /* ≤ limit dòng, mới→cũ — KHÔNG đổi */ ],
    "total": 34,      // COUNT thật trên {asset_ref, docstatus:1} @Asset Repair TRƯỚC khi cắt
    "truncated": 1
  }
}
```

| Field | Kiểu wire | Nguồn (SSoT) | Ràng buộc |
|---|---|---|---|
| `total` | `integer` ≥ 0 | `pg["total"]` do `RepairRepo.list(scope="system")` **ĐÃ tính** (`repositories/base.py:160-161` → `count_ignore_permissions`, filter `{asset_ref, docstatus:1}`) | KHÔNG query COUNT thứ hai · KHÔNG `nullable` |
| `truncated` | `integer` ∈ `{0,1}` | `truncation_meta(len(history), eff_limit, lambda: pg["total"])` | KHÔNG `boolean`, KHÔNG `None` (CR-01) |

**BE Bước-4 delta** (`services/imm09.py::get_asset_history` — 4 dòng, mirror y hệt imm08 §9.2):

1. Thêm import `from assetcore.services.shared.truncation import truncation_meta` (imm09 **CHƯA** import — khác imm08 đã có sẵn `:23`).
2. `history, _ = RepairRepo.list(...)` → `history, pg = RepairRepo.list(...)`.
3. `total, truncated = truncation_meta(len(history), pg["page_size"], lambda: pg["total"])`.
4. `return {"asset_ref": asset_ref, "history": history, "total": total, "truncated": truncated}`.

> ⚠️ **INV-TRUNC-LIMIT (ADR §D5):** đối số thứ 2 = **`pg["page_size"]`** (trần đã clamp `[1,100]`), KHÔNG phải `limit` thô — xem giải thích bẫy ở `../imm-08/05_API_Specification.md §9.2`.
> ✅ **`total` ở đây là tổng TOÀN THIẾT BỊ** (không row-scope) vì nguồn khai `scope="system"`, và `count` dùng **cùng engine** `frappe.get_all` với rows ⇒ INV-ROWSCOPE giữ nguyên (`total == len(history)` khi `total <= limit`).

**Boundaries (Always / Never):**
- **Always:** derive qua SSoT `truncation_meta` · `count_fn` tái dùng `pg["total"]` (0 query thêm) · `truncated` là `int` · `data.required` GIỮ `[asset_ref, history]`.
- **Never:** KHÔNG đổi `scope="system"` thành `"user"` (đổi tập row = đổi ngữ nghĩa D6, ngoài phạm vi CR-69) · KHÔNG bỏ `docstatus:1` khỏi filter `count_fn` (count phải **cùng predicate** với rows — bỏ sót ⇒ `total` đếm cả phiếu Draft ⇒ `truncated` báo oan) · KHÔNG thêm param/path/opId · KHÔNG đưa 2 khoá vào `required`.

**BẤT BIẾN ĐO ĐƯỢC (test `test_imm09`):**

| Invariant | Kiểm chứng |
|---|---|
| **INV-CMH-1** | 3 phiếu submitted, `limit=10` ⇒ `len(history)==3` ∧ `total==3` ∧ `truncated==0` |
| **INV-CMH-2** | 12 phiếu submitted, `limit=5` ⇒ `len==5` ∧ `total==12` ∧ `truncated==1` |
| **INV-CMH-3** (vừa khít) | ĐÚNG 5 phiếu, `limit=5` ⇒ `total==5` ∧ **`truncated==0`** |
| **INV-CMH-4** (kiểu wire) | `type(total) is int` ∧ `type(truncated) is int` (KHÔNG `isinstance` — `bool ⊂ int` ⇒ false-green) |
| **INV-CMH-5** (predicate parity) | asset có 4 phiếu submitted + 3 phiếu **Draft** (`docstatus=0`), `limit=2` ⇒ `total==4` (**KHÔNG 7**) ∧ `truncated==1` |
| **INV-CMH-6** (additive) | `asset_ref` + `history` GIỮ NGUYÊN (0 breaking) |

**FE Bước-4 delta — `frontend/src/api/imm09.ts:239-247`:**

```ts
): Promise<{ asset_ref: string; history: AssetRepair[]; total?: number; truncated?: 0 | 1 }> {
```

Quy tắc render + lý do 2 khoá là **optional** (OAS ngoài `required` + cửa sổ `--preload` chưa reload): xem `../imm-08/05_API_Specification.md §9.2` mục *FE Bước-4 delta* — áp dụng y nguyên, đổi câu chữ dải cảnh báo thành "Đang xem một phần lịch sử sửa chữa — thiết bị có tổng {total} lượt sửa." **Never:** `any` · `truncated: boolean` · tự suy "còn nữa" bằng `history.length < total`.

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
  /**
   * AC-CR-78 — số dòng `spare_parts_used` CHƯA có phiếu xuất kho hợp lệ
   * (= số dòng `stock_entry_ok === 0`). `> 0` ⇒ BR-09-02 sẽ chặn submit ⇒ FE cảnh báo
   * TRƯỚC, không để người dùng ăn 422 tại `on_submit`. Optional (forward-compat:
   * trước khi BE enrich → undefined → 0 dải cảnh báo, KHÔNG vỡ). Xem §13.3.
   */
  parts_pending_stock_entry?: number
}

/** AC-CR-78 — enum SSoT trạng thái phiếu xuất kho của 1 dòng phụ tùng (§13.2). */
export type StockEntryStatus = 'OK' | 'MISSING' | 'NOT_FOUND'

export interface SparePartRow {
  idx: number
  item_code: string
  item_name: string
  qty: number
  uom: string
  unit_cost: number
  total_cost: number
  stock_entry_ref: string | null
  /**
   * AC-CR-78 — trạng thái THẬT của phiếu xuất kho, tính bằng CÙNG predicate SSoT với
   * validator BR-09-02 (`_spare_row_stock_status`, xem `04 §3.8.2`):
   *  - `OK`        → ref trỏ `AC Stock Movement` tồn tại
   *  - `MISSING`   → chưa có ref
   *  - `NOT_FOUND` → **ref TREO** (dangling) — trước AC-CR-78 hiển thị NHƯ HỢP LỆ (badge xanh giả)
   * FE PHẢI phân biệt đủ 3 nhánh, KHÔNG suy diễn lại từ `stock_entry_ref` (INV-PARTS-1).
   * Optional (forward-compat) — undefined ⇒ fallback hành vi cũ 2 nhánh.
   */
  stock_entry_status?: StockEntryStatus
  /** AC-CR-78 — `1` ⟺ `stock_entry_status === 'OK'`. **integer 0|1**, KHÔNG boolean (quirk CR-01). */
  stock_entry_ok?: 0 | 1
}

/**
 * CR-73a — kiểu TRẢ VỀ của `searchSpareParts()`. TÁCH RIÊNG khỏi `SparePartRow`
 * (row `spare_parts_used` của phiếu) vì hai thứ có vòng đời khác nhau: gợi ý mang
 * khoá nhận dạng nguồn (`device_model`, `spare_part`), còn row phiếu thì không.
 * Nhồi 3 field mới vào `SparePartRow` sẽ ép mọi nơi dựng row phiếu
 * (`CMPartsView.addPart`) phải khai thêm field vô nghĩa.
 * KHÔNG optional, KHÔNG `| null` — BE cam kết luôn có mặt, vắng = "".
 */
export interface SparePartSuggestion {
  idx: number
  item_code: string
  item_name: string
  manufacturer_part_no: string
  qty: number
  uom: string
  unit_cost: number
  total_cost: number
  stock_entry_ref: string
  notes: string
  device_model: string        // PK IMM Device Model — dành cho máy
  device_model_name: string   // model_name — dành cho người (hiển thị)
  spare_part: string          // PK AC Spare Part — "" nếu không resolve
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
| **INV-CM-SLA-6 (card == drill PER-PERSONA — 2026-07-25, D7)** | INV-CM-SLA-5 phải đúng cho **TỪNG persona**, không chỉ Administrator. Sau INV-ROWSCOPE, drill chạy `scope="user"` (permission-aware) ⇒ `cm_sla_breach_count()` PHẢI permission-aware theo: nhánh `flagged` đổi `RepairRepo.count` → `count_with_or(...)`, nhánh live truyền `scope="user"` (`services/imm09.py:776, 607`). Nếu để card global vs drill scoped, KTV thấy card **12** nhưng drill **2** — chính class-of-bug mà §7.1 sinh ra để chặn. Xem [ADR-IMM00-LIST-SCOPE §8.4b](../imm-00/ADR-IMM00-LIST-SCOPE.md) + BR-09-LISTSCOPE (§3.1). |

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
| `request_spare_parts` | BR-09-02 (gắn stock_entry_ref), **BR-09-22** (Gate-2 → IMM-15: chỉ tạo allocation khi resolve được `AC Spare Part` + `warehouse`; `null` KHÔNG được dùng để che lỗi quyền — §3.6-bis) |
| `search_spare_parts` | **BR-09-21** (khoá nhận dạng gợi ý = cặp `(device_model, phụ tùng)`; resolve `spare_part` DETERMINISTIC theo §3.13-bis(4); role-gate `IMM Device Model`) |
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

### §10.4 Mobile-BE CR ledger — trạng thái chốt (contract-only, cập nhật 2026-07-27)

Sổ trạng thái CR **contract-layer** (OpenAPI mirror `docs/mobile/openapi/assetcore-mobile.openapi.yaml`) để vòng sau **KHÔNG re-spec** thứ đã đóng. Mỗi dòng có bằng chứng `file:line` verify tại vòng ghi nhận.

| CR | Module | Nội dung | Trạng thái | Bằng chứng @source (verify 2026-07-25) |
|---|---|---|---|---|
| **AC-CR-86** | **IMM-11** | **Dời lịch hiệu chuẩn KHÔNG có đường hợp lệ nào** — `_UPDATE_ALLOWED` (`services/imm11.py:1155-1161`) KHÔNG chứa `scheduled_date` ⇒ `update_calibration` **NUỐT IM LẶNG** khoá này (`:1217` lọc patch → trả `success` + 0 thay đổi), buộc người dùng hủy + tạo lại → **đẻ phiếu `Cancelled` rác vào hồ sơ tuân thủ NĐ98 + mất lịch sử phiếu**. Curate op `rescheduleCalibration` (`assetcore.api.imm11.reschedule_calibration`): **+1 path 109→110** · **+3 schema 287→290** (`RescheduleCalibrationRequest` CLOSED 3 khoá `required:[name,new_date,reason]`, `reason.minLength:5`, `new_date.format:date` / `RescheduleCalibrationResponse` 4 khoá `{name,old_date,new_date,status}` / `RescheduleCalibrationEnvelope`) · **parameters GIỮ 38** · property-add `CalibrationDetail.can_reschedule` (derived-bool; `required` GIỮ `['name']`). Hợp đồng: `status` **KHÔNG FLIP** (khác `reschedulePm` của IMM-08 vốn flip `Pending–Device Busy`) · guard SSoT `RESCHEDULE_CAL_STATES={Scheduled,In Progress}` ∧ `docstatus==0` · `reason` ≥5 ký tự · `new_date ≥ today` · **ĐÚNG 1** `log_audit_event` + append `amendment_reason` mỗi lần dời · cap `calibration.write` gate ở **SERVICE** (403 in-envelope, khuôn `_require_rca_cap` `services/imm12.py:366`) · **KHÔNG đụng** `AC Asset.next_calibration_date` + `IMM Calibration Schedule.next_due_date`. Kèm BR-11-20: `update_calibration` từ chối TƯỜNG MINH khoá `scheduled_date` (422 + `fields`). **Đóng mobile CR-81.** | 🟡 **Contract ĐÓNG (Bước-2) — BE Bước-4 CHƯA land** (`api/imm11.py::reschedule_calibration` chưa tồn tại ⇒ path ở `_PENDING_BE_PATHS`) | `services/imm11.py:1155` `_UPDATE_ALLOWED` (thiếu `scheduled_date`) · `:1217` lọc patch · `services/imm08.py:1515` `reschedule` (sibling PM, CÓ flip) · `services/imm12.py:366` `_require_rca_cap` · spec `docs/imm-11/02 §BR-11-19/20` + `04 §4.1.12/13` + `05 §0.1.11` + `07 §IX`; guard `test_mobile_oas` **1024 OK** (+9 `cr86_a..i`) · `test_mobile_docset` **9 OK** · `test_imm11` **120 OK** (baseline, TC mới thuộc Bước-4) |
| **AC-CR-85** | **IMM-09** | **Dư âm cổng ảnh AC-CR-84 — 2 lỗ đã bịt, 0 đổi hợp đồng OAS.** (a) **NÚT CHẾT** `confirm_inspection`: P3 chỉ gác khoá `close_work_order` trong khi P2 enforce ở `confirm_inspection` ⇒ thiết bị **tái phân loại** lên `High/Critical` SAU khi phiếu đã 'Pending Inspection' làm CTA bật + `reason` rỗng (vỡ **D9/INV-CMCTA-9**) rồi 422 khi bấm. Sửa: bậc business thứ hai + hằng reason riêng `_REPAIR_ACTION_REASON_EVIDENCE_PHOTO_INSPECT` (**INV-CMEVID-4b**). (b) `attach_repair_checklist_photo` **0 guard** `docstatus`/`status` (ghi bằng `frappe.db.set_value` ⇒ lách immutability Frappe, bồi ảnh vào phiếu ĐÃ SUBMIT) ⇒ P5 `_assert_repair_photo_attachable`, đặt **SAU** dedupe pre-check để KHÔNG phá BR-09-16-IDEMP (**INV-CMEVID-9**). (c) **NỚI oracle** parity 54 ô: `_CR82_ADVERTISED_GATE_CODES` tính CẢ mã bậc business + meta-guard AST `test_cr82_b3` | 🟢 **BE LAND 2026-07-27** — `test_imm09` **278 OK** (273→278: `TC-CM-EVID-15..18` + `TC-CR82-B3`), mutation-verify **2/2 ĐỎ** đúng thiết kế · `test_mobile_oas` GIỮ **1008 OK** · `test_mobile_docset` **9 OK** · `test_imm08` **196 OK** · `test_imm12` **198 OK**. **0 đổi YAML ngoài REFRESH CITE** `services/imm09.py` (113 cite dịch dòng + 39 cite dạng dải `A-B`, remap bằng script difflib old→new). 🔴 **3 điểm CHỜ [BA] ratify** (§16.12): **H2** ngõ cụt «Không thể sửa chữa» (ADR-IMM09-CTA-01 ⟂ ADR-IMM09-EVIDENCE-04 — cần chốt khoá CTA thứ 7 hay cách khác) · **M2** dòng `result='N/A'` · **L1** rò `#idx` trần. 🟡 **[FE] M1** ẩn thẻ bằng chứng ở trạng thái kết thúc | `services/imm09.py` `_build_repair_available_actions` (bậc business `confirm_inspection`) · `_assert_repair_photo_attachable` + call-site trong `attach_repair_checklist_photo` (sau dedupe pre-check) · `_REPAIR_ACTION_REASON_EVIDENCE_PHOTO_INSPECT` · `_MSG_REPAIR_PHOTO_WO_FINISHED` · tái dùng SSoT `REPAIR_TERMINAL_STATES` (KHÔNG literal mới) · test `assetcore/tests/imm09/test_imm09.py::TestCmEvidencePhotoGate.test_cr84_15..18` + `TestCmAvailableActionsParity.test_cr82_b3` + `_CR82_ADVERTISED_GATE_CODES` · nguồn phát hiện: QA vòng 3 (HIGH-1/MED-3) |
| **AC-CR-84** | **IMM-09** | **Cổng ẢNH BẰNG CHỨNG NĐ98 (Class C/D) khi đóng phiếu CM hết là CODE CHẾT** — predicate SSoT `_repair_evidence_missing_idxs` dùng CHUNG cho **enforcement** (`close_work_order` + pre-check `confirm_inspection` chống lách), **advertise** (`available_actions[close_work_order].enabled` + reason VI) và **read** (3 khoá `evidence_photo_required` int 0\|1 / `evidence_photo_missing_idxs` array<int≥1> / `evidence_photo_total_required` trên `RepairWorkOrderDetail`). Mã lỗi mới `IMM09-EVIDENCE-PHOTO-REQUIRED` (422) **đến trên HTTP-200** kèm `context.missing_count`/`missing_idxs` + `fields.repair_checklist`. Nguồn nhóm nguy cơ = `risk_classification` {High, Critical} — **KHÔNG** `risk_class` (Class I/II/III, ánh xạ MẤT MÁT: chính chỗ này làm cổng chết trên mobile). `""` (chưa phân loại) ⇒ KHÔNG chặn. Miễn trừ nhánh `cannot_repair=1`. **Đóng mobile CR-51** (kèm phần enforcement còn nợ của **CR-15**) | 🟢 **BE Bước-4 ĐÃ LAND 2026-07-27** (predicate SSoT `_repair_evidence_missing_idxs` + 4 điểm tiêu thụ + mã `IMM09-EVIDENCE-PHOTO-REQUIRED` LIVE; `test_imm09` **273 OK** +14, mutation-verify **7/7 ĐỎ**; `gen_fe_messages --check` xanh; lật `cr84_i`→`cr84_j` + REFRESH CITE ⇒ `test_mobile_oas` GIỮ **1008 OK**; 🟡 **FE Bước-4 còn lại**; cần USER reload gunicorn). CONTRACT ĐÓNG (Bước-2): OAS + guard XANH: `test_mobile_oas` **1008 OK** (`cr84_a..i`, `cr84_i` = PENDING-BE phải LẬT khi BE land) · `test_mobile_docset` **9 OK**; `paths`/`schemas`/`parameters` GIỮ **109/287/38**; `required` GIỮ `['name']` (ADR-IMM09-EVIDENCE-03 — self-correction A7). Kèm sửa **cite-rot 4 chỗ** + **cải chính cap** `closeWorkOrder` `repair.submit`→`repair.create` | `repair_checklist.json` field `photo` · `services/imm09.py:1595` attach_repair_checklist_photo (đính được) · `:2046` close_work_order + `:955` validate_repair_checklist_complete (**0 chỗ đọc `photo` để chặn**) · `_risk_map` ánh xạ mất mát · `frontend/src/constants/labels.ts:430-445` (web có predicate đúng nhưng chỉ tô màu) |
| **AC-CR-83** | **IMM-12** | **`submit_rca`: 3 ràng buộc hồ sơ RCA HẾT thoát envelope thành HTTP-417 THÔ** — curate op `submitRca` (`assetcore.api.imm12.submit_rca`): **+1 path 108→109**, **+4 schema 283→287** (`SubmitRcaRequest`/`RcaFiveWhyStepInput`/`SubmitRcaResponse`/`SubmitRcaEnvelope`), `parameters` **GIỮ 38**. Slot **CHỈ `{200,401,403}`**; 200 = `oneOf [SubmitRcaEnvelope, Error]` closed-schema 0-discriminator. Hợp đồng lỗi: **5 `message_code`** (`IMM12-RCA-FIVE-WHY-INCOMPLETE` 🆕 422 · `…-ROOT-CAUSE-REQUIRED` 422 · `…-CORRECTIVE-REQUIRED` 422 · `IMM12-RCA-ASSIGNEE-REQUIRED` 🆕 422 · `…-ALREADY-COMPLETED` 409) **tất cả đến trên HTTP-200** kèm `fields` field-level; khoá `fields` dùng **TÊN THAM SỐ GHI** `corrective_action` (KHÔNG `corrective_action_summary` — CR-52 quirk 2) và **số hiển thị** bước `five_why_steps.<why_number>`. Đóng **mobile CR-52 §3+§4** (quirk 3 "cao") | 🟢 **RESOLVED-BE 2026-07-27 (Bước-4)** — hợp đồng XANH: `test_mobile_oas` **999 OK** (`cr83_a..g`, ô `cr83_g` MỚI = parity registry LIVE 5/5 mã + `http_status` + `template` khác rỗng) · `test_mobile_docset` **9 OK**. Mutation-verified ×3 ở Bước-2 (rot cite ⇒ `cr83_e` ĐỎ · property `corrective_action_summary` vào body ⇒ `cr83_b` ĐỎ · slot `'422'` ⇒ `cr83_c` ĐỎ). 🟢 **BE LANDED (Bước-4):** `utils/notify.py::nthrow(..., fields=…)` @`:61` (truyền thẳng `ServiceError(fields=…)`) · `utils/messages.py` +3 hằng & entry (`IMM12_RCA_FIVE_WHY_INCOMPLETE` 422 · `IMM12_RCA_ASSIGNEE_REQUIRED` 422 · `IMM12_RCA_SUBMIT_NOT_COMPLETED` 409; 2 entry cũ **0 ký tự đổi** — INV-RCA-6) · `services/imm12.py` 3 predicate THUẦN `validate_five_why_payload` @`:974-1025` / `validate_rca_assignment` @`:1028-1040` / `validate_rca_completion` @`:1043-1071` + 2 adapter `_nthrow_violation` @`:1074-1077` / `_nthrow_violation_in_hook` @`:1080-1086` + **PRE-CHECK** `submit_rca` @`:1236-1250` (NGAY SAU guard trạng thái `:1230`, TRƯỚC phép gán đầu tiên `:1253`) · controller `imm_rca_record.py` **6 → 0** `frappe.throw` (3 validator lazy-import CHÍNH 3 predicate = backstop, hết 'luật thứ hai'; `on_submit` → `nthrow_in_hook(MSG.IMM12_RCA_SUBMIT_NOT_COMPLETED)`) · `frontend/src/locales/messages.ts` regen (`gen_fe_messages.py --check` 0 drift, 149 MSG). Test TDD `test_imm12.py::TestRcaSubmitEnvelope` (11 TC) + `TestRcaValidatorSsot` (3 TC) ⇒ module **198 OK** (185→198). **RED-before đo được:** `frappe.exceptions.ValidationError: Bước 3: phải điền đầy đủ câu hỏi và câu trả lời.` thoát qua `handle` từ `imm_rca_record.py:69`. **Mutation ×3 (BE):** dời pre-check xuống SAU `rca.status=Completed`+`save()` ⇒ TC-03 ĐỎ · khoá `fields` → `corrective_action_summary` ⇒ TC-05 ĐỎ · controller giữ vòng lặp riêng ⇒ TC-11 ĐỎ (`[74] != []`); hoàn nguyên ⇒ XANH. **Cite ĐÃ refresh:** 14 cite `services/imm12.py` trong op+4 schema AC-CR-83 (`963→1116 create_rca` · `1070→1230` · `1075/1077→1240` · `1081→1253` · `1083→1255` · `1084→1256` · `1085→1257` · `1088→1260` · `1091→1265` · `1099→1272` · `1109→1282` · `1118→1290` · `1120→1292`) + 2 cite lân cận cùng module (`get_incident_detail`→`1579-1663` · `get_asset_incident_history`→`1709-1763`) ⇒ 0 DRIFT (script AST). 🔴 **CÒN LẠI:** `RCADetailView.vue` đọc `ApiError.fields` + render dưới đúng control = **[FE] Bước-4**; **BLOCKED-RELOAD** — `.py` đổi chỉ thấy trên HTTP live sau khi USER `bench restart` (gunicorn `--preload`; KHÔNG curl để chấm DoD — LL-DEPLOY-07/08) | **Spec:** [`imm-12/05 §22`](../imm-12/05_API_Specification.md) (hợp đồng đầy đủ + INV-RCA-1..9 + D-RCA-1..4 + ADR-IMM12-13/14/15 + Boundaries) · BR-12-28 [`imm-12/02 §IV`](../imm-12/02_Analysis_Design.md) · code-shape [`imm-12/04 §4.1+§4.3`](../imm-12/04_Backend_Design.md) · FE [`imm-12/06 §7.1`](../imm-12/06_Frontend_Design.md) · TC [`imm-12/07 §IX`](../imm-12/07_Testing_QA.md). **Grounding (verify TẠI CHỖ 2026-07-27):** `services/imm12.py:1093 submit_rca` (`rca.save()` → hook) · `assetcore/assetcore/doctype/imm_rca_record/imm_rca_record.py:14-16` (3 validator) + `:30,54,64,69,77,79` (6 `frappe.throw` TRẦN) · `utils/api_handler.py:44` (CHỈ bắt `ServiceError`) · `services/imm12.py:962-963 create_rca` (seed 5 bước `why_answer=""` ⇒ ca phổ biến nhất) · `services/imm12.py:1075-1078 submit_rca` (2 nhánh có sẵn, thiếu `fields`) · `utils/notify.py:61 nthrow` (CHƯA có `fields`) · `services/shared/errors.py:43,50` + `utils/api_handler.py:57` (đường `fields` ĐÃ sẵn sàng) · `frontend/src/api/helpers.ts::hydrateApiError` (FE đã nhận `fields`) · `frontend/src/views/incident/RCADetailView.vue:105-126` (CHƯA đọc `fields`). **Counters delta ĐÃ sync (Bước-2 +6, Bước-4 +1):** `_EXPECTED_TEST_COUNT` 992→998→**999** (+2 echo trong `cancelcal_j`/`receivecert_j`) · `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` →**999** · `_GUARD_SUITE_SUM` 1135→1141→**1142** · `_MOBILE_OAS_TOTAL` 1161→1167→**1168** · `cr83_submit_rca_envelope_delta = 7`. **Quan hệ sổ mobile:** ĐÓNG **`CR-52 §3+§4`**; **VẪN MỞ** → `CR-70` · `CR-72` · `CR-74m` · `CR-75m` phần dư · `CR-61(b)` phần stream/proxy tệp |
| **AC-CR-82** | **IMM-09** | **`getRepairWorkOrder` phơi `available_actions[]` 6 CTA server-driven** — ĐÚNG 6 phần tử thứ tự CỐ ĐỊNH `[assign_technician, submit_diagnosis, request_spare_parts, start_repair, close_work_order, confirm_inspection]` cho MỌI status trong 9 state (terminal ⇒ vẫn đủ 6, `enabled=false`); phần tử = `AvailableAction` (TÁI DÙNG, **0 schema mới**), `route=""`. `enabled = transition_allowed ∩ has_cap ∩ business_gate`: `transition_allowed` đọc CÙNG hằng `*_FROM` mà 6 service guard dùng · `has_cap` = **HỘI cap 2 tầng** (api `repair.write` ∩ service `repair.create`; close = `repair.create`; confirm = `repair.submit`) · business = **SoD CR-41 FAIL-OPEN**. `reason` VI HẰNG, 3 bậc `transition > capability > business`; D9 `enabled=false ⟺ reason != ""`. Thuần additive: `allowed_transitions` + mọi khoá detail GIỮ NGUYÊN. `paths` GIỮ **108** · `schemas` GIỮ **283** · `parameters` GIỮ **38**. Đóng **NỬA CM của mobile CR-74** (nửa PM = AC-CR-77) ⇒ 3 màn Chi tiết dùng CHUNG 1 từ vựng CTA | 🟢 **CONTRACT ĐÓNG Bước-2 2026-07-27 (BA)** — OAS + guard LANDED và XANH: `test_mobile_oas` **991 OK** (+8 `cr82_a..h` class `TestMobileRepairAvailableActionsParity`) · `test_mobile_docset` **9 OK**. 🟡 **BE+FE Bước-4 CHƯA land**: `_build_repair_available_actions` + 6 hằng `*_FROM` + test parity 54 ô (`test_imm09`) · `CMWorkOrderDetailView.vue` gate 6 CTA + tooltip `reason` + fallback. ⚠️ BE land ⇒ **8 cite PHẢI refresh** (dòng `services/imm09.py` dịch) + bồi `cr82_i` ⇒ 991→992 | Spec §15 · divergence @`api/imm09.py:123/129/137/143/165/182` vs `services/imm09.py:1882/1724/1748/1767/1879/1998` · guards @`services/imm09.py:1881/1723/1747/1766/1859/1985` · SoD @`services/imm09.py:2151 _resolve_wo_closer` |
| **AC-CR-81** | **IMM-05** | **Mỗi dòng hồ sơ phơi TỆP THẬT** — `AssetDossierDocItem` **13 → 18** property/`required`: `file_url` (str, rỗng = `""`) · `file_name` (str, nguồn `File.file_name` — KHÔNG phải cột denorm `file_name_display`) · `file_size` (int BYTE) · `is_private` (int 0|1) · `has_file` (int 0|1). Batch-resolve **ĐÚNG 1 truy vấn `File`** cho toàn payload theo tập `file_url` đã dedup của các dòng **ĐƯỢC XEM** (0 query khi tập rỗng) — chống N+1 **và** chống rò URL của dòng bị ẩn. **Luật LINK MỒ CÔI:** `file_attachment` trỏ URL không còn `File` doc ⇒ `has_file=0` ∧ `file_url=""` (endpoint **KHÔNG phát link chết**); `file_attachment` **thô** không bao giờ ra response. `paths` GIỮ **108** · `schemas` GIỮ **283** · `parameters` GIỮ **38** (chỉ thêm property scalar). Đóng **`CR-61(b)` phần METADATA** sổ mobile | 🟢 **RESOLVED-BE 2026-07-27 (Bước-4)** — OAS + guard LANDED và XANH: `test_mobile_oas` **983 OK** (+8 `cr81_a..h` class `TestMobileAssetDossierFileContract`; `cr75_g` SUPERSEDE 13→18 khoá) · `test_mobile_docset` **9 OK**. **Mutation-verified ×3 (Bước-2):** `has_file`→`boolean` ⇒ `cr81_b` ĐỎ · rot cite `imm05.py:610-618`→`:2000` ⇒ `cr81_c` ĐỎ · bỏ `has_file` khỏi `required` ⇒ `cr81_a` ĐỎ; hoàn nguyên ⇒ XANH. 🟢 **BE LANDED (Bước-4, 2026-07-27):** `assetcore/services/imm05.py` — `_resolve_file_meta` @`:458-502` (1 query `File`, `ignore_permissions=True`, `order_by="creation asc"`, `int()` tường minh) + `_EMPTY_FILE_META` @`:453-455` + `_DT_FILE` @`:450` · `_DOSSIER_ROW_FIELDS` += `file_attachment` @`:443` (khối `:440-444`) (12→13 select) · call-site batch @`:675-678` (tập vào = **V** đã lọc visibility) · `pop` + `update` @`:683-685` · `_DOSSIER_COMPUTE_FIELDS` @`:448` **0 ký tự đổi** (AC4). Test TDD `assetcore/tests/imm05/test_imm05.py::TestAssetDossierFileMeta` **12 TC** (`test_cr81_01..12`, fixture `_mk_file` tạo `File` doc THẬT đuôi `.docx` — VR-08 chặn `.txt`, nội dung có tiền tố ngẫu nhiên vì `File.validate_duplicate_entry` gộp `content_hash` trùng về CÙNG `file_url`) ⇒ module **91 OK** (79→91). **RED-before đo được:** `KeyError: 'has_file'` / `'file_url' not found in {…13 khoá}` / 0 truy vấn `File`. **Mutation ×4 (BE):** bỏ điều kiện File-tồn-tại ⇒ #03 ĐỎ · resolve trong vòng lặp ⇒ #06 ĐỎ (6≠1) + #08 ĐỎ · bỏ `_apply_visibility_filter` ⇒ #10 ĐỎ (rò URL dòng ẩn) · `get` thay `pop` ⇒ #12 ĐỎ (19≠18); hoàn nguyên ⇒ XANH. **Cite ĐÃ refresh (BE):** 5 `description` → `services/imm05.py:458-502 _resolve_file_meta`; item/op description → `:675-678 get_asset_documents`; dọn thêm 4 cite CR-75 bị dịch dòng do helper mới (`:548-633`→`:605-706` get_asset_documents · `:473-544`→`:530-601` _dossier_compliance · `:614-633`→`:693-706` return-dict · `:614-622`→`:679-691` vòng group · `_DOSSIER_ROW_FIELDS @:433-437`→`@:440-445` · `:625`→`:691`) ⇒ 0 DRIFT trên toàn OAS (script AST). Guard XANH sau refresh: `test_mobile_oas` **983 OK** · `test_mobile_docset` **9 OK**; mutation cite `:458-502`→`:2000` ⇒ `cr81_c` ĐỎ. 🔴 **CÒN LẠI:** `DocumentDossierCard.vue` render «Mở tệp»/«Chưa đính kèm tệp» + type `.ts` = **[FE] Bước-4**; **BLOCKED-RELOAD** — `.py` đổi chỉ thấy trên HTTP live sau khi USER reload gunicorn `--preload` (KHÔNG curl để chấm DoD) | **Spec:** [`imm-05/05 §2.7.c–§2.7.d`](../imm-05/05_API_Specification.md) (F0–F6 + INV-FILE-1..8 + Boundaries) · BR-05-22..25 + ADR-IMM05-04..07 [`imm-05/02 §IV.2 + §IV.2.b`](../imm-05/02_Analysis_Design.md) · code-shape [`imm-05/04 §4.4-bis`](../imm-05/04_Backend_Design.md) · FE [`imm-05/06 §4.4-bis`](../imm-05/06_Frontend_Design.md) · TC [`imm-05/07 §III.2.b`](../imm-05/07_Testing_QA.md) (TC-05-FILE-01..12 + TC-FE-DOSSIER-FILE-01..04). **Grounding (verify TẠI CHỖ 2026-07-27):** `services/imm05.py:605-706 get_asset_documents` (`@rowscoped`; V @`:643-648` permission-aware ĐÃ lọc visibility — nguồn DUY NHẤT của tập URL; C @`:651-656` `scope="internal"` — **CẤM** dùng làm tập vào; vòng group @`:679-691`; `hidden_count` @`:704`) · `_DOSSIER_ROW_FIELDS` @`:440-444` (**chưa** select `file_attachment` — BE phải thêm rồi `pop`) · `_DOSSIER_COMPUTE_FIELDS` @`:448` (**KHÔNG đụng** — AC4) · `_apply_visibility_filter` @`:162-165` · DocType field `file_attachment` (Attach) + `file_name_display` @`assetcore/assetcore/doctype/asset_document/asset_document.json:152` (denorm tính lúc save @`asset_document.py:198-199` ⇒ stale) · upload SSoT `assetcore/api/files.py::upload_attachment` (mọi tệp mới `is_private=1`) · fixture MỒ CÔI sẵn có `assetcore/tests/imm05/test_imm05.py:1161` (`/files/dummy-test.pdf`, 0 File doc) ⇒ ca CR-75 cũ tự rơi nhánh `has_file=0`, **0 sửa fixture** · OAS `AssetDossierDocItem` @`docs/mobile/openapi/assetcore-mobile.openapi.yaml:11265` · nguồn yêu cầu `/home/miyano/assetcore-mobile/docs/api/CONTRACT-REQUESTS.md:2792` (CR-61(b)). **Counters delta +8 ĐÃ sync:** `_EXPECTED_TEST_COUNT` 975→**983** (+2 echo) · `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 975→**983** · `_GUARD_SUITE_SUM` 1118→**1126** · `_MOBILE_OAS_TOTAL` 1144→**1152** · `cr81_asset_dossier_file_delta = 8`. **Quan hệ sổ mobile:** ĐÓNG **`CR-61(b)` phần metadata**; **VẪN MỞ** → phần **stream/proxy tệp riêng tư + URL ký hạn + tải offline** (họ G6) · `CR-70` · `CR-72` · `CR-74m` · `CR-75m` |
| **AC-CR-80** | **IMM-00** (dùng chung IMM-04/08/09/11/12) | **Picker "người nhận việc" nói ĐÚNG SỰ THẬT** — curate op `listAssignableUsers` (`assetcore.api.user.list_assignable_users`) vào mirror: **+1 path 107→108**, **+2 schema 281→283** (`AssignableUserItem`, `AssignableUserListEnvelope`), `parameters` **GIỮ 38** (3 param INLINE). `context` **required** + enum **6 giá trị** = `{_ANY_USER_CONTEXT}` ∪ keys(`_ASSIGNABLE_CONTEXTS`) (guard import hằng THẬT). `data` đổi **mảng trần → object** `{items,total,truncated,limit}` derive qua SSoT `truncation_meta`; `truncated` **integer 0|1** (KHÔNG boolean); `total` đếm **SAU** lọc năng lực; `limit` là trần **ĐÃ clamp** 1..100; `context` lạ ⇒ **400 IN-ENVELOPE** trên HTTP-200 (VI, 0 leak DocType). Đóng **`CR-75`** sổ mobile (`listUsers.role` đơn-trị ⇒ picker buộc chọn giữa "lọc sai" và "không lọc") | ✅ **RESOLVED-BE 2026-07-27 (Bước-4)** — contract (Bước-2) **+** application code BE ĐÃ LAND cùng ngày. `test_imm00_base_role` **34 OK** (+13 TC `TestListAssignableUsers` TC-00-ASSIGN-01..12 + guard SSoT hằng ngữ cảnh) · `test_ac_user_source` **14 OK** · `test_imm00_user_approval` **4 OK** · `test_imm08` **196 OK** · `test_imm09` **243 OK** · `test_mobile_oas` **975 OK** (+8 `cr80_a..h` class `TestMobileAssignableUsersContract`) · `test_mobile_docset` **9 OK**. **Mutation-verified ×3 (BE vòng này):** (a) gỡ `truncation_meta` khỏi `list_assignable_users` ⇒ **5 TC ĐỎ** (ASSIGN-03/05/06/07/12) · (b) thêm khoá `_ASSIGNABLE_CONTEXTS` mà quên OAS ⇒ `cr80_b` ĐỎ · (c) rot cite `api/user.py:1057`→`:2000` ⇒ `cr80_e` ĐỎ; hoàn nguyên ⇒ XANH. *(Bước-2 đã mutation-verify bỏ enum ⇒ `cr80_b` ĐỎ · `truncated`→`boolean` ⇒ `cr80_d` ĐỎ.)* **9 cite `api/user.py:*` trong OAS + 5 trong `imm-00/05` ĐÃ REFRESH** theo dòng THẬT sau khi thêm import top-level `truncation_meta` (1035/1037/1047 → **1036/1038/1057**). 🔴 **BLOCKED-RELOAD** gunicorn `--preload` ⇒ HTTP live CHƯA reflect (chấm bằng `run-tests`, **KHÔNG curl** — 417 ma). 🟡 Còn **[FE] Bước-4** (`api/user.ts` tolerant reader + `ApproverSelect.vue` dải cảnh báo + test RENDER); trong cửa sổ chưa reload, FE gọi HTTP vẫn nhận **mảng trần** ⇒ ADR-IMM00-ASSIGN-04 (tolerant reader) là BẮT BUỘC, không phải tuỳ chọn | **Spec:** [`ADR-IMM00-TRUNCATION-SSOT §7`](../imm-00/ADR-IMM00-TRUNCATION-SSOT.md) (ADR-IMM00-ASSIGN-01..04 + INV-ASSIGN-1..8) · [`imm-00/05 §III.23`](../imm-00/05_API_Specification.md) · code-shape [`imm-00/04 §V.6`](../imm-00/04_Backend_Design.md) · FE [`imm-00/06 §VIII.3`](../imm-00/06_Frontend_Design.md) · TC [`imm-00/07 §XVII`](../imm-00/07_Testing_QA.md) · BR [`imm-00/02 §IV.38`](../imm-00/02_Analysis_Design.md). **Grounding (verify TẠI CHỖ 2026-07-27 SAU khi land):** endpoint `assetcore/api/user.py:1057-1137` (`items = capable[:limit]` @`:1130` → `truncation_meta(len(items), limit, lambda: len(capable))` @`:1136` → `_ok({items,total,truncated,limit})` @`:1137` — **hết cắt im lặng**; clamp `max(1, min(int(limit), 100))` @`:1101`; lọc capability @`:1125-1129` **GIỮ NGUYÊN** — AC-CR-80 KHÔNG đổi tập người) · allowlist `api/user.py:1038-1044` `_ASSIGNABLE_CONTEXTS` (5 khoá) + `api/user.py:1036` `_ANY_USER_CONTEXT` + hằng PUBLIC MỚI `api/user.py:1051-1053` `ASSIGNABLE_CONTEXT_KEYS` (nguồn DUY NHẤT cho nhánh validate @`:1097` **và** enum OAS — guard `cr80_b` import hằng THẬT) · predicate enforcement `services/imm09.py:1839 _is_repair_capable` + `services/imm09.py:1857 _assert_valid_technician` (`VALIDATION_ERROR`/422, `IMM09-INVALID-TECHNICIAN`) · SSoT cắt `services/shared/truncation.py:15 truncation_meta` · nguồn người `services/shared/ac_users.py:141 get_ac_users` (`limit_page_length=0` — caller tự cap) · envelope `utils/response.py:95 _err` (`code=VALIDATION_ERROR`, `http_status=400`) · web-FE caller `frontend/src/components/commissioning/ApproverSelect.vue:37` + `frontend/src/api/user.ts:205` (đang khai `AssignableUserItem[]`) · test `assetcore/tests/imm00/test_imm00_base_role.py:304` (`_names` ĐÃ đổi sang `res["data"]["items"]`) + 13 TC mới @`:354-573` · mobile CR-75 `/home/miyano/assetcore-mobile/docs/api/CONTRACT-REQUESTS.md:3226`. **Quan hệ sổ mobile:** ĐÓNG **`CR-75`**; **VẪN MỞ** → `CR-70` · `CR-72` · `CR-74m` · và **`CR-75m` phần dư** (`listUsers.role` vẫn đơn-trị — AC-CR-80 KHÔNG sửa `listUsers`, chỉ cấp đường ĐÚNG cho picker phân công) |
| **AC-CR-79** | **IMM-08 + IMM-09** | **Whitelist khoá `filters` = SSoT + khoá lạ trả 400 IN-ENVELOPE** — `_ALLOWED_FILTER_KEYS` khai ở `services/imm08.py` (**16 khoá**) / `services/imm09.py` (**18 khoá**); cơ chế raise dùng CHUNG `services/shared/filters.py::assert_allowed_filter_keys`. OAS **tách 2 param** `PmWorkOrderFilters`/`RepairWorkOrderFilters` khỏi `WorkOrderFilters` dùng chung (3 op / 3 tập khoá khác nhau — ADR-IMM08-FILTERKEY-01); `WorkOrderFilters` ở lại phục vụ **`listCalibrations`** kèm cảnh báo "IMM-11 CHƯA whitelist". `paths` GIỮ **107**, `schemas` GIỮ **281**, `components.parameters` **+2**. **Đóng `CR-70`** sổ mobile **KÈM CẢI CHÍNH** (dưới) | 🟢 **BE+OAS LANDED 2026-07-27 (Bước-4)** — `test_imm08` **194 OK** (+12 TC `TestPmFilterKeyWhitelist` TC-PMFK-01..12) · `test_imm09` **242 OK** (+12 TC `TestCmFilterKeyWhitelist` TC-CMFK-01..12) · `test_mobile_oas` **967 OK** (+8 `cr79_a..h`) · `test_mobile_docset` **9 OK** · `test_rowscope_invariant` **21 OK**. **Mutation-verified 4/4:** thêm khoá BE quên OAS ⇒ `cr79_d` ĐỎ · đổi tên khoá ⇒ `cr79_d` + `TC-PMFK-04` ĐỎ · sửa `_VENDOR_SCOPE_FIELD_MAP["PM Work Order"]`→`asset` ⇒ `TC-PMFK-05` ĐỎ · rot cite 798→898 ⇒ `cr79_g` ĐỎ. **AC8 ĐÓNG:** cải chính CR-70 đã ghi ở đây; sổ mobile trạng thái đề nghị **RESOLVED-BE + CẢI CHÍNH** (repo KHÁC — chỉ đề nghị sync, chờ user cho phép). 🔴 **2 CẢI CHÍNH SPEC do BE phát hiện khi land** (đã sửa trong `imm-08/05 §14.2`/`§14.6`): (1) envelope AssetCore là **PHẲNG** (`{success, error:<string>, code, http_status, message_code, …}` — `utils/response._err` + OAS `Error` closed-schema), **KHÔNG** lồng `error:{code,message}` như JSON mẫu Bước-2 vẽ; (2) `parse_json` raise `ServiceError` **legacy KHÔNG `message_code`** ⇒ malformed JSON **KHÔNG** trả `VAL-INVALID-PARAMS`; bất biến giữ được là **phân biệt được** 2 cách hỏng. **BLOCKED-RELOAD** gunicorn `--preload` ⇒ chưa reflect trên HTTP live (chấm bằng `run-tests`, KHÔNG curl). Còn **FE Bước-4** (AC6 banner không-thay-bảng + sửa `buildFilters()` PM bỏ `due_date_from`/`due_date_to`) | **Spec:** canonical [`docs/imm-08/05 §14`](../imm-08/05_API_Specification.md) · mirror CM **§14 (cuối file này)** · code-shape [`imm-08/04 §4.4`](../imm-08/04_Backend_Design.md) + [`imm-09/04 §3.9`](./04_Backend_Design.md) · FE [`imm-08/06 §FilterKeyError`](../imm-08/06_Frontend_Design.md) + [`imm-09/06 §FilterKeyError`](./06_Frontend_Design.md) · TC [`imm-08/07 §X`](../imm-08/07_Testing_QA.md) + [`imm-09/07 §X`](./07_Testing_QA.md). **BẰNG CHỨNG LỖI (probe LIVE 2026-07-27 qua `bench --site miyano console` — KHÔNG suy đoán):** `imm08.list_work_orders({"khong_ton_tai_abc":"x"})` → `OperationalError (1054, "Unknown column 'tabPM Work Order.khong_ton_tai_abc' in 'WHERE'")` · `imm09` cùng khoá → `'tabAsset Repair.khong_ton_tai_abc'` · **`imm08` với `{"due_date_from":[…],"due_date_to":[…]}` → 1054 `'tabPM Work Order.due_date_from'`** (web FE gửi ĐÚNG 2 khoá này @`frontend/src/views/pm/PMWorkOrderListView.vue:72-73` ⇒ **bộ lọc khoảng ngày màn PM đang 500 THẬT**) · đối chứng chống vacuous: `imm09` với `{"sla_breached":"1","is_repeat_failure":"1"}` → **OK** · **`imm11.list_calibrations` CÙNG lớp lỗi** → 1054 `'tabIMM Asset Calibration…'` (**NGOÀI phạm vi** — backlog §14.10). **Cơ chế:** `utils/api_handler.py:44-49` CỐ Ý không bắt Exception chung ⇒ `OperationalError` bubble → **HTTP-500 KHÔNG có `body.success`** + lộ tên bảng/cột. **Ràng buộc OAS (verify 2026-07-27):** `WorkOrderFilters` `:235-245` đang $ref bởi **3 op** — `listPmWorkOrders` `:16991` · `listRepairWorkOrders` `:17047` · `listCalibrations` `:17103`. **Counters base ĐỌC LẠI 2026-07-27** (khác đề mục vì AC-CR-78 land giữa spec↔exec — blocker #12): `_EXPECTED_TEST_COUNT` **959** · `_GUARD_SUITE_SUM` **1102** · `_MOBILE_OAS_TOTAL` **1128**; delta dự kiến **+8** (`cr79_a..h`). **🔴 CẢI CHÍNH CR-70 (AC8 — sổ mobile nói SAI):** `CONTRACT-REQUESTS.md:3073` viết *"key sai **không báo lỗi** — BE **bỏ qua im lặng** ⟹ client gửi `{"asset_ref": "..."}` sẽ nhận danh sách KHÔNG lọc"*. **SAI 2 điểm:** (1) BE **KHÔNG bỏ qua im lặng — BE CRASH HTTP-500** (bằng chứng trên) ⇒ rủi ro **nặng hơn** CR-70 mô tả; (2) ví dụ chọn nhầm khoá — **`asset_ref` là khoá HỢP LỆ và ĐƯỢC honor** trên cả 2 endpoint (còn là khoá `apply_vendor_scope` bơm @`services/shared/scope.py:114-115`). CR-70 suy diễn từ hành vi `imm04`/`CommissioningFilters` (nơi khoá lạ **thật sự** bị lọc im lặng) rồi khái quát sang imm08/imm09 — **suy đoán, không phải quan sát**. Trạng thái đề nghị cho sổ mobile: **RESOLVED-BE + CẢI CHÍNH**. ⚠️ **KHÔNG tự sửa** `/home/miyano/assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` (repo KHÁC — chỉ ghi đề nghị sync, cần user cho phép) |
| **AC-CR-78** | **IMM-09** | **`getRepairWorkOrder` += `spare_parts_used[]` typed + trạng thái phiếu xuất kho THẬT** — **+1** schema `RepairSparePartUsedItem` (`additionalProperties:true`, mirror `RepairChecklistItem`) + **2** property trên `RepairWorkOrderDetail` (`spare_parts_used`, `parts_pending_stock_entry`). Mỗi dòng = **9 khoá domain** (1:1 `spare_parts_used.json`) + **ĐÚNG 2** khoá phái sinh `stock_entry_status` ∈ {OK,MISSING,NOT_FOUND} · `stock_entry_ok` **int 0\|1**. `paths` GIỮ **107**, `schemas` **280 → 281**. Đóng **`CR-71`** sổ mobile (hết "gõ mã mò") + **badge XANH GIẢ** cho ref treo trên web | 🟢 **BE+OAS LANDED 2026-07-27 (Bước-4)** — `test_imm09` **229 OK** (+8 TC `TestRepairSparePartsStockEntryStatus` TC-CM-PARTS-01..08) · `test_mobile_oas` **959 OK** (+8 `cr78_a..h`) · `test_mobile_docset` **9 OK**; cite-parity **mutation-verified** (rot cite ⇒ ĐỎ). **BLOCKED-RELOAD** gunicorn `--preload` ⇒ chưa reflect trên HTTP live (chấm bằng `run-tests`, KHÔNG curl). Còn **FE Bước-4** (A8 — 3 trạng thái bằng chữ + dải cảnh báo, test RENDER). ⚠️ **Slice contract KHÔNG đóng ở Bước-2** (mirror AC-CR-77 — §13.10): cite phải trỏ dòng THẬT của symbol chưa tồn tại ⇒ BE land `.py` TRƯỚC | **Spec:** **§13 (cuối file này)** · code-shape + ADR-IMM09-PARTS-01/02/03 [`04 §3.8`](../imm-09/04_Backend_Design.md) · FE [`06 §SparePartsStockEntry`](../imm-09/06_Frontend_Design.md) · TC [`07 §IX`](../imm-09/07_Testing_QA.md). **Grounding (verify 2026-07-27):** validator BR-09-02 `services/imm09.py:861-869` (`frappe.db.exists("AC Stock Movement", …)` trong VÒNG LẶP — N+1) · `get_work_order` `:1170-1232` (3 lớp CR-74 `:1181/:1182/:1185`; `data = doc.as_dict()` `:1186`; `_enrich_sla_breach([data])` `:1231`) · child DocType `assetcore/assetcore/doctype/spare_parts_used/spare_parts_used.json` (istable:1, `field_order` **9 field**) · DocType tồn tại `assetcore/assetcore/doctype/ac_stock_movement/` · `as_dict` emit table-key `[]` `frappe/model/base_document.py::as_dict` · FE lỗ hiển thị `frontend/src/views/cm/CMWorkOrderDetailView.vue:376` (`v-if="p.stock_entry_ref"` ⇒ ref treo hiện XANH) · OAS `RepairWorkOrderDetail:9368`, precedent `RepairChecklistItem:9599`. **Guard ĐÃ thêm (tên THẬT sau khi land — khác spec Bước-2, cập theo code):** `test_mobile_oas::TestMobileRepairSparePartsContract` **8 TC** `cr78_a..h` — `cr78_e` **cite-parity AST quét SCHEMA** (`cr74_g` chỉ quét description của OP; blob CỐ Ý chỉ gồm hiện-vật CR-78 vì mô tả cũ `RepairChecklistItem` chứa cite rác `imm09.py:1194 trả`), `cr78_g` **parity enum import THẬT** hằng BE **`_STOCK_ENTRY_STATUS`** (KHÔNG phải `SPARE_STOCK_ENTRY_STATUSES` như spec Bước-2 phác), `cr78_h` op-description nguồn `item_code` ⇒ **7 counter delta +8** ĐÃ sync: `_EXPECTED_TEST_COUNT` **951→959** · `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` **951→959** · `_GUARD_SUITE_SUM` **1094→1102** · `_MOBILE_OAS_TOTAL` **1120→1128** · 2 echo `assertEqual(_EXPECTED_TEST_COUNT, 959)` · `cr78_repair_spare_parts_delta = 8`. **+2 tổng pinned vòng trước cập theo** (`_CR74_SCHEMA_COUNT` 280→**281**, `cr77_e` 280→**281**) — schema-count là TỔNG TOÀN CỤC, KHÔNG phải delta của vòng đó. **Cite ROT do vòng này đã sửa:** `getRepairWorkOrder`.description + `RepairWorkOrderDetail`.description `imm09.py:1170-1232`→**`1240-1324 get_work_order`** · `SearchSparePartItem` `2118-2166`→**`2224-2272`** / `2233-2234`→**`2209-2221`** (guard `cr73a_e`/`cr74_g` bắt được — bằng chứng cite-drift guard hoạt động). **Quan hệ sổ mobile (verify OAS 2026-07-27):** ĐÓNG **`CR-71`**; **VẪN MỞ** → `CR-70` (`WorkOrderFilters` chưa liệt kê key hợp lệ) · `CR-72` (ngữ nghĩa "0 item hợp lệ" — mới đóng GIÁN TIẾP qua CR-73a) · `CR-74m` nửa CM `available_actions[]` trên `RepairWorkOrderDetail` · `CR-75m` (`listUsers.role` vẫn đơn trị). **KHÔNG re-spec 4 CR này như thể AC-CR-78 đã đóng** |
| **AC-CR-77** | **IMM-08** | **`getPmWorkOrder` += `available_actions[]` server-driven 4 CTA** — mảng ĐÚNG 4 phần tử thứ tự CỐ ĐỊNH `[start_work, submit_result, reschedule, report_major_failure]`, phần tử = **`AvailableAction` TÁI DÙNG** (`{key,label,route,enabled,reason}`, `route=""`) ⇒ **0 schema mới**, paths **107** / schemas **280** GIỮ. `enabled = transition_allowed ∩ has_cap ∩ business_gate`. Đóng: **nút chết** `start_work` (advertise ⊋ enforce) · **CTA ma `Cancelled`** (transition có, **endpoint KHÔNG**) · **CTA ẩn** «Hoãn lịch» (enforce ⊋ advertise) | 🟢 **BE+OAS LANDED 2026-07-26** (test_imm08 **182 OK** +14 TC `TestPmAvailableActions` · test_mobile_oas **951 OK** +9 `cr77_a..i` · test_mobile_docset **9 OK**; mutation-verified cap-drift/cite-rot/A6; **BLOCKED-RELOAD** gunicorn) — còn **FE Bước-4** (render 4 CTA từ `available_actions`). ⚠️ **Slice contract KHÔNG đóng ở Bước-2** (khác CR-74/75/76): cite `services/imm08.py:<dòng> _build_pm_available_actions` phải nằm trong `description` **và** trỏ đúng vùng AST ⇒ **BE land `.py` TRƯỚC**, OAS + guard dán **cùng vòng** (atomic) | **Spec:** [`docs/imm-08/05 §13`](../imm-08/05_API_Specification.md) (ADR-IMM08-CTA-01/02/03 + bảng chân trị 9×4 + INV-PMCTA-1..10) · code-shape [`docs/imm-08/04 §4.3`](../imm-08/04_Backend_Design.md) · FE [`06 §3.4.a`](../imm-08/06_Frontend_Design.md) · TC [`07 §IX`](../imm-08/07_Testing_QA.md). **Grounding (verify 2026-07-26):** `_PM_VALID_TRANSITIONS` `services/imm08.py:127` · `RESCHEDULE_CTA_STATES` `:153` · `get_work_order` `:817` (`allowed_transitions` emit `:869-871`, GIỮ NGUYÊN — A6) · enforcement `assign_technician` `:1096` (Open/Overdue), `submit_result` `:1152`, `report_major_failure` `:1257` (**0 guard status** — backlog B3), `reschedule` `:1335` (chặn Completed/Cancelled) · validator bảng-kiểm-rỗng `:379-380` `MSG.IMM08_CHECKLIST_EMPTY` · cap `api/imm08.py:114/129/151/158` · FE gate nhân bản `frontend/src/views/pm/PMWorkOrderDetailView.vue:91-107,196` · OAS `PmWorkOrderDetail:9170`, `AvailableAction:8005`, `IncidentDetail.available_actions:9885`. **Guard PHẢI thêm:** `test_mobile_oas::TestMobilePmAvailableActionsParity` **9 TC** `cr77_a..i` (gồm `cr77_h` cite-parity AST — ⚠️ `cr74_g` **chỉ quét description của OP**, KHÔNG quét schema ⇒ bắt buộc TC riêng; `cr77_i` parity 4 key OAS ↔ `_PM_ACTION_SPECS`) ⇒ 4 counter **+9** (đọc tại chỗ; giá trị lúc chốt spec: `_EXPECTED_TEST_COUNT` **942**, `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` **942**, `_GUARD_SUITE_SUM` **1085**, `_MOBILE_OAS_TOTAL` **1111**) + delta-name `cr77_pm_available_actions_delta = 9`. **Quan hệ sổ mobile:** đóng **nửa PM** của `CR-74m` (`CONTRACT-REQUESTS.md`); **nửa CM `RepairWorkOrderDetail` VẪN MỞ** → `AC-CR-78` (khảo sát `api/imm09.py` trước, KHÔNG copy mù) |
| **CR-74** | **IMM-08/09/11/12** | **Cụm C6-DETAIL — 4 GET-detail đi qua CÙNG 1 predicate quyền-đọc** (`getPmWorkOrder` · `getRepairWorkOrder` · `getCalibration` · `getIncident`): 3 lớp **ROLE → EXISTS → ROW** (`assert_doctype_read_permission` → `Repo.get` → `assert_can_read_doc` = `frappe.has_permission(doc=…)`), 403 trả **TRONG envelope** trên HTTP-200. Đóng read-vs-write divergence P0 của `Asset Repair`. **0 path / 0 opId / 0 param / 0 schema / 0 field / 0 DocPerm / 0 cap** — chỉ đổi **mô tả 403** trong OAS | ✅ **RESOLVED-BE 2026-07-25 (Bước-4)** — helper SSoT + khuôn 3 lớp ×4 service + guard tĩnh **G5a/G5b** + 8 TC hành vi LANDED (suite XANH, mutation-verified); 🟡 **FE = [FE] song song** (B13: render 403 in-envelope, **KHÔNG logout**, KHÔNG màn trắng) | **Quyết định:** [ADR-IMM00-LIST-SCOPE §9](../imm-00/ADR-IMM00-LIST-SCOPE.md) — ADR-IMM00-DETAIL-READ-01 (D8 một predicate) / -02 (D9 thứ tự chống existence-oracle) / -03 (D10 áp cả IMM-11 dù `Calibration Record` chưa có hook). **Root cause @source (verify 2026-07-25):** `frappe.get_doc` KHÔNG check quyền (`frappe/model/document.py:36`; check ở `Document.check_permission:227`) ⇒ `BaseRepository.get` (`repositories/base.py:53-57`) đọc trần; hook ĐÃ đăng ký `hooks.py:448-455` nhưng **chỉ chạy qua** `frappe.has_permission(doc=…)` (`frappe/permissions.py:196` → `has_controller_permissions:442-460`). **4 điểm sửa — verify TẠI CHỖ 2026-07-25 SAU khi sửa:** `services/imm08.py::get_work_order` @`:816-904` (`@rowscoped` :816 · L0 :829 · L1 :830 · L2 :833) · `services/imm09.py::get_work_order` @`:1169-1232` (`@rowscoped` :1169 · L0 :1181 · L1 :1182 · L2 :1185) · `services/imm11.py::get_calibration` @`:1078-1111` (`@rowscoped` :1078 · L0 :1092 · L1 :1093 · L2 :1096) · `services/imm12.py::get_incident_detail` @`:1406-1491` (`@rowscoped` :1406 · L0 :1435 · L1 :1436 · L2 :1437 — L0 đặt TRONG hàm này, KHÔNG trong helper `_get_incident:329`); helper SSoT MỚI `services/shared/permissions.py::assert_can_read_doc` @`:87-132` (cạnh `assert_doctype_read_permission:41`). **⚠️ CẢI CHÍNH tên DocType IMM-11:** DocType THẬT là **`IMM Asset Calibration`** (`repositories/calibration_repo.py:12`, folder `doctype/imm_asset_calibration/`) — `"Calibration Record"` KHÔNG tồn tại, nó chỉ là **khoá alias vendor-scope** trong `_VENDOR_SCOPE_FIELD_MAP` (`services/shared/scope.py:117`); OAS đã sửa theo. **API tier KHÔNG đổi** — `assert_vendor_can_access` (`services/shared/scope.py:182-217`) GIỮ NGUYÊN (A5). **OAS:** mô tả 403 của 4 op cải chính ("thiếu DocPerm → dispatcher-403 status-line" là **SAI sau CR-74**) — `paths` GIỮ **105**, `components.schemas` **+0**, slot `{200,401,403}` KHÔNG đổi. **Guard hợp đồng:** `test_mobile_oas.py::TestMobileDetailReadGate` **7 TC** `cr74_a..g` (`cr74_g` = **parity cite BE↔OAS**: mọi cite `services/<mod>.py:<dòng> <symbol>` PHẢI nằm TRONG vùng AST của symbol — mutation-verified bằng cách rot 1 cite ⇒ ĐỎ) ⇒ counters `_EXPECTED_TEST_COUNT` 917→923→**924**, `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` →**924**, `_GUARD_SUITE_SUM` 1060→1066→**1067**, `_MOBILE_OAS_TOTAL` 1086→1092→**1093**, `cr74_detail_readgate_delta` 6→**7**. **OAS cite refresh (chống cite-rot):** `imm08.py:572-621`→**`817-904`** · `imm09.py:700-730`→**`1170-1232`** · `imm12.py:773-789`→**`1407-1491`** · `imm11.py:978-989`→**`1079-1111`** (mỗi cite 3 chỗ). **Test BE LANDED:** `test_rowscope_docperm_gate.py::TestDetailReadGateCR74` **8 TC** (01a..01d 4 op × 0-DocPerm ⇒ 403 + 0 khoá nghiệp vụ · 05a no-existence-oracle · 05b 404 GIỮ NGUYÊN · 06 vendor 2 lớp cùng tồn tại · 07 no-500) · `test_rowscope_invariant.py::TestDetailReadGateCR74Invariant` **8 TC** (02a..02c row-deny · 03a..03d 0-regress key-set · **04 bảng chân trị 2×2 = 4/4 trùng**) · guard tĩnh `test_rowscope_scope_guard.py::TestRowScopeStaticGuard` **G5a** `test_detail_reads_are_gated` + **G5b** `test_cr74_named_detail_ops_have_both_gates` (backlog chỉ-giảm `_DETAIL_READ_UNGATED_BACKLOG` = 2 dòng imm04 — B10). **Mutation-verified:** gỡ `assert_can_read_doc` ở imm09 ⇒ G5b ĐỎ; gỡ tiếp `assert_doctype_read_permission` ⇒ G5a+G5b ĐỎ; hoàn nguyên ⇒ XANH. **Suite:** `test_imm08` 168 · `test_imm09` 221 · `test_imm11` 120 · `test_imm12` 184 · `docperm_gate` 17 · `scope_guard` 9 · `rowscope_invariant` 21 · `mobile_oas` 924 · `mobile_docset` 9 — tất cả **OK** |
| **CR-73(a)** | **IMM-09** | **KHOÁ NHẬN DẠNG cho gợi ý phụ tùng CM** — `SearchSparePartItem` **10 → 13** property (`device_model`, `device_model_name`, `spare_part`), `required` đủ 13, `additionalProperties:false` GIỮ. Thuần ADDITIVE trên khoá (10 khoá cũ giữ nguyên tên + giá trị) | ✅ **RESOLVED-BE 2026-07-25 (Bước-4)** — service + gate + OAS + guard LANDED; 🟡 **FE `.ts` + `CMCreateView.vue` = [FE] song song** (bỏ `as unknown as` cast bịa `{name, part_name}`, hiển thị `device_model_name`) | **BE (verify tại chỗ 2026-07-25 sau khi sửa):** `services/imm09.py::search_spare_parts` @`:2169-2240` — `@rowscoped` @`:2169` + `assert_doctype_read_permission('IMM Device Model')` @`:2196` · SQL bỏ `DISTINCT` + `sp.parent AS device_model` + `parenttype='IMM Device Model'` + `ORDER BY part_name, parent` @`:2204-2211` · row literal **13 khoá** @`:2224-2237` (10 khoá cũ @`:2224-2230` BẤT BIẾN) · batch-enrich `_batch_device_model_names` @`:2103-2116` (P1) + `_batch_resolve_spare_parts` @`:2118-2166` (P2+P3, `setdefault` trên `order_by name asc`, bỏ hẳn P3 khi tập fallback rỗng) ⇒ **≤3 truy vấn phụ, hằng theo số dòng**. **Gate-2 hết câm:** `request_spare_parts` @`:1628` nay gọi `imm15.create_allocation_for_work_order` @`services/imm15.py:265-289` (**ADR-IMM09-SPARE-03 THỰC THI**: `_insert_allocation` @`:291` không gate; `create_allocation` @`:250` GIỮ NGUYÊN gate `inventory.write` ⇒ 0 đổi hành vi công khai). **OAS:** `SearchSparePartItem` 13 property + `required` 13 @`docs/mobile/openapi/assetcore-mobile.openapi.yaml:1920-2006`; paths GIỮ **105**, `components.schemas` **+0**. **Guard:** `test_mobile_oas.py::TestMobileSearchSparePartItemIdentity` 6 TC `cr73a_a..f` (gồm **parity AST BE↔OAS** + **chống cite-rot**) ⇒ counters `_EXPECTED_TEST_COUNT` 911→**917**, `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 911→**917**, `_GUARD_SUITE_SUM` 1054→**1060**, `_MOBILE_OAS_TOTAL` 1080→**1086**. **Test BE:** `test_imm09.py::TestSearchSparePartsIdentity` (9 TC, TC-CM-SPARE-01..07) + `TestRequestSparePartsAllocation` (3 TC ALLOC-01/02/03 — **ALLOC-02 chạy bằng persona KTV thật**) + `test_rowscope_docperm_gate.py::TestSearchSparePartsRoleGate` (2 TC cặp 08a/08b). **⚠️ Cite cũ (`:1223-1248`, `:1237-1246`) ĐÃ REFRESH.** **CÒN MỞ:** CR-73 **nhóm-2** (tồn kho `available_qty`/`warehouse` trên dòng gợi ý) — nay KHẢ THI vì đã có `spare_part`; K1 `uom` hằng · K2 escape LIKE · K3 `"search_"` vào `_ENTRYPOINT_PREFIXES` · K5 warehouse-first-item · K6 `work_order_doctype` mis-link |
| **CR-69** | **IMM-08/09/12** | Hợp đồng TRUNG THỰC khi cắt cho **cụm 3 endpoint device-profile history** — `data` của `AssetPmHistoryEnvelope` / `AssetRepairHistoryEnvelope` / `AssetIncidentHistoryEnvelope` khai thêm `total` (integer) + `truncated` (integer `enum [0,1]`), ADDITIVE 0-breaking | ✅ **CLOSED — contract-layer (OAS + guard)** · ✅ **BE Bước-4 LANDED 2026-07-25** (3 service) · 🟡 **FE `.ts` Bước-4** (song song, xem cột kế) | **OAS (verify 2026-07-25, 3 điểm):** `AssetPmHistoryEnvelope.data.total` @`docs/mobile/openapi/assetcore-mobile.openapi.yaml:1733` + `.truncated` @`:1743` (envelope :1696) · `AssetRepairHistoryEnvelope.data.total` @`:1619` + `.truncated` @`:1629` (envelope :1582) · `AssetIncidentHistoryEnvelope.data.total` @`:1510` + `.truncated` @`:1519` (envelope :1476). `required` cả 3 GIỮ NGUYÊN (`[asset_ref,history]`×2 / `[asset,items]`), `additionalProperties:false` GIỮ, **paths GIỮ 105** (0 path/opId/param mới). **Guard:** `assetcore/tests/guards/test_mobile_oas.py::TestMobileHistoryTruncationContract` 6 TC `cr69_a..f` — suite **911 OK**; counters `_EXPECTED_TEST_COUNT` 905→**911** @`test_mobile_oas.py:212`, `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` @`test_mobile_docset.py:781`, `_GUARD_SUITE_SUM` 1048→**1054** @`:949`, `_MOBILE_OAS_TOTAL` 1074→**1080** @`:1138`, delta `cr69_history_truncation_delta = 6` — `test_mobile_docset` **9 OK**. **BE (verify 2026-07-25, 3 service — ĐÃ implement):** `services/imm08.py::get_asset_history` @`:1530-1551` (`logs, pg = PMTaskLogRepo.list` + `truncation_meta` @`:1548`) · `services/imm09.py::get_asset_history` @`:2056-2080` (import SSoT @`:32`, `scope="system"` + `docstatus:1` GIỮ NGUYÊN, `truncation_meta` @`:2077`) · `services/imm12.py::get_asset_incident_history` @`:1523-1551` (import SSoT @`:35`, clamp `clamp_page_size(limit, 10)` @`:1532`, `truncation_meta` @`:1548` với `count_fn` dùng CÙNG object `incident_filters` như rows). SSoT `services/shared/truncation.py::truncation_meta` @`:15-43`; helper clamp MỚI `utils/pagination.py::clamp_page_size` @`:14-34` (`paginate` @`:37` gọi lại helper ⇒ literal 100 vẫn 1 nơi). **API tier KHÔNG đổi chữ ký** (`api/imm08.py:199` · `api/imm09.py:196` · `api/imm12.py:236`) ⇒ 0 path/opId/param mới, `oas_baseline` GIỮ 105. **Guard BE (cập nhật 2026-07-25 vòng sửa lỗi):** `test_imm08.py::TestAssetPmHistoryTruncation` (**6 TC** — +hist_07 parity `limit=0`) · `test_imm09.py::TestAssetRepairHistoryTruncation` (**6 TC** — +hist_05 parity `limit=0`, +hist_06 clamp `limit=500` trên fixture 101) · `test_imm12.py::TestAssetIncidentHistoryTruncation` (**9 TC** — hist_07 seed 12→**101** vì TC cũ VACUOUS, +hist_08 nửa-cắt của INV-INCH-5); `test_mobile_oas` **911 OK** / `test_mobile_docset` **9 OK** (KHÔNG đổi counter — contract-layer đã land vòng trước). **CÒN LẠI:** FE `.ts` (imm08/imm09/imm12) khai `total?`/`truncated?` — Bước-4 [FE]. **🔁 DELTA 2026-07-25 (sửa lỗi sau QA CR-69):** (1) **P1 bảo mật** — `imm12.get_asset_incident_history` là thành viên DUY NHẤT của bộ-ba KHÔNG gate quyền (`frappe.get_all` raw ⇒ persona 0-DocPerm-read đọc được sự cố + `frappe.db.count` của CR-69 còn lộ TỔNG SỐ thật): đã thêm `assert_doctype_read_permission('Incident Report')` + `@rowscoped` (xem `docs/imm-12/05 §20.1` + ADR-IMM00-LIST-SCOPE §8.4 hàng I1); (2) **parity `limit=0` sửa THẬT** — imm08/imm09 nay clamp `clamp_page_size(limit, 10)` (trước đó rơi về 20 của `paginate` ⇒ doc hứa parity mà code lệch); (3) **guard tĩnh G4 MỚI** `tests/test_rowscope_scope_guard.py` chặn endpoint đọc raw-query DocType row-scoped không gate + `tests/test_rowscope_docperm_gate.py` +3 TC hành vi. ADR gốc [ADR-IMM00-TRUNCATION-SSOT](../imm-00/ADR-IMM00-TRUNCATION-SSOT.md) |
| **CR-65** | **IMM-09** | `RepairWorkOrderDetail.repair_checklist[]` typed + component schema mới `RepairChecklistItem` (nối chuỗi typed ĐỌC→ĐÍNH-ẢNH qua khoá `idx`) | ✅ **CLOSED** (vòng này) | OAS `repair_checklist` @`docs/mobile/openapi/assetcore-mobile.openapi.yaml:9452` (trong `RepairWorkOrderDetail` :9244) + schema `RepairChecklistItem` @`:9475` (trước `RepairWorkOrderDetailEnvelope` :9558); grounded `repair_checklist.json` (7 field) + `services/imm09.py:1307` (as_dict) / `:1183-1191` (join idx) / `:80-94` (seed `result=""`) / `:173` (`MAX_REPAIR_CHECKLIST_PHOTOS = 1`); guard `assetcore/tests/guards/test_mobile_oas.py::TestMobileRepairChecklistItemTyped` 7 TC — suite **905 OK** |
| CR-63 | IMM-12 | `ReportIncidentRequest.clinical_impact` (BR-12-01 / NĐ98 Điều 67) | ✅ CLOSED **từ trước** — không re-spec | property `clinical_impact` @`docs/mobile/openapi/assetcore-mobile.openapi.yaml:5020`; enforce server-side (chỉ `severity=Critical` bắt buộc) @`services/imm12.py:559`; param có trong chữ ký @`api/imm12.py:95` |
| CR-64 | IMM-00 | `list_assets` phát `category_name` **cùng khoá** với detail + OAS `AssetListItem` (`additionalProperties:false`) | ✅ CLOSED **từ trước** — không re-spec | `_enrich(items, "asset_category", …, out_field="category_name")` @`assetcore/api/imm00.py:473` (chú thích CR-64 @`:469`) |
| **INV-ROWSCOPE** | IMM-00/08/09 | Row-scope list invariant (`BaseRepository.list(scope=…)`, rows permission-aware KHỚP `count_with_or`) | 🟡 **SPEC chốt 2026-07-25 — BE/FE Bước-4** · ⚠️ **KHÔNG phải contract-CR: 0 delta OAS mobile** (shape/param/schema KHÔNG đổi, chỉ đổi TẬP row trả về theo persona) ⇒ **KHÔNG re-spec như CR OAS** | Spec: BR-09-LISTSCOPE (§3.1) + [ADR-IMM00-LIST-SCOPE §8](../imm-00/ADR-IMM00-LIST-SCOPE.md); bug @`repositories/base.py:67-75` (`frappe.get_all`) vs @`services/shared/filters.py:275-281` (`frappe.get_list`); predicate @`permissions.py:113-121` |

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

**Quy tắc khoá `fields` (field-level) — bổ sung AC-CR-84 · ADR-IMM09-EVIDENCE-05:**
mặc định khoá `fields` dùng **TÊN THAM SỐ GHI** của endpoint (`ADR-IMM12-14`) để FE neo
thông điệp dưới đúng control. **Ngoại lệ có quy tắc:** khi hành động khắc phục **không**
nằm trên tham số ghi nào của endpoint đang gọi mà ở **endpoint khác** tác động lên dữ
liệu client render từ một **khoá ĐỌC**, thì dùng **tên khoá đọc đó**. Ví dụ chuẩn:
`IMM09-EVIDENCE-PHOTO-REQUIRED` trả `fields.repair_checklist` (khoá đọc) chứ không
`fields.checklist_results` (tham số ghi) — vì nút đính ảnh nằm ở **bảng checklist**, còn
`checklist_results` là ô nhập **kết quả**.

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
> `python scripts/gen_fe_messages.py` để regen `frontend/src/locales/messages.ts`.

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

## §12 CR-74 — Read-gate CHI TIẾT phiếu sửa chữa (CM) (`getRepairWorkOrder`) — in-handler 403, ĐÓNG IDOR-đọc

> **SSoT quyết định:** [ADR-IMM00-LIST-SCOPE §9 — INV-ROWSCOPE-DETAIL (CR-74)](../imm-00/ADR-IMM00-LIST-SCOPE.md) · ADR-IMM00-DETAIL-READ-01/02/03 (D8/D9/D10).
> **Trạng thái:** ✅ **RESOLVED-BE 2026-07-25 (Bước-4)** — khuôn 3 lớp đã LANDED @`services/imm09.py:1344-1407` (`@rowscoped` :1169 · L0 :1181 · L1 :1182 · L2 :1185), helper SSoT `services/shared/permissions.py::assert_can_read_doc` @`:87-132`. **0 delta shape** (0 endpoint / 0 param / 0 field / 0 DocType / 0 DocPerm / 0 cap). Test: `test_rowscope_docperm_gate::TestDetailReadGateCR74` (8 TC) + `test_rowscope_invariant::TestDetailReadGateCR74Invariant` (8 TC, gồm bảng chân trị 2×2) + guard tĩnh G5a/G5b — `test_imm09` **221 OK**. 🟡 Còn lại: **[FE] B13** (render 403 in-envelope, KHÔNG logout).

### §12.1 Vấn đề (verify @source 2026-07-25)

`services/imm09.py:1343` `get_work_order` nạp bản ghi bằng `RepairRepo.get(name)` → `frappe.get_doc` (`repositories/base.py:53-57`). **`frappe.get_doc` KHÔNG kiểm tra quyền** (`frappe/model/document.py:36`; kiểm tra nằm ở `Document.check_permission:227` — không đường nào chạm tới). Gate duy nhất đang có là `assert_vendor_can_access` ở API tier (`api/imm09.py:50-54`), mà hàm này **no-op cho mọi user KHÔNG mang role `Vendor Engineer`** (`services/shared/scope.py:192-193`).

⟹ Hệ quả: (a) persona **0 DocPerm read** trên `Asset Repair` vẫn đọc trọn hồ sơ qua URL trực tiếp; (b) KTV **có** DocPerm read vẫn mở được phiếu của đồng nghiệp — **đúng phiếu mà `list_work_orders` đã ẩn** (`services/imm09.py:1320-1331` `scope="user"`, D4) và **đúng phiếu mà `attach_repair_checklist_photo` từ chối** (`_assert_can_attach_repair_photo` `services/imm09.py:1419-1429`). Đây là **P0 read-vs-write divergence** ghi trong STATE.

### §12.2 Hợp đồng SAU CR-74 — 3 lớp theo thứ tự BẮT BUỘC (D9)

| Lớp | Gọi gì | Khi hỏng | Vì sao thứ tự này |
|---|---|---|---|
| **L0 · ROLE** | `assert_doctype_read_permission("Asset Repair")` | `frappe.PermissionError` → `@rowscoped` → **HTTP-200** + `Error{success:false, code:"FORBIDDEN", http_status:403}` | Chạy **TRƯỚC** `exists` ⇒ thiếu quyền thì `name` bịa và `name` thật trả **cùng một** 403 ⇒ 0 existence-oracle (tiền lệ `api/imm00.py:483-509`) |
| **L1 · EXISTS** | `RepairRepo.get(name)` → không có ⇒ `nthrow(`MSG.IMM09_NOT_FOUND`)` | **HTTP-200** + `Error{code:"NOT_FOUND", http_status:404}` — **GIỮ NGUYÊN** | Chỉ người **CÓ** DocPerm read mới tới được đây ⇒ 404 không còn là kênh dò |
| **L2 · ROW** | `assert_can_read_doc("Asset Repair", doc)` → `frappe.has_permission("Asset Repair", ptype="read", doc=doc)` | như L0 (**403 in-envelope**) | Dispatch hook `hooks.py:451` (`asset_repair_has_permission` `permissions.py:222-232` — KTV/NCC chỉ đọc phiếu `assigned_to == mình`; senior/auditor `True`) — dùng **doc đã load ở L1** ⇒ **0 query thêm** |

**Bất biến giữ nguyên (A5 — KHÔNG gỡ, KHÔNG thay):** `assert_vendor_can_access("Asset Repair", name)` ở API tier **giữ nguyên vị trí + thứ tự**. Hai lớp cùng tồn tại: isolation NCC (API) ∧ read-gate (service). Vendor ngoài scope vẫn **403 in-envelope**, KHÔNG rơi nhánh 500.

### §12.3 Ma trận persona (KHÔNG đổi DocPerm — chỉ mô tả hệ quả)

| Persona | DocPerm read `Asset Repair` | Phiếu `assigned_to` | Kết quả sau CR-74 |
|---|---|---|---|
| `AssetCore Super Admin` / `Repair Manager` (senior `permissions.py:34-51`) | ✔ | bất kỳ | **200 success** — payload **byte-identical** trước/sau |
| `AssetCore Auditor` | ✔ (read-only) | bất kỳ | **200 success** |
| `Repair User` (`_TECHNICIAN_ROLES` `permissions.py:50`) | ✔ | **của mình** | **200 success** |
| `Repair User` | ✔ | **của người khác** | **403 in-envelope** — **trùng khớp** kết luận của `list` (ẩn) và `attach` (403) ⇒ đóng bảng chân trị INV-DETAIL-3 |
| Persona thiếu DocPerm read (vd `Calibration User`, `Corrective User`, `PM User`, `Vendor Engineer` — bảng ADR §8.5) | ✘ | bất kỳ | **403 in-envelope** (trước CR-74: đọc được trọn hồ sơ) |
| `Vendor Engineer` ngoài scope | (xem B2) | bất kỳ | **403** — lớp API tier, GIỮ NGUYÊN |

> ⚠️ **KHÔNG được "chữa" bằng cách cấp DocPerm/role.** Persona nào **cần** đọc thì mở riêng bằng ratify B2 (ADR §9.9), KHÔNG sửa trong vòng CR-74.

### §12.4 Envelope 403 — hợp đồng client (BR-00-DETAIL-403)

```json
{ "success": false, "error": "Không đủ quyền", "code": "FORBIDDEN", "http_status": 403 }
```

- **HTTP status-line = 200**; client route **theo GIÁ TRỊ** `body.success` / `body.http_status` — **KHÔNG** theo status-line.
- Client **PHẢI hiển thị message** và **KHÔNG logout** (phân biệt dispatcher-403 = hết phiên → re-auth).
- Body **KHÔNG** được chứa bất kỳ field nghiệp vụ nào (`asset_ref` · `repair_summary` · `mttr_hours` · `root_cause_category` · `asset_info{}`) — chỉ khoá của `Error` envelope.
- Message hằng `MSG.AUTH_FORBIDDEN` (`utils/messages.py:61` = `"AUTH-403"`) — **KHÔNG** mã lỗi mới.

### §12.5 Test bắt buộc (DoD — `bench --site miyano run-tests --module ...`, KHÔNG curl)

| TC | Điều kiện | Kỳ vọng | INV |
|---|---|---|---|
| `TC-CM-DETAILGATE-01` | user đăng nhập, **0 DocPerm read** `Asset Repair` | `success:false` · `code:"FORBIDDEN"` · `http_status:403` trên **HTTP-200**; 0 field nghiệp vụ | INV-DETAIL-1 |
| `TC-CM-DETAILGATE-02` | `Repair User` có DocPerm read, phiếu `assigned_to` **của người khác** | **403 in-envelope**, **và** cùng persona/phiếu đó: `list` KHÔNG chứa + `attach_repair_checklist_photo` 403 (**bảng chân trị 2×2 = 4/4 trùng**) | INV-DETAIL-2 |
| `TC-CM-DETAILGATE-03` | senior/auditor có DocPerm read | **200**, payload **byte-identical** baseline | INV-DETAIL-4 |
| `TC-CM-DETAILGATE-04` | 0 DocPerm read + `name` **KHÔNG tồn tại** | **403 y hệt** TC-01 (0 existence-oracle) | INV-DETAIL-5 |
| `TC-CM-DETAILGATE-05` | **có** DocPerm read + `name` **KHÔNG tồn tại** | **404 GIỮ NGUYÊN** (`MSG.IMM09_NOT_FOUND`) | INV-DETAIL-6 |
| `TC-CM-DETAILGATE-06` | vendor ngoài scope | **403** từ API tier, KHÔNG 500 ⇒ 2 lớp cùng tồn tại | INV-DETAIL-7 |

> **BẮT BUỘC `frappe.set_user(<persona thật>)`** — `frappe/permissions.py:107-109` cho Administrator `return True` ngay ⇒ chạy bằng Administrator là **xanh giả**.

### §12.6 Boundaries

**Always** — gate ROLE trước `exists`; gate ROW trên doc đã load; lỗi quyền = HTTP-200 + Error envelope; test bằng persona thật.
**Ask-first** — cấp DocPerm read cho persona đang bị chặn (B2); nới `get_asset_history` (R5) sang row-scope.
**Never** — ❌ sửa `permissions.py` / DocPerm / role JSON để test xanh · ❌ gỡ `assert_vendor_can_access` · ❌ trả `data` rỗng hay 404 thay 403 · ❌ dùng `doc.check_permission()` (msgprint rò `_server_messages`) · ❌ thêm path/opId/param/schema OAS · ❌ đổi shape payload success · ❌ `git commit/push` · `bench migrate` · reload gunicorn (HARD-STOP USER).

---

## §13 AC-CR-78 — `getRepairWorkOrder` phơi `spare_parts_used[]` typed + trạng thái phiếu xuất kho THẬT

> **Trạng thái:** 🔴 **SPEC CHỐT 2026-07-27 (BA — Bước-2)** · BE **Bước-4** · FE **Bước-4 CÙNG VÒNG (A8)**.
> **Đóng:** `CR-71` sổ mobile (`RepairWorkOrderDetail.spare_parts_used[]` KHÔNG có ⇒ "gõ mã mò") **và**
> lỗ hiển thị web P3 (ref treo hiện **XANH như hợp lệ**).
> **SSoT code-shape + ADR:** [`04_Backend_Design.md §3.8`](./04_Backend_Design.md) (ADR-IMM09-PARTS-01/02/03).
> **Lý do tồn tại của vòng:** **PARITY display ⇔ enforcement** (INV-PARTS-1) — badge là *tấm gương* của
> validator BR-09-02, không phải bản diễn giải thứ hai (class-of-bug đã cắn CR-54 G05, CR-76 G01/G03).

### §13.1 Delta hợp đồng (ADDITIVE tuyệt đối)

| Trục | Trước | Sau | Ghi chú |
|---|---|---|---|
| `paths` | **107** | **107** | 0 path mới, 0 opId mới, 0 param mới |
| `components.schemas` | **280** | **281** | **+1**: `RepairSparePartUsedItem` |
| `RepairWorkOrderDetail.properties` | — | **+2** | `spare_parts_used`, `parts_pending_stock_entry` |
| `required` của `RepairWorkOrderDetail` | `[name]` | `[name]` | **KHÔNG đổi** (mirror `repair_checklist` — emit-luôn nhưng ∉ required, client cũ bỏ qua an toàn) |
| DocType / DocPerm / capability / workflow | — | **0 đổi** | Không migration, không patch |

### §13.2 `RepairSparePartUsedItem` — 1 dòng phụ tùng đã dùng

`additionalProperties: **true**` — **mirror precedent `RepairChecklistItem`**: dòng đến NGUYÊN VẸN qua
`Asset Repair doc.as_dict()` nên còn mang field meta Frappe (`parent`/`parenttype`/`parentfield`/
`doctype`/`owner`/`creation`/`modified`/`modified_by`/`docstatus`) — đóng schema sẽ làm validator
reject payload THẬT.

**9 khoá domain — GROUNDED 1:1 `assetcore/assetcore/doctype/spare_parts_used/spare_parts_used.json`
(`field_order`, istable:1). Giữ NGUYÊN tên + giá trị, KHÔNG đổi, KHÔNG bịa field ngoài DocType:**

| # | Khoá | Kiểu OAS | Nguồn (fieldtype) | Ghi chú |
|---|---|---|---|---|
| 1 | `item_code` | `string` | Data, reqd:1 | Mã vật tư nội bộ (v3 soft-ref, KHÔNG link ERPNext Item) |
| 2 | `item_name` | `string` | Data, reqd:1 | Tên vật tư (hiển thị) |
| 3 | `manufacturer_part_no` | `string` nullable | Data | Mã phụ tùng hãng SX |
| 4 | `qty` | `number` | Float, reqd:1 | Số lượng (**Float ⇒ number**, KHÔNG integer) |
| 5 | `uom` | `string` nullable | Link `AC UOM`, default "Cái" | Đơn vị tính |
| 6 | `unit_cost` | `number` | Currency, reqd:1 | Đơn giá |
| 7 | `total_cost` | `number` nullable | Currency, read_only:1 | Thành tiền (BE tính) |
| 8 | `stock_entry_ref` | `string` nullable | Data | **Mã `AC Stock Movement`** (v3 soft-ref — KHÔNG phải ERPNext `Stock Entry`). `""` ⇒ chưa có phiếu |
| 9 | `notes` | `string` nullable | Text | Ghi chú |

**2 khoá meta Frappe khai tường minh (mirror `RepairChecklistItem`):**

| Khoá | Kiểu | Ghi chú |
|---|---|---|
| `name` | `string` | PK dòng child (hash name). Dùng để dedupe/diff cục bộ |
| `idx` | `integer` | Thứ tự 1-based. **Payload đã sắp tăng dần theo khoá này** (A1) |

**2 khoá PHÁI SINH — ĐÚNG 2, không hơn (AC-CR-78):**

| Khoá | Kiểu | Giá trị | Ngữ nghĩa |
|---|---|---|---|
| `stock_entry_status` | `string`, **enum ĐÚNG 3**: `OK` \| `MISSING` \| `NOT_FOUND` | `MISSING` ⟸ `stock_entry_ref` falsy · `NOT_FOUND` ⟸ có ref nhưng `AC Stock Movement` ∄ · `OK` ⟸ còn lại | Khoá **chẩn đoán** — client hiển thị 3 trạng thái khác nhau bằng chữ tiếng Việt đầy đủ |
| `stock_entry_ok` | `integer`, **enum `[0,1]`** | `1` ⟺ `stock_entry_status == "OK"` | Khoá **quyết định** — đếm/lọc không cần so chuỗi. **KHÔNG boolean** (quirk CR-01: `as_dict` phát Check thành int; ADR-IMM09-PARTS-02) |

> ⚠️ **Cả 2 khoá là DERIVED, KHÔNG lưu DB** ⇒ luôn tươi; `AC Stock Movement` bị xoá sau đó thì lần đọc
> kế **đổi ngay** sang `NOT_FOUND` (đây chính là lý do bác phương án "thêm field `stock_entry_valid`",
> ADR-IMM09-PARTS-01 alt-b).

### §13.3 `RepairWorkOrderDetail` — 2 property mới

| Property | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `spare_parts_used` | `array` items `$ref RepairSparePartUsedItem` | **LUÔN CÓ MẶT**; `[]` khi phiếu chưa có dòng nào (**KHÔNG null**, KHÔNG thiếu khoá); thứ tự **`idx` tăng dần** | Danh sách vật tư đã dùng của phiếu CM |
| `parts_pending_stock_entry` | `integer`, `minimum: 0` | `== len([r for r in spare_parts_used if r.stock_entry_ok == 0])` | Số dòng **chưa** có phiếu xuất kho hợp lệ. `> 0` ⇒ BR-09-02 sẽ chặn submit ⇒ client cảnh báo **TRƯỚC**, thay vì ăn 422 tại `on_submit` |

**Vì sao `spare_parts_used` LUÔN có mặt (không cần `required`):** `frappe/model/base_document.py::as_dict`
duyệt `for fieldname in self._table_fieldnames` và gán `doc[fieldname] = [...]` ⇒ mọi table field đều có
khoá, `[]` khi 0 dòng (INV-PARTS-3, verify @source 2026-07-27).

### §13.4 Ví dụ payload (3 trạng thái trên cùng 1 phiếu)

```jsonc
{
  "success": true,
  "data": {
    "name": "CM-2026-00077",
    "status": "In Repair",
    "allowed_transitions": ["Pending Inspection", "Cannot Repair"],
    "risk_classification": "High",
    "is_sla_breached": false,
    "asset_info": { "asset_name": "Máy thở", "lifecycle_status": "Under Repair" },
    "parts_pending_stock_entry": 2,
    "spare_parts_used": [
      { "idx": 1, "item_code": "VT-001", "item_name": "Cảm biến oxy", "qty": 1.0,
        "uom": "Cái", "unit_cost": 1200000, "total_cost": 1200000,
        "stock_entry_ref": "SM-2026-00042", "notes": "",
        "stock_entry_status": "OK",        "stock_entry_ok": 1 },
      { "idx": 2, "item_code": "VT-002", "item_name": "Bộ lọc HEPA", "qty": 2.0,
        "uom": "Cái", "unit_cost": 350000, "total_cost": 700000,
        "stock_entry_ref": "", "notes": "chờ kho",
        "stock_entry_status": "MISSING",   "stock_entry_ok": 0 },
      { "idx": 3, "item_code": "VT-003", "item_name": "Dây nguồn", "qty": 1.0,
        "uom": "Cái", "unit_cost": 150000, "total_cost": 150000,
        "stock_entry_ref": "SM-2026-99999", "notes": "",
        "stock_entry_status": "NOT_FOUND", "stock_entry_ok": 0 }
    ]
  }
}
```

Phiếu chưa có dòng nào: `"spare_parts_used": []`, `"parts_pending_stock_entry": 0` — **không null**.

### §13.5 Bất biến KHÔNG được đổi (A5 — no-regress)

| Bất biến | Phát biểu |
|---|---|
| **Key-set SIÊU TẬP** | Key-set payload success `get_work_order` sau vòng ⊇ key-set trước vòng. **Chỉ ADDITIVE** — 0 xoá, 0 đổi tên, 0 đổi kiểu |
| **Giá trị giữ nguyên** | `allowed_transitions`, `risk_classification`, `is_sla_breached`, `asset_info{}` giữ **nguyên giá trị** |
| **Thứ tự 3 lớp CR-74** | `assert_doctype_read_permission` → `RepairRepo.get` → `assert_can_read_doc` chạy **TRƯỚC** enrich, thứ tự **KHÔNG đổi** ⇒ persona không đọc được vẫn **403 in-envelope (HTTP-200)**, enrich **không bao giờ** chạy cho họ (INV-PARTS-5) |
| **API tier** | `assert_vendor_can_access("Asset Repair", name)` GIỮ NGUYÊN vị trí + thứ tự |
| **Slot response** | `{200, 401, 403}` KHÔNG đổi; 404 (WO ∄) vẫn đến **trên HTTP-200** trong Error envelope |
| **Enforcement** | BR-09-02 giữ nguyên mã lỗi (`CM-003`/`CM-004`), biên, và **thứ tự raise** (dòng non-OK đầu tiên theo `idx`) |

### §13.6 Cite-parity (A7) — cite nằm trong `description`, KHÔNG trong comment YAML

- Mỗi cite dạng **`services/imm09.py:<dòng> <symbol>`** và **dòng phải nằm trong vùng AST của symbol**.
- **BẮT BUỘC đặt trong `description`** của `RepairSparePartUsedItem` và của 2 property mới —
  **KHÔNG** đặt trong comment YAML (**bài học CR-76**: comment không vào spec đã parse ⇒ rot **không** bắt được).
- Symbol phải cite **(tên ĐÃ LAND — cải chính bản phác Bước-2, xem `04 §3.8.2`)**: `_spare_row_stock_status`
  (predicate SSoT theo dòng) · `validate_spare_parts_stock_entries` (enforcement đối chứng) ·
  `_resolve_known_stock_entries` (batch 1 truy vấn). Enrich nằm **inline trong `get_work_order`** ⇒
  không có symbol `_enrich_spare_parts_used` để cite.
- Guard tái dùng khuôn `cr73a_e` / `cr74_g` / `cr76_h` / `cr77_h` — **mutation-verified**: rot 1 cite ⇒ ĐỎ.
- ⚠️ `cr74_g` **chỉ quét `description` của OPERATION**, không chạm schema ⇒ **bắt buộc** TC riêng — đã land
  là **`cr78_e`** (quét hiện-vật AC-CR-78 trong `components.schemas`, đúng như `cr77_h` đã phải làm).

### §13.7 Guard OAS bắt buộc — `TestMobileRepairSparePartsContract` **8 TC** `cr78_a..h`

> ⚠️ **CẢI CHÍNH sau khi land (2026-07-27):** class THẬT = `TestMobileRepairSparePartsContract`;
> `cr78_e` là **cite-parity AST** (không phải `cr78_h`), `cr78_g` import hằng THẬT
> **`_STOCK_ENTRY_STATUS`** (không phải `SPARE_STOCK_ENTRY_STATUSES`), `cr78_h` kiểm mô tả op
> `getRepairWorkOrder` nêu `spare_parts_used[]` là nguồn `item_code`. Xem `04 §3.8.2` (bảng cải chính tên).

| TC | Kiểm |
|---|---|
| `cr78_a` | Schema `RepairSparePartUsedItem` tồn tại · `type: object` · `additionalProperties: true` (mirror `RepairChecklistItem`) |
| `cr78_b` | **9 khoá domain** có mặt và tên **KHỚP `field_order`** đọc THẬT từ `spare_parts_used.json` (parity DocType↔OAS — chống drift khi thêm/đổi field) |
| `cr78_c` | 2 khoá phái sinh có mặt · `stock_entry_status.enum` **ĐÚNG 3** giá trị · `stock_entry_ok` `type: integer` + `enum: [0,1]` (**KHÔNG boolean** — quirk CR-01) |
| `cr78_d` | `RepairWorkOrderDetail.properties.spare_parts_used` = `array` items `$ref` **RepairSparePartUsedItem** (resolvable) |
| `cr78_e` | `RepairWorkOrderDetail.properties.parts_pending_stock_entry` `type: integer` + `minimum: 0` |
| `cr78_f` | **A6-invariant**: `len(paths) == 107` · `len(components.schemas) == 281` · tập `operationId` KHÔNG đổi |
| `cr78_g` | **Parity enum**: OAS enum `stock_entry_status` == `list(services.imm09._STOCK_ENTRY_STATUS)` **import THẬT** (mirror `cr77_i`) |
| `cr78_h` | **Cite-parity AST** trên `components.schemas`: mọi cite `services/imm09.py:<dòng> <symbol>` trong `description` của `RepairSparePartUsedItem` + 2 property mới nằm trong vùng AST của symbol |

### §13.8 Counters — sync ĐỦ 7 chỗ, delta **+8** (A10)

| # | Chỗ | Trước | Sau |
|---|---|---|---|
| 1 | `test_mobile_oas.py::_EXPECTED_TEST_COUNT` | 951 | **959** |
| 2 | `test_mobile_docset.py::_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` | 951 | **959** |
| 3 | `test_mobile_docset.py::_GUARD_SUITE_SUM` | 1094 | **1102** |
| 4 | `test_mobile_docset.py::_MOBILE_OAS_TOTAL` | 1120 | **1128** |
| 5 | echo `assertEqual(_EXPECTED_TEST_COUNT, …)` #1 (`test_mobile_oas.py`) | 951 | **959** |
| 6 | echo `assertEqual(_EXPECTED_TEST_COUNT, …)` #2 (`test_mobile_oas.py`) | 951 | **959** |
| 7 | narrative delta `cr78_repair_spare_parts_delta = 8` (`test_mobile_docset.py`) | — | **thêm mới** |

> ⚠️ **Con số baseline luôn có thể stale** (CR khác landed giữa spec↔exec — bài học đa-phiên).
> **Chấm theo DELTA `+8`**, đọc giá trị hiện hành tại chỗ trước khi sửa; nếu baseline ≠ 951 thì cộng 8
> vào giá trị ĐANG CÓ, không ghi đè bằng số trong bảng.

### §13.9 Boundaries

**Always** — 2 khoá phái sinh sinh từ SSoT `_spare_parts_stock_entry_statuses` · enrich SAU khuôn 3 lớp
CR-74 · `spare_parts_used` là mảng (`[]` khi rỗng) sắp theo `idx` · `stock_entry_ok` int 0|1 ·
cite trong `description` + guard AST · counters sync **cùng vòng** với OAS.
**Ask-first** — thêm khoá tồn kho `available_qty`/`warehouse` (đó là **CR-73 nhóm-2**) · đưa
`spare_parts_used` vào `required` · chuẩn hoá `stock_entry_ref` (ADR-IMM09-PARTS-03).
**Never** — ❌ path/opId/param mới · ❌ >1 schema mới · ❌ `additionalProperties:false` cho dòng con
(sẽ reject payload thật) · ❌ `stock_entry_ok` boolean · ❌ đổi/xoá 9 khoá domain · ❌ cite trong comment
YAML · ❌ đổi thứ tự/nội dung 3 lớp CR-74 · ❌ sửa `permissions.py`/DocPerm để test xanh.

### §13.10 ⚠️ Slice contract KHÔNG đóng ở Bước-2 (BA→BE handoff)

Cite-parity (A7) đòi symbol **đã tồn tại** ở dòng thật. `_spare_parts_stock_entry_statuses` /
`_enrich_spare_parts_used` **chưa có trên đĩa** ⇒ nếu dán OAS + guard `cr78_h` ngay bây giờ thì guard **ĐỎ
ngay lập tức** (cite trỏ symbol không tồn tại). **Trình tự BẮT BUỘC — mirror AC-CR-77:**

1. **[BE]** land `services/imm09.py` (3 symbol §3.8.2 + điểm cắm trong `get_work_order`) → chạy `test_imm09`.
2. **[BE] CÙNG VÒNG (atomic)** dán OAS (§13.2/§13.3, cite = **dòng THẬT sau khi land**) + guard `cr78_a..h`
   + 7 counter (§13.8) → chạy `test_mobile_oas` + `test_mobile_docset`.
3. **[FE] CÙNG VÒNG** [`06_Frontend_Design.md §SparePartsStockEntry`](./06_Frontend_Design.md) + test RENDER.

---

## §14 AC-CR-79 — Whitelist khoá `filters` cho `list_repair_work_orders` (SSoT) · khoá lạ = **400 in-envelope** 🔴 SPEC (BE+FE Bước-4)

> **Mirror của [`docs/imm-08/05 §14`](../imm-08/05_API_Specification.md) — đọc bản đó TRƯỚC.** Ở đây CHỈ ghi
> phần KHÁC của IMM-09. Bằng chứng lỗi, hợp đồng envelope, vị trí validate, boundaries, 3 ADR, delta OAS,
> counters, thứ tự handoff: **giống hệt**, không lặp lại.

### §14.1 Bằng chứng riêng IMM-09 (probe LIVE 2026-07-27 — `bench --site miyano console`)

| Probe | Kết quả THẬT |
|---|---|
| `imm09.list_work_orders({"khong_ton_tai_abc": "x"})` | `OperationalError (1054, "Unknown column 'tabAsset Repair.khong_ton_tai_abc' in 'WHERE'")` |
| `imm09.list_work_orders({"sla_breached":"1","is_repeat_failure":"1"})` | **`OK`** — đối chứng chống vacuous: 2 cột THẬT trên `Asset Repair`, web FE gửi ĐÚNG 2 khoá này (`CMWorkOrderListView.vue:109-110`) |

⇒ **KHÁC IMM-08**: màn CM **không** có khoá bịa nào (mọi khoá `buildFilters()` `:104-115` đều hợp lệ) ⇒
**FE CM không phải sửa `buildFilters`**, chỉ sửa banner (§14.4).

### §14.2 `_ALLOWED_FILTER_KEYS` (IMM-09) — **18 khoá**

SSoT khai ở `services/imm09.py`. Cơ chế raise dùng CHUNG helper `services/shared/filters.py::assert_allowed_filter_keys`.

| Khoá | Loại | Consumer / bằng chứng |
|---|---|---|
| `name` | cột | PK trong `_LIST_WO_FIELDS` (`services/imm09.py:2620`) |
| `status` | cột | `CMWorkOrderListView.vue:106` · drill dashboard |
| `asset_ref` | cột | `:108` · **`apply_vendor_scope` bơm** (`services/shared/scope.py:115`) — AC4 |
| `asset_name` | cột | `_LIST_WO_FIELDS` (cột THẬT trên `Asset Repair`, không phải enrich) |
| `assigned_to` | cột | `api/imm09.py:38` (`mine=1`) |
| `priority` | cột | `:107` · drill `?priority=` (`:137`) |
| `repair_type` | cột | `_LIST_WO_FIELDS` |
| `risk_class` | cột | `_LIST_WO_FIELDS` (ma trận SLA BR-09-05) |
| `root_cause_category` | cột | `_LIST_WO_FIELDS` (drill RCA) |
| `sla_breached` | cột | `:109` · drill `?sla_breached=` (`:138`) |
| `sla_target_hours` | cột | `_LIST_WO_FIELDS` |
| `is_repeat_failure` | cột | `:110` · drill `?is_repeat_failure=` (`:139`) |
| `open_datetime` | cột | `_LIST_WO_FIELDS` · khoá `order_by` mặc định |
| `completion_datetime` | cột | `_LIST_WO_FIELDS` |
| `mttr_hours` | cột | `_LIST_WO_FIELDS` |
| `open` | **ảo** | `:113` · drill `?open=` (`:140`) → `_apply_open_drill` (`services/imm09.py:1248`) → `open_repair_filter` SoT (BR-09-08) |
| `sla_breached_live` | **ảo** | chip mobile "Quá hạn SLA" → `_list_sla_breached_live` (`services/imm09.py:1374`) |
| `search` | **ảo** | `api/imm09.py:44` → `pop_search` |

**Khoá CỐ Ý KHÔNG whitelist** (0 consumer): `parts_hold_hours`/`parts_hold_started` (nội bộ đồng-hồ-dừng
BR-09-10 — `parts_hold_started` còn bị `_finalize_list_row` **pop khỏi payload**), `workflow_state`,
`incident_report`, `is_warranty_claim`, `warranty_claim_ref`, `firmware_updated`, `firmware_change_request`,
`serial_no`, `asset_category`, `requested_by`, `assigned_by`, `assigned_datetime`, `dept_head_*`,
`total_parts_cost`, `cannot_repair_reason`, `source_pm_wo`, + 3 child table (`repair_checklist`,
`spare_parts_used`, `attachments` — không filter được ở `get_list` parent).

### §14.3 Vị trí validate (AC5) — thứ tự riêng của IMM-09

```
services.imm09.list_work_orders
  ├ ① assert_allowed_filter_keys(filters, _ALLOWED_FILTER_KEYS)   ← ĐIỂM CẮM DUY NHẤT
  └ ② run_rowscoped(_list_work_orders, …)
         ├ pop sla_breached_live   (③)
         ├ pop_search              (④)
         ├ _apply_open_drill       (⑤ — pop `open`)
         └ _normalize_filters      (⑥)
```

① **trước** ③④⑤⑥ ⇒ 3 khoá ảo (`search`, `open`, `sla_breached_live`) **phải** ∈ whitelist và **ngữ nghĩa
không đổi** (`open` vẫn thua `status` đơn lẻ — `_apply_open_drill:1081`).

### §14.4 FE (AC6) — chi tiết ở [`06_Frontend_Design.md`](./06_Frontend_Design.md)

`CMWorkOrderListView.vue:219` cũng dùng `v-else-if="store.error"` ⇒ **bảng biến mất** khi lỗi. Sửa **giống
IMM-08**: banner cộng-thêm khi `store.workOrders.length > 0`, khối lỗi chiếm-chỗ chỉ khi chưa có dữ liệu.
`stores/imm09.ts:65-67` **không** xoá `workOrders` trong `catch` (đã đúng — **không được** thêm reset).
`buildFilters()` **KHÔNG đổi** (§14.1).

### §14.5 Test bắt buộc

`test_imm09.py::TestCmFilterKeyWhitelist` — bộ TC ở [`07_Testing_QA.md §X`](./07_Testing_QA.md).
Baseline **230 `def test`** (đọc lại trước khi sửa — chấm theo **delta**).

---

## §15 AC-CR-82 — `getRepairWorkOrder` phơi `available_actions[]` **6 CTA server-driven** (đóng **NỬA CM** của mobile CR-74) 🟢 CONTRACT ĐÓNG Bước-2 (OAS + guard LANDED, XANH) · BE+FE Bước-4

**Một câu:** màn Chi tiết phiếu CM hết cảnh *"nút hiện cho mọi người rồi để BE từ chối"* — server công bố **đúng 6 hành động**, mỗi hành động kèm `enabled` + `reason` tiếng Việt, và **advertise == enforce** (nút bật ⟹ gọi được).

Mirror **AC-CR-77** (nửa PM, `PmWorkOrderDetail.available_actions` 4 CTA). Sau vòng này **3 màn Chi tiết** (PM · CM · Sự cố) dùng **CHUNG 1 từ vựng CTA** = schema `AvailableAction`.

### §15.1 Vấn đề — 5 divergence ĐO ĐƯỢC @source (verify 2026-07-27)

Hôm nay FE **tự diễn giải** `allowed_transitions` (bảng *trạng-thái-kế*) thành *hành động* — đó là **bản diễn giải thứ hai** của enforcement, và nó đã lệch ở 5 chỗ:

| # | Divergence | Bằng chứng @source | Hệ quả người dùng |
|---|---|---|---|
| **D-CM-1** | **Cap 2 tầng KHÔNG bằng nhau**: lớp API gate `repair.write`, lớp service gate `repair.create` cho **4** endpoint | `api/imm09.py:123/129/137/143` vs `services/imm09.py:1882/1724/1748/1767` | Vai trò có `write` nhưng **không** `create` (DocPerm là **dữ liệu**, sửa ở `/app`) ⇒ nút bật → **403 câm**. FE hiện suy **1 tầng** (`can('repair.create')`, `CMWorkOrderDetailView.vue:110`) ⇒ ngược lại cũng đúng: `create` mà thiếu `write` ⇒ nút bật → 403 |
| **D-CM-2** | `submit_diagnosis` nhận **CẢ** `Assigned` LẪN `Diagnosing`, nhưng bảng transition từ `Assigned` = `[Diagnosing, Cancelled]` (**không** chứa `Pending Parts`) | `services/imm09.py:1908 submit_diagnosis` vs `_REPAIR_VALID_TRANSITIONS` | Suy CTA từ bảng transition ⇒ **sai pha**: FE phải chắp vá `includes('Diagnosing') \|\| includes('Pending Parts')` (`CMWorkOrderDetailView.vue:118-123`) — logic này **không** phải predicate của service |
| **D-CM-3** | `start_repair` **có endpoint** nhưng **KHÔNG có CTA** trên màn Chi tiết | `api/imm09.py:136 start_repair` LIVE · FE chỉ gọi từ `CMPartsView.vue:122` | **Dead-end**: phiếu `Pending Parts` (đã có phụ tùng) không có đường "Bắt đầu sửa chữa" ngay trên màn Chi tiết |
| **D-CM-4** | `request_spare_parts` **KHÔNG có state-guard** nào | `services/imm09.py:1953 request_spare_parts` (0 `IMM09_BAD_STATE`) | Gọi trên phiếu `Completed`/`Cannot Repair` (**docstatus=1**, `imm_09_repair_workflow.json`) ⇒ `RepairRepo.save` ném lỗi Frappe *"Cannot edit submitted document"* — **không** phải lỗi nghiệp vụ in-envelope |
| **D-CM-5** | `close_work_order(cannot_repair=1)` nhận **4** trạng thái nguồn `{Assigned, Diagnosing, Pending Parts, In Repair}` trong khi workflow JSON chỉ có cạnh `In Repair → Cannot Repair` | `services/imm09.py:2046 close_work_order` vs `imm_09_repair_workflow.json` | Enforcement **rộng hơn** máy trạng thái ⇒ có thể đóng "không thể sửa" từ pha chẩn đoán mà workflow không mô hình hoá (backlog `§15.10-B3`) |

> **Không** sửa enforcement trong vòng này (A5/A7). Vòng này **chỉ** đưa quyết định *"nút nào bật"* về **server**, dùng **đúng** hằng mà guard đang dùng.

### §15.2 SSoT `_REPAIR_ACTION_SPECS` — 6 action, **thứ tự CỐ ĐỊNH** = thứ tự render

`available_actions` **LUÔN đủ 6 phần tử** theo thứ tự dưới đây, cho **mọi** trạng thái trong 9 state của `_REPAIR_VALID_TRANSITIONS` (kể cả terminal — khi đó cả 6 `enabled=false`).

| # | `key` | `label` (VI) | Endpoint (`api/imm09.py`) | Tập trạng-thái-nguồn (hằng `*_FROM`) | `caps` (**HỘI**) | Business gate |
|---|---|---|---|---|---|---|
| 1 | `assign_technician` | Phân công kỹ thuật viên | `assign_technician` `:122` | `_ASSIGN_FROM = {Open}` | `repair.write` ∩ `repair.create` | — |
| 2 | `submit_diagnosis` | Ghi nhận chẩn đoán | `submit_diagnosis` `:128` | `_DIAGNOSIS_FROM = {Assigned, Diagnosing}` | `repair.write` ∩ `repair.create` | — |
| 3 | `request_spare_parts` | Yêu cầu phụ tùng | `request_spare_parts` `:142` | `_PARTS_FROM = _START_FROM ∪ {In Repair}` | `repair.write` ∩ `repair.create` | — |
| 4 | `start_repair` | Bắt đầu sửa chữa | `start_repair` `:136` | `_START_FROM = {Assigned, Diagnosing, Pending Parts}` | `repair.write` ∩ `repair.create` | — |
| 5 | `close_work_order` | Hoàn thành sửa chữa | `close_work_order` `:149` | `_CLOSE_FROM = {In Repair}` | `repair.create` | — |
| 6 | `confirm_inspection` | Xác nhận nghiệm thu | `confirm_inspection` `:180` | `_CONFIRM_FROM = {Pending Inspection}` | `repair.submit` | **SoD** (§15.5) |

**Luật sinh hằng (BE Bước-4 — bắt buộc):** 6 hằng `*_FROM` là **frozenset module-level** và **CHÍNH service guard đọc chúng** (`if doc.status not in _X_FROM: nthrow(MSG.IMM09_BAD_STATE, …)`). Refactor **không đổi hành vi observable** (cùng message-code, cùng `expected` context string). Đây là điều kiện để bất biến **INV-CMCTA-1** *chứng minh được*, không phải *tuyên bố*.

`_PARTS_FROM` **dẫn xuất** (`_START_FROM ∪ {In Repair}`) — không phải danh sách literal thứ hai.

**`Cancelled` KHÔNG BAO GIỜ là action** (là đích hợp lệ từ 6 trạng thái nhưng **0 endpoint hủy** trong `api/imm09.py`) — đối xứng ADR-IMM08-CTA-01. **`Cannot Repair` KHÔNG phải action thứ 7**: cùng endpoint `close_work_order` (cờ `cannot_repair=1`) ⇒ dùng **chung khoá** `close_work_order` (§15.9-FE).

### §15.3 Ma trận **54 ô** (9 status × 6 action) — advertise khi **đủ cap** và **không** vướng SoD

`✓` = `enabled=1` · `✗` = `enabled=0` (kèm reason bậc **transition**).

| `status` | assign | diagnosis | parts | start | close | confirm |
|---|---|---|---|---|---|---|
| Open | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Assigned | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Diagnosing | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Pending Parts | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ |
| In Repair | ✗ | ✗ | ✓ | ✗ | ✓ *(⚠️ có điều kiện — xem dưới)* | ✗ |
| Pending Inspection | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ *(SoD)* |
| Completed | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Cannot Repair | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Cancelled | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**12/54 ô** bật. Trạng thái **rỗng** hoặc **mã lạ** ngoài máy trạng thái ⇒ rơi **bậc transition** cho cả 6 (không bao giờ `reason` rỗng).

### §15.4 `reason` — HẰNG tiếng Việt, 3 bậc ưu tiên `transition > capability > business`

| Hằng | Chuỗi VI | Dùng khi |
|---|---|---|
| `_REPAIR_ACTION_REASON_TRANSITION` | `Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu` | `status ∉ *_FROM` (kể cả status rỗng/mã lạ) |
| `_REPAIR_ACTION_REASON_CAPABILITY` | `Bạn không có quyền thực hiện thao tác này` | thiếu **bất kỳ** cap nào trong `caps` |
| `_REPAIR_ACTION_REASON_SELF_INSPECT` | `Người nghiệm thu phải khác người đóng phiếu — bạn là người đã đóng phiếu này` | SoD (§15.5) |

**Never:** f-string nội suy mã trạng thái (`'In Repair'`, `'Pending Inspection'`) hoặc tên vai trò vào `reason` — đó là **rò tiếng Anh ra UI** (chính sách ngôn ngữ `06_Frontend_Design.md §7`, memory `ui_copy_language_policy`).

### §15.5 Business gate **SoD** (segregation-of-duties, CR-41) — **FAIL-OPEN**, khớp ĐÚNG enforcement

Chỉ áp cho `confirm_inspection`, và **chỉ tính khi** `status == Pending Inspection` (2 gate trước đã đạt) ⇒ **≤1 truy vấn thêm**, 0 truy vấn ở 8 trạng thái còn lại.

| Trường hợp | `enabled` | `reason` | Khớp enforcement |
|---|---|---|---|
| `closer == frappe.session.user` | `0` | `_REPAIR_ACTION_REASON_SELF_INSPECT` | `services/imm09.py:2175 confirm_inspection` → `MSG.IMM09_SELF_INSPECT_FORBIDDEN` |
| `closer` khác | `1` | `""` | cho qua |
| `closer` **không xác định được** (`None`) | `1` | `""` | **FAIL-OPEN** — enforcement cũng cho qua + log debug |

`closer` = actor của Asset Lifecycle Event `repair_pending_inspection` mới nhất (`services/imm09.py:2151 _resolve_wo_closer`) — **tái dùng nguyên hàm**, không viết truy vấn thứ hai.

> ⚠️ FAIL-OPEN vs FAIL-CLOSED vẫn là **câu hỏi mở của USER** (STATE blocker #8). Vòng này **cố ý không đổi** — advertise phải là *tấm gương* của enforcement hiện hành, kể cả khi enforcement còn đang chờ ratify. Đổi enforcement ⇒ đổi builder **cùng lúc** (1 predicate, 2 nơi đọc).

### §15.6 Bất biến (khoá bằng test)

| ID | Bất biến | Chứng minh bởi |
|---|---|---|
| **INV-CMCTA-1a** *(soundness — HARD, 54/54 ô)* | `enabled == 1` ⟹ service **KHÔNG** ném `IMM09_BAD_STATE` | test parametric `test_imm09.py::TestCmAvailableActionsParity` |
| **INV-CMCTA-1b** *(completeness — 45/54 ô)* | `enabled == 0` ∧ đủ cap ∧ không vướng SoD ⟹ service **CÓ** ném `IMM09_BAD_STATE` | cùng test; **ngoại lệ duy nhất** = 9 ô của `request_spare_parts` (0 state-guard @source) — allowlist `_ADVERTISE_NARROWER_THAN_ENFORCE = {"request_spare_parts"}` (**chỉ-giảm**, xem ADR-IMM09-CTA-02) |
| **INV-CMCTA-2** | `reason` 100% VI, lấy từ **hằng** (0 nội suy) | assert `reason ∈ {3 hằng}` |
| **INV-CMCTA-3** | ĐÚNG 6 phần tử, ĐÚNG thứ tự, mỗi phần tử ĐÚNG 5 khoá `{key,label,route,enabled,reason}`, `route == ""` | shape test |
| **INV-CMCTA-4** | Mỗi `spec.endpoint` resolve ĐỘNG được trong `assetcore.api.imm09` **và** `fn in frappe.whitelisted` | mirror INV-PMCTA-4 |
| **INV-CMCTA-5** | `caps` của mỗi action == **hợp** của mọi `rbac.require(...)` trên đường gọi (AST-parse `api/imm09.py` + `services/imm09.py`) | test AST anti-drift |
| **INV-CMCTA-9 (D9)** | `enabled is False ⟹ reason != ""` ∧ `enabled is True ⟹ reason == ""` | test parametric 54 ô |
| **INV-CMCTA-10** | READ-ONLY: 0 `save()`, 0 Asset Lifecycle Event, 0 audit record khi GET; **≤1** truy vấn thêm (chỉ khi `Pending Inspection`) | test đếm ALE trước/sau + `_resolve_wo_closer` không gọi khi status khác |
| **INV-CMCTA-11** | `allowed_transitions` + **toàn bộ** khoá detail hiện có **GIỮ NGUYÊN** (thuần additive) | test key-set superset |

### §15.7 OAS + guard — **ĐÃ LANDED & XANH ở Bước-2** (slice contract đóng)

- `RepairWorkOrderDetail` (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`) `+= available_actions` `type: array`, `items.$ref = '#/components/schemas/AvailableAction'` (**TÁI DÙNG**, 0 schema mới), **OPTIONAL** (∉ `required`, `required` giữ `["name"]`), `additionalProperties` giữ `true`.
- **Đếm bất biến:** `paths` **108** · `schemas` **283** · `parameters` **38** — **KHÔNG ĐỔI**.
- Cite nằm **trong `description`** (comment YAML không vào spec đã parse): 8 symbol bắt buộc — `get_work_order`, 6 hàm mang state-guard, `_resolve_wo_closer`; **2 tầng** (`services/` + `api/`).
- Guard **8 TC** `assetcore/tests/guards/test_mobile_oas.py::TestMobileRepairAvailableActionsParity` `cr82_a..h` — **XANH: `Ran 991 tests … OK`** (2026-07-27); `test_mobile_docset` **`Ran 9 … OK`**.

| TC | Khoá lại điều gì |
|---|---|
| `cr82_a` | property tồn tại + `type: array` |
| `cr82_b` | `items.$ref` = `AvailableAction`, **không** inline `properties` (chống mint schema ngầm) |
| `cr82_c` | ∉ `required`; `required` giữ `["name"]` (client cũ không gãy) |
| `cr82_d` | `additionalProperties` giữ `true` |
| `cr82_e` | 0 path / 0 schema / 0 parameter mới (108 · 283 · 38) |
| `cr82_f` | mô tả nêu **đủ 6 key đúng thứ tự** + «Cancelled KHÔNG BAO GIỜ là action» + «Cannot Repair dùng chung `close_work_order`» + **HỘI** cap 2 tầng + token `enabled`/`reason`/`route`/`FAIL-OPEN` |
| `cr82_g` | **1 từ vựng CTA / 3 màn**: Repair ≡ Pm ≡ Incident cùng `$ref`; `AvailableAction.required` giữ 5 khoá |
| `cr82_h` | **cite-drift 2 tầng** (`api/` + `services/`) — mọi cite phải nằm trong vùng AST của symbol |

> ⚠️ **BE Bước-4 làm DỊCH DÒNG `services/imm09.py`** (thêm `_build_repair_available_actions` + 6 hằng `*_FROM`) ⇒ **8 cite trong mô tả OAS PHẢI refresh theo dòng THẬT**, nếu không `cr82_h` **ĐỎ ĐÚNG THIẾT KẾ**. BE đồng thời bồi **`cr82_i`** (parity `_REPAIR_ACTION_SPECS` import THẬT ↔ 6 key OAS, mirror `cr77_i`) ⇒ `_EXPECTED_TEST_COUNT` **991 → 992** + sync docset (§15.8).

### §15.8 Counters — sync theo **DELTA** (không số tuyệt đối)

| Hằng | File | Trước | Sau (Bước-2) | Sau khi BE bồi `cr82_i` |
|---|---|---|---|---|
| `_EXPECTED_TEST_COUNT` | `tests/test_mobile_oas.py` (+2 assert site) | 983 | **991** | 992 |
| `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` | `tests/test_mobile_docset.py` | 983 | **991** | 992 |
| `_GUARD_SUITE_SUM` | `tests/test_mobile_docset.py` | 1126 | **1134** | 1135 |
| `_MOBILE_OAS_TOTAL` | `tests/test_mobile_docset.py` | 1152 | **1160** | 1161 |
| `cr82_cm_available_actions_delta` | `tests/test_mobile_docset.py` | — | **8** | 9 |

### §15.9 Boundaries

**Always**
- `available_actions` emit **luôn**, **đủ 6 phần tử**, **đúng thứ tự**, kể cả terminal (6 × `enabled=false`).
- `enabled` = `transition_allowed ∩ has_cap ∩ business_gate`; `has_cap` = **HỘI** của **mọi** `rbac.require` trên đường gọi (API **và** service).
- `transition_allowed` đọc **cùng hằng** mà service guard dùng để chặn.
- `reason` là **hằng VI**, luôn khác `""` khi `enabled=false`, luôn `""` khi `enabled=true`.
- **READ-ONLY**: builder chỉ đọc field của doc đã nạp + `rbac.can` + tái dùng `_resolve_wo_closer`.
- FE: nút CTA **chỉ** enable khi key tương ứng `enabled=true`; disabled ⇒ hiện `reason` qua `title`/tooltip.

**Never**
- ❌ Suy CTA từ `allowed_transitions` (bảng transition = **tầng emit**, không phải predicate hành động).
- ❌ Suy `has_cap` từ **1 tầng** hoặc từ **tên vai trò**.
- ❌ Bỏ/đổi `allowed_transitions` hay bất kỳ khoá detail hiện có (thuần additive).
- ❌ Advertise CTA **hủy phiếu** (0 endpoint) hoặc mint key thứ 7 cho `Cannot Repair`.
- ❌ Đổi hành vi **enforcement** trong vòng này (SoD fail-open giữ nguyên; `request_spare_parts` **không** thêm guard vòng này).
- ❌ `save()` / Lifecycle Event / audit record trong đường GET; >1 truy vấn thêm.
- ❌ Đưa `available_actions` vào `required` của OAS.

### §15.10 Handoff BA → BE / FE (delta so với bản trước)

**BE (Bước-4) — `assetcore/services/imm09.py` + `assetcore/tests/imm09/test_imm09.py`**
1. Thêm **6 hằng** `_ASSIGN_FROM` / `_DIAGNOSIS_FROM` / `_START_FROM` / `_PARTS_FROM` / `_CLOSE_FROM` / `_CONFIRM_FROM`; **refactor 6 guard** đọc chính hằng đó (hành vi observable **không đổi**).
2. Thêm `_REPAIR_ACTION_SPECS` (§15.2) + 3 hằng reason (§15.4) + `_build_repair_available_actions(wo)`; gọi trong `get_work_order` **sau** khuôn 3 lớp CR-74, **cạnh** `data["allowed_transitions"]`.
3. Test `TestCmAvailableActionsParity` — **54 ô** parametric (INV-CMCTA-1a/1b/9) + INV-CMCTA-3/4/5/10/11.
4. **Refresh 8 cite** trong OAS `available_actions.description` + bồi `cr82_i` + sync 4 counter (§15.8).
5. **DoD:** `bench --site miyano run-tests --module assetcore.tests.imm09.test_imm09` · `…test_mobile_oas` · `…test_mobile_docset` in ra `Ran N … OK` **THẬT** (timeout ≥ 600000ms). **KHÔNG** `bench migrate` (0 DocType/field mới).

**FE (Bước-4) — `frontend/src/views/cm/CMWorkOrderDetailView.vue`** → chi tiết ở [`06_Frontend_Design.md §CM-CTA`](./06_Frontend_Design.md).

**Backlog mở (KHÔNG làm vòng này)**
- **B1** — `request_spare_parts` thiếu state-guard (`services/imm09.py:1953`): thêm `if doc.status not in _PARTS_FROM: nthrow(MSG.IMM09_BAD_STATE, …)` ⇒ gỡ ngoại lệ khỏi `_ADVERTISE_NARROWER_THAN_ENFORCE`, INV-CMCTA-1b thành **54/54**. *(đối xứng lỗ `report_major_failure` của IMM-08)*
- **B2** — `Cancelled`: land endpoint hủy **hoặc** gỡ `Cancelled` khỏi `_REPAIR_VALID_TRANSITIONS` (đụng workflow JSON + parity-guard) — **cùng câu hỏi** với STATE blocker #2 của IMM-08, nên quyết **1 lần cho cả 2 module**.
- **B3** — `close_work_order(cannot_repair=1)` nhận 4 trạng thái nguồn trong khi workflow JSON chỉ có `In Repair → Cannot Repair`: thu enforcement về `_CLOSE_FROM` **hoặc** bổ sung 3 cạnh vào workflow JSON.
- **B4** — Business gate hạng-2 cho `confirm_inspection` (BR-09-02 phụ tùng thiếu phiếu xuất kho `parts_pending_stock_entry > 0` · BR-09-04 checklist chưa `Pass` đủ · BR-09-03 FCR chưa duyệt — cả 3 enforce ở `before_submit`, `asset_repair.py:62-70`). **Chi phí 0 truy vấn** (giá trị đã có trong payload) nhưng cần **3 hằng reason + 3 ô guard riêng** ⇒ tách vòng sau (**AC-CR-82b**).

#### ADR-IMM09-CTA-01: Action = tập **CÓ ĐƯỜNG THỰC THI**, KHÔNG mirror bảng transition

- **Status**: Accepted — **Date**: 2026-07-27 *(mở rộng `ADR-IMM09-CTA` @`04_Backend_Design.md §3.1`, KHÔNG supersede)*
- **Context**: `_REPAIR_VALID_TRANSITIONS` mô tả **máy trạng thái**; `available_actions` mô tả **việc người dùng bấm được**. Hai tập **không** trùng: `Cancelled` là đích hợp lệ từ 6 trạng thái nhưng **0 endpoint**; `submit_diagnosis` hợp lệ từ `Assigned` mà đích `Pending Parts` **không** có trong bảng transition của `Assigned`.
- **Decision**: `available_actions` sinh từ `_REPAIR_ACTION_SPECS` (khoá theo **endpoint**), `transition_allowed` đọc **hằng `*_FROM` của chính guard**, **không** đọc `_REPAIR_VALID_TRANSITIONS`.
- **Alternatives (loại)**: *mirror bảng transition* → sinh nút hủy chết + sai pha chẩn đoán ⇒ loại. *Giữ suy diễn phía client* → mỗi client tự viết lại predicate, drift theo thời gian ⇒ loại.
- **Consequences**: `allowed_transitions` **vẫn giữ** (hợp đồng cũ, client cũ dùng); 2 field cùng tồn tại với **2 ngữ nghĩa khác nhau** — phải nói rõ trong mô tả OAS (đã làm) để client mới không dùng nhầm.

#### ADR-IMM09-CTA-02: `request_spare_parts` — advertise **HẸP HƠN** enforcement (fail-safe), bất biến parity là **1 chiều**

- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: `request_spare_parts` **không có** state-guard (`services/imm09.py:1953`). Parity 2 chiều (`⟺`) sẽ buộc advertise `enabled=1` ở **mọi** trạng thái, gồm `Completed`/`Cannot Repair` (**docstatus=1**) — bấm vào là lỗi Frappe *"Cannot edit submitted document"* (không phải lỗi nghiệp vụ in-envelope), tệ hơn nút chết.
- **Decision**: advertise theo `_PARTS_FROM = _START_FROM ∪ {In Repair}` (hẹp hơn). Bất biến hợp đồng = **soundness 1 chiều** `enabled=1 ⟹ không BAD_STATE` (**INV-CMCTA-1a**, 54/54); chiều ngược lại (**INV-CMCTA-1b**) áp cho 5 action còn lại, `request_spare_parts` nằm trong allowlist **chỉ-giảm** `_ADVERTISE_NARROWER_THAN_ENFORCE`.
- **Alternatives (loại)**: *thêm guard vào service ngay vòng này* → đổi **enforcement** (vi phạm A5/A7 read-only-round) ⇒ hoãn sang **B1**. *Advertise rộng bằng enforcement* → quảng cáo hành động trên phiếu đã submit ⇒ loại.
- **Consequences**: advertise-hẹp **không bao giờ** sinh nút chết (an toàn), nhưng có thể **ẩn** 1 hành động mà server vẫn chấp nhận (`Open`) — chấp nhận được vì chưa có KTV nhận việc. Allowlist là **hợp đồng nợ**: khi B1 land, xoá phần tử ⇒ guard tự siết về 54/54.

#### ADR-IMM09-CTA-03: `has_cap` = **HỘI của MỌI capability trên đường gọi** (api ∩ service)

- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: 4 endpoint gate `repair.write` ở lớp API nhưng `repair.create` ở lớp service. Hôm nay DocPerm `Asset Repair` cho **cả 5 vai trò** có `write == create` (`asset_repair.json`) ⇒ divergence **tiềm ẩn**; nhưng DocPerm là **dữ liệu sửa được ở `/app`** (đó là điểm mạnh của capability-RBAC) — một lần bỏ `create` của *Repair User* là nút bật → 403 câm, **đúng class-of-bug** mà CR này đóng.
- **Decision**: `spec["caps"]` là **tuple**; `has_cap = all(rbac.can(c) for c in caps)`. Guard **INV-CMCTA-5** AST-parse cả `api/imm09.py` lẫn `services/imm09.py`, assert tập cap advertise == hợp `rbac.require` thật.
- **Alternatives (loại)**: *chỉ lấy cap lớp API* (A3 nguyên văn) → advertise **rộng hơn** enforce ⇒ loại (self-correction BA). *Đồng bộ cap 2 lớp về 1 giá trị* → đổi **bề mặt phân quyền** production ⇒ ngoài scope vòng này (ghi backlog nếu USER muốn siết).
- **Consequences**: 0 truy vấn thêm (`frappe.has_permission` dùng cache per-request); guard sẽ **ĐỎ ĐÚNG** nếu ai đó đổi cap 1 lớp mà quên lớp kia — biến divergence câm thành lỗi test.

---

## §16 AC-CR-84 — Cổng **ẢNH BẰNG CHỨNG NĐ98 (Class C/D)** khi đóng phiếu CM 🟢 **BE Bước-4 ĐÃ LAND (2026-07-27)** · slice contract (OAS + guard) ĐÓNG Bước-2 · 🟡 FE Bước-4 còn lại

> **Trạng thái BE (đo được, không tuyên bố):** predicate SSoT + 4 điểm tiêu thụ + 1 mã thông báo đã LIVE trong
> `services/imm09.py` / `utils/messages.py`; `test_imm09` **273 OK** (+14) · `test_mobile_oas` **1008 OK**
> (lật `cr84_i`→`cr84_j`, counter GIỮ) · `test_mobile_docset` **9 OK** · `gen_fe_messages --check` xanh.
> Mutation-verify 7/7 ĐỎ đúng thiết kế (`07 §XII.2`). **0 `bench migrate`** (0 schema change).
> ⚠️ **Cần USER reload gunicorn `--preload`** trước khi live-verify — `.py` prod đã đổi (LL-DEPLOY-07/08).

**Một câu:** cổng "thiết bị nguy cơ cao phải có ảnh bằng chứng cho **từng mục nghiệm thu**" hiện là **CODE CHẾT** — nó chỉ sống ở client mobile, và ngay ở đó cũng không bao giờ kích hoạt; vòng này đưa cổng về **SERVER**, dựng **một** predicate `repair_evidence_missing_idxs` cho **cả enforcement lẫn advertise lẫn read**.

### §16.1 Vấn đề — cổng an toàn NĐ98 đang **không tồn tại ở đâu cả** (verify @source 2026-07-27)

| # | Sự thật ĐO ĐƯỢC | Bằng chứng |
|---|---|---|
| **E-1** | Field `repair_checklist[].photo` (Attach đơn) **có**, endpoint đính ảnh **có** (BR-09-15/16, shipped 2026-07-11) | `repair_checklist.json` field `photo`; `services/imm09.py:1595 attach_repair_checklist_photo` |
| **E-2** | **KHÔNG** có bất kỳ chỗ nào đọc `photo` để **CHẶN**: `close_work_order` (`:2046`) và `validate_repair_checklist_complete` (`:955`, BR-09-04) chỉ kiểm `result` ∈ {non-empty, ≠ Fail} | `grep "evidence_photo\|row.photo" services/imm09.py` ⇒ chỉ vùng attach (`:1554-1666`) |
| **E-3** | Client mobile TỰ gate, và gate đó **chết**: `isHighRiskClass(v) = v==='high'\|\|v==='critical'` được nuôi bằng `risk_class` ∈ {Class I, Class II, Class III} ⇒ **không bao giờ true** ⇒ `requiredPhotoIdxs = []` ⇒ `photosSatisfied` luôn `true` | mobile CR-51 §"Đã verify tại nguồn" #4/#5 (`src/lib/checklist-photos.ts:57-60`, `repair/[name].tsx:464-466`) |
| **E-4** | Ánh xạ `risk_classification → risk_class` là **MẤT MÁT**: `{Low→I, Medium→II, High→III, Critical→III}`, và asset **chưa phân loại** cũng ra `Class II` ⇒ mobile không thể suy ngược Class C/D, cũng không phân biệt được "chưa phân loại" với "Class B" | `services/imm09.py` `_risk_map` (create_work_order) · mobile CR-51 #2 |
| **E-5** | Web FE có `isHighRiskClassification` **đúng nguồn** nhưng chỉ dùng để **tô màu**, 0 enforcement | `frontend/src/constants/labels.ts:430-445`, `views/cm/CMCreateView.vue:124-140` |

> **Hệ quả nghiệp vụ:** hồ sơ sửa chữa của thiết bị **Class C/D** có thể đóng và **nghiệm thu** mà **không có bức ảnh nào** — hỏng đúng nghĩa vụ hồ sơ NĐ98 (Điều 28) mà `02 §Compliance` đang tuyên bố là đã đáp ứng. Đây là **khoảng cách giữa tài liệu và hệ thống**, không phải feature mới.

**Vì sao vòng này KHÔNG chỉ "vá client":** cổng chỉ sống ở client thì mọi client khác (web, Desk, script, app cũ chưa cập nhật) đều đi vòng qua được. Bài học đã lặp 3 lần trong dự án (CR-54 · CR-76 · AC-CR-77/82): **display phải là tấm gương của enforcement**, và **enforcement phải ở server**.

### §16.2 Predicate SSoT — `repair_evidence_missing_idxs`

```python
# services/imm09.py  (BE Bước-4)

# SSoT nhóm nguy cơ "cần bằng chứng ảnh" (NĐ98 Class C/D). Nguồn DUY NHẤT =
# AC Asset.risk_classification (Low|Medium|High|Critical|""). KHÔNG dùng
# Asset Repair.risk_class (Class I/II/III — đầu vào _SLA_MATRIX; ánh xạ MẤT MÁT).
_EVIDENCE_HIGH_RISK: frozenset[str] = frozenset({"High", "Critical"})


def _repair_evidence_gate_applies(risk_classification: str | None) -> bool:
    """True ⟺ thiết bị thuộc nhóm nguy cơ cao ⇒ cổng ảnh bằng chứng ÁP DỤNG.

    Chuỗi rỗng / None / whitespace / giá trị lạ ⇒ False (A4: "chưa phân loại"
    KHÔNG được suy thành nguy cơ cao, cũng KHÔNG suy thành Class B).
    """
    return (risk_classification or "").strip() in _EVIDENCE_HIGH_RISK


def _repair_row_is_persisted(row) -> bool:
    """Dòng checklist ĐÃ có định danh trong DB (đính ảnh được).

    Frappe gắn ``__islocal = 1`` cho child row được ``doc.append`` khi row chưa có
    ``name`` (frappe/model/base_document.py:337-338) ⇒ đây là discriminator chuẩn,
    KHÔNG tự chế cờ mới.
    """
    return bool(getattr(row, "name", None)) and not row.get("__islocal")


def _repair_evidence_missing_idxs(wo, risk_classification: str | None = None) -> list[int]:
    """SSoT: tập ``idx`` (1-based) dòng ``repair_checklist`` CÒN THIẾU ảnh bằng chứng.

    ĐỌC-THUẦN: 0 save, 0 lifecycle, 0 mutation. ≤1 truy vấn (chỉ khi caller KHÔNG
    truyền ``risk_classification``). Rỗng ``[]`` ⟺ cổng ảnh KHÔNG chặn.

    ⚠️ ``risk_classification=None`` nghĩa là "CHƯA TRA" (predicate tự tra);
    ``""`` nghĩa là "ĐÃ TRA, thiết bị chưa phân loại" ⇒ KHÔNG tra lại (A4).
    """
    rc = (risk_classification
          if risk_classification is not None
          else (AssetRepo.get_value(wo.asset_ref, "risk_classification") or ""))
    if not _repair_evidence_gate_applies(rc):
        return []
    return sorted(
        int(row.idx) for row in (wo.repair_checklist or [])
        if _repair_row_is_persisted(row) and not (row.photo or "").strip()
    )
```

**Boundaries của predicate — Always / Never**

- **Always**: đọc `risk_classification` **verbatim**; đếm **mọi** dòng checklist đã lưu (không loại theo `result`); trả list **đã sắp tăng dần**; ĐỌC-THUẦN.
- **Never**: đọc `risk_class` (Class I/II/III); coi `""` là nguy cơ cao; miễn trừ dòng `result='N/A'` (§16.7-Q1); đếm dòng **chưa lưu** (§16.7-Q2); gọi `frappe.throw` bên trong (predicate **không** ném — caller ném).

### §16.3 Bốn nơi đọc **CÙNG MỘT** predicate (1 định nghĩa · 4 điểm tiêu thụ)

| # | Nơi | Vai trò | Hành vi |
|---|---|---|---|
| **P1** | `close_work_order` (`services/imm09.py:2046`) | **ENFORCE** | Nhánh `cannot_repair=0`: `missing ≠ []` ⇒ `nthrow(MSG.IMM09_EVIDENCE_PHOTO_REQUIRED, …)` |
| **P2** | `confirm_inspection` (`:2174`) | **ENFORCE (chống lách)** | Pre-check **TRƯỚC** `doc.submit()`; cùng envelope, cùng mã |
| **P3** | `_build_repair_available_actions` (`:259`) | **ADVERTISE** | Business gate của **2** khoá CTA — `close_work_order` (mirror P1) **và** `confirm_inspection` (mirror P2, **AC-CR-85**) ⇒ `enabled=false` + `reason` VI |
| **P4** | `get_work_order` (`:1447`) | **READ** | Emit 3 khoá `evidence_photo_*` cho client hiển thị |
| **P5** | `attach_repair_checklist_photo` (`_assert_repair_photo_attachable`) | **ENFORCE (đường khắc phục)** | **AC-CR-85** — chặn đính ảnh khi phiếu ĐÃ KẾT THÚC (`docstatus≠0` ∨ `status ∈ REPAIR_TERMINAL_STATES`); 'Pending Inspection' **KHÔNG** bị chặn (là đường khắc phục duy nhất của ca tái phân loại) |

> **[AC-CR-85 — self-correction so với Bước-2]** P3 ban đầu chỉ gác khoá `close_work_order`, trong khi P2 đã enforce ở `confirm_inspection`. `risk_classification` là thuộc tính của **THIẾT BỊ** (không đóng băng theo phiếu) ⇒ đường HỢP LỆ 100%: đóng phiếu lúc thiết bị còn `Low` → rà soát NĐ98 **tái phân loại** lên `Critical` → nghiệm thu bị chặn 422 nhưng CTA vẫn **BẬT** với `reason` **rỗng** ⇒ nút chết **và** vỡ **D9/INV-CMCTA-9**. Sửa: bậc business thứ hai cho `confirm_inspection` + hằng reason riêng cho bước nghiệm thu (§16.5). Guard: `test_imm09::TestCmEvidencePhotoGate.test_cr84_15/16` + meta-guard `TestCmAvailableActionsParity.test_cr82_b3` (oracle 54 ô nay tính CẢ mã bậc business — trước đó chỉ đếm `IMM09_BAD_STATE` nên **mù** với ca này).

> **INV-CMEVID-1 (bất biến trung tâm):** `getRepairWorkOrder(WO).evidence_photo_missing_idxs` == `context.missing_idxs` của lỗi mà `close_work_order(WO)` trả về, với **cùng** trạng thái dữ liệu. Chứng minh bằng **test parity đọc chung predicate**, không bằng tuyên bố trong tài liệu (A3).

#### P1 — `close_work_order`: vị trí guard là một phần hợp đồng

```text
rbac.require("repair.create")
resolve_idempotency_key(...) → cache HIT? → return VERBATIM      # replay KHÔNG bị re-gate
doc = RepairRepo.get(name)              → NOT_FOUND
if cannot_repair: …                     → MIỄN TRỪ (§16.6 / ADR-IMM09-EVIDENCE-04)
if doc.status not in _CLOSE_FROM        → BAD_STATE
if not dept_head_name.strip()           → DEPT_HEAD_REQUIRED
doc.repair_summary / root_cause_category / dept_head_name / firmware_* = …   ← chỉ IN-MEMORY
if checklist_results: _apply_checklist(doc, checklist_results)               ← chỉ IN-MEMORY
────────── ⛔ GUARD AC-CR-84 ĐẶT TẠI ĐÂY ──────────
missing = _repair_evidence_missing_idxs(doc)
if missing: nthrow(MSG.IMM09_EVIDENCE_PHOTO_REQUIRED, fields=…, missing_count=…, missing_idxs=…)
────────────────────────────────────────────────────
if spare_parts: _apply_spare_parts(...)
doc.is_repeat_failure = … ; doc.status = PENDING_INSPECTION ; RepairRepo.save(doc)   ← PERSIST
```

- **SAU `_apply_checklist`** vì phiếu **legacy 0 dòng** được `_apply_checklist` **append** dòng từ `checklist_results` (`services/imm09.py:2266-2278`) — chạy trước thì predicate nhìn nhầm "checklist rỗng ⇒ không chặn".
- **TRƯỚC mọi lệnh lưu** ⇒ **A2**: bị chặn thì đọc lại doc từ DB phải thấy `status = 'In Repair'` và `repair_summary`/`root_cause_category`/`dept_head_name` **chưa** đổi. Frappe chỉ ghi ở `RepairRepo.save`; guard đứng trước nên **không** cần `rollback` thủ công — nhưng **phải có test đọc-lại-từ-DB**, không được suy luận.
- **KHÔNG** set cache idempotency ở nhánh bị chặn (envelope lỗi **không** phải kết quả để replay).

#### P2 — `confirm_inspection`: pre-check chống lách

Thứ tự guard (giữ nguyên 3 bậc cũ, **bồi bậc 4**):

```text
rbac.require("repair.submit") → NOT_FOUND → BAD_STATE(_CONFIRM_FROM) → SoD (CR-41)
  → ⛔ AC-CR-84: missing = _repair_evidence_missing_idxs(doc); if missing: nthrow(...)
  → doc.dept_head_confirmation_datetime = now ; doc.submit()
```

- **Vì sao cần bậc riêng** (A6): `status` có thể bị đưa về `Pending Inspection` **không qua** `close_work_order` (Desk, `_generic_update`, script) ⇒ cổng ở P1 bị vòng qua. Đây **không** phải phòng thủ thừa: cùng lớp lỗ mà `BR-09-19b` đã phải bịt cho FCR.
- **KHÔNG** đẩy cổng này xuống hook `before_submit`: hook ném qua `nthrow_in_hook` → `frappe.ValidationError` → **HTTP-417 THÔ**, ra ngoài envelope (bài học AC-CR-83). Pre-check ở service ⇒ `ServiceError` ⇒ **HTTP-200 + Error envelope**.
- **Hệ quả vận hành (phải nói với người dùng):** phiếu **đang** ở `Pending Inspection` lúc tính năng land, nếu thiếu ảnh, sẽ **không nghiệm thu được** cho tới khi bổ sung. Ảnh vẫn đính được ở trạng thái này (`docstatus` còn 0, `attach_repair_checklist_photo` **không** gate theo status) ⇒ có đường khắc phục, không phải ngõ cụt.

#### P3 — advertise == enforce

`_build_repair_available_actions(wo, *, risk_classification: str | None = None)`:

```python
if spec["key"] == "close_work_order" and transition_ok and has_cap:
    if _repair_evidence_missing_idxs(wo, risk_classification):
        business_ok, business_reason = False, _REPAIR_ACTION_REASON_EVIDENCE_PHOTO
```

- Chỉ tính khi **2 gate trước đã đạt** ⇒ 0 chi phí ở 8 trạng thái còn lại.
- `get_work_order` **LUÔN** truyền `risk_classification=data["risk_classification"]` (đã đọc sẵn ở `asset_info`) ⇒ **0 truy vấn thêm**; **INV-CMCTA-10 giữ nguyên ngưỡng ≤1** (truy vấn duy nhất vẫn là `_resolve_wo_closer` của SoD).
- **Self-correction §15 (AC-CR-82):** ô `In Repair × close` trong ma trận **54 ô** (`§15.3`) từ nay là **✓ có điều kiện** — `✓` khi cổng ảnh không áp dụng hoặc đã đủ ảnh, `✗` (reason **business**) khi thiếu. `INV-CMCTA-1a` (soundness) **được củng cố**, không bị vi phạm: advertise hẹp đi đúng bằng enforcement mới.

#### P4 — 3 khoá read

| Khoá | Kiểu | Ngữ nghĩa |
|---|---|---|
| `evidence_photo_required` | `integer` enum `[0,1]` | `1` ⟺ `risk_classification ∈ {High, Critical}` — cổng **áp dụng**. **KHÔNG boolean** (quirk CR-01 / LL-BE-50) |
| `evidence_photo_missing_idxs` | `array<integer≥1>` | Tập `idx` 1-based còn thiếu ảnh = **INV-CMEVID-1** |
| `evidence_photo_total_required` | `integer≥0` | Mẫu số = số dòng checklist **đã lưu** khi `required=1`; `0` khi không áp dụng |

Emit **vô điều kiện** (mọi phiếu, mọi trạng thái). **∉ `required`** — xem **ADR-IMM09-EVIDENCE-03** (self-correction so với acceptance A7).

### §16.4 Envelope lỗi — hợp đồng client

```jsonc
// HTTP 200 (Decision-B). KHÔNG 417, KHÔNG status-line 422.
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "http_status": 422,
  "message_code": "IMM09-EVIDENCE-PHOTO-REQUIRED",
  "error": "Thiết bị thuộc nhóm nguy cơ cao — còn 2 mục nghiệm thu chưa có ảnh bằng chứng.",
  "context": { "missing_count": 2, "missing_idxs": [2, 5] },
  "fields":  { "repair_checklist": "Các mục chưa có ảnh bằng chứng: #2, #5." }
}
```

**Mã mới cần bồi vào `utils/messages.py`** (BE Bước-4):

```python
IMM09_EVIDENCE_PHOTO_REQUIRED = "IMM09-EVIDENCE-PHOTO-REQUIRED"

MSG.IMM09_EVIDENCE_PHOTO_REQUIRED: {
    "title": "Thiếu ảnh bằng chứng nghiệm thu",
    "template": "Thiết bị thuộc nhóm nguy cơ cao — còn {missing_count} mục nghiệm thu chưa có ảnh bằng chứng.",
    "action_hint": "Đính ảnh cho từng mục còn thiếu rồi thực hiện lại thao tác.",
    "severity": "warning",
    "http_status": 422,
},
```

- **A10 — 0 rò tiếng Anh:** template **không** nội suy giá trị enum (`High`/`Critical`) — đối lập với tiền lệ `IMM08-PHOTO-REQUIRED` (`utils/messages.py:704-710`) đang chèn `{risk_class}` **thẳng chuỗi EN** vào câu tiếng Việt ⇒ ghi backlog **B-CR84-4**, KHÔNG sửa vòng này (đổi câu chữ IMM-08 = đổi test IMM-08).
- Sau khi thêm mã: chạy `python scripts/gen_fe_messages.py` (và `--check` phải **xanh**) — thiếu bước này FE render `SYS-500`.
- Khoá `fields` = **`repair_checklist`** (§16.7-Q3 / **ADR-IMM09-EVIDENCE-05**), **không** phải `checklist_results`.

### §16.5 Reason VI của CTA (hằng — KHÔNG f-string)

```python
_REPAIR_ACTION_REASON_EVIDENCE_PHOTO = (
    "Thiết bị nguy cơ cao — cần đính đủ ảnh bằng chứng cho các mục nghiệm thu "
    "trước khi hoàn thành sửa chữa")
# [AC-CR-85] CÙNG cổng, khoá CTA `confirm_inspection` (bước NGHIỆM THU)
_REPAIR_ACTION_REASON_EVIDENCE_PHOTO_INSPECT = (
    "Thiết bị nguy cơ cao — cần đính đủ ảnh bằng chứng cho các mục nghiệm thu "
    "trước khi xác nhận nghiệm thu")
```

Bậc **business** (thấp nhất) trong 3 bậc `transition > capability > business` (`§15.4`) ⇒ khi phiếu **không** ở `In Repair` thì lý do hiển thị vẫn là bậc transition, **không** phải câu này. Giữ **D9**: `enabled=false ⟹ reason ≠ ""`.

**Vì sao 2 câu chứ không 1 (AC-CR-85):** hai khoá CTA là hai **hành động người dùng khác nhau** ở hai bước khác nhau của quy trình; người phê duyệt đọc "trước khi hoàn thành sửa chữa" trên nút «Xác nhận nghiệm thu» sẽ đi tìm nút sai bước. Trong khoá `confirm_inspection`, thứ tự bậc business **mirror enforcement** (INV-CMEVID-6): **SoD trước → evidence sau**.

### §16.6 Miễn trừ có chủ đích — nhánh `cannot_repair=1`

`close_work_order(cannot_repair=1)` → `_mark_cannot_repair` (`services/imm09.py:2236`) **KHÔNG** bị cổng ảnh chặn: thiết bị **không sửa được** thì **không có** bằng chứng nghiệm thu để chụp; ép ảnh ở đây = tạo ngõ cụt cho đúng ca xấu nhất (thiết bị hỏng nặng, cần đưa `Out of Service` **ngay**). Ratify: **ADR-IMM09-EVIDENCE-04**. Hồ sơ NĐ98 của nhánh này dựa vào `cannot_repair_reason` + lifecycle event + `transition_asset_status` (đã có).

### §16.7 Bốn câu hỏi thiết kế đã chốt (kèm lý do)

- **Q1 — Dòng `result = 'N/A'` có được miễn ảnh không?** → **KHÔNG.** `result` do **chính KTV** tự khai; miễn trừ theo `result` biến cổng ảnh thành **tuỳ chọn** (khai `N/A` cho cả 6 dòng là xong). BR-09-04 vốn đã chấp nhận `N/A` là "đạt", nên chồng thêm một lối tự-khai nữa là **hai lớp lách**. *(Ghi backlog **B-CR84-1** nếu vận hành thực tế cho thấy có mục thật sự không chụp được — khi đó phải là danh mục **do quản lý cấu hình**, không phải do người thực hiện tự khai.)*
- **Q2 — Dòng checklist client gửi kèm lúc đóng phiếu (chưa lưu) có bị tính không?** → **KHÔNG** (`_repair_row_is_persisted`). Ảnh chỉ đính được vào dòng **đã có định danh** (`attach_repair_checklist_photo` ghi `frappe.db.set_value("Repair Checklist", row.name, …)`) ⇒ tính dòng chưa lưu sẽ tạo lỗi **không có đường khắc phục** (deadlock cho phiếu legacy đóng một-phát-kèm-checklist). **ADR-IMM09-EVIDENCE-02**. Đường đúng cho phiếu legacy: chạy `backfill_repair_checklists` (`services/imm09.py:2297`) → 6 dòng chuẩn có định danh → KTV đính ảnh → đóng phiếu.
- **Q3 — Khoá `fields` là `repair_checklist` hay `checklist_results`?** → **`repair_checklist`**. `ADR-IMM12-14` nói khoá `fields` dùng **tên tham số ghi** để FE neo đúng control; nhưng ở đây **việc khắc phục KHÔNG nằm trên tham số ghi nào của `close_work_order`** — nó nằm ở endpoint **khác** (`attach_repair_checklist_photo`) tác động lên các dòng mà client **đọc và render** từ khoá `repair_checklist`. Neo vào `checklist_results` sẽ trỏ người dùng tới ô nhập **kết quả**, không phải nơi có nút đính ảnh. **ADR-IMM09-EVIDENCE-05** (tinh chỉnh, không supersede ADR-IMM12-14).
- **Q4 — Phiếu high-risk nhưng checklist rỗng (legacy chưa backfill) thì sao?** → Cổng ảnh **không** chặn (mẫu số 0, không có mục nào để chụp — chặn ở đây là lỗi không hành động được). Phiếu vẫn **không** nghiệm thu được vì **BR-09-04** (`validate_repair_checklist_complete`, `:955`) chặn checklist rỗng — nhưng chặn đó đi qua `nthrow_in_hook` ⇒ **HTTP-417 THÔ**. Ghi backlog **B-CR84-3** (đưa BR-09-04 lên pre-check in-envelope ở `confirm_inspection`), **không** làm vòng này.

### §16.8 Bất biến (khoá bằng test — `07 §XII`)

| ID | Bất biến |
|---|---|
| **INV-CMEVID-1** | `getRepairWorkOrder.evidence_photo_missing_idxs` == `context.missing_idxs` mà `close_work_order` từ chối (cùng trạng thái dữ liệu) |
| **INV-CMEVID-2** | `evidence_photo_required = 0` ⟹ `evidence_photo_missing_idxs == []` ∧ `evidence_photo_total_required == 0` |
| **INV-CMEVID-3** | `missing_idxs ⊆ {row.idx của repair_checklist đã lưu}`; `len(missing_idxs) ≤ evidence_photo_total_required` |
| **INV-CMEVID-4** | `missing_idxs == []` ⟺ cổng ảnh **không** chặn `close_work_order` **và** `available_actions[close_work_order].enabled` **không** bị hạ bởi bậc business |
| **INV-CMEVID-4b** *(AC-CR-85)* | `missing_idxs ≠ []` ∧ `status == 'Pending Inspection'` ⟹ `available_actions[confirm_inspection].enabled == false` ∧ `reason == _REPAIR_ACTION_REASON_EVIDENCE_PHOTO_INSPECT` — advertise **KHÔNG** được rộng hơn enforce ở bước nghiệm thu (ca thiết bị tái phân loại) |
| **INV-CMEVID-9** *(AC-CR-85)* | Phiếu ĐÃ KẾT THÚC (`docstatus≠0` ∨ `status ∈ REPAIR_TERMINAL_STATES`) ⟹ `attach_repair_checklist_photo` từ chối IN-ENVELOPE (VALIDATION 422, `fields.file`) ∧ `row.photo` **0 byte** đổi; **NGOẠI LỆ** re-drain idempotent (`client_request_id` đã dùng) vẫn trả envelope success VERBATIM (dedupe pre-check chạy TRƯỚC guard) |
| **INV-CMEVID-5** | Bị chặn ⟹ **0 byte** ghi xuống DB (đọc lại doc: `status`, `repair_summary`, `root_cause_category`, `dept_head_name`, `docstatus` **y nguyên**) |
| **INV-CMEVID-6** | Thứ tự guard `confirm_inspection`: NOT_FOUND → BAD_STATE → SoD → **evidence** → `submit()` |
| **INV-CMEVID-7** | `risk_classification ∈ {"", "Low", "Medium"}` ⟹ hành vi `close_work_order` **byte-identical** baseline (0 regression — A4) |
| **INV-CMEVID-8** | Mọi câu chữ mới (message template, `action_hint`, `fields`, `reason`) **100% tiếng Việt**, 0 nội suy enum/vai trò EN (INV-CMCTA-2) |

### §16.9 Delta OAS + guard — **ĐÃ LANDED & XANH ở Bước-2**

| Hạng mục | Delta |
|---|---|
| `paths` · `components.schemas` · `components.parameters` | **GIỮ 109 · 287 · 38** (property-add thuần, 0 schema mới) |
| `RepairWorkOrderDetail.properties` | **+3** (`evidence_photo_required` · `evidence_photo_missing_idxs` · `evidence_photo_total_required`) |
| `RepairWorkOrderDetail.required` | **GIỮ `["name"]`** (ADR-IMM09-EVIDENCE-03) |
| `RepairWorkOrderDetail.available_actions.description` | bồi business-gate **(3b)** + sửa câu chi phí truy vấn |
| `closeWorkOrder.description` | bồi hợp đồng lỗi mới + miễn trừ `cannot_repair=1`; **CẢI CHÍNH** cap `repair.submit` → **`repair.create`** (`api/imm09.py:149`) |
| `confirmInspection.description` | bồi pre-check + lý do chống lách |
| **Cite-rot đã sửa** (bonus, cùng 2 op) | `services/imm09.py:1105/1134` (số **trước** refactor) → `:2046 close_work_order`; `services/imm09.py:1181` → `:2236 _mark_cannot_repair`; `api/imm09.py:105/165` → `:180 confirm_inspection` / `:149 close_work_order` |
| Guard | **+9 TC** `TestMobileRepairEvidencePhotoContract` `cr84_a..i` (`test_mobile_oas`) |
| Counters (theo **DELTA**, không số tuyệt đối) | `test_mobile_oas._EXPECTED_TEST_COUNT` **+9** (999→1008, 3 chỗ) · `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` **+9** · `_GUARD_SUITE_SUM` **+9** (1142→1151) · `_MOBILE_OAS_TOTAL` **+9** (1168→1177) · `cr84_repair_evidence_photo_delta = 9` (transition-baseline) |

**Verify THẬT (2026-07-27):** `bench --site miyano run-tests --app assetcore --module assetcore.tests.guards.test_mobile_oas` ⇒ **`Ran 1008 tests … OK`**; `…test_mobile_docset` ⇒ **`Ran 9 tests … OK`**.

### §16.10 Boundaries của vòng

- **Always**: 1 predicate — 4 nơi đọc · lỗi nghiệp vụ **in-envelope HTTP-200** · reason/message **tiếng Việt hằng** · guard chạy **trước** mọi lệnh lưu · asset `Low/Medium/""` **0 regression**.
- **Ask first**: đổi danh mục 6 dòng checklist chuẩn · miễn trừ theo `result` · mở rộng cổng sang IMM-08 PM (đã có BR-08-06 **mức phiếu**, khác hạt) · đưa 3 khoá vào `required`.
- **Never**: đọc `risk_class` để suy nhóm nguy cơ · chặn nhánh `cannot_repair=1` · dùng `nthrow_in_hook` cho cổng này (417 thô) · sửa DocType/DocPerm/workflow JSON (vòng này **0 schema change** ⇒ **KHÔNG** `bench migrate`) · sửa `IMM08-PHOTO-REQUIRED` (backlog B-CR84-4).

### §16.11 Handoff BA → BE / FE

**BE (Bước-4) — ✅ ĐÃ LAND 2026-07-27 · `assetcore/services/imm09.py` · `assetcore/utils/messages.py` · `assetcore/tests/imm09/test_imm09.py`**

> 2 điểm BE **tự ghi nhận khác** spec, cần [BA] ratify (không thay đổi hành vi hợp đồng):
> 1. Predicate đếm ảnh qua `_repair_checklist_item_photos(row)` thay vì đọc `row.photo` lần thứ hai — CÙNG SoT mà `get_work_order` hiển thị và max-count của `attach_repair_checklist_photo` đọc (mạnh hơn về SSoT, kết quả tương đương).
> 2. `TC-CM-EVID-11` nửa sau (`confirm_inspection` bị chặn bởi **BR-09-04**) KHÔNG khớp thực tế: sau khi close, 3 dòng đã LƯU và thiếu ảnh ⇒ bị chặn bởi **cổng ảnh** (P2 chạy trước `before_submit`). Đã cải chính tại `07 §XII.2`.

1. `utils/messages.py`: `MSG.IMM09_EVIDENCE_PHOTO_REQUIRED` + entry (§16.4) → `python scripts/gen_fe_messages.py` → `--check` xanh.
2. `services/imm09.py`: `_EVIDENCE_HIGH_RISK` · `_repair_evidence_gate_applies` · `_repair_row_is_persisted` · `_repair_evidence_missing_idxs` · `_REPAIR_ACTION_REASON_EVIDENCE_PHOTO` (§16.2/§16.5).
3. Wire **P1** (§16.3, đúng vị trí) · **P2** (thứ tự INV-CMEVID-6) · **P3** (builder + tham số `risk_classification`, `get_work_order` truyền giá trị đã đọc) · **P4** (3 khoá emit vô điều kiện).
4. Test `TestCmEvidencePhotoGate` — bộ TC ở `07 §XII` (≥12 TC, gồm **đọc-lại-từ-DB** cho INV-CMEVID-5 và **parity** cho INV-CMEVID-1/4).
5. **REFRESH CITE:** land xong thì dòng `services/imm09.py` **dịch** ⇒ cập nhật cite trong OAS (`RepairWorkOrderDetail` + 2 op) và **LẬT** `cr84_i` (PENDING-BE) thành `cr84_j` parity đầy đủ — guard `cr84_h`/`cr84_i` sẽ **ĐỎ ĐÚNG THIẾT KẾ** nếu quên. Counter `test_mobile_oas` **KHÔNG đổi** (lật ≠ thêm TC).
6. **DoD:** `test_imm09` · `test_mobile_oas` · `test_mobile_docset` in `Ran N … OK` **THẬT** (timeout tool ≥ 600000ms). **KHÔNG** `bench migrate` · **KHÔNG** commit.

**FE (Bước-4)** → [`06_Frontend_Design.md §CMEvidencePhoto`](./06_Frontend_Design.md).

### §16.12 [AC-CR-85] Dư âm cổng ảnh — **2 điểm BE đã đóng · 3 điểm CHỜ [BA] ratify**

**Đã đóng ở BE (2026-07-27, không đổi hợp đồng OAS — pure behavior fix):**

| # | Vấn đề | Sửa |
|---|---|---|
| **H1** | **NÚT CHẾT** `confirm_inspection` — advertise RỘNG HƠN enforce (ca thiết bị **tái phân loại** sau khi đóng phiếu); vỡ luôn **D9/INV-CMCTA-9** (`enabled=false` mà `reason=""`) | Bậc business thứ hai ở P3 + hằng `_REPAIR_ACTION_REASON_EVIDENCE_PHOTO_INSPECT` (§16.5) · **NỚI oracle** parity 54 ô (`_CR82_ADVERTISED_GATE_CODES` tính CẢ mã bậc business) + meta-guard AST `test_cr82_b3` chống mù lần sau · TC-CM-EVID-15/16 |
| **M3** | `attach_repair_checklist_photo` **0 guard** `docstatus`/`status` — ghi qua `frappe.db.set_value` nên bồi được ảnh vào phiếu ĐÃ SUBMIT (lách immutability của Frappe); MED-1 (FE hiện thẻ bằng chứng trên phiếu kết thúc) biến lỗ tiềm ẩn thành lỗ **với tới được** | P5 `_assert_repair_photo_attachable` (INV-CMEVID-9). Vị trí = **SAU** dedupe pre-check ⇒ re-drain write-outbox vẫn idempotent · TC-CM-EVID-17/18 |

**CHỜ [BA] ratify — BE CỐ Ý KHÔNG sửa (đổi hợp đồng / thiết kế gốc):**

1. 🔴 **H2 — NGÕ CỤT «Không thể sửa chữa» (LỖI THIẾT KẾ GỐC, không phải bug code).** `ADR-IMM09-CTA-01` chốt 'Cannot Repair' **KHÔNG** là khoá CTA thứ 7 vì "cùng endpoint `close_work_order`". `ADR-IMM09-EVIDENCE-04` lại **MIỄN** nhánh `cannot_repair=1` khỏi cổng ảnh. Hai quyết định đó nay **mâu thuẫn**: cổng ảnh hạ `enabled` của **khoá** `close_work_order`, mà FE bind nút «Không thể sửa chữa» vào **chính khoá đó** (`CMWorkOrderDetailView.vue:162` `CTA_CANNOT_REPAIR_KEY='close_work_order'` + `:disabled="!srvEnabled(spec.key)"`) ⇒ thiết bị Class C/D **không sửa được** (không có phép thử để chụp) thì người dùng **mất luôn** đường đánh dấu — đúng ngõ cụt mà ADR-IMM09-EVIDENCE-04 sinh ra để tránh. Tiền đề "cùng endpoint ⇒ cùng khoá" đã **vỡ** (2 lối vào nay KHÁC `enabled`). Lựa chọn cần chốt: (a) tách khoá CTA thứ **7** `mark_cannot_repair` (⇒ `available_actions` 6→7 phần tử = **đổi hợp đồng**: OAS + guard `cr82_a` + FE) · (b) giữ 6 khoá nhưng thêm trường phân biệt (vd `sub_actions[]`) · (c) FE tự tính nút cannot-repair theo `status` (bỏ server-driven cho nút này — **hồi quy** về hardcode). **BE KHÔNG tự chọn** — [BA] ratify trước.
2. 🟡 **M2 — dòng `result='N/A'` vẫn bị đòi ảnh.** `§16.7-Q1` đã chốt "KHÔNG miễn" (chống hai lớp tự-khai), nhưng vận hành cho thấy mục nghiệm thu **không áp dụng** vẫn phải chụp ⇒ ảnh rác. Nếu [BA] lật quyết định thì sửa **ĐÚNG 1 chỗ** (`_repair_evidence_missing_idxs` — predicate SSoT) ⇒ cả 5 điểm tiêu thụ tự đồng bộ; kèm cập nhật `07 §XII` + backlog **B-CR84-1**.
3. 🟢 **L1 — rò `idx` trần ra UI.** `_MSG_REPAIR_EVIDENCE_FIELD` sinh `"Các mục chưa có ảnh bằng chứng: #2, #5."` và `CMChecklistView` neo NGUYÊN VĂN chuỗi này, trong khi chính sách FE cùng vòng (`FE-CR84-1`) assert `not.toMatch(/\d/)` với lý do "idx là khoá máy". **Hai lớp cùng 1 CR nói ngược nhau** ⇒ chốt 1 hướng: (a) câu field-level dùng `test_description` thay `#idx` (đổi `context.missing_idxs`? **KHÔNG** — mảng máy giữ nguyên, chỉ đổi câu người đọc) · (b) bỏ ràng buộc no-digit ở FE.

**Ghi chú cho [FE] (không thuộc BE):** **M1** — `CMWorkOrderDetailView.vue:658` `v-if="evidenceGateApplies"` (và `CMChecklistView.vue:247`) chỉ dựa `evidence_photo_required===1`, **KHÔNG** gate theo `status` ⇒ phiếu 'Cannot Repair'/'Completed' vẫn hiện lời nhắc hổ phách + nút «Đính ảnh bằng chứng». Sau AC-CR-85 nút đó **chắc chắn** trả 422 (P5) ⇒ chỉ dẫn sai + nút chết mới. Fix: ẩn khối (hoặc câu quá-khứ trung tính) khi `status ∈ {Completed, Cannot Repair, Cancelled}`.

**Backlog mở (KHÔNG làm vòng này)**

- **B-CR84-1** — danh mục mục nghiệm thu **được phép** không có ảnh, cấu hình bởi **quản lý** (không phải KTV tự khai `N/A`).
- **B-CR84-2** — đối xứng cho **IMM-08 PM**: BR-08-06 đang gate ở **mức phiếu** (`doc.attachments`) trong khi PM đã có `attach_pm_checklist_photo` **mức mục** ⇒ cùng lớp lệch hạt như CM.
- **B-CR84-3** — BR-09-04 (checklist rỗng / chưa Pass) vẫn thoát ra **HTTP-417 thô** ở `confirm_inspection` ⇒ nâng lên pre-check in-envelope (cùng khuôn AC-CR-83).
- **B-CR84-4** — `IMM08-PHOTO-REQUIRED` nội suy `{risk_class}` chuỗi **EN** vào câu tiếng Việt (`utils/messages.py:704-710`) ⇒ vi phạm chính sách ngôn ngữ; sửa kèm test IMM-08.
- **B-CR84-5** — phơi `evidence_photo_*` trên **list item** phiếu CM (`RepairWorkOrderListItem`) để KTV thấy trước khi mở phiếu (mobile CR-51 gợi ý "nếu rẻ").

#### ADR-IMM09-EVIDENCE-01: Cổng ảnh bằng chứng thuộc **SERVER**, nguồn là `risk_classification`

- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: Cổng NĐ98 Class C/D được spec từ CR-15 nhưng chỉ hiện thực ở client mobile, và ở đó nó chết vì suy nhóm nguy cơ từ `risk_class` (ánh xạ mất mát). Web/Desk/script **không có** cổng nào.
- **Decision**: Enforce ở **service** (`close_work_order` + `confirm_inspection`), nguồn nhóm nguy cơ là `AC Asset.risk_classification` ∈ {High, Critical}; client chỉ **hiển thị** trạng thái cổng.
- **Alternatives (loại)**: *vá client mobile* → mọi client khác vẫn lách; *suy `Class III ⟹ C/D`* → suy diễn trên dữ liệu mất mát, và `Class II` lẫn giữa "Medium" với "chưa phân loại" ⇒ loại; *thêm field `evidence_required` vào DocType* → cần `bench migrate` (HARD-STOP) và sinh nguồn sự thật thứ hai ⇒ loại.
- **Consequences**: `close_work_order`/`confirm_inspection` có thêm ≤1 truy vấn (chỉ khi chưa biết `risk_classification`); phiếu high-risk đang mở sẽ cần bổ sung ảnh trước khi đóng/nghiệm thu (đúng ý đồ, có đường khắc phục).

#### ADR-IMM09-EVIDENCE-02: Chỉ tính dòng checklist **đã lưu**

- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: `_apply_checklist` có nhánh **append** cho phiếu legacy 0 dòng; dòng vừa append **chưa có** `name` ⇒ không thể đính ảnh.
- **Decision**: predicate bỏ qua dòng có `__islocal` / thiếu `name` (`frappe/model/base_document.py:337-338`).
- **Alternatives (loại)**: *tính tất cả* → phiếu legacy đóng-một-phát bị **deadlock** (lỗi không có đường khắc phục); *cấm nhánh append* → đổi hành vi `_apply_checklist`, rủi ro regression ngoài scope.
- **Consequences**: phiếu legacy 0 dòng đóng được **không** kèm ảnh; bù lại **BR-09-04** vẫn chặn nghiệm thu, và `backfill_repair_checklists` là đường chuẩn hoá. Ghi rõ ở §16.7-Q4 + backlog B-CR84-3.

#### ADR-IMM09-EVIDENCE-03: 3 khoá read **KHÔNG** vào `required` — *(self-correction so với acceptance A7)*

- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: Acceptance A7 yêu cầu 3 khoá nằm trong `required` của `RepairWorkOrderDetail`, mục đích là để codegen mobile **không** coi cổng là tuỳ chọn (mầm mống dead-gate). Nhưng repo có bất biến kiến trúc **"4 màn Chi tiết chỉ PK là `required`"** đang được **3 guard độc lập** khoá (`test_mob_oas_30c` sweep 4 schema · `test_repairtrans_b` · `cr82_c`), và schema là data-layer **mở** (`doc.as_dict()`): **mọi** khoá enrich luôn-emit khác (`risk_classification`, `asset_info`, `allowed_transitions`, `available_actions`, `parts_pending_stock_entry`) đều optional.
- **Decision**: 3 khoá **∉ `required`**, nhưng mô tả **bắt buộc** khai 2 điều và guard `cr84_b` khoá lại: (i) server emit **VÔ ĐIỀU KIỆN**; (ii) *"vắng khoá KHÔNG có nghĩa là không có cổng"*.
- **Alternatives (loại)**: *đưa vào `required` theo A7* → phải **nới 3 guard** (một trong đó là sweep 4-schema) để đổi lấy lợi ích **không load-bearing**: sau vòng này an toàn nằm ở **server**, client bỏ qua khoá thì bị chặn in-envelope kèm `missing_idxs`. Nới guard kiến trúc để hợp với spec là đúng anti-pattern *"sửa test cho khớp code"* ⇒ loại. *Đặt `default: 1` fail-safe* → client cũ sẽ chặn oan mọi phiếu ⇒ loại.
- **Consequences**: mirror **không** hứa thứ server chưa phát (BE land ở Bước-4 cùng vòng, contract không nói dối ở giữa); codegen sinh field **nullable** ⇒ tài liệu client (`06`) phải nói rõ *"vắng ⇒ KHÔNG suy là không có cổng"*. Nếu USER muốn theo đúng A7, đây là thay đổi **1 dòng YAML + 4 dòng test** — nhưng phải là quyết định có ý thức, không phải hệ quả phụ.

#### ADR-IMM09-EVIDENCE-04: Miễn trừ nhánh `cannot_repair=1`

- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: "Không thể sửa" là kết luận **không có** quá trình nghiệm thu ⇒ không có ảnh bằng chứng để chụp.
- **Decision**: cổng ảnh chỉ áp cho nhánh HOÀN THÀNH (`cannot_repair=0`) và cho `confirm_inspection`.
- **Alternatives (loại)**: *áp cho cả 2 nhánh* → thiết bị hỏng nặng bị kẹt, không đưa được về `Out of Service` (rủi ro an toàn **ngược**).
- **Consequences**: hồ sơ nhánh này dựa vào `cannot_repair_reason` + lifecycle event; nếu sau này cần ảnh hiện trạng hỏng thì đó là **field/luồng khác** (ảnh lỗi `fault_image`), không phải cổng nghiệm thu.

#### ADR-IMM09-EVIDENCE-05: Khoá `fields` = **`repair_checklist`** (tên khoá ĐỌC), không phải tham số ghi

- **Status**: Accepted — **Date**: 2026-07-27 *(tinh chỉnh `ADR-IMM12-14`, KHÔNG supersede)*
- **Context**: `ADR-IMM12-14` chốt khoá `fields` dùng **tên tham số ghi** của endpoint để FE neo thông điệp dưới đúng control. Ở AC-CR-84, việc khắc phục **không** thực hiện qua tham số ghi nào của `close_work_order` mà qua endpoint khác (`attach_repair_checklist_photo`) trên các dòng client render từ khoá đọc `repair_checklist`.
- **Decision**: khi hành động khắc phục nằm ở **endpoint khác**, khoá `fields` dùng **tên khoá đọc mà client đang render**. Ở đây: `repair_checklist`.
- **Alternatives (loại)**: *`checklist_results`* → neo vào ô nhập **kết quả**, sai chỗ (nút đính ảnh nằm ở bảng đọc); *bỏ `fields`* → mất khả năng neo, người dùng chỉ thấy toast chung.
- **Consequences**: FE/mobile map `fields.repair_checklist` → bảng checklist (không phải form input). Quy tắc bổ sung được ghi vào `05 §11.1` để module khác dùng lại.
