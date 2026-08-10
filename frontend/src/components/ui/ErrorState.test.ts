// TC-UX2-12/13 — ui/ErrorState.vue: câu VI trung tính (0 traceback) + copy parity 'Thử lại'.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import ErrorState from './ErrorState.vue'

const HERE = dirname(fileURLToPath(import.meta.url))
const DETAIL_LOAD_ERROR = resolve(HERE, '../common/DetailLoadError.vue')

describe('ui/ErrorState (TC-UX2-12, TC-UX2-13)', () => {
  it('TC-UX2-12a: message rỗng ⇒ câu VI trung tính, KHÔNG lộ Error/Traceback/undefined', () => {
    const w = mount(ErrorState, { props: { message: '' } })
    const text = w.text()
    expect(text).toContain('Không tải được dữ liệu')
    for (const leak of ['Error', 'Traceback', 'undefined', 'null', 'NaN']) {
      expect(text, `lộ chuỗi kỹ thuật: ${leak}`).not.toContain(leak)
    }
    expect(w.attributes('role')).toBe('alert')
    expect(w.attributes('data-testid')).toBe('ui-error')
  })

  it('TC-UX2-12b: message truyền vào thắng câu mặc định', () => {
    const w = mount(ErrorState, { props: { message: 'Phiên làm việc đã hết hạn.' } })
    expect(w.text()).toContain('Phiên làm việc đã hết hạn.')
    expect(w.text()).not.toContain('Không tải được dữ liệu')
  })

  it('TC-UX2-12c: click "Thử lại" ⇒ emitted("retry") đúng 1 lần', async () => {
    const w = mount(ErrorState)
    await w.find('[data-testid="ui-error-retry"]').trigger('click')
    expect(w.emitted('retry')).toHaveLength(1)
  })

  it('TC-UX2-12d: retryable=false ⇒ 0 nút thử lại (thử lại vô nghĩa khi thiếu quyền)', () => {
    const w = mount(ErrorState, { props: { retryable: false } })
    expect(w.find('[data-testid="ui-error-retry"]').exists()).toBe(false)
  })

  it('TC-UX2-13: nhãn nút retry === nhãn retry của components/common/DetailLoadError.vue', () => {
    const rendered = mount(ErrorState).get('[data-testid="ui-error-retry"]').text().trim()
    const src = readFileSync(DETAIL_LOAD_ERROR, 'utf8')
    const m = src.match(/emit\('retry'\)"[^>]*>\s*([^<]+?)\s*</)
    expect(m, 'không tìm thấy nút retry trong DetailLoadError.vue').toBeTruthy()
    const legacy = m![1].trim()
    expect(rendered).toBe(legacy) // chống lệch chữ giữa 2 lớp
    expect(rendered).toBe('Thử lại') // chốt 2 đầu, tránh cả hai cùng trôi
  })
})
