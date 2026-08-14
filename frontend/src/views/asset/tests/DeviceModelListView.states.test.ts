// TC-UX3-14 (AC-UX-047 · lô 1) — /device-models: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-03: `load()` CÓ `catch` gán `error`, nhưng dải `.alert-error`
// (`DeviceModelListView.vue:191`) hiện SONG SONG với bảng — và bảng lúc đó rỗng nên ngay
// bên dưới vẫn in «Không tìm thấy model thiết bị nào.» + KHÔNG có nút thử lại. Người dùng
// đọc câu rỗng trước, kết luận sai là danh mục trống.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listDeviceModelsSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  listDeviceModels: (...a: unknown[]) => listDeviceModelsSpy(...a),
  deleteDeviceModel: vi.fn(),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/composables/useImportWizard', () => ({
  useImportWizard: () => ({ open: vi.fn(), doExport: vi.fn() }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import DeviceModelListView from '@/views/asset/DeviceModelListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'DM-0001', model_name: 'Ventilator V60', manufacturer: 'Philips', medical_device_class: 'Class II', gmdn_code: '12345' },
  { name: 'DM-0002', model_name: 'Monitor MX450', manufacturer: 'Philips', medical_device_class: 'Class I', gmdn_code: '67890' },
]

const stubs = { PageHeader: true, FilterToggleButton: true, ImportWizardModal: true }

async function mountView() {
  const w = mount(DeviceModelListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/device-models — 4 trạng thái loại trừ + thử lại (TC-UX3-14)', () => {
  beforeEach(() => {
    resetRouteMock()
    listDeviceModelsSpy.mockReset().mockResolvedValue({ items: ROWS, pagination: { total: ROWS.length } })
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listDeviceModelsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại» (không còn banner alert-error song song)', async () => {
    listDeviceModelsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Chưa có')
    expect(w.text()).not.toContain('Không tìm thấy model thiết bị nào')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listDeviceModelsSpy.mockResolvedValue({ items: [], pagination: { total: 0 } })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có model thiết bị nào')
    expect(w.find('[data-testid="ui-empty-description"]').exists()).toBe(true)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng trong list-data', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần ⇒ error → content', async () => {
    listDeviceModelsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(listDeviceModelsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listDeviceModelsSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listDeviceModelsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
