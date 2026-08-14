import api from './axios'
import { ApiError, ErrorCode, httpStatusToCode, type ErrorCodeType, type Severity } from './errors'
import { MESSAGES } from '@/locales/messages'

export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
  code?: string
  http_status?: number
  fields?: Record<string, string>
  // Notification framework extension (Phase 1) — optional.
  message_code?: string
  context?: Record<string, unknown>
  action_hint?: string
  severity?: Severity
  title?: string
}

// Backend chuẩn: { message: { success, data } } HOẶC
//                { message: { success: false, error, code, http_status, fields?,
//                             message_code?, context?, action_hint?, severity?, title? } }
// Helper unwrap 2 lớp (frappe `message` + AssetCore envelope) và throw ApiError
// chuẩn để caller phân nhánh theo `err.code` / `err.fields` / `err.messageCode`.
// Legacy handler trả raw (không có `success`) → passthrough.

// Các key đã có trong envelope chuẩn — không pass qua extra (tránh trùng).
const _ENVELOPE_KEYS = new Set([
  'success', 'data', 'error', 'code', 'http_status', 'fields',
  // Notification framework extension keys
  'message_code', 'context', 'action_hint', 'severity', 'title',
])

/**
 * Hydrate ApiError từ envelope:
 * - Nếu BE trả `message_code` → tra registry, lấy actionHint/severity/title nếu BE
 *   không gửi (BE có thể đã gửi sẵn — dùng giá trị BE ưu tiên).
 * - Nếu không có `message_code` → ApiError tối thiểu (legacy path).
 */
function hydrateApiError(env: ApiResponse<unknown> & Record<string, unknown>): ApiError {
  const code: ErrorCodeType = (env.code as ErrorCodeType | undefined)
    ?? (env.http_status ? httpStatusToCode(env.http_status) : ErrorCode.UNKNOWN)

  // Gom các key BE thêm (vd: existing_user) vào `extra`
  const extra: Record<string, unknown> = {}
  for (const k of Object.keys(env)) {
    if (!_ENVELOPE_KEYS.has(k)) extra[k] = env[k]
  }

  // Resolve notification fields — prefer BE → fallback registry → undefined
  let actionHint = env.action_hint
  let severity = env.severity
  let title = env.title
  if (env.message_code) {
    const entry = MESSAGES[env.message_code]
    if (entry) {
      actionHint ??= entry.action_hint || undefined
      severity ??= entry.severity
      title ??= entry.title
    }
  }

  return new ApiError(env.error || 'Lỗi không xác định', {
    code,
    httpStatus: env.http_status ?? 0,
    fields: env.fields,
    extra: Object.keys(extra).length ? extra : undefined,
    messageCode: env.message_code,
    context: env.context,
    actionHint,
    severity,
    title,
  })
}

function unwrap<T>(message: unknown): T {
  if (message && typeof message === 'object' && 'success' in (message as object)) {
    const env = message as ApiResponse<T> & Record<string, unknown>
    if (env.success === false) {
      throw hydrateApiError(env as ApiResponse<unknown> & Record<string, unknown>)
    }
    return env.data as T
  }
  return message as T
}

export async function frappeGet<T>(endpoint: string, params?: Record<string, unknown>): Promise<T> {
  const response = await api.get<{ message: unknown }>(endpoint, { params })
  return unwrap<T>(response.data.message)
}

export async function frappePost<T>(endpoint: string, body?: Record<string, unknown>): Promise<T> {
  const response = await api.post<{ message: unknown }>(endpoint, body)
  return unwrap<T>(response.data.message)
}
