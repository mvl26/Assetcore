<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Hiển thị "Tên chính" + "Mã phụ" theo chuẩn UX y tế.
// Dùng trong table row, dropdown option, detail card.

defineProps<{
  /** Tên chính — hiển thị nổi bật */
  label: string
  /** Mã định danh phụ (UDI, GMDN, mã kho, serial…) */
  code?: string | null
  /** Gợi ý thêm (VD: "Class II", tên nhà sản xuất) */
  hint?: string | null
  /** Hiển thị inline thay vì stack dọc */
  inline?: boolean
}>()
</script>

<template>
  <span :class="inline ? 'inline-flex items-baseline gap-1.5' : 'flex flex-col gap-0.5'">
    <span class="text-gray-900 font-medium leading-snug">{{ label }}</span>
    <span v-if="code || hint" class="inline-flex items-center gap-1.5">
      <span v-if="code" class="text-xs text-gray-400 font-mono leading-none">{{ code }}</span>
      <span v-if="code && hint" class="text-gray-300 text-xs leading-none">·</span>
      <span v-if="hint" class="text-xs text-gray-400 leading-none">{{ hint }}</span>
    </span>
  </span>
</template>
