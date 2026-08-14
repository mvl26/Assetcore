// Copyright (c) 2026, AssetCore Team
// AC-CR-98 · A9 / INV-CONN-27 — «link tới màn trống» phải NÓI vì sao trống.
//
// Sau khi `services/imm04.list_commissioning` đếm và đọc bằng CÙNG một engine row-scoped,
// Vendor Engineer deep-link `/commissioning?asset=<mã>` tới một thiết bị NGOÀI phạm vi
// được giao sẽ ra 0 dòng THẬT (trước đây rò toàn bộ phiếu của mọi thiết bị được giao).
// Nếu màn danh sách vẫn vẽ khối rỗng vô danh thì người dùng vừa bấm ô ghi "3 bản ghi" lại
// thấy "Không tìm thấy phiếu nào phù hợp." — đúng cái "state chết" vòng này đang diệt.
//
// Vì sao phải mount (không guard tĩnh / không unit logic): điều đang chấm là DOM người
// dùng đọc — có mã thiết bị trong câu, có ĐƯỜNG RA, và khối rỗng vô danh KHÔNG hiện cùng
// lúc (hai câu trả lời khác nhau cho cùng câu hỏi "vì sao trống").
//
// `replace` KHÔNG phải spy trơ: nó ghi lại `routeQuery` đúng như Vue Router thật, nên ca
// TC-FE-CONN-27c đếm được SỐ LẦN nạp (một cú bấm = một request; watcher route là nơi duy
// nhất phát request sau khi URL đổi).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'

const routeQuery = ref<Record<string, string>>({})
const routerReplaceSpy = vi.fn((to: { query?: Record<string, string> }) => {
  routeQuery.value = { ...(to?.query ?? {}) }
})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: routerReplaceSpy }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

/**
 * Store giả CÓ TRẠNG THÁI (không phải spy trơ): `fetchList` cập nhật `pagination` ĐÚNG
 * như backend — `paginate()` **ECHO** tham số `page` và **KHÔNG kẹp** về `total_pages`
 * (`assetcore/utils/pagination.py:45-53`) ⇒ trạng thái «đang ở trang 3 mà tổng 0 dòng»
 * là trạng thái THẬT máy chủ trả về, và đó chính là cái TC-FE-COMM-SE-08 buộc màn danh
 * sách phải tự thoát ra. `serverTotal` tách khỏi số dòng đang hiển thị để TC-FE-COMM-SE-07
 * đo được «tổng của cả bộ lọc» chứ không phải «số dòng của trang này».
 */
const rows = ref<Record<string, unknown>[]>([])
const serverTotal = ref<number | null>(null) // null ⇒ suy từ số dòng (giữ nguyên các ca cũ)
const pageState = ref({ page: 1, page_size: 20, total: 0, total_pages: 0 })
const fetchListSpy = vi.fn(async (_filters?: unknown, page = 1, pageSize = 20) => {
  const size = pageSize || 20
  const total = serverTotal.value ?? rows.value.length
  pageState.value = {
    page: Math.max(1, page),
    page_size: size,
    total,
    total_pages: total ? Math.ceil(total / size) : 0,
  }
})
vi.mock('@/stores/imm04', () => ({
  useCommissioningStore: () => ({
    fetchList: fetchListSpy,
    fetchDashboardStats: vi.fn().mockResolvedValue(undefined),
    refreshList: vi.fn(),
    dashboardStats: null,
    get list() { return rows.value },
    listLoading: false,
    error: null,
    get pagination() { return pageState.value },
  }),
}))

import CommissioningListView from '@/views/commissioning/CommissioningListView.vue'

// ListFilterBar KHÔNG stub: chip «Thiết bị: …» và nút «Xóa tất cả» của nó là phần đường-ra
// mà ca dưới đây phải phân biệt được với nút trong empty-state.
// PageHeader + BasePagination cũng KHÔNG stub: ô «Tổng N phiếu» (TC-FE-COMM-SE-07) và các
// nút chuyển trang (TC-FE-COMM-SE-08) là DOM người dùng đọc/bấm thật, stub đi là chấm rỗng.
const stubs = {
  FilterToggleButton: true,
  SkeletonLoader: true, WorkOrderKpiStrip: true, StatusBadge: true,
  RouterLink: true, 'router-link': true,
}

const ASSET = 'AC-ASSET-2026-00042'
// AC-UX-047 lô 3 (2026-08-04) — màn đã áp `ui/ListPageShell`: chữ rỗng nay có ĐÚNG MỘT nguồn
// (`EmptyState` của khuôn) và ĐỔI NỘI DUNG theo nguyên nhân, thay cho 3 khối rỗng cũ. Vì vậy:
//   · câu rỗng CHUNG lấy theo bảng copy SSoT `docs/ui-ux/02 §14.4` (bỏ dấu chấm cuối);
//   · `list-empty-scoped` GIỮ NGUYÊN tên (02 §14.3 cấm đổi) nhưng nay bọc phần HÀNH ĐỘNG,
//     còn câu giải thích + mã thiết bị nằm ở `ui-empty-title` / `ui-empty-description`.
// Bất biến được canh giữ KHÔNG đổi: rỗng-do-lọc-thiết-bị phải nêu mã thiết bị, phải có lối
// bỏ lọc, và câu rỗng vô danh KHÔNG được hiện cùng lúc.
const GENERIC_EMPTY = 'Chưa có phiếu nghiệm thu lắp đặt nào'
const SCOPED = '[data-testid="list-empty-scoped"]'
const EMPTY_BOX = '[data-testid="ui-empty"]'
const COUNT = '[data-testid="list-count"]'

/** Một dòng danh sách tối thiểu nhưng ĐỦ nhãn hiển thị (không leak mã ra ô tên). */
function makeRow(i: number): Record<string, unknown> {
  return {
    name: `COMM-2026-000${i}`, master_item: `ITEM-${i}`, master_item_name: 'Máy thở Hamilton C6',
    vendor: `SUP-${i}`, vendor_name: 'Công ty A', clinical_dept: `DEP-${i}`, clinical_dept_name: 'Khoa Hồi sức',
    vendor_serial_no: `SN-${i}`, workflow_state: 'Draft', final_asset: ASSET,
    modified: '2026-07-28 10:00:00', expected_installation_date: '2026-07-20',
  }
}

const mounted: VueWrapper[] = []
function mountView(): VueWrapper {
  const w = mount(CommissioningListView, { global: { stubs } }) as VueWrapper
  mounted.push(w)
  return w
}
afterEach(() => { while (mounted.length) mounted.pop()!.unmount() })

/** Nút tìm theo NHÃN người dùng thấy — không theo class/thứ tự DOM. */
function buttonByLabel(w: VueWrapper, label: string) {
  return w.findAll('button').find((b) => b.text().trim() === label)
}

function lastFilters(): Record<string, unknown> {
  const call = fetchListSpy.mock.calls[fetchListSpy.mock.calls.length - 1]
  return (call?.[0] ?? {}) as Record<string, unknown>
}

/** Text đã chuẩn hoá khoảng trắng — đọc như người dùng đọc, không phụ thuộc xuống dòng. */
function squash(t: string): string { return t.replace(/\s+/g, ' ').trim() }

beforeEach(() => {
  routeQuery.value = {}
  rows.value = []
  serverTotal.value = null
  pageState.value = { page: 1, page_size: 20, total: 0, total_pages: 0 }
  fetchListSpy.mockClear()
  routerReplaceSpy.mockClear()
})

describe('AC-CR-98 · A9 — /commissioning empty-state CÓ NGỮ CẢNH', () => {
  // TC-FE-CONN-27a
  it('?asset= + 0 dòng ⇒ empty-state có ngữ cảnh (mã thiết bị + đường ra), KHÔNG có khối rỗng chung', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountView()
    await flushPromises()

    const scoped = w.find(SCOPED)
    expect(scoped.exists(), 'thiếu empty-state có ngữ cảnh ⇒ màn trống vô danh').toBe(true)
    const box = w.find(EMPTY_BOX)
    expect(box.text(), 'empty-state không nêu mã thiết bị đang lọc').toContain(ASSET)
    expect(box.text()).toContain('Không có phiếu nghiệm thu lắp đặt nào của thiết bị')
    expect(
      buttonByLabel(w, 'Xoá bộ lọc thiết bị'),
      'empty-state không có lối thoát «Xoá bộ lọc thiết bị»',
    ).toBeTruthy()
    // Hai khối rỗng KHÔNG được cùng hiện: câu vô danh sẽ mâu thuẫn với câu có ngữ cảnh.
    expect(w.text(), 'khối rỗng vô danh vẫn hiện cạnh empty-state có ngữ cảnh').not.toContain(GENERIC_EMPTY)
  })

  // TC-FE-CONN-27b — 0 hồi quy
  it('KHÔNG có ?asset= + 0 dòng ⇒ giữ empty-state CHUNG, KHÔNG có khối theo ngữ cảnh', async () => {
    const w = mountView()
    await flushPromises()

    expect(w.find(SCOPED).exists(), 'lọt empty-state ngữ cảnh khi không lọc thiết bị').toBe(false)
    expect(w.text()).toContain(GENERIC_EMPTY)
  })

  // TC-FE-CONN-27c
  it('bấm «Xoá bộ lọc thiết bị» ⇒ router.replace bỏ ĐÚNG khoá asset (giữ khoá khác) + nạp lại ĐÚNG 1 lần', async () => {
    routeQuery.value = { asset: ASSET, workflow_state: 'Draft' }
    const w = mountView()
    await flushPromises()
    fetchListSpy.mockClear()

    await buttonByLabel(w, 'Xoá bộ lọc thiết bị')!.trigger('click')
    await flushPromises()

    expect(routerReplaceSpy, 'không đi qua router.replace (reload trang / dựng URL tay?)').toHaveBeenCalledTimes(1)
    const q = routerReplaceSpy.mock.calls[0][0].query as Record<string, string>
    expect(q.asset, 'khoá asset còn trong URL ⇒ F5/back là lọc lại đúng thứ vừa bỏ').toBeUndefined()
    expect(q.workflow_state, 'xoá lây khoá query khác').toBe('Draft')

    expect(fetchListSpy.mock.calls.length, 'một cú bấm phải là MỘT lần nạp').toBe(1)
    expect(lastFilters().final_asset, 'vẫn gửi khoá lọc thiết bị sau khi bỏ').toBeFalsy()
    expect(lastFilters().workflow_state, 'nạp lại mà mất bộ lọc trạng thái').toBe('Draft')

    expect(w.find(SCOPED).exists(), 'empty-state ngữ cảnh còn dính sau khi bỏ lọc').toBe(false)
  })

  it('«Xoá tất cả bộ lọc» hiện khi còn bộ lọc khác ⇒ nạp lại với bộ lọc rỗng, URL sạch khoá asset', async () => {
    routeQuery.value = { asset: ASSET, workflow_state: 'Draft' }
    const w = mountView()
    await flushPromises()
    fetchListSpy.mockClear()

    await buttonByLabel(w, 'Xoá tất cả bộ lọc')!.trigger('click')
    await flushPromises()

    expect(fetchListSpy.mock.calls.length).toBe(1)
    expect(lastFilters()).toEqual({})
    expect(routeQuery.value.asset).toBeUndefined()
  })

  it('chỉ lọc thiết bị (không bộ lọc khác) ⇒ KHÔNG vẽ nút «Xoá tất cả bộ lọc» trùng nghĩa', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountView()
    await flushPromises()

    expect(buttonByLabel(w, 'Xoá bộ lọc thiết bị')).toBeTruthy()
    expect(buttonByLabel(w, 'Xoá tất cả bộ lọc'), 'hai nút cùng nghĩa cạnh nhau').toBeUndefined()
  })

  // Fail-safe: có dữ liệu thì TUYỆT ĐỐI không vẽ câu "không có phiếu nào".
  it('?asset= + CÓ dòng ⇒ không vẽ empty-state nào, bảng vẫn render', async () => {
    routeQuery.value = { asset: ASSET }
    rows.value = [{
      name: 'COMM-2026-0001', master_item: 'ITEM-1', master_item_name: 'Máy thở Hamilton C6',
      vendor: 'SUP-1', vendor_name: 'Công ty A', clinical_dept: 'DEP-1', clinical_dept_name: 'Khoa Hồi sức',
      vendor_serial_no: 'SN-1', workflow_state: 'Draft', final_asset: ASSET, modified: '2026-07-28 10:00:00',
      expected_installation_date: '2026-07-20',
    }]
    const w = mountView()
    await flushPromises()

    expect(w.find(SCOPED).exists()).toBe(false)
    expect(w.text()).not.toContain(GENERIC_EMPTY)
    expect(w.text()).toContain('COMM-2026-0001')
  })

  // LL-FE-53 — empty-state là chữ cho người đọc, không phải khoá kỹ thuật.
  it('LL-FE-53 — empty-state không rò khoá kỹ thuật / tên DocType / trạng thái thô', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountView()
    await flushPromises()

    const html = w.find(EMPTY_BOX).html()
    for (const leak of ['final_asset', 'workflow_state', 'Asset Commissioning', 'Clinical Release']) {
      expect(html, `rò khoá/tên kỹ thuật: ${leak}`).not.toContain(leak)
    }
  })

  // WCAG 2.1 AA — thay đổi kết quả phải được đọc lên; lối thoát phải là <button> thật.
  it('WCAG — empty-state là vùng role="status" aria-live, lối thoát là <button> gõ Tab tới được', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountView()
    await flushPromises()

    // vùng thông báo nay là `EmptyState` của khuôn (`role="status"`, ADR-UX-04) —
    // một nơi giữ hợp đồng a11y cho MỌI màn danh sách thay vì mỗi màn tự khai.
    expect(w.find(SCOPED).exists()).toBe(true)
    expect(w.find(EMPTY_BOX).attributes('role')).toBe('status')
    const btn = buttonByLabel(w, 'Xoá bộ lọc thiết bị')!
    expect(btn.element.tagName).toBe('BUTTON')
    expect(btn.attributes('type')).toBe('button')
  })

  /**
   * TC-FE-COMM-SE-07 — ô đếm phải đọc TỔNG của cả bộ lọc (do máy chủ đếm cùng một engine
   * với các dòng: `services/imm04.list_commissioning` → `count_with_or`), KHÔNG phải số
   * dòng của trang đang xem. Dùng `items.length` là dựng lại đúng lớp lỗi «ô đếm 3 bản ghi
   * ↔ danh sách 2 dòng» mà AC-CR-98 vừa diệt ở backend: người dùng bấm ô đếm rồi tự hỏi
   * số nào mới thật.
   */
  it('TC-FE-COMM-SE-07 — tổng 7 (máy chủ) với 2 dòng đang xem ⇒ «Tổng 7 phiếu» + «Hiển thị 2 / 7 phiếu»', async () => {
    rows.value = [makeRow(1), makeRow(2)]
    serverTotal.value = 7
    const w = mountView()
    await flushPromises()

    const head = squash(w.text())
    expect(head, 'tiêu đề đọc số dòng của trang thay vì tổng do máy chủ đếm').toContain('Tổng 7 phiếu')
    expect(head, 'tiêu đề lấy items.length làm tổng').not.toContain('Tổng 2 phiếu')

    // Khuôn `ListPageShell` phát ô đếm MỘT lần ở `#toolbar` (dùng chung cho cả hai bố cục),
    // thay cho hai bản sao mobile/desktop cũ — một nguồn số, hết cơ hội trôi lệch.
    const counters = w.findAll(COUNT)
    expect(counters.length, 'thiếu ô đếm ở dải công cụ của khuôn danh sách').toBe(1)
    for (const c of counters) {
      expect(squash(c.text()), 'ô đếm không tách «đang xem» khỏi «tổng»').toBe('Hiển thị 2 / 7 phiếu')
    }

    // LL-FE-53 — ô đếm là câu tiếng Việt cho người đọc, không phải khoá kỹ thuật.
    for (const leak of ['pagination', 'total', 'final_asset', 'Asset Commissioning']) {
      expect(squash(counters[0].html()), `rò khoá kỹ thuật: ${leak}`).not.toContain(leak)
    }
  })

  /**
   * TC-FE-COMM-SE-08 — kết quả rỗng ở trang > 1 KHÔNG được để con trỏ trang mắc lại.
   * `paginate()` echo `page` nên máy chủ trả về đúng «trang 3 / 0 trang»: pager tự ẩn, mà
   * mọi lần nạp sau đó (nút «Thử lại» → `refreshList`, hoặc lần lọc kế) vẫn đọc offset 40
   * ⇒ danh sách rỗng vĩnh viễn và lối thoát duy nhất là tải lại trang. Ca này khoá bất
   * biến: rỗng ⇒ nạp lại trang 1, GIỮ bộ lọc thiết bị, và empty-state nói rõ vì sao trống.
   */
  it('TC-FE-COMM-SE-08 — tổng về 0 khi đang ở trang 3 ⇒ tự nạp lại trang 1 + empty-state có ngữ cảnh, không kẹt phân trang', async () => {
    routeQuery.value = { asset: ASSET }
    rows.value = [makeRow(1), makeRow(2), makeRow(3)]
    serverTotal.value = 45 // 45 / 20 ⇒ 3 trang
    const w = mountView()
    await flushPromises()

    const page3 = buttonByLabel(w, '3')
    expect(page3, 'không dựng được cảnh đang-ở-trang-3 (thiếu nút chuyển trang)').toBeTruthy()

    // Giữa hai lần nạp, phạm vi được xem co lại (phiếu bị huỷ / thiết bị ra ngoài phạm vi)
    // ⇒ máy chủ trả 0 dòng nhưng vẫn echo trang 3.
    rows.value = []
    serverTotal.value = 0
    fetchListSpy.mockClear()
    await page3!.trigger('click')
    await flushPromises()

    const requestedPages = fetchListSpy.mock.calls.map((c) => c[1])
    expect(requestedPages, 'không tự nạp lại trang 1 ⇒ con trỏ mắc ở trang 3, chỉ F5 mới thoát').toContain(1)
    expect(requestedPages.length, 'nạp lại lặp vô hạn (watcher tự kích lại chính nó)').toBe(2)
    expect(pageState.value.page, 'trạng thái phân trang vẫn ở trang > 1 sau khi kết quả rỗng').toBe(1)
    expect(lastFilters().final_asset, 'nạp lại mà đánh rơi bộ lọc thiết bị').toBe(ASSET)

    const scoped = w.find(SCOPED)
    expect(scoped.exists(), 'trang rỗng không nói vì sao trống').toBe(true)
    expect(w.find(EMPTY_BOX).text()).toContain(ASSET)
    expect(buttonByLabel(w, 'Xoá bộ lọc thiết bị'), 'empty-state thiếu lối ra').toBeTruthy()
    expect(w.text(), 'khối rỗng vô danh vẫn hiện cạnh empty-state có ngữ cảnh').not.toContain(GENERIC_EMPTY)
    expect(squash(w.text()), 'còn vẽ thanh phân trang trên màn 0 dòng').not.toContain('Trang 1/')
  })
})
