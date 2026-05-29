# assetcore-fe — Lessons Learned (LL-FE-*)

> Bug patterns FE production đã gặp — **always-apply rules**, KHÔNG phải tham khảo tùy chọn.
> `SKILL.md` trỏ tới file này; ĐỌC TRƯỚC khi viết/sửa view · store · API client · workflow buttons.

## Lessons Learned 2026-05 (bug patterns đã gặp — phải tránh)

### LL-FE-1: `TRANSITIONS_BY_STATE` map phải đầy đủ TẤT CẢ states

Bug: PD detail view có 8 states, nhưng `TRANSITIONS_BY_STATE` chỉ map 5 states đầu → state "Contract Signed" không có nút "Phát hành PO" → user kẹt.

```typescript
// ❌ SAI — thiếu state Contract Signed
const TRANSITIONS_BY_STATE: Record<string, string[]> = {
  'Draft':             ['Chọn phương án'],
  'Method Selected':   ['Bắt đầu thương thảo'],
  'Negotiation':       ['Đề xuất trúng thầu'],
  'Award Recommended': ['Trình BGĐ'],
  // ❌ Missing 'Contract Signed': ['Phát hành PO']
}

// ✅ ĐÚNG — đếm states từ workflow.json, map đủ
// python3 -c "import json; d=json.load(open('workflow.json')); print(len(d['states']))"
```

**Quy tắc**: map phải có entry cho mọi state có outgoing transition. Test bằng cách traverse full lifecycle qua UI — nếu kẹt ở state nào → bug.

### LL-FE-2: Workflow action labels phải khớp BE EXACT (tiếng Việt có dấu)

Bug: FE gọi `"Trình Ban Giám đốc"` (đầy đủ) nhưng workflow JSON định nghĩa `"Trình BGĐ"` (viết tắt) → 422 `Not a valid Workflow Action`.

**Quy tắc**: import constant từ `@/utils/wave2Labels` hoặc shared module, không hardcode string. Sau khi BE tạo workflow JSON, FE phải đồng bộ ngay.

### LL-FE-3: StatusBadge label/color phải đồng bộ với BE state machine

Bug: BE `workflow_state = "Submitted"`, FE formatter map `Submitted → "Đã duyệt"` (xanh) → user thấy "Đã duyệt" khi thực ra mới submit.

**Quy tắc**: trong `formatters.ts` mỗi BE state có entry trong `STATUS_LABEL` (label đúng nghĩa) và `STATUS_COLOR`. Khi BE thêm state mới → update FE formatter cùng commit.

### LL-FE-4: List page TỐI THIỂU phải có nút tạo mới

Bug: `/procurement-plans` chỉ có filter, không có nút "+ Tạo" → user không tạo được plan qua UI.

**Quy tắc** (DoD cho List page): mỗi list page (trừ trang view-only) phải có:
- Nút "+ Tạo mới" trong `PageHeader #actions` slot
- Modal hoặc navigate đến `/create` view
- Sau khi tạo: navigate đến detail của record mới

### LL-FE-5: Detail page phải có ĐẦY ĐỦ workflow buttons theo state

Bug: PP detail chỉ có nút "Đưa NR vào kế hoạch" cho state Draft, thiếu "Phê duyệt"/"Kích hoạt"/"Đóng" cho các state khác.

**Quy tắc**: count workflow states, count UI buttons. Mỗi state phải có ít nhất 1 button cho transition tiếp theo (trừ terminal states).

### LL-FE-6: Hiển thị display name, không hiển thị code/email

Bug recurring: subtitle hiển thị `AC-DEPT-0101` thay vì `Khoa Tim mạch can thiệp`. Field `requesting_department` là Link, FE phải đọc `requesting_department_name` (BE đã enrich).

**Bug 2026-05-27** (IMM-06 CompetencyListView): `c.device_model` render `IMM-MDL-2026-0023` thay vì "Dräger Evita V500" — BE quên enrich + FE quên fallback. Fix yêu cầu cả 2 phía (xem CONVENTIONS §37 + §38).

```vue
<!-- ❌ SAI -->
<p>{{ doc.requesting_department }}</p>
<td>{{ c.device_model }}</td>

<!-- ✅ ĐÚNG — `??` (không `||`), giữ ID gốc làm tooltip -->
<p :title="doc.requesting_department">{{ doc.requesting_department_name ?? doc.requesting_department ?? '—' }}</p>
<td :title="c.device_model">{{ c.device_model_name ?? c.device_model }}</td>
```

`??` (nullish coalescing) thay vì `||` — đề phòng giá trị falsy hợp lệ (vd `""` từ BE) bị fallback nhầm.

**Quy tắc**:
1. Snapshot Playwright → grep tìm `AC-*`, `IMM-*`, `email@...` — nơi nào không phải là link/ID thuần thì bug.
2. Chạy CONVENTIONS §0 GATE-2 grep trước khi mark Done — bắt mọi biến (`row`, `item`, `doc`, `c`, `r`, `x`) reference Link field thiếu `_name`.
3. Nếu BE chưa enrich `<field>_name`, FE KHÔNG được hardcode lookup ở FE — sửa BE (xem `assetcore-be` LL-BE-2 + CONVENTIONS §37) rồi FE mới render.

### LL-FE-7: Frappe child table — KHÔNG hiển thị `row.name`

Bug: `plan_items` hiển thị `5mvh1o4qsa` (Frappe auto-name) thay vì `NR-26-05-00010`.

```vue
<!-- ❌ SAI -->
<td>{{ item.name }}</td>

<!-- ✅ ĐÚNG — đọc Link field gốc -->
<td>{{ item.needs_request || '—' }}</td>
```

**Quy tắc**: `row.name` của child table là internal ID — không bao giờ show cho user.

### LL-FE-8: Form Select options phải match BE DocType JSON

Bug: FE form cho free-text `funding_source` nhưng BE DocType định nghĩa `Select` với options cố định → save fail với `Invalid Value`.

```bash
# Verify DocType options trước khi build form
python3 -c "import json; d=json.load(open('<doctype>.json')); \
  [print(f['fieldname'], '=', repr(f['options'])) for f in d['fields'] if f['fieldtype']=='Select']"
```

**Quy tắc**: dùng constant module shared cho enum/select options (FE + BE đọc cùng nguồn).

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

### LL-FE-14: Cấm `window.confirm()` / `alert()` — dùng `BaseModal`

Bug: 2026-05-16 IMM-11 Calibration submit dùng native `confirm()` còn modules khác dùng styled modal → UX inconsistent + native dialog không brand được + không support Vietnamese formatting đẹp.

**Quy tắc:**

1. Mọi destructive/confirm action dùng `<BaseModal>` từ `components/common/BaseModal.vue`
2. Cấm `window.confirm()`, `alert()`, `prompt()` trong `frontend/src/views/**`:

   ```bash
   grep -rn "window\.confirm\|\bconfirm(\|\balert(\|\bprompt(" frontend/src/views/
   # = 0 match
   ```

3. Pattern cho confirm modal: `<BaseModal v-model="showConfirm" title="..." @confirm="doAction">...</BaseModal>` + button trigger `@click="showConfirm = true"`
4. Pattern cho destructive: thêm warning banner đỏ + require typed confirmation (vd "Nhập DELETE để xác nhận") cho action không thể hoàn tác

### LL-FE-15: Rich-text field phải render HTML qua `sanitizeHtml`, không raw text

Bug: 2026-05-16 IMM-12 Incident "Mô tả sự cố" hiển thị `<p>Bệnh nhân...</p><b>nguy cấp</b>` dưới dạng text → user thấy raw HTML markup thay vì văn bản format.

**Quy tắc:**

1. Field DocType `Text Editor` / `HTML` / `Long Text` (chứa markup) phải render qua `v-html` + sanitize:

   ```vue
   <script>import { sanitizeHtml } from '@/utils/sanitizeHtml'</script>
   <div v-html="sanitizeHtml(doc.description)" class="prose prose-sm"></div>
   ```

2. **CẤM `{{ doc.description }}`** cho rich-text — sẽ escape HTML thành text raw
3. **CẤM `v-html="doc.description"` trần** — XSS risk (NEG-06)
4. Mọi `v-html` phải qua `sanitizeHtml()` (file `frontend/src/utils/sanitizeHtml.ts` whitelist `<p><b><i><ul><ol><li><br><a><strong><em>` + strip script/iframe/on*)
5. Self-check:

   ```bash
   grep -rn 'v-html=' frontend/src/views/ | grep -v sanitizeHtml
   # = 0 match
   ```

### LL-FE-16: Destructive button (Xóa) chỉ render ở Draft state

Bug: 2026-05-16 IMM-12 Incident "Critical" ở state "Đang điều tra" vẫn show button "Xóa" → user có thể xóa cứng evidence giữa luồng investigation → audit trail bị mất.

**Quy tắc:**

1. Button "Xóa" / Delete chỉ hiện khi:
   - State = Draft / Open (chưa submit) **VÀ**
   - `canDelete` capability gate **VÀ**
   - Không có child record dependency
2. Sau khi rời Draft, dùng "Hủy" (cancel/void) hoặc "Đóng" (close) — KHÔNG delete:

   ```vue
   <!-- ❌ SAI -->
   <button v-if="canDelete" @click="doDelete">Xóa</button>

   <!-- ✅ ĐÚNG -->
   <button v-if="canDelete && doc.workflow_state === 'Draft'" @click="doDelete">Xóa</button>
   <button v-else-if="canCancel && !isTerminalState(doc.workflow_state)" @click="doCancel">Hủy</button>
   ```

3. BE backup gate: `services/<module>.py:delete_xxx()` phải `require state == "Draft"` — không tin FE
4. Self-check:

   ```bash
   grep -B2 'doDelete\|deleteDoc' frontend/src/views/**/*DetailView.vue | grep -v "workflow_state === 'Draft'\|state === 'Open'"
   # mỗi match là 1 gap
   ```

### LL-FE-17: Dashboard KPI phải dùng cùng query/source với list view

Bug: 2026-05-16 IMM-15 Dashboard "Cảnh báo tồn thấp: 0" nhưng `/stock` list hiển thị 5 bins đang low-stock — root cause: dashboard KPI tính total across warehouses (sum ≥ threshold) thay vì per-bin check.

**Quy tắc:**

1. KPI service function phải dùng cùng predicate với list filter:

   ```python
   # ❌ SAI: aggregate trước, check threshold sau
   total = sum(b.qty for b in bins)
   low_count = 1 if total < threshold else 0

   # ✅ ĐÚNG: check per-row giống list
   low_count = sum(1 for b in bins if b.qty < b.min_threshold)
   ```

2. FE Dashboard widget click → navigate đến list page với filter pre-applied, expected count = KPI number
3. Acceptance test: KPI count ở dashboard PHẢI khớp số dòng ở list khi apply cùng filter

### LL-FE-18: Mọi BE service user-initiated phải có UI button trigger

Bug: 2026-05-16 IMM-16 Compliance: `compliance.run_scan()` + `generate_scorecard()` chỉ có scheduler/seed gọi → FE không có button "Chạy quét tuân thủ" → user không thể trigger thủ công → findings/scorecards rỗng ngoài lịch chạy.

**Quy tắc:**

1. Mọi service function trong `services/<module>.py` có ý nghĩa "user-initiated" (run_*, generate_*, scan_*, trigger_*, recalculate_*) phải có:
   - API endpoint trong `api/<module>.py`
   - UI button ở list/dashboard view tương ứng (gate qua capability)
2. Scheduler + seed là FALLBACK, không substitute UI trigger
3. Tự check: với mỗi `@frappe.whitelist()` POST endpoint, grep FE views có call:

   ```bash
   grep -rn "<endpoint_name>" frontend/src/api/<module>.ts frontend/src/views/<domain>/
   # phải >= 1 match
   ```

### LL-FE-19: Test data không được leak vào production UI

Bug: 2026-05-26 IMM-06 production list hiển thị `_TEST-PROG-IMM06-SHARED`, `_Test Program IMM06 Shared`, `_Test Category`; IMM-16 hiển thị `TEST-R-IMM08-PM-90`, `_Test Asset IMM08-wo`, "Test effectiveness". Test rollback fail ở một point — orphan test records còn lại.

**Quy tắc (cả BE test + FE display):**

1. **Naming convention TEST data**: tất cả test fixtures phải có prefix DỄ GREP để cleanup safe:
   - `_Test*` (underscore prefix, Vietnamese name)
   - `_TEST-*` (uppercase với dash)
   - `TEST-*` (uppercase prefix cho code)
2. **Test teardown**: dùng `frappe.delete_doc(force=True, ignore_permissions=True)` — không rely on `tearDownClass` rollback:

   ```python
   @classmethod
   def tearDownClass(cls):
       for name in cls._created_docs:
           try:
               frappe.delete_doc(cls._doctype, name, force=True, ignore_permissions=True)
           except Exception:
               pass
       super().tearDownClass()
   ```

3. **Pre-release sanity check**:

   ```bash
   # SQL grep tất cả test records leak vào production tables
   bench --site miyano mariadb -e "
     SELECT name FROM \`tabIMM Training Program\` WHERE name LIKE '\\_Test%' OR name LIKE 'TEST-%';
     SELECT name FROM \`tabAC Asset\` WHERE name LIKE '\\_Test%' OR asset_name LIKE '\\_Test%';
     -- ...repeat cho mọi DocType operational
   "
   ```

4. **FE defensive filter** (tạm thời, không substitute fix BE): list view filter ra `name.startsWith('_Test')`:

   ```typescript
   const filtered = items.value.filter(x => !x.name?.startsWith('_Test') && !x.name?.startsWith('TEST-'))
   ```

5. **Audit checkpoint**: trước khi tag release, chạy SQL grep ở (3); kết quả phải = 0.

### LL-FE-20: Computed field (qty × price) phải render — không để "—"

Bug: 2026-05-16 IMM-15 stock-movement detail line "Thành tiền" hiển thị "—" (qty × price không tính); footer total đúng. Detail row computed column bị bỏ trống vì FE không tính client-side và BE không trả field.

**Quy tắc:**

1. Field computed (vd `line_total = qty * price`, `days_until_expiry = expiry_date - today`) phải:
   - Tính ở BE service rồi trả về `_computed` companion field, HOẶC
   - Tính ở FE qua `computed()` từ source fields
2. KHÔNG render "—" / null cho field có thể compute từ data sẵn có:

   ```vue
   <!-- ❌ SAI -->
   <td>{{ line.line_total ?? '—' }}</td>

   <!-- ✅ ĐÚNG -->
   <td>{{ formatVND((line.qty ?? 0) * (line.price ?? 0)) }}</td>
   ```

3. Self-check: footer total ≠ 0 nhưng row "—" → bug (data có nhưng FE không render)

### LL-FE-30: `STATUS_MAP` + `STATUS_COLOR` ở `utils/formatters.ts` là single source of truth

> (Trước đây đánh số trùng LL-FE-21 — đổi thành LL-FE-30 để hết va số; entry LL-FE-21 chính thức là "Sidebar/module-context detection" bên dưới.)

Bug session 2026-05-26: FE hiển thị "Locked", "Evaluated", "Contract Signed" English vì 11 workflow states Wave-2 KHÔNG có entry trong `STATUS_MAP`. `StatusBadge.vue` fallback `STATUS_MAP[status] ?? status` → English literal.

**Quy tắc khi thêm workflow state mới ở BE:**

1. Mọi state trong `workflow.json` BẮT BUỘC có entry trong CẢ 2 map ở `frontend/src/utils/formatters.ts`:
   - `STATUS_MAP` (label tiếng Việt)
   - `STATUS_COLOR` (1 trong 6: COLOR_GREEN/BLUE/YELLOW/ORANGE/RED/PURPLE/GRAY)

2. Audit script trước khi tag release:
   ```bash
   # Dump all states từ workflow JSON files:
   for wf in assetcore/assetcore/workflow/*.json; do
     python3 -c "import json; d=json.load(open('$wf')); [print(s['state']) for s in d['states']]"
   done | sort -u > /tmp/be_states.txt
   # Dump all keys trong STATUS_MAP:
   grep -oE "^\s+'[A-Z][^']*':" frontend/src/utils/formatters.ts | sed "s/.*'\([^']*\)'.*/\1/" | sort -u > /tmp/fe_labels.txt
   # Diff:
   comm -23 /tmp/be_states.txt /tmp/fe_labels.txt
   # Output không rỗng → có state thiếu label → bug.
   ```

3. **KHÔNG dùng local `XXX_LABELS` map trùng lặp** trừ khi key thuộc namespace khác (vd: frequency, severity-only) — dùng STATUS_MAP làm primary, dùng local map cho enum không phải workflow state (vd `FREQUENCY_LABELS = { Daily, Weekly, ... }`).

4. Cross-reference: `wave2Labels.ts:stateLabel()` ĐÃ có labels nhưng `StatusBadge.vue` dùng `formatters.ts:translateStatus()` → CHỌN MỘT map. Hiện `formatters.ts` là canonical.

### LL-FE-31: BE thêm Link field mới → FE detail/list PHẢI render `_name` companion

Bug session 2026-05-26: BE commit 83884c8 wire `linked_incident` / `source_type` / `source_ref` cho `IMM CAPA Record`, nhưng FE `CAPADetailView.vue` chỉ render `finding_ref` cũ → linked incident invisible.

**Quy tắc:**

1. Khi BE commit thêm Link field mới trên DocType + enrich `<field>_name` trong service:
   - FE phải thêm vào TypeScript type (`api/<module>.ts`)
   - Detail view phải thêm section render với fallback `(x as any).foo_name || x.foo`
   - List view (nếu cột hiển thị) phải dùng `_name` ưu tiên
2. Pattern chuẩn rendering Link với fallback navigate:
   ```vue
   <div v-if="capa.incident_ref">
     <p class="t-eyebrow">Sự cố nguồn</p>
     <button class="font-mono text-brand-700 hover:underline"
             @click="router.push(`/incidents/${capa.incident_ref}`)">
       {{ capa.incident_ref }}
     </button>
     <span v-if="capa.incident_subject" class="text-xs text-slate-500 ml-2">
       — {{ capa.incident_subject }}
     </span>
   </div>
   ```
3. Cross-check: sau BE merge, grep FE detail view có reference đến field mới không. Nếu không → gap, mở FE follow-up.

### LL-FE-32: Cell `'—'` khi data có nghĩa null vs khi data CÓ nhưng FE không render

Bug session 2026-05-26: IMM-03 Decisions list cột "Đơn hàng đã mint" hiển thị `AC-PUR-2026-00011` (raw code). BE enrich `ac_purchase_ref_name` nhưng FE template không dùng → user thấy code, không thấy tên.

**Quy tắc cell render Link field:**

```vue
<!-- ❌ SAI: chỉ raw value -->
<td>{{ d.ac_purchase_ref || '—' }}</td>

<!-- ✅ ĐÚNG: prefer _name, fallback raw (raw vẫn meaningful nếu doc name là PO code chính nó) -->
<td>{{ (d as any).ac_purchase_ref_name || d.ac_purchase_ref || '—' }}</td>
```

Khi `_name` là `null` (field display ở DB chưa populate), fallback về `d.ac_purchase_ref` (doc name) là ACCEPTABLE — user vẫn thấy identifier. Backfill data quality là backlog, không phải FE bug.

### LL-FE-33: Vue `(x as any)` cast pattern khi BE enrich field chưa có trong TS type

Tạm thời (trước khi update type): dùng `(x as any).foo_name || x.foo`. Đừng cast cả `(x as any)` cho thân lớn — chỉ inline để type-check không fail.

Lý tưởng: sau khi BE merge, update `api/<module>.ts` interface:
```typescript
export interface CapaDetail extends CapaRecord {
  incident_ref?: string
  incident_subject?: string
  linked_incident?: string | null
}
```
Sau đó remove `as any` cast.

### LL-FE-21: Sidebar / module-context detection PHẢI synchronous từ URL — không chờ `afterEach`

Bug 2026-05-26 (BUG-003): Deep-link `/pm/schedules` → sidebar hiển thị "Trang này không thuộc module nào. Mở Launcher để chọn module." trong 2–3s, action button bị disabled trong khoảng đó. Root cause: `currentModule` chỉ set bởi `router.afterEach` guard → guard chạy SAU first paint.

**Quy tắc:**

1. **`router.isReady()` await trước `app.mount()`** — đảm bảo first paint đã có `route.meta.moduleId`:
   ```ts
   // main.ts
   import { router } from './router'
   const app = createApp(App)
   app.use(router)
   await router.isReady()      // ← bắt buộc
   app.mount('#app')
   ```
2. **Sidebar fallback URL-based, đồng bộ**: extract `resolveModuleId(pathname)` từ router's regex table, export, để sidebar dùng làm fallback khi `route.meta.moduleId` chưa hydrate:
   ```ts
   // router/index.ts
   export function resolveModuleId(path: string): string | undefined {
     for (const [regex, mod] of MODULE_RULES) if (regex.test(path)) return mod
   }
   // AppSidebar.vue
   const currentModuleId = computed(
     () => route.meta.moduleId || resolveModuleId(route.path)
   )
   ```
3. **Action buttons KHÔNG được phụ thuộc `currentModule` hydration** — gate qua `useCapabilities().can('xxx')` thay vì `!!currentModule`.
4. Self-check: thử reload trang ở mọi sub-route — sidebar phải hiển thị module đúng ngay tức thì.
5. Reference: `frontend/src/router/index.ts:resolveModuleId`, `components/common/AppSidebar.vue`, `main.ts:isReady`.

### LL-FE-22: Empty `ROLES_*` stub arrays = silent permission denial

Bug 2026-05-26 (BUG-006/007/011): Calibration "Bắt đầu" + Training "Thêm học viên" + Competency "Nhập điểm" — buttons exist nhưng không render vì gate `auth.hasAnyRole(ROLES_CAL_EXECUTE)` evaluated false. Root cause: `ROLES_CAL_EXECUTE` (và các array khác) được giữ là `[]` trong `frontend/src/constants/roles.ts` như legacy stub — không có role nào pass.

**Quy tắc:**

1. **Empty `ROLES_*` array TRONG roles.ts = bug**. Hoặc fill role names đúng, hoặc xóa hẳn const và migrate caller sang `can('<cap>')`.
2. **Forbidden**: `auth.hasAnyRole(ROLES_*)` cho gating workflow buttons. Required: `useCapabilities().can('<domain>.<ptype>')` — đã sync với BE `rbac.require()`.
3. **Audit trigger**: nếu thấy `ROLES_*` empty `[]` ở roles.ts → grep usage, migrate hết:
   ```bash
   grep -E "^export const ROLES_\w+\s*=\s*\[\s*\]" frontend/src/constants/roles.ts
   # Mỗi empty const → grep usage để migrate
   grep -rn "ROLES_CAL_EXECUTE\|ROLES_TRAINING_MANAGE" frontend/src/
   ```
4. CONVENTIONS §11 đã forbid `hasAnyRole(ROLES_*)` — empty arrays là FE-side violation chính của rule này.
5. Reference: `composables/useCapabilities.ts`, `services/shared/rbac.CAPABILITY_MAP`.

### LL-FE-23: Khi action không render do permission, PHẢI show explicit hint — không silent empty panel

Bug 2026-05-26 (BUG-006/007): User mở Calibration "Đã lên lịch" + Training "Đã lập kế hoạch" → action panel hoàn toàn trống. User kết luận "tính năng vỡ" → ghi vào regression report. Thực tế chỉ là role thiếu.

**Quy tắc:**

1. Mỗi action panel phải có fallback hint khi tất cả buttons bị gate ra:
   ```vue
   <div v-if="canAnyAction" class="flex gap-2">
     <button v-if="canStart" @click="doStart">Bắt đầu</button>
     <button v-if="canCancel" @click="doCancel">Hủy</button>
   </div>
   <div v-else-if="isNonTerminal" class="alert-amber text-xs">
     Bạn không có quyền thực hiện hành động trên phiếu này.
     Liên hệ quản trị để cấp role <b>Calibration User/Manager</b>.
   </div>
   ```
2. Hint chỉ render khi state non-terminal (terminal state không có action nào là expected).
3. Có thể nâng cấp: hiển thị tên role/capability cần có (UX bonus).
4. Self-check khi audit: navigate đến mỗi DetailView ở từng state, KHÔNG có panel nào empty mà không có giải thích.
5. Reference: `views/calibration/CalibrationDetailView.vue` (showPermissionHint), `views/training/SessionDetailView.vue`.

### LL-FE-24: DocType cross-reference — copy đúng string, không gõ lại

Bug 2026-05-26 (BUG-019 — BE-side nhưng FE cũng dính): Một file dùng `"AC Department"` 3 lần đúng + 1 lần `"Department"` sai → crash. Pattern này gặp ở FE qua type strings, API call paths, store action names.

**Quy tắc (FE-side):**

1. **Copy-paste DocType string từ existing usage** trong file thay vì gõ lại từ trí nhớ.
2. **Self-check khi thêm `frappeGet`/`frappePost`** với hardcoded path: verify path khớp `assetcore/api/<module>.<func>` thực tế:
   ```bash
   # Endpoint path FE
   grep -oE "assetcore\.api\.\w+\.\w+" frontend/src/api/immXX.ts | sort -u
   # Function names BE
   grep -E "^def \w+" assetcore/api/immXX.py
   ```
3. Reference: BE-side LL-BE-10.

### LL-FE-25: Dual-display Link field — name primary + code subtitle là pattern chuẩn

Pattern chuẩn 2026-05-26 (verified `AssetDetailView.vue:306-323`): trường Link hiển thị 2 dòng — dòng 1 display name (text-base), dòng 2 raw code (text-xs slate-400 subtitle, chỉ hiện khi cả 2 đều có).

```vue
<dt class="text-slate-400 shrink-0">Nhà cung cấp</dt>
<dd>
  <div>{{ doc.supplier_name || doc.supplier || '—' }}</div>
  <div v-if="doc.supplier && doc.supplier_name"
       class="text-xs text-slate-400">{{ doc.supplier }}</div>
</dd>
```

**Quy tắc**:
- Dòng 1 (primary): luôn `*_name || *` — name có ưu tiên, fallback code, fallback `—`
- Dòng 2 (subtitle): CHỈ hiển thị khi BOTH name + code có giá trị
- KHÔNG xóa subtitle để "clean UI" — operations team cần code để query trong Frappe Desk
- Khi audit bằng Playwright `browser_evaluate`: probe theo label+valueGroup, không chỉ leaf-text (xem `assetcore-test` LL-TEST-13). False positive "code leak" thường vì leaf-probe chỉ bắt subtitle.

### LL-FE-26: Role-gated action panel — bắt buộc empty-state hint cho user không quyền

Bug session 2026-05-26: `CalibrationDetailView.vue` state "Đã lên lịch" không hiện button nào cho user role thấp (Chu Hiếu thiếu CAL_EXECUTE). Workflow JSON có 3 transitions; FE wire đúng; nhưng UI dead-end.

```vue
<!-- ❌ SAI — silent empty panel khi user thiếu role -->
<div class="actions">
  <button v-if="canExecuteCal">Bắt đầu hiệu chuẩn</button>
  <button v-if="canManageCal">Hủy phiếu</button>
</div>

<!-- ✅ ĐÚNG — empty-state hint khi không button nào render -->
<div class="actions">
  <button v-if="canExecuteCal">Bắt đầu hiệu chuẩn</button>
  <button v-if="canManageCal">Hủy phiếu</button>
  <div v-if="!canExecuteCal && !canManageCal && !isTerminal"
       class="text-sm text-slate-500 italic">
    Không có hành động khả dụng cho vai trò hiện tại.
    Liên hệ {{ ROLE_OWNER_HINT[currentStateGroup] || 'quản trị viên' }} để xử lý.
  </div>
</div>
```

**Quy tắc** (cross-ref [[LL-FE-23]]):
- Mọi DetailView panel có 2+ buttons gate bằng `v-if="canXxx"` PHẢI có hint khi tất cả ẩn
- Hint: (1) tại sao ẩn, (2) role nào có thể, (3) action — "Liên hệ KTV"
- Terminal states (Completed/Cancelled/Closed) miễn hint — đặt cờ `isTerminal` để loại
- Audit grep:
  ```bash
  for f in frontend/src/views/**/*DetailView.vue; do
    btns=$(grep -c 'v-if="can' "$f")
    hint=$(grep -c 'Không có hành động khả dụng\|Bạn không có quyền' "$f")
    [ "$btns" -ge 2 ] && [ "$hint" -eq 0 ] && echo "MISSING HINT: $f ($btns gated buttons)"
  done
  ```

### LL-FE-27: Nghi ngờ "FE thiếu enrich" — chạy `bench execute` xem response TRƯỚC khi sửa FE

Bug 2026-05-26 (FP avoidance): UI hiển thị raw code → reflex sửa FE thêm `*_name || *`. Thực tế BE đã enrich, FE template đã đúng, chỉ là DOM probe sai layer.

**Diagnostic procedure TRƯỚC khi đụng FE**:
```bash
# 1. Check BE service trả gì
bench --site miyano execute assetcore.api.imm00.get_asset --kwargs '{"name":"AC-ASSET-2026-00407"}' \
  | grep -oE '"supplier_name":[^,]*|"location_name":[^,]*'

# 2. Nếu BE trả đúng → check FE store có overwrite không
grep -n "currentAsset\|setAsset" frontend/src/stores/<module>.ts

# 3. Nếu store OK → check template binding
grep -n "supplier\|location" frontend/src/views/<domain>/<X>DetailView.vue

# 4. Nếu cả 3 layer đúng → cache stale (TanStack Query) hoặc DOM probe sai (xem LL-TEST-13)
```

### LL-FE-28: Audit Trail Tab — mọi DetailView nghiệp vụ PHẢI có (2026-05-27)

**Bug RC-05:** Phiếu nghiệm thu (ACC) tab "Lịch sử phiếu" trống dù BE đã log `IMM Audit Trail`. Nguyên nhân: FE detail view không render tab Lịch sử, hoặc render nhưng query sai filter.

**Quy tắc:**

1. Mọi `XxxDetailView.vue` của DocType nghiệp vụ PHẢI có tab "Lịch sử phiếu" (hoặc "Lịch sử thay đổi"):
   ```vue
   <Tabs>
     <Tab id="info">Thông tin</Tab>
     <Tab id="workflow">Quy trình</Tab>
     <Tab id="history">Lịch sử phiếu</Tab>
   </Tabs>

   <TabPanel id="history">
     <AuditTrailTab :doctype="DOCTYPE" :name="doc.name" />
   </TabPanel>
   ```

2. **Component canonical**: `<AuditTrailTab>` ở `components/common/AuditTrailTab.vue`. Nếu chưa tồn tại, tạo trong PR đầu tiên touching nhiều DetailView. Component bắt buộc:
   - Merged timeline (lifecycle events + audit trail + workflow transitions)
   - Sort timestamp desc
   - Mỗi row: actor + action + timestamp + change_summary
   - Click vào row → expand JSON diff (nếu có)

3. **API endpoint chuẩn**: `assetcore.api.audit.list_for_doc(doctype, name)` → response merged + sorted.

4. **Empty state actionable**: nếu timeline trống → text + warning:
   ```vue
   <div v-if="!events.length" class="text-center py-8">
     <p class="text-gray-500">Chưa có sự kiện được ghi nhận</p>
     <p class="text-xs text-amber-600 mt-2">
       ⚠️ Nếu phiếu đã có nhiều thao tác mà ô này trống — báo dev (BE có thể chưa log).
     </p>
   </div>
   ```
   Empty silent = bug ẩn (hook chain BE thiếu — xem LL-BE-23).

5. **Self-check trước khi đóng task DetailView**:
   ```bash
   for f in frontend/src/views/**/[A-Z]*DetailView.vue; do
     grep -L "AuditTrailTab\|Lịch sử" "$f" && echo "GAP: $f"
   done
   ```

Reference: `CONVENTIONS.md §42`, `assetcore-be` LL-BE-23 (hook chain), `assetcore-audit` Pillar 5 + Pillar 9.

### LL-FE-29: KPI Scope Disambiguation — label phải nêu rõ phạm vi (2026-05-27)

**Bug RC-09, RC-10:** `/dashboard` báo "Phiếu chờ duyệt: 3" trong khi `/approvals/pending` báo "0". Cả 2 đúng theo logic riêng (toàn hệ thống vs của tôi) nhưng user thấy mâu thuẫn → mất niềm tin vào số liệu.

**Khác LL-FE-17** (KPI count phải bằng list count cùng filter): LL-FE-29 nói về SCOPE LABELING khi 2 trang khác phạm vi.

**Quy tắc:**

1. **Mọi `<KpiTile>` PHẢI có scope qualifier** trong label:
   ```vue
   <!-- ❌ SAI -->
   <KpiTile label="Phiếu chờ duyệt" :value="3" />

   <!-- ✅ ĐÚNG -->
   <KpiTile label="Phiếu chờ duyệt toàn hệ thống" :value="3" :scope="'all'" />
   <KpiTile label="Phiếu chờ duyệt của tôi" :value="0" :scope="'mine'" />
   ```

2. **Scope enum chuẩn** (chọn 1 — type-safe trong TS):
   ```typescript
   export type KpiScope = 'all' | 'mine' | 'department' | 'overdue' | 'next7d'

   const SCOPE_LABEL: Record<KpiScope, string> = {
     all: 'toàn hệ thống',
     mine: 'của tôi',
     department: `khoa ${userStore.department}`,
     overdue: 'quá hạn',
     next7d: '7 ngày tới',
   }
   ```

3. **Click KPI → navigate phải pass scope qua query param**:
   ```typescript
   const onKpiClick = (kpi: KpiDef) => {
     router.push({ path: kpi.target, query: { scope: kpi.scope }})
   }
   ```
   List view đọc `route.query.scope` apply cùng filter — count khớp 100%.

4. **Single-source service** (BE) — nhận `scope` param thay vì 2 endpoint riêng (xem LL-BE-23 hook chain idempotent pattern):
   ```typescript
   // FE API
   countPendingApprovals(scope: KpiScope = 'all'): Promise<number>
   ```

5. **Self-check** (chạy trước commit dashboard/widget):
   ```bash
   grep -rnE "label=\"(Phiếu|Đơn|Yêu cầu|PM|CM|Lịch|Báo cáo)[^\"]*\"" frontend/src/views/ \
     | grep -v "toàn hệ thống\|của tôi\|tôi phụ trách\|khoa\|quá hạn\|7 ngày\|tháng này"
   # Mỗi match → review xem có cần scope không
   ```

6. **Document scope trong page header**: list page có filter scope → render `<PageHeader subtitle="Hiển thị: Của tôi" />` để user thấy ngay phạm vi đang xem.

Reference: `CONVENTIONS.md §43`, `assetcore-fe` LL-FE-17 (KPI consistency — bổ trợ).
