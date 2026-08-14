// TC-UX3-23 (AC-UX-047 · lô 2) — /assets: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: banner `.alert-error` (`:365`) hiện SONG SONG với HAI
// khối rỗng («mobile» `:414` và «desktop» `:521`) — API hỏng ⇒ ngay dưới câu lỗi vẫn in
// «Không có thiết bị nào phù hợp» và KHÔNG có nút nạp lại. Trên tập 1430 thiết bị đây là
// màn dễ hiểu nhầm nhất: người dùng tin viện KHÔNG có thiết bị nào khớp bộ lọc.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listAssetsSpy = vi.fn()
/** Mọi endpoint dữ-liệu-tham-chiếu trỏ chung 1 spy để đếm được «lời gọi phụ». */
const refDataSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: `stores/imm00.ts` dùng `import * as api` nên
// module phải giữ đủ mọi export; liệt kê tay sẽ trôi lệch khi lớp API thêm hàm mới.
//
// Hai KIỂU trả khác nhau, phải mô phỏng đúng nếu không `refData.categories` thành
// object và computed `gmdnOptions` nổ `filter is not a function`:
//   • listLocations/Departments/AssetCategories/SlaPolicies → MẢNG trần
//   • listDeviceModels/listSuppliers                        → `{ items: [...] }`
vi.mock('@/api/imm00', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>()
  const refArray = (...a: unknown[]) => refDataSpy(...a).then(() => [])
  const refPaged = (...a: unknown[]) => refDataSpy(...a).then(() => ({ items: [] }))
  return {
    ...actual,
    listAssets: (...a: unknown[]) => listAssetsSpy(...a),
    listLocations: refArray, listDepartments: refArray,
    listAssetCategories: refArray, listSlaPolicies: refArray,
    listDeviceModels: refPaged, listSuppliers: refPaged,
  }
})
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/composables/useImportWizard', () => ({
  useImportWizard: () => ({ open: vi.fn(), doExport: vi.fn() }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import AssetListView from '@/views/asset/AssetListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'AC-ASSET-2026-00001', asset_code: 'TB-001', asset_name: 'Máy thở Hamilton C1',
    category_name: 'Hồi sức cấp cứu', department_name: 'Khoa Hồi sức tích cực',
    lifecycle_status: 'In Use', next_pm_date: '2026-12-01', byt_reg_expiry: '2027-01-01' },
  { name: 'AC-ASSET-2026-00002', asset_code: 'TB-002', asset_name: 'Máy siêu âm GE Logiq',
    category_name: 'Chẩn đoán hình ảnh', department_name: 'Khoa Chẩn đoán hình ảnh',
    lifecycle_status: 'In Use', next_pm_date: '2026-11-01', byt_reg_expiry: '2027-02-01' },
  { name: 'AC-ASSET-2026-00003', asset_code: 'TB-003', asset_name: 'Máy X-quang Siemens',
    category_name: 'Chẩn đoán hình ảnh', department_name: 'Khoa Chẩn đoán hình ảnh',
    lifecycle_status: 'Under Maintenance', next_pm_date: '2026-10-01', byt_reg_expiry: '2027-03-01' },
]
const ok = (rows: unknown[]) => ({ items: rows, pagination: { total: rows.length, page: 1, page_size: 20, total_pages: 1 } })

const stubs = { PageHeader: true, FilterToggleButton: true, ImportWizardModal: true }

async function mountView() {
  const w = mount(AssetListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/assets — 4 trạng thái loại trừ + thử lại (TC-UX3-23)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listAssetsSpy.mockReset().mockResolvedValue(ok(ROWS))
    refDataSpy.mockReset().mockResolvedValue(undefined)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listAssetsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn banner alert-error song song', async () => {
    listAssetsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    // cả HAI khối rỗng cũ (mobile + desktop) đều phải biến mất khỏi trạng thái lỗi
    expect(w.text()).not.toContain('Không có thiết bị nào phù hợp')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listAssetsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có thiết bị nào')
    expect(w.find('[data-testid="ui-empty-description"]').text())
      .toBe('Hãy thêm thiết bị mới hoặc xoá bộ lọc để xem tất cả.')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng trong list-data', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần; dữ-liệu-tham-chiếu KHÔNG nạp lại', async () => {
    listAssetsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listAssetsSpy).toHaveBeenCalledTimes(1)
    const refCallsBefore = refDataSpy.mock.calls.length
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listAssetsSpy).toHaveBeenCalledTimes(2)
    expect(refDataSpy).toHaveBeenCalledTimes(refCallsBefore) // INV-UX3-21
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listAssetsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(f2) 1×403 của dữ-liệu-tham-chiếu KHÔNG làm trắng danh sách (LL-FE-45)', async () => {
    // `onMounted` chạy `Promise.all([fetchList, refData.fetchAll])`; `refData` không có
    // ô lỗi riêng ⇒ nếu nó ném ra ngoài thì cả trang trắng. Danh sách phải sống độc lập.
    refDataSpy.mockRejectedValue(new Error('403 Forbidden'))
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })
})
