// Copyright (c) 2026, AssetCore Team
// TC-UX4-51 (docs/ui-ux/03 §13.6) — ProgramDetailView áp khuôn `DetailPageShell`
// (lô 2, nhóm N1 + LƯỠNG DỤNG tạo/sửa).
//
// RED trước fix: view có `DetailLoadError` nhưng tự dựng chuỗi trạng thái và tự gọi
// `loadErrorKind` (bản sao thứ N của logic phân loại) ⇒ panel thao tác nằm trong `PageHeader`
// nên «Chỉnh sửa» vẫn render khi bản ghi hỏng. Sau fix: 4 trạng thái loại trừ bằng cấu trúc,
// kind từ SSoT `useDetailAccess`, CTA trong slot `#actions`.
//
// Bẫy riêng của màn này (§13.4.3): router trỏ CÙNG view cho `/imm06/programs/new`. Nối shell
// ngây thơ ⇒ chế độ TẠO rơi vào `notfound` và biểu mẫu tạo biến mất — sub-case (g') canh đúng đó.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { setRouteParams, resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'
import type { TrainingProgram } from '@/api/imm06'
import { describeDetailStates } from '@/test/detailStatesHarness'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true, capabilities: { value: [] } }),
}))

const getProgramSpy = vi.fn()
vi.mock('@/api/imm06', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm06')>()
  return { ...actual, getProgram: () => getProgramSpy() }
})

import ProgramDetailView from '@/views/training/ProgramDetailView.vue'

const stubs = { StatusBadge: true, SmartSelect: true, RouterLink: true }

function programFixture(): TrainingProgram {
  return {
    name: 'TP-2026-0007',
    program_code: 'TRAIN-PB980-INIT',
    program_name: 'Vận hành máy thở PB980 — khoá cơ bản',
    training_type: 'Initial',
    assessment_method: 'Both',
    duration_hours: 8,
    validity_period_months: 12,
    passing_score_pct: 70,
    is_active: 1,
    is_mandatory_for_operation: 0,
    content_outline: 'Bài 1…',
  } as unknown as TrainingProgram
}

function mountEdit() {
  setActivePinia(createPinia())
  resetRouteMock()
  setRouteParams({ name: 'TP-2026-0007' })
  return mount(ProgramDetailView, { props: { name: 'TP-2026-0007' }, global: { stubs } })
}

describeDetailStates({
  view: 'ProgramDetailView',
  tc: 'TC-UX4-51',
  mount: () => mountEdit() as never,
  pending: () => getProgramSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getProgramSpy.mockRejectedValue(e),
  empty: () => getProgramSpy.mockResolvedValue(null),
  ok: () => getProgramSpy.mockResolvedValue(programFixture()),
  loadCalls: () => getProgramSpy.mock.calls.length,
  reset: () => {
    getProgramSpy.mockReset()
    routerPushSpy().mockClear()
  },
  recordId: 'TP-2026-0007',
  ctaTestIds: ['cta-edit', 'cta-save', 'cta-cancel-edit'],
  routerPush: routerPushSpy() as never,
})

describe("ProgramDetailView — (g') chế độ TẠO MỚI không bị shell nuốt (§13.4.3)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    getProgramSpy.mockReset()
  })

  it('/imm06/programs/new ⇒ content, 0 empty-state, biểu mẫu tạo còn nguyên', async () => {
    const w = mount(ProgramDetailView, { props: {}, global: { stubs } })
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-save"]').exists()).toBe(true)
    expect(w.text()).toContain('Tạo chương trình')
    // Không có lượt nạp nào ở chế độ tạo ⇒ không được gọi API chi tiết.
    expect(getProgramSpy).not.toHaveBeenCalled()
  })
})
