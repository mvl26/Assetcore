// Copyright (c) 2026, AssetCore Team
// useApi — wrap call API với toast + loading + field-error chuẩn cho form.
//
// Pattern khuyến nghị cho mọi view:
//
//   const api = useApi()
//
//   await api.run(() => createPmSchedule(data), {
//     successMessage: 'Đã tạo lịch PM',
//     onFieldError: (fields) => Object.assign(formErrors, fields),
//   })
//
// - Tự bật toast: success (xanh), business (vàng), error (đỏ).
// - Trả về `null` khi lỗi → caller chỉ cần check `if (result)` để branch happy path.
// - 401/403 đã được axios redirect; ở đây không spam toast cho 2 case đó.

import { ref } from 'vue'
import { useToast } from './useToast'
import { ApiError, ErrorCode, toApiError } from '@/api/errors'

export interface RunOptions {
  /** Toast hiện khi success (bỏ qua nếu undefined). */
  successMessage?: string
  /** Toast hiện khi error — override message tự động. */
  errorMessage?: string
  /** Callback khi BE trả `fields` (lỗi field-level). */
  onFieldError?: (fields: Record<string, string>) => void
  /** Tắt toast error (dùng khi caller tự render lỗi inline). */
  silentError?: boolean
  /** Tắt toast success. */
  silentSuccess?: boolean
}

export function useApi() {
  const toast = useToast()
  const loading = ref(false)
  const lastError = ref<ApiError | null>(null)

  async function run<T>(fn: () => Promise<T>, opts: RunOptions = {}): Promise<T | null> {
    loading.value = true
    lastError.value = null
    try {
      const result = await fn()
      if (opts.successMessage && !opts.silentSuccess) {
        toast.success(opts.successMessage)
      }
      return result
    } catch (e: unknown) {
      const err = toApiError(e)
      lastError.value = err

      if (err.fields && opts.onFieldError) {
        opts.onFieldError(err.fields)
      }

      if (!opts.silentError) {
        // 401/403 đã được axios redirect — không spam toast.
        if (err.code === ErrorCode.UNAUTHORIZED || err.code === ErrorCode.FORBIDDEN) {
          return null
        }
        const msg = opts.errorMessage ?? err.message
        if (err.isBusinessError) toast.warning(msg)
        else toast.error(msg)
      }
      return null
    } finally {
      loading.value = false
    }
  }

  return { run, loading, lastError }
}
