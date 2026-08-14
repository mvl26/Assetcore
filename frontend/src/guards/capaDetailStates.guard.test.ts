// Copyright (c) 2026, AssetCore Team
// TDD vòng 4 — CAPADetailView áp khuôn `DetailPageShell`.
//
// RED trước fix (mã cũ `:180`): mọi lỗi nạp bị gộp vào MỘT chuỗi phẳng `loadError`
// rồi in ra DÒNG CHỮ ĐỎ `text-red-500` dưới nhãn "Không tìm thấy…" ⇒
//   • mất mạng / 500 bị dán nhãn 404 (sai nguyên nhân),
//   • 403 thiếu quyền cũng bị dán nhãn 404 (không hiện message thật của server),
//   • KHÔNG có nút nạp lại, KHÔNG có nút quay về ⇒ ngõ cụt.
// Sau fix: 4 trạng thái loại trừ lẫn nhau + phân loại kind THẬT + panel thao tác
// TẮT ngoài trạng thái có-dữ-liệu.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { VIEWS } from '@/test/paths'
import { ApiError, ErrorCode } from '@/api/errors'
import type { CapaDetail } from '@/api/imm16'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'CAPA-2026-00001' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ loading: { value: false }, run: (fn: () => Promise<unknown>) => fn() }),
}))

const fetchCapaDetailSpy = vi.fn<() => Promise<CapaDetail | null>>()
vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    fetchCapaDetail: fetchCapaDetailSpy,
    actionUpdateCapaFields: vi.fn(),
    actionAdvanceCapa: vi.fn(),
    actionEffectivenessCheck: vi.fn(),
  }),
}))

import CAPADetailView from '@/views/incident/CAPADetailView.vue'

// KHÔNG stub DetailPageShell / DetailLoadError — khuôn phải mount THẬT (nếu stub thì
// hợp đồng "tắt panel thao tác ngoài content" không được kiểm chứng).
const stubs = {
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
  RecordHistory: { template: '<div />', methods: { reload() {} } },
  RouterLink: true,
}

function capaFixture(over: Partial<CapaDetail> = {}): CapaDetail {
  return {
    name: 'CAPA-2026-00001',
    asset: 'ACC-ASS-0001',
    severity: 'High',
    status: 'Open',
    workflow_state: 'Verification',
    source_type: 'Finding',
    source_ref: null,
    due_date: null,
    closed_date: null,
    effectiveness_check: null,
    ...over,
  } as CapaDetail
}

function mountView() {
  return mount(CAPADetailView, { global: { stubs } })
}

/** Mọi CTA vòng đời của màn này — phải VẮNG ở 3 trạng thái hỏng. */
function ctaCount(w: ReturnType<typeof mountView>): number {
  return (
    w.findAll('[data-testid="cta-edit"]').length
    + w.findAll('[data-testid="cta-close"]').length
    + w.findAll('[data-testid="cta-reopen"]').length
    + w.findAll('[data-testid^="cta-transition-"]').length
    + w.findAll('[data-testid="no-actions-hint"]').length
    + w.findAll('[data-testid="detail-actions"]').length
  )
}

function reloadButton(w: ReturnType<typeof mountView>) {
  return w.findAll('button').find((b) => b.text().includes(['Thử', 'lại'].join(' ')))
}

beforeEach(() => {
  fetchCapaDetailSpy.mockReset()
  pushSpy.mockClear()
})

describe('CAPADetailView — 4 trạng thái loại trừ (TC-UX4-2x)', () => {
  it('a) đang nạp ⇒ khung xương, KHÔNG nội dung, KHÔNG panel thao tác', async () => {
    let release: (v: CapaDetail) => void = () => {}
    fetchCapaDetailSpy.mockReturnValue(new Promise<CapaDetail>((r) => { release = r }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(ctaCount(w)).toBe(0)
    release(capaFixture())
    await flushPromises()
  })

  it('b) lỗi 500/mạng ⇒ kind=unknown + nút nạp lại + 0 CTA', async () => {
    fetchCapaDetailSpy.mockRejectedValue(
      new ApiError('Mất kết nối tới máy chủ', ErrorCode.INTERNAL, 500),
    )
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('error')
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(w.text()).toContain('Mất kết nối tới máy chủ')
    expect(reloadButton(w)).toBeTruthy()
    expect(ctaCount(w)).toBe(0)
  })

  it('b2) bấm nút nạp lại ⇒ gọi lại hàm nạp lần 2 (nút KHÔNG chết)', async () => {
    fetchCapaDetailSpy.mockRejectedValue(new ApiError('Lỗi máy chủ', ErrorCode.INTERNAL, 500))
    const w = mountView()
    await flushPromises()
    expect(fetchCapaDetailSpy).toHaveBeenCalledTimes(1)
    fetchCapaDetailSpy.mockResolvedValue(capaFixture({ allowed_transitions: [] }))
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(fetchCapaDetailSpy).toHaveBeenCalledTimes(2)
    // Lỗi được xoá ở ĐẦU lượt ⇒ sau khi nạp lại thành công thấy nội dung thật.
    expect(w.attributes('data-state')).toBe('content')
  })

  it('c) 403 in-envelope ⇒ kind=forbidden, 0 nút nạp lại, KHÔNG redirect login', async () => {
    fetchCapaDetailSpy.mockRejectedValue(
      new ApiError('Bạn không có quyền xem phiếu này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain('Bạn không có quyền xem phiếu này.')
    expect(reloadButton(w)).toBeUndefined()
    expect(ctaCount(w)).toBe(0)
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('d) 404 ⇒ kind=notfound, 0 nút nạp lại, có nút quay về danh sách', async () => {
    fetchCapaDetailSpy.mockRejectedValue(
      new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(reloadButton(w)).toBeUndefined()
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách hành động'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/capas')
    expect(ctaCount(w)).toBe(0)
  })

  it('e) nạp trả null ⇒ nhánh notfound (KHÔNG khung chi tiết rỗng)', async () => {
    fetchCapaDetailSpy.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(ctaCount(w)).toBe(0)
  })

  it('f) nạp OK + allowed_transitions=[Closed] ⇒ content + cta-close hiện (hành vi cũ)', async () => {
    fetchCapaDetailSpy.mockResolvedValue(
      capaFixture({ workflow_state: 'Verification', allowed_transitions: ['Closed'] }),
    )
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
  })

  it('g) tiêu đề màn hiện ở CẢ 4 trạng thái (luôn biết đang ở đâu)', async () => {
    const scenarios: Array<() => void> = [
      () => fetchCapaDetailSpy.mockReturnValue(new Promise(() => {})),
      () => fetchCapaDetailSpy.mockRejectedValue(new ApiError('x', ErrorCode.INTERNAL, 500)),
      () => fetchCapaDetailSpy.mockResolvedValue(null),
      () => fetchCapaDetailSpy.mockResolvedValue(capaFixture()),
    ]
    for (const setup of scenarios) {
      fetchCapaDetailSpy.mockReset()
      setup()
      const w = mountView()
      await flushPromises()
      expect(w.text()).toContain('Chi tiết hành động khắc phục/phòng ngừa')
    }
  })
})

describe('GATE-8 / LL-FE-51 — chống thoái lui server-driven CTA (TDD-12)', () => {
  const TARGETS = [
    resolve(VIEWS, 'incident', 'CAPADetailView.vue'),
    resolve(VIEWS, 'compliance', 'InternalAuditDetailView.vue'),
    resolve(VIEWS, 'compliance', 'ManagementReviewDetailView.vue'),
  ]

  for (const file of TARGETS) {
    const src = readFileSync(file, 'utf8')
    const short = file.split('/').slice(-2).join('/')

    it(`${short} — 0 lần gate CTA bằng v-if="… status/workflow_state === …"`, () => {
      const hardcoded = src.match(/v-if="[^"]*(?:status|workflow_state)\s*===/g) ?? []
      expect(hardcoded).toEqual([])
    })

    it(`${short} — vẫn gate theo allowed_transitions của server`, () => {
      expect(/allowed_transitions|allowedTransitions/.test(src)).toBe(true)
    })

    it(`${short} — đã áp DetailPageShell, 0 nhánh ngõ-cụt tự chế, 0 dòng chữ đỏ tải lỗi`, () => {
      expect(src).toContain('DetailPageShell')
      expect(src.match(/v-else-if="!(capa|audit|mr)"/g) ?? []).toEqual([])
      expect(src.match(/text-red-500/g) ?? []).toEqual([])
      // INV-UX4-11: shell đã mang `page-container`; view KHÔNG được lồng lớp thứ hai.
      expect(src.match(/page-container/g) ?? []).toEqual([])
    })
  }
})
