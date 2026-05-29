# assetcore-audit — Lessons Learned (regression classes + anti-false-positive)

> Audit checklist mở rộng từ bug thực tế — **always-apply**. `SKILL.md` trỏ tới đây.
> ĐỌC khi chạy audit/security review để không bỏ sót regression class & không log false-positive.

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
4. AUTH-01..10 (xem `docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md`) là MUST trước go-live, không thể single-account.

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

