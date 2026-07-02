// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho phiếu
// kiểm kê. Nút Submit/Post ở CycleCountDetailView gate theo `allowed_transitions`
// do BE emit (_cycle_allowed_transitions trong services/imm15.py) — KHÔNG hardcode
// `detail.status === 'X'`. Mirror pmWorkOrderDetailCtaGate.test.ts.
//
// Contract action token:
//   ['Submit'] → chỉ nút cta-submit
//   ['Post']   → chỉ nút cta-post
//   []         → 0 nút hành động (Posted terminal / thiếu quyền)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn() }),
}))

type Detail = Record<string, unknown>
let mockDetail: Detail = {}
const getCycleCount = vi.fn(async () => mockDetail)
vi.mock('@/api/imm15', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm15')>()
  return { ...actual, getCycleCount: (name: string) => getCycleCount(name) }
})

import CycleCountDetailView from './CycleCountDetailView.vue'

function makeDetail(allowed: string[], over: Detail = {}): Detail {
  const status = (over.status as string)
    ?? (allowed.includes('Submit') ? 'Planned'
      : allowed.includes('Post') ? 'Reviewed' : 'Posted')
  return {
    name: 'CYC-2026-00042',
    warehouse: 'WH-A', warehouse_name: 'Kho Trung tâm',
    count_date: '2026-06-01', count_type: 'Cycle',
    counted_by: 'a@x.vn', counted_by_name: 'Thủ kho A',
    verified_by: '', verified_by_name: '',
    status,
    variance_count: 1, variance_value: 500000,
    items: [{
      spare_part: 'SP-1', part_name: 'Cảm biến SpO2', system_qty: 20,
      counted_qty: 18, variance_qty: -2, variance_pct: 10, variance_value: -500000,
    }],
    adjustment_ref: '', capa_created: 0,
    allowed_transitions: allowed,
    ...over,
  }
}

async function mountDetail() {
  const w = mount(CycleCountDetailView, {
    global: {
      stubs: { RouterLink: true, Transition: false, ApproverSelect: true, WorkflowStepper: true },
    },
  })
  await flushPromises()
  return w
}

const ALL_CTA = ['cta-submit', 'cta-post']
function ctasShown(w: Awaited<ReturnType<typeof mountDetail>>): string[] {
  return ALL_CTA.filter(id => w.find(`[data-testid="${id}"]`).exists())
}

beforeEach(() => {
  setActivePinia(createPinia())
  getCycleCount.mockClear()
})

describe('Cycle Count CTA gate — theo allowed_transitions (server-driven)', () => {
  it("allowed=['Submit'] → chỉ nút Submit", async () => {
    mockDetail = makeDetail(['Submit'])
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-submit"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-post"]').exists()).toBe(false)
    expect(ctasShown(w)).toEqual(['cta-submit'])
  })

  it("allowed=['Post'] → chỉ nút Post", async () => {
    mockDetail = makeDetail(['Post'])
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-post"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-submit"]').exists()).toBe(false)
    expect(ctasShown(w)).toEqual(['cta-post'])
  })

  it('allowed=[] (Posted terminal) → 0 nút hành động', async () => {
    mockDetail = makeDetail([], { status: 'Posted' })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
  })

  it("RED-guard: status='Reviewed' NHƯNG allowed=[] (thiếu quyền) → KHÔNG lộ nút Post", async () => {
    // Nếu view hardcode status==='Reviewed' thì test này sẽ đỏ.
    mockDetail = makeDetail([], { status: 'Reviewed' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-post"]').exists()).toBe(false)
  })

  it('Posted → hiển thị bút toán điều chỉnh + cảnh báo CAPA khi capa_created>0', async () => {
    mockDetail = makeDetail([], {
      status: 'Posted', adjustment_ref: 'SM-ADJ-2026-0001', capa_created: 2,
    })
    const w = await mountDetail()
    expect(w.text()).toContain('SM-ADJ-2026-0001')
    expect(w.text()).toContain('hành động khắc phục/phòng ngừa')
  })
})
