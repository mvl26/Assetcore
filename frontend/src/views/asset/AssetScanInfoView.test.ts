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
// router.resolve dùng để DỰNG URL deep-link (D3) — trả href chứa query asset+source.
// Mock phản chiếu vue-router thật: ghép query-string từ location.query.
const resolveSpy = vi.fn((to: { name?: string; query?: Record<string, string> }) => {
  const qs = new URLSearchParams(to.query ?? {}).toString()
  return { href: `/resolved/${to.name}${qs ? `?${qs}` : ''}` }
})
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: replaceSpy, push: pushSpy, resolve: resolveSpy }),
  useRoute: () => ({ get params() { return routeParams.value } }),
}))

const getAssetScanInfoSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  getAssetScanInfo: (p: { token?: string; name?: string }) => getAssetScanInfoSpy(p),
}))

import AssetScanInfoView from './AssetScanInfoView.vue'

// 4 CTA đủ enabled (Active + đủ cap) — shape MIRROR BE _build_available_actions.
const ACTIONS_ALL_ENABLED = [
  { key: 'report_failure',      label: 'Báo hỏng',          route: 'IncidentCreate',    enabled: true,  reason: '' },
  { key: 'request_pm',          label: 'Yêu cầu bảo trì',   route: 'PMWorkOrderCreate', enabled: true,  reason: '' },
  { key: 'request_cm',          label: 'Yêu cầu sửa chữa',  route: 'CMCreate',          enabled: true,  reason: '' },
  { key: 'request_calibration', label: 'Hiệu chuẩn',        route: 'CalibrationCreate', enabled: true,  reason: '' },
]

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
  // R1 (D2) — 4 CTA derive SERVER-SIDE. Mặc định đủ enabled (Active + đủ cap).
  available_actions: ACTIONS_ALL_ENABLED,
}

describe('AssetScanInfoView — A6 màn info mobile-first khi quét QR', () => {
  beforeEach(() => {
    replaceSpy.mockClear(); pushSpy.mockClear(); resolveSpy.mockClear()
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

  // ── i18n SSoT sweep: status pill 'Under Maintenance' (mã canonical BE phát) ──
  //    Bug gốc: LIFECYCLE_STATUS_LABEL/CLASS THIẾU 'Under Maintenance' → pill leak
  //    raw-EN 'Under Maintenance' + nền xám. Fix tại nguồn map (constants/labels.ts)
  //    → tự lan tới màn quét QR (statusLabel/statusClass đọc qua SSoT).
  it("lifecycle_status='Under Maintenance' → pill 'Đang bảo trì' + nền cam (KHÔNG leak raw-EN, KHÔNG xám)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, lifecycle_status: 'Under Maintenance' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    // Nhãn VI hiển thị; KHÔNG leak mã canonical EN.
    expect(txt).toContain('Đang bảo trì')
    expect(txt).not.toContain('Under Maintenance')
    // Pill có nền cam (SSoT class), KHÔNG rơi fallback xám.
    const pill = w.findAll('span').find(s => s.text().includes('Đang bảo trì'))
    expect(pill, 'không tìm thấy status pill').toBeTruthy()
    expect(pill!.classes().join(' ')).toContain('bg-orange-100')
    expect(pill!.classes().join(' ')).not.toContain('bg-gray-100')
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

  // ── A6 defensive (P2): phân biệt 'field absent' (undefined — payload partial/
  //    stale từ worker cũ) vs 'null thật' (BE chủ động báo CHƯA có lịch). ───────
  //    Quy tắc: key PRESENT + null/rỗng → 'Chưa lên lịch' (giữ hành vi cũ);
  //    key ABSENT (undefined) → 'Cần kiểm tra' (KHÔNG tuyên bố sai là chưa lên
  //    lịch). Cờ overdue ABSENT → KHÔNG bịa pill.

  // (1) regression-guard: null THẬT (key có mặt, value=null) → vẫn 'Chưa lên lịch'.
  it('next_pm_date=null (key CÓ mặt) → render "Chưa lên lịch" (hành vi cũ GIỮ NGUYÊN)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD, next_pm_date: null, pm_overdue: false,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    expect(txt).toContain('Bảo trì định kỳ kế tiếp')
    expect(txt).toContain('Chưa lên lịch')
    expect(txt).not.toContain('Cần kiểm tra')
    expect(txt).not.toContain('Quá hạn bảo trì')
  })

  // (2) ABSENT key next_pm_date (delete khỏi object — undefined runtime) →
  //     'Cần kiểm tra', KHÔNG 'Chưa lên lịch' cho ô PM.
  it('next_pm_date ABSENT (undefined — payload partial/stale) → "Cần kiểm tra", KHÔNG tuyên bố "Chưa lên lịch"', async () => {
    const partial: Record<string, unknown> = { ...PAYLOAD }
    delete partial.next_pm_date
    // calibration vẫn đầy đủ để cô lập ô PM (calibration có ngày hợp lệ).
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    expect(txt).toContain('Bảo trì định kỳ kế tiếp')
    // KHÔNG được tuyên bố sai "Chưa lên lịch" cho ô PM (calibration có ngày → 'Chưa
    // lên lịch' KHÔNG xuất hiện ở đâu cả khi calibration đầy đủ).
    expect(txt).toContain('Cần kiểm tra')
    expect(txt).not.toContain('Chưa lên lịch')
  })

  // (3) ABSENT key next_calibration_date → ô calibration 'Cần kiểm tra', KHÔNG 'Chưa lên lịch'.
  it('next_calibration_date ABSENT (undefined) → ô hiệu chuẩn "Cần kiểm tra", KHÔNG "Chưa lên lịch"', async () => {
    const partial: Record<string, unknown> = { ...PAYLOAD }
    delete partial.next_calibration_date
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    expect(txt).toContain('Hiệu chuẩn kế tiếp')
    expect(txt).toContain('Cần kiểm tra')
    expect(txt).not.toContain('Chưa lên lịch')
  })

  // (4) ABSENT cờ pm_overdue → KHÔNG bịa pill 'Quá hạn bảo trì'.
  it('pm_overdue ABSENT (undefined) → KHÔNG render pill "Quá hạn bảo trì" (không bịa cờ)', async () => {
    const partial: Record<string, unknown> = { ...PAYLOAD }
    delete partial.pm_overdue
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(w.text()).not.toContain('Quá hạn bảo trì')
    expect(w.find('[aria-label="Cảnh báo: quá hạn bảo trì định kỳ"]').exists()).toBe(false)
  })

  // (5) ABSENT cờ calibration_overdue → KHÔNG bịa pill 'Quá hạn hiệu chuẩn'.
  it('calibration_overdue ABSENT (undefined) → KHÔNG render pill "Quá hạn hiệu chuẩn" (không bịa cờ)', async () => {
    const partial: Record<string, unknown> = { ...PAYLOAD }
    delete partial.calibration_overdue
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(w.text()).not.toContain('Quá hạn hiệu chuẩn')
    expect(w.find('[aria-label="Cảnh báo: quá hạn hiệu chuẩn"]').exists()).toBe(false)
  })

  // ── R1 QR-SCAN-ACTION (ADR-IMM00-QR-SCAN-ACTION §D1/D2/D3) — cụm nút hành động ─
  //    capability-gated từ payload BE available_actions. FE v-for render MỌI phần
  //    tử (kể cả enabled=false → disabled + reason). KHÔNG hardcode danh sách
  //    action. Nhãn từ SSoT SCAN_ACTION_LABELS. Deep-link ?asset=&source=qr-scan,
  //    TUYỆT ĐỐI KHÔNG qr_token. Quét lại + Về trang chủ GIỮ NGUYÊN.

  // helper: lấy nút action theo key (data-action-key) — KHÔNG lẫn nút Quét lại/Home.
  const actionBtn = (w: ReturnType<typeof mount>, key: string) =>
    w.find(`[data-action-key="${key}"]`)

  it('4 action enabled → render đúng 4 nút action (nhãn VI SSoT), + 2 nút Quét lại/Về trang chủ', async () => {
    getAssetScanInfoSpy.mockResolvedValue(PAYLOAD)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    // Đủ 4 nút action render (KHÔNG ẩn nút nào).
    const actionEls = w.findAll('[data-action-key]')
    expect(actionEls.length).toBe(4)
    // Nhãn VI từ SSoT SCAN_ACTION_LABELS (KHÔNG hardcode .vue).
    expect(actionBtn(w, 'report_failure').text()).toContain('Báo hỏng')
    expect(actionBtn(w, 'request_pm').text()).toContain('Yêu cầu bảo trì')
    expect(actionBtn(w, 'request_cm').text()).toContain('Yêu cầu sửa chữa')
    expect(actionBtn(w, 'request_calibration').text()).toContain('Hiệu chuẩn')
    // 4 nút enabled → KHÔNG disabled.
    for (const key of ['report_failure', 'request_pm', 'request_cm', 'request_calibration']) {
      expect(actionBtn(w, key).attributes('disabled')).toBeUndefined()
    }
    // 2 nút điều hướng đáy GIỮ NGUYÊN.
    const btns = w.findAll('button').map(b => b.text())
    expect(btns.some(t => t.includes('Quét lại'))).toBe(true)
    expect(btns.some(t => t.includes('Về trang chủ'))).toBe(true)
  })

  it('click nút report_failure (enabled) → router.push({ name:"IncidentCreate", query:{ asset, source:"qr-scan" } }) — KHÔNG qr_token', async () => {
    getAssetScanInfoSpy.mockResolvedValue(PAYLOAD)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    await actionBtn(w, 'report_failure').trigger('click')
    expect(pushSpy).toHaveBeenCalledTimes(1)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'IncidentCreate',
      query: { asset: 'AC-ASSET-2026-00042', source: 'qr-scan' },
    })
    // KHÔNG có qr_token trong location truyền cho router.push.
    const arg = pushSpy.mock.calls[0][0]
    expect(JSON.stringify(arg)).not.toContain('qr_token')
    expect(Object.keys(arg.query)).toEqual(['asset', 'source'])
  })

  it('click các nút enabled khác → push đúng route name + query (asset + qr-scan, no qr_token)', async () => {
    getAssetScanInfoSpy.mockResolvedValue(PAYLOAD)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const cases: Array<[string, string]> = [
      ['request_pm', 'PMWorkOrderCreate'],
      ['request_cm', 'CMCreate'],
      ['request_calibration', 'CalibrationCreate'],
    ]
    for (const [key, routeName] of cases) {
      pushSpy.mockClear()
      await actionBtn(w, key).trigger('click')
      expect(pushSpy).toHaveBeenCalledWith({
        name: routeName,
        query: { asset: 'AC-ASSET-2026-00042', source: 'qr-scan' },
      })
      expect(JSON.stringify(pushSpy.mock.calls[0][0])).not.toContain('qr_token')
    }
  })

  it('action enabled=false (Decommissioned reason) → nút disabled + title=reason + aria-disabled; click no-op', async () => {
    const REASON = 'Thiết bị đã thanh lý'
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      lifecycle_status: 'Decommissioned',
      available_actions: [
        { key: 'report_failure',      label: 'Báo hỏng',         route: 'IncidentCreate',    enabled: false, reason: REASON },
        { key: 'request_pm',          label: 'Yêu cầu bảo trì',  route: 'PMWorkOrderCreate', enabled: false, reason: REASON },
        { key: 'request_cm',          label: 'Yêu cầu sửa chữa', route: 'CMCreate',          enabled: false, reason: REASON },
        { key: 'request_calibration', label: 'Hiệu chuẩn',       route: 'CalibrationCreate', enabled: false, reason: REASON },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const btn = actionBtn(w, 'report_failure')
    // disabled + a11y.
    expect(btn.attributes('disabled')).toBeDefined()
    expect(btn.attributes('aria-disabled')).toBe('true')
    expect(btn.attributes('title')).toBe(REASON)
    // reason đọc được trên màn (title + cụm aria-live).
    expect(w.text()).toContain(REASON)
    // click KHÔNG điều hướng (no-op).
    await btn.trigger('click')
    expect(pushSpy).not.toHaveBeenCalled()
    // KHÔNG ẩn nút nào — vẫn đủ 4 nút action render.
    expect(w.findAll('[data-action-key]').length).toBe(4)
  })

  it('lifecycle Out of Service → 2 enabled (report_failure+request_cm) + 2 disabled (pm+calibration reason) — KHÔNG ẩn nút nào (tổng 4)', async () => {
    const OOS_REASON = 'Thiết bị đang ngừng hoạt động — chỉ cho phép báo hỏng / yêu cầu sửa chữa'
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      lifecycle_status: 'Out of Service',
      available_actions: [
        { key: 'report_failure',      label: 'Báo hỏng',         route: 'IncidentCreate',    enabled: true,  reason: '' },
        { key: 'request_cm',          label: 'Yêu cầu sửa chữa', route: 'CMCreate',          enabled: true,  reason: '' },
        { key: 'request_pm',          label: 'Yêu cầu bảo trì',  route: 'PMWorkOrderCreate', enabled: false, reason: OOS_REASON },
        { key: 'request_calibration', label: 'Hiệu chuẩn',       route: 'CalibrationCreate', enabled: false, reason: OOS_REASON },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    // Tổng 4 nút action render (KHÔNG ẩn nút nào).
    expect(w.findAll('[data-action-key]').length).toBe(4)
    // 2 enabled.
    expect(actionBtn(w, 'report_failure').attributes('disabled')).toBeUndefined()
    expect(actionBtn(w, 'request_cm').attributes('disabled')).toBeUndefined()
    // 2 disabled + reason OOS.
    for (const key of ['request_pm', 'request_calibration']) {
      const b = actionBtn(w, key)
      expect(b.attributes('disabled')).toBeDefined()
      expect(b.attributes('aria-disabled')).toBe('true')
      expect(b.attributes('title')).toBe(OOS_REASON)
    }
    expect(w.text()).toContain(OOS_REASON)
    // enabled vẫn điều hướng được.
    await actionBtn(w, 'request_cm').trigger('click')
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'CMCreate', query: { asset: 'AC-ASSET-2026-00042', source: 'qr-scan' },
    })
    // disabled click no-op.
    pushSpy.mockClear()
    await actionBtn(w, 'request_pm').trigger('click')
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('action enabled=false vì THIẾU QUYỀN (reason capability) → disabled + title=reason quyền (FE chỉ render reason BE)', async () => {
    const CAP_REASON = 'Bạn không có quyền thực hiện thao tác này'
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      lifecycle_status: 'Active',
      available_actions: [
        { key: 'report_failure',      label: 'Báo hỏng',         route: 'IncidentCreate',    enabled: true,  reason: '' },
        { key: 'request_pm',          label: 'Yêu cầu bảo trì',  route: 'PMWorkOrderCreate', enabled: false, reason: CAP_REASON },
        { key: 'request_cm',          label: 'Yêu cầu sửa chữa', route: 'CMCreate',          enabled: true,  reason: '' },
        { key: 'request_calibration', label: 'Hiệu chuẩn',       route: 'CalibrationCreate', enabled: true,  reason: '' },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const b = actionBtn(w, 'request_pm')
    expect(b.attributes('disabled')).toBeDefined()
    expect(b.attributes('aria-disabled')).toBe('true')
    // reason quyền (≠ reason lifecycle) — FE render ĐÚNG chuỗi BE trả.
    expect(b.attributes('title')).toBe(CAP_REASON)
    expect(w.text()).toContain(CAP_REASON)
    // click no-op.
    await b.trigger('click')
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('available_actions rỗng/absent → KHÔNG crash, KHÔNG render nút action (vẫn còn Quét lại/Home)', async () => {
    const partial: Record<string, unknown> = { ...PAYLOAD }
    delete partial.available_actions
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(w.findAll('[data-action-key]').length).toBe(0)
    const btns = w.findAll('button').map(b => b.text())
    expect(btns.some(t => t.includes('Quét lại'))).toBe(true)
    expect(btns.some(t => t.includes('Về trang chủ'))).toBe(true)
  })

  it('nhãn nút action lấy TỪ SSoT SCAN_ACTION_LABELS — đổi BE label vẫn render nhãn SSoT theo key', async () => {
    // BE trả label "lệch" (mô phỏng drift) — FE PHẢI ưu tiên SSoT theo key.
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      available_actions: [
        { key: 'report_failure', label: 'XXX-drift', route: 'IncidentCreate', enabled: true, reason: '' },
        ...ACTIONS_ALL_ENABLED.slice(1),
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    // Render nhãn SSoT VI (KHÔNG render label drift của BE).
    expect(actionBtn(w, 'report_failure').text()).toContain('Báo hỏng')
    expect(w.text()).not.toContain('XXX-drift')
  })
})
