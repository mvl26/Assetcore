// Copyright (c) 2026, AssetCore Team
// Modal composable — singleton queue cho `NotificationModal.vue` render.
//
// Dùng cho lỗi `severity: 'critical'` (compliance gate, mất dữ liệu): chặn
// thao tác, buộc user acknowledge trước khi tiếp tục.
//
// API:
//   const modal = useModal()
//   modal.alert({ title, body, actionHint })
//   const ok = await modal.confirm({ title, body, confirmText, cancelText })
import { ref } from 'vue'

export type ModalKind = 'alert' | 'confirm'

export interface ModalRequest {
  id: number
  kind: ModalKind
  title: string
  body: string
  actionHint?: string
  confirmText?: string
  cancelText?: string
  /** Tone-driven styling — same convention as toast for visual consistency. */
  tone?: 'error' | 'warning' | 'info' | 'critical'
  resolve: (ok: boolean) => void
}

const queue = ref<ModalRequest[]>([])
let _id = 0

export function useModal() {
  function alert(opts: { title: string; body: string; actionHint?: string;
                          tone?: ModalRequest['tone'] }): Promise<void> {
    return new Promise<void>((resolve) => {
      queue.value.push({
        id: ++_id,
        kind: 'alert',
        title: opts.title,
        body: opts.body,
        actionHint: opts.actionHint,
        tone: opts.tone ?? 'critical',
        resolve: () => resolve(),
      })
    })
  }

  function confirm(opts: {
    title: string
    body: string
    actionHint?: string
    confirmText?: string
    cancelText?: string
    tone?: ModalRequest['tone']
  }): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      queue.value.push({
        id: ++_id,
        kind: 'confirm',
        title: opts.title,
        body: opts.body,
        actionHint: opts.actionHint,
        confirmText: opts.confirmText ?? 'Xác nhận',
        cancelText: opts.cancelText ?? 'Huỷ',
        tone: opts.tone ?? 'warning',
        resolve,
      })
    })
  }

  function dismiss(id: number, ok: boolean) {
    const idx = queue.value.findIndex(m => m.id === id)
    if (idx < 0) return
    const req = queue.value[idx]
    queue.value.splice(idx, 1)
    req.resolve(ok)
  }

  return { queue, alert, confirm, dismiss }
}
