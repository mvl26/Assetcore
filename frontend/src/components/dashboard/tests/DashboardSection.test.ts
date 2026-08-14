// Core Doc §9.4.3 — DashboardSection chrome + label consistency.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import DashboardSection from '@/components/dashboard/DashboardSection.vue'
import { translateStatus } from '@/utils/formatters'
import { lifecycleStatusLabel } from '@/constants/labels'

describe('DashboardSection', () => {
  it('render title + hint + accent header + slot', () => {
    const w = mount(DashboardSection, {
      props: { title: 'Tình trạng thiết bị', hint: 'Nhấp để xem' },
      slots: { default: '<p class="body">nội dung</p>' },
    })
    expect(w.text()).toContain('Tình trạng thiết bị')
    expect(w.text()).toContain('Nhấp để xem')
    expect(w.find('.body').exists()).toBe(true)
    // accent bar emerald + card rounded-2xl
    expect(w.html()).toContain('bg-emerald-500')
    expect(w.html()).toContain('rounded-2xl')
  })
})

describe('Status label consistency (donut ↔ list)', () => {
  it('Commissioned: translateStatus khớp lifecycleStatusLabel (không drift)', () => {
    expect(translateStatus('Commissioned')).toBe(lifecycleStatusLabel('Commissioned'))
  })
  it('các lifecycle status chính đồng bộ giữa formatters và labels', () => {
    for (const code of ['Active', 'Under Repair', 'Calibrating', 'Out of Service', 'Decommissioned']) {
      expect(translateStatus(code)).toBe(lifecycleStatusLabel(code))
    }
  })
})
