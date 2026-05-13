# AssetCore — Thiết kế Hệ thống Tài khoản & Phân quyền

**Ngày:** 2026-04-20
**Phạm vi:** Audit hiện trạng + Thiết kế luồng tài khoản Frontend (Vue 3) kế thừa core Frappe/ERPNext.
**Ràng buộc:** Không thay đổi schema DocType `User` của core Frappe. Thông tin nghiệp vụ đi qua custom DocType `AC User Profile` (đã có).

---

## 1. Hiện trạng (Audit)

### 1.1 Backend — đã có

| Thành phần | Vị trí | Trạng thái |
|---|---|---|
| 8 IMM Roles (System Admin, QA Officer, Department Head, Operations Manager, Workshop Lead, Technician, Document Officer, Storekeeper) | `hooks.py` → fixtures `Role` | ✅ |
| `AC User Profile` DocType (link 1-1 với User qua `autoname: field:user`) | `assetcore/doctype/ac_user_profile/ac_user_profile.json` | ✅ |
| Controller `ACUserProfile` — validate IMM roles + auto-sync `imm_roles` → User.roles qua `_sync_roles_to_user` | `ac_user_profile.py` | ✅ |
| Child tables: `AC User Role`, `AC User Certification` | `doctype/ac_user_role/`, `doctype/ac_user_certification/` | ✅ |
| API `list_profiles / get_profile / upsert_profile / get_my_profile / get_available_imm_roles` | `api/user_profile.py` | ✅ (admin/self-read) |
| Helpers `_ok`, `_err`, `_get_role_emails` | `utils/helpers.py` | ✅ |

### 1.2 Backend — thiếu

| Thành phần | Mô tả |
|---|---|
| `api/auth.py` | Endpoint đăng ký tự phục vụ + lấy profile đăng nhập (hiện chỉ có `get_my_profile` — cần bổ sung `register_user`) |
| Role `IMM Clinical User` | Bác sĩ / điều dưỡng khoa lâm sàng (xem thiết bị, báo sự cố — không thao tác WO) |
| Luồng duyệt đăng ký | `enabled=0` → admin duyệt → `enabled=1` + gán role |
| Trường `approval_status` trên `AC User Profile` | Tracking `Pending / Approved / Rejected` |

### 1.3 Frontend — đã có

| Thành phần | Vị trí | Trạng thái |
|---|---|---|
| Pinia `useAuthStore` — login/logout/fetchSession + role helpers (`hasRole`, `hasAnyRole`, `canCreate`, `canSubmit`, `canApprove`) | `stores/auth.ts` | ✅ |
| Persisted session (30 phút TTL) | `stores/auth.ts:131-147` | ✅ |
| `LoginView.vue` | `views/LoginView.vue` | ✅ |
| Router guards `requiresAuth` + `requiredRoles` meta | `router/index.ts:469-494` | ✅ |
| Admin CRUD profile (`UserProfileListView`, `UserProfileFormView`) | `views/` | ✅ |
| `FrappeUser` type | `types/imm04.ts` | ✅ |

### 1.4 Frontend — thiếu

| Thành phần | Mô tả |
|---|---|
| `RegisterView.vue` | Form đăng ký tự phục vụ (tiếng Việt) |
| `ProfileView.vue` | Trang hồ sơ người dùng đã đăng nhập (xem + sửa thông tin cá nhân) |
| `v-permission` directive | Ẩn/hiện UI element theo role |
| Route `/register`, `/profile`, `/unauthorized` | Chưa khai báo |

---

## 2. Kiến trúc Liên kết Data

### 2.1 Sơ đồ

```
┌─────────────────────┐   1:1    ┌──────────────────────┐   N:1    ┌───────────────────┐
│  User (core Frappe) │──────────│  AC User Profile     │──────────│  AC Department    │
│  - name (email)     │  autoname│  - user (link)       │  link    │  (khoa / phòng)   │
│  - full_name        │  field:  │  - employee_code     │          └───────────────────┘
│  - enabled          │   user   │  - job_title, phone  │   N:1    ┌───────────────────┐
│  - roles (child)    │          │  - department        │──────────│  AC Location      │
└─────────────────────┘          │  - location          │  link    └───────────────────┘
          │                      │  - is_active         │
          │ N:N qua child table  │  - approval_status◄──┼── NEW
          ▼                      │  - imm_roles (child) │   pending / approved / rejected
┌─────────────────────┐          │  - certifications    │
│  Role (core Frappe) │          └──────────────────────┘
│  - IMM System Admin │                    │
│  - IMM QA Officer   │   sync on save     │
│  - IMM Dept Head    │◄───────────────────┘
│  - IMM Ops Manager  │   (imm_roles → User.roles)
│  - IMM Workshop Lead│
│  - IMM Technician   │
│  - IMM Doc Officer  │
│  - IMM Storekeeper  │
│  - IMM Clinical User│◄── NEW (bác sĩ / điều dưỡng)
└─────────────────────┘
```

**Nguyên tắc:**
- Authentication (đăng nhập, password, session) → **luôn đi qua `User` core**, không đụng schema.
- Authorization (quyền thao tác) → **dựa trên `User.roles`** (có sẵn từ Frappe).
- Nghiệp vụ HTM (khoa, mã nhân viên, chứng chỉ, job title) → **nằm trên `AC User Profile`**.
- `AC User Profile.imm_roles` là source-of-truth cho IMM roles; controller tự sync sang `User.roles` khi save (đã triển khai tại `ac_user_profile.py::_sync_roles_to_user`).

### 2.2 Bảng ánh xạ Role

| Role (Frappe) | Scope nghiệp vụ | Quyền chính | Có thể tự đăng ký? |
|---|---|---|---|
| `IMM System Admin` | Quản trị hệ thống | CRUD tất cả; duyệt user; cấu hình | ❌ (admin cấp) |
| `IMM Operations Manager` | Điều hành vận hành | Tạo WO, duyệt commissioning, CAPA | ❌ (admin cấp) |
| `IMM Department Head` | Trưởng khoa | Duyệt commissioning của khoa; xem KPI khoa | ❌ (admin cấp) |
| `IMM QA Officer` | Đảm bảo chất lượng | Tạo CAPA, duyệt tài liệu, audit | ❌ (admin cấp) |
| `IMM Workshop Lead` | Trưởng tổ KT | Phân công WO, duyệt PM/CM trong tổ | ❌ (admin cấp) |
| `IMM Technician` | Kỹ thuật viên | Thực hiện WO, cập nhật kết quả | ✅ (self-signup) |
| `IMM Document Officer` | Quản lý hồ sơ | CRUD IMM-05 documents | ❌ (admin cấp) |
| `IMM Storekeeper` | Thủ kho | Xuất/nhập spare parts | ❌ (admin cấp) |
| **`IMM Clinical User`** (mới) | Nhân viên lâm sàng | Xem thiết bị khoa mình; báo sự cố; không thao tác WO | ✅ (self-signup) |

**Luồng gán role:**
1. Self-signup → mặc định nhận role rỗng + `approval_status=Pending` + `User.enabled=0`.
2. Admin (`IMM System Admin` hoặc `IMM Operations Manager`) mở profile, chọn role phù hợp → save → controller sync sang `User.roles` + `User.enabled=1`.

---

## 3. Luồng Đăng ký — Duyệt

```
┌─────────┐               ┌──────────────┐              ┌─────────────────┐
│  User   │               │ FE (Vue 3)   │              │ BE (Frappe)     │
└────┬────┘               └──────┬───────┘              └────────┬────────┘
     │  Mở /register             │                               │
     │─────────────────────────► │                               │
     │                           │                               │
     │  Nhập: họ tên, email,     │                               │
     │  mật khẩu, SĐT,           │                               │
     │  khoa phòng, mã NV        │                               │
     │─────────────────────────► │                               │
     │                           │  POST /api/method/            │
     │                           │  assetcore.api.auth.          │
     │                           │  register_user                │
     │                           │──────────────────────────────►│
     │                           │                               │ (1) frappe.new_doc("User")
     │                           │                               │     enabled=0, send_welcome_email=0
     │                           │                               │ (2) frappe.new_doc("AC User Profile")
     │                           │                               │     approval_status=Pending
     │                           │                               │ (3) notify_admins()
     │                           │  200 { success, pending: true}│
     │                           │◄──────────────────────────────│
     │  Hiển thị "Đăng ký thành  │                               │
     │  công — chờ admin duyệt"  │                               │
     │◄───────────────────────── │                               │
     │                           │                               │
     │  ─────────────── chờ admin duyệt ──────────────────       │
     │                           │                               │
     │                           │                               │ Admin mở UserProfileForm
     │                           │                               │ Gán role + save → enabled=1
     │                           │                               │
     │  Thử đăng nhập            │                               │
     │─────────────────────────► │  POST /api/method/login       │
     │                           │──────────────────────────────►│
     │                           │  Session cookie + CSRF        │
     │                           │◄──────────────────────────────│
     │                           │  GET get_current_session      │
     │                           │  + get_my_profile             │
     │                           │──────────────────────────────►│
     │                           │  user + roles + profile       │
     │                           │◄──────────────────────────────│
     │  Vào /dashboard           │                               │
     │◄───────────────────────── │                               │
```

**Bảo mật:**
- Endpoint `register_user` khai báo `allow_guest=True` (self-signup).
- Rate limit: 5 lần/phút/IP (dùng `frappe.rate_limiter`).
- Password chịu rule của Frappe (`enable_password_policy`).
- `enabled=0` đảm bảo user chưa duyệt không login được.
- Admin nhận email thông báo (dùng `_get_role_emails("IMM System Admin")`).

---

## 4. API Contracts — `api/auth.py`

### 4.1 `register_user`

**Method:** `POST /api/method/assetcore.api.auth.register_user`
**Auth:** `allow_guest=True`
**Body:**
```json
{
  "email": "bs.an@bv.vn",
  "full_name": "Nguyễn Văn An",
  "password": "SecurePass123!",
  "phone": "0912345678",
  "department": "AC-DEPT-ICU",
  "employee_code": "NV-0123",
  "job_title": "Bác sĩ nội trú"
}
```
**Response — success:**
```json
{
  "success": true,
  "data": {
    "user": "bs.an@bv.vn",
    "profile": "bs.an@bv.vn",
    "pending_approval": true
  }
}
```
**Response — error:**
```json
{ "success": false, "error": "Email đã tồn tại", "code": "DUPLICATE_EMAIL" }
```
**Validation:**
- `email` format + chưa tồn tại.
- `password` ≥ 8 ký tự + đủ độ phức tạp (frappe policy).
- `department` tồn tại trong `AC Department`.
- `full_name` không rỗng.

### 4.2 `get_user_profile`

**Method:** `GET /api/method/assetcore.api.auth.get_user_profile`
**Auth:** Session required (guest → 401).
**Response:**
```json
{
  "success": true,
  "data": {
    "user": { "name": "bs.an@bv.vn", "full_name": "...", "user_image": "..." },
    "roles": ["IMM Clinical User"],
    "profile": {
      "department": "AC-DEPT-ICU", "department_name": "Khoa ICU",
      "location": "AC-LOC-BLDG-A", "job_title": "...",
      "employee_code": "...", "phone": "...",
      "is_active": 1, "approval_status": "Approved"
    },
    "permissions": {
      "can_create_wo": false,
      "can_approve": false,
      "can_manage_docs": false,
      "is_admin": false
    }
  }
}
```

### 4.3 `update_my_profile` (self-service)

**Method:** `POST /api/method/assetcore.api.auth.update_my_profile`
**Auth:** Session required.
**Body:** Chỉ cho phép sửa `full_name`, `phone`, `job_title`, `employee_code`. Không cho sửa `department`, `imm_roles`, `is_active`.
**Response:** `{ success: true, data: { updated_fields: [...] } }`

### 4.4 `change_password`

**Method:** `POST /api/method/assetcore.api.auth.change_password`
**Auth:** Session required.
**Body:** `{ "old_password": "...", "new_password": "..." }`
**Response:** `{ success: true }` hoặc `{ success: false, error: "Mật khẩu cũ không đúng", code: "BAD_OLD_PWD" }`

---

## 5. Frontend Components

### 5.1 Routes mới cần thêm

| Path | Name | Component | Guard |
|---|---|---|---|
| `/register` | `Register` | `RegisterView.vue` | `requiresAuth: false` |
| `/profile` | `Profile` | `ProfileView.vue` | `requiresAuth: true` |
| `/unauthorized` | `Unauthorized` | `UnauthorizedView.vue` | `requiresAuth: false` |

### 5.2 Component responsibilities

| Component | Chịu trách nhiệm |
|---|---|
| `RegisterView.vue` | Form đăng ký tiếng Việt; validate client; gọi `register_user`; hiển thị thông báo chờ duyệt |
| `ProfileView.vue` | Hiển thị info từ `get_user_profile`; form sửa nhanh (full_name, phone, job_title); button đổi mật khẩu |
| `UnauthorizedView.vue` | Thông báo 403 khi user không đủ role |
| `v-permission` directive | Nhận `string | string[]`; dùng `auth.hasAnyRole()`; ẩn element (`style.display='none'` hoặc remove node) |

### 5.3 Directive `v-permission` — contract

```html
<button v-permission="'IMM System Admin'">Chỉ admin</button>
<button v-permission="['IMM QA Officer', 'IMM System Admin']">QA hoặc Admin</button>
```

- Nếu value là `string` → check `hasRole(value)`.
- Nếu value là `string[]` → check `hasAnyRole(value)`.
- Nếu không đủ quyền → element bị remove khỏi DOM (không chỉ ẩn, tránh user mở DevTools).

---

## 6. Kế hoạch Triển khai (Phase B)

### 6.1 Backend

1. **Thêm field `approval_status`** vào `AC User Profile`:
   - Select: `Pending` / `Approved` / `Rejected`, default `Pending`.
   - Thêm field `approved_by` (Link User, read_only), `approved_at` (Datetime, read_only).
2. **Thêm role `IMM Clinical User`** vào fixtures/hooks.py.
3. **Tạo `assetcore/api/auth.py`** với 4 endpoints ở mục 4.
4. **Cập nhật `ac_user_profile.py`** — khi `approval_status` chuyển sang `Approved` → set `User.enabled=1` + ghi `approved_by/at`.
5. **Migration:** `bench --site miyano migrate`.

### 6.2 Frontend

1. **Tạo `src/api/auth.ts`** — wrapper cho 4 endpoints mới.
2. **Tạo `src/directives/permission.ts`** + đăng ký trong `main.ts`.
3. **Tạo `src/views/RegisterView.vue`, `ProfileView.vue`, `UnauthorizedView.vue`**.
4. **Cập nhật `router/index.ts`** — thêm 3 routes + redirect `/unauthorized` khi guard fail.
5. **Cập nhật `stores/auth.ts`** — bổ sung `register()`, `fetchFullProfile()` (gọi `get_user_profile` để lấy cả profile lẫn department).
6. **Cập nhật `LoginView.vue`** — thêm link "Chưa có tài khoản? Đăng ký" → `/register`.

### 6.3 Thứ tự thực thi

```
BE: field approval_status → BE: fixture role Clinical User → BE: api/auth.py
 → migrate → bench reload
 → FE: api/auth.ts → FE: directive → FE: views → FE: router → FE: store update
 → test manual (đăng ký → duyệt → đăng nhập → profile)
```

### 6.4 Test checklist (UAT)

- [ ] Đăng ký với email mới → nhận thông báo chờ duyệt, `User.enabled=0`.
- [ ] Đăng ký trùng email → lỗi `DUPLICATE_EMAIL`.
- [ ] Đăng nhập khi `enabled=0` → bị reject.
- [ ] Admin set `approval_status=Approved` → user login được.
- [ ] User đã login → `/profile` hiển thị đúng info.
- [ ] User thường truy cập route `requiredRoles=[SysAdmin]` → redirect `/unauthorized`.
- [ ] `v-permission` ẩn button khi user không đủ role.
- [ ] Đổi mật khẩu → mật khẩu cũ sai → `BAD_OLD_PWD`.

---

## 7. Rủi ro & Giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| Self-signup bị spam bot | Rate limit 5/phút/IP + email verification (phase 2) |
| User forget password không có luồng reset | Dùng `/api/method/frappe.core.doctype.user.user.reset_password` có sẵn của Frappe |
| Admin quên duyệt → user không thể làm việc | Scheduler daily: nhắc admin còn N user Pending > 24h |
| Race condition: 2 admin duyệt cùng 1 user | Frappe `doc.save()` có optimistic lock qua `modified`, OK |
| Role sync sai (User.roles lệch với imm_roles) | Controller `_sync_roles_to_user` đã chạy on_update, test kỹ |

---

## 8. Tham chiếu

- `hooks.py` — fixtures Role, doc_events, scheduler
- `assetcore/doctype/ac_user_profile/` — DocType + controller
- `assetcore/api/user_profile.py` — API hiện có (giữ lại cho admin UI)
- `frontend/src/stores/auth.ts` — Pinia store
- `frontend/src/router/index.ts:469` — guard hiện tại
- CLAUDE.md §5, §12, §19 — nguyên tắc "không modify core, audit trail, lifecycle"
