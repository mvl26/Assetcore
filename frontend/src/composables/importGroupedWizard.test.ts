// Copyright (c) 2026, AssetCore Team
//
// TDD — Nhập NHIỀU bản ghi cha từ MỘT file phẳng (mẫu bảng kiểm: cha + bảng con).
//
// Người dùng điền 30 hàng và không có cách nào biết ra mấy MẪU, mẫu nào đã tồn
// tại, cập nhật thì mất gì. Guard 3 điều:
//   (a) tóm tắt theo nhóm map đủ sang camelCase để màn hình dựng được bảng;
//   (b) bật "cập nhật bản ghi đã có" ⇒ HỎI LẠI server (không tự lọc lỗi ở FE);
//   (c) cờ update_existing đi kèm cả preview lẫn import, mặc định TẮT.
import { describe, it, expect, vi, beforeEach } from 'vitest'

const previewRefImport = vi.fn()
const importRefData = vi.fn()
const initImportFolders = vi.fn().mockResolvedValue('Home/AssetCore Imports')

vi.mock('@/api/importData', () => ({
  previewRefImport: (...a: unknown[]) => previewRefImport(...a),
  importRefData: (...a: unknown[]) => importRefData(...a),
  initImportFolders: (...a: unknown[]) => initImportFolders(...a),
  buildErrorReport: vi.fn(),
  getExportUrl: vi.fn(() => '/export'),
  getTemplateUrl: vi.fn(() => '/template'),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ error: vi.fn(), success: vi.fn() }),
}))

import { useImportWizard } from './useImportWizard'

const DOCTYPE = 'PM Checklist Template' as const

function previewPayload(overrides: Record<string, unknown> = {}) {
  return {
    doctype: DOCTYPE,
    totalRows: 4,
    validRows: 4,
    preview: [],
    fieldnames: ['template_name'],
    fieldLabels: {},
    errors: [],
    warnings: [],
    cascadeCount: 0,
    groups: [
      {
        key: 'CAT-0001 · Quarterly',
        nameValue: 'Bảng kiểm quý — Máy thở',
        rows: 3, items: 3, firstSourceRow: 6,
        exists: false, existingItems: 0, action: 'create',
        category: 'Máy thở', pmType: 'Hàng quý',
      },
      {
        key: 'CAT-0002 · Annual',
        nameValue: 'Bảng kiểm năm — Máy siêu âm',
        rows: 1, items: 1, firstSourceRow: 9,
        exists: true, existingItems: 5, action: 'blocked',
        category: 'Máy siêu âm chẩn đoán', pmType: 'Hàng năm',
      },
    ],
    groupsTotal: 2,
    ...overrides,
  }
}

describe('wizard nhập theo nhóm — nhiều mẫu trong một file', () => {
  beforeEach(() => {
    previewRefImport.mockReset()
    importRefData.mockReset()
    previewRefImport.mockResolvedValue(previewPayload())
    importRefData.mockResolvedValue({
      total: 4, success: 4, failed: 0, skipped: 0,
      errors: [], skippedRows: [], groupsCreated: 1, groupsUpdated: 1,
    })
  })

  async function openedWizard() {
    const w = useImportWizard(DOCTYPE)
    await w.open()
    w.uploadedFileUrl.value = '/files/bang-kiem.xlsx'
    await w.runImport   // giữ tham chiếu, không gọi
    return w
  }

  it('tóm tắt nhóm cho biết ra MẤY mẫu, không chỉ mấy dòng', async () => {
    const w = await openedWizard()
    await w.toggleUpdateExisting(false)          // không đổi ⇒ không gọi lại
    w.previewData.value = previewPayload() as never

    expect(w.groups.value).toHaveLength(2)
    expect(w.groups.value[0].items).toBe(3)
    expect(w.groups.value[0].firstSourceRow).toBe(6)
    expect(w.groups.value[1].existingItems).toBe(5)
    expect(w.hasExistingRecords.value).toBe(true)
  })

  it('không có nhóm nào tồn tại ⇒ không mời chào ghi đè', async () => {
    const w = await openedWizard()
    w.previewData.value = previewPayload({
      groups: [{
        key: 'k', nameValue: 'A', rows: 1, items: 1, firstSourceRow: 6,
        exists: false, existingItems: 0, action: 'create',
      }],
    }) as never
    expect(w.hasExistingRecords.value).toBe(false)
  })

  it('bật cập nhật ⇒ hỏi LẠI server thay vì tự lọc lỗi ở FE', async () => {
    const w = await openedWizard()
    previewRefImport.mockResolvedValueOnce(previewPayload({
      groups: [{
        key: 'CAT-0002 · Annual', nameValue: 'Bảng kiểm năm — Máy siêu âm',
        rows: 1, items: 1, firstSourceRow: 9,
        exists: true, existingItems: 5, action: 'update',
      }],
    }))

    await w.toggleUpdateExisting(true)

    expect(previewRefImport).toHaveBeenCalledWith(
      DOCTYPE, '/files/bang-kiem.xlsx', true,
    )
    expect(w.updateExisting.value).toBe(true)
    expect(w.groups.value[0].action).toBe('update')
  })

  it('bật rồi bật lại cùng giá trị ⇒ không gọi lại server', async () => {
    const w = await openedWizard()
    await w.toggleUpdateExisting(true)
    const calls = previewRefImport.mock.calls.length
    await w.toggleUpdateExisting(true)
    expect(previewRefImport.mock.calls.length).toBe(calls)
  })

  it('mặc định TẮT — mở wizard lần sau không giữ lựa chọn ghi đè', async () => {
    const w = await openedWizard()
    await w.toggleUpdateExisting(true)
    expect(w.updateExisting.value).toBe(true)

    await w.open()
    expect(w.updateExisting.value).toBe(false)
  })

  it('nhập: gửi kèm cờ cập nhật và nhận lại số mẫu tạo/cập nhật', async () => {
    const w = await openedWizard()
    await w.toggleUpdateExisting(true)
    await w.runImport()

    expect(importRefData).toHaveBeenCalledWith(
      DOCTYPE, '/files/bang-kiem.xlsx', 'strict', true,
    )
    expect(w.importResult.value?.groupsCreated).toBe(1)
    expect(w.importResult.value?.groupsUpdated).toBe(1)
  })

  it('không bật gì ⇒ import vẫn gửi cờ TẮT (không để undefined trôi xuống BE)', async () => {
    const w = await openedWizard()
    await w.runImport()
    expect(importRefData).toHaveBeenCalledWith(
      DOCTYPE, '/files/bang-kiem.xlsx', 'strict', false,
    )
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// Loại dữ liệu PHẲNG (nhà cung cấp, danh mục…): không có nhóm, nhưng vẫn phải
// cập nhật được bản ghi đã có — đây là vòng "Xuất → sửa → Nhập lại".
// ─────────────────────────────────────────────────────────────────────────────

const FLAT_DOCTYPE = 'AC Supplier' as const

function flatPreview(overrides: Record<string, unknown> = {}) {
  return {
    doctype: FLAT_DOCTYPE,
    totalRows: 5,
    validRows: 5,
    preview: [], fieldnames: [], fieldLabels: {},
    errors: [], warnings: [], cascadeCount: 0,
    willCreate: 3, willUpdate: 0, existingRows: 2,
    ...overrides,
  }
}

describe('wizard loại dữ liệu phẳng — cập nhật bản ghi đã có', () => {
  beforeEach(() => {
    previewRefImport.mockReset()
    importRefData.mockReset()
    previewRefImport.mockResolvedValue(flatPreview())
    importRefData.mockResolvedValue({
      total: 5, success: 5, failed: 0, skipped: 0,
      errors: [], skippedRows: [], updated: 2,
    })
  })

  async function opened(preview = flatPreview()) {
    const w = useImportWizard(FLAT_DOCTYPE)
    await w.open()
    w.uploadedFileUrl.value = '/files/ncc.xlsx'
    w.previewData.value = preview as never
    return w
  }

  it('có dòng trùng ⇒ mời chào bật cập nhật, dù công tắc đang TẮT', async () => {
    const w = await opened()
    expect(w.groups.value).toHaveLength(0)
    expect(w.updateExisting.value).toBe(false)
    expect(w.hasExistingRecords.value).toBe(true)
  })

  it('không dòng nào trùng ⇒ không mời chào ghi đè', async () => {
    const w = await opened(flatPreview({ existingRows: 0, willCreate: 5 }))
    expect(w.hasExistingRecords.value).toBe(false)
  })

  it('bật cập nhật ⇒ preview lại và trả về số dòng sẽ sửa', async () => {
    const w = await opened()
    previewRefImport.mockResolvedValueOnce(
      flatPreview({ willCreate: 3, willUpdate: 2 }))

    await w.toggleUpdateExisting(true)

    expect(previewRefImport).toHaveBeenLastCalledWith(
      FLAT_DOCTYPE, '/files/ncc.xlsx', true)
    expect(w.previewData.value?.willUpdate).toBe(2)
  })

  it('kết quả nhập tách riêng số bản ghi ĐƯỢC CẬP NHẬT', async () => {
    const w = await opened()
    await w.toggleUpdateExisting(true)
    await w.runImport()
    expect(w.importResult.value?.updated).toBe(2)
    expect(w.importResult.value?.groupsCreated).toBeUndefined()
  })
})
