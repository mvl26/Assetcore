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

/**
 * Danh sách tab literal trong `AssetDetailView.vue`.
 * AC-CR-87 vòng 3: thêm tab thứ 6 «Bản ghi liên quan» (breakage ĐÃ LƯỜNG TRƯỚC —
 * cập nhật literal là hợp lệ, TUYỆT ĐỐI KHÔNG nới lỏng assert overflow-x-auto/shrink-0).
 */
const TAB_LIST_LITERAL = "'info', 'depreciation', 'timeline', 'kpi', 'audit', 'related'"

describe('TC-RWD-07 — AssetDetailView tab-bar cuộn ngang (F4)', () => {
  it('tab-bar container (border-b chứa 6 tab) có overflow-x-auto', () => {
    // Tab-bar = <div ...> bọc v-for tab info/depreciation/timeline/kpi/audit/related.
    // Tìm dòng <div ...> ngay trước cụm tab list literal.
    const tabListIdx = SRC.indexOf(TAB_LIST_LITERAL)
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

  it("tab 'related' (tab thứ 6, AC-CR-87) hiện diện + nhãn tiếng Việt", () => {
    expect(SRC).toContain("'related'")
    expect(SRC).toContain('Bản ghi liên quan')
  })

  it('mỗi tab shrink-0 để không bị co (giữ 1 hàng cuộn)', () => {
    const tabBtnIdx = SRC.indexOf(`v-for="tab in ([${TAB_LIST_LITERAL}]`)
    expect(tabBtnIdx).toBeGreaterThan(-1)
    // class static của <button> tab chứa CẢ shrink-0 lẫn whitespace-nowrap
    const btnBlock = SRC.slice(tabBtnIdx, tabBtnIdx + 600)
    expect(btnBlock).toContain('shrink-0')
    expect(btnBlock).toContain('whitespace-nowrap')
  })
})
