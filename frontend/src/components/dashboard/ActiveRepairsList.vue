<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { ActiveRepair } from '@/stores/useDashboardStore'
import { tLabel, WO_STATUS_LABELS, PRIORITY_LABELS } from '@/constants/labels'

defineProps<{ repairs: ActiveRepair[] }>()
const router = useRouter()

function rowClass(days: number): string {
  if (days >= 14) return 'bg-red-50/80 hover:bg-red-50'
  if (days >= 7)  return 'bg-orange-50/60 hover:bg-orange-50'
  return 'hover:bg-slate-50'
}

function dayBadgeClass(days: number): string {
  if (days >= 14) return 'bg-red-100 text-red-700 border border-red-200'
  if (days >= 7)  return 'bg-orange-100 text-orange-700 border border-orange-200'
  if (days >= 3)  return 'bg-amber-50 text-amber-700 border border-amber-200'
  return 'bg-slate-100 text-slate-600'
}

function priorityClass(p: string): string {
  if (p === 'Emergency') return 'text-red-600 font-bold'
  if (p === 'Urgent')    return 'text-orange-600 font-semibold'
  return 'text-slate-500'
}
</script>

<template>
  <div class="card p-0 overflow-hidden">
    <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100">
      <div class="flex items-center gap-2">
        <span class="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
        <h3 class="text-sm font-semibold text-slate-800">Thiết bị đang sửa chữa</h3>
        <span class="text-xs text-slate-400">({{ repairs.length }})</span>
      </div>
      <button class="text-xs font-medium text-brand-600 hover:text-brand-800"
              @click="router.push('/cm/work-orders')">Xem tất cả →</button>
    </div>

    <div v-if="repairs.length === 0" class="px-5 py-10 text-center text-sm text-slate-400 italic">
      Không có thiết bị nào đang sửa chữa
    </div>

    <table v-else class="w-full text-sm">
      <thead class="bg-slate-50/80">
        <tr class="text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
          <th class="px-5 py-2.5">Thiết bị</th>
          <th class="px-3 py-2.5 hidden md:table-cell">Khoa</th>
          <th class="px-3 py-2.5">Trạng thái</th>
          <th class="px-3 py-2.5 hidden sm:table-cell">Ưu tiên</th>
          <th class="px-3 py-2.5 text-right">Số ngày</th>
          <th class="px-5 py-2.5" />
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100">
        <tr v-for="r in repairs" :key="r.name" :class="rowClass(r.downtime_days)"
            class="cursor-pointer transition-colors"
            @click="router.push(`/cm/work-orders/${r.name}`)">
          <td class="px-5 py-3">
            <p class="font-medium text-slate-800 truncate max-w-[260px]">{{ r.asset_name || r.asset }}</p>
            <p class="text-[11px] text-slate-400 font-mono">{{ r.name }}</p>
          </td>
          <td class="px-3 py-3 text-slate-600 hidden md:table-cell">{{ r.department || '—' }}</td>
          <td class="px-3 py-3">
            <span class="inline-block px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-700">
              {{ tLabel(WO_STATUS_LABELS, r.status) }}
            </span>
          </td>
          <td class="px-3 py-3 hidden sm:table-cell" :class="priorityClass(r.priority)">
            {{ tLabel(PRIORITY_LABELS, r.priority) }}
          </td>
          <td class="px-3 py-3 text-right">
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold"
                  :class="dayBadgeClass(r.downtime_days)">
              {{ r.downtime_days }} ngày
            </span>
          </td>
          <td class="px-5 py-3 text-right">
            <svg class="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
