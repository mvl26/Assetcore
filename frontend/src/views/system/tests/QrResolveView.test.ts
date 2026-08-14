// TDD — A2 (ADR-001 D4): QrResolveView resolver MỎNG cho deep-link /a/:token.
//   • token hợp lệ (resolve 200) → router.replace tới AssetScanInfo (A6 màn info
//     mobile-first), KHÔNG AssetDetail (màn admin nặng) — regression A6.
//   • 404 (token sai) → màn lỗi role=alert, KHÔNG redirect, có nút Quét lại + Nhập tay.
//   • 403 (thiếu asset.read) → màn lỗi quyền VI rõ ràng, KHÔNG trang trắng.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { ApiError, ErrorCode } from '@/api/errors'

const routeParams = ref<Record<string, string>>({ token: '' })
const replaceSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: replaceSpy }),
  useRoute: () => ({ get params() { return routeParams.value } }),
}))

const resolveQrTokenSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  resolveQrToken: (token: string) => resolveQrTokenSpy(token),
}))

import QrResolveView from '@/views/system/QrResolveView.vue'

describe('QrResolveView — A2 deep-link /a/:token', () => {
  beforeEach(() => {
    replaceSpy.mockClear()
    resolveQrTokenSpy.mockReset()
    routeParams.value = { token: 'tok_abc123' }
  })

  it('token hợp lệ (resolve 200) → router.replace tới AssetScanInfo đúng id (A6, KHÔNG AssetDetail)', async () => {
    resolveQrTokenSpy.mockResolvedValue({
      name: 'AC-ASSET-2026-00042', asset_code: 'A-042',
      lifecycle_status: 'Active', device_model_name: 'Dräger', location_name: 'ICU',
    })
    const w = mount(QrResolveView)
    await flushPromises()
    expect(resolveQrTokenSpy).toHaveBeenCalledWith('tok_abc123')
    // Regression A6: landing = AssetScanInfo (màn info mobile-first read-only).
    expect(replaceSpy).toHaveBeenCalledWith({
      name: 'AssetScanInfo', params: { id: 'AC-ASSET-2026-00042' },
    })
    // KHÔNG còn push/replace AssetDetail (màn admin nặng) từ QrResolveView.
    expect(replaceSpy).not.toHaveBeenCalledWith(
      expect.objectContaining({ name: 'AssetDetail' }),
    )
    // KHÔNG render màn lỗi khi thành công.
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  it('404 (token sai) → màn lỗi role=alert, KHÔNG redirect, có nút Quét lại + Nhập tay', async () => {
    resolveQrTokenSpy.mockRejectedValue(
      new ApiError('không tồn tại', ErrorCode.NOT_FOUND, 404),
    )
    const w = mount(QrResolveView)
    await flushPromises()
    // KHÔNG điều hướng tới AssetDetail.
    expect(replaceSpy).not.toHaveBeenCalledWith(
      expect.objectContaining({ name: 'AssetDetail' }),
    )
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('Không tìm thấy thiết bị')
    // Có nút quét lại + nhập tay (KHÔNG trang trắng).
    const btns = w.findAll('button').map(b => b.text())
    expect(btns.some(t => t.includes('Quét lại'))).toBe(true)
    expect(btns.some(t => t.includes('Nhập mã'))).toBe(true)
  })

  it('403 (thiếu asset.read) → màn lỗi quyền VI rõ ràng, KHÔNG trang trắng', async () => {
    resolveQrTokenSpy.mockRejectedValue(
      new ApiError('không đủ quyền', ErrorCode.FORBIDDEN, 403),
    )
    const w = mount(QrResolveView)
    await flushPromises()
    expect(replaceSpy).not.toHaveBeenCalledWith(
      expect.objectContaining({ name: 'AssetDetail' }),
    )
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('Không đủ quyền')
    // Vẫn có hành động để user không kẹt.
    expect(w.findAll('button').length).toBeGreaterThan(0)
  })

  // --- Vòng 12: tách điều hướng 'Quét lại' vs 'Nhập mã thủ công' ---
  // Trước đây CẢ HAI nút gọi cùng goScan → đích y hệt (affordance chết/đánh lừa
  // nhãn). Acceptance: 'Quét lại' → QRScan KHÔNG query; 'Nhập mã thủ công' →
  // QRScan query{mode:'manual'} (mở thẳng ô nhập tay cho user camera-hỏng).
  // Helper: tìm nút theo nhãn VI (KHÔNG dựa thứ tự DOM).
  function btnByText(w: ReturnType<typeof mount>, label: string) {
    const b = w.findAll('button').find(x => x.text().includes(label))
    if (!b) throw new Error(`Không tìm thấy nút '${label}'`)
    return b
  }

  async function mountErrorScreen(err: ApiError) {
    resolveQrTokenSpy.mockRejectedValue(err)
    const w = mount(QrResolveView)
    await flushPromises()
    expect(w.find('[role="alert"]').exists()).toBe(true)
    return w
  }

  // Bảng 3 nhánh lỗi resolver — CẢ BA đều phải tách 2 đích.
  const errorBranches: Array<[string, ApiError]> = [
    ['notfound (404)', new ApiError('không tồn tại', ErrorCode.NOT_FOUND, 404)],
    ['forbidden (403)', new ApiError('không đủ quyền', ErrorCode.FORBIDDEN, 403)],
    ['unknown (mạng/khác)', new ApiError('lỗi mạng', ErrorCode.UNKNOWN, 500)],
  ]

  for (const [label, err] of errorBranches) {
    it(`[${label}] 'Nhập mã thủ công' → QRScan query{mode:'manual'} (KHÔNG trùng 'Quét lại')`, async () => {
      const w = await mountErrorScreen(err)
      await btnByText(w, 'Nhập mã thủ công').trigger('click')
      // Đích nhập-tay THẬT: mode=manual.
      expect(replaceSpy).toHaveBeenCalledWith({ name: 'QRScan', query: { mode: 'manual' } })
      // KHÔNG còn là affordance chết = KHÔNG được replace QRScan-không-query.
      expect(replaceSpy).not.toHaveBeenCalledWith({ name: 'QRScan' })
    })

    it(`[${label}] 'Quét lại mã QR' → QRScan KHÔNG query (KHÔNG trùng nhập-tay)`, async () => {
      const w = await mountErrorScreen(err)
      await btnByText(w, 'Quét lại').trigger('click')
      expect(replaceSpy).toHaveBeenCalledWith({ name: 'QRScan' })
      // KHÔNG được dẫn mode=manual (hai đích phải KHÁC NHAU).
      expect(replaceSpy).not.toHaveBeenCalledWith({ name: 'QRScan', query: { mode: 'manual' } })
    })
  }

  it("hai nút dẫn HAI đích KHÁC NHAU (không còn cùng handler/đích)", async () => {
    const w = await mountErrorScreen(
      new ApiError('không tồn tại', ErrorCode.NOT_FOUND, 404),
    )
    await btnByText(w, 'Quét lại').trigger('click')
    await btnByText(w, 'Nhập mã thủ công').trigger('click')
    const calls = replaceSpy.mock.calls.map(c => JSON.stringify(c[0]))
    expect(calls).toContain(JSON.stringify({ name: 'QRScan' }))
    expect(calls).toContain(JSON.stringify({ name: 'QRScan', query: { mode: 'manual' } }))
    // Hai đích là 2 object KHÁC NHAU (đo được).
    expect(JSON.stringify({ name: 'QRScan' })).not.toBe(
      JSON.stringify({ name: 'QRScan', query: { mode: 'manual' } }),
    )
  })

  it('token rỗng → màn lỗi (notfound), KHÔNG gọi API, KHÔNG redirect', async () => {
    routeParams.value = { token: '' }
    const w = mount(QrResolveView)
    await flushPromises()
    expect(resolveQrTokenSpy).not.toHaveBeenCalled()
    expect(replaceSpy).not.toHaveBeenCalledWith(
      expect.objectContaining({ name: 'AssetDetail' }),
    )
    expect(w.find('[role="alert"]').exists()).toBe(true)
  })

  // --- Regression guard: FE trim defense-in-depth lớp 1 (factory vòng 6) ---
  // BE đã chuẩn hoá whitespace token ở SSoT resolve_qr_token (server tự đúng độc
  // lập). FE GIỮ trim @QrResolveView.vue:34 làm lớp defense thứ 1 — 2 lớp
  // (FE trim + BE strip). Test này KHOÁ hành vi FE trim để KHÔNG bị xoá âm thầm:
  // route-param có khoảng trắng đầu/cuối → tokenParam().trim() → resolveQrToken
  // được gọi với token ĐÃ TRIM (KHÔNG còn whitespace). Khớp BE-4/Task-FE đề mục.
  it('route-param có whitespace đầu/cuối → trim → resolveQrToken gọi với token đã trim (defense lớp 1)', async () => {
    routeParams.value = { token: '  tok_abc123  ' }
    resolveQrTokenSpy.mockResolvedValue({
      name: 'AC-ASSET-2026-00042', asset_code: 'A-042',
      lifecycle_status: 'Active', device_model_name: 'Dräger', location_name: 'ICU',
    })
    const w = mount(QrResolveView)
    await flushPromises()
    // FE trim chạy → token gửi BE đã sạch whitespace (KHÔNG '  tok_abc123  ').
    expect(resolveQrTokenSpy).toHaveBeenCalledWith('tok_abc123')
    expect(replaceSpy).toHaveBeenCalledWith({
      name: 'AssetScanInfo', params: { id: 'AC-ASSET-2026-00042' },
    })
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  it('route-param trailing newline (artifact tem nhiệt) → trim → resolveQrToken gọi token sạch', async () => {
    routeParams.value = { token: 'tok_abc123\n' }
    resolveQrTokenSpy.mockResolvedValue({
      name: 'AC-ASSET-2026-00042', asset_code: 'A-042',
      lifecycle_status: 'Active', device_model_name: 'Dräger', location_name: 'ICU',
    })
    mount(QrResolveView)
    await flushPromises()
    expect(resolveQrTokenSpy).toHaveBeenCalledWith('tok_abc123')
  })

  it('route-param TOÀN whitespace ("   ") → trim thành rỗng → KHÔNG gọi API, màn lỗi (parity guard rỗng-sau-strip)', async () => {
    routeParams.value = { token: '   ' }
    const w = mount(QrResolveView)
    await flushPromises()
    // trim('   ') === '' → guard rỗng → KHÔNG gọi resolveQrToken (KHÔNG để BE
    // phải xử lý whitespace-only từ FE). Đối ứng BE-3 (ws-only → query-count=0).
    expect(resolveQrTokenSpy).not.toHaveBeenCalled()
    expect(replaceSpy).not.toHaveBeenCalledWith(
      expect.objectContaining({ name: 'AssetDetail' }),
    )
    expect(w.find('[role="alert"]').exists()).toBe(true)
  })
})
