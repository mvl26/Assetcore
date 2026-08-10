// Copyright (c) 2026, AssetCore Team — AC-CR-85: cổng G04 «bức xạ» nói đủ 3 trạng thái.
//
// Bug đang khử: thẻ G04 tự suy từ NGUỒN THỨ HAI `doc.is_radiation_device` — trường
// mà server từng ghi đè `= 1` cho MỌI phiếu Class C/D (kể cả máy không phát bức
// xạ) ⇒ phiếu Class C bị đòi «Giấy phép của Cục An toàn Bức xạ Hạt nhân» KHÔNG
// THỂ tồn tại (deadlock, ép nộp giấy tờ sai vào hồ sơ NĐ98).
//
// Sau AC-CR-85 thẻ đọc CHÍNH khoá `g04_applicable` — cùng predicate
// `services/imm04.py::gate_g04_applies` mà VR-07 dùng để chặn ⇒ quảng cáo ==
// thực thi. Khoá vắng (backend chưa nạp bản mới) ⇒ rơi về đúng hành vi cũ.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import type { GateStatus } from '@/api/imm04'
import type { CommissioningDoc } from '@/types/imm04'
import { resolveG04Applicable, g04StatusLabel, g04Description } from './g04Gate'

vi.mock('@/api/imm04', () => ({
  approvePending: vi.fn(),
  getUsersByRole: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/api/user', () => ({ listAssignableUsers: vi.fn().mockResolvedValue([]) }))

import ApprovalPanel from '@/components/commissioning/ApprovalPanel.vue'

const STUBS = { ApproverSelect: true, SubmitForApprovalModal: true }

function makeDoc(over: Partial<CommissioningDoc> = {}): CommissioningDoc {
  return {
    name: 'AC-2026-0085',
    workflow_state: 'Initial Inspection',
    docstatus: 0,
    board_approver: 'giamdoc@assetcore.test',
    risk_class: 'C',
    is_radiation_device: 0,
    qa_license_doc: '',
    allowed_transitions: [{ action: 'Phê duyệt phát hành', next_state: 'Clinical Release' }],
    ...over,
  } as unknown as CommissioningDoc
}

/** Mọi cổng khác ĐẠT ⇒ tổng kết chỉ còn phụ thuộc G04. */
function makeGate(over: Partial<GateStatus> = {}): GateStatus {
  return {
    g01_docs: true, g01_waived: false, g02_facility: true, g03_baseline: true,
    g04_radiation: true, g05_nc: true, g06_approver: true,
    ...over,
  } as GateStatus
}

function mountPanel(doc: CommissioningDoc, gateStatus: GateStatus) {
  return mount(ApprovalPanel, {
    props: { doc, gateStatus, saving: false },
    global: { stubs: STUBS },
  })
}

function g04Card(wrapper: ReturnType<typeof mount>) {
  const el = wrapper.find('[data-test="gate-g04_radiation"]')
  expect(el.exists(), 'thẻ cổng G04 phải render').toBe(true)
  return el
}

describe('ApprovalPanel — cổng G04 đọc `g04_applicable` (AC-CR-85)', () => {
  beforeEach(() => setActivePinia(createPinia()))

  // TC-FE-G04-01 — ca người dùng thật: Class C, model KHÔNG phát bức xạ.
  it('g04_applicable=false ⇒ «Không áp dụng», KHÔNG nói «Đạt», KHÔNG tính là cổng chặn', () => {
    const wrapper = mountPanel(
      // hostile: server cũ từng ghi đè cờ này = 1 cho Class C ⇒ nguồn thứ hai SAI.
      makeDoc({ is_radiation_device: 1 } as Partial<CommissioningDoc>),
      // g04_radiation=false (hostile) mà vẫn KHÔNG được chặn vì cổng không áp dụng.
      makeGate({ g04_applicable: false, g04_radiation: false }),
    )
    const card = g04Card(wrapper)
    expect(card.text()).toContain('Không áp dụng')
    expect(card.text()).toContain('thiết bị không phát bức xạ')
    // TUYỆT ĐỐI không quảng cáo «Đạt» cho cổng không áp dụng…
    expect(card.text()).not.toMatch(/\bĐạt\b/)
    // …và không đòi giấy phép không thể tồn tại.
    expect(card.text()).not.toContain('Chưa có giấy phép')
    expect(card.text()).not.toContain('đang chặn phát hành')
    // Không tính vào tập cổng đang chặn.
    expect(wrapper.text()).toContain('Không còn cổng nào chặn phát hành')
    expect(wrapper.text()).not.toContain('Còn cổng đang chặn phát hành')
  })

  // TC-FE-G04-02
  it('g04_applicable=true + g04_radiation=true ⇒ «Đã có giấy phép an toàn bức xạ»', () => {
    const wrapper = mountPanel(
      makeDoc({ risk_class: 'Radiation', qa_license_doc: '/files/gp.pdf' } as Partial<CommissioningDoc>),
      makeGate({ g04_applicable: true, g04_radiation: true }),
    )
    const card = g04Card(wrapper)
    expect(card.text()).toContain('Đã có giấy phép an toàn bức xạ')
    expect(card.text()).toContain('Cục An toàn Bức xạ Hạt nhân')
    expect(card.text()).not.toContain('Không áp dụng')
    expect(wrapper.text()).toContain('Không còn cổng nào chặn phát hành')
  })

  // TC-FE-G04-03
  it('g04_applicable=true + g04_radiation=false ⇒ «Chưa có giấy phép» + tính là cổng chặn', () => {
    const wrapper = mountPanel(
      makeDoc({ risk_class: 'Radiation' } as Partial<CommissioningDoc>),
      makeGate({ g04_applicable: true, g04_radiation: false }),
    )
    const card = g04Card(wrapper)
    expect(card.text()).toContain('Chưa có giấy phép an toàn bức xạ')
    expect(card.text()).toContain('đang chặn phát hành')
    expect(card.text()).not.toContain('Không áp dụng')
    expect(wrapper.text()).toContain('Còn cổng đang chặn phát hành')
  })

  // TC-FE-G04-04 — backend chưa nạp bản mới: khoá VẮNG ⇒ hành vi CŨ, thẻ không vỡ.
  it('thiếu khoá g04_applicable (backend cũ) ⇒ rơi về suy luận cũ, thẻ vẫn render', () => {
    const legacyGate = {
      g01_docs: true, g02_facility: true, g03_baseline: true,
      g04_radiation: false, g05_nc: true, g06_approver: true,
    } as GateStatus

    // (a) cờ phiếu = 0 ⇒ như trước: không áp dụng
    const off = mountPanel(makeDoc({ is_radiation_device: 0 } as Partial<CommissioningDoc>), legacyGate)
    expect(g04Card(off).text()).toContain('Không áp dụng')
    expect(off.text()).toContain('Không còn cổng nào chặn phát hành')

    // (b) cờ phiếu = 1 ⇒ như trước: áp dụng và đang chặn
    const on = mountPanel(makeDoc({ is_radiation_device: 1 } as Partial<CommissioningDoc>), legacyGate)
    expect(g04Card(on).text()).toContain('Chưa có giấy phép an toàn bức xạ')
    expect(on.text()).toContain('Còn cổng đang chặn phát hành')
  })
})

describe('g04Gate — predicate hiển thị dùng chung (mutation-probe)', () => {
  it('resolveG04Applicable ưu tiên khoá server, chỉ dự phòng khi khoá vắng', () => {
    // khoá server thắng nguồn thứ hai — CẢ HAI CHIỀU
    expect(resolveG04Applicable({ g04_applicable: false }, { is_radiation_device: 1 })).toBe(false)
    expect(resolveG04Applicable({ g04_applicable: true }, { is_radiation_device: 0 })).toBe(true)
    // khoá vắng ⇒ hành vi cũ
    expect(resolveG04Applicable({}, { is_radiation_device: 1 })).toBe(true)
    expect(resolveG04Applicable({}, { is_radiation_device: 0 })).toBe(false)
    expect(resolveG04Applicable(undefined, undefined)).toBe(false)
  })

  it('g04StatusLabel / g04Description trả ĐÚNG 3 trạng thái, không lẫn nhau', () => {
    const labels = [
      g04StatusLabel(false, false), g04StatusLabel(false, true),
      g04StatusLabel(true, true), g04StatusLabel(true, false),
    ]
    expect(labels[0]).toBe('Không áp dụng (thiết bị không phát bức xạ)')
    expect(labels[1]).toBe('Không áp dụng (thiết bị không phát bức xạ)')
    expect(labels[2]).toBe('Đã có giấy phép an toàn bức xạ')
    expect(labels[3]).toBe('Chưa có giấy phép an toàn bức xạ')
    // 3 nhãn phân biệt được với nhau
    expect(new Set(labels).size).toBe(3)
    // không áp dụng ⇒ không bao giờ chứa chữ «Đạt»
    expect(labels[0]).not.toMatch(/\bĐạt\b/)
    expect(g04Description(false, false)).not.toMatch(/\bĐạt\b/)
    expect(g04Description(false, false)).toContain('không chặn phát hành')
    expect(g04Description(true, false)).toContain('đang chặn phát hành')
    expect(g04Description(true, true)).toContain('Cục An toàn Bức xạ Hạt nhân')
  })
})
