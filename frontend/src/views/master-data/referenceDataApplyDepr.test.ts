// TDD — IMM-00 ReferenceDataView "Áp dụng luật khấu hao cho danh mục"
// (bulk_regenerate_schedule_by_category).
//   • UX: click 'Áp dụng' KHÔNG gọi window.confirm — mở BaseModal xác nhận;
//     chỉ khi xác nhận trong modal mới gọi API (skill rule WAVE2 pattern).
//   • Kết quả render đủ: inherited / regenerated / skipped_has_history /
//     skipped_no_rule / errors qua data-testid (KHÔNG leak raw method/token).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { BulkRegenerateResult } from '@/api/imm00'

const listAssetCategoriesSpy = vi.fn()
const getAssetCategorySpy = vi.fn()
const bulkRegenSpy = vi.fn<() => Promise<BulkRegenerateResult>>()

vi.mock('@/api/imm00', () => ({
  listLocations: () => Promise.resolve([]),
  getLocation: vi.fn(),
  createLocation: vi.fn(),
  updateLocation: vi.fn(),
  deleteLocation: vi.fn(),
  listDepartments: () => Promise.resolve([]),
  getDepartment: vi.fn(),
  createDepartment: vi.fn(),
  updateDepartment: vi.fn(),
  deleteDepartment: vi.fn(),
  listAssetCategories: () => listAssetCategoriesSpy(),
  getAssetCategory: (...a: unknown[]) => getAssetCategorySpy(...a),
  createAssetCategory: vi.fn(),
  updateAssetCategory: vi.fn(),
  deleteAssetCategory: vi.fn(),
  bulkRegenerateScheduleByCategory: (...a: unknown[]) => bulkRegenSpy(...a),
}))

// importData + axios are imported by the view but unused on this path.
vi.mock('@/api/importData', () => ({
  previewRefImport: vi.fn(), importRefData: vi.fn(), buildErrorReport: vi.fn(),
  getExportUrl: () => '', getTemplateUrl: () => '', initImportFolders: vi.fn(),
}))
vi.mock('@/api/axios', () => ({
  default: { get: vi.fn().mockResolvedValue({ data: { message: null } }) },
}))

const toastSuccess = vi.fn()
const toastError = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: toastSuccess, error: toastError, info: vi.fn() }),
}))

import ReferenceDataView from './ReferenceDataView.vue'

const CATEGORY = {
  name: 'CAT-0001',
  category_name: 'Máy thở',
  category_code: 'VENT',
  default_depreciation_method: 'Straight Line',
  total_depreciation_months: 60,
  depreciation_frequency: 'Monthly',
  default_residual_value_pct: 10,
  is_active: 1,
}

const RESULT: BulkRegenerateResult = {
  category: 'CAT-0001',
  total_assets: 12,
  inherited: 4,
  regenerated: 6,
  skipped_has_history: 3,
  skipped_no_rule: 2,
  errors: 1,
}

// BaseModal teleports to <body>; render inline so wrapper queries reach it.
const stubs = { SmartSelect: true, teleport: true }

async function openCategoryEditForm() {
  const wrapper = mount(ReferenceDataView, { global: { stubs } })
  await flushPromises()
  // switch to the 'category' tab
  const catTab = wrapper.findAll('button').find(b => b.text() === 'Danh mục tài sản')
  await catTab!.trigger('click')
  await flushPromises()
  // open edit on the seeded category row
  const editBtn = wrapper.findAll('button').find(b => b.text() === 'Sửa')
  await editBtn!.trigger('click')
  await flushPromises()
  return wrapper
}

describe('ReferenceDataView — áp dụng luật khấu hao (BaseModal + 5-number result)', () => {
  let confirmSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    listAssetCategoriesSpy.mockResolvedValue([CATEGORY])
    getAssetCategorySpy.mockResolvedValue(CATEGORY)
    bulkRegenSpy.mockReset()
    bulkRegenSpy.mockResolvedValue(RESULT)
    toastSuccess.mockReset()
    toastError.mockReset()
    confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => { confirmSpy.mockRestore() })

  it('nút "Áp dụng" hiện khi đang sửa 1 danh mục', async () => {
    const wrapper = await openCategoryEditForm()
    expect(wrapper.find('[data-testid="apply-depr-btn"]').exists()).toBe(true)
  })

  it('click "Áp dụng" KHÔNG gọi window.confirm — mở BaseModal; API chưa gọi', async () => {
    const wrapper = await openCategoryEditForm()

    await wrapper.find('[data-testid="apply-depr-btn"]').trigger('click')
    await flushPromises()

    expect(confirmSpy).not.toHaveBeenCalled()
    expect(bulkRegenSpy).not.toHaveBeenCalled()
    // modal xác nhận đã mở
    expect(wrapper.find('[data-testid="apply-confirm-btn"]').exists()).toBe(true)
    // nội dung VI nêu rõ giữ nguyên tài sản đã có kỳ chạy
    expect(wrapper.find('[data-testid="apply-confirm-body"]').text())
      .toContain('giữ nguyên')
  })

  it('xác nhận trong modal → gọi API và render đủ 5 số kết quả', async () => {
    const wrapper = await openCategoryEditForm()

    await wrapper.find('[data-testid="apply-depr-btn"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="apply-confirm-btn"]').trigger('click')
    await flushPromises()

    expect(bulkRegenSpy).toHaveBeenCalledTimes(1)
    expect(bulkRegenSpy).toHaveBeenCalledWith('CAT-0001')
    expect(confirmSpy).not.toHaveBeenCalled()

    expect(wrapper.find('[data-testid="apply-result-inherited"]').text()).toBe('4')
    expect(wrapper.find('[data-testid="apply-result-regenerated"]').text()).toBe('6')
    expect(wrapper.find('[data-testid="apply-result-skipped-history"]').text()).toBe('3')
    expect(wrapper.find('[data-testid="apply-result-skipped-no-rule"]').text()).toBe('2')
    expect(wrapper.find('[data-testid="apply-result-errors"]').text()).toBe('1')
  })

  it('toast tổng kết KHÔNG leak raw method/token, có đủ 4 nhóm số', async () => {
    const wrapper = await openCategoryEditForm()
    await wrapper.find('[data-testid="apply-depr-btn"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="apply-confirm-btn"]').trigger('click')
    await flushPromises()

    expect(toastSuccess).toHaveBeenCalledTimes(1)
    const msg = toastSuccess.mock.calls[0][0] as string
    expect(msg).toContain('Kế thừa luật 4')
    expect(msg).toContain('Sinh lịch 6')
    expect(msg).toContain('Giữ lịch sử 3')
    expect(msg).toContain('Thiếu luật 2')
    // KHÔNG leak raw method/token (vd 'Straight Line', 'csrf', tên field BE).
    expect(msg).not.toContain('Straight Line')
    expect(msg).not.toMatch(/token|csrf/i)
  })

  it('hủy trong modal → KHÔNG gọi API', async () => {
    const wrapper = await openCategoryEditForm()
    await wrapper.find('[data-testid="apply-depr-btn"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="apply-cancel-btn"]').trigger('click')
    await flushPromises()

    expect(bulkRegenSpy).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="apply-confirm-btn"]').exists()).toBe(false)
  })
})
