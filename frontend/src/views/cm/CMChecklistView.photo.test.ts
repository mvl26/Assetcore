// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-09 CR-15/G6 — Ảnh bằng chứng checklist nghiệm thu / NĐ98 Class C/D).
//
// Acceptance (đối xứng IncidentDetailView.photo.test.ts):
//   • repair_checklist[].photo có → render <img> thumbnail; null → không crash, không img.
//   • bấm upload → gọi attachRepairChecklistPhoto với ĐÚNG (woName, item.idx, File user chọn)
//     (LL-FE-47 anti-dead-control: param phát đi == lựa chọn UI, KHÔNG hardcode call-site).
//   • 200 → refetch WO (store.fetchWorkOrder gọi lại).
//   • response VALIDATION (fields.file) → lỗi VN inline dưới control (role=alert), KHÔNG toast trần.
//   • đã có ảnh (max=1) → nút "Đính ảnh" disabled.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

const notifyShow = vi.fn()
const notifyFromError = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: notifyShow, fromError: notifyFromError, fromOk: vi.fn(), confirm: vi.fn() }),
}))

const attachSpy = vi.fn()
vi.mock('@/api/imm09', () => ({
  attachRepairChecklistPhoto: (wo: string, idx: number, file: File) => attachSpy(wo, idx, file),
}))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get currentWO() { return currentWO.value },
    error: null,
    lastApiError: null,
    fetchWorkOrder,
    doCloseWorkOrder: vi.fn().mockResolvedValue(true),
  }),
}))

import CMChecklistView from './CMChecklistView.vue'

interface Row { idx: number; test_description: string; test_category: string; expected_value: string; measured_value: string; result: string | null; notes: string; photo?: string | null }
function row(idx: number, over: Partial<Row> = {}): Row {
  return {
    idx, test_description: `Kiểm tra mục ${idx}`, test_category: 'Safety',
    expected_value: '', measured_value: '', result: 'Pass', notes: '', photo: null, ...over,
  }
}
function makeWO(checklist: Row[]): WO {
  return { name: 'WO-RP-2026-00099', root_cause_category: '', repair_checklist: checklist }
}

async function mountView() {
  const w = mount(CMChecklistView, { props: { id: 'WO-RP-2026-00099' }, global: { stubs: { Transition: false } } })
  await flushPromises()
  return w
}

const uploadBtn = (idx: number) => `button[aria-label="Đính ảnh bằng chứng mục #${idx} (JPG hoặc PNG)"]`

beforeEach(() => {
  currentWO.value = null
  attachSpy.mockReset()
  fetchWorkOrder.mockClear()
  notifyShow.mockReset()
  notifyFromError.mockReset()
})

describe('CMChecklistView — render ảnh bằng chứng mục', () => {
  it('mục có photo → render <img> thumbnail', async () => {
    currentWO.value = makeWO([row(1, { photo: '/private/files/bc-1.jpg' }), row(2)])
    const w = await mountView()
    const imgs = w.findAll('img')
    expect(imgs).toHaveLength(1)
    expect(imgs[0].attributes('src')).toBe('/private/files/bc-1.jpg')
  })

  it('mục photo null → không crash, không img, nút Đính ảnh còn bật', async () => {
    currentWO.value = makeWO([row(1, { photo: null })])
    const w = await mountView()
    expect(w.findAll('img')).toHaveLength(0)
    expect(w.find(uploadBtn(1)).attributes('disabled')).toBeUndefined()
  })

  it('mục đã có ảnh (max=1) → nút Đính ảnh disabled', async () => {
    currentWO.value = makeWO([row(1, { photo: '/private/files/bc-1.jpg' })])
    const w = await mountView()
    const btn = w.find(uploadBtn(1))
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeDefined()
    expect(btn.text()).toContain('Đã đính ảnh bằng chứng')
  })
})

describe('CMChecklistView — upload (LL-FE-47 anti-dead-control + refetch)', () => {
  it('bấm upload → attachRepairChecklistPhoto nhận ĐÚNG (woName, item.idx, File)', async () => {
    currentWO.value = makeWO([row(1), row(2)])
    attachSpy.mockResolvedValue({ file_url: '/private/files/x.jpg', file_name: 'x.jpg', checklist_item_idx: 2 })
    const w = await mountView()

    const file = new File(['xx'], 'bang-chung.jpg', { type: 'image/jpeg' })
    // Chọn input của MỤC #2 (thứ 2) — chứng minh idx phát đi == mục UI, không hardcode.
    const inputs = w.findAll('input[type="file"]')
    expect(inputs).toHaveLength(2)
    Object.defineProperty(inputs[1].element, 'files', { value: [file], configurable: true })
    await inputs[1].trigger('change')
    await flushPromises()

    expect(attachSpy).toHaveBeenCalledTimes(1)
    expect(attachSpy.mock.calls[0][0]).toBe('WO-RP-2026-00099')
    expect(attachSpy.mock.calls[0][1]).toBe(2)
    expect(attachSpy.mock.calls[0][2]).toBe(file)
  })

  it('200 → refetch WO (store.fetchWorkOrder gọi lại) + thumbnail xuất hiện', async () => {
    currentWO.value = makeWO([row(1)])
    attachSpy.mockResolvedValue({ file_url: '/private/files/x.jpg', file_name: 'x.jpg', checklist_item_idx: 1 })
    const w = await mountView()
    fetchWorkOrder.mockClear()

    const file = new File(['xx'], 'bang-chung.jpg', { type: 'image/jpeg' })
    const input = w.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    expect(fetchWorkOrder).toHaveBeenCalledWith('WO-RP-2026-00099')
    expect(notifyShow).toHaveBeenCalledTimes(1)
    // photo set từ response → thumbnail render, nút chuyển disabled.
    expect(w.findAll('img')).toHaveLength(1)
    expect(w.find(uploadBtn(1)).attributes('disabled')).toBeDefined()
  })

  it('response VALIDATION (fields.file) → lỗi VN inline (role=alert), KHÔNG toast trần', async () => {
    currentWO.value = makeWO([row(1)])
    attachSpy.mockRejectedValue(
      new ApiError('Sai định dạng', { code: ErrorCode.VALIDATION, fields: { file: 'Chỉ chấp nhận ảnh JPG hoặc PNG' } }),
    )
    const w = await mountView()

    const file = new File(['xx'], 'tailieu.txt', { type: 'text/plain' })
    const input = w.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('Chỉ chấp nhận ảnh JPG hoặc PNG')
    // fields error → inline, KHÔNG đẩy fromError (tránh double-signal).
    expect(notifyFromError).not.toHaveBeenCalled()
  })
})

describe('CMChecklistView — i18n: nhãn "Không đạt" (không leak "Fail")', () => {
  it('hint có mục Fail dùng "Không đạt", không "mục Fail"', async () => {
    currentWO.value = makeWO([row(1, { result: 'Fail' }), row(2, { result: null })])
    const w = await mountView()
    // deptHeadName rỗng + có Fail → hint hiển thị
    expect(w.text()).not.toContain('mục Fail')
    expect(w.text()).toContain('Không đạt')
  })
})
