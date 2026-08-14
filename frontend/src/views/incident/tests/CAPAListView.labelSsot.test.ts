// TDD — IMM-16/IMM-00 CAPA label SSoT consolidation (LL-FE-30 + GATE-1).
//
// CAPAListView status + severity labels PHẢI render qua formatters.ts SSoT
// (translateStatus / StatusBadge) — KHÔNG dùng map cục bộ (STATUS_LABEL/SEV_LABEL).
// Byte-for-byte parity: nhãn list == nhãn StatusBadge(translateStatus) == detail.
//
//   TDD-2: 1 CAPA mỗi status {Open,In Progress,Pending Verification,Closed,Overdue}
//          → nhãn badge == translateStatus(code) (KHÔNG 'Mới mở', KHÔNG 'Đang xử lý').
//   TDD-3: 1 CAPA mỗi severity {Critical,Major,Minor}
//          → nhãn mức độ == translateStatus(severity) (Critical→'Khẩn cấp').
//   TDD-5: parity cross-view — nhãn list == StatusBadge(translateStatus) cùng code.
//   TDD-6: regression behavior — click badge status vẫn emit quickFilter với CODE EN.
//   TDD-7: RED-experiment (ghi lại) — đặt nhãn cục bộ sai → TDD-3/TDD-5 FAIL.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { translateStatus } from '@/utils/formatters'

const routeQuery = ref<Record<string, string>>({})
const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

interface CapaRow { name: string; status: string; severity: string; due_date?: string; asset?: string; asset_name?: string }
const capasRef = ref<CapaRow[]>([])
const fetchListSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm00', () => ({
  useCapaStore: () => ({
    get capas() { return capasRef.value },
    pagination: { page: 1, page_size: 20, total: capasRef.value.length, total_pages: 1 },
    loading: false,
    error: null,
    fetchList: fetchListSpy,
  }),
}))

import CAPAListView from '@/views/incident/CAPAListView.vue'

// StatusBadge KHÔNG stub — phải render nhãn SSoT thật để bắt drift/leak.
const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, SkeletonLoader: true, RouterLink: true,
}

const STATUS_CODES = ['Open', 'In Progress', 'Pending Verification', 'Closed', 'Overdue'] as const
const SEVERITY_CODES = ['Critical', 'Major', 'Minor'] as const

function mountWith(rows: CapaRow[]) {
  capasRef.value = rows
  return mount(CAPAListView, { global: { stubs } })
}

describe('CAPAListView — status label SSoT (TDD-2)', () => {
  beforeEach(() => { fetchListSpy.mockClear(); pushSpy.mockClear(); routeQuery.value = {} })

  it('mỗi status render nhãn == translateStatus(code)', async () => {
    const rows = STATUS_CODES.map((s, i) => ({
      name: `CAPA-${i}`, status: s, severity: 'Minor', due_date: '2026-01-01',
    }))
    const wrapper = mountWith(rows)
    await flushPromises()
    const html = wrapper.html()
    for (const code of STATUS_CODES) {
      expect(html, `thiếu nhãn SSoT cho "${code}"`).toContain(translateStatus(code))
    }
  })

  it("KHÔNG còn nhãn cục bộ cũ 'Mới mở' / 'Đang xử lý' (drift LL-FE-30)", async () => {
    const rows = [
      { name: 'C1', status: 'Open', severity: 'Minor', due_date: '2026-01-01' },
      { name: 'C2', status: 'In Progress', severity: 'Minor', due_date: '2026-01-01' },
    ]
    const wrapper = mountWith(rows)
    await flushPromises()
    const html = wrapper.html()
    expect(html).not.toContain('Mới mở')
    expect(html).not.toContain('Đang xử lý')
    expect(html).toContain('Đang mở')        // Open SSoT
    expect(html).toContain('Đang thực hiện')  // In Progress SSoT
  })

  it("GATE-1: KHÔNG leak raw EN status token ra UI", async () => {
    const rows = STATUS_CODES.map((s, i) => ({
      name: `CAPA-${i}`, status: s, severity: 'Major', due_date: '2026-01-01',
    }))
    const wrapper = mountWith(rows)
    await flushPromises()
    const visible = wrapper.html().replace(/<!--[\s\S]*?-->/g, '')
    // 'In Progress' / 'Pending Verification' / 'Overdue' không được render trực tiếp.
    expect(visible).not.toContain('In Progress')
    expect(visible).not.toContain('Pending Verification')
    expect(visible).not.toContain('Overdue')
  })
})

describe('CAPAListView — severity label SSoT (TDD-3)', () => {
  beforeEach(() => { fetchListSpy.mockClear(); pushSpy.mockClear(); routeQuery.value = {} })

  it('mỗi severity render nhãn == translateStatus(severity)', async () => {
    const rows = SEVERITY_CODES.map((sev, i) => ({
      name: `CAPA-${i}`, status: 'Open', severity: sev, due_date: '2026-01-01',
    }))
    const wrapper = mountWith(rows)
    await flushPromises()
    const html = wrapper.html()
    expect(translateStatus('Critical')).toBe('Khẩn cấp')   // chốt SSoT
    expect(translateStatus('Major')).toBe('Nghiêm trọng')
    expect(translateStatus('Minor')).toBe('Nhỏ')
    for (const sev of SEVERITY_CODES) {
      expect(html, `thiếu nhãn SSoT cho severity "${sev}"`).toContain(translateStatus(sev))
    }
  })

  it("KHÔNG còn nhãn cục bộ cũ Critical='Nghiêm trọng' / Major='Quan trọng'", async () => {
    const wrapper = mountWith([{ name: 'C1', status: 'Open', severity: 'Critical', due_date: '2026-01-01' }])
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Khẩn cấp')      // Critical SSoT
    expect(html).not.toContain('Quan trọng') // nhãn Major cũ không xuất hiện
  })
})

describe('CAPAListView — parity cross-view (TDD-5)', () => {
  beforeEach(() => { fetchListSpy.mockClear(); pushSpy.mockClear(); routeQuery.value = {} })

  it('nhãn list của CÙNG code == translateStatus(code) cho cả status + severity', async () => {
    const rows = [
      { name: 'C1', status: 'Overdue', severity: 'Critical', due_date: '2026-01-01' },
      { name: 'C2', status: 'Pending Verification', severity: 'Major', due_date: '2026-01-01' },
    ]
    const wrapper = mountWith(rows)
    await flushPromises()
    const html = wrapper.html()
    // Detail badge ('Trạng thái'/'Mức độ') dùng StatusBadge → translateStatus. List
    // phải khớp byte-for-byte → so trực tiếp với translateStatus output.
    expect(html).toContain(translateStatus('Overdue'))               // 'Quá hạn'
    expect(html).toContain(translateStatus('Critical'))              // 'Khẩn cấp'
    expect(html).toContain(translateStatus('Pending Verification'))  // 'Chờ xác minh'
    expect(html).toContain(translateStatus('Major'))                 // 'Nghiêm trọng'
  })
})

describe('CAPAListView — quick-filter behavior regression (TDD-6)', () => {
  beforeEach(() => { fetchListSpy.mockClear(); pushSpy.mockClear(); routeQuery.value = {} })

  it('click badge status vẫn fetchList với status CODE English (không phải nhãn VI)', async () => {
    const wrapper = mountWith([{ name: 'C1', status: 'In Progress', severity: 'Minor', due_date: '2026-01-01' }])
    await flushPromises()
    fetchListSpy.mockClear()
    // Desktop badge nằm trong button quick-filter (cột Trạng thái).
    const buttons = wrapper.findAll('button')
    const statusBtn = buttons.find(b => b.attributes('title')?.includes('Lọc'))
    expect(statusBtn, 'không tìm thấy nút quick-filter status').toBeTruthy()
    await statusBtn!.trigger('click')
    await flushPromises()
    // Filter value PHẢI là CODE English 'In Progress', KHÔNG phải 'Đang thực hiện'.
    const sawCode = fetchListSpy.mock.calls.some(
      c => (c[0] as Record<string, unknown> | undefined)?.status === 'In Progress')
    expect(sawCode).toBe(true)
    const sawLabel = fetchListSpy.mock.calls.some(
      c => (c[0] as Record<string, unknown> | undefined)?.status === 'Đang thực hiện')
    expect(sawLabel).toBe(false)
  })
})

// TDD-7 (RED-experiment, ghi lại): nếu tạm đặt nhãn cục bộ sai trong CAPAListView
// (vd Critical='Nghiêm trọng' qua SEV_LABEL cũ thay vì StatusBadge SSoT), thì
// TDD-3 ("Khẩn cấp" + not 'Quan trọng') và TDD-5 (parity translateStatus('Critical')
// === 'Khẩn cấp') FAIL đúng symptom: list hiển thị 'Nghiêm trọng' cho Critical
// → toContain('Khẩn cấp') FAIL. Restore StatusBadge SSoT → GREEN. Chứng minh guard
// không false-green (đã chạy thủ công khi phát triển — xem báo cáo run).
