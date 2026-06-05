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

import QrResolveView from './QrResolveView.vue'

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
})
