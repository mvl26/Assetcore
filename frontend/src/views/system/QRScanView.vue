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
