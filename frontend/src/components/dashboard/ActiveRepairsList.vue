<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { ActiveRepair } from '@/stores/useDashboardStore'
import { translateStatus, getStatusColor } from '@/utils/formatters'

defineProps<{ repairs: ActiveRepair[] }>()
const router = useRouter()

function priorityConfig(p: string) {
  if (p === 'Emergency') return { cls: 'bg-red-500',    dot: 'bg-red-500',    label: 'Khẩn cấp' }
  if (p === 'Urgent')    return { cls: 'bg-orange-400', dot: 'bg-orange-400', label: 'Khẩn' }
  return                        { cls: 'bg-slate-400',  dot: 'bg-slate-300',  label: 'Bình thường' }
}

function downtimeConfig(days: number) {
  if (days >= 14) return { bar: 'bg-red-400',    text: 'text-red-600 font-bold',   badge: 'bg-red-100 text-red-700 border border-red-200' }
  if (days >= 7)  return { bar: 'bg-orange-400', text: 'text-orange-600 font-semibold', badge: 'bg-orange-100 text-orange-700 border border-orange-200' }
  if (days >= 3)  return { bar: 'bg-amber-400',  text: 'text-amber-600',           badge: 'bg-amber-50 text-amber-700 border border-amber-200' }
  return                 { bar: 'bg-emerald-400',text: 'text-emerald-700',         badge: 'bg-emerald-50 text-emerald-700 border border-emerald-200' }
}

const MAX_DAYS = 21
</script>

<template>
  <div class="card p-0 overflow-hidden h-full flex flex-col">
    <!-- Header -->
    <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100 shrink-0">
      <div class="flex items-center gap-2">
        <span class="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
        <h3 class="text-sm font-semibold text-slate-800">Thiết bị đang sửa chữa</h3>
        <span class="text-xs text-slate-400 tabular-nums">({{ repairs.length }})</span>
      </div>
      <button class="text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
              @click="router.push('/cm/work-orders')">Xem tất cả →</button>
    </div>

    <!-- Empty state -->
    <div v-if="repairs.length === 0"
         class="flex-1 flex flex-col items-center justify-center py-12 gap-2 text-slate-400">
      <svg class="w-10 h-10 opacity-30" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round"
              d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p class="text-sm font-medium">Không có thiết bị nào đang sửa chữa</p>
    </div>

    <!-- Card list -->
    <div v-else class="divide-y divide-slate-50 overflow-y-auto flex-1">
      <div
        v-for="r in repairs" :key="r.name"
        class="px-5 py-3.5 hover:bg-slate-50/70 cursor-pointer transition-colors group"
        @click="router.push(`/cm/work-orders/${r.name}`)"
      >
        <!-- Row 1: priority dot + tên + badge trạng thái -->
        <div class="flex items-start gap-3">
          <span class="mt-1.5 w-2 h-2 rounded-full shrink-0"
                :class="priorityConfig(r.priority).dot" />
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="font-semibold text-slate-800 text-sm truncate">
                {{ r.asset_name || r.asset }}
              </p>
              <span :class="['text-[11px] px-1.5 py-0.5 rounded font-medium', getStatusColor(r.status)]">
                {{ translateStatus(r.status) }}
              </span>
            </div>
            <!-- Row 2: mã WO + khoa -->
            <div class="flex items-center gap-2 mt-0.5 text-[11px] text-slate-400">
              <span class="font-mono">{{ r.name }}</span>
              <span v-if="r.department_name" class="before:content-['·'] before:mr-2">
                {{ r.department_name }}
              </span>
              <span v-if="r.priority !== 'Normal'" class="before:content-['·'] before:mr-2 font-medium"
                    :class="priorityConfig(r.priority).cls">
                {{ priorityConfig(r.priority).label }}
              </span>
            </div>
          </div>
          <!-- ngày downtime -->
          <span class="shrink-0 text-[11px] px-2 py-0.5 rounded font-semibold tabular-nums"
                :class="downtimeConfig(r.downtime_days).badge">
            {{ r.downtime_days }}d
          </span>
        </div>

        <!-- Row 3: downtime progress bar -->
        <div class="mt-2.5 ml-5">
          <div class="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div class="h-full rounded-full transition-all duration-500"
                 :class="downtimeConfig(r.downtime_days).bar"
                 :style="{ width: Math.min((r.downtime_days / MAX_DAYS) * 100, 100) + '%' }" />
          </div>
          <p class="text-[10px] text-slate-400 mt-0.5">
            Downtime: <span :class="downtimeConfig(r.downtime_days).text">{{ r.downtime_days }} ngày</span>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
