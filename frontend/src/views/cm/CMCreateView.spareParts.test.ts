// Copyright (c) 2026, AssetCore Team
// FE-TDD CR-73(a) — CMCreateView: gợi ý phụ tùng có KHOÁ NHẬN DẠNG.
//
// Bug gốc (E3, docs/imm-09/05_API_Specification.md §3.13-bis):
//   `searchSpareParts(q) as unknown as Array<{name, part_name, stock_qty}>` — 3 khoá
//   BỊA (không tồn tại trong response) ⇒ `addPart` đẩy `{spare_part: undefined}` và
//   de-dup so `undefined === undefined` ⇒ chặn MỌI dòng thứ 2 + yêu cầu phụ tùng
//   biến mất im lặng ở `request_spare_parts`.
//
// Acceptance phủ ở đây:
//   T11 — 2 gợi ý CÙNG item_name, KHÁC device_model_name ⇒ 2 <li> và DOM chứa
//         CẢ HAI tên model (assert chuỗi THẬT, không chỉ đếm dòng — LL-FE-48).
//   T12 — click 2 gợi ý khác nhau ⇒ preRequestParts 2 dòng, mỗi dòng `spare_part`
//         truthy (trước fix: 1 dòng `undefined`).
//   T13 — click CÙNG 1 gợi ý 2 lần ⇒ chỉ 1 dòng.
//   +   — gợi ý `spare_part: ''` (không resolve) ⇒ nút disabled + không thêm dòng.
//   +   — payload `request_spare_parts` mang ĐÚNG khoá đã chọn (LL-FE-47:
//         param phát đi == UI-selection, chống dead-control).
//   +   — tương thích cửa sổ BLOCKED-RELOAD: BE chưa nạp bản 13 khoá (thiếu hẳn
//         `spare_part`) ⇒ vẫn chọn được (lùi về `item_code`), KHÔNG chặn người dùng.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { SparePartSuggestion } from '@/api/imm09'

const pushSpy = vi.fn().mockResolvedValue(undefined)
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

const searchSparePartsMock = vi.fn()
const requestSparePartsMock = vi.fn().mockResolvedValue({ name: 'WO-CM-1', updated: 1, allocation: 'ALLOC-1' })
vi.mock('@/api/imm09', () => ({
  searchSpareParts: (q: string) => searchSparePartsMock(q),
  requestSpareParts: (name: string, parts: unknown) => requestSparePartsMock(name, parts),
}))
vi.mock('@/api/imm12', () => ({ getIncident: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn().mockResolvedValue({ file_url: '' }) }))
vi.mock('@/api/imm00', () => ({ getAssetActionMeta: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/helpers', () => ({
  frappeGet: vi.fn().mockResolvedValue(null),
  frappePost: vi.fn().mockResolvedValue(null),
}))
vi.mock('@/composables/useFormDraft', () => ({ useFormDraft: () => ({ clear: vi.fn() }) }))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ run: vi.fn().mockResolvedValue(null) }) }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))

import CMCreateView from './CMCreateView.vue'

function suggestion(over: Partial<SparePartSuggestion>): SparePartSuggestion {
  return {
    idx: 0,
    item_code: 'MPN-1',
    item_name: 'Van PEEP',
    manufacturer_part_no: 'MPN-1',
    qty: 1,
    uom: 'Cái',
    unit_cost: 0,
    total_cost: 0,
    stock_entry_ref: '',
    notes: '',
    device_model: 'MODEL-A',
    device_model_name: 'Dräger Evita V500',
    spare_part: 'AC-SP-0001',
    ...over,
  }
}

function mountView() {
  return mount(CMCreateView, { global: { stubs: { SmartSelect: true } } })
}

/** Gõ ≥2 ký tự vào ô tìm phụ tùng rồi chờ debounce 300ms + flush. */
async function typeSearch(w: ReturnType<typeof mountView>, q = 'Van') {
  const input = w.find('#cm-part-search')
  await input.setValue(q)
  await vi.advanceTimersByTimeAsync(350)
  await w.vm.$nextTick()
}

function suggestionButtons(w: ReturnType<typeof mountView>) {
  // Dropdown gợi ý là <ul> ngay sau ô tìm kiếm; mỗi gợi ý là 1 <button> trong <li>.
  return w.findAll('li > button')
}

/** Danh sách phụ tùng đã chọn (ô số lượng có id cm-part-qty-<i>). */
function selectedRows(w: ReturnType<typeof mountView>) {
  return w.findAll('[id^="cm-part-qty-"]')
}

describe('CMCreateView — gợi ý phụ tùng có khoá nhận dạng (CR-73a)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    routeQuery = {}
    pushSpy.mockClear()
    searchSparePartsMock.mockReset()
    requestSparePartsMock.mockClear()
  })

  it('T11 — 2 gợi ý trùng tên nhưng KHÁC model ⇒ 2 dòng + hiện CẢ HAI tên model', async () => {
    searchSparePartsMock.mockResolvedValue([
      suggestion({ device_model: 'MODEL-A', device_model_name: 'Dräger Evita V500', spare_part: 'AC-SP-0001' }),
      suggestion({ device_model: 'MODEL-B', device_model_name: 'Hamilton C3', spare_part: 'AC-SP-0002' }),
    ])
    const w = mountView()
    await typeSearch(w)

    expect(suggestionButtons(w)).toHaveLength(2)
    const text = w.text()
    expect(text).toContain('Dräger Evita V500')
    expect(text).toContain('Hamilton C3')
  })

  it('T11-bis — thiếu model_name ⇒ hiển thị PK model, KHÔNG bỏ trống', async () => {
    searchSparePartsMock.mockResolvedValue([
      suggestion({ device_model: 'MODEL-A', device_model_name: '', spare_part: 'AC-SP-0001' }),
    ])
    const w = mountView()
    await typeSearch(w)
    expect(w.text()).toContain('MODEL-A')
  })

  it('T12 — chọn 2 gợi ý khác nhau ⇒ 2 dòng, mỗi dòng có khoá THẬT', async () => {
    searchSparePartsMock.mockResolvedValue([
      suggestion({ device_model: 'MODEL-A', device_model_name: 'Dräger Evita V500', spare_part: 'AC-SP-0001' }),
      suggestion({ device_model: 'MODEL-B', device_model_name: 'Hamilton C3', spare_part: 'AC-SP-0002' }),
    ])
    const w = mountView()
    await typeSearch(w)
    await suggestionButtons(w)[0].trigger('click')

    await typeSearch(w)
    await suggestionButtons(w)[1].trigger('click')

    expect(selectedRows(w)).toHaveLength(2)
    // Dòng đã chọn hiển thị TÊN tiếng Việt, không phải mã trần.
    expect(w.text()).toContain('Van PEEP')
  })

  it('T12-bis — payload request_spare_parts mang ĐÚNG 2 khoá đã chọn (chống dead-control)', async () => {
    searchSparePartsMock.mockResolvedValue([
      suggestion({ device_model: 'MODEL-A', spare_part: 'AC-SP-0001', item_code: 'MPN-1' }),
      suggestion({ device_model: 'MODEL-B', spare_part: 'AC-SP-0002', item_code: 'MPN-2' }),
    ])
    const w = mountView()
    await typeSearch(w)
    await suggestionButtons(w)[0].trigger('click')
    await typeSearch(w)
    await suggestionButtons(w)[1].trigger('click')

    const parts = (w.vm as unknown as { preRequestParts: Array<{ spare_part: string }> }).preRequestParts
    expect(parts.map(p => p.spare_part)).toEqual(['AC-SP-0001', 'AC-SP-0002'])
    expect(parts.every(p => !!p.spare_part)).toBe(true)
  })

  it('T13 — click CÙNG 1 gợi ý 2 lần ⇒ chỉ 1 dòng', async () => {
    searchSparePartsMock.mockResolvedValue([suggestion({ spare_part: 'AC-SP-0001' })])
    const w = mountView()
    await typeSearch(w)
    await suggestionButtons(w)[0].trigger('click')
    await typeSearch(w)
    await suggestionButtons(w)[0].trigger('click')

    expect(selectedRows(w)).toHaveLength(1)
  })

  it('gợi ý không resolve (spare_part = "") ⇒ nút disabled + KHÔNG thêm dòng', async () => {
    searchSparePartsMock.mockResolvedValue([suggestion({ spare_part: '' })])
    const w = mountView()
    await typeSearch(w)

    const btn = suggestionButtons(w)[0]
    expect(btn.attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('Chưa có trong danh mục kho')

    await btn.trigger('click')
    expect(selectedRows(w)).toHaveLength(0)
  })

  it('BLOCKED-RELOAD — BE chưa có khoá `spare_part` ⇒ vẫn chọn được (lùi item_code)', async () => {
    // Response CŨ (10 khoá): thiếu hẳn device_model/device_model_name/spare_part.
    searchSparePartsMock.mockResolvedValue([
      { idx: 0, item_code: 'MPN-9', item_name: 'Van PEEP', manufacturer_part_no: 'MPN-9',
        qty: 1, uom: 'Cái', unit_cost: 0, total_cost: 0, stock_entry_ref: '', notes: '' },
    ])
    const w = mountView()
    await typeSearch(w)

    const btn = suggestionButtons(w)[0]
    expect(btn.attributes('disabled')).toBeUndefined()
    await btn.trigger('click')

    const parts = (w.vm as unknown as { preRequestParts: Array<{ spare_part: string }> }).preRequestParts
    expect(parts).toHaveLength(1)
    expect(parts[0].spare_part).toBe('MPN-9')
  })
})
