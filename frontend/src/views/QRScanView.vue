<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-00 QR Scan → GMDN toggle
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { getBarcodeLookup } from '@/api/imm04'
import { toggleGmdnStatus, getAsset } from '@/api/imm00'
import { GMDN_STATUS_LABEL } from '@/stores/imm00'

const router = useRouter()
const manualCode = ref('')
const loading = ref(false)
const error = ref('')
const result = ref<{ asset: string; name: string; from: string; to: string } | null>(null)
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
  result.value = null
  try {
    // Thử barcode lookup (QR tag / serial). Nếu không tìm thấy, dùng code trực tiếp như AC Asset name.
    let assetId = code
    try {
      const lookup = await getBarcodeLookup(code)
      if (lookup?.asset_id) assetId = lookup.asset_id
    } catch { /* không phải barcode/QR tag → tiếp tục với code gốc */ }

    const toggle = await toggleGmdnStatus(assetId) as unknown as { gmdn_status: string; previous: string }
    const asset = await getAsset(assetId) as unknown as { asset_name: string }
    result.value = {
      asset: assetId,
      name: asset?.asset_name || assetId,
      from: toggle.previous,
      to: toggle.gmdn_status,
    }
    manualCode.value = ''
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi xử lý QR'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-container animate-fade-in max-w-md mx-auto">
    <div class="mb-6">
      <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00</p>
      <h1 class="text-2xl font-bold text-slate-900">Quét QR — GMDN Status</h1>
      <p class="text-sm text-slate-500 mt-1">
        Quét QR khi bắt đầu sử dụng → chuyển <strong>Đang sử dụng</strong>.
        Quét lại khi kết thúc → về <strong>Không sử dụng</strong>.
      </p>
    </div>

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
        {{ loading ? 'Đang xử lý…' : 'Xác nhận & Chuyển trạng thái' }}
      </button>
    </div>

    <!-- Result -->
    <div v-if="result" class="card p-5 mt-4 border-l-4 border-green-500">
      <p class="text-xs font-semibold text-green-700 uppercase tracking-wide">✓ Đã cập nhật</p>
      <p class="text-base font-semibold text-slate-900 mt-1">{{ result.name }}</p>
      <p class="text-xs font-mono text-slate-400">{{ result.asset }}</p>
      <div class="mt-3 flex items-center gap-2 text-sm">
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">
          {{ GMDN_STATUS_LABEL[result.from] || result.from }}
        </span>
        <span class="text-slate-400">→</span>
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
              :class="result.to === 'In Use' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
          {{ GMDN_STATUS_LABEL[result.to] || result.to }}
        </span>
      </div>
      <div class="flex gap-2 mt-4">
        <button class="btn-ghost text-xs flex-1" @click="router.push(`/assets/${result.asset}`)">
          Xem thiết bị
        </button>
        <button class="btn-primary text-xs flex-1" @click="result = null">
          Quét tiếp
        </button>
      </div>
    </div>
  </div>
</template>
