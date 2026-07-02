// TDD — TC-RWD-07 (F4 P2): AssetDetailView tab-bar overflow-x-auto → tab cuối
// 'audit' reachable (cuộn ngang) trên mobile, KHÔNG clip. Desktop KHÔNG vỡ.
// Source-level assert (view nặng, mount full brittle) — kiểm class container tab-bar.
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const SRC = readFileSync(
  resolve(__dirname, 'AssetDetailView.vue'),
  'utf8',
)

describe('TC-RWD-07 — AssetDetailView tab-bar cuộn ngang (F4)', () => {
  it('tab-bar container (border-b chứa 5 tab) có overflow-x-auto', () => {
    // Tab-bar = <div ...> bọc v-for tab info/depreciation/timeline/kpi/audit.
    // Tìm dòng <div ...> ngay trước cụm tab list literal.
    const tabListIdx = SRC.indexOf("'info', 'depreciation', 'timeline', 'kpi', 'audit'")
    expect(tabListIdx).toBeGreaterThan(-1)
    // Container div phải nằm trước cụm v-for và phải có overflow-x-auto trong class.
    const before = SRC.slice(0, tabListIdx)
    const lastDivOpen = before.lastIndexOf('<div')
    const container = SRC.slice(lastDivOpen, tabListIdx)
    expect(container).toContain('overflow-x-auto')
  })

  it("tab 'audit' (tab thứ 5) vẫn hiện diện trong danh sách tab", () => {
    expect(SRC).toContain("'audit'")
    // nhãn audit map giữ nguyên (đã Việt hoá: 'Audit Trail' → 'Nhật ký truy vết')
    expect(SRC).toContain('Nhật ký truy vết')
  })

  it('mỗi tab shrink-0 để không bị co (giữ 1 hàng cuộn)', () => {
    const tabBtnIdx = SRC.indexOf("v-for=\"tab in (['info', 'depreciation', 'timeline', 'kpi', 'audit']")
    expect(tabBtnIdx).toBeGreaterThan(-1)
    // class static của <button> tab chứa shrink-0 / whitespace-nowrap
    const btnBlock = SRC.slice(tabBtnIdx, tabBtnIdx + 400)
    expect(/shrink-0|whitespace-nowrap/.test(btnBlock)).toBe(true)
  })
})
