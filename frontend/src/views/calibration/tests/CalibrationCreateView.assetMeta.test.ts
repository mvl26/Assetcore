// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 Vòng 25 scan-action — over-fetch close) — CalibrationCreateView:
// panel meta thiết bị PHẢI nạp qua getAssetActionMeta(name) NẠC perm-aware
// (api/imm00.ts) — KHÔNG getAsset (full doc rò giá mua/khấu hao/giá trị sổ sách),
// KHÔNG raw frappe.client.get_value (LL-FE-40).
//
// Acceptance (Task FE — asset-meta loader over-fetch close):
//   • route {asset, source:'qr-scan'} → getAssetActionMeta('AC-ASSET-0001') ĐƯỢC
//     gọi (KHÔNG getAsset) VÀ frappeGet KHÔNG gọi 'frappe.client.get_value' cho meta.
//   • payload NẠC (KHÔNG field tài chính) → panel "Mức rủi ro" render 'C' khi
//     risk_classification='C'; field cũ 'risk_class' đã bỏ.
//   • em-dash → 'Chưa gán': risk_classification rỗng → 'Chưa gán' (KHÔNG '—').
//   • fail-safe: getAssetActionMeta reject → assetMeta=null, không vỡ trang, không leak.
//   • no-regression manual path: không source → watch gọi getAssetActionMeta, panel nạp đúng.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const pushSpy = vi.fn().mockResolvedValue(undefined)
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

vi.mock('@/api/imm11', () => ({
  createCalibration: vi.fn().mockResolvedValue({ name: 'CAL-2026-00001' }),
  listCalibrationSchedules: vi.fn().mockResolvedValue({ data: [] }),
  getCalibrationSchedule: vi.fn().mockResolvedValue(null),
}))

// frappeGet raw RPC: loadSchedule ĐÃ chuyển sang getCalibrationSchedule perm-aware
// (GATE-4/LL-FE-40 đóng nốt) — view không còn đường raw nào; assert dưới giữ làm
// regression guard: asset-meta KHÔNG được gọi raw (path != AC Asset get_value).
const frappeGetSpy = vi.fn().mockResolvedValue(null)
vi.mock('@/api/helpers', () => ({
  frappeGet: (...args: unknown[]) => frappeGetSpy(...args),
  frappePost: vi.fn().mockResolvedValue(null),
}))

const getActionMetaSpy = vi.fn()
const getAssetSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  getAssetActionMeta: (...args: unknown[]) => getActionMetaSpy(...args),
  getAsset: (...args: unknown[]) => getAssetSpy(...args),
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

import CalibrationCreateView from '@/views/calibration/CalibrationCreateView.vue'

function mountView() {
  return mount(CalibrationCreateView, {
    global: { stubs: { SmartSelect: true, DateInput: true } },
  })
}

// Payload NẠC (6 field, KHÔNG field tài chính) — đúng shape AssetActionMeta BE trả.
// risk_classification = enum THẬT của AC Asset ∈ {Low,Medium,High,Critical}
// (fetch_from device_model). KHÔNG 'C'/'D' — đó là risk_class (A/B/C/D) field KHÁC.
const META = {
  name: 'AC-ASSET-0001',
  asset_name: 'Máy đo SpO2 Masimo',
  device_model_name: 'Masimo Radical-7',
  lifecycle_status: 'Active',
  risk_classification: 'High',
  location_name: 'Khoa Cấp cứu',
}

describe('CalibrationCreateView — panel meta qua getAssetActionMeta (NẠC perm-aware)', () => {
  beforeEach(() => {
    routeQuery = {}
    pushSpy.mockClear()
    frappeGetSpy.mockClear()
    getActionMetaSpy.mockReset()
    getActionMetaSpy.mockResolvedValue(META)
    getAssetSpy.mockReset()
    getAssetSpy.mockResolvedValue(META)
  })

  it('qr-scan: gọi getAssetActionMeta (KHÔNG getAsset), KHÔNG gọi frappe.client.get_value cho meta', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()

    expect(getActionMetaSpy).toHaveBeenCalledWith('AC-ASSET-0001')
    expect(getAssetSpy).not.toHaveBeenCalled()  // KHÔNG kéo full-doc tài chính cho panel
    // KHÔNG dùng raw RPC để lấy asset-meta của AC Asset.
    for (const call of frappeGetSpy.mock.calls) {
      const path = String(call[0])
      const params = call[1] as { doctype?: string } | undefined
      if (path.includes('frappe.client.get_value')) {
        expect(params?.doctype).not.toBe('AC Asset')
      }
    }

    const t = w.text()
    expect(t).toContain('Máy đo SpO2 Masimo')          // asset_name
    expect(t).toContain('Masimo Radical-7')             // device_model_name
    expect(t).toContain('Khoa Cấp cứu')                 // location_name
    expect(t).toContain('Đang hoạt động')               // lifecycle_status VI SSoT
    expect(t).not.toContain('Active')                   // no EN-leak
  })

  it('payload NẠC KHÔNG field tài chính → panel render đúng, KHÔNG render giá', async () => {
    getActionMetaSpy.mockResolvedValue({
      ...META,
      gross_purchase_amount: 250_000_000,
      current_book_value: 120_000_000,
    })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const t = w.text()
    expect(t).toContain('Máy đo SpO2 Masimo')
    expect(t).not.toContain('250000000')
    expect(t).not.toContain('120000000')
  })

  // Ô "Mức rủi ro" trong panel meta — bám anchor data-test ổn định (Vòng 43:
  // thay heuristic findAll('div').startsWith('Mức rủi ro:') fragile bằng anchor).
  function riskCellText(w: ReturnType<typeof mountView>) {
    return w.find('[data-test="scan-cal-meta-risk"]').text()
  }

  // AC2 — map enum THẬT risk_classification → nhãn VI qua SSoT riskClassificationLabel,
  // parity AC1 màn CM. KHÔNG bao giờ leak raw EN (Low/Medium/High/Critical).
  const RISK_VI_CASES: Array<[string, string]> = [
    ['Low', 'Thấp'],
    ['Medium', 'Trung bình'],
    ['High', 'Cao'],
    ['Critical', 'Nghiêm trọng'],
  ]
  it.each(RISK_VI_CASES)(
    'panel "Mức rủi ro": risk_classification "%s" → nhãn VI "%s" (KHÔNG raw EN)',
    async (raw, vi) => {
      getActionMetaSpy.mockResolvedValue({ ...META, risk_classification: raw })
      routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
      const w = mountView()
      await flushPromises()
      const cell = riskCellText(w)
      expect(cell).toContain(vi)
      expect(cell).not.toContain(raw)   // no raw EN enum leak
      expect(cell).not.toContain('—')
      expect(cell).not.toContain('Chưa gán')
    },
  )

  it('AC3 presence-aware: risk_classification rỗng → "Chưa phân loại" (KHÔNG "—", parity scan-info Vòng 38)', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, risk_classification: '' })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const cell = riskCellText(w)
    expect(cell).toContain('Chưa phân loại')
    expect(cell).not.toContain('—')
    expect(cell).not.toContain('Chưa gán')   // nhãn rỗng cũ đã bỏ — 1 SSoT scan-info
  })

  it('AC3 drift: giá trị NGOÀI 4 enum (legacy "Xyz") → "Khác" (KHÔNG leak raw)', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, risk_classification: 'Xyz' })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const cell = riskCellText(w)
    expect(cell).toContain('Khác')
    expect(cell).not.toContain('Xyz')
  })

  it('fail-safe: getAssetActionMeta reject → assetMeta=null, không vỡ trang, không leak exc/email/token', async () => {
    getActionMetaSpy.mockRejectedValue(
      Object.assign(new Error('IDOR vendor leak user@evil.com qr_token=abc123'), { httpStatus: 403 }),
    )
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const t = w.text()
    expect(t).not.toContain('user@evil.com')
    expect(t).not.toContain('qr_token')
    expect(t).not.toContain('IDOR')
    expect(t).toContain('Tạo Phiếu Hiệu chuẩn')
  })

  it('no-regression manual path: không source → watch gọi getAssetActionMeta, panel nạp đúng', async () => {
    routeQuery = { asset: 'AC-ASSET-0001' } // không source=qr-scan → manual
    const w = mountView()
    await flushPromises()
    expect(getActionMetaSpy).toHaveBeenCalledWith('AC-ASSET-0001')
    expect(w.text()).toContain('Máy đo SpO2 Masimo')
  })

  it('gating Decommissioned vẫn chặn submit khi meta load được', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, lifecycle_status: 'Decommissioned' })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    expect(w.text()).toContain('Thiết bị đã thanh lý')
    const submitBtn = w.findAll('button').find(b => b.text().includes('Tạo phiếu'))!
    expect(submitBtn.attributes('disabled')).toBeDefined()
  })

  // ════════════════════════════════════════════════════════════════════════
  // Vòng 43 — Parity a11y + test-anchor cho panel meta Cal (scan-action)
  // (mirror CM-A11Y-1/CM-ANCHOR-3; ngang panel Incident round 26)
  // ════════════════════════════════════════════════════════════════════════

  // CAL-A11Y-6 (mirror CM-A11Y-1): panel <section data-test="scan-cal-meta"> có
  // aria-labelledby trỏ tới <h3 id> tồn tại + cấu trúc <dl>/<dt>/<dd>.
  it('CAL-A11Y-6: panel <section data-test="scan-cal-meta"> có aria-labelledby trỏ tới <h3 id> tồn tại', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const section = w.find('[data-test="scan-cal-meta"]')
    expect(section.exists()).toBe(true)
    const labelledby = section.attributes('aria-labelledby')
    expect(labelledby).toBeTruthy()
    const heading = w.find(`#${labelledby}`)
    expect(heading.exists()).toBe(true)
    expect(heading.element.tagName).toBe('H3')
    expect(heading.text().length).toBeGreaterThan(0)
    expect(section.find('dl').exists()).toBe(true)
    expect(section.findAll('dt').length).toBeGreaterThanOrEqual(5)
    expect(section.findAll('dd').length).toBeGreaterThanOrEqual(5)
  })

  // CAL-ANCHOR-7 (mirror CM-ANCHOR-3): từng ô data-test scan-cal-meta-{name,model,
  // location,status,risk} chứa đúng giá trị mock (display-name VI, KHÔNG raw id/Active).
  it('CAL-ANCHOR-7: scan-cal-meta-{name,model,location,status,risk} chứa đúng giá trị mock (display-name, KHÔNG raw id/Active)', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-test="scan-cal-meta-name"]').text()).toContain('Máy đo SpO2 Masimo')
    expect(w.find('[data-test="scan-cal-meta-model"]').text()).toContain('Masimo Radical-7')
    expect(w.find('[data-test="scan-cal-meta-model"]').text()).not.toContain('AC-ASSET-0001')
    expect(w.find('[data-test="scan-cal-meta-location"]').text()).toContain('Khoa Cấp cứu')
    const status = w.find('[data-test="scan-cal-meta-status"]')
    expect(status.text()).toContain('Đang hoạt động')
    expect(status.text()).not.toContain('Active')
    const risk = w.find('[data-test="scan-cal-meta-risk"]')
    expect(risk.text()).toContain('Mức rủi ro')
    expect(risk.text()).toContain('Cao')       // 'High' → VI
    expect(risk.text()).not.toContain('High')
  })

  // CAL-SAFE-8 (no-regress nhãn rỗng): model=''/location=''/status=''/risk='' →
  // 'Chưa gán' (KHÔNG '—'); status VI an toàn; risk 'Chưa phân loại'.
  it('CAL-SAFE-8: model/location rỗng → "Chưa gán"; status rỗng → VI an toàn; risk rỗng → "Chưa phân loại" (KHÔNG "—")', async () => {
    getActionMetaSpy.mockResolvedValue({
      ...META, device_model_name: '', location_name: '', lifecycle_status: '', risk_classification: '',
    })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const model = w.find('[data-test="scan-cal-meta-model"]')
    const location = w.find('[data-test="scan-cal-meta-location"]')
    const status = w.find('[data-test="scan-cal-meta-status"]')
    const risk = w.find('[data-test="scan-cal-meta-risk"]')
    expect(model.text()).toContain('Chưa gán')
    expect(model.text()).not.toContain('—')
    expect(location.text()).toContain('Chưa gán')
    expect(location.text()).not.toContain('—')
    expect(status.text()).not.toContain('—')
    expect(status.text()).not.toContain('Active')
    expect(risk.text()).toContain('Chưa phân loại')
    expect(risk.text()).not.toContain('—')
  })

  // CAL-FLAG (no-regress cờ): status='Decommissioned' → ô status class đỏ GIỮ.
  it('CAL-FLAG: status="Decommissioned" → ô scan-cal-meta-status có class đỏ', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, lifecycle_status: 'Decommissioned' })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const status = w.find('[data-test="scan-cal-meta-status"]')
    expect(status.classes().some(c => c.includes('red'))).toBe(true)
  })
})
