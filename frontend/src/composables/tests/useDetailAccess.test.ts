// Copyright (c) 2026, AssetCore Team
// TDD — CR-74: handler DÙNG CHUNG cho lỗi nạp bản ghi chi tiết (403 in-envelope).
//
// Vì sao test ở đây (không nhân 4 bản): 4 màn detail (PM/CM/Hiệu chuẩn/Sự cố) dùng
// CÙNG `useDetailAccess` + `DetailLoadError`. Sai ở đây = sai cả 4 màn ⇒ khoá 1 chỗ.
//
// Hợp đồng khoá lại:
//   • FORBIDDEN (code hoặc http_status 403) → kind='forbidden', blocked=true,
//     message = NGUYÊN VĂN server (KHÔNG 'Lỗi không xác định');
//   • 404 → 'notfound'; mạng/500 → 'unknown'; không lỗi → '' (blocked=false);
//   • `DetailLoadError` kind='forbidden' → hiện message server + lý do VI, KHÔNG có
//     nút "Thử lại" (quyền không đổi khi bấm lại), VẪN có lối thoát về danh sách.
import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { mount } from '@vue/test-utils'
import { ApiError, ErrorCode, isForbiddenError, loadErrorKind } from '@/api/errors'
import { useDetailAccess, ACCESS_DENIED_HINT } from '@/composables/useDetailAccess'
import DetailLoadError from '@/components/common/DetailLoadError.vue'

const SERVER_MSG = 'Bạn không có quyền thực hiện hành động này.'

function forbiddenErr(): ApiError {
  return new ApiError(SERVER_MSG, {
    code: ErrorCode.FORBIDDEN,
    httpStatus: 403,
    messageCode: 'AUTH-403',
    title: 'Không đủ quyền',
    severity: 'warning',
  })
}

describe('CR-74 · phân loại lỗi nạp (api/errors.ts)', () => {
  it('403 in-envelope → kind "forbidden" (KHÔNG gộp vào "unknown")', () => {
    expect(loadErrorKind(forbiddenErr())).toBe('forbidden')
    expect(isForbiddenError(forbiddenErr())).toBe(true)
  })

  it('403 chỉ có http_status (BE không gửi code) vẫn nhận diện được', () => {
    const e = new ApiError('Không đủ quyền', { httpStatus: 403 })
    expect(loadErrorKind(e)).toBe('forbidden')
  })

  it('404 → "notfound" (ưu tiên trước forbidden — chỉ tới được khi ĐÃ đủ quyền đọc)', () => {
    const e = new ApiError('Không tìm thấy phiếu', { code: ErrorCode.NOT_FOUND, httpStatus: 404 })
    expect(loadErrorKind(e)).toBe('notfound')
    expect(isForbiddenError(e)).toBe(false)
  })

  it('lỗi mạng/500 → "unknown" (giữ nguyên hành vi cũ)', () => {
    expect(loadErrorKind(new Error('Network Error'))).toBe('unknown')
    expect(loadErrorKind(new ApiError('Có lỗi máy chủ', { code: ErrorCode.INTERNAL_ERROR, httpStatus: 500 })))
      .toBe('unknown')
  })
})

describe('CR-74 · useDetailAccess (state dùng chung 4 màn detail)', () => {
  it('403 → blocked + isForbidden + message NGUYÊN VĂN server', () => {
    const e = ref<unknown>(forbiddenErr())
    const a = useDetailAccess(() => e.value)
    expect(a.kind.value).toBe('forbidden')
    expect(a.blocked.value).toBe(true)
    expect(a.isForbidden.value).toBe(true)
    expect(a.message.value).toBe(SERVER_MSG)
    expect(a.message.value).not.toContain('Lỗi không xác định')
  })

  it('không lỗi → kind rỗng, blocked=false (không chặn nhầm happy-path)', () => {
    const e = ref<unknown>(null)
    const a = useDetailAccess(() => e.value)
    expect(a.kind.value).toBe('')
    expect(a.blocked.value).toBe(false)
    expect(a.isForbidden.value).toBe(false)
    expect(a.message.value).toBe('')
  })

  it('phản ứng theo nguồn: nạp lại thành công → hết blocked', () => {
    const e = ref<unknown>(forbiddenErr())
    const a = useDetailAccess(() => e.value)
    expect(a.blocked.value).toBe(true)
    e.value = null
    expect(a.blocked.value).toBe(false)
    expect(a.kind.value).toBe('')
  })
})

describe('CR-74 · DetailLoadError nhánh "forbidden"', () => {
  function mountForbidden(message?: string) {
    return mount(DetailLoadError, {
      props: {
        kind: 'forbidden' as const,
        entityLabel: 'lệnh sửa chữa',
        recordId: 'WO-RP-2026-00099',
        message,
        backLabel: 'Về danh sách sửa chữa',
      },
    })
  }

  it('hiện message THẬT của server + lý do VI, KHÔNG có nút "Thử lại"', async () => {
    const w = mountForbidden(SERVER_MSG)
    expect(w.text()).toContain(SERVER_MSG)
    expect(w.text()).toContain(ACCESS_DENIED_HINT)
    expect(w.text()).not.toContain('Thử lại')
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
  })

  it('server không gửi message → fallback VI theo nhãn (KHÔNG để trống/"Lỗi không xác định")', () => {
    const w = mountForbidden(undefined)
    expect(w.text()).toContain('Bạn không có quyền xem lệnh sửa chữa này.')
    expect(w.text()).not.toContain('Lỗi không xác định')
  })

  it('vẫn có lối thoát về danh sách (không dead-end)', async () => {
    const w = mountForbidden(SERVER_MSG)
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách sửa chữa'))!
    await back.trigger('click')
    expect(w.emitted('back')).toHaveLength(1)
  })
})
