<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useImm06Store } from '@/stores/imm06'
import SmartSelect from '@/components/common/SmartSelect.vue'
import type { MasterItem } from '@/stores/useMasterDataStore'
import { frappeGet } from '@/api/helpers'

const router = useRouter()
const store  = useImm06Store()

const today = new Date().toISOString().split('T')[0]

const form = ref({
  commissioning_ref: '',
  asset:             '',
  asset_name:        '',
  clinical_dept:     '',
  handover_date:     today,
  received_by:       '',
  handover_type:     'Full' as 'Full' | 'Conditional' | 'Temporary',
  conditions_if_conditional: '',
  handover_notes:    '',
})

const commStatus   = ref<'ok' | 'not_released' | 'loading' | ''>('')
const errors       = ref<Record<string, string>>({})
const touched      = ref<Record<string, boolean>>({})

// ─── Validation ───────────────────────────────────────────────────────────────

function validate(): boolean {
  const e: Record<string, string> = {}
  if (!form.value.commissioning_ref)  e.commissioning_ref = 'Vui lòng chọn phiếu nghiệm thu'
  if (commStatus.value === 'not_released') e.commissioning_ref = 'Commissioning chưa đạt Clinical Release'
  if (!form.value.clinical_dept)      e.clinical_dept = 'Vui lòng chọn khoa nhận'
  if (!form.value.handover_date)      e.handover_date = 'Vui lòng chọn ngày bàn giao'
  if (!form.value.received_by)        e.received_by = 'Vui lòng chọn người nhận'
  if (form.value.handover_type !== 'Full' && !form.value.conditions_if_conditional)
    e.conditions_if_conditional = 'Vui lòng ghi rõ điều kiện bàn giao'
  errors.value = e
  return Object.keys(e).length === 0
}

function touch(f: string) { touched.value[f] = true; validate() }
function fieldError(f: string) { return touched.value[f] ? (errors.value[f] ?? '') : '' }

// ─── Commissioning select → auto-fill asset ───────────────────────────────────

async function onCommSelect(item: MasterItem) {
  form.value.commissioning_ref = item.id
  form.value.asset = ''
  form.value.asset_name = ''
  commStatus.value = 'loading'
  touched.value.commissioning_ref = true
  try {
    const data = await frappeGet<{ workflow_state: string; final_asset: string; final_asset_name?: string }>(
      '/api/method/assetcore.api.imm04.get_commissioning_record',
      { name: item.id },
    )
    if (data.workflow_state === 'Clinical Release') {
      commStatus.value = 'ok'
      form.value.asset      = data.final_asset ?? ''
      form.value.asset_name = data.final_asset_name ?? data.final_asset ?? ''
    } else {
      commStatus.value = 'not_released'
    }
  } catch {
    commStatus.value = 'not_released'
  }
  validate()
}

function clearComm() {
  form.value.commissioning_ref = ''
  form.value.asset = ''
  form.value.asset_name = ''
  commStatus.value = ''
}

// ─── Submit ───────────────────────────────────────────────────────────────────

async function handleSubmit() {
  Object.keys(form.value).forEach(k => (touched.value[k] = true))
  if (!validate()) return
  const name = await store.createHr({
    commissioning_ref: form.value.commissioning_ref,
    clinical_dept:     form.value.clinical_dept,
    handover_date:     form.value.handover_date,
    received_by:       form.value.received_by,
    handover_type:     form.value.handover_type,
  })
  if (name) router.replace(`/handover/${name}`)
}

watch(() => form.value.handover_type, () => {
  if (form.value.handover_type === 'Full') form.value.conditions_if_conditional = ''
})
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-06</p>
        <h1 class="text-2xl font-bold text-slate-900">Tạo Phiếu Bàn giao</h1>
        <p class="text-sm text-slate-500 mt-1">Khởi tạo phiếu bàn giao thiết bị từ Commissioning đã Clinical Release</p>
      </div>
      <button class="btn-ghost shrink-0" @click="router.back()">Quay lại</button>
    </div>

    <!-- Error -->
    <div v-if="store.error" class="alert-error mb-4">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline" @click="store.error = null">Đóng</button>
    </div>

    <!-- Section 1: Commissioning -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:0ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
        Phiếu Nghiệm thu (Commissioning)
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="form-group">
          <label class="form-label">Phiếu Nghiệm thu <span class="text-red-500">*</span></label>
          <SmartSelect
            doctype="Asset Commissioning"
            placeholder="Tìm phiếu nghiệm thu..."
            :model-value="form.commissioning_ref"
            @select="onCommSelect"
            @clear="clearComm"
          />
          <!-- Status feedback -->
          <div v-if="commStatus === 'loading'" class="mt-1.5 text-xs text-slate-400">Đang kiểm tra trạng thái...</div>
          <div v-else-if="commStatus === 'not_released'"
               class="mt-1.5 flex items-center gap-1.5 text-xs text-red-600">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            VR-01: Commissioning chưa đạt Clinical Release — không thể tạo phiếu bàn giao
          </div>
          <div v-else-if="commStatus === 'ok'"
               class="mt-1.5 flex items-center gap-1.5 text-xs text-emerald-600">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            Commissioning hợp lệ — Clinical Release
          </div>
          <p v-if="fieldError('commissioning_ref')" class="mt-1 text-xs text-red-500">
            {{ fieldError('commissioning_ref') }}
          </p>
        </div>

        <div class="form-group">
          <label class="form-label">Thiết bị (tự động)</label>
          <div class="form-input bg-slate-50 select-none cursor-default text-sm"
               :class="form.asset ? 'text-slate-800 font-mono' : 'text-slate-400'">
            {{ form.asset_name || form.asset || 'Chọn Commissioning để tự động điền' }}
          </div>
          <p class="mt-1 text-xs text-slate-400">Lấy từ trường final_asset của Commissioning</p>
        </div>
      </div>
    </div>

    <!-- Section 2: Thông tin bàn giao -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:40ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
        Thông tin Bàn giao
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">

        <div class="form-group">
          <label class="form-label">Khoa nhận <span class="text-red-500">*</span></label>
          <SmartSelect
            doctype="AC Department"
            placeholder="Tìm khoa..."
            :model-value="form.clinical_dept"
            @select="(item: MasterItem) => { form.clinical_dept = item.id; touch('clinical_dept') }"
            @clear="() => { form.clinical_dept = ''; touch('clinical_dept') }"
          />
          <p v-if="fieldError('clinical_dept')" class="mt-1 text-xs text-red-500">{{ fieldError('clinical_dept') }}</p>
        </div>

        <div class="form-group">
          <label class="form-label">Ngày bàn giao <span class="text-red-500">*</span></label>
          <input v-model="form.handover_date" type="date" class="form-input"
                 :class="{ 'border-red-400': fieldError('handover_date') }"
                 @change="touch('handover_date')" />
          <p v-if="fieldError('handover_date')" class="mt-1 text-xs text-red-500">{{ fieldError('handover_date') }}</p>
        </div>

        <div class="form-group">
          <label class="form-label">Người nhận đại diện <span class="text-red-500">*</span></label>
          <SmartSelect
            doctype="User"
            placeholder="Tìm người nhận..."
            :model-value="form.received_by"
            @select="(item: MasterItem) => { form.received_by = item.id; touch('received_by') }"
            @clear="() => { form.received_by = ''; touch('received_by') }"
          />
          <p v-if="fieldError('received_by')" class="mt-1 text-xs text-red-500">{{ fieldError('received_by') }}</p>
        </div>

        <div class="form-group">
          <label class="form-label">Loại bàn giao <span class="text-red-500">*</span></label>
          <div class="flex gap-3 mt-1">
            <label v-for="t in ['Full', 'Conditional', 'Temporary']" :key="t"
                   class="flex items-center gap-2 cursor-pointer">
              <input type="radio" v-model="form.handover_type" :value="t" class="accent-brand-600" />
              <span class="text-sm text-slate-700">{{ t === 'Full' ? 'Đầy đủ' : t === 'Conditional' ? 'Có điều kiện' : 'Tạm thời' }}</span>
            </label>
          </div>
        </div>

        <div v-if="form.handover_type !== 'Full'" class="form-group sm:col-span-2">
          <label class="form-label">Điều kiện bàn giao <span class="text-red-500">*</span></label>
          <textarea
            v-model="form.conditions_if_conditional"
            rows="3"
            class="form-input resize-none"
            :class="{ 'border-red-400': fieldError('conditions_if_conditional') }"
            placeholder="Mô tả điều kiện hoặc giới hạn sử dụng khi bàn giao..."
            @blur="touch('conditions_if_conditional')"
          />
          <p v-if="fieldError('conditions_if_conditional')" class="mt-1 text-xs text-red-500">
            {{ fieldError('conditions_if_conditional') }}
          </p>
        </div>
      </div>
    </div>

    <!-- Section 3: Ghi chú -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:80ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
        Ghi chú <span class="text-xs font-normal text-slate-400">(tùy chọn)</span>
      </h2>
      <textarea
        v-model="form.handover_notes"
        rows="4"
        class="form-textarea w-full"
        placeholder="Ghi chú về tình trạng thiết bị, phụ kiện kèm theo, lưu ý vận hành..."
      />
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-3 pb-8">
      <button class="btn-primary" :disabled="store.loading || commStatus === 'not_released'" @click="handleSubmit">
        <svg v-if="store.loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        {{ store.loading ? 'Đang lưu…' : 'Lưu phiếu bàn giao' }}
      </button>
      <button class="btn-ghost" :disabled="store.loading" @click="router.back()">Hủy</button>
    </div>

  </div>
</template>
