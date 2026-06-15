# ADR-IMM00-SEARCH-ESCAPE — Escape LIKE-metachar (`%` `_` `\`) trong tham số `search` của `list_assets` (literal-match + chống over-match + LIKE-backtracking DoS)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Master / Cross-cutting (list/search hardening) |
| Loại | ADR (cross-cutting — chạm `api/imm00.py::list_assets` + SSoT helper `services/imm00.py`) |
| Trạng thái | **[GATE] Chốt thiết kế 2026-06-11 (Vòng 13)** — BA phân tích + verify thực nghiệm; BE thực thi sau gate |
| Quyết định bởi | BA (phân tích + probe thực nghiệm trên site `miyano`) 2026-06-11 |
| Liên quan | `ADR-IMM00-LIST-SCOPE.md` (INVARIANT count==rows + permission-aware count), `04_Backend_Design.md §II.1.13-SEARCHESCAPE` (mới), `05_API_Specification.md` (search param row), `services/imm00.py::reserved_prefix_sql` (precedent ESCAPE-safe LIKE) |
| Schema/cap delta | **KHÔNG** — chỉ thêm 1 SSoT helper escape + đổi cách dựng `or_filters` LIKE-term trong `list_assets`. `CAP_SET_VERSION` GIỮ NGUYÊN. KHÔNG thêm cap/role/field/endpoint/enum/patch. |

---

## 0. Triệu chứng (RED hiện tại — chưa escape)

`api/imm00.py::list_assets` (dòng 290–298) dựng LIKE-term BẰNG nội suy chuỗi TRỰC TIẾP, KHÔNG escape metachar:

```python
or_filters = None
if search:
    like = f"%{search}%"                         # ← '_' / '%' / '\' do user gõ đi THẲNG vào pattern
    or_filters = [
        [_DT_ASSET, "asset_name",      "like", like],
        [_DT_ASSET, "asset_code",      "like", like],
        [_DT_ASSET, "manufacturer_sn", "like", like],
        [_DT_ASSET, "gmdn_code",       "like", like],
    ]
```

Trong SQL `LIKE`, **`_` = wildcard 1-ký-tự**, **`%` = wildcard nhiều-ký-tự**, **`\` = escape-char**. Vì `search` đi thẳng vào pattern, ký tự user gõ bị diễn giải như wildcard chứ KHÔNG phải literal:

| User gõ | Pattern hiệu dụng | Hậu quả (RED — verify thực nghiệm 2026-06-11) |
|---|---|---|
| `_` | `%_%` | **match GẦN NHƯ MỌI row** (mọi tên ≥1 ký tự) — over-match toàn bảng. Probe site `miyano`: `%_%` trả 10/10 asset. |
| `%` | `%%%` | **match-all** (`total == toàn tập hợp lệ`). Probe: `%%%%` trả 10/10. |
| `%%%%%%%%%%` (10×`%`) | nhiều wildcard liên tiếp | LIKE multi-wildcard → **backtracking pathological** (DoS bề mặt) + match-all. |
| `\` | `%\%` (lẻ) | escape-char lẻ → hành vi phụ thuộc engine; RED bề mặt: KHÔNG literal, có nguy cơ pattern lỗi. |

⟹ Vỡ ngữ nghĩa "tìm chuỗi con literal" + bề mặt over-match/DoS. (KHÔNG phải SQLi — đã parametrized; xem §5.)

---

## 1. Nền kỹ thuật BẮT BUỘC đọc — Frappe ORM `like` xử lý backslash/`%` (verify thực nghiệm + đọc source)

`frappe.model.db_query.DatabaseQuery` (động cơ của `frappe.get_list`/`get_all`, dùng ở CẢ `list_assets` items VÀ `count_with_or` sau ADR-LIST-SCOPE §4b) cho operator `like`/`not like` chạy (Frappe v15, `db_query.py:938-940`):

```python
if f.operator.lower() in ("like", "not like") and isinstance(value, str):
    # because "like" uses backslash (\) for escaping
    value = value.replace("\\", "\\\\").replace("%", "%%")
```

⚠️ **2 hệ quả phải nắm:**
1. **KHÔNG có `ESCAPE` clause tường minh** → MariaDB dùng default escape-char = backslash. `_`/`%` user gõ vẫn là **wildcard** (Frappe KHÔNG escape chúng hộ ta). ⟹ phải tự escape ở tầng app.
2. **Backslash bị nhân đôi** (`\` → `\\`) + `%` bị nhân đôi (`%` → `%%`, đây là param-format escape của driver, KHÔNG phải LIKE-escape). ⟹ chiến lược escape phải tính tới việc Frappe sẽ nhân đôi backslash.

> **Precedent trong codebase:** `services/imm00.py::reserved_prefix_sql` (§II.1.13-TESTPREFIX) đã gặp đúng minefield này và KHÔNG dùng ORM `not like` cho predicate cần escape — chuyển sang **raw-SQL `ESCAPE '\\'` tường minh** HOẶC `not in` (materialize names). Search-escape là vấn đề KHÁC (escape **input của user** trên 4 cột, OR) — ADR này chốt cách giải RIÊNG dưới đây, đã verify khớp INVARIANT.

---

## 2. Kết quả probe thực nghiệm (site `miyano`, 2026-06-11 — quyết định dựa-trên-dữ-liệu, KHÔNG đoán)

Seed 3 asset có metachar **literal** trong `asset_name` (`_PBu_<n>` chứa `_`, `_PBp%<n>` chứa `%`, `_PBb\<n>` chứa `\`) + 1 asset không metachar (`vent`). Đo `len(frappe.get_list(AC Asset, or_filters=[["asset_name","like", <pattern>]], limit_page_length=0))`. So 2 chiến lược escape ở tầng app **rồi đẩy qua ORM `or_filters`** (động cơ TỰ nhân đôi backslash như §1):

| User gõ | Escape **chỉ `%` và `_`** (KHÔNG đụng `\`)  → `_esc(t)=t.replace("%","\\%").replace("_","\\_")` | Escape **cả `\`,`%`,`_`** (backslash-first) | Acceptance |
|---|---|---|---|
| `_`  | **1** (chỉ row có `_` literal) ✅ | 1 ✅ | match literal `_` only |
| `%`  | **1** (chỉ row có `%` literal) ✅ | 1 ✅ | match literal `%` only |
| `\`  | **1** (chỉ row có `\` literal) ✅ | **0** ❌ | match literal `\` |
| `vent` | 1 ✅ | 1 ✅ | substring no-regress |
| `%%%%%%%%%%` | **0, hữu hạn** ✅ | 0 ✅ | DoS guard: không match-all |

**Kết luận (chốt):** với đường ORM `or_filters` (Frappe TỰ nhân đôi backslash), chiến lược **escape CHỈ `%` và `_` (mỗi cái prefix 1 backslash), KHÔNG escape `\`** thỏa MỌI acceptance — KỂ CẢ `search='\'` (1 backslash đơn) trả literal-backslash row, KHÔNG throw, KHÔNG 500. Chiến lược "backslash-first" (đúng cho raw-SQL có `ESCAPE` tường minh) lại **SAI cho đường ORM** vì Frappe đã nhân đôi backslash hộ — escape thêm sẽ thành 2 backslash → MariaDB match dấu backslash, lệch literal.

> **Vì sao count == rows GIỮ NGUYÊN (cốt lõi):** `list_assets` items dùng `frappe.get_list(or_filters=…)` và `count_with_or` (sau ADR-LIST-SCOPE §4b) CŨNG dùng `frappe.get_list(or_filters=…)` — **CÙNG động cơ DatabaseQuery, CÙNG `or_filters` đã-escape**. Mọi biến đổi pattern (kể cả nhân-đôi-backslash của Frappe) áp ĐỒNG NHẤT cho cả 2 path ⟹ `pagination.total == len(items)` byte-for-byte, MỌI persona, CẢ search & non-search. ADR này **KHÔNG** chạm `count_with_or`, `apply_vendor_scope`, `compose_reserved_into`, `permission_query_conditions` — chỉ đổi GIÁ TRỊ term trong `or_filters` (cùng 1 biến `or_filters` dùng cho cả count lẫn list).

> **Edge đã biết (NGOÀI acceptance, ghi rõ — KHÔNG chặn):** với term DÀI có `_`/`%` **kẹp giữa** các ký tự khác (vd user gõ `AC_001`), đường ORM có thể under-match do tương tác nhân-đôi-backslash + absent-ESCAPE của Frappe (probe: `PBu_<n>` → 0 thay vì 1). Acceptance Vòng 13 KHÔNG có input loại này (các substring hợp lệ `vent`/`AC-ASSET`/`35304` đều KHÔNG chứa metachar). Nếu sau này cần literal-match HOÀN HẢO cho metachar-kẹp-giữa → chuyển search sang **raw-SQL `ESCAPE '\\'` tường minh** (precedent `reserved_prefix_sql`) cho CẢ count lẫn list — **[ROADMAP]**, ngoài scope round này (đổi sang raw-SQL phải tự tay AND `apply_vendor_scope`/`compose_reserved_into`/permission → rủi ro cao, không ép Vòng 13).

---

## 3. Quyết định thiết kế (D1–D4)

> **D1 — SSoT helper escape DUY NHẤT.** Thêm 1 hàm thuần `escape_like_term(term: str) -> str` (đề xuất đặt cạnh `reserved_prefix_sql` trong `services/imm00.py`, HOẶC `services/shared/filters.py` nếu dùng chung nhiều endpoint — BE tự chốt vị trí, nhưng PHẢI 1 nơi). Hợp đồng: escape `%` → `\%` và `_` → `\_` (mỗi metachar prefix đúng 1 backslash); **KHÔNG đụng `\`** (Frappe ORM tự nhân đôi backslash — xem §1/§2). Total-function: KHÔNG raise với mọi input (str rỗng → trả rỗng; non-str → caller đã `str()` ở `list_assets`). Áp **NHẤT QUÁN cho CẢ 4 cột** `or_filters` qua 1 lời gọi — KHÔNG rải `.replace()` thủ công ở mỗi cột.

> **D2 — `list_assets` dùng term ĐÃ ESCAPE cho `or_filters`.** Đổi `like = f"%{search}%"` → `like = f"%{escape_like_term(str(search))}%"`. `or_filters` (4 cột) dùng `like` đã-escape. KHÔNG đổi gì khác trong `list_assets` (apply_vendor_scope / compose_reserved_into / count_with_or / get_list / fields / paginate GIỮ NGUYÊN). Vì `or_filters` được truyền y nguyên cho CẢ `count_with_or` (`api/imm00.py:305`) lẫn `frappe.get_list` (`:320`) → escape áp đồng thời 2 path.

> **D3 — INVARIANT `count == rows` BẤT BIẾN.** `pagination.total == len(items)` (cộng dồn các trang) cho CẢ path search & non-search, MỌI persona (senior/internal-technician read-all + Vendor Engineer isolated). Điều kiện đủ: count và list dùng CÙNG `or_filters` đã-escape qua CÙNG động cơ `frappe.get_list` (ADR-LIST-SCOPE §4b vẫn nguyên). KHÔNG được tách count sang `db.count`/raw-SQL (sẽ vỡ INVARIANT).

> **D4 — KHÔNG mở rộng tự phát sang endpoint khác round này.** ADR này CHỈ áp `list_assets`. Các list endpoint khác cũng nội suy `f"%{search}%"` trần (`list_suppliers` `api/imm00.py:994`, `list_device_models` `:1213-1219`, `list_audit_trail` q-search `:1436`, IMM-11 search…) có cùng lỗ over-match — ghi **[BACKLOG]** §6, xử lý riêng (dùng CHUNG `escape_like_term` SSoT). KHÔNG ôm Vòng 13.

---

## 4. Hợp đồng escape (BE thực thi — đã chốt, BE tự chốt cài đặt nhỏ)

### 4.1. Helper SSoT

```python
def escape_like_term(term: str) -> str:
    """Escape LIKE-metachar trong free-text search → match LITERAL khi đẩy qua
    ORM ``frappe.get_list(or_filters=[[field, "like", f"%{escape_like_term(t)}%"]])``.

    Frappe DatabaseQuery (db_query.py:938-940) cho ``like`` TỰ nhân đôi backslash
    (``value.replace("\\\\","\\\\\\\\")``) NHƯNG KHÔNG escape ``%``/``_`` (giữ wildcard) và
    KHÔNG emit ``ESCAPE`` clause. ⟹ tầng app phải prefix 1 backslash cho ``%``/``_``
    để biến chúng thành literal; KHÔNG đụng ``\\`` (engine đã nhân đôi hộ — escape
    thêm sẽ thành match dấu backslash, lệch literal — verify probe site miyano 2026-06-11).

    Total-function: KHÔNG raise. '' → ''. Áp cho CẢ 4 cột or_filters của list_assets.
    """
    return term.replace("%", "\\%").replace("_", "\\_")
```

> **Bất biến cài đặt:**
> - Thứ tự `.replace` không quan trọng giữa `%` và `_` (2 ký tự rời, không chồng); KHÔNG thêm bước `replace("\\", …)`.
> - KHÔNG dùng `frappe.db.escape` (escape giá trị SQL, KHÔNG escape LIKE-metachar — sai mục đích).
> - Vị trí: 1 nơi (SSoT). Nếu để ở `services/imm00.py` → import vào `api/imm00.py`. Nếu để ở `services/shared/filters.py` → đặt cạnh `pop_search`/`count_with_or` (tiện tái dùng cho các endpoint khác ở §6). **0 rải logic escape thủ công ngoài helper.**

### 4.2. Wiring `list_assets` (DELTA tối thiểu — 2 dòng)

```python
or_filters = None
if search:
    like = f"%{escape_like_term(str(search))}%"      # ← DELTA: escape literal metachar
    or_filters = [
        [_DT_ASSET, "asset_name",      "like", like],
        [_DT_ASSET, "asset_code",      "like", like],
        [_DT_ASSET, "manufacturer_sn", "like", like],
        [_DT_ASSET, "gmdn_code",       "like", like],
    ]
# ↓ KHÔNG ĐỔI: count_with_or + get_list dùng CÙNG or_filters đã-escape (INVARIANT D3)
total = count_with_or(_DT_ASSET, filters, or_filters)
...
items = frappe.get_list(_DT_ASSET, filters=filters, or_filters=or_filters if or_filters else None, ...)
```

### 4.3. Docstring `list_assets` — thêm 1 dòng

Bổ sung vào docstring hiện có (KHÔNG xoá phần count==rows/byt_status): *"`search` (free-text) đi qua `escape_like_term` (SSoT) → `%`/`_`/`\\` user gõ là KÝ TỰ LITERAL (không phải wildcard SQL): `search='_'`/`'%'` KHÔNG over-match toàn bảng, `search='\\'` KHÔNG throw. Escape áp CÙNG `or_filters` cho cả count (`count_with_or`) lẫn items (`get_list`) ⟹ INVARIANT `total==len(items)` giữ."*

---

## 5. SQLi vẫn an toàn (KHÔNG hồi quy) — đã verify

`search="x' OR '1'='1"` GIỮ 0-row + `total==len(items)`, KHÔNG throw. Lý do: `or_filters` đi qua `frappe.get_list` → DatabaseQuery **parametrize** giá trị (bind-param, KHÔNG nội suy chuỗi vào SQL). `escape_like_term` chỉ thêm escape LIKE-metachar TRƯỚC khi giá trị thành bind-param — KHÔNG mở bề mặt injection mới (dấu nháy/`OR` vẫn là dữ liệu literal). Probe `x' OR '1'='1` qua raw-SQL `ESCAPE '\\'` parametrized → 0 row, no throw. Test cũ `test_search_param_is_sqli_safe` (`test_imm00_reserved_prefix.py:311`) GIỮ GREEN.

---

## 6. Acceptance — bất biến phải đạt (BE viết test chứng minh — chi tiết ở `07_Testing_QA.md`)

| # | Input `search` | Yêu cầu | Test (đề xuất) |
|---|---|---|---|
| SE-1 | `'_'` | KHÔNG trả toàn bộ asset; chỉ khớp record có `_` LITERAL trong 1 trong 4 cột (`asset_name`/`asset_code`/`manufacturer_sn`/`gmdn_code`) | `test_search_underscore_is_literal_not_wildcard` |
| SE-2 | `'%'` | KHÔNG match-all; chỉ khớp record chứa `%` literal | `test_search_percent_is_literal_not_matchall` |
| SE-3 | `'\\'` (1 backslash) | KHÔNG throw / KHÔNG 500 / KHÔNG SQL error; khớp record chứa backslash literal | `test_search_backslash_no_error_literal` |
| SE-4 | (mọi path) | `pagination.total == len(items)` cho CẢ search & non-search, MỌI persona (count_with_or & get_list dùng CÙNG or_filters đã-escape) | `test_search_escaped_count_equals_rows` |
| SE-5 | `'vent'`, `'AC-ASSET'`, `'35304'` (GMDN, không metachar) | match đúng như trước (no-regress) | giữ `test_search_by_gmdn_code_substring` (`test_imm00_list_assets.py:54`) + smoke |
| SE-6 | `"x' OR '1'='1"` | 0-row + `total==len(items)`, KHÔNG throw | giữ `test_search_param_is_sqli_safe` (`test_imm00_reserved_prefix.py:311`) |
| SE-7 | (4 cột) | escape áp NHẤT QUÁN cho cả 4 cột qua 1 SSoT `escape_like_term` — grep-guard: KHÔNG có `.replace("%"`/`.replace("_"` LIKE-escape thủ công trong `api/imm00.py` (chỉ trong helper SSoT) | `test_escape_like_single_source` (grep-guard) |
| SE-8 | `'%%%%%%%%%%'` (10×`%`) | `total==len(items)` hữu hạn + KHÔNG match-all (mỗi `%` thành literal); thời gian truy vấn không bùng nổ (không multi-wildcard LIKE) | `test_search_many_percent_no_dos_matchall` |

> **SE-4 + SE-8 là bắt buộc** — chứng minh INVARIANT count==rows GIỮ sau escape VÀ DoS-surface đóng. SE-3 chứng minh backslash an toàn (no-500).

### Backlog (NGOÀI scope Vòng 13)

| Endpoint | Vị trí nội suy trần | Trạng thái |
|---|---|---|
| `list_suppliers` | `api/imm00.py:994` (`like = f"%{search}%"`) + raw-SQL `:1004-1006` | **[BACKLOG]** áp `escape_like_term` (raw path: thêm `ESCAPE '\\'`) |
| `list_device_models` | `api/imm00.py:1213-1227` (or_filters + raw-SQL escape parity) | **[BACKLOG]** |
| `list_audit_trail` (`q`) | `api/imm00.py:1436` (`like = f"%{q}%"`) | **[BACKLOG]** |
| IMM-11 `list_*` search | `test_imm11.py` search suite | **[BACKLOG]** |

> Khi xử lý backlog: dùng CHUNG `escape_like_term` SSoT (D1). Endpoint có path raw-SQL (`list_suppliers`/`list_device_models`) cần thêm `ESCAPE '\\'` tường minh + escape backslash (raw-SQL KHÔNG có Frappe-doubling → quy tắc escape KHÁC đường ORM: raw cần escape cả `\`,`%`,`_`). KHÔNG copy nguyên helper ORM sang raw mà không điều chỉnh.

---

## 7. Ràng buộc thực thi (HARD-STOP — quyền user)

- BE chỉ sửa file + chạy `bench --site miyano run-tests` / `bench execute` / `vitest`. **TUYỆT ĐỐI KHÔNG** git commit / push / merge / reset DB / drop site / bench restart / reload gunicorn / bench migrate / pip install. Working tree để user review.
- KHÔNG đổi `CAP_SET_VERSION`; KHÔNG thêm cap/role/field/endpoint/enum/patch. ADR này thuần đổi **giá trị LIKE-term** + thêm **1 helper escape**.
- KHÔNG mâu thuẫn ADR đã có: tương thích `ADR-IMM00-LIST-SCOPE` (count permission-aware GIỮ — escape áp CÙNG `or_filters` cho count lẫn list) + §II.1.13-TESTPREFIX (reserved-exclusion ANDed riêng, KHÔNG đụng or_filters search). ADR này CHỈ CỘNG escape vào term, KHÔNG gỡ lớp nào.

---

*ADR-IMM00-SEARCH-ESCAPE — chốt 2026-06-11 (Vòng 13). Gate thiết kế + verify thực nghiệm; BE thực thi §4 + test §6 trước khi tuyên bố xong. Probe escape table §2 = nguồn quyết định dựa-trên-dữ-liệu.*
