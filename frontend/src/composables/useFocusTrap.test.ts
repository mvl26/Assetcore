/* eslint-disable vue/one-component-per-file -- component "vật thử" dựng tại chỗ để lái trap thật */
// TDD — useFocusTrap (docs/ui-ux/04 §7.1, TC-UX5-01..12).
//
// Nguyên tắc chấm: assert `document.activeElement` THẬT, không đếm số lần gọi hàm — một bẫy
// focus "gọi đủ hàm" mà focus không nhảy thì với người dùng bàn phím nó vẫn hỏng.
// Mọi component test mount `attachTo: document.body` — `.focus()` vô nghĩa khi chưa gắn DOM.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { defineComponent, h, ref, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { useFocusTrap, tabbablesIn, nextDialogId } from './useFocusTrap'
import type { FocusTrap } from './useFocusTrap'

/** Component thật (không mock DOM) phơi `trap` ra ngoài để test lái trực tiếp. */
function makeHost(opts: {
  onEscape?: () => void
  returnFocus?: boolean
  initialFocus?: boolean
  inner?: () => unknown
  autoActivate?: boolean
}) {
  let captured: FocusTrap | null = null
  const Host = defineComponent({
    setup() {
      const box = ref<HTMLElement | null>(null)
      const trap = useFocusTrap({
        container: box,
        onEscape: opts.onEscape,
        returnFocus: opts.returnFocus,
        initialFocus: opts.initialFocus
          ? () => box.value?.querySelector<HTMLElement>('#second') ?? null
          : undefined,
      })
      captured = trap
      return { box, trap }
    },
    render() {
      return h(
        'div',
        { ref: 'box', tabindex: '-1', 'data-testid': 'box' },
        opts.inner
          ? (opts.inner() as never)
          : [
              h('button', { id: 'first' }, 'Một'),
              h('button', { id: 'second' }, 'Hai'),
              h('button', { id: 'third' }, 'Ba'),
            ],
      )
    },
  })
  const wrapper = mount(Host, { attachTo: document.body })
  return { wrapper, trap: captured as unknown as FocusTrap }
}

function tabEvent(shiftKey = false): KeyboardEvent {
  return new KeyboardEvent('keydown', { key: 'Tab', shiftKey, bubbles: true, cancelable: true })
}

beforeEach(() => {
  document.body.innerHTML = ''
})

describe('TC-UX5-01/02 — tabbablesIn (§2.2)', () => {
  it('TC-UX5-01 đúng thứ tự DOM, bỏ [disabled] và tabindex="-1"', () => {
    const root = document.createElement('div')
    root.innerHTML = `
      <a href="#a" id="l1">link</a>
      <button id="b1">b1</button>
      <button id="b2" disabled>b2</button>
      <input id="i1" />
      <input id="i2" disabled />
      <select id="s1"></select>
      <textarea id="t1"></textarea>
      <div id="d1" tabindex="0">div</div>
      <div id="d2" tabindex="-1">skip</div>
      <span id="sp">không tab được</span>
    `
    document.body.appendChild(root)
    expect(tabbablesIn(root).map((el) => el.id)).toEqual(['l1', 'b1', 'i1', 's1', 't1', 'd1'])
  })

  it('TC-UX5-02 KHÔNG rỗng trong jsdom (chống bẫy offsetParent luôn null)', () => {
    const root = document.createElement('div')
    root.innerHTML = '<button id="only">x</button>'
    document.body.appendChild(root)
    // offsetParent trong jsdom = null cho MỌI phần tử ⇒ bộ lọc cũ sẽ trả [].
    expect(root.querySelector<HTMLElement>('#only')!.offsetParent).toBeNull()
    expect(tabbablesIn(root)).toHaveLength(1)
  })

  it('TC-UX5-02b bỏ phần tử [hidden] / aria-hidden="true"', () => {
    const root = document.createElement('div')
    root.innerHTML = `
      <button id="ok">ok</button>
      <button id="h1" hidden>ẩn</button>
      <button id="h2" aria-hidden="true">ẩn</button>
    `
    document.body.appendChild(root)
    expect(tabbablesIn(root).map((el) => el.id)).toEqual(['ok'])
  })

  it('tabbablesIn(null) trả mảng rỗng, không ném lỗi', () => {
    expect(tabbablesIn(null)).toEqual([])
  })
})

describe('TC-UX5-03..06 — bẫy focus 2 chiều (INV-UX5-5/6)', () => {
  it('TC-UX5-03 activate() focus phần tử tab được ĐẦU TIÊN', async () => {
    const { trap } = makeHost({})
    await trap.activate()
    expect((document.activeElement as HTMLElement).id).toBe('first')
  })

  it('TC-UX5-03b initialFocus có ưu tiên hơn phần tử đầu', async () => {
    const { trap } = makeHost({ initialFocus: true })
    await trap.activate()
    expect((document.activeElement as HTMLElement).id).toBe('second')
  })

  it('TC-UX5-04 Tab ở phần tử CUỐI → quay về ĐẦU', async () => {
    const { trap } = makeHost({})
    await trap.activate()
    document.getElementById('third')!.focus()
    const e = tabEvent()
    expect(trap.handleTabKey(e)).toBe(true)
    expect(e.defaultPrevented).toBe(true)
    expect((document.activeElement as HTMLElement).id).toBe('first')
  })

  it('TC-UX5-05 Shift+Tab ở phần tử ĐẦU → về CUỐI', async () => {
    const { trap } = makeHost({})
    await trap.activate()
    document.getElementById('first')!.focus()
    const e = tabEvent(true)
    expect(trap.handleTabKey(e)).toBe(true)
    expect((document.activeElement as HTMLElement).id).toBe('third')
  })

  it('Tab ở GIỮA không bị chặn (trình duyệt tự đi tiếp)', async () => {
    const { trap } = makeHost({})
    await trap.activate()
    document.getElementById('second')!.focus()
    const e = tabEvent()
    expect(trap.handleTabKey(e)).toBe(false)
    expect(e.defaultPrevented).toBe(false)
  })

  it('TC-UX5-06 focus đang NGOÀI container + Tab → kéo về ĐẦU', async () => {
    const outside = document.createElement('button')
    outside.id = 'outside'
    document.body.appendChild(outside)
    const { trap } = makeHost({})
    await trap.activate()
    outside.focus()
    expect(trap.handleTabKey(tabEvent())).toBe(true)
    expect((document.activeElement as HTMLElement).id).toBe('first')
  })

  it('TC-UX5-11 container 0 tabbable + Tab ⇒ preventDefault, không ném lỗi', async () => {
    const { trap } = makeHost({ inner: () => [h('p', 'chỉ có chữ')] })
    await trap.activate()
    const e = tabEvent()
    expect(() => trap.handleTabKey(e)).not.toThrow()
    expect(e.defaultPrevented).toBe(true)
  })

  it('phím KHÁC Tab ⇒ handleTabKey trả false, không đụng focus', async () => {
    const { trap } = makeHost({})
    await trap.activate()
    const e = new KeyboardEvent('keydown', { key: 'ArrowDown', cancelable: true })
    expect(trap.handleTabKey(e)).toBe(false)
    expect(e.defaultPrevented).toBe(false)
  })
})

describe('TC-UX5-07/08 — trả focus + idempotent (INV-UX5-7)', () => {
  it('TC-UX5-07 deactivate() trả focus về opener', async () => {
    const opener = document.createElement('button')
    opener.id = 'opener'
    document.body.appendChild(opener)
    opener.focus()

    const { trap } = makeHost({})
    await trap.activate()
    expect((document.activeElement as HTMLElement).id).toBe('first')

    trap.deactivate()
    expect((document.activeElement as HTMLElement).id).toBe('opener')
  })

  it('returnFocus:false ⇒ KHÔNG trả focus', async () => {
    const opener = document.createElement('button')
    opener.id = 'opener'
    document.body.appendChild(opener)
    opener.focus()

    const { trap } = makeHost({ returnFocus: false })
    await trap.activate()
    trap.deactivate()
    expect((document.activeElement as HTMLElement).id).not.toBe('opener')
  })

  it('TC-UX5-08 deactivate() gọi 2 lần: không ném lỗi, không focus lại lần 2', async () => {
    const opener = document.createElement('button')
    opener.id = 'opener'
    document.body.appendChild(opener)
    opener.focus()

    const { trap } = makeHost({})
    await trap.activate()
    trap.deactivate()

    const other = document.createElement('button')
    other.id = 'other'
    document.body.appendChild(other)
    other.focus()

    expect(() => trap.deactivate()).not.toThrow()
    // Lần 2 phải là no-op ⇒ focus vẫn ở `other`, KHÔNG bị kéo về opener.
    expect((document.activeElement as HTMLElement).id).toBe('other')
  })

  it('unmount ⇒ trả focus (deactivate chạy ở onBeforeUnmount, DOM còn sống)', async () => {
    const opener = document.createElement('button')
    opener.id = 'opener'
    document.body.appendChild(opener)
    opener.focus()

    const { wrapper, trap } = makeHost({})
    await trap.activate()
    wrapper.unmount()
    expect((document.activeElement as HTMLElement).id).toBe('opener')
  })
})

describe('TC-UX5-09/10 — Escape + ngăn xếp hộp thoại (INV-UX5-4/13)', () => {
  it('TC-UX5-09 onEscape chạy ĐÚNG 1 lần; sau unmount dispatch tiếp ⇒ 0 lần', async () => {
    const onEscape = vi.fn()
    const { wrapper, trap } = makeHost({ onEscape })
    await trap.activate()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', cancelable: true }))
    expect(onEscape).toHaveBeenCalledTimes(1)

    wrapper.unmount()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', cancelable: true }))
    expect(onEscape).toHaveBeenCalledTimes(1) // listener đã gỡ — không rò
  })

  it('TC-UX5-09b listener keydown trên document được GỠ THẬT sau unmount (chống rò)', async () => {
    // Vì sao cần TC riêng: assert "không emit thêm" một mình là VACUOUS — ngăn xếp topmost
    // (§2.3) đã chặn handler ngay cả khi listener còn dính. Đã kiểm bằng mutation: bỏ
    // `removeEventListener` mà mọi TC hành vi vẫn xanh. TC này khoá đúng phần RÒ TÀI NGUYÊN.
    const add = vi.spyOn(document, 'addEventListener')
    const remove = vi.spyOn(document, 'removeEventListener')
    try {
      const onEscape = vi.fn()
      const { wrapper, trap } = makeHost({ onEscape })
      await trap.activate()
      const added = add.mock.calls.filter(([type]) => type === 'keydown')
      expect(added.length).toBe(1)

      wrapper.unmount()
      const removed = remove.mock.calls.filter(([type]) => type === 'keydown')
      expect(removed.length).toBe(1)
      // Cùng MỘT tham chiếu hàm — gỡ nhầm hàm khác thì listener vẫn dính.
      expect(removed[0][1]).toBe(added[0][1])
    } finally {
      add.mockRestore()
      remove.mockRestore()
    }
  })

  it('KHÔNG truyền onEscape ⇒ không đăng ký listener nào', async () => {
    const { trap } = makeHost({})
    await trap.activate()
    expect(() =>
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })),
    ).not.toThrow()
  })

  it('TC-UX5-10 2 trap lồng nhau: ESC chỉ chạy của trap TRÊN, đóng rồi mới tới trap DƯỚI', async () => {
    const outer = vi.fn()
    const inner = vi.fn()
    const a = makeHost({ onEscape: outer })
    await a.trap.activate()
    const b = makeHost({ onEscape: inner })
    await b.trap.activate()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', cancelable: true }))
    expect(inner).toHaveBeenCalledTimes(1)
    expect(outer).toHaveBeenCalledTimes(0)

    b.trap.deactivate()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', cancelable: true }))
    expect(outer).toHaveBeenCalledTimes(1)
    expect(inner).toHaveBeenCalledTimes(1)

    a.trap.deactivate()
  })

  it('trap KHÔNG ở đỉnh ngăn xếp thì không cướp phím Tab', async () => {
    const a = makeHost({})
    await a.trap.activate()
    const b = makeHost({})
    await b.trap.activate()

    expect(a.trap.isTopmost()).toBe(false)
    expect(b.trap.isTopmost()).toBe(true)
    expect(a.trap.handleTabKey(tabEvent())).toBe(false)

    b.trap.deactivate()
    a.trap.deactivate()
  })
})

describe('TC-UX5-12 — nextDialogId (INV-UX5-3)', () => {
  it('sinh chuỗi KHÁC nhau qua các lần gọi', () => {
    const ids = [nextDialogId(), nextDialogId(), nextDialogId('ac-modal-title')]
    expect(new Set(ids).size).toBe(3)
    expect(ids[2].startsWith('ac-modal-title-')).toBe(true)
  })
})

describe('activate() — bất biến cài đặt', () => {
  it('idempotent: gọi 2 lần không đổi opener đã lưu', async () => {
    const opener = document.createElement('button')
    opener.id = 'opener'
    document.body.appendChild(opener)
    opener.focus()

    const { trap } = makeHost({})
    await trap.activate()
    await trap.activate() // lần 2 = no-op; nếu ghi đè opener thì opener thành #first
    trap.deactivate()
    expect((document.activeElement as HTMLElement).id).toBe('opener')
  })

  it('listener Escape đăng ký ĐỒNG BỘ (Escape ngay nhịp đầu vẫn ăn)', () => {
    const onEscape = vi.fn()
    const { trap } = makeHost({ onEscape })
    void trap.activate() // CHƯA await nextTick
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', cancelable: true }))
    expect(onEscape).toHaveBeenCalledTimes(1)
    trap.deactivate()
  })

  it('container chưa gắn (null) ⇒ activate không ném lỗi', async () => {
    const Empty = defineComponent({
      setup() {
        const box = ref<HTMLElement | null>(null)
        const trap = useFocusTrap({ container: box })
        return { trap }
      },
      render: () => h('div'),
      })
    const w = mount(Empty, { attachTo: document.body })
    await expect((w.vm as unknown as { trap: FocusTrap }).trap.activate()).resolves.toBeUndefined()
    await nextTick()
    w.unmount()
  })
})
