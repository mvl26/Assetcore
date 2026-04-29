// Copyright (c) 2026, AssetCore Team
// Axios instance với CSRF interceptor cho Frappe backend

import axios, {
  type AxiosInstance,
  type InternalAxiosRequestConfig,
  type AxiosResponse,
  type AxiosError,
} from 'axios'
import { ApiError, ErrorCode, httpStatusToCode } from './errors'

// ─────────────────────────────────────────────────────────────────────────────
// CSRF TOKEN HELPERS
// ─────────────────────────────────────────────────────────────────────────────

// Module-level cache — được set sau login hoặc refresh
let _storedCsrfToken: string = ''

const CSRF_COOKIE_RE = /(?:^|;\s*)csrf_token=([^;]+)/

function readCsrfCookie(): string {
  const match = CSRF_COOKIE_RE.exec(document.cookie)
  return match ? decodeURIComponent(match[1]) : ''
}

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

  const gw = globalThis as typeof globalThis & { frappe?: { csrf_token?: string } }
  if (gw.frappe?.csrf_token) {
    return gw.frappe.csrf_token
  }

  return readCsrfCookie()
}

/**
 * Gọi GET endpoint không cần CSRF để Frappe refresh cookie, sau đó đọc lại.
 * Dùng khi POST bị 400 CSRF error — retry 1 lần sau khi refresh.
 */
type PingResp = {
  message?: {
    success?: boolean
    data?: { user?: string; authenticated?: boolean; csrf_token?: string }
  }
}

/**
 * Gọi ping_session để lấy csrf_token mới + trạng thái session.
 * Trả về { token, authenticated } — caller dùng `authenticated` để quyết định
 * có cần redirect login hay không (case session bị clear khi admin sửa role).
 */
async function refreshCsrfToken(): Promise<{ token: string; authenticated: boolean }> {
  let authenticated = true
  try {
    const res = await axios.get<PingResp>(
      '/api/method/assetcore.api.layout.ping_session',
      { withCredentials: true },
    )
    const data = res.data?.message?.data
    if (data?.csrf_token) {
      _storedCsrfToken = data.csrf_token
    }
    if (typeof data?.authenticated === 'boolean') {
      authenticated = data.authenticated
    }
    if (_storedCsrfToken) return { token: _storedCsrfToken, authenticated }
  } catch {
    // fall through
  }
  _storedCsrfToken = readCsrfCookie()
  return { token: _storedCsrfToken, authenticated }
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

  // Chỉ retry khi là CSRF error thực sự — không match "incorrect" chung chung
  // vì sẽ gây double-submit (tạo user 2 lần → 409 lần 2).
  const isCsrfError = !msg
    || lower.includes('csrf')
    || lower === 'incorrect request'
    || lower.includes('invalid request')

  const originalConfig = error.config as RetryableConfig | undefined
  if (isCsrfError && originalConfig && !originalConfig._csrfRetried) {
    originalConfig._csrfRetried = true
    const { token: newToken, authenticated } = await refreshCsrfToken()
    // Khi admin sửa role, Frappe clear_sessions() → sid cũ chết, server coi là Guest.
    // Trong case này retry sẽ fail tiếp; redirect login để user không bị kẹt với
    // "Invalid Request" và phải tự logout.
    if (!authenticated && !globalThis.location.pathname.startsWith('/login')) {
      globalThis.location.href = `/login?redirect=${encodeURIComponent(globalThis.location.pathname)}`
      throw new ApiError(
        'Phiên đăng nhập đã thay đổi (role/quyền). Đang chuyển hướng đến trang đăng nhập...',
        ErrorCode.UNAUTHORIZED, 401,
      )
    }
    if (newToken && originalConfig.headers) {
      originalConfig.headers['X-Frappe-CSRF-Token'] = newToken
      return api(originalConfig)
    }
  }

  throw new ApiError(
    parseServerMessages((error.response?.data as FrappeErrorData) ?? {}),
    ErrorCode.VALIDATION_ERROR, 400,
  )
}

// ── Per-status handlers (extracted to keep interceptor flat) ──────────────────

function handle401(error: AxiosError<FrappeErrorData>): never {
  const url = error.config?.url ?? ''
  const onLoginPage = url.includes('/api/method/login')
    || globalThis.location.pathname.startsWith('/login')
  if (!onLoginPage) {
    globalThis.location.href = `/login?redirect=${encodeURIComponent(globalThis.location.pathname)}`
    throw new ApiError('Phiên đăng nhập đã hết hạn. Đang chuyển hướng...',
      ErrorCode.UNAUTHORIZED, 401)
  }
  throw new ApiError(
    error.response?.data?.message ?? 'Sai tên đăng nhập hoặc mật khẩu.',
    ErrorCode.UNAUTHORIZED, 401,
  )
}

async function handle403(): Promise<never> {
  // Frappe trả 403 cho cả 2 TH: (1) session hết hạn → Guest,
  // (2) đã login nhưng thiếu role. Phân biệt qua ping_session.
  if (!globalThis.location.pathname.startsWith('/login')) {
    try {
      const ping = await axios.get<{ message?: { data?: { authenticated?: boolean } } }>(
        '/api/method/assetcore.api.layout.ping_session',
        { withCredentials: true },
      )
      if (!(ping.data?.message?.data?.authenticated ?? true)) {
        globalThis.location.href = `/login?redirect=${encodeURIComponent(globalThis.location.pathname)}`
        throw new ApiError(
          'Phiên đăng nhập đã hết hạn. Đang chuyển hướng đến trang đăng nhập...',
          ErrorCode.UNAUTHORIZED, 401,
        )
      }
    } catch (e) {
      if (e instanceof ApiError && e.code === ErrorCode.UNAUTHORIZED) throw e
    }
  }
  throw new ApiError('Bạn không có quyền thực hiện hành động này.',
    ErrorCode.FORBIDDEN, 403)
}

function handle500(data: FrappeErrorData | undefined): never {
  const last = data?.exc ? String(data.exc).split('\n').findLast(Boolean) ?? '' : ''
  throw new ApiError('Lỗi máy chủ nội bộ' + (last ? ' — ' + last : ''),
    ErrorCode.INTERNAL_ERROR, 500)
}

// ── Response interceptor ───────────────────────────────────────────────────────

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<FrappeErrorData>) => {
    if (!error.response) {
      throw new ApiError(
        'Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối mạng.',
        ErrorCode.NETWORK_ERROR, 0,
      )
    }

    const { status, data } = error.response

    if (status === 400) return handle400(error)
    if (status === 401) return handle401(error)
    if (status === 403) return handle403()
    if (status === 404) {
      throw new ApiError(data?.message || 'Không tìm thấy tài nguyên yêu cầu.',
        ErrorCode.NOT_FOUND, 404)
    }
    if (status === 409) {
      throw new ApiError(data?.message || 'Dữ liệu đã tồn tại trong hệ thống.',
        ErrorCode.CONFLICT, 409)
    }
    if (status === 417 || status === 422) {
      throw new ApiError(parseServerMessages(data ?? {}),
        ErrorCode.BUSINESS_RULE, status)
    }
    if (status === 500) return handle500(data)

    throw new ApiError(
      data?.message ?? `Lỗi không xác định (HTTP ${status})`,
      httpStatusToCode(status), status,
    )
  },
)

export default api
