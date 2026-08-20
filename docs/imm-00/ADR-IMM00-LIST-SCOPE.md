# ADR-IMM00-LIST-SCOPE — Row-scope của AC Asset list: NỘI BỘ read-all vs VENDOR isolation + INVARIANT `count == rows`

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Master / Cross-cutting (RBAC registry) |
| Loại | ADR (cross-cutting — chạm `permissions.py` + `api/imm00.py` + `services/shared/`) |
| Trạng thái | **[GATE] Chốt nghiệp vụ 2026-06-08** (USER eval factory run2, persona KTV phamvanduc) — BE thực thi sau gate |
| Quyết định bởi | USER (chốt) + BA (phân tích role/profile) 2026-06-08 |
| Liên quan | `ADR-IMM00-QR-SCAN-ACTION.md` (capability surface), `04_Backend_Design.md §II.1.x` (RC-LIST-VENDORCLOBBER + INVARIANT count==list), memory `role-profile-persona-architecture` |
| Schema/cap delta | **KHÔNG** — chỉ đổi predicate trong `permissions.py` + cách đếm trong list endpoints. `CAP_SET_VERSION` GIỮ NGUYÊN |

---

## 0. Triệu chứng (P1 — factory run2 [USER] eval 2026-06-08)

Persona **KTV (Kỹ thuật viên nội bộ)** `phamvanduc` mở `/assets`:
- Header "**Tổng 1430 thiết bị**" + phân trang "**1 / 72**" NHƯNG **bảng RỖNG**.
- Tái hiện API: `GET /api/method/assetcore.api.imm00.list_assets?page=1&page_size=5` → `{pagination.total: 1430, items: []}`.

→ `count (1430) != len(rows) (0)`. Vỡ trải nghiệm + vỡ INVARIANT `count == rows` mà docstring `list_assets` tự khẳng định.

---

## 1. Root cause (đã verify tại source — BA mở file đọc lại 2026-06-08)

### RC-1 — `permission_query_conditions` scope KTV nội bộ về `responsible_technician`

`assetcore/permissions.py::ac_asset_query` (dòng 69–80):

```python
def ac_asset_query(user):
    roles = _user_roles(user)
    if _is_senior(roles) or _AUDITOR_ROLE in roles:
        return ""                                   # Super Admin + Manager + Auditor → read-all
    safe = _esc(user)
    if _VENDOR_ROLE in roles:                        # Vendor Engineer
        return f"(`tabAC Asset`.responsible_technician = '{safe}')"
    if roles & _TECHNICIAN_ROLES:                    # PM/Repair/Calibration/Corrective User
        return f"(`tabAC Asset`.responsible_technician = '{safe}')"   # ← BUG: KTV nội bộ bị scope
    return ""
```

KTV nội bộ (`PM User` / `Repair User` / `Calibration User` / `Corrective User`) bị giới hạn về **asset mình là `responsible_technician`**. Thực tế seed/prod: hầu hết asset có `responsible_technician` rỗng hoặc gán người khác → KTV phụ trách **0 asset** → list **0 row**.

### RC-2 — Count path KHÔNG áp `permission_query_conditions` (đếm tất cả 1430)

`assetcore/services/shared/filters.py::count_with_or` (dòng 105–128):
- Nhánh search → `frappe.get_all(... fields=["name"], limit_page_length=0)`.
- Nhánh non-search → `frappe.db.count(doctype, filters)`.

**Cả `frappe.get_all` lẫn `frappe.db.count` đều KHÔNG áp `permission_query_conditions`** (mặc định `ignore_permissions` ở góc độ query-condition). ⟹ count đếm **toàn bộ 1430** asset.

Trong khi **`frappe.get_list`** (items, `api/imm00.py:239`) **CÓ** áp `ac_asset_query` → bị scope về `responsible_technician = <user>` → **0 row**.

⟹ `count (get_all/db.count, không scope) = 1430` ≠ `rows (get_list, có scope) = 0`. Đây là **gốc của lệch count!=rows**.

> **Lưu ý — 2 cơ chế isolation cùng tồn tại cho AC Asset (KHÔNG được nhầm):**
> | Cơ chế | Nơi | Predicate vendor | Áp cho count? | Áp cho get_list? |
> |---|---|---|---|---|
> | `ac_asset_query` (`permission_query_conditions`, hooks.py) | `permissions.py` | `responsible_technician = <user>` | **KHÔNG** (get_all/db.count bỏ qua) | CÓ (Frappe tự inject) |
> | `apply_vendor_scope` (gọi tường minh trong `list_assets`) | `services/shared/scope.py` | `name IN (asset được giao qua PM/CM WO `assigned_to`)` | CÓ (cùng `filters` dict → count_with_or + get_list) | CÓ |
>
> ⟹ Với **VENDOR**, isolation hiệu dụng trong `list_assets` đang ride trên `apply_vendor_scope` (đã áp cho CẢ count lẫn list → INVARIANT giữ cho vendor). Với **KTV nội bộ**, KHÔNG có `apply_vendor_scope` → isolation chỉ đến từ `ac_asset_query` (chỉ áp get_list) → đó là persona làm vỡ INVARIANT. Block RC-LIST-VENDORCLOBBER (`04_Backend_Design.md`) chỉ phân tích Administrator-bypass vs Vendor; **bỏ sót persona KTV nội bộ** — ADR này lấp khoảng đó.

### RC-3 — Docstring `list_assets` khẳng định sai

`api/imm00.py::list_assets` docstring: *"INVARIANT count==drill"* / comment *"INVARIANT total == len(items) cho MỌI persona"*. **SAI** cho mọi persona row-scoped-bằng-`ac_asset_query` mà count không áp cùng predicate (KTV nội bộ trước fix; vendor sẽ đúng vì có `apply_vendor_scope`).

---

## 2. Quyết định nghiệp vụ (USER chốt 2026-06-08)

> **D1 — KTV NỘI BỘ → READ-ALL.** Kỹ thuật viên nội bộ (nhân sự bệnh viện: PM User / Repair User / Calibration User / Corrective User) **xem TOÀN BỘ thiết bị**, KHÔNG scope theo `responsible_technician`. Lý do nghiệp vụ: KTV nội bộ làm việc trên thiết bị toàn viện (ai rảnh nhận việc nấy, trực ca, hỗ trợ chéo khoa) — giới hạn theo người-phụ-trách làm liệt list + sai mô hình vận hành.

> **D2 — VENDOR ENGINEER → VẪN SCOPE (isolation BẤT BIẾN).** Vendor Engineer (KTV của NCC, nhân sự NGOÀI viện) **CHỈ thấy asset họ được giao** — GIỮ NGUYÊN. Đổi D1 cho nội bộ **TUYỆT ĐỐI KHÔNG được nới quyền cho vendor** (ràng buộc bất biến CLAUDE.md §5/§19: vendor isolation row-level). Phải có test chứng minh vendor vẫn isolated SAU fix.

> **D3 — INVARIANT `count == len(items)` cho MỌI persona.** Count phải áp **CÙNG predicate** với `get_list` (permission-aware). Header "Tổng N" luôn == số dòng thực tế (cộng dồn qua các trang).

---

## 3. Phân loại role/profile: NỘI BỘ (read-all) vs VENDOR (scope isolation)

Nguồn: `permissions.py` (`_SENIOR_ROLES`/`_TECHNICIAN_ROLES`/`_VENDOR_ROLE`/`_AUDITOR_ROLE`) + `setup/role_profile_catalog.py` (8 Role Profile VI) + memory `role-profile-persona-architecture`.

### 3.1. NỘI BỘ → `ac_asset_query` trả `""` (read-all, KHÔNG thêm điều kiện)

| Role (Frappe Role name) | Thuộc Role Profile | Lý do read-all |
|---|---|---|
| `AssetCore Super Admin` | Quản trị viên IT | Senior — đã read-all (giữ nguyên) |
| `System Manager`, `Administrator` | (Frappe core) | Senior umbrella — đã read-all |
| `Commissioning Manager`, `Compliance Manager`, `PM Manager`, `Repair Manager`, `Calibration Manager`, `Corrective Manager`, `Inventory Manager`, `Document Manager`, `Procurement Manager`, `Spec Manager`, `Needs Manager`, `Data Manager`, `Training Manager` | Trưởng phòng VT-TTBYT / Trưởng xưởng kỹ thuật / Cán bộ hồ sơ / Thủ kho phụ tùng / Trưởng khoa lâm sàng | Senior (`_SENIOR_ROLES`) — đã read-all |
| `AssetCore Auditor` | Cán bộ QA / Kiểm toán | Read-all READ (write chặn ở DocPerm) — giữ nguyên |
| **`PM User`** | **Kỹ thuật viên** | **MỚI: nội bộ → read-all (D1)** |
| **`Repair User`** | **Kỹ thuật viên** | **MỚI: nội bộ → read-all (D1)** |
| **`Calibration User`** | **Kỹ thuật viên** | **MỚI: nội bộ → read-all (D1)** |
| **`Corrective User`** | **Kỹ thuật viên** / Trưởng khoa lâm sàng | **MỚI: nội bộ → read-all (D1)** |

> 4 role `*User` ở trên là tập `_TECHNICIAN_ROLES` trong `permissions.py:50`, và đúng bằng bộ role của Role Profile **"Kỹ thuật viên"** (`role_profile_catalog.py:55-58`). Đây là nhân sự **NỘI BỘ** → read-all.

### 3.2. VENDOR → `ac_asset_query` GIỮ scope `responsible_technician = <user>`

| Role (Frappe Role name) | Role Profile | Hành vi |
|---|---|---|
| **`Vendor Engineer`** | (KHÔNG nằm trong 8 Role Profile chuẩn — gán role thủ công cho nhân sự NCC; xem ghi chú dưới) | **SCOPE: `(`tabAC Asset`.responsible_technician = '<safe>')`** — GIỮ NGUYÊN (D2) |

> **Ghi chú quan trọng về Vendor Engineer:** role `Vendor Engineer` **KHÔNG** thuộc bất kỳ Role Profile nào trong `ROLE_PROFILE_CATALOG` (8 profile đều là persona NỘI BỘ). Vendor Engineer được gán **role thủ công** (không qua profile) cho tài khoản nhân sự NCC — đây chính là ranh giới "nội bộ vs vendor": **profile-based = nội bộ → read-all; `Vendor Engineer` role = ngoài viện → isolation.** Nếu sau này tạo Role Profile cho NCC, profile đó PHẢI chứa `Vendor Engineer` và KHÔNG được thêm vào nhánh read-all.

### 3.3. SSoT để code phân biệt (BE thực thi)

- **Internal-read-all** = `_is_senior(roles)` ∪ `_AUDITOR_ROLE in roles` ∪ `(roles & _TECHNICIAN_ROLES)`.
- **Vendor-scope** = `_VENDOR_ROLE in roles` AND user **KHÔNG** đồng thời là senior/auditor (senior/auditor thắng → read-all; thứ tự check senior/auditor TRƯỚC vendor — giữ nguyên thứ tự hiện có ở `ac_asset_query`).
- Edge case: 1 user vừa có `Vendor Engineer` vừa có 1 role nội bộ → **read-all thắng** (predicate rỗng). Đây là cấu hình bất thường (vendor không nên có role nội bộ); nếu cần siết "vendor luôn isolated dù có role khác" thì phải đảo thứ tự — **ngoài scope round này, ghi backlog** (mặc định: theo thứ tự hiện tại, senior/internal thắng). Vendor THUẦN (chỉ `Vendor Engineer`) → vẫn scope đúng (đây là case thực tế cần bảo vệ).

---

## 4. FIX KÉP BẮT BUỘC (BE thực thi — đã chốt predicate, BE tự chốt cài đặt)

### (a) `permissions.py::ac_asset_query` — phân biệt nội bộ vs vendor

```python
def ac_asset_query(user=None):
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles) or _AUDITOR_ROLE in roles:
        return ""                                    # senior + auditor → read-all
    if roles & _TECHNICIAN_ROLES:
        return ""                                    # ← D1: KTV NỘI BỘ → read-all (was scoped)
    if _VENDOR_ROLE in roles:                        # ← D2: VENDOR → GIỮ isolation
        safe = _esc(user)
        return f"(`tabAC Asset`.responsible_technician = '{safe}')"
    return ""
```

**Bất biến cài đặt:**
- GIỮ `_esc(user)` (escaping qua `frappe.db.escape`) cho nhánh vendor — KHÔNG mở SQLi.
- Đưa nhánh `_TECHNICIAN_ROLES → ""` **TRƯỚC** nhánh `_VENDOR_ROLE` (để user nội-bộ-kiêm-vendor → read-all, đúng §3.3 edge case mặc định).
- **`ac_asset_has_permission` (detail/IDOR gate, `permissions.py:156`) phải SỬA ĐỒNG BỘ:** nhánh `roles & _TECHNICIAN_ROLES` với `ptype == "read"` hiện trả `_scope_check_assigned(doc, user, "responsible_technician")` → phải đổi thành **`return True`** (read-all) cho KTV nội bộ, NGƯỢC LẠI list read-all nhưng mở 1 asset cụ thể lại 403 (mâu thuẫn). Nhánh vendor (`_VENDOR_ROLE`) trong `ac_asset_has_permission` **GIỮ NGUYÊN** scope `responsible_technician`. Write của technician trên AC Asset vẫn để DocPerm quyết (giữ `return False` cho ptype ghi).

### (b) Count path — áp CÙNG `permission_query_conditions` như `get_list`

`count_with_or` (và nhánh non-search trong `list_assets`) phải permission-aware để bằng `get_list`:

- **Đổi `frappe.get_all` → `frappe.get_list`** trong `count_with_or` (search path): `frappe.get_list(doctype, filters=..., or_filters=..., fields=["name"], limit_page_length=0)`. `get_list` áp `permission_query_conditions` → count khớp items.
- **Nhánh non-search** (`or_filters` rỗng): KHÔNG dùng `frappe.db.count` (không permission-aware). Thay bằng `len(frappe.get_list(doctype, filters=..., fields=["name"], limit_page_length=0))` HOẶC `frappe.get_list(..., limit_page_length=0)` đếm — cùng predicate permission như items.
- GIỮ `or_filters` cho free-text search parity (LIKE) — chỉ đổi hàm đếm, KHÔNG đổi logic OR.
- **GIỮ NGUYÊN** `apply_vendor_scope` + `compose_reserved_into` đã ANDed vào `filters` (RC-LIST-VENDORCLOBBER) — fix này CỘNG THÊM permission-awareness, KHÔNG thay 2 lớp đó. Với vendor: `apply_vendor_scope` (`name in assigned`) AND `ac_asset_query` (`responsible_technician=<user>`) cùng áp → giao của 2 tập (chặt hơn hoặc bằng) — vẫn isolated, KHÔNG nới. Với KTV nội bộ: không `apply_vendor_scope`, `ac_asset_query=""` → read-all đúng.

> **Cân nhắc hiệu năng (BE lưu ý, không chặn fix):** `frappe.get_list(..., limit_page_length=0, fields=["name"])` để đếm sẽ materialize danh sách `name` (tối đa ~1430 hiện tại). Chấp nhận được ở quy mô hiện tại. Nếu cần tối ưu sau: dùng `frappe.get_list(..., as_list=True)` hoặc count qua `DatabaseQuery` có `ignore_permissions=False`. Ghi `[ROADMAP]` nếu dataset lớn lên (>50k) — KHÔNG ép round này.

### (c) Sửa docstring `list_assets`

Bỏ false claim. Khẳng định ĐÚNG: *"INVARIANT `pagination.total == len(items)` (cộng dồn các trang) được enforce vì count và `get_list` dùng CÙNG `filters`/`or_filters` VÀ CÙNG `permission_query_conditions` (count qua `frappe.get_list`, không phải `db.count`/`get_all`). Đúng cho MỌI persona: senior/internal-technician → read-all; Vendor Engineer → isolated theo `responsible_technician` ∩ asset-được-giao-qua-WO."* Giữ phần `byt_status` drill (BR-00-17) — count==drill NĐ98 không đổi (cùng dataset, cùng scope).

---

## 5. Bất biến phải đạt (acceptance — BE viết test chứng minh)

| # | Persona / điều kiện | Yêu cầu | Test (07_Testing_QA) |
|---|---|---|---|
| INV-1 | KTV nội bộ (`PM User`/`Repair User`/`Calibration User`/`Corrective User`), `responsible_technician` ≠ user | list trả **toàn bộ** asset non-reserved (read-all); `total == len(items)` qua các trang | `test_list_assets_internal_technician_read_all` |
| INV-2 | KTV nội bộ mở 1 asset KHÔNG phải mình phụ trách (`get_asset`) | **200** (read OK) — KHÔNG 403 (đồng bộ với list read-all) | `test_get_asset_internal_technician_any` |
| INV-3 | **Vendor Engineer** (THUẦN, không role nội bộ), có asset được giao | CHỈ thấy asset thuộc scope (`responsible_technician=<user>` ∩ assigned-via-WO); `result ⊊ toàn bộ`; KHÔNG thấy asset người khác | `test_list_assets_vendor_isolated_after_internal_readall` |
| INV-4 | **Vendor Engineer** scope rỗng | **0 row** (KHÔNG fallback toàn bộ); `total == 0` | giữ test vendor-empty hiện có |
| INV-5 | Vendor mở asset ngoài scope qua `get_asset` (IDOR) | **403** — `assert_vendor_can_access` GIỮ NGUYÊN | giữ test IDOR hiện có |
| INV-6 | MỌI persona | `pagination.total == len(items_qua_tất_cả_trang)` (count permission-aware == rows) | `test_list_assets_count_equals_rows_all_personas` |
| INV-7 | No-regress | Administrator/Super Admin/Manager/Auditor vẫn read-all; reserved-prefix exclusion (`_`/`SI-`) GIỮ; `byt_status` drill count==tile GIỮ | suite IMM-00 hiện có XANH |

> **INV-3 là test BẮT BUỘC chứng minh vendor KHÔNG bị nới sau khi mở KTV read-all** (ràng buộc D2 / CLAUDE.md §5).

---

## 6. RÀ THÊM — list endpoint khác cùng lỗ count vs permission (BACKLOG, ngoài scope round này)

Cùng pattern "count không permission-aware nhưng list có" có thể tồn tại ở các list endpoint khác dùng `count_with_or`/`frappe.db.count` trong khi items dùng `frappe.get_list` + có `permission_query_conditions` wired:

| DocType (có `permission_query_conditions` trong hooks.py) | Endpoint list nghi ngờ | Trạng thái |
|---|---|---|
| `Incident Report` (`incident_report_query`) | IMM-12 list incidents | **[BACKLOG]** kiểm count path |
| `Asset Repair` (`asset_repair_query`) | IMM-09 list repairs | **[BACKLOG]** kiểm count path |
| `PM Work Order` (`pm_work_order_query`) | IMM-08 list PM WO | **[BACKLOG]** kiểm count path |
| `Asset Commissioning` (`asset_commissioning_query`) | IMM-04 list commissioning | **[BACKLOG]** kiểm count path |

> Round này CHỈ sửa `AC Asset`/`list_assets` (P1 đã tái hiện). 4 endpoint trên: nếu `count_with_or` dùng `get_all`/`db.count` → cùng lỗ count!=rows khi user là technician/vendor row-scoped. **KHÔNG ôm round này.** Khi xử lý: nếu `count_with_or` đã đổi sang `frappe.get_list` (mục 4b) thì 4 endpoint dùng chung helper được fix lây — cần test riêng từng endbpoint để xác nhận. **Lưu ý:** các technician role giờ READ-ALL trên `AC Asset` nhưng các `*_query` kia (`incident_report_query`/`asset_repair_query`/`pm_work_order_query`) VẪN scope technician theo `reported_by`/`assigned_to` — đó là **quyết định riêng cho từng DocType WO** (không nằm trong D1). D1 CHỈ áp cho `AC Asset` (registry đọc-tham-chiếu). KHÔNG tự ý nới các WO query theo D1.

---

## 7. Ràng buộc thực thi (HARD-STOP — quyền user)

- BE chỉ sửa file + chạy `bench --site miyano run-tests` / `migrate`, `npm test` / `vue-tsc`. **TUYỆT ĐỐI KHÔNG** git commit / push / merge / reset DB / drop site / bench restart / reload gunicorn / supervisorctl. Working tree để user review.
- KHÔNG đổi `CAP_SET_VERSION`, KHÔNG thêm cap/role/field/endpoint/enum/patch. ADR này thuần đổi **predicate** + **cách đếm**.
- KHÔNG mâu thuẫn ADR đã có: tương thích `ADR-IMM00-QR-SCAN-ACTION` (capability surface không đổi) + block RC-LIST-VENDORCLOBBER (ADR này CỘNG THÊM lớp permission-aware, KHÔNG gỡ `apply_vendor_scope`/reserved-exclusion).

---

# PHẦN II — §8. INV-ROWSCOPE: `BaseRepository.list(scope=…)` — rows permission-aware KHỚP count (chốt 2026-07-25)

> **Status**: Accepted 2026-07-25 · **Đóng §6 BACKLOG** (4 DocType WO) · Bổ sung, **KHÔNG supersede** §1–§7 (D1/D2/D3 giữ nguyên).
> **Trạng thái thực thi**: [GATE] BA chốt — BE thực thi §8.4/§8.5, FE thực thi §8.8, test §8.9.

## 8.0 Triệu chứng (finding CRITICAL vòng trước — IMM-09, persona KTV nội bộ)

Persona **KTV_A** (`Repair User`, nhân sự nội bộ) mở `/cm/work-orders`:

1. Bảng **HIỆN phiếu `assigned_to == KTV_B`** — đọc được phiếu KHÔNG được giao (rò dữ liệu row-level).
2. Bấm **"Đính ảnh"** trên chính phiếu đó → **403** (`_assert_can_attach_repair_photo`, `services/imm09.py:1204-1215`).
3. Header **"Tổng N" ≠ số dòng** hiển thị.

⟹ Vỡ đồng thời 2 bất biến: `count == rows` (§D3) và **"đọc được ⇒ ghi được"**.

## 8.1 Root cause — lệch **NGƯỢC CHIỀU** so với §1 (đã verify @source 2026-07-25)

Sau fix §4(b), `count_with_or` đếm bằng `frappe.get_list` (`services/shared/filters.py:275-281`) ⟹ **count ĐÃ permission-aware**.
Nhưng `BaseRepository.list` vẫn lấy rows bằng **`frappe.get_all`** (`repositories/base.py:67-75`) ⟹ rows **KHÔNG** áp `permission_query_conditions`.

| DocType | `permission_query_conditions` (hooks.py:439-447) | Predicate cho KTV nội bộ | Hệ quả với `BaseRepository.list` |
|---|---|---|---|
| `AC Asset` | `ac_asset_query` (`permissions.py:66-92`) | `""` (D1 read-all) | Không lộ — predicate rỗng, count==rows tình cờ đúng |
| `Asset Repair` | `asset_repair_query` (`permissions.py:113-121`) | `assigned_to = <user>` | **count < rows + RÒ phiếu người khác** |
| `PM Work Order` | `pm_work_order_query` (`permissions.py:123-131`) | `assigned_to = <user>` | **count < rows + RÒ phiếu người khác** |
| `Incident Report` | `incident_report_query` (`permissions.py:95-111`) | `reported_by = <user>` | cùng lỗ (hiện **0 call site** `.list`) |
| `Asset Commissioning` | `asset_commissioning_query` (`permissions.py:133-146`) | vendor-only | cùng lỗ (hiện **0 call site** `.list`) |

> §1 mô tả lệch **count > rows** (AC Asset: count thô 1430 vs rows scoped 0). §8 là **chiều ngược**: count scoped < rows thô — và chiều này **rò dữ liệu**, nghiêm trọng hơn.
> Doc IMM-09 đã cảnh báo đúng chỗ này từ CR-18 (`docs/imm-09/05_API_Specification.md` §3.1, bullet *"⚠ VERIFY BE Bước-4 (bất đối xứng PQC rows-vs-count)"*) nhưng **chưa chốt quyết định** → ADR này chốt.

## 8.2 Quyết định nghiệp vụ (BA chốt 2026-07-25 — trả lời câu hỏi P0 để mở trong STATE)

> **D4 — SSoT row-scope của PHIẾU CÔNG VIỆC (`Asset Repair` / `PM Work Order`) cho KTV nội bộ = `assigned_to` (KHÔNG read-all).**
> **KHÁC** D1 của `AC Asset`. Lý do phân biệt: `AC Asset` là **registry đọc-tham-chiếu** (KTV không hành động ghi trực tiếp trên record asset) — read-all phục vụ trực ca/hỗ trợ chéo khoa. `Asset Repair`/`PM Work Order` là **phiếu công việc có hành động ghi** (đính ảnh bằng chứng, nộp chẩn đoán, đóng phiếu, nghiệm thu) mà write-gate ĐÃ khoá theo `assigned_to` (`_assert_can_attach_repair_photo` `services/imm09.py:1204-1215`). **Read-gate PHẢI khớp write-gate** — nếu không sẽ tái sinh đúng class-of-bug "đọc được nhưng không ghi được".
> ⟹ `asset_repair_query` / `pm_work_order_query` / `_assert_can_attach_repair_photo` **GIỮ NGUYÊN, KHÔNG sửa**. Cái phải sửa là **rows của list** cho khớp predicate đó.

> **D5 — MỘT predicate row-scope duy nhất cho cả `list` + `count` + `detail` + mọi mutate của CÙNG DocType.** Cấm 2 nhánh (count qua engine A, rows qua engine B). Cách thực thi: cùng đi qua `frappe.get_list` (DatabaseQuery) khi ở chế độ `user`.

> **D6 — Ranh giới "hàng-đợi-việc-của-tôi" (assignment-centric) vs "hồ-sơ-thiết-bị/kế-hoạch" (device-centric).**
> - **Assignment-centric** (danh sách phiếu phân trang có `pagination.total`, chip lọc LIVE, card đếm pair với drill) → **row-scoped**, `scope="user"`.
> - **Device-centric / plan-centric** (lịch sử sửa chữa CỦA THIẾT BỊ, lịch PM toàn viện, KPI tổng hợp) → **KHÔNG** scope theo người được giao; scope tự nhiên là *thiết bị* / *kỳ báo cáo*, `scope="system"`. Căn cứ nghiệp vụ (WHO HTM): traceability gắn với **vòng đời THIẾT BỊ**, không gắn với danh tính người thực hiện — KTV sắp sửa 1 máy PHẢI đọc được lịch sử hỏng hóc do đồng nghiệp xử lý trước đó.
> - **Ràng buộc bắt buộc kèm theo:** payload device-centric là **read-only, KHÔNG có nút hành động**, và **KHÔNG được dùng làm căn cứ cấp quyền** — click sang chi tiết/mutate VẪN qua gate riêng.

> **D7 — Card-đếm PHẢI cùng chế độ scope với drill-list của nó.** Mọi helper đếm mà FE drill vào 1 list `scope="user"` thì helper đó PHẢI permission-aware (`count_with_or(...)`), KHÔNG được dùng `frappe.db.count` / `BaseRepository.count`. Đây là **đóng TODO BA-gated** ghi tại `api/dashboard.py:101-103`.

## 8.3 Contract `BaseRepository.list` (BE thực thi — `assetcore/repositories/base.py`)

```python
LIST_SCOPE_USER   = "user"     # rows + total qua frappe.get_list  (permission-aware)
LIST_SCOPE_SYSTEM = "system"   # rows + total qua frappe.get_all   (ignore permissions)

@classmethod
def list(cls, filters=None, *, fields=None, or_filters=None,
         page=1, page_size=20, order_by=DEFAULT_ORDER,
         scope: str = LIST_SCOPE_USER) -> tuple[list[dict], dict]:
```

| Chế độ | `total` | `rows` | Bất biến |
|---|---|---|---|
| `scope="user"` (**mặc định — fail-safe**) | `count_with_or(...)` → `frappe.get_list(limit_page_length=0)` | `frappe.get_list(..., limit_start, limit_page_length)` | CÙNG DatabaseQuery engine, CÙNG `filters`/`or_filters`, CÙNG `permission_query_conditions` + DocPerm + User Permission ⇒ `total == len(rows)` khi `total ≤ page_size` |
| `scope="system"` | `count_ignore_permissions(...)` → `frappe.get_all(limit_page_length=0)` | `frappe.get_all(...)` (**y hệt hôm nay**) | CÙNG engine không-permission ⇒ `total == len(rows)` khi `total ≤ page_size` |

**Ràng buộc cài đặt (BẮT BUỘC):**
- `scope` là **keyword-only**; giá trị ngoài `{"user","system"}` → `ValueError` ngay (fail-fast, chống typo `"System"` biến thành silent-permissive).
- **Mặc định `"user"`** = fail-safe: call site quên khai báo thì bị SIẾT, không bị NỚI.
- `count_ignore_permissions` đặt **cạnh** `count_with_or` trong `assetcore/services/shared/filters.py`, **mirror byte-for-byte** trừ entrypoint (`frappe.get_all` thay `frappe.get_list`) — 2 counter không được drift về cách xử lý `or_filters`/`filters`.
- **KHÔNG** đụng `permissions.py`, **KHÔNG** thêm/sửa DocPerm, **KHÔNG** đổi `CAP_SET_VERSION`.
- `find_one` / `count` / `exists` **giữ nguyên** vòng này (xem §8.10 backlog).

> **Ghi chú de-risk (verify @source):** MỌI call site `BaseRepository.list` hiện tại **ĐÃ** chạy `frappe.get_list` một lần cho `total` (`base.py:64-65`) ⟹ DocPerm read đã được enforce sẵn cho toàn bộ ~50 call site. Chuyển rows sang `get_list` **chỉ cộng thêm** `permission_query_conditions` + User Permission vào rows — KHÔNG mở ra lớp lỗi permission mới. Ngược lại `scope="system"` **gỡ** DocPerm-check khỏi đường đếm; an toàn vì mọi call site `system` đều **vứt bỏ `pg`** (`rows, _ = …`) — xem ma trận §8.4.

### 8.3b Cải chính SAU thực thi — `scope="system"` **KHÔNG** được bỏ DocPerm cấp vai-trò

> ⚠️ **[BE thực thi 2026-07-25 để đóng finding HIGH — CHỜ [BA] RATIFY hậu kiểm]**
> §8.3 (bản đầu) mô tả `system` là *"ignore permissions"*. Thực thi đúng chữ đó tạo **lỗ Broken Access Control (OWASP A01)**: `frappe.get_all` bỏ **HAI** thứ khác bản chất, trong khi **D6 chỉ ratify nới MỘT**.

| Trục | Nghĩa | D6 ratify nới? |
|---|---|---|
| **ROW-scope** | `permission_query_conditions` + User Permission ("dòng nào là của tôi") | ✔ CÓ — device/plan-centric |
| **ROLE-scope** | DocPerm `read` trên DocType (`Has Role` → `DocPerm`) — "vai trò nào được đọc bảng này" | ❌ **KHÔNG** |

**Bằng chứng lỗ (probe thật, trước fix):** user chỉ có role `PM User` (`frappe.has_permission("Asset Repair","read") == False`) gọi `api/imm09.get_asset_repair_history` → `success:true` + đầy đủ `WO-CM-*` (`repair_type`/`mttr_hours`/`root_cause_category`). Đối xứng: `Repair User` gọi `api/imm08.get_pm_calendar` → nhận event của người khác kèm `assigned_to`. Trước khi tham-số-hoá `scope`, DocPerm được enforce như **tác dụng phụ** (mọi call site chạy `frappe.get_list` một lần cho `total`); tham-số-hoá đã gỡ tác dụng phụ đó mà **không** thay bằng gate tường minh.

**Contract sau cải chính — 3 chế độ (`assetcore/repositories/base.py`):**

| `scope` | ROLE-scope (DocPerm read) | ROW-scope | Engine | Dùng cho |
|---|---|---|---|---|
| `"user"` (mặc định, fail-safe) | ✔ enforce | ✔ enforce | `frappe.get_list` | list phiếu-của-tôi |
| `"system"` | ✔ **enforce** (gate tường minh) | ✘ bỏ | `frappe.get_all` | device/plan-centric (D6), KPI kỳ báo cáo |
| `"internal"` (**MỚI**) | ✘ bỏ | ✘ bỏ | `frappe.get_all` | scheduler · domain-logic nội bộ · denorm-enrich NHÃN |

- Gate = `services/shared/permissions.py::assert_doctype_read_permission(doctype)`, **mirror byte-for-byte** `DatabaseQuery._set_permission_map` (`frappe/model/db_query.py:577-583`): cùng `ptype` (`select` khi user chỉ có select-perm, ngược lại `read`) ⇒ **không chặt hơn cũng không lỏng hơn** nhánh `user`; khác biệt còn lại đúng bằng ROW-scope.
- Raise `frappe.PermissionError` (KHÔNG `frappe.throw`) ⇒ cùng một loại exception với nhánh `user` để `run_rowscoped` bọc chung, và KHÔNG đẩy tên DocType vào `_server_messages`.
- `"internal"` tồn tại để **ý định hiện ra mặt chữ**: chỗ nào thật sự phải bỏ mọi kiểm tra (job không có session-user; lookup NHÃN cho row đã scoped ở tầng cha) thì khai `internal`, KHÔNG mượn `system`. Guard tĩnh chặn `internal` lan sang endpoint người-dùng: `tests/test_rowscope_scope_guard.py` (allowlist phải khớp ma trận §8.4).

**[BA] cần ratify hậu kiểm:** (a) tên + ngữ nghĩa 3 chế độ; (b) phân loại `system` vs `internal` của từng call site trong ma trận §8.4 (cột đã cập nhật); (c) hệ quả nghiệp vụ: persona **thiếu DocPerm read** trên `PM Work Order`/`Asset Repair` nay nhận **403 envelope** thay vì dữ liệu ở `get_pm_calendar`/`get_asset_repair_history` — nếu nghiệp vụ MUỐN họ đọc được thì lời giải đúng là **cấp DocPerm read** (B2), KHÔNG phải mở lại lỗ A01.

## 8.4 Ma trận 16 call site `*Repo.list(` trên 5 DocType row-scoped (verify @source 2026-07-25)

`CommissioningRepo.list` / `IncidentRepo.list`: **0 call site** hiện tại (2 DocType vẫn liệt kê vì có hook — bất kỳ call site MỚI phải khai `scope` tường minh).

> ⚠️ **Cải chính 2026-07-25 — ma trận này KHÔNG phủ hết bề mặt.** "0 call site `IncidentRepo.list`" **không** đồng nghĩa "`Incident Report` không bị phục vụ ra client": `services/imm12.py::get_asset_incident_history` truy vấn **THẲNG** `frappe.get_all('Incident Report')` + `frappe.db.count` ⇒ bỏ CẢ ROW-scope LẪN DocPerm read mà **G1–G3 không nhìn thấy** (3 guard đó chỉ soi call site `*Repo.list`). Đây là lỗ A01 thứ hai, cùng class với §8.3b nhưng ở đường raw-query. Đã đóng: gate `assert_doctype_read_permission(_DT_INCIDENT)` + `@rowscoped` (ngữ nghĩa = `scope="system"`, D6 device-centric — xem `docs/imm-12/05_API_Specification.md §20.1`), và **guard G4 MỚI** (`tests/test_rowscope_scope_guard.py`) chặn endpoint đọc MỚI truy vấn raw một DocType row-scoped mà không gate. G4 mang theo **backlog 17 call site raw chưa gate** (`imm04.list_commissioning`, `imm08.get_calendar`, `imm12.list_incidents`, `api/imm00.*depreciation*`, …) — chỉ chặn THÊM MỚI, xem B8 §8.10.

| # | Call site (raw-query, KHÔNG qua Repo) | Hàm bao | Trục quyền | Cơ chế |
|---|---|---|---|---|
| I1 | `services/imm12.py::get_asset_incident_history` | chính nó | ROLE ✔ / ROW ✘ (= `system`) | `assert_doctype_read_permission` + `@rowscoped`; giữ `frappe.get_all` để `truncation_meta` COUNT **lazy** (repo tính `total` eager ⇒ phá zero-cost) |

| # | Call site | Hàm bao | `scope` | Lý do (comment 1 dòng ở code) | `pg` dùng? |
|---|---|---|---|---|---|
| R1 | `services/imm09.py:856` | `check_repair_sla_breach()` — scheduler hourly | `internal` | scheduler, không session-user; quét toàn viện | ✗ |
| R2 | `services/imm09.py:892` | `check_repair_overdue()` — scheduler daily 07:00 | `internal` | scheduler, gửi mail Repair Manager | ✗ |
| R3 | `services/imm09.py:1040` | `_fetch_all_repair_rows()` — helper loop-paginate | **tham-số-hoá** | thêm param `scope`, KHÔNG default ẩn; 2 caller truyền tường minh | ✓ (`total_pages`) |
| R3a | `services/imm09.py:607` | `cm_sla_breach_count()` — card KPI | `user` | **D7**: card pair drill `?sla_breached_live=1` (đã `user`) ⇒ phải cùng scope | — |
| R3b | `services/imm09.py:1072` | `_list_sla_breached_live()` — chip LIVE | `user` | endpoint list người dùng (membership == badge) | — |
| R4 | `services/imm09.py:1108` | `list_work_orders()` — path chính | `user` | **endpoint list người dùng** (A3) | ✓ |
| R5 | `services/imm09.py:2054` | `get_asset_history(asset_ref)` | `system` (role-gated §8.3b) | **D6 device-centric**: lịch sử sửa chữa CỦA THIẾT BỊ, read-only, không nút hành động | ✗ |
| R6 | `services/notifications.py:1107` | `run_sla_breach_scan()` — scheduler hourly | `internal` | scheduler notification, quét toàn viện | ✗ |
| P1 | `services/imm08.py:710` | `_fetch_all_pm_rows()` — helper loop-paginate | **tham-số-hoá** | caller duy nhất `_list_pm_overdue_live` truyền `user` | ✓ (`total_pages`) |
| P2 | `services/imm08.py:771` | `list_work_orders()` — path chính | `user` | **endpoint list người dùng** (A5) | ✓ |
| P3 | `services/imm08.py:1392` | `get_calendar(year, month)` | `system` (role-gated §8.3b) | **D6 plan-centric**: lịch PM toàn viện phục vụ điều phối ca trực; đã có param `technician` để tự thu hẹp | ✗ |
| P4 | `services/imm08.py:1435` | `get_dashboard_stats()` — tile tháng | `system` (role-gated §8.3b) | KPI tổng hợp (không phơi danh tính từng phiếu) | ✗ |
| P5 | `services/imm08.py:1489` | `get_dashboard_stats()` — trend 6 tháng | `system` (role-gated §8.3b) | KPI tổng hợp, cùng mẫu với P4 (INV-PM-KPI-6) | ✗ |
| A1 | `services/imm11.py:819` | `perform_lookback_assessment()` — BR-11-03 | `internal` | domain-logic nội bộ (tìm asset cùng device_model), không trả ra FE | ✗ |
| A2 | `services/imm11.py:964` | `list_schedules()` — enrich `asset_name` | `internal` | **denorm-enrich**: join tên hiển thị cho row ĐÃ scoped ở tầng cha | ✗ |
| A3 | `services/imm11.py:1038` | `list_calibrations()` — enrich `asset_name` | `internal` | denorm-enrich (như A2) | ✗ |
| A4 | `services/imm11.py:1646` | `get_due_calibrations()` — danh sách đến hạn | `system` (role-gated §8.3b) | **D6 device-centric**: danh sách THIẾT BỊ đến hạn hiệu chuẩn (không phải phiếu-của-tôi); `AC Asset` đã read-all cho nội bộ (D1) ⇒ chỉ khác với Vendor Engineer | ✗ |
| A5 | `services/imm05.py:231` | `list_documents()` — enrich `asset_name` | `internal` | denorm-enrich (như A2) | ✗ |

> **A2/A3/A5 (denorm-enrich) BẮT BUỘC `internal` (§8.3b — trước cải chính ghi `system`):** nếu để `user`, Vendor Engineer sẽ bị `ac_asset_query` cắt mất tên hiển thị ⇒ cột "Thiết bị" trống trên chính row họ ĐƯỢC PHÉP xem (over-block, vi phạm A6). Scope thật đã áp ở tầng cha.

### 8.4b Companion BẮT BUỘC cùng vòng (D7 — nếu bỏ, vòng này TẠO lệch card≠drill MỚI)

| Helper | Hiện tại | Đổi thành | Vì sao bắt buộc |
|---|---|---|---|
| `services/imm09.py:601` — nhánh `flagged` của `cm_sla_breach_count()` | `RepairRepo.count({"sla_breached": 1})` → `frappe.db.count` (**không** permission-aware) | `count_with_or(RepairRepo.DOCTYPE, {"sla_breached": 1}, None)` | Nhánh (2) của cùng hàm chuyển sang `user` (R3a) ⇒ để nguyên nhánh (1) = card trộn global+scoped (vô nghĩa) |
| `services/imm08.py:287` — `count_overdue_pm()` | `PMWorkOrderRepo.count(filters)` → `frappe.db.count` | `count_with_or("PM Work Order", filters, None)` | Docstring chính nó khẳng định *"KPI == drill-down `_normalize_filters(overdue=1)`, KHÔNG divergence"*; drill nay `user`-scoped ⇒ card global sẽ phá lời khẳng định đó |

Bằng chứng đối chiếu: các card khác trên CÙNG dashboard (`cm_open`, `cm_repeat_failure`, `pm_due_next7`, …) **ĐÃ** permission-aware qua `_count()` (`api/dashboard.py:81-85`, nhánh `_perm_scoped_doctypes()`). 2 helper trên là ngoại lệ còn sót, gọi qua `_scoped_helper` (`api/dashboard.py:176, 197, 427`) — chính là TODO "BA-gated" ở `api/dashboard.py:101-103`. D7 đóng TODO đó.

## 8.5 Semantics lỗi — 2 loại 403 (BẮT BUỘC, spec-contract DONE-gate)

`frappe.get_list` **raise `frappe.PermissionError`** khi session-user KHÔNG có DocPerm `read` trên DocType. `handle()` (`utils/api_handler.py:47-52`) **cố ý KHÔNG bắt Exception chung** ⇒ hiện tại sẽ bubble thành HTTP-500 / trang lỗi Frappe, KHÔNG phải envelope.

> **BR-00-ROWSCOPE-403 (chốt):** trên đường `scope="user"`, `frappe.PermissionError` PHẢI được chuyển thành **`ServiceError(ErrorCode.FORBIDDEN, http_status=403)`** tại **service layer** (`imm08.list_work_orders` / `imm09.list_work_orders`) ⇒ `handle()` trả **HTTP-200 + Error envelope** (`success:false`, `code`, `error` tiếng Việt). **KHÔNG** raise để thành HTTP-4xx; **KHÔNG** trả list rỗng giả (silent-empty che RBAC misconfig = anti-pattern "dead-gate").
>
> Phân biệt rõ 2 loại 403 (KHÔNG được trộn):
> | Loại | Nơi phát | HTTP | Client xử lý |
> |---|---|---|---|
> | **dispatcher-403** | Frappe dispatcher, guest/không token, TRƯỚC khi vào handler | 403 (hoặc 401 qua `session_guard`) | mobile → logout/re-auth |
> | **in-handler cap-403** | service layer (BR-00-ROWSCOPE-403) — user còn phiên nhưng thiếu DocPerm/quyền row | **200** + Error envelope | hiển thị message, KHÔNG logout |

> **[BE thực thi 2026-07-25 — mở rộng phạm vi, chờ [BA] xác nhận]** Bọc thủ công chỉ phủ **2/≈20** entrypoint (`imm08`/`imm09.list_work_orders`); phần còn lại vẫn ném `PermissionError` trần ⇒ BR-00-ROWSCOPE-403 **thủng trên chính đường mà nó định vá** (vd `get_due_pm_schedules`, `get_pm_dashboard_stats`). Vì vậy `run_rowscoped` được bổ sung dạng decorator **`@rowscoped`** (`services/shared/permissions.py`) và dán cho **MỌI entrypoint đọc** `list_*`/`get_*` chạy `Repo.list(scope="user"|"system")` trong `imm05/06/08/09/11/15/16`. Guard chống rot: `tests/test_rowscope_scope_guard.py::test_read_entrypoints_wrap_permission_error` (AST — entrypoint đọc mới quên bọc = đỏ ngay).

**Persona bị ảnh hưởng (verify @source `asset_repair.json` / `pm_work_order.json` — permissions block):**

| DocType | Có DocPerm `read` | KHÔNG có DocPerm `read` → nhận in-handler 403 |
|---|---|---|
| `Asset Repair` | `AssetCore Super Admin`, `Repair Manager`, `Repair User`, `AssetCore Auditor`, `Commissioning Manager` | `Calibration User`, `Corrective User`, `PM User`, **`Vendor Engineer`** |
| `PM Work Order` | `AssetCore Super Admin`, `PM Manager`, `PM User`, `AssetCore Auditor`, `Commissioning Manager` | `Calibration User`, `Corrective User`, `Repair User`, **`Vendor Engineer`** |

> ⚠️ **Đây KHÔNG phải regression của vòng này**: `count_with_or` đã dùng `frappe.get_list` từ trước (§4b) nên các persona trên **hiện tại đã** vỡ ở đường đếm. Vòng này chỉ **biến 500 câm thành 403 có message**.
> **[BACKLOG-P1 — cần USER/BA ratify riêng] Vendor Engineer thiếu DocPerm `read` trên `Asset Repair`/`PM Work Order`** trong khi contract mobile + `apply_vendor_scope` giả định vendor list được. **TUYỆT ĐỐI KHÔNG nới DocPerm trong vòng này** (A7). Ghi backlog, quyết riêng.

## 8.6 Boundaries (Always / Ask-first / Never)

**Always**
- Mọi call site `BaseRepository.list` trên 5 DocType row-scoped khai `scope=` **TƯỜNG MINH** + comment 1 dòng lý do.
- `total` và `rows` LUÔN cùng một engine (§8.3) — không bao giờ 2 nhánh.
- Card-đếm và drill-list của nó cùng chế độ scope (D7).
- Lỗi quyền trên list = in-handler HTTP-200 + Error envelope (BR-00-ROWSCOPE-403).

**Ask-first (BA/USER chốt trước khi làm)**
- Đổi bất kỳ `*_query` predicate nào trong `permissions.py`.
- Thêm/sửa DocPerm hay Role Profile để "cho test xanh".
- Đổi 1 call site từ `system` → `user` (hoặc ngược lại) ngoài ma trận §8.4.
- Nới `get_calendar` / `get_asset_history` sang row-scope (đổi kết quả nghiệp vụ).

**Never**
- ❌ Sửa `asset_repair_query` / `pm_work_order_query` / `_assert_can_attach_repair_photo` để "khớp list" (D4 — SSoT giữ nguyên).
- ❌ Nới DocPerm / thêm role vào doctype JSON để chữa test đỏ (A7).
- ❌ Trả list rỗng thay cho 403 khi persona thiếu quyền.
- ❌ Đổi `CAP_SET_VERSION`, thêm cap/field/endpoint/patch.
- ❌ `git commit/push/merge` · `reset DB` · `drop site` · `bench restart` / reload gunicorn (HARD-STOP — quyền USER).

## 8.7 Fallback khi call site đỏ (A7 — quy tắc BẮT BUỘC)

Nếu 1 call site `scope="user"` đỏ vì `frappe.get_list` **strip field `permlevel > 0`** (hoặc field không đọc được):
1. Chuyển **ĐÚNG call site đó** (không phải cả module) sang `scope="system"` + comment `# [ROWSCOPE-FALLBACK] <lý do>` + ghi backlog.
2. **TUYỆT ĐỐI KHÔNG** nới DocPerm / thêm DocPerm `permlevel` để chữa (bẫy `permlevel_no_docperm_silent_strip`).
3. Verify trước: **5 DocType row-scoped hiện KHÔNG có field `permlevel > 0`** (đã đọc 5 file `<doctype>.json` — `permlevel fields: []`, `perms permlevels: [0]`) ⇒ rủi ro này thấp; nếu vẫn đỏ thì nguyên nhân là **DocPerm read thiếu** → xử theo §8.5, KHÔNG theo §8.7.

## 8.8 FE contract — "Tổng" đọc TỪ server (INV-ROWSCOPE-FE)

`frontend/src/views/cm/CMWorkOrderListView.vue:165` hiện render `Tổng ${store.pagination.total ?? store.workOrders.length}`.

> **Quy tắc:** "**Tổng**" = **`pagination.total` của server** (SSoT toàn tập, mọi trang). Fallback `?? store.workOrders.length` PHẢI bỏ → `?? 0`. Fallback client-count là **fallback nói dối**: khi BE lỗi/rỗng nó hiển thị số dòng của TRANG HIỆN TẠI như thể là tổng ⇒ với `page_size=20` và 137 phiếu, header báo "Tổng 20". Nó cũng **che chính bug row-scope** này (rows thô 40 = "tổng" trông hợp lý trong khi total thật là 2).
> "**Hiển thị X**" (dòng 227 mobile-card, 286 desktop-table) **GIỮ** `store.workOrders.length` — đúng ngữ nghĩa "số dòng trang hiện tại".
> Guard vitest: render với `pagination.total = 2` + `workOrders.length = 40` ⇒ header chứa `Tổng 2`, KHÔNG chứa `Tổng 40`; và với `pagination` chưa nạp ⇒ `Tổng 0`.

## 8.9 Bất biến phải đạt (acceptance — BE/FE viết test chứng minh)

| # | Điều kiện | Yêu cầu | Test |
|---|---|---|---|
| INV-ROWSCOPE-1 | `scope="user"`, `total ≤ page_size` | `pagination.total == len(rows)` | `test_rowscope_invariant::test_user_scope_total_equals_rows` |
| INV-ROWSCOPE-2 | `scope="system"`, `total ≤ page_size` | `pagination.total == len(rows)` | `test_rowscope_invariant::test_system_scope_total_equals_rows` |
| INV-ROWSCOPE-3 | `scope` sai giá trị (`"System"`, `""`, `None`) | `ValueError` (fail-fast) | `test_rowscope_invariant::test_invalid_scope_raises` |
| INV-ROWSCOPE-4 | **KTV_A** (session user THẬT, KHÔNG Administrator), `list_repair_work_orders` **không** truyền `mine` | 0 phiếu có `assigned_to == KTV_B`; `pagination.total == len(data.data)` | `test_rowscope_invariant::test_imm09_list_excludes_other_technician` |
| INV-ROWSCOPE-5 | KTV_A, **mọi** row trong list | `services.imm09._assert_can_attach_repair_photo(RepairRepo.get(name))` KHÔNG raise | `test_rowscope_invariant::test_read_implies_write_repair_photo` |
| INV-ROWSCOPE-6 | KTV_A, `list_pm_work_orders` | 2 assert như INV-ROWSCOPE-4 (đối xứng PM) | `test_rowscope_invariant::test_imm08_list_excludes_other_technician` |
| INV-ROWSCOPE-7 | Persona **senior/quản lý** (`Repair Manager`/`PM Manager`/Super Admin) | thấy ĐỦ cả 2 phiếu; `total == 2` (KHÔNG over-block) | `test_rowscope_invariant::test_senior_sees_all` |
| INV-ROWSCOPE-8 | **Vendor Engineer THUẦN** | KHÔNG bị nới quyền (D2 bất biến): không thấy phiếu ngoài scope | `test_rowscope_invariant::test_vendor_not_widened` |
| INV-ROWSCOPE-9 | Persona thiếu DocPerm `read` gọi list | **HTTP-200 + Error envelope** `success:false` (KHÔNG 500, KHÔNG list rỗng) | `test_rowscope_invariant::test_missing_docperm_returns_error_envelope` |
| INV-ROWSCOPE-10 | D7 — KTV_A | `cm_sla_breach_count()` == số row của drill `?sla_breached_live=1`; `count_overdue_pm()` == số row drill `?overdue=1` | `test_rowscope_invariant::test_card_equals_drill_per_persona` |
| INV-ROWSCOPE-11 | No-regress | `test_imm09`/`test_imm08`/`test_imm11`/`test_imm05`/`test_imm00`/`test_rbac`/`test_list_search_filter` XANH | suite hiện có |
| INV-ROWSCOPE-FE | FE | "Tổng" từ `pagination.total ?? 0`; "Hiển thị" từ `.length` | vitest guard §8.8 |

> **INV-ROWSCOPE-5 là test BẮT BUỘC đóng finding CRITICAL** — nó phát biểu trực tiếp "đọc được ⇒ ghi được".
> **INV-ROWSCOPE-4/6 PHẢI chạy dưới session user THẬT** (`frappe.set_user(ktv_a)`), KHÔNG Administrator — Administrator bypass `permission_query_conditions` nên test sẽ **xanh giả**.

## 8.10 Backlog mở ra (KHÔNG làm vòng này)

| # | Việc | Ưu tiên |
|---|---|---|
| B1 | `BaseRepository.count` / `find_one` / `exists` cũng bỏ qua permission (`frappe.db.count` / `get_all`) — cùng class-of-bug, chưa tham-số-hoá | P1 |
| B2 | **Vendor Engineer thiếu DocPerm `read`** trên `Asset Repair` / `PM Work Order` trong khi contract mobile giả định vendor list được (§8.5) | P1 · cần USER ratify |
| B3 | ~~Detail-gate IDOR: `RepairRepo.get` → `frappe.get_doc` KHÔNG tự gọi `has_permission` ⇒ mở `/cm/work-orders/<phiếu người khác>` bằng URL trực tiếp vẫn đọc được dù list đã ẩn~~ → **NÂNG P0 + ĐANG ĐÓNG bằng [§9 INV-ROWSCOPE-DETAIL (CR-74)](#phần-iii--9-inv-rowscope-detail-cr-74-4-get-detail-đi-qua-cùng-1-predicate-quyền-đọc-chốt-2026-07-25)** cho 4 op C6-DETAIL; phần còn lại (imm04/05/15/16 + web-only detail) = B10 §9.9 | ✅ §9 |
| B4 | Ratify `get_calendar` (P3) / `get_asset_history` (R5) / `get_due_calibrations` (A4) có nên row-scope (D6 hiện chọn `system`). **Cập nhật 2026-07-25:** 3 call site này nay **role-gated** (§8.3b) ⇒ câu hỏi còn lại đúng bằng "trong số người CÓ DocPerm read, có cần lọc thêm theo `assigned_to` không" | P2 · cần USER ratify |
| B5 | ~~Guard chống hồi quy: lint/test cấm `BaseRepository.list(` không khai `scope=`~~ → **ĐÃ LAND 2026-07-25** dạng mạnh hơn: `tests/test_rowscope_scope_guard.py` (G1 scope literal hợp lệ · G2 allowlist call site non-`user` phải khớp ma trận §8.4 · G3 entrypoint đọc phải bọc `@rowscoped`). **Còn lại**: ~28 call site vẫn nhận default ẩn `scope="user"` — default là fail-safe (siết) nên KHÔNG phải lỗ, chỉ là thiếu tường minh | ✅ DONE (phần còn lại P3) |
| B7 | **Perf (đo 2026-07-25, CHƯA cần sửa):** `count_with_or` materialize toàn bộ cột `name` (`limit_page_length=0`). Đo trên site dev: 1.6 ms @104 dòng · 5.1 ms @1060 dòng (≈ **4 ms/1000 dòng**, tuyến tính). Dạng aggregate `frappe.get_list(fields=["count(name) as _c"])` cho **cùng con số** (11/11 case đối chiếu, 0 lệch — cùng DatabaseQuery ⇒ cùng predicate) và **phẳng ~0.9 ms**. Hot path hiện tại KHÔNG nghẽn: `PM Work Order` = 0 dòng, `Asset Repair` = 9 dòng, `count_overdue_pm()` p95 = 1.96 ms, `imm08.get_dashboard_stats` p95 = 24 ms ⇒ **hoãn tối ưu** (measure-first). Kích hoạt khi 1 DocType được đếm vượt ~20k dòng | P2 · có sẵn recipe |
| B6 | Cite-drift: claim `@file:line` trong docs/OAS không có guard (4 cite đã rot) | P2 |
| B8 | **17 endpoint đọc truy vấn RAW DocType row-scoped, CHƯA gate** (allowlist `_RAW_QUERY_UNGATED_BACKLOG` trong `tests/test_rowscope_scope_guard.py::G4`): `imm04.list_commissioning` / `imm04.get_dashboard_stats` / `imm04.list_my_pending_approvals` / `imm08.get_calendar` / `imm08.get_due_pm_schedules` / `imm12.list_incidents` / `imm12.get_incident_stats` / `imm12.get_dashboard` / `api/dashboard.get_overview` / `api/imm00.{get_asset_kpi, list_audit_trail, list_incidents, list_pm_schedules, list_assets_depreciation, get_depreciation_stats, get_depreciation_by_category}` / `api/purchase.get_purchase_commissionings`. Mỗi dòng cần [BA] ratify: device/KPI-centric (gate ROLE, nới ROW) hay phải row-scope thật. G4 **chỉ chặn thêm mới** ⇒ 17 dòng này KHÔNG làm đỏ build | P1 · cần BA ratify từng dòng |
| B9 | **Vendor isolation trên `Incident Report` hiện dựa HOÀN TOÀN vào DocPerm** (Vendor Engineer 0 read) chứ không phải clause row-scope — nếu cấp read cho vendor thì `get_asset_incident_history` PHẢI chuyển row-scope. Ghim bằng `test_rowscope_docperm_gate::test_incident_history_vendor_isolated` (fail-loud) | P2 · cần BA ratify |

---

# PHẦN III — §9. INV-ROWSCOPE-DETAIL (CR-74): 4 GET-detail đi qua CÙNG 1 predicate quyền-đọc (chốt 2026-07-25)

> **Đây là thực thi của backlog B3 §8.10** ("Detail-gate IDOR: `RepairRepo.get` → `frappe.get_doc` KHÔNG tự gọi `has_permission`"), nâng từ P1 lên **P0** vì §8 vừa siết `list` ⇒ khoảng cách read-vs-write giờ nằm TRỌN ở đường **detail**.

| Mục | Giá trị |
|---|---|
| CR | **CR-74** — cụm **C6-DETAIL** mobile |
| Module | IMM-08 · IMM-09 · IMM-11 · IMM-12 (4 op) |
| Lớp chạm | `assetcore/services/imm08.py` · `imm09.py` · `imm11.py` · `imm12.py` · `services/shared/permissions.py` (helper mới) |
| Schema/cap delta | **KHÔNG** — 0 DocType, 0 field, 0 DocPerm, 0 cap, 0 endpoint, 0 param. `CAP_SET_VERSION` GIỮ NGUYÊN |
| OAS delta | **Mô tả + ngữ nghĩa 403** (`paths` GIỮ **105** · `components.schemas` **+0** · slot `{200,401,403}` KHÔNG đổi · shape payload success **byte-identical**) |

## 9.0 Triệu chứng — "đọc chi tiết không cần quyền"

Sau §8, KTV nội bộ **không còn thấy** phiếu của đồng nghiệp trong `list` (row-scope `assigned_to`, D4) và **không đính được ảnh** vào phiếu đó (write-gate `_assert_can_attach_repair_photo` `services/imm09.py:1244-1254`). Nhưng dán thẳng URL / gọi thẳng `get_repair_work_order?name=<phiếu người khác>` thì **vẫn đọc trọn hồ sơ** — kể cả persona **0 DocPerm read** trên DocType đích.

Đây là **cùng class-of-bug** với §8.0 nhưng **ngược đầu**: §8 lệch *count-vs-rows*, §9 lệch *list/write-vs-detail*. Hệ quả nghiệp vụ giống hệt: một người dùng nhìn thấy hai sự thật mâu thuẫn về **cùng một phiếu**.

## 9.1 Root cause — verify @source 2026-07-25 (BA mở file đọc lại)

### RC-9.1 — `frappe.get_doc` KHÔNG kiểm tra quyền (mặc định)

`BaseRepository.get` (`assetcore/repositories/base.py:53-57`) = `frappe.db.exists(...)` → `frappe.get_doc(...)`. `frappe.get_doc` (`frappe/model/document.py:36-…`) chỉ `load_from_db`, **KHÔNG** gọi `check_permission`. Kiểm tra quyền của Frappe nằm ở `Document.check_permission` (`frappe/model/document.py:227`) → `Document.has_permission` (`:230-242`) → `frappe.permissions.has_permission(...)` — **không đường nào trong 4 service hiện tại chạm tới**.

> ⚠️ Cải chính docstring cũ: comment ở `assetcore/permissions.py:150-153` nói `has_permission` hook chạy *"including the implicit call inside `frappe.get_doc()`"* — **SAI với v15**. Hook CHỈ chạy khi có ai đó gọi `frappe.has_permission(doctype, ptype, doc=…)` / `doc.check_permission(...)`. Đây chính là lý do bug tồn tại **dù hook đã đăng ký đầy đủ** ở `hooks.py:448-455`.

### RC-9.2 — `frappe.has_permission(..., doc=doc)` LÀ predicate hợp nhất (ROLE + ROW + User Permission)

`frappe/permissions.py:77-194` `has_permission(doctype, ptype, doc=…)` → `get_doc_permissions(doc, …)` (`:196`) chạy theo thứ tự:

1. `has_controller_permissions(doc, ptype, user)` (`frappe/permissions.py:442-460`) — **dispatch `hooks.has_permission[doctype]`** ⇒ chính `asset_repair_has_permission` / `pm_work_order_has_permission` / `incident_report_has_permission` của AssetCore;
2. `get_role_permissions(meta, …)` — **DocPerm cấp vai-trò**;
3. `has_user_permission(doc, …)` — **User Permission**.

⟹ **MỘT lời gọi phủ cả 3 trục.** Đây là predicate mà D5 (§8.2) đã yêu cầu — chỉ là đường `detail` chưa dùng.

> **Ràng buộc bản chất (đọc từ docstring `has_controller_permissions:443-446`): "Controllers can only deny permission, they can not explicitly grant any permission that wasn't already present."** Hook trả `True` **KHÔNG cấp thêm** gì — DocPerm vẫn quyết. ⇒ Senior/Auditor giữ 200 **là nhờ họ CÓ DocPerm read**, không phải nhờ hook. Ai suy diễn "hook True ⇒ pass" sẽ đặt sai kỳ vọng test.

> ⚠️ **Bẫy xanh-giả (BẮT BUỘC ghi vào test):** `frappe/permissions.py:107-109` — `user == "Administrator"` → `return True` **ngay lập tức**, bỏ qua cả 3 trục. Mọi TC của §9 PHẢI chạy dưới `frappe.set_user(<persona thật>)`; chạy bằng Administrator = **vacuous pass** (đúng bài học INV-ROWSCOPE-4/6 §8.9).

### RC-9.3 — 4 op hiện KHÔNG có gate nào ngoài vendor-IDOR

| Op | API tier | Service tier | Gate ROLE (DocPerm read) | Gate ROW (hook) |
|---|---|---|---|---|
| `getPmWorkOrder` | `api/imm08.py:53` — `assert_vendor_can_access` → `handle(svc.get_work_order, name)` | `services/imm08.py:814` `PMWorkOrderRepo.get` | ❌ KHÔNG | ❌ KHÔNG |
| `getRepairWorkOrder` | `api/imm09.py:50` — `_run()`: `assert_vendor_can_access` + `svc.get_work_order` | `services/imm09.py:1168` `RepairRepo.get` | ❌ KHÔNG | ❌ KHÔNG |
| `getCalibration` | `api/imm11.py:90` — `assert_vendor_can_access` → `handle(svc.get_calibration, name)` | `services/imm11.py:1076` `CalibrationRepo.get` | ❌ KHÔNG | ❌ KHÔNG *(DocType không có hook — xem D10)* |
| `getIncident` | `api/imm12.py:283` — guest-401 + `_run()`: `assert_vendor_can_access` + `svc_get` | `services/imm12.py:1405` `get_incident_detail` → `_get_incident` (`:329`) `IncidentRepo.get` | ❌ KHÔNG | ❌ KHÔNG |

`assert_vendor_can_access` (`services/shared/scope.py:182-217`) là **no-op cho mọi user KHÔNG mang role `Vendor Engineer`** (`:192-193`) ⇒ nó **không phải** gate quyền-đọc, chỉ là isolation NCC. Nó cũng **không bao giờ** trả 404 (nonexistent → `:204-205` return sớm) ⇒ giữ nguyên nó **không** tạo existence-oracle.

## 9.2 Quyết định nghiệp vụ (ADR — BA chốt 2026-07-25)

### ADR-IMM00-DETAIL-READ-01 — Read-gate của detail == predicate của list/write (KHÔNG có "chế độ đọc lỏng")

- **Status**: Accepted · **Date**: 2026-07-25 · **Bổ sung cho** D4/D5 (§8.2), **thực thi** B3 (§8.10).
- **Context**: `list` đã row-scoped (D4 `assigned_to`), write-gate đã khoá theo `assigned_to` OR `<domain>.write`; chỉ `detail` còn đọc trần bằng `frappe.get_doc`. Ba đường của **cùng một phiếu** đang trả 3 kết luận khác nhau.
- **Decision**: **D8 — mọi GET-detail của DocType phiếu-công-việc PHẢI kết luận bằng CÙNG predicate `frappe.has_permission(<DocType>, ptype="read", doc=<doc>)`** (ROLE ∧ ROW ∧ User Permission), phát 403 **in-envelope**. KHÔNG được có nhánh "đọc thì nới, ghi mới siết".
- **Alternatives loại bỏ**:
  - *(a) Chỉ gate ROLE (DocPerm), bỏ ROW* — giữ nguyên IDOR: KTV vẫn đọc phiếu đồng nghiệp bằng URL trực tiếp ⇒ **không đóng** triệu chứng §9.0.
  - *(b) Đổi `RepairRepo.get` → `frappe.get_doc(..., ignore_permissions=False)`* — Frappe KHÔNG có tham số đó cho `get_doc`; muốn dùng phải là `doc.check_permission()` (raise `frappe.PermissionError` **kèm msgprint** → rò tên DocType + tên bản ghi vào `_server_messages`).
  - *(c) Gate ở API tier (như `imm00.get_asset`)* — chỉ vá 4 điểm gọi hiện tại; service vẫn là hàm đọc-trần cho mọi call site tương lai (`get_incident_detail` đã có **≥2** call site nội bộ). Gate ở **service** phủ cả đường mobile lẫn web lẫn call-site nội bộ.
  - *(d) Nới DocPerm/role cho persona bị chặn để "khỏi vỡ"* — cấm tuyệt đối (A7 §8.7): sửa triệu chứng bằng cách mở lỗ.
- **Consequences**:
  - ✔ Đóng IDOR-đọc trên 4 màn detail mobile + web; đóng vĩnh viễn trạng thái "đọc được nhưng không đính được ảnh".
  - ✔ 3 đường (`list` ⇔ `detail` ⇔ `attach`) trở thành **bảng chân trị nhất quán** ⇒ kiểm chứng được bằng test (INV-DETAIL-3).
  - ⚠️ Persona **thiếu DocPerm read** (bảng §8.5: `Calibration User`/`Corrective User`/`PM User` trên `Asset Repair`, …) nay nhận **403 envelope** thay vì dữ liệu ở màn detail. **Đây là sửa lỗi, KHÔNG phải regression.** Nếu nghiệp vụ MUỐN họ đọc ⇒ lời giải đúng là **cấp DocPerm read** (backlog B2), KHÔNG phải bỏ gate.
  - ⚠️ Vendor Engineer thiếu DocPerm read trên `Asset Repair`/`PM Work Order` (B2 §8.10) ⇒ trên 4 màn này họ sẽ chạm 403 ROLE **trước** khi chạm isolation NCC. Ghi backlog, **KHÔNG** nới trong vòng này.

### ADR-IMM00-DETAIL-READ-02 — Thứ tự 3 lớp: ROLE → EXISTS → ROW (chống existence-oracle)

- **Status**: Accepted · **Date**: 2026-07-25 · **Tiền lệ**: `api/imm00.py:483-509` `get_asset` (3 lớp, cite ngay trong docstring `:486-497`).
- **Context**: gate ROW cần `doc` ⇒ buộc phải `exists`/load trước. Nếu để `exists` chạy trước gate ROLE thì user **không có quyền** vẫn phân biệt được "phiếu có tồn tại" (404) hay "không tồn tại" (404 khác/403) ⇒ **oracle liệt kê** naming-series.
- **Decision**: **D9 — thứ tự BẮT BUỘC trong thân service**:
  1. **L0 · ROLE** `assert_doctype_read_permission(<DocType>)` — **TRƯỚC** mọi `exists`/`get`;
  2. **L1 · EXISTS** `<X>Repo.get(name)` → không có ⇒ `nthrow(MSG.<module>_NOT_FOUND)` **404** (GIỮ NGUYÊN message/mã hiện tại);
  3. **L2 · ROW** `assert_can_read_doc(<DocType>, doc)` → `frappe.has_permission(..., doc=doc)`.
- **Consequences**: thiếu DocPerm read ⇒ **403 y hệt nhau** cho `name` tồn tại và `name` bịa ⇒ 0 oracle. Có DocPerm read + `name` bịa ⇒ **404 GIỮ NGUYÊN** (không siết oan người có quyền). L2 chạy lại DocPerm là **cố ý** (idempotent, mirror `DatabaseQuery`), KHÔNG phải thừa.

### ADR-IMM00-DETAIL-READ-03 — Áp CẢ 4 op, kể cả DocType chưa có hook row-scope

- **Status**: Accepted · **Date**: 2026-07-25.
- **Context**: `Calibration Record` **KHÔNG** nằm trong `hooks.permission_query_conditions` / `hooks.has_permission` (`hooks.py:440-456`) ⇒ với nó, L2 rút gọn về DocPerm + User Permission.
- **Decision**: **D10 — cả 4 op dùng CÙNG một khuôn 3 lớp**, không miễn trừ IMM-11. Lý do: (a) L0 (ROLE) là bắt buộc độc lập với hook — đây mới là lớp chặn "0 DocPerm read vẫn đọc trọn hồ sơ hiệu chuẩn"; (b) nếu mai này `Calibration Record` được thêm hook, gate **tự động** có hiệu lực, không phải nhớ quay lại sửa.
- **Consequences**: IMM-11 hôm nay chỉ siết ROLE (hành vi ROW **không đổi** ⇒ 0 regress cho KTV hiệu chuẩn có DocPerm read); guard tĩnh vẫn phải đặt tên IMM-11 tường minh vì G5-generic (quét theo `_rowscoped_doctypes()`) **không nhìn thấy** nó — xem §9.8 G5b.

## 9.3 Contract helper (BE thực thi — `assetcore/services/shared/permissions.py`)

Thêm **một** helper, đặt **ngay cạnh** `assert_doctype_read_permission` (cùng file, cùng ngôn ngữ lỗi):

```python
def assert_can_read_doc(doctype: str, doc) -> None:
    """Gate quyền-đọc CẤP BẢN GHI — ROLE ∧ ROW ∧ User Permission trong MỘT predicate.

    Raise frappe.PermissionError (KHÔNG frappe.throw) ⇒ @rowscoped bọc chung một
    `except` với nhánh list, và KHÔNG msgprint tên DocType/tên bản ghi ra
    `_server_messages` (chống rò existence + rò nội bộ).
    """
```

**Ràng buộc cài đặt (BẮT BUỘC):**
- Thân hàm gọi **đúng** `frappe.has_permission(doctype, ptype="read", doc=doc, user=frappe.session.user)`; `False` ⇒ `raise frappe.PermissionError(<message KHÔNG chứa name>)`.
- **KHÔNG** dùng `doc.check_permission("read")` — nó `frappe.throw` (msgprint ⇒ rò `_server_messages`, và biến 403 thành `ValidationError`-shape).
- **KHÔNG** truyền `raise_exception=False/True` như một cách "tắt lỗi": v15 không raise ở đây; kết luận nằm ở giá trị trả về.
- Message hằng ra client vẫn là `MSG.AUTH_FORBIDDEN` (`utils/messages.py:61` — `"AUTH-403"`) do `run_rowscoped` phát (`services/shared/permissions.py:87-114`) ⇒ **KHÔNG** thêm mã lỗi mới.

## 9.4 Khuôn thực thi cho 4 service (BE Bước-4 — dán y khuôn, KHÔNG sáng tạo biến thể)

```python
@rowscoped                                        # PermissionError → ServiceError(FORBIDDEN,403) → HTTP-200 envelope
def get_work_order(name: str) -> dict:
    assert_doctype_read_permission(_DT_PM_WO)     # L0 ROLE — TRƯỚC exists (D9, no existence-oracle)
    wo = PMWorkOrderRepo.get(name)                # L1 EXISTS
    if not wo:
        nthrow(MSG.IMM08_WO_NOT_FOUND, name=name) # 404 GIỮ NGUYÊN (chỉ tới được nếu CÓ DocPerm read)
    assert_can_read_doc(_DT_PM_WO, wo)            # L2 ROW — hook has_permission (hooks.py:448-455)
    ...                                           # phần thân CÒN LẠI GIỮ NGUYÊN 100%
```

| Op | Service | DocType hằng | Ghi chú riêng |
|---|---|---|---|
| `getPmWorkOrder` | `services/imm08.py:814` `get_work_order` | `PM Work Order` | `@rowscoped` — kiểm tra chưa có sẵn trước khi dán (tránh bọc 2 lần) |
| `getRepairWorkOrder` | `services/imm09.py:1168` `get_work_order` | `Asset Repair` | L2 dùng **cùng doc object** đã load (KHÔNG load lần 2 — 0 query thêm) |
| `getCalibration` | `services/imm11.py:1076` `get_calibration` | `Calibration Record` | D10 — L2 hôm nay chỉ là DocPerm+UserPerm (0 hook), vẫn PHẢI có mặt |
| `getIncident` | `services/imm12.py:1405` `get_incident_detail` | `Incident Report` | L0 đặt **trong `get_incident_detail`** (KHÔNG trong helper `_get_incident:329` — helper còn phục vụ đường ghi có gate riêng); guard G5 đọc thân hàm `get_*` |

**Ràng buộc bổ sung:**
- **KHÔNG** đụng API tier của 4 op (A5): `assert_vendor_can_access` giữ **nguyên vị trí, nguyên thứ tự** ⇒ 2 lớp cùng tồn tại (vendor-isolation ở API, read-gate ở service).
- **KHÔNG** đụng `permissions.py` (5 hook + 5 query giữ nguyên byte-for-byte) — D4/D8 nói *dùng* predicate, KHÔNG *đổi* predicate.
- **KHÔNG** đụng `BaseRepository.get` (nó còn phục vụ đường ghi/nội bộ; gate ở đó sẽ siết cả scheduler → dead-gate câm).
- **0 query thêm**: L0 đọc role-permission cache; L2 dùng doc đã load ở L1.

## 9.5 Semantics lỗi — kế thừa §8.5, áp cho detail

| Loại | Nơi phát | HTTP status-line | Body | Client mobile |
|---|---|---|---|---|
| **dispatcher-403** | Frappe dispatcher — guest / no-token, TRƯỚC handler (`frappe/__init__.py:876`) | **403** | `FrappeRawError` | **re-auth / logout** |
| **in-handler cap-403 (CR-74)** | service — user CÒN phiên, thiếu DocPerm read **hoặc** phiếu không thuộc row-scope | **200** | `Error` `{success:false, code:"FORBIDDEN", http_status:403}` | **hiển thị message, KHÔNG logout** |
| in-handler 404 | service — `name` không tồn tại (chỉ tới được sau L0) | **200** | `Error` `{code:"NOT_FOUND", http_status:404}` | hiển thị "không tìm thấy" |
| in-handler 401 (chỉ `getIncident`) | `api/imm12.py:286-287` guest-check | **200** | `Error` `{http_status:401}` | refresh / re-auth |

> **BR-00-DETAIL-403 (chốt):** trên 4 op C6-DETAIL, thiếu quyền đọc ⇒ **HTTP-200 + Error envelope FORBIDDEN**. **KHÔNG** raise thành HTTP-4xx; **KHÔNG** trả `data` rỗng/`null` câm (silent-empty che RBAC misconfig — anti-pattern dead-gate); **KHÔNG** trả 404 thay 403 (che lỗi cấu hình quyền thành "mất dữ liệu").

**Ràng buộc rò rỉ (BẮT BUỘC test):** body 403 **KHÔNG** được chứa BẤT KỲ field nghiệp vụ nào của bản ghi — cụ thể cấm: `asset_ref` · `repair_summary` · `mttr_hours` · `root_cause_category` · `clinical_impact` (và mọi khoá khác của payload success). Chỉ được có khoá của `Error` envelope.

## 9.6 Boundaries (Always / Ask-first / Never)

**Always**
- Mọi GET-detail MỚI trên DocType phiếu-công-việc dán ĐỦ khuôn 3 lớp §9.4 + `@rowscoped`.
- Lỗi quyền = in-handler HTTP-200 + Error envelope (BR-00-DETAIL-403).
- Gate ROLE chạy **trước** `exists`; gate ROW chạy **trên doc đã load** (0 query thêm).
- Test chạy dưới **persona thật** (`frappe.set_user`), KHÔNG Administrator.

**Ask-first (BA/USER chốt trước)**
- Cấp DocPerm read cho persona đang bị 403 (B2 — đổi mặt phân quyền, KHÔNG phải fix code).
- Thêm/đổi hook `has_permission` cho `Calibration Record` (D10 hiện cố ý để trống).
- Mở rộng gate sang `BaseRepository.get` (ảnh hưởng scheduler/domain-logic — xem §9.9 B12).

**Never**
- ❌ Sửa `permissions.py` (`*_query` / `*_has_permission`) để "cho test xanh".
- ❌ Nới DocPerm / thêm role vào doctype JSON để chữa test đỏ.
- ❌ Gỡ / thay `assert_vendor_can_access` ở API tier (A5 — 2 lớp phải cùng tồn tại).
- ❌ Trả `data: null`/`{}` thay cho 403; trả 404 thay cho 403.
- ❌ Dùng `doc.check_permission()` (msgprint ⇒ rò `_server_messages`).
- ❌ Thêm path/opId/param/schema vào OAS; đổi shape payload success.
- ❌ `git commit/push/merge` · `reset DB` · `bench migrate` · reload gunicorn (HARD-STOP — quyền USER).

## 9.7 Bất biến phải đạt (acceptance — BE viết test chứng minh)

| # | Điều kiện | Yêu cầu | Test |
|---|---|---|---|
| INV-DETAIL-1 | Persona **đăng nhập** nhưng **0 DocPerm read** trên DocType đích, gọi **từng** op trong 4 | `success:false`, `code:"FORBIDDEN"`, `http_status:403` **trên HTTP-200**; body **0 field nghiệp vụ** | `test_rowscope_docperm_gate::test_detail_*_denied_without_docperm` (×4) |
| INV-DETAIL-2 | KTV **có** DocPerm read, phiếu `assigned_to != user` (`Asset Repair` / `PM Work Order` / `Incident Report`) | CÙNG envelope FORBIDDEN 403 | `test_rowscope_invariant::test_detail_row_denied_for_non_assignee` (×3) |
| INV-DETAIL-3 | **Bảng chân trị 2 persona × 2 phiếu** (`Asset Repair`) | `list_work_orders` (xuất hiện?) ⇔ `get_repair_work_order` (200/403) ⇔ `attach_repair_checklist_photo` (OK/403) — **4/4 tổ hợp trùng khớp** | `test_rowscope_invariant::test_detail_read_write_truth_table` |
| INV-DETAIL-4 | Senior (`_is_senior` `permissions.py:57-58`) / Auditor / persona non-technician **có** DocPerm read | **200 success**, payload **byte-identical** trước-sau CR-74 ⇒ 0 regress | `test_rowscope_invariant::test_detail_senior_unchanged` |
| INV-DETAIL-5 | Persona **0 DocPerm read** + `name` **KHÔNG tồn tại** | 403 **giống hệt** trường hợp `name` tồn tại (0 existence-oracle) | `test_rowscope_docperm_gate::test_detail_no_existence_oracle` |
| INV-DETAIL-6 | Persona **có** DocPerm read + `name` **KHÔNG tồn tại** | **404 GIỮ NGUYÊN** (mã + message như trước CR-74) | `test_rowscope_docperm_gate::test_detail_404_preserved_for_permitted_user` |
| INV-DETAIL-7 | Vendor Engineer ngoài scope | 403 từ `assert_vendor_can_access` (API tier) — **KHÔNG** 500, **KHÔNG** bị gate mới nuốt | `test_rowscope_docperm_gate::test_detail_vendor_layer_still_present` |
| INV-DETAIL-8 | Guard tĩnh **G5** (§9.8) | mọi `get_*` load doc row-scoped mà thiếu gate ⇒ **ĐỎ**; gỡ 1 gate bất kỳ trong 4 service ⇒ **ĐỎ** (mutation-verified) | `test_rowscope_scope_guard::TestRowScopeStaticGuard::test_detail_reads_are_gated` |
| INV-DETAIL-9 | No-regress | `test_imm08` · `test_imm09` · `test_imm11` · `test_imm12` · `test_rowscope_*` · `test_mobile_oas` · `test_mobile_docset` XANH, 0 skip mới | suite hiện có |

> **INV-DETAIL-3 là test BẮT BUỘC đóng P0** — nó phát biểu trực tiếp "đọc ⇔ ghi ⇔ thấy trong danh sách". **INV-DETAIL-1/2/5 PHẢI chạy dưới session user THẬT** — Administrator short-circuit `frappe/permissions.py:107-109` ⇒ xanh giả.

## 9.8 Guard tĩnh **G5** (`assetcore/tests/guards/test_rowscope_scope_guard.py`)

G1–G4 chỉ nhìn **list/raw-query**; đường **detail** (`<X>Repo.get(` / `frappe.get_doc(`) hoàn toàn **vô hình** với cả 4 — đúng lỗ đã lọt của CR-74. G5 gồm 2 vế:

- **G5a (generic)** — mọi `FunctionDef` tên `get_*` (public) trong `assetcore/services/imm*.py` mà thân hàm gọi `<X>Repo.get(` hoặc `frappe.get_doc(` trên DocType ∈ `_rowscoped_doctypes()` (đọc từ `hooks.permission_query_conditions` — SSoT, KHÔNG chép tay) **PHẢI** có gate tường minh **trong chính thân hàm** (`assert_doctype_read_permission` / `assert_can_read_doc` / `rbac.require` / `rbac.can`). Backlog đã biết đi vào một allowlist **chỉ-giảm** (đối xứng `_RAW_QUERY_UNGATED_BACKLOG` của G4): entry biến mất = tin vui, KHÔNG fail build; **cấm thêm dòng mới để cho xanh**.
- **G5b (named)** — 4 service của C6-DETAIL nêu **đích danh** (kể cả `services/imm11.py::get_calibration` mà G5a không thấy vì `Calibration Record` chưa có hook — D10) PHẢI có **cả hai** `assert_doctype_read_permission` **và** `assert_can_read_doc` trong thân hàm.

**Chứng minh không vacuous (BẮT BUỘC ghi bằng chứng vào báo cáo vòng):** gỡ **1** gate bất kỳ trong 4 service ⇒ G5 **ĐỎ**; hoàn nguyên ⇒ **XANH**.

## 9.9 Backlog mở ra (KHÔNG làm vòng này)

| # | Việc | Ưu tiên |
|---|---|---|
| B3 | ~~Detail-gate IDOR trên `*Repo.get`~~ → **ĐANG ĐÓNG bằng §9 (CR-74)** cho 4 op C6-DETAIL | ✅ (phần còn lại: B10) |
| B10 | **Các GET-detail KHÁC** cùng lớp chưa quét: `imm04` (Asset Commissioning — DocType **có hook**), `imm05`, `imm15`, `imm16` + mọi `get_<x>_detail` web-only. G5a sẽ **liệt kê ra** khi chạy; mỗi dòng cần [BA] ratify | P1 |
| B10-a | **[BA ratify 2026-07-26 — CR-76]** Bề mặt `imm04` **đầu tiên** đóng: `get_gate_status` (thẻ cổng G01–G06) chuyển xuống service `evaluate_gate_status()` + dán **nguyên khuôn §9.4** (ROLE→EXISTS→ROW + `@rowscoped`). Vì tên hàm **không** khớp tiền tố `get_`/`list_` của G5a ⇒ ghim bằng vế **named** `_CR76_NAMED_DETAIL_GATES` (mirror `_CR74_NAMED_DETAIL_GATES`). Cặp `("services/imm04.py","evaluate_gate_status")` **CẤM** xuất hiện trong `_DETAIL_READ_UNGATED_BACKLOG`. Spec: `docs/imm-04/04_Backend_Design.md §5.6` + ADR-IMM-04-07 | ✅ đang thực thi |
| B10-b | Phần **còn lại** của `imm04` trong allowlist chỉ-giảm: `get_form_context` · `get_barcode_lookup` — **giữ nguyên**, vòng riêng (cùng khuôn) | P1 |
| B11 | Cải chính comment sai ở `assetcore/permissions.py:150-153` (*"implicit call inside `frappe.get_doc()`"*) — docstring nói ngược với v15, dễ khiến vòng sau bỏ gate | P2 · doc-only |
| B12 | Có nên đưa gate vào `BaseRepository.get` (thay vì từng service)? Đánh đổi: phủ rộng vs siết luôn scheduler/domain-logic ⇒ cần tham-số-hoá `scope=` như `list` | P2 · cần BA ratify |
| B2 | (kế thừa §8.10) **Vendor Engineer / `Calibration User` / `Corrective User` / `PM User` thiếu DocPerm read** — sau CR-74 họ chạm 403 ở CẢ detail. Cần USER ratify: cấp DocPerm read hay chấp nhận chặn | P1 · cần USER ratify |
| B13 | FE 4 màn detail: render 403 in-envelope thành thông báo "Phiếu chưa được giao cho bạn" + **KHÔNG** logout, **KHÔNG** màn trắng; đồng bộ với gate nút đính-ảnh | P1 · [FE] |

---

*ADR-IMM00-LIST-SCOPE — §1–§7 chốt 2026-06-08 (AC Asset). §8 INV-ROWSCOPE chốt 2026-07-25 (5 DocType row-scoped + `BaseRepository.list(scope)`). §9 INV-ROWSCOPE-DETAIL / CR-74 chốt 2026-07-25 (4 GET-detail C6 — read-gate == write-gate). Gate phân tích; BE thực thi §8.3/§8.4/§8.4b/§8.5 + §9.3/§9.4/§9.5 + FE §8.8 + test §8.9/§9.8 trước khi tuyên bố xong.*

---

# PHẦN IV — §10. `Asset Commissioning`: MỘT ENGINE (AC-CR-98) + vendor-scope là PHÉP GIAO (AC-CR-106) — chốt 2026-07-30

> Vòng 3 / run-5. Hai bất biến ĐÃ KHAI TÊN nhưng CHƯA ENFORCE ở run-3/run-4 nay chuyển sang **enforce**:
> **INV-CONN-27** (`docs/imm-00/05_API_Specification.md §III.24.9`) và **INV-CONN-21** (`§III.24.8`).
> §10 là **SSoT duy nhất** cho cả hai; mọi file khác chỉ trỏ về đây.
> Đọc kèm: §1 (RC-2 count thô > rows scoped) · §4b (count phải cùng predicate) · §8.3 (một engine cho count+rows) — §10 là lần **thứ ba** cùng một class-of-bug, lần này trên đường **raw-query trực tiếp** (không qua `BaseRepository`).

## 10.0 Triệu chứng (2 lỗi độc lập, cùng một hệ quả `ô đếm ≠ nhánh drill`)

| # | Triệu chứng người dùng thấy | Persona |
|---|---|---|
| S-10.1 | Bấm ô «Phiếu nghiệm thu lắp đặt» trên tab «Bản ghi liên quan» của một thiết bị → màn `/commissioning?asset=<mã>` hiện **nhiều dòng hơn** con số vừa bấm; trong đó có phiếu **không thuộc phạm vi** của người đang đăng nhập | Vendor Engineer **kiêm** Commissioning User |
| S-10.2 | Deep-link **một** thiết bị (`?asset=X`) nhưng danh sách trả **mọi** thiết bị được giao (PM / CM / lịch hiệu chuẩn / phiếu hiệu chuẩn) — bộ lọc thiết bị "biến mất" | Vendor Engineer (mọi màn dùng `apply_vendor_scope`) |

## 10.1 Root cause — verify @source 2026-07-30 (BA mở file đọc lại, KHÔNG tin doc cũ)

### RC-10.1 — `list_commissioning` dùng **HAI ENGINE**, cả hai đều bỏ row-scope

`services/imm04.py::list_commissioning` (`:1053`):

- `total = frappe.db.count(_DT, query_filters)` (`:1076`)
- `records = frappe.get_all(_DT, filters=query_filters, …)` (`:1079-1083`)

`Asset Commissioning` **CÓ** `permission_query_conditions` → `assetcore.permissions.asset_commissioning_query` (`hooks.py:444`), và predicate cho **Vendor Engineer** là
`(vendor_engineer_name = '<user>' OR owner = '<user>')` (`permissions.py:143-148`).
`frappe.db.count` và `frappe.get_all` **đều KHÔNG** áp hook đó (chỉ `frappe.get_list` áp) ⇒ endpoint trả **toàn bảng** cho persona bị row-scope. Đây **không chỉ** là lệch số: nó là **RÒ DỮ LIỆU** (đúng chiều §8.1 — count scoped < rows thô đảo thành *cả hai đều thô*).

### RC-10.2 — `apply_vendor_scope` **GÁN** thay vì **GIAO**

`services/shared/scope.py::apply_vendor_scope` (`:150-179`), nhánh dict:

```python
filters[field] = ["in", assigned]      # :174  ← GHI ĐÈ giá trị caller
```

Caller gửi `{"asset_ref": "A1"}` (deep-link 1 thiết bị) → bị thay bằng `["in", [A1, A2, …]]` ⇒ **mất** ràng buộc của caller. 5 call site prod bị ảnh hưởng: `api/imm00.py:413` (`AC Asset`/`name`) · `api/imm08.py:39` (`PM Work Order`/`asset_ref`) · `api/imm09.py:36` (`Asset Repair`/`asset_ref`) · `api/imm11.py:30` (`Calibration Schedule`/`asset`) · `api/imm11.py:83` (`Calibration Record`/`asset`) — map field ở `scope.py:111-118`.
Không phải lỗ an ninh (kết quả vẫn ⊆ phạm vi được giao) nhưng **vỡ** `count == drill` và biến deep-link thành vô nghĩa — cùng class-of-bug «bộ lọc bị NUỐT CÂM» đã đóng ở `services/imm11.py:916-933` run-4.

### RC-10.3 — 3 TIỀN ĐỀ TRONG ACCEPTANCE **SAI SỰ THẬT** (BA self-correction, dev PHẢI đọc trước khi viết test)

| # | Acceptance nói | Đĩa nói (verify 2026-07-30) | Hệ quả cho dev |
|---|---|---|---|
| SC-1 | `res['total']` / `res['records']` | Service trả `{"items": [...], "pagination": {...}}` (`services/imm04.py:1133`); `total` nằm trong `pagination` | Chấm `res["pagination"]["total"] == len(res["items"])`. **CẤM** đổi tên khoá (FE `stores/imm04.ts` + OAS `CommissioningListPage` đọc `items`/`pagination`) |
| SC-2 | «Vendor Engineer gọi `list_commissioning(filters={})`» | **Vendor Engineer THUẦN không có DocPerm read** trên `Asset Commissioning` (`asset_commissioning.json` chỉ 4 role: Super Admin · Commissioning Manager · Commissioning User · Auditor) ⇒ `frappe.has_permission(_DT,"read",throw=True)` (`:1055`) FAIL → `ServiceError(FORBIDDEN)` → **HTTP-200 + Error envelope** | Persona rò dữ liệu THẬT = **`Vendor Engineer` + `Commissioning User`** (dual-role). Test dùng vendor THUẦN sẽ chấm nhầm nhánh 403 và kết luận "không rò" |
| SC-3 | A1: «trong thân `list_commissioning` `grep 'frappe.db.count\|frappe.get_all'` = 0 hit» | Thân hàm còn **5** `frappe.get_all` làm **enrich nhãn** (`:1091` `IMM Device Model` · `:1095` `AC Supplier` · `:1099` `AC Department` · `:1106` `AC Purchase` · `:1116` `AC Asset`). 4 doctype đầu **KHÔNG** row-scoped ⇒ đổi sang `get_list` sẽ **mất nhãn** với persona thiếu DocPerm trên bảng master (hồi quy hiển thị, không phải bảo mật) | Xem D-CR98-3: chỉ **2** DocType row-scoped phải rời raw-query (`Asset Commissioning`, `AC Asset`); 4 lookup nhãn còn lại **GIỮ** `frappe.get_all` |

### RC-10.4 — Doc cũ đã **RATIFY SAI** (lỗi thiết kế gốc — nguồn của cả vòng này)

`docs/imm-04/05_API_Specification.md §20.4` (soạn cho mobile CR-25a) viết:
> *«cả `frappe.db.count` lẫn `frappe.get_all` BỎ QUA 2 hook đó → count & rows cùng bỏ qua ⇒ vẫn khớp nhau … Kiểm-soát-truy-cập của endpoint = blanket `has_permission` upfront, KHÔNG row-scope … Nếu mobile cần row-scope → [ROADMAP]».*

Đó là **hợp thức hoá một lỗ rò**: hai cái sai cùng chiều thì hai con số bằng nhau, nhưng **cả hai đều sai**. §10 **SUPERSEDE** đoạn đó (xem `ADR-IMM00-LIST-SCOPE-05` §10.3). Doc §20.4 còn dẫn **line-cite STALE** (`:887/:910/:857-861/:967/:117-123/:125-130` — thực tế `:1053/:1076/:1079-1083/:1133/:124-130/:132-137`) ⇒ sửa cùng vòng.

## 10.2 Quyết định nghiệp vụ — 3 persona CHUẨN của `Asset Commissioning` (BA chốt, đọc @source `permissions.py:137-149`)

`asset_commissioning_query` **chỉ** trả predicate khác `""` cho **duy nhất** nhánh Vendor. Ma trận đầy đủ:

| Persona (role thật) | `asset_commissioning_query` | DocPerm read | Kết quả mong đợi |
|---|---|---|---|
| **QTV** `AssetCore Super Admin` (hoặc `Commissioning Manager`) | `""` — senior read-all (`_SENIOR_ROLES`) | ✅ | thấy mọi phiếu; `count == rows` |
| **Nội bộ** `Commissioning User` | `""` — rơi vào `return ""` cuối hàm (`:149`) | ✅ | thấy mọi phiếu; `count == rows` |
| **KTV NCC** `Vendor Engineer` + `Commissioning User` | `(vendor_engineer_name = user OR owner = user)` (`:145-148`) | ✅ (qua Commissioning User) | **chỉ** phiếu mình tạo/được ghi tên; `count == rows` |
| `Vendor Engineer` **THUẦN** | (không tới được) | ❌ | **HTTP-200 + Error envelope** `FORBIDDEN` (in-handler cap-403, §8.5 loại 2) |
| `AssetCore Auditor` | `""` — read-all | ✅ read-only | thấy mọi phiếu |

> ⚠️ **KHÔNG mở rộng phạm vi ai-thấy-gì trong vòng này.** §10 chỉ bắt buộc "engine đọc == engine đếm"; predicate của `asset_commissioning_query` **GIỮ NGUYÊN từng ký tự**.

**Nợ CÓ TÊN `AC-CR-108` (KHÔNG land vòng này):** `vendor_engineer_name` là **`Data` — «Tên Kỹ sư Hãng»**, KHÔNG phải `Link → User` (verify `asset_commissioning.json`). So sánh nó với `frappe.session.user` (email) **gần như không bao giờ khớp** ⇒ nhánh vendor thực chất là `owner = user`. Test của vòng này **CẤM** phụ thuộc vào việc `vendor_engineer_name` khớp email (sẽ xanh giả trên fixture, đỏ trên dữ liệu thật). Lựa chọn cho vòng sau: (a) thêm `Link → User` riêng và sửa predicate, hoặc (b) gỡ mệnh đề chết → predicate `owner`-only tường minh. Cần USER ratify vì đổi = đổi ai-thấy-gì.

## 10.3 ADR

### ADR-IMM00-LIST-SCOPE-04 — Vendor-scope là **PHÉP GIAO**, và `apply_vendor_scope` giữ **dict-in → dict-out** (AC-CR-106)

- **Status**: Accepted · **Date**: 2026-07-30
- **Context**: RC-10.2. Hàm dùng chung 5 call site; 3 trong số đó **mutate `f[...]` NGAY SAU** lời gọi (`api/imm08.py:41`, `api/imm09.py:38`, `api/imm11.py:85` gán `assigned_to`/`technician`) ⇒ đổi kiểu trả về dict→list sẽ `TypeError` runtime.
- **Decision**:
  1. **GIAO, không GÁN**: giá trị caller trên chính field scope được **giao** với `assigned`.
  2. **Shape ĐẦU RA luôn `["in", <list>]`** — bất biến, để `services/imm11.py::_extract_asset_in_scope` (`:916`) và `services/imm00.py::compose_reserved_into` (`:2553`) tiếp tục nhận đúng shape đã hỗ trợ; **0 dòng** phải đổi ở 2 nơi đó.
  3. **Giao rỗng ⇒ `["in", ["__none__"]]`**, KHÔNG `["in", []]` (Frappe `IN ()` là bẫy match-all/SQL-error — cùng lý do `services/imm11.py::_scoped_asset_list` dùng `[""]`).
  4. **Kiểu trả về BẤT BIẾN theo kiểu vào**: dict→dict, list→list. Tuyệt đối KHÔNG "nâng cấp" dict lên filter-list form.
- **Alternatives**: (a) đổi dict→filter-list rồi AND 2 điều kiện cùng field — **loại**: vỡ 3 call site mutate ngay sau (SC/RC-10.2). (b) Giữ GÁN + bắt mọi caller tự giao trước khi gọi — **loại**: 5 nơi lặp lại logic bảo mật = 5 chỗ để quên. (c) `raise ServiceError(INVALID_PARAMS)` khi op không giao được — **loại vòng này**: 5 call site **không** bọc `try/except` quanh `apply_vendor_scope` ⇒ raise sẽ thành lỗi ngoài envelope, vi phạm DONE-gate «lỗi nghiệp vụ = HTTP-200 + Error envelope». Ghi nợ `AC-CR-107`.
- **Consequences**: deep-link 1 thiết bị hoạt động cho cả vendor; caller ngoài phạm vi ⇒ **0 dòng** (KHÔNG phải "toàn bộ thiết bị của tôi"); op không-giao-được ⇒ fail-**closed** + log cảnh báo (xem §10.4 bảng đại số).

### ADR-IMM00-LIST-SCOPE-05 — `list_commissioning` đếm & đọc bằng **MỘT ENGINE** `frappe.get_list`; SUPERSEDE ratify «no row-scope» (AC-CR-98)

- **Status**: Accepted — **supersedes** đoạn INVARIANT của `docs/imm-04/05_API_Specification.md §20.4` (mobile CR-25a) · **Date**: 2026-07-30
- **Context**: RC-10.1 + RC-10.4. `Asset Commissioning` là DocType **có** hook row-scope; endpoint đang đi cửa sau.
- **Decision**:
  1. `total` **và** `records` đều qua `frappe.get_list` — tái dùng SSoT `services/shared/filters.py::count_with_or` (`:236`) HOẶC recipe `fields=["count(name) as _c"]` ghi trong docstring của nó. **CẤM** `count_ignore_permissions` (mirror RAW — dùng ở đây là tái sinh chính lỗ này).
  2. **CẤM** thay `frappe.has_permission(_DT,"read",throw=True)` (`:1055`) bằng gì khác: nó là lớp ROLE (`§9`-style ROLE→ROW). Lớp ROW do `get_list` + hook lo. Hai lớp **cùng tồn tại**.
  3. `count_with_or` nới **annotation** `filters: dict | list | None` (nhánh `overdue=1` truyền **filter-list form** — `services/imm04.py:1067-1072`). Chỉ annotation + docstring; **0 dòng logic** (thân hàm đã truyền thẳng cho `frappe.get_list`, vốn nhận cả 2 dạng).
  4. Nhãn hiển thị (`master_item_name`/`vendor_name`/`clinical_dept_name`/`po_ref_name`) **GIỮ** `frappe.get_all` — 4 DocType đó KHÔNG row-scoped, chuyển sang `get_list` = mất nhãn (RC-10.3 SC-3). **`AC Asset` thì PHẢI đổi** sang `get_list` (`:1116`) vì nó CÓ hook (`hooks.py:440`) — hệ quả có chủ ý: với Vendor Engineer, thiết bị ngoài phạm vi hiện **mã** thay vì tên (`asset_map` đã có fallback `r.get("final_asset")` `:1131`), KHÔNG hiện tên thiết bị ngoài phạm vi.
- **Alternatives**: (a) Thêm `rbac.require` rồi giữ raw-query (đủ để G4 xanh) — **loại**: gate ROLE không thay ROW được, rò vẫn nguyên. (b) Đếm bằng `frappe.db.count` + lọc rows bằng Python sau khi đọc — **loại**: `total` vẫn thô, và phân trang sai. (c) Bỏ `docstatus != 2` để khớp ô đếm — **loại**: đổi nghiệp vụ (phiếu huỷ không thuộc danh sách làm việc); chênh đã có công thức ở INV-CONN-26.
- **Consequences**: `Asset Commissioning` rời `_RAW_QUERY_UNGATED_BACKLOG` (17 → 16); ô «Phiếu nghiệm thu lắp đặt» khớp drill cho **mọi** persona (dung sai duy nhất = `docstatus==2`, nợ `AC-CR-99`); chi phí đếm chuyển sang `get_list(limit_page_length=0)` — đã đo 4 ms/1000 dòng (`filters.py` docstring), bảng `Asset Commissioning` nhỏ ⇒ chấp nhận (measure-first).

## 10.4 Contract `apply_vendor_scope` — ĐẠI SỐ PHÉP GIAO (BE dán y bảng, KHÔNG sáng tạo biến thể)

Đầu vào: `caller` = giá trị caller đặt trên **chính** field scope (`scope.py:111-118`); `assigned` = `_resolve_vendor_assigned_assets(user) or ["__none__"]` (`:171`, resolver định nghĩa `:121` — **giữ nguyên cả hai**).
Đầu ra: **luôn** `["in", <list>]`. Rỗng ⇒ `["in", ["__none__"]]`. Dedup giữ **thứ tự xuất hiện đầu tiên**.

| # | Shape caller | Ví dụ (`assigned = [A1, A2]`) | Kết quả | Thứ tự | Ghi chú |
|---|---|---|---|---|---|
| 1 | **absent** | `{}` | `["in", ["A1","A2"]]` | theo `assigned` | **y hệt hôm nay** ⇒ 0 hồi quy |
| 2 | vô hướng | `"A1"` | `["in", ["A1"]]` | theo caller | shape deep-link phổ biến nhất |
| 2b | vô hướng ngoài phạm vi | `"A9"` | `["in", ["__none__"]]` | — | **0 dòng**, KHÔNG "mọi thiết bị của tôi" |
| 3 | `["=", v]` | `["=", "A1"]` | `["in", ["A1"]]` | theo caller | |
| 4 | `["in", [...]]` | `["in", ["A1","A9"]]` | `["in", ["A1"]]` | theo caller | |
| 5 | list literal (không phải cặp op) | `["A1","A9"]` | `["in", ["A1"]]` | theo caller | mirror nhánh 3 của `_extract_asset_in_scope` |
| 6 | `["!=", v]` | `["!=", "A1"]` | `["in", ["A2"]]` | theo `assigned` | **trừ** khỏi `assigned` — kết quả CHÍNH XÁC, không cần AND |
| 7 | `["not in", [...]]` | `["not in", ["A1"]]` | `["in", ["A2"]]` | theo `assigned` | như #6 |
| 8 | op KHÔNG tính được: `like`·`not like`·`>`·`<`·`>=`·`<=`·`between`·`is`·`descendants of`… | `["like", "%A%"]` | **`["in", ["__none__"]]`** + `frappe.logger("assetcore.scope").warning(...)` | — | **fail-CLOSED** (không bao giờ rò). 0 call site hiện dùng op này trên cột ID/Link. Nợ `AC-CR-107` = nâng lên 400-in-envelope tường minh |

**Nhánh `filters` là list** (`scope.py:176-177`): **GIỮ** `list(filters) + [[<doctype>, field, "in", assigned]]` — hai điều kiện cùng field ANDed trong SQL **chính là** phép giao, KHÔNG phải "điều kiện xung đột" (A7 hiểu sai chỗ này; xem tiền lệ `services/imm00.py::compose_reserved_into` docstring `:2553+` đã verify `name in assigned` AND `name not in reserved`).
⚠️ **1 sửa BẮT BUỘC ở nhánh này**: nhãn doctype spliced vào điều kiện phải là **tên DocType THẬT**. `"Calibration Schedule"`/`"Calibration Record"` là **alias API**, DocType thật là `IMM Calibration Schedule`/`IMM Asset Calibration` ⇒ thêm map alias→thật và dùng nó **chỉ** cho nhãn điều kiện của nhánh list (nhánh dict không cần). Nếu BE muốn tối giản: được phép hoãn thành `AC-CR-109` **với điều kiện** thêm 1 test `skipIf`-free chứng minh nhánh list **hiện chưa** tới được từ 5 call site (cả 5 truyền dict sau `parse_json`).

## 10.5 Contract `list_commissioning` (BE thực thi — `services/imm04.py:1053`)

| Thứ tự | Bước | Ràng buộc |
|---|---|---|
| 1 | ROLE gate | `frappe.has_permission(_DT, ptype="read", throw=True)` → `except frappe.PermissionError: raise ServiceError(FORBIDDEN, "Không có quyền truy cập")` — **GIỮ NGUYÊN** (`:1055-1057`) |
| 2 | whitelist khoá | `safe_filters` từ `_ALLOWED_FILTER_KEYS` (`:1059`, hằng `:132-137`) — **GIỮ NGUYÊN** (khoá lạ bị **bỏ**, KHÔNG throw; hợp đồng OAS `CommissioningFilters` dựa vào) |
| 3 | mặc định `docstatus != 2` | `:1060-1061` — **GIỮ NGUYÊN** (nguồn của công thức dung sai INV-CONN-26) |
| 4 | virtual `overdue=1` | `:1067-1072` → `query_filters` thành **filter-list form** — **GIỮ NGUYÊN** |
| 5 | **ĐẾM** | `total = count_with_or(_DT, query_filters, None)` — **MỘT** engine `frappe.get_list` |
| 6 | phân trang | `pg = paginate(total, page, page_size)`; `limit_page_length=pg["page_size"]` (SSoT clamp) — **GIỮ NGUYÊN** |
| 7 | **ĐỌC** | `records = frappe.get_list(_DT, filters=query_filters, fields=_LIST_FIELDS, order_by=_ORDER_MODIFIED, limit_start=pg["offset"], limit_page_length=pg["page_size"])` |
| 8 | enrich nhãn | 4 lookup **GIỮ** `frappe.get_all`; **`AC Asset` (`:1116`) đổi sang `frappe.get_list`** |
| 9 | trả về | `{"items": records, "pagination": pg}` — **CẤM đổi khoá** (FE + OAS đọc) |

**Bất biến shape:** không thêm/bớt/đổi tên khoá nào của `pagination` (`page`·`page_size`·`total`·`total_pages`·`offset` — `utils/pagination.py:37`) và của item (20 property, OAS `CommissioningListItem`).

**`order_by` tiebreaker:** `_ORDER_MODIFIED = "modified desc"` (`:139`) **thiếu tiebreaker** ⇒ cùng class-of-bug đã chốt run-4 cho ALE (trang liền kề lặp/bỏ sót khi `modified` trùng). **KHÔNG land vòng này** (ngoài đề mục, đụng thứ tự hiển thị) — ghi nợ `AC-CR-110`: `"modified desc, name desc"` cho **mọi** list phân trang của IMM-04.

## 10.6 Semantics lỗi — kế thừa §8.5, áp cho `list_commissioning`

| Ca | Kênh | Body |
|---|---|---|
| Guest / không token | **dispatcher-403** (trước handler) | Frappe trả 403 → client **re-auth**; KHÔNG có Error envelope |
| Thiếu quyền đọc (vendor thuần) | **in-handler cap-403** | **HTTP-200** + `{"success": false, "error": {...FORBIDDEN...}}` |
| Khoá filter lạ | không lỗi | bị **bỏ** khỏi predicate (hợp đồng hiện hành) |
| Giao rỗng do scope | không lỗi | `{"items": [], "pagination": {"total": 0, …}}` — **0 dòng, KHÔNG 403** |

**CẤM** `raise` → HTTP-4xx cho bất kỳ ca nghiệp vụ nào ở trên (DONE-gate spec-contract).

## 10.7 Boundaries (Always / Ask-first / Never)

- **Always**: đếm và đọc **cùng một engine**, **cùng một biến** `query_filters` · shape ra của `apply_vendor_scope` luôn `["in", list]` · giao rỗng ⇒ sentinel `__none__` · fail-**closed** khi không tính được · mỗi thay đổi có test ĐỎ-TRƯỚC · `.py` prod đổi ⇒ bồi vào danh sách chờ `bench restart` (blocker #1 STATE).
- **Ask-first**: đổi predicate `asset_commissioning_query` (ai-thấy-gì) · cấp DocPerm read `Asset Commissioning` cho `Vendor Engineer` thuần (§8.10 B2) · gỡ mệnh đề `vendor_engineer_name` (`AC-CR-108`) · đổi `_ORDER_MODIFIED` (`AC-CR-110`).
- **Never**: ❌ `count_ignore_permissions` / `frappe.db.count` / `frappe.get_all` trên `Asset Commissioning` hoặc `AC Asset` trong đường list · ❌ đổi kiểu trả về `apply_vendor_scope` (dict→list) · ❌ đổi tên khoá `items`/`pagination` · ❌ dùng `frappe.db.get_value(s)` để **né** guard G4 (đó là gaming detector, không phải fix) · ❌ thêm dòng mới vào `_RAW_QUERY_UNGATED_BACKLOG` · ❌ `git commit`/`bench migrate`/`bench restart`/xoá dữ liệu prod.

## 10.8 Bất biến phải đạt (acceptance — dev viết test chứng minh, KHÔNG "xanh suông")

| ID | Bất biến | Chấm bằng |
|---|---|---|
| **INV-COMM-SCOPE-1** | MỘT ENGINE: trong thân `list_commissioning`, **0** hit `frappe.db.count` / `frappe.get_all` trên **DocType row-scoped** (`Asset Commissioning`, `AC Asset`); 4 lookup nhãn không-row-scoped được phép | AST (chính hàm `_raw_rowscoped_hits` của guard) |
| **INV-COMM-SCOPE-2** | HẾT RÒ: persona `Vendor Engineer + Commissioning User`, `list_commissioning({})` ⇒ phiếu **không** thuộc `(vendor_engineer_name=user OR owner=user)` **vắng** ở CẢ `items` LẪN `pagination.total` | fixture 2 phiếu (1 của persona, 1 của người khác) + `frappe.set_user` |
| **INV-COMM-SCOPE-3** | `count == rows`: 3 persona §10.2, `pagination.total == len(items)` khi tổng ≤ `page_size`; khi > `page_size` thì `total` == số dòng đếm được qua **cùng** predicate (KHÔNG phải tổng toàn bảng) | 2 nhánh: ≤ và > `page_size` |
| **INV-COMM-SCOPE-4** | Allowlist **CHỈ-GIẢM**: `("services/imm04.py","list_commissioning")` **không còn** trong `_RAW_QUERY_UNGATED_BACKLOG`; `len(...) <= 16` | guard tĩnh |
| **INV-VENDORSCOPE-1** | GIAO không GÁN: đủ 8 dòng bảng §10.4, **cho cả 5 doctype** trong `_VENDOR_SCOPE_FIELD_MAP` | unit (monkeypatch resolver) |
| **INV-VENDORSCOPE-2** | dict-in→dict-out; shape ra luôn `["in", list]`; `_extract_asset_in_scope` nhận được kết quả **không cần sửa** | unit + gọi thẳng `_extract_asset_in_scope(out[field])` |
| **INV-VENDORSCOPE-3** | non-vendor / guest / doctype ngoài map / bypass-role ⇒ **passthrough byte-identical** (0 hồi quy — `test_rbac.py:570-586` phải xanh **không sửa**) | chạy lại `test_rbac` |
| **INV-VENDORSCOPE-4** | `overdue=1` (filter-list form) vẫn chạy qua đường đếm mới; `list_commissioning({"overdue":1})` và `{"overdue":1,"workflow_state":X}` giữ nguyên hành vi | `test_imm04.py:779-877` phải xanh **không sửa** |
| **INV-CONN-27 (enforce)** | Với **cùng 1 thiết bị + cùng 1 session**, cho **3 persona** §10.2: `cell.total == len(drill.items) + #{docstatus==2}` ∧ `cell.total_capped == 0` ∧ mọi dòng drill có `final_asset == X` | cross-endpoint `get_connections` ⇄ `list_commissioning({"final_asset":X})` |
| **INV-CONN-21 (enforce)** | Vendor Engineer + deep-link 1 thiết bị: `list_calibration_schedules(filters='{"asset":X}')` / `list_pm_work_orders('{"asset_ref":X}')` / `list_repair_work_orders('{"asset_ref":X}')` trả **chỉ** dòng của X (⊆ phạm vi), KHÔNG mọi thiết bị được giao | 1 TC/endpoint |

**Ràng buộc chấm (bắt buộc):**
- Chạy dưới **session user THẬT** (`frappe.set_user`) — `Administrator` bypass `permission_query_conditions` ⇒ **XANH GIẢ** (bài học §8.9 đã ghi).
- **CẤM** mock `frappe.get_list`: mock chứng minh chữ ký, không chứng minh predicate.
- **CẤM** assert vacuous: `assertIn(<doctype>, cells)` **trước** khi so số; công thức dung sai phải **không vacuous** (seed cả `docstatus` 0 và 1; nếu seed được `docstatus=2` thì chênh phải khác 0 ít nhất 1 TC).
- Fixture master tên **cố định là bẫy** (§run-4): dùng uuid-suffix, `tearDownClass` dọn sạch.
- `QueryDeadlockError` do đa-phiên = **ĐỎ GIẢ** ⇒ chờ quiescence, chạy lại; KHÔNG "sửa cho xanh".

## 10.9 Nơi đặt test (dev KHÔNG tự chọn — tránh đụng shared-file phiên song song)

| Bất biến | File | Ghi chú |
|---|---|---|
| INV-COMM-SCOPE-2/3 · INV-CONN-27 · INV-CONN-21 | **append class mới** vào `assetcore/tests/integration/test_rowscope_invariant.py` | đã có `_ensure_user` + kỷ luật `frappe.set_user` + là nhà của họ INV-ROWSCOPE. **Read-fresh rồi append** (file dirty ở phiên khác) |
| INV-VENDORSCOPE-1..4 (đại số + 5 doctype) | **FILE MỚI** `assetcore/tests/integration/test_vendor_scope_intersect.py` | thuần unit; **CẤM** append vào `test_rbac.py` (shared, đang dirty) |
| INV-COMM-SCOPE-1/4 | delta trong `assetcore/tests/guards/test_rowscope_scope_guard.py` | xoá 1 dòng backlog + thêm assert `len(...) <= 16` |
| A9 (FE) | **FILE MỚI** `frontend/src/views/commissioning/tests/CommissioningListView.scopedEmpty.test.ts` | xem `docs/imm-04/06_Frontend_Design.md §11` |

**DoD run list** (`timeout` tool ≥ 600000 ms, chấm theo **DELTA** đo từ đĩa — baseline trong prompt/STATE **luôn có thể stale**):
`test_rowscope_scope_guard` · `test_rowscope_invariant` · `test_vendor_scope_intersect` (mới) · `test_imm04` · `test_rbac` · `test_connections_tree` · `test_connections_list_filter_parity` · `test_imm08` · `test_imm09` · `test_imm11` · `test_imm00`.
**KHÔNG curl** (blocked-reload gunicorn `--preload`, LL-DEPLOY-07/08).

## 10.10 Backlog mở ra (KHÔNG làm vòng này)

| # | Việc | Ưu tiên |
|---|---|---|
| `AC-CR-99` | Ô đếm `get_connections` chưa loại `docstatus==2` ⇒ chênh với drill. Hiện chỉ **khai bằng công thức** (INV-CONN-26 / §10.8). Sửa = thêm `docstatus: ["!=", 2]` vào filters của ô — nhưng đổi **mọi** ô có DocType submittable ⇒ cần BA ratify từng ô | P1 |
| `AC-CR-107` | Op không-giao-được hiện **fail-closed câm** (chỉ log). Nâng thành **400 in-envelope** tường minh ⇒ phải bọc `try/except` ở **cả 5** call site + OAS ghi nhánh lỗi | P1 |
| `AC-CR-108` | `vendor_engineer_name` là `Data`, không phải `Link → User` ⇒ nhánh vendor thực chất `owner`-only (§10.2) | P1 · cần USER ratify |
| `AC-CR-109` | Alias `Calibration Schedule`/`Calibration Record` trong `_VENDOR_SCOPE_FIELD_MAP` không phải DocType thật ⇒ nhánh list-form + `assert_vendor_can_access` (`scope.py:214-217`) rủi ro (blocker STATE #7) | P1 |
| `AC-CR-110` | `_ORDER_MODIFIED = "modified desc"` thiếu tiebreaker `name desc` ⇒ phân trang lặp/bỏ sót khi `modified` trùng (mọi list IMM-04) | P1 |
| — | `assert_vendor_can_access` raise `http_status` 400 trong khi OAS khai 403 (blocker STATE #6) | P1 · cần ratify |
| — | 16 dòng còn lại của `_RAW_QUERY_UNGATED_BACKLOG` — mỗi dòng cần BA ratify **row-scope thật hay role-gate** trước khi sửa | P1 |
| — | `docs/imm-00/07_Testing_QA.md §XVIII.10.1` prescribe `assetcore/tests/test_connections_list_promotion.py` — **file KHÔNG tồn tại trên đĩa** (verify 2026-07-30) ⇒ TC-CONN-P-01..08 vẫn là **nợ**; TC-CONN-P-04/05/08 được §10.9 hấp thu, còn P-01/02/03/06/07 vẫn mở | P1 · doc↔đĩa drift |

---

*§10 chốt 2026-07-30 (AC-CR-98 + AC-CR-106). Enforce INV-CONN-27 / INV-CONN-21 (trước đó chỉ «khai»). SUPERSEDE đoạn INVARIANT của `docs/imm-04/05_API_Specification.md §20.4`. Gate phân tích; BE thực thi §10.4/§10.5 + FE `docs/imm-04/06 §11` + test §10.8/§10.9 trước khi tuyên bố xong.*

---

# PHẦN V — §11. Đóng nợ VERIFY của §10: nhánh `overdue=1` (list-form) + 4 file test **chưa từng chạy** (AC-CR-112) — chốt 2026-07-30

> **Quan hệ với §10:** §11 **KHÔNG** đổi một dòng quyết định nào của §10 (mã prod của AC-CR-98/AC-CR-106 đã có trên đĩa). §11 đóng **lỗ chứng minh**: bất biến §10.8 hiện dựa một phần vào test **chưa bao giờ chạy** và một phần vào test chạy dưới `Administrator` (bypass row-scope). Đề mục vòng này = **CHẠY THẬT + bịt nhánh chưa phủ**, không phải thiết kế lại.

## 11.1 Bằng chứng đo TỪ ĐĨA 2026-07-30 (không tin số trong STATE/handoff)

| Artefact | Số đo trên đĩa | Trạng thái git | Hệ quả |
|---|---|---|---|
| `assetcore/tests/integration/test_vendor_scope_intersect.py` | **18** `def test_` · 293 dòng | **untracked** | INV-VENDORSCOPE-1/2 **chưa** có bằng chứng chạy |
| `assetcore/tests/guards/test_rowscope_scope_guard.py` | **11** · 584 dòng | **untracked** | INV-COMM-SCOPE-1/4 〃 |
| `assetcore/tests/integration/test_rowscope_invariant.py` | **28** · 1161 dòng | **untracked** | INV-COMM-SCOPE-2/3 · INV-CONN-21/27 〃 |
| `assetcore/tests/integration/test_rowscope_docperm_gate.py` | **22** · 904 dòng | **untracked** | §10.6 (2 loại 403) 〃 |
| `assetcore/tests/imm04/test_imm04.py` | **110** | tracked | baseline hồi quy |
| `frontend/src/views/commissioning/tests/CommissioningListView.scopedEmpty.test.ts` | **8** `it()` | untracked | 8/8 PASS 14:59 hôm nay (đã chạy thật) |
| Tổng file test FE | **287** `*.test.ts` (KHÔNG phải 284) | — | prompt/STATE stale ⇒ **chấm theo delta** |

**Lỗ chứng minh CHÍNH (đo tại chỗ):** nhánh tham số ảo `overdue=1` **đổi SHAPE** của predicate từ `dict` → **list-form** (`services/imm04.py:1100-1105` `_dict_to_list_filters` + append 3 điều kiện SoT), rồi mới vào **cùng** đường đếm/đọc (`:1113 count_with_or` → `:1116 frappe.get_list`). Toàn bộ TC hiện có cho nhánh này (`test_imm04.py:724 TestOverdueSlaLiveInvariant`, gọi `:786` và `:861`) là `unittest.TestCase` chạy dưới **`Administrator`** ⇒ `asset_commissioning_query` trả `""` (permissions.py:140) ⇒ **mọi engine đếm đều cho cùng số** ⇒ TC đó **không thể** ĐỎ khi row-scope bị bỏ. Nghĩa là: bất biến `count == rows` hiện chỉ được chứng minh cho **shape dict**, còn shape **list-form** đi qua đúng cái hàm vừa được đổi (`count_with_or` nhận `dict | list | None`) thì **0 TC** phủ dưới persona row-scoped.

### ADR-IMM00-LIST-SCOPE-06 — «Test **chưa chạy** = **chưa có** bất biến» (evidence-before-claim)

- **Status**: Accepted · **Date**: 2026-07-30
- **Context**: §10.8 liệt kê 10 bất biến kèm "chấm bằng"; run-5 tạo 4 file test (79 TC) nhưng **không** chạy module nào, và handoff ghi các bất biến là đã enforce. Một file test tồn tại trên đĩa chỉ chứng minh **ý định**, không chứng minh **hệ thống**.
- **Decision**: một bất biến chỉ được ghi «enforce» khi có **(a)** dòng `Ran N tests … OK` dán **nguyên văn** của module chứa nó, chạy **module-isolated** (`bench --site miyano run-tests --module assetcore.tests.<mod>`, `timeout` ≥ 600000 ms), **và (b)** ít nhất 1 **mutation** ở mã prod làm TC đó ĐỎ (ghi lại output ĐỎ). Thiếu (a) hoặc (b) ⇒ trạng thái là **`CHƯA CHỨNG MINH`**, không phải «enforce».
- **Alternatives**: (a) tin file test là đủ — **loại**: chính lỗ này sinh ra AC-CR-112. (b) chạy full-suite thay module-isolated — **loại**: đa-phiên gây `QueryDeadlockError` + nhiễm fixture ⇒ ĐỎ GIẢ lấn át tín hiệu (LL-TEST-30). (c) chấm bằng `curl` — **loại**: gunicorn `--preload` ⇒ HTTP không phản ánh đĩa (LL-DEPLOY-07/08).
- **Consequences**: mỗi CR kiểu-verify phải mang theo **bảng baseline đo từ đĩa** + **nghi thức mutation** (§11.5). Đổi lại: chi phí 1 vòng cho mỗi cụm bất biến chưa chạy.

### ADR-IMM00-LIST-SCOPE-07 — Bất biến `count == rows` áp cho **MỌI SHAPE** của `filters`; tham số ảo KHÔNG phải lối thoát

- **Status**: Accepted (mở rộng ADR-…-05, **không** thay thế) · **Date**: 2026-07-30
- **Context**: `list_commissioning` có **2 shape** predicate: `dict` (mặc định) và **list-form** (khi `overdue=1`). Cùng một hàm đếm nhận cả hai (`count_with_or(doctype, filters: dict | list | None, or_filters)` — `services/shared/filters.py:236-288`), nhưng bất biến chỉ được chứng minh ở shape thứ nhất. Bất kỳ tham số ảo tương lai (vd `mine`, `due_soon`) sẽ đi lại đúng đường này.
- **Decision**: `pagination.total == len(items)` (khi tổng ≤ `page_size`) và `total ==` số dòng **row-scoped** đếm qua **cùng** predicate (khi tổng > `page_size`) là bất biến của **hàm**, không của **một shape**. Mọi tham số ảo mở nhánh shape mới ⇒ **bắt buộc** kèm TC dưới **persona row-scoped** cho nhánh đó. Ghi thành **INV-COMM-SCOPE-5/6** (§11.3).
- **Alternatives**: (a) giữ nguyên, tin rằng `get_list` "đằng nào cũng" áp hook cho cả 2 shape — **loại**: đó là suy luận, và chính suy luận cùng dạng ("hai cái sai cùng chiều thì số vẫn khớp") đã hợp thức hoá lỗ rò ở §20.4 cũ. (b) cấm tham số ảo, buộc FE gửi predicate thật — **loại**: rò SSoT overdue ra client (BR-04-10 đặt SoT ở BE).
- **Consequences**: +2 TC BE cho nhánh `overdue`; mỗi tham số ảo mới tốn thêm 1 TC. `TestOverdueSlaLiveInvariant` bị **hạ cấp** thành smoke (§11.3).

## 11.2 Self-correction — hạ cấp một acceptance đã ghi quá tay (BA sửa doc TRƯỚC khi dev code)

| Ghi ở đâu | Bản cũ (SAI về mức chứng minh) | Bản chốt §11 |
|---|---|---|
| §10.8 **INV-VENDORSCOPE-4** | «`overdue=1` (filter-list form) vẫn chạy qua đường đếm mới … `test_imm04.py:779-877` phải xanh **không sửa**» — trình bày như **bất biến scope** | **HẠ CẤP → `SMOKE-VENDORSCOPE-4`**: chỉ chứng minh **không `TypeError`/không hồi quy tập dòng** dưới persona **read-all**. **KHÔNG** chứng minh `count == rows` dưới row-scope (chạy bằng `Administrator`, `permissions.py:140` trả `""`). Bất biến thật = **INV-COMM-SCOPE-5** |
| `docs/imm-04/07 §VIII.1` **TC-IMM04-SCOPE-09** | «chạy lại, **không sửa** ⇒ đường filter-list form đi qua engine đếm mới không hồi quy» | Giữ nguyên **là smoke** (vẫn phải XANH), thêm ghi chú «**không** phải bằng chứng row-scope» + thêm **TC-IMM04-OVD-01/02** (`docs/imm-04/07 §IX.2`) |

**Vì sao đây là lỗi thiết kế gốc chứ không phải lỗi dev:** doc đã *chọn* một TC chạy dưới `Administrator` làm bằng chứng cho một bất biến chỉ quan sát được dưới persona bị row-scope. Dev làm đúng doc thì vẫn để lọt. Sửa doc trước = đúng thứ tự (spec-before-code gate).

## 11.3 Bất biến MỚI (chỉ 2 — không nới đề mục)

| ID | Bất biến | Chấm bằng (phát biểu chấm được) |
|---|---|---|
| **INV-COMM-SCOPE-5** | **Nhánh `overdue=1` (list-form) giữ `count == rows` dưới persona row-scoped.** `frappe.set_user(<Vendor Engineer + Commissioning User>)`; `list_commissioning({"overdue": 1, "final_asset": X})` ⇒ `pagination.total == len(items)` **và** mọi dòng thuộc phạm vi persona (`owner == user`); lặp lại với `page_size=1` ⇒ `total` vẫn là số dòng **row-scoped** (KHÔNG phải tổng toàn bảng) | TC-IMM04-OVD-01 (`docs/imm-04/07 §IX.2`) — **phải ĐỎ** với mutation M1/M2 (§11.5) |
| **INV-COMM-SCOPE-6** | **Không vacuous + không clobber dưới row-scope.** Trong CÙNG fixture: ≥1 phiếu **quá hạn của người khác** (⇒ `frappe.db.count` sẽ đếm thừa ⇒ mutation ĐỎ có thật), ≥1 phiếu **của persona nhưng TRONG hạn** (⇒ chứng minh predicate overdue thật sự lọc), ≥1 phiếu quá hạn ở **terminal state** (⇒ chứng minh `workflow_state not in` còn sống). `{"overdue":1,"workflow_state":"Clinical Hold"}` ⇒ AND cả hai, và tập dòng ⊆ phạm vi persona | TC-IMM04-OVD-02 (〃) |

**Ràng buộc fixture (bắt buộc — nếu thiếu, TC XANH GIẢ):** `_OVERDUE_ANCHOR = "reception_date"` (`services/imm04.py:64`) + `OVERDUE_DAYS = 30` (`:63`). Phiếu **không** có `reception_date` ⇒ `reception_date < cutoff` là **NULL ⇒ FALSE** trong SQL ⇒ **0 dòng ⇒ assert vacuous**. Fixture của `TestCommissioningOneEngineScope` (`test_rowscope_invariant.py:776`) hiện **không** set `reception_date` ⇒ **KHÔNG** dùng lại nguyên trạng: đặt **class MỚI** với fixture riêng (§11.6 Never — cấm sửa 3 TC đang có ở class đó).

## 11.4 Ratify (0 dòng mã đổi) — deep-link ngoài phạm vi ⇒ **0 dòng**, KHÔNG 403

Kế thừa §10.6, phát biểu tường minh cho vendor deep-link (INV-CONN-21 vế "ngoài phạm vi"), vì đây là chỗ dev hay "sửa cho đúng cảm giác" thành 403:

| Ca | Kênh | Body | Vì sao KHÔNG 403 |
|---|---|---|---|
| Guest / không token | **dispatcher-403** (trước handler) | không có envelope | chưa xác thực ⇒ client re-auth |
| Vendor Engineer **thuần** (thiếu DocPerm read) | **in-handler cap-403** | HTTP-200 + Error envelope `FORBIDDEN` | thiếu **quyền loại** ⇒ nói thẳng |
| Vendor Engineer **hợp lệ**, deep-link thiết bị **ngoài** tập được giao | **không lỗi** | HTTP-200 + `{"items": [], "pagination": {"total": 0, …}}` | 403 ở đây **rò thông tin tồn tại** của bản ghi + biến "không có dữ liệu" thành "bạn bị chặn"; FE đã có empty-state **có ngữ cảnh** `list-empty-scoped` (`docs/imm-04/06 §11`) |
| Vendor Engineer hợp lệ, deep-link thiết bị **trong** tập được giao | không lỗi | **chỉ** dòng của thiết bị đó (phép GIAO, `scope.py:_intersect_in`) | không được nới thành "mọi thiết bị của tôi" |

## 11.5 Nghi thức **proof-by-mutation** (bắt buộc — thiếu = DoD không đạt)

Với mỗi bất biến MỚI, mutate **mã prod** (không mutate test), chạy **module-isolated**, dán output ĐỎ, rồi **hoàn nguyên** và chứng minh XANH lại:

| # | Mutation tại | Đổi thành | Kỳ vọng | Chứng minh điều gì |
|---|---|---|---|---|
| **M1** | `services/imm04.py:1113` | `total = frappe.db.count(_DT, query_filters)` | **ĐỎ** TC-IMM04-OVD-01 | đúng yêu cầu A3 nguyên văn. Nếu `db.count` **nổ** với list-form thì ĐỎ dạng *error* — **vẫn tính**, ghi rõ loại ĐỎ |
| **M2** | 〃 | `total = count_ignore_permissions(_DT, query_filters, None)` | **ĐỎ** TC-IMM04-OVD-01 | cùng shape (`get_all` nhận list-form) ⇒ cô lập **đúng nguyên nhân** row-scope, không lẫn với lỗi kiểu dữ liệu |
| **M3** | `services/imm04.py:1102` | bỏ `_dict_to_list_filters`, quay lại `safe_filters.update(...)` | **ĐỎ** TC-IMM04-OVD-02 | clobber `workflow_state` (bug cũ) vẫn bị bắt **dưới row-scope**, không chỉ dưới `Administrator` |
| **M4** (FE) | `CommissioningListView.vue:199` | `Tổng ${store.list.length} phiếu` | **ĐỎ** TC-FE-COMM-SE-07 | nguồn TỔNG là `store.pagination.total` (server), KHÔNG `items.length` |

**Bắt buộc ghi trong báo cáo:** với M1 và M4 — dán nguyên văn dòng đầu của traceback/assert ĐỎ. `QueryDeadlockError` = **ĐỎ GIẢ** (đa-phiên) ⇒ chờ quiescence, chạy lại, ghi rõ.

## 11.6 Boundaries vòng này (Always / Ask-first / Never)

- **Always**: chạy **module-isolated**, `timeout` ≥ 600000 ms, dán `Ran N tests … OK` · số TC mỗi module **≥ baseline §11.1** · mọi ĐỎ sửa **root cause ở mã prod** + test tái hiện viết **TRƯỚC** bản sửa · fixture uuid-suffix + `tearDownClass` dọn sạch · đặt TC mới vào **class MỚI** (read-fresh rồi append — file đang dirty ở phiên khác).
- **Ask-first**: đổi predicate `asset_commissioning_query` · đổi `_ALLOWED_FILTER_KEYS` · đổi copy/testid FE đã chốt · thêm bất biến ngoài INV-COMM-SCOPE-5/6.
- **Never**: ❌ nới assert / `skipIf` / đổi kỳ vọng để cho xanh · ❌ mock `frappe.get_list`/`frappe.db.count` để "chứng minh" scope · ❌ sửa 3 TC đang có của `TestCommissioningOneEngineScope` (`:929/:946/:977`) hoặc 4 TC `TestVendorDeepLinkIntersection` (`:1111/:1123/:1131/:1144`) · ❌ đổi `store.pagination.total` → `items.length` ở FE · ❌ bỏ `data-testid="list-empty-scoped"` · ❌ đổi OAS / 3 counter `test_mobile_oas` (vòng này **0** đổi OAS ⇒ **0** đổi counter) · ❌ `git commit` / `bench migrate` / `bench restart` / xoá dữ liệu prod · ❌ kết luận bằng `curl`.

**ĐỎ trong DANH SÁCH CẤM (báo cáo + backlog, TUYỆT ĐỐI KHÔNG sửa vòng này):** alias `Calibration Record`/`Calibration Schedule` (`AC-CR-109`) · vendor-IDOR IMM-11 · `assert_vendor_can_access` · `_VENDOR_SCOPE_FIELD_MAP` · `http_status` 400-vs-403 · whitelist `filters` IMM-11 · cổng G01–G06 · mobile OAS · notification. **OUT-OF-SCOPE:** counters `test_mobile_oas` · tiebreaker ALE `api/imm00.py:293` (`AC-CR-100`) · `AC-CR-99` (`docstatus==2`) · Việt hoá `PREVIEW_FIELDS` · tab «Bản ghi liên quan» · 403 ba nhánh vận hành · prefill nháp.

## 11.7 Backlog mở ra từ §11 (KHÔNG làm vòng này)

| # | Việc | Ưu tiên |
|---|---|---|
| `AC-CR-113` | 4 file test của §10 là **untracked** ⇒ chưa vào CI; cần user quyết `git add` (HARD-STOP user) — trước đó mọi "xanh" chỉ tồn tại trên máy dev | P1 · cần USER |
| `AC-CR-114` | `SMOKE-VENDORSCOPE-4` (`test_imm04.py:724 TestOverdueSlaLiveInvariant`) là `unittest.TestCase` chạy `Administrator`: nên **thêm** biến thể row-scoped hay **dời** hẳn sang `test_rowscope_invariant.py`? Đụng file tracked ⇒ ratify riêng | P2 |
| — | Kiểm cùng lỗ chứng minh cho **các tham số ảo khác** (`mine` ở IMM-08/09/11, `byt_status` ở IMM-00, `due_soon`) — mỗi cái mở nhánh shape riêng, chưa có TC row-scoped | P1 |

---

*§11 chốt 2026-07-30 (AC-CR-112). KHÔNG đổi quyết định §10; thêm ADR-…-06/07, INV-COMM-SCOPE-5/6, hạ cấp INV-VENDORSCOPE-4 → SMOKE. Thực thi: test `docs/imm-04/07 §IX` · FE `docs/imm-04/06 §11.5`. Vòng này **0** file `.py`/`.vue` prod đổi theo kế hoạch — chỉ thêm test; mọi sửa prod phát sinh phải là **root-cause của một ĐỎ thật** và ghi lại trong §11.5.*
