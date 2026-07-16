// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho RCA Record.
//
// Mọi nút chuyển-trạng-thái ở RCADetailView gate theo `allowed_transitions` +
// `can_manage_rca` do BE get_rca emit (SSoT = _RCA_VALID_TRANSITIONS trong
// services/imm12.py) — KHÔNG hardcode `rca.status === 'X'`. FE = (can_manage_rca
// && allowedTransitions.includes(target)).
//
// SSoT map (AC1 / _RCA_VALID_TRANSITIONS):
//   RCA Required     → [RCA In Progress, Cancelled]
//   RCA In Progress  → [Completed, Cancelled]
//   Completed        → []   (terminal → 0 CTA)
//   Cancelled        → []   (terminal → 0 CTA)
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { rcaStatusLabel } from '@/constants/labels'

// Route param cung cấp name RCA (view đọc route.params.id).
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'RCA-2026-0001' }, query: {}, path: '/rca/RCA-2026-0001' }),
  useRouter: () => ({ push: vi.fn() }),
}))

type Rca = Record<string, unknown>
const currentRca = ref<Rca | null>(null)
const getRcaMock = vi.fn((..._a: unknown[]) => Promise.resolve(currentRca.value))
const submitRcaMock = vi.fn().mockResolvedValue({ name: 'RCA-2026-0001', status: 'Completed' })
const startRcaMock = vi.fn().mockResolvedValue({ name: 'RCA-2026-0001', status: 'RCA In Progress' })
const cancelRcaMock = vi.fn().mockResolvedValue({ name: 'RCA-2026-0001', status: 'Cancelled' })
vi.mock('@/api/imm12', () => ({
  getRca: (...a: unknown[]) => getRcaMock(...a),
  submitRca: (...a: unknown[]) => submitRcaMock(...a),
  startRca: (...a: unknown[]) => startRcaMock(...a),
  cancelRca: (...a: unknown[]) => cancelRcaMock(...a),
}))

import RCADetailView from './RCADetailView.vue'

// SSoT transition map (mirror _RCA_VALID_TRANSITIONS).
const RCA_TRANSITIONS: Record<string, string[]> = {
  'RCA Required': ['RCA In Progress', 'Cancelled'],
  'RCA In Progress': ['Completed', 'Cancelled'],
  'Completed': [],
  'Cancelled': [],
}

const ALL_CTA = ['cta-start-rca', 'cta-complete-rca', 'cta-cancel-rca']

function makeRca(status: string, canManage: 0 | 1 = 1): Rca {
  return {
    name: 'RCA-2026-0001',
    incident_report: 'INC-2026-00042',
    asset: 'AC-ASSET-0099',
    status,
    allowed_transitions: RCA_TRANSITIONS[status] ?? [],
    can_manage_rca: canManage,
    rca_method: '5-Why',
    trigger_type: 'Critical Incident',
    due_date: '2026-07-20',
    root_cause: status === 'Completed' ? 'Lỗi nguồn điện' : '',
    corrective_action_summary: status === 'Completed' ? 'Thay bộ nguồn' : '',
    preventive_action_summary: '',
    rca_notes: '',
    completed_date: status === 'Completed' ? '2026-07-09' : null,
    five_why_steps: Array.from({ length: 5 }, (_, i) => ({
      why_number: i + 1, why_question: `Why ${i + 1}?`, why_answer: '',
    })),
  }
}

let wrapper: VueWrapper | null = null
async function mountDetail(): Promise<VueWrapper> {
  wrapper = mount(RCADetailView, {
    global: { stubs: { Transition: false }, mocks: { $t: (k: string) => k } },
  }) as VueWrapper
  await flushPromises()
  return wrapper
}

function ctasShown(w: VueWrapper): string[] {
  return ALL_CTA.filter((id) => w.find(`[data-testid="${id}"]`).exists())
}

beforeEach(() => {
  currentRca.value = null
  getRcaMock.mockClear()
  submitRcaMock.mockClear()
  startRcaMock.mockClear()
  cancelRcaMock.mockClear()
})

afterEach(() => {
  // Teleport (BaseModal) render vào document.body → unmount để không rò node sang test sau.
  wrapper?.unmount()
  wrapper = null
  document.body.replaceChildren()
})

describe('IMM-12 RCA CTA matrix — tập nút KHỚP allowed_transitions (đủ quyền)', () => {
  const EXPECTED: Record<string, string[]> = {
    'RCA Required': ['cta-start-rca', 'cta-cancel-rca'],
    'RCA In Progress': ['cta-complete-rca', 'cta-cancel-rca'],
  }
  for (const [status, expected] of Object.entries(EXPECTED)) {
    it(`${status} → CTA = [${expected.join(', ')}]`, async () => {
      currentRca.value = makeRca(status)
      const w = await mountDetail()
      expect(ctasShown(w).sort()).toEqual([...expected].sort())
    })
  }

  it('RCA Required → KHÔNG có "Hoàn thành RCA" (chặn nhảy-cóc từ Cần phân tích)', async () => {
    currentRca.value = makeRca('RCA Required')
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-complete-rca"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-start-rca"]').exists()).toBe(true)
  })
})

describe('IMM-12 RCA CTA terminal — allowed=[] → 0 nút CTA', () => {
  it.each(['Completed', 'Cancelled'])('%s → 0 CTA (chỉ nhãn tĩnh)', async (status) => {
    currentRca.value = makeRca(status)
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
    // Terminal banner tĩnh render thay CTA.
    expect(w.find('[data-testid="rca-terminal-banner"]').exists()).toBe(true)
  })
})

describe('IMM-12 RCA CTA capability — gate = (can_manage_rca && includes)', () => {
  it.each(['RCA Required', 'RCA In Progress'])(
    '%s nhưng can_manage_rca=0 → 0 CTA + hint vai trò', async (status) => {
      currentRca.value = makeRca(status, 0)
      const w = await mountDetail()
      expect(ctasShown(w)).toEqual([])
      expect(w.text()).toContain('Không có hành động khả dụng cho vai trò hiện tại')
    })
})

describe('IMM-12 RCA control không dead (GATE-6c) — param phát đi == UI-selection', () => {
  it('bấm "Bắt đầu phân tích RCA" → startRca(name) được gọi', async () => {
    currentRca.value = makeRca('RCA Required')
    const w = await mountDetail()
    await w.find('[data-testid="cta-start-rca"]').trigger('click')
    await flushPromises()
    expect(startRcaMock).toHaveBeenCalledTimes(1)
    expect(startRcaMock).toHaveBeenCalledWith('RCA-2026-0001')
  })

  it('bấm "Hủy RCA" → mở modal lý do; xác nhận → cancelRca(name, reason)', async () => {
    currentRca.value = makeRca('RCA In Progress')
    const w = await mountDetail()
    await w.find('[data-testid="cta-cancel-rca"]').trigger('click')
    await nextTick()
    // BaseModal teleport vào body.
    const ta = document.body.querySelector('#rca-cancel-reason') as HTMLTextAreaElement | null
    expect(ta).not.toBeNull()
    ta!.value = 'Thiết bị đã thanh lý'
    ta!.dispatchEvent(new Event('input', { bubbles: true }))
    await flushPromises()
    const confirm = document.body.querySelector('[data-testid="cta-cancel-rca-confirm"]') as HTMLButtonElement | null
    expect(confirm).not.toBeNull()
    confirm!.dispatchEvent(new Event('click', { bubbles: true }))
    await flushPromises()
    expect(cancelRcaMock).toHaveBeenCalledTimes(1)
    expect(cancelRcaMock).toHaveBeenCalledWith('RCA-2026-0001', 'Thiết bị đã thanh lý')
  })
})

describe('IMM-12 RCA i18n — badge tiếng Việt (KHÔNG lộ mã state EN thô)', () => {
  it.each([
    ['RCA Required', 'Cần phân tích'],
    ['RCA In Progress', 'Đang phân tích'],
    ['Completed', 'Đã hoàn tất'],
    ['Cancelled', 'Đã hủy'],
  ])('status %s → badge "%s" (SSoT rcaStatusLabel)', async (status, viLabel) => {
    currentRca.value = makeRca(status)
    const w = await mountDetail()
    const badge = w.find('[data-testid="rca-status-badge"]')
    expect(badge.text()).toBe(rcaStatusLabel(status))
    expect(badge.text()).toBe(viLabel)
    // KHÔNG lộ mã state tiếng Anh thô.
    expect(badge.text()).not.toContain(status)
  })
})

describe('IMM-12 RCA — KHÔNG hardcode gate status=== (GATE-8/LL-FE-51)', () => {
  const raw = readFileSync(resolve(process.cwd(), 'src/views/incident/RCADetailView.vue'), 'utf8')
  // Bỏ comment (JS //, /* */, HTML <!-- -->) — guard soi CODE THẬT, không bắt nhầm
  // comment giải thích anti-pattern.
  const code = raw
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/.*$/gm, '$1')

  it('component KHÔNG còn nhánh gate action bằng rca.status === "Completed"', () => {
    expect(code).not.toMatch(/status\s*===\s*['"]Completed['"]/)
    // status KHÔNG dùng để so === gate action (chỉ dùng cho nhãn hiển thị).
    expect(code).not.toMatch(/\.status\s*===/)
  })

  it('component gate CTA bằng allowed_transitions + can_manage_rca (server-driven)', () => {
    expect(code).toMatch(/allowed_transitions/)
    expect(code).toMatch(/can_manage_rca/)
  })
})
