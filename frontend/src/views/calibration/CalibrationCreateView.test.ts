// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 R1 QR scan-action slice) — CalibrationCreateView: field-lock theo
// source=qr-scan. Field nội bộ là 'asset' (KHÔNG asset_ref).
//
// Acceptance (D1/D3 + Task FE):
//   • route.query={asset,source:'qr-scan'} → form.asset prefill (đã có) + field asset
//     :disabled=true + badge "Tạo từ quét QR".
//   • route.query={asset} KHÔNG source → editable (no-regression).
//   • source lạ → coerce manual → KHÔNG khoá.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const pushSpy = vi.fn().mockResolvedValue(undefined)
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

vi.mock('@/api/imm11', () => ({
  createCalibration: vi.fn().mockResolvedValue({ name: 'CAL-2026-00001' }),
  listCalibrationSchedules: vi.fn().mockResolvedValue({ data: [] }),
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
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ error: vi.fn(), success: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))

import CalibrationCreateView from './CalibrationCreateView.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'

function mountView() {
  return mount(CalibrationCreateView, {
    global: { stubs: { SmartSelect: true, DateInput: true } },
  })
}

// Field Thiết bị (form.asset) là SmartSelect AC Asset có modelValue prefill.
function assetSelect(w: ReturnType<typeof mountView>) {
  return w.findAllComponents(SmartSelect).find(
    c => c.props('doctype') === 'AC Asset',
  )!
}

describe('CalibrationCreateView — field-lock khi source=qr-scan', () => {
  beforeEach(() => {
    routeQuery = {}
    pushSpy.mockClear()
  })

  it('prefill form.asset + khoá field asset + badge khi source=qr-scan', () => {
    routeQuery = { asset: 'TS-X', source: 'qr-scan' }
    const w = mountView()
    const ss = assetSelect(w)
    expect(ss.exists()).toBe(true)
    expect(ss.props('modelValue')).toBe('TS-X')
    expect(ss.props('disabled')).toBe(true)
    expect(w.text()).toContain('Tạo từ quét QR')
  })

  it('form.asset editable khi không source (no-regression)', () => {
    routeQuery = { asset: 'TS-X' }
    const w = mountView()
    const ss = assetSelect(w)
    expect(ss.props('modelValue')).toBe('TS-X')
    expect(ss.props('disabled')).toBe(false)
    expect(w.text()).not.toContain('Tạo từ quét QR')
  })

  it('source lạ → coerce manual → KHÔNG khoá', () => {
    routeQuery = { asset: 'TS-X', source: 'evil' }
    const w = mountView()
    expect(assetSelect(w).props('disabled')).toBe(false)
  })
})
