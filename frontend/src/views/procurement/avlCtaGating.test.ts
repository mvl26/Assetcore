// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho AVL (IMM-03).
//
// AvlListView gate 100% nút hành động (Phê duyệt / Phục hồi Approved / Đình chỉ)
// theo `row.allowed_transitions` (BE derive từ `_AVL_VALID_TRANSITIONS`, đã LỌC
// theo capability/role caller) — KHÔNG hardcode `a.workflow_state === 'Draft' |
// 'Approved' | 'Conditional'`.
//
// RED trước fix (dead-gate): nút Phê duyệt render v-if="workflow_state==='Draft'"
// + Đình chỉ v-if="'Approved'||'Conditional'" → (1) Suspended/Conditional KHÔNG có
// nút 'Phục hồi Approved' dù fixture cho phép (dead-functionality); (2) nút hiện
// theo state client-map, không theo role thực → lộ nút sai quyền. Ngoài ra
// doApproveAvl cũ prompt('admin@example.com') → approver client-spoof.
//
// Sau fix: nút render CHỈ khi action ∈ allowed_transitions; approve KHÔNG kèm
// approver (server derive frappe.session.user); allowed_transitions rỗng → 0 nút.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { AvlListItem } from '@/types/imm03'

// ── Store mock: kiểm soát avlEntries + spy transition actions ─────────────────
let avlRows: AvlListItem[] = []
const approveAvlEntry = vi.fn().mockResolvedValue(true)
const suspendAvlEntry = vi.fn().mockResolvedValue(true)
const setAvlConditional = vi.fn().mockResolvedValue(true)
const fetchAvl = vi.fn().mockResolvedValue(undefined)
const fetchKpis = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm03', () => ({
  useImm03Store: () => ({
    get avlEntries() { return avlRows },
    kpis: null,
    loading: false,
    error: null,
    lastApiError: null,
    clearError: vi.fn(),
    fetchAvl,
    fetchKpis,
    approveAvlEntry,
    suspendAvlEntry,
    setAvlConditional,
  }),
}))

// notify.confirm → true (approve/restore đi tiếp); show/fromError no-op.
const notifyShow = vi.fn()
const notifyFromError = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({
    show: notifyShow,
    fromError: notifyFromError,
    fromOk: vi.fn(),
    confirm: vi.fn().mockResolvedValue(true),
  }),
}))

import AvlListView from './AvlListView.vue'

const stubs = {
  PageHeader: true,
  FilterToggleButton: true,
  ListFilterBar: true,
  KpiCard: true,
  StatusBadge: true,
  // BaseModal stub PHẢI render slot mặc định + footer để click nút xác nhận đình chỉ.
  BaseModal: { template: '<div class="modal-stub"><slot /><slot name="footer" /></div>' },
}

function row(over: Partial<AvlListItem> = {}): AvlListItem {
  return {
    name: 'AVL-2026-0001',
    supplier: 'SUP-2026-00001',
    vendor_name: 'Philips Healthcare',
    device_category: 'CAT-0001',
    device_category_name: 'Chẩn đoán hình ảnh',
    workflow_state: 'Draft',
    valid_from: '2026-01-01',
    valid_to: '2028-01-01',
    allowed_transitions: [],
    ...over,
  }
}

async function mountWith(rows: AvlListItem[]) {
  avlRows = rows
  const w = mount(AvlListView, { global: { stubs } })
  await flushPromises()
  return w
}

// Thứ tự khớp thứ tự render nút trong actions-col (approve → cấp/hạ có điều kiện →
// phục hồi → đình chỉ). `shown` trả theo thứ tự CTA này.
const CTA = ['cta-approve', 'cta-grant-conditional', 'cta-downgrade-conditional', 'cta-restore', 'cta-suspend']
function shown(w: Awaited<ReturnType<typeof mountWith>>): string[] {
  return CTA.filter((id) => w.find(`[data-testid="${id}"]`).exists())
}

beforeEach(() => {
  approveAvlEntry.mockClear()
  suspendAvlEntry.mockClear()
  setAvlConditional.mockClear()
  notifyShow.mockClear()
  notifyFromError.mockClear()
})

describe('AvlListView — server-driven CTA gating theo allowed_transitions', () => {
  // Matrix khớp EXACT fixture 'IMM-03 AVL Workflow'.
  it("Draft (['Phê duyệt AVL','Cấp Conditional']) → nút Phê duyệt + Cấp có điều kiện", async () => {
    const w = await mountWith([row({ workflow_state: 'Draft', allowed_transitions: ['Phê duyệt AVL', 'Cấp Conditional'] })])
    expect(shown(w)).toEqual(['cta-approve', 'cta-grant-conditional'])
  })

  it("Approved (['Hạ xuống Conditional','Đình chỉ']) → nút Hạ xuống có điều kiện + Đình chỉ", async () => {
    const w = await mountWith([row({ workflow_state: 'Approved', allowed_transitions: ['Hạ xuống Conditional', 'Đình chỉ'] })])
    expect(shown(w)).toEqual(['cta-downgrade-conditional', 'cta-suspend'])
  })

  it("Conditional (['Phục hồi Approved','Đình chỉ']) → Phục hồi Approved + Đình chỉ", async () => {
    const w = await mountWith([row({ workflow_state: 'Conditional', allowed_transitions: ['Phục hồi Approved', 'Đình chỉ'] })])
    expect(shown(w)).toEqual(['cta-restore', 'cta-suspend'])
  })

  it("Suspended (['Phục hồi Approved']) → HIỆN nút Phục hồi Approved (đóng dead-functionality)", async () => {
    const w = await mountWith([row({ workflow_state: 'Suspended', allowed_transitions: ['Phục hồi Approved'] })])
    expect(shown(w)).toEqual(['cta-restore'])
  })

  it('Expired ([]) → 0 nút transition', async () => {
    const w = await mountWith([row({ workflow_state: 'Expired', allowed_transitions: [] })])
    expect(shown(w)).toEqual([])
  })

  it('allowed_transitions undefined (BE cũ chưa reload) → 0 nút (degrade an toàn, không dead-control 403)', async () => {
    const w = await mountWith([row({ workflow_state: 'Draft', allowed_transitions: undefined })])
    expect(shown(w)).toEqual([])
  })

  it('anti-desync: gate THEO server-set, không theo workflow_state — Draft mà allowed rỗng → 0 nút', async () => {
    const w = await mountWith([row({ workflow_state: 'Draft', allowed_transitions: [] })])
    expect(shown(w)).toEqual([])
  })
})

describe('AvlListView — click CTA phát action đúng (anti dead-control)', () => {
  it("click Phê duyệt → store.approveAvlEntry(name) KHÔNG kèm approver", async () => {
    const w = await mountWith([row({ name: 'AVL-2026-0007', workflow_state: 'Draft', allowed_transitions: ['Phê duyệt AVL'] })])
    await w.find('[data-testid="cta-approve"]').trigger('click')
    await flushPromises()
    expect(approveAvlEntry).toHaveBeenCalledTimes(1)
    expect(approveAvlEntry).toHaveBeenCalledWith('AVL-2026-0007')
    expect(approveAvlEntry.mock.calls[0]).toHaveLength(1) // chỉ name — không approver email
    expect(notifyShow).toHaveBeenCalled()
  })

  it("click Phục hồi Approved (Suspended) → store.approveAvlEntry(name) 1 tham số", async () => {
    const w = await mountWith([row({ name: 'AVL-2026-0009', workflow_state: 'Suspended', allowed_transitions: ['Phục hồi Approved'] })])
    await w.find('[data-testid="cta-restore"]').trigger('click')
    await flushPromises()
    expect(approveAvlEntry).toHaveBeenCalledWith('AVL-2026-0009')
    expect(approveAvlEntry.mock.calls[0]).toHaveLength(1)
  })

  it('click Đình chỉ → mở modal lý do, xác nhận → store.suspendAvlEntry(name, reason)', async () => {
    const w = await mountWith([row({ name: 'AVL-2026-0011', workflow_state: 'Approved', allowed_transitions: ['Đình chỉ'] })])
    await w.find('[data-testid="cta-suspend"]').trigger('click')
    await flushPromises()
    // modal mở — nút xác nhận disabled khi chưa có lý do
    const confirmBtn = w.find('[data-testid="cta-suspend-confirm"]')
    expect(confirmBtn.exists()).toBe(true)
    expect(confirmBtn.attributes('disabled')).toBeDefined()
    // nhập lý do → xác nhận
    await w.find('[data-testid="avl-suspend-reason"]').setValue('Chứng chỉ ISO 13485 hết hạn')
    await w.find('[data-testid="cta-suspend-confirm"]').trigger('click')
    await flushPromises()
    expect(suspendAvlEntry).toHaveBeenCalledWith('AVL-2026-0011', 'Chứng chỉ ISO 13485 hết hạn')
  })

  it("click Cấp có điều kiện (Draft) → nhập điều kiện → store.setAvlConditional(name, notes) 1 lần", async () => {
    const w = await mountWith([row({ name: 'AVL-2026-0013', workflow_state: 'Draft', allowed_transitions: ['Cấp Conditional'] })])
    await w.find('[data-testid="cta-grant-conditional"]').trigger('click')
    await flushPromises()
    // modal mở — nút xác nhận disabled khi chưa nhập điều kiện (condition_notes bắt buộc)
    const confirmBtn = w.find('[data-testid="cta-conditional-confirm"]')
    expect(confirmBtn.exists()).toBe(true)
    expect(confirmBtn.attributes('disabled')).toBeDefined()
    await w.find('[data-testid="avl-condition-notes"]').setValue('Chỉ đạt 2/3 tiêu chí')
    await w.find('[data-testid="cta-conditional-confirm"]').trigger('click')
    await flushPromises()
    expect(setAvlConditional).toHaveBeenCalledTimes(1)
    expect(setAvlConditional).toHaveBeenCalledWith('AVL-2026-0013', 'Chỉ đạt 2/3 tiêu chí')
    expect(notifyShow).toHaveBeenCalled()
  })

  it("click Hạ xuống có điều kiện (Approved) → store.setAvlConditional(name, notes)", async () => {
    const w = await mountWith([row({ name: 'AVL-2026-0015', workflow_state: 'Approved', allowed_transitions: ['Hạ xuống Conditional'] })])
    await w.find('[data-testid="cta-downgrade-conditional"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="avl-condition-notes"]').setValue('Phát sinh 1 khiếu nại chất lượng chưa đóng')
    await w.find('[data-testid="cta-conditional-confirm"]').trigger('click')
    await flushPromises()
    expect(setAvlConditional).toHaveBeenCalledWith('AVL-2026-0015', 'Phát sinh 1 khiếu nại chất lượng chưa đóng')
  })
})

// ── API layer: approveAvl KHÔNG gửi approver (chống spoof) ─────────────────────
describe('api/imm03 approveAvl — payload chỉ có name', () => {
  it('approveAvl(name) → frappePost approve_avl chỉ { name }, không approver/approval_doc', async () => {
    vi.resetModules()
    const frappePost = vi.fn().mockResolvedValue({ name: 'AVL-2026-0001', workflow_state: 'Approved' })
    vi.doMock('@/api/helpers', () => ({
      frappeGet: vi.fn(),
      frappePost: (...a: unknown[]) => frappePost(...a),
    }))
    const { approveAvl } = await import('@/api/imm03')
    await approveAvl('AVL-2026-0001')
    expect(frappePost).toHaveBeenCalledWith(
      '/api/method/assetcore.api.imm03.approve_avl',
      { name: 'AVL-2026-0001' },
    )
    vi.doUnmock('@/api/helpers')
  })

  it('setAvlConditional(name, notes) → frappePost set_avl_conditional { name, condition_notes }', async () => {
    vi.resetModules()
    const frappePost = vi.fn().mockResolvedValue({ name: 'AVL-2026-0001', workflow_state: 'Conditional' })
    vi.doMock('@/api/helpers', () => ({
      frappeGet: vi.fn(),
      frappePost: (...a: unknown[]) => frappePost(...a),
    }))
    const { setAvlConditional: apiSetConditional } = await import('@/api/imm03')
    await apiSetConditional('AVL-2026-0001', 'Chỉ đạt 2/3 tiêu chí')
    expect(frappePost).toHaveBeenCalledWith(
      '/api/method/assetcore.api.imm03.set_avl_conditional',
      { name: 'AVL-2026-0001', condition_notes: 'Chỉ đạt 2/3 tiêu chí' },
    )
    vi.doUnmock('@/api/helpers')
  })
})
