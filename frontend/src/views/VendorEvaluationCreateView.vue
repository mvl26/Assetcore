<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm03Store } from '@/stores/imm03'
import SmartSelect from '@/components/common/SmartSelect.vue'
import VendorScoringTable from '@/components/common/VendorScoringTable.vue'
import type { MasterItem } from '@/stores/useMasterDataStore'
import type { VendorEvaluationItem, LockedPlan } from '@/api/imm03'
import { getLockedPlans } from '@/api/imm03'

const router = useRouter()
const store  = useImm03Store()

const today = new Date().toISOString().split('T')[0]

const lockedPlans = ref<LockedPlan[]>([])
const loadingPlans = ref(false)

const form = ref({
  linked_plan: '',
  evaluation_date: today,
  bid_issue_date: '',
  bid_closing_date: '',
  bid_opening_date: '',
})

const errors  = ref<Record<string, string>>({})
const touched = ref<Record<string, boolean>>({})

const vendorRows = ref<VendorEvaluationItem[]>([])

// ─── Validation ───────────────────────────────────────────────────────────────

function validate(): boolean {
  const e: Record<string, string> = {}
  if (!form.value.linked_plan)     e.linked_plan = 'Vui lòng chọn kế hoạch mua sắm'
  if (vendorRows.value.length < 2) e.vendors     = 'Cần ít nhất 2 nhà cung cấp (VR-03-04)'
  for (const row of vendorRows.value) {
    if (!row.vendor.trim()) { e.vendors = 'Mã nhà cung cấp không được để trống'; break }
  }
  errors.value = e
  return Object.keys(e).length === 0
}

function touch(field: string) {
  touched.value[field] = true
  validate()
}

function fieldError(f: string): string {
  return touched.value[f] ? (errors.value[f] ?? '') : ''
}

// ─── Vendor rows ──────────────────────────────────────────────────────────────

function addVendorRow() {
  vendorRows.value.push({
    vendor: '',
    technical_score: 0,
    financial_score: 0,
    profile_score: 0,
    risk_score: 0,
    compliant_with_ts: 0,
    has_nd98_registration: 0,
    total_score: 0,
    score_band: 'D',
    bid_compliant: 1,
    quoted_delivery_weeks: null,
    offered_payment_terms: null,
  })
}

function onVendorRowsChange(updated: VendorEvaluationItem[]) {
  vendorRows.value = updated
}

function updateVendor(index: number, item: MasterItem) {
  vendorRows.value = vendorRows.value.map((row, i) =>
    i === index ? { ...row, vendor: item.id, vendor_name: item.name } : row,
  )
  touched.value.vendors = true
  validate()
}

function clearVendor(index: number) {
  vendorRows.value = vendorRows.value.map((row, i) =>
    i === index ? { ...row, vendor: '', vendor_name: undefined } : row,
  )
}

// ─── Submit ───────────────────────────────────────────────────────────────────

async function handleSubmit() {
  Object.keys(form.value).forEach(k => (touched.value[k] = true))
  touched.value.vendors = true
  if (!validate()) return

  // 1. Create VE
  const veName = await store.createVe({
    linked_plan: form.value.linked_plan,
    evaluation_date: form.value.evaluation_date || undefined,
    bid_issue_date: form.value.bid_issue_date || undefined,
    bid_closing_date: form.value.bid_closing_date || undefined,
    bid_opening_date: form.value.bid_opening_date || undefined,
  })
  if (!veName) return

  // 2. Add each vendor row
  let allOk = true
  for (const row of vendorRows.value) {
    const ok = await store.addVendor({
      ve_name: veName,
      vendor: row.vendor,
      technical_score: row.technical_score,
      financial_score: row.financial_score,
      profile_score: row.profile_score,
      risk_score: row.risk_score,
      quoted_price: row.quoted_price ?? undefined,
      compliant_with_ts: row.compliant_with_ts,
      has_nd98_registration: row.has_nd98_registration,
      notes: row.notes ?? undefined,
      bid_compliant: row.bid_compliant ?? 1,
      quoted_delivery_weeks: row.quoted_delivery_weeks ?? undefined,
      offered_payment_terms: row.offered_payment_terms ?? undefined,
    })
    if (!ok) { allOk = false; break }
  }

  if (allOk) {
    router.replace(`/planning/vendor-evaluations/${veName}`)
  }
}

onMounted(async () => {
  store.veError = null
  loadingPlans.value = true
  try { lockedPlans.value = await getLockedPlans() }
  catch { /* keep empty */ }
  finally { loadingPlans.value = false }
  addVendorRow()
  addVendorRow()
})
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-03</p>
        <h1 class="text-2xl font-bold text-slate-900">Tạo Phiếu Đánh giá NCC</h1>
        <p class="text-sm text-slate-500 mt-1">Khởi tạo phiếu đánh giá nhà cung cấp cho đặc tả kỹ thuật</p>
      </div>
      <button class="btn-ghost shrink-0" @click="router.back()">Quay lại</button>
    </div>

    <!-- Error -->
    <div v-if="store.veError" class="alert-error mb-4">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.veError }}</span>
      <button class="text-xs font-semibold underline" @click="store.veError = null">Đóng</button>
    </div>

    <!-- Section 1: Thông tin cơ bản -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:0ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
        Thông tin cơ bản
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">

        <!-- Kế hoạch mua sắm (Budget Locked) -->
        <div class="form-group sm:col-span-2">
          <label class="form-label">
            Kế hoạch mua sắm <span class="text-red-500">*</span>
          </label>
          <div v-if="loadingPlans" class="form-input text-slate-400 text-sm">Đang tải...</div>
          <select
            v-else
            v-model="form.linked_plan"
            class="form-select"
            :class="{ 'border-red-400': fieldError('linked_plan') }"
            @change="touch('linked_plan')"
          >
            <option value="">— Chọn kế hoạch mua sắm đã khóa ngân sách —</option>
            <option v-for="p in lockedPlans" :key="p.name" :value="p.name">
              {{ p.name }} — Năm {{ p.plan_year }} ({{ p.approved_budget?.toLocaleString('vi-VN') }} VNĐ)
            </option>
          </select>
          <p v-if="lockedPlans.length === 0 && !loadingPlans" class="mt-1 text-xs text-amber-500">
            Chưa có kế hoạch mua sắm nào ở trạng thái Budget Locked.
          </p>
          <p v-if="fieldError('linked_plan')" class="mt-1 text-xs text-red-500">
            {{ fieldError('linked_plan') }}
          </p>
        </div>

        <div class="form-group">
          <label class="form-label">Ngày đánh giá</label>
          <input v-model="form.evaluation_date" type="date" class="form-input" />
        </div>
      </div>
    </div>

    <!-- Section 1b: Hồ sơ Thầu (WHO 6.4) -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:25ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
        Hồ sơ Thầu <span class="text-xs font-normal text-slate-400">(WHO 6.4)</span>
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="form-group">
          <label class="form-label">Ngày phát hành HSMT</label>
          <input v-model="form.bid_issue_date" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Hạn nộp hồ sơ</label>
          <input v-model="form.bid_closing_date" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Ngày mở thầu</label>
          <input v-model="form.bid_opening_date" type="date" class="form-input" />
        </div>
      </div>
    </div>

    <!-- Section 2: Nhà cung cấp -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:50ms">
      <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
        <div>
          <h2 class="text-sm font-semibold text-slate-700">
            Nhà cung cấp ({{ vendorRows.length }})
          </h2>
          <p class="text-xs text-slate-400 mt-0.5">Tối thiểu 2 nhà cung cấp theo VR-03-04</p>
        </div>
        <button type="button" class="btn-primary text-xs" @click="addVendorRow">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm NCC
        </button>
      </div>

      <div v-if="fieldError('vendors') || (touched.vendors && errors.vendors)"
           class="alert-error mb-4 text-sm">
        {{ errors.vendors }}
      </div>

      <!-- Vendor rows: vendor select + scoring table -->
      <div v-if="vendorRows.length > 0" class="space-y-3 mb-4">
        <div v-for="(row, i) in vendorRows" :key="i"
             class="p-3 bg-slate-50 rounded-lg border border-slate-100">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs text-slate-400 w-5 shrink-0 text-center font-mono">{{ i + 1 }}</span>
            <div class="flex-1">
              <SmartSelect
                doctype="AC Supplier"
                placeholder="Tìm nhà cung cấp..."
                :model-value="row.vendor"
                @select="updateVendor(i, $event)"
                @clear="clearVendor(i)"
              />
            </div>
            <input
              :value="row.quoted_price ?? ''"
              type="number"
              min="0"
              step="1000000"
              class="form-input text-sm w-36"
              placeholder="Báo giá (VNĐ)"
              @input="vendorRows[i] = { ...vendorRows[i], quoted_price: Number(($event.target as HTMLInputElement).value) || null }"
            />
            <button
              type="button"
              class="text-slate-300 hover:text-red-500 transition-colors shrink-0"
              @click="vendorRows.splice(i, 1)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 pl-7">
            <label class="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                :checked="row.bid_compliant === 1"
                class="rounded"
                @change="vendorRows[i] = { ...vendorRows[i], bid_compliant: ($event.target as HTMLInputElement).checked ? 1 : 0 }"
              />
              Hồ sơ hợp lệ
            </label>
            <input
              :value="row.quoted_delivery_weeks ?? ''"
              type="number"
              min="0"
              class="form-input text-xs"
              placeholder="Giao hàng (tuần)"
              @input="vendorRows[i] = { ...vendorRows[i], quoted_delivery_weeks: Number(($event.target as HTMLInputElement).value) || null }"
            />
            <input
              :value="row.offered_payment_terms ?? ''"
              type="text"
              class="form-input text-xs"
              placeholder="Điều khoản TT đề xuất"
              @input="vendorRows[i] = { ...vendorRows[i], offered_payment_terms: ($event.target as HTMLInputElement).value || null }"
            />
          </div>
        </div>
      </div>

      <!-- Scoring table -->
      <div v-if="vendorRows.length > 0" class="mt-4">
        <p class="text-xs text-slate-500 font-medium mb-2 uppercase tracking-wide">Bảng chấm điểm</p>
        <VendorScoringTable
          :items="vendorRows"
          :editable="true"
          @update:items="onVendorRowsChange"
        />
      </div>

      <div v-else class="py-10 text-center text-sm text-slate-400 italic">
        Chưa có nhà cung cấp nào. Nhấn "Thêm NCC" để bắt đầu.
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-3 pb-8">
      <button
        class="btn-primary"
        :disabled="store.veLoading"
        @click="handleSubmit"
      >
        <svg v-if="store.veLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        {{ store.veLoading ? 'Đang lưu…' : 'Tạo Phiếu Đánh giá NCC' }}
      </button>
      <button class="btn-ghost" :disabled="store.veLoading" @click="router.back()">Hủy</button>
    </div>

  </div>
</template>
