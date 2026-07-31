<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Thanh tab dùng chung cho MỌI màn chi tiết (AC-CR-87 vòng 3).
//
// Thuần hiển thị + CONTROLLED: component KHÔNG giữ state, chỉ emit `update:modelValue`.
// Cha quyết định tab nào đang mở ⇒ cha cũng là nơi duy nhất quyết định panel nào mount
// (nhờ vậy panel «Bản ghi liên quan» mới mount LƯỜI được — 0 request trước khi mở tab).
//
// Hợp đồng khoá bằng test (`DetailTabBar.test.ts`):
//   • a11y WCAG 2.1 AA — role="tablist"/"tab" + aria-selected + type="button" + focus ring;
//   • cuộn ngang mobile — container `overflow-x-auto`, nút `shrink-0 whitespace-nowrap`
//     (giữ nguyên hợp đồng TC-RWD-07 vốn chỉ áp cho tab bar màn thiết bị).
export interface DetailTab {
  /** Khoá tab — cũng là `data-testid` (`tab-<key>`) để test bấm đúng tab. */
  key: string
  /** Nhãn hiển thị — LUÔN tiếng Việt đầy đủ (LL-FE-53). */
  label: string
}

defineProps<{ tabs: DetailTab[]; modelValue: string }>()
defineEmits<{ (e: 'update:modelValue', value: string): void }>()
</script>

<template>
  <div role="tablist" class="flex gap-1 mb-4 border-b border-slate-200 overflow-x-auto">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      type="button"
      role="tab"
      :aria-selected="modelValue === tab.key ? 'true' : 'false'"
      :data-testid="`tab-${tab.key}`"
      class="shrink-0 whitespace-nowrap px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      :class="modelValue === tab.key
        ? 'text-blue-600 border-b-2 border-blue-600 -mb-px'
        : 'text-slate-500 hover:text-slate-800'"
      @click="$emit('update:modelValue', tab.key)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
