// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho Kế hoạch mua sắm.
//
// Nút chuyển-trạng-thái ở ProcurementPlanDetailView gate theo `allowed_transitions`
// do BE emit (SSoT = get_transitions trên IMM Procurement Plan trong api/imm01.py) —
// KHÔNG hardcode `plan.workflow_state === 'X'`. FE = allowedTransitions.includes(action).
// Chống khiếu nại QTV: "nút Phê duyệt hiện rồi bấm mới báo Bạn không có quyền".
//
// Action khớp EXACT workflow.json (IMM-01 Plan Workflow):
//   Draft    --Phê duyệt kế hoạch--> Approved
//   Approved --Kích hoạt-----------> Active
//   Active   --Đóng kỳ kế hoạch----> Closed
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const getProcurementPlan = vi.fn()
vi.mock('@/api/imm01', () => ({
  getProcurementPlan: (...a: unknown[]) => getProcurementPlan(...a),
  rollIntoPlan: vi.fn(),
  listNeedsRequests: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 }),
  approvePlan: vi.fn(),
  activatePlan: vi.fn(),
  closePlan: vi.fn(),
  setBudgetEnvelope: vi.fn(),
  removeFromPlan: vi.fn(),
}))

import ProcurementPlanDetailView from './ProcurementPlanDetailView.vue'

type Plan = Record<string, unknown>

function makePlan(over: Plan = {}): Plan {
  return {
    name: 'PP-2026-00001', workflow_state: 'Draft',
    plan_year: 2026, plan_period: 'Q1', budget_envelope: 1_000_000,
    allocated_capex: 0, utilization_pct: 0, plan_items: [],
    allowed_transitions: [],
    ...over,
  }
}

async function mountDetail(plan: Plan) {
  getProcurementPlan.mockResolvedValue(plan)
  const w = mount(ProcurementPlanDetailView, {
    props: { id: 'PP-2026-00001' },
    global: { stubs: { CurrencyInput: true } },
  })
  await flushPromises()
  return w
}

const ALL_CTA = ['cta-approve', 'cta-activate', 'cta-close']
function ctasShown(w: Awaited<ReturnType<typeof mountDetail>>): string[] {
  return ALL_CTA.filter((id) => w.find(`[data-testid="${id}"]`).exists())
}

beforeEach(() => {
  getProcurementPlan.mockReset()
})

describe('IMM-01 CTA server-driven — Phê duyệt gate theo allowed_transitions', () => {
  it('(a) allowed=["Phê duyệt kế hoạch"] + Draft → nút "Phê duyệt" RENDER', async () => {
    const w = await mountDetail(makePlan({ workflow_state: 'Draft', allowed_transitions: ['Phê duyệt kế hoạch'] }))
    const btn = w.find('[data-testid="cta-approve"]')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('Phê duyệt')
  })

  it('(b) allowed=[] + Draft → nút "Phê duyệt" KHÔNG render (gate theo transitions, KHÔNG theo status literal)', async () => {
    // RED khi còn hardcode v-if="workflow_state === 'Draft'": nút vẫn hiện dù thiếu quyền.
    const w = await mountDetail(makePlan({ workflow_state: 'Draft', allowed_transitions: [] }))
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
  })

  it('(c) allowed=["Kích hoạt"] + Approved → chỉ "Kích hoạt" hiện, "Phê duyệt" ẩn', async () => {
    const w = await mountDetail(makePlan({ workflow_state: 'Approved', allowed_transitions: ['Kích hoạt'] }))
    expect(w.find('[data-testid="cta-activate"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
    expect(ctasShown(w)).toEqual(['cta-activate'])
  })
})

describe('IMM-01 CTA matrix — tập nút KHỚP allowed_transitions', () => {
  const EXPECTED: { state: string; allowed: string[]; ctas: string[] }[] = [
    { state: 'Draft', allowed: ['Phê duyệt kế hoạch'], ctas: ['cta-approve'] },
    // Approved: workflow chỉ emit 'Kích hoạt' (Approved→Active) — 'Đóng kỳ kế hoạch'
    // là transition từ Active, KHÔNG xuất hiện ở Approved ⇒ nút Đóng đúng-ra ẩn.
    { state: 'Approved', allowed: ['Kích hoạt'], ctas: ['cta-activate'] },
    { state: 'Active', allowed: ['Đóng kỳ kế hoạch'], ctas: ['cta-close'] },
    // Base-role-only / phiên không đủ quyền → BE trả [] → 0 nút CTA (triệt tiêu bấm-rồi-lỗi).
    { state: 'Draft', allowed: [], ctas: [] },
    { state: 'Closed', allowed: [], ctas: [] },
  ]
  for (const { state, allowed, ctas } of EXPECTED) {
    it(`${state} + allowed=[${allowed.join(', ')}] → CTA = [${ctas.join(', ')}]`, async () => {
      const w = await mountDetail(makePlan({ workflow_state: state, allowed_transitions: allowed }))
      expect(ctasShown(w).sort()).toEqual([...ctas].sort())
    })
  }
})

describe('IMM-01 CTA — allowed_transitions absent (BE chưa reload) → 0 nút, KHÔNG crash', () => {
  it('payload thiếu allowed_transitions → canDo=false cho mọi action', async () => {
    const p = makePlan({ workflow_state: 'Draft' })
    delete p.allowed_transitions
    const w = await mountDetail(p)
    expect(ctasShown(w)).toEqual([])
  })
})
