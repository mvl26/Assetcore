// Copyright (c) 2026, AssetCore Team
// Chuẩn hoá `fields` của envelope lỗi BE → Record<fieldname, thông điệp hiển thị>.
//
// BE có HAI dạng `fields` đang cùng tồn tại:
//   1. dict  {field: "câu lỗi riêng cho ô đó"}   — khuôn `utils/response.py` (đa số op)
//   2. list  ["field", ...]                       — op chỉ ĐÁNH DẤU ô lỗi, câu chữ nằm
//      ở `error` (vd `reschedule_calibration`: fields=['reason'] / ['new_date'])
//
// FE phải sống được với CẢ HAI (contract-drift = form không hiện lỗi ở ô nào cả).
// Với dạng list — hoặc dạng dict mà value rỗng/không phải chuỗi — ta gắn NGUYÊN VĂN
// câu tiếng Việt của server (`err.message`) vào ô đó: KHÔNG bịa chuỗi kỹ thuật,
// KHÔNG phơi mã lỗi/traceback cho người dùng (LL-FE-53 · notification contract).

import type { ApiError } from '@/api/errors'

/** Nguồn lỗi tối thiểu cần để chuẩn hoá — nới lỏng để test mock được. */
export interface FieldErrorSource {
  message?: string
  fields?: unknown
}

/**
 * Trả về map {field: message} luôn dùng được cho `:aria-describedby` / hiển thị
 * inline. Không có `fields` (hoặc err null) ⇒ `{}` (caller hiển thị lỗi ở banner chung).
 */
export function normalizeFieldErrors(
  err: ApiError | FieldErrorSource | null | undefined,
): Record<string, string> {
  if (!err) return {}
  const fallback = (err.message ?? '').trim()
  const raw: unknown = err.fields
  const out: Record<string, string> = {}

  if (Array.isArray(raw)) {
    for (const key of raw) {
      if (typeof key === 'string' && key) out[key] = fallback
    }
    return out
  }

  if (raw && typeof raw === 'object') {
    for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
      if (!key) continue
      out[key] = typeof value === 'string' && value.trim() ? value : fallback
    }
  }
  return out
}
