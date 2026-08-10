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
  /**
   * Số/chữ đếm phụ hiện NGAY TRONG nút tab (vd số phiếu không phù hợp còn mở).
   *
   * Thêm ở AC-UX-067 theo lối CHỈ-THÊM (ADR-UX-19): trước đó một nhu cầu nhỏ như
   * «Không phù hợp × 3» đủ để một màn giữ nguyên thanh tab tự chế — và bản fork ấy
   * mất sạch role/aria + không cuộn ngang được. Nay nó có chỗ đứng chính thức.
   *
   * KHÔNG render khi: undefined · null · '' · 0 · '0' (khớp `v-if="openNcCount > 0"` cũ).
   */
  badge?: string | number
}

defineProps<{ tabs: DetailTab[]; modelValue: string }>()
defineEmits<{ (e: 'update:modelValue', value: string): void }>()

/**
 * Badge rỗng ⇒ KHÔNG có phần tử trong DOM (không phải `display:none`): trình đọc màn
 * hình không đọc con số «0» vô nghĩa, và test đếm được phần tử.
 *
 * Cố ý KHÔNG dùng `v-if="tab.badge"`: chuỗi `'0'` là truthy ⇒ sẽ hiện badge «0».
 */
function hasBadge(badge?: string | number | null): boolean {
  if (badge === undefined || badge === null) return false
  const s = String(badge).trim()
  return s !== '' && s !== '0'
}
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
      <!-- Badge NẰM TRONG nút (B1): ngoài nút thì vùng bấm và vòng focus lệch nhau,
           và trình đọc màn hình đọc con số rời khỏi nhãn. Chỉ `<span>` — thêm
           button/a/tabindex ở đây là đẻ một tab-stop giữa dải tab (B2).
           Cố ý KHÔNG `aria-hidden`: con số là thông tin, không phải trang trí. -->
      <span
        v-if="hasBadge(tab.badge)"
        :data-testid="`tab-badge-${tab.key}`"
        class="ml-1.5 inline-flex items-center justify-center min-w-[1rem] h-4 px-1 rounded-full bg-red-500 text-white text-[10px] font-bold align-middle"
      >{{ tab.badge }}</span>
    </button>
  </div>
</template>
