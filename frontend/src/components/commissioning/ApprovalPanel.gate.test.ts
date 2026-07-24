// Copyright (c) 2026, AssetCore Team — ApprovalPanel G06 approve-gate (CR-54 §1)
//
// Đóng gate "QTV click Phê duyệt phát hành → 417 thô": nút phát hành lâm sàng
// PHẢI disable + có lý do khi chưa chỉ định Người phê duyệt BGĐ (gate G06), và
// KHÔNG emit transition khi bị chặn (defense-in-depth). Khi đã có người ký →
// nút bật + emit đúng action.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import type { GateStatus } from '@/api/imm04'
import type { CommissioningDoc } from '@/types/imm04'

// ApproverSelect + SubmitForApprovalModal kéo api/user + api/imm04 (typeahead) →
// mock để không chạm axios. Chỉ cần button-gate ở ApprovalPanel.
vi.mock('@/api/imm04', () => ({
  approvePending: vi.fn(),
  getUsersByRole: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/api/user', () => ({ listAssignableUsers: vi.fn().mockResolvedValue([]) }))

import ApprovalPanel from '@/components/commissioning/ApprovalPanel.vue'

const STUBS = { ApproverSelect: true, SubmitForApprovalModal: true }

function makeDoc(over: Partial<CommissioningDoc> = {}): CommissioningDoc {
  return {
    name: 'AC-2026-0001',
    workflow_state: 'Initial Inspection',
    docstatus: 0,
    board_approver: '',
    allowed_transitions: [{ action: 'Phê duyệt phát hành', next_state: 'Clinical Release' }],
    ...over,
  } as unknown as CommissioningDoc
}

const GATE_NO_APPROVER: GateStatus = {
  g01_docs: true, g02_facility: true, g03_baseline: true,
  g04_radiation: true, g05_nc: true, g06_approver: false,
}
const GATE_ALL: GateStatus = { ...GATE_NO_APPROVER, g06_approver: true }

function approveBtn(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('button').find(b => b.text().includes('Phê duyệt phát hành'))
}

describe('ApprovalPanel — G06 approve gate (CR-54 §1)', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('nút "Phê duyệt phát hành" DISABLE + có tooltip lý do khi thiếu người ký BGĐ', () => {
    const wrapper = mount(ApprovalPanel, {
      props: { doc: makeDoc(), gateStatus: GATE_NO_APPROVER, saving: false },
      global: { stubs: STUBS },
    })
    const btn = approveBtn(wrapper)
    expect(btn, 'nút phát hành phải render').toBeTruthy()
    expect(btn!.attributes('disabled')).toBeDefined()
    expect(btn!.attributes('title')).toContain('Người phê duyệt Ban Giám đốc')
  })

  it('click nút bị chặn KHÔNG emit transition (không rơi ra 417 thô)', async () => {
    const wrapper = mount(ApprovalPanel, {
      props: { doc: makeDoc(), gateStatus: GATE_NO_APPROVER, saving: false },
      global: { stubs: STUBS },
    })
    await approveBtn(wrapper)!.trigger('click')
    expect(wrapper.emitted('transition')).toBeUndefined()
  })

  it('khi đã có người ký (G06 pass) → nút BẬT và emit đúng action', async () => {
    const wrapper = mount(ApprovalPanel, {
      props: {
        doc: makeDoc({ board_approver: 'boss@hosp.vn' }),
        gateStatus: GATE_ALL,
        saving: false,
      },
      global: { stubs: STUBS },
    })
    const btn = approveBtn(wrapper)
    expect(btn!.attributes('disabled')).toBeUndefined()
    await btn!.trigger('click')
    expect(wrapper.emitted('transition')?.[0]).toEqual(['Phê duyệt phát hành'])
  })
})
