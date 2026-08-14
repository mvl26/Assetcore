# Notification & Error Framework — Giai đoạn 2 (Hoàn thiện)

> **Status (2026-05-25):** NOT STARTED. Giai đoạn 1 mới hoàn thành Phase 0–2 (BE foundation + FE composable + demo IMM-04). Phase 3–6 của giai đoạn 1 (seed catalog, migrate-all-modules, cleanup) chưa làm — phải làm trước khi mở giai đoạn 2.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Giai đoạn 1 đã merge — code-first registry `assetcore/utils/messages.py` + `frontend/src/locales/messages.ts` đang chạy production, mọi `frappe.throw` / `toast.error` hardcode đã được migrate. Tham chiếu: [2026-05-20-notification-error-standardization.md](./2026-05-20-notification-error-standardization.md).

**Goal:** Migrate registry từ code-first sang **DB-driven** với `Notification Template` doctype, cho phép BA chỉnh sửa câu chữ live (không cần deploy), bổ sung đa ngôn ngữ (vi/en), admin UI quản lý, audit trail thay đổi nội dung, và telemetry để biết message nào hay được trigger nhất.

**Non-Goals (giai đoạn 2):**
- KHÔNG mở rộng sang notification channel mới (email/SMS/push) — chỉ xử lý in-app UI message. Channel notification có module riêng (`assetcore.events.notify_handlers`).
- KHÔNG xoá hoàn toàn code-first — vẫn giữ làm **fallback offline-first** khi API/cache fail.
- KHÔNG hỗ trợ rich content (markdown, image, link external) trong message — giữ plain text + 1 action_hint string. Rich content nằm ở giai đoạn 3.
- KHÔNG approval workflow cho BA edit message — chỉ audit trail. Workflow approval là enhancement riêng.

**Architecture:**

```
┌──────────────────────────────────────────────────────────────────────┐
│   SOURCE OF TRUTH — Notification Template (DocType, MariaDB)          │
│   ┌──────────────┐    ┌──────────────────────┐    ┌──────────────┐   │
│   │ name (code)  │    │ Notification Locale  │    │ Notification │   │
│   │ severity     │ ─► │ (child table)        │ ─► │ Audit Log    │   │
│   │ http_status  │    │ (locale, title,      │    │ (versioned)  │   │
│   │ module       │    │  template,           │    └──────────────┘   │
│   │ enabled      │    │  action_hint)        │                       │
│   └──────────────┘    └──────────────────────┘                       │
└──────────────────────────────────────────────────────────────────────┘
        ↓ on_update hook                  ↓ on_update hook
┌──────────────────────────────┐    ┌──────────────────────────────┐
│  Redis Cache                 │    │  Audit append                │
│  KEY: ac_notif_dict::{locale}│    │  diff old/new fields         │
│  TTL: 1h (auto-invalidate on │    │                              │
│       template save)         │    │                              │
└──────────────────────────────┘    └──────────────────────────────┘
        ↓ load on session start         ↓ load on session start
┌──────────────────────────────────────────────────────────────────────┐
│  BE  format_message(code, ctx, locale=user.locale)                    │
│      lookup_message() reads Redis → fallback to code-first MESSAGES   │
│  FE  GET /api/method/assetcore.api.notify.get_dict?locale=vi          │
│      → Pinia store `notifyStore.messages`                             │
│      → localStorage persistence (offline cache, 24h)                  │
│      → fallback to bundled `i18n/messages.ts` if API + LS đều fail    │
└──────────────────────────────────────────────────────────────────────┘
        ↓                                            ↓
┌──────────────────────────┐               ┌──────────────────────────┐
│  Admin UI (FE)           │               │  Telemetry               │
│  /system/notifications   │               │  Event: notify.fire      │
│  list/edit/preview       │               │  Store: `Notification    │
│  role-restricted         │               │  Fire Log` (daily roll)  │
└──────────────────────────┘               └──────────────────────────┘
```

**Tech Stack:** Frappe v15 (Python 3.11), MariaDB, Redis, Vue 3 + TypeScript + Pinia, vue-i18n 9.x, TailwindCSS.

**Reference:**
- Giai đoạn 1: [plans/2026-05-20-notification-error-standardization.md](./2026-05-20-notification-error-standardization.md)
- Framework gốc Miyano: [docs/res/frameworks/miyano-error-framework.md](../frameworks/miyano-error-framework.md) §2.1–2.3
- Frappe v15 DocType patterns: `assetcore/assetcore/doctype/ac_user_profile/` (audit trail pattern); `assetcore/services/imm00.py` (Redis cache pattern).

---

## File Structure

### Backend (sửa)

- `assetcore/utils/messages.py` — refactor: `lookup_message()` query Redis trước, fallback static MESSAGES dict. Static dict giữ làm **golden seed** + **offline fallback**.
- `assetcore/utils/notify.py` — `nthrow()` truyền `locale=frappe.local.lang` xuống `format_message()`.
- `assetcore/hooks.py` — register `boot_session` (cho desk admin), scheduler `daily` để roll-up telemetry; thêm event hooks cho `Notification Template`.
- `assetcore/api/notify.py` — **NEW** (xem dưới).
- `frontend/src/api/axios.ts` — interceptor đọc thêm `locale` từ user store khi gọi API.

### Backend (tạo mới)

- `assetcore/assetcore/doctype/notification_template/notification_template.json` — DocType chính.
- `assetcore/assetcore/doctype/notification_template/notification_template.py` — controller: validate (code format, template variables), on_update (invalidate cache + audit), permissions.
- `assetcore/assetcore/doctype/notification_locale/notification_locale.json` — Child Table: 1 template có N locale.
- `assetcore/assetcore/doctype/notification_locale/notification_locale.py` — controller (validate template syntax).
- `assetcore/assetcore/doctype/notification_audit_log/notification_audit_log.json` — DocType audit, append-only.
- `assetcore/assetcore/doctype/notification_audit_log/notification_audit_log.py` — controller (immutable, deny delete trừ role System Manager).
- `assetcore/assetcore/doctype/notification_fire_log/notification_fire_log.json` — Single DocType daily roll-up: `{date, message_code, fire_count, last_user}`.
- `assetcore/assetcore/doctype/notification_fire_log/notification_fire_log.py` — controller + helper `record_fire(code)`.
- `assetcore/api/notify.py` — whitelist endpoints:
  - `get_dict(locale: str = "vi")` → trả toàn bộ messages dict cho FE bootstrap.
  - `preview(code, ctx, locale)` → render template preview cho admin UI.
  - `bulk_export(locale)` → export CSV/JSON cho BA edit offline.
  - `bulk_import(file, dry_run)` → import từ CSV/JSON, dry-run validation trước.
- `assetcore/services/notify_admin.py` — service layer cho admin operations.
- `assetcore/patches/v4_0/001_seed_notification_templates.py` — migrate static MESSAGES dict vào DocType.
- `assetcore/patches/v4_0/002_backfill_locale_en.py` — sinh placeholder `en` locale từ Google Translate hoặc TODO marker.
- `assetcore/tests/test_notification_registry.py` — unit test DocType CRUD + cache + locale fallback.
- `assetcore/tests/test_notify_api.py` — unit test API endpoints.
- `assetcore/fixtures/notification_template.json` — fixture seed data (export sau khi seed patch chạy).

### Frontend (sửa)

- `frontend/src/locales/messages.ts` — đổi thành **bundled fallback** (không phải primary). Generator vẫn chạy → vẫn commit; consumer chỉ dùng khi store empty.
- `frontend/src/composables/useNotify.ts` — `render()` đọc từ `notifyStore.messages[code]` trước; fallback `MESSAGES` bundled.
- `frontend/src/main.ts` — bootstrap: gọi `notifyStore.hydrate()` trước khi mount app.
- `frontend/src/stores/auth.ts` — sau `login()` thành công, gọi `notifyStore.refresh()` (locale có thể đổi theo user).
- `frontend/src/locales/index.ts` — `vue-i18n` setup: locale từ user profile, fallback `vi`.

### Frontend (tạo mới)

- `frontend/src/stores/notify.ts` — Pinia store:
  - `state`: `{ messages: Record<code, MessageEntry>, locale: string, lastSync: number, source: 'api'|'localStorage'|'bundled' }`.
  - `actions`: `hydrate()`, `refresh()`, `setLocale(l)`.
  - persistence: localStorage `ac:notify:dict:{locale}`, TTL 24h.
- `frontend/src/api/notify.ts` — typed wrapper cho `/api/method/assetcore.api.notify.*`.
- `frontend/src/views/system/NotificationAdminView.vue` — list view với search, filter theo module/severity/enabled.
- `frontend/src/views/system/NotificationEditView.vue` — form edit 1 template + N locale tab, preview live, history tab (audit log).
- `frontend/src/views/system/NotificationImportView.vue` — bulk import CSV/JSON wizard 4-step (giống ImportWizardView pattern).
- `frontend/src/components/system/NotificationPreview.vue` — render toast/modal preview với severity selector + sample context input.
- `frontend/src/router/index.ts` — thêm 3 route: `/system/notifications`, `/system/notifications/:code`, `/system/notifications/import`. Role guard `System Manager` hoặc `IMM Content Manager`.
- `frontend/src/views/system/sidebar.ts` (hoặc tương đương) — thêm menu item.
- `frontend/src/__tests__/stores/notify.spec.ts` — unit test store hydrate/refresh/fallback chain.
- `frontend/src/__tests__/views/NotificationAdminView.spec.ts` — component test.

### Docs (sync)

- `docs/imm-00/04_Backend_Design.md` — section "Notification Registry" với CRUD pattern.
- `docs/res/guides/usage-guide.md` — guide cho BA: cách edit message qua admin UI, preview, rollback.
- `CLAUDE.md` §15 — update note: messages giờ live trong DocType, code-first chỉ là fallback.

---

## Phase 1 — DocType + Schema

### Task 1.1: `Notification Template` DocType

**Files:**
- Create: `assetcore/assetcore/doctype/notification_template/notification_template.json`
- Create: `assetcore/assetcore/doctype/notification_template/notification_template.py`
- Create: `assetcore/assetcore/doctype/notification_locale/notification_locale.json`
- Create: `assetcore/assetcore/doctype/notification_locale/notification_locale.py`

- [ ] **Step 1: Viết failing test** `test_notification_registry.py::test_create_template_with_locales`.
- [ ] **Step 2: Schema `Notification Template`**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | Data (PK) | ✓ | `MSG.XXX` code, regex `^[A-Z][A-Z0-9-]+$`, max 50 |
| `module` | Select | ✓ | `SYS / AUTH / VAL / UI / IMM00..IMM16 / IMPORT / INVENTORY / PURCHASE` |
| `severity` | Select | ✓ | `error / warning / info / success / critical` |
| `http_status` | Select | ✓ | `200 / 400 / 401 / 403 / 404 / 409 / 422 / 500` |
| `enabled` | Check | — | default 1; disabled → fallback bundled |
| `description` | Small Text | — | internal note cho BA |
| `template_variables` | Table (Notification Variable) | — | declared variables `{name}` để validate ctx |
| `locales` | Table (Notification Locale) | ✓ | min 1 row (vi mandatory) |
| `tags` | Data | — | comma-sep: `pii, compliance, blocking` |

- [ ] **Step 3: Schema `Notification Locale`** (child table):

| Field | Type | Required |
|---|---|---|
| `locale` | Select | ✓ — `vi / en` (extensible) |
| `title` | Data | ✓ |
| `template` | Small Text | ✓ |
| `action_hint` | Small Text | — |

- [ ] **Step 4: Controller validate** (`notification_template.py`):
  - Code regex `^[A-Z]+[-_][A-Z0-9-]+$`.
  - Phải có locale `vi`.
  - Mọi `{var}` trong template phải xuất hiện trong `template_variables` (nếu khai báo).
  - `severity = critical` ⇒ `http_status ∈ {500, 422}` (rule UX).
- [ ] **Step 5: Permissions**:
  - `System Manager`: full.
  - `IMM Content Manager` (role mới — xem Task 1.4): read + write `template`, `locales`; KHÔNG được sửa `name`, `module`, `severity`, `http_status` (cấu trúc).
  - All other roles: read-only (cần để API `get_dict` chạy với mọi user).
- [ ] **Step 6**: Run test → green.

### Task 1.2: `Notification Audit Log` DocType

**Files:**
- Create: `assetcore/assetcore/doctype/notification_audit_log/notification_audit_log.{json,py}`

- [ ] **Step 1: Viết failing test** `test_audit_log_appended_on_template_save`.
- [ ] **Step 2: Schema**:

| Field | Type |
|---|---|
| `template_code` | Link → Notification Template |
| `field_changed` | Data |
| `locale` | Data |
| `old_value` | Long Text |
| `new_value` | Long Text |
| `changed_by` | Link → User |
| `changed_at` | Datetime |
| `change_type` | Select (`create / update / delete / enable / disable`) |

- [ ] **Step 3: Permissions**: read = `System Manager`, `IMM Content Manager`, `IMM Auditor`. write/delete = NONE (immutable). Implement `on_trash` → raise.
- [ ] **Step 4: Hook** trong `notification_template.py:before_save`: diff `_doc_before_save` vs current → append audit rows.
- [ ] **Step 5**: Run test → green.

### Task 1.3: `Notification Fire Log` (telemetry)

**Files:**
- Create: `assetcore/assetcore/doctype/notification_fire_log/notification_fire_log.{json,py}`

- [ ] **Step 1**: Single DocType với 1 child table `Notification Fire Daily`:

| Field | Type |
|---|---|
| `date` | Date |
| `template_code` | Data |
| `fire_count` | Int |
| `last_user` | Link → User |
| `last_fired_at` | Datetime |

- [ ] **Step 2: Helper `record_fire(code, user)`** trong `assetcore/utils/notify.py`:
  - Increment in-memory counter (frappe.local) trong request.
  - Hook `on_request_end` flush vào Redis sorted set `ac:notify:fire:{YYYY-MM-DD}`.
  - Daily scheduler `roll_up_fire_log` move Redis → DocType, clear Redis key.
- [ ] **Step 3**: Run test smoke — fire 10 lần, sau scheduler thấy 10 trong DocType.

### Task 1.4: Role mới `IMM Content Manager`

**Files:**
- Modify: `assetcore/fixtures/role.json` (hoặc nơi định nghĩa roles)
- Modify: `docs/res/rbac/role-redesign-module-based.md` — note role mới

- [ ] **Step 1**: Tạo role `IMM Content Manager` (chỉ edit content, không sửa logic/schema).
- [ ] **Step 2**: Gán DocPerm tới `Notification Template` (xem Task 1.1 step 5).
- [ ] **Step 3**: Export fixture, update RBAC doc.

---

## Phase 2 — Cache + API

### Task 2.1: Redis cache layer

**Files:**
- Modify: `assetcore/utils/messages.py`
- Modify: `assetcore/assetcore/doctype/notification_template/notification_template.py`

- [ ] **Step 1: Viết failing test** `test_cache_invalidated_on_template_save`.
- [ ] **Step 2: Implement cache**:

```python
# utils/messages.py
CACHE_KEY_TPL = "ac:notif:dict:{locale}"
CACHE_TTL = 3600

def _get_dict_from_cache(locale: str) -> dict | None:
    return frappe.cache().get_value(CACHE_KEY_TPL.format(locale=locale))

def _set_dict_to_cache(locale: str, data: dict) -> None:
    frappe.cache().set_value(CACHE_KEY_TPL.format(locale=locale), data, expires_in_sec=CACHE_TTL)

def _build_dict_from_db(locale: str) -> dict:
    rows = frappe.db.sql("""
        SELECT t.name, t.severity, t.http_status, t.module, t.enabled,
               l.title, l.template, l.action_hint
        FROM `tabNotification Template` t
        LEFT JOIN `tabNotification Locale` l ON l.parent = t.name AND l.locale = %s
        WHERE t.enabled = 1
    """, (locale,), as_dict=True)
    return {r.name: {...} for r in rows}

def get_dict(locale: str = "vi") -> dict:
    cached = _get_dict_from_cache(locale)
    if cached: return cached
    data = _build_dict_from_db(locale)
    _set_dict_to_cache(locale, data)
    return data

def lookup_message(code: str, locale: str | None = None) -> MessageEntry:
    locale = locale or (frappe.local.lang if frappe.local else "vi")
    db_dict = get_dict(locale)
    entry = db_dict.get(code)
    if entry: return entry
    # Fallback A: DB locale khác
    if locale != "vi":
        entry = get_dict("vi").get(code)
        if entry: return entry
    # Fallback B: bundled static MESSAGES (offline)
    return MESSAGES.get(code, MESSAGES[MSG.SYS_500])
```

- [ ] **Step 3: Invalidate hook** trong `notification_template.py`:

```python
def on_update(self):
    for loc in self.locales:
        frappe.cache().delete_value(CACHE_KEY_TPL.format(locale=loc.locale))

def on_trash(self):
    self.on_update()
```

- [ ] **Step 4**: Run test → green.

### Task 2.2: API endpoints `assetcore/api/notify.py`

**Files:**
- Create: `assetcore/api/notify.py`
- Create: `assetcore/services/notify_admin.py`

- [ ] **Step 1: Viết failing test** `test_notify_api.py` covering 4 endpoints + auth/RBAC.
- [ ] **Step 2: Implement `get_dict`** (public — mọi authenticated user):

```python
@frappe.whitelist()
def get_dict(locale: str = "vi") -> dict:
    return _ok({"locale": locale, "messages": messages_module.get_dict(locale)})
```

- [ ] **Step 3: Implement `preview`** (role-restricted):

```python
@frappe.whitelist()
def preview(code: str, context: str = "{}", locale: str = "vi") -> dict:
    _ensure_role(["System Manager", "IMM Content Manager"])
    ctx = _parse_json(context, {})
    title, message, entry = format_message(code, ctx, locale=locale)
    return _ok({"title": title, "message": message, "action_hint": entry.get("action_hint"),
                "severity": entry.get("severity")})
```

- [ ] **Step 4: Implement `bulk_export`** → trả CSV stream với cột `code, locale, title, template, action_hint, severity, http_status, module, enabled`.
- [ ] **Step 5: Implement `bulk_import`** → `dry_run=True` chỉ validate; `dry_run=False` commit qua `frappe.transaction`. Reuse `services/import_validators.py` pattern.
- [ ] **Step 6**: Run all tests → green.

### Task 2.3: Hook telemetry vào `format_message()`

**Files:**
- Modify: `assetcore/utils/messages.py`

- [ ] **Step 1**: Trong `format_message()`, sau khi lookup thành công, gọi `record_fire(code, user)` (Task 1.3 step 2) — wrapped trong try/except, KHÔNG được làm crash flow chính.
- [ ] **Step 2**: Test smoke: fire 5 lần → Redis counter = 5.

---

## Phase 3 — Frontend Consumer

### Task 3.1: Pinia store `notify`

**Files:**
- Create: `frontend/src/stores/notify.ts`
- Create: `frontend/src/api/notify.ts`

- [ ] **Step 1: Viết failing test** `stores/notify.spec.ts::hydrate populates messages from API, falls back to localStorage, then bundled`.
- [ ] **Step 2: Implement**:

```typescript
// stores/notify.ts
export const useNotifyStore = defineStore('notify', {
  state: () => ({
    messages: {} as Record<string, MessageEntry>,
    locale: 'vi' as string,
    lastSync: 0 as number,
    source: 'bundled' as 'api'|'localStorage'|'bundled',
  }),
  actions: {
    async hydrate() {
      const lsKey = `ac:notify:dict:${this.locale}`
      const ls = localStorage.getItem(lsKey)
      if (ls) {
        try {
          const parsed = JSON.parse(ls)
          if (Date.now() - parsed.ts < 24*3600*1000) {
            this.messages = parsed.data
            this.source = 'localStorage'
          }
        } catch { /* corrupt → ignore */ }
      }
      // Always try fresh fetch in background
      this.refresh().catch(() => {
        if (Object.keys(this.messages).length === 0) {
          // Last resort
          this.messages = BUNDLED_MESSAGES
          this.source = 'bundled'
        }
      })
    },
    async refresh() {
      const { messages } = await notifyApi.getDict(this.locale)
      this.messages = messages
      this.lastSync = Date.now()
      this.source = 'api'
      localStorage.setItem(`ac:notify:dict:${this.locale}`,
        JSON.stringify({ ts: this.lastSync, data: messages }))
    },
    async setLocale(l: string) {
      this.locale = l
      await this.refresh()
    },
  },
})
```

- [ ] **Step 3**: Run test → green.

### Task 3.2: Bootstrap + auth integration

**Files:**
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/stores/auth.ts`

- [ ] **Step 1**: Trong `main.ts`, sau khi mount Pinia trước `app.mount()`:

```typescript
const notify = useNotifyStore(pinia)
await notify.hydrate()
```

- [ ] **Step 2**: Trong `auth.ts:login()` success path:

```typescript
const notify = useNotifyStore()
notify.locale = user.locale ?? 'vi'
await notify.refresh()
```

- [ ] **Step 3**: Trong `auth.ts:logout()`: KHÔNG clear `notify.messages` (giữ cho login page render error nếu cần).

### Task 3.3: Refactor `useNotify` composable

**Files:**
- Modify: `frontend/src/composables/useNotify.ts`

- [ ] **Step 1: Viết failing test** `useNotify.spec.ts::render uses store messages, falls back to bundled`.
- [ ] **Step 2: Refactor `render()`**:

```typescript
function render(code: string, ctx: Record<string, unknown> = {}) {
  const store = useNotifyStore()
  const entry = store.messages[code] ?? BUNDLED_MESSAGES[code] ?? BUNDLED_MESSAGES[MSG.SYS_500]
  const message = entry.template.replace(/\{(\w+)\}/g, (_, k) => String(ctx[k] ?? `[${k}]`))
  return { ...entry, message }
}
```

- [ ] **Step 3**: Run test → green.

---

## Phase 4 — i18n Integration

### Task 4.1: Wire `vue-i18n` với notify store

**Files:**
- Modify: `frontend/src/locales/index.ts`
- Modify: `frontend/src/stores/notify.ts`

- [ ] **Step 1**: Confirm `vue-i18n` đã cài (`frontend/src/locales/index.ts:6` đã có import comment).
- [ ] **Step 2**: Khi `notify.setLocale(l)` chạy → cũng set `i18n.global.locale.value = l`.
- [ ] **Step 3**: Reverse — khi i18n locale đổi (từ language switcher) → trigger `notify.setLocale()`.

### Task 4.2: Language switcher UI

**Files:**
- Create: `frontend/src/components/common/LanguageSwitcher.vue`
- Modify: header/topbar component để mount switcher.

- [ ] **Step 1**: Component dropdown `vi / en`, persist chọn lựa vào `user.locale` qua API `assetcore.api.user.update_locale`.
- [ ] **Step 2**: Smoke test: đổi sang `en` → toast hiện tiếng Anh; refresh trang → vẫn `en`.

### Task 4.3: Backend `frappe.local.lang` propagation

**Files:**
- Modify: `assetcore/api/notify.py`
- Modify: `assetcore/utils/notify.py`

- [ ] **Step 1**: API `nthrow()` đọc `frappe.local.lang` (Frappe tự set từ header `Accept-Language` hoặc `User.language`).
- [ ] **Step 2**: Đảm bảo axios FE gửi `Accept-Language: vi` hoặc `en` theo `notify.locale`.
- [ ] **Step 3**: Test: BE response thay đổi message theo header.

### Task 4.4: Seed `en` locale

**Files:**
- Modify: `assetcore/patches/v4_0/002_backfill_locale_en.py`

- [ ] **Step 1**: Patch chạy idempotent: với mỗi template chỉ có `vi`, sinh thêm row `en` với `template = "[EN-TODO] " + vi.template` (placeholder).
- [ ] **Step 2**: BA review + dịch dần qua admin UI.
- [ ] **Step 3**: Test fixture export → fixture có cả 2 locale.

---

## Phase 5 — Admin UI

### Task 5.1: List view `/system/notifications`

**Files:**
- Create: `frontend/src/views/system/NotificationAdminView.vue`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Viết failing test** `NotificationAdminView.spec.ts::lists templates with filters`.
- [ ] **Step 2: Implement**:
  - Table cột: `code`, `module`, `severity` (badge), `vi.title`, `enabled` (toggle), `last_modified`, action menu (Edit / History / Disable).
  - Filter: search by code/title, dropdown module, dropdown severity, toggle enabled-only.
  - Pagination 50/trang.
  - Bulk action: enable/disable many.
- [ ] **Step 3**: Role guard route — chỉ `System Manager` + `IMM Content Manager`.
- [ ] **Step 4**: Add sidebar menu item dưới group "Hệ thống".
- [ ] **Step 5**: Run test → green.

### Task 5.2: Edit view `/system/notifications/:code`

**Files:**
- Create: `frontend/src/views/system/NotificationEditView.vue`
- Create: `frontend/src/components/system/NotificationPreview.vue`

- [ ] **Step 1: Viết failing test** edit form save → API called → toast success.
- [ ] **Step 2: Layout**:
  - Header: code (read-only), module, severity, http_status, enabled toggle.
  - Tabs: 1 tab per locale (`vi`, `en`, ...); button "+ Thêm ngôn ngữ".
  - Per tab fields: `title`, `template` (textarea với syntax highlight `{var}`), `action_hint`.
  - Right panel: **Preview live** — `NotificationPreview` component nhận `severity` + rendered text → mô phỏng toast/modal.
  - Variable explorer: parse `{...}` trong template → liệt kê → input sample value → preview render với data thật.
  - Bottom: tab "History" → list audit log entries cho template này, diff view.
- [ ] **Step 3**: Save button → call `/api/method/frappe.client.save` standard, BE controller auto-invalidate cache (Task 2.1 step 3).
- [ ] **Step 4**: Run test → green.

### Task 5.3: Bulk import view

**Files:**
- Create: `frontend/src/views/system/NotificationImportView.vue`

- [ ] **Step 1**: Reuse pattern `ImportWizardView` (xem skill `assetcore-import`).
- [ ] **Step 2**: Steps: Upload CSV → Pre-validate (call `bulk_import(dry_run=True)`) → Review errors → Commit.
- [ ] **Step 3**: Template CSV download button.

---

## Phase 6 — Migration from code-first

### Task 6.1: Seed patch

**Files:**
- Create: `assetcore/patches/v4_0/001_seed_notification_templates.py`
- Modify: `assetcore/patches.txt`

- [ ] **Step 1**: Patch chạy `post_install` + idempotent:

```python
def execute():
    from assetcore.utils.messages import MESSAGES, MSG
    for code, entry in MESSAGES.items():
        if frappe.db.exists("Notification Template", code):
            continue
        doc = frappe.new_doc("Notification Template")
        doc.name = code
        doc.module = _extract_module(code)
        doc.severity = entry["severity"]
        doc.http_status = entry["http_status"]
        doc.enabled = 1
        doc.append("locales", {
            "locale": "vi",
            "title": entry["title"],
            "template": entry["template"],
            "action_hint": entry["action_hint"],
        })
        doc.insert(ignore_permissions=True)
    frappe.db.commit()
```

- [ ] **Step 2**: Register trong `patches.txt` ở section thường (KHÔNG `pre_model_sync` — cần DocType đã tồn tại).
- [ ] **Step 3**: Test: chạy 2 lần → idempotent, không duplicate.

### Task 6.2: Fixture export

**Files:**
- Create: `assetcore/fixtures/notification_template.json`
- Modify: `assetcore/hooks.py` — thêm vào `fixtures` list

- [ ] **Step 1**: `bench --site assetcore.local export-fixtures` sau khi seed patch chạy.
- [ ] **Step 2**: Add filter trong `hooks.py:fixtures` chỉ export với `enabled = 1` để tránh ô nhiễm fixture với draft data BA tạo.
- [ ] **Step 3**: Cùng cho `notification_locale` (auto kèm parent).

### Task 6.3: Generator → consumer of DB

**Files:**
- Modify: `scripts/gen_fe_messages.py`
- Modify: `frontend/src/locales/messages.ts` (regen)

- [ ] **Step 1**: Generator giờ đọc từ DB (`frappe --site assetcore.local execute assetcore.api.notify.get_dict`) thay vì AST parse `messages.py`.
- [ ] **Step 2**: Fallback nếu Frappe không khả dụng → parse AST như cũ.
- [ ] **Step 3**: Output vẫn là `messages.ts` để FE bundle as offline fallback.
- [ ] **Step 4**: CI nightly regen + commit nếu drift > N entries.

### Task 6.4: Deprecate static `MESSAGES` dict

**Files:**
- Modify: `assetcore/utils/messages.py`

- [ ] **Step 1**: Thêm deprecation comment `# DEPRECATED: bundled fallback only — primary source is Notification Template DocType`.
- [ ] **Step 2**: Vẫn giữ — quan trọng cho offline (bench chạy mà Redis down, hoặc cold start trước khi DB load).
- [ ] **Step 3**: Tài liệu hóa flow: DB → Redis → static fallback.

---

## Phase 7 — Telemetry + Reporting

### Task 7.1: Daily roll-up scheduler

**Files:**
- Modify: `assetcore/hooks.py`
- Modify: `assetcore/utils/notify.py`

- [ ] **Step 1**: Đăng ký `scheduler_events.daily`:

```python
scheduler_events = {
  "daily": ["assetcore.utils.notify.roll_up_fire_log"],
}
```

- [ ] **Step 2**: Hàm `roll_up_fire_log()` đọc Redis sorted set hôm qua → upsert vào `Notification Fire Log`.
- [ ] **Step 3**: Test smoke.

### Task 7.2: Reporting view

**Files:**
- Create: `frontend/src/views/system/NotificationReportView.vue`

- [ ] **Step 1**: Bảng top-50 message code fire nhiều nhất 30 ngày qua + chart line theo ngày.
- [ ] **Step 2**: Filter by module, severity.
- [ ] **Step 3**: Insight: severity `error` nào fire > 100 lần/ngày → highlight (báo hiệu lỗi UX hệ thống cần fix).
- [ ] **Step 4**: Optional: export CSV.

---

## Rollout & Verification

### Strategy

- **Phase 1**: 1 PR — DocType + audit + telemetry schema. Migrate patches chạy đè data có sẵn (idempotent).
- **Phase 2**: 1 PR — cache + API. Feature flag `notify_use_db` mặc định **false** (vẫn dùng code-first).
- **Phase 3**: 1 PR — FE store + bootstrap + composable refactor. Cũng feature-flag.
- **Phase 4**: 1 PR — i18n + en seed (BA review batch dịch riêng).
- **Phase 5**: 2-3 PR — admin UI (list / edit / import tách nhỏ).
- **Phase 6**: 1 PR — seed + fixture + generator switch + flip feature flag `notify_use_db = true`.
- **Phase 7**: 1 PR — telemetry roll-up + report view.

### Feature flag (recommend)

Thêm cờ trong `assetcore/utils/notify.py`:

```python
USE_DB_REGISTRY = frappe.conf.get("notify_use_db", False)

def lookup_message(code, locale=None):
    if USE_DB_REGISTRY:
        return _lookup_from_db(code, locale)
    return MESSAGES.get(code, MESSAGES[MSG.SYS_500])
```

→ Flip per site qua `bench --site X set-config notify_use_db 1`. Cho phép pilot 1 site, verify rồi roll-out cluster.

### Verification per phase

| Phase | Verification |
|---|---|
| 1 | DocType CRUD test green; audit row sinh ra khi save; permissions block đúng |
| 2 | API `get_dict` < 50ms warm cache; cache invalidate trong < 1s sau save; test bulk_import dry-run trả error đúng schema |
| 3 | FE smoke: tắt mạng → vẫn render từ localStorage; xoá localStorage → fallback bundled; bật lại mạng → refresh thành công |
| 4 | Đổi locale `en` qua switcher → toast hiện tiếng Anh; BE response message cũng đổi theo Accept-Language |
| 5 | Manual UAT: BA edit `MSG.VAL_REQUIRED.action_hint` → save → FE toast next time hiện text mới (không cần deploy) |
| 6 | Sau flip flag: dashboard count `Notification Template` rows = `len(MESSAGES)`; flip rollback test (set 0 → static vẫn work) |
| 7 | Sau 1 ngày: Notification Fire Log có rows; top-N report hiển thị đúng |

### Rollback

- **Mọi phase**: `git revert` PR.
- **Phase 6 critical**: flip feature flag `notify_use_db = false` → BE quay về code-first ngay lập tức, không cần code change.
- **Cache corrupt**: `bench --site X execute frappe.cache.delete_keys --kwargs '{"prefix": "ac:notif:dict"}'`.
- **DB seed sai**: drop `Notification Template` records, re-run patch.

---

## Open Questions

1. **Locale storage**: lưu trong `User.language` (Frappe native) hay tạo `AC User Profile.preferred_locale` riêng? **Đề xuất**: dùng `User.language` để tận dụng `frappe.local.lang` tự động.
2. **Approval workflow cho content edit**: BA edit live có cần qua approver (vd `IMM Content Reviewer`)? Hiện plan chỉ có audit log. **Đề xuất giai đoạn 2**: KHÔNG; thêm khi vận hành thực tế cho thấy nhu cầu.
3. **Rich content** (markdown link / button): có cần render link "Liên hệ kế toán ext.102" thành `tel:` clickable không? **Đề xuất giai đoạn 3**: dùng MDX-lite hoặc whitelist `<a>` tag.
4. **Sync với external translation service**: tích hợp Crowdin / Lokalise để dịch đa ngôn ngữ không? **Đề xuất**: không cho giai đoạn 2 — `vi` + `en` đủ; mở khi onboard market thứ 3.
5. **Conflict resolution**: 2 BA cùng edit 1 template → ai win? Frappe có optimistic lock qua `modified` timestamp — đủ. Có cần soft lock UI ("Đang được sửa bởi X")? **Đề xuất**: KHÔNG cho giai đoạn 2; thêm khi có >5 content manager active đồng thời.
6. **Performance**: 200-500 templates × 2-5 locales = ~1-2.5k rows. Trả full dict mỗi login OK không (~50KB JSON)? **Đề xuất**: OK trong scale hiện tại; phân trang/lazy load khi vượt 10k entries.
7. **Audit retention**: giữ audit log bao lâu? Compliance yêu cầu N năm? **Đề xuất**: giữ vĩnh viễn cho đến khi vượt 100k rows → archive cold storage theo policy QMS hiện hành.

---

## Estimated effort

| Phase | Effort | Người |
|---|---|---|
| 1 | 3 ngày | 1 BE |
| 2 | 2 ngày | 1 BE |
| 3 | 2 ngày | 1 FE |
| 4 | 2-3 ngày | 1 FE + 1 BE |
| 5 | 4-5 ngày | 1 FE |
| 6 | 1-2 ngày | 1 BE |
| 7 | 2 ngày | 1 BE + 1 FE |
| **Tổng** | **~16-19 ngày** | 2-3 dev |

---

## Cross-reference với giai đoạn 1

| Giai đoạn 1 deferred / open | Resolved trong giai đoạn 2? |
|---|---|
| Q1: Doctype hook bypass (adapter vs subclass) | KHÔNG — giải pháp adapter đã chấp nhận, giai đoạn 2 không động đến |
| Q2: i18n full | ✅ Phase 4 |
| Q3: Error Registry doctype | ✅ Phase 1-2 (`Notification Template`) |
| Q4: Success notifications từ BE | ✅ Hybrid giữ nguyên — BE truyền `notify` trong `_ok({data, notify: {code, ctx}})` |
| Static `MESSAGES` dict | ✅ Giữ làm offline fallback (Task 6.4) |
| Generator `gen_fe_messages.py` | ✅ Reuse, đảo nguồn từ AST → DB (Task 6.3) |
| Lint guard `no-hardcoded-toast` | KHÔNG đụng — vẫn còn hiệu lực từ giai đoạn 1 |
