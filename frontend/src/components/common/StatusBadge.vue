<script setup lang="ts">
import { computed } from 'vue'
import type { WorkflowState } from '@/types/imm04'

const props = defineProps<{
  state: WorkflowState | string
  size?: 'xs' | 'sm' | 'md'
}>()

interface BadgeConfig {
  label:   string
  dot:     string
  bg:      string
  text:    string
  pulse:   boolean
}

const STATE_MAP: Record<string, BadgeConfig> = {
  // IMM-04 commissioning
  Draft:             { label: 'Nháp',              dot: '#94a3b8', bg: '#f8fafc', text: '#475569', pulse: false },
  Draft_Reception:   { label: 'Nháp',              dot: '#94a3b8', bg: '#f8fafc', text: '#475569', pulse: false },
  Pending_Doc_Verify:{ label: 'Chờ kiểm tra tài liệu', dot: '#a78bfa', bg: '#f5f3ff', text: '#6d28d9', pulse: false },
  To_Be_Installed:   { label: 'Chờ lắp đặt',       dot: '#60a5fa', bg: '#eff6ff', text: '#1d4ed8', pulse: false },
  Installing:        { label: 'Đang lắp đặt',       dot: '#f59e0b', bg: '#fffbeb', text: '#b45309', pulse: true },
  Identification:    { label: 'Nhận dạng',          dot: '#34d399', bg: '#ecfdf5', text: '#065f46', pulse: false },
  Initial_Inspection:{ label: 'Kiểm tra ban đầu',  dot: '#38bdf8', bg: '#f0f9ff', text: '#0369a1', pulse: false },
  Clinical_Hold:     { label: 'Tạm giữ lâm sàng',   dot: '#f87171', bg: '#fff1f2', text: '#b91c1c', pulse: true },
  Clinical_Release:  { label: 'Phát hành',          dot: '#10b981', bg: '#ecfdf5', text: '#065f46', pulse: false },
  Return_To_Vendor:  { label: 'Trả nhà cung cấp',  dot: '#fb923c', bg: '#fff7ed', text: '#9a3412', pulse: false },
  Re_Inspection:     { label: 'Kiểm tra lại',       dot: '#facc15', bg: '#fefce8', text: '#854d0e', pulse: false },
  Pending_Release:   { label: 'Chờ phê duyệt',      dot: '#818cf8', bg: '#eef2ff', text: '#3730a3', pulse: false },
  // IMM-05 documents
  Active:            { label: 'Hiệu lực',           dot: '#10b981', bg: '#ecfdf5', text: '#065f46', pulse: false },
  Expired:           { label: 'Hết hạn',            dot: '#f87171', bg: '#fff1f2', text: '#991b1b', pulse: false },
  Archived:          { label: 'Lưu trữ',            dot: '#94a3b8', bg: '#f8fafc', text: '#475569', pulse: false },
  Pending_Review:    { label: 'Chờ duyệt',          dot: '#a78bfa', bg: '#f5f3ff', text: '#6d28d9', pulse: false },
  Rejected:          { label: 'Từ chối',            dot: '#f43f5e', bg: '#fff1f2', text: '#9f1239', pulse: false },
  // IMM-08 PM
  On_Schedule:       { label: 'Đúng tiến độ',       dot: '#10b981', bg: '#ecfdf5', text: '#065f46', pulse: false },
  Due_Soon:          { label: 'Sắp đến hạn',        dot: '#f59e0b', bg: '#fffbeb', text: '#b45309', pulse: true },
  Overdue:           { label: 'Quá hạn',            dot: '#ef4444', bg: '#fff1f2', text: '#b91c1c', pulse: true },
  In_Progress:       { label: 'Đang thực hiện',     dot: '#3b82f6', bg: '#eff6ff', text: '#1d4ed8', pulse: true },
  Completed:         { label: 'Hoàn thành',         dot: '#10b981', bg: '#ecfdf5', text: '#065f46', pulse: false },
  // IMM-09 CM repairs
  Open:              { label: 'Mở mới',             dot: '#60a5fa', bg: '#eff6ff', text: '#1e40af', pulse: false },
  Assigned:          { label: 'Đã phân công',       dot: '#818cf8', bg: '#eef2ff', text: '#3730a3', pulse: false },
  Diagnosing:        { label: 'Đang chẩn đoán',     dot: '#f59e0b', bg: '#fffbeb', text: '#b45309', pulse: true },
  Pending_Parts:     { label: 'Chờ linh kiện',      dot: '#fb923c', bg: '#fff7ed', text: '#9a3412', pulse: false },
  In_Repair:         { label: 'Đang sửa chữa',      dot: '#a78bfa', bg: '#f5f3ff', text: '#6d28d9', pulse: true },
  Pending_Inspection:{ label: 'Chờ kiểm tra',       dot: '#38bdf8', bg: '#f0f9ff', text: '#0369a1', pulse: false },
  Cannot_Repair:     { label: 'Không sửa được',     dot: '#f43f5e', bg: '#fff1f2', text: '#9f1239', pulse: false },
}

const FALLBACK: BadgeConfig = { label: '', dot: '#94a3b8', bg: '#f8fafc', text: '#475569', pulse: false }

const cfg = computed<BadgeConfig>(() => {
  const key = props.state?.toString() ?? ''
  return STATE_MAP[key] ?? { ...FALLBACK, label: key.replaceAll('_', ' ') }
})

const sizeClass = computed(() => {
  switch (props.size) {
    case 'xs': return 'px-1.5 py-0.5 text-[10px] gap-1'
    case 'md': return 'px-3 py-1 text-xs gap-1.5'
    default:   return 'px-2.5 py-0.5 text-[11px] gap-1.5'
  }
})
</script>

<template>
  <span
    class="inline-flex items-center font-medium rounded-full leading-none whitespace-nowrap"
    :class="sizeClass"
    :style="`background: ${cfg.bg}; color: ${cfg.text};`"
  >
    <span
      class="rounded-full shrink-0"
      :class="[cfg.pulse ? 'animate-pulse-subtle' : '', size === 'xs' ? 'w-1 h-1' : 'w-1.5 h-1.5']"
      :style="`background: ${cfg.dot};`"
    />
    {{ cfg.label }}
  </span>
</template>
