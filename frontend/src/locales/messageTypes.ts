// AUTO-GENERATED from assetcore/utils/messages.py — DO NOT EDIT MANUALLY.
// To regenerate: `python scripts/gen_fe_messages.py`.
// Source of truth: assetcore/utils/messages.py (Python registry).

/** Severity — đồng bộ với `assetcore/utils/messages.py:Severity`. */
export type Severity = 'error' | 'warning' | 'info' | 'success' | 'critical'

/** Shape 1 entry trong MESSAGES — đồng bộ `MessageEntry` TypedDict ở BE. */
export interface MessageEntry {
  title: string
  template: string
  action_hint: string
  severity: Severity
  http_status: number
}

/** Union type cho mọi message code đã đăng ký. Generator emit cụ thể trong messages.ts. */
export type MessageCode = string
