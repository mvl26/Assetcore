// Copyright (c) 2026, AssetCore Team
// FE-TDD AC-CR-84 — cổng ẢNH BẰNG CHỨNG NĐ98 tại chính màn NGHIỆM THU (nơi người dùng
// bấm «Hoàn thành sửa chữa» và là nơi server từ chối). Hợp đồng: docs/imm-09/
// 06_Frontend_Design.md §CMEvidencePhoto U1/U2 + §3 (neo lỗi + refetch).
//
// Acceptance:
//   • required=1, missing=[2,5] ⇒ dải "còn 2/6 mục chưa có ảnh" + đúng 2 chip ở dòng 2 và 5.
//   • required=0 ⇒ 0 dải, 0 chip (thiết bị Thấp/Trung bình/chưa phân loại — 0 nhiễu).
//   • vắng khoá (worker BE chưa reload) ⇒ 0 dải, KHÔNG khẳng định "đã có ảnh".
//   • close_work_order bị từ chối kèm `fields.repair_checklist` ⇒ thông điệp SERVER neo
//     DƯỚI bảng nghiệm thu (không chỉ toast) + refetch phiếu để tập mục-thiếu cập nhật.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

const notifyFromError = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: notifyFromError, fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/api/imm09', () => ({ attachRepairChecklistPhoto: vi.fn() }))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const lastApiError = ref<ApiError | null>(null)
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)
const doCloseWorkOrder = vi.fn().mockResolvedValue(true)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get currentWO() { return currentWO.value },
    get lastApiError() { return lastApiError.value },
    error: null,
    fetchWorkOrder,
    doCloseWorkOrder,
  }),
}))

import CMChecklistView from './CMChecklistView.vue'

interface Row {
  idx: number; test_description: string; test_category: string
  expected_value: string; measured_value: string
  result: string | null; notes: string; photo?: string | null
}
function row(idx: number, over: Partial<Row> = {}): Row {
  return {
    idx, test_description: `Kiểm tra mục ${idx}`, test_category: 'Safety',
    expected_value: '', measured_value: '', result: 'Pass', notes: '', photo: null, ...over,
  }
}
function makeWO(over: WO = {}): WO {
  return {
    name: 'WO-RP-2026-00099', root_cause_category: '',
    repair_checklist: [1, 2, 3, 4, 5, 6].map((i) => row(i)),
    ...over,
  }
}

async function mountView() {
  const w = mount(CMChecklistView, { props: { id: 'WO-RP-2026-00099' }, global: { stubs: { Transition: false } } })
  await flushPromises()
  return w
}

beforeEach(() => {
  currentWO.value = null
  lastApiError.value = null
  fetchWorkOrder.mockClear()
  doCloseWorkOrder.mockReset().mockResolvedValue(true)
  notifyFromError.mockReset()
})

describe('AC-CR-84 · dải ảnh bằng chứng NĐ98 trên màn nghiệm thu', () => {
  it('required=1, missing=[2,5] ⇒ dải "còn 2/6 mục chưa có ảnh" + đúng 2 chip', async () => {
    currentWO.value = makeWO({
      evidence_photo_required: 1,
      evidence_photo_missing_idxs: [2, 5],
      evidence_photo_total_required: 6,
    })
    const w = await mountView()
    const banner = w.find('[data-testid="cm-checklist-evidence-banner"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('còn 2/6 mục chưa có ảnh')
    expect(banner.text()).toContain('Đã có 4/6 mục có ảnh')
    expect(w.findAll('[data-testid="cm-checklist-evidence-chip"]')).toHaveLength(2)
  })

  it('required=0 ⇒ KHÔNG dải, KHÔNG chip', async () => {
    currentWO.value = makeWO({
      evidence_photo_required: 0,
      evidence_photo_missing_idxs: [],
      evidence_photo_total_required: 0,
    })
    const w = await mountView()
    expect(w.find('[data-testid="cm-checklist-evidence-banner"]').exists()).toBe(false)
    expect(w.findAll('[data-testid="cm-checklist-evidence-chip"]')).toHaveLength(0)
  })

  it('vắng cả 3 khoá (worker BE chưa reload) ⇒ KHÔNG dải, KHÔNG khẳng định đã có ảnh', async () => {
    currentWO.value = makeWO()
    const w = await mountView()
    expect(w.find('[data-testid="cm-checklist-evidence-banner"]').exists()).toBe(false)
    expect(w.text()).not.toContain('đã có ảnh')
  })

  it('server từ chối kèm fields.repair_checklist ⇒ neo thông điệp DƯỚI bảng nghiệm thu + refetch', async () => {
    currentWO.value = makeWO({
      evidence_photo_required: 1,
      evidence_photo_missing_idxs: [2, 5],
      evidence_photo_total_required: 6,
    })
    const w = await mountView()

    const serverMsg = 'Thiết bị thuộc nhóm nguy cơ cao — còn 2 mục nghiệm thu chưa có ảnh bằng chứng'
    doCloseWorkOrder.mockResolvedValue(false)
    lastApiError.value = new ApiError(serverMsg, ErrorCode.BUSINESS_RULE_VIOLATION, 200, {
      repair_checklist: serverMsg,
    })

    // Điền điều kiện nghiệp vụ cũ để nút bật (checklist đã Đạt hết từ fixture).
    const inputs = w.findAll('input[type="text"]')
    await inputs[0].setValue('Nguyễn Văn A')
    await flushPromises()

    fetchWorkOrder.mockClear()
    const completeBtn = w.findAll('button').find((b) => b.text().includes('Hoàn thành sửa chữa'))
    expect(completeBtn).toBeTruthy()
    await completeBtn!.trigger('click')
    await flushPromises()

    const anchored = w.find('[data-testid="cm-checklist-field-error"]')
    expect(anchored.exists()).toBe(true)
    expect(anchored.text()).toBe(serverMsg)
    expect(anchored.attributes('role')).toBe('alert')
    // (c) refetch để tập mục-thiếu-ảnh cập nhật (có thể vừa đính ở tab khác).
    expect(fetchWorkOrder).toHaveBeenCalledWith('WO-RP-2026-00099')
    expect(notifyFromError).toHaveBeenCalled()
  })
})
