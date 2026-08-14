// Copyright (c) 2026, AssetCore Team — ApprovalPanel G06 approve-gate (CR-54 §1)
// + thẻ cổng G01–G06 nói đúng cổng thật (CR-76 §FE).
//
// Đóng gate "QTV click Phê duyệt phát hành → 417 thô": nút phát hành lâm sàng
// PHẢI disable + có lý do khi chưa chỉ định Người phê duyệt BGĐ (gate G06), và
// KHÔNG emit transition khi bị chặn (defense-in-depth). Khi đã có người ký →
// nút bật + emit đúng action.
//
// CR-76 bổ sung: (1) G01 qua được NHỜ giải trình thiếu hồ sơ phải hiện nhãn
// riêng, KHÔNG khẳng định "Tất cả hồ sơ bắt buộc đã được xác nhận"; (2) G02 ghi
// rõ là cổng tham khảo; (3) 403 trong envelope ⇒ thông báo tiếng Việt tại chỗ
// thẻ cổng, KHÔNG 6 thẻ đỏ giả, KHÔNG đăng xuất.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import type { GateStatus } from '@/api/imm04'
import type { CommissioningDoc } from '@/types/imm04'
import { ApiError, ErrorCode } from '@/api/errors'
import { gateStatusErrorMessage } from '@/components/commissioning/gateStatusError'

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
  g01_docs: true, g01_waived: false, g02_facility: true, g03_baseline: true,
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

describe('ApprovalPanel — thẻ cổng nói đúng cổng thật (CR-76 §FE)', () => {
  beforeEach(() => setActivePinia(createPinia()))

  // TC-FE-01
  it('G01 đạt NHỜ giải trình ⇒ nhãn riêng + trích giải trình, KHÔNG khẳng định "đã xác nhận đủ hồ sơ"', () => {
    const wrapper = mount(ApprovalPanel, {
      props: {
        doc: makeDoc({
          documents_incomplete: 1,
          documents_incomplete_note: 'Chứng nhận xuất xưởng về sau 10 ngày',
        } as Partial<CommissioningDoc>),
        gateStatus: { ...GATE_ALL, g01_docs: true, g01_waived: true },
        saving: false,
      },
      global: { stubs: STUBS },
    })
    const text = wrapper.text()
    expect(text).toContain('Đạt — có giải trình thiếu hồ sơ')
    expect(text).toContain('Chứng nhận xuất xưởng về sau 10 ngày')
    expect(text).not.toContain('Tất cả hồ sơ bắt buộc đã được xác nhận')
    expect(text).not.toContain('Không còn hồ sơ bắt buộc nào chưa được xác nhận')
  })

  // TC-FE-01b — G01 đạt vì thực sự đủ hồ sơ ⇒ KHÔNG gắn nhãn giải trình
  it('G01 đạt không có giải trình ⇒ không hiện nhãn giải trình', () => {
    const wrapper = mount(ApprovalPanel, {
      props: {
        doc: makeDoc({ board_approver: 'boss@hosp.vn' }),
        gateStatus: { ...GATE_ALL, g01_docs: true, g01_waived: false },
        saving: false,
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.text()).not.toContain('Đạt — có giải trình thiếu hồ sơ')
    expect(wrapper.text()).toContain('Không còn hồ sơ bắt buộc nào chưa được xác nhận')
  })

  // TC-FE-01c — thiếu hồ sơ, KHÔNG giải trình ⇒ nói rõ đang chặn
  it('G01 không đạt ⇒ mô tả nêu rõ đang chặn phát hành', () => {
    const wrapper = mount(ApprovalPanel, {
      props: {
        doc: makeDoc(),
        gateStatus: { ...GATE_ALL, g01_docs: false, g01_waived: false },
        saving: false,
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.text()).toContain('chưa có giải trình — cổng này đang chặn phát hành')
  })

  // TC-FE-01d — phiếu CÓ giải trình nhưng backend vẫn báo cổng chặn (backend chưa
  // nạp bản sửa parity): mô tả KHÔNG được khẳng định oan "chưa có giải trình".
  it('G01 chặn trong khi phiếu đã có giải trình ⇒ không khẳng định "chưa có giải trình"', () => {
    const wrapper = mount(ApprovalPanel, {
      props: {
        doc: makeDoc({
          documents_incomplete: 1,
          documents_incomplete_note: 'Chứng nhận hợp quy về sau 7 ngày',
        } as Partial<CommissioningDoc>),
        gateStatus: { ...GATE_ALL, g01_docs: false, g01_waived: false },
        saving: false,
      },
      global: { stubs: STUBS },
    })
    const text = wrapper.text()
    expect(text).not.toContain('chưa có giải trình')
    expect(text).toContain('Đã có giải trình trên phiếu')
    expect(text).toContain('Chứng nhận hợp quy về sau 7 ngày')
  })

  // TC-FE-02
  it('G02 render nhãn THAM KHẢO + nói rõ không chặn phát hành (cả khi chưa đạt)', () => {
    const wrapper = mount(ApprovalPanel, {
      props: {
        doc: makeDoc(),
        gateStatus: { ...GATE_ALL, g02_facility: false },
        saving: false,
      },
      global: { stubs: STUBS },
    })
    const text = wrapper.text()
    expect(text).toContain('Tham khảo')
    expect(text).toContain('Cổng tham khảo — không chặn phát hành lâm sàng')
    // G02 chưa đạt KHÔNG được kéo tổng kết thành "còn cổng đang chặn"
    expect(text).toContain('Không còn cổng nào chặn phát hành')
  })

  // TC-FE-03 — nhánh 403 in-envelope
  it('403 trong envelope ⇒ thông báo tiếng Việt tại chỗ thẻ cổng, KHÔNG 6 thẻ đỏ giả', () => {
    const msg = gateStatusErrorMessage(
      new ApiError('Không có quyền', { code: ErrorCode.FORBIDDEN, httpStatus: 403 }),
    )
    const wrapper = mount(ApprovalPanel, {
      props: {
        doc: makeDoc(),
        // giống hệt state view đặt lại sau khi lỗi: mọi cổng false
        gateStatus: {
          g01_docs: false, g01_waived: false, g02_facility: false, g03_baseline: false,
          g04_radiation: false, g05_nc: false, g06_approver: false,
        },
        gateError: msg,
        saving: false,
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.find('[data-test="gate-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="gate-error"]').attributes('role')).toBe('alert')
    expect(wrapper.text()).toContain('Bạn không có quyền xem trạng thái cổng của phiếu này')
    // KHÔNG vẽ thẻ cổng nào (6 thẻ đỏ giả)
    expect(wrapper.findAll('li').length).toBe(0)
    expect(wrapper.text()).not.toContain('Còn cổng đang chặn phát hành')
  })

  // TC-FE-03b — helper thuần: map code → câu tiếng Việt, không đụng đăng xuất
  it('gateStatusErrorMessage trả câu tiếng Việt cho FORBIDDEN / NOT_FOUND / lỗi khác', () => {
    expect(
      gateStatusErrorMessage(new ApiError('x', { code: ErrorCode.FORBIDDEN, httpStatus: 403 })),
    ).toContain('không có quyền xem trạng thái cổng')
    expect(
      gateStatusErrorMessage(new ApiError('x', { code: ErrorCode.NOT_FOUND, httpStatus: 404 })),
    ).toContain('Không tìm thấy phiếu nghiệm thu')
    expect(gateStatusErrorMessage(new Error('boom'))).toContain('Chưa tải được trạng thái cổng')
    // không rò mã lỗi thô ra giao diện
    for (const e of [new ApiError('x', { code: ErrorCode.FORBIDDEN }), new Error('boom')]) {
      expect(gateStatusErrorMessage(e)).not.toMatch(/FORBIDDEN|NOT_FOUND|Error/)
    }
  })

  // TC-FE-03c — backend CHƯA nạp phiên bản mới (không có g01_waived) vẫn nói đúng
  it('thiếu khoá g01_waived (backend cũ) ⇒ suy ra giải trình từ chính phiếu', () => {
    const legacyGate = {
      g01_docs: true, g02_facility: true, g03_baseline: true,
      g04_radiation: true, g05_nc: true, g06_approver: true,
    } as GateStatus
    const wrapper = mount(ApprovalPanel, {
      props: {
        doc: makeDoc({
          documents_incomplete: 1,
          documents_incomplete_note: 'Chờ biên bản bàn giao bản gốc',
        } as Partial<CommissioningDoc>),
        gateStatus: legacyGate,
        saving: false,
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.text()).toContain('Đạt — có giải trình thiếu hồ sơ')
  })

  // TC-FE-03d (AC-CR-85) — hợp đồng 8 khoá: `g04_applicable` là khoá PHỤ, KHÔNG
  // đẻ thêm thẻ cổng thứ 7. 6 thẻ G01–G06 giữ nguyên số lượng và thứ tự.
  it('response 8 khoá (thêm g04_applicable) vẫn đúng 6 thẻ cổng G01–G06', () => {
    const gate8: GateStatus = {
      g01_docs: true, g01_waived: false, g02_facility: true, g03_baseline: true,
      g04_radiation: true, g04_applicable: false, g05_nc: true, g06_approver: true,
    }
    const wrapper = mount(ApprovalPanel, {
      props: { doc: makeDoc({ board_approver: 'a@b.c' }), gateStatus: gate8, saving: false },
      global: { stubs: STUBS },
    })
    const cards = wrapper.findAll('li[data-test^="gate-"]')
    expect(cards.length).toBe(6)
    expect(cards.map(c => c.attributes('data-test'))).toEqual([
      'gate-g01_docs', 'gate-g02_facility', 'gate-g03_baseline',
      'gate-g04_radiation', 'gate-g05_nc', 'gate-g06_approver',
    ])
    // khoá phụ KHÔNG rò tên kỹ thuật ra giao diện
    expect(wrapper.text()).not.toContain('g04_applicable')
  })
})
