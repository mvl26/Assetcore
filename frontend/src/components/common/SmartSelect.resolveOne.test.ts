// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 vòng 2 · BUG-PM-1) — SmartSelect single-item label resolution.
//
// Khi props.modelValue truthy (vd prefill QR khoá) mà getItemById trả undefined
// (asset không nằm trong trang đầu search_link với danh mục lớn) → SmartSelect
// PHẢI tự gọi store.resolveOne(doctype, modelValue) 1 lần để resolve tên đọc-được
// → nút khoá hiển thị TÊN thiết bị, KHÔNG raw mã xám đứng một mình.
//
//   (a) modelValue set + cache RỖNG/thiếu id → gọi resolveOne → name hiển thị.
//   (b) cache ĐÃ chứa id → KHÔNG gọi resolveOne (spy 0 call) → name từ cache.
//   (c) resolveOne reject/null → KHÔNG throw → render raw modelValue (fallback lưới an toàn).
//   (d) idempotent: thay đổi modelValue rồi đặt lại → guard không gọi lặp cùng id.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SmartSelect from './SmartSelect.vue'
import { useMasterDataStore, type MasterItem } from '@/stores/masterData'

// fetchDoctype no-op để đường ensureLoaded() không chạm transport thật.
function stubFetch(store: ReturnType<typeof useMasterDataStore>) {
  vi.spyOn(store, 'fetchDoctype').mockResolvedValue([] as MasterItem[])
}

describe('SmartSelect — single-item resolveOne (BUG-PM-1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('(a) modelValue set + cache thiếu id → gọi resolveOne → hiển thị TÊN, không raw mã xám', async () => {
    const store = useMasterDataStore()
    stubFetch(store)
    // getItemById trả undefined ban đầu; resolveOne upsert rồi getItemById thấy.
    const resolveSpy = vi.spyOn(store, 'resolveOne').mockImplementation(async (dt, id) => {
      const item: MasterItem = { id, name: 'Máy thở Dräger Evita V500', description: '' }
      store.cache[dt as string] = store.cache[dt as string]
        ?? { items: [], loadedAt: 0, loading: false, promise: null }
      store.cache[dt as string].items.push(item)
      return item
    })

    const w = mount(SmartSelect, {
      props: { modelValue: 'TS-X', doctype: 'AC Asset', disabled: true },
    })
    await flushPromises()

    expect(resolveSpy).toHaveBeenCalledTimes(1)
    expect(resolveSpy).toHaveBeenCalledWith('AC Asset', 'TS-X')
    // Nút khoá hiển thị TÊN đọc-được.
    expect(w.text()).toContain('Máy thở Dräger Evita V500')
    // Trigger button vẫn disabled.
    expect(w.get('button[type="button"]').attributes('disabled')).toBeDefined()
  })

  it('(b) cache ĐÃ chứa id → KHÔNG gọi resolveOne (0 call) → name từ cache', async () => {
    const store = useMasterDataStore()
    stubFetch(store)
    store.cache['AC Asset'] = {
      items: [{ id: 'TS-X', name: 'Đã có trong cache', description: '' }],
      loadedAt: Date.now(), loading: false, promise: null,
    }
    const resolveSpy = vi.spyOn(store, 'resolveOne')

    const w = mount(SmartSelect, {
      props: { modelValue: 'TS-X', doctype: 'AC Asset', disabled: true },
    })
    await flushPromises()

    expect(resolveSpy).not.toHaveBeenCalled()
    expect(w.text()).toContain('Đã có trong cache')
  })

  it('(c) resolveOne reject → KHÔNG throw, fallback render raw modelValue (lưới an toàn)', async () => {
    const store = useMasterDataStore()
    stubFetch(store)
    vi.spyOn(store, 'resolveOne').mockRejectedValue(new Error('403'))

    let mounted: ReturnType<typeof mount> | null = null
    await expect(
      (async () => {
        mounted = mount(SmartSelect, {
          props: { modelValue: 'TS-X', doctype: 'AC Asset', disabled: true },
        })
        await flushPromises()
      })(),
    ).resolves.not.toThrow()

    // Fallback line 224-226: raw modelValue vẫn render (trang không vỡ).
    expect(mounted!.text()).toContain('TS-X')
  })

  it('(c2) resolveOne trả null (item bị xóa) → fallback raw modelValue, không vỡ', async () => {
    const store = useMasterDataStore()
    stubFetch(store)
    vi.spyOn(store, 'resolveOne').mockResolvedValue(null)

    const w = mount(SmartSelect, {
      props: { modelValue: 'TS-X', doctype: 'AC Asset', disabled: true },
    })
    await flushPromises()
    expect(w.text()).toContain('TS-X')
  })

  it('(d) guard: KHÔNG gọi resolveOne lặp cùng id sau nhiều flush', async () => {
    const store = useMasterDataStore()
    stubFetch(store)
    const resolveSpy = vi.spyOn(store, 'resolveOne').mockResolvedValue(null)

    const w = mount(SmartSelect, {
      props: { modelValue: 'TS-X', doctype: 'AC Asset', disabled: true },
    })
    await flushPromises()
    // Force thêm reactivity cycle với cùng modelValue.
    await w.setProps({ modelValue: 'TS-X' })
    await flushPromises()

    expect(resolveSpy).toHaveBeenCalledTimes(1)
  })

  it('(e) modelValue rỗng → KHÔNG gọi resolveOne', async () => {
    const store = useMasterDataStore()
    stubFetch(store)
    const resolveSpy = vi.spyOn(store, 'resolveOne')

    mount(SmartSelect, { props: { modelValue: '', doctype: 'AC Asset' } })
    await flushPromises()
    expect(resolveSpy).not.toHaveBeenCalled()
  })
})
