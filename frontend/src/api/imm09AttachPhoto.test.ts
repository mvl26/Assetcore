// Copyright (c) 2026, AssetCore Team — attachRepairChecklistPhoto (IMM-09, TDD)
//
// Acceptance:
//   • multipart contract: FormData mang work_order_name + checklist_item_idx + file (đúng
//     field BE api/imm09.attach_repair_checklist_photo mong đợi).
//   • success → trả { file_url, file_name, checklist_item_idx }.
//   • Decision-B lỗi { success:false, code:'VALIDATION', fields:{file} } → ApiError giữ code
//     + fields.file (thông điệp VN curate — echo để render inline).
//   • Finding C: body KHÔNG phải Decision-B (raw Frappe exc / success:false thiếu code /
//     success:true thiếu file_url) → message máy chủ chung, TUYỆT ĐỐI KHÔNG echo exc/traceback.
import { describe, it, expect, vi, beforeEach } from 'vitest'

const postSpy = vi.fn()
vi.mock('./axios', () => ({ default: { post: (...a: unknown[]) => postSpy(...a) } }))

import { attachRepairChecklistPhoto } from './imm09'
import { ApiError, ErrorCode } from './errors'

const GENERIC = 'Có lỗi máy chủ, vui lòng thử lại.'
const TRACEBACK =
  '["Traceback (most recent call last):\\n  File \\"imm09.py\\", line 78, in attach_repair_checklist_photo\\nValueError: bad\\n"]'

function resolveMessage(message: unknown) {
  postSpy.mockResolvedValue({ data: { message } })
}

const file = () => new File(['xx'], 'bang-chung.jpg', { type: 'image/jpeg' })

beforeEach(() => postSpy.mockReset())

describe('attachRepairChecklistPhoto — contract multipart + success', () => {
  it('gửi FormData đúng field (work_order_name, checklist_item_idx, file)', async () => {
    resolveMessage({ success: true, data: { file_url: '/private/files/a.jpg', file_name: 'a.jpg', checklist_item_idx: 2 } })
    const f = file()
    const res = await attachRepairChecklistPhoto('WO-RP-2026-00099', 2, f)

    expect(postSpy).toHaveBeenCalledTimes(1)
    const [url, form] = postSpy.mock.calls[0] as [string, FormData]
    expect(url).toContain('assetcore.api.imm09.attach_repair_checklist_photo')
    expect(form).toBeInstanceOf(FormData)
    expect(form.get('work_order_name')).toBe('WO-RP-2026-00099')
    expect(form.get('checklist_item_idx')).toBe('2')      // int → string ở boundary
    expect(form.get('file')).toBeInstanceOf(File)
    expect(res.file_url).toBe('/private/files/a.jpg')
  })
})

describe('attachRepairChecklistPhoto — Decision-B lỗi VALIDATION (echo curate)', () => {
  it('success:false + code + fields.file → ApiError giữ code + fields.file', async () => {
    resolveMessage({
      success: false, code: 'VALIDATION', http_status: 200,
      error: 'Chỉ chấp nhận ảnh JPG hoặc PNG',
      fields: { file: 'Chỉ chấp nhận ảnh JPG hoặc PNG' },
    })
    let caught: ApiError | null = null
    try { await attachRepairChecklistPhoto('WO-1', 1, file()) } catch (e) { caught = e as ApiError }
    expect(caught).toBeInstanceOf(ApiError)
    expect(caught!.code).toBe(ErrorCode.VALIDATION)
    expect(caught!.fields?.file).toBe('Chỉ chấp nhận ảnh JPG hoặc PNG')
  })
})

describe('attachRepairChecklistPhoto — Finding C: KHÔNG echo body lỗi thô', () => {
  it('raw Frappe exc (không có success) → message VN chung, KHÔNG chứa traceback', async () => {
    resolveMessage({ exc: TRACEBACK, exception: 'ValueError: bad' })
    let caught: ApiError | null = null
    try { await attachRepairChecklistPhoto('WO-1', 1, file()) } catch (e) { caught = e as ApiError }
    expect(caught!.message).toBe(GENERIC)
    expect(caught!.message).not.toContain('Traceback')
    expect(caught!.message).not.toContain('attach_repair_checklist_photo')
    expect(caught!.code).toBe(ErrorCode.INTERNAL_ERROR)
  })

  it('success:false NHƯNG thiếu code (malformed) → generic, KHÔNG echo error thô', async () => {
    resolveMessage({ success: false, error: 'RuntimeError: leak nội bộ tại dòng 42' })
    let caught: ApiError | null = null
    try { await attachRepairChecklistPhoto('WO-1', 1, file()) } catch (e) { caught = e as ApiError }
    expect(caught!.message).toBe(GENERIC)
    expect(caught!.message).not.toContain('RuntimeError')
  })

  it('success:true nhưng thiếu file_url → generic (không coi là thành công)', async () => {
    resolveMessage({ success: true, data: {} })
    let caught: ApiError | null = null
    try { await attachRepairChecklistPhoto('WO-1', 1, file()) } catch (e) { caught = e as ApiError }
    expect(caught!.message).toBe(GENERIC)
  })
})
