// TDD — IMM-00 ReferenceDataView "Áp dụng luật khấu hao cho tất cả tài sản"
// (bulk_regenerate_schedule_by_category).
//
// Acceptance (RC-05 / BR-00-23):
//   - Click "Áp dụng" → mở BaseModal xác nhận (KHÔNG window.confirm); API CHƯA gọi.
//   - Confirm trong modal → gọi bulkRegenerateScheduleByCategory(category).
//   - Render kết quả inherited / regenerated / skipped_has_history /
//     skipped_no_rule / errors qua data-testid (payload 7-key, mirror compute_all).
//   - KHÔNG leak raw method/token vào toast/modal.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { BulkRegenerateResult, AcAssetCategory } from '@/api/imm00'

// ── API mocks ────────────────────────────────────────────────────────────────
const bulkRegenSpy = vi.fn<(c: string) => Promise<BulkRegenerateResult>>()
const _CAT: AcAssetCategory = {
  name: 'CAT-0001', category_name: '_Test Cat',
  total_depreciation_months: 60, default_residual_value_pct: 10,
} as unknown as AcAssetCategory

vi.mock('@/api/imm00', () => ({
  listLocations: vi.fn().mockResolvedValue([]),
  getLocation: vi.fn().mockResolvedValue({}),
  createLocation: vi.fn(), updateLocation: vi.fn(), deleteLocation: vi.fn(),
  listDepartments: vi.fn().mockResolvedValue([]),
  getDepartment: vi.fn().mockResolvedValue({}),
  createDepartment: vi.fn(), updateDepartment: vi.fn(), deleteDepartment: vi.fn(),
  listAssetCategories: vi.fn().mockResolvedValue([
    { name: 'CAT-0001', category_name: '_Test Cat' },
  ]),
  getAssetCategory: vi.fn().mockResolvedValue({
    name: 'CAT-0001', category_name: '_Test Cat',
    total_depreciation_months: 60, default_residual_value_pct: 10,
  }),
  createAssetCategory: vi.fn(), updateAssetCategory: vi.fn(), deleteAssetCategory: vi.fn(),
  bulkRegenerateScheduleByCategory: (c: string) => bulkRegenSpy(c),
}))

vi.mock('@/api/importData', () => ({
  previewRefImport: vi.fn(), importRefData: vi.fn(), buildErrorReport: vi.fn(),
  getExportUrl: vi.fn().mockReturnValue('#'), getTemplateUrl: vi.fn().mockReturnValue('#'),
  initImportFolders: vi.fn().mockResolvedValue(''),
}))

vi.mock('@/api/axios', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

import ReferenceDataView from '@/views/master-data/ReferenceDataView.vue'

// BaseModal NOT stubbed → modal body/footer render so we can assert the buttons
// and the 5 result numbers. SmartSelect stubbed (it pulls remote options).
const stubs = {
  SmartSelect: { template: '<div />' },
  RouterLink: true,
  teleport: true,
}

const RESULT: BulkRegenerateResult = {
  category: 'CAT-0001',
  total_assets: 9,
  inherited: 2,
  regenerated: 4,
  skipped_has_history: 2,
  skipped_no_rule: 1,
  errors: 0,
}

async function openCategoryEditForm(wrapper: ReturnType<typeof mount>) {
  // Switch to the "Danh mục tài sản" tab, then open the category edit form so
  // editingName is set (the apply button only renders for tab==='category' &&
  // editingName). The view exposes openEdit via its setup return on the vm.
  const vm = wrapper.vm as unknown as {
    tab: string
    openEdit: (row: Record<string, unknown>) => Promise<void>
  }
  vm.tab = 'category'
  await flushPromises()
  await vm.openEdit({ name: 'CAT-0001', category_name: '_Test Cat' })
  await flushPromises()
}

function applyBtn(wrapper: ReturnType<typeof mount>) {
  return wrapper.find('[data-testid="apply-depr-btn"]')
}

describe('ReferenceDataView — bulk_regenerate (BaseModal confirm + 5-number result)', () => {
  let confirmSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    bulkRegenSpy.mockReset()
    bulkRegenSpy.mockResolvedValue(RESULT)
    // window.confirm MUST never be used for this flow (WAVE2 pattern).
    confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => {
    confirmSpy.mockRestore()
  })

  it('nút "Áp dụng" hiển thị khi đang sửa 1 Danh mục', async () => {
    const wrapper = mount(ReferenceDataView, { global: { stubs } })
    await flushPromises()
    await openCategoryEditForm(wrapper)
    expect(applyBtn(wrapper).exists()).toBe(true)
  })

  it('click "Áp dụng" → mở BaseModal xác nhận, KHÔNG window.confirm, API chưa gọi', async () => {
    const wrapper = mount(ReferenceDataView, { global: { stubs } })
    await flushPromises()
    await openCategoryEditForm(wrapper)

    await applyBtn(wrapper).trigger('click')
    await flushPromises()

    // window.confirm tuyệt đối KHÔNG được gọi cho luồng này.
    expect(confirmSpy).not.toHaveBeenCalled()
    // API CHƯA được gọi cho tới khi xác nhận trong modal.
    expect(bulkRegenSpy).not.toHaveBeenCalled()
    // BaseModal xác nhận đã mở → có nút "Xác nhận áp dụng".
    const confirmBtn = wrapper.findAll('button').find(
      b => b.text().includes('Xác nhận áp dụng'))
    expect(confirmBtn).toBeTruthy()
  })

  it('confirm trong modal → gọi API với đúng category + render 5 số kết quả', async () => {
    const wrapper = mount(ReferenceDataView, { global: { stubs } })
    await flushPromises()
    await openCategoryEditForm(wrapper)

    await applyBtn(wrapper).trigger('click')
    await flushPromises()

    const confirmBtn = wrapper.findAll('button').find(
      b => b.text().includes('Xác nhận áp dụng'))!
    await confirmBtn.trigger('click')
    await flushPromises()

    // API gọi đúng 1 lần với category đang sửa.
    expect(bulkRegenSpy).toHaveBeenCalledTimes(1)
    expect(bulkRegenSpy).toHaveBeenCalledWith('CAT-0001')

    // Result modal render đủ 5 số qua data-testid.
    expect(wrapper.find('[data-testid="apply-result-inherited"]').text()).toBe('2')
    expect(wrapper.find('[data-testid="apply-result-regenerated"]').text()).toBe('4')
    expect(wrapper.find('[data-testid="apply-result-skipped-history"]').text()).toBe('2')
    expect(wrapper.find('[data-testid="apply-result-skipped-no-rule"]').text()).toBe('1')
    expect(wrapper.find('[data-testid="apply-result-errors"]').text()).toBe('0')

    // KHÔNG leak raw method/token: payload không có 'depreciation_method' hay
    // các khoá kỹ thuật trong DOM hiển thị.
    expect(wrapper.html()).not.toContain('depreciation_method')
  })
})
