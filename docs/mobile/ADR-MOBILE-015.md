# ADR-MOBILE-015 — `listIncidents` scope `reported_by` qua param opt-in `mine` (**ĐÓNG known-gap A2** cho tab "Báo hỏng của tôi" — MyWorkOrdersView › MVP-5c) — contract TRUNG THỰC với cơ-chế thật, KHÔNG còn claim suông "scope reported_by"

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-015 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-28 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | ADR-MOBILE-001 (g — envelope list-read 2 rows-key) · C-LISTREAD (`04-api-contract.md §6.1/§6.2/§8.4`) · Core Doc IMM-12 `05_API_Specification.md §2 #3` + `ADR-IMM12-05` |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm12.py`, `assetcore/services/imm12.py`, `assetcore/tests/test_mobile_oas.py`, `assetcore/tests/test_imm12.py`, `assetcore/tests/test_mobile_docset.py`). Contract: [`04-api-contract.md`](./04-api-contract.md). Core Doc IMM-12: `docs/imm-12/05_API_Specification.md §2 #3 (list_incidents — filter mine)` + `ADR-IMM12-05`.

---

## Context

Màn **`MyWorkOrdersView`** (mobile MVP-flow-5) có tab **"Báo hỏng của tôi"** — KTV xem CHỈ các sự cố do **chính mình** báo. Endpoint tái dùng `assetcore.api.imm12.list_incidents` (`api/imm12.py:197`).

**Lỗi thiết kế gốc (A2 known-gap — contract nói dối):** OpenAPI `listIncidents` summary `[MVP-5c] Sự cố của tôi` + description CLAIM "scope reported_by", NHƯNG `list_incidents(status, severity, asset, open, page, page_size)` (`services/imm12.py:746`) **KHÔNG có cơ chế** nào scope theo `reported_by` — chỉ filter `status`/`severity`/`asset`/`open`. ⇒ tab "Báo hỏng của tôi" gọi endpoint này sẽ trả **mọi** incident mà quyền đọc cho phép, KHÔNG self-scope. Contract = **claim suông** (`04-api-contract.md §6.2` ghi rõ "Scope reported_by (A2 finding) vẫn là known-gap hành vi — Phase-C kế").

`_build_incident_filters(status, severity, asset, open_only)` (`services/imm12.py:310`) build `extra` dict rồi rẽ **3 nhánh**: `if status: extra["status"]=status; return extra` (**return-sớm**, ưu tiên status) · `if open_only: return open_incident_filter(extra)` · `return extra`. `list_incidents` (`:746`) đếm `total = frappe.db.count(_DT_INCIDENT, filters)` (`:755`) + lấy `rows = frappe.get_all(_DT_INCIDENT, filters=filters, …)` (`:757`) — **cùng** `filters` dict ⇒ count==rows.

`reported_by` field tồn tại trên `Incident Report` (đã trả trong list-item `:761`, set bởi `report_incident` `services/imm12.py:366,372` = `reported_by or frappe.session.user`).

## Decision

**Bồi 1 query-param opt-in `mine` (int `0|1`, default `0`) — KHÔNG endpoint mới, KHÔNG đổi shape.**

1. **OpenAPI** — thêm `components/parameters/IncidentMine` (`name:mine`, `in:query`, `required:false`, schema `type:integer default:0 enum:[0,1]` — **mirror `IncidentOpen`**, né int-vs-bool trap Open#1) + `$ref` vào `listIncidents.parameters` (param-set 5→**6**) + sửa `description` khớp cơ-chế thật (KHÔNG còn claim suông). `IncidentMine` `$ref`'d NGAY ⇒ KHÔNG orphan. **0 path mới** (path-count GIỮ **46** — thêm param ≠ thêm path), **0 schema-component mới**.

2. **Service** (`services/imm12.py`) — `_build_incident_filters(status, severity, asset, open_only=False, reported_by="")`: seed `if reported_by: extra["reported_by"] = reported_by` **TRƯỚC** quyết định nhánh ⇒ `reported_by` AND vào **CẢ 3 nhánh** (kể cả status return-sớm). `list_incidents(…, mine=0)` resolve `reported_by = frappe.session.user if int(mine or 0) else ""` → truyền xuống. `total` + `rows` GIỮ cùng `filters` ⇒ **INVARIANT count==rows** khi `mine=1`.

3. **API** (`api/imm12.py`) — `list_incidents(…, mine: int = 0, …)` forward `mine=int(mine or 0)`. Guest-guard `:212` **UNCHANGED** (Guest → 401 in-handler `_err`). KHÔNG thêm in-handler cap-403.

**Hành vi:** `mine=1` → CHỈ incident `reported_by==session.user`, AND với `status`/`severity`/`asset`/`open` (vd `mine=1&open=1` = sự cố của tôi đang mở; `mine=1&status=Cancelled` = sự cố của tôi đã huỷ, status return-sớm vẫn mang `reported_by`). `mine=0`/absent → `filters` **BYTE-IDENTICAL** với trước (backward-compat tuyệt đối — web-FE `IncidentListView` KHÔNG đổi).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | Endpoint riêng `list_my_incidents` | +1 path (vỡ "path-count UNCHANGED" 46) + nhân đôi pagination/enrich/contract surface + 2 điểm bảo trì. |
| B | Auto-scope MỌI read theo `reported_by` qua `permission_query_conditions` | Vỡ view manager/QA (cần thấy TẤT CẢ incident) + đổi security-semantics + count-vs-rows lệch cho persona không-self. |
| C ✅ | Query-param opt-in `mine` (default 0 = cũ) ANDed vào cùng `filters` dict | Blast-radius = 1 nhánh `if mine:` + 1 param; backward-compat; count==rows giữ; codegen sinh client truyền `mine=1` cho tab. |

## Consequences

- **(+)** Contract TRUNG THỰC: `mine=1` ↔ cơ-chế filter `reported_by` thật; description không còn claim suông.
- **(+)** `mine=0`/absent UNCHANGED ⇒ blast-radius fence ĐO ĐƯỢC (test: incident reporter khác VẪN hiện khi `mine=0`).
- **(+)** `pagination.total == len(items)` khi `mine=1` (cùng `filters` dict — chống count-vs-rows drift, memory `asset_list_count_drill_technician`).
- **(+)** Path-count GIỮ 46; KHÔNG schema mới ⇒ `test_mobile_docset` path-count + ADR-registration GREEN (ADR này đăng-ký README).
- **(−)** `mine` là **filter ứng-dụng**, KHÔNG phải hàng-rào-bảo-mật: bảo mật read VẪN do DocPerm/permission_query "Incident Report" (`corrective.read`) đảm trách. KTV `corrective.read` gọi `mine=1` → 200 + chỉ incident của mình, KHÔNG leak reporter khác (vì `reported_by` tường minh).
- **(−)** Scope `assigned_to` cho PM/CM (`listPmWorkOrders`/`listRepairWorkOrders`) VẪN known-gap — Phase-E bồi param đối xứng (`mine`/`assigned`).

**RED-before (BE Bước-4 chứng minh mỗi assert mới):** sau khi BA bồi `IncidentMine` vào yaml, `test_mobile_oas.py::TC-MOB-OAS-14b` (`_LIST_PARAM_EXPECT[listIncidents]`) ĐỎ (param-set 6 ≠ expected 5) ⇒ tín hiệu BE cập nhật `_INCIDENT_PARAM_REFS` (+`IncidentMine`) + thêm assert shape `IncidentMine` (14d) + impl service/api + test_imm12 (mine-filter + fence + count==rows + AND-status/open) → GREEN. Path-count `TC-MOB-OAS` GIỮ 46.
