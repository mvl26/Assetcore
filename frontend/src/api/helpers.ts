import api from './axios'

export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
  code?: string
}

// Backend chuẩn trả về: { message: { success: bool, data: <payload> } }
// Helper unwrap 2 lớp: frappe "message" + AssetCore _ok/_err envelope.
// Legacy handler nào trả raw (không có success key) sẽ được passthrough.

function unwrap<T>(message: unknown): T {
  if (message && typeof message === 'object' && 'success' in (message as object)) {
    const env = message as ApiResponse<T>
    if (env.success === false) {
      throw new Error(env.error || env.code || 'Lỗi không xác định')
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
