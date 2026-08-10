// TC-UX3-37 (AC-UX-047 · lô 3) — /service-contracts: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04 (loại β — BẢNG RỖNG KHI LỖI, docs/ui-ux/02 §14.4):
// `ServiceContractListView.vue:209` gắn thêm điều kiện `&& !error` vào nhánh rỗng ⇒ khi nạp
// hỏng, trạng thái rơi thẳng xuống `<template v-else>` `:215` và view in **bảng 0 dòng** kèm
// dòng đếm «Hiển thị 0 / 0 hợp đồng» ngay dưới banner đỏ — ba tín hiệu mâu thuẫn cùng màn.
//
// Bẫy thứ hai (`:90` `if (res)`): `frappeGet` trả `null` khi BE trả `message: null` ⇒ KHÔNG vào
// `catch`, `contracts` giữ giá trị cũ và `error` rỗng ⇒ màn rỗng CÂM, không lối thử lại.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const frappeGetSpy = vi.fn()

vi.mock('@/api/helpers', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  frappeGet: (...a: unknown[]) => frappeGetSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import ServiceContractListView from './ServiceContractListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  {
    name: 'SC-2026-0001', contract_title: 'Bảo trì hệ thống máy thở',
    supplier: 'SUP-2026-00001', supplier_name: 'Công ty Thiết bị Y tế An Bình',
    contract_type: 'Preventive Maintenance', contract_start: '2026-01-01',
    contract_end: '2026-12-31', sla_response_hours: 8,
  },
  {
    name: 'SC-2026-0002', contract_title: 'Hiệu chuẩn thiết bị xét nghiệm',
    supplier: 'SUP-2026-00002', supplier_name: 'Công ty Hiệu chuẩn Miền Nam',
    contract_type: 'Calibration', contract_start: '2026-03-01',
    contract_end: '2027-02-28', sla_response_hours: 24,
  },
]
const ok = (rows: unknown[]) => ({ items: rows, pagination: { total: rows.length } })

const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  FilterToggleButton: true,
  ImportWizardModal: true,
}

async function mountView() {
  const w = mount(ServiceContractListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/service-contracts — 4 trạng thái loại trừ + thử lại (TC-UX3-37)', () => {
  beforeEach(() => {
    resetRouteMock()
    frappeGetSpy.mockReset().mockResolvedValue(ok(ROWS))
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    frappeGetSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», 0 khối rỗng', async () => {
    frappeGetSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(j) TC RED — lỗi KHÔNG được in bảng 0 dòng kèm dòng đếm', async () => {
    // Bằng chứng lỗi THẬT trên đĩa: `&& !error` đẩy trạng thái lỗi vào nhánh `v-else` `:215`.
    frappeGetSpy.mockRejectedValue(new Error('Mất kết nối máy chủ.'))
    const w = await mountView()
    expect(w.findAll('table')).toHaveLength(0)
    expect(w.text()).not.toContain('Hiển thị')
    expect(w.text()).not.toContain('Chưa có hợp đồng dịch vụ nào')
  })

  it('(j2) TC RED — BE trả `message: null` ⇒ vẫn phải có lối thử lại, không rỗng câm', async () => {
    // `if (res)` `:90` nuốt ca `null`: không `catch`, không lỗi ⇒ màn rỗng không đường thoát.
    frappeGetSpy.mockResolvedValue(null)
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    frappeGetSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có hợp đồng dịch vụ nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Hợp đồng dịch vụ là căn cứ theo dõi hạn bảo hành, bảo trì và hiệu chuẩn theo nhà cung cấp.',
    )
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng, 0 rỗng/lỗi', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» phát emit retry ⇒ gọi lại đúng 1 lần, error → content', async () => {
    frappeGetSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(frappeGetSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(frappeGetSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    frappeGetSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content'].filter((t) =>
      w.find(`[data-testid="${t}"]`).exists(),
    )
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
