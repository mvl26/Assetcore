<script setup lang="ts">
// Generic list/table card cho persona dashboards.
// Cột kiểu 'status'/'severity' render qua StatusBadge → KHÔNG leak raw code
// (WAVE2-RECURRING-BUGS anti-leak). Cột 'link' hiển thị mã + tooltip.
// Core Doc §9.7: row-drill — rowTo(row) trả RouterLocation | null → dòng click
// mở detail record nguồn (RouterLink ở cột đầu + cả <tr> điều hướng programmatic).
import { useRouter, type RouteLocationRaw } from 'vue-router'
import StatusBadge from '@/components/common/StatusBadge.vue'

export interface ListColumn {
  /** field key trong row */
  key: string
  /** nhãn cột (VI) */
  label: string
  /** kiểu render: text (default) | status | severity | link | date */
  type?: 'text' | 'status' | 'severity' | 'link' | 'date'
  /** field _name companion (nếu Link) — ưu tiên hiển thị tên đọc được */
  nameKey?: string
}

const props = defineProps<{
  title: string
  columns: ListColumn[]
  rows: Record<string, unknown>[]
  emptyText?: string
  /** §9.7 — mỗi dòng → route detail record (hoặc null = tĩnh). */
  rowTo?: (row: Record<string, unknown>) => RouteLocationRaw | null
}>()

const router = useRouter()

function asStr(v: unknown): string {
  return v === null || v === undefined ? '' : String(v)
}
function target(r: Record<string, unknown>): RouteLocationRaw | null {
  return props.rowTo ? props.rowTo(r) : null
}
function goRow(r: Record<string, unknown>): void {
  const to = target(r)
  if (to) router.push(to)
}
</script>

<template>
  <div class="rounded-xl border border-neutral-200 bg-white">
    <div class="flex items-center justify-between border-b border-neutral-100 px-4 py-3">
      <h3 class="text-sm font-semibold text-neutral-800">{{ title }}</h3>
      <span class="text-xs text-neutral-400">{{ rows.length }}</span>
    </div>
    <div class="p-2">
      <!-- P3 — bọc overflow-x-auto: KHÔNG tràn viewport mobile khi nhúng nhiều card. -->
      <div v-if="rows.length" class="overflow-x-auto">
        <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-neutral-400">
            <th v-for="c in columns" :key="c.key" class="px-2 py-1.5 font-medium">{{ c.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, i) in rows"
            :key="i"
            class="border-t border-neutral-50 transition"
            :class="target(row) ? 'cursor-pointer hover:bg-blue-50/50' : ''"
            @click="goRow(row)"
          >
            <td v-for="(c, ci) in columns" :key="c.key" class="px-2 py-2 align-middle">
              <!-- status / severity → StatusBadge (single source of truth) -->
              <StatusBadge
                v-if="(c.type === 'status' || c.type === 'severity') && asStr(row[c.key])"
                :state="asStr(row[c.key])"
                size="xs"
              />
              <!-- link → tên đọc được + mã làm tooltip (LL-FE-6) -->
              <span
                v-else-if="c.type === 'link'"
                class="font-mono text-xs text-neutral-700"
                :title="asStr(row[c.key])"
              >{{ (c.nameKey && row[c.nameKey]) ? asStr(row[c.nameKey]) : asStr(row[c.key]) || '—' }}</span>
              <!-- §9.7: cột ĐẦU + có rowTo → RouterLink (affordance + accessibility) -->
              <RouterLink
                v-else-if="ci === 0 && target(row)"
                :to="target(row)!"
                class="font-medium text-blue-700 hover:underline"
                @click.stop
              >{{ (c.nameKey && row[c.nameKey]) ? asStr(row[c.nameKey]) : asStr(row[c.key]) || '—' }}</RouterLink>
              <!-- text/date -->
              <span v-else class="text-neutral-700">
                {{ (c.nameKey && row[c.nameKey]) ? asStr(row[c.nameKey]) : asStr(row[c.key]) || '—' }}
              </span>
            </td>
          </tr>
        </tbody>
        </table>
      </div>
      <p v-else class="px-3 py-6 text-center text-sm text-neutral-400">
        {{ emptyText ?? 'Không có dữ liệu' }}
      </p>
    </div>
  </div>
</template>
