// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 vòng 2 · BUG-PM-1) — masterData.resolveOne single-item resolve.
//
// Root cause (parity 4 create-view khoá QR): SmartSelect resolve label qua
// store.getItemById('AC Asset', modelValue). Với danh mục lớn (>page_length)
// asset prefill KHÔNG nằm trong trang đầu search_link → selectedItem=null →
// SmartSelect chỉ hiện raw mã xám. FIX: store.resolveOne(doctype, id) fetch ĐƠN
// item perm-aware qua search_link (query=id) rồi UPSERT vào cache theo id.
//
// Hợp đồng (test khẳng định):
//   • TC-SS-RESOLVE-01: cache rỗng → resolveOne fetch 1 lần → item.name có trong cache.
//   • TC-SS-RESOLVE-02: id ĐÃ trong cache → resolveOne KHÔNG fetch (frappeGet 0 call).
//   • TC-SS-RESOLVE-03: reject (403/deleted/mạng) → KHÔNG throw → trả null, cache nguyên.
//   • TC-SS-RESOLVE-04: idempotent — gọi 2 lần cùng id KHÔNG nhân đôi item,
//     KHÔNG reset loadedAt của full-list (không vô hiệu cache trang).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/helpers', () => ({
  frappeGet: vi.fn(),
  frappePost: vi.fn(),
}))
import { frappeGet } from '@/api/helpers'
import { useMasterDataStore } from '@/stores/masterData'

const SEARCH_LINK_ENDPOINT = '/api/method/assetcore.api.imm04.search_link'

describe('masterData.resolveOne (BUG-PM-1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('TC-SS-RESOLVE-01: cache rỗng → fetch 1 lần → trả item, name vào cache', async () => {
    vi.mocked(frappeGet).mockResolvedValue([
      { value: 'TS-X', label: 'Máy thở Dräger Evita V500', description: 'AC-CODE-001' },
    ] as never)
    const store = useMasterDataStore()

    expect(store.getItemById('AC Asset', 'TS-X')).toBeUndefined()
    const item = await store.resolveOne('AC Asset', 'TS-X')

    expect(vi.mocked(frappeGet)).toHaveBeenCalledTimes(1)
    const [endpoint, params] = vi.mocked(frappeGet).mock.calls[0]
    expect(endpoint).toBe(SEARCH_LINK_ENDPOINT)
    expect((params as Record<string, unknown>).doctype).toBe('AC Asset')
    // query phải mang đúng id để BE resolve LIKE/exact theo name.
    expect((params as Record<string, unknown>).query).toBe('TS-X')

    expect(item).not.toBeNull()
    expect(item!.id).toBe('TS-X')
    expect(item!.name).toBe('Máy thở Dräger Evita V500')
    // Upsert vào cache → getItemById tìm thấy tên đọc-được.
    expect(store.getItemById('AC Asset', 'TS-X')?.name).toBe('Máy thở Dräger Evita V500')
  })

  it('TC-SS-RESOLVE-01b: nhiều row trả về → chỉ upsert đúng id khớp', async () => {
    vi.mocked(frappeGet).mockResolvedValue([
      { value: 'TS-X-OTHER', label: 'Thiết bị khác', description: '' },
      { value: 'TS-X', label: 'Máy đúng', description: '' },
    ] as never)
    const store = useMasterDataStore()

    const item = await store.resolveOne('AC Asset', 'TS-X')
    expect(item!.id).toBe('TS-X')
    expect(item!.name).toBe('Máy đúng')
    // Item không khớp id KHÔNG được trả về (dù có thể được upsert cache).
    expect(store.getItemById('AC Asset', 'TS-X')?.name).toBe('Máy đúng')
  })

  it('TC-SS-RESOLVE-02: id ĐÃ trong cache → KHÔNG fetch (0 call)', async () => {
    const store = useMasterDataStore()
    // Seed cache trực tiếp (giả lập trang đầu đã chứa id).
    store.cache['AC Asset'] = {
      items: [{ id: 'TS-X', name: 'Tên đã có', description: '' }],
      loadedAt: Date.now(), loading: false, promise: null,
    }

    const item = await store.resolveOne('AC Asset', 'TS-X')
    expect(vi.mocked(frappeGet)).not.toHaveBeenCalled()
    expect(item!.name).toBe('Tên đã có')
  })

  it('TC-SS-RESOLVE-03: reject (403/deleted/mạng) → KHÔNG throw, trả null, cache nguyên', async () => {
    vi.mocked(frappeGet).mockRejectedValue(new Error('403 FORBIDDEN'))
    const store = useMasterDataStore()
    // Cache trang hiện có (KHÔNG được mất khi resolveOne fail).
    store.cache['AC Asset'] = {
      items: [{ id: 'TS-A', name: 'Asset A', description: '' }],
      loadedAt: 123, loading: false, promise: null,
    }

    let item: unknown = 'unset'
    await expect(
      (async () => { item = await store.resolveOne('AC Asset', 'TS-X') })(),
    ).resolves.not.toThrow()

    expect(item).toBeNull()
    // No-regression: cache trang + loadedAt nguyên vẹn.
    expect(store.cache['AC Asset'].items).toEqual([{ id: 'TS-A', name: 'Asset A', description: '' }])
    expect(store.cache['AC Asset'].loadedAt).toBe(123)
  })

  it('TC-SS-RESOLVE-03b: BE trả rỗng (item bị xóa) → trả null, không thêm rác', async () => {
    vi.mocked(frappeGet).mockResolvedValue([] as never)
    const store = useMasterDataStore()
    const item = await store.resolveOne('AC Asset', 'TS-GONE')
    expect(item).toBeNull()
    expect(store.getItemById('AC Asset', 'TS-GONE')).toBeUndefined()
  })

  it('TC-SS-RESOLVE-04: idempotent — gọi 2 lần KHÔNG nhân đôi, loadedAt full-list không reset', async () => {
    const store = useMasterDataStore()
    // Trang đầy đủ đã load (loadedAt cụ thể) NHƯNG không chứa TS-X.
    store.cache['AC Asset'] = {
      items: [{ id: 'TS-A', name: 'Asset A', description: '' }],
      loadedAt: 999, loading: false, promise: null,
    }
    vi.mocked(frappeGet).mockResolvedValue([
      { value: 'TS-X', label: 'Máy X', description: '' },
    ] as never)

    await store.resolveOne('AC Asset', 'TS-X')
    await store.resolveOne('AC Asset', 'TS-X')

    // Lần 2 thấy id ĐÃ có sau lần 1 → KHÔNG fetch lại (tổng 1 call).
    expect(vi.mocked(frappeGet)).toHaveBeenCalledTimes(1)
    // KHÔNG nhân đôi item TS-X.
    const xs = store.cache['AC Asset'].items.filter(i => i.id === 'TS-X')
    expect(xs).toHaveLength(1)
    // loadedAt của full-list KHÔNG bị reset (không vô hiệu cache trang).
    expect(store.cache['AC Asset'].loadedAt).toBe(999)
    // Trang cũ vẫn còn.
    expect(store.getItemById('AC Asset', 'TS-A')?.name).toBe('Asset A')
  })
})
