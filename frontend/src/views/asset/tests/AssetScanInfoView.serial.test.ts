// TDD — Vòng 37 (D5 / NĐ98): AssetScanInfoView card ĐỊNH DANH · dòng 'Số serial NSX'.
//   KTV xác nhận ĐÚNG thiết bị vật lý (định danh truy xuất) TRƯỚC khi báo hỏng/tạo WO.
//   BE build_asset_scan_info LUÔN emit manufacturer_sn as str (coalesce '' khi rỗng).
//   Yêu cầu:
//     • manufacturer_sn='SN-12345' → [data-test=scan-serial] hiển thị 'SN-12345' (no-regress).
//     • manufacturer_sn rỗng ('' / null / '   ' whitespace) → 'Chưa rõ' (nhãn VI SSoT),
//       KHÔNG '—' câm, KHÔNG chứa info.name (docname Frappe nội bộ — record-ID thô).
//     • serialText TUYỆT ĐỐI KHÔNG fallback info.name — chỉ manufacturer_sn || 'Chưa rõ':
//       info.name='ASSET-HASH-9f' + manufacturer_sn rỗng → scan-serial == 'Chưa rõ'
//       (KHÔNG bao giờ == info.name) → chống leak docname qua dòng serial.
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

import AssetScanInfoView from '@/views/asset/AssetScanInfoView.vue'

// Base payload — đủ key để view ready; chỉ manufacturer_sn/name xoay theo TC.
const BASE = {
  name: 'AC-ASSET-2026-00042',
  asset_code: 'A-042',
  asset_name: 'Máy thở Dräger Evita',
  manufacturer_sn: 'SN-12345',
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

const serialLine = (w: ReturnType<typeof mount>) => w.get('[data-test="scan-serial"]')

describe('AssetScanInfoView — card định danh dòng "Số serial NSX" (D5 / NĐ98)', () => {
  beforeEach(() => {
    replaceSpy.mockClear(); pushSpy.mockClear()
    getAssetScanInfoSpy.mockReset()
    routeParams.value = { id: 'AC-ASSET-2026-00042' }
  })

  // TC1 — no-regress: manufacturer_sn có giá trị thật → render NGUYÊN VĂN.
  it('TC1: manufacturer_sn="SN-12345" → scan-serial chứa "SN-12345" (no-regress)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, manufacturer_sn: 'SN-12345' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = serialLine(w)
    expect(line.text()).toContain('SN-12345')
    expect(line.text()).toBe('Số serial NSX: SN-12345')
    // KHÔNG rơi nhãn 'Chưa rõ' khi có giá trị thật.
    expect(line.text()).not.toContain('Chưa rõ')
  })

  // TC2 (assert CHÍNH no-em-dash + no-raw-docname-leak): manufacturer_sn='' + name=docname →
  //   'Số serial NSX: Chưa rõ' VÀ tuyệt đối KHÔNG '—' / docname dưới dòng serial.
  it('TC2: manufacturer_sn="" + name="ASSET-HASH-9f" → "Chưa rõ", KHÔNG "—", KHÔNG leak docname', async () => {
    const DOCNAME = 'ASSET-HASH-9f'
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, manufacturer_sn: '', name: DOCNAME,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = serialLine(w)
    expect(line.text()).toBe('Số serial NSX: Chưa rõ')
    // ASSERT CHÍNH: KHÔNG '—' câm, KHÔNG docname nội bộ lọt xuống dòng serial.
    expect(line.text()).not.toContain('—')
    expect(line.text()).not.toContain(DOCNAME)
    expect(line.text()).not.toBe(DOCNAME)
  })

  // TC3: manufacturer_sn=null (payload drift) → 'Chưa rõ', KHÔNG 'null', KHÔNG info.name.
  it('TC3: manufacturer_sn=null + name=docname → "Chưa rõ", KHÔNG "null", KHÔNG info.name', async () => {
    const DOCNAME = 'ASSET-HASH-9f'
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, manufacturer_sn: null, name: DOCNAME,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = serialLine(w)
    expect(line.text()).toBe('Số serial NSX: Chưa rõ')
    expect(line.text()).not.toContain('null')
    expect(line.text()).not.toContain(DOCNAME)
  })

  // TC4: manufacturer_sn='   ' (chỉ whitespace) → trim → rỗng → 'Chưa rõ', KHÔNG docname.
  it('TC4: manufacturer_sn="   " (whitespace) + name=docname → trim → "Chưa rõ", KHÔNG leak docname', async () => {
    const DOCNAME = 'ASSET-HASH-9f'
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, manufacturer_sn: '   ', name: DOCNAME,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = serialLine(w)
    expect(line.text()).toBe('Số serial NSX: Chưa rõ')
    expect(line.text()).not.toContain(DOCNAME)
  })

  // TC5 (assert CHÍNH chống leak docname): info.name='ASSET-HASH-9f' NHƯNG manufacturer_sn
  //   rỗng → scan-serial == 'Chưa rõ' (KHÔNG bao giờ == info.name) — serialText KHÔNG
  //   fallback info.name. Mount THẬT (REAL-RENDER LL-FE-46).
  it('TC5 (REAL-RENDER): name="ASSET-HASH-9f" + manufacturer_sn rỗng → scan-serial === "Chưa rõ" (KHÔNG bao giờ === info.name)', async () => {
    const DOCNAME = 'ASSET-HASH-9f'
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, manufacturer_sn: '', name: DOCNAME,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = serialLine(w)
    // serial-value == 'Chưa rõ' (sau dán nhãn) — tuyệt đối KHÔNG == docname.
    expect(line.text()).toBe('Số serial NSX: Chưa rõ')
    expect(line.text()).not.toContain(DOCNAME)
    // KHÔNG crash → không màn lỗi.
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  // TC6: manufacturer_sn field ABSENT (undefined — payload partial/stale) → 'Chưa rõ',
  //   KHÔNG 'undefined', KHÔNG crash, KHÔNG info.name.
  it('TC6: manufacturer_sn ABSENT (undefined) → "Chưa rõ", KHÔNG "undefined", KHÔNG crash', async () => {
    const DOCNAME = 'ASSET-HASH-9f'
    const partial: Record<string, unknown> = { ...BASE, name: DOCNAME }
    delete partial.manufacturer_sn
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = serialLine(w)
    expect(line.text()).toBe('Số serial NSX: Chưa rõ')
    expect(line.text()).not.toContain('undefined')
    expect(line.text()).not.toContain(DOCNAME)
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  // ── helpers nguồn (strip CẢ //-comment LẪN <!-- --> Vue-comment) ────────────
  const readSrc = () => readFileSync(resolve(__dirname, '..', 'AssetScanInfoView.vue'), 'utf8')
  const stripComments = (src: string) =>
    src
      .replace(/<!--[\s\S]*?-->/g, '')        // Vue/HTML block comment
      .split('\n')
      .map((l) => l.replace(/\/\/.*$/, ''))   // JS line comment
      .join('\n')
  // Trích RIÊNG biểu thức dòng dán nhãn 'Số serial NSX' (KHÔNG lẫn dòng khác).
  const serialLineExpr = (src: string) => {
    const m = src.match(/Số serial NSX:\s*\{\{([^}]*)\}\}/)
    return m ? m[1].trim() : ''
  }

  // TC7 (SSoT guard NGUỒN): 'Chưa rõ' khai báo ĐÚNG 1 LẦN (const, ngoài comment);
  //   dòng dán nhãn 'Số serial NSX' bind computed serialText — KHÔNG còn raw
  //   'info.name' / '|| info.name' / '|| name' last-resort.
  it('TC7 (SSoT guard): "Chưa rõ" 1 lần (ngoài comment); dòng serial = {{ serialText }}, KHÔNG info.name/|| name', () => {
    const codeOnly = stripComments(readSrc())
    // literal VI SSoT khai báo ĐÚNG 1 lần (trong const) — KHÔNG rải chuỗi.
    expect((codeOnly.match(/Chưa rõ(?!\s*ngày)/g) ?? []).length).toBe(1)
    const expr = serialLineExpr(codeOnly)
    expect(expr).toBe('serialText')
    expect(expr).not.toContain('info.name')
    expect(expr).not.toContain('|| info.name')
    expect(expr).not.toContain('|| name')
  })

  // TC8 (revert-proof LL-TEST-26): chứng minh fallback `manufacturer_sn || info.name`
  //   SẼ leak DOCNAME với payload SN-rỗng; serialText (manufacturer_sn || 'Chưa rõ')
  //   chặn được → guard có răng.
  it('TC8 (revert-proof): nguồn hiện tại chặn leak; fallback `manufacturer_sn || info.name` bị revert SẼ leak docname', () => {
    const DOCNAME = 'ASSET-HASH-9f'
    // (a) nguồn hiện tại: dòng serial bind serialText → không thể leak docname.
    const expr = serialLineExpr(stripComments(readSrc()))
    expect(expr).toBe('serialText')
    // (b) hành vi serialText (presence-aware trim) với manufacturer_sn rỗng → nhãn SSoT.
    const serialText = (manufacturer_sn: unknown) =>
      (typeof manufacturer_sn === 'string' ? manufacturer_sn : (manufacturer_sn ?? '') as string)
        .toString().trim() || 'Chưa rõ'
    expect(serialText('')).toBe('Chưa rõ')
    expect(serialText('')).not.toContain(DOCNAME)
    // (c) fallback NẾU bị revert: SN='' falsy → rơi info.name = docname (LEAK).
    const revertedFallback = (manufacturer_sn: string, name: string) => manufacturer_sn || name
    expect(revertedFallback('', DOCNAME)).toBe(DOCNAME) // ← điều serialText PHẢI chặn
  })
})
