// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-12 CR-WF-12-RCA-ENTRY) — CTA "Yêu cầu phân tích nguyên nhân gốc" trên
// IncidentDetailView (Resolved → RCA Required, action workflow 'Yêu cầu RCA').
//
// Acceptance (map task FE):
//   • Nút SERVER-DRIVEN (GATE-8/LL-FE-51): chỉ hiện khi cap corrective.write ∧
//     status==='Resolved' ∧ allowed_transitions.includes('RCA Required').
//   • Dead-CTA guard: BE Resolved nhưng allowed_transitions THIẾU 'RCA Required'
//     (chưa cấp driver) → ẩn nút.
//   • status != 'Resolved' (vd đã ở 'RCA Required') → ẩn nút (phân định pha).
//   • Thiếu cap corrective.write → ẩn nút dù allowed_transitions hợp lệ.
//   • GATE-6c dead-control: rca_reason người dùng gõ == tham số truyền requestRca.
//   • rca_reason TÙY CHỌN (BE precondition duy nhất = status) → nút xác nhận KHÔNG
//     disabled khi rỗng, vẫn gọi endpoint với chuỗi rỗng.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { IncidentDetail } from '@/api/imm12'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'INC-2026-00001' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

const getIncidentSpy = vi.fn<() => Promise<IncidentDetail>>()
const requestRcaSpy = vi.fn((_name: string, _reason: string) =>
  Promise.resolve({ name: 'INC-2026-00001', status: 'RCA Required', rca_record: 'RCA-2026-00001' }))
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
    reopenIncident: vi.fn(),
    requestRca: (name: string, reason: string) => requestRcaSpy(name, reason),
    createRca: vi.fn(),
  }
})
vi.mock('@/api/imm00', () => ({ deleteIncident: vi.fn() }))
const toastSuccess = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: toastSuccess, error: vi.fn(), warning: vi.fn() }),
}))
// can() phân biệt theo cap: corrective.write gate CTA "Yêu cầu RCA". Cấu hình per-test.
const canImpl = vi.fn((_cap: string) => true)
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (cap: string) => canImpl(cap) }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ isSystemAdmin: false, user: { name: 'reporter@benhvien.vn' } }),
}))

import IncidentDetailView from '@/views/incident/IncidentDetailView.vue'

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

const CTA_TEXT = 'Yêu cầu phân tích nguyên nhân gốc'
function requestRcaCta(w: ViewWrapper) {
  // Nút hành động ở header (KHÔNG phải H2 modal cùng chữ) — lọc theo class nút hành động.
  return w.findAll('button').find(
    (b) => b.text().trim() === CTA_TEXT && b.classes().some((c) => c.startsWith('bg-orange')),
  )
}
function confirmBtn(w: ViewWrapper) {
  return w.findAll('button').find((b) => b.text().trim() === 'Xác nhận yêu cầu')
}

describe('IncidentDetailView — CTA "Yêu cầu phân tích nguyên nhân gốc" (CR-WF-12-RCA-ENTRY, server-driven)', () => {
  beforeEach(() => {
    getIncidentSpy.mockReset()
    requestRcaSpy.mockClear()
    toastSuccess.mockClear()
    canImpl.mockReset()
    canImpl.mockReturnValue(true)
  })

  it('Resolved + allowed_transitions chứa "RCA Required" + cap → HIỆN nút', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Resolved', allowed_transitions: ['Closed', 'RCA Required', 'In Progress'] }))
    const w = await mountView()
    expect(requestRcaCta(w)).toBeTruthy()
  })

  it('dead-CTA guard: Resolved nhưng allowed_transitions THIẾU "RCA Required" → ẨN nút', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Resolved', allowed_transitions: ['Closed', 'In Progress'] }))
    const w = await mountView()
    expect(requestRcaCta(w)).toBeFalsy()
  })

  it('phân định pha: đã ở "RCA Required" → ẨN nút (không lặp lại yêu cầu)', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'RCA Required', allowed_transitions: ['RCA Required'] }))
    const w = await mountView()
    expect(requestRcaCta(w)).toBeFalsy()
  })

  it('thiếu cap corrective.write → ẨN nút dù allowed_transitions hợp lệ', async () => {
    canImpl.mockImplementation((cap: string) => cap !== 'corrective.write')
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Resolved', allowed_transitions: ['Closed', 'RCA Required'] }))
    const w = await mountView()
    expect(requestRcaCta(w)).toBeFalsy()
  })

  it('GATE-6c dead-control: rca_reason người dùng gõ == tham số truyền requestRca(name, reason)', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Resolved', allowed_transitions: ['Closed', 'RCA Required'] }))
    const w = await mountView()
    await requestRcaCta(w)!.trigger('click')
    await flushPromises()
    const ta = w.find('#rca-reason')
    expect(ta.exists()).toBe(true)
    await ta.setValue('Nghi ngờ lỗi hệ thống, cần phân tích sâu')
    await confirmBtn(w)!.trigger('click')
    await flushPromises()
    expect(requestRcaSpy).toHaveBeenCalledTimes(1)
    expect(requestRcaSpy).toHaveBeenCalledWith('INC-2026-00001', 'Nghi ngờ lỗi hệ thống, cần phân tích sâu')
  })

  it('rca_reason TÙY CHỌN: nút xác nhận KHÔNG disabled khi rỗng, vẫn gọi endpoint', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ status: 'Resolved', allowed_transitions: ['Closed', 'RCA Required'] }))
    const w = await mountView()
    await requestRcaCta(w)!.trigger('click')
    await flushPromises()
    expect(confirmBtn(w)!.attributes('disabled')).toBeUndefined()
    await confirmBtn(w)!.trigger('click')
    await flushPromises()
    expect(requestRcaSpy).toHaveBeenCalledWith('INC-2026-00001', '')
  })
})
