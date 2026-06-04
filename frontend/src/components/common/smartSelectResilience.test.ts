// TC-FE-CAL-SEARCH-06 — SmartSelect resilience (defense-in-depth alongside the
// BE root-cause fix for IMM-11 ∩ IMM-04 'asset_ref' crash).
//
// Even after the BE no longer returns 500 for 'IMM Calibration Schedule',
// SmartSelect must never let a rejected/empty master-data fetch escape as an
// unhandled rejection that breaks the host view (e.g. CalibrationCreateView's
// "Tìm lịch khác..." picker → full-page "Trang gặp lỗi khi tải"). Opening the
// dropdown when the store fetch rejects must keep the form alive and render an
// empty-state instead of throwing.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SmartSelect from './SmartSelect.vue'
import { useMasterDataStore } from '@/stores/masterData'

// Transport-level mock (hoisted): R3/R4 exercise the REAL store path
// (fetchDoctype → frappeGet → search_link) so a regression where the store stops
// swallowing — or where the search_link naming-contract drifts — is caught here.
// R1/R2 spy on store.fetchDoctype directly so they never reach this mock.
vi.mock('@/api/helpers', () => ({
  frappeGet: vi.fn(),
  frappePost: vi.fn(),
}))
import { frappeGet } from '@/api/helpers'

const SEARCH_LINK_ENDPOINT = '/api/method/assetcore.api.imm04.search_link'

describe('SmartSelect resilience (TC-FE-CAL-SEARCH-06)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('R1: opening with a rejecting fetch does NOT throw and shows empty-state', async () => {
    const store = useMasterDataStore()
    // Simulate BE search_link reject / network 500 / config drift.
    const rejecting = vi.spyOn(store, 'fetchDoctype').mockRejectedValue(
      new Error('500 search_link'),
    )

    const w = mount(SmartSelect, {
      props: { modelValue: '', doctype: 'IMM Calibration Schedule', placeholder: 'Tìm lịch khác...' },
    })

    // Open the dropdown → triggers ensureLoaded(); reject must be swallowed.
    await expect(
      w.get('button[type="button"]').trigger('click'),
    ).resolves.not.toThrow()
    await w.vm.$nextTick()

    expect(rejecting).toHaveBeenCalled()
    // Dropdown open + empty-state visible, form intact (component still mounted).
    expect(w.text()).toContain('Chưa có dữ liệu')
    expect(w.find('input[type="text"]').exists()).toBe(true)
  })

  it('R2: empty result set (resolved, no rows) renders empty-state, not a crash', async () => {
    const store = useMasterDataStore()
    vi.spyOn(store, 'fetchDoctype').mockResolvedValue(undefined as never)
    vi.spyOn(store, 'getItems').mockReturnValue([])

    const w = mount(SmartSelect, {
      props: { modelValue: '', doctype: 'IMM Calibration Schedule' },
    })
    await w.get('button[type="button"]').trigger('click')
    await w.vm.$nextTick()

    expect(w.text()).toContain('Chưa có dữ liệu')
  })
})

// ── Transport-level: REAL store path through search_link (naming-contract + no leak)
describe('SmartSelect resilience — real store/search_link path (TC-FE-CAL-SEARCH-06)', () => {
  let unhandled: unknown[] = []
  const onUnhandled = (e: PromiseRejectionEvent) => {
    unhandled.push(e.reason)
    e.preventDefault?.()
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    unhandled = []
    if (typeof window !== 'undefined') window.addEventListener('unhandledrejection', onUnhandled)
  })
  afterEach(() => {
    if (typeof window !== 'undefined') window.removeEventListener('unhandledrejection', onUnhandled)
  })

  async function mountAndOpen() {
    const w = mount(SmartSelect, {
      props: { modelValue: '', doctype: 'IMM Calibration Schedule', placeholder: 'Tìm lịch khác...' },
    })
    await flushPromises()
    await w.get('button[type="button"]').trigger('click')
    await flushPromises()
    await flushPromises()
    return w
  }

  it('R3: search_link reject (500/1054) → real store path, empty-state, no unhandled rejection, no SQL leak', async () => {
    vi.mocked(frappeGet).mockRejectedValue(
      new Error('OperationalError 1054: Unknown column asset_ref'),
    )

    const w = await mountAndOpen()
    const html = w.html()

    expect(html).toContain('Chưa có dữ liệu')
    // KHÔNG leak SQL/traceback ra UI.
    expect(html).not.toContain('asset_ref')
    expect(html).not.toContain('1054')
    expect(html).not.toContain('OperationalError')
    // KHÔNG có unhandled promise rejection (chống full-page crash).
    expect(unhandled).toEqual([])

    // Naming-contract: gọi đúng endpoint search_link với param doctype khớp BE.
    expect(frappeGet).toHaveBeenCalled()
    const [endpoint, params] = vi.mocked(frappeGet).mock.calls[0]
    expect(endpoint).toBe(SEARCH_LINK_ENDPOINT)
    expect((params as Record<string, unknown>).doctype).toBe('IMM Calibration Schedule')
  })

  it('R4: search_link OK → render lịch (value→id, label→tên, description=mã asset)', async () => {
    vi.mocked(frappeGet).mockResolvedValue([
      { value: 'CAL-SCH-0001', label: 'CAL-SCH-0001', description: 'AC-0001' },
      { value: 'CAL-SCH-0002', label: 'CAL-SCH-0002', description: 'AC-0002' },
    ] as never)

    const w = await mountAndOpen()
    const html = w.html()

    expect(html).toContain('CAL-SCH-0001')
    expect(html).toContain('AC-0001') // description = mã asset (shape {value,label,description})
    expect(html).not.toContain('Chưa có dữ liệu')
    expect(unhandled).toEqual([])
  })
})
