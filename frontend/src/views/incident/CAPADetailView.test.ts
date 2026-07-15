// TDD — IMM-16 CAPADetailView.
//
// (A) Field "Xác minh hiệu quả" render nhãn VI (không leak English) — i18n leak guard.
//     effectiveness_check='Not Effective' → DOM 'Không hiệu quả' (KHÔNG 'Not Effective').
//     effectiveness_check=null → '— (chưa xác minh)' (no regress).
//
// (B) Header surface lifecycle SoT `status` (Overdue/Closed) BÊN CẠNH workflow_state
//     (stage) — detail phải khớp list+DB+API, invariant dưới cron check_capa_overdue.
//     TDD-1..5 (xem task). Nút transition vẫn dựa workflow_state (no regression).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { CapaDetail } from '@/api/imm16'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'CAPA-2026-00001' } }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

// useApi: api.run trả về kết quả fn; api.loading là ref-like.
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    loading: { value: false },
    run: (fn: () => Promise<unknown>) => fn(),
  }),
}))

const fetchCapaDetailSpy = vi.fn<() => Promise<CapaDetail>>()
vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    fetchCapaDetail: fetchCapaDetailSpy,
    actionUpdateCapaFields: vi.fn(),
    actionAdvanceCapa: vi.fn(),
    actionEffectivenessCheck: vi.fn(),
  }),
}))

import CAPADetailView from './CAPADetailView.vue'

// StatusBadge KHÔNG stub — phải render label SSoT thật để bắt English-leak (GATE-1).
const stubs = {
  BaseModal: true, SkeletonLoader: true, RecordHistory: true, RouterLink: true,
}

function baseCapa(overrides: Partial<CapaDetail>): CapaDetail {
  return {
    name: 'CAPA-2026-00001',
    asset: 'ACC-ASS-0001',
    severity: 'High',
    status: 'Open',
    workflow_state: 'Verification',
    source_type: 'Finding',
    source_ref: null,
    due_date: null,
    closed_date: null,
    effectiveness_check: null,
    ...overrides,
  } as CapaDetail
}

describe('CAPADetailView — Xác minh hiệu quả (i18n leak guard)', () => {
  beforeEach(() => { fetchCapaDetailSpy.mockReset() })

  it("effectiveness_check='Not Effective' → DOM 'Không hiệu quả', KHÔNG 'Not Effective'", async () => {
    fetchCapaDetailSpy.mockResolvedValue(baseCapa({ effectiveness_check: 'Not Effective' }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Không hiệu quả')
    expect(html).not.toContain('Not Effective')
  })

  it("effectiveness_check='Effective' → DOM 'Hiệu quả', KHÔNG raw 'Effective'", async () => {
    fetchCapaDetailSpy.mockResolvedValue(baseCapa({ effectiveness_check: 'Effective' }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Hiệu quả')
    // 'Effective' không được render trực tiếp (nhãn VI 'Hiệu quả' không chứa token EN).
    expect(html).not.toMatch(/>[^<]*\bEffective\b/)
  })

  it('effectiveness_check=null → "— (chưa xác minh)" (no regress)', async () => {
    fetchCapaDetailSpy.mockResolvedValue(baseCapa({ effectiveness_check: null }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.html()).toContain('— (chưa xác minh)')
  })
})

describe('CAPADetailView — header lifecycle status badge (SoT, cron-flip invariant)', () => {
  beforeEach(() => { fetchCapaDetailSpy.mockReset() })

  // TDD-1: lifecycle status 'Overdue' phải được surface ở header.
  it("TDD-1 status='Overdue', workflow_state='Investigating' → header chứa 'Quá hạn'", async () => {
    fetchCapaDetailSpy.mockResolvedValue(
      baseCapa({ status: 'Overdue', workflow_state: 'Investigating' }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.html()).toContain('Quá hạn')
  })

  // TDD-2 INVARIANT cron-flip: cùng fixture → KHÔNG còn 'Đang điều tra' là trạng thái
  // DUY NHẤT; lifecycle badge 'Quá hạn' (capa.status) cùng tồn tại.
  it("TDD-2 cron-flip: cả 'Quá hạn' (lifecycle) lẫn 'Đang điều tra' (stage) đều hiện", async () => {
    fetchCapaDetailSpy.mockResolvedValue(
      baseCapa({ status: 'Overdue', workflow_state: 'Investigating' }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Quá hạn')        // lifecycle SoT (khớp CAPAListView)
    expect(html).toContain('Đang điều tra')   // workflow stage (drive transitions)
  })

  // TDD-3 Closed: header 'Đã đóng' + isClosed=true vẫn ẩn nút transition.
  it("TDD-3 status='Closed', workflow_state='Closed' → 'Đã đóng', ẩn nút transition", async () => {
    fetchCapaDetailSpy.mockResolvedValue(
      baseCapa({ status: 'Closed', workflow_state: 'Closed' }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Đã đóng')
    // Workflow_state='Closed' → TRANSITIONS không có → 0 nút transition, không nút Sửa.
    expect(html).not.toContain('Lập kế hoạch hành động')
    expect(html).not.toContain('Bắt đầu điều tra')
    expect(html).not.toContain('Sửa nội dung')
  })

  // TDD-4 happy path: stage 'Đang điều tra' + lifecycle 'Đang mở'; nút transition của
  // Investigating ('Lập kế hoạch hành động') render theo allowed_transitions (server-driven).
  it("TDD-4 status='Open', workflow_state='Investigating' → 'Đang điều tra' + 'Đang mở' + nút transition", async () => {
    fetchCapaDetailSpy.mockResolvedValue(
      baseCapa({ status: 'Open', workflow_state: 'Investigating',
                 allowed_transitions: ['Action Plan'] }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Đang điều tra')   // stage
    expect(html).toContain('Đang mở')          // lifecycle
    expect(html).toContain('Lập kế hoạch hành động')  // transition của Investigating
  })

  // TDD-5 no-English-leak (GATE-1): header KHÔNG chứa raw EN tokens.
  it("TDD-5 GATE-1: header KHÔNG leak raw 'Overdue'/'Closed'/'Investigating'", async () => {
    fetchCapaDetailSpy.mockResolvedValue(
      baseCapa({ status: 'Overdue', workflow_state: 'Investigating' }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    // Strip HTML comments — chỉ soi nội dung user thấy được (comment mã nguồn
    // như "isClosed" không phải English-leak ra UI).
    const visible = wrapper.html().replace(/<!--[\s\S]*?-->/g, '')
    expect(visible).not.toContain('Overdue')
    expect(visible).not.toContain('Investigating')
    expect(visible).not.toContain('Closed')
  })
})

describe('CAPADetailView — Mức rủi ro imm_risk_level i18n (GATE-1, TDD-4)', () => {
  beforeEach(() => { fetchCapaDetailSpy.mockReset() })

  // TDD-4: imm_risk_level='Critical' → 'Khẩn cấp', KHÔNG raw 'Critical'.
  it("imm_risk_level='Critical' → 'Khẩn cấp', KHÔNG raw 'Critical'", async () => {
    fetchCapaDetailSpy.mockResolvedValue(
      baseCapa({ severity: 'Minor', imm_risk_level: 'Critical', imm_reopen_count: 2 }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    const visible = wrapper.html().replace(/<!--[\s\S]*?-->/g, '')
    expect(visible).toContain('Khẩn cấp')
    // Dòng 'Mức rủi ro' KHÔNG render raw EN 'Critical' (severity Minor → 'Nhỏ' nên
    // 'Khẩn cấp' chỉ có thể đến từ imm_risk_level qua translateStatus).
    expect(visible).not.toMatch(/>[^<]*\bCritical\b/)
    // Giữ phần '· N lần' reopen.
    expect(visible).toContain('2 lần')
  })

  it("imm_risk_level='High' → 'Cao' (SSoT), KHÔNG raw 'High'", async () => {
    fetchCapaDetailSpy.mockResolvedValue(
      baseCapa({ severity: 'Minor', imm_risk_level: 'High' }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    const visible = wrapper.html().replace(/<!--[\s\S]*?-->/g, '')
    expect(visible).toContain('Cao')
    expect(visible).not.toMatch(/>[^<]*\bHigh\b/)
  })

  it('imm_risk_level=null → "—" (no regress)', async () => {
    fetchCapaDetailSpy.mockResolvedValue(
      baseCapa({ imm_risk_level: undefined, imm_reopen_count: 0 }))
    const wrapper = mount(CAPADetailView, { global: { stubs } })
    await flushPromises()
    // Dòng 'Mức rủi ro / Reopen' = '— · 0 lần'.
    expect(wrapper.html()).toContain('— · 0 lần')
  })
})
