// Copyright (c) 2026, AssetCore Team — usePdfLabelPrint composable (PDF print iframe, TDD)
//
// Đảm bảo: createObjectURL gọi 1 lần · iframe tạo + chèn DOM · contentWindow.print()
// gọi · onafterprint → onAfterPrint(names) + revokeObjectURL gọi (no leak) · iframe
// gỡ khỏi DOM · lỗi fetcher → error set + trả null (KHÔNG throw chưa-bắt).
import { describe, it, expect, vi, beforeAll, afterAll, beforeEach, afterEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { usePdfLabelPrint } from '@/composables/usePdfLabelPrint'
import { ApiError, ErrorCode } from '@/api/errors'

// Host component để mount composable (onUnmounted hoạt động).
function makeHost(fetcher: (names: string[]) => Promise<Blob>) {
  let exposed!: ReturnType<typeof usePdfLabelPrint>
  const Host = defineComponent({
    setup() { exposed = usePdfLabelPrint(fetcher); return () => h('div') },
  })
  const wrapper = mount(Host)
  return { wrapper, get api() { return exposed } }
}

// jsdom 29 cố navigate <iframe> khi `src` (blob:) được set → tạo document
// opaque-origin → truy cập localStorage ném SecurityError (vitest 4 fail test khi
// unhandled). Production ĐÚNG (browser thật navigate blob: bình thường); trong test
// ta chỉ LƯU giá trị src (không set content-attribute) để jsdom KHÔNG navigate.
let _origIframeSrc: PropertyDescriptor | undefined
beforeAll(() => {
  _origIframeSrc = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'src')
  Object.defineProperty(HTMLIFrameElement.prototype, 'src', {
    configurable: true,
    get() { return (this as unknown as { __src?: string }).__src ?? '' },
    set(v: string) { (this as unknown as { __src?: string }).__src = v },
  })
})
afterAll(() => {
  if (_origIframeSrc) Object.defineProperty(HTMLIFrameElement.prototype, 'src', _origIframeSrc)
})

let createSpy: ReturnType<typeof vi.fn>
let revokeSpy: ReturnType<typeof vi.fn>
let printSpy: ReturnType<typeof vi.fn>

beforeEach(() => {
  createSpy = vi.fn(() => 'blob:mock-url-123')
  revokeSpy = vi.fn()
  printSpy = vi.fn()
  // @ts-expect-error jsdom URL stub
  globalThis.URL.createObjectURL = createSpy
  // @ts-expect-error jsdom URL stub
  globalThis.URL.revokeObjectURL = revokeSpy
})

afterEach(() => {
  document.querySelectorAll('iframe').forEach((f) => f.remove())
})

// Khi iframe.src set → jsdom KHÔNG tự fire onload với blob: → mô phỏng thủ công:
// gắn contentWindow.print spy + gọi onload đồng bộ.
function fireIframeLoad(): HTMLIFrameElement {
  const iframe = document.body.querySelector('iframe') as HTMLIFrameElement
  expect(iframe).toBeTruthy()
  // Stub contentWindow (jsdom có, nhưng đảm bảo print/focus là spy điều khiển được).
  Object.defineProperty(iframe, 'contentWindow', {
    configurable: true,
    value: { print: printSpy, focus: vi.fn(), onafterprint: null as null | (() => void) },
  })
  iframe.onload?.(new Event('load'))
  return iframe
}

describe('usePdfLabelPrint — luồng in PDF qua iframe ẩn', () => {
  it('printLabels → createObjectURL 1 lần · iframe chèn DOM · contentWindow.print() gọi', async () => {
    const blob = new Blob(['%PDF'], { type: 'application/pdf' })
    const fetcher = vi.fn().mockResolvedValue(blob)
    const { api } = makeHost(fetcher)

    const ret = await api.printLabels(['A1', 'A2'])
    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(fetcher).toHaveBeenCalledWith(['A1', 'A2'])
    expect(ret).toBe(blob)
    // createObjectURL gọi 1 lần với Blob.
    expect(createSpy).toHaveBeenCalledTimes(1)
    expect(createSpy).toHaveBeenCalledWith(blob)
    // previewUrl = Blob URL của CHÍNH PDF (cùng object trả).
    expect(api.previewUrl.value).toBe('blob:mock-url-123')
    // iframe đã chèn vào DOM.
    expect(document.body.querySelector('iframe')).toBeTruthy()

    fireIframeLoad()
    expect(printSpy).toHaveBeenCalledTimes(1)
  })

  it('onafterprint → onAfterPrint(names) gọi + revokeObjectURL + iframe gỡ DOM (no leak)', async () => {
    const blob = new Blob(['%PDF'], { type: 'application/pdf' })
    const onAfter = vi.fn().mockResolvedValue(undefined)
    const { api } = makeHost(() => Promise.resolve(blob))

    await api.printLabels(['A1', 'A2'], { onAfterPrint: onAfter })
    const iframe = fireIframeLoad()
    // Trigger onafterprint (browser fire sau khi hộp thoại in đóng).
    const cw = iframe.contentWindow as unknown as { onafterprint: () => void }
    cw.onafterprint()
    await Promise.resolve() // flush microtask (onAfterPrint async → finally revoke)
    await Promise.resolve()

    expect(onAfter).toHaveBeenCalledTimes(1)
    expect(onAfter).toHaveBeenCalledWith(['A1', 'A2'])
    expect(revokeSpy).toHaveBeenCalledWith('blob:mock-url-123')
    // iframe gỡ khỏi DOM + previewUrl reset.
    expect(document.body.querySelector('iframe')).toBeFalsy()
    expect(api.previewUrl.value).toBeNull()
  })

  it('revoke() thủ công → revokeObjectURL + gỡ iframe (đóng modal exit path)', async () => {
    const blob = new Blob(['%PDF'], { type: 'application/pdf' })
    const { api } = makeHost(() => Promise.resolve(blob))
    await api.printLabels(['A1'])
    fireIframeLoad()
    api.revoke()
    expect(revokeSpy).toHaveBeenCalledWith('blob:mock-url-123')
    expect(document.body.querySelector('iframe')).toBeFalsy()
    expect(api.previewUrl.value).toBeNull()
  })

  it('onUnmounted → revoke (no leak khi rời trang giữa in)', async () => {
    const blob = new Blob(['%PDF'], { type: 'application/pdf' })
    const { wrapper, api } = makeHost(() => Promise.resolve(blob))
    await api.printLabels(['A1'])
    fireIframeLoad()
    wrapper.unmount()
    expect(revokeSpy).toHaveBeenCalledWith('blob:mock-url-123')
    expect(document.body.querySelector('iframe')).toBeFalsy()
  })

  it('fetcher reject (403 ApiError) → error set + trả null + KHÔNG tạo iframe (không in được)', async () => {
    const fetcher = vi.fn().mockRejectedValue(new ApiError('Bạn không có quyền in nhãn.', ErrorCode.FORBIDDEN, 403))
    const { api } = makeHost(fetcher)
    const ret = await api.printLabels(['A1'])
    expect(ret).toBeNull()
    expect(api.error.value).toBeInstanceOf(ApiError)
    expect(api.error.value?.httpStatus).toBe(403)
    // KHÔNG tạo URL / iframe khi fetch lỗi.
    expect(createSpy).not.toHaveBeenCalled()
    expect(document.body.querySelector('iframe')).toBeFalsy()
  })

  it('printLabels([]) rỗng → no-op trả null (KHÔNG gọi fetcher)', async () => {
    const fetcher = vi.fn()
    const { api } = makeHost(fetcher)
    const ret = await api.printLabels([])
    expect(ret).toBeNull()
    expect(fetcher).not.toHaveBeenCalled()
  })
})
