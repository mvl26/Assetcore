<script setup lang="ts">
// Timeline card — sự kiện/audit gần đây. Tên thiết bị qua asset_name (LL-FE-6).
// severity/status (nếu có) qua StatusBadge — không leak raw code.
import StatusBadge from '@/components/common/StatusBadge.vue'

export interface TimelineRow {
  title?: string
  asset_name?: string
  asset?: string
  severity?: string
  status?: string
  reported_at?: string
  modified?: string
  [k: string]: unknown
}

defineProps<{ title: string; rows: TimelineRow[]; emptyText?: string }>()

function label(r: TimelineRow): string {
  return r.title || r.asset_name || (r.asset ? String(r.asset) : '') || '—'
}
function when(r: TimelineRow): string {
  const t = r.reported_at || r.modified || ''
  return t ? String(t).slice(0, 16) : ''
}
</script>

<template>
  <div class="rounded-xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-100 px-4 py-3">
      <h3 class="text-sm font-semibold text-neutral-800">{{ title }}</h3>
    </div>
    <div class="p-4">
      <ul v-if="rows.length" class="space-y-3">
        <li v-for="(r, i) in rows" :key="i" class="flex items-start gap-3">
          <span class="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-neutral-300" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="truncate text-sm text-neutral-700">{{ label(r) }}</span>
              <StatusBadge v-if="r.severity" :state="r.severity" size="xs" />
              <StatusBadge v-else-if="r.status" :state="r.status" size="xs" />
            </div>
            <p v-if="when(r)" class="text-xs text-neutral-400">{{ when(r) }}</p>
          </div>
        </li>
      </ul>
      <p v-else class="py-6 text-center text-sm text-neutral-400">{{ emptyText ?? 'Chưa có sự kiện' }}</p>
    </div>
  </div>
</template>
