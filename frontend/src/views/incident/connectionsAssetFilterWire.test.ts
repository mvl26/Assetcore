// Copyright (c) 2026, AssetCore Team
// AC-CR-91 vòng 5 — «Xem tất cả» phải mở ra danh sách LỌC THẬT (INV-CONNFE5-10/11).
//
// Guard tĩnh (`router/connectionsListParity.test.ts`) chỉ chứng minh view có ĐỌC
// `route.query.asset`. Một view đọc query rồi vứt đi vẫn qua guard đó, còn người dùng
// vẫn thấy danh sách toàn viện — nên bốn vế của hợp đồng D-CR5-7 phải được chấm ở đây:
//   1. khởi tạo state lọc TRƯỚC lần nạp đầu (không nạp-rồi-lọc-lại);
//   2. truyền `asset` xuống store/API;
//   3. chip «Thiết bị: <mã>» + đường bỏ lọc (danh sách lọc câm ≡ "mất dữ liệu");
//   4. đổi `route.query.asset` ⇒ nạp lại đúng bộ lọc mới (drill lần 2 cùng route).
// Kèm LL-FE-53: không khoá kỹ thuật (`asset_ref`/`final_asset`) nào lọt ra giao diện.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'

const mounted: VueWrapper[] = []
function mountTracked(...args: Parameters<typeof mount>): VueWrapper {
  const w = mount(...args) as VueWrapper
  mounted.push(w)
  return w
}
afterEach(() => { while (mounted.length) mounted.pop()!.unmount() })

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const fetchListSpy = vi.fn().mockResolvedValue(undefined)
const fetchStatsSpy = vi.fn().mockResolvedValue(undefined)
const fetchRcasSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm12', () => ({
  useImm12Store: () => ({
    incidents: [],
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 1 },
    loading: false,
    error: null,
    stats: null,
    fetchList: fetchListSpy,
    fetchStats: fetchStatsSpy,
    rcaListItems: [],
    rcaPagination: { page: 1, page_size: 20, total: 0, total_pages: 1 },
    rcaLoading: false,
    rcaError: null,
    fetchRcas: fetchRcasSpy,
  }),
}))

vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import IncidentListView from './IncidentListView.vue'
import RCAListView from './RCAListView.vue'

// ListFilterBar KHÔNG stub: chip lọc là thứ đang được chấm.
const stubs = {
  PageHeader: true, FilterToggleButton: true, BasePagination: true,
  SkeletonLoader: true, WorkOrderKpiStrip: true, SlaBreachBadge: true, RouterLink: true,
}

const ASSET = 'AC-ASSET-2026-00001'

describe('IncidentListView — lọc theo thiết bị từ «Xem tất cả» (?asset=)', () => {
  beforeEach(() => {
    fetchListSpy.mockClear()
    fetchStatsSpy.mockClear()
    routeQuery.value = {}
  })

  it('mount với ?asset=… ⇒ lời gọi API ĐẦU TIÊN đã kèm asset (không nạp-rồi-lọc-lại)', async () => {
    routeQuery.value = { asset: ASSET }
    mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()

    expect(fetchListSpy).toHaveBeenCalledTimes(1)
    expect(fetchListSpy.mock.calls[0][0]?.asset).toBe(ASSET)
  })

  it('DOM hiện chip «Thiết bị: <mã>» + đường bỏ lọc', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()

    expect(w.text()).toContain(`Thiết bị: ${ASSET}`)
    expect(w.text()).toMatch(/Xóa|Bỏ lọc|Đặt lại/i)
  })

  it('asset ĐỘC LẬP với status/severity — cộng dồn, không loại trừ nhau', async () => {
    routeQuery.value = { asset: ASSET, severity: 'Critical' }
    mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()

    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.asset).toBe(ASSET)
    expect(arg?.severity).toBe('Critical')
  })

  it('đổi ?asset= (drill lần 2 cùng route) ⇒ nạp lại đúng bộ lọc mới', async () => {
    routeQuery.value = { asset: ASSET }
    mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()
    fetchListSpy.mockClear()

    routeQuery.value = { asset: 'AC-ASSET-2026-00002' }
    await flushPromises()

    expect(fetchListSpy).toHaveBeenCalled()
    expect(fetchListSpy.mock.calls[0][0]?.asset).toBe('AC-ASSET-2026-00002')
  })

  it('không có ?asset= ⇒ KHÔNG gửi khoá asset (không lọc ngầm)', async () => {
    mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()

    const arg = fetchListSpy.mock.calls[0]?.[0]
    expect(arg?.asset).toBeUndefined()
  })

  it('LL-FE-53 — nhãn/chip không rò khoá kỹ thuật', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()

    for (const leak of ['asset_ref', 'final_asset', 'critical_asset', 'Incident Report']) {
      expect(w.html(), `rò khoá kỹ thuật: ${leak}`).not.toContain(leak)
    }
  })
})

describe('RCAListView — lọc theo thiết bị từ «Xem tất cả» (?asset=)', () => {
  beforeEach(() => {
    fetchRcasSpy.mockClear()
    routeQuery.value = {}
  })

  it('mount với ?asset=… ⇒ lời gọi API ĐẦU TIÊN đã kèm asset', async () => {
    routeQuery.value = { asset: ASSET }
    mountTracked(RCAListView, { global: { stubs } })
    await flushPromises()

    expect(fetchRcasSpy).toHaveBeenCalledTimes(1)
    expect(fetchRcasSpy.mock.calls[0][0]?.asset).toBe(ASSET)
  })

  it('DOM hiện chip «Thiết bị: <mã>» + đường bỏ lọc', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountTracked(RCAListView, { global: { stubs } })
    await flushPromises()

    expect(w.text()).toContain(`Thiết bị: ${ASSET}`)
    expect(w.text()).toMatch(/Xóa|Bỏ lọc|Đặt lại/i)
  })

  it('đổi ?asset= ⇒ nạp lại đúng bộ lọc mới', async () => {
    routeQuery.value = { asset: ASSET }
    mountTracked(RCAListView, { global: { stubs } })
    await flushPromises()
    fetchRcasSpy.mockClear()

    routeQuery.value = { asset: 'AC-ASSET-2026-00002' }
    await flushPromises()

    expect(fetchRcasSpy).toHaveBeenCalled()
    expect(fetchRcasSpy.mock.calls[0][0]?.asset).toBe('AC-ASSET-2026-00002')
  })

  it('không có ?asset= ⇒ KHÔNG gửi khoá asset', async () => {
    mountTracked(RCAListView, { global: { stubs } })
    await flushPromises()

    const arg = fetchRcasSpy.mock.calls[0]?.[0]
    expect(arg?.asset).toBeUndefined()
  })

  it('LL-FE-53 — nhãn/chip không rò khoá kỹ thuật', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountTracked(RCAListView, { global: { stubs } })
    await flushPromises()

    for (const leak of ['asset_ref', 'final_asset', 'critical_asset', 'IMM RCA Record']) {
      expect(w.html(), `rò khoá kỹ thuật: ${leak}`).not.toContain(leak)
    }
  })
})
