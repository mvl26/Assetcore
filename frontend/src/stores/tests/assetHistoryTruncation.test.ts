// Copyright (c) 2026, AssetCore Team
// CR-69 / TC-FE-01 — hợp đồng CẮT DANH SÁCH TRUNG THỰC cho 3 endpoint lịch sử thiết bị
// (imm08 get_asset_pm_history · imm09 get_asset_repair_history · imm12
// get_asset_incident_history).
//
// Bug gốc được chặn: `api/imm08.ts` từng khai `total: number` NON-optional trong khi BE
// CHƯA BAO GIỜ trả khoá đó ⇒ `undefined` lúc chạy mà `vue-tsc` không hé một lời. Test này
// khoá 2 chiều:
//   (1) BE trả ĐỦ `total`/`truncated` ⇒ store map ĐÚNG ra state (không nuốt, không đổi ý).
//   (2) BE trả shape CŨ (worker `--preload` chưa reload, THIẾU 2 khoá) ⇒ KHÔNG crash,
//       fallback `total = rows.length`, `truncated = 0` — KHÔNG bịa chuyện "đã cắt".
// Bất biến neo mọi ca: `truncated === 0` ⇒ `total === rows.length` (đang xem trọn vẹn).

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/imm08', () => ({
  listPMWorkOrders: vi.fn(),
  getPMWorkOrder: vi.fn(),
  assignTechnician: vi.fn(),
  submitPMResult: vi.fn(),
  reportMajorFailure: vi.fn(),
  getPMCalendar: vi.fn(),
  getPMDashboardStats: vi.fn(),
  reschedulePM: vi.fn(),
  getAssetPMHistory: vi.fn(),
}))

vi.mock('@/api/imm09', () => ({
  listRepairWorkOrders: vi.fn(),
  getRepairWorkOrder: vi.fn(),
  assignTechnician: vi.fn(),
  submitDiagnosis: vi.fn(),
  closeWorkOrder: vi.fn(),
  confirmInspection: vi.fn(),
  getRepairKPIs: vi.fn(),
  getAssetRepairHistory: vi.fn(),
  requestSpareParts: vi.fn(),
  startRepair: vi.fn(),
  getMttrReport: vi.fn(),
  createRepairWorkOrder: vi.fn(),
  searchSpareParts: vi.fn(),
}))

import * as api08 from '@/api/imm08'
import * as api09 from '@/api/imm09'
import { useImm08Store } from '@/stores/imm08'
import { useImm09Store } from '@/stores/imm09'

const ASSET = 'ACC-ASS-0001'

/** N dòng lịch sử "đủ dùng" — nội dung không quan trọng, chỉ cần đúng số lượng. */
function rows(n: number): Record<string, unknown>[] {
  return Array.from({ length: n }, (_, i) => ({ name: `REC-${i + 1}` }))
}

const pmHistoryMock = api08.getAssetPMHistory as unknown as ReturnType<typeof vi.fn>
const repairHistoryMock = api09.getAssetRepairHistory as unknown as ReturnType<typeof vi.fn>

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

// ─── IMM-08 · lịch sử bảo trì định kỳ ────────────────────────────────────────────
describe('CR-69 · store IMM-08 — lịch sử bảo trì định kỳ của thiết bị', () => {
  it('BE trả ĐỦ total/truncated khi bị cắt ⇒ map đúng ra state (10 dòng / tổng 12 / đã cắt)', async () => {
    pmHistoryMock.mockResolvedValue({ asset_ref: ASSET, history: rows(10), total: 12, truncated: 1 })
    const store = useImm08Store()

    await store.fetchPMHistory(ASSET)

    expect(store.pmHistory).toHaveLength(10)
    expect(store.pmHistoryTotal).toBe(12)
    expect(store.pmHistoryTruncated).toBe(1)
  })

  it('KHÔNG cắt (3 dòng / trần 10) ⇒ truncated = 0 ∧ total === số dòng đang xem', async () => {
    pmHistoryMock.mockResolvedValue({ asset_ref: ASSET, history: rows(3), total: 3, truncated: 0 })
    const store = useImm08Store()

    await store.fetchPMHistory(ASSET)

    expect(store.pmHistoryTruncated).toBe(0)
    expect(store.pmHistoryTotal).toBe(store.pmHistory.length)
  })

  it('VỪA KHÍT trần (10 dòng / tổng 10) ⇒ truncated = 0 — KHÔNG báo cắt oan', async () => {
    pmHistoryMock.mockResolvedValue({ asset_ref: ASSET, history: rows(10), total: 10, truncated: 0 })
    const store = useImm08Store()

    await store.fetchPMHistory(ASSET)

    expect(store.pmHistoryTotal).toBe(10)
    expect(store.pmHistoryTruncated).toBe(0)
  })

  it('shape CŨ THIẾU total/truncated (worker chưa reload) ⇒ KHÔNG crash, fallback rows.length / 0', async () => {
    // Đây CHÍNH LÀ runtime mà `total: number` non-optional đã nói dối trước CR-69.
    pmHistoryMock.mockResolvedValue({ asset_ref: ASSET, history: rows(4) })
    const store = useImm08Store()

    await store.fetchPMHistory(ASSET)

    expect(store.error).toBeNull()
    expect(store.pmHistoryTotal).toBe(4)
    expect(store.pmHistoryTruncated).toBe(0)
  })
})

// ─── IMM-09 · lịch sử sửa chữa ───────────────────────────────────────────────────
describe('CR-69 · store IMM-09 — lịch sử sửa chữa của thiết bị', () => {
  it('BE trả ĐỦ total/truncated khi bị cắt ⇒ map đúng ra state', async () => {
    repairHistoryMock.mockResolvedValue({ asset_ref: ASSET, history: rows(10), total: 12, truncated: 1 })
    const store = useImm09Store()

    await store.fetchRepairHistory(ASSET)

    expect(store.repairHistory).toHaveLength(10)
    expect(store.repairHistoryTotal).toBe(12)
    expect(store.repairHistoryTruncated).toBe(1)
  })

  it('KHÔNG cắt ⇒ truncated = 0 ∧ total === số dòng đang xem', async () => {
    repairHistoryMock.mockResolvedValue({ asset_ref: ASSET, history: rows(3), total: 3, truncated: 0 })
    const store = useImm09Store()

    await store.fetchRepairHistory(ASSET)

    expect(store.repairHistoryTruncated).toBe(0)
    expect(store.repairHistoryTotal).toBe(store.repairHistory.length)
  })

  it('VỪA KHÍT trần (10/10) ⇒ truncated = 0 — KHÔNG báo cắt oan', async () => {
    repairHistoryMock.mockResolvedValue({ asset_ref: ASSET, history: rows(10), total: 10, truncated: 0 })
    const store = useImm09Store()

    await store.fetchRepairHistory(ASSET)

    expect(store.repairHistoryTotal).toBe(10)
    expect(store.repairHistoryTruncated).toBe(0)
  })

  it('shape CŨ THIẾU 2 khoá ⇒ KHÔNG crash, fallback rows.length / 0', async () => {
    repairHistoryMock.mockResolvedValue({ asset_ref: ASSET, history: rows(4) })
    const store = useImm09Store()

    await store.fetchRepairHistory(ASSET)

    expect(store.error).toBeNull()
    expect(store.repairHistoryTotal).toBe(4)
    expect(store.repairHistoryTruncated).toBe(0)
  })

  it('BE lỡ regress sang BOOL (`truncated: true`) ⇒ FE VẪN nhận diện là đã-cắt (bẫy int-vs-bool CR-01)', async () => {
    // `true === 1` là FALSE trong JS ⇒ nếu store so sánh strict thì dải cảnh báo BIẾN MẤT
    // âm thầm. Chuẩn hoá bằng Number() để lỗi kiểu ở BE không hoá thành lời nói dối ở UI.
    repairHistoryMock.mockResolvedValue({ asset_ref: ASSET, history: rows(10), total: 12, truncated: true })
    const store = useImm09Store()

    await store.fetchRepairHistory(ASSET)

    expect(store.repairHistoryTruncated).toBe(1)
  })
})

// ─── IMM-12 · lịch sử sự cố (chưa có store — kiểm ở tầng API client) ─────────────
describe('CR-69 · API client IMM-12 — lịch sử sự cố của thiết bị', () => {
  it('trả nguyên vẹn asset/items + total/truncated khi BE đã ship 2 khoá', async () => {
    vi.resetModules()
    const get = vi.fn().mockResolvedValue({
      data: { message: { success: true, data: { asset: ASSET, items: rows(10), total: 12, truncated: 1 } } },
    })
    vi.doMock('@/api/axios', () => ({ default: { get } }))
    const { getAssetIncidentHistory } = await import('@/api/imm12')

    const res = await getAssetIncidentHistory(ASSET, 10)

    // Naming contract: path FE == tên function BE (`api/imm12.py`), param khớp signature.
    expect(get).toHaveBeenCalledWith(
      '/api/method/assetcore.api.imm12.get_asset_incident_history',
      { params: { asset: ASSET, limit: 10 } },
    )
    expect(res.asset).toBe(ASSET)
    expect(res.items).toHaveLength(10)
    expect(res.total).toBe(12)
    expect(res.truncated).toBe(1)
  })

  it('shape CŨ THIẾU 2 khoá ⇒ KHÔNG crash; caller fallback được (items.length / 0)', async () => {
    vi.resetModules()
    const get = vi.fn().mockResolvedValue({
      data: { message: { success: true, data: { asset: ASSET, items: rows(4) } } },
    })
    vi.doMock('@/api/axios', () => ({ default: { get } }))
    const { getAssetIncidentHistory } = await import('@/api/imm12')

    const res = await getAssetIncidentHistory(ASSET, 10)

    expect(res.items).toHaveLength(4)
    expect(res.total ?? res.items.length).toBe(4)
    expect(Number(res.truncated ?? 0)).toBe(0)
  })
})
