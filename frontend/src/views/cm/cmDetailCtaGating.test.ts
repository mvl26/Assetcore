// FE-CMCTA-1..7 (AC-CR-82) — CTA SERVER-DRIVEN cho màn chi tiết phiếu SỬA CHỮA:
// CMWorkOrderDetailView render 7 nút TỪ 6 khoá `available_actions` do BE phát
// (`get_repair_work_order` → services.imm09._build_repair_available_actions).
// Mirror `pmWorkOrderDetailServerActions.test.ts` (nửa PM, AC-CR-77) — đóng nốt
// asymmetry mobile CR-74.
//
// Vì sao test này tồn tại:
//   • "nút chết" — trước đây FE tự tính `can('repair.*') && allowedTransitions.includes()`
//     ⇒ persona thiếu capability vẫn thấy nút BẤM ĐƯỢC rồi ăn 403/422 câm. Nay `enabled`
//     do SERVER quyết, nút hiện dạng disabled + `reason` tiếng Việt của SERVER.
//   • "nút ma" — `Cancelled` KHÔNG có endpoint ⇒ BE không phát ⇒ FE không thể vẽ nút
//     huỷ phiếu (test khoá tập key render được).
//   • "dead-end D-CM-3" — `start_repair` có endpoint LIVE (`api/imm09.py:136`) nhưng
//     màn Chi tiết trước đây 0 nút ⇒ thêm `cta-start-repair`.
//   • back-compat — payload CŨ (thiếu `available_actions`, worker BE chưa reload) PHẢI
//     giữ NGUYÊN hành vi gate cũ: không màn trắng, không mất CTA.
//
// Bất biến kiểm ở đây (mirror D9 phía BE): `enabled === false ⟹ reason !== ""`, và
// tooltip/nhãn hiển thị ĐÚNG chuỗi server (KHÔNG phải hằng FE).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

// Capability FE điều khiển được: chế độ server-driven PHẢI KHÔNG phụ thuộc giá trị này
// cho 6 khoá (đó chính là điểm của AC-CR-82) — có test cố tình đặt can()=false.
let canImpl: (c: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)
const doStartRepair = vi.fn().mockResolvedValue(true)
const doConfirmInspection = vi.fn().mockResolvedValue(true)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get currentWO() { return currentWO.value },
    loading: false,
    error: null,
    lastApiError: null,
    fetchWorkOrder,
    doAssignTechnician: vi.fn().mockResolvedValue(true),
    doConfirmInspection,
    doCloseWorkOrder: vi.fn().mockResolvedValue(true),
    doStartRepair,
  }),
}))

import CMWorkOrderDetailView from './CMWorkOrderDetailView.vue'

// ─── SSoT mirror của BE (hợp đồng `docs/imm-09/05 §15`) ────────────────────────
// 6 khoá, THỨ TỰ CỐ ĐỊNH như BE phát.
const ACTION_KEYS = [
  'assign_technician',
  'submit_diagnosis',
  'request_spare_parts',
  'start_repair',
  'close_work_order',
  'confirm_inspection',
] as const
type ActionKey = (typeof ACTION_KEYS)[number]

// Ma trận trạng-thái-cho-phép (mirror `*_FROM` phía BE; `request_spare_parts` advertise
// HẸP HƠN enforcement theo ADR-IMM09-CTA-02 — chỉ-giảm, fail-safe).
const ALLOWED_FROM: Record<ActionKey, string[]> = {
  assign_technician: ['Open'],
  submit_diagnosis: ['Assigned', 'Diagnosing'],
  request_spare_parts: ['Assigned', 'Diagnosing', 'Pending Parts', 'In Repair'],
  start_repair: ['Assigned', 'Diagnosing', 'Pending Parts'],
  close_work_order: ['In Repair'],
  confirm_inspection: ['Pending Inspection'],
}
const ALL_STATUSES = [
  'Open', 'Assigned', 'Diagnosing', 'Pending Parts', 'In Repair',
  'Pending Inspection', 'Completed', 'Cannot Repair', 'Cancelled',
]

// Nhãn/lý do "của SERVER" cố ý KHÁC hằng FE (`CTA_LABEL_FALLBACK`) để chứng minh nhãn
// + tooltip render ra là chuỗi PAYLOAD, không phải chuỗi FE bịa.
const SRV_LABEL: Record<ActionKey, string> = {
  assign_technician: 'Giao việc (nhãn máy chủ)',
  submit_diagnosis: 'Gửi chẩn đoán (nhãn máy chủ)',
  request_spare_parts: 'Đề nghị vật tư (nhãn máy chủ)',
  start_repair: 'Khởi công sửa chữa (nhãn máy chủ)',
  close_work_order: 'Đóng phiếu sửa chữa (nhãn máy chủ)',
  confirm_inspection: 'Xác nhận nghiệm thu (nhãn máy chủ)',
}
const REASON_TRANSITION = 'Phiếu không ở trạng thái cho phép giao việc'
const REASON_SOD = 'Người nghiệm thu phải khác người đóng phiếu (phân tách trách nhiệm)'

/** available_actions mẫu: ĐÚNG 6 phần tử, thứ tự CỐ ĐỊNH như BE phát. */
function actionsFor(
  status: string,
  over: Partial<Record<ActionKey, { enabled?: boolean; reason?: string; label?: string }>> = {},
) {
  return ACTION_KEYS.map((key) => {
    const allowed = ALLOWED_FROM[key].includes(status)
    const base = {
      key,
      label: SRV_LABEL[key],
      route: '',
      enabled: allowed,
      // D9: enabled=false ⟺ reason≠"" (hằng bậc transition khi sai pha).
      reason: allowed ? '' : REASON_TRANSITION,
    }
    return over[key] ? { ...base, ...over[key] } : base
  })
}

function makeWO(over: WO = {}): WO {
  const status = (over.status as string) ?? 'Open'
  return {
    name: 'WO-RP-2026-00099', asset_ref: 'AC-ASSET-0099', asset_name: 'Máy thở CTA',
    asset_category: 'Ventilator', risk_class: 'High', serial_no: 'SN-CTA-1',
    repair_type: 'Corrective', priority: 'Urgent', status,
    allowed_transitions: [],
    available_actions: actionsFor(status),
    open_datetime: '2026-06-01 08:00:00', assigned_datetime: '2026-06-01 09:00:00',
    completion_datetime: null, assigned_to: 'ktv@hospital.vn', assigned_to_name: 'KTV A',
    mttr_hours: null, sla_target_hours: 72, sla_breached: false, is_repeat_failure: false,
    incident_report: null, source_pm_wo: null, diagnosis_notes: '', root_cause_category: '',
    repair_summary: '', firmware_updated: false, firmware_change_request: null,
    dept_head_name: '', total_parts_cost: 0, spare_parts_used: [], repair_checklist: [],
    ...over,
  }
}

async function mountDetail() {
  const w = mount(CMWorkOrderDetailView, {
    props: { id: 'WO-RP-2026-00099' },
    global: { stubs: { RouterLink: true, Transition: false }, mocks: { $t: (k: string) => k } },
  })
  await flushPromises()
  return w
}

// testid → khoá server (7 nút ↔ 6 khoá; `close_work_order` dùng chung 2 nút).
const CTA_KEY_BY_TESTID: Record<string, ActionKey> = {
  'cta-assign': 'assign_technician',
  'cta-diagnose': 'submit_diagnosis',
  'cta-parts': 'request_spare_parts',
  'cta-start-repair': 'start_repair',
  'cta-complete': 'close_work_order',
  'cta-cannot-repair': 'close_work_order',
  'cta-confirm-inspection': 'confirm_inspection',
}
const ALL_TESTIDS = Object.keys(CTA_KEY_BY_TESTID)

type Wrapper = Awaited<ReturnType<typeof mountDetail>>
function ctasShown(w: Wrapper): string[] {
  return ALL_TESTIDS.filter((id) => w.find(`[data-testid="${id}"]`).exists())
}
function ctasEnabled(w: Wrapper): string[] {
  return ALL_TESTIDS.filter((id) => {
    const el = w.find(`[data-testid="${id}"]`)
    return el.exists() && (el.element as HTMLButtonElement).disabled === false
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  fetchWorkOrder.mockClear()
  doStartRepair.mockClear()
  doConfirmInspection.mockClear()
  currentWO.value = null
  canImpl = () => true
})

describe('FE-CMCTA-1 — nút bị SERVER khoá: hiện + disabled + title == reason của server', () => {
  it('assign_technician.enabled=0 ⇒ «Giao việc» disabled, title == chuỗi reason (đọc từ DOM)', async () => {
    currentWO.value = makeWO({
      status: 'Open',
      available_actions: actionsFor('Open', {
        assign_technician: { enabled: false, reason: REASON_TRANSITION },
      }),
    })
    const w = await mountDetail()
    const btn = w.find('[data-testid="cta-assign"]')
    expect(btn.exists()).toBe(true) // KHÔNG ẩn — ẩn là mất thông tin lý do
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
    expect(btn.attributes('title')).toBe(REASON_TRANSITION)
    expect(btn.attributes('aria-disabled')).toBe('true')
    // Nhãn hiển thị = chuỗi SERVER, không phải hằng FE.
    expect(btn.text()).toContain('Giao việc (nhãn máy chủ)')
  })

  it('server-driven KHÔNG phụ thuộc capability client: can()=false nhưng enabled=1 ⇒ nút bấm được', async () => {
    canImpl = () => false
    currentWO.value = makeWO({ status: 'Open' })
    const w = await mountDetail()
    const btn = w.find('[data-testid="cta-assign"]')
    expect(btn.exists()).toBe(true)
    expect((btn.element as HTMLButtonElement).disabled).toBe(false)
  })
})

describe('FE-CMCTA-2 — INVARIANT A9: không nút CTA enabled nào nằm ngoài tập enabled của server', () => {
  it.each(ALL_STATUSES)('%s ⇒ tập nút enabled ⊆ tập khoá enabled server (0 nút ma)', async (status) => {
    currentWO.value = makeWO({ status })
    const w = await mountDetail()
    const srvEnabledKeys = new Set(
      (currentWO.value.available_actions as { key: ActionKey; enabled: boolean }[])
        .filter((a) => a.enabled)
        .map((a) => a.key),
    )
    for (const id of ctasEnabled(w)) {
      expect(srvEnabledKeys.has(CTA_KEY_BY_TESTID[id])).toBe(true)
    }
    // Chiều ngược: mọi khoá server bật PHẢI có ít nhất 1 nút bấm được (không nuốt CTA).
    for (const key of srvEnabledKeys) {
      const ids = ALL_TESTIDS.filter((id) => CTA_KEY_BY_TESTID[id] === key)
      expect(ids.some((id) => ctasEnabled(w).includes(id))).toBe(true)
    }
  })

  it('chỉ start_repair bật ⇒ DOM không chứa nút CTA enabled nào khác (cr82_k)', async () => {
    currentWO.value = makeWO({
      status: 'Pending Parts',
      available_actions: actionsFor('Pending Parts', {
        submit_diagnosis: { enabled: false, reason: REASON_TRANSITION },
        request_spare_parts: { enabled: false, reason: REASON_TRANSITION },
      }),
    })
    const w = await mountDetail()
    expect(ctasEnabled(w)).toEqual(['cta-start-repair'])
  })

  it('D9 — mọi payload dùng trong test: enabled=false ⟺ reason ≠ ""', () => {
    for (const status of ALL_STATUSES) {
      for (const a of actionsFor(status)) {
        expect(a.enabled === false).toBe(a.reason !== '')
      }
    }
  })
})

describe('FE-CMCTA-3 — «Bắt đầu sửa chữa» (D-CM-3): nút MỚI, click gọi store đúng 1 lần', () => {
  it('start_repair.enabled=1 ⇒ cta-start-repair hiện, bấm được, gọi doStartRepair 1 lần', async () => {
    currentWO.value = makeWO({ status: 'Diagnosing' })
    const w = await mountDetail()
    const btn = w.find('[data-testid="cta-start-repair"]')
    expect(btn.exists()).toBe(true)
    expect((btn.element as HTMLButtonElement).disabled).toBe(false)
    await btn.trigger('click')
    await flushPromises()
    expect(doStartRepair).toHaveBeenCalledTimes(1)
    expect(doStartRepair).toHaveBeenCalledWith('WO-RP-2026-00099')
  })

  it('start_repair.enabled=0 ⇒ click là no-op (không gọi store)', async () => {
    currentWO.value = makeWO({ status: 'Open' })
    const w = await mountDetail()
    const btn = w.find('[data-testid="cta-start-repair"]')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
    await btn.trigger('click')
    await flushPromises()
    expect(doStartRepair).not.toHaveBeenCalled()
  })
})

describe('FE-CMCTA-4 — FALLBACK: payload KHÔNG có available_actions ⇒ gate cũ nguyên vẹn', () => {
  const REPAIR_TRANSITIONS: Record<string, string[]> = {
    'Open': ['Assigned', 'Cancelled'],
    'Assigned': ['Diagnosing', 'Cancelled'],
    'Diagnosing': ['In Repair', 'Pending Parts', 'Cancelled'],
    'Pending Parts': ['In Repair', 'Cancelled'],
    'In Repair': ['Pending Inspection', 'Cannot Repair', 'Cancelled'],
    'Pending Inspection': ['Completed', 'In Repair', 'Cancelled'],
  }

  it.each([
    ['Open', ['cta-assign']],
    ['Assigned', ['cta-diagnose']],
    ['Diagnosing', ['cta-diagnose', 'cta-parts']],
    ['Pending Parts', ['cta-parts']],
    ['In Repair', ['cta-complete', 'cta-cannot-repair']],
    ['Pending Inspection', ['cta-confirm-inspection']],
  ] as [string, string[]][])('%s ⇒ CTA fallback = baseline (nút MỚI không lọt vào)', async (status, expected) => {
    const wo = makeWO({ status, allowed_transitions: REPAIR_TRANSITIONS[status] })
    delete wo.available_actions
    currentWO.value = wo
    const w = await mountDetail()
    expect(ctasShown(w).sort()).toEqual([...expected].sort())
    // `cta-start-repair` CHỈ tồn tại ở chế độ server-driven ⇒ 0 nút biến mất/xuất hiện.
    expect(w.find('[data-testid="cta-start-repair"]').exists()).toBe(false)
    expect(w.find('[data-testid="cm-cta-bar"]').exists()).toBe(false)
  })

  it('available_actions = [] (mảng rỗng) ⇒ vẫn rơi về fallback, KHÔNG màn trắng', async () => {
    currentWO.value = makeWO({
      status: 'In Repair',
      allowed_transitions: REPAIR_TRANSITIONS['In Repair'],
      available_actions: [],
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="cm-cta-bar"]').exists()).toBe(false)
    expect(ctasShown(w).sort()).toEqual(['cta-cannot-repair', 'cta-complete'])
  })
})

describe('FE-CMCTA-5 — không có khoá cancel/cannot_repair: nút huỷ phiếu KHÔNG tồn tại', () => {
  it('tập khoá server = đúng 6 (không cancel) ⇒ 0 nút huỷ phiếu; cta-cannot-repair bám close_work_order', async () => {
    currentWO.value = makeWO({ status: 'In Repair' })
    const w = await mountDetail()
    const keys = (currentWO.value.available_actions as { key: string }[]).map((a) => a.key)
    expect(keys).toEqual([...ACTION_KEYS])
    expect(keys).not.toContain('cancel')
    expect(keys).not.toContain('cannot_repair')
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(false)
    expect(w.find('[data-action-key="cancel"]').exists()).toBe(false)
    // 2 nút / 1 khoá: bật-tắt theo CÙNG action object.
    expect(w.find('[data-testid="cta-cannot-repair"]').attributes('data-action-key')).toBe('close_work_order')
    expect(w.find('[data-testid="cta-complete"]').attributes('data-action-key')).toBe('close_work_order')
    expect(ctasEnabled(w).sort()).toEqual(['cta-cannot-repair', 'cta-complete', 'cta-parts'])
  })

  // Bug lộ ra khi RENDER THẬT (LL-FE-46): 2 nút dùng chung 1 khoá ⇒ nếu lấy y nguyên
  // `label` server thì hiện HAI nút CHỮ GIỐNG HỆT ("Đóng phiếu sửa chữa") — người
  // dùng không phân biệt được "hoàn thành" với "không thể sửa".
  it('2 nút dùng chung close_work_order PHẢI có nhãn KHÁC NHAU (chống trùng chữ)', async () => {
    currentWO.value = makeWO({ status: 'In Repair' })
    const w = await mountDetail()
    const complete = w.find('[data-testid="cta-complete"]').text()
    const cannot = w.find('[data-testid="cta-cannot-repair"]').text()
    expect(complete).not.toBe(cannot)
    expect(complete).toBe('Hoàn thành sửa chữa')
    expect(cannot).toBe('Không thể sửa chữa')
    // Bật/tắt vẫn theo CÙNG action object (nhãn là biến thể HIỂN THỊ, không phải gate).
    expect((w.find('[data-testid="cta-complete"]').element as HTMLButtonElement).disabled)
      .toBe((w.find('[data-testid="cta-cannot-repair"]').element as HTMLButtonElement).disabled)
  })
})

describe('FE-CMCTA-6 — terminal ⇒ 0 nút CTA, nhãn tĩnh giữ nguyên', () => {
  it.each([
    ['Completed', 'Đã hoàn thành'],
    ['Cannot Repair', 'Không thể sửa chữa'],
    ['Cancelled', 'Đã huỷ'],
  ])('%s ⇒ 0 CTA render + nhãn "%s"', async (status, label) => {
    currentWO.value = makeWO({ status })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
    expect(w.find('[data-testid="cm-cta-bar"]').exists()).toBe(false)
    expect(w.text()).toContain(label)
  })
})

describe('FE-CMCTA-7 — reason SoD hiện dạng CHỮ (không chỉ tooltip)', () => {
  it('confirm_inspection bị khoá vì phân tách trách nhiệm ⇒ chuỗi reason có trong DOM text', async () => {
    currentWO.value = makeWO({
      status: 'Pending Inspection',
      available_actions: actionsFor('Pending Inspection', {
        confirm_inspection: { enabled: false, reason: REASON_SOD },
      }),
    })
    const w = await mountDetail()
    const btn = w.find('[data-testid="cta-confirm-inspection"]')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
    expect(btn.attributes('title')).toBe(REASON_SOD)
    // a11y: nút disabled KHÔNG nhận focus ⇒ lý do phải có dạng chữ đọc được.
    const reasons = w.find('[data-testid="cm-cta-reasons"]')
    expect(reasons.exists()).toBe(true)
    expect(reasons.text()).toContain(REASON_SOD)
    expect(btn.attributes('aria-describedby')).toBe('cm-cta-reason-confirm_inspection')
    expect(w.find('#cm-cta-reason-confirm_inspection').exists()).toBe(true)
    // Click vẫn no-op.
    await btn.trigger('click')
    await flushPromises()
    expect(doConfirmInspection).not.toHaveBeenCalled()
  })
})
