// Copyright (c) 2026, AssetCore Team
// TC-UX4-40 (docs/ui-ux/03 §13.6) — RCADetailView áp khuôn `DetailPageShell` (lô 2, nhóm N3).
//
// RED trước fix: màn **không có lối nạp lại nào** — lỗi nạp bị đổ vào `err`, cùng cái ref mà
// «Bắt đầu» / «Hoàn thành» / «Huỷ» dùng, rồi in ra một dải chữ đỏ; bên dưới biểu mẫu 5-Why RỖNG
// vẫn hiện nguyên vẹn ⇒ người dùng gõ vào một hồ sơ không tồn tại. Sau fix: `loadError` là ref
// RIÊNG (bẫy 13.9.7 — lỗi hành động không được thay cả trang), 4 trạng thái loại trừ, CTA vòng
// đời nằm trong slot `#actions` nên tắt bằng CẤU TRÚC.
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import type { RCADetail } from '@/api/imm12'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'RCA-2026-0031' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }),
}))

const getRcaSpy = vi.fn<() => Promise<Partial<RCADetail>>>()
vi.mock('@/api/imm12', () => ({
  getRca: (...a: unknown[]) => getRcaSpy(...(a as [])),
  submitRca: vi.fn(),
  startRca: vi.fn(),
  cancelRca: vi.fn(),
}))

import RCADetailView from './RCADetailView.vue'

const stubs = {
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
  RouterLink: true,
}

function rcaFixture(): Partial<RCADetail> {
  return {
    name: 'RCA-2026-0031',
    incident_report: 'INC-2026-0099',
    status: 'RCA In Progress',
    rca_method: '5-Why',
    can_manage_rca: true,
    allowed_transitions: ['Completed', 'Cancelled'],
    five_why_steps: [],
    root_cause: '',
    corrective_action_summary: '',
  } as unknown as Partial<RCADetail>
}

describeDetailStates({
  view: 'RCADetailView',
  tc: 'TC-UX4-40',
  mount: () => mount(RCADetailView, { global: { stubs } }) as never,
  pending: () => getRcaSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getRcaSpy.mockRejectedValue(e),
  // Bản ghi «rỗng» của màn này là object KHÔNG có `name` — `Partial<RCADetail>` khởi tạo `{}`
  // là TRUTHY, nên `:doc` phải là `rca.name ? rca : null` chứ không phải chính `rca`.
  empty: () => getRcaSpy.mockResolvedValue({}),
  ok: () => getRcaSpy.mockResolvedValue(rcaFixture()),
  loadCalls: () => getRcaSpy.mock.calls.length,
  reset: () => {
    getRcaSpy.mockReset()
    pushSpy.mockClear()
  },
  recordId: 'RCA-2026-0031',
  ctaTestIds: ['cta-start-rca', 'cta-complete-rca', 'cta-cancel-rca', 'rca-terminal-banner'],
  routerPush: pushSpy,
})
