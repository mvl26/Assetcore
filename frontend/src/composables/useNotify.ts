// Copyright (c) 2026, AssetCore Team
// useNotify — entrypoint duy nhất cho FE hiển thị thông báo chuẩn hoá.
//
// API:
//   const notify = useNotify()
//   notify.show({ code: MSG.IMM04_SUBMIT_SUCCESS, ctx: { name: 'AC-001' } })
//   notify.fromError(apiError)                  // map ApiError → toast/modal
//   notify.fromOk(response)                     // pickup `data.notify` từ BE _ok envelope
//   await notify.confirm({ title, body, confirmText })
//
// Severity routing:
//   'success' | 'info' | 'warning' | 'error'  → toast (non-blocking)
//   'critical'                                 → modal (blocking)
//
// Phase 2 (doctype-driven): chỉ cần thay `MESSAGES` import bằng pinia store —
// API composable không đổi.
import { ApiError, type Severity } from '@/api/errors'
import { MESSAGES, MSG } from '@/i18n/messages'
import { useModal } from './useModal'
import { useToast } from './useToast'

interface ShowOpts {
  code: string
  ctx?: Record<string, unknown>
  /** Override severity từ registry (rare — vd: success message muốn force warning). */
  severity?: Severity
  /** Duration ms cho toast — modal bỏ qua. */
  duration?: number
}

interface ConfirmOpts {
  code?: string
  ctx?: Record<string, unknown>
  /** Override / standalone — khi không dùng code. */
  title?: string
  body?: string
  actionHint?: string
  confirmText?: string
  cancelText?: string
}

/** Render template + entry từ registry. Fallback SYS-500 nếu code không tồn tại. */
function render(code: string, ctx: Record<string, unknown> = {}) {
  const entry = MESSAGES[code] ?? MESSAGES[MSG.SYS_500]
  const message = entry.template.replace(/\{(\w+)\}/g, (_, k: string) =>
    String(ctx[k] ?? `[${k}]`),
  )
  return { ...entry, message }
}

/** Map severity → toast type. 'critical' → 'error' (modal đã route trước). */
function severityToToastType(s: Severity): 'success' | 'error' | 'warning' | 'info' {
  if (s === 'critical') return 'error'
  return s
}

export function useNotify() {
  const toast = useToast()
  const modal = useModal()

  function show(opts: ShowOpts) {
    const r = render(opts.code, opts.ctx)
    const severity = opts.severity ?? r.severity

    if (severity === 'critical') {
      // Critical → modal blocking. Không await — caller không cần biết.
      void modal.alert({
        title: r.title,
        body: r.message,
        actionHint: r.action_hint || undefined,
        tone: 'critical',
      })
      return
    }
    toast.show(
      r.message,
      severityToToastType(severity),
      opts.duration ?? 4000,
      { title: r.title, actionHint: r.action_hint || undefined },
    )
  }

  function fromError(e: unknown) {
    // ApiError với messageCode → render từ registry với context BE gửi
    if (e instanceof ApiError && e.messageCode) {
      show({ code: e.messageCode, ctx: e.context })
      return
    }
    // ApiError không có messageCode → fallback message tự nhiên + severity-aware
    if (e instanceof ApiError) {
      const severity: Severity = e.severity
        ?? (e.isSystemError ? 'error' : e.isBusinessError ? 'warning' : 'error')
      if (severity === 'critical') {
        void modal.alert({
          title: e.title ?? 'Lỗi',
          body: e.message,
          actionHint: e.actionHint,
          tone: 'critical',
        })
        return
      }
      toast.show(
        e.message,
        severityToToastType(severity),
        4000,
        { title: e.title, actionHint: e.actionHint },
      )
      return
    }
    // Generic Error / unknown — fallback SYS-500 framing
    const msg = e instanceof Error ? e.message : String(e)
    if (!msg) return
    toast.error(msg)
  }

  /**
   * Pickup `data.notify` từ BE _ok envelope (hybrid pattern — xem Open Q4 trong
   * plan Phase 1). BE có thể trả `_ok({...payload, notify: {code, context}})`
   * khi muốn ép FE hiển thị message cụ thể.
   */
  function fromOk(resp: unknown) {
    if (!resp || typeof resp !== 'object') return
    const notify = (resp as { notify?: { code: string; context?: Record<string, unknown> } }).notify
    if (notify?.code) show({ code: notify.code, ctx: notify.context })
  }

  async function confirm(opts: ConfirmOpts): Promise<boolean> {
    let title = opts.title
    let body = opts.body
    let actionHint = opts.actionHint
    if (opts.code) {
      const r = render(opts.code, opts.ctx)
      title ??= r.title
      body ??= r.message
      actionHint ??= r.action_hint || undefined
    }
    return modal.confirm({
      title: title ?? 'Xác nhận',
      body: body ?? '',
      actionHint,
      confirmText: opts.confirmText,
      cancelText: opts.cancelText,
    })
  }

  return { show, fromError, fromOk, confirm }
}
