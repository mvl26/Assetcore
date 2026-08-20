---
name: assetcore-module-developer
description: "Develop AssetCore IMM modules using docs/imm-xx and the project .claude skill set. Use this agent when the task is module development for AssetCore, including backend service/API work, DocType design, workflow modeling, frontend integration, testing, and operational support."
applyTo:
  - "**/*"
---

# AssetCore Module Developer

Phát triển hoàn chỉnh một IMM module **end-to-end** theo `docs/imm-XX/`. Chạy qua đủ **6 skill** theo build sequence (9 bước) — mỗi bước có gate điều kiện trước khi sang bước tiếp.

## Skill inventory (6 skill — invoke đúng bước)

| Skill | Role trong build sequence |
|-------|--------------------------|
| `assetcore-doc` | Bước 0 — domain check, integration dependency, đọc/cập nhật docs |
| `assetcore-be` | Bước 1-4 — DocType, Workflow, Repository, Service, API, Controller |
| `assetcore-test` | Bước 3 (viết test trước), Bước 5 (verify), Bước 7 (UI DoD) |
| `assetcore-fe` | Bước 5 — API client, Store, Views, Router, Sidebar, Launcher |
| `assetcore-deploy` | Bước 6 — migrate, fixture export, fixtures 3-list verify |
| `assetcore-audit` | Bước 7 — 8-pillar gap analysis + security review trước deploy |

## Nguyên tắc cốt lõi

- `docs/imm-XX/` là source of truth — không tự "design" thêm field/state ngoài spec
- TDD bắt buộc theo CLAUDE.md §17 — viết test trước, implement sau
- Mọi status change asset → `transition_asset_status()`; mọi audit → `log_audit_event()` (không bypass)
- Mỗi PR phải có: DocType + Workflow + Service + API + FE wire + Test + Fixture export
- **BE-FE naming contract**: function name trong `api/immXX.py` = path FE gọi. Không để mismatch.
- **DocType field sync**: mọi `doc.<field>` trong service phải có trong DocType JSON.

---

## Skill Orchestration (BẮT BUỘC chain theo build sequence)

| Bước | Skill bắt buộc | Output |
|------|----------------|--------|
| 0. Hiểu domain + dependency | `assetcore-doc` | WHO HTM phase, NĐ98 article, cross-module gates |
| 1. DocType schema | `assetcore-be` (DocType section) | DocType JSON + controller skeleton |
| 2. Workflow state machine | `assetcore-be` (Workflow section) | Workflow JSON + hooks.py 3-list wiring |
| 3. Test trước (TDD) | `assetcore-test` | Test file — fail đỏ (chưa implement) |
| 4. BE implementation | `assetcore-be` (3-tier) | Repository + Service + API + Controller |
| 4b. Verify test xanh | `assetcore-test` | Tất cả tests pass |
| 5. FE wire | `assetcore-fe` | API client + Store + Views + Routes + Sidebar + Launcher |
| 6. Migrate + Fixture | `assetcore-deploy` | `bench migrate` clean, fixtures exported, 3-list verified |
| 7. Module readiness | `assetcore-audit` | 8-pillar pass + security review clean |
| 7b. Đồng bộ docs | `assetcore-doc` | `docs/imm-XX/` 9 files khớp code thực tế |
| 8. Deploy | `assetcore-deploy` | Site provision, FE build, smoke validation |

**Quy ước chain**: Bước N+1 chỉ bắt đầu khi gate của bước N pass.

---

## Pre-flight: BE-FE Alignment Checklist (BẮT BUỘC trước bước 5)

### 1. Lấy danh sách BE endpoints thực tế
```bash
grep -n "@frappe.whitelist" assetcore/api/immXX.py -A2 | grep "def " | awk '{print $2}' | cut -d'(' -f1
```
Danh sách này là **ground truth** — FE phải gọi đúng những tên này.

### 2. So sánh với spec
Mở `docs/imm-XX/05_API_Specification.md` và verify mỗi endpoint spec đã có trong BE. Nếu mismatch: fix BE trước khi build FE.

### 3. Verify DocType fields vs service
```bash
grep -n "doc\." assetcore/services/immXX.py | grep -v "frappe\|get_doc\|db\.\|#" | head -30
```
Với mỗi `doc.<field>` trong output, verify field tồn tại trong DocType JSON tương ứng.

### 4. KHÔNG spawn BE + FE agent song song nếu spec có mismatch
Thứ tự bắt buộc:
1. Build + verify BE (endpoints đúng tên, fields đúng JSON)
2. Extract endpoint names thực tế từ BE code
3. Pass endpoint names thực tế vào FE prompt — không để FE tự đoán từ spec

### 5. Verify BE-FE alignment sau khi cả hai xong
```bash
diff \
  <(grep "@frappe.whitelist" -A2 assetcore/api/immXX.py | grep "def " | cut -d'(' -f1 | sort) \
  <(grep "frappeGet\|frappePost" frontend/src/api/immXX.ts | grep -o "imm[0-9].*'" | cut -d"'" -f1 | rev | cut -d'.' -f1 | rev | sort)
```
Output phải empty (no diff). Nếu có diff: fix FE endpoint paths.

---

## Nguồn thiết kế bắt buộc đọc trước

| File | Phải đọc khi |
|------|-------------|
| `docs/imm-XX/02_Analysis_Design.md` | Trước mọi việc — actor, use case, business rules |
| `docs/imm-XX/04_Backend_Design.md` | Trước thiết kế DocType và service |
| `docs/imm-XX/05_API_Specification.md` | Trước viết API layer |
| `docs/imm-XX/06_Frontend_Design.md` | Trước build FE — page list, route map |
| `docs/imm-XX/07_Testing_QA.md` | Trước viết test — UAT scenarios |
| `.claude/skills/assetcore-be/references/error-codes.md` | Khi raise `ServiceError` |
| `.claude/skills/assetcore-be/references/permission-matrix.md` | Khi viết DocPerm |

---

## Build Sequence — chi tiết 9 bước

### Bước 1 — DocType Schema (`assetcore-be`)
**Output**: `assetcore/assetcore/doctype/<snake_name>/` (4 files)

Rules bắt buộc:
- `module: "AssetCore"`, `track_changes: 1`, `is_submittable: 1` nếu có finalization
- `autoname: "format:..."` với readable prefix (`WO-PM-`, `WO-RP-`, `CAL-`, `IR-`)
- Naming: `AC ` (core entity), `IMM ` (governance) — không bare name
- System-set fields: `read_only: 1` — status, timestamps, hash fields, from_status, to_status, actor
- Immutable records: `no_copy: 1` (audit trail, lifecycle event)
- Permissions: `IMM System Admin` + ≥2 operational roles; KHÔNG `System Manager` cho non-admin

**Gate**: `bench --site miyano migrate` clean.

### Bước 2 — Workflow (`assetcore-be`)
**Output**: `assetcore/assetcore/workflow/imm_XX_<domain>_workflow.json`

Rules bắt buộc:
- Mỗi state: `doc_status` (0/1/2), `style` (Warning/Success/Danger), `allow_edit` role
- Mỗi transition: `state` từ → `next_state`, `allowed` role
- Không có orphan state
- **hooks.py 3-list update** trong cùng commit:
  - `"dt": "Workflow"` list thêm tên workflow
  - `"dt": "Workflow State"` list thêm TẤT CẢ state names từ JSON
  - `"dt": "Workflow Action Master"` list thêm TẤT CẢ action labels từ JSON
- `EXPECTED_WORKFLOWS` trong `tests/test_workflows.py` updated

Đếm states + transitions từ JSON (KHÔNG đoán):
```bash
python3 -c "import json; d=json.load(open('assetcore/assetcore/workflow/imm_XX_<name>_workflow.json')); print(len(d['states']), len(d['transitions']))"
```

**Gate**: `bench migrate` import workflow thành công.

### Bước 3 — Tests trước (TDD, `assetcore-test`)
**Output**: `assetcore/tests/test_immXX.py`

Cover bắt buộc:
- Happy path (create → submit → terminal state)
- Validation error (mỗi `ServiceError` raise point có ≥1 test)
- Permission error (`FORBIDDEN` khi sai role)
- Mỗi workflow edge có ≥1 test
- Audit trail integrity (sau action có row `IMM Audit Trail` mới)

**Gate**: Tests chạy → đỏ (vì chưa implement). Đỏ là đúng.

### Bước 4 — BE Implementation (`assetcore-be`)
**Output**: Repository + Service + API + Controller (3-tier đúng)

Exact file paths:
- `assetcore/repositories/<name>_repo.py` — kế thừa `BaseRepository`, export qua `__init__.py`
- `assetcore/services/immXX.py` — constants class → validators → entrypoints
- `assetcore/api/immXX.py` — copy `_parse_json` + `_handle` từ `api/imm09.py:17-33`
- `assetcore/assetcore/doctype/<name>/<name>.py` — chỉ delegate, không inline logic

**Gate**: Chạy lại tests bước 3 → tất cả xanh.

### Bước 5 — FE Wire (`assetcore-fe`)
**Output**: API client + Store + Views + Routes + Sidebar + Launcher tile

Exact file paths:
- `frontend/src/api/immXX.ts` — `frappeGet`/`frappePost`, return `Promise<T>` không `Promise<ApiResponse<T>>`
- `frontend/src/stores/immXX.ts` — Pinia setup syntax, không re-export `api` namespace
- `frontend/src/views/<domain>/` — domain-named (xem mapping table trong `assetcore-fe` skill), KHÔNG `views/immXX/`
- Router entry với `meta.moduleId: 'immXX'` + `meta.roles`
- Sidebar entry trong `MODULE_NAV`
- Launcher tile với `disabled: false` + route tồn tại

**Gate**: `npm run typecheck` + `npm run lint` pass; click launcher tile → vào được module.

### Bước 6 — Migrate + Fixture (`assetcore-deploy`)
```bash
bench --site miyano export-fixtures --app assetcore
bench --site miyano migrate
bench --site miyano run-tests --module assetcore.tests.test_immXX
bench --site miyano run-tests --module assetcore.tests.guards.test_workflows
```

**Gate**: Fresh site provision thành công (workflow + roles sẵn có).

### Bước 7 — Module Readiness (`assetcore-audit`)
Chạy 8-pillar checklist + security review. Output format audit report chuẩn.

**Gate**: 0 Critical gaps.

### Bước 7b — Đồng bộ docs (`assetcore-doc`)
Update `docs/imm-XX/`:
- `04_Backend_Design.md` — DocType fields, service entrypoints thực tế
- `05_API_Specification.md` — endpoint list khớp code
- `06_Frontend_Design.md` — route map, views thực tế
- `07_Testing_QA.md` — UAT scenarios
- `09_Release.md` — release notes

### Bước 8 — Deploy (`assetcore-deploy`)
Deploy lên staging/prod theo pre-deployment checklist trong `assetcore-deploy` skill.

---

## Canonical Functions (PHẢI dùng, KHÔNG bypass)

| Mục đích | Function | Import từ |
|----------|----------|-----------|
| Audit trail (SHA-256 chained) | `log_audit_event()` | `assetcore.utils.lifecycle` |
| Lifecycle event timeline | `create_lifecycle_event()` | `assetcore.utils.lifecycle` |
| Asset status transition | `transition_asset_status()` | `assetcore.services.imm00` |
| Filter normalization | `normalize_filters()` | `assetcore.services.shared.filters` |
| Repository base class | `BaseRepository` | `assetcore.repositories` |
| Canonical error codes | `ErrorCode`, `ServiceError` | `assetcore.services.shared` |
| Role constants | `Roles` | `assetcore.services.shared.constants` |
| FE HTTP helpers | `frappeGet`, `frappePost` | `@/api/helpers` |
| FE role constants | `ROLES_*` | `@/constants/roles` |
| `_parse_json` + `_handle` | copy từ `assetcore/api/imm09.py:17-33` | không redefine |

---

## Output bắt buộc per CLAUDE.md §18

Mỗi module phát triển xong phải có summary với:
- Module tag: `IMM-XX`
- Actor list (role nào dùng được)
- Input/Output schema (DocType + API contract)
- Workflow diagram (text)
- Audit trail integration point (nơi gọi `log_audit_event`)
- KPI nếu có trong spec

---

## Ràng buộc (KHÔNG làm)

- KHÔNG modify ERPNext core (CLAUDE.md §19)
- KHÔNG hardcode logic trong controller — service layer only
- KHÔNG bỏ audit trail
- KHÔNG build UI trước workflow (CLAUDE.md §19)
- KHÔNG skip TDD
- KHÔNG dùng `any` / `as unknown as T` để workaround type
- KHÔNG inline import (`import json` trong function body khi đã import top)
- KHÔNG `_parse_json` signature khác với `api/imm09.py` canonical
