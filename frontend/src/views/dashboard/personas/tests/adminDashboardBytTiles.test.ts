// TDD — BR-00-17 (NĐ98): 2 tile "ĐK Bộ Y tế sắp/đã hết hạn" trên dashboard quản trị.
//
// SoT count==drill ở BE (byt_expiry_filter). Test này PIN contract FE: tile render
// nhãn SSoT từ payload BE + click drill → /assets?byt_status=expiring|expired.
// value=0 → tone neutral nhưng VẪN drill được (list rỗng). KHÔNG raw-EN leak.
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { BYT_EXPIRY_LABEL } from '@/constants/labels'
import type { PersonaKpi } from '@/api/dashboard'

import KpiCard from '@/components/dashboard/KpiCard.vue'

beforeEach(() => {
  setActivePinia(createPinia())
})

// Payload mô phỏng BE _build_admin trả 2 tile BYT (drill descriptor canonical).
const TILE_EXPIRING: PersonaKpi = {
  key: 'byt_expiring', label_vi: BYT_EXPIRY_LABEL.expiring, value: 4,
  foot_vi: 'NĐ98 · 30 ngày', tone: 'warn' as const,
  drill: { route: '/assets', query: { byt_status: 'expiring' } },
}
const TILE_EXPIRED: PersonaKpi = {
  key: 'byt_expired', label_vi: BYT_EXPIRY_LABEL.expired, value: 0,
  foot_vi: 'NĐ98', tone: 'info' as const,
  drill: { route: '/assets', query: { byt_status: 'expired' } },
}

function mountCard(kpi: PersonaKpi) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div/>' } }],
  })
  return mount(KpiCard, { props: { kpi }, global: { plugins: [router] } })
}

describe('Admin BYT tiles (BR-00-17, NĐ98)', () => {
  it('tile sắp hết hạn render nhãn SSoT + value từ payload', () => {
    const w = mountCard(TILE_EXPIRING)
    expect(w.text()).toContain(BYT_EXPIRY_LABEL.expiring)
    expect(w.text()).toContain('4')
    // KHÔNG raw-EN leak.
    expect(w.text()).not.toContain('expiring')
    expect(w.text()).not.toContain('byt_status')
  })

  it('click tile sắp hết hạn → RouterLink /assets?byt_status=expiring', () => {
    const w = mountCard(TILE_EXPIRING)
    const link = w.findComponent({ name: 'RouterLink' })
    expect(link.exists()).toBe(true)
    expect(link.props('to')).toEqual({ path: '/assets', query: { byt_status: 'expiring' } })
  })

  it('tile đã hết hạn value=0 → vẫn drill được /assets?byt_status=expired', () => {
    const w = mountCard(TILE_EXPIRED)
    expect(w.text()).toContain(BYT_EXPIRY_LABEL.expired)
    // value=0 hiển thị '0' (không phải '—'), tile vẫn là RouterLink drillable.
    const link = w.findComponent({ name: 'RouterLink' })
    expect(link.exists()).toBe(true)
    expect(link.props('to')).toEqual({ path: '/assets', query: { byt_status: 'expired' } })
  })

  it('không raw-EN leak ở cả 2 tile', () => {
    const w1 = mountCard(TILE_EXPIRING)
    const w2 = mountCard(TILE_EXPIRED)
    expect(w1.text()).not.toMatch(/expir(ing|ed)\b/)
    expect(w2.text()).not.toMatch(/expir(ing|ed)\b/)
  })
})
