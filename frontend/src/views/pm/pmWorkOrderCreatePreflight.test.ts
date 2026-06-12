// TDD — IMM-16/IMM-08: pre-flight compliance gate banner on ad-hoc PM WO create.
// BR-16-09: PMWorkOrderCreateView reads the SAME SoT as gate_wo_submit via
// checkAssetComplianceStatus and RENDERS result.blocked + reasons[] verbatim.
//
// TC-PMWO-PREFLIGHT-01: blocked gate → banner role='alert', text 'Quá hạn' (no
//   'Overdue' leak), nút 'Tạo phiếu bảo trì' disabled.
// TC-PMWO-PREFLIGHT-02: blocked=false → banner NOT rendered, nút enabled.
// TC-PMWO-PREFLIGHT-03 (fail-safe): gate REJECT (403/network) → assetMeta panel
//   still renders, complianceGate=null, banner hidden, no uncaught throw.
// TC-PMWO-PREFLIGHT-04 (i18n SSoT / GATE-1): 0 English literal 'Overdue'/'Critical'/
//   'Open' in banner DOM.
// TC-PMWO-PREFLIGHT-05 (reset): clear asset_ref after gate → complianceGate null,
//   banner gone (not stale).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// ROOT-CAUSE test-isolation fix: shared full-shape router mock (xem
// src/test/vueRouterMock.ts). File này chỉ cần useRouter, nhưng dùng full-shape
// để khi mock leak sang file PM khác (đọc useRoute().query) KHÔNG gây undefined.
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

// IMM-08 create endpoint — never called in these tests.
vi.mock('@/api/imm08', () => ({
  createAdhocPMWorkOrder: vi.fn(),
}))

// Asset-meta nay nạp qua getAsset (perm-aware, api/imm00) — KHÔNG còn
// frappe.client.get_value (LL-FE-40). frappeGet CHỈ còn dùng cho list_pm_schedules.
vi.mock('@/api/helpers', () => ({
  frappeGet: vi.fn().mockImplementation(() => Promise.resolve({ data: [] })),
  frappePost: vi.fn(),
}))

// getAssetActionMeta NẠC perm-aware (panel meta loader Vòng 25) — trả benign Active
// asset (display-name, KHÔNG field tài chính). getAsset giữ mock cho hoàn chỉnh module.
// (Inline object — vi.mock hoist lên đầu file, KHÔNG ref top-level var.)
vi.mock('@/api/imm00', () => {
  const benign = {
    name: 'AC-ASSET-0001',
    asset_name: 'Máy thở ICU-01',
    device_model_name: 'VENT-X',
    lifecycle_status: 'Active',
    location_name: 'ICU',
  }
  return {
    getAssetActionMeta: vi.fn().mockResolvedValue(benign),
    getAsset: vi.fn().mockResolvedValue(benign),
  }
})

// The compliance gate — controlled per test.
const gateSpy = vi.fn()
vi.mock('@/api/imm16', () => ({
  checkAssetComplianceStatus: (asset: string) => gateSpy(asset),
}))

// useApi / useFormDraft — minimal stubs (no toast plumbing needed here).
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: vi.fn() }),
}))
vi.mock('@/composables/useFormDraft', () => ({
  useFormDraft: () => ({ clear: vi.fn() }),
}))
// Capability gate (CTA 'Tạo lịch bảo trì' trong empty-state) — không liên quan các
// test ở file này; stub để view mount KHÔNG cần Pinia auth store thật.
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import PMWorkOrderCreateView from './PMWorkOrderCreateView.vue'

// Stub leaf components; SmartSelect emits asset_ref via update:modelValue.
const SmartSelectStub = {
  props: ['modelValue', 'doctype', 'placeholder'],
  emits: ['update:modelValue'],
  template: '<input class="smart-select" :data-doctype="doctype" '
    + '@input="$emit(\'update:modelValue\', $event.target.value)" />',
}
const stubs = {
  SmartSelect: SmartSelectStub,
  DateInput: true,
}

async function selectAsset(w: ReturnType<typeof mount>, ref: string) {
  // First SmartSelect in template is the asset selector.
  const sel = w.findAll('.smart-select')[0]
  await sel.setValue(ref)
  await flushPromises()
}

const submitBtn = (w: ReturnType<typeof mount>) =>
  w.findAll('button').find(b => b.text().includes('Tạo phiếu bảo trì'))

describe('PMWorkOrderCreateView — pre-flight compliance gate (BR-16-09)', () => {
  beforeEach(() => { gateSpy.mockReset() })

  it('TC-PMWO-PREFLIGHT-01: blocked gate → banner role=alert + Quá hạn, nút disabled', async () => {
    gateSpy.mockResolvedValue({
      blocked: true,
      asset: 'ACC-ASS-0001',
      reasons: [{ type: 'CAPA_CRITICAL_OPEN', ref: 'CAPA-2026-00007',
                  status: 'Overdue', workflow_state: 'Investigating',
                  message: 'CAPA Critical chưa close' }],
      active_findings_count: 0,
      active_capas_count: 1,
      blocking_findings: [],
    })
    const w = mount(PMWorkOrderCreateView, { global: { stubs } })
    await selectAsset(w, 'ACC-ASS-0001')

    const banner = w.find('[role="alert"][aria-live="assertive"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('CAPA-2026-00007')
    expect(banner.text()).toContain('Quá hạn')

    const btn = submitBtn(w)
    expect(btn?.attributes('disabled')).toBeDefined()
  })

  it('TC-PMWO-PREFLIGHT-02: blocked=false → banner ẩn, nút không bị gate chặn', async () => {
    gateSpy.mockResolvedValue({
      blocked: false, asset: 'ACC-ASS-0002', reasons: [],
      active_findings_count: 0, active_capas_count: 0, blocking_findings: [],
    })
    const w = mount(PMWorkOrderCreateView, { global: { stubs } })
    await selectAsset(w, 'ACC-ASS-0002')

    expect(w.find('[role="alert"][aria-live="assertive"]').exists()).toBe(false)
    // Asset panel still rendered.
    expect(w.text()).toContain('Máy thở ICU-01')
  })

  it('TC-PMWO-PREFLIGHT-03: gate REJECT (403/network) → panel VẪN render, banner ẩn, no throw', async () => {
    gateSpy.mockRejectedValue(new Error('Request failed with status code 403'))
    const w = mount(PMWorkOrderCreateView, { global: { stubs } })
    await selectAsset(w, 'ACC-ASS-0003')
    await flushPromises()

    // assetMeta panel renders despite gate failure (allSettled fail-safe).
    expect(w.text()).toContain('Máy thở ICU-01')
    expect(w.find('[role="alert"][aria-live="assertive"]').exists()).toBe(false)
  })

  it('TC-PMWO-PREFLIGHT-04: i18n SSoT — 0 English enum leak in banner DOM (GATE-1)', async () => {
    gateSpy.mockResolvedValue({
      blocked: true, asset: 'ACC-ASS-0004',
      reasons: [{ type: 'CAPA_CRITICAL_OPEN', ref: 'CAPA-2026-00009',
                  status: 'Overdue', workflow_state: 'Open',
                  message: 'x' }],
      active_findings_count: 0, active_capas_count: 1, blocking_findings: [],
    })
    const w = mount(PMWorkOrderCreateView, { global: { stubs } })
    await selectAsset(w, 'ACC-ASS-0004')

    const bannerText = w.find('[role="alert"][aria-live="assertive"]').text()
    expect(bannerText).not.toMatch(/\bOverdue\b/)
    expect(bannerText).not.toMatch(/\bCritical\b/)
    expect(bannerText).not.toMatch(/\bOpen\b/)
    expect(bannerText).toContain('Quá hạn')
  })

  it('TC-PMWO-PREFLIGHT-05: reset asset_ref rỗng → complianceGate null, banner biến mất', async () => {
    gateSpy.mockResolvedValue({
      blocked: true, asset: 'ACC-ASS-0005',
      reasons: [{ type: 'CAPA_CRITICAL_OPEN', ref: 'CAPA-2026-00011',
                  status: 'Overdue', workflow_state: 'Open', message: 'x' }],
      active_findings_count: 0, active_capas_count: 1, blocking_findings: [],
    })
    const w = mount(PMWorkOrderCreateView, { global: { stubs } })
    await selectAsset(w, 'ACC-ASS-0005')
    expect(w.find('[role="alert"][aria-live="assertive"]').exists()).toBe(true)

    // Clear selection → watch loadAssetMeta resets gate to null.
    await selectAsset(w, '')
    expect(w.find('[role="alert"][aria-live="assertive"]').exists()).toBe(false)
  })
})
