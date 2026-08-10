# PLAN — Core Refinement: kế hoạch & chia task

| Mục | Giá trị |
|---|---|
| Spec | `SPEC_core_refinement_frappe_native.md` |
| ADR nền | `ADR-CORE-01_workflow_is_ssot.md` (supersede `ADR_status_vs_workflow_state.md`) |
| Ngày | 2026-07-22 · Branch `feature/hieuc/core-refinement` |
| Trạng thái | **Phase 0+1 XONG · Phase 2 mới tới T11 — dừng ở cổng người duyệt (Checkpoint D)** |

## 0. Tiến độ thực thi (cập nhật 2026-07-22)

| Task | Trạng thái | Bằng chứng |
|---|---|---|
| T01 ADR + doc nền | ✅ | 3 file `docs/architecture/` |
| T02 guard connection graph | ✅ | `tests/test_doctype_connectivity.py` — 8 test, 5 guard-bites xanh |
| T03 guard trục trạng thái | ✅ | `tests/test_state_axis_invariant.py` — 8 test, 5 guard-bites xanh; ngân sách khởi điểm **105** chỗ ghi tay/15 file |
| T04 dashboard AC Asset | ✅ | 5 nhóm / 19 mục; guard 12→11 |
| T05 API `get_connections` | ✅ | `api/connections.py` + 11 test xanh; OAS 511→512 (ledger + 5 suite OAS xanh, gồm 882 test mobile) |
| T06 FE `RelatedRecords` | ✅ | component + client + guard link-chết; wire `AssetDetailView` |
| T07 4 hub vận hành | ✅ | PM WO / Asset Repair / Calibration / Incident; guard 11→7 |
| T08 wire 4 màn chi tiết | ✅ | PM/CM/Calibration/Incident Detail |
| T09 7 hub còn lại | ✅ | **TC-CONN-1 + TC-CONN-2 XANH** — 12/12 hub, mọi mục phân giải về field thật |
| T10 helper `transition()` | ✅ | `services/shared/state.py` + `tests/test_shared_state.py` |
| T11 patch backfill | ✅ (viết, **chưa chạy**) | `patches/v3_2/011_backfill_workflow_state.py` + test chạy đôi |
| T21 desk affordances | ✅ | 12 hub có `title_field`/`search_fields`/`in_global_search`; **`test_doctype_connectivity` 9/9 XANH** (thêm test chặn metadata làm hỏng `bench migrate`) |
| T21-bis khoá trục thứ hai | ✅ | 5 doctype IMM-12/15/16 `status` → `read_only`; **`test_state_axis_invariant` 10/10 XANH** |
| T12-pre-A độ phủ vai trò (chiều A) | ✅ | `setup/backfill_workflow_domain_roles` — **138 transition / 16 workflow**, ghi cả 3 nơi (workflow nguồn · fixtures · site live), idempotent; 16/18 khoảng trống đóng |
| **T12-pre-B transition không thực thi được** | 🔴 **CHẶN T12–T17 — cần USER quyết** | 61 cặp / 17 workflow — xem §4-ter |
| T12–T17 cắt module sang engine | ⏸ **bị chặn** bởi T12-pre-B | + cần USER reload gunicorn (Checkpoint D) |
| T18–T20 toàn vẹn tham chiếu | ⏸ | phụ thuộc Checkpoint D |

> ⚠️ **Metadata JSON chỉ vào CSDL khi USER chạy `bench migrate`.** Guard xanh = nguồn sự
> thật đã khai đúng và đã được kiểm là migrate sẽ không từ chối; hiệu lực trên site vẫn
> chờ lệnh migrate của người vận hành.

## 4-bis. T12-pre — độ phủ vai trò của transition (điều kiện tiên quyết, CHẶN T12–T17)

Hôm nay service ghi thẳng `doc.status` nên chỉ bị chặn bởi capability (`rbac.require` →
DocPerm). Sau khi cắt sang `apply_workflow`, engine **chỉ cho phép khi vai trò người dùng
nằm trong `transition.allowed`**. Đo 2026-07-22: **18/22 workflow** có ít nhất một vai trò
giữ DocPerm write/submit nhưng **vắng mặt ở mọi transition** — nghĩa là cắt sang engine sẽ
tước quyền thao tác của họ.

Đáng chú ý nhất là các vai trò **giám sát** vắng mặt khỏi chính workflow module mình:
`PM Manager`, `Repair Manager`, `Calibration Manager`. Đây đồng thời là một **lỗi có sẵn**
(không do việc cắt sinh ra): các vai trò đó hiện đã không bấm được nút workflow trên Desk.

Danh sách đầy đủ nằm trong `KNOWN_ROLE_GAPS` (`tests/test_state_axis_invariant.py`), có 2
test khoá: khoảng trống **mới** ⇒ đỏ ngay; khoảng trống **đã đóng** mà quên xoá khỏi
baseline ⇒ cũng đỏ (baseline không được nói dối về tiến độ).

**Đã xử lý (2026-07-22).** `setup/backfill_workflow_domain_roles.run` cấp **138 transition**
cho **16/18** workflow, theo luật *chỉ đồng bộ, không nâng quyền* — phải thoả CẢ HAI:
(1) vai trò hiện có **0 transition** trong workflow đó (vai trò đã tham gia thì giới hạn của
nó là có chủ đích — vd `PM User` cố ý không được "Hủy phiếu"); (2) vai trò **đã có sẵn**
DocPerm mà transition đòi hỏi. Ghi vào **cả ba** nơi để không bị mất: workflow nguồn
(fresh-install), `fixtures/workflow.json` (đường `bench migrate` ghi đè bảng con), và site
live (không cần migrate). Kiểm chứng: 3 phép tính độc lập đều ra 138; đối chiếu với HEAD
cho thấy **0 transition bị mất**; chạy lại ⇒ 0 (idempotent).

**Còn 2 mục** trong `KNOWN_ROLE_GAPS` (`IMM Procurement Plan`/`Needs User`,
`IMM AVL Entry`/`Procurement User`): mọi transition của chúng dẫn tới state
`doc_status=1` cần `submit` mà vai trò không có ⇒ thuộc về §4-ter.

## 4-ter. T12-pre-B — transition ĐÃ cấp nhưng KHÔNG thực thi được (CHẶN T12–T17)

Chiều lệch ngược lại, và nặng hơn: **61 cặp vai trò×transition trên 17 workflow** được cấp
cho vai trò **thiếu DocPerm mà chính transition đó đòi hỏi** (suy từ `doc_status` của state
đích: `0→write`, `1→submit`, `2→cancel`). Những transition này **đã chết sẵn hôm nay** — bấm
trên Desk là `PermissionError` — và sẽ thành lỗi cứng ngay khi module cắt sang engine.

Ví dụ chạm vào chức năng chính của kỹ thuật viên:

| Workflow | Cặp không thực thi được |
|---|---|
| IMM-08 PM | `PM User → 'Completed'` cần `submit` (KTV không hoàn thành được phiếu bảo trì) |
| IMM-11 Hiệu chuẩn | `Calibration User → 'Passed' / 'Failed' / 'Conditionally Passed'` cần `submit` |
| IMM-12 RCA | `Corrective User → 'Completed'` cần `submit` |
| AC Asset Lifecycle | `PM User → 'Under Maintenance' / 'Under Repair' / …` cần `write` trên AC Asset |

> **IMM-09 (Asset Repair) SẠCH cả hai chiều** ⇒ là ứng viên an toàn nhất để cắt trước, dù
> kế hoạch gốc xếp IMM-08 làm module định khuôn.

**Ba lựa chọn, đều là quyết định của USER** (không tự làm — `report_unexecutable_transitions`
liệt kê đầy đủ):
1. **Cấp thêm DocPerm** (vd `submit` cho `PM User` trên PM Work Order) — nâng quyền THẬT,
   áp cho mọi đường ghi chứ không riêng workflow.
2. **Hạ `doc_status` của state đích** (vd `Completed` 1→0) — bỏ tính bất biến của tài liệu
   đã hoàn thành. Có tiền lệ: lô co-resident đã làm đúng vậy cho 5 doctype non-submittable.
3. **Không cắt các transition đó sang engine** — giữ đường service cho chúng, tức chấp nhận
   ADR-CORE-01 áp dụng một phần.

---

## 1. Tổng quan

Đưa AssetCore từ *110 bảng dữ liệu phẳng + logic tự viết* về *đồ thị nghiệp vụ chạy trên cơ
chế sẵn có của Frappe*, qua 5 phase. Mỗi task **≤5 file**, có acceptance + lệnh verify + file
tài liệu phải sync. Nguyên tắc: **cắt dọc** (một lát cắt = BE + API + FE + doc + test chạy được
thật), không cắt ngang (không "làm hết BE rồi mới làm FE").

## 2. Đồ thị phụ thuộc

```
T01 ADR + doc nền  (không đụng runtime)
      │
      ├── T02 guard connectivity (RED)      ──┐
      └── T03 guard state-axis   (RED)      ──┤   guard đi TRƯỚC để đo tiến độ khách quan
                                              │
   ┌──────────────────────────────────────────┘
   │
   P1 CONNECTIONS                    P2 STATE                    P3 REFERENTIAL
   T04 dashboard AC Asset            T10 shared/state.py         T18 root_doctype→Link
        │                                  │                          │
   T05 api/connections.py            T11 patch backfill          T19 fetch_from batch
        │                                  │                          │
   T06 FE RelatedRecords             T12 cắt IMM-08              T20 Link lẻ + deprecate
        │  ◀── checkpoint B ──▶            │
   T07 4 hub vận hành                T13 IMM-09
        │                                  │
   T08 wire 4 màn detail             T14 IMM-11
        │                                  │
   T09 7 hub còn lại                 T15 IMM-12
        │  ◀── checkpoint C ──▶            │
                                     T16 IMM-15/16 gỡ lockstep
                                           │
                                     T17 AC Asset rollup
                                           │  ◀── checkpoint D ──▶
                                     P4: T21 desk affordances
                                     P5: T22+ (CỔNG DUYỆT USER)
```

**Nhánh song song an toàn:** P1 (T04–T09) và P2 (T10–T17) **không đụng nhau về file**
(P1 = `*_dashboard.py` + `*.json` khoá `links` + FE component; P2 = `services/*.py` + patch).
Có thể chạy 2 phiên song song — **nhưng** cùng chạm `<dt>.json` ở T21, nên T21 phải chạy sau cùng.
P3 (T18–T20) đụng `<dt>.json` ⇒ **không** song song với T21.

## 3. Quyết định kiến trúc chi phối kế hoạch

1. **`status` không bị xoá** — chuyển thành dẫn xuất read-only. Đây là lý do FE/OAS/mobile không vỡ và là điều khiến P2 khả thi.
2. **Guard trước, sửa sau.** T02/T03 viết RED trước, đo tiến độ bằng số guard chuyển GREEN, không bằng cảm tính. Mọi guard phải có **test tự-cắn** (inject vi phạm → guard raise) theo mẫu `tests/test_workflow_submit_gate.py`.
3. **Một SSoT liên kết.** `<dt>_dashboard.py` là nguồn duy nhất; Desk và Vue đều đọc từ đó. FE tuyệt đối không khai lại danh sách liên kết.
4. **Patch viết xong ≠ chạy.** Claude viết patch + test chạy đôi; **USER** chạy `bench migrate`.
5. **Doc sync nằm trong DoD của từng task**, không gom thành task "cập nhật tài liệu" ở cuối.

---

## 4. Danh sách task

> **DoD chung mọi task** (ngoài acceptance riêng): `bench --site miyano run-tests --app assetcore --module <module liên quan>` xanh **và dán output**; không `git commit`; không `bench migrate`; nếu chạm `api/`/`services/` thì ghi rõ "cần USER reload gunicorn `--preload`"; UI copy tiếng Việt đầy đủ (LL-FE-53); checkpoint session context sau khi xong.

### Phase 0 — Nền tài liệu & guard (không đụng runtime)

#### T01 — ADR + đồng bộ tài liệu kiến trúc ✅ ĐÃ XONG (2026-07-22)
**Mô tả:** Ghi quyết định supersede và đóng các open question đã có bằng chứng.
**Acceptance:** ✅ `ADR-CORE-01_workflow_is_ssot.md` tồn tại · ✅ ADR cũ có banner SUPERSEDED + đính chính 2 khẳng định sai dữ kiện · ✅ SPEC §11 đóng OQ-1/2/4/6, hoãn OQ-3/5.
**Verify:** đọc lại 3 file; không file `.py`/`.json`/`.vue` nào bị đụng (`git status --short` chỉ hiện `docs/architecture/`).
**Phụ thuộc:** None · **Scope:** S (3 file, doc-only)

#### T02 — Static guard: connection graph (RED trước)
**Mô tả:** Guard đọc JSON + `*_dashboard.py`, khẳng định 12 hub doctype có đồ thị liên kết hợp lệ. Viết khi **chưa có** dashboard nào ⇒ phải ĐỎ đúng 12 chỗ.
**Acceptance:**
- [ ] Khai danh sách 12 hub trong hằng số `HUB_DOCTYPES` (SSoT của guard).
- [ ] Với mỗi hub: có `<dt>_dashboard.py::get_data()` trả ≥1 `transactions` nhóm; mọi doctype trong `items` **tồn tại thật**; có field trỏ ngược về hub (`fieldname` hoặc `non_standard_fieldnames`).
- [ ] Test tự-cắn: bịa 1 hub trỏ tới doctype không tồn tại ⇒ `AssertionError`.
**Verify:** `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_doctype_connectivity` → **ĐỎ với đúng lý do "thiếu dashboard"**, không phải lỗi import.
**Files:** `assetcore/tests/test_doctype_connectivity.py` · **Phụ thuộc:** T01 · **Scope:** M

#### T03 — Static guard: một trục trạng thái (RED trước)
**Mô tả:** Guard khẳng định invariant của ADR-CORE-01.
**Acceptance:**
- [ ] Doctype có Workflow `is_active=1` ⇒ field rollup (`status`/`allocation_status`) phải `read_only: 1`.
- [ ] `AC Asset`: chỉ `lifecycle_status` là trục ghi; `status` read-only.
- [ ] Grep-guard `frappe.db.set_value(...,"status"...)` / `doc.status = ` trong `services/`: đếm ≤ ngưỡng khai trong `ALLOWED_LEGACY` (khởi điểm = số hiện tại, giảm dần mỗi task P2 → 0 ở T17).
- [ ] Test tự-cắn cho cả 2 nhánh (read_only bị gỡ; thêm 1 chỗ ghi tay ngoài whitelist).
**Verify:** module test chạy → GREEN với ngưỡng khởi điểm; sửa ngưỡng xuống 0 thủ công ⇒ ĐỎ (chứng minh guard cắn).
**Files:** `assetcore/tests/test_state_axis_invariant.py` · **Phụ thuộc:** T01 · **Scope:** M

> ### ⛳ Checkpoint A — sau T01–T03
> - [ ] 2 guard chạy được, ĐỎ/GREEN đúng lý do dự kiến, có test tự-cắn.
> - [ ] `git status` chỉ hiện `docs/architecture/` + 2 file test mới — **0 file runtime**.
> - [ ] User review danh sách 12 hub + ngưỡng `ALLOWED_LEGACY` trước khi sang Phase 1.

---

### Phase 1 — P1 Connection graph (lát cắt dọc: AC Asset trước)

#### T04 — Dashboard connections cho `AC Asset`
**Mô tả:** Khai đồ thị liên kết của tài sản — lát cắt dọc đầu tiên, chứng minh mô hình.
**Acceptance:**
- [ ] `ac_asset_dashboard.py::get_data()` với 4 nhóm nhãn tiếng Việt: *Bảo trì & Sửa chữa* (PM Work Order, Asset Repair, PM Schedule) · *Hiệu chuẩn* (IMM Asset Calibration, IMM Calibration Schedule) · *Sự cố & Chất lượng* (Incident Report, IMM RCA Record, Asset QA Non Conformance) · *Hồ sơ & Vòng đời* (Asset Document, Asset Commissioning, Asset Transfer, Asset Decommission, Asset Lifecycle Event).
- [ ] `non_standard_fieldnames` khai đúng cho doctype không dùng field `asset`.
- [ ] Guard T02 chuyển từ 12 lỗi → 11 lỗi.
**Verify:** module test T02; mở `/app/ac-asset/<name>` trong Desk thấy tab Connections có 4 nhóm (Playwright render-verify, chụp ảnh về `.playwright/eval/`).
**Doc sync:** `docs/imm-00/04_Backend_Design.md` — thêm mục "Đồ thị liên kết (dashboard SSoT)".
**Files:** `doctype/ac_asset/ac_asset_dashboard.py` (mới), `ac_asset.json` (khoá `links`), doc · **Phụ thuộc:** T02 · **Scope:** S

#### T05 — API chung `get_connections`
**Mô tả:** Một endpoint đọc chính SSoT dashboard, để Vue dùng lại cho mọi màn.
**Acceptance:**
- [ ] `@frappe.whitelist() def get_connections(doctype: str, name: str) -> dict` trả `[{label, items:[{doctype, label_vi, count, list_url, filters}]}]`.
- [ ] **Áp permission thật**: dùng `frappe.get_list` (không `ignore_permissions`) ⇒ KTV ngoài scope thấy count=0, không rò dữ liệu.
- [ ] Doctype không có dashboard ⇒ trả `[]` (không 500).
- [ ] Có curate OpenAPI (`openapi_overrides.py`) + tag tiếng Việt để `test_oas_d9_tags` không đỏ thêm.
**Verify:** `--module assetcore.tests.test_connections` (2 persona: QTV thấy đủ, KTV bị lọc) + `test_oas_baseline` không đỏ thêm ngoài 2 lỗi pre-existing của IMM-10.
**Doc sync:** `docs/imm-00/05_API_Specification.md` — thêm endpoint.
**Files:** `assetcore/api/connections.py`, `api/openapi_overrides.py`, `tests/test_connections.py`, doc · **Phụ thuộc:** T04 · **Scope:** M · ⚠️ **cần USER reload**

#### T06 — FE `<RelatedRecords>` + wire màn tài sản
**Mô tả:** Component chung dùng lại được cho 33 màn detail; wire màn đầu tiên.
**Acceptance:**
- [ ] `RelatedRecords.vue`: loading / empty-state có nghĩa ("Chưa có bản ghi liên quan") / lỗi có nút thử lại; click điều hướng sang list đã lọc sẵn.
- [ ] `AssetDetailView.vue` render component; **không** khai lại danh sách liên kết ở FE.
- [ ] Nhãn tiếng Việt đầy đủ (LL-FE-53).
**Verify:** `npm run test:unit` (vitest cho component) + Playwright: mở 1 tài sản, chụp ảnh **đúng dữ liệu thật** (LL-FE-48: không chấp nhận khung rỗng làm bằng chứng).
**Doc sync:** `docs/imm-00/06_Frontend_Design.md`.
**Files:** `frontend/src/components/RelatedRecords.vue`, `frontend/src/api/connections.ts`, `views/asset/AssetDetailView.vue`, test, doc · **Phụ thuộc:** T05 · **Scope:** M

> ### ⛳ Checkpoint B — sau T04–T06 (lát cắt dọc đầu tiên chạy thật)
> - [ ] Mở 1 tài sản: **Desk** thấy tab Connections, **Vue** thấy khối "Bản ghi liên quan" — cùng một nguồn khai báo.
> - [ ] BE test + FE vitest xanh, có output dán ra.
> - [ ] **User xem ảnh Playwright và duyệt hình thức** trước khi nhân ra 11 hub còn lại.

#### T07 — Dashboard cho 4 hub vận hành
**Mô tả:** `PM Work Order`, `Asset Repair`, `IMM Asset Calibration`, `Incident Report`.
**Acceptance:** mỗi hub ≥2 nhóm liên kết (vd PM WO → Asset, PM Schedule, Spare Parts Used, Asset Lifecycle Event); guard T02 còn ≤7 lỗi.
**Verify:** module test T02. **Doc sync:** `docs/imm-08|09|11|12/04_Backend_Design.md` (mỗi file 1 mục ngắn).
**Files:** 4 `*_dashboard.py` (+4 doc) · **Phụ thuộc:** Checkpoint B · **Scope:** M

#### T08 — Wire 4 màn detail vận hành
**Acceptance:** `PMWorkOrderDetailView`, `CMWorkOrderDetailView`, `CalibrationDetailView`, `IncidentDetailView` render `<RelatedRecords>`; 0 dòng khai lại liên kết.
**Verify:** vitest + Playwright 1 màn đại diện. **Doc sync:** `docs/imm-08|09|11|12/06_Frontend_Design.md`.
**Files:** 4 `.vue` · **Phụ thuộc:** T07 · **Scope:** M

#### T09 — 7 hub còn lại + wire
**Mô tả:** `Asset Commissioning`, `Asset Document`, `Asset Transfer`, `AC Supplier`, `IMM Device Model`, `AC Spare Part`, `IMM CAPA Record`.
**Acceptance:** guard T02 **GREEN toàn bộ 12 hub**; ≥5 màn detail đã wire (SC-3).
**Verify:** module test T02 GREEN + vitest. **Doc sync:** `docs/imm-04|05|03|15|16/04+06`.
**Files:** 7 `*_dashboard.py` + ≥3 `.vue` → **tách 2 task con nếu vượt 5 file** (T09a hub IMM-04/05/00, T09b hub IMM-03/15/16).
**Phụ thuộc:** T08 · **Scope:** L → **chia đôi khi thực thi**

> ### ⛳ Checkpoint C — P1 đóng
> - [ ] SC-1 ✅ 12 hub có dashboard · SC-2 ✅ API áp permission · SC-3 ✅ ≥5 màn Vue.
> - [ ] `bench run-tests --app assetcore` xanh (trừ 2 đỏ pre-existing IMM-10).

---

### Phase 2 — P2 Một trục trạng thái (ADR-CORE-01)

#### T10 — Helper `transition()` + bảng ánh xạ rollup
**Acceptance:**
- [ ] `services/shared/state.py`: `transition(doc, action, *, actor=None)` bọc `apply_workflow`; `allowed_transitions(doc)` bọc `get_transitions()` + gate capability.
- [ ] `ROLLUP_MAP` khai **một chỗ** cho 2 ngoại lệ (`IMM CAPA Record`, `AC Asset`), phủ **100%** state (test bắt state thiếu ánh xạ).
- [ ] Unit test không cần record thật cho `ROLLUP_MAP`; integration test cho `transition()`.
**Verify:** `--module assetcore.tests.test_shared_state`. **Doc sync:** ADR-CORE-01 §Kiểm chứng (đánh dấu đã có helper).
**Files:** `services/shared/state.py`, `tests/test_shared_state.py` · **Phụ thuộc:** Checkpoint A · **Scope:** S

#### T11 — Patch backfill `workflow_state` (viết, KHÔNG chạy)
**Acceptance:**
- [ ] `patches/v3_2/011_backfill_workflow_state.py`: với 10 doctype ánh xạ 1-1, set `workflow_state = status` khi rỗng/lệch; dùng `frappe.db.set_value(..., update_modified=False)`; **idempotent**; `flags.ignore_links=True` nếu phải `doc.save()` (bẫy patch cũ).
- [ ] In ra số record đã sửa (site dev = 0 → log "0 record, no-op").
- [ ] Đăng ký trong `patches.txt` kèm comment.
- [ ] Test chạy patch **2 lần** ⇒ lần 2 sửa 0 record.
**Verify:** `--module assetcore.tests.test_patch_backfill_workflow_state`. **Không chạy `bench migrate`** — ghi vào STATE là "chờ USER".
**Files:** patch, `patches.txt`, test · **Phụ thuộc:** T10 · **Scope:** S

#### T12 — Cắt IMM-08 (PM Work Order) sang workflow engine
**Mô tả:** Module tiên phong — chứng minh mô hình cắt trước khi nhân ra 3 module còn lại.
**Acceptance:**
- [ ] Mọi chỗ đổi trạng thái trong `services/imm08.py` gọi `transition()`; **0** `doc.status = ` / `db.set_value(...,"status")`.
- [ ] `allowed_transitions` trả từ engine; xoá bảng `_PM_*_TRANSITIONS` chép tay.
- [ ] `status` giữ nguyên giá trị trả về cho FE/OAS ⇒ **FE không phải sửa**; test FE hiện có vẫn xanh.
- [ ] Ngưỡng `ALLOWED_LEGACY` trong guard T03 giảm tương ứng.
**Verify:** `--module assetcore.tests.test_imm08` xanh + `--module assetcore.tests.test_state_axis_invariant` + `cd frontend && npm run test:unit`.
**Doc sync:** `docs/imm-08/04_Backend_Design.md` (state machine giờ do workflow điều khiển) + `02_Analysis_Design.md` (ghi ADR-CORE-01 thay cho mô tả dual-track).
**Files:** `services/imm08.py`, `api/imm08.py`, `tests/test_imm08.py`, 2 doc · **Phụ thuộc:** T11 · **Scope:** M · ⚠️ **cần USER reload**

#### T13 / T14 / T15 — Cắt IMM-09 · IMM-11 · IMM-12 (Incident + RCA)
**Mô tả:** Lặp đúng khuôn T12 cho từng module. **Mỗi module một task riêng** — không gộp.
**Acceptance / Verify / Doc sync:** y hệt T12, thay `imm08` → `imm09` / `imm11` / `imm12`.
⚠️ T15 đụng 2 doctype (`Incident Report` + `IMM RCA Record`) — nếu vượt 5 file thì tách T15a/T15b.
**Phụ thuộc:** T12 (tuần tự, để khuôn mẫu ổn định) · **Scope:** M mỗi task

> ### ⛳ Checkpoint D — sau T12–T15
> - [ ] 4 doctype Wave-1 chuyển trạng thái qua engine; guard T03 giảm đúng 4 bậc.
> - [ ] Test 4 module + FE vitest xanh, **dán output**.
> - [ ] **USER reload gunicorn `--preload`** rồi xác nhận live: duyệt 1 phiếu PM chạy đúng, nút CTA đúng quyền.
> - [ ] Nếu site khách có dữ liệu → USER chạy `bench migrate` (patch T11) **trước** khi reload.

#### T16 — IMM-15/16: gỡ lockstep, xoá invariant dual-track
**Acceptance:** `imm15.py`/`imm16.py` bỏ `db.set_value` đồng bộ 2 field; dùng `transition()`; xoá `TestAllocationAllowedTransitions` + `_CYCLE_EXCEPTION_EDGES` + `_ALLOCATION_SHORTCUT_EDGES` (không còn lý do tồn tại); rollup CAPA lấy từ `ROLLUP_MAP`.
**Verify:** `--module assetcore.tests.test_imm15` + `test_imm16` xanh.
**Doc sync:** `docs/imm-15/02+04` và `docs/imm-16/02+04` — đánh dấu **ADR-IMM-15-08, ADR-IMM-15-10, ADR-IMM-16-05 superseded bởi ADR-CORE-01**.
**Files:** `services/imm15.py`, `services/imm16.py`, 2 test, doc → **tách T16a/T16b** để giữ ≤5 file.
**Phụ thuộc:** Checkpoint D · **Scope:** L → chia đôi

#### T17 — `AC Asset`: `status` thành rollup dẫn xuất
**Acceptance:** `lifecycle_status` là trục duy nhất ghi được; `status` `read_only:1` + tính lại từ `ROLLUP_MAP`; giá trị legacy `Submitted` ánh xạ rõ ràng; guard T03 về **0** legacy.
**Verify:** `--module assetcore.tests.test_imm00` + guard T03 GREEN với ngưỡng 0.
**Doc sync:** `docs/imm-00/02+04`.
**Files:** `ac_asset.json`, `doctype/ac_asset/ac_asset.py`, `services/imm00.py`, test, doc · **Phụ thuộc:** T16 · **Scope:** M

---

### Phase 3 — P3 Toàn vẹn tham chiếu

#### T18 — Tham chiếu đa hình: `root_doctype` / `ref_doctype` → Link DocType
**Acceptance:** `Asset Lifecycle Event.root_doctype` và `IMM Audit Trail.ref_doctype` đổi Data→`Link → DocType`; `IMM Audit Trail.ref_name` đổi Data→`Dynamic Link`; patch chuẩn hoá giá trị cũ (bỏ giá trị không phải doctype hợp lệ → log, không xoá); guard kiểm 0 field Dynamic Link nào trỏ tới field Data.
**Verify:** module test + patch chạy đôi. **Doc sync:** `docs/imm-00/04` (§audit trail).
**Files:** 2 `.json`, 1 patch, `patches.txt`, test · **Phụ thuộc:** Checkpoint D · **Scope:** M

#### T19 — `fetch_from` cho bản sao denormalize
**Acceptance:** ≥10 field (`asset_name`, `serial_no`, `part_name` ×3, `dept_head_name`, `item_name`, …) chuyển sang `fetch_from` + `read_only:1` + `no_copy`; patch resync giá trị lệch; guard cấm thêm field tên `*_name` kiểu Data cạnh một Link cùng bảng.
**Verify:** module test + patch chạy đôi. **Doc sync:** `docs/imm-09/04`, `docs/imm-15/04`.
**Files:** ~5 `.json`, 1 patch, test → tách nếu vượt · **Phụ thuộc:** T18 · **Scope:** M

#### T20 — Link lẻ + deprecate field chết
**Acceptance:** `AC Asset.insurer_name`→Link `AC Supplier`; `IMM Training Session.location`→Link `AC Location`; `Benchmark Candidate.model`→Link `IMM Device Model`; `AC Asset.item_code` **ẩn + label "(không dùng — sẽ gỡ)"**, KHÔNG xoá cột (ranh giới "Ask first"); patch chuẩn hoá giá trị text→link, giá trị không khớp thì **giữ lại + log**, không mất dữ liệu.
**Verify:** module test + patch chạy đôi. **Doc sync:** `docs/imm-00/04`, `docs/imm-06/04`, `docs/imm-02/04`.
**Files:** 4 `.json`, 1 patch, test · **Phụ thuộc:** T19 · **Scope:** M

---

### Phase 4 — P4 Desk affordances

#### T21 — `title_field` / `search_fields` / `in_global_search` / `states` / `timeline_field`
**Acceptance:** 12 hub có `title_field` (tên người đọc được, không phải `name`), `search_fields` ≥2, ≥1 field `in_global_search`, `states` (màu indicator list view) khớp trục SSoT sau P2, `timeline_field` cho doctype con trỏ về cha; guard T02 mở rộng phần này → GREEN (SC-7).
**Verify:** module test T02 + Desk: gõ tên tài sản vào awesomebar ra kết quả (ảnh Playwright).
**Doc sync:** `docs/imm-00/04` §Desk.
**Files:** ~6 `.json` mỗi lượt → **tách T21a/T21b/T21c** (4 hub mỗi task) · **Phụ thuộc:** T17 + T20 (tránh tranh chấp cùng file JSON) · **Scope:** L → chia ba

---

### Phase 5 — P5 (CỔNG DUYỆT USER, chưa lên lịch)

Chỉ làm khi user bật đèn xanh — các thứ này **sinh tác dụng phụ lên người dùng thật**
(ToDo, email) hoặc trùng lặp với thứ đang chạy ổn:

- T22 Query Report "Danh mục tài sản & hạn hiệu chuẩn" (thay 1 endpoint tự viết).
- T23 Print Format phiếu PM (thay pdfkit thủ công).
- T24 Number Card + Dashboard Chart trên Workspace `IMM Operations`.
- T25 Assignment Rule giao WO/CAPA · T26 Auto Repeat cho PM Schedule ⚠️ **OQ-5**.

---

## 5. Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Cắt state machine làm vỡ FE đang chạy | **Cao** | `status` giữ nguyên tên + enum, chỉ thành dẫn xuất ⇒ FE không phải sửa; FE vitest chạy trong DoD mỗi task P2 |
| Site khách đã có dữ liệu, `workflow_state` rỗng/lệch | Trung bình | Patch T11 idempotent + báo cáo số record; USER chạy migrate trước khi reload |
| Tranh chấp file với ~144 file uncommitted của batch khác | **Cao** | Task này chạm **file mới** là chính; với file chung (`<dt>.json`, `services/imm*.py`) phải **read-fresh trước Edit** (luật đa-phiên); T21 xếp cuối để không tranh JSON với P3 |
| Sửa `services/*.py` không thấy trên HTTP live | Trung bình | DoD = `bench run-tests`, KHÔNG phải curl; ghi rõ "cần USER reload" ở mọi task đụng `api/`/`services/` |
| Xoá invariant test dual-track làm mất lưới an toàn | Trung bình | Chỉ xoá **sau** khi guard T03 GREEN cho module đó; guard mới thay thế vai trò cũ |
| Guard "xanh giả" | Trung bình | Mọi guard bắt buộc có test tự-cắn (mẫu `test_workflow_submit_gate.py`) |
| OAS baseline đỏ thêm | Thấp | T05 curate override + tag VI; đối chiếu `test_oas_baseline`/`test_oas_d9_tags` (2 đỏ pre-existing của IMM-10 là **không** do task này) |
| Phạm vi phình sang ERPNext | Thấp | Ranh giới "Never" trong SPEC §9 |

## 6. Song song hoá

| Nhóm | Có thể song song? |
|---|---|
| P1 (T04–T09) ‖ P2 (T10–T17) | ✅ khác file hoàn toàn — 2 phiên chạy song song được |
| T12 → T13 → T14 → T15 | ❌ tuần tự (T12 định khuôn, 3 task sau lặp khuôn) |
| T18 → T19 → T20 | ❌ tuần tự (cùng đụng JSON + patches.txt) |
| T21 | ❌ chạy **sau** P2 và P3 (tranh chấp `<dt>.json`) |
| Doc sync trong từng task | ✅ nằm ngay trong task, không tách |

## 7. Điều kiện để tuyên bố "xong"

Toàn bộ SC-1..SC-10 của SPEC §10 đạt, cụ thể: 2 static guard GREEN (kèm test tự-cắn) ·
`bench --site miyano run-tests --app assetcore` xanh (trừ 2 đỏ pre-existing của owner IMM-10)
· `npm run test:unit` xanh · ảnh Playwright chứng minh liên kết render **dữ liệu thật** ·
patch chạy đôi cho cùng kết quả · **0** `git commit`, **0** `bench migrate` do Claude thực hiện.
