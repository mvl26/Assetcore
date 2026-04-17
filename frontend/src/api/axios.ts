// Copyright (c) 2026, AssetCore Team
// Axios instance với CSRF interceptor cho Frappe backend

import axios, {
  type AxiosInstance,
  type InternalAxiosRequestConfig,
  type AxiosResponse,
  type AxiosError,
} from 'axios'

// ─────────────────────────────────────────────────────────────────────────────
// CSRF TOKEN HELPERS
// ─────────────────────────────────────────────────────────────────────────────

// Module-level cache — được set sau login hoặc refresh
let _storedCsrfToken: string = ''

/** Set CSRF token từ login response body (gọi từ auth store sau khi login thành công). */
export function setCsrfToken(token: string): void {
  _storedCsrfToken = token
}

/**
 * Đọc CSRF token theo thứ tự ưu tiên:
 * 1. Cached từ login response (đáng tin cậy nhất)
 * 2. window.frappe.csrf_token (khi chạy embedded trong Frappe desk)
 * 3. Cookie csrf_token do Frappe set
 */
function getCsrfToken(): string {
  if (_storedCsrfToken) return _storedCsrfToken

  if (typeof window !== 'undefined' && (window as Window & { frappe?: { csrf_token?: string } }).frappe?.csrf_token) {
    return (window as Window & { frappe?: { csrf_token?: string } }).frappe!.csrf_token!
  }

  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
  if (match) {
    return decodeURIComponent(match[1])
  }

  return ''
}

/**
 * Gọi GET endpoint không cần CSRF để Frappe refresh cookie, sau đó đọc lại.
 * Dùng khi POST bị 400 CSRF error — retry 1 lần sau khi refresh.
 */
async function refreshCsrfToken(): Promise<string> {
  try {
    // GET does not need CSRF — Frappe will set the csrf_token cookie in the response.
    // After the Vite proxy strips Domain= from Set-Cookie the browser accepts it.
    const res = await axios.get<{ csrf_token?: string }>(
      '/api/method/frappe.auth.get_logged_user',
      { withCredentials: true },
    )
    // Some Frappe versions include csrf_token in the response body
    if (res.data?.csrf_token) {
      _storedCsrfToken = res.data.csrf_token
      return _storedCsrfToken
    }
  } catch {
    // ignore — fall through to cookie read
  }
  _storedCsrfToken = ''
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
  if (match) {
    _storedCsrfToken = decodeURIComponent(match[1])
  }
  return _storedCsrfToken
}

// ─────────────────────────────────────────────────────────────────────────────
// AXIOS INSTANCE
// ─────────────────────────────────────────────────────────────────────────────

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
  timeout: 30_000,
  withCredentials: true, // Frappe dùng session cookie
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// ─────────────────────────────────────────────────────────────────────────────
// REQUEST INTERCEPTOR — Đính kèm CSRF token
// ─────────────────────────────────────────────────────────────────────────────

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getCsrfToken()
    if (token) {
      config.headers['X-Frappe-CSRF-Token'] = token
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error),
)

// ─────────────────────────────────────────────────────────────────────────────
// RESPONSE INTERCEPTOR — Handle lỗi chung
// ─────────────────────────────────────────────────────────────────────────────

type RetryableConfig = InternalAxiosRequestConfig & { _csrfRetried?: boolean }
type FrappeErrorData = { message?: string; exc?: string; _server_messages?: string }

function parseServerMessages(data: FrappeErrorData): string {
  if (!data._server_messages) return data.message ?? 'Dữ liệu không hợp lệ.'
  try {
    const msgs: string[] = JSON.parse(data._server_messages)
    return msgs
      .map((m) => { try { return JSON.parse(m).message as string } catch { return m } })
      .join(' | ')
  } catch {
    return data.message ?? 'Dữ liệu không hợp lệ.'
  }
}

async function handle400(
  error: AxiosError<FrappeErrorData>,
): Promise<AxiosResponse> {
  const msg = (error.response?.data as FrappeErrorData)?.message ?? ''
  const lower = msg.toLowerCase()
  const isCsrfError = !msg || lower.includes('csrf') || lower.includes('invalid request') || lower.includes('incorrect')

  const originalConfig = error.config as RetryableConfig | undefined
  if (isCsrfError && originalConfig && !originalConfig._csrfRetried) {
    originalConfig._csrfRetried = true
    const newToken = await refreshCsrfToken()
    if (newToken && originalConfig.headers) {
      originalConfig.headers['X-Frappe-CSRF-Token'] = newToken
      return api(originalConfig)
    }
  }

  throw new Error('Yêu cầu không hợp lệ. Vui lòng tải lại trang và thử lại (CSRF token hết hạn).')
}

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<FrappeErrorData>) => {
    if (!error.response) {
      throw new Error('Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối mạng.')
    }

    const { status, data } = error.response

    if (status === 400) return handle400(error)

    if (status === 401) {
      const url = error.config?.url ?? ''
      if (!url.includes('/api/method/login') && !globalThis.location.pathname.startsWith('/login')) {
        globalThis.location.href = `/login?redirect=${encodeURIComponent(globalThis.location.pathname)}`
        throw new Error('Phiên đăng nhập đã hết hạn. Đang chuyển hướng...')
      }
      throw new Error(data?.message ?? 'Sai tên đăng nhập hoặc mật khẩu.')
    }

    if (status === 403) throw new Error('Bạn không có quyền thực hiện hành động này.')
    if (status === 404) throw new Error('Không tìm thấy tài nguyên yêu cầu.')

    if (status === 417) throw new Error(parseServerMessages(data ?? {}))

    if (status === 500) {
      const excSummary = data?.exc ? String(data.exc).split('\n').findLast(Boolean) ?? '' : ''
      const hint = excSummary ? ' — ' + excSummary : ''
      throw new Error('500 Lỗi máy chủ nội bộ' + hint)
    }

    throw new Error(data?.message ?? `Lỗi không xác định (HTTP ${status})`)
  },
)

export default api
