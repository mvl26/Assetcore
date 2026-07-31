// Copyright (c) 2026, AssetCore Team
// TDD — TC-CONNTAB-01..03 (AC-CR-87 vòng 3): thanh tab dùng chung cho MỌI màn chi tiết.
//
// Vì sao có component này: khối «Bản ghi liên quan» trước đây nối đuôi nội dung chính ở
// 5 màn chi tiết ⇒ luôn gọi `get_connections` lúc tải trang dù người dùng không nhìn tới.
// Đưa vào TAB RIÊNG cần MỘT thanh tab duy nhất — nếu mỗi màn tự vẽ, hợp đồng a11y và
// hợp đồng cuộn ngang mobile (TC-RWD-07) sẽ trôi mỗi nơi một kiểu.
//
// Ba lời hứa khoá ở đây:
//   1. A11y (WCAG 2.1 AA): role="tablist" + role="tab" + aria-selected đúng tab đang chọn,
//      mọi nút `type="button"` (không submit nhầm form bọc ngoài);
//   2. CONTROLLED: bấm chỉ EMIT, KHÔNG tự đổi state — cha là nguồn sự thật duy nhất
//      (nếu component tự nhớ, tab sẽ "đi lạc" khi cha khoá tab theo điều kiện);
//   3. Hợp đồng cuộn ngang mobile: container overflow-x-auto + nút shrink-0/whitespace-nowrap.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DetailTabBar from './DetailTabBar.vue'

const TABS = [
  { key: 'detail', label: 'Chi tiết' },
  { key: 'related', label: 'Bản ghi liên quan' },
]

function mountBar(modelValue = 'detail') {
  return mount(DetailTabBar, { props: { tabs: TABS, modelValue } })
}

describe('TC-CONNTAB-01 — a11y thanh tab (role/aria/type)', () => {
  it('render 1 tablist + đúng số tab, nhãn tiếng Việt đúng thứ tự', () => {
    const w = mountBar()
    expect(w.findAll('[role="tablist"]')).toHaveLength(1)
    const tabs = w.findAll('[role="tab"]')
    expect(tabs).toHaveLength(2)
    expect(tabs.map((t) => t.text())).toEqual(['Chi tiết', 'Bản ghi liên quan'])
  })

  it('aria-selected đúng tab đang chọn (tab kia PHẢI "false", không phải vắng mặt)', () => {
    const w = mountBar('detail')
    const tabs = w.findAll('[role="tab"]')
    expect(tabs[0].attributes('aria-selected')).toBe('true')
    expect(tabs[1].attributes('aria-selected')).toBe('false')

    const w2 = mountBar('related')
    const tabs2 = w2.findAll('[role="tab"]')
    expect(tabs2[0].attributes('aria-selected')).toBe('false')
    expect(tabs2[1].attributes('aria-selected')).toBe('true')
  })

  it('mọi nút có type="button" + data-testid theo key', () => {
    const w = mountBar()
    for (const b of w.findAll('[role="tab"]')) expect(b.attributes('type')).toBe('button')
    expect(w.find('[data-testid="tab-detail"]').exists()).toBe(true)
    expect(w.find('[data-testid="tab-related"]').exists()).toBe(true)
  })
})

describe('TC-CONNTAB-02 — controlled: bấm chỉ emit, không tự đổi state', () => {
  it('bấm tab thứ 2 ⇒ emit update:modelValue ĐÚNG 1 lần với payload "related"', async () => {
    const w = mountBar('detail')
    await w.find('[data-testid="tab-related"]').trigger('click')

    const emitted = w.emitted('update:modelValue')
    expect(emitted).toHaveLength(1)
    expect(emitted?.[0]).toEqual(['related'])
  })

  it('prop KHÔNG đổi ⇒ aria-selected GIỮ NGUYÊN (component không tự nhớ tab)', async () => {
    const w = mountBar('detail')
    await w.find('[data-testid="tab-related"]').trigger('click')
    const tabs = w.findAll('[role="tab"]')
    expect(tabs[0].attributes('aria-selected')).toBe('true')
    expect(tabs[1].attributes('aria-selected')).toBe('false')
  })

  it('cha đổi prop ⇒ tab đang chọn đi theo cha', async () => {
    const w = mountBar('detail')
    await w.setProps({ modelValue: 'related' })
    const tabs = w.findAll('[role="tab"]')
    expect(tabs[1].attributes('aria-selected')).toBe('true')
  })
})

describe('TC-CONNTAB-03 — hợp đồng cuộn ngang mobile (giữ TC-RWD-07)', () => {
  it('container có overflow-x-auto', () => {
    expect(mountBar().find('[role="tablist"]').classes().join(' ')).toContain('overflow-x-auto')
  })

  it('mỗi nút có shrink-0 ∧ whitespace-nowrap (không co, không xuống dòng)', () => {
    for (const b of mountBar().findAll('[role="tab"]')) {
      const cls = b.classes().join(' ')
      expect(cls).toContain('shrink-0')
      expect(cls).toContain('whitespace-nowrap')
    }
  })
})
