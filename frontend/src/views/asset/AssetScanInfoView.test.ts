// TDD — A6: AssetScanInfoView — màn THÔNG TIN thiết bị mobile-first khi quét QR.
//   • mount với mock payload → render status pill nhãn VI (KHÔNG mã EN thô) +
//     bảo trì gần nhất; có nút Quét lại + Về trang chủ; read-only (KHÔNG edit/
//     delete/transition).
//   • loading → aria-busy; 403 → role=alert 'thiếu quyền' VI; 404 → role=alert
//     'không tìm thấy' VI; KHÔNG trang trắng.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { ApiError, ErrorCode } from '@/api/errors'
import { formatDate } from '@/utils/formatters'

const routeParams = ref<Record<string, string>>({ id: 'AC-ASSET-2026-00042' })
const replaceSpy = vi.fn().mockResolvedValue(undefined)
const pushSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: replaceSpy, push: pushSpy }),
  useRoute: () => ({ get params() { return routeParams.value } }),
}))

const getAssetScanInfoSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  getAssetScanInfo: (p: { token?: string; name?: string }) => getAssetScanInfoSpy(p),
}))

import AssetScanInfoView from './AssetScanInfoView.vue'

const PAYLOAD = {
  name: 'AC-ASSET-2026-00042',
  asset_code: 'A-042',
  asset_name: 'Máy thở Dräger Evita',
  device_model_name: 'Evita V500',
  location_name: 'ICU - Tầng 3',
  lifecycle_status: 'Active',
  recent_maintenance: { event_type: 'pm_completed', date: '2026-05-30' },
  next_pm_date: '2026-08-30',
  // Cờ PM quá hạn derive SERVER-SIDE — FE CHỈ đọc cờ, KHÔNG so ngày client.
  pm_overdue: false,
  // Chiều HIỆU CHUẨN (FR-00-86 / BR-00-37) — song song next_pm_date/pm_overdue.
  next_calibration_date: '2026-09-15',
  calibration_overdue: false,
}

describe('AssetScanInfoView — A6 màn info mobile-first khi quét QR', () => {
  beforeEach(() => {
    replaceSpy.mockClear(); pushSpy.mockClear()
    getAssetScanInfoSpy.mockReset()
    routeParams.value = { id: 'AC-ASSET-2026-00042' }
  })

  it('payload hợp lệ → render định danh + status pill nhãn VI (KHÔNG mã EN thô) + bảo trì gần nhất', async () => {
    getAssetScanInfoSpy.mockResolvedValue(PAYLOAD)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    // Định danh đọc được (tên thiết bị, model, vị trí).
    expect(txt).toContain('Máy thở Dräger Evita')
    expect(txt).toContain('Evita V500')
    expect(txt).toContain('ICU - Tầng 3')
    // Status pill: nhãn VI, KHÔNG leak mã EN 'Active'.
    expect(txt).toContain('Đang hoạt động')
    expect(txt).not.toContain('Active')
    // Bảo trì gần nhất: nhãn VI loại sự kiện (KHÔNG 'pm_completed' thô).
    expect(txt).toContain('Hoàn tất bảo trì')
    expect(txt).not.toContain('pm_completed')
    // KHÔNG render màn lỗi khi thành công.
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  it('read-only — KHÔNG có nút Sửa/Xóa/chuyển trạng thái; CÓ nút Quét lại + Về trang chủ', async () => {
    getAssetScanInfoSpy.mockResolvedValue(PAYLOAD)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const btns = w.findAll('button').map(b => b.text())
    expect(btns.some(t => t.includes('Quét lại'))).toBe(true)
    expect(btns.some(t => t.includes('Về trang chủ'))).toBe(true)
    // KHÔNG có hành động ghi (read-only view).
    expect(btns.some(t => /Sửa|Chỉnh sửa|Xóa|Xoá|Chuyển|Phê duyệt|Thanh lý/.test(t))).toBe(false)
  })

  it('loading → aria-busy (KHÔNG trang trắng)', async () => {
    let resolveFn: (v: unknown) => void = () => {}
    getAssetScanInfoSpy.mockReturnValue(new Promise((r) => { resolveFn = r }))
    const w = mount(AssetScanInfoView)
    // chưa resolve → vẫn ở loading.
    expect(w.find('[aria-busy="true"]').exists()).toBe(true)
    resolveFn(PAYLOAD)
    await flushPromises()
  })

  it('403 → role=alert thông báo thiếu quyền (VI), KHÔNG trang trắng', async () => {
    getAssetScanInfoSpy.mockRejectedValue(
      new ApiError('không đủ quyền', ErrorCode.FORBIDDEN, 403),
    )
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('Không đủ quyền')
    // Vẫn có hành động để user không kẹt.
    expect(w.findAll('button').length).toBeGreaterThan(0)
  })

  it('404 → role=alert không tìm thấy (VI), KHÔNG trang trắng', async () => {
    getAssetScanInfoSpy.mockRejectedValue(
      new ApiError('không tồn tại', ErrorCode.NOT_FOUND, 404),
    )
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('Không tìm thấy thiết bị')
  })

  it('resolve theo name từ route param :id (deep-link /assets/:id/info)', async () => {
    getAssetScanInfoSpy.mockResolvedValue(PAYLOAD)
    mount(AssetScanInfoView)
    await flushPromises()
    expect(getAssetScanInfoSpy).toHaveBeenCalledWith({ name: 'AC-ASSET-2026-00042' })
  })

  // ── A6 hardening: cờ pm_overdue (derive server-side) → badge VI cảnh báo ───
  it('pm_overdue=true → badge VI "Quá hạn bảo trì" cạnh ngày + a11y (role/aria, KHÔNG chỉ màu)', async () => {
    // next_pm_date là quá khứ NHƯNG view KHÔNG tự so ngày — chỉ đọc cờ payload.
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD, next_pm_date: '2026-01-01', pm_overdue: true,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    // Badge nhãn VI hiển thị (KHÔNG mã EN / raw 'pm_overdue').
    expect(w.text()).toContain('Quá hạn bảo trì')
    expect(w.text()).not.toContain('pm_overdue')
    // a11y: KHÔNG chỉ dựa màu → có role status + aria-label mô tả cảnh báo.
    const badge = w.get('[aria-label="Cảnh báo: quá hạn bảo trì định kỳ"]')
    expect(badge.attributes('role')).toBe('status')
    // Vẫn render ngày PM kế tiếp như cũ.
    expect(w.text()).toContain(formatDate('2026-01-01'))
  })

  it('pm_overdue=false → KHÔNG badge, vẫn render formatDate(next_pm_date)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD, next_pm_date: '2026-08-30', pm_overdue: false,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(w.text()).not.toContain('Quá hạn bảo trì')
    expect(w.find('[aria-label="Cảnh báo: quá hạn bảo trì định kỳ"]').exists()).toBe(false)
    // Ngày PM kế tiếp vẫn hiển thị bình thường.
    expect(w.text()).toContain(formatDate('2026-08-30'))
  })

  it('SSoT: view đọc cờ pm_overdue payload — next_pm_date quá khứ NHƯNG pm_overdue=false → KHÔNG badge (KHÔNG so ngày client)', async () => {
    // Ngày quá khứ + cờ server=false (vd thiết bị đã loại biên) → FE KHÔNG được
    // tự suy ra "quá hạn" từ client clock; phải tôn trọng cờ BE.
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD, next_pm_date: '2020-01-01', pm_overdue: false,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(w.text()).not.toContain('Quá hạn bảo trì')
  })

  // ── A6 hardening (FR-00-86 / BR-00-37): cờ calibration_overdue ─────────────
  // (a) calibration_overdue=true → badge VI 'Quá hạn hiệu chuẩn' + a11y, KHÔNG raw.
  it('calibration_overdue=true → badge VI "Quá hạn hiệu chuẩn" + role=status/aria (KHÔNG raw key)', async () => {
    // next_calibration_date quá khứ NHƯNG view KHÔNG tự so ngày — chỉ đọc cờ payload.
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD, next_calibration_date: '2026-01-01', calibration_overdue: true,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(w.text()).toContain('Hiệu chuẩn kế tiếp')
    // Badge nhãn VI hiển thị; KHÔNG leak raw key 'calibration_overdue'/'next_calibration_date'.
    expect(w.text()).toContain('Quá hạn hiệu chuẩn')
    expect(w.text()).not.toContain('calibration_overdue')
    expect(w.text()).not.toContain('next_calibration_date')
    // a11y: KHÔNG chỉ dựa màu → role=status + aria-label mô tả cảnh báo.
    const badge = w.get('[aria-label="Cảnh báo: quá hạn hiệu chuẩn"]')
    expect(badge.attributes('role')).toBe('status')
    // Vẫn render ngày hiệu chuẩn kế tiếp như cũ.
    expect(w.text()).toContain(formatDate('2026-01-01'))
  })

  // (b) calibration_overdue=false → KHÔNG badge, vẫn render formatDate(next_calibration_date).
  it('calibration_overdue=false → KHÔNG badge, vẫn render formatDate(next_calibration_date)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD, next_calibration_date: '2026-09-15', calibration_overdue: false,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(w.text()).not.toContain('Quá hạn hiệu chuẩn')
    expect(w.find('[aria-label="Cảnh báo: quá hạn hiệu chuẩn"]').exists()).toBe(false)
    expect(w.text()).toContain(formatDate('2026-09-15'))
  })

  // (c) SSoT: next_calibration_date quá khứ NHƯNG calibration_overdue=false → KHÔNG badge.
  it('SSoT: next_calibration_date quá khứ NHƯNG calibration_overdue=false → KHÔNG badge (KHÔNG so ngày client)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD, next_calibration_date: '2020-01-01', calibration_overdue: false,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(w.text()).not.toContain('Quá hạn hiệu chuẩn')
  })

  // (d) next_calibration_date rỗng → render 'Chưa lên lịch'.
  it('next_calibration_date rỗng → render "Chưa lên lịch" (KHÔNG badge)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD, next_calibration_date: null, calibration_overdue: false,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    expect(txt).toContain('Hiệu chuẩn kế tiếp')
    expect(txt).toContain('Chưa lên lịch')
    expect(txt).not.toContain('Quá hạn hiệu chuẩn')
  })
})
