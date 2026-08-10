// Copyright (c) 2026, AssetCore Team
// TC-UX4-36 (docs/ui-ux/03 §13.6) — ComplianceRuleDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N1).
//
// RED trước fix: view tự dựng chuỗi `loading → !rule → content` và **gộp 404 với mọi lỗi khác**
// (`:kind="loadFailed || 'notfound'"`) ⇒ mất mạng bị dán nhãn «Không tìm thấy quy tắc tuân thủ».
// Sau fix: kind đến từ SSoT `useDetailAccess`, và panel thao tác («Sửa» / «Tạo phiên bản mới» /
// «Ngừng áp dụng») tắt bằng CẤU TRÚC ngoài trạng thái có-dữ-liệu.
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import type { ComplianceRule } from '@/api/imm16'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'CR-2026-0007' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ loading: { value: false }, run: (fn: () => Promise<unknown>) => fn() }),
}))

const fetchRuleSpy = vi.fn<() => Promise<ComplianceRule | null>>()
vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    fetchRule: fetchRuleSpy,
    actionUpdateRule: vi.fn(),
    actionDeactivateRule: vi.fn(),
    actionReactivateRule: vi.fn(),
  }),
}))

import ComplianceRuleDetailView from './ComplianceRuleDetailView.vue'

const stubs = {
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
  RecordHistory: { template: '<div />', methods: { reload() {} } },
  RouterLink: true,
}

function ruleFixture(): ComplianceRule {
  return {
    name: 'CR-2026-0007',
    rule_code: 'CR-2026-0007',
    rule_name: 'Hồ sơ hiệu chuẩn còn hiệu lực',
    source_module: 'IMM-11',
    category: 'Calibration',
    evaluation_frequency: 'Daily',
    severity: 'High',
    is_active: 1,
    version: '1.0',
    threshold_definition: '{"max_overdue_days": 0}',
  } as unknown as ComplianceRule
}

describeDetailStates({
  view: 'ComplianceRuleDetailView',
  tc: 'TC-UX4-36',
  mount: () => mount(ComplianceRuleDetailView, { global: { stubs } }) as never,
  pending: () => fetchRuleSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => fetchRuleSpy.mockRejectedValue(e),
  empty: () => fetchRuleSpy.mockResolvedValue(null),
  ok: () => fetchRuleSpy.mockResolvedValue(ruleFixture()),
  loadCalls: () => fetchRuleSpy.mock.calls.length,
  reset: () => {
    fetchRuleSpy.mockReset()
    pushSpy.mockClear()
  },
  recordId: 'CR-2026-0007',
  // CTA đặc thù của màn — liệt kê TƯỜNG MINH (§13.6 d).
  ctaTestIds: ['cta-edit', 'cta-new-version', 'cta-toggle-active'],
  routerPush: pushSpy,
})
