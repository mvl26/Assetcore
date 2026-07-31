# ADR-IMM00-TRUNCATION-SSOT — Hợp đồng TRUNG THỰC khi cắt danh sách (cross-cutting IMM-00/06/08/09/11/12)

| Mục | Giá trị |
|---|---|
| Status | **Accepted** — 2026-07-25 · **EXTENDS** (không supersede) `ADR-IMM00-APPROVAL-INBOX-F` (CR-43) |
| Scope | MỌI endpoint list **KHÔNG phân trang** phục vụ web-FE + mobile-BE · **mở rộng 2026-07-28 (§8): nguồn ĐÃ phân trang mà CLIENT vứt `pagination.total`** (cắt im lặng ở lớp client) |
| CR liên quan | CR-43 (inbox duyệt) · CR-46 (due-list PM + hiệu chuẩn) · CR-47 (competencies) · **CR-69 (3 endpoint device-profile history IMM-08/09/12)** · **AC-CR-80 (picker "người nhận việc" IMM-00 — xem §7)** · **AC-CR-100 (tab «Lịch sử» Chi tiết tài sản — xem §8; PM gọi "AC-CR-96", số đó đã bị chiếm — §8.0)** |
| SSoT code | `assetcore/services/shared/truncation.py::truncation_meta` (nguồn không phân trang) · `assetcore/utils/pagination.py::paginate` + `_MAX_PAGE_SIZE` (nguồn phân trang, §8) |
| Cập nhật | 2026-07-28 |

---

## 1. Context

Một endpoint list **không phân trang** (chỉ có trần cứng `limit`) trả về `N` dòng. Client **không có cách nào** biết `N` là "hết dữ liệu" hay "mới là phần đầu của 200 dòng". Đây là **cắt IM LẶNG** — hệ quả nghiệp vụ thật:

- **Màn hồ-sơ-vận-hành thiết bị (quét QR → 3 tab lịch sử)**: KTV chuẩn bị sửa máy mở tab "Lịch sử sửa chữa", thấy 10 phiếu, kết luận *"máy này hỏng 10 lần"*. Thực tế 34 lần. Quyết định **thay-vs-sửa** (WHO HTM *Decommission* / NĐ98 hồ sơ thiết bị) dựa trên một con số **sai bản chất** — không phải sai do bug tính toán mà do **hợp đồng API im lặng**.
- Cùng lớp lỗi đã đóng 3 lần trước ở nơi khác: inbox duyệt (CR-43), danh sách "Nhắc việc" PM/hiệu chuẩn (CR-46), năng lực KTV (CR-47).

Đến CR-69, đây là **lần thứ 4** ⇒ cần ghi ADR ở cấp cross-cutting (IMM-00) thay vì lặp lại lý lẽ trong từng module.

Ràng buộc kỹ thuật đi kèm:
- Envelope mobile của 3 endpoint history là **closed-schema** (`additionalProperties: false`) ⇒ nếu BE phát thêm khoá mà OAS chưa khai, payload THẬT **vi phạm** contract (validator/codegen strict reject). ⇒ **OAS phải đi CÙNG vòng với BE**, không tách vòng.
- Codegen Dart/Kotlin: `bool` ≠ `int` — một cờ khai `boolean` mà server phát `0/1` sẽ **crash lúc parse** (CR-01 / LL-BE-52).

---

## 2. Decision

### D1 — MỘT SSoT derive `(total, truncated)`

Mọi endpoint list không-phân-trang PHẢI derive cặp cờ qua `truncation_meta(fetched, limit, count_fn)`. **KHÔNG** nơi nào tự đếm một kiểu (không `len(rows) == limit` trần, không so `total` tự query riêng).

Ngữ nghĩa khoá (SSoT — mọi module đọc chỗ này, không định nghĩa lại):

| Khoá | Kiểu wire | Ngữ nghĩa |
|---|---|---|
| `total` | `integer` ≥ 0 | COUNT DB trên **ĐÚNG filter-set** và **ĐÚNG engine truy vấn** đã dùng lấy rows, **TRƯỚC** khi cắt `limit` |
| `truncated` | `integer` ∈ `{0,1}` | `1` ⟺ (`len(rows) >= limit` ∧ `total > limit`). Vừa khít trần (`total == limit`) ⇒ `0` |

### D2 — `truncated` là `int`, KHÔNG `bool`, KHÔNG `None`

Parity CR-01. Lý do là **codegen**, không phải thẩm mỹ: contract mobile sinh client Dart/Kotlin; `boolean` trong OAS ⇒ `bool` trong client ⇒ parse `0` crash.

### D3 — ADDITIVE, `required` GIỮ NGUYÊN

`total`/`truncated` là property **optional** (không đưa vào `required` của OAS). Hệ quả: client cũ + response BE **chưa deploy** (cửa sổ `--preload` chưa reload) vẫn hợp lệ ⇒ **0 breaking**. Client PHẢI coi `undefined` = *"không rõ có bị cắt"* → **không** hiện dải cảnh báo, **không** hiện `total` bịa.

### D4 — ZERO-COST ở ca thường

`count_fn` là **lazy**: chỉ gọi khi `fetched >= limit`. Ca thường (thiết bị có 3 phiếu, `limit=10`) ⇒ **0 query COUNT thêm**.

Hai hình thái nguồn:

| Hình thái | `count_fn` | Chi phí |
|---|---|---|
| Nguồn đi qua `BaseRepository.list` (đã trả `pagination.total`) | `lambda: pg["total"]` — **tái dùng**, KHÔNG query lần hai | **0 query thêm** ở MỌI ca (COUNT đã phát sẵn bởi Repo) |
| Nguồn `frappe.get_all` / SQL trần | `lambda: <Repo>.count(filters)` hoặc `frappe.db.count(dt, filters)` **cùng predicate** | 1 COUNT **chỉ khi** chạm trần |

### D5 — `limit` truyền vào `truncation_meta` PHẢI là **trần THỰC SỰ áp lên truy vấn** (không phải tham số thô của client)

Đây là điểm dễ sai nhất và là lý do D5 tồn tại như một quyết định riêng:

- `assetcore/utils/pagination.py::paginate` **CLAMP** `page_size` về `[1, 100]` (`_MAX_PAGE_SIZE = 100`) và trả trần đã clamp ở `pg["page_size"]`. Client gửi `limit=500` ⇒ rows thực bị cắt ở **100**, nhưng nếu so `fetched(100) < limit(500)` thì `truncation_meta` kết luận **"không cắt"** ⇒ **nói dối đúng thứ CR-69 sinh ra để xoá**.
- Chiều ngược lại với nguồn `frappe.get_all`: Frappe hiểu `limit_page_length=0` là **KHÔNG giới hạn**. So `fetched(N) < limit(0)` là `False` ⇒ `truncated = 1` trong khi **không dòng nào bị cắt** ⇒ **báo cắt oan**.

⇒ **Invariant INV-TRUNC-LIMIT**: đối số `limit` của `truncation_meta` **PHẢI bằng** trần đã thực sự áp lên truy vấn lấy rows (`pg["page_size"]` với nguồn Repo; `limit` đã clamp cùng quy tắc với nguồn `get_all`). Hai giá trị lệch nhau ⇒ cờ `truncated` sai — im lặng.

### D6 — `total` mang ngữ nghĩa **"tổng mà user NÀY được phép thấy"**, không phải "tổng trong DB"

`total` bắt buộc dùng **cùng engine** với rows (INV-ROWSCOPE, `ADR-IMM00-LIST-SCOPE §8.3`):

- nguồn `scope="user"` ⇒ `total` là count **permission-aware** (`frappe.get_list`);
- nguồn `scope="system"`/`"internal"` ⇒ `total` là count raw (`frappe.get_all`).

**KHÔNG** được "sửa" `total` thành `frappe.db.count` thô cho "chính xác hơn" — đó chính là bug production đã đóng (header *"Tổng 1430"* / bảng RỖNG). `total` lệch engine với rows = tái sinh lỗ `count != rows`.

---

## 3. Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| (A) Chuyển 3 endpoint history sang **phân trang đầy đủ** (`page`/`page_size`/`pagination{}`) | Đổi shape ⇒ **breaking** cho web-FE + mobile client đang chạy; 3 envelope closed-schema phải đổi `required`; nghiệp vụ không cần trang 2 (KTV cần "có bao nhiêu" chứ không lật trang). Có thể làm sau như CR riêng nếu UX yêu cầu. |
| (B) Chỉ trả `total`, để client tự suy `truncated = len(rows) < total` | Client phải biết `limit` hiệu lực **sau clamp** — thứ nó không nhìn thấy (D5). Đẩy một phép suy luận có bẫy sang 3 loại client khác nhau (web/Dart/Kotlin) = 3 chỗ sai độc lập. |
| (C) COUNT **vô điều kiện** mỗi lần gọi | +1 query cho ~mọi request trong khi ca chạm trần là thiểu số. Loại — vi phạm ZERO-COST (D4). |
| (D) `truncated` kiểu `boolean` / `null` khi không rõ | Crash codegen Dart/Kotlin (D2); `null` đẩy ambiguity ngược về client. |
| (E) Mỗi module tự viết helper đếm riêng | Đúng thứ ADR này cấm — 4 CR × 6 endpoint × mỗi nơi một quy ước = drift. |

---

## 4. Consequences

**Được:**
- Client (web + mobile) phân biệt được *"đã xem hết"* vs *"đang xem một phần"* ⇒ quyết định thay-vs-sửa / duyệt / nhắc việc dựa trên dữ liệu **không bị cắt câm**.
- Một quy ước duy nhất cho 6+ endpoint ⇒ codegen/mobile đọc 1 pattern, không phải 6.

**Trả giá / rủi ro:**
- Mỗi endpoint list không-phân-trang mới **phải nhớ** áp `truncation_meta` — chưa có guard tự động phát hiện "endpoint mới quên khai". *(Backlog: guard test quét endpoint list có `limit` mà `data` thiếu `total`/`truncated`.)*
- `total` là số **theo quyền của user hiện tại** (D6) — người đọc dashboard/khiếu nại có thể thấy 2 con số khác nhau cho 2 persona. Đây là **đúng theo thiết kế**, phải nói rõ trong tài liệu người dùng.
- Với nguồn `get_all` trần, ca chạm trần tốn thêm 1 COUNT.

---

## 5. Boundaries (Always / Never)

**Always**
- Derive `(total, truncated)` **chỉ** qua `truncation_meta` (SSoT).
- Truyền vào `truncation_meta` **trần thực tế** đã áp lên truy vấn (INV-TRUNC-LIMIT / D5).
- `count_fn` dùng **CÙNG filter-set + CÙNG engine** với truy vấn lấy rows (D6).
- Khai `total: integer` + `truncated: integer enum [0,1]` trong OAS **cùng vòng** với BE (closed-schema).
- Giữ `required` cũ của envelope (D3).

**Never**
- KHÔNG `truncated` kiểu `boolean`/`None`; KHÔNG `nullable`.
- KHÔNG đưa `total`/`truncated` vào `required` — **ngoại lệ DUY NHẤT có ADR**: envelope **MỚI tinh** chưa từng có client nào (không có gì để tương thích ngược) thì 4 khoá đều `required`, xem **ADR-IMM00-ASSIGN-03** (§7.2). Envelope ĐANG CHẠY được bồi thêm khoá thì luật gốc giữ nguyên.
- KHÔNG dùng `frappe.db.count` thô cho `total` khi rows chạy `get_list` (và ngược lại).
- KHÔNG đổi **tập row** trả về khi bồi 2 khoá này (CR truncation là **read-meta**, không phải CR scope).
- KHÔNG thêm path / operationId / param — `total`/`truncated` là **response meta**, không phải input.

---

## 6. Tham chiếu chéo

- `ADR-IMM00-APPROVAL-INBOX.md` §F (CR-43) — quyết định gốc, phạm vi inbox.
- `ADR-IMM00-LIST-SCOPE.md` §8.3 — INV-ROWSCOPE (`total` và rows cùng engine).
- `../imm-08/05_API_Specification.md` §9.2 · `../imm-09/05_API_Specification.md` §3.14-bis · `../imm-12/05_API_Specification.md` §20 — áp dụng CR-69.
- `../mobile/openapi/assetcore-mobile.openapi.yaml` — `AssetPmHistoryEnvelope` / `AssetRepairHistoryEnvelope` / `AssetIncidentHistoryEnvelope`.
- `./05_API_Specification.md` §III.23 · `./04_Backend_Design.md` §V.6 · `./06_Frontend_Design.md` §VIII.3 · `./07_Testing_QA.md` §XVII — áp dụng AC-CR-80 (picker phân công).
- `../mobile/openapi/assetcore-mobile.openapi.yaml` — `AssignableUserItem` / `AssignableUserListEnvelope` (op `listAssignableUsers`).

---

## 7. AC-CR-80 — áp dụng thứ 5: picker "người nhận việc" (`list_assignable_users`, IMM-00)

> **Status**: Accepted — 2026-07-27 · **EXTENDS** ADR này (không supersede). Đóng **mobile CR-75**.
> **Phạm vi**: `assetcore/api/user.py::list_assignable_users` + mirror `listAssignableUsers` + FE `ApproverSelect.vue`.

### 7.1 Context — hai lỗi TRÊN CÙNG một màn

Field "người nhận việc" (KTV sửa chữa / KTV PM / KTV hiệu chuẩn / người xử lý sự cố / KTV nghiệm thu / người duyệt) là nơi hai lớp lỗi đã biết gặp nhau:

1. **Danh sách nói dối theo chiều "ai"** — mobile CR-75: client chỉ có `listUsers(role=…)` **đơn trị**. Lọc `role='PM User'` thì **giấu mất** `PM Manager`/`Vendor Engineer`; không lọc thì liệt kê cả điều dưỡng/kế toán. Người giao việc chọn nhầm → BE từ chối bằng `IMM09-INVALID-TECHNICIAN` (422) **ngay tại giường bệnh**. Nguyên nhân gốc: **role-name không phải nguồn sự thật về quyền** (anti-pattern *RBAC dead-gate*).
2. **Danh sách nói dối theo chiều "bao nhiêu"** — `list_assignable_users` cắt cứng ở `limit` (`capable[:limit]`, `api/user.py:1094` trước AC-CR-80) mà **không công bố** đã cắt. Tổ trưởng thấy 20 người, kết luận "khoa mình chỉ có 20 KTV" trong khi có 47.

Lỗi (1) **đã được giải** ở BE từ 2026-07-22 (endpoint lọc theo `frappe.has_permission`) nhưng **vắng mirror** ⇒ mobile không biết mà dùng. Lỗi (2) còn nguyên.

### 7.2 Decisions

#### ADR-IMM00-ASSIGN-01 — Picker là TẤM GƯƠNG của validator, không phải diễn giải thứ hai

- **Decision**: tập người trả về PHẢI derive bằng **CÙNG predicate** mà validator dùng để chặn. `context='repair'` ⇒ `frappe.has_permission("Asset Repair", "write", user=u)` — chính là thân của `services/imm09.py:1657 _is_repair_capable` mà `services/imm09.py:1675 _assert_valid_technician` gọi.
- **Alternatives loại**: (a) nới `listUsers.role` thành mảng — vẫn là role-name, vẫn sai khi đổi tên vai/thêm vai (dead-gate); (b) bồi cờ `can_be_assigned_*` vào `UserListItem` — đẩy 1 endpoint chung phải biết mọi ngữ cảnh phân công + client vẫn phải lọc lấy; (c) lọc phía client bằng `imm_roles[]` — sai bản chất + `pagination.total` đếm TRƯỚC khi lọc ⇒ lại nói dối.
- **Consequences**: mỗi ngữ cảnh phân công mới = **1 dòng** trong `_ASSIGNABLE_CONTEXTS` (`api/user.py:1038`) chứ không phải một endpoint mới. Chi phí: 1 lần `has_permission` / ứng viên (in-memory, không SQL) — chấp nhận vì tập ứng viên đã bị giới hạn ở base-role holder + `search`.
- **Hệ quả kiểm chứng được**: **0 dead-pick** — không tồn tại người vừa hiện trong picker vừa bị validator từ chối (INV-ASSIGN-5/6).

#### ADR-IMM00-ASSIGN-02 — `count_fn` đếm SAU lọc năng lực (in-memory), KHÔNG COUNT DB

- **Decision**: `truncation_meta(fetched=len(items), limit=limit, count_fn=lambda: len(capable))`.
- **Vì sao**: predicate năng lực **không biểu diễn được bằng SQL filter** (`has_permission` = DocPerm ∧ row-level ∧ UserPerm, resolve trong Python). Nếu `count_fn` là `count_ac_users(...)` (COUNT DB trước lọc) thì `total` sẽ **lớn hơn** số người thật sự được phép ⇒ dải cảnh báo hiện "20/143" trong khi chỉ 24 người hợp lệ — **tái sinh đúng lớp lỗi `count != rows`** đã đóng ở ADR-IMM00-LIST-SCOPE §8.3.
- **Consequences**: `total` **miễn phí** (0 query thêm ở mọi ca — mạnh hơn D4 vốn chỉ zero-cost ở ca không cắt). Đánh đổi: vòng `has_permission` chạy trên TOÀN BỘ ứng viên khớp `search`, không dừng sớm ở `limit` — **cố ý**, vì dừng sớm thì không biết `total`. Với site hiện tại (bậc trăm user AssetCore) chi phí chấp nhận được; nếu tăng bậc nghìn → xem *Roadmap* §7.5.

#### ADR-IMM00-ASSIGN-03 — Envelope MỚI ⇒ 4 khoá đều `required` (thu hẹp D3 có chủ đích)

- **Decision**: `AssignableUserListEnvelope.data.required = [items, total, truncated, limit]`.
- **Vì sao khác D3** (vốn bắt `total`/`truncated` là optional): D3 bảo vệ **client cũ + envelope ĐANG CHẠY** được bồi thêm khoá. Ở đây `data` **đổi từ mảng trần sang object** — client cũ đã không đọc được nhánh này bất kể `required`; mirror lại **chưa từng** khai op này (0 client mobile). Giữ optional chỉ tạo ảo giác tương thích.
- **Consequences**: OAS mô tả **hợp đồng ĐÍCH**; BE + web-FE PHẢI land **CÙNG VÒNG** (Bước-4). Trong cửa sổ `gunicorn --preload` chưa reload, BE vẫn trả **mảng trần** ⇒ xem ADR-ASSIGN-04.

#### ADR-IMM00-ASSIGN-04 — FE là *tolerant reader* trong cửa sổ chưa reload

- **Decision**: `api/user.ts::listAssignableUsers` chuẩn hoá **cả hai hình dạng**: `Array` (BE cũ) → `{items: rows, total: rows.length, truncated: 0, limit}`; object → dùng nguyên. Dải cảnh báo chỉ hiện khi `truncated === 1`.
- **Vì sao**: dự án chạy `gunicorn --preload` ⇒ sửa `api/*.py` **không có hiệu lực** đến khi USER reload (HARD-STOP). Không có lớp chuẩn hoá thì picker **trắng danh sách** trong cả cửa sổ đó — hồi quy nặng hơn chính lỗi đang sửa.
- **Consequences**: 1 hàm chuẩn hoá ~6 dòng, có test cho cả 2 hình dạng. Gỡ được sau khi prod đã reload (backlog, không tự động gỡ).

### 7.3 Invariants (INV-ASSIGN-*) — chấm được bằng test

| ID | Phát biểu | Vi phạm nghĩa là |
|---|---|---|
| INV-ASSIGN-1 | `len(items) <= limit` | trần không được áp |
| INV-ASSIGN-2 | `total` = số người ĐƯỢC PHÉP (đếm SAU lọc năng lực) | dải cảnh báo phóng đại (count≠rows) |
| INV-ASSIGN-3 | `truncated == 0` ⇒ `total == len(items)`; `truncated == 1` ⟺ `total > limit` | client không phân biệt được "hết" vs "còn" |
| INV-ASSIGN-4 | `isinstance(truncated, bool) is False` ∧ `truncated ∈ {0,1}`; `total`, `limit` là `int ≥ 0` | crash codegen Dart/Kotlin (CR-01) |
| INV-ASSIGN-5 | ∀ `u ∈ items` (context='repair') ⇒ `_is_repair_capable(u.name)` là True | **dead-pick**: chọn xong bị từ chối |
| INV-ASSIGN-6 | user KHÔNG có trong `items` ⇒ `_assert_valid_technician` raise `VALIDATION_ERROR`/422 | picker rộng hơn gate ⇒ vẫn 422 oan |
| INV-ASSIGN-7 | `limit` ngoài `[1,100]` bị clamp; `truncated` tính theo `limit` ĐÃ clamp; `data.limit` trả trần đã clamp | INV-TRUNC-LIMIT (D5) bị phá — báo "không cắt" khi đã cắt |
| INV-ASSIGN-8 | `context` ∉ enum ⇒ **HTTP-200** + `{success:false, code:'VALIDATION_ERROR', http_status:400}`, thông điệp tiếng Việt, **KHÔNG** chứa tên DocType/cột/SQL | lộ bề mặt phân quyền + client logout oan |

### 7.4 Boundaries (Always / Never) — riêng cho họ picker

**Always**
- Mọi field chọn người đi qua `list_assignable_users` (web: `<ApproverSelect context="…">`; mobile: `listAssignableUsers`).
- Ngữ cảnh **cần năng lực thao tác** → context capability; ngữ cảnh **chỉ mô tả người** (giám sát, thủ kho, trưởng khoa, leo thang SLA) → `context="user"`.
- Thêm field phân công mới = thêm **1 khoá** vào `_ASSIGNABLE_CONTEXTS` **và** enum `context` trong OAS **cùng vòng** (guard `cr80_b` import hằng THẬT).
- FE render dải "Đang hiển thị N/M người — gõ tên để tìm thêm" khi `truncated===1`.

**Never**
- KHÔNG nhận `doctype`/`ptype` thô từ client (allowlist nhận **tên ngữ cảnh** — chống probe quyền tuỳ ý).
- KHÔNG lọc người theo **tên role** ở bất kỳ tầng nào (BE, FE, mobile).
- KHÔNG trả `roles`/`imm_roles`/bí mật trong phần tử picker (mời client lọc lại theo role-name = tái sinh lỗi).
- KHÔNG đưa **giá trị** của `_ASSIGNABLE_CONTEXTS` (tên DocType) vào thông điệp lỗi.
- KHÔNG nâng `limit` để "thấy hết" — đường đúng là `search` server-side (trần cứng 100).

### 7.5 Roadmap / backlog mở

- **[P2 — perf]** Nếu số user AssetCore lên bậc nghìn: cache `has_permission` theo `(doctype, ptype)` trong 1 request, hoặc rút gọn ứng viên bằng role-set **trước** khi kiểm capability (chỉ như *tiền lọc*, KHÔNG thay predicate).
- **[P2 — parity]** `imm04.get_users_by_role` (nhánh `role=` của `ApproverSelect`) **vẫn cắt im lặng** — cùng lớp lỗi, chưa đóng vòng này.
- **[P2 — parity]** `layout.get_unread_notifications` trả `{count, items}` **không có** `truncated` (`count` là tổng chưa đọc, không phải tổng của `items`) — cần rà theo D1.
- **[P3]** Guard tự động: quét endpoint có tham số `limit` mà `data` thiếu `total`/`truncated` (đã ghi ở §4 "trả giá").

---

## 8. AC-CR-100 — áp dụng thứ 6: nguồn **ĐÃ phân trang** ⇒ cắt IM LẶNG dịch xuống **lớp CLIENT** (tab «Lịch sử» — Chi tiết tài sản)

> **Status**: Accepted — 2026-07-28 · **EXTENDS** ADR này (không supersede). Đóng backlog run-3 *«`AssetDetailView.vue:202` vẫn `as unknown`, vứt `pagination.total`»*.
> **Phạm vi (đóng khung, đo được)**: `frontend/src/views/asset/AssetDetailView.vue` (chỉ tab `timeline`) · **ĐÚNG 1 dòng** `assetcore/api/imm00.py:293` (`_ORDER_EVENT_TS_DESC`) · 1 file test FE mới · 1 class guard mới trong `assetcore/tests/test_imm00.py`.
> **0 OAS delta · 0 schema/DocType/cap/enum/patch delta · 0 file `.py` prod nào khác.**

### 8.0 Đối chiếu số CR — ĐỌC TRƯỚC KHI VIẾT DÒNG ĐẦU TIÊN

Đề mục PM gọi vòng này là **«AC-CR-96»**. Số đó **ĐÃ BỊ CHIẾM** bởi 4 nợ-khai-tên của các vòng trước (dedup ledger — STATE §Process, blocker #15):

| Số | Đã dành cho | Nguồn (verify @source) |
|---|---|---|
| `AC-CR-96` | `apply_vendor_scope` **ghi đè** khoá `asset` do caller gửi (INV-CONN-21, vendor `count != drill`) | `ADR-IMM00-CONNECTIONS-TREE.md:1482,1537,1602` |
| `AC-CR-97` | Nút «Tạo …» cho ô rỗng (đổi số từ AC-CR-95) | `ADR-IMM00-CONNECTIONS-TREE.md:1589` + `README.md:9` |
| `AC-CR-98` | `list_commissioning` `get_all`→`get_list` (INV-CONN-27, vendor row-scope) | `ADR-IMM00-CONNECTIONS-TREE.md:1711` |
| `AC-CR-99` | Ô đếm chưa loại `docstatus==2` (INV-CONN-26) | `README.md:9` |

⇒ **Vòng này = `AC-CR-100`** (số đầu tiên còn trống; verify `grep -rho "AC-CR-[0-9]\+" docs/ assetcore/ frontend/src | sort -u` — `1[0-9][0-9]` rỗng lúc chốt spec 2026-07-28). Mọi ID mới của vòng dùng **họ `TL`** (timeline) để không đụng dãy `CONN`/`ASSIGN`: `FR-00-TL-01` · `BR-00-TL-01..09` · `INV-TL-1..11`. **KHÔNG** dùng lại số `96` trong bất kỳ artifact nào của vòng (commit message, tên test, comment) — trùng số = ledger vô dụng.

### 8.1 Context — BE **không** nói dối, **client** nói dối

`get_asset_timeline` **đã** phân trang đầy đủ: `_ok({"pagination": pag, "items": items})` (`api/imm00.py:1216-1247`), `pagination` = `paginate(total, page, page_size)` với `total = frappe.db.count("Asset Lifecycle Event", {"asset": name})`. Envelope mobile cũng **đã** khai `data.required = [pagination, items]` + `Pagination.required ∋ total` (`docs/mobile/openapi/assetcore-mobile.openapi.yaml:1868-1901`, `:852-880`). Nghĩa là: **sự thật CÓ trên dây**, chỉ không ai đọc.

Chỗ mất:

```ts
// frontend/src/views/asset/AssetDetailView.vue:202 (TRƯỚC AC-CR-100)
const res = await getAssetTimeline(props.id, 1, 100) as unknown as { items?: typeof timeline.value }
if (res?.items) timeline.value = res.items
```

`as unknown as { items?: … }` **xoá `pagination` khỏi kiểu** ⇒ `pagination.total` biến mất khỏi tầm nhìn của trình biên dịch, dù `api/imm00.ts:71` khai đúng `Promise<PaginatedResponse<AssetLifecycleEvent>>` và `types/imm00.ts:15` khai đúng `pagination.total`. Đây là **lỗi lớp KIỂU**, không phải lỗi hiển thị: hạ tầng đúng, một dòng cast vô hiệu hoá nó. Tệ hơn: view gọi cứng `page = 1` và **không có** đường sang trang 2 ⇒ dữ liệu vượt trần **không thể** tới được người dùng bằng bất kỳ tương tác nào.

Hai trạng thái bị **gộp** cùng chỗ (cũng do thiếu `total`):
- `:824` `v-if="!timeline.length"` → *"Chưa có sự kiện vòng đời"* — nhưng `timeline` cũng rỗng khi **API lỗi** (`loadTimeline` không `try/catch`, promise reject bị nuốt trong `onTabChange`) ⇒ **lỗi mạng hiện thành "thiết bị chưa có lịch sử"**.
- `:399` `if (tab === 'timeline' && !timeline.value.length)` → cùng vị-từ dùng làm cờ "chưa tải" ⇒ *rỗng thật* và *chưa tải* không phân biệt được ở **lớp logic**, nên không có cách nào phân biệt ở lớp hiển thị.

**5 câu hỏi domain (grounding):**
1. **Stage HTM?** *Operation → Maintenance → Decommission* — dòng thời gian vòng đời là hồ sơ nền cho quyết định **thay-vs-sửa** và cho biên bản **giải nhiệm**.
2. **NĐ98?** Nghĩa vụ lập & lưu **hồ sơ thiết bị y tế** đầy đủ, truy vết được toàn bộ hoạt động gắn với thiết bị *(số điều cụ thể: `[UNVERIFIED]` — chưa dẫn được từ `docs/gmdn/`; giữ nhãn thay vì bịa)*. Trục audit-trail hash-chain (`utils/lifecycle.py`) chỉ có giá trị nếu **người đọc thấy đủ mắt xích**.
3. **Stakeholder?** KTV (chuẩn bị sửa/PM) · Trưởng phòng VTTB (thay-vs-sửa, hồ sơ thanh lý) · Auditor/thanh tra (đối chiếu hồ sơ).
4. **Lifecycle event?** MỌI `Asset Lifecycle Event` của asset (`installed`/`commissioned`/`pm_completed`/`repair_completed`/`calibration_passed`/`out_of_service`/`restored`/`depreciation_stopped`/`decommissioned`…).
5. **Hậu quả nếu data sai?** Thiết bị vận hành nhiều năm dễ vượt 100 ALE (mỗi lần đổi trạng thái sinh 1–2 event; mỗi PM/CM/hiệu chuẩn 1 event). Tab hiện **đúng 100 dòng** và **im lặng** ⇒ người đọc kết luận *"đây là toàn bộ lịch sử"*. Quyết định thanh lý / trả lời thanh tra dựa trên hồ sơ **bị cắt câm** — cùng lớp lỗi CR-69, nhưng lần này bị cắt **sau khi** BE đã nói thật.

⇒ Đây là **lần thứ 6** của lớp lỗi này (CR-43 · CR-46 · CR-47 · CR-69 · AC-CR-80 · **AC-CR-100**), và là lần đầu **thủ phạm là client** ⇒ ADR phải nói rõ nghĩa vụ **hai đầu**.

### 8.2 Decisions

#### D-TL-1 — `total` của server là SSoT; **CẤM cast** giá trị trả về của api-client tại view

- **Decision**: view tiêu thụ đúng kiểu `PaginatedResponse<AssetLifecycleEvent>`; số công bố cho người dùng là `res.pagination.total`. **Không** `as unknown`, **không** `as any`, **không** interface tự khai lại tại view. Kiểu sai/thiếu ⇒ sửa tại `api/*.ts` hoặc `types/*.ts` (SSoT kiểu), **không** cast tại chỗ dùng.
- **Vì sao**: cast tại view làm mất **âm thầm** đúng thứ hợp đồng đang cố nói (`pagination`). Đây là biến thể client của *"đếm một kiểu ở mỗi nơi"* mà D1 cấm ở BE.
- **Consequences**: `npx vue-tsc --noEmit` trở thành **guard sống** cho lớp truncation ở FE — thêm khoá vào envelope là đủ để compiler nhắc chỗ dùng.

#### D-TL-2 — Phân trang chỉ trung thực khi **thứ tự TIỀN ĐỊNH**: `timestamp desc` phải có tiebreaker

- **Hiện trạng (@source)**: `_ORDER_EVENT_TS_DESC = "timestamp desc"` (`api/imm00.py:293`) — **không** tiebreaker.
- **Vì sao vỡ**: ALE trùng `timestamp` là **ca thường**, không phải biên: một `transition_asset_status` có thể emit ≥2 event trong cùng giây (vd `restored` + `depreciation_stopped`), patch/seed emit hàng loạt. Với hàng trùng khoá sắp xếp, MySQL **không đảm bảo** thứ tự nhất quán giữa hai truy vấn `LIMIT/OFFSET` khác nhau ⇒ trang 2 có thể **lặp** dòng của trang 1 **và BỎ SÓT** dòng khác. Dedupe theo `name` ở client (D-TL-5) che phần **lặp** nhưng **không phục hồi** phần **sót** ⇒ "đã tải hết" mà vẫn thiếu = **đúng lớp lỗi đang đóng, chỉ đổi cơ chế**.
- **Decision**: `_ORDER_EVENT_TS_DESC = "timestamp desc, name desc"`. `Asset Lifecycle Event` dùng `autoname: naming_series:` ⇒ `name` **tăng đơn điệu theo thứ tự ghi** ⇒ tiebreaker vừa tiền định vừa **đúng chiều thời gian thật**. Precedent trong repo: `services/imm10.py:76 order_by="published_date desc, name desc"`.
- **Biên thay đổi**: sửa **giá trị hằng trên ĐÚNG 1 dòng** ⇒ **0 dịch dòng** trong `api/imm00.py` ⇒ **0 cite-drift** cho các guard cite `@api/imm00.py:<line>` (OAS + `test_mobile_oas`).
- **Consequences**: vòng này **đụng `.py` prod** ⇒ mở **1 blocker `bench restart` mới** (live-HTTP giữ thứ tự cũ đến khi USER reload — `gunicorn --preload`). DoD chấm bằng `run-tests` (logic-level, fresh-import), **KHÔNG curl** (LL-DEPLOY-07/08).

#### D-TL-3 — Ba trạng thái tách rời ở **lớp logic**, không chỉ ở lớp hiển thị

| Trạng thái | Vị-từ **duy nhất** được dùng |
|---|---|
| *chưa tải* | `timelinePage === 0` |
| *rỗng THẬT* | `timelinePage > 0 ∧ timelineTotal === 0 ∧ timelineError === null` |
| *lỗi* | `timelineError !== null` |

**CẤM** dùng `!timeline.length` làm vị-từ cho *"chưa có"* hoặc *"chưa tải"* ở bất kỳ đâu trong tab (đây chính là chỗ 3 trạng thái bị gộp hôm nay: `:824` + `:399`).

#### D-TL-4 — «Tải thêm» tăng `page`, **GIỮ** `page_size = 100`

`page_size` cố định `= _MAX_PAGE_SIZE` (`utils/pagination.py:11`). **KHÔNG** nâng `page_size` để "lấy nhiều hơn" — server clamp về 100 (D5/INV-TRUNC-LIMIT) nên client sẽ **tưởng** đã xin 200 mà chỉ nhận 100: đúng kiểu nói dối D5 sinh ra để xoá. Hằng FE phải mang comment trỏ về `utils/pagination.py:11`.

#### D-TL-5 — APPEND + **dedupe theo `name`** (giữ cả sau D-TL-2)

Trang sau **append** vào cuối, không thay thế. Dedupe theo `name` là **bất biến vĩnh viễn**, không phải cái vá cho D-TL-2: ALE mới sinh **giữa** hai lần bấm sẽ **dịch cửa sổ** (thứ tự desc ⇒ chèn ở đầu) làm trang k+1 lặp dòng cuối của trang k. Dedupe là phòng thủ đúng chỗ cho ca đó.

#### D-TL-6 — `total` = response **mới nhất** thắng; hiển thị không bao giờ nhỏ hơn số dòng đang render

`timelineTotal = max(res.pagination.total, timeline.length)`. Vì sao vế `max`: nếu event bị xoá giữa hai lần bấm, `total` mới có thể **nhỏ hơn** số dòng đã render ⇒ dải "Đang xem 137/100" là vô nghĩa với người đọc. Không có `max` thì `M > N` ⇒ nút ẩn nhưng dải vẫn khoe thiếu.

#### D-TL-7 — Không dead-end: mọi trạng thái lỗi có **đường hành động** tải lại đúng trang lỡ

Lưu `{page, mode}` tại thời điểm lỗi (`timelineErrorPage` / `timelineErrorMode`); `timeline-retry` gọi lại **đúng** cặp đó. Lỗi ở trang ≥2 **KHÔNG** xoá dòng đã tải (đang xem 200/500 mà mất sạch vì 1 lỗi mạng = hồi quy). Nếu chỉ dựa vào "mở lại tab để thử lại" thì lỗi trang ≥2 là **bế tắc** (guard nạp lười thấy `timelinePage > 0` ⇒ không nạp lại) — đó là lý do nút retry là **bắt buộc**, không phải trang trí.

#### D-TL-8 — Chống «Tải thêm» **không tiến** (vòng lặp câm)

"Hết nguồn" (`exhausted`) được suy từ **hai** điều kiện: (a) trang trả **ít dòng hơn trần** (`rows.length < page_size`), hoặc (b) trang append trả **0 dòng MỚI sau dedupe**. Hậu điều kiện **duy nhất** áp sau mỗi lần nạp: `exhausted ∧ M < N` ⇒ danh sách đã đổi dưới chân người dùng ⇒ **ẩn** nút + hiện dải *«Danh sách sự kiện đã thay đổi trong lúc tải. Vui lòng tải lại.»* + retry **mode `reset`**. **CẤM** tồn tại trạng thái (nút ẩn ∧ dải "Đang xem một phần" hiện ∧ 0 đường hành động) — kể cả ca "trang cuối ngắn **và** có dòng trùng" (`M = 132 < N = 137`).

#### D-TL-9 — Refresh sau thao tác ghi = **reset về trang 1**; «Tải thêm» KHÔNG reset

2 call-site hiện có (`confirmTransition`, `confirmDecommission` → `loadTimeline()`) giữ nguyên ngữ nghĩa **reset** (event mới nhất nằm đầu, người dùng cần thấy ngay). `loadMoreTimeline()` là hàm **khác**, chỉ append. Tách 2 hàm là điều kiện để A6 ("nút «Tải thêm» KHÔNG reset về trang 1") chấm được.

### 8.3 Invariants (INV-TL-*) — chấm được bằng test, không bằng mắt

| ID | Phát biểu | Vi phạm nghĩa là |
|---|---|---|
| **INV-TL-1** | Trong `loadTimeline`/`loadMoreTimeline`/`fetchTimelinePage` **không** có `as unknown`/`as any`; kiểu dùng là `PaginatedResponse<AssetLifecycleEvent>`; `vue-tsc --noEmit` 0 lỗi | mất `pagination` khỏi tầm nhìn compiler — lỗi gốc tái phát |
| **INV-TL-2** | Số công bố `N` **= `res.pagination.total`** (SERVER), KHÔNG phải `timeline.length` | tab lại tự đếm — cắt im lặng |
| **INV-TL-3** | `timeline-load-more` render ⟺ (`M < N` ∧ ¬`timelineExhausted`) | nút chết (không còn gì để tải) hoặc dữ liệu không thể tới được người dùng |
| **INV-TL-4** | `timeline-viewing` render ⟺ `M < N`; nội dung **đúng** `Đang xem M/N` | "đang xem hết" và "đang xem một phần" lẫn nhau |
| **INV-TL-5** | `M ≤ N` **luôn** (D-TL-6) | dải khoe số vô nghĩa ("Đang xem 137/100") |
| **INV-TL-6** | Tải tới hết ⇒ `M == N` ∧ 0 `name` trùng ∧ nút ẩn ∧ dải "Đang xem" tắt | `count != rows` ở lớp UI (bất biến ADR-IMM00-LIST-SCOPE §4b) |
| **INV-TL-7** | `timeline-error` ⊕ `timeline-empty` — **không bao giờ đồng hiện**; `timeline-empty` chỉ khi `timelinePage>0 ∧ N==0 ∧ error==null` | lỗi mạng hiện thành "thiết bị chưa có lịch sử" (lỗi gốc) |
| **INV-TL-8** | **Không** tồn tại trạng thái (nút ẩn ∧ dải "Đang xem" hiện ∧ 0 nút hành động) | bế tắc: người dùng biết còn dữ liệu nhưng không có cách lấy |
| **INV-TL-9** | `pagination.total` == COUNT thật trên `{asset: name}` (⇒ `≥ len(items)`); `total_pages == ceil(total/page_size)`; `names(page k) ∩ names(page k+1) = ∅` | "total = len(items)" tái phát / phân trang lặp-sót (D-TL-2) |
| **INV-TL-10** | `"Asset Lifecycle Event" ∉ hooks.permission_query_conditions` — **điều kiện TIÊN QUYẾT** để `frappe.db.count` (raw) ≡ count của `frappe.get_list` (permission-aware) | thêm PQC cho ALE mà giữ `db.count` ⇒ tái sinh `count != rows` (D6 / INV-ROWSCOPE) — guard PHẢI ĐỎ để buộc đổi engine |
| **INV-TL-11** | Mở màn ở tab `info` ⇒ **0** lần gọi `get_asset_timeline`; tab «Bản ghi liên quan» giữ `v-if` ⇒ **0** `get_connections` trước khi mở tab | hồi quy mount lười (AC-CR-89) |

### 8.4 Alternatives (đã loại)

| Phương án | Vì sao loại |
|---|---|
| (A) Giữ cast, chỉ thêm dòng chữ "đang hiện 100 dòng gần nhất" | Vẫn **không** biết tổng ⇒ vẫn không trả lời được câu hỏi nghiệp vụ *"máy này có bao nhiêu sự kiện?"*. Và dữ liệu vượt trần vẫn **không thể** tới người dùng. |
| (B) Nâng `page_size` lên 500/1000 để "khỏi phân trang" | Server clamp 100 (D5) ⇒ client tưởng đã lấy hết ⇒ **nói dối mới**. Kèm tải nặng vô ích. |
| (C) Cuộn vô hạn (infinite scroll) thay nút | Khó chấm bằng test render; không có nơi đặt con số tổng; người dùng không biết còn bao nhiêu. Nút tường minh + dải số là **hợp đồng đo được**. |
| (D) Bồi `total`/`truncated` vào envelope như CR-69 | Nguồn NÀY **đã** phân trang đầy đủ (`pagination.total` required trong OAS). Thêm khoá = mở closed-schema + đụng 3 counter guard, **0 giá trị thêm**. |
| (E) Bỏ dedupe, tin thứ tự BE | Không đủ: ALE sinh **giữa** 2 lần bấm dịch cửa sổ (D-TL-5). Và trước D-TL-2, thứ tự vốn không tiền định. |
| (F) Sửa thứ tự ở FE (sort lại sau khi nhận) | Client **không thấy** dòng bị sót; sort chỉ sắp xếp thứ đã có. Nguyên nhân ở `ORDER BY` của truy vấn ⇒ phải sửa ở BE (D-TL-2). |
| (G) Chuyển tab «Lịch sử» sang endpoint mới có `truncated` | Endpoint mới cho việc đã làm được = drift; `get_asset_timeline` đang được mobile dùng (op `getAssetTimeline`) ⇒ 2 nguồn sự thật. |

### 8.5 Consequences

**Được:**
- Câu hỏi *"thiết bị này có bao nhiêu sự kiện vòng đời?"* trả lời được bằng **số của server**, và mọi dòng đều **tới được** người dùng (phân trang thật).
- Ba trạng thái *chưa tải / rỗng thật / lỗi* tách rời ⇒ lỗi hạ tầng không còn giả dạng "thiết bị chưa có lịch sử" (thứ khiến người đọc kết luận sai về **hồ sơ NĐ98**).
- `vue-tsc` thành guard sống cho họ truncation ở FE (D-TL-1).
- Khuôn mẫu cho **3 tab lịch sử PM/CM/Sự cố** còn treo (backlog CR-69 FE) — cùng vị-từ, cùng microcopy, cùng testid-family.

**Trả giá / rủi ro:**
- **Mở 1 blocker `bench restart` mới** (D-TL-2 đụng `api/imm00.py`). Live-HTTP giữ thứ tự cũ tới khi USER reload; QA **không** được kết luận qua curl trong cửa sổ đó.
- Thiết bị "già" (>100 ALE) cần **nhiều lần bấm** để xem hết — chấp nhận (thay cho im lặng). Nhu cầu "xuất toàn bộ lịch sử" là **CR khác** (`[ROADMAP]`).
- Mỗi lần bấm = 1 COUNT + 1 SELECT (BE đã đếm vô điều kiện từ trước — D4 không áp vì nguồn này phân trang thật, `total` là **required** của hợp đồng).

### 8.6 Boundaries (Always / Never) — họ tab lịch-sử-phân-trang

**Always**
- Công bố **số của server** (`pagination.total`), không bao giờ `items.length`, ở mọi tab đọc nguồn đã phân trang.
- Tách 3 trạng thái bằng **vị-từ riêng** (D-TL-3) — cờ trang/cờ lỗi, không mượn `length`.
- `page_size` cố định `= _MAX_PAGE_SIZE`, có comment trỏ `utils/pagination.py:11`.
- APPEND + dedupe theo `name`; mọi trạng thái lỗi có đường hành động (D-TL-7/8).
- `ORDER BY` của endpoint phân trang **luôn** có tiebreaker tiền định (`, name desc` / `, creation desc`).
- Microcopy tiếng Việt **đầy đủ** (LL-FE-53), testid theo họ `timeline-*` ở §8.9 — đổi tên testid = đổi hợp đồng ⇒ sửa `07 §XIX` **trước**.

**Never**
- KHÔNG `as unknown`/`as any` trên giá trị trả về của api-client tại view (D-TL-1).
- KHÔNG dùng `!items.length` làm cờ "chưa tải" hay "chưa có".
- KHÔNG nâng `page_size` vượt trần để tránh phân trang.
- KHÔNG reset danh sách khi bấm «Tải thêm»; KHÔNG xoá dòng đã tải khi trang sau lỗi.
- KHÔNG thêm khoá response / path / operationId (vòng này **0 OAS delta**).
- KHÔNG đụng `_MAX_PAGE_SIZE`, `paginate`, `truncation_meta`, 3 counter guard mobile (`_EXPECTED_TEST_COUNT` 1024 · `_GUARD_SUITE_SUM` 1167 · `_MOBILE_OAS_TOTAL` 1193 — đọc lại **từ đĩa** trước khi chấm).
- KHÔNG render 3 nhánh lịch sử PM/CM/Sự cố lên màn Chi tiết tài sản trong vòng này (§8.7). *(Phạm vi cấm = **vòng `AC-CR-100`**; hết hiệu lực từ `AC-CR-102` — xem [`ADR-IMM00-ASSET-OP-HISTORY §2`](./ADR-IMM00-ASSET-OP-HISTORY.md).)*

### 8.7 Nợ khai tên (backlog **có tên**, không im lặng)

- **`AC-CR-101` [P2 — fe]** Gỡ 2 cast mù còn lại **cùng file**: `loadKpi` (`AssetDetailView.vue:220`) và `loadChain` (`:225`) vẫn `as unknown as typeof …`. Cùng lớp lỗi D-TL-1 nhưng **ngoài** biên vòng này (2 endpoint đó không phân trang ⇒ không có `total` bị mất) ⇒ vòng riêng, quét cả `grep -rn 'as unknown' frontend/src`.
- **`AC-CR-102` ✅ RESOLVED 2026-07-30 — quyết định PM: phương án (c) ĐƯỢC CHẤP NHẬN, điều khoản «CẤM (c)» dưới đây bị SUPERSEDE bởi [`ADR-IMM00-ASSET-OP-HISTORY §2`](./ADR-IMM00-ASSET-OP-HISTORY.md).** Lý do cấm ("2 con số chỏi nhau") được **giải tán** bằng 3 điều kiện gắn kèm: **C1** vị-từ nằm TRONG tiêu đề section («Kết quả bảo trì» = `PM Task Log` **khác doctype** ô đếm · «Lần sửa chữa đã **hoàn thành**» = khai đúng `docstatus=1` · «Sự cố đã ghi nhận») ⇒ hai số trả lời **hai câu hỏi khác nhau** và mỗi số nói rõ mình là số của câu nào; **C2** mỗi dòng in ≥1 trường **ngoài** `PreviewSpec` của ô (`overall_result`/`is_late`/`mttr_hours`/`sla_breached`/`severity`/`fault_code`) ⇒ không nhân bản diện tích; **C3** 3 section THU mặc định + fetch lười theo section ⇒ 0 chi phí mở máy. Phương án (b) **không bị loại** — thành nợ riêng `AC-CR-104`. Văn bản gốc GIỮ NGUYÊN bên dưới (không xoá ADR cũ — P-DOC-3): ⤵
- **`AC-CR-102` [P1 — quyết định PM] (văn bản gốc 2026-07-28 — nay đã có quyết định, xem dòng trên)** Ba nhánh lịch sử PM/CM/Sự cố: `stores/imm08.ts::fetchPMHistory` · `stores/imm09.ts::fetchRepairHistory` · `api/imm12.ts::getAssetIncidentHistory` — **verify 2026-07-28: 0 caller non-test** (chỉ khai + export). Cùng 3 doctype (`PM Work Order` / `Asset Repair` / `Incident Report`) **đã có** preview + dải cắt + «Xem tất cả» đã lọc ở tab «Bản ghi liên quan» (`components/common/RelatedRecords.vue`, registry `ac_asset_dashboard.py:32,34,58`). Render lại ⇒ **2 con số chỏi nhau** cho cùng một nhánh: `get_asset_history` lọc `{"asset_ref": …, "docstatus": 1}` (`services/imm09.py:2608`) trong khi ô connections đếm **mọi** docstatus. Chọn **một**: (a) **xoá mã chết** ở FE, hoặc (b) **dời** 3 nhánh sang màn chi tiết PM/CM/Sự cố ("lịch sử cùng thiết bị") với đúng ngữ cảnh. **CẤM** phương án (c) "render lên màn Chi tiết tài sản".
- **[P3 — doc]** Sau khi D-TL-2 land: có thể refresh mô tả OAS `AssetTimelineEnvelope`/op `getAssetTimeline` để nêu tiebreaker. **Không bắt buộc** — chuỗi hiện tại ("order_by timestamp desc") vẫn ĐÚNG, chỉ chưa đầy đủ ⇒ tránh đụng OAS trong vòng có `.py` delta.
- **[P2 — fe, khuôn dùng lại]** ✅ **ĐÓNG 2026-07-30 bởi `AC-CR-115`** ([`ADR-IMM00-ASSET-OP-HISTORY §10`](./ADR-IMM00-ASSET-OP-HISTORY.md)) — 3 nhánh lịch sử PM/CM/Sự cố nay render **dải cắt** trong tab «Bản ghi liên quan» của màn Chi tiết tài sản. **Khác khuôn §8.9 ở đúng 1 điểm có lý do**: **KHÔNG** có «Tải thêm» (`D-OPH-19`) vì 3 endpoint **không có** tham số `offset`/`page` (`api/imm08.py:198` · `api/imm09.py:195` · `api/imm12.py:232`) ⇒ nút sẽ chết (LL-FE-47); lối ra là «Xem tất cả» đã mang `?asset=`. Điều kiện render dẫn xuất từ **`total − rows.length > 0`**, **KHÔNG** từ cờ `truncated` (`D-OPH-17` — cờ và số do 2 nhánh mã sinh, có thể lệch). Văn bản gốc: ~~«Áp đúng §8.9 cho 3 tab lịch sử IMM-08/09/12 (backlog CR-69 FE còn treo): `stores/imm08.ts:205` + `stores/imm09.ts:154` **có** state `total/truncated` mà 0 render; `stores/imm12.ts` chưa có state.»~~ *(state cả 3 store đã có từ `AC-CR-102`: `stores/imm08.ts:34-35` · `imm09.ts:26-27` · `imm12.ts:44-45`.)*

### 8.8 Microcopy SSoT (chép nguyên — KHÔNG tự đặt lại chuỗi)

| testid | Chuỗi hiển thị (VI) | Điều kiện render |
|---|---|---|
| `timeline-total` | `{N} sự kiện` | `timelinePage > 0 ∧ N > 0` |
| `timeline-viewing` | `Đang xem {M}/{N}` | `M < N` |
| `timeline-load-more` | `Tải thêm` (đang tải: `Đang tải…`) | `M < N ∧ ¬exhausted` |
| `timeline-empty` | `Chưa có sự kiện vòng đời` *(GIỮ NGUYÊN chuỗi cũ `:825`)* | `timelinePage > 0 ∧ N == 0 ∧ error == null` |
| `timeline-error` (tải lỗi) | `Không tải được dòng thời gian vòng đời. Vui lòng thử lại.` | `timelineError !== null` |
| `timeline-error` (danh sách đổi) | `Danh sách sự kiện đã thay đổi trong lúc tải. Vui lòng tải lại.` | D-TL-8 |
| `timeline-retry` | `Thử lại` | cùng điều kiện `timeline-error` |
| `timeline-loading` | `Đang tải dòng thời gian…` | `timelineLoading ∧ timelinePage == 0` |

### 8.9 Tham chiếu chéo

- Spec thực thi FE: [`./06_Frontend_Design.md` §VIII.11](./06_Frontend_Design.md) · Hợp đồng API: [`./05_API_Specification.md` §III.25](./05_API_Specification.md) · Test matrix + DoD: [`./07_Testing_QA.md` §XIX](./07_Testing_QA.md) · FR/BR: [`./02_Analysis_Design.md` §IV.40](./02_Analysis_Design.md).
- `ADR-IMM00-LIST-SCOPE.md` §8.3 (INV-ROWSCOPE — `total` và rows **cùng engine**) · §4b (bất biến `count == drill`).
- `ADR-IMM00-CONNECTIONS-TREE.md` §11 (họ testid tab) · §D-TAB-* (mount lười — INV-TL-11).
- `docs/mobile/openapi/assetcore-mobile.openapi.yaml:852-880` (`Pagination`, `total` **required**) · `:1868-1901` (`AssetTimelineEnvelope`) · `:14235` (op `getAssetTimeline`) — **0 delta vòng này**.

---
