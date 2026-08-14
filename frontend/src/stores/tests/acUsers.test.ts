// Copyright (c) 2026, AssetCore Team
//
// Nguồn user THỐNG NHẤT (2026-07-22): mọi chỗ đổi id → tên hiển thị phải lấy từ
// `api.user.list_users` (lọc base role AssetCore), KHÔNG qua
// `masterData.fetchDoctype('User')` / `frappe.client.get_list doctype=User` —
// lối đó xổ cả user ERPNext/CRM trên site dùng chung (dashboard 29 vs 4).

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/user', () => ({
  listAllUsers: vi.fn(),
  getAcUserBrief: vi.fn(),
}))

import { useAcUserStore } from '@/stores/acUsers'
import { listAllUsers, getAcUserBrief } from '@/api/user'

const listAllMock = vi.mocked(listAllUsers)
const briefMock = vi.mocked(getAcUserBrief)

/** 1 dòng user AssetCore tối thiểu (các field khác không ảnh hưởng nhãn). */
function row(name: string, full_name: string) {
  return { name, full_name, email: name, enabled: 1 } as never
}

describe('acUsers store — danh bạ user AssetCore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    listAllMock.mockResolvedValue([row('ktv@benhvien.vn', 'Nguyễn Văn A')])
    briefMock.mockResolvedValue({
      name: 'cu@old.vn', full_name: 'Trần Thị B', email: 'cu@old.vn',
      enabled: 0, is_ac_user: false,
    } as never)
  })

  it('prefetch lấy danh bạ từ list_users (không phải doctype User thô)', async () => {
    const store = useAcUserStore()
    await store.prefetch()

    expect(listAllMock).toHaveBeenCalledTimes(1)
    expect(store.label('ktv@benhvien.vn')).toBe('Nguyễn Văn A')
  })

  it('cache theo TTL — gọi prefetch lần 2 không bắn thêm request', async () => {
    const store = useAcUserStore()
    await store.prefetch()
    await store.prefetch()

    expect(listAllMock).toHaveBeenCalledTimes(1)
  })

  it('forceRefresh bỏ qua cache', async () => {
    const store = useAcUserStore()
    await store.prefetch()
    await store.prefetch({ forceRefresh: true })

    expect(listAllMock).toHaveBeenCalledTimes(2)
  })

  it('id rỗng → gạch ngang, không gọi API', () => {
    const store = useAcUserStore()

    expect(store.label('')).toBe('—')
    expect(store.label(null)).toBe('—')
    expect(briefMock).not.toHaveBeenCalled()
  })

  it('id ngoài danh bạ (user đã rời AssetCore) → resolve lẻ rồi hiện tên', async () => {
    const store = useAcUserStore()
    await store.prefetch()

    expect(store.label('cu@old.vn')).toBe('cu@old.vn') // lượt đầu: chưa có, trả id
    await vi.waitFor(() => expect(store.label('cu@old.vn')).toBe('Trần Thị B'))
    expect(briefMock).toHaveBeenCalledWith('cu@old.vn')
  })

  it('nhiều dòng cùng id chỉ resolve 1 lần (không bắn request trùng)', async () => {
    const store = useAcUserStore()
    store.label('cu@old.vn')
    store.label('cu@old.vn')
    store.label('cu@old.vn')

    await vi.waitFor(() => expect(store.label('cu@old.vn')).toBe('Trần Thị B'))
    expect(briefMock).toHaveBeenCalledTimes(1)
  })

  it('resolve lỗi → giữ id làm nhãn, không vỡ render', async () => {
    briefMock.mockRejectedValue(new Error('403'))
    const store = useAcUserStore()

    expect(store.label('la@ngoai.vn')).toBe('la@ngoai.vn')
    await vi.waitFor(() => expect(briefMock).toHaveBeenCalled())
    expect(store.label('la@ngoai.vn')).toBe('la@ngoai.vn')
  })
})
