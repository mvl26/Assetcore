// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-12 báo-hỏng slice) — IncidentCreateView: field-lock + source provenance.
//
// Acceptance (map AC3 + FE-1/FE-2):
//   • route.query={asset,source:'qr-scan'} → ô Thiết bị (SmartSelect) :disabled=true,
//     asset prefill đúng, badge "Tạo từ quét QR" hiển thị.
//   • route.query={asset} KHÔNG source → SmartSelect editable (:disabled=false),
//     không badge khoá.
//   • submit qr-scan → reportIncident payload.source === 'qr-scan'.
//   • submit manual (không source) → payload.source === 'manual'.
//   • source giá trị lạ (vd 'hack') → coerce về 'manual' (parity BA-chốt).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const pushSpy = vi.fn().mockResolvedValue(undefined)
// route.query được set per-test qua biến module-scope.
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

const reportIncidentSpy = vi
  .fn()
  .mockResolvedValue({ name: 'INC-2026-00001', status: 'Open', severity: 'High' })
vi.mock('@/api/imm12', () => ({
  reportIncident: (data: Record<string, unknown>) => reportIncidentSpy(data),
}))

// useFormDraft: no-op (không persist localStorage trong test).
vi.mock('@/composables/useFormDraft', () => ({
  useFormDraft: () => ({ clear: vi.fn() }),
}))

import IncidentCreateView from '@/views/incident/IncidentCreateView.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'

function mountView() {
  return mount(IncidentCreateView, {
    global: { stubs: { SmartSelect: true } },
  })
}

// Điền các field bắt buộc (incident_type, severity, description) để submit qua FE guard.
async function fillRequired(w: ReturnType<typeof mountView>) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const vm = w.vm as any
  vm.form.incident_type = 'Failure'
  vm.form.severity = 'High'
  vm.form.description = 'Máy ngừng hoạt động đột ngột'
  await flushPromises()
}

describe('IncidentCreateView — field-lock khi source=qr-scan [AC3 / FE-1]', () => {
  beforeEach(() => {
    routeQuery = {}
    reportIncidentSpy.mockClear()
    pushSpy.mockClear()
  })

  it('locks asset field when source=qr-scan (SmartSelect disabled + asset prefill)', () => {
    routeQuery = { asset: 'AC-ASSET-2026-00042', source: 'qr-scan' }
    const w = mountView()
    const ss = w.findComponent(SmartSelect)
    expect(ss.exists()).toBe(true)
    expect(ss.props('disabled')).toBe(true)
    expect(ss.props('modelValue')).toBe('AC-ASSET-2026-00042')
    // Badge VI "Tạo từ quét QR" hiển thị (a11y role=status).
    expect(w.text()).toContain('Tạo từ quét QR')
  })

  it('asset editable when manual (không source) — no regression', () => {
    routeQuery = { asset: 'AC-ASSET-2026-00042' }
    const w = mountView()
    const ss = w.findComponent(SmartSelect)
    expect(ss.props('disabled')).toBe(false)
    expect(ss.props('modelValue')).toBe('AC-ASSET-2026-00042')
    // KHÔNG hiện badge khoá khi tạo thủ công.
    expect(w.text()).not.toContain('Tạo từ quét QR')
  })

  it('asset editable khi không có asset prefill dù source=qr-scan (guard !!queryAsset)', () => {
    routeQuery = { source: 'qr-scan' }
    const w = mountView()
    const ss = w.findComponent(SmartSelect)
    expect(ss.props('disabled')).toBe(false)
  })
})

describe('IncidentCreateView — source propagation vào payload [AC3 / FE-2]', () => {
  beforeEach(() => {
    routeQuery = {}
    reportIncidentSpy.mockClear()
    pushSpy.mockClear()
  })

  it('propagates source=qr-scan to reportIncident payload', async () => {
    routeQuery = { asset: 'AC-ASSET-2026-00042', source: 'qr-scan' }
    const w = mountView()
    await fillRequired(w)
    await w.find('button[class*="bg-blue-600"]').trigger('click')
    await flushPromises()
    expect(reportIncidentSpy).toHaveBeenCalledTimes(1)
    const payload = reportIncidentSpy.mock.calls[0][0] as Record<string, unknown>
    expect(payload.source).toBe('qr-scan')
    expect(payload.asset).toBe('AC-ASSET-2026-00042')
  })

  it('không source → payload.source === manual (mặc định)', async () => {
    routeQuery = { asset: 'AC-ASSET-2026-00042' }
    const w = mountView()
    await fillRequired(w)
    await w.find('button[class*="bg-blue-600"]').trigger('click')
    await flushPromises()
    expect(reportIncidentSpy).toHaveBeenCalledTimes(1)
    const payload = reportIncidentSpy.mock.calls[0][0] as Record<string, unknown>
    expect(payload.source).toBe('manual')
  })

  it('source giá trị lạ → coerce về manual (parity BA-chốt)', async () => {
    routeQuery = { asset: 'AC-ASSET-2026-00042', source: 'hack' }
    const w = mountView()
    await fillRequired(w)
    await w.find('button[class*="bg-blue-600"]').trigger('click')
    await flushPromises()
    const payload = reportIncidentSpy.mock.calls[0][0] as Record<string, unknown>
    expect(payload.source).toBe('manual')
    // giá trị lạ KHÔNG được coi là qr-scan → không khoá field.
    const ss = w.findComponent(SmartSelect)
    expect(ss.props('disabled')).toBe(false)
  })
})

describe('IncidentCreateView — occurred_datetime [L-19]', () => {
  beforeEach(() => {
    routeQuery = {}
    reportIncidentSpy.mockClear()
    pushSpy.mockClear()
  })

  it('truyền occurred_datetime vào payload khi user nhập', async () => {
    routeQuery = { asset: 'AC-ASSET-2026-00042' }
    const w = mountView()
    await fillRequired(w)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(w.vm as any).form.occurred_datetime = '2026-06-01 08:30:00'
    await w.find('button[class*="bg-blue-600"]').trigger('click')
    await flushPromises()
    const payload = reportIncidentSpy.mock.calls[0][0] as Record<string, unknown>
    expect(payload.occurred_datetime).toBe('2026-06-01 08:30:00')
  })

  it('để trống occurred_datetime → payload rỗng (BE fallback = reported_at)', async () => {
    routeQuery = { asset: 'AC-ASSET-2026-00042' }
    const w = mountView()
    await fillRequired(w)
    await w.find('button[class*="bg-blue-600"]').trigger('click')
    await flushPromises()
    const payload = reportIncidentSpy.mock.calls[0][0] as Record<string, unknown>
    expect((payload.occurred_datetime as string) ?? '').toBe('')
  })

  it('chặn client khi occurred_datetime ở tương lai (mirror BE guard)', async () => {
    routeQuery = { asset: 'AC-ASSET-2026-00042' }
    const w = mountView()
    await fillRequired(w)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(w.vm as any).form.occurred_datetime = '2099-01-01 00:00:00'
    await w.find('button[class*="bg-blue-600"]').trigger('click')
    await flushPromises()
    expect(reportIncidentSpy).not.toHaveBeenCalled()
    expect(w.text()).toContain('tương lai')
  })
})
