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
import { frappeGet } from '@/api/helpers'

export interface MasterItem {
  id: string           // Primary key (name trong Frappe)
  name: string         // Label hiển thị
  description?: string // Thông tin phụ
}

type DocType =
  | 'AC Asset' | 'AC Department' | 'AC Location' | 'AC Supplier'
  | 'AC Asset Category' | 'IMM Device Model' | 'IMM Calibration Schedule'
  | 'Purchase Order' | 'AC Warehouse'
  | 'AC Spare Part Category' | 'AC Spare Part' | 'AC Vendor' | 'AC Purchase' | 'UOM' | 'AC UOM'
  | 'PM Checklist Template' | 'IMM Trainer'

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
        // search_link trả { success, data: [{ value, label, description }] }
        // frappeGet unwrap envelope → trả thẳng mảng data
        const rows = await frappeGet<Array<{ value: string; label: string; description?: string }>>(
          BASE, { doctype, query: '', page_length: opts.pageLength ?? DEFAULT_PAGE_LENGTH },
        )
        entry.items = (Array.isArray(rows) ? rows : []).map(r => ({ id: r.value, name: r.label || r.value, description: r.description }))
        entry.loadedAt = Date.now()
        return entry.items
      } finally {
        entry.loading = false
        entry.promise = null
      }
    })()
    return entry.promise
  }

  // ── Filtered fetch (cascade dropdowns) ──────────────────────────────────
  // Không cache chung theo doctype vì kết quả phụ thuộc filter. Cache theo
  // key = doctype + JSON(filters) để cascade vẫn instant khi lặp lại.
  const filteredCache = ref<Record<string, CacheEntry>>({})

  function _filteredEntry(key: string): CacheEntry {
    if (!filteredCache.value[key]) {
      filteredCache.value[key] = { items: [], loadedAt: 0, loading: false, promise: null }
    }
    return filteredCache.value[key]
  }

  async function fetchFiltered(
    doctype: DocType,
    filters: Record<string, unknown>,
    opts: { forceRefresh?: boolean; pageLength?: number } = {},
  ): Promise<MasterItem[]> {
    const key = `${doctype}::${JSON.stringify(filters)}`
    const entry = _filteredEntry(key)
    if (!opts.forceRefresh && _fresh(entry)) return entry.items
    if (entry.promise) return entry.promise

    entry.loading = true
    entry.promise = (async () => {
      try {
        const rows = await frappeGet<Array<{ value: string; label: string; description?: string }>>(
          BASE,
          {
            doctype,
            query: '',
            page_length: opts.pageLength ?? DEFAULT_PAGE_LENGTH,
            filters: JSON.stringify(filters),
          },
        )
        entry.items = (Array.isArray(rows) ? rows : []).map(r => ({ id: r.value, name: r.label || r.value, description: r.description }))
        entry.loadedAt = Date.now()
        return entry.items
      } finally {
        entry.loading = false
        entry.promise = null
      }
    })()
    return entry.promise
  }

  function getFilteredItems(doctype: DocType, filters: Record<string, unknown>): MasterItem[] {
    return _filteredEntry(`${doctype}::${JSON.stringify(filters)}`).items
  }

  function isLoadingFiltered(doctype: DocType, filters: Record<string, unknown>): boolean {
    return _filteredEntry(`${doctype}::${JSON.stringify(filters)}`).loading
  }

  function getItems(doctype: DocType): MasterItem[] {
    return _entry(doctype).items
  }

  function getItemById(doctype: DocType, id: string): MasterItem | undefined {
    return _entry(doctype).items.find(it => it.id === id)
  }

  // ── Single-item resolve (BUG-PM-1) ──────────────────────────────────────
  // Khi modelValue (vd asset prefill khoá QR) KHÔNG nằm trong trang đầu
  // search_link (danh mục > page_length) → getItemById trả undefined →
  // SmartSelect chỉ hiện raw mã. resolveOne fetch ĐƠN item perm-aware qua cùng
  // endpoint search_link (query = id) rồi UPSERT vào cache theo id để label
  // resolve được tên đọc-được.
  //
  // Hợp đồng:
  //   • Đã có id trong cache → trả ngay, KHÔNG fetch thêm.
  //   • UPSERT (không clear trang hiện có); KHÔNG đổi loadedAt của full-list
  //     (giữ cache trang hợp lệ); idempotent theo id.
  //   • Nuốt lỗi (reject/403/deleted/mạng) → trả null (no-regression).
  const resolvingIds = ref<Record<string, Promise<MasterItem | null>>>({})

  async function resolveOne(doctype: DocType, id: string): Promise<MasterItem | null> {
    if (!id) return null

    // Cache hit → không fetch (no extra network).
    const cached = getItemById(doctype, id)
    if (cached) return cached

    // De-dup: cùng (doctype,id) đang resolve → chờ cùng promise (idempotent).
    const dedupeKey = `${doctype}::${id}`
    const inflight = resolvingIds.value[dedupeKey]
    if (inflight) return inflight

    const p = (async (): Promise<MasterItem | null> => {
      try {
        const rows = await frappeGet<Array<{ value: string; label: string; description?: string }>>(
          BASE, { doctype, query: id, page_length: 5 },
        )
        const match = (Array.isArray(rows) ? rows : []).find(r => r.value === id)
        if (!match) return null
        const item: MasterItem = {
          id: match.value,
          name: match.label || match.value,
          description: match.description,
        }
        // UPSERT theo id — KHÔNG clear trang, KHÔNG đổi loadedAt của full-list.
        const entry = _entry(doctype)
        const idx = entry.items.findIndex(it => it.id === item.id)
        if (idx >= 0) entry.items[idx] = item
        else entry.items.push(item)
        return item
      } catch {
        // Item bị xóa / 403 / mạng lỗi → fail-safe, giữ hành vi cũ (raw modelValue).
        return null
      } finally {
        delete resolvingIds.value[dedupeKey]
      }
    })()

    resolvingIds.value[dedupeKey] = p
    return p
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
  // GỠ 2026-07-22: `fetchUsers` (search_link doctype=User) xổ toàn bộ user của
  // site. Chọn người → <ApproverSelect> (api.user.list_assignable_users);
  // đọc 1 user → api/user.ts::getAcUserBrief.

  return {
    cache,
    fetchDoctype,
    fetchAssets,
    fetchDepartments,
    fetchLocations,
    fetchSuppliers,
    fetchDeviceModels,
    fetchFiltered,
    getFilteredItems,
    isLoadingFiltered,
    getItems,
    getItemById,
    resolveOne,
    isLoading,
    invalidate,
  }
})
