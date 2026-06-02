// TDD — Core Doc §9.6 (docs/architecture/FE_Persona_Dashboards.md)
// D-FE-8..10: KpiCard drill RouterLink, StatusDonutChart segment-click emit.
// 2026-06-02: + gate clickable theo quyền route đích (§9.5 #9) — KPI/segment
// drill về route user KHÔNG có quyền → render TĨNH (không link /unauthorized).
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import KpiCard from '@/components/dashboard/KpiCard.vue'
import StatusDonutChart from '@/components/dashboard/StatusDonutChart.vue'
import { useAuthStore } from '@/stores/auth'
import type { PersonaKpi } from '@/api/dashboard'

const RouterLinkStub = {
  name: 'RouterLink',
  props: ['to'],
  template: '<a class="router-link-stub"><slot /></a>',
}

function makeKpi(drill: PersonaKpi['drill']): PersonaKpi {
  return { key: 'active_assets', label_vi: 'Thiết bị đang hoạt động', value: 12, foot_vi: '', tone: 'primary', drill }
}

/** Seed capability set lên auth store (Pinia active). */
function seedCaps(caps: Record<string, boolean>): void {
  const auth = useAuthStore()
  auth.capabilities = caps
}

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('KpiCard drill-down (D-FE-8, D-FE-9)', () => {
  it('D-FE-8: kpi.drill present + có quyền route → render RouterLink với to={path,query}', () => {
    seedCaps({ 'data.read': true }) // /assets = master, không cần cap đặc thù vẫn pass
    const kpi = makeKpi({ route: '/assets', query: { lifecycle_status: 'Active' } })
    const wrapper = mount(KpiCard, {
      props: { kpi },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    const link = wrapper.findComponent(RouterLinkStub)
    expect(link.exists()).toBe(true)
    expect(link.props('to')).toEqual({ path: '/assets', query: { lifecycle_status: 'Active' } })
    expect(wrapper.text()).toContain('Thiết bị đang hoạt động')
  })

  it('D-FE-9: không có drill → render <div> tĩnh, KHÔNG RouterLink', () => {
    seedCaps({})
    const wrapper = mount(KpiCard, {
      props: { kpi: makeKpi(null) },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    expect(wrapper.findComponent(RouterLinkStub).exists()).toBe(false)
    expect(wrapper.find('div').exists()).toBe(true)
  })

  // ─── Bug opsmgr 2026-06-02: drill về route THIẾU QUYỀN ───────────────────
  it('D-FE-9b: có drill nhưng THIẾU quyền route đích → card TĨNH (không link /unauthorized)', () => {
    seedCaps({ 'data.read': true }) // KHÔNG có corrective.read
    const kpi = makeKpi({ route: '/incidents/list', query: { severity: 'Critical' } })
    const wrapper = mount(KpiCard, {
      props: { kpi },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    expect(wrapper.findComponent(RouterLinkStub).exists()).toBe(false)
    expect(wrapper.text()).toContain('Thiết bị đang hoạt động') // vẫn hiển thị KPI
  })

  it('D-FE-9c: có drill VÀ có quyền route đích → render RouterLink', () => {
    seedCaps({ 'corrective.read': true })
    const kpi = makeKpi({ route: '/incidents/list', query: { severity: 'Critical' } })
    const wrapper = mount(KpiCard, {
      props: { kpi },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    expect(wrapper.findComponent(RouterLinkStub).exists()).toBe(true)
  })
})

describe('StatusDonutChart segment-click (D-FE-10)', () => {
  const baseProps = {
    labels: ['Đang hoạt động', 'Đang sửa chữa'],
    series: [10, 3],
    colors: ['#10b981', '#ef4444'],
    codes: ['Active', 'Under Repair'],
  }

  it('D-FE-10: click slice → emit segment-click {label, code, value} với canonical code', async () => {
    seedCaps({ 'data.read': true })
    const wrapper = mount(StatusDonutChart, { props: { ...baseProps, drillRoute: '/assets' } })
    const slices = wrapper.findAll('circle')
    const firstArc = slices[1]
    await firstArc.trigger('click')
    const emitted = wrapper.emitted('segment-click')
    expect(emitted).toBeTruthy()
    expect(emitted?.[0][0]).toEqual({ label: 'Đang hoạt động', code: 'Active', value: 10 })
  })

  it('D-FE-10b: không có codes → KHÔNG emit (không drillable)', async () => {
    seedCaps({ 'data.read': true })
    const wrapper = mount(StatusDonutChart, {
      props: { labels: baseProps.labels, series: baseProps.series, colors: baseProps.colors },
    })
    const slices = wrapper.findAll('circle')
    await slices[1].trigger('click')
    expect(wrapper.emitted('segment-click')).toBeFalsy()
  })

  it('D-FE-10c: drillRoute THIẾU quyền → segment KHÔNG emit (không drill /unauthorized)', async () => {
    seedCaps({ 'data.read': true }) // KHÔNG có corrective.read
    const wrapper = mount(StatusDonutChart, { props: { ...baseProps, drillRoute: '/incidents/list' } })
    const slices = wrapper.findAll('circle')
    await slices[1].trigger('click')
    expect(wrapper.emitted('segment-click')).toBeFalsy()
  })
})
