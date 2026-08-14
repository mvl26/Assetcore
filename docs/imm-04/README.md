# IMM-04 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-04 — Lắp đặt, định danh và kiểm tra ban đầu** |
| Wave | 1 |
| Trạng thái | Mature — có v2 UAT |
| Số file hiện có | 8 |
| Cập nhật cuối | 2026-07-30 (**AC-CR-112** — *Đóng nợ VERIFY của AC-CR-98/106, KHÔNG thiết kế lại*: 4 file test của vòng trước (`test_vendor_scope_intersect` **18** · `test_rowscope_scope_guard` **11** · `test_rowscope_invariant` **28** · `test_rowscope_docperm_gate` **22** `def test_`) là **untracked + CHƯA TỪNG CHẠY** ⇒ mọi bất biến §10.8 đang ở trạng thái **CHƯA CHỨNG MINH**; và nhánh tham số ảo `overdue=1` **đổi shape** predicate dict→**list-form** (`services/imm04.py:1101-1105` → cùng `count_with_or` `:1113` → cùng `get_list` `:1116`) mà **0 TC** phủ dưới persona bị row-scope — TC hiện có (`test_imm04.py:724 TestOverdueSlaLiveInvariant`) chạy dưới **`Administrator`**, vai đọc-tất-cả (`permissions.py:140` trả `""`) ⇒ **không thể ĐỎ** khi row-scope bị bỏ. Chốt: **ADR-IMM00-LIST-SCOPE-06** «test chưa chạy = chưa có bất biến» (bằng chứng = `Ran N tests … OK` module-isolated **+** 1 mutation làm TC ĐỎ) · **ADR-IMM00-LIST-SCOPE-07** bất biến `count == rows` thuộc **HÀM**, áp **mọi shape** filters ⇒ 2 bất biến mới **INV-COMM-SCOPE-5/6** + **hạ cấp** `INV-VENDORSCOPE-4` → **`SMOKE-VENDORSCOPE-4`** (self-correction: doc cũ chọn 1 TC chạy `Administrator` làm bằng chứng cho bất biến chỉ quan sát được dưới row-scope). Ratify 0-dòng-mã: deep-link thiết bị ngoài phạm vi ⇒ **0 dòng, KHÔNG 403** (403 ở đây rò thông tin tồn tại + biến "không có dữ liệu" thành "bạn bị chặn"). Delta test: BE **+2** (`TC-IMM04-OVD-01/02`, class MỚI trong `test_rowscope_invariant.py`; **CẤM** dùng lại fixture `TestCommissioningOneEngineScope:776` vì nó **không** set `reception_date` ⇒ NULL `< cutoff` = FALSE ⇒ vacuous) · FE **+2** (`TC-FE-COMM-SE-07/08`, 8 → ≥10 `it()`; guard nguồn TỔNG = `store.pagination.total` ở `:199/:305/:342`, store giả phải cho `total` **độc lập** `rows.length` — nếu không mutation M4 không ĐỎ). Nghi thức **mutation M1–M4** bắt buộc. Baseline đo TỪ ĐĨA (prompt/STATE stale: FE thực tế **287** file test, không phải 284). **0 đổi OAS ⇒ 0 đổi 3 counter `test_mobile_oas`.** Backlog mở: `AC-CR-113` (`git add` 4 file test — HARD-STOP user) · `AC-CR-114` (dời/nhân bản `TestOverdueSlaLiveInvariant` sang row-scoped). File: 02 §BR-04-25b · 04 §11.1 (+bảng refresh cite) · 05 §20.4 (bổ sung hợp đồng mọi-shape + DRIFT vòng 2) · 06 §11.5 · 07 §IX · SSoT [`../imm-00/ADR-IMM00-LIST-SCOPE.md §11`](../imm-00/ADR-IMM00-LIST-SCOPE.md). Handoff → [BE] `test_rowscope_invariant.py` (append class mới) + chạy 8 module, [FE] `CommissioningListView.scopedEmpty.test.ts` (+2 `it()`)) · Trước đó cùng ngày (**AC-CR-98 + AC-CR-106** — *Ô đếm == nhánh drill cho MỌI persona*: `list_commissioning` (`services/imm04.py:1053`) đếm bằng `frappe.db.count` `:1076` + đọc bằng `frappe.get_all` `:1079` ⇒ **cả hai bỏ qua** `permission_query_conditions` (`hooks.py:444`) ⇒ hai số *khớp nhau* mà **cùng là tổng toàn bảng** ⇒ KTV nhà cung cấp (kiêm `Commissioning User`) đọc được phiếu **ngoài phạm vi** — **rò dữ liệu**, không chỉ lệch số. Chốt: MỘT ENGINE `frappe.get_list` cho cả `total` lẫn `items` (SSoT `count_with_or` `filters.py:236`), giữ nguyên 2 lớp gate ROLE + ROW; `AC Asset` enrich đổi sang `get_list`, 4 lookup nhãn không-row-scoped GIỮ `get_all` (đổi = mất nhãn). Song song `apply_vendor_scope` (`scope.py:150`) đổi **GÁN → GIAO** (dòng vi phạm `:174`) cho **cả 5** call site ⇒ deep-link 1 thiết bị hết bị ghi đè; ngoài phạm vi ⇒ **0 dòng**. Enforce `INV-CONN-27`/`INV-CONN-21` (trước chỉ «khai»); allowlist `_RAW_QUERY_UNGATED_BACKLOG` 17 → **16** (CHỈ-GIẢM). **3 self-correction acceptance:** shape là `{items, pagination}` (không có `res['total']`/`res['records']`) · persona rò = `Vendor Engineer` **+** `Commissioning User` (vendor thuần **không có DocPerm read** ⇒ Error envelope) · "0 hit `get_all`" áp cho DocType **row-scoped**, không phải toàn hàm. SSoT: [`../imm-00/ADR-IMM00-LIST-SCOPE.md §10`](../imm-00/ADR-IMM00-LIST-SCOPE.md) (`ADR-IMM00-LIST-SCOPE-04/05`) · File: 02 §BR-04-25 · 04 §11 · 05 §20.4 (SUPERSEDE ratify sai + refresh cite stale) · 06 §11 · 07 §VIII. Nợ mở: `AC-CR-99`/`107`/`108`/`109`/`110`. Handoff → [BE] `services/imm04.py` + `services/shared/scope.py` + `services/shared/filters.py` (annotation), [FE] empty-state `list-empty-scoped`) · Trước đó 2026-07-27 (**AC-CR-85** — *Cổng G04 «bức xạ» hết gộp SAI 2 domain*: `check_auto_clinical_hold` ghi đè `is_radiation_device=1` cho MỌI phiếu Class C/D ⇒ VR-07 đòi Giấy phép Cục ATBXHN **không thể tồn tại** (deadlock + ép nộp giấy tờ sai vào hồ sơ NĐ98). Chốt **BR-04-17**: predicate SSoT `gate_g04_applies` dùng chung VR-07 + verdict + thẻ · khoá additive `g04_applicable` (`GateStatus` 7→8) · **LUẬT ĐỌC 3 TRẠNG THÁI** · bất biến **INV-G04-1** hai chiều · ma trận không-suy-giảm **12 ô** (không phải 10). Nghĩa vụ Class C/D là **NĐ98 Điều 28-32** do **GW-2/BR-04-08** gác qua IMM-05 — khác hẳn **NĐ 142/2020** về bức xạ. `04 §5.7` + ADR-IMM-04-08/09 · `05 §24.6` · `06 §9b` · `07 §III.4f`. Slice contract OAS + 7 guard `cr85_a..g` đóng ở Bước-2; **BE land Bước-4 ✅** — predicate `services/imm04.py:430-455`, VR-07 `asset_commissioning.py:82-100`, `check_auto_clinical_hold` hết ghi đè cờ, thẻ +`g04_applicable`; `test_imm04` **110 OK** · `test_mobile_oas` **1015 OK** · `test_mobile_docset` **9 OK**, mutation M1–M7 ĐỎ 7/7 (`04 §5.7.6` · `07 §III.4f.4-bis`); đóng mobile CR-58). PREV 2026-07-26 (CR-76 — **Thẻ cổng G01–G06 nói đúng cổng thật**: BR-04-15 (display ⟺ enforcement parity, `g01_waived` additive, `_G03_PASSING` SSoT, G02 = cổng tham khảo) · BR-04-16 (read-gate 3 lớp ROLE→EXISTS→ROW cho `get_gate_status`, 403 in-envelope) · ADR-IMM-04-06/07 · mirror OAS mobile `getGateStatus` đóng nửa CR-53). PREV 2026-07-24 (Fail-path baseline: BR-04-04e/f · BR-04-13 · BR-04-14 · ADR-IMM-04-04/05) |
| Khối kiến trúc | B. KHỐI 2 |
| Đợt triển khai | 1 |
| Owner | PTP Khối 2 · Workshop / Nhóm TBYT · Mạng lưới TBYT nội viện |

> File index của module IMM-04. Map cũ ↔ template chuẩn theo `docs/template/` (v4.1+).
> **Strategy: light-touch** — file 6-doc cũ giữ nguyên làm reference; bổ sung file mới theo template khi cần (xem `docs/template/MIGRATION_GUIDE.md`).

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File hiện có | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) + `IMM-04_Module_Overview.md` + `IMM-04_Functional_Specs.md` | ✅ Có (file mới chuẩn template) |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) + `IMM-04_Technical_Design.md` § Diagrams | ✅ Có (file mới chuẩn template) |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) + `IMM-04_Technical_Design.md` | ✅ Có (file mới chuẩn template) |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) + `IMM-04_API_Interface.md` | ✅ Có (envelope chuẩn `{success, data}`) |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) + `IMM-04_UI_UX_Guide.md` | ✅ Có (file mới chuẩn template) |
| 07 §I Test Plan + §III Security + §IV Code quality | `07_Testing_QA.md` | ✅ Có |
| 07 §II UAT Script | `IMM-04_UAT_Script.md` + `IMM-04_UAT_Script_v2.md` | ✅ Có (v1 + v2) |
| 08 Deployment + QMS Mapping | `08_Deployment.md` | ✅ Có |
| 09 User Guide + Release Notes + Traceability | `09_Release.md` | ✅ Có |

## Files hiện có

### Files chuẩn template mới (v4.1+)
- [`02_Analysis_Design.md`](./02_Analysis_Design.md) — Phân tích nghiệp vụ + Use Case + Functional Specs + NFR
- [`03_Diagrams.md`](./03_Diagrams.md) — ERD + Class Diagram + Sequence Diagram + Package Diagram
- [`04_Backend_Design.md`](./04_Backend_Design.md) — DocType + Workflow + Service + API + Scheduler
- [`05_API_Specification.md`](./05_API_Specification.md) — API Catalog + 34 endpoints + Envelope chuẩn
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — Sitemap + Mockup + Components + Pinia + UX rules

### Files tham chiếu (giữ trong module)
- [`07_Testing_QA.md`](./07_Testing_QA.md) — Test plan + UAT script + Security review
- [`08_Deployment.md`](./08_Deployment.md) — Deployment plan + QMS compliance mapping
- [`09_Release.md`](./09_Release.md) — User guide (VI) + Release notes + Traceability matrix

### Architecture Decision Records (ADR)
- [`ADR-001-asset-qr.md`](./ADR-001-asset-qr.md) — **QR cấp tài sản** (factory QR vòng 1): 6 quyết định kiến trúc (payload `qr_token`, deep-link `/a/<token>`, lifecycle `qr_generated`/`label_printed`, RBAC `asset.read`, backfill, tương thích ngược `internal_tag_qr`) + roadmap A1→A6+B. Schema chi tiết ở `imm-00` §II.1.8 + IMM-04 §8.1.

### Source docs (cũ) đã archive
Source docs (cũ) đã archive tại `docs/architecture/archive/imm-04/`:
- `IMM-04_API_Interface.md`
- `IMM-04_Functional_Specs.md`
- `IMM-04_Module_Overview.md`
- `IMM-04_Technical_Design.md`
- `IMM-04_UAT_Script.md`
- `IMM-04_UAT_Script_v2.md`
- `IMM-04_UI_UX_Guide.md`

## Roadmap chuẩn hóa

- [x] Bổ sung **`07_Testing_QA.md`** — Test plan (unit/integration/coverage) + Security review + Code quality
- [x] Bổ sung **`08_Deployment.md`** — Deployment plan + QMS Mapping (NĐ98/WHO HTM)
- [x] Bổ sung **`09_Release.md`** — User guide tiếng Việt + Release notes + Traceability matrix
- [x] Tạo **`02_Analysis_Design.md`** — theo template chuẩn v4.1+
- [x] Tạo **`03_Diagrams.md`** — ERD, Class, Sequence, Communication, Package diagrams
- [x] Tạo **`04_Backend_Design.md`** — Backend design chuẩn 3-tier
- [x] Tạo **`05_API_Specification.md`** — API Catalog với envelope `{success, data}` chuẩn AssetCore
- [x] Tạo **`06_Frontend_Design.md`** — Frontend design chuẩn Vue 3 + Pinia
- [x] Chuẩn hóa naming `Clinical Release` vs `Clinical_Release` trong code (DONE — workflow/services/types đều dùng space)
- [x] Rename Pinia store `stores/commissioning.ts` → `stores/imm04.ts` (DONE — align convention `immXX.ts`)
- [ ] Thêm DB UNIQUE constraint cho `vendor_serial_no` (Sprint 7)
- [ ] Config Print Format Biên bản Bàn giao (Sprint 7)
- [ ] IMM-08 listener cho `imm04_asset_released` (Sprint 8)

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm04.py` (1697 LOC) · `assetcore/api/imm04.py` (**34** `@frappe.whitelist()` endpoints)
- Codebase ground truth (FE): `frontend/src/types/imm04.ts` · `frontend/src/api/imm04.ts`

---

*Module index — auto-generated khi migration. Khi update file thực tế, manual sync README này.*
