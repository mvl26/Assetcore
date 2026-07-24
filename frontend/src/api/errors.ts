// Copyright (c) 2026, AssetCore Team
// ApiError — class lỗi chuẩn cho toàn FE.
// Mọi handler API (frappeGet/Post + axios interceptor) throw instance này.

/** Severity — trùng `assetcore/utils/messages.py:Severity`. */
export type Severity = 'error' | 'warning' | 'info' | 'success' | 'critical'

/** Code khớp với assetcore/utils/response.py — ErrorCode (Phase 0 hợp nhất). */
export const ErrorCode = {
  VALIDATION: 'VALIDATION',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  BUSINESS_RULE: 'BUSINESS_RULE',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  CONFLICT: 'CONFLICT',
  BAD_STATE: 'BAD_STATE',
  DUPLICATE: 'DUPLICATE',
  INVALID_PARAMS: 'INVALID_PARAMS',
  PAYLOAD_TOO_LARGE: 'PAYLOAD_TOO_LARGE',
  RATE_LIMITED: 'RATE_LIMITED',
  COMPLIANCE_BLOCKED: 'COMPLIANCE_BLOCKED',
  INTERNAL: 'INTERNAL',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  NETWORK_ERROR: 'NETWORK_ERROR',
  UNKNOWN: 'UNKNOWN',
} as const

export type ErrorCodeType = typeof ErrorCode[keyof typeof ErrorCode]

/**
 * Options khi construct ApiError (Phase 1 notification framework extension).
 *
 * Backwards-compat: vẫn hỗ trợ constructor signature cũ
 * `new ApiError(msg, code, status, fields, extra)` qua overload.
 */
export interface ApiErrorOpts {
  code?: ErrorCodeType
  httpStatus?: number
  fields?: Record<string, string>
  extra?: Record<string, unknown>
  /** MSG.XXX lookup key — FE tra `MESSAGES[messageCode]` để render lại. */
  messageCode?: string
  /** Biến template cho `{var}` trong message. */
  context?: Record<string, unknown>
  /** Gợi ý hành động kế tiếp cho user. */
  actionHint?: string
  /** Severity — quyết định UI (toast / modal). */
  severity?: Severity
  /** Tiêu đề ngắn cho dialog/toast. */
  title?: string
}

export class ApiError extends Error {
  readonly code: ErrorCodeType
  readonly httpStatus: number
  readonly fields?: Record<string, string>
  /** Các key bổ sung từ BE (vd: `existing_user` khi 409 conflict). */
  readonly extra?: Record<string, unknown>
  /** Notification framework extension (Phase 1) — optional. */
  readonly messageCode?: string
  readonly context?: Record<string, unknown>
  readonly actionHint?: string
  readonly severity?: Severity
  readonly title?: string

  constructor(
    message: string,
    codeOrOpts: ErrorCodeType | ApiErrorOpts = ErrorCode.UNKNOWN,
    httpStatus: number = 0,
    fields?: Record<string, string>,
    extra?: Record<string, unknown>,
  ) {
    super(message)
    this.name = 'ApiError'
    // Overload: nếu codeOrOpts là object → dạng options (mới);
    // ngược lại → positional args (legacy).
    if (typeof codeOrOpts === 'object' && codeOrOpts !== null) {
      const opts = codeOrOpts
      this.code = opts.code ?? ErrorCode.UNKNOWN
      this.httpStatus = opts.httpStatus ?? 0
      this.fields = opts.fields
      this.extra = opts.extra
      this.messageCode = opts.messageCode
      this.context = opts.context
      this.actionHint = opts.actionHint
      this.severity = opts.severity
      this.title = opts.title
    } else {
      this.code = codeOrOpts
      this.httpStatus = httpStatus
      this.fields = fields
      this.extra = extra
    }
  }

  /** True khi lỗi nghiệp vụ — UX thường là warning toast + giữ form. */
  get isBusinessError(): boolean {
    return this.code === ErrorCode.BUSINESS_RULE
      || this.code === ErrorCode.VALIDATION
      || this.code === ErrorCode.VALIDATION_ERROR
      || this.code === ErrorCode.CONFLICT
      || this.code === ErrorCode.BAD_STATE
      || this.code === ErrorCode.DUPLICATE
      || this.code === ErrorCode.COMPLIANCE_BLOCKED
  }

  /** True khi lỗi system — UX thường là error toast đỏ. */
  get isSystemError(): boolean {
    return this.code === ErrorCode.INTERNAL
      || this.code === ErrorCode.INTERNAL_ERROR
      || this.code === ErrorCode.NETWORK_ERROR
      || this.code === ErrorCode.UNKNOWN
  }
}

/** Map HTTP status → ErrorCode khi BE không trả `code`. */
export function httpStatusToCode(status: number): ErrorCodeType {
  switch (status) {
    case 400: return ErrorCode.VALIDATION_ERROR
    case 401: return ErrorCode.UNAUTHORIZED
    case 403: return ErrorCode.FORBIDDEN
    case 404: return ErrorCode.NOT_FOUND
    case 409: return ErrorCode.CONFLICT
    case 413: return ErrorCode.PAYLOAD_TOO_LARGE
    case 417:
    case 422: return ErrorCode.BUSINESS_RULE
    // Vòng 27 B (FR-00-87): 429 rate-limit → bucket RATE_LIMITED. Trước fix rơi về
    // UNKNOWN (mis-bucket — kể cả 429 resolve/scan đã throttle từ Vòng 12). Mirror
    // BE `frappe.RateLimitExceededError` → HTTP 429.
    case 429: return ErrorCode.RATE_LIMITED
    case 500:
    case 502:
    case 503: return ErrorCode.INTERNAL_ERROR
    default: return ErrorCode.UNKNOWN
  }
}

/** Đảm bảo instance ApiError — dùng trong catch khi nhận `unknown`. */
export function toApiError(e: unknown): ApiError {
  if (e instanceof ApiError) return e
  if (e instanceof Error) return new ApiError(e.message || 'Lỗi không xác định', ErrorCode.UNKNOWN)
  return new ApiError(String(e), ErrorCode.UNKNOWN)
}

/**
 * Phân loại lỗi NẠP bản ghi trên màn chi tiết → khoá render `DetailLoadError`.
 *
 * 'notfound' = mã sai / bản ghi đã xoá (BE trả http_status 404 trong envelope, HTTP
 * vẫn 200 — xem in-handler 404 của Frappe RPC) ⇒ empty-state, KHÔNG mời thử lại.
 * Mọi lỗi khác (mạng, 403, 500…) → 'unknown' ⇒ hiện message server + nút Thử lại.
 */
export function loadErrorKind(e: unknown): 'notfound' | 'unknown' {
  const err = toApiError(e)
  return (err.httpStatus === 404 || err.code === ErrorCode.NOT_FOUND) ? 'notfound' : 'unknown'
}
