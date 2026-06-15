# assetcore-fe — Build sequence & UI Completeness Rules

> Heavy reference moved out of `SKILL.md` (progressive disclosure). The exact file-path build order + the full UI-completeness checklists + the workflow-button pattern live here. The synthesized `Verification` section in `SKILL.md` points back to these checklists.

## Build sequence for a new IMM module on FE (exact file paths)

**Tạo các files theo thứ tự này:**
```
frontend/src/api/immXX.ts          ← 1. API client
frontend/src/stores/immXX.ts       ← 2. Pinia store
frontend/src/views/<domain>/       ← 3. View folder (domain-named, không phải immXX/)
    ListView.vue
    DetailView.vue
    components/
```

1. **Verify BE endpoint names trước tiên** (BLOCKING — không skip):
   ```bash
   grep "@frappe.whitelist" -A1 assetcore/api/immXX.py | grep "def " | awk '{print $2}' | cut -d'(' -f1
   ```
   Đây là danh sách path FE phải gọi (`assetcore.api.immXX.<name>`). Đối chiếu với `docs/imm-XX/05_API_Specification.md`. Nếu BE và spec lệch → fix BE trước.

1b. **Verify role constants**: Check `assetcore/services/shared/constants.py::Roles` xem có role mới nào. Sync vào `frontend/src/constants/roles.ts` nếu chưa có.
2. Define TypeScript interfaces in `src/api/<module>.ts` mirroring BE response shape (status union, datetime as `string | null`).
3. Implement endpoint functions using `frappeGet`/`frappePost` (path = `assetcore.api.<module>.<fn>`).
4. Build Pinia store with state + actions. Re-fetch after every mutation so cache stays consistent.
5. Build views: list → detail → form. Each wraps actions in `api.run(...)`. Reuse `BaseModal`, `BasePagination`, `StatusBadge`, `ListFilterBar`, `LinkSearch` from `components/common/` instead of rebuilding.
6. Add routes to the matching numbered section in `src/router/index.ts`. Use `meta.roles = ROLES_X_MANAGE` from `@/constants/roles`. Lazy-import every view.
7. Add nav entries via `composables/useSidebar.ts`.
8. Add role constants/groups to `@/constants/roles.ts` if BE introduced new ones — keep BE/FE in sync.
9. `cd frontend && npm run typecheck && npm run lint` before claiming done (`vue-tsc --noEmit` catches most regressions).
9b. **Verify endpoint connectivity**: Với mỗi `frappeGet/frappePost` trong `api/immXX.ts`, grep tên function trong `assetcore/api/immXX.py` để confirm khớp. Không để API mismatch lọt vào PR.
10. `npm run dev` (with `bench start` running for `/api/method` proxy) and exercise happy path + at least one BE error path in the browser.

---

## UI Completeness — bắt buộc trước khi khai báo Done

Mọi module page phải đáp ứng checklist này. **Thiếu một mục = module chưa xong.**

### List page checklist
- [ ] Có nút **"Tạo mới"** (hoặc "Tạo kế hoạch", "Tạo WO", tùy ngữ cảnh) — click → vào form tạo hoặc modal
- [ ] Click row → navigate đúng detail URL (`:id` hoặc `:name` match route param)
- [ ] Filter → table cập nhật (không chỉ hiển thị danh sách tĩnh)
- [ ] Pagination hoạt động nếu có nhiều records
- [ ] Empty state có CTA rõ ràng, không chỉ "Không có dữ liệu"
- [ ] Loading skeleton hoặc spinner khi đang fetch
- [ ] Error banner + retry button khi API lỗi

### Detail page checklist
- [ ] Hiển thị đủ fields — không section nào toàn "—" nếu data tồn tại
- [ ] Workflow action buttons đúng theo state:
  - Draft/Pending: nút chuyển sang state tiếp theo
  - Final state (Closed/Cancelled/Expired): không có nút transition, chỉ read-only
  - Button disabled + tooltip nếu precondition chưa đủ (không âm thầm ẩn)
- [ ] Nút **"← Quay lại"** về list page
- [ ] Nút **"Chỉnh sửa"** nếu record có thể edit ở trạng thái hiện tại
- [ ] Tabs có dữ liệu (KPI, Audit trail, Timeline) — không empty state giả vì thiếu seed data
- [ ] **Stats tabs (KPI, Uptime, MTBF, Khấu hao)**: phải có work order data + lifecycle events trước khi claim pass. Số liệu luôn 0 dù có WO = bug.

### Lỗi phổ biến cần kiểm tra ngay
| Symptom | Root cause | Fix |
|---|---|---|
| List page không có "Tạo mới" | Button bị quên hoặc wrapped trong permission guard sai | Thêm button; check `v-if` / `v-permission` |
| Click row vào detail → 404 | Route param `id` nhưng link dùng `record.name` (đúng, cần verify naming) hoặc ngược lại | Kiểm tra router `:id` vs link `:to` pattern |
| Tab "KPI"/"Audit" empty dù đã click | Data chưa được seed (work orders, lifecycle events) | Seed data trước khi test, không khai báo tab pass khi chưa có data |
| Workflow button không hiện | State constant FE ≠ BE (vd FE check `=== 'draft'` nhưng BE trả `'Draft'`) | Grep BE service `_STATUS_*` constants và sync FE |
| Stats luôn = 0 | API endpoint không aggregate đúng, hoặc FE không gọi đúng API | Kiểm tra BE service function tính KPI có join đúng table không |

---

## UI Completeness Rules (bắt buộc)

Mọi module FE PHẢI có đủ:

### List page
- **Create button**: nút "Tạo [entity]" hoặc "+ Thêm mới" ở PageHeader `#actions` slot → navigate đến create form
- **Row clickable**: `@click="router.push('/path/' + row.name)"` → detail page
- **Empty state CTA**: nút "Tạo [entity] đầu tiên" khi list rỗng

### Detail page
- **Back button**: nút ← quay lại list
- **Workflow action buttons**: computed `canXxx` based trên `status` + `allowed_transitions`; nút hiện đúng state
  - Pattern: `v-if="canApprove"` → gọi action → reload data → toast
  - Không để page ở trạng thái "read-only hoàn toàn" trừ khi document đã Closed/Cancelled
- **Edit functionality**: nếu Draft → có inline edit hoặc nút "Sửa"
- **Tabs có data**: KPI tab phải hiện số liệu thực (uptime, MTBF, MTTR từ API); Audit Trail tab fetch và hiện events; không hard-code empty state

### Workflow button pattern chuẩn

```vue
<div class="flex gap-2 mt-4">
  <button v-if="canApprove" class="btn-primary" @click="doApprove">
    Phê duyệt
  </button>
  <button v-if="canActivate" class="btn-primary" @click="doActivate">
    Kích hoạt
  </button>
  <button v-if="canClose" class="btn-outline" @click="doClose">
    Đóng
  </button>
</div>

<script setup>
const canApprove = computed(() => form.value.workflow_state === 'Draft')
const canActivate = computed(() => form.value.workflow_state === 'Approved')
const canClose = computed(() => form.value.workflow_state === 'Active')

async function doApprove() {
  await api.run(() => approvePlan(form.value.name))
  await loadData()
}
</script>
```

### API function naming convention
- `create[Entity]` — POST tạo mới
- `approve[Entity]` / `activate[Entity]` / `close[Entity]` — workflow transitions
- `set[Field]` — update single field
- `remove[Child]From[Parent]` — xóa child row
