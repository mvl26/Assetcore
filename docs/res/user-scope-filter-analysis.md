# Phân tích — Lọc User chỉ thuộc AssetCore tại `/user-profiles`

**Ngày**: 2026-05-22
**Module**: IMM-00 (Data / User Management)
**Trang ảnh hưởng**: `frontend/src/views/auth/UserProfileListView.vue` → endpoint `assetcore.api.user.list_users`
**Vấn đề báo cáo**: Trang `http://localhost:3000/user-profiles` đang liệt kê toàn bộ Frappe System User, gồm cả những user không thuộc app AssetCore (ví dụ `buihoangviet` — user của ERPNext HR/Accounting).

---

## 1. Tóm tắt hiện trạng

### 1.1 Logic lọc hiện tại
`assetcore/api/user.py::list_users` (dòng 250–357) build filter:

```python
filters = {"user_type": "System User", "name": ["!=", "Guest"]}
```

Tức là **mọi System User của site Frappe đều xuất hiện**, không cần biết user đó có liên quan tới AssetCore hay không. Filter `role` chỉ kích hoạt khi FE truyền `role=` cụ thể (mặc định trống).

### 1.2 Hệ quả khi cài chung site với ERPNext / app khác
- `Administrator` → hiển thị (mong muốn).
- `buihoangviet` (HR/Accounting) → **không nên hiển thị**.
- User của app khác (Healthcare, CRM, Education…) → đều bị kéo vào.
- KPI "Tổng N người dùng" trên header bị thổi phồng, gây nhiễu báo cáo.
- Filter "Vai trò" của FE chỉ chứa 30 IMM Role, nên người dùng tưởng "Tất cả vai trò" = vai trò AssetCore — đây là **inconsistency UX**.

### 1.3 Nơi rò rỉ thứ hai (không chỉ list view)
| Endpoint | File | Vấn đề |
|---|---|---|
| `list_users` | `api/user.py:250` | Trang /user-profiles — bug chính |
| `list_frappe_users` | `api/user.py:801` | Autocomplete chọn User ở mọi form (Assignee, Owner, Approver…) — **cũng leak** |
| SmartSelect doctype="User" (FE) | nhiều form | Dùng `frappe.client.get_list` chuẩn — leak toàn site |
| Lifecycle Event `actor`, Work Order `assigned_to`, … | mọi DocType có Link User | Hệ thống vẫn cho phép gán user non-AssetCore → ghi audit trail "lạ" |

Fix bug list page mà không fix các điểm trên ⇒ rò rỉ vẫn còn ở mọi nơi khác.

---

## 2. Định nghĩa "User thuộc AssetCore" — 5 phương án

Đây là quyết định **business**, không phải kỹ thuật. Mỗi định nghĩa kéo theo edge case khác nhau.

### Phương án A — Có ≥1 IMM role
"User AssetCore" = user có ít nhất 1 role thuộc `Roles.ALL` (4 System + 26 Domain = 30 role).

| Ưu | Nhược |
|---|---|
| Semantic mạnh nhất — role chính là cơ chế phân quyền của app | `Administrator` của Frappe (không gán IMM role) sẽ biến mất → phải whitelist |
| Đồng bộ với `rbac.can()` — user nào AssetCore "nhìn thấy" thì user đó "có thể" làm gì đó | User Pending (chưa duyệt, chưa có role) sẽ bị ẩn → admin không duyệt được → **chặn flow đăng ký** |
| Filter có thể tận dụng `tabHas Role` (đã có index) | Cần subquery; `frappe.db.count` không filter xuyên child table |

### Phương án B — Có `imm_approval_status` set (Pending/Approved/Rejected)
"User AssetCore" = user nào đã đi qua flow đăng ký AssetCore (custom field được stamp).

| Ưu | Nhược |
|---|---|
| Vẽ đúng vòng đời đăng ký: Pending → Approved/Rejected | Custom field hiện default = `Pending` ⇒ mọi user (kể cả user ERPNext cũ) sẽ bị set Pending sau `bench migrate`? **Phải kiểm tra**: `_USER_CUSTOM_FIELDS` cài default `Pending` nhưng Frappe chỉ stamp default khi `Custom Field.default` được hiện thị ở form và user save; với user đã tồn tại, cột mới sẽ NULL → an toàn |
| Không cần touch role | Admin tạo user qua `create_system_user` → status = Approved (đã stamp) — OK |
| | Phải xác nhận: với user import qua Excel hoặc cấp lại — flow stamp đúng status chưa |

### Phương án C — Có `ac_department` set
"User AssetCore" = user được gán vào một AC Department.

| Ưu | Nhược |
|---|---|
| Đơn giản, query nhanh | KTV ngoài (Vendor Engineer), Super Admin… không thuộc khoa nào → bị ẩn |
| | Discriminator quá yếu, không khuyến nghị đứng một mình |

### Phương án D — Có `role_profile_name` thuộc "AssetCore — *"
"User AssetCore" = user được gán Role Profile bắt đầu bằng "AssetCore — " (seed bởi `_seed_role_profiles`).

| Ưu | Nhược |
|---|---|
| Rõ ràng về intent quản trị | User được gán role lẻ (không qua profile) sẽ bị ẩn |
| | Frappe cho phép gán role không qua profile → false negative cao |

### Phương án E — Bảng AssetCore membership riêng
Tạo DocType `AC App Member { user, status, joined_at, ... }` làm whitelist tường minh.

| Ưu | Nhược |
|---|---|
| Tách bạch nhất, không phụ thuộc role/department | Thêm 1 bảng + migration + UI quản lý — **overkill** với scope hiện tại |
| Hỗ trợ multi-tenant tốt hơn | Khả năng drift với role thực tế (user có role nhưng không có member) |

---

## 3. Khuyến nghị: **A ∪ B ∪ whitelist (Administrator)**

```
user thuộc AssetCore  ⇔
    name = 'Administrator'                          # Frappe siêu admin, luôn show
  ∨ EXISTS(Has Role WHERE parent=u.name
           AND role IN <Roles.ALL>)                  # A — có IMM role
  ∨ imm_approval_status IN ('Pending','Approved','Rejected')   # B — đã đi qua AssetCore signup
```

Lý do chọn A+B:
- **A một mình** ẩn user Pending → chặn admin duyệt đăng ký (regression nghiêm trọng).
- **B một mình** không bắt được user được tạo trực tiếp qua Frappe Admin UI rồi gán IMM role thủ công (custom field NULL).
- **Hợp A∪B** đảm bảo: vào bằng cửa nào cũng được nhận diện.
- **`Administrator`** đặc biệt vì xài chung với Frappe — nếu admin gỡ hết IMM role của Administrator để dọn cho chuẩn thì vẫn nên xuất hiện ở trang /user-profiles để khôi phục.

Không khuyến nghị C (quá yếu), D (false negative), E (overkill cho v1).

---

## 4. Tác động kỹ thuật

### 4.1 Backend — `assetcore/api/user.py`

#### 4.1.1 `list_users` (dòng 250)
Cần thêm bước resolve danh sách user-name "thuộc AssetCore" trước, rồi inject vào `filters["name"] = ["in", ...]`.

```python
def _resolve_ac_user_names() -> list[str]:
    """User được coi là thuộc AssetCore."""
    sql = """
        SELECT u.name FROM `tabUser` u
        WHERE u.user_type = 'System User' AND u.name != 'Guest'
        AND (
            u.name = 'Administrator'
            OR EXISTS (
                SELECT 1 FROM `tabHas Role` r
                WHERE r.parent = u.name
                  AND r.parenttype = 'User'
                  AND r.role IN %(roles)s
            )
            OR u.imm_approval_status IN ('Pending','Approved','Rejected')
        )
    """
    rows = frappe.db.sql(sql, {"roles": tuple(_IMM_ROLES)}, as_dict=True)
    return [r["name"] for r in rows]
```

Lưu ý:
- `_safe_field("imm_approval_status")` — nếu custom field chưa migrate, query sẽ vỡ. Phải kiểm tra trước khi dùng OR clause B.
- Conflict với filter `role=` hiện hữu: cả hai cùng set `filters["name"]` ⇒ phải **intersect**, không overwrite. Cách an toàn: resolve cả hai rồi `set & set`.
- Pagination: `total = frappe.db.count(...)` vẫn đúng vì `filters["name"] = ["in", list]` áp dụng cho cả count lẫn get_all.

#### 4.1.2 `list_frappe_users` (dòng 801)
Endpoint autocomplete — cùng vấn đề. Phải áp **cùng** rule resolve, nếu không SmartSelect User-link sẽ vẫn xổ ra `buihoangviet`.

#### 4.1.3 `create_system_user` (dòng 569)
Đang stamp `imm_approval_status = "Approved"` qua `_stamp_imm_approval` (dòng 549) → user mới tự động lọt qua filter B ✅. Không cần đổi.

⚠️ **Nhưng** nếu admin tạo user mà không tick bất kỳ IMM role nào, user xuất hiện ở /user-profiles do filter B match — nhưng user đó **không có role** → vào hệ thống không làm được gì. Đề xuất: ép default role `AssetCore System User` khi `imm_roles` rỗng.

#### 4.1.4 Import / wizard
`UserProfileListView.vue` import qua `previewRefImport('User', ...)`. Template hiện không bắt buộc cột `imm_approval_status` — sau import user **không có status** → biến mất khỏi list. Phải:
- Hoặc: post-process import auto-stamp `imm_approval_status = "Approved"` + ép `AssetCore System User` role nếu không có IMM role nào.
- Hoặc: thêm cột bắt buộc trong template.

→ Khuyến nghị **auto-stamp** (UX tốt hơn, ít bug user-error hơn).

### 4.2 Frontend
- Header total count sẽ giảm — đảm bảo subtitle `Tổng ${total}` phản ánh đúng "tổng user AssetCore", không phải tổng site. Có thể đổi subtitle thành "Tổng X người dùng AssetCore".
- Empty state: site mới migrate chưa seed user nào có IMM role → trang trống. Cần message thân thiện: "Chưa có người dùng AssetCore — nhấn Thêm để tạo hoặc Import."
- SmartSelect dùng `doctype="User"` ở các form khác: phải đổi sang dùng `list_frappe_users` (đã filter) thay vì query Frappe core trực tiếp. Đây là **work item phụ**, scope rộng — cần audit toàn bộ FE.

### 4.3 Migration / Data
- Site hiện tại có thể có user đã được tạo nhưng chưa stamp `imm_approval_status` và cũng chưa có IMM role (legacy). Sau khi áp filter mới, các user này biến mất. Cần **patch one-shot**:
  - Với mỗi user có ≥1 IMM role nhưng `imm_approval_status` NULL → set Approved.
  - Với `Administrator` → đảm bảo có role `AssetCore Super Admin` để khỏi rơi vào nhánh whitelist.
- Patch nên đặt ở `assetcore/patches/v0_0_X_backfill_ac_membership.py` và thêm vào `patches.txt`.

### 4.4 RBAC / quyền truy cập
- `list_users` hiện không gate (`@frappe.whitelist()` không yêu cầu role). Phải kiểm tra: vendor/non-admin có gọi được không? — Nếu có, phải gate `rbac.require("data.admin")` hoặc role tier tương ứng. **Out of scope** task này nhưng nên flag.

### 4.5 Test impact
- Unit test `tests/api/test_user.py` (nếu có) — phải cập nhật fixture: tạo user Frappe trần (không IMM role) để verify bị filter ra.
- E2E Playwright: kịch bản "tạo user mới" → verify xuất hiện trong list; "tạo user Frappe trực tiếp" → verify KHÔNG xuất hiện.

---

## 5. Edge cases & rủi ro

| # | Tình huống | Tác động | Mitigation |
|---|---|---|---|
| 1 | Admin gỡ hết IMM role của một user "cũ" (đã rời tổ chức) | User biến mất khỏi /user-profiles nhưng vẫn có lịch sử audit trail | Vẫn cho phép **xem profile** qua URL trực tiếp `/user-profiles/:name` ngay cả khi không trong list — `get_user_info` đã không gate điều kiện này, OK. |
| 2 | Frappe `System Manager` (không có IMM role) | Bị ẩn → admin Frappe gốc không thấy chính mình | Khuyến nghị migration patch tự động thêm `AssetCore Super Admin` cho mọi user `System Manager` hiện hữu. |
| 3 | Custom field `imm_approval_status` chưa migrate (site mới) | Query OR clause vỡ vì cột không tồn tại | `_safe_field` guard — nếu cột không có, fallback chỉ điều kiện A + whitelist Administrator. |
| 4 | Performance: subquery EXISTS trên `tabHas Role` cho mỗi user | Site có 10k user → chậm? | `tabHas Role` đã có index trên `parent`. Với scale dự kiến (vài trăm user/site) không vấn đề. Nếu cần, materialize qua view sau. |
| 5 | Pending user xuất hiện trong autocomplete `list_frappe_users` | Assignee picker hiển thị cả user chưa kích hoạt — gán việc cho người không login được | Filter B nên loại Pending khỏi `list_frappe_users` (chỉ Approved) trong khi /user-profiles vẫn show cả Pending để duyệt. → **2 hàm resolve khác nhau**: `_ac_users_for_admin()` vs `_ac_users_for_picker()`. |
| 6 | User được tạo qua API/CLI Frappe core (bypass `create_system_user`) | Không stamp custom field, không gán role → biến mất | Hành vi mong muốn. Nếu admin muốn nhập, dùng Import wizard hoặc gán role thủ công. |
| 7 | Multi-tenant: cùng site phục vụ nhiều bệnh viện | Filter chỉ tách AssetCore vs non-AssetCore, không tách giữa các tenant AssetCore | Nằm ngoài scope. Đã có `ac_department` + RBAC để xử lý visibility cross-tenant. |
| 8 | Import wizard sai role string → user import xong không stamp role | Vẫn ẩn vì không pass filter A | Validation pre-import phải reject; post-process auto-stamp `AssetCore System User` như section 4.1.4. |
| 9 | Filter "Vai trò" sau khi áp filter chính | Combine 2 điều kiện `name IN (...)` — phải **intersect** thay vì overwrite | Đã ghi chú ở §4.1.1. |
| 10 | Total count vs page items mismatch | Người dùng đếm tay không khớp `total` | Cùng filter dict cho cả `count` và `get_all` → đã đảm bảo. |

---

## 6. Plan triển khai (đề xuất, không bắt đầu code)

1. **Confirm rule với BA**: chốt A∪B∪Administrator. (Mục §3)
2. **BE — helper resolver**: viết `_resolve_ac_user_names()` trong `api/user.py`, có test riêng.
3. **BE — list_users**: inject resolver, **intersect** với filter `role=` hiện hữu.
4. **BE — list_frappe_users**: dùng resolver bản "chỉ Approved" (loại Pending).
5. **BE — create_system_user**: ép default role `AssetCore System User` nếu `imm_roles` rỗng.
6. **BE — import postprocess**: auto-stamp `imm_approval_status=Approved` + default role nếu thiếu.
7. **Patch one-shot**: stamp Approved cho legacy user có IMM role nhưng null status; gán `AssetCore Super Admin` cho System Manager.
8. **FE — UserProfileListView**: subtitle "Tổng X người dùng AssetCore"; cập nhật empty state.
9. **FE — audit SmartSelect User**: đổi mọi `doctype="User"` dùng `list_frappe_users` thay vì query Frappe gốc. (Có thể tách PR riêng do scope rộng.)
10. **Test**:
    - Unit: filter A, B, whitelist Administrator; intersect với `role=` param.
    - Integration: tạo user non-AC qua Frappe core → không xuất hiện; tạo qua AC → xuất hiện.
    - Manual Playwright: trang /user-profiles với site có cả ERPNext user.

---

## 7. Câu hỏi cần BA / PM chốt trước khi code

1. **Pending user** có hiển thị trong autocomplete (assignee, approver) hay không? — Đề xuất: **không**, chỉ trong /user-profiles để admin duyệt.
2. **Administrator** có buộc phải có role `AssetCore Super Admin` không, hay vẫn cho whitelist cứng? — Đề xuất: migration tự gán role, không cần hardcode whitelist (sạch hơn).
3. Khi admin tạo user mới mà không tick role nào, có **tự gán** `AssetCore System User` không? — Đề xuất: **có** (UX tránh user mồ côi).
4. User đã rời tổ chức (gỡ hết role) — có **soft-delete** khỏi list hay vẫn show với badge "Đã ngừng"? — Đề xuất: chỉ ẩn khi `enabled=0` AND không có IMM role AND không có audit trail. Nhưng đơn giản nhất là **vẫn ẩn**; muốn xem thì /user-profiles/:name trực tiếp.
5. Có cần expose **toggle** "Hiển thị toàn bộ Frappe user" cho Super Admin để debug không? — Đề xuất: **không** ở v1; nếu cần thì dùng `/app/user` của Frappe Desk.

---

## 8. Tệp ảnh hưởng (checklist)

- `assetcore/api/user.py` — `list_users`, `list_frappe_users`, `create_system_user`
- `assetcore/services/users/import_postprocess.py` (nếu có) — auto-stamp
- `assetcore/patches/v0_0_X_backfill_ac_membership.py` (mới)
- `assetcore/patches.txt` — đăng ký patch
- `frontend/src/views/auth/UserProfileListView.vue` — subtitle, empty state
- `frontend/src/components/common/SmartSelect.vue` (audit usage cho doctype=User)
- `tests/api/test_user_list_filter.py` (mới)
- `docs/imm-00/0X_*.md` — cập nhật BA doc cho rule lọc

---

## 9. Phân tích sâu — Mọi nơi FE chọn User và nguy cơ "profile ≠ picker"

### 9.1 Bản đồ thực tế: 5 đường gọi User khác nhau trên FE

Sau khi quét toàn bộ `frontend/src`, AssetCore đang dùng **5 surface API rời rạc** để liệt kê / tìm User. Mỗi surface có filter riêng, được code rải rác qua nhiều thế hệ → không có "single source of truth".

| # | Surface | Endpoint thực sự gọi | Filter hiện tại | Nơi dùng | Rò rỉ? |
|---|---|---|---|---|---|
| **S1** | List view "Quản lý người dùng" | `assetcore.api.user.list_users` | `user_type='System User'`, `name!='Guest'` | `UserProfileListView.vue` | ✅ Leak — đây là bug user báo |
| **S2** | Autocomplete User dùng `api/user.ts::listFrappeUsers` | `assetcore.api.user.list_frappe_users` | `enabled=1`, `user_type!='Website User'` | (chưa thấy view nào gọi! ⚠️ endpoint mồ côi) | ✅ Leak |
| **S3** | **SmartSelect `doctype="User"`** — surface phổ biến NHẤT trong app | `assetcore.api.imm04.search_link` (qua `useMasterDataStore.fetchDoctype('User')`) | **Chỉ `enabled=1`** (config tại `imm04.py:132`) | ≥12 view: CommissioningCreate, PMWorkOrderCreate, CalibrationCreate, IncidentDetail (modal Acknowledge), StockMovementCreate, WarehouseDetail, WarehouseList, SessionDetail (modal enroll), DocumentRequestList, PmScheduleList, SlaPolicyList, ReferenceDataView | ✅ **Leak nặng nhất** — không cả filter `user_type` |
| **S4** | Trang `/admin/roles` — list user để gán role | `frappe.client.get_list` (raw Frappe API) doctype=User | `enabled=1`, `user_type!='Website User'` | `roleAdmin.ts::listUsers()` | ✅ Leak, **bypass mọi logic AC** |
| **S5** | Read-by-id để resolve label (không list) | `frappe.client.get_value` doctype=User, filters by name | Không filter (đọc theo PK) | NeedsRequestCreate (clinical_head label), ReferenceDataView (dept_head phone), nhiều nơi | ⚠️ Không leak list, nhưng **có thể trả label cho user non-AC** đã được lưu sẵn |

**Bằng chứng code**:

```python
# assetcore/services/imm04.py:132-137 — config _ALLOWED_SEARCH_DOCTYPES
"User": {
    "label_field": "full_name",
    "search_fields": ["name", "full_name", "email"],
    "filters": {"enabled": 1},     # ← chỉ filter enabled, không có user_type
    "extra_fields": ["full_name", "email"],
},
# Service body (imm04.py:890-894)
results = frappe.db.get_all(
    doctype, filters=filters, ...,
    ignore_permissions=True,        # ← bypass DocPerm trên User
)
```

→ `SmartSelect doctype="User"` ở mọi modal trong app đang xổ ra **Website User của Frappe** (ví dụ tài khoản portal của bệnh nhân, nếu site có module Healthcare), `buihoangviet` (HR), Administrator, và toàn bộ user app khác. Vendor isolation hoàn toàn KHÔNG được áp do `ignore_permissions=True`.

```typescript
// frontend/src/api/roleAdmin.ts:31-48 — /admin/roles trang quản trị
export async function listUsers(): Promise<SimpleUser[]> {
  const res = await api.get('/api/method/frappe.client.get_list', {
    params: {
      doctype: 'User',
      filters: JSON.stringify([
        ['enabled', '=', 1],
        ['user_type', '!=', 'Website User'],
      ]),
      ...
    },
  })
}
```

→ Trang gán role hoàn toàn KHÔNG biết khái niệm "AssetCore user", nên admin có thể gán `AssetCore Super Admin` cho `buihoangviet` — bypass mọi gate ở §3.

### 9.2 Vấn đề "profile ≠ picker" — kịch bản thực tế

Giả sử ta fix **chỉ** `list_users` (S1) theo rule §3, các surface khác giữ nguyên:

**Kịch bản A — Audit trail "ma"**
1. Admin mở /pm-work-orders/new.
2. Field "Người giám sát" → SmartSelect doctype="User" → đi qua **S3** → xổ ra `buihoangviet`.
3. Admin chọn `buihoangviet`, save.
4. PM WO record có `supervisor = buihoangviet`, audit Lifecycle Event ghi actor.
5. Admin sau đó vào /user-profiles tìm `buihoangviet` để xem họ là ai → **không có** (S1 đã filter ra).
6. Hệ quả: audit trail trỏ tới user **không tồn tại trong AssetCore**. Report SLA breach gửi mail → user phòng kế toán nhận mail confused.

**Kịch bản B — Stale FK sau khi siết quyền**
1. Admin tin tưởng filter mới ở /user-profiles, tiến hành "dọn dẹp" → revoke IMM role của `buihoangviet`, mong user đó bị loại khỏi mọi nơi.
2. `buihoangviet` biến mất khỏi /user-profiles ✅
3. Nhưng vẫn xuất hiện trong **mọi SmartSelect User** (S3 chỉ filter `enabled=1`).
4. Vẫn xuất hiện trong /admin/roles picker (S4) → admin khác có thể tích lại role → vòng lặp vô hạn.
5. Các record cũ có `assigned_to = buihoangviet` vẫn render label "Buihoangviet" nhờ S5 (`frappe.client.get_value` bypass mọi filter) — không lỗi UI, nhưng người dùng tưởng họ vẫn active.

**Kịch bản C — User mới tạo qua AssetCore không có trong picker**
Ngược chiều: admin tạo `nguyenvana@bv.vn` qua "Thêm người dùng" (`create_system_user`), gán role `Repair Manager`. User xuất hiện trong /user-profiles ✅. Nhưng vì `useMasterDataStore.fetchDoctype('User')` **cache 5 phút** (`CACHE_TTL_MS` ở `masterData.ts:35`), trong 5 phút đầu user mới sẽ **không** xuất hiện trong SmartSelect ở các trang khác. Admin tưởng tạo lỗi.

→ Đây không phải hậu quả của filter mới — đã tồn tại — nhưng minh họa thêm việc **decoupling giữa các surface gây divergence**.

### 9.3 Phân loại divergence

| Loại | Mô tả | Ví dụ surface |
|---|---|---|
| **D1 — Filter divergence** | Mỗi surface filter khác nhau ⇒ tập user khác nhau | S1 vs S3 vs S4 |
| **D2 — Cache divergence** | TTL khác nhau / không invalidate khi create/update | S3 (5 phút cache) vs S1 (no cache) |
| **D3 — Permission divergence** | Một số bypass DocPerm, một số không | S3 (`ignore_permissions=True`) vs S1 (default) |
| **D4 — Label divergence** | Cùng user, label hiển thị khác nhau | S3 `full_name` vs S5 (varies) vs S1 `full_name \|\| name` |
| **D5 — Schema divergence** | Field trả về khác nhau → FE phải normalize lại | S1 (`IMMUserListItem`) vs S3 (`MasterItem {id,name,desc}`) vs S4 (`{name, full_name}`) |

### 9.4 Cách tiếp cận đúng: **một endpoint resolver duy nhất**

Phải gộp **tất cả surface về một endpoint AssetCore**, gọi là canonical `list_ac_users()`, áp rule §3 nội bộ.

```
                ┌────────────────────────────────────────────────────────┐
                │  assetcore.api.user.search_ac_users                    │
                │  (canonical resolver — áp rule §3 ở một chỗ duy nhất)  │
                │  Args: query, exclude_pending, exclude_disabled,       │
                │        role_filter, page_length                        │
                │  Output: [{ name, label, full_name, email,             │
                │             status, roles_brief }]                     │
                └────────────────────────────────────────────────────────┘
                          ▲           ▲           ▲           ▲
                          │           │           │           │
                  ┌───────┴───┐ ┌─────┴─────┐ ┌───┴─────┐ ┌───┴────────────┐
                  │ S1 list   │ │ S3 Smart  │ │ S4 admin│ │ S2 (deprecate) │
                  │ /user-    │ │ Select    │ │ /roles  │ │ list_frappe_   │
                  │ profiles  │ │ doctype=  │ │ picker  │ │ users → alias  │
                  │           │ │ "User"    │ │         │ │ tới canonical  │
                  └───────────┘ └───────────┘ └─────────┘ └────────────────┘
```

**Quy tắc**:
1. **Một resolver** thực sự áp logic A∪B∪Administrator.
2. **Mọi surface khác** chỉ là wrapper với preset args (ví dụ admin/role-picker dùng `exclude_pending=True`).
3. **Cấm** `frappe.client.get_list`/`get_value` doctype=User ở FE — phải route hết qua resolver. Có thể enforce bằng ESLint custom rule hoặc grep CI.
4. **`search_link` ở `imm04`** phải bỏ entry `"User"` khỏi `_ALLOWED_SEARCH_DOCTYPES` — hoặc đổi service `_handle_user(...)` để chuyển hướng sang resolver. (Đề xuất: **bỏ hẳn**, FE đổi SmartSelect User sang gọi resolver trực tiếp).
5. Bỏ `ignore_permissions=True` khi đụng tới User. Hoặc thay bằng gate `rbac.require("data.read")` để vendor không enumerate được toàn bộ User.

### 9.5 Migration path cho mỗi surface

| Surface | Hành động | Ghi chú |
|---|---|---|
| **S1 list_users** | Áp resolver inline (đã ghi ở §4.1.1). | Public API contract giữ nguyên, chỉ siết tập kết quả. |
| **S2 list_frappe_users** | Alias sang `search_ac_users(exclude_pending=True)`. Đánh dấu `@deprecated` trong docstring; kế hoạch xóa ở v0.0.X+2 sau khi audit FE. | Giữ vì có thể có code/integration ngoài đang gọi. |
| **S3 SmartSelect User** | (a) Bỏ entry "User" khỏi `_ALLOWED_SEARCH_DOCTYPES` ở `services/imm04.py:132`. <br/>(b) Trong `stores/masterData.ts::fetchDoctype`, route nhánh `doctype==='User'` sang gọi `search_ac_users` thay vì `imm04.search_link`. <br/>(c) Map schema `{name, full_name, email}` → `MasterItem {id, name, description}`. | Đây là surface lớn nhất — sửa 1 chỗ ở store, 12+ view không cần đổi. |
| **S4 roleAdmin.listUsers** | Đổi gọi sang `search_ac_users(exclude_pending=True, page_length=0)`. Có thể giữ schema `SimpleUser` qua adapter. | Đảm bảo /admin/roles chỉ gán role được cho user AC. |
| **S5 frappe.client.get_value** | Thay bằng endpoint `get_ac_user_brief(name)` mới (label + status), không bypass filter ở read-by-id để vẫn fail-safe nếu name không thuộc AC. | Hoặc giữ — read-by-id ít tệ vì cần `name` rõ ràng. Không bắt buộc đổi v1. |

### 9.6 Edge case bổ sung (phát sinh từ §9.4)

| # | Tình huống | Tác động | Mitigation |
|---|---|---|---|
| 11 | Form đã save với `assigned_to = <user non-AC>` (legacy data) | Khi mở lại form, SmartSelect không resolve được label (user không trong tập filter) | SmartSelect fallback: nếu `modelValue` set mà cache không có → gọi `search_ac_users(query=modelValue, include_legacy=True)` để vẫn render label, kèm badge "không còn thuộc AssetCore". |
| 12 | Cache 5 phút của masterData store stale sau khi tạo user mới | User mới vắng mặt trong picker | Sau `create_system_user` thành công, FE gọi `masterDataStore.invalidate('User')`. (Pattern đã có cho doctype khác.) |
| 13 | Đường gọi raw `frappe.client.*` mới phát sinh trong tương lai | Lại divergence | CI rule: grep `frappe.client.get_list.*User` trong PR mới → fail. Hoặc bọc `frappeGet` wrapper từ chối doctype=User. |
| 14 | Cache cross-tenant: 2 user khác site dùng chung browser (dev) | masterData cache chứa user của site cũ | Đã handle qua đăng nhập lại — invalidate trong `auth` store `logout()`. Cần verify. |
| 15 | Permission gate ở resolver | Vendor Engineer gọi resolver → enumerate được user khác | Resolver phải áp `rbac.require("data.read")` HOẶC giới hạn return chỉ theo tenant/department của caller. Cần BA chốt: vendor được thấy user gì? Đề xuất: vendor **không** gọi được resolver — picker bị disable cho vendor. |
| 16 | `Has Role` lookup performance cho EVERY SmartSelect open | N+1 query, mỗi modal open = 1 lần resolver | Cache cùng `useMasterDataStore` (5 phút TTL hiện hữu). Resolver phải nhanh: 1 SQL với EXISTS, không loop. |

### 9.7 Tác động lên plan §6

Mở rộng plan §6 với các bước **trước khi** sửa S1:

| Bước (mới) | Hành động |
|---|---|
| 0a. | Viết resolver canonical `search_ac_users()` ở `api/user.py` + service `services/users/resolver.py` + unit test. |
| 0b. | Adapter từ resolver → `MasterItem` schema cho FE store. |
| 1. | (§6.1 cũ) Confirm rule A∪B∪Administrator. |
| 2. | S1: refactor `list_users` dùng resolver. |
| 3. | S3: bỏ "User" khỏi `_ALLOWED_SEARCH_DOCTYPES`; redirect `masterData.fetchDoctype('User')` → resolver. |
| 4. | S4: refactor `roleAdmin.ts::listUsers` → resolver. |
| 5. | S2: `list_frappe_users` thành alias deprecated. |
| 6. | S5 (tùy chọn): expose `get_ac_user_brief` riêng cho read-by-id. |
| 7. | FE audit: grep `doctype.*User` + `frappe.client.get_list` cho mọi nơi sót lại. |
| 8. | Cache invalidation hook: sau create/update/delete user. |
| 9. | (giữ nguyên các bước test/migration cũ.) |

### 9.8 Quyết định cần BA chốt (bổ sung §7)

6. **Vendor Engineer** có được mở picker User để chọn assignee không? — Đề xuất: **không** (vendor không assign cross-tenant).
7. Khi xem record cũ có `assigned_to = <user non-AC legacy>`, có hiển thị label hay show "**(deleted)**"? — Đề xuất: **vẫn show label**, kèm badge cảnh báo; không hỏi quyền.
8. Có cần endpoint `get_ac_user_brief` riêng cho mọi read-by-id, hay vẫn cho dùng `frappe.client.get_value`? — Đề xuất: **có endpoint riêng** để tránh tương lai lại drift; bỏ raw `get_value` cho doctype=User ở FE.
9. `search_link` của `imm04.py` đang lo cho 14+ doctype master data của toàn app — có nên tách `search_link` ra module riêng `services/shared/link_search.py` thay vì để trong `imm04`? — Đề xuất: **có**, nhưng tách riêng PR (technical debt, không block bug này).

### 9.9 Bài học rút ra (cho codebase)

1. **"Một khái niệm — một endpoint"**: domain "AssetCore user" phải có duy nhất 1 entry point ở BE. Mọi nơi cần list/search/lookup phải đi qua đó.
2. **Tránh `frappe.client.*` từ FE** với doctype có business rule (User, Asset, Work Order...). Frappe client API là raw, không biết business filter của app.
3. **`ignore_permissions=True`** ở service layer là một **dấu hiệu kỹ thuật nợ**: nó thường được thêm để "cho chạy" lúc dev, nhưng trở thành lỗ hổng khi multi-tenant/vendor isolation áp dụng.
4. **Cache TTL phải đi kèm invalidation hook**, không chỉ thời gian. Mỗi mutation chính (create user, role change) phải `invalidate('User')`.
5. **Audit FE bằng grep trước khi sửa BE**: mọi điểm chạm User ở FE phải được liệt kê trong PR description; reviewer mới biết "đã đi hết surface chưa".

---

## 10. Hướng phát triển: tầng FE thống nhất — composable `useAcUsers` + component `<UserPicker>`

Khái niệm cốt lõi mà user phát biểu:

> "Khi gọi user của 1 app thì đi qua 1 component hoặc hook chuyên xử lý. Đổi rule ở profile (vd không lấy user admin) thì mọi field FE cũng tự đồng bộ."

Đây chính là **single source of truth ở tầng FE**, đối xứng với resolver canonical ở BE (§9.4). Hai tầng cộng lại tạo thành ràng buộc cứng: không có đường ngách nào còn lại để leak.

### 10.1 Cấu trúc 2 lớp

```text
┌──────────────────────────────────────────────────────────────────┐
│ BE: assetcore.api.user.search_ac_users  (resolver canonical §9)  │
│     ↑ một nơi duy nhất áp rule A∪B∪Administrator                 │
└──────────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTP (TanStack Query)
                              │
┌──────────────────────────────────────────────────────────────────┐
│ FE composable: useAcUsers(opts)   ◄── BACKBONE — cache + types   │
│   - fetchAll / search / resolveById / invalidate                 │
│   - default opts ép theo context (assignee vs admin vs picker)   │
└──────────────────────────────────────────────────────────────────┘
            ▲                  ▲                      ▲
            │                  │                      │
   ┌────────┴───────┐  ┌───────┴────────┐  ┌──────────┴──────────┐
   │ <UserPicker/>  │  │ Admin list view│  │ Headless usage      │
   │ wrapper UI mặc │  │ UserProfileList│  │ (vd validate form,  │
   │ định cho 95%   │  │ View — riêng   │  │ bulk-action select) │
   │ form fields    │  │ vì cần field   │  │                     │
   │                │  │ admin-only     │  │                     │
   └────────────────┘  └────────────────┘  └─────────────────────┘
```

Quy tắc bất biến (enforce bằng lint):

1. **Không** view nào được gọi trực tiếp endpoint `search_ac_users` hay `list_users` — phải qua `useAcUsers`.
2. **Không** view nào được gọi `frappe.client.get_list` / `get_value` với `doctype: 'User'`.
3. **Không** view nào được dùng `SmartSelect doctype="User"`.
4. `<UserPicker>` là cách **mặc định**. Composable headless chỉ dùng khi cần custom UI thực sự (bulk select, validation logic).

### 10.2 Vì sao cần CẢ component + composable (không chỉ một)

| Lựa chọn | Ưu | Nhược |
| --- | --- | --- |
| Chỉ component `<UserPicker>` | Dev kéo thả nhanh; UI consistent toàn app | Khi cần list trong modal đa-chọn, bulk action, validation logic, sidebar autocomplete... bị khoá UI |
| Chỉ composable `useAcUsers()` | Linh hoạt, dùng được mọi UI; testable | Mỗi nơi tự build UI → vẫn drift về visual/UX. Junior dev có thể render thiếu badge "Pending", thiếu loading state |
| **Cả hai (đề xuất)** | Component cover 95% case → UI đồng nhất; composable cover edge case còn lại; cùng share 1 cache layer | Code base lớn hơn ~200 LOC một lần; lợi nhuận dài hạn lớn |

→ Composable là **lớp logic**, component là **lớp UI**. Component nội bộ gọi composable. Đổi rule chỉ chạm composable + BE.

### 10.3 API contract đề xuất

**Composable** (`frontend/src/composables/useAcUsers.ts`):

```typescript
export interface AcUserOption {
  name: string                  // email/username — primary key
  full_name: string
  email: string
  user_image?: string
  imm_approval_status: 'Approved' | 'Pending' | 'Rejected' | null
  roles_brief: string[]         // top 2-3 IMM role để render badge
  department_name?: string
  is_legacy?: boolean           // true khi user đã rời AC nhưng vẫn được resolve cho stale FK
}

export interface UseAcUsersOptions {
  /** Loại Pending — dùng cho picker assignee (mặc định: false ở list admin, true ở picker form) */
  excludePending?: boolean
  /** Loại disabled (enabled=0). Mặc định: true */
  excludeDisabled?: boolean
  /** Loại tên cụ thể — vd ['Administrator'] để ẩn siêu admin ở picker */
  excludeNames?: string[]
  /** Yêu cầu user có ≥1 role thuộc danh sách này */
  withRole?: string | string[]
  /** Lọc theo AC Department */
  withDepartment?: string
  /** Cho phép resolveById trả về user "ngoài AC" để render label legacy */
  includeLegacyForResolve?: boolean
}

export function useAcUsers(opts: UseAcUsersOptions = {}) {
  // TanStack Query — cache key = ['ac-users', JSON.stringify(opts)]
  return {
    users:        ComputedRef<AcUserOption[]>,
    loading:      ComputedRef<boolean>,
    error:        ComputedRef<Error | null>,
    refetch:      () => Promise<void>,
    /** Server-side search, không phụ thuộc list đã cache (cho >500 user) */
    search:       (query: string) => Promise<AcUserOption[]>,
    /** Resolve label cho 1 user-id — tự fallback `includeLegacy` nếu không thấy trong tập filter */
    resolveById:  (name: string) => Promise<AcUserOption | null>,
    /** Invalidate cache sau mutation (create user, role change, approve/reject) */
    invalidate:   () => void,
  }
}
```

**Component** (`frontend/src/components/common/UserPicker.vue`):

```vue
<UserPicker
  v-model="form.supervisor"
  placeholder="Chọn người giám sát..."
  :exclude-pending="true"
  :exclude-names="['Administrator']"
  :with-role="['Repair Manager', 'Repair User']"
  show-role-badge
  show-approval-badge
  required
  :error="errors.supervisor"
  @select="onSupervisorSelected"
/>
```

Internals của `<UserPicker>`:

- Gọi `useAcUsers(propsAsOpts)` → lấy `users`, `loading`, `search`, `resolveById`.
- UI base tận dụng `SmartSelect` hiện có nhưng đổi nguồn dữ liệu (không qua masterData store nữa).
- Tự render badge role (chip màu theo `ROLE_GROUP_COLORS` đã có), badge "Pending" khi `excludePending=false`.
- Khi `modelValue` không có trong `users` → fallback `resolveById(value, includeLegacy=true)` → render label + badge "(Đã rời AssetCore)".

### 10.4 Kịch bản "đổi rule ở 1 chỗ" — minh chứng

Yêu cầu user: "ở profile tôi muốn không lấy user admin nữa".

**Trước khi có 2 lớp**: phải sờ vào 5 nơi (S1–S5 §9.1), mỗi nơi cú pháp filter khác nhau, có khả năng sót.

**Sau khi có 2 lớp**, chỉ 1 trong 2 cách dưới — KHÔNG đụng view nào:

- **Cách A (default toàn app)**: chỉnh resolver BE: thêm `exclude_super_admin=True` làm default → cả 12+ view + admin page + role picker đều tự cập nhật sau refresh.
- **Cách B (theo context)**: chỉnh `useAcUsers` defaults: `excludeNames: ['Administrator']` cho mode "picker", giữ nguyên mode "admin-list" → /user-profiles vẫn thấy Administrator để khôi phục, nhưng mọi form khác đều ẩn.

Đây là khác biệt rõ rệt so với hiện trạng: code change scope từ **~15 file** xuống **1–2 file**.

### 10.5 Cơ chế enforce — không để dev sau lại drift

Tạo single source of truth chỉ có giá trị nếu **không thể bypass**. 4 lớp phòng thủ:

| Lớp | Cơ chế | Vi phạm bị bắt khi nào |
| --- | --- | --- |
| L1 — Static lint | ESLint custom rule (`no-raw-user-link`): cấm `doctype: ['"]User['"]`, `frappe.client.get_list.*User`, `frappe.client.get_value.*User`. | Lúc viết code, IDE highlight đỏ |
| L2 — CI grep | GitHub Action grep regex như trên trong PR diff, fail check. | Trước khi merge |
| L3 — Type system | Bỏ entry `'User'` khỏi `DocType` union của `SmartSelect`/`masterData`. Code dùng cũ → TS compile error. | `npm run build` / `tsc --noEmit` |
| L4 — BE gate | Bỏ entry `"User"` khỏi `_ALLOWED_SEARCH_DOCTYPES` của `imm04.search_link` (§9.5 S3). | Runtime — request bị 403 |

L1 + L3 là phòng tuyến chính cho dev mới (bị chặn ngay khi viết). L2 là safety net cho code copy-paste qua nhiều file. L4 là phòng tuyến cuối — kể cả vô tình bypass FE thì BE vẫn từ chối.

### 10.6 Cache & invalidation — mảnh ghép quan trọng để tránh phân kỳ runtime

Hiện trạng (§9.3 D2): masterData store cache 5 phút **không invalidate** sau mutation → user mới vắng mặt 5 phút.

Với `useAcUsers` (TanStack Query):

- Cache key chuẩn: `['ac-users', JSON(opts)]` + `['ac-user', name]` cho resolveById.
- Mọi mutation phải khai báo invalidate:
  - `createSystemUser` → `invalidateQueries(['ac-users'])`
  - `updateUserRoles` / `setUserRoles` → `invalidateQueries(['ac-users']), invalidateQueries(['ac-user', user])`
  - `approveRegistration` → cùng
  - `updateUserInfo` → invalidate user cụ thể
- Module gọi mutation phải dùng wrapper `useAcUserMutation()` đã gắn sẵn invalidate, không tự gọi `api.post` thô.

→ Sau khi tạo user, picker ở mọi form **cập nhật ngay** (≤1 giây), không phải đợi 5 phút.

### 10.7 Phân tích các mặt — không né tránh điểm yếu

#### Lợi ích (kỳ vọng)

1. **Đồng bộ tuyệt đối**: profile = picker theo định nghĩa. Rule change → mọi nơi cập nhật.
2. **Bảo mật**: bypass `ignore_permissions=True` ở `search_link` (§9 lesson 3). Vendor không enumerate được user toàn site.
3. **Code base nhỏ hơn**: 12+ chỗ filter rời được gom về 1. Removed code > added code sau migration.
4. **Developer experience**: code mới chỉ cần `<UserPicker v-model="..." />` — không cần nhớ filter nào, prop nào.
5. **Test surface giảm**: thay vì test 5 endpoint, test 1 composable + 1 resolver.

#### Rủi ro / chi phí

1. **Migration risk**: 12+ view cần đổi từ `SmartSelect doctype="User"` → `<UserPicker>`. Một số view có prop riêng (filters cascade theo `with-role`) — không có mapping 1-1 hoàn hảo. Cần kiểm tra từng view.
2. **Refactor 1 lần lớn**: nên tách thành PR theo wave (Wave 1: BE resolver + composable + component, Wave 2: migrate IMM-04/05/06 views, Wave 3: migrate IMM-08/09/11/12, Wave 4: IMM-15/16 + admin pages, Wave 5: cleanup S2/S3/S4/S5 endpoint).
3. **Storybook / dev mock**: composable phụ thuộc HTTP — Storybook cần inject mock adapter. Pattern `provide('acUsersAdapter', mockAdapter)` để swap trong tests/stories.
4. **Người dùng cũ (legacy data)**: form record cũ chứa user non-AC — cần `resolveById({includeLegacy: true})` + badge. Nếu bỏ qua, label rỗng → confusing.
5. **Frappe Desk forms**: user vẫn vào `/app/...` của Frappe Desk thì field assigned_to gốc của Frappe vẫn xổ ra mọi User. Out of scope, nhưng cần document rõ "AssetCore FE app khác Frappe Desk" để khách hàng không hỏi.
6. **TanStack Query đã cài chưa?**: CLAUDE.md §15 ghi có, nhưng cần verify version (cache key format khác giữa v4 và v5).

#### Khi nào KHÔNG nên dùng pattern này

- Doctype không có business rule phức tạp (vd AC Spare Part) — SmartSelect + search_link đã đủ. Pattern composable+component chỉ áp dụng cho doctype có **rule lọc business + cần cập nhật runtime**: User (chắc chắn), Asset (có thể), Vendor (nếu multi-tenant).
- Surface chỉ dùng 1 lần (vd report config) — không bõ công wrap.

#### So với resolver-only (không có FE wrapper)

Nếu chỉ làm BE resolver ở §9 (không có FE wrapper):

- Dev mới vẫn có thể gọi `frappe.client.get_list doctype=User` raw → leak.
- Dev quên prop default → field thiếu `excludePending` → leak Pending vào picker.

→ Resolver-only là **giải pháp một nửa**. Có FE wrapper mới đạt **single source of truth** thật sự.

### 10.8 Cập nhật plan triển khai

Bổ sung vào §6:

| Bước | Hành động | Ghi chú |
| --- | --- | --- |
| 0a | BE: viết resolver canonical `search_ac_users` + service + unit test | §9 |
| 0b | BE: bỏ entry `"User"` khỏi `_ALLOWED_SEARCH_DOCTYPES` (`imm04.py`) | §9 |
| **0c** | **FE: viết `useAcUsers.ts` composable + types + TanStack Query wiring** | **MỚI** |
| **0d** | **FE: viết `<UserPicker>` component + Storybook story** | **MỚI** |
| **0e** | **FE: thêm ESLint custom rule `no-raw-user-link`** | **MỚI** — chạy --fix báo cáo violations sẵn có |
| **0f** | **FE: bỏ `'User'` khỏi `DocType` union của SmartSelect & masterData → TS error chỉ ra mọi nơi vi phạm** | **MỚI** — bản đồ refactor tự sinh |
| 1 | Confirm rule A∪B∪Administrator với BA | §3 |
| 2 | S1: refactor `list_users` BE dùng resolver | §4 |
| 3 | FE migrate Wave 1 — IMM-04/05/06 views (CommissioningCreate, ReferenceData...) sang `<UserPicker>` | follow TS errors từ 0f |
| 4 | FE migrate Wave 2 — IMM-08/09/11/12 (PMWO, Calibration, Incident...) | |
| 5 | FE migrate Wave 3 — IMM-15/16 (Warehouse, StockMovement, SLA, Document Request) | |
| 6 | FE: `roleAdmin.ts::listUsers` → composable; UserProfileListView giữ admin-mode composable variant | |
| 7 | BE: `list_frappe_users` deprecate, alias sang resolver | §9 |
| 8 | Cache invalidation hooks vào mọi user mutation (create/update/role) | §10.6 |
| 9 | Patch one-shot data + tests (như §6 cũ) | |

### 10.9 File ảnh hưởng (gộp & cập nhật từ §8)

**Tạo mới**:

- `frontend/src/composables/useAcUsers.ts`
- `frontend/src/composables/useAcUserMutation.ts` (wrapper invalidate)
- `frontend/src/components/common/UserPicker.vue`
- `frontend/src/components/common/UserPicker.stories.ts` (Storybook nếu có)
- `frontend/eslint-rules/no-raw-user-link.js`
- `assetcore/api/user.py::search_ac_users` (resolver canonical)
- `assetcore/services/users/resolver.py`
- `assetcore/patches/v0_0_X_backfill_ac_membership.py`
- `tests/api/test_search_ac_users.py`
- `tests/frontend/useAcUsers.spec.ts`

**Sửa**:

- `assetcore/api/user.py` — `list_users`, `list_frappe_users` route qua resolver
- `assetcore/services/imm04.py` — bỏ entry `"User"` khỏi `_ALLOWED_SEARCH_DOCTYPES`
- `frontend/src/stores/masterData.ts` — bỏ `'User'` khỏi `DocType` union
- `frontend/src/components/common/SmartSelect.vue` — bỏ `'User'` khỏi `DocType` union
- `frontend/src/api/roleAdmin.ts` — `listUsers` route qua composable
- `frontend/src/views/auth/UserProfileListView.vue` — subtitle + empty state
- `frontend/.eslintrc` — đăng ký rule custom

**Migrate (~12 file)**:

- `frontend/src/views/commissioning/CommissioningCreateView.vue` (3 SmartSelect User)
- `frontend/src/views/training/SessionDetailView.vue`
- `frontend/src/views/inventory/WarehouseDetailView.vue`
- `frontend/src/views/inventory/StockMovementCreateView.vue` (2 chỗ)
- `frontend/src/views/inventory/WarehouseListView.vue`
- `frontend/src/views/pm/PMWorkOrderCreateView.vue`
- `frontend/src/views/pm/PmScheduleListView.vue`
- `frontend/src/views/document/DocumentRequestListView.vue`
- `frontend/src/views/master-data/SlaPolicyListView.vue` (2 chỗ)
- `frontend/src/views/master-data/ReferenceDataView.vue` (2 chỗ — bao gồm read-by-id fetchUserMobile)
- `frontend/src/views/calibration/CalibrationCreateView.vue`
- `frontend/src/views/incident/IncidentDetailView.vue`
- `frontend/src/views/needs/NeedsRequestCreateView.vue` (read-by-id clinical_head)

### 10.10 Câu hỏi BA bổ sung (gộp với §7 / §9.8)

10. Có chấp nhận **migrate ~12 view** trong cùng release, hay tách thành 3 wave nhỏ (rủi ro thấp hơn nhưng dài hơn)? Đề xuất: **3 wave** theo module group (IMM-04/05/06, IMM-08/09/11/12, IMM-15/16), mỗi wave 1 PR.
11. Có sẵn sàng đầu tư **ESLint custom rule + CI grep** không, hay chỉ enforce qua TS type? Đề xuất: cả hai — TS bắt 95%, ESLint+CI bắt 5% còn lại (vd dynamic doctype string).
12. Storybook đã có trong frontend chưa? Nếu chưa, có cần thêm cho `<UserPicker>` không? Đề xuất: **không bắt buộc** nếu chưa có; viết unit test composable thay thế.

### 10.11 Tóm lược một dòng

> Fix bug "/user-profiles leak Frappe user" mà không kèm tầng FE `useAcUsers + <UserPicker>` thì 6 tháng sau dev mới sẽ tái phát bug ở 1 trong 12 view. Tầng FE là **rào chắn cấu trúc**, không phải lớp UX trang trí.
