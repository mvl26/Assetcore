// Copyright (c) 2026, AssetCore Team — WorkflowActions CTA server-driven (GATE-8 / LL-FE-51)
//
// RED trước fix (2026-07-24): `useWorkflow.filteredActions` lọc LẠI transition bằng TÊN
// ROLE ở client (`auth.roles.includes(t.allowed_role)`) dù BE đã lọc bằng
// `frappe.get_roles(user)`. Bộ lọc thừa này chỉ TRỪ BỚT và đọc từ bản CACHE localStorage
// → lệch nguồn là nút biến mất ÂM THẦM (RBAC dead-gate), đúng ca CTA "Báo cáo lỗi
// baseline" — hành động DUY NHẤT đưa phiếu baseline không đạt sang Kiểm tra lại (CR-54 §2).
//
// Hợp đồng sau fix: FE render ĐÚNG những gì BE đã lọc (`allowed_transitions` = SSoT),
// chỉ de-dup theo `action`.
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import type { WorkflowTransition } from '@/types/imm04'

import WorkflowActions from '@/components/commissioning/WorkflowActions.vue'

const BASELINE_CTA = 'Báo cáo lỗi baseline'

// Payload THẬT chụp từ BE (2026-07-24, phiếu ACC-26-07-00739 @ Initial Inspection):
//   bench --site miyano console → assetcore.services.imm04.get_form_context(...)
// 13 dòng / 3 action, KHÔNG role nào có tiền tố "IMM " ⇒ vừa là fixture wire-parity,
// vừa là ca de-dup thật.
const AT_INITIAL_INSPECTION: WorkflowTransition[] = [
  { action: 'Phê duyệt phát hành', next_state: 'Clinical Release', allowed_role: 'System Manager' },
  { action: 'Phê duyệt phát hành', next_state: 'Clinical Release', allowed_role: 'AssetCore Super Admin' },
  { action: 'Giữ lâm sàng', next_state: 'Clinical Hold', allowed_role: 'Compliance Manager' },
  { action: 'Giữ lâm sàng', next_state: 'Clinical Hold', allowed_role: 'AssetCore Super Admin' },
  { action: BASELINE_CTA, next_state: 'Re Inspection', allowed_role: 'PM User' },
  { action: 'Giữ lâm sàng', next_state: 'Clinical Hold', allowed_role: 'System Manager' },
  { action: BASELINE_CTA, next_state: 'Re Inspection', allowed_role: 'AssetCore Super Admin' },
  { action: BASELINE_CTA, next_state: 'Re Inspection', allowed_role: 'System Manager' },
  { action: 'Phê duyệt phát hành', next_state: 'Clinical Release', allowed_role: 'Commissioning Manager' },
  { action: 'Giữ lâm sàng', next_state: 'Clinical Hold', allowed_role: 'Commissioning Manager' },
  { action: 'Giữ lâm sàng', next_state: 'Clinical Hold', allowed_role: 'Commissioning User' },
  { action: BASELINE_CTA, next_state: 'Re Inspection', allowed_role: 'Commissioning Manager' },
  { action: BASELINE_CTA, next_state: 'Re Inspection', allowed_role: 'Commissioning User' },
]

function mountActions(allowedTransitions: WorkflowTransition[]) {
  return mount(WorkflowActions, {
    props: {
      currentState: 'Initial Inspection' as const,
      allowedTransitions,
      isLocked: false,
      canSubmit: false,
      loading: false,
    },
  })
}

function btnByText(wrapper: ReturnType<typeof mountActions>, label: string) {
  return wrapper.findAll('button').find((b) => b.text().includes(label))
}

describe('WorkflowActions — CTA server-driven theo allowed_transitions', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('render CTA "Báo cáo lỗi baseline" dù role BE trả về KHÔNG nằm trong auth.roles (IMM-*)', () => {
    const wrapper = mountActions(AT_INITIAL_INSPECTION)
    expect(btnByText(wrapper, BASELINE_CTA), 'CTA báo lỗi baseline phải render').toBeTruthy()
    expect(wrapper.text()).not.toContain('Không có hành động nào khả dụng')
  })

  it('de-dup theo action: 13 dòng transition (payload BE thật) → 3 nút, mỗi action 1 nút', () => {
    const wrapper = mountActions(AT_INITIAL_INSPECTION)
    const matches = wrapper.findAll('button').filter((b) => b.text().includes(BASELINE_CTA))
    expect(matches.length).toBe(1)
    for (const label of ['Phê duyệt phát hành', 'Giữ lâm sàng']) {
      expect(wrapper.findAll('button').filter((b) => b.text().includes(label)).length).toBe(1)
    }
  })

  it('nhãn trạng thái đích hiển thị tiếng Việt (không lộ enum "Re Inspection")', () => {
    const wrapper = mountActions(AT_INITIAL_INSPECTION)
    const btn = btnByText(wrapper, BASELINE_CTA)!
    expect(btn.text()).toContain('Kiểm tra lại')
    expect(btn.text()).not.toContain('Re Inspection')
  })

  it('click CTA → emit transition đúng chuỗi action khớp workflow JSON (không lệch → 422)', async () => {
    const wrapper = mountActions(AT_INITIAL_INSPECTION)
    await btnByText(wrapper, BASELINE_CTA)!.trigger('click')
    expect(wrapper.emitted('transition')?.[0]).toEqual([BASELINE_CTA])
  })

  it('BE không cho phép (allowed_transitions rỗng) → KHÔNG render CTA (không tự chế nút)', () => {
    const wrapper = mountActions([])
    expect(btnByText(wrapper, BASELINE_CTA)).toBeUndefined()
    expect(wrapper.text()).toContain('Không có hành động nào khả dụng')
  })
})
