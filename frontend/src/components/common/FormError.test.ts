// L-10 (audit BaoCao_RaSoat_17062026) — shared form error banner.
// Pin: render message khi có lỗi (role=alert, class chuẩn .alert-error);
// rỗng/null/absent → KHÔNG render (không chiếm chỗ, không banner trống).
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FormError from './FormError.vue'

describe('FormError — L-10 shared error banner', () => {
  it('hiển thị message + role=alert + class .alert-error chuẩn', () => {
    const w = mount(FormError, { props: { message: 'Email không hợp lệ' } })
    expect(w.text()).toContain('Email không hợp lệ')
    expect(w.find('[role="alert"]').exists()).toBe(true)
    expect(w.find('.alert-error').exists()).toBe(true)
  })

  it('message rỗng / null / absent → KHÔNG render', () => {
    expect(mount(FormError, { props: { message: '' } }).find('[role="alert"]').exists()).toBe(false)
    expect(mount(FormError, { props: { message: null } }).find('[role="alert"]').exists()).toBe(false)
    expect(mount(FormError, { props: {} }).find('[role="alert"]').exists()).toBe(false)
  })
})
