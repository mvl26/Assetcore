// TDD — Vòng 48 (trạng thái BẢO HÀNH): AssetScanInfoView card ĐỊNH DANH/bảo trì ·
//   dòng 'Bảo hành' (warranty_expiry_date) + badge 'Hết bảo hành' (warranty_expired).
//   KTV biết "còn/hết bảo hành" TRƯỚC khi báo hỏng/tạo CM (affordance chi phí sửa).
//
// Hợp đồng BE (build_asset_scan_info, Vòng 48):
//   • warranty_expiry_date: str|None 'YYYY-MM-DD' (qua _date_str_or_none — parity
//     next_pm_date/next_calibration_date; rỗng/None → None).
//   • warranty_expired: bool derive SERVER-SIDE (_is_warranty_expired, STRICT < ngày
//     server, ĐỘC LẬP lifecycle). FE đọc CỜ — KHÔNG so client-clock.
//
// Yêu cầu FE (DÙNG LẠI formatIsoDateLabel + pattern presence-aware scheduleLabel —
// KHÔNG fork đường xử lý ngày):
//   • key ABSENT (payload stale) → 'Cần kiểm tra'.
//   • PRESENT + null/'' → 'Chưa có thông tin'.
//   • PRESENT + chuỗi-ISO-hợp-lệ → ngày VI (dd/mm/yyyy).
//   • phi-ISO / whitespace / drift → 'Chưa rõ ngày' (KHÔNG leak verbatim).
//   • warranty_expired === true → badge [data-test=warranty-expired] role=status +
//     aria-label VI cảnh báo + text VI 'Hết bảo hành' (màu cảnh báo). false/absent →
//     KHÔNG render badge (no false-alarm). KHÔNG so client-clock.
//   • no-EN-leak: KHÔNG 'Warranty'/'Expired'/raw enum.
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

// Base payload — đủ key để view ready; chỉ warranty_* xoay theo TC.
const BASE = {
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
  available_actions: [],
}

const warrantyLine = (w: ReturnType<typeof mount>) => w.get('[data-test="warranty-date"]')
const warrantyBadge = (w: ReturnType<typeof mount>) => w.find('[data-test="warranty-expired"]')

describe('AssetScanInfoView — dòng "Bảo hành" + badge "Hết bảo hành" (vòng 48)', () => {
  beforeEach(() => {
    replaceSpy.mockClear(); pushSpy.mockClear()
    getAssetScanInfoSpy.mockReset()
    routeParams.value = { id: 'AC-ASSET-2026-00042' }
  })

  // FE-WAR-1 — ISO hợp lệ tương lai + warranty_expired=false → ngày VI, KHÔNG badge.
  it('FE-WAR-1: warranty_expiry_date="2027-05-01" + expired=false → ngày VI, KHÔNG badge', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, warranty_expiry_date: '2027-05-01', warranty_expired: false,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = warrantyLine(w)
    // ngày VI (formatIsoDateLabel → formatDate vi-VN; locale Node có thể KHÔNG
    // zero-pad → so với CHÍNH output locale, KHÔNG hardcode pad).
    expect(line.text()).toContain(new Date('2027-05-01').toLocaleDateString('vi-VN'))
    // KHÔNG nhãn fallback.
    expect(line.text()).not.toContain('Chưa có thông tin')
    expect(line.text()).not.toContain('Cần kiểm tra')
    expect(line.text()).not.toContain('Chưa rõ ngày')
    // no false-alarm: KHÔNG badge.
    expect(warrantyBadge(w).exists()).toBe(false)
  })

  // FE-WAR-2 — quá khứ + warranty_expired=true → badge render (role=status + aria VI);
  //   ngày VẪN hiển thị.
  it('FE-WAR-2: warranty_expiry_date="2020-01-01" + expired=true → badge role/aria VI + ngày vẫn hiện', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, warranty_expiry_date: '2020-01-01', warranty_expired: true,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = warrantyLine(w)
    // ngày VẪN hiển thị (KHÔNG nuốt date khi hết bảo hành).
    expect(line.text()).toContain(new Date('2020-01-01').toLocaleDateString('vi-VN'))
    // badge cảnh báo.
    const badge = warrantyBadge(w)
    expect(badge.exists()).toBe(true)
    expect(['status', 'alert']).toContain(badge.attributes('role'))
    expect(badge.attributes('aria-label')).toBeTruthy()
    expect(badge.attributes('aria-label')).toContain('bảo hành')
    // text VI 'Hết bảo hành'.
    expect(badge.text()).toContain('Hết bảo hành')
    // class màu cảnh báo (amber/rose, KHÔNG slate câm).
    const cls = badge.attributes('class') ?? ''
    expect(/amber|rose/.test(cls)).toBe(true)
    expect(/slate/.test(cls)).toBe(false)
  })

  // FE-WAR-3 — PRESENT + null → 'Chưa có thông tin', KHÔNG badge.
  it('FE-WAR-3: warranty_expiry_date=null → "Chưa có thông tin", KHÔNG badge', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, warranty_expiry_date: null, warranty_expired: false,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = warrantyLine(w)
    expect(line.text()).toContain('Chưa có thông tin')
    expect(line.text()).not.toContain('—')
    expect(warrantyBadge(w).exists()).toBe(false)
  })

  // FE-WAR-4 — key ABSENT (payload stale) → 'Cần kiểm tra'; phi-ISO/whitespace →
  //   'Chưa rõ ngày' (KHÔNG leak verbatim).
  it('FE-WAR-4: key ABSENT → "Cần kiểm tra"; phi-ISO "soon"/whitespace → "Chưa rõ ngày" (no leak)', async () => {
    // ABSENT
    const partial: Record<string, unknown> = { ...BASE }
    delete partial.warranty_expiry_date
    getAssetScanInfoSpy.mockResolvedValue(partial)
    let w = mount(AssetScanInfoView)
    await flushPromises()
    expect(warrantyLine(w).text()).toContain('Cần kiểm tra')

    // phi-ISO 'soon'
    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, warranty_expiry_date: 'soon' })
    w = mount(AssetScanInfoView)
    await flushPromises()
    let line = warrantyLine(w)
    expect(line.text()).toContain('Chưa rõ ngày')
    expect(line.text()).not.toContain('soon')

    // whitespace
    getAssetScanInfoSpy.mockResolvedValue({ ...BASE, warranty_expiry_date: '   ' })
    w = mount(AssetScanInfoView)
    await flushPromises()
    line = warrantyLine(w)
    expect(line.text()).toContain('Chưa rõ ngày')
  })

  // FE-WAR-5 (no-EN-leak): mọi nhánh KHÔNG chứa 'Warranty'/'Expired'/raw enum.
  it('FE-WAR-5 (no-EN-leak): dòng + badge KHÔNG chứa "Warranty"/"Expired"; badge VI "Hết bảo hành"', async () => {
    getAssetScanInfoSpy.mockResolvedValue({
      ...BASE, warranty_expiry_date: '2020-01-01', warranty_expired: true,
    })
    const w = mount(AssetScanInfoView)
    await flushPromises()
    const line = warrantyLine(w)
    const badge = warrantyBadge(w)
    for (const en of ['Warranty', 'Expired', 'warranty', 'expired']) {
      expect(line.text()).not.toContain(en)
      expect(badge.text()).not.toContain(en)
      expect(badge.attributes('aria-label') ?? '').not.toContain(en)
    }
    expect(badge.text()).toContain('Hết bảo hành')
  })

  // ── helpers nguồn (strip CẢ //-comment LẪN <!-- --> Vue-comment) ────────────
  const readSrc = () => readFileSync(resolve(__dirname, '..', 'AssetScanInfoView.vue'), 'utf8')
  const stripComments = (src: string) =>
    src
      .replace(/<!--[\s\S]*?-->/g, '')
      .split('\n')
      .map((l) => l.replace(/\/\/.*$/, ''))
      .join('\n')

  // FE-WAR-6 (revert-proof LL-TEST-26): chứng minh nếu đảo warrantyExpired sang so
  //   warranty_expiry_date với client clock HOẶC bỏ `=== true` guard → guard mất răng.
  //   (a) guard NGUỒN: warrantyExpired đọc cờ server === true, KHÔNG new Date()/Date.now.
  //   (b) hành vi: cờ server=false vẫn cho badge nếu so client-clock với ngày quá khứ →
  //       SAI; guard `=== true` chặn. cờ server=true → badge.
  it('FE-WAR-6 (revert-proof): nguồn đọc cờ server === true (KHÔNG client-clock); guard có răng', () => {
    const codeOnly = stripComments(readSrc())
    // warrantyExpired computed phải đọc info.value?.warranty_expired === true.
    // Bắt phần thân SAU '=>' tới hết dòng (computed(() => <expr>)).
    const m = codeOnly.match(/warrantyExpired\s*=\s*computed\(\(\)\s*=>\s*([^\n]*)/)
    expect(m, 'phải có computed warrantyExpired').toBeTruthy()
    const expr = (m?.[1] ?? '')
    expect(expr).toContain('warranty_expired')
    expect(expr).toContain('=== true')
    // KHÔNG so client-clock trong nhánh warranty.
    expect(expr).not.toContain('new Date')
    expect(expr).not.toContain('Date.now')
    expect(expr).not.toContain('warranty_expiry_date')

    // hành vi guard: badge gated bằng warranty_expired === true.
    const warrantyExpired = (info: { warranty_expired?: unknown }) => info?.warranty_expired === true
    expect(warrantyExpired({ warranty_expired: true })).toBe(true)
    expect(warrantyExpired({ warranty_expired: false })).toBe(false)
    expect(warrantyExpired({})).toBe(false)
    // nếu BỊ revert sang so client-clock: ngày quá khứ → true DÙ cờ server=false (SAI).
    const revertedClientClock = (d: string) => new Date(d) < new Date()
    expect(revertedClientClock('2020-01-01')).toBe(true) // ← điều guard server PHẢI chặn khi cờ=false
  })

  // FE-WAR-7 (SSoT guard NGUỒN): nhãn 'Chưa có thông tin' + 'Hết bảo hành' khai báo
  //   ĐÚNG 1 lần (const, ngoài comment) — KHÔNG rải literal. Dòng bind warrantyDateText.
  it('FE-WAR-7 (SSoT guard): nhãn warranty khai báo 1 lần; dòng bind warrantyDateText', () => {
    const codeOnly = stripComments(readSrc())
    expect((codeOnly.match(/Chưa có thông tin/g) ?? []).length).toBe(1)
    expect((codeOnly.match(/Hết bảo hành/g) ?? []).length).toBe(1)
    // dòng dán nhãn 'Bảo hành' bind computed warrantyDateText (KHÔNG inline xử lý ngày).
    const m = codeOnly.match(/Bảo hành[^{]*\{\{([^}]*)\}\}/)
    expect(m?.[1].trim()).toBe('warrantyDateText')
  })
})
