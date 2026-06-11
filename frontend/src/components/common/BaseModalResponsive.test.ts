// TDD — TC-RWD-08 (D3): BaseModal full-screen mobile, centered sm:+, close ≥44px (P5).
// API-shape regression: prop size/danger/title + slot footer + emit close KHÔNG đổi.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseModal from './BaseModal.vue'

function mountModal(props: Record<string, unknown> = {}, slots: Record<string, string> = {}) {
  return mount(BaseModal, {
    props: { title: 'Tiêu đề', ...props },
    slots: { default: '<p>nội dung</p>', ...slots },
    // BaseModal dùng <Teleport to="body"> → stub Teleport để nội dung ở lại wrapper.
    global: { stubs: { teleport: true } },
  })
}

describe('TC-RWD-08 — BaseModal responsive (D3)', () => {
  it('card container full-screen mobile (inset-0 w-full h-full rounded-none)', () => {
    const w = mountModal()
    const card = w.find('[data-testid="modal-card"]')
    expect(card.exists()).toBe(true)
    const cls = card.attributes('class') || ''
    expect(cls).toContain('inset-0')
    expect(cls).toContain('w-full')
    expect(cls).toContain('h-full')
    expect(cls).toContain('rounded-none')
  })

  it('card container centered + rounded ở sm:+ (sm:rounded-2xl sm:h-auto sm:max-w-*)', () => {
    const w = mountModal({ size: 'lg' })
    const cls = w.find('[data-testid="modal-card"]').attributes('class') || ''
    expect(cls).toContain('sm:rounded-2xl')
    expect(cls).toContain('sm:h-auto')
    expect(cls).toContain('sm:inset-auto')
    expect(cls).toContain('sm:max-w-lg')
  })

  it('nút đóng ≥44px touch target (P5)', () => {
    const w = mountModal()
    const closeBtn = w.find('[data-testid="modal-close"]')
    expect(closeBtn.exists()).toBe(true)
    const cls = closeBtn.attributes('class') || ''
    const has44 =
      (cls.includes('min-h-[44px]') && cls.includes('min-w-[44px]')) ||
      (cls.includes('h-11') && cls.includes('w-11'))
    expect(has44).toBe(true)
  })

  it('API-shape regression: emit close + render title + slot footer', async () => {
    const w = mountModal({ danger: true }, { footer: '<button>OK</button>' })
    expect(w.text()).toContain('Tiêu đề')
    expect(w.text()).toContain('OK')
    await w.find('[data-testid="modal-close"]').trigger('click')
    expect(w.emitted('close')).toBeTruthy()
  })
})
