// TC-ALE-CR60-FE — Tab "Lịch sử vòng đời": deep-link hồ-sơ-gốc + tên người thật.
//
// CR-60 (trục lifecycle NĐ98): mỗi dòng sự kiện, khi BE enrich root_doctype +
// root_record, phải cho phép chạm → mở ĐÚNG hồ sơ gốc (PM Work Order / Asset Repair
// / IMM Asset Calibration…); và hiển thị actor_name (User.full_name) THAY email thô.
// Event legacy (thiếu root) → KHÔNG link, KHÔNG crash. Event hệ thống (actor rỗng)
// → KHÔNG dòng "bởi …".
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: { id: 'ASSET-0001' }, query: {} }),
}))

const currentAsset = { name: 'ASSET-0001', asset_name: 'Máy thở A', lifecycle_status: 'Active' }
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset, loading: false, error: null,
    fetchOne: vi.fn().mockResolvedValue(undefined),
    transition: vi.fn().mockResolvedValue({ success: true }),
  }),
}))

// Timeline ground-truth (BE sau enrich CR-60):
//  - ev1: có nguồn Asset Repair + actor có full_name → link + tên thật.
//  - ev2: legacy (root rỗng '') + actor email không có User (actor_name == raw actor) → KHÔNG link, hiện email.
//  - ev3: event hệ thống (actor '' + actor_name '') → KHÔNG dòng "bởi …".
const CR60_TIMELINE = [
  {
    name: 'ALE-0003', event_type: 'repair_completed',
    actor: 'tech@hosp.vn', actor_name: 'Nguyễn Văn Kỹ',
    from_status: 'Under Repair', to_status: 'Active',
    timestamp: '2026-06-04 09:00:00', event_timestamp: '',
    root_doctype: 'Asset Repair', root_record: 'WO-RP-2026-00123', notes: '',
  },
  {
    name: 'ALE-0002', event_type: 'transferred',
    actor: 'legacy@hosp.vn', actor_name: 'legacy@hosp.vn',
    from_status: '', to_status: '',
    timestamp: '2026-05-30 08:00:00', event_timestamp: '',
    root_doctype: '', root_record: '', notes: '',
  },
  {
    name: 'ALE-0001', event_type: 'depreciated',
    actor: '', actor_name: '',
    from_status: '', to_status: '',
    timestamp: '2026-05-01 00:00:00', event_timestamp: '',
    root_doctype: '', root_record: '', notes: '',
  },
]
const getAssetTimelineSpy = vi.fn().mockResolvedValue({ items: CR60_TIMELINE })
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: (...a: unknown[]) => getAssetTimelineSpy(...a),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue({ valid: true, count: 3 }),
  deleteAsset: vi.fn().mockResolvedValue(undefined),
  getAssetLabelData: vi.fn().mockResolvedValue({}),
  markLabelPrinted: vi.fn(),
  regenerateAssetQrToken: vi.fn(),
  printAssetLabelsPdf: vi.fn(),
  LABEL_PDF_PRESETS: [{ key: 'tem-60x100', label: 'Tem 60×100mm' }],
  LABEL_PDF_PRESET: 'tem-60x100',
  labelPdfPresetLabel: () => 'Tem 60×100mm',
}))
vi.mock('@/api/imm04', () => ({ getCommissioningOrigin: vi.fn().mockResolvedValue(null) }))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => false }) }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: { email: 'tech@hosp.vn' } }) }))

import AssetDetailView from '@/views/asset/AssetDetailView.vue'

// Stub router-link giữ prop `to` để assert đích deep-link (KHÔNG cần router thật).
const RouterLinkStub = { props: ['to'], template: '<a :data-to="to"><slot /></a>' }
const stubs = {
  PageHeader: true, AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
  RelatedRecords: true, RouterLink: RouterLinkStub, 'router-link': RouterLinkStub,
}

async function mountTimeline() {
  const wrapper = mount(AssetDetailView, { props: { id: 'ASSET-0001' }, global: { stubs } })
  await flushPromises()
  const timelineTab = wrapper.findAll('button').filter(b => b.text() === 'Lịch sử').pop()!
  await timelineTab.trigger('click')
  await flushPromises()
  return wrapper
}

describe('TC-ALE-CR60-FE — deep-link hồ-sơ-gốc + actor_name', () => {
  beforeEach(() => getAssetTimelineSpy.mockClear())

  it('event có nguồn → deep-link tới ĐÚNG hồ sơ gốc (Asset Repair → /cm/work-orders/<phiếu>)', async () => {
    const wrapper = await mountTimeline()
    const links = wrapper.findAll('[data-testid="ale-root-link"]')
    // Chỉ ev1 có root resolvable ⇒ đúng 1 link, KHÔNG rò cho legacy/hệ-thống.
    expect(links.length).toBe(1)
    expect(links[0].attributes('data-to')).toBe('/cm/work-orders/WO-RP-2026-00123')
    expect(links[0].text()).toContain('WO-RP-2026-00123')
    // a11y: link icon-mang-nghĩa phải có aria-label mô tả hồ sơ gốc.
    expect(links[0].attributes('aria-label')).toContain('WO-RP-2026-00123')
  })

  it('hiển thị actor_name (full_name) THAY email thô khi có User', async () => {
    const wrapper = await mountTimeline()
    const actors = wrapper.findAll('[data-testid="ale-actor"]').map(n => n.text())
    // ev1: tên thật hiện, email KHÔNG lộ.
    expect(actors.some(t => t.includes('Nguyễn Văn Kỹ'))).toBe(true)
    expect(actors.join(' | ')).not.toContain('tech@hosp.vn')
  })

  it('actor không có User → fallback email; event hệ thống (actor rỗng) → KHÔNG dòng "bởi"', async () => {
    const wrapper = await mountTimeline()
    const actors = wrapper.findAll('[data-testid="ale-actor"]').map(n => n.text())
    // ev2 fallback == raw actor (email legacy vẫn hiện — đúng hợp đồng CR-60).
    expect(actors.some(t => t.includes('legacy@hosp.vn'))).toBe(true)
    // ev3 actor rỗng ⇒ đúng 2 dòng "bởi" (ev1 + ev2), KHÔNG có dòng rỗng "bởi ".
    expect(actors.length).toBe(2)
    expect(actors.every(t => t.replace('bởi', '').trim().length > 0)).toBe(true)
  })

  it('event legacy thiếu root → KHÔNG render link (không đoán → không 404)', async () => {
    const wrapper = await mountTimeline()
    const html = wrapper.html()
    // Không có đường dẫn list-của-transfer hay bất kỳ link nào cho ev2/ev3.
    expect(wrapper.findAll('[data-testid="ale-root-link"]').length).toBe(1)
    expect(html).not.toContain('/asset-transfers/')
  })
})
