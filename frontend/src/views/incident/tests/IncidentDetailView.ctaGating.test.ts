// Copyright (c) 2026, AssetCore Team
// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho Incident (IMM-12).
// Pattern: cm/cmWorkOrderCtaGating.test.ts (WF-ADMIN-E2E — FE guard bổ sung).
//
// Mọi nút CHUYỂN-TRẠNG-THÁI ở IncidentDetailView render DUY NHẤT từ
// `allowed_transitions` do BE emit (SSoT = _VALID_TRANSITIONS, services/imm12.py:243
// → get_incident_detail). FE = (capability && allowedTransitions.includes(target)).
// `status === 'X'` trong view CHỈ được giữ để PHÂN ĐỊNH PHA (vd 'In Progress' vừa là
// đích của "Bắt đầu xử lý" [Acknowledged→] vừa của "Mở lại điều tra" [Resolved→])
// hoặc display (badge/stepper/section) — KHÔNG được là driver độc lập của CTA:
// allowed_transitions=[] ⇒ 0 nút transition DÙ status khớp nhánh hardcode.
//
// SSoT map (mirror _VALID_TRANSITIONS — key = status, value = target states):
//   Open         → [Acknowledged, Cancelled]
//   Acknowledged → [In Progress, Cancelled]
//   In Progress  → [Resolved, Cancelled]
//   Resolved     → [Closed, RCA Required, In Progress]
//   RCA Required / Closed / Cancelled → []  (terminal / auto-advance → 0 CTA)
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
    acknowledgeIncident: vi.fn(),
    startWork: vi.fn(),
    resolveIncident: vi.fn(),
    closeIncident: vi.fn(),
    cancelIncident: vi.fn(),
    reopenIncident: vi.fn(),
    requestRca: vi.fn(),
    createRca: vi.fn(),
    attachIncidentPhoto: vi.fn(),
  }
})
vi.mock('@/api/imm00', () => ({ deleteIncident: vi.fn() }))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}))

// Capability controllable per test (mặc định: đủ mọi quyền incident + corrective).
let canImpl: (c: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ isSystemAdmin: false, user: { name: 'qa@benhvien.vn' } }),
}))

import IncidentDetailView from '@/views/incident/IncidentDetailView.vue'

// SSoT transition map (mirror _VALID_TRANSITIONS trong services/imm12.py).
const INCIDENT_TRANSITIONS: Record<string, string[]> = {
  'Open': ['Acknowledged', 'Cancelled'],
  'Acknowledged': ['In Progress', 'Cancelled'],
  'In Progress': ['Resolved', 'Cancelled'],
  'Resolved': ['Closed', 'RCA Required', 'In Progress'],
  'RCA Required': [],
  'Closed': [],
  'Cancelled': [],
}

// 7 nút CTA transition (nhãn VI hiển thị → target state). KHÔNG gồm "Xóa"
// (hard-delete admin-only, không phải workflow transition) và "Tạo phân tích
// nguyên nhân gốc" (tạo record RCA liên kết, không đổi status Incident).
const TRANSITION_CTA = [
  'Tiếp nhận', // → Acknowledged ("Ghi nhận")
  'Bắt đầu xử lý', // → In Progress
  'Đánh dấu đã giải quyết', // → Resolved
  'Đóng sự cố', // → Closed
  'Yêu cầu phân tích nguyên nhân gốc', // → RCA Required
  'Mở lại điều tra', // Resolved → In Progress (BR-12-23)
  'Hủy (báo nhầm)', // → Cancelled
] as const

type Status = IncidentDetail['status']

function incident(over: Partial<IncidentDetail> = {}): IncidentDetail {
  const status = (over.status as Status) ?? 'Open'
  return {
    name: 'INC-2026-00077',
    asset: 'AC-ASSET-2026-00042',
    asset_name: 'Máy thở CTA',
    incident_type: 'Failure',
    severity: 'Medium',
    status,
    description: 'Thiết bị dừng đột ngột',
    reported_by: 'reporter@benhvien.vn',
    reported_at: '2026-06-01 08:00:00',
    allowed_transitions: INCIDENT_TRANSITIONS[status] ?? [],
    scene_photos: [],
    ...over,
  } as IncidentDetail
}

const stubs = { ApproverSelect: true, WorkflowStepper: true, SlaBreachBadge: true }

async function mountView(fixture: IncidentDetail) {
  getIncidentSpy.mockResolvedValue(fixture)
  const w = mount(IncidentDetailView, { global: { stubs } })
  await flushPromises()
  return w
}
type ViewWrapper = Awaited<ReturnType<typeof mountView>>

function ctasShown(w: ViewWrapper): string[] {
  const texts = w.findAll('button').map((b) => b.text().trim())
  return TRANSITION_CTA.filter((label) => texts.includes(label))
}

beforeEach(() => {
  getIncidentSpy.mockReset()
  canImpl = () => true
})

describe('IMM-12 CTA server-driven — TC-FE-1: allowed_transitions là driver duy nhất', () => {
  it('Open + allowed=["Acknowledged"] (Ghi nhận) → render ĐÚNG 1 nút transition = "Tiếp nhận"', async () => {
    const w = await mountView(incident({ status: 'Open', allowed_transitions: ['Acknowledged'] }))
    expect(ctasShown(w)).toEqual(['Tiếp nhận'])
  })

  it('Open + allowed=[] → 0 nút transition DÙ status khớp nhánh hardcode cũ', async () => {
    const w = await mountView(incident({ status: 'Open', allowed_transitions: [] }))
    expect(ctasShown(w)).toEqual([])
  })

  it.each(Object.keys(INCIDENT_TRANSITIONS) as Status[])(
    '%s + allowed=[] → 0 nút transition (server rút quyền ⇒ FE không tự chế nút)',
    async (status) => {
      const w = await mountView(incident({ status, allowed_transitions: [] }))
      expect(ctasShown(w)).toEqual([])
    },
  )
})

describe('IMM-12 CTA matrix — tập nút KHỚP allowed_transitions per status (đủ mọi quyền)', () => {
  const EXPECTED: Record<string, string[]> = {
    'Open': ['Tiếp nhận', 'Hủy (báo nhầm)'],
    'Acknowledged': ['Bắt đầu xử lý', 'Hủy (báo nhầm)'],
    'In Progress': ['Đánh dấu đã giải quyết', 'Hủy (báo nhầm)'],
    // Resolved KHÔNG có 'Cancelled' trong allowed ⇒ "Hủy (báo nhầm)" phải ẩn.
    'Resolved': ['Đóng sự cố', 'Yêu cầu phân tích nguyên nhân gốc', 'Mở lại điều tra'],
    'RCA Required': [],
    'Closed': [],
    'Cancelled': [],
  }
  for (const [status, expected] of Object.entries(EXPECTED)) {
    it(`${status} → CTA = [${expected.join(', ')}]`, async () => {
      const w = await mountView(incident({ status: status as Status }))
      expect(ctasShown(w).sort()).toEqual([...expected].sort())
    })
  }
})

describe('IMM-12 CTA phân định pha — status=== giữ cho disambiguation, KHÔNG phải driver', () => {
  it('Acknowledged (allowed chứa "In Progress") → hiện "Bắt đầu xử lý", KHÔNG "Mở lại điều tra"', async () => {
    const w = await mountView(incident({ status: 'Acknowledged' }))
    const shown = ctasShown(w)
    expect(shown).toContain('Bắt đầu xử lý')
    expect(shown).not.toContain('Mở lại điều tra')
  })

  it('Resolved (allowed chứa "In Progress") → hiện "Mở lại điều tra", KHÔNG "Bắt đầu xử lý"', async () => {
    const w = await mountView(incident({ status: 'Resolved' }))
    const shown = ctasShown(w)
    expect(shown).toContain('Mở lại điều tra')
    expect(shown).not.toContain('Bắt đầu xử lý')
  })
})

describe('IMM-12 CTA capability — gate = (cap && includes), thiếu cap ⇒ ẩn', () => {
  it('Resolved thiếu incident.close → "Đóng sự cố" + "Mở lại điều tra" ẩn; "Yêu cầu RCA" (corrective.write) vẫn hiện', async () => {
    canImpl = (c: string) => c !== 'incident.close'
    const w = await mountView(incident({ status: 'Resolved' }))
    expect(ctasShown(w)).toEqual(['Yêu cầu phân tích nguyên nhân gốc'])
  })

  it('THIẾU mọi capability → 0 nút transition dù allowed_transitions đầy đủ', async () => {
    canImpl = () => false
    const w = await mountView(incident({ status: 'Resolved' }))
    expect(ctasShown(w)).toEqual([])
  })
})
