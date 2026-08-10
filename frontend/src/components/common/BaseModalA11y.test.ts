// TDD — hợp đồng a11y hộp thoại tại SSoT `BaseModal.vue`. Đánh số theo ĐỀ MỤC VÒNG 5
// (TC-UX5-01..07 của PM). File song song `BaseModalDialog.test.ts` đánh số theo spec BA
// (TC-UX5-20..29) và phủ thêm phần khuôn/footer — HAI hệ đánh số của cùng 1 vòng, cố ý
// giữ cả hai để lệnh chấm của PM lẫn của BA đều chạy được. `BaseModalResponsive.test.ts`
// (4 TC cũ) KHÔNG ĐƯỢC SỬA — nó là cổng chống-regress của vòng.
//
// Nguyên tắc: assert `document.activeElement` THẬT + so khớp GIÁ TRỊ id (không chỉ
// "thuộc tính có tồn tại"). Mọi mount `attachTo: document.body` — không attach thì
// `.focus()` vô nghĩa trong jsdom.
import { describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import BaseModal from './BaseModal.vue'

function mountModal(slotDefault = '<button id="a">A</button><button id="b">B</button>') {
  return mount(BaseModal, {
    props: { title: 'Tiêu đề' },
    slots: { default: slotDefault },
    attachTo: document.body,
    // Teleport stub ⇒ nội dung ở lại wrapper để find() thấy.
    global: { stubs: { teleport: true } },
  })
}

/**
 * Trả về `true` nếu CÓ handler nào đã xử lý phím (handler của bẫy focus gọi `preventDefault`).
 * Dùng `defaultPrevented` làm bằng chứng listener-còn-sống: sau `unmount` mà vẫn `true` nghĩa
 * là listener rò. (Chỉ đếm `emitted('close')` là VACUOUS — Vue ngừng ghi emit sau unmount nên
 * assert đó xanh cả khi listener chưa gỡ; đã kiểm bằng mutation.)
 */
function pressEscapeOnDocument(): boolean {
  const e = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true })
  document.dispatchEvent(e)
  return e.defaultPrevented
}

beforeEach(() => {
  document.body.innerHTML = ''
})

describe('TC-UX5-01/02 — ngữ nghĩa hộp thoại (A1)', () => {
  it('TC-UX5-01 role="dialog" + aria-modal="true" trên đúng [data-testid="modal-card"]', async () => {
    const w = mountModal()
    await nextTick()
    const card = w.find('[data-testid="modal-card"]')
    expect(card.exists()).toBe(true)
    expect(card.attributes('role')).toBe('dialog')
    expect(card.attributes('aria-modal')).toBe('true')
    w.unmount()
  })

  it('TC-UX5-02 aria-labelledby BẰNG ĐÚNG id của <h2> tiêu đề (so khớp giá trị)', async () => {
    const w = mountModal()
    await nextTick()
    const card = w.find('[data-testid="modal-card"]')
    const h2 = w.find('h2')
    const labelledBy = card.attributes('aria-labelledby')
    expect(labelledBy).toBeTruthy()
    expect(labelledBy).toBe(h2.attributes('id'))
    expect(h2.text()).toBe('Tiêu đề')
    w.unmount()
  })

  it('TC-UX5-02b 2 modal mount ĐỒNG THỜI ⇒ id KHÁC nhau, mỗi cái trỏ <h2> của CHÍNH nó', async () => {
    const w1 = mountModal()
    const w2 = mountModal()
    await nextTick()

    const id1 = w1.find('h2').attributes('id')
    const id2 = w2.find('h2').attributes('id')
    expect(id1).toBeTruthy()
    expect(id2).toBeTruthy()
    expect(id1).not.toBe(id2)
    expect(w1.find('[data-testid="modal-card"]').attributes('aria-labelledby')).toBe(id1)
    expect(w2.find('[data-testid="modal-card"]').attributes('aria-labelledby')).toBe(id2)

    w2.unmount()
    w1.unmount()
  })
})

describe('TC-UX5-03/04 — Escape đóng, listener không rò (A3)', () => {
  it('TC-UX5-03 Escape ⇒ emit close ĐÚNG 1 LẦN', async () => {
    const w = mountModal()
    await nextTick()
    pressEscapeOnDocument()
    expect(w.emitted('close')).toBeTruthy()
    expect(w.emitted('close')!).toHaveLength(1)
    w.unmount()
  })

  it('TC-UX5-04 sau unmount, Escape tiếp ⇒ KHÔNG emit thêm, không ném lỗi', async () => {
    const w = mountModal()
    await nextTick()
    // Còn sống ⇒ handler chạy ⇒ preventDefault.
    expect(pressEscapeOnDocument()).toBe(true)
    const emittedClose = w.emitted('close')!
    const before = emittedClose.length
    expect(before).toBe(1)

    w.unmount()

    // Đã gỡ ⇒ KHÔNG handler nào chạy ⇒ không preventDefault, không emit thêm, không ném lỗi.
    let handled: boolean | undefined
    expect(() => { handled = pressEscapeOnDocument() }).not.toThrow()
    expect(handled).toBe(false)
    expect(emittedClose.length).toBe(before)
  })
})

describe('TC-UX5-05/06 — bẫy focus (A4)', () => {
  it('TC-UX5-05 sau mount, document.activeElement nằm TRONG modal-card', async () => {
    const w = mountModal()
    await nextTick()
    const card = w.find('[data-testid="modal-card"]').element
    expect(card.contains(document.activeElement)).toBe(true)
    w.unmount()
  })

  it('TC-UX5-05b focus ban đầu KHÔNG rơi vào nút đóng khi thân bài có phần tử tab được', async () => {
    const w = mountModal()
    await nextTick()
    expect((document.activeElement as HTMLElement).id).toBe('a')
    w.unmount()
  })

  it('TC-UX5-06 Tab ở phần tử CUỐI → về ĐẦU; Shift+Tab ở ĐẦU → về CUỐI', async () => {
    const w = mountModal()
    await nextTick()
    const card = w.find('[data-testid="modal-card"]')
    const cardEl = card.element as HTMLElement

    const tabbables = Array.from(
      cardEl.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input:not([disabled])'),
    )
    const first = tabbables[0]
    const last = tabbables[tabbables.length - 1]
    expect(first).not.toBe(last)

    last.focus()
    await card.trigger('keydown', { key: 'Tab' })
    expect(document.activeElement).toBe(first)

    first.focus()
    await card.trigger('keydown', { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(last)

    w.unmount()
  })
})

describe('TC-UX5-07 — trả focus về nơi mở (A5)', () => {
  it('TC-UX5-07 phần tử focus TRƯỚC khi mở được focus lại sau unmount', async () => {
    const opener = document.createElement('button')
    opener.id = 'opener'
    document.body.appendChild(opener)
    opener.focus()
    expect((document.activeElement as HTMLElement).id).toBe('opener')

    const w = mountModal()
    await nextTick()
    expect((document.activeElement as HTMLElement).id).not.toBe('opener')

    w.unmount()
    expect((document.activeElement as HTMLElement).id).toBe('opener')
  })
})
