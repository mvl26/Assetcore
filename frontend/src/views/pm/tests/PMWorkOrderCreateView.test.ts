// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 R1 QR scan-action slice) — PMWorkOrderCreateView: prefill + field-lock
// theo source=qr-scan (parity mẫu IncidentCreateView).
//
// Acceptance (D1/D3 + Task FE):
//   • route.query={asset,source:'qr-scan'} → form.asset_ref prefill, SmartSelect asset
//     :disabled=true, badge "Tạo từ quét QR" hiển thị.
//   • route.query={asset} KHÔNG source → asset_ref prefill NHƯNG SmartSelect editable
//     (:disabled=false), không badge khoá (no-regression).
//   • source giá trị lạ ('manual'/'evil') → coerce → KHÔNG khoá.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const pushSpy = vi.fn().mockResolvedValue(undefined)
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

// API stubs — view chỉ cần mount + đọc route.query; không gọi BE trong các test này.
vi.mock('@/api/imm08', () => ({
  createAdhocPMWorkOrder: vi.fn().mockResolvedValue({ name: 'PM-WO-2026-00001' }),
}))
vi.mock('@/api/imm16', () => ({
  checkAssetComplianceStatus: vi.fn().mockResolvedValue(null),
}))
vi.mock('@/api/helpers', () => ({
  frappeGet: vi.fn().mockResolvedValue(null),
  frappePost: vi.fn().mockResolvedValue(null),
}))
vi.mock('@/composables/useFormDraft', () => ({
  useFormDraft: () => ({ clear: vi.fn() }),
}))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: vi.fn().mockResolvedValue(null) }),
}))
// Empty-state CTA gate — stub để view mount không cần Pinia auth store.
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import PMWorkOrderCreateView from '@/views/pm/PMWorkOrderCreateView.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'

function mountView() {
  return mount(PMWorkOrderCreateView, {
    global: { stubs: { SmartSelect: true, DateInput: true } },
  })
}

// SmartSelect cho field Thiết bị là component đầu tiên (asset_ref). Supervisor cũng là
// SmartSelect → lấy đúng component bind form.asset_ref bằng modelValue prefill.
function assetSelect(w: ReturnType<typeof mountView>) {
  return w.findAllComponents(SmartSelect).find(
    c => c.props('doctype') === 'AC Asset',
  )!
}

describe('PMWorkOrderCreateView — prefill + field-lock khi source=qr-scan', () => {
  beforeEach(() => {
    routeQuery = {}
    pushSpy.mockClear()
  })

  it('prefill asset_ref + khoá SmartSelect + badge khi source=qr-scan', () => {
    routeQuery = { asset: 'TS-X', source: 'qr-scan' }
    const w = mountView()
    const ss = assetSelect(w)
    expect(ss.exists()).toBe(true)
    expect(ss.props('modelValue')).toBe('TS-X')
    expect(ss.props('disabled')).toBe(true)
    expect(w.text()).toContain('Tạo từ quét QR')
  })

  it('prefill asset_ref NHƯNG KHÔNG khoá khi không có source (no-regression)', () => {
    routeQuery = { asset: 'TS-X' }
    const w = mountView()
    const ss = assetSelect(w)
    expect(ss.props('modelValue')).toBe('TS-X')
    expect(ss.props('disabled')).toBe(false)
    expect(w.text()).not.toContain('Tạo từ quét QR')
  })

  it('source lạ "manual" → coerce → KHÔNG khoá', () => {
    routeQuery = { asset: 'TS-X', source: 'manual' }
    const w = mountView()
    expect(assetSelect(w).props('disabled')).toBe(false)
  })

  it('source lạ "evil" → coerce → KHÔNG khoá', () => {
    routeQuery = { asset: 'TS-X', source: 'evil' }
    const w = mountView()
    expect(assetSelect(w).props('disabled')).toBe(false)
  })

  it('source=qr-scan nhưng KHÔNG asset prefill → KHÔNG khoá (guard !!queryAsset)', () => {
    routeQuery = { source: 'qr-scan' }
    const w = mountView()
    expect(assetSelect(w).props('disabled')).toBe(false)
  })
})
