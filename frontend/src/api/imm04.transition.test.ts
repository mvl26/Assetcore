// Copyright (c) 2026, AssetCore Team — IMM-04 transitionState board_approver (CR-54 §1)
//
// GATE-6c dead-control + backward-compat: chứng minh giá trị board_approver người
// dùng chọn ĐI THẲNG vào body POST transition_state (không hardcode / không rớt),
// và caller cũ (không truyền param) gửi body y hệt trước đây — 0 regression.
import { describe, it, expect, vi, beforeEach } from 'vitest'

const frappePostSpy = vi.fn().mockResolvedValue({
  name: 'AC-2026-0001', action_applied: 'Phê duyệt phát hành',
  new_state: 'Clinical Release', docstatus: 0, message: 'ok',
})
vi.mock('@/api/helpers', () => ({
  frappeGet: vi.fn(),
  frappePost: (...args: unknown[]) => frappePostSpy(...args),
}))

import { transitionState } from '@/api/imm04'

const ENDPOINT = '/api/method/assetcore.api.imm04.transition_state'

describe('imm04.transitionState — board_approver 1-call (CR-54 §1)', () => {
  beforeEach(() => frappePostSpy.mockClear())

  it('đưa board_approver người dùng chọn vào body khi có giá trị (dead-control)', async () => {
    await transitionState('AC-2026-0001', 'Phê duyệt phát hành', 'boss@hosp.vn')
    expect(frappePostSpy).toHaveBeenCalledWith(ENDPOINT, {
      name: 'AC-2026-0001',
      action: 'Phê duyệt phát hành',
      board_approver: 'boss@hosp.vn',
    })
  })

  it('phản chiếu ĐÚNG người được chọn — chọn B gửi B, không phải A', async () => {
    await transitionState('AC-2026-0001', 'Phê duyệt phát hành', 'second.reviewer@hosp.vn')
    const body = frappePostSpy.mock.calls[0][1] as Record<string, unknown>
    expect(body.board_approver).toBe('second.reviewer@hosp.vn')
  })

  it('KHÔNG chèn board_approver khi caller cũ không truyền (backward-compat)', async () => {
    await transitionState('AC-2026-0001', 'Bắt đầu lắp đặt')
    expect(frappePostSpy).toHaveBeenCalledWith(ENDPOINT, {
      name: 'AC-2026-0001',
      action: 'Bắt đầu lắp đặt',
    })
    const body = frappePostSpy.mock.calls[0][1] as Record<string, unknown>
    expect('board_approver' in body).toBe(false)
  })

  it('bỏ qua chuỗi rỗng — không gửi board_approver="" (tránh override câm)', async () => {
    await transitionState('AC-2026-0001', 'Phê duyệt phát hành', '')
    const body = frappePostSpy.mock.calls[0][1] as Record<string, unknown>
    expect('board_approver' in body).toBe(false)
  })
})
