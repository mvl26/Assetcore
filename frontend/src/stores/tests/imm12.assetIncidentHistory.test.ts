// Copyright (c) 2026, AssetCore Team
// TDD — TC-FE-OPH-15/16 (AC-CR-102): store IMM-12 giữ lịch sử sự cố CỦA MỘT THIẾT BỊ.
//
// Ba bẫy được khoá ở đây, cả ba đều từng làm FE nói dối người dùng:
//  (1) hợp đồng payload của `get_asset_incident_history` KHÁC hai endpoint anh em —
//      rows-key là `items` (KHÔNG `history`), asset-key là `asset` (KHÔNG `asset_ref`).
//      Ai "chuẩn hoá" cho giống nhau sẽ làm nhánh sự cố im lặng thành rỗng.
//  (2) worker backend chưa reload trả shape CŨ thiếu `total`/`truncated` ⇒ phải đọc
//      phòng thủ, KHÔNG được ném và KHÔNG được bịa "đã cắt".
//  (3) `truncated` là int 0/1 (CR-01); nếu backend lỡ regress sang bool thì
//      `res.truncated === 1` là FALSE ⇒ FE im lặng báo "không cắt". Phải `Number(...)`.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const getAssetIncidentHistory = vi.fn()
vi.mock('@/api/imm12', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm12')>()),
  getAssetIncidentHistory: (...a: unknown[]) => getAssetIncidentHistory(...a),
}))

import { useImm12Store } from '@/stores/imm12'

const ASSET = 'AC-ASSET-2026-00042'

const ROW = {
  name: 'INC-2026-00009',
  incident_type: 'Device Malfunction',
  severity: 'Critical',
  status: 'Closed',
  reported_at: '2026-01-20 14:05:00',
  fault_code: 'E-204',
  closed_date: '2026-01-22',
  linked_capa: null,
  rca_record: null,
}

beforeEach(() => {
  setActivePinia(createPinia())
  getAssetIncidentHistory.mockReset()
})

describe('TC-FE-OPH-15 — map payload đúng khoá + đọc phòng thủ shape cũ', () => {
  it('shape ĐẦY ĐỦ {items, total, truncated} ⇒ state khớp payload', async () => {
    getAssetIncidentHistory.mockResolvedValue({
      asset: ASSET, items: [ROW], total: 34, truncated: 1,
    })
    const store = useImm12Store()
    const ok = await store.fetchIncidentHistory(ASSET)

    expect(ok).toBe(true)
    expect(getAssetIncidentHistory).toHaveBeenCalledWith(ASSET, 10)
    expect(store.incidentHistory).toHaveLength(1)
    expect(store.incidentHistory[0].name).toBe('INC-2026-00009')
    // Tổng THẬT trước khi cắt — KHÔNG phải số dòng đang xem.
    expect(store.incidentHistoryTotal).toBe(34)
    expect(store.incidentHistoryTruncated).toBe(1)
    expect(store.incidentHistoryError).toBeNull()
  })

  it('shape CŨ thiếu total/truncated ⇒ fallback items.length / 0, KHÔNG crash', async () => {
    getAssetIncidentHistory.mockResolvedValue({ asset: ASSET, items: [ROW, { ...ROW, name: 'INC-2026-00010' }] })
    const store = useImm12Store()
    const ok = await store.fetchIncidentHistory(ASSET)

    expect(ok).toBe(true)
    expect(store.incidentHistoryTotal).toBe(2)
    // KHÔNG bịa "đã cắt" khi backend không nói gì.
    expect(store.incidentHistoryTruncated).toBe(0)
  })

  it('regress bool `truncated: true` ⇒ VẪN nhận là đã-cắt (bẫy int-vs-bool)', async () => {
    getAssetIncidentHistory.mockResolvedValue({
      asset: ASSET, items: [ROW], total: 34, truncated: true,
    })
    const store = useImm12Store()
    await store.fetchIncidentHistory(ASSET)
    expect(store.incidentHistoryTruncated).toBe(1)
  })

  it('vừa khít trần (10 dòng / total 10) ⇒ truncated 0 (không báo cắt oan)', async () => {
    const items = Array.from({ length: 10 }, (_, i) => ({ ...ROW, name: `INC-${i}` }))
    getAssetIncidentHistory.mockResolvedValue({ asset: ASSET, items, total: 10, truncated: 0 })
    const store = useImm12Store()
    await store.fetchIncidentHistory(ASSET)
    expect(store.incidentHistoryTotal).toBe(10)
    expect(store.incidentHistoryTruncated).toBe(0)
  })

  it('`items` vắng mặt (shape lạ) ⇒ [] chứ KHÔNG ném', async () => {
    getAssetIncidentHistory.mockResolvedValue({ asset: ASSET })
    const store = useImm12Store()
    const ok = await store.fetchIncidentHistory(ASSET)
    expect(ok).toBe(true)
    expect(store.incidentHistory).toEqual([])
    expect(store.incidentHistoryTotal).toBe(0)
  })

  it('`limit` truyền xuống nguyên vẹn khi caller chỉ định', async () => {
    getAssetIncidentHistory.mockResolvedValue({ asset: ASSET, items: [], total: 0, truncated: 0 })
    const store = useImm12Store()
    await store.fetchIncidentHistory(ASSET, 25)
    expect(getAssetIncidentHistory).toHaveBeenCalledWith(ASSET, 25)
  })
})

describe('TC-FE-OPH-16 — lỗi KHÔNG bị nuốt thành "rỗng thật"', () => {
  it('API lỗi ⇒ trả false, incidentHistoryError có thông điệp, danh sách giữ []', async () => {
    getAssetIncidentHistory.mockRejectedValue(new Error('Bạn không có quyền đọc sự cố.'))
    const store = useImm12Store()
    const ok = await store.fetchIncidentHistory(ASSET)

    expect(ok).toBe(false)
    expect(store.incidentHistoryError).toContain('không có quyền')
    expect(store.incidentHistory).toEqual([])
    // Tổng KHÔNG được lên số nào — "0" ở đây là "chưa biết", và view phải render dải
    // lỗi (nhờ `ok === false`) thay vì câu «Chưa có sự cố nào».
    expect(store.incidentHistoryTotal).toBe(0)
  })

  it('lỗi rồi thành công ⇒ error được xoá, dữ liệu vào state', async () => {
    getAssetIncidentHistory.mockRejectedValueOnce(new Error('lỗi mạng'))
    const store = useImm12Store()
    await store.fetchIncidentHistory(ASSET)
    expect(store.incidentHistoryError).toBe('lỗi mạng')

    getAssetIncidentHistory.mockResolvedValue({ asset: ASSET, items: [ROW], total: 1, truncated: 0 })
    const ok = await store.fetchIncidentHistory(ASSET)

    expect(ok).toBe(true)
    expect(store.incidentHistoryError).toBeNull()
    expect(store.incidentHistory).toHaveLength(1)
  })

  it('lỗi SAU khi đã có dữ liệu ⇒ KHÔNG xoá dữ liệu đang xem', async () => {
    getAssetIncidentHistory.mockResolvedValue({ asset: ASSET, items: [ROW], total: 1, truncated: 0 })
    const store = useImm12Store()
    await store.fetchIncidentHistory(ASSET)

    getAssetIncidentHistory.mockRejectedValue(new Error('mất mạng'))
    await store.fetchIncidentHistory(ASSET)

    expect(store.incidentHistory).toHaveLength(1)
    expect(store.incidentHistoryError).toBe('mất mạng')
  })
})
