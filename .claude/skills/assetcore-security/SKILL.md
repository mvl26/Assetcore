---
name: assetcore-security
description: Audit and enforce security in AssetCore — RBAC role design, DocPerm, whitelist hygiene, audit trail, input validation, CSRF, secrets, vendor isolation, compliance (NĐ98 / WHO HTM). Use whenever the user asks about "phân quyền", "role", "permission", "audit trail", "GDPR", "compliance", "security review", "ai có quyền X", "vendor không được thấy Y", "SQL injection", "CSRF", "session timeout", "rò rỉ data", or any access-control question. Strongly use this skill for any review of @frappe.whitelist endpoints or DocPerm changes.
---

# AssetCore Security Reviewer & Builder

Healthcare equipment data is regulated (NĐ98/2021, WHO HTM, internal QMS). Security violations here can mean compliance findings, not just bugs. Be conservative; prefer deny-by-default.

## Threat model — what we defend against

1. **Privilege escalation** — a Technician triggers an admin-only action.
2. **Vendor data leakage** — Vendor Engineer of Hospital A sees data of Hospital B.
3. **Audit trail tampering** — actor backdates an event or deletes a lifecycle record.
4. **Session hijacking** — CSRF, stale token, missing httpOnly.
5. **Injection** — SQL via raw `frappe.db.sql`, XSS in user-entered descriptions rendered as HTML.
6. **Mass exfiltration** — unbounded `list_*` endpoint dumps the whole table.

## Two layers, both must be tight

### Layer 1 — Service-layer permission gate (source of truth)

Every mutating service function starts with a role check from `assetcore.services.shared.permissions`:

```python
from assetcore.services.shared.permissions import require_role
from assetcore.services.shared.constants import Roles

def assign_technician(name: str, *, technician: str):
    require_role(Roles.CAN_CREATE_WO, "Không đủ quyền giao việc")
    # ...
```

This is the only line that prevents an authenticated-but-wrong-role user from calling the endpoint. Never skip it.

### Layer 2 — DocPerm (desk navigation guardrail)

Configured in:
- DocType JSON `permissions: [...]` for primary roles.
- `assetcore/setup/setup_permissions.py` for fine-grained matrix (idempotent, code-driven).
- `assetcore/setup/setup_core_permissions.py` for ERPNext core DocTypes (File, ToDo, etc.) — uses `Custom DocPerm` overlay instead of editing core.

**DocPerm doesn't replace service checks** — it limits what desk shows and which records a query returns. API callers can bypass desk; service checks defend the API.

## Whitelist hygiene

Every public endpoint must satisfy ALL of:

```python
@frappe.whitelist(methods=["POST"])  # or ["GET"]
def do_action(name: str, payload: str = "{}") -> dict:
    return _handle(svc.do_action, name, _parse_json(payload, field_name="payload"))
```

| Check | Rule |
|---|---|
| Method restriction | `methods=["POST"]` for any state-changing action — prevents CSRF via image tag. Many existing endpoints don't yet declare this; when reviewing or touching, add it. |
| Authentication | `frappe.whitelist()` (no `allow_guest=True`) unless the endpoint is genuinely public |
| Service permission check | `require_role(...)` in the service function (canonical from `assetcore.services.shared.permissions`) |
| Input parsing | `_parse_json` for JSON params; `int()` / `bool()` for scalars (never trust client types) |
| Page-size cap | Read endpoints cap at 100 — `paginate()` already enforces it but the API layer should also clamp |
| Output via envelope | `_ok(...)` / `_err(...)` (or `@api_endpoint` decorator) — never return raw exceptions |

**`allow_guest=True` requires explicit user OK.** This is the single highest-risk decorator in the codebase.

### Two error envelope patterns — both are fine, neither leaks tracebacks

- **`_handle()` wrapping** (Pattern A in `assetcore-be-module`): catches `ServiceError`, returns envelope.
- **`@api_endpoint`** (Pattern B): catches Frappe exceptions (`DoesNotExistError` → 404, `PermissionError` → 403, `ValidationError` → 422 BUSINESS_RULE, `DuplicateEntryError` → 409, fallback → 500 with `frappe.log_error`).

Either pattern keeps stack traces out of the response body. **Never** add `try/except` that returns the raw exception text.

## Audit trail — SHA-256 chain, mandatory for state changes

`IMM Audit Trail` is a tamper-evident log: each row's `hash_sha256` is computed over `(asset, event_type, timestamp, actor, change_summary, prev_hash)`. Auditors verify integrity by re-walking the chain. **Never write to the table directly** — always go through the helper:

```python
from assetcore.utils.lifecycle import log_audit_event

log_audit_event(
    asset=asset_ref,                       # required
    event_type="document_approved",        # verb in past tense
    ref_doctype="Asset Document",
    ref_name=doc.name,
    from_status=DocStatus.PENDING,         # optional
    to_status=DocStatus.APPROVED,
    change_summary="Approved by {} after QA review".format(frappe.session.user),
    # actor defaults to frappe.session.user — only override in trusted background jobs
)
```

For combined "set asset status + write audit row in one shot":

```python
from assetcore.services.imm00 import transition_asset_status
from assetcore.services.shared import AssetStatus

transition_asset_status(asset_ref, AssetStatus.ACTIVE, root_record=wo_name)
```

**Audit trail rules:**
- DocPerm: `delete: 0` and `write: 0` for ALL roles except `IMM System Admin` (and even then, document the reason in a CAPA).
- Never `set_value` / `db.set_value` on an audit row after creation — that breaks the chain. If you need to correct something, write a new row with `event_type="audit_correction"` and reference the bad row in `change_summary`.
- `actor` defaults to `frappe.session.user`. Only override in scheduler jobs and background workers where there's no session — and even then, prefer the job-runner identity (e.g., `"system@scheduler"`).
- The `Asset Lifecycle Event` DocType (separate from `IMM Audit Trail`) is FE-facing timeline data — populate it when useful for the user-visible history, but it's NOT the compliance source of truth.

## Vendor Engineer isolation

`Roles.VENDOR_ENGINEER` is the highest-risk role: external user with desk access. Apply layered defense:

1. **DocPerm** — Vendor sees only DocTypes listed in `_ALL_DESK_ROLES` allowlist (File, ToDo, Comment, Tag — see `setup_core_permissions.py`). Forbidden by default elsewhere.
2. **Permission Query Conditions** — for DocTypes Vendor can read, filter rows in SQL:
   ```python
   # hooks.py
   permission_query_conditions = {
       "Asset Repair": "assetcore.permissions.repair_query_conditions",
   }
   ```
   ```python
   # assetcore/permissions.py
   def repair_query_conditions(user: str | None = None) -> str:
       user = user or frappe.session.user
       if "Vendor Engineer" in frappe.get_roles(user):
           vendor = frappe.db.get_value("User", user, "vendor_company")
           return f"`tabAsset Repair`.assigned_vendor = {frappe.db.escape(vendor)}"
       return ""
   ```
3. **Service-level check** — for any endpoint a Vendor can hit, verify the requested record belongs to them:
   ```python
   if not _vendor_can_see(wo, frappe.session.user):
       raise forbidden("Không có quyền xem WO này")
   ```

**Forbidden DocTypes for Vendor regardless of context:**
- `IMM Audit Trail`, `IMM CAPA Record`, `IMM Risk Register`, `IMM Internal Audit`
- Other vendors' work orders, contracts, performance reports
- Financial data: `Asset Depreciation Schedule`, `Budget Estimate Line`

If in doubt, deny.

## Input validation

| Source | Validate against |
|---|---|
| Link fields | Existence: `if not frappe.db.exists("AC Asset", asset_ref): raise not_found(...)` |
| Select / status | Whitelist: `if priority not in ("Normal", "Urgent", "Emergency"): raise validation(...)` |
| Numeric ranges | Bounds: `if qty < 0: raise validation("qty < 0 không hợp lệ")` |
| Datetimes | Future/past sanity: incidents can't be from 2099 |
| Free text | Length cap; sanitize before HTML render (FE uses `v-html` rarely; prefer interpolation) |

Never trust client-side validation alone — repeat every check on the server.

## SQL injection

The repository pattern uses `frappe.get_all` / `frappe.db.get_value` which parameterize automatically. **Don't bypass them.** When you must use raw SQL:

```python
# Good: parameterized
frappe.db.sql("SELECT name FROM `tabUser` WHERE email = %s", (email,))

# Good: %s placeholders for IN clauses with explicit list
placeholders = ", ".join(["%s"] * len(roles))
frappe.db.sql(f"... WHERE role IN ({placeholders})", roles)

# BAD — never do this
frappe.db.sql(f"SELECT name FROM `tabUser` WHERE email = '{email}'")
```

`frappe.db.escape(...)` exists but parameterization is preferred.

## CSRF

Frappe's CSRF protection requires a header `X-Frappe-CSRF-Token` on POST. The FE uses `src/api/axios.ts` which:
1. Caches token from login response.
2. Falls back to `csrf_token` cookie.
3. Retries once with `ping_session` if BE returns CSRF error.

**Never** disable CSRF on a whitelist (`@frappe.whitelist(allow_guest=True)` does — that's why guest endpoints need extra scrutiny).

## Secrets handling

- Never put API keys / DB passwords in code or fixtures.
- `frappe-bench/sites/<site>/site_config.json` is the right place for per-site secrets — it's gitignored.
- For shared dev secrets use `.env.local` (also gitignored). Don't paste them into chat.
- If a secret leaks into git history → rotate the secret first, then talk about scrubbing.

## Pagination & rate limits

Every `list_*` endpoint must paginate:

```python
@frappe.whitelist()
def list_things(filters: str = "{}", page: int = 1, page_size: int = 20):
    page_size = min(int(page_size), 100)  # cap to prevent dump
    return _handle(svc.list_things, _parse_json(filters, ...),
                   page=int(page), page_size=page_size)
```

`BaseRepository.list` already paginates via `assetcore.utils.pagination.paginate`. Just make sure the API enforces a max `page_size`.

## Compliance touchpoints

| Regulation | What it requires |
|---|---|
| NĐ98/2021 | UDI/serial tracking, vendor authorization, calibration records |
| WHO HTM | Lifecycle event traceability, decommissioning records |
| Internal QMS | CAPA, document control with version + approver, audit trail integrity |

Every DocType that holds compliance data must have `track_changes: 1` and an audit trail row on mutation.

## Security review checklist

For any PR touching auth, perms, whitelisted endpoints, or DocPerm:

- [ ] Service function starts with `require_role`
- [ ] Whitelist has `methods=["POST"]` if mutating
- [ ] No `allow_guest=True` (or it's documented why)
- [ ] Input parsed/validated before reaching DB
- [ ] Lifecycle event / audit trail written on success
- [ ] Vendor-accessible DocType has `permission_query_conditions` filter
- [ ] List endpoint caps `page_size`
- [ ] No raw SQL with f-string interpolation of user input
- [ ] DocPerm change exported via `bench export-fixtures` and committed
- [ ] Tests include at least one "wrong-role denied" case

## Where to look

- `assetcore/services/shared/permissions.py` — `require_role`, `has_any_role`, `is_admin`, `require_admin`, `require_user_mgmt`
- `assetcore/services/shared/constants.py` — `Roles` (19 roles incl. Wave 2), role groups, `ErrorCode` (canonical), `AssetStatus`, `ApprovalStatus`, `CalibrationStatus`
- `assetcore/services/shared/errors.py` — `ServiceError` + factories (`not_found`, `forbidden`, `validation`, `conflict`, `bad_state`)
- `assetcore/utils/api_endpoint.py` — `@api_endpoint` decorator (Pattern B)
- `assetcore/utils/lifecycle.py` — `log_audit_event` (SHA-256 chain on `IMM Audit Trail`)
- `assetcore/utils/response.py` — `_ok`, `_err`, legacy `ErrorCode`
- `assetcore/setup/setup_permissions.py` — runtime perm matrix (per IMM DocType)
- `assetcore/setup/setup_core_permissions.py` — ERPNext core DocPerm overlays (Custom DocPerm, no core edit)
- `assetcore/setup/setup_role_profiles.py`, `setup_module_profiles.py` — role bundling
- `assetcore/api/auth.py` — login, session, CSRF token, `ping_session`
- `frontend/src/api/axios.ts` — CSRF interceptor + retry-on-csrf-fail + 401 redirect
- `frontend/src/stores/auth.ts` — runtime role helpers (`hasRole`, `canCreate`, `canApprove`, …)
- `frontend/src/constants/roles.ts` — FE mirror of BE `Roles`
- `frontend/src/directives/permission.ts` — `v-permission` directive (DOM-removes element on missing role)
- `frontend/src/composables/usePermissions.ts` — legacy thin wrapper (new code should use `useAuthStore` directly)

---

## Cross-skill conventions

Read [`/.claude/skills/CONVENTIONS.md`](../CONVENTIONS.md) for project-wide rules. Especially relevant to this skill:

- §4. Audit & Lifecycle — IMM Audit Trail SHA-256 chain; verify chain integrity periodically
- §5. Permissions — 3 layers (DocPerm + query_conditions + service guard)
- §10. Forbidden — never write to IMM Audit Trail directly

### Module-specific gotchas
- Vendor isolation: use `permission_query_conditions` to filter rows by vendor
- IMM-16 BR-16-09 gate: Critical CAPA blocks new Work Order — implemented via `services.imm16.gate_wo_submit`
- Audit chain verification script: walk from root, recompute hash, compare to row hash; mismatch = tampering
