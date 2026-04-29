<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { UpcomingItem } from '@/stores/useDashboardStore'

const props = defineProps<{ items: UpcomingItem[] }>()
const router = useRouter()

function dueConfig(days: number | null) {
  if (days == null) return { badge: 'bg-slate-100 text-slate-500 border border-slate-200',             bar: 'bg-slate-300', label: '—',                       ring: 'ring-slate-200' }
  if (days < 0)    return { badge: 'bg-red-100 text-red-700 border border-red-200',                   bar: 'bg-red-500',   label: `Quá hạn ${Math.abs(days)}d`, ring: 'ring-red-200' }
  if (days === 0)  return { badge: 'bg-red-50 text-red-600 border border-red-200',                    bar: 'bg-red-400',   label: 'Hôm nay',                   ring: 'ring-red-100' }
  if (days <= 3)   return { badge: 'bg-orange-100 text-orange-700 border border-orange-200',          bar: 'bg-orange-400',label: `Còn ${days} ngày`,          ring: 'ring-orange-200' }
  if (days <= 7)   return { badge: 'bg-amber-50 text-amber-700 border border-amber-200',              bar: 'bg-amber-400', label: `Còn ${days} ngày`,          ring: 'ring-amber-100' }
  return                  { badge: 'bg-emerald-50 text-emerald-700 border border-emerald-200',        bar: 'bg-emerald-400',label: `Còn ${days} ngày`,         ring: 'ring-emerald-100' }
}

// Group thành 3 nhóm: overdue / urgent (≤7d) / upcoming
const grouped = computed(() => {
  const overdue  = props.items.filter(i => (i.days_until ?? 0) < 0)
  const urgent   = props.items.filter(i => i.days_until != null && i.days_until >= 0 && i.days_until <= 7)
  const upcoming = props.items.filter(i => i.days_until != null && i.days_until > 7)
  return { overdue, urgent, upcoming }
})

function kindConfig(kind: string) {
  return kind === 'PM'
    ? { cls: 'bg-blue-100 text-blue-700 border border-blue-200', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' }
    : { cls: 'bg-purple-100 text-purple-700 border border-purple-200', icon: 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z' }
}

function createWorkOrder(item: UpcomingItem) {
  if (item.kind === 'PM') router.push({ path: '/pm/work-orders/new', query: { asset: item.asset } })
  else                    router.push({ path: '/calibration/new',    query: { asset: item.asset } })
}
</script>

<template>
  <div class="card p-0 overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100">
      <div class="flex items-center gap-2">
        <svg class="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 class="text-sm font-semibold text-slate-800">Cảnh báo hạn bảo trì / hiệu chuẩn</h3>
        <span class="text-xs text-slate-400">(30 ngày tới · {{ items.length }})</span>
      </div>
      <button
class="text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
              @click="router.push('/pm/schedules')">
Xem lịch đầy đủ →
</button>
    </div>

    <!-- Empty -->
    <div
v-if="items.length === 0"
         class="px-5 py-10 text-center text-sm text-slate-400 italic">
      Không có lịch bảo trì/hiệu chuẩn sắp đến
    </div>

    <div v-else class="p-5 space-y-5">
<!-- Nhóm: Quá hạn -->
      <div v-if="grouped.overdue.length">
        <div class="flex items-center gap-2 mb-3">
          <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <p class="text-xs font-bold text-red-600 uppercase tracking-wide">Quá hạn ({{ grouped.overdue.length }})</p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          <div
v-for="(it, i) in grouped.overdue" :key="`ov-${i}`"
               class="group relative rounded-xl border border-red-200 bg-red-50/40 p-4 hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer ring-1 ring-red-100"
               @click="router.push(`/assets/${it.asset}`)">
            <div class="flex items-start justify-between gap-2 mb-2">
              <span :class="['text-[11px] px-1.5 py-0.5 rounded font-medium flex items-center gap-1', kindConfig(it.kind).cls]">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" :d="kindConfig(it.kind).icon" />
                </svg>
                {{ it.kind }} {{ it.detail || '' }}
              </span>
              <span :class="['text-[11px] px-2 py-0.5 rounded font-bold', dueConfig(it.days_until).badge]">
                {{ dueConfig(it.days_until).label }}
              </span>
            </div>
            <p class="font-semibold text-sm text-slate-800 truncate mb-0.5">{{ it.asset_name || it.asset }}</p>
            <p class="text-[11px] text-slate-400">
              {{ it.department_name || it.department || '' }}
              <span class="font-mono ml-1 opacity-60">· {{ it.due_date }}</span>
            </p>
            <button
              class="mt-3 w-full text-[11px] font-semibold py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-700 transition-colors"
              @click.stop="createWorkOrder(it)">
              + Tạo phiếu ngay
            </button>
          </div>
        </div>
      </div>

      <!-- Nhóm: Khẩn (≤7 ngày) -->
      <div v-if="grouped.urgent.length">
        <div class="flex items-center gap-2 mb-3">
          <span class="w-2 h-2 rounded-full bg-orange-400" />
          <p class="text-xs font-bold text-orange-600 uppercase tracking-wide">Sắp đến hạn — ≤ 7 ngày ({{ grouped.urgent.length }})</p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          <div
v-for="(it, i) in grouped.urgent" :key="`urg-${i}`"
               class="group relative rounded-xl border border-orange-200 bg-orange-50/40 p-4 hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer"
               @click="router.push(`/assets/${it.asset}`)">
            <div class="flex items-start justify-between gap-2 mb-2">
              <span :class="['text-[11px] px-1.5 py-0.5 rounded font-medium flex items-center gap-1', kindConfig(it.kind).cls]">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" :d="kindConfig(it.kind).icon" />
                </svg>
                {{ it.kind }} {{ it.detail || '' }}
              </span>
              <span :class="['text-[11px] px-2 py-0.5 rounded font-semibold', dueConfig(it.days_until).badge]">
                {{ dueConfig(it.days_until).label }}
              </span>
            </div>
            <p class="font-semibold text-sm text-slate-800 truncate mb-0.5">{{ it.asset_name || it.asset }}</p>
            <p class="text-[11px] text-slate-400">
              {{ it.department_name || it.department || '' }}
              <span class="font-mono ml-1 opacity-60">· {{ it.due_date }}</span>
            </p>
            <!-- urgency bar -->
            <div class="mt-2.5 h-1 bg-slate-100 rounded-full overflow-hidden">
              <div
class="h-full rounded-full bg-orange-400 transition-all"
                   :style="{ width: it.days_until != null ? Math.max(0, 100 - (it.days_until / 7) * 100) + '%' : '0%' }" />
            </div>
            <button
              class="mt-3 w-full text-[11px] font-semibold py-1.5 rounded-lg bg-orange-100 hover:bg-orange-200 text-orange-700 transition-colors"
              @click.stop="createWorkOrder(it)">
              + Tạo phiếu
            </button>
          </div>
        </div>
      </div>

      <!-- Nhóm: Sắp tới (> 7 ngày) -->
      <div v-if="grouped.upcoming.length">
        <div class="flex items-center gap-2 mb-3">
          <span class="w-2 h-2 rounded-full bg-emerald-400" />
          <p class="text-xs font-bold text-slate-500 uppercase tracking-wide">Sắp tới ({{ grouped.upcoming.length }})</p>
        </div>
        <div class="divide-y divide-slate-50 rounded-xl border border-slate-100 overflow-hidden">
          <div
v-for="(it, i) in grouped.upcoming" :key="`up-${i}`"
               class="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors cursor-pointer"
               @click="router.push(`/assets/${it.asset}`)">
            <!-- kind icon -->
            <div
:class="['w-7 h-7 rounded-lg flex items-center justify-center shrink-0',
                          it.kind === 'PM' ? 'bg-blue-50' : 'bg-purple-50']">
              <svg
class="w-3.5 h-3.5" :class="it.kind === 'PM' ? 'text-blue-600' : 'text-purple-600'"
                   fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" :d="kindConfig(it.kind).icon" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-slate-800 truncate">{{ it.asset_name || it.asset }}</p>
              <p class="text-[11px] text-slate-400">
                {{ it.department_name || it.department || '' }}
                <span class="font-mono ml-1 opacity-60">· {{ it.due_date }}</span>
              </p>
            </div>
            <span :class="['text-[11px] px-2 py-0.5 rounded font-medium shrink-0', dueConfig(it.days_until).badge]">
              {{ dueConfig(it.days_until).label }}
            </span>
            <button
class="shrink-0 text-[11px] font-medium text-blue-600 hover:underline"
                    @click.stop="createWorkOrder(it)">
+ Tạo
</button>
          </div>
        </div>
      </div>
</div>
  </div>
</template>
