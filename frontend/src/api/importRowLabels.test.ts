// Copyright (c) 2026, AssetCore Team
//
// TDD — Import wizard phải chỉ đúng "sai ở hàng nào, cột nào".
// BE đánh số theo dòng dữ liệu (bỏ dòng trống) + fieldname tiếng Anh; người dùng
// chỉ biết số hàng ở lề trái Excel và nhãn tiếng Việt ở hàng 3 của template.
// Guard: (a) map source_row → sourceRow; (b) map label → label với fallback về
// fieldname; (c) file BE cũ (không có 2 khoá này) vẫn ra số hàng đúng layout.
import { describe, it, expect, vi, beforeEach } from 'vitest'

const frappePost = vi.fn()
vi.mock('./helpers', () => ({
  frappeGet: vi.fn(),
  frappePost: (...args: unknown[]) => frappePost(...args),
}))

import { previewRefImport, importRefData } from './importData'

describe('import wizard — số hàng thật + nhãn cột tiếng Việt', () => {
  beforeEach(() => frappePost.mockReset())

  it('preview: lấy source_row/label từ BE, không suy ra từ chỉ số dòng', async () => {
    frappePost.mockResolvedValue({
      doctype: 'AC Asset',
      total_rows: 2,
      valid_rows: 1,
      preview: [],
      fieldnames: ['asset_name', 'asset_category'],
      field_labels: { asset_name: 'Tên tài sản', asset_category: 'Danh mục tài sản' },
      errors: [{
        row: 2, source_row: 9, field: 'asset_category',
        label: 'Danh mục tài sản', message: 'không tồn tại', severity: 'error',
      }],
      warnings: [],
      cascade_count: 0,
    })

    const res = await previewRefImport('AC Asset', '/files/x.xlsx')
    expect(res.errors[0].sourceRow).toBe(9)
    expect(res.errors[0].label).toBe('Danh mục tài sản')
    expect(res.fieldLabels.asset_category).toBe('Danh mục tài sản')
  })

  it('preview: BE cũ thiếu source_row → suy ra theo layout template (5 hàng khung)', async () => {
    frappePost.mockResolvedValue({
      doctype: 'AC Department',
      total_rows: 1,
      valid_rows: 0,
      preview: [],
      fieldnames: ['department_name'],
      errors: [{ row: 3, field: 'department_name', message: 'trùng', severity: 'error' }],
      warnings: [],
    })

    const res = await previewRefImport('AC Department', '/files/x.xlsx')
    expect(res.errors[0].sourceRow).toBe(8)
    // Không có label → hiện fieldname còn hơn hiện rỗng.
    expect(res.errors[0].label).toBe('department_name')
    expect(res.fieldLabels).toEqual({})
  })

  it('import: dòng bị bỏ qua cũng mang số hàng thật + nhãn cột', async () => {
    frappePost.mockResolvedValue({
      total: 3, success: 1, failed: 0, skipped: 2,
      errors: [],
      skipped_rows: [
        {
          row: 1, source_row: 6, reason: 'pre_validate', field: 'department_name',
          label: 'Tên khoa/phòng', message: 'đã tồn tại trong hệ thống',
          severity: 'error',
        },
        {
          row: 2, source_row: 9, reason: 'cascade_parent_skipped',
          field: 'parent_department', label: 'Khoa cha',
          message: "Cha 'Khối Nội' đã bị bỏ qua → bỏ qua dòng này",
          severity: 'error',
        },
      ],
    })

    const res = await importRefData('AC Department', '/files/x.xlsx', 'skip_invalid')
    expect(res.skipped).toBe(2)
    expect(res.skippedRows.map(r => r.sourceRow)).toEqual([6, 9])
    expect(res.skippedRows.map(r => r.label)).toEqual(['Tên khoa/phòng', 'Khoa cha'])
    expect(res.skippedRows[1].reason).toBe('cascade_parent_skipped')
  })

  it('import: DocType cha+bảng con trả thêm số bản ghi CHA đã tạo', async () => {
    // "3/3 dòng nhập thành công" mà không nói tạo mấy MẪU là vô nghĩa với người
    // dùng — số dòng (hạng mục) khác số bản ghi (mẫu bảng kiểm).
    frappePost.mockResolvedValue({
      total: 3, success: 3, failed: 0, skipped: 0, groups_created: 2, errors: [],
    })
    const res = await importRefData('PM Checklist Template', '/files/x.xlsx')
    expect(res.groupsCreated).toBe(2)
  })

  it('import: DocType phẳng KHÔNG có số bản ghi cha ⇒ bỏ trống, không bịa 0', async () => {
    frappePost.mockResolvedValue({ total: 1, success: 1, failed: 0, skipped: 0, errors: [] })
    const res = await importRefData('AC Department', '/files/x.xlsx')
    expect(res.groupsCreated).toBeUndefined()
  })

  it('import: gửi skip_invalid=true khi người dùng chọn bỏ qua dòng lỗi/trùng', async () => {
    // Hằng thay vì literal: đây là THAM SỐ của endpoint import (loại dữ liệu cần
    // nhập), KHÔNG phải truy cập doctype `User` của Frappe — viết literal sẽ dính
    // guard tĩnh `userSource.guard.test.ts` một cách sai lệch.
    const USER_IMPORT_TYPE = 'User' as const
    frappePost.mockResolvedValue({ total: 0, success: 0, failed: 0 })
    await importRefData(USER_IMPORT_TYPE, '/files/x.xlsx', 'skip_invalid')
    expect(frappePost).toHaveBeenCalledWith(
      '/api/method/assetcore.api.import_data.import_ref_data',
      { doctype: USER_IMPORT_TYPE, file_url: '/files/x.xlsx', skip_invalid: true },
    )
  })
})
