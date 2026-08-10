// Copyright (c) 2026, AssetCore Team
// TDD vòng 4 — InternalAuditDetailView áp khuôn `DetailPageShell` + thanh tab dùng
// chung `DetailTabBar` + dải chỉ số.
//
// RED trước fix: `const loading = ref(false)` ⇒ lượt render TRƯỚC khi onMounted chạy
// rơi vào nhánh `!audit` ⇒ NHÁY "không tìm thấy" một nhịp rồi mới ra khung xương.
// Ngoài ra 3 tab tự chế bằng `activeTab === '...'` (27/32 màn chi tiết lặp lại nợ này).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { ApiError, ErrorCode } from '@/api/errors'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push: pushSpy }) }))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: vi.fn((fn: () => unknown) => fn()), loading: { value: false } }),
}))

const getAudit = vi.fn()
vi.mock('@/api/imm16', () => ({ getAudit: (...a: unknown[]) => getAudit(...a) }))

vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    actionStartAudit: vi.fn().mockResolvedValue({ name: 'AUD-2026-00001' }),
    actionCompleteChecklist: vi.fn().mockResolvedValue({ findings_created: 0 }),
    actionCloseAudit: vi.fn().mockResolvedValue({ name: 'AUD-2026-00001' }),
  }),
}))

import InternalAuditDetailView from './InternalAuditDetailView.vue'

// PageHeader stub render slot; KHÔNG stub DetailPageShell/DetailTabBar/DetailLoadError.
const stubs = {
  PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
  StatusBadge: true,
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
    findings_count: 3,
    allowed_transitions: [] as string[],
    can_operate: false,
    can_close: false,
    ...over,
  }
}

function mountView() {
  return mount(InternalAuditDetailView, { props: { id: 'AUD-2026-00001' }, global: { stubs } })
}

function ctaCount(w: VueWrapper): number {
  return (
    w.findAll('[data-testid="cta-start"]').length
    + w.findAll('[data-testid="cta-close"]').length
    + w.findAll('[data-testid="no-actions-hint"]').length
    + w.findAll('[data-testid="detail-actions"]').length
    + w.findAll('[data-testid="detail-kpi"]').length
  )
}

function reloadButton(w: VueWrapper) {
  return w.findAll('button').find((b) => b.text().includes(['Thử', 'lại'].join(' ')))
}

beforeEach(() => {
  getAudit.mockReset()
  pushSpy.mockClear()
})

describe('InternalAuditDetailView — 4 trạng thái loại trừ (TC-UX4-22)', () => {
  it('a) đang nạp ⇒ khung xương; KHÔNG nháy "không tìm thấy" ngay nhịp đầu', async () => {
    getAudit.mockReturnValue(new Promise(() => {}))
    const w = mountView()
    // Chưa flush: đây CHÍNH LÀ nhịp render đầu tiên trước onMounted.
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(ctaCount(w)).toBe(0)
  })

  it('b) lỗi mạng ⇒ kind=unknown; bấm nạp lại ⇒ gọi lại lần 2', async () => {
    getAudit.mockRejectedValue(new ApiError('Mất kết nối', ErrorCode.NETWORK_ERROR, 0))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(ctaCount(w)).toBe(0)
    getAudit.mockResolvedValue(aud())
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(getAudit).toHaveBeenCalledTimes(2)
    expect(w.attributes('data-state')).toBe('content')
  })

  it('c) 403 in-envelope ⇒ kind=forbidden, 0 nút nạp lại, KHÔNG điều hướng', async () => {
    getAudit.mockRejectedValue(
      new ApiError('Bạn không có quyền xem cuộc kiểm toán này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain('Bạn không có quyền xem cuộc kiểm toán này.')
    expect(reloadButton(w)).toBeUndefined()
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('d) 404 ⇒ kind=notfound + nút quay về danh sách kiểm toán', async () => {
    getAudit.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách kiểm toán'))
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/compliance/audits')
    expect(ctaCount(w)).toBe(0)
  })

  it('e) nạp trả null ⇒ nhánh notfound (không khung rỗng)', async () => {
    getAudit.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
  })
})

describe('InternalAuditDetailView — thanh tab dùng chung + dải chỉ số (A9)', () => {
  it('trạng thái lỗi ⇒ thanh tab KHÔNG render', async () => {
    getAudit.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-tabs"]').exists()).toBe(false)
    expect(w.find('[role="tablist"]').exists()).toBe(false)
    expect(w.find('[data-testid="tab-checklist"]').exists()).toBe(false)
  })

  it('content ⇒ thanh tab qua DetailTabBar (role=tablist, 3 tab, a11y)', async () => {
    getAudit.mockResolvedValue(aud())
    const w = mountView()
    await flushPromises()
    expect(w.find('[role="tablist"]').exists()).toBe(true)
    expect(w.findAll('[role="tab"]').length).toBe(3)
    expect(w.find('[data-testid="tab-overview"]').attributes('aria-selected')).toBe('true')
  })

  it('click tab "Bảng kiểm" ⇒ đổi được nội dung (editor hiện)', async () => {
    getAudit.mockResolvedValue(
      aud({ status: 'In Progress', allowed_transitions: ['complete_checklist'], can_operate: true }),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="checklist-editor"]').exists()).toBe(false)
    await w.find('[data-testid="tab-checklist"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="checklist-editor"]').exists()).toBe(true)
    expect(w.find('[data-testid="tab-checklist"]').attributes('aria-selected')).toBe('true')
  })

  it('click tab "Bảng kiểm" ở pha Reporting ⇒ bảng chỉ đọc hiện', async () => {
    getAudit.mockResolvedValue(
      aud({
        status: 'Reporting', allowed_transitions: ['close'], can_close: true,
        checklist_items: [{ idx: 1, item_description: 'A', result: 'Non-Conforming' }],
      }),
    )
    const w = mountView()
    await flushPromises()
    await w.find('[data-testid="tab-checklist"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="checklist-readonly"]').exists()).toBe(true)
  })

  it('dải chỉ số CHỈ ở content, đếm đúng mục không phù hợp', async () => {
    getAudit.mockResolvedValue(
      aud({
        status: 'Reporting', allowed_transitions: ['close'], can_close: true, findings_count: 3,
        checklist_items: [
          { idx: 1, item_description: 'A', result: 'Conforming' },
          { idx: 2, item_description: 'B', result: 'Non-Conforming' },
          { idx: 3, item_description: 'C', result: 'Non-Conforming' },
        ],
      }),
    )
    const w = mountView()
    await flushPromises()
    const kpi = w.find('[data-testid="detail-kpi"]')
    expect(kpi.exists()).toBe(true)
    expect(kpi.text()).toContain('Số phát hiện')
    expect(kpi.text()).toContain('Mục không phù hợp')
    const values = w.findAll('[data-testid="detail-kpi"] .kpi-value').map((v) => v.text())
    expect(values).toEqual(['3', '3', '2'])
  })
})
