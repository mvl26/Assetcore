// TDD — CR-WF-15-AUDIT (FE display-layer): 6 mã event_type IMM-15 (Kiểm kê & Cấp phát)
// do BE ghi vào IMM Audit Trail phải render NHÃN TIẾNG VIỆT trong AuditTrailListView,
// KHÔNG rò mã snake_case thô ra UI (LL-FE-53 / no-raw-code-leak). Đồng thời giá-trị
// <option> filter PHẢI == mã gửi BE (GATE-6c dead-control: value==code).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}))

// Mỗi mã IMM-15 → 1 dòng IMM Audit Trail (đúng shape list_audit_trail đã unwrap).
const CODES: [string, string][] = [
  ['cycle_count_posted', 'Đã chốt kiểm kê'],
  ['allocation_created', 'Tạo phiếu cấp phát'],
  ['allocation_approved', 'Duyệt cấp phát'],
  ['allocation_issued', 'Đã cấp phát'],
  ['allocation_returned', 'Đã hoàn trả'],
  ['allocation_cancelled', 'Đã hủy cấp phát'],
]
const ROWS = CODES.map(([code], i) => ({
  name: `IAT-2026-${String(i + 1).padStart(5, '0')}`,
  event_type: code,
  asset: '',
  asset_name: '',
  timestamp: '2026-07-11 09:00:00',
  actor: 'thukho@benhvien.vn',
  from_status: 'Reviewed',
  to_status: 'Posted',
  // Tóm tắt thực tế từ BE là văn bản người-đọc (không chứa mã snake_case), nên phép
  // assert no-leak dưới đây chỉ trượt nếu chính CỘT SỰ KIỆN rò mã thô.
  change_summary: `Nghiệp vụ kho phiếu số ${i + 1}`,
  current_hash: 'abc123def456',
}))

const frappeGet = vi.fn().mockResolvedValue({
  items: ROWS,
  pagination: { total: ROWS.length, page: 1, page_size: 20, total_pages: 1 },
})
vi.mock('@/api/helpers', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/helpers')>()
  return { ...actual, frappeGet: (url: string, p?: Record<string, unknown>) => frappeGet(url, p) }
})

import AuditTrailListView from '@/views/audit/AuditTrailListView.vue'

async function mountView() {
  const w = mount(AuditTrailListView, {
    global: { stubs: { RouterLink: true, Transition: false, SmartSelect: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  frappeGet.mockClear()
})

describe('AuditTrailListView — nhãn event_type IMM-15 (CR-WF-15-AUDIT)', () => {
  it('gọi list_audit_trail và render đủ 6 bản ghi IMM-15', async () => {
    const w = await mountView()
    expect(frappeGet).toHaveBeenCalled()
    expect(w.text()).toContain('IAT-2026-00001')
    expect(w.text()).toContain('IAT-2026-00006')
  })

  it('render NHÃN tiếng Việt cho cả 6 mã event_type (badge bảng)', async () => {
    const w = await mountView()
    const html = w.text()
    for (const [, label] of CODES) expect(html).toContain(label)
  })

  it('KHÔNG rò mã snake_case thô ra UI', async () => {
    const w = await mountView()
    const html = w.text()
    for (const [code] of CODES) expect(html).not.toContain(code)
  })

  it('GATE-6c dead-control: <option> filter có value == mã gửi BE (không dịch value)', async () => {
    const w = await mountView()
    const options = w.findAll('option')
    for (const [code, label] of CODES) {
      const opt = options.find(o => o.attributes('value') === code)
      expect(opt, `thiếu <option value="${code}">`).toBeTruthy()
      expect(opt!.text()).toBe(label) // label VI, value giữ nguyên mã kỹ thuật
    }
  })
})
