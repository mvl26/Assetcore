// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-12 BR-12-09/13 / INV-SLA-5 — mobile CR-21) IncidentDetailView §Tình trạng SLA.
//
// Acceptance (map task FE):
//   • section 'Tình trạng SLA' có 2 dòng Phản hồi / Xử lý.
//   • is_resolution_breached=1 (server flag derived) → dòng Xử lý render badge 'Quá hạn'.
//   • is_response_breached vắng nhưng response_breached raw=1 → fallback → dòng Phản hồi 'Quá hạn'.
//   • cả server-flag lẫn cờ thô = 0 → cả 2 dòng 'Trong hạn'.
//   • nhánh terminal-flag: Closed + is_resolution_breached=1 → Xử lý 'Quá hạn' (INV-SLA-6).
//   • KHÔNG so ngày client-clock: resolution_due_at quá khứ NHƯNG cờ=0 → vẫn 'Trong hạn'
//     (chứng minh FE đọc cờ server-flag, KHÔNG tự tính từ due_at — overdue_server_flag SSoT).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { IncidentDetail } from '@/api/imm12'
import { SLA_STATUS_LABEL } from '@/constants/labels'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'INC-2026-00001' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

const getIncidentSpy = vi.fn<() => Promise<IncidentDetail>>()
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
    createRca: vi.fn(),
  }
})
vi.mock('@/api/imm00', () => ({ deleteIncident: vi.fn() }))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ isSystemAdmin: false, user: { name: 'reporter@benhvien.vn' } }),
}))

import IncidentDetailView from '@/views/incident/IncidentDetailView.vue'

// KHÔNG stub SlaBreachBadge — muốn assert nhãn 'Quá hạn'/'Trong hạn' render thật.
const stubs = { ApproverSelect: true, WorkflowStepper: true }

function baseIncident(overrides: Partial<IncidentDetail>): IncidentDetail {
  return {
    name: 'INC-2026-00001',
    asset: 'AC-ASSET-2026-00042',
    incident_type: 'Failure',
    severity: 'High',
    status: 'In Progress',
    description: 'Máy ngừng hoạt động',
    reported_by: 'reporter@benhvien.vn',
    allowed_transitions: ['Resolved'],
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

// Trả text của dòng (Phản hồi / Xử lý) chứa nhãn label.
function rowText(w: ViewWrapper, label: string): string {
  const row = w.findAll('dl > div').find((r) => r.text().includes(label))
  return row ? row.text() : ''
}

describe('IncidentDetailView — section Tình trạng SLA (BR-12-09/13)', () => {
  beforeEach(() => { getIncidentSpy.mockReset() })

  it('luôn hiển thị section "Tình trạng SLA" với 2 dòng Phản hồi / Xử lý', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({}))
    const w = await mountView()
    expect(w.text()).toContain('Tình trạng SLA')
    expect(w.text()).toContain('Phản hồi')
    expect(w.text()).toContain('Xử lý')
  })

  it('is_resolution_breached=1 (server flag) → dòng Xử lý render "Quá hạn"', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({ is_resolution_breached: 1, is_response_breached: 0 }))
    const w = await mountView()
    expect(rowText(w, 'Xử lý')).toContain(SLA_STATUS_LABEL.breached)
    // Phản hồi cờ=0 → Trong hạn
    expect(rowText(w, 'Phản hồi')).toContain(SLA_STATUS_LABEL.within)
  })

  it('is_response_breached vắng nhưng response_breached raw=1 → fallback → dòng Phản hồi "Quá hạn"', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({
      is_response_breached: undefined, response_breached: 1,
      is_resolution_breached: undefined, resolution_breached: 0,
    }))
    const w = await mountView()
    expect(rowText(w, 'Phản hồi')).toContain(SLA_STATUS_LABEL.breached)
    expect(rowText(w, 'Xử lý')).toContain(SLA_STATUS_LABEL.within)
  })

  it('cả server-flag lẫn cờ thô = 0 → cả 2 dòng "Trong hạn"', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({
      is_response_breached: 0, response_breached: 0,
      is_resolution_breached: 0, resolution_breached: 0,
    }))
    const w = await mountView()
    expect(rowText(w, 'Phản hồi')).toContain(SLA_STATUS_LABEL.within)
    expect(rowText(w, 'Xử lý')).toContain(SLA_STATUS_LABEL.within)
    // KHÔNG leak English
    expect(w.text().toLowerCase()).not.toContain('breach')
  })

  it('terminal Closed + is_resolution_breached=1 (nhánh cờ INV-SLA-6) → Xử lý "Quá hạn"', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({
      status: 'Closed', allowed_transitions: [],
      is_resolution_breached: 1, is_response_breached: 0,
    }))
    const w = await mountView()
    expect(rowText(w, 'Xử lý')).toContain(SLA_STATUS_LABEL.breached)
  })

  it('KHÔNG so ngày client-clock: resolution_due_at quá khứ NHƯNG cờ=0 → vẫn "Trong hạn"', async () => {
    getIncidentSpy.mockResolvedValue(baseIncident({
      is_resolution_breached: 0, resolution_breached: 0,
      // hạn ở quá khứ xa — nếu FE tự so client-clock sẽ ra "Quá hạn" (SAI).
      resolution_due_at: '2000-01-01 00:00:00',
    }))
    const w = await mountView()
    expect(rowText(w, 'Xử lý')).toContain(SLA_STATUS_LABEL.within)
    expect(rowText(w, 'Xử lý')).not.toContain(SLA_STATUS_LABEL.breached)
  })
})
