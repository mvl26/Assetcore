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
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const pushSpy = vi.fn().mockResolvedValue(undefined)
// Vòng 12: route.query.mode='manual' (deep-link từ QrResolveView 'Nhập mã thủ
// công') → QRScanView focus NGAY ô nhập tay. Mock useRoute với query mutable.
const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
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

import QRScanView from '@/views/system/QRScanView.vue'

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
    routeQuery.value = {}
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

  // Regression guard (factory vòng 6): extractToken() trim @QRScanView.vue:45 là
  // defense-in-depth lớp 1 song song với BE strip SSoT. KHOÁ hành vi: token thô
  // kèm khoảng trắng đầu/cuối → push QrDeepLink với token ĐÃ TRIM (KHÔNG còn
  // whitespace) → resolver/BE nhận token sạch. KHÔNG xoá trim FE.
  it('token thô kèm whitespace đầu/cuối → trim → push QrDeepLink với token đã trim (defense lớp 1)', async () => {
    await typeAndScan(`  ${TOKEN}  `)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: TOKEN },
    })
  })

  it('token thô kèm trailing newline (artifact tem nhiệt) → trim → push QrDeepLink token sạch', async () => {
    await typeAndScan(`${TOKEN}\n`)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: TOKEN },
    })
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
    routeQuery.value = {}
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

// Vòng 12 — auto-focus ô nhập tay khi mở từ QrResolveView 'Nhập mã thủ công'
// (route.query.mode==='manual'). Mục tiêu: user camera-hỏng gõ mã được NGAY,
// KHÔNG phụ thuộc camera có chiếm focus hay không. Đường quét thường (KHÔNG mode)
// GIỮ NGUYÊN: chỉ auto-focus khi activeElement===body (không cướp focus khi quét).
describe('QRScanView — auto-focus ô nhập tay khi mode=manual (Vòng 12)', () => {
  // Phần tử ngoài để chiếm focus → activeElement KHÁC body (mô phỏng camera/UI
  // khác đang giữ focus). Spy focus() trên prototype để bắt lời gọi trên ref input.
  let decoy: HTMLButtonElement
  let focusSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    pushSpy.mockClear()
    startSpy.mockClear()
    stopSpy.mockClear()
    lastOnDetect = null
    supportedFlag = true
    errorRef.value = ''
    activeRef.value = false
    startingRef.value = false
    routeQuery.value = {}
    // Decoy giữ focus → document.activeElement !== document.body.
    decoy = document.createElement('button')
    document.body.appendChild(decoy)
    decoy.focus()
    // Spy focus() — KHÔNG thực thi focus thật (giữ activeElement = decoy ổn định).
    focusSpy = vi.spyOn(HTMLInputElement.prototype, 'focus').mockImplementation(() => {})
  })

  afterEach(() => {
    focusSpy.mockRestore()
    decoy.remove()
  })

  it('mode=manual → focus() ô nhập tay ĐƯỢC gọi sau nextTick (dù activeElement KHÔNG phải body)', async () => {
    routeQuery.value = { mode: 'manual' }
    expect(document.activeElement).not.toBe(document.body)
    const w = mount(QRScanView, { attachTo: document.body })
    await nextTick()
    await nextTick()
    expect(focusSpy).toHaveBeenCalled()
    w.unmount()
  })

  it('KHÔNG mode + activeElement KHÁC body → focus() KHÔNG bị gọi (chống cướp focus khi quét)', async () => {
    routeQuery.value = {}
    expect(document.activeElement).not.toBe(document.body)
    const w = mount(QRScanView, { attachTo: document.body })
    await nextTick()
    await nextTick()
    expect(focusSpy).not.toHaveBeenCalled()
    w.unmount()
  })

  it('parity: mode=manual → nhập mã hợp lệ + submit vẫn push QrDeepLink (KHÔNG phá luồng submit)', async () => {
    routeQuery.value = { mode: 'manual' }
    const w = mount(QRScanView, { attachTo: document.body })
    await nextTick()
    await w.find('input#qr-code-input').setValue(TOKEN)
    await w.find('[data-test="manual-submit"]').trigger('click')
    await flushPromises()
    expect(pushSpy).toHaveBeenCalledWith({ name: 'QrDeepLink', params: { token: TOKEN } })
    w.unmount()
  })
})

// Vòng 29 — percent-decode SEGMENT trích từ /a/<seg> (paste/scan path).
// Bất đối xứng đã bịt: nav URL trực tiếp /a/:token được vue-router AUTO decode
// route.params (đúng), nhưng đường paste/scan→extractToken KHÔNG decode → segment
// percent-encoded (vd %2D do app nhắn tin / trình duyệt encode path tem) chảy
// verbatim vào router.push({params:{token}}) → resolveQrToken nhận token-encoded
// KHÔNG khớp token-decoded trong DB → 404 GIẢ cho deep-link HỢP LỆ.
// FIX: decode an toàn CHỈ segment trích TỪ /a/<seg> (malformed % → giữ raw, KHÔNG
// throw, KHÔNG trang trắng); nhánh token-thô-gõ-tay KHÔNG blanket-decode.
describe('percent-decode token segment (Vòng 29)', () => {
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
    routeQuery.value = {}
  })

  // TC1 (assert-chính, RED trước fix): paste URL tuyệt đối có %2D → decode '-'.
  it('TC1: paste URL tuyệt đối có %2D → push token ĐÃ DECODE (-)', async () => {
    await typeAndScan('http://host/a/AanTF%2D3HT9K3dFyWyaZLNw')
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: 'AanTF-3HT9K3dFyWyaZLNw' },
    })
  })

  // TC2 (AC2): path tương đối '/a/<seg>' decode CÙNG SSoT 1 đường, không fork
  // URL-tuyệt-đối vs path.
  it('TC2: path tương đối /a/<seg> có %2D → decode (-) cùng SSoT', async () => {
    await typeAndScan('/a/AanTF%2D3HT9')
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: 'AanTF-3HT9' },
    })
  })

  // TC3 (parity AC3): token đường paste/scan == token mà vue-router tự decode khi
  // nav trực tiếp /a/<seg> (mô phỏng = decodeURIComponent(seg)). 2 đường HỘI TỤ.
  it('TC3: parity — token (đường paste) == decodeURIComponent(seg) (vue-router nav trực tiếp)', async () => {
    const seg = 'AanTF%2D3HT9K3dFyWyaZLNw'
    // vue-router auto-decode route.params cho nav trực tiếp /a/:token:
    const routerDecoded = decodeURIComponent(seg)
    await typeAndScan(`http://host/a/${seg}`)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: routerDecoded },
    })
  })

  // TC4 (no-regress AC4): TOKEN URL-safe thuần (KHÔNG '%') qua URL + raw + camera →
  // push token y nguyên (decode idempotent trên chuỗi không-%).
  it('TC4: no-regress — token URL-safe thuần (không %) qua URL/raw/camera KHÔNG đổi', async () => {
    // URL tuyệt đối
    await typeAndScan(`http://host/a/${TOKEN}`)
    expect(pushSpy).toHaveBeenLastCalledWith({ name: 'QrDeepLink', params: { token: TOKEN } })
    // raw-typed
    pushSpy.mockClear()
    await typeAndScan(TOKEN)
    expect(pushSpy).toHaveBeenLastCalledWith({ name: 'QrDeepLink', params: { token: TOKEN } })
    // camera
    pushSpy.mockClear()
    const w = mount(QRScanView)
    await w.find('[data-test="camera-toggle"]').trigger('click')
    await flushPromises()
    lastOnDetect!(`http://host/a/${TOKEN}`)
    await flushPromises()
    expect(pushSpy).toHaveBeenLastCalledWith({ name: 'QrDeepLink', params: { token: TOKEN } })
  })

  // TC5 (AC5 malformed): percent hỏng → decodeURIComponent ném URIError → CATCH →
  // giữ NGUYÊN segment thô → vẫn push (resolver tự xử 404). KHÔNG throw/trang trắng.
  it('TC5: malformed percent (%ZZ) → KHÔNG throw, giữ segment thô, VẪN push', async () => {
    await typeAndScan('http://host/a/AanTF%ZZ99')
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: 'AanTF%ZZ99' },
    })
    // assert-chính: pushSpy ĐÃ gọi (không no-op nuốt token / không uncaught).
    expect(pushSpy).toHaveBeenCalledTimes(1)
  })

  // TC6 (AC6 raw-typed KHÔNG decode): input KHÔNG phải URL/không match /a/ → KHÔNG
  // blanket-decode. 'A%2DB' gõ tay giữ NGUYÊN (literal token, % không có semantics).
  it('TC6: raw-typed A%2DB (không match /a/) → giữ NGUYÊN, KHÔNG decode thành A-B', async () => {
    await typeAndScan('A%2DB')
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: 'A%2DB' },
    })
  })

  // TC7 (AC7 trim+decode): whitespace ngoài + encode trong → trim TRƯỚC, decode SAU.
  it('TC7: "  http://host/a/AanTF%2D3HT9  " → trim ngoài + decode trong → AanTF-3HT9', async () => {
    await typeAndScan('  http://host/a/AanTF%2D3HT9  ')
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: 'AanTF-3HT9' },
    })
  })

  // TC8 (AC8 camera): onScanned dùng CHUNG extractToken → quét QR ảnh encode %2D
  // cũng decode đúng + stop() (1 đường, không fork).
  it('TC8: camera onScanned URL có %2D → decode (-) + stop()', async () => {
    const w = mount(QRScanView)
    await w.find('[data-test="camera-toggle"]').trigger('click')
    await flushPromises()
    expect(lastOnDetect).toBeTypeOf('function')
    lastOnDetect!('http://host/a/AanTF%2D3HT9')
    await flushPromises()
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'QrDeepLink',
      params: { token: 'AanTF-3HT9' },
    })
    expect(stopSpy).toHaveBeenCalled()
  })

  // GUARD revert-proof (LL-TEST-26): nguồn extractToken PHẢI gọi safeDecode trên
  // segment trích từ /a/<seg> (KHÔNG return m[1] trần). Xoá lời gọi safeDecode →
  // TC1/TC2/TC3/TC8 ĐỎ; khôi phục → xanh (guard còn răng, không tautology).
  it('GUARD: extractToken decode segment qua safeDecode (KHÔNG return m[1] trần)', () => {
    const src = readFileSync(resolve(__dirname, '..', 'QRScanView.vue'), 'utf-8')
    // Strip comment để không false-match wording trong giải thích.
    const code = src
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .split('\n')
      .map((l) => l.replace(/\/\/.*$/, ''))
      .join('\n')
    // helper safeDecode tồn tại (decodeURIComponent + try/catch giữ raw).
    expect(code).toContain('decodeURIComponent')
    expect(code).toMatch(/function\s+safeDecode/)
    // segment-từ-URL phải đi qua safeDecode — KHÔNG `return m[1]` trần.
    expect(code).toMatch(/return\s+safeDecode\(\s*m\[1\]\s*\)/)
    expect(code).not.toMatch(/return\s+m\[1\]\s*$/m)
  })
})
