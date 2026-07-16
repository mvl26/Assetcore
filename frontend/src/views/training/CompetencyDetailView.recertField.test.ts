// TC-06-FE-01: training/CompetencyDetailView "Hạn tái chứng nhận" panel.
//
// Locks the read-path contract at the FE boundary: when get_competency returns a
// record carrying recertification_due_date (BE field-list surfaces it — Vòng-22
// recert SoT), the detail view MUST render the real date, NOT '—'. Simulating the
// pre-fix payload (key absent) proves the RED branch: the panel renders '—'.
//
// Updated GATE-8 / LL-FE-51: load path is server-driven getCompetency(name) (thay
// store.fetchCompetencies list-filter), nên test mock getCompetency trực tiếp.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import type { UserCompetency } from '@/api/imm06'

const COMP_NAME = 'COMP-2026-00416'

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ loading: ref(false), run: (fn: () => Promise<unknown>) => fn(), lastError: ref(null) }),
}))

// Training Manager so action buttons resolve deterministically (irrelevant to the
// recert panel, but avoids accidental coupling to capability state).
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

// Server-driven load path: getCompetency(name) trả record chi tiết.
let currentRow: UserCompetency | null = null
const getCompetencySpy = vi.fn(async () => {
  if (currentRow === null) throw new Error('not found')
  return currentRow
})
vi.mock('@/api/imm06', () => ({
  getCompetency: (...args: unknown[]) => getCompetencySpy(...(args as [])),
  signoffCompetency: vi.fn(),
  revokeCompetency: vi.fn(),
  recertifyCompetency: vi.fn(),
}))

import CompetencyDetailView from './CompetencyDetailView.vue'

const stubs = { PageHeader: true, StatusBadge: true }

function baseRow(overrides: Partial<UserCompetency>): UserCompetency {
  return {
    name: COMP_NAME,
    user: 'operator@hospital.vn',
    user_full_name: 'Nguyễn Vận Hành',
    device_model: 'IMM-MDL-2026-0453',
    device_model_name: 'Dräger Evita V500',
    training_program: '_TEST-PROG',
    competency_level: 'Operator',
    achieved_date: '2026-01-15',
    expiry_date: '2028-01-15',
    days_until_expiry: 591,
    workflow_state: 'Active',
    recertification_due_date: null,
    department_at_assessment: null,
    last_assessment_score: 85,
    theory_score: 80,
    practical_score: 90,
    supervisor_signoff: 'Administrator',
    signoff_date: '2026-01-16',
    is_expired: 0,
    allowed_transitions: ['Revoke'],
    can_revoke: true,
    ...overrides,
  } as UserCompetency
}

/** Extract the value rendered directly under a given panel label. */
function panelValue(html: string, label: string): string {
  const idx = html.indexOf(label)
  if (idx === -1) return ''
  const after = html.slice(idx + label.length)
  const m = after.match(/<p[^>]*>([\s\S]*?)<\/p>/)
  return m ? m[1].trim() : ''
}

describe('CompetencyDetailView — Hạn tái chứng nhận (read-path field contract)', () => {
  beforeEach(() => {
    currentRow = null
    getCompetencySpy.mockClear()
  })

  it('GREEN: record carrying recertification_due_date → panel renders the date (not "—")', async () => {
    currentRow = baseRow({ recertification_due_date: '2027-11-16' })
    const wrapper = mount(CompetencyDetailView, {
      props: { name: COMP_NAME },
      global: { stubs },
    })
    await flushPromises()

    expect(getCompetencySpy).toHaveBeenCalledWith(COMP_NAME)
    // The recert date must reach the DOM verbatim.
    expect(wrapper.html()).toContain('2027-11-16')
    expect(panelValue(wrapper.html(), 'Hạn tái chứng nhận')).toBe('2027-11-16')
  })

  it('RED proof: pre-fix payload (recertification_due_date absent) → panel renders "—"', async () => {
    const row = baseRow({}) as unknown as Record<string, unknown>
    delete row.recertification_due_date
    currentRow = row as unknown as UserCompetency
    const wrapper = mount(CompetencyDetailView, {
      props: { name: COMP_NAME },
      global: { stubs },
    })
    await flushPromises()

    expect(panelValue(wrapper.html(), 'Hạn tái chứng nhận')).toBe('—')
  })
})
