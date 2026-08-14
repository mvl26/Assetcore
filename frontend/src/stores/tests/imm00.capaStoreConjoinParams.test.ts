// TDD-7 (BR-00-16 — bug #4 USER Vòng 12) — store-level guard:
// useCapaStore.fetchList({not_closed:1, status:'Overdue'}) PHẢI forward CẢ HAI param
// (status + not_closed/overdue) verbatim cho listCapas — KHÔNG drop/clobber khi merge.
// Sau khi BE conjoin (AND), payload trả total == items.length → store render count khớp
// số dòng. Test này khoá invariant "count hiển thị == số dòng render" ở tầng store.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/imm00', () => ({ listCapas: vi.fn() }))

import * as api from '@/api/imm00'
import { useCapaStore } from '@/stores/imm00'

describe('useCapaStore.fetchList — conjoin params + count==rows (BR-00-16)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('forward CẢ status + not_closed cho listCapas (không drop khi merge)', async () => {
    vi.mocked(api.listCapas).mockResolvedValue({
      items: [{ name: 'CAPA-1', status: 'Overdue' }],
      pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    } as never)
    const store = useCapaStore()
    await store.fetchList({ not_closed: 1, status: 'Overdue' })
    const arg = vi.mocked(api.listCapas).mock.calls[0][0]
    expect(arg).toMatchObject({ not_closed: 1, status: 'Overdue' })
  })

  it('forward CẢ status + overdue cho listCapas (không drop khi merge)', async () => {
    vi.mocked(api.listCapas).mockResolvedValue({
      items: [],
      pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    } as never)
    const store = useCapaStore()
    await store.fetchList({ overdue: 1, status: 'Open' })
    const arg = vi.mocked(api.listCapas).mock.calls[0][0]
    expect(arg).toMatchObject({ overdue: 1, status: 'Open' })
  })

  it('pagination.total == capas.length từ payload conjoin (count == số dòng render)', async () => {
    // BE conjoin: not_closed=1 ∩ status=Overdue → subset Overdue (vd 3 dòng), KHÔNG full open-set.
    const items = [
      { name: 'CAPA-1', status: 'Overdue' },
      { name: 'CAPA-2', status: 'Overdue' },
      { name: 'CAPA-3', status: 'Overdue' },
    ]
    vi.mocked(api.listCapas).mockResolvedValue({
      items,
      pagination: { page: 1, page_size: 20, total: items.length, total_pages: 1 },
    } as never)
    const store = useCapaStore()
    await store.fetchList({ not_closed: 1, status: 'Overdue' })
    // Count hiển thị (pagination.total) PHẢI khớp số dòng render (capas.length) — không còn 117.
    expect(store.pagination.total).toBe(store.capas.length)
    expect(store.pagination.total).toBe(3)
  })
})
