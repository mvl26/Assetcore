// TC-UX2-04/05/06 — ui/Button.vue: wrap class @layer .btn-*, không fork CSS.
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import Button from '@/components/ui/Button.vue'

afterEach(() => vi.restoreAllMocks())

describe('ui/Button (TC-UX2-04..06)', () => {
  it('TC-UX2-04: render nhãn slot, type mặc định "button", variant=primary → .btn-primary', () => {
    const w = mount(Button, { props: { variant: 'primary' }, slots: { default: 'Tạo phiếu' } })
    expect(w.text()).toBe('Tạo phiếu')
    expect(w.attributes('type')).toBe('button')
    expect(w.classes()).toContain('btn-primary')
    expect(w.attributes('data-testid')).toBe('ui-button')
  })

  it('TC-UX2-04b: 5 variant ánh xạ đúng class @layer (map tĩnh, không nội suy chuỗi)', () => {
    const expected = {
      primary: 'btn-primary',
      secondary: 'btn-secondary',
      danger: 'btn-danger',
      success: 'btn-success',
      ghost: 'btn-ghost',
    } as const
    for (const [variant, cls] of Object.entries(expected)) {
      const w = mount(Button, { props: { variant: variant as keyof typeof expected }, slots: { default: 'x' } })
      expect(w.classes(), `variant=${variant}`).toContain(cls)
    }
    // Mặc định = secondary (nút phụ an toàn hơn nút nhấn mạnh).
    expect(mount(Button, { slots: { default: 'x' } }).classes()).toContain('btn-secondary')
  })

  it('TC-UX2-05a: disabled ⇒ thuộc tính disabled + aria-disabled="true" + click KHÔNG emit', async () => {
    const w = mount(Button, { props: { disabled: true }, slots: { default: 'Gửi duyệt' } })
    expect(w.attributes('disabled')).toBeDefined()
    expect(w.attributes('aria-disabled')).toBe('true')
    await w.trigger('click')
    expect(w.emitted('click')).toBeUndefined()
  })

  it('TC-UX2-05b: loading ⇒ aria-busy="true" + vẫn chặn click', async () => {
    const w = mount(Button, { props: { loading: true }, slots: { default: 'Đang gửi' } })
    expect(w.attributes('aria-busy')).toBe('true')
    expect(w.attributes('disabled')).toBeDefined()
    await w.trigger('click')
    expect(w.emitted('click')).toBeUndefined()
    // Trạng thái bình thường: click phát ra event.
    const ok = mount(Button, { slots: { default: 'Lưu lại' } })
    expect(ok.attributes('aria-busy')).toBeUndefined()
    await ok.trigger('click')
    expect(ok.emitted('click')).toHaveLength(1)
  })

  it('TC-UX2-06a: iconOnly + ariaLabel ⇒ render aria-label, KHÔNG cảnh báo', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const w = mount(Button, { props: { iconOnly: true, ariaLabel: 'Sửa phiếu bảo trì' } })
    expect(w.attributes('aria-label')).toBe('Sửa phiếu bảo trì')
    expect(warn).not.toHaveBeenCalled()
  })

  it('TC-UX2-06b: iconOnly THIẾU ariaLabel ⇒ console.warn đúng 1 lần (khoá nợ a11y tại gốc)', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    mount(Button, { props: { iconOnly: true } })
    expect(warn).toHaveBeenCalledTimes(1)
    expect(String(warn.mock.calls[0][0])).toContain('ariaLabel')
  })
})
