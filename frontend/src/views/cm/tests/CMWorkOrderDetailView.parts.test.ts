// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-09 / AC-CR-78 — INV-PARTS-1) — CMWorkOrderDetailView cột "Phiếu xuất kho"
// phân biệt ĐỦ 3 trạng thái THẬT do BE derive (CÙNG predicate SSoT với validator
// BR-09-02 `validate_spare_parts_stock_entries`), thay vì suy diễn từ sự có mặt của mã:
//   • 'OK'        → mã phiếu.
//   • 'MISSING'   → "Chưa có phiếu xuất kho".
//   • 'NOT_FOUND' → "Phiếu xuất kho không tồn tại" (+ mã treo) — TRƯỚC vòng này dòng treo
//                   hiển thị NHƯ HỢP LỆ (badge xanh giả) rồi mới nổ 422 lúc submit.
// Kèm dải cảnh báo aggregate `parts_pending_stock_entry > 0` (cảnh báo TRƯỚC khi submit)
// và tương thích ngược khi worker BE chưa reload (2 khoá derived vắng mặt).
//
// Đây là test RENDER (mount thật + assert TEXT trong DOM, KHÔNG assert class CSS) —
// chống "state chết" kiểu CR-69 (BE trả khoá mới nhưng không .vue nào render).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get currentWO() { return currentWO.value },
    loading: false, error: null, lastApiError: null,
    fetchWorkOrder: vi.fn().mockResolvedValue(undefined),
    doAssignTechnician: vi.fn(), doConfirmInspection: vi.fn(), doCloseWorkOrder: vi.fn(),
  }),
}))

import CMWorkOrderDetailView from '@/views/cm/CMWorkOrderDetailView.vue'

function makeRow(over: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    idx: 1, item_code: 'MPN-001', item_name: 'Cảm biến oxy', manufacturer_part_no: 'MPN-001',
    qty: 1, uom: 'Cái', unit_cost: 100000, total_cost: 100000,
    stock_entry_ref: '', notes: '',
    ...over,
  }
}

function makeWO(over: Record<string, unknown> = {}): WO {
  return {
    name: 'WO-RP-2026-00078', asset_ref: 'AC-ASSET-0078', asset_name: 'Máy thở',
    asset_category: 'Ventilator', risk_class: 'Class III', risk_classification: 'High',
    serial_no: 'SN-78', repair_type: 'Corrective', priority: 'Urgent', status: 'In Repair',
    allowed_transitions: [], open_datetime: '2026-06-01 08:00:00',
    assigned_datetime: null, completion_datetime: null,
    assigned_to: null, assigned_to_name: null, mttr_hours: null,
    sla_target_hours: 72, sla_breached: false, is_repeat_failure: false,
    incident_report: null, source_pm_wo: null, diagnosis_notes: '', root_cause_category: '',
    repair_summary: '', firmware_updated: false, firmware_change_request: null,
    dept_head_name: '', total_parts_cost: 300000, spare_parts_used: [], repair_checklist: [],
    ...over,
  }
}

async function mountDetail() {
  const w = mount(CMWorkOrderDetailView, {
    props: { id: 'WO-RP-2026-00078' },
    global: { stubs: { RouterLink: true, Transition: false, ApproverSelect: true }, mocks: { $t: (k: string) => k } },
  })
  await flushPromises()
  return w
}

/** 3 dòng phủ đủ 3 trạng thái derived trong CÙNG một phiếu. */
function threeRows() {
  return [
    makeRow({ idx: 1, item_name: 'Cảm biến oxy', stock_entry_ref: 'AC-SM-2026-00011', stock_entry_status: 'OK', stock_entry_ok: 1 }),
    makeRow({ idx: 2, item_name: 'Màng lọc HEPA', stock_entry_ref: '', stock_entry_status: 'MISSING', stock_entry_ok: 0 }),
    makeRow({ idx: 3, item_name: 'Van một chiều', stock_entry_ref: 'AC-SM-KHONG-TON-TAI', stock_entry_status: 'NOT_FOUND', stock_entry_ok: 0 }),
  ]
}

beforeEach(() => {
  setActivePinia(createPinia())
  currentWO.value = null
})

describe('CMWorkOrderDetailView — cột "Phiếu xuất kho" (AC-CR-78, 3 trạng thái THẬT)', () => {
  it('FE-01: 3 dòng OK/MISSING/NOT_FOUND → DOM có đủ mã phiếu + 2 nhãn tiếng Việt đầy đủ', async () => {
    currentWO.value = makeWO({ spare_parts_used: threeRows(), parts_pending_stock_entry: 2 })
    const w = await mountDetail()
    const text = w.text()

    // Dòng OK giữ nguyên mã phiếu
    expect(text).toContain('AC-SM-2026-00011')
    // Dòng MISSING — nhãn đầy đủ, KHÔNG chỉ "Chưa có"
    expect(text).toContain('Chưa có phiếu xuất kho')
    // Dòng NOT_FOUND — nói rõ ref treo, kèm mã treo để tra cứu
    expect(text).toContain('Phiếu xuất kho không tồn tại')
    expect(text).toContain('AC-SM-KHONG-TON-TAI')

    // Tiêu đề cột việt hoá đầy đủ (LL-FE-53) — hết viết tắt "Phiếu XK"
    expect(text).toContain('Phiếu xuất kho')
    expect(text).not.toContain('Phiếu XK')
  })

  it('FE-01b: dòng NOT_FOUND KHÔNG được hiển thị như dòng hợp lệ (chống badge xanh giả)', async () => {
    currentWO.value = makeWO({
      spare_parts_used: [
        makeRow({ idx: 1, stock_entry_ref: 'AC-SM-KHONG-TON-TAI', stock_entry_status: 'NOT_FOUND', stock_entry_ok: 0 }),
      ],
      parts_pending_stock_entry: 1,
    })
    const w = await mountDetail()
    const cell = w.find('[data-testid="part-stock-cell"]')
    expect(cell.exists()).toBe(true)
    // Ô phải NÊU RÕ tình trạng treo, không chỉ in mã như trạng thái hợp lệ
    expect(cell.text()).toContain('Phiếu xuất kho không tồn tại')
  })

  it('FE-02: parts_pending_stock_entry = 2 → dải cảnh báo hiển thị đúng câu chữ', async () => {
    currentWO.value = makeWO({ spare_parts_used: threeRows(), parts_pending_stock_entry: 2 })
    const w = await mountDetail()
    const banner = w.find('[data-testid="parts-pending-banner"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toBe(
      'Còn 2 dòng vật tư chưa có phiếu xuất kho hợp lệ — chưa thể hoàn tất phiếu sửa chữa.',
    )
    // a11y: cảnh báo chặn hoàn tất phiếu phải được screen-reader công bố
    expect(banner.attributes('role')).toBe('alert')
    // panel tóm tắt đồng bộ: "3 mục (2 chưa xuất kho)"
    expect(w.find('[data-testid="parts-summary"]').text().replace(/\s+/g, ' ')).toBe('3 mục (2 chưa xuất kho)')
  })

  it('FE-02b: parts_pending_stock_entry = 0 → KHÔNG có banner trong DOM', async () => {
    currentWO.value = makeWO({
      spare_parts_used: [
        makeRow({ idx: 1, stock_entry_ref: 'AC-SM-2026-00011', stock_entry_status: 'OK', stock_entry_ok: 1 }),
      ],
      parts_pending_stock_entry: 0,
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="parts-pending-banner"]').exists()).toBe(false)
    expect(w.text()).not.toContain('chưa có phiếu xuất kho hợp lệ')
    expect(w.find('[data-testid="parts-summary"]').text().replace(/\s+/g, ' ')).toBe('1 mục')
  })

  it('FE-03: payload CŨ (worker chưa reload — thiếu 2 khoá derived + aggregate) → hành vi cũ, không throw, không banner', async () => {
    currentWO.value = makeWO({
      spare_parts_used: [
        makeRow({ idx: 1, item_name: 'Cảm biến oxy', stock_entry_ref: 'AC-SM-2026-00011' }),
        makeRow({ idx: 2, item_name: 'Màng lọc HEPA', stock_entry_ref: '' }),
      ],
      // parts_pending_stock_entry cố ý VẮNG MẶT
    })
    const w = await mountDetail()
    const text = w.text()
    expect(text).toContain('AC-SM-2026-00011')   // có ref ⇒ hiện mã (như trước)
    expect(text).toContain('Chưa có')            // không ref ⇒ "Chưa có" (như trước)
    expect(text).not.toContain('Phiếu xuất kho không tồn tại')
    expect(w.find('[data-testid="parts-pending-banner"]').exists()).toBe(false)
    expect(w.find('[data-testid="parts-summary"]').text().replace(/\s+/g, ' ')).toBe('2 mục')
  })

  it('FE-03b: khoá derived hỏng/drift (giá trị lạ) → rơi về hành vi cũ, KHÔNG leak chuỗi thô', async () => {
    currentWO.value = makeWO({
      spare_parts_used: [
        makeRow({ idx: 1, stock_entry_ref: 'AC-SM-2026-00011', stock_entry_status: 'PENDING_XYZ' }),
      ],
    })
    const w = await mountDetail()
    expect(w.text()).toContain('AC-SM-2026-00011')
    expect(w.text()).not.toContain('PENDING_XYZ')
  })

  it('FE-03c: parts_pending_stock_entry sai kiểu (chuỗi) → coi như vắng mặt, KHÔNG banner', async () => {
    currentWO.value = makeWO({
      spare_parts_used: threeRows(),
      parts_pending_stock_entry: '2' as unknown as number,
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="parts-pending-banner"]').exists()).toBe(false)
  })
})
