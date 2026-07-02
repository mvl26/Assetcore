# ADR-MOBILE-016 — `listPmWorkOrders` scope `assigned_to` qua param opt-in `mine` (**ĐÓNG known-gap A2 ĐỐI XỨNG** cho tab "Phiếu PM của tôi" — MyWorkOrdersView › MVP-5a) — contract TRUNG THỰC với cơ-chế thật, KHÔNG còn claim suông "Scope theo user"

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-016 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-28 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-015** (đối-xứng `IncidentMine` — gap "next" nêu đích danh ở §Consequences) · ADR-MOBILE-001 (g — envelope list-read 2 rows-key) · C-LISTREAD (`04-api-contract.md §6.1/§6.2/§8.4`) · Core Doc IMM-08 `05_API_Specification.md §2 #1` + `ADR-IMM08-MOB-04` |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm08.py`, `assetcore/services/imm08.py`, `assetcore/repositories/base.py`, `assetcore/tests/test_mobile_oas.py`, `assetcore/tests/test_imm08.py`, `assetcore/tests/test_mobile_docset.py`). Contract: [`04-api-contract.md`](./04-api-contract.md). Core Doc IMM-08: `docs/imm-08/05_API_Specification.md §2 #1 (list_pm_work_orders — filter mine)` + `ADR-IMM08-MOB-04`.

---

## Context

Màn **`MyWorkOrdersView`** (mobile MVP-flow-5) có tab **"Phiếu PM của tôi"** (MVP-5a) — KTV xem CHỈ các phiếu PM **gán cho chính mình** (`assigned_to == session.user`). Endpoint tái dùng `assetcore.api.imm08.list_pm_work_orders` (`api/imm08.py:28`).

**Lỗi thiết kế gốc (A2 known-gap ĐỐI XỨNG — contract nói dối):** OpenAPI `listPmWorkOrders` summary `[MVP-5a] Phiếu PM của tôi` + description CLAIM "Scope theo user (count==rows, permission-aware)", NHƯNG `list_pm_work_orders(filters, page, page_size)` (`api/imm08.py:28`) **KHÔNG có cơ chế** nào scope theo `assigned_to` — chỉ forward `filters` JSON-blob đã `parse_json` + `apply_vendor_scope` xuống `svc.list_work_orders`. ⇒ tab "Phiếu PM của tôi" gọi endpoint này sẽ trả **mọi** PM WO mà quyền đọc cho phép (kể cả WO gán người khác), KHÔNG self-scope. Contract = **claim suông** — đây chính là gap "next" mà **ADR-MOBILE-015 §Consequences** nêu đích danh: *"Scope `assigned_to` cho PM/CM (`listPmWorkOrders`/`listRepairWorkOrders`) VẪN known-gap — Phase-E bồi param đối xứng (`mine`/`assigned`)."*

**Cơ-chế hiện hữu (đã VERIFY):**
- `list_pm_work_orders` (`api/imm08.py:28`): `f = parse_json(filters)` (`:30`) → `f = apply_vendor_scope(f, "PM Work Order")` (`:33`) → `handle(svc.list_work_orders, f, page, page_size)` (`:34`).
- `svc.list_work_orders(filters, page, page_size)` (`services/imm08.py:558`) → `PMWorkOrderRepo.list(filters=_normalize_filters(filters), …)` (`:559-566`).
- `_normalize_filters` (`services/imm08.py:238`) pass-through key thường (`assigned_to` string → `out["assigned_to"]=v`, nhánh `else`); CHỈ biến đổi virtual key `due_before`/`overdue`.
- `BaseRepository.list` (`repositories/base.py:48`): `total = count_with_or(DOCTYPE, filters, or_filters)` (`:65`) + `rows = frappe.get_all(DOCTYPE, filters=filters, …)` (`:67-71`) — **CÙNG** `filters` dict ⇒ count==rows. `list_pm_work_orders` KHÔNG truyền `or_filters` ⇒ `count_with_or` = `frappe.db.count` thuần.
- `assigned_to` là field thật trên PM WO (đã trả trong list-item `services/imm08.py:561,594`, set bởi `assign_technician` `:672,679`).

## Decision

**Bồi 1 query-param opt-in `mine` (int `0|1`, default `0`) — KHÔNG endpoint mới, KHÔNG đổi shape.** Đối-xứng `IncidentMine`/ADR-MOBILE-015, KHÁC 1 điểm: **inject @api-layer** (vì PM filters là JSON-blob đã parse @api) thay vì seed @service-layer.

1. **OpenAPI** — thêm `components/parameters/WorkOrderMine` (`name:mine`, `in:query`, `required:false`, schema `type:integer default:0 enum:[0,1]` — **mirror `IncidentMine`**, né int-vs-bool trap Open#1) + `$ref` vào `listPmWorkOrders.parameters` (param-set `{WorkOrderFilters, Page, PageSize}` → **+`WorkOrderMine`**) + sửa `description` khớp cơ-chế thật (BỎ claim suông "Scope theo user (count==rows, permission-aware)"). `WorkOrderMine` `$ref`'d NGAY ⇒ KHÔNG orphan. **0 path mới** (path-count GIỮ **46** — thêm param ≠ thêm path), **0 schema-component mới**.

2. **API** (`api/imm08.py`) — `list_pm_work_orders(filters: str = "{}", mine: int = 0, page: int = 1, page_size: int = 20)`: SAU `f = apply_vendor_scope(f, "PM Work Order")` (`:33`), thêm `if int(mine or 0): f["assigned_to"] = frappe.session.user` rồi `handle(svc.list_work_orders, f, …)`. ⇒ `assigned_to` AND vào `filters` dict trước khi xuống service/repo. Guest-gating GIỮ qua DocPerm/permission_query "PM Work Order" + `apply_vendor_scope` (KHÔNG thêm in-handler cap-403).

3. **Service/Repo** — **KHÔNG đụng** `services/imm08.py`/`repositories/`. `_normalize_filters` pass-through `assigned_to`; `BaseRepository.list` đếm `total` + lấy `rows` trên CÙNG `filters` (đã có `assigned_to`) ⇒ **INVARIANT count==rows** khi `mine=1`.

**Hành vi:** `mine=1` → CHỈ PM WO `assigned_to==session.user`, AND với mọi filter trong blob (vd `mine=1&filters={"status":"Open"}` = phiếu PM của tôi đang mở; `mine=1&filters={"overdue":1}` = phiếu PM của tôi quá hạn — virtual key `overdue` vẫn AND với `assigned_to`). `mine=0`/absent → `filters` dict **BYTE-IDENTICAL** với trước (backward-compat tuyệt đối — web-FE `PMWorkOrderListView` KHÔNG đổi, PM WO gán người khác VẪN hiện).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | Endpoint riêng `list_my_pm_work_orders` | +1 path (vỡ "path-count UNCHANGED" 46) + nhân đôi pagination/enrich/contract surface + 2 điểm bảo trì. |
| B | Auto-scope MỌI read theo `assigned_to` qua `permission_query_conditions` | Vỡ view supervisor/QA (cần thấy TẤT CẢ PM WO) + đổi security-semantics + count-vs-rows lệch cho persona không-self (memory `asset_list_count_drill_technician`). |
| C | Seed `assigned_to` @service-layer (giống IncidentMine seed @`_build_incident_filters`) | KHÁC cấu trúc: PM filters là JSON-blob `parse_json` @api (KHÔNG discrete param như imm12). Inject @api-layer SAU `apply_vendor_scope` = 1 dòng, KHÔNG đụng service/repo ⇒ blast-radius nhỏ hơn. |
| D ✅ | Query-param opt-in `mine` (default 0 = cũ), inject `f["assigned_to"]=session.user` @api SAU `apply_vendor_scope`, ANDed vào CÙNG `filters` dict | Blast-radius = 1 nhánh `if mine:` @api + 1 param; backward-compat; count==rows giữ; KHÔNG đụng service/repo; codegen sinh client truyền `mine=1` cho tab. |

## Consequences

- **(+)** Contract TRUNG THỰC: `mine=1` ↔ cơ-chế filter `assigned_to` thật; description không còn claim suông "Scope theo user".
- **(+)** `mine=0`/absent UNCHANGED ⇒ blast-radius fence ĐO ĐƯỢC (test: PM WO assigned cho user khác VẪN hiện khi `mine=0`).
- **(+)** `pagination.total == len(data.data)` khi `mine=1` (cùng `filters` dict — chống count-vs-rows drift, memory `asset_list_count_drill_technician`).
- **(+)** Path-count GIỮ 46; KHÔNG schema mới ⇒ `test_mobile_docset` path-count + ADR-registration GREEN (ADR này đăng-ký README §1 ADR-table).
- **(+)** **Đối-xứng A2 đóng cho PM** — ADR-MOBILE-015 đóng cho `listIncidents` (reported_by), ADR này đóng cho `listPmWorkOrders` (assigned_to). Còn lại `listRepairWorkOrders` (CM, assigned_to) — Phase tiếp (đối-xứng tương tự).
- **(−)** `mine` là **filter ứng-dụng**, KHÔNG phải hàng-rào-bảo-mật: bảo mật read VẪN do DocPerm/permission_query "PM Work Order" (`pm.read`) + `apply_vendor_scope` đảm trách. KTV `pm.read` gọi `mine=1` → 200 + chỉ PM WO của mình, KHÔNG leak assignee khác (vì `assigned_to` tường minh).

**RED-before (BE Bước-4 chứng minh mỗi assert mới):** sau khi BA bồi `WorkOrderMine` vào yaml + `$ref` vào `listPmWorkOrders.parameters`, `test_mobile_oas.py::TC-MOB-OAS-14b` (`_LIST_PARAM_EXPECT[_LIST_PM_PATH]`) ĐỎ (param-set 4 ≠ expected 3) + `_LIST_LIVE_FN[_LIST_PM_PATH]` introspect signature `{filters, page, page_size}` ≠ yaml param ⇒ tín hiệu BE cập nhật: (1) `api/imm08.py` thêm `mine: int = 0` + inject; (2) `_LIST_PARAM_EXPECT[_LIST_PM_PATH]` +`_WO_MINE_REF`; (3) `_LIST_LIVE_FN[_LIST_PM_PATH]` +`mine`; (4) assert shape `WorkOrderMine` (int default 0 enum `[0,1]`) trong `14d`; (5) `test_imm08` (mine-filter + fence backward-compat + count==rows + AND-with-filters) → GREEN. Path-count `TC-MOB-OAS` GIỮ 46.
