// AC-UX-062 — vùng lỗi CHẶN hành động hiện INLINE trong hộp thoại (docs/ui-ux/05 §2).
//
// Vấn đề nó chặn: 15/19 file tiêu thụ `BaseModal` không có vùng lỗi nào trong hộp thoại
// ⇒ lý do một thao tác bị máy chủ từ chối chỉ đến bằng toast **tự tắt sau 4000ms**
// (`composables/useToast.ts:33` → `:45`) trong khi hộp thoại vẫn mở. Người dùng nhìn lại
// hộp thoại thì không còn dấu vết vì sao hỏng.
//
// Hợp đồng cài ở SSoT (`BaseModal.vue` + `ModalInlineError.vue`) — CHỈ THÊM, không đụng
// prop/emit/testid/class cũ (bất biến 0-churn `05 §2.3`).
//
// Khuôn mount đi theo `BaseModalDialog.test.ts` (attachTo body + stub teleport) — không
// dựng bộ khung thứ hai.
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import BaseModal from './BaseModal.vue'
import ModalInlineError from './ModalInlineError.vue'

const HERE = dirname(fileURLToPath(import.meta.url))

function mountModal(
  props: Record<string, unknown> = {},
  slots: Record<string, string> = {},
) {
  return mount(BaseModal, {
    props: { title: 'Tiêu đề', ...props },
    slots: { default: '<button id="a">A</button><button id="b">B</button>', ...slots },
    attachTo: document.body,
    global: { stubs: { teleport: true } },
  })
}

beforeEach(() => {
  document.body.innerHTML = ''
})

describe('TC-UX062-01/02 — hợp đồng render vùng lỗi', () => {
  it('TC-UX062-01 không truyền `error` ⇒ 0 phần tử modal-error (15 màn chưa áp KHÔNG đổi hành vi)', async () => {
    const w = mountModal()
    await nextTick()
    expect(w.findAll('[data-testid="modal-error"]')).toHaveLength(0)
    expect(w.findAll('[role="alert"]')).toHaveLength(0)
    w.unmount()
  })

  it('TC-UX062-02 error="…" ⇒ có modal-error, role=alert, aria-live=assertive, đúng nguyên câu', async () => {
    const MSG = 'Người xác nhận phải khác người kiểm kê.'
    const w = mountModal({ error: MSG })
    await nextTick()
    const box = w.find('[data-testid="modal-error"]')
    expect(box.exists()).toBe(true)
    expect(box.attributes('role')).toBe('alert')
    expect(box.attributes('aria-live')).toBe('assertive')
    expect(box.text()).toContain(MSG)
    w.unmount()
  })
})

describe('TC-UX062-03 — vị trí: đầu modal-body, trước nội dung slot', () => {
  it('vùng lỗi nằm TRONG modal-body và là phần tử ĐẦU TIÊN', async () => {
    const w = mountModal({ error: 'Lỗi chặn' })
    await nextTick()
    const body = w.find('[data-testid="modal-body"]').element
    const box = w.find('[data-testid="modal-error"]').element
    expect(body.contains(box)).toBe(true)
    expect(body.firstElementChild).toBe(box)
    // slot mặc định vẫn render SAU vùng lỗi
    const slotFirst = w.find('#a').element
    expect(box.compareDocumentPosition(slotFirst) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
    w.unmount()
  })
})

describe('TC-UX062-04 — KHÔNG tự tắt (không hẹn giờ)', () => {
  afterEach(() => { vi.useRealTimers() })

  it('sau 10.000 ms giả lập, vùng lỗi VẪN còn trong DOM', async () => {
    vi.useFakeTimers()
    const w = mountModal({ error: 'Lỗi chặn không được biến mất' })
    await nextTick()
    expect(w.find('[data-testid="modal-error"]').exists()).toBe(true)
    vi.advanceTimersByTime(10_000)
    await nextTick()
    expect(w.find('[data-testid="modal-error"]').exists()).toBe(true)
    w.unmount()
  })

  it('mã nguồn SSoT không chứa `setTimeout` (BaseModal.vue và ModalInlineError.vue == 0)', () => {
    for (const f of ['BaseModal.vue', 'ModalInlineError.vue']) {
      const src = readFileSync(resolve(HERE, f), 'utf8')
      expect(src, `${f} không được có setTimeout (vùng lỗi KHÔNG tự tắt)`)
        .not.toMatch(/setTimeout/)
    }
  })
})

describe('TC-UX062-05 — bất biến 0-churn: props cũ render y như trước', () => {
  it('testid + ngữ nghĩa dialog giữ nguyên; error=null KHÔNG thêm node nào', async () => {
    const w = mountModal(
      { title: 'Xoá phiếu', size: 'lg', danger: true, error: null },
      { footer: '<button id="f">OK</button>' },
    )
    await nextTick()
    for (const id of ['modal-card', 'modal-close', 'modal-body', 'modal-footer']) {
      expect(w.find(`[data-testid="${id}"]`).exists(), id).toBe(true)
    }
    const card = w.find('[data-testid="modal-card"]')
    expect(card.attributes('role')).toBe('dialog')
    expect(card.attributes('aria-modal')).toBe('true')
    expect(card.attributes('aria-labelledby')).toBe(w.find('h2').attributes('id'))
    expect(w.findAll('[data-testid="modal-error"]')).toHaveLength(0)
    // Thân bài chỉ chứa nội dung slot — không có node rỗng chèn thêm.
    expect(w.find('[data-testid="modal-body"]').element.firstElementChild)
      .toBe(w.find('#a').element)
    w.unmount()
  })

  it('chuỗi rỗng cũng KHÔNG render khung đỏ trống', async () => {
    const w = mountModal({ error: '' })
    await nextTick()
    expect(w.findAll('[data-testid="modal-error"]')).toHaveLength(0)
    w.unmount()
  })
})

describe('TC-UX062-06 — theo state: null → chuỗi → null, không rò node cũ', () => {
  it('vùng lỗi xuất hiện rồi biến mất đúng theo prop', async () => {
    const w = mountModal({ error: null })
    await nextTick()
    expect(w.findAll('[data-testid="modal-error"]')).toHaveLength(0)

    await w.setProps({ error: 'Không đủ tồn kho để ghi nhận.' })
    await nextTick()
    expect(w.findAll('[data-testid="modal-error"]')).toHaveLength(1)
    expect(w.find('[data-testid="modal-error"]').text()).toContain('Không đủ tồn kho')

    await w.setProps({ error: null })
    await nextTick()
    expect(w.findAll('[data-testid="modal-error"]')).toHaveLength(0)
    w.unmount()
  })
})

describe('TC-UX062-07 — a11y: vùng lỗi không cướp focus, nhưng nằm trong cây modal-card', () => {
  it('focus ban đầu vẫn theo firstFocusTarget (phần tử tabbable đầu ≠ nút đóng)', async () => {
    const w = mountModal({ error: 'Lỗi chặn' })
    await nextTick()
    await nextTick()
    expect(document.activeElement).toBe(w.find('#a').element)
    w.unmount()
  })

  it('`data-autofocus` vẫn thắng, kể cả khi có vùng lỗi', async () => {
    const w = mountModal(
      { error: 'Lỗi chặn' },
      { default: '<button id="a">A</button><input id="focus-me" data-autofocus />' },
    )
    await nextTick()
    await nextTick()
    expect(document.activeElement).toBe(w.find('#focus-me').element)
    w.unmount()
  })

  it('vùng lỗi nằm trong cây modal-card (trình đọc màn hình đọc trong ngữ cảnh hộp thoại)', async () => {
    const w = mountModal({ error: 'Lỗi chặn' })
    await nextTick()
    const card = w.find('[data-testid="modal-card"]').element
    expect(card.contains(w.find('[data-testid="modal-error"]').element)).toBe(true)
    w.unmount()
  })
})

describe('TC-UX062-08 — errorTitle', () => {
  it('có errorTitle ⇒ hiển thị tiêu đề lỗi đó', async () => {
    const w = mountModal({ error: 'Chi tiết lỗi', errorTitle: 'Không ghi nhận được' })
    await nextTick()
    const box = w.find('[data-testid="modal-error"]')
    expect(box.text()).toContain('Không ghi nhận được')
    expect(box.text()).toContain('Chi tiết lỗi')
    w.unmount()
  })

  it('bỏ trống ⇒ tiêu đề mặc định VI, KHÔNG in chuỗi rỗng / "undefined"', async () => {
    const w = mountModal({ error: 'Chi tiết lỗi' })
    await nextTick()
    const text = w.find('[data-testid="modal-error"]').text()
    expect(text).not.toContain('undefined')
    expect(text).toContain('Không thực hiện được thao tác')
    w.unmount()
  })
})

describe('ModalInlineError.vue — dùng trực tiếp (đường B: overlay lai)', () => {
  it('render đủ ngữ nghĩa alert khi dùng độc lập', () => {
    const w = mount(ModalInlineError, { props: { message: 'Lỗi lưu dữ liệu nền.' } })
    const box = w.find('[data-testid="modal-error"]')
    expect(box.exists()).toBe(true)
    expect(box.attributes('role')).toBe('alert')
    expect(box.attributes('aria-live')).toBe('assertive')
    expect(w.find('[data-testid="modal-error-message"]').text()).toBe('Lỗi lưu dữ liệu nền.')
    w.unmount()
  })

  it('không có nút tự đóng vùng lỗi (chỉ biến mất khi thử lại / đóng hộp thoại)', () => {
    const w = mount(ModalInlineError, { props: { message: 'x' } })
    expect(w.findAll('button')).toHaveLength(0)
    w.unmount()
  })
})
