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

*ADR-IMM00-LIST-SCOPE — chốt 2026-06-08. Gate phân tích; BE thực thi mục 4 + test mục 5 trước khi tuyên bố xong.*
