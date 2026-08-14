// TDD — IMM-16 CAPADetailView server-driven CTA gate (ADR-IMM-16-01 / GATE-8 /
// LL-FE-51). Client-map TRANSITIONS đã bị XOÁ: nút chuyển trạng thái render
// THEO `capa.allowed_transitions` do get_capa emit (dẫn xuất từ CÙNG
// _CAPA_TRANSITIONS mà advance_capa_state enforce). Parity get_finding/get_audit.
//
//   - matrix workflow_state × allowed_transitions → render ĐÚNG tập nút.
//   - allowed_transitions rỗng & chưa Closed → 0 nút chuyển + hint không-đủ-quyền.
//   - click 'Bắt đầu điều tra' → store.actionAdvanceCapa(name,'Investigating').
//   - Verification allowed=['Closed','Re-opened'] → nút Đóng + Mở lại (gate xác minh).
//   - degrade an toàn 0 nút khi allowed_transitions undefined (BE cũ).
//   - anti-desync: server-set khác map cũ → render THEO server-set (không hardcode).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { CapaDetail } from '@/api/imm16'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'CAPA-2026-00001' } }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    loading: { value: false },
    run: (fn: () => Promise<unknown>) => fn(),
  }),
}))

const fetchCapaDetailSpy = vi.fn<() => Promise<CapaDetail>>()
const actionAdvanceCapaSpy = vi.fn().mockResolvedValue({ workflow_state: 'Investigating' })
vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    fetchCapaDetail: fetchCapaDetailSpy,
    actionUpdateCapaFields: vi.fn(),
    actionAdvanceCapa: actionAdvanceCapaSpy,
    actionEffectivenessCheck: vi.fn(),
  }),
}))

import CAPADetailView from '@/views/incident/CAPADetailView.vue'

// BaseModal stub PHẢI render slot (default + footer) để click được nút xác nhận
// trong modal chuyển trạng thái. Các stub khác vô hại.
const stubs = {
  BaseModal: { template: '<div class="modal-stub"><slot /><slot name="footer" /></div>' },
  SkeletonLoader: true, RouterLink: true,
  // RecordHistory expose reload() — refreshAll() (sau confirm transition) gọi
  // historyRef.value?.reload(); stub trần thiếu method → unhandled rejection.
  RecordHistory: { template: '<div />', methods: { reload() {} } },
}

function baseCapa(overrides: Partial<CapaDetail>): CapaDetail {
  return {
    name: 'CAPA-2026-00001',
    asset: 'ACC-ASS-0001',
    severity: 'High',
    status: 'In Progress',
    workflow_state: 'Investigating',
    source_type: 'Finding',
    source_ref: null,
    due_date: null,
    closed_date: null,
    effectiveness_check: null,
    ...overrides,
  } as CapaDetail
}

async function mountWith(overrides: Partial<CapaDetail>) {
  fetchCapaDetailSpy.mockResolvedValue(baseCapa(overrides))
  const wrapper = mount(CAPADetailView, { global: { stubs } })
  await flushPromises()
  return wrapper
}

describe('CAPADetailView — server-driven CTA gate (allowed_transitions)', () => {
  beforeEach(() => {
    fetchCapaDetailSpy.mockReset()
    actionAdvanceCapaSpy.mockClear()
  })

  // Matrix: mỗi state với allowed_transitions do server emit → đúng tập nút.
  it('Open + allowed=[Investigating] → chỉ nút "Bắt đầu điều tra"', async () => {
    const w = await mountWith({
      workflow_state: 'Open', status: 'Open',
      allowed_transitions: ['Investigating'], can_advance: true,
    })
    expect(w.find('[data-testid="cta-transition-Investigating"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-transition-Action Plan"]').exists()).toBe(false)
    expect(w.text()).toContain('Bắt đầu điều tra')
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-reopen"]').exists()).toBe(false)
  })

  it('Investigating + allowed=[Action Plan] → chỉ nút "Lập kế hoạch hành động"', async () => {
    const w = await mountWith({ allowed_transitions: ['Action Plan'], can_advance: true })
    expect(w.find('[data-testid="cta-transition-Action Plan"]').exists()).toBe(true)
    expect(w.text()).toContain('Lập kế hoạch hành động')
    expect(w.find('[data-testid="cta-transition-Investigating"]').exists()).toBe(false)
  })

  it('Implementation + allowed=[Verification] → nút "Chuyển sang xác minh"', async () => {
    const w = await mountWith({
      workflow_state: 'Implementation', allowed_transitions: ['Verification'], can_advance: true,
    })
    expect(w.find('[data-testid="cta-transition-Verification"]').exists()).toBe(true)
    expect(w.text()).toContain('Chuyển sang xác minh')
  })

  // Verification: allowed=['Closed','Re-opened'] → nút Đóng + Mở lại (gate xác
  // minh), KHÔNG render 2 target này thành nút transition thường.
  it('Verification + allowed=[Closed,Re-opened] → nút Đóng + Mở lại (gate xác minh)', async () => {
    const w = await mountWith({
      workflow_state: 'Verification',
      allowed_transitions: ['Closed', 'Re-opened'], can_advance: true,
    })
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-reopen"]').exists()).toBe(true)
    // 'Closed'/'Re-opened' KHÔNG render như nút transition thường.
    expect(w.find('[data-testid="cta-transition-Closed"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-transition-Re-opened"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(false)
  })

  // Re-opened state: server emit ['Investigating'] → nút quay lại điều tra.
  it('Re-opened + allowed=[Investigating] → nút "Bắt đầu điều tra"', async () => {
    const w = await mountWith({
      workflow_state: 'Re-opened', allowed_transitions: ['Investigating'], can_advance: true,
    })
    expect(w.find('[data-testid="cta-transition-Investigating"]').exists()).toBe(true)
  })

  // allowed_transitions rỗng & chưa Closed → 0 nút chuyển + hint không đủ quyền.
  it('allowed=[] (viewer read-only) & chưa Closed → 0 nút chuyển + hint', async () => {
    const w = await mountWith({
      workflow_state: 'Investigating', allowed_transitions: [], can_advance: false,
    })
    expect(w.findAll('[data-testid^="cta-transition-"]').length).toBe(0)
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-reopen"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  // degrade an toàn: allowed_transitions undefined (BE cũ) → 0 nút chuyển.
  it('allowed_transitions undefined (BE cũ) → 0 nút chuyển (degrade an toàn)', async () => {
    const w = await mountWith({ workflow_state: 'Investigating' })
    expect(w.findAll('[data-testid^="cta-transition-"]').length).toBe(0)
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-reopen"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  // Closed terminal → 0 nút chuyển, hiển thị badge "đã đóng", KHÔNG hint.
  it('Closed → 0 nút chuyển + badge đã đóng, KHÔNG hint', async () => {
    const w = await mountWith({
      workflow_state: 'Closed', status: 'Closed', allowed_transitions: [], can_advance: true,
    })
    expect(w.findAll('[data-testid^="cta-transition-"]').length).toBe(0)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(false)
    expect(w.text()).toContain('đã đóng')
  })

  // Anti-desync: server-set khác client-map cũ (map cũ ở Investigating chỉ cho
  // 'Action Plan') → render THEO server-set (Verification) chứ không map cũ.
  it('anti-desync: Investigating + allowed=[Verification] (khác map cũ) → render theo server', async () => {
    const w = await mountWith({
      workflow_state: 'Investigating', allowed_transitions: ['Verification'], can_advance: true,
    })
    // Server nói Verification → render nút Verification (map cũ sẽ ra Action Plan).
    expect(w.find('[data-testid="cta-transition-Verification"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-transition-Action Plan"]').exists()).toBe(false)
  })

  // Click transition CTA → mở modal → xác nhận gọi actionAdvanceCapa(name,'Investigating').
  it("click 'Bắt đầu điều tra' → confirm gọi actionAdvanceCapa(name,'Investigating')", async () => {
    const w = await mountWith({
      workflow_state: 'Open', status: 'Open',
      allowed_transitions: ['Investigating'], can_advance: true,
    })
    await w.find('[data-testid="cta-transition-Investigating"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="transition-confirm"]').trigger('click')
    await flushPromises()
    expect(actionAdvanceCapaSpy).toHaveBeenCalledTimes(1)
    expect(actionAdvanceCapaSpy.mock.calls[0][0]).toBe('CAPA-2026-00001')
    expect(actionAdvanceCapaSpy.mock.calls[0][1]).toBe('Investigating')
  })
})
