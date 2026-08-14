// TDD — Sidebar D7 gọn (ADR-IMM00-CMDK D7). TC-CMDK-16.
// THUẦN THỊ GIÁC: collapse/pin KHÔNG đổi itemVisible output (RBAC bất biến).
import { describe, it, expect, beforeEach } from 'vitest'
import {
  defaultClosedGroups,
  orderGroupsWithPins,
  isLowUseGroup,
  readPinnedGroups,
  togglePinnedGroup,
  PINNED_GROUPS_KEY,
  LOW_USE_COLLAPSE_THRESHOLD,
} from '@/constants/sidebarGroups'
import {
  buildSidebarGroupsForRoles,
  type SidebarGroup,
} from '@/constants/sidebarNav'
import { derivePersonas } from '@/constants/personas'

beforeEach(() => localStorage.clear())

const g = (title: string, n = 2): SidebarGroup => ({
  code: title, title, icon: 'grid',
  items: Array.from({ length: n }, (_, i) => ({ label: `${title}-${i}`, path: `/${title}/${i}`, icon: 'grid' })),
})

describe('isLowUseGroup — phân loại tĩnh Governance/Compliance/Admin', () => {
  it('Theo dõi tuân thủ + Hệ thống = ít dùng; vận hành KHÔNG', () => {
    expect(isLowUseGroup('Theo dõi tuân thủ')).toBe(true)
    expect(isLowUseGroup('Hệ thống')).toBe(true)
    expect(isLowUseGroup('Bảo trì định kỳ (PM)')).toBe(false)
    expect(isLowUseGroup('Sửa chữa (CM)')).toBe(false)
  })
})

describe('defaultClosedGroups — D7 default-collapse', () => {
  it('TC-CMDK-15: persona đa-nhóm (>4) → nhóm ít dùng collapsed, vận hành expanded', () => {
    const groups = [
      g('Bảo trì định kỳ (PM)'), g('Sửa chữa (CM)'), g('Hiệu năng & Hiệu chuẩn'),
      g('Sự cố & RCA'), g('Theo dõi tuân thủ'), g('Hệ thống'),
    ]
    expect(groups.length).toBeGreaterThan(LOW_USE_COLLAPSE_THRESHOLD)
    const closed = defaultClosedGroups(groups)
    expect(closed).toContain('Theo dõi tuân thủ')
    expect(closed).toContain('Hệ thống')
    expect(closed).not.toContain('Bảo trì định kỳ (PM)')
    expect(closed).not.toContain('Sửa chữa (CM)')
  })

  it('TC-CMDK-15: persona ≤4 nhóm (KTV) → KHÔNG collapse gì (expand hết)', () => {
    const groups = [g('Bảo trì định kỳ (PM)'), g('Sửa chữa (CM)'), g('Hiệu năng & Hiệu chuẩn'), g('Tài sản & Đối tác')]
    expect(groups.length).toBeLessThanOrEqual(LOW_USE_COLLAPSE_THRESHOLD)
    expect(defaultClosedGroups(groups)).toEqual([])
  })

  it('nhóm ghim KHÔNG bị default-collapse dù ít dùng + đa-nhóm', () => {
    const groups = [
      g('Bảo trì định kỳ (PM)'), g('Sửa chữa (CM)'), g('Hiệu năng & Hiệu chuẩn'),
      g('Sự cố & RCA'), g('Theo dõi tuân thủ'), g('Hệ thống'),
    ]
    const closed = defaultClosedGroups(groups, ['Hệ thống'])
    expect(closed).not.toContain('Hệ thống')   // ghim → luôn expand
    expect(closed).toContain('Theo dõi tuân thủ')
  })
})

describe('orderGroupsWithPins — ghim lên đầu, KHÔNG thêm/bớt nhóm', () => {
  it('nhóm ghim lên đầu, còn lại giữ thứ tự gốc', () => {
    const groups = [g('A'), g('B'), g('C')]
    const ordered = orderGroupsWithPins(groups, ['C'])
    expect(ordered.map((x) => x.title)).toEqual(['C', 'A', 'B'])
  })
  it('BẤT BIẾN: order KHÔNG đổi số nhóm / số entry', () => {
    const groups = [g('A', 3), g('B', 2), g('C', 1)]
    const ordered = orderGroupsWithPins(groups, ['B'])
    expect(ordered.length).toBe(groups.length)
    const entriesBefore = groups.reduce((n, x) => n + x.items.length, 0)
    const entriesAfter = ordered.reduce((n, x) => n + x.items.length, 0)
    expect(entriesAfter).toBe(entriesBefore)
  })
  it('không ghim → giữ nguyên', () => {
    const groups = [g('A'), g('B')]
    expect(orderGroupsWithPins(groups, []).map((x) => x.title)).toEqual(['A', 'B'])
  })
})

describe('TC-CMDK-16: collapse/pin KHÔNG đổi số entry itemVisible (RBAC bất biến)', () => {
  it('admin superuser: orderGroupsWithPins + defaultClosedGroups giữ nguyên tập entry', () => {
    const personas = derivePersonas(['AssetCore Super Admin'])
    const groups = buildSidebarGroupsForRoles(personas, () => true, true)
    const pathsBefore = groups.flatMap((g) => g.items.map((i) => i.path)).sort()

    // Áp D7: ghim 1 nhóm + tính default-collapse.
    const pinned = togglePinnedGroup('Hệ thống') // ['Hệ thống']
    const ordered = orderGroupsWithPins(groups, pinned)
    const closed = defaultClosedGroups(ordered, pinned)

    // Tập entry sau khi order/collapse KHÔNG đổi (collapse chỉ là expand-state).
    const pathsAfter = ordered.flatMap((g) => g.items.map((i) => i.path)).sort()
    expect(pathsAfter).toEqual(pathsBefore)
    // closed chỉ chứa title nhóm — không phải entry.
    for (const t of closed) expect(typeof t).toBe('string')
  })
})

describe('TC-CMDK-16: ghim nhóm persist localStorage + đọc lại', () => {
  it('togglePinnedGroup persist + readPinnedGroups', () => {
    expect(readPinnedGroups()).toEqual([])
    togglePinnedGroup('Hệ thống')
    expect(readPinnedGroups()).toEqual(['Hệ thống'])
    expect(JSON.parse(localStorage.getItem(PINNED_GROUPS_KEY) || '[]')).toEqual(['Hệ thống'])
    togglePinnedGroup('Theo dõi tuân thủ')
    expect(readPinnedGroups()).toEqual(['Hệ thống', 'Theo dõi tuân thủ'])
    togglePinnedGroup('Hệ thống') // bỏ ghim
    expect(readPinnedGroups()).toEqual(['Theo dõi tuân thủ'])
  })
  it('giá trị rác → []', () => {
    localStorage.setItem(PINNED_GROUPS_KEY, '{not array}')
    expect(readPinnedGroups()).toEqual([])
  })
})
