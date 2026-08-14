// Copyright (c) 2026, AssetCore Team
// CR-WF-00-TRANSITION-AUTHZ (Trục A) — FE guard cho endpoint transition_status siết authz.
//
// Bối cảnh: BE nay gate endpoint transition_status bằng rbac.require('asset.write') +
// assert_vendor_can_access (mirror get_asset). FE PHẢI khớp:
//   • T6 (guard chống tái phạm affordance-leak): can('asset.write')=false → KHÔNG render
//     nút '→ <state>' nào (v-if @AssetDetailView.vue giữ nguyên). Test CÔ LẬP đúng gate
//     write: user CÓ read+delete+print+rotate nhưng KHÔNG write vẫn không thấy nút →state
//     (chứng minh khối transition gate ĐÚNG asset.write, không phải "có cap bất kỳ").
//   • FE-2 (notification-contract): khi BE trả 403 (vendor out-of-scope / read-only bypass
//     qua URL), confirmTransition PHẢI notify.fromError — KHÔNG nuốt lỗi im lặng (trước đây
//     handler chỉ try/finally → 403 thành unhandled rejection, modal treo, user không biết).
//   • happy-path regression: write + in-scope → success toast VI + modal đóng, KHÔNG notify lỗi.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { ApiError, ErrorCode } from '@/api/errors'

// ── Mock router ────────────────────────────────────────────────────────────────
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

// ── Mock store — transition điều khiển được per-test (resolve success / reject 403) ──
// allowed_transitions = server-driven CTA (CR-WF-00-LIFECYCLE-SURFACE): view dựng nút
// →state TỪ field này (đã bỏ bảng TRANSITION_MAP hardcode). Active → 4 CTA (sorted BE),
// KHÔNG Decommissioned. Nút vẫn CHỈ render khi can('asset.write') (gate T6 cô lập).
const currentAsset = {
  name: 'AC-ASSET-2026-00042', asset_name: 'Máy thở Dräger',
  lifecycle_status: 'Active', risk_classification: 'Low',
  allowed_transitions: ['Calibrating', 'Out of Service', 'Under Maintenance', 'Under Repair'],
}
const transitionMock = vi.fn()
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset, loading: false, error: null,
    fetchOne: vi.fn().mockResolvedValue(undefined),
    transition: transitionMock,
  }),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: 'tester' }) }))

// Capability set giả lập per-test.
const canCaps = new Set<string>()
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (c: string | readonly string[]) =>
      Array.isArray(c) ? c.some((x) => canCaps.has(x)) : canCaps.has(c as string),
  }),
}))

// Hoisted spies — assert notify.fromError (403) và toast.success (happy) đúng nhánh.
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
  labelPdfPresetLabel: (p: string) => p,
}))
vi.mock('@/api/imm04', () => ({ getCommissioningOrigin: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/imm14', () => ({ createDecommission: vi.fn(), approveDecommission: vi.fn() }))
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))

import AssetDetailView from '@/views/asset/AssetDetailView.vue'

const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
}

function transitionBtns(w: VueWrapper) {
  return w.findAll('button').filter((b) => b.text().startsWith('→'))
}
function confirmBtn(w: VueWrapper) {
  return w.findAll('button').find((b) => b.text().includes('Xác nhận'))
}

describe('AssetDetailView — transition authz (CR-WF-00-TRANSITION-AUTHZ)', () => {
  beforeEach(() => {
    canCaps.clear()
    currentAsset.lifecycle_status = 'Active'
    transitionMock.mockReset()
    notifyFromError.mockReset()
    toastSuccess.mockReset()
  })

  it('T6 — caps khác NHƯNG !asset.write → KHÔNG nút →state nào (write-gate cô lập)', async () => {
    canCaps.add('asset.read'); canCaps.add('asset.delete')
    canCaps.add('asset.print'); canCaps.add('asset.qr.rotate') // KHÔNG asset.write
    const w = mount(AssetDetailView, { props: { id: currentAsset.name }, global: { stubs } })
    await flushPromises()
    expect(w.text()).not.toContain('Chuyển trạng thái:')
    expect(transitionBtns(w).length).toBe(0)
  })

  it('FE-2 — 403 từ BE (vendor out-of-scope) → notify.fromError, KHÔNG nuốt lỗi im lặng', async () => {
    canCaps.add('asset.read'); canCaps.add('asset.write')
    transitionMock.mockRejectedValue(
      new ApiError('Bạn không có quyền thao tác với thiết bị này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mount(AssetDetailView, { props: { id: currentAsset.name }, global: { stubs } })
    await flushPromises()
    const btn = transitionBtns(w)[0]
    expect(btn).toBeTruthy()
    await btn.trigger('click') // mở modal xác nhận
    await flushPromises()
    const cb = confirmBtn(w)
    expect(cb).toBeTruthy()
    await cb!.trigger('click')
    await flushPromises()
    expect(notifyFromError).toHaveBeenCalledTimes(1)
    expect(toastSuccess).not.toHaveBeenCalled()
  })

  it('happy-path — write + in-scope → success toast VI + modal đóng, KHÔNG notify lỗi', async () => {
    canCaps.add('asset.read'); canCaps.add('asset.write')
    transitionMock.mockResolvedValue({
      success: true, data: { name: currentAsset.name, lifecycle_status: 'Under Maintenance' },
    })
    const w = mount(AssetDetailView, { props: { id: currentAsset.name }, global: { stubs } })
    await flushPromises()
    await transitionBtns(w)[0].trigger('click')
    await flushPromises()
    await confirmBtn(w)!.trigger('click')
    await flushPromises()
    expect(toastSuccess).toHaveBeenCalledTimes(1)
    expect(notifyFromError).not.toHaveBeenCalled()
    expect(confirmBtn(w)).toBeFalsy() // modal đóng → nút "Xác nhận" biến mất
  })
})
