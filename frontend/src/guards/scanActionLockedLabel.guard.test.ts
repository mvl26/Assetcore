// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 vòng 2 · BUG-PM-1) — parity 4 create-view: SmartSelect khoá theo
// QR-scan PHẢI hiển thị TÊN thiết bị đã prefill (selectedItem.name), KHÔNG raw mã
// xám đứng một mình, KHI asset chỉ resolve được qua store.resolveOne (không nằm
// trong trang đầu search_link của danh mục lớn).
//
// • IncidentCreateView dùng SmartSelect THẬT (không stub) → chứng minh end-to-end
//   label-resolution: cache getItems RỖNG ban đầu, resolveOne trả tên → nút khoá
//   render TÊN, disabled=true, badge "Tạo từ quét QR". (TC-INC-PARITY-01)
// • PM / CM / Calibration assert qua props SmartSelect (parity): modelValue=id,
//   disabled=true, badge giữ nguyên. (TC-PM/CM/CAL-PARITY-01)
// • TC-NOLEAK-01: text render KHÔNG chứa raw qr_token / status enum EN đứng một mình.
import fs from 'node:fs'
import path from 'node:path'
import { VIEWS } from '@/test/paths'

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const pushSpy = vi.fn().mockResolvedValue(undefined)
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

// ── API stubs cho cả 4 view (mount-only, không gọi BE) ──────────────────────
vi.mock('@/api/imm12', () => ({
  reportIncident: vi.fn().mockResolvedValue({ name: 'INC-0001' }),
  getIncident: vi.fn().mockResolvedValue(null),
}))
vi.mock('@/api/imm08', () => ({
  createAdhocPMWorkOrder: vi.fn().mockResolvedValue({ name: 'PM-WO-0001' }),
}))
vi.mock('@/api/imm09', () => ({
  searchSpareParts: vi.fn().mockResolvedValue([]),
  requestSpareParts: vi.fn().mockResolvedValue(null),
  createRepairWorkOrder: vi.fn().mockResolvedValue({ name: 'WO-RP-0001' }),
}))
vi.mock('@/api/imm11', () => ({
  createCalibration: vi.fn().mockResolvedValue({ name: 'CAL-0001' }),
}))
vi.mock('@/api/imm16', () => ({
  checkAssetComplianceStatus: vi.fn().mockResolvedValue(null),
}))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn().mockResolvedValue({ file_url: '' }) }))
// getAssetActionMeta NẠC perm-aware (panel meta loader Vòng 25) — trả null để panel
// meta ẩn, không nhiễu label test. getAsset giữ mock cho hoàn chỉnh module.
vi.mock('@/api/imm00', () => ({
  getAssetActionMeta: vi.fn().mockResolvedValue(null),
  getAsset: vi.fn().mockResolvedValue(null),
}))
vi.mock('@/composables/useFormDraft', () => ({ useFormDraft: () => ({ clear: vi.fn() }) }))
vi.mock('@/composables/useApi', () => ({ useApi: () => ({ run: vi.fn().mockResolvedValue(null) }) }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))

// frappeGet được dùng bởi: (1) view loaders, (2) masterData store (resolveOne /
// fetchDoctype). Trả về theo endpoint để store.resolveOne resolve được TS-X NHƯNG
// fetchDoctype (full-list) trả RỖNG → asset KHÔNG nằm trong getItems ban đầu.
const ASSET_NAME = 'Máy thở Dräger Evita V500'
const frappeGetSpy = vi.fn((endpoint: string, params?: Record<string, unknown>) => {
  if (typeof endpoint === 'string' && endpoint.includes('imm04.search_link')) {
    // resolveOne truyền query=<id>; full-list fetchDoctype truyền query=''.
    if (params && params.query === 'TS-X') {
      return Promise.resolve([{ value: 'TS-X', label: ASSET_NAME, description: 'AC-CODE-001' }])
    }
    return Promise.resolve([]) // full-list rỗng → asset không có trong getItems
  }
  return Promise.resolve(null)
})
vi.mock('@/api/helpers', () => ({
  frappeGet: (...args: unknown[]) => frappeGetSpy(...(args as [string, Record<string, unknown>?])),
  frappePost: vi.fn().mockResolvedValue(null),
}))

import IncidentCreateView from '@/views/incident/IncidentCreateView.vue'
import PMWorkOrderCreateView from '@/views/pm/PMWorkOrderCreateView.vue'
import CMCreateView from '@/views/cm/CMCreateView.vue'
import CalibrationCreateView from '@/views/calibration/CalibrationCreateView.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'

function assetSelect(w: ReturnType<typeof mount>) {
  return w.findAllComponents(SmartSelect).find(c => c.props('doctype') === 'AC Asset')!
}

beforeEach(() => {
  setActivePinia(createPinia())
  routeQuery = { asset: 'TS-X', source: 'qr-scan' }
  pushSpy.mockClear()
  frappeGetSpy.mockClear()
})

describe('TC-INC-PARITY-01 — IncidentCreateView (SmartSelect THẬT, end-to-end label resolution)', () => {
  it('khoá QR + cache getItems rỗng → resolveOne → nút khoá hiển thị TÊN thiết bị', async () => {
    const w = mount(IncidentCreateView)
    await flushPromises()
    await flushPromises()

    const ss = assetSelect(w)
    expect(ss.exists()).toBe(true)
    expect(ss.props('modelValue')).toBe('TS-X')
    expect(ss.props('disabled')).toBe(true)

    // End-to-end: nút khoá render TÊN đọc-được (không raw 'TS-X' đứng một mình xám).
    expect(w.text()).toContain(ASSET_NAME)
    // Badge giữ nguyên.
    expect(w.text()).toContain('Tạo từ quét QR')
    // Trigger button vẫn disabled.
    expect(ss.get('button[type="button"]').attributes('disabled')).toBeDefined()
  })

  it('TC-NOLEAK-01: KHÔNG leak raw qr_token / status enum EN đứng một mình', async () => {
    const w = mount(IncidentCreateView)
    await flushPromises()
    await flushPromises()
    const t = w.text()
    expect(t).not.toContain('qr_token')
    expect(t).not.toMatch(/\bDecommissioned\b/)
    expect(t).not.toMatch(/\bActive\b/)
  })

  it('no-regression: source lạ → KHÔNG khoá (SmartSelect editable)', async () => {
    routeQuery = { asset: 'TS-X', source: 'manual' }
    const w = mount(IncidentCreateView)
    await flushPromises()
    expect(assetSelect(w).props('disabled')).toBe(false)
    expect(w.text()).not.toContain('Tạo từ quét QR')
  })
})

describe('TC-PM-PARITY-01 — PMWorkOrderCreateView', () => {
  it('khoá QR: SmartSelect modelValue=TS-X, disabled, badge; label resolve qua resolveOne', async () => {
    const w = mount(PMWorkOrderCreateView, { global: { stubs: { DateInput: true } } })
    await flushPromises()
    await flushPromises()
    const ss = assetSelect(w)
    expect(ss.props('modelValue')).toBe('TS-X')
    expect(ss.props('disabled')).toBe(true)
    expect(w.text()).toContain('Tạo từ quét QR')
    // SmartSelect THẬT (không stub) → label resolve tên thiết bị.
    expect(w.text()).toContain(ASSET_NAME)
  })
})

describe('TC-CM-PARITY-01 — CMCreateView', () => {
  it('khoá QR: SmartSelect modelValue=TS-X, disabled, badge; label resolve qua resolveOne', async () => {
    const w = mount(CMCreateView)
    await flushPromises()
    await flushPromises()
    const ss = assetSelect(w)
    expect(ss.props('modelValue')).toBe('TS-X')
    expect(ss.props('disabled')).toBe(true)
    expect(w.text()).toContain('Tạo từ quét QR')
    expect(w.text()).toContain(ASSET_NAME)
  })
})

describe('TC-CAL-PARITY-01 — CalibrationCreateView', () => {
  it('khoá QR: SmartSelect modelValue=TS-X, disabled, badge; label resolve qua resolveOne', async () => {
    const w = mount(CalibrationCreateView)
    await flushPromises()
    await flushPromises()
    const ss = assetSelect(w)
    expect(ss.props('modelValue')).toBe('TS-X')
    expect(ss.props('disabled')).toBe(true)
    expect(w.text()).toContain('Tạo từ quét QR')
    expect(w.text()).toContain(ASSET_NAME)
  })
})

// TC-PARITY-NO-CLIENTGETVALUE-4VIEW (IMM-00 vòng 23 · BUG-META-1) — grep-style:
// cả 4 create-view scan-action (Incident/CM/Cal/PM) PHẢI KHÔNG còn dùng raw
// frappe.client.get_value trong LOADER ASSET-META (LL-FE-40). Static-source assert
// → khoá hồi quy: ai đó tái thêm raw RPC vào loader asset-meta sẽ FAIL test này.
// CHÚ Ý: chỉ soi thân hàm loadAssetMeta() — các loader KHÁC (calibration-schedule,
// PM-template checklist) vẫn được phép dùng frappe.client.get/get_value (ngoài scope).
describe('TC-PARITY-NO-CLIENTGETVALUE-4VIEW — loader asset-meta 4 view không còn frappe.client.get_value', () => {
  // fs/path import tĩnh ở đầu file (ESM) — `require()` không hợp lệ trong ESM
  // và bị @typescript-eslint/no-require-imports chặn.
  // CM/Cal/PM có hàm loadAssetMeta() → soi thân hàm. Incident KHÔNG có panel
  // asset-meta riêng (chỉ SmartSelect label-resolution) → assert whole-file sạch.
  const LOADER_VIEWS: Record<string, string> = {
    CM: 'cm/CMCreateView.vue',
    Calibration: 'calibration/CalibrationCreateView.vue',
    PM: 'pm/PMWorkOrderCreateView.vue',
  }

  // Trích thân hàm loadAssetMeta() (asset-meta loader) bằng cân bằng ngoặc nhọn từ
  // 'async function loadAssetMeta'. Loại comment dòng để 'KHÔNG dùng
  // frappe.client.get_value (LL-FE-40)' không bị tính nhầm.
  function loaderBody(src: string): string {
    const start = src.indexOf('async function loadAssetMeta')
    expect(start).toBeGreaterThanOrEqual(0)
    const open = src.indexOf('{', start)
    let depth = 0
    let end = open
    for (let i = open; i < src.length; i++) {
      if (src[i] === '{') depth++
      else if (src[i] === '}') { depth--; if (depth === 0) { end = i; break } }
    }
    const body = src.slice(open, end + 1)
    // bỏ comment dòng // ... để không bắt nhầm wording LL-FE-40 trong chú thích.
    return body.replace(/\/\/[^\n]*/g, '')
  }

  for (const [label, rel] of Object.entries(LOADER_VIEWS)) {
    it(`${label}: loadAssetMeta() KHÔNG dùng 'frappe.client.get_value' (perm-aware getAssetActionMeta)`, () => {
      const src = fs.readFileSync(path.resolve(VIEWS, rel), 'utf8')
      const body = loaderBody(src)
      expect(body).not.toContain('frappe.client.get_value')
      // parity dương: loader PHẢI gọi getAssetActionMeta NẠC (Vòng 25 over-fetch close);
      // KHÔNG còn getAsset full-doc tài chính cho panel meta.
      expect(body).toContain('getAssetActionMeta(')
      expect(body).not.toContain('getAsset(')
    })
  }

  it('Incident: KHÔNG nạp asset-meta qua raw RPC (whole-file sạch frappe.client.get_value)', () => {
    const src = fs.readFileSync(path.resolve(VIEWS, 'incident/IncidentCreateView.vue'), 'utf8')
    // Loại comment dòng // ... TRƯỚC khi assert: wording cảnh báo LL-FE-40
    // ("KHÔNG dùng frappe.client.get_value") nằm trong chú thích, KHÔNG phải code
    // thật — chỉ bắt lời-gọi RPC THẬT (parity với loaderBody() ở trên).
    const code = src.replace(/\/\/[^\n]*/g, '')
    expect(code).not.toContain('frappe.client.get_value')
  })
})
