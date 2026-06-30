# ADR-MOBILE-019 — `listCalibrations` scope `technician` qua param opt-in `mine` (**ĐÓNG-NỐT quartet phiếu-của-tôi** sau PM/CM/Incident — tab "Phiếu hiệu chuẩn của tôi" — MyWorkOrdersView › MVP-5d) — contract TRUNG THỰC với cơ-chế thật, summary KHÔNG còn claim "của tôi" suông

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-019 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-29 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-017** (đối-xứng CM `listRepairWorkOrders` — A2-symmetry, REUSE `WorkOrderMine`) · **ADR-MOBILE-016** (PM `listPmWorkOrders` — định nghĩa `WorkOrderMine`) · **ADR-MOBILE-015** (`IncidentMine` `reported_by`) · ADR-MOBILE-001 (g — envelope list-read, C3-split element RIÊNG) · C-LISTREAD (`04-api-contract.md §6.1/§6.2`) · Core Doc IMM-11 `05_API_Specification.md §0.1` + `04_Backend_Design.md §3.x ADR-IMM11-LISTMINE` |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm11.py:71-77`, `assetcore/services/imm11.py:978-1018`, `assetcore/repositories/calibration_repo.py:11`, `assetcore/repositories/base.py:48-76`, `assetcore/services/shared/scope.py:117`, `assetcore/assetcore/doctype/imm_asset_calibration/imm_asset_calibration.json:131`, `assetcore/tests/test_mobile_oas.py`, `assetcore/tests/test_imm11.py`, `assetcore/tests/test_mobile_docset.py`). Contract: [`04-api-contract.md`](./04-api-contract.md). Core Doc IMM-11: `docs/imm-11/05_API_Specification.md §0.1 (listCalibrations — param mine)` + `04_Backend_Design.md §3.x`.

---

## Context

Màn **`MyWorkOrdersView`** (mobile MVP-flow-5) có tab **"Phiếu hiệu chuẩn của tôi"** (MVP-5d) — KTV xem CHỈ các phiếu hiệu chuẩn **giao cho chính mình** (`technician == session.user`). Endpoint tái dùng `assetcore.api.imm11.list_calibrations` (`api/imm11.py:71`).

Đây là **mắt-xích THỨ TƯ — đóng-nốt quartet phiếu-của-tôi** của tab MyWorkOrdersView: ADR-MOBILE-015 đóng `listIncidents` (`reported_by`, MVP-5c), ADR-MOBILE-016 đóng `listPmWorkOrders` (`assigned_to`, MVP-5a), ADR-MOBILE-017 đóng `listRepairWorkOrders` (`assigned_to`, MVP-5b), **ADR này đóng `listCalibrations` (`technician`, MVP-5d)** — đối-xứng A2 self-scope HOÀN TẤT cho cả 4 list-read.

**Lỗi thiết kế gốc (contract nói dối — đối-xứng A2 known-gap):** OpenAPI `listCalibrations` summary `[MVP-5d] Hiệu chuẩn của tôi` ĐÃ hứa hẹn semantics "của tôi", NHƯNG `list_calibrations(filters, page, page_size)` (`api/imm11.py:71`) **KHÔNG có cơ chế** nào scope theo `technician` — chỉ forward `filters` JSON-blob đã `parse_json` + `apply_vendor_scope("Calibration Record")` xuống `svc.list_calibrations`. ⇒ tab "Phiếu hiệu chuẩn của tôi" gọi endpoint này sẽ trả **mọi** Calibration Record mà quyền đọc cho phép (kể cả phiếu giao KTV khác), KHÔNG self-scope. Summary = **claim suông**.

**5-câu-hỏi domain:** (stage HTM) Operation/Maintenance — calibration/performance (WHO HTM); (NĐ98) traceability hiệu chuẩn gắn ĐÚNG KTV thực hiện — chứng chỉ hiệu chuẩn phải truy được người chịu trách nhiệm; (stakeholder) KTV field-tech mobile + Calibration Manager/QA web; (lifecycle event) calibration tạo với `technician` reqd (`services/imm11.py:1052`); (hậu quả nếu data sai) tab hiển thị phiếu người khác → KTV nhầm việc hiệu chuẩn, nhưng **KHÔNG leak quyền** vì read-gating GIỮ DocPerm `calibration.read` + `apply_vendor_scope` — `mine` chỉ là filter hiển thị.

**Cơ-chế hiện hữu (đã VERIFY @source):**
- `list_calibrations` (`api/imm11.py:71`): `f = parse_json(filters, default={})` trong `try/except → _err(...)` (`:72-75`) → `f = apply_vendor_scope(f, "Calibration Record")` (`:76`) → `handle(svc.list_calibrations, f, page, page_size)` (`:77`).
- `svc.list_calibrations(filters, page, page_size)` (`services/imm11.py:978`) → `CalibrationRepo.list(filters=_normalize_list_filters(filters), fields=[…technician…], order_by="scheduled_date desc", …)` (`:979-986`).
- `_normalize_list_filters` (`services/imm11.py:1391`) pass-through key thường (string `technician` → `out["technician"]=v`); CHỈ bọc list value (non-operator) thành `["in",[...]]`.
- `CalibrationRepo(BaseRepository)` DOCTYPE `"IMM Asset Calibration"` (`repositories/calibration_repo.py:11`).
- `BaseRepository.list` (`repositories/base.py:48`): `total = count_with_or(DOCTYPE, filters, or_filters)` (`:65`) + `rows = frappe.get_all(DOCTYPE, filters=filters, …)` (`:67-71`) — **CÙNG** `filters` dict ⇒ count==rows. `list_calibrations` KHÔNG truyền `or_filters` ⇒ `count_with_or` = `frappe.db.count` thuần.
- `technician` là field thật **Link → User, reqd=1** (`imm_asset_calibration.json:131`), đã trả trong list-item (`services/imm11.py:982`) + enrich `technician_name` (`:1015`), set lúc tạo (`services/imm11.py:1052`).
- **KHÁC PM/CM:** Calibration Record **KHÔNG có** `permission_query_conditions` riêng (`hooks.py:388` chỉ có `AC Asset`/`Incident Report`/`Asset Repair`/`PM Work Order`/`Asset Commissioning`/`AC Mobile Device Token` — KHÔNG có Calibration). Read-gating cho calibration = DocPerm `calibration.read` (capability) + `apply_vendor_scope("Calibration Record")` (`scope.py:117` → scope cột `asset` chỉ cho role `Vendor Engineer`). Vì vậy: với KTV không-Vendor, `mine=1` thu hẹp từ "tất cả phiếu đọc được" về "của tôi" = use-case CHÍNH của tab.

## Decision

**Bồi 1 query-param opt-in `mine` (int `0|1`, default `0`) — KHÔNG endpoint mới, KHÔNG đổi shape, REUSE component `WorkOrderMine` (R38/ADR-MOBILE-016), KHÔNG tạo component mới.** Đối-xứng ADR-MOBILE-017 (CÙNG cấu trúc filters JSON-blob @api): inject @api-layer SAU `apply_vendor_scope`. **KHÁC 1 điểm grounded @source: cột scope = `technician` (KHÔNG `assigned_to`)** — vì Calibration Record dùng `technician` (Link User reqd) làm cột KTV phụ-trách, KHÔNG có `assigned_to`.

1. **OpenAPI** — `$ref` `components/parameters/WorkOrderMine` (ĐÃ tồn tại từ R38 — `name:mine`, `in:query`, `required:false`, schema `type:integer default:0 enum:[0,1]`) vào `listCalibrations.parameters` (param-set `{WorkOrderFilters, Page, PageSize}` → **+`WorkOrderMine`** = 4) + generalize `WorkOrderMine.description` PM/CM→PM/CM/CAL (ghi rõ cột scope KHÁC theo list: `assigned_to` WO PM/CM, `technician` Calibration) + sửa `listCalibrations.description` khớp cơ-chế thật (`mine=1 → technician==session.user`, summary đổi "Hiệu chuẩn của tôi"→"Phiếu hiệu chuẩn của tôi"). `WorkOrderMine` nay `$ref`'d bởi 3 op (listPm + listRepair + listCalibrations) ⇒ KHÔNG orphan/dangling. **0 path mới** (path-count GIỮ **47** — thêm param ≠ thêm path), **0 schema-component mới** (REUSE). Component shape int 0|1 UNCHANGED.

2. **API** (`api/imm11.py`) — `list_calibrations(filters: str = "{}", mine: int = 0, page: int = 1, page_size: int = 20)`: `mine: int = 0` chèn GIỮA `filters`↔`page` (mirror `imm08.py:29` / `imm09.py:22`). SAU `f = apply_vendor_scope(f, "Calibration Record")` (`:76`), trước `handle(svc.list_calibrations, …)`, thêm `if int(mine or 0): f["technician"] = frappe.session.user`. ⇒ `technician` AND vào `filters` dict trước khi xuống service/repo. Read-gating GIỮ qua DocPerm `calibration.read` + `apply_vendor_scope` (KHÔNG thêm in-handler cap-403).

3. **Service/Repo** — **KHÔNG đụng** `services/imm11.py`/`repositories/`. `_normalize_list_filters` pass-through `technician` (string → nhánh `else`, không bọc `in`); `CalibrationRepo.list` (BaseRepository) đếm `total` + lấy `rows` trên CÙNG `filters` (đã có `technician`) ⇒ **INVARIANT count==rows** khi `mine=1`.

**Hành vi:** `mine=1` → CHỈ Calibration Record `technician==session.user`, AND với mọi filter trong blob (vd `mine=1&filters={"status":"Scheduled"}` = phiếu hiệu chuẩn của tôi đang chờ làm; `mine=1&filters={"calibration_type":"External"}` = phiếu external của tôi). `mine=0`/absent → `filters` dict **BYTE-IDENTICAL** baseline (backward-compat tuyệt đối — web-FE `CalibrationListView` KHÔNG đổi, phiếu giao KTV khác VẪN hiện cho persona không-self-scope như Calibration Manager/QA).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | Endpoint riêng `list_my_calibrations` | +1 path (vỡ "path-count UNCHANGED" 47) + nhân đôi pagination/enrich (asset_name/lab_name/technician_name)/contract surface + 2 điểm bảo trì. |
| B | Tạo component `CalibrationMine` mới | Vô ích — shape giống hệt `WorkOrderMine` (cùng int 0|1, cùng semantics self-scope opt-in). Vỡ "0 schema-component mới"; REUSE đúng vì chỉ CỘT scope khác (assigned_to/technician), shape param y hệt — column-mapping là chuyện @api-handler, KHÔNG phải shape contract. |
| C | Inject `assigned_to` (mirror PM/CM literal) | SAI source — Calibration Record KHÔNG có cột `assigned_to`; KTV phụ-trách = `technician` (Link User reqd, `:131`). Inject `assigned_to` → filter trên cột không tồn tại → 0 row (hoặc Frappe lỗi field). PHẢI `technician`. |
| D | Auto-scope MỌI read theo `technician` qua `permission_query_conditions` | Calibration Record HIỆN KHÔNG có permission_query_conditions; thêm mới sẽ vỡ view Calibration Manager/QA (cần thấy TẤT CẢ phiếu) + đổi security-semantics + count-vs-rows lệch cho persona không-self (memory `asset_list_count_drill_technician`). `mine` = filter ứng-dụng opt-in, KHÔNG đụng tầng permission. |
| E | Seed `technician` @service-layer (giống IncidentMine @`_build_incident_filters`) | KHÁC cấu trúc: CAL filters là JSON-blob `parse_json` @api (KHÔNG discrete param như imm12). Inject @api SAU `apply_vendor_scope` = 1 dòng, KHÔNG đụng service/repo ⇒ blast-radius nhỏ hơn + đối-xứng ADR-MOBILE-016/017. |
| F ✅ | Query-param opt-in `mine` (default 0 = cũ) REUSE `WorkOrderMine`, inject `f["technician"]=session.user` @api SAU `apply_vendor_scope`, ANDed vào CÙNG `filters` dict | Blast-radius = 1 nhánh `if mine:` @api + 1 `$ref`; backward-compat; count==rows giữ; KHÔNG đụng service/repo; KHÔNG component mới; codegen sinh client truyền `mine=1` cho tab. |

## Consequences

- **(+)** Contract TRUNG THỰC: `mine=1` ↔ cơ-chế filter `technician` thật; summary không còn claim "của tôi" suông.
- **(+)** `mine=0`/absent UNCHANGED ⇒ blast-radius fence ĐO ĐƯỢC (test: Calibration Record giao KTV khác VẪN hiện khi `mine=0`).
- **(+)** `pagination.total == len(data.data)` khi `mine=1` (cùng `filters` dict — `count_with_or` + `get_all` của `CalibrationRepo.list`; KHÔNG permission_query riêng để lệch — chống count-vs-rows drift, memory `asset_list_count_drill_technician`).
- **(+)** Path-count GIỮ 47; **0 schema-component mới** (REUSE `WorkOrderMine`) ⇒ `generate_spec` get/post/total UNCHANGED; `test_oas_d12/d15/d17` RE-VERIFY (KHÔNG re-baseline); `test_mobile_docset` ADR-registration GREEN (ADR này đăng-ký README §ADR-table).
- **(+)** **Quartet phiếu-của-tôi ĐÓNG TRỌN** — `WorkOrderMine` nay phục vụ 3 op (listPm `assigned_to` MVP-5a + listRepair `assigned_to` MVP-5b + listCalibrations `technician` MVP-5d); cùng `IncidentMine` (listIncidents `reported_by` MVP-5c) hoàn tất self-scope toàn bộ tab MyWorkOrdersView. Không còn known-gap "mine" cho list-read MVP.
- **(+)** Tiền-lệ "1 component `WorkOrderMine`, cột scope per-op khác nhau" được ghi tường minh — param shape (int 0|1) là contract, column-mapping (`assigned_to`/`technician`/`reported_by`) là chuyện @api-handler.
- **(−)** `mine` là **filter ứng-dụng**, KHÔNG phải hàng-rào-bảo-mật: bảo mật read VẪN do DocPerm `calibration.read` + `apply_vendor_scope("Calibration Record")`. Calibration KHÔNG có `permission_query_conditions` riêng → persona không-Vendor (KTV/Manager/QA) đọc theo cap; `mine=1` chỉ thu hẹp hiển thị về "của tôi", KHÔNG cấp/thu quyền.

**RED-before (BE Bước-4 chứng minh mỗi assert mới):** sau khi BA `$ref` `WorkOrderMine` vào `listCalibrations.parameters` + generalize description, `test_mobile_oas.py` `_LIST_PARAM_EXPECT[list_calibrations]` ĐỎ (param-set yaml 4 ≠ expected 3) ⇒ tín hiệu BE cập nhật: (1) `api/imm11.py::list_calibrations` thêm `mine: int = 0` GIỮA filters↔page + inject `f["technician"]=session.user` SAU `apply_vendor_scope`; (2) `_LIST_PARAM_EXPECT[list_calibrations]` +`WorkOrderMine`-ref; (3) `_LIST_LIVE_FN[list_calibrations]` +`mine` (live-sig parity `['filters','mine','page','page_size']`); (4) +2 TC `TestMobileListReadContract` (`test_list_calibrations_param_set_includes_workordermine` + `test_calibrations_workordermine_shape`, mirror PM/CM); (5) `_EXPECTED_TEST_COUNT` 447→449; (6) `test_imm11` (+mine TC: scope technician==user qua fixture 2 user / fence backward-compat byte-identical mine=0 / AND-with-status / count==rows) → GREEN; (7) `test_mobile_docset` `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 447→449 + `_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL` +2 + `cal_mine_listread_delta=2` transition narrative (pre_fc3_six baseline=191 GIỮ). Path-count `TC-MOB-OAS` GIỮ 47; `d12/d15/d17` get/post UNCHANGED (param ≠ operation mới).
