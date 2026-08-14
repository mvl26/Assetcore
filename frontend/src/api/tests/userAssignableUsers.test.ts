// Copyright (c) 2026, AssetCore Team — IMM-00 list_assignable_users contract guard
//
// Picker phân công (KTV sửa chữa…) lấy user AssetCore ĐỦ NĂNG LỰC từ BE
// `assetcore.api.user.list_assignable_users(context, search, limit)`. Test khoá:
//   1. dùng frappeGet (GET-read), endpoint KHỚP EXACT tên function BE.
//   2. params == signature BE (context, search, limit) — chống drift FE↔BE.
//   3. trả OBJECT đã unwrap `{items,total,truncated,limit}` (Promise<T>, KHÔNG
//      ApiResponse wrapper) — AC-CR-80: hết cắt IM LẶNG ở `limit`.
//   4. `truncated` là SỐ 0|1 (KHÔNG boolean — parity CR-01, chống crash codegen
//      Dart/Kotlin int-vs-bool).
//   5. tolerant reader (ADR-IMM00-ASSIGN-04): trong cửa sổ `gunicorn --preload`
//      chưa reload, BE cũ vẫn trả MẢNG TRẦN ⇒ FE phải bọc, KHÔNG để picker trắng.

import { describe, it, expect, vi, beforeEach } from 'vitest'

const getSpy = vi.fn()
const postSpy = vi.fn()
vi.mock('@/api/helpers', () => ({
  frappeGet: (endpoint: string, params?: Record<string, unknown>) => getSpy(endpoint, params),
  frappePost: (endpoint: string, body?: Record<string, unknown>) => postSpy(endpoint, body),
}))

import { listAssignableUsers, normalizeAssignableUserPage } from '@/api/user'

const ENDPOINT = '/api/method/assetcore.api.user.list_assignable_users'

const KTV = { name: 'ktv@hospital.vn', full_name: 'KTV A', email: 'ktv@hospital.vn' }

/** Shape ĐÍCH của BE sau AC-CR-80. */
function page(over: Record<string, unknown> = {}) {
  return { items: [KTV], total: 1, truncated: 0, limit: 20, ...over }
}

describe('user.listAssignableUsers — capability-scoped picker contract', () => {
  beforeEach(() => {
    getSpy.mockReset()
    postSpy.mockReset()
    getSpy.mockResolvedValue(page())
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

  it('trả OBJECT có .items (KHÔNG phải mảng trần)', async () => {
    const res = await listAssignableUsers('repair')
    expect(Array.isArray(res)).toBe(false)
    expect(res.items).toEqual([KTV])
    expect(res.total).toBe(1)
    expect(res.limit).toBe(20)
  })

  it('meta cắt đi qua nguyên vẹn: items 20 / total 47 / truncated 1', async () => {
    const items = Array.from({ length: 20 }, (_, i) => ({
      name: `u${i}@hospital.vn`, full_name: `Người ${i}`, email: `u${i}@hospital.vn`,
    }))
    getSpy.mockResolvedValue({ items, total: 47, truncated: 1, limit: 20 })
    const res = await listAssignableUsers('repair', '', 20)
    expect(res.items).toHaveLength(20)
    expect(res.total).toBe(47)
    expect(res.truncated).toBe(1)
  })

  it('`truncated` là SỐ 0|1 — KHÔNG boolean (parity CR-01)', async () => {
    getSpy.mockResolvedValue(page({ truncated: 1, total: 47 }))
    const res = await listAssignableUsers('repair')
    expect(typeof res.truncated).toBe('number')
    expect(typeof res.truncated).not.toBe('boolean')
    expect([0, 1]).toContain(res.truncated)
  })

  it('BE echo `limit` ĐÃ CLAMP → FE giữ nguyên, không tự suy lại', async () => {
    // client gửi 999, BE clamp còn 100 và echo lại 100.
    getSpy.mockResolvedValue(page({ limit: 100, total: 3 }))
    const res = await listAssignableUsers('repair', '', 999)
    expect(res.limit).toBe(100)
  })

  it('tolerant reader: BE CŨ trả mảng trần ⇒ bọc thành page, picker KHÔNG trắng', async () => {
    getSpy.mockResolvedValue([KTV, { ...KTV, name: 'ktv2@hospital.vn' }])
    const res = await listAssignableUsers('repair', '', 20)
    expect(res.items).toHaveLength(2)
    expect(res.total).toBe(2)
    expect(res.truncated).toBe(0)
    expect(res.limit).toBe(20)
  })
})

describe('normalizeAssignableUserPage — SSoT chuẩn hoá shape', () => {
  it('mảng trần ⇒ page truncated=0, total=len', () => {
    expect(normalizeAssignableUserPage([KTV], 20)).toEqual({
      items: [KTV], total: 1, truncated: 0, limit: 20,
    })
  })

  it('object đủ khoá ⇒ giữ nguyên', () => {
    expect(normalizeAssignableUserPage({ items: [KTV], total: 47, truncated: 1, limit: 20 }, 20))
      .toEqual({ items: [KTV], total: 47, truncated: 1, limit: 20 })
  })

  it('null/undefined ⇒ page rỗng, KHÔNG ném lỗi', () => {
    expect(normalizeAssignableUserPage(null, 20)).toEqual({ items: [], total: 0, truncated: 0, limit: 20 })
    expect(normalizeAssignableUserPage(undefined, 20)).toEqual({ items: [], total: 0, truncated: 0, limit: 20 })
  })
})
