<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Lịch sử audit-trail dùng chung cho trang chi tiết IMM-16
// (Finding / CAPA / Management Review / Rule). Truy IMM Audit Trail
// theo ref_doctype + ref_name (assetcore.api.imm16.get_record_history).
import { ref, onMounted, watch } from 'vue'
import { getRecordHistory } from '@/api/imm16'
import type { RecordHistoryEntry } from '@/api/imm16'

const props = defineProps<{
  refDoctype: string
  refName: string
}>()

const entries = ref<RecordHistoryEntry[]>([])
const loading = ref(false)
const loaded = ref(false)

async function load() {
  if (!props.refName) return
  loading.value = true
  try {
    const res = await getRecordHistory(props.refDoctype, props.refName)
    entries.value = res.items ?? []
  } catch {
    entries.value = []
  } finally {
    loading.value = false
    loaded.value = true
  }
}

function fmt(ts?: string) {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('vi-VN')
}

defineExpose({ reload: load })
onMounted(load)
watch(() => props.refName, load)
</script>

<template>
  <div class="card p-5">
    <h2 class="font-semibold text-slate-700 mb-3">Lịch sử &amp; Nhật ký kiểm toán</h2>
    <div v-if="loading" class="text-sm text-slate-400 py-4">Đang tải lịch sử...</div>
    <div v-else-if="loaded && !entries.length" class="text-sm text-slate-400 py-4">
      Chưa có sự kiện nào được ghi nhận.
    </div>
    <ol v-else class="relative border-l border-slate-200 ml-2 space-y-4">
      <li v-for="e in entries" :key="e.name" class="ml-4">
        <span class="absolute -left-1.5 w-3 h-3 rounded-full bg-brand-500 border-2 border-white" />
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm font-medium text-slate-800">{{ e.change_summary || e.event_type }}</span>
          <span
            v-if="e.from_status || e.to_status"
            class="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600"
          >
            {{ e.from_status || '—' }} → {{ e.to_status || '—' }}
          </span>
        </div>
        <p class="text-xs text-slate-400 mt-0.5">
          {{ fmt(e.timestamp) }} · {{ e.actor_name || e.actor }}
        </p>
      </li>
    </ol>
  </div>
</template>
