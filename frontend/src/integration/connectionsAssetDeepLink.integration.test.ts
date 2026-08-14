// Copyright (c) 2026, AssetCore Team
// AC-CR-95 — 4 màn đích còn lại của «Xem tất cả» học đọc `route.query.asset`.
//
// Mirror `views/incident/connectionsAssetFilterWire.test.ts` (AC-CR-91) sang 4 màn:
//   /commissioning (IMM-04) · /decommissions (IMM-14) · /capas (IMM-16) · /cm/firmware (IMM-09)
//
// Vì sao KHÔNG dùng guard tĩnh cho việc này: `router/connectionsListParity.test.ts` chỉ
// chứng minh file view có CHỨA chuỗi `route.query.asset`. Một view đọc query rồi vứt đi
// — hoặc nạp danh sách TRỐNG trước rồi mới lọc lại — vẫn qua guard đó, còn người dùng
// vừa bấm ô ghi "6 bản ghi" thì thấy toàn bộ hồ sơ của cả viện. Bốn vế của hợp đồng
// D-CR5-7 chỉ chấm được bằng `mount`:
//   (a) lời gọi store/API ĐẦU TIÊN đã mang khoá asset (init TRƯỚC lần nạp đầu);
//   (b) dịch đúng khoá BE của từng màn (`final_asset` cho IMM-04, `asset` cho 3 màn kia);
//   (c) chip «Thiết bị: …» hiện + có đường BỎ lọc (danh sách lọc câm ≡ mất dữ liệu);
//   (d) đổi `route.query.asset` (drill lần 2 CÙNG route ⇒ không remount) ⇒ nạp lại giá trị MỚI.
// Kèm LL-FE-53: 0 khoá kỹ thuật (`final_asset`/`asset_ref`/`critical_asset`) lọt ra HTML.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

const mounted: VueWrapper[] = []
function mountTracked(...args: Parameters<typeof mount>): VueWrapper {
  const w = mount(...args) as VueWrapper
  mounted.push(w)
  return w
}
afterEach(() => { while (mounted.length) mounted.pop()!.unmount() })

// ─── Router: query PHẢN ỨNG được (drill lần 2 không remount component) ───────────
// `replace` KHÔNG phải spy trơ: nó ghi lại `routeQuery` đúng như Vue Router thật. Mock
// trơ che mất một lớp lỗi có thật — bỏ chip gọi `replace` ⇒ `route.query.asset` đổi ⇒
// watcher route CHẠY LẠI ⇒ nạp lần thứ hai (đã bắt tận tay trên dev server 2026-07-28:
// 2 lời gọi `list_capas` cho một cú bấm). Vì vậy các ca dưới đây đếm SỐ LẦN nạp.
const routeQuery = ref<Record<string, string>>({})
const routerReplaceSpy = vi.fn((to: { query?: Record<string, string> }) => {
  routeQuery.value = { ...(to?.query ?? {}) }
})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: routerReplaceSpy }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn(), show: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

const ASSET = 'AC-ASSET-2026-00001'
const ASSET2 = 'AC-ASSET-2026-00002'
const ASSET_NAME = 'Máy thở Hamilton C6'

// ─── IMM-09 · /cm/firmware (api/imm00.listFirmwareCrs) ───────────────────────────
const listFirmwareCrsSpy = vi.fn()
vi.mock('@/api/imm00', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm00')>()
  return { ...actual, listFirmwareCrs: (p: Record<string, unknown>) => listFirmwareCrsSpy(p) }
})

// ─── IMM-16 · /capas (stores/imm00.useCapaStore) ─────────────────────────────────
const capaFetchListSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm00', () => ({
  useCapaStore: () => ({
    capas: [],
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    loading: false,
    error: null,
    fetchList: capaFetchListSpy,
  }),
}))

// ─── IMM-14 · /decommissions (api/imm14.listDecommissions) ───────────────────────
const listDecommissionsSpy = vi.fn()
vi.mock('@/api/imm14', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm14')>()
  return {
    ...actual,
    listDecommissions: (f: Record<string, unknown>, p: number, ps: number) =>
      listDecommissionsSpy(f, p, ps),
  }
})

// ─── IMM-04 · /commissioning (stores/imm04.useCommissioningStore) ────────────────
const commFetchListSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm04', () => ({
  useCommissioningStore: () => ({
    fetchList: commFetchListSpy,
    fetchDashboardStats: vi.fn().mockResolvedValue(undefined),
    refreshList: vi.fn(),
    dashboardStats: null,
    list: [],
    listLoading: false,
    error: null,
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
  }),
}))

import FirmwareCrListView from '@/views/document/FirmwareCrListView.vue'
import CAPAListView from '@/views/incident/CAPAListView.vue'
import DecommissionListView from '@/views/eol/DecommissionListView.vue'
import CommissioningListView from '@/views/commissioning/CommissioningListView.vue'

// ListFilterBar + dải chip KHÔNG stub: chip lọc là thứ đang được chấm.
const stubs = {
  PageHeader: true, FilterToggleButton: true, BasePagination: true,
  SkeletonLoader: true, WorkOrderKpiStrip: true, StatusBadge: true,
  SmartSelect: true, RouterLink: true, 'router-link': true,
}

/** Một màn đích: component + spy round-trip + khoá BE mà màn đó PHẢI phát đi. */
interface Target {
  label: string
  component: unknown
  spy: ReturnType<typeof vi.fn>
  /** Khoá lọc trong payload gửi BE — KHÁC nhau giữa các màn (đây là phép dịch). */
  key: string
  /** Lấy object bộ lọc từ một lời gọi spy (vị trí tham số khác nhau). */
  filtersOf: (call: unknown[]) => Record<string, unknown> | undefined
  /** Reset spy + trả lời mặc định (mỗi client có shape envelope riêng). */
  reset: () => void
}

const firstArg = (call: unknown[]) => call?.[0] as Record<string, unknown> | undefined

const TARGETS: Target[] = [
  {
    label: 'FirmwareCrListView (/cm/firmware)',
    component: FirmwareCrListView,
    spy: listFirmwareCrsSpy,
    key: 'asset',
    filtersOf: firstArg,
    reset: () => {
      listFirmwareCrsSpy.mockReset()
      listFirmwareCrsSpy.mockResolvedValue({
        items: [{ name: 'FCR-2026-0001', asset_ref: ASSET, asset_name: ASSET_NAME, status: 'Draft' }],
        total: 1,
      })
    },
  },
  {
    label: 'CAPAListView (/capas)',
    component: CAPAListView,
    spy: capaFetchListSpy,
    key: 'asset',
    filtersOf: firstArg,
    reset: () => { capaFetchListSpy.mockReset(); capaFetchListSpy.mockResolvedValue(undefined) },
  },
  {
    label: 'DecommissionListView (/decommissions)',
    component: DecommissionListView,
    spy: listDecommissionsSpy,
    key: 'asset',
    filtersOf: firstArg,
    reset: () => {
      listDecommissionsSpy.mockReset()
      listDecommissionsSpy.mockResolvedValue({
        data: [{
          name: 'DECOM-2026-0001', asset: ASSET, asset_name_snapshot: ASSET_NAME,
          workflow_state: 'Draft', disposal_method: 'Huỷ',
          decommissioned_on: null, responsible: 'a@b.test', responsible_name: 'Nguyễn Văn A',
        }],
        pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
      })
    },
  },
  {
    label: 'CommissioningListView (/commissioning)',
    component: CommissioningListView,
    // IMM-04 lọc theo `final_asset` (fieldname Link → AC Asset trên Asset Commissioning);
    // BE `services/imm04._ALLOWED_FILTER_KEYS` đã whitelist khoá này.
    spy: commFetchListSpy,
    key: 'final_asset',
    filtersOf: firstArg,
    reset: () => { commFetchListSpy.mockReset(); commFetchListSpy.mockResolvedValue(undefined) },
  },
]

function resetAll() {
  setActivePinia(createPinia())
  routeQuery.value = {}
  routerReplaceSpy.mockClear()
  for (const t of TARGETS) t.reset()
}

/** Nút bỏ chip «Thiết bị: …» — tìm theo NHÃN người dùng thấy, không theo class/testid. */
function assetChipButton(w: VueWrapper) {
  return w.findAll('button').find((b) => b.text().includes('Thiết bị:'))
}

beforeEach(resetAll)

describe.each(TARGETS)('AC-CR-95 · $label — «Xem tất cả» lọc THẬT theo ?asset=', (t) => {
  // TC-FE-CONN-31 — vế (a)+(b): init TRƯỚC lần nạp đầu, dịch đúng khoá BE.
  it(`mount với ?asset= ⇒ lời gọi ĐẦU TIÊN đã mang '${t.key}' (không nạp-rồi-lọc-lại)`, async () => {
    routeQuery.value = { asset: ASSET }
    mountTracked(t.component as never, { global: { stubs } })
    await flushPromises()

    expect(t.spy).toHaveBeenCalled()
    expect(t.filtersOf(t.spy.mock.calls[0])?.[t.key]).toBe(ASSET)
  })

  it('không có ?asset= ⇒ KHÔNG gửi khoá lọc thiết bị (không lọc ngầm)', async () => {
    mountTracked(t.component as never, { global: { stubs } })
    await flushPromises()

    expect(t.spy).toHaveBeenCalled()
    expect(t.filtersOf(t.spy.mock.calls[0])?.[t.key]).toBeUndefined()
  })

  // TC-FE-CONN-32 — vế (c): chip + đường bỏ lọc. Danh sách lọc CÂM (không nói đang
  // lọc gì, không có đường ra) người dùng đọc thành "mất dữ liệu".
  it('DOM hiện chip «Thiết bị: …» + có đường bỏ lọc', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountTracked(t.component as never, { global: { stubs } })
    await flushPromises()

    expect(w.text()).toContain('Thiết bị:')
    expect(assetChipButton(w), 'không có nút bỏ chip «Thiết bị: …»').toBeTruthy()
  })

  it('bấm bỏ chip ⇒ nạp lại KHÔNG còn khoá lọc thiết bị', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountTracked(t.component as never, { global: { stubs } })
    await flushPromises()
    t.spy.mockClear()

    await assetChipButton(w)!.trigger('click')
    await flushPromises()

    expect(t.spy, 'bỏ chip mà không nạp lại ⇒ bảng vẫn hiện dữ liệu đã lọc').toHaveBeenCalled()
    const last = t.spy.mock.calls[t.spy.mock.calls.length - 1]
    expect(t.filtersOf(last)?.[t.key]).toBeFalsy()
    // Khoá phải rời cả URL, nếu không F5 / back là lọc lại đúng thứ vừa bỏ.
    expect(routerReplaceSpy, 'chip bỏ rồi mà ?asset= còn trong URL').toHaveBeenCalled()
    expect(routeQuery.value.asset, 'URL còn ?asset= sau khi bỏ chip').toBeUndefined()
    // MỘT cú bấm = MỘT lần nạp. `replace()` làm watcher route chạy lại, nên không có
    // chốt chống-lặp thì mỗi lần bỏ chip là 2 request y hệt nhau (đo thật trên dev
    // server) — vô hại về kết quả nhưng là rác request đúng lúc bảng đang tải.
    expect(t.spy.mock.calls.length, 'bỏ chip 1 lần mà nạp nhiều lần (request rác)').toBe(1)
  })

  // TC-FE-CONN-33 — vế (d): drill lần 2 CÙNG route ⇒ router KHÔNG remount component.
  it('đổi ?asset= (drill lần 2 cùng route) ⇒ nạp lại với giá trị MỚI', async () => {
    routeQuery.value = { asset: ASSET }
    mountTracked(t.component as never, { global: { stubs } })
    await flushPromises()
    t.spy.mockClear()

    routeQuery.value = { asset: ASSET2 }
    await flushPromises()

    expect(t.spy, 'view đóng băng ở lần nạp đầu').toHaveBeenCalled()
    const last = t.spy.mock.calls[t.spy.mock.calls.length - 1]
    expect(t.filtersOf(last)?.[t.key]).toBe(ASSET2)
  })

  // TC-FE-CONN-34 — LL-FE-53: khoá kỹ thuật là mã hệ thống, KHÔNG phải chữ cho người đọc.
  it('LL-FE-53 — HTML không rò khoá kỹ thuật', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountTracked(t.component as never, { global: { stubs } })
    await flushPromises()

    for (const leak of ['final_asset', 'asset_ref', 'critical_asset']) {
      expect(w.html(), `rò khoá kỹ thuật: ${leak}`).not.toContain(leak)
    }
  })
})

// Nhãn chip: mã thiết bị là thứ CUỐI CÙNG mới hiện — có tên đọc được thì dùng tên.
describe('AC-CR-95 · nhãn chip ưu tiên tên thiết bị đọc được', () => {
  it('/cm/firmware — chip lấy asset_name của dòng khớp mã', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountTracked(FirmwareCrListView, { global: { stubs } })
    await flushPromises()
    expect(w.text()).toContain(`Thiết bị: ${ASSET_NAME}`)
  })

  it('/decommissions — chip lấy asset_name_snapshot của dòng khớp mã', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountTracked(DecommissionListView, { global: { stubs } })
    await flushPromises()
    expect(w.text()).toContain(`Thiết bị: ${ASSET_NAME}`)
  })

  it('/capas — chưa có tên (danh sách rỗng) ⇒ lùi về MÃ, KHÔNG để chip rỗng', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mountTracked(CAPAListView, { global: { stubs } })
    await flushPromises()
    expect(w.text()).toContain(`Thiết bị: ${ASSET}`)
  })
})

// Lọc thiết bị phải CỘNG DỒN với bộ lọc sẵn có, không loại trừ nhau (chống clobber).
describe('AC-CR-95 · asset cộng dồn với bộ lọc khác', () => {
  it('/capas — ?asset= + ?not_closed=1 ⇒ gửi CẢ HAI', async () => {
    routeQuery.value = { asset: ASSET, not_closed: '1' }
    mountTracked(CAPAListView, { global: { stubs } })
    await flushPromises()

    const arg = firstArg(capaFetchListSpy.mock.calls[0])
    expect(arg?.asset).toBe(ASSET)
    expect(arg?.not_closed).toBe(1)
  })

  it('/commissioning — ?asset= + ?workflow_state= ⇒ gửi CẢ HAI', async () => {
    routeQuery.value = { asset: ASSET, workflow_state: 'Clinical Release' }
    mountTracked(CommissioningListView, { global: { stubs } })
    await flushPromises()

    const arg = firstArg(commFetchListSpy.mock.calls[0])
    expect(arg?.final_asset).toBe(ASSET)
    expect(arg?.workflow_state).toBe('Clinical Release')
  })
})
