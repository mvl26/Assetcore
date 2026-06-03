---
name: assetcore-audit
description: >
  Audit, tái cấu trúc và sửa lỗi AssetCore — kiểm tra production-readiness toàn module
  (BE 3-tier, FE views, workflow, fixtures, tests, docs, permissions, audit trail),
  đồng thời review security (RBAC, DocPerm, whitelist hygiene, SQL injection, CSRF,
  vendor isolation, compliance NĐ98/WHO HTM).
  Dùng khi user nói "audit module", "module IMM-XX sẵn sàng chưa", "thiếu gì",
  "module gap analysis", "release checklist", "kiểm tra module", "tái cấu trúc",
  "refactor", "code bị lỗi", "fix bug IMM-XX", "phân quyền sai", "permission", "role",
  "audit trail", "security review", "vendor không được thấy data", "SQL injection",
  "CSRF", "rò rỉ data", "compliance". Ưu tiên skill này trước mọi deployment module mới.
---
# AssetCore Audit — Module Readiness & Security

Skill này bao 2 nhiệm vụ: **Module Audit** (production-readiness) + **Security Review**.

---

## 🛑 Phần 0 — Recurring Bug Regression Sweep (chạy ĐẦU mọi audit)

5 phiên test 2026-05-15..26 vẫn để cùng pattern leak vào prod. Trước khi mở 8-pillar checklist, chạy `CONVENTIONS.md` §0 GATE-1..4 và liệt kê output trong audit report. Bất kỳ pattern nào < 100% clean = audit verdict không được Pass.

```bash
# Quick smoke (full version: CONVENTIONS.md §0)
cd /home/miyano/frappe-bench/apps/assetcore
echo "== English enum leak (GATE-1) =="
grep -rnE "\{\{\s*(row|item|doc)\.(status|workflow_state|frequency|severity)\s*\}\}" \
  frontend/src/views/<module>/ | grep -v "STATUS_LABEL\|FREQ_LABEL\|SEVERITY_LABEL"
echo "== Raw code leak (GATE-2) =="
# 2026-05-27 broadened: any var (row|item|doc|d|c|r|x) + device_model/asset_ref/category/etc.
grep -rnE '\{\{ ?[a-zA-Z_]+\.(asset|asset_ref|model|device_model|target_device_model|vendor|supplier|warehouse|department|technician|category|asset_category|location|user|trainer|owner)([^_a-zA-Z]|\}\})' \
  frontend/src/views/<module>/ frontend/src/components/<module>/ 2>/dev/null | grep -vE "_name|_full_name"
echo "== Raw email leak (GATE-3) =="
grep -rnE "\{\{\s*(row|item|doc)\.(technician|assigned_to|owner|created_by)\s*\}\}" \
  frontend/src/views/<module>/ | grep -v "_full_name\|_name"
echo "== Test data leak DB (GATE-4) =="
bench --site miyano console <<'PY'
import frappe
for dt in ["AC Asset","IMM Training Program","IMM Compliance Rule","PM Work Order","Asset Repair","IMM CAPA Record"]:
    rows = frappe.db.sql(f"SELECT name FROM `tab{dt}` WHERE name LIKE '_Test%' OR name LIKE 'TEST-%'", as_dict=True)
    if rows: print(dt, [r.name for r in rows])
PY
```

Audit report phải có section:

```
## 0. Recurring Bug Sweep
- GATE-1 English label leak: <N> findings (path:line)
- GATE-2 Raw code leak: <N> findings
- GATE-3 Raw email leak: <N> findings
- GATE-4 Test data DB: <N> findings
Verdict: PASS chỉ khi cả 4 = 0.
```

---

## Phần 1 — Module Audit (8-pillar checklist)

## NGUYÊN TẮC BẤT BIẾN — UI Completeness

### UC-1: Mọi module PHẢI có Create button

Mỗi list page phải có button tạo mới (không chỉ hiển thị danh sách). Kiểm tra:

- List view có "Tạo mới" / "+ New" / "+ [Tên bản ghi]" button
- Button gọi được modal hoặc navigate đến form mới
- Form tạo mới có đủ fields và submit được

**Ngoại lệ duy nhất**: các page chỉ đọc thuần túy (vd: audit trail, reports).

### UC-2: Mọi bản ghi PHẢI có trang chi tiết với workflow actions

Mỗi bản ghi trong list phải:

- Có link/button "Chi tiết" hoặc click row dẫn đến URL chi tiết (vd: `/capas/:id`)
- Trang chi tiết hiển thị tất cả fields
- Trang chi tiết có workflow action buttons phù hợp với state
- State transitions phải khép kín (Draft → Approved → Active → Closed; không để bản ghi "kẹt" ở một state không có action)

**Khi audit FE**: navigate đến trang chi tiết của 1 bản ghi ở mỗi state → verify buttons.

### UC-3: Asset detail — tất cả tabs phải có dữ liệu hoặc empty state rõ ràng

Trang `/assets/:id` có các tabs: Thông tin, Khấu hao, Lịch sử, KPI, Audit Trail. Mỗi tab phải:

- Hiển thị dữ liệu nếu có
- Hiển thị "Chưa có dữ liệu" rõ ràng nếu chưa có — không để trống hoàn toàn
- Widget Ngừng máy: hiển thị số liệu thực (0 nếu chưa có event, không blank)

### UC-4: Tất cả Link fields phải hiển thị human-readable name

Các trường Link hiển thị cho user phải dùng display name, không phải DocType ID:

- Vendor/Supplier: tên công ty, không phải `SUP-2026-XXXXX`
- Asset: asset_name || asset_code, không phải `ACC-ASS-2026-XXXXX`
- User: full_name, không phải `email@domain.com`
- Department: tên khoa, không phải mã khoa

BE phải enrich `*_name` trong response; FE dùng `x.xxx_name || x.xxx`.

### UC-5: Naming series PHẢI đúng format

DocType có naming series phải:

- `"naming_rule": "Naming Series"` (không phải `"Expression (old style)"`)
- `"autoname": "PREFIX-.YYYY.-.#####"` (không có `format:` prefix)
- Verify bằng cách tạo bản ghi mới và check tên trả về — nếu trả về literal `"PREFIX-.YYYY.-.#####"` thì sai

---

### Mục đích

Dùng trước:

- Tag release (`v3.x.y`)
- Promote module Wave-Planned → Wave-Live
- Cut deployment ticket
- Đóng sprint deliver IMM-XX

Skill này **chỉ verify** — không implement. Khi phát hiện gap, chuyển sang `assetcore-be`, `assetcore-fe`, `assetcore-test`, `assetcore-deploy`.

### 8 pillars audit

#### Pillar 1 — DocType schema

- [ ] `module: "AssetCore"` set
- [ ] `autoname` dùng prefix có ý nghĩa
- [ ] `track_changes: 1`
- [ ] Status fields: `read_only: 1` + `no_copy: 1`
- [ ] Timestamp fields: `read_only: 1` + `no_copy: 1`
- [ ] DocPerm đủ 2+ operational roles
- [ ] Không có field service dùng nhưng không có trong JSON

```bash
# Verify fields tồn tại
grep -n "doc\." services/immXX.py | grep -v "frappe\|get_doc\|db\." | head -20
```

#### Pillar 2 — Service layer

- [ ] 3-tier tách đúng (không có business logic trong API, không có HTTP trong service)
- [ ] Mọi mutating function có permission check ở đầu
- [ ] `require_role(...)` dùng constant từ `Roles`, không hardcode
- [ ] Không có `except: pass` hay `except Exception: pass`
- [ ] Không gọi `frappe.db.*` trực tiếp từ service (đi qua repo)

```bash
# Tìm bare except
grep -n "except:" services/immXX.py | grep -v "ServiceError\|Exception as\|frappe"
# Tìm direct DB calls trong service
grep -n "frappe\.db\." services/immXX.py | grep -v "set_value\|commit"
```

#### Pillar 3 — Repository

- [ ] `<Name>Repo(BaseRepository)` tồn tại
- [ ] Không có raw SQL trừ khi thực sự cần join phức tạp
- [ ] Import từ `assetcore/repositories/__init__.py`, không trực tiếp từ `_repo.py`

#### Pillar 4 — API layer

- [ ] Tất cả endpoints có `@frappe.whitelist()`
- [ ] Mutating endpoints có `methods=["POST"]`
- [ ] Function names khớp với `docs/imm-XX/05_API_Specification.md`
- [ ] Không có business logic trong API handlers
- [ ] Pagination params cast: `int(page)`, `int(page_size)`
- [ ] **Display name enrichment**: mọi `list_*` endpoint có Link field hiển thị → phải gọi `_enrich(items, field, doctype, display_field)` để thêm `*_name`; mọi `get_*` detail endpoint phải enrich tương tự (không chỉ list)

```bash
# Verify whitelist endpoints
grep -n "@frappe.whitelist" api/immXX.py
# Compare với spec
grep "endpoint\|POST\|GET" docs/imm-XX/05_API_Specification.md | head -20
# Tìm get_* endpoint thiếu enrich (trả frappe.get_doc().as_dict() nhưng có Link field user-visible)
grep -n "frappe.get_doc.*as_dict\|get_doc.*as_dict" api/immXX.py
```

#### Pillar 5 — Workflow

- [ ] Workflow JSON tồn tại trong `assetcore/assetcore/workflow/imm_XX_<name>_workflow.json`
- [ ] `name == workflow_name` trong JSON
- [ ] `is_active: 1` set
- [ ] docstatus transitions valid (`0→0`, `0→1`, `1→1`, `1→2` only)
- [ ] Workflow trong `hooks.py` fixtures — đủ CẢ 3 lists (Workflow + State + Action)
- [ ] `EXPECTED_WORKFLOWS` updated trong `tests/test_workflows.py`

```bash
# Verify 3 fixture lists — workflow name trong từng list phải match JSON
grep -A20 '"dt": "Workflow"' assetcore/hooks.py
grep -A50 '"dt": "Workflow State"' assetcore/hooks.py
grep -A30 '"dt": "Workflow Action Master"' assetcore/hooks.py

# Đếm states + transitions từ workflow JSON (không đoán)
python3 -c "import json; d=json.load(open('assetcore/assetcore/workflow/imm_XX_<name>_workflow.json')); print('states:', len(d['states']), 'transitions:', len(d['transitions']))"

# Verify tất cả state names trong hooks.py Workflow State list
python3 -c "import json; d=json.load(open('assetcore/assetcore/workflow/imm_XX_<name>_workflow.json')); [print(s['state']) for s in d['states']]"
```

#### Pillar 6 — FE (Frontend)

- [ ] `api/immXX.ts` — all functions typed `Promise<T>`, không `Promise<ApiResponse<T>>`
- [ ] `stores/immXX.ts` — Pinia setup syntax; không re-export API namespace
- [ ] Views: tri-branch `v-if="loading"` / `v-else-if="error"` / `v-else`
- [ ] `catch (e: unknown)` + `e instanceof Error ? e.message : String(e)` — không `catch (e: any)`
- [ ] Routes đúng trong `router/index.ts` với `meta.moduleId`
- [ ] Launcher tile `disabled: false` + route tồn tại

**FE Display Quality (bắt buộc kiểm tra):**

- [ ] **Display names, không phải system codes**: mọi trường Link hiển thị cho user phải dùng human-readable name, không phải DocType id:

  - Supplier/Vendor: dùng `supplier_name || supplier`, không phải `SUP-2026-XXXXX`
  - Asset: dùng `asset_name || asset`, không phải `ACC-ASS-2026-XXXXX`
  - User: dùng `full_name || user`, không phải `email@domain`
  - BE phải enrich `*_name` vào response; FE dùng pattern `x.xxx_name || x.xxx`
- [ ] **Status values FE = BE constants**: grep `_STATUS_*` trong service layer, verify mọi `STATUS_COLOR`, `STATUS_LABEL`, `allowed_transitions.includes(...)`, `canXxx computed` dùng ĐÚNG string đó

  - Lỗi hay gặp: FE dùng `"Under Investigation"` nhưng BE constant là `"In Progress"` → tất cả workflow buttons ẩn
- [ ] **`allowed_transitions.includes()` dùng exact BE string**: lấy từ `_VALID_TRANSITIONS` dict, không đặt tên thân thiện
- [ ] **Select options FE = DocType JSON options**: grep DocType JSON field `options`, so với `<select>` options trong form — mismatch gây validation error
- [ ] **`useFormDraft` cache**: sau khi fix options, test với fresh browser session hoặc clear localStorage — draft cache giữ giá trị cũ không hợp lệ
- [ ] **Sidebar không che content**: test viewport ≥ 1280px; sidebar fixed z-40 intercept clicks ở viewport nhỏ
- [ ] **Role gating KHÔNG dùng `ROLES_*` constants** (deprecated, LL-FE-12):

  ```bash
  grep -rn "hasAnyRole.*ROLES_\|from '@/constants/roles' import.*ROLES_" frontend/src/views/
  # Match = 0 (trừ admin/role-picker pages)
  ```

  Mọi gate UI phải qua `useCapabilities().can('<domain>.<ptype>')`.
- [ ] **Workflow TRANSITIONS map cover ALL states** (LL-FE-10):

  ```bash
  states_be=$(grep -cE "^\s+_STATUS_\w+\s*=" assetcore/services/<module>.py)
  states_fe=$(grep -cE "'\w[\w ]*':\s*\[" frontend/src/views/<domain>/<X>DetailView.vue)
  # states_fe phải = states_be - terminal_count
  ```
- [ ] **TypeScript union sync BE states** (LL-FE-11): mỗi `_STATUS_*` ở service phải xuất hiện trong `export type XxxStatus = ...` ở `types/<module>.ts`.
- [ ] **Form Link fields dùng SmartSelect, không text** (LL-FE-9):

  ```bash
  # List Link fields trong DocType
  grep -B1 -A3 '"Link"' assetcore/assetcore/doctype/<dt>/<dt>.json | grep fieldname
  # Cho mỗi field name trên, kiểm tra trong form view:
  grep -E "<input.*v-model=\"form\.<field>\"" frontend/src/views/<domain>/*.vue
  # = 0 match (phải là SmartSelect)
  ```
- [ ] **List page có hành động khả thi** (LL-FE-13): list không có create button → phải có ít nhất 1 navigate/import/bulk action button. Empty state phải actionable.
- [ ] **KHÔNG dùng `window.confirm/alert/prompt`** (LL-FE-14):

  ```bash
  grep -rn "window\.confirm\|\bconfirm(\|\balert(\|\bprompt(" frontend/src/views/
  # = 0 match — dùng <BaseModal>
  ```
- [ ] **Rich-text field render qua sanitizeHtml** (LL-FE-15):

  ```bash
  grep -rn 'v-html=' frontend/src/views/ | grep -v sanitizeHtml
  # = 0 match
  ```
- [ ] **Delete button chỉ ở Draft state** (LL-FE-16): mọi `@click="doDelete"` phải có `v-if` check `workflow_state === 'Draft'`. Sau Draft dùng Cancel/Close.
- [ ] **Dashboard KPI khớp list filter** (LL-FE-17): click KPI → navigate list với cùng filter, count phải match.
- [ ] **BE user-initiated service có UI button** (LL-FE-18): mỗi `run_*/generate_*/scan_*/trigger_*` endpoint phải có button FE gọi được.
- [ ] **Test data KHÔNG leak production** (LL-FE-19):

  ```bash
  bench --site miyano mariadb -e "SELECT name FROM \`tabIMM Training Program\` WHERE name LIKE '\\_Test%' OR name LIKE 'TEST-%';"
  # = 0 rows
  ```
- [ ] **Computed field render đúng** (LL-FE-20): row hiển thị "—" trong cột có thể compute từ source data → bug.

**UI Completeness (bắt buộc audit):**

- [ ] **List page có Create button**: không có → 🟠 HIGH gap
- [ ] **Detail page có workflow buttons**: mỗi non-terminal state phải có ≥ 1 action button → không có → 🔴 CRITICAL (user bị kẹt)
- [ ] **KPI/stats tabs có data thực**: nếu có work orders nhưng uptime = 0/null → 🟠 HIGH (KPI service broken)
- [ ] **Audit trail tab hiển thị events**: empty khi có actions → 🟠 HIGH
- [ ] **Tabs không empty giả**: tất cả tabs phải fetch từ API, không hardcode empty

**Procurement Plans — kiểm tra thêm:**

- [ ] `/procurement-plans` list page có Create button → tạo plan mới được
- [ ] Detail page `/procurement-plans/:id` có đủ: tổng ngân sách, tỷ lệ sử dụng (allocated/budget), danh sách NR đã gắn vào plan
- [ ] Tỷ lệ sử dụng không hiển thị 0% khi đã có NR gắn vào plan — nếu 0% → kiểm tra BE roll-up logic
- [ ] Workflow buttons đúng state: Draft → Submit → Approve → Active → Close

**Asset Detail — kiểm tra thêm:**

- [ ] Tab Thông tin: tất cả fields điền đầy đủ, vendor hiển thị tên công ty (không mã SUP-XXXX)
- [ ] Tab Khấu hao: hiển thị schedule nếu purchase_price ≠ 0; hiển thị "Chưa có dữ liệu" nếu chưa nhập giá
- [ ] Tab Lịch sử: ít nhất 1 lifecycle event sau khi asset được tạo/cài đặt
- [ ] Tab KPI: uptime%, MTBF, MTTR hiển thị số liệu hoặc "Chưa đủ dữ liệu để tính" — không để trống hoàn toàn
- [ ] Widget Ngừng máy: hiển thị "0 sự kiện ngừng máy" nếu chưa có downtime log (không blank, không error)
- [ ] Audit Trail tab: có ít nhất 1 entry từ lúc tạo asset — empty hoàn toàn → 🟠 HIGH

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
# Grep để verify status strings:
grep -n "_STATUS_\|STATUS_COLOR\|STATUS_LABEL\|allowed_transitions" services/immXX.py views/immXX/*.vue
```

#### Pillar 7 — Tests

- [ ] `test_immXX.py` tồn tại
- [ ] Mỗi BR-XX-NN có ≥ 1 happy + 1 negative test
- [ ] Workflow smoke test pass
- [ ] Tests chạy được trên fresh site

```bash
bench --site miyano run-tests --module assetcore.tests.test_immXX
bench --site miyano run-tests --module assetcore.tests.test_workflows
```

#### Pillar 8 — Docs & Audit trail

- [ ] `docs/imm-XX/` có đủ 9 files (README + 02→09)
- [ ] `07_Testing_QA.md` có bảng UAT scenarios
- [ ] Mọi state transition gọi `log_audit_event(...)` — không bypass
- [ ] Không có module-local `_log_audit` hay `_create_lifecycle_event` (phải dùng canonical)

**Realistic data check (dùng trong UAT, không chỉ unit test):**

- [ ] Test data dùng tên thiết bị y tế thực, không phải "_Test", "sample"
- [ ] Work orders có complete fields: asset, technician, description thực tế
- [ ] KPI/stats được generate từ data thực (không mock 0)
- [ ] Audit trail có events thực sau khi tạo/sửa/chuyển trạng thái

### Severity grading

- 🔴 **Critical** — app crashes, data corruption, security hole. Block release.
- 🟠 **High** — feature broken hoặc audit gap. Fix before Wave goes Live.
- 🟡 **Medium** — UX degraded, missing validation. Fix in next sprint.
- 🟢 **Low** — code smell, doc gap. Backlog.

### Audit report format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Module Audit — IMM-XX
  Date: YYYY-MM-DD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pillar 1 DocType   : ✅ / ❌ [gaps]
Pillar 2 Service   : ✅ / ❌ [gaps]
Pillar 3 Repo      : ✅ / ❌ [gaps]
Pillar 4 API       : ✅ / ❌ [gaps]
Pillar 5 Workflow  : ✅ / ❌ [gaps]
Pillar 6 FE        : ✅ / ❌ [gaps]
Pillar 7 Tests     : ✅ / ❌ [gaps]
Pillar 8 Docs/Audit: ✅ / ❌ [gaps]

VERDICT: ✅ PRODUCTION-READY / ❌ NOT READY
Critical gaps: [list]
Action items: [list với owner]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phần 2 — Security Review

### Threat model

1. **Privilege escalation** — Technician trigger admin-only action
2. **Vendor data leakage** — Hospital A thấy data Hospital B
3. **Audit trail tampering** — backdating hoặc xóa lifecycle record
4. **Session hijacking** — CSRF, stale token
5. **Injection** — SQL via raw `frappe.db.sql`, XSS in descriptions
6. **Mass exfiltration** — unbounded list endpoint dump toàn bộ table

### Security checklist

#### Layer 1 — Service permission gate

```python
from assetcore.services.shared.permissions import require_role
from assetcore.services.shared.constants import Roles

def assign_technician(name: str, *, technician: str):
    require_role(Roles.CAN_CREATE_WO, "Không đủ quyền giao việc")
    # ...
```

- [ ] Mọi mutating service function có `require_role(...)` ở đầu
- [ ] Roles từ `Roles` constant, không hardcode string
- [ ] Permission check TRƯỚC khi đọc record (không để data leak qua error message)

#### Layer 2 — DocPerm (defense in depth)

```bash
# Verify permissions trong JSON
grep -A10 '"permissions"' assetcore/assetcore/doctype/<name>/<name>.json
```

- [ ] `delete: 0` cho mọi role trên audit trail DocTypes
- [ ] Không có `System Manager` trong non-admin DocType permissions
- [ ] `read: 1` tối thiểu cho operational roles

#### Whitelist hygiene

```bash
# Tìm endpoints thiếu permission gate
grep -B2 "@frappe.whitelist" api/immXX.py | grep -v "require_role\|#"
```

- [ ] Mọi POST endpoint có `methods=["POST"]`
- [ ] Mọi endpoint đọc data nhạy cảm có `require_role` hoặc filter theo `frappe.session.user`
- [ ] Pagination params bounded: `min(int(page_size), 200)` — không cho dump unlimited

#### Audit trail integrity

```bash
# Tìm bypass (insert trực tiếp thay vì log_audit_event)
grep -rn "doctype.*IMM Audit Trail" assetcore/ | grep -v "log_audit_event\|test_"
```

- [ ] Không có code insert `IMM Audit Trail` trực tiếp
- [ ] Không có `frappe.delete_doc("IMM Audit Trail", ...)` ngoài test teardown
- [ ] `delete: 0` trong DocPerm cho `IMM Audit Trail`

#### Input validation & Injection

```bash
# Tìm raw SQL với string interpolation
grep -n "frappe\.db\.sql" assetcore/ -r | grep -v "?.*%s\|:%(.*)" | grep "%\|format\|f\""
```

- [ ] Raw SQL dùng parameterized queries (`%s`, không f-string)
- [ ] User-entered text không render as HTML (escape hoặc dùng Jinja `{{ value | e }}`)
- [ ] File upload qua `@frappe.whitelist(methods=["POST"])` với MIME type check

#### Vendor isolation (multi-tenant)

```python
# Mọi list query phải filter theo tenant
filters["hospital_site"] = frappe.local.site
# Hoặc check ownership:
if doc.created_by_hospital != frappe.local.site:
    frappe.throw("Không có quyền truy cập")
```

- [ ] Mọi `list_*` endpoint filter theo `hospital_site` hoặc user scope
- [ ] Vendor Engineer không thấy data của hospital khác

### Security report format

```
Security Review — IMM-XX / [endpoint/feature]
🔴 CRITICAL: [issue + exploit path + fix]
🟠 HIGH: [issue + fix]
🟡 MEDIUM: [issue + fix]
Verdict: SECURE / NEEDS FIX
```

---

## Khi nào dùng skill nào tiếp theo

| Audit phát hiện                  | Skill tiếp          |
| ---------------------------------- | -------------------- |
| BE layer gap (service, repo, API)  | `assetcore-be`     |
| FE layer gap (views, store, types) | `assetcore-fe`     |
| Test missing                       | `assetcore-test`   |
| Deployment issue                   | `assetcore-deploy` |
| Doc gap                            | `assetcore-doc`    |

---

## Lessons Learned — audit checklist mở rộng (BẮT BUỘC ĐỌC khi audit)

> ⚠️ Các regression class **A–L**, **LL-AUDIT-1..7** (backend/FE/UI checks, anti-false-positive,
> DocType cross-ref, derived field, dangling FK, slug-in-display, hydration, ROLES stub,
> permission-denied UI, label sync, raw-code leak…) đã chuyển sang
> [`references/lessons-learned.md`](references/lessons-learned.md).
>
> **BẮT BUỘC: `Read references/lessons-learned.md` TRƯỚC KHI chốt verdict audit/security.**
> Bỏ qua = bỏ sót bug đã biết hoặc log false-positive.

## Phần 3 — Data Hygiene Audit (pre-release MUST-CHECK)

Áp dụng trước mỗi release tag, deploy lên staging/prod, hoặc khi user nói "data có sạch không".

### DH-1: 0 record chứa pattern test trong production-bound site

```bash
bench --site <site> mariadb -e "
SELECT 'AC Asset' AS dt, COUNT(*) FROM \`tabAC Asset\`
  WHERE LOWER(name) LIKE '%test%' OR LOWER(asset_name) LIKE '%test%'
UNION ALL SELECT 'AC Warehouse', COUNT(*) FROM \`tabAC Warehouse\`
  WHERE LOWER(name) LIKE '%test%' OR LOWER(warehouse_name) LIKE '%test%'
UNION ALL SELECT 'AC Spare Part', COUNT(*) FROM \`tabAC Spare Part\`
  WHERE LOWER(name) LIKE '%test%' OR LOWER(part_name) LIKE '%test%'
UNION ALL SELECT 'IMM Training Session', COUNT(*) FROM \`tabIMM Training Session\`
  WHERE training_program LIKE '\\_TEST-%'
UNION ALL SELECT 'IMM Training Program', COUNT(*) FROM \`tabIMM Training Program\`
  WHERE name LIKE '\\_TEST-%' OR LOWER(program_name) LIKE '%test%'
UNION ALL SELECT 'IMM CAPA Record', COUNT(*) FROM \`tabIMM CAPA Record\`
  WHERE LOWER(_comments) LIKE '%test%' OR LOWER(_comments) LIKE '%_test%';"
```

Tất cả phải = 0. Nếu > 0 → `assetcore-deploy` Phần 3 cleanup checklist.

### DH-2: 0 orphan FK reference

Sau cleanup, masters bị xoá có thể để lại dependents trỏ NULL:

```sql
SELECT 'ALE orphan asset' AS chk, COUNT(*) FROM `tabAsset Lifecycle Event`
WHERE asset IS NOT NULL AND asset != '' AND asset NOT IN (SELECT name FROM (SELECT name FROM `tabAC Asset`) x)
UNION ALL SELECT 'Audit Trail orphan asset', COUNT(*) FROM `tabIMM Audit Trail`
WHERE asset IS NOT NULL AND asset != '' AND asset NOT IN (SELECT name FROM (SELECT name FROM `tabAC Asset`) x)
UNION ALL SELECT 'Spare Stock orphan part', COUNT(*) FROM `tabAC Spare Part Stock`
WHERE spare_part IS NOT NULL AND spare_part != '' AND spare_part NOT IN (SELECT name FROM (SELECT name FROM `tabAC Spare Part`) x)
UNION ALL SELECT 'Asset orphan category', COUNT(*) FROM `tabAC Asset`
WHERE asset_category IS NOT NULL AND asset_category != '' AND asset_category NOT IN (SELECT name FROM (SELECT name FROM `tabAC Asset Category`) x);
```

Tất cả phải = 0.

### DH-3: 0 record vi phạm required-field constraint

```python
# assetcore/_scan_incomplete.py
import frappe

def run():
    modules = frappe.get_all("Module Def", filters={"app_name": "assetcore"}, pluck="name")
    doctypes = [d.name for d in frappe.get_all("DocType",
                filters={"module": ["in", modules]},
                fields=["name", "istable", "issingle"])
                if not d.istable and not d.issingle]
    skip = {"naming_series", "amended_from"}
    for dt in doctypes:
        meta = frappe.get_meta(dt)
        reqd = [f.fieldname for f in meta.fields
                if f.reqd == 1 and f.fieldname not in skip
                and frappe.db.has_column(dt, f.fieldname)
                and f.fieldtype not in ("Table", "Table MultiSelect",
                                         "Section Break", "Column Break", "HTML")]
        for f in reqd:
            cnt = frappe.db.sql(
                f"SELECT COUNT(*) FROM `tab{dt}` WHERE `{f}` IS NULL OR `{f}` = ''"
            )[0][0]
            if cnt:
                print(f"  {dt}.{f}: {cnt} empty")
```

```bash
bench --site <site> execute assetcore._scan_incomplete.run
```

Pre-release: phải = 0 cho field reqd=1.

### DH-4: 0 record có docstatus mismatch với workflow_state

```sql
-- Submitted nhưng còn ở Draft, Cancelled mà chưa Cancel
SELECT name, docstatus, workflow_state
FROM `tabAsset Repair`
WHERE (docstatus = 1 AND workflow_state IN ('Draft', 'Open'))
   OR (docstatus = 2 AND workflow_state NOT IN ('Cancelled'));
```

### Audit verdict — thêm row Data Hygiene

| Item                                       | Check            | Tool              |
| ------------------------------------------ | ---------------- | ----------------- |
| DH-1: zero test records                    | DH-1 SQL above   | `bench mariadb` |
| DH-2: zero orphan FK                       | DH-2 SQL above   | `bench mariadb` |
| DH-3: zero empty required fields           | DH-3 Python scan | `bench execute` |
| DH-4: docstatus ↔ workflow_state coherent | DH-4 SQL above   | `bench mariadb` |

### Cross-reference (mở rộng bảng E)

| Pattern phát hiện                        | Skill fix                                 | Reference         |
| ------------------------------------------ | ----------------------------------------- | ----------------- |
| `Unknown column 1054` raw SQL            | `assetcore-be`                          | LL-BE-22          |
| `not enough arguments for format string` | `assetcore-be`                          | LL-BE-21          |
| Xoá nhầm > scope dự kiến (LIKE bug)    | `assetcore-be` + `assetcore-deploy`   | LL-BE-21, Phần 3 |
| Test data tích luỹ trong DB              | `assetcore-test` + `assetcore-deploy` | R-9 + Phần 3     |
| Orphan FK sau cleanup                      | `assetcore-deploy`                      | Phần 3 step 5    |
| `bench restore` blocked (no root pw)     | `assetcore-deploy`                      | Phần 3 "Restore" |
| Empty required field trên real data       | `assetcore-be` LL-BE-9                  | Completion gate   |

Reference: `CONVENTIONS.md §32, §33`; `assetcore-deploy` Phần 3; `assetcore-test` R-9, R-10.

---

## Phần 4 — Lifecycle Hook Chain Audit (2026-05-27 — root: G2 Test Plan)

**Bug pattern recurring 5/11 trong G2:** RCA→CAPA, RCA→Incident, ACC→Asset, Asset→Cal Schedule, Asset→nextPM/nextCal — không wire.

### Pillar 9: Cross-Module Trigger Wiring

Audit mọi service `_finalize_*` / `complete_*` / `submit_*` trong `services/imm<XX>.py`:

#### Check 9.1: Doc chain trong `04_Backend_Design.md`

```bash
for module in 04 05 08 09 11 12 16; do
  f="docs/imm-${module}/04_Backend_Design.md"
  echo "=== imm-$module ==="
  grep -A5 "Cross-Module Triggers\|Side effect\|Trigger:" "$f" 2>/dev/null || echo "  ❌ Section missing"
done
```

Verdict: mọi module có completion service → phải có §Cross-Module Triggers documented.

#### Check 9.2: Service complete/submit có chain call (không silent end)

```bash
for f in assetcore/services/imm*.py; do
  python3 -c "
import ast
tree = ast.parse(open('$f').read())
for n in ast.walk(tree):
    if isinstance(n, ast.FunctionDef) and n.name.startswith(('complete_','submit_','_finalize_','finalize_')):
        body = ast.unparse(n)
        if 'from assetcore.services.imm' not in body and 'log_audit_event' in body:
            print('$f::' + n.name + ' — terminal transition nhưng KHÔNG chain call cross-module')
"
done
```

Verdict: mỗi `complete_*` cross-check spec — chain thiếu = 🔴 Critical (RC-03/04/06/07/11 pattern).

#### Check 9.3: Service B downstream phải idempotent

```bash
grep -B2 -A10 "^def create_from_\|^def create_.*_from_" assetcore/services/imm*.py \
  | grep -B5 "frappe\.get_doc\|insert\(" \
  | grep -L "frappe\.db\.exists\|existing"
# Mỗi match → service B không idempotent → call lần 2 sẽ tạo duplicate
```

#### Check 9.4: Audit `triggered_record` field

```bash
grep -rn "log_audit_event\|log_lifecycle_event" assetcore/services/imm*.py \
  | grep -v "triggered_record\|trigger_doc\|source_a"
# Mỗi audit log trong chain context phải có triggered_record link
```

#### Check 9.5: Test coverage cho hook chain

```bash
for f in assetcore/tests/test_imm*.py; do
  grep -L "creates_\|hook chain\|triggers_" "$f" && echo "$f missing chain test"
done
```

Reference: `CONVENTIONS.md §40`, `assetcore-be` LL-BE-23.

---

## Phần 5 — Whitelist Permission Gate Audit (extends Pillar 8 Security)

**Bug pattern P1 chưa fix (AUTH-02):** FE ẩn nút nhưng BE whitelist endpoint không có `rbac.require()` → privilege escalation.

### Check S-9: Mọi mutating whitelist có server-side gate

```bash
cd /home/miyano/frappe-bench/apps/assetcore
for f in assetcore/api/imm*.py assetcore/api/*.py; do
  python3 -c "
import ast
src = open('$f').read()
tree = ast.parse(src)
for n in ast.walk(tree):
    if isinstance(n, ast.FunctionDef) and any('whitelist' in ast.unparse(d) for d in n.decorator_list):
        # Bỏ qua endpoint có 'list_' / 'get_' / 'count_' prefix (read-only)
        if n.name.startswith(('list_','get_','count_','search_','export_')):
            continue
        body = ast.unparse(n)
        if 'rbac.require' not in body and 'has_any_role' not in body and 'frappe.only_for' not in body:
            print('$f::' + n.name + ' — missing server-side gate (POST/mutating)')
" 2>/dev/null
done
```

Mỗi match = 🔴 P1 security finding. Verdict: 100% mutating endpoints có gate.

### Check S-10: Capability strings BE↔FE khớp 1-1

```bash
# Liệt kê capability strings ở BE
grep -rn "rbac\.require(" assetcore/api/ assetcore/services/ | grep -oE '"[a-z]+\.[a-z_]+"' | sort -u > /tmp/be_caps.txt

# Liệt kê ở FE
grep -rn "can(" frontend/src/views/ frontend/src/components/ | grep -oE "'[a-z]+\.[a-z_]+'" | tr "'" '"' | sort -u > /tmp/fe_caps.txt

diff /tmp/be_caps.txt /tmp/fe_caps.txt
# Lines only BE → FE thiếu capability check (UI mở quá rộng)
# Lines only FE → FE check capability BE không khai báo (silent allow, hoặc typo)
```

### Check S-11: Test coverage cho permission gate

```bash
for f in assetcore/tests/test_imm*.py; do
  count=$(grep -c "FORBIDDEN\|test.*reject.*role\|test.*permission" "$f")
  [ "$count" -lt 2 ] && echo "$f: only $count permission tests (need ≥2)"
done
```

Reference: `CONVENTIONS.md §41`, `assetcore-be` LL-BE-24, `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md` AUTH-02.

---

## Phần 6 — Audit Trail UI Visibility Check (extends Pillar 6 FE)

**Bug RC-05:** Tab "Lịch sử phiếu" trống mặc dù BE đã log.

### Check FE-9: Mọi DetailView có AuditTrailTab

```bash
for f in frontend/src/views/**/[A-Z]*DetailView.vue; do
  if ! grep -q "AuditTrailTab\|Lịch sử" "$f"; then
    echo "🟡 GAP: $f — không có tab Lịch sử"
  fi
done
```

### Check FE-10: Empty state có warning prompt user báo dev

```bash
grep -rn "AuditTrailTab\|history.*empty\|events\.length" frontend/src/views/ \
  | grep -L "báo dev\|chưa có sự kiện"
# Empty silent = không phát hiện được hook chain thiếu
```

### Check BE Cross-Reference: Hook chain có audit log

Nếu Pillar 9 Check 9.4 fail → tab Lịch sử sẽ trống ngay khi hook chain wire xong. Phải fix cả 2 chỗ.

Reference: `CONVENTIONS.md §42`, `assetcore-fe` LL-FE-28.

---

## Phần 7 — KPI Scope Audit (extends Pillar 6 FE)

**Bug RC-09, RC-10:** KPI counter mâu thuẫn giữa 2 page do scope không nêu rõ.

### Check FE-11: KPI tile labels có scope qualifier

```bash
grep -rnE "<KpiTile[^>]*label=\"[^\"]+\"" frontend/src/views/ frontend/src/components/ \
  | grep -v "toàn hệ thống\|của tôi\|tôi phụ trách\|khoa\|quá hạn\|7 ngày\|tháng này\|hôm nay\|tuần này"
# Mỗi match → review thêm scope hoặc xác nhận unambiguous (vd "Tổng số tài sản")
```

### Check FE-12: Click KPI có pass scope qua route query

```bash
grep -rn "router.push" frontend/src/views/**/Dashboard*.vue frontend/src/components/**/Kpi*.vue \
  | grep -v "scope:\|query:"
# Mỗi tile clickable → query param phải đính scope khớp tile filter
```

Reference: `CONVENTIONS.md §43`, `assetcore-fe` LL-FE-29.

---

## Phần 8 — Auto-Default Field Audit (extends Pillar 1 DocType)

**Bug RC-02:** Field critical nhưng không default → user quên nhập → break downstream.

### Check BE-15: Field critical có default-by-condition trong before_save

```bash
# Tìm field downstream service đọc (vd asset.depreciation_method)
grep -rn "asset\.\|doc\." assetcore/services/imm*.py | grep -oE "\.(depreciation_method|calibration_interval_months|warranty_months|sla_priority|severity)" | sort -u

# Kiểm tra controller có before_save default
for dt_folder in assetcore/assetcore/doctype/ac_asset; do
  py_file="$dt_folder/$(basename $dt_folder).py"
  grep -A3 "def before_save" "$py_file" | grep -E "depreciation_method|calibration_interval" || \
    echo "🟡 $py_file: critical field không default ở before_save"
done
```

### Check BE-16: Required-when-condition validation

```bash
grep -B2 -A5 "def validate" assetcore/assetcore/doctype/*/*.py \
  | grep -B5 "frappe\.throw\|raise ValidationError" \
  | grep -v "^--"
# Critical asset/incident DocType phải có conditional required check (vd "tick HC nhưng thiếu chu kỳ")
```

Reference: `CONVENTIONS.md §44`, `assetcore-be` LL-BE-25, `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md` RC-02.

---

## Phần 9 — Verdict update (audit report format)

Mở rộng bảng audit verdict (`Audit report format`):

| Item                    | Check                                                     | Reference  |
| ----------------------- | --------------------------------------------------------- | ---------- |
| Pillar 1 DocType        | Pillar 1 + Phần 8 (BE-15, BE-16)                         | §44       |
| Pillar 2 Service        | Pillar 2 + Phần 4 (Check 9.1-9.5)                        | §40       |
| Pillar 6 FE             | Pillar 6 + Phần 6 (FE-9, FE-10) + Phần 7 (FE-11, FE-12) | §42, §43 |
| Pillar 8 Security       | Pillar 8 + Phần 5 (S-9, S-10, S-11)                      | §41       |
| Pillar 9 Hook Chain     | Phần 4 toàn bộ                                         | §40       |
| Phần 0 Recurring Sweep | GATE-1..4 (CONVENTIONS §0)                               | §0        |
| Phần 3 Data Hygiene    | DH-1..4                                                   | §32, §33 |

**Verdict rule:** mọi Pillar phải PASS — single fail = audit overall FAIL. Hook chain (Pillar 9) Critical = release block per CLAUDE.md §10/§12.

Reference: `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md` toàn bộ.

---

## 🔗 Session context — bàn giao phiên (assetcore-session)

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE+LOG mới nhất — "đang dở ở đâu"; dữ liệu NGOÀI repo, đừng tìm `sessions/` trong repo). Main session hook tự nạp mỗi prompt; subagent phải chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY `STATE.md`(ghi đè)+`LOG.md` — KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `sessions/`; fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
