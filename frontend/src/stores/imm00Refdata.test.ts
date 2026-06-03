// Copyright (c) 2026, AssetCore Team
// Refdata prefetch (useRefDataStore.fetchAll) phải fail-closed PER-ENDPOINT:
// một bảng tham chiếu bị 403 (vd AC Supplier khi persona thiếu read) CHỈ làm
// bảng đó rỗng — KHÔNG throw, KHÔNG kéo sập các bảng khác, KHÔNG blank trang.
// Bảo vệ guard Promise.allSettled trong stores/imm00.ts (Nhiệm vụ 2 2026-06-02).

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('@/api/imm00', () => ({
  listLocations: vi.fn(),
  listDepartments: vi.fn(),
  listAssetCategories: vi.fn(),
  listDeviceModels: vi.fn(),
  listSlaPolicies: vi.fn(),
  listSuppliers: vi.fn(),
}))

import * as api from '@/api/imm00'
import { useRefDataStore } from '@/stores/imm00'

const FORBIDDEN = new ApiError('Bạn không có quyền thực hiện hành động này.', {
  code: ErrorCode.FORBIDDEN,
  httpStatus: 403,
})

describe('useRefDataStore.fetchAll — fail-closed per-endpoint (allSettled)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(api.listLocations).mockResolvedValue([{ name: 'LOC-1' }] as never)
    vi.mocked(api.listDepartments).mockResolvedValue([{ name: 'DEPT-1' }] as never)
    vi.mocked(api.listAssetCategories).mockResolvedValue([{ name: 'CAT-1' }] as never)
    vi.mocked(api.listDeviceModels).mockResolvedValue({ items: [{ name: 'M-1' }] } as never)
    vi.mocked(api.listSlaPolicies).mockResolvedValue([{ name: 'SLA-1' }] as never)
  })

  it('listSuppliers 403 KHÔNG throw và KHÔNG làm rỗng các bảng còn lại', async () => {
    vi.mocked(api.listSuppliers).mockRejectedValue(FORBIDDEN)
    const store = useRefDataStore()
    await expect(store.fetchAll()).resolves.toBeUndefined()
    // Bảng bị 403 → rỗng (fail-closed), KHÔNG crash.
    expect(store.suppliers).toEqual([])
    // Các bảng khác vẫn nạp đầy đủ.
    expect(store.locations).toHaveLength(1)
    expect(store.departments).toHaveLength(1)
    expect(store.categories).toHaveLength(1)
    expect(store.deviceModels).toHaveLength(1)
    expect(store.slaPolicies).toHaveLength(1)
    expect(store.loading).toBe(false)
  })

  it('happy path: mọi bảng nạp đủ khi không có lỗi', async () => {
    vi.mocked(api.listSuppliers).mockResolvedValue({ items: [{ name: 'SUP-1' }] } as never)
    const store = useRefDataStore()
    await store.fetchAll()
    expect(store.suppliers).toHaveLength(1)
    expect(store.locations).toHaveLength(1)
  })
})
