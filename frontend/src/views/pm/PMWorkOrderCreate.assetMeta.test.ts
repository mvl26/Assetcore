// Copyright (c) 2026, AssetCore Team
// FE-TDD (IMM-00 Vòng 25 scan-action — over-fetch close) — PMWorkOrderCreateView:
// panel meta thiết bị PHẢI qua getAssetActionMeta(name) NẠC perm-aware
// (api/imm00.ts) — KHÔNG getAsset (full doc rò giá mua/khấu hao/giá trị sổ sách),
// KHÔNG raw frappe.client.get_value (LL-FE-40). Parity CM/Calibration.
//
// Khác CM/Cal: PM nạp song song getAssetActionMeta + checkAssetComplianceStatus qua
// Promise.allSettled → asserts thêm: gate fail-safe độc lập, panel ẩn khi meta lỗi,
// loadSchedules() chạy SAU set assetMeta.
//
// Acceptance (Task FE — asset-meta loader over-fetch close):
//   • TC-PM-META-CALLED: deep-link qr-scan → getAssetActionMeta(asset_ref) gọi đúng
//     tên (KHÔNG getAsset); KHÔNG request nào tới '/api/method/frappe.client.get_value'.
//   • TC-PM-META-RENDER-NAMES: panel render asset_name / device_model_name /
//     location_name (tên người-đọc-được) + trạng thái VI (SSoT).
//   • TC-PM-META-NO-RAWCODE-LEAK: device_model='DM-0001'/location='LOC-0042' KHÔNG
//     ở field name → panel KHÔNG render raw 'DM-0001'/'LOC-0042'.
//   • TC-PM-META-FAILSAFE-403: getAsset reject(403) → assetMeta=null, panel ẩn,
//     KHÔNG throw, KHÔNG leak exc/email/token; complianceGate xử lý độc lập.
//   • TC-PM-META-DECOMMISSIONED-GATE: lifecycle_status='Decommissioned' →
//     canSubmit=false (gate giữ nguyên sau migrate).
//   • TC-PM-SCHEDULES-AFTER-META: loadSchedules() vẫn gọi SAU set assetMeta.
//   • TC-PM-LOCKED-LABEL-PARITY: qr-scan → lockedFromScan=true + badge.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const pushSpy = vi.fn().mockResolvedValue(undefined)
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: routeQuery }),
}))

vi.mock('@/api/imm08', () => ({
  createAdhocPMWorkOrder: vi.fn().mockResolvedValue({ name: 'PM-WO-2026-00001' }),
}))

// Compliance gate độc lập (allSettled slot 2) — mặc định null (không chặn).
const checkComplianceSpy = vi.fn().mockResolvedValue(null)
vi.mock('@/api/imm16', () => ({
  checkAssetComplianceStatus: (...args: unknown[]) => checkComplianceSpy(...args),
}))

// frappeGet là RAW RPC — slice asset-meta PHẢI KHÔNG còn dùng cho asset-meta.
// (Vẫn dùng cho loadSchedules → list_pm_schedules + watch checklist → KHÔNG xoá.)
const frappeGetSpy = vi.fn((endpoint: string) => {
  if (typeof endpoint === 'string' && endpoint.includes('imm08.list_pm_schedules')) {
    return Promise.resolve({ data: [{ name: 'PM-SCH-0001', pm_type: 'Định kỳ', pm_interval_days: 90 }] })
  }
  return Promise.resolve(null)
})
vi.mock('@/api/helpers', () => ({
  frappeGet: (...args: unknown[]) => frappeGetSpy(...(args as [string])),
  frappePost: vi.fn().mockResolvedValue(null),
}))

// getAssetActionMeta NẠC perm-aware (api/imm00) — loader mới (over-fetch close).
// getAsset mock để KHẲNG ĐỊNH panel KHÔNG còn gọi nó (full-doc tài chính).
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
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import PMWorkOrderCreateView from './PMWorkOrderCreateView.vue'

function mountView() {
  return mount(PMWorkOrderCreateView, {
    global: { stubs: { SmartSelect: true, DateInput: true } },
  })
}

// Payload NẠC (6 field, KHÔNG field tài chính) — đúng shape AssetActionMeta BE trả.
const META = {
  name: 'AC-ASSET-0001',
  asset_name: 'Máy thở X',
  device_model_name: 'Model A',
  location_name: 'Khoa Hồi sức',
  lifecycle_status: 'Active',
}

describe('PMWorkOrderCreateView — panel meta qua getAssetActionMeta (NẠC perm-aware)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    routeQuery = {}
    pushSpy.mockClear()
    frappeGetSpy.mockClear()
    checkComplianceSpy.mockClear()
    checkComplianceSpy.mockResolvedValue(null)
    getActionMetaSpy.mockReset()
    getActionMetaSpy.mockResolvedValue(META)
    getAssetSpy.mockReset()
    getAssetSpy.mockResolvedValue(META)
  })

  it('TC-PM-META-CALLED: qr-scan → getAssetActionMeta(asset_ref) (KHÔNG getAsset); KHÔNG gọi frappe.client.get_value', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()

    expect(getActionMetaSpy).toHaveBeenCalledWith('AC-ASSET-0001')
    expect(getAssetSpy).not.toHaveBeenCalled()  // KHÔNG kéo full-doc tài chính cho panel
    for (const call of frappeGetSpy.mock.calls) {
      expect(String(call[0])).not.toContain('frappe.client.get_value')
    }
  })

  it('TC-PM-META-NO-FINANCIAL: payload NẠC KHÔNG field tài chính → panel KHÔNG render giá', async () => {
    getActionMetaSpy.mockResolvedValue({
      ...META,
      gross_purchase_amount: 850_000_000,
      current_book_value: 600_000_000,
    })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const t = w.text()
    expect(t).toContain('Máy thở X')
    expect(t).not.toContain('850000000')
    expect(t).not.toContain('600000000')
  })

  it('TC-PM-META-RENDER-NAMES: panel render tên người-đọc-được + trạng thái VI', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()

    const t = w.text()
    expect(t).toContain('Máy thở X')        // asset_name
    expect(t).toContain('Model A')          // device_model_name
    expect(t).toContain('Khoa Hồi sức')     // location_name
    expect(t).toContain('Đang hoạt động')   // lifecycle_status VI qua SSoT
    expect(t).not.toContain('Active')       // no EN-leak
  })

  it('TC-PM-META-NO-RAWCODE-LEAK: raw doc-name DM-0001/LOC-0042 KHÔNG render ra panel', async () => {
    // BE meta NẠC KHÔNG trả raw id, nhưng giả định payload còn field device_model/location:
    // FE map THEO device_model_name/location_name → raw id KHÔNG được leak.
    getActionMetaSpy.mockResolvedValue({
      ...META,
      device_model: 'DM-0001',
      location: 'LOC-0042',
    })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    const t = w.text()
    expect(t).not.toContain('DM-0001')
    expect(t).not.toContain('LOC-0042')
    // vẫn render tên người-đọc-được
    expect(t).toContain('Model A')
    expect(t).toContain('Khoa Hồi sức')
  })

  it('TC-PM-META-FAILSAFE-403: getAssetActionMeta reject(403) → assetMeta=null, panel ẩn, KHÔNG leak; gate độc lập', async () => {
    getActionMetaSpy.mockRejectedValue(
      Object.assign(new Error('PermissionError IDOR user@evil.com qr_token=abc123'), { httpStatus: 403 }),
    )
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()

    const t = w.text()
    expect(t).not.toContain('user@evil.com')
    expect(t).not.toContain('qr_token')
    expect(t).not.toContain('PermissionError')
    // panel meta ẩn → KHÔNG render tên thiết bị
    expect(t).not.toContain('Máy thở X')
    // trang KHÔNG vỡ (heading còn)
    expect(t).toContain('Tạo phiếu bảo trì đột xuất')
    // gate độc lập vẫn được gọi (allSettled) → compliance xử lý riêng
    expect(checkComplianceSpy).toHaveBeenCalledWith('AC-ASSET-0001')
  })

  it('TC-PM-META-DECOMMISSIONED-GATE: lifecycle_status=Decommissioned → canSubmit=false', async () => {
    getActionMetaSpy.mockResolvedValue({ ...META, lifecycle_status: 'Decommissioned' })
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    expect(w.text()).toContain('Thiết bị đã thanh lý')
    const submitBtn = w.findAll('button').find(b => b.text().includes('Tạo phiếu bảo trì'))!
    expect(submitBtn.attributes('disabled')).toBeDefined()
  })

  it('TC-PM-SCHEDULES-AFTER-META: loadSchedules() vẫn chạy SAU set assetMeta', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    // list_pm_schedules được gọi (qua frappeGet) → schedule render trong <option>.
    const calledSchedules = frappeGetSpy.mock.calls.some(
      c => String(c[0]).includes('imm08.list_pm_schedules'),
    )
    expect(calledSchedules).toBe(true)
    expect(w.text()).toContain('Định kỳ')
  })

  it('TC-PM-LOCKED-LABEL-PARITY: qr-scan → lockedFromScan + badge', async () => {
    routeQuery = { asset: 'AC-ASSET-0001', source: 'qr-scan' }
    const w = mountView()
    await flushPromises()
    expect(w.text()).toContain('Tạo từ quét QR')
  })
})
