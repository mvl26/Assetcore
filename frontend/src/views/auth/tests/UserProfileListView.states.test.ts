// TC-UX3-08 (AC-UX-041/042) — /user-profiles: 4 trạng thái danh sách + «Thử lại» + nhãn VI.
//
// Bug gốc đo trên đĩa 2026-07-31: `grep -cE 'error|catch' UserProfileListView.vue` == **0**
// ⇒ 0 nhánh lỗi. API 500 làm `loading.value = false` (đặt SAU `await`) không bao giờ chạy
// ⇒ khung xương quay MÃI MÃI + unhandled rejection trong onMounted. Nếu lượt nạp trả rỗng
// vì lỗi, người dùng đọc «Không có dữ liệu.» — lỗi giả dạng rỗng.
// A11 (LL-FE-53): nhãn «Import» / «Import Người dùng» phải là tiếng Việt đầy đủ.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listUsersSpy = vi.fn()
const rolesSpy = vi.fn()
vi.mock('@/api/user', () => ({
  listUsers: (...a: unknown[]) => listUsersSpy(...a),
  getAvailableImmRoles: (...a: unknown[]) => rolesSpy(...a),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ isSystemAdmin: true }) }))
vi.mock('@/composables/useImportWizard', () => ({
  useImportWizard: () => ({ open: vi.fn(), doExport: vi.fn(), showImport: false }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import UserProfileListView from '@/views/auth/UserProfileListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const USERS = [
  { name: 'a@benhvien.vn', full_name: 'Nguyễn Văn A', email: 'a@benhvien.vn',
    department_name: 'Khoa Chẩn đoán hình ảnh', imm_approval_status: 'Approved', imm_roles: [] },
  { name: 'b@benhvien.vn', full_name: 'Trần Thị B', email: 'b@benhvien.vn',
    department_name: 'Khoa Xét nghiệm', imm_approval_status: 'Pending', imm_roles: [] },
]
const okPage = (items: typeof USERS) => ({
  items, pagination: { page: 1, page_size: 20, total: items.length, total_pages: 1 },
})

const stubs = { PageHeader: true, FilterToggleButton: true, SmartSelect: true, ImportWizardModal: true }

async function mountView() {
  const w = mount(UserProfileListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/user-profiles — 4 trạng thái loại trừ + thử lại + nhãn VI (TC-UX3-08)', () => {
  beforeEach(() => {
    resetRouteMock()
    listUsersSpy.mockReset().mockResolvedValue(okPage(USERS))
    rolesSpy.mockReset().mockResolvedValue([])
  })

  it('(a) đang tải ⇒ khung xương, 0 <table> dữ liệu', async () => {
    listUsersSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('table')).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + «Thử lại», KHÔNG còn «Không có dữ liệu.»', async () => {
    listUsersSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.html()).not.toContain('Không có dữ liệu')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(b2) danh sách vai trò hỏng KHÔNG chặn lượt nạp người dùng', async () => {
    rolesSpy.mockRejectedValue(new Error('403'))
    const w = await mountView()
    expect(listUsersSpy).toHaveBeenCalledTimes(1)
    expect(state(w)).toBe('content')
  })

  it('(c) rỗng ⇒ ui-empty có câu hướng dẫn', async () => {
    listUsersSpy.mockResolvedValue(okPage([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    const empty = w.find('[data-testid="ui-empty"]')
    expect(empty.exists()).toBe(true)
    expect(empty.text()).toMatch(/Hãy|Bấm|Nhấn|Thêm |Xoá bộ lọc|Xóa bộ lọc/)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng, 0 ui-empty, 0 ui-error', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.findAll('tbody tr')).toHaveLength(USERS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) bấm «Thử lại» ⇒ hàm nạp được gọi lần 2; lượt 2 OK ⇒ về trạng thái có dữ liệu', async () => {
    listUsersSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(listUsersSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listUsersSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
  })

  it('(f) nhãn tiếng Việt — DOM không chứa chuỗi «Import» (A11 / LL-FE-53)', async () => {
    const w = await mountView()
    expect(w.html()).not.toContain('Import')
  })

  it('(g) bộ lọc KHÔNG biến mất khi lỗi', async () => {
    listUsersSpy.mockRejectedValue(new Error('Bộ lọc không hợp lệ.'))
    const w = await mountView()
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
