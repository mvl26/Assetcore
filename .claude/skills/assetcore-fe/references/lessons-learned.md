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

**Bug 2026-05-27** (IMM-06 CompetencyListView): `c.device_model` render `IMM-MDL-2026-0023` thay vì "Dräger Evita V500" — BE quên enrich + FE quên fallback. Fix yêu cầu cả 2 phía.

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
2. Chạy GATE-2 grep trước khi mark Done — bắt mọi biến (`row`, `item`, `doc`, `c`, `r`, `x`) reference Link field thiếu `_name`.
3. Nếu BE chưa enrich `<field>_name`, FE KHÔNG được hardcode lookup ở FE — sửa BE (xem `assetcore-be` LL-BE-2) rồi FE mới render.

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

   **Audit-list key thường thiếu** (Wave2 — phải có entry, áp grep cả DetailView + dashboard card, KHÔNG chỉ ListView): `Under Maintenance`→'Đang bảo trì', `Scheduled`→'Đã lên lịch', `Locked`, `Evaluated`, `Contract Signed`, `Weekly`, `Minor`. Bug IMM-12-A (dashboard cards 'Open'/'In Progress') + IMM-11-B (Cal detail 'Scheduled' dù list đã đúng) lọt vì detail+card quên áp map dù list đúng → mở rộng phạm vi grep GATE-1/GATE-2 sang detail+card.

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
4. `hasAnyRole(ROLES_*)` is forbidden — empty arrays là FE-side violation chính của rule này.
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

Reference: `assetcore-be` LL-BE-23 (hook chain), `assetcore-audit` Pillar 5 + Pillar 9.

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

Reference: `assetcore-fe` LL-FE-17 (KPI consistency — bổ trợ).

### LL-FE-39: KPI/tile clickable PHẢI có đích lọc THẬT — nếu không thì render TĨNH (2026-05-29)

> (Trước đây đánh số LL-FE-34 — đổi thành LL-FE-39 để nhường số 34 cho Responsive DoD theo ADR-IMM00-RESPONSIVE D5; nội dung KHÔNG đổi.)

**Bug đã gặp 2026-05-29 (IMM-05 document KPI):** tile "Thiết bị thiếu hồ sơ" được làm clickable → `router.push('/assets?filter=missing-docs')`, nhưng `/assets` **KHÔNG handle** query `filter=missing-docs` → điều hướng tới list hiển thị **toàn bộ asset** (không lọc) → user tưởng đang xem "thiếu hồ sơ" nhưng thấy tất cả. **Đổi một dead-end ("đang phát triển" toast) lấy một điều hướng SAI LỆCH — còn tệ hơn** (LL-FE-17/29: KPI count ≠ list count).

**Quy tắc:**

1. Một KPI/tile chỉ được clickable khi có **đích lọc THẬT đã verify**: route + filter mà list đích thực sự áp dụng, count khớp KPI. Verify bằng grep route đích có đọc `route.query.<param>` không:
   ```bash
   grep -rn "route.query.<param>\|<param>=" frontend/src/views/<đích>/*ListView.vue
   # rỗng = đích CHƯA lọc → KHÔNG được làm clickable
   ```
2. **Không có đích lọc thật → render TĨNH** (informational): cờ `clickable: false` + `hint` mô tả "chỉ tiêu thống kê", KHÔNG `@click`, KHÔNG cursor pointer. Tách data-driven:
   ```ts
   // KPI_FILTERS: mỗi tile có clickable + hint; tile không có buildFilter thật → clickable:false
   { kind: 'missing', label: 'Thiết bị thiếu hồ sơ', clickable: false,
     hint: 'Số thiết bị chưa có hồ sơ — chỉ tiêu thống kê (lọc chi tiết bổ sung sau)' }
   ```
   ```vue
   <template v-for="t in tiles" :key="t.kind">
     <button v-if="t.clickable" @click="filterByKpi(t.kind)"><KpiCard .../></button>
     <div v-else class="kpi-static" :title="t.hint"><KpiCard .../></div>
   </template>
   ```
3. **Guard hàm filter**: `if (buildKpiFilter(kind) === null) return` — không điều hướng khi không có filter thật.
4. Self-check: mỗi tile/widget clickable → click thử, list đích PHẢI đổi đúng + count khớp. Không khớp/không đổi = bug → chuyển tĩnh hoặc làm đích lọc thật.

**Verify-before-fix (cross-ref LL-BE-29):** đừng "fix" dead-end bằng cách điều hướng đại tới route chưa lọc — verify đích có lọc thật trước.

Reference: `views/document/{DocumentManagement.vue,documentFilters.ts}`, LL-FE-13 (no dead-end), LL-FE-17/29 (KPI consistency/scope).

### LL-FE-35: FE api-client function PHẢI trỏ method BE whitelisted có thật — dead endpoint 404 là trap (2026-06-01)

**Bug đã gặp 2026-06-01 (audit AUTH):** `api/auth.ts` có `approveRegistration()` trỏ `assetcore.api.auth.approve_registration` — method **KHÔNG TỒN TẠI** (404). Không caller (view dùng bản đúng từ `api/user.ts`), nhưng là bẫy chờ nổ: ai gọi nhầm → 404 runtime, không bắt được lúc typecheck.

**Quy tắc:**

1. Mỗi hàm trong `frontend/src/api/*.ts` phải map tới một `@frappe.whitelist()` method có thật. Khi viết/sửa api-client, grep ngược BE xác nhận tồn tại:
   ```bash
   grep -rnE "method: *['\"]assetcore\.[\w.]+" frontend/src/api/   # method FE gọi
   grep -rn "def approve_registration" assetcore/api/              # có whitelist tương ứng?
   ```
2. Hai api-client cùng chức năng (vd `auth.ts` vs `user.ts`) → kiểm bản nào có caller thật, xoá bản dead (đừng để 2 đường gọi lệch endpoint).
3. Self-check trước commit: api-client method không có caller VÀ không có BE method tương ứng = dead → xoá ngay.

Cross-ref: [[LL-BE-35]] (verify live wired path), LL-FE-24 (copy đúng string cross-reference).

### LL-FE-36: Route cap-gate PHẢI mirror sidebar cap — thiếu quyền = ẩn + redirect, KHÔNG render trang "không có quyền" (2026-06-01)

**Bug user báo:** vào `/suppliers` thấy trang + thông báo "Bạn không có quyền thực hiện hành động này." thay vì bị ẩn. **Root cause:** route master/system khai `moduleId='master'` → `moduleIdToCap('master')=null` → `resolveRouteAccess` rơi xuống default **allow**. Sidebar gate `data.read` (ẩn menu) NHƯNG route hở → user gõ URL thẳng vẫn vào, thấy list rỗng + câu "không có quyền". Lệch giữa nav-gate và route-gate.

**Quy tắc:**

1. MỌI route nghiệp vụ PHẢI có `meta.requiredCapabilities` (hoặc cap suy từ moduleId) **khớp đúng** cap mà sidebar dùng để ẩn/hiện cùng mục. Nav ẩn nhưng route hở = bug bảo mật/UX.
2. Thiếu quyền là **ẩn + chặn sớm**: route guard `resolveRouteAccess` redirect `/unauthorized` (hoặc dashboard) TRƯỚC khi render. KHÔNG để vào trang rồi mới hiện "bạn không có quyền" như luồng chính (component guard chỉ là defense-in-depth tầng cuối).
3. Audit drift định kỳ: với mỗi mục sidebar có cap, route tương ứng phải có đúng cap đó.
   ```bash
   grep -nE "requiredCapabilities|moduleId" frontend/src/router/index.ts
   grep -nE "cap:" frontend/src/constants/sidebarNav.ts
   # mọi path trong sidebarNav có cap → path đó trong router phải có cap khớp
   ```
4. Giữ mở có chủ đích (route không gate) chỉ khi sidebar cũng không gate (vd `/assets`, `/qr-scan`) — ghi rõ lý do, đừng siết nhầm.
5. Test: `routeAccess.test.ts` — user thiếu cap navigate tới route → `next({name:'Unauthorized'})`; có cap → pass.

Cross-ref: LL-FE-37 (cap granularity), [[LL-BE-38]] (FE ẩn ≠ BE bảo vệ), LL-AUDIT-10.

### LL-FE-37: KHÔNG gate nav theo persona bằng capability chung quá rộng (vd `data.read`) (2026-06-01)

**Bug user báo:** user persona Document/Training (vd `sohaidiuuu@gmail.com`) THẤY mục `/depreciation` (khấu hao — domain tài chính, không liên quan). **Root cause:** mục Khấu hao gate `data.read`; mà `data.read` resolve qua `frappe.has_permission("IMM Device Model","read")` — Device Model là danh mục dùng-chung → **mọi** user AssetCore có `data.read=True` → cap này KHÔNG phân biệt được persona → lộ cho doc/training.

**Quy tắc:**

1. Cap dùng để gate mục nav **đặc thù persona** KHÔNG được là cap chung mà gần như mọi user đều có (`data.read` cấp qua read danh mục dùng-chung). Chọn cap đúng phạm vi persona, hoặc OR nhiều cap đặc thù.
   ```ts
   // Khấu hao: gate bằng tổ hợp cap tài chính/vận hành, KHÔNG phải data.read
   const FINANCE_READ_CAPS = ['data.write','needs.read','procurement.read','pm.read','calibration.read']
   ```
2. Khi thêm/sửa cap gate cho 1 mục: thử nghiệm với ≥2 persona KHÔNG nên thấy mục đó (vd doc, store) → xác nhận `rbac.can(cap)=false`. Đừng tin cap "nghe có vẻ đúng".
3. Verify thật: `frappe.set_user("<persona user>")` rồi eval `rbac.can('<cap>')` cho từng persona trong/ngoài phạm vi.
4. Mục nav + route phải gate **cùng** cap (xem LL-FE-36). Cap khai song song 2 file (sidebarNav + router) → comment ràng buộc "giá trị phải khớp".

Cross-ref: LL-FE-36 (route↔nav gate), [[LL-BE-38]] (over-grant DocPerm là gốc của cap rộng), Core Doc `FE_Persona_Navigation.md §7.septies`.

### LL-FE-38: KHÔNG có persona/role switcher client-side — nav derive từ ROLE THẬT; persona = nhãn FE, không render ở chrome (2026-06-01)

**Bối cảnh (yêu cầu user, nhiều vòng):** FE từng có "persona switcher" góc phải (dropdown tự đổi persona) + render nhãn persona ("Cán bộ hồ sơ"...) ở header sidebar góc trái. User yêu cầu bỏ: quyền & giao diện phải theo ROLE THẬT của session, không phải lựa chọn client-side; và không hiển thị nhãn persona ở chrome chung.

**Kiến trúc đã chốt (giữ nguyên, đừng đảo):**

1. **BE = chuẩn Frappe**: Role Profile + DocPerm. BE KHÔNG biết khái niệm "persona".
2. **Persona = lớp trình bày FE-only**: mapping persona ↔ Role Profile sống ở `frontend/src/constants/personas.ts` (`roleProfile`, `roleProfileForPersona()`/`personaForRoleProfile()`). Gán "theo persona" ở màn admin = FE dịch persona → Role Profile → gọi `assign_role_profile()` (API thuần Frappe).
3. **Nav derive từ role THẬT** session: `buildSidebarGroupsForRoles(personas, can, isSuperuser)` union các persona mà role thật mở khoá, dedupe path, lọc theo capability. KHÔNG có dropdown cho user tự đổi persona.
4. **`usePersona` là read-only** (`{ personas, primaryPersona }`) — KHÔNG có `setPersona`/`canSwitch`; KHÔNG persist `ac_persona` localStorage.
5. **Chrome KHÔNG render nhãn persona**: header sidebar = hằng "AssetCore". Badge Role Profile ở màn quản trị user (`UserProfileFormView`) thì GIỮ (context admin hợp lệ — là nhãn Role Profile chứ không phải "persona nav").

**Quy tắc:** thấy đề xuất thêm "đổi persona/role ở UI để xem giao diện khác" → TỪ CHỐI; phân quyền + nav phải theo role thật. Muốn test nhiều persona → tạo user test có role tương ứng (`scripts/seed_test_users.py`), đăng nhập từng user.

Cross-ref: LL-FE-36/37 (gate theo role thật), [[LL-BE-37]] (gán role qua admin), Core Doc `FE_Persona_Navigation.md §7.bis–7.septies`.

### LL-FE-34: Responsive DoD (mobile-first) — 5 pattern P1-P5, breakpoint sm/md/lg/xl, modal full-screen mobile (2026-06-10)

**Bối cảnh (ADR-IMM00-RESPONSIVE, Accepted 2026-06-09):** KTV TBYT làm việc tại hiện trường cầm phone quét tem QR → cần xem danh sách / báo hỏng / tạo WO ngay trên mobile. FE có pattern responsive rải rác (37 view dùng `hidden sm:block`/`sm:hidden`) NHƯNG không DoD bắt buộc → view mới quên → bảng tràn ngang, tab-bar cắt, touch <44px. Đây là họ bug kế tiếp sau English/raw-code leak (memory `wave2_ui_bugs`).

**Breakpoint chuẩn (Tailwind DEFAULT — KHÔNG custom px, KHÔNG `theme.screens`):**

| Prefix | min-width | Persona |
|---|---|---|
| (base) | 0 | Mobile — KTV hiện trường (phone) |
| `sm:` | 640px | Phone ngang / phablet |
| `md:` | 768px | Tablet — QL vật tư |
| `lg:` | 1024px | Laptop |
| `xl:` | 1280px | Desktop — admin |

- **Mobile-first:** class base = trạng thái mobile; thêm `sm:`/`md:`/`lg:` cho màn lớn hơn. KHÔNG `max-sm:` ngược chiều trừ bất khả kháng.
- **KHÔNG PWA** (service worker / manifest / offline cache / "install app"). Responsive web thuần.
- **KHÔNG custom breakpoint px** — cấm `min-[900px]:` / `max-[...]:` ad-hoc trong `src/views`. md/lg đã đủ. (Lưu ý: `min-h-[44px]`/`min-w-[44px]` là touch-target, KHÔNG phải media-prefix breakpoint — hợp lệ.)

**5 PATTERN BẮT BUỘC (vi phạm = blocker FE-DoD, `assetcore-audit` Pillar 6 flag 🟠):**

| # | Pattern | Class chốt | Áp cho |
|---|---|---|---|
| P1 | List = table→card | desktop `<table>` bọc `hidden sm:block`; mobile `<div class="mobile-card-list sm:hidden">` mỗi record 1 card | mọi List view |
| P2 | Form = 1-col mobile → 2-col desktop | `grid grid-cols-1 md:grid-cols-2 gap-*` | mọi form create/edit |
| P3 | MỌI `<table>` bọc `overflow-x-auto` | `<div class="overflow-x-auto"><table>…</table></div>` | mọi bảng (kể cả khi có card-list — bảng desktop vẫn cần) |
| P4 | Tab-bar / chip-bar dài cuộn được | `overflow-x-auto` (cuộn ngang) HOẶC `flex-wrap` trên container; mỗi item `shrink-0` | mọi tab-bar/chip-bar (vd AssetDetail 5 tab) |
| P5 | Touch target ≥44px | `min-h-[44px] min-w-[44px]` (hoặc `h-11 w-11`) | mọi nút icon/action chạm bằng ngón tay |

**Modal full-screen mobile (D3):**
- Mobile (base): `inset-0 w-full h-full rounded-none max-h-screen` — chiếm full viewport, dễ thao tác ngón tay, không tràn.
- `sm:`+ : centered card `sm:inset-auto sm:m-auto sm:w-full sm:max-w-* sm:rounded-2xl sm:h-auto sm:max-h-[90vh]`.
- Nút đóng modal ≥44px (P5).
- `BaseModal.vue` + ⌘K `CommandPalette.vue` ĐỒNG BỘ rule này (CommandPalette full-screen mobile qua scoped CSS `@media (max-width:639px)`).

**Self-check (chạy trước khi nói DONE):**
```bash
# D1 — không ad-hoc breakpoint px trong views (touch-target min-h-[44px] KHÔNG tính):
grep -rnE '\b(min|max)-\[[^]]+\]:' frontend/src/views   # = 0
# P3 — mọi <table> trong views có ancestor overflow-x-auto.
# P1 — mọi List view có cặp hidden sm:block (table) + sm:hidden (card-list).
# Playwright viewport 375px: body scrollWidth <= clientWidth (0 horizontal-scroll); tab cuối reachable; modal full-screen.
```

**Anti-pattern PHẢI tránh:** `<table>` không bọc `overflow-x-auto` → tràn mobile · custom breakpoint px ad-hoc · tab-bar không cuộn → cắt item cuối · nút icon <44px · modal centered cố định mobile · PWA/service worker (ngoài scope) · quên DoD → lặp bug mỗi vòng.

**Light-touch:** KHÔNG audit-rewrite 37 view đã đúng — chỉ áp DoD cho view MỚI + 4 gap đã verify (`AssetDetailView` tab-bar, `PersonaDashboardShell` KPI tablet, `RCAListView` card, `ListCard` table overflow) + `BaseModal` full-screen.

Cross-ref: ADR-IMM00-RESPONSIVE (D1-D5), `component-patterns.md` ## Responsive, LL-FE-25 (dual-display Link), memory `wave2_ui_bugs`.

### LL-FE-40: CẤM raw `frappe.client.*` call ở FE — lookup phải qua endpoint AssetCore whitelisted permission-aware (2026-06-11)

**Triệu chứng:** BUG-META-1 — view/composable/store gọi thẳng `frappe.client.get_value/get_list/get` → 417 + bypass permission (frappe.client là generic CRUD, KHÔNG áp `permission_query_conditions` của AssetCore).
**Nguyên nhân:** DONE-gate cũ (GATE-1 EN-enum / GATE-2 raw-code / GATE-3 hardcoded-EN) KHÔNG cover raw frappe.client call → lọt.
**Rule kiểm được (PRE-DONE GREP GATE-4, output PHẢI = 0):**
```bash
grep -rnE "frappe\.client\.(get_value|get_list|get)" frontend/src/{views,composables,stores}
```
≠0 → thay bằng endpoint module whitelisted (`assetcore.api.<module>.<fn>` qua `frappeGet/frappePost`) permission-aware. KHÔNG skip.

Cross-ref: GATE-4 (SKILL.md PRE-DONE GREP GATE), LL-FE-35 (api-client trỏ method có thật), [[LL-BE-38]] (FE ẩn ≠ BE bảo vệ).

### LL-FE-41: Fieldname FE xin/khai PHẢI khớp EXACT fieldname DocType — `risk_class` ≠ `risk_classification` (field-name drift) (2026-06-11)

**Triệu chứng:** BUG-META-1 — `CalibrationCreateView.vue:86` xin field `risk_class` (∄, field thật = `risk_classification`); `Cal:19` define `risk_class?` sai trong TS interface → asset meta nhận về luôn `null` cho field đó → render em-dash dù record tồn tại.
**Nguyên nhân:** đặt fieldname theo trí nhớ, KHÔNG đối chiếu DocType. TS cast pass typecheck nhưng runtime field rỗng (BE không có key đó để trả).
**Rule kiểm được:** trước khi viết TS interface hoặc request `fields=[...]`, verify fieldname khớp EXACT DocType JSON HOẶC field BE thực trả — KHÔNG đặt theo trí nhớ:
```bash
grep -E '"fieldname"' assetcore/assetcore/doctype/<dt>/<dt>.json
# HOẶC copy key từ response thật:
bench --site miyano execute assetcore.api.imm00.get_asset --kwargs '{"name":"<id>"}'
```
Field rủi ro asset = `risk_classification` (KHÔNG `risk_class`). Self-check: field FE xin nhận về LUÔN `null`/`undefined` dù record tồn tại = nghi field-name drift → đối chiếu DocType JSON.

**Khác LL-FE-24** (DocType-string drift `"AC Department"` vs `"Department"`) — đây là FIELDNAME drift trong cùng 1 record.

Cross-ref: LL-FE-40 (raw client ban), LL-FE-42 (prefetch meta), LL-FE-8 (Select options match DocType JSON).

### LL-FE-42: Prefetch meta cho create-view (qr-scan prefill) — fetch fail/null → error-state + retry, KHÔNG render '—' im lặng (2026-06-11)

**Triệu chứng:** BUG-META-1 — create-view prefetch asset meta cho qr-scan prefill render '—' TOÀN BỘ block (asset_name/device_model_name/manufacturer_sn/risk_classification/location_name) dù asset tồn tại → user tưởng asset rỗng.
**Nguyên nhân:** prefetch đi qua endpoint sai (raw `frappe.client.get_value`, LL-FE-40) + field-name drift (`risk_class`→null, LL-FE-41) → meta CÓ data nhưng nhận về null → FE render '—' im lặng không báo lỗi.
**Rule kiểm được:** khi create-view prefetch asset/entity meta, fetch fail HOẶC trả null → KHÔNG render '—' im lặng; PHẢI show error-state + retry (tri-branch loading/error/data như list view). Test BẮT BUỘC: với asset hợp lệ, mọi nhãn meta render giá trị THẬT — assert KHÔNG render '—'/em-dash cho field BE trả non-null. Self-check: meta block toàn '—' khi asset tồn tại = prefetch hỏng → kiểm endpoint permission-aware (LL-FE-40) + field-name (LL-FE-41) TRƯỚC.

**Khác LL-FE-20/32** (computed/null cell hợp lệ khi data thực null) — đây là meta CÓ data nhưng prefetch hỏng.

Cross-ref: LL-FE-40, LL-FE-41, LL-FE-20 (computed render), LL-FE-32 (cell null vs not-rendered).

### LL-FE-43: qr-scan create-view PHẢI prefill SmartSelect locked text == asset code (2026-06-11)

**Triệu chứng:** BUG-PM-1 — vào create-view qua `?asset=<id>&source=qr-scan`, SmartSelect tài sản bị lock nhưng text hiển thị RỖNG (chỉ có id ngầm, user không thấy mã thiết bị).
**Nguyên nhân:** prefill set `v-model` (id) nhưng không hydrate label hiển thị của SmartSelect → locked control rỗng.
**Rule kiểm được (PRE-DONE GREP GATE-6a manual):** mỗi create-view có qr-scan prefill chạy parity test 4 view **PM / Incident / CM / Cal** → locked SmartSelect text == asset code (KHÔNG rỗng). Prefill phải set cả id + label (hoặc trigger load option để SmartSelect resolve label).

Cross-ref: GATE-6 (SKILL.md), LL-FE-9 (Link → SmartSelect), LL-FE-25 (dual-display Link).

### LL-FE-44: Form required-dropdown dựa list endpoint — case `total:0` phải có banner + ≥1 lối thoát actionable, KHÔNG chỉ disabled (2026-06-11)

**Triệu chứng:** BUG-PM-2 — form tạo WO với required-dropdown "Lịch bảo trì" lấy từ list endpoint; khi `total:0` (chưa có schedule) → dropdown disabled trống, submit bất khả → dead-end, user không biết phải làm gì.
**Nguyên nhân:** 0-state chỉ disable control, không hướng dẫn cách tạo nguồn dữ liệu thiếu.
**Rule kiểm được (PRE-DONE GREP GATE-6b manual):** mỗi form có required-dropdown dựa list endpoint chạy test-case `total:0` → PHẢI có banner giải thích + ≥1 lối thoát actionable (nút "Tạo lịch bảo trì" / navigate tới nơi tạo), KHÔNG chỉ disabled. Đồng pattern empty-state-actionable của LL-FE-13.

Cross-ref: GATE-6 (SKILL.md), LL-FE-13 (no dead-end UX), LL-FE-9 (Link → SmartSelect).

### LL-FE-45: prefetch ref/lookup PHỤ dùng `Promise.allSettled` — 1×403 KHÔNG được blank cả trang (2026-06-11)

**Triệu chứng:** Factory §Khác(c) — `Promise.all([...])` prefetch nhiều ref/lookup; 1 nhánh 403 → reject toàn bộ → blank cả trang dù phần chính load được.
**Nguyên nhân:** `Promise.all` fail-fast: 1 reject huỷ cả batch; ref phụ (vendor/location/category) thiếu quyền KHÔNG nên đánh sập màn hình.
**Rule kiểm được (PRE-DONE GREP GATE-5):**
```bash
grep -rn 'Promise.all(' frontend/src/{stores,composables}
```
review MỖI match: prefetch ref/lookup PHỤ → đổi `Promise.allSettled` (xử lý từng `result.status === 'fulfilled'`). Giữ `Promise.all` CHỈ khi mọi nhánh bắt buộc thành công (vd data chính của trang).

Cross-ref: GATE-5 (SKILL.md), LL-FE-23/26 (action ẩn do permission → hint, không silent), memory `factory_rounds_6_10` (allSettled ref-prefetch 403 không blank trang).

### LL-FE-46: UI/trang "xong" = RENDER THẬT chứng minh, KHÔNG chỉ vitest/structural xanh (2026-06-11)

**Triệu chứng→nguyên nhân:** Swagger UI page (`www/api-docs.html`) vitest + oas-test XANH nhưng trang render TRẮNG ("Unable to render this definition") vì feed spec bọc `{message:}` (F-C1). Unit/structural test KHÔNG chạm DOM render thật → "xanh" mà user thấy trang chết.

**Rule kiểm được:** deliverable UI/trang KHÔNG tuyên "xong" CHỈ bằng vitest/vue-tsc/structural xanh. Cần 1 trong:
1. **Render THẬT:** Playwright mở trang (@:3000) — assert có DOM/opblock/nội dung thật + console 0 error; HOẶC `curl` HTML đã serve + grep loader đúng (HTTP-wire, LL-TEST-26);
2. Nếu BLOCKED (reload-pending `api/*.py`, thiếu login persona) → ghi RÕ "blocked on reload/login", KHÔNG tuyên "trang hoạt động".
Endpoint spec/JSON mà trang FE tiêu thụ: unwrap envelope Frappe `payload.message || payload` + feed `spec:` object, KHÔNG `url:` thẳng (LL-BE-50).

Cross-ref: LL-BE-50 (`{message:}` envelope), LL-TEST-26 (assert render/wire thật), `references/playwright-patterns.md`; session 2026-06-11 F-C1.

### LL-FE-47: DEAD CONTROL = bug giao diện — control không đổi hành vi downstream (2026-06-11)

**Triệu chứng:** F1 — dropdown "Khổ tem" @AssetLabelPrintView render 3 option (Tem 50×30 / 70×40 / 60×100) NHƯNG `printAll()` HARDCODE `preset='tem-60x100'` ngay ở call-site → user chọn "Tem 50×30" vẫn in ra 60×100 IM LẶNG, không cảnh báo.
**Nguyên nhân:** control chỉ đổi state hiển thị/preview, giá trị thật bị hardcode ở call-site nên không truyền xuống logic/API → lựa chọn UI vô nghĩa.
**Rule kiểm được:** mọi control (dropdown/toggle/radio/checkbox) PHẢI thật sự đổi param/logic downstream — KHÔNG để giá trị bị hardcode ở call-site. Test BẮT BUỘC: assert **param phát đi (body/query/store) == lựa chọn UI** — chọn option B → spy nhận B; KHÔNG chỉ assert "render đủ N option". Red-flag: "control chỉ đổi state hiển thị/preview, không truyền xuống API".

Cross-ref: LL-FE-48 (verify render thật khổ in), LL-FE-46 (xanh structural ≠ render thật), LL-TEST (assert param/artifact thật); session 2026-06-11 F1.

### LL-FE-48: Layout in/khổ-cố-định — `overflow:hidden` CẮT chữ ÂM THẦM → verify bằng RENDER ẢNH THẬT (2026-06-11)

**Triệu chứng:** tem 50×30 / 70×40 — mã/tên dài wrap rồi bị `overflow:hidden` cắt mất dòng dưới; vitest DOM assertion PASS (text vẫn nằm trong DOM) NHƯNG bản in thực tế CẮT chữ.
**Nguyên nhân:** assertion text-trong-DOM không phản ánh layout in khổ cố định — text có trong DOM nhưng bị clip khỏi vùng nhìn/in; DOM-test mù với pixel render.
**Rule kiểm được:** với output in (PDF/tem/khổ cố định) verify bằng RENDER ra ảnh (pdftoppm/screenshot → đọc ảnh bằng mắt), KHÔNG tin assertion text-trong-DOM. Khổ nhỏ: in VALUE-only (bỏ tiền tố nhãn) + `nowrap` + `text-overflow:ellipsis` + font/QR thu theo khổ (KHÔNG wrap→cắt dọc); QR giữ ≥18mm để còn quét được.

Cross-ref: LL-FE-47 (dead control khổ tem), LL-FE-46 (render thật chứng minh), LL-TEST (assert artifact render thật, không assert template); session 2026-06-11 F1.

### LL-FE-49: Gom helper trùng về SSoT — import-alias để KHÔNG churn template + `vue-tsc` bắt helper chết; banner/guard dùng SSoT (2026-06-29)

**Triệu chứng→nguyên nhân:** audit L-16/L-10. (a) 2 view (DepreciationView + InventoryDashboardView) mỗi nơi tự định nghĩa `vndShort` y hệt → audit yêu cầu 1 formatter SSoT. (b) 4 form (AssetCreate/Incident/AssetTransfer/Supplier) mỗi nơi render `<div>` lỗi style KHÁC nhau (`alert-error` vs tailwind ad-hoc).

**Rule (kiểm được):**
1. **Gom helper trùng** vào `utils/formatters.ts` (hàm thuần, có test) — hành vi PHẢI khớp inline cũ (vd `formatCurrencyShort`: '—' cho null · "x.x tỷ"/"x tr" · full VND fallback). Để **giảm churn template**, import-alias `import { formatCurrencyShort as vndShort } from '@/utils/formatters'` rồi XOÁ hàm local (template gọi `vndShort(...)` y nguyên).
2. **Sau khi xoá helper local, dependency của nó có thể thành DEAD** → `vue-tsc --noEmit` báo `TS6133 'vnd' declared but never read`. ⇒ LUÔN chạy full `vue-tsc` sau refactor SSoT (đếm-usage tay không đủ: `grep -c "vnd("` gồm cả định nghĩa) → xoá helper chết.
3. **Component dùng chung** (vd `FormError.vue`) build trên CLASS SSoT sẵn có (`.alert-error`, dùng ở 30+ view) + `role="alert"`; **margin do call-site quyết định** (fallthrough `class="mb-4"`) để 1 component hợp cả parent `space-y-*` lẫn standalone → giữ spacing từng nơi. Adopt vào CÁC form được audit nêu, KHÔNG mass-migrate (scope discipline).
4. **Client validation = mirror BE guard** (UX), BE vẫn authoritative: reuse `utils/formValidation` (vd `notFutureError`) + component sẵn có (`DateTimeInput`); rỗng = hợp lệ (BE fallback).

Cross-ref: component-patterns.md (SmartSelect allow-create/@create wire vào endpoint `create_*` sẵn có); LL-BE-65 (reuse endpoint, no new OAS); session audit 2026-06-29.

### LL-FE-54: "Điền file" LUÔN = TẢI LÊN, không bao giờ là ô gõ đường dẫn (2026-07-22)

**Triệu chứng (USER báo):** modal "Thêm chứng chỉ nhà cung cấp" (`VendorProfileDetailView`) có field "Tệp đính kèm" là `<input v-model="newCert.attachment" placeholder="/files/...">` — bắt người dùng **tự gõ đường dẫn**. Sweep toàn FE ra **7 chỗ cùng lỗi** ở 5 module (IMM-03 cert + hợp đồng quyết định mua sắm ×2, IMM-04 bảng kiểm hồ sơ, IMM-05 văn bản miễn đăng ký ×2, IMM-16 biên bản họp + bằng chứng CAPA). `ExemptModal.vue` còn ghi hẳn hint "Upload file trước qua Files, rồi dán đường dẫn vào đây" — anti-pattern được **viết thành hướng dẫn**.

**Vì sao nghiêm trọng (không phải lỗi thẩm mỹ):** tệp KHÔNG vào hệ thống ⇒ không có bản ghi `File` ⇒ không có quyền/không có vết audit; đường dẫn gõ sai = link chết; hồ sơ NĐ98 (chứng chỉ, hợp đồng, biên bản, bằng chứng CAPA) **rỗng bằng chứng** trong khi UI vẫn xanh. BE `Vendor Cert.attachment` khai `Attach` ĐÚNG — chỉ FE render sai ⇒ vitest/typecheck không bao giờ bắt được.

**Rule (kiểm được):**
1. Field lưu tệp ⇒ FE dùng **`components/common/FileUploadField.vue`** (v-model = `file_url` server trả về). CẤM `<input type="text">`, CẤM placeholder `/files/...`, CẤM nhãn "(file URL)"/"Đường dẫn file", CẤM hint "upload trước rồi dán".
2. Upload đi qua **`api/files.ts::uploadAttachment`** → `assetcore.api.files.upload_attachment` (gate quyền). KHÔNG gọi `/api/method/upload_file` **trần**.
3. Truyền `:docname` **bất cứ khi nào đã có** bản ghi cha — nếu không, File riêng tư mồ côi chỉ CHỦ SỞ HỮU đọc được (`File.has_permission`) ⇒ người duyệt/kiểm toán mở link bị 403. Màn tạo mới (chưa có tên) được phép bỏ trống: hook BE `link_uploaded_files` gắn lại sau khi lưu.
4. `doctype` là **bảng con** (Vendor Cert, Commissioning Document Record…) ⇒ BẮT BUỘC thêm `parent-doctype` (dùng xét quyền).
5. Tải lên xong phải **XEM LẠI ĐƯỢC**: bảng/danh sách phải có cột/link mở tệp — upload mà không có lối xem = dead-end ([[LL-FE-47]] dead-control).
6. Kiểm tra chéo BE: nếu field đích khai `Data`/`Small Text` thay vì `Attach` ⇒ đó cũng là bug (sửa doctype JSON), không phải cớ để giữ ô text. (`IMM CAPA Record.imm_effectiveness_evidence` là ca này — `Data` + description "link hoặc mô tả".)

**Gate:** SKILL §GATE-9 (3 lệnh grep, output PHẢI = 0). Guard tự động: `assetcore/tests/test_attachment_upload.py::TestNoTypedFilePathInputs` — quét mọi `.vue` tìm placeholder `/files/` + `<input>` text bind vào fieldname vốn là Attach trong doctype JSON.

Cross-ref: BE anti-pattern #19; `assetcore/api/files.py`; `assetcore/utils/attachments.py` (hook `doc_events["*"]`); [[LL-FE-47]] (control không dead); memory `ui_copy_language_policy` (nhãn VI); session 2026-07-22.

### LL-FE-53: UI copy — chính sách keep/translate viết tắt + 3 bẫy + kỹ thuật sweep glossary song song (2026-07-01)

**Bối cảnh:** USER yêu cầu bỏ viết tắt tiếng Anh trên UI ("phần mềm không được viết tắt trừ thuật ngữ người Việt hay dùng như QR/PIN"). Sweep ~85 file toàn FE. Đây là lớp **CHÍNH SÁCH** bổ sung cho [[LL-FE-52]] (LL-FE-52 = *cách* dịch an toàn; LL-FE-53 = *dịch cái gì* + bẫy + kỹ thuật). RED thực (đã quan sát trong phiên): agent phải `AskUserQuestion` **2 lần** để biết policy + scope vòng đầu bỏ sót `constants/`+`i18n/` → phải sweep vòng 2 + 10 test vỡ (chuỗi coupled). Chốt xong = **KHÔNG cần hỏi lại**.

**Glossary chốt (SPELL OUT — acronym tiếng Anh → tiếng Việt đầy đủ):**
`CAPEX`→Đầu tư mua sắm · `OPEX`→Chi phí vận hành · `TCO`→Tổng chi phí sở hữu · `SLA`→cam kết mức dịch vụ · `KPI`→chỉ số hiệu suất · `MTTR`/`TTR`→thời gian sửa chữa trung bình · `CAPA`→hành động khắc phục/phòng ngừa · `RCA`→phân tích nguyên nhân gốc · `AVL`→danh sách nhà cung cấp được duyệt · `QMS`→hệ thống quản lý chất lượng · `WO`→lệnh công việc · `PO`→đơn mua hàng · `DOA`→hỏng khi nhận · `NC`→sự không phù hợp · `HTM`→thiết bị y tế · `SKU`→mã hàng · `FCR`→yêu cầu thay đổi firmware · `FTA`→phân tích cây lỗi · `PM`→bảo trì định kỳ · `CM`→sửa chữa · `QA`→đảm bảo chất lượng · `L1`/`L2`→cấp 1/cấp 2 · `SC`→sửa chữa · `TB`→thiết bị (CHỈ khi nghĩa "thiết bị" — xem bẫy 1).

**GIỮ NGUYÊN (không dịch):** (a) VI-common: `QR`, `PIN`, `BHYT`, `NSNN`, `BGĐ`, `VD`, `VN`, `NSX`, `KH`, `KTV`, `NCC`, `BH`, `STT`, `TTBYT`, `BYT`, `VT-TTBYT`(tên phòng ban gắn `roleProfile` BE); (b) tiền tệ `VND`; (c) chuẩn/danh từ riêng `ISO`/`GMDN`/`WHO`/`NIST`/`VILAS` + tên phương pháp (5-Why/Fishbone/Ishikawa/Pareto) + ký hiệu chuẩn `N/A`; (d) value enum / `workflow_state` / fieldname / doctype name / `<option value>` / ID-mask (`PM-WO-…-XXXXX`, `R-IMM08-PM-COMP-90`) / module code (`IMM`/`AC`); (e) đuôi file (JPG/PNG/DOCX).

**3 bẫy (kiểm được):**
1. **Cùng token — khác nghĩa theo NGỮ CẢNH (data-bound check).** `TB`=thiết bị (glossary) NHƯNG `TB`=trung bình khi bind metric (`"Thời gian sửa TB"` ← `mttr_hours`/`metrics.mttr_hours`; `"Trễ TB"` ← average). `PM`/`QA` có thể là KEY của label-map (`PM:'Bảo trì'`) hoặc value (`value="QA"`, text đã là "Chất lượng") — hiển thị KHÔNG có acronym → KHÔNG đụng. LUÔN đọc DATA/binding trước khi thay; áp glossary mù = sai nghĩa ("thời gian sửa thiết bị").
2. **Scope hiển thị ≠ chỉ `views/`+`components/`.** Text end-user còn render từ: `constants/*.ts` label map (`labels.ts`/`sidebarNav.ts`/`personas.ts`/`roles.ts` — đổi **RHS VALUE**, GIỮ **KEY** + role-name BE như `personas.ts` `roleProfile`) · `utils/formatters.ts`/`wave2Labels.ts` · `i18n/messages.ts` (**GENERATED** từ `messages.py` — sửa `messages.py` rồi `python scripts/gen_fe_messages.py`, KHÔNG sửa tay [[LL-BE-66]]; giữ mã lỗi `IMM08-…`/`VR-04`/`Gate G05` + mọi `{placeholder}`). Enumerate ĐỦ nguồn render TRƯỚC sweep.
3. **Nhãn hành động workflow = FE-only display, GIỮ value BE.** "Phát hành PO" → hiển thị "Phát hành đơn mua hàng" qua map `ACTION_LABELS` NHƯNG vẫn gửi value gốc `'Phát hành PO'` cho backend. Đổi chuỗi transition thật = vỡ workflow JSON/hooks + buộc `bench migrate` (nhớ bug "Trình BGĐ" 422 đầu file này). Test co-located assert chuỗi hành động → mirror literal cùng lúc.

**Test coupling (RED thực 2026-07-01):** spell-out 1 nhãn **status/SSoT** (`RCA Required`→"Cần phân tích nguyên nhân gốc", `SLA`→"cam kết dịch vụ") vỡ **≥5 file test tên KHÁC, module KHÁC** (`constants/labels.incidentLabels.test.ts` · `utils/formatters.test.ts` · `views/incident/IncidentListView.drilldown.test.ts` · `views/incident/slaBreachLiveSoT.test.ts` · `views/cm/CMWorkOrderDetailView.slaClockStop.test.ts` · `CMWorkOrderListView.slaBreachedDivergence.test.ts`) — colocated-check MISS hết. Fix: **grep literal CŨ toàn repo (kể cả `*.test.ts`)** rồi cập nhật mọi assertion cùng pass; full `vitest run` (KHÔNG `--changed`/colocated).

**Kỹ thuật sweep glossary song song (sweep text lớn, đa module):** (1) viết 1 file glossary DÙNG CHUNG (scratchpad); (2) phân vùng theo THƯ MỤC — mỗi agent 1 nhóm dir, KHÔNG file nào bị đụng 2 lần; (3) dispatch agent song song, mỗi agent theo cùng glossary + rule include/exclude nghiêm (chỉ text node `>…<` + attr hiển thị `label|placeholder|title|aria-label|header`; KHÔNG `value=`/`===`/`.includes()`/comment/ID-mask), BÁO mọi edit + FLAG token nghi ngờ; (4) pass 2 gom cho token cross-cutting nằm ở ranh value↔display (`PM`/`CM`/`QA`); (5) verify: full `vue-tsc --noEmit`=0 + full `vitest run` + grep lại từng token (còn lại phải chỉ là code/value/comment/ID).

Cross-ref: [[LL-FE-52]] (dịch display-layer, giữ value); [[LL-BE-66]] (doctype label + `messages.py` SSoT); SKILL §"UI copy — chính sách viết tắt"; `assetcore-test` `frontend-unit-tests.md` §full-vitest-sau-sweep; session 2026-07-01 (bỏ viết tắt UI + factory 3 vòng).

### LL-FE-52: Việt-hoá display-layer — enum-binding KHÔNG chỉ `status` + bare-option value-injection (2026-06-29)

**Bối cảnh:** sweep Việt-hoá toàn FE ("sửa hết tiếng Anh trên UI"). Chiến lược DUY NHẤT an toàn = **chỉ dịch lớp hiển thị**: GIỮ NGUYÊN value enum / `workflow_state` / `fieldname` / `<option value>` (đổi value = vỡ data + workflow + buộc migrate); dịch qua label fn FE + doctype `label` ([[LL-BE-66]]) + `messages.py`.

**3 cạm bẫy + cách đúng (kiểm được):**
1. **Enum-binding leak KHÔNG chỉ `status`:** `{{ x.transfer_type|pm_type|wo_type|overall_result|calibration_type|medical_device_class|reference_type|avl_status|nc_type|lifecycle_status|priority|event_type|measurement_type }}` render thô tiếng Anh y hệt status. GATE-1 cũ (chỉ status|frequency|severity) BỎ SÓT 17 leak → đã bồi field-list + prefix-bất-kỳ (SKILL §GATE-1). Wrap qua label fn ở `constants/labels.ts` (SSoT); enum chưa có map → THÊM map + helper TẠI `labels.ts`, KHÔNG hardcode/dup local.
2. **Bare `<option>EN</option>` (value==text):** muốn dịch text PHẢI thêm `value="<EN gốc>"` TRƯỚC (khớp EXACT DocType Select `options`), rồi đổi text sang VI. Bỏ bước này → `v-model` submit tiếng Việt → 422 / filter vỡ. (SKILL §GATE-7.)
3. **Hàm logic trả `'Pass'/'Fail'` (vd `computeResult`) dùng để SO SÁNH — KHÔNG đổi return**; chỉ wrap nhãn ở template. Filter free-text khớp value EN → placeholder hint trung tính, ĐỪNG ví dụ tiếng Việt (user gõ VI không khớp value EN đã lưu).

**DRIFT bonus:** đối chiếu tập `<option value>` FE vs DocType `options` BE — lệch = bug (FE `audit_type` [Internal/External/Surveillance] ≠ BE [Internal/Self-assessment]) → flag BA, KHÔNG tự sửa trong sweep dịch.

Cross-ref: SKILL §GATE-1/§GATE-7; LL-FE-2/3/30 (label map sync BE EXACT); [[LL-BE-66]] (doctype label); `assetcore-test` (full vitest sau sweep — test assert chuỗi hiển thị, không chỉ colocated); session 2026-06-29 Việt-hoá UI.

### LL-FE-51: Workflow *Detail view phải render nút theo BE `allowed_transitions` (server-driven CTA) — KHÔNG hardcode `status === 'X'` (2026-06-29)

**Triệu chứng→nguyên nhân:** màn chi tiết phiếu workflow lộ "quá nhiều nút / luồng không rõ" — nút của 2 nhánh nghiệp vụ khác nhau hiện cùng lúc + nút submit/nhập-liệu hiện ở trạng thái chưa được phép. RED 2026-06-29: `CalibrationDetailView` gate nút bằng `form.value.status === 'Scheduled'` (hardcode client) → phiếu External ở *Đã lên lịch* hiện đồng thời "Bắt đầu hiệu chuẩn" (In-House) + "Gửi phòng hiệu chuẩn" (External) + "Gửi duyệt"(disabled+tooltip) + bảng nhập tham số đo — dù state machine BE KHÔNG cho submit từ Scheduled. BE đã expose SSoT `allowed_transitions = _CAL_VALID_TRANSITIONS.get(status, [])` (imm11.py) ĐÚNG để FE bám theo nhưng view chưa dùng.

**Rule (kiểm được — GATE-8):** 4 *Detail view workflow (Incident imm12 R3 · PM imm08 R21 · CM/Repair imm09 R22 · Calibration imm11) BE đều emit `allowed_transitions`. FE PHẢI:
1. `const allowedTransitions = computed(() => form.value.allowed_transitions ?? [])` + khai field vào interface API.
2. Mỗi nút workflow: `canXxx = capability && allowedTransitions.includes('<NextState>')` (mirror `IncidentDetailView`) — KHÔNG `form.value.status === 'X'`. Chuỗi `includes()` = EXACT enum BE (LL-FE/SKILL §allowed_transitions check).
3. Tách pha nhập-liệu: `canEnterResults = capability && !isSubmitted && RESULT_STATES.some(s => allowedTransitions.includes(s))` → bảng nhập đo + "Gửi duyệt" CHỈ hiện ở pha có result-transition (In Progress / Cert Received), KHÔNG ở Scheduled/Sent-to-Lab. `!isSubmitted` bắt buộc (phiếu Failed sau submit vẫn còn allowed=[Conditionally Passed] → đừng nhầm là còn nhập được).
4. Test mount-component vitest mọi (status × type) → assert đúng bộ nút (mẫu `CalibrationDetailView.buttonGating.test.ts`, 7 case, RED-proven bằng `git stash push -- <view>.vue`).

**Gate (output AT phải >0 cho CẢ 4):**
```bash
for v in IncidentDetailView PMWorkOrderDetailView CMWorkOrderDetailView CalibrationDetailView; do
  f=$(find frontend/src/views -name "$v.vue"); echo "AT=$(grep -cE 'allowed_transitions|allowedTransitions' "$f")  $v"; done
```
Hiện trạng 2026-06-29: Incident=7, Calibration=7 (đã wired); **PMWorkOrderDetailView=0, CMWorkOrderDetailView=0 (12 status-literal) VẪN hardcode** → backlog migrate sang allowed_transitions.

Cross-ref: SKILL §GATE-8; `_CAL_VALID_TRANSITIONS`/`_VALID_TRANSITIONS` (BE service); memory `overdue_server_flag_ssot` (cùng nguyên tắc SSoT server, FE không tự suy state).

### LL-FE-50: Doc tổng-hợp = TẠO bằng CHỌN ≥1 child ĐÃ-DUYỆT, KHÔNG tạo-rỗng-rồi-thêm (2026-06-29)

**Triệu chứng→nguyên nhân:** Kế hoạch mua sắm tạo rỗng trước rồi mới thêm đề xuất → cho phép tồn tại plan RỖNG → duyệt plan rỗng = lỗi workflow (LL-BE-62) + sai nghiệp vụ (kế hoạch phải GOM các đề xuất ĐÃ DUYỆT). Modal create cũ chỉ year/period/budget, không chọn nguồn.

**Rule (kiểm được):** doc tổng-hợp (Procurement Plan ← Needs Request approved; allocation ← lines…) → modal create PHẢI: (1) `openCreateModal()` fetch candidate ĐÃ DUYỆT (`listNeedsRequests({workflow_state:'Approved'},1,100)`), (2) bảng checkbox chọn + đếm "Đã chọn N", (3) submit `:disabled="selected.size===0"` (gate ≥1), (4) gọi `create*(..., Array.from(selectedIds))` truyền MẢNG id. KHÔNG tạo-rỗng-rồi-thêm. DONE-gate: component test — 0 chọn→submit disabled + KHÔNG gọi API; ≥1 chọn→spy nhận đúng mảng id (LL-FE-47 param == lựa chọn); render-verify browser: modal nạp candidate + gate disabled↔enabled.

Cross-ref: LL-FE-47 (control không dead — param == lựa chọn), BE LL-BE-62 (precondition ≥1 line TRƯỚC workflow); `views/needs/ProcurementPlanListView.vue` proposal-first modal; session 2026-06-29.

### LL-FE-55: [BE] chạy SONG SONG — cấm bind vào khoá chưa grep thấy trên đĩa (2026-07-28)

**Triệu chứng→nguyên nhân:** trong factory, [BE] và [FE] của cùng một vòng chạy **đồng thời**; khi FE code, thư mục BE có thể chưa có gì. Thực tế đã xảy ra 2 lần trong 1 run: (a) FE khai kiểu `ConnectionCell` VERBATIM theo spec trong khi `services/connections.py` + `services/shared/connection_meta.py` **chưa tồn tại** (`ls` báo No such file); (b) FE ship consumer `create_prefill` mà BE **0 hit** ⇒ nút «+ Tạo …» mở màn tạo TRỐNG. Cả hai đều **không thể bị vitest bắt**: test FE dựng payload bằng tay nên khoá luôn "có". Hệ quả là state chết sống sót qua nhiều vòng và được báo cáo là đã xong.

**Rule (kiểm được):**
1. **Grep trước khi bind:** `grep -rn "<khoá>" assetcore/` cho mọi khoá payload / endpoint / hằng số của BE mà bạn đọc. 0 hit ⇒ **(a)** code fail-safe (thiếu khoá KHÔNG vỡ UI), **(b)** khai vào `contract_unverified`, **(c)** KHÔNG tuyên bố acceptance đó đạt, **(d)** ghi `open_issues` "hợp đồng chưa land".
2. **Khai kiểu theo spec thì được, coi là đã chạy thì không.** `?:` optional + fallback là bắt buộc cho khoá chưa verify.
3. **Test chống khoá-ma:** với khoá mới, thêm 1 TC dựng payload **THIẾU** khoá đó và assert UI vẫn dùng được (fail-safe) — payload-đầy-đủ-dựng-tay một mình luôn xanh giả.
4. `landed_symbols` chỉ ghi thứ chính bạn vừa grep lại thấy (`symbol → file:line`).

Cross-ref: [[LL-BE-69]] (phía phát), [[LL-AUDIT-22]] (claim ≠ đĩa), LL-FE-47 (control không dead); session run-3 2026-07-28.

### LL-FE-56: Nhãn enum = 1 SSoT ở `constants/labels.ts` + parity với file nhập/xuất (2026-08-11)

**Triệu chứng→nguyên nhân:** Việt hoá lớp nhập/xuất Excel (mẫu bảng kiểm) xong mới lộ ra: cùng một enum có tới **3 kiểu tồn tại** trong FE — (a) map cục bộ TRÙNG LẶP giữa 2 view (`VENDOR_TYPE_LABEL` ở `SupplierDetailView` + `SupplierListView`), (b) map cục bộ DUY NHẤT một view (`CATEGORIES` loại phụ tùng ở `SparePartListView`), (c) **không có map nào** (`clinical_area_type` / `infection_control_level` → `ReferenceDataView` in nguyên "ICU"/"Standard"). Hệ quả: sau khi file Excel hỏi bằng tiếng Việt, MÀN HÌNH vẫn in tiếng Anh ⇒ người dùng đọc hai nơi ra hai thứ, không biết điền theo cái nào.

Đây là biến thể của anti-pattern A (English-enum leak) nhưng **không grep ra được bằng cách tìm chuỗi tiếng Anh trong `views/`** — vì chuỗi đến từ DATA, không phải literal.

**Rule (kiểm được):**
1. Nhãn enum sống ở `constants/labels.ts` (hoặc `utils/formatters.ts` nếu dùng toàn app), export `XXX_LABEL` + hàm `xxxLabel(v)` fallback trả nguyên `v`. View **chỉ import** — 0 map cục bộ. Kiểm: `grep -rn "Record<string, string> = {" src/views/` phải rỗng.
2. **Field khác nhau ≠ dùng chung map**: `AC Supplier.supplier_group` kết thúc bằng `Service Provider`, `vendor_type` bằng `Service`. Gộp 1 map = khoá rác + 2 nhãn trùng trong một cột ⇒ đổi ngược không xác định. Đọc `options` của TỪNG field trước khi gộp.
3. **Lớp nhập/xuất Excel cũng là lớp hiển thị** ⇒ nhãn phải khớp màn hình. SSoT BE = `utils/import_helpers.py::ENUM_DISPLAY_BY_DOCTYPE`; guard `assetcore/tests/test_import_enum_labels.py` đọc THẲNG map trong `.ts` và đỏ khi lệch chữ (4 tầng: phủ-kín · không-khoá-rác · parity FE · dropdown trong file .xlsx thật).
4. Value/enum vẫn GIỮ NGUYÊN ([[LL-FE-52]]/[[LL-FE-53]]) — chỉ nhãn đổi.

**Bẫy kèm theo (guard bắt được, đáng nhớ):** dropdown trong file mẫu từng chào `P1 Critical` / `P1 High` trong khi DocType `IMM SLA Policy.priority` chỉ có `P1..P4` ⇒ người dùng chọn đúng theo hướng dẫn mà hệ thống vẫn từ chối. Danh sách lựa chọn của file mẫu PHẢI sinh/kiểm từ `options` thật của DocType, không chép tay từ tài liệu.

Cross-ref: SKILL §"UI copy — chính sách viết tắt"; [[LL-FE-53]]; skill `assetcore-import` LL-IMP-7; session 2026-08-11.
