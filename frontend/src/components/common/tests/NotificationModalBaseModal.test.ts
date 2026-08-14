// AC-UX-064 — `NotificationModal` render QUA `BaseModal` (docs/ui-ux/04 §1.2).
//
// Vì sao: `useModal()` là SSoT xác nhận của toàn ứng dụng, nhưng bản render của nó lại
// TỰ VẼ overlay (`fixed inset-0 z-[10000]`) ⇒ mọi hộp thoại xác nhận đứng NGOÀI khoản
// đầu tư a11y vòng 5 (`role=dialog` · `aria-labelledby` · bẫy focus · Escape 1 chủ sở
// hữu). Càng di trú `confirm()` trần sang `useModal()` thì lỗ này càng rộng — nên phải
// vá SSoT TRƯỚC, di trú SAU.
//
// Hợp đồng đối ngoại của `useModal()` (alert/confirm/dismiss/queue · tone · confirmText/
// cancelText) GIỮ NGUYÊN TUYỆT ĐỐI: 0 dòng sửa ở phía gọi. Bộ test này khoá cả hai đầu —
// ngữ nghĩa dialog MỚI và hành vi CŨ.
import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { useModal } from '@/composables/useModal'
import { mountModalHost, resetModalQueue, modalQueue } from '@/test/confirmHarness'

afterEach(() => {
  resetModalQueue()
  // Dọn node teleport còn sót giữa hai test (không dùng innerHTML — replaceChildren
  // là API DOM thuần, không đi qua parser HTML).
  document.body.replaceChildren()
})

/** Bấm phím Escape ở tầng `document` — đúng nơi `useFocusTrap` nghe. */
async function pressEscape(): Promise<void> {
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
  await flushPromises()
}

describe('TC-UX064-1 — hộp thoại xác nhận là dialog THẬT (qua BaseModal)', () => {
  it('mở confirm ⇒ đúng 1 modal-card với role/aria-modal/aria-labelledby trỏ tiêu đề TỒN TẠI', async () => {
    const host = mountModalHost()
    const modal = useModal()
    void modal.confirm({ title: 'Xoá đơn nháp này?', body: 'Hành động không thể hoàn tác.' })
    await flushPromises()

    const cards = host.findAll('[data-testid="modal-card"]')
    expect(cards, 'NotificationModal phải render QUA BaseModal, không tự vẽ overlay').toHaveLength(1)

    const card = cards[0]
    expect(card.attributes('role')).toBe('dialog')
    expect(card.attributes('aria-modal')).toBe('true')

    // `aria-labelledby` phải trỏ tới một id CÓ THẬT trong card — trỏ vào hư vô thì
    // trình đọc màn hình đọc rỗng, tệ hơn là không khai gì.
    const labelledBy = card.attributes('aria-labelledby')
    expect(labelledBy).toBeTruthy()
    const titleEl = card.find(`#${labelledBy}`)
    expect(titleEl.exists(), `aria-labelledby="${labelledBy}" không trỏ tới phần tử nào`).toBe(true)
    expect(titleEl.text()).toBe('Xoá đơn nháp này?')

    host.unmount()
  })

  it('KHÔNG có hộp thoại nào khi hàng đợi rỗng', async () => {
    const host = mountModalHost()
    await flushPromises()
    expect(host.findAll('[data-testid="modal-card"]')).toHaveLength(0)
    host.unmount()
  })
})

// ── ESC KÉP — Prove-It ───────────────────────────────────────────────────────
// `NotificationModal` cũ tự gắn `globalThis.addEventListener('keydown', …)`. Sau khi
// render qua `BaseModal`, `useFocusTrap` CŨNG nghe Escape trên `document` ⇒ 2 chủ sở hữu.
//
// ĐÍNH CHÍNH giả thuyết ban đầu của đề bài («resolve gọi 2 lần cho 1 hộp thoại»): điều đó
// KHÔNG tái lập được — `dismiss()` tra theo id và `splice` ĐỒNG BỘ, nên lời gọi thứ hai
// rơi vào `findIndex < 0` và thoát. Đã dựng thử nghiệm với listener khôi phục để kiểm chứng.
//
// Hỏng THẬT (đã tái lập, xem TC dưới): khi hàng đợi có ≥2 mục, listener thứ hai chạy SAU
// khi mục đầu đã bị gỡ ⇒ `current` đã trỏ sang mục THỨ HAI ⇒ một lần nhấn Escape huỷ oan
// CẢ HAI hộp thoại. Người dùng mất luôn câu hỏi chưa kịp đọc. Đây là dấu hiệu để canh.
describe('TC-UX064-2 — ESC KÉP: 1 lần nhấn = ĐÚNG 1 hộp thoại bị huỷ (Prove-It)', () => {
  it('Escape 1 lần ⇒ resolve gọi đúng 1 lần, giá trị false, hàng đợi rỗng', async () => {
    const host = mountModalHost()
    const modal = useModal()

    // Spy đếm: `resolve` bị gọi 2 lần thì promise chỉ settle 1 lần (JS nuốt lần 2),
    // nên assert trên `await` KHÔNG bao giờ bắt được lỗi này. Phải đếm lời gọi.
    const spy = vi.fn()
    const p = modal.confirm({ title: 'Huỷ đơn hàng?', body: 'Đơn sẽ chuyển sang trạng thái đã huỷ.' })
    const req = modalQueue()[0]
    const original = req.resolve
    req.resolve = (ok: boolean) => { spy(ok); original(ok) }

    await flushPromises()
    await pressEscape()

    expect(spy).toHaveBeenCalledTimes(1)
    expect(spy).toHaveBeenCalledWith(false)
    await expect(p).resolves.toBe(false)
    expect(modalQueue()).toHaveLength(0)

    host.unmount()
  })

  // 🔴 DẤU HIỆU CANH GÁC: khôi phục `addEventListener('keydown', …)` trong
  // `NotificationModal.vue` ⇒ TC này ĐỎ (hàng đợi về 0 thay vì còn 1).
  it('hàng đợi 2 mục + Escape 1 lần ⇒ CHỈ mục đầu bị huỷ, mục thứ hai còn nguyên', async () => {
    const host = mountModalHost()
    const modal = useModal()
    const first = modal.confirm({ title: 'Huỷ đơn hàng?', body: 'Nội dung một' })
    const second = modal.confirm({ title: 'Xoá đơn nháp?', body: 'Nội dung hai' })
    await flushPromises()

    await pressEscape()

    await expect(first).resolves.toBe(false)
    expect(
      modalQueue(),
      'Escape huỷ oan hộp thoại thứ hai — NotificationModal còn tự nghe keydown ' +
        'song song useFocusTrap (2 chủ sở hữu phím Escape).',
    ).toHaveLength(1)
    expect(host.find('[data-testid="modal-card"]').text()).toContain('Xoá đơn nháp?')

    // Dọn: trả lời nốt hộp thoại thứ hai.
    await host.find('[data-testid="modal-cancel"]').trigger('click')
    await expect(second).resolves.toBe(false)
    host.unmount()
  })

  it('Escape lần 2 (hàng đợi đã rỗng) KHÔNG ném lỗi, không dismiss oan hộp thoại kế tiếp', async () => {
    const host = mountModalHost()
    const modal = useModal()
    const first = modal.confirm({ title: 'Thao tác 1', body: 'Nội dung 1' })
    await flushPromises()
    await pressEscape()
    await expect(first).resolves.toBe(false)

    // Không có hộp thoại nào: nhấn thêm Escape phải là no-op.
    await pressEscape()
    expect(modalQueue()).toHaveLength(0)

    // Hộp thoại kế tiếp vẫn mở bình thường (listener cũ không còn treo).
    void modal.confirm({ title: 'Thao tác 2', body: 'Nội dung 2' })
    await flushPromises()
    expect(host.find('[data-testid="modal-card"]').text()).toContain('Thao tác 2')

    host.unmount()
  })
})

describe('TC-UX064-3 — bẫy focus theo hợp đồng BaseModal', () => {
  it('focus nằm TRONG card và KHÔNG phải nút đóng khi còn phần tử khác', async () => {
    const host = mountModalHost()
    const modal = useModal()
    void modal.confirm({ title: 'Duyệt đơn hàng?', body: 'Đơn sẽ chuyển sang trạng thái đã duyệt.' })
    await flushPromises()

    const card = host.find('[data-testid="modal-card"]').element
    const active = document.activeElement as HTMLElement
    expect(card.contains(active), 'focus phải nằm trong hộp thoại sau khi mở').toBe(true)

    const closeBtn = host.find('[data-testid="modal-close"]').element
    // Nút đóng nằm đầu DOM — focus vào đó rồi gõ Enter theo phản xạ = đóng nhầm.
    expect(active).not.toBe(closeBtn)

    host.unmount()
  })

  it('Tab tại phần tử cuối quay về phần tử đầu (vòng kín)', async () => {
    const host = mountModalHost()
    const modal = useModal()
    void modal.confirm({ title: 'Huỷ phiếu?', body: 'Tồn kho sẽ được hoàn nguyên.' })
    await flushPromises()

    const card = host.find('[data-testid="modal-card"]')
    const tabbables = card.element.querySelectorAll<HTMLElement>('button:not([disabled])')
    expect(tabbables.length).toBeGreaterThan(1)
    const first = tabbables[0]
    const last = tabbables[tabbables.length - 1]

    last.focus()
    await card.trigger('keydown', { key: 'Tab' })
    expect(document.activeElement).toBe(first)

    // Shift+Tab tại phần tử đầu quay về cuối.
    first.focus()
    await card.trigger('keydown', { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(last)

    host.unmount()
  })
})

describe('TC-UX064-4 — mọi đường huỷ đều resolve false (alert resolve void)', () => {
  type Act = (host: ReturnType<typeof mountModalHost>) => Promise<void>

  const clickCancel: Act = async (host) => {
    await host.find('[data-testid="modal-cancel"]').trigger('click')
  }
  const clickClose: Act = async (host) => {
    await host.find('[data-testid="modal-close"]').trigger('click')
  }
  const clickBackdrop: Act = async (host) => {
    // `@click.self` trên overlay — phần tử cha trực tiếp của card. `bubbles: false`
    // để `target` chắc chắn LÀ overlay (bấm vào card không được đóng hộp thoại).
    const overlay = host.find('[data-testid="modal-card"]').element.parentElement!
    overlay.dispatchEvent(new MouseEvent('click', { bubbles: false }))
    await flushPromises()
  }
  const escape: Act = async () => { await pressEscape() }

  // `confirm` có 2 nút ⇒ 3 đường huỷ bằng chuột + Escape.
  const CONFIRM_PATHS: readonly (readonly [string, Act])[] = [
    ['click nền', clickBackdrop], ['nút «Huỷ»', clickCancel], ['nút đóng', clickClose], ['phím Escape', escape],
  ]
  // `alert` theo hợp đồng chỉ có 1 nút («Đã hiểu») ⇒ KHÔNG có `modal-cancel`.
  // Ba đường thoát của nó là: nền · nút đóng · Escape.
  const ALERT_PATHS: readonly (readonly [string, Act])[] = [
    ['click nền', clickBackdrop], ['nút đóng', clickClose], ['phím Escape', escape],
  ]

  for (const [label, act] of CONFIRM_PATHS) {
    it(`confirm huỷ qua ${label} ⇒ resolve false, hàng đợi rỗng`, async () => {
      const host = mountModalHost()
      const p = useModal().confirm({ title: 'Xoá lịch khấu hao?', body: 'Lịch hiện tại sẽ bị xoá.' })
      await flushPromises()
      await act(host)
      await expect(p).resolves.toBe(false)
      expect(modalQueue()).toHaveLength(0)
      host.unmount()
    })
  }

  for (const [label, act] of ALERT_PATHS) {
    it(`alert đóng qua ${label} ⇒ resolve void, hàng đợi rỗng`, async () => {
      const host = mountModalHost()
      const p = useModal().alert({ title: 'Không thực hiện được', body: 'Thiếu quyền thao tác.' })
      await flushPromises()
      await act(host)
      await expect(p).resolves.toBeUndefined()
      expect(modalQueue()).toHaveLength(0)
      host.unmount()
    })
  }

  it('bấm vào CARD (không phải nền) KHÔNG đóng hộp thoại', async () => {
    const host = mountModalHost()
    const p = useModal().confirm({ title: 'Duyệt phiếu?', body: 'Tồn kho sẽ được cập nhật.' })
    await flushPromises()
    await host.find('[data-testid="modal-card"]').trigger('click')
    expect(modalQueue()).toHaveLength(1)
    // Dọn: trả lời để promise không bị bỏ rơi.
    await host.find('[data-testid="modal-cancel"]').trigger('click')
    await expect(p).resolves.toBe(false)
    host.unmount()
  })
})

describe('TC-UX064-5 — hồi quy hợp đồng useModal (0 dòng sửa phía gọi)', () => {
  it('confirm không truyền nhãn ⇒ «Xác nhận» / «Huỷ», tone mặc định warning (KHÔNG danger)', async () => {
    const host = mountModalHost()
    void useModal().confirm({ title: 'Tạo phiếu tiếp nhận?', body: 'Phiếu mới sẽ được tạo.' })
    await flushPromises()

    expect(host.find('[data-testid="modal-confirm"]').text()).toBe('Xác nhận')
    expect(host.find('[data-testid="modal-cancel"]').text()).toBe('Huỷ')

    // tone mặc định của confirm là 'warning' ⇒ KHÔNG mang tiêu đề đỏ của BaseModal.
    const title = host.find('[data-testid="modal-card"] h2')
    expect(title.classes()).not.toContain('text-red-700')

    host.unmount()
  })

  it('confirmText/cancelText tuỳ chỉnh được tôn trọng', async () => {
    const host = mountModalHost()
    void useModal().confirm({
      title: 'Sinh lại lịch?', body: 'Lịch cũ sẽ bị xoá.',
      confirmText: 'Sinh lại', cancelText: 'Giữ nguyên',
    })
    await flushPromises()
    expect(host.find('[data-testid="modal-confirm"]').text()).toBe('Sinh lại')
    expect(host.find('[data-testid="modal-cancel"]').text()).toBe('Giữ nguyên')
    host.unmount()
  })

  it('alert render ĐÚNG 1 nút hành động (không có nút Huỷ)', async () => {
    const host = mountModalHost()
    void useModal().alert({ title: 'Đã khoá thao tác', body: 'Liên hệ quản trị viên.' })
    await flushPromises()

    expect(host.find('[data-testid="modal-cancel"]').exists()).toBe(false)
    expect(host.find('[data-testid="modal-confirm"]').text()).toBe('Đã hiểu')

    host.unmount()
  })

  it("tone 'error'/'critical' ⇒ BaseModal ở chế độ danger (tiêu đề đỏ)", async () => {
    for (const tone of ['error', 'critical'] as const) {
      const host = mountModalHost()
      void useModal().confirm({ title: 'Xoá vĩnh viễn?', body: 'Không thể hoàn tác.', tone })
      await flushPromises()
      expect(
        host.find('[data-testid="modal-card"] h2').classes(),
        `tone='${tone}' phải bật prop danger của BaseModal`,
      ).toContain('text-red-700')
      resetModalQueue()
      host.unmount()
    }
  })

  it('actionHint vẫn render khi được truyền (hợp đồng cũ)', async () => {
    const host = mountModalHost()
    void useModal().alert({
      title: 'Không đủ tồn kho', body: 'Kho A còn 2 cái.', actionHint: 'Hãy tạo phiếu nhập trước.',
    })
    await flushPromises()
    expect(host.text()).toContain('Hãy tạo phiếu nhập trước.')
    host.unmount()
  })

  it('FIFO: hộp thoại thứ hai chỉ hiện sau khi hộp thoại đầu được trả lời', async () => {
    const host = mountModalHost()
    const modal = useModal()
    const first = modal.confirm({ title: 'Hộp thoại một', body: 'Nội dung một' })
    void modal.confirm({ title: 'Hộp thoại hai', body: 'Nội dung hai' })
    await flushPromises()

    expect(host.findAll('[data-testid="modal-card"]')).toHaveLength(1)
    expect(host.text()).toContain('Hộp thoại một')
    expect(host.text()).not.toContain('Hộp thoại hai')

    await host.find('[data-testid="modal-confirm"]').trigger('click')
    await expect(first).resolves.toBe(true)
    await flushPromises()
    expect(host.text()).toContain('Hộp thoại hai')

    host.unmount()
  })
})

describe('TC-UX064-7 — tầng xếp chồng (ADR-UX-17): hộp thoại hệ thống nằm TRÊN', () => {
  it("overlay mang `z-[10000]` (layer='system'), KHÔNG phải `z-50` mặc định", async () => {
    const host = mountModalHost()
    void useModal().confirm({ title: 'Xoá vĩnh viễn?', body: 'Không thể hoàn tác.', tone: 'error' })
    await flushPromises()

    const overlay = host.find('[data-testid="modal-card"]').element.parentElement as HTMLElement
    // Hộp thoại chặn thao tác phải nằm trên hộp thoại nghiệp vụ của màn; nếu cùng z-50
    // thì thứ tự vẽ chỉ còn phụ thuộc thứ tự Teleport chèn vào <body> — tức là ngẫu nhiên.
    expect(overlay.className).toContain('z-[10000]')
    expect(overlay.className).not.toContain('z-50')

    host.unmount()
  })
})

describe('TC-UX064-6 — LL-FE-53: nhãn mặc định 100% tiếng Việt', () => {
  it('0 chuỗi tiếng Anh trong hộp thoại mặc định', async () => {
    const host = mountModalHost()
    void useModal().confirm({ title: 'Duyệt phiếu?', body: 'Tồn kho sẽ được cập nhật.' })
    await flushPromises()
    const text = host.text()
    for (const en of ['Confirm', 'Cancel', 'OK', 'Close', 'Yes', 'No ']) {
      expect(text, `lọt chuỗi tiếng Anh «${en}» ra hộp thoại`).not.toContain(en)
    }
    host.unmount()
  })
})
