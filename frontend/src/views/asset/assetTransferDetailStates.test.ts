// Copyright (c) 2026, AssetCore Team
// TC-UX4-27 — AssetTransferDetailView áp khuôn `DetailPageShell` (lô 1, AC-UX-048).
//
// RED trước fix: CẢ CỤM CTA vòng đời (Phê duyệt · Từ chối · Hủy phiếu · Xác nhận tiếp
// nhận) render TRƯỚC nhánh `v-if="loading"` ⇒ nằm NGOÀI mọi trạng thái. Nạp hỏng (mã
// sai / 403 / mất mạng) vẫn thấy nút và bấm được — thao tác vòng đời trên bản ghi
// không tồn tại. `load()` cũng KHÔNG có `catch` ⇒ unhandled rejection + không lối nạp lại.
//
// Sau fix: CTA nằm trong slot `#actions`; lỗi NẠP dùng ref MỚI (`loadKind`/`loadMsg`),
// KHÔNG trộn với `err` — vốn là lỗi HÀNH ĐỘNG của 5 nút.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { ApiError, ErrorCode } from '@/api/errors'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'TRF-2026-00007' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

type TransferFixture = Record<string, unknown>
const getTransferFull = vi.fn<() => Promise<TransferFixture | null>>()
vi.mock('@/api/imm00', () => ({
  getTransferFull: () => getTransferFull(),
  updateTransfer: vi.fn(),
  approveTransfer: vi.fn(),
}))
vi.mock('@/api/helpers', () => ({ frappePost: vi.fn() }))

import AssetTransferDetailView from './AssetTransferDetailView.vue'

// Mount THẬT khuôn (bẫy §7.5) — chỉ stub picker.
const stubs = { SmartSelect: true, ApproverSelect: true, DateInput: true, teleport: true }

function fixture(over: TransferFixture = {}): TransferFixture {
  return {
    name: 'TRF-2026-00007',
    status: 'Pending Approval',
    transfer_type: 'Internal',
    transfer_date: '2026-02-01',
    asset: 'ACC-ASS-0001',
    asset_name: 'Máy thở Hamilton C3',
    from_location_name: 'Khoa Hồi sức',
    to_location_name: 'Khoa Cấp cứu',
    can_edit: 0,
    can_approve: 1,
    can_receive: 0,
    can_cancel: 1,
    ...over,
  }
}

function mountView() {
  return mount(AssetTransferDetailView, { global: { stubs } })
}

/** 2 lớp: panel thao tác + testid CTA cụ thể bị test cũ khoá (§12.6). */
function actionCount(w: ReturnType<typeof mountView>): number {
  return (
    w.findAll('[data-testid="detail-actions"]').length
    + w.findAll('[data-testid="cta-approve"]').length
    + w.findAll('[data-testid="cta-reject"]').length
    + w.findAll('[data-testid="cta-cancel"]').length
    + w.findAll('[data-testid="cta-receive"]').length
    + w.findAll('[data-testid="transfer-no-actions-hint"]').length
  )
}

function reloadButton(w: ReturnType<typeof mountView>) {
  return w.findAll('button').find((b) => b.text().includes('Thử lại'))
}

beforeEach(() => {
  getTransferFull.mockReset()
  pushSpy.mockClear()
})

describe('AssetTransferDetailView — 4 trạng thái loại trừ (TC-UX4-27)', () => {
  it('a) ĐANG TẢI ⇒ khung xương, KHÔNG nội dung, KHÔNG panel thao tác', async () => {
    let release: (v: TransferFixture) => void = () => {}
    getTransferFull.mockReturnValue(new Promise<TransferFixture>((r) => { release = r }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(actionCount(w)).toBe(0)
    release(fixture())
    await flushPromises()
  })

  it('b) 404 ⇒ kind=notfound + tiêu đề vẫn hiện mã phiếu, 0 «Thử lại», 0 CTA vòng đời', async () => {
    getTransferFull.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    // slot #title hiện ở MỌI trạng thái ⇒ luôn biết đang mở phiếu nào.
    expect(w.find('h1').text()).toBe('TRF-2026-00007')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách phiếu luân chuyển'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/asset-transfers')
  })

  it('c) 403 ⇒ kind=forbidden, message THẬT, 0 «Thử lại», KHÔNG redirect login', async () => {
    getTransferFull.mockRejectedValue(
      new ApiError('Bạn không có quyền xem phiếu luân chuyển này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain('Bạn không có quyền xem phiếu luân chuyển này.')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('d) lỗi MẠNG ⇒ kind=unknown + «Thử lại» ⇒ lần 2 OK thì banner tan, CTA trở lại', async () => {
    getTransferFull.mockRejectedValue(new Error('Network Error'))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(getTransferFull).toHaveBeenCalledTimes(1)
    getTransferFull.mockResolvedValue(fixture())
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(getTransferFull).toHaveBeenCalledTimes(2)
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(true)
  })

  it('e) nạp trả null ⇒ notfound RIÊNG (không phải khung «—» đầy dấu gạch)', async () => {
    getTransferFull.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(actionCount(w)).toBe(0)
  })

  it('f) CONTENT ⇒ nội dung + panel thao tác + CTA server-driven đúng cờ capability', async () => {
    getTransferFull.mockResolvedValue(fixture())
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-reject"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(true)
    expect(w.find('[data-testid="asset-name"]').text()).toContain('Máy thở Hamilton C3')
  })
})

describe('TC-UX4-31 — chống tái phát ngõ cụt tự chế (AssetTransferDetailView)', () => {
  const src = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), 'AssetTransferDetailView.vue'),
    'utf8',
  )

  it('3 chỗ `text-red-500` đã đổi sang token ngữ nghĩa `text-danger-500` (dấu sao GIỮ NGUYÊN)', () => {
    expect(src.match(/text-red-500/g) ?? []).toEqual([])
    expect((src.match(/text-danger-500/g) ?? []).length).toBe(3)
  })

  it('0 `page-container` · 0 nhánh `v-else-if="!…"` · 0 nhánh tự quyết trạng thái TẢI', () => {
    expect(src.match(/page-container/g) ?? []).toEqual([])
    expect(src.match(/v-else-if="!/g) ?? []).toEqual([])
    expect(src.match(/v-(?:if|else-if)="[^"]*\bloading\b[^"]*"/g) ?? []).toEqual([])
  })
})
