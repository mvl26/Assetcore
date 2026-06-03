// TDD [FE TDD-8] — IMM-16 ScorecardView regression guard:
// The view must render the BE-computed `score_pct` VERBATIM and must NOT
// inline-compute the score from compliant/non_compliant/total counts.
//
// Regression context (compute_compliance_rate SoT): pending findings
// (Open + Under Review) are EXCLUDED from the score denominator. So for a
// payload {compliant:1, non_compliant:1, pending:1, total:3} the correct
// score is 50.0 (1/(1+1)), NOT 66.67 (a naive (total-nc)/total = 2/3).
// If the FE ever derived the score from counts it would print 66.7% — this
// test fails loudly on that divergence.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { ComplianceScorecard } from '@/api/imm16'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: {} }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    loading: { value: false },
    run: (fn: () => Promise<unknown>) => fn(),
  }),
}))

const getCurrentScorecardSpy = vi.fn<() => Promise<ComplianceScorecard>>()
vi.mock('@/api/imm16', () => ({
  getCurrentScorecard: () => getCurrentScorecardSpy(),
  getScorecardByPeriod: () => getCurrentScorecardSpy(),
  runComplianceEvaluation: vi.fn(),
  generateScorecard: vi.fn(),
}))

vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    scorecards: [],
    scorecardsPagination: { page: 1, total: 0, total_pages: 0, page_size: 20 },
    scorecardsLoading: false,
    fetchScorecards: vi.fn().mockResolvedValue(undefined),
    actionPublishScorecard: vi.fn(),
  }),
}))

import ScorecardView from './ScorecardView.vue'

const stubs = { PageHeader: true, SkeletonLoader: true, RouterLink: true }

function baseScorecard(overrides: Partial<ComplianceScorecard>): ComplianceScorecard {
  return {
    name: 'SC-2026-00001',
    period_year: 2026,
    period_month: 6,
    scope: 'Hospital',
    score_pct: 50.0,
    trend_vs_prev_month: 0,
    capa_open_count: 0,
    capa_overdue_count: 0,
    is_published: 0,
    ...overrides,
  } as ComplianceScorecard
}

describe('ScorecardView — score_pct verbatim (no inline-compute) [FE TDD-8]', () => {
  beforeEach(() => { getCurrentScorecardSpy.mockReset() })

  it('renders BE score_pct=50.0 verbatim for a payload with pending>0 (not 66.7 from counts)', async () => {
    getCurrentScorecardSpy.mockResolvedValue(baseScorecard({
      score_pct: 50.0,
      total_rules_evaluated: 3,
      compliant_count: 1,
      non_compliant_count: 1,
      pending_count: 1,
    }))
    const wrapper = mount(ScorecardView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()

    // Score shown exactly as BE computed it.
    expect(html).toContain('50.0%')
    // Must NOT have derived 66.7% from (total - nc) / total = 2/3.
    expect(html).not.toContain('66.7%')
    expect(html).not.toContain('66.67')
  })

  it('shows the "Đang xét: N" pending badge so 100 − score is not misread as compliant', async () => {
    getCurrentScorecardSpy.mockResolvedValue(baseScorecard({
      score_pct: 50.0,
      compliant_count: 1,
      non_compliant_count: 1,
      pending_count: 1,
    }))
    const wrapper = mount(ScorecardView, { global: { stubs } })
    await flushPromises()

    const badge = wrapper.find('[data-testid="pending-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('Đang xét: 1')

    const breakdown = wrapper.find('[data-testid="adjudication-breakdown"]')
    expect(breakdown.text()).toContain('Tuân thủ: 1')
    expect(breakdown.text()).toContain('Không tuân thủ: 1')
  })

  it('renders score verbatim even when adjudicated==0 → score_pct=100.0 (no NC confirmed)', async () => {
    getCurrentScorecardSpy.mockResolvedValue(baseScorecard({
      score_pct: 100.0,
      total_rules_evaluated: 3,
      compliant_count: 0,
      non_compliant_count: 0,
      pending_count: 3,
    }))
    const wrapper = mount(ScorecardView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('100.0%')
    expect(wrapper.find('[data-testid="pending-badge"]').text()).toContain('Đang xét: 3')
  })

  it('does not render the breakdown row when BE omits the counts (back-compat payload)', async () => {
    getCurrentScorecardSpy.mockResolvedValue(baseScorecard({ score_pct: 87.5 }))
    const wrapper = mount(ScorecardView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.find('[data-testid="adjudication-breakdown"]').exists()).toBe(false)
    expect(wrapper.html()).toContain('87.5%')
  })

  it('does not leak raw English finding status codes into the DOM', async () => {
    getCurrentScorecardSpy.mockResolvedValue(baseScorecard({
      score_pct: 50.0,
      compliant_count: 1,
      non_compliant_count: 1,
      pending_count: 1,
    }))
    const wrapper = mount(ScorecardView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).not.toContain('Under Review')
    expect(html).not.toContain('Confirmed NC')
    expect(html).not.toContain('>Open<')
  })
})
