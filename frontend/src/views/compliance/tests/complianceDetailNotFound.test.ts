// Copyright (c) 2026, AssetCore Team
// TDD (FE regression guard) — IMM-16: 3 màn chi tiết KHÔNG dead-end khi mã bản ghi
// không tồn tại (404). Cùng họ lỗi với CalibrationDetailView (CAL-2026-04591):
//   • load() không catch ⇒ ApiError nổi lên console (unhandled rejection);
//   • InternalAuditDetailView không có nhánh v-else ⇒ TRANG TRẮNG hoàn toàn;
//   • ComplianceRule / ManagementReview có dòng chữ đỏ nhưng KHÔNG có lối thoát.
//
// Bất biến khoá cho cả 3: mount không văng unhandled rejection + render empty-state
// nêu mã bản ghi + nút quay về danh sách gọi router.push đúng route.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ApiError, ErrorCode } from '@/api/errors'

const push = vi.hoisted(() => vi.fn())
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'CR-2026-99999' } }),
  useRouter: () => ({ push, back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    loading: { value: false },
    lastError: { value: null },
    run: (fn: () => Promise<unknown>) => fn(),
  }),
}))

const fetchRuleSpy = vi.hoisted(() => vi.fn())
vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    fetchRule: fetchRuleSpy,
    actionUpdateRule: vi.fn(), actionDeactivateRule: vi.fn(), actionReactivateRule: vi.fn(),
    actionStartAudit: vi.fn(), actionCompleteChecklist: vi.fn(), actionCloseAudit: vi.fn(),
    actionAdvanceMr: vi.fn(), actionFinalizeReview: vi.fn(), actionUpdateReview: vi.fn(),
  }),
}))

const getAuditSpy = vi.hoisted(() => vi.fn())
const getMRSpy = vi.hoisted(() => vi.fn())
vi.mock('@/api/imm16', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm16')>()
  return { ...actual, getAudit: () => getAuditSpy(), getManagementReview: () => getMRSpy() }
})

import ComplianceRuleDetailView from '@/views/compliance/ComplianceRuleDetailView.vue'
import InternalAuditDetailView from '@/views/compliance/InternalAuditDetailView.vue'
import ManagementReviewDetailView from '@/views/compliance/ManagementReviewDetailView.vue'

const stubs = {
  PageHeader: true, StatusBadge: true, BaseModal: true, SkeletonLoader: true,
  DateInput: true, ApproverSelect: true, RouterLink: true,
  RecordHistory: { template: '<div />', methods: { reload() {} } },
}

function notFound(msg: string): ApiError {
  return new ApiError(msg, { code: ErrorCode.NOT_FOUND, httpStatus: 404 })
}

describe('IMM-16 *DetailView — bản ghi không tồn tại (404)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchRuleSpy.mockRejectedValue(notFound('Không tìm thấy quy tắc: CR-2026-99999.'))
    getAuditSpy.mockRejectedValue(notFound('Không tìm thấy kiểm toán: AUD-2026-99999.'))
    getMRSpy.mockRejectedValue(notFound('Không tìm thấy soát xét: MR-2026-99999.'))
  })

  it('ComplianceRuleDetailView → empty-state + về danh sách quy tắc', async () => {
    const wrapper = mount(ComplianceRuleDetailView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('Không tìm thấy quy tắc tuân thủ')
    expect(wrapper.text()).toContain('CR-2026-99999')

    const back = wrapper.findAll('button').find(b => /danh sách/i.test(b.text()))!
    await back.trigger('click')
    expect(push).toHaveBeenCalledWith('/compliance/rules')
  })

  it('InternalAuditDetailView → KHÔNG trang trắng, có empty-state + về danh sách kiểm toán', async () => {
    const wrapper = mount(InternalAuditDetailView, {
      props: { id: 'AUD-2026-99999' },
      global: { stubs },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Không tìm thấy cuộc kiểm toán nội bộ')
    expect(wrapper.text()).toContain('AUD-2026-99999')

    const back = wrapper.findAll('button').find(b => /danh sách/i.test(b.text()))!
    await back.trigger('click')
    expect(push).toHaveBeenCalledWith('/compliance/audits')
  })

  it('ManagementReviewDetailView → empty-state + về danh sách soát xét', async () => {
    const wrapper = mount(ManagementReviewDetailView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('Không tìm thấy cuộc soát xét quản lý')
    expect(wrapper.text()).toContain('CR-2026-99999')

    const back = wrapper.findAll('button').find(b => /danh sách/i.test(b.text()))!
    await back.trigger('click')
    expect(push).toHaveBeenCalledWith('/compliance/mr')
  })
})
