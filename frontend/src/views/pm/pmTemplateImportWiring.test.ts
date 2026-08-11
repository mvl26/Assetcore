// Copyright (c) 2026, AssetCore Team
//
// TDD — /pm/templates phải nhập/xuất được mẫu bảng kiểm bằng Excel.
// Bảng kiểm là dữ liệu CHA + BẢNG CON: 1 hàng file = 1 hạng mục, BE gộp theo
// Danh mục + Loại bảo trì. Guard: (a) hai nút có mặt và mở đúng luồng;
// (b) wizard gắn đúng loại dữ liệu 'PM Checklist Template' (sai loại ⇒ tải nhầm
// template và nhập nhầm bảng); (c) kết quả hiện SỐ MẪU đã tạo, không chỉ số dòng
// — "12/12 dòng" mà không nói tạo mấy mẫu là vô nghĩa với người dùng.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listPmTemplatesSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  listPmTemplates: (...a: unknown[]) => listPmTemplatesSpy(...a),
  getPmTemplate: vi.fn(),
  createPmTemplate: vi.fn(),
  updatePmTemplate: vi.fn(),
  deletePmTemplate: vi.fn(),
  applyPmTemplateToCategory: vi.fn(),
}))

const useImportWizardSpy = vi.fn()
vi.mock('@/composables/useImportWizard', async () => {
  const actual = await vi.importActual<typeof import('@/composables/useImportWizard')>(
    '@/composables/useImportWizard',
  )
  return {
    useImportWizard: (...a: Parameters<typeof actual.useImportWizard>) => {
      useImportWizardSpy(...a)
      return actual.useImportWizard(...a)
    },
  }
})

vi.mock('@/api/importData', () => ({
  previewRefImport: vi.fn(),
  importRefData: vi.fn(),
  buildErrorReport: vi.fn(),
  initImportFolders: vi.fn().mockResolvedValue('Home/AssetCore Imports/PM_Checklist_Template'),
  getExportUrl: (dt: string) => `/export?doctype=${dt}`,
  getTemplateUrl: (dt: string) => `/template?doctype=${dt}`,
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import PmTemplateListView from './PmTemplateListView.vue'
import ImportWizardModal from '@/components/import/ImportWizardModal.vue'

const stubs = { PageHeader: false, FilterToggleButton: true, SmartSelect: true, DateInput: true }

async function mountView() {
  const w = mount(PmTemplateListView, { global: { stubs } })
  await flushPromises()
  return w
}

describe('/pm/templates — nhập/xuất mẫu bảng kiểm', () => {
  beforeEach(() => {
    resetRouteMock()
    useImportWizardSpy.mockReset()
    listPmTemplatesSpy.mockReset().mockResolvedValue({ data: [], pagination: { total: 0 } })
  })

  it('gắn wizard đúng loại dữ liệu mẫu bảng kiểm', async () => {
    await mountView()
    expect(useImportWizardSpy).toHaveBeenCalledTimes(1)
    expect(useImportWizardSpy.mock.calls[0][0]).toBe('PM Checklist Template')
  })

  it('có nút Nhập Excel + Xuất Excel ngay cả khi danh sách rỗng', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="pm-template-import"]').exists()).toBe(true)
    expect(w.find('[data-testid="pm-template-export"]').exists()).toBe(true)
  })

  it('bấm Nhập Excel mở wizard (hộp thoại nằm NGOÀI khuôn 4 trạng thái)', async () => {
    const w = await mountView()
    expect(w.findComponent(ImportWizardModal).find('input[type="file"]').exists()).toBe(false)
    await w.find('[data-testid="pm-template-import"]').trigger('click')
    await flushPromises()
    expect(w.findComponent(ImportWizardModal).find('input[type="file"]').exists()).toBe(true)
  })

  it('truyền đơn vị đếm theo dòng VÀ theo mẫu cho bước kết quả', async () => {
    const w = await mountView()
    const modal = w.findComponent(ImportWizardModal)
    expect(modal.props('unit')).toBe('hạng mục')
    expect(modal.props('groupUnit')).toBe('mẫu bảng kiểm')
  })

  it('lưu ý trước khi nhập nói rõ 1 hàng = 1 hạng mục và điền TÊN danh mục', async () => {
    const w = await mountView()
    const notice = (w.findComponent(ImportWizardModal).props('notice') ?? []).join(' ')
    expect(notice).toContain('1 hạng mục kiểm tra')
    expect(notice).toContain('TÊN')
  })
})
