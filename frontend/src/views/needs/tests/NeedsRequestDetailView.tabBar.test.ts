// Copyright (c) 2026, AssetCore Team
// TC-UXTAB-05 (docs/ui-ux/07 §4.3, AC-UX-068) — màn Chi tiết đề xuất nhu cầu di trú
// `<nav>` tab tự chế về SSoT `DetailTabBar`.
//
// Bản fork ở đây có **0** `role="tablist"`, **0** `role="tab"`, **0** `aria-selected` —
// với trình đọc màn hình nó chỉ là ba cái nút rời rạc. Nhưng nó cũng mang một hành vi
// PHẢI giữ: 3 panel dùng `v-show`, KHÔNG `v-if`. Tab «Chấm điểm ưu tiên» và «Dự toán»
// chứa biểu mẫu đang gõ dở; đổi sang `v-if` là mỗi lần liếc sang tab khác lại mất trắng
// chữ vừa nhập (N4). Vì đây là hồi quy KHÔNG nhìn thấy trong ảnh chụp màn hình nên nó
// được khoá bằng một ca gõ-đi-quay-lại thật.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'NR-2026-00001' } }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: vi.fn(async (fn: () => unknown) => fn()) }),
}))
// isSystemAdmin ⇒ canScore đúng khi workflow_state = 'Reviewing' (cần ô nhập thật để
// chứng minh v-show giữ chữ đã gõ).
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ hasRole: () => true, hasAnyRole: () => true, isSystemAdmin: true, user: { name: 'qa@test.local' } }),
}))

const getNeedsRequest = vi.fn()
const getAllowedTransitions = vi.fn()
vi.mock('@/api/imm01', () => ({
  getNeedsRequest: (...a: unknown[]) => getNeedsRequest(...a),
  getAllowedTransitions: (...a: unknown[]) => getAllowedTransitions(...a),
  rollIntoPlan: vi.fn(),
  listNeedsRequests: vi.fn(),
  createNeedsRequest: vi.fn(),
  updateNeedsRequest: vi.fn(),
  scoreNeedsRequest: vi.fn(),
  submitBudgetEstimate: vi.fn(),
  transitionWorkflow: vi.fn(),
  approveNeedsRequest: vi.fn(),
  rejectNeedsRequest: vi.fn(),
  listProcurementPlans: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 }),
  getDashboardKpis: vi.fn(),
}))

import DetailTabBar from '@/components/common/DetailTabBar.vue'
import NeedsRequestDetailView from '@/views/needs/NeedsRequestDetailView.vue'

const stubs = {
  PageHeader: true, CurrencyInput: true, StatusBadge: true,
  BaseModal: true, SkeletonLoader: true, ApproverSelect: true,
}

const TAB_LABELS = ['Tổng quan', 'Chấm điểm ưu tiên', 'Dự toán']

function nrFixture(over: Record<string, unknown> = {}) {
  return {
    name: 'NR-2026-00001',
    request_type: 'New',
    requesting_department: 'AC-DEPT-1928',
    requesting_department_name: 'Phòng Vật tư - Thiết bị y tế',
    quantity: 1,
    target_year: 2027,
    clinical_justification: 'Lý do lâm sàng test.',
    workflow_state: 'Reviewing',
    scoring_rows: [
      { criterion: 'Clinical Need', score: 3, weight_pct: 20, justification: '' },
      { criterion: 'Patient Safety', score: 4, weight_pct: 30, justification: '' },
    ],
    budget_lines: [],
    allowed_transitions: [] as string[],
    ...over,
  }
}

async function mountDetail(over: Record<string, unknown> = {}) {
  getNeedsRequest.mockResolvedValue(nrFixture(over))
  getAllowedTransitions.mockResolvedValue({ transitions: [] })
  const w = mount(NeedsRequestDetailView, { global: { stubs } })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  getNeedsRequest.mockReset()
  getAllowedTransitions.mockReset()
})

describe('TC-UXTAB-05 — 3 tab qua SSoT: có role/aria (TRƯỚC vòng này là 0)', () => {
  it('ĐÚNG 1 DetailTabBar + 1 tablist + 3 tab', async () => {
    const w = await mountDetail()
    expect(w.findAllComponents(DetailTabBar)).toHaveLength(1)
    expect(w.findAll('[role="tablist"]')).toHaveLength(1)
    expect(w.findAll('[role="tab"]')).toHaveLength(3)
  })

  it('3 nhãn tiếng Việt giữ NGUYÊN VĂN, đúng thứ tự', async () => {
    const w = await mountDetail()
    expect(w.findAll('[role="tab"]').map((t) => t.text().trim())).toEqual(TAB_LABELS)
  })

  it('đổi tab ⇒ aria-selected DI CHUYỂN, luôn đúng 1 tab được chọn', async () => {
    const w = await mountDetail()
    expect(w.find('[data-testid="tab-overview"]').attributes('aria-selected')).toBe('true')

    await w.find('[data-testid="tab-scoring"]').trigger('click')
    await flushPromises()

    expect(w.find('[data-testid="tab-scoring"]').attributes('aria-selected')).toBe('true')
    expect(w.find('[data-testid="tab-overview"]').attributes('aria-selected')).toBe('false')
    expect(
      w.findAll('[role="tab"]').filter((t) => t.attributes('aria-selected') === 'true'),
    ).toHaveLength(1)
  })

  it('màn này KHÔNG khai badge (không có số đếm nào để hiện) ⇒ 0 phần tử badge', async () => {
    const w = await mountDetail()
    const tabs = w.findComponent(DetailTabBar).props('tabs') as { key: string; badge?: unknown }[]
    for (const t of tabs) expect(t.badge ?? '').toBe('')
    expect(w.findAll('[data-testid^="tab-badge-"]')).toHaveLength(0)
  })
})

describe('TC-UXTAB-05b — panel giữ `v-show`: chữ đã gõ KHÔNG mất khi đổi tab (N4)', () => {
  it('gõ trọng số ở «Chấm điểm ưu tiên» → sang «Dự toán» → quay lại ⇒ giá trị CÒN NGUYÊN', async () => {
    const w = await mountDetail()

    await w.find('[data-testid="tab-scoring"]').trigger('click')
    await flushPromises()

    const inputs = w.findAll('input[type="number"]')
    expect(inputs.length, 'Tab chấm điểm phải có ô nhập trọng số để TC này có ý nghĩa')
      .toBeGreaterThan(0)
    await inputs[0].setValue('45')

    await w.find('[data-testid="tab-budget"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="tab-scoring"]').trigger('click')
    await flushPromises()

    const after = w.findAll('input[type="number"]')[0]
    expect(
      (after.element as HTMLInputElement).value,
      'Giá trị đã gõ bị mất khi đổi tab — panel đã bị đổi sang v-if (N4).',
    ).toBe('45')
  })

  it('panel không hoạt động vẫn CÒN trong DOM (dấu hiệu v-show, không phải v-if)', async () => {
    const w = await mountDetail()
    // Đang ở «Tổng quan» mà nội dung 2 tab kia vẫn tồn tại (ẩn bằng CSS) ⇒ v-show.
    expect(w.html()).toContain('6 tiêu chí ưu tiên')
    expect(w.html()).toContain('Bảng dự toán chi phí')
  })
})
