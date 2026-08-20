# ADR-MOBILE-017 — `listRepairWorkOrders` scope `assigned_to` qua param opt-in `mine` (**ĐÓNG known-gap A2 — symmetry CUỐI** cho tab "Phiếu CM của tôi" — MyWorkOrdersView › MVP-5b) — contract TRUNG THỰC với cơ-chế thật, KHÔNG còn claim suông "Scope theo user"

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-017 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-29 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-016** (đối-xứng PM `listPmWorkOrders` — gap "next" `listRepairWorkOrders` nêu đích danh ở §Consequences) · **ADR-MOBILE-015** (đối-xứng `IncidentMine`) · ADR-MOBILE-001 (g — envelope list-read, C3-split element RIÊNG) · C-LISTREAD (`04-api-contract.md §6.1/§6.2/§8.4`) · Core Doc IMM-09 `05_API_Specification.md §3.1` + `04_Backend_Design.md §3.6 ADR-IMM09-LISTMINE` |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm09.py`, `assetcore/services/imm09.py`, `assetcore/repositories/base.py`, `assetcore/permissions.py`, `assetcore/tests/guards/test_mobile_oas.py`, `assetcore/tests/imm09/test_imm09.py`, `assetcore/tests/guards/test_mobile_docset.py`). Contract: [`04-api-contract.md`](./04-api-contract.md). Core Doc IMM-09: `docs/imm-09/05_API_Specification.md §3.1 (list_repair_work_orders — filter mine)` + `04_Backend_Design.md §3.6`.

---

## Context

Màn **`MyWorkOrdersView`** (mobile MVP-flow-5) có tab **"Phiếu CM của tôi"** (MVP-5b) — KTV xem CHỈ các phiếu CM/sửa-chữa **gán cho chính mình** (`assigned_to == session.user`). Endpoint tái dùng `assetcore.api.imm09.list_repair_work_orders` (`api/imm09.py:21`).

Đây là **mắt-xích CUỐI** đóng đối-xứng A2 (self-scope của 3 list-read MyWorkOrdersView): ADR-MOBILE-015 đóng `listIncidents` (`reported_by`, MVP-5c), ADR-MOBILE-016 đóng `listPmWorkOrders` (`assigned_to`, MVP-5a), ADR này đóng `listRepairWorkOrders` (`assigned_to`, MVP-5b) — đúng gap "next" mà **ADR-MOBILE-016 §Consequences** nêu đích danh: *"Còn lại `listRepairWorkOrders` (CM, assigned_to) — Phase tiếp (đối-xứng tương tự)."*

**Lỗi thiết kế gốc (A2 known-gap — contract nói dối):** OpenAPI `listRepairWorkOrders` summary `[MVP-5b] Phiếu CM của tôi` + description CLAIM **"Scope theo user"**, NHƯNG `list_repair_work_orders(filters, page, page_size)` (`api/imm09.py:21`) **KHÔNG có cơ chế** nào scope theo `assigned_to` — chỉ forward `filters` JSON-blob đã `parse_json` + `apply_vendor_scope` xuống `svc.list_work_orders`. ⇒ tab "Phiếu CM của tôi" gọi endpoint này sẽ trả **mọi** CM WO mà quyền đọc cho phép (kể cả WO gán người khác — vd với senior/supervisor có `asset_repair_query` trả `""`), KHÔNG self-scope. Contract = **claim suông**.

**Cơ-chế hiện hữu (đã VERIFY):**
- `list_repair_work_orders` (`api/imm09.py:21`): `f = parse_json(filters)` (`:25-28`) → `f = apply_vendor_scope(f, "Asset Repair")` (`:29`) → `handle(svc.list_work_orders, f, page, page_size)` (`:30`).
- `svc.list_work_orders(filters, page, page_size)` (`services/imm09.py:714`) → `RepairRepo.list(filters=_normalize_filters(_apply_open_drill(filters)), …)` (`:715-726`).
- `_apply_open_drill` (`services/imm09.py:701`) CHỈ đụng virtual key `open` (pop + `open_repair_filter`); key `status` đơn ƯU TIÊN hơn `open`. KHÔNG đụng `assigned_to`.
- `_normalize_filters` (`services/imm09.py:1312`) pass-through key thường (`assigned_to` string → `out["assigned_to"]=v`, nhánh `else`); CHỈ bọc list value (non-operator) thành `["in",[...]]`.
- `BaseRepository.list` (`repositories/base.py:48`): `total = count_with_or(DOCTYPE, filters, or_filters)` (`:65`) + `rows = frappe.get_all(DOCTYPE, filters=filters, …)` (`:67-71`) — **CÙNG** `filters` dict ⇒ count==rows. `list_repair_work_orders` KHÔNG truyền `or_filters` ⇒ `count_with_or` = `frappe.db.count` thuần. Cả 2 áp `permission_query_conditions` "Asset Repair" (`asset_repair_query` `permissions.py:115`).

> ⚠️ **CẢI CHÍNH 2 FACT TRONG DÒNG TRÊN (BA Self-Correction 2026-07-25 — cite đã rot, quyết định `mine` KHÔNG đổi):**
> 1. *"`count_with_or` = `frappe.db.count` thuần"* — **SAI kể từ ADR-IMM00-LIST-SCOPE §4b**: `count_with_or` nay LUÔN đếm bằng `frappe.get_list(..., limit_page_length=0)` cho **cả** nhánh search lẫn non-search (`services/shared/filters.py:275-281`).
> 2. *"Cả 2 áp `permission_query_conditions`"* — **SAI**: `frappe.get_all` **KHÔNG** áp `permission_query_conditions`; chỉ `frappe.get_list` áp. ⇒ `total` (scoped) và `rows` (thô) chạy **2 predicate KHÁC nhau** ⇒ **count < rows + rò phiếu người khác** cho persona row-scoped — đây chính là finding CRITICAL đóng bởi **INV-ROWSCOPE** ([ADR-IMM00-LIST-SCOPE §8](../imm-00/ADR-IMM00-LIST-SCOPE.md), `BaseRepository.list(scope="user")`).
>
> **Quyết định của ADR-017 (query-param `mine`) KHÔNG đổi** — `mine` vẫn là filter ứng-dụng, đúng như §Consequences đã ghi. Chỉ **cơ sở "count==rows đã đúng sẵn"** là sai; bất biến đó nay do INV-ROWSCOPE bảo đảm chứ không phải do `filters` dict dùng chung.
- `assigned_to` là field thật (Link → User, `asset_repair.json:234`), đã trả trong list-item (`services/imm09.py:719`) + enrich `assigned_to_name`, set bởi `assign_technician` (`services/imm09.py:449`).

## Decision

**Bồi 1 query-param opt-in `mine` (int `0|1`, default `0`) — KHÔNG endpoint mới, KHÔNG đổi shape, REUSE component `WorkOrderMine` (R38/ADR-MOBILE-016), KHÔNG tạo component mới.** Đối-xứng ADR-MOBILE-016 hệt (CÙNG cấu trúc filters JSON-blob @api): inject @api-layer SAU `apply_vendor_scope`.

1. **OpenAPI** — `$ref` `components/parameters/WorkOrderMine` (ĐÃ tồn tại từ R38 — `name:mine`, `in:query`, `required:false`, schema `type:integer default:0 enum:[0,1]`) vào `listRepairWorkOrders.parameters` (param-set `{WorkOrderFilters, Page, PageSize}` → **+`WorkOrderMine`** = 4) + sửa `description` khớp cơ-chế thật (BỎ claim suông "Scope theo user" → "mine=1 → assigned_to==session.user (tab Phiếu CM của tôi MVP-5b)"). `WorkOrderMine` đã defined + nay `$ref`'d bởi 2 op (listPm + listRepair) ⇒ KHÔNG orphan/dangling. **0 path mới** (path-count GIỮ **46** — thêm param ≠ thêm path), **0 schema-component mới** (REUSE). Component description generalize PM→PM+CM (shape UNCHANGED).

2. **API** (`api/imm09.py`) — `list_repair_work_orders(filters: str = "{}", mine: int = 0, page: int = 1, page_size: int = 20)`: SAU `f = apply_vendor_scope(f, "Asset Repair")` (`:29`), trước `handle(svc.list_work_orders, …)`, thêm `if int(mine or 0): f["assigned_to"] = frappe.session.user`. ⇒ `assigned_to` AND vào `filters` dict trước khi xuống service/repo (mirror BYTE-for-BYTE `api/imm08.py::list_pm_work_orders`). Read-gating GIỮ qua DocPerm/permission_query "Asset Repair" (`repair.read` + `asset_repair_query`) + `apply_vendor_scope` (KHÔNG thêm in-handler cap-403).

3. **Service/Repo** — **KHÔNG đụng** `services/imm09.py`/`repositories/`. `_apply_open_drill` + `_normalize_filters` pass-through `assigned_to`; `BaseRepository.list` đếm `total` + lấy `rows` trên CÙNG `filters` (đã có `assigned_to`) ⇒ **INVARIANT count==rows** khi `mine=1`.

**Hành vi:** `mine=1` → CHỈ CM WO `assigned_to==session.user`, AND với mọi filter trong blob (vd `mine=1&filters={"status":"Open"}` = phiếu CM của tôi đang mở; `mine=1&filters={"open":1}` = phiếu CM của tôi đang-mở qua `open_repair_filter`; `mine=1&filters={"sla_breached":1}` = phiếu CM của tôi vi phạm SLA). `mine=0`/absent → `filters` dict **BYTE-IDENTICAL** baseline (backward-compat tuyệt đối — web-FE `RepairWorkOrderListView` KHÔNG đổi, CM WO gán người khác VẪN hiện cho persona không-self-scope như senior/QA).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | Endpoint riêng `list_my_repair_work_orders` | +1 path (vỡ "path-count UNCHANGED" 46) + nhân đôi pagination/enrich/SLA-derive/contract surface + 2 điểm bảo trì. |
| B | Tạo component `RepairWorkOrderMine` mới | Vô ích — shape giống hệt `WorkOrderMine` (cùng `assigned_to`, cùng int 0|1). Vỡ "0 schema-component mới"; REUSE đúng vì cả PM lẫn CM đều scope `assigned_to`. |
| C | Auto-scope MỌI read theo `assigned_to` qua `permission_query_conditions` | Vỡ view supervisor/QA/manager (`asset_repair_query` trả `""` cho senior để thấy TẤT CẢ CM WO — `permissions.py:117-118`) + đổi security-semantics + count-vs-rows lệch cho persona không-self (memory `asset_list_count_drill_technician`). |
| D | Seed `assigned_to` @service-layer (giống IncidentMine @`_build_incident_filters`) | KHÁC cấu trúc: CM filters là JSON-blob `parse_json` @api (KHÔNG discrete param như imm12). Inject @api SAU `apply_vendor_scope` = 1 dòng, KHÔNG đụng service/repo ⇒ blast-radius nhỏ hơn + đối-xứng ADR-MOBILE-016. |
| E ✅ | Query-param opt-in `mine` (default 0 = cũ) REUSE `WorkOrderMine`, inject `f["assigned_to"]=session.user` @api SAU `apply_vendor_scope`, ANDed vào CÙNG `filters` dict | Blast-radius = 1 nhánh `if mine:` @api + 1 `$ref`; backward-compat; count==rows giữ; KHÔNG đụng service/repo; KHÔNG component mới; codegen sinh client truyền `mine=1` cho tab. |

## Consequences

- **(+)** Contract TRUNG THỰC: `mine=1` ↔ cơ-chế filter `assigned_to` thật; description không còn claim suông "Scope theo user".
- **(+)** `mine=0`/absent UNCHANGED ⇒ blast-radius fence ĐO ĐƯỢC (test: CM WO assigned cho user khác VẪN hiện khi `mine=0`).
- **(+)** `pagination.total == len(data.data)` khi `mine=1` (cùng `filters` dict + cùng `permission_query_conditions` — chống count-vs-rows drift, memory `asset_list_count_drill_technician`).
- **(+)** Path-count GIỮ 46; **0 schema-component mới** (REUSE `WorkOrderMine`) ⇒ `generate_spec` get=232/post=256/total=488 UNCHANGED; `test_oas_d12/d15/d17` RE-VERIFY (KHÔNG re-baseline); `test_mobile_docset` ADR-registration GREEN (ADR này đăng-ký README §1 ADR-table).
- **(+)** **Đối-xứng A2 ĐÓNG TRỌN** — `WorkOrderMine` nay phục vụ 2 op (listPm `assigned_to` MVP-5a + listRepair `assigned_to` MVP-5b); cùng `IncidentMine` (listIncidents `reported_by` MVP-5c) hoàn tất self-scope toàn bộ tab MyWorkOrdersView. Không còn known-gap "mine" cho list-read MVP.
- **(−)** `mine` là **filter ứng-dụng**, KHÔNG phải hàng-rào-bảo-mật: bảo mật read VẪN do DocPerm/permission_query "Asset Repair" (`repair.read` + `asset_repair_query`) + `apply_vendor_scope`. KTV `repair.read` gọi `mine=1` → 200 + chỉ CM WO của mình (với KTV thì `asset_repair_query` ĐÃ tự scope `assigned_to`, nên `mine` thừa nhưng vô hại — AND idempotent); senior gọi `mine=1` → thu hẹp từ "tất cả" về "của tôi" (đây là use-case chính của tab).

**RED-before (BE Bước-4 chứng minh mỗi assert mới):** sau khi BA `$ref` `WorkOrderMine` vào `listRepairWorkOrders.parameters` + sửa description, `test_mobile_oas.py::TC-MOB-OAS-14b` (`_LIST_PARAM_EXPECT[_LIST_REPAIR_PATH]`) ĐỎ (param-set yaml 4 ≠ expected 3) ⇒ tín hiệu BE cập nhật: (1) `api/imm09.py::list_repair_work_orders` thêm `mine: int = 0` + inject `f["assigned_to"]=session.user` SAU `apply_vendor_scope`; (2) `_LIST_PARAM_EXPECT[_LIST_REPAIR_PATH]` +`_WORKORDER_MINE_REF`; (3) `_LIST_LIVE_FN[_LIST_REPAIR_PATH]` +`mine` (introspect `14g` subset — vẫn GREEN, nhưng cập-nhật để khớp ý-định); (4) sửa comment `_LIST_PARAM_EXPECT` (xoá "list_repair KHÔNG có mine — ngoài scope"); (5) +1 TC `test_list_repair_param_set_includes_workordermine` (mirror PM) + reuse `test_workordermine_param_shape` (shape UNCHANGED ⇒ không cần TC shape mới); (6) `_EXPECTED_TEST_COUNT` 437→438; (7) `test_imm09` (mine-filter + fence backward-compat byte-identical mine=0 + count==rows + AND-with-filters) → GREEN. Path-count `TC-MOB-OAS` GIỮ 46; `d12/d15/d17` get/post UNCHANGED.
