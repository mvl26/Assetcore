// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-09 CR-50 — nghiệm thu sau sửa chữa với repair_checklist BE seed sẵn).
//
// Bối cảnh: BE seed danh mục nghiệm thu chuẩn (>=N dòng, mỗi dòng test_description +
// test_category, result TRỐNG) ngay tại create_work_order ⇒ gỡ deadlock confirm_inspection
// 422 IMM09_CHECKLIST_INCOMPLETE. FE chỉ RENDER các dòng THẬT + cho KTV chấm kết quả.
//
// Regression guard (bảo toàn bất biến vacuous-pass: mọi 'Đạt' ⟺ dòng THẬT):
//   • Dòng seed render kèm test_category; điền tất cả = Đạt + trưởng khoa → "Hoàn thành
//     sửa chữa" BẬT; bấm → doCloseWorkOrder nhận checklist_results = các dòng seed (idx +
//     test_category BẢO TOÀN, result Pass) — đối xứng AC2 luồng web.
//   • BR-09-04 nguyên vẹn ở FE: còn dòng để trống HOẶC Fail → nút DISABLED (không cho gửi).
//   • Checklist RỖNG (phiếu cũ chưa backfill) → FE KHÔNG fabricate 1 dòng "pass" generic
//     (band-aid cũ đã bỏ): 0 nút "Đạt", empty-state có lối thoát, nút "Hoàn thành" DISABLED
//     kể cả khi đã nhập trưởng khoa ⇒ FE KHÔNG còn là lỗ bypass BR-09-04.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

const notifyShow = vi.fn()
const notifyFromError = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: notifyShow, fromError: notifyFromError, fromOk: vi.fn(), confirm: vi.fn() }),
}))

vi.mock('@/api/imm09', () => ({ attachRepairChecklistPhoto: vi.fn() }))

type Row = { idx: number; test_description: string; test_category: string; expected_value?: string; measured_value: string; result: string | null; notes: string }
type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)
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

// Danh mục seed chuẩn: mỗi dòng test_category thuộc enum, result TRỐNG (chờ KTV chấm).
const SEED_CATEGORIES = ['Electrical', 'Mechanical', 'Software', 'Safety'] as const
function seededChecklist(): Row[] {
  return SEED_CATEGORIES.map((cat, i) => ({
    idx: i + 1,
    test_description: `Kiểm tra ${cat}`,
    test_category: cat,
    expected_value: '',
    measured_value: '',
    result: null,
    notes: '',
  }))
}
function makeWO(checklist: Row[]): WO {
  return { name: 'WO-RP-2026-00099', root_cause_category: 'Wear and tear', repair_checklist: checklist }
}

async function mountView() {
  const w = mount(CMChecklistView, { props: { id: 'WO-RP-2026-00099' }, global: { stubs: { Transition: false } } })
  await flushPromises()
  return w
}
const completeBtn = (w: ReturnType<typeof mount>) =>
  w.findAll('button').find(b => b.text().includes('Hoàn thành sửa chữa'))
const passButtons = (w: ReturnType<typeof mount>) =>
  w.findAll('button').filter(b => b.text().trim() === 'Đạt')

beforeEach(() => {
  currentWO.value = null
  doCloseWorkOrder.mockClear()
  fetchWorkOrder.mockClear()
  notifyShow.mockReset()
  notifyFromError.mockReset()
  vi.stubGlobal('crypto', { randomUUID: () => 'IDEMP-KEY-001' })
})
afterEach(() => { vi.unstubAllGlobals() })

describe('CMChecklistView — checklist BE seed sẵn (CR-50)', () => {
  it('render mỗi dòng seed kèm test_category (không rỗng)', async () => {
    currentWO.value = makeWO(seededChecklist())
    const w = await mountView()
    for (const cat of SEED_CATEGORIES) expect(w.text()).toContain(cat)
    // N dòng ⇒ N bộ nút Đạt/Không đạt/Không áp dụng.
    expect(passButtons(w)).toHaveLength(SEED_CATEGORIES.length)
  })

  it('điền tất cả = Đạt + trưởng khoa → Hoàn thành BẬT → doCloseWorkOrder nhận dòng seed (idx + test_category bảo toàn, result Pass)', async () => {
    currentWO.value = makeWO(seededChecklist())
    const w = await mountView()

    for (const btn of passButtons(w)) await btn.trigger('click')
    await w.find('input[placeholder="Nguyễn Văn A"]').setValue('Nguyễn Văn A')
    await flushPromises()

    const btn = completeBtn(w)!
    expect(btn.attributes('disabled')).toBeUndefined()   // BẬT
    await btn.trigger('click')
    await flushPromises()

    expect(doCloseWorkOrder).toHaveBeenCalledTimes(1)
    const payload = doCloseWorkOrder.mock.calls[0][0] as { name: string; checklist_results: Row[] }
    expect(payload.name).toBe('WO-RP-2026-00099')
    // AC4 parity: gửi đúng các dòng seed theo idx, test_category BẢO TOÀN, mọi dòng Pass.
    expect(payload.checklist_results).toHaveLength(SEED_CATEGORIES.length)
    expect(payload.checklist_results.map(r => r.idx)).toEqual([1, 2, 3, 4])
    expect(payload.checklist_results.map(r => r.test_category)).toEqual([...SEED_CATEGORIES])
    expect(payload.checklist_results.every(r => r.result === 'Pass')).toBe(true)
  })

  it('BR-09-04 ở FE: còn 1 dòng để trống → Hoàn thành DISABLED (không cho gửi)', async () => {
    currentWO.value = makeWO(seededChecklist())
    const w = await mountView()
    const btns = passButtons(w)
    // Chỉ chấm N-1 dòng (còn 1 dòng result=null).
    for (let i = 0; i < btns.length - 1; i++) await btns[i].trigger('click')
    await w.find('input[placeholder="Nguyễn Văn A"]').setValue('Nguyễn Văn A')
    await flushPromises()
    expect(completeBtn(w)!.attributes('disabled')).toBeDefined()
    expect(doCloseWorkOrder).not.toHaveBeenCalled()
  })

  it('BR-09-04 ở FE: có 1 dòng Không đạt → Hoàn thành DISABLED', async () => {
    currentWO.value = makeWO(seededChecklist())
    const w = await mountView()
    for (const btn of passButtons(w)) await btn.trigger('click')
    // Đổi 1 dòng sang Không đạt.
    const failBtn = w.findAll('button').find(b => b.text().trim() === 'Không đạt')!
    await failBtn.trigger('click')
    await w.find('input[placeholder="Nguyễn Văn A"]').setValue('Nguyễn Văn A')
    await flushPromises()
    expect(completeBtn(w)!.attributes('disabled')).toBeDefined()
    expect(doCloseWorkOrder).not.toHaveBeenCalled()
  })
})

describe('CMChecklistView — checklist RỖNG không còn fabricate pass giả (band-aid gỡ)', () => {
  it('0 dòng → không có nút "Đạt" nào (FE không tự chèn dòng), empty-state có lối thoát', async () => {
    currentWO.value = makeWO([])
    const w = await mountView()
    expect(passButtons(w)).toHaveLength(0)                 // KHÔNG fabricate dòng
    expect(w.text()).toContain('chưa có mục nghiệm thu nào')
    // Lối thoát actionable (LL-FE-44): nút quay lại phiếu.
    expect(w.findAll('button').some(b => b.text().includes('Quay lại'))).toBe(true)
  })

  it('0 dòng + đã nhập trưởng khoa → Hoàn thành vẫn DISABLED (FE không bypass BR-09-04)', async () => {
    currentWO.value = makeWO([])
    const w = await mountView()
    await w.find('input[placeholder="Nguyễn Văn A"]').setValue('Nguyễn Văn A')
    await flushPromises()
    expect(completeBtn(w)!.attributes('disabled')).toBeDefined()
    expect(doCloseWorkOrder).not.toHaveBeenCalled()
  })
})
