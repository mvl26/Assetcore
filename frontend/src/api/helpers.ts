import api from './axios'
import { ApiError, ErrorCode, httpStatusToCode, type ErrorCodeType } from './errors'

export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
  code?: string
  http_status?: number
  fields?: Record<string, string>
}

// Backend chuẩn: { message: { success, data } } HOẶC
//                { message: { success: false, error, code, http_status, fields? } }
// Helper unwrap 2 lớp (frappe `message` + AssetCore envelope) và throw ApiError
// chuẩn để caller phân nhánh theo `err.code` / `err.fields`.
// Legacy handler trả raw (không có `success`) → passthrough.

// Các key đã có trong envelope chuẩn — không pass qua extra (tránh trùng).
const _ENVELOPE_KEYS = new Set(['success', 'data', 'error', 'code', 'http_status', 'fields'])

function unwrap<T>(message: unknown): T {
  if (message && typeof message === 'object' && 'success' in (message as object)) {
    const env = message as ApiResponse<T> & Record<string, unknown>
    if (env.success === false) {
      const code: ErrorCodeType = (env.code as ErrorCodeType | undefined)
        ?? (env.http_status ? httpStatusToCode(env.http_status) : ErrorCode.UNKNOWN)
      // Gom các key BE thêm (vd: existing_user) vào `extra`
      const extra: Record<string, unknown> = {}
      for (const k of Object.keys(env)) {
        if (!_ENVELOPE_KEYS.has(k)) extra[k] = env[k]
      }
      throw new ApiError(
        env.error || 'Lỗi không xác định',
        code,
        env.http_status ?? 0,
        env.fields,
        Object.keys(extra).length ? extra : undefined,
      )
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
