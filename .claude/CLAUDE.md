# .claude — AssetCore AI Workspace Configuration

This directory configures Claude Code for the AssetCore project.
Root project context is in `/CLAUDE.md` at the repo root.

---

## Slash Commands Available

### dev/

| Command | Use When |
| --- | --- |
| `/dev:build-workflow <DocType>` | Need a Frappe Workflow JSON for a new DocType |
| `/dev:write-test-case <feature>` | Need UAT test cases with full coverage |
| `/dev:implement-validation-rule <rule>` | Adding a business rule to backend + frontend |
| `/dev:scaffold-doctype <entity>` | Bootstrapping a new DocType with all files |
| `/dev:generate-api-contract <module>` | Producing OpenAPI spec for an API module |

### pm/

| Command | Use When |
| --- | --- |
| `/pm:backlog-prioritization <items>` | Need WSJF-scored prioritization for sprint planning |
| `/pm:sprint-breakdown <goal>` | Breaking a sprint goal into tasks with DoD |
| `/pm:risk-review <scope>` | Risk register for a feature or release |

### qms/

| Command | Use When |
| --- | --- |
| `/qms:draft-sop <process>` | Writing a new SOP (PR document) |
| `/qms:map-qms-document <module>` | Mapping a feature to QMS doc hierarchy |
| `/qms:build-audit-trail-check <DocType>` | Verifying audit trail completeness |
| `/qms:create-controlled-form <form>` | Specifying a BM (biểu mẫu) document |

### ba/

| Command | Use When |
| --- | --- |
| `/ba:draft-requirement <feature>` | Formal FR/NFR specification |
| `/ba:review-gap-analysis <scope>` | Gap between current state and requirement |
| `/ba:write-acceptance-criteria <story>` | Gherkin acceptance criteria |
| `/ba:build-traceability-matrix <module>` | RTM linking requirements → tests |
| `/ba:write-user-story <feature>` | User stories with acceptance criteria |

---

## Skills Available

| Skill | Trigger With |
| --- | --- |
| `/erpnext-doctype-designer` | Design complete DocType spec |
| `/dashboard-spec-writer` | Design KPI dashboard spec |
| `/asset-lifecycle-designer` | Design device lifecycle workflow |
| `/qms-mapper` | Map module to QMS requirements |

---

## Hooks (Manual Checklists)

Review before key actions — see `hooks/` directory:

- `before-coding.md` — before writing any new feature
- `before-closing-task.md` — before marking task done
- `before-merging.md` — before merging to master
- `before-writing-docs.md` — before creating documentation

---

## Key Patterns

**API responses:** always `_ok(data)` or `_err(message, code)` — never raw dict

**No logic in controllers** — controllers call service layer only

**Every action = a record** — no state change without a Lifecycle Event

**Vietnamese error messages** — all user-facing validation uses `frappe.throw(_("..."))`

**Naming prefix:** `ACC-` commissioning · `WO-` work order · `MP-` maintenance plan · `IR-` incident
