<script setup lang="ts">
// NotificationModal — bản RENDER của hàng đợi `useModal()`. Mount 1 lần ở `App.vue`
// song song `ToastContainer`. Hiển thị ĐÚNG phần tử đầu hàng đợi (FIFO).
//
// AC-UX-064 (docs/ui-ux/04 §1.2): render QUA `BaseModal.vue` — SSoT hộp thoại. Trước
// đây file này TỰ VẼ overlay (lớp phủ toàn màn hình z-[10000] + card riêng) nên mọi hộp
// thoại xác nhận của ứng dụng đứng NGOÀI hợp đồng a11y vòng 5: không `aria-labelledby`, không
// bẫy focus, không trả focus về nơi mở. Vì `useModal()` là SSoT thay thế `confirm()`
// trần, mỗi lần di trú thêm một call-site là lỗ đó rộng thêm ⇒ vá SSoT trước, di trú sau.
//
// KHÔNG đăng ký `keydown` ở đây: `BaseModal` → `useFocusTrap` đã sở hữu phím Escape.
// Hai chủ sở hữu = 1 lần nhấn ESC gọi `resolve` HAI lần. Bẫy này promise không lộ ra
// (JS nuốt lần settle thứ hai) — chỉ spy đếm mới thấy (TC-UX064-2).
//
// Hợp đồng đối ngoại của `useModal()` GIỮ NGUYÊN TUYỆT ĐỐI: alert/confirm/dismiss/queue,
// `tone`, `confirmText`/`cancelText`, `actionHint` — 0 dòng sửa ở phía gọi.
import { computed } from 'vue'
import { useModal, type ModalRequest } from '@/composables/useModal'
import BaseModal from './BaseModal.vue'

const { queue, dismiss } = useModal()

const current = computed<ModalRequest | undefined>(() => queue.value[0])

// Dải màu + biểu tượng theo `tone` — GIỮ NGUYÊN bảng cũ. Nay nằm TRONG thân bài của
// BaseModal (không fork lại card), nên hộp thoại vẫn đọc được sắc thái ngay từ cái nhìn
// đầu tiên mà không cần dựng lại khung.
const TONE_CFG: Record<NonNullable<ModalRequest['tone']>, { bar: string; icon: string; emoji: string }> = {
  error:    { bar: 'bg-red-500',    icon: 'text-red-600',    emoji: '✕' },
  warning:  { bar: 'bg-amber-500',  icon: 'text-amber-600',  emoji: '!' },
  info:     { bar: 'bg-blue-500',   icon: 'text-blue-600',   emoji: 'i' },
  critical: { bar: 'bg-red-600',    icon: 'text-red-700',    emoji: '⚠' },
}

function cfg(req: ModalRequest) {
  return TONE_CFG[req.tone ?? 'critical']
}

/** Hành động phá huỷ / chặn ⇒ bật `danger` của BaseModal (tiêu đề + viền đỏ). */
const isDanger = computed(() => {
  const tone = current.value?.tone
  return tone === 'error' || tone === 'critical'
})

function onConfirm() {
  if (current.value) dismiss(current.value.id, true)
}

// Mọi đường HUỶ (nút «Huỷ» · nút đóng · click nền · Escape) hội tụ ở đây:
// confirm → resolve(false); alert → resolve(void). `ok=false` đúng cho cả hai.
function onCancel() {
  if (current.value) dismiss(current.value.id, false)
}
</script>

<template>
  <!-- `:key` theo id request: mỗi hộp thoại là một instance BaseModal MỚI ⇒ bẫy focus
       kích hoạt lại và `aria-labelledby` sinh id riêng khi hàng đợi nhảy sang mục kế. -->
  <BaseModal
    v-if="current"
    :key="current.id"
    :title="current.title"
    :danger="isDanger"
    size="md"
    layer="system"
    @close="onCancel"
  >
    <!-- Dải màu theo `tone` — GIỮ NGUYÊN vị trí cũ (vắt ngang đầu thân bài). `-mx-6 -mt-5`
         bù đúng `px-6 py-5` của thân BaseModal để dải chạm hai mép card như trước khi
         hợp nhất; đặt trong slot nên KHÔNG phải fork lại card. -->
    <div :class="['-mx-6 -mt-5 mb-5 h-1', cfg(current).bar]" aria-hidden="true" />
    <div class="flex items-start gap-4">
      <span
        :class="['shrink-0 inline-flex items-center justify-center w-10 h-10 rounded-full text-lg font-bold ring-2 ring-current/20 bg-current/5', cfg(current).icon]"
        aria-hidden="true"
      >{{ cfg(current).emoji }}</span>
      <div class="flex-1 min-w-0">
        <p data-testid="modal-message" class="text-sm text-slate-700 whitespace-pre-line">{{ current.body }}</p>
        <p
          v-if="current.actionHint"
          class="mt-2 text-xs text-slate-500 italic"
        >
          {{ current.actionHint }}
        </p>
      </div>
    </div>

    <template #footer>
      <button
        v-if="current.kind === 'confirm'"
        data-testid="modal-cancel"
        type="button"
        class="px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-emerald-500"
        @click="onCancel"
      >
        {{ current.cancelText }}
      </button>
      <button
        data-testid="modal-confirm"
        type="button"
        :class="[
          'px-3 py-1.5 text-sm font-semibold text-white rounded-md focus-visible:ring-2 focus-visible:ring-offset-1',
          isDanger ? 'bg-red-600 hover:bg-red-700 focus-visible:ring-red-500' : 'bg-blue-600 hover:bg-blue-700 focus-visible:ring-blue-500',
        ]"
        @click="onConfirm"
      >
        {{ current.kind === 'confirm' ? current.confirmText : 'Đã hiểu' }}
      </button>
    </template>
  </BaseModal>
</template>
