// TDD — Vòng 13 IMM-00 list-scope SEARCH-LIKE-ESCAPE / TC-FE-1 (parity-only).
//
// Hợp đồng: BE là ĐIỂM ESCAPE DUY NHẤT cho LIKE-metachar (`%`/`_`/`\`) trong
// tham số `search` của `list_assets`. FE PHẢI gửi NGUYÊN VĂN chuỗi user gõ
// (chỉ `.trim()` khoảng trắng 2 đầu) — KHÔNG tự escape/strip/biến đổi metachar.
// Nếu FE escape thì BE escape lần 2 → double-escape → tìm kiếm sai.
//
// Test này khẳng định:
//  (1) `filters.search` user gõ ('_' / '%' / '\' / 'AC_001' …) đi tới param
//      `search` của fetchList NGUYÊN VĂN (không pre-mangle, không escape).
//  (2) Chip search hiển thị nguyên văn user-input — render KHÔNG leak/biến đổi
//      metachar (chips dùng `"..."` bao quanh chuỗi trim).
//  (3) Substring hợp lệ ('vent', '35304' GMDN) vẫn truyền y nguyên (no-regress).
//  (4) Chỉ `.trim()` được áp (khoảng trắng 2 đầu) — đây KHÔNG phải escape.
//
// Không đổi UX/code — chỉ thêm test parity (BE round 13 mới là điểm escape).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

// Mutable route mock — set query.search để mô phỏng user gõ vào ô tìm kiếm.
// applyQueryToFilters() đọc route.query.search → filters.search → cleanParams.
const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

// Spy fetchList — bắt ĐÚNG chuỗi search FE gửi xuống store → api → BE.
const fetchListSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    assets: [],
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    loading: false,
    error: null,
    fetchList: fetchListSpy,
  }),
  useRefDataStore: () => ({
    categories: [], departments: [], locations: [],
    fetchAll: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/composables/useImportWizard', () => ({
  useImportWizard: () => ({ open: vi.fn(), doExport: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string | readonly string[]) =>
    Array.isArray(c) ? c.includes('asset.print') : c === 'asset.print' }),
}))

import AssetListView from './AssetListView.vue'

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  ImportWizardModal: true, RouterLink: true,
}

/** Mount với route.query.search = <raw> và trả về chuỗi search mà fetchList nhận. */
async function searchSentFor(raw: string): Promise<string | undefined> {
  routeQuery.value = { search: raw }
  mount(AssetListView, { global: { stubs } })
  await flushPromises()
  expect(fetchListSpy).toHaveBeenCalled()
  const arg = fetchListSpy.mock.calls[0][0]
  return arg?.search as string | undefined
}

describe('AssetListView — search param parity (TC-FE-1, BE là điểm escape duy nhất)', () => {
  beforeEach(() => {
    fetchListSpy.mockClear()
    routeQuery.value = {}
  })

  // ── (1) Metachar truyền NGUYÊN VĂN — FE KHÔNG escape/strip ─────────────────
  it('gửi "_" NGUYÊN VĂN (KHÔNG escape thành "\\_") — BE mới escape', async () => {
    expect(await searchSentFor('_')).toBe('_')
  })

  it('gửi "%" NGUYÊN VĂN (KHÔNG escape thành "\\%")', async () => {
    expect(await searchSentFor('%')).toBe('%')
  })

  it('gửi "\\" (1 backslash) NGUYÊN VĂN (KHÔNG nhân đôi / không strip)', async () => {
    expect(await searchSentFor('\\')).toBe('\\')
  })

  it('gửi "AC_001" NGUYÊN VĂN — "_" giữa chuỗi KHÔNG bị FE escape', async () => {
    expect(await searchSentFor('AC_001')).toBe('AC_001')
  })

  it('gửi "%%%%%" (multi-%) NGUYÊN VĂN — FE không strip/collapse', async () => {
    expect(await searchSentFor('%%%%%')).toBe('%%%%%')
  })

  it('gửi chuỗi SQLi "x\' OR \'1\'=\'1" NGUYÊN VĂN (FE không sanitize — BE lo)', async () => {
    expect(await searchSentFor("x' OR '1'='1")).toBe("x' OR '1'='1")
  })

  // ── (2) No-regress substring hợp lệ ───────────────────────────────────────
  it('no-regress: "vent" truyền y nguyên', async () => {
    expect(await searchSentFor('vent')).toBe('vent')
  })

  it('no-regress: "35304" (GMDN) truyền y nguyên', async () => {
    expect(await searchSentFor('35304')).toBe('35304')
  })

  // ── (3) Chỉ `.trim()` khoảng trắng 2 đầu — KHÔNG phải escape ───────────────
  it('chỉ trim khoảng trắng 2 đầu, metachar bên trong giữ nguyên', async () => {
    expect(await searchSentFor('  AC_%  ')).toBe('AC_%')
  })

  it('search chỉ khoảng trắng → KHÔNG gửi param search (sau trim rỗng)', async () => {
    routeQuery.value = { search: '   ' }
    mount(AssetListView, { global: { stubs } })
    await flushPromises()
    // applyQueryToFilters chỉ set khi val truthy; '   ' truthy → filters.search='   ',
    // nhưng cleanParams chỉ thêm khi `.trim()` non-empty → search KHÔNG có trong params.
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.search).toBeUndefined()
  })
})

describe('AssetListView — chip search render parity (metachar không bị biến đổi)', () => {
  beforeEach(() => {
    fetchListSpy.mockClear()
    routeQuery.value = {}
  })

  // Chip dùng activeChips (exposed) — assert chuỗi user-input hiện nguyên văn
  // trong nhãn chip, không escape/strip metachar. Chip bọc `"..."` quanh trim.
  async function chipLabelFor(raw: string): Promise<string | undefined> {
    routeQuery.value = { search: raw }
    const wrapper = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    const chips = (wrapper.vm as unknown as {
      activeChips: { key: string; label: string }[]
    }).activeChips
    return chips.find(c => c.key === 'search')?.label
  }

  it('chip hiển thị "_" nguyên văn trong nhãn', async () => {
    expect(await chipLabelFor('_')).toBe('"_"')
  })

  it('chip hiển thị "%" nguyên văn trong nhãn', async () => {
    expect(await chipLabelFor('%')).toBe('"%"')
  })

  it('chip hiển thị "AC_001" nguyên văn — không escape "_"', async () => {
    expect(await chipLabelFor('AC_001')).toBe('"AC_001"')
  })

  it('chip hiển thị backslash nguyên văn — không nhân đôi', async () => {
    expect(await chipLabelFor('\\')).toBe('"\\"')
  })
})
