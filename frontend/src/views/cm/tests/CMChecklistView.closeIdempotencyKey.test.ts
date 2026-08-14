// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-09 CR-24 op#5/5 — dedup idempotency close_work_order / mobile write-outbox
// closure). GATE-6c / LL-FE-47 anti-dead-control: chứng minh KHOÁ client `client_request_id`
// PHÁT ĐI == khoá do handler sinh cho MỖI lần user bấm — KHÔNG hardcode ở call-site, KHÔNG
// hằng-số đông cứng. Đây là regression guard cho lát wiring đã có ở working tree
// (CMChecklistView.handleComplete + api/imm09.closeWorkOrder body `client_request_id`).
//
// Bối cảnh: BE `close_work_order` nhận `client_request_id` optional (resolve qua shared
// resolve_idempotency_key, body THẮNG header). Web FE gửi khoá mới mỗi lần bấm ⇒ an toàn
// double-submit desk + auto-retry (BE replay success-envelope thay vì 422-giả). Bỏ trống ⇒
// hành vi legacy. Test này khoá invariant "khoá phát đi == khoá sinh" để refactor tương lai
// KHÔNG âm thầm rớt param (dead-control) mà mọi test khác vẫn xanh.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

const notifyShow = vi.fn()
const notifyFromError = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: notifyShow, fromError: notifyFromError, fromOk: vi.fn(), confirm: vi.fn() }),
}))

// Mock api layer để tránh nạp axios; component chỉ import attachRepairChecklistPhoto (không dùng ở đây).
vi.mock('@/api/imm09', () => ({ attachRepairChecklistPhoto: vi.fn() }))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)
// Spy trung tâm: bắt payload thực sự chảy tới store.doCloseWorkOrder (view → store → api).
const doCloseWorkOrder = vi.fn().mockResolvedValue(true)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get currentWO() { return currentWO.value },
    error: null,
    lastApiError: null,
    fetchWorkOrder,
    doCloseWorkOrder,
  }),
}))

import CMChecklistView from '@/views/cm/CMChecklistView.vue'

// Khoá UUID xác định để assert GIÁ TRỊ CHÍNH XÁC phát đi == giá trị handler sinh (không hardcode).
let uuidCounter = 0
const randomUUID = vi.fn(() => `IDEMP-KEY-${String(++uuidCounter).padStart(3, '0')}`)

beforeEach(() => {
  currentWO.value = null
  uuidCounter = 0
  randomUUID.mockClear()
  doCloseWorkOrder.mockClear()
  fetchWorkOrder.mockClear()
  notifyShow.mockReset()
  notifyFromError.mockReset()
  vi.stubGlobal('crypto', { randomUUID })
})
afterEach(() => { vi.unstubAllGlobals() })

function makeWO(): WO {
  return {
    name: 'WO-RP-2026-00099',
    root_cause_category: 'Wear and tear',
    repair_checklist: [
      { idx: 1, test_description: 'Xác nhận thiết bị hoạt động bình thường', result: null, measured_value: '', notes: '' },
    ],
  }
}

async function mountAndComplete(w?: ReturnType<typeof mount>) {
  const view = w ?? mount(CMChecklistView, { props: { id: 'WO-RP-2026-00099' }, global: { stubs: { Transition: false } } })
  await flushPromises()
  // canComplete = tất cả mục đã chấm + không có Fail + có tên trưởng khoa.
  const passBtn = view.findAll('button').find(b => b.text().trim() === 'Đạt')
  expect(passBtn, 'nút "Đạt" phải tồn tại').toBeTruthy()
  await passBtn!.trigger('click')
  await view.find('input[placeholder="Nguyễn Văn A"]').setValue('Nguyễn Văn A')
  await flushPromises()
  const completeBtn = view.findAll('button').find(b => b.text().includes('Hoàn thành sửa chữa'))
  expect(completeBtn, 'nút "Hoàn thành sửa chữa" phải tồn tại').toBeTruthy()
  await completeBtn!.trigger('click')
  await flushPromises()
  return view
}

describe('CMChecklistView — close_work_order gắn client_request_id (GATE-6c / LL-FE-47)', () => {
  it('bấm "Hoàn thành" → doCloseWorkOrder nhận ĐÚNG khoá handler sinh (không hardcode/không rỗng)', async () => {
    currentWO.value = makeWO()
    await mountAndComplete()

    expect(doCloseWorkOrder).toHaveBeenCalledTimes(1)
    const payload = doCloseWorkOrder.mock.calls[0][0] as Record<string, unknown>
    // Khoá PHÁT ĐI == khoá handler SINH (randomUUID) — chống dead-control (hardcode call-site).
    expect(randomUUID).toHaveBeenCalledTimes(1)
    expect(payload.client_request_id).toBe('IDEMP-KEY-001')
    expect(String(payload.client_request_id)).not.toBe('')
    // WO name đúng — payload không lệch phiếu.
    expect(payload.name).toBe('WO-RP-2026-00099')
  })

  it('mỗi lần bấm sinh khoá MỚI (không hằng-số đông cứng) — 2 lần bấm ⇒ 2 khoá khác nhau', async () => {
    currentWO.value = makeWO()
    await mountAndComplete()
    // Lần bấm thứ 2 (user chủ động thử lại) — handler chạy lại, sinh khoá mới.
    currentWO.value = makeWO()
    await mountAndComplete()

    expect(doCloseWorkOrder).toHaveBeenCalledTimes(2)
    const k1 = (doCloseWorkOrder.mock.calls[0][0] as Record<string, unknown>).client_request_id
    const k2 = (doCloseWorkOrder.mock.calls[1][0] as Record<string, unknown>).client_request_id
    expect(k1).toBe('IDEMP-KEY-001')
    expect(k2).toBe('IDEMP-KEY-002')
    expect(k1).not.toBe(k2)
  })
})
