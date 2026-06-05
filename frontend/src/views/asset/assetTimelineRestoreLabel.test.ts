// TC-ALE-RST-08-FE — Regression dòng thời gian khôi phục (IMM-00 Asset Lifecycle).
//
// BUG-class (memory `wave2_ui_bugs`): AssetDetailView tab "Lịch sử" render
// `event.event_type` + from/to status THÔ → lộ mã EN ('restored'/'activated'/
// 'Out of Service'/'Active'). Fix = SSoT formatter translateLifecycleEvent +
// translateStatus.
//
// Invariant kiểm: 1 transition Out of Service → Active sinh ĐÚNG 1 event
// 'restored' (BE bỏ double-emit 'activated'+'restored'); FE phải render 1 chip
// nhãn VI 'Khôi phục hoạt động', KHÔNG kèm 'activated', KHÔNG leak mã EN thô.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { translateLifecycleEvent } from '@/utils/formatters'

// ─── Router mock ────────────────────────────────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: { id: 'ASSET-0001' }, query: {} }),
}))

// ─── Store mock — currentAsset truthy để render <template> chính ─────────────
const currentAsset = {
  name: 'ASSET-0001',
  asset_name: 'Máy thở A',
  lifecycle_status: 'Active',
}
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset,
    loading: false,
    error: null,
    fetchOne: vi.fn().mockResolvedValue(undefined),
    transition: vi.fn().mockResolvedValue({ success: true }),
  }),
}))

// ─── API mock — timeline trả 1 event 'restored' (đường OoS→Active sau fix) ────
// Đây là ground-truth BE sau khi diệt double-emit: KHÔNG có 'activated' đi kèm.
const RESTORE_TIMELINE = [
  {
    name: 'ALE-0002',
    event_type: 'restored',
    actor: 'tech@hosp.vn',
    from_status: 'Out of Service',
    to_status: 'Active',
    timestamp: '2026-06-04 09:00:00',
    event_timestamp: '2026-06-04 09:00:00',
    notes: 'Khôi phục sau tạm ngừng: dời 2 kỳ khấu hao Pending thêm 5 ngày.',
  },
  {
    name: 'ALE-0001',
    event_type: 'out_of_service',
    actor: 'tech@hosp.vn',
    from_status: 'Active',
    to_status: 'Out of Service',
    timestamp: '2026-05-30 08:00:00',
    event_timestamp: '2026-05-30 08:00:00',
    notes: '',
  },
]
const getAssetTimelineSpy = vi.fn().mockResolvedValue({ items: RESTORE_TIMELINE })
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: (...a: unknown[]) => getAssetTimelineSpy(...a),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue({ valid: true, count: 2 }),
  deleteAsset: vi.fn().mockResolvedValue(undefined),
}))
vi.mock('@/api/imm04', () => ({
  getCommissioningOrigin: vi.fn().mockResolvedValue(null),
}))
// IMM-14 entrypoint thêm useCapabilities + useAuthStore vào setup → mock để mount
// không cần active Pinia (test này chỉ kiểm timeline label, không kiểm nút giải nhiệm).
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => false }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ user: { email: 'tech@hosp.vn' } }),
}))

import AssetDetailView from './AssetDetailView.vue'

const stubs = {
  PageHeader: true,
  AssetDowntimeWidget: true,
  AssetDepreciationSchedule: true,
  RouterLink: true,
  'router-link': true,
}

async function mountTimeline() {
  const wrapper = mount(AssetDetailView, {
    props: { id: 'ASSET-0001' },
    global: { stubs },
  })
  await flushPromises()
  // Chuyển sang tab "Lịch sử" (timeline) → trigger loadTimeline.
  const tabBtns = wrapper.findAll('nav button, button').filter(b => b.text() === 'Lịch sử')
  // Tab button "Lịch sử" nằm trong dải tab info/depreciation/timeline/kpi/audit.
  const timelineTab = tabBtns[tabBtns.length - 1]
  await timelineTab.trigger('click')
  await flushPromises()
  return wrapper
}

describe('TC-ALE-RST-08-FE — timeline khôi phục render 1 chip VI, không double/leak', () => {
  beforeEach(() => getAssetTimelineSpy.mockClear())

  it("đúng 1 chip 'restored' nhãn VI 'Khôi phục hoạt động', 0 chip 'activated'", async () => {
    const wrapper = await mountTimeline()
    const chips = wrapper.findAll('[data-testid="ale-event-type"]')
    const texts = chips.map(c => c.text())
    const restoredChips = texts.filter(t => t === 'Khôi phục hoạt động')
    expect(restoredChips.length).toBe(1)
    // KHÔNG còn cặp 'activated'+'restored' trùng (nhãn VI của activated = 'Kích hoạt').
    expect(texts.filter(t => t === 'Kích hoạt').length).toBe(0)
  })

  it('KHÔNG leak mã event_type EN thô (restored/activated/out_of_service)', async () => {
    const wrapper = await mountTimeline()
    const html = wrapper.html()
    // Mã enum EN không được lọt ra UI (đã map qua SSoT).
    expect(html).not.toMatch(/\brestored\b/)
    expect(html).not.toMatch(/\bactivated\b/)
    expect(html).not.toMatch(/\bout_of_service\b/)
  })

  it('KHÔNG leak status EN thô (Out of Service / Active) ở dòng chuyển trạng thái', async () => {
    const wrapper = await mountTimeline()
    const rows = wrapper.findAll('[data-testid="ale-status-transition"]')
    expect(rows.length).toBeGreaterThan(0)
    const joined = rows.map(r => r.text()).join(' | ')
    expect(joined).toContain('Ngừng hoạt động')
    expect(joined).toContain('Đang hoạt động')
    expect(joined).not.toContain('Out of Service')
    // 'Active' không được xuất hiện như token độc lập (đã dịch 'Đang hoạt động').
    expect(joined).not.toMatch(/\bActive\b/)
  })
})

// ─── Unit SSoT — translateLifecycleEvent phủ enum + phân biệt restored/activated ─
describe('translateLifecycleEvent — SSoT nhãn VI cho event_type vòng đời', () => {
  it("'restored' → 'Khôi phục hoạt động' (KHÁC 'activated')", () => {
    expect(translateLifecycleEvent('restored')).toBe('Khôi phục hoạt động')
    expect(translateLifecycleEvent('activated')).toBe('Kích hoạt')
    expect(translateLifecycleEvent('restored')).not.toBe(translateLifecycleEvent('activated'))
  })

  it('null/empty → "—"; key lạ → trả nguyên (không crash, không bịa)', () => {
    expect(translateLifecycleEvent(null)).toBe('—')
    expect(translateLifecycleEvent('')).toBe('—')
    expect(translateLifecycleEvent('khong_co_trong_enum')).toBe('khong_co_trong_enum')
  })

  it('phủ ĐỦ 18 option enum Asset Lifecycle Event — không leak mã EN', () => {
    const ENUM = [
      'commissioned', 'activated', 'pm_started', 'pm_completed', 'repair_opened',
      'repair_completed', 'calibration_started', 'calibration_passed',
      'calibration_failed', 'incident_reported', 'out_of_service', 'restored',
      'decommissioned', 'transferred', 'registered', 'depreciated',
      'depreciation_rules_inherited', 'depreciation_stopped',
    ]
    for (const code of ENUM) {
      const vi = translateLifecycleEvent(code)
      expect(vi, `thiếu nhãn VI cho event_type "${code}"`).not.toBe(code)
      expect(/[a-z]_[a-z]/.test(vi), `nhãn còn dạng snake_case EN: "${vi}"`).toBe(false)
    }
  })
})
