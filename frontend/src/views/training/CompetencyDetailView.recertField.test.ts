// TC-06-FE-01 (RED-first): training/CompetencyDetailView "Hạn tái chứng nhận" panel.
//
// Locks the read-path contract at the FE boundary: when store.fetchCompetencies
// returns a competency row carrying recertification_due_date (BE field-list now
// surfaces it — Vòng-22 recert SoT), the detail view MUST render the real date,
// NOT '—'. Simulating the pre-fix payload (key absent) proves the RED branch:
// the panel would render '—', which is exactly the bug this guard catches.
//
// ZERO production code change required — UserCompetency type already declares the
// field (api/imm06.ts:84) and the view already binds it (CompetencyDetailView.vue:241).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { UserCompetency } from '@/api/imm06'

const COMP_NAME = 'COMP-2026-00416'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { name: COMP_NAME } }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    loading: { value: false },
    run: (fn: () => Promise<unknown>) => fn(),
  }),
}))

// Training Manager so the action buttons resolve deterministically (irrelevant
// to the recert panel, but avoids accidental coupling to capability state).
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

// Fallback path (getExpiringCompetencies) must never be hit when the store row
// is found — stub it so a regression that bypasses the store is visible.
const getExpiringSpy = vi.fn(async () => [] as UserCompetency[])
vi.mock('@/api/imm06', () => ({
  getExpiringCompetencies: (...args: unknown[]) => getExpiringSpy(...(args as [])),
  signoffCompetency: vi.fn(),
  revokeCompetency: vi.fn(),
  recertifyCompetency: vi.fn(),
}))

// Store: fetchCompetencies populates `competencies`; the view reads it back.
let storeRows: UserCompetency[] = []
const fetchCompetenciesSpy = vi.fn(async () => { /* rows already set per-test */ })
vi.mock('@/stores/imm06', () => ({
  useImm06Store: () => ({
    get competencies() { return storeRows },
    error: null,
    fetchCompetencies: fetchCompetenciesSpy,
  }),
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
    ...overrides,
  } as UserCompetency
}

/** Extract the value rendered directly under a given panel label. */
function panelValue(html: string, label: string): string {
  // Panels render: <p class="...">LABEL</p><p ...>VALUE</p>
  const idx = html.indexOf(label)
  if (idx === -1) return ''
  const after = html.slice(idx + label.length)
  const m = after.match(/<p[^>]*>([\s\S]*?)<\/p>/)
  return m ? m[1].trim() : ''
}

describe('CompetencyDetailView — Hạn tái chứng nhận (read-path field contract)', () => {
  beforeEach(() => {
    storeRows = []
    fetchCompetenciesSpy.mockClear()
    getExpiringSpy.mockClear()
  })

  it('GREEN: store row carrying recertification_due_date → panel renders the date (not "—")', async () => {
    storeRows = [baseRow({ recertification_due_date: '2027-11-16' })]
    const wrapper = mount(CompetencyDetailView, {
      props: { name: COMP_NAME },
      global: { stubs },
    })
    await flushPromises()

    expect(fetchCompetenciesSpy).toHaveBeenCalled()
    // The recert date must reach the DOM verbatim.
    expect(wrapper.html()).toContain('2027-11-16')
    // And specifically under the "Hạn tái chứng nhận" panel, not '—'.
    expect(panelValue(wrapper.html(), 'Hạn tái chứng nhận')).toBe('2027-11-16')
    // Store row was found → fallback API must NOT be consulted.
    expect(getExpiringSpy).not.toHaveBeenCalled()
  })

  it('RED proof: pre-fix payload (recertification_due_date absent) → panel renders "—"', async () => {
    // Simulate the dropped BE field: row with the key missing entirely.
    const row = baseRow({}) as unknown as Record<string, unknown>
    delete row.recertification_due_date
    storeRows = [row as unknown as UserCompetency]
    const wrapper = mount(CompetencyDetailView, {
      props: { name: COMP_NAME },
      global: { stubs },
    })
    await flushPromises()

    expect(panelValue(wrapper.html(), 'Hạn tái chứng nhận')).toBe('—')
  })
})
