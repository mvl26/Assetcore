// TDD (FE regression) — IMM-14: AssetDetailView.confirmDecommission KHÔNG để hồ sơ
// giải nhiệm draft mồ côi câm.
//
// Luồng §11.3: create_decommission (docstatus=0) → approve_decommission. Nếu approve
// LỖI SAU khi create THÀNH CÔNG (vd 403 create-only / gate) → thay vì chỉ toast, phải
// điều hướng /decommissions/<created.name> để user/approver mở lại duyệt/thu hồi
// (tách create ≠ approve, GATE-8/LL-FE-51). Happy-path đủ quyền vẫn auto-approve.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// ── Router: pushSpy capturable (component gọi useRouter() 1 lần ở setup) ─────────
const pushSpy = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push: pushSpy }) }))

// Asset risk 'Low' → KHÔNG bắt buộc xác nhận dữ liệu bệnh nhân (đơn giản hoá form).
const currentAsset = {
  name: 'AC-ASSET-2026-00042',
  asset_name: 'Máy X-quang di động',
  asset_code: 'AC-XR-0042',
  lifecycle_status: 'Active',
  risk_classification: 'Low',
}
const fetchOneSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset, loading: false, error: null, fetchOne: fetchOneSpy, transition: vi.fn(),
  }),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: { email: 'tester@h.vn' } }) }))

// Quyền: có decommission.approve → nút "Giải nhiệm" hiện; asset.read/write để render.
const canCaps = new Set<string>(['asset.read', 'asset.write', 'decommission.approve', 'decommission.create'])
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (c: string | readonly string[]) =>
      Array.isArray(c) ? c.some((x) => canCaps.has(x)) : canCaps.has(c as string),
  }),
}))

const notifyFromError = vi.fn()
const toastSuccess = vi.fn()
vi.mock('@/composables/useNotify', () => ({ useNotify: () => ({ fromError: notifyFromError, success: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ show: vi.fn(), success: toastSuccess }) }))

vi.mock('@/api/imm00', () => ({
  getAssetTimeline: vi.fn().mockResolvedValue({ items: [] }),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue(null),
  deleteAsset: vi.fn(),
  getAssetLabelData: vi.fn().mockResolvedValue({}),
  markLabelPrinted: vi.fn(),
  regenerateAssetQrToken: vi.fn(),
  printAssetLabelsPdf: vi.fn(),
  LABEL_PDF_PRESETS: [{ key: 'tem-60x100', label: 'Tem 60×100mm' }],
  LABEL_PDF_PRESET: 'tem-60x100',
  labelPdfPresetLabel: () => 'Tem 60×100mm',
}))
vi.mock('@/api/imm04', () => ({ getCommissioningOrigin: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/errors', () => ({ toApiError: (e: unknown) => e }))
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))

const createDecommission = vi.fn()
const approveDecommission = vi.fn()
vi.mock('@/api/imm14', () => ({
  createDecommission: (...a: unknown[]) => createDecommission(...a),
  approveDecommission: (...a: unknown[]) => approveDecommission(...a),
}))

import AssetDetailView from './AssetDetailView.vue'

const stubs = {
  PageHeader: true,
  teleport: true,
  SmartSelect: true,
  ApproverSelect: true,
  AssetDowntimeWidget: true,
  AssetDepreciationSchedule: true,
  'router-link': { template: '<a><slot /></a>' },
}

async function mountAndFillForm() {
  const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
  await flushPromises()
  // Mở modal giải nhiệm.
  await w.find('[data-testid="btn-decommission"]').trigger('click')
  await flushPromises()
  // Điền form đủ điều kiện submit (risk Low → không cần patient_data).
  await w.find('[data-testid="decom-disposal-method"]').setValue('Huỷ')
  await w.find('[data-testid="decom-reason"]').setValue('Thiết bị hết khấu hao, có quyết định thanh lý.')
  await w.find('[data-testid="decom-confirm-name"]').setValue('AC-ASSET-2026-00042')
  await flushPromises()
  return w
}

beforeEach(() => {
  pushSpy.mockClear()
  fetchOneSpy.mockClear()
  notifyFromError.mockClear()
  toastSuccess.mockClear()
  createDecommission.mockReset()
  approveDecommission.mockReset()
})

describe('AssetDetailView.confirmDecommission — orphan draft guard', () => {
  it('create OK nhưng approve LỖI → điều hướng /decommissions/<created.name> (không mồ côi câm)', async () => {
    createDecommission.mockResolvedValue({
      name: 'DECOM-2026-0099', asset: 'AC-ASSET-2026-00042', workflow_state: 'Draft', docstatus: 0,
    })
    approveDecommission.mockRejectedValue(new Error('403 create-only'))

    const w = await mountAndFillForm()
    await w.find('[data-testid="decom-submit"]').trigger('click')
    await flushPromises()

    expect(createDecommission).toHaveBeenCalledTimes(1)
    expect(approveDecommission).toHaveBeenCalledTimes(1)
    // Lỗi được surface (toast cảnh báo VI) + điều hướng tới biên bản draft.
    expect(notifyFromError).toHaveBeenCalled()
    expect(pushSpy).toHaveBeenCalledWith('/decommissions/DECOM-2026-0099')
    // KHÔNG toast "thành công" khi duyệt lỗi.
    expect(toastSuccess).not.toHaveBeenCalled()
  })

  it('happy-path đủ quyền → create + auto-approve + toast thành công, KHÔNG điều hướng draft', async () => {
    createDecommission.mockResolvedValue({
      name: 'DECOM-2026-0100', asset: 'AC-ASSET-2026-00042', workflow_state: 'Draft', docstatus: 0,
    })
    approveDecommission.mockResolvedValue({
      name: 'DECOM-2026-0100', asset: 'AC-ASSET-2026-00042', workflow_state: 'Approved', docstatus: 1,
      lifecycle_status: 'Decommissioned', decommissioned_on: '2026-07-10 09:00:00',
    })

    const w = await mountAndFillForm()
    await w.find('[data-testid="decom-submit"]').trigger('click')
    await flushPromises()

    expect(createDecommission).toHaveBeenCalledTimes(1)
    expect(approveDecommission).toHaveBeenCalledTimes(1)
    expect(toastSuccess).toHaveBeenCalled()
    expect(fetchOneSpy).toHaveBeenCalled()   // refresh asset → badge đổi
    // KHÔNG điều hướng tới trang biên bản draft ở happy-path.
    expect(pushSpy).not.toHaveBeenCalledWith('/decommissions/DECOM-2026-0100')
  })

  it('create LỖI (duplicate/terminal) → toast lỗi, KHÔNG gọi approve, KHÔNG điều hướng', async () => {
    createDecommission.mockRejectedValue(new Error('CONFLICT duplicate'))

    const w = await mountAndFillForm()
    await w.find('[data-testid="decom-submit"]').trigger('click')
    await flushPromises()

    expect(createDecommission).toHaveBeenCalledTimes(1)
    expect(approveDecommission).not.toHaveBeenCalled()
    expect(notifyFromError).toHaveBeenCalled()
    expect(pushSpy).not.toHaveBeenCalledWith(expect.stringContaining('/decommissions/'))
  })
})
