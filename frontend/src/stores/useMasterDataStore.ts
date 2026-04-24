// Copyright (c) 2026, AssetCore Team
// Pinia store cache Master Data — giảm số lần gọi API cho các DocType ít thay đổi.
//
// Pattern:
//   1. Lần đầu gọi fetchX() → hit API → lưu vào state
//   2. Lần sau gọi fetchX() → nếu state đã có data → return ngay (không gọi API)
//   3. Gọi fetchX({ forceRefresh: true }) → bypass cache
//
// Cache TTL tùy chọn: sau N giây từ lần fetch cuối, tự động refresh kế tiếp.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/axios'

export interface MasterItem {
  id: string           // Primary key (name trong Frappe)
  name: string         // Label hiển thị
  description?: string // Thông tin phụ
}

type DocType =
  | 'AC Asset' | 'AC Department' | 'AC Location' | 'AC Supplier'
  | 'AC Asset Category' | 'IMM Device Model' | 'IMM Calibration Schedule'
  | 'Purchase Order' | 'User' | 'AC Warehouse'
  | 'AC Spare Part Category' | 'AC Vendor' | 'AC Purchase' | 'UOM' | 'AC UOM'

interface CacheEntry {
  items: MasterItem[]
  loadedAt: number
  loading: boolean
  promise: Promise<MasterItem[]> | null
}

const CACHE_TTL_MS = 5 * 60 * 1000  // 5 phút — master data đổi hiếm nên TTL vừa đủ
const DEFAULT_PAGE_LENGTH = 500     // đủ rộng cho dropdown — vượt mức này cần autocomplete

const BASE = '/api/method/assetcore.api.imm04.search_link'

export const useMasterDataStore = defineStore('masterData', () => {
  // Key = DocType, value = CacheEntry
  const cache = ref<Record<string, CacheEntry>>({})

  function _entry(doctype: DocType): CacheEntry {
    if (!cache.value[doctype]) {
      cache.value[doctype] = { items: [], loadedAt: 0, loading: false, promise: null }
    }
    return cache.value[doctype]
  }

  function _fresh(entry: CacheEntry): boolean {
    return entry.items.length > 0 && (Date.now() - entry.loadedAt) < CACHE_TTL_MS
  }

  async function fetchDoctype(
    doctype: DocType,
    opts: { forceRefresh?: boolean; pageLength?: number } = {},
  ): Promise<MasterItem[]> {
    const entry = _entry(doctype)

    // Cache hit
    if (!opts.forceRefresh && _fresh(entry)) return entry.items

    // Đang fetch song song → chờ cùng promise (tránh race-condition N calls cùng doctype)
    if (entry.promise) return entry.promise

    entry.loading = true
    entry.promise = (async () => {
      try {
        const res = await api.get(BASE, {
          params: { doctype, query: '', page_length: opts.pageLength ?? DEFAULT_PAGE_LENGTH },
        })
        const envelope = res.data?.message ?? res.data
        const rows: Array<{ value: string; label: string; description?: string }> =
          envelope?.success && Array.isArray(envelope.data) ? envelope.data : []
        entry.items = rows.map(r => ({ id: r.value, name: r.label || r.value, description: r.description }))
        entry.loadedAt = Date.now()
        return entry.items
      } finally {
        entry.loading = false
        entry.promise = null
      }
    })()
    return entry.promise
  }

  function getItems(doctype: DocType): MasterItem[] {
    return _entry(doctype).items
  }

  function getItemById(doctype: DocType, id: string): MasterItem | undefined {
    return _entry(doctype).items.find(it => it.id === id)
  }

  function isLoading(doctype: DocType): boolean {
    return _entry(doctype).loading
  }

  function invalidate(doctype?: DocType) {
    if (doctype) {
      delete cache.value[doctype]
    } else {
      cache.value = {}
    }
  }

  // Convenience methods cho các DocType phổ biến
  const fetchAssets = (opts?: { forceRefresh?: boolean }) => fetchDoctype('AC Asset', opts)
  const fetchDepartments = (opts?: { forceRefresh?: boolean }) => fetchDoctype('AC Department', opts)
  const fetchLocations = (opts?: { forceRefresh?: boolean }) => fetchDoctype('AC Location', opts)
  const fetchSuppliers = (opts?: { forceRefresh?: boolean }) => fetchDoctype('AC Supplier', opts)
  const fetchDeviceModels = (opts?: { forceRefresh?: boolean }) => fetchDoctype('IMM Device Model', opts)
  const fetchUsers = (opts?: { forceRefresh?: boolean }) => fetchDoctype('User', opts)

  return {
    cache,
    fetchDoctype,
    fetchAssets,
    fetchDepartments,
    fetchLocations,
    fetchSuppliers,
    fetchDeviceModels,
    fetchUsers,
    getItems,
    getItemById,
    isLoading,
    invalidate,
  }
})
