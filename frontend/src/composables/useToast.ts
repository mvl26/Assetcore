// Copyright (c) 2026, AssetCore Team
// Toast container — non-blocking, auto-dismiss.
//
// Phase 1 notification framework: ToastType ≡ Severity (sans 'critical' — critical
// được route sang modal). Composable `useNotify` wrap useToast và bổ sung lookup
// MSG.XXX → render template → show(...).
import { ref } from 'vue'

/**
 * ToastType khớp với `Severity` ngoại trừ `'critical'` (critical → modal).
 * Đồng bộ với `frontend/src/locales/messageTypes.ts:Severity`.
 */
export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: number
  type: ToastType
  message: string
  duration: number
  /** Tiêu đề ngắn — optional, render nổi bật phía trên message khi có. */
  title?: string
  /** Gợi ý hành động — optional, render nhỏ phía dưới message. */
  actionHint?: string
}

const toasts = ref<Toast[]>([])
let _id = 0

export function useToast() {
  function show(
    message: string,
    type: ToastType = 'info',
    duration = 4000,
    opts: { title?: string; actionHint?: string } = {},
  ) {
    const id = ++_id
    toasts.value.push({
      id,
      type,
      message,
      duration,
      title: opts.title,
      actionHint: opts.actionHint,
    })
    setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, duration)
  }

  const success = (msg: string) => show(msg, 'success')
  const error = (msg: string) => show(msg, 'error')
  const warning = (msg: string) => show(msg, 'warning')
  const info = (msg: string) => show(msg, 'info')

  function dismiss(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return { toasts, show, success, error, warning, info, dismiss }
}
