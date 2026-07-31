// Copyright (c) 2026, AssetCore Team
// ApiError — class lỗi chuẩn cho toàn FE.
// Mọi handler API (frappeGet/Post + axios interceptor) throw instance này.

import { MSG } from '@/i18n/messages'

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

/** Khoá render của `DetailLoadError` — 1 nhánh empty-state cho mỗi loại lỗi nạp. */
export type DetailLoadKind = 'notfound' | 'forbidden' | 'unknown'

/**
 * True khi lỗi là "KHÔNG ĐỦ QUYỀN ĐỌC" do BE trả **trong envelope** (HTTP-200 +
 * `{success:false, code:'FORBIDDEN', http_status:403}` — Decision-B, CR-74).
 *
 * PHÂN BIỆT với dispatcher-403 (status-line): dispatcher-403 do `axios.ts::handle403`
 * xử lý — nó ping `layout.ping_session` và CHỈ redirect login khi phiên đã chết. Lỗi
 * in-envelope KHÔNG bao giờ đi qua interceptor ⇒ **KHÔNG logout, KHÔNG redirect**:
 * người dùng vẫn đăng nhập hợp lệ, chỉ là không được đọc bản ghi này.
 */
export function isForbiddenError(e: unknown): boolean {
  const err = toApiError(e)
  return err.code === ErrorCode.FORBIDDEN || err.httpStatus === 403
}

/**
 * Mã lỗi BE dùng cho **tham số lọc không hợp lệ** trên endpoint danh sách
 * (AC-CR-79 — whitelist khoá `filters` của `list_pm_work_orders` /
 * `list_repair_work_orders`).
 *
 * FE cố ý nhận NHIỀU mã: BA có thể chốt mã mới `INVALID_FILTER_KEY` hoặc tái dùng
 * mã cũ (`VAL-INVALID-PARAMS` → `VALIDATION_ERROR`/`INVALID_PARAMS`). Đây là phân
 * loại MÃ LỖI, **KHÔNG phải bản sao whitelist khoá lọc** — FE tuyệt đối không giữ
 * danh sách khoá hợp lệ (SSoT duy nhất nằm ở `services/imm08.py` / `imm09.py`),
 * chỉ hiển thị lại message tiếng Việt do BE trả về.
 */
const _FILTER_ERROR_CODES: ReadonlySet<string> = new Set<string>([
  'INVALID_FILTER_KEY',
  ErrorCode.INVALID_PARAMS,
  ErrorCode.VALIDATION_ERROR,
  ErrorCode.VALIDATION,
])

/**
 * True khi lỗi là "khoá lọc không hợp lệ" BE trả **trong envelope**
 * (HTTP-200 + `{success:false, code:…, http_status:400}` — AC-CR-79).
 *
 * Dùng ở store danh sách để phân biệt với lỗi nạp THẬT: lỗi tham số lọc KHÔNG
 * được xoá bảng đang xem (người dùng vẫn thấy dữ liệu cũ + cảnh báo), còn lỗi
 * mạng/500/403 vẫn đi nhánh error cũ.
 *
 * ⚠️ Loại trừ FORBIDDEN TRƯỚC: `assert_vendor_can_access` (services/shared/scope.py)
 * hiện raise `code='FORBIDDEN'` kèm `http_status=400` (blocker BA đang chờ ratify)
 * ⇒ chỉ lọc theo `http_status === 400` sẽ nuốt nhầm lỗi phân quyền thành "bộ lọc sai".
 */
export function isFilterKeyError(e: unknown): boolean {
  const err = toApiError(e)
  if (isForbiddenError(err)) return false
  // So sánh trên `string` (không phải `ErrorCodeType`): mã `INVALID_FILTER_KEY` do BA
  // đề xuất CHƯA có trong `ErrorCode` (bản sao của `assetcore/utils/response.py`).
  // Khi BA chốt và BE thêm mã, mirror vào `ErrorCode` rồi bỏ lớp widen này — FE nhận
  // trước để không phụ thuộc thứ tự land BE↔FE (`hydrateApiError` vốn giữ nguyên
  // chuỗi `code` server trả, kể cả mã ngoài enum).
  // Tín hiệu CHÍNH XÁC nhất: `message_code` BE gửi kèm envelope. `MSG` là file
  // GENERATED từ `assetcore/utils/messages.py` ⇒ dùng hằng số, KHÔNG gõ chuỗi tay.
  if (err.messageCode === MSG.VAL_INVALID_FILTER_KEY) return true
  if (err.messageCode === MSG.VAL_INVALID_PARAMS) return true
  const code: string = err.code
  if (code === 'INVALID_FILTER_KEY') return true
  return err.httpStatus === 400 && _FILTER_ERROR_CODES.has(code)
}

/**
 * Phân loại lỗi NẠP bản ghi trên màn chi tiết → khoá render `DetailLoadError`.
 *
 * 'notfound'  = mã sai / bản ghi đã xoá (BE trả http_status 404 trong envelope, HTTP
 *               vẫn 200 — xem in-handler 404 của Frappe RPC) ⇒ empty-state, KHÔNG mời thử lại.
 * 'forbidden' = thiếu quyền đọc (role DocPerm HOẶC phiếu không giao cho mình — hook
 *               `has_permission`); BE trả FORBIDDEN 403 TRONG envelope ⇒ hiện message
 *               THẬT của server, KHÔNG mời thử lại (thử lại vô nghĩa), KHÔNG logout.
 * Còn lại (mạng, 500…) → 'unknown' ⇒ message server + nút Thử lại.
 *
 * Thứ tự khớp BE (CR-74 / ADR-IMM00-DETAIL-READ-02): role-gate chạy TRƯỚC `exists`
 * ⇒ thiếu quyền + mã bịa vẫn là 403 (no existence-oracle), nên nhánh 404 chỉ tới khi
 * người dùng ĐÃ đủ quyền đọc.
 */
export function loadErrorKind(e: unknown): DetailLoadKind {
  const err = toApiError(e)
  if (err.httpStatus === 404 || err.code === ErrorCode.NOT_FOUND) return 'notfound'
  if (isForbiddenError(err)) return 'forbidden'
  return 'unknown'
}
