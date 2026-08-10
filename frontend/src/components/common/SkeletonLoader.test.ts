// TC-UX2-15/16 (AC-UX-036) — Adoption LIVE: SkeletonLoader render QUA ui/Skeleton.
//
// Vì sao cần: primitive không được dùng ở đâu = shelf-ware. SkeletonLoader là điểm áp
// dụng an toàn duy nhất của vòng này — 49 view tiêu thụ nó, nên nó vừa chứng minh
// primitive chạy thật, vừa không buộc sửa một dòng nào trong view.
//
// BẤT BIẾN KHÔNG-ĐỔI-GIAO-DIỆN: số khối `.skeleton` mỗi biến thể phải GIỮ NGUYÊN so với
// mã trước khi thay (đếm từ SkeletonLoader.vue: kpi-cards 4×4, table rows×6, form 6×2+3,
// card 2+rows, list rows×4). Lệch số ⇒ giao diện đã đổi ⇒ chặn ngay tại đây.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SkeletonLoader from './SkeletonLoader.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const VARIANTS = ['table', 'kpi-cards', 'form', 'card', 'list'] as const

/** rows mặc định = 5 (KHÔNG đổi API công khai của SkeletonLoader). */
const EXPECTED_BLOCKS: Record<(typeof VARIANTS)[number], number> = {
  'table': 30, // 5 dòng × 6 khối
  'kpi-cards': 16, // 4 thẻ × 4 khối
  'form': 15, // 6 nhóm × 2 + 3 khối lẻ
  'card': 7, // 2 khối đầu + 5 dòng
  'list': 20, // 5 dòng × 4 khối
}

describe('SkeletonLoader ⇄ ui/Skeleton (TC-UX2-15, TC-UX2-16)', () => {
  it.each(VARIANTS)('TC-UX2-15: variant=%s render qua ui/Skeleton (không còn div rời)', (variant) => {
    const w = mount(SkeletonLoader, { props: { variant } })
    expect(w.findAllComponents(Skeleton).length).toBeGreaterThan(0)
  })

  it('TC-UX2-16: variant=table, rows=5 ⇒ ĐÚNG 30 khối .skeleton (0 đổi giao diện)', () => {
    const w = mount(SkeletonLoader, { props: { variant: 'table', rows: 5 } })
    expect(w.findAll('.skeleton')).toHaveLength(30)
  })

  it('TC-UX2-16b: 4 biến thể còn lại giữ nguyên số khối đếm từ mã cũ', () => {
    for (const variant of VARIANTS) {
      const w = mount(SkeletonLoader, { props: { variant } })
      expect(w.findAll('.skeleton').length, `variant=${variant}`).toBe(EXPECTED_BLOCKS[variant])
    }
  })

  it('TC-UX2-16c: API công khai không đổi — rows điều khiển số dòng như cũ', () => {
    const w = mount(SkeletonLoader, { props: { variant: 'table', rows: 3 } })
    expect(w.findAll('.skeleton')).toHaveLength(18) // 3 × 6
    // wrapper giữ nguyên tín hiệu trạng thái cho trình đọc màn hình
    // (template có comment ở cấp cao nhất ⇒ nhiều root, phải tìm theo selector)
    expect(w.find('[aria-busy="true"]').exists()).toBe(true)
  })
})
