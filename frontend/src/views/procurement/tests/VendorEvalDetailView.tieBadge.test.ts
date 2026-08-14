// TDD/regression — IMM-03 cổng tie-break chấm điểm NCC (INV-VE-TIE §IV.7 / NĐ98), phía FE.
//
// Hợp đồng FE (ZERO shape-change ngoài đọc thêm has_top_tie/tied_candidates):
// BE quyết định tie — FE BIND VERBATIM, KHÔNG tự suy tie từ weighted_score.
//
// Bài test chốt các bất biến FE của VendorEvalDetailView:
//   1. recommended rỗng + has_top_tie=1 → render badge 'Hòa điểm — cần quyết định
//      thủ công' + liệt kê tied_candidates (theo TÊN, không leak mã); KHÔNG '—' câm.
//   2. Khi KHÔNG tie → KHÔNG render badge; chỉ 1 dòng được gắn 'Gợi ý trúng thầu'.
//   3. Chỉ các dòng đồng hạng nhất được highlight (.tied); candidate thấp hơn KHÔNG.
//   4. i18n VI qua SSoT formatters — KHÔNG leak raw EN state/code.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { EvalDoc } from '@/types/imm03'

// ─── API mocks (store dùng `import * as api`, view import named) ─────────────────
const getEvaluationSpy = vi.fn<() => Promise<EvalDoc>>()

vi.mock('@/api/imm03', () => ({
  getEvaluation: () => getEvaluationSpy(),
  scoreEvaluation: vi.fn(),
  addCandidate: vi.fn(),
  submitQuotations: vi.fn(),
  transitionEvalWorkflow: vi.fn(),
  getVendorScorecard: vi.fn(),
  listVendorProfiles: vi.fn().mockResolvedValue({ items: [] }),
}))

// ─── notification-contract mock ─────────────────────────────────────────────────
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({
    confirm: vi.fn().mockResolvedValue(true),
    fromError: vi.fn(),
    show: vi.fn(),
    fromOk: vi.fn(),
  }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'VE-0001' } }),
  // Lô 2: view lấy `router.push` để nối `@back` của DetailPageShell (lối thoát khi 403/404).
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

import VendorEvalDetailView from '@/views/procurement/VendorEvalDetailView.vue'

const BASE: EvalDoc = {
  name: 'VE-0001',
  spec_ref: 'TS-0001',
  draft_date: '2026-06-04',
  candidates: [],
  quotations: [],
  criteria: [],
  workflow_state: 'Quotation Received',
  docstatus: 0,
}

const stubs = { teleport: true }

async function mountView() {
  const wrapper = mount(VendorEvalDetailView, {
    props: { id: 'VE-0001' },
    global: { stubs, mocks: { $router: { back: vi.fn(), push: vi.fn() } } },
  })
  await flushPromises()
  return wrapper
}

describe('IMM-03 VendorEvalDetailView — tie badge (INV-VE-TIE)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getEvaluationSpy.mockReset()
  })

  it('HÒA đỉnh: recommended rỗng + has_top_tie=1 → render badge + list tied (theo tên)', async () => {
    getEvaluationSpy.mockResolvedValue({
      ...BASE,
      recommended_candidate: '',
      has_top_tie: 1,
      tied_candidates: 'SUP-A,SUP-B',
      candidates: [
        { idx: 1, supplier: 'SUP-A', supplier_name: 'NCC Alpha', in_avl: 1, weighted_score: 4.5 },
        { idx: 2, supplier: 'SUP-B', supplier_name: 'NCC Beta', in_avl: 1, weighted_score: 4.5 },
      ],
    })
    const wrapper = await mountView()
    const html = wrapper.html()

    // badge cảnh báo hòa điểm hiện ra + đúng câu chữ SSoT
    const banner = wrapper.find('.tie-banner')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('Hòa điểm — cần quyết định thủ công')
    // a11y: role=alert + aria-live cho screen reader
    expect(banner.attributes('role')).toBe('alert')
    expect(banner.attributes('aria-live')).toBeTruthy()
    // liệt kê tied theo TÊN, KHÔNG leak mã SUP-*
    expect(banner.text()).toContain('NCC Alpha')
    expect(banner.text()).toContain('NCC Beta')
    expect(banner.text()).not.toContain('SUP-A')
    expect(banner.text()).not.toContain('SUP-B')
    // KHÔNG gắn marker 'Gợi ý trúng thầu' cho dòng nào khi hòa
    expect(wrapper.findAll('.rec-tag').length).toBe(0)
    // cả 2 dòng đỉnh được highlight .tied
    expect(wrapper.findAll('tr.tied').length).toBe(2)
    // KHÔNG leak raw EN state
    expect(html).not.toMatch(/\bEvaluated\b/)
  })

  it('KHÔNG tie: KHÔNG badge; đúng 1 dòng được gắn "Gợi ý trúng thầu"', async () => {
    getEvaluationSpy.mockResolvedValue({
      ...BASE,
      recommended_candidate: 'SUP-A',
      has_top_tie: 0,
      tied_candidates: '',
      candidates: [
        { idx: 1, supplier: 'SUP-A', supplier_name: 'NCC Alpha', in_avl: 1, weighted_score: 4.5 },
        { idx: 2, supplier: 'SUP-B', supplier_name: 'NCC Beta', in_avl: 1, weighted_score: 4.0 },
      ],
    })
    const wrapper = await mountView()

    expect(wrapper.find('.tie-banner').exists()).toBe(false)
    // đúng 1 marker gợi ý
    expect(wrapper.findAll('.rec-tag').length).toBe(1)
    expect(wrapper.find('.rec-tag').text()).toContain('Gợi ý trúng thầu')
    // dòng winner có class .winner, KHÔNG có .tied
    const rows = wrapper.findAll('tbody tr')
    const winnerRow = rows.find(r => r.classes().includes('winner'))
    expect(winnerRow).toBeTruthy()
    expect(wrapper.findAll('tr.tied').length).toBe(0)
  })

  it('hòa 1 phần: chỉ đỉnh được highlight .tied, candidate thấp hơn KHÔNG vào tied', async () => {
    getEvaluationSpy.mockResolvedValue({
      ...BASE,
      recommended_candidate: '',
      has_top_tie: 1,
      tied_candidates: 'SUP-A,SUP-B',
      candidates: [
        { idx: 1, supplier: 'SUP-A', supplier_name: 'NCC Alpha', in_avl: 1, weighted_score: 4.5 },
        { idx: 2, supplier: 'SUP-B', supplier_name: 'NCC Beta', in_avl: 1, weighted_score: 4.5 },
        { idx: 3, supplier: 'SUP-C', supplier_name: 'NCC Gamma', in_avl: 1, weighted_score: 3.0 },
      ],
    })
    const wrapper = await mountView()

    // chỉ 2 dòng đỉnh được highlight
    expect(wrapper.findAll('tr.tied').length).toBe(2)
    // tied list chỉ chứa 2 supplier đỉnh, KHÔNG có Gamma
    const bannerText = wrapper.find('.tie-banner').text()
    expect(bannerText).toContain('NCC Alpha')
    expect(bannerText).toContain('NCC Beta')
    expect(bannerText).not.toContain('NCC Gamma')
  })
})
