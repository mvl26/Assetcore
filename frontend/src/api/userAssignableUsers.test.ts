// Copyright (c) 2026, AssetCore Team — IMM-00 list_assignable_users contract guard
//
// Picker phân công (KTV sửa chữa…) lấy user AssetCore ĐỦ NĂNG LỰC từ BE
// `assetcore.api.user.list_assignable_users(context, search, limit)`. Test khoá:
//   1. dùng frappeGet (GET-read), endpoint KHỚP EXACT tên function BE.
//   2. params == signature BE (context, search, limit) — chống drift FE↔BE.
//   3. trả mảng đã unwrap (Promise<T>, KHÔNG ApiResponse wrapper).

import { describe, it, expect, vi, beforeEach } from 'vitest'

const getSpy = vi.fn()
const postSpy = vi.fn()
vi.mock('@/api/helpers', () => ({
  frappeGet: (endpoint: string, params?: Record<string, unknown>) => getSpy(endpoint, params),
  frappePost: (endpoint: string, body?: Record<string, unknown>) => postSpy(endpoint, body),
}))

import { listAssignableUsers } from '@/api/user'

const ENDPOINT = '/api/method/assetcore.api.user.list_assignable_users'

describe('user.listAssignableUsers — capability-scoped picker contract', () => {
  beforeEach(() => {
    getSpy.mockReset()
    postSpy.mockReset()
    getSpy.mockResolvedValue([
      { name: 'ktv@hospital.vn', full_name: 'KTV A', email: 'ktv@hospital.vn' },
    ])
  })

  it('dùng frappeGet, endpoint KHỚP EXACT list_assignable_users', async () => {
    await listAssignableUsers('repair', 'ktv', 20)
    expect(getSpy).toHaveBeenCalledTimes(1)
    expect(postSpy).not.toHaveBeenCalled()
    expect(getSpy).toHaveBeenCalledWith(ENDPOINT, expect.any(Object))
  })

  it('params == signature BE (context, search, limit)', async () => {
    await listAssignableUsers('repair', 'ktv', 50)
    const [, params] = getSpy.mock.calls[0]
    expect(params).toEqual({ context: 'repair', search: 'ktv', limit: 50 })
  })

  it('default search="" + limit=20 khi không truyền', async () => {
    await listAssignableUsers('repair')
    const [, params] = getSpy.mock.calls[0]
    expect(params).toEqual({ context: 'repair', search: '', limit: 20 })
  })

  it('trả mảng user đã unwrap', async () => {
    const rows = await listAssignableUsers('repair')
    expect(rows).toEqual([
      { name: 'ktv@hospital.vn', full_name: 'KTV A', email: 'ktv@hospital.vn' },
    ])
  })
})
