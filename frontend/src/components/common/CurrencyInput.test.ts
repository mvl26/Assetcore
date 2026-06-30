// TDD — CurrencyInput component contract (GATE-6c: emitted value == UI value).
// Hiển thị nhóm hàng nghìn kiểu VN; v-model emit number SẠCH (KHÔNG chuỗi) để
// form submit thẳng cho BE. Mount thật (jsdom + @vue/test-utils).
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CurrencyInput from './CurrencyInput.vue'

describe('CurrencyInput', () => {
  it('hiển thị modelValue với dấu phân nhóm hàng nghìn', () => {
    const wrapper = mount(CurrencyInput, { props: { modelValue: 1234567 } })
    expect(wrapper.get('input').element.value).toBe('1.234.567')
  })

  it('gõ số → emit update:modelValue là NUMBER sạch + hiển thị đã nhóm', async () => {
    const wrapper = mount(CurrencyInput, { props: { modelValue: null } })
    const input = wrapper.get('input')
    await input.setValue('2000000000')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted!.at(-1)).toEqual([2000000000])          // number, không phải "2.000.000.000"
    expect(typeof emitted!.at(-1)![0]).toBe('number')
    expect(input.element.value).toBe('2.000.000.000')
  })

  it('xoá hết → emit null (ô trống)', async () => {
    const wrapper = mount(CurrencyInput, { props: { modelValue: 5000 } })
    const input = wrapper.get('input')
    await input.setValue('')
    expect(wrapper.emitted('update:modelValue')!.at(-1)).toEqual([null])
  })

  it('modelValue đổi từ ngoài (reset form) → input reflect lại', async () => {
    const wrapper = mount(CurrencyInput, { props: { modelValue: 1000 } })
    await wrapper.setProps({ modelValue: 7500000 })
    expect(wrapper.get('input').element.value).toBe('7.500.000')
  })

  it('input là type=text inputmode=numeric (bàn phím số mobile, cho phép dấu chấm)', () => {
    const wrapper = mount(CurrencyInput, { props: { modelValue: 0 } })
    const el = wrapper.get('input').element
    expect(el.getAttribute('type')).toBe('text')
    expect(el.getAttribute('inputmode')).toBe('numeric')
  })
})
