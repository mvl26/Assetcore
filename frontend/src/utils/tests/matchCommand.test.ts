// TDD — fuzzy search ⌘K (ADR-IMM00-CMDK D3). TC-CMDK-06.
import { describe, it, expect } from 'vitest'
import { matchCommand } from '@/utils/matchCommand'
import type { CommandItem } from '@/types/command'

function cmd(title: string, id = title): CommandItem {
  return { id, title, to: '/' + id, source: 'nav' }
}

// Catalog mô phỏng nhãn thật trong MODULE_NAV.
const ITEMS: CommandItem[] = [
  cmd('Bảo trì định kỳ (PM)', 'pm'),
  cmd('Lệnh bảo trì', 'pm-wo'),
  cmd('Tổng quan bảo trì', 'pm-dash'),
  cmd('Thiết bị', 'device'),
  cmd('Danh sách thiết bị', 'asset-list'),
  cmd('Tạo PM', 'pm-create'),
  cmd('Tạo báo hỏng', 'cm-create'),
  cmd('Hiệu chuẩn', 'cal'),
  cmd('Sửa chữa (CM)', 'cm'),
  cmd('Tồn kho', 'stock'),
  cmd('Người dùng', 'users'),
  cmd('Nhà cung cấp', 'supplier'),
]

function top(query: string): string {
  const res = matchCommand(query, ITEMS)
  return res[0]?.title ?? ''
}

describe('matchCommand — bảng query không-dấu → top result (≥10 cặp)', () => {
  const cases: Array<[string, RegExp]> = [
    ['bao tri', /Bảo trì/],
    ['thiet bi', /Thiết bị/],
    ['tao pm', /Tạo PM/],
    ['tao bao hong', /Tạo báo hỏng/],
    ['hieu chuan', /Hiệu chuẩn/],
    ['sua chua', /Sửa chữa/],
    ['ton kho', /Tồn kho/],
    ['nguoi dung', /Người dùng/],
    ['nha cung cap', /Nhà cung cấp/],
    ['danh sach thiet bi', /Danh sách thiết bị/],
    ['lenh bao tri', /Lệnh bảo trì/],
  ]
  for (const [q, re] of cases) {
    it(`TC-CMDK-06: "${q}" → top khớp ${re}`, () => {
      expect(top(q)).toMatch(re)
    })
  }

  it('exact-prefix xếp trên substring: "thiet bi" → "Thiết bị" trước "Danh sách thiết bị"', () => {
    const res = matchCommand('thiet bi', ITEMS).map((c) => c.title)
    expect(res.indexOf('Thiết bị')).toBeLessThan(res.indexOf('Danh sách thiết bị'))
  })

  it('token-AND: "tao bao hong" KHÔNG khớp "Tạo PM"', () => {
    const res = matchCommand('tao bao hong', ITEMS).map((c) => c.title)
    expect(res).not.toContain('Tạo PM')
    expect(res).toContain('Tạo báo hỏng')
  })

  it('query rỗng → trả nguyên list (caller xử recent/pinned)', () => {
    expect(matchCommand('', ITEMS).length).toBe(ITEMS.length)
  })

  it('pinned/recent boost đẩy lệnh lên khi CÙNG tầng điểm (tie-break)', () => {
    // 'bao tri' khớp 'Lệnh bảo trì'(pm-wo) + 'Tổng quan bảo trì'(pm-dash) cùng
    // token-prefix tier. KHÔNG khớp exact-prefix nào trong cặp này → boost quyết.
    const subset = ITEMS.filter((c) => c.id === 'pm-wo' || c.id === 'pm-dash')
    const res = matchCommand('bao tri', subset, { pinned: ['pm-dash'] }).map((c) => c.id)
    expect(res[0]).toBe('pm-dash')
  })

  it('boost KHÔNG vượt tầng: pinned substring KHÔNG vượt exact-prefix (ranking ADR)', () => {
    // 'Bảo trì định kỳ (PM)'(pm) = exact-prefix(1000); pinned 'pm-wo'(token-prefix)
    // + boost 80 = 780 < 1000 → exact-prefix vẫn đầu.
    const res = matchCommand('bao tri', ITEMS, { pinned: ['pm-wo'] }).map((c) => c.id)
    expect(res[0]).toBe('pm')
  })

  it('không khớp → vắng mặt (không trả 0-score)', () => {
    expect(matchCommand('zzzzz', ITEMS)).toEqual([])
  })
})
