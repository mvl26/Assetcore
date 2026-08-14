// TDD — hợp đồng hộp thoại SSoT `BaseModal.vue`, đánh số theo spec BA
// (docs/ui-ux/04 §7.2 — TC-UX5-20..29) + TC-UX5-12 (footer responsive).
// File song song `BaseModalA11y.test.ts` đánh số theo đề mục PM (TC-UX5-01..07): hai hệ
// đánh số của CÙNG một vòng, giữ cả hai để lệnh chấm của BA lẫn của PM đều chạy được.
// `BaseModalResponsive.test.ts` (4 TC cũ) là cổng chống-regress — KHÔNG SỬA.
import { describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import BaseModal from '@/components/common/BaseModal.vue'

function mountModal(
  props: Record<string, unknown> = {},
  slots: Record<string, string> = {},
) {
  return mount(BaseModal, {
    props: { title: 'Tiêu đề', ...props },
    slots: { default: '<button id="a">A</button><button id="b">B</button>', ...slots },
    attachTo: document.body, // BẮT BUỘC — không attach thì .focus() vô nghĩa trong jsdom
    global: { stubs: { teleport: true } }, // giữ nội dung trong wrapper để find() thấy
  })
}

beforeEach(() => {
  document.body.innerHTML = ''
})

describe('TC-UX5-20..22 — ngữ nghĩa dialog (A1 · INV-UX5-1/2/3)', () => {
  it('TC-UX5-20 role="dialog" + aria-modal="true" trên modal-card', async () => {
    const w = mountModal()
    await nextTick()
    const card = w.find('[data-testid="modal-card"]')
    expect(card.attributes('role')).toBe('dialog')
    expect(card.attributes('aria-modal')).toBe('true')
    // tabindex=-1 để card nhận được focus khi thân bài trống.
    expect(card.attributes('tabindex')).toBe('-1')
    w.unmount()
  })

  it('TC-UX5-21 aria-labelledby === id của <h2>, và <h2> chứa đúng title', async () => {
    const w = mountModal({ title: 'Xác nhận huỷ phiếu' })
    await nextTick()
    const h2 = w.find('h2')
    expect(w.find('[data-testid="modal-card"]').attributes('aria-labelledby')).toBe(
      h2.attributes('id'),
    )
    expect(h2.text()).toBe('Xác nhận huỷ phiếu')
    w.unmount()
  })

  it('TC-UX5-22 2 modal đồng thời ⇒ id khác nhau (id sinh theo INSTANCE, không theo app)', async () => {
    const w1 = mountModal({ title: 'Hộp thoại một' })
    const w2 = mountModal({ title: 'Hộp thoại hai' })
    await nextTick()
    const id1 = w1.find('h2').attributes('id')!
    const id2 = w2.find('h2').attributes('id')!
    expect(id1).not.toBe(id2)
    expect(id1.startsWith('ac-modal-title-')).toBe(true)
    expect(id2.startsWith('ac-modal-title-')).toBe(true)
    w2.unmount()
    w1.unmount()
  })
})

describe('TC-UX5-23/24 — Escape (A3 · INV-UX5-4)', () => {
  function escape(): boolean {
    const e = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true })
    document.dispatchEvent(e)
    return e.defaultPrevented
  }

  it('TC-UX5-23 Escape ⇒ emitted("close") có ĐÚNG 1 phần tử', async () => {
    const w = mountModal()
    await nextTick()
    expect(escape()).toBe(true)
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
  })

  it('TC-UX5-24 unmount rồi Escape ⇒ tổng emit KHÔNG tăng và phím không bị chặn', async () => {
    const w = mountModal()
    await nextTick()
    escape()
    const emitted = w.emitted('close')!
    w.unmount()
    expect(escape()).toBe(false)
    expect(emitted).toHaveLength(1)
  })

  it('2 modal chồng nhau: Escape chỉ đóng modal TRÊN (ngăn xếp topmost)', async () => {
    const below = mountModal({ title: 'Dưới' })
    await nextTick()
    const above = mountModal({ title: 'Trên' })
    await nextTick()

    escape()
    expect(above.emitted('close')).toHaveLength(1)
    expect(below.emitted('close')).toBeUndefined()

    above.unmount()
    escape()
    expect(below.emitted('close')).toHaveLength(1)
    below.unmount()
  })
})

describe('TC-UX5-25..27 — bẫy focus (A4 · INV-UX5-5/6)', () => {
  it('TC-UX5-25 mở ⇒ card.contains(document.activeElement)', async () => {
    const w = mountModal()
    await nextTick()
    expect(
      (w.find('[data-testid="modal-card"]').element as HTMLElement).contains(document.activeElement),
    ).toBe(true)
    w.unmount()
  })

  it('TC-UX5-26 focus ban đầu KHÔNG rơi vào nút đóng khi thân bài còn phần tử tab được', async () => {
    const w = mountModal()
    await nextTick()
    const closeBtn = w.find('[data-testid="modal-close"]').element
    expect(document.activeElement).not.toBe(closeBtn)
    expect((document.activeElement as HTMLElement).id).toBe('a')
    w.unmount()
  })

  it('TC-UX5-26b thân bài KHÔNG có phần tử tab được ⇒ lùi về nút đóng (không mất focus)', async () => {
    const w = mountModal({}, { default: '<p>chỉ có chữ</p>' })
    await nextTick()
    expect(document.activeElement).toBe(w.find('[data-testid="modal-close"]').element)
    w.unmount()
  })

  it('TC-UX5-26c [data-autofocus] có ưu tiên cao nhất', async () => {
    const w = mountModal({}, { default: '<button id="x">X</button><input id="y" data-autofocus />' })
    await nextTick()
    expect((document.activeElement as HTMLElement).id).toBe('y')
    w.unmount()
  })

  it('TC-UX5-27 Tab ở cuối → đầu; Shift+Tab ở đầu → cuối (dispatch trên modal-card)', async () => {
    const w = mountModal({}, { footer: '<button id="z">Lưu</button>' })
    await nextTick()
    const card = w.find('[data-testid="modal-card"]')
    const el = card.element as HTMLElement
    const items = Array.from(el.querySelectorAll<HTMLElement>('button, input'))
    const first = items[0]
    const last = items[items.length - 1]
    expect(first.getAttribute('data-testid')).toBe('modal-close') // nút đóng là phần tử ĐẦU DOM
    expect(last.id).toBe('z')

    last.focus()
    await card.trigger('keydown', { key: 'Tab' })
    expect(document.activeElement).toBe(first)

    await card.trigger('keydown', { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(last)
    w.unmount()
  })
})

describe('TC-UX5-28/29 — trả focus + hợp đồng cũ (A5 · A7)', () => {
  it('TC-UX5-28 opener được focus lại sau unmount', async () => {
    const opener = document.createElement('button')
    opener.id = 'opener'
    document.body.appendChild(opener)
    opener.focus()

    const w = mountModal()
    await nextTick()
    w.unmount()
    expect(document.activeElement).toBe(opener)
  })

  it('TC-UX5-29 nút modal-close vẫn emit close (hợp đồng cũ không đổi)', async () => {
    const w = mountModal()
    await nextTick()
    await w.find('[data-testid="modal-close"]').trigger('click')
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
  })

  it('TC-UX5-29b click nền (overlay) vẫn emit close', async () => {
    const w = mountModal()
    await nextTick()
    await w.find('.fixed.inset-0').trigger('click')
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
  })
})

describe('TC-UX5-12 — footer responsive (nút chính nằm TRÊN ở ≤768px)', () => {
  it('slot footer có flex-col-reverse + sm:flex-row', async () => {
    const w = mountModal({}, { footer: '<button id="huy">Huỷ</button><button id="luu">Lưu</button>' })
    await nextTick()
    const footer = w.find('[data-testid="modal-footer"]')
    expect(footer.exists()).toBe(true)
    const cls = footer.attributes('class') || ''
    expect(cls).toContain('flex-col-reverse')
    expect(cls).toContain('sm:flex-row')
    expect(cls).toContain('sm:justify-end')
    w.unmount()
  })

  it('không có slot footer ⇒ không render khung footer (hợp đồng cũ)', async () => {
    const w = mountModal()
    await nextTick()
    expect(w.find('[data-testid="modal-footer"]').exists()).toBe(false)
    w.unmount()
  })
})

// ── ADR-UX-17 (AC-UX-064) — prop `layer` là THÊM tuỳ chọn, mặc định KHÔNG đổi gì ──
// Bẫy Tailwind JIT: hai chuỗi z-index phải là literal trong BaseModal.vue; ghép động
// (`z-[${n}]`) ⇒ JIT không sinh class ⇒ overlay mất z-index một cách câm lặng.
describe('TC-UX6-07 — BaseModal prop `layer` (tầng xếp chồng)', () => {
  function overlayOf(w: ReturnType<typeof mount>): HTMLElement {
    return w.find('[data-testid="modal-card"]').element.parentElement as HTMLElement
  }

  it("KHÔNG truyền `layer` ⇒ giữ nguyên `z-50` (19 file tiêu thụ đổi 0 dòng)", () => {
    const w = mount(BaseModal, { props: { title: 'Hộp thoại nghiệp vụ' }, global: { stubs: { teleport: true } } })
    const cls = overlayOf(w).className
    expect(cls).toContain('z-50')
    expect(cls).not.toContain('z-[10000]')
    w.unmount()
  })

  it("`layer=\"system\"` ⇒ `z-[10000]`, KHÔNG còn `z-50`", () => {
    const w = mount(BaseModal, {
      props: { title: 'Hộp thoại hệ thống', layer: 'system' },
      global: { stubs: { teleport: true } },
    })
    const cls = overlayOf(w).className
    expect(cls).toContain('z-[10000]')
    expect(cls).not.toContain('z-50')
    w.unmount()
  })

  it("`layer=\"default\"` tường minh ⇒ y hệt khi bỏ trống", () => {
    const w = mount(BaseModal, {
      props: { title: 'Hộp thoại nghiệp vụ', layer: 'default' },
      global: { stubs: { teleport: true } },
    })
    expect(overlayOf(w).className).toContain('z-50')
    w.unmount()
  })
})
