// TC-UX2-14 — ui/Skeleton.vue: atom shimmer, kích thước do caller truyền (fallthrough)
// ⇒ thay thế trong SkeletonLoader.vue KHÔNG đổi một pixel.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Skeleton from './Skeleton.vue'

/** Đếm số khối shimmer render thật (findAll của test-utils tính CẢ root nếu root khớp). */
function countBlocks(w: ReturnType<typeof mount>): number {
  return w.findAll('.skeleton').length
}

describe('ui/Skeleton (TC-UX2-14)', () => {
  it('TC-UX2-14a: root mang class .skeleton + aria-busy + aria-hidden cho nội dung giả', () => {
    const w = mount(Skeleton)
    expect(w.classes()).toContain('skeleton')
    expect(w.attributes('aria-busy')).toBe('true')
    expect(w.attributes('aria-hidden')).toBe('true')
    expect(w.attributes('data-testid')).toBe('ui-skeleton')
  })

  it('TC-UX2-14b: class của caller được merge (giữ nguyên kích thước gọi từ ngoài)', () => {
    const w = mount(Skeleton, { attrs: { class: 'h-3.5 w-24 rounded' } })
    expect(w.classes()).toEqual(expect.arrayContaining(['skeleton', 'h-3.5', 'w-24', 'rounded']))
  })

  it('TC-UX2-14c: style của caller được merge + props width/height', () => {
    const w = mount(Skeleton, { attrs: { style: 'width: 70%' } })
    expect(w.attributes('style')).toContain('70%')
    const sized = mount(Skeleton, { props: { width: '120px', height: '14px' } })
    expect(sized.attributes('style')).toContain('120px')
    expect(sized.attributes('style')).toContain('14px')
  })

  it('TC-UX2-14d: lines=3 ⇒ đúng 3 khối, container mang aria-busy, khối con aria-hidden', () => {
    const w = mount(Skeleton, { props: { lines: 3 } })
    expect(w.attributes('aria-busy')).toBe('true')
    const blocks = w.findAll('.skeleton')
    expect(countBlocks(w)).toBe(3)
    for (const b of blocks) expect(b.attributes('aria-hidden')).toBe('true')
  })

  it('TC-UX2-14e: mặc định (lines=1) là ĐÚNG 1 khối — bất biến đếm của SkeletonLoader', () => {
    expect(countBlocks(mount(Skeleton))).toBe(1)
    expect(countBlocks(mount(Skeleton, { props: { lines: 1 } }))).toBe(1)
  })
})
