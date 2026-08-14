// Copyright (c) 2026, AssetCore Team — axios interceptor 5xx mapping (Finding C, TDD)
//
// Finding C (2026-07-09, TOÀN CỤC): khi BE trả HTTP 500 (KHÔNG phải envelope Decision-B),
// interceptor CŨ lấy dòng cuối traceback Python (`data.exc`) ghép vào message → rò
// thông tin nội bộ ('Lỗi máy chủ nội bộ — ["Traceback (most recent call last)...') +
// gây hoảng người dùng cuối. Interceptor MỚI:
//   • Mọi 5xx → ApiError code INTERNAL_ERROR + message VN chung 'Có lỗi máy chủ, vui lòng thử lại.'
//   • TUYỆT ĐỐI KHÔNG chứa 'Traceback' / 'File ' / tên hàm / exc / exception ra message hiển thị.
//   • Áp cho MỌI endpoint (post + get qua frappeGet) — không riêng 1 module.
import { describe, it, expect, vi, beforeEach } from 'vitest'

// navigation utils chạm window.location → stub để import axios không nổ trong jsdom.
vi.mock('@/utils/navigation', () => ({
  loginPath: (p?: string) => `/login?next=${p ?? ''}`,
  isOnLoginPage: () => false,
}))

import api from '@/api/axios'
import { frappeGet } from '@/api/helpers'
import { ApiError, ErrorCode } from '@/api/errors'

const GENERIC = 'Có lỗi máy chủ, vui lòng thử lại.'

// Body 500 kiểu Frappe: `exc` là chuỗi JSON-array traceback (đúng như bug report —
// findLast(Boolean) cũ trả nguyên chuỗi vì không có newline THẬT trong 1 dòng),
// kèm biến thể có newline thật để chắc chắn cả 2 nhánh đều không leak.
const TRACEBACK_EXC =
  '["Traceback (most recent call last):\\n  File \\"/home/miyano/frappe-bench/apps/assetcore/assetcore/api/imm09.py\\", line 78, in attach_repair_checklist_photo\\n    idx = int(checklist_item_idx)\\nValueError: invalid literal for int()\\n"]'

function status5xxAdapter(status: number, data: Record<string, unknown>) {
  return () =>
    Promise.reject({
      config: {},
      response: { status, data, headers: {}, config: {} },
    })
}

function noLeak(msg: string) {
  expect(msg).toBe(GENERIC)
  expect(msg).not.toContain('Traceback')
  expect(msg).not.toContain('File ')
  expect(msg).not.toContain('attach_repair_checklist_photo') // tên hàm
  expect(msg).not.toContain('ValueError')
  expect(msg).not.toContain('imm09.py')
  expect(msg.toLowerCase()).not.toContain('exception')
}

describe('axios interceptor — 500 traceback KHÔNG rò ra UI (Finding C)', () => {
  beforeEach(() => { api.defaults.adapter = undefined })

  it('500 body có exc=traceback → message VN chung, KHÔNG echo stack', async () => {
    api.defaults.adapter = status5xxAdapter(500, {
      exc_type: 'ValueError',
      exc: TRACEBACK_EXC,
      exception: 'ValueError: invalid literal for int()',
      _server_messages: '[]',
      message: 'Internal Server Error',
    })
    let caught: ApiError | null = null
    try {
      await api.post('/api/method/assetcore.api.imm09.attach_repair_checklist_photo', {})
    } catch (e) { caught = e as ApiError }
    expect(caught).toBeInstanceOf(ApiError)
    expect(caught!.code).toBe(ErrorCode.INTERNAL_ERROR)
    expect(caught!.httpStatus).toBe(500)
    noLeak(caught!.message)
  })

  it('500 với exc = newline THẬT (multi-line) vẫn KHÔNG leak dòng cuối', async () => {
    api.defaults.adapter = status5xxAdapter(500, {
      exc: 'Traceback (most recent call last):\n  File "x.py", line 1\nKeyError: \'secret\'\n',
    })
    let caught: ApiError | null = null
    try {
      await api.post('/api/method/assetcore.api.imm12.attach_incident_photo', {})
    } catch (e) { caught = e as ApiError }
    expect(caught!.message).toBe(GENERIC)
    expect(caught!.message).not.toContain('KeyError')
    expect(caught!.message).not.toContain('secret')
  })

  it('TOÀN CỤC: 500 qua frappeGet (endpoint bất kỳ) cũng ra message VN chung', async () => {
    api.defaults.adapter = status5xxAdapter(500, { exc: TRACEBACK_EXC })
    let caught: ApiError | null = null
    try {
      await frappeGet('/api/method/assetcore.api.imm08.list_pm_work_orders')
    } catch (e) { caught = e as ApiError }
    expect(caught).toBeInstanceOf(ApiError)
    noLeak(caught!.message)
  })

  it('502/503 (5xx khác) cũng → message VN chung, không passthrough data.message HTML', async () => {
    for (const status of [502, 503]) {
      api.defaults.adapter = status5xxAdapter(status, { message: '<html>Bad Gateway</html>' })
      let caught: ApiError | null = null
      try {
        await api.post('/api/method/assetcore.api.imm09.get_repair_work_order', {})
      } catch (e) { caught = e as ApiError }
      expect(caught!.message).toBe(GENERIC)
      expect(caught!.message).not.toContain('<html>')
      expect(caught!.code).toBe(ErrorCode.INTERNAL_ERROR)
    }
  })
})
