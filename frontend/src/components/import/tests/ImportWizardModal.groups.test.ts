// Copyright (c) 2026, AssetCore Team
//
// Bước "Kiểm tra" của wizard phải trả lời được câu hỏi của người nhập liệu:
// "tôi điền 4 hàng thì ra MẤY mẫu, mẫu nào đã có, bấm nhập thì mất gì".
// Guard chống 2 lỗi đã gặp: (a) chỉ hiện số DÒNG cho DocType cha+bảng con;
// (b) control ghi đè là nút chết — hiện ra nhưng không nối tay cầm.
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { computed, ref } from 'vue'

import ImportWizardModal from '@/components/import/ImportWizardModal.vue'
import type { ImportGroupSummary } from '@/types/import'

const GROUPS: ImportGroupSummary[] = [
  {
    key: 'CAT-0001 · Quarterly', nameValue: 'Bảng kiểm quý — Máy thở',
    rows: 3, items: 3, firstSourceRow: 6,
    exists: false, existingItems: 0, action: 'create',
    category: 'Máy thở', pmType: 'Hàng quý',
  },
  {
    key: 'CAT-0002 · Annual', nameValue: 'Bảng kiểm năm — Máy siêu âm',
    rows: 1, items: 1, firstSourceRow: 9,
    exists: true, existingItems: 5, action: 'blocked',
    category: 'Máy siêu âm chẩn đoán', pmType: 'Hàng năm',
  },
]

function makeCtx(groupList: ImportGroupSummary[] = GROUPS) {
  // `hasExistingRecords` phải suy ra TỪ CHÍNH ref đang dùng — dựng hai nguồn rời
  // nhau là test tự nói dối (đúng cái bẫy composable thật phải tránh).
  const groups = ref<ImportGroupSummary[]>(groupList)
  const ctx = {
    showImport: ref(true),
    importStep: ref('preview'),
    uploading: ref(false),
    importLoading: ref(false),
    uploadedFileUrl: ref('/files/x.xlsx'),
    uploadedFileName: ref('bang-kiem.xlsx'),
    importFolder: ref('Home'),
    previewData: ref({
      doctype: 'PM Checklist Template',
      totalRows: 4, validRows: 4, preview: [], fieldnames: [], fieldLabels: {},
      errors: [], warnings: [], cascadeCount: 0,
      groups: groups.value, groupsTotal: 2,
    }),
    importResult: ref(null),
    importErr: ref(''),
    isDragOver: ref(false),
    importMode: ref('strict'),
    updateExisting: ref(false),
    open: vi.fn(), close: vi.fn(),
    handleFileChange: vi.fn(), handleDrop: vi.fn(),
    toggleUpdateExisting: vi.fn(),
    runImport: vi.fn(), downloadErrorReport: vi.fn(),
    doExport: vi.fn(), doDownloadTemplate: vi.fn(),
    hasBlockingErrors: computed(() => false),
    totalSkip: computed(() => 0),
    skipRatio: computed(() => 0),
    allRowsInvalid: computed(() => false),
    canImport: computed(() => true),
    groups,
    hasExistingRecords: computed(() => groups.value.some(g => g.exists)),
  }
  return ctx
}

function mountWizard(ctx = makeCtx()) {
  return mount(ImportWizardModal, {
    props: {
      ctx: ctx as never,
      title: 'Nhập mẫu bảng kiểm bảo trì',
      unit: 'hạng mục',
      groupUnit: 'mẫu bảng kiểm',
    },
  })
}

describe('wizard bước kiểm tra — tóm tắt theo mẫu', () => {
  it('nói rõ 4 dòng ra 2 mẫu, kèm số hạng mục từng mẫu', () => {
    const text = mountWizard().text()
    expect(text).toContain('2')
    expect(text).toContain('mẫu bảng kiểm')
    expect(text).toContain('Bảng kiểm quý — Máy thở')
    expect(text).toContain('Bảng kiểm năm — Máy siêu âm')
    expect(text).toContain('3 hạng mục')
  })

  it('mẫu đã tồn tại hiện rõ đang bị chặn + đang có bao nhiêu hạng mục', () => {
    const text = mountWizard().text()
    expect(text).toContain('Đã tồn tại')
    expect(text).toContain('5 hạng mục')
    expect(text).toContain('Tạo mới')
  })

  it('chỉ ra HÀNG THẬT trong file để mở đúng chỗ mà sửa', () => {
    const text = mountWizard().text()
    expect(text).toContain('hàng 6')
    expect(text).toContain('hàng 9')
  })

  it('công tắc ghi đè nối thật vào tay cầm, không phải nút chết', async () => {
    const ctx = makeCtx()
    const wrapper = mountWizard(ctx)
    const box = wrapper.find('input[type="checkbox"]')

    expect(box.exists()).toBe(true)
    expect((box.element as HTMLInputElement).checked).toBe(false)

    await box.setValue(true)
    expect(ctx.toggleUpdateExisting).toHaveBeenCalledWith(true)
  })

  it('không mẫu nào trùng ⇒ không mời chào ghi đè', () => {
    const ctx = makeCtx([GROUPS[0]])
    const wrapper = mountWizard(ctx)
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(false)
  })

  it('loại dữ liệu phẳng ⇒ không dựng bảng tóm tắt nhóm', () => {
    const ctx = makeCtx([])
    const wrapper = mountWizard(ctx)
    expect(wrapper.text()).not.toContain('sẽ tạo/cập nhật')
  })
})
