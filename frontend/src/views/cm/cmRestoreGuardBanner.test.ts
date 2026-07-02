// TDD — BR-09-09 / INV-09-RESTORE-1 (FE side, Core Doc §06):
// Sau khi đóng WO (complete_repair), `CMWorkOrderDetailView` phải bind badge trạng
// thái thiết bị theo `asset_info.lifecycle_status` THỰC từ response — KHÔNG hardcode
// 'Active'. Khi asset KHÔNG về Active (giữ hold governance khác: Out of Service /
// Decommissioned) → hiện note phụ "giữ trạng thái … do hạng mục khác — cần xử lý
// riêng", và TUYỆT ĐỐI không hiện nhầm "Thiết bị đã hoạt động trở lại".
//
// INV-FE-RESTORE-1: badge thiết bị == lifecycleStatusLabel(asset_info.lifecycle_status thật);
//   hold-note hiện ⟺ (status==Completed ∧ lifecycle_status ∉ {Active}).
// RED-prove: hardcode badge='Active' (bỏ bind asset_info) ⇒ TC-02/03 FAIL (đếm sai +
//   hold-note ẩn); restore ⇒ GREEN.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

// Shared full-shape router mock (ROOT-CAUSE test-isolation fix — xem
// src/test/vueRouterMock.ts). Đồng nhất mọi file CM → race vô hại, hết pollution.
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const showSpy = vi.fn()
const fromErrorSpy = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: showSpy, fromError: fromErrorSpy }),
}))

// CMWorkOrderDetailView nay gate CTA server-driven qua useCapabilities (GATE-8 /
// LL-FE-51). Test này chỉ kiểm badge/hold-note lifecycle (không phải CTA) → mock để
// KHÔNG chạm auth store thật (tránh cần active pinia + cách ly khỏi RBAC).
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => false }),
}))

// Store mock có currentWO mutable để mỗi test set 1 ngữ cảnh lifecycle.
import type { AssetRepair } from '@/api/imm09'
const storeState: {
  currentWO: AssetRepair | null
  loading: boolean
  error: string | null
  lastApiError: null
} = { currentWO: null, loading: false, error: null, lastApiError: null }

vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get currentWO() { return storeState.currentWO },
    get loading() { return storeState.loading },
    get error() { return storeState.error },
    get lastApiError() { return storeState.lastApiError },
    fetchWorkOrder: vi.fn().mockResolvedValue(undefined),
    doConfirmInspection: vi.fn().mockResolvedValue(true),
    doAssignTechnician: vi.fn().mockResolvedValue(true),
    doCloseWorkOrder: vi.fn().mockResolvedValue(true),
  }),
}))

import CMWorkOrderDetailView from './CMWorkOrderDetailView.vue'

function makeWO(over: Partial<AssetRepair> & { lifecycle_status?: string }): AssetRepair {
  const { lifecycle_status, ...rest } = over
  return {
    name: 'WO-RP-2026-00001',
    asset_ref: 'AC-ASSET-2026-00001',
    asset_name: 'Máy thở Dräger',
    asset_category: 'CAT-0001',
    risk_class: 'Class II',
    serial_no: 'SN-1',
    repair_type: 'Corrective',
    priority: 'Normal',
    status: 'Completed',
    open_datetime: '2026-06-01 08:00:00',
    assigned_datetime: '2026-06-01 09:00:00',
    completion_datetime: '2026-06-01 12:00:00',
    assigned_to: 'ktv@hospital.vn',
    assigned_by: null,
    mttr_hours: 4,
    sla_target_hours: 24,
    sla_breached: false,
    is_repeat_failure: false,
    incident_report: null,
    source_pm_wo: null,
    diagnosis_notes: '',
    root_cause_category: '',
    repair_summary: '',
    firmware_updated: false,
    firmware_change_request: null,
    dept_head_name: '',
    total_parts_cost: 0,
    spare_parts_used: [],
    repair_checklist: [],
    asset_info: { lifecycle_status },
    ...rest,
  } as AssetRepair
}

async function mountWith(wo: AssetRepair) {
  storeState.currentWO = wo
  const wrapper = mount(CMWorkOrderDetailView, {
    props: { id: wo.name },
    global: { stubs: { RouterLink: true, Transition: false } },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  // Active Pinia bắt buộc: CMWorkOrderDetailView nay gọi useCapabilities()→useAuthStore()
  // ở setup (GATE-8/LL-FE-51 CTA server-driven). Dù file đã mock useCapabilities, trong
  // full-suite run mock có thể bị registry-race giữa các file CM (xem vueRouterMock.ts) →
  // impl thật lọt vào → useAuthStore cần active Pinia. setActivePinia = fallback an toàn:
  // store rỗng ⇒ can()===false (khớp ý định mock), test không phụ thuộc thứ tự file.
  setActivePinia(createPinia())
  resetRouteMock(); showSpy.mockClear(); fromErrorSpy.mockClear()
  storeState.currentWO = null; storeState.loading = false; storeState.error = null
})

describe('CMWorkOrderDetailView — BR-09-09 restore-guard banner (INV-FE-RESTORE-1)', () => {
  it('TC-FE-RESTORE-01: WO Completed + asset Active → badge "Đang hoạt động", KHÔNG hold-note', async () => {
    const wrapper = await mountWith(makeWO({ lifecycle_status: 'Active' }))
    const badge = wrapper.find('[data-testid="asset-lifecycle-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('Đang hoạt động')
    // asset về Active → KHÔNG có note hold
    expect(wrapper.find('[data-testid="asset-hold-note"]').exists()).toBe(false)
  })

  it('TC-FE-RESTORE-02 (BUG CHÍNH): WO Completed + asset Out of Service → badge "Ngừng hoạt động" + hold-note, KHÔNG ép Active', async () => {
    const wrapper = await mountWith(makeWO({ lifecycle_status: 'Out of Service' }))
    const badge = wrapper.find('[data-testid="asset-lifecycle-badge"]')
    expect(badge.exists()).toBe(true)
    // RED-prove: nếu badge hardcode 'Active' → text này SAI
    expect(badge.text()).toContain('Ngừng hoạt động')
    expect(badge.text()).not.toContain('Đang hoạt động')
    // hold-note phải hiện (đóng WO ≠ thiết bị trở lại)
    const note = wrapper.find('[data-testid="asset-hold-note"]')
    expect(note.exists()).toBe(true)
    expect(note.text()).toContain('cần xử lý riêng')
    expect(note.text()).toContain('Ngừng hoạt động')
  })

  it('TC-FE-RESTORE-03: WO Completed + asset Decommissioned → badge "Đã thanh lý" + hold-note', async () => {
    const wrapper = await mountWith(makeWO({ lifecycle_status: 'Decommissioned' }))
    const badge = wrapper.find('[data-testid="asset-lifecycle-badge"]')
    expect(badge.text()).toContain('Đã thanh lý')
    expect(wrapper.find('[data-testid="asset-hold-note"]').exists()).toBe(true)
  })

  it('TC-FE-RESTORE-04: KHÔNG leak raw status EN + KHÔNG claim sai "đã hoạt động trở lại"', async () => {
    const wrapper = await mountWith(makeWO({ lifecycle_status: 'Out of Service' }))
    const html = wrapper.html()
    // nhãn hiển thị là VI — raw EN chỉ được phép trong title/attr, không phải text node hiển thị
    expect(wrapper.find('[data-testid="asset-lifecycle-badge"]').text()).not.toContain('Out of Service')
    // không tồn tại câu khẳng định thiết bị đã trở lại hoạt động (false claim)
    expect(html).not.toContain('đã hoạt động trở lại')
  })

  it('TC-FE-RESTORE-05: WO chưa đóng (In Repair) → badge theo trạng thái thật, KHÔNG hold-note (note chỉ cho Completed)', async () => {
    const wrapper = await mountWith(makeWO({ status: 'In Repair', lifecycle_status: 'Under Repair' }))
    const badge = wrapper.find('[data-testid="asset-lifecycle-badge"]')
    expect(badge.text()).toContain('Đang sửa chữa')
    // chưa Completed → không show hold-note
    expect(wrapper.find('[data-testid="asset-hold-note"]').exists()).toBe(false)
  })
})
