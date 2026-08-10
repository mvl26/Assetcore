// Hạ tầng test cho hộp thoại xác nhận SSoT (`useModal()` + `NotificationModal.vue`).
//
// VÌ SAO CẦN: `useModal()` giữ hàng đợi ở **module-level singleton** (`composables/
// useModal.ts` — `const queue = ref([])` ngoài hàm). Hệ quả với test:
//
//  1. Mount RIÊNG một view rồi bấm nút hành động ⇒ `await modal.confirm(...)` treo
//     vĩnh viễn, vì không có ai render hàng đợi để bấm nút trả lời. Test sẽ "xanh"
//     một cách vô nghĩa (API không được gọi vì handler còn đang chờ) — đúng kiểu
//     false-green mà `window.confirm` giả lập trước đây che mất.
//     ⇒ `mountWithConfirm()` mount view **kèm** `NotificationModal`.
//
//  2. Hàng đợi KHÔNG reset giữa các test. Một test để hộp thoại mở rồi kết thúc thì
//     test SAU thấy "hộp thoại ma" và câu trả lời của nó rơi nhầm vào request cũ.
//     ⇒ `resetModalQueue()` bắt buộc gọi trong `afterEach`.
//
// KHÔNG dùng `vi.spyOn(window, 'confirm')` ở bất kỳ đâu nữa: đó chính là thứ lô 1
// đang xoá bỏ, và nó không chứng minh được hộp thoại có render tiếng Việt hay không.
import { mount, flushPromises } from '@vue/test-utils'
import type { ComponentMountingOptions } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import type { Component } from 'vue'
import { useModal } from '@/composables/useModal'
import NotificationModal from '@/components/common/NotificationModal.vue'

/**
 * Dọn hàng đợi hộp thoại giữa hai test.
 *
 * Mỗi request còn treo được `resolve(false)` — promise của test trước không bị bỏ rơi
 * (bỏ rơi ⇒ unhandled rejection / test treo ở CI dù xanh ở máy dev).
 */
export function resetModalQueue(): void {
  const { queue, dismiss } = useModal()
  // Chụp id TRƯỚC khi lặp: `dismiss` cắt phần tử khỏi mảng đang duyệt.
  for (const id of queue.value.map((m) => m.id)) dismiss(id, false)
}

/** Nội dung hàng đợi hiện tại — dùng để assert "queue rỗng" / đọc tiêu đề đang hiện. */
export function modalQueue() {
  return useModal().queue.value
}

/** Request đang hiển thị (phần tử đầu FIFO), `undefined` nếu không có hộp thoại nào. */
export function currentModal() {
  return useModal().queue.value[0]
}

export interface ConfirmHarness<T> {
  /** Wrapper của view đang kiểm — dùng để tìm nút, đọc text như bình thường. */
  wrapper: T
  /** Wrapper của `NotificationModal` — nơi hộp thoại thật sự render. */
  modal: ReturnType<typeof mount>
  /**
   * Trả lời hộp thoại đang mở: `true` = bấm «Xác nhận», `false` = bấm «Huỷ».
   * Bấm nút THẬT trong DOM (không gọi `dismiss()` tắt) ⇒ test chứng minh nút tồn tại,
   * bấm được và nối đúng dây. Ném lỗi nếu không có hộp thoại nào đang mở — im lặng
   * bỏ qua sẽ biến "quên mở hộp thoại" thành test xanh.
   */
  answerConfirm: (ok: boolean) => Promise<void>
  /** Text hiển thị của hộp thoại đang mở (tiêu đề + nội dung + nhãn nút). */
  modalText: () => string
  /** Gỡ cả hai wrapper. `resetModalQueue()` vẫn nên gọi trong `afterEach`. */
  unmount: () => void
}

/**
 * Mount view CÙNG `NotificationModal` để luồng `await modal.confirm(...)` chạy trọn vẹn.
 *
 * `teleport: true` được ép vào stubs của CẢ HAI wrapper: `BaseModal` teleport ra `<body>`,
 * không stub thì `modal.find(...)` không thấy gì.
 */
export function mountWithConfirm<C extends Component>(
  component: C,
  options: ComponentMountingOptions<C> = {} as ComponentMountingOptions<C>,
): ConfirmHarness<ReturnType<typeof mount<C>>> {
  const opts = options as Record<string, unknown>
  const global = (opts.global ?? {}) as Record<string, unknown>
  const stubs = (global.stubs ?? {}) as Record<string, unknown>

  const wrapper = mount(component, {
    ...(opts as object),
    global: { ...global, stubs: { ...stubs, teleport: true } },
  } as ComponentMountingOptions<C>)

  const modal = mount(NotificationModal, { global: { stubs: { teleport: true } } })

  async function answerConfirm(ok: boolean): Promise<void> {
    await flushPromises()
    const testid = ok ? 'modal-confirm' : 'modal-cancel'
    const btn = modal.find(`[data-testid="${testid}"]`)
    if (!btn.exists()) {
      throw new Error(
        `Không có hộp thoại xác nhận đang mở (không tìm thấy [data-testid="${testid}"]). ` +
          'Nút hành động phải gọi `await modal.confirm(...)` của `useModal()` — ' +
          'nếu vẫn dùng `window.confirm` thì không có gì render.',
      )
    }
    await btn.trigger('click')
    await flushPromises()
  }

  return {
    wrapper,
    modal,
    answerConfirm,
    modalText: () => modal.text(),
    unmount: () => { wrapper.unmount(); modal.unmount() },
  }
}

/**
 * Mount CHỈ `NotificationModal` — cho test hợp đồng của chính hộp thoại
 * (`NotificationModalBaseModal.test.ts`), không cần view nào.
 */
export function mountModalHost() {
  return mount(
    defineComponent({
      name: 'ModalHost',
      render: () => h(NotificationModal),
    }),
    { global: { stubs: { teleport: true } }, attachTo: document.body },
  )
}
