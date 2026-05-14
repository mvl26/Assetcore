<script setup lang="ts">
/**
 * Hiển thị thông tin chi tiết của bản ghi đã liên kết.
 * Dùng dưới LinkSearch để cho user thấy ngay context của lựa chọn.
 */
defineProps<{
  title?: string
  fields: Array<{ label: string; value: string | number | null | undefined; type?: 'text' | 'badge' | 'mono' | 'currency' }>
  variant?: 'info' | 'success' | 'warning'
}>()

const variantClass: Record<string, string> = {
  info:    'border-blue-200 bg-blue-50/40',
  success: 'border-green-200 bg-green-50/40',
  warning: 'border-amber-200 bg-amber-50/40',
}

function fmt(v: string | number | null | undefined, type?: string): string {
  if (v === null || v === undefined || v === '') return '—'
  if (type === 'currency' && typeof v === 'number') return `${v.toLocaleString('vi-VN')} ₫`
  return String(v)
}
</script>

<template>
  <div
    class="mt-2 px-3 py-2.5 border rounded-lg text-xs animate-fade-in"
    :class="variantClass[variant ?? 'info']"
  >
    <p v-if="title" class="font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
      <svg class="w-3.5 h-3.5 text-brand-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {{ title }}
    </p>
    <dl class="grid grid-cols-2 gap-x-3 gap-y-1">
      <template v-for="f in fields" :key="f.label">
        <dt class="text-slate-500">{{ f.label }}:</dt>
        <dd
          class="text-slate-800 truncate"
          :class="{
            'font-mono text-[11px]': f.type === 'mono',
            'inline-flex items-center px-1.5 py-0.5 rounded bg-white border border-slate-200 text-[10px] font-medium w-fit': f.type === 'badge',
            'font-semibold': f.type === 'currency',
          }"
        >
          {{ fmt(f.value, f.type) }}
        </dd>
      </template>
    </dl>
  </div>
</template>
