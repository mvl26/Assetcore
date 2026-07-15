// Copyright (c) 2026, AssetCore Team
//
// IMM-16 — InternalAuditDetailView: HYDRATE verdict bảng kiểm đã lưu (CR-27b /
// silent-verdict-loss). Khi mở audit ĐÃ nhập bảng kiểm, get_audit trả
// checklist_items[].result đã lưu → FE phải:
//   (a) reverse-map result → finding_status để prime lại <select> (KHÔNG reset về
//       'Compliant'), khớp SSoT map BE _FINDING_STATUS_TO_RESULT;
//   (b) khi KHÔNG còn sửa được (Reporting/Closed) vẫn render read-only verdict
//       per-dòng (nguồn = `result` persisted, VI, không leak enum EN).
//
// RED trước fix: checklistItems LUÔN khởi tạo [{ finding_status: 'Compliant' }] và
// tab checklist chỉ hiện message khi !canChecklist → verdict đã lưu BIẾN MẤT khi reload.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: vi.fn((fn: () => unknown) => fn()), loading: { value: false } }),
}))

const auditState: { value: Record<string, unknown> | null } = { value: null }
const getAudit = vi.fn(async (..._a: unknown[]) => auditState.value)
vi.mock('@/api/imm16', () => ({ getAudit: (...a: unknown[]) => getAudit(...a) }))

const actionStartAudit = vi.fn().mockResolvedValue({ name: 'AUD-2026-00001' })
const actionCompleteChecklist = vi.fn().mockResolvedValue({ findings_created: 0 })
const actionCloseAudit = vi.fn().mockResolvedValue({ name: 'AUD-2026-00001' })
vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({ actionStartAudit, actionCompleteChecklist, actionCloseAudit }),
}))

import InternalAuditDetailView from './InternalAuditDetailView.vue'

const stubs = {
  PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
  StatusBadge: true,
  SkeletonLoader: true,
}

function aud(over: Record<string, unknown> = {}) {
  return {
    name: 'AUD-2026-00001',
    audit_code: 'AUD-2026-00001',
    audit_type: 'Internal',
    planned_start: '2026-01-01',
    planned_end: '2026-01-10',
    lead_auditor: 'auditor@benhvien.vn',
    lead_auditor_name: 'KTV Nguyễn Văn A',
    status: 'Planned',
    findings_count: 0,
    allowed_transitions: [] as string[],
    can_operate: false,
    can_close: false,
    ...over,
  }
}

async function render(fixture: Record<string, unknown>) {
  auditState.value = fixture
  const w = mount(InternalAuditDetailView, { props: { id: 'AUD-2026-00001' }, global: { stubs } })
  await flushPromises()
  return w
}

async function openChecklistTab(w: VueWrapper) {
  const btn = w.findAll('button').find((b) => b.text() === 'Bảng kiểm')
  if (btn) await btn.trigger('click')
  await flushPromises()
}

function has(w: VueWrapper, testid: string) {
  return w.find(`[data-testid="${testid}"]`).exists()
}

beforeEach(() => {
  vi.clearAllMocks()
  auditState.value = null
})

describe('InternalAuditDetailView — read-only verdict round-trip (Reporting/Closed)', () => {
  it("audit ĐÃ Gửi (Reporting) có result='Non-Conforming' → hiện verdict 'Không phù hợp', KHÔNG reset về Compliant", async () => {
    const w = await render(
      aud({
        status: 'Reporting',
        allowed_transitions: ['close'],
        can_operate: true,
        can_close: true,
        checklist_items: [
          { idx: 1, item_description: 'Hồ sơ hiệu chuẩn đầy đủ', result: 'Non-Conforming', notes: 'Thiếu tem' },
        ],
      }),
    )
    await openChecklistTab(w)
    expect(has(w, 'checklist-readonly')).toBe(true)
    expect(has(w, 'checklist-editor')).toBe(false)
    const verdict = w.find('[data-testid="readonly-verdict"]')
    expect(verdict.exists()).toBe(true)
    expect(verdict.text()).toBe('Không phù hợp') // verdict đã lưu hiển thị lại
    expect(verdict.text()).not.toBe('Phù hợp') // KHÔNG rơi về Conforming/Compliant
  })

  it('nhiều dòng round-trip đúng nhãn VI theo result [Conforming, Non-Conforming, Not Applicable]', async () => {
    const w = await render(
      aud({
        status: 'Closed',
        allowed_transitions: [],
        can_close: true,
        checklist_items: [
          { idx: 1, item_description: 'A', result: 'Conforming' },
          { idx: 2, item_description: 'B', result: 'Non-Conforming' },
          { idx: 3, item_description: 'C', result: 'Not Applicable' },
        ],
      }),
    )
    await openChecklistTab(w)
    const verdicts = w.findAll('[data-testid="readonly-verdict"]').map((v) => v.text())
    expect(verdicts).toEqual(['Phù hợp', 'Không phù hợp', 'Không áp dụng'])
  })

  it('Reporting KHÔNG có checklist_items → fallback message (không crash, không bảng rỗng giả)', async () => {
    const w = await render(
      aud({ status: 'Reporting', allowed_transitions: ['close'], can_close: true }),
    )
    await openChecklistTab(w)
    expect(has(w, 'checklist-readonly')).toBe(false)
    expect(has(w, 'checklist-editor')).toBe(false)
    expect(w.text()).toContain('Bảng kiểm chỉ chỉnh sửa được')
  })
})

describe('InternalAuditDetailView — editable hydration (In Progress)', () => {
  it("editor prime <select> = 'Major NC' từ result='Non-Conforming' (reverse-map), KHÔNG 'Compliant'", async () => {
    const w = await render(
      aud({
        status: 'In Progress',
        allowed_transitions: ['complete_checklist'],
        can_operate: true,
        checklist_items: [{ idx: 1, item_description: 'X', result: 'Non-Conforming', notes: '' }],
      }),
    )
    await openChecklistTab(w)
    expect(has(w, 'checklist-editor')).toBe(true)
    const select = w.find('[data-testid="checklist-editor"] select')
    expect(select.exists()).toBe(true)
    expect((select.element as HTMLSelectElement).value).toBe('Major NC')
  })

  it("editor hydrate Conforming→'Compliant' và Not Applicable→'N/A' đúng option select", async () => {
    const w = await render(
      aud({
        status: 'In Progress',
        allowed_transitions: ['complete_checklist'],
        can_operate: true,
        checklist_items: [
          { idx: 1, item_description: 'A', result: 'Conforming' },
          { idx: 2, item_description: 'B', result: 'Not Applicable' },
        ],
      }),
    )
    await openChecklistTab(w)
    const selects = w.findAll('[data-testid="checklist-editor"] select')
    expect((selects[0].element as HTMLSelectElement).value).toBe('Compliant')
    expect((selects[1].element as HTMLSelectElement).value).toBe('N/A')
  })

  it('In Progress KHÔNG có checklist_items → giữ 1 dòng mặc định finding_status=Compliant (regression)', async () => {
    const w = await render(
      aud({ status: 'In Progress', allowed_transitions: ['complete_checklist'], can_operate: true }),
    )
    await openChecklistTab(w)
    const selects = w.findAll('[data-testid="checklist-editor"] select')
    expect(selects.length).toBe(1)
    expect((selects[0].element as HTMLSelectElement).value).toBe('Compliant')
  })
})
