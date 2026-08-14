// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho FCR.
//
// FirmwareCrDetailView gate 100% nút hành động (Duyệt / Triển khai / Khôi phục)
// theo `allowed_transitions` (BE derive từ _FCR_VALID_TRANSITIONS đã LỌC theo
// capability caller) + cờ `can_approve` — KHÔNG hardcode `fcr.status === 'X'`.
//
// RED trước fix (dead-gate): nút "Phê duyệt" render với v-if="status==='Draft' ||
// status==='Pending Approval'" → Repair User (không manager) bấm được, đổi status
// qua update_firmware_cr generic (nhảy-cóc, không audit). Sau fix: nút Duyệt chỉ
// render khi allowed_transitions.includes('Approved') && can_approve === true.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({
    show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(),
    confirm: vi.fn().mockResolvedValue(true),
  }),
}))

// useApi.run = passthrough (chạy fn thật để verify param phát đi == UI-selection).
const runSpy = vi.fn(async (fn: () => Promise<unknown>) => await fn())
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: runSpy, loading: ref(false), lastError: ref(null) }),
}))

type FCR = Record<string, unknown>
const currentFcr = ref<FCR | null>(null)
const getFirmwareCr = vi.fn(async () => currentFcr.value)
const transitionFirmwareCr = vi.fn().mockResolvedValue({ name: 'FCR-2026-0001', status: 'Approved' })
vi.mock('@/api/imm00', () => ({
  getFirmwareCr: () => getFirmwareCr(),
  transitionFirmwareCr: (...args: unknown[]) => transitionFirmwareCr(...args),
}))

import FirmwareCrDetailView from '@/views/document/FirmwareCrDetailView.vue'

function makeFcr(over: FCR = {}): FCR {
  return {
    name: 'FCR-2026-0001', asset_ref: 'AC-ASSET-0007', asset_name: 'Máy X-quang CTA',
    version_before: '1.0.0', version_after: '1.1.0', change_notes: 'Vá bảo mật',
    status: 'Pending Approval', allowed_transitions: [], can_approve: false,
    approved_by: null, approved_by_name: null, approved_datetime: null, applied_datetime: null,
    ...over,
  }
}

async function mountDetail() {
  const w = mount(FirmwareCrDetailView, {
    props: { id: 'FCR-2026-0001' },
    global: {
      stubs: { PageHeader: true, StatusBadge: true, RouterLink: true, Transition: false },
      mocks: { $t: (k: string) => k },
    },
  })
  await flushPromises()
  return w
}

const ALL_CTA = ['cta-approve', 'cta-deploy', 'cta-rollback']
function ctasShown(w: Awaited<ReturnType<typeof mountDetail>>): string[] {
  return ALL_CTA.filter((id) => w.find(`[data-testid="${id}"]`).exists())
}

beforeEach(() => {
  currentFcr.value = null
  runSpy.mockClear()
  transitionFirmwareCr.mockClear()
})

describe('FCR CTA gating — nút Duyệt chỉ theo allowed_transitions + can_approve', () => {
  it('Pending Approval + allowed=[Approved] + can_approve=true → nút Duyệt HIỂN THỊ', async () => {
    currentFcr.value = makeFcr({ status: 'Pending Approval', allowed_transitions: ['Approved'], can_approve: true })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-deploy"]').exists()).toBe(false)
  })

  it('Pending Approval + can_approve=false (Repair User) → nút Duyệt ẨN dù có allowed', async () => {
    // Repair User: BE lọc allowed rỗng cho nhánh duyệt + can_approve=false.
    currentFcr.value = makeFcr({ status: 'Pending Approval', allowed_transitions: ['Approved'], can_approve: false })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  it('Pending Approval + allowed=[] + can_approve=true → nút Duyệt ẨN (không có cạnh Approved)', async () => {
    currentFcr.value = makeFcr({ status: 'Pending Approval', allowed_transitions: [], can_approve: true })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
  })

  it('KHÔNG suy nút từ status thô: status=Draft + allowed=[] → nút Duyệt ẨN (dead-gate cũ đã gỡ)', async () => {
    // Dead-gate cũ: v-if="status==='Draft'" → LỘ nút Duyệt. Fix: gate theo allowed.
    currentFcr.value = makeFcr({ status: 'Draft', allowed_transitions: [], can_approve: false })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
  })
})

describe('FCR CTA gating — nút Triển khai + Khôi phục', () => {
  it('Approved + allowed=[Applied] → nút Triển khai HIỂN THỊ (không cần can_approve)', async () => {
    currentFcr.value = makeFcr({ status: 'Approved', allowed_transitions: ['Applied'], can_approve: false })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-deploy"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
  })

  it('Applied + allowed=[Rolled Back] → nút Khôi phục HIỂN THỊ', async () => {
    currentFcr.value = makeFcr({ status: 'Applied', allowed_transitions: ['Rolled Back'], can_approve: false })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-rollback"]').exists()).toBe(true)
  })

  it('Terminal (Rolled Back) + allowed=[] → 0 CTA + hint', async () => {
    currentFcr.value = makeFcr({ status: 'Rolled Back', allowed_transitions: [], can_approve: false })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  it('thiếu allowed_transitions (BE chưa emit) → mọi CTA ẩn (degrade an toàn)', async () => {
    currentFcr.value = makeFcr({ status: 'Pending Approval', allowed_transitions: undefined, can_approve: undefined })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
  })
})

describe('FCR CTA — anti-dead-control: click phát đúng action qua transition endpoint', () => {
  it('bấm Duyệt → transitionFirmwareCr(name, "approve") — KHÔNG update_firmware_cr({status})', async () => {
    currentFcr.value = makeFcr({ status: 'Pending Approval', allowed_transitions: ['Approved'], can_approve: true })
    const w = await mountDetail()
    await w.find('[data-testid="cta-approve"]').trigger('click')
    await flushPromises()
    expect(transitionFirmwareCr).toHaveBeenCalledTimes(1)
    expect(transitionFirmwareCr).toHaveBeenCalledWith('FCR-2026-0001', 'approve')
  })

  it('bấm Triển khai → transitionFirmwareCr(name, "deploy")', async () => {
    currentFcr.value = makeFcr({ status: 'Approved', allowed_transitions: ['Applied'], can_approve: false })
    const w = await mountDetail()
    await w.find('[data-testid="cta-deploy"]').trigger('click')
    await flushPromises()
    expect(transitionFirmwareCr).toHaveBeenCalledWith('FCR-2026-0001', 'deploy')
  })
})
