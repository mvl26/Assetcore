// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 R1 QR scan-action slice) — CMCreateView: field-lock theo source=qr-scan.
//
// Acceptance (D1/D3 + Task FE):
//   • route.query={asset,source:'qr-scan'} → asset_ref prefill (đã có) + SmartSelect
//     asset :disabled=true + badge "Tạo từ quét QR".
//   • route.query={asset} KHÔNG source → editable (no-regression).
//   • source lạ → coerce manual → KHÔNG khoá.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const pushSpy = vi.fn().mockResolvedValue(undefined)
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

vi.mock('@/api/imm12', () => ({ getIncident: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/imm09', () => ({
  searchSpareParts: vi.fn().mockResolvedValue([]),
  requestSpareParts: vi.fn().mockResolvedValue(null),
}))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn().mockResolvedValue({ file_url: '' }) }))
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
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))

import CMCreateView from './CMCreateView.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'

function mountView() {
  return mount(CMCreateView, {
    global: { stubs: { SmartSelect: true } },
  })
}

// Field Thiết bị (asset_ref) ở chế độ mặc định selectMode='asset' là SmartSelect
// AC Asset có modelValue = form.asset_ref. Lấy đúng component đó.
function assetSelect(w: ReturnType<typeof mountView>) {
  return w.findAllComponents(SmartSelect).find(
    c => c.props('doctype') === 'AC Asset' && c.props('modelValue') !== undefined,
  )!
}

describe('CMCreateView — field-lock khi source=qr-scan', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
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

  it('asset_ref editable khi không source (no-regression)', () => {
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
