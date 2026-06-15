// TDD — Vòng 49 (WARRANTY-CTA affordance): AssetScanInfoView — cụm CTA quét QR.
//   Nối cờ HẾT BẢO HÀNH (warranty_expired — derive SERVER-SIDE qua _is_warranty_expired,
//   vòng 48) với 2 CTA đường-SỬA (report_failure 'Báo hỏng' + request_cm 'Yêu cầu sửa
//   chữa') ở màn quét QR: nút mang affordance "ngoài bảo hành" (chip VI + màu phân biệt)
//   để KTV lường CHI PHÍ SỬA NGOÀI BẢO HÀNH TRƯỚC khi tạo phiếu.
//
// Map SSoT THUẦN-FE (presentation-only, KHÔNG thêm field BE, KHÔNG so client-clock):
//   WARRANTY_CTA_KEYS = {report_failure, request_cm}. request_pm/request_calibration
//   KHÔNG bao giờ mang affordance bảo hành (sai ngữ cảnh: bảo hành liên quan CHI PHÍ
//   SỬA, không liên quan PM/hiệu chuẩn).
//   isOutOfWarrantyCta(a) = effectiveEnabled(a) ∧ warrantyExpired.value ∧ a.key ∈ KEYS.
//   Disabled ưu tiên hơn affordance (KHÔNG dụ KTV bấm nút khoá — parity isOverdueCta).
//
// 2 TRỤC affordance (overdue vòng 21 + warranty vòng 49) ĐỘC LẬP, KHÔNG leak chéo:
//   overdue-key {request_pm, request_calibration} ∩ warranty-key {report_failure,
//   request_cm} = ∅ → thực tế KHÔNG trùng 1 nút, nhưng test PHẢI khẳng định không leak.
//
// Affordance bảo hành: chip text VI 'Ngoài bảo hành' (KHÔNG tái dùng URGENT_CTA_HINT
//   'Cần làm ngay') + attr data-warranty-cta=key + aria-label nối hậu tố VI (a11y:
//   không chỉ-màu, WCAG 1.4.1). no-EN-leak: KHÔNG 'Warranty'/'Out of warranty'/'Expired'.
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

// 4 CTA đủ enabled (Active + đủ cap, route resolvable) — shape MIRROR BE.
const ACTIONS_ALL_ENABLED = [
  { key: 'report_failure',      label: 'Báo hỏng',          route: 'IncidentCreate',    enabled: true, reason: '' },
  { key: 'request_pm',          label: 'Yêu cầu bảo trì',   route: 'PMWorkOrderCreate', enabled: true, reason: '' },
  { key: 'request_cm',          label: 'Yêu cầu sửa chữa',  route: 'CMCreate',          enabled: true, reason: '' },
  { key: 'request_calibration', label: 'Hiệu chuẩn',        route: 'CalibrationCreate', enabled: true, reason: '' },
]

const PAYLOAD = {
  name: 'AC-ASSET-2026-00042',
  asset_code: 'A-042',
  asset_name: 'Máy thở Dräger Evita',
  manufacturer_sn: 'SN-12345',
  risk_classification: 'Medium',
  device_model_name: 'Evita V500',
  location_name: 'ICU - Tầng 3',
  lifecycle_status: 'Active',
  recent_maintenance: { event_type: 'pm_completed', date: '2026-05-30' },
  next_pm_date: '2026-08-30',
  pm_overdue: false,
  next_calibration_date: '2026-09-15',
  calibration_overdue: false,
  warranty_expiry_date: '2027-05-01',
  warranty_expired: false,
  available_actions: ACTIONS_ALL_ENABLED,
}

// Nhãn VI affordance bảo hành (vòng 49) — KHÔNG tái dùng 'Cần làm ngay' (overdue).
const OUT_OF_WARRANTY_HINT = 'Ngoài bảo hành'
const URGENT_HINT = 'Cần làm ngay'

const actionBtn = (w: ReturnType<typeof mount>, key: string) =>
  w.find(`[data-action-key="${key}"]`)
// nút có affordance bảo hành = có attr data-warranty-cta == key.
const warrantyAttr = (w: ReturnType<typeof mount>, key: string) =>
  actionBtn(w, key).attributes('data-warranty-cta')
// chip affordance bảo hành ở bất kỳ đâu trong DOM (data-test ổn định).
const warrantyChip = (w: ReturnType<typeof mount>) => w.find('[data-test="cta-out-of-warranty"]')

describe('AssetScanInfoView — WARRANTY-CTA affordance "Ngoài bảo hành" (vòng 49)', () => {
  beforeEach(() => {
    replaceSpy.mockClear(); pushSpy.mockClear()
    getAssetScanInfoSpy.mockReset()
    routeParams.value = { id: 'AC-ASSET-2026-00042' }
  })

  // TC1 (REAL-RENDER, assert-chính): warranty_expired=true + report_failure & request_cm
  //   enabled (route resolvable) → 2 nút có affordance bảo hành (data-test + attr + chip
  //   text VI 'Ngoài bảo hành'), KHÔNG leak 'Warranty'/'Expired'/raw key.
  it("TC1: warranty_expired=true + report_failure & request_cm enabled → 2 nút có affordance 'Ngoài bảo hành' (data-test=cta-out-of-warranty), KHÔNG leak EN/raw key", async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, warranty_expired: true })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    // CHÍNH: chip affordance bảo hành xuất hiện thật (REAL-RENDER, data-test ổn định).
    expect(warrantyChip(w).exists()).toBe(true)
    // 2 nút đường-sửa mang affordance bảo hành (attr = key + chip text VI trong nút).
    for (const key of ['report_failure', 'request_cm']) {
      expect(warrantyAttr(w, key), `key=${key}`).toBe(key)
      expect(actionBtn(w, key).text(), `key=${key}`).toContain(OUT_OF_WARRANTY_HINT)
      // aria-label nối hậu tố VI cho affordance (a11y không chỉ-màu).
      expect(actionBtn(w, key).attributes('aria-label') ?? '', `key=${key} aria`).toContain(OUT_OF_WARRANTY_HINT)
    }
    // chip có nội dung text VI (KHÔNG chỉ màu).
    expect(warrantyChip(w).text()).toContain(OUT_OF_WARRANTY_HINT)
    // no-EN-leak: KHÔNG 'Warranty'/'Out of warranty'/'Expired' + KHÔNG raw key/route.
    const t = w.text()
    const html = w.html()
    for (const leak of ['Warranty', 'Out of warranty', 'Expired', 'warranty_expired',
      'report_failure', 'request_cm', 'IncidentCreate', 'CMCreate']) {
      expect(t, `text leak=${leak}`).not.toContain(leak)
    }
    // route name KHÔNG render ra nội dung DOM (data-* attr kỹ thuật là hợp lệ).
    for (const leak of ['IncidentCreate', 'CMCreate', 'report_failure', 'request_cm']) {
      expect(html, `html node leak=${leak}`).not.toContain('>' + leak + '<')
    }
  })

  // TC2: warranty_expired=false + cùng actions enabled → KHÔNG nút nào có affordance
  //   bảo hành (no false-alarm).
  it('TC2: warranty_expired=false + cùng actions enabled → KHÔNG affordance bảo hành (no false-alarm)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, warranty_expired: false })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(warrantyChip(w).exists()).toBe(false)
    for (const key of ['report_failure', 'request_pm', 'request_cm', 'request_calibration']) {
      expect(warrantyAttr(w, key), `key=${key}`).toBeUndefined()
      expect(actionBtn(w, key).text(), `key=${key}`).not.toContain(OUT_OF_WARRANTY_HINT)
    }
  })

  // TC3: warranty_expired ABSENT (delete key) / undefined → isOutOfWarrantyCta===false
  //   mọi nút, KHÔNG crash, KHÔNG render chip bảo hành.
  it('TC3: warranty_expired ABSENT (undefined) → KHÔNG affordance mọi nút, KHÔNG crash', async () => {
    const partial: Record<string, unknown> = { ...PAYLOAD }
    delete partial.warranty_expired
    getAssetScanInfoSpy.mockResolvedValue(partial)
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(warrantyChip(w).exists()).toBe(false)
    for (const key of ['report_failure', 'request_pm', 'request_cm', 'request_calibration']) {
      expect(warrantyAttr(w, key), `absent key=${key}`).toBeUndefined()
      expect(actionBtn(w, key).text(), `absent key=${key}`).not.toContain(OUT_OF_WARRANTY_HINT)
    }
    // vẫn render đủ 4 nút (no crash).
    expect(w.findAll('[data-action-key]').length).toBe(4)
  })

  // TC4: warranty_expired=true NHƯNG action.key ∈ {request_pm, request_calibration} →
  //   2 nút này KHÔNG có affordance bảo hành (chỉ report_failure/request_cm thuộc KEYS).
  it('TC4: warranty_expired=true + request_pm & request_calibration → 2 nút này KHÔNG affordance bảo hành (sai ngữ cảnh)', async () => {
    getAssetScanInfoSpy.mockResolvedValue({ ...PAYLOAD, warranty_expired: true })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    for (const key of ['request_pm', 'request_calibration']) {
      expect(warrantyAttr(w, key), `key=${key}`).toBeUndefined()
      expect(actionBtn(w, key).text(), `key=${key}`).not.toContain(OUT_OF_WARRANTY_HINT)
    }
    // còn 2 nút đường-sửa VẪN có affordance (no-regress TC1).
    expect(warrantyAttr(w, 'report_failure')).toBe('report_failure')
    expect(warrantyAttr(w, 'request_cm')).toBe('request_cm')
  })

  // TC5: warranty_expired=true NHƯNG report_failure enabled=false (BE disable vì
  //   lifecycle, vd Decommissioned) → KHÔNG affordance bảo hành (disabled ưu tiên),
  //   nút vẫn disabled + reason VI giữ nguyên.
  it('TC5: warranty_expired=true NHƯNG report_failure enabled=false (lifecycle) → KHÔNG affordance, nút vẫn disabled + reason cũ (disabled ưu tiên)', async () => {
    const REASON = 'Thiết bị đã thanh lý'
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      lifecycle_status: 'Decommissioned',
      warranty_expired: true,
      available_actions: [
        { key: 'report_failure', label: 'Báo hỏng',         route: 'IncidentCreate', enabled: false, reason: REASON },
        { key: 'request_cm',     label: 'Yêu cầu sửa chữa', route: 'CMCreate',       enabled: false, reason: REASON },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    for (const key of ['report_failure', 'request_cm']) {
      const b = actionBtn(w, key)
      // KHÔNG affordance bảo hành (disabled ưu tiên).
      expect(warrantyAttr(w, key), `key=${key}`).toBeUndefined()
      expect(b.text(), `key=${key}`).not.toContain(OUT_OF_WARRANTY_HINT)
      // nút vẫn disabled + reason VI giữ nguyên.
      expect(b.attributes('disabled'), `key=${key}`).toBeDefined()
      expect(b.attributes('aria-disabled'), `key=${key}`).toBe('true')
      expect(b.attributes('title'), `key=${key}`).toBe(REASON)
      // aria-label đi nhánh disabled, KHÔNG có hậu tố affordance bảo hành.
      expect(b.attributes('aria-label') ?? '', `key=${key} aria`).not.toContain(OUT_OF_WARRANTY_HINT)
      expect((b.attributes('aria-label') ?? '').endsWith(REASON), `key=${key} ends`).toBe(true)
    }
    expect(warrantyChip(w).exists()).toBe(false)
  })

  // TC6: warranty_expired=true NHƯNG report_failure route lạ (∉ allow-list FE) →
  //   effectiveEnabled=false → KHÔNG affordance bảo hành, nút disabled +
  //   ROUTE_UNAVAILABLE_REASON giữ nguyên (parity vòng 20).
  it('TC6: warranty_expired=true NHƯNG report_failure route lạ (∉ allow-list) → KHÔNG affordance, nút disabled + reason route', async () => {
    const ROUTE_REASON = 'Thao tác này hiện chưa khả dụng trên thiết bị của bạn'
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      warranty_expired: true,
      available_actions: [
        { key: 'report_failure', label: 'Báo hỏng', route: 'BogusIncident', enabled: true, reason: '' },
      ],
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const b = actionBtn(w, 'report_failure')
    expect(warrantyAttr(w, 'report_failure')).toBeUndefined()
    expect(b.text()).not.toContain(OUT_OF_WARRANTY_HINT)
    // route lạ → disabled + ROUTE_UNAVAILABLE_REASON (vòng 20 giữ nguyên).
    expect(b.attributes('disabled')).toBeDefined()
    expect(b.attributes('title')).toBe(ROUTE_REASON)
    expect(warrantyChip(w).exists()).toBe(false)
  })

  // TC7 (parity-độc-lập): warranty_expired=true + pm_overdue=true cùng payload →
  //   nút request_pm CHỈ có chip overdue 'Cần làm ngay'; nút report_failure/request_cm
  //   CHỈ có affordance bảo hành 'Ngoài bảo hành' — 2 trục KHÔNG leak chéo
  //   (overdue-key ∩ warranty-key = ∅).
  it("TC7 (parity-độc-lập): warranty_expired=true + pm_overdue=true → request_pm CHỈ overdue; report_failure/request_cm CHỈ warranty — KHÔNG leak chéo", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      next_pm_date: '2026-01-01',
      pm_overdue: true,
      calibration_overdue: false,
      warranty_expired: true,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    // request_pm: overdue ('Cần làm ngay'), KHÔNG warranty.
    expect(actionBtn(w, 'request_pm').attributes('data-overdue-cta')).toBe('request_pm')
    expect(warrantyAttr(w, 'request_pm')).toBeUndefined()
    expect(actionBtn(w, 'request_pm').text()).toContain(URGENT_HINT)
    expect(actionBtn(w, 'request_pm').text()).not.toContain(OUT_OF_WARRANTY_HINT)
    // report_failure + request_cm: warranty ('Ngoài bảo hành'), KHÔNG overdue.
    for (const key of ['report_failure', 'request_cm']) {
      expect(warrantyAttr(w, key), `key=${key}`).toBe(key)
      expect(actionBtn(w, key).attributes('data-overdue-cta'), `key=${key}`).toBeUndefined()
      expect(actionBtn(w, key).text(), `key=${key}`).toContain(OUT_OF_WARRANTY_HINT)
      expect(actionBtn(w, key).text(), `key=${key}`).not.toContain(URGENT_HINT)
    }
    // request_calibration: KHÔNG overdue (cờ cal=false) + KHÔNG warranty (sai ngữ cảnh).
    expect(actionBtn(w, 'request_calibration').attributes('data-overdue-cta')).toBeUndefined()
    expect(warrantyAttr(w, 'request_calibration')).toBeUndefined()
  })

  // TC8 (no-client-clock guard, LL-TEST-26 revert-proof): warranty_expired=false NHƯNG
  //   warranty_expiry_date='2000-01-01' (quá khứ xa) → KHÔNG affordance bảo hành
  //   (chứng minh đọc CỜ server, KHÔNG so ngày client). + grep nguồn
  //   isOutOfWarrantyCta KHÔNG chứa Date/getdate/new Date/so-sánh warranty_expiry_date.
  it("TC8 (no-client-clock): warranty_expired=false + warranty_expiry_date quá khứ xa → KHÔNG affordance (đọc cờ server, KHÔNG so client-clock)", async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...PAYLOAD,
      warranty_expiry_date: '2000-01-01', // quá khứ xa
      warranty_expired: false,            // CỜ server vẫn false
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    expect(warrantyChip(w).exists()).toBe(false)
    for (const key of ['report_failure', 'request_cm']) {
      expect(warrantyAttr(w, key), `key=${key}`).toBeUndefined()
      expect(actionBtn(w, key).text(), `key=${key}`).not.toContain(OUT_OF_WARRANTY_HINT)
    }
    // sanity: nếu BỊ revert sang so client-clock thì ngày quá khứ → true (SAI). Guard
    // server `=== true` chặn điều này khi cờ=false.
    expect(new Date('2000-01-01') < new Date()).toBe(true)
  })

  // ── helpers nguồn (strip CẢ //-comment LẪN <!-- --> Vue-comment) ────────────
  const readSrc = () => readFileSync(resolve(__dirname, 'AssetScanInfoView.vue'), 'utf8')
  const stripComments = (src: string) =>
    src
      .replace(/<!--[\s\S]*?-->/g, '')
      .split('\n')
      .map((l) => l.replace(/\/\/.*$/, ''))
      .join('\n')

  // TC8-src (revert-proof LL-TEST-26): nguồn isOutOfWarrantyCta đọc warrantyExpired
  //   (cờ server === true), KHÔNG so warranty_expiry_date với client clock.
  it('TC8-src: isOutOfWarrantyCta NGUỒN đọc warrantyExpired (cờ), KHÔNG Date/getdate/new Date/warranty_expiry_date', () => {
    const codeOnly = stripComments(readSrc())
    // bắt thân function isOutOfWarrantyCta(a) tới dấu '}' đóng đầu tiên ở cột 0.
    const m = codeOnly.match(/function isOutOfWarrantyCta\([^)]*\)[^{]*\{([\s\S]*?)\n\}/)
    expect(m, 'phải có function isOutOfWarrantyCta').toBeTruthy()
    const body = m?.[1] ?? ''
    expect(body).toContain('warrantyExpired')
    expect(body).not.toContain('new Date')
    expect(body).not.toContain('getdate')
    expect(body).not.toContain('Date.now')
    expect(body).not.toContain('warranty_expiry_date')
  })

  // GUARD (SSoT no-drift): OUT_OF_WARRANTY_CTA_HINT literal ĐÚNG 1 lần (ngoài comment);
  //   WARRANTY_CTA_KEYS == {report_failure, request_cm}; KHÔNG tái dùng URGENT_CTA_HINT
  //   cho affordance bảo hành (phân biệt ngữ nghĩa overdue vs warranty).
  it("GUARD: 'Ngoài bảo hành' khai báo 1 lần; WARRANTY_CTA_KEYS = {report_failure, request_cm}; KHÔNG tái dùng URGENT_CTA_HINT", () => {
    const codeOnly = stripComments(readSrc())
    // literal 'Ngoài bảo hành' xuất hiện ĐÚNG 1 lần trong code (no rải literal).
    expect((codeOnly.match(/Ngoài bảo hành/g) ?? []).length).toBe(1)
    // hằng SSoT khai báo.
    expect(codeOnly).toContain('OUT_OF_WARRANTY_CTA_HINT')
    // map WARRANTY_CTA_KEYS chứa ĐÚNG 2 key đường-sửa.
    expect(codeOnly).toContain('WARRANTY_CTA_KEYS')
    const km = codeOnly.match(/WARRANTY_CTA_KEYS[\s\S]*?(\[[\s\S]*?\]|\{[\s\S]*?\})/)
    const block = km?.[1] ?? ''
    expect(block).toContain('report_failure')
    expect(block).toContain('request_cm')
    expect(block).not.toContain('request_pm')
    expect(block).not.toContain('request_calibration')
    // affordance bảo hành KHÔNG tái dùng URGENT_CTA_HINT (overdue) — phân biệt ngữ nghĩa.
    // (URGENT_CTA_HINT vẫn còn cho trục overdue, nhưng chip warranty bind hằng riêng.)
    const chipBlock = codeOnly.match(/data-test="cta-out-of-warranty"[\s\S]{0,200}/)?.[0] ?? ''
    expect(chipBlock).not.toContain('URGENT_CTA_HINT')
  })
})
