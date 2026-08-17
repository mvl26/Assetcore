# SPEC — Core Refinement: đưa AssetCore về "Frappe-native"

| Mục | Giá trị |
|---|---|
| Loại | Specification (spec-driven development, Phase 1) |
| Trạng thái | **DRAFT — chờ user duyệt** (chưa được code) |
| Ngày | 2026-07-22 |
| Branch | `feature/hieuc/core-refinement` |
| Phạm vi | Toàn bộ 110 DocType + services + api + FE detail views |
| Supersede | `docs/architecture/ADR_status_vs_workflow_state.md` (Accepted 2026-06-02) — xem §5 |

---

## 0. Assumptions (đã xác nhận với user 2026-07-22)

| # | Giả định | Nguồn |
|---|---|---|
| A1 | Phạm vi = **framework Frappe**, KHÔNG tái dùng master ERPNext (`Item`/`Supplier`/`Warehouse`/`Stock Entry`/`Asset`). `AC *` giữ nguyên là master của AssetCore. | user chốt |
| A2 | Liên kết phải nhìn thấy ở **cả Desk lẫn Vue FE** qua **một API chung** đọc từ **một SSoT** khai báo trong DocType. | user chốt |
| A3 | **Được phép chuẩn hoá cột** (Data→Link, gộp trục trạng thái) — kèm patch idempotent. | user chốt |
| A4 | `bench migrate` là **HARD-STOP**: mọi patch viết xong chỉ *chờ USER chạy*, Claude KHÔNG tự chạy. | CLAUDE.md + STATE |
| A5 | KHÔNG auto-commit. Working tree đang có ~144+ file uncommitted của batch khác ⇒ mọi thay đổi phải **tách batch rõ ràng**. | STATE Blocker#2 |
| A6 | Site `miyano` chạy chung 8 app (erpnext, hrms, antmed_crm, …) ⇒ KHÔNG đụng doctype core/của app khác. | site apps.txt |
| A7 | Production chạy gunicorn `--preload` ⇒ sửa `api/*.py` / `services/*.py` cần USER reload; DoD = `bench run-tests`, KHÔNG phải curl. | memory `gunicorn_preload_staleness` |

---

## 1. Objective

**Vấn đề (user, nguyên văn):** "các doctype gần như chỉ lưu data chứ không có liên kết connect gì … cần tối ưu để dùng những gì sẵn có của Frappe chứ không chỉ để lưu data."

**Mục tiêu:** chuyển AssetCore từ *110 bảng dữ liệu phẳng + logic tự viết* sang *đồ thị nghiệp vụ chạy trên cơ chế sẵn có của Frappe*, sao cho:

1. Mở một record bất kỳ **thấy ngay mọi record liên quan** (Desk + Vue) mà không phải code riêng cho từng màn.
2. **Một trục trạng thái duy nhất** cho mỗi doctype, do **workflow engine của Frappe** điều khiển — hết cảnh "đủ quyền vẫn không duyệt được" và hết `_VALID_TRANSITIONS` chép tay mỗi module.
3. **Toàn vẹn tham chiếu do DB/metadata bảo đảm** (Link/Dynamic Link/fetch_from) thay vì chuỗi text tự do.
4. Tìm kiếm, giao việc, lịch lặp, in ấn, báo cáo, biểu đồ **dùng core** thay vì endpoint tự viết.

**Người dùng hưởng lợi:** kỹ thuật viên (thấy lịch sử thiết bị tại chỗ), quản lý thiết bị (duyệt được, tra được), admin (Desk dùng được thật), đội phát triển (bớt nợ kỹ thuật, bớt bug lặp).

**Không thuộc phạm vi (non-goals):**
- Tái dùng/di trú sang master ERPNext (A1).
- Modify core Frappe/ERPNext (CLAUDE.md §19).
- Viết lại FE framework, đổi stack, đổi giao diện.
- Tối ưu hiệu năng (đó là `assetcore-perf`), trừ index đi kèm việc đổi Data→Link.

---

## 2. Hiện trạng — bằng chứng đo được (2026-07-22)

Quét `assetcore/assetcore/doctype/*/*.json` (110 file, 65 doctype không phải child):

| Cơ chế core Frappe | Hiện trạng | Hệ quả |
|---|---|---|
| Dashboard connections (`*_dashboard.py` / khoá `links`) | **0/110**; 62 file có `"links": []` | Mở `AC Asset` không thấy PM/Sửa chữa/Hiệu chuẩn/Sự cố/Hồ sơ/Điều chuyển ⇒ đúng lời phàn nàn của user |
| `timeline_field` | **0/110** | Comment/hoạt động của con không nổi lên cha |
| Query Report / Dashboard Chart / Number Card | **0 / 0 / 0** | Mọi KPI phải code API + Vue tay |
| Print Format | **0** | Phiếu PM/hiệu chuẩn/QR phải tự dựng pdfkit (LL-BE-55..58) |
| Notification (doctype core) | **1** | Framework thông báo tự viết trong `services/notifications.py` |
| `in_global_search` / `search_fields` / `title_field` | **3 / 7 / 18** trên 110 | Awesomebar Desk không tìm ra tài sản; list view hiện `name` thay vì tên người đọc được |
| Assignment Rule / Auto Repeat / Document Follow | **0 / 0 / 0** | Giao việc + lịch PM lặp tự viết scheduler |
| Trục trạng thái | **26 doctype có ≥2 trục** (`docstatus` + `workflow_state` + `status` + `lifecycle_status`); 14 doctype có `status` nhưng KHÔNG có workflow | Desync, CTA câm, bug RBAC duyệt |
| Ghi trạng thái | `frappe.db.set_value` **84 chỗ** trong `services/`; `apply_workflow` chỉ **42 chỗ / 9 file** | Bỏ qua hook, Version, workflow engine, permission |
| `ignore_permissions` | **100 chỗ** | Quyền không do core bảo đảm |
| Data lẽ ra là Link/fetch_from | ~30 field thực sự (xem §6.3); `fetch_from` chỉ dùng **14 chỗ** | Trôi dữ liệu (`asset_name`, `part_name`, `serial_no` copy tay), `root_doctype` là Data ⇒ Dynamic Link `root_record` không validate |
| `is_tree` | 2 (`AC Location`, `AC Department`) — đúng | ✅ điểm sáng |
| `permission_query_conditions` / `has_permission` | 6 / 6 doctype | ✅ có nhưng chưa phủ |

### 2.1 Nguyên nhân gốc (thesis)

> Service layer **tự chạy state machine** (`_VALID_TRANSITIONS`, `doc.status = ...`, `frappe.db.set_value`) thay vì gọi `frappe.model.workflow.apply_workflow`. Workflow engine bị đẩy xuống vai trò "chỉ phục vụ desk" (nguyên văn `docs/imm-15/04_Backend_Design.md:909`).

Chuỗi hệ quả đã có bằng chứng trong repo:
- Workflow engine không phải SSoT ⇒ mỗi module phải tự đẻ `_allowed_transitions` + **invariant test dual-track** để canh lệch (IMM-15 §VI.1.1/§VI.2.1, IMM-16 ADR-05).
- `workflow_state` đọng ⇒ ADR-IMM-16-05 phải "lockstep sync" bằng `db.set_value` — vá triệu chứng.
- Transition RBAC/`doc_status` sai thì **câm lặng** ⇒ bug "QTV đủ quyền vẫn không duyệt được" (memory `workflow_admin_override_rbac`, root-cause #1 và #2).
- FE hardcode `status === '...'` ⇒ luật GATE-8/LL-FE-51 phải ra đời để cấm.

ADR `status_vs_workflow_state` (Accepted) **hợp thức hoá** tình trạng này ("KHÔNG hợp nhất về một field duy nhất"). Muốn sửa từ lõi thì phải supersede nó — đây là quyết định kiến trúc lớn nhất của spec này (§5, Open Question OQ-1).

---

## 3. Kiến trúc đích — 5 trụ

### P1 — Connection graph (đồ thị liên kết) là first-class

- Mỗi **hub doctype** khai báo liên kết **một lần** trong `<doctype>_dashboard.py` (chuẩn Frappe: `get_data()`), gồm `fieldname`, `transactions[{label, items[]}]`, `non_standard_fieldnames`, `internal_links`.
- Desk hiển thị tab "Connections" **miễn phí**, không code thêm.
- Vue FE dùng **1 endpoint chung** `assetcore.api.connections.get_connections(doctype, name)` — đọc chính SSoT đó, trả về số lượng + link, có áp permission. FE có **1 component chung** `<RelatedRecords>` dùng lại cho 33 màn `*Detail*.vue`.
- Hub doctype (đợt đầu, 12): `AC Asset`, `PM Work Order`, `Asset Repair`, `IMM Asset Calibration`, `Incident Report`, `Asset Commissioning`, `Asset Document`, `Asset Transfer`, `AC Supplier`, `IMM Device Model`, `AC Spare Part`, `IMM CAPA Record`.

### P2 — Một trục trạng thái, do workflow engine điều khiển

| Trục | Vai trò duy nhất | Ai được ghi |
|---|---|---|
| `docstatus` | Tính bất biến (Draft/Submitted/Cancelled) | core, qua submit/cancel |
| `workflow_state` | **SSoT nghiệp vụ** — trạng thái hiện tại | **chỉ** `apply_workflow` |
| `status` | **Dẫn xuất, read-only** — rollup cho FE/report/tương thích ngược | controller tính trong `on_update`, không ai set tay |
| `lifecycle_status` (AC Asset) | gộp vào `workflow_state` của `AC Asset Lifecycle` | — |

- Mọi service ghi trạng thái đi qua **một helper chung** `assetcore.services.shared.state.transition(doc, action)` → gọi `apply_workflow` → engine tự set `workflow_state` + `docstatus` + sinh `Workflow Action` + audit.
- `allowed_transitions` trả cho FE lấy từ `frappe.model.workflow.get_transitions()` — **xoá** các bảng `_*_ALLOWED_TRANSITIONS` chép tay và các invariant test dual-track đi kèm.
- 14 doctype có `status` nhưng chưa có workflow: hoặc gắn workflow, hoặc tuyên bố `status` là **derived** và khoá read-only.

### P3 — Toàn vẹn tham chiếu do metadata bảo đảm

- **Tham chiếu thật đang là Data** → `Link` / `Dynamic Link` (kèm `search_index`).
- **Bản sao denormalize** (`asset_name`, `part_name`, `serial_no`, `dept_head_name`, …) → `fetch_from` + `read_only: 1` + `no_copy` ⇒ core tự đồng bộ, hết trôi dữ liệu.
- **Mã định danh thật** (`udi_code`, `byt_reg_no`, `manufacturer_sn`, `gmdn_code`) → **giữ Data**, nhưng thêm `unique`/`search_index`/`in_global_search` phù hợp. (Ngoại lệ: `gmdn_code` có thể lên master riêng — OQ-3.)

### P4 — Desk-native affordances

`title_field`, `search_fields`, `in_global_search`, `show_title_field_in_link`, `states` (indicator màu list view), `timeline_field`, `allow_auto_repeat` (PM Schedule), Assignment Rule (giao WO/CAPA), `max_attachments`/`allow_attachments`.

### P5 — Report / Print / Chart bằng core (đợt sau, hẹp)

Chỉ chuyển những thứ **trùng lặp rõ**: 1 Query Report (danh mục tài sản + hạn hiệu chuẩn), 1 Print Format (phiếu PM), 2 Number Card + 2 Dashboard Chart trên Workspace `IMM Operations`. **Không** chuyển KPI đã có API + FE đang chạy ổn.

---

## 4. Tech stack & Commands

**Stack:** Frappe v15 (Python 3.11, MariaDB) · Vue 3 + TypeScript + Pinia + TanStack Query + Tailwind.

```bash
# Test BE (DoD chính — module-isolated để tránh nhiễm fixture)
bench --site miyano run-tests --app assetcore
bench --site miyano run-tests --module assetcore.tests.guards.test_doctype_connectivity

# Test FE
cd frontend && npm run test:unit          # vitest
cd frontend && npm run build              # emptyOutDir → deploy live (LL-DEPLOY-09)

# Patch (CHỈ USER chạy — HARD-STOP)
bench --site miyano migrate

# Reload worker sau khi sửa api/services (CHỈ USER)
sudo supervisorctl restart frappe-bench-web:  # hoặc bench restart
```

---

## 5. Quyết định kiến trúc cần chốt (supersede ADR cũ)

**ADR-CORE-01 (đề xuất):** *Workflow engine của Frappe là SSoT trạng thái duy nhất.*

- **Supersede** `ADR_status_vs_workflow_state.md` (Mô hình 1 "`status` là SoT, `workflow_state` vestigial" bị bãi bỏ).
- **Lý do:** mô hình cũ tạo ra 3 lớp vá liên tiếp (lockstep sync, invariant dual-track, `_ALLOWED_TRANSITIONS` chép tay) và là gốc của bug duyệt-không-ăn. Chi phí duy trì > chi phí hợp nhất.
- **Tương thích ngược:** `status` **không bị xoá** — trở thành field dẫn xuất read-only, giữ nguyên giá trị enum hiện tại ⇒ FE/OAS/mobile **không vỡ**. Đây là điểm khiến việc hợp nhất khả thi mà không phải viết lại FE.
- **Rủi ro:** 4 doctype Wave-1 (`PM Work Order`, `Asset Repair`, `IMM Asset Calibration`, `Incident Report`) đang chạy thật ⇒ cần patch backfill `workflow_state = status` + test hồi quy trước khi cắt.

---

## 6. Project structure — file mới/sửa

```
assetcore/assetcore/doctype/<dt>/<dt>_dashboard.py   ← MỚI (P1, 12 file đợt 1)
assetcore/assetcore/doctype/<dt>/<dt>.json           ← SỬA (links, title_field, states, fetch_from, Data→Link)
assetcore/api/connections.py                         ← MỚI: get_connections(doctype, name) whitelist
assetcore/services/shared/state.py                   ← MỚI: transition() bọc apply_workflow
assetcore/patches/0xx_backfill_workflow_state.py     ← MỚI (P2)
assetcore/patches/0xx_normalize_data_to_link.py      ← MỚI (P3)
assetcore/patches.txt                                ← SỬA
assetcore/tests/guards/test_doctype_connectivity.py         ← MỚI: static guard P1/P4
assetcore/tests/guards/test_state_axis_invariant.py         ← MỚI: static guard P2
frontend/src/components/RelatedRecords.vue           ← MỚI (P1 FE)
frontend/src/api/connections.ts                      ← MỚI
docs/architecture/ADR-CORE-01_workflow_is_ssot.md    ← MỚI (§5)
docs/imm-XX/04_Backend_Design.md                     ← SỬA (BA ratify, KHÔNG self-edit — LL-AUDIT)
```

### 6.3 Danh sách Data→Link/fetch_from (rút gọn, đợt 1)

| Doctype | Field | Hiện tại | Đích |
|---|---|---|---|
| Asset Lifecycle Event | `root_doctype` | Data | **Link → DocType** (để `root_record` Dynamic Link validate được) |
| IMM Audit Trail | `ref_doctype` / `ref_name` | Data / Data | **Link → DocType** / **Dynamic Link** |
| AC Asset | `item_code` | Data | Link → `IMM Device Model` *(hoặc bỏ — OQ-2)* |
| AC Asset | `insurer_name` | Data | Link → `AC Supplier` |
| Asset Repair | `asset_name`, `serial_no` | Data | `fetch_from: asset.asset_name` / `asset.manufacturer_sn`, read_only |
| Spare Parts Used | `item_code`, `item_name`, `manufacturer_part_no` | Data ×3 | Link → `AC Spare Part` + 2 `fetch_from` |
| AC Spare Part Stock / AC Stock Movement Item / IMM Spare Allocation Item | `part_name` | Data | `fetch_from: spare_part.part_name` |
| Service Contract Asset | `asset_name` | Data | `fetch_from: asset.asset_name` |
| IMM Training Session | `location` | Data | Link → `AC Location` |
| Benchmark Candidate | `model` | Data | Link → `IMM Device Model` |
| Asset Commissioning | `vendor_serial_no` | Data | giữ Data (số của hãng, không phải FK) |

*(Danh sách đầy đủ + phân loại 85 field ứng viên sẽ nằm trong Phase 2 — Plan.)*

---

## 7. Code style

**Dashboard SSoT** (`ac_asset_dashboard.py`):

```python
from __future__ import annotations


def get_data() -> dict:
    """Liên kết hiển thị ở tab Connections (Desk) và API /connections (Vue).

    SSoT duy nhất cho đồ thị liên kết của AC Asset — KHÔNG khai báo lại ở FE.
    """
    return {
        "fieldname": "asset",
        "non_standard_fieldnames": {"Asset Transfer": "asset", "AC Purchase": "asset"},
        "transactions": [
            {"label": "Bảo trì & Sửa chữa", "items": ["PM Work Order", "Asset Repair", "PM Schedule"]},
            {"label": "Hiệu chuẩn", "items": ["IMM Asset Calibration", "IMM Calibration Schedule"]},
            {"label": "Sự cố & Chất lượng", "items": ["Incident Report", "IMM RCA Record", "Asset QA Non Conformance"]},
            {"label": "Hồ sơ & Vòng đời", "items": ["Asset Document", "Asset Commissioning", "Asset Transfer",
                                                     "Asset Decommission", "Asset Lifecycle Event"]},
        ],
    }
```

**Write-path trạng thái** (`services/shared/state.py`):

```python
def transition(doc: "Document", action: str, *, actor: str | None = None) -> "Document":
    """Chuyển trạng thái QUA workflow engine — đường ghi DUY NHẤT.

    Cấm: doc.status = ... / frappe.db.set_value(dt, name, "status", ...).
    Engine tự lo workflow_state, docstatus, Workflow Action, permission và audit.
    """
    from frappe.model.workflow import apply_workflow
    return apply_workflow(doc, action)
```

**Patch idempotent:**

```python
def execute() -> None:
    """Backfill workflow_state = status cho doctype Mô hình 1 (ADR-CORE-01).

    Idempotent: chỉ ghi khi workflow_state rỗng/lệch. flags.ignore_links=True để
    link cũ hỏng không abort cả bench migrate (memory: patch_docsave_ignore_links).
    """
```

Quy ước chung: type hints + docstring bắt buộc (CLAUDE.md §15); không đặt logic trong controller; UI copy tiếng Việt đầy đủ (memory `ui_copy_language_policy`).

---

## 8. Testing strategy

TDD bắt buộc (CLAUDE.md §17). Ba tầng:

1. **Static guard tests** (chạy nhanh, không cần DB record) — mô hình đã chứng minh hiệu quả với `tests/test_workflow_submit_gate.py`:
   - `test_doctype_connectivity.py`: mọi hub doctype (danh sách khai báo) **phải** có `get_data()` trả ≥1 transaction; mọi doctype trong `items` phải tồn tại và có field trỏ ngược; hub phải có `title_field` + ≥1 `in_global_search`.
   - `test_state_axis_invariant.py`: doctype có workflow bound ⇒ `status` phải `read_only: 1`; **0** doctype có 2 trục ghi được; grep-guard `frappe.db.set_value(..., "status")` chỉ được xuất hiện trong whitelist rỗng dần.
   - Mỗi guard phải có **test tự-cắn** (inject vi phạm → guard raise) để không "xanh giả".
2. **Integration BE** — module-isolated: `apply_workflow` đi đúng đường cho 4 doctype Wave-1; `get_connections` áp permission (KTV không thấy record ngoài scope).
3. **FE vitest** — `RelatedRecords.vue` render từ payload API; không hardcode `status ===`.

**DoD:** `bench --site miyano run-tests --app assetcore` xanh + `npm run test:unit` xanh. Live-HTTP chỉ xác nhận **sau khi USER reload** (A7).

---

## 9. Boundaries

**Always**
- Đọc `.claude/contexts/` trước, checkpoint sau mỗi việc đáng kể.
- Viết static guard **trước** khi sửa hàng loạt metadata.
- Patch idempotent + `flags.ignore_links=True` + ghi rõ cách rollback.
- Giữ `status` là field tương thích ngược (không xoá) để FE/OAS/mobile không vỡ.
- Tách batch commit riêng khỏi ~144 file uncommitted đang tồn.

**Ask first**
- Supersede ADR `status_vs_workflow_state` (OQ-1).
- Bất kỳ field nào **xoá** khỏi schema (khác với chuyển read-only).
- Đổi `AC Asset.item_code` / gộp `lifecycle_status` (ảnh hưởng FE + OAS baseline).
- Thêm Assignment Rule / Auto Repeat (đổi hành vi vận hành thật, sinh thông báo cho người dùng thật).

**Never**
- Chạy `bench migrate` (A4) hoặc `git commit` (A5).
- Sửa doctype của core Frappe/ERPNext hoặc của app khác trên site chung (A6).
- Sửa `docs/imm-XX/*` do BA sở hữu mà không qua BA (self-correct → surface, không tự viết).
- Xoá dữ liệu/record thật (data-purge phải chờ user duyệt — STATE Blocker#5).
- Tuyên bố "xong" khi chưa chạy test và dán output.

---

## 10. Success criteria (đo được)

| # | Tiêu chí | Cách đo |
|---|---|---|
| SC-1 | 12 hub doctype có `get_data()` ≥1 nhóm liên kết | `test_doctype_connectivity` xanh |
| SC-2 | `get_connections(doctype, name)` trả liên kết + đếm, áp permission | integration test 2 persona (QTV / KTV) |
| SC-3 | Vue: ≥5 màn `*Detail*.vue` render `<RelatedRecords>` từ API chung | vitest + Playwright render-verify (LL-QA-16) |
| SC-4 | **0** doctype có >1 trục trạng thái ghi được | `test_state_axis_invariant` xanh + test tự-cắn |
| SC-5 | 4 doctype Wave-1 chuyển trạng thái qua `apply_workflow`; `_VALID_TRANSITIONS` chép tay giảm về 0 ở các module đã cắt | grep-guard + integration test |
| SC-6 | Danh sách §6.3 còn **0** field sai kiểu | static guard đọc JSON |
| SC-7 | 12 hub doctype có `title_field` + `search_fields` + `in_global_search` | static guard |
| SC-8 | Patch chạy 2 lần cho cùng kết quả (idempotent), có rollback note | test patch chạy đôi |
| SC-9 | `bench run-tests --app assetcore` xanh (trừ 2 đỏ pre-existing của owner IMM-10 — STATE Blocker#4) | dán output |
| SC-10 | OAS baseline **không đổi số path** ngoài `connections` mới; `test_oas_baseline` không đỏ thêm | test hiện có |

---

## 11. Open questions — trạng thái sau khi đo (cập nhật 2026-07-22)

| # | Câu hỏi | Kết luận |
|---|---|---|
| **OQ-1** | Supersede `ADR_status_vs_workflow_state`? | ✅ **ĐÓNG — supersede.** Bằng chứng làm đảo cán cân rủi ro: `status` enum **trùng khớp hoàn toàn** tên state workflow ở **10/12** doctype ⇒ hợp nhất là ánh xạ 1-1; live site `miyano` có **0 record** ở PM WO/Repair/Calibration/Incident/Commissioning/Document/CAPA ⇒ chi phí di trú ≈ 0; 10/12 đã `read_only: 1`. → `ADR-CORE-01_workflow_is_ssot.md` |
| **OQ-2** | `AC Asset.item_code` để làm gì? | ✅ **ĐÓNG — field chết.** 0 tham chiếu ở `services/`/`api/`; mọi hit `item_code` trong FE thuộc ngữ cảnh phụ tùng (`Spare Parts Used`, `CMPartsView`). → ẩn + đánh dấu deprecated, KHÔNG link, KHÔNG xoá cột (T20) |
| **OQ-3** | Nâng `gmdn_code` thành master? | ⏸ **HOÃN** — ngoài phạm vi đợt này (đụng danh mục GMDN + import). Ghi vào backlog |
| **OQ-4** | Đợt 1 mấy hub? | ✅ **12 hub** (đo kết quả rồi mới mở rộng) |
| **OQ-5** | Assignment Rule / Auto Repeat trên site thật? | ⏸ **CỔNG DUYỆT ở Phase 5** — sinh ToDo + email cho người dùng thật, chỉ làm khi user bật đèn xanh |
| **OQ-6** | `AC Asset`: `status` hay `lifecycle_status`? | ✅ **ĐÓNG — `lifecycle_status`.** `ac_asset_lifecycle_workflow.json` đã bind `workflow_state_field = "lifecycle_status"`; `status` (legacy registry, thiếu Draft/Commissioned/Under Maintenance) trở thành rollup dẫn xuất |

---

## 12. Bước kế tiếp (gated)

```
[✔] Phase 1 SPECIFY  ← file này
[✔] Phase 2 PLAN     → PLAN_core_refinement_tasks.md §1–3
[✔] Phase 3 TASKS    → PLAN_core_refinement_tasks.md §4 (T01–T21)
[ ] Phase 4 IMPLEMENT — TDD từng task; KHÔNG tự commit, KHÔNG tự migrate
```
