// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-09 / CR-51) — CMWorkOrderDetailView dòng "Phân loại rủi ro" render
// NHÃN VN từ risk_classification (Low/Medium/High/Critical → Thấp/Trung bình/Cao/
// Nghiêm trọng qua SSoT riskClassificationLabel), KHÔNG leak raw code "Class II/III"
// (field risk_class là đầu vào ma trận SLA — KHÔNG phải nhãn hiển thị).
//   • Nguồn ưu tiên: top-level `risk_classification` (BE get_repair_work_order flatten,
//     CR-51) → fallback `asset_info.risk_classification` (parity value, tồn tại sẵn).
//   • Presence-aware: rỗng/whitespace/absent → "Chưa phân loại" (KHÔNG "—", KHÔNG "Class II").
//   • Drift (ngoài 4 enum) → "Khác" (KHÔNG leak chuỗi EN thô).
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

// Base WO — risk_class LUÔN set 'Class III' để chứng minh dòng render KHÔNG dùng
// field cũ (chống revert: nếu ai đó đổi lại {{ wo.risk_class }} test đỏ ngay).
function makeWO(over: Record<string, unknown> = {}): WO {
  return {
    name: 'WO-RP-2026-00077', asset_ref: 'AC-ASSET-0077', asset_name: 'Máy thở',
    asset_category: 'Ventilator', risk_class: 'Class III', serial_no: 'SN-77',
    repair_type: 'Corrective', priority: 'Urgent', status: 'Open',
    allowed_transitions: [], open_datetime: '2026-06-01 08:00:00',
    assigned_datetime: null, completion_datetime: null,
    assigned_to: null, assigned_to_name: null, mttr_hours: null,
    sla_target_hours: 72, sla_breached: false, is_repeat_failure: false,
    incident_report: null, source_pm_wo: null, diagnosis_notes: '', root_cause_category: '',
    repair_summary: '', firmware_updated: false, firmware_change_request: null,
    dept_head_name: '', total_parts_cost: 0, spare_parts_used: [], repair_checklist: [],
    ...over,
  }
}

async function mountDetail() {
  const w = mount(CMWorkOrderDetailView, {
    props: { id: 'WO-RP-2026-00077' },
    global: { stubs: { RouterLink: true, Transition: false, ApproverSelect: true }, mocks: { $t: (k: string) => k } },
  })
  await flushPromises()
  return w
}

function riskCell(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="wo-risk-classification"]')
}

beforeEach(() => {
  setActivePinia(createPinia())
  currentWO.value = null
})

describe('CMWorkOrderDetailView — dòng "Phân loại rủi ro" (nhãn VN từ risk_classification)', () => {
  it('top-level risk_classification "High" → "Cao" (KHÔNG "High", KHÔNG "Class III")', async () => {
    currentWO.value = makeWO({ risk_classification: 'High' })
    const w = await mountDetail()
    const cell = riskCell(w)
    expect(cell.exists()).toBe(true)
    expect(cell.text()).toBe('Cao')
    expect(cell.text()).not.toContain('High')
    expect(cell.text()).not.toContain('Class')
  })

  it('top-level "Critical" → "Nghiêm trọng"', async () => {
    currentWO.value = makeWO({ risk_classification: 'Critical' })
    const w = await mountDetail()
    expect(riskCell(w).text()).toBe('Nghiêm trọng')
  })

  it('không có top-level → fallback asset_info.risk_classification "Medium" → "Trung bình"', async () => {
    currentWO.value = makeWO({ asset_info: { risk_classification: 'Medium' } })
    const w = await mountDetail()
    expect(riskCell(w).text()).toBe('Trung bình')
  })

  it('rỗng (top-level "" + asset_info thiếu) → "Chưa phân loại" (KHÔNG "—", KHÔNG "Class III")', async () => {
    currentWO.value = makeWO({ risk_classification: '', asset_info: {} })
    const w = await mountDetail()
    const cell = riskCell(w)
    expect(cell.text()).toBe('Chưa phân loại')
    expect(cell.text()).not.toContain('—')
    expect(cell.text()).not.toContain('Class')
  })

  it('whitespace-only → "Chưa phân loại"', async () => {
    currentWO.value = makeWO({ risk_classification: '   ' })
    const w = await mountDetail()
    expect(riskCell(w).text()).toBe('Chưa phân loại')
  })

  it('absent hoàn toàn (không risk_classification, không asset_info) → "Chưa phân loại", KHÔNG crash', async () => {
    currentWO.value = makeWO({})
    const w = await mountDetail()
    expect(riskCell(w).text()).toBe('Chưa phân loại')
  })

  it('drift ngoài enum "Xyz" → "Khác" (KHÔNG leak "Xyz" thô)', async () => {
    currentWO.value = makeWO({ risk_classification: 'Xyz' })
    const w = await mountDetail()
    const cell = riskCell(w)
    expect(cell.text()).toBe('Khác')
    expect(cell.text()).not.toContain('Xyz')
  })

  it('top-level THẮNG asset_info khi cả hai có (top-level là SSoT sau flatten)', async () => {
    currentWO.value = makeWO({ risk_classification: 'Low', asset_info: { risk_classification: 'Critical' } })
    const w = await mountDetail()
    expect(riskCell(w).text()).toBe('Thấp')
  })
})
