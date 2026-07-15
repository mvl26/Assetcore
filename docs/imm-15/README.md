# IMM-15 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-15 — Spare Parts Inventory Tracking (Theo dõi tồn kho phụ tùng y tế)** |
| Wave | 2 — IMPLEMENTED (feature/hieuc/wave-2) |
| Trạng thái | ✅ Stable — BE + FE đã merge; chờ UAT |
| Số file | 9 (README + 02-09; nguồn gốc đã archive) |
| Cập nhật cuối | 2026-07-14 (vòng 42, CR-29b · Mobile Trục B MỞ NHÁNH IMM-15 **F9-DETAIL**: curate `getAllocation` (`imm15.get_allocation`) — phiếu cấp phát CHI TIẾT (header + `items[]` child + `allowed_transitions[]` CTA) vào OAS mirror; DETAIL-sibling của `listAllocations` (vòng đây, ADR-MOBILE-049). CONTRACT-ONLY (0 `.py`/reload/migrate — BE LIVE @api/imm15.py:66 · service @services/imm15.py:224). 2 schema `SpareAllocationItem`(13)/`SpareAllocationDetail`(27) — **Self-Correct: CẢ HAI `additionalProperties:true` OPEN** (service `doc.as_dict()` mirror `CalibrationDetail`/`TransferDetail`, KHÔNG closed như acceptance) + inline `oneOf` (KHÔNG response-component) + `used_for`/`return_condition` string-nullable KHÔNG enum (Select leading-blank). path 80→81 · c5 69→70 · _PARITY 69→70 · _MVP_LIST_ENVELOPE KHÔNG đổi — **ADR-MOBILE-050**, 05 §3.0; vòng 16, CR-WF-15-ALLOC: `get_allocation` emit `allowed_transitions` SSoT `_allocation_allowed_transitions` + INVARIANT `TestAllocationAllowedTransitions` dual-track — ADR-IMM-15-10, 04 §VI.1.1; vòng 23: BR-15-17 + VR-15-17 — low-stock + forecast `current_qty` so theo tồn **KHẢ DỤNG** `(qty_on_hand − reserved_qty)` qua `LOW_STOCK_COND` SoT (đảo round-3 dùng tồn vật lý) → bin reserved-full (available=0) báo low + Reorder; biểu thức RAW bắt oversell; `_sum_part_stock` 1 aggregate no-N+1; 3 con số card==drill==count đồng nhất — 04 §II.A/§III.6.2; vòng 21: BR-15-11 + VR-15-16 — `check_expiring_batches` predicate cửa sổ 30 ngày SoT `EXPIRY_WINDOW_DAYS`, fix dict-key trùng `expiry_date` + naming-contract `batch_no` (≠ batch_code) + gate `table_exists("IMM Spare Batch")` (KHÔNG prefix `tab`) + guard `qty_on_hand>0` — 04 §VII; vòng 11: VR-15-15 data-contract `historical_consumption_12m` = 12 tháng CỐ ĐỊNH, tách khỏi `lookback_months` — 04 §III.6.1, fix bug horizon=6 SAI 2×; +VR-15-07 reorder≥safety có test bắt buộc; vòng 2: BR-15-16 line_value/total_value lifecycle-aware SoT — 04 §III-bis.8; vòng 1: BR-15-15 số-xuất==số-duyệt — 04 §III-bis.7; vòng 34: reservation ledger SoT — 04 §III-bis, VR-15-14) |
| Khối kiến trúc | C. KHỐI 3 |
| Đợt triển khai | 2 |
| Owner | Kho trung tâm & Kho vận |

> ✅ Module đã triển khai trên branch `feature/hieuc/wave-2`. AC Inventory Backbone (Wave 1) LIVE. Banners PLANNED trong file 02–09 đã được gỡ (Wave-2 Sync Pass 2026-05-14).

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | ✅ Đã tạo |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) | ✅ Đã tạo |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | ✅ Đã tạo |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) | ✅ Đã tạo (envelope `{success, data}`) |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | ✅ Đã tạo |
| 07 Testing_QA | [`07_Testing_QA.md`](./07_Testing_QA.md) | ✅ Đã tạo |
| 08 Deployment | [`08_Deployment.md`](./08_Deployment.md) | ✅ Đã tạo |
| 09 Release | [`09_Release.md`](./09_Release.md) | ✅ Đã tạo |

## Files nguồn gốc (Archived)

> Source docs (cũ) đã archive tại [`docs/architecture/archive/imm-15/`](../../architecture/archive/imm-15/).  
> Không tham chiếu trực tiếp — dùng các file template chuẩn `02_`…`09_` ở trên.

| File (archive) | Nội dung |
|---|---|
| `IMM-15_API_Interface.md` | API gốc (BA draft — envelope cũ) |
| `IMM-15_Functional_Specs.md` | FR/NFR/User Stories |
| `IMM-15_Module_Overview.md` | Architecture/DocTypes/BRs |
| `IMM-15_Technical_Design.md` | Schemas/Algorithms/Hooks |
| `IMM-15_UAT_Script.md` | 14 kịch bản UAT |
| `IMM-15_UI_UX_Guide.md` | 12 màn hình/wireframes |

## Roadmap chuẩn hóa

- [x] Tạo `02_Analysis_Design.md`
- [x] Tạo `03_Diagrams.md`
- [x] Tạo `04_Backend_Design.md`
- [x] Tạo `05_API_Specification.md` (với AssetCore envelope `{success, data}`)
- [x] Tạo `06_Frontend_Design.md`
- [x] Tạo `07_Testing_QA.md`
- [x] Tạo `08_Deployment.md`
- [x] Tạo `09_Release.md`

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm15.py` · `assetcore/api/imm15.py`
- Codebase ground truth (FE): `frontend/src/types/imm15.ts` · `frontend/src/api/imm15.ts`
- AC Backbone prerequisite: `assetcore/api/inventory.py` · `assetcore/services/inventory.py`

## Kiến trúc đặc biệt

IMM-15 xây trên **AC Inventory Backbone** (Wave 1 LIVE):

| RULE | Nội dung |
|---|---|
| RULE-F01 | KHÔNG tạo DocType phụ tùng mới — dùng `AC Spare Part` |
| RULE-F02 | KHÔNG tạo bảng tồn song song — dùng `AC Spare Part Stock` |
| RULE-F03 | Mọi movement phải sinh `AC Stock Movement` (submitted) |
| RULE-F04 | IMM DocType chỉ LINK qua `stock_movement_ref` — không ghi thẳng vào stock |

---

*Module IMM-15 — Wave 2 Implemented. Cập nhật 2026-07-13.*

> **Delta vòng 16 (2026-07-13) — CR-WF-15-ALLOC · Surface `allowed_transitions` cho Spare Allocation (Trục A · CTA-ẩn-câm):** `get_allocation` chưa emit `allowed_transitions` → FE (nếu build AllocationDetail) buộc hardcode `allocation_status===`. Fix (spec-before-code, BA doc-only, ADR-IMM-15-10 đối xứng ADR-IMM-15-08 Cycle Count): (1) SSoT `_ALLOCATION_ALLOWED_TRANSITIONS` (dict status→**next-state strings**, KHÔNG token; **KHÔNG role-gate**) + accessor `_allocation_allowed_transitions(status)` (`.get`→0 KeyError; keys==6 enum) + emit trong `get_allocation` — 04 §VI.1.1, 05 §3.0, BR-15-19; (2) **INVARIANT `TestAllocationAllowedTransitions`** dual-track `SVC⊆WF∪SHORTCUT` + `WF⊆SVC∪EXCEPTION` RED→GREEN — 07 §III.4c; (3) FE `AllocationDetail += allowed_transitions: string[]` (imm15.ts) — 06 §II.5. **Self-Correct vs acceptance:** EXCEPTION deferred = **3 cạnh** (acceptance sót `Returned→Issued` "Đóng phiếu" re-close) + **1 SHORTCUT** `Approved→Issued` (`issue_allocation` guard nhận APPROVED @318, đi tắt Pick chain chưa-wire — "0 bypass" bất khả, phải khai `_ALLOCATION_SHORTCUT_EDGES` y hệt §VI.2.1 vì allocation status-driven KHÔNG `apply_workflow`). Pick chain (`Approved→Picked→Issued`) + re-close GIỮ deferred. **Backlog:** wire `pick_allocation`/`close_allocation`; build `AllocationDetailView.vue` + wrapper `cancelAllocation` (endpoint CÓ, imm15.ts CHƯA). **KHÔNG đụng workflow json/fixtures** → `test_workflows`+`test_workflow_admin_override` GREEN, 0 migrate.

> **Delta vòng 2 (2026-07-01) — Surface Cycle Count UI:** thêm endpoint **`get_cycle_count`** (detail + `allowed_transitions` capability-aware — 05 §3.6a, ADR-IMM-15-06) + surface FE (view/route `/inventory/cycle-counts` + `:name`, nav "Kiểm kê tồn kho", StoreDashboard link — 06 §II.8bis, ADR-IMM-15-07). BE lifecycle create/submit/post đã có. ⚠️ Child LIVE = `IMM Cycle Count Item` (orphan `IMM Stock Cycle Count Item` cần BE dọn). Endpoint FE store: `submitCycleCount` (KHÔNG `save_counted_qty`).

> **Delta vòng 12 (2026-07-12) — CR-WF-15-AUDIT · Bịt silent-audit-loss (Trục A):** 6 slug domain IMM-15 emit KHÔNG ∈ `IMM Audit Trail.event_type` Select ⇒ `log_audit_event().insert()` raise ValidationError, bị try/except NUỐT ⇒ **0 dòng audit** tại `post_cycle_count` (`cycle_count_posted`) + 5 allocation transition @258/282/361/409/450 (`allocation_*`, except @1374 = **bare `pass`** câm hoàn toàn). Fix (spec-before-code, BA doc-only, ADR-IMM-15-09 **Supersedes** khuyến nghị vòng 11 "đổi post→State Change"): (1) **REGISTER 6 slug** vào `imm_audit_trail.json` field event_type (parity sibling `audit_*`/`competency_*`; KHÔNG collapse — giữ granularity provenance NĐ98/WHO HTM) + `bench migrate` sync — 04 §IV-AUDIT, 08 §Schema-note; (2) **SSoT constant** `IMM15_AUDIT_EVENT_TYPES` (frozenset 6) + tuple `_ALLOCATION_AUDIT_ACTIONS` — 04 §IV-AUDIT; (3) bare `pass`→`frappe.log_error` @`_write_allocation_audit` (non-blocking best-effort, KHÔNG raise→rollback) — D3; (4) **INVARIANT** `TestImm15AuditEventTypeParity` (`IMM15_AUDIT_EVENT_TYPES ⊆ Select`) RED→GREEN + TC-15-AUD-01..09 (per-transition 1-row đúng slug + ref/actor + bare-pass regression) — 07 §III.4b; (5) BR-15-10 refine — 02 §IV.2. **Backlog (ngoài scope):** IMM-16 emit `internal_audit_closed` vs Select `audit_closed` — nghi audit-loss đối xứng. **KHÔNG đụng workflow json** → `test_workflow_admin_override` GREEN.

> **Delta vòng 11 (2026-07-11) — CR-WF-15-CC · Surface "Sửa đếm lại" (Reviewed→Counting):** đối soát SSoT `_cycle_allowed_transitions` ⇄ `imm_15_cycle_count_workflow.json` — cạnh `Reviewed→Counting` bị **ẩn câm** (INVARIANT RED). Fix (spec-before-code, BA doc-only): (1) chuẩn hoá 3 map `_CYCLE_VALID_TRANSITIONS`/`_CYCLE_TOKEN_TARGET`/`_CYCLE_TOKEN_CAP` → `[Reviewed]=["Recount","Post"]` — 04 §VI.2.1, ADR-IMM-15-08; (2) endpoint **`recount_cycle_count(count_name, reason)`** cap `inventory.submit`, reason bắt buộc (422 `IMM15_RECOUNT_REASON_REQUIRED`), status≠Reviewed→409, guest→401 — 05 §3.7c; (3) INVARIANT `TestCycleCountAllowedTransitions` (INV-1 `SVC⊆WF∪SHORTCUT` + INV-2 `WF⊆SVC∪EXC`) RED→GREEN + `TestCycleCountRecount` TC-15-RECOUNT-01..05 — 07 §III.4a; (4) FE nút "Sửa đếm lại" server-driven `allowed_transitions.includes('Recount')` + modal reason — 06 §II.8bis; (5) BR-15-18 — 02 §IV.2. **Self-Correct:** token SSoT là hành động (`Submit/Post/Recount`) KHÔNG next-state (doc-06/05 cũ sai) · chữ ký `_cycle_allowed_transitions(status)` 1-arg · **BUG pre-existing** `post_cycle_count` audit `event_type="cycle_count_posted"` ∉ Select → 0 record persist (recount dùng `"State Change"` hợp lệ; khuyến nghị BE đổi post cùng lúc). **KHÔNG đụng workflow json** → `test_workflow_admin_override` GREEN.
