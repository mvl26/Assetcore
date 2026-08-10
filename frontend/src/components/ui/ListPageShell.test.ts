// TC-UX3-01…09 (AC-UX-041) — ui/ListPageShell.vue: khuôn 4 trạng thái LOẠI TRỪ LẪN NHAU.
//
// Bối cảnh (docs/ui-ux/02_LIST_PAGE_SHELL.md §1.1): nợ nặng nhất của lớp danh sách KHÔNG phải
// thiếu khung xương mà là **lỗi giả dạng rỗng** — API 500 ⇒ view rơi vào nhánh «chưa có dữ liệu»
// ⇒ người dùng tin là KHÔNG có bản ghi và không có đường thử lại. Guard này khoá bất biến
// «lỗi LUÔN thắng rỗng» ngay ở tầng 0, một lần cho mọi màn áp khuôn.
//
// Ưu tiên đã chốt (ADR-UX-05): error > loading > empty > content.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import ListPageShell from './ListPageShell.vue'

const SLOTS = {
  header: '<div data-testid="t-header">Tiêu đề màn</div>',
  summary: '<div data-testid="t-summary">Dải chỉ số</div>',
  filters: '<div data-testid="t-filters">Bộ lọc</div>',
  toolbar: '<div data-testid="t-toolbar">Hiển thị 3 / 3</div>',
  default: '<table data-testid="t-data"><tbody><tr><td>hàng 1</td></tr></tbody></table>',
  pagination: '<div data-testid="t-pagination">Trang 1</div>',
  'empty-action': '<button data-testid="t-empty-action">Xóa bộ lọc để xem tất cả</button>',
}

type Props = {
  loading?: boolean
  errorMessage?: string | null
  isEmpty?: boolean
  emptyTitle?: string
  emptyHint?: string
  errorHint?: string
}

function mountShell(props: Props = {}) {
  return mount(ListPageShell, { props, slots: SLOTS })
}

/** Tên máy-đọc của control: aria-label thắng, không có thì lấy text. */
function accessibleName(el: { attributes: (k: string) => string | undefined; text: () => string }) {
  return (el.attributes('aria-label') ?? el.text()).trim()
}

function retryControls(w: VueWrapper) {
  return w.findAll('button').filter((b) => accessibleName(b) === 'Thử lại')
}

/** 4 vùng thân bài loại trừ lẫn nhau — đếm vùng nào đang có mặt. */
function bodyRegions(w: VueWrapper) {
  return {
    loading: w.find('[data-testid="list-loading"]').exists(),
    error: w.find('[data-testid="ui-error"]').exists(),
    empty: w.find('[data-testid="ui-empty"]').exists(),
    content: w.find('[data-testid="list-content"]').exists(),
  }
}
function presentCount(w: VueWrapper) {
  return Object.values(bodyRegions(w)).filter(Boolean).length
}

/** Chuỗi rỗng cũ của 4 màn đích — không được xuất hiện khi đang lỗi (A3). */
const OLD_EMPTY_PHRASES = [
  'Chưa có đơn hàng nào',
  'Không có dữ liệu.',
  'Không có dữ liệu',
  'Không có kế hoạch nào phù hợp',
  'Chưa có nhà cung cấp nào.',
]

describe('ui/ListPageShell — 4 trạng thái loại trừ lẫn nhau (TC-UX3-01…09)', () => {
  it('TC-UX3-01: bảng tổ hợp — mỗi tổ hợp props chỉ 1 trong 4 vùng có mặt', () => {
    const combos: Array<[string, Props, keyof ReturnType<typeof bodyRegions>]> = [
      ['đang tải', { loading: true }, 'loading'],
      ['lỗi', { errorMessage: 'Máy chủ trả về 500.' }, 'error'],
      ['rỗng', { isEmpty: true }, 'empty'],
      ['có dữ liệu', { isEmpty: false }, 'content'],
    ]
    for (const [label, props, expected] of combos) {
      const w = mountShell(props)
      const regions = bodyRegions(w)
      expect(presentCount(w), `${label}: phải có ĐÚNG 1 vùng thân bài`).toBe(1)
      expect(regions[expected], `${label}: phải hiện vùng ${expected}`).toBe(true)
      expect(w.attributes('data-state'), `${label}: data-state`).toBe(
        expected === 'loading' ? 'loading' : expected === 'error' ? 'error'
          : expected === 'empty' ? 'empty' : 'content',
      )
      w.unmount()
    }
  })

  it('TC-UX3-01b: đang tải ⇒ khung xương, 0 <table> dữ liệu', () => {
    const w = mountShell({ loading: true })
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.find('[data-testid="t-data"]').exists()).toBe(false)
    expect(w.find('table').exists()).toBe(false)
  })

  it('TC-UX3-02 (BẤT BIẾN CHÍNH): lỗi + rỗng ⇒ ui-error, ui-empty === null', () => {
    const w = mountShell({ errorMessage: 'Không kết nối được máy chủ.', isEmpty: true })
    expect(w.attributes('data-state')).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    // queryByTestId === null tương đương exists() === false trong @vue/test-utils
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).toContain('Không kết nối được máy chủ.')
    for (const phrase of OLD_EMPTY_PHRASES) {
      expect(w.html(), `lỗi mà vẫn lộ chuỗi rỗng: ${phrase}`).not.toContain(phrase)
    }
  })

  it('TC-UX3-03: lỗi thắng mọi trạng thái khác (kèm đang tải / kèm dữ liệu cũ)', () => {
    // (a) lỗi + đang tải ⇒ lỗi (ADR-UX-05: người dùng LUÔN nhìn thấy lỗi)
    const a = mountShell({ errorMessage: 'Hết phiên làm việc.', loading: true })
    expect(a.attributes('data-state')).toBe('error')
    expect(a.find('[data-testid="list-loading"]').exists()).toBe(false)

    // (b) lỗi + còn dữ liệu cũ (isEmpty=false) ⇒ vẫn lỗi, KHÔNG giả vờ dữ liệu là mới
    //     (02_LIST_PAGE_SHELL.md §2.1 — bảng cũ dưới banner lỗi khiến người dùng tin
    //      bộ lọc mới đã áp; view có nghĩa vụ dọn rows về 0 — INV-UX3-5)
    const b = mountShell({ errorMessage: 'Máy chủ trả về 500.', isEmpty: false })
    expect(b.attributes('data-state')).toBe('error')
    expect(b.find('[data-testid="list-content"]').exists()).toBe(false)
    expect(b.find('[data-testid="t-data"]').exists()).toBe(false)
  })

  it('TC-UX3-03b: chuỗi lỗi chỉ có khoảng trắng KHÔNG tính là lỗi', () => {
    const w = mountShell({ errorMessage: '   ', isEmpty: true })
    expect(w.attributes('data-state')).toBe('empty')
  })

  it('TC-UX3-04: rỗng ⇒ ui-empty + tiêu đề/hướng dẫn + slot empty-action', () => {
    const w = mountShell({
      isEmpty: true,
      emptyTitle: 'Chưa có đơn hàng nào',
      emptyHint: 'Hãy tạo đơn hàng mới hoặc xoá bộ lọc để xem tất cả.',
    })
    expect(w.attributes('data-state')).toBe('empty')
    expect(w.text()).toContain('Chưa có đơn hàng nào')
    expect(w.text()).toContain('Hãy tạo đơn hàng mới hoặc xoá bộ lọc để xem tất cả.')
    expect(w.find('[data-testid="t-empty-action"]').exists()).toBe(true)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('TC-UX3-05: có dữ liệu ⇒ toolbar + slot mặc định + phân trang; vùng dữ liệu bọc overflow-x-auto', () => {
    const w = mountShell()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="t-toolbar"]').exists()).toBe(true)
    expect(w.find('[data-testid="t-data"]').exists()).toBe(true)
    expect(w.find('[data-testid="t-pagination"]').exists()).toBe(true)
    // bảng rộng phải cuộn TRONG khung của nó, không làm cuộn ngang cả trang
    const dataBox = w.find('[data-testid="list-data"]')
    expect(dataBox.exists()).toBe(true)
    expect(dataBox.classes()).toContain('overflow-x-auto')
    expect(dataBox.find('[data-testid="t-data"]').exists()).toBe(true)
  })

  it('TC-UX3-05b: slot pagination CHỈ render khi có dữ liệu', () => {
    for (const props of [{ loading: true }, { errorMessage: 'X' }, { isEmpty: true }]) {
      const w = mountShell(props)
      expect(w.find('[data-testid="t-pagination"]').exists(),
        `pagination không được render ở ${JSON.stringify(props)}`).toBe(false)
      expect(w.find('[data-testid="t-toolbar"]').exists()).toBe(false)
      w.unmount()
    }
  })

  it('TC-UX3-06: nút «Thử lại» ở trạng thái lỗi, bấm ⇒ emit retry ĐÚNG 1 lần', async () => {
    const w = mountShell({ errorMessage: 'Lỗi mạng.' })
    const btns = retryControls(w)
    expect(btns).toHaveLength(1)
    await btns[0].trigger('click')
    expect(w.emitted('retry')).toHaveLength(1)
  })

  it('TC-UX3-07: slot header + filters render ở CẢ 4 trạng thái; summary chỉ ở rỗng/có dữ liệu', () => {
    const cases: Array<[Props, boolean]> = [
      [{ loading: true }, false],
      [{ errorMessage: 'X' }, false],
      [{ isEmpty: true }, true],
      [{}, true],
    ]
    for (const [props, summaryVisible] of cases) {
      const w = mountShell(props)
      const where = JSON.stringify(props)
      expect(w.find('[data-testid="t-header"]').exists(), `header ở ${where}`).toBe(true)
      expect(w.find('[data-testid="list-filters"]').exists(), `khung lọc ở ${where}`).toBe(true)
      expect(w.find('[data-testid="t-filters"]').exists(), `bộ lọc ở ${where}`).toBe(true)
      expect(w.find('[data-testid="t-summary"]').exists(), `dải chỉ số ở ${where}`).toBe(summaryVisible)
      w.unmount()
    }
  })

  it('TC-UX3-08: emptyTitle/emptyHint là PROP KHAI — không rò ra DOM khi đang lỗi', () => {
    const w = mountShell({
      errorMessage: 'Máy chủ trả về 500.',
      isEmpty: true,
      emptyTitle: 'Chưa có đơn hàng nào',
      emptyHint: 'Hãy tạo đơn hàng mới.',
    })
    // prop không khai sẽ rơi vào $attrs và in thẳng lên thẻ gốc (§7.1)
    expect(w.html()).not.toContain('Chưa có đơn hàng nào')
    expect(w.html()).not.toContain('empty-title')
    expect(w.html()).not.toContain('emptyTitle')
    expect(w.html()).not.toContain('Hãy tạo đơn hàng mới.')
  })

  it('TC-UX3-09: ĐÚNG 1 control tên «Thử lại» ở trạng thái lỗi, 0 ở 3 trạng thái còn lại', () => {
    expect(retryControls(mountShell({ errorMessage: 'X' }))).toHaveLength(1)
    for (const props of [{ loading: true }, { isEmpty: true }, {}]) {
      expect(retryControls(mountShell(props)),
        `không được có nút Thử lại ở ${JSON.stringify(props)}`).toHaveLength(0)
    }
  })

  it('TC-UX3-09b: errorHint truyền xuống ErrorState; bỏ trống ⇒ câu VI mặc định', () => {
    const custom = mountShell({ errorMessage: 'X', errorHint: 'Kiểm tra kết nối mạng rồi thử lại.' })
    expect(custom.text()).toContain('Kiểm tra kết nối mạng rồi thử lại.')
    const fallback = mountShell({ errorMessage: 'X' })
    expect(fallback.text()).toContain('Vui lòng thử lại hoặc tải lại trang.')
  })
})
