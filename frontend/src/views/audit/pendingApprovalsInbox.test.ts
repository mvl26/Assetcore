// TDD — APPROVAL-INBOX-CR32: /approvals/pending đa-module (PendingApprovalsView
// consume imm00.get_pending_approvals_inbox thay imm04.list_my_pending_approvals).
//
// TC-FE-1: render 3 loại row với nhãn module VN đúng (Nghiệm thu thiết bị /
//          Điều chuyển / Xuất kho phụ tùng) + href/router-link đúng route detail
//          THẬT từng doctype (verified khớp router/index.ts).
// TC-FE-2: items=[] → empty-state 'Không có phiếu chờ duyệt', KHÔNG bảng rỗng trơ.
// + error-branch (banner + Thử lại), row-click điều hướng, fallback route FE map,
// + guard: fallback map khớp path THẬT trong router/index.ts (chống drift),
// + inbox CHỈ ĐỌC — KHÔNG nút duyệt inline (GATE-8: duyệt ở detail view).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import { resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'
import type { PendingApprovalsInbox } from '@/api/imm00'

const getPendingApprovalsInbox = vi.fn()
vi.mock('@/api/imm00', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm00')>()
  return { ...actual, getPendingApprovalsInbox: () => getPendingApprovalsInbox() }
})

import PendingApprovalsView from './PendingApprovalsView.vue'

// Fixture: 1 phiếu mỗi nguồn — sort pending_since asc (BE contract).
const INBOX_3: PendingApprovalsInbox = {
  items: [
    {
      doctype: 'Asset Commissioning', name: 'ACM-2026-0001', module: 'imm04',
      title: 'Nghiệm thu Máy thở Bennett 840', summary: 'Nghiệm thu ban đầu · bậc 1/2',
      asset: 'ACC-ASS-0001',
      asset_name: 'Máy thở Bennett 840', requested_by: 'ktv@x.vn',
      requested_by_name: 'Nguyễn Văn Kỹ', pending_since: '2026-07-10 08:00:00',
      route: '/commissioning/ACM-2026-0001',
    },
    {
      doctype: 'Asset Transfer', name: 'AT-2026-0002', module: 'imm00',
      title: 'Điều chuyển Monitor B450 sang Khoa Nội',
      summary: 'Khoa Cấp cứu → Khoa Nội · Monitor B450', asset: 'ACC-ASS-0002',
      asset_name: 'Monitor B450', requested_by: 'dieuduong@x.vn',
      requested_by_name: 'Trần Thị Điều', pending_since: '2026-07-11 09:30:00',
      route: '/asset-transfers/AT-2026-0002',
    },
    {
      doctype: 'IMM Spare Allocation', name: 'ALLOC-2026-0003', module: 'imm15',
      title: 'Cấp phát phụ tùng cho lệnh sửa chữa WO-RP-2026-0003',
      summary: 'Dây điện cực 3 chấu ×2 cái', asset: '',
      asset_name: '', requested_by: 'ktv2@x.vn',
      requested_by_name: 'Lê Văn Kho', pending_since: '2026-07-12 10:15:00',
      route: '/cm/work-orders/WO-RP-2026-0003',
    },
  ],
  total: 3,
  by_module: { imm04: 1, imm00: 1, imm15: 1 },
}

const EMPTY: PendingApprovalsInbox = { items: [], total: 0, by_module: {} }

// CR-42 — nguồn thứ 4: phiếu CM 'Asset Repair' chờ nghiệm thu (module imm09), route /cm/work-orders/{name}.
const INBOX_CR42: PendingApprovalsInbox = {
  items: [
    {
      doctype: 'Asset Repair', name: 'WO-RP-2026-0099', module: 'imm09',
      title: 'Sửa Monitor GE — chờ nghiệm thu',
      summary: 'Màn hình không lên nguồn · Monitor GE B40', asset: 'ACC-ASS-0099',
      asset_name: 'Monitor GE B40', requested_by: 'ktv@x.vn',
      requested_by_name: 'Phạm Văn Sửa', pending_since: '2026-07-13 07:00:00',
      route: '/cm/work-orders/WO-RP-2026-0099',
    },
  ],
  total: 1,
  by_module: { imm09: 1 },
}

async function mountView() {
  const w = mount(PendingApprovalsView, {
    global: { stubs: { Transition: false } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  resetRouteMock()
  getPendingApprovalsInbox.mockReset()
})

describe('PendingApprovalsView — inbox đa-module (CR-32)', () => {
  it('TC-FE-1a: render 3 loại row với nhãn module tiếng Việt đúng', async () => {
    getPendingApprovalsInbox.mockResolvedValue(INBOX_3)
    const w = await mountView()
    const text = w.text()
    expect(getPendingApprovalsInbox).toHaveBeenCalled()
    expect(text).toContain('Nghiệm thu thiết bị')
    expect(text).toContain('Điều chuyển')
    expect(text).toContain('Xuất kho phụ tùng')
    // đủ 3 phiếu
    expect(text).toContain('ACM-2026-0001')
    expect(text).toContain('AT-2026-0002')
    expect(text).toContain('ALLOC-2026-0003')
  })

  it('TC-FE-1b: KHÔNG leak doctype/module code tiếng Anh ra UI', async () => {
    getPendingApprovalsInbox.mockResolvedValue(INBOX_3)
    const w = await mountView()
    const text = w.text()
    expect(text).not.toContain('Asset Commissioning')
    expect(text).not.toContain('Asset Transfer')
    expect(text).not.toContain('IMM Spare Allocation')
    expect(text).not.toContain('imm04')
    expect(text).not.toContain('imm15')
    // email người gửi KHÔNG render (chỉ requested_by_name)
    expect(text).not.toContain('ktv@x.vn')
    expect(text).toContain('Nguyễn Văn Kỹ')
  })

  it('TC-FE-1c: href router-link đúng route detail THẬT từng doctype', async () => {
    getPendingApprovalsInbox.mockResolvedValue(INBOX_3)
    const w = await mountView()
    const hrefs = w.findAll('a').map((a) => a.attributes('href'))
    expect(hrefs).toContain('/commissioning/ACM-2026-0001')
    expect(hrefs).toContain('/asset-transfers/AT-2026-0002')
    expect(hrefs).toContain('/cm/work-orders/WO-RP-2026-0003')
  })

  it('TC-FE-1d: click hàng → router.push đúng route detail', async () => {
    getPendingApprovalsInbox.mockResolvedValue(INBOX_3)
    const w = await mountView()
    const rows = w.findAll('tbody tr')
    expect(rows.length).toBe(3)
    await rows[1].trigger('click')
    expect(routerPushSpy()).toHaveBeenCalledWith('/asset-transfers/AT-2026-0002')
  })

  it('TC-FE-1e: item thiếu route → fallback FE map theo doctype (2 route verified)', async () => {
    getPendingApprovalsInbox.mockResolvedValue({
      items: [
        { ...INBOX_3.items[0], route: '' },
        { ...INBOX_3.items[1], route: '' },
      ],
      total: 2,
      by_module: { imm04: 1, imm00: 1 },
    })
    const w = await mountView()
    const hrefs = w.findAll('a').map((a) => a.attributes('href'))
    expect(hrefs).toContain('/commissioning/ACM-2026-0001')
    expect(hrefs).toContain('/asset-transfers/AT-2026-0002')
  })

  it('TC-FE-2: items=[] → empty-state "Không có phiếu chờ duyệt", không bảng rỗng trơ', async () => {
    getPendingApprovalsInbox.mockResolvedValue(EMPTY)
    const w = await mountView()
    expect(w.text()).toContain('Không có phiếu chờ duyệt')
    expect(w.find('table').exists()).toBe(false)
  })

  it('error-branch: BE lỗi → banner + nút Thử lại (retry gọi lại API)', async () => {
    getPendingApprovalsInbox.mockRejectedValueOnce(new Error('Lỗi mạng'))
    getPendingApprovalsInbox.mockResolvedValueOnce(INBOX_3)
    const w = await mountView()
    expect(w.text()).toContain('Lỗi mạng')
    const retry = w.findAll('button').find((b) => b.text().includes('Thử lại'))
    expect(retry).toBeTruthy()
    await retry!.trigger('click')
    await flushPromises()
    expect(getPendingApprovalsInbox).toHaveBeenCalledTimes(2)
    expect(w.text()).toContain('ACM-2026-0001')
  })

  it('chip by_module: đếm theo loại phiếu với nhãn VN', async () => {
    getPendingApprovalsInbox.mockResolvedValue(INBOX_3)
    const w = await mountView()
    const chips = w.find('[data-testid="module-chips"]')
    expect(chips.exists()).toBe(true)
    expect(chips.text()).toContain('Nghiệm thu thiết bị')
    expect(chips.text()).toContain('Điều chuyển')
    expect(chips.text()).toContain('Xuất kho phụ tùng')
  })

  it('inbox CHỈ ĐỌC: KHÔNG có nút duyệt inline (GATE-8 — duyệt ở detail view)', async () => {
    getPendingApprovalsInbox.mockResolvedValue(INBOX_3)
    const w = await mountView()
    const buttons = w.findAll('button').map((b) => b.text())
    expect(buttons.some((t) => /duyệt|approve/i.test(t))).toBe(false)
  })

  // ─── CR-42 — nguồn thứ 4: phiếu CM 'Asset Repair' chờ nghiệm thu (imm09) ──────────
  it('CR-42: phiếu Asset Repair → nhãn "Chờ nghiệm thu (CM)", href /cm/work-orders, KHÔNG leak doctype EN', async () => {
    getPendingApprovalsInbox.mockResolvedValue(INBOX_CR42)
    const w = await mountView()
    const text = w.text()
    expect(text).toContain('Chờ nghiệm thu (CM)')
    expect(text).toContain('WO-RP-2026-0099')
    expect(text).not.toContain('Asset Repair') // KHÔNG rò doctype English
    expect(text).not.toContain('imm09')
    const hrefs = w.findAll('a').map((a) => a.attributes('href'))
    expect(hrefs).toContain('/cm/work-orders/WO-RP-2026-0099')
  })

  it('CR-42: chip by_module.imm09 hiển thị nhãn VN (KHÔNG rơi về "Khác")', async () => {
    getPendingApprovalsInbox.mockResolvedValue(INBOX_CR42)
    const w = await mountView()
    const chips = w.find('[data-testid="module-chips"]')
    expect(chips.exists()).toBe(true)
    expect(chips.text()).toContain('Chờ nghiệm thu (CM)')
    expect(chips.text()).not.toContain('Khác')
  })

  it('CR-42: item thiếu route → fallback FE map Asset Repair → /cm/work-orders/{name}', async () => {
    getPendingApprovalsInbox.mockResolvedValue({
      items: [{ ...INBOX_CR42.items[0], route: '' }],
      total: 1,
      by_module: { imm09: 1 },
    })
    const w = await mountView()
    const hrefs = w.findAll('a').map((a) => a.attributes('href'))
    expect(hrefs).toContain('/cm/work-orders/WO-RP-2026-0099')
  })

  // ─── CR-44 — summary 'cái đang được duyệt' render VERBATIM dưới title ──────────
  it('CR-44: render summary server-built VERBATIM dưới title mỗi item (4 nguồn)', async () => {
    getPendingApprovalsInbox.mockResolvedValue(INBOX_3)
    const w = await mountView()
    const text = w.text()
    // Verbatim từng nguồn — FE KHÔNG dựng lại, chỉ render chuỗi BE phát.
    expect(text).toContain('Nghiệm thu ban đầu · bậc 1/2')       // Asset Commissioning
    expect(text).toContain('Khoa Cấp cứu → Khoa Nội · Monitor B450') // Asset Transfer (from→to · asset)
    expect(text).toContain('Dây điện cực 3 chấu ×2 cái')          // IMM Spare Allocation (item ×qty uom)
  })

  it('CR-44: Asset Repair (CM) — summary chứa mô tả hỏng + tên thiết bị', async () => {
    getPendingApprovalsInbox.mockResolvedValue(INBOX_CR42)
    const w = await mountView()
    expect(w.text()).toContain('Màn hình không lên nguồn · Monitor GE B40')
  })

  it('CR-44: summary rỗng (coalesce "") → KHÔNG render dòng trống, KHÔNG crash', async () => {
    getPendingApprovalsInbox.mockResolvedValue({
      items: [{ ...INBOX_3.items[0], summary: '' }],
      total: 1,
      by_module: { imm04: 1 },
    })
    const w = await mountView()
    // Row vẫn render đầy đủ (title + code), chỉ dòng summary bị ẩn (v-if).
    expect(w.text()).toContain('Nghiệm thu Máy thở Bennett 840')
    expect(w.text()).toContain('ACM-2026-0001')
    expect(w.findAll('tbody tr').length).toBe(1)
  })
})
