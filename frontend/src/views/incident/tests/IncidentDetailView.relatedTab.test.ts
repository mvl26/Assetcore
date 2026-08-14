// Copyright (c) 2026, AssetCore Team
// TDD — TC-CONNTAB-08 + ca A4 (AC-CR-87 vòng 3): «Bản ghi liên quan» thành TAB mount LƯỜI
// ở màn chi tiết phiếu sự cố (IMM-12).
//
// Ca A4 «không mất dữ liệu khi đổi tab» được đo bằng HAI bằng chứng độc lập, vì thân màn
// này không có ô nhập văn bản nào (ảnh hiện trường dùng input file — không gán value được):
//   1. state DOM tự đặt trên panel chính SỐNG SÓT qua vòng đổi tab, và phần tử panel là
//      CÙNG MỘT node (v-show ⇒ không unmount; nếu đổi sang v-if node sẽ khác ⇒ ĐỎ);
//   2. `getIncident` KHÔNG bị gọi lần 2 (không remount ⇒ không refetch).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { IncidentDetail } from '@/api/imm12'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'INC-2026-00077' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

const getIncidentSpy = vi.fn<() => Promise<IncidentDetail>>()
vi.mock('@/api/imm12', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm12')>()
  return {
    ...actual,
    getIncident: () => getIncidentSpy(),
    attachIncidentPhoto: vi.fn(), acknowledgeIncident: vi.fn(), startWork: vi.fn(),
    resolveIncident: vi.fn(), closeIncident: vi.fn(), cancelIncident: vi.fn(),
    reopenIncident: vi.fn(), requestRca: vi.fn(), createRca: vi.fn(),
  }
})
vi.mock('@/api/imm00', () => ({ deleteIncident: vi.fn() }))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ isSystemAdmin: false, user: { name: 'reporter@benhvien.vn' } }),
}))

const getConnections = vi.fn()
vi.mock('@/api/connections', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/connections')>()),
  getConnections: (...a: unknown[]) => getConnections(...a),
}))

import RelatedRecords from '@/components/common/RelatedRecords.vue'
import IncidentDetailView from '@/views/incident/IncidentDetailView.vue'
import { expectVietnameseTabs } from '@/test/tabLabelParity'

const INC_NAME = 'INC-2026-00077'

function incFixture(): IncidentDetail {
  return {
    name: INC_NAME, asset: 'AC-ASSET-0077', asset_name: 'Máy thở CTA',
    incident_type: 'Device Failure', severity: 'Medium', status: 'Open',
    description: 'Máy báo lỗi khi khởi động', reported_by: 'dd@benhvien.vn',
    reported_at: '2026-06-01 08:00:00', patient_affected: 0, rca_required: 0,
    scene_photos: [], allowed_transitions: ['Acknowledged', 'Cancelled'],
  } as unknown as IncidentDetail
}

async function mountDetail() {
  const w = mount(IncidentDetailView, {
    global: { stubs: { ApproverSelect: true, WorkflowStepper: true, SlaBreachBadge: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  getConnections.mockReset()
  getConnections.mockResolvedValue({
    doctype: 'Incident Report', name: INC_NAME, total: 0, groups: [],
  })
  getIncidentSpy.mockReset()
  getIncidentSpy.mockResolvedValue(incFixture())
})

describe('TC-CONNTAB-08 — IMM-12: tab «Bản ghi liên quan» mount lười', () => {
  it('tab mặc định ⇒ 0 lần gọi get_connections ∧ 0 khối liên quan trong DOM', async () => {
    const w = await mountDetail()
    expect(getConnections).toHaveBeenCalledTimes(0)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(0)
    expect(w.find('[data-testid="tab-panel-related"]').exists()).toBe(false)
  })

  it('bấm tab liên quan ⇒ ĐÚNG 1 lần gọi ∧ prop = (Incident Report, mã phiếu)', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    expect(getConnections).toHaveBeenCalledTimes(1)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(1)

    const rr = w.findComponent(RelatedRecords)
    expect(rr.props('doctype')).toBe('Incident Report')
    expect(rr.props('name')).toBe(INC_NAME)
  })

  it('tab liên quan active ⇒ [data-testid="tab-panel-detail"] có display:none', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="tab-panel-detail"]').attributes('style')).toContain('display: none')
  })

  it('nhãn tab 100% tiếng Việt (LL-FE-53)', async () => {
    expectVietnameseTabs(await mountDetail())
  })
})

describe('TC-CONNTAB-08 · ca A4 — đổi tab KHÔNG unmount thân trang, KHÔNG nạp lại phiếu', () => {
  it('state DOM trên panel chính CÒN NGUYÊN sau vòng đổi tab (cùng một node)', async () => {
    const w = await mountDetail()
    const before = w.find('[data-testid="tab-panel-detail"]').element as HTMLElement
    before.dataset.giaTriDangNhap = 'giữ nguyên'

    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="tab-detail"]').trigger('click')
    await flushPromises()

    const after = w.find('[data-testid="tab-panel-detail"]').element as HTMLElement
    expect(after).toBe(before)
    expect(after.dataset.giaTriDangNhap).toBe('giữ nguyên')
    expect(after.getAttribute('style') || '').not.toContain('display: none')
  })

  it('getIncident KHÔNG bị gọi lần 2 khi đổi tab', async () => {
    const w = await mountDetail()
    expect(getIncidentSpy).toHaveBeenCalledTimes(1)

    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="tab-detail"]').trigger('click')
    await flushPromises()

    expect(getIncidentSpy).toHaveBeenCalledTimes(1)
  })
})
