// TC-UX2-07 — ui/Badge.vue: 6 tone ⇒ 6 tập class KHÁC NHAU, chỉ dùng token ngữ nghĩa.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Badge from '@/components/ui/Badge.vue'

const TONES = ['neutral', 'success', 'warning', 'danger', 'info', 'brand'] as const

describe('ui/Badge (TC-UX2-07)', () => {
  it('TC-UX2-07a: 6 tone cho 6 tập class khác nhau (Set size === 6)', () => {
    const signatures = TONES.map((tone) => {
      const w = mount(Badge, { props: { tone }, slots: { default: 'x' } })
      // chỉ lấy phần class phụ thuộc tone (bg-*/text-*), bỏ class cấu trúc chung
      return w
        .classes()
        .filter((c) => /^(bg|text)-[a-z]+-\d{2,3}$/.test(c))
        .sort()
        .join(' ')
    })
    expect(new Set(signatures).size).toBe(6)
    expect(signatures.every((s) => s.length > 0)).toBe(true)
  })

  it('TC-UX2-07b: nội dung slot render nguyên văn', () => {
    const w = mount(Badge, { props: { tone: 'success' }, slots: { default: 'Đã hoàn tất' } })
    expect(w.text()).toBe('Đã hoàn tất')
    expect(w.attributes('data-testid')).toBe('ui-badge')
  })

  it('TC-UX2-07c: mặc định tone=neutral, size=sm', () => {
    const def = mount(Badge, { slots: { default: 'x' } })
    const neutral = mount(Badge, { props: { tone: 'neutral', size: 'sm' }, slots: { default: 'x' } })
    expect(def.classes().sort()).toEqual(neutral.classes().sort())
  })

  it('TC-UX2-07d: 3 bậc kích thước khớp StatusBadge.vue (không lệch 2 nguồn)', () => {
    const map = {
      xs: 'px-1.5 py-0.5 text-[10px]',
      sm: 'px-2.5 py-0.5 text-[11px]',
      md: 'px-3 py-1 text-xs',
    } as const
    for (const [size, cls] of Object.entries(map)) {
      const w = mount(Badge, { props: { size: size as keyof typeof map }, slots: { default: 'x' } })
      for (const token of cls.split(' ')) {
        expect(w.classes(), `size=${size}`).toContain(token)
      }
    }
  })
})
