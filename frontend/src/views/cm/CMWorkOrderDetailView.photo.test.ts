// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-09 CR-15/G6) — CMWorkOrderDetailView render ảnh bằng chứng checklist
// (read-only cho QL/Kiểm toán xem bằng chứng NĐ98). photo có → <img>; null → không crash.
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

import CMWorkOrderDetailView from './CMWorkOrderDetailView.vue'

interface Row { idx: number; test_description: string; test_category: string; result: string | null; notes: string; photo?: string | null }
function row(idx: number, over: Partial<Row> = {}): Row {
  return { idx, test_description: `Mục ${idx}`, test_category: 'Safety', result: 'Pass', notes: '', photo: null, ...over }
}
function makeWO(checklist: Row[]): WO {
  return {
    name: 'WO-RP-2026-00099', asset_ref: 'AC-ASSET-0099', asset_name: 'Máy thở',
    asset_category: 'Ventilator', risk_class: 'High', serial_no: 'SN-1',
    repair_type: 'Corrective', priority: 'Urgent', status: 'Completed',
    allowed_transitions: [], open_datetime: '2026-06-01 08:00:00',
    assigned_datetime: '2026-06-01 09:00:00', completion_datetime: '2026-06-01 12:00:00',
    assigned_to: 'ktv@hospital.vn', assigned_to_name: 'KTV A', mttr_hours: 4,
    sla_target_hours: 72, sla_breached: false, is_repeat_failure: false,
    incident_report: null, source_pm_wo: null, diagnosis_notes: '', root_cause_category: '',
    repair_summary: '', firmware_updated: false, firmware_change_request: null,
    dept_head_name: '', total_parts_cost: 0, spare_parts_used: [], repair_checklist: checklist,
  }
}

async function mountDetail() {
  const w = mount(CMWorkOrderDetailView, {
    props: { id: 'WO-RP-2026-00099' },
    global: { stubs: { RouterLink: true, Transition: false, ApproverSelect: true }, mocks: { $t: (k: string) => k } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  currentWO.value = null
})

describe('CMWorkOrderDetailView — ảnh bằng chứng checklist (read-only)', () => {
  it('mục có photo → render <img> thumbnail', async () => {
    currentWO.value = makeWO([row(1, { photo: '/private/files/bc-1.jpg' }), row(2)])
    const w = await mountDetail()
    const imgs = w.findAll('img')
    expect(imgs.length).toBe(1)
    expect(imgs[0].attributes('src')).toBe('/private/files/bc-1.jpg')
  })

  it('mọi mục photo null → không render img, không crash', async () => {
    currentWO.value = makeWO([row(1, { photo: null }), row(2, { photo: null })])
    const w = await mountDetail()
    expect(w.findAll('img')).toHaveLength(0)
    // Section checklist vẫn render bình thường (không vỡ template).
    expect(w.text()).toContain('Checklist nghiệm thu')
  })
})
