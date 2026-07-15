// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-12 BR-12-23 / CR-WF-12) — CTA "Mở lại điều tra" trên IncidentDetailView.
//
// Acceptance (map task FE):
//   • Nút SERVER-DRIVEN (GATE-8/LL-FE-51): chỉ hiện khi cap incident.close ∧
//     status==='Resolved' ∧ allowed_transitions.includes('In Progress').
//   • status==='Resolved' KHÔNG thừa — phân định pha: 'In Progress' cũng là đích của
//     "Bắt đầu xử lý" (Acknowledged→start_work). Acknowledged có 'In Progress' → ẩn "Mở lại".
//   • BE chưa đối soát map (Resolved thiếu 'In Progress' trong allowed_transitions) → ẩn nút.
//   • Thiếu cap incident.close → ẩn nút dù allowed_transitions hợp lệ.
//   • GATE-6c dead-control: reason người dùng gõ == tham số truyền vào reopenIncident.
//   • reason bắt buộc (BR-12-23) → nút xác nhận disabled khi rỗng, KHÔNG gọi endpoint.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { IncidentDetail } from '@/api/imm12'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'INC-2026-00001' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

const getIncidentSpy = vi.fn<() => Promise<IncidentDetail>>()
const reopenIncidentSpy = vi.fn((_name: string, _reason: string) => Promise.resolve({ name: 'INC-2026-00001', status: 'In Progress' }))
vi.mock('@/api/imm12', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm12')>()
  return {
    ...actual,
    getIncident: () => getIncidentSpy(),
    attachIncidentPhoto: vi.fn(),
    acknowledgeIncident: vi.fn(),
    startWork: vi.fn(),
    resolveIncident: vi.fn(),
    closeIncident: vi.fn(),
    cancelIncident: vi.fn(),
    reopenIncident: (name: string, reason: string) => reopenIncidentSpy(name, reason),
    createRca: vi.fn(),
  }
})
vi.mock('@/api/imm00', () => ({ deleteIncident: vi.fn() }))
const toastWarning = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: toastWarning }),
}))
const canSpy = vi.fn((_cap: string) => true)
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: canSpy }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ isSystemAdmin: false, user: { name: 'reporter@benhvien.vn' } }),
}))

import IncidentDetailView from './IncidentDetailView.vue'

const stubs = { ApproverSelect: true, WorkflowStepper: true, SlaBreachBadge: true }

function baseIncident(overrides: Partial<IncidentDetail>): IncidentDetail {
  return {
    name: 'INC-2026-00001',
    asset: 'AC-ASSET-2026-00042',
    incident_type: 'Failure',
    severity: 'High',
    status: 'Resolved',
    description: 'Máy ngừng hoạt động',
    reported_by: 'reporter@benhvien.vn',
    allowed_transitions: [],
    scene_photos: [],
    ...overrides,
  } as IncidentDetail
}

async function mountView() {
  const w = mount(IncidentDetailView, { global: { stubs } })
  await flushPromises()
  return w
}
type ViewWrapper = Awaited<ReturnType<typeof mountView>>

// CTA text đúng "Mở lại điều tra" (H2 modal = "Mở lại điều tra sự cố", confirm = "Xác nhận mở lại").
function reopenCta(w: ViewWrapper) {
  return w.findAll('button').find((b) => b.text().trim() === 'Mở lại điều tra')
}
function confirmBtn(w: ViewWrapper) {
  return w.findAll('button').find((b) => b.text().trim() === 'Xác nhận mở lại')
}

describe('IncidentDetailView — CTA "Mở lại điều tra" (BR-12-23 / CR-WF-12, server-driven)', () => {
  beforeEach(() => {
    getIncidentSpy.mockReset()
    reopenIncidentSpy.mockClear()
    toastWarning.mockClear()
    canSpy.mockReset()
    canSpy.mockReturnValue(true)
  })

  it('Resolved + allowed_transitions chứa "In Progress" + cap → HIỆN nút', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Resolved', allowed_transitions: ['Closed', 'RCA Required', 'In Progress'] }))
    const w = await mountView()
    expect(reopenCta(w)).toBeTruthy()
  })

  it('server chưa đối soát map: Resolved nhưng allowed_transitions THIẾU "In Progress" → ẨN nút', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Resolved', allowed_transitions: ['Closed', 'RCA Required'] }))
    const w = await mountView()
    expect(reopenCta(w)).toBeFalsy()
  })

  it('phân định pha: Acknowledged có "In Progress" (start_work) KHÔNG hiện "Mở lại" (hiện "Bắt đầu xử lý")', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Acknowledged', allowed_transitions: ['In Progress', 'Cancelled'] }))
    const w = await mountView()
    expect(reopenCta(w)).toBeFalsy()
    expect(w.findAll('button').some((b) => b.text().trim() === 'Bắt đầu xử lý')).toBe(true)
  })

  it('thiếu cap incident.close → ẨN nút dù allowed_transitions hợp lệ', async () => {
    canSpy.mockReturnValue(false)
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Resolved', allowed_transitions: ['Closed', 'In Progress'] }))
    const w = await mountView()
    expect(reopenCta(w)).toBeFalsy()
  })

  it('GATE-6c dead-control: reason người dùng gõ == tham số truyền reopenIncident(name, reason)', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Resolved', allowed_transitions: ['Closed', 'In Progress'] }))
    const w = await mountView()
    await reopenCta(w)!.trigger('click')
    await flushPromises()
    const ta = w.find('#reopen-reason')
    expect(ta.exists()).toBe(true)
    await ta.setValue('Sự cố tái phát sau 2 ngày')
    await confirmBtn(w)!.trigger('click')
    await flushPromises()
    expect(reopenIncidentSpy).toHaveBeenCalledTimes(1)
    expect(reopenIncidentSpy).toHaveBeenCalledWith('INC-2026-00001', 'Sự cố tái phát sau 2 ngày')
  })

  it('reason rỗng (BR-12-23 required) → nút xác nhận disabled, KHÔNG gọi endpoint', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Resolved', allowed_transitions: ['Closed', 'In Progress'] }))
    const w = await mountView()
    await reopenCta(w)!.trigger('click')
    await flushPromises()
    expect(confirmBtn(w)!.attributes('disabled')).toBeDefined()
    expect(reopenIncidentSpy).not.toHaveBeenCalled()
  })
})
