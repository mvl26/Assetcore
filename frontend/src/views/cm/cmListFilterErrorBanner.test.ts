// Copyright (c) 2026, AssetCore Team
// AC-CR-79 / TC-FE-CR79-render (IMM-09) — màn danh sách lệnh sửa chữa khi BE từ chối
// KHOÁ LỌC lạ bằng lỗi 400 **TRONG envelope** (HTTP-200, `success:false`).
//
// Đối xứng với `views/pm/pmListFilterErrorBanner.test.ts`: banner cảnh báo TIẾNG VIỆT
// bằng CHÍNH message BE · bảng GIỮ dữ liệu đang xem · KHÔNG điều hướng/đăng xuất ·
// 0 `console.error` · lối thoát "Đặt lại bộ lọc".
//
// Mock ở tầng **axios** (không mock `@/api/imm09`) ⇒ chạy THẬT
// `frappeGet → unwrap → hydrateApiError`. FE KHÔNG giữ bản sao whitelist khoá lọc
// (SSoT `services/imm09.py::_ALLOWED_FILTER_KEYS`) — chỉ hiển thị lại message BE.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const { httpGet } = vi.hoisted(() => ({ httpGet: vi.fn() }))
vi.mock('@/api/axios', () => ({ default: { get: httpGet, post: vi.fn() } }))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import CMWorkOrderListView from './CMWorkOrderListView.vue'

const ROWS = [{
  name: 'WO-RP-2026-00123', asset_ref: 'ACC-ASS-2026-0002', asset_name: 'Máy X-quang Siemens',
  repair_type: 'Corrective', status: 'Open', priority: 'Urgent', open_datetime: '2026-07-20 08:00:00',
  assigned_to: 'ktv@benhvien.vn', assigned_to_name: 'Trần Kỹ Thuật', sla_breached: 0,
}]
const PAGE_OK = { data: ROWS, pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 } }

/** Message BE (tiếng Việt) — FE chỉ hiển thị lại, không tự dựng. */
const FILTER_MSG =
  "Bộ lọc không hợp lệ: khoá 'khong_ton_tai_abc' không được hỗ trợ. "
  + 'Vui lòng đặt lại bộ lọc rồi thử lại.'

function okEnvelope(data: unknown) {
  return { data: { message: { success: true, data } } }
}
function filterErrorEnvelope() {
  return {
    data: {
      message: {
        success: false, error: FILTER_MSG, code: 'INVALID_FILTER_KEY', http_status: 400,
      },
    },
  }
}

let listEnvelope: () => unknown

const ListFilterBarStub = {
  props: ['search', 'chips', 'show', 'searchPlaceholder'],
  emits: ['update:search', 'apply', 'reset', 'clear-chip'],
  template: '<div><slot name="fields" /></div>',
}
const stubs = {
  PageHeader: true, FilterToggleButton: true, BasePagination: true,
  SkeletonLoader: true, WorkOrderKpiStrip: true, RouterLink: true,
  ListFilterBar: ListFilterBarStub,
}

let consoleErrorSpy: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  setActivePinia(createPinia())
  resetRouteMock()
  listEnvelope = () => okEnvelope(PAGE_OK)
  httpGet.mockReset()
  httpGet.mockImplementation((url: string) => {
    if (url.includes('list_repair_work_orders')) return Promise.resolve(listEnvelope())
    return Promise.resolve(okEnvelope(null))   // KPI strip: null ⇒ strip rỗng
  })
  consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => { consoleErrorSpy.mockRestore() })

describe('CMWorkOrderListView — AC-CR-79 banner khoá lọc không hợp lệ', () => {
  it('envelope lỗi filter ⇒ banner tiếng Việt + BẢNG GIỮ dữ liệu cũ + 0 console.error', async () => {
    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    expect(w.text()).toContain('WO-RP-2026-00123')
    expect(w.find('[data-test="cm-filter-error"]').exists()).toBe(false)

    listEnvelope = () => filterErrorEnvelope()
    await w.findAll('select.form-select')[0].setValue('Open')   // watch → reload(1)
    await flushPromises()

    const banner = w.find('[data-test="cm-filter-error"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain(FILTER_MSG)
    expect(banner.text()).not.toContain('INVALID_FILTER_KEY')
    expect(w.text()).toContain('WO-RP-2026-00123')
    expect(w.find('.alert-error').exists()).toBe(false)
    expect(routerPushSpy()).not.toHaveBeenCalled()
    expect(consoleErrorSpy).not.toHaveBeenCalled()
  })

  it('banner KHÔNG lộ chi tiết SQL của BE (assert phủ định AC1)', async () => {
    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    listEnvelope = () => filterErrorEnvelope()
    await w.findAll('select.form-select')[0].setValue('Open')
    await flushPromises()

    const text = w.find('[data-test="cm-filter-error"]').text()
    for (const leak of ['Unknown column', 'tabAsset Repair', 'OperationalError', 'SELECT']) {
      expect(text).not.toContain(leak)
    }
  })

  it('nút "Đặt lại bộ lọc" khôi phục bộ lọc mặc định ⇒ banner biến mất, bảng có dữ liệu', async () => {
    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    listEnvelope = () => filterErrorEnvelope()
    await w.findAll('select.form-select')[0].setValue('Open')
    await flushPromises()
    expect(w.find('[data-test="cm-filter-error"]').exists()).toBe(true)

    listEnvelope = () => okEnvelope(PAGE_OK)
    const resetBtn = w.find('[data-test="cm-filter-error"] button')
    expect(resetBtn.text()).toBe('Đặt lại bộ lọc')
    await resetBtn.trigger('click')
    await flushPromises()

    expect(w.find('[data-test="cm-filter-error"]').exists()).toBe(false)
    expect(w.text()).toContain('WO-RP-2026-00123')
    const lastCall = httpGet.mock.calls.filter(c => String(c[0]).includes('list_repair_work_orders')).at(-1)!
    const sentFilters = JSON.parse((lastCall[1] as { params: { filters: string } }).params.filters)
    expect(sentFilters).toEqual({})
  })

  it('envelope Y HỆT BE `nthrow(MSG.VAL_INVALID_FILTER_KEY)` (code=INVALID_PARAMS) ⇒ vẫn ra banner', async () => {
    // `utils/notify.nthrow` gửi `code` = BUCKET (INVALID_PARAMS); tên mã thật ở
    // `message_code`. FE phải nhận diện được cả 2 đường, nếu không lỗi filter rơi
    // nhầm nhánh "lỗi nạp" ⇒ trắng bảng.
    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    listEnvelope = () => ({
      data: {
        message: {
          success: false, code: 'INVALID_PARAMS', http_status: 400,
          message_code: 'VAL-INVALID-FILTER-KEY',
          context: { invalid_keys: 'khong_ton_tai_abc', allowed_keys: 'asset_ref, priority, status' },
          error: 'Bộ lọc chứa khoá không được hỗ trợ: khong_ton_tai_abc. '
            + 'Các khoá hợp lệ: asset_ref, priority, status.',
        },
      },
    })
    await w.findAll('select.form-select')[0].setValue('Open')
    await flushPromises()

    expect(w.find('[data-test="cm-filter-error"]').exists()).toBe(true)
    expect(w.find('.alert-error').exists()).toBe(false)
    expect(w.text()).toContain('WO-RP-2026-00123')
  })

  it('lỗi KHÔNG phải filter (500) vẫn đi nhánh lỗi cũ — không nuốt thành cảnh báo', async () => {
    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    listEnvelope = () => ({
      data: { message: { success: false, error: 'Lỗi hệ thống', code: 'INTERNAL_ERROR', http_status: 500 } },
    })
    await w.findAll('select.form-select')[0].setValue('Open')
    await flushPromises()

    expect(w.find('[data-test="cm-filter-error"]').exists()).toBe(false)
    // AC-UX-047 lô 3 (2026-08-04): nhánh lỗi NẠP nay do `ui/ListPageShell` → `ui/ErrorState`
    // render (một nguồn cho cả 40 màn danh sách), thay cho dải `.alert-error` tự chế của màn.
    // Bất biến được canh giữ KHÔNG đổi: lỗi 500 đi nhánh LỖI, không bị nuốt thành cảnh báo lọc.
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.find('[data-testid="list-page-shell"]').attributes('data-state')).toBe('error')
  })

  it('[hợp đồng gửi đi] drill SLA/lỗi-lặp gửi khoá sla_breached + is_repeat_failure — whitelist BE phải phủ đủ', async () => {
    // Input cho AC3/AC4: 2 khoá này KHÔNG nằm trong danh sách 10 khoá "đang dùng
    // thật" của spec, nhưng màn CM THỰC SỰ gửi chúng khi drill từ thẻ MTTR/SLA và
    // thẻ lỗi lặp lại (`?sla_breached=1` / `?is_repeat_failure=1`). Thiếu trong
    // `_ALLOWED_FILTER_KEYS` ⇒ drill THẬT ăn 400 (regression do chính CR này gây ra).
    const { setRouteQuery } = await import('@/test/vueRouterMock')
    setRouteQuery({ sla_breached: '1', is_repeat_failure: '1' })
    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    await w.findAll('select.form-select')[1].setValue('Urgent')   // ưu tiên → priority
    await flushPromises()

    const lastCall = httpGet.mock.calls.filter(c => String(c[0]).includes('list_repair_work_orders')).at(-1)!
    const sentFilters = JSON.parse((lastCall[1] as { params: { filters: string } }).params.filters)
    expect(Object.keys(sentFilters).sort())
      .toEqual(['is_repeat_failure', 'priority', 'sla_breached'])
  })
})
