// Copyright (c) 2026, AssetCore Team
// Axios instance với CSRF interceptor cho Frappe backend

import axios, {
  type AxiosInstance,
  type InternalAxiosRequestConfig,
  type AxiosResponse,
  type AxiosError,
} from 'axios'
import { ApiError, ErrorCode, httpStatusToCode } from './errors'
import { MESSAGES } from '@/i18n/messages'
import { loginPath, isOnLoginPage } from '@/utils/navigation'

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
type FrappeErrorData = {
  message?: string
  exc?: string
  _server_messages?: string
  // Phase 1 notification framework — present when raised qua nthrow_in_hook
  message_code?: string
  context?: Record<string, unknown>
  // Lỗi FIELD-LEVEL (khoá field → câu tiếng Việt). ĐÃ có sẵn trong envelope
  // Decision-B (`helpers.ts::ApiResponse.fields`); khai ở đây để nhánh HTTP
  // 417/422 (hook backstop `nthrow_in_hook` ghi vào `frappe.local.response`)
  // KHÔNG đánh rơi nó. FE chỉ ĐỌC — không sinh hợp đồng mới.
  fields?: Record<string, string>
}

// ─────────────────────────────────────────────────────────────────────────────
// AC-UX-063 — LÀM SẠCH CÂU LỖI NGHIỆP VỤ (ADR-UX-15, docs/ui-ux/05 §7)
//
// Một cửa duy nhất: bọc `parseServerMessages` — cửa chung của CẢ `handle400` LẪN
// `makeBusinessRuleError` nhánh fallback (417/422 không có `message_code`). Nhánh
// CÓ `message_code` đã render từ registry VI ⇒ KHÔNG đi qua đây (B5).
// ─────────────────────────────────────────────────────────────────────────────

/** Câu VI trung tính duy nhất — không sinh biến thể theo màn. */
const NEUTRAL_BUSINESS_MESSAGE =
  'Không thực hiện được thao tác do quy tắc nghiệp vụ. ' +
  'Vui lòng kiểm tra lại dữ liệu hoặc liên hệ quản trị hệ thống.'

/** Thẻ trình bày lành tính của Frappe — GỠ THẺ, giữ nguyên chữ (B4). */
const BENIGN_TAG_RE =
  /<\/?(?:b|strong|i|em|u|p|span|div|ul|ol|li|small)(?:\s[^>]*)?>/gi
const BR_TAG_RE = /<br\s*\/?>/gi

/**
 * Dấu hiệu kỹ thuật (docs/ui-ux/05 §7.3). Khớp BẤT KỲ mẫu nào ⇒ thay cả câu.
 * SQL dò theo CẶP từ khoá, không dò từ đơn — câu VI hợp lệ có thể chứa "update" (B3).
 */
const TECHNICAL_SIGNS: readonly RegExp[] = [
  /Traceback/,                       // traceback Python
  /File "/,
  /line \d+, in /,
  /<class '/,                        // kiểu/đối tượng Python
  /<module/,
  /<function/,
  /<built-in/,
  /cannot import name/i,             // lỗi import
  /\bSELECT\b[\s\S]*\bFROM\b/i,      // SQL — cặp từ khoá
  /\bINSERT\s+INTO\b/i,
  /\bUPDATE\b[\s\S]*\bSET\b/i,
  /\bDELETE\s+FROM\b/i,
  /\btab[A-Z]/,                      // tên bảng Frappe (`tabAC Asset`)
  /pymysql/i,                        // driver / lỗi DB
  /OperationalError/,
  /ProgrammingError/,
  /IntegrityError/,
  /frappe\.exceptions/,              // ngoại lệ Frappe
  /\.py\b/,                          // tệp nguồn
  /<[^>]+>/,                         // thẻ CÒN SÓT sau bước gỡ (vd <a href='/app/...'>)
]

/**
 * Làm sạch chuỗi lỗi máy chủ trước khi tới giao diện. Export để test khoá trực tiếp.
 *
 * 3 bước (`05 §7.2`): chuẩn hoá rỗng → gỡ thẻ trình bày lành tính → dò dấu hiệu kỹ
 * thuật. Câu tiếng Việt sạch đi qua NGUYÊN VĂN (chống sửa quá tay).
 */
export function sanitizeBusinessMessage(raw: string): string {
  const input = typeof raw === 'string' ? raw : String(raw ?? '')

  const stripped = input
    .replace(BR_TAG_RE, ' ')
    .replace(BENIGN_TAG_RE, '')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()

  const dirty = stripped === '' || TECHNICAL_SIGNS.some((re) => re.test(stripped))
  if (!dirty) return stripped

  // Chỉ log khi THẬT SỰ thay thế và có gì để đọc — dev vẫn chẩn đoán được, người
  // dùng cuối không bao giờ thấy chuỗi thô (A8).
  if (import.meta.env.DEV && input.trim() !== '') {
    console.debug('[axios] sanitizeBusinessMessage: chuỗi thô bị thay', input)
  }
  return NEUTRAL_BUSINESS_MESSAGE
}

/** Bóc `_server_messages` theo quy ước Frappe — logic gốc, KHÔNG đổi. */
function rawServerMessage(data: FrappeErrorData): string {
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

function parseServerMessages(data: FrappeErrorData): string {
  return sanitizeBusinessMessage(rawServerMessage(data))
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
    if (!authenticated && !isOnLoginPage()) {
      globalThis.location.href = loginPath(globalThis.location.pathname)
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
    || isOnLoginPage()
  if (!onLoginPage) {
    globalThis.location.href = loginPath(globalThis.location.pathname)
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
  if (!isOnLoginPage()) {
    try {
      const ping = await axios.get<{ message?: { data?: { authenticated?: boolean } } }>(
        '/api/method/assetcore.api.layout.ping_session',
        { withCredentials: true },
      )
      if (!(ping.data?.message?.data?.authenticated ?? true)) {
        globalThis.location.href = loginPath(globalThis.location.pathname)
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

function handle500(): never {
  // Finding C (2026-07-09): TUYỆT ĐỐI KHÔNG echo `data.exc`/traceback/exception ra UI.
  // Trước đây lấy dòng cuối của traceback Python ghép vào message → rò thông tin nội bộ
  // (đường dẫn file, tên hàm, stack) + gây hoảng cho người dùng cuối
  // ('Lỗi máy chủ nội bộ — ["Traceback (most recent call last)...'). Mọi 5xx (không
  // khớp shape Decision-B) → 1 thông điệp VN chung; chi tiết lỗi đã có ở Error Log server.
  throw new ApiError('Có lỗi máy chủ, vui lòng thử lại.',
    ErrorCode.INTERNAL_ERROR, 500)
}

// IMM-00 B-hardening (Vòng 12 resolve/scan + rotate): @rate_limit vượt ngưỡng →
// frappe.RateLimitExceededError (HTTP 429). Message gốc của Frappe là TIẾNG ANH
// ("You hit the rate limit because of too many requests...") → KHÔNG passthrough
// (chống EN-leak). Trả message VI verbatim + code RATE_LIMITED (FE bucket đúng,
// render thông báo "thao tác quá nhanh"; với rotate QR, modal Sinh-lại GIỮ MỞ để
// thử lại). KHÔNG leak raw status/code ra message.
function handle429(): never {
  throw new ApiError('Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút.',
    ErrorCode.RATE_LIMITED, 429)
}

/**
 * Build ApiError cho status 417/422 — ưu tiên hydrate từ `message_code` nếu BE
 * gửi qua frappe.local.response (nthrow_in_hook). Nếu không có, fallback parse
 * `_server_messages` (Frappe legacy convention).
 */
function makeBusinessRuleError(data: FrappeErrorData | undefined, status: number): ApiError {
  const messageCode = data?.message_code
  const context = data?.context
  // `fields` đi cùng lỗi nghiệp vụ để form gắn thông điệp vào ĐÚNG ô (AC-CR-83).
  // Nhánh in-envelope đã có (`helpers.ts::hydrateApiError`); nhánh status-line
  // 417/422 trước đây LÀM RƠI khoá này ⇒ lỗi hook backstop chỉ còn toast chung.
  const fields = data?.fields && Object.keys(data.fields).length ? data.fields : undefined
  const entry = messageCode ? MESSAGES[messageCode] : undefined
  if (entry) {
    const rendered = entry.template.replace(/\{(\w+)\}/g, (_, k: string) =>
      String(context?.[k] ?? `[${k}]`),
    )
    return new ApiError(rendered, {
      code: ErrorCode.BUSINESS_RULE,
      httpStatus: status,
      fields,
      messageCode,
      context,
      actionHint: entry.action_hint || undefined,
      severity: entry.severity,
      title: entry.title,
    })
  }
  return new ApiError(parseServerMessages(data ?? {}), {
    code: ErrorCode.BUSINESS_RULE,
    httpStatus: status,
    fields,
  })
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
      throw makeBusinessRuleError(data, status)
    }
    if (status === 429) return handle429()
    // Mọi 5xx (500/502/503/504…) → thông điệp máy chủ chung, KHÔNG passthrough
    // `data.message`/traceback (Finding C — chống rò thông tin nội bộ).
    if (status >= 500) return handle500()

    throw new ApiError(
      data?.message ?? `Lỗi không xác định (HTTP ${status})`,
      httpStatusToCode(status), status,
    )
  },
)

export default api
