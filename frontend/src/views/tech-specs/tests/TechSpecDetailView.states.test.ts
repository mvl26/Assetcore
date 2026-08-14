// Copyright (c) 2026, AssetCore Team
// TC-UX4-49 (docs/ui-ux/03 §13.6) — TechSpecDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N4).
//
// RED trước fix: `onMounted` gọi `store.fetchOne(...)` **không có catch nào** ⇒ 404 / 403 / mất
// mạng đều rơi xuống nhánh `v-else` in «Không có dữ liệu». Người dùng đọc câu đó và tin rằng hồ sơ
// yêu cầu kỹ thuật RỖNG, trong khi thật ra họ không có quyền đọc hoặc mạng chết — và ApiError nổi
// lên console dưới dạng unhandled rejection. Sau fix: view tự `try/catch` (KHÔNG sửa `stores/`),
// kind đến từ SSoT `useDetailAccess`, panel thao tác tắt bằng CẤU TRÚC.
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
  useRoute: () => ({ params: { id: 'TS-26-00001' } }),
}))

vi.mock('@/api/imm02', () => ({
  submitBenchmark: vi.fn(),
  submitLockInAssessment: vi.fn(),
}))

vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))

const storeState: { currentSpec: Record<string, unknown> | null } = { currentSpec: null }
const fetchOneSpy = vi.fn<() => Promise<void>>()
vi.mock('@/stores/imm02', () => ({
  useImm02Store: () => ({
    get currentSpec() { return storeState.currentSpec },
    loading: false,
    error: null as string | null,
    lastApiError: null,
    clearError: vi.fn(),
    fetchOne: fetchOneSpy,
    lock: vi.fn(),
    withdraw: vi.fn(),
    reissue: vi.fn(),
    transitionWorkflow: vi.fn(),
  }),
}))

import TechSpecDetailView from '@/views/tech-specs/TechSpecDetailView.vue'

const stubs = { RequirementTable: true, CurrencyInput: true, RouterLink: true }

function specFixture(): Record<string, unknown> {
  return {
    name: 'TS-26-00001',
    version: 1,
    workflow_state: 'Pending Approval',
    quantity: 2,
    device_model_ref: 'DM-0001',
    source_needs_request: 'NR-2026-0001',
    source_plan: 'PP-2026-0001',
    requirements: [],
    infrastructure_checks: [],
    allowed_actions: ['Gửi rà soát'],
    can_lock: true,
  }
}

/** `fetchOne` ghi vào store thật ⇒ mock phải mô phỏng cả tác dụng phụ đó. */
function resolveWith(doc: Record<string, unknown> | null) {
  fetchOneSpy.mockImplementation(async () => { storeState.currentSpec = doc })
}

describeDetailStates({
  view: 'TechSpecDetailView',
  tc: 'TC-UX4-49',
  mount: () => mount(TechSpecDetailView, { props: { id: 'TS-26-00001' }, global: { stubs } }) as never,
  pending: () => {
    storeState.currentSpec = null
    fetchOneSpy.mockReturnValue(new Promise(() => {}))
  },
  fail: (e) => {
    storeState.currentSpec = null
    fetchOneSpy.mockRejectedValue(e)
  },
  empty: () => resolveWith(null),
  ok: () => resolveWith(specFixture()),
  loadCalls: () => fetchOneSpy.mock.calls.length,
  reset: () => {
    fetchOneSpy.mockReset()
    pushSpy.mockClear()
    storeState.currentSpec = null
  },
  recordId: 'TS-26-00001',
  ctaTestIds: ['cta-lock', 'cta-withdraw', 'cta-reissue', 'cta-wf-gui-ra-soat'],
  routerPush: pushSpy,
})
