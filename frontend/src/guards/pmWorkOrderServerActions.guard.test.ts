// TC-FE-10 / TC-FE-11 (AC-CR-77) — CTA SERVER-DRIVEN cho màn chi tiết phiếu bảo trì
// định kỳ: PMWorkOrderDetailView render 4 nút TỪ `available_actions` do BE phát
// (`get_pm_work_order` → services.imm08._build_pm_available_actions).
//
// Vì sao test này tồn tại:
//   • "nút chết" — trước đây FE tự tính `can('pm.*') && allowedTransitions.includes()`
//     ⇒ persona thiếu capability vẫn thấy nút BẤM ĐƯỢC rồi ăn 403 câm. Nay `enabled`
//     do SERVER quyết, disabled + `reason` VI của SERVER hiện ra.
//   • "CTA ma" — 'Cancelled' CÓ trong _PM_VALID_TRANSITIONS nhưng KHÔNG có endpoint
//     ⇒ BE không phát ⇒ FE không thể vẽ (test khoá tập key render được).
//   • back-compat — payload CŨ (thiếu `available_actions`, worker BE chưa reload)
//     PHẢI giữ nguyên hành vi gate cũ: không màn trắng, không mất CTA.
//
// Bất biến kiểm ở đây (mirror D9 phía BE): `enabled === false ⟹ reason !== ""`, và
// tooltip hiển thị ĐÚNG chuỗi server (KHÔNG phải hằng FE).
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { REPO_ROOT, SRC } from '@/test/paths'

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}))

// Capability FE điều khiển được: server-driven mode PHẢI không phụ thuộc giá trị này
// cho 4 CTA (đó chính là điểm của CR-77) — vài test dưới cố tình đặt can()=false.
let canImpl: (c: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const checklistComplete = ref(true)
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)
const doAssignTechnician = vi.fn().mockResolvedValue(true)
vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    get currentWO() { return currentWO.value },
    loading: false,
    error: null,
    lastApiError: null,
    get ratedCount() { return (currentWO.value?.checklist_results as unknown[] | undefined)?.length ?? 0 },
    get checklistComplete() { return checklistComplete.value },
    get hasMajorFailure() { return false },
    get hasMinorFailure() { return false },
    fetchWorkOrder,
    updateChecklistResult: vi.fn(),
    doSubmitResult: vi.fn().mockResolvedValue({ success: true }),
    doReportMajorFailure: vi.fn().mockResolvedValue('WO-RP-1'),
    doReschedule: vi.fn().mockResolvedValue(true),
    doAssignTechnician,
  }),
}))

import PMWorkOrderDetailView from '@/views/pm/PMWorkOrderDetailView.vue'

// Chuỗi "của SERVER" cố ý KHÁC hằng FE (`CTA_LABEL_FALLBACK`) để chứng minh nhãn +
// tooltip render ra là chuỗi PAYLOAD, không phải chuỗi FE bịa.
const SRV_LABEL_START = 'Khởi công bảo trì (nhãn máy chủ)'
const SRV_REASON_SUBMIT = 'Phiếu chưa ở trạng thái đang thực hiện — chưa thể nghiệm thu'
const SRV_REASON_RESCHEDULE = 'Bạn không có quyền hoãn lịch bảo trì'
const SRV_REASON_MAJOR = 'Chỉ báo lỗi nghiêm trọng khi phiếu đang thực hiện'

/** available_actions mẫu: ĐÚNG 4 phần tử, thứ tự CỐ ĐỊNH như BE phát. */
function actions(over: Partial<Record<string, { enabled: boolean; reason: string; label?: string }>> = {}) {
  const base = [
    { key: 'start_work', label: SRV_LABEL_START, route: '', enabled: true, reason: '' },
    { key: 'submit_result', label: 'Hoàn thành bảo trì', route: '', enabled: false, reason: SRV_REASON_SUBMIT },
    { key: 'reschedule', label: 'Hoãn lịch bảo trì', route: '', enabled: false, reason: SRV_REASON_RESCHEDULE },
    { key: 'report_major_failure', label: 'Báo lỗi nghiêm trọng', route: '', enabled: false, reason: SRV_REASON_MAJOR },
  ]
  return base.map((a) => (over[a.key] ? { ...a, ...over[a.key] } : a))
}

function makeWO(over: WO = {}): WO {
  return {
    name: 'WO-PM-2026-00042',
    asset_ref: 'AC-ASSET-0042',
    asset_name: 'Máy siêu âm',
    risk_class: 'Medium',
    status: 'Open',
    pm_type: 'Preventive',
    wo_type: 'PM',
    due_date: '2026-06-30',
    is_late: false,
    assigned_to: 'ktv@hospital.vn',
    assigned_to_name: 'KTV A',
    supervisor: '',
    checklist_results: [],
    overall_result: null,
    completion_date: null,
    // A6 back-compat: `allowed_transitions` GIỮ NGUYÊN, payload mới là superset.
    allowed_transitions: ['In Progress', 'Overdue', 'Cancelled'],
    ...over,
  }
}

async function mountDetail() {
  const w = mount(PMWorkOrderDetailView, {
    props: { id: 'WO-PM-2026-00042' },
    global: {
      stubs: { RouterLink: true, Transition: false, DateInput: true },
      mocks: { $t: (k: string) => k },
    },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  fetchWorkOrder.mockClear()
  doAssignTechnician.mockClear()
  currentWO.value = null
  checklistComplete.value = true
  canImpl = () => true
})

describe('TC-FE-10 — render 4 CTA từ available_actions (nhãn/disabled/tooltip = SERVER)', () => {
  it('render đủ 4 nút, ĐÚNG thứ tự BE phát, trong cụm CTA server-driven', async () => {
    currentWO.value = makeWO({ available_actions: actions() })
    const w = await mountDetail()

    const bar = w.find('[data-testid="pm-cta-bar"]')
    expect(bar.exists()).toBe(true)
    const keys = bar.findAll('button[data-action-key]').map((b) => b.attributes('data-action-key'))
    expect(keys).toEqual(['start_work', 'submit_result', 'reschedule', 'report_major_failure'])
  })

  it('nút "bắt đầu" (enabled) bấm được + hiển thị ĐÚNG nhãn SERVER (không phải hằng FE)', async () => {
    currentWO.value = makeWO({ available_actions: actions() })
    const w = await mountDetail()

    const start = w.find('[data-testid="cta-start"]')
    expect(start.exists()).toBe(true)
    expect(start.attributes('disabled')).toBeUndefined()
    expect(start.text()).toBe(SRV_LABEL_START)
    // Không có lý do khoá ⇒ không gắn tooltip rỗng.
    expect(start.attributes('title')).toBeUndefined()
  })

  it('nút "hoàn thành" (server disabled) có thuộc tính disabled + tooltip == ĐÚNG chuỗi reason SERVER', async () => {
    currentWO.value = makeWO({ available_actions: actions() })
    const w = await mountDetail()

    const complete = w.find('[data-testid="cta-complete"]')
    expect(complete.exists()).toBe(true)
    expect(complete.attributes('disabled')).toBeDefined()
    expect(complete.attributes('title')).toBe(SRV_REASON_SUBMIT)
    expect(complete.attributes('aria-disabled')).toBe('true')
  })

  it('reason SERVER cũng hiện dạng CHỮ (a11y: nút disabled không focus được nên tooltip một mình không đủ)', async () => {
    currentWO.value = makeWO({ available_actions: actions() })
    const w = await mountDetail()

    const bar = w.find('[data-testid="pm-cta-bar"]')
    expect(bar.text()).toContain(SRV_REASON_SUBMIT)
    expect(bar.text()).toContain(SRV_REASON_RESCHEDULE)
    expect(bar.text()).toContain(SRV_REASON_MAJOR)
    // aria-describedby trỏ tới ĐÚNG id của dòng lý do tương ứng.
    const complete = w.find('[data-testid="cta-complete"]')
    const describedBy = complete.attributes('aria-describedby')
    expect(describedBy).toBe('pm-cta-reason-submit_result')
    expect(w.find(`#${describedBy}`).text()).toContain(SRV_REASON_SUBMIT)
  })

  it('click nút server-disabled = no-op (không mở modal hoàn thành) — chống dead-control', async () => {
    currentWO.value = makeWO({ available_actions: actions() })
    const w = await mountDetail()

    await w.find('[data-testid="cta-complete"]').trigger('click')
    await flushPromises()
    expect(w.text()).not.toContain('Xác nhận hoàn thành bảo trì')
  })

  it('click nút server-enabled gọi ĐÚNG hành động với ĐÚNG tham số (GATE-6c param == UI-selection)', async () => {
    currentWO.value = makeWO({ available_actions: actions() })
    const w = await mountDetail()

    await w.find('[data-testid="cta-start"]').trigger('click')
    await flushPromises()
    expect(doAssignTechnician).toHaveBeenCalledWith('WO-PM-2026-00042', 'ktv@hospital.vn')
  })

  it('SERVER là nguồn quyền: can()=false toàn bộ vẫn KHÔNG tắt nút mà server nói enabled', async () => {
    canImpl = () => false
    currentWO.value = makeWO({ available_actions: actions() })
    const w = await mountDetail()

    const start = w.find('[data-testid="cta-start"]')
    expect(start.exists()).toBe(true)
    expect(start.attributes('disabled')).toBeUndefined()
  })

  it('reschedule enabled ở phiếu Open (KHÔNG quá hạn) vẫn render — không bị chôn trong banner quá hạn', async () => {
    currentWO.value = makeWO({
      status: 'Open',
      is_overdue: false,
      available_actions: actions({ reschedule: { enabled: true, reason: '', label: 'Hoãn lịch bảo trì' } }),
    })
    const w = await mountDetail()

    const resched = w.find('[data-testid="cta-reschedule"]')
    expect(resched.exists()).toBe(true)
    expect(resched.attributes('disabled')).toBeUndefined()
    await resched.trigger('click')
    await flushPromises()
    expect(w.text()).toContain('Hoãn lịch bảo trì')
  })

  it('CTA ma: chỉ render đúng tập key server phát — không có nút huỷ dù "Cancelled" nằm trong allowed_transitions', async () => {
    currentWO.value = makeWO({ available_actions: actions() })
    const w = await mountDetail()

    const keys = w.findAll('button[data-action-key]').map((b) => b.attributes('data-action-key'))
    expect(keys).not.toContain('cancel')
    expect(new Set(keys)).toEqual(
      new Set(['start_work', 'submit_result', 'reschedule', 'report_major_failure']),
    )
    expect(w.text()).not.toContain('Cancelled')
  })

  it('A5 parity: server disable submit_result vì bảng kiểm rỗng ⇒ tooltip là lý do SERVER; thêm mục + server enable ⇒ bấm được', async () => {
    const emptyChecklistReason = 'Phiếu chưa có mục bảng kiểm — không thể nghiệm thu'
    currentWO.value = makeWO({
      status: 'In Progress',
      checklist_results: [],
      available_actions: actions({ submit_result: { enabled: false, reason: emptyChecklistReason } }),
    })
    let w = await mountDetail()
    let complete = w.find('[data-testid="cta-complete"]')
    expect(complete.attributes('disabled')).toBeDefined()
    expect(complete.attributes('title')).toBe(emptyChecklistReason)

    // Có mục bảng kiểm đã chấm + đủ điều kiện form ⇒ server enable ⇒ bấm được.
    currentWO.value = makeWO({
      status: 'In Progress',
      checklist_results: [{ idx: 1, checklist_item_idx: 1, description: 'Kiểm tra nguồn', measurement_type: 'Pass/Fail', unit: '', result: 'Pass', measured_value: null, notes: '', photo: null }],
      available_actions: actions({ submit_result: { enabled: true, reason: '' } }),
    })
    w = await mountDetail()
    // Điều kiện form cục bộ (thời lượng > 0, đã gắn tem) vẫn do client giữ — nhập vào.
    await w.find('#duration-min').setValue(30)
    await w.find('#sticker').setValue(true)
    await flushPromises()
    complete = w.find('[data-testid="cta-complete"]')
    expect(complete.attributes('disabled')).toBeUndefined()
    await complete.trigger('click')
    await flushPromises()
    expect(w.text()).toContain('Xác nhận hoàn thành bảo trì')
  })

  it('bất biến D9 phía render: mọi nút disabled đều có lý do hiển thị, mọi nút enabled đều không', async () => {
    currentWO.value = makeWO({ available_actions: actions() })
    const w = await mountDetail()

    for (const btn of w.findAll('button[data-action-key]')) {
      const disabled = btn.attributes('disabled') !== undefined
      const title = btn.attributes('title') ?? ''
      expect(disabled ? title !== '' : title === '').toBe(true)
    }
  })
})

describe('TC-FE-11 — fallback khi payload CŨ (thiếu available_actions)', () => {
  it('không có available_actions ⇒ không render cụm server-driven, CTA cũ vẫn hiện đúng', async () => {
    currentWO.value = makeWO({ status: 'Open' })
    const w = await mountDetail()

    expect(w.find('[data-testid="pm-cta-bar"]').exists()).toBe(false)
    // Open + assigned_to + cap pm.write → nút bắt đầu (đường cũ) vẫn còn.
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(true)
  })

  it('fallback vẫn gate theo capability như cũ (thiếu pm.write ⇒ ẩn nút bắt đầu)', async () => {
    canImpl = (c) => c !== 'pm.write'
    currentWO.value = makeWO({ status: 'Open' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(false)
  })

  it('fallback In Progress: nút hoàn thành + báo lỗi nghiêm trọng vẫn render như hành vi cũ', async () => {
    currentWO.value = makeWO({
      status: 'In Progress',
      allowed_transitions: ['Completed', 'Halted–Major Failure', 'Pending–Device Busy', 'Cancelled'],
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-complete"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-major"]').exists()).toBe(true)
  })

  it('available_actions = [] (degenerate) ⇒ coi như thiếu khoá → fallback, KHÔNG mất hết CTA', async () => {
    currentWO.value = makeWO({ status: 'Open', available_actions: [] })
    const w = await mountDetail()
    expect(w.find('[data-testid="pm-cta-bar"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(true)
  })

  it('key LẠ (BE thêm action mà giao diện chưa biết) ⇒ nút KHOÁ + lý do VI, click no-op — không đẻ nút chết kiểu mới', async () => {
    currentWO.value = makeWO({
      available_actions: [
        { key: 'cancel_work_order', label: 'Huỷ phiếu', route: '', enabled: true, reason: '' },
      ],
    })
    const w = await mountDetail()

    const btn = w.find('button[data-action-key="cancel_work_order"]')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeDefined()
    expect(btn.attributes('title')).toContain('chưa được hỗ trợ')
    await btn.trigger('click')
    await flushPromises()
    // Không mở modal nào, không gọi action nào.
    expect(doAssignTechnician).not.toHaveBeenCalled()
    expect(w.text()).not.toContain('Xác nhận hoàn thành bảo trì')
  })

  it('server-driven KHÔNG nhân đôi nút: cụm CTA cũ tắt hẳn khi có available_actions', async () => {
    currentWO.value = makeWO({
      status: 'In Progress',
      allowed_transitions: ['Completed', 'Halted–Major Failure', 'Pending–Device Busy', 'Cancelled'],
      available_actions: actions(),
    })
    const w = await mountDetail()
    // Mỗi testid chỉ xuất hiện ĐÚNG 1 lần (nếu đường cũ còn sống → 2 nút "Hoàn thành").
    expect(w.findAll('[data-testid="cta-complete"]').length).toBe(1)
    expect(w.findAll('[data-testid="cta-major"]').length).toBe(1)
    expect(w.findAll('[data-testid="cta-start"]').length).toBe(1)
  })
})

// ─── Guard chống DRIFT khoá BE↔FE ───────────────────────────────────────────────
// Class-of-bug: BE đổi/thêm `key` trong `_PM_ACTION_SPECS` mà FE không cập nhật ⇒ nút
// render nhưng KHÔNG có handler/testid/lớp CSS ⇒ "nút chết" kiểu mới (đúng thứ CR-77
// muốn diệt). Guard đọc THẲNG nguồn BE + nguồn view, so tập khoá — không mock, không
// chép tay hằng ở chỗ thứ ba.
const BE_SRC_PATH = resolve(REPO_ROOT, 'assetcore/services/imm08.py')
const VIEW_SRC_PATH = resolve(SRC, 'views/pm/PMWorkOrderDetailView.vue')

/** Khoá action BE, theo ĐÚNG thứ tự khai báo trong `_PM_ACTION_SPECS`. */
function beActionKeys(src: string): string[] {
  const start = src.indexOf('_PM_ACTION_SPECS: tuple[dict, ...] = (')
  const end = src.indexOf('def _pm_checklist_has_items', start)
  const block = src.slice(start, end)
  return [...block.matchAll(/"key":\s*"([a-z_]+)"/g)].map((m) => m[1])
}
/** Khoá có HANDLER ở view (nguồn dispatch click). */
function feHandlerKeys(src: string): string[] {
  const start = src.indexOf('const CTA_HANDLERS')
  const end = src.indexOf('const UNSUPPORTED_ACTION_REASON', start)
  return [...src.slice(start, end).matchAll(/^ {2}([a-z_]+):/gm)].map((m) => m[1])
}

describe.skipIf(!existsSync(BE_SRC_PATH))('Parity khoá CTA BE ↔ FE (chống drift âm thầm)', () => {
  const beKeys = beActionKeys(readFileSync(BE_SRC_PATH, 'utf8'))
  const viewSrc = readFileSync(VIEW_SRC_PATH, 'utf8')

  it('BE khai ĐÚNG 4 khoá, thứ tự cố định (hợp đồng A1)', () => {
    expect(beKeys).toEqual(['start_work', 'submit_result', 'reschedule', 'report_major_failure'])
  })

  it('MỌI khoá BE phát đều có handler ở view (không nút nào bấm rơi vào hư không)', () => {
    expect(feHandlerKeys(viewSrc).sort()).toEqual([...beKeys].sort())
  })

  it('MỌI khoá BE phát đều có testid + lớp nút ở view (không nút vô danh/không định dạng)', () => {
    for (const k of beKeys) {
      expect(viewSrc).toMatch(new RegExp(`\\n\\s{2}${k}: 'cta-`))
      expect(viewSrc).toMatch(new RegExp(`\\n\\s{2}${k}: 'btn-`))
    }
  })
})
