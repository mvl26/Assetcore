---
name: assetcore-fe
description: Build or extend an AssetCore frontend feature using Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query. Use this whenever the user asks to add a view, list/detail page, form, store, composable, API client, dashboard widget, or any frontend feature for any IMM-XX module — including phrases like "tạo view IMM-09", "thêm trang", "wire FE với BE", "form WO", "Pinia store", "list table với filter", "modal chi tiết". Strongly prefer this skill any time the user is touching the `frontend/` directory or talks about Vue components, even if they don't name the framework.
---

# AssetCore Frontend Module Builder

You are extending the Vue 3 SPA at `/home/miyano/frappe-bench/apps/assetcore/frontend/`. The app talks to the Frappe backend via the `frappeGet` / `frappePost` helpers and uses a strict 4-layer architecture.

## Overview

Skill này xây/mở rộng FE feature trên Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query. Nguyên tắc cốt lõi: **kiến trúc 4-layer nghiêm ngặt** (views → composables/stores → api → axios), **không leak mã hệ thống ra UI** (hiển thị display name, status qua label map), và **mọi tương tác có phản hồi** qua notification pipeline.

## When to Use

- Thêm view / list / detail page / form / modal cho module IMM-XX.
- Tạo Pinia store, composable, API client, dashboard widget, sidebar/launcher entry, workflow buttons.
- Wire FE với BE (typed API client mirror BE endpoint), filter table, pagination, autosave form.
- Bất cứ khi nào đụng thư mục `frontend/` hoặc nói về Vue components.
- **KHÔNG dùng khi**: chỉ đụng backend / endpoint / DocType / workflow / service (→ `assetcore-be`), chỉ viết/chạy test (→ `assetcore-test`), hoặc còn ở mức ý tưởng chưa chốt module (→ `assetcore-plan` / `assetcore-doc`).

## Process — build/extend FE feature (4-layer, render-verified)

Quy trình từng bước (spine — chi tiết ở mục dưới):
1. **Mental model 4 layers** — views → composables/stores → api → axios; hard rules + display rules → §Mental model — 4 layers
2. **File layout + Naming NO-EXCEPTIONS** — `api/immXX.ts`·`stores/immXX.ts` IMM-coded, `views/<domain>/` domain-named → §File layout, §Naming convention — NO EXCEPTIONS
3. **Templates** — scaffold API client / Store / View / Form (TanStack Query) → §Templates (API client · Store · View · Forms · TanStack Query)
4. **useApi + Routing + Permissions** — `api.run` toast/loading/field-error; lazy route + `meta.roles`; 3-layer perms → §useApi pattern (memorize this), §Routing, §Permissions — three layers, pick the right one
5. **Notification pipeline** — success/error qua `useNotify`, 1 toast/modal; KHÔNG `toast.error("literal")` nghiệp vụ → §🔔 Notification pipeline (BẮT BUỘC — mọi tương tác có phản hồi)
6. **UI quality** — WCAG 2.1 AA + design system (token Tailwind) + component architecture (container↔presentational) → §Engineering principles — UI quality (named, tailor Vue 3 + Tailwind)
7. **PRE-DONE GREP GATE** — chạy GATE-1..5 + manual GATE-6a/6b/6c/6d trên view vừa sửa; output ≠ 0 → fix → §🛑 PRE-DONE GREP GATE (chạy TRƯỚC khi nói DONE)
8. **Verification** — RENDER thật trong browser (happy + ≥1 error path), không chỉ vitest/structural → §Verification

## Mental model — 4 layers

```
src/views/<module>/*.vue      ← UI (composition API, <script setup>)
        ↓ uses
src/composables/use*.ts       ← reactive logic (useApi, usePermissions, ...)
        ↓ delegates to
src/stores/<module>.ts        ← Pinia store: shared state across views
        ↓ calls
src/api/<module>.ts           ← typed API client (frappeGet/frappePost)
        ↓ axios
src/api/axios.ts              ← CSRF + auth interceptor
```

**Hard rules:**
- Views never call axios directly. Views call store actions or composables; composables/stores call `src/api/`.
- Every API call goes through `frappeGet`/`frappePost` in `src/api/helpers.ts` — they unwrap the `{message: {success, data}}` envelope and throw `ApiError`.
- **`frappeGet`/`frappePost` return `T` directly, not `ApiResponse<T>`.** API functions must be typed `Promise<T>`, never `Promise<ApiResponse<T>>`. Wrong return type is the #1 root cause of `as unknown as` casts cascading through stores and views — catch it at the API layer, not after.
- Use `useApi().run(fn, opts)` in views to get free toast + loading + field-error wiring.
- Type every API response with an `interface` exported from `src/api/<module>.ts`. The store and views import these — no `any`.
- Stores must NOT re-export the API module (`return { ..., api }` where `api = * from '@/api/xxx'`). That leaks the transport layer into views and breaks the 4-layer separation.
- Catch blocks in stores: always `catch (e: unknown)` + `e instanceof Error ? e.message : String(e)`. Never `catch (e: any)`.

**Display rules (UI/UX — không hiện mã hệ thống với user):**
- **Tên nhà cung cấp**: hiển thị `supplier_name` (tên đọc được), KHÔNG phải `name` (mã `SUP-2026-XXXXX`). Luôn request thêm `supplier_name` trong API response.
- **Tên thiết bị**: hiển thị `asset_name` hoặc device_model — KHÔNG phải `name` (mã `ACC-ASS-*`). Bên dưới mã nhỏ hơn làm sub-text là OK.
- **Người dùng (hiển thị)**: `full_name`, KHÔNG phải `email` hay system user ID — trừ sub-text phụ.
- **Người dùng (CHỌN — mọi picker phân công / mô-tả-người)**: BẮT BUỘC `<ApproverSelect context="...">` (`components/commissioning/ApproverSelect.vue` → `api/user.ts::listAssignableUsers` → BE `list_assignable_users`). **TUYỆT ĐỐI KHÔNG `SmartSelect doctype="User"`** cho field chọn người — nó kéo TOÀN BỘ Frappe user, bỏ qua định danh "user AssetCore" (base role `AssetCore System User`) → lộ người ngoài hệ thống + chọn nhầm người mà BE từ chối. Đây **KHÔNG phải "fallback đơn giản hơn" — nó SAI**. Chọn `context`: field cần **năng lực thao tác** (KTV sửa/PM/hiệu chuẩn/sự cố/lắp đặt) → context capability (`repair`/`pm`/`calibration`/`incident`/`commissioning`); field **chỉ mô-tả-người** (giám sát, thủ kho, trưởng khoa, người nhận, leo thang SLA) → `context="user"` (mọi user AssetCore, KHÔNG lọc năng lực). `role="..."` CHỈ khi cần đúng 1 Frappe role (hiếm). Cần context mới → thêm ở BE `_ASSIGNABLE_CONTEXTS` (xem `assetcore-be` anti-pattern #18). ApproverSelect: `modelValue` nhận `string|undefined|null`, có prop `id` cho `<label for>`.
- **Trạng thái**: dùng `STATUS_LABEL` map để dịch — mọi status key trong map PHẢI khớp **chính xác** với constant trong BE service (`_STATUS_*`). Không tự đặt tên "thân thiện" cho status key.
- **Select options trong form**: options `<select>` PHẢI khớp chính xác với `options` trong DocType JSON field. Không dùng nhãn tiếng Việt làm value — value là string kỹ thuật, label mới là tiếng Việt.
- **Risk class mapping**: AC Asset dùng `"Low/Medium/High/Critical"`. Khi truyền sang DocType khác có schema khác (vd Asset Repair dùng `"Class I/II/III"`), PHẢI có mapping layer trong service BE — FE không tự map.
- **`allowed_transitions` check**: `includes(...)` dùng đúng chuỗi BE trả về, không dùng tên display. Luôn kiểm tra `_VALID_TRANSITIONS` dict trong service khi viết `canXxx` computed.

**Form state rules:**
- `useFormDraft` lưu draft vào localStorage — sau khi fix options/values, test với fresh state (clear localStorage hoặc dùng private window) để tránh bug từ cache cũ.
- Khi thay đổi select options hay default values, luôn kiểm tra: form draft có thể giữ giá trị cũ không còn hợp lệ.

## Stack quick-reference

| Concern | Tool | Where it lives |
|---|---|---|
| Component framework | Vue 3 (`<script setup lang="ts">`) | `vite.config.ts` |
| State | Pinia + `pinia-plugin-persistedstate` (auth only) | `src/stores/`, `src/main.ts` |
| Routing | Vue Router 4 | `src/router/index.ts` (12 numbered sections) |
| HTTP | axios + `frappeGet/frappePost` envelope unwrap | `src/api/axios.ts`, `src/api/helpers.ts` |
| Generic CRUD | `FrappeResource<T>` for `/api/resource/...` (rarely needed) | `src/services/frappeResource.ts` |
| Server cache | `@tanstack/vue-query` (`staleTime: 5min`, `gcTime: 10min` global) | `src/main.ts` |
| i18n | `vue-i18n` | `src/locales/` |
| Styling | TailwindCSS (utility-first; emerald-600 primary, neutral-* surfaces) | `tailwind.config.js` |
| Forms | controlled `ref`s + `useApi.onFieldError` + `useFormDraft` autosave | `src/composables/useFormDraft.ts` |
| QR | `qrcode` npm — for asset labels | — |
| Permissions UI | `v-permission` directive | `src/directives/permission.ts` |
| Toast | `useToast` composable + `ToastContainer` mounted in `App.vue` | `src/composables/useToast.ts` |

## File layout

```
frontend/src/
├── api/immXX.ts            # IMM-coded — mirror BE module name
├── stores/immXX.ts         # IMM-coded — match api/ layer
├── composables/use<X>.ts   # reusable reactive logic
├── views/<domain>/         # DOMAIN-named — never immXX
│   ├── ListView.vue
│   ├── DetailView.vue
│   ├── tests/              # ⇐ MỌI test của các .vue trong thư mục này
│   └── components/...
├── components/<domain>/    # shared sub-components (cards, modals) + tests/
├── router/index.ts         # add new routes here
├── types/                  # cross-cutting types
├── locales/                # NHÀ CHUỖI DUY NHẤT: vi/en.json (vue-i18n) + messages.ts (GENERATED từ BE)
├── test/                   # harness dùng chung + paths.ts (SSoT đường dẫn cho guard)
├── guards/                 # test ĐỌC ĐĨA / cưỡng chế quy ước / parity doc↔mã
└── integration/            # test khởi động app · route · luồng chéo nhiều nguồn
```

## 🧭 Vị trí & tên file test FE — BẮT BUỘC

> SSoT cưỡng chế: `frontend/src/guards/testFileConvention.guard.test.ts` (K1–K9).
> Spec đầy đủ: `docs/architecture/SPEC_chuan_hoa_cau_truc_frontend.md`.

Mỗi file test chỉ được ở **một trong ba nhà**:

| # | Loại test | Nhà | Tên file |
|---|---|---|---|
| 1 | Test của **MỘT** file nguồn | **`<thư-mục-nguồn>/tests/`** | `<Nguồn>.test.ts` — nếu là test duy nhất<br>`<Nguồn>.<khiaCanh>.test.ts` — nếu tách nhiều khía cạnh |
| 2 | **Guard / parity / ngân sách** (đọc đĩa, cưỡng chế quy ước, đối chiếu doc↔mã) | **`src/guards/`** | `<chuDe>.guard.test.ts` |
| 3 | **Tích hợp / khởi động / route** (không thuộc file nguồn nào) | **`src/integration/`** | `<luong>.integration.test.ts` |

**Nhà #1 = thư mục con `tests/` NGAY CẠNH nguồn**, KHÔNG đặt ngang hàng file nguồn:

```
views/cm/
├── CMCreateView.vue
├── CMWorkOrderDetailView.vue
└── tests/
    ├── CMCreateView.test.ts
    ├── CMCreateView.qrPrefill.test.ts
    └── CMWorkOrderDetailView.allowedTransitions.test.ts
```

`<Nguồn>` khớp **CHÍNH XÁC** tên file nguồn ở **thư mục cha** của `tests/` (`PascalCase` cho `.vue`, `camelCase` cho `.ts`). `<khiaCanh>` là `camelCase`, **đã lược tiền tố trùng tên nguồn**.
`src/guards/` và `src/integration/` **KHÔNG** thêm tầng `tests/` — bản thân chúng đã là nhà test riêng, không có file nguồn nào lẫn vào.

| ❌ Sai | ✅ Đúng | Vì sao |
|---|---|---|
| `components/common/smartSelectResilience.test.ts` | `components/common/tests/SmartSelect.resilience.test.ts` | nguồn là `SmartSelect.vue`; tên phải nói ra + phải nằm trong `tests/` |
| `views/asset/assetScanInfoSerial.test.ts` | `views/asset/tests/AssetScanInfoView.serial.test.ts` | |
| `views/cm/CMCreateView.test.ts` | `views/cm/tests/CMCreateView.test.ts` | tên đúng nhưng **sai chỗ** — không đặt ngang hàng nguồn |
| `views/detailShellAdoption.test.ts` | `guards/detailShellAdoption.guard.test.ts` | quét `SRC/views` ⇒ là guard |
| `api/connectionsLegacyKeysRetired.acr92.test.ts` | `guards/connectionsLegacyKeys.guard.test.ts` | đọc đĩa ⇒ guard; **bỏ mã ticket khỏi tên** |
| `App.auth.test.ts` | `integration/appAuth.integration.test.ts` | mount cả app + router ⇒ test khởi động |

**CẤM (guard sẽ ĐỎ):**
- Đặt file test **ngang hàng** file nguồn (K1a) · thư mục `__tests__/` (dùng `tests/`) · thư mục `tests/` **mồ côi** (cha không có file nguồn nào) · đuôi `.spec.ts` · mã ticket trong **tên file** (`acr92`, `AC-CR-…` → đưa vào `describe()`/`it()`).
- Dấu chấm giữa tên file **nguồn** `.ts` (`messages.types.ts` ❌ → `messageTypes.ts` ✅).
- Test **ngoài** `guards/` mà **quét thư mục** (`readdirSync`, `import.meta.glob`) hoặc **đọc file ở thư mục KHÁC** — đó là guard, phải chuyển vào `guards/`. Test trong `tests/` chỉ được đọc file nguồn ở **thư mục cha** (`resolve(__dirname, '..', 'X.vue')`).
- Guard trong `guards/` mà tính đường dẫn theo **độ sâu** (`resolve(HERE, '../..')`, `resolve(__dirname, '..')`, `process.cwd()`) — phải lấy anchor từ **`@/test/paths`**.
- Guard **quét thư mục** mà không **chốt dân số tối thiểu** — dùng `listFiles(DIR, { ext, min: N })` hoặc đánh dấu `// [K8] dân số:` ngay tại chỗ khoá. Thiếu chốt ⇒ thư mục bị dời thì guard đếm 0 và **PASS giả**.

**Trước khi báo xong:** `cd frontend && npx vitest run src/guards/testFileConvention.guard.test.ts`

## Naming convention — NO EXCEPTIONS

The codebase uses **two layers with different naming systems**. Mixing them creates the worst-of-both situation. Stick to:

| Layer | Pattern | Example | Wrong |
|-------|---------|---------|-------|
| `api/` | `immXX.ts` (IMM-coded, mirrors BE) | `api/imm09.ts` | `api/repair.ts`, `api/immXX-cm.ts` |
| `stores/` | `immXX.ts` (IMM-coded, no prefix/suffix) | `stores/imm09.ts` | `stores/useImm09Store.ts`, `stores/repair.ts`, `stores/imm09Store.ts` |
| `views/<domain>/` | Domain folder, lowercase, hyphenated | `views/cm/`, `views/tech-specs/`, `views/master-data/` | `views/imm09/`, `views/IMM09/`, `views/CM/` |
| `components/<domain>/` | Same as views | `components/commissioning/` | `components/imm04/` |

**Domain → IMM module mapping** (canonical — extend this table when adding a new module):

| Domain folder | IMM module | Notes |
|---------------|-----------|-------|
| `needs` | IMM-01 | Needs Requests + Procurement Plans |
| `tech-specs` | IMM-02 | Technical Specifications |
| `procurement` | IMM-03 | Vendor Eval, AVL, Decisions (purchase orders go in `purchase/`) |
| `commissioning` | IMM-04 | Installation + commissioning |
| `document` | IMM-05 | Document repository |
| `training` | IMM-06 | Training programs + sessions |
| `pm` | IMM-08 | Preventive Maintenance |
| `cm` | IMM-09 | Corrective Maintenance / Repair |
| `calibration` | IMM-11 | Calibration |
| `incident` | IMM-12 | Incident + RCA |
| `inventory` | IMM-15 | Spare parts + stock |
| `audit` | IMM-16 | Compliance / audit trail |

**Rationale:**
- `api/` and `stores/` are the "code" layer — they mirror BE for traceability (`assetcore.api.imm09` ↔ `frontend/src/api/imm09.ts`).
- `views/` is the "presentation" layer — URL paths are domain-named (`/cm/work-orders`, not `/imm09/work-orders`), so folders match URLs for readability.
- New modules MUST use domain folder names. If a clean domain noun doesn't exist, propose one in this table before creating the folder.

## Templates (API client · Store · View · Forms · TanStack Query)

> Heavy reference: see [references/fe-templates.md](references/fe-templates.md).

Copy-paste scaffolds for `api/immXX.ts`, `stores/immXX.ts`, the List/Detail view, `useFormDraft` autosave, and Vue Query. Key reminders that live here too:
- API function return type is `Promise<T>`, never `Promise<ApiResponse<T>>` — `frappeGet`/`frappePost` already unwrap.
- Pass dict/list params as `JSON.stringify(...)`; endpoint path mirrors BE `assetcore.api.<module>.<fn>`.
- Pinia "setup" syntax only; store sets `error`, views surface it (no `useToast` inside stores).
- Reserve Pinia for client-owned state; use Vue Query for server-owned read-heavy lists.

## useApi pattern (memorize this)

```ts
const api = useApi()

const formErrors = reactive<Record<string, string>>({})

const result = await api.run(() => createXThing(payload), {
  successMessage: 'Đã tạo work order',
  onFieldError: (fields) => Object.assign(formErrors, fields),
})

if (result) {
  // happy path — result is the unwrapped data
  router.push({ name: 'imm09-detail', params: { name: result.name } })
}
// `result` is null on error; toast already shown unless silentError: true
```

`useApi` automatically:
- Shows green toast on `successMessage`.
- Shows yellow toast for `BUSINESS_RULE_VIOLATION` / `VALIDATION_ERROR` / `CONFLICT` (`isBusinessError`).
- Shows red toast for `INTERNAL_ERROR` / network errors.
- Skips toast for 401/403 (axios interceptor redirects to login).
- Calls `onFieldError(fields)` so your form can render inline errors next to inputs.

## Routing

```ts
// src/router/index.ts — add to existing routes array
import { ROLES_CM_MANAGE } from '@/constants/roles'

{
  path: '/imm09',
  meta: { requiresAuth: true, roles: ROLES_CM_MANAGE },
  children: [
    { path: '', name: 'imm09-list', component: () => import('@/views/cm/ListView.vue') },
    { path: ':name', name: 'imm09-detail', component: () => import('@/views/cm/DetailView.vue'), props: true },
  ],
}
```

Conventions:
- Lazy-import every view (`() => import(...)`) — keeps initial bundle small.
- `meta.roles` should be a `readonly RoleName[]` from `@/constants/roles` (not inline strings). The navigation guard in `router/index.ts` checks them against `useAuthStore().roles` and redirects to `/login` or `/403` accordingly.
- Existing routing convention sections are documented at the top of `router/index.ts` (12 sections: Auth/Root, IMM-00, IMM-04, …, Errors). Insert new routes into the matching section instead of appending.

## Permissions — three layers, pick the right one

**1. Role constants — `@/constants/roles`** (mirrors BE `services.shared.constants.Roles`):

```ts
import { Roles, ALL_IMM_ROLES, ROLES_CREATE_WO, ROLES_APPROVE, ROLES_PM_MANAGE,
         ROLES_CM_MANAGE, ROLES_CAL_MANAGE, ROLES_INCIDENT_REPORT, ROLES_RCA_OWNER,
         ROLES_CAPA_CLOSE, ROLES_MANAGE_DOCS, ROLES_ADMIN_ONLY } from '@/constants/roles'
```

Every role and group used by routes / directives must come from this file. Adding a role to BE? Mirror it here.

**2. Auth store — `useAuthStore()`** is the source of truth at runtime:

```ts
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()

auth.hasRole(Roles.WORKSHOP)
auth.hasAnyRole(ROLES_APPROVE)
auth.canCreate          // group computeds
auth.canApprove
auth.canSubmit
auth.canManageDocs
auth.isSystemAdmin
```

**3. `v-permission` directive** — for declarative show/hide:

```vue
<button v-permission="Roles.SYS_ADMIN">Admin only</button>
<button v-permission="ROLES_APPROVE">Approve</button>
```

The directive removes the element from the DOM if the user lacks the role — it's not just `display: none`, so don't rely on `v-permission` to hide truly sensitive data (the API check is what matters).

**Note on the `usePermissions` composable:** an older composable at `composables/usePermissions.ts` exposes a thinner subset (`isAdmin`, `isQA`, `canApproveRelease`). New code should prefer `useAuthStore()` directly — it has more accurate IMM role helpers and stays in sync with the role constants. The composable is kept for the few legacy components still using it.

## 🔔 Notification pipeline (BẮT BUỘC — mọi tương tác có phản hồi)

> Contract đầy đủ BE↔FE: [`../assetcore-be/references/notification-contract.md`](../assetcore-be/references/notification-contract.md).
> Quy tắc: success/error đều qua `useNotify` → 1 toast/modal duy nhất. KHÔNG `toast.error("literal")` cho nghiệp vụ, KHÔNG để action thành công mà user không nhận phản hồi.

**Store** (`stores/immXX.ts`) — giữ ApiError đã hydrate:
```ts
import { ApiError, toApiError } from '@/api/errors'
const lastApiError = ref<ApiError | null>(null)
function _captureError(e: unknown): void {
  const err = toApiError(e); lastApiError.value = err; error.value = err.message
}
async function submit(id: string) {
  try { return await apiSubmit(id) }
  catch (e: unknown) { _captureError(e); return null }   // mọi action: catch → _captureError → null
}
return { /* ... */ lastApiError, _captureError, submit }
```

**View** (`views/.../XDetailView.vue`):
```ts
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/i18n/messages'
const notify = useNotify()

const ok = await store.submit(props.id)
if (ok) notify.show({ code: MSG.IMM11_SUBMIT_SUCCESS, ctx: { name: props.id } })
else    notify.fromError(store.lastApiError)
```
- Success → `notify.show({ code: MSG.*, ctx })` (CRUD generic: `MSG.UI_SAVE_SUCCESS` + `ctx.entity`).
- Fail → `notify.fromError(store.lastApiError)` — render title + action_hint + severity từ registry; `critical` → modal.
- FE-only pre-check (vd thiếu file) → cũng `notify.show({ code: MSG.* })`, KHÔNG `toast.warning("literal")`.
- Thêm mã mới? BE sửa `messages.py` + chạy `scripts/gen_fe_messages.py` để regen `i18n/messages.ts`. FE KHÔNG tự sửa `messages.ts`.

## Build sequence & UI Completeness

> Heavy reference: see [references/fe-build-sequence.md](references/fe-build-sequence.md).

The exact file-path build order for a new IMM module on FE (verify BE endpoint names FIRST — BLOCKING), the full **List page / Detail page checklists**, the **UI Completeness Rules**, the canonical **Workflow button pattern**, and the API-function naming convention all live there. Read it before scaffolding a module and before claiming Done.

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Cascade of `as unknown as T` casts in store/views | API function typed `Promise<ApiResponse<T>>` instead of `Promise<T>` | Fix return type in `api/immXX.ts` — `frappeGet`/`frappePost` already unwrap the envelope |
| Runtime crash: `e.message` is undefined | `catch (e: any)` when `e` is a string or plain object | Use `catch (e: unknown)` + `e instanceof Error ? e.message : String(e)` |
| View can call `store.api.xxx()` — layer violation | Store returns `api` namespace in its return object | Remove `api` from store return; views import directly from `@/api/` |
| `object` / `object[]` param not type-safe | API function typed `param: object` | Use `Record<string, unknown>` or `Record<string, unknown>[]` |
| Empty table flashes before data loads | `v-if="!loading"` shows table with 0 rows during first fetch | Use `v-if="loading"` / `v-else-if="error"` / `v-else` tri-branch |
| Error is swallowed silently, user sees empty list | `v-else` shows empty state even when `store.error !== null` | Always add `v-else-if="error"` branch with error banner + retry button |
| 403 on every POST after login | CSRF token not refreshed | `setCsrfToken(loginResponse.data.csrf_token)` after login |
| Store updates but view doesn't re-render | Used `const { items } = store` instead of `storeToRefs` | Use `storeToRefs` |
| Toast shows red for "asset already under repair" | BE returned wrong code (should be `CONFLICT`) | Fix BE — UX category derives from `ErrorCode` |
| Form errors don't appear | Forgot `onFieldError` in `api.run` opts | Add it; bind to a reactive `formErrors` |
| `JSON.parse` error from FE | BE used `frappe.whitelist` without methods=POST and FE sent body | BE needs `methods=["POST"]` |
| Hot reload broken | Vite proxy not configured for `/api/method` | Check `vite.config.ts` proxy |
| Table cell hiển thị raw `WO-RP-2026-00123` thay vì tên thiết bị | BE list endpoint chỉ trả `asset_ref` (Link ID), thiếu `asset_name` | **Fix BE**: `services/immXX.py` thêm `asset_name` vào `fields=[...]` của `frappe.get_all(...)`. FE không workaround bằng extra fetch. |
| FE template dùng pattern `{{ wo.asset_name \|\| wo.asset_ref }}` fallback | BE response shape không nhất quán — đôi khi trả name, đôi khi không | **Fix BE** một lần cho dứt; FE bỏ fallback sau khi BE đã chuẩn |
| Form Create gọi `loadAssetMeta(ref)` riêng sau khi user nhập ref → N+1 query, UX chậm | BE list/search endpoint cho Link field không kèm meta | **Fix BE**: link search endpoint trả `{name, asset_name, device_model_name, location_name, risk_class}` trong cùng response. FE bỏ `loadXxxMeta()` |
| Sidebar trống khi vào module | Route thiếu `meta.moduleId` hoặc key sai với `MODULE_NAV` | Set `meta.moduleId: 'immXX'` matching key trong `MODULE_NAV` |
| Module mới không hiện trong launcher | Tile có `disabled: true` từ wave trước hoặc `to:` route không tồn tại | Set `disabled: false` + verify route tồn tại trong router |

## 🛑 PRE-DONE GREP GATE (chạy TRƯỚC khi nói DONE)

5 phiên test 2026-05-15..26 leak lại cùng pattern dù LL-FE-3/6/13 đã có. Bắt buộc chạy các grep gate dưới đây (GATE-1..5,7 + manual GATE-6a/6b) trên view/component bạn vừa sửa. **Output ≠ 0 → fix, không skip.**

```bash
cd /home/miyano/frappe-bench/apps/assetcore

# GATE-1: English enum leak. Mọi {{ x.<enum> }} phải đi qua label fn (constants/labels.ts).
# KHÔNG CHỈ status — mọi field enum render thô đều leak. GATE-1 cũ (chỉ status|frequency|
# severity + prefix row|item|doc|d) BỎ SÓT 17 leak (session 2026-06-29): transfer_type,
# pm_type, wo_type, overall_result, calibration_type, medical_device_class, reference_type,
# avl_status, nc_type, lifecycle_status, priority, audit_type, event_type, measurement_type.
# Prefix object BẤT KỲ (wo./m./form./nc./selectedEvent./a./...), KHÔNG chỉ row/doc.
grep -rnE "\{\{\s*[A-Za-z_][A-Za-z0-9_.]*\.(status|workflow_state|frequency|severity|transfer_type|pm_type|wo_type|overall_result|calibration_type|medical_device_class|reference_type|imm_avl_status|avl_status|nc_type|lifecycle_status|priority|audit_type|event_type|measurement_type|category|scope|pass_fail)\s*\}\}" \
  frontend/src/views/<your-domain>/ \
  | grep -vE "Label\(|labelFor|formatStatus|translateStatus|tLabel"

# GATE-2: Raw code/email leak. row.technician/owner/vendor/model/asset/warehouse
# phải có `_name` / `_full_name` companion từ BE và FE phải dùng `x_name || x`.
grep -rnE "row\.(asset|model|vendor|warehouse|department|technician|assigned_to|owner)\b" \
  frontend/src/views/<your-domain>/ | grep -vE "_name|_full_name|_label"

# GATE-3: Hardcoded English status strings trong code (không phải template)
grep -rnE "['\"](Locked|Evaluated|Contract Signed|Scheduled|Weekly|Minor|Open|In Progress)['\"]" \
  frontend/src/views/<your-domain>/ | grep -v "STATUS_LABEL\|// "

# GATE-4: Raw frappe.client.* call leak (→ LL-FE-40). Output PHẢI = 0.
# Mọi lookup phải qua endpoint AssetCore whitelisted permission-aware — KHÔNG frappe.client.get_value/get_list/get.
grep -rnE "frappe\.client\.(get_value|get_list|get)" frontend/src/{views,composables,stores}

# GATE-5: Promise.all ref-prefetch (→ LL-FE-45). Review MỖI match.
# prefetch ref/lookup PHỤ phải đổi Promise.allSettled (giữ Promise.all chỉ khi mọi nhánh bắt buộc thành công).
# Mục tiêu: 1×403 KHÔNG blank cả trang.
grep -rn 'Promise.all(' frontend/src/{stores,composables}

# GATE-7: Bare <option> tiếng Anh (value==text) trong <select> bound enum (→ LL-FE-49).
# Việt-hoá text BARE option PHẢI thêm value="<EN gốc>" (khớp EXACT DocType Select `options`)
# TRƯỚC, nếu không form submit tiếng Việt → 422 / filter vỡ. Review mỗi match:
grep -rnE "<option>[^<]*[A-Za-zÀ-ỹ]{3}" frontend/src/views/<your-domain>/
# + đối chiếu tập <option value="X"> FE vs DocType field Select `options` BE — DRIFT = bug
#   (vd FE audit_type [Internal/External/Surveillance] ≠ BE [Internal/Self-assessment]).

# GATE-7: User-picker phải là ApproverSelect, KHÔNG `SmartSelect doctype="User"`
# (→ user-source-base-role rule: chọn người = user AssetCore, KHÔNG toàn bộ Frappe
# user). Output PHẢI = 0. Mỗi match → đổi sang
# <ApproverSelect context="user|repair|pm|calibration|incident|commissioning">.
grep -rnE 'doctype="User"' frontend/src/views/

# GATE-9: Field đính kèm bị render bằng ô GÕ ĐƯỜNG DẪN (→ LL-FE-54). Output PHẢI = 0.
# "Điền file" = TẢI LÊN + lưu vào hệ thống, KHÔNG phải gõ/dán '/files/...' hay URL.
grep -rn "placeholder=\"[^\"]*/files/" frontend/src            # ô gõ path (trừ FileUploadField.vue)
grep -rniE '<input[^>]*v-model[^>]*(attachment|_doc|_proof|evidence|certificate_file|file_url)' frontend/src
grep -rn "upload_file" frontend/src/api                          # /api/method/upload_file TRẦN
# Mỗi match → thay bằng <FileUploadField v-model="..." doctype="..." fieldname="..."
#   [parent-doctype="..." khi doctype là bảng con] :docname="..." />
```

**GATE-1/GATE-2 scope (BẮT BUỘC mở rộng — KHÔNG chỉ ListView):** chạy GATE-1 (EN-enum) + GATE-2 (raw-code) thêm trên **DetailView + dashboard card** (`{{ ...status }}` trong `KpiCard`/donut), không chỉ ListView. Bug Wave2 IMM-12-A (dashboard cards 'Open'/'In Progress') + IMM-11-B (Cal detail 'Scheduled' dù list đã 'Đã lên lịch') lọt vì detail+card quên áp map dù list đúng. Bồi thêm key thiếu vào audit-list LL-FE-30: `Under Maintenance`→'Đang bảo trì', `Scheduled`→'Đã lên lịch', `Locked`, `Evaluated`, `Contract Signed`, `Weekly`, `Minor`.

Kèm 4 manual check không tự động được:
- DetailView có **TRANSITIONS_BY_STATE đầy đủ initial state** (Draft/Open/Planned)? Count entries trong map phải = số state non-terminal trong workflow JSON.
- ListView có **ít nhất 1 action button** (Tạo / Import / Navigate)? Empty state actionable?
- **GATE-6a — qr-scan prefill parity** (→ LL-FE-43): mỗi create-view có qr-scan prefill (`?asset=<id>&source=qr-scan`) chạy parity test 4 view (PM/Incident/CM/Cal) → locked SmartSelect text == asset code (KHÔNG rỗng).
- **GATE-6b — form 0-state** (→ LL-FE-44): mỗi form có required-dropdown dựa list endpoint chạy test-case `total:0` → có banner + ≥1 lối thoát actionable, KHÔNG chỉ disabled.
- **GATE-6c — control mới (dropdown/toggle/radio)** (→ LL-FE-47): test **param phát đi (body/query/store) == UI-selection** (chọn option B → spy nhận B), chống dead-control — KHÔNG để giá trị hardcode ở call-site, KHÔNG chỉ assert "render đủ N option".
- **GATE-6d — output in/khổ cố định** (→ LL-FE-48): verify bằng RENDER ẢNH thật (pdftoppm/screenshot → đọc bằng mắt), KHÔNG chỉ DOM-assert text-trong-DOM (`overflow:hidden` cắt chữ âm thầm mà DOM-test vẫn PASS).
- **GATE-10 — khoá payload BE phải GREP THẤY TRÊN ĐĨA trước khi bind** (→ LL-FE-55). [BE] chạy SONG SONG trong factory ⇒ khoá trong spec có thể chưa tồn tại. Với MỖI khoá/endpoint mới đọc từ BE: `grep -rn "<khoá>" assetcore/` — **0 hit ⇒ code fail-safe + khai `contract_unverified` + KHÔNG tuyên bố acceptance đạt**. Vitest KHÔNG bao giờ bắt được lỗi này (payload test dựng tay luôn có khoá) ⇒ thêm 1 TC dựng payload **THIẾU** khoá đó, assert UI vẫn dùng được. Gate kiểm-được:
  ```bash
  # mỗi khoá mới tiêu thụ trong api/*.ts phải có ít nhất 1 hit ở BE
  grep -rn "create_prefill\|<khoá-mới>" ../assetcore/ | head   # 0 dòng = hợp đồng CHẾT, dừng lại
  ```
- **GATE-8 — workflow *Detail view render nút theo BE `allowed_transitions` (server-driven CTA), KHÔNG hardcode `status === 'X'`** (→ LL-FE-51). BE emit `allowed_transitions = _VALID_TRANSITIONS.get(status, [])` cho 4 *Detail (Incident imm12 R3 · PM imm08 R21 · CM/Repair imm09 R22 · Calibration imm11). FE gate `canXxx = capability && allowedTransitions.includes('<NextState>')` (mirror `IncidentDetailView`) — KHÔNG `form.value.status === 'X'` (hardcode = trộn luồng + lộ nút sai pha). Với 4 view này nguồn là SERVER, mạnh hơn map client "TRANSITIONS_BY_STATE" ở trên. Gate kiểm-được (AT phải >0 cho CẢ 4):
  ```bash
  for v in IncidentDetailView PMWorkOrderDetailView CMWorkOrderDetailView CalibrationDetailView; do
    f=$(find frontend/src/views -name "$v.vue"); echo "AT=$(grep -cE 'allowed_transitions|allowedTransitions' "$f")  $v"; done
  ```
  RED 2026-06-29: `CalibrationDetailView` hardcode `status === 'Scheduled'` → lộ "Gửi duyệt"(disabled+tooltip) + bảng nhập tham số đo ngay ở Scheduled, trộn In-House↔External; đã fix bằng `allowedTransitions` (AT=7) + tách `canEnterResults` (chỉ pha có result-transition). Gate còn lòi **PMWorkOrderDetailView (AT=0) + CMWorkOrderDetailView (AT=0, 12 status-literal) VẪN hardcode** dù BE đã emit → backlog migrate.

## ✍️ UI copy — chính sách viết tắt (keep/translate) — [[LL-FE-53]]

Mọi chuỗi HIỂN THỊ end-user PHẢI viết **đầy đủ tiếng Việt**. USER đã chốt (2026-07-01) → **KHÔNG cần AskUserQuestion lại**:

- **DỊCH (spell out)** acronym tiếng Anh: `CAPEX`→"Đầu tư mua sắm" · `OPEX`→"Chi phí vận hành" · `TCO`→"Tổng chi phí sở hữu" · `SLA`→"cam kết mức dịch vụ" · `KPI`→"chỉ số hiệu suất" · `MTTR/TTR`→"thời gian sửa chữa trung bình" · `CAPA`→"hành động khắc phục/phòng ngừa" · `RCA`→"phân tích nguyên nhân gốc" · `AVL`→"danh sách nhà cung cấp được duyệt" · `QMS`→"hệ thống quản lý chất lượng" · `WO`→"lệnh công việc" · `PO`→"đơn mua hàng" · `DOA`→"hỏng khi nhận" · `NC`→"sự không phù hợp" · `HTM`→"thiết bị y tế" · `SKU`→"mã hàng" · `FCR`→"yêu cầu thay đổi firmware" · `FTA`→"phân tích cây lỗi" · `PM`→"bảo trì định kỳ" · `CM`→"sửa chữa" · `QA`→"đảm bảo chất lượng" · `L1/L2`→"cấp 1/cấp 2". (glossary đầy đủ: [[LL-FE-53]].)
- **GIỮ NGUYÊN**: (a) VI-common `QR`·`PIN`·`BHYT`·`NSNN`·`BGĐ`·`VD`·`NSX`·`KH`·`KTV`·`NCC`·`BH`·`STT`·`TTBYT`·`BYT`·`VT-TTBYT`(tên phòng ban); (b) tiền tệ `VND`; (c) chuẩn/danh từ riêng `ISO`/`GMDN`/`WHO`/`NIST`/`VILAS` + tên phương pháp (5-Why/Fishbone/Pareto) + ký hiệu `N/A`; (d) value/enum/key/`workflow_state`/fieldname/doctype-name/ID-mask/module-code (`IMM`/`AC`); (e) đuôi file. → chỉ đổi lớp hiển thị, GIỮ value ([[LL-FE-52]]).

**3 bẫy (chi tiết [[LL-FE-53]]):**
1. **Cùng token, khác nghĩa theo NGỮ CẢNH** — `TB`="thiết bị" (glossary) NHƯNG `TB`="trung bình" ở metric (`"thời gian sửa TB"` bind `mttr_hours`); `PM`/`QA` có thể là KEY label-map / value (text đã VI). LUÔN đọc DATA bind trước khi thay — áp glossary mù = sai nghĩa.
2. **Scope KHÔNG chỉ `views/`+`components/`** — text còn render từ `constants/*.ts` (label map: đổi RHS VALUE, GIỮ KEY + role-name BE), `utils/*Labels.ts`, `i18n/messages.ts` (GENERATED — sửa `messages.py` + `python scripts/gen_fe_messages.py`, KHÔNG sửa tay). Liệt kê ĐỦ nguồn render TRƯỚC sweep.
3. **Nhãn hành động workflow** (vd "Phát hành PO") — GIỮ value gửi BE, chỉ thêm `ACTION_LABELS` hiển thị FE-only; đổi chuỗi transition = vỡ workflow + buộc migrate.

**Nhãn enum: 1 SSoT ở `constants/labels.ts`, KHÔNG map cục bộ trong view — [[LL-FE-56]]**
Mỗi map nhãn khai trong 1 `.vue` là một bản sao sẽ drift. RED 2026-08-11: `VENDOR_TYPE_LABEL` khai TRÙNG ở `SupplierDetailView` + `SupplierListView`; `CATEGORIES` (loại phụ tùng) chỉ sống trong `SparePartListView`; `clinical_area_type` **không có map nào** ⇒ màn hình in "ICU"/"Standard" trong khi file nhập/xuất Excel hỏi bằng tiếng Việt — người dùng đọc hai nơi ra hai thứ.
- Nhãn enum sống ở `constants/labels.ts` (hoặc `utils/formatters.ts` cho map dùng-toàn-app), export kèm hàm `xxxLabel(v)`; view CHỈ import.
- Lớp nhập/xuất Excel là **lớp hiển thị** ⇒ cũng phải tiếng Việt. SSoT BE = `assetcore/utils/import_helpers.py::ENUM_DISPLAY_BY_DOCTYPE`; **guard parity BE↔FE** = `assetcore/tests/guards/test_import_enum_labels.py` (đọc thẳng map trong `.ts`, đỏ khi lệch chữ). Sửa nhãn ở FE mà quên BE ⇒ guard đỏ, KHÔNG lọt ra khách.
- Value/enum vẫn GIỮ NGUYÊN (mục (d) ở trên) — chỉ nhãn đổi.

**Sau sweep chuỗi:** grep literal CŨ toàn repo (kể cả `*.test.ts`) — 1 nhãn SSoT đổi vỡ ≥5 file test ở module KHÁC (RCA/SLA 2026-07-01); full `vue-tsc --noEmit` + full `vitest run` (KHÔNG chỉ colocated — `assetcore-test`).

## Critical anti-patterns (từ bugs thực tế — KHÔNG lặp lại)

### ✅ Pattern chuẩn: BASE URL trong API client
```typescript
// ✅ ĐÚNG — dùng const BASE như IMM-09 gold standard
const BASE = '/api/method/assetcore.api.imm06'
return frappeGet(`${BASE}.list_programs`, params)
```
`frappeGet` nhận full path string và pass thẳng vào axios (baseURL = `''`). Pattern `const BASE = '/api/method/assetcore.api.immXX'` là **chuẩn** và nhất quán với IMM-09. Đây KHÔNG phải double-prefix bug.

### 🚫 Lỗi #2: Function name không khớp BE
FE gọi `assetcore.api.imm06.list_programs` nhưng BE expose `list_training_programs`. Result: 100% call fail 404. **Trước khi build FE**: verify mỗi endpoint name trong `assetcore/api/immXX.py` khớp với gì FE sẽ gọi.

Verify command:
```bash
grep "@frappe.whitelist" assetcore/api/immXX.py -A1 | grep "def " | awk '{print $2}' | cut -d'(' -f1
```

### 🚫 Lỗi #3: Planning/Wave 2 roles thiếu trong roles.ts
FE `constants/roles.ts` có thể thiếu roles mới thêm vào BE (`PLANNING`, `TRAINING_OFFICER`, v.v.). **Trước khi build views**: check `assetcore/services/shared/constants.py` và sync tất cả Roles chưa có trong `frontend/src/constants/roles.ts`.

### 🚫 Lỗi #4: Store thiếu nhưng view vẫn chạy (silent undefined)
Một số modules chỉ có API client mà không có dedicated Pinia store — views dùng composable inline hoặc `useMasterDataStore`. **Check trước**: nếu module có ≥3 views hoặc shared state giữa views, cần store riêng. Nếu không, document rõ "module X dùng `useMasterDataStore`".

### 🚫 Lỗi #5: `<style scoped>` mất tác dụng khi thay raw `<input>` bằng child component
View cha có `<style scoped> .modal-body input {…} </style>`. Đổi 1 raw `<input>` → child component (`<DateInput>`/`<CurrencyInput>`/`<ApproverSelect>`) thì inner `<input>` của child **KHÔNG mang `data-v-*` scope của cha** ⇒ selector scoped `.modal-body input` KHÔNG khớp → **mất style** (width/border). **Fix:** child TỰ gắn class utility GLOBAL trên inner input (`form-input w-full`, như `CurrencyInput` vốn làm) — KHÔNG dựa vào scoped-selector của cha. **Rule:** khi swap raw `<input>`→child dưới scoped CSS, verify child sở hữu layout class riêng (render thật, đo width). (session 2026-07-14)

### 🚫 Lỗi #6: raw `<input type="date">` hiển thị theo locale trình duyệt
`<input type="date">` render ngày theo locale trình duyệt (en-US = **mm/dd/yyyy**), user VN đọc sai thứ tự — dù v-model vẫn ISO. **Fix:** dùng wrapper `<DateInput>` (hiển thị **dd/mm/yyyy**, v-model GIỮ ISO → API KHÔNG đổi). **Rule:** KHÔNG ship raw `<input type=date>` cho ngày user-facing; verify bằng render thật (nhập → thấy dd/mm/yyyy). (session 2026-07-14)

## Common Rationalizations

| Lý do hay viện để skip | Sự thật |
|---|---|
| "API trả gì cũng được, cast `as unknown as T` cho nhanh" | Sai return type (`Promise<ApiResponse<T>>`) là root-cause #1 của cascade cast. Type `Promise<T>` ngay ở API layer — `frappeGet`/`frappePost` đã unwrap. |
| "Đặt tên endpoint FE theo trí nhớ, BE chắc cũng vậy" | FE gọi `list_programs` còn BE expose `list_training_programs` = 100% call 404 (Lỗi #2). Grep `@frappe.whitelist` verify TRƯỚC khi build. |
| "Roles mới chắc đã có trong roles.ts rồi" | BE thêm role mà FE chưa mirror → permission denial âm thầm / route không vào được (Lỗi #3, LL-FE-22). Sync `constants.py::Roles` → `roles.ts`. |
| "Module này dùng chung store cũng được, khỏi tạo store riêng" | ≥3 views / shared state mà không có store riêng = silent undefined (Lỗi #4). Tạo store hoặc document rõ dùng `useMasterDataStore`. |
| "Cell hiện `WO-RP-...`/email cũng đọc được mà" | Leak mã hệ thống ra UI; hiển thị `asset_name`/`full_name`. Thiếu `_name` companion → **fix BE** thêm field, KHÔNG fallback `x_name || x` lâu dài. |
| "`{{ row.status }}` raw cho nhanh, sửa sau" | English-enum leak (GATE-1). Mọi status/frequency/severity qua label map; áp cả DetailView + dashboard card, không chỉ ListView. |
| "Cứ dịch hết mọi acronym cho đồng bộ" | Cùng token khác nghĩa theo ngữ cảnh (`TB`=thiết bị vs trung bình; `PM`/`QA` có thể là KEY/value/tên Role Profile BE). Đọc DATA bind + GIỮ value/enum/key/i18n-generated. Policy keep/translate + glossary: §UI copy / [[LL-FE-53]]. |
| "Sửa chuỗi hiển thị rồi, test cùng thư mục xanh là xong" | 1 nhãn SSoT (RCA/SLA) đổi vỡ ≥5 file test ở module KHÁC (incident/cm/utils/constants). Grep literal CŨ toàn repo + full `vitest run`, KHÔNG chỉ colocated (LL-FE-53). |
| "Cho gõ đường dẫn file cũng được, người dùng tự upload chỗ khác" | Tệp KHÔNG vào hệ thống: không có bản ghi `File`, không quyền, không vết audit, gõ sai = hồ sơ NĐ98 rỗng bằng chứng. "Điền file" LUÔN = upload (GATE-9 / LL-FE-54). |
| "Lookup nhanh bằng `frappe.client.get_value`" | Bypass permission-aware endpoint (GATE-4 / LL-FE-40) — output PHẢI = 0. Dùng endpoint AssetCore whitelisted. |
| "Render structural/vitest xanh là UI xong" | UI "xong" = RENDER THẬT chứng minh (LL-FE-46); `overflow:hidden` cắt chữ mà DOM-test vẫn PASS (GATE-6d/LL-FE-48). Verify bằng ảnh thật. |
| "Toast `error('literal')` cho lỗi nghiệp vụ là đủ" | Vi phạm notification contract — success/error đều qua `useNotify`. KHÔNG để action thành công mà user không nhận phản hồi. |
| "Icon button khỏi `aria-label`, ai cũng hiểu cái bút là Sửa" | Vi phạm **WCAG 2.1 AA** — screen-reader đọc rỗng; icon-only PHẢI có `aria-label`. Status chỉ-bằng-màu cũng fail (mù màu) → `StatusBadge` luôn kèm label chữ. |
| "Dựng hết view + mọi nút trước cho nhanh, wire BE sau" | Trái **thin vertical slice** (`incremental-implementation`): 1 api→store→1 view chạy thật rồi mới mở rộng. Build-hết-trước = lỗi dồn, không biết lát nào sai. |

## Red Flags — STOP

- API function typed `Promise<ApiResponse<T>>` (phải `Promise<T>`); param typed `object` (phải `Record<string, unknown>`).
- `catch (e: any)` trong store (phải `catch (e: unknown)` + `instanceof Error` guard).
- Store re-export `api` namespace trong return object (leak transport layer ra views).
- View gọi axios trực tiếp / `store.api.xxx()` — vi phạm 4-layer.
- `{{ row.status }}` / status / severity / frequency raw không qua label map (GATE-1).
- Cell hiển thị `name` (mã `WO-RP-*`/`SUP-*`/`ACC-ASS-*`) hoặc email thay vì `_name`/`full_name` (GATE-2).
- `frappe.client.get_value|get_list|get` ở FE (GATE-4 / LL-FE-40) — output phải = 0.
- Ô nhập tệp là `<input type="text">` / placeholder `/files/...` / nhãn "(file URL)" / hint "upload trước rồi dán đường dẫn" (GATE-9 / LL-FE-54) — dùng `FileUploadField.vue`.
- View thiếu tri-branch `v-if="loading"` / `v-else-if="error"` / `v-else` → lỗi bị nuốt, user thấy empty.
- `TRANSITIONS_BY_STATE` thiếu state có outgoing transition (kể cả Draft/Open/Planned) → user kẹt.
- List page không có action button; Detail page read-only hoàn toàn dù chưa Closed/Cancelled.
- `Promise.all` cho prefetch ref/lookup PHỤ (1×403 blank cả trang — phải `Promise.allSettled`, GATE-5/LL-FE-45).
- Workflow action label / status key FE không khớp EXACT BE (tiếng Việt có dấu) → 422.
- Tuyên bố "xong" chỉ dựa vitest/structural mà không RENDER ẢNH thật (LL-FE-46/48).
- Bind vào khoá payload BE **chưa grep thấy** trong `assetcore/` (GATE-10 / LL-FE-55) — hợp đồng chết: nút bấm được, màn hình trống, vitest vẫn xanh.
- Icon-only button thiếu `aria-label`; `focus:outline-none` không kèm focus ring; status chỉ phân biệt bằng màu (vi phạm **WCAG 2.1 AA** — xem Engineering principles).
- Hex thô / `style="padding:13px"` / đổi primary sang indigo-purple thay vì token Tailwind (`emerald-600`/`neutral-*`) — phá **design system**.

## Verification

Trước khi khai báo FE "xong" — phải có BẰNG CHỨNG (không "có vẻ đúng"). Checklist đầy đủ List/Detail page ở [references/fe-build-sequence.md](references/fe-build-sequence.md):
- [ ] `cd frontend && npm run typecheck && npm run lint` xanh (`vue-tsc --noEmit`) — paste output.
- [ ] PRE-DONE GREP GATE-1..5 chạy trên view/component vừa sửa, mọi output đã xử lý (GATE-4 = 0).
- [ ] GATE-1/GATE-2 chạy thêm trên **DetailView + dashboard card**, không chỉ ListView.
- [ ] GATE-9 (không còn ô gõ đường dẫn tệp) chạy trên view/component vừa sửa — output = 0.
- [ ] GATE-10: mọi khoá payload BE mới tiêu thụ đã `grep` thấy trong `assetcore/` (0 hit ⇒ fail-safe + khai `contract_unverified`, KHÔNG khai "xong").
- [ ] Manual GATE-6a (qr-scan prefill parity) / 6b (form 0-state) / 6c (control không dead) / 6d (render ảnh thật khổ cố định) đã chạy.
- [ ] List page: có nút "Tạo mới", row click → detail đúng URL, filter cập nhật table, pagination, empty-state CTA, loading + error banner.
- [ ] Detail page: đủ fields, workflow buttons đúng state, nút "Quay lại" + "Sửa", tabs (KPI/Audit) có data thật (không 0/empty giả).
- [ ] `TRANSITIONS_BY_STATE` count = số state non-terminal trong workflow JSON (đếm từ JSON, không đoán).
- [ ] Mỗi `frappeGet/frappePost` đối chiếu khớp tên function trong `assetcore/api/immXX.py`; roles mới đã sync vào `constants/roles.ts`.
- [ ] success/error đều qua `useNotify` (notification pipeline) — không `toast.error("literal")` nghiệp vụ.
- [ ] **WCAG 2.1 AA**: Tab qua được mọi action; icon button có `aria-label`; focus ring nhìn thấy; status có label chữ (không chỉ màu); empty/loading/error tri-branch (xem Engineering principles).
- [ ] UI verify bằng RENDER THẬT trong browser (happy path + ≥1 BE error path), không chỉ vitest/structural (LL-FE-46); màn GATED bằng phiên sai-role → cấp-tạm capability rồi REVERT (playwright-patterns LL-QA-16/17, LL-BE-63).
- [ ] Đã đọc `references/lessons-learned.md` (LL-FE-*) trước khi viết — không tái phạm.

## Where to look for live examples

- `src/api/imm09.ts`, `src/stores/imm09.ts`, `src/views/cm/` — full IMM-09 vertical (Corrective Maintenance)
- `src/api/imm08.ts`, `src/stores/imm08.ts`, `src/views/pm/` — IMM-08 (Preventive Maintenance)
- `src/api/imm11.ts`, `src/views/calibration/` — IMM-11 (Calibration)
- `src/api/helpers.ts` — `frappeGet`, `frappePost`, envelope unwrap
- `src/api/errors.ts` — `ApiError`, `ErrorCode`, `httpStatusToCode`, `toApiError`
- `src/api/axios.ts` — CSRF interceptor (`setCsrfToken`, `getCsrfToken`, retry-on-CSRF-fail)
- `src/services/frappeResource.ts` — generic `FrappeResource<T>` wrapper for `/api/resource/...` (Frappe core CRUD); use sparingly, prefer module-specific endpoints in `src/api/`
- `src/composables/useApi.ts` — request wrapper (toast + loading + field-error)
- `src/composables/usePagination.ts`, `useFormDraft.ts`, `useWorkflow.ts`, `useToast.ts` — common composables
- `src/components/common/` — `BaseModal`, `BasePagination`, `StatusBadge`, `ListFilterBar`, `LinkSearch`, `SmartSelect`, `LoadingSpinner`, `SkeletonLoader`, `ToastContainer`, `PageHeader`, `AppLayout`, `AppSidebar`, `AppTopBar` — reuse these instead of rebuilding
- `src/constants/roles.ts` — role catalog (mirror of BE)
- `src/directives/permission.ts` — `v-permission`
- `src/stores/auth.ts` — auth + role helpers (canCreate, canApprove, etc.)
- `src/main.ts` — app bootstrap (Pinia + persisted state, Vue Query defaults, i18n, error handlers)

> Reusable component patterns (modal, confirm dialog, status badge, pagination, table, responsive mobile-first, loading+error tri-branch, form field with inline error): see [references/component-patterns.md](references/component-patterns.md).

## Cross-skill conventions

Project-wide rules especially relevant to this skill:

- Error Handling — FE error codes mirror BE `ErrorCode` enum; sync via `frontend/src/api/errors.ts`
- Vietnamese vs English — labels VN, code EN
- Wave-aware — IMM-09 is the BE reference; mirror its FE patterns

### Module-specific gotchas
- `useWorkflow` composable is the canonical workflow-aware form pattern
- `usePermissions` is legacy; new code should use `useAuthStore()`
- Routes for IMM-XX live under `frontend/src/views/<module>/`

---

## Lessons Learned — bug patterns FE production (BẮT BUỘC ĐỌC)

> ⚠️ Các quy tắc **LL-FE-*** (always-apply, KHÔNG optional) đã chuyển sang
> [`references/lessons-learned.md`](references/lessons-learned.md) — TRANSITIONS_BY_STATE đầy đủ,
> workflow action labels khớp BE (tiếng Việt có dấu), StatusBadge sync, list/detail buttons,
> hiển thị display name (không leak code/email), child table không dùng `row.name`, KPI consistency…
>
> **BẮT BUỘC: `Read references/lessons-learned.md` TRƯỚC KHI viết/sửa view · store · API client.**
> Bỏ qua = tái phạm bug đã biết.

---

## Engineering principles — UI quality (named, tailor Vue 3 + Tailwind)

> Absorb 2 principle generic vào FE AssetCore. Hiệu năng FE (lazy route, TanStack cache,
> virtual list, **Core Web Vitals**) là principle riêng → thuộc skill **assetcore-perf**,
> KHÔNG lặp ở đây — khi đụng LCP/INP/bundle/virtual-list, dùng `assetcore-perf`.

### `frontend-ui-engineering` (production-quality UI)

Mọi view/list/detail/form AssetCore phải đạt 3 trục — không phải "AI look":

**1. WCAG 2.1 AA accessibility** (bắt buộc mỗi component tương tác):
- **Keyboard nav**: action click được phải Tab tới + Enter/Space được. Dùng `<button>`/`<a>` thật, KHÔNG `<div @click>` (mất focus). Modal (`BaseModal`) phải trap focus + Esc đóng + trả focus về trigger.
- **Focus ring**: KHÔNG `focus:outline-none` trần — luôn kèm `focus-visible:ring-2 focus-visible:ring-emerald-500`.
- **aria-label cho icon button**: nút chỉ có icon (sửa/xoá/QR/đóng) phải `aria-label="Sửa work order"` (KHÔNG để screen-reader đọc rỗng).
- **Contrast ≥ 4.5:1** text thường (3:1 text lớn); status KHÔNG chỉ bằng màu — `StatusBadge` phải có **label chữ** kèm màu (mù màu vẫn đọc được).
- **Empty / loading / error state**: tri-branch `v-if="loading"` (SkeletonLoader) / `v-else-if="error"` (banner + retry) / `v-else` (data hoặc empty-state có CTA). Trùng GATE tri-branch — đây là lý do AA của nó.

```vue
<!-- ✅ icon button có aria-label + focus ring -->
<button :aria-label="`Sửa ${row.asset_name}`"
        class="focus-visible:ring-2 focus-visible:ring-emerald-500 rounded p-1.5"
        @click="edit(row)"><PencilIcon class="h-4 w-4" /></button>
```

**2. Design system** (token Tailwind nhất quán, không tự chế giá trị):
- Màu **semantic qua config**: `emerald-600` primary, `neutral-*` surface (xem `tailwind.config.js`) — KHÔNG hex thô, KHÔNG đổi sang indigo/purple "cho đẹp" (AI default).
- Spacing trên scale Tailwind (`p-3 gap-2`), KHÔNG `style="padding:13px"`. Border-radius nhất quán (đừng `rounded-2xl` mọi nơi).
- Component nhất quán: tái dùng `StatusBadge`/`BaseModal`/`BasePagination`/`PageHeader`/`ListFilterBar` từ `components/common/` thay vì dựng lại (trùng "Where to look").

**3. Component architecture** (tách container ↔ presentational, props rõ, 1 mục đích):
- **Container** = ListView/DetailView: gọi store/composable, giữ loading/error, KHÔNG nhồi markup row phức tạp.
- **Presentational** = card/row/badge trong `components/<domain>/`: nhận `props` typed (KHÔNG `any`), `emit` event ra ngoài, KHÔNG tự fetch — "dumb", tái dùng được.
- 1 component = 1 mục đích; > ~200 dòng → tách. Ưu tiên composition (`<PageHeader><slot/>`) hơn 1 component nuốt 15 prop config.

```vue
<!-- Container giữ data, Presentational chỉ render -->
<WorkOrderTable :rows="store.items" :loading="store.loading"
                @row-click="goDetail" @edit="edit" />
```

### `incremental-implementation` (thin vertical slice)

Build FE module theo **lát dọc mỏng**: `api/immXX.ts` (1 endpoint) → `stores/immXX.ts` (1 action) → 1 view (vd ListView) → chạy/verify → mới sang lát kế (DetailView, form). KHÔNG dựng toàn bộ UI (mọi view + mọi nút) rồi mới wire BE — mỗi lát phải chạy thật end-to-end trước khi mở rộng (trùng tinh thần Build sequence).

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE + file phiên mới nhất (curated; cần truy gốc chi tiết → đọc mục 🪞 Mirror của file phiên) — "đang dở ở đâu"; dữ liệu trong `.claude/contexts/` — gitignored; file phiên ở `sessions/<ngày>/`). Main session: hook tự nạp mỗi prompt + tự **mirror TOÀN BỘ lượt** (prompt+phản hồi+tool) vào file phiên qua hook `Stop`; subagent phải TỰ chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY: `STATE.md`(ghi đè) + bồi **semantic** vào file phiên (`session-log.sh current` → path; **KHÔNG còn LOG.md**). Hook `Stop` đã mirror nguyên văn → bạn CHỈ cần tóm Làm/Quyết-định/Để-lại. KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `.claude/contexts/` (STATE.md + sessions/<ngày>/); fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
