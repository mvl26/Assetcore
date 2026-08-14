// TDD/regression — IMM-01 ProcurementPlanListView create modal (proposal-first).
//
// QĐ nghiệp vụ: kế hoạch mua sắm được TẠO bằng cách CHỌN ≥1 đề xuất (Needs
// Request đã duyệt), KHÔNG tạo kế hoạch rỗng rồi thêm sau. Hợp đồng FE:
//   1. Mở modal "Tạo kế hoạch" → nạp danh sách đề xuất đã duyệt
//      (listNeedsRequests({workflow_state:'Approved'})) để chọn.
//   2. Nút submit BỊ KHOÁ khi chưa chọn đề xuất nào (≥1 là bắt buộc).
//   3. Chọn ≥1 đề xuất + submit → createProcurementPlan gọi KÈM mảng
//      needs_requests (khớp BE create_procurement_plan đã yêu cầu ≥1).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { reactive } from 'vue'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'

enableAutoUnmount(afterEach)

// ─── API mocks ──────────────────────────────────────────────────────────────
const createPlanSpy = vi.fn()
const listNeedsSpy = vi.fn()
vi.mock('@/api/imm01', () => ({
  createProcurementPlan: (...a: unknown[]) => createPlanSpy(...a),
  listNeedsRequests: (...a: unknown[]) => listNeedsSpy(...a),
}))

// ─── store mock (chỉ cần các thuộc tính view dùng) ────────────────────────────
const fakeStore = reactive({
  plans: [] as unknown[],
  loading: false,
  error: null as string | null,
  fetchPlans: vi.fn().mockResolvedValue(undefined),
  clearError: vi.fn(),
})
vi.mock('@/stores/imm01', () => ({ useImm01Store: () => fakeStore }))

// can('needs.create') → true để nút "Tạo" hiển thị.
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

const routerPushSpy = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push: routerPushSpy }) }))

import ProcurementPlanListView from '@/views/needs/ProcurementPlanListView.vue'

const APPROVED = [
  { name: 'NR-26-001', requesting_department: 'KCDHA', department_name: 'Khoa CĐHA',
    weighted_score: 8.5, total_capex: 1_000_000, workflow_state: 'Approved',
    request_type: 'New', quantity: 1, request_date: '2026-06-01' },
  { name: 'NR-26-002', requesting_department: 'KXN', department_name: 'Khoa Xét nghiệm',
    weighted_score: 7.0, total_capex: 2_000_000, workflow_state: 'Approved',
    request_type: 'New', quantity: 2, request_date: '2026-06-02' },
]

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  KpiCard: true, StatusBadge: true, CurrencyInput: true,
}

async function mountView() {
  const w = mount(ProcurementPlanListView, { global: { stubs } })
  await flushPromises()
  return w
}

// Mở modal qua nút empty-state "+ Tạo kế hoạch đầu tiên" (nằm trong body, không
// bị stub như slot của PageHeader). store.plans rỗng nên empty-state hiển thị.
async function openCreateModal(w: Awaited<ReturnType<typeof mountView>>) {
  const openBtn = w.findAll('button').find(b => b.text().includes('Tạo kế hoạch'))
  expect(openBtn, 'phải có nút mở modal tạo kế hoạch').toBeTruthy()
  await openBtn!.trigger('click')
  await flushPromises()
}

function submitButton(w: Awaited<ReturnType<typeof mountView>>) {
  // Nút submit trong modal: text == 'Tạo kế hoạch' (header là '+ Tạo kế hoạch').
  return w.findAll('button').find(b => b.text().trim() === 'Tạo kế hoạch')
}

describe('IMM-01 ProcurementPlanListView — tạo kế hoạch theo đề xuất (proposal-first)', () => {
  beforeEach(() => {
    createPlanSpy.mockReset().mockResolvedValue({ name: 'PP-26-NEW' })
    listNeedsSpy.mockReset().mockResolvedValue(
      { items: APPROVED, total: APPROVED.length, page: 1, page_size: 100 })
    routerPushSpy.mockClear()
    fakeStore.plans = []
    fakeStore.error = null
  })

  it('mở modal → nạp đề xuất đã duyệt để chọn', async () => {
    const w = await mountView()
    await openCreateModal(w)
    expect(listNeedsSpy).toHaveBeenCalledWith({ workflow_state: 'Approved' }, 1, 100)
    // Mỗi đề xuất 1 checkbox để chọn.
    expect(w.findAll('input[type="checkbox"]').length).toBe(APPROVED.length)
  })

  it('chưa chọn đề xuất nào → nút tạo BỊ KHOÁ + KHÔNG gọi createProcurementPlan', async () => {
    const w = await mountView()
    await openCreateModal(w)
    const btn = submitButton(w)
    expect(btn, 'phải có nút submit trong modal').toBeTruthy()
    expect(btn!.attributes('disabled')).toBeDefined()
    expect(createPlanSpy).not.toHaveBeenCalled()
  })

  it('chọn ≥1 đề xuất + submit → createProcurementPlan kèm needs_requests', async () => {
    const w = await mountView()
    await openCreateModal(w)
    await w.findAll('input[type="checkbox"]')[0].setValue(true)
    await flushPromises()
    const btn = submitButton(w)
    expect(btn!.attributes('disabled')).toBeUndefined()
    await btn!.trigger('click')
    await flushPromises()
    expect(createPlanSpy).toHaveBeenCalledTimes(1)
    const args = createPlanSpy.mock.calls[0]
    // (plan_year, plan_period, budget_envelope, needs_requests[])
    expect(args[3]).toEqual(['NR-26-001'])
    expect(routerPushSpy).toHaveBeenCalledWith('/procurement-plans/PP-26-NEW')
  })
})
