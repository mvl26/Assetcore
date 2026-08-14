// TC-CONNFE6-3/4 (AC-CR-94) — deep-link «Xem tất cả» ĐẾN ĐÍCH cho màn Lịch bảo trì định kỳ.
//
// Vì sao file này tồn tại: ô «Lịch bảo trì định kỳ» trong tab «Bản ghi liên quan» của một
// thiết bị báo N, nhưng `/pm/schedules` KHÔNG đọc khoá nào ⇒ bấm «Xem tất cả» mở ra lịch
// của CẢ VIỆN (hoặc nút bị ẩn hẳn). Bất biến bị vỡ là count == drill mà
// `ADR-IMM00-LIST-SCOPE §4b` viện dẫn — và nó vỡ ở lớp UI, nơi vitest cũ không canh.
//
// Bốn điều được khoá ở đây:
//   (a) tham số gửi BE CHỨA `asset` và KHÔNG có `status`/`pm_type` mặc định — nếu view tự
//       thêm `status: 'Active'` thì lịch Paused/Suspended rơi ra ⇒ 3 ô ≠ 2 dòng;
//   (b) DOM render ĐÚNG số dòng BE trả (kể cả Paused) — count == drill ở lớp UI;
//   (c) mọi dòng thuộc ĐÚNG thiết bị gốc (không lẫn hồ sơ thiết bị khác);
//   (d) chip tiếng Việt «Thiết bị: …» hiện ra và bỏ được (0 lọc ẩn treo lại).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const routeQuery = ref<Record<string, string>>({})
const replaceSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: (...a: unknown[]) => replaceSpy(...a) }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const ASSET = 'AC-ASSET-X'
// 3 lịch CÙNG thiết bị: 2 Active + 1 Paused ⇒ nếu view lọc status thì chỉ còn 2 dòng.
const ROWS = [
  {
    name: 'PMS-0001', asset_ref: ASSET, asset_name: 'Máy thở ICU giường 1',
    pm_type: 'Quarterly', status: 'Active', pm_interval_days: 90, next_due_date: '2026-09-01',
  },
  {
    name: 'PMS-0002', asset_ref: ASSET, asset_name: 'Máy thở ICU giường 1',
    pm_type: 'Annual', status: 'Active', pm_interval_days: 365, next_due_date: '2026-12-01',
  },
  {
    name: 'PMS-0003', asset_ref: ASSET, asset_name: 'Máy thở ICU giường 1',
    pm_type: 'Ad-hoc', status: 'Paused', pm_interval_days: 0, next_due_date: '2027-01-15',
  },
]

const listSpy = vi.fn().mockResolvedValue({ items: ROWS, total: ROWS.length, page: 1, page_size: 30 })
vi.mock('@/api/imm00', () => ({
  listPmSchedules: (...a: unknown[]) => listSpy(...a),
  getPmSchedule: vi.fn(),
  createPmSchedule: vi.fn(),
  updatePmSchedule: vi.fn(),
  deletePmSchedule: vi.fn(),
}))

const fetchDoctypeSpy = vi.fn().mockResolvedValue([])
vi.mock('@/stores/masterData', () => ({
  useMasterDataStore: () => ({ fetchDoctype: (...a: unknown[]) => fetchDoctypeSpy(...a) }),
}))
vi.mock('@/stores/acUsers', () => ({
  useAcUserStore: () => ({ prefetch: vi.fn().mockResolvedValue([]), label: (v?: string) => v || '—' }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ can: () => true }),
}))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    // run() phải THẬT SỰ gọi fn — nếu stub trả sẵn dữ liệu thì test không còn chứng
    // minh được view gửi tham số nào xuống BE.
    run: async (fn: () => Promise<unknown>) => {
      try { return await fn() } catch { return null }
    },
    lastError: ref(null),
  }),
}))

// ListFilterBar để THẬT (không stub) — chip là DOM cần assert, stub hoá sẽ tự-chứng-minh.
const stubs = {
  PageHeader: true, FilterToggleButton: true, SkeletonLoader: true,
  SmartSelect: true, ApproverSelect: true, DateInput: true,
}

import PmScheduleListView from '@/views/pm/PmScheduleListView.vue'

function lastParams(): Record<string, unknown> {
  const call = listSpy.mock.calls[listSpy.mock.calls.length - 1]
  return (call?.[0] ?? {}) as Record<string, unknown>
}

/** Chờ debounce 300ms của watcher filters (view gộp mọi thay đổi lọc vào 1 request). */
async function settleDebounce() {
  await new Promise((r) => setTimeout(r, 360))
  await flushPromises()
}

describe('PmScheduleListView — deep-link ?asset= (TC-CONNFE6-3)', () => {
  beforeEach(() => {
    listSpy.mockClear()
    replaceSpy.mockClear()
    listSpy.mockResolvedValue({ items: ROWS, total: ROWS.length, page: 1, page_size: 30 })
    routeQuery.value = {}
  })

  it('(a) gửi BE `asset` và KHÔNG tự thêm status/pm_type (lịch Paused vẫn phải hiện)', async () => {
    routeQuery.value = { asset: ASSET }
    mount(PmScheduleListView, { global: { stubs } })
    await flushPromises()

    expect(listSpy).toHaveBeenCalled()
    const p = lastParams()
    expect(p.asset).toBe(ASSET)
    expect(p.status, 'view tự thêm status ⇒ lịch Paused/Suspended rơi ra, count ô ≠ số dòng')
      .toBeUndefined()
    expect(p.pm_type).toBeUndefined()
  })

  it('(b) DOM render ĐÚNG 3 dòng — kể cả dòng Paused (count == drill ở lớp UI)', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mount(PmScheduleListView, { global: { stubs } })
    await flushPromises()

    const rows = w.findAll('tbody tr')
    expect(rows.length).toBe(3)
    expect(w.text()).toContain('Tạm dừng')   // nhãn VI của status Paused
  })

  it('(c) mọi dòng render thuộc ĐÚNG thiết bị gốc', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mount(PmScheduleListView, { global: { stubs } })
    await flushPromises()

    const rows = w.findAll('tbody tr')
    expect(rows.length).toBe(3)
    for (const r of rows) expect(r.text()).toContain(ASSET)
  })

  it('(d) chip tiếng Việt «Thiết bị: …» hiện ra, không lộ khoá kỹ thuật', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mount(PmScheduleListView, { global: { stubs } })
    await flushPromises()

    const chip = w.findAll('button').map((b) => b.text()).find((t) => t.includes('Thiết bị'))
    expect(chip, 'không thấy chip «Thiết bị: …» ⇒ người dùng không biết đang bị lọc').toBeTruthy()
    expect(chip).toContain('Máy thở ICU giường 1')
    expect(chip?.toLowerCase()).not.toContain('asset_ref')
    expect(chip?.toLowerCase()).not.toMatch(/\basset\b/)
  })

  it('chip lùi về MÃ thiết bị khi BE chưa trả asset_name (không hiện chuỗi rỗng)', async () => {
    listSpy.mockResolvedValue({
      items: [{ name: 'PMS-9', asset_ref: ASSET, pm_type: 'Quarterly', status: 'Active' }],
      total: 1, page: 1, page_size: 30,
    })
    routeQuery.value = { asset: ASSET }
    const w = mount(PmScheduleListView, { global: { stubs } })
    await flushPromises()

    const chip = w.findAll('button').map((b) => b.text()).find((t) => t.includes('Thiết bị'))
    expect(chip).toBe(`Thiết bị: ${ASSET}`)
  })

  // LL-FE-45 / GATE-5 — prefetch tham chiếu PHỤ hỏng KHÔNG được xoá trắng drill.
  it('403 ở prefetch tham chiếu phụ ⇒ VẪN render 3 dòng, KHÔNG banner "Thử lại"', async () => {
    fetchDoctypeSpy.mockRejectedValueOnce(new Error('403 PM Checklist Template'))
    routeQuery.value = { asset: ASSET }
    const w = mount(PmScheduleListView, { global: { stubs } })
    await flushPromises()

    expect(w.findAll('tbody tr').length,
      'một nhánh prefetch phụ 403 làm trắng bảng ⇒ ô báo 3 mà người dùng thấy 0').toBe(3)
    expect(w.text()).not.toContain('Thử lại')
    fetchDoctypeSpy.mockResolvedValue([])
  })

  it('không có query.asset ⇒ KHÔNG gửi khoá asset (màn danh sách chung không bị lọc ngầm)', async () => {
    routeQuery.value = {}
    mount(PmScheduleListView, { global: { stubs } })
    await flushPromises()
    expect(lastParams().asset).toBeUndefined()
  })
})

describe('PmScheduleListView — bỏ chip «Thiết bị» (TC-CONNFE6-4)', () => {
  beforeEach(() => {
    listSpy.mockClear()
    replaceSpy.mockClear()
    listSpy.mockResolvedValue({ items: ROWS, total: ROWS.length, page: 1, page_size: 30 })
    routeQuery.value = { asset: ASSET, foo: 'giu-lai' }
  })

  it('router.replace bỏ query.asset (giữ khoá khác) VÀ lần fetch kế KHÔNG còn asset', async () => {
    const w = mount(PmScheduleListView, { global: { stubs } })
    await flushPromises()
    expect(lastParams().asset).toBe(ASSET)

    const chipBtn = w.findAll('button').find((b) => b.text().includes('Thiết bị'))
    expect(chipBtn, 'không có chip để bỏ').toBeTruthy()
    await chipBtn!.trigger('click')
    await settleDebounce()

    expect(replaceSpy).toHaveBeenCalled()
    const arg = replaceSpy.mock.calls[replaceSpy.mock.calls.length - 1][0] as { query: Record<string, string> }
    expect(arg.query.asset, 'query.asset còn treo trên URL ⇒ F5 là lọc lại').toBeUndefined()
    expect(arg.query.foo).toBe('giu-lai')
    expect(lastParams().asset, '0 lọc ẩn còn treo sau khi user bỏ chip').toBeUndefined()
  })

  it('«Xóa tất cả» cũng dọn query.asset (chip và reset không nói hai giọng)', async () => {
    const w = mount(PmScheduleListView, { global: { stubs } })
    await flushPromises()

    const resetBtn = w.findAll('button').find((b) => b.text().trim() === 'Xóa tất cả')
    expect(resetBtn).toBeTruthy()
    await resetBtn!.trigger('click')
    await settleDebounce()

    expect(replaceSpy).toHaveBeenCalled()
    expect(lastParams().asset).toBeUndefined()
  })
})
