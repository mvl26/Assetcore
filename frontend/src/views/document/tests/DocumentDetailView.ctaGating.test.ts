// Copyright (c) 2026, AssetCore Team
//
// IMM-05 — DocumentDetailView: nút CTA chuyển trạng thái (Gửi duyệt / Phê duyệt /
// Từ chối / Gửi lại / Lưu trữ) gate theo SSoT `allowed_transitions` (BE
// _DOC_VALID_TRANSITIONS, services/imm05.py) + capability doc.approve
// (can_approve), KHÔNG hardcode doc.workflow_state === 'X' (GATE-8 / LL-FE-51).
//
// Khoá 2 hành vi:
//   1. Hết FALSE-PERMISSIVE: user thiếu doc.approve KHÔNG còn thấy Phê duyệt/Từ chối
//      trên phiếu Pending Review (trước đây thấy → bấm mới 403).
//   2. Parity guard: nút CTA quyết định bằng allowed_transitions, KHÔNG workflow_state
//      === (Pending Review nhưng allowed=[] → 0 nút).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ warning: vi.fn(), success: vi.fn(), error: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))
vi.mock('@/api/imm05', () => ({
  submitForReview: vi.fn(),
  archiveDocument: vi.fn(),
}))

// Store hoàn toàn mock — currentDocument = fixture cần render, các action là no-op.
const storeState: { currentDocument: Record<string, unknown> | null } = { currentDocument: null }
vi.mock('@/stores/imm05', () => ({
  useImm05Store: () => ({
    get currentDocument() { return storeState.currentDocument },
    loading: false,
    error: null,
    lastApiError: null,
    fetchDocument: vi.fn(),
    updateDocument: vi.fn(),
    approveDocument: vi.fn(),
    rejectDocument: vi.fn(),
  }),
}))

import DocumentDetailView from '@/views/document/DocumentDetailView.vue'

const stubs = { DateInput: true, StatusBadge: true, SkeletonLoader: true, PageHeader: true }

function docFixture(overrides: Record<string, unknown> = {}) {
  return {
    name: 'DOC-2026-00001',
    asset_ref: 'AC-ASSET-2026-00001',
    asset_name: 'Máy thở',
    doc_category: 'Technical',
    doc_type_detail: 'Manual',
    doc_number: 'DN-01',
    version: '1.0',
    workflow_state: 'Draft',
    issued_date: '2026-01-01',
    expiry_date: null,
    issuing_authority: null,
    visibility: 'Public',
    file_attachment: '/files/x.pdf',
    approved_by: null,
    approval_date: null,
    rejection_reason: null,
    change_summary: null,
    notes: null,
    is_exempt: 0,
    days_until_expiry: null,
    modified: '2026-01-01',
    allowed_transitions: [] as string[],
    can_approve: 0,
    ...overrides,
  }
}

async function render(fixture: Record<string, unknown>) {
  storeState.currentDocument = fixture
  const w = mount(DocumentDetailView, { props: { name: 'DOC-2026-00001' }, global: { stubs } })
  await flushPromises()
  return w
}

function hasBtn(w: Awaited<ReturnType<typeof render>>, txt: string) {
  return w.findAll('button').some(b => b.text().trim() === txt)
}

const APPROVE = 'Duyệt tài liệu'
const REJECT = 'Từ chối'
const SUBMIT = 'Gửi duyệt'
const RESUBMIT = 'Gửi lại'
const ARCHIVE = 'Lưu trữ'
const CANCEL_DRAFT = 'Hủy bỏ'

describe('DocumentDetailView — CTA gating theo allowed_transitions + can_approve', () => {
  beforeEach(() => vi.clearAllMocks())

  it('Pending Review + can_approve=1 → render Phê duyệt & Từ chối', async () => {
    const w = await render(docFixture({
      workflow_state: 'Pending Review',
      allowed_transitions: ['Active', 'Rejected'],
      can_approve: 1,
    }))
    expect(hasBtn(w, APPROVE)).toBe(true)
    expect(hasBtn(w, REJECT)).toBe(true)
  })

  it('Pending Review + can_approve=0 → KHÔNG render Phê duyệt & Từ chối (hết false-permissive)', async () => {
    const w = await render(docFixture({
      workflow_state: 'Pending Review',
      allowed_transitions: ['Active', 'Rejected'],
      can_approve: 0,
    }))
    expect(hasBtn(w, APPROVE)).toBe(false)
    expect(hasBtn(w, REJECT)).toBe(false)
  })

  it('allowed_transitions=[] (Archived) → KHÔNG nút CTA transition nào render', async () => {
    const w = await render(docFixture({
      workflow_state: 'Archived',
      allowed_transitions: [],
      can_approve: 1,
    }))
    for (const t of [SUBMIT, APPROVE, REJECT, RESUBMIT, ARCHIVE, CANCEL_DRAFT]) {
      expect(hasBtn(w, t), `nút "${t}" KHÔNG được render ở trạng thái cuối`).toBe(false)
    }
  })

  it('Draft + allowed gồm Pending Review → nút gộp nhãn "Gửi duyệt" (không "Gửi lại")', async () => {
    // Nút "Gửi duyệt"↔"Gửi lại" GỘP MỘT (06 §7.5): nhãn theo workflow_state
    // (display-only). Draft → "Gửi duyệt".
    const w = await render(docFixture({
      workflow_state: 'Draft',
      allowed_transitions: ['Pending Review', 'Archived'],
      can_approve: 0,
    }))
    expect(hasBtn(w, SUBMIT)).toBe(true)
    expect(hasBtn(w, RESUBMIT)).toBe(false)
  })

  it('Rejected → nút gộp nhãn "Gửi lại" (không "Gửi duyệt") — nhãn theo state (display-only)', async () => {
    const w = await render(docFixture({
      workflow_state: 'Rejected',
      allowed_transitions: ['Pending Review'],
      can_approve: 0,
      rejection_reason: 'Thiếu chữ ký',
    }))
    expect(hasBtn(w, RESUBMIT)).toBe(true)
    expect(hasBtn(w, SUBMIT)).toBe(false)
  })

  it('Lưu trữ/Hủy bỏ gate thêm canApprove: Draft can_approve=1 → Hủy bỏ; can_approve=0 → KHÔNG', async () => {
    const yes = await render(docFixture({
      workflow_state: 'Draft',
      allowed_transitions: ['Pending Review', 'Archived'],
      can_approve: 1,
    }))
    expect(hasBtn(yes, CANCEL_DRAFT)).toBe(true)

    const no = await render(docFixture({
      workflow_state: 'Draft',
      allowed_transitions: ['Pending Review', 'Archived'],
      can_approve: 0,
    }))
    expect(hasBtn(no, CANCEL_DRAFT)).toBe(false)
  })

  it('Active + can_approve=1 → render Lưu trữ (Archived trong allowed)', async () => {
    const w = await render(docFixture({
      workflow_state: 'Active',
      allowed_transitions: ['Archived'],
      can_approve: 1,
    }))
    expect(hasBtn(w, ARCHIVE)).toBe(true)
  })

  it('PARITY: Pending Review nhưng allowed_transitions=[] + can_approve=1 → 0 Phê duyệt/Từ chối (gate là allowed_transitions, KHÔNG workflow_state===)', async () => {
    const w = await render(docFixture({
      workflow_state: 'Pending Review',
      allowed_transitions: [],
      can_approve: 1,
    }))
    expect(hasBtn(w, APPROVE)).toBe(false)
    expect(hasBtn(w, REJECT)).toBe(false)
  })
})
