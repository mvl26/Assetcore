// Copyright (c) 2026, AssetCore Team
// Khối "Bản ghi liên quan" — hiển thị đúng dữ liệu backend trả về, và KHÔNG dẫn người
// dùng tới màn hình không tồn tại.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

const getConnections = vi.fn()
vi.mock('@/api/connections', async () => {
  const actual = await vi.importActual<typeof import('@/api/connections')>('@/api/connections')
  return { ...actual, getConnections: (...a: unknown[]) => getConnections(...a) }
})

import RelatedRecords from './RelatedRecords.vue'

const PAYLOAD = {
  doctype: 'AC Asset',
  name: 'AC-ASSET-2026-00001',
  total: 3,
  groups: [
    {
      label: 'Sự cố & Chất lượng',
      items: [
        { doctype: 'Incident Report', label: 'Sự cố', count: 2, capped: false, filters: { asset: 'AC-ASSET-2026-00001' } },
        { doctype: 'IMM RCA Record', label: 'Phân tích nguyên nhân', count: 0, capped: false, filters: { asset: 'AC-ASSET-2026-00001' } },
      ],
    },
    {
      label: 'Hồ sơ & Vòng đời',
      items: [
        { doctype: 'Asset Lifecycle Event', label: 'Sự kiện vòng đời', count: 1, capped: false, filters: { asset: 'AC-ASSET-2026-00001' } },
      ],
    },
  ],
}

describe('RelatedRecords', () => {
  beforeEach(() => {
    push.mockReset()
    getConnections.mockReset()
  })

  const mountIt = () =>
    mount(RelatedRecords, { props: { doctype: 'AC Asset', name: 'AC-ASSET-2026-00001' } })

  it('render nhóm + số đếm từ backend, không tự khai danh sách doctype', async () => {
    getConnections.mockResolvedValue(PAYLOAD)
    const w = mountIt()
    await flushPromises()

    expect(getConnections).toHaveBeenCalledWith('AC Asset', 'AC-ASSET-2026-00001')
    expect(w.text()).toContain('Sự cố & Chất lượng')
    expect(w.text()).toContain('Hồ sơ & Vòng đời')
    expect(w.text()).toContain('Sự cố')
    expect(w.text()).toContain('Tổng 3')
  })

  it('đếm chạm trần hiển thị dạng 100+ thay vì con số sai', async () => {
    getConnections.mockResolvedValue({
      ...PAYLOAD,
      total: 100,
      groups: [{
        label: 'Bảo trì & Sửa chữa',
        items: [{ doctype: 'PM Work Order', label: 'Phiếu bảo trì', count: 100, capped: true, filters: {} }],
      }],
    })
    const w = mountIt()
    await flushPromises()
    expect(w.text()).toContain('100+')
  })

  it('empty-state có nghĩa khi chưa có bản ghi liên quan', async () => {
    getConnections.mockResolvedValue({ ...PAYLOAD, total: 0, groups: [] })
    const w = mountIt()
    await flushPromises()
    expect(w.text()).toContain('Chưa có bản ghi nào liên quan')
  })

  it('lỗi tải KHÔNG làm vỡ màn, có nút Thử lại gọi lại API', async () => {
    getConnections.mockRejectedValueOnce(new Error('Mất kết nối'))
    const w = mountIt()
    await flushPromises()
    expect(w.text()).toContain('Thử lại')

    getConnections.mockResolvedValue(PAYLOAD)
    await w.findAll('button').find(b => b.text().includes('Thử lại'))!.trigger('click')
    await flushPromises()
    expect(w.text()).toContain('Sự cố & Chất lượng')
  })

  it('bấm ô có màn hình → điều hướng kèm bộ lọc của backend', async () => {
    getConnections.mockResolvedValue(PAYLOAD)
    const w = mountIt()
    await flushPromises()

    await w.findAll('button').find(b => b.text().includes('Sự cố') && !b.text().includes('Chất lượng'))!.trigger('click')
    expect(push).toHaveBeenCalledWith({
      path: '/incidents/list',
      query: { asset: 'AC-ASSET-2026-00001' },
    })
  })

  it('ô của doctype CHƯA có màn hình bị vô hiệu hoá, không điều hướng mù', async () => {
    getConnections.mockResolvedValue(PAYLOAD)
    const w = mountIt()
    await flushPromises()

    // 'Asset Lifecycle Event' không nằm trong DOCTYPE_ROUTE → nút phải disabled.
    const btn = w.findAll('button').find(b => b.text().includes('Sự kiện vòng đời'))!
    expect(btn.attributes('disabled')).toBeDefined()
    await btn.trigger('click')
    expect(push).not.toHaveBeenCalled()
  })
})
