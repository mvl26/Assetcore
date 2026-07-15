// Copyright (c) 2026, AssetCore Team — attachIncidentPhoto guard (Finding C, TDD)
//
// Sau khi siết Finding C: attachIncidentPhoto CHỈ echo `error`/`fields` khi body là
// Decision-B hợp lệ (success:false + code string); mọi shape khác (raw Frappe exc /
// thiếu code / success:true thiếu file_url) → message máy chủ chung, KHÔNG echo traceback.
import { it, expect, vi, beforeEach } from 'vitest'

const postSpy = vi.fn()
vi.mock('./axios', () => ({ default: { post: (...a: unknown[]) => postSpy(...a) } }))

import { attachIncidentPhoto } from './imm12'
import { ApiError, ErrorCode } from './errors'

const GENERIC = 'Có lỗi máy chủ, vui lòng thử lại.'
const resolveMessage = (message: unknown) => postSpy.mockResolvedValue({ data: { message } })
const file = () => new File(['xx'], 'hien-truong.jpg', { type: 'image/jpeg' })

beforeEach(() => postSpy.mockReset())

it('success → trả { file_url, file_name }', async () => {
  resolveMessage({ success: true, data: { file_url: '/private/files/s.jpg', file_name: 's.jpg' } })
  const res = await attachIncidentPhoto('INC-1', file())
  expect(res.file_url).toBe('/private/files/s.jpg')
})

it('Decision-B VALIDATION (fields.file) → ApiError giữ code + fields.file', async () => {
  resolveMessage({ success: false, code: 'VALIDATION', http_status: 200, error: 'Tối đa 5 ảnh', fields: { file: 'Tối đa 5 ảnh' } })
  let caught: ApiError | null = null
  try { await attachIncidentPhoto('INC-1', file()) } catch (e) { caught = e as ApiError }
  expect(caught!.code).toBe(ErrorCode.VALIDATION)
  expect(caught!.fields?.file).toBe('Tối đa 5 ảnh')
})

it('Finding C: raw exc (không có success) → generic, KHÔNG echo traceback', async () => {
  resolveMessage({ exc: '["Traceback (most recent call last):\\n  File \\"imm12.py\\"\\nKeyError: x\\n"]' })
  let caught: ApiError | null = null
  try { await attachIncidentPhoto('INC-1', file()) } catch (e) { caught = e as ApiError }
  expect(caught!.message).toBe(GENERIC)
  expect(caught!.message).not.toContain('Traceback')
  expect(caught!.code).toBe(ErrorCode.INTERNAL_ERROR)
})
