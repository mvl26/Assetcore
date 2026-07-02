// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 Vòng 25 scan-action — over-fetch close) — CMCreateView:
// panel meta thiết bị PHẢI nạp qua getAssetActionMeta(name) NẠC perm-aware
// (api/imm00.ts) — KHÔNG getAsset (full doc rò giá mua/khấu hao/giá trị sổ sách),
// KHÔNG raw frappe.client.get_value (LL-FE-40).
//
// Acceptance (Task FE — asset-meta loader over-fetch close):
//   • route {asset, source:'qr-scan'} → getAssetActionMeta('AC-ASSET-0001') ĐƯỢC
//     gọi (KHÔNG getAsset) VÀ frappeGet KHÔNG gọi '/api/method/frappe.client.get_value'.
//   • payload mock KHÔNG chứa field tài chính ⟹ panel render 5 dòng đúng:
//     asset_name / device_model_name (KHÔNG raw id) / location_name (KHÔNG id) /
//     risk_classification / trạng thái VI (SSoT).
//   • em-dash → 'Chưa gán': risk_classification rỗng/thiếu → 'Chưa gán' (KHÔNG '—').
//   • fail-safe: getAssetActionMeta reject → assetMeta=null, không throw, không leak.
//   • no-regression manual path: không source → watch gọi getAssetActionMeta, panel
//     nạp đúng; canSubmit gating Decommissioned vẫn chặn.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
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

// frappeGet là RAW RPC — slice này PHẢI KHÔNG còn dùng cho asset-meta.
const frappeGetSpy = vi.fn().mockResolvedValue(null)
vi.mock('@/api/helpers', () => ({
  frappeGet: (...args: unknown[]) => frappeGetSpy(...args),
  frappePost: vi.fn().mockResolvedValue(null),
}))

// getAssetActionMeta NẠC perm-aware (api/imm00) — loader mới (over-fetch close).
// getAsset cũng mock để KHẲNG ĐỊNH panel KHÔNG còn gọi nó (full-doc tài chính).
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
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))

import CMCreateView from './CMCreateView.vue'

function mountView() {
  return mount(CMCreateView, { global: { stubs: { SmartSelect: true } } })
}

// Payload NẠC (6 field, KHÔNG field tài chính) — đúng shape AssetActionMeta BE trả.
// risk_classification = enum THẬT của AC Asset ∈ {Low,Medium,High,Critical}
// (fetch_from device_model). KHÔNG 'C'/'D' — đó là risk_class (A/B/C/D) field KHÁC.
const META = {
  name: 'AC-ASSET-0001',
  asset_name: 'Máy thở Dräger V500',
  device_model_name: 'Dräger Evita V500',
  lifecycle_status: 'Active',
  risk_classification: 'High',
  location_name: 'Khoa Hồi sức tích cực',
}

describe('CMCreateView — panel meta qua getAssetActionMeta (NẠC perm-aware)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    routeQuery = {}
    pushSpy.mockClear()
    frappeGetSpy.mockClear()
    getActionMetaSpy.mockReset()
    getActionMetaSpy.mockResolvedValue(META)
    getAssetSpy.mockReset()
    getAssetSpy.mockResolvedValue(META)
  })

  it('qr-scan: gọi getAssetActionMeta (KHÔNG getAsset), KHÔNG gọi frappe.client.get_value', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()

    expect(getActionMetaSpy).toHaveBeenCalledWith('AC-ASSET-0001')
    // KHÔNG còn kéo full-doc tài chính qua getAsset chỉ để render panel meta.
    expect(getAssetSpy).not.toHaveBeenCalled()
    // frappeGet KHÔNG được gọi tới endpoint raw RPC cho asset-meta.
    for (const call of frappeGetSpy.mock.calls) {
      expect(String(call[0])).not.toContain('frappe.client.get_value')
    }

    const t = w.text()
    expect(t).toContain('Máy thở Dräger V500')        // asset_name
    expect(t).toContain('Dräger Evita V500')           // device_model_name (KHÔNG raw id)
    expect(t).toContain('Khoa Hồi sức tích cực')       // location_name (KHÔNG location id)
    expect(t).toContain('Cao')                         // risk_classification 'High' → VI SSoT
    expect(t).not.toContain('High')                    // no EN-leak risk enum
    expect(t).toContain('Đang hoạt động')              // lifecycle_status VI qua SSoT
    expect(t).not.toContain('Active')                  // no EN-leak
  })

  it('payload NẠC KHÔNG field tài chính → panel render 5 dòng đúng (no over-fetch leak)', async () => {
    // BE meta NẠC KHÔNG trả gross_purchase_amount/current_book_value/... → panel
    // chỉ render 5 dòng meta. (Field tài chính dù lọt vào payload cũng KHÔNG render.)
    getActionMetaSpy.mockResolvedValue({
      ...META,
      gross_purchase_amount: 850_000_000,
      current_book_value: 600_000_000,
    })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const t = w.text()
    expect(t).toContain('Máy thở Dräger V500')
    expect(t).toContain('Dräger Evita V500')
    expect(t).toContain('Khoa Hồi sức tích cực')
    expect(t).not.toContain('850000000')   // KHÔNG render giá mua
    expect(t).not.toContain('600000000')   // KHÔNG render giá trị sổ sách
  })

  // Ô "Mức rủi ro" trong panel meta — bám anchor data-test ổn định (Vòng 43:
  // thay heuristic findAll('div').startsWith('Risk class:') fragile bằng anchor).
  function riskCellText(w: ReturnType<typeof mountView>) {
    return w.find('[data-test="scan-cm-meta-risk"]').text()
  }

  // AC1 / AC2 — map enum THẬT risk_classification → nhãn VI qua SSoT
  // riskClassificationLabel. KHÔNG bao giờ leak raw EN (Low/Medium/High/Critical).
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

  it('no-EN-leak DOM: với mỗi enum, KHÔNG chuỗi EN nào trong {Low,Medium,High,Critical} lọt panel', async () => {
    for (const [raw] of RISK_VI_CASES) {
      getActionMetaSpy.mockResolvedValue({ ...META, risk_classification: raw })
      routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
      const w = mountView()
      await flushPromises()
      const cell = riskCellText(w)
      for (const en of ['Low', 'Medium', 'High', 'Critical']) {
        expect(cell).not.toContain(en)
      }
      w.unmount()
    }
  })

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
    // panel ẩn (assetMeta=null) — KHÔNG render tên field meta + KHÔNG leak raw exception.
    const t = w.text()
    expect(t).not.toContain('user@evil.com')
    expect(t).not.toContain('qr_token')
    expect(t).not.toContain('IDOR')
    // trang vẫn còn (heading tồn tại)
    expect(t).toContain('Tạo Phiếu Sửa Chữa')
  })

  // ── AC4: isHighRisk derive từ ĐÚNG enum risk_classification ∈ {High, Critical}
  // (KHÔNG 'C'/'D' — đó là risk_class field KHÁC). Banner QA-phê-duyệt + style cam
  // HIỆN khi High/Critical; ẨN khi Low/Medium/''/drift/legacy 'C'. ──
  const QA_BANNER = 'bắt buộc đảm bảo chất lượng phê duyệt'
  const HIGH_RISK_CASES = ['High', 'Critical']
  const LOW_RISK_CASES = ['Low', 'Medium', '', 'C', 'Xyz']

  it.each(HIGH_RISK_CASES)(
    'AC4 isHighRisk: risk_classification "%s" ⇒ banner QA-phê-duyệt HIỆN + class cam',
    async (raw) => {
      getActionMetaSpy.mockResolvedValue({ ...META, risk_classification: raw })
      routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
      const w = mountView()
      await flushPromises()
      expect(w.text()).toContain(QA_BANNER)
      // style cam: panel meta risk cell mang class cam khi isHighRisk
      expect(w.html()).toContain('bg-orange-50')
    },
  )

  it.each(LOW_RISK_CASES)(
    'AC4 isHighRisk: risk_classification "%s" ⇒ banner QA-phê-duyệt ẨN (câm cũ phải FAIL→PASS sau fix)',
    async (raw) => {
      getActionMetaSpy.mockResolvedValue({ ...META, risk_classification: raw })
      routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
      const w = mountView()
      await flushPromises()
      expect(w.text()).not.toContain(QA_BANNER)
    },
  )

  it('AC5 banner no-EN-leak: risk_classification "Critical" ⇒ dòng banner chứa "Nghiêm trọng" (KHÔNG "Critical"/"undefined")', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, risk_classification: 'Critical' })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    // tìm dòng banner cảnh báo (alert-warning) chứa cụm QA-phê-duyệt
    const banner = w.findAll('div').filter(d => d.text().includes(QA_BANNER))
      .map(d => d.text()).sort((a, b) => a.length - b.length)[0]
    expect(banner).toContain('Nghiêm trọng')
    expect(banner).not.toContain('Critical')
    expect(banner).not.toContain('undefined')
  })

  it('AC5 banner no-EN-leak: risk_classification "High" ⇒ banner chứa "Cao" (KHÔNG "High")', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, risk_classification: 'High' })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const banner = w.findAll('div').filter(d => d.text().includes(QA_BANNER))
      .map(d => d.text()).sort((a, b) => a.length - b.length)[0]
    expect(banner).toContain('Cao')
    expect(banner).not.toContain('High')
    expect(banner).not.toContain('undefined')
  })

  it('no-regression manual path: không source → watch gọi getAssetActionMeta, gating Decommissioned chặn submit', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, lifecycle_status: 'Decommissioned' })
    routeQuery = { asset: 'AC-ASSET-0001' } // không source=qr-scan → manual
    const w = mountView()
    await flushPromises()
    expect(getActionMetaSpy).toHaveBeenCalledWith('AC-ASSET-0001')
    // Decommissioned → banner cảnh báo + nút submit disabled (canSubmit=false).
    expect(w.text()).toContain('Thiết bị đã thanh lý')
    const submitBtn = w.findAll('button').find(b => b.text().includes('Tạo phiếu sửa chữa'))!
    expect(submitBtn.attributes('disabled')).toBeDefined()
  })

  // ════════════════════════════════════════════════════════════════════════
  // Vòng 43 — Parity a11y + i18n + test-anchor cho panel meta CM (scan-action)
  // (ngang panel Incident round 26: <section data-test aria-labelledby> + <dl>/<dt>/<dd>)
  // ════════════════════════════════════════════════════════════════════════

  // CM-A11Y-1 (đỏ-trước): panel render khi qr-scan + meta đủ; container có
  // aria-labelledby trỏ tới <h3 id> tồn tại (screen-reader đọc được nhãn-giá-trị).
  it('CM-A11Y-1: panel <section data-test="scan-cm-meta"> có aria-labelledby trỏ tới <h3 id> tồn tại', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const section = w.find('[data-test="scan-cm-meta"]')
    expect(section.exists()).toBe(true)
    const labelledby = section.attributes('aria-labelledby')
    expect(labelledby).toBeTruthy()
    // <h3 id="..."> mà aria-labelledby trỏ tới PHẢI tồn tại trong DOM
    const heading = w.find(`#${labelledby}`)
    expect(heading.exists()).toBe(true)
    expect(heading.element.tagName).toBe('H3')
    expect(heading.text().length).toBeGreaterThan(0)
    // markup a11y: dl/dt/dd
    expect(section.find('dl').exists()).toBe(true)
    expect(section.findAll('dt').length).toBeGreaterThanOrEqual(5)
    expect(section.findAll('dd').length).toBeGreaterThanOrEqual(5)
  })

  // CM-I18N-2 (đỏ-trước): bịt EN-leak 'Risk class:' → 'Mức rủi ro:'; ô risk chứa
  // nhãn VI rủi ro (KHÔNG raw EN, KHÔNG '—').
  it('CM-I18N-2: KHÔNG còn "Risk class"; ô risk chứa "Mức rủi ro" + nhãn VI (KHÔNG "Medium"/"—")', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, risk_classification: 'Medium' })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    // grep render: KHÔNG chuỗi 'Risk class' bất kỳ đâu trong panel
    expect(w.text()).not.toContain('Risk class')
    const cell = w.find('[data-test="scan-cm-meta-risk"]')
    expect(cell.exists()).toBe(true)
    expect(cell.text()).toContain('Mức rủi ro')
    expect(cell.text()).toContain('Trung bình')   // VI cho 'Medium'
    expect(cell.text()).not.toContain('Medium')   // KHÔNG raw EN
    expect(cell.text()).not.toContain('—')
  })

  // CM-ANCHOR-3: từng ô data-test scan-cm-meta-{name,model,location,status} chứa
  // đúng giá trị mock (display-name VI), KHÔNG raw Link id, KHÔNG 'Active'.
  it('CM-ANCHOR-3: scan-cm-meta-{name,model,location,status} chứa đúng giá trị mock (display-name, KHÔNG raw id/Active)', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-test="scan-cm-meta-name"]').text()).toContain('Máy thở Dräger V500')
    expect(w.find('[data-test="scan-cm-meta-model"]').text()).toContain('Dräger Evita V500')
    expect(w.find('[data-test="scan-cm-meta-model"]').text()).not.toContain('AC-ASSET-0001')
    expect(w.find('[data-test="scan-cm-meta-location"]').text()).toContain('Khoa Hồi sức tích cực')
    const status = w.find('[data-test="scan-cm-meta-status"]')
    expect(status.text()).toContain('Đang hoạt động')   // 'Active' → VI SSoT
    expect(status.text()).not.toContain('Active')
  })

  // CM-SAFE-4 (no-regress nhãn rỗng): model=''/location=''/status=''/risk='' →
  // 'Chưa gán' (KHÔNG '—'), status nhãn VI an toàn, risk 'Chưa phân loại'.
  it('CM-SAFE-4: model/location rỗng → "Chưa gán" (KHÔNG "—"); status rỗng → VI an toàn; risk rỗng → "Chưa phân loại"', async () => {
    getActionMetaSpy.mockResolvedValue({
      ...META, device_model_name: '', location_name: '', lifecycle_status: '', risk_classification: '',
    })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const model = w.find('[data-test="scan-cm-meta-model"]')
    const location = w.find('[data-test="scan-cm-meta-location"]')
    const status = w.find('[data-test="scan-cm-meta-status"]')
    const risk = w.find('[data-test="scan-cm-meta-risk"]')
    expect(model.text()).toContain('Chưa gán')
    expect(model.text()).not.toContain('—')
    expect(location.text()).toContain('Chưa gán')
    expect(location.text()).not.toContain('—')
    expect(status.text()).not.toContain('—')
    expect(status.text()).not.toContain('Active')
    expect(risk.text()).toContain('Chưa phân loại')
    expect(risk.text()).not.toContain('—')
  })

  // CM-FLAG-5 (no-regress cờ): Decommissioned → ô status class đỏ; High/Critical →
  // isHighRisk → ô risk class cam + alert-warning QA GIỮ nguyên.
  it('CM-FLAG-5a: status="Decommissioned" → ô scan-cm-meta-status có class đỏ', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, lifecycle_status: 'Decommissioned' })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const status = w.find('[data-test="scan-cm-meta-status"]')
    expect(status.classes().some(c => c.includes('red'))).toBe(true)
  })

  it('CM-FLAG-5b: risk High/Critical → ô scan-cm-meta-risk class cam + banner QA GIỮ nguyên', async () => {
    for (const raw of ['High', 'Critical']) {
      getActionMetaSpy.mockResolvedValue({ ...META, risk_classification: raw })
      routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
      const w = mountView()
      await flushPromises()
      const risk = w.find('[data-test="scan-cm-meta-risk"]')
      expect(risk.classes().some(c => c.includes('orange'))).toBe(true)
      expect(w.text()).toContain('bắt buộc đảm bảo chất lượng phê duyệt')
      w.unmount()
    }
  })
})
