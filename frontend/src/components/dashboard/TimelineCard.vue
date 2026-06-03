<script setup lang="ts">
// Timeline card — sự kiện/audit gần đây. Tên thiết bị qua asset_name (LL-FE-6).
// severity/status (nếu có) qua StatusBadge — không leak raw code.
// Core Doc §9.7: row-drill — rowTo(row) trả RouterLocation | null. Có target →
// bọc <li> trong RouterLink (feed truy về source record); null → dòng tĩnh.
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { RouteLocationRaw } from 'vue-router'

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

const props = defineProps<{
  title: string
  rows: TimelineRow[]
  emptyText?: string
  /** §9.7 — mỗi dòng → route source record (hoặc null = tĩnh). */
  rowTo?: (row: TimelineRow) => RouteLocationRaw | null
}>()

function label(r: TimelineRow): string {
  return r.title || r.asset_name || (r.asset ? String(r.asset) : '') || '—'
}
function when(r: TimelineRow): string {
  const t = r.reported_at || r.modified || ''
  return t ? String(t).slice(0, 16) : ''
}
function target(r: TimelineRow): RouteLocationRaw | null {
  return props.rowTo ? props.rowTo(r) : null
}
</script>

<template>
  <div class="rounded-xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-100 px-4 py-3">
      <h3 class="text-sm font-semibold text-neutral-800">{{ title }}</h3>
    </div>
    <div class="p-4">
      <ul v-if="rows.length" class="space-y-1">
        <li v-for="(r, i) in rows" :key="i">
          <!-- Drillable row → RouterLink (hover affordance); else <div> tĩnh. §9.7 -->
          <component
            :is="target(r) ? 'RouterLink' : 'div'"
            :to="target(r) ?? undefined"
            class="flex items-start gap-3 rounded-lg px-2 py-1.5 -mx-2 transition"
            :class="target(r)
              ? 'group cursor-pointer hover:bg-neutral-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300'
              : ''"
          >
            <span class="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-neutral-300"
              :class="target(r) ? 'group-hover:bg-blue-400' : ''" />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="truncate text-sm text-neutral-700"
                  :class="target(r) ? 'group-hover:text-blue-700' : ''">{{ label(r) }}</span>
                <StatusBadge v-if="r.severity" :state="r.severity" size="xs" />
                <StatusBadge v-else-if="r.status" :state="r.status" size="xs" />
              </div>
              <p v-if="when(r)" class="text-xs text-neutral-400">{{ when(r) }}</p>
            </div>
            <svg v-if="target(r)" class="mt-1 h-3.5 w-3.5 shrink-0 text-neutral-300 transition group-hover:translate-x-0.5 group-hover:text-neutral-500"
              fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </component>
        </li>
      </ul>
      <p v-else class="py-6 text-center text-sm text-neutral-400">{{ emptyText ?? 'Chưa có sự kiện' }}</p>
    </div>
  </div>
</template>
