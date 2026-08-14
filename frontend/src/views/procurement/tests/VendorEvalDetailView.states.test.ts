// Copyright (c) 2026, AssetCore Team
// TC-UX4-45 (docs/ui-ux/03 §13.6) — VendorEvalDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N4).
//
// RED trước fix: `onMounted` gọi `store.fetchEvaluation(...)` **không await, không catch** ⇒ mọi
// lỗi nạp rơi xuống `v-else` in «Không có dữ liệu» — người dùng tin hồ sơ đánh giá trống trong khi
// thật ra bị 403. Kèm `catch (e: any)` ở `loadScorecard` (mất type-safety). Sau fix: view tự
// `try/catch` (KHÔNG sửa `stores/`), `catch (e: unknown)`, và danh sách nhà cung cấp — dữ liệu PHỤ —
// không còn kéo sập cả màn khi lỗi.
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { EvalDoc } from '@/types/imm03'
import { describeDetailStates } from '@/test/detailStatesHarness'

const getEvaluationSpy = vi.fn<() => Promise<EvalDoc>>()
vi.mock('@/api/imm03', () => ({
  getEvaluation: () => getEvaluationSpy(),
  scoreEvaluation: vi.fn(),
  addCandidate: vi.fn(),
  submitQuotations: vi.fn(),
  transitionEvalWorkflow: vi.fn(),
  getVendorScorecard: vi.fn(),
  listVendorProfiles: vi.fn().mockResolvedValue({ items: [] }),
}))

vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ confirm: vi.fn(), fromError: vi.fn(), show: vi.fn(), fromOk: vi.fn() }),
}))

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'VE-2026-0004' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

import VendorEvalDetailView from '@/views/procurement/VendorEvalDetailView.vue'

const stubs = { DateInput: true, CurrencyInput: true, RouterLink: true }

function evalFixture(): EvalDoc {
  return {
    name: 'VE-2026-0004',
    spec_ref: 'TS-26-00001',
    draft_date: '2026-08-01',
    workflow_state: 'Quotation Received',
    docstatus: 0,
    candidates: [],
    criteria: [],
    allowed_transitions: ['Evaluated'],
  } as unknown as EvalDoc
}

setActivePinia(createPinia())

describeDetailStates({
  view: 'VendorEvalDetailView',
  tc: 'TC-UX4-45',
  mount: () => {
    setActivePinia(createPinia())
    return mount(VendorEvalDetailView, {
      props: { id: 'VE-2026-0004' },
      global: { stubs },
    }) as never
  },
  pending: () => getEvaluationSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getEvaluationSpy.mockRejectedValue(e),
  empty: () => getEvaluationSpy.mockResolvedValue(null as unknown as EvalDoc),
  ok: () => getEvaluationSpy.mockResolvedValue(evalFixture()),
  loadCalls: () => getEvaluationSpy.mock.calls.length,
  reset: () => {
    getEvaluationSpy.mockReset()
    pushSpy.mockClear()
  },
  recordId: 'VE-2026-0004',
  ctaTestIds: ['workflow-action'],
  routerPush: pushSpy,
})
