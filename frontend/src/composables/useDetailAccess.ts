// Copyright (c) 2026, AssetCore Team
// useDetailAccess — HANDLER DÙNG CHUNG cho trạng thái "nạp bản ghi chi tiết thất bại"
// trên mọi màn *DetailView (CR-74).
//
// VÌ SAO 1 CHỖ, KHÔNG 4 BẢN: 4 GET-detail mobile/web (imm08.get_pm_work_order,
// imm09.get_repair_work_order, imm11.get_calibration, imm12.get_incident) nay đi qua
// CÙNG 1 predicate quyền-đọc ở BE và trả CÙNG 1 envelope
//   HTTP-200 + {success:false, code:'FORBIDDEN', http_status:403, error:'<thông điệp VI>'}
// (Decision-B). FE phải route-by-VALUE (`body.success`), KHÔNG route-by-status-line.
//
// HAI LOẠI 403 — KHÔNG ĐƯỢC LẪN:
//   1. dispatcher-403 (status-line, Frappe re-auth)  → `api/axios.ts::handle403`
//      ping `layout.ping_session`; phiên chết ⇒ redirect login. ĐÂY mới là "hết phiên".
//   2. in-envelope FORBIDDEN (HTTP-200, CR-74)       → composable NÀY.
//      Người dùng VẪN đăng nhập hợp lệ ⇒ **KHÔNG logout, KHÔNG router.push('/login')**,
//      chỉ hiện message thật của server + ẩn toàn bộ CTA (chống dead-control).
import { computed, type ComputedRef } from 'vue'
import { loadErrorKind, toApiError, type DetailLoadKind } from '@/api/errors'

/**
 * Lý do VI hiển thị dưới thông điệp 403 + dùng làm tooltip cho CTA bị khoá.
 * SSoT copy — mọi màn chi tiết dùng CHUNG chuỗi này (tránh lệch chữ giữa module).
 */
export const ACCESS_DENIED_HINT =
  'Phiếu chưa được giao cho bạn hoặc bạn không có quyền xem. '
  + 'Liên hệ quản lý bộ phận nếu cần truy cập.'

export interface DetailAccessState {
  /** '' = nạp OK; còn lại = khoá render empty-state của `DetailLoadError`. */
  kind: ComputedRef<'' | DetailLoadKind>
  /** True khi BE từ chối vì thiếu quyền đọc (403 in-envelope) — CTA phải bị ẩn. */
  isForbidden: ComputedRef<boolean>
  /** True khi bản ghi KHÔNG khả dụng (403/404/lỗi khác) ⇒ 0 CTA được render. */
  blocked: ComputedRef<boolean>
  /** Message THẬT từ envelope (không bịa "Lỗi không xác định" khi server đã nói rõ). */
  message: ComputedRef<string>
}

/**
 * @param source getter trả lỗi nạp hiện tại (ApiError/Error/null). Truyền getter —
 *        KHÔNG truyền giá trị — để composable phản ứng theo store/ref của view.
 *
 * ```ts
 * const access = useDetailAccess(() => (store.currentWO ? null : store.lastApiError))
 * // template: <DetailLoadError v-else-if="access.blocked.value" :kind="access.kind.value" ... />
 * ```
 */
export function useDetailAccess(source: () => unknown): DetailAccessState {
  const kind = computed<'' | DetailLoadKind>(() => {
    const e = source()
    return e ? loadErrorKind(e) : ''
  })
  const isForbidden = computed(() => kind.value === 'forbidden')
  const blocked = computed(() => kind.value !== '')
  const message = computed(() => {
    const e = source()
    return e ? toApiError(e).message : ''
  })
  return { kind, isForbidden, blocked, message }
}
