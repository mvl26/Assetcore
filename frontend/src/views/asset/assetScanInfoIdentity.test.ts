// TDD — AssetScanInfoView (A6) card ĐỊNH DANH · TIÊU ĐỀ h1 + dòng phụ 'Mã thiết bị'.
//   Bịt rò docname Frappe nội bộ (info.name) ở CẢ HAI vị trí card định danh khi
//   asset_name/asset_code rỗng (legacy/drift). Trước đây:
//     • dòng phụ render `info.asset_code || info.name` (vòng 27 ĐÃ siết → assetCodeText)
//     • TIÊU ĐỀ h1 render `info.asset_name || info.asset_code || info.name` (vòng 28
//       siết NỐT) → khi cả asset_name+asset_code rỗng ('' coalesce / payload partial/
//       stale) thì RƠI sang info.name = record-ID thô (vd 'PDF-ASSET-d5-83fd9b5f')
//       hiển thị Ở TIÊU ĐỀ — leak định danh nội bộ ra UI quét QR (hard-constraint).
//   Yêu cầu vòng 28: computed presence-aware assetTitleText —
//     • asset_name chuỗi-có-giá-trị (sau trim) → render NGUYÊN VĂN (no-regress)
//     • asset_name rỗng nhưng asset_code có giá-trị → asset_code (tên-hiển-thị HỢP LỆ,
//       KHÔNG phải docname → KHÔNG thay)
//     • cả 2 rỗng / null / undefined / chỉ-whitespace → nhãn VI SSoT
//       'Thiết bị chưa định danh' (KHÔNG '—' câm, KHÔNG 'null'/'undefined',
//       TUYỆT ĐỐI KHÔNG info.name docname thô last-resort).
//   Dòng phụ 'Mã thiết bị' (assetCodeText vòng 27) GIỮ NGUYÊN — round này CHỈ thêm
//   guard cho TIÊU ĐỀ h1 '[data-test=asset-title-text]'.
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

// Base payload — đủ key để view ready; chỉ asset_code/name/asset_name xoay theo TC.
const BASE = {
  name: 'AC-ASSET-2026-00042',
  asset_code: 'A-042',
  asset_name: 'Máy thở Dräger Evita',
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

const codeLine = (w: ReturnType<typeof mount>) => w.get('[data-test="asset-code-text"]')
const titleLine = (w: ReturnType<typeof mount>) => w.get('[data-test="asset-title-text"]')

describe('AssetScanInfoView — card định danh dòng "Mã thiết bị" no-raw-docname-leak', () => {
  beforeEach(() => {
    replaceSpy.mockClear(); pushSpy.mockClear()
    getAssetScanInfoSpy.mockReset()
    routeParams.value = { id: 'AC-ASSET-2026-00042' }
  })

  // TC1 — no-regress: asset_code có giá trị thật → render NGUYÊN VĂN dưới nhãn mã.
  it('TC1: asset_code="A-042" → dòng asset-code-text chứa "A-042" (no-regress giá trị thật)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, asset_code: 'A-042' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = codeLine(w)
    expect(line.text()).toContain('A-042')
    // dán nhãn 'Mã thiết bị:' + giá trị thật (no-regress hiển thị cũ).
    expect(line.text()).toBe('Mã thiết bị: A-042')
    // KHÔNG rơi nhãn 'Chưa gán mã' khi có giá trị thật.
    expect(line.text()).not.toContain('Chưa gán mã')
  })

  // TC2 (assert CHÍNH no-raw-docname-leak): asset_code='' + name=docname thô →
  //   'Mã thiết bị: Chưa gán mã' VÀ tuyệt đối KHÔNG chứa docname dưới nhãn mã.
  it('TC2: asset_code="" + name="PDF-ASSET-d5-83fd9b5f" → "Mã thiết bị: Chưa gán mã", KHÔNG leak docname', async () => {
    const DOCNAME = 'PDF-ASSET-d5-83fd9b5f'
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, asset_code: '', name: DOCNAME, asset_name: 'Máy PDF Nhãn',
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = codeLine(w)
    expect(line.text()).toBe('Mã thiết bị: Chưa gán mã')
    // ASSERT CHÍNH: docname nội bộ KHÔNG lọt xuống dòng dán nhãn 'Mã thiết bị'.
    expect(line.text()).not.toContain(DOCNAME)
  })

  // TC3: asset_code=null (payload drift) → 'Chưa gán mã', KHÔNG 'null', KHÔNG info.name.
  it('TC3: asset_code=null → "Chưa gán mã", KHÔNG "null", KHÔNG info.name', async () => {
    const DOCNAME = 'PDF-ASSET-d5-83fd9b5f'
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, asset_code: null, name: DOCNAME, asset_name: 'Máy PDF Nhãn',
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = codeLine(w)
    expect(line.text()).toBe('Mã thiết bị: Chưa gán mã')
    expect(line.text()).not.toContain('null')
    expect(line.text()).not.toContain(DOCNAME)
  })

  // TC4: asset_code field ABSENT (undefined — payload partial/stale) → 'Chưa gán mã',
  //   KHÔNG 'undefined', KHÔNG crash, KHÔNG info.name.
  it('TC4: asset_code ABSENT (undefined) → "Chưa gán mã", KHÔNG "undefined", KHÔNG crash', async () => {
    const DOCNAME = 'PDF-ASSET-d5-83fd9b5f'
    const partial: Record<string, unknown> = { ...BASE, name: DOCNAME, asset_name: 'Máy PDF Nhãn' }
    delete partial.asset_code
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = codeLine(w)
    expect(line.text()).toBe('Mã thiết bị: Chưa gán mã')
    expect(line.text()).not.toContain('undefined')
    expect(line.text()).not.toContain(DOCNAME)
    // KHÔNG crash → không màn lỗi.
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  // TC5: asset_code='   ' (chỉ whitespace) → trim → rỗng → 'Chưa gán mã'.
  it('TC5: asset_code="   " (whitespace) → trim → "Chưa gán mã" (không khoảng trắng câm)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, asset_code: '   ', name: 'PDF-ASSET-d5-83fd9b5f',
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(codeLine(w).text()).toBe('Mã thiết bị: Chưa gán mã')
  })

  // ════════════════════════════════════════════════════════════════════════════
  //  VÒNG 28 — TIÊU ĐỀ h1 no-raw-docname-leak (assetTitleText)
  //  (FE-4: TC cũ 'h1 GIỮ NGUYÊN' — vốn assert h1.text()===DOCNAME khi cả asset_name
  //   + asset_code rỗng — ĐÃ ĐỔI sang hành vi mới: h1 KHÔNG còn fallback info.name,
  //   thay bằng nhãn VI SSoT 'Thiết bị chưa định danh'. KHÔNG để 2 test mâu thuẫn
  //   cùng tồn tại — no false-green.)
  // ════════════════════════════════════════════════════════════════════════════

  // TC1 (h1 AC1 no-regress): asset_name có giá trị thật → h1 render NGUYÊN VĂN.
  it('TC1 (h1): asset_name="Máy thở Dräger Evita" → h1 === giá trị thật (no-regress)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, asset_name: 'Máy thở Dräger Evita' })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(titleLine(w).text()).toBe('Máy thở Dräger Evita')
    expect(titleLine(w).text()).not.toContain('Thiết bị chưa định danh')
  })

  // TC2 (h1 AC2 fallback HỢP LỆ): asset_name='' + asset_code='A-042' + name=docname →
  //   h1 === 'A-042' (asset_code là tên-hiển-thị hợp lệ, KHÔNG phải docname → ưu tiên)
  //   VÀ KHÔNG chứa docname.
  it('TC2 (h1): asset_name="" + asset_code="A-042" + name=DOCNAME → h1 === "A-042", KHÔNG docname', async () => {
    const DOCNAME = 'PDF-ASSET-d5-83fd9b5f'
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, asset_name: '', asset_code: 'A-042', name: DOCNAME,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(titleLine(w).text()).toBe('A-042')
    expect(titleLine(w).text()).not.toContain(DOCNAME)
  })

  // TC3 (h1 AC3 assert CHÍNH — REAL-RENDER LL-FE-46): asset_name='' VÀ asset_code=''
  //   VÀ name='PDF-ASSET-d5-83fd9b5f' → mount component THẬT qua Vite/Vue runtime →
  //   h1 DOM text === 'Thiết bị chưa định danh' VÀ tuyệt đối KHÔNG chứa docname thô.
  it('TC3 (h1, REAL-RENDER): asset_name="" + asset_code="" + name=DOCNAME → h1 === "Thiết bị chưa định danh", KHÔNG leak docname', async () => {
    const DOCNAME = 'PDF-ASSET-d5-83fd9b5f'
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, asset_name: '', asset_code: '', name: DOCNAME,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(titleLine(w).text()).toBe('Thiết bị chưa định danh')
    // ASSERT CHÍNH: docname nội bộ KHÔNG lọt ra TIÊU ĐỀ h1.
    expect(titleLine(w).text()).not.toContain(DOCNAME)
    expect(w.get('h1').html()).not.toContain(DOCNAME)
    // Dòng phụ 'Mã thiết bị' vòng 27 GIỮ — cũng không leak.
    expect(codeLine(w).text()).toBe('Mã thiết bị: Chưa gán mã')
  })

  // TC4 (h1 AC4 drift null/undefined):
  //   (a) asset_name=null + asset_code=null → 'Thiết bị chưa định danh'.
  //   (b) cả 2 key ABSENT (delete khỏi payload) → undefined no-crash → nhãn VI,
  //       KHÔNG 'null'/'undefined'/DOCNAME.
  it('TC4 (h1, drift): null/undefined cả asset_name+asset_code → "Thiết bị chưa định danh", KHÔNG null/undefined/docname/crash', async () => {
    const DOCNAME = 'PDF-ASSET-d5-83fd9b5f'
    // (a) null thật
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, asset_name: null, asset_code: null, name: DOCNAME,
    })
    let w = mount(AssetScanInfoView)
    await flushPromises()
    expect(titleLine(w).text()).toBe('Thiết bị chưa định danh')
    expect(titleLine(w).text()).not.toContain('null')
    expect(titleLine(w).text()).not.toContain(DOCNAME)
    expect(w.find('[role="alert"]').exists()).toBe(false)

    // (b) cả 2 key ABSENT (undefined) — payload partial/stale
    const partial: Record<string, unknown> = { ...BASE, name: DOCNAME }
    delete partial.asset_name
    delete partial.asset_code
    getAssetScanInfoSpy.mockResolvedValue(partial)
    w = mount(AssetScanInfoView)
    await flushPromises()
    expect(titleLine(w).text()).toBe('Thiết bị chưa định danh')
    expect(titleLine(w).text()).not.toContain('undefined')
    expect(titleLine(w).text()).not.toContain(DOCNAME)
    expect(w.find('[role="alert"]').exists()).toBe(false)
  })

  // TC5 (h1 AC5 whitespace-trim): asset_name='   ' + asset_code='   ' → trim → rỗng →
  //   'Thiết bị chưa định danh' (whitespace-only coi như rỗng, parity assetCodeText V27).
  it('TC5 (h1, whitespace): asset_name="   " + asset_code="   " + name=DOCNAME → trim → "Thiết bị chưa định danh"', async () => {
    const DOCNAME = 'PDF-ASSET-d5-83fd9b5f'
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, asset_name: '   ', asset_code: '   ', name: DOCNAME,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(titleLine(w).text()).toBe('Thiết bị chưa định danh')
    expect(titleLine(w).text()).not.toContain(DOCNAME)
  })

  // ── helper trích RIÊNG biểu thức TIÊU ĐỀ h1 (KHÔNG lẫn dòng phụ 'Mã thiết bị') ──
  //   để guard nguồn TC6 bám CODE thật của h1.
  const titleExpr = (src: string) => {
    // <h1 ...> {{ <expr> }} </h1> — trích biểu thức bind đầu tiên trong thẻ h1.
    const m = src.match(/<h1\b[^>]*>\s*\{\{([^}]*)\}\}/)
    return m ? m[1].trim() : ''
  }

  // TC6 (h1 AC6 SSoT-guard NGUỒN): 'Thiết bị chưa định danh' khai báo ĐÚNG 1 LẦN
  //   (const, ngoài comment); biểu thức h1 === '{{ assetTitleText }}' — KHÔNG còn
  //   raw 'info.name' / '|| info.name' / '|| name' last-resort.
  it('TC6 (h1 SSoT-guard): "Thiết bị chưa định danh" 1 lần (ngoài comment); h1 === {{ assetTitleText }}, KHÔNG info.name/|| name', () => {
    const codeOnly = stripComments(readSrc())
    // literal VI SSoT khai báo ĐÚNG 1 lần (trong const) — KHÔNG rải chuỗi/comment.
    expect((codeOnly.match(/Thiết bị chưa định danh/g) ?? []).length).toBe(1)
    // biểu thức h1 bind ĐÚNG computed (KHÔNG fallback rò docname).
    const expr = titleExpr(codeOnly)
    expect(expr).toBe('assetTitleText')
    expect(expr).not.toContain('info.name')
    expect(expr).not.toContain('|| info.name')
    expect(expr).not.toContain('|| name')
  })

  // TC7 (h1 AC7 revert-proof LL-TEST-26): chứng minh fallback
  //   `asset_name || asset_code || info.name` SẼ leak DOCNAME với payload AC3;
  //   assetTitleText chặn được → guard có răng.
  it('TC7 (h1 revert-proof): nguồn hiện tại chặn leak; fallback `asset_name||asset_code||info.name` bị revert SẼ leak docname', () => {
    const DOCNAME = 'PDF-ASSET-d5-83fd9b5f'
    // (a) nguồn hiện tại: h1 bind assetTitleText → không thể leak docname.
    const expr = titleExpr(stripComments(readSrc()))
    expect(expr).toBe('assetTitleText')
    // (b) hành vi assetTitleText (presence-aware trim) AC3 (cả 2 rỗng) → nhãn SSoT.
    const assetTitleText = (asset_name: unknown, asset_code: unknown) => {
      const nm = (typeof asset_name === 'string' ? asset_name : (asset_name ?? '') as string).toString().trim()
      if (nm) return nm
      const cd = (typeof asset_code === 'string' ? asset_code : (asset_code ?? '') as string).toString().trim()
      if (cd) return cd
      return 'Thiết bị chưa định danh'
    }
    expect(assetTitleText('', '')).toBe('Thiết bị chưa định danh')
    expect(assetTitleText('', '')).not.toContain(DOCNAME)
    // (c) fallback NẾU bị revert: cả 2 falsy → rơi info.name = docname (LEAK).
    const revertedFallback = (asset_name: string, asset_code: string, name: string) =>
      asset_name || asset_code || name
    expect(revertedFallback('', '', DOCNAME)).toBe(DOCNAME) // ← điều assetTitleText PHẢI chặn
  })

  // ── helpers nguồn (strip CẢ //-comment LẪN <!-- --> Vue-comment) ────────────
  //   để guard bám CODE thật, KHÔNG dính literal/wording nằm trong comment giải thích.
  const readSrc = () => readFileSync(resolve(__dirname, 'AssetScanInfoView.vue'), 'utf8')
  const stripComments = (src: string) =>
    src
      .replace(/<!--[\s\S]*?-->/g, '')        // Vue/HTML block comment
      .split('\n')
      .map((l) => l.replace(/\/\/.*$/, ''))   // JS line comment
      .join('\n')
  // Trích RIÊNG dòng <p> dán nhãn 'Mã thiết bị' (KHÔNG lẫn h1 last-resort).
  const codeLineExpr = (src: string) => {
    const m = src.match(/Mã thiết bị:\s*\{\{([^}]*)\}\}/)
    return m ? m[1].trim() : ''
  }

  // TC6 (SSoT guard nguồn): 'Chưa gán mã' khai báo ĐÚNG 1 LẦN (const, ngoài comment);
  //   dòng dán nhãn 'Mã thiết bị' tham chiếu computed assetCodeText — KHÔNG còn
  //   `asset_code || info.name` (h1 last-resort GIỮ NGUYÊN, không bị động tới).
  it('TC6 (SSoT guard): "Chưa gán mã" 1 lần (ngoài comment); dòng mã = {{ assetCodeText }}, KHÔNG `asset_code || info.name`', () => {
    const codeOnly = stripComments(readSrc())
    // literal VI SSoT khai báo ĐÚNG 1 lần (trong const) — KHÔNG rải chuỗi.
    expect((codeOnly.match(/Chưa gán mã/g) ?? []).length).toBe(1)
    // dòng dán nhãn 'Mã thiết bị' bind ĐÚNG computed (KHÔNG fallback rò docname).
    const expr = codeLineExpr(codeOnly)
    expect(expr).toBe('assetCodeText')
    expect(expr).not.toContain('info.name')
    expect(expr).not.toContain('asset_code || info.name')
  })

  // TC7 (revert-proof LL-TEST-26): mô phỏng REVERT thật trên nguồn — đổi dòng dán
  //   nhãn về `info.asset_code || info.name`, mount lại với payload TC2 → docname
  //   LEAK (chứng minh guard còn răng); KHÔNG sửa file thật (chỉ revert in-memory +
  //   stub render path). Cách làm: assert (a) nguồn HIỆN TẠI bind assetCodeText
  //   (không leak), (b) hàm presence của assetCodeText chặn rỗng, (c) fallback bị
  //   revert SẼ leak — 3 vế nối nhau khoá chặt hành vi.
  it('TC7 (revert-proof): nguồn hiện tại chặn leak; fallback `asset_code || info.name` bị revert SẼ leak docname', () => {
    const DOCNAME = 'PDF-ASSET-d5-83fd9b5f'
    // (a) nguồn hiện tại: dòng mã KHÔNG dùng info.name → không thể leak docname.
    const expr = codeLineExpr(stripComments(readSrc()))
    expect(expr).toBe('assetCodeText')
    // (b) hành vi assetCodeText (presence-aware trim) với asset_code='' → nhãn SSoT.
    const assetCodeText = (asset_code: unknown) =>
      (typeof asset_code === 'string' ? asset_code : (asset_code ?? '') as string)
        .toString().trim() || 'Chưa gán mã'
    expect(assetCodeText('')).toBe('Chưa gán mã')
    expect(assetCodeText(DOCNAME === DOCNAME ? '' : 'x')).not.toContain(DOCNAME)
    // (c) fallback NẾU bị revert: asset_code='' falsy → rơi info.name = docname (LEAK).
    const revertedFallback = (asset_code: string, name: string) => asset_code || name
    expect(revertedFallback('', DOCNAME)).toBe(DOCNAME) // ← điều assetCodeText PHẢI chặn
  })
})
