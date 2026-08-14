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

import AssetScanInfoView from '@/views/asset/AssetScanInfoView.vue'

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
  // Vòng 48 (trạng thái BẢO HÀNH) — BE LUÔN emit 2 key này (contract). Mặc định
  // còn bảo hành (ngày tương lai + cờ false) → KHÔNG kích hoạt nhánh fallback
  // 'Cần kiểm tra'/'Chưa có thông tin' trong các test shape chung.
  warranty_expiry_date: '2027-05-01',
  warranty_expired: false,
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

  // ── no-leak fallback (vòng 17): recent_maintenance.event_type mã LẠ/drift/legacy ──
  //    (vd 'pm_aborted' BE chưa map enum) — DÒNG render AssetScanInfoView.vue:229
  //    {{ translateLifecycleEvent(info.recent_maintenance.event_type) }} TUYỆT ĐỐI
  //    KHÔNG được lộ raw code ra UI quét QR (hard-constraint). Fallback → 'Khác'.
  it("recent_maintenance.event_type mã LẠ ('pm_aborted') → hiển thị 'Khác', KHÔNG rò mã thô", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: 'pm_aborted', date: '2026-01-01' },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    // Nhãn an toàn VI hiển thị; raw code KHÔNG lọt ra DOM.
    expect(txt).toContain('Khác')
    expect(txt).not.toContain('pm_aborted')
    // Bất biến no-leak: không snake_case nào lọt qua dòng bảo trì gần nhất.
    expect(txt).not.toContain('_aborted')
  })

  it("recent_maintenance.event_type='pm_completed' (canonical BE) → 'Hoàn tất bảo trì'", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: 'pm_completed', date: '2026-01-01' },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    expect(txt).toContain('Hoàn tất bảo trì')
    expect(txt).not.toContain('pm_completed')
  })

  // ── Vòng 42: DÒNG LOẠI 'Bảo trì gần nhất' — em-dash câm khi event_type rỗng ────
  //    recent_maintenance TỒN TẠI (BE _recent_maintenance_event trả {event_type,
  //    date}) nhưng event_type='' / null / undefined / chỉ-whitespace (legacy/drift/
  //    payload partial) → dòng data-test="recent-maintenance-type" KHÔNG bao giờ
  //    render '—' (em-dash câm vô nghĩa cho KTV ngay cạnh ngày bảo trì). Hiển thị
  //    nhãn VI an toàn 'Bảo trì' (literal SSoT 1 chỗ trong view). KHÔNG sửa shared
  //    formatter translateLifecycleEvent (vẫn '—' cho ''/null — guard timeline). Fix
  //    CHỈ ở tầng view qua computed presence-aware. Parity no-em-dash modelText(V22)/
  //    serialText(V37) + no-regress no-EN-leak vòng 17 (mã lạ vẫn 'Khác').

  // TC-MAINT-TYPE-EMPTY: event_type='' → 'Bảo trì', KHÔNG '—'.
  it("TC-MAINT-TYPE-EMPTY: recent_maintenance.event_type='' → 'Bảo trì' (KHÔNG '—' câm)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: '', date: '2026-05-30' },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const cell = w.get('[data-test="recent-maintenance-type"]')
    expect(cell.text()).toBe('Bảo trì')
    expect(cell.text()).not.toBe('—')
  })

  // TC-MAINT-TYPE-NULL: event_type=null → 'Bảo trì', KHÔNG '—', KHÔNG 'null'.
  it("TC-MAINT-TYPE-NULL: recent_maintenance.event_type=null → 'Bảo trì' (KHÔNG '—', KHÔNG 'null')", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: null as unknown as string, date: '2026-05-30' },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const cell = w.get('[data-test="recent-maintenance-type"]')
    expect(cell.text()).toBe('Bảo trì')
    expect(cell.text()).not.toBe('—')
    expect(cell.text()).not.toContain('null')
  })

  // TC-MAINT-TYPE-WHITESPACE: event_type chỉ-whitespace → 'Bảo trì', KHÔNG leak thô.
  it("TC-MAINT-TYPE-WHITESPACE: recent_maintenance.event_type='   \\n' → 'Bảo trì' (KHÔNG '—', KHÔNG leak whitespace thô)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: '   \n\t', date: '2026-05-30' },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const cell = w.get('[data-test="recent-maintenance-type"]')
    expect(cell.text()).toBe('Bảo trì')
    expect(cell.text()).not.toBe('—')
  })

  // TC-MAINT-TYPE-CANONICAL (no-regress): event_type hợp lệ → vẫn nhãn enum đúng.
  it("TC-MAINT-TYPE-CANONICAL: recent_maintenance.event_type='pm_completed' → 'Hoàn tất bảo trì' (no-regress enum)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: 'pm_completed', date: '2026-05-30' },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const cell = w.get('[data-test="recent-maintenance-type"]')
    expect(cell.text()).toBe('Hoàn tất bảo trì')
    expect(cell.text()).not.toBe('Bảo trì')
  })

  // TC-MAINT-TYPE-UNKNOWN (no-regress vòng 17): mã lạ → 'Khác', KHÔNG nuốt nhầm.
  it("TC-MAINT-TYPE-UNKNOWN: recent_maintenance.event_type='pm_aborted' (mã lạ) → 'Khác' (KHÔNG rò raw, KHÔNG '—', KHÔNG nhánh empty nuốt nhầm)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: 'pm_aborted', date: '2026-05-30' },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const cell = w.get('[data-test="recent-maintenance-type"]')
    expect(cell.text()).toBe('Khác')
    expect(cell.text()).not.toBe('—')
    expect(cell.text()).not.toBe('Bảo trì')
    expect(cell.text()).not.toContain('pm_aborted')
    expect(cell.text()).not.toContain('_aborted')
  })

  // ── Vòng 18: DÒNG NGÀY 'Bảo trì gần nhất' — null/''/phi-ISO không leak ───────
  //    BE _recent_maintenance_event trả {event_type, date} với date=_date_str_or_none
  //    (str|None hợp lệ: None khi timestamp rỗng/legacy). FE DÒNG NGÀY (AssetScanInfoView
  //    .vue:231) trước đây render formatDate(date) THẲNG → null/'' ra em-dash trơ '—'
  //    (vô nghĩa), và chuỗi phi-ISO leak verbatim qua nhánh fallback `return d` của
  //    formatDate. Yêu cầu: presence-aware như scheduleLabel + parity no-raw-leak
  //    Vòng 17 (event_type) → mọi date không-parse-được → nhãn VI 'Chưa rõ ngày'.

  // TC1 (no-regress AC1): date ISO hợp lệ → formatDate VI, KHÔNG 'Chưa rõ ngày'.
  it('TC1: recent_maintenance.date ISO hợp lệ (2026-05-30) → render formatDate VI, KHÔNG "Chưa rõ ngày"', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: 'pm_completed', date: '2026-05-30' },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    const viDate = formatDate('2026-05-30')
    expect(viDate).toBe(new Date('2026-05-30').toLocaleDateString('vi-VN')) // sanity: VI thật
    expect(txt).toContain(viDate)
    expect(txt).not.toContain('Chưa rõ ngày')
  })

  // TC2: date=null (output hợp lệ BE khi timestamp rỗng) → 'Chưa rõ ngày', KHÔNG '—' trơ, KHÔNG 'null'.
  it('TC2: recent_maintenance.date=null → "Chưa rõ ngày" (KHÔNG em-dash trơ, KHÔNG chữ "null")', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: 'pm_completed', date: null },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const dateLine = w.get('[data-test="recent-maintenance-date"]')
    expect(dateLine.text()).toBe('Chưa rõ ngày')
    // KHÔNG em-dash trơ ở dòng ngày + KHÔNG rò chữ 'null'.
    expect(dateLine.text()).not.toBe('—')
    expect(w.text()).not.toContain('null')
  })

  // TC3: date='' (chuỗi rỗng) → CÙNG nhãn 'Chưa rõ ngày' (gộp với null).
  it("TC3: recent_maintenance.date='' (rỗng) → CÙNG nhãn 'Chưa rõ ngày' (gộp với null)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: 'pm_completed', date: '' },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(w.get('[data-test="recent-maintenance-date"]').text()).toBe('Chưa rõ ngày')
  })

  // TC4 (no-raw-leak, parity Vòng 17): chuỗi phi-ISO drift → KHÔNG leak thô, KHÔNG
  //   mis-parse câm. Bịt 2 LỚP rò:
  //   (a) '2026/13/99' → NaN khi new Date → formatDate fallback `return d` LEAK verbatim.
  //   (b) 'không rõ ngày 99' → V8 KHÔNG NaN (lenient parse → 1/1/1999) → formatDate ra
  //       ngày SAI plausible (mis-parse câm, còn nguy hơn). Guard ISO-strict ở view chặn
  //       CẢ HAI → 'Chưa rõ ngày' (KHÔNG dựa NaN-check của new Date).
  it("TC4: recent_maintenance.date phi-ISO (NaN HOẶC lenient-misparse) → KHÔNG leak/mis-parse, 'Chưa rõ ngày'", async () => {
    // sanity (a): '2026/13/99' NaN → formatDate fallback rò verbatim nếu render thẳng.
    expect(Number.isNaN(new Date('2026/13/99').getTime())).toBe(true)
    expect(formatDate('2026/13/99')).toBe('2026/13/99')
    // sanity (b): 'không rõ ngày 99' KHÔNG NaN (V8 lenient) → formatDate ra ngày SAI.
    expect(Number.isNaN(new Date('không rõ ngày 99').getTime())).toBe(false)
    for (const RAW of ['2026/13/99', 'không rõ ngày 99']) {
      getAssetScanInfoSpy.mockResolvedValue({
        ...PAYLOAD,
        recent_maintenance: { event_type: 'pm_completed', date: RAW },
      })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      const dateLine = w.get('[data-test="recent-maintenance-date"]')
      expect(dateLine.text(), `RAW=${RAW}`).toBe('Chưa rõ ngày')
      expect(w.text(), `RAW=${RAW} leak verbatim`).not.toContain(RAW)
    }
  })

  // TC5: parity Vòng 17 — event_type lạ + date=null → 'Khác' VÀ 'Chưa rõ ngày', KHÔNG rò raw.
  it("TC5: event_type='pm_aborted' (mã lạ) + date=null → 'Khác' (loại) VÀ 'Chưa rõ ngày' (ngày), KHÔNG rò raw", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: 'pm_aborted', date: null },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    expect(txt).toContain('Khác')
    expect(txt).toContain('Chưa rõ ngày')
    expect(txt).not.toContain('pm_aborted')
    expect(txt).not.toContain('_aborted')
  })

  // TC6: recent_maintenance=null → v-else 'Chưa có lịch sử bảo trì' (no-regress AC6).
  it("TC6: recent_maintenance=null → 'Chưa có lịch sử bảo trì' (v-else, no-regress)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, recent_maintenance: null })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    expect(txt).toContain('Chưa có lịch sử bảo trì')
    expect(w.find('[data-test="recent-maintenance-date"]').exists()).toBe(false)
  })

  // TC7: layout — date=null → card vẫn 2 dòng (loại sự kiện + ngày) + heading vẫn hiện.
  it('TC7: date=null → card vẫn 2 dòng (loại sự kiện + ngày), heading "Bảo trì gần nhất" vẫn hiện', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      recent_maintenance: { event_type: 'pm_completed', date: null },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(w.text()).toContain('Bảo trì gần nhất') // heading
    expect(w.find('[data-test="recent-maintenance-type"]').exists()).toBe(true)  // dòng 1: loại sự kiện
    expect(w.find('[data-test="recent-maintenance-date"]').exists()).toBe(true)  // dòng 2: ngày
    expect(w.get('[data-test="recent-maintenance-type"]').text()).toBe('Hoàn tất bảo trì')
    expect(w.get('[data-test="recent-maintenance-date"]').text()).toBe('Chưa rõ ngày')
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

  // (1b) Vòng 11 — defensive parity: next_pm_date là chuỗi 'YYYY-MM-DD' (BE
  //      _date_str_or_none → str|None, đối xứng next_calibration_date) → render
  //      NGÀY VI hợp lệ (toLocaleDateString('vi-VN')), TUYỆT ĐỐI không 'Invalid
  //      Date' và không lộ raw ISO 'YYYY-MM-DD' lên UI. Pin contract scheduleLabel
  //      khi BE đã chuẩn hoá kiểu (KHÔNG còn datetime.date thô → JSON string).
  it('next_pm_date="YYYY-MM-DD" → ngày VI hợp lệ (KHÔNG "Invalid Date", KHÔNG raw ISO)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD, next_pm_date: '2026-08-30', pm_overdue: false,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    // Ô PM hiển thị NGÀY VI thật (khớp formatter) — KHÔNG 'Chưa lên lịch'/'Cần kiểm tra'.
    const viDate = new Date('2026-08-30').toLocaleDateString('vi-VN')
    expect(formatDate('2026-08-30')).toBe(viDate) // sanity: formatter ra VI (không 'Invalid Date')
    expect(txt).toContain('Bảo trì định kỳ kế tiếp')
    expect(txt).toContain(viDate)
    expect(txt).not.toContain('Invalid Date')
    expect(txt).not.toContain('2026-08-30') // KHÔNG lộ raw ISO khi parse THÀNH CÔNG
    expect(txt).not.toContain('Chưa lên lịch')
    expect(txt).not.toContain('Cần kiểm tra')
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

  // ── R1 reason-when-disabled (ADR-IMM00-QR-SCAN-ACTION §D9 · vòng 7) ──────────
  //    Bịt lỗ "nút disabled mà KHÔNG có lý do". BE bất biến: enabled=False ⟹ reason
  //    != '' (kể cả status rỗng/lạ → hằng VI _LIFECYCLE_REASON_UNKNOWN). FE khoá
  //    contract: reason không rỗng → :title=reason + <li id=reason-${key}> khớp
  //    aria-describedby (NO DANGLING) + aria-label tận cùng = reason thực. reason
  //    là literal VI SSoT ở BE — FE CHỈ render (no hardcode, no-EN-leak).

  // FE TC-6 — disabled + reason _LIFECYCLE_REASON_UNKNOWN (status rỗng/lạ + đủ cap)
  //   → :title==reason · <li id=reason-${key}> tồn tại · aria-describedby trỏ ĐÚNG id
  //     (no dangling) · aria-label kết thúc bằng reason thực.
  it('disabled + reason _LIFECYCLE_REASON_UNKNOWN (status rỗng) → title=reason, <li id=reason-key> khớp aria-describedby (no dangling), aria-label tận cùng = reason', async () => {
    // Hằng VI BE phát khi status rỗng/lạ + đủ cap (SSoT ở BE — FE chỉ render).
    const UNKNOWN = 'Thiết bị không ở trạng thái cho phép thao tác này'
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      lifecycle_status: '', // status RỖNG (legacy/drift) — BE vẫn phát reason != ''
      available_actions: [
        { key: 'report_failure',      label: 'Báo hỏng',         route: 'IncidentCreate',    enabled: false, reason: UNKNOWN },
        { key: 'request_pm',          label: 'Yêu cầu bảo trì',  route: 'PMWorkOrderCreate', enabled: false, reason: UNKNOWN },
        { key: 'request_cm',          label: 'Yêu cầu sửa chữa', route: 'CMCreate',          enabled: false, reason: UNKNOWN },
        { key: 'request_calibration', label: 'Hiệu chuẩn',       route: 'CalibrationCreate', enabled: false, reason: UNKNOWN },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    // Đủ 4 nút render (KHÔNG ẩn nút chết).
    expect(w.findAll('[data-action-key]').length).toBe(4)
    for (const key of ['report_failure', 'request_pm', 'request_cm', 'request_calibration']) {
      const b = actionBtn(w, key)
      // disabled + title = reason VI thực.
      expect(b.attributes('disabled')).toBeDefined()
      expect(b.attributes('title')).toBe(UNKNOWN)
      // aria-label tận cùng = reason thực (KHÔNG trailing rỗng sau dấu ':').
      const label = b.attributes('aria-label') ?? ''
      expect(label.endsWith(UNKNOWN)).toBe(true)
      // aria-describedby trỏ ĐÚNG id <li> tồn tại (NO DANGLING).
      const describedby = b.attributes('aria-describedby')
      expect(describedby).toBe(`reason-${key}`)
      const li = w.find(`#reason-${key}`)
      expect(li.exists()).toBe(true)
      expect(li.text()).toContain(UNKNOWN)
    }
    // reason đọc được trên màn.
    expect(w.text()).toContain(UNKNOWN)
  })

  // FE TC-7 (defensive) — nếu reason RỖNG (payload bất thường, BE lẽ ra không phát)
  //   → aria-describedby KHÔNG trỏ id không tồn tại (undefined) + KHÔNG render <li>
  //     dangling + aria-label KHÔNG có trailing rỗng (chỉ nhãn action).
  //   Mục tiêu: kể cả payload bất thường, FE KHÔNG bao giờ dangling.
  it('defensive: disabled + reason RỖNG → aria-describedby=undefined (no dangling), KHÔNG <li>, aria-label KHÔNG trailing rỗng', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      lifecycle_status: 'Draft',
      available_actions: [
        // payload bất thường: disabled NHƯNG reason rỗng (BE đảm bảo không xảy ra —
        // đây là phòng thủ FE để KHÔNG dangling kể cả khi contract bị vi phạm).
        { key: 'report_failure',      label: 'Báo hỏng',         route: 'IncidentCreate',    enabled: false, reason: '' },
        { key: 'request_pm',          label: 'Yêu cầu bảo trì',  route: 'PMWorkOrderCreate', enabled: true,  reason: '' },
        { key: 'request_cm',          label: 'Yêu cầu sửa chữa', route: 'CMCreate',          enabled: true,  reason: '' },
        { key: 'request_calibration', label: 'Hiệu chuẩn',       route: 'CalibrationCreate', enabled: true,  reason: '' },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const b = actionBtn(w, 'report_failure')
    expect(b.attributes('disabled')).toBeDefined()
    // aria-describedby KHÔNG được trỏ tới id không tồn tại → undefined.
    expect(b.attributes('aria-describedby')).toBeUndefined()
    // KHÔNG render <li> reason cho action reason rỗng → KHÔNG dangling.
    expect(w.find('#reason-report_failure').exists()).toBe(false)
    // aria-label KHÔNG có trailing rỗng (không kết thúc bằng ': ' lủng lẳng) —
    // chỉ là nhãn action.
    const label = b.attributes('aria-label') ?? ''
    expect(label.endsWith(': ')).toBe(false)
    expect(label.trim().endsWith(':')).toBe(false)
    expect(label).toBe('Báo hỏng')
  })

  // FE TC-7b (defensive bất biến tổng quát) — KHÔNG bao giờ có nút disabled mà
  //   aria-describedby trỏ <li> KHÔNG tồn tại, dù reason rỗng hay không.
  it('bất biến: mọi nút disabled — aria-describedby (nếu set) PHẢI trỏ <li> tồn tại (no dangling toàn cục)', async () => {
    const UNKNOWN = 'Thiết bị không ở trạng thái cho phép thao tác này'
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      lifecycle_status: 'GARBAGE', // status LẠ ngoài enum
      available_actions: [
        { key: 'report_failure',      label: 'Báo hỏng',         route: 'IncidentCreate',    enabled: false, reason: UNKNOWN },
        { key: 'request_pm',          label: 'Yêu cầu bảo trì',  route: 'PMWorkOrderCreate', enabled: false, reason: '' /* bất thường */ },
        { key: 'request_cm',          label: 'Yêu cầu sửa chữa', route: 'CMCreate',          enabled: false, reason: UNKNOWN },
        { key: 'request_calibration', label: 'Hiệu chuẩn',       route: 'CalibrationCreate', enabled: true,  reason: '' },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    for (const b of w.findAll('[data-action-key]')) {
      const describedby = b.attributes('aria-describedby')
      if (describedby) {
        // nếu có aria-describedby → <li> tương ứng PHẢI tồn tại (no dangling).
        expect(w.find(`#${describedby}`).exists()).toBe(true)
      }
    }
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

  // ── vòng 8 (FE-6) — status pill no-EN/raw-code/empty leak ────────────────────
  //    BE phát lifecycle_status rỗng/lạ (legacy/drift, services/imm00.py:317/597
  //    `or ""`). statusLabel computed đọc qua SSoT lifecycleStatusLabel → fallback
  //    'Không xác định' (vòng 8 FE-6). Pill PHẢI render nhãn VI fallback, KHÔNG raw
  //    code, KHÔNG box trống. Fix tại nguồn mapper (constants/labels.ts) → tự lan
  //    tới màn quét QR (KHÔNG cần sửa view).

  // helper: lấy status pill qua anchor ỔN ĐỊNH data-test="scan-status" (vòng 39).
  //   Trước đây heuristic findAll('span').find('rounded-full') — mong manh, đụng cả
  //   overdue-badge (pm/calibration) + CTA-chip 'Cần làm ngay' (cùng rounded-full).
  const statusPill = (w: ReturnType<typeof mount>) => w.find('[data-test="scan-status"]')

  it("lifecycle_status='' (legacy/rỗng) → status pill nhãn VI 'Không xác định' (KHÔNG box trống, KHÔNG crash)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, lifecycle_status: '' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const pill = statusPill(w)
    expect(pill.exists(), 'không tìm thấy status pill').toBe(true)
    // Pill render nhãn VI fallback non-empty (KHÔNG box trống vô nghĩa).
    expect(pill.text()).toBe('Không xác định')
    expect(pill.text().length).toBeGreaterThan(0)
    // Class trung tính gray (parity với label fallback) — KHÔNG màu trạng thái khác.
    expect(pill.classes().join(' ')).toContain('bg-gray-100')
    // KHÔNG crash → không màn lỗi.
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  it("lifecycle_status='LegacyUnknown' (mã lạ/drift) → pill 'Không xác định' (KHÔNG leak raw code EN)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, lifecycle_status: 'LegacyUnknown' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const pill = statusPill(w)
    expect(pill.exists(), 'không tìm thấy status pill').toBe(true)
    expect(pill.text()).toBe('Không xác định')
    // KHÔNG leak mã thô lên pill / toàn màn.
    expect(pill.text()).not.toContain('LegacyUnknown')
    expect(w.text()).not.toContain('LegacyUnknown')
    // KHÔNG leak mã thô trong aria-label (no-EN/raw-code-leak ở CẢ aria-label).
    expect(pill.attributes('aria-label')).not.toContain('LegacyUnknown')
    // Class trung tính.
    expect(pill.classes().join(' ')).toContain('bg-gray-100')
  })

  it("lifecycle_status='In Use' (legacy EN drift) → pill 'Không xác định', KHÔNG rò 'In Use'", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, lifecycle_status: 'In Use' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const pill = statusPill(w)
    expect(pill.text()).toBe('Không xác định')
    expect(w.text()).not.toContain('In Use')
    // no-EN-leak trong aria-label: KHÔNG rò mã 'In Use'.
    expect(pill.attributes('aria-label')).not.toContain('In Use')
  })

  // ── Vòng 19: DÒNG NGÀY LỊCH PM / Hiệu chuẩn — guard ISO-strict no-raw-leak ────
  //    Mở rộng guard ISO-strict Vòng 18 (recent_maintenance.date) sang 2 trường
  //    lịch next_pm_date / next_calibration_date, VẪN presence-aware:
  //      • key ABSENT (undefined, payload stale) → 'Cần kiểm tra' (giữ)
  //      • key PRESENT + null/''                  → 'Chưa lên lịch' (giữ)
  //      • key PRESENT + ISO hợp lệ               → formatDate VI (no-regress)
  //      • key PRESENT + chuỗi phi-ISO/drift      → 'Chưa rõ ngày' (LỖI ĐANG SỬA:
  //        trước đây leak verbatim qua nhánh NaN-fallback `return d` của formatDate,
  //        HOẶC mis-parse câm ra ngày sai do V8 lenient-parse).
  //    Helper formatIsoDateLabel DÙNG CHUNG 1 SSoT cho cả 3 dòng ngày (parity).

  // helper: lấy dòng ngày PM / Hiệu chuẩn theo data-test (KHÔNG lẫn badge/heading).
  const pmDateLine = (w: ReturnType<typeof mount>) => w.get('[data-test="next-pm-date"]')
  const calDateLine = (w: ReturnType<typeof mount>) => w.get('[data-test="next-calibration-date"]')

  // TC-PM-1 (AC1 no-regress): ISO hợp lệ → formatDate VI, KHÔNG nhãn fallback nào.
  it("TC-PM-1: next_pm_date='2026-08-30' (ISO hợp lệ) → '30/08/2026' VI, KHÔNG 'Chưa rõ ngày'/'Chưa lên lịch'/'Cần kiểm tra'", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, next_pm_date: '2026-08-30' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const viDate = formatDate('2026-08-30')
    expect(viDate).toBe(new Date('2026-08-30').toLocaleDateString('vi-VN')) // sanity: VI thật
    expect(pmDateLine(w).text()).toBe(viDate)
    const t = pmDateLine(w).text()
    expect(t).not.toContain('Chưa rõ ngày')
    expect(t).not.toContain('Chưa lên lịch')
    expect(t).not.toContain('Cần kiểm tra')
  })

  // TC-PM-2 (AC2 presence-aware): null (key có mặt) → 'Chưa lên lịch';
  //   key ABSENT (undefined) → 'Cần kiểm tra'. Hai nhãn KHÁC nhau, KHÔNG gộp.
  it("TC-PM-2: next_pm_date=null → 'Chưa lên lịch'; next_pm_date ABSENT → 'Cần kiểm tra' (2 nhãn khác nhau)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, next_pm_date: null })
    const w1 = mount(AssetScanInfoView)
    await flushPromises()
    expect(pmDateLine(w1).text()).toBe('Chưa lên lịch')

    const partial: Record<string, unknown> = { ...PAYLOAD }
    delete partial.next_pm_date
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w2 = mount(AssetScanInfoView)
    await flushPromises()
    expect(pmDateLine(w2).text()).toBe('Cần kiểm tra')
  })

  // TC-PM-3 (AC3 no-raw-leak): chuỗi phi-ISO/drift → 'Chưa rõ ngày' + KHÔNG leak RAW.
  it("TC-PM-3: next_pm_date phi-ISO (pending/30-08-2026/2026/08/30/'không rõ 99'/N/A) → 'Chưa rõ ngày', KHÔNG leak RAW", async () => {
    for (const RAW of ['pending', '30-08-2026', '2026/08/30', 'không rõ 99', 'N/A']) {
      getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, next_pm_date: RAW })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      expect(pmDateLine(w).text(), `RAW=${RAW}`).toBe('Chưa rõ ngày')
      expect(w.text(), `RAW=${RAW} leak verbatim`).not.toContain(RAW)
    }
  })

  // TC-PM-4 (AC4 mis-parse câm): ISO-shape phi lý → 'Chưa rõ ngày' (loại qua NaN sau regex).
  it("TC-PM-4: next_pm_date ISO-shape phi lý ('2026-13-99'/'2026-02-31') → 'Chưa rõ ngày' (KHÔNG ngày sai lenient)", async () => {
    for (const RAW of ['2026-13-99', '2026-02-31']) {
      getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, next_pm_date: RAW })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      expect(pmDateLine(w).text(), `RAW=${RAW}`).toBe('Chưa rõ ngày')
      expect(w.text(), `RAW=${RAW} leak verbatim`).not.toContain(RAW)
    }
  })

  // TC-CAL-1..4: lặp y hệt cho next_calibration_date (đối xứng AC3 chiều hiệu chuẩn).
  it("TC-CAL-1: next_calibration_date='2026-09-15' (ISO hợp lệ) → '15/09/2026' VI, KHÔNG nhãn fallback", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, next_calibration_date: '2026-09-15' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const viDate = formatDate('2026-09-15')
    expect(viDate).toBe(new Date('2026-09-15').toLocaleDateString('vi-VN'))
    expect(calDateLine(w).text()).toBe(viDate)
    const t = calDateLine(w).text()
    expect(t).not.toContain('Chưa rõ ngày')
    expect(t).not.toContain('Chưa lên lịch')
    expect(t).not.toContain('Cần kiểm tra')
  })

  it("TC-CAL-2: next_calibration_date=null → 'Chưa lên lịch'; ABSENT → 'Cần kiểm tra' (2 nhãn khác nhau)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, next_calibration_date: null })
    const w1 = mount(AssetScanInfoView)
    await flushPromises()
    expect(calDateLine(w1).text()).toBe('Chưa lên lịch')

    const partial: Record<string, unknown> = { ...PAYLOAD }
    delete partial.next_calibration_date
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w2 = mount(AssetScanInfoView)
    await flushPromises()
    expect(calDateLine(w2).text()).toBe('Cần kiểm tra')
  })

  it("TC-CAL-3: next_calibration_date phi-ISO → 'Chưa rõ ngày', KHÔNG leak RAW", async () => {
    for (const RAW of ['pending', '15-09-2026', '2026/09/15', 'không rõ 99', 'N/A']) {
      getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, next_calibration_date: RAW })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      expect(calDateLine(w).text(), `RAW=${RAW}`).toBe('Chưa rõ ngày')
      expect(w.text(), `RAW=${RAW} leak verbatim`).not.toContain(RAW)
    }
  })

  it("TC-CAL-4: next_calibration_date ISO-shape phi lý ('2026-13-99'/'2026-02-31') → 'Chưa rõ ngày'", async () => {
    for (const RAW of ['2026-13-99', '2026-02-31']) {
      getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, next_calibration_date: RAW })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      expect(calDateLine(w).text(), `RAW=${RAW}`).toBe('Chưa rõ ngày')
      expect(w.text(), `RAW=${RAW} leak verbatim`).not.toContain(RAW)
    }
  })

  // TC-PARITY (AC5): cùng RAW phi-ISO gán đồng thời cả 3 trường ngày → CẢ 3 dòng
  //   đều 'Chưa rõ ngày' (chứng minh 1 helper SSoT, KHÔNG đường xử lý lệch).
  it("TC-PARITY: cùng RAW phi-ISO gán next_pm_date + next_calibration_date + recent_maintenance.date → CẢ 3 dòng 'Chưa rõ ngày' (1 helper SSoT)", async () => {
    const RAW = 'không rõ 99'
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      next_pm_date: RAW,
      next_calibration_date: RAW,
      recent_maintenance: { event_type: 'pm_completed', date: RAW },
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(pmDateLine(w).text()).toBe('Chưa rõ ngày')
    expect(calDateLine(w).text()).toBe('Chưa rõ ngày')
    expect(w.get('[data-test="recent-maintenance-date"]').text()).toBe('Chưa rõ ngày')
    expect(w.text()).not.toContain(RAW)
  })

  // TC-OVERDUE-NOREGRESS (AC6): guard ngày KHÔNG nuốt ngày ISO hợp lệ, KHÔNG đổi
  //   badge quá hạn (đọc TRỰC TIẾP cờ server, KHÔNG so client-clock).
  it("TC-OVERDUE-NOREGRESS: next_pm_date='2020-01-01' quá khứ + pm_overdue=false → KHÔNG badge VÀ dòng ngày vẫn formatDate VI; pm_overdue=true → badge VI", async () => {
    // (a) quá khứ + cờ false → KHÔNG badge, nhưng ngày ISO vẫn render VI (guard không nuốt).
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, next_pm_date: '2020-01-01', pm_overdue: false })
    const w1 = mount(AssetScanInfoView)
    await flushPromises()
    expect(w1.text()).not.toContain('Quá hạn bảo trì')
    expect(pmDateLine(w1).text()).toBe(formatDate('2020-01-01'))
    expect(pmDateLine(w1).text()).not.toContain('Chưa rõ ngày')

    // (b) cờ true → badge VI hiển thị (no-regress).
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, next_pm_date: '2020-01-01', pm_overdue: true })
    const w2 = mount(AssetScanInfoView)
    await flushPromises()
    expect(w2.text()).toContain('Quá hạn bảo trì')
    expect(pmDateLine(w2).text()).toBe(formatDate('2020-01-01'))
  })

  // TC-NO-KEY-LEAK (AC7): mọi case — KHÔNG render literal key / 'null'/'undefined'/'NaN'.
  it("TC-NO-KEY-LEAK: phi-ISO + null + ABSENT — w.text() KHÔNG chứa key thô hay 'null'/'undefined'/'NaN'", async () => {
    // phi-ISO trên cả 2 trường lịch.
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD, next_pm_date: '2026-13-99', next_calibration_date: 'pending',
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const t = w.text()
    for (const leak of ['next_pm_date', 'next_calibration_date', 'pm_overdue', 'null', 'undefined', 'NaN']) {
      expect(t, `leak=${leak}`).not.toContain(leak)
    }

    // null (key có mặt) + ABSENT key — vẫn KHÔNG leak 'null'/'undefined' thô.
    const partial: Record<string, unknown> = { ...PAYLOAD, next_pm_date: null }
    delete partial.next_calibration_date
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w2 = mount(AssetScanInfoView)
    await flushPromises()
    const t2 = w2.text()
    for (const leak of ['next_pm_date', 'next_calibration_date', 'null', 'undefined', 'NaN']) {
      expect(t2, `leak=${leak}`).not.toContain(leak)
    }
  })

  // ── Vòng 20: route-resolvability allow-list + raw-key fallback (anti-drift) ───
  //    Bịt 2 lỗ ở cụm CTA màn quét QR khi BE drift:
  //    (1) route LẠ ngoài allow-list FE (typo/route mới chưa map) → KHÔNG router.push
  //        route lạ (tránh uncaught Vue Router rejection) → nút render DISABLED +
  //        reason VI ROUTE_UNAVAILABLE_REASON (giữ bất biến 'disabled ⟹ reason != ""').
  //    (2) key LẠ ngoài SCAN_ACTION_LABELS → nhãn + aria-label KHÔNG leak raw key,
  //        dùng nhãn VI fallback an toàn ('Thao tác khác').
  //    capability vẫn do BE (a.enabled) quyết — FE CHỈ thêm lớp resolvability + nhãn.

  // FE-TDD-1: click route hợp lệ enabled=true (IncidentCreate) → push 1 lần đúng
  //   { name, query:{asset,source:'qr-scan'} }, KHÔNG qr_token (regression guard).
  it('FE-TDD-1: route hợp lệ enabled=true (IncidentCreate) → push 1 lần đúng query, KHÔNG qr_token', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      available_actions: [
        { key: 'report_failure', label: 'Báo hỏng', route: 'IncidentCreate', enabled: true, reason: '' },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const b = actionBtn(w, 'report_failure')
    // route hợp lệ → KHÔNG bị chặn nhầm (enabled, click được).
    expect(b.attributes('disabled')).toBeUndefined()
    expect(b.attributes('aria-disabled')).toBeUndefined()
    await b.trigger('click')
    expect(pushSpy).toHaveBeenCalledTimes(1)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'IncidentCreate',
      query: { asset: 'AC-ASSET-2026-00042', source: 'qr-scan' },
    })
    const arg = pushSpy.mock.calls[0][0]
    expect(JSON.stringify(arg)).not.toContain('qr_token')
    expect(Object.keys(arg.query)).toEqual(['asset', 'source'])
  })

  // FE-TDD-2: route='SomeBogusRoute' (ngoài allow-list) enabled=true → render DISABLED
  //   + reason VI != '' trong cụm aria-live; click → pushSpy KHÔNG gọi (no-op).
  it("FE-TDD-2: route='SomeBogusRoute' enabled=true → nút DISABLED + reason VI; click no-op (KHÔNG navigate sai)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      available_actions: [
        { key: 'report_failure', label: 'Báo hỏng', route: 'SomeBogusRoute', enabled: true, reason: '' },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const b = actionBtn(w, 'report_failure')
    // route lạ → render disabled dù BE enabled=true.
    expect(b.attributes('disabled')).toBeDefined()
    expect(b.attributes('aria-disabled')).toBe('true')
    // reason VI != '' (bất biến disabled ⟹ reason) — đọc được trong cụm aria-live.
    const reason = 'Thao tác này hiện chưa khả dụng trên thiết bị của bạn'
    expect(b.attributes('title')).toBe(reason)
    const li = w.find('#reason-report_failure')
    expect(li.exists()).toBe(true)
    expect(li.text()).toContain(reason)
    expect(w.text()).toContain(reason)
    // click → KHÔNG navigate (no-op, KHÔNG uncaught rejection).
    await b.trigger('click')
    expect(pushSpy).not.toHaveBeenCalled()
    // raw route name KHÔNG leak ra DOM.
    expect(w.text()).not.toContain('SomeBogusRoute')
  })

  // FE-TDD-3: key='request_inspection' (không trong SCAN_ACTION_LABELS) route hợp lệ →
  //   nhãn nút + aria-label KHÔNG chứa 'request_inspection'; chứa nhãn VI fallback.
  it("FE-TDD-3: key='request_inspection' (ngoài labels) → nhãn + aria-label KHÔNG leak raw key, dùng 'Thao tác khác'", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      available_actions: [
        // route hợp lệ để cô lập trục key-fallback (không lẫn disabled-route-lạ).
        { key: 'request_inspection', label: 'Inspect', route: 'IncidentCreate', enabled: true, reason: '' },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const b = actionBtn(w, 'request_inspection')
    // nhãn nút = fallback VI an toàn, KHÔNG raw key.
    expect(b.text()).toContain('Thao tác khác')
    expect(b.text()).not.toContain('request_inspection')
    // aria-label KHÔNG leak raw key.
    const label = b.attributes('aria-label') ?? ''
    expect(label).not.toContain('request_inspection')
    // toàn màn KHÔNG leak raw key.
    expect(w.text()).not.toContain('request_inspection')
  })

  // FE-TDD-4: bất biến — duyệt mọi action render: phần tử nào disabled (do !enabled
  //   HOẶC route lạ) đều có reason VI khác rỗng (parity invariant BE).
  it('FE-TDD-4: bất biến — mọi nút disabled (do !enabled HOẶC route lạ) đều có reason VI != ""', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      lifecycle_status: 'Out of Service',
      available_actions: [
        // (a) disabled do BE (!enabled) + reason BE.
        { key: 'request_pm', label: 'Yêu cầu bảo trì', route: 'PMWorkOrderCreate', enabled: false, reason: 'Thiết bị đang ngừng hoạt động' },
        // (b) enabled=true NHƯNG route lạ → FE chặn → disabled + reason FE.
        { key: 'request_cm', label: 'Yêu cầu sửa chữa', route: 'BogusCM', enabled: true, reason: '' },
        // (c) enabled + route hợp lệ → KHÔNG disabled.
        { key: 'report_failure', label: 'Báo hỏng', route: 'IncidentCreate', enabled: true, reason: '' },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    for (const b of w.findAll('[data-action-key]')) {
      if (b.attributes('disabled') !== undefined) {
        // mọi nút disabled PHẢI có reason VI != '' (title + cụm aria-live).
        const title = b.attributes('title') ?? ''
        expect(title.length, `key=${b.attributes('data-action-key')}`).toBeGreaterThan(0)
        const key = b.attributes('data-action-key')
        const li = w.find(`#reason-${key}`)
        expect(li.exists(), `li reason cho ${key}`).toBe(true)
        expect(li.text().trim().length).toBeGreaterThan(0)
      }
    }
    // báo hỏng (route hợp lệ + enabled) KHÔNG bị chặn nhầm.
    expect(actionBtn(w, 'report_failure').attributes('disabled')).toBeUndefined()
  })

  // FE-TDD-5: 4 route allow-list FE == 4 route hợp lệ; mỗi route trong allow-list →
  //   4 CTA chuẩn KHÔNG bị chặn nhầm, vẫn enabled & click được.
  it('FE-TDD-5: 4 route allow-list (IncidentCreate/PMWorkOrderCreate/CMCreate/CalibrationCreate) → 4 CTA KHÔNG bị chặn nhầm', async () => {
    getAssetScanInfoSpy.mockResolvedValue(PAYLOAD) // ACTIONS_ALL_ENABLED — 4 route hợp lệ
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const cases: Array<[string, string]> = [
      ['report_failure', 'IncidentCreate'],
      ['request_pm', 'PMWorkOrderCreate'],
      ['request_cm', 'CMCreate'],
      ['request_calibration', 'CalibrationCreate'],
    ]
    for (const [key, routeName] of cases) {
      const b = actionBtn(w, key)
      // 4 route chuẩn KHÔNG bị allow-list chặn nhầm.
      expect(b.attributes('disabled'), `key=${key}`).toBeUndefined()
      expect(b.attributes('aria-disabled'), `key=${key}`).toBeUndefined()
      pushSpy.mockClear()
      await b.trigger('click')
      expect(pushSpy).toHaveBeenCalledWith({
        name: routeName,
        query: { asset: 'AC-ASSET-2026-00042', source: 'qr-scan' },
      })
    }
  })

  // ── Vòng 21: OVERDUE-CTA urgency (ADR-IMM00-QR-SCAN-ACTION §overdue-cta) ──────
  //    Nối cờ quá hạn (pm_overdue/calibration_overdue — derive SERVER-SIDE) với CTA
  //    tương ứng ở màn quét QR: nút 'Yêu cầu bảo trì'/'Hiệu chuẩn' mang affordance
  //    "cần làm ngay" KHI VÀ CHỈ KHI action ĐỒNG THỜI effectiveEnabled. Map SSoT
  //    THUẦN-FE (presentation-only, KHÔNG thêm field BE, KHÔNG so client-clock):
  //      pm_overdue===true ↦ key 'request_pm'; calibration_overdue===true ↦ 'request_calibration'.
  //    Disabled ưu tiên hơn overdue (không dụ KTV bấm nút khoá). report_failure/request_cm
  //    KHÔNG bao giờ urgency (không có cờ tương ứng). Affordance: chip VI 'Cần làm ngay'
  //    + attr data-overdue-cta=key + aria-label nối hậu tố VI (a11y: không chỉ-màu).

  const URGENT_HINT = 'Cần làm ngay'
  // helper: nút urgency = có attr data-overdue-cta == key.
  const overdueAttr = (w: ReturnType<typeof mount>, key: string) =>
    actionBtn(w, key).attributes('data-overdue-cta')

  // TC-1: pm_overdue=true + request_pm enabled → request_pm urgency (chip + attr +
  //   aria-label hậu tố VI); request_calibration KHÔNG urgency. KHÔNG leak raw key.
  it("TC-OVERDUE-CTA-1: pm_overdue=true + request_pm enabled → request_pm urgency (chip 'Cần làm ngay' + data-overdue-cta + aria-label hậu tố); request_calibration KHÔNG urgency; KHÔNG leak raw key", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      next_pm_date: '2026-01-01',
      pm_overdue: true,
      calibration_overdue: false,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const pm = actionBtn(w, 'request_pm')
    // attr đánh dấu urgency = key (test bám attr, KHÔNG bám màu).
    expect(overdueAttr(w, 'request_pm')).toBe('request_pm')
    // chip text VI 'Cần làm ngay' nằm TRONG nút request_pm (a11y: có nội dung text).
    expect(pm.text()).toContain(URGENT_HINT)
    // aria-label nối hậu tố VI cho urgency.
    const label = pm.attributes('aria-label') ?? ''
    expect(label).toContain(URGENT_HINT)
    expect(label).toContain('Yêu cầu bảo trì')
    // request_calibration KHÔNG urgency (cờ calibration=false).
    expect(overdueAttr(w, 'request_calibration')).toBeUndefined()
    expect(actionBtn(w, 'request_calibration').text()).not.toContain(URGENT_HINT)
    // KHÔNG leak raw key/cờ ra DOM text.
    const t = w.text()
    expect(t).not.toContain('pm_overdue')
    expect(t).not.toContain('request_pm')
    expect(t).not.toContain('calibration_overdue')
  })

  // TC-2: calibration_overdue=true + request_calibration enabled → urgency đúng trên
  //   request_calibration; request_pm KHÔNG urgency. KHÔNG leak raw key.
  it("TC-OVERDUE-CTA-2: calibration_overdue=true + request_calibration enabled → request_calibration urgency; request_pm KHÔNG urgency; KHÔNG leak raw key", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      next_calibration_date: '2026-01-01',
      pm_overdue: false,
      calibration_overdue: true,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const cal = actionBtn(w, 'request_calibration')
    expect(overdueAttr(w, 'request_calibration')).toBe('request_calibration')
    expect(cal.text()).toContain(URGENT_HINT)
    const label = cal.attributes('aria-label') ?? ''
    expect(label).toContain(URGENT_HINT)
    expect(label).toContain('Hiệu chuẩn')
    // request_pm KHÔNG urgency.
    expect(overdueAttr(w, 'request_pm')).toBeUndefined()
    expect(actionBtn(w, 'request_pm').text()).not.toContain(URGENT_HINT)
    const t = w.text()
    expect(t).not.toContain('calibration_overdue')
    expect(t).not.toContain('request_calibration')
    expect(t).not.toContain('pm_overdue')
  })

  // TC-3: CẢ HAI overdue=true → CẢ request_pm VÀ request_calibration urgency;
  //   report_failure/request_cm KHÔNG urgency (không có cờ tương ứng).
  it("TC-OVERDUE-CTA-3: CẢ pm_overdue + calibration_overdue=true → CẢ request_pm VÀ request_calibration urgency; report_failure/request_cm KHÔNG urgency", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      next_pm_date: '2026-01-01',
      next_calibration_date: '2026-01-01',
      pm_overdue: true,
      calibration_overdue: true,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(overdueAttr(w, 'request_pm')).toBe('request_pm')
    expect(overdueAttr(w, 'request_calibration')).toBe('request_calibration')
    expect(actionBtn(w, 'request_pm').text()).toContain(URGENT_HINT)
    expect(actionBtn(w, 'request_calibration').text()).toContain(URGENT_HINT)
    // 2 action KHÔNG có cờ tương ứng → KHÔNG bao giờ urgency.
    expect(overdueAttr(w, 'report_failure')).toBeUndefined()
    expect(overdueAttr(w, 'request_cm')).toBeUndefined()
    expect(actionBtn(w, 'report_failure').text()).not.toContain(URGENT_HINT)
    expect(actionBtn(w, 'request_cm').text()).not.toContain(URGENT_HINT)
  })

  // TC-4: pm_overdue=true NHƯNG request_pm disabled (lifecycle Out of Service khoá
  //   request_pm HOẶC route lạ → effectiveEnabled=false) → KHÔNG urgency, nút vẫn
  //   disabled + reason cũ giữ nguyên (disabled ưu tiên hơn overdue).
  it("TC-OVERDUE-CTA-4: pm_overdue=true NHƯNG request_pm disabled (lifecycle) → KHÔNG urgency, nút vẫn disabled + reason cũ (disabled ưu tiên)", async () => {
    const OOS_REASON = 'Thiết bị đang ngừng hoạt động — chỉ cho phép báo hỏng / yêu cầu sửa chữa'
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      lifecycle_status: 'Out of Service',
      next_pm_date: '2026-01-01',
      pm_overdue: true,
      calibration_overdue: false,
      available_actions: [
        { key: 'report_failure',      label: 'Báo hỏng',         route: 'IncidentCreate',    enabled: true,  reason: '' },
        { key: 'request_cm',          label: 'Yêu cầu sửa chữa', route: 'CMCreate',          enabled: true,  reason: '' },
        { key: 'request_pm',          label: 'Yêu cầu bảo trì',  route: 'PMWorkOrderCreate', enabled: false, reason: OOS_REASON },
        { key: 'request_calibration', label: 'Hiệu chuẩn',       route: 'CalibrationCreate', enabled: false, reason: OOS_REASON },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const pm = actionBtn(w, 'request_pm')
    // KHÔNG urgency (disabled ưu tiên).
    expect(overdueAttr(w, 'request_pm')).toBeUndefined()
    expect(pm.text()).not.toContain(URGENT_HINT)
    // nút vẫn disabled + reason cũ giữ nguyên.
    expect(pm.attributes('disabled')).toBeDefined()
    expect(pm.attributes('aria-disabled')).toBe('true')
    expect(pm.attributes('title')).toBe(OOS_REASON)
    // aria-label KHÔNG có hậu tố urgency (đi nhánh disabled, không phải urgency).
    const label = pm.attributes('aria-label') ?? ''
    expect(label).not.toContain(URGENT_HINT)
    expect(label.endsWith(OOS_REASON)).toBe(true)

    // route lạ (effectiveEnabled=false vì route ∉ allow-list) — cũng KHÔNG urgency.
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      next_pm_date: '2026-01-01',
      pm_overdue: true,
      available_actions: [
        { key: 'request_pm', label: 'Yêu cầu bảo trì', route: 'BogusPM', enabled: true, reason: '' },
      ],
    })
    const w2 = mount(AssetScanInfoView)
    await flushPromises()
    const pm2 = actionBtn(w2, 'request_pm')
    expect(overdueAttr(w2, 'request_pm')).toBeUndefined()
    expect(pm2.attributes('disabled')).toBeDefined()
    expect(pm2.text()).not.toContain(URGENT_HINT)
  })

  // TC-5: overdue absent/undefined → KHÔNG urgency; overdue=false → KHÔNG urgency
  //   ('không bịa khi absent', parity cờ pill).
  it("TC-OVERDUE-CTA-5: pm_overdue/calibration_overdue ABSENT → KHÔNG urgency; =false → KHÔNG urgency (không bịa khi absent)", async () => {
    // (a) ABSENT (delete cả 2 cờ).
    const partial: Record<string, unknown> = { ...PAYLOAD }
    delete partial.pm_overdue
    delete partial.calibration_overdue
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w1 = mount(AssetScanInfoView)
    await flushPromises()
    for (const key of ['report_failure', 'request_pm', 'request_cm', 'request_calibration']) {
      expect(overdueAttr(w1, key), `absent key=${key}`).toBeUndefined()
      expect(actionBtn(w1, key).text(), `absent key=${key}`).not.toContain(URGENT_HINT)
    }
    // (b) =false rõ ràng.
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, pm_overdue: false, calibration_overdue: false })
    const w2 = mount(AssetScanInfoView)
    await flushPromises()
    for (const key of ['report_failure', 'request_pm', 'request_cm', 'request_calibration']) {
      expect(overdueAttr(w2, key), `false key=${key}`).toBeUndefined()
      expect(actionBtn(w2, key).text(), `false key=${key}`).not.toContain(URGENT_HINT)
    }
  })

  // TC-6: a11y — nút urgency có aria-label hậu tố VI riêng + chip có nội dung text
  //   (không chỉ màu); pill 'Quá hạn bảo trì'/'Quá hạn hiệu chuẩn' ở card maintenance
  //   VẪN render (regression-guard không phá vòng trước).
  it("TC-OVERDUE-CTA-6: a11y — nút urgency có aria-label hậu tố VI + chip text; pill 'Quá hạn bảo trì'/'Quá hạn hiệu chuẩn' card maintenance VẪN render (regression)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      next_pm_date: '2026-01-01',
      next_calibration_date: '2026-01-01',
      pm_overdue: true,
      calibration_overdue: true,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    // a11y: aria-label hậu tố VI (không chỉ màu) trên CẢ HAI nút urgency.
    expect(actionBtn(w, 'request_pm').attributes('aria-label') ?? '').toContain(URGENT_HINT)
    expect(actionBtn(w, 'request_calibration').attributes('aria-label') ?? '').toContain(URGENT_HINT)
    // chip có nội dung text (không phải span rỗng chỉ màu).
    expect(actionBtn(w, 'request_pm').text()).toContain(URGENT_HINT)
    expect(actionBtn(w, 'request_calibration').text()).toContain(URGENT_HINT)
    // regression-guard: pill quá hạn ở card 'Bảo trì gần nhất' VẪN render y như cũ.
    expect(w.text()).toContain('Quá hạn bảo trì')
    expect(w.text()).toContain('Quá hạn hiệu chuẩn')
    expect(w.find('[aria-label="Cảnh báo: quá hạn bảo trì định kỳ"]').exists()).toBe(true)
    expect(w.find('[aria-label="Cảnh báo: quá hạn hiệu chuẩn"]').exists()).toBe(true)
  })

  // TC-7: regression — effectiveEnabled/effectiveReason/runAction KHÔNG đổi hành vi.
  //   click nút urgency vẫn push name=route query {asset,source:'qr-scan'} KHÔNG qr_token;
  //   click nút disabled vẫn no-op; available_actions=[] → section CTA không render.
  it("TC-OVERDUE-CTA-7: regression — click nút urgency vẫn push đúng query KHÔNG qr_token; disabled no-op; available_actions=[] → section CTA không render", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      next_pm_date: '2026-01-01',
      pm_overdue: true,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const pm = actionBtn(w, 'request_pm')
    // nút urgency vẫn click được + push đúng query (runAction KHÔNG đổi).
    expect(pm.attributes('disabled')).toBeUndefined()
    await pm.trigger('click')
    expect(pushSpy).toHaveBeenCalledTimes(1)
    expect(pushSpy).toHaveBeenCalledWith({
      name: 'PMWorkOrderCreate',
      query: { asset: 'AC-ASSET-2026-00042', source: 'qr-scan' },
    })
    const arg = pushSpy.mock.calls[0][0]
    expect(JSON.stringify(arg)).not.toContain('qr_token')
    expect(Object.keys(arg.query)).toEqual(['asset', 'source'])

    // available_actions=[] → section CTA không render, không throw.
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, pm_overdue: true, available_actions: [] })
    const w2 = mount(AssetScanInfoView)
    await flushPromises()
    expect(w2.findAll('[data-action-key]').length).toBe(0)
    expect(w2.text()).not.toContain('Thao tác nhanh')
  })

  // TC-8: no-leak parity — với mọi tổ hợp overdue, w.text()/html KHÔNG chứa raw key
  //   'pm_overdue'/'calibration_overdue'/'request_pm'/'request_calibration'/route thô.
  it("TC-OVERDUE-CTA-8: no-leak parity — mọi tổ hợp overdue → KHÔNG leak 'pm_overdue'/'calibration_overdue'/'request_pm'/'request_calibration'/route thô", async () => {
    const combos = [
      { pm_overdue: true,  calibration_overdue: false },
      { pm_overdue: false, calibration_overdue: true },
      { pm_overdue: true,  calibration_overdue: true },
      { pm_overdue: false, calibration_overdue: false },
    ]
    for (const c of combos) {
      getAssetScanInfoSpy.mockResolvedValue({
        ...PAYLOAD,
        next_pm_date: '2026-01-01',
        next_calibration_date: '2026-01-01',
        ...c,
      })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      const t = w.text()
      const html = w.html()
      for (const leak of ['pm_overdue', 'calibration_overdue', 'request_pm', 'request_calibration',
        'PMWorkOrderCreate', 'CalibrationCreate', 'IncidentCreate', 'CMCreate']) {
        expect(t, `combo=${JSON.stringify(c)} text leak=${leak}`).not.toContain(leak)
        // html: raw key/route KHÔNG được render ra DOM nội dung; data-action-key là
        // attr kỹ thuật hợp lệ (data-* không phải nội dung user-visible) — nên grep text,
        // còn html chỉ chặn route thô (route name KHÔNG nằm trong data-* attr).
        expect(html, `combo=${JSON.stringify(c)} html route leak=${leak}`).not.toContain('>' + leak + '<')
      }
    }
  })

  // ── Vòng 22: card 'Model & Vị trí' — bịt em-dash-trơ Model/Vị trí ────────────
  //    BE build_asset_scan_info LUÔN emit device_model_name/location_name as str
  //    (coalesce '' khi rỗng). Trước đây 2 dòng render `{{ info.device_model_name
  //    || '—' }}` / `{{ info.location_name || '—' }}` → khi model/location rỗng
  //    (legacy/drift) ra em-dash '—' câm (vô nghĩa cho KTV). Yêu cầu: parity
  //    no-em-dash với 3 dòng ngày (vòng 17-19) → rỗng/null/undefined → nhãn VI
  //    'Chưa gán' (SSoT literal UNASSIGNED 1 chỗ), KHÔNG render '—' ở 2 dòng này.
  //    Thuần FE presentation — KHÔNG đụng BE contract.
  const modelLine = (w: ReturnType<typeof mount>) => w.get('[data-test="scan-model"]')
  const locationLine = (w: ReturnType<typeof mount>) => w.get('[data-test="scan-location"]')

  // TC-MODEL-EMPTY: device_model_name='' → dòng Model 'Chưa gán', KHÔNG '—'.
  it("TC-MODEL-EMPTY: device_model_name='' → dòng Model thiết bị 'Chưa gán', KHÔNG em-dash trơ", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, device_model_name: '' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = modelLine(w)
    expect(line.text()).toBe('Chưa gán')
    expect(line.text()).not.toBe('—')
    expect(line.text()).not.toContain('—')
  })

  // TC-MODEL-PRESENT (no-regress): device_model_name='Evita V500' → render nguyên văn.
  it("TC-MODEL-PRESENT (no-regress): device_model_name='Evita V500' → render nguyên văn", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, device_model_name: 'Evita V500' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(modelLine(w).text()).toBe('Evita V500')
  })

  // TC-LOCATION-EMPTY: location_name='' → dòng Vị trí 'Chưa gán', KHÔNG '—'.
  it("TC-LOCATION-EMPTY: location_name='' → dòng Vị trí 'Chưa gán', KHÔNG em-dash trơ", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, location_name: '' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = locationLine(w)
    expect(line.text()).toBe('Chưa gán')
    expect(line.text()).not.toBe('—')
    expect(line.text()).not.toContain('—')
  })

  // TC-LOCATION-PRESENT (no-regress): location_name='ICU - Tầng 3' → render nguyên văn.
  it("TC-LOCATION-PRESENT (no-regress): location_name='ICU - Tầng 3' → render nguyên văn", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, location_name: 'ICU - Tầng 3' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(locationLine(w).text()).toBe('ICU - Tầng 3')
  })

  // TC-NULLISH: device_model_name=null & location_name=undefined (payload partial/
  //   stale defensive) → cả 2 dòng 'Chưa gán', KHÔNG crash, KHÔNG '—', KHÔNG
  //   'null'/'undefined' leak.
  it("TC-NULLISH: device_model_name=null & location_name=undefined → cả 2 dòng 'Chưa gán', KHÔNG crash/'—'/'null'/'undefined'", async () => {
    const partial: Record<string, unknown> = { ...PAYLOAD, device_model_name: null }
    delete partial.location_name // undefined runtime
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(modelLine(w).text()).toBe('Chưa gán')
    expect(locationLine(w).text()).toBe('Chưa gán')
    expect(modelLine(w).text()).not.toContain('—')
    expect(locationLine(w).text()).not.toContain('—')
    // KHÔNG crash → không màn lỗi.
    expect(w.find('[role="alert"]').exists()).toBe(false)
    // KHÔNG rò chữ 'null'/'undefined' ra dòng model/location.
    expect(modelLine(w).text()).not.toContain('null')
    expect(modelLine(w).text()).not.toContain('undefined')
    expect(locationLine(w).text()).not.toContain('null')
    expect(locationLine(w).text()).not.toContain('undefined')
  })

  // TC-NO-EMDASH-PARITY: model+location rỗng → grep toàn text card 'Model & Vị trí'
  //   KHÔNG chứa ký tự '—'.
  it("TC-NO-EMDASH-PARITY: model+location rỗng → text 2 dòng card 'Model & Vị trí' KHÔNG chứa '—'", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, device_model_name: '', location_name: '' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    // Cụ thể 2 dòng model/location — KHÔNG em-dash ở MỌI nhánh.
    expect(modelLine(w).text()).not.toContain('—')
    expect(locationLine(w).text()).not.toContain('—')
    // Cả 2 đều ra nhãn VI fallback.
    expect(modelLine(w).text()).toBe('Chưa gán')
    expect(locationLine(w).text()).toBe('Chưa gán')
  })

  // ── Vòng 46: parity trim-then-truthy modelText/locationText (như assetCode V27 /
  //    serial V37). BE đã coalesce whitespace-only→'' qua _str_or_blank; FE phòng thủ
  //    SONG SONG: trim 2 đầu trước truthy-check → device_model_name='   ' (stale/drift
  //    từ worker cũ) hiển thị 'Chưa gán', KHÔNG render <dd> chứa whitespace câm. KHÔNG
  //    nuốt khoảng-trắng-GIỮA ('ICU - Tầng 3' giữ nguyên). RED trước fix vì thiếu .trim().
  it("TC-WS-MODEL-FE-1: device_model_name='   ' (whitespace-only) → dòng Model 'Chưa gán'", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, device_model_name: '   ' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = modelLine(w)
    expect(line.text()).toBe('Chưa gán')
    // KHÔNG render whitespace câm (sau trim() rỗng → fallback, không còn '   ').
    expect(line.text()).not.toContain('—')
  })

  it("TC-WS-LOC-FE-1: location_name='\\t' (tab-only) → dòng Vị trí 'Chưa gán'", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, location_name: '\t' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(locationLine(w).text()).toBe('Chưa gán')
  })

  it("TC-WS-LOC-FE-2: location_name='\\n' (newline-only) → dòng Vị trí 'Chưa gán'", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, location_name: '\n' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(locationLine(w).text()).toBe('Chưa gán')
  })

  // TC-WS-NOREG-MIDDLE: giá trị thật có khoảng-trắng-GIỮA → render NGUYÊN VĂN
  //   (trim chỉ 2 đầu, KHÔNG nuốt giữa). Chứng minh 'ICU - Tầng 3' không bị méo.
  it("TC-WS-NOREG-MIDDLE: location_name='ICU - Tầng 3' → render nguyên văn (KHÔNG nuốt khoảng-trắng-giữa)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, location_name: 'ICU - Tầng 3' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(locationLine(w).text()).toBe('ICU - Tầng 3')
  })

  // TC-NO-REGRESS-OTHER: status pill / dòng ngày PM-Cal / CTA vẫn render đúng
  //   (smoke 1 case full-payload) — refactor 2 dòng model/location KHÔNG phá render khác.
  it('TC-NO-REGRESS-OTHER: full-payload → status pill + ngày PM/Cal + CTA + model/location đều render đúng', async () => {
    getAssetScanInfoSpy.mockResolvedValue(PAYLOAD)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const txt = w.text()
    // status pill VI.
    expect(txt).toContain('Đang hoạt động')
    // dòng ngày PM + Cal vẫn đúng formatDate.
    expect(txt).toContain(formatDate('2026-08-30'))
    expect(txt).toContain(formatDate('2026-09-15'))
    // 4 CTA render.
    expect(w.findAll('[data-action-key]').length).toBe(4)
    // model/location render nguyên văn (no-regress).
    expect(modelLine(w).text()).toBe('Evita V500')
    expect(locationLine(w).text()).toBe('ICU - Tầng 3')
  })

  // ── Vòng 47: dòng 'Phân loại rủi ro' — cờ urgency rủi ro cao + a11y ───────────
  //    risk_classification ∈ {High, Critical} → dòng scan-risk mang affordance CẢNH
  //    BÁO trực quan (màu amber + chip/aria 'Rủi ro cao' VI), KHÔNG còn neutral slate.
  //    Urgency derive THUẦN bằng enum-equality trên giá trị server đã .trim() (KHÔNG
  //    so client-clock, KHÔNG nghiệp vụ FE — parity overdue SSoT vòng 21). Low/Medium
  //    HOẶC rỗng/whitespace HOẶC ngoài-4-enum → KHÔNG urgency (no false-alarm). riskText
  //    (nhãn nội dung) GIỮ NGUYÊN (no-regress vòng 38/40). A11y WCAG 1.4.1: phần tử
  //    cảnh báo role=status + aria-label VI → screen-reader nghe được, KHÔNG chỉ màu.
  //    No-leak: KHÔNG rò enum EN 'High'/'Critical' thô ra dòng risk / aria.
  const riskLine = (w: ReturnType<typeof mount>) => w.get('[data-test="scan-risk"]')
  const riskUrgent = (w: ReturnType<typeof mount>) => w.find('[data-test="scan-risk-urgent"]')
  const RISK_URGENT_HINT = 'Rủi ro cao'
  const RISK_URGENT_ARIA = 'Cảnh báo: thiết bị rủi ro cao'

  // TC-RISK-CRITICAL: 'Critical' → riskText 'Nghiêm trọng' (no-regress) + scan-risk-urgent
  //   EXISTS với role hợp lệ + aria-label VI cảnh báo + class màu cảnh báo (KHÔNG slate).
  it("TC-RISK-CRITICAL: risk_classification='Critical' → 'Nghiêm trọng' + scan-risk-urgent (role/aria VI + màu amber, KHÔNG slate)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, risk_classification: 'Critical' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    // no-regress: nhãn nội dung VI vẫn 'Nghiêm trọng'.
    expect(riskLine(w).text()).toContain('Nghiêm trọng')
    // cờ urgency EXISTS.
    const urgent = riskUrgent(w)
    expect(urgent.exists()).toBe(true)
    // role hợp lệ (status hoặc alert) — a11y không-chỉ-bằng-màu.
    expect(['status', 'alert']).toContain(urgent.attributes('role'))
    // aria-label VI mô tả cảnh báo.
    expect(urgent.attributes('aria-label')).toBe(RISK_URGENT_ARIA)
    // chip có nội dung text VI (không phải span rỗng chỉ-màu).
    expect(urgent.text()).toContain(RISK_URGENT_HINT)
    // dòng risk mang class màu cảnh báo amber, KHÔNG còn slate neutral.
    const lineClasses = riskLine(w).classes().join(' ')
    expect(lineClasses).toContain('text-amber-700')
    expect(lineClasses).not.toContain('text-slate-500')
  })

  // TC-RISK-HIGH: 'High' → riskText 'Cao' + scan-risk-urgent EXISTS (parity Critical).
  it("TC-RISK-HIGH: risk_classification='High' → 'Cao' + scan-risk-urgent EXISTS (parity Critical)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, risk_classification: 'High' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(riskLine(w).text()).toContain('Cao')
    const urgent = riskUrgent(w)
    expect(urgent.exists()).toBe(true)
    expect(['status', 'alert']).toContain(urgent.attributes('role'))
    expect(urgent.attributes('aria-label')).toBe(RISK_URGENT_ARIA)
    expect(urgent.text()).toContain(RISK_URGENT_HINT)
    expect(riskLine(w).classes().join(' ')).toContain('text-amber-700')
  })

  // TC-RISK-MEDIUM: 'Medium' → riskText 'Trung bình' + scan-risk-urgent KHÔNG tồn tại
  //   (no false-alarm) + dòng giữ styling slate.
  it("TC-RISK-MEDIUM: risk_classification='Medium' → 'Trung bình' + KHÔNG urgent (no false-alarm) + slate", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, risk_classification: 'Medium' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(riskLine(w).text()).toContain('Trung bình')
    expect(riskUrgent(w).exists()).toBe(false)
    const lineClasses = riskLine(w).classes().join(' ')
    expect(lineClasses).toContain('text-slate-500')
    expect(lineClasses).not.toContain('text-amber-700')
  })

  // TC-RISK-LOW: 'Low' → riskText 'Thấp' + KHÔNG urgent.
  it("TC-RISK-LOW: risk_classification='Low' → 'Thấp' + KHÔNG urgent", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, risk_classification: 'Low' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(riskLine(w).text()).toContain('Thấp')
    expect(riskUrgent(w).exists()).toBe(false)
    expect(riskLine(w).classes().join(' ')).toContain('text-slate-500')
  })

  // TC-RISK-EMPTY: '' (rỗng/whitespace) → riskText 'Chưa phân loại' + KHÔNG urgent
  //   (no false-alarm).
  it("TC-RISK-EMPTY: risk_classification='   ' (rỗng/whitespace) → 'Chưa phân loại' + KHÔNG urgent", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, risk_classification: '   ' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(riskLine(w).text()).toContain('Chưa phân loại')
    expect(riskUrgent(w).exists()).toBe(false)
    expect(riskLine(w).classes().join(' ')).toContain('text-slate-500')
  })

  // TC-RISK-DRIFT: 'Weird' (ngoài-4-enum) → riskText 'Khác' + KHÔNG urgent + KHÔNG
  //   leak chuỗi 'Weird' thô ra DOM.
  it("TC-RISK-DRIFT: risk_classification='Weird' (ngoài enum) → 'Khác' + KHÔNG urgent + KHÔNG leak 'Weird' thô", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, risk_classification: 'Weird' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(riskLine(w).text()).toContain('Khác')
    expect(riskUrgent(w).exists()).toBe(false)
    // no-leak: chuỗi drift KHÔNG lọt ra DOM (dòng risk + toàn màn).
    expect(riskLine(w).text()).not.toContain('Weird')
    expect(w.text()).not.toContain('Weird')
  })

  // TC-RISK-NO-EN-LEAK: Critical/High → toàn bộ textContent dòng risk + aria KHÔNG
  //   chứa 'High'/'Critical' thô (chỉ VI). Cờ suy từ enum nhưng hiển thị đều VI.
  it("TC-RISK-NO-EN-LEAK: Critical/High → dòng risk + aria KHÔNG chứa 'High'/'Critical' thô (chỉ VI)", async () => {
    for (const raw of ['Critical', 'High']) {
      getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, risk_classification: raw })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      const urgent = riskUrgent(w)
      expect(urgent.exists(), `raw=${raw}`).toBe(true)
      // dòng risk KHÔNG leak enum EN thô.
      expect(riskLine(w).text(), `raw=${raw} line`).not.toContain(raw)
      // aria-label phần urgency KHÔNG leak enum EN thô (chỉ VI).
      const aria = urgent.attributes('aria-label') ?? ''
      expect(aria, `raw=${raw} aria`).not.toContain(raw)
      expect(aria, `raw=${raw} aria VI`).toBe(RISK_URGENT_ARIA)
    }
  })

  // TC-RISK-A11Y: scan-risk-urgent có role + aria-label (cảnh báo KHÔNG truyền tải
  //   CHỈ bằng màu — WCAG 1.4.1; parity status-pill vòng 39 / overdue badge vòng 21).
  it("TC-RISK-A11Y: scan-risk-urgent có role + aria-label (WCAG 1.4.1 — không-chỉ-bằng-màu)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, risk_classification: 'Critical' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const urgent = riskUrgent(w)
    expect(urgent.exists()).toBe(true)
    // role tồn tại (status/alert) + aria-label non-empty VI.
    expect(['status', 'alert']).toContain(urgent.attributes('role'))
    const aria = urgent.attributes('aria-label') ?? ''
    expect(aria.length).toBeGreaterThan(0)
    expect(aria).toBe(RISK_URGENT_ARIA)
    // có nội dung text (screen-reader + sighted đều nhận) — không chỉ là màu nền.
    expect(urgent.text().trim().length).toBeGreaterThan(0)
  })

  // TC-RISK-NOREGRESS: data-test='scan-risk' GIỮ NGUYÊN (anchor cũ) + nhãn 'Phân loại
  //   rủi ro: {{ riskText }}' nguyên cấu trúc cho cả case urgent + non-urgent.
  it("TC-RISK-NOREGRESS: data-test='scan-risk' tồn tại + nhãn 'Phân loại rủi ro:' (urgent + non-urgent)", async () => {
    for (const raw of ['Critical', 'Low']) {
      getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, risk_classification: raw })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      expect(riskLine(w).exists(), `raw=${raw}`).toBe(true)
      expect(riskLine(w).text(), `raw=${raw}`).toContain('Phân loại rủi ro:')
    }
  })

})
