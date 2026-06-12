// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 Vòng 40 scan-action — bịt rò enum EN risk_classification) —
// Parity guard gom: KHÔNG view nào trong {CM, Calibration} render raw enum risk EN
// ({Low,Medium,High,Critical}) lên panel meta màn QR scan-action — mirror nguyên tắc
// no-EN-leak scan-info Vòng 38. Map VI qua SSoT riskClassificationLabel.
//
// Acceptance (Vòng 40):
//   AC1/AC2 — Low→Thấp, Medium→Trung bình, High→Cao, Critical→Nghiêm trọng (cả 2 view).
//   AC3 — rỗng → 'Chưa phân loại'; drift → 'Khác' (KHÔNG leak raw EN/code).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { RISK_CLASSIFICATION_LABEL, riskClassificationLabel } from '@/constants/labels'

const pushSpy = vi.fn().mockResolvedValue(undefined)
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

// — CM deps —
vi.mock('@/api/imm12', () => ({ getIncident: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/imm09', () => ({
  searchSpareParts: vi.fn().mockResolvedValue([]),
  requestSpareParts: vi.fn().mockResolvedValue(null),
}))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn().mockResolvedValue({ file_url: '' }) }))
// — Cal deps —
vi.mock('@/api/imm11', () => ({
  createCalibration: vi.fn().mockResolvedValue({ name: 'CAL-2026-00001' }),
  listCalibrationSchedules: vi.fn().mockResolvedValue({ data: [] }),
}))

const frappeGetSpy = vi.fn().mockResolvedValue(null)
vi.mock('@/api/helpers', () => ({
  frappeGet: (...args: unknown[]) => frappeGetSpy(...args),
  frappePost: vi.fn().mockResolvedValue(null),
}))

const getActionMetaSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  getAssetActionMeta: (...args: unknown[]) => getActionMetaSpy(...args),
  getAsset: vi.fn(),
}))

vi.mock('@/composables/useFormDraft', () => ({ useFormDraft: () => ({ clear: vi.fn() }) }))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ run: vi.fn().mockResolvedValue(null) }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ error: vi.fn(), success: vi.fn() }) }))
vi.mock('@/composables/useNotify', () => ({ useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }) }))

import CMCreateView from './CMCreateView.vue'
import CalibrationCreateView from '../calibration/CalibrationCreateView.vue'

const VIEWS: Array<[string, unknown, Record<string, boolean>]> = [
  ['CMCreateView', CMCreateView, { SmartSelect: true }],
  ['CalibrationCreateView', CalibrationCreateView, { SmartSelect: true, DateInput: true }],
]

const BASE_META = {
  name: 'AC-ASSET-0001',
  asset_name: 'Thiết bị parity',
  device_model_name: 'Model parity',
  lifecycle_status: 'Active',
  location_name: 'Khoa parity',
}

const RAW_EN = ['Low', 'Medium', 'High', 'Critical'] as const

function mountView(Comp: unknown, stubs: Record<string, boolean>) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return mount(Comp as any, { global: { stubs } })
}

describe('risk_classification parity — no-EN-leak {CM, Calibration} (Vòng 40)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    routeQuery = {}
    pushSpy.mockClear()
    frappeGetSpy.mockClear()
    getActionMetaSpy.mockReset()
  })

  it('SSoT riskClassificationLabel map đúng 4 enum + drift→Khác', () => {
    expect(RISK_CLASSIFICATION_LABEL).toEqual({
      Low: 'Thấp', Medium: 'Trung bình', High: 'Cao', Critical: 'Nghiêm trọng',
    })
    expect(riskClassificationLabel('Xyz')).toBe('Khác')
  })

  for (const [name, Comp, stubs] of VIEWS) {
    it.each(RAW_EN.map(en => [en, RISK_CLASSIFICATION_LABEL[en]]))(
      `${name}: risk "%s" → "%s" VI, KHÔNG raw EN nào lọt panel`,
      async (raw, vi_) => {
        getActionMetaSpy.mockResolvedValue({ ...BASE_META, risk_classification: raw })
        routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
        const w = mountView(Comp, stubs)
        await flushPromises()
        // panel meta render khi assetMeta != null (grid bg-slate-50 cells)
        const grid = w.findAll('div').filter(d => d.text().includes(vi_ as string))
        expect(grid.length).toBeGreaterThan(0)
        // không enum EN nào ngoài cái match nhãn VI được leak ở cell rủi ro
        const riskCell = w.findAll('div')
          .filter(d => /Risk class:|Mức rủi ro:/.test(d.text()))
          .map(d => d.text())
          .sort((a, b) => a.length - b.length)[0]
        expect(riskCell).toBeTruthy()
        for (const en of RAW_EN) {
          expect(riskCell).not.toContain(en)
        }
        w.unmount()
      },
    )

    it(`${name}: rỗng → "Chưa phân loại"`, async () => {
      getActionMetaSpy.mockResolvedValue({ ...BASE_META, risk_classification: '' })
      routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
      const w = mountView(Comp, stubs)
      await flushPromises()
      const riskCell = w.findAll('div')
        .filter(d => /Risk class:|Mức rủi ro:/.test(d.text()))
        .map(d => d.text())
        .sort((a, b) => a.length - b.length)[0]
      expect(riskCell).toContain('Chưa phân loại')
      w.unmount()
    })

    it(`${name}: drift "Zzz" → "Khác" (KHÔNG leak raw)`, async () => {
      getActionMetaSpy.mockResolvedValue({ ...BASE_META, risk_classification: 'Zzz' })
      routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
      const w = mountView(Comp, stubs)
      await flushPromises()
      const riskCell = w.findAll('div')
        .filter(d => /Risk class:|Mức rủi ro:/.test(d.text()))
        .map(d => d.text())
        .sort((a, b) => a.length - b.length)[0]
      expect(riskCell).toContain('Khác')
      expect(riskCell).not.toContain('Zzz')
      w.unmount()
    })
  }
})
