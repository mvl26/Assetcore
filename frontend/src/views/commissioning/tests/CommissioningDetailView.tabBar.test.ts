// Copyright (c) 2026, AssetCore Team
// TC-UXTAB-03/04 (docs/ui-ux/07 §4.2, AC-UX-068) — màn Chi tiết phiếu lắp đặt di trú
// thanh tab tự chế về SSoT `DetailTabBar`.
//
// Đây là bản fork TỆ NHẤT trong 9 bản: 3 nút viết tay, **0** `role="tablist"`, **0**
// `role="tab"`, **0** `aria-selected` (trình đọc màn hình không biết đây là dải tab; bàn
// phím không có ngữ cảnh nào) và **không cuộn ngang** — trên khung 375px tab thứ ba bị
// cắt. Lý do nó tồn tại chỉ là một con số nhỏ trong nút «Không phù hợp» × N, nay đã có
// chỗ đứng chính thức trong SSoT (prop `badge`, ADR-UX-19).
//
// Hai bất biến KHÔNG được vỡ khi đổi khuôn:
//   • TAB THEO ROUTE — bấm tab vẫn `router.push`, `activeTab` vẫn là `computed` đọc
//     `route.name`. Chuyển sang state cục bộ là mất deep-link và mất nút Back (N3).
//   • BADGE hiện iff `openNcCount > 0` — y hệt `v-if` cũ, không in số 0 vô nghĩa.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const push = vi.fn()
const routeRef = { name: 'CommissioningDetail' as string }
vi.mock('vue-router', () => ({
  useRouter: () => ({ push, back: vi.fn() }),
  useRoute: () => routeRef,
}))

const DOC_ID = 'INS-2026-00007'

const storeState = {
  currentDoc: {
    name: DOC_ID,
    workflow_state: 'Installing',
    docstatus: 0,
    final_asset: null as string | null,
    board_approver: null as string | null,
  },
  loading: false,
  error: null as string | null,
  lastApiError: null,
  openNcCount: 0,
}

vi.mock('@/stores/imm04', () => ({
  useCommissioningStore: () => ({
    get currentDoc() { return storeState.currentDoc },
    get loading() { return storeState.loading },
    get error() { return storeState.error },
    get lastApiError() { return storeState.lastApiError },
    get openNcCount() { return storeState.openNcCount },
    fetchDetail: vi.fn().mockResolvedValue(undefined),
    clearError: vi.fn(),
    transitionState: vi.fn().mockResolvedValue(true),
    saveDoc: vi.fn().mockResolvedValue(true),
    submitDoc: vi.fn().mockResolvedValue(true),
    deleteDoc: vi.fn().mockResolvedValue(true),
    cancelDoc: vi.fn().mockResolvedValue(true),
  }),
}))
vi.mock('@/stores/imm05', () => ({
  useImm05Store: () => ({
    fetchAssetDocuments: vi.fn().mockResolvedValue(undefined),
    assetDocumentStatus: null, assetCompletenessPct: 0, missingRequired: [],
    assetExpiredRequired: [], assetExpiringRequired: [], assetRequiredTotal: null,
    assetRequiredSatisfied: null, assetHiddenCount: 0, assetIsCompliant: null,
    assetDocuments: {},
  }),
}))
vi.mock('@/composables/usePermissions', () => ({
  usePermissions: () => ({ isAdmin: { value: true }, isQA: { value: true } }),
}))
// View render danh sách toast qua `toast.toasts.value` ⇒ mock phải có `toasts` dạng ref.
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    toasts: { value: [] as unknown[] },
    show: vi.fn(), success: vi.fn(), error: vi.fn(), warning: vi.fn(), remove: vi.fn(),
  }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ fromError: vi.fn(), show: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/api/imm04', () => ({
  getGateStatus: vi.fn().mockResolvedValue({
    g01_docs: true, g01_waived: false, g02_facility: true, g03_baseline: true,
    g04_radiation: true, g05_nc: true, g06_approver: true,
  }),
}))

import DetailTabBar from '@/components/common/DetailTabBar.vue'
import CommissioningDetailView from '@/views/commissioning/CommissioningDetailView.vue'

const stubs = {
  PageHeader: true, CommissioningForm: true, ApprovalPanel: true,
  SkeletonLoader: true, StatusBadge: true, teleport: true,
}

async function mountDetail() {
  const w = mount(CommissioningDetailView, { props: { id: DOC_ID }, global: { stubs } })
  await flushPromises()
  return w
}

beforeEach(() => {
  push.mockClear()
  routeRef.name = 'CommissioningDetail'
  storeState.openNcCount = 0
})

describe('TC-UXTAB-03 — 3 tab qua SSoT: a11y có role/aria (TRƯỚC vòng này là 0)', () => {
  it('ĐÚNG 1 tablist + 3 tab có role="tab"', async () => {
    const w = await mountDetail()
    expect(w.findAllComponents(DetailTabBar)).toHaveLength(1)
    expect(w.findAll('[role="tablist"]')).toHaveLength(1)
    expect(w.findAll('[role="tab"]')).toHaveLength(3)
  })

  it('nhãn giữ NGUYÊN VĂN tiếng Việt, đúng thứ tự cũ', async () => {
    const w = await mountDetail()
    expect(w.findAll('[role="tab"]').map((t) => t.text().trim())).toEqual([
      'Chi tiết phiếu', 'Không phù hợp', 'Lịch sử',
    ])
  })

  it('aria-selected đi theo ROUTE (bản fork cũ không có thuộc tính này)', async () => {
    const w = await mountDetail()
    expect(w.find('[data-testid="tab-detail"]').attributes('aria-selected')).toBe('true')
    expect(w.find('[data-testid="tab-nc"]').attributes('aria-selected')).toBe('false')

    routeRef.name = 'CommissioningNC'
    const w2 = await mountDetail()
    expect(w2.find('[data-testid="tab-nc"]').attributes('aria-selected')).toBe('true')
    expect(w2.find('[data-testid="tab-detail"]').attributes('aria-selected')).toBe('false')
  })

  it('container cuộn ngang được trên mobile (TC-RWD-07): overflow-x-auto + shrink-0', async () => {
    const w = await mountDetail()
    expect(w.find('[role="tablist"]').classes().join(' ')).toContain('overflow-x-auto')
    for (const t of w.findAll('[role="tab"]')) {
      expect(t.classes().join(' ')).toContain('shrink-0')
    }
  })
})

describe('TC-UXTAB-03b — tab vẫn ĐIỀU HƯỚNG BẰNG ROUTE (N3: cấm state cục bộ)', () => {
  it('bấm «Không phù hợp» ⇒ router.push(/commissioning/<id>/nc)', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-nc"]').trigger('click')
    expect(push).toHaveBeenCalledTimes(1)
    expect(push).toHaveBeenCalledWith(`/commissioning/${DOC_ID}/nc`)
  })

  it('bấm «Lịch sử» ⇒ router.push(/commissioning/<id>/timeline)', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-timeline"]').trigger('click')
    expect(push).toHaveBeenCalledWith(`/commissioning/${DOC_ID}/timeline`)
  })

  it('bấm «Chi tiết phiếu» ⇒ router.push(/commissioning/<id>)', async () => {
    routeRef.name = 'CommissioningNC'
    const w = await mountDetail()
    await w.find('[data-testid="tab-detail"]').trigger('click')
    expect(push).toHaveBeenCalledWith(`/commissioning/${DOC_ID}`)
  })

  it('bấm tab KHÔNG tự đổi tab đang chọn — chỉ route mới đổi được (SSoT controlled)', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-nc"]').trigger('click')
    await flushPromises()
    // Route giả lập chưa đổi ⇒ tab đang chọn PHẢI vẫn là 'detail'.
    expect(w.find('[data-testid="tab-detail"]').attributes('aria-selected')).toBe('true')
    expect(w.find('[data-testid="tab-nc"]').attributes('aria-selected')).toBe('false')
  })
})

describe('TC-UXTAB-04 — badge «Không phù hợp» giữ nguyên hành vi v-if cũ', () => {
  it('openNcCount = 2 ⇒ badge hiện «2», nằm TRONG nút tab', async () => {
    storeState.openNcCount = 2
    const w = await mountDetail()
    const badge = w.find('[data-testid="tab-badge-nc"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe('2')
    expect(w.find('[data-testid="tab-nc"]').find('[data-testid="tab-badge-nc"]').exists()).toBe(true)
  })

  it('openNcCount = 0 ⇒ KHÔNG có phần tử badge (không in số 0)', async () => {
    storeState.openNcCount = 0
    const w = await mountDetail()
    expect(w.findAll('[data-testid="tab-badge-nc"]')).toHaveLength(0)
    expect(w.find('[data-testid="tab-nc"]').text().trim()).toBe('Không phù hợp')
  })

  it('badge KHÔNG đẻ thêm tab-stop: vẫn đúng 3 [role=tab]', async () => {
    storeState.openNcCount = 5
    const w = await mountDetail()
    expect(w.findAll('[role="tab"]')).toHaveLength(3)
    expect(w.find('[data-testid="tab-nc"]').findAll('button')).toHaveLength(0)
  })
})
