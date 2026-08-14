// TC-UX065-6 / -10 — `DocumentDetailView` (2 call-site) di trú `confirm()` trần
// → `notify.confirm()` (ADR-UX-16): phê duyệt tài liệu · lưu trữ theo NĐ98.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithConfirm, resetModalQueue, currentModal } from '@/test/confirmHarness'
import { ref } from 'vue'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const archiveDocument = vi.fn().mockResolvedValue({ name: 'DOC-2026-0001' })
const submitForReview = vi.fn().mockResolvedValue({ name: 'DOC-2026-0001' })
vi.mock('@/api/imm05', () => ({
  archiveDocument: (...a: unknown[]) => archiveDocument(...a),
  submitForReview: (...a: unknown[]) => submitForReview(...a),
}))

const approveDocument = vi.fn().mockResolvedValue(true)
const rejectDocument = vi.fn().mockResolvedValue(true)
const currentDocument = ref<Record<string, unknown> | null>(null)
vi.mock('@/stores/imm05', () => ({
  useImm05Store: () => ({
    currentDocument: currentDocument.value,
    loading: false,
    error: null,
    lastApiError: null,
    fetchDocument: vi.fn(),
    updateDocument: vi.fn(),
    approveDocument: (...a: unknown[]) => approveDocument(...a),
    rejectDocument: (...a: unknown[]) => rejectDocument(...a),
  }),
}))
// KHÔNG mock `useNotify`: view gọi `notify.confirm()` (ADR-UX-16) và ta cần đường thật
// notify → useModal → NotificationModal chạy trọn vẹn. Chỉ chặn phần toast/registry
// bằng cách để `show`/`fromError` chạy thật — chúng không đụng mạng.


import DocumentDetailView from '@/views/document/DocumentDetailView.vue'

const ALL_APIS = [archiveDocument, submitForReview, approveDocument, rejectDocument]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let harness: any = null
beforeEach(() => { harness = null; vi.clearAllMocks() })
afterEach(() => { resetModalQueue(); harness?.unmount(); harness = null })

function makeDoc(over: Record<string, unknown> = {}) {
  return {
    name: 'DOC-2026-0001', document_title: 'Quy trình vận hành máy thở',
    document_type: 'SOP', category: 'Technical', version: '1.0',
    workflow_state: 'Pending Review', status: 'Pending Review',
    allowed_transitions: ['Active', 'Rejected', 'Archived'],
    can_approve: 1, attachments: [], asset: '', asset_name: '',
    ...over,
  }
}

async function mountDetail(over: Record<string, unknown> = {}) {
  currentDocument.value = makeDoc(over)
  harness = mountWithConfirm(DocumentDetailView, {
    props: { name: 'DOC-2026-0001' },
    global: {
      stubs: {
        PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
        StatusBadge: true, SkeletonLoader: true, DateInput: true,
      },
    },
  })
  await flushPromises()
  return harness.wrapper
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function btnByText(w: any, text: string) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const b = (w.findAll('button') as any[]).find((x) => x.text().trim() === text)
  if (!b) throw new Error(`không tìm thấy nút «${text}»`)
  return b
}

// tone theo bảng copy đóng băng `06 §5.2` (bảng 6): lưu trữ NĐ98 là không hoàn tác ⇒ 'error'.
const CASES = [
  { label: 'Duyệt tài liệu', api: approveDocument, over: {}, tone: 'warning' },
  { label: 'Lưu trữ', api: archiveDocument, over: { workflow_state: 'Active' }, tone: 'error' },
] as const

describe('TC-UX065-6 — DocumentDetailView: 2 call-site qua hộp thoại SSoT', () => {
  for (const { label, api, over, tone } of CASES) {
    it(`[${label}] hộp thoại hiện tiếng Việt, CHƯA gọi API`, async () => {
      const w = await mountDetail(over)
      await btnByText(w, label).trigger('click')
      await flushPromises()

      const req = currentModal()
      expect(req, 'không có hộp thoại ⇒ vẫn dùng confirm() trần').toBeTruthy()
      expect(req!.title.length).toBeGreaterThan(0)
      expect(req!.body.length).toBeGreaterThan(0)
      expect(`${req!.title} ${req!.body}`).not.toMatch(/\b(Confirm|Cancel|Approve|Archive|OK)\b/)
      expect(req!.tone, `tone sai cho «${label}» (06 §5.2)`).toBe(tone)
      for (const spy of ALL_APIS) expect(spy).not.toHaveBeenCalled()
    })

    it(`[${label}] «Huỷ» ⇒ 0 lời gọi API`, async () => {
      const w = await mountDetail(over)
      await btnByText(w, label).trigger('click')
      await flushPromises()
      await harness.answerConfirm(false)
      for (const spy of ALL_APIS) expect(spy).not.toHaveBeenCalled()
    })

    it(`[${label}] «Xác nhận» ⇒ ĐÚNG 1 lời gọi với payload cũ`, async () => {
      const w = await mountDetail(over)
      await btnByText(w, label).trigger('click')
      await flushPromises()
      await harness.answerConfirm(true)
      expect(api).toHaveBeenCalledTimes(1)
      expect(api).toHaveBeenCalledWith('DOC-2026-0001')
      for (const spy of ALL_APIS) if (spy !== api) expect(spy).not.toHaveBeenCalled()
    })
  }

  it('[Lưu trữ] giữ NGUYÊN câu NĐ98 cũ trong nội dung hộp thoại', async () => {
    const w = await mountDetail({ workflow_state: 'Active' })
    await btnByText(w, 'Lưu trữ').trigger('click')
    await flushPromises()
    expect(currentModal()!.body).toContain('NĐ98')
    expect(currentModal()!.body).toContain('10 năm')
  })
})
