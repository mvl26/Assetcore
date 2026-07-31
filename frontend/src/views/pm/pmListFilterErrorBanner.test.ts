// Copyright (c) 2026, AssetCore Team
// AC-CR-79 / TC-FE-CR79-render (IMM-08) — màn danh sách phiếu bảo trì định kỳ khi BE
// từ chối KHOÁ LỌC lạ bằng lỗi 400 **TRONG envelope** (HTTP-200, `success:false`).
//
// Hành vi phải đúng (AC6): banner cảnh báo TIẾNG VIỆT dùng CHÍNH message của BE ·
// bảng GIỮ nguyên dữ liệu đang xem (KHÔNG trắng trang) · KHÔNG điều hướng/đăng xuất ·
// 0 `console.error` · có lối thoát "Đặt lại bộ lọc".
//
// FIDELITY: test mock ở tầng **axios**, KHÔNG mock `@/api/imm08` ⇒ chạy THẬT
// `frappeGet → unwrap → hydrateApiError` (đúng đường đi production của envelope lỗi
// Frappe — LL-BE-50) rồi mới tới store và view. Mock ở tầng api-client sẽ bỏ qua
// chính đoạn code đang được sửa.
//
// FE-3 (KHÔNG SSoT thứ hai): test CỐ Ý không assert tập khoá hợp lệ — nó chỉ assert
// FE hiển thị NGUYÊN VĂN message BE. Whitelist khoá là SSoT DUY NHẤT ở
// `services/imm08.py::_ALLOWED_FILTER_KEYS`; parity khoá do guard BE/OAS lo.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { resetRouteMock, routerPushSpy, setRouteQuery } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const { httpGet } = vi.hoisted(() => ({ httpGet: vi.fn() }))
vi.mock('@/api/axios', () => ({ default: { get: httpGet, post: vi.fn() } }))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import PMWorkOrderListView from './PMWorkOrderListView.vue'

// --- Dữ liệu server ---------------------------------------------------------
const ROWS = [{
  name: 'PM-WO-2026-00042', asset_ref: 'ACC-ASS-2026-0001', asset_name: 'Máy thở Dräger',
  pm_type: 'Quarterly', status: 'Open', due_date: '2026-07-20', is_late: 0,
  assigned_to: 'ktv@benhvien.vn', assigned_to_name: 'Trần Kỹ Thuật',
}]
const PAGE_OK = { data: ROWS, pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 } }

/** Message BE (tiếng Việt) — FE chỉ hiển thị lại, không tự dựng. */
const FILTER_MSG =
  "Bộ lọc không hợp lệ: khoá 'khong_ton_tai_abc' không được hỗ trợ. "
  + 'Vui lòng đặt lại bộ lọc rồi thử lại.'

function okEnvelope(data: unknown) {
  return { data: { message: { success: true, data } } }
}
/** Lỗi khoá lọc: HTTP-200 + `success:false` + `http_status:400` (in-envelope). */
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
// DateInput stub "sống" (setValue được) để dựng lại đúng bộ lọc ngày mà màn PM gửi.
const DateInputStub = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<input class="date-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
}
const stubs = {
  PageHeader: true, FilterToggleButton: true, BasePagination: true,
  SkeletonLoader: true, WorkOrderKpiStrip: true, RouterLink: true,
  DateInput: DateInputStub, ListFilterBar: ListFilterBarStub,
}

let consoleErrorSpy: ReturnType<typeof vi.spyOn>

/** Dict `filters` của lần gọi list gần nhất (đã JSON.parse). */
function lastSentFilters(): Record<string, unknown> {
  const call = httpGet.mock.calls.filter(c => String(c[0]).includes('list_pm_work_orders')).at(-1)!
  return JSON.parse((call[1] as { params: { filters: string } }).params.filters)
}

beforeEach(() => {
  setActivePinia(createPinia())
  resetRouteMock()
  listEnvelope = () => okEnvelope(PAGE_OK)
  httpGet.mockReset()
  httpGet.mockImplementation((url: string) => {
    if (url.includes('list_pm_work_orders')) return Promise.resolve(listEnvelope())
    // KPI strip đọc dashboard stats — null ⇒ strip rỗng, không ảnh hưởng ca test.
    return Promise.resolve(okEnvelope(null))
  })
  consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => { consoleErrorSpy.mockRestore() })

describe('PMWorkOrderListView — AC-CR-79 banner khoá lọc không hợp lệ', () => {
  it('envelope lỗi filter ⇒ banner tiếng Việt + BẢNG GIỮ dữ liệu cũ + 0 console.error', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    // Baseline: đã có dữ liệu trên bảng.
    expect(w.text()).toContain('PM-WO-2026-00042')
    expect(w.find('[data-test="pm-filter-error"]').exists()).toBe(false)

    // Lần lọc kế tiếp bị BE từ chối vì khoá lạ.
    listEnvelope = () => filterErrorEnvelope()
    await w.find('select.form-select').setValue('Open')   // watch → reload(1)
    await flushPromises()

    const banner = w.find('[data-test="pm-filter-error"]')
    expect(banner.exists()).toBe(true)
    // Nói THẬT bằng chính lời của BE (không diễn giải lại, không mã lỗi thô).
    expect(banner.text()).toContain(FILTER_MSG)
    expect(banner.text()).not.toContain('INVALID_FILTER_KEY')
    // KHÔNG trắng trang: dòng đang xem còn nguyên, không rơi vào nhánh lỗi nạp.
    expect(w.text()).toContain('PM-WO-2026-00042')
    expect(w.find('.alert-error').exists()).toBe(false)
    // KHÔNG điều hướng / đăng xuất; không nổ console.
    expect(routerPushSpy()).not.toHaveBeenCalled()
    expect(consoleErrorSpy).not.toHaveBeenCalled()
  })

  it('banner KHÔNG lộ chi tiết SQL của BE (assert phủ định AC1)', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    listEnvelope = () => filterErrorEnvelope()
    await w.find('select.form-select').setValue('Open')
    await flushPromises()

    const text = w.find('[data-test="pm-filter-error"]').text()
    for (const leak of ['Unknown column', 'tabPM Work Order', 'OperationalError', 'SELECT']) {
      expect(text).not.toContain(leak)
    }
  })

  it('nút "Đặt lại bộ lọc" khôi phục bộ lọc mặc định ⇒ banner biến mất, bảng có dữ liệu', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    listEnvelope = () => filterErrorEnvelope()
    await w.find('select.form-select').setValue('Open')
    await flushPromises()
    expect(w.find('[data-test="pm-filter-error"]').exists()).toBe(true)

    // BE lành lại khi bộ lọc về mặc định.
    listEnvelope = () => okEnvelope(PAGE_OK)
    const resetBtn = w.find('[data-test="pm-filter-error"] button')
    expect(resetBtn.text()).toBe('Đặt lại bộ lọc')
    await resetBtn.trigger('click')
    await flushPromises()

    expect(w.find('[data-test="pm-filter-error"]').exists()).toBe(false)
    expect(w.text()).toContain('PM-WO-2026-00042')
    // Bộ lọc thật sự về mặc định: lần gọi cuối KHÔNG còn khoá `status`.
    expect(lastSentFilters()).toEqual({})
  })

  it('envelope Y HỆT BE `nthrow(MSG.VAL_INVALID_FILTER_KEY)` (code=INVALID_PARAMS) ⇒ vẫn ra banner', async () => {
    // Fidelity: `utils/notify.nthrow` gửi `code` = BUCKET (INVALID_PARAMS), tên mã
    // thật nằm ở `message_code`. Nếu FE chỉ nhận diện theo `code` thì lỗi filter sẽ
    // rơi nhầm vào nhánh "lỗi nạp" ⇒ trắng bảng. Ca này khoá đúng đường đi thật.
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    listEnvelope = () => ({
      data: {
        message: {
          success: false, code: 'INVALID_PARAMS', http_status: 400,
          message_code: 'VAL-INVALID-FILTER-KEY',
          context: { invalid_keys: 'khong_ton_tai_abc', allowed_keys: 'asset_ref, due_date, status' },
          error: 'Bộ lọc chứa khoá không được hỗ trợ: khong_ton_tai_abc. '
            + 'Các khoá hợp lệ: asset_ref, due_date, status.',
        },
      },
    })
    await w.find('select.form-select').setValue('Open')
    await flushPromises()

    expect(w.find('[data-test="pm-filter-error"]').exists()).toBe(true)
    expect(w.find('.alert-error').exists()).toBe(false)
    expect(w.text()).toContain('PM-WO-2026-00042')
  })

  it('lỗi KHÔNG phải filter (500) vẫn đi nhánh lỗi cũ — không nuốt thành cảnh báo', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    listEnvelope = () => ({
      data: { message: { success: false, error: 'Lỗi hệ thống', code: 'INTERNAL_ERROR', http_status: 500 } },
    })
    await w.find('select.form-select').setValue('Open')
    await flushPromises()

    expect(w.find('[data-test="pm-filter-error"]').exists()).toBe(false)
    expect(w.find('.alert-error').exists()).toBe(true)
  })

  it('[hợp đồng gửi đi] khoảng ngày dùng cột THẬT due_date + toán tử — hết khoá bịa due_date_from/to', async () => {
    // GATE-6c (param phát đi == UI-selection) + AC3. Bug được chặn: 2 khoá
    // `due_date_from`/`due_date_to` KHÔNG tồn tại ở BE (không phải cột PM Work Order,
    // không được `_normalize_filters` dịch) ⇒ bộ lọc "Từ ngày/Đến ngày" trước đây
    // luôn ăn `Unknown column` = HTTP-500. Dạng đúng: `due_date` + [op, value].
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    await w.find('select.form-select').setValue('Open')
    const dates = w.findAll('input.date-input')
    await dates[0].setValue('2026-07-01')            // Từ ngày
    await dates[1].setValue('2026-07-31')            // Đến ngày
    // Ô "Thiết bị" — chọn theo placeholder vì DateInput cũng nhận class form-input
    // (attrs fallthrough) nên `input.form-input` khớp cả 2 ô ngày.
    await w.find('input[placeholder="Mã AC Asset..."]').setValue('ACC-ASS-2026-0001')
    await flushPromises()

    const sent = lastSentFilters()
    expect(Object.keys(sent).sort()).toEqual(['asset_ref', 'due_date', 'status'])
    expect(sent.due_date).toEqual(['between', ['2026-07-01', '2026-07-31']])
    expect(JSON.stringify(sent)).not.toContain('due_date_from')
    expect(JSON.stringify(sent)).not.toContain('due_date_to')
  })

  it('[hợp đồng gửi đi] chỉ 1 đầu khoảng ngày ⇒ toán tử >= / <= trên due_date', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const dates = w.findAll('input.date-input')
    await dates[0].setValue('2026-07-01')
    await flushPromises()
    expect(lastSentFilters().due_date).toEqual(['>=', '2026-07-01'])

    await dates[0].setValue('')
    await dates[1].setValue('2026-07-31')
    await flushPromises()
    expect(lastSentFilters().due_date).toEqual(['<=', '2026-07-31'])
  })

  it('[hợp đồng gửi đi] drill ?due_before ⇒ KHÔNG gửi kèm due_date (BE ghi đè ⇒ nuốt im lặng)', async () => {
    setRouteQuery({ due_before: '2026-08-03' })
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    await w.findAll('input.date-input')[0].setValue('2026-07-01')
    await flushPromises()

    const sent = lastSentFilters()
    expect(sent.due_before).toBe('2026-08-03')
    expect(sent.due_date).toBeUndefined()
  })
})
