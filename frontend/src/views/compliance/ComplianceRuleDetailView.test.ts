// TDD — IMM-16 ComplianceRuleDetailView: field "Tần suất đánh giá" render nhãn VI
// (không leak English). evaluation_frequency='Weekly' → DOM 'Hàng tuần' (KHÔNG 'Weekly').
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { ComplianceRule } from '@/api/imm16'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'CR-2026-00001' } }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    loading: { value: false },
    run: (fn: () => Promise<unknown>) => fn(),
  }),
}))

const fetchRuleSpy = vi.fn<() => Promise<ComplianceRule>>()
vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    fetchRule: fetchRuleSpy,
    actionDeactivateRule: vi.fn(),
    actionReactivateRule: vi.fn(),
    actionUpdateRule: vi.fn(),
    actionCreateVersion: vi.fn(),
  }),
}))

import ComplianceRuleDetailView from './ComplianceRuleDetailView.vue'

const stubs = {
  PageHeader: true, StatusBadge: true, BaseModal: true,
  SkeletonLoader: true, RecordHistory: true, RouterLink: true,
}

function baseRule(overrides: Partial<ComplianceRule>): ComplianceRule {
  return {
    name: 'CR-2026-00001',
    rule_code: 'CR-001',
    rule_name: 'Quy tắc test',
    source_module: 'IMM-05',
    category: 'Document',
    severity: 'Medium',
    evaluation_frequency: 'Daily',
    is_active: 1,
    ...overrides,
  } as ComplianceRule
}

describe('ComplianceRuleDetailView — Tần suất đánh giá (i18n leak guard)', () => {
  beforeEach(() => { fetchRuleSpy.mockReset() })

  it("evaluation_frequency='Weekly' → DOM 'Hàng tuần', KHÔNG 'Weekly'", async () => {
    fetchRuleSpy.mockResolvedValue(baseRule({ evaluation_frequency: 'Weekly' }))
    const wrapper = mount(ComplianceRuleDetailView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Hàng tuần')
    expect(html).not.toContain('>Weekly<')
    expect(html).not.toMatch(/>[^<]*\bWeekly\b[^<]*</)
  })

  it("evaluation_frequency='Realtime' → DOM 'Thời gian thực', KHÔNG raw 'Realtime'", async () => {
    fetchRuleSpy.mockResolvedValue(baseRule({ evaluation_frequency: 'Realtime' }))
    const wrapper = mount(ComplianceRuleDetailView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Thời gian thực')
    expect(html).not.toMatch(/>[^<]*\bRealtime\b[^<]*</)
  })
})
