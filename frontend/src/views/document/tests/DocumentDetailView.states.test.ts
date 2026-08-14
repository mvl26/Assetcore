// Copyright (c) 2026, AssetCore Team
// TC-UX4-37 (docs/ui-ux/03 §13.6) — DocumentDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N3).
//
// RED trước fix: nhánh lỗi tự chế in «Không thể tải tài liệu» + nút «Thử lại» cho MỌI loại lỗi —
// kể cả 404 (thử lại vô nghĩa) và 403 (message thật của server bị nuốt, không phân biệt với
// dispatcher-403 hết phiên), và KHÔNG có lối về danh sách ⇒ ngõ cụt. `error` lại là CHUỖI dùng
// chung cho cả lỗi hành động (bẫy 13.9.7). Sau fix: kind THẬT từ SSoT `useDetailAccess`.
import { reactive } from 'vue'
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { describeDetailStates } from '@/test/detailStatesHarness'
import { toApiError } from '@/api/errors'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
  useRoute: () => ({ params: { name: 'DOC-2026-00001' } }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ warning: vi.fn(), success: vi.fn(), error: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/api/imm05', () => ({ submitForReview: vi.fn(), archiveDocument: vi.fn() }))

// Store mock mirror hành vi THẬT của `stores/imm05`: NUỐT lỗi thành chuỗi `error` + giữ
// `lastApiError` — chính hình dạng khiến view cũ không phân loại được kind.
// `reactive` chứ không phải object thường: view đọc qua `computed(() => store.currentDocument)`
// nên state của mock PHẢI theo dõi được, nếu không kết quả nạp bất đồng bộ không tới màn.
const storeState = reactive<{
  currentDocument: Record<string, unknown> | null
  loading: boolean
  error: string | null
  lastApiError: unknown
}>({ currentDocument: null, loading: false, error: null, lastApiError: null })

const fetchDocumentSpy = vi.fn()
vi.mock('@/stores/imm05', () => ({
  useImm05Store: () => ({
    get currentDocument() { return storeState.currentDocument },
    get loading() { return storeState.loading },
    get error() { return storeState.error },
    get lastApiError() { return storeState.lastApiError },
    fetchDocument: fetchDocumentSpy,
    updateDocument: vi.fn(),
    approveDocument: vi.fn(),
    rejectDocument: vi.fn(),
  }),
}))

import DocumentDetailView from '@/views/document/DocumentDetailView.vue'

const stubs = { DateInput: true, StatusBadge: true, RouterLink: true }

function docFixture() {
  return {
    name: 'DOC-2026-00001',
    asset_ref: 'AC-ASSET-2026-00001',
    asset_name: 'Máy thở PB980 — Khoa Hồi sức',
    doc_type: 'Giấy phép lưu hành',
    doc_number: 'GPLH-2026-01',
    version: '1.0',
    issued_date: '2026-01-01',
    workflow_state: 'Pending Review',
    visibility: 'Internal',
    allowed_transitions: ['Active'],
    can_approve: true,
  }
}

function setStore(over: Partial<typeof storeState>) {
  Object.assign(storeState, { currentDocument: null, loading: false, error: null, lastApiError: null }, over)
}

describeDetailStates({
  view: 'DocumentDetailView',
  tc: 'TC-UX4-37',
  mount: () => mount(DocumentDetailView, { props: { name: 'DOC-2026-00001' }, global: { stubs } }) as never,
  pending: () => {
    setStore({ loading: true })
    fetchDocumentSpy.mockReturnValue(new Promise(() => {}))
  },
  fail: (e) => {
    // Store NUỐT lỗi: ghi chuỗi vào `error` + đối tượng vào `lastApiError` (không throw).
    fetchDocumentSpy.mockImplementation(async () => {
      setStore({ error: toApiError(e).message, lastApiError: e })
    })
  },
  empty: () => fetchDocumentSpy.mockImplementation(async () => setStore({ currentDocument: null })),
  ok: () => fetchDocumentSpy.mockImplementation(async () => setStore({ currentDocument: docFixture() })),
  loadCalls: () => fetchDocumentSpy.mock.calls.length,
  reset: () => {
    fetchDocumentSpy.mockReset()
    pushSpy.mockClear()
    setStore({})
  },
  recordId: 'DOC-2026-00001',
  ctaTestIds: ['doc-actions'],
  routerPush: pushSpy,
})
