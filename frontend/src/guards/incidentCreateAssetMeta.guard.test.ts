// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 Vòng 26 scan-action — parity panel ngữ-cảnh-thiết-bị NẠC) —
// IncidentCreateView: khi vào qua deep-link QR (?asset=<name>&source=qr-scan) →
// render panel ngữ-cảnh-thiết-bị NẠC 4 dòng (asset_name / device_model_name /
// location_name / lifecycle_status VI) — PARITY với CM/Cal/PM CreateView.
//
// Invariant data-minimization (Vòng 25): panel nạp DUY NHẤT qua getAssetActionMeta
// (endpoint NẠC 6-key, perm-aware, IDOR/vendor-gate). TUYỆT ĐỐI KHÔNG getAsset
// full-doc / raw frappe.client.get_value → KHÔNG bao giờ fetch tài chính
// (gross_purchase_amount / current_book_value / accumulated_depreciation /
// purchase_cost / salvage_value / qr_token) vào màn báo hỏng.
//
// TC1: qr-scan + asset prefill → panel render đúng 4 dòng, status nhãn VI, no-EN/financial leak.
// TC2: getAsset KHÔNG bao giờ được gọi (chỉ getActionMeta); field tài chính thừa KHÔNG render.
// TC3: manual (không source / source≠qr-scan) → panel KHÔNG render; getActionMeta KHÔNG gọi.
// TC4: getActionMeta reject (403/404/network) → panel ẩn, không 'undefined'/'null'/'—' câm, form vẫn submit.
// TC5: device_model_name='' / location_name='' (legacy) → 'Chưa gán'; status rỗng/lạ → nhãn VI an toàn.
// TC6 (parity guard): 4 view scan-action ĐỀU dùng getAssetActionMeta cho panel meta.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { SRC } from '@/test/paths'

// Đường dẫn lấy từ SSoT `src/test/paths.ts` (SPEC §5.2 N5): neo bằng mốc
// package.json + vite.config.ts, không phụ thuộc `process.cwd()` (đổi theo nơi
// gọi vitest) hay số cấp `..` (đổi khi file bị dời).
const VIEWS_ROOT = resolve(SRC, 'views')

const pushSpy = vi.fn().mockResolvedValue(undefined)
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

const reportIncidentSpy = vi
  .fn()
  .mockResolvedValue({ name: 'INC-2026-00001', status: 'Open', severity: 'High' })
vi.mock('@/api/imm12', () => ({
  reportIncident: (data: Record<string, unknown>) => reportIncidentSpy(data),
}))

// frappeGet là RAW RPC — slice này PHẢI KHÔNG còn dùng cho asset-meta (no raw
// frappe.client.get_value — LL-FE-40).
const frappeGetSpy = vi.fn().mockResolvedValue(null)
vi.mock('@/api/helpers', () => ({
  frappeGet: (...args: unknown[]) => frappeGetSpy(...args),
  frappePost: vi.fn().mockResolvedValue(null),
}))

// getAssetActionMeta NẠC perm-aware (api/imm00). getAsset cũng mock để KHẲNG ĐỊNH
// panel KHÔNG gọi nó (full-doc tài chính over-fetch).
const getActionMetaSpy = vi.fn()
const getAssetSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  getAssetActionMeta: (...args: unknown[]) => getActionMetaSpy(...args),
  getAsset: (...args: unknown[]) => getAssetSpy(...args),
}))

vi.mock('@/composables/useFormDraft', () => ({
  useFormDraft: () => ({ clear: vi.fn() }),
}))

import IncidentCreateView from '@/views/incident/IncidentCreateView.vue'

function mountView() {
  return mount(IncidentCreateView, { global: { stubs: { SmartSelect: true } } })
}

// Điền field bắt buộc để submit qua FE guard.
async function fillRequired(w: ReturnType<typeof mountView>) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const vm = w.vm as any
  vm.form.incident_type = 'Failure'
  vm.form.severity = 'High'
  vm.form.description = 'Máy ngừng hoạt động đột ngột'
  await flushPromises()
}

// Payload NẠC (6 field, KHÔNG field tài chính) — đúng shape AssetActionMeta BE trả.
const META = {
  name: 'AC-ASSET-0001',
  asset_name: 'Máy thở Dräger V500',
  device_model_name: 'Dräger Evita V500',
  lifecycle_status: 'Active',
  risk_classification: 'C',
  location_name: 'Khoa Hồi sức tích cực',
}

describe('IncidentCreateView — panel ngữ-cảnh-thiết-bị NẠC qua getAssetActionMeta', () => {
  beforeEach(() => {
    routeQuery = {}
    pushSpy.mockClear()
    reportIncidentSpy.mockClear()
    frappeGetSpy.mockClear()
    getActionMetaSpy.mockReset()
    getActionMetaSpy.mockResolvedValue(META)
    getAssetSpy.mockReset()
    getAssetSpy.mockResolvedValue(META)
  })

  it('TC1 — qr-scan + asset prefill → panel render đúng 4 dòng + status VI, no-EN/financial leak', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()

    expect(getActionMetaSpy).toHaveBeenCalledWith('AC-ASSET-0001')
    const t = w.text()
    expect(t).toContain('Máy thở Dräger V500')   // asset_name
    expect(t).toContain('Dräger Evita V500')      // device_model_name (KHÔNG raw id)
    expect(t).toContain('Khoa Hồi sức tích cực')  // location_name (KHÔNG location id)
    expect(t).toContain('Đang hoạt động')         // lifecycle_status VI qua SSoT
    expect(t).not.toContain('Active')             // no EN-leak

    // Panel a11y: heading + dt/dd readable. data-test bám ổn định cho vitest.
    expect(w.find('[data-test="scan-incident-meta"]').exists()).toBe(true)
    expect(w.find('[data-test="scan-incident-meta-name"]').text()).toContain('Máy thở Dräger V500')
    expect(w.find('[data-test="scan-incident-meta-model"]').text()).toContain('Dräger Evita V500')
    expect(w.find('[data-test="scan-incident-meta-location"]').text()).toContain('Khoa Hồi sức tích cực')
    expect(w.find('[data-test="scan-incident-meta-status"]').text()).toContain('Đang hoạt động')
  })

  it('TC2 — getAsset KHÔNG bao giờ gọi; field tài chính thừa KHÔNG render', async () => {
    getActionMetaSpy.mockResolvedValue({
      ...META,
      gross_purchase_amount: 850_000_000,
      current_book_value: 600_000_000,
      accumulated_depreciation: 250_000_000,
      qr_token: 'qr_token_secret_abc123',
    })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()

    // CHỈ getAssetActionMeta — KHÔNG getAsset full-doc.
    expect(getActionMetaSpy).toHaveBeenCalledWith('AC-ASSET-0001')
    expect(getAssetSpy).not.toHaveBeenCalled()
    // frappeGet KHÔNG được gọi tới endpoint raw RPC cho asset-meta.
    for (const call of frappeGetSpy.mock.calls) {
      expect(String(call[0])).not.toContain('frappe.client.get_value')
    }
    const t = w.text()
    expect(t).not.toContain('850000000')              // giá mua
    expect(t).not.toContain('600000000')              // giá trị sổ sách
    expect(t).not.toContain('250000000')              // khấu hao luỹ kế
    expect(t).not.toContain('qr_token_secret_abc123') // qr_token
  })

  it('TC3 — manual (không source) → panel KHÔNG render; getActionMeta KHÔNG gọi (no fetch thừa)', async () => {
    routeQuery = { asset: 'AC-ASSET-0001' } // manual — không source=qr-scan
    const w = mountView()
    await flushPromises()

    expect(getActionMetaSpy).not.toHaveBeenCalled()
    expect(w.find('[data-test="scan-incident-meta"]').exists()).toBe(false)
    // Ô Thiết bị editable như cũ (no regression).
    expect(w.text()).not.toContain('Tạo từ quét QR')
  })

  it('TC3b — source≠qr-scan (giá trị lạ) → panel KHÔNG render; getActionMeta KHÔNG gọi', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'hack' }
    const w = mountView()
    await flushPromises()
    expect(getActionMetaSpy).not.toHaveBeenCalled()
    expect(w.find('[data-test="scan-incident-meta"]').exists()).toBe(false)
  })

  it('TC4 — getActionMeta reject (403 IDOR / 404 / network) → panel ẩn, no undefined/null/—, form vẫn submit', async () => {
    getActionMetaSpy.mockRejectedValue(
      Object.assign(new Error('IDOR vendor leak user@evil.com qr_token=abc123'), { httpStatus: 403 }),
    )
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()

    // panel ẩn hoàn toàn (assetMeta=null).
    expect(w.find('[data-test="scan-incident-meta"]').exists()).toBe(false)
    const t = w.text()
    // KHÔNG leak raw exception / email / token.
    expect(t).not.toContain('user@evil.com')
    expect(t).not.toContain('qr_token')
    expect(t).not.toContain('IDOR')
    // KHÔNG 'undefined'/'null'/'—' câm trong panel (panel không tồn tại).
    expect(t).not.toContain('undefined')
    expect(t).not.toContain('null')
    // Trang vẫn còn (heading + ô Thiết bị khoá tồn tại).
    expect(t).toContain('Tạo phiếu sự cố')
    expect(t).toContain('Tạo từ quét QR')

    // Form vẫn submit được dù panel ẩn — fail-safe KHÔNG chặn báo hỏng.
    await fillRequired(w)
    await w.find('button[class*="bg-blue-600"]').trigger('click')
    await flushPromises()
    expect(reportIncidentSpy).toHaveBeenCalledTimes(1)
    const payload = reportIncidentSpy.mock.calls[0][0] as Record<string, unknown>
    expect(payload.source).toBe('qr-scan')
    expect(payload.asset).toBe('AC-ASSET-0001')
  })

  it('TC5 — device_model_name=""/location_name="" (legacy) → "Chưa gán"; status rỗng → nhãn VI an toàn', async () => {
    getActionMetaSpy.mockResolvedValue({
      ...META,
      device_model_name: '',
      location_name: '',
      lifecycle_status: '',
    })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()

    const modelCell = w.find('[data-test="scan-incident-meta-model"]').text()
    const locCell = w.find('[data-test="scan-incident-meta-location"]').text()
    const statusCell = w.find('[data-test="scan-incident-meta-status"]').text()
    expect(modelCell).toContain('Chưa gán')
    expect(modelCell).not.toContain('—')   // no-em-dash parity
    expect(locCell).toContain('Chưa gán')
    expect(locCell).not.toContain('—')
    // status rỗng → 'Không xác định' (no-raw-EN/code leak, SSoT lifecycleStatusLabel).
    expect(statusCell).toContain('Không xác định')
    expect(statusCell).not.toContain('—')
  })

  it('TC5b — lifecycle_status mã lạ (legacy drift) → nhãn VI an toàn, no-raw-leak', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, lifecycle_status: 'Retired' })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const statusCell = w.find('[data-test="scan-incident-meta-status"]').text()
    expect(statusCell).toContain('Không xác định')
    expect(statusCell).not.toContain('Retired')  // KHÔNG leak mã EN/legacy
  })

  it('TC6 (parity guard) — 4 view scan-action ĐỀU dùng getAssetActionMeta cho panel meta thiết bị', () => {
    // Parity invariant: panel ngữ-cảnh-thiết-bị trên đường qr-scan của CẢ 4 view
    // (Incident/CM/Cal/PM) nạp qua getAssetActionMeta (NẠC perm-aware) — KHÔNG view
    // nào quay lại getAsset full-doc cho panel này.
    const views = [
      'incident/IncidentCreateView.vue',
      'cm/CMCreateView.vue',
      'calibration/CalibrationCreateView.vue',
      'pm/PMWorkOrderCreateView.vue',
    ]
    for (const rel of views) {
      const src = readFileSync(resolve(VIEWS_ROOT, rel), 'utf-8')
      // Mọi view phải import + gọi getAssetActionMeta cho panel meta thiết bị.
      expect(src).toContain('getAssetActionMeta')
    }
  })

  it('TC6b (no-raw-leak) — IncidentCreateView (view round này) KHÔNG raw frappe.client.get_value (LL-FE-40)', () => {
    // GATE-4: view vừa sửa KHÔNG được gọi raw RPC frappe.client.get_value cho bất
    // kỳ lookup nào — loại comment cảnh báo negation, chỉ bắt CODE THẬT.
    const src = readFileSync(resolve(VIEWS_ROOT, 'incident/IncidentCreateView.vue'), 'utf-8')
    const codeLines = src
      .split('\n')
      .filter(l => !l.trimStart().startsWith('//'))
      .join('\n')
    expect(codeLines).not.toContain('frappe.client.get_value')
  })
})
