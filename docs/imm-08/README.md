# IMM-08 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-08 — Bảo trì định kỳ (PM)** |
| Wave | 1 |
| Trạng thái | Mature |
| Số file hiện có | 14 |
| Cập nhật cuối | 2026-07-27 (**AC-CR-79 [BA spec — Bước-2]** — **whitelist khoá `filters` cho `list_pm_work_orders` = SSoT; khoá lạ nay 400 IN-ENVELOPE thay vì HTTP-500 lộ SQL**. **Bằng chứng probe LIVE 2026-07-27** (`bench --site miyano console`): `imm08.list_work_orders({"khong_ton_tai_abc":"x"})` → `OperationalError (1054, "Unknown column 'tabPM Work Order.khong_ton_tai_abc' in 'WHERE'")`; **và** `{"due_date_from":[…],"due_date_to":[…]}` → 1054 `'tabPM Work Order.due_date_from'` — **web FE gửi ĐÚNG 2 khoá này** (`PMWorkOrderListView.vue:72-73`) ⇒ **bộ lọc khoảng ngày màn PM đang 500 THẬT trên production** (phát hiện mới của vòng này). Cơ chế: `utils/api_handler.py:44-49` CỐ Ý không bắt Exception chung ⇒ bubble → HTTP-500 KHÔNG có `body.success` + lộ tên bảng/cột. **Chốt:** `_ALLOWED_FILTER_KEYS` **16 khoá** ở `services/imm08.py` (12 cột THẬT + 4 khoá ảo `overdue`/`due_before`/`overdue_live`/`search`), cơ chế raise dùng CHUNG `services/shared/filters.py::assert_allowed_filter_keys`; validate **TRƯỚC** `pop_search`/`_normalize_filters` (AC5) và **NGOÀI** `run_rowscoped`. Envelope: HTTP-**200** · `success:false` · `error.code=INVALID_PARAMS` · `http_status=400` · `message_code=VAL-INVALID-FILTER-KEY` · message VI nêu khoá sai + tập hợp lệ. **3 ADR:** FILTERKEY-01 tách OAS param `PmWorkOrderFilters`/`RepairWorkOrderFilters` khỏi `WorkOrderFilters` dùng chung (đang $ref bởi **3 op** — `listCalibrations` IMM-11 chưa whitelist nên không thể nói dối chung 1 mô tả) · FILTERKEY-02 **tái dùng** bucket `INVALID_PARAMS` (KHÔNG đẻ ErrorCode mới, phân biệt bằng `message_code`) · FILTERKEY-03 **Self-Correction** khoảng ngày dùng toán tử `["between",[a,b]]` trên `due_date` (khoá đã whitelist) — **KHÔNG** hợp thức hoá `due_date_from/to` FE tự bịa. **Đóng `CR-70` sổ mobile KÈM CẢI CHÍNH**: CR-70 nói "BE bỏ qua im lặng" là **SAI** (BE CRASH) và ví dụ `asset_ref` của nó là **khoá HỢP LỆ**. File chạm: 04 §4.4 · 05 §14 (canonical) · 06 §7e · 07 §X · README · ledger `docs/imm-09/05 §10.4`. ⚠️ **Slice contract KHÔNG đóng ở Bước-2** (mirror §13.10): guard AC2 import THẲNG hằng số + cite phải trỏ dòng THẬT ⇒ **[BE] land `.py` TRƯỚC** rồi OAS + `cr79_a..h` (8 TC) + 6 counter (+8: **959→967 · 959→967 · 1102→1110 · 1128→1136**, đọc lại trước khi sửa) **cùng vòng (atomic)**; **[FE] cùng vòng** banner-không-thay-bảng + sửa `buildFilters` + **test RENDER**. Backlog kèm bằng chứng: `imm11.list_calibrations` CÙNG lớp lỗi (probe → 1054 `tabIMM Asset Calibration`) — **ngoài phạm vi**) · Trước đó 2026-07-26 (**AC-CR-77 [BE+OAS ĐÃ LAND 2026-07-26 · FE còn lại] — `get_pm_work_order` += `available_actions[]` server-driven 4 CTA**: BE land `services/imm08.py` `_PM_ACTION_SPECS:196` · `_pm_checklist_has_items:212` · `_build_pm_available_actions:231-302` · wire `get_work_order:1058` · 4 điểm chạm §4.3.4 ĐỦ (validate_work_order:530 · reschedule:1501 · assign_technician:1257); OAS `PmWorkOrderDetail.available_actions` `$ref AvailableAction` + guard `TestMobilePmAvailableActionsParity` 9 TC `cr77_a..i` + 4 counter +9 (942→951 · 942→951 · 1085→1094 · 1111→1120). Verify: test_imm08 **182 OK** · test_mobile_oas **951 OK** · test_mobile_docset **9 OK**; mutation-verified 3/3. **BLOCKED-RELOAD** (USER reload gunicorn --preload). Chi tiết spec: mảng ĐÚNG 4 phần tử thứ tự CỐ ĐỊNH `[start_work, submit_result, reschedule, report_major_failure]`, shape `AvailableAction` **TÁI DÙNG** (`{key,label,route,enabled,reason}`, `route=""`) ⇒ OAS giữ **107 paths / 280 schemas**. Đóng **4 lỗ đo được**: D-1 **nút chết** `start_work` (FE gate `allowed_transitions.includes('In Progress')` bật ở 4 status, enforcement `assign_technician` chỉ nhận Open/Overdue) · D-2 **CTA ma `Cancelled`** (đích hợp lệ trong `_PM_VALID_TRANSITIONS` nhưng **0 endpoint**) · D-3 **CTA ẩn** «Hoãn lịch» (web chỉ render trong banner quá hạn) · D-4 predicate nhân bản 4 lần ở FE. `enabled = transition_allowed ∩ has_cap ∩ business_gate`; cap = **ĐÚNG** cap endpoint ghi (`pm.write`/`pm.submit`/`pm.reschedule`/`pm.write`); business_gate CHỈ nhận predicate **thuộc trạng thái phiếu** (`assigned_to` cho start_work · `_pm_checklist_has_items` cho submit_result — **CÙNG** predicate validator `IMM08-CHECKLIST-EMPTY`). **3 ADR:** ADR-IMM08-CTA-01 (action = tập CÓ ENDPOINT, KHÔNG mirror bảng transition) · **ADR-IMM08-CTA-02 Self-Correction** (`from` của reschedule = `RESCHEDULE_ACTION_STATES` = 5 status không-terminal, ⊇ `RESCHEDULE_CTA_STATES` neo bằng invariant; dùng CHUNG advertise ⇔ enforce — dùng đúng `{Open,Overdue}` sẽ regression nút ở `In Progress` + lệch enforcement ở `Pending–Device Busy`/`Halted–Major`) · ADR-IMM08-CTA-03 (business_gate ≠ form-gate; duration/tem/"chấm hết mục" ở lại FE). INV-PMCTA-1..10 + bảng chân trị 9 hàng × 4 cột. `allowed_transitions` **GIỮ NGUYÊN 100%** (superset-only, 0 client gãy). **⚠️ SLICE CONTRACT KHÔNG ĐÓNG Ở BƯỚC-2** (khác CR-74/75/76): A7 buộc cite `services/imm08.py:<dòng> _build_pm_available_actions` nằm TRONG `description` + trỏ đúng vùng AST ⇒ **BE land `.py` TRƯỚC**, rồi OAS + 9 TC `cr77_a..i` + 4 counter (+9: 942→951 / 942→951 / 1085→1094 / 1111→1120) trong CÙNG vòng. File: 05 §13 + §0 · 04 §4.3 + bảng service · 06 §3.4.a · 07 §IX · README · ledger `docs/imm-09/05 §10.4`. **Backlog mở kèm bằng chứng:** B1 không có endpoint "tiếp tục bảo trì" (`Pending`/`Halted → In Progress` advertise mà câm) · B2 nút chết FE `cta-resume` (chỉ refetch) · B3 `report_major_failure` **0 guard status** (`set_values` bypass validate) · B4 `reschedule` xoá tín hiệu `Halted–Major Failure` · nửa CM `RepairWorkOrderDetail` của CR-74m vẫn MỞ → AC-CR-78) · Trước đó 2026-07-25 (CR-74 [BA spec] — **read-gate CHI TIẾT `get_pm_work_order`**: 3 lớp ROLE→EXISTS→ROW (`assert_doctype_read_permission` TRƯỚC `exists` ⇒ 0 existence-oracle · `assert_can_read_doc` = `frappe.has_permission(doc=…)` dispatch hook), 403 trả **TRONG envelope trên HTTP-200** (client hiển thị message, KHÔNG logout). 0 DocType/field/endpoint/param/DocPerm/cap mới. SSoT [ADR-IMM00-LIST-SCOPE §9](../imm-00/ADR-IMM00-LIST-SCOPE.md) D8/D9/D10. **BA slice ĐÓNG (CONTRACT-ONLY):** OAS 4 op cải chính ngữ nghĩa 403 + guard `test_mobile_oas` **+6 TC** `TestMobileDetailReadGate` (923 OK, mutation-verified) + `test_mobile_docset` sync (9 OK). File: 05 §12 + 07 §VIII + README. Handoff → [BE] Bước-4 (dán khuôn vào `services/imm08.py::get_work_order` + TC-01..06 + guard tĩnh **G5**; **cần USER reload gunicorn `--preload`**), [FE] render 403 in-envelope KHÔNG logout) · Trước đó 2026-07-24 (CR-45 — màn "Nhắc việc" mở đường vào phiếu: `getDuePmSchedules` bồi `next_wo_ref`/`next_wo_status` [enrich 1-batch, 9→11 field ADDITIVE, ADR-IMM08-NEXTWO] · `get_pm_work_order` reschedule-CTA overlay `+Pending–Device Busy` cho Open/Overdue [ADR-IMM08-RESCHED-CTA] · `reschedule()` guard terminal Completed/Cancelled→VALIDATION 422 [ADR-IMM08-RESCHED-GUARD, KHÔNG MSG-code mới] · §05 §0.1.5 + §2 + §8 · OAS+shape-guard đóng Bước-2 BA, service `.py`+test BE Bước-4 · reload-only KHÔNG migrate) · 2026-07-19 (BR-08-19 — chống nghiệm-thu-giả PM khi bảng kiểm RỖNG: guard 0-dòng TRƯỚC vòng lặp trong `validate_work_order`, mã MỚI `IMM08-CHECKLIST-EMPTY` ≠ INCOMPLETE · BR-08-20 anti-drop idx `IMM08-CHECKLIST-IDX-UNKNOWN` OPTIONAL · ADR-IMM08-CHECKLIST-EMPTY-01 · reload-only KHÔNG migrate · BE handoff) · 2026-07-18 (CR-24-PM — idempotency `submit_pm_result` qua `client_request_id` cho mobile write-outbox · terminal-state re-read, KHÔNG DocField/migrate · BR-08-18 + ADR-IMM08-IDEMPOTENCY-01 · §05 §4.1 · BE-owned atomic slice CHƯA land) · 2026-07-15 (CR-28b — mobile-contract `getDuePmSchedules` read-list KHÔNG-pagination, màn "Nhắc việc" F8 nửa-PM · §05 §0.1.5 + ADR-IMM08-DUEPM + ADR-MOBILE-054) |
| Khối kiến trúc | C. KHỐI 3 |
| Đợt triển khai | 1 |
| Owner | PTP Khối 2 · Workshop / Nhóm TBYT |

> File index của module IMM-08. Map cũ ↔ template chuẩn theo `docs/template/` (v4.1+).
> **Source docs đã archive tại `docs/architecture/archive/imm-08/`** — 6 file format cũ (IMM-08_*.md) đã được chuyển vào archive sau khi template chuẩn 02–09 được bổ sung đầy đủ.

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File hiện có | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | ✅ Template chuẩn |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) | ✅ Template chuẩn |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | ✅ Template chuẩn |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) | ✅ Template chuẩn (envelope `{success,data}`, 23 endpoints) |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | ✅ Template chuẩn (8 routes, store actions đồng bộ code) |
| 07 §I Test Plan + §III Security + §IV Code quality | [`07_Testing_QA.md`](./07_Testing_QA.md) | ✅ Có |
| 07 §II UAT Script | Archive: `docs/architecture/archive/imm-08/IMM-08_UAT_Script.md` | ✅ Archived |
| 08 Deployment + QMS Mapping | [`08_Deployment.md`](./08_Deployment.md) | ✅ Có |
| 09 User Guide + Release Notes + Traceability | [`09_Release.md`](./09_Release.md) | ✅ Có |

## Files hiện có

**Template chuẩn mới (02–06):**
- [`02_Analysis_Design.md`](./02_Analysis_Design.md) — Phân tích nghiệp vụ + Use Cases + BR + NFR
- [`03_Diagrams.md`](./03_Diagrams.md) — ERD + Class + Sequence + Communication + Package
- [`04_Backend_Design.md`](./04_Backend_Design.md) — DocType + Workflow + Service + API + Scheduler
- [`05_API_Specification.md`](./05_API_Specification.md) — Catalog 23 endpoints + envelope chuẩn `{success,data}`
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — Sitemap 8 routes + Components + Store (đồng bộ code) + i18n

**Template chuẩn mới (07–09):**
- [`07_Testing_QA.md`](./07_Testing_QA.md)
- [`08_Deployment.md`](./08_Deployment.md)
- [`09_Release.md`](./09_Release.md)

**Format cũ (đã archive — xem `docs/architecture/archive/imm-08/`):**
- `IMM-08_API_Interface.md`
- `IMM-08_Functional_Specs.md`
- `IMM-08_Module_Overview.md`
- `IMM-08_Technical_Design.md`
- `IMM-08_UAT_Script.md`
- `IMM-08_UI_UX_Guide.md`

## Roadmap chuẩn hóa

- [x] Bổ sung **`02_Analysis_Design.md`** — Phân tích nghiệp vụ + Use Cases + BR + NFR (template chuẩn)
- [x] Bổ sung **`03_Diagrams.md`** — ERD + Class + Sequence + Communication + Package (template chuẩn)
- [x] Bổ sung **`04_Backend_Design.md`** — DocType + Workflow + Service + Scheduler + Migration (template chuẩn)
- [x] Bổ sung **`05_API_Specification.md`** — API Catalog 23 endpoints + envelope `{success,data}` chuẩn AssetCore
- [x] Bổ sung **`06_Frontend_Design.md`** — Sitemap 8 routes + Mockup + Components + Store (đồng bộ code) + i18n (template chuẩn)
- [x] Bổ sung **`07_Testing_QA.md`** — Test plan (unit/integration/coverage) + Security review + Code quality
- [x] Bổ sung **`08_Deployment.md`** — Deployment plan + QMS Mapping (NĐ98/WHO HTM) + Cấu hình môi trường
- [x] Bổ sung **`09_Release.md`** — User guide tiếng Việt + Release notes + Traceability matrix

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm08.py` · `assetcore/api/imm08.py`
- Codebase ground truth (FE): `frontend/src/types/imm08.ts` · `frontend/src/api/imm08.ts`

---

*Module index — auto-generated khi migration. Khi update file thực tế, manual sync README này.*
