// TDD — IMM-00 DepreciationView "Áp dụng khấu hao cho TẤT CẢ tài sản" (compute_all).
// Root-cause fix: nút global backfill-rồi-sinh trả payload 6 số
// {inherited, generated, executed_rows, updated_assets, skipped_has_history,
//  skipped_no_rule}; view render đủ 6 số.
// UX: KHÔNG còn gọi window.confirm — mở BaseModal xác nhận; chỉ khi xác nhận
// trong modal mới gọi API.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type {
  DepreciationStats, ComputeAllDepreciationResult,
} from '@/api/imm00'

const listSpy = vi.fn()
const statsSpy = vi.fn<() => Promise<DepreciationStats>>()
const computeAllSpy = vi.fn<() => Promise<ComputeAllDepreciationResult>>()

vi.mock('@/api/imm00', () => ({
  listAssetsDepreciation: (...a: unknown[]) => listSpy(...a),
  getDepreciationStats: () => statsSpy(),
  computeDepreciation: vi.fn(),
  computeAllDepreciation: () => computeAllSpy(),
}))

import DepreciationView from '@/views/asset/DepreciationView.vue'

// BaseModal NOT stubbed → modal body/footer render so we can assert the 6 numbers
// and click the confirm button. PageHeader stub MUST render its #actions slot
// (the compute-all button lives there) — a bare `true` stub drops slots.
const stubs = {
  PageHeader: {
    template: '<div><slot /><slot name="actions" /></div>',
  },
  AssetDepreciationSchedule: true,
  RouterLink: true,
  // BaseModal teleports to <body>; render inline so wrapper queries reach it.
  teleport: true,
}

const emptyStats: DepreciationStats = {
  total_assets: 3, configured_count: 3, unconfigured_count: 0, fully_depreciated: 0,
  total_gross: 0, total_accumulated: 0, total_book_value: 0, overall_pct: 0,
  by_method: [], by_category: [],
}

const RESULT: ComputeAllDepreciationResult = {
  inherited: 2,
  generated: 5,
  executed_rows: 11,
  updated_assets: 7,
  skipped_has_history: 3,
  skipped_no_rule: 1,
}

describe('DepreciationView — compute_all backfill (6-number payload + BaseModal)', () => {
  let confirmSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    listSpy.mockResolvedValue({ items: [], pagination: { total: 0 } })
    statsSpy.mockResolvedValue(emptyStats)
    computeAllSpy.mockReset()
    computeAllSpy.mockResolvedValue(RESULT)
    // Spy global confirm: assert it is NEVER called (we use a modal instead).
    confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => {
    confirmSpy.mockRestore()
  })

  function findComputeAllBtn(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll('button').find(
      b => b.text().includes('Áp dụng khấu hao cho TẤT CẢ tài sản'),
    )
  }

  it('nút có nhãn VI "Áp dụng khấu hao cho TẤT CẢ tài sản"', async () => {
    const wrapper = mount(DepreciationView, { global: { stubs } })
    await flushPromises()
    expect(findComputeAllBtn(wrapper)).toBeTruthy()
  })

  it('click nút KHÔNG gọi window.confirm — mở BaseModal xác nhận; API chưa gọi', async () => {
    const wrapper = mount(DepreciationView, { global: { stubs } })
    await flushPromises()

    await findComputeAllBtn(wrapper)!.trigger('click')
    await flushPromises()

    // window.confirm tuyệt đối KHÔNG được gọi.
    expect(confirmSpy).not.toHaveBeenCalled()
    // API chưa gọi cho tới khi xác nhận trong modal.
    expect(computeAllSpy).not.toHaveBeenCalled()
    // Modal xác nhận đã mở (có nút "Xác nhận áp dụng").
    const confirmBtn = wrapper.findAll('button').find(
      b => b.text().includes('Xác nhận áp dụng'),
    )
    expect(confirmBtn).toBeTruthy()
  })

  it('xác nhận trong modal → gọi computeAllDepreciation và render đủ 6 số', async () => {
    const wrapper = mount(DepreciationView, { global: { stubs } })
    await flushPromises()

    await findComputeAllBtn(wrapper)!.trigger('click')
    await flushPromises()

    const confirmBtn = wrapper.findAll('button').find(
      b => b.text().includes('Xác nhận áp dụng'),
    )!
    await confirmBtn.trigger('click')
    await flushPromises()

    // Đúng 1 lần gọi API sau khi xác nhận.
    expect(computeAllSpy).toHaveBeenCalledTimes(1)
    // window.confirm vẫn KHÔNG được dùng.
    expect(confirmSpy).not.toHaveBeenCalled()

    // Render đủ 6 số từ payload.
    expect(wrapper.find('[data-testid="result-inherited"]').text()).toBe('2')
    expect(wrapper.find('[data-testid="result-generated"]').text()).toBe('5')
    expect(wrapper.find('[data-testid="result-executed"]').text()).toBe('11')
    expect(wrapper.find('[data-testid="result-updated"]').text()).toBe('7')
    expect(wrapper.find('[data-testid="result-skipped-history"]').text()).toBe('3')
    expect(wrapper.find('[data-testid="result-skipped-no-rule"]').text()).toBe('1')
  })
})
