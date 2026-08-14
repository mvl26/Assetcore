// Copyright (c) 2026, AssetCore Team
// TC-UX4-32 (docs/ui-ux/03 §13.6) — AssetDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N4).
//
// Màn NẶNG NHẤT của lô (1300+ dòng, 24 file test cũ bám vào) nên làm CUỐI. RED trước fix: lỗi nạp
// in ra một dải `.alert-error` với CHUỖI `store.error` — 403, 404 và mất mạng cùng một câu, KHÔNG
// nút «Thử lại», KHÔNG lối về danh sách (ngõ cụt); dải 6 tab + 2 nút Chỉnh sửa/Xoá nằm NGOÀI nhánh
// nội dung nên hồ sơ không đọc được vẫn phơi nguyên. Sau fix: 4 trạng thái loại trừ bằng cấu trúc,
// thanh tab hoisting lên prop shell (ADR-UX-25) và NẠP LƯỜI vẫn đi qua `onTabChange`.
import { reactive } from 'vue'
import { vi, describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push: pushSpy, back: vi.fn() }) }))

const ASSET_ID = 'AC-ASSET-2026-00042'

// Store mock mirror hành vi THẬT của `stores/imm00`: NUỐT lỗi thành chuỗi `error`, KHÔNG throw
// — chính hình dạng khiến view cũ không phân loại được kind.
// `reactive`: view đọc qua getter của store mock ⇒ state phải theo dõi được, nếu không kết
// quả nạp bất đồng bộ không bao giờ tới màn (và test «xanh giả» ở nhánh notfound).
const storeState = reactive<{
  currentAsset: Record<string, unknown> | null
  loading: boolean
  error: string | null
}>({ currentAsset: null, loading: false, error: null })
const fetchOneSpy = vi.fn()

vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    get currentAsset() { return storeState.currentAsset },
    get loading() { return storeState.loading },
    get error() { return storeState.error },
    fetchOne: fetchOneSpy,
    transition: vi.fn(),
  }),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: 'tester' }) }))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ fromError: vi.fn(), success: vi.fn(), show: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ show: vi.fn(), success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}))
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: vi.fn().mockResolvedValue({ items: [], total: 0 }),
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
vi.mock('@/api/imm14', () => ({ createDecommission: vi.fn(), approveDecommission: vi.fn() }))
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))
vi.mock('@/api/connections', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/connections')>()),
  getConnections: vi.fn().mockResolvedValue({ doctype: 'AC Asset', name: 'AC-ASSET-2026-00042', total: 0, groups: [] }),
}))

import AssetDetailView from '@/views/asset/AssetDetailView.vue'

const stubs = {
  teleport: true, SmartSelect: true, ApproverSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
  RelatedRecords: true,
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
  'router-link': { template: '<a><slot /></a>' },
}

function assetFixture() {
  return {
    name: ASSET_ID,
    asset_name: 'Máy thở Dräger Evita V600',
    asset_code: 'AC-VENT-0042',
    lifecycle_status: 'Active',
    purchase_date: '2025-01-10',
    gross_purchase_amount: 1_200_000_000,
  }
}

function setStore(over: Partial<typeof storeState>) {
  Object.assign(storeState, { currentAsset: null, loading: false, error: null }, over)
}

function mountView() {
  setActivePinia(createPinia())
  return mount(AssetDetailView, { props: { id: ASSET_ID }, global: { stubs } })
}

describeDetailStates({
  view: 'AssetDetailView',
  tc: 'TC-UX4-32',
  mount: () => mountView() as never,
  pending: () => {
    setStore({ loading: true })
    fetchOneSpy.mockReturnValue(new Promise(() => {}))
  },
  // Store nuốt lỗi ⇒ view chỉ thấy `error` chuỗi; vì vậy mock NÉM để chứng minh nhánh
  // `try/catch` mới của view giữ NGUYÊN đối tượng lỗi (kind phân loại được).
  fail: (e) => fetchOneSpy.mockImplementation(async () => { setStore({}); throw e }),
  empty: () => fetchOneSpy.mockImplementation(async () => setStore({ currentAsset: null })),
  ok: () => fetchOneSpy.mockImplementation(async () => setStore({ currentAsset: assetFixture() })),
  loadCalls: () => fetchOneSpy.mock.calls.length,
  reset: () => {
    fetchOneSpy.mockReset()
    pushSpy.mockClear()
    setStore({})
  },
  recordId: ASSET_ID,
  ctaTestIds: ['cta-edit', 'cta-delete', 'btn-decommission'],
  hasTabs: true,
  routerPush: pushSpy,
})

describe('AssetDetailView — nạp LƯỜI tab «Bản ghi liên quan» sống sót sau hoisting', () => {
  it('bấm tab thứ 6 ⇒ đổi panel đúng 1 lần, vẫn ĐÚNG 1 thanh tab', async () => {
    fetchOneSpy.mockReset().mockImplementation(async () => setStore({ currentAsset: assetFixture() }))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="tab-panel-related"]').exists()).toBe(false)
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="tab-panel-related"]').exists()).toBe(true)
    expect(w.findAll('[role="tablist"]').length).toBe(1)
    expect(w.findAll('[aria-selected="true"]').length).toBe(1)
  })
})
