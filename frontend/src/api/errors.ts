// Copyright (c) 2026, AssetCore Team
// ApiError — class lỗi chuẩn cho toàn FE.
// Mọi handler API (frappeGet/Post + axios interceptor) throw instance này.

/** Code khớp với assetcore/utils/response.py — ErrorCode. */
export const ErrorCode = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  BUSINESS_RULE: 'BUSINESS_RULE_VIOLATION',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  CONFLICT: 'CONFLICT',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  NETWORK_ERROR: 'NETWORK_ERROR',
  UNKNOWN: 'UNKNOWN',
} as const

export type ErrorCodeType = typeof ErrorCode[keyof typeof ErrorCode]

export class ApiError extends Error {
  readonly code: ErrorCodeType
  readonly httpStatus: number
  readonly fields?: Record<string, string>
  /** Các key bổ sung từ BE (vd: `existing_user` khi 409 conflict). */
  readonly extra?: Record<string, unknown>

  constructor(
    message: string,
    code: ErrorCodeType = ErrorCode.UNKNOWN,
    httpStatus = 0,
    fields?: Record<string, string>,
    extra?: Record<string, unknown>,
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.httpStatus = httpStatus
    this.fields = fields
    this.extra = extra
  }

  /** True khi lỗi nghiệp vụ — UX thường là warning toast + giữ form. */
  get isBusinessError(): boolean {
    return this.code === ErrorCode.BUSINESS_RULE
      || this.code === ErrorCode.VALIDATION_ERROR
      || this.code === ErrorCode.CONFLICT
  }

  /** True khi lỗi system — UX thường là error toast đỏ. */
  get isSystemError(): boolean {
    return this.code === ErrorCode.INTERNAL_ERROR
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
    case 417:
    case 422: return ErrorCode.BUSINESS_RULE
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
