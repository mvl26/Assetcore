// TDD — P1 hợp nhất đường quét: /qr-scan nhập-tay PHẢI đi qua resolver QrDeepLink
// (KHÔNG còn router.push('/assets/<token>') coi token = asset name).
//   • token thô (AanTF-…) → router.push({name:'QrDeepLink', params:{token}}).
//   • paste URL deep-link đầy đủ http(s)://host/a/<token> → trích <token> → push QrDeepLink.
//   • input rỗng → no-op (không gọi API, không điều hướng).
//   • regression guard: KHÔNG BAO GIỜ push('/assets/<token>') (coi token = asset id).
// A5 (mở rộng) — quét bằng camera dùng useQrCameraScanner (mock):
//   • onDetect(URL/token) → extractToken → push QrDeepLink + stop() (camera tắt).
//   • môi trường không hỗ trợ → nút camera ẩn/disabled hoặc hint VI unsupported; nhập tay vẫn render.
//   • unmount khi camera bật → stop() được gọi (no leak).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const pushSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
}))

// getBarcodeLookup KHÔNG được gọi cho đường QR-token (đường barcode IMM-04 tách bạch).
const barcodeLookupSpy = vi.fn()
vi.mock('@/api/imm04', () => ({
  getBarcodeLookup: (code: string) => barcodeLookupSpy(code),
}))

// Mock composable camera để test thuần view: bắt onDetect callback + spy start/stop.
let lastOnDetect: ((raw: string) => void) | null = null
const startSpy = vi.fn().mockResolvedValue(undefined)
const stopSpy = vi.fn()
let supportedFlag = true
// Dùng ref THẬT để mutation trong test trigger re-render (giống composable thật).
const errorRef = ref<string>('')
const activeRef = ref<boolean>(false)
const startingRef = ref<boolean>(false)

vi.mock('@/composables/useQrCameraScanner', () => ({
  useQrCameraScanner: (opts: { onDetect: (raw: string) => void }) => {
    lastOnDetect = opts.onDetect
    return {
      error: errorRef,
      active: activeRef,
      starting: startingRef,
      isSupported: () => supportedFlag,
      start: startSpy,
      stop: stopSpy,
    }
  },
}))

import QRScanView from './QRScanView.vue'

const TOKEN = 'AanTF-3HT9K3dFyWyaZLNw'

async function typeAndScan(value: string) {
  const w = mount(QRScanView)
  const input = w.find('input#qr-code-input')
  await input.setValue(value)
  // Nút submit đường nhập tay (data-test) — A5 thêm nút "Quét bằng camera" cũng
  // .btn-primary nên target chính xác bằng data-test để không nhầm.
  await w.find('[data-test="manual-submit"]').trigger('click')
  await flushPromises()
  return w
}

describe('QRScanView — hợp nhất đường quét qua resolver QrDeepLink', () => {
  beforeEach(() => {
    pushSpy.mockClear()
    barcodeLookupSpy.mockReset()
    startSpy.mockClear()
    stopSpy.mockClear()
    lastOnDetect = null
    supportedFlag = true
    errorRef.value = ''
    activeRef.value = false
    startingRef.value = false
  })

  it('token thô đi qua resolver (push QrDeepLink params.token)', async () => {
    await typeAndScan(TOKEN)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: TOKEN },
    })
  })

  it('paste URL deep-link đầy đủ → trích token → push QrDeepLink', async () => {
    await typeAndScan(`http://host/a/${TOKEN}`)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: TOKEN },
    })
  })

  it('paste URL https + query/hash → vẫn trích đúng token', async () => {
    await typeAndScan(`https://benhvien.example.vn/a/${TOKEN}?utm=x#top`)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: TOKEN },
    })
  })

  // B (deep-link host công khai) — khi BE đổi base-URL sang host công khai
  // (site_config `assetcore_qr_base_url`, vd https://htm.benhvien.vn), tem in ra
  // chứa URL host công khai. extractToken() PHẢI tách token y nguyên bất kể host
  // — regex `/\/a\/([^/?#]+)/` là host-agnostic, FE KHÔNG hardcode host nào.
  it('host công khai mới https://htm.benhvien.vn/a/<token> → trích token y nguyên', async () => {
    await typeAndScan(`https://htm.benhvien.vn/a/${TOKEN}`)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: TOKEN },
    })
  })

  // Regression: host nội bộ cũ (get_url fallback dev/test → http://miyano/a/...)
  // vẫn match — đổi base-URL phía BE KHÔNG hồi quy đường quét host nội bộ.
  it('regression host nội bộ cũ http://miyano/a/<token> → vẫn trích đúng token', async () => {
    await typeAndScan(`http://miyano/a/${TOKEN}`)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: TOKEN },
    })
  })

  it('input rỗng → no-op (không gọi API, không điều hướng)', async () => {
    const w = mount(QRScanView)
    await w.find('input#qr-code-input').setValue('   ')
    await w.find('[data-test="manual-submit"]').trigger('click')
    await flushPromises()
    expect(pushSpy).not.toHaveBeenCalled()
    expect(barcodeLookupSpy).not.toHaveBeenCalled()
  })

  it('regression: KHÔNG push("/assets/<token>") (token KHÔNG phải asset id)', async () => {
    await typeAndScan(TOKEN)
    // KHÔNG có lời gọi push dạng chuỗi '/assets/<token>'.
    for (const call of pushSpy.mock.calls) {
      expect(call[0]).not.toBe(`/assets/${TOKEN}`)
      if (typeof call[0] === 'string') {
        expect(call[0].startsWith('/assets/')).toBe(false)
      }
    }
  })
})

describe('QRScanView — A5 quét bằng camera (useQrCameraScanner)', () => {
  beforeEach(() => {
    pushSpy.mockClear()
    barcodeLookupSpy.mockReset()
    startSpy.mockClear()
    stopSpy.mockClear()
    lastOnDetect = null
    supportedFlag = true
    errorRef.value = ''
    activeRef.value = false
    startingRef.value = false
  })

  it('môi trường HỖ TRỢ → có nút "Quét bằng camera"; nhập tay vẫn render', () => {
    supportedFlag = true
    const w = mount(QRScanView)
    expect(w.find('[data-test="camera-toggle"]').exists()).toBe(true)
    expect(w.find('input#qr-code-input').exists()).toBe(true)
  })

  // A5+(B): trên iOS Safari / Firefox (KHÔNG BarcodeDetector nhưng có getUserMedia)
  // isSupported() giờ trả true (fallback jsQR) → nút camera HIỆN, KHÔNG còn rơi vào
  // nhánh camera-unsupported. Đường quét vẫn 1 (onScanned → extractToken → QrDeepLink).
  it('fallback (isSupported() true) → nút camera HIỆN, KHÔNG hiện hint unsupported; quét → push QrDeepLink', async () => {
    supportedFlag = true
    const w = mount(QRScanView)
    expect(w.find('[data-test="camera-toggle"]').exists()).toBe(true)
    expect(w.find('[data-test="camera-unsupported"]').exists()).toBe(false)
    await w.find('[data-test="camera-toggle"]').trigger('click')
    await flushPromises()
    lastOnDetect!(`http://host/a/${TOKEN}`)
    await flushPromises()
    expect(pushSpy).toHaveBeenCalledWith({ name: 'QrDeepLink', params: { token: TOKEN } })
    expect(stopSpy).toHaveBeenCalled()
  })

  it('môi trường KHÔNG hỗ trợ → ẩn/disable nút camera + hint VI unsupported (role=alert); nhập tay vẫn render', () => {
    supportedFlag = false
    const w = mount(QRScanView)
    const toggle = w.find('[data-test="camera-toggle"]')
    // Ẩn HOẶC disabled — chấp nhận cả hai.
    const hiddenOrDisabled =
      !toggle.exists() || (toggle.element as HTMLButtonElement).disabled
    expect(hiddenOrDisabled).toBe(true)
    const hint = w.find('[data-test="camera-unsupported"]')
    expect(hint.exists()).toBe(true)
    expect(hint.attributes('role')).toBe('alert')
    expect(hint.text()).toContain('không hỗ trợ quét bằng camera')
    // Fallback nhập tay vẫn dùng được.
    expect(w.find('input#qr-code-input').exists()).toBe(true)
  })

  it('bấm "Quét bằng camera" → gọi scanner.start(video)', async () => {
    const w = mount(QRScanView)
    await w.find('[data-test="camera-toggle"]').trigger('click')
    await flushPromises()
    expect(startSpy).toHaveBeenCalledTimes(1)
    // tham số đầu là phần tử <video>
    const arg = startSpy.mock.calls[0][0] as HTMLElement
    expect(arg?.tagName).toBe('VIDEO')
  })

  it('onDetect URL deep-link http://host/a/<TOKEN> → extractToken → push QrDeepLink + stop()', async () => {
    const w = mount(QRScanView)
    await w.find('[data-test="camera-toggle"]').trigger('click')
    await flushPromises()
    expect(lastOnDetect).toBeTypeOf('function')
    lastOnDetect!(`http://host/a/${TOKEN}`)
    await flushPromises()
    expect(pushSpy).toHaveBeenCalledWith({ name: 'QrDeepLink', params: { token: TOKEN } })
    expect(stopSpy).toHaveBeenCalled()
  })

  it('onDetect token thô <TOKEN> → push QrDeepLink params.token=TOKEN', async () => {
    const w = mount(QRScanView)
    await w.find('[data-test="camera-toggle"]').trigger('click')
    await flushPromises()
    lastOnDetect!(TOKEN)
    await flushPromises()
    expect(pushSpy).toHaveBeenCalledWith({ name: 'QrDeepLink', params: { token: TOKEN } })
  })

  it('onDetect chuỗi không trích được token → KHÔNG push, KHÔNG stop (tiếp tục quét)', async () => {
    const w = mount(QRScanView)
    await w.find('[data-test="camera-toggle"]').trigger('click')
    await flushPromises()
    stopSpy.mockClear()
    lastOnDetect!('https://host/no-token-here')
    await flushPromises()
    expect(pushSpy).not.toHaveBeenCalled()
    expect(stopSpy).not.toHaveBeenCalled()
  })

  it('regression A5: quét camera KHÔNG bao giờ push("/assets/<token>")', async () => {
    const w = mount(QRScanView)
    await w.find('[data-test="camera-toggle"]').trigger('click')
    await flushPromises()
    lastOnDetect!(TOKEN)
    await flushPromises()
    for (const call of pushSpy.mock.calls) {
      if (typeof call[0] === 'string') {
        expect(call[0].startsWith('/assets/')).toBe(false)
      }
    }
  })

  it('cameraError=denied → hiện thông báo VI role=alert; ô nhập tay vẫn render', async () => {
    const w = mount(QRScanView)
    await w.find('[data-test="camera-toggle"]').trigger('click')
    errorRef.value = 'denied'
    await flushPromises()
    const alert = w.find('[data-test="camera-error"]')
    expect(alert.exists()).toBe(true)
    expect(alert.attributes('role')).toBe('alert')
    expect(alert.text().length).toBeGreaterThan(0)
    expect(w.find('input#qr-code-input').exists()).toBe(true)
  })

  it('unmount khi camera bật → stop() được gọi (cleanup, no camera leak)', async () => {
    const w = mount(QRScanView)
    await w.find('[data-test="camera-toggle"]').trigger('click')
    await flushPromises()
    activeRef.value = true
    stopSpy.mockClear()
    w.unmount()
    expect(stopSpy).toHaveBeenCalled()
  })
})
