// Copyright (c) 2026, AssetCore Team
// «Bản ghi liên quan» — NỘI DUNG MỘT TAB (AC-CR-87, vòng 2).
//
// Hợp đồng hiển thị ĐÃ ĐỔI so với bản card cũ: ô liên quan KHÔNG còn là một nút điều
// hướng duy nhất, mà là một dòng gọn [nhãn tiếng Việt][số đếm][chuỗi cắt bớt] kèm tối
// đa 5 dòng xem trước THẬT và một nút «Xem tất cả» CHỈ khi deep-link có khoá lọc.
// Bộ test này khoá đúng 4 lời hứa hay bị phá nhất:
//   1. Nhãn 100% tiếng Việt (không rò tên DocType tiếng Anh ra giao diện);
//   2. Preview là DỮ LIỆU (title + nhãn trạng thái VI + ngày), không phải mỗi con số;
//   3. Không sinh NÚT CHẾT: không route chi tiết ⇒ text tĩnh; không khoá lọc ⇒ không
//      có «Xem tất cả» (bấm ra danh sách chung/trống chính là bug người dùng báo);
//   4. Cắt bớt TRUNG THỰC: chạm trần đếm ⇒ '100+', TUYỆT ĐỐI không bịa "còn N".
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'

// Chỉ những đường dẫn ở đây mới "phân giải được" — mô phỏng router thật để nút tạo
// mới / «Xem tất cả» không bao giờ trỏ vào route không tồn tại.
const RESOLVABLE = new Set<string>([
  '/pm/work-orders/new', '/cm/create', '/incidents/new', '/calibration/new',
  '/pm/work-orders', '/cm/work-orders', '/calibration', '/compliance/findings',
  '/documents', '/documents/requests', '/asset-transfers', '/incidents/list', '/rca',
])

const push = vi.fn()
const resolve = vi.fn((to: string) => ({ matched: RESOLVABLE.has(to) ? [{ path: to }] : [] }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push, resolve }) }))

// Capability của phiên đang đăng nhập — lớp phòng thủ thứ hai của nút «Tạo …».
// `beforeEach` nạp đủ cả 4 cap tạo; test nào cần thiếu quyền thì tự xoá.
const caps = new Set<string>()
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (c: string | readonly string[]) =>
      Array.isArray(c) ? c.some((x) => caps.has(x)) : caps.has(c as string),
  }),
}))

const getConnections = vi.fn()
vi.mock('@/api/connections', async () => {
  const actual = await vi.importActual<typeof import('@/api/connections')>('@/api/connections')
  return { ...actual, getConnections: (...a: unknown[]) => getConnections(...a) }
})

import { DOCTYPE_ROUTE } from '@/api/connections'
import type { ConnectionItem, ConnectionPreviewRow, ConnectionsPayload } from '@/api/connections'
import { formatDate } from '@/utils/formatters'
import RelatedRecords from './RelatedRecords.vue'

// ─────────────────────────────────────────────────────────────────────────────
// Dựng payload
// ─────────────────────────────────────────────────────────────────────────────
function row(over: Partial<ConnectionPreviewRow> = {}): ConnectionPreviewRow {
  return {
    name: 'REC-0001',
    title: 'Bản ghi mẫu',
    status: 'ZZTHOSTATUS',
    status_label: 'Đang thực hiện',
    date: '2026-03-04',
    ...over,
  }
}

// Hợp đồng ô = ĐÚNG 10 khoá (AC-CR-92 + `create_prefill` bắt buộc từ AC-CR-105):
// `label`/`count`/`capped`/`filters` đã gỡ ở CẢ hai đầu. Cờ chạm trần là `total_capped`
// (int 0|1) — nghĩa: `total` là CẬN DƯỚI ⇒ badge '+'. `create_prefill` mặc định `{}` =
// "không có gì điền sẵn" (KHÔNG BAO GIỜ `null` — đó là hợp đồng backend, INV-CONN4-1).
function item(over: Partial<ConnectionItem> = {}): ConnectionItem {
  return {
    doctype: 'Incident Report',
    label_vi: 'Báo cáo sự cố',
    total: 1,
    truncated: 0,
    total_capped: 0,
    items: [row()],
    deep_link_filters: { asset: 'AC-ASSET-2026-00001' },
    can_create: false,
    create_route_hint: '',
    create_prefill: {},
    ...over,
  }
}

function payload(items: ConnectionItem[], over: Partial<ConnectionsPayload> = {}): ConnectionsPayload {
  return {
    doctype: 'AC Asset',
    name: 'AC-ASSET-2026-00001',
    total: items.reduce((s, i) => s + i.total, 0),
    groups: [{ label: 'Nhóm kiểm thử', label_vi: 'Nhóm kiểm thử', items }],
    ...over,
  }
}

const mountIt = (): VueWrapper =>
  mount(RelatedRecords, { props: { doctype: 'AC Asset', name: 'AC-ASSET-2026-00001' } })

async function mountWith(p: unknown): Promise<VueWrapper> {
  getConnections.mockResolvedValue(p)
  const w = mountIt()
  await flushPromises()
  return w
}

const cells = (w: VueWrapper) => w.findAll('[data-testid="conn-item"]')
const rows = (w: VueWrapper) => w.findAll('[data-testid="conn-row"]')

describe('RelatedRecords — nội dung tab «Bản ghi liên quan»', () => {
  beforeEach(() => {
    push.mockReset()
    resolve.mockClear()
    getConnections.mockReset()
    caps.clear()
    for (const c of [
      'pm.create', 'repair.create', 'calibration.create', 'corrective.create',
      // Cap ĐỌC của route đích — lớp gác thứ 3 của «Xem tất cả» (ADR D-CR5-5).
      'pm.read', 'repair.read', 'calibration.read', 'corrective.read',
      'compliance.read', 'document.read',
    ]) {
      caps.add(c)
    }
  })

  // ── A1 · Nhãn tiếng Việt 100% ──────────────────────────────────────────────
  it('TC-FE-CONN-01 — ưu tiên label_vi, KHÔNG rò tên DocType tiếng Anh', async () => {
    const w = await mountWith(payload([
      item({ doctype: 'PM Work Order', label_vi: 'Phiếu bảo trì định kỳ' }),
    ]))

    expect(getConnections).toHaveBeenCalledWith('AC Asset', 'AC-ASSET-2026-00001')
    expect(w.text()).toContain('Phiếu bảo trì định kỳ')
    // Soi cả HTML (kể cả title/aria-label) — tên DocType thô không được lọt qua thuộc tính.
    expect(w.html()).not.toContain('PM Work Order')
  })

  // AC-CR-92 — ô LEGACY (`label`/`count`/`capped`/`filters`) không còn tồn tại; ca cần bảo
  // vệ giờ là CỬA SỔ DEPLOY: worker `--preload` chưa reload trả ô THIẾU khoá mới. Màn chi
  // tiết phải vẫn đọc được, và TUYỆT ĐỐI không in "undefined"/"NaN" lên badge (A9).
  it('TC-FE-CONN-02 — BE stale (thiếu total_capped/items) ⇒ nhãn VI + số trần, 0 chữ "undefined"', async () => {
    const staleCell = {
      doctype: 'Asset Repair',
      label_vi: 'Phiếu sửa chữa',
      total: 2,
      deep_link_filters: { asset: 'AC-ASSET-2026-00001' },
    }
    const w = await mountWith(payload([staleCell as unknown as ConnectionItem]))

    expect(w.text()).toContain('Phiếu sửa chữa')
    expect(cells(w)).toHaveLength(1)
    expect(w.find('[data-testid="conn-count"]').text()).toBe('2')
    expect(w.text()).not.toContain('undefined')
    expect(w.text()).not.toContain('NaN')
    expect(w.text()).not.toContain('null')
  })

  it('TC-FE-CONN-03 — parity: MỌI doctype trong DOCTYPE_ROUTE đều render nhãn VI', async () => {
    const keys = Object.keys(DOCTYPE_ROUTE)
    expect(keys.length).toBeGreaterThanOrEqual(20)

    const all = keys.map((dt, i) => item({
      doctype: dt,
      label_vi: `VI-${i}`,
      items: [row({ name: `REC-${i}`, title: `Bản ghi ${i}`, status_label: `Trạng thái ${i}`, date: '' })],
    }))
    const w = await mountWith(payload(all))

    const html = w.html()
    const leaked = keys.filter(dt => html.includes(dt))
    expect(leaked, `Tên DocType thô lọt ra giao diện: ${JSON.stringify(leaked)}`).toEqual([])
    keys.forEach((_dt, i) => expect(w.text()).toContain(`VI-${i}`))
  })

  // ── A2 · Preview là DỮ LIỆU THẬT ───────────────────────────────────────────
  it('TC-FE-CONN-04 — mỗi dòng preview có tiêu đề + nhãn trạng thái VI + ngày', async () => {
    const w = await mountWith(payload([
      item({
        total: 3,
        truncated: 0,
        items: [
          row({ name: 'IR-1', title: 'Máy thở báo lỗi', status: 'ZZOPEN', status_label: 'Đang mở', date: '2026-03-04' }),
          row({ name: 'IR-2', title: 'Bơm tiêm rò rỉ', status: 'ZZINPROGRESS', status_label: 'Đang xử lý', date: '2026-03-05' }),
          row({ name: 'IR-3', title: 'Monitor mất tín hiệu', status: 'ZZCLOSED', status_label: 'Đã đóng', date: '' }),
        ],
      }),
    ]))

    expect(rows(w)).toHaveLength(3)
    const text = w.text()
    expect(text).toContain('Máy thở báo lỗi')
    expect(text).toContain('Bơm tiêm rò rỉ')
    expect(text).toContain('Đang mở')
    expect(text).toContain('Đã đóng')
    // Ngày đi qua SSoT `formatDate` (dd/mm/yyyy) — KHÔNG in chuỗi ISO thô.
    expect(text).toContain(formatDate('2026-03-04'))
    expect(text).not.toContain('2026-03-04')
    // Ngày rỗng ⇒ '—', không phải chuỗi rỗng câm.
    expect(rows(w)[2].text()).toContain('—')
    // Mã trạng thái kỹ thuật KHÔNG bao giờ ra giao diện.
    for (const raw of ['ZZOPEN', 'ZZINPROGRESS', 'ZZCLOSED']) {
      expect(w.html()).not.toContain(raw)
    }
    expect(text).not.toContain('undefined')
  })

  // ── A3 · Dòng preview mở ĐÚNG bản ghi ──────────────────────────────────────
  it('TC-FE-CONN-05 — có route chi tiết ⇒ nút mở đúng hồ sơ; không route ⇒ text tĩnh', async () => {
    const w = await mountWith(payload([
      item({
        doctype: 'Asset Repair', label_vi: 'Phiếu sửa chữa',
        items: [row({ name: 'AR-2026-0001', title: 'Sửa máy thở' })],
        deep_link_filters: { asset: 'AC-ASSET-2026-00001' },
      }),
      item({
        doctype: 'Asset Lifecycle Event', label_vi: 'Sự kiện vòng đời',
        items: [row({ name: 'ALE-9', title: 'Ghi nhận đưa vào sử dụng' })],
      }),
    ]))

    const all = rows(w)
    expect(all).toHaveLength(2)

    const repairRow = all.find(r => r.text().includes('Sửa máy thở'))!
    expect(repairRow.element.tagName).toBe('BUTTON')
    await repairRow.trigger('click')
    expect(push).toHaveBeenCalledWith('/cm/work-orders/AR-2026-0001')

    push.mockReset()
    const eventRow = all.find(r => r.text().includes('Ghi nhận đưa vào sử dụng'))!
    expect(eventRow.element.tagName).not.toBe('BUTTON')
    await eventRow.trigger('click')
    expect(push).not.toHaveBeenCalled()
  })

  // ── A4 · «Xem tất cả» = deep-link CÓ LỌC ───────────────────────────────────
  it('TC-FE-CONN-06 — có khoá lọc + có route danh sách ⇒ deep-link đúng bộ lọc', async () => {
    const w = await mountWith(payload([
      item({ doctype: 'Incident Report', deep_link_filters: { asset: 'AC-ASSET-2026-00001' } }),
    ]))

    const seeAll = w.find('[data-testid="conn-see-all"]')
    expect(seeAll.exists()).toBe(true)
    await seeAll.trigger('click')
    expect(push).toHaveBeenCalledWith({
      path: '/incidents/list',
      query: { asset: 'AC-ASSET-2026-00001' },
    })
  })

  it('TC-FE-CONN-07 — count > 0 nhưng KHÔNG có khoá lọc ⇒ TUYỆT ĐỐI không có «Xem tất cả»', async () => {
    const w = await mountWith(payload([
      item({ doctype: 'Incident Report', total: 7, truncated: 1, deep_link_filters: {} }),
    ]))

    expect(w.text()).toContain('7')
    expect(w.find('[data-testid="conn-see-all"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Xem tất cả')
  })

  it('TC-FE-CONN-08 — có khoá lọc nhưng doctype chưa có màn danh sách ⇒ không nút, không push', async () => {
    const w = await mountWith(payload([
      item({
        doctype: 'Asset Lifecycle Event', label_vi: 'Sự kiện vòng đời',
        deep_link_filters: { asset: 'AC-ASSET-2026-00001' },
      }),
    ]))

    expect(w.find('[data-testid="conn-see-all"]').exists()).toBe(false)
    expect(push).not.toHaveBeenCalled()
  })

  // ── A5 · Cắt bớt TRUNG THỰC ────────────────────────────────────────────────
  it('TC-FE-CONN-09 — 5/12 khi cắt bớt thường; 100+ khi chạm trần (không bịa "còn 95")', async () => {
    const five = Array.from({ length: 5 }, (_, i) => row({ name: `IR-${i}`, title: `Sự cố ${i}` }))

    const w1 = await mountWith(payload([item({ total: 12, truncated: 1, total_capped: 0, items: five })]))
    expect(w1.text()).toContain('5/12')

    getConnections.mockReset()
    const w2 = await mountWith(payload([item({ total: 100, truncated: 1, total_capped: 1, items: five })]))
    expect(w2.text()).toContain('100+')
    expect(w2.text()).not.toContain('còn 95')
    expect(w2.text()).not.toMatch(/còn\s+\d+/)
  })

  // TC-FE-CONN-31 (AC-CR-92 · A8) — RENDER THẬT, chấm ĐÚNG phần tử. `text()` của cả
  // wrapper vẫn xanh khi badge in '100' trần mà chuỗi '100+' đến từ dải meta; ca này chốt
  // trên chính `conn-count` để nghĩa "cận dưới" không thể tuột khỏi badge.
  it('TC-FE-CONN-31 — total_capped=1 ⇒ badge conn-count === "100+", meta === "Đang xem 5/100+"', async () => {
    const five = Array.from({ length: 5 }, (_, i) => row({ name: `IR-${i}`, title: `Sự cố ${i}` }))
    const w = await mountWith(payload([item({ total: 100, total_capped: 1, truncated: 1, items: five })]))

    const badge = w.find('[data-testid="conn-count"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe('100+')
    expect(badge.text()).not.toBe('100')

    const meta = w.find('[data-testid="conn-meta"]')
    expect(meta.exists()).toBe(true)
    expect(meta.text()).toContain('Đang xem 5/100+')
    // 0 dấu vết của phép trừ dưới mọi mẫu câu.
    expect(w.text()).not.toContain('còn ')
    expect(w.text()).not.toContain('95')
  })

  it('TC-FE-CONN-32 — total_capped=0 ⇒ badge số THẬT "7" + dải "Đang xem 5/7" (không dấu "+")', async () => {
    const five = Array.from({ length: 5 }, (_, i) => row({ name: `IR-${i}`, title: `Sự cố ${i}` }))
    const w = await mountWith(payload([item({ total: 7, total_capped: 0, truncated: 1, items: five })]))

    const badge = w.find('[data-testid="conn-count"]')
    expect(badge.text()).toBe('7')
    expect(badge.text()).not.toContain('+')
    expect(w.find('[data-testid="conn-meta"]').text()).toContain('Đang xem 5/7')
  })

  // Dòng 3 bảng `06 §VIII.12.5` — đã xem hết: dải cắt bớt KHÔNG được tồn tại (một dải nói
  // "Đang xem 3/3" là nhiễu thuần tuý, và là chỗ để phép suy diễn cũ lẻn về).
  it('TC-FE-CONN-33 — total 3 / 3 dòng / truncated 0 ⇒ badge "3" và KHÔNG có conn-meta', async () => {
    const three = Array.from({ length: 3 }, (_, i) => row({ name: `IR-${i}`, title: `Sự cố ${i}` }))
    const w = await mountWith(payload([item({ total: 3, total_capped: 0, truncated: 0, items: three })]))

    expect(w.find('[data-testid="conn-count"]').text()).toBe('3')
    expect(w.find('[data-testid="conn-meta"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Đang xem')
  })

  // ── A6 · Hình dạng TAB ─────────────────────────────────────────────────────
  // ⚠️ BREAKAGE KHAI BÁO TRƯỚC (AC-CR-93 — ADR §14.8 · `07 §XVIII.8.4`): phạm vi chấm
  // "ô count 0 render gọn" chuyển từ `conn-item` sang `conn-empty-summary`, vì từ vòng
  // này ô rỗng KHÔNG còn ô riêng (D-FE-8 vốn đã nói vậy từ vòng 2 — assert cũ đang khoá
  // một cài đặt PHẢN hợp đồng). Hai vế '0 nút / 0 conn-row' GIỮ NGUYÊN, chỉ đổi chỗ chấm.
  it('TC-FE-CONN-10 — không heading/card riêng; expose total; ô count 0 gộp vào dòng gộp', async () => {
    const w = await mountWith(payload(
      [
        item({ doctype: 'Incident Report', total: 2 }),
        item({
          doctype: 'IMM RCA Record', label_vi: 'Hồ sơ phân tích nguyên nhân gốc',
          total: 0, truncated: 0, items: [],
          can_create: true, create_route_hint: '/pm/work-orders/new',
        }),
      ],
      { total: 2 },
    ))

    expect(w.text()).not.toContain('Bản ghi liên quan')
    expect(w.element.tagName).not.toBe('SECTION')
    expect((w.vm as unknown as { total: number }).total).toBe(2)

    // Ô rỗng không còn là `conn-item` — nhãn của nó đi vào dòng gộp của CHÍNH nhóm nó.
    expect(cells(w)).toHaveLength(1)
    const empty = w.find('[data-testid="conn-empty-summary"]')
    expect(empty.exists()).toBe(true)
    expect(empty.text()).toContain('Hồ sơ phân tích nguyên nhân gốc')
    expect(empty.findAll('button')).toHaveLength(0)
    expect(empty.findAll('[data-testid="conn-row"]')).toHaveLength(0)
  })

  // ── A7 · Không sinh nút chết cho vòng 4 ────────────────────────────────────
  it('TC-FE-CONN-11 — can_create=false ⇒ 0 nút tạo; can_create=true + route thật ⇒ đúng 1', async () => {
    const w1 = await mountWith(payload([item({ can_create: false, create_route_hint: '' })]))
    expect(w1.findAll('[data-testid="conn-create"]')).toHaveLength(0)
    expect(w1.findAll('button').filter(b => b.text().includes('Tạo'))).toHaveLength(0)

    getConnections.mockReset()
    const w2 = await mountWith(payload([
      item({ doctype: 'PM Work Order', label_vi: 'Phiếu bảo trì định kỳ', can_create: true, create_route_hint: '/pm/work-orders/new' }),
    ]))
    expect(w2.findAll('[data-testid="conn-create"]')).toHaveLength(1)

    // Gợi ý trỏ route KHÔNG tồn tại ⇒ vẫn 0 nút (không dẫn tới 404).
    getConnections.mockReset()
    const w3 = await mountWith(payload([
      item({ can_create: true, create_route_hint: '/route/khong-ton-tai' }),
    ]))
    expect(w3.findAll('[data-testid="conn-create"]')).toHaveLength(0)
  })

  // ── A8 · Trạng thái phụ trợ (hợp đồng cũ) ──────────────────────────────────
  it('TC-FE-CONN-12 — đang tải / lỗi có «Thử lại» / rỗng có câu tiếng Việt có nghĩa', async () => {
    // Đang tải
    let release: (v: unknown) => void = () => {}
    getConnections.mockReturnValue(new Promise(res => { release = res }))
    const loadingWrapper = mountIt()
    await flushPromises()
    expect(loadingWrapper.text()).toContain('Đang tải')
    release(payload([item()]))
    await flushPromises()

    // Lỗi + thử lại
    getConnections.mockReset()
    getConnections.mockRejectedValueOnce(new Error('Mất kết nối'))
    const w = mountIt()
    await flushPromises()
    expect(w.text()).toContain('Thử lại')

    getConnections.mockResolvedValue(payload([item({ label_vi: 'Báo cáo sự cố' })]))
    await w.findAll('button').find(b => b.text().includes('Thử lại'))!.trigger('click')
    await flushPromises()
    expect(w.text()).toContain('Báo cáo sự cố')
    expect(getConnections).toHaveBeenCalledTimes(2)

    // Rỗng
    getConnections.mockReset()
    const wEmpty = await mountWith(payload([], { groups: [], total: 0 }))
    expect(wEmpty.text()).toContain('Chưa có bản ghi nào liên quan')
  })

  // ── A9 · «Tạo từ ngữ cảnh cha» ─────────────────────────────────────────────
  // Nút tạo phải (a) mang theo hồ sơ cha, (b) không bao giờ sinh query rác,
  // (c) không render khi phiên thiếu capability của CHÍNH route đích.
  const repairCell = (over: Partial<ConnectionItem> = {}): ConnectionItem => item({
    doctype: 'Asset Repair',
    label_vi: 'Phiếu sửa chữa',
    can_create: true,
    create_route_hint: '/cm/create',
    create_prefill: { asset: 'AC-ASSET-2026-00001' },
    ...over,
  })

  it('TC-FE-CONN-13 — nhãn nút tạo là tiếng Việt theo label_vi (không ghép tên DocType)', async () => {
    const w = await mountWith(payload([
      repairCell(),
      item({
        doctype: 'Incident Report', label_vi: 'Báo cáo sự cố',
        can_create: true, create_route_hint: '/incidents/new',
        create_prefill: { asset: 'AC-ASSET-2026-00001' },
      }),
    ]))

    const labels = w.findAll('[data-testid="conn-create"]').map(b => b.text())
    expect(labels).toEqual(['Tạo phiếu sửa chữa', 'Báo sự cố'])
    // aria-label bắt đầu bằng đúng nhãn nhìn thấy (WCAG 2.5.3 label-in-name).
    const aria = w.findAll('[data-testid="conn-create"]').map(b => b.attributes('aria-label'))
    expect(aria[0]).toBe('Tạo phiếu sửa chữa cho hồ sơ này')
    for (const raw of ['Asset Repair', 'Incident Report']) {
      expect(w.html()).not.toContain(raw)
    }
  })

  it('TC-FE-CONN-14 — bấm «Tạo phiếu sửa chữa» ⇒ push KÈM query điền sẵn thiết bị cha', async () => {
    const w = await mountWith(payload([repairCell()]))

    const btn = w.find('[data-testid="conn-create"]')
    expect(btn.exists()).toBe(true)
    await btn.trigger('click')
    expect(push).toHaveBeenCalledWith({
      path: '/cm/create',
      query: { asset: 'AC-ASSET-2026-00001' },
    })
  })

  it('TC-FE-CONN-15 — prefill nhiều khoá đi đủ; khoá màn tạo KHÔNG đọc bị loại', async () => {
    const w = await mountWith(payload([
      repairCell({
        create_prefill: {
          asset: 'AC-ASSET-2026-00001',
          pm_wo: 'WO-PM-2026-0007',
          // Khoá backend gửi mà CMCreateView không đọc ⇒ chỉ tạo query rác.
          khoa_la: 'rac',
        } as unknown as Record<string, string>,
      }),
    ]))

    await w.find('[data-testid="conn-create"]').trigger('click')
    expect(push).toHaveBeenCalledWith({
      path: '/cm/create',
      query: { asset: 'AC-ASSET-2026-00001', pm_wo: 'WO-PM-2026-0007' },
    })
  })

  it('TC-FE-CONN-16 — prefill thiếu/rỗng/không phải chuỗi ⇒ push KHÔNG kèm query', async () => {
    const cases: Array<Partial<ConnectionItem>> = [
      { create_prefill: undefined },
      { create_prefill: {} },
      { create_prefill: { asset: '   ' } },
      { create_prefill: { asset: undefined } as unknown as Record<string, string> },
      { create_prefill: { asset: null } as unknown as Record<string, string> },
    ]
    for (const over of cases) {
      getConnections.mockReset()
      push.mockReset()
      const w = await mountWith(payload([repairCell(over)]))
      await w.find('[data-testid="conn-create"]').trigger('click')

      expect(push).toHaveBeenCalledWith({ path: '/cm/create' })
      const arg = push.mock.calls[0][0] as Record<string, unknown>
      expect(Object.prototype.hasOwnProperty.call(arg, 'query')).toBe(false)
      expect(JSON.stringify(arg)).not.toContain('undefined')
    }
  })

  it('TC-FE-CONN-17 — thiếu capability route đích ⇒ 0 nút tạo dù backend nói can_create', async () => {
    caps.delete('repair.create')
    const w = await mountWith(payload([repairCell()]))

    expect(w.findAll('[data-testid="conn-create"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Tạo phiếu sửa chữa')
    // Ô vẫn hiện dữ liệu — mất quyền TẠO không được làm mất quyền XEM.
    expect(w.findAll('[data-testid="conn-row"]').length).toBeGreaterThan(0)
  })

  it('TC-FE-CONN-18 — can_create=false ⇒ prefill/hint backend gửi kèm cũng bị bỏ qua', async () => {
    const w = await mountWith(payload([
      repairCell({ can_create: false, create_route_hint: '/cm/create' }),
    ]))

    expect(w.findAll('[data-testid="conn-create"]')).toHaveLength(0)
    expect(push).not.toHaveBeenCalled()
  })

  // ── A10 · «Xem tất cả» dẫn tới danh sách ĐÃ LỌC (AC-CR-91 vòng 5) ──────────
  // Bug đóng ở vòng này: ô ghi "6 phiếu bảo trì" mà bấm «Xem tất cả» ra danh sách
  // TOÀN VIỆN, vì backend phát fieldname (`asset_ref`) còn màn đích đọc `asset`.
  const pmCell = (over: Partial<ConnectionItem> = {}): ConnectionItem => item({
    doctype: 'PM Work Order', label_vi: 'Phiếu bảo trì định kỳ',
    total: 6, truncated: 1,
    items: Array.from({ length: 5 }, (_, i) => row({ name: `WO-PM-${i}`, title: `Phiếu ${i}` })),
    deep_link_filters: { asset_ref: 'AC-ASSET-1' },
    can_create: false, create_route_hint: '',
    ...over,
  })

  it('TC-FE-CONN-19 — ô có bản đồ dịch ⇒ push ĐÚNG khoá màn đích (asset), không phải asset_ref', async () => {
    const w = await mountWith(payload([pmCell()]))

    const seeAll = w.findAll('[data-testid="conn-see-all"]')
    expect(seeAll).toHaveLength(1)
    await seeAll[0].trigger('click')
    expect(push).toHaveBeenCalledTimes(1)
    expect(push).toHaveBeenCalledWith({
      path: '/pm/work-orders', query: { asset: 'AC-ASSET-1' },
    })
  })

  it('TC-FE-CONN-20 — doctype ∈ LIST_TARGET_NO_FILTER ⇒ 0 nút, preview VẪN render', async () => {
    const w = await mountWith(payload([
      item({
        doctype: 'Asset Commissioning',
        label_vi: 'Hồ sơ nghiệm thu', total: 4, truncated: 0,
        items: Array.from({ length: 4 }, (_, i) => row({ name: `AC-${i}`, title: `Nghiệm thu ${i}` })),
        deep_link_filters: { final_asset: 'AC-ASSET-1' },
      }),
      item({
        doctype: 'IMM Critical Spare Watchlist',
        label_vi: 'Theo dõi vật tư trọng yếu', total: 2, truncated: 0,
        items: [row({ name: 'CSW-1', title: 'Cảm biến SpO2' })],
        deep_link_filters: { critical_asset: 'AC-ASSET-1' },
      }),
    ]))

    expect(w.findAll('[data-testid="conn-see-all"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Xem tất cả')
    // Mất NÚT không được làm mất DỮ LIỆU — ô vẫn giữ preview.
    expect(w.findAll('[data-testid="conn-row"]').length).toBe(5)
    expect(w.text()).toContain('Nghiệm thu 0')
  })

  it('TC-FE-CONN-21 — liên kết nội bộ nhiều bản ghi (name: "a,b,c") ⇒ 0 nút', async () => {
    const w = await mountWith(payload([
      item({
        doctype: 'Incident Report', total: 3,
        deep_link_filters: { name: 'IR-1,IR-2,IR-3' },
      }),
    ]))

    expect(w.findAll('[data-testid="conn-see-all"]')).toHaveLength(0)
    expect(push).not.toHaveBeenCalled()
  })

  it('TC-FE-CONN-22 — thiếu capability route đích ⇒ 0 nút «Xem tất cả» (không để route-guard đá)', async () => {
    caps.delete('pm.read')
    const w = await mountWith(payload([pmCell()]))

    expect(w.findAll('[data-testid="conn-see-all"]')).toHaveLength(0)
    // Mất quyền VÀO MÀN không được làm mất quyền XEM ô.
    expect(w.findAll('[data-testid="conn-row"]').length).toBeGreaterThan(0)
  })

  it('TC-FE-CONN-23 — DOM không rò khoá kỹ thuật (asset_ref/final_asset/critical_asset)', async () => {
    const w = await mountWith(payload([
      pmCell(),
      item({
        doctype: 'Asset Commissioning', label_vi: 'Hồ sơ nghiệm thu',
        total: 1, deep_link_filters: { final_asset: 'AC-ASSET-1' },
      }),
      item({
        doctype: 'IMM Critical Spare Watchlist', label_vi: 'Theo dõi vật tư trọng yếu',
        total: 1, deep_link_filters: { critical_asset: 'AC-ASSET-1' },
      }),
    ]))

    const html = w.html()
    for (const leak of ['asset_ref', 'final_asset', 'critical_asset', 'PM Work Order',
      'Asset Commissioning', 'IMM Critical Spare Watchlist']) {
      expect(html, `rò khoá/tên kỹ thuật ra giao diện: ${leak}`).not.toContain(leak)
    }
  })

  // ── A11 · Ô rỗng gộp MỘT dòng/nhóm (AC-CR-93 — INV-CONNFE6-1..8) ───────────
  // Nửa còn lại của lời phàn nàn gốc: tab của 1 thiết bị dựng 19 khối cho 3 ô có dữ
  // liệu. Từ vòng này chỉ ô CÓ dữ liệu được render; ô rỗng vẫn được NÊU TÊN bằng tiếng
  // Việt trong đúng một dòng gộp của CHÍNH nhóm nó — không "ẩn hẳn" (mất phân biệt
  // "chưa có gì" vs "chưa tải"), không toggle (mời bấm vào hư không).
  //
  // Nhãn dưới đây là FIXTURE, không phải bản đồ sản phẩm (SSoT là `connection_meta.LABEL_VI`
  // ở backend, canh bằng INV-CONN-7). Phủ đủ 20 khoá `DOCTYPE_ROUTE` để ca "mọi ô rỗng"
  // dựng được TỪ CHÍNH bản đồ sản phẩm thay vì liệt kê tay.
  const VI: Record<string, string> = {
    'AC Asset': 'Thiết bị',
    'PM Work Order': 'Phiếu bảo trì định kỳ',
    'PM Schedule': 'Kế hoạch bảo trì định kỳ',
    'Asset Repair': 'Phiếu sửa chữa',
    'Firmware Change Request': 'Yêu cầu thay đổi phần mềm nhúng',
    'IMM Asset Calibration': 'Phiếu hiệu chuẩn',
    'IMM Calibration Schedule': 'Kế hoạch hiệu chuẩn',
    'Incident Report': 'Báo cáo sự cố',
    'IMM RCA Record': 'Hồ sơ phân tích nguyên nhân gốc',
    'IMM CAPA Record': 'Hồ sơ hành động khắc phục và phòng ngừa',
    'IMM Compliance Finding': 'Phát hiện tuân thủ',
    'Asset Commissioning': 'Hồ sơ nghiệm thu',
    'Asset Document': 'Hồ sơ thiết bị',
    'Document Request': 'Yêu cầu tài liệu',
    'Asset Transfer': 'Phiếu điều chuyển',
    'Asset Decommission': 'Hồ sơ thanh lý',
    'AC Supplier': 'Nhà cung cấp',
    'IMM Device Model': 'Dòng thiết bị',
    'AC Spare Part': 'Vật tư phụ tùng',
    'IMM Critical Spare Watchlist': 'Theo dõi vật tư trọng yếu',
  }

  /** Ô RỖNG: `total: 0` + 0 dòng preview (khuôn backend AC-CR-87 cho ô không có bản ghi). */
  const emptyCell = (doctype: string, over: Partial<ConnectionItem> = {}): ConnectionItem => item({
    doctype, label_vi: VI[doctype],
    total: 0, truncated: 0, items: [],
    deep_link_filters: {},
    can_create: false, create_route_hint: '',
    ...over,
  })

  /** Ô CÓ dữ liệu: `total = n` + tối đa 5 dòng preview (mã bản ghi trung tính, không rò doctype). */
  const dataCell = (doctype: string, n: number, over: Partial<ConnectionItem> = {}): ConnectionItem => item({
    doctype, label_vi: VI[doctype],
    total: n, truncated: n > 5 ? 1 : 0,
    items: Array.from({ length: Math.min(n, 5) }, (_, i) => row({
      name: `REC-${i}`, title: `${VI[doctype]} số ${i}`,
    })),
    ...over,
  })

  function grouped(
    specs: Array<{ label: string; items: ConnectionItem[] }>,
    over: Partial<ConnectionsPayload> = {},
  ): ConnectionsPayload {
    const all = specs.flatMap(s => s.items)
    return {
      doctype: 'AC Asset',
      name: 'AC-ASSET-2026-00001',
      total: all.reduce((s, i) => s + i.total, 0),
      groups: specs.map(s => ({ label: s.label, label_vi: s.label, items: s.items })),
      ...over,
    }
  }

  /** Khuôn đồ thị `ac_asset_dashboard`: 19 ô / ĐÚNG 3 ô có dữ liệu / 4 nhóm (2 nhóm toàn rỗng). */
  function payload19(emptyOver: Partial<ConnectionItem> = {}): ConnectionsPayload {
    const E = (dt: string) => emptyCell(dt, emptyOver)
    const byAsset = { deep_link_filters: { asset_ref: 'AC-1' } }
    return grouped([
      {
        label: 'Bảo trì và sửa chữa',
        items: [
          dataCell('PM Work Order', 6, byAsset), E('PM Schedule'),
          dataCell('Asset Repair', 3, byAsset), E('Firmware Change Request'),
          E('IMM Critical Spare Watchlist'),
        ],
      },
      {
        label: 'Hiệu chuẩn và tuân thủ',
        items: [
          dataCell('IMM Asset Calibration', 2), E('IMM Calibration Schedule'),
          E('IMM Compliance Finding'), E('IMM CAPA Record'),
        ],
      },
      {
        label: 'Hồ sơ và tài liệu',
        items: [
          E('Asset Document'), E('Document Request'), E('Asset Commissioning'),
          E('Asset Transfer'), E('Asset Decommission'),
        ],
      },
      {
        label: 'Liên quan khác',
        items: [
          E('Incident Report'), E('IMM RCA Record'), E('AC Supplier'),
          E('IMM Device Model'), E('AC Spare Part'),
        ],
      },
    ])
  }

  const summaries = (w: VueWrapper) => w.findAll('[data-testid="conn-empty-summary"]')
  const effectiveCount = (i: ConnectionItem) => i.total

  it('TC-FE-CONN-24 — 19 ô / 3 có dữ liệu ⇒ ĐÚNG 3 conn-item (giảm ≥ 84%), 0 badge "0"', async () => {
    const p = payload19()
    const all = p.groups.flatMap(g => g.items)
    expect(all).toHaveLength(19)
    expect(all.filter(i => effectiveCount(i) > 0)).toHaveLength(3)

    const w = await mountWith(p)

    // Đếm PHẦN TỬ, không đếm chữ: `text().includes('Chưa có')` xanh cả khi 19 ô còn nguyên.
    expect(cells(w)).toHaveLength(3)
    expect(1 - cells(w).length / 19).toBeGreaterThanOrEqual(0.84)
    // Không còn ô nào chỉ để nói "0".
    for (const badge of w.findAll('[data-testid="conn-count"]')) {
      expect(badge.text()).not.toBe('0')
    }
    // Gộp là thuần client ⇒ KHÔNG phát sinh thêm request nào.
    expect(getConnections).toHaveBeenCalledTimes(1)
  })

  it('TC-FE-CONN-25 — mỗi ô rỗng nằm trong ĐÚNG 1 dòng gộp của CHÍNH nhóm nó, khuôn «Chưa có: …»', async () => {
    const p = payload19()
    const w = await mountWith(p)

    const groupsDom = w.findAll('[data-testid="conn-group"]')
    expect(groupsDom).toHaveLength(p.groups.length)

    p.groups.forEach((g, gi) => {
      const dom = groupsDom[gi]
      const own = g.items.filter(i => effectiveCount(i) === 0).map(i => i.label_vi)
      const foreign = p.groups
        .filter((_, j) => j !== gi)
        .flatMap(o => o.items)
        .filter(i => effectiveCount(i) === 0)
        .map(i => i.label_vi)
        .filter(l => !own.includes(l))

      const line = dom.findAll('[data-testid="conn-empty-summary"]')
      expect(line.length, `nhóm ${gi} phải có ≤1 dòng gộp`).toBeLessThanOrEqual(1)
      expect(line).toHaveLength(1)

      const text = line[0].text()
      expect(text).toMatch(/^Chưa có: /)
      for (const label of own) expect(text).toContain(label)
      // Dòng gộp của nhóm này KHÔNG được nuốt nhãn của nhóm khác (mất ngữ cảnh phân loại).
      for (const label of foreign) expect(text).not.toContain(label)
      // Ngăn cách đúng ', ' ⇒ số nhãn = số dấu phẩy + 1.
      expect(text.replace(/^Chưa có: /, '').split(', ')).toHaveLength(own.length)

      // 0 rò tên DocType tiếng Anh — loop trên CHÍNH bản đồ sản phẩm, không liệt kê tay.
      const html = line[0].html()
      for (const dt of Object.keys(DOCTYPE_ROUTE)) {
        expect(html, `rò tên DocType trong dòng gộp: ${dt}`).not.toContain(dt)
      }
    })
  })

  it('TC-FE-CONN-26 — dòng gộp là TEXT TĨNH: 0 nút, 0 link, dù backend gửi can_create + hint hợp lệ', async () => {
    const w = await mountWith(payload19({
      can_create: true,
      create_route_hint: '/cm/create',
      create_prefill: { asset: 'AC-ASSET-2026-00001' },
    }))

    expect(summaries(w).length).toBeGreaterThan(0)
    for (const s of summaries(w)) {
      expect(s.findAll('button')).toHaveLength(0)
      expect(s.findAll('a')).toHaveLength(0)
      expect(s.findAll('[data-testid="conn-row"]')).toHaveLength(0)
      expect(s.findAll('[data-testid="conn-see-all"]')).toHaveLength(0)
      expect(s.findAll('[data-testid="conn-create"]')).toHaveLength(0)
      expect(s.html()).not.toContain('role="button"')
      expect(s.html()).not.toContain('cursor-pointer')
    }
    // ⚠️ SUPERSEDE có chủ đích (AC-CR-105 A7 · blocker STATE #2): assert cũ ở đây là
    // `w.findAll('conn-create').length === 0` trên TOÀN wrapper — nó KHÔNG thuộc đặc tả
    // TC-FE-CONN-26 (`docs/imm-00/07_Testing_QA.md:2251`, phạm vi đúng là "trong MỖI
    // conn-empty-summary", đã giữ nguyên từng chữ ở vòng lặp trên) mà là bản mã hoá của
    // quyết định D-CR93-4 "ô rỗng không còn chỗ treo nút tạo". Quyết định đó loại trừ
    // AC-CR-90 («Tạo từ ngữ cảnh cha» LUÔN nhắm ô count=0) ⇒ giữ nó nghĩa là ship hợp đồng
    // chết. Thay bằng bất biến MẠNH HƠN: chip tồn tại, nhưng KHÔNG ô nào của nó nằm trong
    // dòng gộp — mọi chip phải ở khối SIBLING `conn-empty-actions`.
    const chips = w.findAll('[data-testid="conn-create"]')
    expect(chips.length, 'ô rỗng qua đủ 3 lớp gate ⇒ phải có chip, nếu không test vacuous')
      .toBeGreaterThan(0)
    for (const chip of chips) {
      const holder = chip.element.closest('[data-testid="conn-empty-actions"]')
      expect(holder, 'chip «Tạo …» của ô rỗng phải nằm trong conn-empty-actions').not.toBeNull()
      expect(chip.element.closest('[data-testid="conn-empty-summary"]')).toBeNull()
    }
  })

  it('TC-FE-CONN-27 — ô có total>0 nhưng preview 0 dòng VẪN có ô riêng; 0 ô mang dữ liệu bị nuốt', async () => {
    // (a) Ca hay bị gộp oan: doctype không khai `PREVIEW_FIELDS` ⇒ `items: []` dù total 6.
    //     Vị-từ đọc `total` (KHÔNG `items.length`) nên ô này giữ nguyên chỗ của nó.
    const noPreview = item({
      doctype: 'Asset Repair', label_vi: 'Phiếu sửa chữa',
      total: 6, truncated: 0, items: [], deep_link_filters: {},
    })

    const w1 = await mountWith(grouped([
      { label: 'Bảo trì và sửa chữa', items: [noPreview, emptyCell('PM Schedule'), emptyCell('Document Request')] },
    ]))

    expect(cells(w1)).toHaveLength(1)
    expect(cells(w1)[0].text()).toContain('Phiếu sửa chữa')
    expect(cells(w1)[0].find('[data-testid="conn-count"]').text()).toBe('6')
    const line = w1.find('[data-testid="conn-empty-summary"]')
    expect(line.text()).toBe('Chưa có: Kế hoạch bảo trì định kỳ, Yêu cầu tài liệu')
    expect(line.text()).not.toContain('Phiếu sửa chữa')

    // (b) Bất biến: MỌI ô bị gộp đều có số đếm hiệu lực == 0 (tính từ chính fixture).
    getConnections.mockReset()
    const p = payload19()
    const w2 = await mountWith(p)
    const merged = summaries(w2).map(s => s.text()).join(' | ')
    const swallowed = p.groups.flatMap(g => g.items).filter(i => merged.includes(i.label_vi))
    expect(swallowed).toHaveLength(16)
    expect(swallowed.reduce((s, i) => s + effectiveCount(i), 0)).toBe(0)
  })

  it('TC-FE-CONN-28 — nhóm toàn rỗng: 0 conn-item, 0 tiêu đề nhóm, ĐÚNG 1 dòng gộp', async () => {
    const w = await mountWith(grouped([
      { label: 'Bảo trì và sửa chữa', items: [dataCell('PM Work Order', 2), emptyCell('PM Schedule')] },
      { label: 'Hiệu chuẩn và tuân thủ', items: [dataCell('IMM Asset Calibration', 1)] },
      { label: 'Hồ sơ và tài liệu', items: [emptyCell('Asset Document'), emptyCell('Document Request')] },
    ]))

    // Số tiêu đề nhóm == số nhóm có ≥1 ô có dữ liệu (2/3).
    expect(w.findAll('[data-testid="conn-group-label"]')).toHaveLength(2)

    const groupsDom = w.findAll('[data-testid="conn-group"]')
    expect(groupsDom).toHaveLength(3)
    const allEmpty = groupsDom[2]
    expect(allEmpty.findAll('[data-testid="conn-item"]')).toHaveLength(0)
    expect(allEmpty.findAll('[data-testid="conn-group-label"]')).toHaveLength(0)
    expect(allEmpty.findAll('[data-testid="conn-empty-summary"]')).toHaveLength(1)
    expect(allEmpty.text()).toBe('Chưa có: Hồ sơ thiết bị, Yêu cầu tài liệu')
    // Tiêu đề nhóm rỗng không được lọt vào DOM (1 dòng mang 0 thông tin mới).
    expect(w.text()).not.toContain('Hồ sơ và tài liệu')
  })

  it('TC-FE-CONN-29 — MỌI ô rỗng (20 doctype): câu tiếng Việt + dòng gộp cùng tồn tại, expose total 0', async () => {
    const keys = Object.keys(DOCTYPE_ROUTE)
    expect(keys.length).toBeGreaterThanOrEqual(20)
    for (const dt of keys) expect(VI[dt], `fixture thiếu nhãn VI cho ${dt}`).toBeTruthy()

    const p = grouped([
      { label: 'Nhóm một', items: keys.slice(0, 7).map(dt => emptyCell(dt)) },
      { label: 'Nhóm hai', items: keys.slice(7, 14).map(dt => emptyCell(dt)) },
      { label: 'Nhóm ba', items: keys.slice(14).map(dt => emptyCell(dt)) },
    ])
    const w = await mountWith(p)

    expect(cells(w)).toHaveLength(0)
    expect(w.text()).toContain('Chưa có bản ghi nào liên quan tới hồ sơ này.')
    expect(summaries(w).length).toBeGreaterThanOrEqual(1)
    expect((w.vm as unknown as { total: number }).total).toBe(0)
    // Không mất thông tin: mọi nhãn VI vẫn được nêu tên.
    const merged = summaries(w).map(s => s.text()).join(' | ')
    for (const dt of keys) expect(merged).toContain(VI[dt])
    // 0 tiêu đề nhóm (không nhóm nào có dữ liệu) và 0 rò tên DocType tiếng Anh.
    expect(w.findAll('[data-testid="conn-group-label"]')).toHaveLength(0)
    const html = w.html()
    for (const dt of keys) expect(html, `rò tên DocType: ${dt}`).not.toContain(dt)
  })

  it('TC-FE-CONN-30 — đang tải / lỗi / groups rỗng ⇒ TUYỆT ĐỐI không dòng gộp nào', async () => {
    // Đang tải: chưa biết gì thì không được nói "chưa có".
    let release: (v: unknown) => void = () => {}
    getConnections.mockReturnValue(new Promise(res => { release = res }))
    const wLoading = mountIt()
    await flushPromises()
    expect(wLoading.text()).toContain('Đang tải')
    expect(summaries(wLoading)).toHaveLength(0)
    release(payload19())
    await flushPromises()

    // Lỗi: dòng gộp sẽ là lời khẳng định sai về dữ liệu chưa tải được.
    getConnections.mockReset()
    getConnections.mockRejectedValueOnce(new Error('Mất kết nối'))
    const wError = mountIt()
    await flushPromises()
    expect(summaries(wError)).toHaveLength(0)
    expect(wError.findAll('button').some(b => b.text().includes('Thử lại'))).toBe(true)

    // groups: [] ⇒ chỉ câu tiếng Việt (hành vi vòng 2, giữ nguyên).
    getConnections.mockReset()
    const wEmpty = await mountWith(payload([], { groups: [], total: 0 }))
    expect(wEmpty.text()).toContain('Chưa có bản ghi nào liên quan tới hồ sơ này.')
    expect(summaries(wEmpty)).toHaveLength(0)
    expect(wEmpty.findAll('[data-testid="conn-group"]')).toHaveLength(0)
  })

  // ── A12 · «Tạo từ ngữ cảnh cha» cho ô 0 bản ghi (AC-CR-105 — INV-CONN4-1..3) ─
  // Nghịch lý mà vòng này đóng: thứ người dùng cần TẠO gần như luôn là thứ CHƯA CÓ, tức ô
  // `total === 0` — đúng những ô mà AC-CR-93 gộp vào một dòng text tĩnh. Hệ quả trước vòng
  // này: cả tính năng «Tạo từ ngữ cảnh cha» thành nút chết (0 chỗ treo). Lời hứa "dòng gộp
  // 0 nút" KHÔNG bị nới: chip sống ở khối SIBLING `conn-empty-actions`, ngoài thẻ `<p>`.
  //
  // Số hiệu TC theo sổ vòng AC-CR-105 (TC-FE-CONN4-xx) — hệ `TC-FE-CONN-xx` giữ nguyên cho
  // các vòng trước để không đánh số lại lịch sử.
  const actions = (w: VueWrapper) => w.findAll('[data-testid="conn-empty-actions"]')
  const chipsOf = (w: VueWrapper) => w.findAll('[data-testid="conn-create"]')

  /** Ô RỖNG nhưng ĐƯỢC PHÉP tạo — backend gửi đủ hint + prefill (hợp đồng AC-CR-105). */
  const emptyCreatable = (doctype: string, over: Partial<ConnectionItem> = {}): ConnectionItem =>
    emptyCell(doctype, {
      can_create: true,
      create_route_hint: '/cm/create',
      create_prefill: { asset: 'AC-ASSET-2026-00042' },
      ...over,
    })

  it('TC-FE-CONN4-12 — ô rỗng + can_create ⇒ ĐÚNG 1 chip, trong khối SIBLING của dòng gộp', async () => {
    const w = await mountWith(grouped([
      {
        label: 'Bảo trì và sửa chữa',
        items: [dataCell('PM Work Order', 2), emptyCreatable('Asset Repair')],
      },
    ]))

    // Đúng 1 chip cho đúng 1 ô rỗng đủ điều kiện (không nhân bản, không mọc thêm cho ô có dữ liệu).
    expect(chipsOf(w)).toHaveLength(1)
    expect(actions(w)).toHaveLength(1)
    expect(chipsOf(w)[0].text()).toContain('Tạo phiếu sửa chữa')

    const summary = w.find('[data-testid="conn-empty-summary"]')
    expect(summary.exists()).toBe(true)
    // SIBLING, không phải CON: cùng cha `conn-group`, và khối chip đứng NGAY SAU thẻ `<p>`.
    expect(actions(w)[0].element.parentElement).toBe(summary.element.parentElement)
    expect(summary.element.nextElementSibling).toBe(actions(w)[0].element)
    expect(summary.element.contains(chipsOf(w)[0].element)).toBe(false)
    // Ô có dữ liệu vẫn giữ khối hành động RIÊNG của nó (2 đường không trộn vào nhau).
    expect(cells(w)).toHaveLength(1)
    expect(cells(w)[0].findAll('[data-testid="conn-create"]')).toHaveLength(0)
  })

  it('TC-FE-CONN4-13 — REGRESSION TC-FE-CONN-26 dưới fixture 19 ô: dòng gộp vẫn 0 nút/0 link', async () => {
    const w = await mountWith(payload19({
      can_create: true,
      create_route_hint: '/cm/create',
      create_prefill: { asset: 'AC-ASSET-2026-00042' },
    }))

    // Non-vacuous: fixture này PHẢI sinh chip, nếu không phần dưới chấm trên hư không.
    expect(chipsOf(w).length).toBeGreaterThan(0)
    expect(summaries(w).length).toBeGreaterThan(0)
    for (const s of summaries(w)) {
      expect(s.findAll('button')).toHaveLength(0)
      expect(s.findAll('a')).toHaveLength(0)
      expect(s.findAll('[data-testid="conn-row"]')).toHaveLength(0)
      expect(s.findAll('[data-testid="conn-see-all"]')).toHaveLength(0)
      expect(s.findAll('[data-testid="conn-create"]')).toHaveLength(0)
      expect(s.html()).not.toContain('role="button"')
      expect(s.html()).not.toContain('cursor-pointer')
    }
    // Mỗi khối chip nằm trong CHÍNH nhóm của nó (không dồn hết xuống nhóm cuối).
    for (const grp of w.findAll('[data-testid="conn-group"]')) {
      const inGroup = grp.findAll('[data-testid="conn-empty-actions"]')
      expect(inGroup.length).toBeLessThanOrEqual(1)
      for (const chip of grp.findAll('[data-testid="conn-create"]')) {
        expect(grp.element.contains(chip.element)).toBe(true)
      }
    }
  })

  it('TC-FE-CONN4-14 — bấm chip ⇒ ĐÚNG 1 push tới màn tạo kèm query thiết bị cha', async () => {
    const w = await mountWith(grouped([
      { label: 'Bảo trì và sửa chữa', items: [emptyCreatable('Asset Repair')] },
    ]))

    await chipsOf(w)[0].trigger('click')
    expect(push).toHaveBeenCalledTimes(1)
    expect(push).toHaveBeenCalledWith({
      path: '/cm/create',
      query: { asset: 'AC-ASSET-2026-00042' },
    })
  })

  it('TC-FE-CONN4-15 — prefill rỗng / VẮNG MẶT (worker chưa reload) ⇒ push TRẦN, 0 dấu "?"', async () => {
    const cases: Array<Partial<ConnectionItem>> = [
      { create_prefill: {} },
      // Ca hợp đồng CHƯA tới: backend cũ không phát khoá thứ 10 ⇒ chip vẫn phải bấm được.
      { create_prefill: undefined },
    ]
    for (const over of cases) {
      getConnections.mockReset()
      push.mockReset()
      const w = await mountWith(grouped([
        { label: 'Bảo trì và sửa chữa', items: [emptyCreatable('Asset Repair', over)] },
      ]))

      expect(chipsOf(w), `prefill ${JSON.stringify(over)} ⇒ chip vẫn phải có`).toHaveLength(1)
      await chipsOf(w)[0].trigger('click')
      expect(push).toHaveBeenCalledTimes(1)
      const arg = push.mock.calls[0][0] as Record<string, unknown>
      expect(arg).toEqual({ path: '/cm/create' })
      expect(Object.prototype.hasOwnProperty.call(arg, 'query')).toBe(false)
      expect(JSON.stringify(arg)).not.toContain('undefined')
    }
  })

  it('TC-FE-CONN4-16 — khoá ngoài allowlist bị loại im lặng; giá trị có dấu phẩy cũng bị loại', async () => {
    getConnections.mockReset()
    const w = await mountWith(grouped([
      {
        label: 'Bảo trì và sửa chữa',
        items: [emptyCreatable('Asset Repair', {
          create_prefill: {
            asset: 'AC-ASSET-2026-00042',
            // Fieldname của BE (KHÔNG phải khoá URL màn tạo đọc) ⇒ chỉ tạo query rác.
            asset_ref: 'AC-ASSET-2026-00042',
            pm_wo: 'WO-PM-2026-0007',
          },
        })],
      },
    ]))

    await chipsOf(w)[0].trigger('click')
    expect(push).toHaveBeenCalledWith({
      path: '/cm/create',
      query: { asset: 'AC-ASSET-2026-00042', pm_wo: 'WO-PM-2026-0007' },
    })
    expect(JSON.stringify(push.mock.calls[0][0])).not.toContain('asset_ref')

    // Dấu phẩy = tập nhiều bản ghi (ADR §D7) — không màn tạo nào điền được.
    getConnections.mockReset()
    push.mockReset()
    const w2 = await mountWith(grouped([
      {
        label: 'Bảo trì và sửa chữa',
        items: [emptyCreatable('Asset Repair', { create_prefill: { asset: 'A-1,A-2' } })],
      },
    ]))
    await chipsOf(w2)[0].trigger('click')
    expect(push).toHaveBeenCalledWith({ path: '/cm/create' })
  })

  it('TC-FE-CONN4-17 — fail-CLOSED: route không có thật / thiếu capability ⇒ 0 chip', async () => {
    // (a) Backend gợi ý route FE chưa có ⇒ không dẫn tới 404.
    const wGhost = await mountWith(grouped([
      {
        label: 'Bảo trì và sửa chữa',
        items: [emptyCreatable('Asset Repair', { create_route_hint: '/route/khong-ton-tai' })],
      },
    ]))
    expect(chipsOf(wGhost)).toHaveLength(0)
    expect(actions(wGhost)).toHaveLength(0)
    // Mất chip KHÔNG được làm mất tên ô trong câu «Chưa có: …» (A9).
    expect(wGhost.find('[data-testid="conn-empty-summary"]').text()).toContain('Phiếu sửa chữa')

    // (b) Phiên thiếu capability của CHÍNH route đích ⇒ không mời người dùng vào /unauthorized.
    getConnections.mockReset()
    caps.delete('repair.create')
    const wNoCap = await mountWith(grouped([
      { label: 'Bảo trì và sửa chữa', items: [emptyCreatable('Asset Repair')] },
    ]))
    expect(chipsOf(wNoCap)).toHaveLength(0)
    expect(actions(wNoCap)).toHaveLength(0)
    expect(wNoCap.text()).not.toContain('Tạo phiếu sửa chữa')
    expect(push).not.toHaveBeenCalled()
  })

  it('TC-FE-CONN4-18 — A9 không mất ô: mọi ô rỗng vẫn được nêu tên, kể cả ô ĐÃ có chip', async () => {
    const p = grouped([
      {
        label: 'Bảo trì và sửa chữa',
        items: [
          dataCell('PM Work Order', 4),
          emptyCreatable('Asset Repair'),                 // ô rỗng CÓ chip
          emptyCell('PM Schedule'),                       // ô rỗng KHÔNG chip
          emptyCell('Firmware Change Request'),
        ],
      },
    ])
    const w = await mountWith(p)

    const group = p.groups[0]
    const dataDom = w.findAll('[data-testid="conn-item"]')
    const named = w.find('[data-testid="conn-empty-summary"]').text()
      .replace(/^Chưa có: /, '').split(', ')

    // Bất biến đếm: mỗi ô thuộc ĐÚNG một nhánh (không đếm 2 lần, không sót ô).
    expect(dataDom.length + named.length).toBe(group.items.length)
    for (const it of group.items) {
      const inData = dataDom.some(c => c.text().includes(it.label_vi))
      const inNamed = named.includes(it.label_vi)
      expect(inData !== inNamed, `ô '${it.label_vi}' phải ở đúng 1 nhánh`).toBe(true)
    }
    // Ô có chip KHÔNG bị xoá khỏi câu — chip là LỐI ĐI THÊM, không phải thay thế thông tin.
    expect(named).toContain('Phiếu sửa chữa')
    expect(chipsOf(w)).toHaveLength(1)
  })
})
