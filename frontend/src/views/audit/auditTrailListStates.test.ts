// TC-UX3-35 (AC-UX-047 · lô 3) — /audit-trail: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04 (loại α — LỖI GIẢ DẠNG RỖNG THẬT, docs/ui-ux/02 §14.4):
// `AuditTrailListView.vue:198` (`v-if="fetchError"`) là một khối ĐỘC LẬP, tách rời khỏi
// chuỗi `v-if="loading"` / `v-else-if="trails.length === 0"` bắt đầu ở `:237`. `catch` `:103`
// gán `trails = []` rồi mới set `fetchError` ⇒ HAI khối cùng render: banner đỏ «Không tải được
// nhật ký kiểm toán» VÀ ngay dưới là minh hoạ «Không có bản ghi kiểm toán nào phù hợp».
// Người dùng đọc câu thứ hai và tin là KHÔNG CÓ BẢN GHI — sự cố im lặng.
//
// Bộ dò `ui-audit-inventory.mjs` chấm màn này ✅ vì nó đo SỰ CÓ MẶT của nút «Thử lại» (`:209`),
// không đo tính LOẠI TRỪ ⇒ phải có phép đo thứ hai (guard AC-UX-070 + file test này).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'

enableAutoUnmount(afterEach)

const frappeGetSpy = vi.fn()
const verifyChainSpy = vi.fn()

// `importOriginal` + ghi đè ĐÚNG hàm nạp: liệt kê tay sẽ trôi lệch ngay khi lớp API thêm
// hàm mới ("No export named …" — bẫy đã gặp ở lô 2).
vi.mock('@/api/helpers', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  frappeGet: (...a: unknown[]) => frappeGetSpy(...a),
}))
vi.mock('@/api/imm00', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  verifyChain: (...a: unknown[]) => verifyChainSpy(...a),
}))

import AuditTrailListView from './AuditTrailListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  {
    name: 'AT-2026-00001', asset: 'AC-ASSET-2026-00001', asset_name: 'Máy thở Hamilton C1',
    event_type: 'State Change', from_status: 'Draft', to_status: 'Active',
    actor: 'Nguyễn Văn A', change_summary: 'Kích hoạt thiết bị',
    timestamp: '2026-07-01 08:00:00', hash: 'a1b2c3d4e5f6a7b8',
  },
  {
    name: 'AT-2026-00002', asset: 'AC-ASSET-2026-00002', asset_name: 'Máy siêu âm GE Logiq',
    event_type: 'Calibration', from_status: '', to_status: '',
    actor: 'Trần Thị B', change_summary: 'Hoàn tất hiệu chuẩn',
    timestamp: '2026-07-02 09:30:00', hash: 'b2c3d4e5f6a7b8c9',
  },
  {
    name: 'AT-2026-00003', asset: '', asset_name: '',
    event_type: 'System', from_status: '', to_status: '',
    actor: 'Hệ thống', change_summary: 'Chạy tác vụ nền',
    timestamp: '2026-07-03 10:15:00', hash: 'c3d4e5f6a7b8c9d0',
  },
]
const ok = (rows: unknown[]) => ({
  items: rows,
  pagination: { total: rows.length, page: 1, page_size: 50, total_pages: 1 },
})

// `SmartSelect` tự nạp danh mục thiết bị qua lớp API riêng — không thuộc phạm vi 4 trạng thái
// của danh sách; stub để lượt gọi của nó không lẫn vào spy nạp danh sách.
const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  FilterToggleButton: true,
  SmartSelect: true,
}

async function mountView() {
  const w = mount(AuditTrailListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/audit-trail — 4 trạng thái loại trừ + thử lại (TC-UX3-35)', () => {
  beforeEach(() => {
    frappeGetSpy.mockReset().mockResolvedValue(ok(ROWS))
    verifyChainSpy.mockReset().mockResolvedValue({ valid: true, count: 3, broken_at: null })
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

  it('(j) TC RED — lỗi KHÔNG được kèm câu rỗng «Không có bản ghi kiểm toán nào phù hợp»', async () => {
    // Bằng chứng lỗi THẬT trên đĩa: banner `:198` và khối rỗng `:240` cùng render.
    frappeGetSpy.mockRejectedValue(new Error('Mất kết nối máy chủ.'))
    const w = await mountView()
    expect(w.text()).not.toContain('Không có bản ghi kiểm toán nào phù hợp')
    expect(w.text()).not.toContain('Chưa có bản ghi kiểm toán nào')
    expect(w.findAll('table')).toHaveLength(0)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    frappeGetSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có bản ghi kiểm toán nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Nhật ký kiểm toán được ghi tự động khi có thao tác trên thiết bị, phiếu bảo trì hoặc hồ sơ chất lượng.',
    )
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng trong list-data, 0 rỗng/lỗi', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần ⇒ error → content', async () => {
    frappeGetSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(frappeGetSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(frappeGetSpy).toHaveBeenCalledTimes(2)
    // «Xác minh chuỗi hash» là hành động ĐỌC-KIỂM-TRA riêng, không ăn theo nút «Thử lại».
    expect(verifyChainSpy).not.toHaveBeenCalled()
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
