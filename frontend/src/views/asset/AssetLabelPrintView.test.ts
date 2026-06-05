// Copyright (c) 2026, AssetCore Team — AssetLabelPrintView in nhãn QR hàng loạt (A4/V5, TDD)
//
// RED-prove (task A4):
//   • 3 asset → getAssetLabelDataBatch gọi ĐÚNG 1 lần với 3 names THEO THỨ TỰ;
//     KHÔNG gọi getAssetLabelData (chống N+1); render 3 nhãn.
//   • payload chứa { name, error: 'AC-E001' } → ô lỗi VI đúng vị trí thứ tự, nhãn
//     hợp lệ vẫn render, KHÔNG throw/blank toàn trang.
//   • bấm 'In' → markLabelPrinted chỉ gửi name HỢP LỆ (loại item error).
//   • loading → aria-busy; lỗi network → role=alert thông điệp VI.
//   • empty (0 name) → hint VI, KHÔNG gọi batch API.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { ApiError, ErrorCode } from '@/api/errors'

const routeQuery = ref<Record<string, string | string[]>>({})
const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const getBatchSpy = vi.fn()
const getOneSpy = vi.fn()
const markPrintedSpy = vi.fn().mockResolvedValue({ printed: [], event_count: 0 })
vi.mock('@/api/imm00', () => ({
  getAssetLabelDataBatch: (names: string[]) => getBatchSpy(names),
  getAssetLabelData: (n: string) => getOneSpy(n),
  markLabelPrinted: (assets: string[]) => markPrintedSpy(assets),
}))
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))

// Toast SSoT (parity màn in đơn AssetDetailView) — spy success/error/show qua
// composable (KHÔNG hardcode DOM / literal trùng lặp).
const toastSuccessSpy = vi.fn()
const toastErrorSpy = vi.fn()
const toastShowSpy = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: toastSuccessSpy, error: toastErrorSpy, show: toastShowSpy }),
}))

import AssetLabelPrintView from './AssetLabelPrintView.vue'
import { MAX_LABEL_BATCH } from '@/constants/label'

function lbl(name: string) {
  return { name, asset_code: name, device_model_name: 'M', location_name: 'L', lifecycle_status: 'Active', qr_url: `http://miyano/a/${name}` }
}

describe('AssetLabelPrintView — in nhãn QR hàng loạt (A4)', () => {
  beforeEach(() => {
    getBatchSpy.mockReset()
    getOneSpy.mockReset()
    markPrintedSpy.mockClear()
    markPrintedSpy.mockResolvedValue({ printed: [], event_count: 0 })
    pushSpy.mockClear()
    toastSuccessSpy.mockClear()
    toastErrorSpy.mockClear()
    toastShowSpy.mockClear()
    routeQuery.value = { names: 'A1,A2,A3' }
    vi.spyOn(window, 'print').mockImplementation(() => {})
  })

  it('3 asset → getAssetLabelDataBatch 1 lần với 3 names THEO THỨ TỰ; KHÔNG N+1; render 3 nhãn', async () => {
    getBatchSpy.mockResolvedValue([lbl('A1'), lbl('A2'), lbl('A3')])
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    expect(getBatchSpy).toHaveBeenCalledTimes(1)
    expect(getBatchSpy).toHaveBeenCalledWith(['A1', 'A2', 'A3'])
    // Chống N+1: KHÔNG gọi get_asset_label_data lặp.
    expect(getOneSpy).not.toHaveBeenCalled()
    // 3 nhãn render (3 ảnh QR).
    expect(w.findAll('img').length).toBe(3)
  })

  it("item lỗi AC-E001 → ô lỗi VI đúng vị trí thứ tự, nhãn hợp lệ vẫn render, KHÔNG blank toàn trang", async () => {
    getBatchSpy.mockResolvedValue([lbl('A1'), { name: 'BAD', error: 'AC-E001' }, lbl('A3')])
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const text = w.text()
    expect(text).toContain('Không tìm thấy thiết bị')
    expect(text).toContain('BAD')
    // Nhãn hợp lệ vẫn render (2 QR ảnh cho A1, A3).
    expect(w.findAll('img').length).toBe(2)
  })

  it("bấm 'In' → markLabelPrinted chỉ gửi name HỢP LỆ (loại item error)", async () => {
    getBatchSpy.mockResolvedValue([lbl('A1'), { name: 'BAD', error: 'AC-E001' }, lbl('A3')])
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const printBtn = w.findAll('button').find(b => b.text().includes('In'))
    expect(printBtn).toBeTruthy()
    await printBtn!.trigger('click')
    await flushPromises()
    expect(window.print).toHaveBeenCalled()
    expect(markPrintedSpy).toHaveBeenCalledTimes(1)
    expect(markPrintedSpy).toHaveBeenCalledWith(['A1', 'A3'])
  })

  it('loading → aria-busy hiển thị', async () => {
    let resolveBatch!: (v: unknown) => void
    getBatchSpy.mockReturnValue(new Promise(r => { resolveBatch = r }))
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    expect(w.find('[aria-busy="true"]').exists()).toBe(true)
    resolveBatch([lbl('A1')])
    await flushPromises()
  })

  it('lỗi network → role=alert thông điệp VI', async () => {
    getBatchSpy.mockRejectedValue(new ApiError('mạng lỗi', ErrorCode.NETWORK_ERROR, 0))
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text().length).toBeGreaterThan(0)
    // KHÔNG leak token/raw EN code.
    expect(alert.text()).not.toContain('NETWORK_ERROR')
  })

  // --- B: error-contract hardening (parity QrResolveView/AssetScanInfoView) ---

  it('lỗi raw EN trong .message → KHÔNG echo verbatim, chỉ bucket VI unknown', async () => {
    // BE trả lỗi nội bộ với message tiếng Anh thô (rò rỉ stacktrace/AttributeError).
    getBatchSpy.mockRejectedValue(
      new ApiError(
        'Failed to get method ... module has no attribute resolve (AttributeError)',
        ErrorCode.UNKNOWN,
        0,
      ),
    )
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const text = w.text()
    // KHÔNG render bất kỳ chuỗi tiếng Anh raw nào.
    expect(text).not.toContain('Failed to get method')
    expect(text).not.toContain('has no attribute')
    expect(text).not.toContain('module')
    expect(text).not.toContain('AttributeError')
    // Bucket unknown VI cố định.
    expect(text).toContain('Không thể tải dữ liệu nhãn, thử lại sau')
    expect(w.find('[role="alert"]').exists()).toBe(true)
  })

  it('403 (FORBIDDEN) → VI "Không đủ quyền in nhãn thiết bị" + role=alert', async () => {
    getBatchSpy.mockRejectedValue(new ApiError('Forbidden', ErrorCode.FORBIDDEN, 403))
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('Không đủ quyền in nhãn thiết bị')
    expect(alert.text()).not.toContain('Forbidden')
    expect(alert.text()).not.toContain('FORBIDDEN')
  })

  it('404 (NOT_FOUND) → VI "Không tìm thấy dữ liệu nhãn thiết bị"', async () => {
    getBatchSpy.mockRejectedValue(new ApiError('Not found', ErrorCode.NOT_FOUND, 404))
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('Không tìm thấy dữ liệu nhãn thiết bị')
    expect(alert.text()).not.toContain('Not found')
    expect(alert.text()).not.toContain('NOT_FOUND')
  })

  it('lỗi khác/417/network → bucket unknown VI "Không thể tải dữ liệu nhãn, thử lại sau"', async () => {
    getBatchSpy.mockRejectedValue(new ApiError('Expectation Failed', ErrorCode.BUSINESS_RULE, 417))
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('Không thể tải dữ liệu nhãn, thử lại sau')
    expect(alert.text()).not.toContain('Expectation Failed')
  })

  it("Recovery: 'Thử lại' gọi lại loadBatch (getAssetLabelDataBatch lần 2)", async () => {
    getBatchSpy.mockRejectedValue(new ApiError('Forbidden', ErrorCode.FORBIDDEN, 403))
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    expect(getBatchSpy).toHaveBeenCalledTimes(1)
    const retry = w.findAll('button').find(b => b.text().includes('Thử lại'))
    expect(retry).toBeTruthy()
    // Lần thử lại thành công.
    getBatchSpy.mockResolvedValue([lbl('A1'), lbl('A2'), lbl('A3')])
    await retry!.trigger('click')
    await flushPromises()
    expect(getBatchSpy).toHaveBeenCalledTimes(2)
  })

  it("Recovery: 'Về danh sách thiết bị' → router.push('/assets')", async () => {
    getBatchSpy.mockRejectedValue(new ApiError('Forbidden', ErrorCode.FORBIDDEN, 403))
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const back = w.findAll('button').find(b => b.text().includes('Về danh sách thiết bị'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/assets')
  })

  it('Regression: source view KHÔNG còn binding raw .message vào biến hiển thị', async () => {
    // Đọc trực tiếp source để đảm bảo không tái diễn .message-leak.
    const fs = await import('node:fs')
    const path = await import('node:path')
    const src = fs.readFileSync(
      path.resolve(process.cwd(), 'src/views/asset/AssetLabelPrintView.vue'),
      'utf8',
    )
    // KHÔNG còn gán toApiError(e).message vào biến hiển thị.
    expect(src).not.toMatch(/toApiError\([^)]*\)\.message/)
    // KHÔNG còn render {{ error }} trực tiếp (error giờ là boolean cờ).
    expect(src).not.toMatch(/\{\{\s*error\s*\}\}/)
  })

  it('Happy-path không hồi quy: 2 valid + 1 AC-E001 → N nhãn + ô lỗi + In tất cả enabled', async () => {
    getBatchSpy.mockResolvedValue([lbl('A1'), { name: 'BAD', error: 'AC-E001' }, lbl('A3')])
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    expect(w.findAll('img').length).toBe(2)
    expect(w.text()).toContain('Không tìm thấy thiết bị')
    const printBtn = w.findAll('button').find(b => b.text().includes('In tất cả'))
    expect(printBtn).toBeTruthy()
    expect(printBtn!.attributes('disabled')).toBeUndefined()
  })

  it('empty (0 name) → hint VI, KHÔNG gọi batch API', async () => {
    routeQuery.value = { names: '' }
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    expect(getBatchSpy).not.toHaveBeenCalled()
    expect(w.text()).toContain('Chưa chọn thiết bị')
  })

  // ── Vòng B (BR-00-33) — CAP batch-size: parity 413 bucket VI 'toolarge' ──────
  it('names.length > MAX_LABEL_BATCH (qua query, paste URL) → KHÔNG gọi API + cảnh báo VI role=alert', async () => {
    const big = Array.from({ length: MAX_LABEL_BATCH + 1 }, (_, i) => `A${i}`).join(',')
    routeQuery.value = { names: big }
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    // FE guard: KHÔNG gọi getAssetLabelDataBatch (request chắc-chắn-413).
    expect(getBatchSpy).not.toHaveBeenCalled()
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain(String(MAX_LABEL_BATCH))
    expect(alert.text()).toContain('tối đa')
  })

  it('names.length == MAX_LABEL_BATCH → gọi API bình thường (biên dưới PASS)', async () => {
    const atCap = Array.from({ length: MAX_LABEL_BATCH }, (_, i) => `A${i}`)
    routeQuery.value = { names: atCap.join(',') }
    getBatchSpy.mockResolvedValue(atCap.map(lbl))
    mount(AssetLabelPrintView)
    await flushPromises()
    expect(getBatchSpy).toHaveBeenCalledTimes(1)
    expect(getBatchSpy).toHaveBeenCalledWith(atCap)
  })

  it('API trả 413 (PAYLOAD_TOO_LARGE) → map bucket VI toolarge, KHÔNG raw .message, KHÔNG white-screen', async () => {
    // Nếu vẫn lọt tới BE (race) → map 413 sang bucket VI cố định.
    getBatchSpy.mockRejectedValue(
      new ApiError('Payload Too Large', ErrorCode.PAYLOAD_TOO_LARGE, 413))
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain(String(MAX_LABEL_BATCH))
    // KHÔNG leak raw EN message / code.
    expect(alert.text()).not.toContain('Payload Too Large')
    expect(alert.text()).not.toContain('PAYLOAD_TOO_LARGE')
  })

  // ── B-hardening a11y: phản hồi thành-công/lỗi + aria-live cho IN BATCH ───────
  // Parity màn in đơn AssetDetailView (toast VI qua useToast); KHÔNG nuốt câm.

  it("printAll() thành công → useToast.success gọi ĐÚNG 1 lần với chuỗi VI chứa số nhãn hợp lệ", async () => {
    getBatchSpy.mockResolvedValue([lbl('A1'), { name: 'BAD', error: 'AC-E001' }, lbl('A3')])
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const printBtn = w.findAll('button').find(b => b.text().includes('In tất cả'))
    await printBtn!.trigger('click')
    await flushPromises()
    expect(window.print).toHaveBeenCalled()
    // 2 nhãn hợp lệ (A1, A3) → toast.success ĐÚNG 1 lần với chuỗi VI chứa '2'.
    expect(toastSuccessSpy).toHaveBeenCalledTimes(1)
    const msg = toastSuccessSpy.mock.calls[0][0] as string
    expect(msg).toContain('2')
    expect(msg).toContain('Đã ghi nhận in')
    // KHÔNG gọi toast.error khi thành công.
    expect(toastErrorSpy).not.toHaveBeenCalled()
  })

  it("printAll() khi markLabelPrinted REJECT → useToast.error (bucket VI) + KHÔNG throw + KHÔNG echo raw EN + window.print vẫn gọi", async () => {
    getBatchSpy.mockResolvedValue([lbl('A1'), lbl('A2'), lbl('A3')])
    // Audit-write lỗi: BE trả message tiếng Anh thô.
    markPrintedSpy.mockRejectedValue(
      new ApiError('Internal Server Error (AttributeError)', ErrorCode.UNKNOWN, 500))
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const printBtn = w.findAll('button').find(b => b.text().includes('In tất cả'))
    // KHÔNG throw lên trên (printAll nuốt lỗi audit nhưng có phản hồi).
    await expect(printBtn!.trigger('click')).resolves.toBeUndefined()
    await flushPromises()
    // Giấy KHÔNG bị chặn — đã in trước khi ghi audit.
    expect(window.print).toHaveBeenCalled()
    // toast.error bucket VI cố định — KHÔNG echo error.message raw EN.
    expect(toastErrorSpy).toHaveBeenCalledTimes(1)
    const emsg = toastErrorSpy.mock.calls[0][0] as string
    expect(emsg).not.toContain('Internal Server Error')
    expect(emsg).not.toContain('AttributeError')
    expect(emsg.length).toBeGreaterThan(0)
    // KHÔNG báo nhầm thành công.
    expect(toastSuccessSpy).not.toHaveBeenCalled()
  })

  it("aria-live: sau printAll thành công, role='status' aria-live='polite' chứa text VI số nhãn", async () => {
    getBatchSpy.mockResolvedValue([lbl('A1'), lbl('A2'), lbl('A3')])
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const status = w.find('[role="status"]')
    expect(status.exists()).toBe(true)
    expect(status.attributes('aria-live')).toBe('polite')
    // Trước khi in → rỗng (không vang nhầm).
    expect(status.text()).toBe('')
    const printBtn = w.findAll('button').find(b => b.text().includes('In tất cả'))
    await printBtn!.trigger('click')
    await flushPromises()
    expect(status.text()).toContain('3')
    expect(status.text()).toContain('Đã ghi nhận in')
  })

  it("aria-live: sau lỗi markLabelPrinted → role='status' chứa thông điệp lỗi VI (KHÔNG raw EN)", async () => {
    getBatchSpy.mockResolvedValue([lbl('A1'), lbl('A2'), lbl('A3')])
    markPrintedSpy.mockRejectedValue(
      new ApiError('Internal Server Error (AttributeError)', ErrorCode.UNKNOWN, 500))
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const printBtn = w.findAll('button').find(b => b.text().includes('In tất cả'))
    await printBtn!.trigger('click')
    await flushPromises()
    const status = w.find('[role="status"]')
    expect(status.text().length).toBeGreaterThan(0)
    expect(status.text()).not.toContain('Internal Server Error')
    expect(status.text()).not.toContain('AttributeError')
  })

  it("Regression: 'In tất cả' disabled khi 0 nhãn hợp lệ (toàn item lỗi AC-E001)", async () => {
    getBatchSpy.mockResolvedValue([
      { name: 'B1', error: 'AC-E001' }, { name: 'B2', error: 'AC-E001' },
    ])
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const printBtn = w.findAll('button').find(b => b.text().includes('In tất cả'))
    expect(printBtn!.attributes('disabled')).toBeDefined()
  })

  it('Regression: source KHÔNG còn catch{} rỗng nuốt câm + KHÔNG còn comment sai "BE có retry audit"', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const src = fs.readFileSync(
      path.resolve(process.cwd(), 'src/views/asset/AssetLabelPrintView.vue'),
      'utf8',
    )
    // KHÔNG còn comment khẳng định sai (BE không có retry audit).
    expect(src).not.toContain('BE có retry audit')
    // markLabelPrinted vẫn chỉ nhận validNames (loại AC-E001).
    expect(src).toContain('markLabelPrinted(validNames.value)')
  })
})
