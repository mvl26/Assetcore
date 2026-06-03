# Skill Updates — 2026-05-27

Tổng hợp các bug đã gặp trong wave 1 và wave 2, mỗi bug → 1 rule mới hoặc strengthen rule cũ trong bộ `.claude/skills/`.

> File này là **patch proposal**. Để apply, user cần grant Edit permission cho `.claude/skills/**` hoặc paste tay từng block dưới đây vào skill file tương ứng.

---

## Inventory bug → rule mapping

| Bug | Module | Skill cần update | Rule mới/strengthen |
|---|---|---|---|
| Import asset `lifecycle_status="Active"` → workflow reject | IMM-00 import | `assetcore-be` | LL-BE-6 Import workflow state |
| Import asset `asset_category` nhận tên nhưng cần code | IMM-00 import | `assetcore-be` + `assetcore-import` | LL-BE-7 Resolve display→code |
| Asset Draft kẹt — TRANSITIONS map thiếu state | IMM-00 FE | `assetcore-fe` | LL-FE-10 Workflow map completeness |
| `LifecycleStatus` TS union thiếu Draft / Under Maintenance | IMM-00 FE | `assetcore-fe` | LL-FE-11 Type union sync BE |
| IMM-06 list/detail ẩn nút "Tạo mới" — `ROLES_TRAINING_MANAGE = []` | IMM-06 FE | `assetcore-fe` | LL-FE-12 Capability gating only |
| IMM-06 Program form Link-as-text | IMM-06 FE | `assetcore-fe` | LL-FE-9 strengthen |
| IMM-06 Competency list UX dead-end | IMM-06 FE | `assetcore-fe` | LL-FE-13 Actionable list page |
| Wave 2: English status leak / raw code leak / missing workflow buttons | IMM-02/03/06/16 | `assetcore-audit` | Pillar 6 strengthen |

---

## A. `assetcore-fe/SKILL.md`

### A1. THAY THẾ block LL-FE-9 hiện tại (3 dòng) → checklist 5 bước

Tìm trong `assetcore-fe/SKILL.md`:

```
### LL-FE-9: Link field input phải dropdown, không free text

Bug: form thêm candidate vào Vendor Evaluation dùng `<input type="text">` cho supplier → user nhập "Philips Healthcare" nhưng BE DocType `supplier` là Link → "Could not find Row #1: Vendor: Philips Healthcare".

**Quy tắc**: mọi field Link trong form PHẢI là dropdown/autocomplete load từ API list endpoint của target DocType.
```

THAY BẰNG:

```
### LL-FE-9: Link field input phải dropdown, không free text

Bug pattern: form (Create/Edit/Modal) dùng `<input type="text">` cho field mà DocType khai báo `"fieldtype": "Link"`. User phải gõ ID hệ thống (vd: "IMM-MDL-2026-00012") → không thực dụng + dễ sai → save fail "Could not find Row…" hoặc lưu chuỗi rác qua kiểm tra Frappe.

**Real incidents:**
- 2026-05 Vendor Evaluation: `supplier` text → "Philips Healthcare" → BE reject
- 2026-05-27 IMM-06 Program form: `target_device_model` + `target_device_category` đều Link nhưng FE render `<input type="text">` → user không chọn được, phải copy-paste ID

**Quy tắc (BẮT BUỘC trước khi viết hoặc sửa form):**

1. **Pre-check**: mở DocType JSON, list mọi field Link:
   ```bash
   grep -B1 -A3 '"Link"' assetcore/assetcore/doctype/<dt>/<dt>.json
   ```

2. **Component bắt buộc**: `<SmartSelect v-model="form.field" doctype="<TargetDocType>" placeholder="Chọn..." />`.
   - Nếu target DocType chưa có trong `DocType` union ở `components/common/SmartSelect.vue` → mở rộng union + thêm loader trong `stores/masterData.ts`. KHÔNG fallback `<input type="text">` vì "tạm chưa support".

3. **Loại trừ hợp lệ** (vẫn dùng `<input>`):
   - Field `Data` / `Small Text` (free text user-entered)
   - Field `Link` đến DocType nhỏ-lẻ chỉ dùng 1 chỗ (vd: `qms_doc_ref` → Asset Document): tạm chấp nhận text với hint `<p class="text-xs">Mã ...</p>` mô tả format, NHƯNG phải log gap để chuyển SmartSelect sau

4. **Self-check command** trước khi đóng task:
   ```bash
   grep -E "<input.*v-model=\"form\.(target_|supplier|department|location|asset|model|category|user|custodian|responsible)" frontend/src/views/<module>/*.vue
   ```
   Mỗi match → đối chiếu DocType JSON; nếu là Link → đổi sang SmartSelect.

5. **Data PK field (naming-series)**: nếu field là PK (vd `program_code` với `"autoname": "field:program_code"`), giữ `<input>` nhưng:
   - `:readonly="!isCreateMode"` (không cho đổi sau khi tạo)
   - Có placeholder + helper `<p class="text-xs">` mô tả format gợi ý
   - BE đã validate uniqueness (Frappe duplicate constraint)

Không tuân thủ là blocker FE-DoD — `assetcore-audit` Pillar 6 flag 🟠 HIGH.
```

### A2. THÊM MỚI sau LL-FE-9 (nếu chưa có)

```
### LL-FE-10: TRANSITIONS map phải cover ALL workflow states (bao gồm Draft)

Bug: 2026-05-27 imported asset ở Draft không có nút chuyển trạng thái — `AssetDetailView.vue` có `TRANSITIONS` map nhưng thiếu entry `'Draft': [...]`. Trước đó luồng create_asset auto-transition về Active nên không ai gặp Draft trong UI. Khi feature import được thêm, asset bắt đầu xuất hiện ở Draft → user kẹt.

**Quy tắc:**

1. Mở workflow JSON: `assetcore/assetcore/workflow/<workflow>.json`
2. Đếm `states` (trừ terminal):
   ```bash
   python3 -c "import json; d=json.load(open('<path>.json')); print([s['state'] for s in d['states']])"
   ```
3. Cho mỗi non-terminal state, FE DetailView phải có entry trong `TRANSITIONS: Record<string, Status[]>` với danh sách target states tương ứng `_VALID_TRANSITIONS` ở `services/<module>.py`
4. **Đặc biệt: state khởi tạo** (vd `Draft`, `Open`, `Planned`) — DỄ BỊ QUÊN vì luồng create thường skip qua state này. Phải check explicit.
5. Self-check:
   ```bash
   states_be=$(grep -E "^\s+_STATUS_\w+\s*=" assetcore/services/<module>.py | wc -l)
   states_fe=$(grep -cE "'\w[\w ]*':\s*\[" frontend/src/views/<domain>/<X>DetailView.vue)
   # states_fe phải >= (states_be - số terminal states)
   ```

### LL-FE-11: TypeScript union types phải sync BE constants

Bug: `LifecycleStatus` union ở `types/imm00.ts` thiếu `'Draft'` và `'Under Maintenance'` — TS compile vẫn pass vì cast as any/never check exhaustive. Khi thêm Draft vào TRANSITIONS map, TypeScript phải compile được mà không cần workaround.

**Quy tắc:**

1. Cho mỗi enum/status field, source-of-truth là `_STATUS_*` constants ở `services/<module>.py`
2. FE TypeScript union ở `types/<module>.ts` phải có TẤT CẢ state values, kể cả terminal/initial
3. Workflow JSON là cross-check thứ 2:
   ```bash
   # BE states
   python3 -c "import json; d=json.load(open('<wf>.json')); [print(s['state']) for s in d['states']]"
   # FE union
   grep -A5 "export type \w*Status" frontend/src/types/<module>.ts
   ```
4. Mismatch → strengthen union; không cast `as any` để bypass

### LL-FE-12: Role gating CHỈ dùng useCapabilities, không hasAnyRole(ROLES_*)

Bug: 2026-05-27 IMM-06 Program/Session list ẩn nút "Tạo mới" → root cause `ROLES_TRAINING_MANAGE = _empty` (`constants/roles.ts:104,129`). Các hằng số `ROLES_*` đã được deprecate thành `[]` từ wave RBAC redesign nhưng 3 view vẫn import & dùng → `hasAnyRole([])` luôn false.

**Quy tắc (BẮT BUỘC mọi view có gate UI):**

1. **CẤM** import `ROLES_*` từ `@/constants/roles` cho logic gate:
   ```bash
   grep -rn "ROLES_\w\+" frontend/src/views/ | grep -v ROLE_CATALOG
   # phải = 0 ngoài file admin/role-picker
   ```

2. **Dùng**: `const { can } = useCapabilities()` + `can('<domain>.<ptype>')`. Capability strings:
   - `<domain>.<ptype>` với ptype ∈ {read, write, create, delete, submit, cancel}
   - Domain enum: data, needs, spec, procurement, commissioning, document, training, pm, repair, calibration, corrective, inventory, compliance
   - Special: `pm.reschedule`, `incident.acknowledge`, `incident.close`, `cal.send_lab`, `doc.approve`, `capa.close`, `data.admin`, `audit.read`

3. **Mapping BE → FE capability** (cùng nguồn `services/shared/rbac.py::CAPABILITY_MAP`):
   - BE `rbac.require("training.write")` → FE `can('training.write')`
   - BE `rbac.require("incident.close")` → FE `can('incident.close')`
   - Phải khớp EXACT — không đặt tên thân thiện ở FE

4. **Self-check command**:
   ```bash
   grep -rn "hasAnyRole\|ROLES_TRAINING\|ROLES_PM\|ROLES_CM\|ROLES_CAL\|ROLES_INCIDENT\|ROLES_DOC\|ROLES_COMPLIANCE\|ROLES_STOCK\|ROLES_PLANNING\|ROLES_PROCUREMENT" frontend/src/views/
   # Mỗi match là 1 bug — đổi sang can('xxx')
   ```

### LL-FE-13: List page phải có hành động khả thi (KHÔNG dead-end UX)

Bug: 2026-05-27 IMM-06 `/competencies` list không có button nào ngoài filter — competency được sinh auto từ session nên không có create endpoint. User vào trang trống → không biết làm gì.

**Quy tắc:**

1. Mọi list page PHẢI có ít nhất 1 trong các hành động:
   - **Create button** (đa số case — gate qua capability)
   - **Navigate button** đến nơi tạo bản ghi (case auto-generated như Competency → "Buổi đào tạo")
   - **Bulk action** (Import / Export / Assign)

2. **Empty state phải actionable**: ngoài text "Chưa có dữ liệu", phải có ít nhất 1 button + 1 dòng giải thích cách tạo:
   ```html
   <div v-else-if="!items.length">
     <p>Chưa có ...</p>
     <p class="text-xs">{{ how_to_create_hint }}</p>
     <button @click="navigateToCreate">+ Tạo / Đi tới ...</button>
   </div>
   ```

3. **Process hint banner** (cho list auto-generated): banner xanh ở đầu trang giải thích "X được sinh tự động khi Y → đi tới Y để bắt đầu" (ví dụ: `CompetencyListView.vue:131-143`)

4. Self-check:
   ```bash
   # List view không có button create/navigate/import → flag
   for f in frontend/src/views/**/[A-Z]*ListView.vue; do
     grep -L "btn-primary\|@click=\"router.push\|@click=\"openImport" "$f" && echo "GAP: $f"
   done
   ```
```

---

## B. `assetcore-be/SKILL.md`

### B1. THÊM MỚI ở phần Lessons Learned (cuối file)

```
### LL-BE-6: Import endpoint phải bypass workflow validator bằng "Draft + transition"

Bug: 2026-05-27 `import_data.py` cho phép set `lifecycle_status="Active"` từ CSV → Frappe Workflow validator chặn vì doc mới chỉ được khởi tạo ở state đầu (Draft). Pre-validator thì pass (status nằm trong VALID_LIFECYCLE) → row fail ở insert.

**Quy tắc cho mọi import bulk DocType có workflow:**

1. Pre-validator chấp nhận desired_status (mọi giá trị hợp lệ)
2. Insert path:
   ```python
   desired_status = (clean.get("status_field") or "").strip()
   clean["status_field"] = INITIAL_STATE  # vd "Draft"
   doc.update(clean)
   doc.insert(ignore_permissions=True)
   if desired_status and desired_status != INITIAL_STATE:
       transition_to_status(doc.name, desired_status)
   ```
3. `transition_to_status` walk qua state machine (vd Draft → Commissioned → Active) — dùng cùng service layer `transition_<x>_status` để giữ audit trail + lifecycle event
4. Nếu desired_status không reachable từ INITIAL_STATE (vd terminal Decommissioned), skip transition silently — không trap row mid-flight

Pattern reference: `api/imm00.py:create_asset` (line 200-209), `api/import_data.py:_transition_asset_lifecycle`

### LL-BE-7: Import resolvable links — accept display name HOẶC system code

Bug: 2026-05-27 user fill template với "Máy chụp CT" (category_name) nhưng AC Asset Category PK = code → Frappe Link validator reject.

**Quy tắc:**

1. Define `_RESOLVABLE_LINKS_BY_DOCTYPE` cho mỗi import-supported DocType:
   ```python
   _RESOLVABLE_LINKS_BY_DOCTYPE = {
       "AC Asset": {
           "asset_category":  ("AC Asset Category",  "category_name"),
           "device_model":    ("IMM Device Model",    "model_name"),
           "location":        ("AC Location",         "location_name"),
           "department":      ("AC Department",       "department_name"),
           "supplier":        ("AC Supplier",         "supplier_name"),
       },
   }
   ```

2. Trong loop insert, trước `doc.update(clean)`:
   ```python
   for fld, (link_dt, display_field) in resolvable_links.items():
       val = clean.get(fld)
       if not val or frappe.db.exists(link_dt, val):
           continue
       resolved = frappe.db.get_value(link_dt, {display_field: val}, "name")
       if resolved:
           clean[fld] = resolved
   ```

3. Pre-validator cũng phải accept cả 2 (name OR display field) — không cứng chỉ chấp nhận PK
```

---

## C. `assetcore-audit/SKILL.md`

### C1. STRENGTHEN Pillar 6 FE checklist — thêm 3 checks sau "Sidebar không che content"

THÊM block:

```
- [ ] **Role gating KHÔNG dùng `ROLES_*` constants** (deprecated):
  ```bash
  grep -rn "hasAnyRole.*ROLES_\|from '@/constants/roles' import.*ROLES_" frontend/src/views/
  # Match = 0 (trừ admin/role-picker pages)
  ```
  Mọi gate UI phải qua `useCapabilities().can('<domain>.<ptype>')` (LL-FE-12).

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
```

### C2. THÊM vào cross-reference table

```
| Pattern phát hiện | Skill fix | Reference |
|---|---|---|
| ... (rows hiện có) | | |
| Button "Tạo mới" ẩn vô lý | `assetcore-fe` | LL-FE-12 |
| Workflow state có doc nhưng không có nút action | `assetcore-fe` | LL-FE-10 |
| TS error khi thêm state mới vào map | `assetcore-fe` | LL-FE-11 |
| Import workflow state reject | `assetcore-be` | LL-BE-6 |
| Import Link field name không resolve | `assetcore-be` | LL-BE-7 |
| List page không có action button | `assetcore-fe` | LL-FE-13 |
```

---

## D. `CONVENTIONS.md` (cross-skill rules)

### D1. THÊM section mới ở cuối

```
## §X. FE Auth Gating Convention

- **Forbidden**: `hasAnyRole(ROLES_*)`, `userStore.roles.includes(...)` — role-name checks at view layer.
- **Required**: `useCapabilities().can('<domain>.<ptype>')` — capability checks resolved từ `services/shared/rbac.CAPABILITY_MAP`.
- Capability string phải match EXACT giữa BE (`rbac.require("xxx")`) và FE (`can("xxx")`).
- View nào còn import `ROLES_*` ngoài admin role-picker = bug — flag bởi assetcore-audit.

## §Y. FE Link Field Convention

- Field `Link` trong DocType JSON ⇔ FE form phải dùng `<SmartSelect>` (component canonical từ `components/common/`).
- KHÔNG `<input type="text">` cho Link field — kể cả khi DocType chưa nằm trong SmartSelect `DocType` union (giải pháp: mở rộng union + thêm masterDataStore loader).
- Loại trừ: Data PK field với `autoname: "field:xxx"` — dùng `<input :readonly="!isCreateMode">` + helper text.

## §Z. FE TypeScript Union Convention

- Mọi enum/status union ở `types/<module>.ts` phải bao TẤT CẢ values từ BE `_STATUS_*` constants.
- Include cả initial state (Draft, Open, Planned) và terminal state (Closed, Decommissioned, Cancelled).
- Sync command: chạy `assetcore-audit` Pillar 6 → check TS union match BE.
```

---

## E. `assetcore-import/SKILL.md` (cross-reference)

Thêm note ở cuối:

```
> **BE rules áp dụng**: LL-BE-6 (workflow state via Draft + transition), LL-BE-7 (resolve display→code). Xem `assetcore-be/SKILL.md`.
```

---

## Apply

User có 2 lựa chọn:

**Option 1 — Tôi apply trực tiếp** (cần grant Edit cho `.claude/skills/**`):
```
/permissions
→ Add allow rule: Edit on .claude/skills/**
→ Sau khi grant, tôi sẽ apply 5 patches trên
```

**Option 2 — User paste tay** từ file này vào từng skill file. File này (`docs/res/guides/skill-updates-2026-05-27.md`) là source-of-truth của tất cả patches.

---

## Test cases để verify rule lần sau

Sau khi apply, các bug sau sẽ bị **bắt sớm** (audit hoặc tự check trước khi đóng task):

| Bug tương lai | Rule bắt | Skill flag |
|---|---|---|
| View mới import `ROLES_*` constant | LL-FE-12 + audit Pillar 6 | assetcore-fe + assetcore-audit |
| Form mới có `<input>` cho Link field | LL-FE-9 (strengthened) + audit | assetcore-fe + assetcore-audit |
| Workflow mới thêm state nhưng quên FE TRANSITIONS | LL-FE-10 + audit | assetcore-fe + assetcore-audit |
| Import endpoint cho phép set non-initial workflow state trực tiếp | LL-BE-6 | assetcore-be |
| List page mới không có action button | LL-FE-13 + audit | assetcore-fe + assetcore-audit |
| TS union enum thiếu state mới | LL-FE-11 | assetcore-fe |
