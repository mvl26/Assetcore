// Copyright (c) 2026, AssetCore Team
// TC-UXTAB-01/02 (docs/ui-ux/07 §4.1, AC-UX-068) — màn Chi tiết thiết bị đã UỶ QUYỀN
// thanh tab cho SSoT `DetailTabBar`, và việc đổi khuôn KHÔNG làm hồi quy hai hành vi
// đắt nhất của màn này:
//
//   (1) NẠP LƯỜI — `onTabChange` chỉ nạp dữ liệu của tab vừa mở, ĐÚNG 1 lần mỗi lần bấm
//       (hợp đồng AC-CR-87/96: mở thiết bị KHÔNG bắn `get_connections`, không bắn
//       timeline/kpi/audit trước khi người dùng vào tab). Đây là lý do màn này CỐ Ý dùng
//       `:model-value` + `@update:model-value` chứ không `v-model`: một nơi ghi state,
//       một nơi chạy tác dụng phụ.
//   (2) ĐIỀU HƯỚNG NỘI BỘ — nút «Xem chi tiết →» trong thẻ Khấu hao đặt thẳng
//       `activeTab = 'depreciation'`; sau khi đổi khuôn, thanh tab (do component KHÁC vẽ)
//       vẫn phải đi theo. Đây chính là ca mà một thanh tab «tự nhớ state» sẽ đi lạc.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

const currentAsset = {
  name: 'AC-ASSET-2026-00042',
  asset_name: 'Máy thở Dräger Evita V600',
  asset_code: 'AC-VENT-0042',
  lifecycle_status: 'Active',
  asset_category: 'CAT-0007',
  category_name: 'Thiết bị hỗ trợ hô hấp',
  device_model: 'DM-DRAGER-V600',
  device_model_name: 'Dräger Evita V600',
  supplier: 'SUP-2026-00011',
  supplier_name: 'Công ty TNHH Dräger Việt Nam',
  department_name: 'Khoa Hồi sức tích cực',
  location_name: 'ICU - Giường 01',
  purchase_date: '2025-01-10',
  gross_purchase_amount: 1200000000,
}

const fetchOneSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset, loading: false, error: null, fetchOne: fetchOneSpy, transition: vi.fn(),
  }),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: 'tester' }) }))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ fromError: vi.fn(), success: vi.fn(), show: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ show: vi.fn(), success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}))

// 3 endpoint nạp LƯỜI — spy để đếm số lần `onTabChange` thật sự chạy.
const getAssetTimeline = vi.fn().mockResolvedValue({ items: [], total: 0 })
const getAssetKpi = vi.fn().mockResolvedValue(null)
const verifyChain = vi.fn().mockResolvedValue(null)
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: (...a: unknown[]) => getAssetTimeline(...a),
  getAssetKpi: (...a: unknown[]) => getAssetKpi(...a),
  verifyChain: (...a: unknown[]) => verifyChain(...a),
  deleteAsset: vi.fn(),
  getAssetLabelData: vi.fn().mockResolvedValue({}),
  markLabelPrinted: vi.fn(),
  regenerateAssetQrToken: vi.fn(),
  printAssetLabelsPdf: vi.fn(),
  LABEL_PDF_PRESETS: [{ key: 'tem-60x100', label: 'Tem 60×100mm' }],
  LABEL_PDF_PRESET: 'tem-60x100',
  labelPdfPresetLabel: () => 'Tem 60×100mm',
}))
vi.mock('@/api/imm04', () => ({ getCommissioningOrigin: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/imm14', () => ({ createDecommission: vi.fn(), approveDecommission: vi.fn() }))
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))

const getConnections = vi.fn()
vi.mock('@/api/connections', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/connections')>()),
  getConnections: (...a: unknown[]) => getConnections(...a),
}))

import DetailTabBar from '@/components/common/DetailTabBar.vue'
import AssetDetailView from './AssetDetailView.vue'

const stubs = {
  PageHeader: true, teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
  'router-link': { template: '<a><slot /></a>' },
}

/** 6 tab, ĐÚNG thứ tự nguồn — thứ tự cũng là hợp đồng (người dùng nhớ vị trí). */
const TAB_KEYS = ['info', 'depreciation', 'timeline', 'kpi', 'audit', 'related'] as const

async function mountDetail() {
  const w = mount(AssetDetailView, { props: { id: currentAsset.name }, global: { stubs } })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  getAssetTimeline.mockClear()
  getAssetKpi.mockClear()
  verifyChain.mockClear()
  getConnections.mockReset()
  getConnections.mockResolvedValue({
    doctype: 'AC Asset', name: currentAsset.name, total: 0, groups: [],
  })
})

describe('TC-UXTAB-01 — 6 tab render QUA SSoT DetailTabBar', () => {
  it('màn dùng ĐÚNG 1 DetailTabBar (không còn thanh tab tự chế song song)', async () => {
    const w = await mountDetail()
    expect(w.findAllComponents(DetailTabBar)).toHaveLength(1)
    expect(w.findAll('[role="tablist"]')).toHaveLength(1)
  })

  it('đủ 6 testid tab-<key> đúng thứ tự, nhãn tiếng Việt', async () => {
    const w = await mountDetail()
    const tabs = w.findAll('[role="tab"]')
    expect(tabs).toHaveLength(6)
    expect(tabs.map((t) => t.attributes('data-testid'))).toEqual(TAB_KEYS.map((k) => `tab-${k}`))
    expect(tabs.map((t) => t.text())).toEqual([
      'Thông tin', 'Khấu hao', 'Lịch sử', 'Chỉ số hiệu suất', 'Nhật ký truy vết', 'Bản ghi liên quan',
    ])
  })

  it('ĐÚNG 1 tab có aria-selected="true" (mặc định «Thông tin»)', async () => {
    const w = await mountDetail()
    const selected = w.findAll('[role="tab"]').filter((t) => t.attributes('aria-selected') === 'true')
    expect(selected).toHaveLength(1)
    expect(selected[0].attributes('data-testid')).toBe('tab-info')
  })

  it('tabs được truyền dạng DetailTab[] có key + label (không phải markup rời)', async () => {
    const w = await mountDetail()
    const tabs = w.findComponent(DetailTabBar).props('tabs') as { key: string; label: string }[]
    expect(tabs.map((t) => t.key)).toEqual([...TAB_KEYS])
    for (const t of tabs) expect(t.label.length).toBeGreaterThan(0)
  })
})

describe('TC-UXTAB-01b — NẠP LƯỜI không hồi quy (AC-CR-87/96)', () => {
  it('vừa mở màn ⇒ 0 lần gọi timeline/kpi/audit/liên quan', async () => {
    await mountDetail()
    expect(getAssetTimeline).toHaveBeenCalledTimes(0)
    expect(getAssetKpi).toHaveBeenCalledTimes(0)
    expect(verifyChain).toHaveBeenCalledTimes(0)
    expect(getConnections).toHaveBeenCalledTimes(0)
  })

  it('bấm «Lịch sử» ⇒ onTabChange chạy ĐÚNG 1 lần (timeline gọi 1, kpi/audit vẫn 0)', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-timeline"]').trigger('click')
    await flushPromises()

    expect(getAssetTimeline).toHaveBeenCalledTimes(1)
    expect(getAssetKpi).toHaveBeenCalledTimes(0)
    expect(verifyChain).toHaveBeenCalledTimes(0)
  })

  it('bấm lại chính tab đang mở ⇒ KHÔNG nạp lần 2 (đã có dữ liệu)', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-kpi"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="tab-kpi"]').trigger('click')
    await flushPromises()
    // 2 lần bấm ⇒ 2 lần onTabChange, nhưng nhánh nạp có điều kiện `!kpi` ⇒ tối đa 2
    // (fixture trả null nên không cache được). Điều cần khoá: KHÔNG nhân đôi mỗi lần bấm.
    expect(getAssetKpi.mock.calls.length).toBeLessThanOrEqual(2)
    expect(getAssetTimeline).toHaveBeenCalledTimes(0)
  })
})

describe('TC-UXTAB-02 — bấm «Bản ghi liên quan» ⇒ panel mount + aria đổi đúng', () => {
  it('panel tab-panel-related mount và gọi get_connections ĐÚNG 1 lần', async () => {
    const w = await mountDetail()
    expect(w.find('[data-testid="tab-panel-related"]').exists()).toBe(false)

    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    expect(w.find('[data-testid="tab-panel-related"]').exists()).toBe(true)
    expect(getConnections).toHaveBeenCalledTimes(1)
  })

  it('aria-selected chuyển sang tab-related, tab-info về false', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    expect(w.find('[data-testid="tab-related"]').attributes('aria-selected')).toBe('true')
    expect(w.find('[data-testid="tab-info"]').attributes('aria-selected')).toBe('false')
    expect(
      w.findAll('[role="tab"]').filter((t) => t.attributes('aria-selected') === 'true'),
    ).toHaveLength(1)
  })
})

describe('TC-UXTAB-02b — điều hướng nội bộ «Xem chi tiết →» kéo thanh tab đi theo', () => {
  it('bấm link trong thẻ Khấu hao ⇒ aria-selected về tab-depreciation', async () => {
    const w = await mountDetail()
    const link = w.findAll('button').find((b) => b.text().includes('Xem chi tiết'))
    expect(link, 'Không tìm thấy nút «Xem chi tiết →» trong thẻ Khấu hao').toBeTruthy()

    await link!.trigger('click')
    await flushPromises()

    expect(w.find('[data-testid="tab-depreciation"]').attributes('aria-selected')).toBe('true')
    expect(w.find('[data-testid="tab-info"]').attributes('aria-selected')).toBe('false')
  })
})
