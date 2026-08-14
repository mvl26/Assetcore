// TDD (FE regression guard) — IMM-15 approve_forecast "chặn DUYỆT-GIẢ".
// SpareForecastView lái UI theo `workflow_state` THỰC server trả (đọc-lại DB),
// KHÔNG optimistic flip. Chứng minh 3 nhánh:
//   (1) resolve {workflow_state:'Approved'} → toast success + row lật 'Đã phê duyệt'
//       + nút "Phê duyệt" biến mất (gate CTA chỉ dòng Bản nháp).
//   (2) reject ApiError(BAD_STATE)          → notify.fromError + row GIỮ 'Bản nháp'
//       + KHÔNG toast success (không false-success).
//   (3) resolve 200 nhưng workflow_state!='Approved' (submit lỗi bị nuốt phía cũ)
//       → coi như CHƯA duyệt: notify.fromError + row GIỮ 'Bản nháp' + không success.
//
// Mock ở tầng api (`@/api/imm15`) — store `fetchForecasts` đọc-lại từ
// `listSpareForecasts` nên row chỉ lật khi "server" (serverState) đổi THẬT.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const notifyShow = vi.fn()
const notifyFromError = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: notifyShow, fromError: notifyFromError, fromOk: vi.fn(), confirm: vi.fn() }),
}))

const FORECAST_NAME = 'SPF-2026-00007'
// Trạng thái "server" (mô phỏng DB) — fetchForecasts đọc-lại từ đây. Chỉ đổi khi
// approve THẬT persist; guard "no optimistic flip".
let serverState = 'Draft'
function forecastRow() {
  const approved = serverState === 'Approved'
  return {
    name: FORECAST_NAME, forecast_period: '2026-Q3', method: 'Moving_Avg',
    workflow_state: serverState,
    generated_by: 'ktv@x.vn', generated_by_name: 'KTV A',
    approved_by: approved ? 'lead@x.vn' : '',
    approved_by_name: approved ? 'Tổ trưởng B' : '',
    docstatus: approved ? 1 : 0,
  }
}
const listSpareForecasts = vi.fn(async () => ({
  data: [forecastRow()],
  pagination: { total: 1, page: 1, page_size: 50, total_pages: 1 },
}))
const approveForecast = vi.fn()

vi.mock('@/api/imm15', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm15')>()
  return {
    ...actual,
    listSpareForecasts: (p: Record<string, unknown>) => listSpareForecasts(p),
    approveForecast: (f: string) => approveForecast(f),
  }
})

import SpareForecastView from '@/views/inventory/SpareForecastView.vue'

let wrapper: VueWrapper | null = null
async function mountView() {
  wrapper = mount(SpareForecastView, {
    global: { stubs: { RouterLink: true, Transition: false } },
  }) as VueWrapper
  await flushPromises()
  return wrapper
}

const rowSel = `[data-testid="forecast-status-${FORECAST_NAME}"]`
const btnSel = `[data-testid="forecast-approve-${FORECAST_NAME}"]`

beforeEach(() => {
  setActivePinia(createPinia())
  serverState = 'Draft'
  notifyShow.mockClear()
  notifyFromError.mockClear()
  listSpareForecasts.mockClear()
  approveForecast.mockReset()
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.replaceChildren()
})

describe('SpareForecastView — duyệt dự báo theo state THỰC (chặn duyệt-giả)', () => {
  it('render ban đầu: row Bản nháp + có nút "Phê duyệt"', async () => {
    const w = await mountView()
    expect(w.find(rowSel).text()).toContain('Bản nháp')
    expect(w.find(btnSel).exists()).toBe(true)
  })

  it("(1) approve resolve 'Approved' → toast success + row lật 'Đã phê duyệt' + nút ẩn", async () => {
    approveForecast.mockImplementation(async () => {
      serverState = 'Approved' // BE persist thật → refetch trả Approved
      return { name: FORECAST_NAME, workflow_state: 'Approved', docstatus: 1, reorder_recommendations: 3 }
    })
    const w = await mountView()
    await w.find(btnSel).trigger('click')
    await flushPromises()

    expect(approveForecast).toHaveBeenCalledWith(FORECAST_NAME)
    // Toast thành công (qua notify contract), KHÔNG báo lỗi.
    expect(notifyShow).toHaveBeenCalledTimes(1)
    expect(notifyShow.mock.calls[0][0].code).toBe('UI-SAVE-SUCCESS')
    expect(notifyFromError).not.toHaveBeenCalled()
    // Row lật sang 'Đã phê duyệt' + CTA biến mất (gate Draft-only).
    expect(w.find(rowSel).text()).toContain('Đã phê duyệt')
    expect(w.find(btnSel).exists()).toBe(false)
  })

  it('(2) approve reject BAD_STATE → notify.fromError + row GIỮ Bản nháp + KHÔNG success', async () => {
    approveForecast.mockImplementation(async () => {
      throw new ApiError(
        'Không thể duyệt dự báo đã được duyệt.',
        ErrorCode.BAD_STATE, 409,
      )
    })
    const w = await mountView()
    await w.find(btnSel).trigger('click')
    await flushPromises()

    expect(notifyFromError).toHaveBeenCalledTimes(1)
    // notify.fromError nhận lastApiError (ApiError BAD_STATE) — KHÔNG null.
    const arg = notifyFromError.mock.calls[0][0]
    expect(arg).toBeInstanceOf(ApiError)
    expect((arg as ApiError).code).toBe(ErrorCode.BAD_STATE)
    // KHÔNG false-success.
    expect(notifyShow).not.toHaveBeenCalled()
    // Row KHÔNG lật + nút vẫn còn.
    expect(w.find(rowSel).text()).toContain('Bản nháp')
    expect(w.find(rowSel).text()).not.toContain('Đã phê duyệt')
    expect(w.find(btnSel).exists()).toBe(true)
  })

  it("(3) approve resolve 200 nhưng state != 'Approved' (submit lỗi nuốt) → CHƯA duyệt, không success", async () => {
    approveForecast.mockImplementation(async () => (
      // serverState GIỮ 'Draft' — mô phỏng BE trả 200 nhưng chưa persist submit.
      { name: FORECAST_NAME, workflow_state: 'Draft', docstatus: 0, reorder_recommendations: 0 }
    ))
    const w = await mountView()
    await w.find(btnSel).trigger('click')
    await flushPromises()

    // Coi như blocked: surface lỗi, KHÔNG toast success, KHÔNG lật row.
    expect(notifyShow).not.toHaveBeenCalled()
    expect(notifyFromError).toHaveBeenCalledTimes(1)
    expect(w.find(rowSel).text()).toContain('Bản nháp')
    expect(w.find(btnSel).exists()).toBe(true)
  })
})
