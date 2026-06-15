// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 vòng 3 · BUG-PM-2) — PMWorkOrderCreateView: empty-state khi
// thiết bị chưa có PM Schedule Active (list_pm_schedules total:0).
//
// Acceptance (LL-FE-44 — form required-dropdown dựa list endpoint, case total:0):
//   • QR-scan + 0 schedule → empty-state panel role=status, nêu TÊN thiết bị + cụm
//     'chưa có lịch' VI; nút 'Tạo phiếu bảo trì' disabled.
//   • can('pm.write')=true → CTA 'Tạo lịch bảo trì' → router.push('/pm/schedules').
//   • can('pm.write')=false → KHÔNG nút CTA; có dòng 'Liên hệ quản lý vật tư...'.
//   • loadingSchedules=true → KHÔNG flash empty-state.
//   • schedules.length>0 → KHÔNG empty-state (regression-free).
//   • reset asset_ref='' → empty-state biến mất (không stale).
//   • i18n VI thuần, 0 EN-leak / token / email.
//   • guidance cạnh nút submit khi !pm_schedule; biến mất khi đã chọn schedule.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const pushSpy = vi.fn().mockResolvedValue(undefined)
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

// can('pm.write') toggle per-test.
let canImpl: (c: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

// frappeGet: phân nhánh theo endpoint. list_pm_schedules → {data: schedulesFixture};
// PM Template get → {checklist: []}. Asset-meta KHÔNG còn qua frappeGet — nay nạp qua
// getAsset perm-aware (api/imm00, LL-FE-40).
let schedulesFixture: Array<Record<string, unknown>> = []
const assetMetaFixture = {
  device_model_name: 'Servo-i',
  asset_name: 'Máy thở ICU-01',
  lifecycle_status: 'Active',
  location_name: 'ICU-01',
}
const defaultFrappeGet = async (path: string) => {
  if (path.includes('list_pm_schedules')) return { data: schedulesFixture }
  if (path.includes('frappe.client.get')) return { checklist: [] }
  return null
}
const frappeGetMock = vi.fn(defaultFrappeGet)
vi.mock('@/api/helpers', () => ({
  frappeGet: (...args: unknown[]) => frappeGetMock(...(args as [string])),
  frappePost: vi.fn().mockResolvedValue(null),
}))
// getAssetActionMeta NẠC perm-aware (panel meta loader Vòng 25). Trả assetMetaFixture
// (display-name, KHÔNG field tài chính). getAsset giữ mock cho hoàn chỉnh module.
vi.mock('@/api/imm00', () => ({
  getAssetActionMeta: vi.fn().mockImplementation(() => Promise.resolve(assetMetaFixture)),
  getAsset: vi.fn().mockImplementation(() => Promise.resolve(assetMetaFixture)),
}))
vi.mock('@/api/imm08', () => ({
  createAdhocPMWorkOrder: vi.fn().mockResolvedValue({ name: 'PM-WO-2026-00001' }),
}))
vi.mock('@/api/imm16', () => ({
  checkAssetComplianceStatus: vi.fn().mockResolvedValue(null),
}))
vi.mock('@/composables/useFormDraft', () => ({
  useFormDraft: () => ({ clear: vi.fn() }),
}))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: vi.fn().mockResolvedValue(null) }),
}))

import PMWorkOrderCreateView from './PMWorkOrderCreateView.vue'

function mountView() {
  return mount(PMWorkOrderCreateView, {
    global: { stubs: { SmartSelect: true, DateInput: true } },
  })
}

function emptyStatePanel(w: ReturnType<typeof mountView>) {
  return w.find('[data-test="pm-schedule-empty"]')
}

function submitButton(w: ReturnType<typeof mountView>) {
  return w.findAll('button').find((b) => b.text().includes('Tạo phiếu bảo trì'))!
}

describe('PMWorkOrderCreateView — empty-state khi 0 PM Schedule Active (BUG-PM-2)', () => {
  beforeEach(() => {
    routeQuery = {}
    schedulesFixture = []
    canImpl = () => true
    pushSpy.mockClear()
    frappeGetMock.mockReset()
    frappeGetMock.mockImplementation(defaultFrappeGet)
  })

  it('TC-PMWO-EMPTY-01: QR-scan + 0 schedule → empty-state nêu tên thiết bị + "chưa có lịch"; submit disabled', async () => {
    routeQuery = { asset: 'ACC-ASS-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const panel = emptyStatePanel(w)
    expect(panel.exists()).toBe(true)
    expect(panel.attributes('role')).toBe('status')
    expect(panel.attributes('aria-live')).toBe('polite')
    expect(panel.text()).toContain('Máy thở ICU-01')
    expect(panel.text()).toContain('chưa có lịch')
    expect(submitButton(w).attributes('disabled')).toBeDefined()
  })

  it('TC-PMWO-EMPTY-02: can(pm.write)=true → CTA "Tạo lịch bảo trì" → router.push("/pm/schedules")', async () => {
    canImpl = (c) => c === 'pm.write'
    routeQuery = { asset: 'ACC-ASS-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const cta = w.find('[data-test="pm-schedule-create-cta"]')
    expect(cta.exists()).toBe(true)
    expect(cta.text()).toContain('Tạo lịch bảo trì')
    await cta.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/pm/schedules')
  })

  it('TC-PMWO-EMPTY-03: can(pm.write)=false → KHÔNG CTA, có hướng dẫn liên hệ; không push', async () => {
    canImpl = () => false
    routeQuery = { asset: 'ACC-ASS-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-test="pm-schedule-create-cta"]').exists()).toBe(false)
    const panel = emptyStatePanel(w)
    expect(panel.text()).toContain('Liên hệ quản lý vật tư')
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('TC-PMWO-EMPTY-04: loadingSchedules=true → KHÔNG flash empty-state', async () => {
    // resolve list_pm_schedules sau (giữ loadingSchedules=true) để kiểm flash.
    let resolveList: (v: { data: unknown[] }) => void = () => {}
    frappeGetMock.mockImplementation(async (path: string) => {
      if (path.includes('list_pm_schedules')) {
        return new Promise((res) => { resolveList = res as typeof resolveList })
      }
      return null
    })
    routeQuery = { asset: 'ACC-ASS-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    // đang tải → empty-state CHƯA render; option 'Đang tải...' xuất hiện.
    expect(emptyStatePanel(w).exists()).toBe(false)
    expect(w.text()).toContain('Đang tải...')
    // resolve [] → empty-state mới hiện.
    resolveList({ data: [] })
    await flushPromises()
    expect(emptyStatePanel(w).exists()).toBe(true)
  })

  it('TC-PMWO-EMPTY-05: schedules.length>0 → KHÔNG empty-state; dropdown có option', async () => {
    schedulesFixture = [
      { name: 'PM-SCH-0001', pm_type: 'Bảo trì định kỳ', pm_interval_days: 90, next_due_date: '2026-07-01' },
    ]
    routeQuery = { asset: 'ACC-ASS-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    expect(emptyStatePanel(w).exists()).toBe(false)
    const options = w.findAll('option')
    expect(options.some((o) => o.text().includes('PM-SCH-0001'))).toBe(true)
  })

  it('TC-PMWO-EMPTY-06: reset asset_ref="" → empty-state biến mất (không stale)', async () => {
    routeQuery = { asset: 'ACC-ASS-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    expect(emptyStatePanel(w).exists()).toBe(true)
    // QR khoá asset; nhưng reset programmatic (vd manual flow) phải clear empty-state.
    ;(w.vm as unknown as { form: { asset_ref: string } }).form.asset_ref = ''
    await flushPromises()
    expect(emptyStatePanel(w).exists()).toBe(false)
  })

  it('TC-PMWO-EMPTY-07: i18n no-leak — không EN enum / qr_token / email trong empty-state', async () => {
    routeQuery = { asset: 'ACC-ASS-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const t = emptyStatePanel(w).text()
    expect(t).not.toMatch(/\bOverdue\b/)
    expect(t).not.toMatch(/\bActive\b/)
    expect(t).not.toMatch(/\bDecommissioned\b/)
    expect(t).not.toMatch(/qr_token|@/)
  })

  it('TC-PMWO-EMPTY-09: asset-meta status render qua translateStatus (KHÔNG leak raw "Active")', async () => {
    routeQuery = { asset: 'ACC-ASS-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    expect(w.text()).toContain('Đang hoạt động')
    expect(w.text()).not.toMatch(/\bActive\b/)
  })

  it('TC-PMWO-EMPTY-08: guidance cạnh nút submit khi !pm_schedule; biến mất khi đã chọn', async () => {
    schedulesFixture = [
      { name: 'PM-SCH-0001', pm_type: 'Bảo trì định kỳ', pm_interval_days: 90, next_due_date: '2026-07-01' },
    ]
    routeQuery = { asset: 'ACC-ASS-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-test="submit-guidance"]').exists()).toBe(true)
    // chọn schedule → guidance biến mất.
    ;(w.vm as unknown as { form: { pm_schedule: string } }).form.pm_schedule = 'PM-SCH-0001'
    await flushPromises()
    expect(w.find('[data-test="submit-guidance"]').exists()).toBe(false)
  })
})
