// Copyright (c) 2026, AssetCore Team
//
// Vòng 33 — FE guard cho list-scope coercion (IMM-00 / list_assets).
//
// BE coerce an toàn page/page_size phi-số (helper _safe_page_int) → envelope
// {pagination, items} hợp lệ luôn được trả, KHÔNG còn HTTP-500 traceback. Phía FE
// listAssets() thin-wrap frappeGet (đã unwrap envelope) — guard này chốt rằng khi
// BE trả envelope hợp lệ (kể cả list rỗng), listAssets() RESOLVE chứ KHÔNG throw,
// và trả items=[] (không undefined) cho UI bind an toàn.
import { describe, it, expect, vi, beforeEach } from 'vitest'

const frappeGet = vi.fn()
vi.mock('./helpers', () => ({
  frappeGet: (...args: unknown[]) => frappeGet(...args),
  frappePost: vi.fn(),
}))

import { listAssets } from './imm00'

describe('listAssets() FE guard — coercion envelope', () => {
  beforeEach(() => {
    frappeGet.mockReset()
  })

  it('resolve KHÔNG throw + trả items=[] khi BE trả envelope hợp lệ (list rỗng)', async () => {
    frappeGet.mockResolvedValue({
      pagination: { page: 1, page_size: 20, total: 0, total_pages: 0, offset: 0 },
      items: [],
    })

    const res = await listAssets()

    expect(res.items).toEqual([])
    expect(res.pagination.page).toBe(1)
    expect(res.pagination.page_size).toBe(20)
    expect(res.pagination.total).toBe(0)
  })

  it('truyền page/page_size client xuống BE nguyên dạng (coercion sống Ở BE)', async () => {
    frappeGet.mockResolvedValue({
      pagination: { page: 1, page_size: 20, total: 0, total_pages: 0, offset: 0 },
      items: [],
    })

    await listAssets({ page: 1, page_size: 20 })

    expect(frappeGet).toHaveBeenCalledWith(
      expect.stringContaining('list_assets'),
      expect.objectContaining({ page: 1, page_size: 20 }),
    )
  })
})
