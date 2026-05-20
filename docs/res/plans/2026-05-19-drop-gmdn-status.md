# Drop `gmdn_status` + Filter by `gmdn_code` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Loại bỏ hoàn toàn field `gmdn_status` khỏi `AC Asset`, thay bằng cơ chế lọc/quản lý theo `gmdn_code` (kế thừa từ `AC Asset Category`) trên trang `/assets`.

**Architecture:** Hai pha — (1) BE: xoá service/API/schema field cũ, mở rộng `list_assets` với `gmdn_code` filter + search; (2) FE: xoá types/store/api liên quan, rewrite filter & cột "GMDN" trong AssetListView, dọn AssetDetailView + repurpose QRScanView. Patch DB chạy ở `pre_model_sync` để drop column trước khi schema sync.

**Tech Stack:** Frappe v15 (Python), MariaDB, Vue 3 + TypeScript + Pinia, TailwindCSS.

**Reference:** Background phân tích — [docs/res/gmdn-asset-category-analysis.md](../../res/gmdn-asset-category-analysis.md) §6.

---

## File Structure

### Backend (sửa)

- `assetcore/services/imm00.py` — xoá `update_gmdn_status`, `toggle_gmdn_status_via_qr`, constants `_GMDN_STATUS_*`, `_GMDN_BLOCKED_LIFECYCLE`
- `assetcore/api/imm00.py` — xoá 2 whitelist endpoints, xoá param `gmdn_status` trong `list_assets`, thêm param `gmdn_code`, mở rộng `or_filters` search
- `assetcore/assetcore/doctype/ac_asset/ac_asset.json` — xoá field `gmdn_status` khỏi `field_order` và `fields`
- `assetcore/tests/test_imm00_list_assets.py` — **NEW** unit test cho filter `gmdn_code` + search

### Backend (tạo mới)

- `assetcore/patches/v3_1/008_drop_gmdn_status.py` — pre-model-sync patch xoá column DB
- `assetcore/patches.txt` — đăng ký patch mới ở `[pre_model_sync]`

### Frontend (sửa)

- `frontend/src/types/imm00.ts` — xoá `GmdnStatus` type, `gmdn_status?` properties, `gmdn_status` trong `AssetListParams`
- `frontend/src/api/imm00.ts` — xoá `updateGmdnStatus`, `toggleGmdnStatus`
- `frontend/src/stores/imm00.ts` — xoá `GMDN_OPTIONS`, `GMDN_STATUS_LABEL`, `updateGmdn`
- `frontend/src/views/asset/AssetListView.vue` — drop filter "GMDN" dropdown; rewrite cột "GMDN" → `gmdn_code` + tooltip `gmdn_term`; thêm filter `gmdn_code` autocomplete; extend chips
- `frontend/src/views/asset/AssetDetailView.vue` — xoá modal đổi GMDN status, computed/handler liên quan
- `frontend/src/views/system/QRScanView.vue` — repurpose: scan QR → router.push(`/assets/<id>`), không gọi toggle

### Scripts (cleanup)

- `assetcore/scripts/fix_asset_gmdn.py` — **DELETE**
- `assetcore/scripts/fix_master_display_names.py` — xoá block sửa `gmdn_status`
- `assetcore/scripts/cleanup_and_seed_assets.py` — xoá keys `gmdn_status`
- `assetcore/scripts/audit_master_data.py` — xoá `gmdn_status` khỏi fields

### Docs (sync)

- `docs/imm-00/04_Backend_Design.md` — xoá mọi mention `gmdn_status`, thêm note filter `gmdn_code`

---

## Phase 1 — Backend

### Task 1: Viết test failing cho list_assets filter `gmdn_code`

**Files:**
- Create: `assetcore/tests/test_imm00_list_assets.py`

- [ ] **Step 1: Tạo test file**

```python
# assetcore/tests/test_imm00_list_assets.py
# Copyright (c) 2026, AssetCore Team
"""Unit tests cho list_assets filter theo gmdn_code + search mở rộng."""
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.api.imm00 import list_assets


class TestListAssetsGmdnFilter(FrappeTestCase):
    """BR-00-XX: lọc Asset theo gmdn_code kế thừa từ Asset Category."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Category với gmdn_code cố định
        if not frappe.db.exists("AC Asset Category", "TEST-CAT-USG"):
            frappe.get_doc({
                "doctype": "AC Asset Category",
                "category_name": "Test Ultrasound",
                "category_code": "TEST-CAT-USG",
                "gmdn_code": "35304",
                "gmdn_term": "Ultrasound imaging system, general purpose",
            }).insert(ignore_permissions=True)

    def test_filter_by_gmdn_code_returns_only_matching_assets(self):
        result = list_assets(gmdn_code="35304")
        assert "items" in result
        for item in result["items"]:
            assert item["gmdn_code"] == "35304"

    def test_search_by_gmdn_code_substring(self):
        result = list_assets(search="35304")
        # Không raise; items có thể rỗng nếu chưa có asset thật
        assert "items" in result
        assert "pagination" in result

    def test_gmdn_status_param_removed(self):
        import inspect
        sig = inspect.signature(list_assets)
        assert "gmdn_status" not in sig.parameters, \
            "list_assets() vẫn còn param gmdn_status — phải xoá."
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm00_list_assets`

Expected: FAIL — `list_assets() got an unexpected keyword argument 'gmdn_code'` (test 1, 2) + test 3 sẽ pass sau khi xoá param ở Task 3.

---

### Task 2: Xoá service-layer GMDN status functions

**Files:**
- Modify: `assetcore/services/imm00.py:223-275`

- [ ] **Step 1: Xoá 3 constants + 2 functions**

Xoá block từ dòng 223 tới 275 (3 constants + `update_gmdn_status` + `toggle_gmdn_status_via_qr`):

```python
# XOÁ TOÀN BỘ BLOCK NÀY
_GMDN_STATUS_ACTIVE = "In Use"
_GMDN_STATUS_INACTIVE = "Not Use"
_GMDN_BLOCKED_LIFECYCLE = (_STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED)


def update_gmdn_status(asset_name: str, gmdn_status: str, reason: str) -> dict:
    ...

def toggle_gmdn_status_via_qr(asset_name: str) -> dict:
    ...
```

- [ ] **Step 2: Verify không còn import nội bộ**

Run: `grep -n "_GMDN_STATUS\|update_gmdn_status\|toggle_gmdn_status_via_qr" /home/miyano/frappe-bench/apps/assetcore/assetcore/services/imm00.py`

Expected: không có kết quả.

- [ ] **Step 3: Commit**

```bash
cd /home/miyano/frappe-bench/apps/assetcore
git add assetcore/services/imm00.py assetcore/tests/test_imm00_list_assets.py
git commit -m "refactor(imm00): drop gmdn_status service functions"
```

---

### Task 3: Xoá API endpoints + Mở rộng list_assets filter `gmdn_code` + search

**Files:**
- Modify: `assetcore/api/imm00.py:17-18` (imports), `85-135` (list_assets), `238-256` (endpoints)

- [ ] **Step 1: Xoá 2 imports không dùng nữa**

Tại dòng 17-18, xoá:

```python
    update_gmdn_status as svc_update_gmdn_status,
    toggle_gmdn_status_via_qr as svc_toggle_gmdn_via_qr,
```

- [ ] **Step 2: Sửa signature `list_assets` — drop `gmdn_status`, add `gmdn_code`**

Thay block dòng 85-110:

```python
def list_assets(
    page: int = 1,
    page_size: int = 20,
    lifecycle_status: str = None,
    department: str = None,
    location: str = None,
    asset_category: str = None,
    search: str = None,
    gmdn_code: str = None,
):
    """GET /api/method/assetcore.api.imm00.list_assets"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if lifecycle_status:
        filters["lifecycle_status"] = lifecycle_status
    if department:
        filters["department"] = department
    if location:
        filters["location"] = location
    if asset_category:
        filters["asset_category"] = asset_category
    if gmdn_code:
        filters["gmdn_code"] = gmdn_code
```

- [ ] **Step 3: Mở rộng `or_filters` search bao gồm `gmdn_code`**

Thay block search (around `if search:`):

```python
    or_filters = None
    if search:
        like = f"%{search}%"
        or_filters = [
            [_DT_ASSET, "asset_name",      "like", like],
            [_DT_ASSET, "asset_code",      "like", like],
            [_DT_ASSET, "manufacturer_sn", "like", like],
            [_DT_ASSET, "gmdn_code",       "like", like],
        ]
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tab{_DT_ASSET}`"
            f" WHERE asset_name LIKE %s OR asset_code LIKE %s"
            f" OR manufacturer_sn LIKE %s OR gmdn_code LIKE %s",
            [like, like, like, like],
        )[0][0]
    else:
        total = frappe.db.count(_DT_ASSET, filters=filters)
```

- [ ] **Step 4: Xoá `gmdn_status` khỏi fields select**

Dòng 132, đổi:

```python
        "gmdn_code", "gmdn_status",
```

thành:

```python
        "gmdn_code",
```

- [ ] **Step 5: Xoá 2 whitelist endpoints `update_gmdn_status` + `toggle_gmdn_status`**

Xoá block dòng 238-256 (cả decorator `@frappe.whitelist()` ngay trên):

```python
# XOÁ TOÀN BỘ
@frappe.whitelist()
def update_gmdn_status(name: str, gmdn_status: str, reason: str = ""):
    ...

@frappe.whitelist()
def toggle_gmdn_status(name: str):
    ...
```

- [ ] **Step 6: Chạy lại test, xác nhận 3 test pass**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm00_list_assets`

Expected: 3 PASS.

- [ ] **Step 7: Commit**

```bash
cd /home/miyano/frappe-bench/apps/assetcore
git add assetcore/api/imm00.py
git commit -m "feat(imm00): replace gmdn_status filter with gmdn_code on list_assets"
```

---

### Task 4: Patch DB — drop column `gmdn_status`

**Files:**
- Create: `assetcore/patches/v3_1/008_drop_gmdn_status.py`
- Modify: `assetcore/patches.txt`

- [ ] **Step 1: Tạo patch file**

```python
# assetcore/patches/v3_1/008_drop_gmdn_status.py
# Copyright (c) 2026, AssetCore Team
"""
Pre-model-sync: xoá column gmdn_status khỏi tabAC Asset trước khi schema sync.

Lý do: gmdn_status (In Use / Not Use) trộn ngữ nghĩa với lifecycle_status —
ref docs/res/gmdn-asset-category-analysis.md §6. Lọc thiết bị chuyển sang
dùng gmdn_code (kế thừa từ Asset Category).
"""
from __future__ import annotations

import frappe


def execute() -> None:
    if not frappe.db.table_exists("AC Asset"):
        return

    cols = frappe.db.sql(
        """SELECT COLUMN_NAME FROM information_schema.COLUMNS
           WHERE TABLE_SCHEMA = DATABASE()
             AND TABLE_NAME = 'tabAC Asset'
             AND COLUMN_NAME = 'gmdn_status'""",
        as_dict=True,
    )
    if not cols:
        return

    frappe.db.sql("ALTER TABLE `tabAC Asset` DROP COLUMN `gmdn_status`")
    frappe.db.commit()
```

- [ ] **Step 2: Đăng ký patch trong `patches.txt`**

Mở `assetcore/patches.txt`, thêm vào block `[pre_model_sync]`:

```
[pre_model_sync]
assetcore.patches.v3_1.006_dedupe_asset_category_gmdn_code
assetcore.patches.v3_1.008_drop_gmdn_status
```

- [ ] **Step 3: Xoá field `gmdn_status` khỏi DocType JSON**

Mở `assetcore/assetcore/doctype/ac_asset/ac_asset.json`:

- Trong `field_order`, xoá dòng `"gmdn_status",` (sau `"gmdn_code"`).
- Trong `fields`, xoá block field định nghĩa `gmdn_status` (Select, options "In Use\nNot Use", default "Not Use").

- [ ] **Step 4: Chạy migrate**

Run: `cd /home/miyano/frappe-bench && bench --site miyano migrate`

Expected: patch chạy thành công, không error. `bench --site miyano console` → `frappe.db.sql("SHOW COLUMNS FROM \`tabAC Asset\` LIKE 'gmdn_status'")` trả `()`.

- [ ] **Step 5: Commit**

```bash
cd /home/miyano/frappe-bench/apps/assetcore
git add assetcore/patches/v3_1/008_drop_gmdn_status.py assetcore/patches.txt assetcore/assetcore/doctype/ac_asset/ac_asset.json
git commit -m "feat(imm00): drop AC Asset.gmdn_status column + schema field"
```

---

## Phase 2 — Frontend

### Task 5: Xoá `GmdnStatus` type + `gmdn_status` khỏi interfaces

**Files:**
- Modify: `frontend/src/types/imm00.ts:14,38,80-81,127-128,139`

- [ ] **Step 1: Xoá type alias dòng 14**

```ts
// XOÁ
export type GmdnStatus = 'In Use' | 'Not Use'
```

- [ ] **Step 2: Xoá property `gmdn_status?` khỏi mọi interface**

Tìm và xoá toàn bộ dòng có pattern `gmdn_status?:` trong file (5 chỗ: dòng 38, 81, 128, 139). Cũng xoá khỏi `AssetListParams` interface (param filter cũ).

- [ ] **Step 3: Thêm `gmdn_code?` vào `AssetListParams`**

Xác định interface `AssetListParams` (gần dòng 130-145). Thêm:

```ts
export interface AssetListParams {
  // ... existing fields
  gmdn_code?: string  // ← THÊM
  // KHÔNG còn gmdn_status?
}
```

- [ ] **Step 4: Verify types compile**

Run: `cd /home/miyano/frappe-bench/apps/assetcore/frontend && npx vue-tsc --noEmit 2>&1 | head -30`

Expected: errors về `GmdnStatus` không tồn tại trong các file khác sẽ là báo cáo tiếp theo (Task 6-9). Ghi nhận, không fix riêng — tiếp tục pha xoá rồi recheck cuối.

---

### Task 6: Xoá `updateGmdnStatus` + `toggleGmdnStatus` khỏi api layer

**Files:**
- Modify: `frontend/src/api/imm00.ts:40-46`

- [ ] **Step 1: Xoá 2 functions**

```ts
// XOÁ HẾT
export function updateGmdnStatus(name: string, gmdn_status: string, reason: string): ... {
  return frappePost(`${BASE}.update_gmdn_status`, { name, gmdn_status, reason })
}

export function toggleGmdnStatus(name: string): ... {
  return frappePost(`${BASE}.toggle_gmdn_status`, { name })
}
```

- [ ] **Step 2: Verify**

Run: `grep -n "updateGmdnStatus\|toggleGmdnStatus" /home/miyano/frappe-bench/apps/assetcore/frontend/src/api/imm00.ts`

Expected: không kết quả.

---

### Task 7: Xoá GMDN constants + `updateGmdn` action khỏi store

**Files:**
- Modify: `frontend/src/stores/imm00.ts:11,21-30,67-72,82`

- [ ] **Step 1: Xoá `GmdnStatus` khỏi import**

Dòng 11, đổi:

```ts
import type {
  ...
  GmdnStatus,
  ...
} from '@/types/imm00'
```

→ Xoá dòng `GmdnStatus,`.

- [ ] **Step 2: Xoá constants `GMDN_OPTIONS`, `GMDN_STATUS_LABEL`**

Xoá block khoảng dòng 21-30 (cả 2 export const).

- [ ] **Step 3: Xoá action `updateGmdn`**

Xoá function `updateGmdn` (khoảng dòng 67-72) và xoá khỏi return statement (dòng 82).

```ts
// Trước:
return { assets, currentAsset, pagination, loading, error, fetchList, fetchOne, transition, updateGmdn, reset }
// Sau:
return { assets, currentAsset, pagination, loading, error, fetchList, fetchOne, transition, reset }
```

- [ ] **Step 4: Commit pha 1 FE**

```bash
cd /home/miyano/frappe-bench/apps/assetcore
git add frontend/src/types/imm00.ts frontend/src/api/imm00.ts frontend/src/stores/imm00.ts
git commit -m "refactor(fe-imm00): drop GmdnStatus type, api, store actions"
```

---

### Task 8: Rewrite `AssetListView.vue` — filter + cột GMDN theo `gmdn_code`

**Files:**
- Modify: `frontend/src/views/asset/AssetListView.vue`

- [ ] **Step 1: Sửa `filters` ref — drop `gmdn_status`, add `gmdn_code`**

Dòng 20-29:

```ts
const filters = ref<AssetListParams>({
  lifecycle_status: '',
  department: '',
  location: '',
  asset_category: '',
  gmdn_code: '',      // ← THAY
  search: '',
  page: 1,
  page_size: 20,
})
```

- [ ] **Step 2: Sửa `cleanParams` computed**

Dòng 42-51, đổi:

```ts
if (filters.value.gmdn_status) p.gmdn_status = filters.value.gmdn_status
```

→

```ts
if (filters.value.gmdn_code) p.gmdn_code = filters.value.gmdn_code
```

- [ ] **Step 3: Sửa `activeChips` computed**

Dòng 73-75, đổi:

```ts
if (filters.value.gmdn_code) {
  chips.push({ key: 'gmdn_code', label: `GMDN: ${filters.value.gmdn_code}` })
}
```

(thay block `gmdn_status` cũ).

- [ ] **Step 4: Sửa `resetFilters`**

Dòng 106:

```ts
filters.value = { lifecycle_status: '', department: '', location: '', asset_category: '', gmdn_code: '', search: '', page: 1, page_size: 20 }
```

- [ ] **Step 5: Tạo computed list GMDN options từ `refData.categories`**

Sau import block, thêm:

```ts
const gmdnOptions = computed(() => {
  const seen = new Set<string>()
  return refData.categories
    .filter(c => c.gmdn_code && !seen.has(c.gmdn_code) && (seen.add(c.gmdn_code), true))
    .map(c => ({ value: c.gmdn_code!, label: `${c.gmdn_code} — ${c.gmdn_term || c.category_name}` }))
})
```

Lưu ý: cần `gmdn_code`/`gmdn_term` có trong type `AssetCategory` của `refData.categories` — verify ở `frontend/src/types/imm00.ts` (đã có trên schema BE). Nếu missing thêm vào type interface.

- [ ] **Step 6: Thay dropdown filter "GMDN" trong template**

Dòng 184-191 template, đổi:

```vue
<div class="form-group">
  <label class="form-label">GMDN Code</label>
  <select v-model="filters.gmdn_code" class="form-select" @change="applyFilters">
    <option value="">Tất cả mã GMDN</option>
    <option v-for="g in gmdnOptions" :key="g.value" :value="g.value">{{ g.label }}</option>
  </select>
</div>
```

- [ ] **Step 7: Rewrite cột bảng "GMDN" — hiển thị `gmdn_code` + tooltip term**

Dòng 283-289 (cột table), đổi:

```vue
<td class="table-cell">
  <button
    v-if="asset.gmdn_code"
    class="font-mono text-sm text-slate-700 hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
    :title="asset.gmdn_term || ''"
    @click.stop="quickFilter('gmdn_code', asset.gmdn_code!)"
  >{{ asset.gmdn_code }}</button>
  <span v-else class="text-slate-400">—</span>
</td>
```

- [ ] **Step 8: Build FE + smoke test**

Run: `cd /home/miyano/frappe-bench/apps/assetcore/frontend && npm run build 2>&1 | tail -15`

Expected: build success, không TS error còn tham chiếu `gmdn_status` / `GmdnStatus`.

Smoke test thủ công:
```bash
cd /home/miyano/frappe-bench && bench start  # (nếu chưa chạy)
# Mở http://localhost:3000/assets
# - Dropdown filter mới "GMDN Code" hiển thị danh sách codes
# - Chọn 1 code → list filter đúng
# - Cột "GMDN" hiển thị code thật, hover thấy term
# - Click code trong row → quickFilter set
# - Ô search nhập "35304" → tìm được asset có gmdn_code match
```

- [ ] **Step 9: Commit**

```bash
cd /home/miyano/frappe-bench/apps/assetcore
git add frontend/src/views/asset/AssetListView.vue frontend/src/types/imm00.ts
git commit -m "feat(fe-asset-list): replace gmdn_status filter with gmdn_code dropdown + column"
```

---

### Task 9: Dọn `AssetDetailView.vue` — xoá modal đổi GMDN status

**Files:**
- Modify: `frontend/src/views/asset/AssetDetailView.vue:127-156` (script) + template tương ứng

- [ ] **Step 1: Xoá refs/computed/handler trong `<script setup>`**

Xoá block (dòng 127-156, các identifiers):
- `gmdnReason`, `gmdnSaving`, `gmdnError`
- `showGmdnModal`
- `currentGmdn`, `targetGmdnStatus`, `targetGmdnLabel`
- Function `submitGmdn` (hay tên tương đương)
- Branch `if (action === 'gmdn' && store.currentAsset) showGmdnModal.value = true`

- [ ] **Step 2: Xoá template GMDN modal**

Tìm `<div v-if="showGmdnModal"` (hoặc tên modal tương đương) trong template, xoá toàn bộ block.

- [ ] **Step 3: Xoá nút action "Đổi GMDN Status" trong header**

Tìm button trigger `action === 'gmdn'` hoặc label "GMDN" trong action bar, xoá.

- [ ] **Step 4: Đảm bảo section hiển thị GMDN readonly vẫn còn**

Section info card hiển thị `currentAsset.gmdn_code` và `gmdn_term` (readonly, derived from Device Model) → GIỮ NGUYÊN. Chỉ xoá phần state-mutating.

- [ ] **Step 5: Build verify**

Run: `cd /home/miyano/frappe-bench/apps/assetcore/frontend && npm run build 2>&1 | tail -10`

Expected: build success.

- [ ] **Step 6: Commit**

```bash
cd /home/miyano/frappe-bench/apps/assetcore
git add frontend/src/views/asset/AssetDetailView.vue
git commit -m "refactor(fe-asset-detail): remove GMDN status modal — readonly only"
```

---

### Task 10: Repurpose `QRScanView.vue` — scan QR → mở Asset detail

**Files:**
- Modify: `frontend/src/views/system/QRScanView.vue`

- [ ] **Step 1: Thay toàn bộ file**

```vue
<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — QR Scan → mở Asset Detail
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { getBarcodeLookup } from '@/api/imm04'
import PageHeader from '@/components/common/PageHeader.vue'

const router = useRouter()
const manualCode = ref('')
const loading = ref(false)
const error = ref('')
const qrInput = ref<HTMLInputElement | null>(null)

onMounted(() => {
  nextTick(() => {
    if (document.activeElement === document.body) qrInput.value?.focus()
  })
})

async function scan() {
  const code = manualCode.value.trim()
  if (!code) return
  loading.value = true
  error.value = ''
  try {
    let assetId = code
    try {
      const lookup = await getBarcodeLookup(code)
      if (lookup?.asset_id) assetId = lookup.asset_id
    } catch { /* fallback: dùng code gốc */ }
    router.push(`/assets/${assetId}`)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Lỗi khi xử lý QR'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-container animate-fade-in max-w-md mx-auto">
    <PageHeader
      title="Quét QR — Mở hồ sơ thiết bị"
      subtitle="Quét hoặc nhập mã QR / barcode để mở nhanh hồ sơ thiết bị tương ứng."
    />

    <div class="card p-6 space-y-4">
      <div>
        <label for="qr-code-input" class="block text-sm font-medium text-slate-700 mb-2">
          Mã QR / Barcode
        </label>
        <input
          id="qr-code-input"
          ref="qrInput"
          v-model="manualCode"
          type="text"
          class="form-input w-full text-sm"
          placeholder="Nhập hoặc scan mã thiết bị…"
          @keyup.enter="scan"
        />
      </div>
      <div v-if="error" class="alert-error text-sm">{{ error }}</div>
      <button
        class="btn-primary w-full"
        :disabled="loading || !manualCode.trim()"
        @click="scan"
      >
        {{ loading ? 'Đang mở…' : 'Mở hồ sơ thiết bị' }}
      </button>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Smoke test**

Run: `cd /home/miyano/frappe-bench/apps/assetcore/frontend && npm run build 2>&1 | tail -5`

Expected: build success.

Mở `http://localhost:3000/qr-scan` (hoặc route hiện hành), nhập 1 mã asset thật → router push thành công.

- [ ] **Step 3: Commit**

```bash
cd /home/miyano/frappe-bench/apps/assetcore
git add frontend/src/views/system/QRScanView.vue
git commit -m "refactor(fe-qr): scan QR opens asset detail (no state toggle)"
```

---

## Phase 3 — Cleanup

### Task 11: Xoá / dọn scripts utility

**Files:**
- Delete: `assetcore/scripts/fix_asset_gmdn.py`
- Modify: `assetcore/scripts/fix_master_display_names.py:68-72`
- Modify: `assetcore/scripts/cleanup_and_seed_assets.py:236,262,269`
- Modify: `assetcore/scripts/audit_master_data.py:20`

- [ ] **Step 1: Xoá file `fix_asset_gmdn.py`**

Run: `rm /home/miyano/frappe-bench/apps/assetcore/assetcore/scripts/fix_asset_gmdn.py`

- [ ] **Step 2: Dọn `fix_master_display_names.py`**

Xoá block dòng 68-72 (block sửa `gmdn_status` "Not Use" → "Active"). Nếu hàm còn xử lý `depreciation_method`, giữ phần đó.

- [ ] **Step 3: Dọn `cleanup_and_seed_assets.py`**

Tìm và xoá:
- Dòng 236: phần tử `"gmdn_status"` trong tuple kiểm tra keys
- Dòng 262: key `"gmdn_status": "In Use"` trong seed dict
- Dòng 269: phần tử `"gmdn_status"` trong tuple keys

- [ ] **Step 4: Dọn `audit_master_data.py`**

Dòng 20, xoá `"gmdn_status",` khỏi list `fields`.

- [ ] **Step 5: Verify scripts không còn reference**

Run: `grep -n "gmdn_status" /home/miyano/frappe-bench/apps/assetcore/assetcore/scripts/*.py`

Expected: không kết quả.

- [ ] **Step 6: Commit**

```bash
cd /home/miyano/frappe-bench/apps/assetcore
git add -A assetcore/scripts/
git commit -m "chore: drop gmdn_status references from utility scripts"
```

---

### Task 12: Sync docs imm-00 + audit cuối

**Files:**
- Modify: `docs/imm-00/04_Backend_Design.md`

- [ ] **Step 1: Tìm các mention `gmdn_status` trong docs imm-00**

Run: `grep -rn "gmdn_status" /home/miyano/frappe-bench/apps/assetcore/docs/imm-00/`

- [ ] **Step 2: Xoá/sửa từng đoạn**

Mỗi đoạn nói về `gmdn_status` field, modal, QR toggle → thay bằng note:

```markdown
**Note (2026-05-19):** Field `gmdn_status` đã được loại bỏ. Lọc và quản lý thiết bị theo
`gmdn_code` (kế thừa từ Asset Category). Tham chiếu:
[docs/res/gmdn-asset-category-analysis.md](../res/gmdn-asset-category-analysis.md) §6.
```

Bổ sung mô tả filter `gmdn_code` mới trong section "API List Assets".

- [ ] **Step 3: Final repo-wide audit**

Run: `grep -rn "gmdn_status\|GmdnStatus\|update_gmdn_status\|toggle_gmdn_status\|updateGmdnStatus\|toggleGmdnStatus\|GMDN_OPTIONS\|GMDN_STATUS_LABEL" /home/miyano/frappe-bench/apps/assetcore/ --include="*.py" --include="*.json" --include="*.ts" --include="*.vue" --include="*.js" --include="*.md" 2>&1 | grep -v __pycache__ | grep -v "node_modules" | grep -v "public/frontend/assets/" | grep -v "docs/res/gmdn-asset-category-analysis.md"`

Expected: không kết quả (file analysis được phép giữ vì là tài liệu lịch sử).

- [ ] **Step 4: Chạy lại full test suite**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm00_list_assets`

Expected: 3 PASS.

Optional (nếu có): full module test
Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore 2>&1 | tail -30`

Expected: không regression liên quan IMM-00.

- [ ] **Step 5: Build FE production**

Run: `cd /home/miyano/frappe-bench/apps/assetcore/frontend && npm run build 2>&1 | tail -5`

Expected: build success, không TS error.

- [ ] **Step 6: Smoke test cuối trên `/assets`**

Manual checklist tại `http://localhost:3000/assets`:
- [ ] Filter "GMDN Code" hiển thị dropdown autocomplete với danh sách mã GMDN từ categories
- [ ] Filter trả đúng tập asset matching
- [ ] Cột bảng "GMDN" hiển thị mã code thật (không phải chip status)
- [ ] Tooltip cột GMDN hiển thị `gmdn_term`
- [ ] Click vào code trong row → quickFilter set, list refresh
- [ ] Ô search hỗ trợ tìm bằng `gmdn_code` (nhập "35304" tìm ra asset)
- [ ] Trang detail asset không còn nút/modal "Đổi GMDN Status"
- [ ] Trang `/qr-scan` (nếu có) scan QR → redirect tới asset detail, không toggle state

- [ ] **Step 7: Commit cuối + tổng hợp**

```bash
cd /home/miyano/frappe-bench/apps/assetcore
git add docs/
git commit -m "docs(imm-00): sync gmdn_status removal — filter by gmdn_code"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ Drop `gmdn_status` field → Tasks 2, 3, 4
- ✅ Drop service/API endpoints → Tasks 2, 3
- ✅ Add `gmdn_code` filter ở list_assets → Task 3
- ✅ Extend search bao gồm `gmdn_code` → Task 3
- ✅ Rewrite filter UI + cột bảng → Task 8
- ✅ Dọn AssetDetailView modal → Task 9
- ✅ Repurpose QRScanView → Task 10
- ✅ Cleanup scripts → Task 11
- ✅ Sync docs → Task 12
- ✅ Migration DB column → Task 4 (pre_model_sync patch)

**Risk / rollback:**
- Patch xoá column là **không reversible** trong cùng release. Trước khi merge: backup `tabAC Asset` (`bench --site <site> backup`).
- Nếu rollback cần: revert commits + restore DB từ backup (cột `gmdn_status` không thể tạo lại với data cũ).

**Out of scope (backlog riêng):**
- Tính năng `clinical_availability` (QR check-in/out chuẩn) — không làm trong plan này.
- Auto-sync `gmdn_code` từ Device Model khi thay đổi (ref §6.2 vấn đề 8) — backlog `assetcore-doc` follow-up.
