// AC-CR-96 — Tab «Lịch sử» (dòng thời gian vòng đời) của Chi tiết tài sản HẾT CẮT IM LẶNG.
//
// Trước vòng này `loadTimeline()` gọi `getAssetTimeline(id, 1, 100)` rồi CAST MÙ
// (`as unknown as { items?: … }`) và VỨT `pagination.total`: asset có 137 sự kiện chỉ
// render 100 dòng mà KHÔNG một dấu hiệu nào cho biết đã bị cắt — người dùng kết luận
// "thiết bị chỉ có 100 sự kiện" (hồ sơ NĐ98 thiếu vết mà không ai biết).
//
// Hợp đồng khoá ở đây (SSoT = `pagination` của BE `imm00.get_asset_timeline`):
//   A2  TỔNG THẬT     — `timeline-total` = `pagination.total` (SERVER), KHÔNG `items.length`.
//   A3  cắt ⟺ báo cắt  — `timeline-load-more` + dải "Đang xem X/Y" tồn tại ⟺ `length < total`.
//   A4  phân trang THẬT — «Tải thêm» gọi page+1 với page_size GIỮ NGUYÊN 100 (trần
//                        `utils/pagination.py::_MAX_PAGE_SIZE`), APPEND + dedupe theo `name`.
//   A5  "chưa tải" ≠ "chưa có" — API lỗi ⇒ dải lỗi VI, KHÔNG empty-state "Chưa có sự kiện".
//   A6  KHÔNG regress mount lười — tab `info` ⇒ 0 request timeline.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: { id: 'ASSET-0001' }, query: {} }),
}))

const currentAsset = { name: 'ASSET-0001', asset_name: 'Máy thở A', lifecycle_status: 'Active' }
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset, loading: false, error: null,
    fetchOne: vi.fn().mockResolvedValue(undefined),
    transition: vi.fn().mockResolvedValue({ success: true }),
  }),
}))

const getAssetTimelineSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: (...a: unknown[]) => getAssetTimelineSpy(...a),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue({ valid: true, count: 3 }),
  deleteAsset: vi.fn().mockResolvedValue(undefined),
  getAssetLabelData: vi.fn().mockResolvedValue({}),
  markLabelPrinted: vi.fn(),
  regenerateAssetQrToken: vi.fn(),
  printAssetLabelsPdf: vi.fn(),
  LABEL_PDF_PRESETS: [{ key: 'tem-60x100', label: 'Tem 60×100mm' }],
  LABEL_PDF_PRESET: 'tem-60x100',
  labelPdfPresetLabel: () => 'Tem 60×100mm',
}))
vi.mock('@/api/imm04', () => ({ getCommissioningOrigin: vi.fn().mockResolvedValue(null) }))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => false }) }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: { email: 'tech@hosp.vn' } }) }))

import AssetDetailView from '@/views/asset/AssetDetailView.vue'

const RouterLinkStub = { props: ['to'], template: '<a :data-to="to"><slot /></a>' }
const stubs = {
  PageHeader: true, AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
  RelatedRecords: true, RouterLink: RouterLinkStub, 'router-link': RouterLinkStub,
}

/** 1 dòng Asset Lifecycle Event tối thiểu — `name` DUY NHẤT để đo dedupe. */
function ev(i: number) {
  return {
    name: `ALE-${String(i).padStart(4, '0')}`,
    event_type: 'pm_completed',
    actor: '', actor_name: '',
    from_status: '', to_status: '',
    timestamp: '2026-07-01 08:00:00', event_timestamp: '',
    root_doctype: '', root_record: '', notes: '',
  }
}
function evRange(from: number, to: number) {
  return Array.from({ length: to - from + 1 }, (_, k) => ev(from + k))
}
function page<T>(items: T[], p: number, total: number, pageSize = 100) {
  return {
    pagination: {
      page: p, page_size: pageSize, total,
      total_pages: Math.ceil(total / pageSize), offset: (p - 1) * pageSize,
    },
    items,
  }
}

async function mountAsset() {
  const wrapper = mount(AssetDetailView, { props: { id: 'ASSET-0001' }, global: { stubs } })
  await flushPromises()
  return wrapper
}
async function openTimeline() {
  const wrapper = await mountAsset()
  await wrapper.find('[data-testid="tab-timeline"]').trigger('click')
  await flushPromises()
  return wrapper
}

describe('AC-CR-96 — tab «Lịch sử»: TỔNG THẬT + «Tải thêm» (hết cắt im lặng)', () => {
  beforeEach(() => {
    getAssetTimelineSpy.mockReset()
  })

  // ── TC-1 (A2, A3): tổng = pagination.total (137) dù trang 1 chỉ có 100 dòng ──
  it('TC-1: total=137 / trang 1 = 100 dòng ⇒ "137 sự kiện" + "Đang xem 100/137" + có «Tải thêm»', async () => {
    getAssetTimelineSpy.mockResolvedValue(page(evRange(1, 100), 1, 137))
    const wrapper = await openTimeline()

    const total = wrapper.find('[data-testid="timeline-total"]')
    expect(total.exists()).toBe(true)
    // TỔNG THẬT từ SERVER — nếu FE lấy timeline.length sẽ ra "100 sự kiện" ⇒ ĐỎ.
    expect(total.text()).toContain('137 sự kiện')
    expect(wrapper.text()).toContain('Đang xem 100/137')
    expect(wrapper.find('[data-testid="timeline-load-more"]').exists()).toBe(true)
    // 100 dòng render (đúng số dòng đã tải, KHÔNG phải tổng).
    expect(wrapper.findAll('[data-testid="timeline-event"]').length).toBe(100)
  })

  // ── TC-2 (A4): «Tải thêm» = phân trang THẬT — page 2, page_size GIỮ 100, APPEND + dedupe ──
  it('TC-2: bấm «Tải thêm» ⇒ gọi page=2 & page_size=100, append + dedupe ⇒ 137 dòng, nút biến mất', async () => {
    // Trang 2 CỐ TÌNH trả lại `ALE-0100` (event mới chèn đầu ⇒ cửa sổ trượt 1 dòng):
    // dedupe theo `name` phải giữ đúng 137 dòng, KHÔNG nhân bản thành 138.
    getAssetTimelineSpy
      .mockResolvedValueOnce(page(evRange(1, 100), 1, 137))
      .mockResolvedValueOnce(page([ev(100), ...evRange(101, 137)], 2, 137))
    const wrapper = await openTimeline()

    expect(getAssetTimelineSpy).toHaveBeenCalledTimes(1)
    await wrapper.find('[data-testid="timeline-load-more"]').trigger('click')
    await flushPromises()

    // Tham số phát đi == phân trang thật (chống dead-control LL-FE-47):
    expect(getAssetTimelineSpy).toHaveBeenCalledTimes(2)
    const [, p2, size2] = getAssetTimelineSpy.mock.calls[1]
    expect(p2).toBe(2)
    expect(size2).toBe(100) // GIỮ trần _MAX_PAGE_SIZE — KHÔNG đổi page_size giữa 2 trang

    const rows = wrapper.findAll('[data-testid="timeline-event"]')
    expect(rows.length).toBe(137)                                     // count == drill
    const names = new Set(rows.map(r => r.attributes('data-name')))
    expect(names.size).toBe(137)                                      // 0 dòng trùng
    // Trang 1 KHÔNG bị thay thế (append thật, không reset).
    expect(names.has('ALE-0001')).toBe(true)
    expect(names.has('ALE-0137')).toBe(true)
    // Đã tải hết ⇒ tắt cả nút lẫn dải "Đang xem".
    expect(wrapper.find('[data-testid="timeline-load-more"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Đang xem')
    expect(wrapper.find('[data-testid="timeline-total"]').text()).toContain('137 sự kiện')
  })

  // ── TC-3 (A3): không cắt thì KHÔNG báo cắt (chống "cắt oan") ──
  it('TC-3: total=7 & đã tải 7 ⇒ "7 sự kiện", KHÔNG «Tải thêm», KHÔNG "Đang xem"', async () => {
    getAssetTimelineSpy.mockResolvedValue(page(evRange(1, 7), 1, 7))
    const wrapper = await openTimeline()

    expect(wrapper.find('[data-testid="timeline-total"]').text()).toContain('7 sự kiện')
    expect(wrapper.find('[data-testid="timeline-load-more"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Đang xem')
    expect(wrapper.findAll('[data-testid="timeline-event"]').length).toBe(7)
  })

  // ── TC-4 (A5): "chưa tải" ≠ "chưa có" ──
  it('TC-4a: API lỗi ⇒ dải lỗi tiếng Việt, KHÔNG hiện "Chưa có sự kiện vòng đời"', async () => {
    getAssetTimelineSpy.mockRejectedValue(new Error('boom'))
    const wrapper = await openTimeline()

    const err = wrapper.find('[data-testid="timeline-error"]')
    expect(err.exists()).toBe(true)
    expect(err.text()).toContain('Không tải được dòng thời gian')
    expect(wrapper.text()).not.toContain('Chưa có sự kiện vòng đời')
    // KHÔNG leak thông điệp kỹ thuật thô ra giao diện.
    expect(wrapper.text()).not.toContain('boom')
  })

  it('TC-4b: total=0 THẬT ⇒ giữ empty-state cũ, KHÔNG hiện dải lỗi', async () => {
    getAssetTimelineSpy.mockResolvedValue(page([], 1, 0))
    const wrapper = await openTimeline()

    expect(wrapper.text()).toContain('Chưa có sự kiện vòng đời')
    expect(wrapper.find('[data-testid="timeline-error"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="timeline-load-more"]').exists()).toBe(false)
  })

  // ── TC-6 (LL-FE-47): «Tải thêm» KHÔNG được thành NÚT CHẾT ──
  // Nếu BE lệch count/rows (COUNT không lọc quyền mà rows có lọc — lớp bug
  // "count != drill"), trang kế trả 0 dòng trong khi `total` vẫn 137: nút phải
  // NGƯNG mời bấm, nhưng dải "Đang xem" GIỮ tổng thật (không giả vờ đã xem hết).
  it('TC-6: trang kế trả 0 dòng dù total=137 ⇒ nút biến mất, "Đang xem 100/137" vẫn giữ', async () => {
    getAssetTimelineSpy
      .mockResolvedValueOnce(page(evRange(1, 100), 1, 137))
      .mockResolvedValueOnce(page([], 2, 137))
    const wrapper = await openTimeline()

    await wrapper.find('[data-testid="timeline-load-more"]').trigger('click')
    await flushPromises()

    expect(getAssetTimelineSpy).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[data-testid="timeline-load-more"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="timeline-total"]').text()).toContain('137 sự kiện')
    expect(wrapper.text()).toContain('Đang xem 100/137')
    // Dữ liệu đã tải KHÔNG bị xoá.
    expect(wrapper.findAll('[data-testid="timeline-event"]').length).toBe(100)
  })

  // ── TC-5 (A6): mount lười KHÔNG regress ──
  it('TC-5: mount ở tab «Thông tin» ⇒ 0 lần gọi; chỉ khi mở tab mới gọi đúng 1 lần page=1', async () => {
    getAssetTimelineSpy.mockResolvedValue(page(evRange(1, 3), 1, 3))
    const wrapper = await mountAsset()
    expect(getAssetTimelineSpy).toHaveBeenCalledTimes(0)

    await wrapper.find('[data-testid="tab-timeline"]').trigger('click')
    await flushPromises()
    expect(getAssetTimelineSpy).toHaveBeenCalledTimes(1)
    const [, p1, size1] = getAssetTimelineSpy.mock.calls[0]
    expect(p1).toBe(1)
    expect(size1).toBe(100)

    // Rời tab rồi quay lại KHÔNG nạp lại (dữ liệu đã có) — giữ hợp đồng lười cũ.
    await wrapper.find('[data-testid="tab-info"]').trigger('click')
    await wrapper.find('[data-testid="tab-timeline"]').trigger('click')
    await flushPromises()
    expect(getAssetTimelineSpy).toHaveBeenCalledTimes(1)
  })
})
