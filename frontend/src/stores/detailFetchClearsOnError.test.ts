// Copyright (c) 2026, AssetCore Team
// TDD — CR-74: store PM/CM phải XOÁ bản ghi đang giữ khi nạp chi tiết thất bại.
//
// Kịch bản dead-control (P0): KTV mở phiếu ĐƯỢC GIAO (200) → điều hướng sang phiếu
// KHÔNG được giao (403 in-envelope). Nếu `currentWO` giữ nguyên bản ghi cũ thì màn
// chi tiết vẫn render dữ liệu + đủ CTA (kể cả "đính ảnh") của phiếu TRƯỚC — vừa lộ
// dữ liệu vừa để người dùng bấm rồi mới báo lỗi. Xoá ⇒ view rơi vào empty-state 403.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

const getPMWorkOrderMock = vi.fn()
const getRepairWorkOrderMock = vi.fn()

vi.mock('@/api/imm08', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm08')>()
  return { ...actual, getPMWorkOrder: (...a: unknown[]) => getPMWorkOrderMock(...a) }
})
vi.mock('@/api/imm09', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm09')>()
  return { ...actual, getRepairWorkOrder: (...a: unknown[]) => getRepairWorkOrderMock(...a) }
})

import { useImm08Store } from './imm08'
import { useImm09Store } from './imm09'

const SERVER_MSG = 'Bạn không có quyền thực hiện hành động này.'
const forbidden = () => new ApiError(SERVER_MSG, {
  code: ErrorCode.FORBIDDEN, httpStatus: 403, messageCode: 'AUTH-403',
})

beforeEach(() => {
  setActivePinia(createPinia())
  getPMWorkOrderMock.mockReset()
  getRepairWorkOrderMock.mockReset()
})

describe('CR-74 · imm08.fetchWorkOrder', () => {
  it('403 sau khi đã nạp phiếu hợp lệ → currentWO = null (không giữ bản ghi cũ)', async () => {
    const store = useImm08Store()
    getPMWorkOrderMock.mockResolvedValueOnce({ name: 'WO-PM-2026-00042', status: 'Open', checklist_results: [] })
    await store.fetchWorkOrder('WO-PM-2026-00042')
    expect(store.currentWO?.name).toBe('WO-PM-2026-00042')

    getPMWorkOrderMock.mockRejectedValueOnce(forbidden())
    await store.fetchWorkOrder('WO-PM-2026-99999')

    expect(store.currentWO).toBeNull()
    expect(store.lastApiError?.code).toBe(ErrorCode.FORBIDDEN)
    expect(store.error).toBe(SERVER_MSG)
  })
})

describe('CR-74 · imm09.fetchWorkOrder', () => {
  it('403 sau khi đã nạp phiếu hợp lệ → currentWO = null (không giữ bản ghi cũ)', async () => {
    const store = useImm09Store()
    getRepairWorkOrderMock.mockResolvedValueOnce({ name: 'WO-RP-2026-00099', status: 'Open', repair_checklist: [] })
    await store.fetchWorkOrder('WO-RP-2026-00099')
    expect(store.currentWO?.name).toBe('WO-RP-2026-00099')

    getRepairWorkOrderMock.mockRejectedValueOnce(forbidden())
    await store.fetchWorkOrder('WO-RP-2026-99999')

    expect(store.currentWO).toBeNull()
    expect(store.lastApiError?.code).toBe(ErrorCode.FORBIDDEN)
    expect(store.error).toBe(SERVER_MSG)
  })
})
