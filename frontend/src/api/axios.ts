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

/**
 * Đọc CSRF token từ cookie `csrf_token` do Frappe set.
 * Frappe cũng expose window.frappe.csrf_token nếu đang trong Frappe desk.
 */
function getCsrfToken(): string {
  // 1. Thử lấy từ window.frappe (khi chạy embedded trong Frappe desk)
  if (typeof window !== 'undefined' && (window as Window & { frappe?: { csrf_token?: string } }).frappe?.csrf_token) {
    return (window as Window & { frappe?: { csrf_token?: string } }).frappe!.csrf_token!
  }

  // 2. Lấy từ cookie csrf_token
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
  if (match) {
    return decodeURIComponent(match[1])
  }

  return ''
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

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<{ message?: string; exc?: string; _server_messages?: string }>) => {
    if (!error.response) {
      // Network error
      return Promise.reject(new Error('Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối mạng.'))
    }

    const { status, data } = error.response

    switch (status) {
      case 401: {
        // Nếu chính request login bị 401 → sai mật khẩu, không redirect
        const url = error.config?.url ?? ''
        const isLoginRequest = url.includes('/api/method/login')
        if (!isLoginRequest && !window.location.pathname.startsWith('/login')) {
          window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`
          return Promise.reject(new Error('Phiên đăng nhập đã hết hạn. Đang chuyển hướng...'))
        }
        // Lỗi đăng nhập sai thông tin
        const serverMsg = (data as { message?: string })?.message
        return Promise.reject(new Error(serverMsg ?? 'Sai tên đăng nhập hoặc mật khẩu.'))
      }

      case 403:
        return Promise.reject(new Error('Bạn không có quyền thực hiện hành động này.'))

      case 417: {
        // Frappe validation error — parse server_messages
        let msg = 'Dữ liệu không hợp lệ.'
        if (data?._server_messages) {
          try {
            const msgs: string[] = JSON.parse(data._server_messages)
            msg = msgs
              .map((m: string) => {
                try {
                  return JSON.parse(m).message as string
                } catch {
                  return m
                }
              })
              .join(' | ')
          } catch {
            msg = data.message ?? msg
          }
        } else if (data?.message) {
          msg = data.message
        }
        return Promise.reject(new Error(msg))
      }

      case 404:
        return Promise.reject(new Error('Không tìm thấy tài nguyên yêu cầu.'))

      case 500:
        return Promise.reject(new Error('Lỗi máy chủ nội bộ. Vui lòng liên hệ IT.'))

      default:
        return Promise.reject(
          new Error(data?.message ?? `Lỗi không xác định (HTTP ${status})`),
        )
    }
  },
)

export default api
