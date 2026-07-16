// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho phiếu
// kiểm kê. Nút Submit/Recount/Post ở CycleCountDetailView gate theo
// `allowed_transitions` do BE emit (_cycle_allowed_transitions trong
// services/imm15.py) — KHÔNG hardcode `detail.status === 'X'`. Mirror
// pmWorkOrderDetailCtaGate.test.ts + rcaDetailCtaGating.test.ts.
//
// Contract action token:
//   ['Submit']            → chỉ nút cta-submit
//   ['Recount', 'Post']   → cta-recount + cta-post (Reviewed, đủ quyền)
//   ['Post']              → chỉ cta-post (Reviewed, thiếu inventory.submit-recount)
//   []                    → 0 nút hành động (Posted terminal / thiếu quyền)
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick } from 'vue'
import { setRouteParams } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn() }),
}))

type Detail = Record<string, unknown>
let mockDetail: Detail = {}
const getCycleCount = vi.fn(async () => mockDetail)
// GATE-6c dead-control spy: reason gõ vào PHẢI == tham số truyền recountCycleCount.
const recountCycleCount = vi.fn(async (_name: string, _reason: string) => ({
  name: 'CYC-2026-00042', workflow_state: 'Counting',
}))
vi.mock('@/api/imm15', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm15')>()
  return {
    ...actual,
    getCycleCount: (name: string) => getCycleCount(name),
    recountCycleCount: (name: string, reason: string) => recountCycleCount(name, reason),
  }
})

import CycleCountDetailView from './CycleCountDetailView.vue'

function makeDetail(allowed: string[], over: Detail = {}): Detail {
  const status = (over.status as string)
    ?? (allowed.includes('Submit') ? 'Planned'
      : (allowed.includes('Recount') || allowed.includes('Post')) ? 'Reviewed'
        : 'Posted')
  return {
    name: 'CYC-2026-00042',
    warehouse: 'WH-A', warehouse_name: 'Kho Trung tâm',
    count_date: '2026-06-01', count_type: 'Cycle',
    counted_by: 'a@x.vn', counted_by_name: 'Thủ kho A',
    verified_by: '', verified_by_name: '',
    status,
    variance_count: 1, variance_value: 500000,
    items: [{
      spare_part: 'SP-1', part_name: 'Cảm biến SpO2', system_qty: 20,
      counted_qty: 18, variance_qty: -2, variance_pct: 10, variance_value: -500000,
    }],
    adjustment_ref: '', capa_created: 0,
    allowed_transitions: allowed,
    ...over,
  }
}

let wrapper: VueWrapper | null = null
async function mountDetail() {
  wrapper = mount(CycleCountDetailView, {
    global: {
      stubs: { RouterLink: true, Transition: false, ApproverSelect: true, WorkflowStepper: true },
    },
  }) as VueWrapper
  await flushPromises()
  return wrapper
}

const ALL_CTA = ['cta-submit', 'cta-recount', 'cta-post']
function ctasShown(w: VueWrapper): string[] {
  return ALL_CTA.filter(id => w.find(`[data-testid="${id}"]`).exists())
}

beforeEach(() => {
  setActivePinia(createPinia())
  getCycleCount.mockClear()
  recountCycleCount.mockClear()
  // Detail-view đọc route.params.name làm khoá phiếu (→ recountCycleCount(name, ...)).
  setRouteParams({ name: 'CYC-2026-00042' })
})

afterEach(() => {
  // BaseModal teleport vào document.body → dọn để node không rò sang test sau.
  wrapper?.unmount()
  wrapper = null
  document.body.replaceChildren()
  // Clear params trên globalThis để không rò sang file test khác cùng worker.
  setRouteParams({})
})

describe('Cycle Count CTA gate — theo allowed_transitions (server-driven)', () => {
  it("allowed=['Submit'] → chỉ nút Submit", async () => {
    mockDetail = makeDetail(['Submit'])
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-submit"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-recount"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-post"]').exists()).toBe(false)
    expect(ctasShown(w)).toEqual(['cta-submit'])
  })

  it("allowed=['Recount','Post'] (Reviewed, đủ quyền) → nút Recount + Post", async () => {
    mockDetail = makeDetail(['Recount', 'Post'])
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-recount"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-post"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-submit"]').exists()).toBe(false)
    // Recount đứng TRƯỚC Post (mirror thứ tự token BE).
    expect(ctasShown(w)).toEqual(['cta-recount', 'cta-post'])
  })

  it("allowed=['Recount'] → chỉ nút Recount", async () => {
    mockDetail = makeDetail(['Recount'])
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-recount"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-post"]').exists()).toBe(false)
    expect(ctasShown(w)).toEqual(['cta-recount'])
  })

  it("allowed=['Post'] → chỉ nút Post (KHÔNG lộ Recount khi thiếu token)", async () => {
    mockDetail = makeDetail(['Post'])
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-post"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-recount"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-submit"]').exists()).toBe(false)
    expect(ctasShown(w)).toEqual(['cta-post'])
  })

  it('allowed=[] (Posted terminal) → 0 nút hành động', async () => {
    mockDetail = makeDetail([], { status: 'Posted' })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
  })

  it("RED-guard: status='Reviewed' NHƯNG allowed=[] (thiếu quyền) → KHÔNG lộ Recount/Post", async () => {
    // Nếu view hardcode status==='Reviewed' thì test này sẽ đỏ.
    mockDetail = makeDetail([], { status: 'Reviewed' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-post"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-recount"]').exists()).toBe(false)
  })

  it('Posted → hiển thị bút toán điều chỉnh + cảnh báo CAPA khi capa_created>0', async () => {
    mockDetail = makeDetail([], {
      status: 'Posted', adjustment_ref: 'SM-ADJ-2026-0001', capa_created: 2,
    })
    const w = await mountDetail()
    expect(w.text()).toContain('SM-ADJ-2026-0001')
    expect(w.text()).toContain('hành động khắc phục/phòng ngừa')
  })
})

describe('Cycle Count Recount — control không dead (GATE-6c) — reason gõ == param phát đi', () => {
  it('bấm "Sửa đếm lại" → mở modal lý do; xác nhận → recountCycleCount(name, reason)', async () => {
    mockDetail = makeDetail(['Recount', 'Post'])
    const w = await mountDetail()
    await w.find('[data-testid="cta-recount"]').trigger('click')
    await nextTick()

    // BaseModal teleport vào document.body → query trực tiếp.
    const ta = document.body.querySelector('#cc-recount-reason') as HTMLTextAreaElement | null
    expect(ta).not.toBeNull()
    ta!.value = 'Chênh lệch bất thường tại kệ A3'
    ta!.dispatchEvent(new Event('input', { bubbles: true }))
    await flushPromises()

    const confirm = document.body.querySelector(
      '[data-testid="cta-recount-confirm"]') as HTMLButtonElement | null
    expect(confirm).not.toBeNull()
    expect(confirm!.disabled).toBe(false)
    confirm!.dispatchEvent(new Event('click', { bubbles: true }))
    await flushPromises()

    expect(recountCycleCount).toHaveBeenCalledTimes(1)
    expect(recountCycleCount).toHaveBeenCalledWith('CYC-2026-00042', 'Chênh lệch bất thường tại kệ A3')
  })

  it('reason rỗng → nút Xác nhận disabled (không gọi recountCycleCount)', async () => {
    mockDetail = makeDetail(['Recount'])
    const w = await mountDetail()
    await w.find('[data-testid="cta-recount"]').trigger('click')
    await nextTick()

    const confirm = document.body.querySelector(
      '[data-testid="cta-recount-confirm"]') as HTMLButtonElement | null
    expect(confirm).not.toBeNull()
    expect(confirm!.disabled).toBe(true)
    // Click khi disabled → mọi trình duyệt bỏ qua; đảm bảo không gọi API.
    confirm!.dispatchEvent(new Event('click', { bubbles: true }))
    await flushPromises()
    expect(recountCycleCount).not.toHaveBeenCalled()
  })
})

describe('Cycle Count — KHÔNG hardcode gate status=== cho Recount (GATE-8/LL-FE-51)', () => {
  it('canRecount gate bằng allowed_transitions.includes("Recount"), KHÔNG status===', async () => {
    const { readFileSync } = await import('node:fs')
    const { resolve } = await import('node:path')
    const raw = readFileSync(
      resolve(process.cwd(), 'src/views/inventory/CycleCountDetailView.vue'), 'utf8')
    const code = raw
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/(^|[^:])\/\/.*$/gm, '$1')
    // canRecount phải derive từ allowedTransitions.includes('Recount').
    // (showVariance vẫn được dùng status===Reviewed cho cột hiển thị — đó là
    // display concern, KHÔNG phải gate CTA; nên chỉ assert nguồn của canRecount.)
    expect(code).toMatch(/canRecount[\s\S]{0,80}allowedTransitions[\s\S]{0,40}Recount/)
    // Nút Recount trong template gate bằng canRecount (KHÔNG v-if="status...").
    expect(code).toMatch(/v-if="canRecount"/)
  })
})
