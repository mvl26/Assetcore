// TC-UX2-08 — ui/Card.vue: có tiêu đề ⇒ <section aria-labelledby> trỏ id CÓ THẬT trong DOM.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Card from './Card.vue'

describe('ui/Card (TC-UX2-08)', () => {
  it('TC-UX2-08a: slot title ⇒ <section> mang aria-labelledby trỏ id có thật', () => {
    const w = mount(Card, { slots: { title: 'Thông tin thiết bị', default: '<p>nội dung</p>' } })
    expect(w.element.tagName).toBe('SECTION')
    const id = w.attributes('aria-labelledby')
    expect(id).toBeTruthy()
    expect(w.find(`#${id}`).exists()).toBe(true)
    expect(w.find(`#${id}`).text()).toBe('Thông tin thiết bị')
  })

  it('TC-UX2-08b: prop title ⇒ cũng sinh aria-labelledby hợp lệ', () => {
    const w = mount(Card, { props: { title: 'Lịch bảo trì' } })
    const id = w.attributes('aria-labelledby')
    expect(id).toBeTruthy()
    expect(w.find(`#${id}`).text()).toBe('Lịch bảo trì')
  })

  it('TC-UX2-08c: không title ⇒ KHÔNG sinh aria-labelledby rỗng', () => {
    const w = mount(Card, { slots: { default: '<p>chỉ có nội dung</p>' } })
    expect(w.attributes('aria-labelledby')).toBeUndefined()
    expect(w.find('h3').exists()).toBe(false)
    expect(w.attributes('data-testid')).toBe('ui-card')
  })

  it('TC-UX2-08d: padding map đúng class @layer (.card / .card-sm), interactive ⇒ .card-interactive', () => {
    expect(mount(Card).classes()).toContain('card')
    expect(mount(Card, { props: { padding: 'sm' } }).classes()).toContain('card-sm')
    expect(mount(Card, { props: { interactive: true } }).classes()).toContain('card-interactive')
  })

  it('TC-UX2-08e: slot actions render cạnh tiêu đề; slot title thắng prop title', () => {
    const w = mount(Card, {
      props: { title: 'Từ prop' },
      slots: { title: 'Từ slot', actions: '<button>Sửa lại</button>' },
    })
    expect(w.text()).toContain('Từ slot')
    expect(w.text()).not.toContain('Từ prop')
    expect(w.find('button').text()).toBe('Sửa lại')
  })
})
