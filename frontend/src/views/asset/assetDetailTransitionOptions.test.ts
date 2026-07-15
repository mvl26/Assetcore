// Copyright (c) 2026, AssetCore Team
// CR-WF-00-LIFECYCLE-SURFACE (Trục A) — FE: nút "Chuyển trạng thái" dựng THUẦN từ
// server field `asset.allowed_transitions` (get_asset emit). Bảng TRANSITION_MAP
// hardcode client-side ĐÃ BỊ XOÁ khỏi AssetDetailView.vue.
//
// 3 hành vi khoá (chống tái phạm hardcode + carve-out IMM-14):
//   • options-from-server: mock allowed_transitions=[A,B] → render ĐÚNG {A,B}, không hơn.
//   • no-CTA-when-empty: mock allowed_transitions=[] → KHÔNG render khối CTA chuyển-
//     trạng-thái; nút "Giải nhiệm" (IMM-14) độc lập theo canDecommission riêng.
//   • behavioral anti-rehardcode: đổi giá trị mock allowed_transitions PHẢI đổi tập
//     option render → chứng minh options bám server field, KHÔNG bảng tĩnh.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'

// ── Mock router ────────────────────────────────────────────────────────────────
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

// ── Mock store — currentAsset mutable per-test (đổi allowed_transitions trước mount) ──
const currentAsset: {
  name: string; asset_name: string; lifecycle_status: string
  risk_classification: string; allowed_transitions: string[]
} = {
  name: 'AC-ASSET-2026-00042', asset_name: 'Máy thở Dräger',
  lifecycle_status: 'Active', risk_classification: 'Low',
  allowed_transitions: [],
}
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset, loading: false, error: null,
    fetchOne: vi.fn().mockResolvedValue(undefined),
    transition: vi.fn(),
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

vi.mock('@/composables/useNotify', () => ({ useNotify: () => ({ fromError: vi.fn(), success: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ show: vi.fn(), success: vi.fn() }) }))

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

import AssetDetailView from './AssetDetailView.vue'

const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
}

function transitionBtns(w: VueWrapper) {
  return w.findAll('button').filter((b) => b.text().startsWith('→'))
}
function transitionLabels(w: VueWrapper) {
  // '→ Đang bảo trì' → 'Đang bảo trì'
  return transitionBtns(w).map((b) => b.text().replace(/^→\s*/, '').trim())
}
async function mountView() {
  const w = mount(AssetDetailView, { props: { id: currentAsset.name }, global: { stubs } })
  await flushPromises()
  return w
}

describe('AssetDetailView — CTA chuyển-trạng-thái server-driven (CR-WF-00-LIFECYCLE-SURFACE)', () => {
  beforeEach(() => {
    canCaps.clear()
    currentAsset.lifecycle_status = 'Active'
    currentAsset.allowed_transitions = []
  })

  it('options-from-server — render ĐÚNG tập allowed_transitions, KHÔNG hơn', async () => {
    canCaps.add('asset.read'); canCaps.add('asset.write')
    currentAsset.allowed_transitions = ['Under Maintenance', 'Out of Service']
    const w = await mountView()
    expect(w.text()).toContain('Chuyển trạng thái:')
    const labels = transitionLabels(w)
    expect(labels.sort()).toEqual(['Đang bảo trì', 'Ngừng hoạt động'].sort())
    // KHÔNG render option nào ngoài server field (vd Calibrating/Under Repair).
    expect(labels).not.toContain('Đang hiệu chuẩn')
    expect(labels).not.toContain('Đang sửa chữa')
    expect(transitionBtns(w)).toHaveLength(2)
  })

  it('no-CTA-when-empty — allowed_transitions=[] → KHÔNG render khối CTA chuyển-trạng-thái', async () => {
    canCaps.add('asset.read'); canCaps.add('asset.write')
    currentAsset.allowed_transitions = []
    const w = await mountView()
    expect(w.text()).not.toContain('Chuyển trạng thái:')
    expect(transitionBtns(w)).toHaveLength(0)
  })

  it('no-CTA-when-empty — nút "Giải nhiệm" (IMM-14) VẪN theo canDecommission riêng, độc lập allowed_transitions', async () => {
    // allowed_transitions rỗng NHƯNG có quyền giải nhiệm + asset chưa terminal →
    // đường IMM-14 (Hồ sơ giải nhiệm) KHÔNG bị gộp/ẩn theo khối CTA chuyển-trạng-thái.
    canCaps.add('asset.read'); canCaps.add('decommission.approve')
    currentAsset.allowed_transitions = []
    const w = await mountView()
    expect(transitionBtns(w)).toHaveLength(0)         // khối CTA chuyển-trạng-thái ẩn
    expect(w.text()).toContain('Giải nhiệm thiết bị') // nút IMM-14 vẫn hiện (gate riêng)
  })

  it('behavioral anti-rehardcode — đổi mock allowed_transitions → đổi tập option render', async () => {
    canCaps.add('asset.read'); canCaps.add('asset.write')

    currentAsset.allowed_transitions = ['Calibrating']
    const w1 = await mountView()
    const set1 = transitionLabels(w1)
    expect(set1).toEqual(['Đang hiệu chuẩn'])

    currentAsset.allowed_transitions = ['Active', 'Under Repair']
    const w2 = await mountView()
    const set2 = transitionLabels(w2)
    expect(set2.sort()).toEqual(['Đang hoạt động', 'Đang sửa chữa'].sort())

    // Tập option THAY ĐỔI theo server field (nếu còn bảng tĩnh, set2 sẽ giống set1).
    expect(set2).not.toEqual(set1)
    expect(set2).not.toContain('Đang hiệu chuẩn')
  })

  it('write-gate — !asset.write → KHÔNG render nút →state dù server trả allowed_transitions', async () => {
    // Defense-in-depth: server đã lọc capability, nhưng FE giữ can('asset.write') để
    // read-only user (payload cache còn field) KHÔNG thấy nút mutating.
    canCaps.add('asset.read') // KHÔNG asset.write
    currentAsset.allowed_transitions = ['Under Maintenance', 'Out of Service']
    const w = await mountView()
    expect(w.text()).not.toContain('Chuyển trạng thái:')
    expect(transitionBtns(w)).toHaveLength(0)
  })
})
