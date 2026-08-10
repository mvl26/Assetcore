<script setup lang="ts">
// SSoT hộp thoại (docs/ui-ux/04 §3). Hợp đồng đối ngoại GIỮ NGUYÊN TUYỆT ĐỐI —
// prop title/size/danger · slot mặc định + footer · emit close · data-testid modal-card/
// modal-close · toàn bộ chuỗi class — để 19 màn tiêu thụ thừa hưởng a11y với 0 dòng sửa.
// Chỉ THÊM: ngữ nghĩa dialog (role/aria-modal/aria-labelledby) + bẫy focus qua useFocusTrap.
import { ref, onMounted } from 'vue'
import { useFocusTrap, tabbablesIn, nextDialogId } from '@/composables/useFocusTrap'
import ModalInlineError from './ModalInlineError.vue'

defineProps<{
  title: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  danger?: boolean
  // AC-UX-062 (docs/ui-ux/05 §2.2) — CHỈ THÊM, tuỳ chọn: lỗi CHẶN hành động hiện
  // inline ở đầu thân bài, KHÔNG tự tắt, hộp thoại KHÔNG đóng. Bỏ trống ⇒ 15 màn
  // chưa áp giữ nguyên hành vi cũ (0 node thêm).
  error?: string | null
  errorTitle?: string
  // AC-UX-064 / ADR-UX-17 (docs/ui-ux/06 §3.5) — CHỈ THÊM, tuỳ chọn: tầng xếp chồng.
  // Hộp thoại HỆ THỐNG (lỗi chặn, xác nhận phá huỷ — `NotificationModal`) phải nằm TRÊN
  // hộp thoại NGHIỆP VỤ của màn; nếu cùng `z-50` thì thứ tự vẽ chỉ còn phụ thuộc thứ tự
  // `Teleport` chèn vào `<body>` — tức là ngẫu nhiên.
  // Bỏ trống ⇒ `'default'` ⇒ class y hệt hôm nay ⇒ 19 file tiêu thụ đổi 0 dòng.
  layer?: 'default' | 'system'
}>()

const emit = defineEmits<{ close: [] }>()

function onClose() { emit('close') }

const cardEl = ref<HTMLElement | null>(null)
// Id theo INSTANCE — 2 hộp thoại mở đồng thời KHÔNG được trùng `aria-labelledby`.
const titleId = nextDialogId('ac-modal-title')

// Thứ tự chọn focus ban đầu — KHÔNG chọn nút đóng nếu còn lựa chọn khác: nút đóng nằm
// ĐẦU DOM, focus vào đó rồi gõ Enter theo phản xạ = đóng nhầm hộp thoại.
function firstFocusTarget(): HTMLElement | null {
  const root = cardEl.value
  if (!root) return null
  const auto = root.querySelector<HTMLElement>('[data-autofocus]')
  if (auto) return auto
  const closeBtn = root.querySelector<HTMLElement>('[data-testid="modal-close"]')
  const rest = tabbablesIn(root).filter((el) => el !== closeBtn)
  return rest[0] ?? closeBtn ?? root
}

// ESC do composable lo (listener trên document, gỡ ở onBeforeUnmount) — KHÔNG thêm
// `@keydown.esc` trên card "cho chắc": 2 handler = emit `close` 2 lần.
const trap = useFocusTrap({ container: cardEl, onEscape: onClose, initialFocus: firstFocusTarget })

onMounted(() => { void trap.activate() })

function onKeydown(e: KeyboardEvent): void { trap.handleTabKey(e) }

// BẪY Tailwind JIT: hai chuỗi z-index phải là LITERAL trong file này. Ghép động
// (`z-[${n}]`) ⇒ JIT không quét ra tên class ⇒ overlay mất z-index một cách câm lặng.
const layerClass: Record<string, string> = {
  default: 'z-50',
  system: 'z-[10000]',
}

// Size cap chỉ áp ở sm:+ (mobile full-screen w-full không bị max-w giới hạn — D3).
const sizeClass: Record<string, string> = {
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-md',
  lg: 'sm:max-w-lg',
  xl: 'sm:max-w-2xl',
}
</script>

<template>
  <Teleport to="body">
    <!-- Overlay. Mobile: stretch (modal full-screen); sm:+ : centered card (ADR-IMM00-RESPONSIVE D3). -->
    <div
      :class="[
        'fixed inset-0 flex items-stretch justify-center sm:items-center sm:justify-center sm:p-4',
        layerClass[layer ?? 'default'],
      ]"
      style="background: rgba(0,0,0,0.45)"
      @click.self="onClose"
    >
      <div
        ref="cardEl"
        data-testid="modal-card"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        tabindex="-1"
        :class="[
          'bg-white shadow-2xl flex flex-col',
          // Mobile (base): full-screen — inset-0 w-full h-full rounded-none, không tràn.
          'inset-0 w-full h-full rounded-none max-h-screen',
          // sm:+ : centered card (giữ pattern desktop hiện hữu).
          'sm:inset-auto sm:m-auto sm:w-full sm:rounded-2xl sm:h-auto sm:max-h-[90vh]',
          sizeClass[size ?? 'md'],
        ]"
        @keydown="onKeydown"
      >
        <!-- Header -->
        <div
          class="flex items-center justify-between px-6 py-4 shrink-0"
          :class="danger ? 'border-b border-red-100' : 'border-b border-slate-100'"
        >
          <h2
            :id="titleId"
            class="text-lg font-semibold"
            :class="danger ? 'text-red-700' : 'text-slate-800'"
          >
            {{ title }}
          </h2>
          <button
            data-testid="modal-close"
            aria-label="Đóng"
            class="min-h-[44px] min-w-[44px] -mr-2 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            @click="onClose"
          >
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Body -->
        <div data-testid="modal-body" class="flex-1 overflow-y-auto px-6 py-5">
          <!-- Lỗi CHẶN hành động: ĐẦU thân bài, trước nội dung slot (AC-UX-062). -->
          <ModalInlineError v-if="error" :message="error" :title="errorTitle" />
          <slot />
        </div>

        <!-- Footer. ≤768px: xếp dọc, nút chính NẰM TRÊN (flex-col-reverse + DOM order
             phụ→chính); sm:+ giữ nguyên hàng ngang, phụ trái → chính phải. -->
        <div
          v-if="$slots.footer"
          data-testid="modal-footer"
          class="px-6 py-4 border-t border-slate-100 shrink-0 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end"
        >
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
