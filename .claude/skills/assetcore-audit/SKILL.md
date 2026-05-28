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

## Lessons Learned 2026-05 — Audit checklist mở rộng

Khi audit 1 module, bắt buộc check các pattern bug đã gặp:

### A. Backend audit checks

```bash
# A1. Frappe 417 risk — int|None trong GET whitelist
grep -rn "int | None\|float | None" assetcore/api/ \
  | xargs -I{} grep -B2 "@frappe.whitelist" {} 2>/dev/null

# A2. Schema mismatch — service ref field không có trong DocType
# Cho mỗi service file, list field assignments rồi cross-check với DocType JSON
grep -E "doc\.\w+ =" assetcore/services/<module>.py | sort -u

# A3. Workflow action label inconsistency
diff <(python3 -c "import json; d=json.load(open('workflow.json')); print(sorted(t['action'] for t in d['transitions']))") \
     <(grep -E "transition.*action" assetcore/api/<module>.py)

# A4. Response enrichment — Link field phải có _name companion
grep -E "doctype.*Link" <doctype>.json
# Verify api/<module>.py có batch _enrich() cho từng Link field

# A5. Gate validator existence — mỗi gate G0X phải có function _validate_gate_g0X
grep -E "^def _validate_gate_g" assetcore/services/<module>.py
```

### B. Frontend audit checks

```bash
# B1. TRANSITIONS_BY_STATE completeness — đếm states vs entries trong map
states=$(python3 -c "import json; d=json.load(open('workflow.json')); print(len(d['states']))")
entries=$(grep -c "':\\s*\\[" frontend/src/views/<module>/DetailView.vue)
echo "States: $states | Map entries: $entries"  # phải bằng nhau (trừ terminal)

# B2. List page thiếu create button
for f in frontend/src/views/**/[A-Z]*ListView.vue; do
  grep -L "Tạo\|+ \|create\|new" "$f"
done

# B3. Hardcoded internal codes trong template
grep -rn "AC-SUP-\|AC-DEPT-\|AC-ASSET-\|IMM-MDL-" frontend/src/views/ \
  | grep -v "\.test\.\|\.spec\."

# B4. Link field as text input (bug pattern)
# Tìm <input type="text"> bind v-model có tên trùng Link field
grep -E "<input.*type=\"text\".*supplier|department|vendor|model" frontend/src/views/

# B5. StatusBadge sync — mỗi BE state có entry trong formatters
grep -E "^\s+'[A-Z][a-zA-Z\s]+':" assetcore/assetcore/workflow/*.json
grep "STATUS_LABEL\|STATUS_COLOR" frontend/src/utils/formatters.ts
```

### C. UI audit checks (Playwright)

Cho mỗi page trong module:

```
1. browser_navigate → list page
2. browser_snapshot → grep "Tạo" || "+ "  # phải có button create
3. browser_console_messages(error)  # phải 0 errors
4. browser_evaluate: tìm regex /AC-(SUP|DEPT|ASSET)-\d+/g  # phải 0 matches in user-facing text
5. browser_evaluate: tìm regex /\b[a-z0-9]{10}\b/g  # phải 0 matches (Frappe auto-name leak)

6. Click row → detail page
7. browser_snapshot → count workflow buttons  # phải >= 1 cho non-terminal state
8. Traverse all states → mỗi state phải có forward button
```

### D. New audit verdict items

Thêm vào audit report:

```
== Frappe API hygiene ==
- [ ] No int|None params trong GET endpoints (LL-BE-1)
- [ ] All Link fields enriched với _name companion (LL-BE-2)
- [ ] Service code ref fields verified vs DocType JSON (LL-BE-3)
- [ ] All gate validators implemented as functions (LL-BE-5)

== FE-BE contract sync ==
- [ ] Workflow action labels match exact (LL-BE-4, LL-FE-2)
- [ ] TRANSITIONS_BY_STATE covers all states (LL-FE-1)
- [ ] StatusBadge sync với BE workflow states (LL-FE-3)
- [ ] Form Select options = DocType options (LL-FE-8)
- [ ] Form Link fields use dropdown (LL-FE-9)

== UI completeness ==
- [ ] Every list has create button (LL-FE-4)
- [ ] Every detail has workflow buttons for current state (LL-FE-5)
- [ ] No code/email leaks user-facing (LL-FE-6)
- [ ] No Frappe auto-name leaks (LL-FE-7)
```

### E. Audit cross-reference

Khi audit bắt được pattern X → recommend fix theo skill tương ứng:

| Pattern phát hiện                                     | Skill fix                           | Reference         |
| ------------------------------------------------------- | ----------------------------------- | ----------------- |
| 417 EXPECTATION FAILED                                  | `assetcore-be`                    | LL-BE-1           |
| Unknown column 1054                                     | `assetcore-be`                    | LL-BE-3           |
| Workflow action 422                                     | `assetcore-be` + `assetcore-fe` | LL-BE-4 + LL-FE-2 |
| Code/email leak UI                                      | `assetcore-be` + `assetcore-fe` | LL-BE-2 + LL-FE-6 |
| List thiếu create                                      | `assetcore-fe`                    | LL-FE-4           |
| State stuck                                             | `assetcore-fe`                    | LL-FE-1           |
| Auto-name leak                                          | `assetcore-fe`                    | LL-FE-7           |
| Form Link as text                                       | `assetcore-fe`                    | LL-FE-9           |
| Gate enforced muộn                                     | `assetcore-be`                    | LL-BE-5           |
| Button "Tạo mới" ẩn vô lý (ROLES_* empty)          | `assetcore-fe`                    | LL-FE-12          |
| Workflow state có doc nhưng không có nút action    | `assetcore-fe`                    | LL-FE-10          |
| TS error khi thêm state mới vào map                  | `assetcore-fe`                    | LL-FE-11          |
| Import workflow state reject                            | `assetcore-be`                    | LL-BE-7           |
| Import Link field name không resolve                   | `assetcore-be`                    | LL-BE-8           |
| List page không có action button (dead-end UX)        | `assetcore-fe`                    | LL-FE-13          |
| Native `confirm()/alert()` thay vì modal             | `assetcore-fe`                    | LL-FE-14          |
| Rich-text hiển thị raw HTML `<p>`                   | `assetcore-fe`                    | LL-FE-15          |
| Delete button còn ở state non-Draft                   | `assetcore-fe`                    | LL-FE-16          |
| Dashboard KPI ≠ list filter count                      | `assetcore-fe`                    | LL-FE-17          |
| Service `run_/generate_/scan_` không có UI button   | `assetcore-fe`                    | LL-FE-18          |
| Test data leak vào production UI                       | `assetcore-fe` + cleanup          | LL-FE-19          |
| Cột computed (qty × price) hiển thị "—"            | `assetcore-fe`                    | LL-FE-20          |
| `complete_xxx` cho close khi prerequisite chưa đủ  | `assetcore-be`                    | LL-BE-9           |
| DocType name typo (`Department` vs `AC Department`) | `assetcore-be`                    | LL-BE-10          |
| Derived field trusts user input (Q1-2099)               | `assetcore-be`                    | LL-BE-11          |
| Dangling FK leaks raw ID trong UI                       | `assetcore-be`                    | LL-BE-12          |
| Slug appears trong display_name field                   | `assetcore-be`                    | LL-BE-13          |
| Deep-link sidebar "không thuộc module nào"           | `assetcore-fe`                    | LL-FE-21          |
| Empty `ROLES_*` stub array                            | `assetcore-fe`                    | LL-FE-22          |
| Action panel silent empty (permission denied)           | `assetcore-fe`                    | LL-FE-23          |

---

## Lessons Learned 2026-05-26 (round 2 — audit checks bổ sung)

### F. DocType cross-reference audit (BUG-019 regression class)

Bug pattern: 1 ký tự sai trong DocType name string crash cả module. Khi audit, MUST grep mọi `frappe.get_all|get_doc|db.exists|db.get_value` với DocType literal và verify JSON tồn tại.

```bash
# Liệt kê tất cả DocType strings dùng trong API/service files
grep -rhoE '(get_all|get_doc|db\.(exists|get_value|get_list))\("[A-Z][A-Za-z ]+"' \
  assetcore/api/ assetcore/services/ | sort -u

# Cross-reference với JSON tồn tại
for dt in $(grep -rhoE '"[A-Z][A-Za-z ]+"' assetcore/api/imm*.py assetcore/services/imm*.py \
            | tr -d '"' | sort -u); do
  snake=$(echo "$dt" | tr '[:upper:] ' '[:lower:]_')
  test -f "assetcore/assetcore/doctype/$snake/$snake.json" || \
    echo "POSSIBLE BAD DOCTYPE: $dt"
done
```

Flag any miss với severity 🔴 CRITICAL (crash class).

### G. Derived field validation audit (BUG-002 regression class)

Mỗi DocType controller có field tự động compute (quarter, days_overdue, age_days, line_total) phải re-compute trong `validate()`, không chỉ `before_insert`.

```bash
# Tìm before_insert có gán field
grep -A10 "def before_insert" assetcore/assetcore/doctype/*/*.py \
  | grep -E "self\.\w+\s*=" | grep -v "set_default\|created_by"

# Verify same field cũng được compute trong validate()
# Manual check — flag bất kỳ before_insert compute mà validate() không re-compute
```

Service nào nhận derived field từ user input MUST validate format + range:

```bash
grep -n "data\.get(.quarter\|data\.get(.\w*_year\|data\.get(.\w*_date" \
  assetcore/services/imm*.py | grep -v "_RE\|validate"
# Nếu match mà không có _RE pattern check → flag 🟠 HIGH
```

### H. Dangling FK enrichment audit (BUG-020 regression class)

Mọi enrichment helper PHẢI handle "linked record deleted" case explicit:

```bash
# Tìm enrichment pattern truyền raw ID làm fallback
grep -rn "_map\.get([^,]*,\s*r\[" assetcore/api/ assetcore/services/
# Anti-pattern: sup_map.get(r.supplier, r.supplier)  ← fallback về ID
# Đúng pattern phải có "[Đã xoá]" wrap + *_missing flag
grep -rn "Đã xoá\|_missing\b" assetcore/api/ assetcore/services/
```

Flag missing handler 🟠 HIGH cho mọi list endpoint enrichment.

### I. Slug-in-display audit (BUG-014 regression class)

```bash
# Tìm code compose display strings từ slug
grep -rnE "f['\"][^'\"]*\{[^}]*_slug\b" assetcore/services/ assetcore/api/
grep -rnE "f['\"][^'\"]*— \{[^}]*\}" assetcore/services/ assetcore/api/
# Verify mỗi {var} là display name, không phải slug/category_slug/snake_case identifier

# Runtime check trên DB
bench --site miyano console <<'EOF'
import re, frappe
slug = re.compile(r"\b[a-z]+-[a-z]+-[a-z]+\b")
for dt in ["PM Checklist Template", "IMM Training Program", "IMM Internal Audit"]:
    rows = frappe.db.get_all(dt, fields=["name"], limit=200)
    for r in rows:
        d = frappe.get_doc(dt, r.name)
        for field in d.meta.fields:
            if field.fieldtype in ("Data", "Small Text") and field.fieldname.endswith("_name"):
                val = d.get(field.fieldname) or ""
                if slug.search(val): print(dt, r.name, field.fieldname, val)
EOF
```

### J. Frontend hydration audit (BUG-003 regression class)

```bash
# router.isReady() PHẢI await trước app.mount()
grep -A2 "createApp\|app\.mount" frontend/src/main.ts | grep -E "router\.isReady"

# resolveModuleId export tồn tại + sidebar dùng nó
grep -n "export.*resolveModuleId\|resolveModuleId(" frontend/src/router/index.ts \
  frontend/src/components/common/AppSidebar.vue

# Sidebar fallback hint không phải "không thuộc module nào" cho route hợp lệ
grep -n "không thuộc module" frontend/src/components/common/AppSidebar.vue
# Nếu xuất hiện mà không có conditional check resolveModuleId() → 🔴 CRITICAL
```

### K. Empty ROLES_* stub audit (BUG-006/007/011 regression class)

```bash
# Tìm empty role array stubs
grep -nE "^export const ROLES_\w+\s*(:[^=]+)?\s*=\s*\[\s*\]" \
  frontend/src/constants/roles.ts

# Mỗi empty const phải có 0 usages — nếu còn usage thì migration chưa hoàn
for const in $(grep -oE "^export const ROLES_\w+" frontend/src/constants/roles.ts \
               | awk '{print $3}'); do
  count=$(grep -rc "\b$const\b" frontend/src/views/ frontend/src/components/)
  echo "$const: $count usages"
done
```

Flag empty const có usage > 0 → 🟠 HIGH (silent permission denial).

### L. Permission-denied silent UI audit (BUG-006/007 regression class)

Mọi DetailView có action panel phải có fallback hint khi không có button render:

```bash
# Tìm action panel bị gate hoàn toàn bằng v-if="can…" mà thiếu v-else hint
# Manual review per DetailView — checklist:
# 1. Open file frontend/src/views/<domain>/<X>DetailView.vue
# 2. grep "<button" — đếm số buttons
# 3. Check mỗi button có v-if="can…" gate
# 4. Verify có <div v-else-if="isNonTerminal"> hint
```

Cho mỗi DetailView audit, navigate qua từng state với test user role thấp → no buttons → MUST thấy hint "Bạn không có quyền…".

---

## Lessons Learned 2026-05-26 — Audit anti-false-positive checklist

Phát hiện trong session test Wave 1 + IMM-00: 2 trên 5 "bug" báo cáo là FALSE POSITIVE vì audit không verify đủ context. Các quy tắc dưới đây PHẢI áp dụng TRƯỚC khi log bug.

### LL-AUDIT-1: Trước khi log "code/email leak" — verify dual-display pattern

Bug 2026-05-26 (FP): Asset detail snapshot bắt được `AC-SUP-2026-0017` ở leaf div → kết luận "FE thiếu enrich". Sự thật: template `AssetDetailView.vue:306-323` hiển thị **2 dòng**: dòng 1 là `supplier_name` (primary), dòng 2 là `supplier` code (text-xs slate-400 subtitle). Đây là design pattern chuẩn — name + code dual display.

**Audit procedure**:

1. Đọc view file tại label/dt tương ứng (vd `grep -n "Nhà cung cấp" frontend/src/views/asset/AssetDetailView.vue`)
2. Verify template KHÔNG có `*_name` fallback hoặc subtitle hiển thị name → mới log bug
3. Nếu có: BE response cần check `frappe.db.get_value` cho field enrich (BE bug); FE template cần check `x.xxx_name || x.xxx` (FE bug)
4. Nếu cả 2 đúng nhưng UI vẫn raw code → API response thực không có `*_name` (kiểm tra qua `bench --site execute <module>.<get_xxx>`)

### LL-AUDIT-2: Trước khi log "workflow stuck" — verify role-gating

Bug 2026-05-26 (FP): Calibration detail tại Scheduled không có button → kết luận stuck. Sự thật: workflow JSON có 3 valid transitions; FE wire đầy đủ nhưng gate bằng `v-if="canExecuteCal"` / `v-if="canManageCal"`. Test user thiếu CAL_EXECUTE → buttons correctly hidden.

**Audit procedure**:

1. Đọc workflow JSON: `python3 -c "import json; d=json.load(open('imm_XX_xxx_workflow.json')); [print(t['state'],'->',t['next_state'],t['action']) for t in d['transitions']]"`
2. Đọc view file: `grep -n "v-if\|canXxx\|hasAnyRole" frontend/src/views/<domain>/<X>DetailView.vue`
3. Check role gate của user hiện tại (Pinia auth store) — nếu thiếu role → expected behavior, KHÔNG phải bug
4. Real bug variant: user role HỢP LỆ + state có transition + button vẫn ẩn → log P1
5. UX gap variant: role không hợp lệ + thiếu empty-state "Không có hành động khả dụng" → log P3 (xem LL-FE-21 / L.Permission-denied silent UI)

### LL-AUDIT-3: HTTP 200 + envelope `success:false` — luôn check response body

Bug 2026-05-26 thực: `get_incident(IR-2026-0108)` trả HTTP 200 nhưng body `{success:false, http_status:500, error:"Lỗi server"}`. Network tab xanh nhưng UI hiển thị "Lỗi server".

**Audit procedure**:

1. Khi UI báo "Lỗi server" — KHÔNG dừng ở "HTTP 200 OK" — phải đọc response body
2. Playwright: `browser_network_request(index=N, part="response-body")`
3. Bench reproduce: `bench --site miyano execute <module>.<api>.<endpoint> --kwargs '{...}'`
4. Trace root cause: `frappe.get_all("Error Log", filters={"error":["like","%<endpoint>%"]}, order_by="creation desc", limit=1)` (qua bench execute, KHÔNG qua console — xem LL-TEST-16)

### LL-AUDIT-4: Service detail endpoint — bắt buộc null-guard mọi `Repo.get(fk)`

Bug 2026-05-26 thực: `services/imm12.py:489` — `rca = RCARepo.get(doc.rca_record); data["rca"] = {"name": rca.name, ...}` crash khi `rca_record` là orphan ref (RCA đã bị xóa). Test data residue tạo ra rất nhiều orphan refs.

**Audit grep**:

```bash
# Tìm pattern Repo.get().field hoặc get_doc(dt, fk).field không null-guard
grep -nE "Repo\.get\([^)]+\)\.\w+" assetcore/services/imm*.py
grep -nE "frappe\.get_doc\([^)]+\)\.\w+" assetcore/services/imm*.py | grep -v "self\.\|cls\."

# Mỗi match → phải có `if obj:` guard hoặc `getattr(obj, field, default)`
```

**Quy tắc**: BẤT KỲ `Repo.get(fk)` hay `frappe.get_doc(dt, fk)` nào trên FK từ DocType khác PHẢI `if obj:` guard. Orphan refs xuất hiện sau xóa thủ công, test cleanup, hoặc data migration.

### LL-AUDIT-5: tearDown errors vs test failures — đọc unittest output cẩn thận

Bug 2026-05-26: `test_imm08` báo `Ran 19 tests in 1.3s` `FAILED (errors=2)`. Easy to misread as "2 test fails". Sự thật: `errors=2` là tearDownClass errors, KHÔNG phải logic test fails (logic tests 19/19 pass).

**Audit procedure khi đọc bench run-tests output**:

- `failures=N` = N test assertion fails → 🔴 logic bug
- `errors=N` = N setUp/tearDown exceptions → ⚠️ infra issue (test fixture, not product). Verify bằng cách scroll up: nếu tất cả errors ở `tearDownClass`/`tearDownModule` → KHÔNG block release nhưng phải fix trong sprint (xem LL-TEST-9, LL-TEST-17)
- `OK` = pass tuyệt đối

Trong audit report: phân biệt rõ "BE logic ✅" với "test infra ⚠️" — đừng gộp.

### LL-AUDIT-6: FE/BE label sync audit (English status leak)

Bug session 2026-05-26 (B-IMM02-1, B-IMM02-2, B-IMM03-1, B-IMM16-1): 5+ workflow states/enums hiển thị English trên UI (Locked, Evaluated, Contract Signed, Weekly, Minor). Root cause: `STATUS_MAP` ở `frontend/src/utils/formatters.ts` thiếu entry cho states Wave-2.

**Audit script** (chạy mỗi sprint, mỗi pre-release):

```bash
# 1. Dump tất cả workflow states từ JSON:
for wf in assetcore/assetcore/workflow/*.json; do
  python3 -c "import json; d=json.load(open('$wf')); [print(s['state']) for s in d['states']]"
done | sort -u > /tmp/be_states.txt

# 2. Dump labels từ FE formatters:
grep -oE "^\s+'[A-Z][^']*':" frontend/src/utils/formatters.ts \
  | sed "s/.*'\([^']*\)'.*/\1/" | sort -u > /tmp/fe_labels.txt

# 3. Diff:
comm -23 /tmp/be_states.txt /tmp/fe_labels.txt
# Output không rỗng → có state thiếu label → 🟠 HIGH (English leak)

# 4. Frequency/enum labels (severity, frequency, ...) — grep DocType JSON `Select` options:
grep -E "\"options\":" assetcore/assetcore/doctype/*/imm_*_rule.json | head
# Match với FE local label maps (`FREQUENCY_LABELS`, `SEVERITY_LABELS`)
```

Mỗi missing label = 1 P3 bug. Audit verdict failed nếu >3 unlabeled.

### LL-AUDIT-7: List/detail enrichment audit (raw code leak `AC-PUR-*`, `IMM-MDL-*`)

Bug session 2026-05-26 (B-IMM03-2, B-IMM06-3): list endpoint trả Link field raw (`ac_purchase_ref`, `target_device_model`) nhưng KHÔNG enrich `_name` companion → FE cell hiển thị raw code.

**Audit script**:

```bash
# 1. Dump tất cả Link field declared trên DocType chính của mỗi module:
python3 <<'PY'
import json, glob
for jf in glob.glob("assetcore/assetcore/doctype/*/*.json"):
    try:
        d = json.load(open(jf))
        if d.get("doctype") != "DocType":
            continue
        links = [f["fieldname"] for f in d.get("fields", []) if f.get("fieldtype") == "Link"]
        if links:
            print(f"{d['name']}: {links}")
    except Exception:
        pass
PY
# Output: "IMM Procurement Decision: ['spec_ref', 'winner_supplier', 'ac_purchase_ref', ...]"

# 2. Với mỗi DocType, grep service/api file có _enrich/_fetch_display cho mỗi Link field:
for dt in $(grep -lE "list_\w+|get_\w+" assetcore/api/imm*.py); do
  module=$(basename $dt .py)
  echo "=== $module ==="
  grep -nE "_fetch_display|_enrich" assetcore/api/$module.py assetcore/services/$module.py 2>/dev/null
done

# 3. Cross-check với FE template: nơi nào dùng raw field name (without _name fallback)?
grep -rnE "\{\{ [a-z_]+\.[a-z_]+_ref \}\}|\{\{ [a-z_]+\.target_device_model \}\}" frontend/src/views/ | head
# Mỗi match là 1 potential leak — phải dùng `obj.foo_name || obj.foo` pattern
```

### LL-AUDIT-8: Single-account audit limitation — RBAC pillar cần ≥ 4 accounts

Bug session 2026-05-26: tester `chuvanhieu357@gmail.com` không có `ROLES_TRAINING_MANAGE` → IMM-06 program detail không hiển thị "Chỉnh sửa", "Lưu trữ" → tưởng B-IMM06-2/4 (missing buttons). Thực ra RBAC đúng.

**Quy tắc khi audit RBAC pillar:**

1. Dump roles của user test:
   ```bash
   bench --site miyano console <<< "import frappe; print(frappe.get_roles('<user>'))"
   ```
2. Khi audit report có item "list thiếu Create" hoặc "detail thiếu workflow button":
   - Grep FE component: `grep -E "v-if=\".*canManage\|hasAnyRole\|useCapabilities" <view>.vue`
   - Nếu có role gate → ghi "role-gated, test user lacks `<role>`" — KHÔNG mark là bug
   - Nếu KHÔNG có gate + button vẫn ẩn → bug thực sự
3. **Full RBAC audit cần 4 accounts**: Admin / User / Auditor (read-only) / Vendor-tech. Single-account audit chỉ cover subset, phải note trong verdict.
4. AUTH-01..10 (xem `docs/res/AssetCore_Test_Plan_NextRound_1_Analysis.md`) là MUST trước go-live, không thể single-account.

### LL-AUDIT-9: BE→FE follow-up gap khi BE commit thêm field mới

Bug session 2026-05-26 (B-IMM16-2): BE commit 83884c8 thêm `linked_incident`/`source_type`/`source_ref` cho `IMM CAPA Record` + enrich service. FE `CAPADetailView.vue` không có render section → field invisible. BE-only commit thiếu paired FE work.

**Audit khi review BE commit có thêm Link field:**

```bash
# 1. Liệt kê Link field mới trong commit (diff DocType JSON):
git diff <base>..<head> -- "assetcore/assetcore/doctype/*/.json" | grep -E "\"fieldtype\": \"Link\"|\"fieldname\":"

# 2. Grep FE detail view có render Link field mới không:
grep -E "linked_incident|source_type|source_ref|<new_field>" frontend/src/views/<domain>/<X>DetailView.vue
# Match = 0 → 🟠 HIGH (BE wired, FE invisible). Tạo FE follow-up task.
```

**Quy tắc**: BE commit thêm field user-visible PHẢI có 1 trong:

- Commit chung BE+FE
- Follow-up FE issue/PR mở ngay sau merge BE
- Audit note explicit "FE follow-up pending"

---

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

Reference: `CONVENTIONS.md §41`, `assetcore-be` LL-BE-24, `docs/res/AssetCore_Test_Plan_NextRound_1_Analysis.md` AUTH-02.

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

Reference: `CONVENTIONS.md §44`, `assetcore-be` LL-BE-25, `docs/res/AssetCore_Test_Plan_NextRound_1_Analysis.md` RC-02.

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

Reference: `docs/res/AssetCore_Test_Plan_NextRound_1_Analysis.md` toàn bộ.
