# assetcore-audit — Module Audit 8-Pillar Checklist (heavy reference)

> Chi tiết 8-pillar production-readiness + các pillar mở rộng (Phần 4–9). `SKILL.md` giữ INLINE: Phần 0 sweep, UC-1..5, severity grading, audit report format, audit verdict. Đây là checklist đầy đủ để chạy từng pillar.

## Mục đích

Dùng trước:

- Tag release (`v3.x.y`)
- Promote module Wave-Planned → Wave-Live
- Cut deployment ticket
- Đóng sprint deliver IMM-XX

Skill này **chỉ verify** — không implement. Khi phát hiện gap, chuyển sang `assetcore-be`, `assetcore-fe`, `assetcore-test`, `assetcore-deploy`.

## 8 pillars audit

### Pillar 1 — DocType schema

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

### Pillar 2 — Service layer

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

### Pillar 3 — Repository

- [ ] `<Name>Repo(BaseRepository)` tồn tại
- [ ] Không có raw SQL trừ khi thực sự cần join phức tạp
- [ ] Import từ `assetcore/repositories/__init__.py`, không trực tiếp từ `_repo.py`

### Pillar 4 — API layer

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

### Pillar 5 — Workflow

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

### Pillar 6 — FE (Frontend)

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

### Pillar 7 — Tests

- [ ] `test_immXX.py` tồn tại
- [ ] Mỗi BR-XX-NN có ≥ 1 happy + 1 negative test
- [ ] Workflow smoke test pass
- [ ] Tests chạy được trên fresh site

```bash
bench --site miyano run-tests --module assetcore.tests.test_immXX
bench --site miyano run-tests --module assetcore.tests.guards.test_workflows
```

### Pillar 8 — Docs & Audit trail

- [ ] `docs/imm-XX/` có đủ 9 files (README + 02→09)
- [ ] `07_Testing_QA.md` có bảng UAT scenarios
- [ ] Mọi state transition gọi `log_audit_event(...)` — không bypass
- [ ] Không có module-local `_log_audit` hay `_create_lifecycle_event` (phải dùng canonical)

**Realistic data check (dùng trong UAT, không chỉ unit test):**

- [ ] Test data dùng tên thiết bị y tế thực, không phải "_Test", "sample"
- [ ] Work orders có complete fields: asset, technician, description thực tế
- [ ] KPI/stats được generate từ data thực (không mock 0)
- [ ] Audit trail có events thực sau khi tạo/sửa/chuyển trạng thái

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

Reference: `assetcore-be` LL-BE-23.

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

Reference: `assetcore-be` LL-BE-24, `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md` AUTH-02.

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

Reference: `assetcore-fe` LL-FE-28.

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

Reference: `assetcore-fe` LL-FE-29.

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

Reference: `assetcore-be` LL-BE-25, `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md` RC-02.

---

## Phần 9 — Verdict update (audit report format)

Mở rộng bảng audit verdict (`Audit report format` trong SKILL.md):

| Item                    | Check                                                     |
| ----------------------- | --------------------------------------------------------- |
| Pillar 1 DocType        | Pillar 1 + Phần 8 (BE-15, BE-16)                         |
| Pillar 2 Service        | Pillar 2 + Phần 4 (Check 9.1-9.5)                        |
| Pillar 6 FE             | Pillar 6 + Phần 6 (FE-9, FE-10) + Phần 7 (FE-11, FE-12) |
| Pillar 8 Security       | Pillar 8 + Phần 5 (S-9, S-10, S-11)                      |
| Pillar 9 Hook Chain     | Phần 4 toàn bộ                                         |
| Phần 0 Recurring Sweep | GATE-1..4                                                 |
| Phần 3 Data Hygiene    | DH-1..4                                                   |

**Verdict rule:** mọi Pillar phải PASS — single fail = audit overall FAIL. Hook chain (Pillar 9) Critical = release block per CLAUDE.md §10/§12.

Reference: `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md` toàn bộ.
