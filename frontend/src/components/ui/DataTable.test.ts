// TC-UX2-09/10 — ui/DataTable.vue: bất biến chống tràn ngang + rỗng KHÔNG câm.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DataTable from './DataTable.vue'
import EmptyState from './EmptyState.vue'
import ErrorState from './ErrorState.vue'
import Skeleton from './Skeleton.vue'

const COLUMNS = [
  { key: 'name', label: 'Mã phiếu' },
  { key: 'asset_name', label: 'Thiết bị' },
  { key: 'due', label: 'Hạn xử lý', align: 'right' as const },
]
const ROWS = [
  { name: 'WO-2026-0001', asset_name: 'Máy thở A', due: '01/08/2026' },
  { name: 'WO-2026-0002', asset_name: 'Máy siêu âm B', due: '05/08/2026' },
]

describe('ui/DataTable (TC-UX2-09, TC-UX2-10)', () => {
  it('TC-UX2-09: luôn có phần tử cha overflow-x-auto + <caption class="sr-only"> khớp prop', () => {
    const w = mount(DataTable, {
      props: { columns: COLUMNS, rows: ROWS, caption: 'Danh sách phiếu bảo trì' },
    })
    expect(w.classes()).toContain('overflow-x-auto')
    expect(w.classes()).toContain('table-wrapper')
    const caption = w.find('caption')
    expect(caption.exists()).toBe(true)
    expect(caption.classes()).toContain('sr-only')
    expect(caption.text()).toBe('Danh sách phiếu bảo trì')
  })

  it('TC-UX2-09b: render đủ <th> theo columns và đúng số <tr> theo rows', () => {
    const w = mount(DataTable, { props: { columns: COLUMNS, rows: ROWS } })
    expect(w.findAll('th')).toHaveLength(3)
    expect(w.findAll('th')[0].text()).toBe('Mã phiếu')
    expect(w.findAll('tbody tr')).toHaveLength(2)
    expect(w.text()).toContain('Máy thở A')
  })

  it('TC-UX2-09c: slot cell-<key> ghi đè nội dung ô', () => {
    const w = mount(DataTable, {
      props: { columns: COLUMNS, rows: ROWS },
      slots: { 'cell-asset_name': '<span class="ghi-de">đã ghi đè</span>' },
    })
    expect(w.find('.ghi-de').text()).toBe('đã ghi đè')
    expect(w.text()).not.toContain('Máy thở A')
  })

  it('TC-UX2-10: rows=[] ⇒ render EmptyState, KHÔNG để <tbody> rỗng câm', () => {
    const w = mount(DataTable, { props: { columns: COLUMNS, rows: [] } })
    expect(w.findComponent(EmptyState).exists()).toBe(true)
    expect(w.text()).toContain('Chưa có dữ liệu')
    // ô rỗng phải trải hết bề ngang bảng
    expect(w.find('tbody td').attributes('colspan')).toBe('3')
  })

  it('TC-UX2-10b: loading ⇒ render Skeleton; error ⇒ render ErrorState phát retry', async () => {
    const loading = mount(DataTable, { props: { columns: COLUMNS, rows: [], loading: true } })
    expect(loading.findAllComponents(Skeleton).length).toBeGreaterThan(0)
    expect(loading.findComponent(EmptyState).exists()).toBe(false)

    const failed = mount(DataTable, {
      props: { columns: COLUMNS, rows: [], error: 'Không tải được danh sách.' },
    })
    expect(failed.findComponent(ErrorState).exists()).toBe(true)
    await failed.find('[data-testid="ui-error-retry"]').trigger('click')
    expect(failed.emitted('retry')).toHaveLength(1)
  })

  it('TC-UX2-09d: clickable ⇒ dòng có role/tabindex + emit row-click; mặc định KHÔNG emit', async () => {
    const w = mount(DataTable, { props: { columns: COLUMNS, rows: ROWS, clickable: true } })
    const row = w.findAll('tbody tr')[1]
    expect(row.attributes('role')).toBe('button')
    expect(row.attributes('tabindex')).toBe('0')
    await row.trigger('click')
    expect(w.emitted('row-click')).toHaveLength(1)
    expect(w.emitted('row-click')![0][0]).toEqual(ROWS[1])
    await row.trigger('keydown.enter')
    expect(w.emitted('row-click')).toHaveLength(2)

    const plain = mount(DataTable, { props: { columns: COLUMNS, rows: ROWS } })
    await plain.findAll('tbody tr')[0].trigger('click')
    expect(plain.emitted('row-click')).toBeUndefined()
  })
})
