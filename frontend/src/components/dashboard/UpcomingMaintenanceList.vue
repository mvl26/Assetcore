<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { UpcomingItem } from '@/stores/useDashboardStore'

defineProps<{ items: UpcomingItem[] }>()
const router = useRouter()

function dueBadgeClass(days: number | null): string {
  if (days == null) return 'bg-slate-100 text-slate-500'
  if (days < 0)  return 'bg-red-100 text-red-700 border border-red-200'
  if (days <= 3) return 'bg-orange-100 text-orange-700 border border-orange-200'
  if (days <= 7) return 'bg-amber-50 text-amber-700 border border-amber-200'
  return 'bg-emerald-50 text-emerald-700 border border-emerald-200'
}

function dueText(days: number | null): string {
  if (days == null) return '—'
  if (days < 0)  return `Quá hạn ${Math.abs(days)} ngày`
  if (days === 0) return 'Hôm nay'
  return `Còn ${days} ngày`
}

function createWorkOrder(item: UpcomingItem) {
  if (item.kind === 'PM') {
    router.push({ path: '/pm/work-orders/new', query: { asset: item.asset } })
  } else {
    router.push({ path: '/calibration/new', query: { asset: item.asset } })
  }
}
</script>

<template>
  <div class="card p-0 overflow-hidden">
    <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100">
      <div class="flex items-center gap-2">
        <svg class="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 class="text-sm font-semibold text-slate-800">
          Cảnh báo hạn bảo trì / hiệu chuẩn
        </h3>
        <span class="text-xs text-slate-400">(30 ngày tới · {{ items.length }})</span>
      </div>
      <button class="text-xs font-medium text-brand-600 hover:text-brand-800"
              @click="router.push('/pm/schedules')">Xem lịch đầy đủ →</button>
    </div>

    <div v-if="items.length === 0" class="px-5 py-10 text-center text-sm text-slate-400 italic">
      Không có lịch bảo trì/hiệu chuẩn sắp đến
    </div>

    <table v-else class="w-full text-sm">
      <thead class="bg-slate-50/80">
        <tr class="text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
          <th class="px-5 py-2.5">Thiết bị</th>
          <th class="px-3 py-2.5 hidden md:table-cell">Khoa</th>
          <th class="px-3 py-2.5">Loại</th>
          <th class="px-3 py-2.5">Hạn</th>
          <th class="px-3 py-2.5 text-right">Còn lại</th>
          <th class="px-5 py-2.5 text-right">Hành động</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100">
        <tr v-for="(it, i) in items" :key="`${it.asset}-${i}`" class="hover:bg-slate-50 transition-colors">
          <td class="px-5 py-3">
            <button class="font-medium text-slate-800 hover:text-brand-700 truncate max-w-[260px] text-left"
                    @click="router.push(`/assets/${it.asset}`)">
              {{ it.asset_name || it.asset }}
            </button>
            <p class="text-[11px] text-slate-400 font-mono">{{ it.asset }}</p>
          </td>
          <td class="px-3 py-3 text-slate-600 hidden md:table-cell">{{ it.department || '—' }}</td>
          <td class="px-3 py-3">
            <span class="inline-block px-2 py-0.5 rounded-md text-[11px] font-medium"
                  :class="it.kind === 'PM'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'bg-purple-50 text-purple-700 border border-purple-200'">
              {{ it.kind === 'PM' ? `PM ${it.detail || ''}`.trim() : `Hiệu chuẩn ${it.detail || ''}`.trim() }}
            </span>
          </td>
          <td class="px-3 py-3 text-slate-600 font-mono text-xs">{{ it.due_date }}</td>
          <td class="px-3 py-3 text-right">
            <span class="inline-block px-2 py-0.5 rounded-md text-[11px] font-semibold"
                  :class="dueBadgeClass(it.days_until)">
              {{ dueText(it.days_until) }}
            </span>
          </td>
          <td class="px-5 py-3 text-right">
            <button class="text-[11px] font-medium text-brand-600 hover:text-brand-800 hover:underline"
                    @click="createWorkOrder(it)">
              + Tạo phiếu
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
