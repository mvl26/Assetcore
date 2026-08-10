// Copyright (c) 2026, AssetCore Team
// TDD — TC-CONNTAB-09 (AC-CR-87 vòng 3): «Bản ghi liên quan» rời panel «Thông tin» sang
// TAB RIÊNG ở màn chi tiết thiết bị (IMM-00).
//
// Trước vòng này khối liên quan nằm NGAY trong tab «Thông tin» (tab mặc định) ⇒ mở bất kỳ
// thiết bị nào cũng bắn `get_connections`. Sau vòng này nó là tab thứ 6, mount lười.
//
// AC-CR-102 bồi thêm TC-FE-OPH-01/02 ở CUỐI FILE: tab này giờ còn chứa khối «Dữ liệu vận
// hành của thiết bị». Kiểm chứng qua CHÍNH màn chi tiết (không phải mount component rời)
// vì hai điều chỉ sai được ở mức tích hợp: (a) khối có thật trong panel liên quan, và
// (b) vào tab KHÔNG phát sinh thêm request nào (ba nhánh THU mặc định).
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
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ fromError: vi.fn(), success: vi.fn(), show: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ show: vi.fn(), success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}))
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: vi.fn().mockResolvedValue({ items: [] }),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue(null),
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

// AC-CR-102 — ba endpoint của khối «Dữ liệu vận hành»: giữ spy để khẳng định vào tab
// KHÔNG gọi cái nào (THU mặc định). Store THẬT vẫn chạy ⇒ cần Pinia (xem beforeEach).
const getAssetPMHistory = vi.fn().mockResolvedValue({ asset_ref: '', history: [], total: 0, truncated: 0 })
const getAssetRepairHistory = vi.fn().mockResolvedValue({ asset_ref: '', history: [], total: 0, truncated: 0 })
const getAssetIncidentHistory = vi.fn().mockResolvedValue({ asset: '', items: [], total: 0, truncated: 0 })
vi.mock('@/api/imm08', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm08')>()),
  getAssetPMHistory: (...a: unknown[]) => getAssetPMHistory(...a),
}))
vi.mock('@/api/imm09', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm09')>()),
  getAssetRepairHistory: (...a: unknown[]) => getAssetRepairHistory(...a),
}))
vi.mock('@/api/imm12', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm12')>()),
  getAssetIncidentHistory: (...a: unknown[]) => getAssetIncidentHistory(...a),
}))

import RelatedRecords from '@/components/common/RelatedRecords.vue'
import AssetDetailView from './AssetDetailView.vue'
import { expectVietnameseTabs } from '@/test/tabLabelParity'

// RelatedRecords CỐ Ý không stub — cần khẳng định nó mount/không mount thật.
const stubs = {
  PageHeader: true, teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
  'router-link': { template: '<a><slot /></a>' },
}

async function mountDetail() {
  const w = mount(AssetDetailView, {
    props: { id: 'AC-ASSET-2026-00042' }, global: { stubs },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  // Khối «Dữ liệu vận hành» dùng store Pinia thật (imm08/imm09/imm12) ⇒ panel liên
  // quan không mount được nếu thiếu Pinia hoạt động.
  setActivePinia(createPinia())
  getAssetPMHistory.mockClear()
  getAssetRepairHistory.mockClear()
  getAssetIncidentHistory.mockClear()
  getConnections.mockReset()
  getConnections.mockResolvedValue({
    doctype: 'AC Asset', name: currentAsset.name, total: 0, groups: [],
  })
  fetchOneSpy.mockClear()
})

describe('TC-CONNTAB-09 — IMM-00: tab «Bản ghi liên quan» ở màn chi tiết thiết bị', () => {
  it('tab «Bản ghi liên quan» tồn tại trong thanh tab', async () => {
    const w = await mountDetail()
    expect(w.find('[data-testid="tab-related"]').exists()).toBe(true)
    expect(w.find('[data-testid="tab-related"]').text()).toBe('Bản ghi liên quan')
  })

  it('tab mặc định "info" ⇒ 0 lần gọi get_connections ∧ 0 khối liên quan', async () => {
    const w = await mountDetail()
    expect(getConnections).toHaveBeenCalledTimes(0)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(0)
  })

  it('bấm tab ⇒ ĐÚNG 1 lần gọi, khối xuất hiện 1 lần, prop = (AC Asset, mã thiết bị)', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    expect(getConnections).toHaveBeenCalledTimes(1)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(1)

    const rr = w.findComponent(RelatedRecords)
    expect(rr.props('doctype')).toBe('AC Asset')
    expect(rr.props('name')).toBe(currentAsset.name)
  })

  it('tab liên quan active ⇒ panel «Thông tin» biến mất (v-if), thanh tab vẫn còn', async () => {
    const w = await mountDetail()
    expect(w.text()).toContain('Thông tin chung')

    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    expect(w.text()).not.toContain('Thông tin chung')
    expect(w.find('[data-testid="tab-panel-related"]').exists()).toBe(true)
    expect(w.find('[data-testid="tab-info"]').attributes('aria-selected')).toBe('false')
    expect(w.find('[data-testid="tab-related"]').attributes('aria-selected')).toBe('true')
  })

  it('quay lại tab «Thông tin» ⇒ panel liên quan bị huỷ (v-if)', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="tab-info"]').trigger('click')
    await flushPromises()

    expect(w.find('[data-testid="tab-panel-related"]').exists()).toBe(false)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(0)
  })

  it('nhãn 6 tab 100% tiếng Việt (LL-FE-53)', async () => {
    expectVietnameseTabs(await mountDetail())
  })
})

describe('TC-FE-OPH-01/02 (AC-CR-102) — khối «Dữ liệu vận hành» trong CHÍNH tab liên quan', () => {
  it('vào tab ⇒ ĐÚNG 1 khối [asset-op-history] với ĐÚNG 3 nhánh, nhãn tiếng Việt', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    expect(w.findAll('[data-testid="asset-op-history"]')).toHaveLength(1)
    const heads = w.findAll('[data-testid="op-history-toggle"]')
    expect(heads).toHaveLength(3)
    expect(heads[0].text()).toContain('Kết quả bảo trì')
    expect(heads[1].text()).toContain('Lần sửa chữa đã hoàn thành')
    expect(heads[2].text()).toContain('Sự cố đã ghi nhận')
  })

  it('khối nằm TRONG panel liên quan (tab «Thông tin» KHÔNG có nó)', async () => {
    const w = await mountDetail()
    expect(w.find('[data-testid="asset-op-history"]').exists()).toBe(false)

    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="tab-panel-related"]').find('[data-testid="asset-op-history"]').exists()).toBe(true)
  })

  it('vào tab ⇒ 0 dòng ∧ 0 lần gọi cả BA endpoint lịch sử (THU mặc định)', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    expect(w.findAll('[data-testid="op-history-row"]')).toHaveLength(0)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(0)
    expect(getAssetRepairHistory).toHaveBeenCalledTimes(0)
    expect(getAssetIncidentHistory).toHaveBeenCalledTimes(0)
  })

  it('KHÔNG thêm tab mới: thanh tab vẫn ĐÚNG 6 tab và vẫn 100% tiếng Việt', async () => {
    const w = await mountDetail()
    expect(w.findAll('[role="tab"]')).toHaveLength(6)
    expectVietnameseTabs(w)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// AC-CR-115 (D-OPH-18) — BẢN GHI đứng TRƯỚC Ô CHỨC NĂNG + đúng 2 tiêu đề khối.
// Chỉ sai được ở mức tích hợp (thứ tự do AssetDetailView quyết, tiêu đề khối 2 cũng
// nằm ở đây vì RelatedRecords.vue dùng chung 5 màn chi tiết) ⇒ test tại CHÍNH màn.
// ═══════════════════════════════════════════════════════════════════════════════
describe('TC-FE-OPH-19/20 (AC-CR-115) — thứ tự DOM 2 khối + 2 tiêu đề khối', () => {
  async function openRelated() {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    return w
  }

  it('TC-FE-OPH-19 — [asset-op-history] đứng TRƯỚC [related-records] theo thứ tự DOM', async () => {
    const w = await openRelated()
    const panel = w.find('[data-testid="tab-panel-related"]')
    // So bằng querySelectorAll (thứ tự tài liệu THẬT), KHÔNG bằng indexOf trên html().
    const blocks = Array.from(
      panel.element.querySelectorAll(
        '[data-testid="asset-op-history"],[data-testid="related-records"]',
      ),
    ).map((el) => el.getAttribute('data-testid'))

    expect(blocks).toEqual(['asset-op-history', 'related-records'])
  })

  it('TC-FE-OPH-20 — ĐÚNG 2 [related-block-heading], đúng chuỗi VI theo thứ tự', async () => {
    const w = await openRelated()
    const panel = w.find('[data-testid="tab-panel-related"]')
    const headings = Array.from(
      panel.element.querySelectorAll('[data-testid="related-block-heading"]'),
    ).map((el) => (el.textContent ?? '').replace(/\s+/g, ' ').trim())

    expect(headings).toEqual([
      'Dữ liệu vận hành của thiết bị',
      'Liên kết nhanh theo chức năng',
    ])
  })

  it('TC-FE-OPH-20 — 2 tiêu đề 100% tiếng Việt: 0 acronym EN chưa dịch (LL-FE-53)', async () => {
    const w = await openRelated()
    const headings = w.findAll('[data-testid="related-block-heading"]').map((h) => h.text())
    expect(headings).toHaveLength(2)
    for (const h of headings) {
      expect(/\b(PM|CM|WO|SLA|KPI|CAPA|RCA)\b/.test(h), `acronym EN chưa dịch: ${h}`).toBe(false)
    }
  })

  it('TC-CONNTAB-11 — vào tab ⇒ 6 tab VI ∧ 0 dòng ∧ 0 dải cắt ∧ 3 API 0 lần gọi', async () => {
    const w = await openRelated()

    expect(w.findAll('[role="tab"]')).toHaveLength(6)
    expectVietnameseTabs(w)
    expect(w.findAll('[data-testid="op-history-row"]')).toHaveLength(0)
    expect(w.findAll('[data-testid="op-history-truncation"]')).toHaveLength(0)
    expect(getAssetPMHistory).toHaveBeenCalledTimes(0)
    expect(getAssetRepairHistory).toHaveBeenCalledTimes(0)
    expect(getAssetIncidentHistory).toHaveBeenCalledTimes(0)
  })
})
