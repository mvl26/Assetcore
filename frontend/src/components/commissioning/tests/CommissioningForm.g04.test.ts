// Copyright (c) 2026, AssetCore Team — AC-CR-85: cảnh báo giấy phép bức xạ trên
// form nghiệm thu phải theo CÙNG cờ với thẻ cổng G04 (`g04_applicable`).
//
// Bug đang khử: phiếu Class C của thiết bị KHÔNG phát bức xạ vẫn hiện «Bắt buộc
// cho thiết bị bức xạ» (vì server từng ghi đè `is_radiation_device = 1`), buộc
// người dùng đính kèm giấy tờ SAI vào hồ sơ pháp lý NĐ98.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import type { CommissioningDoc } from '@/types/imm04'

vi.mock('@/api/imm04', () => ({
  getCommissioning: vi.fn(),
  updateCommissioning: vi.fn(),
  transitionState: vi.fn(),
  listCommissionings: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getUsersByRole: vi.fn().mockResolvedValue([]),
  uploadFile: vi.fn(),
}))
vi.mock('@/api/user', () => ({ listAssignableUsers: vi.fn().mockResolvedValue([]) }))

import CommissioningForm from '@/components/commissioning/CommissioningForm.vue'

function makeDoc(over: Partial<CommissioningDoc> = {}): CommissioningDoc {
  return {
    name: 'AC-2026-0085',
    workflow_state: 'Initial Inspection',
    docstatus: 0,
    risk_class: 'C',
    is_radiation_device: 0,
    qa_license_doc: '',
    baseline_tests: [],
    documents: [],
    ...over,
  } as unknown as CommissioningDoc
}

function mountForm(doc: CommissioningDoc, g04Applicable?: boolean) {
  return mount(CommissioningForm, {
    props: { doc, editMode: true, g04Applicable },
    shallow: true,
  })
}

describe('CommissioningForm — cảnh báo giấy phép bức xạ (AC-CR-85)', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('phiếu Class C không phát bức xạ (g04_applicable=false) ⇒ KHÔNG đòi giấy phép', () => {
    // hostile: cờ trên phiếu vẫn = 1 (dữ liệu cũ do server ghi đè) — server nói
    // cổng KHÔNG áp dụng thì giao diện phải nghe server.
    const wrapper = mountForm(makeDoc({ is_radiation_device: 1 } as Partial<CommissioningDoc>), false)
    expect(wrapper.find('[data-test="g04-license-required"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Bắt buộc cho thiết bị bức xạ')
    expect(wrapper.text()).not.toContain('Bắt buộc upload Giấy phép Cục An toàn Bức xạ')
  })

  it('phiếu bức xạ chưa có giấy phép (g04_applicable=true) ⇒ VẪN cảnh báo', () => {
    const wrapper = mountForm(
      makeDoc({ risk_class: 'Radiation', is_radiation_device: 0 } as Partial<CommissioningDoc>),
      true,
    )
    expect(wrapper.find('[data-test="g04-license-required"]').exists()).toBe(true)
    // giải thích vì sao cổng áp dụng dù ô «thiết bị phát bức xạ» không tích
    expect(wrapper.find('[data-test="g04-applies-by-risk-class"]').exists()).toBe(true)
  })

  it('đã có giấy phép ⇒ hết cảnh báo đỏ', () => {
    const wrapper = mountForm(
      makeDoc({ is_radiation_device: 1, qa_license_doc: '/files/gp.pdf' } as Partial<CommissioningDoc>),
      true,
    )
    expect(wrapper.find('[data-test="g04-license-required"]').exists()).toBe(false)
  })

  it('không truyền g04Applicable (backend cũ) ⇒ rơi về hành vi cũ theo cờ trên phiếu', () => {
    const on = mountForm(makeDoc({ is_radiation_device: 1 } as Partial<CommissioningDoc>))
    expect(on.find('[data-test="g04-license-required"]').exists()).toBe(true)

    const off = mountForm(makeDoc({ is_radiation_device: 0 } as Partial<CommissioningDoc>))
    expect(off.find('[data-test="g04-license-required"]').exists()).toBe(false)
  })
})
