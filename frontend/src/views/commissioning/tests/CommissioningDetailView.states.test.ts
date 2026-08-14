// Copyright (c) 2026, AssetCore Team
// TC-UX4-35 (docs/ui-ux/03 §13.6) — CommissioningDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N4).
//
// RED trước fix: nhánh lỗi tự chế in «Không thể tải phiếu» + chuỗi `store.error` cho MỌI loại lỗi
// (404 và 403 cùng một câu), và THANH TAB nằm NGOÀI nhánh nội dung ⇒ phiếu 403 vẫn phơi 3 nút tab
// bấm được nhưng không dẫn tới đâu. Sau fix: shell quyết định 4 trạng thái; thanh tab hoisting lên
// prop shell nên nằm TRONG nhánh `content`.
//
// Bẫy riêng (13.9.2): `activeTab` của màn này là `computed` đọc `route.name` (KHÔNG setter) ⇒ phải
// dùng cặp `:active-tab` + `@update:active-tab`, `v-model` sẽ vỡ. Sub-case (g2) khoá điều đó.
import { reactive } from 'vue'
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { describeDetailStates } from '@/test/detailStatesHarness'

const push = vi.fn()
const routeRef = { name: 'CommissioningDetail' as string }
vi.mock('vue-router', () => ({
  useRouter: () => ({ push, back: vi.fn() }),
  useRoute: () => routeRef,
}))

const DOC_ID = 'INS-2026-00007'

// `reactive`: view đọc qua getter của store mock ⇒ state phải theo dõi được, nếu không
// kết quả nạp bất đồng bộ không bao giờ tới màn.
const storeState = reactive({
  currentDoc: null as Record<string, unknown> | null,
  loading: false,
  error: null as string | null,
  lastApiError: null as unknown,
  openNcCount: 0,
})
const fetchDetailSpy = vi.fn()

vi.mock('@/stores/imm04', () => ({
  useCommissioningStore: () => ({
    get currentDoc() { return storeState.currentDoc },
    get loading() { return storeState.loading },
    get error() { return storeState.error },
    get lastApiError() { return storeState.lastApiError },
    get openNcCount() { return storeState.openNcCount },
    fetchDetail: fetchDetailSpy,
    clearError: vi.fn(),
    transitionState: vi.fn(),
    saveDoc: vi.fn(),
    submitDoc: vi.fn(),
    deleteDoc: vi.fn(),
    cancelDoc: vi.fn(),
  }),
}))
vi.mock('@/stores/imm05', () => ({
  useImm05Store: () => ({
    fetchAssetDocuments: vi.fn(),
    assetDocumentStatus: null, assetCompletenessPct: 0, missingRequired: [],
    assetExpiredRequired: [], assetExpiringRequired: [], assetRequiredTotal: null,
    assetRequiredSatisfied: null, assetHiddenCount: 0, assetIsCompliant: null,
    assetDocuments: {},
  }),
}))
vi.mock('@/composables/usePermissions', () => ({
  usePermissions: () => ({ isAdmin: { value: true }, isQA: { value: true } }),
}))
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

import CommissioningDetailView from '@/views/commissioning/CommissioningDetailView.vue'

const stubs = {
  PageHeader: true, CommissioningForm: true, ApprovalPanel: true,
  StatusBadge: true, teleport: true,
}

function docFixture() {
  return {
    name: DOC_ID,
    workflow_state: 'Installing',
    docstatus: 0,
    final_asset: null,
    board_approver: null,
  }
}

function setStore(over: Partial<typeof storeState>) {
  Object.assign(storeState, { currentDoc: null, loading: false, error: null, lastApiError: null, openNcCount: 0 }, over)
}

describeDetailStates({
  view: 'CommissioningDetailView',
  tc: 'TC-UX4-35',
  mount: () => mount(CommissioningDetailView, { props: { id: DOC_ID }, global: { stubs } }) as never,
  pending: () => {
    setStore({ loading: true })
    fetchDetailSpy.mockReturnValue(new Promise(() => {}))
  },
  fail: (e) => fetchDetailSpy.mockImplementation(async () => {
    setStore({ error: 'Không tải được phiếu', lastApiError: e })
  }),
  empty: () => fetchDetailSpy.mockImplementation(async () => setStore({ currentDoc: null })),
  ok: () => fetchDetailSpy.mockImplementation(async () => setStore({ currentDoc: docFixture() })),
  loadCalls: () => fetchDetailSpy.mock.calls.length,
  reset: () => {
    fetchDetailSpy.mockReset()
    push.mockClear()
    setStore({})
  },
  recordId: DOC_ID,
  // Panel thao tác của màn này nằm TRONG `ApprovalPanel` / `CommissioningForm` (đã stub để
  // cô lập 4 trạng thái) ⇒ dấu vân tay «điều khiển chỉ-có-ở-content» đo được là THANH TAB:
  // trước lô 2 nó nằm NGOÀI nhánh nội dung nên phiếu 403 vẫn phơi 3 nút tab bấm-không-tới-đâu.
  ctaTestIds: ['detail-tabs'],
  hasTabs: true,
  routerPush: push,
})

describe('CommissioningDetailView — tab THEO ROUTE giữ nguyên sau hoisting (bẫy 13.9.2)', () => {
  it('bấm tab thứ 2 ⇒ router.push, KHÔNG sinh state tab cục bộ', async () => {
    fetchDetailSpy.mockReset().mockImplementation(async () => setStore({ currentDoc: docFixture() }))
    push.mockClear()
    const w = mount(CommissioningDetailView, { props: { id: DOC_ID }, global: { stubs } })
    await flushPromises()
    const tabs = w.findAll('[role="tab"]')
    expect(tabs.length).toBeGreaterThan(1)
    await tabs[1].trigger('click')
    expect(push).toHaveBeenCalled()
    // `activeTab` là computed từ `route.name` ⇒ route chưa đổi thì tab đang mở KHÔNG đổi.
    expect(w.findAll('[aria-selected="true"]').length).toBe(1)
  })
})
