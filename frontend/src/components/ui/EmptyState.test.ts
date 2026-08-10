// TC-UX2-11 — ui/EmptyState.vue: khung rỗng LUÔN có câu VI đầy đủ + lối thoát.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EmptyState from './EmptyState.vue'

describe('ui/EmptyState (TC-UX2-11)', () => {
  it('TC-UX2-11a: mặc định hiện "Chưa có dữ liệu" + role="status"', () => {
    const w = mount(EmptyState)
    expect(w.text()).toContain('Chưa có dữ liệu')
    expect(w.attributes('role')).toBe('status')
    expect(w.attributes('data-testid')).toBe('ui-empty')
    // câu cụt kiểu '/dashboard' hoặc chuỗi rỗng là lỗi audit §7.2
    expect(w.text().trim().length).toBeGreaterThan(5)
  })

  it('TC-UX2-11b: truyền description + slot action ⇒ cả hai render', () => {
    const w = mount(EmptyState, {
      props: { title: 'Chưa có phiếu bảo trì', description: 'Tạo phiếu đầu tiên để bắt đầu theo dõi.' },
      slots: { action: '<button class="loi-thoat">Tạo phiếu</button>' },
    })
    expect(w.text()).toContain('Chưa có phiếu bảo trì')
    expect(w.text()).toContain('Tạo phiếu đầu tiên để bắt đầu theo dõi.')
    expect(w.find('.loi-thoat').exists()).toBe(true)
  })

  it('TC-UX2-11c: actionLabel ⇒ nút mặc định hiện và phát "action"', async () => {
    const w = mount(EmptyState, { props: { actionLabel: 'Tạo phiếu mới' } })
    const btn = w.find('[data-testid="ui-empty-action"]')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toBe('Tạo phiếu mới')
    await btn.trigger('click')
    expect(w.emitted('action')).toHaveLength(1)
  })

  it('TC-UX2-11d: không description/actionLabel ⇒ 0 nút, 0 dòng mô tả rỗng', () => {
    const w = mount(EmptyState)
    expect(w.find('[data-testid="ui-empty-action"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-empty-description"]').exists()).toBe(false)
  })
})
