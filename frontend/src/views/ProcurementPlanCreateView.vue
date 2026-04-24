<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm02Store } from '@/stores/imm02'

const router = useRouter()
const store  = useImm02Store()

const form = ref({
  plan_year:       new Date().getFullYear(),
  approved_budget: 0,
})
const errors  = ref<Record<string, string>>({})
const touched = ref<Record<string, boolean>>({})

const budgetPreview = computed(() => {
  if (!form.value.approved_budget) return ''
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency', currency: 'VND', maximumFractionDigits: 0,
  }).format(form.value.approved_budget)
})

function validate(): boolean {
  const e: Record<string, string> = {}
  const yr = form.value.plan_year
  if (!yr || yr < 2000 || yr > 2100) e.plan_year = 'Năm kế hoạch không hợp lệ (2000–2100)'
  if (!form.value.approved_budget || form.value.approved_budget <= 0)
    e.approved_budget = 'Ngân sách duyệt phải > 0'
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

async function handleSubmit() {
  Object.keys(form.value).forEach(k => (touched.value[k] = true))
  if (!validate()) return
  const name = await store.createPlan(form.value.plan_year, form.value.approved_budget)
  if (name) router.replace(`/planning/procurement-plans/${name}`)
}

onMounted(() => store.clearError())
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-02</p>
        <h1 class="text-2xl font-bold text-slate-900">Tạo Kế hoạch Mua sắm</h1>
        <p class="text-sm text-slate-500 mt-1">Thiết lập kế hoạch mua sắm thiết bị y tế cho năm tài chính</p>
      </div>
      <button class="btn-ghost shrink-0" @click="router.back()">Quay lại</button>
    </div>

    <div v-if="store.error" class="alert-error mb-4">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline" @click="store.clearError">Đóng</button>
    </div>

    <div class="card animate-slide-up max-w-lg">
      <h2 class="text-sm font-semibold text-slate-700 mb-5">Thông tin kế hoạch</h2>
      <div class="grid grid-cols-1 gap-5">
        <div class="form-group">
          <label class="form-label">Năm kế hoạch <span class="text-red-500">*</span></label>
          <input v-model.number="form.plan_year" type="number" min="2000" max="2100" class="form-input"
                 :class="{ 'border-red-400': fieldError('plan_year') }"
                 placeholder="vd: 2026"
                 @blur="touch('plan_year')" />
          <p v-if="fieldError('plan_year')" class="mt-1 text-xs text-red-500">{{ fieldError('plan_year') }}</p>
        </div>

        <div class="form-group">
          <label class="form-label">Ngân sách duyệt (VNĐ) <span class="text-red-500">*</span></label>
          <input v-model.number="form.approved_budget" type="number" min="0" class="form-input"
                 :class="{ 'border-red-400': fieldError('approved_budget') }"
                 placeholder="vd: 5000000000"
                 @blur="touch('approved_budget')" />
          <p v-if="budgetPreview && !fieldError('approved_budget')" class="mt-1 text-xs text-slate-500">
            {{ budgetPreview }}
          </p>
          <p v-if="fieldError('approved_budget')" class="mt-1 text-xs text-red-500">
            {{ fieldError('approved_budget') }}
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2 mt-6 pt-5 border-t border-slate-100">
        <button class="btn-primary" :disabled="store.loading" @click="handleSubmit">
          <svg v-if="store.loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          {{ store.loading ? 'Đang tạo…' : 'Tạo kế hoạch' }}
        </button>
        <button class="btn-ghost" :disabled="store.loading" @click="router.back()">Hủy</button>
      </div>
    </div>

  </div>
</template>
