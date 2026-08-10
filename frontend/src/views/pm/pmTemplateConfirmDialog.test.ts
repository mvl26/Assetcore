// TC-UX065-5 / -8 / -10 — `PmTemplateListView` (2 call-site) di trú `confirm()` trần
// → `useModal()`: xoá mẫu bảo trì · áp mẫu cho toàn danh mục.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithConfirm, resetModalQueue, currentModal } from '@/test/confirmHarness'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const deletePmTemplate = vi.fn().mockResolvedValue({ deleted: 'PMT-0001' })
const applyPmTemplateToCategory = vi.fn().mockResolvedValue({
  created: 4, total_assets: 6, skipped_existing: 2, errors: 0,
})
const getPmTemplate = vi.fn(async () => ({
  name: 'PMT-0001', template_name: 'Mẫu bảo trì máy thở', pm_type: 'Preventive',
  asset_category: 'CAT-0001', version: '1', checklist_items: [],
}))

const TEMPLATES = [{
  name: 'PMT-0001', template_name: 'Mẫu bảo trì máy thở',
  display_template_name: 'Mẫu bảo trì máy thở', pm_type: 'Preventive',
  asset_category: 'CAT-0001', category_name: 'Máy thở', version: '1',
  effective_date: '2026-01-01',
}]

vi.mock('@/api/imm00', () => ({
  listPmTemplates: vi.fn(async () => ({ data: TEMPLATES, pagination: { total: TEMPLATES.length } })),
  getPmTemplate: (...a: unknown[]) => getPmTemplate(...a),
  createPmTemplate: vi.fn(), updatePmTemplate: vi.fn(),
  deletePmTemplate: (...a: unknown[]) => deletePmTemplate(...a),
  applyPmTemplateToCategory: (...a: unknown[]) => applyPmTemplateToCategory(...a),
}))

import PmTemplateListView from './PmTemplateListView.vue'

const ALL_APIS = [deletePmTemplate, applyPmTemplateToCategory]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let harness: any = null
// `SmartSelect` (bên trong biểu mẫu) đọc `useMasterDataStore()` ⇒ cần Pinia hoạt động.
beforeEach(() => { setActivePinia(createPinia()); harness = null; vi.clearAllMocks() })
afterEach(() => { resetModalQueue(); harness?.unmount(); harness = null })

async function mountList() {
  harness = mountWithConfirm(PmTemplateListView, {
    global: {
      stubs: {
        PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
        ListPageShell: { template: '<div><slot /></div>' },
        ListFilterBar: true, FilterToggleButton: true, SkeletonLoader: true,
        SmartSelect: true, DateInput: true,
      },
    },
  })
  await flushPromises()
  return harness.wrapper
}

/** Nút «Xóa» đầu tiên trong bảng danh sách. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function deleteBtn(w: any) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const b = (w.findAll('button') as any[]).find((x) => x.text().trim() === 'Xóa')
  if (!b) throw new Error('không tìm thấy nút «Xóa» trong danh sách mẫu')
  return b
}

describe('TC-UX065-5 — PmTemplateListView: xoá mẫu bảo trì qua hộp thoại SSoT', () => {
  it('bấm «Xóa» ⇒ hộp thoại hiện tiếng Việt, tone error, CHƯA gọi API', async () => {
    const w = await mountList()
    await deleteBtn(w).trigger('click')
    await flushPromises()

    const req = currentModal()
    expect(req, 'không có hộp thoại ⇒ vẫn dùng confirm() trần').toBeTruthy()
    expect(req!.tone, 'xoá là hành động phá huỷ (TC-UX065-8)').toBe('error')
    // LL-FE-53: nhãn kỹ thuật «template» phải được Việt hoá thành «mẫu bảo trì».
    expect(`${req!.title} ${req!.body}`).not.toMatch(/\btemplate\b/i)
    expect(`${req!.title} ${req!.body}`).toMatch(/mẫu/i)
    expect(deletePmTemplate).not.toHaveBeenCalled()
  })

  it('«Huỷ» ⇒ 0 lời gọi API', async () => {
    const w = await mountList()
    await deleteBtn(w).trigger('click')
    await flushPromises()
    await harness.answerConfirm(false)
    for (const spy of ALL_APIS) expect(spy).not.toHaveBeenCalled()
  })

  it('«Xác nhận» ⇒ ĐÚNG 1 lời gọi deletePmTemplate(name) với payload cũ', async () => {
    const w = await mountList()
    await deleteBtn(w).trigger('click')
    await flushPromises()
    await harness.answerConfirm(true)
    expect(deletePmTemplate).toHaveBeenCalledTimes(1)
    expect(deletePmTemplate).toHaveBeenCalledWith('PMT-0001')
    expect(applyPmTemplateToCategory).not.toHaveBeenCalled()
  })
})

describe('TC-UX065-5b — PmTemplateListView: áp mẫu cho danh mục qua hộp thoại SSoT', () => {
  /** Mở biểu mẫu sửa (cần `editingName`) rồi lấy nút áp-dụng. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async function openEditAndFindApply(w: any) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const edit = (w.findAll('button') as any[]).find((x) => x.text().trim() === 'Sửa')
    expect(edit, 'không tìm thấy nút «Sửa»').toBeTruthy()
    await edit.trigger('click')
    await flushPromises()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const apply = (w.findAll('button') as any[]).find((x) => x.text().includes('Tạo lịch bảo trì định kỳ cho mọi thiết bị'))
    expect(apply, 'không tìm thấy nút áp dụng mẫu cho danh mục').toBeTruthy()
    return apply
  }

  it('bấm «áp dụng» ⇒ hộp thoại hiện, giữ NGUYÊN câu tiếng Việt cũ, CHƯA gọi API', async () => {
    const w = await mountList()
    const apply = await openEditAndFindApply(w)
    await apply.trigger('click')
    await flushPromises()

    const req = currentModal()
    expect(req).toBeTruthy()
    // Câu gốc được giữ nguyên trong `body` (không viết lại nghĩa).
    expect(req!.body).toContain('Tạo lịch bảo trì định kỳ cho mọi thiết bị thuộc danh mục')
    expect(req!.body).toContain('Thiết bị đã có lịch cùng loại bảo trì định kỳ sẽ được giữ nguyên.')
    // Không phá huỷ ⇒ KHÔNG dùng tone error.
    expect(req!.tone).not.toBe('error')
    expect(applyPmTemplateToCategory).not.toHaveBeenCalled()
  })

  it('«Huỷ» ⇒ 0 lời gọi API', async () => {
    const w = await mountList()
    const apply = await openEditAndFindApply(w)
    await apply.trigger('click')
    await flushPromises()
    await harness.answerConfirm(false)
    for (const spy of ALL_APIS) expect(spy).not.toHaveBeenCalled()
  })

  it('«Xác nhận» ⇒ ĐÚNG 1 lời gọi applyPmTemplateToCategory(editingName)', async () => {
    const w = await mountList()
    const apply = await openEditAndFindApply(w)
    await apply.trigger('click')
    await flushPromises()
    await harness.answerConfirm(true)
    expect(applyPmTemplateToCategory).toHaveBeenCalledTimes(1)
    expect(applyPmTemplateToCategory).toHaveBeenCalledWith('PMT-0001')
    expect(deletePmTemplate).not.toHaveBeenCalled()
  })
})
