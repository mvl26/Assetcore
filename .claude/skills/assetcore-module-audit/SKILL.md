---
name: assetcore-module-audit
description: |
  Audit a complete IMM module end-to-end to verify production-readiness — checks BE 3-tier completeness, FE views, workflow JSON, fixtures, tests, docs, permissions, and audit trail wiring. Use whenever the user asks "is IMM-XX ready?", "release checklist for imm-xx", "audit module", "what's missing in IMM-XX", "module gap analysis", "kiểm tra module sẵn sàng", "module-XX hoàn chỉnh chưa", "thiếu gì cho IMM-XX". Strongly prefer this skill before any deployment of a new IMM module.
---

# AssetCore Module Audit

Run a structured 8-pillar audit on a single IMM-XX module to determine whether it is production-ready. This skill consolidates BE / FE / test / docs / security / devops / deploy criteria into one consistent gate.

## Purpose

IMM modules in AssetCore span 7+ layers (DocType, service, repo, API, workflow, FE, tests, docs). A "feature complete" claim is meaningless unless every layer is verified. This skill is the single checklist used before:

- Tagging a release (`v3.x.y`)
- Promoting a module from Wave-Planned → Wave-Live
- Cutting a deployment ticket per `assetcore-deployment`
- Closing a sprint that delivered an IMM-XX module

Complements (does NOT replace):
- `assetcore-be-module` (how to build BE)
- `assetcore-fe-module` (how to build FE)
- `assetcore-tester` (how to write tests)
- `assetcore-deployment` (how to ship)

This skill **only verifies** — it does not implement. If gaps exist, hand off to the relevant builder skill.

## When to invoke

Trigger phrases:
- "Is IMM-09 ready for production?"
- "Audit module IMM-06"
- "Release checklist for IMM-04"
- "What's missing in IMM-11?"
- "Kiểm tra module IMM-08 đã sẵn sàng chưa"
- "IMM-12 hoàn chỉnh chưa?"
- "Thiếu gì cho IMM-15?"
- "Module gap analysis for wave 2"

Concrete scenarios: pre-deployment review, sprint review, stakeholder demo prep, regulatory inspection prep.

## The 8-Pillar Audit Checklist

Run each pillar in order. A single 🔴 critical gap → module is **NOT READY**.

### Pillar 1 — DocTypes
- [ ] All required DocTypes exist under `assetcore/assetcore/doctype/<snake>/`
- [ ] Each DocType has `.json` + `.py` + `__init__.py`
- [ ] `module: "AssetCore"` in JSON
- [ ] `track_changes: 1` set
- [ ] `autoname` uses readable prefix (no hash naming)
- [ ] Status fields are `read_only: 1` AND `no_copy: 1`
- [ ] Controller hooks delegate to service (no inline logic)
- [ ] Naming follows `AC ` / `IMM ` convention (Wave 2+) — see `../CONVENTIONS.md` §1

### Pillar 2 — Service Layer
- [ ] `assetcore/services/imm<XX>.py` exists
- [ ] Imports `ErrorCode`, `ServiceError`, `Roles`, `AssetStatus` from `assetcore.services.shared`
- [ ] No hardcoded role names or status strings
- [ ] Module-local Status class (`PMStatus`, `RepairStatus`, etc.) for enums
- [ ] Permission gates at every mutating entrypoint (`require_role(...)`)
- [ ] Validators are pure (`validate_*(doc)`) and reusable from controllers
- [ ] No bare `except:` or `except Exception: pass`

### Pillar 3 — Repository Layer
- [ ] `assetcore/repositories/<name>_repo.py` exists
- [ ] Class extends `BaseRepository` and sets `DOCTYPE = "..."`
- [ ] Re-exported in `assetcore/repositories/__init__.py`
- [ ] No `frappe.db.*` calls in service layer (must go through repo)

### Pillar 4 — API Layer
- [ ] `assetcore/api/imm<XX>.py` exists
- [ ] Every public function `@frappe.whitelist()`
- [ ] Mutating endpoints declare `methods=["POST"]`
- [ ] Either `_handle()` wrapper OR `@api_endpoint` decorator (consistent within module)
- [ ] Returns the standard `{success, data}` / `{success: false, error, code}` envelope
- [ ] Endpoint signatures documented in `assetcore/api/README.md`

### Pillar 5 — Workflows
- [ ] `assetcore/assetcore/workflow/imm_<XX>_*.json` exists for every submittable DocType with >2 active states
- [ ] `document_type` field matches the actual DocType name
- [ ] Every state is reachable from the start state
- [ ] No state is a dead-end (except terminal Completed/Cancelled)
- [ ] `doc_status` values are valid (0=Draft, 1=Submitted, 2=Cancelled)
- [ ] `allow_edit` roles match the DocPerm matrix

### Pillar 6 — Frontend
- [ ] Pinia store at `frontend/src/stores/imm<XX>.ts`
- [ ] List view + detail view + (if applicable) form modal in `frontend/src/views/imm<XX>/`
- [ ] Router entries registered in `frontend/src/router/`
- [ ] TypeScript types in `frontend/src/types/imm<XX>.ts` mirror BE response shape
- [ ] API client functions in `frontend/src/api/imm<XX>.ts`
- [ ] All UI labels in Vietnamese (per `../CONVENTIONS.md` §6)

### Pillar 7 — Tests
- [ ] `assetcore/tests/test_imm<XX>.py` exists
- [ ] Service-level unit tests cover all entrypoints (happy + error paths)
- [ ] Workflow smoke test: full state-machine traversal
- [ ] Permission test: at least one role denied + one role allowed
- [ ] `bench --site <site> run-tests --module assetcore.tests.test_imm<XX>` passes

### Pillar 8 — Docs + Fixtures
- [ ] `docs/imm-<XX>/` contains all 9 standard files (overview, BR, data model, workflow, API, UI, test, deploy, runbook)
- [ ] Fixtures exported in `hooks.py` (workflows, roles, custom fields)
- [ ] `assetcore/fixtures/role.json` includes any new IMM roles
- [ ] `setup/install.py` creates required defaults (if any)

## Audit script template

Run this from the app root (`/home/miyano/frappe-bench/apps/assetcore`):

```bash
M=06   # module number — change me
echo "=== Pillar 1: DocTypes ==="
ls assetcore/assetcore/doctype/ | grep -E "^(imm_|asset_|incident_)" | head
echo
echo "=== Pillar 2: Service ==="
test -f assetcore/services/imm$M.py && echo "OK" || echo "MISSING service file"
grep -c "^def " assetcore/services/imm$M.py 2>/dev/null
grep -c "ServiceError" assetcore/services/imm$M.py 2>/dev/null
echo
echo "=== Pillar 3: Repository ==="
ls assetcore/repositories/*_repo.py | xargs grep -l "DOCTYPE" | head
echo
echo "=== Pillar 4: API ==="
test -f assetcore/api/imm$M.py && echo "OK" || echo "MISSING api file"
grep -c "@frappe.whitelist" assetcore/api/imm$M.py 2>/dev/null
grep -c 'methods=\["POST"\]' assetcore/api/imm$M.py 2>/dev/null
echo
echo "=== Pillar 5: Workflows ==="
ls assetcore/assetcore/workflow/ | grep "imm_$M" || echo "NO workflow files"
echo
echo "=== Pillar 6: Frontend ==="
ls frontend/src/stores/ 2>/dev/null | grep -i "imm$M"
ls frontend/src/views/ 2>/dev/null | grep -i "imm$M"
echo
echo "=== Pillar 7: Tests ==="
test -f assetcore/tests/test_imm$M.py && echo "OK" || echo "MISSING test file"
echo
echo "=== Pillar 8: Docs ==="
ls docs/imm-$M/ 2>/dev/null | wc -l   # expect 9
```

## Severity grading

Use this rubric when reporting findings — be explicit about severity per gap.

| Severity | Meaning | Examples |
|---|---|---|
| 🔴 Critical | Blocks production. Module is NOT READY. | Missing audit trail call, no permission gate, no test file, workflow has unreachable state |
| 🟠 High | Must fix before next sprint. | Hardcoded role string, `_handle` missing, FE label in English, no `methods=["POST"]` on mutating endpoint |
| 🟡 Medium | Tech debt — track in backlog, not blocking. | Duplicated `_normalize_filters`, redundant validator, missing 1 of 9 docs files |
| 🟢 Low | Style / polish. | Missing docstring on private helper, suboptimal field order in JSON |

## Output format

Always report findings in this structure:

```
# Audit: IMM-XX <Module Name>

## Verdict: NOT READY | READY WITH CAVEATS | READY

## Pillar Results
| # | Pillar       | Status | Critical Gaps |
|---|--------------|--------|---------------|
| 1 | DocTypes     | PASS   | -             |
| 2 | Service      | FAIL   | 2             |
| ...

## Critical Gaps (🔴)
- `assetcore/services/imm06.py:142` — uses hardcoded role string "IMM Workshop Lead" instead of `Roles.WORKSHOP_LEAD`
- `assetcore/tests/` — no `test_imm06.py` file exists

## High Priority (🟠)
- ...

## Medium / Low
- ...

## Recommendation
Hand off to `assetcore-tester` to add the missing test file before deploying.
```

Always cite **specific file paths and line numbers**. Vague findings are useless.

## Wave-specific notes

- **Wave 1 reference** — `IMM-09` (Asset Repair) is the gold-standard reference module. When auditing other modules, compare against IMM-09's structure.
- **Wave 2 LIVE** — IMM-01, IMM-02, IMM-03, IMM-06 (recently merged). Hold these to full 8-pillar standard.
- **Wave 3 PLANNED** — IMM-15 (Spare Parts), IMM-16 (Compliance/CAPA). Audits here are scaffolding-stage; expect Pillars 6–8 to be incomplete.
- **Wave 1 modules with no test file**: IMM-04, IMM-05, IMM-06, IMM-08, IMM-09, IMM-11, IMM-12 — known gap, log as 🔴 critical until closed.

## Common findings (from recent audits)

Recurring issues to look for first — these are present across multiple modules:

1. **Test coverage gap** — `test_imm<XX>.py` missing for 7+ Wave 1 modules
2. **`_normalize_filters` duplicated** in `services/imm08.py`, `services/imm09.py`, `services/imm11.py` — should live in `services/shared/filters.py`
3. **IMM-04 workflow state names** carry tech debt (mixed Vietnamese/English) — flag if you see "Đang lắp đặt" alongside "Installation"
4. **Hardcoded role strings** appear in older code — grep for `"IMM ` literal usage in `services/`
5. **Missing `methods=["POST"]`** on mutating endpoints (Pattern A modules)
6. **Audit trail gaps** — services that call `frappe.get_doc({...}).insert()` directly without a corresponding `log_audit_event(...)` from `assetcore.utils.lifecycle`

## Don'ts

- ❌ Don't claim "ready" without checking all 8 pillars — partial audits are worse than none
- ❌ Don't skip workflow state reachability check — unreachable states cause silent UAT failures
- ❌ Don't ignore Vietnamese label coverage on FE views — required by `../CONVENTIONS.md` §6
- ❌ Don't grade missing tests as 🟡 medium — TDD is mandatory per CLAUDE.md §17, this is always 🔴
- ❌ Don't audit two modules in one report — keep one report per IMM-XX for traceability

## References

- `../CONVENTIONS.md` — project-wide rules (naming, layers, error codes)
- `assetcore-be-module` — BE 3-tier reference
- `assetcore-fe-module` — FE structure reference
- `assetcore-tester` — test patterns
- `assetcore-deployment` — deployment gate
- `assetcore-security` — RBAC + audit trail review (run alongside this audit for high-risk modules)
- `assetcore/services/imm09.py` — gold-standard reference implementation
