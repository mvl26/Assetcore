// TC-FE-06-DASH-01 / TC-FE-06-DASH-02 — TrainingDashboardView (IMM-06).
//
// BR-06-14: tile năng lực 'Sắp/Đã hết hạn' bind VERBATIM kpis.competencies
// .expiring/.expired qua competencyExpiryTiles(stats). View KHÔNG tự đếm lại.
//   DASH-01: mount với stats giả (expiring=4, expired=1) → DOM render đúng 4 và 1
//            trên đúng tile; KHÔNG render .active(50) lên tile 'Sắp hết hạn'.
//   DASH-02: click tile 'Sắp hết hạn' → router.push tới CompetencyList với query
//            filter cửa sổ hết hạn (assert đối số push).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import type { Imm06DashboardStats } from '@/api/imm06'

function makeStats(expiring: number, expired: number): Imm06DashboardStats {
  return {
    sessions: { total: 12, planned: 3, confirmed: 2, in_progress: 1, completed: 5, cancelled: 1 },
    competencies: { total: 99, pending: 7, active: 50, expiring, expired, revoked: 2 },
    programs: { total: 8, active: 6 },
  }
}

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    loading: { value: false },
    run: (fn: () => Promise<unknown>) => fn(),
  }),
}))

// Store: real refs so the real pinia storeToRefs unwraps them in the template.
const dashboardStatsRef = ref<Imm06DashboardStats | null>(null)
const loadingRef = ref(false)
const errorRef = ref<string | null>(null)
const fetchStatsSpy = vi.fn(async () => { /* dashboardStatsRef set per-test */ })
vi.mock('@/stores/imm06', () => ({
  useImm06Store: () => ({
    dashboardStats: dashboardStatsRef,
    loading: loadingRef,
    error: errorRef,
    fetchDashboardStats: fetchStatsSpy,
  }),
}))

import TrainingDashboardView from '@/views/training/TrainingDashboardView.vue'

const stubs = { PageHeader: true, SkeletonLoader: true }
const EN_LEAK = /\b(Expiring|Expired|Active|Revoked|Suspended|Pending)\b/

async function mountWith(stats: Imm06DashboardStats) {
  dashboardStatsRef.value = stats
  loadingRef.value = false
  errorRef.value = null
  const wrapper = mount(TrainingDashboardView, { global: { stubs } })
  await flushPromises()
  return wrapper
}

describe('TC-FE-06-DASH-01 — tile render VERBATIM expiring/expired', () => {
  beforeEach(() => { dashboardStatsRef.value = null; fetchStatsSpy.mockClear(); pushSpy.mockClear() })

  it('expiring=4, expired=1 → DOM render đúng 4 và 1 trên đúng tile', async () => {
    const wrapper = await mountWith(makeStats(4, 1))
    expect(fetchStatsSpy).toHaveBeenCalled()

    const expiringTile = wrapper.find('[data-tile="expiring"]')
    const expiredTile = wrapper.find('[data-tile="expired"]')
    expect(expiringTile.exists()).toBe(true)
    expect(expiredTile.exists()).toBe(true)

    // VERBATIM: tile 'Sắp hết hạn' = expiring (4); tile 'Đã hết hạn' = expired (1).
    expect(expiringTile.find('[data-tile-value="expiring"]').text()).toBe('4')
    expect(expiredTile.find('[data-tile-value="expired"]').text()).toBe('1')

    // Nhãn VI đúng, không leak EN.
    expect(expiringTile.text()).toContain('Sắp hết hạn')
    expect(expiredTile.text()).toContain('Đã hết hạn')
  })

  it('chống wire nhầm: KHÔNG render .active(50) lên tile "Sắp hết hạn"', async () => {
    const wrapper = await mountWith(makeStats(4, 1))
    const expiringTile = wrapper.find('[data-tile="expiring"]')
    // active=50 KHÔNG được lọt vào value của tile expiring.
    expect(expiringTile.find('[data-tile-value="expiring"]').text()).not.toBe('50')
    expect(expiringTile.find('[data-tile-value="expiring"]').text()).toBe('4')
  })

  it('value {0} render được (không nuốt 0)', async () => {
    const wrapper = await mountWith(makeStats(0, 0))
    expect(wrapper.find('[data-tile-value="expiring"]').text()).toBe('0')
    expect(wrapper.find('[data-tile-value="expired"]').text()).toBe('0')
  })

  it('no leak EN trên toàn dashboard', async () => {
    const wrapper = await mountWith(makeStats(4, 1))
    expect(wrapper.text()).not.toMatch(EN_LEAK)
  })

  it('render đủ nhóm tile sessions + competencies + programs theo shape', async () => {
    const wrapper = await mountWith(makeStats(4, 1))
    const txt = wrapper.text()
    // sessions
    expect(txt).toContain('Tổng số buổi')
    expect(txt).toContain('Đang diễn ra')
    // competencies stat (không drill)
    expect(txt).toContain('Tổng hồ sơ năng lực')
    expect(txt).toContain('Đã thu hồi')
    // programs
    expect(txt).toContain('Tổng chương trình')
  })
})

describe('TC-FE-06-DASH-02 — click tile "Sắp hết hạn" → router.push drill', () => {
  beforeEach(() => { dashboardStatsRef.value = null; fetchStatsSpy.mockClear(); pushSpy.mockClear() })

  it('click tile expiring → push tới CompetencyList với query filter cửa sổ hết hạn', async () => {
    const wrapper = await mountWith(makeStats(4, 1))
    await wrapper.find('[data-tile="expiring"]').trigger('click')

    expect(pushSpy).toHaveBeenCalledTimes(1)
    const arg = pushSpy.mock.calls[0][0]
    expect(arg).toEqual({ path: '/imm06/competencies', query: { window: 'expiring' } })
  })

  it('click tile expired → push tới CompetencyList với query đã-hết-hạn', async () => {
    const wrapper = await mountWith(makeStats(4, 1))
    await wrapper.find('[data-tile="expired"]').trigger('click')

    expect(pushSpy).toHaveBeenCalledTimes(1)
    expect(pushSpy.mock.calls[0][0]).toEqual({
      path: '/imm06/competencies', query: { window: 'expired' },
    })
  })
})
