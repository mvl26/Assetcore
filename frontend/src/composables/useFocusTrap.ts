// useFocusTrap — nguồn DUY NHẤT của logic bẫy focus hộp thoại (docs/ui-ux/04 §2).
//
// Vì sao tồn tại: hành vi bàn phím của hộp thoại (Tab quay vòng · Escape · trả focus về
// nơi mở) trước đây chỉ có ở `CommandPalette.vue` dưới dạng mã tự viết. `BaseModal.vue`
// — SSoT của 19 màn — KHÔNG có gì cả. Chép mã sang BaseModal = 2 bản sao trôi khỏi nhau.
// Composable này TRÍCH nguyên hành vi đã chạy tốt của palette ra 1 chỗ; cả BaseModal lẫn
// CommandPalette cùng dùng (no-fork, khoá bằng guard `modalOverlayHygiene.test.ts`).
//
// Luật tầng: logic THUẦN DOM — 0 store, 0 router, 0 API, 0 component. Chỉ phụ thuộc `vue`.
import { nextTick, onBeforeUnmount } from 'vue'
import type { Ref } from 'vue'

export interface FocusTrapOptions {
  /** Phần tử gốc của vùng bẫy. Đọc TẠI THỜI ĐIỂM GỌI (ref có thể chưa gắn lúc setup). */
  container: Ref<HTMLElement | null>
  /**
   * Có handler ⇒ composable tự đăng ký listener `keydown` trên `document` khi activate,
   * và GỠ khi deactivate/unmount. Không truyền ⇒ KHÔNG đăng ký listener nào
   * (thành phần tự xử lý Escape — một hộp thoại chỉ được có ĐÚNG 1 chủ sở hữu phím Escape).
   */
  onEscape?: () => void
  /** Mặc định true — trả focus về phần tử đang focus TRƯỚC khi activate. */
  returnFocus?: boolean
  /** Phần tử focus đầu tiên. Mặc định = `tabbablesIn(container)[0]` ?? chính container. */
  initialFocus?: () => HTMLElement | null
}

export interface FocusTrap {
  /** Lưu opener → đẩy vào ngăn xếp → đăng ký listener (đồng bộ) → await nextTick → focus. */
  activate: () => Promise<void>
  /** Idempotent: gọi nhiều lần chỉ có tác dụng lần đầu. Gỡ listener + rời ngăn xếp + trả focus. */
  deactivate: () => void
  /** Gọi từ `@keydown` của container. Trả `true` nếu ĐÃ xử lý (đã `preventDefault`). */
  handleTabKey: (e: KeyboardEvent) => boolean
  /** Danh sách phần tử tab được trong container, tính lại mỗi lần gọi. */
  tabbables: () => HTMLElement[]
  /** Instance này có đang ở ĐỈNH ngăn xếp hộp thoại không. */
  isTopmost: () => boolean
}

const TABBABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

/**
 * "Đang hiển thị" — KHÔNG dùng `offsetParent !== null`.
 *
 * jsdom không cài layout ⇒ `offsetParent` luôn `null` cho MỌI phần tử ⇒ danh sách rỗng
 * ⇒ mọi test bẫy focus đỏ vĩnh viễn dù mã đúng. (Mã cũ của palette phải vá bằng
 * `|| el === inputEl.value` chính vì bẫy này — đừng chép lại cái vá đó.)
 */
function isVisible(el: HTMLElement): boolean {
  if (el.hasAttribute('hidden') || el.closest('[hidden]')) return false
  if (el.getAttribute('aria-hidden') === 'true') return false
  const s = typeof getComputedStyle === 'function' ? getComputedStyle(el) : null
  return !s || (s.display !== 'none' && s.visibility !== 'hidden')
}

/**
 * Danh sách phần tử tab được trong `root`, theo THỨ TỰ DOM.
 *
 * Giới hạn đã biết (ghi rõ, không phải bug ẩn):
 *  1. `tabindex` DƯƠNG cố ý không hỗ trợ — dự án 0 hit `tabindex="1"`+.
 *  2. Phần tử bị CHA `display:none` che ở trình duyệt thật vẫn lọt (computed style của
 *     con không phải `none`). Chấp nhận: nội dung hộp thoại theo thiết kế là đang hiện.
 *
 * Dùng chung — KHÔNG nhân bản selector này ở bất kỳ file nào khác (guard §5.4 khoá).
 */
export function tabbablesIn(root: HTMLElement | null): HTMLElement[] {
  if (!root) return []
  return Array.from(root.querySelectorAll<HTMLElement>(TABBABLE_SELECTOR)).filter(isVisible)
}

let dialogIdSeq = 0

/**
 * Sinh id duy nhất theo THỨ TỰ TẠO (đếm theo MODULE).
 *
 * KHÔNG dùng `useId()` của Vue 3.5: nó đếm theo APP — 2 lần `mount()` trong cùng file test
 * tạo 2 app khác nhau và CÙNG cho `v-0` ⇒ 2 hộp thoại đồng thời trùng id (A1 đỏ oan).
 */
export function nextDialogId(prefix = 'ac-dialog'): string {
  dialogIdSeq += 1
  return `${prefix}-${dialogIdSeq}`
}

/**
 * Ngăn xếp hộp thoại (module-scope, dùng chung mọi instance).
 *
 * 2 hộp thoại mở đồng thời là tình huống THẬT (A1 đòi id không trùng chính vì vậy). Nếu cả
 * hai cùng nghe `Escape` trên `document` thì 1 lần nhấn đóng CẢ HAI, và `handleTabKey` của
 * hộp dưới cũng cướp phím Tab. ⇒ `onEscape` và `handleTabKey` CHỈ chạy khi ở đỉnh ngăn xếp.
 */
const stack: symbol[] = []

export function useFocusTrap(options: FocusTrapOptions): FocusTrap {
  const token = Symbol('ac-focus-trap')
  let active = false
  let opener: HTMLElement | null = null

  const isTopmost = (): boolean => stack[stack.length - 1] === token
  const tabbables = (): HTMLElement[] => tabbablesIn(options.container.value)

  function onDocKeydown(e: KeyboardEvent): void {
    if (e.key !== 'Escape' || !isTopmost()) return
    e.preventDefault()
    options.onEscape?.()
  }

  async function activate(): Promise<void> {
    if (active) return
    active = true
    opener = (document.activeElement as HTMLElement) ?? null
    stack.push(token)
    // ĐỒNG BỘ — đăng ký sau `await nextTick()` thì nhấn Escape ở nhịp đầu rơi vào khoảng chết.
    if (options.onEscape) document.addEventListener('keydown', onDocKeydown)
    await nextTick()
    const target = options.initialFocus?.() ?? tabbables()[0] ?? options.container.value
    target?.focus()
  }

  function deactivate(): void {
    if (!active) return
    active = false
    if (options.onEscape) document.removeEventListener('keydown', onDocKeydown)
    const i = stack.indexOf(token)
    if (i >= 0) stack.splice(i, 1)
    // Trả focus phải chạy TRƯỚC khi DOM biến mất ⇒ gắn ở `onBeforeUnmount`, không `onUnmounted`.
    if (options.returnFocus !== false && opener && document.contains(opener)) opener.focus()
    opener = null
  }

  function handleTabKey(e: KeyboardEvent): boolean {
    if (e.key !== 'Tab' || !isTopmost()) return false
    const items = tabbables()
    if (items.length === 0) {
      e.preventDefault()
      return true
    }
    const first = items[0]
    const last = items[items.length - 1]
    const root = options.container.value
    const el = document.activeElement as HTMLElement | null
    const outside = !root || !el || !root.contains(el)
    if (e.shiftKey && (outside || el === first)) {
      e.preventDefault()
      last.focus()
      return true
    }
    if (!e.shiftKey && (outside || el === last)) {
      e.preventDefault()
      first.focus()
      return true
    }
    return false
  }

  onBeforeUnmount(deactivate)

  return { activate, deactivate, handleTabKey, tabbables, isTopmost }
}
