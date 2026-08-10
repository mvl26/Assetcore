// TDD — TC-RWD-07 (F4 P2): AssetDetailView tab-bar overflow-x-auto → tab cuối
// 'audit'/'related' reachable (cuộn ngang) trên mobile, KHÔNG clip. Desktop KHÔNG vỡ.
//
// ── VIẾT LẠI 2026-08-04 (AC-UX-068, docs/ui-ux/07 §5): DỜI LỜI HỨA, KHÔNG NỚI LỎNG ──
// Bản cũ là test MỨC NGUỒN: nó tìm chuỗi literal 6 khoá tab trong `AssetDetailView.vue`
// rồi soi `<div>` đứng ngay trước có `overflow-x-auto`, và soi khối `v-for` có
// `shrink-0`/`whitespace-nowrap`. Sau khi màn này uỷ quyền thanh tab cho SSoT
// `DetailTabBar`, markup ấy KHÔNG CÒN nằm trong file này — regex sẽ không tìm thấy gì.
//
// Chú thích bản cũ dặn «TUYỆT ĐỐI KHÔNG nới lỏng assert overflow-x-auto/shrink-0».
// Cách tôn trọng câu đó không phải là xoá assert, mà là chấm CHÍNH lời hứa ấy ở nơi
// markup thật sự sống — và chấm bằng RENDER THẬT thay vì regex:
//   • hợp đồng mức component: `DetailTabBar.test.ts` (TC-CONNTAB-03/08) — 0 lời hứa bị mất;
//   • hợp đồng mức MÀN (file này): màn đã tiêu thụ SSoT, không còn bản fork, và khi
//     mount thật thì container vẫn cuộn ngang được, mỗi nút vẫn không co.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const SRC = readFileSync(resolve(__dirname, 'AssetDetailView.vue'), 'utf8')

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

const currentAsset = {
  name: 'AC-ASSET-2026-00042',
  asset_name: 'Máy thở Dräger Evita V600',
  asset_code: 'AC-VENT-0042',
  lifecycle_status: 'Active',
  purchase_date: '2025-01-10',
  gross_purchase_amount: 1200000000,
}

vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset, loading: false, error: null,
    fetchOne: vi.fn().mockResolvedValue(undefined), transition: vi.fn(),
  }),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: 'tester' }) }))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ fromError: vi.fn(), success: vi.fn(), show: vi.fn() }),
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
  getConnections: vi.fn().mockResolvedValue({
    doctype: 'AC Asset', name: 'AC-ASSET-2026-00042', total: 0, groups: [],
  }),
}))

import AssetDetailView from './AssetDetailView.vue'

const stubs = {
  PageHeader: true, teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
  'router-link': { template: '<a><slot /></a>' },
}

async function mountDetail() {
  const w = mount(AssetDetailView, { props: { id: currentAsset.name }, global: { stubs } })
  await flushPromises()
  return w
}

/** Dấu vân tay thanh tab tự chế — docs/ui-ux/07 §1.2. */
const SELF_DRAWN_TAB_RE = /<button\b[^>]*?:class\s*=\s*"[^"]*\b(?:activeTab|tab)\s*===/g

beforeEach(() => setActivePinia(createPinia()))

describe('TC-RWD-07 — AssetDetailView đã uỷ quyền thanh tab cho SSoT', () => {
  // Lô 2 / ADR-UX-25: thanh tab HOISTING lên prop của `DetailPageShell` ⇒ màn này tiêu thụ
  // SSoT GIÁN TIẾP (đúng hình dạng mà `detailTabBarAdoption` test (h) đã khoá cho
  // `InternalAuditDetailView`). Lời hứa KHÔNG đổi — chỉ đổi đường đi tới SSoT: 0 import trực
  // tiếp, 0 thẻ `<DetailTabBar>` cục bộ, và thanh tab chỉ tồn tại trong nhánh `content`.
  it('nguồn KHÔNG import trực tiếp DetailTabBar mà đi qua DetailPageShell', () => {
    expect(SRC).not.toMatch(/import\s+DetailTabBar\b/)
    expect(SRC.split('<DetailTabBar').length - 1).toBe(0)
    expect(SRC).toContain('DetailPageShell')
    expect(SRC).toContain('active-tab')
  })

  it('nguồn KHÔNG còn bản fork: 0 nút-tab tự chế, 0 role="tablist" tự khai', () => {
    expect(SRC.match(SELF_DRAWN_TAB_RE) ?? []).toHaveLength(0)
    expect(SRC).not.toContain('role="tablist"')
  })

  it('6 khoá tab + 6 nhãn tiếng Việt còn nguyên trong nguồn (không mất tab khi đổi khuôn)', () => {
    for (const key of ['info', 'depreciation', 'timeline', 'kpi', 'audit', 'related']) {
      expect(SRC, `mất khoá tab '${key}'`).toContain(`'${key}'`)
    }
    for (const label of [
      'Thông tin', 'Khấu hao', 'Lịch sử', 'Chỉ số hiệu suất', 'Nhật ký truy vết', 'Bản ghi liên quan',
    ]) {
      expect(SRC, `mất nhãn «${label}»`).toContain(label)
    }
  })
})

describe('TC-RWD-07 — hợp đồng cuộn ngang chấm bằng RENDER THẬT trên chính màn này', () => {
  it('tab-bar container có overflow-x-auto (tab cuối reachable, KHÔNG clip)', async () => {
    const w = await mountDetail()
    const bar = w.find('[role="tablist"]')
    expect(bar.exists()).toBe(true)
    expect(bar.classes().join(' ')).toContain('overflow-x-auto')
  })

  it('mỗi tab shrink-0 ∧ whitespace-nowrap để không bị co / xuống dòng', async () => {
    const w = await mountDetail()
    const tabs = w.findAll('[role="tab"]')
    expect(tabs).toHaveLength(6)
    for (const t of tabs) {
      const cls = t.classes().join(' ')
      expect(cls).toContain('shrink-0')
      expect(cls).toContain('whitespace-nowrap')
    }
  })

  it("tab 'audit' và 'related' (2 tab cuối) render đủ, nhãn tiếng Việt", async () => {
    const w = await mountDetail()
    expect(w.find('[data-testid="tab-audit"]').text()).toBe('Nhật ký truy vết')
    expect(w.find('[data-testid="tab-related"]').text()).toBe('Bản ghi liên quan')
  })
})
