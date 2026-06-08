// Copyright (c) 2026, AssetCore Team — AssetDetailView rotate QR token (B hardening, TDD)
//
// RED-prove (task B):
//   • user asset.qr.rotate → nút 'Sinh lại mã QR' render; user chỉ-đọc/chỉ-print → KHÔNG render.
//   • click nút → mở BaseModal cảnh báo (KHÔNG window.confirm); xác nhận →
//     regenerateAssetQrToken + refetch asset + toast VI; huỷ → API KHÔNG gọi.
//   • on-error (403/404) → notify VI role=alert, KHÔNG white-screen, KHÔNG leak EN/raw-code.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// ── Mock router ────────────────────────────────────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// ── Mock store (asset đã load) ───────────────────────────────────────────────────
const currentAsset = {
  name: 'AC-ASSET-2026-00042', asset_name: 'Máy thở Dräger',
  lifecycle_status: 'Active', risk_classification: 'Low',
}
const fetchOneSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset, loading: false, error: null,
    fetchOne: fetchOneSpy,
    transition: vi.fn(), error_set: vi.fn(),
  }),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: 'tester' }) }))

// D6 (ADR-IMM00-QR-SCAN-ACTION, phương án B): nút 'Sinh lại mã QR' gate
// asset.QR.ROTATE (rotate = GHI; KHÔNG asset.print). print KHÔNG đủ để rotate.
const canCaps = new Set<string>(['asset.qr.rotate'])
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (c: string | readonly string[]) =>
      Array.isArray(c) ? c.some((x) => canCaps.has(x)) : canCaps.has(c as string),
  }),
}))

const notifyFromErrorSpy = vi.fn()
const toastSuccessSpy = vi.fn()
const toastShowSpy = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ fromError: notifyFromErrorSpy, success: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ show: toastShowSpy, success: toastSuccessSpy }),
}))

// ── Spy API ──────────────────────────────────────────────────────────────────────
const regenerateSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: vi.fn().mockResolvedValue({ items: [] }),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue(null),
  deleteAsset: vi.fn(),
  getAssetLabelData: vi.fn().mockResolvedValue({}),
  markLabelPrinted: vi.fn(),
  regenerateAssetQrToken: (asset: string) => regenerateSpy(asset),
}))
vi.mock('@/api/imm04', () => ({ getCommissioningOrigin: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/imm14', () => ({ createDecommission: vi.fn(), approveDecommission: vi.fn() }))
// Giữ ApiError/ErrorCode THẬT (test 429 cần instanceof ApiError + code đúng);
// chỉ stub toApiError thành identity để ApiError đã reject pass thẳng qua.
vi.mock('@/api/errors', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/errors')>()
  return { ...actual, toApiError: (e: unknown) => e }
})
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))

import AssetDetailView from './AssetDetailView.vue'
import { ApiError, ErrorCode } from '@/api/errors'

const stubs = {
  PageHeader: true, teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
}

function findByText(w: ReturnType<typeof mount>, txt: string) {
  return w.findAll('button').find(b => b.text().includes(txt))
}

describe('AssetDetailView — rotate QR token (B)', () => {
  beforeEach(() => {
    // No-raw-token (ADR-001 §D4 rule 9): resolve trả {name, qr_url} — KHÔNG qr_token.
    // Flow vẫn xanh ⇒ confirmRegenQr KHÔNG phụ thuộc field đã gỡ.
    regenerateSpy.mockReset().mockResolvedValue({
      name: 'AC-ASSET-2026-00042', qr_url: 'http://miyano/a/NEW_tok',
    })
    fetchOneSpy.mockClear()
    notifyFromErrorSpy.mockClear()
    toastSuccessSpy.mockClear()
    toastShowSpy.mockClear()
    canCaps.clear()
    canCaps.add('asset.qr.rotate')
  })

  it("user CHỈ-ĐỌC (asset.read, KHÔNG rotate) → nút 'Sinh lại mã QR' KHÔNG render", async () => {
    canCaps.clear()
    canCaps.add('asset.read')
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findByText(w, 'Sinh lại mã QR')).toBeFalsy()
  })

  it("D6 — user CHỈ có asset.print (KHÔNG rotate) → nút 'Sinh lại mã QR' KHÔNG render", async () => {
    // Tách quyền: persona vận hành in được NHƯNG KHÔNG rotate được (least-privilege).
    canCaps.clear()
    canCaps.add('asset.print')
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findByText(w, 'Sinh lại mã QR')).toBeFalsy()
  })

  it("user CÓ asset.qr.rotate → nút 'Sinh lại mã QR' render", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findByText(w, 'Sinh lại mã QR')).toBeTruthy()
  })

  it("click nút → mở modal cảnh báo (KHÔNG window.confirm); API CHƯA gọi", async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'Sinh lại mã QR')!.trigger('click')
    await flushPromises()
    // KHÔNG dùng window.confirm — cảnh báo qua modal.
    expect(confirmSpy).not.toHaveBeenCalled()
    // Cảnh báo: vô hiệu hoá mọi nhãn QR đã in.
    expect(w.text()).toContain('vô hiệu hoá mọi nhãn QR đã in')
    // Mở modal-only, CHƯA gọi API.
    expect(regenerateSpy).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it("xác nhận trong modal → regenerateAssetQrToken(id) + refetch + toast VI", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'Sinh lại mã QR')!.trigger('click')
    await flushPromises()
    // Nút xác nhận trong modal.
    const confirmBtn = findByText(w, 'Xác nhận cấp lại')
    expect(confirmBtn).toBeTruthy()
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(regenerateSpy).toHaveBeenCalledTimes(1)
    expect(regenerateSpy).toHaveBeenCalledWith('AC-ASSET-2026-00042')
    // Refetch asset sau rotate (nhãn/qr_url mới phản ánh trong view).
    expect(fetchOneSpy).toHaveBeenCalled()
    // Toast VI thành công.
    expect(toastSuccessSpy).toHaveBeenCalled()
    const msg = String(toastSuccessSpy.mock.calls[0]?.[0] ?? '')
    expect(msg.length).toBeGreaterThan(0)
    expect(/[A-Za-z]{4,}/.test(msg.replace(/QR/g, ''))).toBe(false) // KHÔNG leak EN
  })

  it("huỷ modal → regenerateAssetQrToken KHÔNG được gọi (no-op)", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'Sinh lại mã QR')!.trigger('click')
    await flushPromises()
    const cancelBtn = w.findAll('button').find(b => b.text().trim() === 'Huỷ')
    expect(cancelBtn).toBeTruthy()
    await cancelBtn!.trigger('click')
    await flushPromises()
    expect(regenerateSpy).not.toHaveBeenCalled()
  })

  it("on-error (403/404) → notify VI (KHÔNG white-screen, KHÔNG leak raw-code)", async () => {
    regenerateSpy.mockRejectedValueOnce({ code: 'FORBIDDEN', message: 'Bạn không có quyền cấp lại mã QR.' })
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'Sinh lại mã QR')!.trigger('click')
    await flushPromises()
    await findByText(w, 'Xác nhận cấp lại')!.trigger('click')
    await flushPromises()
    // notify.fromError nhận ApiError VI (KHÔNG throw → KHÔNG white-screen).
    expect(notifyFromErrorSpy).toHaveBeenCalledTimes(1)
    // View vẫn render (KHÔNG trang trắng).
    expect(w.text()).toContain('Máy thở Dräger')
  })

  it("429 RATE_LIMITED → notify VI 'thao tác quá nhanh', modal Sinh-lại VẪN MỞ, 0 EN-leak/raw-code, guard reset", async () => {
    // BE rotate hardening (B): vượt ngưỡng @rate_limit → envelope 429 → axios dựng
    // ApiError code=RATE_LIMITED + message VI verbatim (KHÔNG EN-leak "rate limit",
    // KHÔNG raw-code "429"/"RATE_LIMITED"). FE chỉ cần notify.fromError đúng bucket.
    const rateErr = new ApiError(
      'Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút.',
      { code: ErrorCode.RATE_LIMITED, httpStatus: 429 },
    )
    regenerateSpy.mockRejectedValueOnce(rateErr)
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'Sinh lại mã QR')!.trigger('click')
    await flushPromises()
    await findByText(w, 'Xác nhận cấp lại')!.trigger('click')
    await flushPromises()
    // notify.fromError nhận ApiError 429 (KHÔNG throw → KHÔNG white-screen).
    expect(notifyFromErrorSpy).toHaveBeenCalledTimes(1)
    const arg = notifyFromErrorSpy.mock.calls[0]?.[0] as ApiError
    expect(arg.code).toBe(ErrorCode.RATE_LIMITED)
    expect(arg.httpStatus).toBe(429)
    // Message VI verbatim — KHÔNG EN-leak, KHÔNG raw-code/status.
    expect(arg.message).toContain('thao tác quá nhanh')
    expect(/rate limit/i.test(arg.message)).toBe(false)
    expect(arg.message).not.toContain('RATE_LIMITED')
    expect(arg.message).not.toContain('429')
    // Modal Sinh-lại VẪN MỞ để user thử lại (chỉ đóng khi thành công).
    expect(findByText(w, 'Xác nhận cấp lại')).toBeTruthy()
    // Double-submit guard reset về false (finally) → cho phép thử lại.
    const confirmBtn = findByText(w, 'Xác nhận cấp lại')!
    expect(confirmBtn.attributes('disabled')).toBeUndefined()
    // View vẫn render.
    expect(w.text()).toContain('Máy thở Dräger')
  })
})
