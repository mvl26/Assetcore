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

// ═══════════════════════════════════════════════════════════════════════════════
// AC-UX-067 (docs/ui-ux/07 §3) — DELTA CHỈ-THÊM: trường tuỳ chọn `badge`.
//
// Vì sao mở rộng chứ không để màn tự vẽ: `/commissioning/:id` cần một con số ngay
// trong nút tab («Không phù hợp» × N). Trước vòng này đó chính là LÝ DO màn ấy giữ
// một thanh tab tự chế — một nhu cầu hiển thị nhỏ đã đẻ ra cả một bản fork không có
// `role="tablist"`, không `aria-selected`, không cuộn ngang được trên mobile.
//
// 3 describe PHÍA TRÊN không được sửa một ký tự nào: nếu phải sửa thì delta đã KHÔNG
// còn là CHỈ-THÊM (ADR-UX-19).
// ═══════════════════════════════════════════════════════════════════════════════
const TABS_BADGE = [
  { key: 'detail', label: 'Chi tiết phiếu' },
  { key: 'nc', label: 'Không phù hợp', badge: 3 },
  { key: 'timeline', label: 'Lịch sử' },
]

describe('TC-CONNTAB-05 — badge render BÊN TRONG nút tab', () => {
  it('badge: 3 ⇒ đúng 1 phần tử [data-testid="tab-badge-nc"] chứa «3»', () => {
    const w = mount(DetailTabBar, { props: { tabs: TABS_BADGE, modelValue: 'detail' } })
    const badges = w.findAll('[data-testid="tab-badge-nc"]')
    expect(badges).toHaveLength(1)
    expect(badges[0].text()).toBe('3')
  })

  it('phần tử badge NẰM TRONG button[role=tab] của đúng tab đó (B1)', () => {
    const w = mount(DetailTabBar, { props: { tabs: TABS_BADGE, modelValue: 'detail' } })
    const btn = w.find('[data-testid="tab-nc"]')
    expect(btn.exists()).toBe(true)
    // Tìm badge TỪ TRONG nút — nằm ngoài nút thì find() này rỗng.
    expect(btn.find('[data-testid="tab-badge-nc"]').exists()).toBe(true)
    // Tên khả truy cập gộp nhãn + số (cố ý KHÔNG aria-hidden: con số là thông tin).
    expect(btn.text().replace(/\s+/g, ' ')).toBe('Không phù hợp 3')
  })

  it('badge dạng chuỗi cũng render (vd "12+")', () => {
    const w = mount(DetailTabBar, {
      props: { tabs: [{ key: 'nc', label: 'Không phù hợp', badge: '12+' }], modelValue: 'nc' },
    })
    expect(w.find('[data-testid="tab-badge-nc"]').text()).toBe('12+')
  })
})

describe('TC-CONNTAB-06 — badge RỖNG ⇒ KHÔNG có phần tử trong DOM (B4)', () => {
  // 5 ca: 0 (số) · '0' (chuỗi — bẫy truthy) · '' · undefined tường minh · thiếu hẳn trường.
  const EMPTY_CASES: { name: string; badge?: string | number }[] = [
    { name: 'badge: 0 (số)', badge: 0 },
    { name: "badge: '0' (chuỗi — v-if=\"tab.badge\" SAI ở ca này)", badge: '0' },
    { name: "badge: '' (chuỗi rỗng)", badge: '' },
    { name: 'badge: undefined tường minh', badge: undefined },
    { name: 'thiếu hẳn trường badge' },
  ]

  for (const c of EMPTY_CASES) {
    it(`${c.name} ⇒ 0 phần tử badge (không phải display:none)`, () => {
      const tab: Record<string, unknown> = { key: 'nc', label: 'Không phù hợp' }
      if ('badge' in c) tab.badge = c.badge
      const w = mount(DetailTabBar, {
        props: { tabs: [tab as { key: string; label: string }], modelValue: 'nc' },
      })
      expect(w.findAll('[data-testid="tab-badge-nc"]')).toHaveLength(0)
      // Nhãn vẫn nguyên vẹn — badge biến mất KHÔNG được kéo theo chữ nào.
      expect(w.find('[data-testid="tab-nc"]').text().trim()).toBe('Không phù hợp')
    })
  }
})

describe('TC-CONNTAB-07 — badge KHÔNG đụng hợp đồng cũ', () => {
  it('số tab-stop không đổi: [role=tab] vẫn = số tab, mọi nút vẫn type="button"', () => {
    const w = mount(DetailTabBar, { props: { tabs: TABS_BADGE, modelValue: 'detail' } })
    const tabs = w.findAll('[role="tab"]')
    expect(tabs).toHaveLength(3)
    for (const t of tabs) expect(t.attributes('type')).toBe('button')
  })

  it('aria-selected vẫn đúng 2 chiều khi có badge', () => {
    const w = mount(DetailTabBar, { props: { tabs: TABS_BADGE, modelValue: 'nc' } })
    expect(w.find('[data-testid="tab-nc"]').attributes('aria-selected')).toBe('true')
    expect(w.find('[data-testid="tab-detail"]').attributes('aria-selected')).toBe('false')
  })

  it('bấm tab CÓ badge vẫn chỉ emit 1 lần với đúng key (badge không nuốt sự kiện)', async () => {
    const w = mount(DetailTabBar, { props: { tabs: TABS_BADGE, modelValue: 'detail' } })
    await w.find('[data-testid="tab-badge-nc"]').trigger('click')
    const emitted = w.emitted('update:modelValue')
    expect(emitted).toHaveLength(1)
    expect(emitted?.[0]).toEqual(['nc'])
  })
})

describe('TC-CONNTAB-08 — badge giữ hợp đồng cuộn ngang mobile (TC-RWD-07)', () => {
  it('container vẫn overflow-x-auto, nút có badge vẫn shrink-0 ∧ whitespace-nowrap', () => {
    const w = mount(DetailTabBar, { props: { tabs: TABS_BADGE, modelValue: 'detail' } })
    expect(w.find('[role="tablist"]').classes().join(' ')).toContain('overflow-x-auto')
    const cls = w.find('[data-testid="tab-nc"]').classes().join(' ')
    expect(cls).toContain('shrink-0')
    expect(cls).toContain('whitespace-nowrap')
  })
})

describe('TC-CONNTAB-09 — badge KHÔNG đẻ tab-stop lồng nhau (B2)', () => {
  it('trong nút tab không có <button>/<a>/[tabindex] lồng nhau', () => {
    const w = mount(DetailTabBar, { props: { tabs: TABS_BADGE, modelValue: 'detail' } })
    const btn = w.find('[data-testid="tab-nc"]')
    expect(btn.findAll('button')).toHaveLength(0)
    expect(btn.findAll('a')).toHaveLength(0)
    expect(btn.findAll('[tabindex]')).toHaveLength(0)
  })
})
