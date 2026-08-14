// Copyright (c) 2026, AssetCore Team
//
// TDD — Core Doc §9.7 (row-level drill cho section ListCard / TimelineCard).
// Mỗi dòng dữ liệu là record thật → click mở detail source (CLAUDE.md §5, §10
// root_record). rowTo(row) trả RouterLocation | null. null → dòng tĩnh.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'
import TimelineCard from '@/components/dashboard/TimelineCard.vue'

const RouterLinkStub = {
  name: 'RouterLink',
  props: ['to'],
  template: '<a class="router-link-stub"><slot /></a>',
}

const mountOpts = { global: { stubs: { RouterLink: RouterLinkStub } } }

describe('ListCard rowTo (R3 §9.7)', () => {
  const cols: ListColumn[] = [
    { key: 'name', label: 'Email', nameKey: 'full_name' },
    { key: 'creation', label: 'Ngày tạo', type: 'date' },
  ]
  const rows = [
    { name: 'u1@x.test', full_name: 'User Một', creation: '2026-06-01' },
    { name: 'u2@x.test', full_name: 'User Hai', creation: '2026-06-02' },
  ]

  it('D-FE-30: rowTo trả target → render RouterLink mỗi dòng với to đúng', () => {
    const w = mount(ListCard, {
      props: {
        title: 'Người dùng', columns: cols, rows,
        rowTo: (r: Record<string, unknown>) => ({ path: `/user-profiles/${r.name}` }),
      },
      ...mountOpts,
    })
    const links = w.findAllComponents(RouterLinkStub)
    expect(links.length).toBe(2)
    expect(links[0].props('to')).toEqual({ path: '/user-profiles/u1@x.test' })
    expect(w.text()).toContain('User Một')
  })

  it('D-FE-31: không có rowTo → KHÔNG render RouterLink (giữ hành vi cũ, tĩnh)', () => {
    const w = mount(ListCard, {
      props: { title: 'Người dùng', columns: cols, rows },
      ...mountOpts,
    })
    expect(w.findComponent(RouterLinkStub).exists()).toBe(false)
  })

  it('D-FE-32: rowTo trả null cho 1 dòng → dòng đó tĩnh, dòng khác link', () => {
    const w = mount(ListCard, {
      props: {
        title: 'Người dùng', columns: cols, rows,
        rowTo: (r: Record<string, unknown>) =>
          r.name === 'u1@x.test' ? { path: '/user-profiles/u1@x.test' } : null,
      },
      ...mountOpts,
    })
    expect(w.findAllComponents(RouterLinkStub).length).toBe(1)
  })
})

describe('TimelineCard rowTo (R2 §9.7 — feed truy về source)', () => {
  const rows = [
    { name: 'INC-001', asset: 'AST-001', asset_name: 'Máy thở A', severity: 'Critical', reported_at: '2026-06-02 10:00' },
    { name: 'INC-002', asset: 'AST-002', asset_name: 'Máy X-quang', severity: 'High', reported_at: '2026-06-01 09:00' },
  ]

  it('D-FE-33: rowTo → mỗi <li> bọc RouterLink tới source record', () => {
    const w = mount(TimelineCard, {
      props: {
        title: 'Hoạt động gần đây', rows,
        rowTo: (r: Record<string, unknown>) =>
          r.asset ? { path: '/incidents/list', query: { asset: String(r.asset) } } : null,
      },
      ...mountOpts,
    })
    const links = w.findAllComponents(RouterLinkStub)
    expect(links.length).toBe(2)
    expect(links[0].props('to')).toEqual({ path: '/incidents/list', query: { asset: 'AST-001' } })
    expect(w.text()).toContain('Máy thở A')
  })

  it('D-FE-34: không rowTo → render <li> tĩnh (back-compat), không link', () => {
    const w = mount(TimelineCard, {
      props: { title: 'Hoạt động gần đây', rows },
      ...mountOpts,
    })
    expect(w.findComponent(RouterLinkStub).exists()).toBe(false)
  })

  it('D-FE-35: row không có asset (root_record trống) → rowTo null → tĩnh, không bịa link', () => {
    const w = mount(TimelineCard, {
      props: {
        title: 'Hoạt động gần đây',
        rows: [{ name: 'SYS-1', title: 'Sự kiện hệ thống', modified: '2026-06-02 08:00' }],
        rowTo: (r: Record<string, unknown>) =>
          r.asset ? { path: '/incidents/list', query: { asset: String(r.asset) } } : null,
      },
      ...mountOpts,
    })
    expect(w.findComponent(RouterLinkStub).exists()).toBe(false)
    expect(w.text()).toContain('Sự kiện hệ thống')
  })
})
