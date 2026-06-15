// TDD — Vòng 38 (risk_classification): AssetScanInfoView card ĐỊNH DANH · dòng 'Phân loại rủi ro'.
//   AC Asset.risk_classification là enum EN 'Low/Medium/High/Critical' (read-only,
//   fetch_from device_model). BE GIỮ raw enum làm SSoT contract (KHÔNG dịch) → FE
//   map sang VI qua SSoT RISK_CLASSIFICATION_LABEL/riskClassificationLabel.
//   Yêu cầu (no-raw-EN-leak + no-em-dash, parity serialText vòng 37):
//     • 'High'→'Cao'; 'Low'→'Thấp'; 'Medium'→'Trung bình'; 'Critical'→'Nghiêm trọng'.
//     • rỗng ('' / null / '   ' whitespace) → 'Chưa phân loại' (KHÔNG '—' câm, KHÔNG
//       chứa EN thô, KHÔNG chứa info.name = docname Frappe nội bộ).
//     • giá trị NGOÀI 4 enum ('UNKNOWN_DRIFT') → 'Khác' (KHÔNG leak chuỗi EN thô).
//     • riskText TUYỆT ĐỐI KHÔNG fallback info.name — info.name='AST-0001' +
//       risk_classification rỗng → scan-risk KHÔNG chứa 'AST-0001'.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const routeParams = ref<Record<string, string>>({ id: 'AC-ASSET-2026-00042' })
const replaceSpy = vi.fn().mockResolvedValue(undefined)
const pushSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: replaceSpy, push: pushSpy, resolve: vi.fn() }),
  useRoute: () => ({ get params() { return routeParams.value } }),
}))

const getAssetScanInfoSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  getAssetScanInfo: (p: { token?: string; name?: string }) => getAssetScanInfoSpy(p),
}))

import AssetScanInfoView from './AssetScanInfoView.vue'

// Base payload — đủ key để view ready; chỉ risk_classification/name xoay theo TC.
const BASE = {
  name: 'AC-ASSET-2026-00042',
  asset_code: 'A-042',
  asset_name: 'Máy thở Dräger Evita',
  manufacturer_sn: 'SN-12345',
  risk_classification: 'High',
  device_model_name: 'Evita V500',
  location_name: 'ICU - Tầng 3',
  lifecycle_status: 'Active',
  recent_maintenance: { event_type: 'pm_completed', date: '2026-05-30' },
  next_pm_date: '2026-08-30',
  pm_overdue: false,
  next_calibration_date: '2026-09-15',
  calibration_overdue: false,
  available_actions: [],
}

const riskLine = (w: ReturnType<typeof mount>) => w.get('[data-test="scan-risk"]')

describe('AssetScanInfoView — card định danh dòng "Phân loại rủi ro" (vòng 38)', () => {
  beforeEach(() => {
    replaceSpy.mockClear(); pushSpy.mockClear()
    getAssetScanInfoSpy.mockReset()
    routeParams.value = { id: 'AC-ASSET-2026-00042' }
  })

  // TC1a — enum rủi ro THẤP (Low/Medium) → nhãn VI đúng, dòng EXACT (KHÔNG chip
  //   urgency — no false-alarm vòng 47), styling slate neutral GIỮ NGUYÊN.
  const LOW_RISK_CASES: Array<[string, string]> = [
    ['Low', 'Thấp'],
    ['Medium', 'Trung bình'],
  ]
  for (const [raw, vi_label] of LOW_RISK_CASES) {
    it(`TC1a: risk_classification="${raw}" → scan-risk EXACT "${vi_label}" (KHÔNG chip urgency)`, async () => {
      getAssetScanInfoSpy.mockResolvedValue({ ...BASE, risk_classification: raw })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      const line = riskLine(w)
      // dòng EXACT (không có chip urgency thêm vào text).
      expect(line.text()).toBe(`Phân loại rủi ro: ${vi_label}`)
      expect(line.text()).not.toContain(raw)
      // no false-alarm: KHÔNG render phần tử cảnh báo.
      expect(w.find('[data-test="scan-risk-urgent"]').exists()).toBe(false)
    })
  }

  // TC1b — enum rủi ro CAO (High/Critical) → nhãn VI nội dung GIỮ NGUYÊN (no-regress
  //   vòng 38/40) NHƯNG dòng thêm chip urgency 'Rủi ro cao' (vòng 47). Dùng .toContain
  //   cho nhãn nội dung; assert riêng phần tử scan-risk-urgent (role/aria VI + chip).
  //   KHÔNG leak enum EN thô ('High'/'Critical') ra dòng risk / aria.
  const HIGH_RISK_CASES: Array<[string, string]> = [
    ['High', 'Cao'],
    ['Critical', 'Nghiêm trọng'],
  ]
  for (const [raw, vi_label] of HIGH_RISK_CASES) {
    it(`TC1b: risk_classification="${raw}" → "${vi_label}" (no-regress) + chip urgency 'Rủi ro cao' (vòng 47)`, async () => {
      getAssetScanInfoSpy.mockResolvedValue({ ...BASE, risk_classification: raw })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      const line = riskLine(w)
      // nhãn nội dung VI GIỮ NGUYÊN (no-regress vòng 38/40).
      expect(line.text()).toContain(`Phân loại rủi ro: ${vi_label}`)
      // chip urgency hiển thị.
      expect(line.text()).toContain('Rủi ro cao')
      // phần tử cảnh báo: role hợp lệ + aria-label VI.
      const urgent = w.find('[data-test="scan-risk-urgent"]')
      expect(urgent.exists()).toBe(true)
      expect(['status', 'alert']).toContain(urgent.attributes('role'))
      expect(urgent.attributes('aria-label')).toBe('Cảnh báo: thiết bị rủi ro cao')
      // KHÔNG leak chuỗi EN thô của enum (dòng + aria).
      expect(line.text()).not.toContain(raw)
      expect(urgent.attributes('aria-label')).not.toContain(raw)
    })
  }

  // TC2 — rỗng ('' / null / whitespace) → 'Chưa phân loại'; KHÔNG '—', KHÔNG EN,
  //   KHÔNG chứa info.name (docname Frappe nội bộ).
  const EMPTY_CASES: Array<[string, unknown]> = [
    ['empty-string', ''],
    ['null', null],
    ['whitespace', '   '],
  ]
  for (const [tag, val] of EMPTY_CASES) {
    it(`TC2: risk_classification=${tag} → "Chưa phân loại", KHÔNG "—"/EN/docname`, async () => {
      const DOCNAME = 'AST-0001'
      getAssetScanInfoSpy.mockResolvedValue({
        ...BASE, risk_classification: val, name: DOCNAME,
      })
      const w = mount(AssetScanInfoView)
      await flushPromises()
      const line = riskLine(w)
      expect(line.text()).toBe('Phân loại rủi ro: Chưa phân loại')
      expect(line.text()).not.toContain('—')
      // no-raw-EN-leak: KHÔNG lọt enum EN nào.
      for (const en of ['Low', 'Medium', 'High', 'Critical']) {
        expect(line.text()).not.toContain(en)
      }
      // chống leak docname Frappe qua fallback.
      expect(line.text()).not.toContain(DOCNAME)
    })
  }

  // TC3 — field ABSENT (undefined — payload partial/stale) → 'Chưa phân loại',
  //   KHÔNG 'undefined', KHÔNG crash, KHÔNG docname.
  it('TC3: risk_classification ABSENT (undefined) → "Chưa phân loại", KHÔNG "undefined"/crash', async () => {
    const DOCNAME = 'AST-0001'
    const partial: Record<string, unknown> = { ...BASE, name: DOCNAME }
    delete partial.risk_classification
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = riskLine(w)
    expect(line.text()).toBe('Phân loại rủi ro: Chưa phân loại')
    expect(line.text()).not.toContain('undefined')
    expect(line.text()).not.toContain(DOCNAME)
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  // TC4 — giá trị NGOÀI 4 enum (drift/legacy) → 'Khác' (KHÔNG leak chuỗi EN thô).
  it('TC4: risk_classification="UNKNOWN_DRIFT" (ngoài enum) → "Khác" (KHÔNG leak EN thô)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, risk_classification: 'UNKNOWN_DRIFT' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = riskLine(w)
    expect(line.text()).toBe('Phân loại rủi ro: Khác')
    // ASSERT CHÍNH: chuỗi EN drift KHÔNG bao giờ lọt ra UI.
    expect(line.text()).not.toContain('UNKNOWN_DRIFT')
  })

  // TC5 (assert CHÍNH chống leak docname): info.name='AST-0001' NHƯNG
  //   risk_classification rỗng → scan-risk KHÔNG chứa 'AST-0001' (riskText KHÔNG
  //   fallback info.name). Mount THẬT (REAL-RENDER LL-FE-46).
  it('TC5 (REAL-RENDER): name="AST-0001" + risk rỗng → scan-risk KHÔNG chứa "AST-0001"', async () => {
    const DOCNAME = 'AST-0001'
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, risk_classification: '', name: DOCNAME,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = riskLine(w)
    expect(line.text()).toBe('Phân loại rủi ro: Chưa phân loại')
    expect(line.text()).not.toContain(DOCNAME)
    // KHÔNG crash → không màn lỗi.
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  // ── helpers nguồn (strip CẢ //-comment LẪN <!-- --> Vue-comment) ────────────
  const readSrc = () => readFileSync(resolve(__dirname, 'AssetScanInfoView.vue'), 'utf8')
  const stripComments = (src: string) =>
    src
      .replace(/<!--[\s\S]*?-->/g, '')        // Vue/HTML block comment
      .split('\n')
      .map((l) => l.replace(/\/\/.*$/, ''))   // JS line comment
      .join('\n')
  // Trích RIÊNG biểu thức dòng dán nhãn 'Phân loại rủi ro' (KHÔNG lẫn dòng khác).
  const riskLineExpr = (src: string) => {
    const m = src.match(/Phân loại rủi ro:\s*\{\{([^}]*)\}\}/)
    return m ? m[1].trim() : ''
  }

  // TC6 (SSoT guard NGUỒN): dòng dán nhãn 'Phân loại rủi ro' bind computed riskText —
  //   KHÔNG raw 'info.name' / '|| info.name' / '|| name' last-resort. 'Chưa phân loại'
  //   khai báo ĐÚNG 1 lần (const, ngoài comment) — KHÔNG rải chuỗi.
  it('TC6 (SSoT guard): dòng risk = {{ riskText }}, KHÔNG info.name/|| name; "Chưa phân loại" 1 lần', () => {
    const codeOnly = stripComments(readSrc())
    expect((codeOnly.match(/Chưa phân loại/g) ?? []).length).toBe(1)
    const expr = riskLineExpr(codeOnly)
    expect(expr).toBe('riskText')
    expect(expr).not.toContain('info.name')
    expect(expr).not.toContain('|| info.name')
    expect(expr).not.toContain('|| name')
  })

  // TC7 (revert-proof LL-TEST-26): chứng minh fallback `risk_classification || info.name`
  //   SẼ leak DOCNAME với payload risk-rỗng; riskText (rỗng → 'Chưa phân loại') chặn
  //   được → guard có răng.
  it('TC7 (revert-proof): nguồn hiện tại chặn leak; fallback `risk || info.name` bị revert SẼ leak docname', () => {
    const DOCNAME = 'AST-0001'
    const expr = riskLineExpr(stripComments(readSrc()))
    expect(expr).toBe('riskText')
    // hành vi riskText (presence-aware trim) với risk rỗng → nhãn SSoT.
    const riskText = (rc: unknown) => {
      const raw = (typeof rc === 'string' ? rc : (rc ?? '') as string).toString().trim()
      return raw || 'Chưa phân loại'
    }
    expect(riskText('')).toBe('Chưa phân loại')
    expect(riskText('')).not.toContain(DOCNAME)
    // fallback NẾU bị revert: risk='' falsy → rơi info.name = docname (LEAK).
    const revertedFallback = (rc: string, name: string) => rc || name
    expect(revertedFallback('', DOCNAME)).toBe(DOCNAME) // ← điều riskText PHẢI chặn
  })
})
